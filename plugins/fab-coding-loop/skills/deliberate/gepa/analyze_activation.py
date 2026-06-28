#!/usr/bin/env python3
"""analyze_activation.py — GEPA analyze-first over a mesh-activation trace.

GEPA's core move is *reflection*: run a candidate, read the full execution trace,
let an LLM diagnose in natural language WHY it scored the way it did, and propose
a targeted mutation. This script does exactly one such reflection step — the
"analyze-first" pass — over Claude's mesh-ACTIVATION procedure:

  seed procedure (procedure.md, the textual artifact)
    + the deliberation trace it produced
    + score_activation.py's per-dimension scores & notes  ← Actionable Side Info
  --> local_reflection_lm (:8003 35B, generous token budget)
  --> { diagnosis, proposed improved procedure }

This is the analysis step, NOT a full optimize loop: it tells you what to change
and why before you spend rollouts. Feed `proposed_procedure` back as the next
seed (or into gepa.optimize_anything with this scorer as evaluator) to iterate.

Usage:
  analyze_activation.py --trace /tmp/deliberate-grounded-trace.txt
  analyze_activation.py --trace t.txt --procedure procedure.md --out report.md
Reflection model: GEPA_LLAMA_BASE (default here points at the running :8003).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# reflect on the running batched 35B (:8003) — same model the mesh uses, already up.
os.environ.setdefault("GEPA_LLAMA_BASE", "http://127.0.0.1:8003/v1")
os.environ.setdefault("GEPA_REFLECT_MAX_TOKENS", "8192")

sys.path.insert(0, str(HERE))  # score_activation
sys.path.insert(0, os.path.expanduser("~/.claude/skills/gepa"))  # local_lm

from score_activation import score, WEIGHTS  # noqa: E402
from local_lm import local_reflection_lm  # noqa: E402

REFLECT_PROMPT = """You are GEPA's reflection module. You optimize the PROCEDURE an \
AI coordinator uses to ACTIVATE a multi-agent A2A mesh for a cross-repository \
deliberation. You are NOT judging whether the agents are correct, and NOT changing \
the mesh internals — only the coordinator's activation procedure (its grounding \
strategy and round prompts) so the next run scores higher.

The procedure is scored on five dimensions (weights in []):
- participation [{w_participation}]: every member posts a substantive position every round
- grounding [{w_grounding}]: positions cite REAL artifacts (issue #N, commit hashes) from the injected facts
- convergence [{w_convergence}]: the final round reaches an agreed P0–P3 priority
- actionability [{w_actionability}]: positions carry concrete commitments / next-steps / asks
- efficiency [{w_efficiency}]: low noise — no empty consults, no boilerplate/opener leakage, not bloated

## CURRENT PROCEDURE (the candidate to improve)
{procedure}

## TRACE IT PRODUCED (the deliberation channel)
{trace}

## AUTOMATED SCORES (Actionable Side Information)
{scores}

## YOUR TASK
1. DIAGNOSIS: For each dimension that is below 1.0 (and any latent risk even at \
1.0), explain in concrete terms WHAT in the trace caused it and WHICH part of the \
procedure is responsible. Be specific — quote the offending trace text.
2. PROPOSED PROCEDURE: Rewrite the procedure to fix the highest-leverage problems. \
Keep what works (do not regress grounding). Make targeted, minimal edits — e.g. an \
explicit instruction to suppress the proactive-opener boilerplate, a tighter output \
contract, a length cap. Output the FULL revised procedure in the same sectioned \
format so it can be dropped in as the next seed.

Format your answer as:
### DIAGNOSIS
<per-dimension>
### PROPOSED PROCEDURE
<full revised procedure>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", required=True, help="deliberation trace file")
    ap.add_argument("--procedure", default=str(HERE / "procedure.md"))
    ap.add_argument(
        "--out", default="", help="write report here (default: stdout only)"
    )
    args = ap.parse_args()

    trace = Path(args.trace).read_text()
    procedure = Path(args.procedure).read_text()
    scores = score(trace)

    print("=== Activation scores ===", file=sys.stderr)
    print(json.dumps(scores["dimensions"], indent=2), file=sys.stderr)
    print(f"total: {scores['total']}", file=sys.stderr)

    # trim the trace if huge so the reflection prompt itself fits the 8192 slot
    trace_for_prompt = trace if len(trace) < 12000 else trace[:12000] + "\n…[truncated]"

    prompt = REFLECT_PROMPT.format(
        w_participation=WEIGHTS["participation"],
        w_grounding=WEIGHTS["grounding"],
        w_convergence=WEIGHTS["convergence"],
        w_actionability=WEIGHTS["actionability"],
        w_efficiency=WEIGHTS["efficiency"],
        procedure=procedure,
        trace=trace_for_prompt,
        scores=json.dumps(
            {
                "dimensions": scores["dimensions"],
                "total": scores["total"],
                "notes": scores["notes"],
            },
            indent=2,
        ),
    )

    print(
        f"Reflecting via local_reflection_lm ({os.environ['GEPA_LLAMA_BASE']})…",
        file=sys.stderr,
    )
    reflection = local_reflection_lm(prompt).strip()

    report = (
        f"# Mesh-activation GEPA analysis\n\n"
        f"trace: {args.trace}\n"
        f"scores: {json.dumps(scores['dimensions'])}  total={scores['total']}\n"
        f"notes: {scores['notes']}\n\n"
        f"{reflection}\n"
    )
    if args.out:
        Path(args.out).write_text(report)
        print(f"wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
