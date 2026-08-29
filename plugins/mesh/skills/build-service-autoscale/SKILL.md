---
name: build-service-autoscale
description: "The shared CI build service: a Hetzner cx43 as PRIMARY build server plus local k8s lanes on strix. Use when a repo needs its heavy build/test suite off strix, when choosing which lane a pipeline belongs in, when a pipeline sits pending forever, when a build is OOM-killed (exit 137), or when reasoning about build cost. Covers the label contract, memory ceilings, the idle reaper, and the traps that waste a day."
triggers: [build-service-autoscale, buildserver, build server, hetzner, pool=hetzner, tier=dev, woodpecker lane, pipeline pending, exit 137, OOM build, cargo slow ci, wp-build-1, burst agent, ci memory, ci-doctor, orphaned workflow, clone unreachable, exit 128, two vms, autoscaler replicas, infra vs real failure, pass rate, immutable sqlite]
---

# The build service

One sentence: **heavy builds run on a Hetzner box; strix runs only fast checks.**

strix is a workstation whose real job is local LLM inference — ~67 GiB of it is
page cache holding mmap'd model weights. An unbounded build evicts that cache and
tanks inference latency *before* it ever shows as memory pressure, because
kubelet counts reclaimable page cache as available. Getting heavy builds off the
box is the whole point of this service.

## The three lanes

| Lane | Where | Ceiling | How a pipeline opts in |
|---|---|---|---|
| **hetzner** (primary) | `wp-build-1`, cx43 — 8 vCPU / 16 GB / 160 GB | 16 GB | `labels: {pool: hetzner}` |
| **local** (fast checks) | 2 k8s agents on strix | **4 Gi per container** | *no label* (default) |
| **dev** (2 GB challenge) | k8s, `replicas: 0` by default | **2 Gi per container** | `labels: {tier: dev}` |

```yaml
# heavy suite -> Hetzner
labels:
  pool: hetzner
steps:
  - name: test
    image: rust:1.83
    commands: [cargo test --workspace]
```

Omit the label and you are on the local fast lane, capped at 4 Gi. Use that for
fmt, clippy, lint, doc — anything that finishes in a minute or two.

## The label contract (enforced by the scheduler, not by convention)

From woodpecker `server/scheduler/filter.go`:

- A task matches an agent when **every task label** is present on the agent.
- **An unlabelled task therefore matches ANY agent** — there is nothing to check.
- An agent label prefixed `!` is a **required** label: `!pool=hetzner` means
  *the task must carry `pool=hetzner`*.

That last mechanic is what reserves a lane. The Hetzner agent runs
`!pool=hetzner`, so it takes only opted-in work and never steals fast checks.
The dev lane runs `!tier=dev` for the same reason — before that was set, an
ordinary build could land on the 2 GB box and OOM for no reason.

## Why a pipeline sits pending forever

**The most common confusion.** The upstream autoscaler's capacity maths is
label-blind: the server reports `Stats.Workers` as a flat count of polling
agents with no label filtering, so

```
reqPool = pending − free
```

counts *local* free slots against *Hetzner-pinned* demand. A job pinned
`pool: hetzner` will **never** trigger a VM while any local slot is idle — it
just waits. Observed live: a pipeline sat pending 20+ minutes against
`freeTasks = 2`, then started within seconds of the build server appearing.

That is why the build server is **scheduled/idle-reaped, not autoscaled**. If it
is down and your pinned job is pending, bring it up (below) — do not wait for
the autoscaler, it will not act.

## Operating it

Scripts live in `~/Developer/personal/hetzner/scripts/` (repo `fabiantax/hetzner`),
installed on strix under `~/.local/bin/`:

```bash
ssh strix-remote '~/.local/bin/wp-build-up.sh'      # idempotent; no-op if already up
ssh strix-remote 'bash /tmp/build-server-down.sh'   # refuses while a build runs (FORCE=1 overrides)
```

**Idle reaper** — `wp-build-reap.timer`, every 5 min. Deletes the VM when
idle ≥ 15 min **AND** ≥ 50 min into the paid hour. Hetzner bills per *started*
hour, so reaping early throws away paid time and a warm cargo cache for zero
saving. Busy is decided by querying the woodpecker DB for running workflows on
`hetzner`-labelled agents — never by SSH-probing the VM, because a failed probe
is indistinguishable from idle and would delete a machine mid-build.

Consequence you should plan for: **the first build after a reap is cold.**
Within a paid hour the cache is warm and builds are much faster.

## Verify the invariants — before AND after every change

Every incident on 2026-08-29 was a violated invariant that nothing was checking.
Run this first; if it is not green, fix that before debugging anything else.

| Invariant | Why it breaks | Symptom when violated |
|---|---|---|
| At most **1** Hetzner server | autoscaler cannot see a scheduled VM (below) | double spend |
| autoscaler replicas **0** while a scheduled VM exists | they are mutually exclusive | two VMs |
| every repo's `clone` URL is the **tailnet IP** | a repo activated before the k8s migration kept `127.0.0.1` | every remote build fails in ~5s |
| **0** workflows `running` on a dead agent | Woodpecker enforces `timeout` agent-side | phantom queue load forever |
| every queued task's labels match **some live agent** | retiring an agent retires its label | those pipelines wait forever |
| **0** dead agent rows | reaping is the autoscaler's job, and it is off | phantom capacity |
| legacy `woodpecker-server` stopped | retired 2026-08-29 | two control planes |
| `woodpecker-agent.service` (user unit) **active** | it is the `host=strix` lane, NOT legacy | `host: strix` pipelines strand |

```bash
KDB=/var/lib/rancher/k3s/storage/pvc-e1d7b350-dffe-43ba-b7e4-48c41ad2392a_woodpecker_data-woodpecker-server-0/woodpecker.db
q() { sudo -n sqlite3 "$KDB" "$1"; }          # NOT ?immutable=1 — see the trap below
IP=100.112.37.119

curl -s -o /dev/null -w 'healthz=%{http_code}\n' http://$IP:30080/healthz     # want 204
kubectl -n woodpecker get deploy woodpecker-autoscaler -o jsonpath='{.spec.replicas}{"\n"}'  # want 0
q "SELECT 'bad_clone: ' || full_name || ' -> ' || clone FROM repos WHERE clone NOT LIKE 'http://$IP:%';"
q "SELECT 'orphan_running: ' || count(*) FROM workflows WHERE state='running' AND agent_id != 0
     AND agent_id NOT IN (SELECT id FROM agents WHERE last_contact > strftime('%s','now')-300);"
q "SELECT 'queued: ' || count(*) FROM workflows WHERE state='pending';"   # then check label satisfiability, below
q "SELECT 'dead_agents: ' || count(*) FROM agents WHERE last_contact <= strftime('%s','now')-300;"
```

Packaged as `scripts/ci-doctor.sh` in the `hetzner` repo (laptop-only), which exits
non-zero on any violation. The snippet above is the portable equivalent.

## The one-VM rule is structural, not a preference

The autoscaler enumerates **only the servers it created itself**. A scheduled
primary (`wp-build-1`) counts as `pool = 0` to it, so given pending work it
spawns its own VM on top. `MAX_AGENTS=1` caps *its* pool at one — one plus the
scheduled server is **two**. This is not a misconfiguration that can be tuned
away; the two mechanisms cannot both be live.

> **A scheduled primary and a running autoscaler are mutually exclusive.**
> `kubectl -n woodpecker scale deploy/woodpecker-autoscaler --replicas=0`

`build-server-up.sh` now scales the autoscaler to 0 itself and refuses to create
a second server (`FORCE=1` overrides). Re-enabling the autoscaler requires
deleting the scheduled VM **first**.

## Reading a red build: infra vs real

A red build means nothing until you know which kind of red. Atlas #40/#42/#43
failed in ~5 seconds with `clone` exit 128 — a stale forge URL, indistinguishable
from a test failure in the UI, and read as "the fix is broken" for hours.

| Exit | Meaning | Class |
|---|---|---|
| `128` on `clone` | git could not reach the forge — check `repos.clone` | **INFRA** |
| any other on `clone` (255, 2) | clone failed for another reason | **INFRA** |
| `137` | SIGKILL — almost always OOM | **INFRA** |
| `143` | SIGTERM — cancelled, or timed out | **INFRA** |
| `125` / `126` | container could not start or exec | **CONFIG** |
| `127` | command not found in the image | **CONFIG** |
| `101` | Rust: cargo/clippy/test failed | **REAL** |
| `1`, `2`, `100` | the step itself failed | **REAL** |

```bash
q "SELECT CASE
       WHEN s.name='clone' THEN 'INFRA clone (' || s.exit_code || ')'
       WHEN s.exit_code IN (137,143) THEN 'INFRA signal (' || s.exit_code || ')'
       WHEN s.exit_code IN (125,126,127) THEN 'CONFIG (' || s.exit_code || ')'
       ELSE 'REAL exit ' || s.exit_code END AS class, count(*)
     FROM steps s JOIN pipelines p ON p.id=s.pipeline_id
    WHERE s.state='failure' AND p.created > strftime('%s','now') - 14*86400
    GROUP BY class ORDER BY 2 DESC;"
```

Packaged as `scripts/ci-failures.sh` (also per-repo and per-event pass rates).

**Measured baseline, 14 days to 2026-08-29** — use it to tell drift from normal:

| repo | infra | config | real | PR pass rate |
|---|---|---|---|---|
| GraphFusion | 56 | 9 | 197 | **9.3%** |
| fab-swarm | 26 | 5 | 53 | 57.3% |
| Atlas | 9 | 0 | 17 | **0%** |
| aliestax.nl | 3 | **18** | 0 | 28.6% |
| touristthai | 2 | 1 | 9 | 79.6% |

Read it honestly: GraphFusion's gate is failing mostly on **real** failures
(98 × `clippy` exit 101), not infrastructure. aliestax.nl is the opposite —
18 of its 21 failures are a missing binary (`audit`, exit 127), i.e. a broken
pipeline definition, not broken code.

## Trap: never verify a live SQLite DB with `?immutable=1`

That flag asserts the file never changes, so SQLite **skips the WAL** and may
serve stale pages. It reported 11 agent rows as still present after they had
already been deleted — the API had returned `204` for each. Reads are safe
without it; WAL handles concurrent readers.

```bash
sudo -n sqlite3 "$KDB" "..."                    # correct
sudo -n sqlite3 "file:$KDB?immutable=1" "..."   # lies after a write
```

## Trap: orphaned workflows cannot be cancelled through the API

When an agent dies mid-workflow the workflow stays `running` forever
(Woodpecker enforces `timeout` **agent-side**). `POST /api/repos/N/pipelines/M/cancel`
returns **HTTP 400** on these, because the pipeline row is already `killed`
while the workflow row is not — and no endpoint reconciles that drift.
DB surgery is the only route. Back up first (`.backup`), then:

```sql
UPDATE workflows SET state='killed', finished=strftime('%s','now'),
       error='reaped: agent died, workflow orphaned'
 WHERE state IN ('running','pending') AND agent_id != 0
   AND agent_id NOT IN (SELECT id FROM agents WHERE last_contact > strftime('%s','now')-300);
```
Then the matching `steps` (by `steps.pipeline_id`, which references `pipelines.id`)
and any `pipelines` still `running`. Packaged as `scripts/reap-orphans.sh`
(`DRY_RUN=1` supported). 28 were cleared this way on 2026-08-29; see hetzner#23.

**A `pending` workflow is NOT an orphan — check label satisfiability first.**
Woodpecker matches task labels as a **subset** of agent labels. A task pinned to
`labels: {host: strix}` can only run on an agent advertising `host=strix`; if the
agent carrying that label is retired, the task waits forever and reaping does
nothing. This is a *retired lane*, not a queue bug.

```bash
# which queued tasks can no live agent ever run?
q "SELECT t.id, t.labels FROM tasks t JOIN workflows w ON w.id=t.id WHERE w.state='pending';"
q "SELECT id, name, custom_labels FROM agents WHERE last_contact > strftime('%s','now')-300;"
```
Compare the two, ignoring the `woodpecker-ci.org/*`, `org-id` and `repo` keys
(metadata, not matching keys). A task waiting on a *busy but compatible* agent is
normal and must not be flagged.

> Measured 2026-08-29: 9 tasks pinned `host=strix` were stranded because the
> only local-backend agent carrying that label had just been retired with the
> legacy stack. An earlier reading of this — "Woodpecker loses pending tasks
> across a server restart" — was **wrong**: `/api/queue/info` showed every task
> present, and all had been created *after* the last restart.

## The three backends, and why `image:` means two different things

| backend | where steps run | what `image:` means | who uses it |
|---|---|---|---|
| **local** | processes on the agent host | the step **interpreter** (`bash`) | `woodpecker-agent.service` on strix, label `host=strix` |
| **docker** | sibling containers via `docker.sock` | a **container image** | the Hetzner VM, label `pool=hetzner` |
| **kubernetes** | pods in k3s | a **container image** | the three in-cluster agents on strix |

The Hetzner box is **not** a container: image `425448770` is an 80GB Ubuntu
**disk snapshot**, booted as a cx43 VM. Docker runs *on* it, and the agent is a
container there with `/var/run/docker.sock` mounted, so steps are sibling
containers. The docker backend is used rather than kubernetes simply because the
VM is not a k3s member — using the kubernetes backend would mean joining an
ephemeral VM to the cluster over the tailnet (node churn every burst, CNI over
WAN, kubeconfig distribution) or running a second k3s on it.

**Consequence for moving a workflow between lanes:** docker and kubernetes share
`image:` semantics, so moving between *those two* is a label change. Moving a
**local**-backend workflow to either is a two-part atomic edit — `labels` AND
`image:` in one commit — because `image: bash` on a container backend pulls the
`bash` container instead of selecting an interpreter. Never flip only the label.

## Trap: deleting an agent registration breaks a merely-stopped agent

The agent persists its id in `~/.local/share/woodpecker/agent.conf`
(`{"agent_id":2}`). Delete that row from the `agents` table and the agent fails
to start with:

```
authenticate with server: agent could not auth: AgentID not found in database
```

...and `Restart=on-failure` loops it. Fix: `rm` the config file; it registers
fresh on the next start. So only delete registrations for agents that are
genuinely gone — a stopped agent still owns its id.

## Running commands on strix from a laptop session

Use a quoted heredoc on stdin. No temp file, no `scp`, and no quoting damage —
single quotes, double quotes, `$`, and `%` all survive intact:

```bash
ssh strix-remote bash -s <<'EOF'
sudo -n sqlite3 "$KDB" "SELECT count(*) FROM repos WHERE clone LIKE 'http://100.%';"
EOF
```

Writing a script to a file and `scp`-ing it works too, but costs a round trip per
command; that workaround was adopted under early quoting failures and kept far
longer than it needed to be.


## Cost

cx43 is €0.0256/h (~€15.99/mo if left up 24/7). With idle reaping a normal day
lands around €5–10/mo. There is a hard cap of **one** VM
(`WOODPECKER_MAX_AGENTS=1`) — two ran unnoticed for an hour once, which is why
the cap exists. Do not raise it without a deliberate decision.

## Traps that waste a day

0. **`incremental` never applies to your dependencies.** Per the Cargo
   reference: *"Incremental compilation is only used for workspace members and
   'path' dependencies."* Registry crates (tokio, lance, serde...) are **never**
   built incrementally whatever you set. So `incremental = true` does NOT poison
   dependency caching — it only costs sccache coverage on your own crates, which
   are the least worth caching because they are what changes. The reason to
   disable it in CI is different and simpler: **a fresh CI machine has no prior
   incremental state to reuse**, so it can only cost disk, memory and artifact
   size for a benefit that cannot exist there. Prefer `CARGO_INCREMENTAL=0` in
   the pipeline over editing a repo config that also governs local dev.
1. **`rust-toolchain.toml` overrides your image.** If it pins `channel = "stable"`,
   rustup ignores the toolchain baked into `rust:1.83` and downloads current
   stable **every run**. Pin the exact version, or bake a matching toolchain.
2. **The repo's `.cargo/config.toml` IS inherited by CI; the host's is NOT.**
   Step pods get a fresh `$HOME`, so `jobs`, `rustc-wrapper` and linker settings
   must live in the repo. Host-level sccache/mold does nothing for CI.
3. **`cargo test` does not use `[profile.release]`.** With no `[profile.test]`,
   tests build at `debug = 2`, `codegen-units = 256`. Debug info at link time is
   usually the memory peak — not LTO, which sits on the release profile.
4. **cargo-nextest is not a memory fix.** It runs one process per *test* and
   defaults to `num-cpus` threads, so it *raises* run-time peak. Pin
   `test-threads` if you use it.
5. **Exit 137 = SIGKILL = OOM.** You busted the lane's ceiling. The fix is
   usually `debug = 0` and capping `CARGO_BUILD_JOBS`, not a bigger lane.
6. **cgroup `memory.peak` counts page cache**, so naive measurement pins to the
   limit and tells you nothing. Measure with `/usr/bin/time -v` or
   `kubectl top pod`.

## Caching: what persists, and what is actually fast

**Storage layers — the image does NOT determine your volume.**

| Layer | Set by | Survives VM deletion |
|---|---|---|
| VM root disk (160 GB on cx43) | **server type**, not the image | no |
| Snapshot "disk size" | image — only the *minimum* disk it needs | n/a |
| Docker volumes on the VM (`/var/lib/wp-cache`) | the agent compose file | no |
| Woodpecker workspace | docker backend, per pipeline | no |
| Hetzner Volume | attached separately | yes — but **single-attach** |

The image decides what is *installed*; the server type decides *disk size*;
persistence across VMs needs a Volume or object storage.

### The performance fact that decides the design

A Hetzner Cloud Volume is **Ceph-backed network storage, not fast local disk** —
every block is written to three servers. It is 1–2 orders of magnitude slower
than the NVMe already in the VM:

| | Local NVMe (cx43 root disk) | Cloud Volume (Ceph) |
|---|---|---|
| Random 4K IOPS | **~30,000** | 5,000 sustained / 7,500 burst (official cap); community reports often **300–400** |
| Sequential | **2.5–3.6 GB/s** | 200 MB/s sustained / 300 MB/s burst |
| fsync p99 | 1–3 ms | an order of magnitude worse |

**Do not put `target/` on a Volume.** Rust builds are metadata- and fsync-heavy
— thousands of small files, incremental state, per-crate artifacts — which is
exactly the IOPS-bound workload where a Ceph volume loses to local NVMe. You
would be trading recompilation for waiting on network block IO, and builds get
*slower*. A Volume is cheaper than object storage below ~105 GB
(EUR 0.0572/GB/mo vs a flat EUR 5.99/mo for 1 TB), but here that buys slower
builds.

**sccache against object storage is the right shape.** Its pattern is a hash
lookup plus a blob fetch per compilation unit: fewer, larger objects, fetched
with high parallelism over HTTP. That is throughput- and concurrency-bound, not
IOPS-bound, and it does not compete with the local disk the build is using.

### The architecture that follows

1. **Build on the local NVMe.** `target/` lives on the ephemeral 160 GB root
   disk at ~30,000 IOPS. Let it die with the VM.
2. **Bake third-party deps into the snapshot** (`cargo-chef cook`). Free, no
   network, works cold. Cargo.lock changed in only **3 of 21 commits over 30
   days (~86% hit rate)** — the best return available, and independent of
   everything below.
3. **Persist only the content-addressed cache** — sccache -> **Hetzner Object
   Storage** (EUR 5.99/mo, 1 TB + 1 TB egress, same datacentre, multi-client).
   Add this only if measurement shows your own crates' compilation is still the
   bottleneck after (2). It survives VM deletion, which the local disk does not.
4. **`strix-garage`** (S3-compatible, already running, EUR 0) is the free
   alternative to (3) — but every read and write crosses the tailnet to a home
   uplink behind CGNAT, so same-datacentre object storage will beat it. Only
   adopt on measurement.
5. **Hetzner Volume — do not use for this.** Slower than local NVMe for the
   build, and a volume attaches to exactly ONE server at a time and "cannot be
   used simultaneously by multiple servers in a writable state". Even if
   multi-attach existed you would not want it: two VMs writing one ext4
   corrupts it, so it would need a cluster filesystem (OCFS2/GFS2).

> This is why "remote cache for ephemeral runners" is the standard advice:
> build fast on local disk, persist only what is cheap to re-fetch in parallel.
> Single-attach is not a constraint while `MAX_AGENTS=1`; it only becomes one if
> that cap is lifted.

## sccache: read the stats correctly before acting on them

**First, the arithmetic that everyone gets wrong.** sccache computes

```
hit rate = hits / (hits + misses)
```

**Non-cacheable calls are a SEPARATE counter and are NOT in the denominator.**
Verified on strix: `Compile requests 119,539`, `Compile requests executed
62,709`, and hits 28,711 + misses 33,771 = 62,482 ~= executed.

This matters because it is easy to see ~45,000 `crate-type` refusals, conclude
"the hit rate is structurally capped", and stop. **That conclusion is false.**
Refusals cost *wall-clock*, not hit rate. Nothing you do to test binaries,
bins, cdylibs or proc-macros moves the percentage by a single point.

The actual anomaly is the opposite: of the compiles sccache **did** accept,
**~69% missed** (Rust: 14,552 hits / 31,085 misses = 31.9%). Dependency rlibs
are deterministic — after one build they should approach 100%. So this is a
misconfiguration, not a ceiling, and it is fixable.

### The three things that actually cause the misses

1. **`SCCACHE_BASEDIRS` is unset while ~16 worktrees exist.** sccache puts the
   **working directory in the cache key**. strix carries `atlas-wt-{336,347,356,
   375,378,379,381,393,...}`, `atlas-callgraph`, `~/.mesh/bodies/atlas` and the
   main checkout — so `serde` built in one worktree shares nothing with the
   next. With ~1065 dep rlibs per graph that is up to 16x key duplication over
   the entire dependency set. `Base directories (none)` confirms it.
   Biggest single lever. (`--remap-path-prefix` is not a substitute: the flag's
   presence itself alters the key.)
2. **The cache is thrashing.** 43 GiB used against a 60 GiB cap that was never
   tuned, while the working set (deps x worktrees x flag-sets) plausibly exceeds
   it. Raise it only *together with* (1), or you just cache more duplicates.
3. **A repo-local `.cargo/config.toml` silently overrides the global one.**
   Atlas's own sets `incremental = true`, `debug = true`, `jobs = 6` — so the
   carefully-tuned global `incremental = false` / `line-tables-only` is **NOT
   in effect for Atlas**. `-C incremental` makes rustc calls non-cacheable
   outright. Always check the *repo's* config before believing host-level
   tuning applies.

### The measurement trap that invalidates naive readings

**One sccache server serves every Rust project on the box.** Its counters are
per-server and **reset on restart** (uptime was ~23.5h when these were read).
So a `--show-stats` snapshot is a rolling, mixed-workload aggregate across every
repo, worktree and agent — attributing it to one project's crate structure is
unsound.

To get a number you can act on:

```bash
sccache --stop-server && sccache --start-server
# ...one clean build of the repo you care about...
sccache --show-stats
```

To test the worktree hypothesis specifically: reset, build in one worktree,
reset, build the identical commit in another. If the second run is not near
100% Rust hits, cause (1) is wrong.

### Hit rate is a proxy — measure the thing you want

The goal is CI wall-clock and peak memory, not a percentage. `Average compiler
1.541 s` vs `Average cache read hit 0.023 s` means a hit saves ~1.5 s of CPU —
but wall-clock depends on the **dependency critical path**, and a recovered hit
on a crate off that path buys nothing. Use `cargo build --timings` for the
critical path and `/usr/bin/time -v` for peak RSS.

### Work worth removing regardless of caching

- **A fat `main.rs` compiles its whole module tree twice** — once into the
  cacheable rlib, once inside the uncacheable bin. Atlas's `atlas-cli` has a
  2,706-line `main.rs` declaring the same modules as its `lib.rs` across
  ~104k LOC of `src/`. Reduce `main.rs` to a thin `fn main() { lib::run() }`
  wrapper. This is a *remove-work* win, not a hit-rate win.
- **Do not consolidate `tests/*.rs` for caching reasons.** Yes, every test file
  is its own uncacheable `bin` target (Atlas: 156 test targets, 47 benches,
  45 examples). But consolidating costs test isolation and parallelism, and
  `cargo nextest` recovers most of the execution win without that loss.
- **proc-macro crates cannot be cached, ever.** There is nothing to do.
- **Pre-baking deps into the VM snapshot sidesteps sccache entirely.** Keep the
  two ideas distinct: raising the *hit rate* and *removing work from CI* are
  different wins, and conflating them is how the wrong plan gets built.

## Measured 2026-08-29: what did NOT reproduce

**`SCCACHE_BASEDIRS` was recommended as the biggest lever. It did not
reproduce.** Three rounds against an isolated sccache server (own port + cache
dir, shared server untouched), identical synthetic source at two paths:

| Round | Config | Result at path B |
|---|---|---|
| 1 | `SCCACHE_BASEDIRS` unset | 0 hits / 4 misses |
| 2 | `SCCACHE_BASEDIRS=<common parent>` | 0 hits / 4 misses |
| 3 | `SCCACHE_BASEDIRS=<both roots listed>` | 0 hits / 4 misses |

**Do not implement it on the strength of the argument alone.** The theory —
"16 worktrees each hold a private key space over ~1065 dep rlibs" — is
plausible, internally consistent, and unverified.

There is also reason to think the premise is wrong: strix's global config sets
`target-dir = /mnt/models/cargo-target` for **every** project and worktree, so
cargo reuses artifacts at its own layer *before* sccache is consulted. The test
above had to break that sharing (separate `CARGO_TARGET_DIR` per path) to make
sccache visible at all — which introduced a `--out-dir` difference that does not
exist in production. So the experiment cannot settle it either way, and neither
can the argument.

The measurement that would settle it needs a quiet box: stop the shared sccache
server, start it fresh, run **one** clean build of the repo in question, read
stats. Counters are per-server and reset only on restart.

### Calibration: a hello-world is 60% non-cacheable

A 4-dependency probe crate produces **4 cacheable and 6 non-cacheable** calls
(build scripts and the bin itself). So a ~47% non-cacheable ratio on a real
workspace is *better than trivial code*, not evidence of pathology. Any
"N% of calls are refused" argument needs this baseline before it means anything.

## The shared target directory is the bigger question

strix points every project and all ~16 Atlas worktrees at one
`/mnt/models/cargo-target` (105 GB, 28 profile dirs). This is a real trade-off,
not an obvious win:

- **Sharing** gives artifact reuse across worktrees — but cargo takes a **lock
  on the build directory**, so independent builds **serialise** rather than run
  in parallel.
- **Isolating** (a target dir per worktree) removes contention at the cost of
  duplicated artifacts and duplicated compiler work.

Observed here, not theorised: a prior investigation recorded
`"Blocking waiting for file lock"` at the start of a CI build, alongside
signal-15 kills when Gitea Actions and Woodpecker were both admitted into the
shared build pool on the same host. With three CI systems plus multiple agent
sessions building concurrently, **serialisation is a plausible dominant cost —
and it is completely invisible in sccache statistics**, which only ever see
work that actually reached rustc.

If you are optimising CI wall-clock, measure contention before cache hit rate:
grep build logs for `Blocking waiting for file lock`, and check whether
concurrent builds are queueing on the lock or on the strix-build admission pool.

## Trap: `cargo` on strix is not cargo

`~/.local/bin/cargo` shadows the real binary and runs builds under
`systemd-run` (cgroup admission control). Environment variables set around a
`cargo` invocation may **not propagate** into the actual compile — a probe that
sets `RUSTC_WRAPPER` or `SCCACHE_*` and sees no effect is likely hitting this,
not a broken cache. Use `$(rustup which cargo)` to bypass it when measuring.

## Known gaps (do not assume these work)

- **No persistent cache across VMs yet** — see the ranking above; nothing is
  implemented, the cache is warm only within a paid hour.
- **No CI traces**, and build-step memory is not yet in OpenObserve. Woodpecker
  metrics in O2 are scraped from the *legacy* server on `:8010`, not the k8s
  one — do not trust them for the k8s instance.
- **Secrets reach the VM through cloud-init user-data**, readable by anything on
  the box. Treat the build VM as a trust boundary.

## Where the reasoning lives

`fabiantax/hetzner` — `docs/CI-TOPOLOGY.md` (label contract, trigger maths,
memory model), `docs/SECRETS.md`, and `.loopit/ci-pool-split/adr.md`:
ADR-004 (Hetzner primary, why not autoscaled), ADR-005 (billing-aware reaping).
Issues are tracked in that repo's `CI pool split` and
`Observability: build infra` milestones.

> The older `woodpecker` skill describes the **legacy host install** on
> `:8010/:9010` (v3.15, systemd binaries). That instance still exists and still
> serves several repos, but it is not this service. Use this skill for the build
> lanes; use `woodpecker` for the legacy server's own operation.
