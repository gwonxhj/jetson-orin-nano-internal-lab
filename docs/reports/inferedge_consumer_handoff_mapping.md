# InferEdge Consumer Handoff Mapping

> Jetson Orin Nano Internal Lab의 multi-workload runtime evidence를 InferEdge Runtime, Orchestrator, AIGuard, Lab이 어떤 필드 기준으로 소비해야 하는지 고정한 mapping 문서입니다.
> 이 문서는 integration contract guide이며 production readiness, capacity planning, autonomous operation proof가 아닙니다.

## Source Artifacts

| Artifact | Role | Primary Consumer |
|---|---|---|
| `results/inferedge/multi_workload_sustained_20260518_002910/metadata.json` | Handoff envelope, artifact hashes, producer/export context | InferEdge Lab, Runtime |
| `results/inferedge/multi_workload_sustained_20260518_002910/result.json` | Multi-workload runtime result envelope | Runtime, Orchestrator, AIGuard, Lab |
| `results/runtime_compare/multi_workload_timeline_20260518_002910.json` | Bucketed event/telemetry timeline | Orchestrator, AIGuard, Lab |
| `results/runtime_compare/multi_workload_burst_windows_20260518_002910.json` | Before/during/after Whisper burst latency and telemetry windows | AIGuard, Lab |
| `results/runtime_compare/multi_workload_degradation_signal_20260518_023351.json` | Bounded degradation signal | AIGuard, Lab |
| `results/runtime_compare/multi_workload_serving_observability_20260518_023351.json` | Request counts, failed counts, backlog proxy | Runtime, Orchestrator, AIGuard |

## Consumer Mapping

| Consumer | Should Read | Purpose | Should Not Infer |
|---|---|---|---|
| InferEdge Runtime | `runtime_role`, `engine_backend`, `backend_key`, `model_metadata.inputs`, `latency_ms`, `workload_interaction.summary_by_workload`, `jetson_evidence.power_mode` | Register a real Jetson runtime result, workload mix, input shape/source, latency envelope, and runtime/backend condition. | Do not treat this as a single-model direct regression or deployment-ready runtime guarantee. |
| InferEdge Orchestrator | `workload_interaction.scenario`, `workload_interaction.workloads`, `workload_interaction.interaction`, timeline buckets, `serving_observability.client_backlog_proxy`, `serving_observability.server_metrics_after` | Use workload mix, concurrency, burst timing, observed backlog proxy, and telemetry windows as scheduling/contention input. | Do not derive a production capacity plan or hard queue-depth limit from localhost evidence. |
| InferEdge AIGuard | `comparison.verdict`, degradation `signals`, burst-window deltas, `serving_observability.failed_request_count`, `dropped_request_count_proxy`, `jetson_evidence.tegrastats_summary` | Detect runtime reliability signals such as latency spikes, resource pressure, failed requests, backlog proxy, and bounded degradation. | Do not classify model quality, object detection accuracy, speech accuracy, or LLM answer quality from these smoke inputs. |
| InferEdge Lab | `metadata.artifacts`, `metadata.handoff`, `extra`, `comparison`, report paths, raw log paths, schema validation output | Present reproducible evidence chain, public portfolio narrative, and handoff readiness while preserving artifact hashes and boundaries. | Do not claim broad benchmark leadership, production serving, autonomous robotics readiness, or external sensor validation. |

## Field-Level Contract

| Field | Meaning | Consumer Notes |
|---|---|---|
| `schema_version` | Result envelope schema, currently `inferedge-runtime-result-v1` | Lab and CI validation should reject unknown incompatible schema changes. |
| `runtime_role` | Evidence role, currently `multi-workload-runtime-result` | Runtime should route this separately from single-model `runtime-result` and `serving-result`. |
| `comparison.verdict` | Interpretation guardrail | AIGuard/Lab should preserve `multi_workload_runtime_interaction_evidence_not_production_stress_test`. |
| `workload_interaction.summary_by_workload` | Event counts, success/error counts, p50/p95/p99/max latency by workload | Orchestrator/AIGuard should compare windows and workload behavior, not direct model regressions. |
| `workload_interaction.interaction` | Whisper burst window and before/during/after latency buckets | Use for contention-window analysis. |
| `workload_interaction.serving_observability` | Server in-flight counters and client outstanding request proxy | Use as queue/backlog proxy only; ASGI production queue depth is not exposed. |
| `jetson_evidence.tegrastats_summary` | Parsed Jetson resource telemetry | Use with power mode and workload mix; do not compare across modes as direct regression. |
| `extra.runtime_reliability_ready` | Marks the result as reliability evidence-ready | Must remain true only when result contains bounded interpretation and telemetry context. |
| `extra.deployment_ready_claim` | Explicit non-goal flag | Must remain false for this project. |
| `extra.production_stress_test_claim` | Explicit non-goal flag | Must remain false for this project. |

## Handoff Flow

1. Jetson scripts generate raw logs, JSON result, Markdown report, and optional timeline/degradation/observability derivatives.
2. Export scripts convert selected results into `metadata.json` / `result.json` pairs under `results/inferedge/`.
3. Schema validation checks all committed handoff pairs and artifact hashes.
4. InferEdge consumers use the mapping above to decide which fields are runtime facts, scheduling hints, degradation signals, or report context.

## Boundary

- This mapping is for constrained Jetson internal workload evidence.
- Queue/backlog values are proxy signals, not production queue telemetry.
- Latency/resource changes are runtime reliability signals, not deployment-ready proof.
- Accuracy, quality, uptime, real-time behavior, and external sensor integration remain out of scope.
