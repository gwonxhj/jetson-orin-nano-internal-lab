#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_KIND="${ORT_CUDA_ENV_KIND:-conda}"
CONDA_ENV_NAME="${ORT_CUDA_CONDA_ENV_NAME:-ort_cuda_env}"
VENV_DIR="${ORT_CUDA_ENV_DIR:-${HOME}/.venvs/ort_cuda_env}"
PIP_INDEX_URL="${ORT_CUDA_PIP_INDEX_URL:-https://pypi.jetson-ai-lab.io/jp6/cu126}"
INSTALL_SPEC="${ORT_CUDA_INSTALL_SPEC:-onnxruntime-gpu==1.23.0}"
MODE="${1:-plan}"

if [ "${MODE}" != "--execute" ]; then
  cat <<EOF
ONNX Runtime CUDA isolated env plan

This script is safe by default and has not created or modified an env.

To execute:
  ORT_CUDA_ENV_KIND="${ENV_KIND}" \\
  ORT_CUDA_CONDA_ENV_NAME="${CONDA_ENV_NAME}" \\
  ORT_CUDA_PIP_INDEX_URL="${PIP_INDEX_URL}" \\
  ORT_CUDA_INSTALL_SPEC="${INSTALL_SPEC}" \\
  bash scripts/create_ort_cuda_env.sh --execute

Then verify:
  conda run -n "${CONDA_ENV_NAME}" python benchmarks/inference/onnxruntime_cuda_ep_attempt.py \\
    --output results/inference/onnxruntime_cuda_ep_attempt_<timestamp>.json \\
    --report docs/reports/onnxruntime_cuda_ep_activation_attempt.md
EOF
  exit 0
fi

if [ "${ENV_KIND}" = "conda" ]; then
  if ! command -v conda >/dev/null 2>&1; then
    if [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
      # shellcheck source=/dev/null
      source "${HOME}/miniconda3/etc/profile.d/conda.sh"
    fi
  fi
  if ! command -v conda >/dev/null 2>&1; then
    printf 'conda is unavailable. Set ORT_CUDA_ENV_KIND=venv or install/enable conda first.\n' >&2
    exit 2
  fi
  if conda env list | awk '{print $1}' | grep -Fx "${CONDA_ENV_NAME}" >/dev/null 2>&1; then
    printf 'Refusing to overwrite existing conda env: %s\n' "${CONDA_ENV_NAME}" >&2
    printf 'Set ORT_CUDA_CONDA_ENV_NAME to a new name or remove the env manually after review.\n' >&2
    exit 2
  fi
  conda create -y -n "${CONDA_ENV_NAME}" python=3.10 pip
  conda run -n "${CONDA_ENV_NAME}" python -m pip install --upgrade pip setuptools wheel
  conda run -n "${CONDA_ENV_NAME}" python -m pip install "numpy<2"
  conda run -n "${CONDA_ENV_NAME}" python -m pip install --index-url "${PIP_INDEX_URL}" "${INSTALL_SPEC}"
  cd "${ROOT_DIR}"
  conda run -n "${CONDA_ENV_NAME}" python - <<'PY'
import onnxruntime as ort
print("onnxruntime", ort.__version__)
print("providers", ort.get_available_providers())
PY
  exit 0
fi

if [ "${ENV_KIND}" != "venv" ]; then
  printf 'Unknown ORT_CUDA_ENV_KIND: %s\n' "${ENV_KIND}" >&2
  exit 2
fi

if [ -e "${VENV_DIR}" ]; then
  printf 'Refusing to overwrite existing env: %s\n' "${VENV_DIR}" >&2
  printf 'Set ORT_CUDA_ENV_DIR to a new path or remove it manually after review.\n' >&2
  exit 2
fi

python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel
"${VENV_DIR}/bin/python" -m pip install "numpy<2"
"${VENV_DIR}/bin/python" -m pip install --index-url "${PIP_INDEX_URL}" "${INSTALL_SPEC}"

cd "${ROOT_DIR}"
"${VENV_DIR}/bin/python" - <<'PY'
import onnxruntime as ort
print("onnxruntime", ort.__version__)
print("providers", ort.get_available_providers())
PY
