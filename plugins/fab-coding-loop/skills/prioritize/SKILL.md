---
name: prioritize
description: Score and rank a list of items using RICE, WSJF, CoD, ROI, and Kano frameworks. Output a single prioritized table.
---

# Prioritize

Score a raw backlog using multiple prioritization frameworks and produce a single ranked output.

## Input

The user provides:
- A list of items (features, tasks, refactor targets, anything)
- Optionally: constraints (deadline, team size, budget)
- Optionally: which framework to emphasize (default: composite of all)

If items are vague, ask clarifying questions BEFORE scoring. Better to score 5 well-defined items than 20 half-baked ones.

## Frameworks

### RICE (Reach × Impact × Confidence / Effort)

| Factor | Scale | Notes |
|--------|-------|-------|
| Reach | Number of users/sessions affected per quarter | 1–10K+ or use raw count |
| Impact | 3=massive, 2=high, 1=medium, 0.5=low, 0.25=minimal | Per-user impact |
| Confidence | 100%=high, 80%=medium, 50%=low | How sure are we about R and I |
| Effort | Agent-hours (or t-shirt: XS=1h, S=2h, M=4h, L=12h, XL=24h+) | Lower = better |

Score = (Reach × Impact × Confidence) / Effort

**Effort default: agent-hours, not human-days.** When work is executed by AI coding agents (Claude Code, sub-agents, parallel workers) the bottleneck is *clarification + verification*, not typing. Reference codebases (HuggingFace, official repos, vendored crates) collapse what would be a multi-day human task into a single focused agent session. Calibrate against actual agent runs in the project, not abstract human-week estimates.

Calibration anchors:
- XS (≤1h): wire up a known config; one-file edit; cleanup; commit + push
- S (2-3h): add a feature to existing code path; new test suite; small refactor
- M (4-8h): build a new module from a reference impl; multi-file feature; data pipeline addition
- L (10-16h): port a paper-quality model end-to-end with bench; major subsystem
- XL (24h+): genuinely new architecture across multiple crates/packages

If the user is *not* using AI agents, fall back to person-months (1 person-month ≈ 160 person-hours ≈ 13 agent-hours for typical CRUD-heavy work). Ask if it's not obvious.

### WSJF (Weighted Shortest Job First — SAFe)

| Factor | Scale |
|--------|-------|
| User-Business Value | 1–10 (revenue, user delight, strategic) |
| Time Criticality | 1–10 (deadline, market window, penalty for delay) |
| Risk Reduction / Opportunity Enablement | 1–10 (unblocks others, removes risk) |
| Job Size | 1–10 (effort, lower = smaller job) |

Score = (UBV + TC + RROE) / Job Size

### CoD (Cost of Delay)

Estimate the value lost per unit time if NOT doing this item.

CoD = UBV + TC + RROE (same sub-scores as WSJF numerator)

Then: CoD / Duration = priority. Same formula as WSJF but forces explicit "what does delay cost?" thinking.

### ROI

Score = (Estimated value generated) / (Estimated cost to implement)

Value can be: revenue, time saved × engineer count, bugs prevented × cost-per-bug, etc.
Cost = engineering time × fully-loaded cost.

### Kano (numeric score)

Classify each item, then read off its **numeric Kano score** (0–1) — Kano is a
first-class number in the composite, not just a label.

| Type | Meaning | Kano score | Priority implication |
|------|---------|:---:|---------------------|
| Must-have | Table stakes — absence causes dissatisfaction | **1.0** | Do first (mandatory) |
| Performance | More = better, linear value | **0.7** | Prioritize by RICE/WSJF |
| Delight | Unexpected — absence is fine, presence delights | **0.4** | Strategic — schedule for impact |
| Indifferent | Nobody cares | **0.1** | Drop or defer |
| Reverse | Implementing it makes things worse | **0.0** | Don't do |

The category→score map above is the **default** (use it when you only have a
classification). When you have Kano **survey data** (a functional + dysfunctional
question per item → counts of **A**ttractive / **O**ne-dimensional / **M**ust-be /
**I**ndifferent responses), compute the coefficients and use them as the numeric
score instead:

- **Satisfaction coefficient** `CS+ = (A + O) / (A + O + M + I)` — how much *presence* satisfies (0…1).
- **Dissatisfaction coefficient** `CS- = (O + M) / (A + O + M + I)` — how much *absence* dissatisfies (0…1; conventionally written negative).
- **Kano score** `= 0.5 × CS+ + 0.5 × CS-` — a single 0–1 number blending upside and table-stakes pressure. Must-be items score high via `CS-`; delighters via `CS+`; indifferents fall near 0.

Always surface the **number** (with the category in parens) in the output table, e.g. `1.0 (Must)`.

## Process

1. **Clarify** — If items are ambiguous, ask the user to define what each item IS and what "done" looks like. Max 3 clarifying questions, then proceed with best estimates.

2. **Estimate factors** — For each item, estimate all factors across all frameworks. Use a compact table. If data is missing, use the Confidence factor in RICE to downweight uncertain items.

3. **Compute scores** — Calculate RICE, WSJF, CoD, and ROI for each item. Classify each item via Kano and record its numeric Kano score (0–1).

4. **Composite rank** — Normalize each framework's scores to [0, 1], then compute:
   ```
   composite = 0.3 × WSJF_norm + 0.25 × RICE_norm + 0.2 × CoD_norm + 0.15 × ROI_norm + 0.1 × Kano_score
   ```
   Where `Kano_score` is the 0–1 numeric value from the Kano table above (category default, or the survey-derived `0.5·CS+ + 0.5·CS-`). It is already on a 0–1 scale, so no separate normalization is needed.

5. **Output** — Single sorted table:

```
## Priority Ranking

| # | Item | Kano | RICE | WSJF | CoD/yr | ROI | Composite | Next step |
|---|------|------|------|------|--------|-----|-----------|-----------|
| 1 | ...  | 1.0 (Must) | 840  | 12.5 | $50K   | 5x  | 0.92      | Start now |
| 2 | ...  | 0.7 (Perf) | 420  | 8.3  | $30K   | 3x  | 0.71      | Wave 2    |
```

6. **Wave assignment** — Group ranked items into execution waves:
   - Wave 1: Composite ≥ 0.7 (do now)
   - Wave 2: Composite 0.4–0.69 (do next)
   - Wave 3: Composite < 0.4 (backlog)

7. **Brief rationale** — 1-2 sentences on WHY the top 3 items ranked highest and any surprising results.

## Rules

- All estimates are quick — this is a triage tool, not a thesis. 30 seconds per item max.
- If the user says "just use RICE" or similar, drop the other frameworks and only compute that one.
- Don't ask permission to proceed — score, rank, present. The user can adjust.
- Numbers beat feelings. If two items score similarly, flag the tie for the user to break.
- Output the full scoring table even if the user only asked to "prioritize this list" — transparency matters.
- **Effort estimates assume AI-agent execution by default.** If the work will be human-only, ask once and switch to person-days/months. Do not silently mix the two scales — it inflates the effort axis and demotes high-leverage items that an agent can ship in hours (e.g., porting a reference model from a public repo, sweeping a config grid, extracting a documented factor set).
- For agent-built items, the binding constraints are usually (a) data availability, (b) schema/contract clarity at boundaries, (c) verification cost — *not* keystrokes. Score Effort against those, not against "how long would I take to type this."
