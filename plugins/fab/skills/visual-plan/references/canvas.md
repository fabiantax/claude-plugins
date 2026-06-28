# Canvas & Artboard Placement Guide

This canonical guide establishes rules for visual-plan canvas design:

**Core Principles:**
- The `surface` locks each artboard's footprint and aspect — never set artboard width/height and rely on auto-placement for simple layouts
- Organize mixed canvases using board-level positioning to create distinct lanes rather than cramped horizontal strips
- Maintain at least 96 pixels between rendered artboard rectangles plus annotation space

**Annotation Standards:**
Notes should be designer-style explanations placed near relevant frames. Use `targetId` and `placement` attributes rather than free-form positioning. "Use an arrow only to point at one specific control or transition; for a broad frame-level note, write text beside the frame with no connector."

**Content Requirements:**
Every artboard on the canvas must contain either inline HTML wireframe content or reference a wireframe block. "A label-only frame or a frame pointing at a deleted block renders empty and is rejected at parse time."

**Modern Practices:**
Newer plans should use HTML mockups rather than legacy kit-tree screen arrays. The document emphasizes using content patches for surgical edits rather than regenerating entire sections, enabling AI agents to make targeted modifications through the public MCP action schema.
