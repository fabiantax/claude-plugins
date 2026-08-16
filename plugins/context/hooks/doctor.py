#!/usr/bin/env python3
"""context doctor — what does this repo's CLAUDE.md cost, and what of it could be
enforced instead of stated?

Run:  python3 doctor.py [path/to/CLAUDE.md]

WHY THE HEURISTIC CHANGED (and what the first one got wrong)
------------------------------------------------------------
v1 counted prohibition words per section and reported the whole SECTION's tokens
as "mechanisable". Piloted on a real repo it claimed **61% of the file**. The
honest answer, after auditing every candidate and shipping the survivors, was
**five rules**. Two compounding errors:

  1. Converting one rule inside a 2,881-token section does not free 2,881
     tokens. It frees the rule's own lines. Section-level attribution
     overstates by the ratio of section size to rule size — here, ~50x.
  2. A prohibition is only mechanisable if it names something a regex can match
     in a command: a command, a flag, a path. "Never deploy an IS-only model",
     "check existing before building new" and "escalate to the team, not the
     user" are all prohibitions and none is a predicate.

So v2 works at LINE level and requires a command-shaped literal. It reports a
count of candidate rules, not a percentage of the file, because the count is
what a human then has to audit.

**This is still an upper bound.** On the pilot it surfaced 18 candidates of
which 5 survived audit — the rest were mentions, judgement in command clothing,
or rules needing context a command line does not carry. Treat the output as a
worklist, not a verdict.

CALIBRATION (the numbers this was tuned against, so a future change can be
checked rather than guessed):

    fab-trader   18 candidates, 5/5 of the rules that shipped after audit
    strix core    1 candidate  — a known false positive, see below
    fab-swarm     9 candidates

Recall was chosen over precision because the output is a list a human reads. A
16-candidate variant missed one shipped rule; a 24-candidate variant caught it
but added eight more to audit. 18 is the middle that keeps 5/5.

KNOWN FALSE-POSITIVE CLASS: a filename in prose. The strix core's single hit is
`DECISIONS.md` in "record the decision in the commit/issue (or DECISIONS.md)" —
a filename, obliging language, and no command anywhere. Accepted deliberately:
dropping the filename shape would lose a real shipped rule (the *_SUMMARY.md
cruft ban) to save one easily-dismissed line.
"""
from __future__ import annotations

import os
import re
import sys

TOK = lambda s: -(-len(s) // 4)

# A rule is only a candidate if it BOTH obliges and names something matchable.
# Calibration caught a real miss here: the pilot's highest-value rule reads
# "Live mode REQUIRES an additional LIVE_TRADING_CONFIRMED=yes env", and an
# earlier version matched only "required", so the one capital-risk rule in the
# file was the one it failed to surface. Inflections matter more than breadth.
OBLIGE = re.compile(
    r"\b(never|must not|must|do not|don'?t|always|forbidden"
    r"|require[sd]?|refuse|only after|mandatory)\b"
    # Emphatic "**No X**" is a common rule form. Scoped to the bolded/bulleted
    # shape rather than every "no": bare \bno\b lifted fab-trader's candidate
    # count 16 -> 24 for one extra real rule, which is a worklist a human then
    # has to read.
    r"|\*\*No\b|^\s*[-*]\s*No\b", re.I | re.M)

# Command-shaped: a backticked token that looks like a command, flag or path —
# not prose in backticks. Requires a flag, a slash, or a command-ish head token.
BACKTICK = re.compile(r"`([^`\n]{2,80})`")
CMD_SHAPE = re.compile(r"""
    ^--?[a-zA-Z][\w-]*            # a flag:            --isolated, -f
  | ^[a-z][\w.-]*\s+[a-z-]        # a command + arg:   git push, uv run
  | ^[a-z][\w.-]*/[\w./*-]+       # a path:            scripts/train.py
  | ^[A-Z_]{3,}=                  # an env assignment: ENGINE_MODE=
  | ^\*?[\w.*-]+\.(md|json|toml|ya?ml|rs|py|ts|sh)$   # a file or glob: *_SUMMARY.md
""", re.X)


def is_candidate(line: str):
    """-> the command-shaped literals that make this line mechanisable, or []."""
    if not OBLIGE.search(line):
        return []
    return [t for t in BACKTICK.findall(line) if CMD_SHAPE.search(t)]


def sections(text):
    lines = text.split("\n")
    fence, marks = None, []
    for i, l in enumerate(lines):
        s = l.lstrip()
        if fence is None:
            m = re.match(r"(`{3,}|~{3,})", s)
            if m:
                fence = m.group(1)[0]
                continue
        else:
            if re.match(r"(`{3,}|~{3,})\s*$", s) and s[0] == fence:
                fence = None
            continue
        if l.startswith("## "):
            marks.append(i)
    if not marks:
        return [], lines
    out = []
    for a, b in zip(marks, marks[1:] + [len(lines)]):
        out.append((lines[a][3:].strip(), lines[a:b]))
    return out, lines


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        path = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd(),
                            "CLAUDE.md")
    if not os.path.isfile(path):
        print("context doctor: no CLAUDE.md at %s" % path)
        return 1
    text = open(path, encoding="utf-8", errors="replace").read()
    secs, _ = sections(text)
    total = TOK(text)

    print("context doctor — %s\n" % path)
    print("  resident cost: %d tok, every session, every task in this repo" % total)
    if not secs:
        print("  (no H2 sections)")
        return 0

    print("\n  where it sits:")
    for title, body in sorted(secs, key=lambda s: -TOK("\n".join(s[1])))[:8]:
        t = TOK("\n".join(body))
        print("   %6d tok  %3.0f%%  %s" % (t, 100 * t / total, title[:52]))

    # --- candidate rules, at LINE level -------------------------------------
    cands = []
    for title, body in secs:
        for l in body:
            lits = is_candidate(l)
            if lits:
                cands.append((title, l.strip(), lits))

    cand_tok = sum(TOK(l) for _, l, _ in cands)
    print("\n  ENFORCEABLE-RULE CANDIDATES: %d" % len(cands))
    print("  combined cost of those lines: %d tok (%.1f%% of the file)"
          % (cand_tok, 100 * cand_tok / total))
    print("  ^ this is the realistic ceiling for conversion, not the section total.")
    for title, line, lits in cands[:12]:
        print("\n   [%s]" % title[:44])
        print("     %s" % line[:104])
        print("     -> %s" % ", ".join("`%s`" % x for x in lits[:3]))
    if len(cands) > 12:
        print("\n   ... and %d more" % (len(cands) - 12))

    g = os.path.join(os.path.dirname(os.path.abspath(path)), ".claude", "guards.toml")
    print("\n  guards declared here: %s"
          % (("yes — %d rules" % len(re.findall(r"^id = ", open(g).read(), re.M)))
             if os.path.isfile(g) else "no (plugin is inert for this repo)"))

    print("""
  READ THIS BEFORE CONVERTING ANYTHING
  These are candidates, not conclusions. On the pilot repo this surfaced ~15 and
  5 survived audit; the rest were prose that merely NAMED a command, judgement
  wearing command clothing, or rules needing context a command line does not
  carry. Two hard rules from that pilot:
    * Screen every pattern against real commands from THIS repo's transcripts
      before shipping it. One draft rule there matched 213 commands because the
      command name was also a directory.
    * Anchor to an invocation position, never a bare mention, or writing docs
      about the rule will trip it.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
