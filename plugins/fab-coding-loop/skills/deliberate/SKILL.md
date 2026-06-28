---
name: deliberate
description: Run a multi-party cross-repo decision over the fab-agent-runtime A2A mesh — fan a question out to the relevant agents (Atlas/GraphFusion/Localscout/fab-swarm CTOs/CEOs etc.), let them post and rebut positions in a shared team channel, then converge to a ranked decision recorded on the blackboard and filed as Gitea issues. Use when agents need to discuss priority, request features across repos, or make a joint technical/product decision.
allowed-tools: Read Bash
---

# deliberate — cross-repo A2A decision-making

Drives a **multi-party deliberation** across the live A2A mesh. It supplies the one piece the
runtime lacks (driving members to contribute + a rebuttal round) and reuses everything else the
mesh already provides.

## What the mesh already gives you (don't rebuild)

| Primitive | Role in deliberation |
|---|---|
| `fab-agent-runtime team form --members a,b,c --convener x --duration` | shared deliberation channel (libSQL `teams`) |
| `team append <id> --author --repo <obs>` | a member posts a position; **all members can read all positions** |
| `team read <id>` | the chronological shared channel |
| `team dissolve <id>` / `team sweep` | **convergence**: spawns `claude --agent <convener> --model sonnet` over the whole channel → **outcome → blackboard** (group `ceo`, tag `team-<id>`) + `<<<STORY>>>` blocks → **auto-filed Gitea issues** (needs `GITEA_TOKEN`) |
| `reflection` (mesh-reflector :50281) | pre-response critic on each consult (APPROVE/REVISE/re-run) — grounding |
| `patterns` | reflection REVISE findings stored + re-injected into persona next consult — built-in online learning |

## The loop (what deliberate.sh adds)

1. **Select members** — `--role cto` (via `registry find`) or explicit `--members a,b,c`; optional `--repos` filter.
2. **Form team** — `team form` with members + convener (default: first member; override for a neutral CEO).
3. **Ground** (`ground.py`) — assemble ONE neutral cross-repo fact-sheet (gitea open issues + recent git commits for every repo in the deliberation, topic-keyword-flagged ⭐, bounded) and inject it into every consult. This is the **activator-injects-grounding** model (Option A): the lean agents have no repo/gitea access, so the facts they reason over must arrive in the question. Without it, atlas/localscout-cto correctly but uselessly reply "I don't have that in my consult context".
4. **Round 1 — positions** (parallel `consult` → `team append`): each agent answers the OUTPUT CONTRACT (STANCE / GROUNDING / IMPACT / PRIORITY / COMMITMENTS-ASKS).
5. **Round 2 — rebuttal** (parallel): each agent re-consulted *with all peers' positions visible*, gives final priority + peer alignment + commitments. (Skip with `--rounds 1`.)
6. **Converge** — `team dissolve` → convener synthesizes → ranked outcome on blackboard + Gitea issues.

### Lean, pi-less consults (`mesh-consult`)

Each `consult` is handled by `~/.local/bin/mesh-consult` → the batched **llama-server on :8003** (one 35B, 4 slots). pi (the interactive coding agent) was removed from every CEO/CTO handler: a mesh consult is "persona + grounded question → opinion", not a tool-using session. mesh-consult renders the persona `.md` as the system prompt, runs `enable_thinking:false`, and **strips** the dispatcher's generic `<peer_registry>`/`<recent_blackboard>`/`<recent_memory>` blocks (the real grounding now arrives in the question). Those generic blocks + 28-agent registry are what overflowed the **8192-tokens/slot** budget and produced empty consults (localscout#11) — stripping them is what fixed it.

### GEPA analyze-first (`gepa/`)

The activation itself is measurable. `gepa/score_activation.py` scores a deliberation trace on 5 dims (participation / grounding / convergence / actionability / efficiency); `gepa/analyze_activation.py` feeds the seed procedure (`gepa/procedure.md`) + trace + scores to GEPA's reflection LM (:8003) for a diagnosis + improved procedure. Proven loop (2026-06-04, converged to **1.000**): baseline 0.970 → reflection diagnosed the proactive-opener efficiency leak → OUTPUT CONTRACT (0.985) → persona-opener gating (1.000). Both mutations accepted. Run: `python3 gepa/analyze_activation.py --trace <trace> --out <report>`.

## Usage

```bash
SK=~/.claude/skills/deliberate/deliberate.sh

# All CTOs deliberate a cross-repo priority call
"$SK" --topic "Should GraphFusion prioritize per-profile CCH metric export for Localscout v7 routing?" --role cto

# Explicit members + neutral convener
"$SK" --topic "Adopt typed-triple extraction (ReLiK) across the stack?" \
      --members graphfusion-cto,atlas-cto,localscout-cto --convener graphfusion-ceo

# Scope to two repos, one round
"$SK" --topic "..." --role cto --repos GraphFusion,localscout --rounds 1

# Safe trials:
"$SK" --topic "..." --role cto --dry-run    # positions + rebuttal, NO synthesis, NO Gitea (team left active)
"$SK" --topic "..." --role cto --no-gitea   # synthesize to blackboard, file NO Gitea issues
```

Prints the team id, the full channel, and (unless dry-run) the synthesized outcome + filed issues.
Read the outcome later: `fab-agent-runtime blackboard read --group ceo --tag team-<id>`.

## Preconditions

- Agents running (`systemctl --user list-units | grep -E 'ceo|cto'`), sqld up (:8080), `claude` on PATH (for `team dissolve` synthesis).
- **Batched llama-server on :8003** up (`startup llm/batched`) — every consult goes here via `mesh-consult`. `curl -sf http://127.0.0.1:8003/health`.
- **`LIBSQL_URL=http://127.0.0.1:8080`** — the script exports it; without it `team form` dies with `URL_SCHEME_NOT_SUPPORTED` (falls back to an unsupported `file:` URL).
- `GITEA_TOKEN` set — needed both for grounding (gitea issue fetch in `ground.py`) and issue auto-filing (else use `--no-gitea`).
- Self-signed TLS handled (`NODE_TLS_REJECT_UNAUTHORIZED=0`, set by the script).

## Gotchas

- **Consults are fast now** (lean `mesh-consult` → :8003, ~2–20s each, no pi tool loop) — rounds still run members in parallel; `CONSULT_TIMEOUT_MS` defaults to 180000.
- **The 8192-tokens/slot budget is hard** (32768 ctx ÷ 4 slots on :8003). `ground.py` caps the fact-sheet (10 issues, 6 commits, truncation) and `mesh-consult` strips the dispatcher prefix to stay under it. If you widen grounding, watch for empty consults = overflow.
- **Single consults are unreliable** (cross-verify against repo/Gitea). The injected grounding mitigates this; for high-stakes calls, spot-check the cited issues/PRs before acting on the decision.
- The convener must be a real agent with a persona (`claude --agent <name>`); default = first member.
- `--dry-run` leaves the team active — dissolve manually or it auto-expires after `--duration` (default 2h) and gets swept.

## Driver model & roadmap

- **Now (Phase 1):** Claude Code (or a human) invokes this script; the mesh's `team dissolve` does convergence. This is the *staged* approach.
- **Later (Phase 2 — autonomous):** promote this loop into `am-ceo serve` / a runtime handler so any peer can request a deliberation over A2A without a human driver.
- **Optimization (Phase 3 — GEPA):** done analyze-first — `gepa/` scores each activation and reflects on the **activation procedure** (`gepa/procedure.md`: grounding + round prompts), not the mesh internals. Three accepted mutations: 0.970 → 0.985 (OUTPUT CONTRACT) → 1.000 (persona-opener gating) → STANCE/PRIORITY de-dup (clarity fix). **Multi-topic validation (`gepa/validate_topics.sh`, 4 diverse topics incl. a 3-party run on agents never in the loop): mean 0.953, min 0.880, max 1.000.** Participation/grounding/efficiency pinned at 1.0 on every topic — the procedure generalizes to unseen agents/team-sizes; the single-topic 1.000 was a lucky clean-priority run, not representative. Convergence is the only variable dim (0.65–1.0) and SHOULD be — it tracks genuine priority agreement, which legitimately varies run-to-run; **do not optimize it toward a fixed 1.0** (forcing agreement games the metric — genuine disagreement is signal). Validation is complete; the procedure holds. A future `gepa.optimize_anything` loop (using `score_activation.score` as evaluator) would be the autonomous form, but is not needed for quality. **Run GEPA as a scheduled batch job, NOT a per-message hook** (it needs many rollouts). See the gepa skill.
