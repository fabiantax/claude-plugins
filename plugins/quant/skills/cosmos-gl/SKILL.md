---
name: cosmos-gl
description: Cosmos.gl v2.6.4 WebGL force graph — verified API from CDN bundle, data formats, GraphFusion CSR mapping, event handling, and gf viz integration.
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - WebSearch
  - WebFetch
  - Agent
---

# Cosmos.gl — WebGL Force Graph Visualization (v2.6.4 Verified)

## Overview

cosmos.gl (`@cosmos.gl/graph`) is a GPU-accelerated force graph renderer built on WebGL 2 via regl. It handles hundreds of thousands of nodes at 60fps. It is a **rendering engine only** — no community detection, no property system, no label rendering, no CSV/Arrow parsing. Data must be provided as typed arrays.

**Documented version**: v2.6.4 (stable, regl-based). All APIs below were verified by inspecting the actual CDN bundle at `https://cdn.jsdelivr.net/npm/@cosmos.gl/graph@2.6.4/dist/index.js`.

**License**: MIT.

---

## IMPORTANT: v2.6.4 API Gotchas

These are the most common integration mistakes:

1. **NO `setPointLabels()`** — cosmos.gl v2.6.4 has no label API. Implement hover tooltips manually using `onPointMouseOver`/`onPointMouseOut`.
2. **NO `showLabels`, `labelFontSize`, `labelColor`** — these config options do not exist.
3. **`onPointClick`** for node clicks, NOT `onClick`. `onClick` fires on background clicks only.
4. **`setConfig()`** for live updates, NOT `setConfigPartial` (doesn't exist).
5. **Colors in v2**: `Float32Array`, 4 floats per point (R, G, B, A), values 0–255 per channel.
6. **`onMouseMove`** receives `(hoveredPointIndex, hoveredPointPosition)`, NOT a DOM MouseEvent. Track mouse position globally for tooltip positioning.

---

## Event Callbacks (Verified from Bundle)

| Event | Signature | Fires When |
|-------|-----------|-----------|
| `onPointClick` | `(pointIndex: number) => void` | User clicks on a node |
| `onLinkClick` | `(linkIndex: number) => void` | User clicks on a link |
| `onClick` | `(event: MouseEvent) => void` | User clicks on background (no node) |
| `onBackgroundClick` | `() => void` | User clicks on background |
| `onPointMouseOver` | `(pointIndex: number, position: [number, number]) => void` | Mouse enters a node |
| `onPointMouseOut` | `(event: MouseEvent) => void` | Mouse leaves a node |
| `onLinkMouseOver` | `(linkIndex: number, position: [number, number]) => void` | Mouse enters a link |
| `onLinkMouseOut` | `(event: MouseEvent) => void` | Mouse leaves a link |
| `onMouseMove` | `(hoveredPointIndex: number \| null, hoveredPointPosition: [number, number] \| null) => void` | Any mouse movement over canvas |
| `onZoomStart` | `() => void` | Zoom starts |
| `onZoom` | `() => void` | Zoom in progress |
| `onZoomEnd` | `() => void` | Zoom ends |
| `onDragStart` | `() => void` | Drag starts |
| `onDrag` | `() => void` | Drag in progress |
| `onDragEnd` | `() => void` | Drag ends |
| `onSimulationStart` | `() => void` | Simulation starts |
| `onSimulationTick` | `() => void` | Each simulation tick |
| `onSimulationEnd` | `() => void` | Simulation stops |
| `onSimulationPause` | `() => void` | Simulation paused |
| `onSimulationRestart` | `() => void` | Simulation restarted |
| `onSimulationUnpause` | `() => void` | Simulation unpaused |

---

## Data Format

cosmos.gl accepts **only** `Float32Array`, `Uint8Array`, and `boolean[]`. No Arrow, no CSV, no JSON objects, no property bags.

### Point Positions

```typescript
// Float32Array [x1, y1, x2, y2, ...] — 2 floats per point
graph.setPointPositions(new Float32Array([
  100.0, 200.0,  // point 0
  300.0, 400.0,  // point 1
  500.0, 600.0,  // point 2
]))
```

Coordinates live in a `spaceSize × spaceSize` box (default 4096). Points can be initialized randomly or with force-directed seeds.

### Links

```typescript
// Float32Array [srcIdx, tgtIdx, srcIdx, tgtIdx, ...] — 2 floats per link
graph.setLinks(new Float32Array([
  0, 1,  // link from point 0 → point 1
  1, 2,  // link from point 1 → point 2
  2, 0,  // link from point 2 → point 0
]))
```

Indices are 0-based integer node positions. Direct CSR mapping — no string IDs, no edge objects.

### Point Colors (v2.6.4)

```typescript
// Float32Array RGBA — 4 floats per point, values 0–255 per channel
graph.setPointColors(new Float32Array([
  255, 0, 0, 255,    // point 0: red
  0, 255, 0, 255,    // point 1: green
  0, 0, 255, 255,    // point 2: blue
]))
```

**IMPORTANT**: v2.6.4 uses 0–255 per channel, NOT 0.0–1.0. The alpha channel also uses 0–255 (use 255 for fully opaque). Do NOT pass packed `Uint32Array` — cosmos.gl expects a `Float32Array` with 4 separate floats per point.

### Point Sizes

```typescript
// Float32Array [size1, size2, ...] — 1 float per point
graph.setPointSizes(new Float32Array([10.0, 20.0, 15.0]))
```

Max point size: 64 (hardware limit on point sprite texture).

### Link Colors

```typescript
// Float32Array RGBA — 4 floats per link (same order as links array), 0–255 per channel
graph.setLinkColors(new Float32Array([128, 128, 128, 76, ...]))
```

### Link Widths

```typescript
// Float32Array [width1, width2, ...] — 1 float per link
graph.setLinkWidths(new Float32Array([1.0, 2.0, 0.5]))
```

### Point Shapes

```typescript
// Uint8Array [shape1, shape2, ...] — 1 byte per point
graph.setPointShapes(new Uint8Array([0, 1, 2, 3]))
```

### Point Images

```typescript
// string[] — image URLs per point
graph.setPointImages(['url1.png', 'url2.png'])
graph.setPointImageSizes(new Float32Array([16.0, 24.0]))
graph.setPointImageIndices(new Float32Array([0, 1]))
```

### Point Clusters

```typescript
// Float32Array — per-point cluster assignment for gravity forces
graph.setPointClusters(new Float32Array([0, 0, 1, 1, 2]))
graph.setPointClusterStrength(new Float32Array([1.0, 1.0, 0.5]))
```

### Pinned Points

```typescript
// boolean[] — true = point stays fixed during simulation
graph.setPinnedPoints(new boolean[](...[true, false, true]))
```

---

## Configuration Options (Verified from Bundle)

### Initialization Config

```typescript
const graph = new Graph(container, {
  // --- Space ---
  spaceSize: 4096,

  // --- Simulation ---
  simulationFriction: 0.85,
  simulationGravity: 0.1,
  simulationRepulsion: 0.5,
  simulationRepulsionTheta: 0.5,
  simulationRepulsionQuadtreeLevels: 12,
  simulationLinkSpring: 0.5,
  simulationLinkDistance: 10,
  simulationLinkDistRandomVariationRange: 0,
  simulationRepulsionFromMouse: 0,
  simulationDecay: 1000,
  simulationCenter: [0, 0],
  simulationCluster: 0,
  enableSimulation: true,
  enableSimulationDuringZoom: false,

  // --- Rendering ---
  curvedLinks: false,
  curvedLinkSegments: 16,
  curvedLinkWeight: 0.5,
  curvedLinkControlPointDistance: 0.5,
  backgroundColor: [0, 0, 0, 255],    // RGBA 0–255
  linkOpacity: 0.3,
  linkGreyoutOpacity: 0.1,
  linkWidth: 1,
  linkWidthScale: 1,
  linkArrows: false,
  linkArrowsSizeScale: 1,
  linkVisibilityDistanceRange: [0, Infinity],
  linkVisibilityMinTransparency: 0,
  renderLinks: true,
  scaleLinksOnZoom: true,
  pointOpacity: 1.0,
  pointGreyoutOpacity: 0.1,
  pointSize: 5,
  pointSizeScale: 1,
  pointColor: [0.5, 0.5, 0.5, 1],
  pointDefaultColor: undefined,
  pointDefaultSize: undefined,
  scalePointsOnZoom: true,
  pixelRatio: window.devicePixelRatio,
  antialias: true,
  showFPSMonitor: false,

  // --- Interaction ---
  enableDrag: true,
  enableZoom: true,
  enableRightClickRepulsion: true,
  fitViewOnInit: false,
  fitViewDelay: 0,
  fitViewPadding: 0.2,
  fitViewDuration: 200,
  fitViewByPointsInRect: undefined,
  fitViewByPointIndices: undefined,
  initialZoomLevel: undefined,
  hoveredPointCursor: "pointer",
  hoveredLinkCursor: "pointer",
  randomSeed: undefined,

  // --- Events (see Event Callbacks table above) ---
  onPointClick: (idx) => {},
  onBackgroundClick: () => {},
  onPointMouseOver: (idx, pos) => {},
  onPointMouseOut: (event) => {},
  // ... etc
})
```

### Live Config Updates

Use `setConfig()` to update config after construction. It merges with current config:

```typescript
graph.setConfig({
  pointGreyoutOpacity: 0.1,
  linkGreyoutOpacity: 0.05,
})
```

**NOT** `setConfigPartial` — that method does not exist.

---

## Methods Reference (Verified from Bundle)

### Data Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `setPointPositions` | `(positions: Float32Array) => void` | Set x,y coordinates |
| `setLinks` | `(links: Float32Array) => void` | Set edge list as [src,tgt,...] |
| `setPointSizes` | `(sizes: Float32Array) => void` | Set per-point sizes |
| `setPointColors` | `(colors: Float32Array) => void` | Set per-point RGBA (0–255) |
| `setPointShapes` | `(shapes: Uint8Array) => void` | Set per-point shape enum |
| `setPointImages` | `(images: string[]) => void` | Set per-point image URLs |
| `setPointImageIndices` | `(indices: Float32Array) => void` | Image index per point |
| `setPointImageSizes` | `(sizes: Float32Array) => void` | Image sizes per point |
| `setPointClusters` | `(clusters: Float32Array) => void` | Cluster assignment per point |
| `setPointClusterStrength` | `(strength: Float32Array) => void` | Cluster gravity strength |
| `setPointWeight` | `(weight: Float32Array) => void` | Per-point simulation weight |
| `setLinkColors` | `(colors: Float32Array) => void` | Per-link RGBA (0–255) |
| `setLinkWidths` | `(widths: Float32Array) => void` | Per-link widths |
| `setLinkArrows` | `(arrows: boolean[]) => void` | Per-link arrow visibility |
| `setPinnedPoints` | `(pinned: boolean[]) => void` | Pin points in place |
| `setConfig` | `(config: Partial<Config>) => void` | Merge config updates |
| `setFocusedPoint` | `(index: number) => void` | Focus a specific point |
| `setFocusedPointRingColor` | `(color: number[]) => void` | Focused point ring color |
| `setHoveredPointRingColor` | `(color: number[]) => void` | Hovered point ring color |
| `setGreyoutPointColor` | `(color: number[]) => void` | Greyed-out point color |
| `setHoveredLinkColor` | `(color: number[]) => void` | Hovered link color |
| `setZoomTransformByPointPositions` | `(positions: Float32Array) => void` | Zoom to fit given positions |

**Methods that DO NOT exist in v2.6.4** (common mistakes):
- ~~`setPointLabels`~~ — no label API
- ~~`setSelectedPoints`~~ — no selection state API
- ~~`setConfigPartial`~~ — use `setConfig`
- ~~`selectPoint`, `deselectPoint`, `deselectAll`~~ — no selection methods
- ~~`getPointByCoordinates`, `getPointNeighbors`~~ — no query methods
- ~~`getZoom`, `getCenter`, `setZoom`, `setCenter`~~ — no direct zoom/center getters/setters

### View Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `render` | `() => void` | Trigger re-render (call after any `set*()`) |
| `resize` | `() => void` | Handle container resize |
| `fitView` | `() => void` | Zoom to fit all points |
| `fitViewByPointIndices` | `(indices: number[]) => void` | Zoom to fit specific points |

### Simulation Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `start` | `() => void` | Start force simulation |
| `stop` | `() => void` | Stop simulation |
| `restart` | `() => void` | Restart simulation |
| `step` | `() => void` | Single simulation tick |

### Lifecycle Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `destroy` | `() => void` | Clean up WebGL resources |

---

## Hover/Tooltip Pattern

Since cosmos.gl has no label API, implement tooltips manually:

```typescript
// Track mouse position globally (cosmos.gl callbacks don't pass DOM events)
let mouseX = 0, mouseY = 0;
document.addEventListener('mousemove', (e) => { mouseX = e.clientX; mouseY = e.clientY; });

const tooltip = document.getElementById('tooltip');

const graph = new Graph(container, {
  onPointMouseOver: (idx) => {
    if (idx == null || idx < 0) return;
    const label = labels[idx];
    tooltip.innerHTML = `<b>${label}</b> · deg ${degrees[idx]}`;
    tooltip.style.display = 'block';
    tooltip.style.left = (mouseX + 14) + 'px';
    tooltip.style.top = (mouseY - 28) + 'px';
  },
  onPointMouseOut: () => { tooltip.style.display = 'none'; },
});
```

---

## GraphFusion CSR → Cosmos.gl Mapping

The `BidirectionalCsr` stores adjacency as `offsets: Vec<usize>` and `targets: Vec<NodeId>`. This maps directly to cosmos.gl's link format with zero logical transformation.

### Links from CSR

```rust
fn csr_to_links(csr: &BidirectionalCsr) -> Vec<f32> {
    let offsets = csr.forward_offsets();
    let targets = csr.forward_targets();
    let mut links = Vec::with_capacity(csr.edge_count() * 2);
    for node in 0..csr.node_count() {
        let start = offsets[node];
        let end = offsets[node + 1];
        for i in start..end {
            links.push(node as f32);
            links.push(targets[i].0 as f32);
        }
    }
    links
}
```

### Degree-Based Sizes

```rust
fn degree_sizes(csr: &BidirectionalCsr) -> Vec<f32> {
    (0..csr.node_count())
        .map(|n| {
            let deg = csr.out_degree(NodeId(n));
            2.0 + (deg.max(1) as f32).ln()
        })
        .collect()
}
```

### Color Palette (Packed uint32 → Float32Array)

The server sends colors as packed uint32 RGBA. The frontend unpacks:

```javascript
function unpackColors(packed) {
  const n = packed.length;
  const out = new Float32Array(n * 4);
  for (let i = 0; i < n; i++) {
    const c = packed[i] >>> 0;
    out[i * 4]     = (c >>> 24) & 0xff;   // R
    out[i * 4 + 1] = (c >>> 16) & 0xff;   // G
    out[i * 4 + 2] = (c >>>  8) & 0xff;   // B
    out[i * 4 + 3] =  c         & 0xff;    // A
  }
  return out;
}
```

---

## Community Aggregation Strategy

cosmos.gl has NO built-in community detection. Its `setPointClusters()` applies per-point gravity toward a cluster center — purely a visual force, not a detection algorithm.

### Scaling Tiers

```
node_count <= 10,000:
  → Direct render. cosmos.gl handles 10K at 60fps trivially.
  → Use Louvain/Leiden colors only (no aggregation).

10,000 < node_count <= 100,000:
  → Run Louvain → render communities as meta-nodes.
  → Meta-node size = member count. Meta-edge weight = inter-community edge count.
  → Click meta-node → fetch /api/community/:id/nodes → expand inline.

node_count > 100,000:
  → Run Louvain → render top-N communities by size.
  → Only expand on explicit drill-down.
  → Limit visible links to top 50K by weight.
```

---

## Performance Characteristics

| Scale | Strategy | Target FPS | Notes |
|-------|----------|-----------|-------|
| <10K nodes | Direct render | 60fps | All nodes visible |
| 10K–100K | Community meta-nodes | 60fps | ~1K–10K meta-nodes |
| 100K–500K | Community + link filter | 60fps | cosmos.gl handles 500K points on WebGL 2 |
| 500K+ | Aggressive sampling | 30fps | Texture-bound limit |

### Optimization Tips

1. **Filter links** — send only top-K edges by weight. cosmos.gl renders ALL links it receives
2. **Limit `simulationDecay`** — lower values stop simulation sooner (less CPU)
3. **Reduce `spaceSize`** — smaller space = tighter layout = fewer ticks to convergence
4. **Use `pointWeight`** — high-degree nodes get more gravity, producing better layouts
5. **Pre-compute positions** — skip force simulation entirely with pre-seeded positions
6. **Call `render()` after every `set*()` call** — changes are not applied until render

---

## Integration Example (v2.6.4 Verified)

```html
<script type="module">
  import { Graph } from 'https://esm.sh/@cosmos.gl/graph@2.6.4';

  let mouseX = 0, mouseY = 0;
  document.addEventListener('mousemove', e => { mouseX = e.clientX; mouseY = e.clientY; });

  const resp = await fetch('/api/graph');
  const data = await resp.json();
  const tooltip = document.getElementById('tooltip');

  const graph = new Graph(document.getElementById('container'), {
    spaceSize: 4096,
    simulationFriction: 0.85,
    simulationGravity: 0.1,
    simulationRepulsion: 0.5,
    curvedLinks: true,
    fitViewOnInit: true,
    fitViewPadding: 0.3,
    enableDrag: true,
    enableZoom: true,
    linkOpacity: 0.25,
    pointOpacity: 0.9,
    pointSize: 4,
    showFPSMonitor: true,
    onPointClick: (idx) => showNodePanel(idx),
    onBackgroundClick: () => { panel.style.display = 'none'; },
    onPointMouseOver: (idx) => {
      if (idx == null || idx < 0) return;
      tooltip.textContent = data.labels[idx] + ' · deg ' + data.degree[idx];
      tooltip.style.display = 'block';
      tooltip.style.left = (mouseX + 14) + 'px';
      tooltip.style.top = (mouseY - 28) + 'px';
    },
    onPointMouseOut: () => { tooltip.style.display = 'none'; },
  });

  graph.setPointPositions(new Float32Array(data.positions));
  graph.setLinks(new Float32Array(data.links));
  graph.setPointSizes(new Float32Array(data.sizes));
  graph.setPointColors(new Float32Array(data.colors));  // 4 floats/node, 0-255
  graph.render();
</script>
```

---

## CDN URLs

```html
<!-- v2.6.4 (stable, recommended) — esm.sh works well for ES module imports -->
<script type="module">
  import { Graph } from 'https://esm.sh/@cosmos.gl/graph@2.6.4';
</script>

<!-- v2.6.4 via jsdelivr (alternative) -->
<script type="module">
  import { Graph } from 'https://cdn.jsdelivr.net/npm/@cosmos.gl/graph@2.6.4/dist/index.js';
</script>
```

---

## Key Constraints

1. **No label API** — `setPointLabels`, `showLabels`, `labelFontSize`, `labelColor` do NOT exist. Implement tooltips via `onPointMouseOver`/`onPointMouseOut`.
2. **No Arrow/CSV/Parquet** — all data must be `Float32Array`/`Uint8Array`/`boolean[]`
3. **No property system** — use separate API endpoints for node details
4. **No community detection** — Louvain/Leiden must run externally
5. **No WebGPU** — WebGL 2 only
6. **Max point size 64** — hardware limit on GL point sprites
7. **v2 colors 0–255** — NOT 0.0–1.0 (that's v3 beta only)
8. **`onPointClick`** for node clicks — `onClick` is background click only
9. **`setConfig()`** for live updates — NOT `setConfigPartial`
10. **`render()` required after data changes** — changes don't apply automatically
