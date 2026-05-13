# Jetson Orin Nano Internal Lab

Jetson Orin Nano를 외부 카메라, 센서, 로봇 부품 없이 순수 내부 edge AI 실험 장비로 사용해 환경 점검, TensorRT 최적화, runtime comparison, InferEdge-compatible evidence를 재현 가능한 형태로 정리하는 프로젝트입니다.

이 repo의 포트폴리오 메시지는 단순 latency 숫자가 아니라, **환경 조건 → 실행 스크립트 → raw log → JSON result → Markdown report → InferEdge handoff**까지 이어지는 추적 가능한 evidence입니다.

## Representative Evidence

- [TensorRT FP16 optimization report](docs/reports/tensorrt_optimization_report.md) — ResNet18 ONNX export, `trtexec` build/run command, model hash, input shape, precision, warmup/repeat 조건을 기록합니다.
- [Runtime comparison report](docs/reports/runtime_comparison.md) — PyTorch CUDA FP32와 TensorRT FP16 결과를 direct regression이 아닌 system/runtime comparison evidence로 정리합니다.
- [ONNX Runtime CUDA EP activation attempt](docs/reports/onnxruntime_cuda_ep_activation_attempt.md) — 기존 `yolo_env`를 변경하지 않고 CUDAExecutionProvider 활성화 가능 여부를 evidence로 기록합니다.
- [InferEdge-compatible export report](docs/reports/inferedge_export.md) — runtime comparison 결과를 `metadata.json` / `result.json` handoff evidence로 변환한 내용을 설명합니다.

## Scope

포함:

- Jetson 내부 명령어 기반 환경 점검
- system baseline smoke benchmark
- CUDA/GPU compute smoke and host/device transfer baseline
- PyTorch CUDA image inference smoke
- ONNX Runtime CPU provider inference smoke와 CUDA provider availability 확인
- ONNX Runtime CUDA Execution Provider 격리 활성화 시도 기록
- JetPack 6 / CUDA 12.6 / cuDNN 9용 ONNX Runtime GPU wheel 후보 검증
- ResNet18 ONNX export와 TensorRT FP16 `trtexec` engine smoke
- PyTorch CUDA FP32 vs ONNX Runtime CPU FP32 vs ONNX Runtime CUDA FP32 vs TensorRT FP16 runtime comparison
- InferEdge-compatible `metadata.json` / `result.json` export

제외:

- 외부 카메라, 센서, 모터, 로봇 부품 의존 실험
- benchmark 숫자만으로 deployment-ready 주장
- power mode, backend, precision이 다른 결과의 direct regression 판정

## Portfolio Quickstart

Jetson Orin Nano에서 실행합니다. 현재 검증된 Python 환경은 `yolo_env`입니다.

```bash
cd ~/jetson-orin-nano-internal-lab
source ~/miniconda3/etc/profile.d/conda.sh
conda activate yolo_env
```

### 1. Day 1 환경 점검

JetPack/L4T, CUDA, cuDNN, TensorRT, Python, PyTorch CUDA, ONNX Runtime, power mode, `tegrastats`, memory/disk/swap, Docker/Git/SSH 상태를 수집합니다.

```bash
bash scripts/collect_env.sh
```

주요 산출물:

- `artifacts/system/jetson_env_raw.log`
- `docs/environment/jetson_system_snapshot.md`
- `docs/reports/day1_environment_check.md`

현재 기록된 기준:

- L4T R36.4.7, Ubuntu 22.04.5 LTS
- CUDA 12.6, cuDNN 9.3, TensorRT 10.3
- PyTorch 2.8.0, CUDA available: true
- power mode: 25W

### 2. System Baseline

AI 모델 실행 전 CPU/Python, NumPy, PyTorch CPU, PyTorch CUDA, disk smoke 기준선을 기록합니다. `tegrastats` side log도 함께 저장합니다.

```bash
bash scripts/run_system_baseline.sh
```

주요 산출물:

- `results/system/system_baseline_20260513_122758.json`
- `artifacts/system/tegrastats_system_baseline_20260513_122758.log`
- `docs/reports/system_baseline.md`

현재 smoke 결과 예시:

| Benchmark | Mean ms | P95 ms |
|---|---:|---:|
| CPU Python loop | 516.7891 | 536.5952 |
| NumPy matmul | 2.9245 | 3.953 |
| Torch CPU matmul | 4.0727 | 4.4538 |
| Torch CUDA matmul | 1.8951 | 1.9109 |
| Disk write/read smoke | 127.1347 | 127.6417 |

### 3. PyTorch Image Inference Smoke

ResNet18, synthetic `[1, 3, 224, 224]` input, CUDA FP32 조건으로 PyTorch inference smoke를 실행합니다. Random seeded weights를 사용하므로 accuracy evidence가 아니라 runtime path evidence입니다.

```bash
bash scripts/run_inference_smoke.sh resnet18 cuda
```

주요 산출물:

- `results/inference/pytorch_resnet18_20260513_125245.json`
- `artifacts/system/tegrastats_inference_resnet18_20260513_125245.log`
- `docs/reports/pytorch_inference_smoke.md`

현재 smoke 결과:

| Runtime | Precision | Mean ms | P95 ms | Model hash |
|---|---|---:|---:|---|
| PyTorch CUDA | FP32 | 11.6289 | 16.3123 | `9300a6d...72245` |

### 4. TensorRT FP16 Engine Smoke

같은 ResNet18 canonical model hash를 ONNX로 export하고, TensorRT FP16 engine을 `trtexec`로 build/run합니다. Static ONNX shape를 사용하므로 `--shapes`는 넘기지 않습니다.

```bash
bash scripts/run_tensorrt_bench.sh resnet18
```

주요 산출물:

- `models/resnet18_random_seed42_opset17.onnx`
- `artifacts/engines/resnet18_fp16_20260513_125323.engine`
- `artifacts/tensorrt/resnet18_fp16_build_20260513_125323.log`
- `artifacts/tensorrt/resnet18_fp16_run_20260513_125323.log`
- `results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json`
- `docs/reports/tensorrt_optimization_report.md`

현재 TensorRT smoke 결과:

| Runtime | Precision | Mean ms | P95 ms | Throughput qps |
|---|---|---:|---:|---:|
| TensorRT trtexec | FP16 | 0.926784 | 0.932251 | 1134.83 |

### 5. ONNX Runtime Inference Smoke

기존 ResNet18 ONNX artifact를 ONNX Runtime으로 실행하고, CPU/CUDA Execution Provider availability를 기록합니다. 현재 `yolo_env`에서는 CPUExecutionProvider만 실행 가능하고 CUDAExecutionProvider는 사용할 수 없습니다.

```bash
bash scripts/run_onnxruntime_smoke.sh
```

주요 산출물:

- `results/inference/onnxruntime_resnet18_cpu_20260514_013723.json`
- `artifacts/system/tegrastats_onnxruntime_resnet18_20260514_013723.log`
- `docs/reports/onnxruntime_inference_smoke.md`

현재 ONNX Runtime smoke 결과:

| Runtime | Provider | Precision | Mean ms | P95 ms | CUDA EP available |
|---|---|---|---:|---:|---:|
| ONNX Runtime | CPUExecutionProvider | FP32 | 42.2252 | 44.6845 | false |

### 6. ONNX Runtime CUDA EP Activation Attempt

기존 `yolo_env`를 변경하지 않고, 별도 `ort_cuda_env`에서 ONNX Runtime `CUDAExecutionProvider`를 활성화할 수 있는지 evidence로 기록합니다. 성공, 실패, unavailable 모두 정상적인 실험 결과입니다.

```bash
bash scripts/run_onnxruntime_cuda_ep_attempt.sh
```

주요 산출물:

- `results/inference/onnxruntime_cuda_ep_attempt_20260514_023545.json`
- `docs/reports/onnxruntime_cuda_ep_activation_attempt.md`

현재 정책:

| Field | Value |
|---|---|
| Existing env modified | false |
| Isolated env | conda env `ort_cuda_env` |
| ONNX Runtime GPU | `onnxruntime-gpu==1.23.0` |
| NumPy constraint | `numpy<2` |
| Current activation status | succeeded |
| Current provider list | `TensorrtExecutionProvider`, `CUDAExecutionProvider`, `CPUExecutionProvider` |

### 7. ONNX Runtime CUDA Env Candidate Probe

JetPack 6 / CUDA 12.6 / cuDNN 9 조합에서 사용할 수 있는 Jetson용 ONNX Runtime GPU wheel 후보를 검증합니다. 이 단계는 URL/태그/환경 compatibility evidence만 만들며, 기존 Python 환경에 패키지를 설치하지 않습니다.

```bash
bash scripts/probe_ort_cuda_wheel_candidates.sh
```

주요 산출물:

- `results/inference/ort_cuda_wheel_candidates_20260514_020616.json`
- `docs/reports/onnxruntime_cuda_env_candidate_probe.md`

격리 env 생성은 명시적으로 실행할 때만 진행합니다.

```bash
bash scripts/create_ort_cuda_env.sh
bash scripts/create_ort_cuda_env.sh --execute
```

현재 정책:

| Field | Value |
|---|---|
| Existing env modified by probe | false |
| Install command executed by probe | false |
| Default env | conda env `ort_cuda_env` |
| Preferred source | Jetson AI Lab `jp6/cu126` candidate before third-party mirrors |

### 8. Runtime Compare

PyTorch CUDA FP32, ONNX Runtime CPU FP32, ONNX Runtime CUDA FP32, TensorRT FP16 결과를 별도 runtime comparison evidence로 묶습니다. 같은 model hash와 input shape를 사용하지만 backend/provider/precision이 다르므로 direct regression이 아니라 runtime comparison입니다.

```bash
bash scripts/run_runtime_compare.sh
```

주요 산출물:

- `results/runtime_compare/resnet18_pytorch_cuda_fp32_vs_onnxruntime_cpu_fp32_vs_onnxruntime_cuda_fp32_vs_tensorrt_fp16_20260514_023553.json`
- `docs/reports/runtime_comparison.md`

현재 comparison 요약:

| Runtime | Precision | Input shape | Mean ms | P95 ms |
|---|---|---|---:|---:|
| PyTorch CUDA | FP32 | `[1, 3, 224, 224]` | 11.6289 | 16.3123 |
| ONNX Runtime CPU | FP32 | `[1, 3, 224, 224]` | 42.2252 | 44.6845 |
| ONNX Runtime CUDA | FP32 | `[1, 3, 224, 224]` | 6.7277 | 7.3183 |
| TensorRT trtexec | FP16 | `[1, 3, 224, 224]` | 0.926784 | 0.932251 |

- Same model hash: true
- Same input shape: true
- Same precision: false
- Verdict: `runtime_comparison_not_direct_regression`
- Mean latency PyTorch/TensorRT ratio: `12.5476x`
- Mean latency ONNX Runtime/TensorRT ratio: `45.561x`
- Mean latency ONNX Runtime CUDA/TensorRT ratio: `7.2592x`

### 9. InferEdge Export

Runtime comparison evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환합니다. `result.json`은 Lab-compatible Runtime top-level fields를 유지하고, comparison details는 `comparison`에 보존합니다.

```bash
bash scripts/export_inferedge_evidence.sh
```

주요 산출물:

- `results/inferedge/resnet18_runtime_compare_20260513_133100/metadata.json`
- `results/inferedge/resnet18_runtime_compare_20260513_133100/result.json`
- `docs/reports/inferedge_export.md`

InferEdge-compatible 핵심 필드:

- `metadata.json`: `schema_version`, `source_model`, `artifacts`, `build`, `handoff`, `lab_compat`
- `result.json`: `schema_version`, `compare_key`, `backend_key`, `mean_ms`, `p95_ms`, `p99_ms`, `latency_ms`, `jetson_evidence`, `extra.compare_ready`, `comparison`

## Evidence Map

| Stage | Script | Result | Report |
|---|---|---|---|
| Day 1 env | `scripts/collect_env.sh` | `artifacts/system/jetson_env_raw.log` | `docs/reports/day1_environment_check.md` |
| System baseline | `scripts/run_system_baseline.sh` | `results/system/system_baseline_20260513_122758.json` | `docs/reports/system_baseline.md` |
| System resource map | `scripts/run_tegrastats.sh` | `artifacts/system/tegrastats_idle.log`, `artifacts/system/tegrastats_load_smoke.log` | `docs/system/jetson_resource_map.md` |
| CUDA compute smoke | `scripts/run_cuda_compute_smoke.sh` | `results/cuda/cuda_compute_smoke_20260513_151135.json` | `docs/reports/cuda_compute_notes.md` |
| PyTorch smoke | `scripts/run_inference_smoke.sh` | `results/inference/pytorch_resnet18_20260513_125245.json` | `docs/reports/pytorch_inference_smoke.md` |
| TensorRT FP16 | `scripts/run_tensorrt_bench.sh` | `results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json` | `docs/reports/tensorrt_optimization_report.md` |
| ONNX Runtime smoke | `scripts/run_onnxruntime_smoke.sh` | `results/inference/onnxruntime_resnet18_cpu_20260514_013723.json` | `docs/reports/onnxruntime_inference_smoke.md` |
| ONNX Runtime CUDA EP attempt | `scripts/run_onnxruntime_cuda_ep_attempt.sh` | `results/inference/onnxruntime_cuda_ep_attempt_20260514_023545.json` | `docs/reports/onnxruntime_cuda_ep_activation_attempt.md` |
| ONNX Runtime CUDA env candidate probe | `scripts/probe_ort_cuda_wheel_candidates.sh` | `results/inference/ort_cuda_wheel_candidates_20260514_020616.json` | `docs/reports/onnxruntime_cuda_env_candidate_probe.md` |
| Runtime compare | `scripts/run_runtime_compare.sh` | `results/runtime_compare/resnet18_pytorch_cuda_fp32_vs_onnxruntime_cpu_fp32_vs_onnxruntime_cuda_fp32_vs_tensorrt_fp16_20260514_023553.json` | `docs/reports/runtime_comparison.md` |
| InferEdge export | `scripts/export_inferedge_evidence.sh` | `results/inferedge/resnet18_runtime_compare_20260513_133100/result.json` | `docs/reports/inferedge_export.md` |

## Repository Layout

```text
docs/                 Markdown snapshots and reports
benchmarks/           Python benchmark/export/compare runners
scripts/              Reproducible command entrypoints
models/               ONNX model artifacts and model notes
artifacts/            Raw logs, TensorRT build/run logs, engines
results/              Structured JSON evidence
src/common/           Shared schema/export helpers
tests/                Schema and parser smoke tests
```

## Validation

Run the current test set on Jetson:

```bash
python3 -m py_compile \
  src/common/inferedge_schema.py \
  benchmarks/system/system_smoke_bench.py \
  benchmarks/cuda/cuda_compute_smoke.py \
  benchmarks/inference/pytorch_image_smoke.py \
  benchmarks/inference/onnxruntime_image_smoke.py \
  benchmarks/inference/onnxruntime_cuda_ep_attempt.py \
  benchmarks/inference/ort_cuda_wheel_candidate_probe.py \
  benchmarks/tensorrt/resnet18_trtexec_smoke.py \
  benchmarks/runtime_compare/build_runtime_comparison.py \
  tests/test_system_baseline_json.py \
  tests/test_cuda_compute_json.py \
  tests/test_inference_smoke_json.py \
  tests/test_onnxruntime_smoke_json.py \
  tests/test_onnxruntime_cuda_ep_attempt_json.py \
  tests/test_ort_cuda_wheel_candidate_probe_json.py \
  tests/test_tensorrt_metric_parser.py \
  tests/test_runtime_comparison.py \
  tests/test_inferedge_export.py

bash -n scripts/*.sh
python3 tests/test_system_baseline_json.py
python3 tests/test_cuda_compute_json.py
python3 tests/test_inference_smoke_json.py
python3 tests/test_onnxruntime_smoke_json.py
python3 tests/test_onnxruntime_cuda_ep_attempt_json.py
python3 tests/test_ort_cuda_wheel_candidate_probe_json.py
python3 tests/test_tensorrt_metric_parser.py
python3 tests/test_runtime_comparison.py
python3 tests/test_inferedge_export.py
```

## Interpretation Rules

- benchmark 숫자만으로 deployment-ready를 주장하지 않습니다.
- power mode, backend, precision이 다르면 direct regression이 아니라 system/runtime comparison으로 해석합니다.
- TensorRT engine build command, model hash, input shape, precision, warmup/repeat 조건을 반드시 기록합니다.
- `trtexec` GPU/host latency와 deployment-oriented runtime wall-clock latency를 같은 의미로 직접 비교하지 않습니다.
- InferEdge 호환 `metadata.json`, `result.json`, compare output format을 깨지 않습니다.
