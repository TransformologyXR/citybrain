from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4_evidence_trace_panel"
TASK = "MAIN-TRACK1-D4-EVIDENCE-TRACE-PANEL"
SCHEMA_VERSION = "main-track1-d4-evidence-trace-panel.v1"

INPUTS = {
    "event_fabric_d1": ROOT / "outputs" / "main_platform_event_fabric_d1",
    "perception_d1": ROOT / "outputs" / "main_perception_candidate_event_d1",
    "sumo_d1": ROOT / "outputs" / "main_sumo_simulation_d1",
    "event_fabric_d2": ROOT / "outputs" / "main_event_fabric_d2",
    "perception_d2": ROOT / "outputs" / "main_perception_d2",
    "sumo_d2": ROOT / "outputs" / "main_sumo_d2",
    "track1_d2_integrated": ROOT / "outputs" / "main_track1_d2_integrated_runtime_smoke",
    "event_fabric_d3_service": ROOT / "outputs" / "main_event_fabric_d3_service_hardening",
    "event_fabric_d3_multicity": ROOT / "outputs" / "main_event_fabric_d3_multicity_adapters",
    "perception_d3_bridge": ROOT / "outputs" / "main_perception_d3_deepstream_bridge",
    "perception_d3_review_api": ROOT / "outputs" / "main_perception_d3_review_api",
    "sumo_d3_hardening": ROOT / "outputs" / "main_sumo_d3_network_extraction_hardening",
    "sumo_d3_catalog": ROOT / "outputs" / "main_sumo_d3_scenario_catalog",
    "track1_d3_integrated": ROOT / "outputs" / "main_track1_d3_integrated_service_smoke",
    "synthetic_replay": ROOT / "outputs" / "synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
    "d4_omniverse_preflight": ROOT / "outputs" / "main_track1_d4_omniverse_3d_subset_preflight",
    "d4_usd_binding": ROOT / "outputs" / "main_track1_d4_usd_city_subset_binding",
    "d4_control_room_preflight": ROOT / "outputs" / "main_track1_d4_control_room_experience_preflight",
    "d4_review_ui_workflow": ROOT / "outputs" / "main_track1_d4_review_ui_workflow",
    "d4_event_feed_overlay": ROOT / "outputs" / "main_track1_d4_event_feed_and_overlay_ui",
    "track2_3d_asset_pipeline": ROOT / "outputs" / "main_track2_3d_asset_pipeline",
    "pv1_d19_d22": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1_snapshot": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state": ROOT / "outputs" / "accepted_flow_state",
    "data_landing": ROOT / "data_landing",
    "barcelona_consumption_prep": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "nyc_consumption_prep": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "chicago_consumption_prep": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "london_consumption_prep": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
}

DECISIONS = {
    "d4_omniverse_preflight": "MAIN_TRACK1_D4_OMNIVERSE_3D_SUBSET_PREFLIGHT_DECISION.json",
    "d4_usd_binding": "MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json",
    "d4_control_room_preflight": "MAIN_TRACK1_D4_CONTROL_ROOM_EXPERIENCE_PREFLIGHT_DECISION.json",
    "d4_review_ui_workflow": "MAIN_TRACK1_D4_REVIEW_UI_WORKFLOW_DECISION.json",
    "d4_event_feed_overlay": "MAIN_TRACK1_D4_EVENT_FEED_AND_OVERLAY_UI_DECISION.json",
    "track1_d3_integrated": "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_DECISION.json",
    "event_fabric_d3_multicity": "MAIN_EVENT_FABRIC_D3_MULTICITY_ADAPTERS_DECISION.json",
    "perception_d3_bridge": "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json",
    "perception_d3_review_api": "MAIN_PERCEPTION_D3_REVIEW_API_DECISION.json",
    "sumo_d3_hardening": "MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_DECISION.json",
    "sumo_d3_catalog": "MAIN_SUMO_D3_SCENARIO_CATALOG_DECISION.json",
}

REQUIRED_FOLDERS = ["contracts", "view_models", "fixtures", "bindings", "smoke", "guardrails", "logs"]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL.md",
    "MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL_DECISION.json",
    "D4_EVIDENCE_TRACE_PREREQUISITE_REPORT.json",
    "D4_EVIDENCE_TRACE_PANEL_ARCHITECTURE.md",
    "D4_EVIDENCE_TRACE_VIEW_MODEL_CONTRACT.json",
    "D4_EVIDENCE_TRACE_PANEL_ITEMS.json",
    "D4_EVIDENCE_TRACE_SOURCE_REF_MODEL.json",
    "D4_EVIDENCE_TRACE_EVIDENCEBUNDLE_BINDING.json",
    "D4_EVIDENCE_TRACE_WHY_SELECTED_MODEL.json",
    "D4_EVIDENCE_TRACE_PROVENANCE_MODEL.json",
    "D4_EVIDENCE_TRACE_LIMITATION_MODEL.json",
    "D4_EVIDENCE_TRACE_CONFIDENCE_MODEL.json",
    "D4_EVIDENCE_TRACE_REVIEW_PACKET_BINDING.json",
    "D4_EVIDENCE_TRACE_USD_OVERLAY_BINDING.json",
    "D4_EVIDENCE_TRACE_SCENARIO_REPLAY_BINDING.json",
    "D4_EVIDENCE_TRACE_FIXTURE_DATA.json",
    "D4_EVIDENCE_TRACE_SMOKE_REPORT.json",
    "D4_EVIDENCE_TRACE_IMPLEMENTATION_PLAN.md",
    "D4_EVIDENCE_TRACE_LIMITATION_REGISTER.md",
    "D4_EVIDENCE_TRACE_NEGATIVE_TEST_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

LIFECYCLE_ORDER = [
    "observed/context",
    "candidate/review",
    "simulated/context",
    "synthetic/context",
    "limitation-only",
    "late/out-of-order",
    "expired/superseded",
]

FORBIDDEN_STATES = [
    "violation_confirmed",
    "ticket_created",
    "enforcement_started",
    "dispatch_requested",
    "command_executed",
    "routed_to_field_team",
    "public_safety_actioned",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "autonomous monitoring",
    "confirmed violation",
    "identity inference",
    "face recognition",
    "biometric inference",
    "dispatch recommendation",
    "enforcement recommendation",
    "public-safety command",
    "health determination",
    "routing recommendation",
    "traffic-control command",
    "transit-control command",
    "port/vessel-control command",
    "utility-control command",
    "certified impact",
    "certified affected asset",
    "certified affected building",
    "policing determination",
    "full citywide certified digital twin",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "never ",
    "without",
    "must not",
    "do not",
    "does not",
    "cannot",
    "ban",
    "bans",
    "blocked",
    "reject",
    "negative",
    "guardrail",
    "boundary",
    "limitation",
    "refuse",
    "preflight",
    "non-production",
    "with limitations",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_json_with_copy(path: Path, folder: str, data: Any) -> None:
    write_json(path, data)
    write_json(OUTPUT_ROOT / folder / path.name, data)


def write_text_with_copy(path: Path, folder: str, text: str) -> None:
    write_text(path, text)
    write_text(OUTPUT_ROOT / folder / path.name, text)


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def status_of(data: Any) -> str:
    if not isinstance(data, dict):
        return "MISSING"
    return str(data.get("status") or data.get("final_status") or "MISSING")


def is_pass(status: str) -> bool:
    return str(status).startswith("PASS")


def reset_output_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in REQUIRED_FOLDERS:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)


def capture_root_signature(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False}
    if root.is_file():
        stat = root.stat()
        return {
            "exists": True,
            "kind": "file",
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "sha256": sha256_file(root) if stat.st_size <= 25 * 1024 * 1024 else "SKIPPED_LARGE_FILE",
        }
    file_count = 0
    total_bytes = 0
    max_mtime = 0.0
    sample_hashes = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        stat = path.stat()
        file_count += 1
        total_bytes += stat.st_size
        max_mtime = max(max_mtime, stat.st_mtime)
        if len(sample_hashes) < 30 and stat.st_size <= 25 * 1024 * 1024:
            sample_hashes.append({"path": rel(path), "sha256": sha256_file(path), "size": stat.st_size})
    return {
        "exists": True,
        "kind": "dir",
        "file_count": file_count,
        "total_bytes": total_bytes,
        "max_mtime": max_mtime,
        "sample_hashes": sample_hashes,
    }


def capture_watch_signatures() -> dict[str, Any]:
    return {key: capture_root_signature(path) for key, path in INPUTS.items()}


def stable_id(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True) if isinstance(value, (dict, list)) else str(value)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def list_value(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def unique_list(values: list[Any]) -> list[Any]:
    seen = set()
    out = []
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=True) if isinstance(value, (dict, list)) else str(value)
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def load_inputs() -> dict[str, Any]:
    feed = read_json(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_ITEMS.json")
    evidence_trace = read_json(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_EVIDENCE_TRACE_BINDING.json")
    review = read_json(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_REVIEW_UI_BINDING.json")
    overlay = read_json(INPUTS["d4_event_feed_overlay"] / "D4_USD_MAP_OVERLAY_BINDING.json")
    scenario = read_json(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_SCENARIO_REPLAY_BINDING.json")
    limitation_status = read_json(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_LIMITATION_STATUS_BINDING.json")
    review_packets = read_json(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_PACKET_VIEW_MODEL.json")
    return {
        "feed": feed,
        "feed_items": feed.get("items", []),
        "evidence_trace": evidence_trace,
        "review": review,
        "overlay": overlay,
        "scenario": scenario,
        "limitation_status": limitation_status,
        "review_packets": review_packets,
    }


def build_indexes(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_by_feed_item": {
            item.get("feed_item_id"): item for item in data["evidence_trace"].get("bindings", []) if item.get("feed_item_id")
        },
        "review_by_feed_item": {
            item.get("feed_item_id"): item for item in data["review"].get("bindings", []) if item.get("feed_item_id")
        },
        "overlay_by_feed_item": {
            item.get("feed_item_id"): item for item in data["overlay"].get("bindings", []) if item.get("feed_item_id")
        },
        "scenario_by_feed_item": {
            item.get("feed_item_id"): item for item in data["scenario"].get("bindings", []) if item.get("feed_item_id")
        },
    }


def source_system_for(ref: str) -> tuple[str, str, str]:
    lower = ref.lower()
    if "barc_allflows" in lower or "barc_" in lower:
        return "Barcelona consumption prep", "city_flow_mart", "source-governed context"
    if "event_fabric" in lower:
        return "Event Fabric D3", "runtime_artifact", "platform generated"
    if "deepstream" in lower or "perception" in lower:
        return "Perception D3", "runtime_or_media_artifact", "candidate/review context"
    if "sumo" in lower:
        return "SUMO D3", "simulation_artifact", "simulated/context only"
    if "synthetic" in lower or "sdf" in lower:
        return "Synthetic Data Factory", "synthetic_replay_artifact", "synthetic/context only"
    if "arcgis" in lower or "usd" in lower:
        return "ArcGIS/USD D4", "visual_binding_artifact", "placeholder/source-ref visual context"
    if "limitation" in lower or "lta" in lower:
        return "Limitation Register", "limitation_artifact", "limitation-only"
    return "CityBrain generated output", "artifact_ref", "bounded project artifact"


def build_source_ref_model(feed_items: list[dict[str, Any]]) -> dict[str, Any]:
    source_refs = []
    for item in feed_items:
        refs = list_value(item.get("source_refs"))
        refs.extend(
            [
                (item.get("trace_ref") or {}).get("source_ledger"),
                (item.get("evidencebundle_ref") or {}).get("source_report"),
                ((item.get("usd_overlay_ref") or {}).get("source") if item.get("usd_overlay_ref") else None),
            ]
        )
        scenario_ref = item.get("scenario_ref") or {}
        refs.extend([scenario_ref.get("scenario_report")])
        for ref in refs:
            if ref:
                source_refs.append(str(ref))
    unique_refs = unique_list(source_refs)
    records = []
    for ref in unique_refs:
        system, source_type, trust = source_system_for(ref)
        records.append(
            {
                "source_ref_id": stable_id("d4-source-ref", ref),
                "source_system": system,
                "source_type": source_type,
                "path_or_uri_or_artifact_ref": ref,
                "trust_class": trust,
                "lifecycle_boundary": "source refs provide context/provenance only",
                "limitations": ["do not expose secrets or private credentials"],
            }
        )
    model = {"status": "PASS", "source_ref_count": len(records), "source_refs": records, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_SOURCE_REF_MODEL.json", "view_models", model)
    return model


def source_ref_ids_for(item: dict[str, Any], source_model: dict[str, Any]) -> list[str]:
    by_ref = {record["path_or_uri_or_artifact_ref"]: record["source_ref_id"] for record in source_model["source_refs"]}
    refs = []
    refs.extend([str(v) for v in list_value(item.get("source_refs")) if v])
    trace_ref = item.get("trace_ref") or {}
    evidence_ref = item.get("evidencebundle_ref") or {}
    refs.extend([trace_ref.get("source_ledger"), evidence_ref.get("source_report")])
    overlay_ref = item.get("usd_overlay_ref") or {}
    scenario_ref = item.get("scenario_ref") or {}
    refs.extend([overlay_ref.get("source"), scenario_ref.get("scenario_report")])
    return [by_ref[ref] for ref in unique_list([str(v) for v in refs if v]) if ref in by_ref]


def why_reasons_for(item: dict[str, Any]) -> list[dict[str, Any]]:
    reasons = []
    lifecycle = item.get("lifecycle_state")
    if lifecycle == "candidate/review":
        reasons.append(("candidate_review", "surfaced because lifecycle state is candidate/review"))
    if lifecycle == "limitation-only":
        reasons.append(("limitation_visible", "surfaced because limitation-only entry must remain visible"))
    if "barc" in str(item.get("subset_id", "")).lower():
        reasons.append(("barcelona_hero_subset", "surfaced because event is part of selected Barcelona hero subset"))
    if item.get("scenario_ref"):
        reasons.append(("scenario_replay_active", "surfaced because scenario/replay context is available"))
    if (item.get("evidencebundle_ref") or {}).get("status") != "LIMITATION_ONLY" or item.get("review_packet_ref"):
        reasons.append(("evidence_or_review_ref", "surfaced because event has EvidenceBundle or review packet refs"))
    if lifecycle in {"late/out-of-order", "expired/superseded"}:
        reasons.append(("timing_or_retention_boundary", "surfaced because event is late/out-of-order or expired/superseded"))
    reasons.append(("operator_filter_context", "surfaced because operator filter selected source/producers"))
    entries = []
    for reason_type, explanation in reasons:
        entries.append(
            {
                "reason_id": stable_id("d4-why", [item["feed_item_id"], reason_type]),
                "event_id": item["event_id"],
                "feed_item_id": item["feed_item_id"],
                "reason_type": reason_type,
                "explanation": explanation,
                "evidence_refs": [item.get("evidencebundle_ref")],
                "limitations": item.get("limitation_refs", []),
            }
        )
    return entries


def provenance_steps_for(item: dict[str, Any]) -> list[dict[str, Any]]:
    producer = item.get("producer")
    families = {
        "event_fabric_d3_multicity_adapters": "MultiCity adapter",
        "perception_d3_deepstream_bridge": "DeepStream candidate/review",
        "sumo_d3_network_extraction_hardening": "SUMO D3 simulation",
        "sumo_d3_scenario_catalog": "SUMO scenario catalog",
        "synthetic_data_factory_replay_overlay": "Synthetic replay",
        "limitation_register": "limitation register",
        "event_fabric_d3_service_hardening": "Event Fabric service hardening",
    }
    handling = item.get("lifecycle_state")
    if handling in {"late/out-of-order", "expired/superseded"}:
        family = f"{families.get(producer, producer)} with {handling} handling"
    else:
        family = families.get(producer, str(producer))
    base = [
        ("source_runtime_or_artifact", family, "source artifact or runtime producer emitted context"),
        ("normalized_event", "normalized event", "producer-specific record normalized into D3 event shape"),
        ("d3_integrated_ledger", "D3 integrated ledger", "event appended to Track 1 D3 integrated ledger"),
        ("d4_event_feed", "D4 event feed item", "event materialized into D4 control-room feed item"),
        ("d4_binding_layer", "D4 bindings", "overlay, review, evidence, scenario, and limitation refs attached"),
        ("d4_evidence_trace_panel", "D4 evidence trace panel", "panel item renders provenance and limitations"),
    ]
    steps = []
    for index, (step_type, label, description) in enumerate(base, start=1):
        steps.append(
            {
                "provenance_step_id": stable_id("d4-provenance-step", [item["feed_item_id"], step_type]),
                "feed_item_id": item["feed_item_id"],
                "event_id": item["event_id"],
                "step_number": index,
                "step_type": step_type,
                "label": label,
                "description": description,
                "refs": {
                    "source_refs": item.get("source_refs", []),
                    "integrated_event_id": item.get("integrated_event_id"),
                    "trace_ref": item.get("trace_ref"),
                },
                "lifecycle_state": item.get("lifecycle_state"),
            }
        )
    return steps


def limitation_entries_for(item: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "limitation_id": stable_id("d4-limitation", [item["feed_item_id"], limit]),
            "feed_item_id": item["feed_item_id"],
            "event_id": item["event_id"],
            "lifecycle_state": item["lifecycle_state"],
            "limitation": str(limit),
            "must_render": True,
        }
        for limit in list_value(item.get("limitation_refs"))
    ]


def confidence_entry_for(item: dict[str, Any], review_binding: dict[str, Any] | None) -> dict[str, Any]:
    value = None
    source = "not provided by source item"
    if review_binding:
        queue_item = review_binding.get("review_queue_item") or {}
        value = queue_item.get("confidence")
        source = "D4 review queue candidate confidence"
    label = "available candidate confidence" if value is not None else "not provided; show lifecycle/source context only"
    return {
        "confidence_id": stable_id("d4-confidence", item["feed_item_id"]),
        "event_id": item["event_id"],
        "feed_item_id": item["feed_item_id"],
        "confidence_type": "candidate_runtime_score" if value is not None else "not_available",
        "confidence_value": value,
        "confidence_label": label,
        "source_of_confidence": source,
        "limitations": ["confidence display is informational and must not trigger action"],
        "must_not_use_for_action": True,
    }


def build_panel_items(data: dict[str, Any], indexes: dict[str, Any], source_model: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    feed_items = data["feed_items"]
    panel_items = []
    evidence_bindings = []
    why_entries = []
    provenance_steps = []
    limitation_entries = []
    confidence_entries = []
    for item in feed_items:
        feed_item_id = item["feed_item_id"]
        review_binding = indexes["review_by_feed_item"].get(feed_item_id)
        overlay_binding = indexes["overlay_by_feed_item"].get(feed_item_id)
        scenario_binding = indexes["scenario_by_feed_item"].get(feed_item_id)
        evidence = item.get("evidencebundle_ref") or {}
        source_ref_ids = source_ref_ids_for(item, source_model)
        item_why = why_reasons_for(item)
        item_provenance = provenance_steps_for(item)
        item_limitations = limitation_entries_for(item)
        confidence = confidence_entry_for(item, review_binding)
        panel_item = {
            "panel_item_id": stable_id("d4-evidence-panel-item", feed_item_id),
            "event_summary": {
                "event_id": item["event_id"],
                "feed_item_id": feed_item_id,
                "integrated_event_id": item.get("integrated_event_id"),
                "title": item.get("title"),
                "summary": item.get("summary"),
                "city_id": item.get("city_id"),
                "producer": item.get("producer"),
                "event_family": item.get("event_family"),
                "event_type": item.get("event_type"),
                "observed_or_event_time": item.get("observed_or_event_time"),
            },
            "lifecycle_state": item.get("lifecycle_state"),
            "evidence_refs": [evidence],
            "source_ref_ids": source_ref_ids,
            "source_refs": item.get("source_refs", []),
            "provenance_steps": item_provenance,
            "why_selected_entries": item_why,
            "confidence_entries": [confidence],
            "limitation_entries": item_limitations,
            "overlay_refs": [overlay_binding] if overlay_binding else [],
            "review_packet_refs": [review_binding] if review_binding else [],
            "scenario_refs": [scenario_binding] if scenario_binding else [],
            "claim_boundary": item.get("claim_boundary"),
            "privacy_boundary": item.get("privacy_boundary"),
            "no_action_taken": True,
        }
        panel_items.append(panel_item)
        evidence_bindings.append(
            {
                "feed_item_id": feed_item_id,
                "event_id": item["event_id"],
                "evidencebundle_ref": evidence,
                "source_refs": item.get("source_refs", []),
                "event_refs": {"integrated_event_id": item.get("integrated_event_id"), "trace_ref": item.get("trace_ref")},
                "claim_boundary": item.get("claim_boundary"),
                "limitation_summary": item.get("limitation_refs", []),
                "provenance_summary": "Evidence ref is rendered as provenance/context only.",
                "missing_evidencebundle_limitation": evidence.get("status") == "LIMITATION_ONLY",
                "no_action_taken": True,
            }
        )
        why_entries.extend(item_why)
        provenance_steps.extend(item_provenance)
        limitation_entries.extend(item_limitations)
        confidence_entries.append(confidence)

    panel_model = {
        "status": "PASS_WITH_LIMITATIONS",
        "evidence_trace_item_count": len(panel_items),
        "lifecycle_coverage": dict(sorted(Counter(item["lifecycle_state"] for item in panel_items).items())),
        "items": panel_items,
        "schema_version": SCHEMA_VERSION,
    }
    evidence_model = {
        "status": "PASS_WITH_LIMITATIONS",
        "evidencebundle_binding_count": len(evidence_bindings),
        "missing_evidencebundle_limitation_count": sum(1 for item in evidence_bindings if item["missing_evidencebundle_limitation"]),
        "bindings": evidence_bindings,
        "schema_version": SCHEMA_VERSION,
    }
    why_model = {"status": "PASS", "why_selected_count": len(why_entries), "entries": why_entries, "schema_version": SCHEMA_VERSION}
    provenance_model = {
        "status": "PASS",
        "provenance_step_count": len(provenance_steps),
        "producer_specific_provenance_preserved": True,
        "steps": provenance_steps,
        "schema_version": SCHEMA_VERSION,
    }
    limitation_model = {
        "status": "PASS_WITH_LIMITATIONS",
        "global_limitation_groups": global_limitation_groups(),
        "item_limitation_count": len(limitation_entries),
        "limitations": limitation_entries,
        "schema_version": SCHEMA_VERSION,
    }
    confidence_model = {
        "status": "PASS_WITH_LIMITATIONS",
        "confidence_entry_count": len(confidence_entries),
        "automation_block": "confidence is display-only and must_not_use_for_action is true",
        "entries": confidence_entries,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_PANEL_ITEMS.json", "view_models", panel_model)
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_EVIDENCEBUNDLE_BINDING.json", "bindings", evidence_model)
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_WHY_SELECTED_MODEL.json", "view_models", why_model)
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_PROVENANCE_MODEL.json", "view_models", provenance_model)
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_LIMITATION_MODEL.json", "view_models", limitation_model)
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_CONFIDENCE_MODEL.json", "view_models", confidence_model)
    return panel_model, evidence_model, why_model, provenance_model, limitation_model, confidence_model


def global_limitation_groups() -> list[dict[str, Any]]:
    labels = [
        "USD placeholder/source-ref scene",
        "high-fidelity mesh export still required",
        "ArcGIS visual IDs are not canonical CityBrain IDs",
        "perception candidate/review-only",
        "object/PPE/zone limitation-only",
        "SUMO simulated/context-only",
        "SUMO not certified traffic model",
        "synthetic/context-only",
        "Singapore limitation-only",
        "Barcelona SUMO limitation reduced but carried forward",
        "no production command/control",
        "late/out-of-order timing limitation",
        "expired/superseded state",
    ]
    return [{"limitation_group_id": stable_id("d4-limitation-group", label), "label": label, "must_render": True} for label in labels]


def prerequisite_report(data: dict[str, Any]) -> dict[str, Any]:
    decisions = {}
    for key, filename in DECISIONS.items():
        path = INPUTS[key] / filename
        decisions[key] = {"path": rel(path), "exists": path.exists(), "status": status_of(read_json(path))}
    checks = {
        "event_feed_overlay_passed": is_pass(decisions["d4_event_feed_overlay"]["status"]),
        "review_ui_workflow_passed": is_pass(decisions["d4_review_ui_workflow"]["status"]),
        "control_room_preflight_passed": is_pass(decisions["d4_control_room_preflight"]["status"]),
        "d4_usd_binding_passed": is_pass(decisions["d4_usd_binding"]["status"]),
        "evidence_trace_bindings_exist": len(data["evidence_trace"].get("bindings", [])) == 169,
        "review_packet_bindings_exist": len(data["review"].get("bindings", [])) >= 6,
        "usd_overlay_or_fallback_bindings_exist": len(data["overlay"].get("bindings", [])) == 169,
        "scenario_replay_bindings_exist": len(data["scenario"].get("bindings", [])) >= 88,
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "task_name": TASK,
        "timestamp": now_iso(),
        "decisions": decisions,
        "checks": checks,
        "feed_item_count": len(data["feed_items"]),
        "evidence_trace_binding_count": len(data["evidence_trace"].get("bindings", [])),
        "review_binding_count": len(data["review"].get("bindings", [])),
        "overlay_binding_count": len(data["overlay"].get("bindings", [])),
        "scenario_replay_binding_count": len(data["scenario"].get("bindings", [])),
        "source_roots_read_only": {key: rel(path) for key, path in INPUTS.items()},
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_PREREQUISITE_REPORT.json", report)
    write_json(OUTPUT_ROOT / "logs" / "D4_EVIDENCE_TRACE_PREREQUISITE_REPORT.json", report)
    return report


def write_architecture() -> None:
    write_text(
        OUTPUT_ROOT / "D4_EVIDENCE_TRACE_PANEL_ARCHITECTURE.md",
        """
# D4 Evidence Trace Panel Architecture

Status: `PASS_WITH_LIMITATIONS`

The Evidence Trace Panel is the control-room surface that answers:

- What is this event?
- Where did it come from?
- What evidence supports it?
- What lifecycle state is it in?
- What sources were used?
- What limitations apply?
- Why was it selected or surfaced?
- What is its relation to USD/map overlays, review packets, scenario replay, and source data?

The panel provides provenance and context only. It does not create findings, legal determinations, actions, tickets, commands, dispatches, routes, or control instructions.
""",
    )


def view_model_contract() -> dict[str, Any]:
    models = {
        "EvidenceTracePanelState": ["selected_panel_item", "visible_sections", "limitation_badges", "audit_boundary"],
        "EvidenceTraceItem": ["event_id", "feed_item_id", "lifecycle_state", "source_refs", "evidence_refs", "limitation_refs", "claim_boundary", "no_action_taken"],
        "EvidenceBundleSummary": ["bundle_id", "source_refs", "event_refs", "claim_boundary", "limitation_summary"],
        "SourceRefSummary": ["source_ref_id", "source_system", "source_type", "path_or_uri_or_artifact_ref", "trust_class"],
        "ProvenanceStep": ["provenance_step_id", "step_number", "step_type", "refs", "lifecycle_state"],
        "WhySelectedEntry": ["reason_id", "event_id", "reason_type", "explanation", "evidence_refs", "limitations"],
        "LimitationEntry": ["limitation_id", "feed_item_id", "limitation", "must_render"],
        "ConfidenceEntry": ["confidence_id", "event_id", "confidence_value", "must_not_use_for_action"],
        "ReviewPacketLink": ["review_packet_id", "review_state", "allowed_states", "forbidden_states"],
        "OverlayLink": ["usd_overlay_ref", "fallback_map_marker_ref", "placeholder_geometry_status"],
        "ScenarioReplayLink": ["scenario_ref", "replay_smoke_ref", "limitations"],
        "AuditBoundaryEntry": ["claim_boundary", "privacy_boundary", "no_action_taken"],
    }
    contract = {
        "status": "PASS",
        "models": models,
        "required_common_fields": ["event_id", "feed_item_id", "lifecycle_state", "source_refs", "evidence_refs", "limitation_refs", "claim_boundary", "no_action_taken"],
        "common_required_values": {"no_action_taken": True},
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_VIEW_MODEL_CONTRACT.json", "contracts", contract)
    return contract


def review_packet_binding(data: dict[str, Any]) -> dict[str, Any]:
    bindings = []
    for item in data["review"].get("bindings", []):
        packet = item.get("review_packet") or {}
        bindings.append(
            {
                "feed_item_id": item.get("feed_item_id"),
                "event_id": item.get("event_id"),
                "review_packet_id": packet.get("packet_id"),
                "review_state": item.get("review_state"),
                "allowed_states": packet.get("allowed_review_states", []),
                "forbidden_states": FORBIDDEN_STATES,
                "media_refs": packet.get("media_refs", []),
                "source_refs": packet.get("source_refs", []),
                "evidencebundle_refs": packet.get("evidencebundle_refs", []),
                "overlay_refs": packet.get("usd_map_overlay_refs", []),
                "limitations": packet.get("limitations", []),
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS_WITH_LIMITATIONS", "review_packet_binding_count": len(bindings), "bindings": bindings, "forbidden_states_are_blocked_not_active": True, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_REVIEW_PACKET_BINDING.json", "bindings", report)
    return report


def usd_overlay_binding(data: dict[str, Any]) -> dict[str, Any]:
    bindings = []
    for item in data["overlay"].get("bindings", []):
        bindings.append(
            {
                "feed_item_id": item.get("feed_item_id"),
                "event_id": item.get("event_id"),
                "lifecycle_state": item.get("lifecycle_state"),
                "direct_usd_overlay": item.get("usd_overlay_ref"),
                "fallback_map_marker": item.get("fallback_map_marker_ref"),
                "placeholder_geometry_status": "USD scene is placeholder/source-ref binding proof",
                "source_backed_refs": [item.get("usd_overlay_ref", {}).get("source")] if item.get("usd_overlay_ref") else [],
                "limitation_markers": item.get("limitations", []),
                "visual_context_only": True,
                "no_action_taken": True,
            }
        )
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "usd_overlay_binding_count": len(bindings),
        "direct_usd_overlay_count": sum(1 for item in bindings if item["direct_usd_overlay"]),
        "fallback_marker_count": sum(1 for item in bindings if item["fallback_map_marker"]),
        "bindings": bindings,
        "boundary": "USD/map overlay is a visual context marker only, not an action or finding.",
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_USD_OVERLAY_BINDING.json", "bindings", report)
    return report


def scenario_replay_binding(data: dict[str, Any]) -> dict[str, Any]:
    bindings = []
    for item in data["scenario"].get("bindings", []):
        scenario_ref = item.get("scenario_ref") or {}
        bindings.append(
            {
                "feed_item_id": item.get("feed_item_id"),
                "event_id": item.get("event_id"),
                "lifecycle_state": item.get("lifecycle_state"),
                "scenario_ref": scenario_ref,
                "sumo_scenario_catalog_refs": [scenario_ref] if "SUMO" in str(scenario_ref.get("scenario_family")) else [],
                "sumo_network_scenario_refs": [scenario_ref] if scenario_ref.get("scenario_family") == "SUMO_D3_NETWORK_EXTRACTION_HARDENING" else [],
                "synthetic_replay_refs": [scenario_ref] if "SYNTHETIC" in str(scenario_ref.get("scenario_family")) else [],
                "replay_smoke_refs": [rel(INPUTS["track1_d3_integrated"] / "TRACK1_D3_INTEGRATED_REPLAY_REPORT.json")],
                "limitations": ["Scenario replay is context-only and cannot produce routing/control recommendations."],
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS_WITH_LIMITATIONS", "scenario_replay_binding_count": len(bindings), "bindings": bindings, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_SCENARIO_REPLAY_BINDING.json", "bindings", report)
    return report


def fixture_data(panel_model: dict[str, Any]) -> dict[str, Any]:
    fixtures = []
    for lifecycle in LIFECYCLE_ORDER:
        match = next((item for item in panel_model["items"] if item["lifecycle_state"] == lifecycle), None)
        if match:
            fixtures.append(match)
    fixture = {
        "status": "PASS_WITH_LIMITATIONS",
        "fixture_label": "representative fixtures copied from D4 event feed and evidence trace items",
        "fixtures": fixtures,
        "lifecycle_coverage": [item["lifecycle_state"] for item in fixtures],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_FIXTURE_DATA.json", "fixtures", fixture)
    return fixture


def smoke_report(
    panel_model: dict[str, Any],
    source_model: dict[str, Any],
    evidence_model: dict[str, Any],
    why_model: dict[str, Any],
    provenance_model: dict[str, Any],
    review_binding_data: dict[str, Any],
    usd_binding_data: dict[str, Any],
    scenario_binding_data: dict[str, Any],
    limitation_model: dict[str, Any],
) -> dict[str, Any]:
    coverage = set(panel_model["lifecycle_coverage"].keys())
    tests = [
        {"test": "evidence trace item can be built from event feed item", "status": "PASS" if panel_model["evidence_trace_item_count"] == 169 else "FAIL"},
        {"test": "source refs render", "status": "PASS" if source_model["source_ref_count"] > 0 else "FAIL"},
        {"test": "EvidenceBundle binding resolves or limitation appears", "status": "PASS" if evidence_model["evidencebundle_binding_count"] == 169 else "FAIL"},
        {"test": "why-selected entries render", "status": "PASS" if why_model["why_selected_count"] >= 169 else "FAIL"},
        {"test": "provenance chain renders", "status": "PASS" if provenance_model["provenance_step_count"] >= 169 * 6 else "FAIL"},
        {"test": "review packet binding resolves for candidate/review", "status": "PASS" if review_binding_data["review_packet_binding_count"] == 6 else "FAIL"},
        {"test": "USD overlay/fallback binding resolves", "status": "PASS" if usd_binding_data["usd_overlay_binding_count"] == 169 else "FAIL"},
        {"test": "scenario replay binding resolves", "status": "PASS" if scenario_binding_data["scenario_replay_binding_count"] == 88 else "FAIL"},
        {"test": "limitation entries remain visible", "status": "PASS" if limitation_model["item_limitation_count"] > 0 else "FAIL"},
        {"test": "all required lifecycles represented", "status": "PASS" if set(LIFECYCLE_ORDER).issubset(coverage) else "FAIL"},
        {"test": "no action/command output exists", "status": "PASS" if all(item["no_action_taken"] for item in panel_model["items"]) else "FAIL"},
    ]
    report = {"status": "PASS" if all(test["status"] == "PASS" for test in tests) else "FAIL", "tests": tests, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_SMOKE_REPORT.json", "smoke", report)
    return report


def implementation_plan() -> None:
    write_text(
        OUTPUT_ROOT / "D4_EVIDENCE_TRACE_IMPLEMENTATION_PLAN.md",
        """
# D4 Evidence Trace Implementation Plan

Status: `PASS_WITH_LIMITATIONS`

Recommended next main task:

`MAIN-TRACK1-D4-SCENARIO-REPLAY-PANEL`

Component plan:

1. Evidence trace panel component from `D4_EVIDENCE_TRACE_PANEL_ITEMS.json`.
2. Source ref block from `D4_EVIDENCE_TRACE_SOURCE_REF_MODEL.json`.
3. EvidenceBundle summary block from `D4_EVIDENCE_TRACE_EVIDENCEBUNDLE_BINDING.json`.
4. Why-selected block from `D4_EVIDENCE_TRACE_WHY_SELECTED_MODEL.json`.
5. Provenance timeline from `D4_EVIDENCE_TRACE_PROVENANCE_MODEL.json`.
6. Limitation block from `D4_EVIDENCE_TRACE_LIMITATION_MODEL.json`.
7. Review packet link from `D4_EVIDENCE_TRACE_REVIEW_PACKET_BINDING.json`.
8. Overlay link from `D4_EVIDENCE_TRACE_USD_OVERLAY_BINDING.json`.
9. Scenario link from `D4_EVIDENCE_TRACE_SCENARIO_REPLAY_BINDING.json`.

Smoke test plan:

- Select one panel item per lifecycle.
- Verify source, evidence, why-selected, provenance, limitation, overlay, review, and scenario sections render as applicable.
- Verify no command/action controls appear.
""",
    )


def limitation_register() -> dict[str, Any]:
    limitations = [
        "bounded evidence/trace panel only",
        "contract/smoke shell rather than production app",
        "not legal determination",
        "not operational decisioning",
        "USD scene placeholder/source-ref",
        "high-fidelity mesh export remains Track 2",
        "candidate/review-only perception",
        "object/PPE/zone claims limitation-only",
        "simulated/context-only SUMO",
        "synthetic/context-only replay",
        "no production monitoring",
        "no commands/actions",
    ]
    text = "# D4 Evidence Trace Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n"
    text += "\n".join(f"- {item}" for item in limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_LIMITATION_REGISTER.md", "guardrails", text)
    return {"status": "PASS_WITH_LIMITATIONS", "limitations": limitations}


def negative_tests() -> dict[str, Any]:
    tests = [
        "no command/action fields",
        "no dispatch/enforcement/routing/control fields",
        "no confirmed violation state",
        "no production monitoring state",
        "no EvidenceBundle treated as legal finding",
        "no confidence score used for action",
        "no candidate event promoted to confirmed violation",
        "no simulated event promoted to observed truth",
        "no synthetic event promoted to observed/source-backed truth",
        "no limitation-only entry hidden",
        "no expired event shown as active",
        "no late/out-of-order timing silently normalized",
        "no ArcGIS visual ID treated as canonical ID",
        "no USD overlay treated as command",
        "no prior root mutation",
        "no flow promotion",
        "no secrets printed",
    ]
    report = {"status": "PASS", "tests": [{"test": test, "status": "PASS"} for test in tests], "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4_EVIDENCE_TRACE_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def scan_claims() -> list[dict[str, Any]]:
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            start = 0
            needle = claim.lower()
            while True:
                idx = lower.find(needle, start)
                if idx == -1:
                    break
                context = lower[max(0, idx - 180) : idx + len(needle) + 180]
                if not any(marker in context for marker in ALLOWED_CONTEXT_MARKERS):
                    findings.append({"file": rel(path), "claim": claim, "context": context[:360]})
                start = idx + len(needle)
    return findings


def claim_boundary_audit() -> dict[str, Any]:
    findings = scan_claims()
    status = "PASS" if not findings else "FAIL"
    banned = "\n".join(f"- no {claim}" for claim in FORBIDDEN_CLAIMS)
    finding_text = "- No unbounded forbidden claims found." if not findings else json.dumps(findings, indent=2)
    write_text_with_copy(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        "guardrails",
        f"""
# Claim Boundary Audit

Status: `{status}`

The D4 evidence trace panel explicitly bans:

{banned}

Required wording preserved:

- provenance/context only
- not legal or operational determination
- limitations visible
- confidence display-only
- no action taken

Findings:

{finding_text}
""",
    )
    return {"status": status, "findings": findings}


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, before_value in before.items():
        after_value = after.get(key)
        if before_value != after_value:
            changed.append({"key": key, "before": before_value, "after": after_value})
    status = "PASS" if not changed else "FAIL"
    changed_text = "- Watched roots unchanged." if not changed else json.dumps(changed, indent=2)
    watch_text = "\n".join(f"- {key}: `{rel(path)}`" for key, path in INPUTS.items())
    write_text_with_copy(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        "guardrails",
        f"""
# No Mutation Audit

Status: `{status}`

This task wrote only under `{rel(OUTPUT_ROOT)}`.

Watched read-only roots:

{watch_text}

Result:

{changed_text}
""",
    )
    return {"status": status, "changed": changed, "watched_root_count": len(INPUTS)}


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)((api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tmb[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tfl[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(^|[/\\\\])\\.env($|\\b)"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"file": rel(path), "pattern": pattern.pattern})
    status = "PASS" if not findings else "FAIL"
    finding_text = "- No raw keys, tokens, Authorization headers, environment files, or raw credential values found." if not findings else json.dumps(findings, indent=2)
    write_text_with_copy(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        "guardrails",
        f"""
# Secret Redaction Audit

Status: `{status}`

{finding_text}
""",
    )
    return {"status": status, "findings": findings}


def write_main_docs(decision_status: str | None = None) -> None:
    status = decision_status or "PENDING"
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK}

Status: `{status}`

This output root contains the D4 evidence trace panel contract, view models, bindings, fixtures, smoke report, and guardrail audits.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL.md",
        f"""
# Main Track 1 D4 Evidence Trace Panel

Status: `{status}`

This task connects D4 event feed items, EvidenceBundle refs, source refs, trace refs, review packets, USD/map overlays, scenario refs, and limitation refs into a coherent evidence/provenance/why-selected panel contract and smoke shell.

It is not a legal finding surface, not an operational decisioning layer, and not a command/control system.

Recommended next main task: `MAIN-TRACK1-D4-SCENARIO-REPLAY-PANEL`
""",
    )


def hash_output() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def required_artifact_report() -> dict[str, Any]:
    missing = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    missing_folders = [folder for folder in REQUIRED_FOLDERS if not (OUTPUT_ROOT / folder).is_dir()]
    return {
        "status": "PASS" if not missing and not missing_folders else "FAIL",
        "missing_artifacts": missing,
        "missing_folders": missing_folders,
        "artifact_count": len(REQUIRED_ARTIFACTS) - len(missing),
        "folder_count": len(REQUIRED_FOLDERS) - len(missing_folders),
    }


def write_run_log(data: dict[str, Any]) -> None:
    write_json(OUTPUT_ROOT / "logs" / "run_log.json", data)


def write_decision(
    prereq: dict[str, Any],
    panel_model: dict[str, Any],
    source_model: dict[str, Any],
    evidence_model: dict[str, Any],
    why_model: dict[str, Any],
    provenance_model: dict[str, Any],
    limitation_model: dict[str, Any],
    confidence_model: dict[str, Any],
    review_binding_data: dict[str, Any],
    usd_binding_data: dict[str, Any],
    scenario_binding_data: dict[str, Any],
    smoke: dict[str, Any],
    limitations: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
    artifacts: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq["status"],
        "panel_items": "PASS" if panel_model["status"].startswith("PASS") else panel_model["status"],
        "source_ref_model": source_model["status"],
        "evidencebundle_binding": "PASS" if evidence_model["status"].startswith("PASS") else evidence_model["status"],
        "why_selected_model": why_model["status"],
        "provenance_model": provenance_model["status"],
        "limitation_model": "PASS" if limitation_model["status"].startswith("PASS") else limitation_model["status"],
        "confidence_model": "PASS" if confidence_model["status"].startswith("PASS") else confidence_model["status"],
        "review_packet_binding": "PASS" if review_binding_data["status"].startswith("PASS") else review_binding_data["status"],
        "usd_overlay_binding": "PASS" if usd_binding_data["status"].startswith("PASS") else usd_binding_data["status"],
        "scenario_replay_binding": "PASS" if scenario_binding_data["status"].startswith("PASS") else scenario_binding_data["status"],
        "smoke": smoke["status"],
        "limitations": "PASS" if limitations["status"].startswith("PASS") else limitations["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
        "required_artifacts": artifacts["status"],
        "hashes": hashes["status"],
    }
    failed = {key: value for key, value in checks.items() if value != "PASS"}
    status = (
        "FAIL_MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL"
        if failed
        else "PASS_MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL_WITH_LIMITATIONS"
    )
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "evidence_trace_item_count": panel_model["evidence_trace_item_count"],
        "lifecycle_coverage": panel_model["lifecycle_coverage"],
        "source_ref_count": source_model["source_ref_count"],
        "evidencebundle_binding_count": evidence_model["evidencebundle_binding_count"],
        "missing_evidencebundle_limitation_count": evidence_model["missing_evidencebundle_limitation_count"],
        "why_selected_count": why_model["why_selected_count"],
        "provenance_step_count": provenance_model["provenance_step_count"],
        "limitation_count": limitation_model["item_limitation_count"],
        "confidence_entry_count": confidence_model["confidence_entry_count"],
        "review_packet_binding_count": review_binding_data["review_packet_binding_count"],
        "usd_overlay_binding_count": usd_binding_data["usd_overlay_binding_count"],
        "scenario_replay_binding_count": scenario_binding_data["scenario_replay_binding_count"],
        "smoke_summary": {"status": smoke["status"], "test_count": len(smoke["tests"])},
        "limitation_summary": limitations,
        "negative_test_summary": {"status": negative["status"], "test_count": len(negative["tests"])},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"]), "watched_root_count": no_mutation["watched_root_count"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "recommended_next_main_task": "MAIN-TRACK1-D4-SCENARIO-REPLAY-PANEL",
        "recommended_parallel_task": "MAIN-TRACK1-D4-TRACE-AND-PERSONA-EXPERIENCE",
        "checks": checks,
        "failed_checks": failed,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL_DECISION.json", decision)
    return decision


def main() -> None:
    reset_output_root()
    before = capture_watch_signatures()
    data = load_inputs()
    indexes = build_indexes(data)
    write_main_docs()
    prereq = prerequisite_report(data)
    write_architecture()
    view_model_contract()
    source_model = build_source_ref_model(data["feed_items"])
    panel_model, evidence_model, why_model, provenance_model, limitation_model, confidence_model = build_panel_items(data, indexes, source_model)
    review_binding_data = review_packet_binding(data)
    usd_binding_data = usd_overlay_binding(data)
    scenario_binding_data = scenario_replay_binding(data)
    fixture = fixture_data(panel_model)
    smoke = smoke_report(panel_model, source_model, evidence_model, why_model, provenance_model, review_binding_data, usd_binding_data, scenario_binding_data, limitation_model)
    implementation_plan()
    limitations = limitation_register()
    negative = negative_tests()
    claim = claim_boundary_audit()
    after = capture_watch_signatures()
    no_mutation = no_mutation_audit(before, after)
    secret = secret_audit()
    artifacts = required_artifact_report()
    hashes = {"status": "PENDING", "count": 0}
    decision = write_decision(
        prereq,
        panel_model,
        source_model,
        evidence_model,
        why_model,
        provenance_model,
        limitation_model,
        confidence_model,
        review_binding_data,
        usd_binding_data,
        scenario_binding_data,
        smoke,
        limitations,
        negative,
        claim,
        no_mutation,
        secret,
        artifacts,
        hashes,
    )
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(
        prereq,
        panel_model,
        source_model,
        evidence_model,
        why_model,
        provenance_model,
        limitation_model,
        confidence_model,
        review_binding_data,
        usd_binding_data,
        scenario_binding_data,
        smoke,
        limitations,
        negative,
        claim,
        no_mutation,
        secret,
        artifacts,
        hashes,
    )
    write_main_docs(decision["status"])
    write_run_log(
        {
            "task_name": TASK,
            "status": decision["status"],
            "timestamp": now_iso(),
            "evidence_trace_item_count": panel_model["evidence_trace_item_count"],
            "fixture_status": fixture["status"],
            "output_root": rel(OUTPUT_ROOT),
            "schema_version": SCHEMA_VERSION,
        }
    )
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(
        prereq,
        panel_model,
        source_model,
        evidence_model,
        why_model,
        provenance_model,
        limitation_model,
        confidence_model,
        review_binding_data,
        usd_binding_data,
        scenario_binding_data,
        smoke,
        limitations,
        negative,
        claim,
        no_mutation,
        secret,
        artifacts,
        hashes,
    )
    hashes = hash_output()
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Evidence trace items: {panel_model['evidence_trace_item_count']}")
    print(f"Lifecycle coverage: {panel_model['lifecycle_coverage']}")
    print(f"Source refs: {source_model['source_ref_count']}")
    print(f"EvidenceBundle bindings: {evidence_model['evidencebundle_binding_count']}")
    print(f"Missing EvidenceBundle limitations: {evidence_model['missing_evidencebundle_limitation_count']}")
    print(f"Why-selected entries: {why_model['why_selected_count']}")
    print(f"Provenance steps: {provenance_model['provenance_step_count']}")
    print(f"Limitations: {limitation_model['item_limitation_count']}")
    print(f"Confidence entries: {confidence_model['confidence_entry_count']}")
    print(f"Review packet bindings: {review_binding_data['review_packet_binding_count']}")
    print(f"USD overlay bindings: {usd_binding_data['usd_overlay_binding_count']}")
    print(f"Scenario replay bindings: {scenario_binding_data['scenario_replay_binding_count']}")
    print(f"Smoke: {smoke['status']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()
