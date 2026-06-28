---
name: loop-improvement
description: Loop Improvement Cycle
---

# Loop Improvement Cycle

Structured cycle for iteratively improving trading strategy performance. Each cycle follows a strict protocol to prevent overfitting and ensure genuine alpha discovery.

## Cycle Protocol

```
1. HYPOTHESIS  — "Adding X will improve [metric] by >[threshold] on holdout"
2. GATE        — Check prerequisites (model quality, data availability, no garbage models)
3. IMPLEMENT   — ONE change only. No bundles.
4. ABLATION    — Test feature ON vs OFF on dev data. No feature ships without ablation.
5. HOLDOUT     — Validate on untouched holdout. Must beat previous best on Sharpe AND return.
6. DECIDE      — Pass → git tag, update baseline. Fail → revert, record why in memory.
7. RESEARCH    — SOTA research ONLY when genuinely stuck or encountering new domain.
```

## Rules

- **One change per cycle.** Never bundle features. If you add 5 things at once, you don't know which worked.
- **Ablation is mandatory.** Every new feature must be tested ON vs OFF before it ships.
- **Holdout is sacred.** Never optimize on holdout data. Holdout is for validation only.
- **Record failures.** Failed hypotheses are as valuable as successes. Write them to memory.
- **No IS-only results.** IS metrics are meaningless without OOS validation.

## Baseline tracking

Current baseline must be recorded in memory before each cycle. Format:

```
Baseline: return +X%, Sharpe Y.YY, MDD Z.Z%, Calmar W.WW, N trades
Source: [config name] on [holdout period]
```

If a cycle fails, baseline stays unchanged. If it passes, baseline updates.

## Hypothesis template

```
Hypothesis: Adding [FEATURE] will improve [METRIC] by >[THRESHOLD] on holdout.
Prerequisites: [what must be true before implementing]
Risk: [what could go wrong]
Ablation plan: [how to test ON vs OFF]
Acceptance: [exact pass/fail criteria]
```

## Failure recording

When a cycle fails, save to memory:
```
Cycle N: [FEATURE] — FAILED
Hypothesis: [what we expected]
Result: [what actually happened]
Why: [root cause analysis]
Lesson: [what we learned]
```

## When to use

Invoke this skill when:
- Starting a new improvement iteration
- The user says "continue the loop" or "next cycle"
- After a competition or parameter sweep, to validate findings with ablation

## Model quality gate

Before any cycle that uses a model:
1. Check tree count (must be > 50)
2. Check metrics (AUC/accuracy must be > 0)
3. Check feature count vs sample count (max 1:20 ratio)
4. If model is garbage, the cycle is BLOCKED until retraining
