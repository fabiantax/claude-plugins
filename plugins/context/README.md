# context — enforce the rules, stop reciting them

A CLAUDE.md is paid for in **every session, on every task, in that repo**. Most of
it is reference material a given task never touches, and a meaningful slice is
*prohibitions* — rules that would be better enforced than remembered.

This plugin does two things:

1. **`guard.py`** — a `PreToolUse` hook that denies a Bash command when it
   violates a rule declared in `.claude/guards.toml`, returning the reason.
2. **`doctor.py`** — reports what a repo's CLAUDE.md costs and which sections are
   prohibition-dense enough to be worth converting.

On the host it was built for, this took a session from **9,150 to 1,386 resident
tokens (−85%)** while making the enforced rules categorical instead of
probabilistic.

## It is inert until you opt in

No `.claude/guards.toml` in the repo means **no rules, no blocking, no effect**.
Enabling the plugin globally is safe. Repo rules and `~/.claude/guards.toml` are
**unioned**, so a repo cannot silently disable a host rule that protects the
machine.

## Try it before installing anything

```bash
python3 doctor.py /path/to/repo/CLAUDE.md
```

Real output, on a repo that had never been touched:

```
  resident cost: 15574 tok, every session, every task in this repo
     2881 tok   18%  Multi-agent parallelization   <- prohibition-dense
     2738 tok   18%  Rules                         <- prohibition-dense
  mechanisable (prohibition-dense): 9565 tok = 61% of the file
```

The heuristic counts prohibition words. It is a **prompt for review, not a
verdict** — only you can say whether a rule is a predicate over a command or a
matter of judgement. Judgement does not mechanise; authorisation tiers, working
principles and taste stay prose.

## Declaring guards

```toml
# .claude/guards.toml
[[deny]]
id = "no-prod-migrations"
match = 'migrate[^|;&]*--env[= ]prod'
why = "Production migrations go through the release pipeline, never a shell."

[[require]]
id = "benchmarks-under-lock"
match = '(cargo bench|pytest.*--benchmark)'
unless = 'bench-lock'
why = "This box is shared — benchmarks must hold the lock or the numbers are noise."
```

`match` is a Python regex over the whole command string. `deny` blocks outright;
`require` blocks *unless* `unless` also matches — that second form is the one
prompt-based rules handle worst, because the trigger is an action the agent is
about to take rather than anything the user said.

## Four things learned the hard way

**Test patterns against real commands, not fixtures.** Replaying 9,189 real Bash
commands from the transcript corpus found two false positives that hand-written
fixtures never would have: one rule matched *every* `git push` (163 real
commands) because a path component was optional, and another matched the
*correct* form of the command it was meant to police, on 8 of 8 real hits.
`test_guard.py::test_no_false_positives_on_real_commands` does this replay.

**Anchor to invocation, not mention.** A rule matching a bare flag name fires
when you write documentation *about* it. This happened four times while building
this plugin, including on the commit that added it.

**A guard can block its own repair.** An over-broad rule prevented editing the
file that defined it, through the tool it intercepts. Guards must stay fixable
through a channel they do not intercept — the file-editing tools, not Bash. For
the same reason, **run guard tests from a file, never as an inline shell
command.**

**Fail open, always.** The hook runs on every Bash call. Unreadable config, bad
regex, malformed input — every error path allows. A missed guard is one
unenforced rule; a false positive is an agent that cannot run `ls`.

## Prior art

The reliability gap this closes is measured: *Prompts Don't Protect*
(arXiv:2605.18414) reports unauthorized tool invocation at 48.5–68.5% ungated,
4.0–37.0% with the rule stated in the prompt, and **0%** enforced at the tool
layer — though note it is a single-author preprint, so treat the exact figures as
provisional. OpenAI's *Instruction Hierarchy* (arXiv:2404.13208) makes the
general point independently: a prompt-stated rule is probabilistic, never
categorical.

## Tests

```bash
cd hooks && python3 -m pytest test_guard.py -q
```
