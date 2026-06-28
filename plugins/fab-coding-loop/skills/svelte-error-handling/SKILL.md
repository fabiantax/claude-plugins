---
name: svelte-error-handling
description: Svelte 5 Error Handling & Logging
---

# Svelte 5 Error Handling & Logging

Patterns for catching, logging, and recovering from errors in Svelte 5 apps.

---

## 1. `<svelte:boundary>` — component error boundaries

Svelte 5.3+ provides `<svelte:boundary>` to catch rendering and `$effect` errors in a subtree.

```svelte
<script>
  import ErrorFallback from './ErrorFallback.svelte';

  function handleBoundaryError(error) {
    // error is the thrown value
    console.error('[boundary]', error.message, error.stack);
    // send to error tracking service
    reportError(error);
  }
</script>

<svelte:boundary onerror={handleBoundaryError}>
  {#snippet failed(error, reset)}
    <ErrorFallback {error} {reset} />
  {/snippet}

  <ChartPanel {symbol} {indicators} />
</svelte:boundary>
```

Key points:
- `onerror` receives the error object. Called for rendering errors and `$effect` errors within the boundary's subtree.
- `failed` snippet receives `(error, reset)`. Call `reset()` to re-render the failed component.
- Errors NOT caught: async callback errors, event handler errors, `onMount` async body errors (unless re-thrown into rendering).
- Boundaries nest: innermost boundary catches first. Uncaught errors bubble up.

### When to use boundaries

- Around third-party library wrappers (chart libraries, map SDKs) that may throw during render.
- Around data-fetching components where the fetch failure should show a retry UI.
- Around lazy-loaded route components.

### When NOT to use boundaries

- For form validation or user input errors — use explicit UI state instead.
- For expected error flows (404, empty state) — those are not errors, they're states.

## 2. Global error handlers

Boundaries don't catch everything. Add global handlers for uncaught errors:

```typescript
// main.ts or a top-level +layout.svelte
window.addEventListener('error', (event) => {
  console.error('[global]', event.error);
  reportError(event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('[unhandled rejection]', event.reason);
  reportError(event.reason);
});
```

This catches:
- Uncaught errors in `onclick`, `oninput`, and other DOM event handlers
- Uncaught promise rejections (forgotten `.catch()` or un-awaited async calls)
- Errors in `setTimeout`/`setInterval` callbacks

## 3. Async error patterns in Svelte

`$effect` with async code requires careful handling:

```typescript
// WRONG: $effect does not await — unhandled rejection
$effect(() => {
  fetchData().then(d => data = d);  // rejection is unhandled!
});

// RIGHT: catch explicitly
$effect(() => {
  fetchData()
    .then(d => data = d)
    .catch(e => { error = e.message; console.error('[fetch]', e); });
});

// ALSO RIGHT: async IIFE with boundary-friendly throw
$effect(() => {
  let cancelled = false;
  (async () => {
    try {
      const d = await fetchData();
      if (!cancelled) data = d;
    } catch (e) {
      if (!cancelled) throw e;  // boundary catches this in $effect
    }
  })();
  return () => { cancelled = true; };
});
```

## 4. Structured logging pattern

Use a consistent log format for debugging:

```typescript
const log = {
  info: (component: string, msg: string, data?: unknown) =>
    console.log(`[${component}] ${msg}`, data ?? ''),
  error: (component: string, msg: string, err?: unknown) =>
    console.error(`[${component}] ${msg}`, err ?? ''),
};

// Usage in component:
log.info('ChartPanel', 'loading data', { symbol, tf });
log.error('ChartPanel', 'fetch failed', e);
```

## 5. Error display patterns

### Inline error (within component)

```svelte
{#if error}
  <div class="flex items-center justify-center flex-1">
    <span class="text-xs text-destructive">{error}</span>
  </div>
{/if}
```

### Boundary fallback with retry

```svelte
{#snippet failed(error, reset)}
  <div class="flex flex-col items-center justify-center flex-1 gap-2">
    <span class="text-sm text-destructive">{error.message}</span>
    <button onclick={reset} class="text-xs text-info hover:underline">Retry</button>
  </div>
{/snippet}
```

### Toast notifications (for non-blocking errors)

Use a reactive error store that auto-clears:

```typescript
// error-store.svelte.ts
let toasts = $state<Array<{ id: number; message: string; level: 'error' | 'warn' }>>([]);

export function addToast(message: string, level: 'error' | 'warn' = 'error') {
  const id = Date.now();
  toasts.push({ id, message, level });
  setTimeout(() => { toasts = toasts.filter(t => t.id !== id); }, 5000);
}

export function getToasts() { return toasts; }
```

## 6. Playwright console error capture

When testing with Playwright, capture browser console errors:

```typescript
const errors: string[] = [];
const warnings: string[] = [];

page.on('console', (msg) => {
  if (msg.type() === 'error') errors.push(msg.text());
  if (msg.type() === 'warning') warnings.push(msg.text());
});

page.on('pageerror', (error) => {
  errors.push(`PAGE ERROR: ${error.message}`);
});

// After test actions:
if (errors.length) {
  console.error(`\n${errors.length} console errors:`);
  errors.forEach(e => console.error(`  - ${e}`));
}
```

## References

- Svelte 5 docs: https://svelte-5-preview.vercel.app/docs/svelte-boundary
- Svelte errors: https://svelte.dev/docs/svelte/compiler-errors
- MDN ErrorEvent: https://developer.mozilla.org/en-US/docs/Web/API/ErrorEvent
- MDN PromiseRejectionEvent: https://developer.mozilla.org/en-US/docs/Web/API/PromiseRejectionEvent
