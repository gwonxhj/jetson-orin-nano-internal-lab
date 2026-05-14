# Evidence Release Notes

> Public portfolio snapshot for Jetson Orin Nano Internal Lab evidence as of 2026-05-15 KST.

## Snapshot Identity

| Field | Value |
|---|---|
| Snapshot purpose | Public portfolio evidence package |
| Source evidence commit | `17b9ebc` |
| Release note location | `docs/reports/evidence_release_notes.md` |
| Hardware scope | Jetson Orin Nano internal-only experiments |
| External hardware dependency | None |

`17b9ebc` is the evidence source commit used to define this snapshot. The release note itself is tracked by the repository commit that contains this file, so readers should use `git rev-parse --short HEAD` after checkout to identify the exact packaging commit.

## Included Evidence Package

| Track | Final Report | Primary JSON / Raw Artifact | InferEdge Handoff |
|---|---|---|---|
| Portfolio map | [Portfolio evidence index](portfolio_evidence_index.md), [Portfolio final review](portfolio_final_review.md) | `README.md` | Not applicable |
| Environment baseline | [Day 1 environment check](day1_environment_check.md), [System baseline](system_baseline.md) | `artifacts/system/jetson_env_raw.log`, `results/system/system_baseline_20260513_122758.json` | Not applicable |
| Jetson resource map | [Resource map](../system/jetson_resource_map.md) | `artifacts/system/tegrastats_idle.log`, `artifacts/system/tegrastats_load_smoke.log` | Not applicable |
| CUDA compute | [CUDA compute notes](cuda_compute_notes.md) | `results/cuda/cuda_compute_smoke_20260513_151135.json` | Not applicable |
| ResNet18 PyTorch/ONNX/TensorRT | [ResNet18 runtime matrix summary](resnet18_runtime_matrix_summary.md), [TensorRT FP16 optimization report](tensorrt_optimization_report.md) | `results/runtime_compare/resnet18_pytorch_cuda_fp32_vs_onnxruntime_cpu_fp32_vs_onnxruntime_cuda_fp32_vs_onnxruntime_tensorrt_fp32_vs_tensorrt_fp16_20260514_025504.json` | `results/inferedge/resnet18_runtime_compare_20260513_133100/` |
| FastAPI ResNet18 serving | [FastAPI API usage](fastapi_api_usage.md), [FastAPI concurrency smoke](fastapi_concurrency_smoke.md), [Serving boundary notes](serving_boundary_notes.md) | `results/inference/fastapi_resnet18_server_20260514_142053.json`, `results/inference/fastapi_resnet18_concurrency_20260514_233246.json` | `results/inferedge/resnet18_fastapi_serving_20260514_142053/` |
| Whisper offline transcription | [Whisper speech smoke](whisper_speech_transcription_smoke.md), [Whisper InferEdge export](whisper_inferedge_export.md) | `results/inference/whisper_tiny_speech_transcription_20260514_182822.json` | `results/inferedge/whisper_tiny_speech_transcription_20260514_182822/` |
| FastAPI Whisper serving | [FastAPI Whisper smoke](fastapi_whisper_speech_server_smoke.md), [FastAPI Whisper InferEdge export](fastapi_whisper_inferedge_export.md) | `results/inference/fastapi_whisper_speech_server_20260514_202459.json` | `results/inferedge/fastapi_whisper_serving_20260514_202459/` |
| LLM text generation | [LLM text generation smoke](llm_text_generation_smoke.md), [LLM InferEdge export](llm_inferedge_export.md) | `results/llm/llm_tiny-gpt2_text_generation_20260515_005755.json` | `results/inferedge/llm_tiny-gpt2_text_generation_20260515_005755/` |
| InferEdge schema validation | [InferEdge schema validation](inferedge_schema_validation.md) | `scripts/validate_inferedge_artifacts.py`, `.github/workflows/inferedge-schema.yml` | all committed `results/inferedge/*/` pairs |

## Snapshot Claim Boundary

This snapshot supports the following public claim:

> Jetson Orin Nano can be used as an internal-only edge AI evidence lab where environment, runtime comparison, local serving, audio transcription, text generation, and InferEdge-compatible handoff artifacts are recorded in a reproducible chain.

This snapshot does **not** claim:

- deployment readiness, production uptime, or capacity planning;
- broad speech recognition accuracy from one generated speech sample;
- LLM output quality from `sshleifer/tiny-gpt2`;
- direct regression conclusions across different backend, precision, provider, or power conditions;
- external camera, microphone, sensor, motor, or robot hardware validation.

## Reproduction Entry Points

Use these commands only after setting up the intended Jetson environment described in the reports.

```bash
cd ~/jetson-orin-nano-internal-lab
source ~/miniconda3/etc/profile.d/conda.sh
conda activate yolo_env
bash scripts/collect_env.sh
bash scripts/run_system_baseline.sh
bash scripts/run_inference_smoke.sh resnet18 cuda
bash scripts/run_tensorrt_bench.sh resnet18
bash scripts/run_runtime_compare.sh
```

Isolated optional tracks use separate environments:

```bash
bash scripts/create_whisper_env.sh --execute
conda run -n whisper_env bash scripts/run_whisper_smoke.sh tiny

bash scripts/create_llm_env.sh --execute
LLM_ALLOW_DOWNLOAD=1 conda run -n llm_env bash scripts/run_llm_smoke.sh tiny-gpt2
```

## Public Sharing Checklist

- README first screen points to the evidence index and final review.
- Core reports link back to JSON results, raw logs, or handoff directories.
- InferEdge handoff directories include both `metadata.json` and `result.json`.
- `bash scripts/validate_inferedge_artifacts.sh` passes before sharing a snapshot.
- Smoke reports keep boundary language explicit and avoid deployment-ready claims.
- Local absolute paths and private host details are not required to understand the public narrative.

## Recommended Follow-Up After This Snapshot

1. Add CI-style schema validation for `results/inferedge/**/metadata.json` and `result.json`.
2. Add a longer localhost FastAPI soak or burst test with `tegrastats` telemetry.
3. Try one small non-toy LLM model only after recording license, memory use, cache path, and latency conditions.
