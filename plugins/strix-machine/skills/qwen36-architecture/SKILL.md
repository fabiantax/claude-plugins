---
name: qwen36-architecture
description: Qwen3.6 model architecture reference — Gated DeltaNet + MoE hybrid, MTP speculative decoding, Mamba SSM layers, and inference implications. Use when optimizing inference for Qwen3.x models on vLLM or llama.cpp.
allowed-tools: Read Bash WebSearch
---

# Qwen3.6 Architecture Reference

---

## Model Family

| Model | Architecture | Params | Active Params | Notes |
|-------|-------------|--------|---------------|-------|
| Qwen3.6-35B-A3B | Gated DeltaNet + MoE | 36B | 3B/token | 256 experts, 8 active |
| Qwen3.5-35B-A3B | MoE only | 36B | 3B/token | 256 experts, 8 active |
| Qwen3.5-27B | Dense | 27B | 27B | Full attention |
| Qwen3.5-4B | Dense | 4B | 4B | Full attention |

---

## Qwen3.6-35B-A3B Architecture

### Key Innovation: Gated DeltaNet

Qwen3.6 replaces the standard attention in 30 of 40 layers with **Gated DeltaNet** (a linear/recurrent attention mechanism). The remaining 10 layers use full self-attention.

```
Layer 0-29:  Gated DeltaNet (linear attention + Mamba SSM state)
Layer 30-39: Full self-attention (standard multi-head attention)
```

This makes it a **Mamba-hybrid** model — similar to Jamba and Zamba architectures.

### Model Config

```json
{
  "model_type": "qwen3_5_moe",
  "hidden_size": 2048,
  "intermediate_size": 768,
  "num_hidden_layers": 40,
  "num_attention_heads": 32,
  "num_key_value_heads": 4,
  "num_experts": 256,
  "num_experts_per_tok": 8,
  "mtp_num_hidden_layers": 1,
  "max_position_embeddings": 262144,
  "vocab_size": 151936,
  "rope_theta": 10000.0
}
```

### Gated DeltaNet Layers (0-29)

- **Linear attention**: O(n) complexity instead of O(n²)
- **Mamba SSM state**: Recurrent state that carries information across positions
- **No KV cache** in the traditional sense — uses SSM state instead
- **Implication**: `--mamba-ssm-cache-dtype float16` is critical for KV cache sizing

### Full Attention Layers (30-39)

- Standard multi-head attention with KV cache
- GQA: 32 query heads, 4 KV heads (8:1 ratio)
- These layers benefit from standard KV cache optimizations (fp8, prefix caching)

### MoE (all layers)

- **256 experts**, **8 active per token** (3.1% sparsity)
- Expert routing via learned gate
- Each expert is a small MLP (intermediate_size=768)
- Fused via Triton `fused_moe` kernel on ROCm

---

## MTP (Multi-Token Prediction)

Qwen3.6 has native MTP support via `mtp_num_hidden_layers: 1`:

```
Main model head: predicts token T+1
MTP head:        predicts token T+2, T+3, T+4
```

### vLLM Configuration

```json
--speculative-config '{"method":"mtp","num_speculative_tokens":3}'
```

- The MTP head runs sequentially 3 times (not in parallel)
- Each run predicts the next token
- Target model verifies all draft tokens in one forward pass
- Acceptance rate depends on KV cache availability

### Acceptance Rates (Strix Halo, fp16 SSM)

| Position | Acceptance |
|----------|-----------|
| 1 | ~91.5% |
| 2 | ~79.7% |
| 3 | ~79.6% |
| Overall | ~71.4% |

---

## Thinking Mode

Qwen3.6 has a dual-mode architecture:

- **Thinking mode**: Emits `<think...<think` blocks with reasoning before answering
- **Non-thinking mode**: Direct response without reasoning

### Suppressing Thinking (CRITICAL)

`extra_body.enable_thinking=false` does NOT work. Use:

```json
{
  "chat_template_kwargs": {"enable_thinking": false}
}
```

as a top-level parameter in the chat completions request.

### Impact on Benchmarks

Without proper thinking suppression, thinking tokens are counted as output tokens, inflating throughput numbers by 2-3×. **All benchmarks must use `chat_template_kwargs.enable_thinking:false` for Qwen3.x models.**

---

## Quantization Formats

| Format | Quant Method | Size | Backend | Notes |
|--------|-------------|------|---------|-------|
| AWQ 4-bit | compressed-tensors | ~14 GB | vLLM compressed-tensors | Actually INT4 group quantization, not standard AWQ |
| FP8 | fp8 | ~36 GB | vLLM fp8 | Official Qwen release |
| GGUF Q4_K_M | gguf | ~14 GB | llama.cpp | Good for small context |
| GGUF Q8_0 | gguf | ~28 GB | llama.cpp | Higher quality |

---

## vLLM Flags (Optimized for Strix Halo)

```bash
--dtype float16                    # Model compute dtype
--max-model-len 32768              # Context window
--max-num-seqs 32                  # Concurrent sequences
--max-num-batched-tokens 16384     # Token budget per iteration
--gpu-memory-utilization 0.90      # VRAM fraction
--kv-cache-dtype fp8               # FP8 KV cache
--mamba-ssm-cache-dtype float16    # FP16 SSM state (CRITICAL)
--enable-chunked-prefill           # Interleave prefill/decode
--enable-prefix-caching            # Share system prompt KV
--enforce-eager                    # No CUDA graphs (ROCm)
--speculative-config '{"method":"mtp","num_speculative_tokens":3}'
```

### What Does NOT Work

| Flag/Method | Error/Reason |
|-------------|-------------|
| `--attention-backend ROCM_AITER_FA` | `fmha_fwd invalid argument` on DeltaNet layers |
| `--flash-attn` | Not compatible with hybrid Mamba architecture |
| `--mamba-cache-mode all` | Falls back to "align" for hybrid models |
| `ngram_gpu` speculative | Worse throughput than MTP |
| `DFlash` speculative | Only supports dense models |

---

## Papers

- **Qwen3 Technical Report** (2025): https://hf.co/papers/2505.09388
  - 0.6B to 235B parameter family, thinking + non-thinking unified, 119 languages
- **Qwen3-VL** (2025): https://hf.co/papers/2511.21631
  - Vision-language variant with 256K interleaved context

---

## Performance on Strix Halo (INT4 AWQ + MTP spec=3)

| Conc | tg/s | Notes |
|------|------|-------|
| 1 | ~31 | Single request |
| 2 | ~34 | |
| 4 | ~62 | Sweet spot for agent workloads |
| 8 | ~91 | Near GPU bandwidth limit |
