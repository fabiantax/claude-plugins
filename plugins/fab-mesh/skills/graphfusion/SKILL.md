---
name: graphfusion
description: This skill should be used when the user asks to "load a graph into graphfusion", "ingest into GF", "start the GF server / studio", "query the graph", "run a cypher query against graphfusion", "import a parquet/lance/.gfx", "export-gfx", "add an edge", "what port is graphfusion on", "ask the GF a2a agent", "why is the graph empty / no graph data", "cosmos.gl / studio not showing data", "graphfusion CLI", or otherwise works with the local GraphFusion server container, its CLI, the `.gfx` format, or the GF A2A agent. Covers running-container topology, ports, the in-container CLI (init/import/add-edge/export-gfx/gfx/query/flight/a2a), how to load a real graph (nodes vs edges), and the GF↔Atlas viz ownership split.
---

# GraphFusion — local server, CLI, `.gfx`, and A2A agent

GraphFusion (GF) is the native graph query engine (CSR storage, Lance, Arrow Flight, Cypher). On this host it runs as a **podman container** and is the data layer behind Atlas (and behind the cosmos.gl Studio viz). This skill is the operational handbook for that container — the facts below were verified live on 2026-06-17 against the running container + CLI `--help`, not assumed.

## When to Use
- Loading / ingesting a graph into the running GF server ("the graph is empty")
- Running Cypher or graph-algo queries against GF (CLI or A2A)
- Starting or debugging GF Studio (the cosmos.gl web app) or its backend connection
- Importing/exporting `.gfx`, Parquet, Lance, Arrow
- Consulting the GF A2A agent
- Port/container questions ("what port is GF on?")
- **Ownership ambiguity**: "is viz an Atlas thing or a GF thing?" → see [GF↔Atlas viz ownership](#gf-vs-atlas-who-owns-what) below; default instinct is usually wrong

## The running container

```
podman run --rm --name graphfusion-server \
  -p 8092:8080 -p 50051:50051 -p 50053:50052 \
  -v /home/fabian/.local/share/graphfusion-server:/data \
  localhost:3200/fabiantax/graphfusion-server:latest  all
```
- Image built locally from Gitea (`localhost:3200/fabiantax/graphfusion-server:latest`), entrypoint `/entrypoint.sh`, cmd `all` = HTTP `serve` + `flight` + `a2a`.
- **`--rm` ⇒ ephemeral**: any graph held only in memory is lost on restart. A graph persists only if it lives under the bind-mounted `/data` (host: `/home/fabian/.local/share/graphfusion-server/`).
- Data mount: host `/home/fabian/.local/share/graphfusion-server` → container `/data`. A fresh/empty mount → logs say `no graph data at /data; starting with an empty graph`.

### Ports (host → container)

| Host | In-container | Service | Notes |
|---|---|---|---|
| `:8092` | `:8080` | HTTP (`serve`) | REST routes exist but are partial; do not rely on `/health` |
| `:50051` | `:50051` | **Arrow Flight SQL** (gRPC) | the real query interface; `Connect with: grpc://0.0.0.0:50051` |
| `:50053` | `:50052` | **A2A agent** (HTTP JSON-RPC) | agent card at `/.well-known/agent.json`; note the **swapped** mapping `50053→50052` |

A second container, **`graphfusion-routed`** (`localhost:3200/fabiantax/routed:latest`, host `:8091→8090`), is a separate routing/CCH engine — unrelated to graph data needs.

### ⚠️ Pasta proxy flakiness on host ports
Direct host-side `curl http://localhost:50053/...` and `:8092/...` **intermittently return HTTP 000 / `fetch failed`** — the pasta network proxy warms up slowly and flaps. `ss` shows the port listening, but GETs can still fail. **Workaround that always works: run the call from inside the container via `podman exec`, hitting the in-container loopback (`127.0.0.1:50052` / `:8080`).** This is the single most important operational gotcha. Do not conclude a GF service is "down" from a host-side `curl -sf` returning 000 — verify via `podman exec` first.

## The in-container CLI (source of truth)

Always invoke via `podman exec graphfusion-server sh -c 'graphfusion <...>'`. The CLI is more authoritative than the A2A agent card (see [A2A caveat](#a2a-agent)).

```
graphfusion init                           # create DB at -d <path> (default .graphfusion)
graphfusion import <FILE> -d <db>          # FILE = JSON | CSV | Parquet | Arrow (auto-detected)
graphfusion add-node / add-edge            # single node / edge
graphfusion query "<cypher>" -d <db>       # Cypher
graphfusion stats -d <db>                  # node/edge counts, types
graphfusion export-gfx -i <input> -o <out> # input = .gfx | Lance dir | Parquet dir
graphfusion gfx {inspect,validate,diff,open} <file>
graphfusion open <file.gfx>                # shorthand for `gfx open`
graphfusion migrate <file>                 # .gfx format/schema upgrades
graphfusion serve | flight | a2a           # start a server
graphfusion a2a-client ...                 # talk to other A2A agents
```

`-d, --database <PATH>` selects the graph DB (default `.graphfusion`).

## How to load a graph (the question this skill exists for)

### Nodes vs edges — the load-bearing distinction
- **`import` is NODES-ONLY.** `graphfusion import --help` has no edge/relationship option: it turns each row into a node with `--node-type <T>` (default `Data`) and optional `--id-column`. Importing a nodes-only parquet yields N isolated nodes — the exact "mostly isolated graph" failure that defeats every consumer (dead-code, clone, impact). **Do not import nodes alone and expect a working call graph.**
- **Edges**: either
  - `add-edge --source <ID> --target <ID> --edge-type CALLS` (one at a time), or
  - **the `.gfx` round-trip**, which carries BOTH nodes and edges. `export-gfx --input` accepts a **Lance directory or Parquet directory** (not just `.gfx`), so the canonical full-graph load is: export your Lance/parquet graph to `.gfx`, then `gfx open`/import it.

### Loading the Atlas graph into this server (concrete)
The atlas graph (from `atlas scan`, post-#217 ≈226K nodes + CALLS edges) lives at `atlas/.atlas/nodes.lance` (+ `edges` sibling) — **not** under the GF mount by default.
1. Make the atlas graph reachable from the container: `podman cp` it in, or point the bind mount at it, or place a copy under `/home/fabian/.local/share/graphfusion-server/`.
2. Because edges matter, prefer the `.gfx` path over a bare `import`:
   `graphfusion export-gfx -i <atlas-lance-dir> -o /data/atlas.gfx` then `graphfusion gfx open /data/atlas.gfx` (or re-init the DB from it).
3. Restart the container (`--rm`) so it reloads `/data`, then `graphfusion stats -d /data/...` to confirm non-zero nodes AND edges.
4. Verify the call graph survived: a Cypher reachability / shortest-path query (`references/` or the A2A `graphfusion-shortest-path` skill) should return real paths, not "0 edges".

### ⚠️ Don't trust a "successful" load without an edge check
GF #673 (csr.bin written with `num_edges=0`) means even a populated graph can read back as zero-edges on the CSR fast path — every cold read rebuilds ~172MB. If `stats` shows edges but queries behave edgeless, that's the upstream defect (filed, `from:atlas unblocks:atlas`), not your ingest. See memory `graphfusion_csr_bin_zero_edges`.

## A2A agent

Agent card (stable via in-container curl):
```
podman exec graphfusion-server sh -c 'curl -s http://127.0.0.1:50052/.well-known/agent.json'
```
`name=graphfusion-agent`, `version=0.1.0`, `url=http://0.0.0.0:50052`. Skills:
- `graphfusion-cypher-query`, `graphfusion-graph-search` (BM25+dense RRF), `graphfusion-community-detection` (Louvain/Leiden), `graphfusion-shortest-path` (Dijkstra/BFS), `graphfusion-pagerank`, `graphfusion-node-embedding`, `graphfusion-min-cut` (DynamicMinCut on CSR), `graphfusion-graph-import`, `graphfusion-graph-export`.
- `capabilities: streaming=false, push_notifications=false` → it does **not** implement A2A v2 `message/send` streaming; `fab-agent-runtime call ...` against it fetch-fails through the flaky host port. Prefer `podman exec` + direct curl for any A2A call.

**A2A caveat (treat as prioritization, not truth):** the agent card's `graphfusion-graph-import` claims "from .gfx format", but the CLI `import` actually takes JSON/CSV/Parquet/Arrow. The CLI wins. Always cross-verify an A2A answer against `graphfusion --help` / the code. (See memory `feedback_a2a_peer_consults_unreliable`.)

## GF vs Atlas — who owns what (don't get this wrong)

| Capability | Owner | Where |
|---|---|---|
| **Interactive cosmos.gl graph viz (web)** | **GraphFusion** | `GF/apps/studio/` (Fresh/Preact/Deno; `islands/GraphViewer.tsx` loads `@cosmos.gl/graph@2.6.4` from CDN) |
| **CLI diagram text emission (`atlas viz -t c4/graph/heatmap`)** | Atlas | `atlas-cli/src/{d2,graph}_visualizer.rs` — lesser, separate; `-t graph`→DOT renders (graphviz installed), `-t c4/heatmap`→D2 text needs `d2` |
| Graph **layout math** (force-directed/hierarchical) | Atlas | `crates/atlas-viz/` |
| Graph **data / storage / query** | GraphFusion | the container + Lance/CSR |

The runnable cosmos.gl Studio is on GF branch `fix/geodata-syntax-338` (worktree `.claude/worktrees/agent-*/apps/studio/`); it uses an **HTTP** client (`fetch /query/arrow`) while the running GF server is **Flight** — bridging them is the point of GF branch `feat/viz-flight-sdk`. Studio's default `GRAPHFUSION_URL=http://localhost:8080` is **wrong for this box** (8080 is the `fab-agent-sqld` container); point it at the GF server's host port. See memory `graph_viz_ownership`.

## Related
- `/cosmos-gl` skill — the renderer itself (API, data formats, GF CSR mapping)
- `/gitea` skill — the GF image is built from `localhost:3200/fabiantax/graphfusion-server`
- memories: `graph_viz_ownership`, `graphfusion_csr_bin_zero_edges`, `feedback_a2a_peer_consults_unreliable`, `fast-path-graphfusion-gap`
- `references/cli-cookbook.md` — copy-paste command recipes (init/import/edges/export/query/stats + the podman-exec pasta bypass)
