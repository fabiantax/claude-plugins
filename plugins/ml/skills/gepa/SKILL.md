---
name: gepa
description: Optimize prompts, code, and other textual system components with GEPA (Genetic-Pareto reflective evolution). Use when tuning an LLM prompt, a code snippet, or any text artifact against an eval metric — locally on Strix Halo via the llama-server on :8002. Covers gepa.optimize(), optimize_anything(), the GEPAAdapter interface, and DSPy integration.
allowed-tools: Read Bash Edit Write
---

# GEPA — Reflective Text Evolution (Strix Halo)

GEPA (Genetic-Pareto) optimizes any system with **textual parameters** — prompts, code, agent
instructions, configs — against an evaluation metric. Instead of gradients it uses **reflection**:
it runs the candidate, reads the *full execution trace* (outputs, errors, logs), an LLM diagnoses
why it failed in natural language, proposes a targeted mutation, and keeps a **Pareto frontier** of
candidates that each win on different slices of the eval set. Beats GRPO RL and MIPROv2 with far
fewer rollouts (ICLR 2026 Oral).

> **The loop:** select (Pareto) → execute on minibatch + capture traces → reflect (LLM diagnoses) →
> mutate → accept if improved + update frontier. The diagnostic feedback is the "gradient analogue"
> (GEPA calls it *Actionable Side Information*).

## Install location (already set up)

- venv: `~/.claude/skills/gepa/.venv` (`gepa==0.1.1`, Python 3.12)
- local-model helper: `~/.claude/skills/gepa/local_lm.py` — wires GEPA to llama-server on :8002
- Run with: `~/.claude/skills/gepa/.venv/bin/python your_script.py`

`litellm` is **not** installed, so model-id *strings* like `"openai/gpt-4.1-mini"` won't work
offline. On this box, pass the **callables** from `local_lm.py` instead (see below). Only install
litellm + set a cloud key if you deliberately want a frontier model as the reflector.

## Prereq: local model up

```bash
startup llm/mtp           # coder Qwen3.x on :8002 (reflection LM)
curl -sf http://127.0.0.1:8002/v1/models >/dev/null && echo ok
```

The **reflection LM does the heavy lifting** — it needs room to think. `local_lm.py` already sets an
8192-token reflection budget (Qwen3.x is a thinking model; too small → empty content, see the
`thinking-token-budget` memory). Tune via `GEPA_REFLECT_MAX_TOKENS`.

## API surface (gepa 0.1.1, verified)

```python
gepa.optimize(
    seed_candidate: dict[str, str],          # named text components to evolve, e.g. {"system_prompt": "..."}
    trainset: list, valset: list | None = None,
    adapter: GEPAAdapter | None = None,      # None -> DefaultAdapter (system-prompt optimization)
    task_lm: str | Callable | None = None,   # model that RUNS the task
    reflection_lm: str | Callable | None = None,  # model that DIAGNOSES + mutates (quality-critical)
    candidate_selection_strategy = "pareto", # | "current_best" | "epsilon_greedy" | "top_k_pareto"
    max_metric_calls: int | None = None,     # rollout budget (main stop condition)
    reflection_minibatch_size: int | None = None,
    use_merge: bool = False,                 # crossover of Pareto candidates
    display_progress_bar: bool = False,
    seed: int = 0,
    ...
) -> GEPAResult   # .best_candidate, .best_outputs, frontier, history
```

Three usage tiers:

1. **`gepa.optimize(...)` + DefaultAdapter** — evolve named prompt strings; you supply a metric.
2. **`gepa.optimize_anything(...)`** — evolve a single arbitrary artifact behind an `evaluate(candidate)->float`.
3. **Custom `GEPAAdapter`** — full control. Implement `evaluate`, `make_reflective_dataset`, `propose_new_texts`.

### GEPAAdapter interface

```python
class GEPAAdapter:
    def evaluate(self, batch, candidate, capture_traces=False) -> EvaluationBatch: ...
    def make_reflective_dataset(self, candidate, eval_batch, components_to_update) -> dict: ...
    def propose_new_texts(self, candidate, reflective_dataset, components_to_update) -> dict: ...  # optional
```
`evaluate` returns scores (+ traces when asked); `make_reflective_dataset` turns traces into the
diagnostic text the reflection LM reads. **The richer the trace, the better the mutations.**

## Minimal local example (optimize_anything)

```python
# ~/.claude/skills/gepa/.venv/bin/python this.py   (needs :8002 up)
import sys; sys.path.insert(0, "/home/fabian/.claude/skills/gepa")
from gepa.optimize_anything import optimize_anything, GEPAConfig, EngineConfig
from local_lm import local_reflection_lm

def evaluate(candidate: str) -> float:
    # run_my_system(candidate) ... return a score in [0,1]
    return float("urgent" in candidate.lower())   # toy objective

result = optimize_anything(
    seed_candidate="Summarize the ticket.",
    evaluator=evaluate,
    objective="Make the prompt flag urgent tickets.",
    reflection_lm=local_reflection_lm,
    config=GEPAConfig(engine=EngineConfig(max_metric_calls=20)),
)
print(result.best_candidate)
```

## Prompt-optimization example (gepa.optimize + DefaultAdapter)

```python
import sys; sys.path.insert(0, "/home/fabian/.claude/skills/gepa")
import gepa
from local_lm import local_reflection_lm, local_chat_lm

# trainset/valset: list of dicts the DefaultAdapter understands
#   {"input": "...", "answer": "..."} plus a metric you wire via a custom adapter,
#   OR use a built-in adapter (gepa.adapters). For arbitrary scoring prefer optimize_anything.
result = gepa.optimize(
    seed_candidate={"system_prompt": "You are a classifier. Answer yes or no."},
    trainset=trainset, valset=valset,
    task_lm=local_chat_lm,
    reflection_lm=local_reflection_lm,
    max_metric_calls=150,
    candidate_selection_strategy="pareto",
    display_progress_bar=True,
)
print(result.best_candidate["system_prompt"])
```

## DSPy integration (optimize a whole program)

```python
import dspy
optimizer = dspy.GEPA(metric=my_metric, max_metric_calls=150, reflection_lm="openai/gpt-5")
compiled = optimizer.compile(student=MyProgram(), trainset=trainset, valset=valset)
```
Requires `dspy` + a litellm-resolvable reflection model. For local DSPy, configure
`dspy.LM("openai/local", api_base="http://127.0.0.1:8002/v1", api_key="x")`.

## Using a cloud reflector instead of local (optional)

```bash
~/.claude/skills/gepa/.venv/bin/pip install litellm
export OPENAI_API_KEY=...   # then pass reflection_lm="openai/gpt-5", task_lm="openai/gpt-4.1-mini"
```

## GraphFusion fit (candidate targets)

Good things in this repo to point GEPA at — all have a natural eval metric:
- `graphfusion-npu` relation-extraction prompts (vs a labeled triple set)
- the `ai-code-review` gate prompt in `.gitea/workflows/code-review.yml`
- `graphfusion-dsl` / workflow prompts
- `graphfusion-eval` already provides non-LLM retrieval-quality scores → ready-made evaluators

## Gotchas

- **Empty mutations / blank reflections** → reflection budget too small. Bump `GEPA_REFLECT_MAX_TOKENS`. Don't disable thinking.
- **String model-ids error** → litellm not installed; use `local_lm` callables (default on this box).
- `seed_candidate` for `gepa.optimize` is a **dict of named components**, not a bare string (that's `optimize_anything`).
- `max_metric_calls` is the real budget knob — it bounds total task executions, not iterations.
- Keep `task_lm` temperature low (0) for stable scoring; `reflection_lm` higher (1.0) for diverse mutations — `local_lm.py` does this.

## Related on this machine

- `gepa-ai/gepa` upstream: https://github.com/gepa-ai/gepa
- Adjacent self-improving systems (NOT gepa): `safla-neural`/`sona-learning-optimizer` agents, `graphfusion-learn` (RL query-opt), fab-swarm SAFLA loop. See conversation notes for the broader landscape (SIA, Darwin Gödel Machine, Hermes).
