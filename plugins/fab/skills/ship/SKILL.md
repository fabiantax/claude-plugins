---
name: ship
description: Ship one issue end-to-end on a local Gitea repo — branch, commit, push, PR, squash-merge, sync main, prune. Atomic per feature.
argument-hint: "[issue-number] [optional title override] — e.g. '42' or '42 routed handler skeleton'"
---

# /ship — atomic feature-ship recipe (Gitea flavor)

One issue → one branch → one commit → one PR → squash-merge → sync. Matches the cadence already established in this org (one feature per PR, see PRs #38/#39/#45).

## When to use

- Issue is implementation-ready: scope is concrete, code is written or about to be, tests pass locally.
- Repo's remote is a local Gitea (`http://localhost:3200`) — for GitHub repos use `gh pr create` instead.
- The change is a single logical unit. If it isn't, stop and split first.

## When NOT to use

- Work-in-progress that needs review before merge → push branch, open PR, **don't** call the merge step.
- The main branch is not `main` — adjust manually.
- You are about to commit secrets, generated lockfile churn, or unrelated formatter sweeps. Read the diff first.

---

## Preconditions

```bash
# Working tree should have ONLY the changes for this issue staged or unstaged.
git status                          # confirm scope
git diff --stat                     # eyeball the blast radius

# Tests green.
npm test                            # or whatever this repo uses
```

If `git status` shows changes from *other* issues mixed in, stop and split them first (`git stash`, branch separately).

---

## Pre-flight: authorization tier (decide merge-vs-ask BEFORE step 5)

Before opening the PR, classify the ship against the machine-wide **PR/merge/commit
authorization tiers** (`~/CLAUDE.md` → "PR / merge / commit policy"). This decides
whether step 5 (squash-merge) runs unattended or stops for review.

- **Tier 1 — auto-merge** (proceed through step 5, report after): green required
  Gitea-Actions check + `mergeable:true` + same-repo `Closes #N` + ≤100 LOC +
  no new deps/env/systemd/infra. Push, PR, and a same-repo review/approval from
  the repo's `<repo>-cto` bot (to satisfy the 1-approval gate) are all Tier 1.
- **Tier 2 — merge, but flag** (proceed, call it out in the report): cross-repo
  issue close + `from:`/`unblocks:` labels, 100–500 LOC refactors, or a deploy
  chained *automatically* from this green merge.
- **Tier 3 — stop after step 4, ask first** (do NOT auto-merge): the diff touches
  secrets/`secrets.env`/token values, `npm publish`/`cargo publish`/a marketplace
  release, remote network access, deletes files you didn't author, or it's a
  *manual* release cut not chained from a green merge. When Tier 3, open the PR
  (step 4), then hand back for review instead of running step 5.

**Non-negotiable (above every tier):** squash-only; never `--force`/`--admin`/
`--no-verify`/push-`--force` to a protected branch; red CI = stop. Never
`gh pr merge` a Gitea-mirrored repo (merge via the Gitea API). Commit identity:
never override (`git var GIT_AUTHOR_IDENT` before committing).

When unsure of the tier, default to stopping after step 4 — but ask once with a
recommendation, not a survey.

---

## Sync with remote main — DO NOT SKIP

**Mandatory before you branch, and again immediately before you push/PR.** This is the step whose absence wastes the most time: shipping a branch off a *stale* base, tripping a CI fmt/test gate that was already fixed upstream, then discovering the fix is already on `main`. A 12-commits-behind branch produced a redundant PR and a fake "repo-wide fmt failure" exactly this way. (`<remote>` = `gitea`, fallback `origin`; base = `main`.)

*(This procedure was evolved with GEPA against a rubric covering fetch → staleness-detection → integrate → conflict-resolution → re-verify → final-resync; the conflict step is hand-corrected — never auto-stage markers.)*

### A. Fetch + detect staleness (before any work)

```bash
git fetch gitea main || git fetch origin main
BEHIND=$(git rev-list --count gitea/main..HEAD)      # commits main has that you don't
echo "branch is $BEHIND commits behind gitea/main"
git merge-base --is-ancestor gitea/main HEAD \
  && echo "current — proceed" \
  || echo "STALE base — sync before continuing"
```

If `BEHIND` = 0 **and** main is an ancestor, you're current — go to the recipe.

### B. Put the branch on the current main tip

```bash
git rebase gitea/main          # preferred (linear history); or: git merge gitea/main
```

### C. Resolve conflicts honestly (only if the rebase/merge stops)

Do **NOT** `git add -A && git rebase --continue` blindly — that stages conflict markers and ships broken code.

```bash
git status --short | grep '^UU'     # the genuinely-conflicted files
# edit each: remove <<<<<<< ======= >>>>>>> markers, keep the correct resolution
git add <each-resolved-file>        # stage only what you actually resolved
git rebase --continue               # (for a merge: git commit)
# repeat until "Successfully rebased" + clean tree.   Escape hatch: git rebase --abort
```

### D. Re-run the quality gate on the NEW base

The synced base may carry a `cargo fmt --all` sweep or moved APIs — re-verify, don't assume green from before the sync:

```bash
strix-build cargo fmt --all -- --check && strix-build cargo nextest run   # or this repo's gate (npm test, …)
```

### E. Final resync immediately before push/PR/merge

Catch commits that landed on main during your branch's life:

```bash
git fetch gitea main && git rebase gitea/main      # if already pushed: git push --force-with-lease
```

Only once **E** is clean do you push, open the PR, and squash-merge. A `mergeable: false` PR means a new conflict landed — return to **C**, don't bypass.

---

## The recipe

Replace `<N>` with the issue number, `<slug>` with a 2-4 word kebab-case description, `<TITLE>` with the conventional-commit title.

### 1. Branch off main

Run **"Sync with remote main — DO NOT SKIP"** (above) first — `git pull` alone does not detect a stale base or a branch that already diverged.

```bash
git checkout main
git fetch gitea main && git merge --ff-only gitea/main   # fail loudly if not fast-forwardable
git checkout -b feat/<N>-<slug>     # or fix/, chore/, refactor/, docs/
```

### 2. Stage + commit with issue ref

Stage **specific files**, never `-A`:

```bash
git add path/to/file1 path/to/file2
git commit -m "$(cat <<'EOF'
<TYPE>(<scope>): <short summary> (<TAG>)

<1-2 paragraphs on WHY this exists — the user-visible behavior change
or the constraint that motivated it. Don't describe what the diff does;
the diff describes itself.>

Refs gitea #<N>
EOF
)"
```

Convention from this org's history:
- `feat(mesh):`, `feat(stream):`, `fix(release):`, `feat(mem):` — scope is the subsystem
- Trailing tag in parens: `(ACK-1)`, `(MEM-1)`, `(MESH-1)` — matches the issue's title prefix
- Body uses `Refs gitea #N` (not `Closes` — that goes on the PR so squash-merge auto-closes)

### 3. Push

```bash
git push -u gitea feat/<N>-<slug>
```

### 4. Open PR via Gitea API

`gh` is GitHub-only. For Gitea use the REST API:

```bash
curl -s -X POST "http://localhost:3200/api/v1/repos/fabiantax/<REPO>/pulls" \
  -u "fabiantax:$GITEA_PASSWORD" \
  -H "Content-Type: application/json" \
  -d "$(cat <<'EOF'
{
  "title": "<TYPE>(<scope>): <short summary> (<TAG>)",
  "head": "feat/<N>-<slug>",
  "base": "main",
  "body": "## Summary\n- <bullet>\n- <bullet>\n\n## Test plan\n- [x] npm test — N pass, 0 fail\n- [x] <other check>\n\nCloses #<N>"
}
EOF
)" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('html_url') or d)"
```

The PR body's `Closes #<N>` is what makes the squash-merge auto-close the issue. Don't skip it.

### 4.5. Wait for the required Gitea-Actions check (green before merge)

**Do not merge on a red or pending check.** The required checks ("typecheck +
build", "test (unit + bdd)", "bun --compile smoke" for fab-agent-runtime-style
repos) must be `success` before step 5. Poll the run on the PR's head branch
until every job is terminal, emitting the name of any failing step so red
surfaces immediately. **Never foreground `sleep`-poll** — it blocks the agent
and hides failures; use a background poller (the `poll_pr*.py` pattern) or the
`monitor` tool that exits when `ALL_TERMINAL`.

```bash
# Find the run for this branch, then poll jobs until all terminal.
RUN_ID=$(curl -s "http://localhost:3200/api/v1/repos/fabiantax/<REPO>/actions/runs?limit=10" \
  -u "fabiantax:$GITEA_PASSWORD" \
  | python3 -c "import json,sys; r=json.load(sys.stdin); runs=r.get('workflow_runs',r) if isinstance(r,dict) else r; \
print(next((x['id'] for x in runs if x.get('head_branch')=='feat/<N>-<slug>'),''))")
# then loop: GET .../actions/runs/$RUN_ID/jobs → statuses; stop when all in
# {success,failure,cancelled,skipped,blocked}. Report the first non-success job name.
```

- **Red (any `failure`):** STOP. Read the failed job log, fix on the branch,
  push, re-poll. Never merge over red CI — this is the #1 way a bad commit
  lands on `main`.
- **Pending:** keep polling (Gitea-Actions runs take 1–5 min; the 300 s
  `healthCheckTimeout` on a model load is the long pole). Don't merge until green.
- **HTTP 405 "Not all required status checks successful" at merge time even
  though checks look green:** that's a propagation delay (Gitea hasn't re-read
  the status), not a real failure — `GET .../commits/{sha}/status`; if
  `state:success`, retry the merge within seconds. This is a retry, not a bypass.

### 5. Squash-merge

```bash
curl -s -X POST "http://localhost:3200/api/v1/repos/fabiantax/<REPO>/pulls/<PR>/merge" \
  -u "fabiantax:$GITEA_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{"Do":"squash","MergeTitleField":"<TYPE>(<scope>): <short summary> (<TAG>) (#<PR>)","delete_branch_after_merge":true}' \
  -w "\nHTTP %{http_code}\n"
```

Expect `HTTP 200`. Anything else (409, 422) means the PR isn't mergeable — investigate, don't retry.

**Approval-gate fallback (HTTP 422 mentioning "approval"):** repos with
1-approval branch protection reject the merge if no one has approved the PR.
The author can't self-approve, so POST an `APPROVE` review from the repo's
`<repo>-cto` bot token, then retry the merge **once**:

```bash
# POST the approval from the repo's -cto bot (has write:repository scope)
curl -s -X POST "http://localhost:3200/api/v1/repos/fabiantax/<REPO>/pulls/<PR>/reviews" \
  -H "Authorization: token ${GITEA_TOKEN_<REPO>_CTO}" \
  -H "Content-Type: application/json" \
  -d '{"event":"APPROVE","body":"green CI + in-scope — approving for the 1-approval gate."}'
# then retry the merge (step 5). Expect HTTP 200 on the retry.
```

The default `GITEA_TOKEN` lacks `write:repository` and will 403 here — use the
repo-scoped `GITEA_TOKEN_<REPO>_CTO` (e.g. `GITEA_TOKEN_MESH_CTO`,
`GITEA_TOKEN_ATLAS_CTO`, `GITEA_TOKEN_FAB_TRADER_CTO`). If approval also fails,
stop and ask — don't loop approvals or escalate privileges.

### 6. Sync + prune

```bash
git checkout main
git pull gitea main                 # fast-forward through the squash commit
git branch -d feat/<N>-<slug>       # local prune (remote already deleted by merge)
```

### 6.5. Cross-repo close (if the issue lives in a *different* repo than the PR)

Gitea only auto-closes a `Closes #N` that points at an issue **in the same
repo** as the PR. If the fix landed in repo A but the issue is in repo B (common
in this mesh — a fab-agent-runtime fix closes a fab-agent-mesh issue), the PR's
merge does **not** close the issue. Do it explicitly:

```bash
# 1. POST a linking comment on the issue (so the audit trail is intact)
curl -s -X POST "http://localhost:3200/api/v1/repos/fabiantax/<ISSUE_REPO>/issues/<N>/comments" \
  -u "fabiantax:$GITEA_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{"body":"Fixed in <PR_REPO> PR #<PR> — merged to main as <squash-sha>. Not auto-closed because the fix lives in a different repo; closing explicitly here.\n\n<root cause + fix summary, same as the PR body>."}'

# 2. PATCH the issue closed
curl -s -X PATCH "http://localhost:3200/api/v1/repos/fabiantax/<ISSUE_REPO>/issues/<N>" \
  -u "fabiantax:$GITEA_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{"state":"closed","state_reason":"completed"}'
```

Skip this step when `<ISSUE_REPO>` == `<PR_REPO>` — the squash-merge already
closed it (verify with step 7). The comment token needs `write:issue` scope;
the repo's `<repo>-cto`/`<repo>-ceo` bot tokens have it (`write:repository`
covers issues in scope) when the default admin creds aren't appropriate.

### 7. Verify

```bash
curl -s "http://localhost:3200/api/v1/repos/fabiantax/<REPO>/issues/<N>" \
  -u "fabiantax:$GITEA_PASSWORD" | python3 -c "import json,sys; print('#<N> state=' + json.load(sys.stdin)['state'])"
```

Expect `state=closed`.

---

## Auth note

Admin creds (`fabiantax:Strix2024!`) work for everything in dev. For scripts that get checked in, prefer a token:

```bash
export GITEA_TOKEN="$(pass show gitea/api-token)"   # or however you store it
curl -H "Authorization: token $GITEA_TOKEN" ...
```

---

## Loopit integration (built in)

`/ship` is `/loopit`-aware. When run inside a `/loopit <slug>` session, it reads
the scratchpad before committing and appends to it after merging. This is what
makes a multi-issue milestone coherent — decisions from issue N propagate to
issue N+1 without you having to remember them.

### Detecting loopit context

Two signals, in order:

1. **Explicit**: caller passed `--loopit-slug <slug>` (or arg `<N> ... loopit:<slug>`).
2. **Inferred**: `$PWD/.loopit/*/scratchpad.md` exists. If exactly one slug,
   use it. If multiple, ask which.

If neither, run in plain mode (skip the steps below).

### Step 0 (loopit only) — read scratchpad before implementing

```bash
SLUG=<slug>
test -f .loopit/$SLUG/scratchpad.md && cat .loopit/$SLUG/scratchpad.md
test -f .loopit/$SLUG/adr.md && cat .loopit/$SLUG/adr.md
```

Scan for:
- **Constraints** marked `MUST:` or `INVARIANT:` — these are non-negotiable.
- **Open questions** that this issue might resolve — answer them in the PR body.
- **Prior decisions** (in `adr.md`) — if your implementation contradicts one,
  stop and either revise the implementation or open a new ADR entry.

### Step 4.5 (loopit only) — link the PR back

Append to the PR body before posting:

```
## Loopit context

- Goal: <slug>
- Scratchpad: `.loopit/<slug>/scratchpad.md`
- Decisions honored: <bullet list of ADR entries this PR respects>
- Decisions added: <bullet list of new ADR entries this PR establishes>
```

### Step 6.5 (loopit only) — append to scratchpad after merge

Once `HTTP 200` from the merge endpoint:

```bash
cat >> .loopit/$SLUG/scratchpad.md <<EOF

## $(date -u +%Y-%m-%dT%H:%M:%SZ) — shipped #$N as PR #$PR

**What landed:** <one line on user-visible change>

**Decisions made:** <one line per non-obvious choice; "none" is a valid answer>

**Carries forward to:** <which next issue this constrains, or "nothing pending">
EOF
```

If a real decision was made (not just an implementation detail — something
future-you would re-litigate without a record), also append to `adr.md`:

```bash
cat >> .loopit/$SLUG/adr.md <<EOF

## ADR-$(date -u +%Y%m%d-%H%M) — <one-line title>

**Context:** <why this decision came up>
**Decision:** <what was chosen>
**Alternatives:** <what was rejected, briefly>
**Consequences:** <what this constrains downstream>
**Refs:** PR #$PR, issue #$N
EOF
```

### Convergence signal

After merging, count `\`state=open\`` issues remaining in the loopit goal:

```bash
curl -s "http://localhost:3200/api/v1/repos/fabiantax/<REPO>/issues?state=open&milestone=<MS>" \
  -u "fabiantax:$GITEA_PASSWORD" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"
```

If 0 → tell `/loopit` to stop. If >0 → return control to `/loopit` for the next
iteration with the updated scratchpad.

## Composing with other skills

### With `/loop` — strict-iteration controller

For a tight checklist of pre-scoped issues with no decisions to record, `/loop`
is lighter than `/loopit`:

```
/loop ship every ready issue in the mesh-routing milestone in dependency order;
stop when the milestone has no open issues left.
```

Use `/loop` when the issues are the deliverable. Use `/loopit` when the *plan*
is the deliverable and decisions accumulate. When in doubt, `/loopit` — the
scratchpad overhead is small and the ADR pays off the first time you'd have
otherwise forgotten a constraint.

### Against `/ultrareview`

For risky changes (auth, migrations, public API surface) run `/ultrareview <PR#>`
between steps 4 and 5 above. Don't merge until the review is back and acted on.
If the review surfaces a decision (e.g. "we're going to validate at the edge,
not in the handler"), record it as an ADR before merging — that's exactly the
kind of constraint that needs to survive into the next iteration.

---

## Cheat sheet — minimum viable ship

```bash
# Assumes you're on main, working tree dirty with just this feature.
N=42 SLUG=route-1-handler REPO=fab-agent-runtime LOOPIT=mesh-routing  # LOOPIT="" for plain mode

# 0. (loopit only) read prior context
[ -n "$LOOPIT" ] && cat .loopit/$LOOPIT/scratchpad.md .loopit/$LOOPIT/adr.md 2>/dev/null

# 0.5 SYNC — never skip: fail loudly if base is stale
git fetch gitea main
[ "$(git rev-list --count gitea/main..HEAD)" -gt 0 ] && git rebase gitea/main   # resolve conflicts honestly (§C), then re-verify (§D)

# 1-3. branch, commit, push
git checkout -b feat/$N-$SLUG
git add <files> && git commit -m "feat(...) ... (TAG)

...

Refs gitea #$N"
git push -u gitea feat/$N-$SLUG

# 4. PR (add Loopit context block to body if $LOOPIT set)
#    capture PR number as $PR

# 5. merge (HTTP 200 expected)

# 6. sync
git checkout main && git pull gitea main && git branch -d feat/$N-$SLUG

# 6.5. (loopit only) record what shipped + any decisions
[ -n "$LOOPIT" ] && cat >> .loopit/$LOOPIT/scratchpad.md <<EOF

## $(date -u +%Y-%m-%dT%H:%M:%SZ) — shipped #$N as PR #$PR
**What landed:** ...
**Decisions made:** ...
**Carries forward to:** ...
EOF
```

---

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `git push` rejected | Branch already exists remotely | Rename or delete remote branch first |
| CI fmt/test gate red on files you never touched | Branch is on a **stale base** (predates an upstream fmt sweep / API move) | Run **Sync with remote main** §A–D; rebase onto `gitea/main`, re-verify, re-push. Don't "fix" the drift in your PR. |
| PR you opened is redundant (fix already upstream) | Branched off old main; `git rev-list --count gitea/main..HEAD` was never checked | Close the PR, delete the branch; §A prevents this — always check behind-count before committing |
| PR `mergeable: false` | Conflicts with main | **Sync with remote main §C** on the feature branch (resolve honestly), `git push --force-with-lease`, retry |
| Squash-merge 409 | CI hasn't run / required check failing | Wait for CI, then retry. Don't bypass. |
| Squash-merge HTTP 405 "Not all required status checks successful" | Required checks are green on the commit, but Gitea's merge gate hasn't re-read them yet (propagation delay) | `GET .../commits/{sha}/status` — if `state: success`, retry the merge; it goes `200` within seconds. This is a retry, not a bypass. |
| Squash-merge 422 mentioning "approval" | 1-approval branch protection; PR has no approval and the author can't self-approve | **Approval-gate fallback (step 5):** POST an `APPROVE` review from the repo's `<repo>-cto` bot token (`GITEA_TOKEN_<REPO>_CTO`, has `write:repository`), retry the merge once. Don't loop approvals. |
| Issue still open after a green squash-merge | The fix PR and the issue are in **different repos** — Gitea only auto-closes same-repo `Closes #N` | **Cross-repo close (step 6.5):** POST a linking comment, then PATCH the issue `state=closed`. Verify with step 7. |
| After squash-merge, `git merge --ff-only gitea/main` fails on local main | Squash rewrites the commit, so local main (still at the pre-squash tip) is no longer an ancestor — `--ff-only` correctly refuses | `git checkout main && git fetch gitea && git reset --hard gitea/main`. Content is identical; the SHA just changed. Don't try to reconcile by hand. |
| `Closes #N` didn't close the issue | Wrong syntax (e.g. `Close` instead of `Closes`), or merge wasn't squash | Manually close via API; fix syntax next time |
| Local branch won't `-d` delete | Tracking ref still ahead of HEAD | `git fetch gitea --prune` first, then retry |
| `git branch --merged main` lists nothing for a branch you squash-merged | Squash rewrites the commit, so the branch tip is no longer an ancestor of main — `--merged` can never see squash-merged branches | `git cherry main <branch>`: lines prefixed `-` = equivalent change already on main (safe to `git branch -D`), `+` = unique (verify by content, then keep or cherry-pick). Don't trust `--merged` after squash. |
