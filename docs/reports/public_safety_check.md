# Public Safety Check

> V1 release 전 공개 포트폴리오 안전 점검 기록입니다. 이 점검은 tracked repository content를 대상으로 secrets, local path, private host/IP, 불필요한 raw log 노출, large artifact exposure를 확인합니다.

## Summary

| Field | Result |
|---|---|
| Repository | `gwonxhj/jetson-orin-nano-internal-lab` |
| Source snapshot checked | V1 pre-release main snapshot |
| Safety scan base commit | `fdb7289` |
| Report commit | The commit containing this file |
| Latest public release observed | [`v0.5-runtime-interaction-evidence`](https://github.com/gwonxhj/jetson-orin-nano-internal-lab/releases/tag/v0.5-runtime-interaction-evidence) |
| Latest release target | `85ad4e7` |
| GitHub visibility observed | `public` |
| Default branch | `main` |
| Blocking public-safety issue | none found |
| Visibility change performed | none |

The repository is already public. This V1 refresh covers the runtime interaction evidence added after v0.5: 30-minute sustained multi-workload run, timeline export, burst-window report, bounded degradation signal, queue/serving observability, InferEdge consumer mapping, and schema drift protection review.

## Scan Coverage

The safety pass scanned tracked repository content for:

- local absolute paths, home-directory paths, and temporary macOS paths;
- private host markers, Jetson device account names, and private LAN address patterns;
- email-like strings and SSH public/private key markers;
- GitHub token prefix patterns and common credential wording;
- raw `artifacts/` and `results/` files that may expose unnecessary machine context;
- large tracked artifacts that could surprise a public repo visitor.

## Findings

| Area | Result | Notes |
|---|---|---|
| Local absolute paths | pass | No tracked local home-directory path, temporary macOS path, device DNS, device account, or private LAN path marker found. |
| Private host/IP | pass with context | Hits are TensorRT package/version strings such as `10.3.0.30-1+cuda12.5`, not private IP addresses. |
| Email / key / token markers | pass with context | No email address, SSH key, private key, GitHub token, or OpenAI-style secret key marker found. The `token` hits are LLM token-count code/documentation, and the `sk-` pattern hits are `disk-mib` CLI arguments, not credentials. |
| Password wording | pass with context | Hits explain that non-interactive `sudo nvpmodel -q` may need a sudo password; no password value is present. |
| Hostname fields | pass | Evidence uses generic `jetson-orin-nano` hostname values. |
| Raw logs | pass | Raw logs are environment, TensorRT, FastAPI server, and `tegrastats` evidence. No secret, private path, private host/IP, token, or key marker was found. |
| Large tracked files | accepted | ONNX, YOLOv8n, TensorRT engine/cache, and multi-workload JSON/log files are intentional reproducibility evidence. They are public-heavy but not secrets. |
| InferEdge handoff schema | pass | `bash scripts/validate_inferedge_artifacts.sh` validates 11 handoff directories with strict artifact hash checks. |

## Large Artifact Review

| Artifact | Approx Size | Decision |
|---|---:|---|
| `models/resnet18_random_seed42_opset17.onnx` | 45 MB | keep: canonical ONNX model evidence |
| `artifacts/tensorrt/ort_trt_engine_cache/resnet18_fp32/...engine` | 45 MB | keep: ORT TensorRT EP cache evidence |
| `artifacts/engines/resnet18_fp16_20260513_125323.engine` | 23 MB | keep: native TensorRT FP16 engine evidence |
| `results/runtime_compare/multi_workload_sustained_20260518_002910.json` | 15 MB | keep: V1 30-minute runtime interaction evidence |
| `results/runtime_compare/multi_workload_degradation_20260518_013625.json` | 6.8 MB | keep: bounded degradation evidence |
| `models/yolov8n.pt` | 6.3 MB | keep: YOLO file-image detection smoke model with recorded SHA256 |
| `results/runtime_compare/multi_workload_sustained_20260517_221116.json` | 5.0 MB | keep: v0.5 10-minute runtime interaction evidence |
| `results/runtime_compare/multi_workload_degradation_20260518_023351.json` | 4.3 MB | keep: V1 queue/serving observability source evidence |
| `artifacts/system/fastapi_multi_workload_server_20260518_002910.log` | 2.6 MB | keep: V1 30-minute FastAPI server log evidence |
| `results/inferedge/multi_workload_sustained_20260518_002910/result.json` | 1.5 MB | keep: InferEdge-compatible 30-minute handoff result |

These files make the repository heavier, but they support the portfolio claim that runtime artifacts and handoff evidence are reproducible. They are acceptable for the V1 public narrative. If size becomes a presentation problem later, move heavyweight artifacts to GitHub Release assets while preserving hashes and commands in the repo.

## Commands Used

The scan used `rg` over tracked content for local-path, private-host, private-LAN, email, SSH key, GitHub token, OpenAI-style key, password/credential wording, and large tracked artifact patterns. Exact private host/account patterns are intentionally not repeated in this public report. The final gate also ran:

```bash
git ls-files -z | xargs -0 du -h | sort -hr | head -30
bash scripts/validate_inferedge_artifacts.sh
```

## Decision

No cleanup is required before preparing the V1 public narrative. The tracked V1 artifact set does not expose obvious secrets, local absolute paths, private host/IP markers, SSH keys, GitHub tokens, or unnecessary raw machine context. Schema validation is green for all 11 InferEdge handoff pairs.

## Follow-Up

- Re-run this check before cutting `v1.0-runtime-evidence-lab`.
- Keep `scripts/validate_inferedge_artifacts.sh` green before sharing future snapshots.
- Re-run this check whenever new raw logs, model artifacts, or InferEdge handoff directories are added.
- If artifact size becomes a portfolio UX problem, move heavyweight model/engine/log files to release assets while keeping hashes and commands in the repo.
