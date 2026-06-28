# HTML Wireframe Quality Guidelines — Summary

This canonical guide establishes standards for HTML wireframes used in `/visual-plan` and `/visual-recap`.

**Core Philosophy**
"A wireframe is an HTML mockup. The renderer owns the look; you write the content." Authors create semantic HTML fragments while the renderer handles styling, theming, and sketch effects.

**HTML Structure**
Wireframes consist of two properties: `surface` (the device type) and `html` (self-contained semantic markup). The framework prohibits `<html>`, `<body>`, `<script>`, and `<style>` tags, requiring authors to use only layout and product content.

**Styling Approach**
"Write PLAIN semantic HTML and let the renderer style it." The system provides helper classes (`.wf-card`, `.wf-pill`, `.wf-muted`) and CSS custom properties (`--wf-ink`, `--wf-line`, `--wf-accent`) that automatically adapt to light/dark themes. Hard-coded hex colors and custom fonts are prohibited.

**Layout Requirements**
Use inline flexbox/grid for real layouts with `gap`, padding, and `height:100%`. Preserve borders as design elements and wrap content with adequate padding to prevent flush alignment against frame edges.

**Surface Selection**
Match actual contexts: `browser` for web pages, `desktop` for apps, `mobile` for phones, `popover` for floating menus, and `panel` for sidebars. Avoid unnecessary variants unless responsive behavior genuinely changes.

**Modification Strategy**
"Modify, don't redesign." When altering existing screens, reproduce the current layout first, then highlight only changed elements with annotations.

**Sub-surface Handling**
For small surfaces like dialogs or popovers, show the full context once, then create separate focused artboards using appropriate `surface` values.

**Special Cases**
Skeleton states use `skeleton: true` with textless placeholder geometry. Before/After comparisons preserve unchanged controls and use column headers for state labels, never embedded text.
