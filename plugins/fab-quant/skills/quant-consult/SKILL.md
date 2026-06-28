---
name: quant-consult
description: Convene an advisory board of independent quant specialists (parallel subagents) before any capital-adjacent decision — alpha attribution, risk, execution, overfitting, regime. Surfaces benchmark-relative truth and dissent, not consensus.
argument-hint: "[the decision in question, e.g. \"wire gamma to live paper capital\" or \"raise max_concurrent from 6 to 16\"]"
---

# /quant-consult — independent quant advisory board

**Decision under review**: `$ARGUMENTS`

Convene a board of **independent** specialists before committing to a capital-adjacent
or strategy-validating decision. Each seat is a separate subagent with its own lens,
its own skepticism mandate, and no sight of the others' answers. **Dissent is the
deliverable** — a unanimous board usually means the question was too easy or the seats
anchored on your framing. Surface the split, do not average it away.

## Why this exists

The +8.52% YTD "gamma edge" sat unchallenged for months because a single perspective
treated it as given and asked "how do we capture it" instead of "is there an edge vs the
benchmark." It was beta (SPY did +9.28% over the same window). No benchmark was recorded
alongside the return, so nothing looked wrong. This board exists so that the **Alpha
Attribution** seat demands a benchmark, the **Overfitting** seat demands OOS, and the
**Execution** seat prices the backtest→live gap — *before* the decision is made, every
time. The failure mode is a single mind reasoning itself into a framing; independence is
the fix.

## The five seats

Spawn all five **in parallel** (one message, five `Agent` calls) so no seat anchors on
another. Each gets: the decision, its mandate, the repo facts it must verify against, and
a structured return (see below).

### Seat 1 — Alpha Attribution & Benchmarking
- **Mandate:** Is the return/edge *real* or beta? Decompose into beta / alpha / sizing.
  **Refuse to accept any P&L or return figure that has no benchmark beside it.** Compute
  gamma-return vs SPY **and** vs the traded-universe equal-weight buy-and-hold over the
  *same window*. Alpha < 0 = not an edge, no matter the headline number.
- **Challenges:** "8.52% sounds fine — what did the index do?" / "Is this the market's
  move wearing a strategy costume?" / "Forward window or backtest? Don't let a backtest
  number justify a live decision."
- **Primary sources:** `data/paper/gamma-order-history.jsonl` (daily gamma_equity),
  `data/ohlcv/SPY/1D.parquet` (note: raw `time` is epoch **seconds**), universe manifest
  in `data/universe/`, saved runs in `data/experiments/` (`bh_return`, `total_return`).
- **subagent_type:** `quant-reviewer`

### Seat 2 — Risk, Sizing & Concentration
- **Mandate:** Is the book survivable? Tail risk, drawdown path, concentration. Look at
  *how few* names and trades carry the return — if 6 names / 14 trades / one +6.3% day
  produced the whole number, the "edge" is a small-sample lottery ticket, not a process.
  Check `max_concurrent`, `cross_sectional_top_n`, leverage, vol-targeting.
- **Challenges:** "How many trades is this really?" / "What's the MDD path, not just the
  number?" / "If the one big day had landed red, what's the return?" / "1× leverage only —
  is even that justified before alpha is shown?"
- **Primary sources:** order-history per-day `n_entries/n_exits/gamma_book`, config
  defaults in `crates/nt-backtest/src/gamma/config.rs` (`max_concurrent:6`,
  `cross_sectional_top_n:5`), risk metrics in saved runs (`max_dd`, `cvar95`, `calmar`).
- **subagent_type:** `quant-reviewer`

### Seat 3 — Execution & Backtest→Live Gap
- **Mandate:** Is the edge *executable* as measured? Slippage, fill assumptions, the gap
  between backtest P&L and what a real broker returns. The measured −5.55pp paper-execution
  gap (lever A, initial-only stop) is the standing number — but flag that fixing execution
  is *moot* until alpha is proven.
- **Challenges:** "Backtest fills at what assumption?" / "What does the paper sim actually
  execute vs the signal?" / "Capacity — does this survive size, or is it a 60-name micro-book
  artifact?" / "Is the stop policy costing more than it saves?"
- **Primary sources:** `apps/engine/src/plugins/order-plan-executor.ts`, `gamma-replay.ts`
  (the 5-policy StopPolicy harness), `simulated-broker.ts` (the `getCash()` constant
  gotcha), `order-plan-pipeline.test.ts`.
- **subagent_type:** `general-purpose`

### Seat 4 — Overfitting & OOS Validity
- **Mandate:** Is the edge real or curve-fit? **IS-only numbers are meaningless.** Demand
  walk-forward OOS, IS/OOS degradation ratio (>0.3), deflated Sharpe, multiple-comparison
  correction across all the config sweeps in `data/experiments/`. A backtest that returned
  +5396% over 6.2 years but +8.52% forward is a regime/overfit smell, not a flex.
- **Challenges:** "How many configs were tried to get this one?" / "OOS degradation?" /
  "Is the forward window just one benign bull regime?" / "Deflated Sharpe after all the
  sweeps?"
- **Primary sources:** `data/experiments/gamma-run/` (sweep history — count the configs),
  OOS/bear-validation memories, `crates/nt-backtest/tests/aapl_full_benchmark.rs`
  (CSCV/degradation harness).
- **subagent_type:** `overfitting-diagnostician`

### Seat 5 — Regime & Macro
- **Mandate:** Does this hold across regimes, or is it a single-regime artifact? The
  forward window (Jan–Jun 2026) is one benign bull slice. Classify the regime; ask whether
  the strategy is long beta in a bull market and nothing more. What breaks in a transition
  or bear?
- **Challenges:** "Is this just long-beta in a bull tape?" / "Bear-validated?" / "What's
  the macro tailwind doing to this number?" / "Regime shift → does the book go flat or
  invert?"
- **Primary sources:** intermarket ratios / TSI regime classification
  (`packages/regime`), bear-OOS validation memory, `gamma_paper_run` regime flags.
- **subagent_type:** `regime-analyst`

## Dispatch

```
Spawn seats 1–5 in ONE message (five Agent tool calls) — genuinely concurrent.
Each agent prompt = decision + that seat's mandate + its primary sources + the
return contract below. Tell each: "You are an independent advisor. Be adversarial.
Your value is finding the reason NOT to do this. Ground every claim in repo data;
cite file:line or a computed number. Do not defer to the framing."
```

**Model tier:** these are expensive-if-wrong reasoning seats → default to the heavy
tier (Opus). De-escalate only under explicit budget pressure.

**Return contract (every seat must answer):**
1. **Verdict:** PROCEED / HOLD / BLOCK (one word + one sentence).
2. **Confidence:** low / medium / high.
3. **The one assumption** in the decision this seat most disputes.
4. **The single number or check** that, if different, would flip the verdict.
5. **Pre-mortem:** if this decision loses money in 6 months, what was the cause (from
   this seat's lens)?

## Synthesis (the driver's job — do NOT let agents do this)

1. **Collect** all five returns. **Read them, don't trust summaries** — verify each
   cites real data.
2. **Consensus:** list where ≥4 seats agree. That's the load-bearing signal.
3. **Dissent:** surface every split explicitly — name the seat, its verdict, its reason.
   A single BLOCK from any seat on its home turf (e.g. Alpha Attribution with no
   benchmark) is enough to halt, regardless of the others.
4. **Recommendation:** state the decision and the conditions attached (e.g. "PROCEED
   only after Seat 1 computes forward alpha vs SPY and it's positive"). Never average
   away a strong dissent into a soft "mostly yes."
5. **Record:** if the decision proceeds, write the board's verdict + dissent to
   `.loopit/<slug>/adr.md` (or a fresh quant-consult log) so the reasoning survives.

## Hard rules (apply to every consult)

- **No benchmark, no claim.** Any return/P&L number must sit beside a benchmark over the
  *identical* window. The Alpha Attribution seat enforces this; if it can't find a
  benchmark, the verdict is BLOCK until one is computed.
- **Forward ≠ backtest.** A backtest number (+5396% replay) never justifies a live
  decision. Only the forward, out-of-sample slice counts.
- **OOS or it didn't happen.** IS metrics are reported *with* OOS, or labeled
  "NOT YET OOS VALIDATED."
- **Count the trades.** A return built on 14 trades and 6 names is a small-sample
  observation, not a validated process.
- **Dissent beats consensus.** If you catch yourself writing "the board broadly agrees,"
  stop and check whether you silenced a seat. Re-run that seat sharper.

## When NOT to use this

- Pure plumbing/infra with no strategy or capital implication (the timer wiring, a lint
  fix). Save the board's cost for decisions where being wrong loses money or masks a
  non-edge.
- A decision you've already consulted on this turn — don't re-convene for a trivial
  follow-up.
