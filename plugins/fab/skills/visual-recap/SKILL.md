---
name: visual-recap
description: **name:** visual-recap
---

**name:** visual-recap

**description:** Use when publishing a summary of completed coding work as a visual-plan interactive document. Recap transforms diffs into structured blocks — UI wireframes, file trees, schema/API changes, code excerpts, and diagrams — avoiding plain list-diffs in favor of outcome narrative and prose.

## Key Principles

**Publication & Output:** Recaps must always be published as Agent-Native Plans through the `plan` MCP tool — never delivered as inline chat content. The hosted, interactive plan is the entire deliverable value.

**Privacy Mode Exception:** Local-files mode allows fully offline recaps stored in `plans/<slug>/` directories without database writes, provided users explicitly request this approach.

**Scope:** Recap the entire work unit/thread, gathering all thread-owned changes including original work, bug fixes, tests, and related artifacts while excluding unrelated pre-existing edits.

## Content Structure

A substantial recap follows this skeleton:
1. UI wireframes (when applicable)
2. Outcome narrative in 1-3 paragraphs
3. Schema/API blocks for contract changes
4. File tree showing changed files
5. Key changes section with focused diffs in horizontal tabs

**Budget guidance:** 3-8 key-change tabs keeps recaps reviewable; each excerpt should stay under approximately 150 lines.

## Mapping Changes to Blocks

- **Schema changes** → `data-model` blocks with change flags
- **API/route changes** → `api-endpoint` blocks with method, path, params
- **Code hunks** → `diff` blocks (split mode by default) with summaries and annotations
- **New files** → `annotated-code` rather than one-sided diffs
- **File changes** → `file-tree` with change flags
- **UI changes** → wireframes showing visual impact
- **Architecture shifts** → `diagram` blocks

## Quality Standards

Recaps must be **grounded in actual diffs** — paths, fields, and code must be mechanically derived, never inferred. When facts aren't in the diff, omit them rather than guess. Redact any secrets, tokens, or credential-like literals. Always call `get-plan-blocks` before authoring to access current block schemas rather than relying on memory.

## References

See `references/wireframe.md` for HTML wireframe standards.
