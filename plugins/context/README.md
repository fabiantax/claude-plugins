# context — enforce the rules, stop reciting them

A CLAUDE.md is paid for in **every session, on every task, in that repo**. Most of
it is reference material a given task never touches, and a meaningful slice is
*prohibitions* — rules that would be better enforced than remembered.

This plugin does three things:

1. **`guard.py`** — a `PreToolUse` hook that denies a Bash command when it
   violates a rule declared in `.claude/guards.toml`, returning the reason.
2. **`doctor.py`** — reports what a repo's CLAUDE.md costs and which of its rules
   could be *enforced* instead of stated.
3. **`split.py`** — moves the *reference* half out to a sidecar the agent reads
   on demand, verbatim, and proves the move lost nothing.

Those are the two halves of the bill. `doctor` and `guard` deal with the rules;
`split` deals with everything that is *not* a rule — usually most of the file.

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

  where it sits:
     2881 tok   18%  Multi-agent parallelization
     2738 tok   18%  Rules
     2018 tok   13%  Tooling workflow (mandatory for all coding agents)

  ENFORCEABLE-RULE CANDIDATES: 18
  combined cost of those lines: 1837 tok (11.8% of the file)
  ^ this is the realistic ceiling for conversion, not the section total.
```

It reports a **count of candidate rules**, not a percentage of the file, because
the count is what you then have to audit. A candidate needs BOTH an obligation
("never", "requires", "always") AND a command-shaped literal — a command, flag,
path or env assignment. A prohibition with no command in it is judgement, and
judgement does not mechanise.

**Calibrated against two real repos**: on the pilot it surfaced 18 candidates, of
which 5 survived audit and shipped — and it finds all 5. On a repo whose rules
were already converted it reports 1 (a known false positive: a filename
mentioned in prose).

An earlier version counted prohibition words per *section* and reported the whole
section's tokens as mechanisable. It claimed **61% of the pilot file** when the
honest answer was five rules — overstating by roughly 6x, because converting one
rule inside a 2,881-token section frees the rule's lines, not the section.

## Splitting the reference out

Enforcing rules only ever addresses the rules. On a real 15,574-token manual the
*enforceable* lines came to 1,837 tok — the other 87% was reference the agent
pays for in every session and reads in almost none.

```bash
python3 split.py CLAUDE.md                                  # inventory + chunk ids
python3 split.py CLAUDE.md --core-ids core.txt \
    --out-core CLAUDE.md --out-sidecar docs/claude-md-sections.md
```

**The only question worth asking per chunk** is not "is this important" — all of
it is. Ask what the chunk costs you when you *don't* read it:

- **Resident** — a rule you can violate *without knowing to look it up*. Capital
  safety, silent-corruption traps, standing authorizations, honesty gates. No
  index and no search rescues a wrong call here: retrieval cannot save you from a
  rule you never thought to fetch.
- **Sidecar** — what you would naturally look up *once the task touches it*.
  Inventories, layouts, tool post-mortems, orchestration mechanics.

Because **insurance is a property of a rule, not of the section around it**, the
inventory chunks at H3 as well as H2, so one surviving rule can be rescued out of
a 2,018-token post-mortem and the rest still moves.

Everything moves **verbatim**, and the tool **refuses to write** unless every
non-blank line of the original appears in exactly one of the two files. That
check is the point: an unverifiable split of a file full of hard-won safety rules
is not worth the tokens it saves. Finer line-level surgery compresses more and
cannot be checked this way, so it isn't offered.

Measured on that manual: **15,574 → 7,211 tok resident (−54%)**, 0 lines lost.

### The check worth wiring into CI

The split is a one-off; the risk is permanent, because the next edit can quietly
move a capital rule into the sidecar and nothing will complain.

```bash
python3 split.py CLAUDE.md --assert-resident insurance.txt
```

`insurance.txt` is one string per line — the rules that must never leave. On the
repo above it reads 10/10 against the core and 0/10 against the sidecar, so it
discriminates rather than passing by default.

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
cd hooks && python3 -m pytest test_guard.py test_doctor.py test_split.py -q
```
