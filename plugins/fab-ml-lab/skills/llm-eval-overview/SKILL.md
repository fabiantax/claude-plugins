---
name: llm-eval-overview
description: Master reference for LLM evaluation on Strix Halo. Covers benchmark landscape, SOTA papers, when to use each benchmark, and how to extend with real-world code. Use when planning evaluations or comparing models.
allowed-tools: Read Bash
---

# LLM Evaluation Overview — Strix Halo

**Inference stack:** llama-server :8001 (GGUF), vLLM :8000 (AWQ)  
**Models available:** Qwen3.5-4B Q4_K_M, Gemma 4 E4B Q4_K_M (llama.cpp), Qwen3-Coder-Next AWQ, Qwen3.5-35B-A3B AWQ (vLLM)

---

## Benchmark Tiers

### Fast (minutes, run today)
| Benchmark | Skill | Measures | Custom code? |
|-----------|-------|----------|--------------|
| `llama-perplexity` | `/llm-eval-overview` | Quantization quality vs your corpus | ✅ trivial |
| Classic NIAH | `/niah-bench` | Context retrieval at depth × size | ✅ easy |
| tg/s scaling | `~/ctx-bench.sh` | PP + TG speed vs context size | — |

### Medium (hours, needs setup)
| Benchmark | Skill | Measures | Custom code? |
|-----------|-------|----------|--------------|
| NoLiMa NIAH | `/niah-bench` | Reasoning-based retrieval (no literal match) | ✅ medium |
| lm-eval-harness | `/code-bench` | HumanEval, MMLU, GSM8K | ✅ YAML tasks |
| MultiPL-E | `/code-bench` | Code gen in Rust, TypeScript, C# | ✅ JSONL |
| Thinking-mode eval | `/thinking-eval` | Quality + speed with/without reasoning | ✅ easy |

### Ambitious (days, agent loop needed)
| Benchmark | Skill | Measures | Custom code? |
|-----------|-------|----------|--------------|
| Multi-SWE-bench mini | `/code-bench` | Real issue resolution: Rust, TS, JS, Go | ✅ hard |
| SWE-Sharp-Bench | `/code-bench` | C# issue resolution (Microsoft Research) | ✅ hard |
| Personal SWE-bench | `/code-bench` | Your own bugs → gold patches | ✅ the point |
| CRUST-Bench style | `/code-bench` | C → safe Rust transpilation | ✅ medium |

---

## SOTA Papers (2025–2026)

### Coding agents / SWE-bench
- **SWE-Master** (Feb 2026) — RL + test-time scaling, best open framework — [2602.03411](https://hf.co/papers/2602.03411)
- **Skywork-SWE** (Jun 2025) — data scaling laws for SWE agents — [2506.19290](https://hf.co/papers/2506.19290)
- **Multi-SWE-bench** (Apr 2025) — multilingual: Java, TS, JS, Go, Rust, C, C++ — [2504.02605](https://hf.co/papers/2504.02605)
- **SWE-Sharp-Bench** (Nov 2025, MS Research) — C# only — [2511.02352](https://hf.co/papers/2511.02352)
- **OmniCode** (Feb 2026) — bug fix + test gen + code review, multi-lang — [2602.02262](https://hf.co/papers/2602.02262)
- **CRUST-Bench** (Apr 2025) — C → safe Rust transpilation — [2504.15254](https://hf.co/papers/2504.15254)
- **SWE-bench Live** (May 2025) — continuously updated from live GitHub issues — [2505.23419](https://hf.co/papers/2505.23419)

### Long context / NIAH
- **NoLiMa** (Feb 2025) — no literal match, requires reasoning — [2502.05167](https://hf.co/papers/2502.05167)
- **NeedleChain** (Jul 2025) — multi-hop needle, proposes RoPE Contraction — [2507.22411](https://hf.co/papers/2507.22411)
- **LongGenBench** (Oct 2024) — generation quality at scale, not just retrieval — [2410.04199](https://hf.co/papers/2410.04199)

### Thinking / reasoning efficiency
- **OptimalThinkingBench** (Aug 2025) — no model optimally balances over/underthinking — [2508.13141](https://hf.co/papers/2508.13141)
- **S1-Bench** (Apr 2025) — System 1 tasks don't benefit from thinking mode — [2504.10368](https://hf.co/papers/2504.10368)
- **THINK-Bench** (May 2025) — reasoning efficiency metrics — [2505.22113](https://hf.co/papers/2505.22113)
- **StyleBench** (Sep 2025) — CoT vs ToT vs AoT vs SoT across model families — [2509.20868](https://hf.co/papers/2509.20868)

### Quantization quality
- **Comprehensive quant eval up to 405B** (Sep 2024) — quantized larger > smaller fp16 — [2409.11055](https://hf.co/papers/2409.11055)

---

## Running perplexity on your own codebase

```bash
# Build corpus from any source tree
find ~/myproject -name "*.cs" -o -name "*.razor" | sort | xargs cat > /tmp/corpus.txt

# Run perplexity — lower is better
toolbox run -c strix-llama \
  ~/code/tools/llama.cpp/build/bin/llama-perplexity \
  -m ~/models/unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf \
  --n-gpu-layers 999 \
  -f /tmp/corpus.txt \
  --ctx-size 2048 \
  --ppl-stride 512

# Compare models or quantizations:
# Q3_K_M vs Q4_K_M vs Q5_K_M on YOUR code
# Lower perplexity = model understands your codebase better
```

---

## Extending benchmarks with real daily work

**Best candidates for customization (ranked by effort):**

1. **Perplexity corpus** — just cat your source files (zero effort)
2. **NIAH haystack** — replace filler with your actual codebase files (~1hr)
3. **lm-eval YAML tasks** — define custom coding tasks in YAML + JSONL (~half day)
4. **MultiPL-E JSONL** — add your own function-level tasks with unit tests (~1 day)
5. **Personal SWE-bench** — extract real bugs from PRs as benchmark instances (~several days)

**Personal SWE-bench instance format:**
```jsonl
{
  "instance_id": "myapp-blazor-001",
  "repo": "mycompany/admin-panel",
  "problem_statement": "DataTable throws NullReferenceException when Items is null",
  "patch": "--- a/Components/DataTable.razor\n+++ b/...",
  "test_patch": "// unit test verifying the fix",
  "language": "csharp",
  "difficulty": "easy"
}
```

---

## Key insight: quantized larger > smaller fp16

For your stack, running Q4_K_M on a 35B-A3B MoE gives **better quality AND faster tg/s** than fp16 on a 4B dense model. The bandwidth math:
- Qwen3.5-4B dense Q4_K_M: 56 tg/s, 2.6GB active weights
- Qwen3.5-35B-A3B MoE Q4_K_M: ~85 tg/s, ~1.7GB active weights (3B active params)
- MoE wins on speed AND quality

---

## Scripts on this machine

| Script | What |
|--------|------|
| `~/ctx-bench.sh <model> [max_ctx_k]` | PP + TG toks/s at 10k→Nk context steps |
| `~/blazor-convo.sh` | 5-turn conversational Blazor build, measures tg/s per turn |
| `~/blazor-bench.sh` | Sequential + batched + coding agents (2 coders + 1 reviewer) |
