---
name: preview
description: Open the fab-trader app in a browser via Tailscale or SSH port-forward. Shows charts, HQ dashboard, or any route.
argument-hint: "[charts/AAPL | hq | /] defaults to charts/AAPL"
---

# Preview fab-trader App

Open the running fab-trader API in a browser.

## Network paths

| Method | URL |
|--------|-----|
| **Tailscale (direct)** | `https://100.112.37.119:{port}/{path}` |
| **SSH port-forward** | `ssh -L {port}:127.0.0.1:{port} strix` then `https://localhost:{port}/{path}` |

## Quick routes

| Route | What |
|-------|------|
| `/charts/AAPL` | Charts SPA (candlestick + indicators) |
| `/charts/SPY` | Charts SPA for SPY |
| `/hq` | HQ Dashboard |
| `/health` | Health check JSON |
| `/regime` | Current regime JSON |
| `/screener/top` | Screener results |
| `/portfolio` | Portfolio state |

## Behavior

1. Check if the API is running: `curl -sk https://127.0.0.1:{port}/health`. Default port is 3001.
2. If not running, start it: `cd ~/Developer/personal/fab-trader/apps/api && API_PORT={port} pnpm dev` (background).
3. Print the Tailscale URL and the SSH port-forward command for the user's machine (MacBook `100.109.245.96`, iPhone `100.96.40.102`).
4. If the argument specifies a route, use that. Default: `/charts/AAPL`.

## Tailscale IPs

| Device | IP |
|--------|---|
| Strix (this machine) | `100.112.37.119` |
| MacBook | `100.109.245.96` |
| iPhone | `100.96.40.102` |

## Starting the server

```bash
cd ~/Developer/personal/fab-trader/apps/api && API_PORT=3001 pnpm dev
```

Server binds HTTPS on `0.0.0.0:{port}` with self-signed certs from `.ssl/`.
Browser will warn about self-signed cert — proceed anyway.

## SSH port-forward (from MacBook)

```bash
ssh -L 3001:127.0.0.1:3001 strix
# Then open https://localhost:3001/charts/AAPL
```
