# Audio Examples

This directory keeps small, repo-safe audio inputs for local inference smoke tests.

## `license_clear_whisper_smoke.wav`

- Purpose: Whisper real speech transcription path smoke.
- Text: `hello world`
- Generator: `scripts/generate_whisper_speech_sample.sh`
- Source: locally generated with FFmpeg `flite` text-to-speech filter.
- Constraints: This is not a microphone recording and is not a broad speech recognition accuracy benchmark.

