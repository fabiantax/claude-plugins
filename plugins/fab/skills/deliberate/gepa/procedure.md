# Mesh-activation procedure (current best candidate)

This is the procedure Claude (the activator) uses to run a cross-repo deliberation
over the A2A mesh. GEPA evolves THIS text; the deliberation trace it produces is
scored by score_activation.py (participation / grounding / convergence /
actionability / efficiency).

> GEPA loop, 2026-06-04 (converged to 1.000):
> - v1 seed (open-ended round prompts): **0.970** — efficiency 0.70, 2 proactive-opener leaks.
> - v2 + OUTPUT CONTRACT (§3/§4): **0.985** — efficiency 0.85, 1 leak. ACCEPTED (all other dims held).
> - v3 + persona gating: **1.000** — efficiency 1.00, 0 leaks. ACCEPTED. The residual leak
>   came from the personas' "You lead **every** conversation with: <opener>" instruction; gated
>   to fire only on proactive openings (not when answering a question / OUTPUT CONTRACT) in
>   graphfusion-cto/ceo(+divergent) and localscout-ceo(+divergent) `.md`.
> Both proposed mutations accepted under GEPA's accept-if-improved rule. A scorer false-negative
> (actionability undercounted third-person commitment phrasing) was caught at v2 and fixed in
> score_activation.py's is_actionable() before judging — the reflection surfaced the metric gap.
>
> MULTI-TOPIC VALIDATION (overfitting check, 2026-06-04, gepa/validate_topics.sh — 4 diverse
> topics: baseline feature-priority, CONTENTIOUS gate-vs-velocity, 3-party standardization,
> intra-roadmap tradeoff): **mean total 0.953, min 0.880, max 1.000**.
>   - participation / grounding / efficiency = **1.0 on ALL 4 topics**, including a 3-party
>     deliberation driven by atlas-cto + fab-swarm-cto — agents NEVER in the optimization loop.
>     The two mutations generalize to unseen agents and team sizes (0 opener leaks, 0 empties,
>     full artifact-grounded contract compliance everywhere). The single-topic 1.000 was a lucky
>     clean-priority run, NOT representative — but the procedure itself is robust.
>   - convergence is the only variable dim (0.65–1.0), and it SHOULD be: it measures genuine
>     priority agreement, which legitimately varies run-to-run (the same baseline topic scored
>     0.65 one run, 1.00 on re-run). Do NOT chase it toward a fixed 1.0 — forcing priority
>     agreement games the metric and destroys the deliberation's value (genuine disagreement is
>     signal). The CONTENTIOUS and 3-party topics scored convergence 1.0 because those agents
>     happened to take crisply aligned stances, not because they were "easy".
> - v4 + STANCE/PRIORITY de-dup (§4): the R2 contract stated priority in TWO places (STANCE line
>   `[Maintain/Revise] P[0-3]` AND the PRIORITY field). One run an agent wrote `STANCE: Revise P2`
>   but `PRIORITY: P1` — a self-contradiction the scorer (reads first P-token) misread as
>   non-convergence. Fix: STANCE is now prose-only (`[Maintain/Revise] — <why>`); priority is
>   stated ONCE in the PRIORITY field. Verified mechanically: post-fix R2 STANCE lines carry zero
>   P-numbers, so convergence now reflects ONLY real PRIORITY-field spread. This is a clarity fix,
>   NOT a score-chase — it removes a spurious convergence-killer while preserving genuine splits
>   (a real P0-vs-P2 baseline disagreement still scores ~0.65 as it should).

## 1. Grounding (ground.py)
Before any round, assemble ONE neutral cross-repo fact-sheet and inject it into
every consult. Sources per repo: gitea open issues (state=open, type=issues) and
recent non-merge git commits. Issues/commits whose text matches the topic's
keywords are flagged ⭐ and sorted first. Capped (10 issues, 6 commits, titles
truncated) so persona + fact-sheet + question stay under the 8192-tokens/slot
budget of the :8003 batched server. Facts only — no stance, no priority.

## 2. Lean handler (mesh-consult)
Each agent answers via `mesh-consult` → :8003 (one 35B model, 4 slots). It renders
the agent's persona .md as the system prompt and the consult question as the user
turn. `enable_thinking` is OFF. It STRIPS the dispatcher's generic
<peer_registry>/<recent_blackboard>/<recent_memory> blocks (the real grounding now
arrives in the question). No tools — the agent reasons over injected facts.

## 3. Round 1 prompt (parallel, one per member) — OUTPUT CONTRACT
"""
DELIBERATION (team {id}). Topic: {topic}

{grounding fact-sheet}

Reply from your repo/role's perspective using EXACTLY these fields. NO intro, NO
rhetorical questions, NO generic openers, NO timestamps.
STANCE: [your repo's stance in one line]
GROUNDING: [cite 1-3 real artifacts from the facts above — issue #N or commit hash — that bear on your repo]
IMPACT: [1-2 sentences: concrete impact on your repo]
PRIORITY: [P0/P1/P2/P3] — [one-line justification]
COMMITMENTS/ASKS: [bullet list of concrete next-steps you commit to and what you need from the other repos]
"""

## 4. Round 2 prompt (parallel, peers' R1 positions visible) — OUTPUT CONTRACT
"""
DELIBERATION (team {id}). Topic: {topic}

{grounding fact-sheet}

PEER POSITIONS so far:
{digest of R1 positions}

Reply using EXACTLY these fields. NO intro, NO rhetorical questions, NO generic
openers, NO timestamps.
STANCE: [Maintain/Revise] — [one line: did your position change after seeing peers, and why]
GROUNDING: [cite the real artifacts — issue #N or commit hash — supporting your final stance]
PEER ALIGNMENT: [where you AGREE / DISAGREE and with whom, and why]
IMPACT: [1-2 sentences: updated impact on your repo]
PRIORITY: [P0/P1/P2/P3] — [one-line justification]   (state the priority ONCE, here only — do not put a P-number on the STANCE line)
COMMITMENTS/ASKS: [bullet list of FINAL concrete commitments and what you need from the other repos]
"""

## 5. Convergence
Dissolve the team → convener synthesizes the channel into an outcome (blackboard)
plus `<<<STORY>>>` blocks auto-filed as gitea issues.
