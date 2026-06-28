---
name: plan-and-decompose
description: Size, decompose, and track prioritized work items in one pass. Replaces task-sizing, fab-swarm-refine, and coordinated-task-management with a single pipeline: assess → split → create → dispatch.
---

# Plan and Decompose

One skill to go from a prioritized backlog to tracked, sized, dispatchable tasks.

## Pipeline

```
Input: prioritized items (from RICE/WSJF/Kano or ad-hoc)
  │
  ├─ 1. SIZE     → XS/S/M/L/XL + model tier + uncertainty
  ├─ 2. SPLIT    → decompose L/XL into subtasks with deps
  ├─ 3. TRACK    → create in TaskCreate (+ fab-swarm MCP if multi-agent)
  └─ 4. DISPATCH → assign owners, spawn agents if ready
```

## Step 1: Size

| Size | Time | Files | Model | Action |
|------|------|-------|-------|--------|
| XS | <5m | 1 | haiku | Execute immediately |
| S | 5-15m | 1-2 | haiku | Single agent |
| M | 15-60m | 3-5 | sonnet | Consider splitting |
| L | 1-4h | 5-10 | sonnet/opus | Must split |
| XL | >4h | 10+ | opus | Split into epic + subtasks |

**Uncertainty** — Low (execute) / Medium (spike first) / High (prototype)
**Risk** — Low / Medium (cross-cutting) / High (core system, security, data)

**Heuristics:**
- `grep -r` for related patterns → estimate file count
- Cross-crate changes → bump size
- No existing tests → bump risk
- async/concurrency → bump uncertainty

## Step 2: Split

Split if ANY: size L/XL, >5 files, multiple concerns, different expertise needed.

**Decomposition rules:**
- Max 1 file per subtask for XS-S, 2-3 files for M
- Declare dependencies at creation time (enables DAG wave execution)
- Each subtask must be independently verifiable (`cargo check` / `cargo nextest`)
- Name subtasks imperatively: "Fix X", "Extract Y", "Add Z"

**Dependency patterns:**
```
Sequential:  A → B → C         (B blocked by A, C blocked by B)
Parallel:    A ┐               (B and C independent, both blocked by A)
             B ├→ D
             C ┘
Diamond:     A → B → D        (B and C parallel, D waits for both)
                → C ┘
```

## Step 3: Track

**For solo work** — just TaskCreate:
```
TaskCreate({ subject, description, activeForm })
```

**For multi-agent work** — dual system:
1. `stig_add_tasks` in fab-swarm (source of truth for coordination)
2. `TaskCreate` in Claude Code (persistence + UI)

**For cross-session work** — ensure `CLAUDE_CODE_TASK_LIST_ID` is set.

## Step 4: Dispatch

| Size | Dispatch |
|------|----------|
| XS | Do it inline, no agent |
| S-M | Single coder agent, `run_in_background: true` |
| L | Spawn team: coordinator + N coders (1 per file) + reviewer |
| XL | Break into L epics first, then dispatch each |

**Agent assignment:**
- `coder` for implementation
- `tester` for test writing
- `reviewer` for code review
- `Explore` for research/spikes

**Parallelism rules:**
- Non-overlapping files → spawn agents simultaneously
- Same file → sequential (or use worktrees)
- Cross-file dependencies → declare in blockedBy

## Output Format

When running this skill, produce:

```markdown
## Execution Plan

### Wave 1 (unblocked)
| # | Task | Size | Model | Agent | Files |
|---|------|------|-------|-------|-------|
| 1 | ...  | S    | haiku | coder | foo.rs |

### Wave 2 (blocked by wave 1)
| # | Task | Size | Model | Agent | Files | blockedBy |
|---|------|------|-------|-------|-------|-----------|
| 2 | ...  | M    | sonnet| coder | bar.rs| 1         |

### Wave N
...
```

Then create all tasks with TaskCreate and spawn wave 1 agents.

## Decision Tree

```
Got a backlog?
│
├─ Single task, obvious scope?
│  └─ SIZE → execute (skip tracking)
│
├─ Multiple tasks, prioritized?
│  └─ SIZE each → SPLIT L/XL → TRACK all → DISPATCH wave 1
│
├─ Multi-agent project?
│  └─ SIZE → SPLIT → TRACK (dual: stig + TaskCreate) → DISPATCH
│
└─ Research spike?
   └─ SIZE=M → single Explore agent → report → re-assess
```
