# Whisper Transcription Smoke Report

> Whisper tiny/base offline transcription path를 Jetson에서 evidence로 남기기 위한 smoke report입니다.
> Synthetic tone input은 accuracy evidence가 아니라 audio decode/model path evidence입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-14T18:06:30+09:00 |
| Hostname | `jetson-orin-nano` |
| Conda env | `whisper_env` |
| Python | `3.10.12` |
| Package | `whisper` available: True |
| Model | `tiny` |
| Model cache present | True |
| Model cache path | `[home]/.cache/whisper/tiny.pt` |
| Download allowed | True |
| Offline only | False |
| Status | `succeeded` |
| Failure reason | `none` |

## Audio Input

| Field | Value |
|---|---|
| Path | `artifacts/audio/whisper_smoke_16khz.wav` |
| SHA256 | `cb9568ee93b04dba4a309580b45a0369e486682e2e57305ac8f302630bb8e2ea` |
| Duration s | 1.0 |
| Sample rate Hz | 16000 |
| Source | `generated_synthetic_tone_no_speech_accuracy_claim` |

## Runtime

| Metric | Value |
|---|---:|
| Warmup | 0 |
| Repeat | 1 |
| Mean ms | 1766.6792 |
| P95 ms | 1766.6792 |
| Real-time factor | 1.7667 |

## Transcript Preview

```text
(empty or not measured)
```

## Interpretation

- This runner does not install packages or download model weights by default.
- `dependency_missing` and `model_missing` are valid evidence states, not test failures.
- Synthetic tone input does not prove speech recognition quality.
- A future speech sample should be committed only if it is safe to publish and license-clear.
