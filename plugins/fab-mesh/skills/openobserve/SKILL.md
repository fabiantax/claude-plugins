---
name: openobserve
description: OpenObserve — Observability Platform
---

# OpenObserve — Observability Platform

## Overview

OpenObserve (O2) is the observability platform for this host — logs, metrics, and traces via OTLP. Single Rust binary, Parquet storage, 140x cheaper than Elasticsearch.

## Service

| What | Value |
|------|-------|
| Service file | `~/.config/systemd/user/openobserve.service` |
| Container image | `public.ecr.aws/zinclabs/openobserve:v0.90.3` |
| HTTP port | **5080** (web UI + REST API) |
| gRPC port | **5081** (OTLP ingestion) |
| Data dir | `/mnt/models/openobserve-data/` (symlinked from `~/.local/share/openobserve`) |
| Logs | `/tmp/openobserve.log` |
| Web UI | http://localhost:5080/web/login |

## Credentials

| Field | Value |
|-------|-------|
| Email | `root@example.com` |
| Password | `Complexpass#123` |

## Commands

```bash
# Service management
systemctl --user start openobserve
systemctl --user stop openobserve
systemctl --user restart openobserve
systemctl --user status openobserve
journalctl --user -fu openobserve

# Health check
curl -sf http://127.0.0.1:5080/web/login -o /dev/null && echo "OK" || echo "DOWN"

# Login (API)
curl -s http://127.0.0.1:5080/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"name":"root@example.com","password":"Complexpass#123"}'

# API calls (basic auth)
curl -s http://127.0.0.1:5080/api/default/streams \
  -u 'root@example.com:Complexpass#123'
```

## Important: Login Endpoint

The login endpoint is **`/auth/login`** (NOT `/api/login`). The JS bundle calls `sign_in_user` → `POST /auth/login` with `{"name": "<email>", "password": "<pass>"}`. Basic auth (`-u user:pass`) also works for API calls.

## OTLP Integration

### Atlas Telemetry

Atlas has built-in OTLP telemetry (gated by env var):

```bash
# Enable atlas telemetry → exports to OpenObserve
export ATLAS_TELEMETRY_ENABLED=1
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:5081
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic cm9vdEBleGFtcGxlLmNvbTpDb21wbGV4cGFzcyMxMjM=,organization=default"
```

The telemetry code is in `crates/atlas-cli/src/telemetry.rs` — uses tonic gRPC to export traces.

**IMPORTANT**: OpenObserve requires two headers on the gRPC endpoint:
1. `Authorization: Basic <base64(email:password)>` — for authentication
2. `organization: default` — to specify the org (O2 default org)

Without these headers, O2 silently rejects traces with `InvalidArgument: Please specify organization id with header key 'organization'`. The `OTEL_EXPORTER_OTLP_HEADERS` env var is the standard way to pass these — the `opentelemetry-otlp` crate reads it automatically and applies them as gRPC metadata.

### OTLP Endpoints

| Protocol | Address | Notes |
|----------|---------|-------|
| gRPC | `127.0.0.1:5081` | Primary — used by Atlas tonic exporter |
| HTTP | `127.0.0.1:5080/api/{org}/traces` | OTLP/HTTP (protobuf body) |

### Sending Traces from Other Services

For any service with OTLP support:
- Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:5081`
- Set `OTEL_EXPORTER_OTLP_PROTOCOL=grpc` (default)
- For HTTP: `OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:5080`
- Organization: `default` (the initial org created by root user)

## Querying

### Log Search (SQL)
```bash
# Search logs via API
curl -s "http://127.0.0.1:5080/api/default/_search" \
  -u 'root@example.com:Complexpass#123' \
  -H 'Content-Type: application/json' \
  -d '{"query":{"sql":"SELECT * FROM default LIMIT 10"}}'
```

### Stream Types
- **Logs**: `api/{org}/streams?type=logs`
- **Traces**: `api/{org}/streams?type=traces`
- **Metrics**: `api/{org}/streams?type=metrics`

## Architecture Notes

- **Single binary** — no Elasticsearch/Zookeeper needed
- **SQLite metadata** — `/mnt/models/openobserve-data/db/metadata.sqlite`
- **Parquet data files** — `/mnt/models/openobserve-data/streaming/{org}/`
- **Schema migration** — auto-migrates on startup (DB_SCHEMA_VERSION check)
- **Memory** — sets disk cache 3.4 GB, memory cache 15.6 GB, datafusion pool 23.5 GB based on 62 GB RAM

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Invalid credentials" | Wrong endpoint | Use `/auth/login`, not `/api/login` |
| 401 on API calls | Missing auth | Add `-u 'root@example.com:Complexpass#123'` |
| Container crash on start | Password too weak | Password needs special char (`#`, `!`, etc.) |
| Port already in use | Old container | `podman rm -f openobserve` then restart |
| Data corruption | Version mismatch | `rm -rf /mnt/models/openobserve-data/*` (fresh start) |

## Registry Info

| Registry | Image | Notes |
|----------|-------|-------|
| `public.ecr.aws/zinclabs/openobserve` | ✅ Works | Public ECR, OSS edition |
| `docker.io/openobserve/openobserve` | ⚠️ Broken | Points to v0.91.0-rc1 with broken auth |
| `o2cr.ai/openobserve/openobserve-enterprise` | ❌ Auth required | Needs login |

## Version

Currently: **v0.90.3** (stable). Check latest: `curl -s https://api.github.com/repos/openobserve/openobserve/releases | python3 -c "import json,sys;[print(r['tag_name']) for r in json.load(sys.stdin)[:5]]"`
