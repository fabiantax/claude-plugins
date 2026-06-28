---
name: creative-thinking-ml
description: "ML-inference / Apple-Silicon variant of the creative-thinking panel. Runs several inventive-design lenses (TRIZ technical+physical contradictions & separation principles, Axiomatic Design decoupling, the information lens 'bits per useful token', the Algorithm-Architecture Bridge, plus constraint-relaxation / first-principles / inversion / analogies) on ONE hard LLM-inference, GPU-kernel, quantization, KV-cache, speculative-decoding, attention, or MLX/Metal design problem — with calibrated examples and the /triz, /info-lens, /aab reference tables. Prefer this over the generic /creative-thinking whenever the problem is ML / model-serving / Apple-Silicon. Defining trigger: a stuck inference design tradeoff ('improving tg/s worsens memory', 'compression worsens quality', 'one knob must be both large and small') OR wanting many inventive lenses at once on an ML-perf or architecture problem ('all the lenses', 'the whole toolkit', 'brainstorm novel approaches', 'we are stuck / hitting a wall') that names or implies ML / MLX / CUDA / quant / KV-cache / attention / decoding. Skip for non-ML design (use /creative-thinking), creative writing, debugging / root-cause, paper summaries, or applying exactly ONE named framework."
argument-hint: "[design problem / contradiction: 'improving X worsens Y' or 'must be both X and not-X' | example]"
user_invocable: true
---

# Creative-thinking engine — ML-inference

One pass that pushes a hard design problem through a panel of inventive-design
lenses, ordered so each hands the next a sharper problem. The standalone skills
(`/triz`, `/info-lens`, `/aab`, `/constraint-relax`, `/first-principles`,
`/inversion`, `/analogies`, `/ideal-final-result`, plus `/reasoning-toolkit` as the
router) exist for when you want exactly one. **This skill is the fusion** — for when
you want the whole panel on the same problem in a single sweep, and you want the
lenses to *interact*: the axiom check can dissolve the contradiction before you
generate; the bits reframe tells you which candidates can physically work; the
bridge stops you reinventing what the field already shipped.

This is the **ML-inference / Apple-Silicon** variant — the examples, the contradiction
matrix, and the prior-art catalog are calibrated for LLM-inference, GPU kernels,
quantization, and KV-cache work. For a non-ML / any-domain problem, use the generic
**`/creative-thinking`** instead (same pipeline, domain-neutral).

## When to use

- "Help me brainstorm / think of novel approaches to X."
- "We're stuck — improving X keeps making Y worse" *(technical contradiction)*, or
  "this thing has to be both big and small / fast and accurate" *(physical contradiction)*.
- "What would TRIZ / axiomatic design / a framework say about this?"
- "Is this a fundamental limit or are we just doing it wrong?"
- Any non-trivial design decision where you want creative range *and* a feasibility
  filter, not just a brainstorm dump.

## When NOT to use

- The problem has an obvious engineering answer — just code it; don't ceremony-wrap.
- The constraint hasn't been **measured** yet. Reasoning on a hand-waved constraint
  manufactures plausible nonsense. Measure first (`/llm-perf` for perf), then return.
- You want one framework, not the panel → `/reasoning-toolkit` routes to the best fit.

## The pipeline (≈15–20 min)

Run the stages in order. Each can **short-circuit** the rest — if the axiom check
dissolves the contradiction, you may be done before generating a single principle.
Don't force every stage if an early one answers it. Stage 3 has a **reinforcement
palette** to pull from when the matrix comes up dry.

### Stage 0 — Frame the contradiction (TRIZ entry)

Name it precisely, and classify which **kind** it is — this picks your generative path:

- **Technical contradiction** — "improving FEATURE_A worsens FEATURE_B" (two different
  parameters trade off). → resolved via the **contradiction matrix → 40 principles**
  (Stage 3a).
- **Physical contradiction** — "one parameter must be both X and not-X" (e.g. the
  latent budget must be *large* for comprehension and *small* for memory). → resolved
  via the **separation principles** (Stage 3b). Physical contradictions are sharper
  and often hide *under* a technical one — push a technical contradiction ("why does
  A trade against B?") and you frequently surface the single parameter pulled two ways.

Naming the pair (and its kind) is ~80% of the value. If you can't write it in one of
these two forms, you're not ready — go measure.

### Stage 0.5 — Ideal Final Result (aim before you generate)

State the **IFR**: the system delivers the function *by itself*, with zero added
cost/structure, and the harmful effect removes itself. ("The cache stores only the
bits the eventual question needs, and nothing else.") You almost never reach the IFR,
but the **gap between IFR and reality is the design target**, and reasoning *backward*
from it beats reasoning forward from the current mess. (Depth: `/ideal-final-result`.)

### Stage 1 — Axiom check: is the contradiction even real? (Axiomatic Design)

Test whether the contradiction is **self-imposed by a coupled design** before
generating anything. Suh's apparatus:

- **Independence axiom** — each design parameter (DP) should affect exactly one
  functional requirement (FR). Build the **design matrix** (rows = FRs, cols = DPs,
  mark which DP moves which FR):
  - *Diagonal* (each DP → one FR) = **uncoupled** — ideal.
  - *Triangular* = **decoupled** — tunable in the right order, acceptable.
  - *Full* (one DP smears across many FRs) = **coupled** — fragile, and the
    "contradiction" is usually just the coupling biting. **The fix is to decouple**,
    which often dissolves the trade-off rather than trading around it.
- **Information axiom** — among independent designs, prefer the lowest complexity
  (fewest parameters, widest tolerance, describable in one paragraph).

If one DP maps to ≥2 FRs, that coupling is your prime suspect. Propose the decoupled
factoring as a candidate in its own right — it frequently beats anything generated.

### Stage 2 — Reframe in bits: bottleneck or extrapolation? (Information lens)

For each FR/candidate, ask the question that unifies all compression-style problems:
**how few bits per useful unit, while preserving the loss-relevant information?** The
decisive sub-question for "would more X help?":

- **Info present but under-served** (coverage / out-of-distribution / wrong mechanism)
  → *fixable*: more data, more budget, or a matched mechanism moves it.
- **Info physically absent at this budget** (a true bottleneck) → *no amount of
  training/tuning recovers it*; route that FR to a different mechanism (often the
  Stage-1 decoupling). Name the redundancy structure (range, outlier, rank, sparsity,
  temporal, positional) so the mechanism matches it. (Table: `/info-lens`.)

This is the feasibility filter — it kills candidates that can't physically work before
you spend on them.

### Stage 3 — Generate candidates

Generate only for the FRs Stage 2 marked feasible.

- **3a — Technical → matrix.** Look up the improving × worsening pair in the
  contradiction matrix (`/triz` has the LLM-inference subset); take the 3–5 associated
  principles; treat each as a *generative prompt* ("what would [principle] look like
  here?"). Most translations are bad; one or two are interesting. Don't enumerate all 40.
- **3b — Physical → separation principles.** Resolve "must be both X and not-X" by
  **separating the conflicting demands**:
  - **in time** — X during one phase, not-X during another (compress small at prefill,
    expand on demand at query time).
  - **in space** — X in one region, not-X in another (full precision on hot tokens,
    coarse elsewhere).
  - **in scale (part ↔ whole)** — X at the component level, not-X at the system level
    (hierarchical: fine local pools inside a coarse global one).
  - **on condition** — X when a condition holds, not-X otherwise (budget that adapts to
    query / information density).
- **3c — Reinforcement palette** (pull one when 3a/3b stall):
  - **Constraint-relaxation** (`/constraint-relax`) — temporarily *delete* the binding
    constraint, see what becomes possible, then price relaxing it 10×. ("If memory
    weren't the constraint, you'd keep full KV — so the real question is purely *which
    tokens to drop*.")
  - **First-principles** (`/first-principles`) — strip to physical/math primitives and
    rebuild. Use when "that's how it's done" is the only justification.
  - **Inversion** (`/inversion`) — ask "how would I *guarantee* this fails?" to surface
    load-bearing assumptions. ("Spend latents uniformly on filler" → so don't.)
  - **Analogies** (`/analogies`) — map onto solved problems in databases, OS,
    networking, biology, economics (caching, paging, LRU, indexing, compression codecs).

### Stage 4 — Bridge to prior art (Algorithm-Architecture Bridge)

Fresh candidates usually resemble something the field already shipped. Before building,
run AAB so you *adapt* a proven mechanism instead of reinventing it:

1. **Catalog** adjacent prior art (5–10 entries; thin catalog → AAB is the wrong tool,
   the generated candidate stands alone).
2. **Diagnose the blocker** — the *single structural feature* of your setting that
   stops a direct port. Name the exact tensor/op/invariant, not "it's different."
3. **Minimum bridge** — the smallest architectural change that removes the blocker while
   leaving the no-bridge path's quality untouched.
4. **Validate in isolation** before composing end-to-end. (Depth: `/aab`.)

### Stage 5 — Final axiom check + rank

Re-apply Independence + Information to the survivors. Lead with the candidate that
serves one FR cleanly (decoupled) and is describable in one paragraph (low information
content). The rest are backups or compose orthogonally.

## Worked example — still-kv: compression ↔ comprehension

End-to-end, so the hand-offs and the new physical-contradiction path are visible.

- **Stage 0.** *Technical:* "compression ratio↑ (memory↓) worsens passage comprehension
  (accuracy↓)," measured util 0.6→0.4 from 4×→14×. Push it and the *physical*
  contradiction surfaces: **`n_latents` must be LARGE (hold passage detail) AND SMALL
  (memory savings).**
- **Stage 0.5 — IFR.** "The cache keeps exactly the tokens the eventual question needs,
  nothing else." Gap from IFR: we compress *query-agnostically*, so we can't know which
  tokens matter → the gap points straight at salience / query-conditioning.
- **Stage 1 — axiom (the key move).** The three quality axes degrade differently (gist
  robust, needle a flat floor, passage between) — the fingerprint of a **coupled**
  design: one DP (uniform `n_latents`) smears across three FRs (gist / passage / needle).
  Design matrix is *full* → decouple to *triangular*: gist pool (FR1) + verbatim
  salience side-cache (FR3) + query-conditioned top-up (FR2).
- **Stage 2 — bits.** Needle (exact recall) is a true **bottleneck** at 2048 latents —
  the exact tokens aren't in the representation, *no training fixes it* → route to the
  side-channel. Passage degradation is **extrapolation** (trained 1×–4× / ≤8K, tested
  14× / 29K) → trainable. Gist already lossless → leave it.
- **Stage 3.** *3a technical:* principles 3 (local quality → density-adaptive latents),
  22 (blessing in disguise → offload exact recall), 23 (feedback → query top-up).
  *3b physical (the new path):* separate "large-and-small `n_latents`" **on condition**
  → density/query-adaptive budget; **in scale** → hierarchical coarse+fine pools;
  **in time** → compress small at prefill, expand on-demand at query time.
  *3c reinforcement:* constraint-relax ("memory free → keep full KV → problem is purely
  *which* tokens to drop" → salience); inversion ("to guarantee failure, spend latents
  uniformly on filler" → so don't).
- **Stage 4 — bridge.** Catalog: SnapKV, H2O, PyramidKV, StreamingLLM, landmark
  attention. Blocker: those do *online eviction during decode*; still-kv does *amortized
  compress-once over prefill*. Bridge: borrow SnapKV's salience scoring at prefill to
  populate the side-cache, without touching the compress-once property.
- **Stage 5 — rank.** Information axiom → lead with the salience side-cache (one
  paragraph, fixes the *worst* axis training can't, decoupled). Density-adaptive latents
  + longer-context training next (passage, in-distribution). Query top-up / KL-training
  last (couples back in; only if passage is still short).

Payoff: the panel *reordered the backlog* — the cheap decoupling beats "train the
coupled compactor harder," which Stage 2 proves can never fix needles, and the physical
contradiction surfaced the query-adaptive budget that the technical framing alone missed.

## Anti-patterns

| Smell | Fix |
|---|---|
| **Skipping Stage 0 / mis-classifying the contradiction** | A physical contradiction run through the technical matrix (or vice-versa) generates weak candidates. Name the pair *and its kind* first. |
| **Framework theater** | Marching all stages + the whole palette for a 4-line fix. Let early stages short-circuit; pull reinforcements only when 3a/3b stall. |
| **Generating before the axiom/bits filter** | TRIZ-ing candidates the bits stage would kill as bottlenecks. Filter feasibility (1–2) *before* you generate (3). |
| **"Improves everything at once"** | A candidate that helps every FR usually hides a coupling. Find the DP↔FR collision. |
| **Bridge that's a redesign** | If the AAB "bridge" rewrites half the system, it isn't a bridge — find a smaller one or accept the standalone candidate. |
| **Decorating, not deciding** | If you already knew the answer, you're justifying it, not thinking. The stages should change your mind sometimes. |

## Relationship to the standalone skills

| Want | Use |
|---|---|
| The whole panel, interacting, one sweep | **this skill** |
| Route to the single best framework for the moment | `/reasoning-toolkit` |
| Contradiction engine + 40 principles + matrix + separation | `/triz` |
| Bits/redundancy analysis + mechanism table | `/info-lens` |
| Prior-art catalog → blocker → bridge | `/aab` |
| Delete the binding constraint and look | `/constraint-relax` |
| Rebuild from physical primitives | `/first-principles` |
| Surface load-bearing assumptions | `/inversion` |
| Steal a solution from another domain | `/analogies` |
| The zero-added-structure ideal to aim at | `/ideal-final-result` |
| Confirm the constraint is real/binding first | `/llm-perf` |
| The same panel for a NON-ML / any-domain problem | `/creative-thinking` |

This skill intentionally **duplicates none** of their reference tables (the full 40
principles, the contradiction matrix, the redundancy↔mechanism table, the AAB catalog,
the analogy domains). When a stage needs the exhaustive material, open the corresponding
standalone skill — keeping each table in one place avoids drift.

## Output format when invoked

Produce, compactly (fit it in a chat reply — don't write the textbook):
1. **Contradiction** — the pair, classified technical vs physical (Stage 0), and the IFR.
2. **Axiom check** — the FR↔DP design matrix; flag coupling and the decoupled factoring.
3. **Bits** — per FR: bottleneck (route away) vs extrapolation (fixable).
4. **Candidates** — the 2–3 principles / separations that translated well (note any
   reinforcement lens used), bridged to prior art.
5. **Ranked recommendation** — the axiom-winner first with the one-line *why*, then
   backups / what composes orthogonally.
