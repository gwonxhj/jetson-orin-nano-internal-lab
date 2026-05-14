# FastAPI Whisper Speech Server Smoke Report

> Whisper tiny CUDA transcription path를 localhost FastAPI serving layer로 감싼 smoke evidence입니다.
> License-clear generated speech input을 사용하므로 broad accuracy evidence나 deployment-ready evidence가 아닙니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-14T20:25:10+09:00 |
| Hostname | `jetson-orin-nano` |
| Base URL | `http://127.0.0.1:18081` |
| Endpoint | `/v1/infer/whisper/speech` |
| Server log | `artifacts/system/fastapi_whisper_server_20260514_202459.log` |
| Tegrastats log | `artifacts/system/tegrastats_fastapi_whisper_20260514_202459.log` |

## Model / Audio

| Field | Value |
|---|---|
| Model | whisper-tiny |
| Backend | cuda |
| Precision | fp32_or_fp16_by_device |
| Audio path | `examples/audio/license_clear_whisper_smoke.wav` |
| Audio SHA256 | `5eb101e247c9ab4f6743c48256e1e783ab57be418d12647bae315cb953d577dc` |
| Expected text | `hello world` |
| Transcript | `Hello world!` |
| Expected matched | True |

## Latency

| Metric | Mean ms | P95 ms | P99 ms |
|---|---:|---:|---:|
| Client roundtrip | 3276.5571 | 3276.5571 | 3276.5571 |
| Server transcription | 1802.9543 | 1802.9543 | 1802.9543 |

## Interpretation

- Client roundtrip includes localhost HTTP serialization, FastAPI routing, audio path validation, transcription, and response serialization.
- Server transcription is measured inside the FastAPI handler around `model.transcribe`.
- This is localhost serving-layer evidence, not production deployment approval.
