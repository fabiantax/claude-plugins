---
name: casbin-ecosystem
description: Casbin Ecosystem Reference
---

# Casbin Ecosystem Reference

## Decision

**Chosen April 2026** for the Alies time-management platform. Casbin (Apache Foundation) over CASL, OpenFGA, SpiceDB, Cedar for multi-tenant RBAC.

**Why Casbin:** Native multi-tenant domains (tenant = domain), Apache governance, zero CVEs across 7+ years, Rust path for Scaleway serverless, PE-gradable marketplace architecture.

---

## Core Library — Language Ports

All under Apache Software Foundation (`apache/` on GitHub). Casbin is an Apache top-level project.

| Language | Repo | Stars | Version | Status |
|----------|------|-------|---------|--------|
| Go (original) | `apache/casbin` | 20,061 | — | Production |
| Node.js/TS | `apache/casbin-node-casbin` | 2,892 | 5.50.0 | Production (140K/wk npm) |
| Java | `apache/casbin-jcasbin` | 2,631 | — | Production |
| Python | `apache/casbin-pycasbin` | 1,728 | — | Production |
| Rust | `apache/casbin-rs` | 1,099 | 2.20.0 | Production (1.22M crate DL) |
| C#/.NET | `apache/casbin-Casbin.NET` | 1,312 | — | Production |
| PHP | `php-casbin/php-casbin` | 1,326 | — | Production |
| C++ | `apache/casbin-cpp` | 251 | — | Beta |
| Dart | `apache/casbin-dart-casbin` | 44 | — | Available |

---

## npm Packages (Node.js)

### Core
| Package | Version | Weekly DL | Notes |
|---------|---------|-----------|-------|
| `casbin` | 5.50.0 | 140K | Main engine. 157 published versions. |

### Official Adapters
| Package | Version | Weekly DL | DB | Notes |
|---------|---------|-----------|-----|-------|
| `typeorm-adapter` | 1.9.0 | 20.8K | MySQL, PG, SQLite, etc. | Most popular adapter |
| `drizzle-adapter` | 1.4.0 | 938 | PG, MySQL, SQLite | **We use this** (Turso/libSQL) |
| `casbin-prisma-adapter` | 1.12.0 | 6.2K | Prisma-supported DBs | |
| `casbin-mongoose-adapter` | 5.6.1 | 3.8K | MongoDB | |
| `casbin-sequelize-adapter` | 2.7.1 | 3.8K | SQL databases | Stale since 2023 |
| `casbin-basic-adapter` | 1.3.0 | — | SQLite/PG/MySQL via Knex | |

### Watchers (Real-Time Policy Sync)
| Package | Weekly DL | Backend |
|---------|-----------|---------|
| `@casbin/redis-watcher` | 5.8K | Redis Pub/Sub |
| `@casbin/mongo-changestream-watcher` | — | MongoDB Change Streams |

### Browser
| Package | Version | Weekly DL | Notes |
|---------|---------|-----------|-------|
| `casbin.js` | 1.1.0 | 4K | Official browser-side enforcement. Manual mode (set permissions) or auto mode (fetch from API) |

---

## Framework Middleware

### Node.js
| Package | Framework | Weekly DL | Notes |
|---------|-----------|-----------|-------|
| `fastify-casbin` | Fastify | 562 | NearForm, v4.0.0 |
| `fastify-casbin-rest` | Fastify (REST) | 294 | NearForm, RESTful model |
| `@hono/casbin` | Hono | 443 | Under @hono scope |
| `@midwayjs/casbin` | Midway.js | 497 | Official Midway component |
| `nest-authz` | NestJS | 1.4K | Official (`apache/casbin-nest-authz`) |
| `casbin-express-authz` | Express | 24 | Stale (2020) |

### Rust
| Package | Framework |
|---------|-----------|
| `casbin-axum-casbin` | Axum (69 stars) |
| `casbin-actix-casbin-auth` | Actix-web (58 stars) |

### Go
| Package | Framework |
|---------|-----------|
| `casbin-gin-example` | Gin |
| `casbin-negroni-authz` | Negroni (157 stars) |
| `casbin-caddy-authz` | Caddy web server (249 stars) |

### PHP
| Package | Framework |
|---------|-----------|
| `laravel-authz` | Laravel (327 stars) |
| `think-authz` | ThinkPHP (275 stars) |

### .NET
| Package | Framework |
|---------|-----------|
| `casbin-aspnetcore` | ASP.NET Core (76 stars) |

---

## Ecosystem Tools

| Tool | Stars | What | URL |
|------|-------|------|-----|
| **Casbin Editor** | 112 | Web-based model & policy editor | casbin-editor.apache.org |
| **Casbin Dashboard** | 89 | Admin portal for policy management | dashboard.casbin.com |
| **Casbin Gateway** | 559 | AI & MCP security gateway/WAF/proxy | `apache/casbin-gateway` |
| **Casbin Server** | 336 | "Casbin as a Service" (gRPC) | `apache/casbin-server` |
| **Casdoor** | 13,522 | Full IAM/SSO platform (OAuth, OIDC, SAML, LDAP, WebAuthn, MFA) | `casdoor/casdoor` |
| **K8s Gatekeeper** | 35 | Kubernetes admission webhook | `apache/casbin-k8s-gatekeeper` |
| **Docker Plugin** | 219 | Docker RBAC/ABAC authorization | `apache/casbin-docker-plugin` |
| **IntelliJ Plugin** | 29 | IDE plugin for .conf model files | `will7200/casbin-idea-plugin` |

---

## What Doesn't Exist

| Gap | Status |
|-----|--------|
| tRPC integration | None — DIY middleware calling `enforce()` |
| libSQL/Turso adapter | None — use `drizzle-adapter` with `drizzle-orm/libsql` |
| WASM build | None — `casbin.js` is closest (browser permissions only) |
| React wrapper (official) | None — `casbin.js` + custom `<Can>` component |
| `casbin-core` (universal JS) | Abandoned at beta |
| Swift port | None |

---

## Our Integration

### Packages Used
```
apps/api:       casbin + drizzle-adapter
apps/dashboard: casbin.js
```

### Adapter Setup (Turso/libSQL)
```typescript
import { drizzle } from 'drizzle-orm/libsql';
import { DrizzleAdapter } from 'drizzle-adapter';

const drizzleDb = drizzle(tursoClient);  // wrap existing libsql client
const adapter = await DrizzleAdapter.newAdapter({ db: drizzleDb });
```

### Model (RBAC with Domains)
```ini
[request_definition]
r = sub, dom, obj, act
[policy_definition]
p = sub, dom, obj, act
[role_definition]
g = _, _, _
[policy_effect]
e = some(where (p.eft == allow))
[matchers]
m = g(r.sub, p.sub, r.dom) && r.dom == p.dom && r.obj == p.obj && r.act == p.act
```

### casbin.js (Browser)
```typescript
import { CasbinJs } from 'casbin.js';
const authorizer = new CasbinJs({ mode: 'manual', permission: permissionMap });
authorizer.can('write', 'scan_event'); // true/false
```

### Future: Casdoor
If we outgrow custom JWT auth, Casdoor (13.5K stars) is the Casbin team's full IAM platform. Supports OAuth 2.0, OIDC, SAML 2.0, LDAP, WebAuthn, MFA. Drop-in replacement for our `AuthService`.

### Future: casbin-rs
For Scaleway Rust serverless functions, `casbin-rs` v2.20.0 supports tokio + RBAC with domains. Policy-compatible with Node.js port (same `casbin_rule` table schema).
