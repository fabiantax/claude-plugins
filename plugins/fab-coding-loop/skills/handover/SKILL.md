---
name: handover
description: Write a durable, date-stamped session handover for any repo. Gathers live state (git log/status, running containers/services, task board, preview/deploy URLs, health checks), reads prior handovers for continuity, then writes HANDOVER-YYYY-MM-DD.md using a standard 9-section template — never clobbering an earlier handover. Use when the user says "create a handover", "write a handover", "handover for the next session", or wraps up a long session and wants the next agent to pick up cleanly. Generic across repos: probes for git, podman/docker/systemd/dev-server, and gitea/github boards rather than assuming any particular stack.
---

# Handover — write a dated session handover

A handover is a short markdown file that lets the next session (or next agent) pick up exactly where this one left off, *without re-deriving the state from scratch*. This skill produces one per session, date-stamped so successive handovers accumulate instead of overwriting each other.

## When to use

The user asks for a handover, or a long session is wrapping up and there's non-obvious state worth preserving (live URLs, running services, what just shipped, gotchas hit, what's next).

**Do not use** for trivial sessions with nothing to hand off — a handover that says "nothing happened" is noise. If the session was routine, say so and skip.

## What it produces

`HANDOVER-YYYY-MM-DD.md` at the **repo root**, where the date is *today's* (use the current date from context, or `date +%F`). The date suffix is load-bearing:

- Each session → its own file. `HANDOVER-2026-06-22.md`, `HANDOVER-2026-06-25.md`, …
- They sort chronologically and never clobber each other.
- If two handovers land on the same day, suffix `-2`, `-3` (`HANDOVER-2026-06-22-2.md`).

Newer handovers **link back** to the most recent prior one ("Continues from `HANDOVER-<prev>.md`") and only re-state what changed — the older file remains the detailed record.

## The procedure

### Step 1 — date + filename

Resolve today's date. Form the target path: `<repo-root>/HANDOVER-YYYY-MM-DD.md`. Check it doesn't already exist (same-day re-run → add suffix).

### Step 2 — read prior handovers for continuity

Glob `HANDOVER-*.md` at the repo root. Read the most recent one (if any) so this handover can reference it and avoid re-explaining standing context. Standing facts (project overview, deploy topology, long-lived gotchas) live in the *oldest* handover that covers them — newer ones can link instead of repeat.

### Step 3 — gather live state (adaptive, generic)

Probe each category. **Only record what you actually detect** — don't fabricate services, URLs, or boards that aren't there. Mark a category "—" or omit it if nothing applies.

| Category | Probes | Notes |
|---|---|---|
| **Git** | `git status -sb`, `git log --oneline -8`, `git remote -v` | Always works. This session's commits = those since the prior handover's HEAD (or the merge-base with main). |
| **Date** | `date +%F` | For the filename + the "verified <date>" line. |
| **Running services** | `podman ps` OR `docker ps` (whichever exists); `systemctl --user list-units --state=running` filtered to project-ish names; a stray dev server (`lsof -i` / `ps`) | Filter to containers/units named after the repo or its stack. Skip unrelated infra (gitea, grafana, etc. unless this repo *is* that infra). |
| **Task board** | If `git remote` is the local Gitea host (`127.0.0.1:3200` / `strix:3200`) → use `/gitea-pm` for milestones + open issues. If GitHub remote → `gh issue/milestone list`. Otherwise → none. | Record milestone summary (open/closed counts) + the next ~5 issues by number. Don't dump the whole board. |
| **Preview / deploy URLs** | Read them from docs — `README.md`, `DEPLOY.md`, the prior handover, or a project-local `.claude/handover.md` hook (below). Scan for `http(s)://` URLs. | These are project-specific; don't guess. If none found and one is known, note it. |
| **Reachability** | `curl -sf -o /dev/null -w '%{http_code}' <url>` for each discovered URL. | A handover that *says* the preview is live must have *checked*. State the code, or say "not verified". |

**Multi-tenant box safety:** when inspecting processes or ports, never `kill` anything to "check" it — read state only. (See host memory `project-box-is-multitenant` on shared boxes.)

### Step 4 — write the file

Use the template below. Fill every section; if a section has no content, write a one-line reason ("no board configured for this repo", "single binary, no container stack") rather than leaving it blank — a blank section reads as "didn't check".

**Never write secret values into a handover.** Record pointers only: "ADMIN_PASSWORD is in `apps/cms/.env` (gitignored)", not the password itself. Handovers get committed and shared.

### Step 5 — offer to commit

Handovers are usually committed so the team shares them, but commit policy is per-repo. Offer (`commit this as 'docs: add <date> handover'?`) and respect the answer. If the repo keeps handovers local (gitignored), leave it untracked.

---

## Template

````markdown
# Handover — <repo name> (<YYYY-MM-DD>)

[Optional, if continuing: Continues from `HANDOVER-<prev-date>.md`. Only changes since then are below.]

State snapshot for the next session. Everything below was verified live at write-time.

---

## 1. What this project is

One paragraph: what the project is, who it's for, the one-liner purpose. Then a short bullet list of the tech stack + any non-obvious invariant (e.g. "CMS is single source of truth — all UI is data-driven").

## 2. Live state RIGHT NOW (verified <date>)

| Thing | Value |
|---|---|
| Git branch | `<branch>` (tracks `<upstream>`) |
| HEAD | `<sha>` — <clean / N uncommitted files> |
| <Preview/deploy URLs> | <https://... > |
| <Admin/internal URLs> | <http://...> |
| <Smoke test> | <e.g. "all 20 pages HTTP 200, 0 errors"> |

**Running containers / services:**
- `<name>` — <what it is, port mapping>
- …

One-line note on what the primary preview URL is and whether it's public or private (e.g. tailnet-only, staging, prod).

## 3. What just shipped this session

<N> commits on `<branch>` (`<first-sha>` → `<last-sha>`):
1. **<one-line summary>** (`<sha>`) — <one sentence of context if non-obvious>.
2. …

If there was a notable bug fix or root cause, call it out with a short paragraph — the *why* is the expensive thing to re-derive.

## 4. Board / tasks

[If a tracker exists:] Milestones + open counts. The next batch of work by issue number + one-line scope each. Link the board URL.
[If none:] "No task tracker configured for this repo."

## 5. How to run / rebuild (the dev loop)

The exact commands the next session needs: how to start the stack, how to rebuild after a change, how to re-seed/re-init data. Call out the non-obvious flags (e.g. `--network=host` build args, load-bearing pipes like `| cat`). One copy-pasteable block per common operation.

## 6. Secrets & credentials

Where each secret lives (which gitignored file / env source), never the value. Auth-scheme gotchas (e.g. "auth header is `JWT <token>` not Bearer").

## 7. Hard-won gotchas

The traps this session (or prior sessions) hit that cost real time — root cause + fix, one bullet each. If a repo-local memory/skill already captures the full detail, link it and summarize here.

## 8. Working constraints

The non-negotiable rules for this repo (data-driven only, foreground-sleep blocked, vision tool broken → DOM-verify, no root installs, etc.). One bullet each.

## 9. Immediate next steps (pick up here)

2–3 numbered next actions, ranked. End with the key URLs on one line: board · preview · admin.
````

---

## Project context hook (optional)

A repo can supply project-specific facts that can't be auto-detected (the tailscale preview URL, the board location, the deploy topology) in **`.claude/handover.md`** at the repo root. If present, read it first — it overrides/annotates the probes. Keep it to pointers and one-liners, not prose. Example:

```markdown
# handover context (read by /handover)
preview_url: https://strix.tail47010a.ts.net/
admin_url: http://127.0.0.1:3000/admin
board: gitea:fabiantax/aliestax.nl
container_prefix: aliestax-ts
deploy_docs: DEPLOY.md
```

If the file is absent, the skill falls back to probing + doc-scanning. No repo needs one.

## Conventions

- **Date in the filename, always.** `HANDOVER-YYYY-MM-DD.md`. Never `HANDOVER.md` (clobbers) or `handover.md` (collides with the context-hook file).
- **Verify before you state.** "Preview is live" must follow a `curl` that returned 200.
- **No secret values.** Pointers only.
- **Link, don't repeat.** Standing context already in an older handover → reference it, don't copy it.
- **One handover per session.** If the session forks into distinct efforts, write one handover covering the dominant thread and note the others as "also touched".
- **Newest at top when reading, chronological when listing.** `ls HANDOVER-*.md` gives chronological; the next session reads the most recent first.
