#!/usr/bin/env python3
"""Tests for the doctor's mechanisability heuristic.

The heuristic is a judgement call tuned against two real repos, so these tests
pin the SHAPE of that judgement — what counts as a rule, what does not — rather
than exact counts against files that will change.

The bug they exist to prevent: v1 counted prohibition words per section and
reported the whole SECTION's tokens as mechanisable, claiming 61% of a file when
the honest answer was five rules. Two errors compounded — section-level
attribution for a line-level change, and treating any prohibition as a
predicate.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doctor  # noqa: E402


# --- what IS a candidate ------------------------------------------------------

@pytest.mark.parametrize("line,expect", [
    ("Do NOT use bare `uv run` — it will fail.", "uv run"),
    ("Live mode requires an additional `LIVE_TRADING_CONFIRMED=yes` env.",
     "LIVE_TRADING_CONFIRMED=yes"),
    ("**Always pass `--save-run <tag>` to gamma-run**", "--save-run <tag>"),
    ("All gamma tests require `--features onnx`:", "--features onnx"),
    ("**No `*_SUMMARY.md` cruft.** Document in code.", "*_SUMMARY.md"),
    ("never edit `scripts/train.py` directly", "scripts/train.py"),
])
def test_command_shaped_obligation_is_a_candidate(line, expect):
    """WHY: each of these became a shipped guard on a real repo. If the oblige
    list or the shape list is narrowed, one of these stops being found — which is
    exactly how the capital-risk LIVE_TRADING rule was missed by an earlier
    version that matched 'required' but not 'requires'."""
    lits = doctor.is_candidate(line)
    assert lits, "should be a candidate: %s" % line
    assert any(expect in l for l in lits), "expected %r among %r" % (expect, lits)


# --- what is NOT a candidate --------------------------------------------------

@pytest.mark.parametrize("line", [
    # obliging, but no command anywhere — judgement, must stay prose
    "Never deploy an IS-only model without out-of-sample validation.",
    "Always check existing work before building something new.",
    "Do not escalate to the user; escalate to the team.",
    "Never trust a peer consult as repo truth.",
    # a command, but no obligation — reference, not a rule
    "Run `cargo nextest run` to execute the suite.",
    "The pipeline uses `uv run --isolated python scripts/train.py`.",
    # prose in backticks is not a command shape
    "Never use the `naive` approach for this.",
])
def test_not_a_candidate(line):
    """WHY: the v1 failure was treating every prohibition as mechanisable. These
    are the two halves that must BOTH be present — obligation and a matchable
    literal — and each line here has exactly one of them."""
    assert doctor.is_candidate(line) == [], "must not be a candidate: %s" % line


# --- the structural fix -------------------------------------------------------

def test_reporting_is_line_level_not_section_level():
    """WHY: this is the actual v1 bug. Converting one rule inside a large section
    frees the rule's lines, not the section. A regression would show up as the
    candidate cost approaching the section cost."""
    section = "\n".join(
        ["## Big Section"]
        + ["Some prose that is not a rule at all." for _ in range(60)]
        + ["Do NOT use bare `uv run` here."])
    secs, _ = doctor.sections(section)
    assert len(secs) == 1
    body = secs[0][1]
    cand = [l for l in body if doctor.is_candidate(l)]
    assert len(cand) == 1, "exactly one line is a rule"
    cand_tok = doctor.TOK(cand[0])
    section_tok = doctor.TOK("\n".join(body))
    assert cand_tok < section_tok / 10, (
        "candidate cost (%d) must reflect the LINE, not the section (%d)"
        % (cand_tok, section_tok))


def test_fenced_code_is_not_scanned_for_sections():
    """WHY: example blocks contain `## Context`-style headings. Counting those as
    real sections inflates the section list and misattributes rule lines."""
    text = "## Real\ntext\n\n```\n## NotASection\n```\n\n## AlsoReal\ntext\n"
    secs, _ = doctor.sections(text)
    assert [t for t, _ in secs] == ["Real", "AlsoReal"]
