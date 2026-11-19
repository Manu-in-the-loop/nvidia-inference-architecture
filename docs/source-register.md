# Source register

Retrieved 19 November 2026. Confidence tags:

- **measured**: a vendor page, model file, or benchmark states the number
- **derived**: arithmetic from measured inputs, done in `capacity/model.py`
- **assumed**: a planning choice this study states because no source gives it
- **provisional**: the publisher says the figure can change

The capacity script is the only place derived seat counts are calculated. This register does not restate those seats.

## Hardware

| Claim | Tag | Source |
| --- | --- | --- |
| GB300 NVL72 is 72 Blackwell Ultra GPUs and 36 Grace CPUs. GPU memory is 20 TB at up to 576 TB/s. CPU memory is 17 TB LPDDR5X at 14 TB/s. NVLink bandwidth is 130 TB/s. Dense FP4 is 1,080 PFLOPS, sparse FP4 is 1,440 PFLOPS. | measured | [NVIDIA GB300 NVL72](https://www.nvidia.com/en-us/data-center/gb300-nvl72/) |
| Each B300 in the Lenovo tray has 288 GB HBM3e. Four ConnectX-8 ports per tray provide up to 800 Gb/s. | measured | [Lenovo GB300 NVL72 product guide](https://lenovopress.lenovo.com/lp2357-lenovo-nvidia-gb300-nvl72-rack-scale-ai) |
| A compute tray has 4 B300 GPUs with 1,152 GB aggregate, 4 ConnectX-8 adapters, one BlueField-3, and about 1 TB of LPDDR5X. The rack needs up to 142 kW. NVLink across 72 GPUs is 130 TB/s. | measured | [NVL72 AI Factory components](https://docs.nvidia.com/enterprise-reference-architectures/nvl72-ai-factory/latest/components.html) |
| Supermicro states GB300 NVL72 operating power of 132–140 kW. The study uses 140 kW. | measured | [Supermicro GB300 NVL72 datasheet](https://www.supermicro.com/datasheet/datasheet_SuperCluster_GB300_NVL72.pdf) |
| The enterprise reference architecture is one rack per scalable unit, tested through 8 scalable units (576 GPUs), on Spectrum-X Ethernet with a rail-optimized fat tree. | measured | [GB300 NVL72 Enterprise RA (PDF)](https://docs.nvidia.com/enterprise-reference-architectures/nvl72-ai-factory-with-gb300-nvl72-dual-plane-networking-architecture.pdf) |
| East-west RoCE is optional for pure inference and recommended for storage. North-south and storage RoCE are recommended for inference. | measured | [Network logical architecture](https://docs.nvidia.com/enterprise-reference-architectures/nvl72-ai-factory/latest/network-logical-architecture.html) |
| ConnectX-8 on GB300 NVL72 provides 800 Gb/s per GPU, on InfiniBand or Spectrum-X Ethernet. | measured | [NVIDIA GB300 NVL72](https://www.nvidia.com/en-us/data-center/gb300-nvl72/) |
| Vera Rubin NVL72 is 72 Rubin GPUs and 36 Vera CPUs, 20.7 TB HBM4, up to 1,580 TB/s, 3,600 PFLOPS NVFP4, NVLink 6 at 260 TB/s, scale-out listed as 28.8 TB/s per rack. Figures are preliminary. | provisional | [NVIDIA Vera Rubin NVL72](https://www.nvidia.com/en-us/data-center/vera-rubin-nvl72.md) |
| DGX Vera Rubin NVL72 lists 144 single-port ConnectX-9 at 800 Gb/s and 18 dual-port BlueField-4. | provisional | [DGX Vera Rubin NVL72](https://www.nvidia.com/en-au/data-center/dgx-vera-rubin-nvl72/) |
| Supermicro lists 288 GB HBM4 per Rubin GPU, 1.6 Tb/s east-west per GPU, 800 Gb/s BlueField-4 north-south, operating power 220 kW, and up to 54 TB LPDDR5X with 768 GB per CPU as the standard tray. | measured, vendor brochure | [Supermicro Vera Rubin brochure](https://www.supermicro.com/manuals/brochure/Brochure_NVIDIA-Vera-Rubin-Architecture-Solutions.pdf) |
| A Vera Rubin SuperPOD scalable unit contains 3 racks (216 GPUs) on a 2-plane Spectrum-X fabric. Each GPU has 2x800 Gb/s east-west. The design scales past 30 scalable units. | measured | [DGX SuperPOD Spectrum-X RA for Vera Rubin NVL72 (PDF)](https://docs.nvidia.com/dgx-superpod-spectrum-x-reference-architecture-with-dgx-vera-rubin-nvl72.pdf) |
| The study treats 1.6 Tb/s per Rubin GPU as the unidirectional RoCE rate. The 28.8 TB/s rack figure is exactly twice the 144x800 Gb/s port total, which is what both directions would sum to. | derived | Product page and SuperPOD RA above |

## Serving software

| Claim | Tag | Source |
| --- | --- | --- |
| Dynamo is the distributed serving layer above TensorRT-LLM and compatible engines. The reference stack also names GPU Operator, Network Operator, KAI Scheduler, Grove, ModelExpress, NIXL, AIPerf, and the KV Block Manager. | measured | [NVIDIA DSX inference reference architecture](https://docs.nvidia.com/dsx/ncp/inference-ra/home) |
| A request enters the Dynamo frontend, the prefill router picks a worker, NIXL moves KV, and the decode worker streams tokens. The Gateway API Inference Extension must not replace that path. Identity and the gateway product are partner choices. | measured | [Dynamo architecture](https://docs.nvidia.com/dynamo/knowledge-base/concepts/architecture) and the DSX RA |
| Dynamo installs on Kubernetes 1.30 or later. The GPU Operator supplies the GPUs. | measured | [Dynamo Kubernetes install](https://docs.nvidia.com/dynamo/kubernetes/installation/install-dynamo) |
| GPU Operator 26.7 supports HGX GB300 NVL72 on ARM, and OpenShift 4.18 through 4.22 and 5.0. ComputeDomain is the Grace Blackwell multi-node NVLink path. | measured | [GPU Operator platform support](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html) and [OpenShift DRA](https://docs.nvidia.com/datacenter/cloud-native/openshift/26.7/dra-gpu-ocp.html) |
| The Network Operator matrix lists OpenShift for GB200 NVL72 and for HGX B300 with ConnectX-8. The fetched page does not name GB300 NVL72 itself. | measured | [Network Operator platform support](https://docs.nvidia.com/networking/display/kubernetes2612/platform-support.html) |
| GPU Operator 26.7's platform list does not include Vera Rubin. Red Hat has announced an intention to support Rubin on OpenShift at general availability. | measured | GPU Operator platform support, and [Red Hat and NVIDIA Rubin announcement](https://www.redhat.com/en/about/press-releases/red-hat-nvidia-pair-enterprise-open-source-rack-scale-ai-faster-production-ready-innovation) |

## Models and benchmarks

| Claim | Tag | Source |
| --- | --- | --- |
| GLM-5.3 is a 753B-parameter MoE, about 40B active, 78 layers, 256 routed experts with top-8 plus one shared expert, MLA latent 512+64, indexer top-2048, 21 full indexer layers and 57 shared, 1,048,576-token context. | measured | `config.json` on [zai-org/GLM-5.3](https://huggingface.co/zai-org/GLM-5.3) retrieved 19 November 2026. Indexer-layer count was checked locally: 21 full, 57 shared. |
| NVIDIA's GLM-5.3 endpoint runs vLLM on Dynamo on GB300, NVFP4 weights, FP8 KV, MTP, data parallel plus expert parallel on 8-GPU workers. | measured | [NVIDIA NIM GLM-5.3](https://docs.api.nvidia.com/nim/reference/z-ai-glm-5-3) |
| The NVFP4 checkpoint `usedStorage` is 464,185,032,918 bytes. Safetensors counts 27,874,712,576 BF16 parameters and 724,775,731,200 U8 elements. SGLang is the eval engine named on the model card. | measured | [nvidia/GLM-5.3-NVFP4](https://huggingface.co/nvidia/GLM-5.3-NVFP4) |
| Stored GLM KV is the MLA latent on every layer plus a 128-wide indexer key on full layers only. Sparse attention still stores every token and reads the indexer across the context. | derived | Config above, cross-checked with the indexer description in [archdb GLM-5.3](https://archdb.vladsavinov.com/models/glm53/) and [InferenceX on GLM-5.3 DSA](https://inferencex.semianalysis.com/blog/sparse-savings-persistent-demand-inside-glm53). The byte formula in the capacity script is this study's, not a quoted engine measurement. |
| Kimi K3 is a 2.8T MoE, 104B active, 896 experts with 16 selected, 93 layers of which 69 are KDA and 24 are gated MLA, 1,048,576-token context, MXFP4 routed experts. | measured | [moonshotai/Kimi-K3](https://huggingface.co/moonshotai/Kimi-K3) config and model card |
| Kimi checkpoint `usedStorage` is 1,561,018,243,668 bytes. | measured | Hugging Face API for `moonshotai/Kimi-K3`, 19 November 2026 |
| FP8 MLA KV at 1,048,576 tokens is 14.496 GB for 24 layers of 576 values. KDA state does not grow with context. | measured arithmetic | [AMD, Kimi K3 on Instinct](https://www.amd.com/en/developer/resources/technical-articles/2026/kimi-k3-on-amd-instinct-gpus.html). The article's per-GPU column label disagrees with the 14.496 GB product; 1,048,576 × 576 × 24 bytes is 14.496 GB, so this study uses that product as the FP8 total. |
| KDA state used here is 69 × 96 × 128 × 128 × 4 bytes. | derived | `linear_attn_config` in the Kimi config: 69 KDA layers, 96 heads, head dim 128. FP32 is the AMD article's stated SSM dtype. |
| TensorRT-LLM on GB300: TEP16, 16 GPUs, concurrency 4, median TPOT 18.12 ms, 55.18 tok/s per user, on an 8k/1k sweep. DEP16 at concurrency 64 falls to 29.36 tok/s per user. Per-rank weights are 115 GB for TEP16 and 210 GB for DEP16. | measured | [TensorRT-LLM Kimi K3 deployment guide](https://nvidia.github.io/TensorRT-LLM/latest/deployment-guide/deployment-guide-for-kimi-k3-on-trtllm.html) |
| Verified MLPerf Endpoints v1.0 GB300 result: TensorRT-LLM 1.3.0rc25 plus Dynamo, concurrency 1,024, 13,905.8 tok/s, 13.6 tok/s per user, TTFT p90 15,223 ms, 90 kW. A separate verified point cited by NVIDIA is concurrency 48 on 48 GPUs, TTFT p90 2,305.1 ms, 2,210.4 tok/s, 56.2 tok/s per user, 60 kW. | measured | [MLPerf report](https://endpoints.mlcommons.org/report?run=1294146a-85b3-4ee8-88b4-7b21efcae7bc&submission=b987824f-ff60-4444-b532-ac0d77e7229b) and [NVIDIA's MLPerf Endpoints write-up](https://developer.nvidia.com/blog/nvidia-vera-rubin-nvl72-leads-agentic-inference-performance-on-mlperf-endpoints-v1-0/) |
| Vera Rubin MLPerf Kimi K3 figures (32 GPUs, concurrency 1,024, 41,414 tok/s, 50.4 tok/s per user) are provisional and are not inputs to the capacity model. | provisional | NVIDIA MLPerf write-up above |
| Dynamo's GB300 Kimi recipes are 16-GPU workers, MXFP4 experts, FP8 KV, with DCP16 or TEP8/TEP16 parallelism, and DSPARK speculation on the GB300 targets. The published agentic target is median 64k input, 400 output, 90% KV hit, 50 tok/s, TTFT p50 at or under 5 seconds. | measured | [Dynamo Kimi-K3 recipes](https://docs.nvidia.com/dynamo/dev/recipes/kimi-k3) |

## Clients

| Claim | Tag | Source |
| --- | --- | --- |
| Claude Code calls the Anthropic Messages API. OpenCode, Cline, and Roo Code call OpenAI Chat Completions. Roo requires native tool-call streaming. | measured | [LocalAI coding-agent API map](https://localai.io/docs/features/coding-agents/) and [Roo Code OpenAI-compatible provider](https://github.com/RooCodeInc/Roo-Code/blob/main/apps/docs/docs/providers/openai-compatible.md) |
| A published harness comparison models a coding session as a ~30k stable prefix, ~2.5k new tokens per turn, ~400 output tokens, ~60 turns. | assumed as the turn shape | [Prompt caching in coding agents](https://www.maximem.ai/blog/prompt-caching-coding-agent-harnesses), checked by that author on 27 October 2026. This study did not re-measure the IDE traffic. |
| In TraceLab coding-agent traces, LLM generation is 41.0% of request response time and tool execution is 59.8%. With human gaps capped at 1 hour, generation is 14.5% of the hour and tools are 21.2%. Uncapped human idle is 92.3% and is not used, because it counts sessions left open for days. | measured | [TraceLab](https://arxiv.org/html/2606.30560v2), Table 7 |
| In GitHub Copilot production traces, median in-turn LLM concurrency is 1.15. Median user idle between turns is 25.2 minutes. KV-cache idle is 1.2 seconds median inside a turn and 2.9 minutes median across turns. Prefix hit rate stays high under 2 minutes of idle and collapses after about 10 minutes. | measured | [Agentic Coding in the Wild](https://arxiv.org/html/2608.00101) |

## Assumptions that are not in a source

| Choice | Tag | Why it is here |
| --- | --- | --- |
| 16 GB of HBM per GPU for runtime overhead | assumed | CUDA graphs, activations, and fragmentation are real and unpublished for these replicas |
| Prefill efficiency 0.35 | assumed | No rack prefill trace was available for these two models |
| Three-rack scheduling factor 0.98, and eight-rack factor 0.97 | assumed | Replicas stay inside one rack. The factor is imbalance, not a RoCE hop |
| Tool gaps under 60 seconds stay in HBM. A pause up to 15 minutes is offloaded to Grace. A longer absence is evicted to NVMe | assumed policy | Copilot's in-turn KV idle P95 is 37 seconds, and hit rate collapses after about 10 minutes. The exact cutoffs are operating choices |
| Rubin uses the GB300 replica shape | assumed | No Rubin serving recipe for GLM-5.3 or Kimi K3 was found |
