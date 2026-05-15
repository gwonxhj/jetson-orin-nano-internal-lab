# Models

이 디렉토리는 모델 파일 자체보다 모델 획득, hash, 변환 절차, license, 입력 shape, precision 기록을 우선 보존합니다.

대용량 모델 파일은 기본적으로 Git에 직접 커밋하지 않습니다. 필요한 경우 다운로드 명령, source URL, checksum, 변환 명령을 문서화하고 artifact 저장 위치를 명시합니다.

## Tracked Small Smoke Models

| Model | Source | SHA256 | Purpose | Boundary |
|---|---|---|---|---|
| `yolov8n.pt` | Ultralytics assets download used by `YOLO_ALLOW_DOWNLOAD=1 bash scripts/run_yolo_detection_smoke.sh` | `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36` | Optional file-image object detection smoke | Pretrained smoke model for pipeline evidence, not broad accuracy or deployment-readiness evidence |
