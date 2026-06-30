---
name: mesh-health
description: Diagnose the A2A mesh's inference path in one shot — live backends, per-agent exec adapter + timeout audit, dead-port references, local-load activity, and OpenObserve reachability. Use when the mesh seems idle/broken, consults fail or time out, local-GPU utilization is unexpectedly low, or before/after changing mesh routing.
---

# Mesh health

One command instead of fifteen reactive probes. Encodes the playbook derived the hard
way (2026-06-30): the two failure modes that actually bite are **a dead inference port**
and **a too-tight subprocess timeout**, and both hide in plain text in the configs.

## The one command

```bash
mesh-health-probe          # human summary + verdict
mesh-health-probe --json   # structured, for piping / an agent
```
Read-only. Source: `strix-inference/host-config/bin/mesh-health-probe` (symlinked to
`~/.local/bin`). For a reasoning deep-dive + fixes, dispatch the **`mesh-doctor`** agent.

## What it checks (and why each matters)

1. **Live backends** — zai-shim :4099, bifrost :3003, **llama-router :8005** (the
   local-qwen chokepoint), llama-swap :8007, gemma :8004. A consult can only land if these are up.
2. **Per-agent adapter + timeout audit** — for every `~/.mesh/brains/*/agents/*.yaml`:
   its `exec:` adapter, the inference backend that implies, and `timeout_ms`. **Flags
   `timeout_ms < 120000`** — a 35B consult (≤4096 tok @ ~30–50 tg/s) plus prompt-eval and
   GPU-queue contention routinely exceeds 60s; the runtime's own default is 180000.
3. **Dead-port references** — scans `mesh-consult`, `pi-fab-agent-runtime`, and the agent
   yamls for the **decommissioned :8002/:8003** llama-server ports (replaced by llama-swap
   :8007 / router :8005). A consult firing at :8003 silently fails → the mesh looks "idle."
4. **Local-load activity** — `strix_router_routed_total{coder,mesh}` + bifrost `local-qwen`
   count. Is the mesh actually driving local inference, or flat?
5. **OpenObserve reachability** — the 3 distinct logins (see the credential map below);
   `:401` means a stale cred (the cto-hq scanner / mesh trace export silently failing).

## The two classic failure modes → fixes

| Symptom (probe verdict) | Cause | Fix |
|---|---|---|
| consult returns nothing / mesh "idle"; dead-port ref flagged | adapter posts to dead :8003 | repoint to the live router: `mesh-consult` `MESH_LLM_PORT` default → `8005` (it rewrites the model + is the OO chokepoint) |
| `subprocess '…' exceeded 60000ms`; tight-timeout flagged | `timeout_ms` too low for a 35B under load | `sed -i -E 's/timeout_ms:\s*[0-9]+/timeout_ms: 180000/'` the agent yaml, **restart that agent** to reload |
| backend down | service crashed/hung | `systemctl --user restart llama-router` (or llama-swap); the self-heal responder also covers this |
| OO `:401` | stale credential | use the right login from the map; for the mesh trace acct, the user must **exist** in the mac OO |

After editing a `~/.mesh/brains/*/agents/*.yaml`, **restart that agent** (`systemctl --user
restart <agent>`) — fab-agent-runtime reads the yaml at startup.

## OpenObserve credential map (3 distinct logins)

| instance | who uses it | login |
|---|---|---|
| strix `:5080` | otel exports Bifrost+router metrics | `root@example.com:StrixObserve2026` |
| mac `100.109.245.96:5080` | cto-hq scanner reads; mesh exports traces | `admin@local.dev:admin123456` (root) |
| mac (service acct) | the mesh units' `OPENOBSERVE_AUTH` | `fabian@raaf.local:raaf2026` (must exist as an OO user) |

(CLAUDE.md's `admin@local.dev:MtpObserve2026!` is **stale** — 401.)

## Driving a consult (to test / activate)

```bash
NODE_TLS_REJECT_UNAUTHORIZED=0 fab-agent-runtime call https://strix:50221 consult "question"
# ports: atlas-cto 50221 · atlas-ceo 50220 · fab-swarm-cto 50271 · fab-swarm-ceo 50270 …
# registry: SELECT name,url FROM agents  (sqld :8080)
```
Solo consult ≈ 30s. Concurrency queues through np=2 mesh + np=1 coder ≈ 3 slots.

## Method (the meta-lesson)

When debugging an unfamiliar multi-hop system: **read the path in parallel before poking
the surface.** Trace one request end-to-end through the source (endpoint → runtime →
adapter → backend → metric) and the bugs are visible in the config before any live test.
