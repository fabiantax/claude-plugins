---
name: fab-agent-runtime
description: Work on the fab-agent-runtime A2A agent mesh — build, test, deploy agents, manage the mesh (reflection, routing, grounding, blackboard, registry), and clear the Gitea issue backlog.
argument-hint: "[command or issue number] — e.g. '#100', 'build', 'test reflection', 'deploy graphfusion-cto', 'status', 'backlog'"
---

# fab-agent-runtime — Declarative A2A Agent Mesh

## When to Use
- Working on any issue in the `fabiantax/fab-agent-runtime` Gitea repo
- Building, testing, or deploying the runtime or individual agents
- Adding new agent YAMLs, personas, or skills
- Debugging mesh features: reflection, routing, grounding, blackboard, registry
- Managing systemd services for mesh agents
- Running the test suite or fixing flaky tests

## Repo Location

`~/Developer/personal/fab-agent-runtime`

## Gitea

| What | Value |
|------|-------|
| Repo | `http://localhost:3200/fabiantax/fab-agent-runtime` |
| Issues | 3 open: #143 (DevLake DORA), #144 (secrets manager), #44 (cross-host Mac verification) |
| Branch protection | `main` branch protected, force-push disabled, non-admin token enforced (#80) |

## Build & Test

```bash
cd ~/Developer/personal/fab-agent-runtime

# Typecheck (TypeScript 7 / tsgo)
npm run typecheck

# Build (output to dist/)
npm run build

# Unit tests (157+)
npm test

# Specific test file
npx vitest run src/__tests__/reflection.test.ts
# or with node test runner:
node --test src/__tests__/subprocess-idle-timeout.test.ts

# Build standalone binary
bun build --compile --target=bun-linux-x64 ./dist/bin/am-runtime.js --outfile fab-agent-runtime
```

## Architecture Overview

### Core Flow
1. `agent.yaml` declares agent name, port, skills, and handler types
2. `fab-agent-runtime serve agent.yaml` starts HTTP/3 + WebSocket server
3. Agent self-registers in sqld mesh registry (port 8080)
4. Incoming `message/send` or `message/stream` JSON-RPC calls dispatch to skills
5. SkillDispatcher routes to handler: `subprocess`, `mcp`, `http`, or `routed`

### Key Source Files

| File | Purpose |
|------|---------|
| `src/server.ts` | HTTP/3 + WS entry, `message/send` and `message/stream` JSON-RPC |
| `src/dispatcher.ts` | SkillDispatcher — routes calls, runs reflection, persists memories |
| `src/types.ts` | am-protocol wire types (TransportMessage, A2ATask, AgentSkill) |
| `src/client.ts` | A2AClient — outbound skill calls to other mesh peers |
| `src/agent-yaml.ts` | YAML parser — agent config schema with handler types |
| `src/reflection.ts` | Pre-response critic pass — calls mesh-reflector, parses verdict |
| `src/router.ts` | `handler.type: routed` — rules-based backend picker (length + pool) |
| `src/blackboard.ts` | Cross-agent knowledge blackboard backed by libSQL (sqld) |
| `src/mesh-registry.ts` | Peer registry backed by libSQL, with TTL stale detection |
| `src/prompt-context.ts` | Builds context prefix (registry + blackboard) for consults |
| `src/agent-memory.ts` | Per-agent persistent memory via sqld |
| `src/handlers/subprocess.ts` | Spawns CLI tools, captures JSON/NDJSON stdout, idle+total watchdogs |
| `src/handlers/mcp.ts` | Bridges to MCP server tools |
| `src/handlers/http.ts` | Proxies to HTTP endpoints |
| `src/telemetry.ts` | Per-iteration timing for consult subprocesses |
| `src/strip-code-fences.ts` | Strips ```json fences from LLM output (critic compliance fix) |

### Handler Types

| `handler.type` | Bridge | Use when |
|---|---|---|
| `mcp` | Calls a tool on a configured MCP server | Project ships an MCP server |
| `subprocess` | Spawns a command, captures JSON/NDJSON stdout | One-off skills, CLI tools |
| `http` | Proxies to an HTTP endpoint | Existing HTTP API |
| `routed` | Rules-based backend picker across pool | Load-balance between backends (e.g., mtp vs batched) |

### Subprocess Handler — Watchdog Timers

Two independent timers control subprocess lifecycle:

| Timer | Config | Purpose |
|-------|--------|---------|
| `idle_ms` | Required | Fires when subprocess emits nothing for N ms |
| `total_ms` | Optional | Hard wall-clock ceiling regardless of activity |
| `timeout_ms` | Legacy alias | Maps to `total_ms` when `total_ms` is unset |

The handler writes the full `TransportMessage` to stdin (#100) and parses stdout as NDJSON. When the subprocess exits without emitting a `type: "result"` event, it falls back to `parseStdout` which handles single JSON objects and arrays.

### Pi Shim (`~/.local/bin/pi-fab-agent-runtime`)

Wraps `pi -p --mode json` for agent consults. Key behaviors (#100):
- When stdin is piped (subprocess handler): reads TransportMessage, extracts prompt text, strips `{{text}}` from argv, pipes prompt to pi via stdin
- When stdin is a TTY (direct CLI use): falls through to `pi "$@"`
- Emits Claude-shape `result` NDJSON events from pi's `turn_end` output

### Pi Providers & Model Backends (read before adding/debugging any agent)

Consults run `pi` against an OpenAI-compatible backend chosen by `--provider`. Providers
are defined in `~/.pi/agent/models.json`; the global default lives in
`~/.pi/agent/settings.json` (currently `zai`/`glm-5.1` — a footgun: agents MUST set
`--provider local-mesh` explicitly, or they inherit the cloud default).

| `--provider` | Backend | Concurrency | ctx/slot | Use for |
|---|---|---|---|---|
| **`local-mesh`** | llama-server **:8003** (`--parallel 4 --cont-batching`) | 4 slots | `ctx ÷ 4` | **Mesh agents — the correct default.** Built for concurrent fan-out |
| `local` | llama-server **:8002** (`--parallel 1`, MTP coder) | 1 slot | full ctx | Single-stream coding ONLY — **NOT mesh agents** |
| `local-auto` | router **:8005** (MTP-when-idle / mesh-slot-when-busy) | mixed | — | Experimental smart router (may not be running) |
| `zai` | **api.z.ai cloud** (GLM; needs `ZAI_API_KEY` with balance) | n/a | n/a | Avoid for the local mesh — external dependency + billing |

**Context-per-slot rule (the #1 footgun):** a batched server splits its `--ctx-size`
across `--parallel` slots — `:8003` at `--ctx-size 32768 --parallel 4` gives only **8192
tokens/slot**. Agent prompts (persona + grounding + `--append-system-prompt` + project
CLAUDE.md context files) are often **15–20k tokens** → `400 ... exceeds the available
context size`. A heavy-prompt agent needs a slot ≥ its prompt size; e.g. size `:8003` to
`--ctx-size 131072 --parallel 4` for 32k/slot.

### A2A consult failure modes (diagnosed 2026-06-04)

A consult that "times out" at the `total_ms`/`timeout_ms` cap is almost never the network
— diagnose the **backend** first (`curl -sf :8003/health`, then a direct
`:8003/v1/chat/completions` test isolates backend-vs-agent; `ss -tnp | grep :8002` shows
leaked `pi` connections):

| Symptom | Root cause | Fix |
|---|---|---|
| Every consult hits the full cap; a fast 429 underneath | `--provider zai` + **Z.AI out of balance** → `429 code 1113 "Insufficient balance"`; pi **retries** to the cap | Switch to `local-mesh`, or recharge Z.AI |
| Consults hang, **GPU idle**, `/health` ok | `--provider local` = **:8002 single slot** under concurrency; orphaned `pi` procs from prior timeouts hold the slot; slot can wedge (`should_stop`/`cancel task` in log) | Use `local-mesh`; kill orphan `pi` PIDs on `:8002`; restart `:8002` if wedged (`startup llm/mtp`) |
| `400 ... exceeds available context size (8192 tokens)` | ctx-per-slot too small (see rule above) | Raise `:8003` `--ctx-size` (or lower `--parallel`) |

Repro for the balance case: `curl :8003/...` works; `curl api.z.ai/api/paas/v4/chat/completions -H "Authorization: Bearer $ZAI_API_KEY" -d '{"model":"glm-5.1",...}'` → `429 code 1113` in ~1s. Cross-ref **fab-agent-mesh #21** (consult should fail-fast on non-retryable 429/auth instead of retrying to the cap) and **#6** (timeout-value tuning).

### Multi-machine topology (strix + macbook) — agents are pinned per host

The mesh spans two machines with **different inference engines**, and an agent is **pinned to one machine** (not portable across both):

| Host | Engine | `local*` mapping in *that host's* `models.json` |
|---|---|---|
| **strix** (GPU, always-on) | **llama-server** (ROCm), :8002 / :8003 | `local`→:8002, `local-mesh`→:8003 (Qwen3.6-35B GGUF) |
| **macbook** (Apple Silicon) | **MLX / oMLX** (Metal), `127.0.0.1`-only | `local*` → the local MLX OpenAI endpoint (MLX-format model) |

Rules:
- **`~/.pi/agent/models.json` is per-machine — never sync it verbatim.** strix's llama-server ports + GGUF model ids are wrong on the macbook, and the macbook's MLX endpoint/model is wrong on strix.
- A **pinned** agent yaml may hardcode its host's `--provider` + `--model` (strix agents: `--provider local-mesh` + `--model Qwen3.6-35B-A3B-UD-Q4_K_M.gguf`). That yaml is **not** expected to run on the other host.
- Current agents are **strix-pinned** (the registry advertises them on `strix:502xx`). The macbook runs MLX locally for its own host-pinned agents; MLX is not exposed over Tailscale.
- The *only* case needing a cross-machine (remote) provider is if you deliberately want a macbook agent to use strix's GPU: point it at `http://100.112.37.119:8003/v1` (strix `:8003` binds `0.0.0.0` and is Tailscale-reachable). Otherwise keep everything host-local.

## Mesh Subsystems

### Reflection (Critic Loop)

`docs/mesh-reflection.md` — Every `consult` skill with `reflect: true` runs a pre-response critic pass:

1. Agent produces draft response
2. Draft + context sent to `mesh-reflector` (port 50281) via A2A `reflect` skill
3. Critic returns `{verdict: APPROVE|REVISE|ERROR, findings: [...], revised_draft?: "..."}`
4. APPROVE/ERROR → emit original draft
5. REVISE with `revised_draft` → emit revised draft
6. REVISE without `revised_draft` → re-run leaf handler with findings appended to persona

Events persisted to `reflection_events` table in sqld. No truncation cap since #100 (stdin delivery).

### Routing (Backend Pool)

`src/router.ts` — `handler.type: routed` with rules-based backend selection:
- Rules match on `args.length` (question length)
- `use` for direct backend choice, `pool` for in-flight load balancing
- `inFlight` map tracks concurrent calls per backend

### Grounding

Static knowledge files auto-derived from codebase and injected into agent personas:
- Generator: `scripts/generate-grounding.mjs` — scans repo, produces grounding docs
- CI workflow: regenerates on every push to main
- Agent YAML: wired via `--append-system-prompt` pointing to grounding files
- Confidence rule: all CEO/CTO personas say "I don't know" when <90% confident
- Staleness: agents signal when their knowledge may be outdated

### Blackboard

Cross-agent knowledge sharing via libSQL (sqld at `http://127.0.0.1:8080`):
- Append-only: status transitions are new INSERTs with `refs_id`
- Groups, tags, author attribution
- Used by digest, survey, and mesh-reflector

### Mesh Agents (systemd)

All agents run as systemd user services under `~/.config/systemd/user/`:

| Service | Port | Role |
|---------|------|------|
| `graphfusion-ceo` | 50210 | GraphFusion product/roadmap |
| `graphfusion-cto` | 50211 | GraphFusion technical design |
| `graphfusion-devops` | 50212 | GraphFusion deploy/monitoring |
| `atlas-ceo` | 50220 | Atlas product/roadmap |
| `atlas-cto` | 50221 | Atlas technical design |
| `atlas-agent` | 50222 | Atlas implementation engineer |
| `fab-swarm-ceo/cto` | 50250+ | fab-swarm roles |
| `localscout-ceo/cto/devops` | 50230+ | LocalScout roles |
| `mesh-reflector` | 50281 | Critic for reflection loop |
| `mesh-reviewer-bot` | 50282 | Autonomous PR reviewer |
| `mesh-ci-watcher` | 50295 | CI failure pattern diagnosis |
| `mesh-webhook-receiver` | 50299 | Gitea webhook → reviewer trigger |

OOM policy: `MemoryHigh=512M`, `MemoryMax=1G`, `OOMScoreAdjust=-100` (Gitea #9).

### Secrets

All tokens in `~/.config/fab-agent-runtime/secrets.env`:
- Per-agent Gitea tokens: `GITEA_TOKEN_<TEAM>_<ROLE>`
- Generic fallback: `GITEA_TOKEN` (non-admin `agent-mesh` user since #51)
- `ZAI_API_KEY` — only for the **`zai` cloud** provider (optional). The local mesh runs on `local-mesh` (:8003); if an agent uses `zai` and the account runs out of balance, every consult 429s and pi retries to the timeout (see "A2A consult failure modes"). Prefer local.

## Agent YAML Structure

```yaml
name: my-agent
description: Agent description
version: 0.0.1
host: 0.0.0.0
port: 50211
reflect: true          # enable pre-response critic (optional)
skills:
  - id: consult
    description: Ask the agent a question
    handler:
      type: subprocess
      exec: pi-fab-agent-runtime
      args:
        - -p
        - --mode
        - json
        - --provider
        - local-mesh                         # :8003 batched — NOT 'zai' (cloud) or 'local' (:8002 single-slot). See Pi Providers above.
        - --model
        - Qwen3.6-35B-A3B-UD-Q4_K_M.gguf
        - --no-session
        - --append-system-prompt
        - /path/to/persona.md
        - '{{text}}'
      timeout_ms: 180000
```

> Heavy-prompt agents (~15–20k tokens of persona + grounding + context files) need a slot ≥ their prompt size. With `:8003` at `--ctx-size 32768 --parallel 4` (8192/slot) they hit `400 ... exceeds available context size` — size `:8003` for ≥1 slot of ≥18k (e.g. `--ctx-size 131072 --parallel 4`).

## Scripts & Tools

| Script | Purpose |
|--------|---------|
| `scripts/generate-grounding.mjs` | Auto-derive agent knowledge from codebase |
| `scripts/mesh-daily-digest.ts` | End-of-day digest to blackboard (fires daily 21:00) |
| `scripts/mesh-weekly-survey.ts` | 3-round self-survey across agents (fires Sun 18:00) |
| `scripts/mesh-webhook-receiver.ts` | Gitea webhook → mesh-reviewer trigger |
| `scripts/provision-mesh-bot.sh` | Create Gitea bot users + tokens |
| `scripts/mesh-restart.sh` / `mesh-kill.sh` | Bulk agent lifecycle |

## Test Patterns

### Subprocess Timeout Tests

Located in `src/__tests__/subprocess-idle-timeout.test.ts`. Key pattern: the test asserts ONLY the watchdog contract (the timer fires and rejects), not the count of pre-timeout events. Under CI load, Node cold-start can delay first output past the timer — that's fine, the contract is "timer kills the subprocess."

### Reflection Tests

Located in `src/__tests__/reflection.test.ts`. The mock A2A client returns a canned JSON verdict. Tests verify APPROVE/REVISE/ERROR paths and that full drafts pass through without truncation.

### LibSQL Tests

Some tests fail with `URL_SCHEME_NOT_SUPPORTED: got "file:"` when sqld is down — pre-existing, unrelated to most changes. Tests use `:memory:` when possible.

## Common Workflows

### Deploy an Updated Agent

```bash
cd ~/Developer/personal/fab-agent-runtime
npm run build
systemctl --user restart <agent-service>
```

### Add a New Agent

1. Create persona `.md` file in target project's `.claude/agents/`
2. Create `demo/<agent-name>.yaml` following the YAML structure above
3. Create systemd service file (copy from existing, change port + YAML path)
4. `systemctl --user daemon-reload && systemctl --user start <service>`
5. Verify: `curl -sf http://127.0.0.1:<port>/.well-known/agent.json | jq .`

### Verify Mesh Health

```bash
# Check all agent services
systemctl --user status '*-ceo*' '*-cto*' '*-devops*' '*-agent*' '*-reflector*' '*-reviewer*' '*-watcher*'

# Check registry
fab-agent-runtime registry list

# Check blackboard
fab-agent-runtime blackboard read

# Test a consult
NODE_TLS_REJECT_UNAUTHORIZED=0 fab-agent-runtime call https://127.0.0.1:50211 consult "What is GraphFusion?"

# If a consult hangs to the timeout, diagnose the BACKEND before anything else:
grep -A2 -- '--provider' <agent>.yaml          # which backend? (want local-mesh, not zai/local)
curl -sf http://127.0.0.1:8003/health          # is the batched server up?
ss -tnp | grep ':8002'                          # leaked pi connections on the single-slot server?
# Direct backend test (isolates backend-vs-agent):
curl -sS http://127.0.0.1:8003/v1/chat/completions -H 'content-type: application/json' \
  -d '{"model":"Qwen3.6-35B-A3B-UD-Q4_K_M.gguf","messages":[{"role":"user","content":"ok"}],"max_tokens":8}'
```

## Open Issues (as of 2026-06-04)

| # | Title | Scope | Status |
|---|-------|-------|--------|
| 143 | Deploy Apache DevLake + Gitea plugin for DORA metrics | Large | Open |
| 144 | Migrate agent secrets from flat secrets.env to secrets manager | Medium | Open |
| 44 | Cross-host mesh verification (Mac + strix) | Runtime | Deferred — needs Mac runner |

## Completed Milestones

- **Mesh foundation**: Registry, blackboard, A2A protocol, streaming (#4-#8, #14, #17-#18, #26, #36-#37, #40-#43)
- **Security hardening**: Non-admin tokens, branch protection (#51, #80)
- **Reflection system**: Critic loop, re-run path, stdin delivery (#53, #77, #89, #93, #100)
- **PR review**: mesh-reviewer-bot, webhook, timeout fix (#59, #108, #114)
- **Grounding**: Generator, CI workflow, wiring, confidence, staleness (#137-#141)
- **Mesh ops**: CI-watcher, daily digest, weekly survey, durable opinions (#62-#65)
- **Test reliability**: Flaky subprocess timeout fix (#72)
