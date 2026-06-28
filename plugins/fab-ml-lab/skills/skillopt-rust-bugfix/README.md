# skillopt-rust-bugfix

A Claude Code skill for **zero-exploration bugfix workflows** in Rust CLI projects. Enforces surgical search → precise edit → `cargo check` → commit, cutting agent fix time from 17 min to <5 min.

## Install

Copy this directory into your Claude Code skills path:

```bash
cp -r skillopt-rust-bugfix/ ~/.claude/skills/
```

Or symlink if you're developing locally:

```bash
ln -s $(pwd)/skillopt-rust-bugfix ~/.claude/skills/skillopt-rust-bugfix
```

## Use

In a Claude Code session working on a Rust bug:

```
/skillopt-rust-bugfix
```

The skill activates the pre-edit checklist gate, fix-type decision tree, and surgical workflow.

## What It Does

1. **Pre-Edit Checklist Gate** — Forces you to locate the exact failure, classify the bug type, and draft a precise edit BEFORE touching any file
2. **Fix-Type Decision Tree** — Maps common Rust CLI bug patterns (serde_default, commented_out, flag_logic, fmt, missing_guard) to surgical fix patterns
3. **File Location Table** — Skip exploration by jumping to known line ranges for command dispatch, config parser, scan pipeline, etc.
4. **Anti-Pattern Enforcement** — Concrete examples of what NOT to do (vague prompts, full-file reads, local test runs) with the correct alternative

## SkillOpt Integration

This skill ships with a one-shot optimizer (`scripts/skillopt-optimize-skill.py`) that re-optimizes the skill document using a local LLM (llama-server on port 8002):

```bash
# Add new rollout results to the ROLLOUT_RESULTS array in the script
# Then run:
python3 scripts/skillopt-optimize-skill.py
```

The optimizer:
1. Reads the current skill document
2. Formats rollout results (time, files read, edits made)
3. Sends a reflect+rewrite prompt to the local model
4. Writes the optimized version for review

## Training Data

Ground truth task batches live in `.skillopt/tasks/train/`:

- `batch_001.json` — 4 bugfix tasks from Wave 1 (atlas-127, atlas-143, atlas-113, atlas-118)

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | The skill document (active version) |
| `rust-bugfix_v0.1.0.md` | Original unoptimized skill for comparison |
| `README.md` | This file |
| `scripts/skillopt-optimize-skill.py` | One-shot SkillOpt optimizer (copies into project) |
| `.skillopt/atlas-bugfix.yaml` | SkillOpt training config for future full runs |
| `.skillopt/tasks/train/batch_001.json` | Ground truth training data |

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-06-05 | Initial skill (unoptimized, from skillopt-rust-bugfix.md) |
| 0.2.0 | 2026-06-05 | SkillOpt-optimized: added pre-edit checklist, fix-type decision tree, file location table, anti-patterns, rollout baseline |
