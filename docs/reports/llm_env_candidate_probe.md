# LLM Env Candidate Probe

> 기존 `yolo_env`를 변경하지 않고 tiny text-generation smoke로 넘어가기 위한 격리 env 후보 검증입니다.

## Environment

| Field | Value |
|---|---|
| Date | 2026-05-15T00:39:13+09:00 |
| Hostname | `jetson-orin-nano` |
| Current conda env | `yolo_env` |
| Target env | `llm_env` exists: False |
| Python tag | `cp310` |
| Machine | `aarch64` |
| Torch CUDA available | True |
| Current transformers installed | False |
| Result JSON | `results/llm/llm_env_candidates_20260515_003908.json` |

## Candidate Summary

| Backend | Model candidate | Install spec | Runtime engine | Verdict |
|---|---|---|---|---|
| transformers | `sshleifer/tiny-gpt2` | `transformers accelerate safetensors sentencepiece` | PyTorch | `recommended_first_isolated_candidate` |
| transformers | `distilgpt2` | `transformers accelerate safetensors sentencepiece` | PyTorch | `followup_after_tiny_smoke` |
| llama-cpp-python | `small GGUF model candidate to be selected later` | `llama-cpp-python` | llama.cpp | `followup_requires_native_build_review` |

## Recommended Flow

1. Keep `yolo_env` unchanged.
2. Run `bash scripts/create_llm_env.sh` first and review the plan.
3. Create the isolated env only with `bash scripts/create_llm_env.sh --execute`.
4. Use `conda run -n llm_env bash scripts/run_llm_smoke.sh tiny-gpt2` after reviewing model download/cache policy.
5. Treat `sshleifer/tiny-gpt2` as path smoke only; do not claim model quality or deployment readiness.

## Notes

- This probe does not install packages, create envs, or download model weights.
- The first candidate is intentionally tiny to validate local text-generation plumbing before trying larger models.
- `llama-cpp-python` is a follow-up runtime candidate because native build/CUDA support must be proven separately.
