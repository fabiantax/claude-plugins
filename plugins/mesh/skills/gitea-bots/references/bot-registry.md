# Bot Registry — Agent-to-Gitea Coupling

Live registry of all bot accounts, tokens, and access.
Updated 2026-06-03.

## Naming Convention

```
login:      graphfusion-cto                    ← matches A2A service name
full_name:  Fabrik / GraphFusion / CTO         ← breadcrumb: Org / Team / Role
email:      graphfusion-cto@fabrik.strix.local ← org in domain
```

Hierarchy lives in Gitea membership (org → team → agent). Login stays short. full_name carries the breadcrumb.

## All Bots

### GraphFusion (team id=3)

| Login | ID | Port | Token Key | Repos |
|---|---|---|---|---|
| `graphfusion-ceo` | 10 | 50210 | `GITEA_TOKEN_GRAPHFUSION_CEO` | collaborator: `fabiantax/GraphFusion`; team: `fabrik/fab-brain`, `fabrik/fab-gnosis`, `fabrik/fab-types` |
| `graphfusion-cto` | 11 | 50211 | `GITEA_TOKEN_GRAPHFUSION_CTO` | same |
| `graphfusion-devops` | 12 | 50212 | `GITEA_TOKEN_GRAPHFUSION_DEVOPS` | same |

### Atlas (team id=4)

| Login | ID | Port | Token Key | Repos |
|---|---|---|---|---|
| `atlas-ceo` | 13 | 50220 | `GITEA_TOKEN_ATLAS_CEO` | collaborator: `fabiantax/Atlas` |
| `atlas-cto` | 14 | 50221 | `GITEA_TOKEN_ATLAS_CTO` | same |
| `atlas-agent` | 15 | 50225 | `GITEA_TOKEN_ATLAS_AGENT` | same |
| `atlas-reviewer` | — | 50292 | admin token (pre-convention) | same |

### fab-swarm (team id=5)

| Login | ID | Port | Token Key | Repos |
|---|---|---|---|---|
| `fab-swarm-ceo` | 16 | 50270 | `GITEA_TOKEN_FAB_SWARM_CEO` | collaborator: `fabiantax/fab-swarm`, `fabiantax/fab-agent-mesh`, `fabiantax/fab-agent-runtime`; team: all 13 `fabrik/*` |
| `fab-swarm-cto` | 17 | 50271 | `GITEA_TOKEN_FAB_SWARM_CTO` | same |

### fab-trader (team id=6)

| Login | ID | Port | Token Key | Repos |
|---|---|---|---|---|
| `fab-trader-ceo` | 18 | 50230 | `GITEA_TOKEN_FAB_TRADER_CEO` | collaborator: `fabiantax/fab-trader`; team: `fabrik/fab-brain`, `fabrik/fab-gnosis`, `fabrik/fab-types`, `fabrik/fab-pruner` |
| `fab-trader-cto` | 19 | 50231 | `GITEA_TOKEN_FAB_TRADER_CTO` | same |
| `fab-trader-signal-pipeline` | 24 | 50232 | `GITEA_TOKEN_FAB_TRADER_SIGNAL_PIPELINE` | same |
| `fab-trader-strategy-research` | 25 | 50233 | `GITEA_TOKEN_FAB_TRADER_STRATEGY_RESEARCH` | same |
| `fab-trader-surfaces` | 26 | 50234 | `GITEA_TOKEN_FAB_TRADER_SURFACES` | same |
| `fab-trader-rust-platform` | 23 | 50235 | `GITEA_TOKEN_FAB_TRADER_RUST_PLATFORM` | same |
| `fab-trader-data-platform` | 20 | 50236 | `GITEA_TOKEN_FAB_TRADER_DATA_PLATFORM` | same |
| `fab-trader-quant-ml` | 22 | 50237 | `GITEA_TOKEN_FAB_TRADER_QUANT_ML` | same |
| `fab-trader-devops` | 21 | 50238 | `GITEA_TOKEN_FAB_TRADER_DEVOPS` | same |

### Pre-convention (keep as-is)

| Login | Purpose |
|---|---|
| `mesh-ci-watcher` | CI monitoring |
| `mesh-digest-bot` | Mesh digest generator |
| `mesh-reviewer` | Mesh code review |
| `mesh-survey-bot` | Mesh survey |

## Orgs

| Org | Teams | Description |
|---|---|---|
| `fabrik` | graphfusion(3), atlas(4), swarm(5), fab-trader(6), Owners(2) | All product teams + shared ML primitives |
| `local-llm-lab` | Owners | Inference tooling (no bots) |

## Secrets

All tokens in `~/.config/fab-agent-runtime/secrets.env`. Key format: `GITEA_TOKEN_` + login uppercased, hyphens → underscores. No generic `GITEA_TOKEN` in the file — each service sets its own via `Environment=` in its systemd unit.

## Service Wiring Pattern

```ini
# In ~/.config/systemd/user/<login>.service
EnvironmentFile=%h/.config/fab-agent-runtime/secrets.env

# Bot identity override (after EnvironmentFile — later wins)
Environment=GITEA_TOKEN=<bot-scoped-token>
Environment=GIT_AUTHOR_NAME=<login>
Environment=GIT_AUTHOR_EMAIL=<login>@fabrik.strix.local
Environment=GIT_COMMITTER_NAME=<login>
Environment=GIT_COMMITTER_EMAIL=<login>@fabrik.strix.local
```
