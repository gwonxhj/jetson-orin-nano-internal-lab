#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
MODEL_ALIAS="${1:-tiny-gpt2}"
RESULT_FILE="${ROOT_DIR}/results/llm/llm_${MODEL_ALIAS}_text_generation_${STAMP}.json"
REPORT_FILE="${ROOT_DIR}/docs/reports/llm_text_generation_smoke.md"
TEGRSTATS_REL="artifacts/system/tegrastats_llm_${MODEL_ALIAS}_${STAMP}.log"
TEGRSTATS_LOG="${ROOT_DIR}/${TEGRSTATS_REL}"
PID=""
ALLOW_DOWNLOAD_ARGS=()

if [ "${LLM_ALLOW_DOWNLOAD:-0}" = "1" ]; then
  ALLOW_DOWNLOAD_ARGS=(--allow-download)
fi

mkdir -p "${ROOT_DIR}/results/llm" "${ROOT_DIR}/docs/reports" "${ROOT_DIR}/artifacts/system"

cleanup() {
  if [ -n "${PID}" ] && kill -0 "${PID}" >/dev/null 2>&1; then
    kill "${PID}" >/dev/null 2>&1 || true
    wait "${PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if command -v tegrastats >/dev/null 2>&1; then
  tegrastats --interval 1000 > "${TEGRSTATS_LOG}" 2>&1 &
  PID="$!"
  sleep 1
else
  printf 'tegrastats unavailable; LLM smoke will run without thermal/power side log\n' >&2
  TEGRASTATS_LOG=""
  TEGRASTATS_REL=""
fi

cd "${ROOT_DIR}"

python3 "${ROOT_DIR}/benchmarks/inference/llm_text_generation_smoke.py" \
  --output "${RESULT_FILE}" \
  --report "${REPORT_FILE}" \
  --model-alias "${MODEL_ALIAS}" \
  --prompt "${LLM_PROMPT:-Jetson edge AI}" \
  --max-new-tokens "${LLM_MAX_NEW_TOKENS:-16}" \
  --device auto \
  --warmup "${LLM_WARMUP:-0}" \
  --repeat "${LLM_REPEAT:-1}" \
  --tegrastats-log "${TEGRSTATS_REL}" \
  "${ALLOW_DOWNLOAD_ARGS[@]}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote report: %s\n' "${REPORT_FILE}"
if [ -n "${TEGRSTATS_LOG}" ]; then
  printf 'Wrote tegrastats: %s\n' "${TEGRSTATS_LOG}"
fi
