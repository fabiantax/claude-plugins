---
name: system-recon
description: Read the path through source — in parallel — before poking the surface. Use when debugging an unfamiliar multi-hop system (a request that crosses services/adapters/ports), before live-testing or changing routing. Front-loading the trace finds the bug in the config before any test fails.
---

# System recon — trace the path before you poke

The expensive failure mode: **black-box probing surface-by-surface** (is this port up? is
that metric flowing?), each probe revealing the next surprise, when the bug was plain text
in a config the whole time. Front-load one read of the full path; the bug is usually visible
before any live test.

> Worked example: a mesh consult had been firing at a decommissioned port and a too-tight
> timeout — both literally in two files. ~15 reactive probe-turns; one path-read would have
> found both.

## Method
1. **Name the hops.** Write the request path end to end:
   `entrypoint → router/runtime → adapter/handler → backend → metric/sink`. You can't trace
   what you haven't named.
2. **Read the path through source, in parallel.** For each hop, open the config/script/unit
   that defines *where it sends next* and *its timeout/limits*. Fan these out — they're
   independent (one **Explore agent** per hop, or one agent told "trace the whole path"). Do
   NOT do them one-at-a-time waiting on each.
3. **Diff intent vs reality.** For each hop ask: does the endpoint it targets still exist?
   Is the timeout sane for the work? Does the credential/port match what's actually live?
   The classic bugs: **dead endpoint** (a decommissioned port/host still referenced) and
   **mis-set limit** (a timeout/retry too tight for the real latency).
4. **Only then probe live** — to confirm the hypothesis the source already gave you, not to
   discover the bug.

## Checklist per hop
- Where does it send next? (URL/port/model/provider — grep the handler)
- What are its limits? (timeout, retries, concurrency, token budget)
- Does the target still exist & match? (port live? cred valid? model name current?)
- Is there a metric/counter to confirm flow? (so you can watch one request move)

## When to use vs not
- **Use:** multi-hop systems (gateways, routers, adapters, queues), "it's mysteriously idle
  / slow / failing", before changing routing, after a topology change.
- **Skip:** a single-file bug, or when one `rg` answers it. Don't ceremony-wrap a one-liner.

## Pairs with
`/mesh-health` (the mesh-specific instance of this), the `recon` agent (read-only parallel
path tracer), and `/autonomy` (the recon is read-only → proceed without asking).
