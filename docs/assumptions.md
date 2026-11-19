# Assumptions you can change

Every number in the capacity table is recomputed from two files. Change the value, then run:

```bash
python3 capacity/model.py
```

The script rewrites `capacity/results.md`, `capacity/results.csv`, and `capacity/results.json`. The report quotes that output. After a change, update the table in `docs/architecture-report.md` from `capacity/results.md` so the two do not drift.

## Usage pattern

These three values define a concurrent developer and the larger population that shares those seats. They live in `capacity/scenarios.yaml` under `usage`.

| Key | Current | What it means | What moves when you change it |
| --- | ---: | --- | --- |
| `generation_share_of_active_turn` | 0.410 | Share of an active turn spent generating tokens. The rest is tool execution. Source: TraceLab Table 7, 41.0% generation and 59.8% tools. | Concurrent seats on decode-bound rows. Memory-bound rows stay put. Set this to `1.0` to require every admitted developer to be generating at the same time. |
| `active_turn_share_of_hour` | 0.357 | Share of a working hour spent inside an active turn, after human gaps longer than 1 hour are capped. Source: TraceLab, 14.5% generation + 21.2% tools. | Developers served. Concurrent seats do not move. Set this to `1.0` if every developer is in an active turn for the whole hour. |
| `requests_per_developer` | 1.15 | LLM calls in flight for one developer during a turn. Source: Copilot production traces, median concurrency 1.15. | Concurrent developers and developers served, on every row. Set this to `2` for a developer who keeps two full requests in flight. |

Developers served = concurrent developers / `active_turn_share_of_hour`.

The uncapped TraceLab mix, in which human waiting is 92.3% of wall time, is not an input. That figure counts sessions left open for days. Copilot's median gap between turns is 25.2 minutes, which this design treats as an eviction, not as a held GPU seat.

Strict case, all developers generating at once: set `generation_share_of_active_turn` to `1.0` and leave `requests_per_developer` at `1.15`. On GB300 with Kimi K3 at 200k, concurrent developers fall from 601 to 246. GLM rows do not fall, because GPU memory fills before decode does.

## Service level and context

In `capacity/scenarios.yaml`:

| Key | Current | Effect |
| --- | ---: | --- |
| `slo.tokens_per_second_per_developer` | 50 | Decode budget per generating developer. Raised from the MLPerf agentic floor. Lowering it adds decode-bound seats. |
| `slo.cache_hit_ttft_seconds` | 1.0 | Pass or fail mark for a cache-hit first token and for Grace recall. It does not change the seat count. |
| `turn.uncached_suffix_tokens` | 2500 | New tokens prefilled on a cache hit. Changes cache-hit TTFT only. |
| `turn.output_tokens_per_turn` | 400 | Recorded turn size. The seat count does not read it. |
| `turn.stable_prefix_tokens` | 30000 | Recorded prefix size. Admission still reserves the full context below. |
| `scenarios[].context_tokens` | 200000 and 1048576 | KV reserved per concurrent developer. This is the main memory lever. |
| `scaling.three_rack_factor` | 0.98 | Multiplier on `3 x one rack`. Scheduling imbalance only. Replicas stay in one rack. |
| `scaling.eight_rack_factor` | 0.97 | Same rule for an eight-rack comparison kept in `results.json`. The customer table uses three racks. |

## Cache policy

In `capacity/scenarios.yaml` under `policy`. Changing these does not change the seat count. They change when KV leaves GPU memory.

| Key | Current | Behavior |
| --- | ---: | --- |
| `tool_gap_keep_in_hbm_seconds` | 60 | A tool gap inside a turn keeps KV in HBM. Copilot's in-turn KV idle P95 is 37 seconds. |
| `pause_offload_to_grace_minutes` | 15 | A developer who pauses is offloaded to Grace memory. |
| `away_evict_to_nvme_minutes` | 15 | A longer absence is written to rack NVMe. Resume is a logged load, then a normal turn. |

Copilot traces show prefix hit rate staying high below 2 minutes of idle and falling apart after about 10 minutes. Fifteen minutes is the operating choice past that cliff, so a returning developer pays a cold prefill rather than a failed recall.

## Hardware and model knobs

In `capacity/constants.json`:

| Key | Current | Effect |
| --- | ---: | --- |
| `runtime.hbm_overhead_gb_decimal_per_gpu` | 16 | HBM kept for runtime, not for KV. Assumed. |
| `runtime.prefill_efficiency` | 0.35 | Cold and cache-hit TTFT. Assumed. Seat count does not use it. |
| `runtime.host_memory_usable_fraction` | 0.7 | How much Grace memory can hold parked KV. Does not add decode seats. |
| `glm.replica_gpus` | 8 | Data-parallel attention, experts sharded. NVIDIA's GB300 endpoint shape. |
| `glm.spare_replicas_per_rack` | 1 | One 8-GPU replica left unused in the rack. |
| `kimi.replica_gpus` | 16 | Context-parallel attention and expert parallel. TensorRT-LLM TEP16 shape. |
| `kimi.spare_replicas_per_rack` | 0 | Four 16-GPU replicas fill 64 GPUs. Eight GPUs remain. |
| `kimi.weight_gb_decimal_per_rank` | 115 | Read on every decode step. TensorRT-LLM TEP16 measurement. |
| `kimi.calibration.tpot_ms` | 18.12 | Fits HBM efficiency (0.808 on the last run). Do not edit the efficiency by hand. |
| Rubin block | product brief figures | Same replica shape as GB300. No Rubin recipe for these models was found. Changing Rubin bandwidth or HBM changes Rubin rows only. |

## Design choices that are not numeric

Change these in `docs/component-decisions.md`. They do not feed `model.py`.

| Choice | Current decision |
| --- | --- |
| Serving control | NVIDIA Dynamo. llm-d is not deployed. |
| GLM-5.3 engine | vLLM, NVFP4, FP8 KV, 8 GPUs. |
| Kimi K3 engine | TensorRT-LLM, 16 GPUs. vLLM and SGLang recipes exist and can replace the engine without moving the router. |
| Steady-state placement | Aggregated workers and chunked prefill. A separate prefill pool is for a cold 1M admission. |
| KV location | Hot prefix stays in the rack. Cross-rack RoCE is for weights, storage, and new replicas. |
| Identity | Keycloak for developers. SPIRE for CPU services. No sidecar on GPU pods. |
| Guardrails | NeMo Guardrails on the request, not on each output token. |
| Cluster | OpenShift for the control plane and for GB300 GPU nodes. Rubin GPU nodes stay on Mission Control Kubernetes until the GPU Operator lists Rubin. |
| Gateway | Kubernetes Gateway API in front of Dynamo. It does not replace the Dynamo router. |
