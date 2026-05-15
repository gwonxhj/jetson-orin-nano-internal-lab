# Public Safety Check

> Public portfolio sharing safety check for Jetson Orin Nano Internal Lab as of 2026-05-16 KST.

## Summary

| Field | Result |
|---|---|
| Repository | `gwonxhj/jetson-orin-nano-internal-lab` |
| Source snapshot checked | v0.4 detection handoff evidence commit |
| Latest release observed | [`v0.4-detection-handoff`](https://github.com/gwonxhj/jetson-orin-nano-internal-lab/releases/tag/v0.4-detection-handoff) |
| Latest release target | `bc09365` |
| GitHub visibility observed | `public` |
| Default branch | `main` |
| Blocking public-safety issue | none found |
| Visibility change performed | none |

The repository is already public at the time of this check. This pass covers the post-v0.2 `/metrics` follow-up evidence, the `v0.3-observability-smoke` release, and the v0.4 YOLOv8n file-image detection smoke plus InferEdge handoff artifacts.

## GitHub Repo Card

| Field | Value |
|---|---|
| Description | Jetson Orin Nano internal edge AI evidence lab: environment baselines, PyTorch/ONNX Runtime/TensorRT comparison, YOLO detection, FastAPI serving, Whisper audio, and InferEdge exports. |
| Topics | `ai-inference`, `benchmark`, `cuda`, `edge-ai`, `embedded-ai`, `evidence`, `fastapi`, `inferedge`, `jetson`, `jetson-orin-nano`, `onnx`, `onnxruntime`, `pytorch`, `runtime-comparison`, `tensorrt`, `trtexec`, `whisper` |
| README state | Representative evidence, evidence index, final review, release notes, baseline snapshot, latest serving milestone, and schema validation are linked. |
| Actions state | `InferEdge Schema Validation` workflow passed on `main`. |

## Scan Coverage

The safety pass scanned tracked repository content for:

- local absolute paths, home-directory paths, and temporary macOS paths;
- private host markers, device account names, and private LAN address patterns;
- email-like strings and SSH public/private key markers;
- GitHub token prefix patterns;
- raw `artifacts/` and `results/` files that may expose unnecessary machine context;
- large tracked artifacts that could surprise a public repo visitor.

## Findings

| Area | Result | Notes |
|---|---|---|
| Local absolute paths | pass | No tracked local home-directory or private temp paths found. |
| Private host/IP | pass | No private device DNS name, device account name, or private LAN address marker found. A TensorRT package version can look like an address pattern, but it is version text, not a private IP. |
| Email / key / token markers | pass | No email, SSH key, or GitHub token marker found. |
| Password wording | pass with context | Hits are documentation explaining that non-interactive `sudo nvpmodel -q` needs a sudo password; no password value is present. |
| Hostname fields | pass | Evidence uses generic `jetson-orin-nano` hostname values. |
| Raw logs | pass | Raw logs are environment, TensorRT, server, and `tegrastats` evidence; no sensitive local path, IP, token, or key markers found. The FastAPI soak/burst logs, the post-v0.2 `/metrics` FastAPI server/`tegrastats` logs, and the YOLOv8n detection `tegrastats` log were included in this pass. |
| Large tracked files | accepted | ONNX, YOLOv8n, and TensorRT engine/cache artifacts are intentional reproducibility evidence, not secrets. |
| InferEdge handoff schema | pass | `bash scripts/validate_inferedge_artifacts.sh` validates 8 handoff directories with strict artifact hash checks, including YOLO object detection. |

## Large Artifact Review

| Artifact | Approx Size | Decision |
|---|---:|---|
| `models/resnet18_random_seed42_opset17.onnx` | 45 MB | keep: canonical ONNX model evidence |
| `artifacts/engines/resnet18_fp16_20260513_125323.engine` | 23 MB | keep: native TensorRT FP16 engine evidence |
| `artifacts/tensorrt/ort_trt_engine_cache/resnet18_fp32/...engine` | 45 MB | keep: ORT TensorRT EP cache evidence |
| `artifacts/system/fastapi_soak_burst_server_20260515_222841.log` | 228 KB | keep: v0.2 localhost serving soak/burst server evidence |
| `artifacts/system/tegrastats_fastapi_soak_burst_20260515_222841.log` | 20 KB | keep: v0.2 serving soak/burst telemetry evidence |
| `artifacts/system/fastapi_resnet18_server_20260516_001440.log` | 4 KB | keep: post-v0.2 `/metrics` serving smoke server evidence |
| `artifacts/system/tegrastats_fastapi_resnet18_20260516_001440.log` | 10 KB | keep: post-v0.2 `/metrics` serving telemetry evidence |
| `models/yolov8n.pt` | 6.3 MB | keep: optional YOLO detection smoke model with recorded SHA256 |
| `artifacts/system/tegrastats_yolo_yolov8n_20260516_010734.log` | 2.3 KB | keep: YOLO detection smoke telemetry evidence |

These files make the repository heavier, but they support the portfolio claim that runtime artifacts and handoff evidence are reproducible. They are acceptable for the current public snapshot.

## Decision

No cleanup is required before continuing to share the repo publicly. The repo is already public, the GitHub repo card is populated, the latest `v0.4` detection handoff milestone is linked from README, the post-v0.2 `/metrics` evidence, post-v0.3 YOLO smoke artifacts, and YOLO InferEdge handoff have been scanned, schema validation is green, and the tracked evidence does not expose obvious secrets, local absolute paths, private host/IP markers, or unnecessary raw machine context.

## Follow-Up

- Re-run this check whenever new raw logs, model artifacts, or InferEdge handoff directories are added.
- Keep `scripts/validate_inferedge_artifacts.sh` green before sharing future snapshots.
- If artifact size becomes a portfolio UX problem, move heavyweight model/engine files to release assets while keeping hashes and commands in the repo.
