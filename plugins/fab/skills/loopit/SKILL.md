---
name: loopit
description: Draft a /loop prompt for a goal, persist findings + decisions across iterations, optionally execute now.
argument-hint: "[goal description, e.g. \"harden the e2e suite against alphabetical-order races\"]"
---

# /loopit — drive an iterative goal with persistent learning

**Goal**: $ARGUMENTS

### Resolving the goal

1. If `$ARGUMENTS` is non-empty → that's the goal.
2. If `$ARGUMENTS` is empty → look back over the last few assistant turns in this conversation for a **prioritised list, ranked recommendations, or a "TL;DR / next steps" block** that the assistant just proposed. Common shapes:
   - "P0 / P1 / P2 ranked …", "Low-hanging fruit ranked …", "Next, do X then Y then Z", checklists or numbered tables.
   - The user saying "yes do it" / "ok let's start" / "let's start with the low-hanging fruit" / "create a loop for these" right after such a list is the strongest signal.
   Treat that list as the **initial seed** and synthesise a one-sentence goal that summarises it. Confirm the goal and seed back to the user *before* writing any files: "I'll seed the loop with these N items from the prior turn — confirm?"
3. If neither — ask the user to state the goal in one sentence. Don't guess.

## What this command does (compared to a raw `/loop`)

- Persists **findings** between iterations in a scratchpad — each cold-start iteration starts with what previous iterations learned, instead of re-discovering it.
- Records **decisions** in an ADR file — when a non-trivial choice is made (A vs B vs C), the rationale survives long enough for a PR reviewer or a future-you to read.
- Is **re-entrant**: invoking `/loopit` again with the same goal slug picks up the existing scratchpad and continues. Idempotent.
- **Explicit convergence signal**: the items checklist shrinks, the findings stream slows; when both stabilise, the loop stops.

## Workflow

### Step 1 — derive the slug

Take the goal, kebab-case it, cap at 40 chars (keep the most distinctive words). Examples:
- "harden the e2e suite against alphabetical-order races" → `e2e-alpha-order-races`
- "implement EMS-333 P1 scenarios" → `ems-333-p1`

### Step 2 — set up state files

Two files under `.loopit/<slug>/`:

- `scratchpad.md` — the shared brain across iterations.
- `adr.md` — append-only decision log.

If they already exist (re-entrant invocation), **read them first** and continue. Don't overwrite.

#### `scratchpad.md` shape

```markdown
# Loopit — <goal one-liner>

## Status
- Started: <YYYY-MM-DD HH:MM>
- Last iteration: <YYYY-MM-DD HH:MM>
- Stop condition: <one-line, observable>

## Items
- [ ] <item-id>: <imperative, one outcome each> — PASS: <observable gate> / FAIL: <observable condition>
- [x] <done-item>: <result> (iteration <N>, <YYYY-MM-DD>)

## Findings (newest at top, max 20 retained)
- <YYYY-MM-DD HH:MM> [iter N]: <one-line learning that the next iteration must know>

## Blockers (open)
- <blocker> — <what's needed to unblock>

## Recent runs (5 max, newest first)
- <YYYY-MM-DD HH:MM> [iter N]: <items closed>; <items deferred>; <findings added: count>
```

#### `adr.md` shape

```markdown
# ADR log — <goal one-liner>

## ADR-NNN — <decision title>
- **Date**: YYYY-MM-DD HH:MM
- **Iteration**: N
- **Status**: Accepted | Superseded by ADR-MMM
- **Context**: 1-3 sentences — what made the choice necessary
- **Alternatives considered**:
  - A: <option> — pro / con
  - B: <option> — pro / con
- **Decision**: <chosen option>
- **Why**: 1-2 sentences
- **Consequences**: what this commits future iterations to
```

### Step 3 — draft the `/loop` prompt

The prompt is a single self-contained block the model fires each turn. Build it from these sections:

```
/loop <one-line goal restatement>. Read .loopit/<slug>/scratchpad.md and .loopit/<slug>/adr.md before doing anything; they are the load-bearing memory across iterations. Each iteration:

1. Read both files cold.
2. Pick the first unchecked item in scratchpad. If none remain, run the diagnostic pass: <project-specific git grep / file scan / test re-run that surfaces new items, OR a single line "no items, propose convergence">.
3. Apply the change.
4. Verify with: <one concrete command — e.g. `dotnet build && pwsh ./scripts/web.e2e/headless.ps1 -Filter <X>`>. Quality gate must be green.
5. If a non-trivial choice was made (>=2 viable options, one chosen), append an ADR entry to .loopit/<slug>/adr.md with date, alternatives, decision, why, consequences.
6. Append a finding to scratchpad if anything was surprising or non-obvious — newest at top, prune at 20 entries.
7. Mark the item done with iteration number + date; update Status block.
8. Commit per item by default with subject "<short-prefix>: <item summary>". Skip the commit if the change is trivial scratchpad edits.

INVARIANTS (do NOT violate):
- <invariant 1 — quality gate, e.g. "tests must remain green; revert on red">
- <invariant 2 — scope, e.g. "no work outside the items list; new items go in via the diagnostic pass, not ad-hoc edits">
- <invariant 3 — safety, e.g. "do not push to shared branches; do not modify other worktrees' processes">
- <invariant N>

CONVERGENCE: stop when (a) all items checked AND (b) the diagnostic pass produces zero new items AND (c) the verification command is green for two consecutive iterations.

INITIAL SEED: <bullet list of starting items — must give iteration #1 something concrete to do>
```

### Step 4 — execution mode

**Always execute unless the user says "draft only".** Do not ask — just start running.

In **execute** mode:

#### Per-iteration cycle

1. Read scratchpad + ADR.
2. Pick the first unchecked item.
3. **Pre-flight gate**: before writing code or running a target command, enumerate the full required-input surface (config keys, abstract methods, env vars, CLI flags). Delegate to an `Explore` agent if the surface spans >1 file or >300 lines total. **Do not guess.** The pre-flight output replaces the "discover one missing key, fail, repeat" anti-pattern with one informed execution.
4. Mark the item `in progress` with iteration N and timestamp.
5. **Delegate the work.** Two execution engines — pick by item shape:
   - **Single-shape item** (one investigation, one edit, one command) → spawn a specialized `Task()` agent: `Explore` for research, `Plan` for architecture, project-specific agents from `.claude/agents/` for domain issues, `general-purpose` only when no specialist fits.
   - **Multi-stage / fan-out item** (understand→implement→verify, N-file sweep, find→verify, needs a compile/test repair loop) → author a **dynamic `Workflow`** for that iteration (see "Dynamic workflow execution" below). The workflow IS the iteration's engine; loopit stays the outer driver.
   - **Independent multi-file items** → split into 2-3 focused coder agents running in parallel (e.g. A=dataloader, B=rollout, C=adapter), each with an isolated file scope. All complete in ~1 wall-clock round instead of N sequential rounds.
6. **Run verification** (tests, build, e2e) — or fold it into the workflow's Verify phase.
7. **Evaluate the pass/fail gate** defined in the item. If the item said "PASS: ≥1 edit proposed", then "0 edits proposed" is a FAIL even if no crash occurred. Log the outcome explicitly.
8. **Cycle report** — after each item, report to the user:
   - What completed (item ID, result, commit hash)
   - What needs more work (blockers, failed tests, unexpected findings)
   - What's next (next unchecked item)
9. Update scratchpad (findings, item status, recent runs).
10. Commit per item.

#### Item creation gates (mandatory at seed time)

Every item added to the scratchpad — whether in the initial seed or discovered by a diagnostic pass — **must** carry an observable pass/fail gate:

- **PASS**: concrete, measurable outcome (e.g. "test X runs green", "grep -c 'bug' returns 0", "artifact contains ≥1 non-boilerplate edit").
- **FAIL**: the negation or a specific error signal.
- **"Exists" is not a gate.** "Config file exists" fails to distinguish between an empty template and a correct config. If you can't define a meaningful pass/fail, the item is too vague — split or sharpen it.
- **Optimization items take *two* gates, not one** — a hard correctness gate plus a soft metric objective. See *Optimization-shaped items* below.

Format in scratchpad:
```markdown
- [ ] L4: Run end-to-end training — PASS: epoch completes with loss < 1.0 / FAIL: epoch crashes or loss diverges
```

#### Optimization-shaped items (metric-maximizing, not binary)

Most items have a binary gate (test green / `grep` returns 0). Some instead have an
**objective to maximize or minimize** — throughput, latency, perplexity, bundle size, a
benchmark score. These take a different shape. (Source: ComPilot, PACT 2025 — a closed
loop with grounded *measured* feedback + best-of-N turned an off-the-shelf model into a
specialist: 2.66× single-run, 3.54× best-of-5, competitive with a SOTA hand-built
optimizer. arXiv 2511.00592.)

**Two-channel gating — a hard correctness gate UNDER a soft objective.** An optimization
item carries *two* gates, not one:

- **Hard gate (correctness / legality)** — binary, must hold: the change is still valid
  (tests green, type-checks, transform is legal, output numerically equivalent). A variant
  that fails this is discarded outright, *regardless of its score*.
- **Soft objective (the measured metric)** — the number to improve, read from a **real
  measurement** (benchmark, profiler, byte count) — never the model's self-estimate.

Never collapse the two into one gate: a loop that optimizes only the metric will "improve"
into a faster-but-broken state. The hard gate is the floor; the objective is the climb.

```markdown
- [ ] OPT-3: Tile the matmul loop nest — HARD: `cargo nextest` green (output numerically identical) / SOFT: maximize GFLOP/s (baseline 41.2, target >50)
```

**Best-of-N — sample in parallel, keep the best survivor.** One sequential chain
under-explores an optimization objective. Instead:

1. Spawn **N independent attempts from the *same* start state** in parallel — *divergent
   sampling* (different strategies), not iterative refinement of one. Reuse the
   Parallel-execution machinery (below); N≈3–5 (the best-of-5 sweet spot — cap N,
   diminishing returns past ~5).
2. Each attempt verifies *itself* against the hard gate and reports its objective score —
   but treat that self-reported number as a **filter, not a ranking**. Parallel attempts run
   under different contention, so their self-timings routinely mis-rank (observed in testing:
   the self-reported *fastest* attempt placed *last* under fair measurement).
3. **Discard every attempt that fails the hard gate.** Then **re-measure all survivors
   yourself, back-to-back in one run** (same conditions; on a shared GPU, under `gpu-bench`)
   and **select the single best by *your* measurement** — never the attempts' self-reports.
   If none survive, the item FAILs — log it; do not ship a broken "winner".
4. **Commit only the winner** (preserves one-commit-per-item). Record `N`, the per-attempt
   scores, and the winner in the scratchpad so a cold iteration sees the *search*, not just
   the result.

```markdown
- <ts> [iter N]: OPT-3 best-of-4 → scores [48.1, 51.9✓, 44.0, 50.2]; 1 failed hard gate (NaN); committed 51.9 GFLOP/s (abc1234)
```

**Cost discipline.** N attempts cost ≈N× the tokens/GPU of one. The payoff scales with **how
much attempt quality actually varies**: a wide, multi-strategy objective benefits most; a task
with one obvious win (low variance) barely beats best-of-1, so the N× spend is wasted there
(observed in testing: 4 attempts on a single-obvious-fix kernel landed within ~3% of each other).
Reserve best-of-N for **high-value items with a genuinely broad solution space** — not binary
items (a test passes or it doesn't) and not low-variance edits. Same cheap-by-default ethos as
the autonomy envelope above.

#### Delegation rules for Reads and research

- **Reading >300 lines of any file** → delegate to an `Explore` agent, even if it's "just recon". The main context window is scarce; burning it on a 1000-line Read leaves no room for reasoning about what was read.
- **Reading 3+ files to understand a surface** → delegate to an `Explore` agent with a scoped question ("what are all required config keys?"), not inline catenation.
- **Reading <300 lines of a single file** → inline read is acceptable.

#### Delegation rules for documentation edits

- **Documentation deliverables are subagent work, never inline.** Any write to `documentation/`, `docs/`, `README*`, plan/reference/research docs, or skill/agent docs is delegated to a subagent (Sonnet for well-specified writes; Opus when the doc requires synthesis across many sources). The loop driver supplies the outline, the facts to include (with file:line / evidence pointers), and the destination path; the subagent drafts, writes, and opens the PR.
- **Why**: inline doc authoring burns the driver's context on prose generation and skips review; a subagent gets a focused prompt, and the driver reviews the result like any other deliverable.
- **Exemption**: `.loopit/<slug>/scratchpad.md` and `adr.md` are the loop's own working memory — the driver edits those inline by design. Tiny mechanical doc fixes (one-line link/typo) may also be inline.

#### ADR capture threshold

ADR entries are cheap; re-litigating a forgotten decision is expensive. Write an ADR when:

- You weighed ≥2 viable options for >2 minutes (wall-clock or token reasoning).
- You chose between libraries, patterns, naming conventions, or architectural splits.
- A prior iteration's finding forced a change in approach.

If in doubt, write the ADR. A 5-line ADR is better than a 5-minute re-discovery next session.

#### Dynamic workflow execution (per-iteration engine)

`/loopit` and the `Workflow` tool are complementary, not redundant:

| Concern | Owner |
|---------|-------|
| Cross-iteration memory (scratchpad + ADR), convergence, Gitea sync | **loopit** (the outer loop) — persists *between* iterations |
| Deterministic fan-out / verify / repair *within* one iteration | **Workflow** (the inner engine) — stateless, returns a result |

When an iteration's item is multi-stage or fans out, author a Workflow instead of hand-spawning Tasks. The loop body becomes:

1. Read scratchpad + ADR; pick the item.
2. `Workflow({ script })` whose phases mirror the item — e.g. `Understand` (parallel readers → file:line map) → `Implement` (coders, parallel where files don't overlap, then an integrate stage) → `Verify` (a `while (!green && round<N)` compile/test **repair loop**).
3. The workflow runs in the background and notifies on completion; **read its returned result object** (not just trust it), then update the scratchpad/ADR and Gitea from that result.
4. Convergence/looping stays loopit's job — one workflow == one iteration's work.

**What to push DOWN into the workflow** (deterministic, no cross-iteration memory needed): the repair loop, parallel file edits, fan-out verification, find→adversarially-verify. **What stays UP in loopit** (needs memory/judgement): which item next, ADR decisions, convergence call, commit-per-item, Gitea issue state.

**Constraints still apply inside workflow agents** — bake project rules into the shared prompt prefix: build-mutex wrappers (e.g. `strix-build`), worktree path, "no git commit/push" (loopit owns commits at step 10, after reading the result), production-quality/no-stubs, test-manifest conventions. Pass the worktree path explicitly so every agent writes to the same isolated tree.

**Don't** use a workflow for a trivial one-file edit (a single `Task()` or inline edit is lighter), and **don't** let the workflow commit — loopit commits per item once the returned result is verified, preserving the one-commit-per-item invariant.

#### Agent monitoring rules

- **Never say "still writing" passively.** If a background agent hasn't completed in 60 seconds, check its output. If stalled (>2 min without progress), kill and restart with a clearer prompt.
- **Split large agent tasks.** If an agent's scope covers 3+ distinct topics, split into 2-3 agents running in parallel instead of one monolithic agent.
- **Verify agent output.** After an agent completes, read the actual files it wrote — don't just trust its summary.
- **Chain agents for dependent work.** If item B depends on item A's output, run A first, then spawn B with A's results in the prompt.
- **Ignore stale signals.** A backgrounded agent that spawned detached jobs (builds, test reruns, verifications) keeps emitting completion notifications long *after* its deliverable already landed/merged. Those are **stale echoes, not events** — don't burn a turn reacting to one, and never *wait* on one. A signal is stale if it concerns work already completed (cross-check the artifact: the PR is merged, the item is `[x]`). Acknowledge in one line at most and move on; if a finished agent's leftover jobs spam, note it and stop responding substantively.
- **Gate on the condition, not the clock.** When an action is blocked on an observable condition (load < N, CI green, a dependency merging, a file appearing), wait on *that condition* — arm a Monitor / background watcher that fires when it flips, or act on the real event when it arrives — rather than deferring a now-ready action to the next scheduled heartbeat/tick. Punting a satisfiable action to a timer *is* waiting on a stale signal: the timer tells you "15 minutes passed", not "the thing you were waiting for happened".

#### Parallel execution

When multiple items are independent (no blockedBy), execute them in parallel:
- Spawn one agent per item in a single message
- Use `run_in_background: true` for agents that don't block the next step
- Sync results after all parallel agents complete
- **Concrete pattern that works**: for a multi-file implementation item, split by file scope into 3 focused coder agents (e.g. A=dataloader+evaluator, B=rollout, C=adapter+train_patch), all running in parallel, each verifying independently.

#### Fill CI/verification waits — start other stories instead of idling

While an item's verification is in flight — a PR's CI running, a `nextest`/`cargo build` behind the strix-build mutex, a background `Workflow` mid-run, an e2e suite executing — that wall-clock is otherwise wasted. Do **not** sit idle polling it. Use the wait productively:

1. **Arm a watcher, then move on.** One background Monitor / `run_in_background` job fires when the in-flight item reaches a terminal state (CI green/red, build exit, workflow done). That's your "it's ready" signal — you do not poll for it.
2. **Immediately pick the next independent item** from the scratchpad (or the backlog if the scratchpad is drained) and **start it now** — not at the next heartbeat. CI-wait minutes are free throughput.
3. **Two hard rules for the item you start during a wait:**
   - It must be **independent** of the in-flight item (no shared files, no shared branch, no dependency on its result). Two agents editing the same file or stacking on the same PR defeats the point and risks a merge conflict.
   - It must be on its **own branch** (PR-only, never push main). A second PR open while the first's CI runs is fine and normal.
4. **Throttle to one concurrent build.** The strix-build mutex serializes builds anyway, but a second heavy `cargo` build queued behind the first just burns a slot — prefer CI-wait work that is *not* build-bound (docs, a small Rust change verifiable by `cargo check`, a Playwright spec, a BDD scenario, triaging an issue, writing an ADR, cross-verifying an A2A claim). If the only available work *is* build-bound, start it anyway — the mutex queues it and it runs the moment the first build frees up, so the wait still isn't idle.
5. **When the watcher fires**, finish the sentence you're on, then handle the terminal item (merge if green, repair if red) before continuing the wait-started item. Don't abandon the wait-started work — it's already mid-flight; just re-prioritize.
6. **Log it.** Note in the scratchpad's Recent runs that item B was started during item A's CI wait, so the next iteration (cold start) knows the two were concurrent, not sequential, and doesn't misread the timeline.

This is the positive complement to "Gate on the condition, not the clock" above: that rule says *don't* block on a timer for the thing you're waiting for; this one says *do* advance unrelated work while you wait for it.

#### Convergence report

When all items are checked, run a final diagnostic and report:

```
## Loopit Converged: <slug>

### Completed (N items)
- [x] Item 1: result (commit abc1234)
- [x] Item 2: result (commit def5678)

### Findings (top 5)
- Finding 1
- Finding 2

### Needs more work (for future loopits)
- Issue A: description
- Issue B: description

### Key commits
- abc1234 — summary
- def5678 — summary
```

## Autonomy, cadence & cost (the loop's operating envelope)

This skill is an adaptation of the **loop-engineering** model
(`cobusgreyling/loop-engineering`: 5 building blocks + memory — scheduling,
worktrees, skills, MCP connectors, sub-agents — a fixed loop anatomy, an
autonomy ladder, and token-cost discipline). Borrow that vocabulary so loops
are legible across sessions and agents.

Declare these in the scratchpad's `## Status` block up front:

- **Autonomy level** —
  - **L1 report-only**: observes and reports a proposed diff; never mutates. Start here for anything uncertain.
  - **L2 assisted**: commits/opens PRs behind a human gate or a checker's pass.
  - **L3 unattended**: runs on a timer, acts, self-alerts on failure. Earn L3; don't assume it.
- **Cadence + token cost** — for scheduled loops, how often it runs and how expensive a tick is. Default to **cheap-by-default**: the timer runs the cheap form (HTTP reachability, a grep, a `SELECT 1`); expensive LLM/GPU round-trips are an opt-in flag (`--deep`), never the default heartbeat. A timer that burns the GPU every tick is a bug.
- **Budget + run-log** — a rough token ceiling plus the `## Recent runs` tail, so cost is visible and a runaway loop is obvious. If you cap coverage (top-N, sampling, no-retry), say so in a Finding — silent truncation reads as "done."
- **Escalation gate** — the exact condition that ends iteration and routes work to a human or another repo instead of looping again.

### Loop-engineering's two principles (non-negotiable)

1. **Comprehension debt grows faster than code debt.** A loop that ships changes you no longer understand is a liability, not leverage. Every iteration MUST leave the scratchpad readable by a cold agent. Verification is *your* job — it cannot be delegated to the loop itself.
2. **present ≠ credited.** Context being *assembled* is not context being *received and used*. Before a loop acts on grounding (code structure, peer registry, prior findings), assert the agent actually has it — don't assume the plumbing delivered it. (This rule exists because it once didn't.)

## Git operations: commit → PR → drive-green → merge → conflicts

A develop-loop's output is git history, so the loop owns the full path from change to merged code, *as its own identity* (accountable history). Never bypass the integrity gates — the gates are why the loop is trustable. (These extend the "Safety rails" below; they do not replace them.)

- **Commit.** One logical change per commit. Never `--no-verify` past a pre-commit hook; if a formatter/linter fails, fix the root cause, don't suppress it.
- **Branch + PR.** Develop on a feature branch, never directly on a protected `main`. Open the PR as the loop's identity. Mirror the repo's PR-template section headings if one exists; skip any section asking for secrets.
- **Watch the PR, drive it green.** After opening, subscribe to PR activity instead of polling. On each CI failure: re-diagnose, fix, re-push — one round is not the task; the terminal state is MERGED/CLOSED. On review comments: push unambiguous in-scope fixes; escalate ambiguous or architecturally-significant ones.
- **Merge — gates are sacred.** Merge only when CI is green and required approvals are met. NEVER pass `force_merge`, `--admin`, `merge_when_checks_pass`, or `git push --force` to a protected branch. **If CI is red, stop and report — don't work around the gate.**
- **Resolve conflicts by understanding both sides.** A conflict is two real intents colliding — never blindly take one side or delete markers to make it compile. Re-run the checker/tests after resolving. If a conflict reveals a genuine *design* collision (not a mechanical overlap), that's an escalation gate — surface it rather than papering over it.
- **Re-check PR state proactively.** CI-success, fresh pushes, and conflict transitions aren't always delivered as events — don't rely on webhooks alone.

### Mesh-aware escalation (mesh-participating repos)

When a loop hits its gate and the fix belongs elsewhere, don't sit on it: file on the **upstream** repo (e.g. via `gitea-pm`) with `from:<this-repo>` + `unblocks:<downstream>` labels so the autonomy loop and the downstream team get a return-signal. Grep before you consult; consult CEO/CTO only for intent/roadmap; cross-verify every consult against the code (consults are advisory, not truth). For a multi-team call, prefer `/deliberate`.

## Safety rails (apply to every loop)

- One commit per item by default. Force-push only on explicitly-labelled feature branches; **never** on shared mainlines (e.g. `master`, `main`, `develop`).
- Do **not** start a loop on an unclean working tree unless an explicit "stage current changes" item leads the list.
- **Stop** on any of: build red, tests red, infrastructure absent (port held, container missing, credentials missing), user-signalled stop, three consecutive iterations without progress.
- Log every stop reason in the scratchpad's `Findings` section so the next invocation knows.

## Anti-patterns (don't do these)

- **Passive waiting.** Never say "still writing" or "still running" without checking. If a background task is slow, investigate — don't just report the delay.
- **Inline long reads.** Reading >300 lines of a file into the main context burns the context window. Delegate to an `Explore` agent instead, even for "just recon".
- **Error-driven sub-iterations.** Running a command, hitting one missing config key, fixing it, re-running, hitting another — this is N iterations disguised as one. Instead, **pre-flight: enumerate the full required-input surface** (grep config schemas, read abstract method signatures, check env vars) before the first execution. One informed run beats N reactive fixes.
- **Gateless items.** An item without an observable pass/fail criterion cannot be evaluated. "Verify artifact exists" is not a gate — "artifact contains ≥1 non-boilerplate edit" is. Define the gate at creation time.
- Doing the work without writing to the scratchpad. The point IS the cross-iteration memory; skipping the write defeats the loop.
- Re-discovering decisions on every iteration. If the prior iteration picked a path, the ADR captures it; trust it unless evidence forces a Supersede.
- Padding the items list to make convergence look further away. Items must be concrete and outcome-shaped; "polish later" is not an item.
- Using `/loopit` as a project planner. It's an execution loop. Long-horizon planning belongs in design docs / Jira / ADRs *before* `/loopit` starts.
- Using `general-purpose` agents when specialists exist. Check `.claude/agents/` and built-in agent types first. Delegate to `Explore` for research, `Plan` for design, domain-specific agents for domain issues.
- One monolithic agent for multi-topic work. Split into 2-3 focused agents running in parallel.
- **Best-of-N on a binary item.** Spawning N parallel attempts at a pass/fail item burns N× the budget for no gain — best-of-N is only for metric-maximizing items where attempt quality varies (see *Optimization-shaped items*). Likewise, optimizing a metric with **no hard correctness gate** lets the loop "win" by breaking correctness.

## Example — first invocation

```
/loopit harden e2e suite against alphabetical-order races
```

Result:
- Slug: `e2e-alpha-order-races`
- `.loopit/e2e-alpha-order-races/scratchpad.md` created with the initial items derived from a project-specific diagnostic.
- `.loopit/e2e-alpha-order-races/adr.md` created empty (no decisions yet).
- `/loop` prompt drafted with that scratchpad + ADR as load-bearing references.
- User asked: draft only or execute now?

## Example — auto-seed from prior suggestion

Assistant just produced a prioritised list, e.g.:

> ### Low-hanging fruit
> 1. AC #12 — update operating area in Edit scenario *(15 min)*
> 2. AC #1 — assert authorized planner identity *(10 min)*
> 3. AC #9 — unique-identifier round-trip *(10 min)*

User then types:

```
/loopit
```

Result:
- Recent-turn scan finds the ranked list.
- Synthesised goal: "EMS-333 partial-coverage low-hanging fruit (AC #12, #1, #9)".
- Slug: `ems-333-low-hanging-fruit`.
- Confirms the seed back to the user before writing any files.
- On confirm: items list pre-populated with the three AC entries, each with the effort estimate as a hint and a pass/fail gate (e.g. "PASS: test Edit_scenario passes with new operating area / FAIL: test red or operating area unchanged").

## Example — re-invocation a week later

```
/loopit harden e2e suite against alphabetical-order races
```

Result:
- Slug matches → existing files read.
- Status block updated with new "Last iteration" timestamp.
- Loop continues from the first unchecked item; ADRs from prior runs constrain choices (e.g. "we decided in ADR-002 that we use `@ResetState` over per-fixture reset; don't re-litigate").

## Notes

- `.loopit/` should generally be **committed** so the team shares the learning. If you want personal scratchpads, add `.loopit/personal/` to `.gitignore` and store there.
- ADR numbering is per-slug, not global. ADR-001 in slug `e2e-alpha-order-races` is unrelated to ADR-001 in `dflash-bench-tuning`.
- Keep findings short — one line each. If a finding is long, it's probably an ADR.
- **Pre-flight before first run.** When an item involves running a command or tool for the first time (e.g. a training script, a test suite, a build), the iteration must first enumerate the full required-input surface — config keys, env vars, abstract methods, CLI flags — before executing. This collapses N "fix one missing key" sub-iterations into one informed run. Delegate the enumeration to an `Explore` agent if it spans multiple files.

## Gitea integration (optional, for projects with a local Gitea)

When a Gitea instance is available (e.g. `localhost:3200`), `/loopit` can sync items to issues so progress is visible beyond the session. **This is load-bearing for multi-session work** — without it, every fresh session re-discovers what's already filed.

### Setup

1. Ensure a **milestone** exists for the loopit slug. Create via:
   ```
   curl -s -u "<user>:<token>" -X POST "http://localhost:3200/api/v1/repos/<owner>/<repo>/milestones" \
     -H "Content-Type: application/json" \
     -d '{"title":"<slug>","description":"<goal>"}'
   ```
2. Record the milestone ID in the scratchpad's `## Status` section as `Gitea milestone: #<id>`.

### Per-item sync rules

| Event | Action |
|-------|--------|
| **Item created** in scratchpad | Create a Gitea issue with title = `<item-id>: <summary>`, body = description + acceptance criteria, milestone = slug's milestone. Record `gitea: #<n>` next to the item in scratchpad. |
| **Item completed** | Close the Gitea issue with a comment summarizing the result (commit hash, key metric). |
| **Item blocked** | Add a `blocked` label + comment explaining what's needed. |
| **Diagnostic pass finds new work** | Create new issues + scratchpad items in one step. |
| **Convergence** | Close the milestone. |

### Confirmed-root-cause / decisive finding → comment on the issue **in the same iteration**

**This is the rule that prevents the most expensive double-work.** When an iteration confirms a root cause, decisively refutes a prior theory, or pins a bug to a file/line with evidence — **post it to the source-of-truth Gitea issue that iteration, not only to the local scratchpad/ADR.** The scratchpad and ADR are session-local; the Gitea issue is the cross-session, cross-team source of truth. If the work is ever resumed fresh, re-discovered by another agent, or handed to a reviewer, the decisive finding must already be on the issue — otherwise a future pass re-derives it from scratch (and re-runs the same probes), which is exactly the loop failure mode that costs hours.

- A finding is "decisive" if it would change *what the next pass does* — confirmed root cause, a refuted hypothesis, a file:line pin, a "do NOT re-bake / do NOT ship X" verdict, a repro recipe, or an answer to an open question on the issue.
- Mirror it to **every** issue that tracks the same bug (a finding often applies to a cluster — e.g. #743 + #804). Don't make a reader hop between issues.
- If a prior ADR/comment was **overstated or refuted** by new evidence, post a **correction** the same iteration and mark the old ADR superseded. Never let a known-wrong conclusion sit as the last word on an issue — that is worse than no conclusion.
- Keep it a *finding*, not a scratchpad dump: evidence + conclusion + fix direction + the precise repro/test that the next pass must reproduce. One focused comment beats five.
- This does **not** mean syncing every one-line scratchpad note — only the decisive ones. Routine findings stay in the scratchpad.

### Reading from Gitea on re-entry

When `/loopit` is re-invoked and the scratchpad already exists:
1. Fetch all open issues for the milestone: `GET /api/v1/repos/<owner>/<repo>/issues?milestones=<id>&state=open`
2. Cross-reference with scratchpad items — any issue not in the scratchpad is a new item (someone else filed it).
3. Any scratchpad item without a `gitea: #<n>` tag gets an issue created.
4. Any closed issue not marked done in scratchpad — investigate (may have been closed externally).

### Scratchpad item format with Gitea

```markdown
- [ ] CAL-4: Add JMA/Kalman gates — PASS: kalman_filter_test green / FAIL: test red (gitea: #4)
- [x] CAL-3: Fix Rust scorer — completed before Gitea tracking
```

### Anti-patterns for Gitea sync

- Don't sync trivial scratchpad edits (typos, timestamp updates) to Gitea — only item state changes.
- Don't use Gitea comments as a substitute for *routine* scratchpad findings. The scratchpad is the source of truth; Gitea is the visibility layer. **But decisive findings (confirmed root cause, refuted theory, file:line pin) DO go on the issue the same iteration** — see "Confirmed-root-cause" rule above. That is not "using comments as a substitute"; it is keeping the cross-session source of truth honest.
- Don't create issues for items that are already done before the first sync.