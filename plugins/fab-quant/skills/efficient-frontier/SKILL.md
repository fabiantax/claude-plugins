---
name: efficient-frontier
description: **name:** efficient-frontier
---

**name:** efficient-frontier

**description:** Apply the same orchestration as `/fable-efficient` to any high-cost frontier model: delegate research, coding, and testing to cheaper subagents while keeping planning, synthesis, and final review with the expensive model.

## Workflow

The strategy involves four key steps:

1. Recognize which decisions require the frontier model: architecture, prioritization, ambiguity resolution, risk, synthesis, and final review.

2. Recognize delegable work: research scans, repository inventory, search, docs extraction, browser/testing passes, log reduction, test failure clustering, narrow coding, and mechanical edits.

3. Spawn parallel subagents for independent slices with clear ownership, bounded scope, verification gates, and expected evidence.

4. Require compact returns: findings, changed files, commands run, residual risk, stop conditions hit, and anything the frontier model must decide.

5. Integrate and review centrally before presenting the result.

## Handoff Packets

Delegated prompts should be self-contained, including repo path, objective, scope boundaries, relevant files, expected formats, verification commands, and stopping points when work exceeds assignment scope or evidence becomes unavailable.

## Review Loop

Treat delegated output as evidence to inspect, not a verdict to forward. Reexamine critical files, review risky changes, and verify important results independently before concluding work.

## Common Scenarios

Research, coding, testing, and debugging work can be distributed while the frontier model retains strategic decision-making authority.

## Guardrails

Key restrictions include avoiding delegation of immediate blockers, preventing simultaneous multi-agent edits to shared files, maintaining independent verification of high-risk work, and recognizing that efficiency gains depend on parallelizable activities.

## Default Framing

Use the frontier model as the orchestrator and reviewer, and use cheaper subagents for token-heavy research, coding, or testing.
