# Loop It

Run a self-paced work loop: pick the highest-leverage user story you can make
real progress on, work it, then loop. The loop is the unit — you decide the
cadence, you don't ask permission to continue.

**User input:** $ARGUMENTS

## Core principle: never idle-block on CI

**When you are waiting on CI (or any async gate — a build, a test run, a remote
job, RAM to free, an A2A consult reply), do NOT stop and wait. Immediately start
the next independent user story.** A blocked thread at idle is wasted throughput;
a blocked thread that has pivoted to other work costs nothing.

Concretely, the moment you arm a monitor / fire-and-forget a CI run and the
outcome won't land for minutes:

1. **Switch context, don't stall.** Pick a *different* user story from the
   backlog that shares no files, no branch, and no gate with the blocked one.
2. **Prefer work that needs no heavyweight resources** while the box is under
   load — read/verify code, draft tests, write a sibling fix on its own branch,
   file/refine user stories, update memory/handovers, do the cheap part of the
   next item now so the expensive part (build/test) is ready to fire the moment
   resources free.
3. **Arm a monitor for the blocked gate** (CI outcome, RAM threshold, PR
   status) so you get pinged the instant it resolves — then resume that story
   immediately, without manual polling or foreground `sleep`.
4. **Keep the blocked story's next action prepped** (diffs reviewed, fmt clean,
   commit message drafted, PR body ready) so when the gate clears you act in one
   step instead of re-loading the context.

If there is genuinely *no* other story to start — then and only then report
you're blocked and say what you're waiting for. The default is to keep moving.

## The loop

Each iteration:

1. **Select** the highest-priority user story that is currently actionable
   (unblocked, has a clear next step). Use `/prioritize` if the backlog needs
   ranking.
2. **Scope** it to one shippable slice — a branch, a commit, a merged PR, a
   filed issue. Don't boil the ocean in one iteration.
3. **Execute** it end-to-end: read → implement → verify → commit → push → PR →
   merge (autonomously, per standing directive). Fan out subagents for
   >30-LOC / multi-file work, one per file.
4. **Record** the outcome: close the issue explicitly via the API (`Closes #N`
   is unreliable on squash-merge), write a trace/handover, update memory if
   something non-obvious was learned.
5. **Loop**: return to step 1. If a gate is now blocking the next story, apply
   the "never idle-block on CI" rule above — pivot to an independent story and
   arm a monitor for the gate.

## Stop conditions

- The backlog of actionable stories is empty (and no gate will imminently free
  one).
- The user gave a bounded scope ("just ship X") and X is shipped.
- Every remaining story is blocked on a gate you cannot parallelize past, and
  monitors are armed for each — then report status and what you're waiting on.

## Per-iteration scratchpad

Keep a scratchpad for the loop under the repo's `.loopit/<epic-or-story>/` (or
`~/.loopit/<topic>/` for cross-repo work). Use it for decisions, captured
evidence, and the "next action when the gate clears" note — so any resumed
iteration picks up without re-deriving context.
