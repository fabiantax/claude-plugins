---
name: gitea-pm
description: Gitea project management — issues, milestones, labels, kanban boards, dependencies, releases, time tracking, batch operations.
argument-hint: "[repo] [command] — e.g. 'fabiantax/GraphFusion board' or 'fabiantax/GraphFusion issues --open"
---

# Gitea Project Management

## Instance

| What | Value |
|------|-------|
| URL | `http://127.0.0.1:3200` (local), `http://strix:3200` (Tailscale) |
| API base | `http://127.0.0.1:3200/api/v1` |
| Version | 1.26.1 |
| Admin | `fabiantax` |
| Token env | `$GITEA_TOKEN` |
| Service | `systemctl --user start/stop/restart gitea` |

**Setup before use:**
```bash
# A durable token is already exported from ~/.bashrc.d/99-secrets.sh (login shells).
# Non-login/agent shells may not source it — if $GITEA_TOKEN is empty, source it:
[ -n "$GITEA_TOKEN" ] || source ~/.bashrc.d/99-secrets.sh
# (Do NOT mint a throwaway token per run — reuse the persistent one above.)
# For repo-scoped ops:
export GITEA_REPO="fabiantax/GraphFusion"   # owner/repo
```

---

## Issues

### Create issue
```bash
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d "$(jq -n --arg title "Issue title" --arg body "Description" \
    --argjson labels '[15,22]' --argjson milestone 1 \
    '{title:$title, body:$body, labels:$labels, milestone:$milestone}')" \
  | jq '{number, title, state, milestone: .milestone.title}'
```

**IMPORTANT:** Labels use numeric IDs, not names. Get IDs: `curl -sS -H "Authorization: token ${GITEA_TOKEN}" "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/labels" | jq '.[] | {id, name}'`

### List issues
```bash
# Open issues with specific label and milestone
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues?state=open&labels=15&milestone=1&limit=50&type=issues" \
  | jq '.[] | {number, title, state, labels: [.labels[].name], assignee: .assignee.login, milestone: .milestone.title}'

# All open issues
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues?state=open&type=issues" \
  | jq '.[] | {number, title, labels: [.labels[].name]}'
```

### Update issue
```bash
# Close issue
curl -sS -X PATCH "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"state":"closed"}'

# Reopen issue
... -d '{"state":"open"}'

# Assign to user
... -d '{"assignees":["fabiantax"]}'

# Change title/body/milestone
... -d '{"title":"New title","body":"New body","milestone":2}'

# Set due date
... -d '{"due_date":"2026-06-01T00:00:00Z"}'
```

### Pin/unpin
```bash
# Pin issue (max 3 per repo by default)
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/18/pin" \
  -H "Authorization: token ${GITEA_TOKEN}"

# Unpin
curl -sS -X DELETE "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/18/pin" \
  -H "Authorization: token ${GITEA_TOKEN}"

# Reorder pinned issues
curl -sS -X PATCH "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/18/pin/1" \
  -H "Authorization: token ${GITEA_TOKEN}"

# List pinned
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/pinned" \
  | jq '.[] | {number, title}'
```

### Lock/unlock
```bash
curl -sS -X PUT "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/18/lock" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"issue_title":"Too heated"}'

curl -sS -X DELETE "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/18/lock" \
  -H "Authorization: token ${GITEA_TOKEN}"
```

### Bulk close milestone issues
```bash
# Close all open issues in a milestone
MILESTONE_ID=1
ISSUES=$(curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues?state=open&milestone=${MILESTONE_ID}&type=issues&limit=50" \
  | jq '.[].number')
for num in $ISSUES; do
  curl -sS -X PATCH "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/${num}" \
    -H "Authorization: token ${GITEA_TOKEN}" \
    -H 'content-type: application/json' \
    -d '{"state":"closed"}' > /dev/null
  echo "Closed #${num}"
done
```

---

## Labels

### CRUD
```bash
# Create label
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/labels" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"name":"status:backlog","color":"#808080","description":"Not yet started"}' \
  | jq '{id, name, color}'

# List labels
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/labels" \
  | jq '.[] | {id, name, color}'

# Update label
curl -sS -X PATCH "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/labels/22" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"name":"status:in-progress","color":"#0074D9"}'

# Delete label
curl -sS -X DELETE "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/labels/22" \
  -H "Authorization: token ${GITEA_TOKEN}"
```

### Apply/remove labels from issues
```bash
# REPLACE all labels on an issue (removes labels not in the list)
curl -sS -X PUT "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19/labels" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"labels":[15,22]}' \
  | jq '.[].name'

# ADD labels to an issue (keeps existing)
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19/labels" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"labels":[15,22]}'

# REMOVE a single label from an issue
curl -sS -X DELETE "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19/labels/22" \
  -H "Authorization: token ${GITEA_TOKEN}"
```

### Kanban labels (status columns)
```bash
# Create the four standard columns
declare -A COLORS=(
  ["status:backlog"]="#808080"
  ["status:in-progress"]="#0074D9"
  ["status:review"]="#B60205"
  ["status:done"]="#0E8A16"
)
for label in "${!COLORS[@]}"; do
  curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/labels" \
    -H "Authorization: token ${GITEA_TOKEN}" \
    -H 'content-type: application/json' \
    -d "{\"name\":\"${label}\",\"color\":\"${COLORS[$label]}\"}" \
    | jq '{id, name}'
done
```

---

## Milestones

### CRUD
```bash
# Create milestone
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/milestones" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"title":"Phase 1 — Block Format","description":"Define blocked CSR data structures and serialization.","due_date":"2026-06-01T00:00:00Z"}' \
  | jq '{id, title, open_issues, closed_issues}'

# List milestones
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/milestones" \
  | jq '.[] | {id, title, state, open_issues, closed_issues, due_date}'

# Update milestone
curl -sS -X PATCH "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/milestones/1" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"title":"Updated title","state":"closed"}'

# Delete milestone
curl -sS -X DELETE "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/milestones/1" \
  -H "Authorization: token ${GITEA_TOKEN}"
```

### Progress report
```bash
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/milestones" \
  | jq '.[] | "\(.title): \(.closed_issues)/\(.open_issues + .closed_issues) closed (\(.open_issues) open)"'
```

---

## Comments

```bash
# Add comment
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19/comments" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"body":"Implemented. Files: csr_blocked.rs. Tests: 12 passed."}' \
  | jq '{id, body: (.body[:100])}'

# Update comment
curl -sS -X PATCH "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/comments/123" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"body":"Updated text"}'

# Delete comment
curl -sS -X DELETE "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/comments/123" \
  -H "Authorization: token ${GITEA_TOKEN}"

# Add reaction
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/comments/123/reactions" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"content":"+1"}'
```

---

## Dependencies

**GOTCHA:** the dependency body must identify the target issue by **`{"owner","repo","index"}`** — a bare `{"index":N}` silently 404s with `IsErrRepoNotExist`. Derive owner/repo from `GITEA_REPO` (`owner/repo`):

```bash
OWNER="${GITEA_REPO%/*}"   # fabiantax
REPO="${GITEA_REPO#*/}"    # GraphFusion

# Issue #20 depends on (blocked by) #19
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/20/dependencies" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d "{\"owner\":\"${OWNER}\",\"repo\":\"${REPO}\",\"index\":19}" \
  | jq '{dependency: .dependency.index, dependent: .dependent.index}'

# #19 blocks #20
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19/blocks" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d "{\"owner\":\"${OWNER}\",\"repo\":\"${REPO}\",\"index\":20}"

# Remove dependency
curl -sS -X DELETE "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/20/dependencies" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d "{\"owner\":\"${OWNER}\",\"repo\":\"${REPO}\",\"index\":19}"
```

---

## Time Tracking

```bash
# Start stopwatch on issue
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19/stopwatch/start" \
  -H "Authorization: token ${GITEA_TOKEN}"

# Stop stopwatch
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19/stopwatch/stop" \
  -H "Authorization: token ${GITEA_TOKEN}"

# Add manual time entry (seconds)
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19/times" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"time":3600}' # 1 hour

# List time entries
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19/times" \
  | jq '.[] | {user: .user.login, time_seconds, created}'
```

---

## Releases & Tags

```bash
# Create release
curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d '{"tag_name":"v0.3.0","target":"main","title":"v0.3.0 — Blocked CSR","body":"Added BlockedCsrBlock data structure and spatial partitioning.","draft":false}' \
  | jq '{id, tag_name, title, html_url}'

# List releases
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases" \
  | jq '.[] | {tag_name, title, draft, prerelease}'

# Delete release
curl -sS -X DELETE "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases/1" \
  -H "Authorization: token ${GITEA_TOKEN}"
```

---

## Search

```bash
# Global search across all repos
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/issues/search?q=blocked+CSR&state=open&type=issues&limit=20" \
  | jq '.[] | {repo: .repository.full_name, number, title, state}'

# Filter by labels + milestone + assignee
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues?state=open&labels=15&milestone=1&created_by=fabiantax&type=issues" \
  | jq '.[] | {number, title, created_at}'
```

---

## Kanban Board (simulated)

Gitea 1.26.1 has no project board API. Use `status:*` labels as kanban columns.

### Board view
```bash
# Get status label IDs first
LABELS=$(curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/labels" | jq -r '.[] | select(.name | startswith("status:")) | "\(.name | sub("status:"; "")) \(.id)"')

echo "=== BOARD: ${GITEA_REPO} ==="
while read -r col id; do
  echo -e "\n--- ${col^^} ---"
  curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
    "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues?state=open&labels=${id}&type=issues&limit=50" \
    | jq -r '.[] | "#\(.number) \(.title) [\(.milestone.title // "no milestone")]"'
done <<< "$LABELS"

# Closed column
echo -e "\n--- DONE (closed) ---"
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues?state=closed&type=issues&limit=20" \
  | jq -r '.[] | "#\(.number) \(.title)"'
```

### Move issue to column
```bash
# Remove old status labels, add new one
# Step 1: Get all current labels (non-status)
CURRENT=$(curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19" | jq '[.labels[] | select(.name | startswith("status:") | not) | .id]')

# Step 2: Add new status label ID
NEW_STATUS_ID=25  # e.g., status:in-progress
ALL_LABELS=$(echo "$CURRENT" | jq --argjson sid "$NEW_STATUS_ID" '. + [$sid]')

# Step 3: Replace all labels
curl -sS -X PUT "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/19/labels" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H 'content-type: application/json' \
  -d "{\"labels\":${ALL_LABELS}}" \
  | jq '[.[].name]'
```

---

## Batch Operations

### Move all milestone issues to a new milestone
```bash
OLD_MILESTONE=1
NEW_MILESTONE=2
ISSUES=$(curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues?state=open&milestone=${OLD_MILESTONE}&type=issues&limit=50" \
  | jq '.[].number')
for num in $ISSUES; do
  curl -sS -X PATCH "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/${num}" \
    -H "Authorization: token ${GITEA_TOKEN}" \
    -H 'content-type: application/json' \
    -d "{\"milestone\":${NEW_MILESTONE}}" > /dev/null
  echo "Moved #${num} to milestone ${NEW_MILESTONE}"
done
```

### Relabel issues matching a filter
```bash
# Add type:task label to all issues with from:graphfusion-engineer
ENGINEER_LABEL=22
TASK_LABEL=15
ISSUES=$(curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues?state=open&labels=${ENGINEER_LABEL}&type=issues" \
  | jq '.[].number')
for num in $ISSUES; do
  curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/${num}/labels" \
    -H "Authorization: token ${GITEA_TOKEN}" \
    -H 'content-type: application/json' \
    -d "{\"labels\":[${TASK_LABEL}]}" > /dev/null
  echo "Labeled #${num}"
done
```

---

## Agent Integration

Mesh agents should use this skill instead of embedding curl recipes in their personas. Pattern:

```bash
# Agent consults gitea-pm to file a story
am-runtime call http://127.0.0.1:50250 consult \
  "File a user story on fabiantax/GraphFusion: title='...', body='...', labels=[type:user-story, from:graphfusion-ceo]"

# Agent asks for board status
am-runtime call http://127.0.0.1:50250 consult \
  "Show the board for fabiantax/GraphFusion milestone 'Blocked CSR'"
```

---

## Executor Suggestions (model + agent + skills)

Every DoR'd issue gets ONE comment titled `### 🤖 Suggested executor` posted at triage time — same pass as labels, milestone, and DoD. It names: (a) model tier, (b) agent type, (c) skills to load, and (d) a phase split when a decision must precede implementation.

### Model tiers

| Tier | Use for |
|------|---------|
| **Fable** (coordinator, inline) | Decisions, analysis, architecture forks, root-cause calls, ADRs, final review/merge — never delegated to a sub-agent |
| **Opus** | Complex implementation: type-system design, cost-model/CCH internals, multi-crate refactors, anything "easy to get wrong" |
| **Sonnet** | Well-specified moderate work: CI plumbing, test writing, mechanical refactors, doc writes, evidence gathering |
| **Haiku** | Trivial mechanical edits only (rare; most routing/db work doesn't qualify) |

### Agent selection

| Agent | When |
|-------|------|
| `rust-coder` | Idiomatic Rust implementation |
| `cicd-engineer` | CI workflows, scripts, Gitea Actions |
| `bake-doctor` | Routing-bake connectivity/cost diagnostics — evidence-only, no writes |
| `tester` | Test suites, property-based tests, benchmarks |
| `geospatial-developer` | WKT/R-tree/H3/spatial queries, DE-9IM predicates |
| `rust-perf-optimizer` | SIMD, cache, throughput, flamegraph follow-up |
| `sre` | Host/infra diagnostics, journald, service failures |
| `gitea-pm` | Issue ops (this skill) |
| `general-purpose` | Fallback when no specialist fits |
| `Explore` | Read-only codebase recon (fast, no writes) |
| `Plan` | Architecture planning (read-only + design output) |

Discover the full registry: Agent tool's `subagent_type` list, repo agents in `.claude/agents/`, machine agents in `~/.claude/agents/`.

### Phase-split pattern

When an issue has a genuine fork (design choice, weld-vs-drop, threshold pick), split it:

- **Phase 1:** Fable + `<evidence agent>` — decision recorded as ADR or issue comment before any code is written.
- **Phase 2:** Implementation tier (Opus/Sonnet + appropriate coder agent).

Rule of thumb: **don't send a coder in cold** — if the issue has an "Open decision" line in its DoR, it needs a phase split.

Real examples:
- **#545** Opus + `rust-coder` — subtle type design, easy to get wrong.
- **#541** Sonnet + `cicd-engineer` — mechanical but correctness-critical CI wiring.
- **#537** Fable + `bake-doctor` → conditional Sonnet — analysis-led; implementation only if evidence warrants.
- **#562** Phased: investigate → design-doc → Opus implementation.

### Needed skills

Name the skills the executor must load in the comment (e.g. `/gitea-pm` for issue ops, `/llama-cpp-rocm` for inference work, repo-specific skills under `.claude/skills/`). Check `~/.claude/skills/` for the available set.

### Gap handling

- **Agent almost fits:** note the stretch in the comment ("general-purpose + this context block").
- **Real recurring gap:** the executor comment proposes creating one — new agent = `~/.claude/agents/<name>.md` (machine-wide) or `.claude/agents/<name>.md` (repo); new skill = `~/.claude/skills/<name>/SKILL.md`. For substantial gaps, file a separate `type:tooling` story rather than blocking the issue. Precedent: the `bake-doctor` agent + `xtask bake-doctor` tool (reusable-core rule: lib core + thin CLI wrapper + agent).

### Posting template

```bash
jq -n '{body:"### 🤖 Suggested executor\n**<Tier> + `<agent>`** — <one-line why>. Skills: `/<skill>`.\n<optional phase split>"}' \
  | curl -sS -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/issues/<N>/comments" \
    -H "Authorization: token ${GITEA_TOKEN}" -H 'content-type: application/json' -d @-
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Labels return `[]` after PUT | Label IDs not numeric | Use `jq` to get integer IDs, not names |
| 404 on project boards | Gitea 1.26.1 has no boards API | Use `status:*` labels as columns |
| `cannot unmarshal JSON string` | Labels expects integer array | `"labels":[15,22]` not `"labels":["type:task"]` |
| Issue not appearing in search | `type=issues` excludes PRs | Add `&type=issues` to filter out pull requests |
| 403 on token operations | Token scope too narrow | Recreate with `write:issue` and `write:repository` |
