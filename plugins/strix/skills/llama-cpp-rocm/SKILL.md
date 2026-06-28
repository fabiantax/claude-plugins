---
name: llama-cpp-rocm
description: llama.cpp ROCm/HIP build and runtime optimization guide for AMD Strix Halo (gfx1151, RDNA3.5, 128 GB unified, ~96 GiB GPU-allocatable). Use when building, tuning, or benchmarking llama.cpp on this machine.
allowed-tools: Read Bash
---

# llama.cpp ROCm Optimization Guide — Strix Halo (gfx1151, RDNA3.5)

**Binary:** `~/code/tools/llama.cpp/build/bin/llama-server`  
**Wrapper:** `~/.local/bin/llama-server-strix` (port 8001, --flash-attn on, --n-gpu-layers 999)  
**Toolbox:** `strix-llama` (`docker.io/kyuz0/amd-strix-halo-toolboxes:rocm-7.2.1`)  
**Rebuild:** `toolbox run -c strix-llama bash -c "cd ~/code/tools/llama.cpp && cmake --build build -j\$(nproc)"`

---

## Current Build Config

```bash
toolbox run -c strix-llama bash -c "
  cd ~/code/tools/llama.cpp && rm -rf build &&
  cmake -B build \
    -DGGML_HIP=ON \
    -DGPU_TARGETS=gfx1151 \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLAMA_CURL=ON \
    -DGGML_HIP_ROCWMMA_FATTN=ON \
    '-DCMAKE_HIP_FLAGS=-D__AMDGCN_WAVEFRONT_SIZE=32 -D__AMDGCN_WAVEFRONT_SIZE__=32' &&
  cmake --build build -j\$(nproc) --target llama-server
"
```

**Notes:**
- `__AMDGCN_WAVEFRONT_SIZE`: ROCm clang 22 does not auto-define for gfx1151 — must pass manually
- `HIP_VERSION >= 60000000`: hipBLAS 3.x (ROCm 7.2) renamed types. Patched in `ggml/src/ggml-cuda/vendors/hip.h` line 160
- `--mllvm -amdgpu-unroll-threshold-local=600`: **does not exist** in ROCm 7.2 clang — causes build failure, do not use

---

## CMake Build Flags

| Flag | Value | Effect |
|------|-------|--------|
| `GGML_HIP` | ON | Enable ROCm/HIP backend |
| `GPU_TARGETS` | gfx1151 | Compile only for Strix Halo GPU |
| `GGML_HIP_ROCWMMA_FATTN` | ON | rocWMMA flash attention |
| `LLAMA_CURL` | ON | Enable model download via curl |
| `CMAKE_HIP_FLAGS` | `-D__AMDGCN_WAVEFRONT_SIZE=32 -D__AMDGCN_WAVEFRONT_SIZE__=32` | Required for gfx1151 |

**Do NOT use:**
- `ROCBLAS_USE_HIPBLASLT=1` at runtime — unstable on RDNA (CDNA-only)
- `-DGGML_HIP_MMQ_MFMA=ON` — MFMA is CDNA-only

---

## Source Patches Applied

### 1. hipBLAS API patch (`ggml/src/ggml-cuda/vendors/hip.h` line 160)
```cpp
// Changed: threshold 60500000 → 60000000
// Reason: HIP_VERSION=60443484 on ROCm 7.2 is below 60500000 but hipBLAS 3.x renamed types
```

### 2. gfx1151 MMQ tile size patch (`ggml/src/ggml-cuda/mmq.cuh`)

**Problem (issue #21284):** gfx1151 was using 128×128 MMQ tiles — too large, causes register
spilling. Fix: cap at 48×64 with nwarps=4 (nwarps×tile_C::I(16)==mmq_y(64)).

```cpp
// get_mmq_x_max_host(): added before main return
if (GGML_CUDA_CC_IS_RDNA3_5(cc)) { return 48; }

// get_mmq_x_max_device(): added before AMD_WMMA_AVAILABLE check
#if defined(RDNA3_5)
    return 48;

// get_mmq_y_host(): RDNA3.5 now returns 64 instead of 128
GGML_CUDA_CC_IS_RDNA1(cc) || GGML_CUDA_CC_IS_RDNA3_5(cc) ? 64 : 128

// get_mmq_y_device(): same for compile-time path
#if defined(RDNA1) || defined(RDNA3_5)
    return 64;

// mmq_get_nwarps_host/device(): nwarps=4 for RDNA3.5 (satisfies nwarps*16==mmq_y(64))
if (GGML_CUDA_CC_IS_RDNA3_5(cc)) { return 4; }
#if defined(RDNA3_5)
    return 4;
```

### 3. gfx1151 MMVQ dispatch patch (`ggml/src/ggml-cuda/mmvq.cu`)

**Problem:** gfx1151 was using RDNA2 MMVQ parameters (nwarps=1 for all types).
Fix: dedicated `MMVQ_PARAMETERS_RDNA3_5` table with nwarps=8 for simple quant types.

```cpp
// Added to enum:
MMVQ_PARAMETERS_RDNA3_5,  // gfx1150/gfx1151

// Device dispatch: RDNA3_5 checked before RDNA3_0
#elif defined(RDNA3_5)
    return MMVQ_PARAMETERS_RDNA3_5;

// Host dispatch: RDNA3.5 checked before RDNA3.0
if (GGML_CUDA_CC_IS_RDNA3_5(cc)) { return MMVQ_PARAMETERS_RDNA3_5; }

// calc_nwarps: nwarps=8 for simple types at ncols_dst=1
// (Q4_0, Q4_1, Q5_0, Q5_1, Q8_0, Q4_K, Q6_K, IQ4_NL, IQ4_XS)
```

---

## Measured Performance (Qwen3.5-4B Q4_K_M, April 2026)

### PP tok/s vs context (ROCm patched vs Vulkan)

| PP batch | ROCm patched | Vulkan (rm_kq=1) | Winner |
|----------|-------------|-----------------|--------|
| ~150 tok | 1399 tok/s | 1087 tok/s | **ROCm +29%** |
| ~570 tok | 1699 tok/s | 1507 tok/s | **ROCm +13%** |
| ~1086 tok | 1822 tok/s | 1679 tok/s | **ROCm +8%** |
| ~1656 tok | 1833 tok/s | 1908 tok/s | Vulkan +4% |

### TG tok/s

| Backend | TG tok/s | Notes |
|---------|----------|-------|
| ROCm patched | 56.4 | Bandwidth-bound — patches don't help TG |
| Vulkan (rm_kq=1) | 63.3 | +12% vs ROCm — RADV decode path advantage |

### Context scaling (ROCm, Qwen3.5-4B Q4_K_M, f16 KV, April 2026)

| Context | PP tok/s | TG tok/s | TTFT |
|---------|----------|----------|------|
| 25k (22623t) | 1439.4 | 37.0 | 15.7s |
| 50k (45379t) | 1051.1 | 29.4 | 43.2s |
| 75k (68134t) | 750.5 | 24.5 | 90.8s |
| 100k (90890t) | 566.8 | 21.1 | 160.4s |
| 125k (113645t) | 777.6 | 27.6 | 146.2s |
| 150k (136401t) | 676.6 | 24.9 | 201.6s |
| 175k (159157t) | 590.2 | 23.0 | 269.7s |
| 200k (181912t) | 514.7 | 21.3 | 353.4s |
| 225k (204669t) | 456.7 | 19.8 | 448.1s |
| 250k | OOM — f16 KV at 250k exceeds VRAM |

**Notes:**
- TG drops with context (more KV cache to attend over even with FA)
- PP scales roughly as O(N) from bandwidth bottleneck on large KV
- Do NOT use `-ctk q4_0 -ctv q4_0` for long-context benchmarking (see bug below)

#### Known bug: `-ctk q4_0` OOM at 110k+ context

With `-ctk q4_0 -ctv q4_0`, the WMMA/TILE flash attention kernels need to convert quantized K/V to f16 on every FA call. Since KV length grows monotonically during prefill, old-size pool buffers are never reused. The ROCm pool accumulates ~2(N+1)(N+2) MB of wasted K_f16+V_f16 allocations after N ubatches (each ubatch = 512 tokens). At 128k context (~250 ubatches), the pool grows to ~130 GB → OOM. The crash shows as `ROCm error: out of memory` in `launch_fattn` for `ggml_cuda_flash_attn_ext_tile_case<256,256>`.

**Workaround:** Use f16 KV (default, no `-ctk`). KV VRAM grows 4× but the pool stays small.

Run `~/ctx-bench.sh <model.gguf> [max_ctx_k]` — bench uses f16 KV by default.

---

### Context scaling (ROCm, Gemma-4-E4B Q4_K_M, f16 KV, April 2026)

| Context | PP tok/s | TG tok/s | TTFT |
|---------|----------|----------|------|
| 25k (22629t) | 1384.0 | 41.8 | 16.4s |
| 50k (45385t) | 1116.8 | 37.4 | 40.6s |
| 75k (68140t) | 936.6 | 34.0 | 72.8s |
| 100k (90896t) | 807.8 | 31.1 | 112.5s |
| 125k (113651t) | 709.0 | 28.7 | 160.3s |

**Notes:**
- Full-attention architecture (no SSM hybrid) — TG scales ~linearly with context unlike Qwen3.5-4B
- TG at 125k (28.7) vs Qwen3.5-4B at 125k (27.6) — similar despite larger model

---

### Context scaling (ROCm, Qwen3.5-35B-A3B Q4_K_M, f16 KV, April 2026)

| Context | PP tok/s | TG tok/s | TTFT |
|---------|----------|----------|------|
| 25k (22623t) | 1238.5 | 45.0 | 18.3s |
| 50k (45379t) | 1017.8 | 41.4 | 44.6s |

**Notes:**
- MoE architecture (activates ~3B of 35B params) — TG 45 tok/s at 25k despite 21GB model size
- Requires vLLM to be stopped; 21GB model + KV cache exhausts VRAM when vLLM is running (91GB used)
- Only tested to 50k due to MoE VRAM constraints alongside KV cache growth

---

### Context scaling (ROCm, Gemma-4-26B-A4B Q4_K_M, f16 KV, April 2026)

| Context | PP tok/s | TG tok/s | TTFT |
|---------|----------|----------|------|
| 25k (22629t) | 1257.1 | 36.6 | 18.0s |
| 50k (45385t) | 968.6 | 34.2 | 46.9s |

**Notes:**
- MoE architecture (activates ~4B of 26B params) — 16GB model, similar constraints as 35B
- Requires vLLM to be stopped for benchmarking

---

## Backend Selection Guide

| Scenario | Use | Reason |
|----------|-----|--------|
| Interactive chat (low latency) | **Vulkan** | +12% TG tok/s |
| Coding agent with 10–64k context | **ROCm** | Better PP at all batch sizes <1656 tok |
| Large model > 20GB | **Either** | On current Mesa both reach ~the full unified pool (~96 GiB); only an old Mesa capped Vulkan at ~26GB (then prefer ROCm) |
| Batched prefill throughput | **ROCm** | +8–29% PP depending on batch |
| Long context 128k+ | **ROCm** | Flash attention scales better |

---

## Runtime Launch

```bash
# ROCm (via wrapper)
llama-server-strix -m ~/models/unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf

# Or directly
toolbox run -c strix-llama ~/code/tools/llama.cpp/build/bin/llama-server \
  --host 0.0.0.0 --port 8001 \
  --flash-attn on \
  --ctx-size 32768 \
  --n-gpu-layers 999 \
  -m ~/models/unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf
```

**Server flags:**

| Flag | Recommended | Notes |
|------|-------------|-------|
| `--flash-attn on` | yes | Must use `on` not bare flag |
| `--ctx-size N` | 32768 | Up to 131072 with `-ctk q4_0 -ctv q4_0` |
| `--n-gpu-layers 999` | all | Offload everything |
| `--ubatch-size 1024` | start here | Try 512/1024/2048 for tuning |
| `-ctk q4_0 -ctv q4_0` | long ctx | Quantize KV cache; saves ~4× VRAM |

---

## Benchmarking Scripts

| Script | Purpose |
|--------|---------|
| `~/blazor-convo.sh` | 5-turn Blazor conversation, tg/s per turn |
| `~/blazor-bench.sh` | Sequential + batched + coding-agents scenario |
| `~/ctx-bench.sh <model> [max_ctx_k]` | PP+TG at 10k→Nk (default 128k) |

---

## Known Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `--flash-attn` parse error | Bare flag | Use `--flash-attn on` |
| `hipblasGemmEx` compile error | hipBLAS 3.x API rename | Patch hip.h threshold (done) |
| `__AMDGCN_WAVEFRONT_SIZE` undeclared | ROCm clang 22 | Pass via CMAKE_HIP_FLAGS (done) |
| Build fails with `-amdgpu-unroll-threshold-local` | Flag doesn't exist in ROCm 7.2 | Remove from CMAKE_HIP_FLAGS |
| `static_assert(nwarps*tile_C::I == mmq_y)` | mmq_y=64 needs nwarps=4 | Patch mmq_get_nwarps (done) |
| `toolbox run ... &` hangs | stdin requirement | Use `nohup ... &` or `toolbox run -c ... bash -c "... & sleep N"` |
