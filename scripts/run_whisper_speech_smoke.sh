#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
MODEL="${1:-tiny}"
EXPECTED_TEXT="${WHISPER_SPEECH_TEXT:-hello world}"
AUDIO_REL="examples/audio/license_clear_whisper_smoke.wav"
RESULT_FILE="${ROOT_DIR}/results/inference/whisper_${MODEL}_speech_transcription_${STAMP}.json"
REPORT_FILE="${ROOT_DIR}/docs/reports/whisper_speech_transcription_smoke.md"
TEGRSTATS_REL="artifacts/system/tegrastats_whisper_speech_${MODEL}_${STAMP}.log"
TEGRSTATS_LOG="${ROOT_DIR}/${TEGRSTATS_REL}"
PID=""
ALLOW_DOWNLOAD_ARGS=()

if [ "${WHISPER_ALLOW_DOWNLOAD:-0}" = "1" ]; then
  ALLOW_DOWNLOAD_ARGS=(--allow-download)
fi

mkdir -p "${ROOT_DIR}/results/inference" "${ROOT_DIR}/docs/reports" "${ROOT_DIR}/artifacts/system"

if [ ! -f "${ROOT_DIR}/${AUDIO_REL}" ]; then
  WHISPER_SPEECH_TEXT="${EXPECTED_TEXT}" bash "${ROOT_DIR}/scripts/generate_whisper_speech_sample.sh" "${AUDIO_REL}"
fi

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
  printf 'tegrastats unavailable; Whisper speech smoke will run without thermal/power side log\n' >&2
  TEGRASTATS_LOG=""
  TEGRASTATS_REL=""
fi

cd "${ROOT_DIR}"

python3 "${ROOT_DIR}/benchmarks/inference/whisper_transcription_smoke.py" \
  --output "${RESULT_FILE}" \
  --report "${REPORT_FILE}" \
  --audio "${AUDIO_REL}" \
  --audio-source "generated_license_clear_ffmpeg_flite_text_to_speech" \
  --expected-text "${EXPECTED_TEXT}" \
  --model "${MODEL}" \
  --device auto \
  --warmup 0 \
  --repeat 1 \
  --language en \
  --tegrastats-log "${TEGRSTATS_REL}" \
  "${ALLOW_DOWNLOAD_ARGS[@]}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote report: %s\n' "${REPORT_FILE}"
printf 'Wrote audio: %s\n' "${ROOT_DIR}/${AUDIO_REL}"
if [ -n "${TEGRSTATS_LOG}" ]; then
  printf 'Wrote tegrastats: %s\n' "${TEGRSTATS_LOG}"
fi
