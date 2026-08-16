#!/usr/bin/env python3
"""Tests for the CLAUDE.md splitter.

What these exist to prevent: a split that looks fine and quietly drops a line.
The whole value of moving text verbatim is that it can be *checked*, so the
conservation property is the thing under test, not the token savings.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import split as S  # noqa: E402


DOC = """# Manual

Intro line.

## Rules

Never deploy on Friday.

## Layout

- `src/` — code

## Tooling

Preamble to tooling.

### Broken thing

Long post-mortem.

### The rule that survived

Grep for the shape.
"""


def ids(text, split_h2=()):
    _, secs = S.chunks(text, split_h2)
    return [cid for _, parts in secs for cid, _ in parts]


# --- chunking -----------------------------------------------------------------

def test_h3_chunks_appear_only_for_requested_sections():
    """WHY: H3 granularity is opt-in per section. Splitting everything would make
    the id list unusable on a large file, and splitting nothing would force a
    2,000-token reference section to stay resident for the one rule inside it."""
    assert ids(DOC) == ["Rules", "Layout", "Tooling"]
    assert ids(DOC, {"Tooling"}) == [
        "Rules", "Layout", "Tooling",
        "Tooling > Broken thing", "Tooling > The rule that survived"]


def test_headings_inside_code_fences_are_not_headings():
    """WHY: these files routinely contain an example prompt template with
    '## Context' in a fenced block. Counting it as a section misattributes every
    rule that follows it, and the misattribution is silent."""
    t = "## Real\nx\n\n```\n## NotASection\n### AlsoNot\n```\n\n## AlsoReal\ny\n"
    assert ids(t) == ["Real", "AlsoReal"]


# --- the property the whole design exists to give -----------------------------

def test_split_loses_nothing():
    """WHY: THE load-bearing invariant. A verbatim split is only trustworthy
    because it is checkable; if lines can vanish, the checkability is the only
    thing that was actually lost."""
    core, side, _ = S.split(DOC, {"Rules"}, "ref.md")
    assert S.conservation(DOC, core, side) == {}


def test_conservation_actually_detects_a_dropped_line():
    """WHY: a checker that cannot fail proves nothing. This is the mutation."""
    core, side, _ = S.split(DOC, {"Rules"}, "ref.md")
    mangled = core.replace("Never deploy on Friday.", "")
    lost = S.conservation(DOC, mangled, side)
    assert "Never deploy on Friday." in lost


# --- what stays vs what moves -------------------------------------------------

def test_named_chunk_stays_resident_and_unnamed_moves():
    core, side, titles = S.split(DOC, {"Rules"}, "ref.md")
    assert "Never deploy on Friday." in core
    assert "`src/` — code" not in core
    assert "`src/` — code" in side
    assert "Layout" in titles


def test_h3_selection_keeps_one_subsection_and_moves_its_siblings():
    """WHY: the reason H3 exists — insurance is a property of a RULE, not of the
    section around it. A single line must be rescuable from a reference section."""
    core, side, _ = S.split(DOC, {"Tooling > The rule that survived"}, "ref.md")
    assert "Grep for the shape." in core
    assert "Long post-mortem." not in core
    assert "Long post-mortem." in side
    # the H2 heading is duplicated so each file reads standalone
    assert core.count("## Tooling") == 1 and side.count("## Tooling") == 1
    assert S.conservation(DOC, core, side) == {}


def test_banner_names_the_sidecar_and_lists_what_moved():
    """WHY: an index nobody can act on means the sidecar is never read, which
    turns a split into plain deletion."""
    core, _, _ = S.split(DOC, {"Rules"}, "docs/ref.md")
    assert "docs/ref.md" in core
    assert "> - Layout" in core
    assert "> - Rules" not in core


@pytest.mark.parametrize("keep", [set(), {"Rules"}, {"Rules", "Layout", "Tooling"}])
def test_conservation_holds_for_every_selection(keep):
    core, side, _ = S.split(DOC, keep, "ref.md")
    assert S.conservation(DOC, core, side) == {}
