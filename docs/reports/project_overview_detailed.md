# Jetson Orin Nano Internal Lab 프로젝트 상세 소개

> Jetson Orin Nano를 외부 카메라, 센서, 로봇 부품 없이 순수 내부 edge AI evidence lab으로 구성하고, 환경 점검부터 runtime 비교, TensorRT 최적화, FastAPI serving, Whisper/LLM smoke, YOLO detection, InferEdge-compatible handoff까지 재현 가능한 형태로 정리한 프로젝트입니다.

## 1. 프로젝트명

**Jetson Orin Nano Internal Lab**

GitHub repository:

- `gwonxhj/jetson-orin-nano-internal-lab`
- Latest release: [`v0.4-detection-handoff`](https://github.com/gwonxhj/jetson-orin-nano-internal-lab/releases/tag/v0.4-detection-handoff)

## 2. 프로젝트 목적

이 프로젝트의 목적은 Jetson Orin Nano를 단순히 "AI 모델이 돌아가는 보드"로 사용하는 것이 아니라, **실험 조건과 실행 결과를 추적 가능한 evidence chain으로 남기는 내부 엣지 AI 실험 장비**로 정리하는 것입니다.

핵심 포트폴리오 메시지는 다음과 같습니다.

> Jetson Orin Nano를 외부 센서 없이 내부 edge AI 실험 장비로 사용해, 환경 조건 -> 실행 스크립트 -> raw log -> JSON result -> Markdown report -> InferEdge-compatible handoff까지 이어지는 재현 가능한 evidence를 구축했다.

이 repo는 단일 latency 숫자만 보여주는 benchmark repo가 아닙니다. 각 결과에는 가능한 한 다음 정보를 함께 기록합니다.

- JetPack/L4T, CUDA, cuDNN, TensorRT, Python, PyTorch, ONNX Runtime 버전
- power mode, `tegrastats`, memory/disk/swap 등 시스템 조건
- backend, precision, input shape, warmup/repeat 조건
- model hash, engine build command, artifact path
- JSON result와 사람이 읽는 Markdown report
- InferEdge-compatible `metadata.json` / `result.json` handoff artifact

## 3. 설계 원칙

이 프로젝트는 다음 원칙을 유지합니다.

| 원칙 | 설명 |
|---|---|
| 내부 실험 장비화 | 외부 카메라, 센서, 마이크, 모터, 로봇 부품 없이 Jetson 내부 입력과 package/sample artifact만 사용합니다. |
| 조건 기반 해석 | power mode, backend, precision, provider가 다르면 direct regression이 아니라 runtime/system comparison으로 해석합니다. |
| 과장 방지 | 짧은 smoke benchmark만으로 deployment-ready, accuracy benchmark, capacity plan을 주장하지 않습니다. |
| 재현성 우선 | 실행 명령, raw log, JSON result, report, model/engine hash를 함께 남깁니다. |
| InferEdge 호환성 | `metadata.json`, `result.json`, compare output format을 깨지 않도록 schema validation을 유지합니다. |
| 환경 격리 | Whisper, LLM, ONNX Runtime CUDA EP 같은 후보는 기존 안정 env를 직접 오염시키지 않고 별도 env에서 검증합니다. |

## 4. 전체 Evidence 흐름

현재 evidence는 아래 순서로 읽으면 가장 자연스럽습니다.

1. **환경 점검**: JetPack/L4T, CUDA, TensorRT, Python, PyTorch, ONNX Runtime, Docker/Git/SSH 상태 확인
2. **시스템 기준선**: CPU/Python, NumPy, PyTorch CPU/CUDA, disk smoke, `tegrastats` 기록
3. **CUDA compute smoke**: 모델 추론이 아닌 일반 GPU 연산과 host/device transfer 비용 분리
4. **ResNet18 runtime smoke**: PyTorch CUDA, ONNX Runtime, TensorRT FP16, runtime/provider/cache 비교
5. **YOLO detection smoke**: 외부 카메라 없이 file-image object detection path 검증
6. **FastAPI serving layer**: ResNet18/Whisper inference를 localhost API로 감싸고 `/health`, `/v1/models`, `/metrics`, inference endpoint 사용 흐름 기록
7. **Whisper audio inference**: synthetic path smoke와 license-clear generated speech transcription smoke 분리
8. **LLM text-generation smoke**: 별도 `llm_env`에서 tiny text-generation path 검증
9. **InferEdge handoff**: runtime, detection, serving, audio, text 결과를 `metadata.json` / `result.json`으로 변환
10. **Schema validation / release**: committed handoff artifact의 schema와 artifact hash drift를 CI-style로 검증하고 release snapshot으로 고정

## 5. 구현된 주요 작업

### 5.1 Day 1 환경 점검

Jetson Orin Nano의 기본 실행 환경을 먼저 고정했습니다.

수집/기록한 항목:

- JetPack / L4T
- Ubuntu / kernel
- CUDA / cuDNN / TensorRT
- Python / pip / conda env
- PyTorch CUDA availability
- ONNX Runtime provider availability
- power mode
- `tegrastats`
- memory / disk / swap
- Docker / Git / SSH

대표 산출물:

| 구분 | 산출물 |
|---|---|
| Raw log | `artifacts/system/jetson_env_raw.log` |
| Environment snapshot | `docs/environment/jetson_system_snapshot.md` |
| Day 1 report | `docs/reports/day1_environment_check.md` |

### 5.2 System baseline과 Resource map

모델 추론 전 Jetson 자체의 기준선을 기록했습니다.

구현 내용:

- CPU Python loop smoke
- NumPy matmul smoke
- PyTorch CPU/CUDA matmul smoke
- disk read/write smoke
- idle/load `tegrastats` evidence
- Jetson resource map 문서화

대표 산출물:

| 구분 | 산출물 |
|---|---|
| System baseline JSON | `results/system/system_baseline_20260513_122758.json` |
| System baseline report | `docs/reports/system_baseline.md` |
| Resource map | `docs/system/jetson_resource_map.md` |
| Telemetry logs | `artifacts/system/tegrastats_idle.log`, `artifacts/system/tegrastats_load_smoke.log` |

### 5.3 CUDA/GPU compute smoke

모델 추론 latency와 별도로, 일반 CUDA 연산 및 host/device transfer 비용을 분리해서 기록했습니다.

구현 내용:

- CUDA/PyTorch GPU availability 확인
- GPU matmul smoke
- host-to-device / device-to-host transfer smoke
- 결과 JSON과 Markdown report 생성

대표 산출물:

| 구분 | 산출물 |
|---|---|
| Script | `scripts/run_cuda_compute_smoke.sh` |
| Result | `results/cuda/cuda_compute_smoke_20260513_151135.json` |
| Report | `docs/reports/cuda_compute_notes.md` |

### 5.4 ResNet18 PyTorch / ONNX Runtime / TensorRT runtime 비교

작은 이미지 모델인 ResNet18을 기준으로 여러 runtime/backend 경로를 비교했습니다.

구현 내용:

- PyTorch CUDA FP32 inference smoke
- ResNet18 ONNX export
- TensorRT FP16 engine build/run smoke using `trtexec`
- ONNX Runtime CPU provider smoke
- ONNX Runtime CUDA EP activation attempt
- ONNX Runtime TensorRT EP activation attempt
- TensorRT EP provider option과 engine cache cold/warm 비교
- PyTorch CUDA FP32 vs ONNX Runtime CPU/CUDA/TensorRT EP vs native TensorRT FP16 runtime comparison

대표 산출물:

| 구분 | 산출물 |
|---|---|
| PyTorch smoke | `docs/reports/pytorch_inference_smoke.md` |
| TensorRT report | `docs/reports/tensorrt_optimization_report.md` |
| ONNX Runtime report | `docs/reports/onnxruntime_inference_smoke.md` |
| Runtime comparison | `docs/reports/runtime_comparison.md` |
| Runtime matrix summary | `docs/reports/resnet18_runtime_matrix_summary.md` |
| Native TensorRT result | `results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json` |
| Runtime compare JSON | `results/runtime_compare/resnet18_pytorch_cuda_fp32_vs_onnxruntime_cpu_fp32_vs_onnxruntime_cuda_fp32_vs_onnxruntime_tensorrt_fp32_vs_tensorrt_fp16_20260514_025504.json` |

해석 원칙:

- TensorRT FP16, PyTorch FP32, ONNX Runtime provider 결과는 precision/backend가 다르므로 direct regression이 아닙니다.
- `trtexec` GPU/host latency와 deployment-oriented runtime wall-clock latency를 같은 의미로 직접 비교하지 않습니다.

### 5.5 ONNX Runtime CUDA/TensorRT provider 격리 검증

기존 `yolo_env`를 직접 망가뜨리지 않고 ONNX Runtime GPU provider 후보를 별도 환경에서 검증했습니다.

구현 내용:

- `ort_cuda_env` 생성 스크립트 작성
- JetPack 6 / CUDA 12.6 / cuDNN 9 조합의 ONNX Runtime GPU wheel 후보 검증
- `onnxruntime-gpu==1.23.0` 설치 시도
- CUDA EP activation evidence 기록
- TensorRT EP와 engine cache 조건 기록

대표 산출물:

| 구분 | 산출물 |
|---|---|
| Candidate probe | `docs/reports/onnxruntime_cuda_env_candidate_probe.md` |
| CUDA EP attempt | `docs/reports/onnxruntime_cuda_ep_activation_attempt.md` |
| TensorRT EP attempt | `docs/reports/onnxruntime_tensorrt_ep_activation_attempt.md` |
| TensorRT cache bench | `docs/reports/onnxruntime_tensorrt_cache_bench.md` |

### 5.6 FastAPI local inference server

단순 benchmark에서 한 단계 나아가 localhost serving layer를 구현하고, API 호출 흐름과 evidence export를 연결했습니다.

구현 내용:

- FastAPI app 구현
- `/health`
- `/v1/models`
- `/metrics`
- `/v1/infer/resnet18/synthetic`
- `/v1/infer/whisper/speech`
- ResNet18 synthetic inference server smoke
- short concurrency smoke
- longer soak/burst follow-up with `tegrastats`
- API usage report
- serving boundary notes

대표 산출물:

| 구분 | 산출물 |
|---|---|
| FastAPI app | `src/server/resnet18_app.py` |
| Server smoke | `docs/reports/fastapi_resnet18_server_smoke.md` |
| API usage | `docs/reports/fastapi_api_usage.md` |
| Concurrency smoke | `docs/reports/fastapi_concurrency_smoke.md` |
| Soak/burst report | `docs/reports/fastapi_soak_burst.md` |
| Boundary notes | `docs/reports/serving_boundary_notes.md` |

주의:

- 이 serving evidence는 localhost smoke입니다.
- production load test, uptime evidence, deployment approval이 아닙니다.

### 5.7 Whisper audio inference

Whisper는 음성 인식 모델입니다. 이 프로젝트에서는 외부 마이크를 쓰지 않고, 내부 파일 기반 오디오 입력으로 transcription path를 검증했습니다.

구현 내용:

- 기존 `yolo_env`를 직접 수정하지 않고 `whisper_env` 후보/생성 스크립트 작성
- `openai-whisper` / `faster-whisper` 후보 비교
- `openai-whisper==20250625` 기반 tiny transcription smoke
- synthetic tone path smoke와 generated speech transcription smoke 분리
- license-clear speech WAV sample 추가
- FastAPI Whisper speech serving smoke
- Whisper offline/serving 결과 InferEdge handoff export

대표 산출물:

| 구분 | 산출물 |
|---|---|
| Env candidate probe | `docs/reports/whisper_env_candidate_probe.md` |
| Synthetic path smoke | `docs/reports/whisper_transcription_smoke.md` |
| Speech transcription smoke | `docs/reports/whisper_speech_transcription_smoke.md` |
| FastAPI Whisper smoke | `docs/reports/fastapi_whisper_speech_server_smoke.md` |
| Whisper InferEdge export | `docs/reports/whisper_inferedge_export.md` |
| FastAPI Whisper InferEdge export | `docs/reports/fastapi_whisper_inferedge_export.md` |

주의:

- generated speech sample 하나로 broad speech recognition accuracy를 주장하지 않습니다.
- transcription path와 evidence export가 성공했다는 의미로 해석합니다.

### 5.8 LLM text-generation smoke

기존 안정 benchmark 환경을 오염시키지 않고, 별도 `llm_env`에서 local text-generation path를 검증했습니다.

구현 내용:

- `llm_env` 후보/생성 스크립트 작성
- `transformers` stack 격리 설치
- `sshleifer/tiny-gpt2` tiny text-generation smoke
- dependency_missing / model_missing 상태도 readiness evidence로 기록할 수 있게 구성
- 성공 결과를 InferEdge-compatible handoff로 export

대표 산출물:

| 구분 | 산출물 |
|---|---|
| Env candidate probe | `docs/reports/llm_env_candidate_probe.md` |
| Text generation smoke | `docs/reports/llm_text_generation_smoke.md` |
| LLM InferEdge export | `docs/reports/llm_inferedge_export.md` |
| Result JSON | `results/llm/llm_tiny-gpt2_text_generation_20260515_005755.json` |

주의:

- `tiny-gpt2` 결과는 text quality benchmark가 아닙니다.
- local text-generation plumbing이 동작한다는 path evidence입니다.

### 5.9 YOLOv8n file-image object detection

v0.4에서 선택 확장으로 YOLOv8n object detection smoke와 InferEdge handoff를 추가했습니다.

구현 내용:

- Ultralytics `yolov8n.pt` small model 사용
- 외부 카메라 없이 Ultralytics package sample image `bus.jpg` 사용
- CUDA backend에서 detection smoke 실행
- model hash, input image hash, detection count, class counts, latency, `tegrastats` 기록
- `object-detection-result` role을 InferEdge-compatible schema에 추가
- YOLO smoke result를 `metadata.json` / `result.json` handoff로 export
- schema validation에 object detection role 추가
- v0.4 GitHub Release로 고정

대표 산출물:

| 구분 | 산출물 |
|---|---|
| Script | `scripts/run_yolo_detection_smoke.sh` |
| Export script | `scripts/export_yolo_detection_inferedge.sh` |
| Smoke report | `docs/reports/yolo_detection_smoke.md` |
| InferEdge export report | `docs/reports/yolo_inferedge_export.md` |
| Smoke JSON | `results/inference/yolo_yolov8n_detection_20260516_010734.json` |
| Handoff result | `results/inferedge/yolo_yolov8n_detection_20260516_010734/result.json` |
| Model artifact | `models/yolov8n.pt` |

현재 YOLO smoke 해석:

- YOLOv8n CUDA file-image detection path가 Jetson에서 동작함
- sample image 기준 detection count와 class counts가 기록됨
- broad object detection accuracy를 증명하지 않음
- external camera/sensor dependency가 없음
- deployment-ready proof가 아님

### 5.10 InferEdge-compatible handoff schema

여러 runtime과 serving 결과를 공통 handoff 구조로 변환했습니다.

지원하는 runtime role:

| Runtime role | 의미 |
|---|---|
| `runtime-result` | ResNet18 runtime comparison handoff |
| `serving-result` | FastAPI ResNet18/Whisper serving handoff |
| `audio-transcription-result` | Whisper offline transcription handoff |
| `text-generation-result` | LLM text-generation handoff |
| `object-detection-result` | YOLO detection handoff |

구현 내용:

- 공통 schema helper: `src/common/inferedge_schema.py`
- 각 track별 exporter script
- `metadata.json` artifact hash validation
- `result.json` role semantics validation
- CI-style validation script와 GitHub Actions workflow

대표 산출물:

| 구분 | 산출물 |
|---|---|
| Schema helper | `src/common/inferedge_schema.py` |
| Validation script | `scripts/validate_inferedge_artifacts.sh` |
| Validation report | `docs/reports/inferedge_schema_validation.md` |
| GitHub Actions workflow | `.github/workflows/inferedge-schema.yml` |

현재 validation 상태:

- 8개 InferEdge handoff directory validated
- strict artifact hash check enabled
- GitHub Actions schema validation passing

## 6. Release History

| Release | Evidence Commit | 의미 |
|---|---|---|
| [`v0.1-public-evidence-snapshot`](https://github.com/gwonxhj/jetson-orin-nano-internal-lab/releases/tag/v0.1-public-evidence-snapshot) | `bc0dcc5` | 환경, runtime, serving, Whisper, LLM, InferEdge handoff를 포함한 초기 공개 evidence snapshot |
| [`v0.2-serving-soak-evidence`](https://github.com/gwonxhj/jetson-orin-nano-internal-lab/releases/tag/v0.2-serving-soak-evidence) | `43c4390` | FastAPI soak/burst serving milestone과 serving InferEdge export |
| [`v0.3-observability-smoke`](https://github.com/gwonxhj/jetson-orin-nano-internal-lab/releases/tag/v0.3-observability-smoke) | `7c270c1` | FastAPI `/metrics` localhost observability smoke와 metrics-aware serving export |
| [`v0.4-detection-handoff`](https://github.com/gwonxhj/jetson-orin-nano-internal-lab/releases/tag/v0.4-detection-handoff) | `bc09365` | YOLOv8n file-image object detection smoke와 InferEdge-compatible object-detection handoff |

## 7. 프로젝트 구조 요약

```text
jetson-orin-nano-internal-lab/
  README.md
  AGENTS.md
  docs/
    environment/      Jetson environment snapshots
    system/           resource map and system notes
    reports/          benchmark, serving, release, safety, portfolio reports
  benchmarks/
    system/           system baseline scripts
    cuda/             CUDA/GPU compute smoke
    inference/        PyTorch, ONNX Runtime, Whisper, LLM, YOLO smoke scripts
    runtime_compare/  backend/runtime comparison scripts
  src/
    common/           InferEdge schema and shared helpers
    inference/        inference helper modules
    server/           FastAPI local inference server
  examples/           image/audio/text sample inputs
  models/             model artifact notes and small tracked model evidence
  artifacts/          raw logs, TensorRT engines, telemetry artifacts
  results/            JSON results and InferEdge handoff artifacts
  scripts/            command entrypoints
  tests/              JSON/schema/script smoke tests
```

## 8. 공개 포트폴리오에서 주장할 수 있는 것

이 프로젝트로 주장할 수 있는 내용:

- Jetson Orin Nano 환경과 power/runtime 조건을 기록한 뒤 benchmark를 해석했다.
- ResNet18 inference path를 PyTorch CUDA, ONNX Runtime, TensorRT EP, native TensorRT로 분리해 비교했다.
- TensorRT FP16 engine build/run evidence에 model hash, input shape, precision, warmup/repeat, build command를 기록했다.
- FastAPI localhost serving layer로 image/audio inference API path를 검증했다.
- `/metrics` endpoint를 추가해 in-process observability smoke를 남겼다.
- Whisper transcription과 LLM text-generation을 안정 env와 분리해 검증했다.
- YOLOv8n file-image object detection을 외부 카메라 없이 실행하고 InferEdge handoff로 연결했다.
- 여러 evidence를 InferEdge-compatible `metadata.json` / `result.json`으로 export하고 schema validation으로 drift를 감시했다.

## 9. 주장하지 않는 것

이 프로젝트가 주장하지 않는 내용:

- production deployment-ready 상태
- production uptime 또는 capacity planning
- broad object detection accuracy
- broad speech recognition accuracy
- LLM text quality
- backend/precision/power mode가 다른 결과 간 direct regression
- 외부 카메라, 마이크, 센서, 모터, 로봇 하드웨어 validation

## 10. 대표 문서 링크

| 목적 | 문서 |
|---|---|
| 전체 evidence 읽는 순서 | [Portfolio evidence index](portfolio_evidence_index.md) |
| 공개 관점 최종 해석 | [Portfolio final review](portfolio_final_review.md) |
| 공개 snapshot artifact 묶음 | [Evidence release notes](evidence_release_notes.md) |
| 공개 안전 점검 | [Public safety check](public_safety_check.md) |
| Runtime matrix 요약 | [ResNet18 runtime matrix summary](resnet18_runtime_matrix_summary.md) |
| FastAPI 사용 흐름 | [FastAPI API usage](fastapi_api_usage.md) |
| YOLO detection handoff | [YOLO InferEdge export](yolo_inferedge_export.md) |
| Schema validation | [InferEdge schema validation](inferedge_schema_validation.md) |

## 11. 한 줄 소개

Jetson Orin Nano를 외부 센서 없이 순수 내부 edge AI 실험 장비로 사용해, 환경 점검부터 TensorRT 최적화, runtime/provider 비교, FastAPI serving, Whisper/LLM/YOLO smoke, InferEdge-compatible handoff까지 재현 가능한 evidence chain으로 정리한 프로젝트입니다.
