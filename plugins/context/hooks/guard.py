#!/usr/bin/env python3
"""guard.py — PreToolUse(Bash) guard runner. Enforces rules that used to be prose.

gitea #87. Replaces ~2,400 tokens of resident instruction text with predicates
evaluated at the tool-call layer.

WHY ENFORCE RATHER THAN STATE
A rule in the prompt is followed probabilistically. Measured on this host (#85),
some rules cannot be *retrieved* from a prompt even in principle — `gpu-bench` is
triggered by an action the agent is about to take, not by anything the user
types, so no retriever can surface it. "Prompts Don't Protect" (arXiv:2605.18414)
reports unauthorized tool invocation at 48.5-68.5% ungated, 4.0-37.0% with the
rule stated in the prompt, and 0% enforced at the tool layer.

BLOCKING CONTRACT (verified live on this host 2026-08-16, see #87)
Two mechanisms block a Bash call. This uses the JSON one deliberately:

    JSON permissionDecision:"deny"  -> surfaces as the reason text alone
    bare exit 2                     -> surfaces as "PreToolUse:Bash hook error: ..."

The exit-2 form reads as a hook MALFUNCTION, which invites a retry or a
workaround. The JSON form reads as a policy decision. Same block, different
downstream behaviour — so always the JSON form.

FAIL-OPEN, NON-NEGOTIABLE
This runs on EVERY Bash call. Any unreadable config, any bad regex, any
exception, any missing field => exit 0 (allow). A guard that cannot be evaluated
must never block real work. The cost asymmetry is stark: a missed guard is one
unenforced rule; a false positive is a wedged agent that cannot run `ls`.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def config_paths():
    """Where guards may be declared, cheapest-scope first.

    Portability is the whole point of the plugin form: the hook ships once and
    every repo declares its own rules, or none. Absent config means NO rules,
    which means fail-open — a repo that never opts in is unaffected, so enabling
    the plugin globally is safe.

      1. $CLAUDE_GUARDS_CONFIG      explicit override (tests, CI)
      2. <project>/.claude/guards.toml   repo-scoped rules, committed with the repo
      3. ~/.claude/guards.toml           machine-wide rules (host infrastructure)

    Repo and host rules are UNIONED, not overridden: a host rule protecting the
    machine must not be silently disabled by a repo that ships its own file.
    """
    explicit = os.environ.get("CLAUDE_GUARDS_CONFIG")
    if explicit:
        return [explicit]
    out = []
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    out.append(os.path.join(project, ".claude", "guards.toml"))
    out.append(os.path.expanduser("~/.claude/guards.toml"))
    return out


def load_all(paths):
    """Union the rules from every readable config. Never raises."""
    deny, req = [], []
    seen = set()
    for p in paths:
        try:
            rp = os.path.realpath(p)
        except Exception:                                # noqa: BLE001
            continue
        if rp in seen:
            continue
        seen.add(rp)
        d, r = load_rules(p)
        deny.extend(d)
        req.extend(r)
    return deny, req


def load_rules(path: str):
    """Parse guards.toml. Returns ([], []) on ANY problem — fail open.

    Uses tomllib (3.11+) when available and falls back to a deliberately small
    parser, so the guard never depends on a third-party package being installed
    in whatever interpreter the hook happens to run under.
    """
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return [], []
    try:
        import tomllib
        data = tomllib.loads(raw.decode("utf-8"))
        return data.get("deny", []), data.get("require", [])
    except Exception:                                    # noqa: BLE001
        pass
    # Minimal fallback: [[deny]] / [[require]] blocks of key = 'single-quoted'
    deny, req, cur, bucket = [], [], None, None
    try:
        for line in raw.decode("utf-8").split("\n"):
            s = line.strip()
            if s in ("[[deny]]", "[[require]]"):
                cur = {}
                bucket = deny if s == "[[deny]]" else req
                bucket.append(cur)
                continue
            if cur is None or not s or s.startswith("#"):
                continue
            m = re.match(r"(\w+)\s*=\s*['\"](.*)['\"]$", s)
            if m:
                cur[m.group(1)] = m.group(2)
    except Exception:                                    # noqa: BLE001
        return [], []
    return deny, req


def _in_scope(rule, cwd: str) -> bool:
    """Optional `cwd_match`: apply the rule only where its premise actually holds.

    Added after a live false positive. A rule forbidding a GitHub-side merge
    exists because most repos on that host are Gitea source-of-truth with a
    push-mirror — but it fired in a GitHub-NATIVE repo, where that same command
    is the correct tool. The guard blocked the right action for a reason that did
    not apply.

    A rule whose justification is repo-specific must say so, or it fires wherever
    its words match rather than wherever its reason holds. Rules with no
    `cwd_match` apply everywhere, as before.

    A broken `cwd_match` fails CLOSED for that rule — skipped, not applied
    everywhere — so a typo'd scope loses enforcement instead of gaining it.
    """
    pat = rule.get("cwd_match")
    if not pat:
        return True
    try:
        return bool(re.search(pat, cwd or ""))
    except re.error:
        return False


def evaluate(command: str, deny, require, cwd: str = ""):
    """-> (rule_id, why) for the first violated rule, else None. Never raises."""
    for r in deny:
        try:
            if not _in_scope(r, cwd):
                continue
            if r.get("match") and re.search(r["match"], command):
                return r.get("id", "deny"), r.get("why", "blocked by guard")
        except re.error:
            continue                                     # bad pattern => allow
    for r in require:
        try:
            if not _in_scope(r, cwd):
                continue
            if not (r.get("match") and re.search(r["match"], command)):
                continue
            unless = r.get("unless")
            if unless and re.search(unless, command):
                continue
            return r.get("id", "require"), r.get("why", "precondition not met")
        except re.error:
            continue
    return None


def deny(rule_id: str, why: str) -> None:
    """Emit the JSON deny. Reason names the rule so it reads as policy."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "[guard:%s] %s" % (rule_id, why),
        }
    }))


def main() -> int:
    try:
        payload = sys.stdin.read()
        if not payload.strip():
            return 0
        data = json.loads(payload)
        command = (data.get("tool_input") or {}).get("command") or ""
        if not command:
            return 0
        deny_rules, require_rules = load_all(config_paths())
        if not deny_rules and not require_rules:
            return 0                                     # no repo opted in
        cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or ""
        hit = evaluate(command, deny_rules, require_rules, cwd)
        if hit:
            deny(*hit)
    except Exception:                                    # noqa: BLE001
        return 0                                         # fail open, always
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                    # noqa: BLE001
        sys.exit(0)
