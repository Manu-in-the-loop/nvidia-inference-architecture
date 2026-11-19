# Component decisions

NVIDIA's DSX inference reference architecture already names the serving stack. Dynamo stays the control path for routing, scaling, and KV movement. A Red Hat component is used only where that reference leaves the function to the partner, or where putting a proxy on the GPU path would break RoCE.

## Kept from NVIDIA

| Function | Component | Why |
| --- | --- | --- |
| Serving control | Dynamo frontend, prefill router, planner, KV events | This is the layer DSX assigns to multi-GPU LLM serving. llm-d would be a second orchestrator, so it is not deployed. |
| KV movement and offload | NIXL and the KV Block Manager | GPU-to-GPU and GPU-to-Grace movement stays in this path. A Redis-shaped KV store is not added. |
| GLM-5.3 engine | vLLM under Dynamo, NVFP4 weights, FP8 KV, 8-GPU data parallel plus expert parallel | NVIDIA's own GB300 endpoint documents that shape. The NVFP4 model card names SGLang for accuracy eval. SGLang remains the fallback if vLLM's NVFP4 quality regresses. It is not the serving engine in this design. |
| Kimi K3 engine | TensorRT-LLM under Dynamo | The verified MLPerf Endpoints submission is TensorRT-LLM 1.3 plus Dynamo. The replica is 16 GPUs with context-parallel attention and expert parallel, which is the Dynamo GB300 worker shape, using the published 115 GB TEP16 rank. vLLM and SGLang recipes exist on the same Dynamo page and can replace the engine without moving the router. The seat model does not take credit for DSPARK. |
| Placement | KAI Scheduler and Grove | Gang scheduling and topology stay with the NVIDIA Kubernetes layer DSX names. |
| Node enablement | GPU Operator and Network Operator | They are the supported way to expose GPUs and RoCE. |
| Weights | ModelExpress from object or file storage onto node NVMe, then into HBM | DSX puts model movement here. |
| Guardrails | NeMo Guardrails on the request path, not inside the decode loop | Input policy and sampled output checks. A per-token check would sit on the ITL path the 50 tok/s target is measured against. |
| Serving eval | NVIDIA AIPerf, plus the publisher's accuracy set for NVFP4 versus FP8 | DSX names AIPerf for token-service evidence. |
| Rack operations | NVIDIA Mission Control and AI Enterprise | The GB300 enterprise RA recommends Mission Control for the rack. |

## Red Hat, and only these

| Function | Component | Why NVIDIA does not cover it |
| --- | --- | --- |
| Human and IDE identity | Red Hat build of Keycloak | DSX says identity is a partner choice. The IDEs need a bearer token. Keycloak issues it. Dynamo does not. |
| Workload identity | SPIFFE/SPIRE | SPIRE issues identities for the gateway, the Dynamo frontend, eval jobs, and other CPU services. It stops at that control plane. GPU workers have no mesh sidecar. NIXL and RoCE stay direct. |
| Cluster for the control plane, and for GB300 GPU nodes | OpenShift | GPU Operator 26.7 lists HGX GB300 NVL72 on ARM and lists OpenShift 4.18–4.22 and 5.0, including ComputeDomain for the rack NVLink domain. Dynamo asks for Kubernetes 1.30 or later, which those OpenShift releases provide. That is an integration, not a named "Dynamo on OpenShift" reference. |

Vera Rubin is not on the GPU Operator 26.7 platform list. Red Hat has said it intends to support Rubin on OpenShift when the platform is generally available. Until that list includes Rubin, Rubin GPU nodes run on the DGX OS and Mission Control Kubernetes from the SuperPOD reference. The OpenShift cluster still hosts the gateway, Keycloak, and SPIRE in front of those nodes.

The Network Operator's published matrix lists OpenShift for GB200 NVL72 and for HGX B300 with ConnectX-8. It does not, on the page retrieved for this study, name GB300 NVL72. GB300 NVL72 uses ConnectX-8, so the same operator is the intended RoCE path, and production still needs a confirmation against the build that names this rack.

## Gateway

The gateway is Kubernetes Gateway API with the Inference Extension, which DSX allows in front of Dynamo and forbids as a replacement for the Dynamo router.

On the OpenShift control cluster the implementation is Red Hat Connectivity Link. It is the Gateway API implementation that belongs on that platform, and it is where Keycloak authentication, admission, and rate limits terminate. The GPU data plane does not pass through it a second time.

The gateway exposes both client protocols:

- `POST /v1/messages` for Claude Code
- `POST /v1/chat/completions` for OpenCode, Roo Code, and Cline, with native tool-call deltas

It translates both to Dynamo's OpenAI-compatible frontend and forwards a stable session key so the next tool turn can land on the worker that still holds the prefix.

## Serving shape for this traffic

A tool turn is a few thousand new tokens on a prefix that is already resident. The capacity model puts suffix prefill in the tens of milliseconds and suffix NVLink transfer under a tenth of a millisecond. A separate prefill pool does not improve that turn.

The design is aggregated Dynamo workers, KV-aware routing, and chunked prefill. Disaggregated prefill and decode remains a validated Kimi option (matched 16-GPU groups) for a cold 1M admission that would otherwise stall a decode batch. It is not the steady-state path.

KV for a live session stays inside one rack. Moving a full 1M GLM cache across GB300 RoCE takes about half a second in the model, which consumes most of the one-second cache-hit budget. Cross-rack RoCE carries new replicas, weight loads, and storage, not the hot prefix.

## Explicitly not used

- llm-d as a second router or planner
- a shared Redis KV store
- an exact-match response cache (tool turns differ, and GLM-5.3 cannot turn thinking off)
- a service-mesh sidecar on GPU pods
