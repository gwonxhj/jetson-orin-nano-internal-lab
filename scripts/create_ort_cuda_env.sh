#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${ORT_CUDA_ENV_DIR:-${HOME}/.venvs/ort_cuda_env}"
PIP_INDEX_URL="${ORT_CUDA_PIP_INDEX_URL:-https://pypi.jetson-ai-lab.io/jp6/cu126}"
INSTALL_SPEC="${ORT_CUDA_INSTALL_SPEC:-onnxruntime-gpu==1.23.0}"
MODE="${1:-plan}"

if [ "${MODE}" != "--execute" ]; then
  cat <<EOF
ONNX Runtime CUDA isolated env plan

This script is safe by default and has not created or modified an env.

To execute:
  ORT_CUDA_ENV_DIR="${ENV_DIR}" \\
  ORT_CUDA_PIP_INDEX_URL="${PIP_INDEX_URL}" \\
  ORT_CUDA_INSTALL_SPEC="${INSTALL_SPEC}" \\
  bash scripts/create_ort_cuda_env.sh --execute

Then verify:
  "${ENV_DIR}/bin/python" benchmarks/inference/onnxruntime_cuda_ep_attempt.py \\
    --output results/inference/onnxruntime_cuda_ep_attempt_<timestamp>.json \\
    --report docs/reports/onnxruntime_cuda_ep_activation_attempt.md
EOF
  exit 0
fi

if [ -e "${ENV_DIR}" ]; then
  printf 'Refusing to overwrite existing env: %s\n' "${ENV_DIR}" >&2
  printf 'Set ORT_CUDA_ENV_DIR to a new path or remove it manually after review.\n' >&2
  exit 2
fi

python3 -m venv "${ENV_DIR}"
"${ENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel
"${ENV_DIR}/bin/python" -m pip install numpy
"${ENV_DIR}/bin/python" -m pip install --index-url "${PIP_INDEX_URL}" "${INSTALL_SPEC}"

cd "${ROOT_DIR}"
"${ENV_DIR}/bin/python" - <<'PY'
import onnxruntime as ort
print("onnxruntime", ort.__version__)
print("providers", ort.get_available_providers())
PY
