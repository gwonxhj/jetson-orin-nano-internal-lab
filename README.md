# Jetson Orin Nano Internal Lab

Jetson Orin Nano를 외부 카메라, 센서, 로봇 부품 없이 순수 내부 edge AI 실험 장비로 사용해 환경 점검, TensorRT 최적화, LLM/Whisper 실험, 로컬 inference server, InferEdge-compatible evidence를 재현 가능한 형태로 정리하는 프로젝트입니다.

## Day 1 목표

Day 1은 Jetson 환경 점검과 기준선 기록입니다.

- JetPack / L4T
- CUDA / cuDNN / TensorRT
- Python / pip / venv
- PyTorch CUDA 사용 가능 여부
- ONNX Runtime 설치 여부
- power mode
- `tegrastats`
- memory / disk / swap
- Docker / Git / SSH

## 빠른 시작

Jetson Orin Nano에서 다음 명령으로 환경 정보를 수집합니다.

```bash
bash scripts/collect_env.sh
```

생성되는 주요 산출물:

- `artifacts/system/jetson_env_raw.log`
- `docs/environment/jetson_system_snapshot.md`
- `docs/reports/day1_environment_check.md`

## 원칙

- benchmark 숫자만으로 deployment-ready를 주장하지 않습니다.
- power mode, backend, precision이 다르면 direct regression이 아니라 system/runtime comparison으로 해석합니다.
- TensorRT engine build command, model hash, input shape, precision, warmup/repeat 조건을 반드시 기록합니다.
- InferEdge 호환 `metadata.json`, `result.json`, compare output format을 깨지 않습니다.
