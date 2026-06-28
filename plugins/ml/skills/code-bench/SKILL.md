---
name: code-bench
description: Code generation and software engineering benchmarks for Strix Halo. Covers lm-evaluation-harness, MultiPL-E (Rust/TypeScript/C#), Multi-SWE-bench, SWE-Sharp-Bench (C#), and how to build a personal SWE-bench from your own codebase. Use when evaluating coding quality.
allowed-tools: Read Bash Write
---

# Code Benchmark Guide — Strix Halo

**Stack:** llama-server :8001 (GGUF), vLLM :8000 (AWQ)  
**Languages of interest:** C#, Blazor, Rust, TypeScript

---

## Tier 1: lm-evaluation-harness (easiest, local API)

Supports OpenAI-compatible endpoints directly.

```bash
pip install lm-evaluation-harness

# HumanEval — Python function completion, pass@1
lm_eval \
  --model local-chat-completions \
  --model_args model=Qwen3.5-4B-Q4_K_M.gguf,base_url=http://127.0.0.1:8001/v1,num_concurrent=4 \
  --tasks humaneval \
  --output_path ~/evals/results/

# Multiple tasks at once
lm_eval \
  --model local-chat-completions \
  --model_args model=Qwen3.5-4B-Q4_K_M.gguf,base_url=http://127.0.0.1:8001/v1 \
  --tasks humaneval,gsm8k,mmlu \
  --output_path ~/evals/results/
```

### Adding custom tasks (YAML + JSONL)

```yaml
# ~/evals/tasks/blazor_tasks.yaml
task: blazor_codegen
dataset_path: /home/fabian/evals/datasets/blazor_tasks.jsonl
dataset_name: default
output_type: generate_until
doc_to_text: "{{prompt}}"
doc_to_target: "{{canonical_solution}}"
generation_kwargs:
  until: ["```\n", "</razor>"]
  max_gen_toks: 1024
metric_list:
  - metric: exact_match
    aggregation: mean
```

```jsonl
// ~/evals/datasets/blazor_tasks.jsonl — one task per line
{"prompt": "Create a Blazor component that shows a loading spinner while IsLoading is true.", "canonical_solution": "@if (IsLoading) {\n  <div class=\"spinner\"></div>\n}\n@code {\n  [Parameter] public bool IsLoading { get; set; }\n}"}
{"prompt": "Write a Blazor EventCallback<T> parameter named OnSelected that fires when a row is clicked.", "canonical_solution": "[Parameter] public EventCallback<TItem> OnSelected { get; set; }"}
```

Run with custom task:
```bash
lm_eval \
  --model local-chat-completions \
  --model_args model=Qwen3.5-4B-Q4_K_M.gguf,base_url=http://127.0.0.1:8001/v1 \
  --tasks blazor_codegen \
  --include_path ~/evals/tasks/ \
  --output_path ~/evals/results/
```

---

## Tier 2: MultiPL-E (Rust, TypeScript, C#, 18 languages)

Translates HumanEval to 18 languages. Uses Podman for safe execution.

```bash
git clone https://github.com/nuprl/MultiPL-E ~/evals/MultiPL-E
cd ~/evals/MultiPL-E
pip install aiohttp numpy tqdm pytest datasets

# Pull execution container (uses Podman, already on this machine)
podman pull ghcr.io/nuprl/multipl-e-evaluation:latest
podman tag ghcr.io/nuprl/multipl-e-evaluation:latest multipl-e-eval
```

### Generate completions

```bash
cd ~/evals/MultiPL-E

# TypeScript
python3 automodel_vllm.py \
  --name Qwen3.5-4B-Q4 \
  --root-dataset humaneval \
  --lang ts \
  --completion-limit 20 \
  --batch-size 10 \
  --temperature 0.2 \
  --model http://127.0.0.1:8001/v1   # OpenAI-compat

# Rust
python3 automodel_vllm.py \
  --name Qwen3.5-4B-Q4 \
  --root-dataset humaneval \
  --lang rs \
  --completion-limit 20 \
  --batch-size 10
```

### Execute and score

```bash
podman run --rm \
  -v $(pwd)/results:/results:z \
  multipl-e-eval \
  --dir /results/Qwen3.5-4B-Q4-humaneval-ts \
  --output /results/Qwen3.5-4B-Q4-humaneval-ts-results.json
```

### Add your own problems

```jsonl
// ~/evals/MultiPL-E/datasets/mycompany-ts-problems.jsonl
{
  "name": "mycompany/parse_config_ts",
  "language": "TypeScript",
  "prompt": "// Parse a TOML config string into a Record<string,string>\nfunction parseConfig(input: string): Record<string, string> {\n",
  "tests": "const result = parseConfig('key=val\\nfoo=bar');\nconsole.assert(result['key'] === 'val');\nconsole.assert(result['foo'] === 'bar');",
  "stop_tokens": ["\n}"],
  "entry_point": "parseConfig"
}
```

---

## Tier 3: Multi-SWE-bench (Rust, TypeScript — real issue resolution)

**Paper:** [2504.02605](https://hf.co/papers/2504.02605) — Apr 2025, 2132 instances, mini=400

```bash
git clone https://github.com/multi-swe-bench/multi-swe-bench ~/evals/multi-swe-bench
cd ~/evals/multi-swe-bench
pip install -e .

# Dataset on HuggingFace: Daoguang/Multi-SWE-bench
# mini version: Daoguang/Multi-SWE-bench-mini (400 instances, 8 languages)
```

**Requirements:** Docker, 120GB disk, ~8 CPU cores for parallel evaluation.  
**Realistic on this machine:** Run mini (400 instances) with `--max_workers 4`.

---

## Tier 3: SWE-Sharp-Bench (C# only)

**Paper:** [2511.02352](https://hf.co/papers/2511.02352) — Nov 2025, Microsoft Research  
**Specifically for C#** — first benchmark of its kind for .NET issue resolution.

Check for dataset release:
```bash
# Dataset may be at: https://github.com/microsoft/SWE-Sharp-Bench
# or: huggingface.co/datasets/microsoft/SWE-Sharp-Bench
```

---

## Tier 3: CRUST-Bench (C → safe Rust)

**Paper:** [2504.15254](https://hf.co/papers/2504.15254)  
Tests transpilation from C to idiomatic, memory-safe Rust.

```bash
# Dataset: https://github.com/anirudhkhatry/CRUST-bench
git clone https://github.com/anirudhkhatry/CRUST-bench ~/evals/crust-bench
```

Can extend with your own C functions that you want transpiled to safe Rust.

---

## Personal SWE-bench — build from your real PRs

The most valuable benchmark: your own codebase, your own bugs.

### Instance format

```jsonl
{
  "instance_id": "myapp-{language}-{number}",
  "repo": "mycompany/repo-name",
  "language": "csharp",
  "problem_statement": "One-paragraph description of the bug, same as you'd write in a GitHub issue",
  "patch": "--- a/src/Components/DataTable.razor\n+++ b/src/Components/DataTable.razor\n@@ -45,6 +45,9 @@\n...",
  "test_patch": "// xUnit test that fails before patch, passes after",
  "difficulty": "easy|medium|hard",
  "tags": ["blazor", "null-safety", "pagination"]
}
```

### Extraction script

```bash
# ~/evals/extract-swe-instances.sh
# Extracts recent bug-fix PRs from a git repo into SWE-bench format

REPO_PATH="${1:?Usage: $0 <repo-path> [output.jsonl]}"
OUTPUT="${2:-/home/fabian/evals/datasets/personal-swe.jsonl}"

cd "$REPO_PATH"

# Find commits with "fix" in message
git log --oneline --grep="fix\|bug\|error\|crash" --since="1 year ago" | while read sha msg; do
  # Get the diff for this commit
  diff=$(git show "$sha" --unified=5 -- "*.cs" "*.razor" "*.ts" "*.rs" 2>/dev/null)
  [ -z "$diff" ] && continue

  # Get parent commit message as problem statement
  pr_body=$(git log -1 --format="%B" "$sha")

  python3 -c "
import json, sys
print(json.dumps({
  'instance_id': 'personal-${sha:0:8}',
  'repo': '$(basename $REPO_PATH)',
  'language': 'mixed',
  'problem_statement': sys.argv[1],
  'patch': sys.argv[2],
  'difficulty': 'unknown'
}))" "$pr_body" "$diff" >> "$OUTPUT"
done

echo "Extracted to $OUTPUT"
```

### Running a personal eval

```python
# ~/evals/run-personal-swe.py
import json, time
from openai import OpenAI

client = OpenAI(api_key="dummy", base_url="http://127.0.0.1:8001/v1")

with open("/home/fabian/evals/datasets/personal-swe.jsonl") as f:
    instances = [json.loads(l) for l in f]

results = []
for inst in instances:
    prompt = f"""You are a software engineer. Fix the following bug.

Repository: {inst['repo']}
Language: {inst['language']}

Issue:
{inst['problem_statement']}

Provide a unified diff patch that fixes the issue."""

    start = time.time()
    resp = client.chat.completions.create(
        model="Qwen3.5-4B-Q4_K_M.gguf",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.2,
    )
    elapsed = time.time() - start

    results.append({
        "instance_id": inst["instance_id"],
        "predicted_patch": resp.choices[0].message.content,
        "gold_patch": inst["patch"],
        "time_s": elapsed,
        "tokens": resp.usage.completion_tokens,
        "tg_s": resp.usage.completion_tokens / elapsed,
    })

# Save for manual review
with open("/home/fabian/evals/results/personal-swe-results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"Ran {len(results)} instances")
print(f"Avg tg/s: {sum(r['tg_s'] for r in results)/len(results):.1f}")
```

---

## Benchmark comparison table

| Benchmark | C# | Blazor | Rust | TypeScript | Setup | Run time |
|-----------|----|---------|----- |-----------|-------|----------|
| lm-eval HumanEval | ❌ | ❌ | ❌ | ❌ | pip install | ~30min |
| lm-eval custom YAML | ✅ | ✅ | ✅ | ✅ | YAML+JSONL | ~1hr setup |
| MultiPL-E | ✅ | ❌ | ✅ | ✅ | Podman | ~2hr setup |
| Multi-SWE-bench mini | ❌ | ❌ | ✅ | ✅ | Docker | ~1 day |
| SWE-Sharp-Bench | ✅ | ✅ | ❌ | ❌ | Docker | ~1 day |
| Personal SWE-bench | ✅ | ✅ | ✅ | ✅ | git log | your call |

---

## Key finding from quantization research

From [2409.11055](https://hf.co/papers/2409.11055):  
**Quantized larger models outperform smaller fp16 models** on most coding tasks.  
→ Run Q4_K_M 35B-A3B over fp16 4B for both speed AND quality.
