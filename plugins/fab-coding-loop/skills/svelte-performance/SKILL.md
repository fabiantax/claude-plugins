---
name: svelte-performance
description: Svelte 5 Performance Best Practices
---

# Svelte 5 Performance Best Practices

Performance patterns for Svelte 5 apps — runes, effects, rendering, third-party libraries.

---

## 1. Runes: `$state` vs `$derived` vs `$effect`

### Use `$derived` for computed values — never `$effect` + assignment

```typescript
// BAD: effect sets state on every change (two render passes)
$effect(() => { fullName = `${first} ${last}`; });

// GOOD: single-pass, no extra render
let fullName = $derived(`${first} ${last}`);
```

### Use `$derived.by` for expensive computations

```typescript
let sortedData = $derived.by(() => {
  return [...rawData].sort((a, b) => b.value - a.value);
});
```

### Keep `$state` minimal — derive the rest

Only mark data as `$state` if it's independently mutable. Everything else should be `$derived` from those atoms.

```typescript
// GOOD: one source of truth
let panels = $state<PanelConfig[]>([...defaults]);
let cols = $derived(PRESETS[activePreset].cols);
let rows = $derived(Math.ceil(panels.length / cols));
```

## 2. `$effect` rules

### Effects are for side effects, not state derivation

Effects run AFTER the DOM updates. Use them for:
- Syncing external systems (chart libraries, WebSocket messages)
- DOM measurements (`getBoundingClientRect`)
- Analytics/logging

```typescript
// GOOD: syncing chart with prop changes
$effect(() => {
  void symbol; void tf; void type;
  if (!chart) return;
  // ...
});
```

### Track dependencies explicitly with `void`

Svelte tracks whatever you READ inside `$effect`. If you need to read a prop to trigger the effect but don't use its value, use `void`:

```typescript
$effect(() => {
  void symbol;  // track symbol changes
  void tf;      // track tf changes
  void type;    // track type changes
  // ...
});
```

### Avoid multiple effects that could race

Two effects tracking overlapping props can both fire on the same tick. Merge into a single effect with a key to distinguish cases:

```typescript
// BAD: two effects, both fire on parent re-render
$effect(() => { void symbol; void tf; fetchAndRender(); });
$effect(() => { void type; renderSeries(); });

// GOOD: single unified effect with key comparison
let fetchedKey = "";
$effect(() => {
  void symbol; void tf; void type;
  if (!chart) return;
  const key = symbol + ":" + tf;
  if (key !== fetchedKey) {
    fetchedKey = key;
    fetchAndRender();  // data change
  } else if (cachedData) {
    renderSeries();    // type-only change
  }
});
```

### Effects must handle stale async results

When an effect triggers an async operation, use a version counter to discard stale results:

```typescript
let fetchVersion = 0;

async function fetchAndRender() {
  const version = ++fetchVersion;
  loading = true;
  const data = await fetchData();
  if (version !== fetchVersion) return;  // stale — discard
  cachedData = data;
  renderSeries();
}
```

### Never set loading state before checking guards

If the effect or function might return early, set loading AFTER the guard check:

```typescript
// BAD: loading stuck true if chart is null
async function fetchAndRender() {
  loading = true;
  if (!chart) return;  // loading stays true forever
}

// GOOD: guard first
async function fetchAndRender() {
  if (!chart) return;
  loading = true;
}
```

## 3. Third-party library lifecycle

### Create once, mutate — don't teardown on every prop change

Libraries like Lightweight Charts, Chart.js, and map SDKs create expensive internal state. Keep the instance alive and swap data/series:

```typescript
onMount(() => {
  chart = createChart(container, options);
  return () => chart.remove();  // only on unmount
});

// Swap series on prop changes — no chart.remove() / createChart()
function renderSeries() {
  clearSeries();
  mainSeries = chart.addSeries(CandlestickSeries, options);
  mainSeries.setData(candles);
}
```

### Check the library's actual API — don't assume methods exist

Library major versions remove or rename methods. Always check the typings:

```typescript
// LW Charts v4: series.remove()  ✓
// LW Charts v5: chart.removeSeries(series)  ✓ (series.remove() removed!)

function removeSeriesFromChart(s: ISeriesApi<any>) {
  chart?.removeSeries(s);  // v5 API
}
```

### Store plugin references for cleanup

Libraries return plugin handles that must be explicitly detached:

```typescript
// BAD: return value discarded — plugin leaks
createSeriesMarkers(mainSeries, markers);

// GOOD: store and detach on cleanup
let markerPlugin: ISeriesMarkersPluginApi<any> | null = null;
// ...
markerPlugin = createSeriesMarkers(mainSeries, markers);
// in clearSeries:
if (markerPlugin) { markerPlugin.detach(); markerPlugin = null; }
```

### ResizeObserver for canvas sizing

Don't use window.resize — use ResizeObserver on the container:

```typescript
$effect(() => {
  if (!container) return;
  resizeObserver?.disconnect();
  resizeObserver = new ResizeObserver(() => {
    const r = container.getBoundingClientRect();
    chart?.applyOptions({ width: r.width, height: r.height });
  });
  resizeObserver.observe(container);
});
```

## 4. `{#each}` reconciliation

### Use keyed each for dynamic lists

```svelte
<!-- BAD: index-keyed — removing item 0 patches all children -->
{#each panels as panel, i}

<!-- GOOD: keyed — Svelte reuses matching components -->
{#each panels as panel (panel.id)}
```

Without a key, Svelte patches props by index. If you remove panel 0, panel 1 becomes index 0 and gets panel 0's props — usually fine but can cause unexpected effect re-fires.

## 5. Loading state patterns

### Absolute overlay — don't disrupt layout

Loading overlays must not participate in flex/grid layout:

```svelte
<!-- BAD: flex-1 takes space, squishes chart -->
{#if loading}
  <div class="flex-1 flex items-center justify-center">Loading...</div>
{/if}

<!-- GOOD: absolute overlay, no layout impact -->
{#if loading}
  <div class="absolute inset-0 z-20 flex items-center justify-center bg-background/80">
    <span class="text-xs text-muted-foreground">Loading...</span>
  </div>
{/if}
```

### Avoid testing intermediate loading states in e2e

With fast APIs or mocked responses, loading overlays flash too quickly to assert on. Test the final state instead:

```typescript
// BAD: racy — overlay may have already cleared
await expect(page.getByTestId("loading-overlay")).toHaveCount(1);

// GOOD: assert the outcome
await expect(panel.getByTestId("chart-symbol")).toHaveText("SPY");
await expect(panel.locator("canvas").first()).toBeVisible();
```

## 6. Data fetching

### Cache data client-side to avoid refetch on type switches

```typescript
let cachedData: ChartData | null = null;

// Fetch only on symbol/TF change
if (key !== fetchedKey) {
  fetchedKey = key;
  fetchAndRender();
} else if (cachedData) {
  renderSeries();  // reuse cached data for type change
}
```

### Route interception for deterministic e2e tests

```typescript
await page.route("**/charts/SPY/data**", async (route) => {
  await route.fulfill({ json: mockData });
});
```

This eliminates network variability and makes symbol/TF change tests deterministic.

## 7. Common pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `series.remove()` in LW Charts v5 | `u.remove is not a function` | Use `chart.removeSeries(series)` |
| Loading state set before early return | Overlay stuck forever | Set loading after guards |
| Two `$effect`s tracking same prop | Race condition, double renders | Merge into single effect with key |
| Plugin return value not stored | Memory leak, stale markers | Store handle, call `.detach()` |
| `$effect` for derived state | Extra render pass | Use `$derived` or `$derived.by` |
| `onMount` + `$effect` both fetch | Double fetch on load | Remove from `onMount`, let effect handle |
