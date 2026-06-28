---
name: gitea-bots
description: Manage Gitea bot accounts for AI agents — creation, team assignment, A2A profile coupling, per-agent metrics attribution, and DORA integration with Apache DevLake.
argument-hint: "[command] — e.g. 'create graphfusion-cto', 'couple atlas-cto', 'list', 'metrics graphfusion-cto'"
---

# Gitea Bot Accounts for AI Agents

## When to Use
- Creating or managing bot accounts for AI agents on the local Gitea
- Coupling Gitea bot accounts to A2A agent service profiles
- Querying per-agent attribution (commits, PRs, reviews, issues)
- Setting up org/team structures for value streams (agent teams)
- Integrating with Apache DevLake for DORA metrics

## Instance

| What | Value |
|------|-------|
| URL | `http://127.0.0.1:3200` |
| API | `http://127.0.0.1:3200/api/v1` |
| Admin | `fabiantax` / `Strix2024!` |
| Token env | `$GITEA_TOKEN` (from `~/.bashrc.d/99-secrets.sh`) |

**Setup before use:**
```bash
[ -n "$GITEA_TOKEN" ] || source ~/.bashrc.d/99-secrets.sh
```

---

## Naming Convention

Bot login = A2A service name. No prefixes, no codenames — the agent name is the identity.

```
login:      graphfusion-cto                          ← git log, PR author, API calls
full_name:  Fabrik / GraphFusion / CTO                ← Gitea profile breadcrumb
email:      graphfusion-cto@fabrik.strix.local        ← encodes org in domain
```

The hierarchy (org → team → agent) lives in **Gitea membership** — queryable, mutable, no rename needed when structure changes. The `full_name` field carries the human-readable breadcrumb. The login stays short and matches the A2A service name exactly.

| Level | Source of truth | Example |
|---|---|---|
| Org (value stream) | Gitea org membership | `fabrik` |
| Team (product) | Gitea team within org | `graphfusion` |
| Agent (bot) | Login = A2A service name | `graphfusion-cto` |

---

## Access Model

Gitea org teams can only govern **org-owned repos**. Product repos live under `fabiantax/` (personal), so there are two access mechanisms:

| Repo type | Access mechanism | Example |
|---|---|---|
| `fabrik/*` (org repos) | Team assignment via `PUT /teams/{id}/repos/{org}/{repo}` | swarm team → all `fabrik/fab-*` repos |
| `fabiantax/*` (personal repos) | Direct collaborator via `PUT /repos/{owner}/{repo}/collaborators/{bot}` | `graphfusion-cto` → `fabiantax/GraphFusion` |

Cross-team access: an org repo can be assigned to multiple teams (e.g., `fabrik/fab-gnosis` is in both `graphfusion` and `fab-trader` teams).

### Token scopes

Bot tokens are scoped to `["write:repository", "write:issue", "read:organization"]` — enough to create issues, PRs, push commits, and read org data. **No `read:user`** (can't call `/api/v1/user`), **no admin** scope.

### Verified access isolation

```
atlas-ceo → Atlas repo → 200 ✓
atlas-ceo → fab-trader repo → 404 (no access, correct)
```

---

## Deployed Bots (2026-06-03)

### GraphFusion team (id=3)

| Bot | ID | Port | Token key | Repo access |
|---|---|---|---|---|
| `graphfusion-ceo` | 10 | 50210 | `GITEA_TOKEN_GRAPHFUSION_CEO` | `fabiantax/GraphFusion`, `fabrik/fab-gnosis`, `fabrik/fab-types` |
| `graphfusion-cto` | 11 | 50211 | `GITEA_TOKEN_GRAPHFUSION_CTO` | same |
| `graphfusion-devops` | 12 | 50212 | `GITEA_TOKEN_GRAPHFUSION_DEVOPS` | same |

### Atlas team (id=4)

| Bot | ID | Port | Token key | Repo access |
|---|---|---|---|---|
| `atlas-ceo` | 13 | 50220 | `GITEA_TOKEN_ATLAS_CEO` | `fabiantax/Atlas` |
| `atlas-cto` | 14 | 50221 | `GITEA_TOKEN_ATLAS_CTO` | same |
| `atlas-agent` | 15 | 50225 | `GITEA_TOKEN_ATLAS_AGENT` | same |
| `atlas-reviewer` | — | 50292 | admin token | same |

### fab-swarm team (id=5)

| Bot | ID | Port | Token key | Repo access |
|---|---|---|---|---|
| `fab-swarm-ceo` | 16 | 50270 | `GITEA_TOKEN_FAB_SWARM_CEO` | `fabiantax/fab-swarm`, `fabiantax/fab-agent-mesh`, `fabiantax/fab-agent-runtime`, all `fabrik/*` |
| `fab-swarm-cto` | 17 | 50271 | `GITEA_TOKEN_FAB_SWARM_CTO` | same |

### fab-trader team (id=6)

| Bot | ID | Port | Token key | Repo access |
|---|---|---|---|---|
| `fab-trader-ceo` | 18 | 50230 | `GITEA_TOKEN_FAB_TRADER_CEO` | `fabiantax/fab-trader`, `fabrik/fab-brain`, `fabrik/fab-gnosis`, `fabrik/fab-types`, `fabrik/fab-pruner` |
| `fab-trader-cto` | 19 | 50231 | `GITEA_TOKEN_FAB_TRADER_CTO` | same |
| `fab-trader-signal-pipeline` | 24 | 50232 | `GITEA_TOKEN_FAB_TRADER_SIGNAL_PIPELINE` | same |
| `fab-trader-strategy-research` | 25 | 50233 | `GITEA_TOKEN_FAB_TRADER_STRATEGY_RESEARCH` | same |
| `fab-trader-surfaces` | 26 | 50234 | `GITEA_TOKEN_FAB_TRADER_SURFACES` | same |
| `fab-trader-rust-platform` | 23 | 50235 | `GITEA_TOKEN_FAB_TRADER_RUST_PLATFORM` | same |
| `fab-trader-data-platform` | 20 | 50236 | `GITEA_TOKEN_FAB_TRADER_DATA_PLATFORM` | same |
| `fab-trader-quant-ml` | 22 | 50237 | `GITEA_TOKEN_FAB_TRADER_QUANT_ML` | same |
| `fab-trader-devops` | 21 | 50238 | `GITEA_TOKEN_FAB_TRADER_DEVOPS` | same |

### Pre-convention accounts (keep as-is)

| Login | Purpose |
|---|---|
| `mesh-ci-watcher` | CI monitoring |
| `mesh-digest-bot` | Mesh digest generator |
| `mesh-reviewer` | Mesh code review |
| `mesh-survey-bot` | Mesh survey |

---

## Service Wiring

Each agent's systemd unit is wired with its own Gitea identity. The pattern:

```ini
# ~/.config/systemd/user/<agent-name>.service

[Service]
# ... other Environment= lines ...

# Shared secrets (ZAI_API_KEY, bot-specific GITEA_TOKEN_*, ...) — no generic GITEA_TOKEN here
EnvironmentFile=%h/.config/fab-agent-runtime/secrets.env

# Bot identity override — placed AFTER EnvironmentFile so it wins.
# systemd processes Environment= in document order; later wins.
Environment=GITEA_TOKEN=<this-bot's-scoped-token>
Environment=GIT_AUTHOR_NAME=<login>
Environment=GIT_AUTHOR_EMAIL=<login>@fabrik.strix.local
Environment=GIT_COMMITTER_NAME=<login>
Environment=GIT_COMMITTER_EMAIL=<login>@fabrik.strix.local
```

### Key detail: systemd env precedence

`Environment=` placed **after** `EnvironmentFile=` overrides same-name vars from the file. The shared `secrets.env` has per-bot `GITEA_TOKEN_*` vars but **no generic `GITEA_TOKEN`** — each service sets its own via the inline `Environment=`.

### Secrets file

`~/.config/fab-agent-runtime/secrets.env` contains:
```
ZAI_API_KEY=<key>
# Per-bot Gitea tokens (generated 2026-06-03)
GITEA_TOKEN_GRAPHFUSION_CEO=<token>
GITEA_TOKEN_GRAPHFUSION_CTO=<token>
# ... one per bot ...
```

**No generic `GITEA_TOKEN`** in the file — removed so the per-service override doesn't clash.

### Verify a running agent's identity
```bash
pid=$(systemctl --user show graphfusion-cto.service -p MainPID --value)
cat /proc/${pid}/environ | tr '\0' '\n' | grep -E '^GITEA_TOKEN=|^GIT_AUTHOR|^GIT_COMMITTER'
```

---

## Bot Account CRUD

### Create a bot
```bash
create_bot() {
  local login="$1" full_name="$2" org="${3:-fabrik}"
  local email="${login}@${org}.strix.local"
  curl -sS -X POST "http://127.0.0.1:3200/api/v1/admin/users" \
    -u "fabiantax:Strix2024!" \
    -H 'content-type: application/json' \
    -d "$(jq -n \
      --arg u "$login" --arg e "$email" --arg f "$full_name" \
      '{username:$u, email:$e, full_name:$f,
        password: "bot-no-login-" + (now | tostring),
        must_change_password: false,
        visibility: "private", restricted: true}')" \
    | jq '{login: .login, id: .id}'
}
# create_bot "graphfusion-cto" "Fabrik / GraphFusion / CTO" "fabrik"
```

**Note:** Admin API requires basic auth (`-u fabiantax:Strix2024!`), not token auth — the standard `$GITEA_TOKEN` lacks `write:admin` scope.

### Generate API token for a bot
```bash
gen_bot_token() {
  local login="$1" token_name="${2:-agent-token}"
  curl -sS -X POST "http://127.0.0.1:3200/api/v1/users/${login}/tokens" \
    -u "fabiantax:Strix2024!" \
    -H 'content-type: application/json' \
    -d '{"name":"agent-token","scopes":["write:repository","write:issue","read:organization"]}' \
    | jq -r '.sha1'
}
# gen_bot_token "graphfusion-cto"  # returns the token string
```

**Note:** `scopes` must be a JSON array, not a string. Required scope for `/api/v1/user`: `read:user` (not included — agents don't need it).

### List all bot accounts
```bash
curl -sS -u "fabiantax:Strix2024!" \
  "http://127.0.0.1:3200/api/v1/admin/users?limit=50" \
  | jq '[.[] | select(.login != "fabian" and .login != "fabiantax") | {login, email, full_name}]'
```

### Delete a bot
```bash
curl -sS -X DELETE "http://127.0.0.1:3200/api/v1/admin/users/${BOT_LOGIN}" \
  -u "fabiantax:Strix2024!"
```

---

## Org & Team Management

### Teams in `fabrik` org

| Team | ID | Repos |
|---|---|---|
| `graphfusion` | 3 | `fabrik/fab-brain`, `fabrik/fab-gnosis`, `fabrik/fab-types` (cross-team ML deps) |
| `atlas` | 4 | (no org repos — product repo is `fabiantax/Atlas` with collaborator access) |
| `swarm` | 5 | all 13 `fabrik/*` repos (ML primitives) |
| `fab-trader` | 6 | `fabrik/fab-brain`, `fabrik/fab-gnosis`, `fabrik/fab-types`, `fabrik/fab-pruner` (ML deps) |

### Add repo to team (org repos only)
```bash
# Only works for repos owned by the org (fabrik/*)
curl -sS -X PUT "http://127.0.0.1:3200/api/v1/teams/${TEAM_ID}/repos/${ORG}/${REPO}" \
  -u "fabiantax:Strix2024!" -H 'content-type: application/json' -d '{}'
```

### Add bot as collaborator (personal repos)
```bash
# For repos under fabiantax/* — the only way to give bot access
curl -sS -X PUT "http://127.0.0.1:3200/api/v1/repos/fabiantax/${REPO}/collaborators/${BOT_LOGIN}" \
  -u "fabiantax:Strix2024!" -H 'content-type: application/json' -d '{"permission":"write"}'
```

### Add/remove bot from team
```bash
# Add
curl -sS -X PUT "http://127.0.0.1:3200/api/v1/teams/${TEAM_ID}/members/${BOT_LOGIN}" \
  -u "fabiantax:Strix2024!"

# Remove
curl -sS -X DELETE "http://127.0.0.1:3200/api/v1/teams/${TEAM_ID}/members/${BOT_LOGIN}" \
  -u "fabiantax:Strix2024!"
```

### Create new team
```bash
curl -sS -X POST "http://127.0.0.1:3200/api/v1/orgs/fabrik/teams" \
  -u "fabiantax:Strix2024!" -H 'content-type: application/json' \
  -d '{"name":"new-team","description":"...","permission":"write","units":["repo.code","repo.issues","repo.pulls","repo.releases"]}'
```

---

## Full Bootstrap for a New Agent

End-to-end: create bot → token → secrets → team → repo access → service wiring → restart.

```bash
bootstrap_agent() {
  local login="$1" breadcrumb="$2" team_name="$3" repo="$4"
  local org="fabrik"

  # 1. Create bot account
  create_bot "$login" "$breadcrumb" "$org"

  # 2. Generate scoped token
  local token=$(gen_bot_token "$login")
  echo "Token: ${token}"

  # 3. Store in secrets.env
  local key=$(echo "$login" | tr '[:lower:]-' '[:upper:]_')
  echo "GITEA_TOKEN_${key}=${token}" >> ~/.config/fab-agent-runtime/secrets.env

  # 4. Add to team
  local team_id=$(curl -sS -u "fabiantax:Strix2024!" \
    "http://127.0.0.1:3200/api/v1/orgs/${org}/teams" \
    | jq ".[] | select(.name==\"${team_name}\") | .id")
  curl -sS -X PUT "http://127.0.0.1:3200/api/v1/teams/${team_id}/members/${login}" \
    -u "fabiantax:Strix2024!"

  # 5. Add repo access (collaborator for personal repos, team assignment for org repos)
  if [[ "$repo" == fabrik/* ]]; then
    curl -sS -X PUT "http://127.0.0.1:3200/api/v1/teams/${team_id}/repos/${repo}" \
      -u "fabiantax:Strix2024!" -H 'content-type: application/json' -d '{}'
  else
    curl -sS -X PUT "http://127.0.0.1:3200/api/v1/repos/${repo}/collaborators/${login}" \
      -u "fabiantax:Strix2024!" -H 'content-type: application/json' -d '{"permission":"write"}'
  fi

  # 6. Patch service unit (add after EnvironmentFile= line)
  local unit="${HOME}/.config/systemd/user/${login}.service"
  if [ -f "$unit" ]; then
    sed -i "/^EnvironmentFile=/a\\
\\
# Bot identity override (fabrik org, agent-specific Gitea token)\\
Environment=GITEA_TOKEN=${token}\\
Environment=GIT_AUTHOR_NAME=${login}\\
Environment=GIT_AUTHOR_EMAIL=${login}@${org}.strix.local\\
Environment=GIT_COMMITTER_NAME=${login}\\
Environment=GIT_COMMITTER_EMAIL=${login}@${org}.strix.local" "$unit"
    systemctl --user daemon-reload
    systemctl --user restart "${login}.service"
  fi

  echo "Bootstrapped: ${login} (${breadcrumb})"
  echo "Token key: GITEA_TOKEN_${key}"
}
# bootstrap_agent "graphfusion-newbot" "Fabrik / GraphFusion / New Role" "graphfusion" "fabiantax/GraphFusion"
```

---

## Per-Agent Attribution Queries

### Commits by author
```bash
for repo in $(curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "http://127.0.0.1:3200/api/v1/repos/search?limit=100" \
  | jq -r '.data[].full_name'); do
  count=$(curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
    "http://127.0.0.1:3200/api/v1/repos/${repo}/commits?author=${BOT_LOGIN}&limit=1" \
    | jq 'length')
  [ "$count" -gt 0 ] && echo "${repo}: ${count}+ commits by ${BOT_LOGIN}"
done
```

### PRs by author
```bash
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "http://127.0.0.1:3200/api/v1/repos/${REPO}/pulls?poster=${BOT_LOGIN}&state=all&limit=50" \
  | jq '[.[] | {number, title, state, created: .created_at, merged: .merged_at}]'
```

### Issues created by bot
```bash
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "http://127.0.0.1:3200/api/v1/repos/${REPO}/issues?poster=${BOT_LOGIN}&state=all&type=issues&limit=50" \
  | jq '[.[] | {number, title, state, created: .created_at}]'
```

### Reviews by bot
```bash
curl -sS -H "Authorization: token ${GITEA_TOKEN}" \
  "http://127.0.0.1:3200/api/v1/repos/${REPO}/pulls/${PR_NUMBER}/reviews" \
  | jq "[.[] | select(.user.login==\"${BOT_LOGIN}\")]"
```

---

## DORA Metrics with Apache DevLake

Apache DevLake (`https://devlake.apache.org`) is an open-source dev data platform that provides DORA metrics dashboards out of the box, powered by Grafana.

### What DevLake gives us
- **DORA dashboards**: Deployment Frequency, Lead Time for Changes, Change Failure Rate, MTTR
- **Per-author/per-team metrics**: commits, PRs, issues, reviews
- **Blueprints**: scheduled data collection from dev tools
- **Plugin architecture**: extensible data sources (GitHub, GitLab, BitBucket, Gitee, Jenkins, Jira...)

### The gap: no native Gitea plugin
DevLake supports **Gitee** (Alibaba's cloud platform), not self-hosted Gitea. However:
- Gitea's API is modeled on GitHub's — the DevLake GitHub plugin is a strong template
- DevLake's plugin system is Go-based and documented
- Writing a Gitea plugin maps: Gitea API endpoints → DevLake domain models (commits, PRs, issues, reviews)

### Deployment architecture
```
Gitea (:3200)  ──►  DevLake Gitea Plugin (new)  ──►  DevLake  ──►  Grafana dashboards
     │                                                    │
     ├── repos, PRs, issues, commits                      ├── DORA metrics (4 keys)
     ├── bot user accounts (attribution)                  ├── Per-agent throughput
     └── org/team structure                               └── Team-level aggregates
```

See `references/devlake-gitea-plugin.md` for the plugin implementation guide.

---

## Temporary Teams

Agents belong to exactly 1 value stream (org) but can join temporary cross-functional teams:

```bash
# Create a temporary team for a sprint/cross-cutting effort
curl -sS -X POST "http://127.0.0.1:3200/api/v1/orgs/fabrik/teams" \
  -u "fabiantax:Strix2024!" -H 'content-type: application/json' \
  -d '{"name":"sprint-42-cross-cut","permission":"write","units":["repo.code","repo.issues","repo.pulls"]}'

# Add agents from different value streams
curl -sS -X PUT "http://127.0.0.1:3200/api/v1/teams/${TEAM_ID}/members/graphfusion-cto" \
  -u "fabiantax:Strix2024!"
curl -sS -X PUT "http://127.0.0.1:3200/api/v1/teams/${TEAM_ID}/members/atlas-cto" \
  -u "fabiantax:Strix2024!"

# When the sprint ends, dissolve:
curl -sS -X DELETE "http://127.0.0.1:3200/api/v1/teams/${TEAM_ID}" -u "fabiantax:Strix2024!"
```

---

## Existing Orgs

| Org | Full Name | Description |
|---|---|---|
| `fabrik` | Fabrik — Shared ML Primitives | ML library ecosystem + all product teams |
| `local-llm-lab` | Local LLM Lab | Inference tooling & benchmarks (no bots) |

---

## Git Attribution (for Claude Code sessions)

When Claude Code runs on behalf of an agent, set git identity so commits attribute correctly:

```bash
export GIT_AUTHOR_NAME="graphfusion-cto"
export GIT_AUTHOR_EMAIL="graphfusion-cto@fabrik.strix.local"
export GIT_COMMITTER_NAME="graphfusion-cto"
export GIT_COMMITTER_EMAIL="graphfusion-cto@fabrik.strix.local"
```

Or per-commit:
```bash
git commit --author="graphfusion-cto <graphfusion-cto@fabrik.strix.local>" -m "feat: ..."
```

What this looks like in `git log`:
```
a3f4b2c feat: add CSR edge compression         graphfusion-cto <graphfusion-cto@fabrik.strix.local>
7e1d9a0 fix: false positive in trait impl       atlas-cto <atlas-cto@fabrik.strix.local>
c2b8f1e refactor: stigmergy coordination loop   fab-swarm-cto <fab-swarm-cto@fabrik.strix.local>
```

---

## Known Issues

- **No `read:user` scope**: Bot tokens can't call `/api/v1/user`. Agents authenticate fine for repo/issue/PR operations — just can't read their own profile.
- **Personal repos can't use team access**: `fabiantax/*` repos require per-bot collaborator grants. Only `fabrik/*` repos support team-based access control.
- **`atlas-reviewer` uses admin token**: Pre-convention account, no scoped bot token. If it needs isolation, create a new token with `gen_bot_token`.
- **Generic `GITEA_TOKEN` removed from secrets.env**: Services that don't have a bot identity override (e.g., `fab-engine`) must set `GITEA_TOKEN` inline in their unit if needed.

---

## Additional Resources

- **`references/devlake-gitea-plugin.md`** — Implementation guide for the DevLake Gitea plugin
- **`references/bot-registry.md`** — Live registry of all bot accounts, tokens, and team assignments
- **`references/agent-grounding.md`** — Agent grounding system: anti-hallucination knowledge files

Use `/gitea` for repo management, `/gitea-pm` for issue/PR/milestone operations, and this skill (`/gitea-bots`) for agent identity management and DORA metrics.
