---
name: visual-plan
description: **name:** visual-plan
---

**name:** visual-plan

**description:** Use Agent-Native Plans when coding-agent work needs a reviewable plan published as an interactive document — inline diagrams, annotated code walkthroughs, file trees, optional UI wireframes or prototypes, open-question forms, and comments — before implementation starts.

**metadata visibility:** exported

## Core Purpose

Agent-Native Plans is a structured visual planning mode for coding agents. It combines scannable documents with editable blocks including inline diagrams, code snippets, and open questions, alongside optional visual review areas (wireframe canvas, live prototype, or both in tabs).

## When To Use

Multi-file, ambiguous, long-running, risky, or UI-heavy work that benefits from human review before implementation starts.

## Plan Discipline

- Gate hard: don't draft a plan for trivial or well-scoped single-file work.
- Research files before drafting: inspect the codebase, real schemas, and existing patterns first.
- Decide hard-to-reverse bets upfront: call out irreversible choices explicitly.
- Preserve existing plans: update rather than replace when revising.
- Planning is read-only: no implementation until the user approves.
- Clarify vs. assume: surface open questions in a bottom `question-form` block rather than guessing.
- The plan is the approval gate: treat user sign-off on the plan as the trigger to begin coding.

## Core Workflow

1. Inspect codebase — read relevant files, schemas, APIs, component trees.
2. Call `get-plan-blocks` for the authoritative block catalog before composing.
3. Compose using native blocks: diagrams, annotated-code, file-tree, wireframes, question-form.
4. Surface plan link for user review.
5. Call `get-plan-feedback` before applying any edits.
6. Apply changes via `update-visual-plan`.
7. Export only when the user requests it.

## Self-Review Before Handoff

For high-stakes work (auth, data migrations, public API changes, architecture shifts), run an adversarial review pass concurrently with the plan draft. Ask: "What would break if this plan is wrong?"

## Visual Surface Choice

| Work type | Surface |
|---|---|
| Architecture-only / backend | No canvas — document only |
| Static screens | Canvas only |
| Multi-step flows | Canvas + prototype tabs |
| Interaction-heavy | Prototype-first |

## Document Quality

- Outcome-first: lead with what will be different after the work, not how.
- Prose-first: write full sentences; bullet lists only for genuine enumerations.
- Self-contained: a reader with no prior context should understand the plan.
- Open questions at the bottom in a single `question-form` block — never scattered through the document.

## Local-Files Privacy Mode

Set `AGENT_NATIVE_PLANS_MODE=local-files` to store plans as MDX folders under `plans/<slug>/` with no hosted Plan app writes. All functionality preserved; plans stay fully local.

## Setup

```sh
npx @agent-native/core@latest skills add visual-plan
```

Browser guests work without sign-up.

## References

See `references/canvas.md`, `references/document-quality.md`, `references/exemplar.md`, and `references/wireframe.md` for detailed standards.
