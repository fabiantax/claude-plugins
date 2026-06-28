---
name: catch-up
description: Show what happened while you were away — recent agent activity, Gitea issue progress, CI results, and what's still open. Run this when returning to a session after sleeping or being away.
argument-hint: "[focus] — e.g. 'GraphFusion', 'fab-agent-runtime', 'agents', 'ci', or leave empty for full report"
---

# /catch-up — What happened while you were away

Runs on every return. Shows recent activity and open work across the machine.

## Scoping — read `$ARGUMENTS` FIRST

`$ARGUMENTS` determines scope. Resolve BEFORE running any checks:

| `$ARGUMENTS` | Scope | Steps to run |
|---|---|---|
| Empty / `all` | Everything | 1–6 |
| A repo name (e.g. `GraphFusion`, `fab-agent-runtime`) | That repo only | 2 + 3 + 5 for that repo, plus Step 4 filtered to that repo's team | 
| `agents` | Mesh health + blackboard | 1 + 4 + 6 |
| `ci` | CI only | 5 |
| `issues` | Issues only (all repos) | 2 + 3 |

**Repo name matching**: Case-insensitive, partial match. `graph` matches `GraphFusion`. If ambiguous, match against all repos and pick the closest. Valid repos: `GraphFusion`, `fab-agent-runtime`, `fab-swarm`, `localscout`, `fab-agent-mesh`, `atlas`, `fab-trader`, `fab-brain`, `fab-gnosis`, `fab-types`, `fab-pruner`, `fab-learn`.

## Execution — ALWAYS run the relevant checks. Do NOT just describe them.

### Step 1: Agent mesh health (scope: `all`, `agents`)

```bash
systemctl --user status '*-ceo*' '*-cto*' '*-devops*' '*-agent*' '*-reflector*' '*-reviewer*' '*-watcher*' --no-pager 2>/dev/null | grep -E '●' | wc -l
systemctl --user status '*-ceo*' '*-cto*' '*-devops*' '*-agent*' '*-reflector*' '*-reviewer*' '*-watcher*' --no-pager 2>/dev/null | grep -c 'failed'
```

Report: N services up, any failed by name.

### Step 2: Open issues (scope: `all`, `issues`, repo name)

**For `all` / `issues`** — all repos with open issues:
```bash
ADMIN_TOKEN=$(grep 'GITEA_TOKEN_FAB_SWARM_CEO' ~/.config/fab-agent-runtime/secrets.env | cut -d= -f2)
curl -sf -H "Authorization: token $ADMIN_TOKEN" "http://localhost:3200/api/v1/repos/search?limit=100" | \
  jq -r '.data | sort_by(.open_issues_count) | reverse[] | select(.open_issues_count > 0) | "\(.full_name) — \(.open_issues_count) open"'
```

**For a specific repo** — list all open issues with labels:
```bash
ADMIN_TOKEN=$(grep 'GITEA_TOKEN_FAB_SWARM_CEO' ~/.config/fab-agent-runtime/secrets.env | cut -d= -f2)
REPO="<resolved-repo-name>"
curl -sf -H "Authorization: token $ADMIN_TOKEN" \
  "http://localhost:3200/api/v1/repos/fabiantax/$REPO/issues?state=open&limit=50&type=issues" | \
  jq -r '.[] | "#\(.number): \(.title) [\(.labels | map(.name) | join(", "))]"'
```

Also show milestone breakdown if any milestones exist:
```bash
curl -sf -H "Authorization: token $ADMIN_TOKEN" \
  "http://localhost:3200/api/v1/repos/fabiantax/$REPO/milestones" | \
  jq -r '.[] | select(.open_issues > 0) | "  \(.title): \(.open_issues) open / \(.closed_issues) closed"'
```

### Step 3: Recently closed (scope: `all`, `issues`, repo name)

**For `all` / `issues`** — scan all active repos:
```bash
ADMIN_TOKEN=$(grep 'GITEA_TOKEN_FAB_SWARM_CEO' ~/.config/fab-agent-runtime/secrets.env | cut -d= -f2)
SINCE=$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-24H +%Y-%m-%dT%H:%M:%SZ)

for repo in fab-agent-runtime GraphFusion fab-swarm localscout fab-agent-mesh atlas fab-trader; do
  closed=$(curl -sf -H "Authorization: token $ADMIN_TOKEN" \
    "http://localhost:3200/api/v1/repos/fabiantax/$repo/issues?state=closed&limit=10&type=issues&since=$SINCE" | \
    jq -r '.[] | "#\(.number) \(.title)"' 2>/dev/null)
  if [ -n "$closed" ]; then
    echo "[$repo]"
    echo "$closed" | sed 's/^/  /'
  fi
done
```

**For a specific repo** — show more detail (up to 20, with closed date):
```bash
curl -sf -H "Authorization: token $ADMIN_TOKEN" \
  "http://localhost:3200/api/v1/repos/fabiantax/$REPO/issues?state=closed&limit=20&type=issues&since=$SINCE" | \
  jq -r '.[] | "#\(.number) \(.title) (closed \(.updated_at | .[0:10]))"'
```

### Step 4: Blackboard (scope: `all`, `agents`, repo name)

**For `all` / `agents`** — latest 5 entries:
```bash
curl -sf http://127.0.0.1:8080/v2/pipeline -X POST -H 'Content-Type: application/json' -d '{
  "requests":[
    {"type":"execute","stmt":{"sql":"SELECT author, substr(observation,1,120) as obs, created_at FROM blackboard_entries ORDER BY id DESC LIMIT 5"}},
    {"type":"close"}
  ]
}' | jq -r '.results[0].response.result.rows[] | "  \(.[2].value | .[0:16]) \(.[0].value): \(.[1].value)"'
```

**For a specific repo** — filter by author matching the repo's team name (e.g. `graphfusion-%` for GraphFusion):
```bash
# Map repo name to team prefix
# GraphFusion → graphfusion-%, fab-swarm → fab-swarm-%, localscout → localscout-%,
# atlas → atlas-%, fab-trader → fab-trader-%, fab-agent-runtime → mesh-%
curl -sf http://127.0.0.1:8080/v2/pipeline -X POST -H 'Content-Type: application/json' -d '{
  "requests":[
    {"type":"execute","stmt":{"sql":"SELECT author, substr(observation,1,120) as obs, created_at FROM blackboard_entries WHERE author LIKE \"'"$TEAM_PREFIX"'%\" ORDER BY id DESC LIMIT 10"}},
    {"type":"close"}
  ]
}' | jq -r '.results[0].response.result.rows[] | "  \(.[2].value | .[0:16]) \(.[0].value): \(.[1].value)"'
```

Also show reflection events for that team:
```bash
curl -sf http://127.0.0.1:8080/v2/pipeline -X POST -H 'Content-Type: application/json' -d '{
  "requests":[
    {"type":"execute","stmt":{"sql":"SELECT agent_name, verdict, latency_ms, created_at FROM reflection_events WHERE agent_name LIKE \"'"$TEAM_PREFIX"'%\" ORDER BY id DESC LIMIT 5"}},
    {"type":"close"}
  ]
}' | jq -r '.results[0].response.result.rows[] | "  \(.[3].value | .[0:16]) \(.[0].value): \(.[1].value) (\(.[2].value)ms)"' 2>/dev/null
```

### Step 5: CI runs (scope: `all`, `ci`, repo name)

```bash
ADMIN_TOKEN=$(grep 'GITEA_TOKEN_FAB_SWARM_CEO' ~/.config/fab-agent-runtime/secrets.env | cut -d= -f2)
# If scoped to a repo, only check that one. Otherwise check all.
REPOS="<repo-or-all-active-repos>"
for repo in $REPOS; do
  runs=$(curl -sf -H "Authorization: token $ADMIN_TOKEN" \
    "http://localhost:3200/api/v1/repos/fabiantax/$repo/actions/runs?limit=5" 2>/dev/null)
  echo "$runs" | jq -r '(.workflowRuns // [])[] | "  \(.name // .id): \(.status) \(.conclusion // "") (\(.updated_at // .created_at | .[0:10]))"' 2>/dev/null
done
```

### Step 6: Inference stack (scope: `all`, `agents`)

```bash
pgrep -x llama-server >/dev/null && echo "llama-server: running" || echo "llama-server: down"
systemctl --user is-active vllm 2>/dev/null | sed 's/active/vLLM: running/' | sed 's/inactive/vLLM: down/' | sed 's/failed/vLLM: failed/'
```

## Output format

### Full report (no args)

```
## Catch-up — <date>

### Agent Mesh: <N> services up, 0 failed

### Open Issues (109 total across 5 repos)
- GraphFusion: 79 open
- fab-swarm: 22 open
- localscout: 3 open
- fab-agent-runtime: 3 open
- fab-agent-mesh: 2 open

### Recently Closed (last 24h)
[repo-name]
  #42 Issue title
  ...

### Blackboard (latest)
  2026-06-03T20:22 mesh-digest-bot: ## Mesh Digest — ...

### CI
  No recent runs. / [repo] run-name: success/failure

### Inference
  llama-server: running, vLLM: down
```

### Repo-scoped report (e.g. `/catch-up GraphFusion`)

```
## Catch-up — GraphFusion — <date>

### Open Issues (79)
#354: Some issue title [bug]
#355: Another issue [enhancement]
...

### Milestones
  v0.4: 12 open / 8 closed

### Recently Closed (last 24h)
  #353 chore(core): test/bench + all-features clippy surface
  #352 chore(core): delete dead benches
  ...

### Blackboard (GraphFusion team)
  2026-06-02 12:44 graphfusion-cto: dependency status + route-label contract

### Reflections (GraphFusion agents)
  2026-06-03 graphfusion-cto: APPROVE (1200ms)

### CI
  No recent runs.
```

## What this skill is NOT

- Not a project planner. It reports state, doesn't propose work.
- Not a replacement for `/gitea-pm` or `/fab-agent-runtime`. Those manage; this observes.
- Not a persistent monitor. It's a point-in-time snapshot you run on demand.
