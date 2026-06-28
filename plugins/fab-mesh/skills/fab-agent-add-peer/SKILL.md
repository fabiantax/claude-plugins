---
name: fab-agent-add-peer
description: Add a fab-agent peer to the mesh
---

# Add a fab-agent peer to the mesh

Stand up the TypeScript `fab-agent-runtime` peer (CEO/CTO/devops/specialist)
for a repo so it joins the A2A mesh and can consult-and-be-consulted by
existing peers (atlas, GraphFusion, localscout, fab-agent-state).

For the **Rust** `fab-agent-mesh` crate dependency (protocol/transport/registry
library) see `fab-agent-add-mesh.md` — different layer.

## TL;DR

Once per machine:

```sh
curl -sSL http://strix:3200/fabiantax/fab-agent-runtime/raw/main/install.sh | sh
```

Mint the Gitea token first (private repo) at http://strix:3200/user/settings/applications
— needs `read:package` + `read:repository` scopes — then `export GITEA_TOKEN=<token>`
or add `machine strix login <user> password <token>` to `~/.netrc` (chmod 600).

Needs `bun` or `node` on PATH. Drops `fab-agent-runtime` + `fab-agent-runtime.mjs`
into `~/.local/bin/` (~350 KB tarball, no symlinks).

Per repo: copy the persona / yaml / systemd templates from `docs/BOOTSTRAP.md`
in `fabiantax/fab-agent-runtime`, pick a free /10 port block (taken: 50210
GraphFusion, 50220 atlas, 50240 localscout, 50260 raaf, 50300 fab-agent-state;
50230 / 50250 / 50270 / 50280 are reserved-free), set in each `.service`:

- `MESH_STATE_URL=http://127.0.0.1:50300`
- `AM_PUBLIC_HOST=strix`
- `After=network-online.target fab-agent-state.service`
- `Wants=fab-agent-state.service`
- `EnvironmentFile=%h/.config/fab-agent-runtime/secrets.env` (for `ZAI_API_KEY`)

Then:

```sh
systemctl --user daemon-reload
systemctl --user enable --now <repo>-{ceo,cto}.service
```

## Verify

```sh
journalctl --user -u <repo>-ceo.service -n 20 | grep mesh:
# expect: "mesh: registered via A2A (fab-agent-state) (attempt 1)"
fab-agent-runtime registry list | grep <repo>
```

## Naming convention

`<repo>-<role>` always — `atlas-ceo`, `graphfusion-cto`, etc. Never bare role
names. Personas live at `~/Developer/personal/<repo>/.claude/agents/<repo>-<role>.md`,
yamls next to them.

## Required envs are CI-enforced

`scripts/lint-bootstrap-env.mjs` (run in CI) parses the systemd template in
`docs/BOOTSTRAP.md` and asserts `MESH_STATE_URL`, `AM_PUBLIC_HOST` (non-state
peers) and `LIBSQL_URL` (state peer) appear. If you drift the template, CI
fails before the regression reaches a peer.

## Reference

- Source repo: http://strix:3200/fabiantax/fab-agent-runtime
- Canonical recipe: `docs/BOOTSTRAP.md` at the repo root.
- Current version on registry: see `releases/latest`.
