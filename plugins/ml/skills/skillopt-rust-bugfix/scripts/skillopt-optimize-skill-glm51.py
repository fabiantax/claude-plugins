#!/usr/bin/env python3
"""One-shot SkillOpt optimizer pointing at GLM-5.1 via Z.AI (Anthropic-compat).

Reads `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, and
`OPTIMIZER_DEPLOYMENT` (model name) from the environment — populated by
the sibling `skillopt-train-glm51.sh` launcher that sources them from
the CWD's `.claude/settings.local.json`.

Differences vs `skillopt-optimize-skill.py`:
  - Anthropic Messages API shape instead of OpenAI chat completions
  - Reads credentials from env (no hardcoded localhost:8002)
  - Includes the fab-swarm wire/ implementation as a real rollout
    result (delegation-violation case study) — the reflect prompt
    targets DELEGATION enforcement, not just surgical bugfix
"""

import os
import sys
import httpx
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILL_PATH = SKILL_DIR / "SKILL.md"

BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "").rstrip("/")
AUTH_TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
MODEL = (
    os.environ.get("OPTIMIZER_DEPLOYMENT")
    or os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL")
    or "glm-5.1"
)

if not BASE_URL or not AUTH_TOKEN:
    print(
        "error: ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN must be set in env.\n"
        "       run via scripts/skillopt-train-glm51.sh from a repo whose\n"
        "       .claude/settings.local.json defines them.",
        file=sys.stderr,
    )
    sys.exit(1)

# Ground truth: real rollouts of agents using the current skill.
# The fab-swarm wire/ entry is the case-study the user flagged in
# session — agent wrote ~700 LOC inline across 4 files in the main
# context instead of delegating to parallel coder agents.
ROLLOUT_RESULTS = [
    {
        "id": "atlas-127",
        "task": "Fix #127: atlas query --quiet suppresses the query result",
        "outcome": "success",
        "time_minutes": 17,
        "files_read": 18,
        "edits_made": 2,
        "notes": "Agent spent 15 min exploring, 2 min editing. Should have been <2 min with precise file path.",
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
        "id": "fab-swarm-83-wire-impl",
        "task": "Implement fab-swarm#83 `fab-swarm wire`: 4 new modules (cli/wire.rs, commands/wire/mod.rs, commands/wire/mcp_json.rs, commands/wire/settings_merge.rs) + dispatch wiring",
        "outcome": "partial-failure (compile errors + delegation violation)",
        "time_minutes": 35,
        "files_read": 12,
        "edits_made": 8,
        "loc_written_inline": 906,
        "notes": (
            "AGENT WROTE 906 LOC INLINE IN MAIN CONTEXT across 4 new Rust modules + 4 small edits. "
            "Direct violation of CLAUDE.md 'Agent Delegation MANDATORY' (>30 LOC creation/edit → spawn coder agent; multi-file → parallel coder team). "
            "Should have been split into 3 parallel coder agents (one per module) + integration agent for dispatch wiring + reviewer agent. "
            "Net wall-clock: 35 min inline vs estimated ~12 min parallel + 5 min synthesis. "
            "Compile errors surfaced AFTER all 4 modules were written (private-module path, missing `use`) — would have been caught faster with smaller per-agent scope."
        ),
    },
]

REFLECT_PROMPT = """You are optimizing a skill document used by AI coding agents working in the fab-swarm Rust workspace.

## Current Skill Document

{skill_content}

## Rollout Results (agents using this skill)

{rollout_results}

## Task

Produce a PATCHED version of the skill document. The most important issue surfaced by the rollouts:

The `fab-swarm-83-wire-impl` rollout shows the agent wrote 906 LOC INLINE in the main context across 4 new Rust modules — directly violating the parent CLAUDE.md's `Agent Delegation MANDATORY` rule (>30 LOC creation/edit → spawn coder agent; multi-file → parallel coder team).

The current skill doc focuses entirely on BUGFIX workflows (Fix-Type Decision Tree, surgical edits, single-file fixes). It has NO guidance for FEATURE IMPLEMENTATION work that touches multiple files and produces >30 LOC modules. As a result, when the agent encountered a feature-implementation task it had no anti-pattern to invoke, and defaulted to the path-of-least-resistance: inline writes.

Patch the skill document to:
1. Add a top-level **FEATURE IMPLEMENTATION** section as a peer of the existing Bugfix workflow, BEFORE the bugfix section, since feature work is the more common failure mode.
2. Add a hard rule: **>30 LOC of new code OR >1 new file → spawn coder-agent team (parallel where files are independent).** Cite the CLAUDE.md "Agent Delegation MANDATORY" section as the source authority.
3. Add a Decision Tree for feature work: "if task = new CLI subcommand → spawn (cli struct agent, command impl agent, dispatch wiring agent, integration test agent) in parallel; if task = single new module → still spawn one coder agent, NOT inline write".
4. Add a counter-example specifically referencing the fab-swarm-83-wire-impl rollout: "Past failure: agent wrote 906 LOC inline across cli/wire.rs + commands/wire/{{mod,mcp_json,settings_merge}}.rs in 35 min. Should have been 3 parallel coder agents + 1 reviewer (~12 min)."
5. Preserve the existing Bugfix workflow unchanged — it's working as intended for the bugfix rollouts (atlas-143, atlas-113).
6. Keep the doc concise — under ~6KB total. Cut anything that isn't directly load-bearing for either workflow.

Output ONLY the rewritten skill document in markdown. No commentary."""


def call_glm51(prompt: str) -> str:
    url = f"{BASE_URL}/v1/messages"
    headers = {
        "x-api-key": AUTH_TOKEN,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": MODEL,
        "max_tokens": 12000,
        "messages": [{"role": "user", "content": prompt}],
    }
    print(f"Calling GLM-5.1 at {url} model={MODEL} ...", flush=True)
    resp = httpx.post(url, json=payload, headers=headers, timeout=300)
    if resp.status_code != 200:
        print(f"HTTP {resp.status_code}: {resp.text[:1000]}", file=sys.stderr)
        resp.raise_for_status()
    data = resp.json()
    blocks = data.get("content", [])
    text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    return "".join(text_parts)


def main() -> int:
    skill_content = SKILL_PATH.read_text()
    print(f"Read skill: {len(skill_content)} chars from {SKILL_PATH}")

    results_text = "\n".join(
        f"### Task {r['id']}: {r['task']}\n"
        f"- Outcome: {r['outcome']}\n"
        f"- Time: {r['time_minutes']} min\n"
        f"- Files read: {r['files_read']}\n"
        f"- Edits made: {r['edits_made']}\n"
        + (
            f"- LOC written inline: {r['loc_written_inline']}\n"
            if "loc_written_inline" in r
            else ""
        )
        + f"- Notes: {r['notes']}\n"
        for r in ROLLOUT_RESULTS
    )

    prompt = REFLECT_PROMPT.format(
        skill_content=skill_content,
        rollout_results=results_text,
    )

    content = call_glm51(prompt).strip()

    # Strip markdown fences if the model wrapped the output.
    if content.startswith("```markdown"):
        content = content[len("```markdown") :].lstrip("\n")
    elif content.startswith("```"):
        content = content[3:].lstrip("\n")
    if content.endswith("```"):
        content = content[:-3].rstrip("\n")

    output_path = SKILL_DIR / "SKILL_optimized_glm51.md"
    output_path.write_text(content)

    print(f"\nOptimized skill written to: {output_path}")
    print(
        f"Original:  {len(skill_content)} chars / {len(skill_content.splitlines())} lines"
    )
    print(f"Optimized: {len(content)} chars / {len(content.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
