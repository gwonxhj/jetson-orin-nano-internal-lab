# Portfolio Evidence Index

> Jetson Orin Nano를 외부 카메라, 센서, 로봇 부품 없이 내부 edge AI evidence lab으로 사용한 흐름을 한 장으로 묶은 안내서입니다.

## Start Here

이 프로젝트의 evidence는 **환경 조건 -> runtime 비교 -> serving layer -> audio/text inference -> InferEdge-compatible handoff** 순서로 읽으면 가장 자연스럽습니다. 각 결과는 재현 조건과 한계를 함께 기록하며, 짧은 smoke benchmark만으로 deployment-ready를 주장하지 않습니다. 공개 포트폴리오 관점의 한 장짜리 결론은 [Portfolio final review](portfolio_final_review.md)에, 공유용 snapshot artifact 묶음은 [Evidence release notes](evidence_release_notes.md)에 정리합니다.

## Recommended Reading Order

| Step | What To Read | Why It Matters | Primary Evidence |
|---:|---|---|---|
| 1 | Environment and baseline | JetPack/L4T, CUDA, TensorRT, power mode, memory, disk, `tegrastats` 기준을 먼저 고정합니다. | [Day 1 environment check](day1_environment_check.md), [System baseline](system_baseline.md), [Resource map](../system/jetson_resource_map.md) |
| 2 | CUDA and model runtime | 일반 CUDA 비용과 ResNet18 PyTorch/ONNX Runtime/TensorRT 경로를 분리해 봅니다. | [CUDA compute notes](cuda_compute_notes.md), [PyTorch smoke](pytorch_inference_smoke.md), [TensorRT report](tensorrt_optimization_report.md) |
| 3 | Runtime matrix | CPU, CUDA, ORT TensorRT EP, native TensorRT의 backend/precision/cache 차이를 direct regression이 아닌 runtime comparison으로 해석합니다. | [ResNet18 runtime matrix summary](resnet18_runtime_matrix_summary.md), [Runtime comparison](runtime_comparison.md) |
| 4 | Serving layer | ResNet18 inference와 Whisper speech transcription을 localhost FastAPI API로 감싸 client/server latency, short concurrency smoke, soak/burst follow-up, API 사용 흐름을 확인합니다. | [FastAPI server smoke](fastapi_resnet18_server_smoke.md), [FastAPI concurrency smoke](fastapi_concurrency_smoke.md), [FastAPI soak/burst](fastapi_soak_burst.md), [FastAPI Whisper smoke](fastapi_whisper_speech_server_smoke.md), [API usage](fastapi_api_usage.md), [Serving boundary](serving_boundary_notes.md) |
| 5 | Audio inference | Whisper synthetic tone path smoke와 license-clear generated speech transcription smoke를 분리합니다. | [Whisper synthetic path smoke](whisper_transcription_smoke.md), [Whisper speech smoke](whisper_speech_transcription_smoke.md) |
| 6 | Text inference readiness | 기존 `yolo_env`를 변경하지 않고 LLM 후보 env와 tiny text-generation smoke readiness를 기록합니다. | [LLM env candidate probe](llm_env_candidate_probe.md), [LLM text generation smoke](llm_text_generation_smoke.md) |
| 7 | InferEdge handoff | ResNet18 runtime, FastAPI image/audio serving, FastAPI soak/burst, Whisper speech, LLM text-generation 결과를 `metadata.json` / `result.json` handoff evidence로 변환하고 schema validation으로 drift를 확인합니다. | [Runtime InferEdge export](inferedge_export.md), [FastAPI InferEdge export](fastapi_inferedge_export.md), [FastAPI soak/burst InferEdge export](fastapi_soak_burst_inferedge_export.md), [FastAPI Whisper InferEdge export](fastapi_whisper_inferedge_export.md), [Whisper InferEdge export](whisper_inferedge_export.md), [LLM InferEdge export](llm_inferedge_export.md), [InferEdge schema validation](inferedge_schema_validation.md) |

## Evidence Tracks

| Track | Question Answered | Key Result | Handoff |
|---|---|---|---|
| ResNet18 runtime | Which local backend/runtime path works on this Jetson, under which precision and cache conditions? | [Runtime matrix summary](resnet18_runtime_matrix_summary.md) | `results/inferedge/resnet18_runtime_compare_20260513_133100/result.json` |
| FastAPI serving | Can local image and audio inference be exposed through reproducible localhost API paths, including short concurrency and longer soak/burst evidence? | [FastAPI API usage](fastapi_api_usage.md), [FastAPI concurrency smoke](fastapi_concurrency_smoke.md), [FastAPI soak/burst](fastapi_soak_burst.md), [FastAPI soak/burst InferEdge export](fastapi_soak_burst_inferedge_export.md), [FastAPI Whisper smoke](fastapi_whisper_speech_server_smoke.md), [FastAPI Whisper InferEdge export](fastapi_whisper_inferedge_export.md) | `results/inferedge/resnet18_fastapi_serving_20260514_142053/result.json`; `results/inferedge/fastapi_resnet18_soak_burst_20260515_222841/result.json`; `results/inferedge/fastapi_whisper_serving_20260514_202459/result.json` |
| Whisper audio | Can a license-clear audio input exercise the local transcription path without external sensors? | [Whisper speech smoke](whisper_speech_transcription_smoke.md) | `results/inferedge/whisper_tiny_speech_transcription_20260514_182822/result.json` |
| LLM text readiness | Can local text-generation plumbing be introduced without mutating the stable benchmark env first? | [LLM env candidate probe](llm_env_candidate_probe.md), [LLM text generation smoke](llm_text_generation_smoke.md), [LLM InferEdge export](llm_inferedge_export.md) | `results/inferedge/llm_tiny-gpt2_text_generation_20260515_005755/result.json` |

## What This Proves

- The Jetson environment and power/runtime conditions are recorded alongside results.
- ResNet18 inference paths were exercised across PyTorch, ONNX Runtime, TensorRT EP, and native TensorRT evidence.
- A localhost FastAPI serving layer can produce structured image, audio, short concurrency, and soak/burst result evidence without claiming production readiness.
- Whisper tiny can run in an isolated `whisper_env` and transcribe a license-clear generated speech sample on CUDA.
- LLM text-generation support runs in an isolated `llm_env`; current tiny-gpt2 CUDA path smoke succeeded while stable `yolo_env` remains unmodified.
- InferEdge-compatible `metadata.json` / `result.json` exports exist for runtime, FastAPI image serving, FastAPI audio serving, audio transcription, and LLM text-generation tracks.
- CI-style schema validation now checks all committed InferEdge handoff pairs for schema semantics and artifact sha256 drift.

## What This Does Not Prove

- It does not prove deployment readiness, uptime, production concurrency behavior, or production observability.
- The concurrency and soak/burst evidence is localhost-only; it is not a capacity plan or production load test.
- It does not treat backend/precision changes as direct regressions.
- It does not claim broad speech recognition accuracy from a single generated `hello world` sample.
- It does not claim LLM text quality or deployment readiness; the current tiny-gpt2 result is path smoke evidence only.
- It does not rely on external camera, microphone, sensor, motor, or robot hardware.

## Fast Links

- [README Quickstart](../../README.md#portfolio-quickstart)
- [Portfolio final review](portfolio_final_review.md)
- [Evidence release notes](evidence_release_notes.md)
- [Public safety check](public_safety_check.md)
- [Evidence Map](../../README.md#evidence-map)
- [InferEdge runtime result](../../results/inferedge/resnet18_runtime_compare_20260513_133100/result.json)
- [InferEdge serving result](../../results/inferedge/resnet18_fastapi_serving_20260514_142053/result.json)
- [InferEdge soak/burst serving result](../../results/inferedge/fastapi_resnet18_soak_burst_20260515_222841/result.json)
- [FastAPI Whisper serving result](../../results/inference/fastapi_whisper_speech_server_20260514_202459.json)
- [InferEdge FastAPI Whisper serving result](../../results/inferedge/fastapi_whisper_serving_20260514_202459/result.json)
- [InferEdge Whisper result](../../results/inferedge/whisper_tiny_speech_transcription_20260514_182822/result.json)
- [LLM env candidate result](../../results/llm/llm_env_candidates_20260515_010032.json)
- [LLM text-generation smoke result](../../results/llm/llm_tiny-gpt2_text_generation_20260515_005755.json)
- [InferEdge LLM result](../../results/inferedge/llm_tiny-gpt2_text_generation_20260515_005755/result.json)
