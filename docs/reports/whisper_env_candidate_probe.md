# Whisper Env Candidate Probe

> 기존 `yolo_env`를 변경하지 않고 Whisper transcription 성공 evidence로 넘어가기 위한 격리 env 후보 검증입니다.

## Environment

| Field | Value |
|---|---|
| Date | 2026-05-14T17:54:16+09:00 |
| Hostname | `jetson-orin-nano` |
| Current conda env | `yolo_env` |
| Target env | `whisper_env` exists: False |
| Python tag | `cp310` |
| Machine | `aarch64` |
| ffmpeg available | True |
| Torch CUDA available | True |
| Current whisper packages | `whisper=False`, `faster_whisper=False` |
| Result JSON | `results/inference/whisper_env_candidates_20260514_175410.json` |

## Candidate Summary

| Backend | Install spec | Runtime engine | Verdict |
|---|---|---|---|
| openai-whisper | `openai-whisper` | PyTorch | `recommended_first_isolated_candidate` |
| faster-whisper | `faster-whisper` | CTranslate2 | `secondary_isolated_candidate_requires_cuda_validation` |

## Recommended Flow

1. Keep `yolo_env` unchanged.
2. Run `bash scripts/create_whisper_env.sh` first and review the plan.
3. Create the isolated env only with `bash scripts/create_whisper_env.sh --execute`.
4. Activate or use `conda run -n whisper_env` and rerun `bash scripts/run_whisper_smoke.sh tiny` from the isolated env.
5. Treat `openai-whisper` as the first candidate and `faster-whisper` as a follow-up optimization candidate.

## Notes

- This probe does not install packages, create envs, or download model weights.
- `openai-whisper` is preferred first because it can reuse the cloned Jetson PyTorch CUDA stack.
- `faster-whisper` may be faster, but CTranslate2 CUDA support on Jetson must be proven separately.
- A successful transcription smoke is still audio inference path evidence, not deployment readiness or accuracy benchmarking.
