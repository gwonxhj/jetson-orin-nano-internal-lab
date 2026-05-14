#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONDA_ENV_NAME="${WHISPER_CONDA_ENV_NAME:-whisper_env}"
SOURCE_ENV="${WHISPER_SOURCE_CONDA_ENV:-yolo_env}"
BACKEND="${WHISPER_BACKEND:-openai-whisper}"
MODE="${1:-plan}"

case "${BACKEND}" in
  openai-whisper)
    INSTALL_SPEC="${WHISPER_INSTALL_SPEC:-openai-whisper}"
    IMPORT_CHECK="import whisper; print('whisper', getattr(whisper, '__version__', 'unknown'))"
    ;;
  faster-whisper)
    INSTALL_SPEC="${WHISPER_INSTALL_SPEC:-faster-whisper}"
    IMPORT_CHECK="import faster_whisper; print('faster_whisper', getattr(faster_whisper, '__version__', 'unknown'))"
    ;;
  *)
    printf 'Unknown WHISPER_BACKEND: %s\n' "${BACKEND}" >&2
    printf 'Use WHISPER_BACKEND=openai-whisper or WHISPER_BACKEND=faster-whisper\n' >&2
    exit 2
    ;;
esac

if [ "${MODE}" != "--execute" ]; then
  cat <<EOF
Whisper isolated env plan

This script is safe by default and has not created or modified an env.

Plan:
  1. Clone existing Jetson Python stack: conda create --clone "${SOURCE_ENV}" -n "${CONDA_ENV_NAME}"
  2. Install candidate backend inside the clone only: python -m pip install "${INSTALL_SPEC}"
  3. Verify imports and ffmpeg.
  4. Run the existing smoke from the isolated env.

To execute:
  WHISPER_CONDA_ENV_NAME="${CONDA_ENV_NAME}" \\
  WHISPER_SOURCE_CONDA_ENV="${SOURCE_ENV}" \\
  WHISPER_BACKEND="${BACKEND}" \\
  WHISPER_INSTALL_SPEC="${INSTALL_SPEC}" \\
  bash scripts/create_whisper_env.sh --execute

Then verify:
  conda run -n "${CONDA_ENV_NAME}" python benchmarks/inference/whisper_transcription_smoke.py \\
    --output results/inference/whisper_tiny_transcription_<timestamp>.json \\
    --report docs/reports/whisper_transcription_smoke.md \\
    --audio artifacts/audio/whisper_smoke_16khz.wav \\
    --model tiny \\
    --allow-download

Notes:
  - This keeps "${SOURCE_ENV}" unchanged.
  - Model weight download is still controlled by the smoke runner; use --allow-download only after reviewing the plan.
  - Prefer openai-whisper first; faster-whisper is a follow-up optimization candidate.
EOF
  exit 0
fi

if ! command -v conda >/dev/null 2>&1; then
  if [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
    # shellcheck source=/dev/null
    source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  fi
fi
if ! command -v conda >/dev/null 2>&1; then
  printf 'conda is unavailable. Enable conda first.\n' >&2
  exit 2
fi

if ! conda env list | awk '{print $1}' | grep -Fx "${SOURCE_ENV}" >/dev/null 2>&1; then
  printf 'Source conda env not found: %s\n' "${SOURCE_ENV}" >&2
  exit 2
fi
if conda env list | awk '{print $1}' | grep -Fx "${CONDA_ENV_NAME}" >/dev/null 2>&1; then
  printf 'Refusing to overwrite existing conda env: %s\n' "${CONDA_ENV_NAME}" >&2
  printf 'Set WHISPER_CONDA_ENV_NAME to a new name or remove the env manually after review.\n' >&2
  exit 2
fi

conda create -y --clone "${SOURCE_ENV}" -n "${CONDA_ENV_NAME}"
conda run -n "${CONDA_ENV_NAME}" python -m pip install --upgrade pip setuptools wheel
conda run -n "${CONDA_ENV_NAME}" python -m pip install "${INSTALL_SPEC}"

cd "${ROOT_DIR}"
conda run -n "${CONDA_ENV_NAME}" python - <<PY
${IMPORT_CHECK}
try:
    import torch
    print("torch", torch.__version__)
    print("cuda available", torch.cuda.is_available())
except Exception as exc:
    print("torch unavailable", repr(exc))
PY
conda run -n "${CONDA_ENV_NAME}" ffmpeg -version | head -n 2
