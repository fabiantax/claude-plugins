---
name: rdna35-architecture
description: RDNA 3.5 (gfx1151) GPU architecture reference for AMD Strix Halo. Compute units, cache hierarchy, wavefront mechanics, and implications for ML inference kernels.
allowed-tools: Read Bash
---

# RDNA 3.5 Architecture — gfx1151 (Radeon 8060S / Strix Halo)

---

## Hardware Overview

| Spec | Value |
|------|-------|
| Architecture | RDNA 3.5 (gfx1151) |
| GPU | Radeon 8060S (Strix Halo APU) |
| Device ID | 0x1586, Rev 0xd1 |
| Compute Units (CUs) | 40 |
| Stream Processors | 2560 (64 per CU × 40) |
| Wavefront Size | 32 (32 lanes/work-group) |
| GPU Clock | Up to ~2.9 GHz (reported: 602 MHz idle) |
| Memory | 128 GB unified LPDDR5X (shared CPU/GPU); ~96 GiB GPU-allocatable via GTT (512 MiB fixed VRAM carveout + dynamic GTT) |
| Memory Bandwidth | ~128 GB/s (LPDDR5X) |
| VBIOS | 113-STRXLGEN-001 |

---

## Wavefront Architecture

RDNA3.5 uses **wave32** (not wave64 like older GCN). This is critical for kernel optimization:

- **Wavefront size**: 32 work-items per wave
- **SIMD width**: 32-wide per clock
- **Waves per CU**: Up to 40 concurrent waves
- **VGPR count**: 256 per SIMD unit (1024 per CU, 4 SIMDs/CU)

### Implications for ML Kernels

1. **Triton kernels**: Block sizes should be multiples of 32. `BLOCK_SIZE_M/N/K: 32, 64, 128` — not 16 or 48.
2. **Matrix cores (MAI)**: RDNA3.5 has matrix AI instructions but they're different from CDNA's MFMA. The rocWMMA library wraps these.
3. **LDS (Local Data Share)**: 128 KB per CU (2× 64 KB). Critical for MoE expert dispatch and attention kernels.

---

## Cache Hierarchy

```
┌─────────────────────────────────────────┐
│  L3 (Infinity Cache / MALL)             │
│  ~4 MB shared across all CUs            │
│  ── highest bandwidth for repeated data │
├─────────────────────────────────────────┤
│  L2 Cache                               │
│  ~2 MB shared across shader array       │
│  ── backs L1, services LDS misses       │
├─────────────────────────────────────────┤
│  L1 Data Cache (per CU pair)            │
│  ~128 KB per CU pair                    │
│  ── scalar + vector data paths          │
├─────────────────────────────────────────┤
│  L0 (per SIMD)                          │
│  ~16 KB instruction cache               │
│  ── instruction fetch only              │
├─────────────────────────────────────────┤
│  LDS / VGPR File (per CU)              │
│  128 KB LDS + 256 VGPRs per SIMD       │
│  ── programmable scratchpad             │
└─────────────────────────────────────────┘
```

### Memory Bandwidth Implications

- **LDS**: ~10 TB/s effective bandwidth (register-file speed)
- **L1**: ~5 TB/s
- **L2**: ~2 TB/s
- **L3/MALL**: ~1 TB/s
- **VRAM (LPDDR5X)**: ~128 GB/s — **this is the bottleneck**

The 128 GB/s VRAM bandwidth is 10-50x slower than caches. For MoE models (256 experts, 8 active), expert weight fetching dominates inference time. Optimal strategies:
1. **Keep active expert weights in L2/L3** via GROUP_SIZE_M tiling (reuse across tokens)
2. **Prefetch next expert** during current expert compute
3. **Quantize to INT4/FP8** to halve/quartenary memory traffic

---

## Compute Unit (CU) Detail

Each CU contains:
- **4 SIMD units** (32-wide each)
- **1 Matrix AI (MAI) unit** — rocWMMA/WMMA instructions
- **128 KB LDS** (shared across the 4 SIMDs)
- **2 Scalar ALUs** (branch management, address calculation)
- **1 Texture fetch unit**
- **1 L1 data cache interface**

### Matrix Operations (MAI)

RDNA3.5 supports WMMA instructions via rocWMMA library:
- Input shapes: 16×16×16, 32×32×8, etc.
- Data types: fp16, bf16, int8, fp8 (via rocWMMA)
- NOT as flexible as CDNA MFMA (no fp64, limited accumulator types)

For vLLM/llama.cpp:
- `GGML_HIP_ROCWMMA_FATTN=ON` enables rocWMMA flash attention in llama.cpp
- hipBLASLt can use MAI for small-batch GEMM but is unstable on RDNA

---

## gfx1151-Specific Notes

### Why `HSA_OVERRIDE_GFX_VERSION=11.5.1`

ROCm 7.x does not natively support `gfx1151`. The override tells ROCm to use `gfx1150` (RDNA3.5 mobile) ISA, which is binary-compatible. This is required for:
- hipBLAS / hipBLASLt
- Triton kernel compilation
- rocWMMA

### Wavefront Size in Build Flags

ROCm clang 22 does not define `__AMDGCN_WAVEFRONT_SIZE` for gfx1151. Must pass explicitly:
```bash
-DCMAKE_HIP_FLAGS="-D__AMDGCN_WAVEFRONT_SIZE=32 -D__AMDGCN_WAVEFRONT_SIZE__=32"
```

### Unified Memory (128 GB unified, ~96 GiB GPU-allocatable)

The Strix Halo APU uses unified LPDDR5X memory shared between CPU and GPU:
- **Advantage**: Model weights can be loaded without explicit CPU→GPU copy overhead
- **Disadvantage**: Only ~128 GB/s bandwidth (vs HBM2e at ~3 TB/s on MI250)
- **GPU memory budget**: One 128 GB unified pool, no fixed VRAM partition — the GPU borrows on demand via GTT for ~96 GiB allocatable (512 MiB fixed VRAM carveout + ~97.6 GiB GTT). On current Mesa/RADV, Vulkan also exposes ~the full pool (~96 GiB), matching ROCm; the old ~26 GB Vulkan cap was a stale-Mesa limitation that newer Mesa fixed.
- **GPU memory utilization**: vLLM at 0.90 uses ~86 GB for KV cache + model weights

---

## Implications for Inference Optimization

| Factor | Impact | Recommendation |
|--------|--------|----------------|
| Low VRAM bandwidth (128 GB/s) | MoE expert fetch dominates | Use INT4 or FP8 quantization |
| Large unified memory (~96 GiB GPU-allocatable, of 128 GB) | Can fit 35B+ models easily | Use high gpu_memory_utilization |
| Wave32 architecture | Kernel block sizing | BLOCK_SIZE multiples of 32 |
| 128 KB LDS/CU | MoE expert tile | BLOCK_SIZE_K=64 (not 128, LDS pressure) |
| No CDNA MFMA | Limited matmul throughput | Use rocWMMA where available |
| Large L3 (4 MB) | Expert weight caching | GROUP_SIZE_M=4-8 for L2 reuse |

---

## Key Sources

- AMD RDNA 3.5 ISA reference (NDA — not publicly available)
- ROCm documentation: https://rocm.docs.amd.com
- AMD GPUOpen: https://gpuopen.com
- rocWMMA: https://github.com/ROCm/rocWMMA
- llama.cpp HIP backend: `~/code/tools/llama.cpp/ggml/src/ggml-cuda/`
