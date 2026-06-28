---
name: mesh-context
description: Pull the mesh's view of the repo you're coding in — which value streams it serves, open blackboard threads addressed to its agents, and (on request) the CEO/CTO's current priority/design read. Use when deciding what to do next or before filing a user story, so the work is grounded in the mesh, not guessed.
argument-hint: "[repo] — e.g. 'atlas', 'GraphFusion', 'mesh'; empty = the repo of the current working dir"
---

# /mesh-context — connect the coding session to the mesh

The mesh (value streams + CEO/CTO agents + the shared blackboard) is reachable
but not automatic. This skill is the **explicit deep pull**: it surfaces the
mesh's view of the repo so a coding decision or a new user story is grounded in
real cross-team state instead of guessed. (The `SessionStart` hook already does
a *brief, silent-unless-signal* version of step 1 — this skill is the full one,
plus the live consult in steps 3–4.)

## Step 0 — resolve scope from `$ARGUMENTS`

- Empty → use the current working directory's repo.
- A repo name (`atlas`, `GraphFusion`, `graphfusion`, `mesh`, `localscout`,
  `fab-swarm`, `fab-trader`, `ml`) → resolve its checkout dir, usually
  `/home/fabian/Developer/personal/<Repo>` (`mesh` →
  `fab-agent-mesh`/`fab-agent-runtime`). Pass that dir as the script's 2nd arg.

## Step 1 — snapshot (always; read-only, no LLM)

```bash
/home/fabian/.claude/hooks/mesh-context-snapshot.sh full <repo-dir>
```

Prints: the repo's value streams, and open blackboard threads addressed to its
`<repo>-cto` / `<repo>-ceo`. This is the cheap grounding — run it first.

## Step 2 — read the stream (only if a stream is relevant to the task)

```bash
fab-agent-runtime value-stream show --stream <name>     # flow + producers/consumers by layer
```

Use it to see who is **downstream** of a change (whom this work unblocks) and
who is **upstream** (whom to consult / wait on).

## Step 3 — consult, only when the question is intent/roadmap (not code)

**Grep first** for "does X exist / what does field Y mean / who calls Z" — those
are code questions. **Consult** only for "is this a known limitation / what's the
plan / should I work around or wait / is this the right priority":

```bash
fab-agent-runtime call http://127.0.0.1:<port> consult "Question. Include the consumer-side PR/issue link. Ask for prioritization input, not authoritative answers."
```

Governance ports (CEO = product/priority, CTO = technical/contract):

| Repo | CEO | CTO |
|------|-----|-----|
| graphfusion | 50210 | 50211 |
| atlas | 50220 | 50221 |
| mesh | 50293 | 50294 |
| fab-swarm | 50270 | 50271 |
| fab-trader | 50230 | 50231 |
| localscout | 50240 | 50241 |
| ml-knowledgegraph | 50250 | 50251 |

(Plain HTTP — not https. The full endpoint list + calling pattern is in
`~/CLAUDE.md` → "Cross-repo coordination".)

**Treat every consult as a prioritization signal, not authoritative repo truth**
— always cross-verify against the code/issues (memory
`feedback_a2a_peer_consults_unreliable`).

## Step 4 — synthesize and act

- **Deciding what's next:** rank candidates against the stream's outcome + the
  CEO's stated priority + open blackboard threads. Surface the top 1–3 with the
  grounding (stream, thread #, SHA/issue) cited.
- **Filing a user story:** file via the **gitea-pm** agent/skill on the *upstream*
  repo, tagged `from:<consumer>` + `unblocks:<downstream>` so the autonomy loop
  can pick it up (CLAUDE.md → cross-repo signal labels). For a multi-team
  decision, prefer **/deliberate** (fans out, agents rebut, converges, files).

## Notes

- The snapshot is read-only and fails silent — safe to run anytime.
- If nothing material surfaces (no streams, no threads, sqld down), say so and
  proceed on code grounding alone. Do not fabricate a mesh signal.
