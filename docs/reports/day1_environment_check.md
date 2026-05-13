# Day 1 Environment Check

> 목표: Jetson Orin Nano의 환경 상태를 기록하고 이후 benchmark의 기준선을 만든다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-13T12:03:56+09:00 |
| Device | Jetson Orin Nano |
| Hostname | `nano01` |
| Active env | `yolo_env` |
| Command | `bash scripts/collect_env.sh` |
| Raw log | `artifacts/system/jetson_env_raw.log` |
| Snapshot | `docs/environment/jetson_system_snapshot.md` |

## Checklist

- [x] JetPack / L4T 확인: L4T R36.4.7
- [x] CUDA 확인: CUDA 12.6, V12.6.68
- [x] cuDNN 확인: libcudnn9 9.3.0.75-1
- [x] TensorRT 확인: TensorRT packages 10.3.0.30-1+cuda12.5, trtexec v100300
- [x] Python / pip 확인: Python 3.10.12, pip 26.0.1 in `yolo_env`
- [x] PyTorch 설치 여부 확인: torch 2.8.0
- [x] PyTorch CUDA 사용 가능 여부 확인: True
- [x] ONNX Runtime 설치 여부 확인: onnxruntime 1.23.2
- [x] power mode 확인: 25W, mode id 1
- [x] `tegrastats` 동작 확인: 5-second idle smoke captured
- [x] memory / disk / swap 확인: 7.4 GiB RAM, 3.7 GiB swap, 833G root disk available
- [x] Docker / Git / SSH 확인: Docker 29.4.0, Git 2.34.1, OpenSSH 8.9p1

## Findings

- Jetson OS baseline is Ubuntu 22.04.5 LTS with L4T R36.4.7 and kernel 5.15.148-tegra.
- CUDA compiler is available at version 12.6, and PyTorch 2.8.0 reports CUDA availability as `True`.
- TensorRT packages are installed at 10.3.0.30-1+cuda12.5; `trtexec --version` emits TensorRT v100300 before printing help text.
- ONNX Runtime 1.23.2 is installed, but available providers are `AzureExecutionProvider` and `CPUExecutionProvider`; CUDA/TensorRT providers are not listed in the active `yolo_env`.
- Current power mode is 25W, mode id 1. Non-interactive `sudo nvpmodel -q` fails because sudo requires a password, but plain `nvpmodel -q` succeeds.
- Idle tegrastats smoke shows GR3D 0%, RAM about 877/7620 MB, GPU around 40 C, and VDD_IN around 4.3 W.
- Root filesystem is NVMe-backed at `/dev/nvme0n1p1`, with 915G total and 833G available.

## Risks / Gaps

- GitHub clone from the Jetson failed because HTTPS requires credentials and SSH public key auth is not configured. The local Jetson repo was initialized manually with origin metadata.
- The repo has no commits yet, so `git rev-parse --short HEAD` is unavailable in the raw log.
- ONNX Runtime GPU/TensorRT provider availability is not established in `yolo_env`; treat future ONNX Runtime results as CPU-only until providers are installed or a different env is selected.
- `sudo nvpmodel -q` cannot be used in non-interactive scripts without passwordless sudo or an interactive step.

## Next Step

Add `benchmarks/system/` smoke benchmarks for CPU, NumPy, PyTorch CPU/CUDA tensor ops, and disk I/O, then run them under the same 25W power mode with tegrastats logging.
