---
name: fab-agent-add-mesh
description: Add fab-agent-mesh Dependency
---

# Add fab-agent-mesh Dependency

Add the **Rust** `fab-agent-mesh` crate (protocol/transport/registry library)
from the private Gitea Cargo registry on strix.

For the **TypeScript** `fab-agent-runtime` peer-install (CEO/CTO/devops
joining the A2A mesh as a process) see `fab-agent-add-peer.md` — different
layer.

## Registry setup

If `~/.cargo/config.toml` doesn't already have `[registries.strix]`, append:
```toml
[registries.strix]
index = "sparse+http://strix:3200/api/packages/fabiantax/cargo/"
```
The registry is anonymous-readable on Tailnet — no token needed to pull.

## Dependency

This is an umbrella crate — a single dependency pulls in all sub-crates
(protocol, transport, registry, security). Add it as a workspace dependency
and to whichever crate(s) need it:

```toml
# workspace Cargo.toml [workspace.dependencies]
fab-agent-mesh = { version = "0.3.0", registry = "strix" }
```

```toml
# consuming crate's Cargo.toml [dependencies]
fab-agent-mesh = { workspace = true }
```

Do NOT add the individual sub-crates (-protocol, -transport, -registry,
-security) — they are re-exported through the umbrella.

## Verify

Run `cargo fetch` and show the `source = "sparse+http://strix..."` lines
from Cargo.lock to confirm resolution.

## Rust import

`use fab_agent_mesh;` — single module ident, everything is re-exported.

## Reference

Source repo: http://strix:3200/fabiantax/fab-agent-mesh
Consumer docs: CONSUMERS.md at the repo root.
Old `am-*` v0.2.x package names on the registry are orphans — don't use them.
