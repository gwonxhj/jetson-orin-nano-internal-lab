# Whisper Transcription Smoke Report

> Whisper tiny/base offline transcription path를 Jetson에서 evidence로 남기기 위한 smoke report입니다.
> Synthetic tone input은 audio decode/model path evidence이고, license-clear generated speech는 transcription path evidence입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-14T18:28:29+09:00 |
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
| Path | `examples/audio/license_clear_whisper_smoke.wav` |
| SHA256 | `5eb101e247c9ab4f6743c48256e1e783ab57be418d12647bae315cb953d577dc` |
| Duration s | 1.235 |
| Sample rate Hz | 16000 |
| Source | `generated_license_clear_ffmpeg_flite_text_to_speech` |
| Expected text | `hello world` |

## Runtime

| Metric | Value |
|---|---:|
| Warmup | 0 |
| Repeat | 1 |
| Mean ms | 1701.2686 |
| P95 ms | 1701.2686 |
| Real-time factor | 1.3775 |

## Transcript Preview

```text
Hello world!
```

## Interpretation

- This runner does not install packages or download model weights by default.
- `dependency_missing` and `model_missing` are valid evidence states, not test failures.
- Synthetic tone input does not prove speech recognition quality.
- License-clear generated speech input is a transcription-path smoke, not a broad accuracy benchmark.
- A future speech sample should be committed only if it is safe to publish and license-clear.
