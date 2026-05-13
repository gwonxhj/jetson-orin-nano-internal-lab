# PyTorch Image Inference Smoke Report

> 첫 모델 추론 smoke evidence입니다.
> 이 실행은 pretrained accuracy 검증이 아니라 PyTorch CUDA inference path와 latency 기록을 위한 synthetic-input smoke입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-13T12:52:53+09:00 |
| Hostname | `jetson-orin-nano` |
| Conda env | `yolo_env` |
| Result JSON | `results/inference/pytorch_resnet18_20260513_125245.json` |
| Tegrastats log | `artifacts/system/tegrastats_inference_resnet18_20260513_125245.log` |
| Power mode | NV Power Mode: 25W; 1 |
| Git commit | 34d04fc |

## Model / Runtime

| Field | Value |
|---|---|
| Framework | pytorch |
| Backend | cuda |
| Precision | fp32 |
| Architecture | resnet18 |
| Weights | random_seeded_weights_no_pretrained_accuracy_claim |
| Parameter count | 11689512 |
| Canonical model hash | `9300a6d687232af2e17af0afba72d35cfc0e828fb3cd519aa72e1bb873b72245` |
| Torch | 2.8.0 |
| Torchvision | 0.23.0 |
| CUDA device | Orin |

## Input / Output

| Field | Value |
|---|---|
| Input source | synthetic_random_tensor |
| Input shape | [1, 3, 224, 224] |
| Input dtype | float32 |
| Preprocessing included | False |
| Output shape | [1, 1000] |
| Top-5 indices | [275, 562, 630, 439, 366] |
| Top-5 values | [1.42081, 1.402925, 1.386302, 1.350889, 1.256872] |

## Latency

| Metric | Value ms |
|---|---:|
| Warmup | 10 runs |
| Repeat | 50 runs |
| Mean | 11.6289 |
| P50 | 11.4165 |
| P95 | 16.3123 |
| P99 | 16.7595 |
| Min | 9.7152 |
| Max | 17.1059 |

## Notes

- Random seeded weights mean this result must not be interpreted as ImageNet accuracy evidence.
- The input is a deterministic synthetic tensor, so preprocessing cost is not included.
- The model hash is computed from a canonical CPU state_dict so it can be compared with ONNX/TensorRT export evidence.
- Backend, precision, input shape, warmup, repeat, model hash, and power mode are recorded for future TensorRT comparison.
