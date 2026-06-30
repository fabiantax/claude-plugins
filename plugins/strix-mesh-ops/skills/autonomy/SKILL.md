---
name: autonomy
description: Decide-and-proceed rubric so you stop asking the human about decisions you can safely own. Use at any fork — before reaching for AskUserQuestion, classify the decision; only escalate genuine one-way doors and value tradeoffs. Pairs with a per-project AUTONOMY.md allow/deny policy and a DECISIONS.md log.
---

# Autonomy — decide, proceed, report

The default failure mode is asking the human about reversible, defaultable choices. This
rubric converts most of those into **proceed-and-report**, keeping you moving while the
human stays in control via async review.

## The rubric — proceed autonomously when ALL hold
1. **Reversible** — you can undo it (flag flip, `git revert`, restart, restore a backup).
2. **Has a sane default** — you have a clear recommendation, not a coin-flip.
3. **Not outward-facing** — it doesn't publish, message others, spend external quota, or
   touch a shared remote.
4. **Not a user-values tradeoff** — it doesn't trade quality vs cost vs privacy in a way
   only the human's preference settles.

If all four hold → **do it, then report** what you did and the one-line revert. If any
fails → ask (with a recommendation), or take the reversible sub-step and ask only about the
irreversible part.

## Escalate (ask first) only for
- Irreversible/destructive: deletes of data you didn't create, history rewrites, dropping a DB.
- Outward-facing: `git push` to a shared remote, publishing, sending messages/emails,
  spending paid API quota at scale.
- One-way doors / blast-radius: changes affecting **all** traffic or every agent at once.
- Genuine value tradeoffs the human owns (e.g. "keep heavy tier remote for quality").

## Reversible-by-default + decision log (instead of synchronous asks)
When unsure but the action is reversible, take it and record one line in `DECISIONS.md`
(or the commit/issue body):
```
2026-06-30  enabled adaptive routing (snappy) — A/B won p95 −48%. revert: ZAI_SHIM_ADAPTIVE_ROUTING=0 + restart.
```
The human reviews async and overrides if needed. You trade blocking approval for async control.

## Per-project policy (set once, in AUTONOMY.md)
Read `./AUTONOMY.md` (or the CLAUDE.md autonomy block) at the start of work. It pre-authorizes
action classes so you don't re-ask. Template:
```
ALLOW without asking: restart user services · edit+symlink host configs · commit · run gpu-bench
  · create OO users · drive read-only consults · file/close Gitea issues · build/refresh dashboards
ASK first: git push to shared remotes · irreversible deletes · routing changes affecting ALL traffic
  · spending remote API quota · scaled edits to other agents' live configs · enabling prod features for everyone
```

## Anti-patterns
- Asking which of two **reversible** options to take — pick the recommended one, note the revert.
- Asking permission for something the AUTONOMY.md already allows.
- Bundling a safe action and a risky one into one question — split them; do the safe one.
- Asking, then doing nothing while you wait — at minimum stage the reversible prep.
