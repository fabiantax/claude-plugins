---
name: creative-thinking
description: "Domain-neutral creative-thinking panel — runs several inventive-design lenses (TRIZ technical+physical contradictions & separation principles, Axiomatic Design decoupling, an essential-information vs redundancy lens, a prior-art bridge, plus constraint-relaxation / first-principles / inversion / analogies) on ONE hard design problem in a single sweep, in ANY field — engineering, software architecture, product, systems, process, research, or strategy. Use whenever you want to brainstorm or generate novel, non-obvious solutions by attacking a problem from MANY angles at once, or are stuck on a tradeoff ('improving X worsens Y', or 'it must be both X and not-X'). Defining trigger: wanting multiple lenses together ('all the lenses', 'the whole toolkit', 'throw everything at it') or plain idea-generation asks ('creative way to…', 'novel approaches/angles', 'brainstorm mode', 'we are stuck / hitting a wall on this design') in any domain. For ML-inference / GPU / model-serving / Apple-Silicon design specifically, prefer the calibrated /creative-thinking-ml. Skip for creative writing, debugging / root-cause, summaries, or applying exactly ONE named framework."
argument-hint: "[design problem / contradiction: 'improving X worsens Y' or 'must be both X and not-X' | example]"
user_invocable: true
---

# Creative-thinking engine (domain-neutral)

One pass that pushes a hard design problem — in any field — through a panel of
inventive-design lenses, ordered so each hands the next a sharper problem. **This is
the fusion**: you want the whole panel on the same problem in a single sweep, and you
want the lenses to *interact* — the axiom check can dissolve the contradiction before
you generate; the information reframe tells you which candidates can actually work; the
bridge stops you reinventing what someone else already shipped.

Self-contained — it carries enough of each method inline to run anywhere. The standalone
skills (`/triz`, `/info-lens`, `/aab`, `/constraint-relax`, `/first-principles`,
`/inversion`, `/analogies`, `/ideal-final-result`) go deeper but are calibrated for
ML/inference; for an ML-inference/GPU problem use **`/creative-thinking-ml`** instead.

## When to use

- "Help me brainstorm / think of novel approaches to X."
- "We're stuck — improving X keeps making Y worse" *(technical contradiction)*, or
  "it has to be both big and small / fast and thorough / flexible and simple"
  *(physical contradiction)*.
- "Is this a fundamental limit, or are we just doing it wrong?"
- Any non-trivial design decision — software, hardware, product, process, org,
  research — where you want creative range *and* a feasibility filter, not a brain-dump.

## When NOT to use

- The problem has an obvious answer — just do it; don't ceremony-wrap it.
- The constraint hasn't been **observed/measured** yet. Reasoning on a guessed
  constraint manufactures plausible nonsense. Get the real numbers first, then return.
- You want one framework, not the panel → `/reasoning-toolkit` routes to the best fit.

## The pipeline (≈15–20 min)

Run the stages in order. Each can **short-circuit** the rest — if the axiom check
dissolves the contradiction, you may be done before generating a single idea. Don't
force every stage. Stage 3 has a **reinforcement palette** for when generation stalls.

### Stage 0 — Frame the contradiction

Name it precisely, and classify its **kind** — this picks your generative path:

- **Technical contradiction** — "improving FEATURE_A worsens FEATURE_B" (two different
  parameters trade off). → resolved by the **inventive principles** (Stage 3a).
- **Physical contradiction** — "one parameter must be both X and not-X" (e.g. the config
  surface must be *large* for power and *small* for simplicity). → resolved by the
  **separation principles** (Stage 3b). Physical contradictions are sharper and often
  hide *under* a technical one — push "why does A trade against B?" and you frequently
  surface the single thing pulled two ways.

Naming the pair (and its kind) is ~80% of the value. If you can't write it in one of
these forms, you're not ready — go observe the system.

### Stage 0.5 — Ideal Final Result (aim before you generate)

State the **IFR**: the function delivers *itself*, with zero added cost or structure,
and the harmful effect removes itself. ("The user writes nothing for the common case and
the right thing happens.") You rarely reach it, but the **gap between IFR and reality is
the design target**, and reasoning *backward* from it beats reasoning forward from the
current mess.

### Stage 1 — Axiom check: is the contradiction even real? (Axiomatic Design)

Test whether the contradiction is **self-imposed by a coupled design** before generating
anything. Suh's apparatus:

- **Independence axiom** — each design parameter (DP) should affect exactly one
  functional requirement (FR). Build the **design matrix** (rows = FRs, cols = DPs; mark
  which DP moves which FR):
  - *Diagonal* (each DP → one FR) = **uncoupled** — ideal.
  - *Triangular* = **decoupled** — tunable in the right order, acceptable.
  - *Full* (one DP smears across many FRs) = **coupled** — fragile, and the
    "contradiction" is usually just the coupling biting. **The fix is to decouple**,
    which often dissolves the trade-off rather than trading around it.
- **Information axiom** — among independent designs, prefer the lowest complexity
  (fewest parts, widest tolerance, describable in one paragraph).

If one DP maps to ≥2 FRs, that coupling is your prime suspect. Propose the decoupled
factoring as a candidate in its own right — it frequently beats anything generated.

### Stage 2 — Reframe: essential information vs redundancy

For each FR/candidate, ask: **how few essential elements — bits, parts, rules, steps,
parameters, people, options — carry the load-bearing signal, and how much of the rest is
just redundancy?** The decisive sub-question for "would more X help?":

- **The needed information is present but under-used** (mis-organized, wrong mechanism,
  out-of-its-tested-range) → *fixable*: reorganize, re-budget, or match the mechanism.
- **The needed information is genuinely absent at this budget** (a true bottleneck) → *no
  amount of effort recovers it*; route that requirement to a different mechanism (often
  the Stage-1 decoupling).

Name the *kind* of redundancy (duplication, low-value detail, rare-case clutter,
temporal staleness, excess precision) so the fix removes *that* kind. This is the
feasibility filter — it kills candidates that can't work before you spend on them.

### Stage 3 — Generate candidates

Generate only for the FRs Stage 2 marked feasible.

- **3a — Technical → inventive principles.** Treat each as a *generative prompt* ("what
  would this look like here?"). The domain-general high-hitters:
  *segmentation* (split into independent parts), *extraction* (pull the troublesome part
  onto its own path), *local quality* (different regions get different properties),
  *asymmetry* (treat the hot path unlike the cold), *merging* (combine adjacent
  functions), *nesting* (one structure inside another — hierarchy), *the other way round*
  (invert: pull vs push, lazy vs eager), *dynamics* (make a fixed parameter adapt at
  runtime), *preliminary action* (do it ahead of time — precompute, pre-stage),
  *blessing in disguise* (turn the harmful effect into the mechanism), *intermediary*
  (insert a broker/adapter), *cheap disposability* (many short-lived copies beat one
  precious durable thing), *composite* (hybridize two strategies). Most translations are
  bad; one or two are interesting. (`/triz` has the full 40 + a contradiction matrix —
  ML-calibrated, so map it loosely outside ML.)
- **3b — Physical → separation principles.** Resolve "must be both X and not-X" by
  **separating the conflicting demands**:
  - **in time** — X in one phase, not-X in another (defaults now, overrides later;
    fast screen first, deep review later).
  - **in space** — X in one region, not-X in another (rich detail where it matters,
    coarse elsewhere).
  - **in scale (part ↔ whole)** — X at the component level, not-X at the system level
    (per-item overrides inside a global default).
  - **on condition** — X when a condition holds, not-X otherwise (a simple mode and an
    advanced mode; a budget that adapts to demand).
- **3c — Reinforcement palette** (pull one when 3a/3b stall):
  - **Constraint-relaxation** (`/constraint-relax`) — temporarily *delete* the binding
    constraint, see what becomes possible, then price relaxing it 10×.
  - **First-principles** (`/first-principles`) — strip to base truths and rebuild. Use
    when "that's how it's done" is the only justification.
  - **Inversion** (`/inversion`) — ask "how would I *guarantee* this fails?" to surface
    load-bearing assumptions, then avoid them.
  - **Analogies** (`/analogies`) — map onto solved problems in other fields (databases,
    OS, biology, economics, logistics, law): caching, queuing, markets, redundancy, tiers.

### Stage 4 — Bridge to prior art

Fresh candidates usually resemble something already shipped — somewhere. Before building,
bridge so you *adapt* a proven solution instead of reinventing it:

1. **Catalog** adjacent prior art (5–10 entries; thin catalog → the generated candidate
   stands alone, skip the bridge).
2. **Diagnose the blocker** — the *single structural feature* of your setting that stops
   a direct copy. Name the exact mechanism/constraint/invariant, not "it's different."
3. **Minimum bridge** — the smallest change that removes the blocker while leaving the
   rest untouched.
4. **Validate in isolation** before committing the whole thing. (Depth: `/aab`.)

### Stage 5 — Final axiom check + rank

Re-apply Independence + Information to the survivors. Lead with the candidate that serves
one FR cleanly (decoupled) and is describable in one paragraph (low complexity). The rest
are backups or compose orthogonally.

## Worked example — config system: powerful ↔ simple

A non-ML run, end-to-end.

- **Stage 0.** *Technical:* "more expressiveness (power) worsens learnability
  (simplicity)." Push it → *physical:* **the config surface must be both LARGE (express
  anything) and SMALL (easy to learn).**
- **Stage 0.5 — IFR.** "The user writes nothing for the common case and the system does
  the right thing; the rare case stays possible." Gap from IFR: today every option is on
  the common path → the gap points at *defaults*.
- **Stage 1 — axiom (the key move).** One config format serves two FRs (power +
  learnability) → *coupled*. Decouple: **sensible defaults** (DP1 → simplicity) +
  **explicit overrides / escape hatch** (DP2 → power). Triangular: defaults first,
  override only when needed.
- **Stage 2 — information vs redundancy.** How few concepts for the 90% case? Very few —
  and they're present, just buried. The redundancy is *rare-case clutter on the common
  path*. So it's an organization problem (present-but-mis-surfaced), **not** a fundamental
  one → fixable by layering, no expressiveness sacrificed.
- **Stage 3.** *3a:* extraction (move advanced options to a separate layer), preliminary
  action (ship good defaults), local quality (per-component overrides). *3b separation:*
  on condition (simple vs advanced mode); in time (defaults now, override later); in scale
  (global default + per-item overrides). *3c:* inversion ("to guarantee it's unusable,
  require every option up front" → so don't); analogies (Rails convention-over-config; the
  CSS cascade; `.gitconfig` layering; UX progressive disclosure).
- **Stage 4 — bridge.** Catalog: convention-over-configuration, cascading/layered config
  (CSS, git), feature flags, progressive disclosure. Blocker (if any): "validation is
  all-or-nothing." Bridge: layered resolution (defaults ← profile ← explicit) — a small,
  local change.
- **Stage 5 — rank.** Information axiom → lead with **defaults + escape-hatch**
  (decoupled, one paragraph, nothing given up). Layered overrides next; full schema-DSL
  last (re-couples power into the common path).

*Same pipeline on a non-engineering problem* — a hiring process that must be "fast AND
thorough": separate **in time** — a cheap fast screen gates a deep slow final round. Not
a fundamental tradeoff, a sequencing one.

## Anti-patterns

| Smell | Fix |
|---|---|
| **Skipping Stage 0 / mis-classifying the contradiction** | A physical contradiction run as a technical one (or vice-versa) generates weak candidates. Name the pair *and its kind* first. |
| **Framework theater** | Marching all stages + the whole palette for a small fix. Let early stages short-circuit; pull reinforcements only when 3a/3b stall. |
| **Generating before the axiom/information filter** | Brainstorming candidates the feasibility stage would kill as bottlenecks. Filter (1–2) *before* you generate (3). |
| **"Improves everything at once"** | A candidate that helps every FR usually hides a coupling. Find the DP↔FR collision. |
| **Bridge that's a redesign** | If the "bridge" rebuilds half the system, it isn't a bridge — find a smaller one or accept the standalone candidate. |
| **Decorating, not deciding** | If you already knew the answer, you're justifying it, not thinking. The stages should change your mind sometimes. |

## Relationship to the other skills

| Want | Use |
|---|---|
| The whole panel, any domain, one sweep | **this skill** |
| The same panel calibrated for ML-inference / GPU / model-serving | `/creative-thinking-ml` |
| Route to the single best framework for the moment | `/reasoning-toolkit` |
| Contradiction engine + 40 principles + separation (ML-calibrated tables) | `/triz` |
| Prior-art catalog → blocker → bridge | `/aab` |
| Delete the binding constraint and look | `/constraint-relax` |
| Rebuild from base truths | `/first-principles` |
| Surface load-bearing assumptions | `/inversion` |
| Steal a solution from another field | `/analogies` |
| The zero-added-structure ideal to aim at | `/ideal-final-result` |

## Output format when invoked

Produce, compactly (fit it in a chat reply — don't write the textbook):
1. **Contradiction** — the pair, classified technical vs physical (Stage 0), and the IFR.
2. **Axiom check** — the FR↔DP design matrix; flag coupling and the decoupled factoring.
3. **Feasibility** — per FR: genuine bottleneck (route away) vs present-but-underused (fixable).
4. **Candidates** — the 2–3 principles / separations that translated well (note any
   reinforcement lens used), bridged to prior art.
5. **Ranked recommendation** — the axiom-winner first with the one-line *why*, then
   backups / what composes orthogonally.
