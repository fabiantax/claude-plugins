# DevLake Gitea Plugin — Implementation Guide

## Overview

Apache DevLake doesn't have a native Gitea plugin. It supports Gitee (Alibaba's platform) and GitHub/GitLab. Since Gitea's API is modeled on GitHub's, the GitHub plugin is the best template.

## DevLake Plugin Architecture

Each DevLake plugin:
1. Registers data scopes (repos, orgs)
2. Collects data via API (commits, PRs, issues, reviews, refs)
3. Transforms raw API data into DevLake's domain models
4. Stores in DevLake's MySQL/Postgres for Grafana dashboards

Key domain models:
- `repo` — repository
- `commit` — git commit (with author info → per-agent attribution)
- `pull_request` — PR (poster → agent attribution)
- `issue` — issue (poster → agent attribution)
- `pull_request_comment` / `review` — code reviews
- `cicd_pipeline` / `cicd_task` — CI/CD runs (for DORA deployment frequency)
- `account` — maps to Gitea user/bot

## Gitea API → DevLake Domain Mapping

| DevLake Model | Gitea API Endpoint | Notes |
|---|---|---|
| `repo` | `GET /api/v1/repos/search` | Org + personal repos |
| `commit` | `GET /api/v1/repos/{owner}/{repo}/git/commits` | Author email → agent identity |
| `pull_request` | `GET /api/v1/repos/{owner}/{repo}/pulls` | `poster` field → agent identity |
| `pull_request_comment` | `GET /api/v1/repos/{owner}/{repo}/issues/{index}/comments` | Review comments |
| `issue` | `GET /api/v1/repos/{owner}/{repo}/issues` | `poster` field → agent identity |
| `review` | `GET /api/v1/repos/{owner}/{repo}/pulls/{index}/reviews` | Official review + body |
| `account` | `GET /api/v1/admin/users` | Map Gitea users → DevLake accounts |

## DORA Metrics Derivation

### Deployment Frequency
- Gitea Actions runs (`GET /api/v1/repos/{owner}/{repo}/actions/runs`)
- Or: tags/releases as deployment proxy
- DevLake's existing DORA dashboards handle the calculation

### Lead Time for Changes
- Commit timestamp → PR merge timestamp
- Per-agent: filter by commit author = bot user email

### Change Failure Rate
- Failed CI runs / total CI runs
- Or: revert PRs / total merged PRs

### MTTR (Mean Time to Recovery)
- Issue (bug) created → PR merged that fixes it
- Link via issue references in PR body (`Fixes #123`)

## Implementation Steps

1. **Fork DevLake's GitHub plugin** as `backend/plugins/gitea/`
2. **Adapt API calls**: Gitea uses `poster` where GitHub uses `user`, pagination is identical
3. **Add connection config**: Gitea instance URL + admin token
4. **Map bot users**: Add a config mapping `gitea_login → agent_name` for dashboard labeling
5. **Test with Strix Gitea**: Point at `http://host.containers.internal:3200`
6. **Contribute upstream**: Apache DevLake accepts new plugins via PR

## Resources

- DevLake plugin development docs: https://devlake.apache.org/docs/DeveloperManuals/PluginDevelopment
- DevLake GitHub plugin source: https://github.com/apache/incubator-devlake/tree/main/backend/plugins/github
- Gitea Swagger API: http://localhost:3200/api/swagger
