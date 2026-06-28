# GraphFusion CLI cookbook

All commands run against the running `graphfusion-server` container. Two invocation styles:

```bash
# Inside the container (STABLE — bypasses flaky host pasta ports):
podman exec graphfusion-server sh -c 'graphfusion <subcmd>'

# From the host, for inspection only (may flap — see SKILL.md "Pasta proxy flakiness"):
podman exec graphfusion-server graphfusion <subcmd>
```

For data files, the DB path is `/data` inside the container (bind-mounted to
`/home/fabian/.local/share/graphfusion-server` on the host).

## Container lifecycle
```bash
podman ps --format '{{.Names}} {{.Ports}}' | grep graphfusion          # what's running + ports
podman logs --tail 30 graphfusion-server                              # "no graph data"? empty /data
podman restart graphfusion-server                                     # reloads /data (container is --rm-safe for /data)
podman exec graphfusion-server sh -c 'curl -s http://127.0.0.1:50052/.well-known/agent.json'   # A2A card (stable)
```

## Create a DB + import nodes
```bash
# init the database directory
podman exec graphfusion-server sh -c 'graphfusion init -d /data/graphs/mygraph'

# import NODES from JSON/CSV/Parquet/Arrow (auto-detected). NODES-ONLY — no edges.
podman exec graphfusion-server sh -c \
  'graphfusion import /data/nodes.parquet -d /data/graphs/mygraph -t Function --id-column id -p'
```
`-t/--node-type` defaults to `Data`. `--id-column` sets the node id column.

## Add edges (because import doesn't)
```bash
# one edge at a time
podman exec graphfusion-server sh -c \
  'graphfusion add-edge --source <src-id> --target <dst-id> --edge-type CALLS -d /data/graphs/mygraph'
# edge types seen in atlas: CALLS, IMPORTS, CONTAINS
```
For bulk edges, use the `.gfx` round-trip below instead of N add-edge calls.

## Full graph (nodes + edges) via .gfx
```bash
# export a Lance dir or Parquet dir (carries both nodes and edges) to .gfx
podman exec graphfusion-server sh -c \
  'graphfusion export-gfx -i /data/atlas-lance -o /data/atlas.gfx'

# inspect/validate before opening
podman exec graphfusion-server sh -c 'graphfusion gfx inspect /data/atlas.gfx'
podman exec graphfusion-server sh -c 'graphfusion gfx validate /data/atlas.gfx'

# open it as a DB
podman exec graphfusion-server sh -c 'graphfusion open /data/atlas.gfx'   # = gfx open

# upgrade an older .gfx across format/schema changes
podman exec graphfusion-server sh -c 'graphfusion migrate /data/old.gfx'
```

## Query + sanity-check
```bash
# counts + types — ALWAYS verify edges > 0 after a load
podman exec graphfusion-server sh -c 'graphfusion stats -d /data/graphs/mygraph'

# Cypher
podman exec graphfusion-server sh -c \
  'graphfusion query "MATCH (n:Function) RETURN count(n)" -d /data/graphs/mygraph'
podman exec graphfusion-server sh -c \
  'graphfusion query "MATCH (a)-[r:CALLS]->(b) RETURN a.id, b.id LIMIT 5" -d /data/graphs/mygraph'
```
**Edge-survival check (load-bearing):** if `stats` shows edges but Cypher `(a)-[r]->(b)` returns none,
suspect upstream GF #673 (csr.bin `num_edges=0`, cold-read CSR rebuild) — not your ingest.
See memory `graphfusion_csr_bin_zero_edges`.

## Copy a graph from the host into the container
```bash
# host file → container /data
podman cp /home/fabian/Developer/personal/atlas/.atlas/nodes.lance graphfusion-server:/data/atlas-nodes/

# or: place it under the bind mount directly (no restart needed for the file, but the GF
# process must re-open the DB)
cp -r /path/to/graph /home/fabian/.local/share/graphfusion-server/graphs/
```

## Loading the Atlas graph (the common case on this box)
The atlas graph from `atlas scan` (~226K nodes + CALLS edges, post-#217) is at
`atlas/.atlas/nodes.lance` (+ `edges` sibling). It is NOT under the GF mount by default.

Recommended (edges survive):
```bash
podman cp /home/fabian/Developer/personal/atlas/.atlas/nodes.lance graphfusion-server:/data/atlas-lance
podman exec graphfusion-server sh -c 'graphfusion export-gfx -i /data/atlas-lance -o /data/atlas.gfx'
podman exec graphfusion-server sh -c 'graphfusion gfx validate /data/atlas.gfx'
podman restart graphfusion-server
podman exec graphfusion-server sh -c 'graphfusion stats -d /data/atlas.gfx'   # confirm nodes AND edges > 0
```
If `export-gfx` rejects the atlas Lance layout (it expects Lance/Parquet **dirs** with GF's schema),
fall back to: `init` + `import` the parquet for nodes, then bulk-add CALLS edges, then `export-gfx`
the result for a clean reusable snapshot.

## Ports quick reference
| Host | In-container | Service |
|---|---|---|
| `:8092` | `:8080` | HTTP `serve` (partial REST) |
| `:50051` | `:50051` | Arrow Flight SQL (gRPC) — primary query path |
| `:50053` | `:50052` | A2A agent (HTTP) — note the **swapped** mapping |

Host-side curl to these can return HTTP 000 (pasta flakiness); use `podman exec` + in-container `127.0.0.1:<port>` for stable calls.
