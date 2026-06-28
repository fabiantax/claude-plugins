---
name: huggingface-workflow
description: HuggingFace Hub workflow for Strix Halo. Covers the hf CLI, model download/management, searching models, upload, and Hub API usage. Use when downloading, managing, or discovering models.
allowed-tools: Read Bash
---

# HuggingFace Hub Workflow — Strix Halo

---

## CLI Setup

```bash
# hf CLI (alias in ~/.bashrc)
hf --help

# Location: ~/code/ai/hf-env/bin/hf
# Version: 1.10.1
# Authenticated as: futurebreeze
```

---

## Downloading Models

```bash
# Full model download
hf download Qwen/Qwen3.6-35B-A3B-FP8 --local-dir ~/models/Qwen3.6-35B-A3B-FP8

# Partial download (specific files)
hf download unsloth/Qwen3.5-4B-GGUF \
  --include "*Q4_K_M*" \
  --local-dir ~/models/unsloth/Qwen3.5-4B-GGUF

# Resume interrupted download (just re-run — hf is idempotent)
hf download Qwen/Qwen3.6-35B-A3B-FP8 --local-dir ~/models/Qwen3.6-35B-A3B-FP8

# Check download progress
du -sh ~/models/<model-name>/
ls ~/models/<model-name>/*.safetensors | wc -l
```

### Download Speed

Xet protocol typically gets 5-20 MB/s. Large models (36 GB) take 30 min - 2 hours.
Run downloads in background: `nohup hf download ... > /tmp/hf-download.log 2>&1 &`

---

## Model Discovery

```bash
# Search via CLI
hf search models --author Qwen --sort downloads --limit 20

# Search specific model
hf model info Qwen/Qwen3.6-35B-A3B-FP8

# List downloaded models
ls ~/models/
```

### Checking Model Config Before Download

```bash
# Fetch just the config (fast)
hf download Qwen/Qwen3.6-35B-A3B-FP8 --include "config.json" --local-dir /tmp/model-check
cat /tmp/model-check/config.json | python3 -c "
import json, sys
c = json.load(sys.stdin)
print(f'Arch: {c.get(\"model_type\")}')
print(f'Quant: {c.get(\"quant_method\", \"none\")}')
print(f'Params: {c.get(\"num_hidden_layers\")} layers, {c.get(\"hidden_size\")} hidden')
print(f'Experts: {c.get(\"num_experts\", \"dense\")}')
"
rm -rf /tmp/model-check
```

---

## Model Management

```bash
# List all models with sizes
du -sh ~/models/*/

# Check model integrity
python3 -c "
from safetensors import safe_open
import glob
for f in glob.glob('/home/fabian/models/<model>/*.safetensors'):
    with safe_open(f, framework='pt') as sf:
        print(f'{f}: {len(sf.keys())} tensors')
"

# Delete model
rm -rf ~/models/<model-name>

# Switch active vLLM model
echo "<model-dir-name>" > ~/.config/vllm/current-model
systemctl --user restart vllm
```

---

## ROCm Compatibility Check

Before downloading, verify:

1. **Architecture**: Must be supported by vLLM or llama.cpp
2. **Quantization**: Must be ROCm-compatible (see `/model-quantization` skill)
3. **Size**: Must fit in the ~96 GiB GPU-allocatable budget (GTT, of 128 GB unified) — model + KV cache + overhead
4. **Trust remote code**: Some models need `--trust-remote-code`

### Quick Compatibility Check

```python
# Check if model uses CUDA-only features
import json
c = json.load(open("config.json"))
quant = c.get("quant_method", "")
if quant in ["gptq_marlin", "awq_marlin", "modelopt_fp4"]:
    print("WARNING: May not work on ROCm — NVIDIA-optimized backend")
```

---

## Hub API (Python)

The vLLM container has `huggingface_hub` installed:

```python
from huggingface_hub import ModelInfo, list_models, model_info

# Get model info
info = model_info("Qwen/Qwen3.6-35B-A3B-FP8")
print(f"Downloads: {info.downloads}")
print(f"Library: {info.library_name}")
print(f"Size: {info.safetensors.total if info.safetensors else 'unknown'}")

# Search models
models = list_models(
    search="qwen3 moe",
    sort="downloads",
    direction=-1,
    limit=10,
)
for m in models:
    print(f"{m.modelId}: {m.downloads} downloads")
```

---

## Directory Structure

```
~/models/
├── Qwen3-Coder-Next-AWQ-4bit/         # vLLM — active (46GB)
├── Qwen3.6-35B-A3B-AWQ-4bit/          # vLLM — MoE INT4 (14GB)
├── Qwen3.6-35B-A3B-FP8/               # vLLM — MoE FP8 (36GB, downloading)
├── Qwen3.5-27B-AWQ-4bit/              # vLLM — dense (14GB)
├── Qwen3.5-4B-AWQ-4bit/               # vLLM — small (2.5GB)
├── Qwen3.5-2B-AWQ-4bit/               # vLLM — tiny (1.5GB)
├── gemma-4-26B-A4B-it-AWQ-4bit/       # vLLM — multimodal MoE
├── gemma-4-31B-it-AWQ-4bit/           # vLLM — text dense
└── unsloth/
    ├── Qwen3.5-4B-GGUF/               # llama.cpp — Q4_K_M
    └── gemma-4-E4B-it-GGUF/           # llama.cpp — Q4_K_M
```

### Available Disk Space

```bash
df -h ~/models/
# Monitor during large downloads
watch -n 5 'du -sh ~/models/*/'
```
