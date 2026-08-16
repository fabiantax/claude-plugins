#!/usr/bin/env python3
"""Tests for the guard runner. Run: python3 -m pytest test_guard.py -q

Structure mirrors the two ways a guard fails, which have very different costs:

  FALSE POSITIVE  blocks legitimate work -> a wedged agent. Catastrophic.
  FALSE NEGATIVE  misses a violation     -> one unenforced rule. Recoverable.

So every deny rule is paired with its *legitimate near-miss* — the command that
looks similar and must still be allowed. Both bugs found during development were
false positives caught only by replaying 9,189 real commands from the transcript
corpus (see test_no_false_positives_on_real_commands), not by fixtures:
`llamacpp-upstream-push` matched every `git push`, and `pkill-f-llama-server`
matched `pkill -x llama-server`, the correct form.
"""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guard  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# The plugin ships NO active config — rules are per-repo, and a repo that has not
# opted in gets no rules at all. Tests run against the worked example, which
# doubles as a check that the shipped example stays valid and false-positive-free.
CFG = os.path.normpath(os.path.join(HERE, "..", "examples", "guards.toml"))


@pytest.fixture(scope="module")
def rules():
    d, r = guard.load_rules(CFG)
    assert d and r, "config must parse — an unparsed config fails open silently"
    return d, r


def ev(rules, cmd):
    return guard.evaluate(cmd, *rules)


# --- true positives: each must block -----------------------------------------

@pytest.mark.parametrize("cmd,rule", [
    ("rm ~/.local/share/containers/storage", "podman-storage-symlink"),
    ("mv /home/fabian/.local/share/containers/storage /tmp/x", "podman-storage-symlink"),
    ("pkill -f llama-server", "pkill-f-llama-server"),
    ("pkill -9f llama-server", "pkill-f-llama-server"),
    ("mv ~/.local/bin/strix-llama /tmp/", "onpath-symlink-overwrite"),
    ("startup llm/mtp", "startup-llm-vs-llama-swap"),
    ("git push --force origin main", "protected-force-push"),
    ("git commit --no-verify -m x", "merge-gate-bypass"),
    ("gh pr merge 42 --squash", "gh-pr-merge-on-mirrored-repo"),
    ("git -c user.email=x@y.z commit -m hi", "commit-identity-override"),
    ("git commit --author='Someone <a@b.c>' -m hi", "commit-identity-override"),
    ("llama-bench -m /models/foo.gguf -p 512", "gpu-exclusive-under-gpu-bench"),
])
def test_violation_is_blocked(rules, cmd, rule):
    """WHY: reverting the rule (or loosening its pattern) makes this allow, so
    the guard silently stops enforcing exactly what it was added for."""
    hit = ev(rules, cmd)
    assert hit is not None, "should have blocked: %s" % cmd
    assert hit[0] == rule, "blocked by %s, expected %s" % (hit[0], rule)


# --- false positives: the legitimate near-miss of each rule -------------------

@pytest.mark.parametrize("cmd", [
    "pkill -x llama-server",                                  # the CORRECT form
    "pkill -x llama-server 2>/dev/null; sleep 1",
    "ls -la ~/.local/share/containers/storage",               # inspecting, not removing
    "cat ~/.local/bin/strix-llama",                           # reading the symlink
    "git push origin main",                                   # ordinary push
    "git push -u gitea feat/x",
    "git push --force-with-lease origin feat/x",              # allowed on a branch
    "git commit -m 'fix: thing'",                             # ordinary commit
    "gh pr view 42",                                          # not a merge
    "gpu-bench llama-bench -m /models/foo.gguf",              # precondition satisfied
    "gpu-bench --no-drain llama-bench -m /models/foo.gguf",
    "llama-bench --help",                                     # no model, not exclusive
    "grep -r 'pkill -f' docs/",                               # discussing the rule
    "startup infra/status",
])
def test_legitimate_command_is_allowed(rules, cmd):
    """WHY: a false positive wedges the agent. Each of these is the near-miss of
    a real rule — if a pattern is loosened, one of these starts failing."""
    assert ev(rules, cmd) is None, "must NOT block: %s" % cmd


# --- fail-open contract -------------------------------------------------------

def test_unreadable_config_fails_open():
    """WHY: the guard runs on every Bash call. An unreadable config must allow,
    never block, or a typo in the file wedges the whole host."""
    assert guard.load_rules("/nonexistent/guards.toml") == ([], [])
    assert guard.evaluate("rm ~/.local/share/containers/storage", [], []) is None


def test_bad_regex_is_skipped_not_fatal(rules):
    """WHY: one malformed pattern must not take out the other rules, and must
    not raise into the hook (which would surface as a hook error)."""
    bad = [{"id": "bad", "match": "([unclosed", "why": "x"}]
    assert guard.evaluate("anything", bad, []) is None


@pytest.mark.parametrize("payload", ["", "not json", '{"tool_input":{}}', "{}"])
def test_main_allows_on_malformed_input(payload):
    """WHY: exit non-zero or stray stdout here would block or corrupt a real call."""
    p = subprocess.run([sys.executable, os.path.join(HERE, "guard.py")],
                       input=payload, capture_output=True, text=True)
    assert p.returncode == 0, "must exit 0 (allow) on malformed input"
    assert p.stdout.strip() == "", "must emit nothing when not denying"


def test_plugin_is_inert_without_repo_config(tmp_path, monkeypatch):
    """WHY: the plugin may be enabled globally, so a repo that has not opted in
    must be completely unaffected. If config discovery ever defaulted to a
    bundled file, every repo on the machine would inherit another repo's rules.

    Reverting the `if not deny_rules and not require_rules: return 0` early-out,
    or pointing config_paths() at the shipped example, makes this fail.
    """
    monkeypatch.delenv("CLAUDE_GUARDS_CONFIG", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))          # no ~/.claude/guards.toml either
    paths = guard.config_paths()
    assert not any(os.path.isfile(p) for p in paths), "fixture leaked a real config"
    deny, req = guard.load_all(paths)
    assert (deny, req) == ([], []), "must find no rules when none are declared"
    assert guard.evaluate("rm -rf /anything", deny, req) is None


def test_repo_and_host_rules_are_unioned(tmp_path, monkeypatch):
    """WHY: a repo shipping its own guards must not silently disable a host rule
    protecting the machine. If load_all ever became first-wins, this fails."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "guards.toml").write_text(
        "[[deny]]\nid = 'repo-rule'\nmatch = 'REPOONLY'\nwhy = 'r'\n")
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "guards.toml").write_text(
        "[[deny]]\nid = 'host-rule'\nmatch = 'HOSTONLY'\nwhy = 'h'\n")
    monkeypatch.delenv("CLAUDE_GUARDS_CONFIG", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(home))
    deny, req = guard.load_all(guard.config_paths())
    ids = {r.get("id") for r in deny}
    assert ids == {"repo-rule", "host-rule"}, "both scopes must apply, got %s" % ids


def test_deny_emits_the_json_contract():
    """WHY: the JSON path surfaces as a policy reason; exit 2 surfaces as
    'PreToolUse:Bash hook error', which reads as a malfunction and invites a
    workaround. Verified live on this host 2026-08-16."""
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": "pkill -f llama-server"}})
    # CLAUDE_GUARDS_CONFIG must be explicit: the subprocess would otherwise find
    # no repo config and correctly allow, which is the inertness behaviour tested
    # separately above.
    env = dict(os.environ, CLAUDE_GUARDS_CONFIG=CFG)
    p = subprocess.run([sys.executable, os.path.join(HERE, "guard.py")],
                       input=payload, capture_output=True, text=True, env=env)
    assert p.returncode == 0, "must use JSON deny, not exit 2"
    out = json.loads(p.stdout)
    hs = out["hookSpecificOutput"]
    assert hs["hookEventName"] == "PreToolUse"
    assert hs["permissionDecision"] == "deny"
    assert "pkill-f-llama-server" in hs["permissionDecisionReason"]


# --- the test that found both real bugs ---------------------------------------

def test_no_false_positives_on_real_commands(rules):
    """WHY: fixtures encode what the author already thought of. This replays
    actual Bash commands from the transcript corpus, and is what caught both
    development bugs. Skips if the corpus is unavailable."""
    import glob
    cmds = []
    for f in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
        try:
            for line in open(f, errors="replace"):
                if '"Bash"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                c = d.get("message", {}).get("content")
                if not isinstance(c, list):
                    continue
                for b in c:
                    if (isinstance(b, dict) and b.get("type") == "tool_use"
                            and b.get("name") == "Bash"):
                        cmd = (b.get("input") or {}).get("command")
                        if cmd:
                            cmds.append(cmd)
        except Exception:
            continue
        if len(cmds) > 6000:
            break
    if len(cmds) < 500:
        pytest.skip("transcript corpus unavailable (%d commands)" % len(cmds))
    blocked = [(ev(rules, c), c) for c in cmds]
    blocked = [(h[0], c) for h, c in blocked if h]
    assert not blocked, "false positives on real commands: %s" % blocked[:5]
