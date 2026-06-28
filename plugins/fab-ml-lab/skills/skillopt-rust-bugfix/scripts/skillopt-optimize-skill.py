#!/usr/bin/env python3
"""One-shot SkillOpt optimizer for Atlas bugfix skill.

Bypasses the full training loop — just runs a single reflect+rewrite pass
using the local llama-server to optimize the skill doc.

Usage: python3 scripts/skillopt-optimize-skill.py
"""

import httpx
from pathlib import Path

# Path relative to this script's location (inside the skill package)
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILL_PATH = str(SKILL_DIR / "SKILL.md")
BASE_URL = "http://127.0.0.1:8002/v1"
MODEL = "Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"

# Ground truth: what happened when agents used the unoptimized skill
ROLLOUT_RESULTS = [
    {
        "id": "atlas-127",
        "task": "Fix #127: atlas query --quiet suppresses the query result",
        "outcome": "success",
        "time_minutes": 17,
        "files_read": 18,
        "edits_made": 2,
        "notes": "Agent spent 15 min exploring, 2 min editing. Should have been <2 min total with precise file path.",
    },
    {
        "id": "atlas-143",
        "task": "Fix #143: atlas stats is a stub but advertised",
        "outcome": "success",
        "time_minutes": 0.5,
        "files_read": 1,
        "edits_made": 1,
        "notes": "Surgical fix — uncommented 1 line. Precise prompt with exact file and line number.",
    },
    {
        "id": "atlas-113",
        "task": "Fix #113: atlas init writes broken TOML",
        "outcome": "success",
        "time_minutes": 2,
        "files_read": 3,
        "edits_made": 1,
        "notes": "Explore agent found exact mismatch in 2 min. Edit took 30 seconds.",
    },
    {
        "id": "atlas-132",
        "task": "Create smoke test for init && scan && query",
        "outcome": "success",
        "time_minutes": 3,
        "files_read": 2,
        "edits_made": 1,
        "notes": "Used existing test patterns as reference. Straightforward once pattern was known.",
    },
]

REFLECT_PROMPT = """You are optimizing a skill document for AI coding agents that fix bugs in a Rust CLI project (Atlas).

## Current Skill Document

{skill_content}

## Rollout Results (agents using this skill)

{rollout_results}

## Task

Analyze the rollout results and produce a PATCHED version of the skill document that would reduce agent exploration time.

Key observations from the data:
- Vague prompts ("find and fix X") cause agents to read 18+ files and take 17 minutes
- Precise prompts ("edit file.rs line 42") lead to 30-second fixes
- The Explore→Edit→Check→Commit workflow works but needs to be enforced more strongly

Produce the FULL rewritten skill document. Focus on:
1. Adding explicit "NEVER do X" anti-patterns with concrete examples
2. Providing a file location lookup table so agents skip exploration
3. Adding a decision tree: "if fix type = serde_default, do X; if fix type = commented_out, do Y"
4. Reducing the skill to the minimum viable instructions — cut anything that doesn't directly reduce fix time

Output ONLY the rewritten skill document in markdown, nothing else."""


def main():
    # Read current skill
    with open(SKILL_PATH) as f:
        skill_content = f.read()

    print(f"Read skill: {len(skill_content)} chars")

    # Format rollout results
    results_text = "\n".join(
        f"### Task {r['id']}: {r['task']}\n"
        f"- Outcome: {r['outcome']}\n"
        f"- Time: {r['time_minutes']} min\n"
        f"- Files read: {r['files_read']}\n"
        f"- Edits made: {r['edits_made']}\n"
        f"- Notes: {r['notes']}\n"
        for r in ROLLOUT_RESULTS
    )

    prompt = REFLECT_PROMPT.format(
        skill_content=skill_content,
        rollout_results=results_text,
    )

    print("Calling optimizer model...")
    response = httpx.post(
        f"{BASE_URL}/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 8192,
        },
        timeout=300,
    )
    response.raise_for_status()

    result = response.json()
    content = result["choices"][0]["message"]["content"]

    # Strip markdown fences if present
    if content.startswith("```markdown"):
        content = content[len("```markdown") :]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    # Write optimized skill next to the original
    output_path = str(SKILL_DIR / "SKILL_optimized.md")
    with open(output_path, "w") as f:
        f.write(content)

    print(f"\nOptimized skill written to: {output_path}")
    print(f"Original: {len(skill_content)} chars → Optimized: {len(content)} chars")

    # Show diff summary
    orig_lines = skill_content.split("\n")
    opt_lines = content.split("\n")
    print(f"Original: {len(orig_lines)} lines → Optimized: {len(opt_lines)} lines")


if __name__ == "__main__":
    main()
