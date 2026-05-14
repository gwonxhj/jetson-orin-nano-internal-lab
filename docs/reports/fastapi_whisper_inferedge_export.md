# FastAPI Whisper InferEdge Serving Export Report

> FastAPI Whisper localhost speech serving smoke evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.

## Exported Files

| File | Purpose |
|---|---|
| `results/inferedge/fastapi_whisper_serving_20260514_202459/metadata.json` | Forge/Lab handoff metadata envelope |
| `results/inferedge/fastapi_whisper_serving_20260514_202459/result.json` | Lab-compatible audio serving result envelope |

## Compatibility

| Field | Value |
|---|---|
| metadata schema | `0.1.0` |
| result schema | `inferedge-runtime-result-v1` |
| runtime role | `serving-result` |
| compare key | `whisper-tiny__fastapi_speech__16000hz__cuda` |
| backend key | `fastapi_openai_whisper_cuda__jetson` |
| handoff ready | True |
| serving ready | True |
| transcription ready | True |
| verdict | `serving_layer_evidence_not_direct_regression` |

## Endpoint

| Field | Value |
|---|---|
| Framework | `fastapi` |
| ASGI | `uvicorn` |
| Endpoint | `/v1/infer/whisper/speech` |
| Backend | `fastapi+openai-whisper` |
| Precision | `fp32_or_fp16_by_device` |

## Audio / Transcription

| Field | Value |
|---|---|
| Audio path | `examples/audio/license_clear_whisper_smoke.wav` |
| Audio SHA256 | `5eb101e247c9ab4f6743c48256e1e783ab57be418d12647bae315cb953d577dc` |
| Duration s | 1.235 |
| Expected text | `hello world` |
| Transcript | `Hello world!` |
| Expected matched | True |

## Latency

| Layer | Mean ms | P95 ms | P99 ms |
|---|---:|---:|---:|
| Client roundtrip | 3276.5571 | 3276.5571 | 3276.5571 |
| Server transcription | 1802.9543 | 1802.9543 | 1802.9543 |

## Notes

- This is localhost audio serving-layer evidence, not a deployment approval.
- Client roundtrip latency includes local HTTP serialization, FastAPI routing, audio path validation, transcription, and response serialization.
- The exported `result.json` preserves InferEdge-compatible serving top-level fields while keeping audio and transcription details under `audio`, `transcription`, and `serving`.
- The generated speech sample validates plumbing for one license-clear phrase; it is not a broad speech recognition accuracy benchmark.
