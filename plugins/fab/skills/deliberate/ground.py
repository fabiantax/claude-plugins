#!/usr/bin/env python3
"""ground.py — assemble a neutral cross-repo fact-sheet for a deliberation.

The mesh agents run LEAN (mesh-consult -> :8003, no tools, no repo access): they
reason over what arrives in the question. That is by design (Option A:
"the activator injects grounding"). Without grounding, atlas/localscout-cto
correctly reply "I don't have that in my consult context" — true, but useless.

This script is that activator's grounding step. For each repo in the
deliberation it pulls the TWO sources every lean agent lacks and that ARE
reliably available on this host:

  1. gitea open issues (http://localhost:3200 API) — the cross-repo work ledger
  2. recent git commits (read-only `git log` on the local checkout) — what is
     actively changing right now

Issues/commits whose text matches the topic keywords are flagged ⭐ so the
agents anchor on the relevant work, not the whole backlog.

It is deliberately NEUTRAL: facts only, no stance, no priority — the agents
form those. Output is bounded (caps + truncation) so persona + fact-sheet +
question stay under the 8192-tokens/slot budget of the :8003 batched server.

NOT used: `atlas search` (needs an embeddings DB that isn't populated here) and
`atlas query`/`stats` ("not yet implemented"). When atlas gains a populated
semantic index, a code-level enrichment block can be added — until then a grep
fallback is deliberately NOT added (no shadow systems).

Usage:
  ground.py --topic "Should GraphFusion prioritize X for localscout?" \
            --repos GraphFusion,localscout,atlas
Prints the fact-sheet to stdout (empty + exit 0 if nothing could be gathered).

Env: GITEA_TOKEN (or ~/.config/gitea-token), GITEA_URL (http://localhost:3200).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

GITEA_URL = os.environ.get("GITEA_URL", "http://localhost:3200").rstrip("/")

# repo slug (registry `repo` field, == gitea slug, case-insensitive) -> local checkout
REPO_PATHS = {
    "graphfusion": os.path.expanduser("~/Developer/personal/GraphFusion"),
    "atlas": os.path.expanduser("~/Developer/personal/atlas"),
    "localscout": os.path.expanduser("~/Developer/personal/localscout"),
    "fab-swarm": os.path.expanduser("~/Developer/personal/fab-swarm/fab-swarm"),
}

MAX_ISSUES = 10  # per repo
MAX_COMMITS = 6  # per repo
TITLE_TRUNC = 110  # chars
STOPWORDS = {
    "should",
    "would",
    "could",
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "this",
    "that",
    "what",
    "when",
    "where",
    "which",
    "prioritize",
    "priority",
    "deliberation",
    "deliberate",
    "topic",
    "repo",
    "repos",
    "across",
    "their",
    "your",
    "you",
    "are",
    "can",
    "does",
    "how",
    "why",
    "have",
    "has",
    "need",
    "needs",
    "given",
    "over",
    "between",
    "about",
}


def _token() -> str:
    tok = os.environ.get("GITEA_TOKEN", "").strip()
    if tok:
        return tok
    try:
        with open(os.path.expanduser("~/.config/gitea-token")) as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _keywords(topic: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{3,}", topic.lower())
    return sorted({w for w in words if w not in STOPWORDS})


def _matches(text: str, kws: list[str]) -> bool:
    low = text.lower()
    return any(k in low for k in kws)


def _gitea_issues(repo: str, token: str) -> list[dict] | None:
    """Open issues for fabiantax/<repo>; None on transport failure (distinct from
    'repo has zero open issues' which is []). type=issues excludes PRs."""
    url = (
        f"{GITEA_URL}/api/v1/repos/fabiantax/{repo}"
        f"/issues?state=open&type=issues&limit=30"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp)
    except Exception:
        return None


def _git_commits(repo: str) -> list[str]:
    path = REPO_PATHS.get(repo.lower())
    if not path or not os.path.isdir(os.path.join(path, ".git")):
        return []
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                path,
                "log",
                "--no-merges",
                f"-{MAX_COMMITS}",
                "--pretty=%h %s",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode != 0:
            return []
        return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    except Exception:
        return []


def _fmt_issue(i: dict, kws: list[str]) -> str:
    num = i.get("number", "?")
    title = (i.get("title") or "").strip()
    if len(title) > TITLE_TRUNC:
        title = title[: TITLE_TRUNC - 1] + "…"
    labels = ",".join(l.get("name", "") for l in (i.get("labels") or []))
    lbl = f" [{labels}]" if labels else ""
    body = i.get("body") or ""
    star = " ⭐" if _matches(f"{title} {body}", kws) else ""
    return f"  #{num}{lbl} {title}{star}"


def build(topic: str, repos: list[str]) -> str:
    token = _token()
    kws = _keywords(topic)
    blocks: list[str] = []

    for repo in repos:
        lines = [f"### {repo}"]
        issues = _gitea_issues(repo, token) if token else None
        if issues is None:
            lines.append("  (gitea unavailable)")
        elif not issues:
            lines.append("  (no open issues)")
        else:
            # relevant issues first, then most-recent, capped
            ranked = sorted(
                issues,
                key=lambda i: (
                    not _matches(f"{i.get('title', '')} {i.get('body', '')}", kws),
                    -(i.get("number") or 0),
                ),
            )[:MAX_ISSUES]
            lines.append("  open issues:")
            lines.extend(_fmt_issue(i, kws) for i in ranked)
            extra = len(issues) - len(ranked)
            if extra > 0:
                lines.append(f"  …+{extra} more open issues")

        commits = _git_commits(repo)
        if commits:
            lines.append("  recent commits:")
            lines.extend(f"    {c}" for c in commits)
        blocks.append("\n".join(lines))

    if not blocks:
        return ""

    kw_line = ", ".join(kws) if kws else "(none extracted)"
    header = (
        "## CROSS-REPO GROUNDING (facts, not opinions)\n"
        "Auto-assembled from gitea open issues + recent git commits. ⭐ = matches "
        "this topic's keywords. Use these concrete facts to ground your position; "
        "if a claim isn't supported here, say so rather than inventing it.\n"
        f"topic keywords: {kw_line}\n"
    )
    return header + "\n" + "\n\n".join(blocks) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--repos", required=True, help="comma-separated gitea repo slugs")
    args = ap.parse_args()
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    sys.stdout.write(build(args.topic, repos))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
