---
name: toolbox-ml
description: Strix-llama toolbox for persistent ML work on Strix Halo. Covers setup, PyTorch installation, quantization, fine-tuning, evaluation, and when to use toolbox vs vLLM container. Use when doing long-running ML work that needs persistence.
allowed-tools: Read Bash
---

# Strix-llama Toolbox — Persistent ML Work

---

## When to Use Toolbox vs vLLM Container

| Task | Toolbox | vLLM Container |
|------|---------|----------------|
| Build C++/HIP/llama.cpp | Yes (persistent toolchain) | No |
| Fine-tuning (LoRA/QLoRA) | Yes (pip installs survive) | Risky (--rm) |
| Model quantization | Yes | Yes |
| Evaluation harnesses | Yes (long-running, persistent) | Possible |
| Inference services | No | Yes (systemd) |
| Custom HIP kernels | Yes (hipcc, amdclang) | No compiler |
| rocprof profiling | Yes | Limited |

---

## Environment

```bash
# Enter interactive shell
toolbox enter strix-llama

# Run single command
toolbox run -c strix-llama <command>

# Python
python3 --version   # 3.14.3

# ROCm
/opt/rocm-7.2.1/bin/rocm-smi
hipcc --version     # HIP 7.2.5
hipconfig --version
amdclang --version

# GPU
HSA_OVERRIDE_GFX_VERSION=11.5.1   # Required for gfx1151
```

### ROCm Packages Installed

```
rocm-core-7.2.1
rocm-hip-6.4.2
rocm-llvm-22.0.0
rocm-comgr-19
rocm-runtime-6.4.2
rocm-device-libs
```

---

## PyTorch Installation (One-Time)

The toolbox does NOT have PyTorch by default. Install it for fine-tuning, quantization, and evaluation:

```bash
toolbox run -c strix-llama bash -c "
  pip3 install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/rocm6.4
"
```

Then install ML dependencies:

```bash
toolbox run -c strix-llama bash -c "
  pip3 install \
    transformers accelerate datasets peft \
    lm-eval safetensors bitsandbytes \
    huggingface_hub scipy numpy pandas
"
```

Verify:

```bash
toolbox run -c strix-llama python3 -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'GPU: {torch.cuda.get_device_name(0)}')
print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
"
```

---

## Fine-Tuning in Toolbox

The toolbox is better for fine-tuning than the vLLM container because:
- pip installs persist (no need to reinstall on restart)
- Home directory is mounted (models in `~/models/` accessible)
- GPU access is automatic (no device flags needed)

```bash
toolbox run -c strix-llama python3 ~/code/ai/finetune.py \
  --model /home/fabian/models/Qwen3.6-35B-A3B-AWQ-4bit \
  --dataset /home/fabian/data/my-dataset.jsonl \
  --output /home/fabian/models/finetuned/
```

---

## Evaluation Harnesses

### lm-eval-harness

```bash
toolbox run -c strix-llama bash -c "
  lm_eval \
    --model hf \
    --model_args pretrained=/home/fabian/models/Qwen3.6-35B-A3B-AWQ-4bit,dtype=float16 \
    --tasks wikitext,hellaswag,mmlu \
    --batch_size auto \
    --output_path /home/fabian/data/lm-eval-results/
"
```

### Perplexity

```bash
toolbox run -c strix-llama python3 -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model = AutoModelForCausalLM.from_pretrained(
    '/home/fabian/models/Qwen3.6-35B-A3B-AWQ-4bit',
    device_map='auto', trust_remote_code=True
)
tokenizer = AutoTokenizer.from_pretrained(
    '/home/fabian/models/Qwen3.6-35B-A3B-AWQ-4bit'
)

# Quick perplexity on sample text
import math
with torch.no_grad():
    inputs = tokenizer('The quick brown fox jumps over the lazy dog.' * 50,
                       return_tensors='pt').to('cuda')
    loss = model(**inputs, labels=inputs['input_ids']).loss
    print(f'Perplexity: {math.exp(loss.item()):.2f}')
"
```

---

## Building Custom HIP Kernels

The toolbox has the full HIP compiler toolchain:

```bash
# Compile HIP kernel
toolbox run -c strix-llama hipcc \
  --offload-arch=gfx1151 \
  -o my_kernel my_kernel.hip

# Run
toolbox run -c strix-llama ./my_kernel
```

### Building llama.cpp (existing)

```bash
# Incremental build
toolbox run -c strix-llama bash -c "cd ~/code/tools/llama.cpp && cmake --build build -j\$(nproc)"

# Full reconfigure
toolbox run -c strix-llama bash -c "
  cd ~/code/tools/llama.cpp && rm -rf build &&
  cmake -B build -DGGML_HIP=ON -DGPU_TARGETS=gfx1151 \
    -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=ON \
    -DGGML_HIP_ROCWMMA_FATTN=ON \
    '-DCMAKE_HIP_FLAGS=-D__AMDGCN_WAVEFRONT_SIZE=32' &&
  cmake --build build -j\$(nproc) --target llama-server
"
```

---

## rocprof Profiling

The toolbox has rocprofv2 for kernel-level profiling:

```bash
# Profile a HIP binary
toolbox run -c strix-llama /opt/rocm-7.2.1/bin/rocprofv2 \
  --hip-trace --hsa-trace \
  -d ./output \
  ./my_kernel

# Profile Python (if PyTorch installed)
toolbox run -c strix-llama /opt/rocm-7.2.1/bin/rocprofv2 \
  --hip-trace \
  -d /tmp/rocprof-output \
  python3 /home/fabian/code/ai/profile_script.py
```

---

## Model Quantization in Toolbox

After installing PyTorch + transformers:

```bash
# AWQ quantization
toolbox run -c strix-llama python3 -m awq.entrypoint \
  --model_path /home/fabian/models/source-model \
  --w_bit 4 --q_group_size 32 \
  --output_path /home/fabian/models/output-awq

# Convert to GGUF (uses llama.cpp already built in toolbox)
toolbox run -c strix-llama python3 ~/code/tools/llama.cpp/convert_hf_to_gguf.py \
  /home/fabian/models/source-model \
  --outfile /home/fabian/models/output.gguf \
  --outtype f16

toolbox run -c strix-llama ~/code/tools/llama.cpp/build/bin/llama-quantize \
  /home/fabian/models/output-f16.gguf \
  /home/fabian/models/output-q4_k_m.gguf \
  Q4_K_M
```

---

## Installing Additional Packages

All pip installs in the toolbox persist across sessions:

```bash
# Install anything
toolbox run -c strix-llama pip3 install <package>

# Check what's installed
toolbox run -c strix-llama pip3 list

# Install from requirements
toolbox run -c strix-llama pip3 install -r /home/fabian/code/ai/requirements.txt
```

---

## Disk Usage

The toolbox shares the host filesystem. Check space before large operations:

```bash
df -h /home/fabian/models/
du -sh /home/fabian/models/*/
```

---

## Environment Variables

Set these for ML work in the toolbox:

```bash
export HSA_OVERRIDE_GFX_VERSION=11.5.1
export HIP_FORCE_DEV_KERNARG=1
export ROCBLAS_USE_HIPBLASLT=1
export HSA_XNACK=0
```

Add to `~/.bashrc` inside the toolbox for persistence:
```bash
toolbox run -c strix-llama bash -c 'cat >> ~/.bashrc << EOF
export HSA_OVERRIDE_GFX_VERSION=11.5.1
export HIP_FORCE_DEV_KERNARG=1
export ROCBLAS_USE_HIPBLASLT=1
export HSA_XNACK=0
export PATH=/opt/rocm-7.2.1/bin:\$PATH
EOF'
```
