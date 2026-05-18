# Schema Drift Protection Review

> V1 release 전에 InferEdge-compatible `metadata.json` / `result.json` handoff가 무엇을 자동으로 보호하고, 무엇을 보호하지 않는지 정리한 최종 점검 문서입니다.
> 이 문서는 schema drift guardrail이며 Jetson benchmark 재실행, production validation, deployment-ready proof가 아닙니다.

## Current Status

| Field | Value |
|---|---:|
| Validation command | `bash scripts/validate_inferedge_artifacts.sh` |
| GitHub Actions workflow | `.github/workflows/inferedge-schema.yml` |
| Handoff directories validated | 11 |
| Strict artifact hash check | enabled |
| Current expected status | pass |

The current validation run passes all committed handoff pairs with strict artifact hash checking enabled.

## What It Protects

| Protection | How It Is Checked | Why It Matters |
|---|---|---|
| Handoff pair presence | Every `results/inferedge/*/` directory must contain `metadata.json` and `result.json`. | Prevents half-written handoff artifacts from being published. |
| Metadata schema shape | `validate_inferedge_metadata` checks required keys, schema version, `handoff.ready`, and Lab profile readiness. | Keeps the Lab/Forge handoff envelope stable. |
| Result schema shape | `validate_inferedge_result` checks required result keys and `inferedge-runtime-result-v1`. | Keeps runtime consumers from receiving incomplete result envelopes. |
| Runtime role semantics | Role-specific verdict and readiness flags are checked for runtime, serving, audio, text, object detection, and multi-workload results. | Prevents smoke evidence from silently turning into deployment, quality, or accuracy claims. |
| Artifact hash drift | Metadata artifact paths must exist and sha256 must match committed files. | Detects stale metadata when scripts, result files, or referenced reports change. |
| Handoff path consistency | `lab_compat.runtime.result_json_path` must point to the paired `result.json`. | Prevents a metadata/result pair from pointing at the wrong artifact. |
| Export schema consistency | `extra.export_schema_version` must match the current exporter schema version. | Forces explicit updates when exporter contract changes. |

## Runtime Roles Covered

| Runtime role | Boundary enforced |
|---|---|
| `runtime-result` | Runtime comparison must remain `runtime_comparison_not_direct_regression`. |
| `serving-result` | Serving evidence must remain serving-layer evidence and expose serving details. |
| `audio-transcription-result` | Whisper evidence must remain transcription smoke, not accuracy benchmark. |
| `text-generation-result` | LLM evidence must not claim text quality or deployment readiness. |
| `object-detection-result` | YOLO evidence must remain file-image/internal-only and must not claim broad accuracy. |
| `multi-workload-runtime-result` | Multi-workload evidence must remain runtime interaction/reliability evidence, not production stress coverage. |

## What It Does Not Protect

- It does not rerun Jetson workloads, rebuild TensorRT engines, or regenerate raw logs.
- It does not verify that old latency numbers are still reproducible on a changed Jetson environment.
- It does not prove production serving, uptime, capacity, queue-depth correctness, or real-time behavior.
- It does not validate model accuracy, speech recognition quality, LLM answer quality, or object detection generalization.
- It does not replace public safety review for secrets, local paths, private hosts, or unnecessary raw log exposure.

## V1 Gate

Before a V1 release, run:

```bash
bash scripts/validate_inferedge_artifacts.sh
python3 tests/test_inferedge_artifact_validation.py
git status --short
```

The release should proceed only if validation passes, `git status` contains no unexpected files, and public safety review remains clean.

## Change Policy

- If a new `runtime_role` is added, update `validate_inferedge_result`, add a test fixture, and update this review.
- If a new artifact role is added, ensure `metadata.artifacts` records path and sha256, and strict validation can resolve the file.
- If an exporter changes referenced script/report hashes, regenerate affected handoff metadata before committing.
- If a result intentionally records failure evidence, do not export it as a successful handoff unless a failure-specific schema is introduced.
