#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_REL="${1:-examples/audio/license_clear_whisper_smoke.wav}"
TEXT="${WHISPER_SPEECH_TEXT:-hello world}"
OUT_FILE="${ROOT_DIR}/${OUT_REL}"

mkdir -p "$(dirname "${OUT_FILE}")"

if ! command -v ffmpeg >/dev/null 2>&1; then
  printf 'ffmpeg is required to generate the license-clear Whisper speech sample\n' >&2
  exit 1
fi

FILTERS="$(ffmpeg -hide_banner -filters 2>/dev/null)"
if ! grep -Eq '(^|[[:space:]])flite[[:space:]]' <<<"${FILTERS}"; then
  printf 'ffmpeg flite filter is required to synthesize the license-clear speech sample\n' >&2
  exit 1
fi

ffmpeg -hide_banner -loglevel error -y \
  -f lavfi \
  -i "flite=text='${TEXT}':voice=slt" \
  -ar 16000 \
  -ac 1 \
  -sample_fmt s16 \
  "${OUT_FILE}"

printf 'Wrote speech sample: %s\n' "${OUT_FILE}"
printf 'Text: %s\n' "${TEXT}"
