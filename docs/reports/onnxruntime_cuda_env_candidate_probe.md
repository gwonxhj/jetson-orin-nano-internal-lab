# ONNX Runtime CUDA Env Candidate Probe

> 기존 `yolo_env`를 변경하지 않고 JetPack 6 / CUDA 12.6 / cuDNN 9 조합에서 사용할 수 있는 ONNX Runtime GPU wheel 후보를 검증한 evidence입니다.

## Environment

| Field | Value |
|---|---|
| Date | 2026-05-14T02:08:24+09:00 |
| Hostname | `jetson-orin-nano` |
| Conda env | `yolo_env` |
| Python tag | `cp310` |
| Machine | `aarch64` |
| CUDA | `12.6.11` |
| cuDNN | `9.3.0` |
| Result JSON | `results/inference/ort_cuda_wheel_candidates_20260514_020616.json` |

## Candidate Summary

| Candidate | Version | Trust level | Verdict | URL reachable |
|---|---:|---|---|---|
| jetson_ai_lab_index_jp6_cu126 | 1.23.0 | nvidia_forum_recommended_index | compatible_candidate | True |
| jetson_ai_lab_direct_wheel_1_20_2 | 1.20.2 | nvidia_forum_confirmed_direct_wheel | compatible_candidate | False |
| ultralytics_assets_direct_wheel_1_23_0 | 1.23.0 | third_party_documented_mirror | compatible_candidate | True |
| ultralytics_assets_direct_wheel_1_20_0 | 1.20.0 | third_party_documented_mirror | compatible_candidate | True |

## Recommended Flow

1. Keep `yolo_env` unchanged.
2. Use `scripts/create_ort_cuda_env.sh --execute` only when ready to create an isolated env.
3. Prefer the Jetson AI Lab `jp6/cu126` index or NVIDIA-forum-confirmed direct wheel before third-party mirrors.
4. After install, run `benchmarks/inference/onnxruntime_cuda_ep_attempt.py` from the isolated env and record provider availability again.

## Notes

- Candidate compatibility means the wheel tags and detected Jetson runtime family match; it is not a deployment-ready claim.
- Network reachability is recorded separately because package hosts can be temporarily unavailable.
- If CUDAExecutionProvider appears, add ONNX Runtime CUDA as a new runtime row instead of replacing existing CPU evidence.
