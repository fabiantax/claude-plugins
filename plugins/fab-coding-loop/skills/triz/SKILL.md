---
name: triz
description: Apply TRIZ (Theory of Inventive Problem Solving) to surface non-obvious algorithmic or engineering solutions. Uses contradiction matrix, Ideal Final Result, Substance-Field analysis, and the 40 inventive principles to escape the "obvious surveyed-solution" trap and propose novel candidates.
---

# TRIZ — Theory of Inventive Problem Solving

Use when:
- You've surveyed the literature and the "best surveyed answer" feels like a compromise.
- A real contradiction is blocking progress (improving A worsens B).
- The team is converging on the obvious next step and you want to surface what they're not seeing.
- A new problem maps to an old, solved problem in a different domain.

Don't use for:
- Picking between two well-defined options — use `/prioritize` instead.
- Implementation/planning — use `/plan-and-decompose`.
- Pure research synthesis — use the researcher agent.

TRIZ is for the moment **before** prioritization, when you suspect the candidate list is missing the right answer.

---

## Inputs

User describes a problem. Ask for these explicitly if missing:

1. **Goal** — what is being optimized for? (one sentence)
2. **Surveyed candidates** — what algorithms/approaches have been considered? (3-5 named, with their tradeoffs)
3. **The contradiction** — what does each candidate make worse to improve the goal?
4. **Constraints** — what cannot change? (interface, runtime budget, language, deps)
5. **Existing system** — what data structures / fields / substances already exist that we might exploit?

If contradictions are vague ("I want it fast AND correct"), push back — TRIZ needs a *specific* contradiction (e.g., "speed (O(N) angular) vs concavity-fidelity (O(N log N) Delaunay)").

---

## Process

Run all four phases. Output them in order. Don't skip any.

### Phase 1 — Frame the contradiction

Write the contradiction as a one-line technical claim:

> "Improving **<feature A>** with the obvious approaches forces us to worsen **<feature B>**."

Then locate it on the **classical TRIZ contradiction matrix** by mapping A and B to one of the 39 engineering parameters. Common ones for software:

| Parameter | Software analogue |
|---|---|
| Speed (#9) | Runtime / latency / throughput |
| Accuracy of measurement (#28) | Correctness on edge cases / approximation error |
| Productivity (#39) | Lines of code, ergonomics, dev velocity |
| Complexity of system (#36) | Algorithmic complexity, dep count, conceptual load |
| Complexity of control (#37) | Configuration burden, tuning surface |
| Adaptability (#35) | Generality, polymorphism, dataset breadth |
| Loss of substance (#23) | Memory footprint, GC pressure, IO bandwidth |
| Stability of object (#13) | Robustness, determinism, reproducibility |
| Reliability (#27) | Test stability, error recovery, fault tolerance |
| Use of energy (#19) | CPU/GPU cycles, network round-trips |

You don't need to be precise — the mapping just unlocks the right cell of the matrix.

### Phase 2 — Ideal Final Result (IFR)

Write what the *perfect* system would do — one that resolves the contradiction by making one side disappear:

> "The polygon emerges with **zero extra computation** — it's a side effect of work we already do."
> "Validation happens **without any validation code** — invalid states are unrepresentable in the type system."
> "The cache **invalidates itself** — there is no invalidation logic."

The IFR is intentionally absurd. Its job is to point at the constraint that, if relaxed, makes the problem trivial. Ask: *what work am I already doing that I could repurpose?*

### Phase 3 — Apply the 40 inventive principles

For each principle that plausibly applies, write one concrete instantiation in the problem domain. Don't list all 40 — pick the 4-8 most relevant, instantiate hard.

Mapping software analogues for the most useful principles:

| # | Principle | Software pattern |
|---|---|---|
| 1 | Segmentation | Sharding, partitioning, decomposition into smaller subproblems |
| 2 | Taking out / Extraction | Delete the layer entirely; do it inline; skip the abstraction |
| 3 | Local quality | Different algorithm per region; adaptive precision; per-tile tuning |
| 5 | Merging | Coalesce two passes into one; fold steps; combine data structures |
| 6 | Universality | One function many uses (e.g., serde for both wire and storage) |
| 7 | Nested doll | Hierarchical structures (B-tree, R-tree, CCH) |
| 10 | Preliminary action | Precompute; build index at write time, not read time |
| 13 | Inversion | Reverse the operation (anti-join, complement set, work backwards) |
| 14 | Spheroidality / Curvature | Polar/log coords; non-Cartesian space; cyclic data structures |
| 15 | Dynamics | Adaptive parameters; runtime-tuned; auto-scaling |
| 17 | Another dimension | Add a coordinate (time, layer); 2D → 3D; embed in higher-dim space |
| 19 | Periodic action | Batching; tick-based instead of event-driven; sampling |
| 20 | Continuity of useful action | Streaming; pipeline; backpressure-driven |
| 22 | Blessing in disguise | Use harmful effect as the signal (e.g., cache miss → prefetch hint) |
| 23 | Feedback | Online learning; control loops; PID-style adjustment |
| 24 | Intermediary | Coordinator/proxy/adapter; bridge two incompatible systems |
| 25 | Self-service | The system serves itself (idempotent retry; self-healing; auto-bootstrap) |
| 26 | Copying | Use a cheap proxy (sketch, sample, lower-dim embedding) for the expensive query |
| 28 | Mechanics substitution | Replace geometry/structure with semantics; e.g., graph instead of point cloud |
| 32 | Color changes | Tagged unions; phantom types; type-level distinctions |
| 35 | Parameter changes | Change the representation (compressed, quantized, different basis) |
| 40 | Composite materials | Hybrid algorithm — fast path + accurate path + fallback |

For each candidate principle, write:

```
Principle #N (<name>): <one-line instantiation>
Why it might work: <one sentence>
Why it might fail: <one sentence>
```

### Phase 4 — Substance-Field check

Model the problem as **substances** (the data) and **fields** (the operations / forces between them). Identify:

1. **Substances present**: what data already exists? (CSR graph, settled distances, edge geometries, R-tree, ...)
2. **Fields present**: what operations are running over them? (Dijkstra, contains-query, ...)
3. **Missing field**: what field, if added, would make the problem trivial?
4. **Harmful field**: what existing operation is fighting us?

The goal is to find a way to **add a field that uses already-present substances** — that's TRIZ's signature move. New computation on existing data beats new data on existing computation.

---

## Output

Deliver a single response with these four sections, in this order:

```markdown
## TRIZ analysis: <problem one-liner>

### Contradiction
Improving <A> worsens <B>. Matrix cell: <param #N> vs <param #M>.

### Ideal Final Result
"<the absurd one-liner>"
Implication: <what constraint would have to be relaxed>

### Inventive principles (top 4-8)
- **#N <name>**: <concrete instantiation in the domain>
- ... (one per row)

### Substance-Field check
- Substances: <list>
- Fields: <list>
- Missing field: <what would unlock the IFR>
- Proposed new field on existing substance: <the candidate algorithm>

### Verdict
**The TRIZ-derived candidate**: <one paragraph algorithm sketch>

**Dominates surveyed candidates because**:
| Property | Best surveyed | TRIZ candidate |
|---|---|---|
| ... | ... | ... |

**Risks / failure modes**: <2-3 honest bullets>

**Next concrete step**: <1-2 line "what to prototype to validate">
```

---

## Honest caveats

- **TRIZ is not a magic wand.** It is a discipline for asking better questions. You can run the whole framework and end up confirming the surveyed answer. That's a valid output.
- **The IFR is the most powerful step.** Most TRIZ wins come from taking the IFR seriously and asking "what constraint would I have to relax to get this?" not from picking the right inventive principle.
- **The contradiction matrix is from 1970s mechanical engineering.** The 40 principles transfer reasonably; the matrix lookups are approximate at best. Don't get religious about which cell.
- **Substance-Field analysis is the underrated tool.** "Add a new field on existing substance" is the recipe for ~70% of TRIZ wins in software.
- **Counter-bias check**: TRIZ tends to over-recommend novel solutions. If the surveyed approach is the right answer and you've TRIZ'd into a fancier candidate, prefer the boring choice unless the gap is large and well-quantified. The verdict table is where you make this honest.

---

## Worked example (the one that prompted this skill)

**Problem**: concave-hull polygonization for road-network isochrones (8000 settled nodes; preserve real concavities from rivers/highways; <50ms).

**Contradiction**: Speed (#9, O(N) angular sweep) vs Accuracy of measurement (#28, Delaunay-of-points captures concavity at O(N log N) + heuristic).

**IFR**: "The polygon emerges for free as a side effect of Dijkstra settling. There is no separate polygonization step."

**Relevant principles**:
- **#2 Extraction**: delete the polygonization step entirely. Use the SSSP cut directly.
- **#25 Self-service**: Dijkstra already touches every frontier edge — make it record them.
- **#28 Mechanics substitution**: replace the geometric (point-cloud) approach with a topological (graph-edge) one.
- **#3 Local quality**: handle bridges, cul-de-sacs, T-intersections with localized rules at face-walk time.

**Substance-Field**:
- Substances: CSR graph, edge polylines, `dist[v]` per settled node, R-tree index.
- Fields: Dijkstra relaxation, point-in-polygon, k-NN lookup.
- Missing field: **edge-bearing sort at each node** (cheap precompute, enables planar face walking).
- Proposed new field on existing substance: **frontier-edge tracing** — extract boundary directly from edges (u,v) where dist[u] ≤ budget < dist[u] + w(u,v), then trace face walks via bearing-sorted next-CCW-edge.

**Verdict**: This algorithm doesn't appear in the literature (concaveman, χ-shapes, GraphHopper Delaunay-contour) because they all treat settled nodes as an abstract point cloud and lose the graph structure. Preserves IJ-river concavities for free (graph has no edges crossing the river except at bridges), handles disconnected islands as multi-polygon, O(frontier) compute ≈ O(√N).

This is the prototype to validate.

---

## When TRIZ confirms the boring answer

Sometimes the contradiction is genuine and irreducible. If you run all four phases and the only candidates are slight variants of the surveyed approach, **say so**. The honest output is:

> "TRIZ surfaced no candidate that dominates [surveyed approach]. The contradiction between A and B appears to be fundamental in this problem class. Recommend shipping [surveyed approach]."

That's still a useful output — it converts "I have a vague unease about the obvious answer" into "I have systematically searched and the obvious answer is correct."
