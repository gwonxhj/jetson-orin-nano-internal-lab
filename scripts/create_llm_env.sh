#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONDA_ENV_NAME="${LLM_CONDA_ENV_NAME:-llm_env}"
SOURCE_ENV="${LLM_SOURCE_CONDA_ENV:-yolo_env}"
BACKEND="${LLM_BACKEND:-transformers}"
MODE="${1:-plan}"

case "${BACKEND}" in
  transformers)
    INSTALL_SPEC="${LLM_INSTALL_SPEC:-transformers accelerate safetensors sentencepiece}"
    IMPORT_CHECK="import transformers; print('transformers', transformers.__version__)"
    ;;
  *)
    printf 'Unknown LLM_BACKEND: %s\n' "${BACKEND}" >&2
    printf 'Use LLM_BACKEND=transformers for the first isolated smoke.\n' >&2
    exit 2
    ;;
esac

if [ "${MODE}" != "--execute" ]; then
  cat <<EOF
LLM isolated env plan

This script is safe by default and has not created or modified an env.

Plan:
  1. Clone existing Jetson Python stack: conda create --clone "${SOURCE_ENV}" -n "${CONDA_ENV_NAME}"
  2. Install candidate backend inside the clone only: python -m pip install ${INSTALL_SPEC}
  3. Verify imports and PyTorch CUDA.
  4. Run the tiny text-generation smoke from the isolated env.

To execute:
  LLM_CONDA_ENV_NAME="${CONDA_ENV_NAME}" \\
  LLM_SOURCE_CONDA_ENV="${SOURCE_ENV}" \\
  LLM_BACKEND="${BACKEND}" \\
  LLM_INSTALL_SPEC="${INSTALL_SPEC}" \\
  bash scripts/create_llm_env.sh --execute

Then verify:
  conda run -n "${CONDA_ENV_NAME}" bash scripts/run_llm_smoke.sh tiny-gpt2

Notes:
  - This keeps "${SOURCE_ENV}" unchanged.
  - Model weight download/cache is controlled by the smoke runner; use LLM_ALLOW_DOWNLOAD=1 only after reviewing the plan.
  - The first model candidate is intentionally tiny and is path evidence, not model quality evidence.
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
  printf 'Set LLM_CONDA_ENV_NAME to a new name or remove the env manually after review.\n' >&2
  exit 2
fi

conda create -y --clone "${SOURCE_ENV}" -n "${CONDA_ENV_NAME}"
conda run -n "${CONDA_ENV_NAME}" python -m pip install --upgrade pip setuptools wheel
conda run -n "${CONDA_ENV_NAME}" python -m pip install ${INSTALL_SPEC}

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
