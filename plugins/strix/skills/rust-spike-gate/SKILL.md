---
name: rust-spike-gate
description: Measurement-gated Rust feature work on strix — scratch spike before any crates/ change, blind subagent write + driver gate sequence, real-artifact gate reproduction. Use when planning a perf-sensitive feature, building a measurement spike or bench harness, posting a design/M-gate on an issue, or running driver gates (clippy/nextest/live boot A/B) for staymatch-style repos.
---

# rust-spike-gate

Field-tested workflow from staymatch#152 (mmap-first POI sidecar, merged as #229)
and staymatch#220 (duplicate collapse, #228). Plan → measure → then code, with
the driver as the only commit/gate authority.

## When to use

- A perf- or correctness-sensitive feature where the design must be **measured
  before it touches `crates/`** (the repo's plan-then-code ruling).
- Building a scratch bench/spike against a real dataset.
- Acting as the **driver** for a blind-writer subagent implementation.
- Reproducing a feature's gates on real artifacts before merge.

## Procedure

1. **Recon + design on-thread, before code.** Read the issue ACs + last sweep
   comment, read the actual serving/ingest path, then post the design as an
   issue comment: numbered decisions (D1…), non-goals, and an explicit
   **spike gate** — the table the implementation must later reproduce. No
   `crates/` change before that table exists.
2. **Spike in a scratch crate OUTSIDE the repo**
   (`/mnt/models/scratch/claude-tmp/opencode/<name>/`), minimal deps
   (`memmap2`, `libc`, `csv`; xorshift for randomness — no `rand`), with a
   `gen` (build artifact) and `bench` (measure) subcommand.
3. **Bit-exact data export.** Never trust float print/parse through CSV. If
   the source data feeds a quantised key (morton, geohash…), have duckdb
   export the quantised integers directly
   (`CAST(floor((v - lo) / span * 4294967296.0) AS UBIGINT)`) and interleave
   in the spike. Add two self-checks: (a) parity — reproduced keys must be
   non-decreasing along the stored row order; (b) round-trip — quantise over
   the parsed f64 must equal the exported integer.
4. **Measure honest populations.** Per-class percentiles (per radius/query
   size), not just a mixed p99; cold runs via `posix_fadvise(DONTNEED)`; RSS
   from `/proc/self/status`; print **hits + a checksum + scanned/query +
   dir-comparisons/query** so an empty or wrong query is visible.
5. **Let measurement amend the design.** A falsified design point is the
   spike working (e.g. #152: fixed top-bits directory was degenerate →
   two-level min-cover; 48 B stride → 56 B). Update the on-thread design,
   then freeze surviving constants as production constants.
6. **Post the M-gate table on-thread** (correctness evidence first, then the
   measured table vs targets). This is the baseline the implementation PR
   must reproduce.
7. **Dispatch the blind writer** (`rust-coder`) with: exact format/layout
   spec (offsets, constants), the measured gate numbers to reproduce, tests
   that fail-on-revert, required ADR/doc edits, and "no build, no commit".
   Point it at the spike source as reference.
8. **Driver fixes mechanics inline; never re-dispatch.** Budget 1–2 rounds
   (one session: 13 compile errors + 2 clippy rounds in blind-written code).
   Then gates, in order:
   - `strix-build cargo clippy --workspace --all-targets -- -D warnings`
   - `strix-build cargo nextest run --workspace` (quote "N tests run: N passed")
   - `strix-build cargo test --doc --workspace` (nextest skips doctests)
9. **Gate reproduction on real artifacts.** Rebuild the real thing with the
   new flag; boot the real server on loopback + an ephemeral port; A/B the
   mode switch (poll `/health` for time-to-ready, VmHWM from `/proc`);
   diff `/match` outputs across modes for parity; feed a stale/corrupt
   artifact and require the loud fallback. For staymatch bundle+sidx builds
   this is now scripted: `scripts/bundle-v2/sidx-gate.sh` (self-tested,
   see `sidx-gate.test.sh`).
10. **PR → all CI lanes green → squash-merge → close-out comment with the
    evidence table → sync main → prune worktree + branch.**

## Pitfalls

- **Float print/parse drift**: printed-f64 → quantise produced 16,394 phantom
  parity violations on 1.29 M rows. Fix: export quantised u32s from the query
  engine (step 3). Sanity: 98.7%-correct order means a drift bug, not a wrong
  algorithm; 0-violations means parity.
- **Empty-query trap**: spectacular latencies with `hits=0` are measuring
  nothing (one session: a directory read missing its header offset searched
  garbage). Any bench that reports hits/scanned must show nonzero hits, and a
  `dbg` dump of the first table entries against known magic bytes localises
  offset bugs in seconds.
- **Binary-search cost dominates when leaves are too fine**: 7,276 dir
  comparisons/query at depth 20 → 115 with depth-17 windows. Measure the
  comparison breakdown, not just wall time.
- **Fixed-prefix directories are degenerate for clustered data** — print the
  depth table (cells/max-per-cell per depth) first; exact-duplicate
  coordinates set a floor no scheme can split.
- **strix-build gives each worktree a private target dir** (`cargo-target-<slug>`):
  fresh binaries are NOT in `/mnt/models/cargo-target/release`. Check the
  build verdict line or `ls /mnt/models/cargo-target-*/release`.
- **Shared target-dir locks**: another session's cargo build blocks yours
  ("Blocking waiting for file lock", invisible under `| grep`). Sidestep for
  scratch crates: `CARGO_TARGET_DIR=./target cargo build --release --offline`.
- **`pkill -f "staymatch --config"` kills your own shell** (the pattern
  matches your script's cmdline). Use `pkill -x staymatch`.
- **Ports on strix**: 8093 routed-th, 8094 tt-preview, 8095 staymatch dev,
  8096 journey-api, 8098/8198 staymatch-cloud instances, 8099 gf-poi. Bench
  on an ephemeral port (e.g. 18443) and curl it *before* trusting any health
  read — a stale server answering makes you measure the wrong process.
- **Backgrounded `a && b &` chains put var assignments in a subshell** (the
  foreground never sees them); set vars on separate lines. Killing a
  systemd-run/`time` wrapper can orphan the child holding a lock — clean up
  with `pkill -x` and re-check the port.
- **Minimal server configs**: staymatch's TOML requires a `providers` table
  (an empty `[providers]` parses fine); `feed_path` is dead code — the
  loader only reads `feed_dir` + `countries`.

## Verification

- Spike: `morton_parity 0 violations`, `quantise_mismatches 0`, hits > 0,
  identical hits/checksum across directory configurations.
- Gates: quote `clippy … exit 0`, `N tests run: N passed` (could-fail proof:
  they failed earlier in the session and pass only on the final tree),
  doctests exit 0.
- Live gate: `/health` shows the new mode key; the A/B table prints per-leg
  ready-time + VmHWM; stale artifact → loud fallback line in the log + healthy
  degraded mode; `/match` parity IDENTICAL across modes
  (`scripts/bundle-v2/sidx-gate.sh all` prints PASS lines for each).
- Evidence posted on the tracker issue before merge; commit + push only from
  the driver context.
