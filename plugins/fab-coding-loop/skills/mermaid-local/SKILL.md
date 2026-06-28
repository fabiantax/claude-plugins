---
name: mermaid-local
description: Mermaid Local — validate and render Mermaid diagrams locally
---

# Mermaid Local — validate and render Mermaid diagrams locally

## Activation
When the user asks to validate, verify, check, render, or display a Mermaid diagram.

## Behavior
Run `~/.claude/skills/mermaid-local/mermaid.ts` via `bun`.

### Validate syntax only
```bash
bun ~/.claude/skills/mermaid-local/mermaid.ts validate < file.mmd
echo 'graph TD; A-->B' | bun ~/.claude/skills/mermaid-local/mermaid.ts validate
```

### Render to PNG
```bash
bun ~/.claude/skills/mermaid-local/mermaid.ts render file.mmd output.png
bun ~/.claude/skills/mermaid-local/mermaid.ts render file.mmd output.svg
```

### Render from string
```bash
bun ~/.claude/skills/mermaid-local/mermaid.ts render - output.png <<< 'graph TD; A-->B'
```

## Output
- `validate`: prints `VALID` or `INVALID: <error>` and exits 0/1
- `render`: writes PNG/SVG to the output path, prints dimensions

## Dependencies
- `bun` runtime
- `playwright` (headless Chromium, already installed)
- No external API calls
