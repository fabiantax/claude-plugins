# Gitea API cookbook — non-obvious endpoints

Verified quirks for the local Gitea (1.26.1, `localhost:3200`, admin `fabiantax:Strix2024!`).
Load this when scripting issue dependencies, project boards, PR reviews, or editing the
server config. Each entry below cost real debugging time — trust the documented shape, not
the swagger default.

## Config file path (the swagger/CLAUDE.md path is wrong)

The **active** config is `~/.local/share/gitea/gitea/conf/app.ini`, NOT `~/.config/gitea/app.ini`.
The container mounts `~/.local/share/gitea → /data` and `~/.config/gitea → /etc/gitea`, but sets
`GITEA_CUSTOM=/data/gitea`, so Gitea reads `/data/gitea/conf/app.ini`. Edits to
`~/.config/gitea/app.ini` are **silently ignored**.

The real file is owned by the userns-mapped git uid, so edit it from inside the container:
```bash
podman exec gitea sh -c 'cat >> /data/gitea/conf/app.ini <<EOF

[section]
KEY = value
EOF'
systemctl --user restart gitea
podman exec gitea grep -nE "^\[section\]|KEY" /data/gitea/conf/app.ini   # verify
```

## Issue dependencies (blocked-by)

```
POST /api/v1/repos/{owner}/{repo}/issues/{index}/dependencies
```
Body MUST be the full `IssueMeta`: `{"owner":"fabiantax","repo":"GraphFusion","index":N}`
(N = the blocking issue's **display number**). The field is **`repo`**, not `name`. The
swagger-suggested `{"index":N}` and `{"owner","name","index"}` both fail with a misleading
`IsErrRepoNotExist` 404. **Cross-repo deps work** — a localscout issue can be blocked-by a
GraphFusion issue by passing that repo's owner/repo.

Note: GraphFusion has **no `size:*` labels** (record size in the body); localscout DOES have
`size:S/M/L/XL`. No `epic`/`part-of` label anywhere — express epic linkage via "Part of #N"
in the body plus the dependency tree.

## Project boards (no REST API — drive the web session)

Gitea 1.26.1 has **zero project paths in swagger**. Drive boards via the authenticated web
session. **CSRF is disabled on this instance** — POSTs need only the session cookie; there is
no `_csrf` field/cookie/meta to hunt for.

```bash
BASE=http://localhost:3200
curl -c jar -X POST $BASE/user/login \
  --data-urlencode user_name=fabiantax --data-urlencode password=Strix2024! \
  --data-urlencode remember=on            # 303 = ok
```

**Create board:** `POST /{owner}/{repo}/projects/new` with `title`, `content=`,
`template_type=1` (basic kanban → Backlog/To Do/In Progress/Done; `""`=blank), `card_type=2`.
On success it redirects to `/projects` with **no id in Location** — re-fetch
`GET /{owner}/{repo}/projects` and grep `projects/\K[0-9]+`. Check the list first for
idempotency.

**Attach issue:** `POST /{owner}/{repo}/issues/projects` with `id=<projectId>` and
`issue_ids=<INTERNAL DB id>`. CRITICAL: `issue_ids` is the issue's internal `.id` (from
`/api/v1/repos/{full}/issues/{num}` → `.id`), **NOT the display number**. The display number
yields `404 "Not found."`. Issues land in Uncategorized until dragged.

## PR review approval (two-call dance)

Creating a review with `event:"APPROVE"` lands as `state:"PENDING"` — it does not submit.
Submit with a **second** call using the **past-tense** event on the per-review endpoint:

```bash
# 1. create → returns a review id, state=PENDING
curl -X POST -H "Authorization: token $T" -H "Content-Type: application/json" \
  -d '{"event":"APPROVE","body":"LGTM"}' \
  "$GITEA/api/v1/repos/$OWNER/$REPO/pulls/$N/reviews"
# 2. submit → flips to state=APPROVED, official=true
curl -X POST -H "Authorization: token $T" -H "Content-Type: application/json" \
  -d '{"event":"APPROVED"}' \
  "$GITEA/api/v1/repos/$OWNER/$REPO/pulls/$N/reviews/$REVIEW_ID"
```
The submit endpoint is `/reviews/{id}` (no `/submit` suffix — `/submit` → 422). Tense matters:
`APPROVE` (imperative) is silently rejected; `APPROVED` (state name) is accepted.

## Webhooks to host services

To deliver webhooks to a receiver on the host (rootless podman), set in `[webhook]`:
```ini
[webhook]
ALLOWED_HOST_LIST = *
ALLOW_LOCAL_NETWORKS = true
```
`ALLOW_LOCAL_NETWORKS = true` is load-bearing — without it, delivery to loopback/private
targets is refused even with `ALLOWED_HOST_LIST = *`. The webhook URL must be
`http://host.containers.internal:<port>/…` (resolves to the link-local host gateway
169.254.1.2 from the container netns; the host LAN IP is connection-refused). The receiver
must bind `0.0.0.0`.
