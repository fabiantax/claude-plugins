#!/usr/bin/env python3
"""score_activation.py — score how well Claude ACTIVATED the A2A mesh in a deliberation.

The thing being measured is NOT the mesh internals and NOT whether the agents are
"right" — it is the quality of the *activation*: did Claude's deliberation
procedure (grounding injection + round prompts + handler wiring) produce a
deliberation that was participatory, grounded, convergent, actionable, and
efficient? That is the objective GEPA reflects on (see analyze_activation.py).

Input: the team-channel trace `deliberate.sh` prints (the `### <ts> — <author>`
blocks with `**Observation:** [R1|R2] …`). Works on the full `tee`'d run log too
— non-block lines are ignored.

Five dimensions, each in [0,1]; total = weighted mean:

  participation  did every member post a non-empty position in every round?
  grounding      do positions cite REAL artifacts (issue #N, commit hashes)?
  convergence    did the final round reach an agreed priority (P0–P3)?
  actionability  do positions carry concrete commitments / next-steps / asks?
  efficiency     low noise — no empty consults, no proactive-opener leakage,
                 not bloated.

Usage:
  score_activation.py < trace.txt            # pretty + JSON to stdout
  score_activation.py --json < trace.txt     # JSON only (for analyze_activation.py)
"""

from __future__ import annotations

import json
import re
import sys

WEIGHTS = {
    "participation": 0.20,
    "grounding": 0.30,  # the whole point of Option A — weight it most
    "convergence": 0.20,
    "actionability": 0.20,
    "efficiency": 0.10,
}

# noise signatures that indicate a degraded activation
OPENER_LEAK = re.compile(r"what can i do for you that will make your product", re.I)
EMPTY_MARK = re.compile(r"\(no response[^)]*\)|consult failed", re.I)

ISSUE_RE = re.compile(r"#\d{1,5}\b")
COMMIT_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
PRIORITY_RE = re.compile(r"\bP([0-3])\b")
COMMIT_WORDS = re.compile(
    r"\b(i will|we will|i'll|we'll|commit|commitment|next step|action item|"
    r"need from|i need|require|deliverable|by (eod|tomorrow|sprint)|"
    r"will (trigger|publish|release|update|merge|migrate|run))\b",
    re.I,
)
# A position is actionable if it carries concrete commitments/asks. Beyond the
# first-person phrasing above, agents legitimately phrase commitments as
# third-person assignments ("GraphFusion to publish…", "Localscout will merge…")
# or cross-repo requests ("Request X to…", "pause … until…"). A dedicated
# COMMITMENTS/ASKS/NEXT-STEPS section with bullets is itself the contract's
# actionable payload. Counting only first-person verbs undercounts these.
ASSIGN_RE = re.compile(
    r"\b[A-Za-z][\w-]+ (to|will|must|should) "
    r"(publish|proceed|close|confirm|open|merge|provide|update|migrate|adopt|"
    r"release|validate|verify|schedule|pause|bump|trigger|lockstep|deliver|fix)\b",
    re.I,
)
REQUEST_RE = re.compile(r"\b(request|ask|need)\b.{0,40}\bto\b", re.I)
COMMIT_SECTION = re.compile(
    r"(commitments?|asks?|next[ \-]?steps?|action items?|deliverables?)\s*[:\-]",
    re.I,
)
BULLET_RE = re.compile(r"(?m)^\s*[-*•]|\b\d\.\s")


def is_actionable(body: str) -> bool:
    if COMMIT_WORDS.search(body) or ASSIGN_RE.search(body) or REQUEST_RE.search(body):
        return True
    # a commitments/asks/next-steps section with at least one bullet
    return bool(COMMIT_SECTION.search(body) and BULLET_RE.search(body))


AGREE_RE = re.compile(r"\b(agree|concur|aligned|maintain|endorse)\b", re.I)


def parse_positions(text: str) -> list[dict]:
    """Split the channel into per-entry positions. Returns list of
    {author, round, body}. round ∈ {'R1','R2',''}."""
    # entries start at lines like:  ### <ts> — <author>
    chunks = re.split(r"(?m)^###\s+.*?—\s*(.+?)\s*$", text)
    # re.split with one group -> [pre, author1, body1, author2, body2, ...]
    positions = []
    it = iter(chunks[1:])
    for author in it:
        try:
            body = next(it)
        except StopIteration:
            break
        m = re.search(r"\*\*Observation:\*\*\s*\[(R\d)\]", body)
        rnd = m.group(1) if m else ""
        # strip the markdown header fields, keep the observation text
        obs = re.split(r"\*\*Observation:\*\*", body, maxsplit=1)
        obs_text = obs[1] if len(obs) > 1 else body
        positions.append(
            {"author": author.strip(), "round": rnd, "body": obs_text.strip()}
        )
    return positions


def _nonempty(p: dict) -> bool:
    b = p["body"]
    return bool(b) and not EMPTY_MARK.search(b) and len(b.strip()) > 40


def score(text: str) -> dict:
    positions = parse_positions(text)
    authors = sorted({p["author"] for p in positions})
    rounds = sorted({p["round"] for p in positions if p["round"]})
    n_auth = len(authors) or 1
    n_round = len(rounds) or 1

    if not positions:
        zero = {k: 0.0 for k in WEIGHTS}
        return {
            "dimensions": zero,
            "total": 0.0,
            "notes": ["no positions parsed"],
            "authors": [],
            "rounds": [],
            "n_positions": 0,
        }

    notes: list[str] = []

    # participation: filled, non-empty slots / expected slots
    expected = n_auth * n_round
    filled = sum(1 for p in positions if p["round"] and _nonempty(p))
    participation = min(1.0, filled / expected) if expected else 0.0
    empties = [p["author"] for p in positions if p["round"] and not _nonempty(p)]
    if empties:
        notes.append(f"empty/short positions: {empties}")

    # grounding: fraction of non-empty positions citing >=1 real artifact
    grounded = 0
    total_cites = 0
    for p in positions:
        if not _nonempty(p):
            continue
        cites = len(ISSUE_RE.findall(p["body"])) + len(
            [c for c in COMMIT_RE.findall(p["body"]) if not c.isdigit()]
        )
        total_cites += cites
        if cites > 0:
            grounded += 1
    ne = [p for p in positions if _nonempty(p)] or [None]
    grounding = grounded / len(ne) if ne[0] else 0.0
    notes.append(
        f"artifact citations: {total_cites} across {grounded}/{len(ne)} positions"
    )

    # convergence: among final-round positions, do they agree on a priority?
    final = rounds[-1] if rounds else ""
    finals = [p for p in positions if p["round"] == final and _nonempty(p)]
    prios = []
    for p in finals:
        m = PRIORITY_RE.findall(p["body"])
        if m:
            prios.append(m[0])  # first stated priority
    if prios:
        top = max(set(prios), key=prios.count)
        agree_ratio = prios.count(top) / len(finals) if finals else 0.0
        # bonus for explicit agreement language
        agree_lang = sum(1 for p in finals if AGREE_RE.search(p["body"])) / len(finals)
        convergence = 0.7 * agree_ratio + 0.3 * agree_lang
        notes.append(
            f"final-round priorities {prios} -> consensus P{top} ({agree_ratio:.0%})"
        )
    else:
        convergence = 0.0
        notes.append("no explicit P0–P3 priority in final round")

    # actionability: fraction of non-empty positions with concrete commitment/ask
    actionable = sum(1 for p in positions if _nonempty(p) and is_actionable(p["body"]))
    actionability = actionable / len(ne) if ne[0] else 0.0

    # efficiency: start at 1, subtract noise penalties
    eff = 1.0
    leaks = sum(1 for p in positions if OPENER_LEAK.search(p["body"]))
    if leaks:
        eff -= 0.15 * leaks
        notes.append(f"proactive-opener leak in {leaks} position(s)")
    if empties:
        eff -= 0.20 * len(empties)
    avg_len = sum(len(p["body"]) for p in positions) / len(positions)
    if avg_len > 3500:
        eff -= 0.15
        notes.append(f"verbose positions (avg {int(avg_len)} chars)")
    efficiency = max(0.0, eff)

    dims = {
        "participation": round(participation, 3),
        "grounding": round(grounding, 3),
        "convergence": round(convergence, 3),
        "actionability": round(actionability, 3),
        "efficiency": round(efficiency, 3),
    }
    total = round(sum(dims[k] * WEIGHTS[k] for k in WEIGHTS), 3)
    return {
        "dimensions": dims,
        "weights": WEIGHTS,
        "total": total,
        "authors": authors,
        "rounds": rounds,
        "n_positions": len(positions),
        "notes": notes,
    }


def main() -> int:
    json_only = "--json" in sys.argv[1:]
    text = sys.stdin.read()
    result = score(text)
    if json_only:
        print(json.dumps(result, indent=2))
        return 0
    d = result["dimensions"]
    print("=== Mesh-activation score ===")
    print(
        f"authors: {result['authors']}  rounds: {result['rounds']}  "
        f"positions: {result['n_positions']}"
    )
    for k in WEIGHTS:
        bar = "█" * int(d[k] * 20)
        print(f"  {k:<14} {d[k]:.3f}  {bar}")
    print(f"  {'TOTAL':<14} {result['total']:.3f}")
    print("notes:")
    for n in result["notes"]:
        print(f"  - {n}")
    print()
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
