# LLM Text Generation Smoke Report

> Tiny local text-generation path를 Jetson에서 격리 검증하기 위한 smoke report입니다.
> 이 결과는 model quality나 deployment readiness를 주장하지 않습니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-15T00:58:00+09:00 |
| Hostname | `jetson-orin-nano` |
| Conda env | `llm_env` |
| Transformers available | True |
| Torch CUDA available | True |
| Model | `sshleifer/tiny-gpt2` |
| Device | `cuda` |
| Download allowed | True |
| Offline only | False |
| Status | `succeeded` |
| Failure reason | `none` |

## Runtime

| Metric | Value |
|---|---:|
| Warmup | 0 |
| Repeat | 1 |
| Max new tokens | 16 |
| Mean ms | 660.2308 |
| P95 ms | 660.2308 |

## Prompt

```text
Jetson edge AI
```

## Generated Text Preview

```text
Jetson edge AI factors factors factors factors factors factors factors factors factors factors factors factors factors factors factors factors
```

## Interpretation

- This is path evidence for an isolated local LLM smoke, not a benchmark claiming deployment readiness.
- `dependency_missing` or `model_missing` is an expected safe state before the isolated `llm_env` is created or model cache policy is approved.
- Compare latency only with matching model, device, precision, warmup/repeat, and download/cache state.
