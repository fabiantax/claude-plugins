#!/usr/bin/env bash
# Launcher for skillopt-train pointing at GLM-5.1 via Z.AI.
#
# Reads .claude/settings.local.json from the CWD and exports
# ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, ANTHROPIC_API_KEY into the
# parent process so the `claude` CLI subprocess (spawned by skillopt's
# claude_backend with cwd=temp_dir) inherits them and talks to Z.AI's
# GLM-5.1 Anthropic-compat endpoint.
#
# Usage:
#   cd <repo-with-.claude/settings.local.json>
#   ~/.claude/skills/skillopt-rust-bugfix/scripts/skillopt-train-glm51.sh \
#     [--config <yaml-path>]  # default: ~/.claude/skills/skillopt-rust-bugfix/.skillopt/glm51.yaml

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_CONFIG="${SKILL_DIR}/.skillopt/glm51-phase1.yaml"

CONFIG="${DEFAULT_CONFIG}"
USE_ONESHOT=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --oneshot)
      USE_ONESHOT=1; shift
      ;;
    -h|--help)
      echo "Usage: $(basename "$0") [--config <yaml>] [--oneshot]"
      echo ""
      echo "  Reads .claude/settings.local.json from CWD for GLM-5.1 credentials."
      echo "  Default config: ${DEFAULT_CONFIG}"
      echo "  --oneshot: run scripts/skillopt-optimize-skill-glm51.py (httpx reflect+rewrite)"
      echo "             instead of the real SkillOpt training loop via skillopt-train."
      exit 0
      ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

SETTINGS="$(pwd)/.claude/settings.local.json"
if [[ ! -f "${SETTINGS}" ]]; then
  echo "error: ${SETTINGS} not found." >&2
  echo "       run this from a repo whose .claude/settings.local.json has the" >&2
  echo "       Z.AI env vars (ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, ..)." >&2
  exit 1
fi

# Extract env values via jq — bail early on missing keys.
BASE_URL="$(jq -r '.env.ANTHROPIC_BASE_URL // empty' "${SETTINGS}")"
AUTH_TOKEN="$(jq -r '.env.ANTHROPIC_AUTH_TOKEN // empty' "${SETTINGS}")"
API_KEY="$(jq -r '.env.ANTHROPIC_API_KEY // empty' "${SETTINGS}")"
MODEL="$(jq -r '.env.ANTHROPIC_DEFAULT_SONNET_MODEL // empty' "${SETTINGS}")"

if [[ -z "${BASE_URL}" || -z "${AUTH_TOKEN}" ]]; then
  echo "error: ANTHROPIC_BASE_URL or ANTHROPIC_AUTH_TOKEN missing in env block of ${SETTINGS}" >&2
  exit 1
fi
if [[ -z "${MODEL}" ]]; then
  MODEL="glm-5.1"
  echo "warn: ANTHROPIC_DEFAULT_SONNET_MODEL not set in settings; defaulting to ${MODEL}" >&2
fi

# Anthropic-compat path (used by `--oneshot` and by claude_backend if active).
export ANTHROPIC_BASE_URL="${BASE_URL}"
export ANTHROPIC_AUTH_TOKEN="${AUTH_TOKEN}"
export ANTHROPIC_API_KEY="${API_KEY}"

# OpenAI-compat path — required for the real SkillOpt train loop.
# Z.AI's OpenAI-compat endpoint accepts the same auth token as the
# Anthropic-compat one (pending validation, see ADR-003).
export AZURE_OPENAI_AUTH_MODE="openai_compatible"
export AZURE_OPENAI_ENDPOINT="https://api.z.ai/api/coding/paas/v4"
export AZURE_OPENAI_API_KEY="${AUTH_TOKEN}"

export OPTIMIZER_DEPLOYMENT="${MODEL}"
export TARGET_DEPLOYMENT="${MODEL}"
# Make sure claude CLI doesn't pop a UI prompt if claude_backend is reached.
export CLAUDE_PERMISSION_MODE="dontAsk"

echo "GLM-5.1 wire-up:"
echo "  ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL}"
echo "  AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}"
echo "  Auth token=${AUTH_TOKEN:0:8}..."
echo "  OPTIMIZER/TARGET=${MODEL}"
if [[ "${USE_ONESHOT}" == "1" ]]; then
  echo "  Path: --oneshot (httpx reflect+rewrite against Anthropic-compat)"
else
  echo "  Path: skillopt-train (real SkillOpt loop via openai_compatible → Z.AI)"
fi
echo "  Config=${CONFIG}"
echo ""

if [[ "${USE_ONESHOT}" == "1" ]]; then
  exec python3 "${SKILL_DIR}/scripts/skillopt-optimize-skill-glm51.py"
fi

# Default path: real SkillOpt training loop with our custom env adapter.
exec skillopt-train --config "${CONFIG}"
