---
name: llama-cpp-vulkan
description: llama.cpp Vulkan backend build, configuration, and optimization for AMD Strix Halo (gfx1151, RADV mesa 26). Use when running or tuning the Vulkan llama-server, comparing against ROCm, or debugging Vulkan-specific issues.
allowed-tools: Read Bash
---

# llama.cpp Vulkan Backend — Strix Halo (gfx1151, RADV)

**Binary:** `~/code/tools/llama.cpp/build-vulkan/bin/llama-server`  
**Driver:** RADV (mesa 26.0.3), Vulkan 1.4.335  
**Device:** `Vulkan0: Radeon 8060S Graphics (RADV STRIX_HALO)`. Current Mesa/RADV reports ~the full unified pool (logs `Vulkan0 … 97383 MiB`, ~96 GiB GPU-allocatable); an older Mesa showed only ~114227 MiB total / ~22760 MiB free — the stale-Mesa UMA-framebuffer cap, since fixed.  
**Note:** On current Mesa/RADV, Vulkan exposes ~the full unified pool (logs `Vulkan0 … 97383 MiB`, ~96 GiB), matching ROCm. The old ~26GB cap was a stale-Mesa limitation (RADV exposing only the UMA framebuffer portion) that newer Mesa fixed.

---

## Performance vs ROCm (measured, Qwen3.5-4B Q4_K_M, April 2026)

All numbers post-optimization (ROCm patched for gfx1151 MMQ/MMVQ, Vulkan with rm_kq=1).

### PP tok/s vs batch size

| PP batch | ROCm patched | Vulkan (rm_kq=1) | Winner |
|----------|-------------|-----------------|--------|
| ~150 tok | 1399 tok/s | 1087 tok/s | **ROCm +29%** |
| ~570 tok | 1699 tok/s | 1507 tok/s | **ROCm +13%** |
| ~1086 tok | 1822 tok/s | 1679 tok/s | **ROCm +8%** |
| ~1656 tok | 1833 tok/s | 1908 tok/s | **Vulkan +4%** |

### TG tok/s

| Backend | TG tok/s | Notes |
|---------|----------|-------|
| ROCm patched | 56.4 | Bandwidth-bound |
| **Vulkan (rm_kq=1)** | **63.3** | **+12% vs ROCm** |

**ROCm wins PP at all realistic batch sizes up to ~1500 tokens.** Vulkan wins TG and very large batch PP.  
**VRAM caveat (largely gone on current Mesa):** Vulkan/RADV now exposes ~the full unified pool (~96 GiB, of 128 GB unified), matching ROCm — the old ~26GB cap was a stale-Mesa limitation. On an old Mesa you may still see the ~26GB cap, in which case prefer ROCm for models > 20GB.

### Context scaling (ROCm, 10k–30k)

| Context | PP tok/s | TG tok/s | TTFT |
|---------|----------|----------|------|
| 10k (8970 tokens) | 1726.8 | 43.2 | 5.2s |
| 20k (18072 tokens) | 1570.0 | 38.0 | 11.5s |
| 30k (27174 tokens) | 1375.2 | 33.7 | 19.8s |

TG drops with context due to growing KV attention cost (flash attention helps but doesn't eliminate it).

---

## Source Patches Applied

### rm_kq=1 (`ggml/src/ggml-vulkan/ggml-vulkan.cpp`)

**Problem:** The dequant-mul-mat-vec kernel uses `rm_kq` to split workgroup reductions. Default was 2;
lowering to 1 improves efficiency on RDNA3.5.

**Fix:**
```cpp
// Line ~4046 in ggml_vk_build_graph() / mul_mat_vec dispatch
uint32_t rm_kq = 1;  // was 2
```

**Effect:** +26.5% PP at short context (1335→1689 tok/s measured). TG unchanged.

---

## Build (host, no toolbox needed)

```bash
# Install deps (once)
sudo dnf install -y vulkan-headers vulkan-loader-devel glslang glslc

# Configure — inside strix-llama toolbox (has glslc/glslang)
toolbox run -c strix-llama bash -c "
  cd ~/code/tools/llama.cpp &&
  cmake -B build-vulkan \
    -DGGML_VULKAN=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLAMA_CURL=ON &&
  cmake --build build-vulkan -j\$(nproc) --target llama-server
"
```

**Or build on host** if glslc is installed:
```bash
cd ~/code/tools/llama.cpp
cmake -B build-vulkan -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=ON
cmake --build build-vulkan -j$(nproc) --target llama-server
```

**No toolbox needed at runtime** — uses host RADV driver directly.

---

## CMake Build Flags

| Flag | Default | Effect |
|------|---------|--------|
| `GGML_VULKAN` | OFF | Enable Vulkan backend |
| `GGML_VULKAN_CHECK_RESULTS` | OFF | Validate GPU results vs CPU (slow, debug only) |
| `GGML_VULKAN_DEBUG` | OFF | Verbose Vulkan operation logging |
| `GGML_VULKAN_MEMORY_DEBUG` | OFF | Track all GPU memory allocations |
| `GGML_VULKAN_SHADER_DEBUG_INFO` | OFF | Embed debug info in compiled shaders |
| `GGML_VULKAN_VALIDATE` | OFF | Enable Vulkan validation layers (very slow) |
| `GGML_VULKAN_RUN_TESTS` | OFF | Run Vulkan op tests at startup |

**Auto-detected at configure time (cannot set manually):**
- `GGML_VULKAN_COOPMAT_GLSLC_SUPPORT` — cooperative matrix (coopmat) v1 — key perf feature for RDNA3
- `GGML_VULKAN_COOPMAT2_GLSLC_SUPPORT` — coopmat v2 (newer, higher perf)
- `GGML_VULKAN_INTEGER_DOT_GLSLC_SUPPORT` — integer dot product (for quantized types)
- `GGML_VULKAN_BFLOAT16_GLSLC_SUPPORT` — BF16 shader support

Check what was detected:
```bash
grep -i "COOPMAT\|INTEGER_DOT\|BFLOAT" ~/code/tools/llama.cpp/build-vulkan/CMakeCache.txt
```

---

## Runtime: Start the Server

```bash
# Basic — runs on host, no toolbox
nohup ~/code/tools/llama.cpp/build-vulkan/bin/llama-server \
    --host 0.0.0.0 \
    --port 8001 \
    --ctx-size 32768 \
    --n-gpu-layers 999 \
    --flash-attn on \
    -m ~/models/unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf \
    > /tmp/llama-vulkan.log 2>&1 &

# Verify device used:
~/code/tools/llama.cpp/build-vulkan/bin/llama-server --list-devices
# Output: Vulkan0: Radeon 8060S Graphics (RADV STRIX_HALO) (114227 MiB, 22760 MiB free)
```

---

## Runtime Server Flags (Vulkan-relevant)

| Flag | Recommended | Notes |
|------|-------------|-------|
| `--n-gpu-layers 999` | all | Offload all layers |
| `--flash-attn on` | yes | Flash attention — test if Vulkan impl is faster |
| `--ctx-size N` | 32768 | Keep ≤ GPU-allocatable budget (~96 GiB on current Mesa; old Mesa capped Vulkan at ~22-26GB) |
| `--ubatch-size N` | 512–2048 | Try 1024 first, tune up |
| `-ctk q4_0 -ctv q4_0` | for long ctx | KV cache quantization; saves VRAM at large contexts |
| `--device Vulkan0` | auto | Explicit device selection if multiple GPUs |
| `--split-mode none` | single GPU | Only one GPU on this machine |
| `--op-offload on` | default | Keep host tensor ops on GPU |

---

## RADV Environment Variables

Set before launching llama-server to tune the driver:

### Performance
```bash
# Force wave32 for compute shaders — RDNA3.5 natively uses wave32
RADV_PERFTEST=cs_wave32

# Enable SAM (Smart Access Memory / Resizable BAR) — ensures full VRAM visibility
RADV_PERFTEST=sam

# NIR shader cache — faster shader recompilation across restarts
RADV_PERFTEST=nir_cache

# Combine multiple flags with commas
RADV_PERFTEST=cs_wave32,sam,nir_cache

# BFloat16 (experimental — may speed up BF16 paths)
RADV_PERFTEST=bfloat16
```

### Memory visibility (important for Strix Halo APU)
```bash
# Force SAM — Strix Halo should use this for full unified-pool visibility
RADV_PERFTEST=sam

# Disable GTT spill — keeps buffers in VRAM instead of spilling to system RAM
RADV_PERFTEST=no_gtt_spill
```

### Debug (only when troubleshooting)
```bash
RADV_DEBUG=info          # Print device/driver info at startup
RADV_DEBUG=startup       # Verbose startup messages
RADV_DEBUG=no_cache      # Disable pipeline cache (for testing)
RADV_DEBUG=dump_shader_stats  # Print shader stats (perf profiling)
```

### Vulkan loader
```bash
# Force RADV only (skip other ICDs like llvmpipe, Intel)
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json

# Enable Vulkan validation layers (slow, debug only)
VK_INSTANCE_LAYERS=VK_LAYER_KHRONOS_validation
```

### Full recommended launch command
```bash
RADV_PERFTEST=cs_wave32,sam,nir_cache \
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json \
nohup ~/code/tools/llama.cpp/build-vulkan/bin/llama-server \
    --host 0.0.0.0 --port 8001 \
    --ctx-size 32768 --n-gpu-layers 999 \
    --flash-attn on --ubatch-size 1024 \
    -m ~/models/unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf \
    > /tmp/llama-vulkan.log 2>&1 &
```

---

## VRAM Visibility Issue (APU-specific)

On current Mesa/RADV, Vulkan exposes ~the full unified pool (~96 GiB, logs `Vulkan0 … 97383 MiB`), matching ROCm — this issue is largely resolved. On an **old Mesa**, RADV could report only ~26GB free. Historical causes of that cap:
- BIOS UMA Frame Buffer Size setting limited what RADV exposed
- SAM (Resizable BAR) not fully active for Vulkan

**Fix options:**
1. Set `RADV_PERFTEST=sam` — may unlock more VRAM
2. Check BIOS: set UMA Frame Buffer to 512MB or 2GB (counterintuitively unlocks more VRAM for ROCm; Vulkan behavior varies)
3. Kernel cmdline: add `amdgpu.gttsize=126976` to expose 124GB GTT

**Check what Vulkan actually sees:**
```bash
~/code/tools/llama.cpp/build-vulkan/bin/llama-server --list-devices
# Look for total MiB and free MiB
```

---

## Cooperative Matrix (coopmat) — Key Performance Feature

coopmat is the Vulkan equivalent of WMMA/tensor cores. On RDNA3.5:
- coopmat v1: supported by RADV on RDNA3
- coopmat v2: supported on RDNA3+ with mesa 24.1+

If not auto-detected, rebuild after ensuring mesa ≥ 24.1:
```bash
# Check mesa version
mesa_version=$(cat /usr/share/mesa/VERSION 2>/dev/null || \
  rpm -q mesa-libGL --qf "%{VERSION}" 2>/dev/null)
echo "Mesa: $mesa_version"

# Check what llama.cpp detected
grep -i "COOPMAT" ~/code/tools/llama.cpp/build-vulkan/CMakeCache.txt
```

If coopmat is enabled, expect another 10-30% TG/s improvement over baseline Vulkan.

---

## Updating the Wrapper Script

To use Vulkan as the default server:
```bash
# ~/.local/bin/llama-server-strix
#!/usr/bin/env bash
RADV_PERFTEST=cs_wave32,sam,nir_cache \
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json \
exec "$HOME/code/tools/llama.cpp/build-vulkan/bin/llama-server" \
    --host 0.0.0.0 \
    --port 8001 \
    --flash-attn on \
    --ctx-size 32768 \
    --n-gpu-layers 999 \
    "$@"
```

---

## Rebuild after llama.cpp update

```bash
cd ~/code/tools/llama.cpp
git pull
cmake --build build-vulkan -j$(nproc) --target llama-server
```

Full reconfigure (e.g. after mesa update):
```bash
cd ~/code/tools/llama.cpp
rm -rf build-vulkan
toolbox run -c strix-llama bash -c "
  cd ~/code/tools/llama.cpp &&
  cmake -B build-vulkan -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=ON &&
  cmake --build build-vulkan -j\$(nproc) --target llama-server
"
```

---

## Known Issues / Gotchas

| Symptom | Cause | Fix |
|---------|-------|-----|
| Server exits after one request | Interaction with stale ROCm process | Kill all llama-server processes first |
| Only ~26GB VRAM visible | Stale-Mesa RADV UMA limit (fixed on current Mesa, which sees ~96 GiB) | Update Mesa; or try `RADV_PERFTEST=sam` |
| Slower than ROCm on large models | (old Mesa only) VRAM visibility cap caused paging — fixed on current Mesa, which exposes ~96 GiB | Update Mesa; ROCm also fine for models > 20GB |
| `nohup toolbox run ... &` hangs | toolbox background issue | Run directly on host for Vulkan (no toolbox needed) |
| PP much slower than ROCm | coopmat not enabled | Check mesa version, rebuild |

---

## Backend Selection Guide

| Scenario | Use | Reason |
|----------|-----|--------|
| Interactive chat (low latency) | **Vulkan** | +12% TG tok/s (63.3 vs 56.4) |
| Coding agent with 10–64k context | **ROCm** | Better PP at all batch sizes < ~1600 tok |
| Large model > 20GB | **Either** | On current Mesa both reach ~the full unified pool (~96 GiB); only an old Mesa capped Vulkan at ~26GB (then prefer ROCm) |
| Batched prefill throughput | **ROCm** | +8–29% PP depending on batch |
| Long context 128k+ | **ROCm** | Flash attention scales better, more VRAM |
| Debugging GPU issues | **ROCm** | Better tooling: rocm-smi, rocprof |
