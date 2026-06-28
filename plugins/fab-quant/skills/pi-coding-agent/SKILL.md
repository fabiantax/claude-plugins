---
name: pi-coding-agent
description: Reference for the Pi coding agent (pi-mono by Mario Zechner) — installation, provider setup, extensions, skills, settings, and strix-specific config. Use when setting up Pi, configuring providers, writing extensions, or troubleshooting Pi on this machine.
allowed-tools: Read, Bash, Glob, Grep
---

# Pi Coding Agent — Strix Halo Reference

Pi is an open-source terminal AI coding agent (like Claude Code but provider-agnostic and minimal).
Homepage: https://github.com/badlogic/pi-mono

---

## Installation

Pi is not installed globally on strix — run it via bunx:

```bash
bunx @mariozechner/pi-coding-agent [options] [prompt]
```

Or install globally:

```bash
bun install -g @mariozechner/pi-coding-agent
```

---

## Providers on Strix

| Provider | Status | How |
|----------|--------|-----|
| Local vLLM (:8000) | Needs `registerProvider` in extension | OpenAI-compatible, baseUrl `http://127.0.0.1:8000/v1` |
| GitHub Copilot | Available, needs OAuth | `bunx @mariozechner/pi-ai login copilot` |
| z.ai | Check Pi model list | `--provider z` or similar |
| Ollama (:11434) | Via registerProvider | OpenAI-compatible, baseUrl `http://127.0.0.1:11434/v1` |
| llama-server (:8001) | Via registerProvider | OpenAI-compatible, baseUrl `http://127.0.0.1:8001/v1` |
| Anthropic | Via API key | `ANTHROPIC_API_KEY=... --provider anthropic` |

### Registering a local provider in an extension:

```typescript
pi.registerProvider("vllm", {
  baseUrl: "http://127.0.0.1:8000/v1",
  apiKey: "dummy",
  api: "openai-completions",
  models: [{ id: "Qwen3-Coder-Next-AWQ-4bit", contextWindow: 32768, maxOutputTokens: 8192 }],
})
```

---

## CLI Flags

```
pi [options] [@files...] [prompt]

--provider <name>              Provider (default: google)
--model <pattern>              Model ID or "provider/id"
--api-key <key>                API key
--print, -p                    Non-interactive, process and exit
--continue, -c                 Continue previous session
--resume, -r                   Select session to resume
--extension, -e <path>         Load extension file (repeatable)
--no-extensions, -ne           Disable auto-discovered extensions
--list-models                  List all available models
```

---

## Extensions

Extensions are TypeScript modules with a default export `(pi: ExtensionAPI) => void`.

### Installation

```bash
# Global (auto-loaded)
pi install ~/.pi/agent/extensions/my-ext.ts

# List installed
pi list

# Remove
pi remove ~/.pi/agent/extensions/my-ext.ts
```

### Extension API

```typescript
import type { ExtensionFactory } from "@mariozechner/pi-coding-agent"

const extension: ExtensionFactory = (pi) => {
  // Events
  pi.on("session_start",    async (event, ctx) => { /* ctx.cwd, ctx.model */ })
  pi.on("tool_call",        async (event, ctx) => { /* event.toolName, event.input, event.toolCallId */ })
  pi.on("tool_result",      async (event, ctx) => { /* event.toolName, event.isError, event.content */ })
  pi.on("agent_end",        async (event, ctx) => { /* event.messages */ })
  pi.on("turn_end",         async (event, ctx) => { /* event.turnIndex, event.message */ })
  pi.on("session_shutdown", async (event, ctx) => { })

  // Register a provider
  pi.registerProvider("local", { baseUrl: "...", apiKey: "x", api: "openai-completions", models: [...] })

  // Register a tool
  pi.registerTool(defineTool({ name: "mytool", ... }))

  // Register a slash command
  pi.registerCommand("mycommand", { description: "...", run: async (ctx) => { } })
}

export default extension
```

### Key event shapes

| Event | Key fields |
|-------|-----------|
| `session_start` | `event.reason` ("startup"\|"resume"\|"fork") |
| `tool_call` | `event.toolName`, `event.input`, `event.toolCallId` |
| `tool_result` | `event.toolName`, `event.isError`, `event.content`, `event.details` |
| `agent_end` | `event.messages` (full AgentMessage[]) |
| `turn_end` | `event.turnIndex`, `event.message`, `event.toolResults` |

**Important:** Extensions run via Node.js/jiti, NOT Bun. Use `node:sqlite` not `bun:sqlite`.

---

## Settings

Global: `~/.pi/agent/settings.json`  
Project: `.pi/settings.json`

```json
{
  "defaultProvider": "anthropic",
  "defaultModel": "claude-sonnet-4-5",
  "packages": ["extensions/moshi-hooks.ts"],
  "extensions": ["~/.pi/agent/extensions/my-ext.ts"],
  "compaction": { "enabled": true, "reserveTokens": 4000 }
}
```

---

## Installed Extensions on Strix

| Extension | Path | What it does |
|-----------|------|-------------|
| `moshi-hooks` | `~/.pi/agent/extensions/moshi-hooks.ts` | Logs events to `~/.local/share/moshi-hooks/events.db` + Moshi push notifications |

---

## Moshi Integration

The moshi-hooks extension mirrors Claude Code's behaviour:
- `tool_call` → "Running bash/edit/write/grep/find" notification
- `tool_result` → "Finished / Failed <tool>" notification  
- `agent_end` → "Task Complete" notification with last assistant message
- Token: `MOSHI_TOKEN` env var (set in `~/.bashrc.d/99-secrets.sh`), fallback `~/.config/moshi/token`
- DB: `~/.local/share/moshi-hooks/events.db` — shared with Claude Code, queryable with:

```bash
bun -e "
import {Database} from 'bun:sqlite';
const db = new Database(process.env.HOME+'/.local/share/moshi-hooks/events.db');
console.log(db.query('SELECT datetime(ts/1000,\"unixepoch\") as time, event_type, title, message, project_name FROM hook_events ORDER BY ts DESC LIMIT 20').all());
"
```

---

## Known Issues on Strix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Cannot find module 'bun:sqlite'` | Extensions run in Node, not Bun | Use `node:sqlite` (`DatabaseSync`) |
| `ParseError: Unexpected token` in extension | Trailing comma in `.run([...])` | Use `stmt.run(a, b, c)` spread form |
| Pi hits OpenAI despite `OPENAI_BASE_URL` | Pi ignores that env var | Use `registerProvider` in extension or Pi settings |
| `401 Incorrect API key` | No local provider registered | Register vLLM via `registerProvider` in extension |
