# Gitea Actions / CI — logs, runs, runners

Reference for reading CI results and keeping the self-hosted runners healthy on the
local Gitea (1.26.1, `localhost:3200`). Load this when a CI run failed, when a runner
crash-loops, or when an Actions log needs to be read programmatically.

## Reading run results and logs

**Two distinct surfaces — do not confuse them:**

| Goal | Endpoint | Returns |
|------|----------|---------|
| List recent runs/tasks | `GET /api/v1/repos/{owner}/{repo}/actions/tasks?limit=N` | JSON: id, status, run_number, job name, workflow |
| Read a job's log text | `GET /{owner}/{repo}/actions/runs/{run}/jobs/{jobId}/logs` | **`text/plain`** — the actual log |
| Server version | `GET /api/v1/version` | `{"version":"1.26.1"}` |

```bash
U="fabiantax:Strix2024!"; R="http://localhost:3200"
# list failing runs
curl -s -u "$U" "$R/api/v1/repos/fabiantax/GraphFusion/actions/tasks?limit=20" \
  | jq -r '.workflow_runs[]? // .[]? | "\(.id) \(.status) \(.run_number) \(.name)"'
# pull a job log as plain text (run index + internal job id from the run page URL)
curl -s -u "$U" "$R/fabiantax/GraphFusion/actions/runs/2077/jobs/3516/logs"
```

**GOTCHA — the view page is a JS shell.** `GET /{owner}/{repo}/actions/runs/{run}/jobs/{jobId}`
(no `/logs`) returns an HTML page whose log lines are streamed in by JavaScript from the
`/logs` endpoint. Fetching that page yields a near-empty HTML stub with **no log text** —
this is the trap that makes it look like "logs aren't API-readable." They are; append `/logs`.

**GOTCHA — `strix-build` mutex truncation.** A run that blocks on the build mutex shows its
persisted log ending at `Waiting for build slot (another build is running)...`. The
post-build test-result lines are not in the retrievable artifact for that run — that is a
property of *that run's* truncated log, not a missing API. Re-run when the mutex is free, or
read the test output from a run that actually acquired the slot.

**Default-on caveat:** reach for the `/logs` endpoint before ever asserting "Gitea can't show
CI output." Check the API first; do not claim a capability is absent.

## Runners on this box

Two runners serve the same host labels (`self-hosted`, `strix-host`, `ubuntu-latest/-22.04/-24.04`),
both host-mode (no containers):

| Runner | Service / launch | Config | Registration file |
|--------|------------------|--------|-------------------|
| systemd `gitea-runner` | `systemctl --user … gitea-runner` | `~/.local/share/gitea-runner/config.yaml` | `~/.local/share/gitea-runner/.runner` |
| manual `act_runner` | `~/code/tools/act_runner daemon --config ~/.config/act_runner/runner-config.yaml` | that config | `~/.local/share/act_runner/runner.json` |

Two runners = 2-way job parallelism. With only one alive, a 3rd concurrent job queues and CI
crawls. **Do not kill a runner while it has in-flight jobs** — that aborts the runs.

### Crash-loop: "Unauthenticated … unregistered runner"

Symptom: `gitea-runner.service` restart counter climbing into the thousands,
`fail to invoke Declare … unregistered runner`. Cause: the local `.runner`/`runner.json`
registration is stale — the server-side `action_runner` row was deleted or its token rotated.
The file existing does **not** mean it authenticates.

```bash
# 1. mint a fresh global token from the gitea container
podman exec gitea gitea actions generate-runner-token        # 40-char token
# 2. stop the loop, back up the stale file
systemctl --user stop gitea-runner.service
cd ~/.local/share/gitea-runner && cp -a .runner .runner.stale.bak
# 3. re-register (labels MUST match config.yaml; instance from the old .runner address)
~/.local/bin/gitea-runner register --no-interactive \
  --instance http://localhost:3200 --token <TOKEN> --name strix-host \
  --labels "self-hosted:host,strix-host:host,ubuntu-latest:host,ubuntu-22.04:host,ubuntu-24.04:host"
# 4. start + verify (want active/running/0)
systemctl --user start gitea-runner.service
systemctl --user show gitea-runner.service -p ActiveState -p SubState -p NRestarts
```

Inspect registered runners (stale ghosts accumulate; `last_online` is unix epoch):
```bash
podman exec gitea sqlite3 /data/gitea/gitea.db \
  "SELECT id,uuid,name,last_online FROM action_runner;"
```

The manual `act_runner` re-registers analogously: `rm ~/.local/share/act_runner/runner.json`,
get a token, `act_runner register --no-interactive --instance http://localhost:3200 --token <T> --name strix-runner --config ~/.config/act_runner/runner-config.yaml`.

### Git-LFS checkout fails in ~1s

`actions/checkout@v4` with `lfs: true` fails the job: `git lfs install --local` →
`Hook already exists: pre-push` → exit 2. Cause: host `init.templateDir = ~/.git-templates`
whose `hooks/pre-push` is the force-push-protection hook; every `git init` (including
checkout's) seeds it and `git lfs install` refuses to clobber it.

**Fix (workflow-local — do NOT weaken the host hook):** check out *without* `lfs: true`, then
add a step `run: git lfs pull`. `git lfs pull` (fetch + checkout) replaces pointer files
without reinstalling hooks, reusing checkout's auth extraheader against the gitea origin.
Applied in `.gitea/workflows/geodata-nightly.yml`.

### Known instance bug

Gitea 1.26.1 logs a recurring `start_schedule_tasks … assignment to entry in nil map` panic.
Other scheduled workflows still fire, so it is non-fatal — an open upstream bug, not a misconfig.

## Branch protection (status-check gating)

```bash
curl -u "fabiantax:Strix2024!" -X PATCH \
  "http://localhost:3200/api/v1/repos/{owner}/{repo}/branch_protections/main" \
  -H "Content-Type: application/json" -d '{"enable_status_check":true}'
```
Disable (`false`) when the runner is offline — otherwise PRs wedge on checks that never run.

## Auto-versioning workflow pattern

`.gitea/workflows/bump-version.yml` bumps patch on every push to `main`: strips a `-mvp`
suffix, bumps patch, commits `chore(release): …`, tags `vX.Y.Z`, moves `v-latest`. It **skips
when the commit subject starts with `chore(release):`** (prevents an infinite loop) and needs
a `RELEASE_TOKEN` repo secret.
