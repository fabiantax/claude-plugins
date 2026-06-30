---
name: learn
description: Capture a just-finished workflow (or a dir/URL/notes) into a reusable SKILL.md — auto-distill a skill from experience so next time it's one command, not a rediscovery.
argument-hint: "[what to learn — e.g. \"this session's gitea CI mirror\", a dir path, a URL, or empty to capture the last workflow]"
---

# /learn — distill a workflow into a reusable skill

**Source**: $ARGUMENTS

Turn something you just did (or a body of source material) into a `SKILL.md`, so the next
occurrence is one command instead of a from-scratch rediscovery. Modeled on Nous Research's
Hermes `/learn` (same SKILL.md standard), adapted to this repo's autonomy + packaging rules.
The self-evolution half already exists here as `/gepa` (SkillOpt) — `/learn` is the missing
**capture** half.

## When to use
- Right after a **complex, multi-step task (≥5 tool calls)** that succeeded — *especially* one
  that took dead-ends to get right. The dead-ends are the most valuable thing to capture.
- To ingest reference material into a skill: a code directory, an API-docs URL, a manual/PDF,
  pasted notes.
- When you catch yourself thinking "I'll have to figure this out again next time."

## Resolving the source
1. `$ARGUMENTS` names a **dir / URL / notes** → that's the material; gather it with
   `Read` / `Grep` / `Glob` / `WebFetch`.
2. `$ARGUMENTS` describes a **workflow** ("this session's X") or is empty → reconstruct it from
   the recent conversation: the ordered tool calls, the decisions, and *what failed first* +
   the fix that worked.
3. Ambiguous → ask one question: "capture which workflow, in one sentence?"

## Procedure
1. **Reconstruct the winning path only** — the ordered steps that actually worked, not the full
   transcript. Each step = the command/tool + the one-line *why*.
2. **Mine the dead-ends → Pitfalls.** Every wrong turn becomes a Pitfall ("X looked right but
   failed because Y → do Z"). This is the highest-value content; it's what a cold re-attempt
   re-hits.
3. **Derive slug + frontmatter.** `name`: kebab-case, ≤30 chars. `description`: one line of
   *what + when*, phrased to match how the task is actually requested — this string is the
   **activation trigger** for skill auto-discovery, so make it fire on the right prompts.
4. **Author `~/.claude/skills/<slug>/SKILL.md`** with these sections, in order:
   - **When to use** — trigger conditions.
   - **Procedure** — numbered, the winning path. Reference only commands/tools that *actually
     exist* (verify before writing).
   - **Pitfalls** — the dead-ends + their fixes.
   - **Verification** — the concrete command(s)/observable that confirm success. **Mandatory** —
     a skill with no verification gate is a guess (same rule as `/loopit` item gates).
5. **Bundle assets** — if the workflow used a script/probe, put it under `<slug>/scripts/` and
   reference it (don't inline a 200-line script in prose).

## Gate before save (propose-then-write)
Unlike Hermes' silent auto-save, **show the drafted SKILL.md and take one approval** before
writing (a new on-disk artifact = ask once, per the autonomy rubric). Then verify:
- Frontmatter has `name` + `description`; file ≤ 15 KB.
- Every command / path / port / flag the skill names **actually exists** — grep/ls/curl to
  confirm. A skill that references a dead port or a removed flag is worse than none (CLAUDE.md
  drift is exactly this failure). Same "read facts, not memory" rule.
- Cold-agent test: could someone execute it with zero of the original context?

## Package + evolve
- Add the slug to `build.py` `ALLOCATION` — portable skill → `fab`; host-specific → `mesh` /
  `strix-mesh-ops` / `strix`. Run `python3 build.py`; confirm `No errors`.
- Commit to `claude-plugins` (auto-mirrors to local Gitea hourly). A `git push` is
  outward-facing → ask first.
- **Improve with use:** once a captured skill has real runs, point `/gepa` (SkillOpt) at it +
  session traces to evolve the wording — gated on size / valid frontmatter / `build.py` clean /
  semantic preservation, PR-only. That's the GEPA self-evolution loop (already available).

## Auto-trigger (the closed loop)
After finishing a ≥5-tool-call task that worked, **offer** (never silently write):
"Capture this as a skill via /learn? — proposed name `<slug>`." One line; user says yes/no.

## Anti-patterns
- **Transcript dump.** Capture the winning path + pitfalls, not every step.
- **No Verification section.** If you can't state how to confirm success, the skill is a guess.
- **Referencing things that don't exist** (a dead port, a removed flag, a renamed file). Verify
  live before writing.
- **Capturing a true one-off.** If it won't recur, write a memory, not a skill.
- **Over-generalizing.** Capture the specific procedure you actually ran; don't invent steps you
  didn't verify.
