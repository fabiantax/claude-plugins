---
name: gpu-bench-pipeline
description: Fast experiment pipeline for optimizing llama.cpp and vLLM for new models. Covers benchmark scripts, experiment flow, and batching optimization on ROCm/RDNA.
allowed-tools: Read Bash
---

# GPU Benchmark & Experiment Pipeline — Strix Halo

---

## Quick Experiment Flow

When a new model lands, follow this sequence:

```
1. Download → 2. Smoke test → 3. Baseline bench → 4. Tune flags → 5. Batch bench → 6. Log results
     5 min        2 min          5 min            15 min        10 min         2 min
```

Total: ~40 minutes from download to optimized config.

---

## Step 1: Download & Verify

```bash
# Download model
hf download <org>/<model> --local-dir ~/models/<model-name>

# Verify config
cat ~/models/<model-name>/config.json | python3 -c "
import json, sys
c = json.load(sys.stdin)
print(f'Architecture: {c.get(\"model_type\", \"?\")}')
print(f'Hidden: {c.get(\"hidden_size\", \"?\")}')
print(f'Layers: {c.get(\"num_hidden_layers\", \"?\")}')
print(f'Quant: {c.get(\"quant_method\", \"none\")}')
print(f'MoE experts: {c.get(\"num_experts\", \"N/A\")}')
print(f'Active experts: {c.get(\"num_experts_per_tok\", \"N/A\")}')
print(f'MTP heads: {c.get(\"mtp_num_hidden_layers\", 0)}')
print(f'Max position: {c.get(\"max_position_embeddings\", \"?\")}')
print(f'Vocab: {c.get(\"vocab_size\", \"?\")}')
"

# Calculate model size
du -sh ~/models/<model-name>/
```

---

## Step 2: Smoke Test

### vLLM (port 8000)

```bash
# Switch model
echo "<model-dir-name>" > ~/.config/vllm/current-model
systemctl --user restart vllm

# Wait for ready
until curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; do sleep 2; done

# Smoke test
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"default","messages":[{"role":"user","content":"Say hello."}],"max_tokens":10,"chat_template_kwargs":{"enable_thinking":false}}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
```

### llama.cpp (port 8001)

```bash
# Find GGUF file
ls ~/models/<model-dir>/*.gguf

# Start server
llama-server-strix -m ~/models/<model-dir>/<file>.gguf &

# Smoke test
curl -s http://127.0.0.1:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Say hello."}],"max_tokens":10}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
```

---

## Step 3: Baseline Benchmark

### Throughput at Concurrency Levels

Save as `/tmp/bench-model.sh`:

```bash
#!/usr/bin/env bash
API="${1:-http://127.0.0.1:8000}"
LEVELS="${2:-1 2 4 8}"
MODEL="${3:-default}"
PROMPT="Write a concise 3-sentence summary of team dynamics in software engineering."

for N in $LEVELS; do
  echo -n "  Conc $N: "
  START=$(date +%s%N)
  PIDS=()
  for i in $(seq 1 $N); do
    curl -s "$API/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"$PROMPT\"}],\"max_tokens\":128,\"temperature\":0.7,\"chat_template_kwargs\":{\"enable_thinking\":false}}" \
      -o /tmp/conc-$i.json &
    PIDS+=($!)
  done
  for pid in "${PIDS[@]}"; do wait $pid; done
  END=$(date +%s%N)
  TOTAL_TOKENS=0
  for i in $(seq 1 $N); do
    TOK=$(python3 -c "import json; d=json.load(open('/tmp/conc-$i.json')); print(d.get('usage',{}).get('completion_tokens',0))" 2>/dev/null || echo 0)
    TOTAL_TOKENS=$((TOTAL_TOKENS + TOK))
  done
  ELAPSED=$(( (END - START) / 1000000 ))
  if [ "$ELAPSED" -gt 0 ]; then
    TPS=$(python3 -c "print(f'{$TOTAL_TOKENS / ($ELAPSED/1000):.1f}')")
    echo "${TPS} tg/s (${TOTAL_TOKENS} tokens in ${ELAPSED}ms)"
  else
    echo "too fast (${TOTAL_TOKENS} tokens)"
  fi
done
```

### Context Scaling (llama.cpp)

```bash
~/ctx-bench.sh <model> 64  # PP + TG at 10k→64k context steps
```

### Agent Scenario (multi-turn)

```bash
~/blazor-bench.sh  # Sequential + batched + 2-coder/1-reviewer
```

---

## Step 4: Flag Tuning Checklist

### vLLM Flags to Try (one at a time)

| Flag | Default | Try | Effect |
|------|---------|-----|--------|
| `--max-num-batched-tokens` | auto | 8192, 16384, 32768 | Token budget per iteration |
| `--max-num-seqs` | auto | 16, 32, 64 | Max concurrent sequences |
| `--gpu-memory-utilization` | 0.9 | 0.85, 0.92, 0.95 | KV cache size |
| `--kv-cache-dtype` | auto | fp8 | Halves KV cache memory |
| `--speculative-config` | none | `{"method":"mtp","num_speculative_tokens":3}` | If model supports MTP |
| `--mamba-ssm-cache-dtype` | auto | float16 | For Mamba-hybrid models |
| `--attention-backend` | auto | ROCM_AITER_FA (may crash) | Faster attention if compatible |
| `--enable-chunked-prefill` | false | true | Interleave prefill with decode |
| `--enable-prefix-caching` | false | true | Share KV blocks for common prefixes |

### llama.cpp Flags to Try

| Flag | Default | Try | Effect |
|------|---------|-----|--------|
| `--flash-attn` | off | on | rocWMMA flash attention |
| `-t` | auto | 8, 16 | CPU threads for PP |
| `-ngl` | 999 | 999 | All layers on GPU |
| `-c` | 512 | 32768 | Context size |
| `--batch-size` | 512 | 512, 1024 | Prompt batch size |
| `-ctk` | f16 | q8_0, q4_0 | KV cache type |

---

## Step 5: Batching Optimization

For multi-agent creature simulations (5 agents, 8 rounds):

### Key Insight: Continuous Batching Throughput

```
Single request:  27 tg/s × 1 req = 27 tokens/s total
4 concurrent:    62 tg/s × 4 req = 248 tokens/s total (9.2× single)
8 concurrent:    91 tg/s × 8 req = 728 tokens/s total (27× single)
```

The GPU is memory-bandwidth bound. More concurrent requests = more work done per VRAM fetch.

### Batching Strategy

1. **Batch all think requests**: Send all agent think prompts in one vLLM batch call
2. **Batch all react requests**: Send all reaction prompts in one batch
3. **Use shared system prompts**: Prefix caching deduplicates common system prompt blocks
4. **Minimize max_tokens**: Use 256-512 for reactions, 512 for thoughts (not 2048)

### Code Pattern

```typescript
// Send N requests in parallel via vLLM continuous batching
async function batchChat(requests: ChatRequest[]): Promise<ChatResult[]> {
  return Promise.all(
    requests.map(req =>
      fetch("http://127.0.0.1:8000/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "default",
          messages: [
            { role: "system", content: req.systemPrompt },
            { role: "user", content: req.userPrompt },
          ],
          max_tokens: req.maxTokens,
          temperature: 0.7,
          chat_template_kwargs: { enable_thinking: false },
        }),
      }).then(r => r.json())
    )
  );
}
```

---

## Step 6: Log Results

Update memory file at:
`~/.claude/projects/-home-fabian-Developer-personal-Alies-time-management/memory/vllm-moe-tuning.md`

Format:
```
| Conc | Config | tg/s | Notes |
|------|--------|------|-------|
| 1    | INT4+MTP | 31.3 | Baseline |
| 4    | INT4+MTP | 61.9 | Baseline |
```

---

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `~/blazor-convo.sh` | 5-turn conversation benchmark | `~/blazor-convo.sh` |
| `~/blazor-bench.sh` | Agent scenario benchmark | `~/blazor-bench.sh` |
| `~/ctx-bench.sh` | Context scaling PP+TG | `~/ctx-bench.sh <model> [max_k]` |
| `/tmp/bench-model.sh` | Concurrent throughput | `/tmp/bench-model.sh [api] [levels] [model]` |
