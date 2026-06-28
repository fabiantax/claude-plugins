---
name: hipblas-internals
description: hipBLAS and hipBLASLt internals for AMD RDNA GPUs. Covers ROCBLAS_USE_HIPBLASLT, RDNA vs CDNA differences, known issues, and tuning for gfx1151.
allowed-tools: Read Bash
---

# hipBLAS / hipBLASLt Internals — RDNA (gfx1151)

---

## Overview

| Library | Purpose | RDNA Support |
|---------|---------|-------------|
| **rocBLAS** | Full BLAS (GEMM, etc.) | Full — primary backend for RDNA |
| **hipBLASLt** | Lightweight GEMM (optimized matmul) | Experimental on RDNA |
| **hipBLAS** | BLAS wrapper (dispatches to rocBLAS/hipBLASLt) | Full |

---

## rocBLAS

The primary BLAS library for AMD GPUs. Wraps library-specific GEMM implementations:

- Supports fp16, bf16, fp32, fp64, int8
- Uses `Tensile` library for auto-tuned GEMM kernels
- On RDNA: uses WMMA/MAI instructions where available
- Well-tested on RDNA, stable

---

## hipBLASLt

A lightweight GEMM library inspired by cuBLASLt. Designed for ML workloads:

### What It Accelerates

- **Batched GEMM**: Multiple small matrix multiplications (common in attention QKV projection)
- **Fused operations**: GEMM + bias, GEMM + activation
- **Epilogue fusion**: Output directly to destination format (e.g., fp8 quantization after GEMM)

### RDNA vs CDNA

| Feature | CDNA (MI-series) | RDNA (gfx1151) |
|---------|------------------|----------------|
| MFMA instructions | Full support | Not available |
| WMMA instructions | Limited | rocWMMA available |
| hipBLASLt stability | Production-ready | Experimental — may crash or produce wrong results |
| XNACK (page migration) | Supported | Not supported (`HSA_XNACK=0`) |

### Why hipBLASLt Is Unstable on RDNA

1. **No MFMA**: CDNA's Matrix Fused Multiply-Add is the primary accelerator. RDNA only has WMMA (limited shapes/types).
2. **Kernel auto-tuning gap**: hipBLASLt's auto-tuning assumes CDNA compute capabilities.
3. **Wavefront differences**: CDNA uses wave64; RDNA uses wave32. Some kernels may have incorrect subgroup sizing.
4. **Memory layout**: CDNA's HBM has different access patterns than RDNA's GDDR/LPDDR unified memory.

### The `ROCBLAS_USE_HIPBLASLT=1` Flag

This environment variable tells rocBLAS to try hipBLASLt first for eligible GEMM operations:

```bash
# In vLLM container
ROCBLAS_USE_HIPBLASLT=1  # Currently enabled

# To disable (if unstable)
unset ROCBLAS_USE_HIPBLASLT
```

**Current status on this machine**: Enabled and appears stable for the Qwen3.6-35B-A3B model. If you see GEMM crashes or NaN outputs, disable it first.

---

## Tuning Matrix

| Scenario | hipBLASLt | Notes |
|----------|-----------|-------|
| Large-batch GEMM (>32 tokens) | On | Most benefit from epilogue fusion |
| Single-token decode | Marginal | Small GEMM, overhead may dominate |
| MoE expert dispatch | N/A | Uses Triton fused_moe, not hipBLASLt |
| Attention QKV | On | Batched GEMM with bias — main win |

---

## Debugging

```bash
# Enable rocBLAS logging
export ROCBLAS_LAYER=1          # Log all GEMM calls
export ROCBLAS_LAYER_ARGS=1     # Log arguments
export ROCBLAS_LAYER_BENCH=1    # Log benchmark results

# Check which backend is used
# In container:
python3 -c "import torch; print(torch.backends.cuda.flash_sdp_enabled())"

# hipBLASLt arch check
# hipBLASLt checks for gfx architecture at load time
# gfx1151 with HSA_OVERRIDE_GFX_VERSION=11.5.1 may or may not pass the check
```

---

## Known Issues on This Machine

1. **hipBLASLt + `--enforce-eager`**: No known interaction. Both work fine together.
2. **hipBLASLt + speculative decoding (MTP)**: No known issues.
3. **hipBLASLt + MoE (fused_moe)**: hipBLASLt is not used for MoE — Triton kernels handle expert dispatch.

---

## Sources

- rocBLAS docs: https://rocm.docs.amd.com/projects/rocBLAS
- hipBLASLt docs: https://rocm.docs.amd.com/projects/hipBLASLt
- ROCm math libraries overview: https://rocm.docs.amd.com
