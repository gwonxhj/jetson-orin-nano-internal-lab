# Jetson Orin Nano Internal Lab

Jetson Orin Nano를 외부 카메라, 센서, 로봇 부품 없이 순수 내부 edge AI 실험 장비로 사용해 환경 점검, TensorRT 최적화, runtime comparison, InferEdge-compatible evidence를 재현 가능한 형태로 정리하는 프로젝트입니다.

이 repo의 포트폴리오 메시지는 단순 latency 숫자가 아니라, **환경 조건 → 실행 스크립트 → raw log → JSON result → Markdown report → InferEdge handoff**까지 이어지는 추적 가능한 evidence입니다.

Public snapshot: [v0.1-public-evidence-snapshot](https://github.com/gwonxhj/jetson-orin-nano-internal-lab/releases/tag/v0.1-public-evidence-snapshot)

## Representative Evidence

- [Portfolio evidence index](docs/reports/portfolio_evidence_index.md) — ResNet18 runtime, FastAPI serving, Whisper audio, LLM smoke, InferEdge export 흐름을 어떤 순서로 보면 되는지 한 장으로 안내합니다.
- [ResNet18 runtime matrix summary](docs/reports/resnet18_runtime_matrix_summary.md) — PyTorch CUDA, ONNX Runtime CPU/CUDA/TensorRT EP, native TensorRT, TensorRT EP cache 비용을 한 장으로 요약합니다.
- [TensorRT FP16 optimization report](docs/reports/tensorrt_optimization_report.md) — ResNet18 ONNX export, `trtexec` build/run command, model hash, input shape, precision, warmup/repeat 조건을 기록합니다.
- [FastAPI API usage report](docs/reports/fastapi_api_usage.md) — `/health`, `/v1/models`, ResNet18 synthetic inference, Whisper speech transcription API 호출 흐름과 evidence 산출물 연결을 설명합니다.
- [Whisper / FastAPI Whisper exports](docs/reports/portfolio_evidence_index.md) — Offline transcription과 FastAPI serving 결과를 `metadata.json` / `result.json` handoff evidence로 연결합니다.

전체 report map과 보조 evidence 링크는 [portfolio evidence index](docs/reports/portfolio_evidence_index.md)와 [Evidence Map](#evidence-map)에 위임합니다.
공개 포트폴리오 관점의 최종 해석은 [portfolio final review](docs/reports/portfolio_final_review.md)에 정리하고, 현재 공개 snapshot에 포함된 핵심 artifact는 [evidence release notes](docs/reports/evidence_release_notes.md)에 묶습니다.

## Scope

포함:

- Jetson 내부 명령어 기반 환경 점검
- system baseline smoke benchmark
- CUDA/GPU compute smoke and host/device transfer baseline
- PyTorch CUDA image inference smoke
- ONNX Runtime CPU provider inference smoke와 CUDA provider availability 확인
- ONNX Runtime CUDA Execution Provider 격리 활성화 시도 기록
- ONNX Runtime TensorRT Execution Provider 격리 활성화 시도 기록
- ONNX Runtime TensorRT EP provider option과 engine cache cold/warm 비교
- JetPack 6 / CUDA 12.6 / cuDNN 9용 ONNX Runtime GPU wheel 후보 검증
- ResNet18 ONNX export와 TensorRT FP16 `trtexec` engine smoke
- PyTorch CUDA FP32 vs ONNX Runtime CPU FP32 vs ONNX Runtime CUDA FP32 vs ONNX Runtime TensorRT FP32 vs TensorRT FP16 runtime comparison
- FastAPI localhost ResNet18 inference server smoke
- FastAPI `/health`, `/v1/models`, `/v1/infer/resnet18/synthetic`, `/v1/infer/whisper/speech` API usage flow
- FastAPI localhost ResNet18 short concurrency smoke
- FastAPI localhost Whisper speech transcription server smoke
- FastAPI localhost serving boundary notes
- FastAPI serving smoke의 InferEdge-compatible `metadata.json` / `result.json` export
- FastAPI Whisper serving smoke의 InferEdge-compatible `metadata.json` / `result.json` export
- Whisper tiny/base offline transcription smoke with separate synthetic tone and generated speech inputs
- Whisper speech smoke의 InferEdge-compatible `metadata.json` / `result.json` export
- Whisper isolated env candidate probe for `openai-whisper` and `faster-whisper`
- LLM isolated env candidate probe and tiny text-generation smoke readiness evidence
- LLM text-generation smoke의 InferEdge-compatible `metadata.json` / `result.json` export
- InferEdge-compatible `metadata.json` / `result.json` export
- CI-style InferEdge handoff schema validation

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

### 7. ONNX Runtime TensorRT EP Activation Attempt

같은 격리 env `ort_cuda_env`에서 ONNX Runtime `TensorrtExecutionProvider`를 활성화하고, native `trtexec`와는 별개의 ORT TensorRT provider path evidence로 기록합니다.

```bash
bash scripts/run_onnxruntime_tensorrt_ep_attempt.sh
```

주요 산출물:

- `results/inference/onnxruntime_tensorrt_ep_attempt_20260514_025120.json`
- `docs/reports/onnxruntime_tensorrt_ep_activation_attempt.md`

현재 ONNX Runtime TensorRT EP smoke 결과:

| Runtime | Provider | Precision | Mean ms | P95 ms | Activation |
|---|---|---|---:|---:|---|
| ONNX Runtime | TensorrtExecutionProvider | FP32 | 4.0276 | 5.4686 | succeeded |

### 8. ONNX Runtime TensorRT EP Engine Cache

ORT TensorRT EP provider option을 명시하고 engine cache를 켠 상태에서 cold build와 warm cache session creation을 분리해 기록합니다.

```bash
bash scripts/run_onnxruntime_tensorrt_cache_bench.sh
```

주요 산출물:

- `results/inference/onnxruntime_tensorrt_cache_bench_20260514_030413.json`
- `docs/reports/onnxruntime_tensorrt_cache_bench.md`
- `artifacts/tensorrt/ort_trt_engine_cache/resnet18_fp32/resnet18_fp32_12793127510422195378_0_sm87.engine`

현재 cache benchmark 결과:

| Phase | Session create ms | First run ms | Mean ms | P95 ms |
|---|---:|---:|---:|---:|
| Cold build | 24489.9395 | 8.2652 | 4.1027 | 5.5288 |
| Warm cache | 2175.843 | 6.7976 | 4.0811 | 5.4887 |

Provider options:

| Option | Value |
|---|---|
| `trt_engine_cache_enable` | `True` |
| `trt_engine_cache_path` | `artifacts/tensorrt/ort_trt_engine_cache/resnet18_fp32` |
| `trt_engine_cache_prefix` | `resnet18_fp32` |
| `trt_fp16_enable` | `False` |

### 9. ONNX Runtime CUDA Env Candidate Probe

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

### 10. Runtime Compare

PyTorch CUDA FP32, ONNX Runtime CPU FP32, ONNX Runtime CUDA FP32, ONNX Runtime TensorRT FP32, TensorRT FP16 결과를 별도 runtime comparison evidence로 묶습니다. 같은 model hash와 input shape를 사용하지만 backend/provider/precision이 다르므로 direct regression이 아니라 runtime comparison입니다.

```bash
bash scripts/run_runtime_compare.sh
```

주요 산출물:

- `results/runtime_compare/resnet18_pytorch_cuda_fp32_vs_onnxruntime_cpu_fp32_vs_onnxruntime_cuda_fp32_vs_onnxruntime_tensorrt_fp32_vs_tensorrt_fp16_20260514_025504.json`
- `docs/reports/runtime_comparison.md`

현재 comparison 요약:

| Runtime | Precision | Input shape | Mean ms | P95 ms |
|---|---|---|---:|---:|
| PyTorch CUDA | FP32 | `[1, 3, 224, 224]` | 11.6289 | 16.3123 |
| ONNX Runtime CPU | FP32 | `[1, 3, 224, 224]` | 42.2252 | 44.6845 |
| ONNX Runtime CUDA | FP32 | `[1, 3, 224, 224]` | 6.7277 | 7.3183 |
| ONNX Runtime TensorRT | FP32 | `[1, 3, 224, 224]` | 4.0276 | 5.4686 |
| TensorRT trtexec | FP16 | `[1, 3, 224, 224]` | 0.926784 | 0.932251 |

- Same model hash: true
- Same input shape: true
- Same precision: false
- Verdict: `runtime_comparison_not_direct_regression`
- Mean latency PyTorch/TensorRT ratio: `12.5476x`
- Mean latency ONNX Runtime/TensorRT ratio: `45.561x`
- Mean latency ONNX Runtime CUDA/TensorRT ratio: `7.2592x`
- Mean latency ONNX Runtime TensorRT/TensorRT ratio: `4.3458x`

### 11. FastAPI Local Inference Server

같은 ResNet18 random seeded model hash를 FastAPI localhost server로 감싸고, client roundtrip latency와 server-side PyTorch CUDA inference latency를 분리해 기록합니다. 같은 server app은 `whisper_env`에서 license-clear generated speech WAV를 Whisper tiny CUDA transcription endpoint로도 노출합니다.

```bash
bash scripts/run_fastapi_server_smoke.sh
FASTAPI_CONCURRENCY_LEVELS=1,2,4 FASTAPI_REQUESTS_PER_LEVEL=8 bash scripts/run_fastapi_concurrency_smoke.sh
conda activate whisper_env
bash scripts/run_fastapi_whisper_smoke.sh
```

주요 산출물:

- `results/inference/fastapi_resnet18_server_20260514_142053.json`
- `artifacts/system/fastapi_resnet18_server_20260514_142053.log`
- `artifacts/system/tegrastats_fastapi_resnet18_20260514_142053.log`
- `docs/reports/fastapi_resnet18_server_smoke.md`
- `results/inference/fastapi_resnet18_concurrency_20260514_233246.json`
- `docs/reports/fastapi_concurrency_smoke.md`
- `results/inference/fastapi_whisper_speech_server_20260514_202459.json`
- `artifacts/system/fastapi_whisper_server_20260514_202459.log`
- `artifacts/system/tegrastats_fastapi_whisper_20260514_202459.log`
- `docs/reports/fastapi_whisper_speech_server_smoke.md`
- `docs/reports/fastapi_api_usage.md`
- `docs/reports/serving_boundary_notes.md`

현재 FastAPI server smoke 결과:

| Layer | Backend | Precision | Mean ms | P95 ms |
|---|---|---|---:|---:|
| Client roundtrip | localhost HTTP | FP32 | 28.5178 | 29.5806 |
| Server inference | PyTorch CUDA | FP32 | 18.415 | 19.1253 |

FastAPI concurrency smoke는 같은 endpoint를 concurrency level별로 짧게 호출합니다. 이 결과는 serving path evidence이며 capacity plan이나 deployment-ready evidence가 아닙니다.

현재 FastAPI Whisper speech server smoke 결과:

| Endpoint | Backend | Transcript | Expected matched | Client mean ms | Server mean ms |
|---|---|---|---:|---:|---:|
| `/v1/infer/whisper/speech` | CUDA | `Hello world!` | true | 3276.5571 | 1802.9543 |

### 12. FastAPI Serving InferEdge Export

FastAPI localhost serving smoke를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환합니다. Client roundtrip latency를 top-level runtime result로 두고, server-side inference/transcription latency와 endpoint 정보는 `serving` 섹션에 보존합니다.

```bash
bash scripts/export_fastapi_serving_inferedge.sh
bash scripts/export_fastapi_whisper_serving_inferedge.sh
```

주요 산출물:

- `results/inferedge/resnet18_fastapi_serving_20260514_142053/metadata.json`
- `results/inferedge/resnet18_fastapi_serving_20260514_142053/result.json`
- `docs/reports/fastapi_inferedge_export.md`
- `results/inferedge/fastapi_whisper_serving_20260514_202459/metadata.json`
- `results/inferedge/fastapi_whisper_serving_20260514_202459/result.json`
- `docs/reports/fastapi_whisper_inferedge_export.md`

현재 serving export 요약:

| Evidence | Runtime role | Endpoint | Engine backend | Verdict |
|---|---|---|---|---|
| ResNet18 FastAPI serving | `serving-result` | `/v1/infer/resnet18/synthetic` | `fastapi+pytorch` | `serving_layer_evidence_not_direct_regression` |
| Whisper FastAPI serving | `serving-result` | `/v1/infer/whisper/speech` | `fastapi+openai-whisper` | `serving_layer_evidence_not_direct_regression` |

### 13. InferEdge Export

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

### 14. Whisper Synthetic Path Smoke

외부 마이크 없이 synthetic 16kHz tone WAV를 생성하고, Whisper tiny/base audio decode/model path의 준비 상태를 기록합니다. 이 runner는 기본적으로 패키지를 설치하거나 model weight를 다운로드하지 않으므로, `dependency_missing`과 `model_missing`도 정상적인 evidence 상태입니다.

```bash
bash scripts/run_whisper_smoke.sh tiny
WHISPER_ALLOW_DOWNLOAD=1 conda run -n whisper_env bash scripts/run_whisper_smoke.sh tiny
```

주요 산출물:

- `artifacts/audio/whisper_smoke_16khz.wav`
- `artifacts/system/tegrastats_whisper_tiny_20260514_180622.log`
- `results/inference/whisper_tiny_transcription_20260514_180622.json`
- `docs/reports/whisper_transcription_smoke.md`

현재 Whisper smoke 결과:

| Model | Status | Env | Backend | Mean ms | Real-time factor | Package install/download |
|---|---|---|---|---:|---:|---|
| `tiny` | `succeeded` | `whisper_env` | `cuda` | 1766.6792 | 1.7667 | `openai-whisper` installed in isolated env, tiny weight cache present |

### 15. Whisper Speech Transcription Smoke

외부 마이크를 쓰지 않고 `ffmpeg` `flite` filter로 license-clear generated speech WAV를 만들어 실제 transcription path를 synthetic tone smoke와 분리합니다. 이 결과는 짧은 문구 smoke이며, 넓은 음성 인식 정확도 benchmark나 deployment-ready evidence가 아닙니다.

```bash
bash scripts/generate_whisper_speech_sample.sh
WHISPER_ALLOW_DOWNLOAD=1 conda run -n whisper_env bash scripts/run_whisper_speech_smoke.sh tiny
```

주요 산출물:

- `examples/audio/license_clear_whisper_smoke.wav`
- `artifacts/system/tegrastats_whisper_speech_tiny_20260514_182822.log`
- `results/inference/whisper_tiny_speech_transcription_20260514_182822.json`
- `docs/reports/whisper_speech_transcription_smoke.md`

현재 Whisper speech smoke 결과:

| Model | Status | Env | Backend | Expected | Transcript | Mean ms | Real-time factor |
|---|---|---|---|---|---|---:|---:|
| `tiny` | `succeeded` | `whisper_env` | `cuda` | `hello world` | `Hello world!` | 1701.2686 | 1.3775 |

### 16. Whisper InferEdge Export

Whisper speech transcription smoke를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환합니다. 이 export는 audio/transcription 세부 정보를 보존하지만, 여전히 짧은 license-clear smoke evidence이며 accuracy benchmark나 deployment approval이 아닙니다.

```bash
bash scripts/export_whisper_inferedge.sh
```

주요 산출물:

- `results/inferedge/whisper_tiny_speech_transcription_20260514_182822/metadata.json`
- `results/inferedge/whisper_tiny_speech_transcription_20260514_182822/result.json`
- `docs/reports/whisper_inferedge_export.md`

InferEdge-compatible 핵심 필드:

- `metadata.json`: `schema_version`, `source_model`, `artifacts`, `build`, `handoff`, `lab_compat`
- `result.json`: `schema_version`, `compare_key`, `backend_key`, `runtime_role`, `mean_ms`, `p95_ms`, `p99_ms`, `latency_ms`, `audio`, `transcription`, `jetson_evidence`, `extra.compare_ready`

### 17. Whisper Env Candidate Probe

기존 `yolo_env`를 직접 수정하지 않고, 별도 `whisper_env`를 만들기 전 `openai-whisper`와 `faster-whisper` 후보를 비교합니다. 기본 경로는 `yolo_env`를 clone해서 PyTorch CUDA stack을 보존한 뒤 candidate package만 격리 설치하는 방식입니다.

```bash
bash scripts/probe_whisper_env_candidates.sh
bash scripts/create_whisper_env.sh
```

`create_whisper_env.sh`는 기본적으로 plan만 출력하며, 실제 env 생성은 명시적으로 실행할 때만 진행합니다.

```bash
bash scripts/create_whisper_env.sh --execute
```

현재 `whisper_env`는 `create_whisper_env.sh --execute`로 생성되었고, `openai-whisper==20250625`가 설치된 상태에서 tiny transcription smoke를 성공 evidence로 갱신했습니다. 기존 `yolo_env`에는 Whisper package를 직접 설치하지 않았습니다.

주요 산출물:

- `results/inference/whisper_env_candidates_20260514_175410.json`
- `docs/reports/whisper_env_candidate_probe.md`

현재 candidate probe 결과:

| Candidate | Verdict | Notes |
|---|---|---|
| `openai-whisper` | `recommended_first_isolated_candidate` | cloned `yolo_env`의 Jetson PyTorch CUDA stack을 재사용하는 첫 후보 |
| `faster-whisper` | `secondary_isolated_candidate_requires_cuda_validation` | CTranslate2 CUDA/aarch64 호환성을 별도 검증해야 하는 최적화 후보 |

### 18. LLM Env Candidate Probe and Tiny Text Generation Smoke

기존 `yolo_env`에 LLM package를 바로 설치하지 않고, 별도 `llm_env` 후보와 tiny text-generation smoke를 격리 검증합니다. 기본 smoke는 package 설치나 model download를 수행하지 않으며, `dependency_missing` / `model_missing`도 안전한 readiness evidence로 기록합니다.

```bash
bash scripts/create_llm_env.sh
bash scripts/probe_llm_env_candidates.sh
bash scripts/run_llm_smoke.sh tiny-gpt2
```

실제 env 생성은 명시적으로 실행할 때만 진행합니다.

```bash
bash scripts/create_llm_env.sh --execute
LLM_ALLOW_DOWNLOAD=1 conda run -n llm_env bash scripts/run_llm_smoke.sh tiny-gpt2
```

주요 산출물:

- `results/llm/llm_env_candidates_20260515_010032.json`
- `results/llm/llm_tiny-gpt2_text_generation_20260515_005755.json`
- `artifacts/system/tegrastats_llm_tiny-gpt2_20260515_005755.log`
- `docs/reports/llm_env_candidate_probe.md`
- `docs/reports/llm_text_generation_smoke.md`

현재 LLM smoke 상태:

| Model | Env | Backend | Device | Status | Mean ms |
|---|---|---|---|---|---:|
| `sshleifer/tiny-gpt2` | `llm_env` | `transformers 5.8.1` | `cuda` | `succeeded` | 660.2308 |

주의: 이 결과는 tiny model path smoke이며 text quality나 deployment-ready evidence가 아닙니다. 기존 `yolo_env`에는 `transformers`를 설치하지 않았습니다.

### 19. LLM InferEdge Export

LLM tiny text-generation smoke를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환합니다. `result.json`은 text-generation 세부 정보를 `text_generation`에 보존하며, 이 결과는 text quality benchmark나 deployment approval이 아닙니다.

```bash
bash scripts/export_llm_inferedge.sh
```

주요 산출물:

- `results/inferedge/llm_tiny-gpt2_text_generation_20260515_005755/metadata.json`
- `results/inferedge/llm_tiny-gpt2_text_generation_20260515_005755/result.json`
- `docs/reports/llm_inferedge_export.md`

InferEdge-compatible 핵심 필드:

- `metadata.json`: `schema_version`, `source_model`, `artifacts`, `build`, `handoff`, `lab_compat`
- `result.json`: `schema_version`, `compare_key`, `backend_key`, `runtime_role`, `mean_ms`, `p95_ms`, `p99_ms`, `latency_ms`, `text_generation`, `jetson_evidence`, `extra.compare_ready`

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
| ONNX Runtime TensorRT EP attempt | `scripts/run_onnxruntime_tensorrt_ep_attempt.sh` | `results/inference/onnxruntime_tensorrt_ep_attempt_20260514_025120.json` | `docs/reports/onnxruntime_tensorrt_ep_activation_attempt.md` |
| ONNX Runtime TensorRT cache | `scripts/run_onnxruntime_tensorrt_cache_bench.sh` | `results/inference/onnxruntime_tensorrt_cache_bench_20260514_030413.json` | `docs/reports/onnxruntime_tensorrt_cache_bench.md` |
| ONNX Runtime CUDA env candidate probe | `scripts/probe_ort_cuda_wheel_candidates.sh` | `results/inference/ort_cuda_wheel_candidates_20260514_020616.json` | `docs/reports/onnxruntime_cuda_env_candidate_probe.md` |
| Runtime compare | `scripts/run_runtime_compare.sh` | `results/runtime_compare/resnet18_pytorch_cuda_fp32_vs_onnxruntime_cpu_fp32_vs_onnxruntime_cuda_fp32_vs_onnxruntime_tensorrt_fp32_vs_tensorrt_fp16_20260514_025504.json` | `docs/reports/runtime_comparison.md` |
| Runtime matrix summary | n/a | existing runtime/cache results | `docs/reports/resnet18_runtime_matrix_summary.md` |
| FastAPI server smoke | `scripts/run_fastapi_server_smoke.sh` | `results/inference/fastapi_resnet18_server_20260514_142053.json` | `docs/reports/fastapi_resnet18_server_smoke.md` |
| FastAPI concurrency smoke | `scripts/run_fastapi_concurrency_smoke.sh` | `results/inference/fastapi_resnet18_concurrency_20260514_233246.json` | `docs/reports/fastapi_concurrency_smoke.md` |
| FastAPI Whisper server smoke | `scripts/run_fastapi_whisper_smoke.sh` | `results/inference/fastapi_whisper_speech_server_20260514_202459.json` | `docs/reports/fastapi_whisper_speech_server_smoke.md` |
| FastAPI API usage | n/a | existing FastAPI server smoke and serving export results | `docs/reports/fastapi_api_usage.md` |
| FastAPI serving boundary | n/a | existing FastAPI server smoke and serving export results | `docs/reports/serving_boundary_notes.md` |
| FastAPI serving InferEdge export | `scripts/export_fastapi_serving_inferedge.sh` | `results/inferedge/resnet18_fastapi_serving_20260514_142053/result.json` | `docs/reports/fastapi_inferedge_export.md` |
| FastAPI Whisper serving InferEdge export | `scripts/export_fastapi_whisper_serving_inferedge.sh` | `results/inferedge/fastapi_whisper_serving_20260514_202459/result.json` | `docs/reports/fastapi_whisper_inferedge_export.md` |
| Whisper transcription smoke | `scripts/run_whisper_smoke.sh` | `results/inference/whisper_tiny_transcription_20260514_180622.json` | `docs/reports/whisper_transcription_smoke.md` |
| Whisper speech transcription smoke | `scripts/run_whisper_speech_smoke.sh` | `results/inference/whisper_tiny_speech_transcription_20260514_182822.json` | `docs/reports/whisper_speech_transcription_smoke.md` |
| Whisper InferEdge export | `scripts/export_whisper_inferedge.sh` | `results/inferedge/whisper_tiny_speech_transcription_20260514_182822/result.json` | `docs/reports/whisper_inferedge_export.md` |
| Whisper env candidate probe | `scripts/probe_whisper_env_candidates.sh` | `results/inference/whisper_env_candidates_20260514_175410.json` | `docs/reports/whisper_env_candidate_probe.md` |
| LLM env candidate probe | `scripts/probe_llm_env_candidates.sh` | `results/llm/llm_env_candidates_20260515_010032.json` | `docs/reports/llm_env_candidate_probe.md` |
| LLM text-generation smoke | `scripts/run_llm_smoke.sh` | `results/llm/llm_tiny-gpt2_text_generation_20260515_005755.json` | `docs/reports/llm_text_generation_smoke.md` |
| LLM InferEdge export | `scripts/export_llm_inferedge.sh` | `results/inferedge/llm_tiny-gpt2_text_generation_20260515_005755/result.json` | `docs/reports/llm_inferedge_export.md` |
| InferEdge schema validation | `scripts/validate_inferedge_artifacts.sh` | all `results/inferedge/*/{metadata.json,result.json}` pairs | `docs/reports/inferedge_schema_validation.md` |
| Portfolio final review | n/a | current evidence chain | `docs/reports/portfolio_final_review.md` |
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
  benchmarks/inference/onnxruntime_tensorrt_cache_bench.py \
  benchmarks/inference/ort_cuda_wheel_candidate_probe.py \
  benchmarks/inference/fastapi_resnet18_client_smoke.py \
  benchmarks/inference/fastapi_concurrency_smoke.py \
  benchmarks/inference/fastapi_whisper_client_smoke.py \
  benchmarks/inference/whisper_transcription_smoke.py \
  benchmarks/inference/whisper_env_candidate_probe.py \
  benchmarks/inference/llm_env_candidate_probe.py \
  benchmarks/inference/llm_text_generation_smoke.py \
  benchmarks/tensorrt/resnet18_trtexec_smoke.py \
  benchmarks/runtime_compare/build_runtime_comparison.py \
  src/server/resnet18_app.py \
  scripts/export_fastapi_serving_inferedge.py \
  scripts/export_fastapi_whisper_serving_inferedge.py \
  scripts/export_llm_inferedge.py \
  scripts/validate_inferedge_artifacts.py \
  tests/test_system_baseline_json.py \
  tests/test_cuda_compute_json.py \
  tests/test_inference_smoke_json.py \
  tests/test_onnxruntime_smoke_json.py \
  tests/test_onnxruntime_cuda_ep_attempt_json.py \
  tests/test_onnxruntime_tensorrt_cache_bench_json.py \
  tests/test_ort_cuda_wheel_candidate_probe_json.py \
  tests/test_tensorrt_metric_parser.py \
  tests/test_runtime_comparison.py \
  tests/test_inferedge_export.py \
  tests/test_fastapi_server_smoke.py \
  tests/test_fastapi_concurrency_smoke.py \
  tests/test_fastapi_whisper_server_smoke.py \
  tests/test_fastapi_inferedge_export.py \
  tests/test_fastapi_whisper_inferedge_export.py \
  tests/test_whisper_transcription_smoke.py \
  tests/test_whisper_env_candidate_probe.py \
  tests/test_llm_env_candidate_probe.py \
  tests/test_llm_text_generation_smoke.py \
  tests/test_llm_inferedge_export.py \
  tests/test_inferedge_artifact_validation.py

bash -n scripts/*.sh
bash scripts/validate_inferedge_artifacts.sh
python3 tests/test_system_baseline_json.py
python3 tests/test_cuda_compute_json.py
python3 tests/test_inference_smoke_json.py
python3 tests/test_onnxruntime_smoke_json.py
python3 tests/test_onnxruntime_cuda_ep_attempt_json.py
python3 tests/test_onnxruntime_tensorrt_cache_bench_json.py
python3 tests/test_ort_cuda_wheel_candidate_probe_json.py
python3 tests/test_tensorrt_metric_parser.py
python3 tests/test_runtime_comparison.py
python3 tests/test_inferedge_export.py
python3 tests/test_fastapi_server_smoke.py
python3 tests/test_fastapi_concurrency_smoke.py
python3 tests/test_fastapi_whisper_server_smoke.py
python3 tests/test_fastapi_inferedge_export.py
python3 tests/test_fastapi_whisper_inferedge_export.py
python3 tests/test_whisper_transcription_smoke.py
python3 tests/test_whisper_env_candidate_probe.py
python3 tests/test_llm_env_candidate_probe.py
python3 tests/test_llm_text_generation_smoke.py
python3 tests/test_llm_inferedge_export.py
python3 tests/test_inferedge_artifact_validation.py
```

## Interpretation Rules

- benchmark 숫자만으로 deployment-ready를 주장하지 않습니다.
- power mode, backend, precision이 다르면 direct regression이 아니라 system/runtime comparison으로 해석합니다.
- TensorRT engine build command, model hash, input shape, precision, warmup/repeat 조건을 반드시 기록합니다.
- `trtexec` GPU/host latency와 deployment-oriented runtime wall-clock latency를 같은 의미로 직접 비교하지 않습니다.
- InferEdge 호환 `metadata.json`, `result.json`, compare output format을 깨지 않습니다.
