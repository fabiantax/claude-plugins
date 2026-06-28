---
name: triton-kernels
description: Triton kernel development and debugging on AMD ROCm (gfx1151). Covers writing, profiling, and optimizing custom Triton kernels for RDNA3.5, including MoE fused kernels and attention.
allowed-tools: Read Bash
---

# Triton Kernels on ROCm — gfx1151

---

## Setup

Triton 3.7 is installed inside the vLLM container with ROCm patches:

```bash
podman exec vllm-server python3 -c "import triton; print(triton.__version__)"
# 3.7.0+git6aa07328.rocm7.13
```

---

## Writing Triton Kernels for RDNA3.5

### Key Constraints

| Parameter | Value | Implication |
|-----------|-------|-------------|
| Wavefront size | 32 | Block sizes must be multiples of 32 |
| SIMD width | 32 | `tl.arange(0, BLOCK_SIZE)` ≤ 32 per program |
| LDS per CU | 128 KB | BLOCK_SIZE_K=64 (not 128, LDS pressure) |
| CU count | 40 | Max 40 concurrent blocks per SM |
| VRAM bandwidth | ~128 GB/s | Memory-bound, not compute-bound |

### Basic Kernel Template

```python
import triton
import triton.language as tl
import torch

@triton.jit
def add_kernel(
    x_ptr, y_ptr, output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements

    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y

    tl.store(output_ptr + offsets, output, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    output = torch.empty_like(x)
    n_elements = output.numel()
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    add_kernel[grid](x, y, output, n_elements, BLOCK_SIZE=1024)
    return output
```

### Block Size Rules for gfx1151

```python
# GOOD — multiples of 32
BLOCK_SIZE_M: tl.constexpr = 32   # or 64, 128, 256
BLOCK_SIZE_N: tl.constexpr = 32   # 32 was biggest win for MoE
BLOCK_SIZE_K: tl.constexpr = 64   # 128 causes LDS pressure on RDNA3.5

# BAD — not multiples of 32
BLOCK_SIZE: tl.constexpr = 16     # Wastes half the wavefront
BLOCK_SIZE_K: tl.constexpr = 48   # Misaligned
```

---

## MoE Fused Kernel Tuning

The Qwen3.6-35B-A3B model uses Triton `fused_moe` kernels. Custom config:

```json
// ~/.config/vllm/moe-configs/E=256,N=512,device_name=Radeon_8060S_Graphics,dtype=int4_w4a16.json
{
  "BLOCK_SIZE_M": 64,
  "BLOCK_SIZE_N": 32,
  "BLOCK_SIZE_K": 64,
  "GROUP_SIZE_M": 8,
  "num_warps": 4,
  "num_stages": 4
}
```

### Key Findings from Tuning

| Parameter | Default | Optimal (RDNA3.5) | Why |
|-----------|---------|-------------------|-----|
| `BLOCK_SIZE_N` | 16 | 32 | Doubles per-wave output, biggest single win |
| `GROUP_SIZE_M` | 1 | 4-8 | Improves L2 reuse across tokens |
| `SPLIT_K` | 1 | 1 | >1 hurts on RDNA (sync overhead > parallelism) |
| `BLOCK_SIZE_K` | 64 | 64 | 128 causes LDS overflow on RDNA3.5 |
| `num_warps` | 4 | 4 | 8 wastes VGPRs, 2 underutilizes |

---

## Debugging Triton on ROCm

### JIT Compilation Errors

```python
# Enable Triton logging
import os
os.environ["TRITON_PRINT_AUTOTUNING"] = "1"
os.environ["TRITON_LOG_DEBUG"] = "1"

# Check compiled PTX/HSACO
os.environ["TRITON_DUMP_DIR"] = "/tmp/triton_dump"
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `invalid argument for fmha_fwd` | AITER FA incompatible with model | Remove `--attention-backend ROCM_AITER_FA` |
| Triton JIT cold start (~30s) | First call compiles kernel | Warm up with dummy input |
| `NUM_THREADS must be power of 2` | Wavefront alignment | Use 32, 64, 128, 256 |
| OOM in Triton | LDS overflow | Reduce BLOCK_SIZE_K to 64 |

### Profiling Kernel Performance

```python
import triton
import torch

def benchmark(kernel, *args, **kwargs):
    # Warmup
    for _ in range(10):
        kernel(*args, **kwargs)
    torch.cuda.synchronize()

    # Benchmark
    ms = triton.testing.do_bench(lambda: kernel(*args, **kwargs))
    print(f"Kernel time: {ms:.3f} ms")
    return ms
```

---

## Custom Kernel Patterns

### GEMM (Matrix Multiply)

```python
@triton.jit
def matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)

    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        a = tl.load(a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak),
                    mask=(offs_m[:, None] < M) & (offs_k[None, :] < K), other=0.0)
        b = tl.load(b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn),
                    mask=(offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0)
        accumulator += tl.dot(a, b)
        offs_k += BLOCK_SIZE_K

    c = accumulator.to(c_ptr.dtype.element_ty)
    tl.store(c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn),
             c, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))
```

---

## Autotuning

```python
@triton.autotune(
    configs=[
        triton.Config({'BM': 32, 'BN': 32, 'BK': 32}, num_warps=4),
        triton.Config({'BM': 64, 'BN': 32, 'BK': 64}, num_warps=4),
        triton.Config({'BM': 64, 'BN': 64, 'BK': 32}, num_warps=4),
        triton.Config({'BM': 128, 'BN': 32, 'BK': 64}, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def tuned_matmul(...):
    ...
```

---

## vLLM Custom Kernels

vLLM's ROCm kernels live in the container at:
```
/opt/venv/lib/python3.12/site-packages/vllm/attention/ops/     # Attention kernels
/opt/venv/lib/python3.12/site-packages/vllm/model_executor/layers/fused_moe/  # MoE kernels
```

The MoE config file at `~/.config/vllm/moe-configs/` overrides default autotuning.
