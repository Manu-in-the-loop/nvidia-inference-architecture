# Coding-agent inference on GB300 NVL72 and Vera Rubin NVL72

A private endpoint for developers using Claude Code, OpenCode, Roo Code, or Cline. The models are GLM-5.3 and Kimi K3. NVIDIA Dynamo serves both. One admitted developer has either 200,000 tokens or the full 1,048,576-token window reserved.

The figures below come from `capacity/model.py`. Change any input in [Assumptions you can change](assumptions.md), rerun the script, and replace this table with `capacity/results.md`.

## Recommendation

Buy Vera Rubin NVL72 for Kimi K3. Buy GB300 NVL72 for GLM-5.3.

GLM-5.3 fills GPU memory before it fills decode throughput, on both platforms. The seat count matches. GB300 does it at 140 kW. Rubin does it at 220 kW.

Kimi K3 on GB300 is limited by decode throughput. Rubin has the HBM bandwidth to turn that same 16-GPU replica into a memory-limited service, with several times the seats.

A Vera Rubin purchase unit is 3 racks. A GB300 purchase unit is 1 rack, tested on one Spectrum-X fabric through 8 racks. The table uses 1 rack and 3 racks for both, so the two platforms can be compared on the same count. Three GB300 racks are a planning quantity, not a separate tested fabric size.

## What the two counts mean

**Concurrent developers** are people inside an active agent turn at the same time. The turn includes token generation and tool execution. KV for that turn stays in GPU memory. Each person must be able to receive 50 tokens per second while generating, with a cache-hit first token under 1 second.

**Developers served** are the people who can use that endpoint over a working hour. Measured coding-agent traces spend 35.7% of a cache-relevant hour inside an active turn. The other 64.3% is the developer reading, editing, or away, and that time does not hold a GPU seat.

Developers served = concurrent developers / 0.357.

## Capacity

| Platform | Model | Context | Limit | Concurrent, 1 rack | Served, 1 rack | Concurrent, 3 racks | Served, 3 racks |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| GB300 NVL72 | GLM-5.3 | 200k | Memory | 890 | 2,492 | 2,616 | 7,327 |
| GB300 NVL72 | GLM-5.3 | 1M | Memory | 166 | 464 | 488 | 1,366 |
| GB300 NVL72 | Kimi K3 | 200k | Decode | 601 | 1,683 | 1,766 | 4,946 |
| GB300 NVL72 | Kimi K3 | 1M | Decode | 126 | 352 | 370 | 1,036 |
| Vera Rubin NVL72 | GLM-5.3 | 200k | Memory | 890 | 2,492 | 2,616 | 7,327 |
| Vera Rubin NVL72 | GLM-5.3 | 1M | Memory | 166 | 464 | 488 | 1,366 |
| Vera Rubin NVL72 | Kimi K3 | 200k | Memory | 2,720 | 7,619 | 7,996 | 22,397 |
| Vera Rubin NVL72 | Kimi K3 | 1M | Memory | 580 | 1,624 | 1,705 | 4,775 |

Three-rack counts are one rack times 3 times 0.98. The 0.98 factor is scheduling imbalance. A replica and its KV stay inside one rack.

Five Rubin units (15 racks) at the Kimi K3 200k row serve about 112,000 developers under this hour mix: 5 times 22,397. That illustration uses the same 0.98 factor once per 3-rack unit.

Cache-hit first-token time in the model is under 0.04 seconds on every row. A cold 1M prefill is about 2.0 seconds for GLM-5.3 on GB300 and about 2.6 seconds for Kimi K3 on GB300. On Rubin those cold times are about 0.60 and 0.78 seconds. Cold time uses an assumed prefill efficiency of 0.35, so treat it as a planning figure.

## Assumptions that set these numbers

Full list, file paths, and the effect of each change: [assumptions.md](assumptions.md).

The usage inputs, in `capacity/scenarios.yaml`:

| Input | Value | Source | If you change it |
| --- | ---: | --- | --- |
| Share of an active turn spent generating | 0.410 | TraceLab Table 7: 41.0% generation, 59.8% tools | Decode-bound rows move. Set to 1.0 if every admitted developer generates at once. GB300 Kimi K3 at 200k then drops from 601 to 246 concurrent developers. GLM rows do not drop. |
| Share of a working hour spent in an active turn | 0.357 | TraceLab, human gaps capped at 1 hour: 14.5% generation + 21.2% tools | Developers served move. Concurrent seats do not. |
| Requests in flight per developer | 1.15 | Copilot production traces, median | Every row moves. Set to 2.0 for two full requests per person. |

TraceLab's uncapped mix is 92.3% human waiting. That figure is not used. It counts sessions left open for days. Copilot's median gap between turns is 25.2 minutes. This design treats that gap as an eviction, not as a GPU seat.

Other inputs that move the table:

| Input | Value | Where |
| --- | ---: | --- |
| Reserved context | 200,000 or 1,048,576 tokens | `scenarios.yaml` |
| Decode rate | 50 tokens/s while generating | `scenarios.yaml` |
| Cache-hit first-token target | 1 second | `scenarios.yaml`. Pass or fail only. It does not change seats. |
| Three-rack factor | 0.98 | `scenarios.yaml` |
| HBM kept for runtime, per GPU | 16 GB | `constants.json`. Assumed. |
| GLM replica | 8 GPUs, one replica spare per rack | `constants.json` |
| Kimi replica | 16 GPUs, 115 GB read per rank per step | `constants.json` |
| Rubin replica shape | Same GPU counts as GB300 | Assumed. No Rubin recipe for these models was found. |

Cache times are policy. They live in `scenarios.yaml` under `policy` and do not change the seat count:

- Under 60 seconds inside a turn: KV stays in HBM. Copilot's in-turn KV idle P95 is 37 seconds.
- Up to 15 minutes away: KV is offloaded to Grace memory. Recall fits the 1 second budget in every row of the model.
- Longer than 15 minutes: KV is written to rack NVMe, the GPU seat is freed, and resume is logged as a new admission. Copilot prefix hit rate falls apart after about 10 minutes of idle, so 15 minutes is past that cliff on purpose.

## Request path

Diagrams, each an HTML file with its JSON source beside it:

- [Rack, network, and KV placement](../diagrams/infrastructure.html)
- [Prompt path, hit and miss](../diagrams/request-flow.html)
- [Weight sharding and the prompt path](../diagrams/parallelism.html)

A developer sends a prompt from the IDE. Claude Code uses `POST /v1/messages`. OpenCode, Roo Code, and Cline use `POST /v1/chat/completions` with native tool-call streaming.

The gateway checks the Keycloak token, applies the context reservation and the rate limit, and runs NeMo Guardrails on the request. Guardrails do not sit on the per-token decode loop. The gateway writes the prompt, the allow or deny decision, and the token timings to the prompt log, then forwards a stable session key to Dynamo.

On a cache hit, Dynamo returns the turn to the worker that still holds the prefix. Only the new suffix is prefilled. Tokens and tool-call deltas stream back.

On a cache miss, the reserved context is prefilled on that replica. NIXL places the new KV on the decode worker. The cold first-token times above are this path.

While tools run, for less than 60 seconds, the KV stays in HBM. If the developer pauses, Grace holds the copy and the GPU seat can be reused. If the developer is away past 15 minutes, rack NVMe holds the copy. The next prompt is authenticated, logged, and admitted again.

SPIRE identities cover the gateway, Dynamo, and the log path. GPU pods have no mesh sidecar. NVLink and RoCE stay direct.

## Hardware

An NVL72 rack is 18 compute trays, 72 GPUs, and 36 CPUs, tied by NVLink. GB300 uses ConnectX-8 at 800 Gb/s per GPU and BlueField-3 for north-south traffic. Vera Rubin uses two 800 Gb/s ConnectX-9 ports per GPU and BlueField-4. East-west traffic is Spectrum-X Ethernet with RoCEv2.

Hot KV does not cross that Ethernet fabric. RoCE carries checkpoints, parked KV that has left the rack, and new replicas. Operating power used here is 140 kW for a GB300 rack and 220 kW for a Rubin rack. Rubin product figures are preliminary.

## Weights and parallelism

GLM-5.3 is served by vLLM under Dynamo. A replica is 8 GPUs. Attention is data parallel, so each GPU holds the KV of its own developers. Routed experts are sharded across the eight. Non-expert weights are replicated. Nine replicas fit in a rack. One is spare, so eight serve.

Kimi K3 is served by TensorRT-LLM under Dynamo, the engine in the verified MLPerf Endpoints submission. A replica is 16 GPUs. Attention is context parallel, so the KV is split across the ranks. Experts follow the TEP16 layout. Each rank reads a 115 GB slice on every step. Four replicas use 64 GPUs. Eight GPUs remain.

A prompt stays on one replica for the life of the hot prefix. The router uses the session key to return there.

## What this document does not claim

These seat counts are not an MLPerf result and not a measured 200k or 1M benchmark. The verified GB300 Kimi point near 50 tokens per second was 48 concurrent queries on 48 GPUs. Use it as a calibration anchor. The Vera Rubin MLPerf point is provisional and is not an input.

HBM efficiency, 0.808 on the last run, is fitted so a published TensorRT-LLM step (batch 4, 8,192 tokens, 18.12 ms TPOT on GB300) matches a full 115 GB rank read. That efficiency is then applied to every other case, including Rubin.

No price is estimated.

## Sources

- [TraceLab: Characterizing Coding Agent Workloads for LLM Serving](https://arxiv.org/html/2606.30560v2), Table 7. Generation share of a request, and the 1-hour-capped hour mix.
- [Agentic Coding in the Wild: Characterizing GitHub Copilot at Production Scale](https://arxiv.org/html/2608.00101). In-turn concurrency, idle gaps, and KV lifetime.
- [How Claude Code is used in practice](https://www.anthropic.com/research/claude-code-expertise). About four user turns in a typical session, each setting off a chain of agent actions.
- [NVIDIA DSX inference reference architecture](https://docs.nvidia.com/dsx/ncp/inference-ra/home). Dynamo, NIXL, the KV Block Manager, and the gateway rule.
- Hardware and model sources, with confidence tags, are in [source-register.md](source-register.md).
