---
name: model-quantization
description: Model quantization guide for Strix Halo. Covers AWQ, GPTQ, FP8, GGUF, and compressed-tensors formats. How to quantize models locally, evaluate quality, and choose the right format for vLLM/llama.cpp on ROCm.
allowed-tools: Read Bash
---

# Model Quantization — Strix Halo

---

## Formats Compatible with ROCm/gfx1151

| Format | Backend | vLLM | llama.cpp | Size Reduction | Quality |
|--------|---------|------|-----------|----------------|---------|
| AWQ 4-bit | compressed-tensors | Yes | No | ~4× | Good |
| GPTQ 4-bit | gptq/gptq_marlin | Yes (marlin may fail) | No | ~4× | Good |
| FP8 | fp8 | Yes | No | ~2× | Excellent |
| GGUF Q4_K_M | gguf | No | Yes | ~4× | Good |
| GGUF Q8_0 | gguf | No | Yes | ~2× | Very good |
| bitsandbytes NF4 | bitsandbytes | Yes (training) | No | ~4× | Good |
| MXFP4 | mxfp4 | Experimental | No | ~8× | Moderate |

### NOT Compatible (NVIDIA-only)

| Format | Why |
|--------|-----|
| NVFP4 | NVIDIA Blackwell (sm_120) only |
| modelopt_fp4 | NVIDIA-specific |
| FP8 per-tensor/block | May work but less tested on RDNA |

---

## Quantization Tools in Container

```bash
# AMD Quark (AMD's quantization toolkit)
podman exec vllm-server python3 -c "import quark; print(quark.__version__)"

# compressed-tensors (for AWQ-format models)
podman exec vllm-server python3 -c "import compressed_tensors; print(compressed_tensors.__version__)"

# bitsandbytes (for QLoRA/NF4)
podman exec vllm-server python3 -c "import bitsandbytes; print(bitsandbytes.__version__)"
```

---

## Quantizing a Model

### FP8 (Simplest, Best Quality)

```python
# Using llm-compressor or direct torch
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained(
    "/models/source-model",
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
)

# FP8 quantization (dynamic)
# vLLM handles FP8 quantization at load time for fp8 checkpoints
# For static FP8, use llm-compressor or AMD Quark
```

### INT4 AWQ (Best for Bandwidth-Limited)

```bash
# Using auto-awq (if installed)
# podman exec vllm-server python3 -m awq.entrypoint \
#   --model_path /models/source \
#   --w_bit 4 --q_group_size 32 \
#   --output_path /models/output-awq
```

### GGUF (for llama.cpp)

```bash
# Convert HF model to GGUF
# cd ~/code/tools/llama.cpp
# python3 convert_hf_to_gguf.py /models/source --outfile /models/output.gguf --outtype q4_k_m

# Quantize
# ./build/bin/llama-quantize /models/output-f16.gguf /models/output-q4_k_m.gguf Q4_K_M
```

---

## Quality Evaluation

### Perplexity (Gold Standard)

```bash
# Using llama.cpp
llama-perplexity -m /models/model.gguf -f /path/to/wikitext.txt --chunks 32

# Using lm-eval (if installed)
# lm_eval --model hf --model_args pretrained=/models/model --tasks wikitext
```

### Quick Quality Check

```python
# Generate samples and compare to original
import json
prompts = [
    "Explain the concept of trust in organizations.",
    "Write a Python function to compute Fibonacci numbers.",
    "Summarize the key findings of the Edmondson psychological safety paper.",
]

for prompt in prompts:
    response = call_vllm(prompt, model="quantized-model")
    print(f"Q: {prompt}\nA: {response}\n")
```

---

## Choosing a Format

```
Is the model > 30B params?
├── Yes → Use AWQ 4-bit or FP8 (fits in ~96 GiB GPU-allocatable, of 128 GB unified)
│   ├── Need best quality? → FP8 (~2× size)
│   └── Need smallest size? → AWQ 4-bit (~4× size)
└── No → Use GGUF Q4_K_M or Q8_0
    ├── Running vLLM? → AWQ 4-bit
    └── Running llama.cpp? → GGUF Q4_K_M
```

### MoE Models (Qwen3.6-35B-A3B)

MoE models are special — only 3B active params per token:
- **AWQ 4-bit**: ~14 GB total. Only quantize the active expert weights.
- **FP8**: ~36 GB total. Better quality, but 2.5× larger.
- **GGUF**: Poor MoE support in llama.cpp — expert dispatch overhead.

---

## Downloading Pre-Quantized Models

```bash
# Official Qwen (recommended — highest quality, verified)
hf download Qwen/Qwen3.6-35B-A3B-FP8 --local-dir ~/models/Qwen3.6-35B-A3B-FP8
hf download Qwen/Qwen3.6-35B-A3B-AWQ --local-dir ~/models/Qwen3.6-35B-A3B-AWQ

# Trusted community quants
hf download unsloth/Qwen3.5-4B-GGUF --include "*Q4_K_M*" --local-dir ~/models/unsloth/Qwen3.5-4B-GGUF
```

### Trusted Sources

| Provider | Trust Level | Notes |
|----------|------------|-------|
| Official org (Qwen, Google) | Highest | Official releases, verified |
| unsloth | High | Popular, well-maintained |
| bullpoint | Medium | Good AWQ quants |
| bartowski | Medium | Good GGUF quants |
| mradermacher | Medium | Wide variety of quants |

---

## Quantization Impact on Performance

| Format | Model Size | VRAM Used | tg/s (conc 4) | Quality Loss |
|--------|-----------|-----------|---------------|-------------|
| FP16 (full) | 72 GB | ~70 GB | ~25 | None (baseline) |
| FP8 | 36 GB | ~35 GB | ~30-35 | Negligible |
| AWQ 4-bit | 14 GB | ~14 GB | ~62 | Small (perplexity +0.1-0.3) |
| GPTQ 4-bit | 14 GB | ~14 GB | ~55-60 | Small (similar to AWQ) |

AWQ 4-bit is paradoxically faster than FP8 on this hardware because the memory bandwidth bottleneck means smaller model = faster inference, even with the dequantization overhead.
