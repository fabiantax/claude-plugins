#!/usr/bin/env python3
"""context split — move reference out of a CLAUDE.md, keep the rules resident.

The doctor tells you which rules could be *enforced*. This handles the other
half: the reference material that costs you tokens in every session and earns
them back only in the sessions that touch it.

    python3 split.py CLAUDE.md                       # inventory: what's in there
    python3 split.py CLAUDE.md --core-ids core.txt \\
        --out-core CLAUDE.md --out-sidecar docs/claude-md-sections.md
    python3 split.py CLAUDE.md --assert-resident insurance.txt   # regression check

THE ONLY QUESTION WORTH ASKING PER SECTION
------------------------------------------
Not "is this important" — all of it is. Ask what the section costs you when you
DON'T read it:

  RESIDENT   a rule you can violate WITHOUT knowing to look it up. Capital
             safety, silent-corruption traps, standing authorizations, honesty
             gates. Retrieval cannot save you from a rule you never thought to
             fetch, so no index and no search fixes a wrong call here.
  SIDECAR    what you would naturally look up once the task touches it.
             Inventories, layouts, tool post-mortems, orchestration mechanics.

Insurance is a property of a RULE, not of a section — a 2,000-token reference
section can contain one line you must never lose. Hence H3 granularity and the
inventory mode: look at the chunks before choosing.

WHY VERBATIM, AT H3, AND NO FINER
---------------------------------
Every moved chunk is copied byte-for-byte. That is what makes the result
checkable instead of trusted: after the split, every non-blank line of the
original must appear in exactly one of the two files. Finer line-level surgery
compresses more but cannot be verified this way, and an unverifiable split of a
file full of hard-won safety rules is not worth the tokens it saves.

--assert-resident is the part worth wiring into CI. The split is a one-off; the
risk is permanent, because the next person to edit the file can quietly move a
capital rule into the sidecar and nothing will complain.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter

TOK = lambda s: -(-len(s) // 4)
FENCE = re.compile(r"(`{3,}|~{3,})")


def chunks(text, split_h2=()):
    """-> (preamble, [(h2_title, [(chunk_id, lines)])]), fence-aware.

    Headings inside fenced code blocks are NOT headings. Example blocks that
    show a "## Context" prompt template are common in these files, and counting
    them silently misattributes every rule that follows.
    """
    lines = text.split("\n")
    fence, heads = None, []
    for i, l in enumerate(lines):
        s = l.lstrip()
        if fence is None:
            m = FENCE.match(s)
            if m:
                fence = m.group(1)[0]
                continue
        else:
            if re.match(r"(`{3,}|~{3,})\s*$", s) and s[0] == fence:
                fence = None
            continue
        if l.startswith("## "):
            heads.append((i, 2, l[3:].strip()))
        elif l.startswith("### "):
            heads.append((i, 3, l[4:].strip()))

    h2s = [h for h in heads if h[1] == 2]
    if not h2s:
        return lines, []
    out = []
    for k, (a, _, title) in enumerate(h2s):
        b = h2s[k + 1][0] if k + 1 < len(h2s) else len(lines)
        subs = [h for h in heads if h[1] == 3 and a < h[0] < b]
        if title not in split_h2 or not subs:
            out.append((title, [(title, lines[a:b])]))
            continue
        parts = [(title, lines[a:subs[0][0]])]
        for j, (sa, _, st) in enumerate(subs):
            sb = subs[j + 1][0] if j + 1 < len(subs) else b
            parts.append(("%s > %s" % (title, st), lines[sa:sb]))
        out.append((title, parts))
    return lines[: h2s[0][0]], out


def split(text, core_ids, link):
    """-> (core, sidecar, side_titles). Chunks not named in core_ids move out."""
    split_h2 = {cid.split(" > ")[0] for cid in core_ids if " > " in cid}
    pre, sections = chunks(text, split_h2)
    core_c, side_c, side_titles = [], [], []
    for h2, parts in sections:
        kept = [p for p in parts if p[0] in core_ids]
        gone = [p for p in parts if p[0] not in core_ids]
        head = ["## " + h2]
        # A split section's H2 heading is duplicated so each file reads
        # standalone; the conservation check declares it rather than hiding it.
        if kept:
            if kept[0][0] != h2:
                core_c += [head, [""]]
            core_c += [ls for _, ls in kept]
        if gone:
            if gone[0][0] != h2:
                side_c += [head, [""]]
            side_c += [ls for _, ls in gone]
            side_titles.append(h2)

    flat = lambda cs: [l for c in cs for l in c]
    sidecar = (
        "# Subsystem reference\n\n"
        "Sections moved out of the resident `CLAUDE.md` so they cost nothing until\n"
        "a task touches them. Nothing here was rewritten — every section is verbatim.\n\n"
        "Rules that fire *without* being looked up stayed in `CLAUDE.md`: retrieval\n"
        "cannot save you from a rule you never thought to fetch.\n\n---\n\n"
        + "\n".join(flat(side_c)).rstrip() + "\n"
    )
    banner = (
        "> **This file is the resident core, not the whole manual.** The subsystem\n"
        "> reference below is NOT loaded — read `%s` when a task touches one of\n"
        "> these, and read it *before* assuming a rule is unwritten:\n>\n" % link
        + "\n".join("> - %s" % t for t in side_titles)
        + "\n>\n> Reading it costs ~%d tokens, so read it when a task touches one of\n"
          "> the above, not by default.\n" % TOK(sidecar)
    )
    core = ("\n".join(pre).rstrip() + "\n\n" + banner + "\n"
            + "\n".join(flat(core_c)).rstrip() + "\n")
    return core, sidecar, side_titles


def conservation(original, *produced):
    """-> lines of `original` present in none of `produced` (blank lines ignored)."""
    got = Counter()
    for p in produced:
        got += Counter(p.split("\n"))
    return {l: n for l, n in (Counter(original.split("\n")) - got).items() if l.strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--core-ids", help="file of chunk ids to keep resident, one per line")
    ap.add_argument("--out-core")
    ap.add_argument("--out-sidecar")
    ap.add_argument("--link", default="docs/claude-md-sections.md",
                    help="path the core's banner points at")
    ap.add_argument("--assert-resident", metavar="FILE",
                    help="file of strings that MUST still be in the core; "
                         "the check worth wiring into CI")
    a = ap.parse_args()
    text = open(a.path, encoding="utf-8").read()

    # --- regression check: are the insurance rules still resident? -----------
    if a.assert_resident:
        probes = [l.rstrip("\n") for l in open(a.assert_resident, encoding="utf-8")
                  if l.strip() and not l.startswith("#")]
        missing = [p for p in probes if p not in text]
        for p in missing:
            print("EVICTED: %s" % p[:100])
        print("%d/%d resident in %s" % (len(probes) - len(missing), len(probes), a.path))
        return 1 if missing else 0

    # --- inventory -----------------------------------------------------------
    if not a.core_ids:
        _, sections = chunks(text, {t for t, _ in chunks(text)[1]})
        print("%s — %d tok resident, every session\n" % (a.path, TOK(text)))
        print("Chunk ids (pass the ones to KEEP via --core-ids):\n")
        for _, parts in sections:
            for cid, ls in parts:
                body = "\n".join(ls)
                if not body.strip():
                    continue
                print("%6d tok  %s" % (TOK(body), cid))
        print("\nKeep a chunk resident if a rule in it fires WITHOUT being looked up.")
        return 0

    # --- split ---------------------------------------------------------------
    core_ids = {l.strip() for l in open(a.core_ids, encoding="utf-8")
                if l.strip() and not l.startswith("#")}
    known = {cid for _, parts in chunks(text, {c.split(" > ")[0] for c in core_ids
                                               if " > " in c})[1] for cid, _ in parts}
    for cid in sorted(core_ids - known):
        print("WARNING: --core-ids names a chunk that does not exist: %s" % cid,
              file=sys.stderr)

    core, sidecar, _ = split(text, core_ids, a.link)
    lost = conservation(text, core, sidecar)
    print("original %d tok -> core %d tok (-%.0f%%), sidecar %d tok"
          % (TOK(text), TOK(core), 100 * (1 - TOK(core) / TOK(text)), TOK(sidecar)))
    print("lines lost: %d" % len(lost))
    for l in list(lost)[:10]:
        print("   LOST: %s" % l[:100])
    if lost:
        print("\nREFUSING TO WRITE — a verbatim split must lose nothing.")
        return 1
    if a.out_core and a.out_sidecar:
        open(a.out_core, "w", encoding="utf-8").write(core)
        open(a.out_sidecar, "w", encoding="utf-8").write(sidecar)
        print("wrote %s + %s" % (a.out_core, a.out_sidecar))
    else:
        print("(dry run — pass --out-core and --out-sidecar to write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
