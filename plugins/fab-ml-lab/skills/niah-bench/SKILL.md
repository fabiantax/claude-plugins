---
name: niah-bench
description: Needle-in-a-Haystack benchmark setup and customization for Strix Halo. Covers classic NIAH, NoLiMa (reasoning-based), and replacing synthetic filler with real codebases. Use when testing long-context retrieval quality.
allowed-tools: Read Bash Write
---

# Needle-in-a-Haystack Benchmark — Strix Halo

**API endpoint:** `http://127.0.0.1:8001` (llama-server) or `http://127.0.0.1:8000` (vLLM)

---

## Why NIAH matters for coding assistants

Classic NIAH: can the model find "The secret passphrase is FOOBAR" in 50k tokens of filler?  
**Code NIAH:** can the model find a specific bug/function/interface buried in your real codebase?

Modern models pass classic NIAH easily at ≤32k context. The hard tests are:
- **NoLiMa** — needle requires *reasoning*, not string matching
- **Code haystack** — your actual repo as context, not Lorem Ipsum
- **Multi-hop** — answer requires connecting two facts in different parts of the context

---

## Setup

```bash
# Install in a venv
python3 -m venv ~/evals/niah-env
source ~/evals/niah-env/bin/activate
pip install openai tiktoken matplotlib seaborn pandas numpy

git clone https://github.com/gkamradt/LLMTest_NeedleInAHaystack ~/evals/niah
```

---

## Quick run — classic NIAH against llama-server

```python
# ~/evals/run-niah.py
import os
from needlehaystack.llmtest import LLMNeedleHaystackTester

tester = LLMNeedleHaystackTester(
    model_provider="openai",
    model_name="Qwen3.5-4B-Q4_K_M.gguf",      # matches llama-server model id
    openai_api_key="dummy",                     # llama-server doesn't check
    api_base="http://127.0.0.1:8001/v1",
    context_lengths_min=10000,
    context_lengths_max=128000,
    context_lengths_num_intervals=8,            # 10k, 27k, 44k, 61k, 78k, 95k, 112k, 128k
    document_depth_percent_intervals=10,        # 10%, 20% ... 100% depth
    results_version=1,
    save_results=True,
    print_ongoing_status=True,
)
tester.start_test()
```

```bash
source ~/evals/niah-env/bin/activate
python ~/evals/run-niah.py
```

Output: JSON results + heatmap PNG in `~/evals/niah/results/`

---

## Code haystack NIAH — use your real codebase

Replace synthetic filler (Paul Graham essays) with your actual source files:

```python
# ~/evals/run-niah-code.py
import os, glob
from needlehaystack.llmtest import LLMNeedleHaystackTester

# Build haystack from real C#/Blazor source
def load_code_haystack(root: str, extensions=("*.cs", "*.razor", "*.ts", "*.rs")) -> str:
    files = []
    for ext in extensions:
        files.extend(glob.glob(f"{root}/**/{ext}", recursive=True))
    files.sort()
    corpus = ""
    for f in files:
        try:
            content = open(f).read()
            corpus += f"\n\n// File: {f}\n{content}"
        except Exception:
            pass
    return corpus

haystack = load_code_haystack("/home/fabian/myproject")

# Needle: a real fact buried in the code
# Examples:
#   "The DeleteUser endpoint does not validate the admin role before deleting"
#   "The rate limit for /api/search is 100 requests per minute, configured in RateLimitPolicy.cs"
#   "The DataTable component uses IQueryable<T> not IEnumerable<T> for server-side paging"

needle = "The secret API key for the payment gateway is stored in PaymentConfig.cs line 42"

tester = LLMNeedleHaystackTester(
    model_provider="openai",
    model_name="Qwen3.5-4B-Q4_K_M.gguf",
    openai_api_key="dummy",
    api_base="http://127.0.0.1:8001/v1",
    haystack_text=haystack,                  # override with real code
    needle=needle,
    retrieval_question="What is the secret API key location?",
    context_lengths_min=10000,
    context_lengths_max=64000,
    context_lengths_num_intervals=6,
    document_depth_percent_intervals=5,
    results_version=2,
    save_results=True,
)
tester.start_test()
```

---

## NoLiMa — harder, no literal match

NoLiMa (Feb 2025, [2502.05167](https://hf.co/papers/2502.05167)) uses needles where the answer requires *inference*, not retrieval.

Example — classic NIAH needle:
> "The magic word is ZEPHYR."  
> Question: "What is the magic word?"  
> *(model just needs to find and copy)*

NoLiMa-style needle:
> "Alice's pet is a dog. Dogs are mammals."  
> Question: "What type of animal is Alice's pet?"  
> *(model must chain: pet→dog→mammal)*

For code:
```python
# NoLiMa-style code needle
needle = """
// AuthService.cs line 89
// Note: admin check is skipped when request comes from localhost
if (!request.IsLocal) { CheckAdminRole(user); }
"""
retrieval_question = "Under what network condition is the admin role check bypassed?"
# Model must reason: IsLocal → localhost → bypass, not just find "IsLocal"
```

Install NoLiMa:
```bash
pip install git+https://github.com/adobe-research/NoLiMa
```

---

## Thinking mode comparison

Run the same NIAH test with thinking ON and OFF:

```python
# In your NIAH runner, send two variants per cell:
# 1. prompt ends with "/no_think" — Qwen3.5 fast mode
# 2. prompt normal — thinking enabled

def query_with_thinking(prompt, thinking=True):
    suffix = "" if thinking else " /no_think"
    resp = client.chat.completions.create(
        model="Qwen3.5-4B-Q4_K_M.gguf",
        messages=[{"role": "user", "content": prompt + suffix}],
        max_tokens=200,
        temperature=0.0,
    )
    return resp.choices[0].message.content, resp.usage.completion_tokens

# Expected: thinking mode helps at large context (harder retrieval)
# Expected: no_think is faster and sufficient at short context
```

---

## Heatmap interpretation

```
Context size (tokens) →  10k   27k   44k   61k   78k   95k  112k  128k
Depth (needle position)
10% (near top)          ████  ████  ████  ███   ██    ██    █     █
50% (middle)            ████  ████  ███   ██    ██    █     █     ░
90% (near bottom)       ████  ███   ██    ██    █     ░     ░     ░

█ = correct retrieval  ░ = failed
```

- Degradation at large context + deep position = KV cache attention decay
- If thinking mode fills in the ░ cells → thinking helps for long-context retrieval
- If no improvement → model's context window is the real limit

---

## Visualize results

```bash
source ~/evals/niah-env/bin/activate
cd ~/evals/niah
jupyter notebook viz/CreateVizFromLLMTesting.ipynb
```

Or generate PNG directly:
```bash
python viz/CreateVizFromLLMTesting.py --results_dir results/
```

---

## Context size vs model limits

| Model | Max ctx (trained) | Practical llama-server ctx | Flash attn needed |
|-------|------------------|--------------------------|-------------------|
| Qwen3.5-4B Q4_K_M | 262k | 128k (with `-ctk q4_0`) | yes |
| Gemma 4 E4B Q4_K_M | 128k | 64k | yes |
| Qwen3-Coder-Next (vLLM) | 32k | 32k | yes (fp8 KV) |

For NIAH above 32k on llama-server: always use `--flash-attn on` and quantized KV cache:
```bash
nohup toolbox run -c strix-llama ~/code/tools/llama.cpp/build/bin/llama-server \
    --host 0.0.0.0 --port 8001 --flash-attn on \
    --ctx-size 131072 --n-gpu-layers 999 \
    -ctk q4_0 -ctv q4_0 \
    -m ~/models/unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf \
    > /tmp/llama-server.log 2>&1 &
```
