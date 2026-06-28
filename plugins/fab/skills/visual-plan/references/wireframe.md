# HTML Wireframe Quality — Single Source of Truth

This document establishes the canonical quality standards for HTML wireframes used in `/visual-plan` and `/visual-recap`.

## Core Concept
"A wireframe is an HTML mockup. The renderer owns the look; you write the content." Authors provide semantic HTML fragments while the renderer handles styling, theming, and visual effects.

## Structure Requirements
Wireframes consist of two parts: self-contained HTML content and a surface type (browser, desktop, mobile, popover, or panel). Authors should never include `<html>`, `<body>`, `<script>`, or `<style>` tags.

## Styling Approach
Plain semantic HTML elements receive automatic theming. Helper classes like `.wf-card`, `.wf-pill`, and `.wf-muted` provide common patterns. "Never hard-code a hex color and never set `font-family`" — instead use CSS custom properties like `--wf-ink`, `--wf-line`, and `--wf-accent`.

## Layout Principles
Use inline flexbox and grid for layouts. "You write the real layout" with properties like `display:flex; gap:10px; padding:16px`, allowing the renderer to maintain consistent rendering across themes and zoom levels.

## Surface Selection
Match the actual user interface being depicted rather than defaulting to desktop. Use only appropriate surface types and avoid creating unnecessary responsive variants.

## Content Guidelines
Include realistic product content — real labels, counts, dates, and button text — rather than placeholder text. Fill frames completely to demonstrate actual vertical rhythm.

## Special Considerations
- Skeleton states use `data.skeleton: true`
- Before/After comparisons preserve unchanged controls
- Bottom bars should pin to frame bottom using flexbox
- Persistent chrome spans full frame width
- Labels should remain short and use `white-space: nowrap` where appropriate
