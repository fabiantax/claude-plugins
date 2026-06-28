---
name: pytorch-rocm
description: PyTorch on AMD ROCm for Strix Halo. Covers container-based PyTorch usage, training, profiling, mixed precision, custom kernels, and ROCm-specific patterns. Use when writing PyTorch code for this machine, profiling models, or debugging GPU compute issues.
allowed-tools: Read Bash
---

# PyTorch on ROCm — Strix Halo (gfx1151)

---

## Setup

PyTorch is NOT installed on the host. It lives inside two environments:

| Environment | PyTorch | Access | Use For |
|-------------|---------|--------|---------|
| vLLM container | 2.13.0a0+rocm7.13 | `podman exec vllm-server python3 ...` | Inference, profiling, quantization |
| strix-llama toolbox | None | ROCm toolchain only | Building C++/HIP binaries |

### Running PyTorch Code

```bash
# One-liner
podman exec vllm-server python3 -c "import torch; print(torch.cuda.get_device_name(0))"

# Script
podman exec vllm-server python3 /path/to/script.py

# Interactive (if needed)
podman exec -it vllm-server python3
```

### Mounting Volumes

The container already has:
- `~/models/` → `/models/` (model weights)
- `~/.config/vllm/patches/` → patched rocm.py
- `~/.config/vllm/moe-configs/` → MoE kernel configs

For custom work, exec into the container or mount additional volumes.

---

## Key Packages in Container

```
torch                  2.13.0a0+rocm7.13
torchvision            0.27.0a0+rocm7.13
torchaudio             2.11.0+rocm7.13
triton                 3.7.0+rocm7.13
transformers           5.5.4
accelerate             1.13.0
datasets               4.8.4
peft                   0.19.1
flash_attn             2.8.4
compressed-tensors     0.15.0.1
amd-aiter              0.1.11
amd-quark              0.11.1
bitsandbytes           0.43.3
conch-triton-kernels   1.2.1
safetensors            (included)
```

---

## Device Properties

```python
import torch

print(torch.cuda.get_device_name(0))       # Radeon 8060S Graphics
print(torch.cuda.device_count())            # 1
print(torch.cuda.get_device_properties(0))
# total_memory: ~96 GiB GPU-allocatable via GTT (of 128 GB unified)
# major: 11, minor: 5 (gfx1151)
# multi_processor_count: 40 (CUs)
```

---

## Mixed Precision

```python
# FP16 (most common for inference)
model = model.half()

# BF16 (better numerical stability, supported on RDNA3.5)
model = model.bfloat16()

# FP8 (via torch.float8_e4m3fn / torch.float8_e5m2)
# Available in PyTorch 2.x with ROCm 7.x
x_fp8 = x.to(torch.float8_e4m3fn)

# Automatic Mixed Precision
from torch.cuda.amp import autocast, GradScaler
scaler = GradScaler()

with autocast(dtype=torch.float16):
    output = model(input)
    loss = criterion(output, target)
scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

---

## Profiling

### PyTorch Profiler (recommended for RDNA)

```python
import torch.profiler as profiler

with profiler.profile(
    activities=[
        profiler.ProfilerActivity.CPU,
        profiler.ProfilerActivity.CUDA,
    ],
    record_shapes=True,
    profile_memory=True,
    with_stack=True,
    with_modules=True,
) as prof:
    model(input_ids)

# Top kernels by GPU time
print(prof.key_averages().table(
    sort_by="cuda_time_total",
    row_limit=20,
    max_name_width=60,
))

# Export for TensorBoard (can view locally)
prof.export_chrome_trace("/tmp/trace.json")
# View: chrome://tracing in Chrome/Chromium
```

### Memory Profiling

```python
torch.cuda.reset_peak_memory_stats()
torch.cuda.empty_cache()

# Before forward
before = torch.cuda.memory_allocated() / 1e9
peak_before = torch.cuda.max_memory_allocated() / 1e9

# Run model
output = model(input_ids)

# After forward
after = torch.cuda.memory_allocated() / 1e9
peak_after = torch.cuda.max_memory_allocated() / 1e9

print(f"Allocated: {before:.2f} → {after:.2f} GB")
print(f"Peak: {peak_before:.2f} → {peak_after:.2f} GB")
```

### Simple Timing

```python
# Warmup
for _ in range(3):
    model(input_ids)
torch.cuda.synchronize()

# Timed run
start = torch.cuda.Event(enable_timing=True)
end = torch.cuda.Event(enable_timing=True)
start.record()
output = model(input_ids)
end.record()
torch.cuda.synchronize()
print(f"Forward pass: {start.elapsed_time(end):.1f} ms")
```

---

## ROCm-Specific Patterns

### Environment Variables in Container

```bash
HSA_OVERRIDE_GFX_VERSION=11.5.1   # Required for gfx1151
HIP_FORCE_DEV_KERNARG=1            # Device kernarg allocation
ROCBLAS_USE_HIPBLASLT=1            # hipBLASLt for GEMM
HSA_XNACK=0                        # No XNACK on RDNA
HSA_ENABLE_SDMA=0                  # Disable SDMA
```

### torch.compile on ROCm

```python
# torch.compile works with ROCm but may be slow on first call
model = torch.compile(model, backend="inductor")

# Disable if causing issues
TORCH_COMPILE_DISABLE=1

# For dynamic shapes (common in LLM inference)
model = torch.compile(model, dynamic=True)
```

### Flash Attention

```python
# flash_attn is installed in container (2.8.4)
from flash_attn import flash_attn_func

# But for vLLM, use the Triton-based attention backend
# Flash Attention 2 may not work correctly on RDNA3.5 for all shapes
```

---

## Fine-Tuning (LoRA/QLoRA)

The container has `peft` and `bitsandbytes` for parameter-efficient fine-tuning:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, TaskType

model = AutoModelForCausalLM.from_pretrained(
    "/models/Qwen3.6-35B-A3B-AWQ-4bit",
    device_map="auto",
    trust_remote_code=True,
)

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "v_proj"],
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
```

---

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `HIP error: invalid device ordinal` | Multiple GPU indices | Use `HIP_VISIBLE_DEVICES=0` |
| `RuntimeError: No HIP GPUs are available` | Missing HSA override | Set `HSA_OVERRIDE_GFX_VERSION=11.5.1` |
| Triton kernel crash | gfx1151 not in supported list | Override GFX version (already set) |
| OOM with large models | ~96 GiB GPU-allocatable limit (GTT, of 128 GB unified) | Use quantization (AWQ/FP8) |
| `torch.compile` slow first call | Inductor JIT on ROCm | `TORCH_COMPILE_DISABLE=1` or accept warmup |
| NaN in loss | FP16 overflow | Use BF16 or GradScaler |
