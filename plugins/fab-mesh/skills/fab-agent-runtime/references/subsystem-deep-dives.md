# Mesh Subsystem Details

## Reflection Flow (detailed)

```
Agent consult → dispatcher.dispatch()
  → leaf handler produces draft parts
  → if config.reflect === true:
    → dispatcher.maybeReflectParts()
      → reflection.runReflection()
        → A2AClient.callSkill("reflect", JSON.stringify(envelope))
          → mesh-reflector (port 50281) evaluates draft
          → returns {verdict, findings, revised_draft?}
      → if APPROVE/ERROR: emit original draft
      → if REVISE + revised_draft: emit revised draft
      → if REVISE without revised_draft:
        → re-run leaf handler with findings appended to persona file
      → persistReflectionEvent() to sqld reflection_events table
```

## Subprocess Handler Internals

### Watchdog Architecture
- `idle_ms`: Reset on every stdout line. Fires when no line received for N ms.
- `total_ms`: Wall-clock ceiling. Fires regardless of activity.
- Both timers run independently. First to fire kills the subprocess.
- Legacy `timeout_ms` maps to `total_ms` when `total_ms` is unset.

### Stdin/stdout Protocol
1. Dispatcher writes full `TransportMessage` to subprocess stdin (always)
2. Subprocess reads from stdin (the pi shim extracts prompt text)
3. Subprocess emits NDJSON lines to stdout
4. Lines with `type: "system"` / `type: "assistant"` / `type: "result"` are parsed as events
5. On subprocess exit: if no `type: "result"` event seen, `parseStdout` fallback handles:
   - Single JSON object → `{type: "data", data: <parsed>}` Part
   - JSON array → Part[] verbatim
   - Non-JSON text → `{type: "text", text: <raw>}` Part

### Streaming vs Send
- `message/stream`: Uses `runSubprocessStream` with per-event callback
- `message/send`: Uses `runSubprocess` (collects all stdout, no streaming)

## Routing (`handler.type: routed`)

```yaml
handler:
  type: routed
  default: mtp
  rules:
    - if: { length_lte: 500 }
      use: mtp
    - if: { length_gte: 501 }
      pool:
        - use: mtp
          when: { in_flight: 0 }
        - use: batched
  backends:
    mtp:
      type: subprocess
      exec: pi-fab-agent-runtime
      args: [...]
    batched:
      type: subprocess
      exec: pi-fab-agent-runtime
      args: [...]
```

- First matching rule wins. `use` for direct, `pool` for in-flight check.
- Pool entries tried in order; first matching `when` wins. No match → skip rule, try next.
- `inFlight` counters scoped as `${skillId}:${backendName}`.

## Blackboard Schema

Tables auto-created by `blackboard.ensureSchema()` on connect:

- `blackboard`: id, group_name, author, author_repo, for_target, observation, status, tags, refs_id, team_id, created_at
- `reflection_events`: id, agent_name, question_hash, verdict, findings, latency_ms, rerun, created_at
- `error_patterns`: id, agent_name, pattern, count, last_seen, created_at
- `agent_memory`: id, agent_name, key, value, created_at, updated_at

## Grounding File Convention

Grounding files live at `<project>/.claude/grounding/<agent>.md` and are referenced via `--append-system-prompt` in the agent YAML. The generator (`scripts/generate-grounding.mjs`) scans:
- Source code structure and key modules
- API surfaces and type definitions
- Recent git history for active areas
- README and docs for project context

CI workflow (`.gitea/workflows/`) runs the generator on every push to main and commits the result.
