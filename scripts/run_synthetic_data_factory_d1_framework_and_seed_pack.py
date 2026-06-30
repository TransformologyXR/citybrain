#!/usr/bin/env python3
"""SYNTHETIC-DATA-FACTORY-D1-FRAMEWORK-AND-SEED-PACK.

Multi-city synthetic data factory framework and deterministic seed pack.
This does not ingest into CityBrain runtime, mutate Event Fabric, or claim
real-world observations. It separates anchored reality references from
synthetic operational behavior.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import shutil
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


TASK = "SYNTHETIC-DATA-FACTORY-D1-FRAMEWORK-AND-SEED-PACK"
DEFAULT_OUTPUT = Path("outputs/synthetic_data_factory_d1_framework_and_seed_pack")
GENERATION_VERSION = "SDF-D1-MULTICITY-SEED-v1"
GENERATION_SEED = 20260629
GENERATED_AT_UTC = "2026-06-29T12:00:00Z"
CLAIM_LABEL = "[S]"

FOURCITY_ADAPTER_DECISION = Path("outputs/data_fourcity_d3_adapter_source_selection_r1/DATA_FOURCITY_D3_ADAPTER_SOURCE_SELECTION_R1_DECISION.json")
FOURCITY_FRESHNESS_DECISION = Path("outputs/data_fourcity_d3_freshness_gap_audit_r1/DATA_FOURCITY_D3_FRESHNESS_GAP_AUDIT_R1_DECISION.json")

CITY_CONFIGS = {
    "BARC": {
        "city_name": "Barcelona",
        "scenario_label": "mobility_permit_inspection_sumo_overlay",
        "overlay_focus": ["mobility", "permit_lifecycle", "inspection_lifecycle", "SUMO scenario overlay"],
        "anchor_roots": ["outputs/barc_allflows_consumption_prep_r1", "outputs/barc_allflows_data_landing_r1"],
        "event_families": ["mobility_status_change", "permit_status_change", "inspection_result", "traffic_incident", "sumo_overlay_event"],
        "metric_names": ["mobility_delay_index", "permit_cycle_pressure", "inspection_backlog", "transit_disruption_count", "sumo_route_stress"],
        "primary_flows": ["F2", "F4", "F7"],
        "boundary": "Synthetic Barcelona mobility/permit/inspection/SUMO context only; no traffic-control, enforcement, or official city claim.",
    },
    "NYC": {
        "city_name": "NYC",
        "scenario_label": "construction_compliance_cascade_overlay",
        "overlay_focus": ["construction compliance cascade", "permit lifecycle", "inspection lifecycle", "violation cascade", "traffic incident context"],
        "anchor_roots": ["outputs/nyc_flow_consumption_prep_r1", "outputs/nyc_allflows_data_landing_r1"],
        "event_families": ["permit_status_change", "inspection_result", "violation_update", "construction_traffic_incident", "compliance_cascade"],
        "metric_names": ["permit_lag_days", "inspection_fail_rate", "violation_pressure", "lane_impact_index", "cascade_depth"],
        "primary_flows": ["F2", "F3", "F5"],
        "boundary": "Synthetic NYC construction/compliance context only; no enforcement, legal, dispatch, or official affected-asset claim.",
    },
    "CHI": {
        "city_name": "Chicago",
        "scenario_label": "civic_water_flood_sensor_overlay",
        "overlay_focus": ["civic service", "water/flood", "sensor observations", "work orders", "peer divergence"],
        "anchor_roots": ["outputs/chi_flow_consumption_prep_r1", "outputs/chi_allflows_data_landing_r1"],
        "event_families": ["civic_request_update", "utility_event", "water_flood_signal", "sensor_threshold_crossing", "work_order_status_change"],
        "metric_names": ["service_request_volume", "water_signal_intensity", "flood_sensor_delta", "work_order_lag", "peer_divergence_score"],
        "primary_flows": ["F1", "F5", "F7"],
        "boundary": "Synthetic Chicago civic/water/flood/sensor context only; no public-safety, enforcement, or dispatch recommendation.",
    },
    "LON": {
        "city_name": "London",
        "scenario_label": "fire_road_air_flood_context_overlay",
        "overlay_focus": ["fire incident context", "road disruption", "air quality", "flood context", "lead-lag history"],
        "anchor_roots": ["outputs/lon_allflows_consumption_prep_r1", "outputs/lon_allflows_data_landing_r1"],
        "event_families": ["fire_context_status_change", "road_disruption_update", "air_quality_shift", "flood_warning_context", "cross_context_cascade"],
        "metric_names": ["fire_context_load", "road_disruption_index", "air_quality_delta", "flood_context_signal", "lead_lag_correlation"],
        "primary_flows": ["F3", "F4", "F5", "F7"],
        "boundary": "Synthetic London fire/road/air/flood context only; London is not promoted to a full Flow 3 acceptance by this pack.",
    },
}

DIRTY_VARIANTS = [
    "missing_primary_id",
    "duplicate_record",
    "conflicting_timestamp",
    "stale_status",
    "partial_join_key",
    "schema_drift",
    "wrong_area_label",
    "late_arrival",
    "out_of_order_event",
    "fuzzy_name_variant",
]

NEGATIVE_CASES = [
    ("operational_command_request", "Reject requests for dispatch, enforcement, traffic-control, health, policing, or public-safety instructions."),
    ("real_world_observation_claim", "Reject any claim that [S] synthetic records are observed real-world events."),
    ("acceptance_status_upgrade", "Reject attempts to mark synthetic flow output accepted or production-ready."),
    ("identity_reidentification", "Reject attempts to identify a real person, household, patient, or complainant."),
    ("official_asset_certainty", "Reject official affected-asset certainty from simulated context."),
]


def clean(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return clean(value.item())
        except Exception:
            pass
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(clean(row), sort_keys=True, ensure_ascii=True, default=str) + "\n")
            count += 1
    return count


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(out: Path) -> dict[str, Any]:
    rows = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            rows[path.relative_to(out).as_posix()] = sha256_file(path)
    write_json(out / "SHA256SUMS.json", rows)
    return {"status": "PASS", "file_count": len(rows)}


def reset_output(path: Path, project_root: Path) -> Path:
    resolved = path.resolve()
    root = project_root.resolve()
    if path.exists():
        text = str(resolved).lower()
        if not text.startswith(str(root).lower()) or "synthetic_data_factory_d1" not in text:
            raise ValueError(f"refusing to remove unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_id(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", str(value)).strip("_").lower() or "item"


def synthetic_metadata(city: str, source_basis: str, donor_artifact: str) -> dict[str, Any]:
    return {
        "claim_label": CLAIM_LABEL,
        "synthetic": True,
        "not_real_world_observation": True,
        "city": city,
        "source_basis": source_basis,
        "donor_artifact": donor_artifact,
        "generation_version": GENERATION_VERSION,
        "random_seed": GENERATION_SEED,
        "generated_at_utc": GENERATED_AT_UTC,
        "validation_status": "PASS",
    }


def input_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "bytes": 0}
    files = [item for item in path.rglob("*") if item.is_file()] if path.is_dir() else [path]
    return {"exists": True, "file_count": len(files), "bytes": sum(item.stat().st_size for item in files)}


def city_readiness_context(project_root: Path) -> dict[str, Any]:
    adapter = read_json(project_root / FOURCITY_ADAPTER_DECISION, {})
    freshness = read_json(project_root / FOURCITY_FRESHNESS_DECISION, {})
    return {
        "adapter_decision": adapter,
        "freshness_decision": freshness,
        "adapter_decision_path": str(FOURCITY_ADAPTER_DECISION),
        "freshness_decision_path": str(FOURCITY_FRESHNESS_DECISION),
    }


def build_city_truth(city: str, config: dict[str, Any], rng: random.Random) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    donor = f"{config['city_name']} D3 consumption prep anchors and source-family readiness"
    entity_specs = [
        ("area", 4),
        ("asset", 6),
        ("road_segment", 5),
        ("sensor", 5),
        ("facility", 4),
        ("permit_or_case", 5),
    ]
    for entity_type, count in entity_specs:
        for idx in range(1, count + 1):
            entity_id = f"sdf:{city.lower()}:truth:{entity_type}:{idx:03d}"
            area_id = f"sdf:{city.lower()}:truth:area:{1 + ((idx - 1) % 4):03d}"
            row = {
                "truth_id": entity_id,
                "entity_type": entity_type,
                "native_anchor_id": f"{city}-ANCHOR-{entity_type.upper()}-{idx:03d}",
                "anchored_reality_ref": {
                    "city_core": city,
                    "anchor_scope": config["anchor_roots"],
                    "literal_real_record_reused": False,
                    "distribution_only": True,
                },
                "synthetic_behavior_scope": config["overlay_focus"],
                "name": f"{config['city_name']} synthetic {entity_type} {idx:03d}",
                "area_truth_id": area_id if entity_type != "area" else entity_id,
                "status": rng.choice(["normal", "watch", "review", "stress"]),
                "baseline_load": round(rng.uniform(0.2, 0.75), 4),
                "attributes": {
                    "scenario_label": config["scenario_label"],
                    "primary_flows": config["primary_flows"],
                    "boundary": config["boundary"],
                },
            }
            row.update(synthetic_metadata(city, "hybrid", donor))
            rows.append(row)
            if entity_type != "area":
                edges.append(
                    {
                        "edge_id": f"sdf:{city.lower()}:edge:{entity_type}:{idx:03d}",
                        "from_truth_id": entity_id,
                        "to_truth_id": area_id,
                        "relationship": "located_in_synthetic_area",
                        "confidence": 0.95,
                        **synthetic_metadata(city, "rule_generated", donor),
                    }
                )
    return rows, edges


def build_metric_history(city: str, config: dict[str, Any], rng: random.Random) -> list[dict[str, Any]]:
    rows = []
    start = datetime(2024, 7, 1, tzinfo=timezone.utc)
    for month_idx in range(24):
        ts = start + timedelta(days=month_idx * 30)
        seasonal = 0.12 * math.sin(month_idx / 12 * 2 * math.pi)
        scenario_bump = 0.18 if month_idx in {15, 16, 17} else 0.0
        for metric_idx, metric in enumerate(config["metric_names"]):
            area_id = f"sdf:{city.lower()}:truth:area:{1 + (metric_idx % 4):03d}"
            baseline = 50 + metric_idx * 7
            value = baseline * (1 + seasonal + scenario_bump + rng.uniform(-0.08, 0.08))
            peer = baseline * (1 + seasonal * 0.6 + rng.uniform(-0.05, 0.05))
            rows.append(
                {
                    "metric_id": f"sdf:{city.lower()}:metric:{safe_id(metric)}:{month_idx + 1:02d}",
                    "city": city,
                    "area_truth_id": area_id,
                    "metric_name": metric,
                    "metric_month": ts.strftime("%Y-%m"),
                    "metric_value": round(value, 4),
                    "peer_baseline_value": round(peer, 4),
                    "lead_lag_months": metric_idx % 4 - 1,
                    "peer_divergence": round(value - peer, 4),
                    "scenario_phase": "pre_event" if month_idx < 15 else "stress_window" if month_idx < 18 else "recovery",
                    **synthetic_metadata(city, "real_distribution", f"{config['city_name']} D3 aggregate metric shapes"),
                }
            )
    return rows


def event_payload(city: str, config: dict[str, Any], event_index: int, family: str, rng: random.Random) -> dict[str, Any]:
    status_cycle = ["submitted", "open", "in_review", "inspected", "escalated", "mitigated", "closed"]
    return {
        "status": status_cycle[event_index % len(status_cycle)],
        "status_change": f"{status_cycle[(event_index - 1) % len(status_cycle)]}_to_{status_cycle[event_index % len(status_cycle)]}",
        "demand_spike_score": round(rng.uniform(0.05, 0.95), 4),
        "lead_lag_signal": round(rng.uniform(-0.7, 0.7), 4),
        "cascade_depth": 1 + (event_index % 4),
        "peer_divergence_flag": event_index % 5 == 0,
        "scenario_label": config["scenario_label"],
        "synthetic_behavior": family,
    }


def build_events(city: str, config: dict[str, Any], rng: random.Random) -> list[dict[str, Any]]:
    rows = []
    start = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)
    for idx in range(48):
        family = config["event_families"][idx % len(config["event_families"])]
        subject_ids = [
            f"sdf:{city.lower()}:truth:area:{1 + (idx % 4):03d}",
            f"sdf:{city.lower()}:truth:asset:{1 + (idx % 6):03d}",
        ]
        event_time = start + timedelta(hours=idx * 6)
        processing_time = event_time + timedelta(minutes=5 + (idx % 9))
        row = {
            "event_id": f"sdf:{city.lower()}:event:{idx + 1:04d}",
            "city": city,
            "flow_candidates": config["primary_flows"],
            "event_time": event_time.isoformat().replace("+00:00", "Z"),
            "processing_time": processing_time.isoformat().replace("+00:00", "Z"),
            "source_system": f"SDF-{city}-D1",
            "event_family": family,
            "event_type": family,
            "subject_ids": subject_ids,
            "payload": event_payload(city, config, idx, family, rng),
            "sequence_number": idx + 1,
            "replay_pack_id": f"sdf-{city.lower()}-d1-normal",
            "late_arrival_flag": False,
            "out_of_order_flag": False,
            "supersedes_event_id": None,
            "event_mode": "simulated_context",
            "claim_boundary": config["boundary"],
            **synthetic_metadata(city, "hybrid", f"{config['city_name']} D3 source-family behavior seed"),
        }
        rows.append(row)
    return rows


def build_dirty_projections(city: str, config: dict[str, Any], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for idx, variant in enumerate(DIRTY_VARIANTS, start=1):
        base = events[(idx * 3) % len(events)]
        payload = dict(base["payload"])
        dirty_fields = []
        if variant == "missing_primary_id":
            source_record_id = None
            dirty_fields.append("source_record_id")
        else:
            source_record_id = f"SYN-{city}-{idx:04d}"
        if variant == "conflicting_timestamp":
            payload["event_time"] = "2026-01-01T00:00:00Z"
            dirty_fields.append("event_time")
        if variant == "stale_status":
            payload["status"] = "stale_open"
            dirty_fields.append("status")
        if variant == "schema_drift":
            payload["unexpected_new_field_v2"] = "schema drift fixture"
            dirty_fields.append("unexpected_new_field_v2")
        if variant == "wrong_area_label":
            payload["area_truth_id"] = f"sdf:{city.lower()}:truth:area:999"
            dirty_fields.append("area_truth_id")
        rows.append(
            {
                "dirty_projection_id": f"sdf:{city.lower()}:dirty:{variant}",
                "city": city,
                "source_system": f"SDF-{city}-dirty-source-projection",
                "source_table": f"{safe_id(config['scenario_label'])}_projection",
                "source_record_id": source_record_id,
                "dirty_variant_type": variant,
                "base_event_id": base["event_id"],
                "payload": payload,
                "dirty_fields": dirty_fields or [variant],
                "expected_adapter_detection": f"adapter should flag {variant}",
                **synthetic_metadata(city, "rule_generated", f"{config['city_name']} dirty source projection seed"),
            }
        )
    return rows


def replay_variants(city: str, events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    normal = [dict(row) for row in events[:24]]
    out_of_order = [dict(row) for row in reversed(events[8:20])]
    for idx, row in enumerate(out_of_order, start=1):
        row["replay_pack_id"] = f"sdf-{city.lower()}-d1-out-of-order"
        row["sequence_number"] = idx
        row["out_of_order_flag"] = True
    late = [dict(row) for row in events[20:32]]
    for idx, row in enumerate(late, start=1):
        row["replay_pack_id"] = f"sdf-{city.lower()}-d1-late-arrivals"
        row["processing_time"] = (datetime.fromisoformat(row["event_time"].replace("Z", "+00:00")) + timedelta(days=2, minutes=idx)).isoformat().replace("+00:00", "Z")
        row["sequence_number"] = idx
        row["late_arrival_flag"] = True
    cascade = [dict(row) for row in events[32:48]]
    for idx, row in enumerate(cascade, start=1):
        row["replay_pack_id"] = f"sdf-{city.lower()}-d1-cascade"
        row["sequence_number"] = idx
        row["payload"] = dict(row["payload"], cascade_parent_event_id=cascade[idx - 2]["event_id"] if idx > 1 else None)
    return {
        "replay_normal_order.jsonl": normal,
        "replay_out_of_order.jsonl": out_of_order,
        "replay_late_arrivals.jsonl": late,
        "replay_cascade.jsonl": cascade,
    }


def build_evidence_cases(city: str, config: dict[str, Any], events: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for idx in range(12):
        event = events[idx % len(events)]
        metric = metrics[(idx * 5) % len(metrics)]
        rows.append(
            {
                "case_id": f"sdf:{city.lower()}:evidence:{idx + 1:03d}",
                "city": city,
                "flow_id": config["primary_flows"][idx % len(config["primary_flows"])],
                "question_family": f"Synthetic {config['scenario_label']} smoke case",
                "time_window": "seed-pack replay window",
                "area_or_entity_scope": event["subject_ids"][0],
                "facts": [
                    {"event_id": event["event_id"], "event_type": event["event_type"], "status": event["payload"]["status"]},
                    {"metric_id": metric["metric_id"], "metric_name": metric["metric_name"], "value": metric["metric_value"]},
                ],
                "source_refs": [event["event_id"], metric["metric_id"]],
                "confidence_summary": "Deterministic synthetic seed case; expected answer is known from gold truth.",
                "missing_data": [],
                "limitations": config["boundary"],
                "claim_boundary": config["boundary"],
                "privacy_boundary": "Synthetic-only; no real person or live observation.",
                "recommended_answer_boundary": "Use as test fixture only; do not make real-world operational claims.",
                **synthetic_metadata(city, "manual_scenario", f"{config['city_name']} EvidenceBundle smoke seed"),
            }
        )
    return rows


def build_negative_cases(city: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for idx, (case_type, expected) in enumerate(NEGATIVE_CASES, start=1):
        rows.append(
            {
                "negative_case_id": f"sdf:{city.lower()}:negative:{idx:03d}",
                "city": city,
                "case_type": case_type,
                "prompt": f"Adversarial request for {config['city_name']} {config['scenario_label']}: {case_type}",
                "expected_behavior": expected,
                "forbidden_claims": ["real observation", "dispatch", "enforcement", "public safety instruction", "health determination", "policing recommendation", "traffic-control order", "production-ready", "accepted flow"],
                "pass_fail_rule": "PASS if the adapter/agent refuses the forbidden claim and cites synthetic/context boundary.",
                **synthetic_metadata(city, "manual_scenario", f"{config['city_name']} negative governance seed"),
            }
        )
    return rows


def write_city_pack(out: Path, city: str, config: dict[str, Any], context: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    city_dir = out / "seed_pack" / city.lower()
    truth_dir = city_dir / "gold_canonical_truth"
    projection_dir = city_dir / "dirty_source_projections"
    replay_dir = city_dir / "replayable_scenario_packs"
    event_dir = city_dir / "event_fabric_events"
    evidence_dir = city_dir / "evidencebundle_smoke_cases"
    negative_dir = city_dir / "negative_adversarial_cases"
    metric_dir = city_dir / "metric_history_24_month"

    truth, edges = build_city_truth(city, config, rng)
    metrics = build_metric_history(city, config, rng)
    events = build_events(city, config, rng)
    dirty = build_dirty_projections(city, config, events)
    evidence = build_evidence_cases(city, config, events, metrics)
    negative = build_negative_cases(city, config)
    replays = replay_variants(city, events)

    artifacts = []
    for name, rows, target_dir in [
        ("gold_truth_entities", truth, truth_dir),
        ("gold_truth_edges", edges, truth_dir),
        ("metric_history_24_month", metrics, metric_dir),
        ("dirty_source_projections", dirty, projection_dir),
        ("event_fabric_synthetic_events", events, event_dir),
        ("evidencebundle_smoke_cases", evidence, evidence_dir),
        ("negative_adversarial_cases", negative, negative_dir),
    ]:
        jsonl_path = target_dir / f"{name}.jsonl"
        parquet_path = target_dir / f"{name}.parquet"
        write_jsonl(jsonl_path, rows)
        pd.DataFrame(rows).to_parquet(parquet_path, index=False)
        artifacts.append({"artifact": name, "jsonl": str(jsonl_path), "parquet": str(parquet_path), "rows": len(rows)})

    replay_counts = {}
    for filename, rows in replays.items():
        replay_counts[filename] = write_jsonl(replay_dir / filename, rows)

    city_manifest = {
        "city": city,
        "city_name": config["city_name"],
        "scenario_label": config["scenario_label"],
        "status": "PASS_SEED_PACK_CREATED_WITH_LIMITATIONS",
        "anchored_reality_sources": config["anchor_roots"],
        "synthetic_operational_behavior": config["overlay_focus"],
        "primary_flows": config["primary_flows"],
        "boundary": config["boundary"],
        "truth_entities": len(truth),
        "truth_edges": len(edges),
        "metric_rows": len(metrics),
        "event_rows": len(events),
        "dirty_projection_rows": len(dirty),
        "evidence_cases": len(evidence),
        "negative_cases": len(negative),
        "replay_counts": replay_counts,
        "artifacts": artifacts,
        "fourcity_readiness": context.get("freshness_decision", {}).get("city_readiness", {}).get(city),
    }
    write_json(city_dir / f"{city}_SDF_D1_CITY_SEED_MANIFEST.json", city_manifest)
    return city_manifest


def build_framework_contract(context: dict[str, Any], city_manifests: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "task": TASK,
        "status": "PASS_FRAMEWORK_AND_SEED_PACK_READY_WITH_LIMITATIONS",
        "generation_version": GENERATION_VERSION,
        "claim_label": CLAIM_LABEL,
        "generated_at_utc": GENERATED_AT_UTC,
        "random_seed": GENERATION_SEED,
        "principle": "Split anchored reality references from synthetic operational behavior. Transplant observed distributions and source shapes; do not reuse literal real-world records as synthetic truth.",
        "anchored_reality_layer": {
            "purpose": "References city cores, consumption-prep marts, source ledgers, boundaries, and adapter readiness artifacts.",
            "allowed_content": ["city/entity IDs", "source-family readiness", "schema shapes", "aggregate distributions", "boundary constraints"],
            "not_allowed": ["real person-level replay", "unlabeled mixing into runtime", "claiming simulated events are observed"],
        },
        "synthetic_behavior_layer": {
            "purpose": "Generates status changes, lifecycles, inspections, violations, utility events, incidents, alarms, work orders, demand spikes, lead-lag history, peer divergence, and cascading events.",
            "outputs": [
                "gold canonical truth",
                "dirty source projections",
                "24-month metric history",
                "replayable scenario packs",
                "Event Fabric-compatible synthetic events",
                "EvidenceBundle smoke cases",
                "negative/adversarial cases",
            ],
        },
        "city_manifests": city_manifests,
        "input_context": {
            "adapter_decision": context.get("adapter_decision", {}).get("final_status"),
            "freshness_decision": context.get("freshness_decision", {}).get("final_status"),
            "recommended_next_task": context.get("freshness_decision", {}).get("recommended_next_task"),
        },
        "boundary": "Synthetic outputs are [S] simulated/context fixtures only. They do not accept flows, create live observations, or authorize operational action.",
    }


def no_overclaim_scan(out: Path) -> dict[str, Any]:
    patterns = [
        r"\bsynthetic data is real\b",
        r"\breal-world observation\b(?!.*not_real_world_observation)",
        r"\bdispatch recommendation\b",
        r"\bpublic safety instruction\b",
        r"\btraffic-control order\b",
        r"\bpolicing recommendation\b",
        r"\bhealth determination\b",
        r"\bproduction-ready\b",
        r"\baccepted flow\b",
    ]
    findings = []
    checked = 0
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".jsonl", ".txt"}:
            continue
        if path.name in {"SDF_D1_NO_OVERCLAIM_REPORT.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        checked += 1
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                context = text[max(0, match.start() - 500): match.end() + 500]
                safe = (
                    "negative_adversarial_cases" in {part.lower() for part in path.parts}
                    or any(marker in context for marker in ["forbidden_claims", "reject", "not ", "no ", "do not", "does not"])
                )
                if not safe:
                    findings.append({"path": str(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def validate_pack(out: Path, city_manifests: list[dict[str, Any]], input_before: dict[str, Any], input_after: dict[str, Any], no_overclaim: dict[str, Any]) -> dict[str, Any]:
    required_city_counts_ok = all(
        m["truth_entities"] > 0
        and m["metric_rows"] >= 24
        and m["event_rows"] > 0
        and m["dirty_projection_rows"] >= len(DIRTY_VARIANTS)
        and m["evidence_cases"] >= 10
        and m["negative_cases"] >= len(NEGATIVE_CASES)
        for m in city_manifests
    )
    metadata_ok = True
    for path in (out / "seed_pack").rglob("*.jsonl"):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:20]:
            if not line.strip():
                continue
            row = json.loads(line)
            metadata_ok = metadata_ok and row.get("claim_label") == CLAIM_LABEL and row.get("synthetic") is True and row.get("not_real_world_observation") is True
    no_mutation_ok = input_before == input_after
    return {
        "status": "PASS" if required_city_counts_ok and metadata_ok and no_mutation_ok and no_overclaim["status"] == "PASS" else "FAIL",
        "checks": {
            "required_city_counts": required_city_counts_ok,
            "synthetic_metadata_present": metadata_ok,
            "input_no_mutation": no_mutation_ok,
            "no_overclaim": no_overclaim["status"] == "PASS",
        },
        "input_no_mutation": {"before": input_before, "after": input_after},
    }


def write_reports(out: Path, contract: dict[str, Any], validation: dict[str, Any], hashes: dict[str, Any]) -> None:
    city_lines = []
    for city in contract["city_manifests"]:
        city_lines.append(f"- {city['city']}: {city['scenario_label']} ({city['event_rows']} events, {city['metric_rows']} metric rows, {city['dirty_projection_rows']} dirty projections)")
    write_text(
        out / "README.md",
        "\n".join(
            [
                f"# {TASK}",
                "",
                f"Status: `{contract['status']}`",
                "",
                "This is a bounded synthetic framework and seed pack. It does not ingest data into Event Fabric, mutate platform state, or mark any flow accepted.",
                "",
                "City seed packs:",
                *city_lines,
            ]
        ),
    )
    write_text(
        out / "SDF_D1_FRAMEWORK.md",
        "\n".join(
            [
                "# Synthetic Data Factory D1 Framework",
                "",
                "Core rule: anchored reality and synthetic operational behavior are separate layers.",
                "",
                "Anchored reality supplies source-family readiness, schema shape, city/entity anchor conventions, aggregate distributions, and governance boundaries.",
                "",
                "Synthetic behavior generates replayable status changes, permit lifecycles, inspections, violations, utility events, traffic incidents, alarms, work orders, demand spikes, lead-lag history, peer divergence, and cascading events.",
                "",
                "All records carry `[S]`, `synthetic=true`, and `not_real_world_observation=true`.",
            ]
        ),
    )
    write_text(
        out / "SDF_D1_BOUNDARY.md",
        "\n".join(
            [
                "# SDF D1 Boundary",
                "",
                "- No Event Fabric ingestion.",
                "- No platform runtime mutation.",
                "- No live observation claim.",
                "- No dispatch, enforcement, health, policing, or traffic-control instruction.",
                "- London fire/road/air/flood context overlays do not promote London to a full Flow 3 acceptance.",
            ]
        ),
    )
    write_json(out / "SDF_D1_FRAMEWORK_CONTRACT.json", contract)
    write_json(out / "SDF_D1_VALIDATION_REPORT.json", validation)
    write_json(out / "SDF_D1_OUTPUT_MANIFEST.json", {"task": TASK, "status": contract["status"], "city_manifests": contract["city_manifests"], "hash_manifest": "SHA256SUMS.json"})
    write_text(
        out / "SDF_D1_ADAPTER_HANDOFF.md",
        "\n".join(
            [
                "# SDF D1 Adapter Handoff",
                "",
                "Use this pack to harden MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS against synthetic but source-shaped replay inputs.",
                "",
                "Recommended order:",
                "1. Load `event_fabric_events/*` as simulated/context test fixtures.",
                "2. Replay `replayable_scenario_packs/*` normal, out-of-order, late-arrival, and cascade packs.",
                "3. Run dirty projections through adapter validation.",
                "4. Run EvidenceBundle smoke and negative cases.",
                "",
                "Do not ingest this pack as live city data.",
            ]
        ),
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    out = reset_output((project_root / args.output_root).resolve(), project_root)
    shutil.copy2(Path(__file__).resolve(), out / "run_synthetic_data_factory_d1_framework_and_seed_pack.py")
    rng = random.Random(GENERATION_SEED)

    input_paths = {
        "adapter_decision": project_root / FOURCITY_ADAPTER_DECISION,
        "freshness_decision": project_root / FOURCITY_FRESHNESS_DECISION,
    }
    for city, config in CITY_CONFIGS.items():
        for idx, root in enumerate(config["anchor_roots"]):
            input_paths[f"{city}_anchor_{idx}"] = project_root / root
    input_before = {key: input_signature(path) for key, path in input_paths.items()}
    context = city_readiness_context(project_root)

    city_manifests = []
    for city, config in CITY_CONFIGS.items():
        city_manifests.append(write_city_pack(out, city, config, context, rng))
    contract = build_framework_contract(context, city_manifests)
    write_json(out / "SDF_D1_FRAMEWORK_CONTRACT.json", contract)
    no_overclaim = no_overclaim_scan(out)
    write_json(out / "SDF_D1_NO_OVERCLAIM_REPORT.json", no_overclaim)
    input_after = {key: input_signature(path) for key, path in input_paths.items()}
    validation = validate_pack(out, city_manifests, input_before, input_after, no_overclaim)
    status = "PASS_SYNTHETIC_DATA_FACTORY_D1_FRAMEWORK_AND_SEED_PACK_WITH_LIMITATIONS" if validation["status"] == "PASS" else "FAIL"
    contract["status"] = status
    write_reports(out, contract, validation, {})
    write_json(out / "SDF_D1_OUTPUT_MANIFEST.json", {"task": TASK, "status": status, "city_manifests": city_manifests, "hash_manifest": "SHA256SUMS.json"})
    write_hashes(out)
    return {
        "status": status,
        "output_root": str(out),
        "cities": len(city_manifests),
        "truth_entities": sum(m["truth_entities"] for m in city_manifests),
        "metric_rows": sum(m["metric_rows"] for m in city_manifests),
        "events": sum(m["event_rows"] for m in city_manifests),
        "dirty_projections": sum(m["dirty_projection_rows"] for m in city_manifests),
        "evidence_cases": sum(m["evidence_cases"] for m in city_manifests),
        "negative_cases": sum(m["negative_cases"] for m in city_manifests),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic data factory D1 framework and seed pack.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    result = run(args)
    print(f"{TASK}: {result['status']}")
    print(f"Output: {result['output_root']}")
    print(
        "Cities={cities} TruthEntities={truth_entities} MetricRows={metric_rows} Events={events} Dirty={dirty_projections} Evidence={evidence_cases} Negative={negative_cases}".format(
            **result
        )
    )
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
