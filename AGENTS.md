# Jetson Orin Nano Internal Lab 작업 가이드

> Root `AGENTS.md`는 전체 설명서가 아니라 작업 map이다.
> 영역별 세부 규칙이 필요해지면 해당 디렉토리의 하위 `AGENTS.md`로 분리한다.

## 1. WHAT — 이 프로젝트는 무엇을 하는가

Jetson Orin Nano Internal Lab은 외부 카메라, 센서, 로봇 부품 없이 보드 내부에서만 환경 점검, 성능 기준선, TensorRT 최적화, LLM/Whisper 실험, 로컬 inference API, InferEdge-compatible evidence를 축적하는 프로젝트다. 이 프로젝트가 없으면 Jetson 실험의 실행 조건과 결과를 재현 가능한 포트폴리오 evidence로 남길 수 없다.

## 2. CONTENTS — 파일/디렉토리와 기술 스택

- `docs/environment/` — Jetson 환경 스냅샷과 실행 조건 문서
- `docs/system/` — power mode, tegrastats, resource map 등 시스템 이해 문서
- `docs/reports/` — Day별 점검 보고서와 benchmark 해석 문서
- `benchmarks/system/` — CPU, memory, disk, PyTorch smoke benchmark
- `benchmarks/cuda/` — CUDA 동작 확인과 GPU smoke benchmark
- `benchmarks/inference/` — 모델 inference benchmark 스크립트
- `benchmarks/runtime_compare/` — backend/precision/runtime 비교 스크립트
- `src/common/` — 공통 schema, metadata, filesystem helper
- `src/inference/` — 모델 로딩, preprocessing, inference runner
- `src/server/` — FastAPI 기반 local inference server
- `examples/` — 이미지, 오디오, 텍스트 샘플 입력
- `models/` — 모델 다운로드/변환 지침. 대용량 모델 파일은 원칙적으로 Git에 직접 넣지 않는다.
- `artifacts/` — raw log, TensorRT engine, LLM 실행 부산물 등 재현 증거
- `results/` — JSON/CSV/Markdown benchmark 결과와 InferEdge 호환 결과
- `scripts/` — 환경 수집과 benchmark 실행 entrypoint
- `tests/` — schema, parser, script smoke test

기술 스택: Bash, Python, PyTorch, ONNX Runtime, TensorRT, FastAPI, Markdown/JSON/CSV.

## 3. HOW — 일반적인 수정은 어떻게 하는가

1. 구현 전에 관련 설계 문서와 이 root map을 먼저 확인한다.
2. 변경 범위가 특정 영역에 속하면 그 영역의 하위 `AGENTS.md`가 있는지 확인한다.
3. 환경/benchmark 결과를 추가할 때는 실행 명령, 날짜, power mode, backend, precision, input shape, warmup/repeat 조건을 함께 기록한다.
4. 스크립트는 Jetson 전용 명령이 없을 때도 실패 원인을 raw log에 남기고, 불필요하게 시스템 상태를 변경하지 않게 작성한다.
5. `metadata.json`, `result.json`, compare output format에 닿는 변경은 문서와 테스트로 schema compatibility를 명시적으로 검증한다.
6. 완료 전 관련 테스트를 실행하고 `git status`로 예상 밖 변경이 없는지 확인한다.

## 4. HOW NOT — 시스템을 깨뜨리는 비명백한 함정

- benchmark 숫자만으로 `deployment-ready`를 주장하지 않는다. 짧은 smoke 결과는 배포 안정성 증거가 아니다.
- power mode, backend, precision이 다른 결과를 direct regression으로 해석하지 않는다. 이런 차이는 system/runtime comparison으로 기록한다.
- TensorRT engine만 남기고 build command, model hash, input shape, precision을 생략하지 않는다. engine artifact만으로는 재현성이 부족하다.
- 외부 카메라, 센서, 모터, 로봇 부품에 의존하는 실험을 기본 경로에 넣지 않는다. 이 프로젝트의 포트폴리오 메시지는 내부 실험 장비화다.
- `artifacts/`와 `results/`의 원시 evidence를 임의로 덮어쓰지 않는다. 같은 실험을 다시 실행하면 timestamp 또는 run id로 구분한다.
- 테스트 실패 상태에서 commit, push, PR, merge를 진행하지 않는다.

## 5. WHERE — 다른 모듈과의 의존성

- **의존**: JetPack/L4T, CUDA, cuDNN, TensorRT, Python, PyTorch, ONNX Runtime, Docker, Git, SSH, Jetson system tools.
- **피의존**: README, reports, InferEdge evidence, portfolio narrative가 `docs/`, `artifacts/`, `results/`의 산출물을 근거로 사용한다.
- **경계 / 어댑터**: `scripts/`는 Jetson 명령과 repo 산출물의 경계이며, `src/common/`은 향후 InferEdge-compatible schema와 runtime 결과의 경계가 된다.

## 6. WHY — 코드에 안 적힌 배경 지식

- 목표는 "Jetson을 써봤다"가 아니라, 외부 부품 없이도 환경 점검부터 TensorRT/LLM/API/InferEdge evidence까지 재현 가능한 실측 흐름을 만드는 것이다.
- Day 1 환경 점검은 이후 benchmark 해석의 기준선이다. JetPack, TensorRT, power mode, thermal 상태가 없으면 latency 숫자의 의미가 약해진다.
- InferEdge 호환 결과는 장기적으로 다른 edge runtime 결과와 비교될 수 있으므로 schema 안정성이 성능 최적화보다 우선될 때가 있다.

## 7. LEARNED CAUTIONS — 학습된 주의사항

- GitHub clone은 Jetson의 GitHub 인증이 설정되기 전까지 HTTPS/SSH 모두 실패할 수 있다. 이 경우 인증 설정 전에는 SSH 세션에서 안전하게 파일을 생성해 작업을 이어간다.
