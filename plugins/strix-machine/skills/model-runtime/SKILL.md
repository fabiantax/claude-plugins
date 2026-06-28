---
name: model-runtime
description: Per-model vLLM runtime notes for Strix Halo — architectures, sizes, quirks, and known issues discovered in production. Use when starting, debugging, or switching models on the inference stack.
allowed-tools: Read Bash
---

# vLLM Model Runtime Notes — Strix Halo (gfx1151, ROCm 7.2.1)

**Container:** `docker.io/kyuz0/vllm-therock-gfx1151:20260313-163059`  
**Switch model:** `echo "<name>" > ~/.config/vllm/current-model && systemctl --user restart vllm`

---

## Critical: Required container flags (missing = "Memory in use" crash)

vLLM crashes with this error if the container is missing security/IPC flags:
```
Memory critical error by agent node-0 (Agent handle: ...). Reason: Memory in use.
RuntimeError: Engine core initialization failed.
```
**Root cause:** Default rootless podman seccomp profile blocks `mmap`/`mprotect` calls that KFD/HSA needs during EngineCore initialization. Also: default user memlock limit (8 MB) is too low to pin GPU memory.

**Required flags — all in `vllm.service` now:**
```
--security-opt seccomp=unconfined    # allows KFD mmap/mprotect
--ipc=host                           # shared memory between processes
--ulimit memlock=-1:-1               # unlimited memlock inside container
--cap-add SYS_PTRACE                 # needed by HSA/ROCm
LimitMEMLOCK=infinity                # [Service] section — raises user limit for rootless podman
```

**Also required in kernel cmdline:**
- `amd_iommu=off` — verified via `cat /proc/cmdline`

**LD_PRELOAD note:** `LD_PRELOAD=/opt/rocm/lib/librocm_smi64.so` is required. Without it, `libtorch_hip.so` fails to import (`undefined symbol: rsmi_is_P2P_accessible`). The container has this library at the same path but LD_LIBRARY_PATH alone is insufficient.

**Performance (Qwen3-Coder-Next, steady-state):** ~11.5 tg/s (23 tokens / ~2s). First inference call is ~58s due to KV warmup.

**Verified NOT to fix "Memory in use":** `NCCL_SHM_DISABLE=1`, `NCCL_P2P_DISABLE=1`, `NCCL_IB_DISABLE=1`, `HSA_DISABLE_FRAGMENT_ALLOCATOR=1`, `VLLM_WORKER_MULTIPROC_METHOD=spawn`, `HSA_XNACK` changes, removing LD_PRELOAD.

---

## Startup troubleshooting checklist

Before starting vLLM, check:
1. `rocm-smi --showpids` → should show "No KFD PIDs currently running"
2. `ls /dev/shm/sem.mp-*` → delete any leftover semaphores (`rm -f /dev/shm/sem.mp-*`)
3. `pgrep -f "hf download"` → kill any active downloads (on APU with XNACK=1, mmap'd download buffers register with HSA and can conflict with RCCL startup)
4. IOMMU must be off (see above)

After a vLLM crash, orphaned processes can hold the GPU:
```bash
kill -9 $(rocm-smi --showpids 2>/dev/null | awk 'NR>3 && /[0-9]/{print $1}')
```

---

## Model Catalog

### Qwen3.6-35B-A3B-AWQ-4bit
- **Size on disk:** 23GB | **VRAM:** ~18GB | **Shards:** 5
- **Architecture:** `Qwen3_5MoeForConditionalGeneration` (Gated DeltaNet + MoE: 10x(3xGatedDeltaNet→MoE → 1xGatedAttention→MoE))
- **NOT supported by llama.cpp** — Gated DeltaNet architecture only works in vLLM >=0.19.0
- **vLLM flags required:** `--enforce-eager` (pickling fix), `--max-num-batched-tokens 4096` (Mamba cache alignment)
- **Container:** Updated to `20260422-075517` (vLLM 0.19.2rc1)
- **Speed:** Similar to Qwen3.5-35B-A3B — MoE 3B active per token
- **Status:** ✅ Downloaded and verified complete
- **Use case:** Next-gen general purpose — improved reasoning over Qwen3.5, Gated DeltaNet architecture

### Qwen3.5-2B-AWQ-4bit
- **Size on disk:** 2.4GB | **VRAM:** ~1.5GB | **Shards:** 1
- **Architecture:** `Qwen3_5ForConditionalGeneration` (Mamba-hybrid: attention + SSM layers)
- **vLLM flags:** Enable-prefix-caching triggers experimental "Mamba cache align mode" warning — harmless but watch for instability
- **Warnings to ignore:** "Unrecognized keys in rope_parameters (mrope_interleaved, mrope_section)" — these are multimodal params, safe to ignore for text-only use
- **Use case:** Test/dev, ultra-low VRAM, latency benchmarking

### Qwen3.5-4B-AWQ-4bit
- **Size on disk:** 3.8GB | **VRAM:** ~2.5GB | **Shards:** 1
- **Architecture:** `Qwen3_5ForConditionalGeneration` (Mamba-hybrid, same as 2B)
- **Same warnings as 2B** — mrope params, Mamba cache mode
- **Use case:** Small/fast, edge-like workloads, very low VRAM

### Qwen3.5-27B-AWQ-4bit
- **Size on disk:** 19GB | **VRAM:** ~14GB | **Shards:** multiple
- **Architecture:** `Qwen3_5ForConditionalGeneration` (dense 27B, NOT MoE)
- **Warning:** Dense 27B — slower TG/s than MoE variants at similar quality
- **Use case:** When you need dense (no expert routing overhead), quality matters more than speed

### Qwen3.5-35B-A3B-AWQ-4bit
- **Size on disk:** 23GB | **VRAM:** ~18GB | **Shards:** multiple
- **Architecture:** `Qwen3_5MoeForConditionalGeneration` (MoE, 35B total / 3B active per token)
- **Speed:** TG/s similar to a dense 3B — extremely fast
- **Quality:** Closer to full 35B model at 3B compute cost
- **Status:** ✅ Downloaded and verified complete
- **Use case:** Best general-purpose model on this stack — fast, high quality, fits comfortably

### Qwen3-Coder-Next-AWQ-4bit
- **Size on disk:** 45GB (NOT ~18GB as the model guide estimated) | **VRAM:** ~40GB+ | **Shards:** multiple
- **Architecture:** `Qwen3NextForCausalLM` (fine-grained MoE: 512 experts, 10 active per token)
- **Note:** 512-expert fine-grained MoE is very different from coarse-grained MoE (35B-A3B). Expert routing overhead is higher.
- **Status:** ✅ Downloaded and verified complete
- **Use case:** Coding agents, SWE-Bench 70%+ capable, concurrent agent requests via vLLM batching

### gemma-4-26B-A4B-it-AWQ-4bit
- **Size on disk:** 17GB | **VRAM:** ~14GB | **Shards:** multiple
- **Architecture:** `Gemma4ForConditionalGeneration` (multimodal: vision + text, MoE 26B/4B active)
- **Use case:** Image understanding + text, vision-capable chat
- **Status:** ✅ Downloaded and verified complete

### gemma-4-31B-it-AWQ-4bit
- **Size on disk:** 20GB | **VRAM:** ~16GB | **Shards:** multiple
- **Architecture:** Gemma4 (text-only variant, dense ~31B — NOT multimodal despite the name)
- **Use case:** General reasoning, coding, text tasks; no vision capability
- **Status:** ✅ Downloaded and verified complete

### Qwen3-Omni-30B-A3B-Instruct-AWQ-4bit
- **Size on disk:** 2.8GB (INCOMPLETE — stalled download)
- **Architecture:** Audio + multimodal (speech, text, vision)
- **Download issue:** hf-transfer repeatedly stalls on this model — got stuck twice for 500+ minutes each. 6 shards frozen. Restart with:
  ```bash
  kill $(pgrep -f "hf download") && bash ~/download-models.sh
  ```
- **Status:** ❌ Download incomplete — needs restart
- **Use case:** Audio/speech input, multimodal tasks

### Qwen3-Next-80B-A3B-Instruct-AWQ-4bit
- **Size on disk:** 322MB (download just started as of Apr 14 09:00)
- **Architecture:** `Qwen3NextForCausalLM` (fine-grained MoE: 512 experts, same as Coder-Next but 80B)
- **Expected size:** ~40GB on disk | **VRAM:** ~40GB
- **Speed:** Despite 80B total params, 3B active → similar TG/s to dense 3B
- **Status:** ❌ Download in progress
- **Use case:** Maximum quality reasoning — 80B-level quality at ~3B compute cost

---

## Service file notes
- Current service: `~/.config/systemd/user/vllm.service`
- Current model: `~/.config/vllm/current-model`
- Useful flags already set: `--enforce-eager` (no CUDA graphs), `--enable-prefix-caching` (KV cache reuse), `--enable-chunked-prefill`, `--gpu-memory-utilization 0.90`
- `--max-model-len 32768` — fine for most models; increase for long-context needs
