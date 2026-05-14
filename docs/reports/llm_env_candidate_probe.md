# LLM Env Candidate Probe

> 기존 `yolo_env`를 변경하지 않고 tiny text-generation smoke로 넘어가기 위한 격리 env 후보 검증입니다.

## Environment

| Field | Value |
|---|---|
| Date | 2026-05-15T01:00:37+09:00 |
| Hostname | `jetson-orin-nano` |
| Current conda env | `yolo_env` |
| Target env | `llm_env` exists: True |
| Python tag | `cp310` |
| Machine | `aarch64` |
| Torch CUDA available | True |
| Current transformers installed | False |
| Result JSON | `results/llm/llm_env_candidates_20260515_010032.json` |

## Candidate Summary

| Backend | Model candidate | Install spec | Runtime engine | Verdict |
|---|---|---|---|---|
| transformers | `sshleifer/tiny-gpt2` | `transformers accelerate safetensors sentencepiece` | PyTorch | `isolated_env_exists_validate_or_reuse` |
| transformers | `distilgpt2` | `transformers accelerate safetensors sentencepiece` | PyTorch | `followup_after_tiny_smoke` |
| llama-cpp-python | `small GGUF model candidate to be selected later` | `llama-cpp-python` | llama.cpp | `followup_requires_native_build_review` |

## Recommended Flow

1. Keep `yolo_env` unchanged.
2. Reuse existing `llm_env` for tiny text-generation smoke validation.
3. Run `LLM_ALLOW_DOWNLOAD=1 conda run -n llm_env bash scripts/run_llm_smoke.sh tiny-gpt2` when model download/cache is allowed.
4. Treat `sshleifer/tiny-gpt2` as path smoke only; do not claim model quality or deployment readiness.

## Notes

- This probe does not install packages, create envs, or download model weights.
- The first candidate is intentionally tiny to validate local text-generation plumbing before trying larger models.
- `llama-cpp-python` is a follow-up runtime candidate because native build/CUDA support must be proven separately.
