#!/usr/bin/env bash
# deliberate.sh — drive a multi-party A2A deliberation over the fab-agent-runtime mesh.
#
# Supplies the ONE missing piece in the mesh: nothing fans `consult` out to a team's
# members or runs a rebuttal round. The runtime already provides:
#   team form    -> shared deliberation channel (libSQL)
#   team append  -> members post cross-readable positions
#   team dissolve -> claude --agent <convener> synthesizes the channel into an
#                    outcome (-> blackboard) + <<<STORY>>> blocks (-> auto-filed Gitea issues)
#
# This script: select members -> form team -> Round 1 (parallel consult -> append) ->
# Round 2 (re-consult with peers' positions -> append) -> dissolve (synthesis + filing).
#
# Usage:
#   deliberate.sh --topic "Should GraphFusion prioritize X for Localscout?" --role cto
#   deliberate.sh --topic "..." --members graphfusion-cto,atlas-cto,localscout-cto --convener graphfusion-ceo
#   deliberate.sh --topic "..." --role cto --repos GraphFusion,localscout --rounds 2
#   deliberate.sh --topic "..." --role cto --dry-run      # form + positions, NO synthesis/Gitea
#   deliberate.sh --topic "..." --role cto --no-gitea     # synthesize to blackboard, file NO issues
set -euo pipefail
export NODE_TLS_REJECT_UNAUTHORIZED=0
# team/blackboard live in the libSQL mesh store (sqld on :8080). Without this the
# CLI falls back to an unsupported file: URL and `team form` dies with URL_SCHEME_NOT_SUPPORTED.
export LIBSQL_URL="${LIBSQL_URL:-http://127.0.0.1:8080}"
FAR="fab-agent-runtime"
CONSULT_TIMEOUT_MS="${CONSULT_TIMEOUT_MS:-180000}"

TOPIC="" ROLE="" MEMBERS_CSV="" REPOS_CSV="" CONVENER="" ROUNDS=2 DURATION="2h"
DRY_RUN=0 NO_GITEA=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --topic) TOPIC="$2"; shift 2;;
    --role) ROLE="$2"; shift 2;;
    --members) MEMBERS_CSV="$2"; shift 2;;
    --repos) REPOS_CSV="$2"; shift 2;;
    --convener) CONVENER="$2"; shift 2;;
    --rounds) ROUNDS="$2"; shift 2;;
    --duration) DURATION="$2"; shift 2;;
    --dry-run) DRY_RUN=1; shift;;
    --no-gitea) NO_GITEA=1; shift;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[[ -z "$TOPIC" ]] && { echo "ERROR: --topic required" >&2; exit 2; }
[[ -z "$ROLE" && -z "$MEMBERS_CSV" ]] && { echo "ERROR: pass --role or --members" >&2; exit 2; }

WORK="$(mktemp -d /tmp/deliberate.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT
log() { printf '\033[1;36m[deliberate]\033[0m %s\n' "$*" >&2; }

# --- resolve members: name url repo, one per line into $WORK/members ---
: > "$WORK/members"
if [[ -n "$MEMBERS_CSV" ]]; then
  IFS=',' read -ra NAMES <<< "$MEMBERS_CSV"
  for n in "${NAMES[@]}"; do
    n="$(echo "$n" | xargs)"
    row="$($FAR registry get --name "$n" --json 2>/dev/null)" || { log "WARN: $n not in registry, skipping"; continue; }
    echo "$row" | python3 -c "import sys,json;r=json.load(sys.stdin);print(r['name'],r['url'],r.get('repo','-'))" >> "$WORK/members"
  done
else
  args=(registry find --role "$ROLE" --json)
  $FAR "${args[@]}" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin); rows=d if isinstance(d,list) else d.get('data',[])
repos=[r.strip() for r in '''$REPOS_CSV'''.split(',') if r.strip()]
for r in rows:
    if repos and r.get('repo') not in repos: continue
    print(r['name'], r['url'], r.get('repo','-'))
" >> "$WORK/members"
fi
MEMBER_COUNT=$(wc -l < "$WORK/members")
[[ "$MEMBER_COUNT" -lt 2 ]] && { echo "ERROR: need >=2 members, got $MEMBER_COUNT" >&2; cat "$WORK/members" >&2; exit 1; }
NAMES_CSV="$(awk '{print $1}' "$WORK/members" | paste -sd,)"
[[ -z "$CONVENER" ]] && CONVENER="$(head -1 "$WORK/members" | awk '{print $1}')"
log "members: $NAMES_CSV | convener: $CONVENER | rounds: $ROUNDS"

# --- grounding (Option A: the activator injects cross-repo facts) ---
# Lean agents (mesh-consult -> :8003, tool-less) have no repo/gitea access; they
# reason over what arrives in the question. So gather the facts here, ONCE, and
# inject them into every consult. Sources = gitea open issues + recent git
# commits across all repos in the deliberation (members' repos ∪ --repos). This
# is what lets atlas/localscout-cto answer with substance instead of the correct
# but useless "I don't have that in my consult context".
GROUND="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ground.py"
GROUND_REPOS="$(
  { awk '{print $3}' "$WORK/members"; printf '%s\n' "${REPOS_CSV//,/$'\n'}"; } \
    | grep -vE '^-?$' | sort -u | paste -sd,
)"
GROUNDING=""
if [[ -n "$GROUND_REPOS" && -f "$GROUND" ]]; then
  log "Grounding: gitea issues + git commits for [$GROUND_REPOS]…"
  GROUNDING="$(python3 "$GROUND" --topic "$TOPIC" --repos "$GROUND_REPOS" 2>"$WORK/ground.err")" \
    || log "WARN: grounding failed: $(head -1 "$WORK/ground.err" 2>/dev/null)"
  if [[ -n "$GROUNDING" ]]; then
    log "Grounding assembled ($(printf '%s' "$GROUNDING" | wc -c) bytes)."
  else
    log "WARN: grounding empty — agents will deliberate without injected facts."
  fi
fi

# --- form the team ---
# `team form` prints a human sentence: `team #N formed — topic="…", convener=…`.
# Extract the integer id (NOT the whole line); fall back to the highest active team id.
FORM_OUT="$($FAR team form --topic "$TOPIC" --members "$NAMES_CSV" --convener "$CONVENER" --duration "$DURATION" 2>&1)" \
  || { echo "ERROR: team form failed: $FORM_OUT" >&2; exit 1; }
TEAM_ID="$(printf '%s' "$FORM_OUT" | grep -oE 'team #[0-9]+' | grep -oE '[0-9]+' | head -1)"
[[ -z "$TEAM_ID" ]] && TEAM_ID="$($FAR team list --json 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(max((t['id'] for t in d),default=''))" 2>/dev/null)"
[[ -z "$TEAM_ID" ]] && { echo "ERROR: could not parse team id from: $FORM_OUT" >&2; exit 1; }
log "team formed: $TEAM_ID"

# --- one consult -> append (runs in background per member) ---
EXTRACT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/extract_answer.py"
consult_and_append() {
  local name="$1" url="$2" repo="$3" prompt="$4" tag="$5"
  local raw answer
  # --output-format json wraps the agent's whole pi session in parts[].text; extract_answer.py
  # pulls only the final result. Appending the raw 28KB session blob pollutes <recent_blackboard>
  # on later consults (→ 8192-ctx overflow → empty answers) and overflows the libSQL append.
  raw="$($FAR call "$url" consult "$prompt" --no-stream --output-format json --timeout-ms "$CONSULT_TIMEOUT_MS" 2>"$WORK/$name.err")" \
    || log "WARN: consult $name transport failed: $(head -1 "$WORK/$name.err")"
  answer="$(printf '%s' "$raw" | python3 "$EXTRACT" 2>/dev/null)" \
    || { log "WARN: $name empty answer (model error / ctx overflow)"; answer="(no response — consult failed)"; }
  printf '[%s] %s' "$tag" "$answer" > "$WORK/$name.$tag.txt"
  $FAR team append "$TEAM_ID" --author "$name" --repo "$repo" "$(cat "$WORK/$name.$tag.txt")" >/dev/null 2>"$WORK/$name.append.err" \
    || log "WARN: append for $name failed: $(head -1 "$WORK/$name.append.err")"
}

# --- Round 1: positions (parallel) ---
log "Round 1: collecting positions from $MEMBER_COUNT agents (parallel)…"
R1_PROMPT="DELIBERATION (team $TEAM_ID). Topic: $TOPIC
${GROUNDING:+
$GROUNDING}
Reply from your repo/role's perspective using EXACTLY these fields. NO intro, NO rhetorical questions, NO generic openers, NO timestamps.
STANCE: [your repo's stance in one line]
GROUNDING: [cite 1-3 real artifacts from the facts above — issue #N or commit hash — that bear on your repo]
IMPACT: [1-2 sentences: concrete impact on your repo]
PRIORITY: [P0/P1/P2/P3] — [one-line justification]
COMMITMENTS/ASKS: [bullet list of concrete next-steps you commit to and what you need from the other repos]"
while read -r name url repo; do
  consult_and_append "$name" "$url" "$repo" "$R1_PROMPT" "R1" &
done < "$WORK/members"
wait
log "Round 1 complete."

# --- Round 2: rebuttal with peers' positions visible ---
if [[ "$ROUNDS" -ge 2 ]]; then
  DIGEST="$($FAR team read "$TEAM_ID" --json 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin); rows=d if isinstance(d,list) else d.get('entries',d.get('data',[]))
for r in rows:
    a=r.get('author','?'); o=r.get('observation',r.get('text',''))
    print(f'- {a}: {o}'.replace(chr(10),' ')[:600])
")"
  log "Round 2: rebuttal round with peers' positions visible (parallel)…"
  while read -r name url repo; do
    R2_PROMPT="DELIBERATION (team $TEAM_ID). Topic: $TOPIC
${GROUNDING:+
$GROUNDING}
PEER POSITIONS so far:
$DIGEST

Reply using EXACTLY these fields. NO intro, NO rhetorical questions, NO generic openers, NO timestamps.
STANCE: [Maintain/Revise] — [one line: did your position change after seeing peers, and why]
GROUNDING: [cite the real artifacts — issue #N or commit hash — supporting your final stance]
PEER ALIGNMENT: [where you AGREE / DISAGREE and with whom, and why]
IMPACT: [1-2 sentences: updated impact on your repo]
PRIORITY: [P0/P1/P2/P3] — [one-line justification]   (state the priority ONCE, here only — do not put a P-number on the STANCE line)
COMMITMENTS/ASKS: [bullet list of FINAL concrete commitments and what you need from the other repos]"
    consult_and_append "$name" "$url" "$repo" "$R2_PROMPT" "R2" &
  done < "$WORK/members"
  wait
  log "Round 2 complete."
fi

# --- show the channel ---
log "Team channel ($TEAM_ID):"
$FAR team read "$TEAM_ID" 2>/dev/null || true

# --- converge: dissolve -> claude --agent convener synthesis (-> blackboard + Gitea) ---
if [[ "$DRY_RUN" -eq 1 ]]; then
  log "DRY-RUN: skipping synthesis. Team $TEAM_ID left active (dissolve manually: $FAR team dissolve $TEAM_ID)."
  echo "TEAM_ID=$TEAM_ID"
  exit 0
fi
log "Converging: dissolving team $TEAM_ID (convener=$CONVENER synthesizes via claude)…"
if [[ "$NO_GITEA" -eq 1 ]]; then
  log "--no-gitea: synthesis -> blackboard only, NO Gitea issues filed."
  ( unset GITEA_TOKEN; $FAR team dissolve "$TEAM_ID" )
else
  $FAR team dissolve "$TEAM_ID"
fi
log "Done. Outcome on blackboard (group 'ceo', tag team-$TEAM_ID); any stories filed to Gitea above."
echo "TEAM_ID=$TEAM_ID"
