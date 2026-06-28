# Issue History & Design Decisions

## Completed Issues — Key Takeaways

### #100: Reflection critic argv → stdin switch
- **Problem**: Linux `E2BIG` (~128KB argv ceiling) forced a 16KB draft truncation cap for the critic
- **Solution**: The subprocess handler already writes `TransportMessage` to stdin (#100). The pi-fab-agent-runtime shim detects piped stdin, extracts prompt text, strips `{{text}}` from argv, and pipes to pi via stdin
- **Key insight**: Zero changes needed in dispatcher/client/subprocess handler — all change was in the shim
- **Files**: `~/.local/bin/pi-fab-agent-runtime`, `src/reflection.ts` (cap removed), `src/__tests__/reflection.test.ts`

### #72: Flaky subprocess-idle-timeout test
- **Problem**: `count >= 1` assertion raced against Node cold-start under CI load
- **Solution**: Only assert the watchdog contract (timer fires and rejects), not event count
- **Pattern**: Subprocess timeout tests should NEVER assert pre-timeout event counts

### #53/#77/#89: Reflection system (3-phase)
- Phase 1 (#53): Pre-response critic hook in dispatcher
- Phase 2a (#77): Wire critic LLM via A2A call to mesh-reflector
- Phase 2b (#89): REVISE without revised_draft triggers re-run with findings appended to persona
- **Design**: ERROR is treated identically to APPROVE — original draft always emits

### #114: mesh-reviewer-bot timeout
- **Problem**: Large diffs caused idle >60s on shared MTP slot
- **Solution**: Separate the reviewer onto its own provider slot or use `local-mesh` (batched)

### #137-#141: Grounding system (5 stories)
- Generator script scans codebase → grounding markdown files
- CI workflow auto-regenerates on push to main
- Agent YAMLs wired via `--append-system-prompt`
- Confidence rule: "I don't know" when <90% confident
- Staleness TTL signal in dispatcher

### #51: Non-admin Gitea token
- Created `agent-mesh` user (id=33, is_admin=false)
- Token scopes: write:repository, write:issue, read:user
- Prevents force-merge bypass via admin API

## Open Issues — Prerequisites

### #44: Cross-host Mac verification
- **Blocker**: No mac-host runner registered. Mac is pingable at 100.109.245.96 via Tailscale
- **Needs**: SSH key authorized on Mac, act-runner installed, registered against localhost:3200

### #143: DevLake + DORA
- **Scope**: Deploy DevLake (podman + systemd), write Gitea plugin in Go, Grafana dashboards
- **Alternative**: Lightweight collector → Prometheus pushgateway → existing Grafana

### #144: Secrets manager
- **Scope**: Evaluate Vault/doppler/sops+age/1Password/systemd LoadCredential/libsecret
- **Requirements**: Per-agent isolation, offline, backward compatible with EnvironmentFile=
