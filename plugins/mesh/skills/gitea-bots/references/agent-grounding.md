# Agent Grounding — Anti-Hallucination Knowledge Files

Updated 2026-06-03.

## Problem

AI agents (CEO/CTO personas running on Qwen3.6-35B-A3B) hallucinate crate names, types, and features that don't exist. Grounding files give each agent a concise "what actually exists" cheat sheet loaded alongside their persona at inference time.

## Architecture

```
.claude/
  agents/
    <agent>.md          ← hand-maintained persona
    <agent>.yaml        ← runtime config (includes grounding_file: path)
  grounding/
    <agent>.md          ← MACHINE-GENERATED (do not edit by hand)
    hallucination-blacklist.txt  ← hand-maintained per-project
```

## Generator Script

**Location:** `fab-agent-runtime/scripts/generate-grounding.mjs`

**Usage:**
```bash
# Single role
node scripts/generate-grounding.mjs --project ~/Developer/personal/GraphFusion --role cto

# All agents in project
node scripts/generate-grounding.mjs --project ~/Developer/personal/GraphFusion --all-roles

# Dry-run (stdout only, no files written)
node scripts/generate-grounding.mjs --project ~/Developer/personal/GraphFusion --role cto --dry-run
```

**What it scans:**
- `cargo metadata --format-version 1 --no-deps` → workspace crate list + descriptions
- `grep -rh "^pub (fn|struct|trait|enum)" <crate>/src/` → key public symbols (CTO only)
- `CLAUDE.md` → architecture constraints (build mutex, memory budgets)
- `.claude/grounding/hallucination-blacklist.txt` → static hallucination targets

**Output:** markdown file with YAML frontmatter (`generated_at`, `ttl_hours: 72`, `project`, `role`)

## Dispatcher Integration

1. Agent YAML declares `grounding_file: /absolute/path/to/<agent>.md`
2. At dispatch time, `mergeGrounding()` in `dispatcher.ts`:
   - Reads the grounding file + persona file
   - Concatenates: `<grounding>\n\n---\n\n<persona>`
   - Writes to temp file, substitutes `--append-system-prompt` path
   - Cleans up temp file after subprocess exits
3. If grounding file missing, falls back to persona-only (graceful degradation)
4. **Staleness check (STORY-141):** warns in logs when TTL exceeded

## Role Differentiation

| Section | CEO | CTO/Specialist |
|---------|-----|---------------|
| Crates (with descriptions) | ✓ | ✓ |
| Key Types (pub symbols) | ✗ | ✓ (5 per crate) |
| What Does NOT Exist | Top 8 | Full list |
| Architecture Constraints | ✓ | ✓ |
| Confidence Rule | ✓ | ✓ |

Typical sizes: CEO 55-81 lines, CTO 120-292 lines.

## CI Auto-Regeneration (STORY-138)

Each project has `.gitea/workflows/grounding-regenerate.yml` that triggers on:
- Push to `main` touching `Cargo.toml`, `crates/*/src/**/*.rs`, `crates/*/Cargo.toml`, or `hallucination-blacklist.txt`
- Manual `workflow_dispatch`

The workflow runs the generator and auto-commits changed grounding files.

## Grounded Agents (17 total)

| Project | Agents |
|---------|--------|
| GraphFusion | graphfusion-ceo, graphfusion-cto, graphfusion-devops, graphfusion-agent, gf-codegraph, gf-graphrag, gf-legal, gf-spatial |
| Atlas | atlas-ceo, atlas-cto, atlas-agent |
| fab-trader | fab-trader-ceo, fab-trader-cto, fab-trader-data-platform, fab-trader-devops, fab-trader-quant-ml, fab-trader-rust-platform, fab-trader-signal-pipeline, fab-trader-strategy-research, fab-trader-surfaces |
| localscout | localscout-ceo, localscout-cto, localscout-devops |

## Adding Grounding to a New Agent

1. Create `.claude/grounding/hallucination-blacklist.txt` in the project
2. Run: `node scripts/generate-grounding.mjs --project <dir> --role <role>`
3. Add `grounding_file:` to the agent YAML
4. Restart the agent service

## Blacklist Maintenance

Edit `<project>/.claude/grounding/hallucination-blacklist.txt` — one entry per line, `#` comments, blank lines ignored. Common hallucination patterns:
- Crate names that sound right but don't exist (e.g., `graphfusion-spatial` → real is `graphfusion-geodata`)
- Types/structs that don't exist (e.g., `AtlasEmbeddings`)
- Re-ground after adding entries: `node scripts/generate-grounding.mjs --project <dir> --all-roles`
