# PyTorch Image Inference Smoke Report

> 첫 모델 추론 smoke evidence입니다.
> 이 실행은 pretrained accuracy 검증이 아니라 PyTorch CUDA inference path와 latency 기록을 위한 synthetic-input smoke입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-13T12:38:03+09:00 |
| Hostname | `nano01` |
| Conda env | `yolo_env` |
| Result JSON | `results/inference/pytorch_resnet18_20260513_123756.json` |
| Tegrastats log | `/home/risenano01/jetson-orin-nano-internal-lab/artifacts/system/tegrastats_inference_resnet18_20260513_123756.log` |
| Power mode | NV Power Mode: 25W; 1 |
| Git commit | 977bcc1 |

## Model / Runtime

| Field | Value |
|---|---|
| Framework | pytorch |
| Backend | cuda |
| Precision | fp32 |
| Architecture | resnet18 |
| Weights | random_seeded_weights_no_pretrained_accuracy_claim |
| Parameter count | 11689512 |
| Model hash | `fb5581c023afb259497b342b2bec2c5a0066377101a7d38fe697fd019f0063d4` |
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
| Mean | 11.6585 |
| P50 | 11.5909 |
| P95 | 15.8536 |
| P99 | 16.1578 |
| Min | 9.7131 |
| Max | 16.158 |

## Notes

- Random seeded weights mean this result must not be interpreted as ImageNet accuracy evidence.
- The input is a deterministic synthetic tensor, so preprocessing cost is not included.
- Backend, precision, input shape, warmup, repeat, model hash, and power mode are recorded for future TensorRT comparison.
- This smoke result can be used as the PyTorch CUDA baseline before ONNX export and TensorRT engine build.
