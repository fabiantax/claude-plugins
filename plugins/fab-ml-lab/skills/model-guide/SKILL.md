---
name: model-guide
description: Guide for selecting LLM models compatible with the Strix ROCm inference server. Use when asked about model selection, quantization formats, MoE techniques, or which models to download for ROCm/vLLM/llama.cpp.
allowed-tools: Read
---

# Model Selection Guide for Strix Halo (ROCm / gfx1151)

**Hardware:** AMD Ryzen AI MAX+ Pro 395 (Strix Halo), Radeon 8060S iGPU (gfx1151), 128 GB unified LPDDR5X; ~96 GiB GPU-allocatable via GTT (512 MiB fixed VRAM carveout + dynamic GTT), ROCm 7.2.1

**Inference stack:**
- vLLM on :8000 — primary, concurrent batching, agents
- llama.cpp on :8001 — GGUF, single-stream, patchable
- Lemonade on :8080 — NPU+iGPU, multi-modal, long context

---

## ROCm Compatibility — Quantization Formats

### For vLLM (use these):
| Format | ROCm | Notes |
|--------|------|-------|
| **AWQ** | ✅ Best | Hardware-accelerated, best throughput |
| **GPTQ** | ✅ Good | Supported, slightly slower than AWQ |
| **FP8** | ✅ Good | ROCm 6+ native, good quality/speed |
| **compressed-tensors** | ✅ Good | cyankiwi's format, vLLM supports natively |
| EXL2 | ❌ No | CUDA-only kernels |
| BitsAndBytes | ❌ No | CUDA-only |
| Marlin / AQLM | ❌ No | CUDA-only |

### For llama.cpp (use these):
| Format | ROCm | Notes |
|--------|------|-------|
| **GGUF Q4_K_M** | ✅ Best | Sweet spot quality/speed |
| **GGUF Q5_K_M** | ✅ Good | Better quality, ~20% larger |
| **GGUF Q8_0** | ✅ Good | Near-lossless, fits in ~96 GiB GPU-allocatable (GTT, of 128 GB unified) |

---

## "Optimizer" Names — What They Actually Mean

| Name | What it is | ROCm? |
|------|-----------|-------|
| **AWQ** | Quantization format (4-bit weights) | ✅ Use for vLLM |
| **GPTQ** | Quantization format (4-bit weights) | ✅ Use for vLLM |
| **Unsloth** | Tool that produces standard GGUF — not a format | ✅ Output is plain GGUF |
| **APEX** | NVIDIA CUDA training library | ❌ Inference-irrelevant, CUDA-only |
| **Flash Attention** | Attention kernel optimization | ✅ Built into kyuz0 vLLM |
| **compressed-tensors** | Serialization format used by vLLM/llm-compressor | ✅ |
| **imatrix** | Importance-matrix calibrated GGUF quantization | ✅ Better Q4 quality |

---

## MoE Techniques — Expert Merging/Pruning

MoE models activate only a fraction of parameters per token — high quality at low compute cost.

| Technique | What it does | Quality impact |
|-----------|-------------|---------------|
| **REAM** (Router Expert Adaptive Merging) | Merges similar experts | Minimal loss, smaller model |
| **REAP** (Router Expert Adaptive Pruning) | Removes least-used experts | Small loss, smaller + faster |
| **SVD** | Decomposes weight matrices | Moderate loss |
| **imatrix** | Calibrated quantization | Lower quant error than standard Q4 |

**Rule:** Base AWQ > REAM AWQ > REAP AWQ in quality. For production agents, prefer base AWQ.

---

## Source Selection Rules

When multiple quantizers offer the same model, apply in order:

1. **ROCm ecosystem first** — prefer sources known to test on ROCm/gfx1151. High CUDA download counts don't validate ROCm compatibility.
2. **Active maintenance beats download count** — a source that updated post-release (recalibration, bug fix) is more reliable than one frozen at launch day.
3. **compressed-tensors > standard AWQ for vLLM** — vLLM loads compressed-tensors natively; standard AWQ requires a conversion pass on first load.
4. **Calibration dataset matters for Q4** — domain-specific calibration (code, agent tasks) produces better Q4 quality than generic. Check the model card.
5. **Official quantizer = safest for new models** — the model team's own GPTQ/AWQ is day-of-release and uses the correct tokenizer config.
6. **GGUF: imatrix > standard** — imatrix-calibrated GGUF has measurably lower quantization error at Q4.

## Trusted Sources

| Source | Format | Notes |
|--------|--------|-------|
| **cyankiwi** | AWQ (compressed-tensors) | ROCm-first (kyuz0 ecosystem). Wins on Rule 1. Both cyankiwi and bullpoint use compressed-tensors — format is no longer a differentiator. |
| **bullpoint** | AWQ (compressed-tensors) | Also uses compressed-tensors. Good download count, good tags. CUDA-first ecosystem — ROCm fixes lag behind cyankiwi. |
| **Qwen/** (official) | GPTQ | Day-of-release, correct tokenizer, always available. No imatrix calibration. |
| **unsloth** | GGUF | imatrix-calibrated. Hosts own repo directly (e.g. unsloth/Qwen3-Coder-Next-GGUF). Highest downloads. Primary GGUF source. |
| **bartowski** | GGUF | imatrix-calibrated. Good secondary GGUF source. |
| **mradermacher** | GGUF | Wide coverage, often imatrix (check tags). Good for obscure models unsloth doesn't cover. |

---

## Model Recommendations (~96 GiB GPU-allocatable, of 128 GB unified)

### Qwen3.5 (released Feb/Mar 2026) — MoE family
| Model | Downloads | Size | Notes |
|-------|-----------|------|-------|
| [cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit](https://hf.co/cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit) | 454K | 35B/3B active | ⭐ Best Qwen3.5 — MoE, fastest |
| [Qwen/Qwen3.5-35B-A3B-GPTQ-Int4](https://hf.co/Qwen/Qwen3.5-35B-A3B-GPTQ-Int4) | 694K | 35B/3B active | Official GPTQ from Qwen team |
| [cyankiwi/Qwen3.5-27B-AWQ-4bit](https://hf.co/cyankiwi/Qwen3.5-27B-AWQ-4bit) | 168K | 27B dense | Good quality, larger |
| [cyankiwi/Qwen3.5-122B-A10B-AWQ-4bit](https://hf.co/cyankiwi/Qwen3.5-122B-A10B-AWQ-4bit) | 103K | 122B/10B active | Massive MoE, fits in ~96 GiB GPU-allocatable AWQ |

### Qwen3-Coder / Coding Agents (vLLM :8000)
| Model | Downloads | Size | Notes |
|-------|-----------|------|-------|
| [cyankiwi/Qwen3-Coder-Next-AWQ-4bit](https://hf.co/cyankiwi/Qwen3-Coder-Next-AWQ-4bit) | 170K | MoE | ⭐ Agent workloads, SWE-Bench 70%+ |
| [cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit](https://hf.co/cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit) | 83K | 30B/3B | Coding, stable |
| [cyankiwi/Qwen3-Next-80B-A3B-Instruct-AWQ-4bit](https://hf.co/cyankiwi/Qwen3-Next-80B-A3B-Instruct-AWQ-4bit) | 12K | 80B/3B active | ⭐ 80B quality at 3B speed |

### Vision / Multimodal
| Model | Downloads | Notes |
|-------|-----------|-------|
| [cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit](https://hf.co/cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit) | 311K | MoE, image+text |
| [cyankiwi/Qwen3-VL-32B-Instruct-AWQ-4bit](https://hf.co/cyankiwi/Qwen3-VL-32B-Instruct-AWQ-4bit) | 16K | Vision+language |

### GGUF / llama.cpp (:8001)
| Model | Notes |
|-------|-------|
| [unsloth/Qwen3-Coder-Next-GGUF](https://hf.co/unsloth/Qwen3-Coder-Next-GGUF) | imatrix, 202K downloads — pick Q4_K_M variant |

---

## Quick Commands

```bash
# Download a model
hf download <repo-id> --local-dir ~/models/<name>

# Switch vLLM model
echo "cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit" > ~/.config/vllm/current-model
systemctl --user restart vllm

# Check what's running
ai-status
```
