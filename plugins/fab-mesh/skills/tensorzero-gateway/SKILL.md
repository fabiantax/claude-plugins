---
name: tensorzero-gateway
description: Manage the TensorZero LLM gateway on strix (port 3002) — fronts Z.AI GLM, Xiaomi Mimo, local llama.cpp, and (when key is ready) Anthropic. Use when switching models, adding providers, troubleshooting routing, or wiring clients to the gateway.
allowed-tools: Read Bash
---

# tensorzero-gateway — LLM gateway management

Manage the TensorZero gateway on strix (port 3002) that replaced LiteLLM as the
unified LLM gateway. TensorZero is a Rust-based gateway with sub-millisecond
p99 overhead, TOML configuration, and an OpenAI-compatible endpoint.

---

## Architecture

```
Claude Code (Anthropic SDK)
        │
        ▼
  ┌──────────────────────────┐
  │ zai-shim :4099           │  Anthropic→OpenAI protocol bridge
  │ Anthropic Messages API   │  - lifts system messages
  │    ↔ OpenAI Chat Compl.  │  - converts request/response shapes
  │ MODEL_MAP: model aliases │  - handles streaming (SSE) both ways
  └──────┬───────────────────┘
         │
         ▼
  ┌──────────────────────────┐
  │ tensorzero-gateway :3002 │  Rust gateway, <1ms p99 latency
  │ /openai/v1/chat/...      │  OpenAI-compatible endpoint
  └──────┬───────────────────┘
         │ routes by model_name (tensorzero::model_name::<name>)
    ┌────┼────────────┬──────────────────┐
    ▼    ▼            ▼                  ▼
┌──────┐ ┌──────┐ ┌─────────────┐  ┌──────────────┐
│Z.AI  │ │Mimo  │ │Anthropic    │  │llama-router  │
│coding│ │direct│ │(commented   │  │:8005         │
│endpoint│      │ │ out, no key)│  ├──────────────┤
└──────┘ └──────┘ └─────────────┘  │  coder :8002 │
                                  │  mesh  :8003 │
                                  └──────────────┘

Hermes / agents / scripts ──► TensorZero :3002 (direct, OpenAI protocol)
```

| Port | Service | Role |
|------|---------|------|
| `:3002` | tensorzero-gateway | Unified OpenAI-compatible gateway — ALL traffic routes here |
| `:4099` | zai-shim | Anthropic→OpenAI protocol bridge for Claude Code only |
| `:8005` | llama-router | Local Qwen3.6-35B MTP/batched router |
| `:8002` | llama-server-coder | Local Qwen3.6-35B-A3B MTP single-stream |
| `:8003` | llama-server-mesh | Local Qwen3.6-35B-A3B batched (np=4) |

---

## Providers

| Model Name | Provider | Type | Notes |
|-----------|----------|------|-------|
| `glm_5_1` | Z.AI | openai | Z.AI coding endpoint, `max_tokens` required |
| `glm_5_turbo` | Z.AI | openai | Z.AI coding endpoint |
| `glm_5` | Z.AI | openai | Z.AI coding endpoint |
| `mimo_v2_5` | Xiaomi | openai | Thinking model, needs >=200 `max_tokens` |
| `mimo_v2_5_pro` | Xiaomi | openai | Thinking model |
| `mimo_v2_pro` | Xiaomi | openai | |
| `local_qwen35` | llama-router | openai | Thinking model, needs >=200 `max_tokens` |

All models are accessed via the OpenAI-compatible endpoint using the model ID
`tensorzero::model_name::<name>` (e.g. `tensorzero::model_name::glm_5_1`).

---

## Service management

```bash
# Status
systemctl --user status tensorzero-gateway
systemctl --user status zai-shim           # still needed for Claude Code

# Restart (pick up config changes)
systemctl --user restart tensorzero-gateway
systemctl --user restart zai-shim

# Logs
journalctl --user -fu tensorzero-gateway    # gateway logs
journalctl --user -fu zai-shim              # shim logs
tail -f ~/.local/share/litellm-proxy/zai-shim.log   # shim request log

# Start full stack
systemctl --user start zai-shim tensorzero-gateway

# Health check
curl http://127.0.0.1:3002/status
```

---

## Config

### File locations

| File | Purpose |
|------|---------|
| `~/.config/tensorzero/tensorzero.toml` | Gateway config — models, providers, functions |
| `~/.config/systemd/user/tensorzero-gateway.service` | systemd unit |
| `~/.bashrc.d/99-secrets.sh` | API keys (`ZAI_API_KEY`, `MIMO_API_KEY`) |
| `~/.local/share/litellm-proxy/zai-shim.py` | Anthropic→OpenAI protocol bridge (Claude Code → TensorZero) |
| `~/.config/systemd/user/zai-shim.service` | Shim systemd unit |

### Config structure (TOML)

```toml
[gateway]
bind_address = "0.0.0.0:3002"

# Model definition: name + routing chain
[models.<model_name>]
routing = ["<provider_id>"]

# Provider: type + credentials
[models.<model_name>.providers.<provider_id>]
type = "anthropic" | "openai"
api_base = "<url>"
model_name = "<upstream_model_id>"
api_key_location = "env::<ENV_VAR>" | "none"

# Optional: default function for simple clients
[functions.default_chat]
type = "chat"
[functions.default_chat.variants.<variant_name>]
type = "chat_completion"
model = "<model_name>"
max_tokens = 8192
```

### Key env vars (from `~/.bashrc.d/99-secrets.sh`)

| Var | Purpose |
|-----|---------|
| `ZAI_API_KEY` | Z.AI API key |
| `MIMO_API_KEY` | Xiaomi Mimo API key |
| `ANTHROPIC_API_KEY` | _(not yet set)_ Direct Anthropic access |

---

## Claude Code integration

Claude Code uses the Anthropic SDK and sends Messages API requests. TensorZero
exposes an OpenAI-compatible endpoint. The zai-shim on port 4099 bridges the
two protocols:

1. Claude Code sends an **Anthropic Messages API** request to `:4099`
2. zai-shim translates it to an **OpenAI Chat Completions** request
3. zai-shim forwards to **TensorZero on :3002** (which routes to the provider)
4. The OpenAI response is translated back to **Anthropic Messages API** format
5. Streaming (SSE) is translated in both directions

The shim also handles model name mapping via its `MODEL_MAP` dict:
`claude-sonnet-4-20250514` maps to `tensorzero::model_name::glm_5_1` (default),
or explicit aliases like `glm-5.1`, `mimo-v2.5`, `local-qwen35`.

```bash
# Claude Code env (already configured)
export ANTHROPIC_BASE_URL=http://localhost:4099
```

For all other clients (agents, scripts, curl), use TensorZero directly:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:3002/openai/v1
# No API key needed for local gateway
```

---

## Testing

```bash
# Gateway status
curl http://127.0.0.1:3002/status

# Chat completion — Z.AI GLM 5.1
curl -s http://127.0.0.1:3002/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"tensorzero::model_name::glm_5_1","messages":[{"role":"user","content":"Say hi"}],"max_tokens":50}'

# Chat completion — Mimo
curl -s http://127.0.0.1:3002/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"tensorzero::model_name::mimo_v2_5","messages":[{"role":"user","content":"Say hi"}],"max_tokens":200}'

# Chat completion — local Qwen
curl -s http://127.0.0.1:3002/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"tensorzero::model_name::local_qwen35","messages":[{"role":"user","content":"Say hi"}],"max_tokens":200}'

# Smoke test — all models
for m in glm_5_1 glm_5_turbo mimo_v2_5 local_qwen35; do
  echo -n "$m: "
  curl -sf http://127.0.0.1:3002/openai/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"tensorzero::model_name::$m\",\"messages\":[{\"role\":\"user\",\"content\":\"reply ok\"}],\"max_tokens\":20}" \
    | jq -r '.choices[0].message.content // "FAIL"' 2>/dev/null || echo "FAIL"
done
```

---

## Adding a new provider

1. **Edit tensorzero.toml** — add model and provider sections:
   ```toml
   [models.my_new_model]
   routing = ["my_provider"]

   [models.my_new_model.providers.my_provider]
   type = "openai"
   api_base = "https://api.example.com/v1"
   model_name = "model-id"
   api_key_location = "env::MY_PROVIDER_KEY"
   ```

2. **Add API key** to `~/.bashrc.d/99-secrets.sh`:
   ```bash
   export MY_PROVIDER_KEY=sk-xxxxx
   ```

3. **Restart**:
   ```bash
   systemctl --user restart tensorzero-gateway
   ```

4. **Test**:
   ```bash
   curl -s http://127.0.0.1:3002/openai/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"tensorzero::model_name::my_new_model","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
   ```

---

## Adding Anthropic when key is ready

The config already has a commented-out section. Uncomment and set the key:

```toml
[models.claude_sonnet_4]
routing = ["anthropic_direct"]

[models.claude_sonnet_4.providers.anthropic_direct]
type = "anthropic"
model_name = "claude-sonnet-4-20250514"
api_key_location = "env::ANTHROPIC_API_KEY"
```

Then add the key:
```bash
echo 'export ANTHROPIC_API_KEY=sk-ant-xxxxx' >> ~/.bashrc.d/99-secrets.sh
source ~/.bashrc.d/99-secrets.sh
systemctl --user restart tensorzero-gateway
```

---

## TensorZero UI (optional)

TensorZero provides a web UI for monitoring requests, testing models, and
viewing metrics. Runs on port 4000 via docker compose.

```bash
# Start the UI (requires docker compose)
cd ~/.config/tensorzero
docker compose up -d tensorzero-ui

# Access at http://localhost:4000
```

The UI is optional — all management can be done via config file and curl.

---

## TensorZero Autopilot

TensorZero Autopilot is an automated AI engineer that uses TensorZero's
observability to iteratively improve prompts and model configurations.
See https://tensorzero.com/docs/autopilot for setup.

---

## How to switch models

TensorZero uses model names directly in requests. No config change needed to
switch — just change the model name in the request body:

```bash
# Use GLM 5.1
-d '{"model":"tensorzero::model_name::glm_5_1",...}'

# Switch to Mimo
-d '{"model":"tensorzero::model_name::mimo_v2_5",...}'

# Switch to local
-d '{"model":"tensorzero::model_name::local_qwen35",...}'
```

For the default function (used by simple clients that don't specify a model),
change the variant in `tensorzero.toml`:

```toml
[functions.default_chat.variants.glm_5_1]
type = "chat_completion"
model = "glm_5_1"   # change this to any model name
max_tokens = 8192
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Connection refused :3002 | tensorzero-gateway not running | `systemctl --user start tensorzero-gateway` |
| 422 from Z.AI on system messages | Client sends system-in-messages | shim (:4099) hoists them automatically; direct TensorZero clients must use top-level `system` field |
| 401 from provider | API key expired/wrong | Update in `~/.bashrc.d/99-secrets.sh`, restart gateway |
| Model not found (400) | Not in tensorzero.toml | Add model+provider sections, restart |
| Empty content from Mimo | All tokens used for reasoning | Increase `max_tokens` to >=200 |
| Empty content from local Qwen | Thinking model used all tokens | Increase `max_tokens` to >=200 |
| Slow responses on local model | llama-server down | Check `systemctl --user status llama-server-coder` |
| Gateway OOM | Unlikely (Rust, ~30MB) | `MemoryMax=512M` in service; restart if needed |
| Claude Code 422 errors | Shim not running or wrong port | Set `ANTHROPIC_BASE_URL=http://localhost:4099`, check `systemctl --user status zai-shim` |

### Diagnostic commands

```bash
# Gateway health
curl http://127.0.0.1:3002/status

# Full stack status
systemctl --user status tensorzero-gateway zai-shim llama-router --no-pager

# Check upstream shim (for Claude Code)
tail -20 ~/.local/share/litellm-proxy/zai-shim.log

# Check llama-router backend health
curl -sf http://127.0.0.1:8005/health | jq .

# Check gateway logs for routing errors
journalctl --user -u tensorzero-gateway --since "5 min ago" --no-pager
```
