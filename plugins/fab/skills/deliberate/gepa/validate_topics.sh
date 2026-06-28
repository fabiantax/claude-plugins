#!/usr/bin/env bash
# validate_topics.sh — run the CURRENT (accepted) activation procedure across a
# panel of DIVERSE deliberations and aggregate the activation scores.
#
# Why: a single-topic 1.000 risks overfitting the procedure to one easy,
# converging decision. This exercises the procedure on different repos, team
# sizes, and decision types — including a deliberately CONTENTIOUS topic that
# should NOT trivially converge — so we see which dimension (if any) degrades
# on harder inputs. Whatever scores lowest becomes the next GEPA reflection input.
#
# Each topic runs deliberate.sh --dry-run (positions + rebuttal, NO synthesis /
# NO gitea filing), is scored by score_activation.py, and the per-dimension
# results are tabulated. Runs SEQUENTIALLY (each deliberation already fans its
# members across the 4 :8003 slots; overlapping deliberations would oversubscribe).
set -uo pipefail
export NODE_TLS_REJECT_UNAUTHORIZED=0
export LIBSQL_URL="${LIBSQL_URL:-http://127.0.0.1:8080}"

SK=~/.claude/skills/deliberate/deliberate.sh
SCORE=~/.claude/skills/deliberate/gepa/score_activation.py
OUT="${1:-/tmp/gepa-topic-validation}"
mkdir -p "$OUT"

# topic | members | note(decision type)
PANEL=(
  "Should GraphFusion prioritize the per-profile CCH .metric export so localscout can adopt route_with_profile for door-to-door routing?|graphfusion-cto,localscout-cto|feature-priority (baseline, expected converge)"
  "Should Atlas block every GraphFusion release on a clean dead-code + SOLID scan, even when it slows the release cadence?|atlas-cto,graphfusion-cto|CONTENTIOUS gate-vs-velocity (should NOT trivially converge)"
  "Should the stack standardize on typed-triple (subject,relation,object) extraction across GraphFusion, Atlas, and fab-swarm — and who owns the schema?|graphfusion-cto,atlas-cto,fab-swarm-cto|3-party standardization (ownership tension)"
  "Should fab-swarm prioritize the Hungarian optimal batch-router over further SAFLA learning work this cycle?|fab-swarm-cto,graphfusion-cto|intra-roadmap tradeoff (different repos' stakes)"
)

printf '%-58s %5s %5s %5s %5s %5s %6s\n' "TOPIC (truncated)" "part" "grnd" "conv" "actn" "effi" "TOTAL" | tee "$OUT/summary.txt"
printf '%s\n' "-------------------------------------------------------------------------------------------------" | tee -a "$OUT/summary.txt"

i=0
declare -a TOTALS
for row in "${PANEL[@]}"; do
  i=$((i+1))
  IFS='|' read -r topic members note <<< "$row"
  trace="$OUT/topic-$i.txt"
  echo ">>> [$i] $note" >&2
  echo "    members=$members" >&2
  timeout 340 bash "$SK" --topic "$topic" --members "$members" \
    --convener "${members%%,*}" --rounds 2 --dry-run > "$trace" 2>"$OUT/topic-$i.err" \
    || echo "    WARN: deliberation exited non-zero (see $OUT/topic-$i.err)" >&2
  # score (json on the last line of the pretty output)
  json="$(python3 "$SCORE" < "$trace" 2>/dev/null | tail -1)"
  read -r part grnd conv actn effi total <<< "$(printf '%s' "$json" | python3 -c '
import sys,json
try:
    d=json.load(sys.stdin); dim=d["dimensions"]
    print(dim["participation"],dim["grounding"],dim["convergence"],dim["actionability"],dim["efficiency"],d["total"])
except Exception:
    print("0 0 0 0 0 0")
')"
  TOTALS+=("$total")
  printf '%-58.58s %5s %5s %5s %5s %5s %6s\n' "$note" "$part" "$grnd" "$conv" "$actn" "$effi" "$total" | tee -a "$OUT/summary.txt"
done

# aggregate
echo "-------------------------------------------------------------------------------------------------" | tee -a "$OUT/summary.txt"
printf '%s\n' "${TOTALS[@]}" | python3 -c '
import sys
v=[float(x) for x in sys.stdin.read().split()]
if v:
    print("mean total: %.3f   min: %.3f   max: %.3f   n=%d" % (sum(v)/len(v), min(v), max(v), len(v)))
' | tee -a "$OUT/summary.txt"
echo "traces + summary in $OUT" >&2
