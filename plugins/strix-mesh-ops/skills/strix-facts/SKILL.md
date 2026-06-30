---
name: strix-facts
description: Verify the stale-prone facts about the Strix box LIVE before relying on them — credentials, inference ports, GPU carveout, OpenObserve logins. CLAUDE.md and memory drift; this runs the actual checks so you act on ground truth, not a stale line. Use before any task that depends on a credential, port, or capacity number.
---

# Strix facts — verify before you trust

CLAUDE.md and memories go stale (this is stated in CLAUDE.md itself). Several load-bearing
facts bit hard this session: a stale OpenObserve password (`MtpObserve2026!` → 401), a
decommissioned inference port (:8003), and a GPU carveout that had changed. **Run the check,
don't quote the doc.**

## One-shot verifier
```bash
# inference backends (live ports — :8002/:8003 are DECOMMISSIONED)
for p in 4099 3003 8005 8007 8004; do printf ":%s " "$p"; curl -s -o /dev/null -w "%{http_code} " --max-time 3 "http://127.0.0.1:$p/" 2>/dev/null; done; echo
mesh-health-probe                      # full inference-path + OO-cred verdict (if installed)

# OpenObserve logins (3 distinct — the doc's admin@local.dev:MtpObserve2026! is STALE)
#   strix :5080  → root@example.com:StrixObserve2026   (otel exports metrics here)
#   mac   :5080  → admin@local.dev:admin123456         (cto-hq scanner; mesh traces)
#   mesh acct    → fabian@raaf.local:raaf2026          (must exist as an OO user)
for c in "root@example.com:StrixObserve2026" "admin@local.dev:admin123456"; do
  printf "%s → " "${c%%:*}"; curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Basic $(printf %s "$c" | base64)" http://127.0.0.1:5080/api/default/streams; done

# GPU carveout (NOT a fixed split — verify; it has moved before)
cat /sys/class/drm/card1/device/mem_info_{vram,gtt}_total 2>/dev/null; free -g | awk '/Mem|Swap/'

# toolchain currency (a stale Mesa/ROCm silently costs perf)
rpm -q mesa-vulkan-drivers 2>/dev/null; ls -d /opt/rocm-* 2>/dev/null
```

## The facts most likely to be stale (and the live source of truth)
| Fact | Don't trust the doc — read | 
|---|---|
| OO password | the OO service/launchd args, or test the cred (`/streams` → 200) |
| inference ports | live probe; llama-swap `:8007` + router `:8005` are current; **:8002/:8003 are dead** |
| GPU VRAM/GTT split | `/sys/class/drm/card1/device/mem_info_*` (carveout is dynamic, has changed) |
| which model is on which port | `curl :8007/v1/models`, `:8007/running`, `:8005/health` |
| ROCm/Mesa version | `rpm -q` / `ls /opt/rocm-*` (CLAUDE.md has said 7.13 while host ran 7.2.1) |

## Rule
Cite the **source of every load-bearing claim** (command output or `file:line`). If you can't
point to where you verified it *now*, treat it as unverified and run the check first. Update
the doc when you find drift — don't silently route around it.
