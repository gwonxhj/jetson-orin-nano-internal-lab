# LLM InferEdge Export Report

> Local LLM text-generation smoke evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.

## Exported Files

| File | Purpose |
|---|---|
| `results/inferedge/llm_tiny-gpt2_text_generation_20260515_005755/metadata.json` | Forge/Lab handoff metadata envelope |
| `results/inferedge/llm_tiny-gpt2_text_generation_20260515_005755/result.json` | Lab-compatible text-generation result envelope |

## Compatibility

| Field | Value |
|---|---|
| metadata schema | `0.1.0` |
| result schema | `inferedge-runtime-result-v1` |
| runtime role | `text-generation-result` |
| compare key | `sshleifer_tiny-gpt2__text_generation__cuda__fp32_cuda_framework_default` |
| backend key | `transformers_cuda__jetson` |
| handoff ready | True |
| text generation ready | True |
| verdict | `text_generation_smoke_not_quality_benchmark` |

## Runtime Summary

| Field | Value |
|---|---|
| Model | `sshleifer/tiny-gpt2` |
| Engine | `transformers` |
| Device | `cuda` |
| Precision | `fp32_cuda_framework_default` |
| Mean ms | 660.2308 |
| P95 ms | 660.2308 |
| Generated tokens/s | 24.2339 |

## Text Generation

| Field | Value |
|---|---|
| Prompt token count | 5 |
| Generated token count | 16 |
| Max new tokens | 16 |
| Download allowed | True |

Prompt:

```text
Jetson edge AI
```

Generated text preview:

```text
Jetson edge AI factors factors factors factors factors factors factors factors factors factors factors factors factors factors factors factors
```

## Notes

- This is tiny text-generation path evidence, not a text quality benchmark.
- `compare_ready` means the handoff envelope is complete; it does not imply a deployment approval.
- The stable `yolo_env` remains separate from the isolated `llm_env` used for this smoke.
