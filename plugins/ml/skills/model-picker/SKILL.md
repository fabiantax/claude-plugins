---
name: model-picker
description: Interactive model selection for Strix ROCm inference server. Searches HuggingFace trending/downloads and walks through a decision diagram to recommend the best model for the use case. Use when the user wants to find, compare, or choose a model to download.
allowed-tools: Read mcp__claude_ai_Hugging_Face__hub_repo_search mcp__claude_ai_Hugging_Face__hub_repo_details
---

You are helping select the best LLM model for the Strix inference server.

**Hardware constraints:**
- GPU: gfx1151 (ROCm 7.2.1) — 128 GB unified LPDDR5X, ~96 GiB GPU-allocatable via GTT
- Backends: vLLM (AWQ/GPTQ), llama.cpp (GGUF)
- Rule: AWQ for vLLM, GGUF Q4_K_M for llama.cpp. No EXL2, no BitsAndBytes, no Marlin.

---

## Step 1 — Walk the decision diagram

Ask the user (or infer from context) which branch applies:

```
What do I need the model for?
│
├── CODING / AGENTS
│   ├── Concurrent (multiple agents at once)?
│   │   └── → vLLM + AWQ  [go to Step 2, filter: coding AWQ]
│   └── Single stream, GGUF preferred?
│       └── → llama.cpp + GGUF Q4_K_M  [go to Step 2, filter: coding GGUF]
│
├── REASONING / GENERAL
│   ├── Need maximum quality?
│   │   └── → Large MoE AWQ (80B-122B A3B/A10B)  [go to Step 2]
│   └── Balanced quality/speed?
│       └── → Mid MoE AWQ (30-35B A3B)  [go to Step 2]
│
├── VISION / MULTIMODAL
│   ├── Image understanding?
│   │   └── → Gemma 4 or Qwen3-VL AWQ  [go to Step 2]
│   └── Audio / speech?
│       └── → Lemonade backend (NPU), Qwen3-Omni  [go to Step 2]
│
└── FAST / SMALL (edge, low latency)
    ├── <5GB VRAM budget?
    │   └── → Qwen3.5-4B or 9B AWQ  [go to Step 2]
    └── NPU offload?
        └── → Lemonade backend handles routing automatically
```

---

## Step 2 — Search HuggingFace for current best options

Search using `mcp__claude_ai_Hugging_Face__hub_repo_search` with appropriate query.

**Source selection rules (apply in order when multiple quantizers offer the same model):**

1. **ROCm ecosystem first** — prefer sources known to test on ROCm/gfx1151. High CUDA download counts don't validate ROCm compatibility.
2. **Active maintenance beats download count** — a source that updated the model after release (recalibration, bug fixes) is more reliable than one frozen at launch day.
3. **compressed-tensors > standard AWQ for vLLM** — vLLM loads compressed-tensors natively; standard AWQ requires a conversion pass on first load.
4. **Calibration dataset matters for Q4** — sources that use a domain-specific calibration dataset (e.g. code, instruction-following, agent tasks) produce better Q4 quality than generic calibration. Check the model card.
5. **Official quantizer = safest for new models** — the model team's own GPTQ/AWQ release is always available day-of and uses the correct tokenizer config.
6. **GGUF: imatrix calibration > standard** — imatrix-calibrated GGUF has measurably lower quantization error at Q4. Look for "imatrix" in the model name or card.

**Trusted sources (as of Apr 2026):**

| Rank | Source | Format | Notes |
|------|--------|--------|-------|
| ⭐⭐⭐ | **cyankiwi** | AWQ (compressed-tensors) | ROCm-first (kyuz0 ecosystem). Both cyankiwi and bullpoint now use compressed-tensors — format is no longer a differentiator. Wins on Rule 1 alone. |
| ⭐⭐⭐ | **Qwen/** (official) | GPTQ | Day-of-release, correct tokenizer, always available |
| ⭐⭐⭐ | **unsloth** | GGUF | imatrix-calibrated, highest downloads (202K+). Hosts own repo directly. Primary GGUF pick. |
| ⭐⭐ | **bullpoint** | AWQ (compressed-tensors) | Also compressed-tensors. Good download count. CUDA-first — ROCm fixes lag behind cyankiwi. |
| ⭐⭐ | **bartowski** | GGUF | imatrix-calibrated. Good secondary GGUF source. |
| ⭐⭐ | **mradermacher** | GGUF | Wide model coverage, often imatrix. Good for obscure models. |
| ⭐ | **others** | varies | Verify download count >10K and check for imatrix tag before trusting |

**Download count signals:**
- >100K downloads → community-validated, safe to use
- 10K–100K → established, likely fine
- 1K–10K → newer or niche, check base model and tags carefully
- <1K → experimental, verify provenance

**Trending score signals:**
- Use `sort: trendingScore` to find what the community is currently using
- High trending + low downloads = newly released, watch for issues
- High trending + high downloads = strong signal, use this

---

## Step 3 — Apply ROCm compatibility filter

Before recommending, verify:
1. Format is AWQ, GPTQ, FP8, or compressed-tensors → ✅ vLLM
2. Format is GGUF (any quant) → ✅ llama.cpp
3. Format is EXL2, BitsAndBytes, Marlin, MLX → ❌ skip
4. "Unsloth" tag = just GGUF, ignore the branding

**MoE efficiency check** — if model name contains A3B, A4B, A10B, A17B:
- That's active parameters. 35B-A3B = 35B total, only 3B active per token
- TG/s will be similar to a dense 3B model — very fast
- Quality will be closer to the full 35B
- These are always preferred over equivalent dense models on this hardware

---

## Step 4 — Present recommendation

Show a ranked shortlist (max 3) with:
- Model name + HuggingFace link
- Download count + trending score
- Estimated VRAM usage (AWQ 4-bit ≈ model_params_B × 0.5 GB)
- Download command:
  ```bash
  hf download <repo-id> --local-dir ~/models/<short-name>
  ```
- Switch vLLM to use it:
  ```bash
  echo "<repo-id>" > ~/.config/vllm/current-model
  systemctl --user restart vllm
  ```

---

## Quick reference — known good models (as of Apr 2026)

| Use case | Model | Source | VRAM |
|----------|-------|--------|------|
| Coding agents (concurrent) | Qwen3-Coder-Next-AWQ-4bit | cyankiwi | ~18GB |
| Coding (stable) | Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | cyankiwi | ~15GB |
| General reasoning (fast) | Qwen3.5-35B-A3B-AWQ-4bit | cyankiwi | ~18GB |
| General reasoning (best) | Qwen3.5-122B-A10B-AWQ-4bit | cyankiwi | ~62GB |
| Maximum quality | Qwen3-Next-80B-A3B-Instruct-AWQ-4bit | cyankiwi | ~40GB |
| Vision + text | gemma-4-26B-A4B-it-AWQ-4bit | cyankiwi | ~14GB |
| Vision + text (alt) | Qwen3-VL-32B-Instruct-AWQ-4bit | cyankiwi | ~17GB |
| GGUF coding | Qwen3-Coder-Next-GGUF (Q4_K_M variant) | unsloth | ~18GB |
| Small/fast | Qwen3.5-9B-AWQ-4bit | cyankiwi | ~5GB |

Always search HuggingFace for newer releases before defaulting to this table.
