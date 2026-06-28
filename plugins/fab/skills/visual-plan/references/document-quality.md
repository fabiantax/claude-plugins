# Plan Document Quality — Single Source of Truth

This document serves as the canonical quality standard for technical plan documents.

**Core Philosophy**
The plan should be "a serious technical plan, not marketing" with "outcome-first, prose-first, self-contained, and specific" writing that avoids vague steps like "make it work."

**Visual and Document Relationship**
When top visuals exist, "the document carries the technical depth the visuals cannot show — concrete file/symbol maps, API and data contracts, code snippets, migration or implementation phases, risks, and validation."

**Block Usage Standards**
The document prescribes specific block types for different purposes:
- Use `rich-text` for prose with formatting
- Use `annotated-code` for files worth highlighting, with margin notes anchored to specific lines
- Use `diagram` for two-dimensional architecture relationships
- Use `columns` for side-by-side comparisons
- Use `tabs` for multiple states or directions
- Reserve `custom-html` as "a bounded escape hatch only"

**Open Questions Protocol**
"Open questions live at the bottom as a form when answers would change the plan." These should appear in a single final `question-form` block, never duplicated elsewhere in the document.

**Pre-Handoff Verification**
Before submission, authors must "open the plan and check it" to fix overlap, whitespace issues, clipped content, contrast problems, and unreadable diagrams.
