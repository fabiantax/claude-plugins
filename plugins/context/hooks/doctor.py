#!/usr/bin/env python3
"""context doctor — what does this repo's CLAUDE.md actually cost, and what of it
could be enforced instead of stated?

Run:  python3 doctor.py [path/to/CLAUDE.md]

Reports three things and no more, because the point is a decision, not a report:

  1. Resident cost. Every token here is paid in every session on this repo.
  2. Section breakdown. Where the cost actually sits — usually one or two
     sections dominate, and they are rarely the ones people expect.
  3. Mechanisable share. Sections whose content is largely PROHIBITIONS
     ("never", "must not", "do not") are candidates to become guards in
     .claude/guards.toml, where they cost zero resident tokens and are enforced
     categorically rather than followed probabilistically.

The mechanisable heuristic is deliberately crude and is a PROMPT FOR REVIEW, not
a verdict. It counts imperative-prohibition lines; a section full of "never"
sentences is a strong candidate, but only a human can say whether a rule is a
predicate over a command or a matter of judgement. Judgement does not mechanise
— authorisation tiers, working principles and taste stay prose.
"""
from __future__ import annotations

import os
import re
import sys

TOK = lambda s: -(-len(s) // 4)
PROHIBIT = re.compile(
    r"\b(never|must not|do not|don't|no longer|forbidden|refuse|prohibited)\b", re.I)


def sections(text):
    lines = text.split("\n")
    fence = None
    marks = []
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
        return []
    out = []
    bounds = marks + [len(lines)]
    for a, b in zip(bounds, bounds[1:]):
        out.append((lines[a][3:].strip(), "\n".join(lines[a:b])))
    return out


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        path = os.path.join(project, "CLAUDE.md")
    if not os.path.isfile(path):
        print("context doctor: no CLAUDE.md at %s" % path)
        return 1
    text = open(path, encoding="utf-8", errors="replace").read()
    secs = sections(text)
    total = TOK(text)

    print("context doctor — %s\n" % path)
    print("  resident cost: %d tok, every session, every task in this repo" % total)
    if not secs:
        print("  (no H2 sections — nothing to break down)")
        return 0

    print("\n  where it sits:")
    mech_tok = 0
    rows = sorted(secs, key=lambda s: -TOK(s[1]))
    for title, body in rows[:10]:
        t = TOK(body)
        hits = len(PROHIBIT.findall(body))
        dens = hits / max(1, body.count("\n"))
        flag = ""
        if hits >= 3 and dens > 0.04:
            flag = "  <- prohibition-dense, candidate for guards"
            mech_tok += t
        print("   %6d tok  %3.0f%%  %-46s%s" % (t, 100 * t / total, title[:46], flag))
    if len(rows) > 10:
        print("   %6d tok         ... and %d more sections"
              % (sum(TOK(b) for _, b in rows[10:]), len(rows) - 10))

    print("\n  mechanisable (prohibition-dense): %d tok = %.0f%% of the file"
          % (mech_tok, 100 * mech_tok / total))
    print("  Those are candidates for .claude/guards.toml — enforced at the tool")
    print("  layer, zero resident tokens. Judgement (authorisation tiers, working")
    print("  principles, taste) does NOT mechanise and should stay prose.")

    g = os.path.join(os.path.dirname(os.path.abspath(path)), ".claude", "guards.toml")
    print("\n  guards declared here: %s" % ("yes — " + g if os.path.isfile(g)
                                            else "no (plugin is inert for this repo)"))
    print("\n  Heuristic, not a verdict: it counts prohibition words. Read the")
    print("  flagged sections before moving anything.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
