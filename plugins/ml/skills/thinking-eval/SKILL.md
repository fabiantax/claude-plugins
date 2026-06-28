---
name: thinking-eval
description: Evaluating Qwen3.5 thinking mode (on vs off) on speed, quality, and perplexity. Covers when thinking helps, when it wastes tokens, how to measure both, and which benchmark tasks benefit from reasoning. Use when comparing thinking vs non-thinking inference.
allowed-tools: Read Bash Write
---

# Thinking Mode Evaluation — Qwen3.5 on Strix Halo

**Models with thinking:** Qwen3.5-4B (llama-server :8001), Qwen3-Coder-Next (vLLM :8000)  
**Toggle:** `/no_think` suffix in user message disables thinking; default = thinking enabled

---

## What thinking mode does

Qwen3.5 (and Qwen3) models support a "thinking" mode that generates internal `<think>...</think>` reasoning before the visible answer. This is similar to DeepSeek-R1 or o1-style chain-of-thought.

**Cost:** extra tokens (measured in completion_tokens, billed the same)  
**Benefit:** better reasoning on hard tasks  
**Key finding from SOTA papers:** no model optimally balances over/underthinking — thinking wastes tokens on simple tasks ([S1-Bench, 2504.10368](https://hf.co/papers/2504.10368))

---

## Toggle thinking in API calls

```python
from openai import OpenAI

client = OpenAI(api_key="dummy", base_url="http://127.0.0.1:8001/v1")

# Thinking OFF — fast, for simple/retrieval tasks
def ask_fast(prompt: str, **kwargs):
    return client.chat.completions.create(
        model="Qwen3.5-4B-Q4_K_M.gguf",
        messages=[{"role": "user", "content": prompt + " /no_think"}],
        max_tokens=1024,
        temperature=0.1,
        **kwargs,
    )

# Thinking ON — slower, for complex reasoning/coding
def ask_thinking(prompt: str, **kwargs):
    return client.chat.completions.create(
        model="Qwen3.5-4B-Q4_K_M.gguf",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,          # needs more room for <think> block
        temperature=0.6,          # Qwen3 recommends higher temp with thinking
        **kwargs,
    )
```

---

## Recommended settings per task type

| Task | Thinking | Temp | Why |
|------|----------|------|-----|
| Simple retrieval (NIAH) | OFF | 0.0 | No reasoning needed, literal lookup |
| Code completion (autocomplete) | OFF | 0.1 | Speed matters, context is enough |
| Bug fix / debugging | ON | 0.6 | Needs multi-step reasoning |
| Architecture / design question | ON | 0.7 | Benefits from exploration |
| Math / algorithm | ON | 0.6 | Explicit reasoning steps help |
| Summarization | OFF | 0.3 | No reasoning needed |
| Test generation | ON | 0.4 | Edge case reasoning matters |
| Blazor component from spec | ON | 0.5 | Spec → implementation reasoning |

---

## Measure thinking overhead

```python
# ~/evals/thinking-compare.py
import time, json
from openai import OpenAI

client = OpenAI(api_key="dummy", base_url="http://127.0.0.1:8001/v1")
MODEL = "Qwen3.5-4B-Q4_K_M.gguf"

TASKS = [
    # (label, prompt, expected_benefit_of_thinking)
    ("simple_retrieval", "What is 2+2?", "none"),
    ("code_completion", "Complete this C# method: public bool IsAdmin(User u) {", "low"),
    ("bug_fix", "Fix this Blazor component: it throws NullReferenceException when Items is null.\n```razor\n@foreach(var item in Items) { <div>@item.Name</div> }\n@code { [Parameter] public List<Item> Items { get; set; } }\n```", "high"),
    ("architecture", "Design a clean architecture for a Blazor Server admin panel with role-based access and an audit log.", "high"),
    ("niah_retrieval", "The secret code is ZEPHYR-9421. " + ("The fox jumps over the lazy dog. " * 500) + "\n\nWhat is the secret code?", "none"),
]

results = []
for label, prompt, expected in TASKS:
    for mode in ["thinking", "no_think"]:
        suffix = "" if mode == "thinking" else " /no_think"
        max_tokens = 2048 if mode == "thinking" else 1024
        temp = 0.6 if mode == "thinking" else 0.1

        start = time.time()
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt + suffix}],
            max_tokens=max_tokens,
            temperature=temp,
        )
        elapsed = time.time() - start

        content = resp.choices[0].message.content
        think_tokens = content.count("<think>")  # rough proxy
        out_tokens = resp.usage.completion_tokens
        tg_s = out_tokens / elapsed

        results.append({
            "task": label,
            "mode": mode,
            "expected_benefit": expected,
            "total_tokens": out_tokens,
            "time_s": round(elapsed, 2),
            "tg_s": round(tg_s, 1),
            "has_think_block": "<think>" in content,
            "response_preview": content[:200],
        })
        print(f"  {label:20s} {mode:12s}  {out_tokens:5d} tok  {elapsed:.1f}s  {tg_s:.1f} tg/s")

with open("/home/fabian/evals/results/thinking-compare.json", "w") as f:
    json.dump(results, f, indent=2)

# Print summary
print("\n=== Summary ===")
for task in set(r["task"] for r in results):
    t = next(r for r in results if r["task"] == task and r["mode"] == "thinking")
    n = next(r for r in results if r["task"] == task and r["mode"] == "no_think")
    print(f"{task:20s}  thinking: {t['total_tokens']:5d}tok {t['tg_s']:.1f}tg/s  |  no_think: {n['total_tokens']:5d}tok {n['tg_s']:.1f}tg/s  |  expected: {t['expected_benefit']}")
```

Run:
```bash
python ~/evals/thinking-compare.py
```

---

## NIAH with thinking — heatmap comparison

Run NIAH twice (thinking on vs off) and compare heatmaps:

```python
# Key config changes for thinking-aware NIAH:

# Run 1: thinking OFF (fast)
tester_fast = LLMNeedleHaystackTester(
    ...
    needle_postfix=" /no_think",   # append to needle question
    results_version=1,             # "nothink"
)

# Run 2: thinking ON (slow but thorough)
tester_think = LLMNeedleHaystackTester(
    ...
    needle_postfix="",             # default = thinking on
    results_version=2,             # "think"
    generate_kwargs={"temperature": 0.6, "max_tokens": 2048},
)
```

Expected pattern:
- Short context (< 16k): no difference — thinking wastes tokens
- Long context (> 64k): thinking may improve deep-position retrieval
- NoLiMa tasks: thinking helps significantly (reasoning required)

---

## Perplexity with/without thinking context

Thinking mode affects **generation** not **tokenization**, so perplexity measurement is the same for both modes. What you can do:

```bash
# Compare perplexity of model's own output (thinking vs no_think)
# Generate outputs from both modes, save to files, measure PPL on the outputs

# Generate ~1000 tokens with thinking
curl -s --ipv4 http://127.0.0.1:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Explain Blazor component lifecycle in detail."}],"max_tokens":1000}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])" \
  > /tmp/thinking-output.txt

# Generate same without thinking
curl -s --ipv4 http://127.0.0.1:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Explain Blazor component lifecycle in detail. /no_think"}],"max_tokens":1000}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])" \
  > /tmp/nothink-output.txt

# Measure perplexity of each output (lower = more confident/coherent)
toolbox run -c strix-llama ~/code/tools/llama.cpp/build/bin/llama-perplexity \
  -m ~/models/unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf \
  --n-gpu-layers 999 -f /tmp/thinking-output.txt
```

---

## Key metrics to track

| Metric | Command | Thinking ON | Thinking OFF |
|--------|---------|------------|--------------|
| TG/s | timings.predicted_per_second | ~same raw speed | ~same raw speed |
| Tokens used | usage.completion_tokens | higher (think block) | lower |
| Latency to first token | timings.prompt_ms | higher | lower |
| Task accuracy | manual / pass@1 | better on hard tasks | worse on hard tasks |
| Token efficiency | quality/tokens | lower on easy tasks | better on easy tasks |

---

## SOTA context

From the papers:
- **S1-Bench** ([2504.10368](https://hf.co/papers/2504.10368)) — reasoning models waste tokens on simple tasks, System 1 thinking (fast/direct) is optimal for retrieval
- **OptimalThinkingBench** ([2508.13141](https://hf.co/papers/2508.13141)) — no model optimally balances over/underthinking across task types
- **THINK-Bench** ([2505.22113](https://hf.co/papers/2505.22113)) — defines reasoning efficiency = (quality gain) / (extra tokens) — measure this for your tasks
- **StyleBench** ([2509.20868](https://hf.co/papers/2509.20868)) — strategy efficacy depends on model scale AND task type

**Practical rule:** Use thinking for tasks where you'd write pseudocode or draft on paper first. Skip thinking for tasks where you'd answer immediately.
