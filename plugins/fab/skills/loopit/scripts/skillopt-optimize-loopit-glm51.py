#!/usr/bin/env python3
"""One-shot SkillOpt-style optimizer for the /loopit skill via GLM-5.1.

Same pattern as ~/.claude/skills/skillopt-rust-bugfix/scripts/skillopt-optimize-skill-glm51.py —
honest framing: NOT the real SkillOpt training loop, just a single LLM call
with structured rollout data + reflect prompt. The /loopit skill has no
concrete ground-truth scoring signal (rust-bugfix had broken_file matches);
a real SkillOpt env adapter for loopit would need an LLM judge for "is this
items list a reasonable decomposition" — which is itself one-shot reflect.

Reads ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN from env. Source them via:
  cd <repo-with-.claude/settings.local.json>
  source <(jq -r '.env | to_entries[] | "export \\(.key)=\\(.value | tojson)"' .claude/settings.local.json)
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
        "       run this from a repo whose .claude/settings.local.json defines them,\n"
        "       and source them first (see module docstring for the one-liner).",
        file=sys.stderr,
    )
    sys.exit(1)

# Real rollout data — observed loopit runs with what worked vs what bogged down.
# The skillopt-phase1-env entry below is verbatim from this session's
# scratchpad, so the optimization signal is grounded in actual experience.
ROLLOUT_RESULTS = [
    {
        "id": "skillopt-phase1-env",
        "goal": "Build a custom _fab_swarm_rust SkillOpt env adapter that runs skillopt-train end-to-end against Z.AI's OpenAI-compat endpoint",
        "outcome": "converged",
        "items_planned": 5,
        "iterations": 7,
        "wall_clock_min": 95,
        "anti_patterns_hit": [
            "L1-recon read 1000+ lines of officeqa/rollout.py inline in main context — the rust-bugfix SKILL.md explicitly prohibits this (<300 line threshold), but loopit doesn't surface it. Should have delegated to Explore agent.",
            "L4-run produced 6 sub-iterations because each YAML config error was treated as a separate 'fix this single error' loop. Should have been ONE item: 'discover full required-cfg surface via grep config.py + trainer.py BEFORE first run'. Wasted ~30 min of wall-clock + 6 separate LLM-loaded iterations.",
            "Items L4 + L5 were under-specified — 'capture full output' and 'verify artifact' had no pass/fail gate beyond 'exists', so we couldn't tell at item-creation time whether 'analyst proposed 0 edits' counted as success or failure.",
        ],
        "patterns_that_worked": [
            "L2-parallel-impl split into 3 coder agents (A=dataloader+evaluator, B=rollout, C=adapter+train_patch) running in parallel. All 3 completed within ~3 min and verified independently. The split was decided by the just-adopted rust-bugfix SKILL.md decision tree, not by loopit.",
            "ADR file captured the 3 non-trivial decisions (phase split, site-packages-vs-fork, shared auth token). ADR-003 explicitly said 'pending validation in L4' — and the validation came naturally during L4. That ADR-shape (decision + pending evidence) carried real load.",
            "Findings stream captured surprising knowledge each iteration — e.g., 'skillopt/prompts/analyst_success.md AREN'T shipped in the wheel (installation gap)'. These would have been re-discovered every session without the scratchpad.",
        ],
        "notes": (
            "Net: the loop converged but spent a lot of wall-clock in L4 because the items were too coarse. "
            "A 'pre-flight: enumerate full cfg surface' item would have collapsed L4#1-6 into one iteration. "
            "Also: the SKILL.md doesn't say anything about delegating long Read calls — this should be a hard rule like rust-bugfix has."
        ),
    },
    {
        "id": "gepa-epic-116-style",
        "goal": "Drive an autonomous GEPA optimisation epic end-to-end (multi-session, persistent learning)",
        "outcome": "converged across multiple sessions",
        "items_planned": "~15 across the epic",
        "iterations": "~30+",
        "wall_clock_min": "multi-day",
        "anti_patterns_hit": [
            "Re-discovery of conventions every session — the scratchpad findings stream worked, but ADR was used too rarely. Decisions like 'use sha256-trunc as candidate hash' had to be re-litigated multiple times when re-loaded in a fresh session.",
        ],
        "patterns_that_worked": [
            "Gitea issue sync per item — every item had a `gitea: #N` tag so progress was visible beyond the loopit scratchpad. PR auto-close + issue auto-close worked.",
            "Long-horizon resilience — the loop survived 3 session compactions because scratchpad + ADR were both committed to git. Cold-start of iteration N+1 picked up exactly where N left off.",
        ],
        "notes": "The Gitea integration in /loopit was load-bearing for multi-session work — without it, every fresh session re-discovers what's already filed.",
    },
]

REFLECT_PROMPT = """You are optimizing the /loopit skill document. /loopit is a Claude Code skill that drives iterative goal achievement with persistent findings + ADR across sessions.

## Current Skill Document

{skill_content}

## Real rollout observations

{rollout_results}

## Task

Produce a PATCHED version of the skill document. Focus on the SPECIFIC failure patterns surfaced by the rollouts above, not generic improvements. Top issues to address:

1. **Coarse items waste wall-clock** — the `skillopt-phase1-env` rollout collapsed because L4 had 6 sub-iterations of "fix one YAML error". The current SKILL.md doesn't tell the agent to **enumerate full requirements surface before first execution**. Add a **Pre-flight gate**: before running any new command for the first time, the iteration must `grep` / `Read` the full required-input surface (config schema, abstract method signatures, required env vars). This collapses N error-driven sub-iterations into 1 informed iteration.

2. **Inline long Reads** — L1 read 1000+ lines of reference code in the main context, violating the just-adopted parent skill (rust-bugfix's `<300 lines = delegate to Explore`). The current loopit SKILL.md doesn't reinforce that delegation rule. Add: **Reading >300 lines = delegate to Explore agent, even if it's "just recon"**.

3. **Items without pass/fail gates** — L5 was "verify artifact exists" with no criterion beyond filesystem existence. Even when "0 edits proposed by analyst" we couldn't tell if that meant success or failure. Add a rule: **every item must define an OBSERVABLE pass/fail gate at creation time, not at completion time**. "Exists" is not a gate.

4. **ADR underuse on multi-session work** — gepa-epic-116 had decisions re-litigated across sessions. Add: **ADR threshold = anything that took >2 minutes of weighing alternatives**. Easier ADR creation surfaces more decisions before they decay.

5. **Reinforce what worked** — the parallel-agent split (3 coder agents per L2 item) and the Gitea sync were load-bearing wins. The current SKILL.md mentions them but they're buried. Surface them in the **per-iteration cycle** section with concrete invocations.

Constraints:
- Keep all existing safety rails, anti-patterns, and Gitea integration sections.
- Don't remove the dynamic workflow execution section.
- Maintain the example sections (auto-seed, re-invocation) — they're load-bearing for first-time users.
- Total length should stay near current size (around 300 lines / 16KB) — additions OK, but cut filler if needed.

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
        "max_tokens": 16000,
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
        f"### Loopit run: {r['id']}\n"
        f"- Goal: {r['goal']}\n"
        f"- Outcome: {r['outcome']}\n"
        f"- Items planned: {r['items_planned']}\n"
        f"- Iterations actual: {r['iterations']}\n"
        f"- Wall clock: {r['wall_clock_min']} min\n"
        f"- Anti-patterns hit:\n"
        + "\n".join(f"    - {ap}" for ap in r["anti_patterns_hit"])
        + "\n"
        "- Patterns that worked:\n"
        + "\n".join(f"    - {p}" for p in r["patterns_that_worked"])
        + "\n"
        f"- Notes: {r['notes']}\n"
        for r in ROLLOUT_RESULTS
    )

    prompt = REFLECT_PROMPT.format(
        skill_content=skill_content,
        rollout_results=results_text,
    )

    content = call_glm51(prompt).strip()

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
