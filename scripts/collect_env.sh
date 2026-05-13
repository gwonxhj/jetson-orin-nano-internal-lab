#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/artifacts/system"
LOG_FILE="${LOG_DIR}/jetson_env_raw.log"

mkdir -p "${LOG_DIR}"

run_section() {
  local title="$1"
  shift

  {
    printf '
===== %s =====
' "${title}"
    printf '$'
    printf ' %q' "$@"
    printf '
'
  } >> "${LOG_FILE}"

  "$@" >> "${LOG_FILE}" 2>&1
  local status=$?
  if [ "${status}" -eq 0 ]; then
    return 0
  fi

  printf '[unavailable or failed: exit %s]
' "${status}" >> "${LOG_FILE}"
  return 0
}

run_python_probe() {
  {
    printf '
===== Python ML runtime probe =====
'
    printf '$ python3 - <<PY
'
  } >> "${LOG_FILE}"

  python3 - <<'PYML' >> "${LOG_FILE}" 2>&1 || true
import os
import platform
import sys

print("python executable", sys.executable)
print("conda env", os.environ.get("CONDA_DEFAULT_ENV", ""))
print("virtualenv", os.environ.get("VIRTUAL_ENV", ""))
print("platform", platform.platform())

try:
    import torch
    print("torch", torch.__version__)
    print("torch cuda available", torch.cuda.is_available())
except Exception as exc:
    print("torch unavailable:", exc)

try:
    import onnxruntime as ort
    print("onnxruntime", ort.__version__)
    print("onnxruntime providers", ort.get_available_providers())
except Exception as exc:
    print("onnxruntime unavailable:", exc)
PYML
}

run_tegrastats_probe() {
  {
    printf '
===== tegrastats smoke =====
'
    printf '$ tegrastats --interval 1000
'
  } >> "${LOG_FILE}"

  if ! command -v tegrastats >/dev/null 2>&1; then
    printf '[unavailable: tegrastats command not found]
' >> "${LOG_FILE}"
    return 0
  fi

  if command -v timeout >/dev/null 2>&1; then
    timeout 5s tegrastats --interval 1000 >> "${LOG_FILE}" 2>&1 || true
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout 5s tegrastats --interval 1000 >> "${LOG_FILE}" 2>&1 || true
  else
    printf '[skipped: timeout command unavailable]
' >> "${LOG_FILE}"
  fi
}

: > "${LOG_FILE}"
{
  printf '# Jetson environment raw log
'
  printf 'generated_at=%s
' "$(date -Iseconds 2>/dev/null || date)"
  printf 'root_dir=%s
' "${ROOT_DIR}"
} >> "${LOG_FILE}"

run_section "Git commit" git rev-parse --short HEAD
run_section "Git status" git status --short --branch
run_section "Jetson L4T release" cat /etc/nv_tegra_release
run_section "Kernel" uname -a
run_section "Distribution" lsb_release -a
run_section "CUDA nvcc" nvcc --version
run_section "cuDNN packages" dpkg-query -W "*cudnn*"
run_section "TensorRT packages" dpkg-query -W "*tensorrt*" "libnvinfer*"
run_section "Python" python3 --version
run_section "pip" python3 -m pip --version
run_python_probe
run_section "TensorRT trtexec in PATH" trtexec --version
run_section "TensorRT trtexec default Jetson path" /usr/src/tensorrt/bin/trtexec --version
run_section "Power mode without sudo" nvpmodel -q
run_section "Power mode" sudo -n nvpmodel -q
run_tegrastats_probe
run_section "Memory" free -h
run_section "Disk" df -h
run_section "Docker" docker --version
run_section "Git" git --version
run_section "SSH" ssh -V

printf 'Wrote %s
' "${LOG_FILE}"
