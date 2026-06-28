---
name: vllm-internals
description: vLLM inference engine internals — PagedAttention, scheduler, continuous batching, speculative decoding, and tuning for ROCm/RDNA GPUs. Use when optimizing vLLM performance, debugging scheduling issues, or tuning flags.
allowed-tools: Read Bash
---

# vLLM Internals & Tuning — ROCm (gfx1151)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│  API Server (FastAPI/Uvicorn)                            │
│  - /v1/chat/completions, /v1/completions, /health        │
│  - Authentication, request validation                     │
├──────────────────────────────────────────────────────────┤
│  Engine (AsyncLLM or LLM)                                │
│  - Request queue, response streaming                     │
│  - EngineCore communicates via IPC (V1 architecture)     │
├──────────────────────────────────────────────────────────┤
│  EngineCore                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Scheduler   │  │ KV Cache     │  │ Model Runner   │  │
│  │ (FIFO/      │  │ Manager      │  │ (GPU forward   │  │
│  │  Priority)  │  │ (PagedAttn)  │  │  passes)       │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                │                   │           │
│  ┌──────┴────────────────┴───────────────────┴────────┐  │
│  │              GPU Worker Process                     │  │
│  │  - Model weights in GPU VRAM                       │  │
│  │  - Paged KV cache blocks                           │  │
│  │  - Attention kernels (ROCm: Triton/ciGCN)          │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## Request Lifecycle

```
PENDING → PREFILLING → DECODING → FINISHED
              ↓             ↑
         (chunked       (+1 token
          prefill)       per step)
```

1. **PENDING**: Request queued, waiting for scheduler to admit
2. **PREFILLING**: Prompt tokens processed in forward pass(es)
3. **DECODING**: Output tokens generated one at a time
4. **FINISHED**: Generation complete, result returned

---

## PagedAttention

PagedAttention is inspired by OS virtual memory — KV cache is stored in non-contiguous blocks:

```
Block table: Request A → [block 2, block 5, block 7]
             Request B → [block 0, block 3]

Physical blocks:  [B₀] [·] [A₀] [B₁] [·] [A₁] [·] [A₂] [·] [·]
                  Used: A=3, B=2   Free: 5
```

### Key Parameters

| Parameter | Default | Our Setting | Notes |
|-----------|---------|-------------|-------|
| `block_size` | 16 | 16 | Tokens per KV block |
| `gpu_memory_utilization` | 0.9 | 0.9 | Fraction of VRAM for KV cache |
| `kv_cache_dtype` | auto | fp8 | FP8 halves KV cache memory |
| `enable_prefix_caching` | false | true | Content-hash blocks for shared prompts |
| `swap_space_bytes` | 4GB | 4GB | CPU swap space for preemption |

### KV Cache Sizing

With Qwen3.6-35B-A3B-AWQ-4bit at fp16 with fp8 KV cache:
- ~3600 KV blocks available
- Each block = 16 tokens × 40 layers × 2 (K+V) × fp8 = ~10 KB/block
- Total KV cache ≈ 3600 × 16 = 57,600 tokens capacity

---

## Scheduler (SchedulerConfig)

```python
max_num_batched_tokens: int    # Max tokens per iteration (our: 16384)
max_num_seqs: int              # Max concurrent sequences (our: 32)
max_num_partial_prefills: int  # Chunked prefill concurrency (default: 1)
enable_chunked_prefill: bool   # Split large prefills across steps (our: true)
```

### How Scheduling Works

1. **Priority**: Active decode requests > active prefill > new waiting requests (FIFO)
2. **Token budget**: Each iteration limited by `max_num_batched_tokens`
3. **Cache budget**: Each iteration limited by available KV blocks
4. **Admission**: New request admitted only if enough free blocks for all layers

### Tuning for Small-Batch Inference (4-8 agents)

| Flag | Recommended | Why |
|------|------------|-----|
| `--max-num-seqs 32` | 32 | Allows all agents to be in-flight simultaneously |
| `--max-num-batched-tokens 16384` | 16384 | Good balance; 32768 showed no improvement |
| `--enable-chunked-prefill` | true | Prevents long system prompts from blocking |
| `--enable-prefix-caching` | true | Agents share system prompt structure |

---

## Speculative Decoding

### MTP (Multi-Token Prediction) — Qwen3.6 native

Qwen3.6-35B-A3B has `mtp_num_hidden_layers: 1` — a single MTP head that predicts next tokens.

```json
--speculative-config '{"method":"mtp","num_speculative_tokens":3}'
```

**How it works:**
1. Target model generates 1 token normally
2. MTP head runs 3 times sequentially, predicting tokens 2-4
3. Target model verifies all 3 draft tokens in one forward pass
4. Accepted tokens are kept; rejected tokens trigger re-generation

**Acceptance rates (fp16 SSM cache):**
- Position 1: ~91.5%
- Position 2: ~79.7%
- Position 3: ~79.6%
- Overall: ~71.4% of all draft tokens accepted

**Critical dependency on KV cache:**
- `--mamba-ssm-cache-dtype float16` is REQUIRED — float32 consumes half the KV cache for SSM state, killing acceptance rates at concurrency >4

### What Doesn't Work

| Method | Why |
|--------|-----|
| `ngram_gpu` | Worse than MTP for all workloads |
| `DFlash` | Only supports dense models, not MoE/Mamba hybrid |
| `--mamba-cache-mode all` | Falls back to "align" for hybrid models |
| `ROCM_AITER_FA` | Crashes with `fmha_fwd` error on hybrid models |

---

## Continuous Batching

vLLM uses iteration-level scheduling (not request-level):

```
Step 1: [Prefill A] [Decode B]
Step 2: [Decode A] [Decode B] [Prefill C]   ← C fills slot after B finishes
Step 3: [Decode A] [Decode C]               ← B finished, removed
```

This is why concurrent requests get better throughput — the GPU is never idle between requests.

### Scheduler Types (V1)

- **FIFO** (default): Fill batch in priority order. Decode > prefill > waiting.
- **PrefillFirst**: Complete chunked prefills before resuming decode. Better for long-prompt workloads.

---

## ROCm-Specific Internals

### Attention Backends on ROCm

| Backend | Status | Notes |
|---------|--------|-------|
| `ROCM_AITER_FA` | Crashes on hybrid models | `fmha_fwd` invalid argument |
| Triton paged attention | Works (default fallback) | Slower than ciGCN on CDNA |
| `ROCM_FLASH` | N/A | CDNA-only (MI-series hardware) |

### AITER (AMD Inner Tensor Runtime)

- `VLLM_ROCM_USE_AITER=1` enables AITER for attention and linear ops
- **gfx1x support**: Attention (partial), linear (partial)
- **gfx1x NOT supported**: MoE kernels, RMSNorm — falls back to Triton
- The gfx1x check in AITER source disables MoE/RMSNorm paths regardless of env var

### MoE Kernel Execution

For Qwen3.6-35B-A3B (256 experts, 8 active):
1. Router selects top-8 experts per token
2. Token dispatched to expert GPUs via Triton fused_moe kernel
3. Custom MoE config: `~/.config/vllm/moe-configs/E=256,N=512,device_name=Radeon_8060S_Graphics,dtype=int4_w4a16.json`
4. Key tuning: `BLOCK_SIZE_N: 32`, `BLOCK_SIZE_K: 64`, `SPLIT_K: 1`

---

## Monitoring & Debugging

```bash
# Check running config
journalctl --user -u vllm | grep "non-default args"

# Monitor KV cache usage
curl -s http://127.0.0.1:8000/metrics | grep vllm:gpu_cache_usage

# Check preemption (KV cache eviction)
curl -s http://127.0.0.1:8000/metrics | grep vllm:num_preemption

# Speculative decoding metrics
curl -s http://127.0.0.1:8000/metrics | grep speculative

# Scheduler state
curl -s http://127.0.0.1:8000/metrics | grep -E "running|waiting|swapped"
```

---

## Key Sources

- vLLM PagedAttention paper: https://blog.vllm.ai/2023/06/20/vllm.html
- vLLM docs: https://docs.vllm.ai
- HuggingFace continuous batching architecture: https://huggingface.co/docs/transformers/continuous_batching_architecture
- vLLM SchedulerConfig source: `vllm/config.py`
