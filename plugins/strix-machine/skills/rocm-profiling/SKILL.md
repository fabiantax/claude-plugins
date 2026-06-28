---
name: rocm-profiling
description: ROCm profiling and debugging tools for AMD RDNA GPUs (gfx1151, Strix Halo). Use when diagnosing performance, profiling kernels, or debugging GPU issues.
allowed-tools: Read Bash
---

# ROCm Profiling & Debugging — Strix Halo (gfx1151)

**GPU:** AMD Radeon 8060S (gfx1151, RDNA3.5, 128 GB unified LPDDR5X; ~96 GiB GPU-allocatable via GTT)
**Driver:** 6.19.12-300.fc44.x86_64
**ROCm:** 7.2.1 (in `strix-llama` toolbox), host has rocm-smi only
**Device ID:** 0x1586, Rev 0xd1

---

## Available Tools

### Host (no toolbox needed)

| Tool | Location | Works on RDNA |
|------|----------|---------------|
| `rocm-smi` | `/opt/rocm/bin/rocm-smi` | Yes — basic monitoring only |
| `rocm-smi --showall` | Full GPU info dump | Yes |
| `rocm-smi -d 0 --showhw` | Hardware details | Yes |
| `rocm-smi -d 0 --showmeminfo vram` | VRAM usage | Yes |
| `rocm-smi -d 0 --showpids` | Processes using GPU | Yes |

### In Toolbox (`strix-llama`)

| Tool | Status on RDNA | Notes |
|------|----------------|-------|
| `rocprof` / `rocprofv2` | Limited | CDNA-focused; RDNA may crash or return incomplete data |
| `omniperf` | Limited | Works for basic metrics; many PMCs unavailable on RDNA |
| `rocm-smi` | Full | Same as host |

### In vLLM Container

| Tool | Notes |
|------|-------|
| `rocm-smi` | Available via LD_PRELOAD |
| Python profiling | Use `torch.profiler` with `rocprof` backend |

---

## Quick Commands

```bash
# GPU status
rocm-smi

# VRAM usage
rocm-smi -d 0 --showmeminfo vram

# Processes using GPU
rocm-smi -d 0 --showpids

# Temperature + clocks
rocm-smi -d 0 --showtemp --showclk

# Full hardware info
rocm-smi --showall

# Reset GPU (if hung)
sudo echo 1 > /sys/class/drm/card0/device/reset
```

---

## Profiling vLLM

### PyTorch Profiler (recommended for RDNA)

```python
import torch.profiler as profiler

with profiler.profile(
    activities=[
        profiler.ProfilerActivity.CPU,
        profiler.ProfilerActivity.CUDA,  # Works for HIP too
    ],
    record_shapes=True,
    profile_memory=True,
    with_stack=True,
) as prof:
    # Run inference here
    pass

print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=20))
```

### vLLM Built-in Metrics

```bash
# Prometheus metrics (if enabled)
curl http://127.0.0.1:8000/metrics

# Key metrics to watch:
# - vllm:num_requests_running
# - vllm:num_requests_waiting
# - vllm:gpu_cache_usage_perc
# - vllm:num_preemption
# - vllm:avg_generation_throughput
```

### Log-Based Profiling

```bash
# vLLM with detailed logging
VLLM_LOGGING_LEVEL=DEBUG in container env

# Check Triton kernel compilation times
journalctl --user -u vllm | grep -E "JIT|triton|compiling"
```

---

## rocprofv2 in Toolbox (CDNA-biased, may not work on RDNA)

```bash
toolbox run -c strix-llama bash -c "
  rocprofv2 --hsa-trace --hip-trace \
    -d /tmp/rocprof-output \
    -- ./your_binary
"
```

If `rocprofv2` crashes or returns empty traces, fall back to PyTorch profiler or `rocm-smi` polling.

---

## Known RDNA Limitations

1. **No hardware performance counters (PMCs)** — RDNA GPUs lack many of the profiling counters that CDNA (MI-series) exposes. `omniperf` and `rocprof` return partial data.
2. **No power management via rocm-smi** — `get_power_cap`, `get_overdrive_level` are not supported. Power is managed by the kernel driver (`amdgpu`).
3. **No fan control** — Fan metrics not supported on 8060S (likely OEM thermal solution).
4. **Clock reporting** — Only `sclk` (shader clock) is reported. Memory clock not separately visible.

---

## Driver-Level Tuning (amdgpu kernel module)

```bash
# Check current power_dpm_state
cat /sys/class/drm/card0/device/power_dpm_state

# Force high performance mode
echo performance > /sys/class/drm/card0/device/power_dpm_force_performance_level

# Check pp_feature_mask (enables/disables power features)
cat /sys/class/drm/card0/device/pp_feature_mask

# VRAM info
cat /sys/class/drm/card0/device/mem_info_vram_total
cat /sys/class/drm/card0/device/mem_info_vram_used
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `rocm-smi` shows no GPU | Driver not loaded | `sudo modprobe amdgpu` |
| `HSA_STATUS_ERROR` | Wrong GFX version | Set `HSA_OVERRIDE_GFX_VERSION=11.5.1` |
| GPU hang / black screen | Unrecoverable fault | `sudo echo 1 > /sys/class/drm/card0/device/reset` |
| vLLM "Memory in use" | KFD memlock | `ulimit -l unlimited` or `LimitMEMLOCK=infinity` in systemd |
| VRAM not fully visible | amdgpu gtt_size | Check `amdgpu.gtt_size` kernel param |

---

## Environment Variables Reference

```bash
# Essential for gfx1151
HSA_OVERRIDE_GFX_VERSION=11.5.1    # Required — ROCm doesn't natively recognize gfx1151
HSA_XNACK=0                         # Disable XNACK (not supported on RDNA)
HSA_ENABLE_SDMA=0                   # Disable SDMA (workaround for pci_notifier issues)

# Performance
HIP_FORCE_DEV_KERNARG=1             # Force device kernarg allocation
ROCBLAS_USE_HIPBLASLT=1             # Use hipBLASLt for GEMM (may be unstable)
HIP_VISIBLE_DEVICES=0               # Select GPU

# Triton/Flash Attention
TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1
FLASH_ATTENTION_TRITON_AMD_ENABLE=TRUE

# Debug
HSA_ENABLE_DEBUG=1                  # Enable HSA debug queues
AMD_LOG_LEVEL=4                     # HIP runtime logging (0-6)
```
