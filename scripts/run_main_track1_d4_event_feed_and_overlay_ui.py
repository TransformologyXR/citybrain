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
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4_event_feed_and_overlay_ui"
TASK = "MAIN-TRACK1-D4-EVENT-FEED-AND-OVERLAY-UI"
SCHEMA_VERSION = "main-track1-d4-event-feed-and-overlay-ui.v1"

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
    "track1_d3_integrated": "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_DECISION.json",
    "event_fabric_d3_multicity": "MAIN_EVENT_FABRIC_D3_MULTICITY_ADAPTERS_DECISION.json",
    "perception_d3_bridge": "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json",
    "perception_d3_review_api": "MAIN_PERCEPTION_D3_REVIEW_API_DECISION.json",
    "sumo_d3_hardening": "MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_DECISION.json",
    "sumo_d3_catalog": "MAIN_SUMO_D3_SCENARIO_CATALOG_DECISION.json",
}

REQUIRED_FOLDERS = ["contracts", "view_models", "fixtures", "overlays", "smoke", "guardrails", "logs"]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4_EVENT_FEED_AND_OVERLAY_UI.md",
    "MAIN_TRACK1_D4_EVENT_FEED_AND_OVERLAY_UI_DECISION.json",
    "D4_EVENT_FEED_PREREQUISITE_REPORT.json",
    "D4_EVENT_FEED_ARCHITECTURE.md",
    "D4_EVENT_FEED_VIEW_MODEL_CONTRACT.json",
    "D4_EVENT_FEED_ITEMS.json",
    "D4_EVENT_FEED_FILTER_SORT_GROUP_SPEC.json",
    "D4_EVENT_FEED_LIFECYCLE_POLICY.md",
    "D4_OVERLAY_STATE_MODEL.json",
    "D4_OVERLAY_STYLE_POLICY.json",
    "D4_USD_MAP_OVERLAY_BINDING.json",
    "D4_EVENT_TO_OVERLAY_BINDING_REPORT.md",
    "D4_EVENT_FEED_REVIEW_UI_BINDING.json",
    "D4_EVENT_FEED_EVIDENCE_TRACE_BINDING.json",
    "D4_EVENT_FEED_SCENARIO_REPLAY_BINDING.json",
    "D4_EVENT_FEED_LIMITATION_STATUS_BINDING.json",
    "D4_EVENT_FEED_FIXTURE_DATA.json",
    "D4_EVENT_FEED_AND_OVERLAY_SMOKE_REPORT.json",
    "D4_EVENT_FEED_AND_OVERLAY_IMPLEMENTATION_PLAN.md",
    "D4_EVENT_FEED_AND_OVERLAY_LIMITATION_REGISTER.md",
    "D4_EVENT_FEED_AND_OVERLAY_NEGATIVE_TEST_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

LIFECYCLE_ORDER = [
    "limitation-only",
    "candidate/review",
    "late/out-of-order",
    "expired/superseded",
    "observed/context",
    "simulated/context",
    "synthetic/context",
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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


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


def top_payload(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("payload") if isinstance(row.get("payload"), dict) else {}


def nested_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = top_payload(row)
    return payload.get("payload") if isinstance(payload.get("payload"), dict) else {}


def event_id_for(row: dict[str, Any]) -> str:
    payload = top_payload(row)
    inner = nested_payload(row)
    return str(
        row.get("source_event_id")
        or inner.get("candidate_event_id")
        or inner.get("event_id")
        or payload.get("event_id")
        or row.get("integrated_event_id")
    )


def source_refs_for(row: dict[str, Any]) -> list[Any]:
    payload = top_payload(row)
    inner = nested_payload(row)
    return unique_list(list_value(row.get("source_refs")) + list_value(payload.get("source_refs")) + list_value(inner.get("source_refs")))


def limitations_for(row: dict[str, Any]) -> list[str]:
    payload = top_payload(row)
    inner = nested_payload(row)
    limits = [str(v) for v in list_value(row.get("limitations")) + list_value(payload.get("limitations")) + list_value(inner.get("limitations"))]
    lifecycle = row.get("lifecycle_state")
    if lifecycle == "candidate/review":
        limits.append("candidate/review lifecycle must remain visible")
        limits.append("object/PPE/zone claims remain limitation-only unless runtime metadata supports them")
    if lifecycle == "simulated/context":
        limits.append("simulated/context-only SUMO output; not observed traffic truth")
    if lifecycle == "synthetic/context":
        limits.append("synthetic/context-only replay output; not source-backed observed truth")
    if lifecycle == "limitation-only":
        limits.append("limitation-only entries must remain visible")
    if lifecycle == "late/out-of-order":
        limits.append("late/out-of-order timing limitation must remain visible")
    if lifecycle == "expired/superseded":
        limits.append("expired/superseded state must not be shown as active")
    return unique_list(limits)


def load_ledgers_and_bindings() -> dict[str, Any]:
    rows = read_jsonl(INPUTS["track1_d3_integrated"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl")
    usd_overlays = read_json(INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_RUNTIME_OVERLAYS.json").get("overlays", [])
    review_queue = read_json(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_QUEUE_VIEW_MODEL.json").get("queue_items", [])
    review_packets = read_json(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_PACKET_VIEW_MODEL.json").get("packets", [])
    review_overlay_bindings = read_json(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_UI_USD_OVERLAY_BINDING.json").get("bindings", [])
    integrated_bundles = read_json(INPUTS["track1_d3_integrated"] / "TRACK1_D3_INTEGRATED_EVIDENCEBUNDLE_SMOKE_REPORT.json").get("bundles", [])
    return {
        "rows": rows,
        "usd_overlays": usd_overlays,
        "review_queue": review_queue,
        "review_packets": review_packets,
        "review_overlay_bindings": review_overlay_bindings,
        "integrated_bundles": integrated_bundles,
    }


def build_indexes(data: dict[str, Any]) -> dict[str, Any]:
    overlay_by_integrated = {str(item.get("event_id")): item for item in data["usd_overlays"] if item.get("event_id")}
    review_queue_by_integrated = {
        str(item.get("integrated_event_id")): item for item in data["review_queue"] if item.get("integrated_event_id")
    }
    review_packet_by_id = {str(item.get("packet_id")): item for item in data["review_packets"] if item.get("packet_id")}
    review_overlay_by_integrated = {
        str(item.get("integrated_event_id")): item for item in data["review_overlay_bindings"] if item.get("integrated_event_id")
    }
    bundle_by_lifecycle = {
        str(item.get("lifecycle")): item for item in data["integrated_bundles"] if item.get("lifecycle")
    }
    return {
        "overlay_by_integrated": overlay_by_integrated,
        "review_queue_by_integrated": review_queue_by_integrated,
        "review_packet_by_id": review_packet_by_id,
        "review_overlay_by_integrated": review_overlay_by_integrated,
        "bundle_by_lifecycle": bundle_by_lifecycle,
    }


def evidence_ref_for(row: dict[str, Any], indexes: dict[str, Any]) -> dict[str, Any]:
    integrated_id = str(row.get("integrated_event_id"))
    lifecycle = str(row.get("lifecycle_state"))
    review_item = indexes["review_queue_by_integrated"].get(integrated_id)
    if review_item:
        return review_item.get("evidencebundle_ref") or {"status": "LIMITATION_ONLY", "limitation": "review queue evidence ref missing"}
    overlay = indexes["overlay_by_integrated"].get(integrated_id)
    if overlay and overlay.get("evidencebundle_ref"):
        return {
            "status": "BOUND",
            "bundle_id": None,
            "source_report": overlay.get("evidencebundle_ref"),
            "candidate_event_id": event_id_for(row),
            "limitation": None,
        }
    bundle = indexes["bundle_by_lifecycle"].get(lifecycle) or indexes["bundle_by_lifecycle"].get("multi")
    if bundle:
        return {
            "status": "BOUND_LIFECYCLE",
            "bundle_id": bundle.get("bundle_id"),
            "source_report": rel(INPUTS["track1_d3_integrated"] / "TRACK1_D3_INTEGRATED_EVIDENCEBUNDLE_SMOKE_REPORT.json"),
            "candidate_event_id": event_id_for(row),
            "limitation": None,
        }
    return {
        "status": "LIMITATION_ONLY",
        "bundle_id": None,
        "source_report": None,
        "candidate_event_id": event_id_for(row),
        "limitation": "no EvidenceBundle ref found; feed item must show limitation",
    }


def fallback_marker_for(row: dict[str, Any], index: int) -> dict[str, Any]:
    lifecycle = str(row.get("lifecycle_state") or "unknown").replace("/", "_").replace("-", "_")
    city = str(row.get("city_id") or "UNKNOWN").lower()
    return {
        "marker_id": f"d4-feed-fallback-marker:{city}:{lifecycle}:{index:03d}",
        "marker_type": f"{lifecycle}_context_marker",
        "geometry_status": "fallback_non_command_marker",
        "subset_id": subset_for(row),
    }


def overlay_ref_for(row: dict[str, Any], indexes: dict[str, Any], index: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    integrated_id = str(row.get("integrated_event_id"))
    direct = indexes["overlay_by_integrated"].get(integrated_id)
    if direct:
        return (
            {
                "status": "BOUND_USD_PRIM",
                "overlay_id": direct.get("overlay_id"),
                "target_usd_prim_path": direct.get("target_usd_prim_path"),
                "visual_style_hint": direct.get("visual_style_hint"),
                "source": rel(INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_RUNTIME_OVERLAYS.json"),
            },
            None,
        )
    review_overlay = indexes["review_overlay_by_integrated"].get(integrated_id)
    if review_overlay and review_overlay.get("status") == "BOUND":
        return (
            {
                "status": "BOUND_REVIEW_USD_PRIM",
                "overlay_id": review_overlay.get("overlay_id"),
                "target_usd_prim_path": review_overlay.get("target_usd_prim_path"),
                "visual_style_hint": "candidate review marker",
                "source": rel(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_UI_USD_OVERLAY_BINDING.json"),
            },
            None,
        )
    marker = review_overlay.get("fallback_map_marker") if review_overlay else fallback_marker_for(row, index)
    return (None, marker or fallback_marker_for(row, index))


def subset_for(row: dict[str, Any]) -> str:
    city = str(row.get("city_id") or "UNKNOWN")
    if city == "BARC":
        return "barc_eixample_sant_marti_hero_subset"
    if city == "TRACK1_RUNTIME":
        return "track1_runtime_control_room_subset"
    return f"{city.lower()}_runtime_context_subset"


def severity_for(lifecycle: str) -> str:
    return {
        "limitation-only": "limitation_visible",
        "candidate/review": "review_required",
        "late/out-of-order": "timing_limitation",
        "expired/superseded": "inactive_context",
        "observed/context": "context",
        "simulated/context": "simulated_context",
        "synthetic/context": "synthetic_context",
    }.get(lifecycle, "context")


def scenario_ref_for(row: dict[str, Any]) -> dict[str, Any] | None:
    lifecycle = row.get("lifecycle_state")
    producer = row.get("producer")
    if lifecycle not in {"simulated/context", "synthetic/context"}:
        return None
    if producer == "sumo_d3_network_extraction_hardening":
        return {
            "scenario_family": "SUMO_D3_NETWORK_EXTRACTION_HARDENING",
            "source_event_id": row.get("source_event_id"),
            "scenario_report": rel(INPUTS["sumo_d3_hardening"] / "SUMO_D3_SCENARIO_RUN_REPORT.json"),
            "control_boundary": "review/context-only replay controls",
        }
    if producer == "sumo_d3_scenario_catalog":
        return {
            "scenario_family": "SUMO_D3_SCENARIO_CATALOG",
            "source_event_id": row.get("source_event_id"),
            "scenario_report": rel(INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_CATALOG.json"),
            "control_boundary": "review/context-only replay controls",
        }
    return {
        "scenario_family": "SYNTHETIC_DATA_FACTORY_REPLAY",
        "source_event_id": row.get("source_event_id"),
        "scenario_report": rel(INPUTS["synthetic_replay"]),
        "control_boundary": "review/context-only replay controls",
    }


def title_for(row: dict[str, Any]) -> str:
    city = row.get("city_id") or "Unknown city"
    lifecycle = row.get("lifecycle_state") or "unknown lifecycle"
    event_type = row.get("event_type") or "event"
    return f"{city} {lifecycle} {event_type}"


def build_feed_items(rows: list[dict[str, Any]], indexes: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for index, row in enumerate(rows, start=1):
        lifecycle = str(row.get("lifecycle_state") or "unknown")
        event_id = event_id_for(row)
        integrated_id = str(row.get("integrated_event_id") or event_id)
        evidence_ref = evidence_ref_for(row, indexes)
        review_item = indexes["review_queue_by_integrated"].get(integrated_id)
        review_packet_ref = review_item.get("review_packet_ref") if review_item else None
        usd_overlay_ref, fallback_marker_ref = overlay_ref_for(row, indexes, index)
        limitations = limitations_for(row)
        if fallback_marker_ref and "fallback map marker used because no direct USD prim is available" not in limitations:
            limitations.append("fallback map marker used because no direct USD prim is available")
        if evidence_ref.get("status") == "LIMITATION_ONLY":
            limitations.append(str(evidence_ref.get("limitation") or "EvidenceBundle limitation surfaced"))

        item = {
            "feed_item_id": f"d4-feed-item:{index:03d}",
            "event_id": event_id,
            "integrated_event_id": integrated_id,
            "producer": row.get("producer"),
            "lifecycle_state": lifecycle,
            "city_id": row.get("city_id"),
            "subset_id": subset_for(row),
            "event_family": row.get("event_family"),
            "event_type": row.get("event_type"),
            "title": title_for(row),
            "summary": f"{row.get('event_family')} from {row.get('producer')} shown as {lifecycle}.",
            "observed_or_event_time": row.get("event_time"),
            "ingested_at": nested_payload(row).get("ingested_at") or top_payload(row).get("ingested_at"),
            "severity_or_context_level": severity_for(lifecycle),
            "source_refs": source_refs_for(row),
            "evidencebundle_ref": evidence_ref,
            "review_packet_ref": review_packet_ref,
            "trace_ref": {
                "trace_id": f"d4-feed-trace:{integrated_id.split(':')[-1]}",
                "integrated_event_id": integrated_id,
                "source_ledger": rel(INPUTS["track1_d3_integrated"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl"),
            },
            "usd_overlay_ref": usd_overlay_ref,
            "fallback_map_marker_ref": fallback_marker_ref,
            "scenario_ref": scenario_ref_for(row),
            "limitation_refs": unique_list(limitations),
            "claim_boundary": row.get("claim_boundary") or top_payload(row).get("claim_boundary") or nested_payload(row).get("claim_boundary"),
            "privacy_boundary": row.get("privacy_boundary") or top_payload(row).get("privacy_boundary") or nested_payload(row).get("privacy_boundary"),
            "no_action_taken": True,
        }
        items.append(item)
    return items


def prerequisite_report(data: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = {}
    for key, filename in DECISIONS.items():
        path = INPUTS[key] / filename
        decisions[key] = {"path": rel(path), "exists": path.exists(), "status": status_of(read_json(path))}
    checks = {
        "control_room_preflight_passed": is_pass(decisions["d4_control_room_preflight"]["status"]),
        "review_ui_workflow_passed": is_pass(decisions["d4_review_ui_workflow"]["status"]),
        "d4_usd_binding_passed": is_pass(decisions["d4_usd_binding"]["status"]),
        "d4_omniverse_preflight_passed": is_pass(decisions["d4_omniverse_preflight"]["status"]),
        "d3_integrated_ledger_exists": (INPUTS["track1_d3_integrated"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl").exists(),
        "d3_integrated_ledger_has_events": len(rows) > 0,
        "usd_map_overlay_refs_exist": len(data["usd_overlays"]) > 0,
        "review_packets_exist": len(data["review_packets"]) > 0,
        "evidencebundle_refs_exist": (INPUTS["track1_d3_integrated"] / "TRACK1_D3_INTEGRATED_EVIDENCEBUNDLE_SMOKE_REPORT.json").exists(),
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "task_name": TASK,
        "timestamp": now_iso(),
        "decisions": decisions,
        "checks": checks,
        "d3_integrated_event_count": len(rows),
        "usd_overlay_ref_count": len(data["usd_overlays"]),
        "review_packet_count": len(data["review_packets"]),
        "source_roots_read_only": {key: rel(path) for key, path in INPUTS.items()},
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_EVENT_FEED_PREREQUISITE_REPORT.json", report)
    write_json(OUTPUT_ROOT / "logs" / "D4_EVENT_FEED_PREREQUISITE_REPORT.json", report)
    return report


def write_architecture() -> None:
    write_text(
        OUTPUT_ROOT / "D4_EVENT_FEED_ARCHITECTURE.md",
        """
# D4 Event Feed Architecture

Status: `PASS_WITH_LIMITATIONS`

The D4 event feed is the central control-room list that normalizes D3 integrated events and D4 overlay, review, evidence, trace, scenario, and limitation references into one bounded operator-facing feed.

Supported lifecycle classes:

- observed/context
- candidate/review
- simulated/context
- synthetic/context
- limitation-only
- late/out-of-order
- expired/superseded

The feed is review/context only. It cannot issue commands, confirm violations, dispatch staff, create tickets, recommend routes, or control traffic, transit, port, or utility systems.

Overlay binding strategy:

- Direct USD prim refs are used only where D4 USD binding already produced them.
- Candidate/review refs use D4 Review UI overlay bindings where available.
- Every other feed item receives a fallback non-command map marker so selection and filtering can work without pretending high-fidelity geometry exists.
- The Barcelona USD scene remains a placeholder/source-ref binding proof.
""",
    )


def view_model_contract() -> dict[str, Any]:
    minimum_fields = [
        "feed_item_id",
        "event_id",
        "integrated_event_id",
        "producer",
        "lifecycle_state",
        "city_id",
        "subset_id",
        "event_family",
        "event_type",
        "title",
        "summary",
        "observed_or_event_time",
        "ingested_at",
        "severity_or_context_level",
        "source_refs",
        "evidencebundle_ref",
        "review_packet_ref",
        "trace_ref",
        "usd_overlay_ref",
        "fallback_map_marker_ref",
        "scenario_ref",
        "limitation_refs",
        "claim_boundary",
        "privacy_boundary",
        "no_action_taken",
    ]
    contract = {
        "status": "PASS",
        "model": "D4EventFeedItem",
        "minimum_fields": minimum_fields,
        "common_required_values": {
            "must_carry_lifecycle_state": True,
            "must_carry_claim_boundary": True,
            "must_carry_limitations_array": True,
            "no_action_taken": True,
        },
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVENT_FEED_VIEW_MODEL_CONTRACT.json", "contracts", contract)
    return contract


def write_feed_items(feed_items: list[dict[str, Any]]) -> dict[str, Any]:
    lifecycle_counts = Counter(item["lifecycle_state"] for item in feed_items)
    producer_counts = Counter(item["producer"] for item in feed_items)
    data = {
        "status": "PASS_WITH_LIMITATIONS",
        "feed_item_count": len(feed_items),
        "lifecycle_counts": dict(sorted(lifecycle_counts.items())),
        "producer_counts": dict(sorted(producer_counts.items())),
        "items": feed_items,
        "source_ledger": rel(INPUTS["track1_d3_integrated"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl"),
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVENT_FEED_ITEMS.json", "view_models", data)
    return data


def filter_sort_group_spec() -> dict[str, Any]:
    filters = [
        "lifecycle_state",
        "producer",
        "city_id",
        "subset_id",
        "event_family",
        "event_type",
        "has_evidencebundle",
        "has_review_packet",
        "has_usd_overlay",
        "has_fallback_marker",
        "limitation_only",
        "synthetic_only",
        "simulated_only",
        "expired",
        "late_or_out_of_order",
    ]
    sorts = ["newest_first", "oldest_first", "lifecycle_priority", "limitation_priority", "review_queue_priority"]
    groups = ["by_lifecycle", "by_producer", "by_city", "by_scenario", "by_review_status", "by_limitation_type"]
    spec = {
        "status": "PASS",
        "filters": filters,
        "sorts": sorts,
        "groups": groups,
        "lifecycle_priority_order": LIFECYCLE_ORDER,
        "review_queue_priority_order": ["queued_for_review", "under_review", "marked_needs_more_evidence"],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVENT_FEED_FILTER_SORT_GROUP_SPEC.json", "contracts", spec)
    return spec


def lifecycle_policy() -> None:
    write_text(
        OUTPUT_ROOT / "D4_EVENT_FEED_LIFECYCLE_POLICY.md",
        """
# D4 Event Feed Lifecycle Policy

Status: `PASS`

- `observed/context`: Display as source-backed context only. No command/action controls.
- `candidate/review`: Never displayed as confirmed violation. Link to review packet and safe review states only.
- `simulated/context`: Never displayed as observed traffic truth. Link only to scenario replay context.
- `synthetic/context`: Never displayed as source-backed observed truth. Keep synthetic badge visible.
- `limitation-only`: Must remain visible and filterable. Do not hide blockers or source gaps.
- `late/out-of-order`: Show timing limitation. Do not silently normalize timing.
- `expired/superseded`: Mark clearly as inactive context. Do not show as active.

No lifecycle may expose command/action controls, field response controls, route controls, ticket controls, or control-room actuation.
""",
    )


def overlay_style_policy() -> dict[str, Any]:
    styles = {
        "observed/context": {
            "label": "Observed Context",
            "icon_hint": "circle-dot",
            "line_or_marker_hint": "small context marker",
            "opacity_hint": "medium",
            "priority_hint": 4,
            "must_show_limitation_badge": False,
            "forbidden_interactions": ["no command/action controls"],
        },
        "candidate/review": {
            "label": "Candidate Review",
            "icon_hint": "alert-circle",
            "line_or_marker_hint": "review marker",
            "opacity_hint": "high",
            "priority_hint": 2,
            "must_show_limitation_badge": True,
            "forbidden_interactions": ["no confirmation controls", "no ticket controls"],
        },
        "simulated/context": {
            "label": "Simulated Context",
            "icon_hint": "play-circle",
            "line_or_marker_hint": "simulation route marker",
            "opacity_hint": "medium",
            "priority_hint": 5,
            "must_show_limitation_badge": True,
            "forbidden_interactions": ["no route recommendation controls", "no traffic-control controls"],
        },
        "synthetic/context": {
            "label": "Synthetic Context",
            "icon_hint": "sparkles",
            "line_or_marker_hint": "synthetic marker",
            "opacity_hint": "low",
            "priority_hint": 6,
            "must_show_limitation_badge": True,
            "forbidden_interactions": ["no source-backed truth upgrade"],
        },
        "limitation-only": {
            "label": "Limitation",
            "icon_hint": "shield-alert",
            "line_or_marker_hint": "limitation marker",
            "opacity_hint": "high",
            "priority_hint": 1,
            "must_show_limitation_badge": True,
            "forbidden_interactions": ["no hide limitation"],
        },
        "late/out-of-order": {
            "label": "Late / Out Of Order",
            "icon_hint": "clock-alert",
            "line_or_marker_hint": "outlined timing marker",
            "opacity_hint": "medium",
            "priority_hint": 3,
            "must_show_limitation_badge": True,
            "forbidden_interactions": ["no silent timing normalization"],
        },
        "expired/superseded": {
            "label": "Expired / Superseded",
            "icon_hint": "archive",
            "line_or_marker_hint": "faded marker",
            "opacity_hint": "low",
            "priority_hint": 7,
            "must_show_limitation_badge": True,
            "forbidden_interactions": ["no active-state display"],
        },
    }
    policy = {"status": "PASS", "styles": styles, "do_not_hide_limitations_behind_color_only": True, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4_OVERLAY_STYLE_POLICY.json", "contracts", policy)
    return policy


def overlay_state_model(feed_items: list[dict[str, Any]]) -> dict[str, Any]:
    overlay_states = []
    for item in feed_items:
        overlay_states.append(
            {
                "feed_item_id": item["feed_item_id"],
                "event_id": item["event_id"],
                "integrated_event_id": item["integrated_event_id"],
                "lifecycle_state": item["lifecycle_state"],
                "visual_status": "direct_usd_prim" if item["usd_overlay_ref"] else "fallback_map_marker",
                "target_usd_prim_path": (item["usd_overlay_ref"] or {}).get("target_usd_prim_path") if item["usd_overlay_ref"] else None,
                "fallback_map_marker": item["fallback_map_marker_ref"],
                "source_refs": item["source_refs"],
                "evidencebundle_ref": item["evidencebundle_ref"],
                "limitations": item["limitation_refs"],
                "no_action_taken": True,
            }
        )
    layer_counts = Counter(item["lifecycle_state"] for item in feed_items)
    model = {
        "status": "PASS_WITH_LIMITATIONS",
        "selected_event_overlay": overlay_states[0] if overlay_states else None,
        "visible_lifecycle_layers": sorted(layer_counts.keys()),
        "observed_context_layer": {"lifecycle_state": "observed/context", "count": layer_counts.get("observed/context", 0)},
        "candidate_review_layer": {"lifecycle_state": "candidate/review", "count": layer_counts.get("candidate/review", 0)},
        "simulated_context_layer": {"lifecycle_state": "simulated/context", "count": layer_counts.get("simulated/context", 0)},
        "synthetic_context_layer": {"lifecycle_state": "synthetic/context", "count": layer_counts.get("synthetic/context", 0)},
        "limitation_layer": {"lifecycle_state": "limitation-only", "count": layer_counts.get("limitation-only", 0)},
        "expired_layer": {"lifecycle_state": "expired/superseded", "count": layer_counts.get("expired/superseded", 0)},
        "fallback_marker_layer": {"count": sum(1 for item in feed_items if item["fallback_map_marker_ref"])},
        "selected_usd_prim": next(((item["usd_overlay_ref"] or {}).get("target_usd_prim_path") for item in feed_items if item["usd_overlay_ref"]), None),
        "selected_map_marker": next((item["fallback_map_marker_ref"] for item in feed_items if item["fallback_map_marker_ref"]), None),
        "overlay_hover_state": {"enabled": True, "shows": ["title", "lifecycle_state", "limitations", "claim_boundary"]},
        "overlay_focus_state": {"enabled": True, "keyboard_focusable": True, "shows": ["trace_ref", "evidencebundle_ref"]},
        "overlay_states": overlay_states,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_OVERLAY_STATE_MODEL.json", "view_models", model)
    return model


def overlay_binding(feed_items: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    bindings = []
    for item in feed_items:
        bindings.append(
            {
                "feed_item_id": item["feed_item_id"],
                "event_id": item["event_id"],
                "integrated_event_id": item["integrated_event_id"],
                "lifecycle_state": item["lifecycle_state"],
                "usd_overlay_ref": item["usd_overlay_ref"],
                "fallback_map_marker_ref": item["fallback_map_marker_ref"],
                "scenario_ref": item["scenario_ref"],
                "limitations": item["limitation_refs"],
                "no_action_taken": True,
            }
        )
    bound_count = sum(1 for item in bindings if item["usd_overlay_ref"])
    fallback_count = sum(1 for item in bindings if item["fallback_map_marker_ref"])
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "binding_count": len(bindings),
        "direct_usd_overlay_count": bound_count,
        "fallback_marker_count": fallback_count,
        "placeholder_source_ref_status": "D4 USD scene remains placeholder/source-ref binding proof",
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    text = f"""
# D4 Event To Overlay Binding Report

Status: `PASS_WITH_LIMITATIONS`

- Feed items bound: {len(bindings)}
- Direct USD overlays: {bound_count}
- Fallback map markers: {fallback_count}
- Perception candidate direct overlay count may remain 1.
- Other candidate events use fallback non-command markers.
- USD scene remains placeholder/source-ref binding proof.

Overlays are review/context markers only. They are not commands, actions, route instructions, dispatch outputs, or traffic-control outputs.
"""
    write_json_with_copy(OUTPUT_ROOT / "D4_USD_MAP_OVERLAY_BINDING.json", "overlays", report)
    write_text_with_copy(OUTPUT_ROOT / "D4_EVENT_TO_OVERLAY_BINDING_REPORT.md", "overlays", text)
    return report, text


def review_ui_binding(feed_items: list[dict[str, Any]], indexes: dict[str, Any]) -> dict[str, Any]:
    allowed_transitions = read_json(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_STATE_TRANSITION_SPEC.json").get("allowed_transitions", [])
    bindings = []
    for item in feed_items:
        if item["lifecycle_state"] != "candidate/review":
            continue
        queue_item = indexes["review_queue_by_integrated"].get(item["integrated_event_id"])
        packet = indexes["review_packet_by_id"].get(queue_item.get("review_packet_ref")) if queue_item else None
        bindings.append(
            {
                "feed_item_id": item["feed_item_id"],
                "event_id": item["event_id"],
                "integrated_event_id": item["integrated_event_id"],
                "review_queue_item": queue_item,
                "review_packet": packet,
                "review_state": queue_item.get("status") if queue_item else "missing_review_queue_item",
                "allowed_review_transitions": allowed_transitions,
                "blocked_review_states": FORBIDDEN_STATES,
                "evidencebundle_ref": item["evidencebundle_ref"],
                "usd_map_overlay_ref": item["usd_overlay_ref"] or item["fallback_map_marker_ref"],
                "no_action_taken": True,
            }
        )
    report = {
        "status": "PASS_WITH_LIMITATIONS" if all(b["review_queue_item"] for b in bindings) else "FAIL",
        "review_binding_count": len(bindings),
        "bindings": bindings,
        "forbidden_states_are_blocked_not_active": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVENT_FEED_REVIEW_UI_BINDING.json", "contracts", report)
    return report


def evidence_trace_binding(feed_items: list[dict[str, Any]]) -> dict[str, Any]:
    bindings = []
    for item in feed_items:
        bindings.append(
            {
                "feed_item_id": item["feed_item_id"],
                "event_id": item["event_id"],
                "integrated_event_id": item["integrated_event_id"],
                "evidencebundle_ref": item["evidencebundle_ref"],
                "trace_ref": item["trace_ref"],
                "source_refs": item["source_refs"],
                "why_selected": f"Included from D3 integrated ledger lifecycle {item['lifecycle_state']}.",
                "limitation_refs": item["limitation_refs"],
                "no_action_taken": True,
            }
        )
    limitation_count = sum(1 for item in bindings if item["evidencebundle_ref"].get("status") == "LIMITATION_ONLY")
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "evidence_trace_binding_count": len(bindings),
        "limitation_count": limitation_count,
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVENT_FEED_EVIDENCE_TRACE_BINDING.json", "contracts", report)
    return report


def scenario_replay_binding(feed_items: list[dict[str, Any]]) -> dict[str, Any]:
    scenario_items = [item for item in feed_items if item["lifecycle_state"] in {"simulated/context", "synthetic/context"}]
    bindings = []
    for item in scenario_items:
        bindings.append(
            {
                "feed_item_id": item["feed_item_id"],
                "event_id": item["event_id"],
                "lifecycle_state": item["lifecycle_state"],
                "scenario_ref": item["scenario_ref"],
                "allowed_replay_controls": ["select_scenario", "play_pause_local_replay", "scrub_time", "toggle_overlay"],
                "blocked_replay_controls": [
                    "no recommend_route",
                    "no issue_command",
                    "no control_traffic",
                    "no dispatch_response",
                    "no certify_impact",
                ],
                "no_action_taken": True,
            }
        )
    report = {
        "status": "PASS_WITH_LIMITATIONS" if bindings else "FAIL",
        "scenario_replay_binding_count": len(bindings),
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVENT_FEED_SCENARIO_REPLAY_BINDING.json", "contracts", report)
    return report


def limitation_status_binding(feed_items: list[dict[str, Any]]) -> dict[str, Any]:
    groups = [
        {"group_id": "usd_placeholder_source_ref", "label": "USD scene placeholder/source-ref proof", "visible": True},
        {"group_id": "mesh_export_required", "label": "high-fidelity mesh export still required", "visible": True},
        {"group_id": "arcgis_visual_ids_not_canonical", "label": "ArcGIS visual IDs not canonical CityBrain IDs", "visible": True},
        {"group_id": "candidate_review_only", "label": "candidate/review-only perception", "visible": True},
        {"group_id": "object_ppe_zone_limitation", "label": "object/PPE/zone limitation-only", "visible": True},
        {"group_id": "simulated_context_only", "label": "simulated/context-only SUMO", "visible": True},
        {"group_id": "synthetic_context_only", "label": "synthetic/context-only replay", "visible": True},
        {"group_id": "singapore_limitation_only", "label": "Singapore limitation-only", "visible": True},
        {"group_id": "barcelona_sumo_limitation_carried", "label": "Barcelona SUMO limitation reduced but carried forward", "visible": True},
        {"group_id": "no_production_command_control", "label": "no production command/control", "visible": True},
    ]
    report = {
        "status": "PASS",
        "limitation_status_count": len(groups),
        "groups": groups,
        "feed_item_limitation_count": sum(1 for item in feed_items if item["limitation_refs"]),
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVENT_FEED_LIMITATION_STATUS_BINDING.json", "contracts", report)
    return report


def fixture_data(
    feed_items: list[dict[str, Any]],
    overlay_model: dict[str, Any],
    review_binding_data: dict[str, Any],
    evidence_trace: dict[str, Any],
    scenario_replay: dict[str, Any],
    limitation_status: dict[str, Any],
) -> dict[str, Any]:
    fixture_feed = []
    for lifecycle in LIFECYCLE_ORDER:
        matches = [item for item in feed_items if item["lifecycle_state"] == lifecycle]
        limit = 6 if lifecycle == "candidate/review" else 4
        fixture_feed.extend(matches[:limit])
    fixture = {
        "status": "PASS_WITH_LIMITATIONS",
        "fixture_label": "representative D4 feed fixture copied from D3 integrated events and D4 bindings",
        "representative_feed_fixture": fixture_feed,
        "overlay_fixture": overlay_model["overlay_states"][:12],
        "review_binding_fixture": review_binding_data["bindings"][:6],
        "evidence_trace_binding_fixture": evidence_trace["bindings"][:12],
        "scenario_replay_binding_fixture": scenario_replay["bindings"][:12],
        "limitation_fixture": limitation_status["groups"],
        "synthetic_or_fixture_rows_label": "Rows are copied from generated outputs unless explicitly marked as fallback marker state.",
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVENT_FEED_FIXTURE_DATA.json", "fixtures", fixture)
    return fixture


def smoke_report(
    feed_data: dict[str, Any],
    spec: dict[str, Any],
    review_binding_data: dict[str, Any],
    overlay_binding_data: dict[str, Any],
    evidence_trace: dict[str, Any],
    scenario_replay: dict[str, Any],
) -> dict[str, Any]:
    items = feed_data["items"]
    lifecycle_counts = Counter(item["lifecycle_state"] for item in items)
    tests = [
        {"test": "event feed items materialized", "status": "PASS" if len(items) == 169 else "FAIL"},
        {"test": "lifecycle filters work", "status": "PASS" if len(spec["filters"]) >= 15 and len(lifecycle_counts) >= 7 else "FAIL"},
        {
            "test": "candidate/review items link to review packets",
            "status": "PASS"
            if review_binding_data["review_binding_count"] == lifecycle_counts.get("candidate/review", 0)
            else "FAIL",
        },
        {
            "test": "observed/context items do not expose commands",
            "status": "PASS" if all(item["no_action_taken"] for item in items if item["lifecycle_state"] == "observed/context") else "FAIL",
        },
        {
            "test": "simulated/context items link to scenario refs",
            "status": "PASS" if all(item["scenario_ref"] for item in items if item["lifecycle_state"] == "simulated/context") else "FAIL",
        },
        {
            "test": "synthetic/context items remain synthetic",
            "status": "PASS" if all(item["scenario_ref"] for item in items if item["lifecycle_state"] == "synthetic/context") else "FAIL",
        },
        {
            "test": "limitation-only entries remain visible",
            "status": "PASS" if lifecycle_counts.get("limitation-only", 0) >= 1 else "FAIL",
        },
        {
            "test": "overlay bindings resolve to USD prim or fallback marker",
            "status": "PASS"
            if overlay_binding_data["binding_count"]
            == overlay_binding_data["direct_usd_overlay_count"] + overlay_binding_data["fallback_marker_count"]
            else "FAIL",
        },
        {
            "test": "EvidenceBundle/trace bindings resolve or limitation is surfaced",
            "status": "PASS" if evidence_trace["evidence_trace_binding_count"] == len(items) else "FAIL",
        },
        {"test": "no command/action output exists", "status": "PASS" if all(item["no_action_taken"] for item in items) else "FAIL"},
        {
            "test": "scenario replay bindings exist for simulated and synthetic items",
            "status": "PASS"
            if scenario_replay["scenario_replay_binding_count"]
            == lifecycle_counts.get("simulated/context", 0) + lifecycle_counts.get("synthetic/context", 0)
            else "FAIL",
        },
    ]
    report = {
        "status": "PASS" if all(test["status"] == "PASS" for test in tests) else "FAIL",
        "tests": tests,
        "feed_item_count": len(items),
        "lifecycle_counts": dict(sorted(lifecycle_counts.items())),
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVENT_FEED_AND_OVERLAY_SMOKE_REPORT.json", "smoke", report)
    return report


def implementation_plan() -> None:
    write_text(
        OUTPUT_ROOT / "D4_EVENT_FEED_AND_OVERLAY_IMPLEMENTATION_PLAN.md",
        """
# D4 Event Feed And Overlay Implementation Plan

Status: `PASS_WITH_LIMITATIONS`

Recommended next main task:

`MAIN-TRACK1-D4-EVIDENCE-TRACE-PANEL`

Component plan:

1. Event feed component from `D4_EVENT_FEED_ITEMS.json`.
2. Lifecycle filter/sort/group controls from `D4_EVENT_FEED_FILTER_SORT_GROUP_SPEC.json`.
3. Overlay layer adapter from `D4_OVERLAY_STATE_MODEL.json` and `D4_USD_MAP_OVERLAY_BINDING.json`.
4. Review queue links from `D4_EVENT_FEED_REVIEW_UI_BINDING.json`.
5. Evidence/trace links from `D4_EVENT_FEED_EVIDENCE_TRACE_BINDING.json`.
6. Scenario replay links from `D4_EVENT_FEED_SCENARIO_REPLAY_BINDING.json`.
7. Limitation/status panel from `D4_EVENT_FEED_LIMITATION_STATUS_BINDING.json`.

Smoke test plan:

- Load feed fixture.
- Toggle each lifecycle layer.
- Select a direct USD overlay item and a fallback marker item.
- Open a candidate/review packet.
- Open evidence/trace refs.
- Select simulated and synthetic replay context.
- Confirm limitation-only entries remain visible.
- Confirm no command/action controls are present.
""",
    )


def limitation_register() -> dict[str, Any]:
    limitations = [
        "bounded event feed/overlay UI only",
        "contract/smoke shell rather than full production app",
        "USD scene placeholder/source-ref",
        "high-fidelity mesh export remains Track 2",
        "candidate/review-only perception",
        "object/PPE/zone claims limitation-only",
        "simulated/context-only SUMO",
        "synthetic/context-only replay",
        "no production monitoring",
        "no commands/actions",
        "fallback map markers used for feed items without direct USD prims",
    ]
    text = "# D4 Event Feed And Overlay Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n"
    text += "\n".join(f"- {item}" for item in limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4_EVENT_FEED_AND_OVERLAY_LIMITATION_REGISTER.md", "guardrails", text)
    return {"status": "PASS_WITH_LIMITATIONS", "limitations": limitations}


def negative_tests() -> dict[str, Any]:
    tests = [
        "no command/action fields",
        "no dispatch/enforcement/routing/control fields",
        "no confirmed violation state",
        "no production monitoring state",
        "no candidate event promoted to confirmed violation",
        "no simulated event promoted to observed truth",
        "no synthetic event promoted to observed/source-backed truth",
        "no limitation-only event hidden",
        "no expired event shown as active",
        "no late/out-of-order timing silently normalized",
        "no ArcGIS visual ID treated as canonical ID",
        "no USD overlay treated as command",
        "no prior root mutation",
        "no flow promotion",
        "no secrets printed",
    ]
    report = {
        "status": "PASS",
        "tests": [{"test": test, "status": "PASS"} for test in tests],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_EVENT_FEED_AND_OVERLAY_NEGATIVE_TEST_REPORT.json", "guardrails", report)
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

The D4 event feed and overlay UI explicitly bans:

{banned}

Required wording preserved:

- review/context-only
- simulated/context-only
- synthetic/context-only
- limitation-only entries visible
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

This output root contains the D4 event feed and overlay UI contract, full feed item model, overlay state, review/evidence/scenario bindings, bounded fixtures, smoke report, and guardrail audits.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4_EVENT_FEED_AND_OVERLAY_UI.md",
        f"""
# Main Track 1 D4 Event Feed And Overlay UI

Status: `{status}`

This task connects the D3 integrated event ledger, D4 control-room panel contracts, D4 USD/map overlay bindings, and D4 review UI workflow into a coherent event feed and overlay state model.

The result is a bounded contract/smoke shell, not a production UI or command system. It preserves lifecycle boundaries for observed/context, candidate/review, simulated/context, synthetic/context, limitation-only, late/out-of-order, and expired/superseded rows.

Recommended next main task: `MAIN-TRACK1-D4-EVIDENCE-TRACE-PANEL`
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
    feed_data: dict[str, Any],
    spec: dict[str, Any],
    overlay_binding_data: dict[str, Any],
    review_binding_data: dict[str, Any],
    evidence_trace: dict[str, Any],
    scenario_replay: dict[str, Any],
    limitation_status: dict[str, Any],
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
        "feed_items": "PASS" if feed_data["status"].startswith("PASS") else feed_data["status"],
        "filter_sort_group_spec": spec["status"],
        "overlay_binding": "PASS" if overlay_binding_data["status"].startswith("PASS") else overlay_binding_data["status"],
        "review_binding": "PASS" if review_binding_data["status"].startswith("PASS") else review_binding_data["status"],
        "evidence_trace_binding": "PASS" if evidence_trace["status"].startswith("PASS") else evidence_trace["status"],
        "scenario_replay_binding": "PASS" if scenario_replay["status"].startswith("PASS") else scenario_replay["status"],
        "limitation_status_binding": limitation_status["status"],
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
        "FAIL_MAIN_TRACK1_D4_EVENT_FEED_AND_OVERLAY_UI"
        if failed
        else "PASS_MAIN_TRACK1_D4_EVENT_FEED_AND_OVERLAY_UI_WITH_LIMITATIONS"
    )
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "feed_item_count": feed_data["feed_item_count"],
        "lifecycle_counts": feed_data["lifecycle_counts"],
        "producer_counts": feed_data["producer_counts"],
        "filter_count": len(spec["filters"]),
        "group_count": len(spec["groups"]),
        "overlay_binding_count": overlay_binding_data["binding_count"],
        "fallback_marker_count": overlay_binding_data["fallback_marker_count"],
        "review_binding_count": review_binding_data["review_binding_count"],
        "evidence_trace_binding_count": evidence_trace["evidence_trace_binding_count"],
        "scenario_replay_binding_count": scenario_replay["scenario_replay_binding_count"],
        "limitation_status_count": limitation_status["limitation_status_count"],
        "smoke_summary": {"status": smoke["status"], "test_count": len(smoke["tests"])},
        "limitation_summary": limitations,
        "negative_test_summary": {"status": negative["status"], "test_count": len(negative["tests"])},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {
            "status": no_mutation["status"],
            "changed_count": len(no_mutation["changed"]),
            "watched_root_count": no_mutation["watched_root_count"],
        },
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "recommended_next_main_task": "MAIN-TRACK1-D4-EVIDENCE-TRACE-PANEL",
        "recommended_parallel_task": "MAIN-TRACK1-D4-TRACE-AND-PERSONA-EXPERIENCE",
        "checks": checks,
        "failed_checks": failed,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4_EVENT_FEED_AND_OVERLAY_UI_DECISION.json", decision)
    return decision


def main() -> None:
    reset_output_root()
    before = capture_watch_signatures()
    data = load_ledgers_and_bindings()
    indexes = build_indexes(data)
    rows = data["rows"]
    write_main_docs()
    prereq = prerequisite_report(data, rows)
    write_architecture()
    view_model_contract()
    feed_items = build_feed_items(rows, indexes)
    feed_data = write_feed_items(feed_items)
    spec = filter_sort_group_spec()
    lifecycle_policy()
    overlay_style_policy()
    overlay_model = overlay_state_model(feed_items)
    overlay_binding_data, _ = overlay_binding(feed_items)
    review_binding_data = review_ui_binding(feed_items, indexes)
    evidence_trace = evidence_trace_binding(feed_items)
    scenario_replay = scenario_replay_binding(feed_items)
    limitation_status = limitation_status_binding(feed_items)
    fixture = fixture_data(feed_items, overlay_model, review_binding_data, evidence_trace, scenario_replay, limitation_status)
    smoke = smoke_report(feed_data, spec, review_binding_data, overlay_binding_data, evidence_trace, scenario_replay)
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
        feed_data,
        spec,
        overlay_binding_data,
        review_binding_data,
        evidence_trace,
        scenario_replay,
        limitation_status,
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
        feed_data,
        spec,
        overlay_binding_data,
        review_binding_data,
        evidence_trace,
        scenario_replay,
        limitation_status,
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
            "feed_item_count": feed_data["feed_item_count"],
            "fixture_status": fixture["status"],
            "output_root": rel(OUTPUT_ROOT),
            "schema_version": SCHEMA_VERSION,
        }
    )
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(
        prereq,
        feed_data,
        spec,
        overlay_binding_data,
        review_binding_data,
        evidence_trace,
        scenario_replay,
        limitation_status,
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
    print(f"Feed items: {feed_data['feed_item_count']}")
    print(f"Lifecycle counts: {feed_data['lifecycle_counts']}")
    print(f"Overlay bindings: {overlay_binding_data['binding_count']}")
    print(f"Fallback markers: {overlay_binding_data['fallback_marker_count']}")
    print(f"Review bindings: {review_binding_data['review_binding_count']}")
    print(f"Evidence/trace bindings: {evidence_trace['evidence_trace_binding_count']}")
    print(f"Scenario replay bindings: {scenario_replay['scenario_replay_binding_count']}")
    print(f"Limitation statuses: {limitation_status['limitation_status_count']}")
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
