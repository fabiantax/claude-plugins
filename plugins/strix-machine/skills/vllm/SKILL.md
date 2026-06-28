---
name: vllm
description: vLLM inference server management on Strix Halo (gfx1151, ROCm 7.2.1). Use for starting, stopping, switching models, troubleshooting, tuning flags, and monitoring performance.
allowed-tools: Read Bash
---

# vLLM — Strix Halo (gfx1151, ROCm 7.2.1)

## Quick Reference

| Action | Command |
|--------|---------|
| Start | `systemctl --user start vllm` |
| Stop | `systemctl --user stop vllm` |
| Status | `systemctl --user status vllm` |
| Logs | `journalctl --user -fu vllm` |
| Switch model | `echo "<name>" > ~/.config/vllm/current-model && systemctl --user restart vllm` |
| Check model | `cat ~/.config/vllm/current-model` |
| Test endpoint | `curl -s http://127.0.0.1:8000/v1/models \| python3 -m json.tool` |

## Service File

- **Location:** `~/.config/systemd/user/vllm.service`
- **Model selector:** `~/.config/vllm/current-model` (filename relative to `~/models/`)
- **Port:** 8000
- **Model served as:** `default` (via `--served-model-name default`)
- **Logs are in UTC** (container timezone), not local time

## Container

- **Image:** `docker.io/kyuz0/vllm-therock-gfx1151:20260422-075517`
- **vLLM version:** 0.19.2rc1.dev113
- **Latest tag check:** `skopeo list-tags docker://docker.io/kyuz0/vllm-therock-gfx1151 \| python3 -c "import sys,json; tags=json.load(sys.stdin)['Tags']; [print(t) for t in sorted(tags) if '20260' in t]"`
- **GitHub repo:** `kyuz0/amd-strix-halo-vllm-toolboxes`

## Current Flags

```
--served-model-name default     # Model ID = "default" for API calls
--dtype float16                 # Compute dtype
--max-model-len 32768           # Context window
--max-num-seqs 32               # Max concurrent sequences
--max-num-batched-tokens 4096   # Required for Mamba-hybrid models (Qwen3.5/3.6)
--gpu-memory-utilization 0.90   # VRAM usage target
--kv-cache-dtype fp8            # FP8 KV cache for memory savings
--enable-chunked-prefill        # Overlap prefill with decode
--enable-prefix-caching         # KV cache reuse for shared prefixes
--enforce-eager                 # Skip CUDA graph capture (avoids pickling errors with custom archs)
--trust-remote-code             # Required for custom model architectures
```

## Required Container Environment

```
HSA_ENABLE_SDMA=0
HSA_XNACK=0
HIP_VISIBLE_DEVICES=0
HSA_OVERRIDE_GFX_VERSION=11.5.1
HIP_FORCE_DEV_KERNARG=1
ROCBLAS_USE_HIPBLASLT=1
TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1
FLASH_ATTENTION_TRITON_AMD_ENABLE=TRUE
LD_LIBRARY_PATH=/opt/rocm/lib
LD_PRELOAD=/opt/rocm/lib/librocm_smi64.so
TORCH_COMPILE_DISABLE=1
VLLM_WORKER_MULTIPROC_METHOD=spawn
```

## Required Container Flags

```
--security-opt seccomp=unconfined    # KFD mmap/mprotect
--ipc=host                           # Shared memory
--ulimit memlock=-1:-1               # Unlimited memlock
--cap-add SYS_PTRACE                 # HSA/ROCm
```

Service section also needs: `LimitMEMLOCK=infinity`

## Troubleshooting

### "Memory in use" crash
- **Cause:** Missing container flags (seccomp, IPC, memlock)
- **Fix:** Ensure all required flags above are in the service file
- **Also check:** `amd_iommu=off` in kernel cmdline

### `_pickle.PicklingError: Can't pickle <function launcher>`
- **Cause:** AOT autograd cache fails with custom architectures (Gated DeltaNet, etc.)
- **Fix:** `--enforce-eager` flag + `TORCH_COMPILE_DISABLE=1` env var

### `AssertionError: block_size (2096) must be <= max_num_batched_tokens (2048)`
- **Cause:** Mamba-hybrid models (Qwen3.5/3.6) set block_size=2096 for cache alignment
- **Fix:** `--max-num-batched-tokens 4096` (must be >= block_size)

### Model not found (404 on `model: "default"`)
- **Fix:** Add `--served-model-name default` to vLLM serve command
- **Alternative:** Pass the full model path via `VLLM_MODEL` env var to the client app

### vLLM won't start after crash
1. `rocm-smi --showpids` — check for orphan GPU processes
2. Kill orphans: `kill -9 $(rocm-smi --showpids 2>/dev/null | awk 'NR>3 && /[0-9]/{print $1}')`
3. Clean semaphores: `rm -f /dev/shm/sem.mp-*`
4. Kill active downloads: `pkill -f "hf download"` (mmap'd buffers can conflict with HSA)

### "IPv6 connection refused"
- **Cause:** pasta container networking doesn't bind IPv6
- **Fix:** Use `127.0.0.1` (not `localhost`) in curl/API calls

## Model-Specific Notes

### Qwen3.6-35B-A3B-AWQ-4bit (Gated DeltaNet + MoE)
- **Architecture:** `Qwen3_5MoeForConditionalGeneration` (resolved by vLLM)
- **NOT supported by llama.cpp** — Gated DeltaNet architecture only works in vLLM >=0.19.0
- Requires `--enforce-eager` and `--max-num-batched-tokens 4096`
- Hybrid: 10x(3xGated DeltaNet -> MoE -> 1xGated Attention -> MoE)

### Qwen3.5-35B-A3B-AWQ-4bit (Mamba-hybrid MoE)
- Same architecture class as Qwen3.6 in vLLM
- Also needs `--max-num-batched-tokens 4096` for Mamba cache alignment

### Qwen3-Coder-Next-AWQ-4bit (fine-grained MoE)
- 512 experts, 10 active per token — higher routing overhead than coarse MoE
- 45GB on disk, ~40GB+ VRAM

## Performance Tuning

- **FP8 KV cache** (`--kv-cache-dtype fp8`): saves ~50% KV memory, minimal quality loss
- **Chunked prefill**: overlaps prompt processing with token generation
- **Prefix caching**: reuses KV cache for shared system prompts across requests
- **enforce-eager**: avoids CUDA graph compilation overhead, required for custom archs
