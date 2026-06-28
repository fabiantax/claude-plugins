---
name: woodpecker
description: "Woodpecker CI (v3.15) on this host — a self-hosted CI server+agent running alongside gitea Actions as a lighter alternative. Use when managing the woodpecker-server/woodpecker-agent services, logging into the UI, enabling a repo, authoring/linting/running .woodpecker.yml pipelines (incl. the local backend + Dagger-TS), debugging agent registration/OOM/concurrency, or comparing against gitea Actions."
triggers: [woodpecker, woodpecker-server, woodpecker-agent, .woodpecker.yml, woodpecker-cli, :8010, :9010, dagger, ci alternative, MAX_WORKFLOWS]
---

# Woodpecker CI (self-hosted, gitea forge)

Lightweight Go CI server+agent running on this host as an **evaluation spike to replace gitea Actions** (set up 2026-06-16). It runs **alongside** gitea Actions — nothing was removed. Rationale: gitea Actions caused recurring maintenance pain (the GF#424 scheduler bug, `state=None` concurrency-cancellations, crude `act_runner` capacity/cgroup-OOM model). Woodpecker's per-agent workflow cap gives explicit, predictable "one heavy build at a time" control.

> Why Woodpecker over the alternatives: for this profile (self-hosted, solo+agents, heavy Rust, 62 GB shared RAM) Woodpecker (single Go binary, light) beats **Jenkins** (JVM bloat + plugin maintenance = more work) and **Concourse** (heavier, steeper). There is **no mature Rust or TypeScript self-hosted CI *server*** — the TS angle is **Dagger's TS SDK** (write pipeline logic in TS; engine runs *under* Woodpecker). Drone is Woodpecker's now-open-core parent → prefer Woodpecker. Forgejo Actions is the *same* engine as gitea → wouldn't fix the scheduler bugs.

---

## Topology (host binaries + systemd --user — NOT a container, NOT its own repo)

Woodpecker needs no dedicated git repo. The server+agent are binaries; each project's pipeline is a `.woodpecker.yml` **inside that repo** (like `ci.yml`). Server state is a small SQLite DB.

| What | Where |
|------|-------|
| Binaries | `~/code/tools/woodpecker/{woodpecker-server,woodpecker-agent,woodpecker-cli}` (v3.15.0) |
| Server unit | `~/.config/systemd/user/woodpecker-server.service` — HTTP **:8010**, gRPC **:9010** |
| Agent unit | `~/.config/systemd/user/woodpecker-agent.service` — **local backend**, `MAX_WORKFLOWS=1` |
| Config (secrets, chmod 600) | `~/.config/woodpecker/{server.env,agent.env}` |
| SQLite DB | `~/.local/share/woodpecker/woodpecker.db` |
| Agent registration | `~/.local/share/woodpecker/agent.conf` (`{"agent_id":N}`) |
| UI | **http://100.112.37.119:8010** (tailscale IP — see gotcha) |
| Logs | `journalctl --user -fu woodpecker-server` / `-fu woodpecker-agent` |

**Agent design (the OOM fix):** `WOODPECKER_BACKEND=local` runs steps directly on the host shell → reuses `cargo`/`sccache`/`strix-build`/ROCm with no container mounts (mirrors `act_runner`'s host mode). `WOODPECKER_MAX_WORKFLOWS=1` = exactly one workflow at a time → never two heavy Rust compiles concurrently → no cgroup OOM. The agent unit sets `MemoryHigh=36G/MemoryMax=40G` to override the host's blanket 4 G user-service cap so a single build fits.

---

## Operational commands

```bash
# lifecycle
systemctl --user restart woodpecker-server woodpecker-agent
systemctl --user status woodpecker-agent
journalctl --user -fu woodpecker-server          # logs

# health / version
curl -sf -o /dev/null -w '%{http_code}\n' http://localhost:8010/healthz   # 204 = ok
curl -sf http://localhost:8010/version

# ground-truth: registered agents (no token needed)
sqlite3 ~/.local/share/woodpecker/woodpecker.db 'select id,name,backend,capacity,version from agents'
```

---

## Telemetry → OpenObserve (wired 2026-06-16)

Woodpecker server metrics flow to OpenObserve: `WOODPECKER_PROMETHEUS_AUTH_TOKEN` in `server.env` unlocks `/metrics` (bearer-gated; 404 without it), and otel-collector has a `prometheus/woodpecker` scrape job (`127.0.0.1:8010`, bearer credentials) → `woodpecker_*` metric streams in OpenObserve (:5080). Edit the scrape in `~/.config/otel-collector/config.yaml` (backup `.bak-20260616`; restart `otel-collector` after — malformed YAML drops ALL telemetry incl. bifrost). gitea `act_runner` has no Prometheus surface; the gitea server can expose some via `ENABLE_METRICS` but it's thin — Woodpecker's metrics are the better CI signal.

## Forge wiring (gitea OAuth)

- gitea OAuth2 app **"Woodpecker CI"** (app id 4). Client/secret live in `~/.config/woodpecker/server.env`.
- **CRITICAL gotcha — use the tailscale IP, not localhost.** gitea runs under **pasta** networking, so `localhost` inside the gitea container ≠ the host. Both `WOODPECKER_HOST` and `WOODPECKER_GITEA_URL` are set to **`http://100.112.37.119:…`** so (a) the browser OAuth redirect resolves, (b) the woodpecker server reaches the gitea API, and (c) gitea webhooks reach woodpecker. If you ever see OAuth redirect mismatches or webhooks not firing, this is why.
- Admin user: `fabiantax` (`WOODPECKER_OPEN=false` — no open registration).
- Redirect URIs registered: `http://100.112.37.119:8010/authorize` and `http://localhost:8010/authorize`.

### First-time login + enabling a repo (interactive — requires a browser; Claude can't click OAuth)
1. Open **http://100.112.37.119:8010** → **Login** → authorize via gitea. First login as `fabiantax` ⇒ admin.
2. **Repositories → enable** the repo (e.g. GraphFusion). This installs the gitea webhook automatically.
3. (Optional) Generate a CLI token: UI → user menu → **CLI / API token**.

---

## woodpecker-cli (after you have a token)

```bash
export WOODPECKER_SERVER=http://100.112.37.119:8010
export WOODPECKER_TOKEN=<token from UI>
~/code/tools/woodpecker/woodpecker-cli info
~/code/tools/woodpecker/woodpecker-cli repo ls
~/code/tools/woodpecker/woodpecker-cli pipeline ls fabiantax/GraphFusion

# author pipelines safely WITHOUT a server/token:
woodpecker-cli lint .woodpecker.yml          # validate syntax
woodpecker-cli exec .woodpecker.yml          # run the pipeline locally (great for iterating)
```

---

## Authoring `.woodpecker.yml` (local backend specifics)

Lives at the repo root (or `.woodpecker/*.yml` for multiple workflows). With the **local backend**, steps run as host shell commands — **omit `image:`** (it's a container field); the host PATH/toolchain is available, so `strix-build`, `cargo`, `atlas`, etc. work directly.

```yaml
when:
  - event: [push, pull_request]

steps:
  - name: test-edge
    commands:
      - strix-build cargo nextest run -p graphfusion-edge   # strix-build keeps the build-mutex + 20G cap
  - name: smoke
    commands:
      - strix-build cargo run -p graphfusion-edge --example isochrone_bbox_probe
    depends_on: [test-edge]        # serialize; or omit for parallel (but MAX_WORKFLOWS=1 already serializes workflows)
```

Concurrency model: steps within a workflow run per `depends_on`; **workflows** are what the agent's `MAX_WORKFLOWS=1` serializes. To allow light steps to parallelize while still capping heavy compiles, split into multiple workflow files and/or raise `MAX_WORKFLOWS` — but the default cap-1 is the safe, OOM-proof choice on this box.

### Pipelines-as-TypeScript via Dagger (planned for GraphFusion)
Write pipeline logic in a typed **Dagger TS** program; Woodpecker just triggers `dagger call …`. This decouples pipeline logic from the scheduler (portable if the scheduler changes again) and is the "CI in TypeScript" answer, since no standalone TS CI server is mature.

---

## Remote build agents (offload heavy builds to another machine)

The **server** (control plane on strix) is separate from **agents** (where builds run). Add an agent on any machine to direct builds there — the recommended fix for strix RAM contention (heavy Rust compiles leave the 62 G shared box, freeing it for vLLM + agents).

- **No git repo needed** — an agent is just the `woodpecker-agent` binary + `agent.env` + a systemd --user unit.
- **Staged installer:** `~/code/tools/woodpecker/install-woodpecker-agent.sh` (on strix). Copy to the new box and run (tailscale must be up so it reaches `100.112.37.119:9010`; secret from strix `~/.config/woodpecker/server.env`):
  ```bash
  WP_AGENT_SECRET=<secret> WP_LABEL=host=buildbox WP_BACKEND=local WP_MAX=2 \
    bash install-woodpecker-agent.sh
  ```
  It checks reachability, enables linger (headless), downloads the matching agent, writes env+unit, registers.
- **Routing by label:** the agent advertises `WOODPECKER_AGENT_LABELS="host=buildbox"` (plus auto `platform`/`hostname`/`backend`). A workflow selects an agent via a top-level `labels:` map:
  ```yaml
  labels: { host: buildbox }   # this workflow runs ONLY on the build server
  ```
  Omit → any agent. So send heavy compiles to `buildbox`, keep lint/light on strix (run agents on both).
- **Backend:** `local` (reuse strix-build/cargo/sccache — box needs the toolchain installed) or `docker`/`podman` (steps in a build image — reproducible, no host drift). A dedicated box can run a higher `WP_MAX`.
- **Shared sccache:** point both machines' sccache at the local **garage S3** (`SCCACHE_BUCKET` on :3900) so they warm each other's cache.
- **gitea Actions equivalent:** register `act_runner` on the box with a label, then `runs-on: buildbox`.
- **Verify (on strix):** `sqlite3 ~/.local/share/woodpecker/woodpecker.db 'select id,name,backend,capacity from agents'` → a second row named for the box.

## Gotchas (cost hours to rediscover)

1. **tailscale IP, not localhost** for `WOODPECKER_HOST`/`WOODPECKER_GITEA_URL` (pasta networking — see above).
2. **Agent config path** — default `/etc/woodpecker/agent.conf` isn't writable as a user, so the agent re-registers (orphan rows) every restart. Fixed via `WOODPECKER_AGENT_CONFIG_FILE=~/.local/share/woodpecker/agent.conf` in `agent.env`.
3. **Port 8000 is vLLM** — Woodpecker server is on **8010** (HTTP) / **9010** (gRPC) to avoid the inference stack (8000/8002–8006), sqld (8080), bifrost (3003), gitea (3200), garage (3900).
4. **Local backend needs the toolchain on PATH** — it runs on the host, so whatever the systemd unit's environment exposes is what pipelines get. Heavy builds should call `strix-build` to stay under the build mutex.
5. **`act_runner` restart orphans in-flight jobs** (a gitea-Actions pain) — Woodpecker's agent unregisters cleanly on stop; prefer `systemctl --user restart woodpecker-agent` over killing it.

---

## Coexistence / rollback
Woodpecker is additive — gitea Actions (`act-runner.service` on `strix-host`, currently capacity 1) still runs all existing `.gitea/workflows/*`. To retire Woodpecker: `systemctl --user disable --now woodpecker-server woodpecker-agent`, delete the gitea OAuth app (id 4), and remove `~/.config/woodpecker` + `~/.local/share/woodpecker`. Nothing in GraphFusion depends on it until a `.woodpecker.yml` is committed and the repo is enabled.
