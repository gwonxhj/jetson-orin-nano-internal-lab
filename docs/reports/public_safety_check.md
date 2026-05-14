# Public Safety Check

> Public portfolio sharing safety check for Jetson Orin Nano Internal Lab as of 2026-05-15 KST.

## Summary

| Field | Result |
|---|---|
| Repository | `gwonxhj/jetson-orin-nano-internal-lab` |
| Source snapshot checked | `5ca1115` |
| GitHub visibility observed | `public` |
| Default branch | `main` |
| Blocking public-safety issue | none found |
| Visibility change performed | none |

The repository is already public at the time of this check. `5ca1115` is the source snapshot scanned before this report was committed, and the report itself is tracked by the commit that contains this file.

## GitHub Repo Card

| Field | Value |
|---|---|
| Description | Jetson Orin Nano internal edge AI evidence lab: environment baselines, PyTorch/ONNX Runtime/TensorRT comparison, FastAPI serving, Whisper audio, and InferEdge exports. |
| Topics | `ai-inference`, `benchmark`, `cuda`, `edge-ai`, `embedded-ai`, `evidence`, `fastapi`, `inferedge`, `jetson`, `jetson-orin-nano`, `onnx`, `onnxruntime`, `pytorch`, `runtime-comparison`, `tensorrt`, `trtexec`, `whisper` |
| README state | Representative evidence, evidence index, final review, release notes, and schema validation are linked. |
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
| Raw logs | pass | Raw logs are environment, TensorRT, server, and `tegrastats` evidence; no sensitive local path, IP, token, or key markers found. |
| Large tracked files | accepted | ONNX and TensorRT engine/cache artifacts are intentional reproducibility evidence, not secrets. |
| InferEdge handoff schema | pass | `bash scripts/validate_inferedge_artifacts.sh` validates 5 handoff directories with strict artifact hash checks. |

## Large Artifact Review

| Artifact | Approx Size | Decision |
|---|---:|---|
| `models/resnet18_random_seed42_opset17.onnx` | 45 MB | keep: canonical ONNX model evidence |
| `artifacts/engines/resnet18_fp16_20260513_125323.engine` | 23 MB | keep: native TensorRT FP16 engine evidence |
| `artifacts/tensorrt/ort_trt_engine_cache/resnet18_fp32/...engine` | 45 MB | keep: ORT TensorRT EP cache evidence |

These files make the repository heavier, but they support the portfolio claim that runtime artifacts and handoff evidence are reproducible. They are acceptable for the current public snapshot.

## Decision

No cleanup is required before continuing to share the repo publicly. The repo is already public, the GitHub repo card is populated, the schema validation workflow is green, and the tracked evidence does not expose obvious secrets, local absolute paths, private host/IP markers, or unnecessary raw machine context.

## Follow-Up

- Re-run this check whenever new raw logs, model artifacts, or InferEdge handoff directories are added.
- Keep `scripts/validate_inferedge_artifacts.sh` green before sharing future snapshots.
- If artifact size becomes a portfolio UX problem, move heavyweight model/engine files to release assets while keeping hashes and commands in the repo.
