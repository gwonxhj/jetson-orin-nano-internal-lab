# Jetson System Snapshot

> Day 1 환경 점검의 기준 스냅샷입니다.
> Raw evidence: `artifacts/system/jetson_env_raw.log`

## Snapshot Metadata

| Field | Value |
|---|---|
| Date | 2026-05-13T12:03:56+09:00 |
| Device | Jetson Orin Nano |
| Hostname | `jetson-orin-nano` |
| Operator | `local-jetson-user` |
| Repo path | `.` |
| Repo commit | unavailable, no commits yet |
| Raw log | `artifacts/system/jetson_env_raw.log` |

## OS / JetPack / L4T

| Field | Value |
|---|---|
| L4T release | R36, revision 4.7 |
| L4T GCID | 42132812 |
| L4T date | Thu Sep 18 22:54:44 UTC 2025 |
| Kernel | Linux 5.15.148-tegra, aarch64 |
| Distribution | Ubuntu 22.04.5 LTS, jammy |

## CUDA / cuDNN / TensorRT

| Field | Value |
|---|---|
| CUDA (`nvcc --version`) | 12.6, V12.6.68 |
| cuDNN | libcudnn9 / libcudnn9-cuda-12 9.3.0.75-1 |
| TensorRT packages | 10.3.0.30-1+cuda12.5 |
| `trtexec` | TensorRT v100300 |

## Python Runtime

| Field | Value |
|---|---|
| Python | 3.10.12 |
| pip | 26.0.1 from `yolo_env` |
| conda env | `yolo_env` |
| Python executable | `python3 (yolo_env)` |
| Platform | Linux-5.15.148-tegra-aarch64-with-glibc2.35 |

## ML Runtime

| Field | Value |
|---|---|
| PyTorch | 2.8.0 |
| PyTorch CUDA available | True |
| ONNX Runtime | 1.23.2 |
| ONNX Runtime providers | AzureExecutionProvider, CPUExecutionProvider |
| ONNX Runtime note | GPU device discovery warning was emitted; CUDA/TensorRT providers are not listed in this env. |

## System State

| Field | Value |
|---|---|
| Power mode | NV Power Mode: 25W, mode id 1 |
| `sudo nvpmodel -q` | unavailable in non-interactive SSH because sudo password is required |
| `tegrastats` availability | available; 5-second smoke captured |
| Idle RAM sample | 877 / 7620 MB |
| Swap sample | 0 / 3810 MB |
| GPU idle sample | GR3D_FREQ 0% |
| Temperature sample | gpu about 39.8-40.0 C, tj about 39.9-40.0 C |
| Power sample | VDD_IN about 4.25-4.32 W during idle smoke |
| Memory (`free -h`) | 7.4 GiB total, 788 MiB used, 6.4 GiB available |
| Disk root (`df -h`) | `/dev/nvme0n1p1`, 915G size, 35G used, 833G available, 5% used |

## Tooling

| Field | Value |
|---|---|
| Docker | 29.4.0, build 9d7ad9f |
| Git | 2.34.1 |
| SSH | OpenSSH_8.9p1 Ubuntu-3ubuntu0.14, OpenSSL 3.0.2 |

## Interpretation Notes

- 이 문서는 이후 benchmark의 기준선입니다.
- power mode, thermal 상태, backend, precision이 다르면 direct regression으로 해석하지 않습니다.
- 현재 ONNX Runtime은 CUDA/TensorRT provider가 보이지 않으므로, PyTorch CUDA 결과와 ONNX Runtime CPU 결과를 같은 backend regression으로 비교하지 않습니다.
- 짧은 tegrastats smoke는 idle system evidence이며 sustained thermal benchmark가 아닙니다.
