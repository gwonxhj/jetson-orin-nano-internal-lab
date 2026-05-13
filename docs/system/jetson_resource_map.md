# Jetson Resource Map

> Jetson Orin Nano를 외부 카메라, 센서, 로봇 부품 없이 내부 edge AI 실험 장비로 사용할 때 참고할 system resource map입니다.
> 이 문서는 deployment readiness가 아니라 이후 CUDA, ONNX Runtime, TensorRT, LLM, FastAPI 실험의 해석 조건을 고정하기 위한 evidence입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-13T14:23:38+09:00 |
| Device | Jetson Orin Nano |
| Hostname | `jetson-orin-nano` |
| Conda env | `yolo_env` |
| Power mode | NV Power Mode: 25W; 1 |
| Idle tegrastats | `artifacts/system/tegrastats_idle.log` |
| Load smoke tegrastats | `artifacts/system/tegrastats_load_smoke.log` |
| Load command | PyTorch CUDA `1024 x 1024` matmul loop for 18 seconds |

## Compute / Memory / Storage

| Resource | Observed value |
|---|---|
| CPU architecture | `aarch64` |
| CPU model | Cortex-A78AE |
| CPU cores | 6 online cores, `0-5` |
| CPU max MHz | 1728.0000 |
| Memory | 7.4 GiB total, 5.7 GiB available at collection time |
| Swap / zram | 3.7 GiB total, 0 B used at collection time |
| Root storage | `/dev/nvme0n1p1`, 915G size, 834G available, 4% used |

## Tegrastats Summary

| Condition | Samples | GR3D min/max/mean | RAM used mean | GPU temp min/max/mean | CPU temp min/max/mean | VDD_IN min/max/mean |
|---|---:|---|---:|---|---|---|
| Idle | 14 | 0% / 0% / 0.00% | 1697 MB | 40.843C / 41.281C / 41.03C | 40.218C / 40.468C / 40.34C | 4287 / 4361 / 4292.29 mW |
| Load smoke | 18 | 90% / 93% / 91.28% | 2028 MB | 43.062C / 47.5C / 45.78C | 41.062C / 44.937C / 43.33C | 13588 / 15558 / 15369.72 mW |

## Interpretation

- Idle evidence shows the board resting near 0% GR3D with GPU temperature around 41C.
- Load smoke evidence confirms internal GPU activity without external hardware: PyTorch CUDA matrix multiplication drove GR3D to roughly 90-93%.
- The load run is intentionally short. It is useful for confirming telemetry behavior, not for sustained thermal throttling or deployment-readiness claims.
- Power mode must stay attached to all future comparisons. A different power mode should be treated as a new system/runtime comparison condition.
- Temperature and power readings are side evidence for interpreting benchmark runs; they should not be mixed with latency numbers without their runtime/backend/precision context.

## Commands

```bash
bash scripts/run_tegrastats.sh 15 1000

python3 - <<'PY'
import subprocess
import time
import torch

proc = subprocess.Popen(['tegrastats', '--interval', '1000'])
try:
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    a = torch.randn((1024, 1024), device=device)
    b = torch.randn((1024, 1024), device=device)
    if device.type == 'cuda':
        torch.cuda.synchronize()
    end = time.time() + 18
    while time.time() < end:
        c = a @ b
        if device.type == 'cuda':
            torch.cuda.synchronize()
finally:
    proc.terminate()
PY
```

## Learned Cautions

- `timeout` returns exit code 124 when it stops `tegrastats` after the requested duration. `scripts/run_tegrastats.sh` treats that expected stop as success so smoke collection does not look like a failed test.
- `tegrastats` raw lines are preserved in artifacts; this document only summarizes them for quick reading.
