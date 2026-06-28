---
name: gitea
description: This skill should be used when the user asks to "manage a gitea repo", "read CI logs", "check Actions results", "why did CI fail", "fix the gitea runner", "set up a Cargo git dependency", "add an issue dependency", "create a project board", "approve a PR via API", or works with the local self-hosted Gitea instance on localhost:3200 (repos, Actions/CI, runners, issues, project boards, PR reviews, config).
---

# Gitea Local Repository Manager

## When to Use
- Creating or managing repos on the local Gitea instance
- Reading CI / Actions run results and job logs (`references/actions-ci.md`)
- Diagnosing or re-registering self-hosted runners (`references/actions-ci.md`)
- Setting up Cargo git dependencies against local Gitea
- Configuring mirror remotes (GitHub <-> Gitea)
- Managing Gitea API tokens, users, or org settings
- Scripting issues, dependencies, project boards, or PR reviews (`references/api-cookbook.md`)

## Instance Details

| What | Value |
|------|-------|
| URL (local) | `http://gitea.localhost:3200` |
| URL (Tailscale) | `http://100.112.37.119:3200` |
| SSH | `git@gitea` (port 2222 via ~/.ssh/config) |
| Admin user | `fabiantax` |
| Service | `systemctl --user start/stop/restart gitea` |
| Data | `~/.local/share/gitea/` |
| Config (active) | `~/.local/share/gitea/gitea/conf/app.ini` — edit inside the container; `~/.config/gitea/app.ini` is **ignored** (see `references/api-cookbook.md`) |
| Container | `podman ps -a --filter name=gitea` |

## Quick Commands

```bash
gitea ls                          # list repos
gitea create my-crate             # create repo + add remote
gitea clone my-crate              # clone via SSH
gitea push                        # push current branch to gitea
gitea delete my-crate             # delete repo
gitea api GET /repos/search       # raw API call
gitea token my-token              # generate API token
```

## Git Remote Shorthand

`~/.gitconfig` rewrites `gitea:` to the full SSH URL:
```bash
# In any git repo, just use:
git remote add gitea gitea:fabiantax/GraphFusion.git
git push gitea main

# Instead of:
git remote add gitea git@gitea:fabiantax/GraphFusion.git
```

## Cargo Git Dependencies

### From Strix (local)
```toml
[dependencies]
graphfusion-core = { git = "http://gitea.localhost:3200/fabiantax/GraphFusion.git", branch = "main" }
```

### From MacBook (Tailscale)
```toml
[dependencies]
graphfusion-core = { git = "http://100.112.37.119:3200/fabiantax/GraphFusion.git", branch = "main" }
```

### Via SSH (either machine)
```toml
[dependencies]
graphfusion-core = { git = "ssh://gitea/fabiantax/GraphFusion.git", branch = "main" }
```

## CI / Actions (logs + runners)

Read CI results via the API — **do not assert "logs aren't API-readable" before checking.**

| Goal | Endpoint | Returns |
|------|----------|---------|
| List recent runs | `GET /api/v1/repos/{owner}/{repo}/actions/tasks?limit=N` | JSON (id, status, run_number, job) |
| Read a job log | `GET /{owner}/{repo}/actions/runs/{run}/jobs/{jobId}/logs` | **`text/plain`** |

```bash
U="fabiantax:Strix2024!"; R="http://localhost:3200"
curl -s -u "$U" "$R/fabiantax/GraphFusion/actions/runs/2077/jobs/3516/logs"   # plain-text log
```

Key gotchas (full detail in `references/actions-ci.md`):
- The `…/jobs/{jobId}` **view page is a JS shell** — log lines load client-side; fetching it yields an empty stub. Append `/logs` for the text.
- A run blocked on `strix-build` truncates its log at `Waiting for build slot…` — read a run that acquired the slot.
- Runner crash-loop ("unregistered runner") = stale `.runner`; re-register with a fresh `generate-runner-token`.
- `actions/checkout` `lfs:true` fails on the host hook; use a `git lfs pull` step instead.

## API Cookbook (issues, boards, reviews, config)

Non-obvious endpoints, each verified — see `references/api-cookbook.md`:
- **Issue dependencies** need `{"owner","repo","index"}` (field is `repo`, not `name`); cross-repo works.
- **Project boards** have no REST API — drive the web session (CSRF disabled); `issue_ids` = internal `.id`, not display number.
- **PR approval** is a two-call dance: create (`APPROVE`→PENDING) then submit (`APPROVED`→official).
- **Config edits** must go to `/data/gitea/conf/app.ini` inside the container — `~/.config/gitea/app.ini` is silently ignored.

## Service Management
```bash
systemctl --user start gitea     # Start
systemctl --user stop gitea      # Stop
systemctl --user restart gitea   # Restart
systemctl --user status gitea    # Check status
journalctl --user -fu gitea      # Follow logs
```

## Migrating to Another Machine

When moving Gitea to a different host, change ONE thing in each location:

| Where | What to change |
|-------|---------------|
| `~/.ssh/config` | `HostName` under `Host gitea` → new IP |
| `~/.gitconfig` | `insteadOf` target → new IP |
| `~/.local/bin/gitea` | `GITEA_URL` → new address |
| `~/.config/gitea/app.ini` | `DOMAIN` and `ROOT_URL` → new address |

All git remotes (`gitea:fabiantax/repo.git`) keep working because they go through the SSH config.

## Known Issues
- Port 3000 is used by Open WebUI, Gitea runs on 3200
- Bound to `127.0.0.1` + Tailscale IP only — not exposed on LAN
- Container user is `git` (UID inside container)
- Gitea 1.26.1 logs a recurring `start_schedule_tasks … nil map` panic — non-fatal (see `references/actions-ci.md`)

## Additional Resources

- **`references/actions-ci.md`** — Reading CI run results + job logs via the API (and the JS-shell view-page / `strix-build`-truncation gotchas), self-hosted runner management (crash-loop re-registration, the two runners, LFS-checkout fix), branch-protection toggle, auto-versioning workflow pattern.
- **`references/api-cookbook.md`** — Verified non-obvious endpoints: active config path, issue dependencies (`{owner,repo,index}`), project boards (web-session, internal `.id`), PR-review two-call approval, host-service webhooks.

Use `/gitea-pm` (skill + agent) for higher-level project management — milestones, labels, kanban, batch issue ops.
