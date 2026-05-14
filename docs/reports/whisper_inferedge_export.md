# Whisper InferEdge Export Report

> Whisper speech transcription smoke evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.

## Exported Files

| File | Purpose |
|---|---|
| `results/inferedge/whisper_tiny_speech_transcription_20260514_182822/metadata.json` | Forge/Lab handoff metadata envelope |
| `results/inferedge/whisper_tiny_speech_transcription_20260514_182822/result.json` | Lab-compatible audio transcription result envelope |

## Compatibility

| Field | Value |
|---|---|
| metadata schema | `0.1.0` |
| result schema | `inferedge-runtime-result-v1` |
| runtime role | `audio-transcription-result` |
| compare key | `whisper-tiny__speech__16000hz__cuda` |
| backend key | `openai_whisper_cuda__jetson` |
| handoff ready | True |
| transcription ready | True |
| verdict | `audio_transcription_smoke_not_accuracy_benchmark` |

## Audio Summary

| Field | Value |
|---|---|
| Audio path | `examples/audio/license_clear_whisper_smoke.wav` |
| Audio source | `generated_license_clear_ffmpeg_flite_text_to_speech` |
| Audio SHA256 | `5eb101e247c9ab4f6743c48256e1e783ab57be418d12647bae315cb953d577dc` |
| Duration s | 1.235 |
| Sample rate Hz | 16000 |

## Transcription Summary

| Field | Value |
|---|---|
| Expected text | `hello world` |
| Transcript | `Hello world!` |
| Expected matched | True |
| Mean ms | 1701.2686 |
| P95 ms | 1701.2686 |
| Real-time factor | 1.3775 |

## Notes

- This is a license-clear generated speech transcription smoke, not a broad accuracy benchmark.
- The exported `result.json` keeps InferEdge-compatible top-level fields while preserving audio details under `audio` and `transcription`.
- `compare_ready` means the handoff envelope is complete; it does not imply a deployment approval.
