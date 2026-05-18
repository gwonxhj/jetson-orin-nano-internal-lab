# InferEdge Schema Validation

> `results/inferedge/**/metadata.json` / `result.json` handoff pair가 schema drift 없이 유지되는지 확인하는 CI-style validation 기록입니다.

## Purpose

InferEdge-compatible evidence가 늘어날수록 개별 export는 성공해도 기존 handoff artifact가 조용히 깨질 수 있습니다. 이 validation은 repository에 커밋된 모든 InferEdge handoff directory를 순회하며 schema, runtime role semantics, artifact hash를 함께 확인합니다.

## Validation Entry Points

```bash
bash scripts/validate_inferedge_artifacts.sh
python3 scripts/validate_inferedge_artifacts.py --json
python3 tests/test_inferedge_artifact_validation.py
```

GitHub Actions workflow:

```text
.github/workflows/inferedge-schema.yml
```

## What It Checks

- each `results/inferedge/*/` directory has both `metadata.json` and `result.json`;
- `metadata.json` satisfies `validate_inferedge_metadata`;
- `result.json` satisfies `validate_inferedge_result`;
- runtime roles remain one of `runtime-result`, `serving-result`, `audio-transcription-result`, `text-generation-result`, `object-detection-result`, or `multi-workload-runtime-result`;
- smoke and runtime interaction evidence keep their boundary verdicts, including non-accuracy, non-quality, non-production-stress, and non-deployment claims;
- metadata contains exactly one `runtime_result` artifact pointing at the paired `result.json`;
- artifact sha256 values are filled and match committed files when strict artifact validation is enabled.

## Current Snapshot

| Field | Value |
|---|---:|
| Handoff directories validated | 11 |
| Strict artifact hash check | enabled |
| Expected status | pass |

Current handoff directories:

- `results/inferedge/resnet18_runtime_compare_20260513_133100/`
- `results/inferedge/resnet18_fastapi_serving_20260514_142053/`
- `results/inferedge/resnet18_fastapi_serving_20260516_001440/`
- `results/inferedge/fastapi_whisper_serving_20260514_202459/`
- `results/inferedge/fastapi_resnet18_soak_burst_20260515_222841/`
- `results/inferedge/whisper_tiny_speech_transcription_20260514_182822/`
- `results/inferedge/llm_tiny-gpt2_text_generation_20260515_005755/`
- `results/inferedge/yolo_yolov8n_detection_20260516_010734/`
- `results/inferedge/multi_workload_sustained_20260517_213947/`
- `results/inferedge/multi_workload_sustained_20260517_221116/`
- `results/inferedge/multi_workload_sustained_20260518_002910/`

## Boundary

This validation protects handoff schema compatibility and committed artifact hash consistency. It does not rerun Jetson benchmarks, rebuild TensorRT engines, retest FastAPI serving, prove queue-depth correctness, or make deployment-readiness claims. See [Schema drift protection review](schema_drift_protection_review.md) for the V1 gate interpretation.
