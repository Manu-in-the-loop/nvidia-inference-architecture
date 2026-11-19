#!/usr/bin/env python3
"""Capacity model for GLM-5.3 and Kimi K3 on GB300 NVL72 and Vera Rubin NVL72.

Every derived figure is recomputed from capacity/constants.json and
capacity/scenarios.yaml. The script writes results.json, results.csv, and
results.md. It does not invent a second copy of the arithmetic in the report.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GB = 1_000_000_000
TB = 1_000_000_000_000


def load_yaml(path: Path) -> dict:
    """Parse the small nested subset used by scenarios.yaml."""
    return normalize_lists(path)


def normalize_lists(path: Path) -> dict:
    """Re-read so a key whose children are list items becomes a list.

    The first pass cannot know that an empty value introduces a list until it
    sees the dash. Doing it in one forward scan is enough for this file.
    """
    root: dict = {}
    stack: list[tuple[int, object]] = [(-1, root)]

    def attach(parent: object, key: str, value: object) -> None:
        if isinstance(parent, dict):
            parent[key] = value
        elif isinstance(parent, list):
            raise SystemExit(f"cannot attach {key} to a list")

    lines = [
        ln
        for ln in path.read_text().splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    for index, raw in enumerate(lines):
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if line.startswith("- "):
            if not isinstance(parent, list):
                raise SystemExit(f"dash under a non-list: {line}")
            item = {}
            parent.append(item)
            body = line[2:]
            key, value = body.split(":", 1)
            item[key.strip()] = coerce(value.strip())
            stack.append((indent, item))
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        nxt = lines[index + 1] if index + 1 < len(lines) else ""
        nxt_indent = len(nxt) - len(nxt.lstrip(" ")) if nxt else -1
        nxt_list = nxt.strip().startswith("- ") if nxt else False
        if value == "" and nxt_list and nxt_indent > indent:
            container = []
            attach(parent, key, container)
            stack.append((indent, container))
        elif value == "":
            container = {}
            attach(parent, key, container)
            stack.append((indent, container))
        else:
            attach(parent, key, coerce(value))
    return root


def coerce(value: str):
    if value == "":
        return ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if any(c in value for c in ".eE"):
            return float(value)
        return int(value)
    except ValueError:
        return value.strip('"')


def platform_bytes(spec: dict) -> dict:
    gpus = spec["gpus_per_rack"]
    if "hbm_gb_decimal_per_gpu" in spec:
        hbm = spec["hbm_gb_decimal_per_gpu"] * GB
    else:
        hbm = spec["hbm_tb_per_rack"] * TB / gpus
    bw = spec["hbm_bandwidth_tb_per_rack"] * TB / gpus
    nvlink = spec["nvlink_tb_per_rack"] * TB / gpus
    roce = spec["roce_gbps_per_gpu"] * GB / 8
    return {
        "gpus": gpus,
        "hbm": hbm,
        "bw": bw,
        "nvlink": nvlink,
        "roce": roce,
        "host": spec["host_memory_tb"] * TB,
        "host_bw": spec["host_or_c2c_bandwidth_tb_per_rack"] * TB,
        "power_w": spec["operating_power_kw"] * 1000,
        "flops": spec["dense_nvfp4_pflops_per_rack"] * 1e15 / gpus,
    }


def glm_weights(glm: dict) -> dict:
    bf16 = glm["bf16_params"] * 2
    fp8 = glm["fp8_params"] * 1
    fp32 = glm["fp32_params"] * 4
    expert_file = glm["checkpoint_bytes"] - bf16 - fp8 - fp32
    experts = glm["routed_experts"] + glm["shared_experts"]
    shared = expert_file * glm["shared_experts"] / experts
    routed = expert_file * glm["routed_experts"] / experts
    routed_per_gpu = routed / glm["replica_gpus"]
    always = bf16 + fp8 + fp32 + shared
    return {
        "always": always,
        "routed_per_gpu": routed_per_gpu,
        "per_gpu": always + routed_per_gpu,
        "hit_p": glm["experts_per_token"] / glm["routed_experts"],
    }


def glm_kv(glm: dict, context: int, latent_bytes: int = 1, indexer_bytes: int = 2) -> tuple[int, int]:
    latent_dims = glm["kv_lora_rank"] + glm["qk_rope_head_dim"]
    stored = context * (
        glm["layers"] * latent_dims * latent_bytes
        + glm["full_indexer_layers"] * glm["index_head_dim"] * indexer_bytes
    )
    attended = min(context, glm["index_topk"])
    read = (
        context * glm["full_indexer_layers"] * glm["index_head_dim"] * indexer_bytes
        + glm["layers"] * attended * latent_dims * latent_bytes
    )
    return stored, read


def kimi_kv(kimi: dict, context: int) -> tuple[int, int]:
    latent = kimi["kv_lora_rank"] + kimi["qk_rope_head_dim"]
    mla = context * kimi["mla_layers"] * latent  # FP8, one byte
    kda = kimi["kda_layers"] * kimi["kda_heads"] * kimi["kda_head_dim"] ** 2 * 4
    total = mla + kda
    return total, total  # decode reads the whole retained state


def max_batch(step_bytes, bw: float, efficiency: float, limit_s: float) -> int:
    budget = limit_s * efficiency * bw
    best = 0
    for batch in range(1, 100_000):
        if step_bytes(batch) > budget:
            return best
        best = batch
    return best


def achieved_tps(step_bytes, batch: int, bw: float, efficiency: float) -> float:
    if batch <= 0:
        return 0.0
    return 1.0 / (step_bytes(batch) / (efficiency * bw))


def prefill_seconds(active_params: float, tokens: int, flops: float, gpus: int, efficiency: float) -> float:
    return (2 * active_params * tokens) / (flops * gpus * efficiency)


def main() -> None:
    constants = json.loads((ROOT / "constants.json").read_text())
    scenarios = load_yaml(ROOT / "scenarios.yaml")
    runtime = constants["runtime"]
    glm = constants["glm"]
    kimi = constants["kimi"]
    weights = glm_weights(glm)

    # Calibrate HBM efficiency on the published TEP16 point. That point reads
    # essentially the full 115 GB rank plus a small 8k cache. KV is replicated
    # under attention tensor parallel, which is the measured geometry.
    cal = kimi["calibration"]
    cal_store, _ = kimi_kv(kimi, cal["context_tokens"])
    cal_bytes = kimi["weight_gb_decimal_per_rank"] * GB + cal["batch"] * cal_store
    gb300 = platform_bytes(constants["platforms"]["gb300"])
    measured_s = cal["tpot_ms"] / 1000
    efficiency = cal_bytes / (measured_s * gb300["bw"])
    predicted_ms = cal_bytes / gb300["bw"] * 1000
    if not 0.5 < efficiency < 0.95:
        raise SystemExit(f"unexpected HBM efficiency {efficiency:.3f}")

    rows = []
    detail = {
        "hbm_efficiency": efficiency,
        "efficiency_basis": (
            "115 GB TEP16 rank plus replicated FP8/KDA state at batch 4 and "
            f"8,192 tokens, fitted to {cal['tpot_ms']} ms TPOT on GB300"
        ),
        "glm_weight_bytes_per_gpu": weights["per_gpu"],
        "glm_always_read_bytes_per_gpu": weights["always"],
        "predicted_tep16_full_bandwidth_ms": predicted_ms,
        "rows": rows,
    }

    limit_s = 1 / scenarios["slo"]["tokens_per_second_per_developer"]
    suffix = scenarios["turn"]["uncached_suffix_tokens"]
    three = scenarios["scaling"]["three_rack_factor"]
    eight = scenarios["scaling"]["eight_rack_factor"]
    usage = scenarios["usage"]
    gen_share = usage["generation_share_of_active_turn"]
    hour_share = usage["active_turn_share_of_hour"]
    requests_per_developer = usage["requests_per_developer"]

    for platform_id, spec in constants["platforms"].items():
        hw = platform_bytes(spec)
        overhead = runtime["hbm_overhead_gb_decimal_per_gpu"] * GB
        for model_id in ("glm-5.3", "kimi-k3"):
            for scenario in scenarios["scenarios"]:
                context = int(scenario["context_tokens"])
                if model_id == "glm-5.3":
                    replica = glm["replica_gpus"]
                    spare = glm["spare_replicas_per_rack"]
                    stored, read = glm_kv(glm, context)

                    def step_bytes(batch: int, read=read, weights=weights) -> float:
                        touched = 1 - (1 - weights["hit_p"]) ** batch
                        return weights["always"] + touched * weights["routed_per_gpu"] + batch * read

                    free = hw["hbm"] - overhead - weights["per_gpu"]
                    memory_local = int(free // stored) if stored else 0
                    slo_local = max_batch(step_bytes, hw["bw"], efficiency, limit_s)
                    memory_developers_unit = memory_local * replica
                    slo_developers_unit = slo_local * replica
                    kv_for_recall = stored
                else:
                    replica = kimi["replica_gpus"]
                    spare = kimi["spare_replicas_per_rack"]
                    stored, read = kimi_kv(kimi, context)
                    weight = kimi["weight_gb_decimal_per_rank"] * GB

                    def step_bytes(batch: int, read=read, weight=weight, replica=replica) -> float:
                        return weight + batch * (read / replica)

                    free = hw["hbm"] - overhead - weight
                    memory_global = int((free * replica) // stored) if stored else 0
                    slo_global = max_batch(step_bytes, hw["bw"], efficiency, limit_s)
                    memory_developers_unit = memory_global
                    slo_developers_unit = slo_global
                    memory_local = memory_global
                    slo_local = slo_global
                    kv_for_recall = stored

                raw_replicas = hw["gpus"] // replica
                serving_replicas = max(0, raw_replicas - spare)
                memory_developers = memory_developers_unit * serving_replicas
                slo_developers = slo_developers_unit * serving_replicas
                # Tool waits inside a turn leave the GPU idle. Staggered turns
                # share each decode slot. KV still has to fit for every turn.
                active_turns = min(memory_developers, int(slo_developers / gen_share))
                developers = int(active_turns / requests_per_developer)
                reason = "memory" if memory_developers <= int(slo_developers / gen_share) else "slo"
                local = memory_local if reason == "memory" else slo_local
                tps = achieved_tps(step_bytes, max(slo_local, 1), hw["bw"], efficiency)
                if local == 0:
                    tps = 0
                three_devs = int(developers * 3 * three)
                eight_devs = int(developers * 8 * eight)
                served = int(developers / hour_share) if developers else 0
                served_three = int(three_devs / hour_share) if three_devs else 0
                recall_bw = hw["host_bw"] / hw["gpus"]
                recall_s = kv_for_recall / recall_bw if recall_bw else None
                host_slots = int(hw["host"] * runtime["host_memory_usable_fraction"] // kv_for_recall)
                active = glm["active_params"] if model_id == "glm-5.3" else kimi["active_params"]
                # Cold prefill uses the whole replica. Cache-hit prefill of one
                # sequence stays on that sequence's attention rank for GLM (1 GPU)
                # and can use the DCP group for Kimi.
                hit_gpus = 1 if model_id == "glm-5.3" else replica
                cold_gpus = replica
                hit_ttft = prefill_seconds(active, suffix, hw["flops"], hit_gpus, runtime["prefill_efficiency"])
                cold_ttft = prefill_seconds(active, context, hw["flops"], cold_gpus, runtime["prefill_efficiency"])
                suffix_bytes = int(stored * suffix / context)
                nvlink_s = suffix_bytes / hw["nvlink"]
                roce_full_s = stored / hw["roce"]
                rows.append(
                    {
                        "platform": platform_id,
                        "model": model_id,
                        "scenario": scenario["id"],
                        "context_tokens": context,
                        "binding_constraint": reason,
                        "batch_per_attention_group": local,
                        "memory_batch": memory_local,
                        "slo_batch": slo_local,
                        "replicas_per_rack": serving_replicas,
                        "spare_gpus": hw["gpus"] - serving_replicas * replica,
                        "memory_developers_per_rack": memory_developers,
                        "decode_developers_if_synchronized": slo_developers,
                        "active_turns_per_rack": active_turns,
                        "developers_per_rack": developers,
                        "developers_served_per_rack": served,
                        "developers_three_racks": three_devs,
                        "developers_served_three_racks": served_three,
                        "developers_eight_racks": eight_devs,
                        "achieved_tokens_per_second": round(tps, 1),
                        "slo_tokens_per_second_per_rack": developers * scenarios["slo"]["tokens_per_second_per_developer"],
                        "tokens_per_watt_at_slo": round(
                            (developers * scenarios["slo"]["tokens_per_second_per_developer"]) / hw["power_w"], 4
                        ),
                        "kv_gib_per_developer": round(stored / 1024**3, 2),
                        "grace_recall_seconds": round(recall_s, 3),
                        "grace_recall_meets_ttft": recall_s <= scenarios["slo"]["cache_hit_ttft_seconds"],
                        "host_resident_developers_per_rack": host_slots,
                        "cache_hit_ttft_seconds": round(hit_ttft, 3),
                        "cold_ttft_seconds": round(cold_ttft, 2),
                        "suffix_nvlink_seconds": round(nvlink_s, 6),
                        "full_kv_roce_seconds": round(roce_full_s, 3),
                        "generation_share_of_active_turn": gen_share,
                        "active_turn_share_of_hour": hour_share,
                        "requests_per_developer": requests_per_developer,
                    }
                )

    (ROOT / "results.json").write_text(json.dumps(detail, indent=2) + "\n")
    fieldnames = list(rows[0].keys())
    with (ROOT / "results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    write_markdown(rows, detail, scenarios)
    print(f"efficiency={efficiency:.4f}")
    print(f"glm_weight_gib={weights['per_gpu']/1024**3:.2f}")
    for row in rows:
        print(
            f"{row['platform']:6} {row['model']:8} {row['scenario']:8} "
            f"rack={row['developers_per_rack']:6} eight={row['developers_eight_racks']:7} "
            f"bind={row['binding_constraint']:6} tps={row['achieved_tokens_per_second']:7} "
            f"hit={row['cache_hit_ttft_seconds']}s cold={row['cold_ttft_seconds']}s"
        )


def write_markdown(rows: list[dict], detail: dict, scenarios: dict) -> None:
    lines = [
        "# Capacity results",
        "",
        "Generated by `capacity/model.py`. Do not edit by hand.",
        "",
        f"HBM efficiency used for every decode estimate: **{detail['hbm_efficiency']:.3f}**.",
        f"Basis: {detail['efficiency_basis']}.",
        f"GLM-5.3 resident weight per GPU: **{detail['glm_weight_bytes_per_gpu']/1e9:.1f} GB**.",
        "",
        "A concurrent developer is one person in an active agent turn.",
        "Developers served spreads those seats across a working hour using the TraceLab mix.",
        "Three-rack figures multiply one rack by 3 and then by "
        f"{scenarios['scaling']['three_rack_factor']}.",
        "",
        "| Platform | Model | Context | Bind | Concurrent / rack | Served / rack | Concurrent / 3 racks | Served / 3 racks |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {platform} | {model} | {context_tokens} | {binding_constraint} | "
            "{developers_per_rack} | {developers_served_per_rack} | "
            "{developers_three_racks} | {developers_served_three_racks} |".format(**row)
        )
    lines.append("")
    (ROOT / "results.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
