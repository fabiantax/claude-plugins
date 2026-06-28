---
name: bifrost
description: "Bifrost LLM gateway (maximhq/bifrost v1.5.13) reference — feature surface, host topology, tier routing, semantic cache, and operational commands. Use when working with the :3003 gateway, debugging routing/cache, adding providers, or editing zai-shim tier routing."
triggers: [bifrost, gateway, semantic cache, zai-shim, glm-5.2, local_qwen, gemma-4-26b, :3003]
---

# Bifrost LLM Gateway

Unified OpenAI-compatible LLM gateway fronting **all** LLM traffic on this host. Replaced the archived TensorZero on 2026-06-14. Path: **Claude Code → zai-shim (:4099, Anthropic Messages→OpenAI) → Bifrost (:3003) → providers**. The zai-shim is the single cutover/rollback point.

- **Image:** `docker.io/maximhq/bifrost:v1.5.13` (Go, fasthttp, Apache-2.0)
- **Port:** 3003 (default 8080 is taken by sqld)
- **Service:** `bifrost-gateway.service` (podman `--network host`)

---

## Feature surface (upstream v1.5.13)

### Routing & providers
- **Unified OpenAI-compatible API** across all providers — drop-in base-URL swap for OpenAI/Anthropic/Google SDKs.
- **23+ provider integrations:** OpenAI, Anthropic, AWS Bedrock, Google Vertex, Azure, Cerebras, Cohere, Mistral, Ollama, Groq, + custom OpenAI-compatible.
- **Custom OpenAI-compatible providers** via `base_provider_type: openai` + `base_url` (how all 5 local/remote providers are wired here).
- **Model aliasing** — `aliases` field renames a model *within* a provider.

### Reliability & resilience
- **Automatic fallbacks** — provider/model failover (configured per-model).
- **Load balancing** — weighted API-key selection across keys/providers (~10 ns weighted pick).
- **Request retries** with configurable backoff (`governance.retry_backoff_initial/max`).
- Sub-100 µs overhead at 5k RPS; 100% success rate under sustained 5k RPS.

### Caching
- **Semantic caching plugin** — responses cached by embedding similarity (the feature TensorZero couldn't deliver; working here). Direct-hit ~8 ms, paraphrase ~6 ms, miss ~16 s.
- Per-request cache key, TTL, model/provider scoping.

### Streaming & modalities
- **Full SSE streaming** for `/v1/chat/completions`.
- **Multimodal** — text, images, audio behind a common interface.

### Governance (cost/security)
- Virtual keys, usage tracking, rate limiting, hierarchical budgets.
- Auth config (disabled here — `disable_auth_on_inference: true`).

### Observability
- **Native Prometheus `/metrics`** (scraped by otel-collector → OpenObserve as `bifrost_*` streams).
- Distributed tracing, request logging, transaction log (`/api/transactions`).
- Web UI + three config paths: Web UI, management API, file-based seed.

### Plugins & extensibility
- Plugin architecture (types: `llm`, `http`). **Real built-ins** (per source `plugins.go`): *auto-loaded* `telemetry`, `compat` · *conditional* `logging`, `governance`, `prompts`, `modelcatalogresolver` · *opt-in* `semantic_cache` (active), `otel` (added + persisted in `config.db`, traces-only → otel-collector :4318 → OpenObserve), `maxim`. **There is NO `mocking` or `JSON parsing` plugin** — an earlier list claimed those; they do not exist in Bifrost.
- **Gotcha — `http`-type plugins need a gateway *restart* after hot-add.** `POST /api/plugins` for `otel` (an `http`-type plugin) returns 201 + status `active` and persists to `config.db`, but it is NOT wired into the running request middleware chain (built at server start) — so it emits no spans until `systemctl --user restart bifrost-gateway`. Tell-tale: Bifrost log lines already carry a `trace_id`, but the collector's debug exporter shows zero `Traces` (only its own `Metrics`).
- **MCP** integration (model tool-use).

> **Enterprise-gated (not on this OSS deployment):** adaptive load balancer, cluster mode, guardrails, OIDC/OAuth login, MCP gateway. The OSS image carries the full routing + cache + telemetry surface.

---

## Host topology (this deployment)

| Layer | What | Where |
|---|---|---|
| Gateway | Bifrost :3003 | `bifrost-gateway.service` (podman `--network host`) |
| Protocol shim | Anthropic→OpenAI translation, **tier routing lives here** | zai-shim :4099 (`~/.local/share/litellm-proxy/zai-shim.py`) |
| Vector store | RediSearch for semantic cache (needs `FT.*`, NOT plain valkey) | `bifrost-valkey.service` → `redis/redis-stack:latest` :3033 |
| Embeddings | **jina-embeddings-v5-text-nano** (768-dim, 8K ctx; served under alias `bge-small-en-v1.5`), cache source | `bifrost-embeddings.service` :8006 |
| Telemetry | scrape `/metrics` → OpenObserve | otel-collector (`prometheus/bifrost` receiver) |

### Config persistence (load-bearing gotcha)
- `~/.config/bifrost/config.json` is **SEED-ONLY** after first boot.
- Live config (incl. plugin config) persists in **`/app/data/config.db` (SQLite)** inside the container.
- **Edit plugins via the management API**, not the JSON — JSON edits don't update a running plugin.

### Providers configured here

| Provider | base_url | Models | Backend |
|---|---|---|---|
| `zai-coding` | `api.z.ai/api/coding/paas/v4` | `glm-5.2`, `glm-5.1` | remote Z.AI (heavy tier) |
| `mimo` | `token-plan-ams.xiaomimimo.com/v1` | `mimo-v2.5*` | remote Xiaomi (key may be quota-exhausted) |
| `local-qwen` | `127.0.0.1:8005/v1` | `local_qwen35` | llama-router → :8002/:8003 |
| `local-gemma` | `127.0.0.1:8004/v1` | `gemma-4-26b` | local llama-server |
| `embeddings` | `127.0.0.1:8006/v1` | `bge-small-en-v1.5` (alias; actually jina-v5-nano, 768-dim) | cache embedding source |

### Tier routing (in zai-shim `map_model()`, one model→one provider)
| Claude Code tier | Resolves to | Provider |
|---|---|---|
| `claude-opus-*` / `claude-fable-*` / default | `glm-5.2` | zai-coding (remote) |
| `claude-sonnet-*` | `local_qwen35` | local-qwen (:8005 router) |
| `claude-haiku-*` | `gemma-4-26b` | local-gemma (:8004) |

---

## API endpoints (gateway :3003)

| Endpoint | Purpose |
|---|---|
| `GET /health` | Gateway health (`{"components":{"db_pings":"ok"}}`) |
| `GET /v1/models` | Resolvable models |
| `POST /v1/chat/completions` | OpenAI-compatible chat (SSE streaming supported) |
| `POST /v1/embeddings` | OpenAI-compatible embeddings |
| `GET /metrics` | Prometheus exposition |
| `GET /api/plugins` | List plugins |
| `GET /api/plugins/semantic_cache` | Live semantic-cache config |
| `PUT /api/plugins/semantic_cache` | **Update cache config (live + persisted)** |
| `GET /api/providers` | Provider state |
| `GET /api/transactions` | Request log |
| `GET /api/config` | Live config |

---

## Semantic cache (active)

Live config (via mgmt API — this is the source of truth, not config.json):
```json
{
  "provider": "embeddings",
  "embedding_model": "bge-small-en-v1.5",
  "dimension": 768,
  "threshold": 0.82,
  "ttl": "1h",
  "default_cache_key": "bifrost-default",
  "cache_by_model": true,
  "cache_by_provider": true,
  "exclude_system_prompt": false,
  "conversation_history_threshold": 6
}
```
**Three mandatory pieces** (all must be right or caching silently no-ops): (a) `default_cache_key` set, (b) an embeddings provider named in `provider`, (c) `dimension` matching the embedding model.

**Embedding model (2026-06-16):** the `:8006` server now runs **`jina-embeddings-v5-text-nano`** (text-matching, 768-dim, 8K ctx, `--pooling last`), replacing bge-small-en-v1.5 (which capped at 512 tokens → silently skipped caching for any prompt >512). The model is served under the **`--alias bge-small-en-v1.5`** so the provider + `embedding_model` name didn't have to change (a clean rename is a pending follow-up). Changing dimension 384→768 required the index rebuild (gotcha #4 below).

**`exclude_system_prompt: false`** means the full system prompt is embedded — inflates input length (more `>8K` skips) and can cause cross-persona cache hits. Left as-is deliberately (flipping to `true` is the smaller-input/better-semantics option but risks serving one persona's answer to another). Watch the gateway log for `input … too large` to decide.

---

## Operational commands

```bash
# Lifecycle
systemctl --user restart bifrost-gateway zai-shim   # restart gateway + shim
systemctl --user status bifrost-gateway
journalctl --user -fu bifrost-gateway               # logs

# Health / models
curl -sf http://127.0.0.1:3003/health
curl -sf http://127.0.0.1:3003/v1/models

# Semantic cache config (live)
curl -sf http://127.0.0.1:3003/api/plugins/semantic_cache | jq

# Metrics
curl -sf http://127.0.0.1:3003/metrics | grep -E 'bifrost_cache|http_requests_total'

# Probe a tier directly (bypass zai-shim)
curl -s http://127.0.0.1:3003/v1/chat/completions \
  -d '{"model":"glm-5.2","messages":[{"role":"user","content":"ping"}],"max_tokens":50}'
```

---

## Critical gotchas (cost hours to rediscover — full detail in memory `tensorzero_local_offload_routing.md`)

1. **`models:["*"]` on multiple providers = weighted-random ambiguity.** Each provider must list ONLY its own models, or a request lands on the wrong backend.
2. **Bifrost hardcodes `/v1/chat/completions`.** Every provider needs `custom_provider_config.request_path_overrides` → `{"chat_completion":"/chat/completions","chat_completion_stream":"/chat/completions"}` or the path doubles (`/v4/v1/...` → 404).
3. **config.json is seed-only after first boot.** Edit plugins via `PUT /api/plugins/...`, not the JSON.
4. **Changing `dimension` requires dropping the RediSearch index first:** `redis-cli FT.DROPINDEX BifrostSemanticCachePlugin`, flush `BifrostSemanticCachePlugin:*`, restart gateway. Else silent misindex (`num_docs:0`).
5. **redis-stack required** (not plain valkey) for `FT.*` — on :3033.
6. **OpenObserve metrics path is `/api/default/v1/metrics`** (not `/metrics` — 404s).
7. **Needs `--network host`** — the link-local `host.containers.internal` (169.254.1.2) is blocked by Bifrost's SSRF guard.

---

## Rollback (to TensorZero, <2 min)

1. zai-shim.py: `GATEWAY_BASE_URL` default `:3003`→`:3002`, path `/v1/chat/completions`→`/openai/v1/chat/completions`, MODEL_MAP values back to `tensorzero::model_name::…`.
2. `systemctl --user restart zai-shim`.
3. `systemctl --user enable --now tensorzero-gateway tensorzero-postgres tensorzero-ui` (units still on disk).

---

## Proven working (post-cutover 2026-06-14)
- All 3 Claude tiers route correctly (opus→glm-5.2, sonnet→qwen, haiku→gemma).
- Semantic cache: direct hit ~8 ms, paraphrase hit ~6 ms, miss ~16 s. `num_docs` increments.
- Metrics stream into OpenObserve with full labels (provider, model, `routing_engine_used`).
- Mimo key is quota-exhausted (account state) — routing works, content returns 429.
