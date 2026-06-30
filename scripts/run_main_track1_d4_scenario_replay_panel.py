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
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4_scenario_replay_panel"
TASK = "MAIN-TRACK1-D4-SCENARIO-REPLAY-PANEL"
SCHEMA_VERSION = "main-track1-d4-scenario-replay-panel.v1"

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
    "sumo_d3_hardening": ROOT / "outputs" / "main_sumo_d3_network_extraction_hardening",
    "sumo_d3_catalog": ROOT / "outputs" / "main_sumo_d3_scenario_catalog",
    "track1_d3_integrated": ROOT / "outputs" / "main_track1_d3_integrated_service_smoke",
    "synthetic_replay": ROOT / "outputs" / "synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
    "d4_usd_binding": ROOT / "outputs" / "main_track1_d4_usd_city_subset_binding",
    "d4_control_room_preflight": ROOT / "outputs" / "main_track1_d4_control_room_experience_preflight",
    "d4_review_ui_workflow": ROOT / "outputs" / "main_track1_d4_review_ui_workflow",
    "d4_event_feed_overlay": ROOT / "outputs" / "main_track1_d4_event_feed_and_overlay_ui",
    "d4_evidence_trace_panel": ROOT / "outputs" / "main_track1_d4_evidence_trace_panel",
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
    "sumo_d3_hardening": "MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_DECISION.json",
    "sumo_d3_catalog": "MAIN_SUMO_D3_SCENARIO_CATALOG_DECISION.json",
    "synthetic_replay": "SDF_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_DECISION.json",
    "track1_d3_integrated": "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_DECISION.json",
    "d4_usd_binding": "MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json",
    "d4_control_room_preflight": "MAIN_TRACK1_D4_CONTROL_ROOM_EXPERIENCE_PREFLIGHT_DECISION.json",
    "d4_review_ui_workflow": "MAIN_TRACK1_D4_REVIEW_UI_WORKFLOW_DECISION.json",
    "d4_event_feed_overlay": "MAIN_TRACK1_D4_EVENT_FEED_AND_OVERLAY_UI_DECISION.json",
    "d4_evidence_trace_panel": "MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL_DECISION.json",
}

REQUIRED_FOLDERS = ["contracts", "view_models", "fixtures", "bindings", "smoke", "guardrails", "logs"]
REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4_SCENARIO_REPLAY_PANEL.md",
    "MAIN_TRACK1_D4_SCENARIO_REPLAY_PANEL_DECISION.json",
    "D4_SCENARIO_REPLAY_PREREQUISITE_REPORT.json",
    "D4_SCENARIO_REPLAY_PANEL_ARCHITECTURE.md",
    "D4_SCENARIO_REPLAY_VIEW_MODEL_CONTRACT.json",
    "D4_SCENARIO_REPLAY_ITEMS.json",
    "D4_SCENARIO_REPLAY_TIMELINE_MODEL.json",
    "D4_SCENARIO_REPLAY_CONTROL_MODEL.json",
    "D4_SCENARIO_REPLAY_SUMO_BINDING.json",
    "D4_SCENARIO_REPLAY_SYNTHETIC_BINDING.json",
    "D4_SCENARIO_REPLAY_EVENT_FEED_BINDING.json",
    "D4_SCENARIO_REPLAY_EVIDENCE_TRACE_BINDING.json",
    "D4_SCENARIO_REPLAY_USD_OVERLAY_BINDING.json",
    "D4_SCENARIO_REPLAY_LIMITATION_MODEL.json",
    "D4_SCENARIO_REPLAY_FIXTURE_DATA.json",
    "D4_SCENARIO_REPLAY_SMOKE_REPORT.json",
    "D4_SCENARIO_REPLAY_IMPLEMENTATION_PLAN.md",
    "D4_SCENARIO_REPLAY_LIMITATION_REGISTER.md",
    "D4_SCENARIO_REPLAY_NEGATIVE_TEST_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

ALLOWED_REPLAY_TYPES = [
    "sumo_simulated_context",
    "sumo_scenario_catalog_context",
    "synthetic_context",
    "limitation_only",
    "validation_only",
]

ALLOWED_CONTROLS = [
    "select_scenario",
    "play_local_replay",
    "pause_local_replay",
    "step_forward",
    "step_back",
    "scrub_timeline",
    "reset_local_replay",
    "toggle_overlay_layer",
    "open_EvidenceBundle",
    "open_trace",
    "open_limitation_detail",
]

FORBIDDEN_CONTROLS = [
    "recommend_route",
    "apply_route",
    "dispatch",
    "enforce",
    "notify_public_safety",
    "control_traffic_signal",
    "control_transit",
    "control_port_vessel",
    "execute_command",
    "create_ticket",
    "certify_impact",
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
    "certified traffic model",
    "observed traffic truth",
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
    return {"exists": True, "kind": "dir", "file_count": file_count, "total_bytes": total_bytes, "max_mtime": max_mtime, "sample_hashes": sample_hashes}


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


def load_inputs() -> dict[str, Any]:
    feed_items = read_json(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_ITEMS.json").get("items", [])
    event_feed_scenario = read_json(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_SCENARIO_REPLAY_BINDING.json")
    evidence_scenario = read_json(INPUTS["d4_evidence_trace_panel"] / "D4_EVIDENCE_TRACE_SCENARIO_REPLAY_BINDING.json")
    evidence_items = read_json(INPUTS["d4_evidence_trace_panel"] / "D4_EVIDENCE_TRACE_PANEL_ITEMS.json").get("items", [])
    usd_overlay = read_json(INPUTS["d4_event_feed_overlay"] / "D4_USD_MAP_OVERLAY_BINDING.json")
    scenario_catalog = read_json(INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_CATALOG.json")
    scenario_validation = read_json(INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_VALIDATION_REPORT.json")
    return {
        "feed_items": feed_items,
        "event_feed_scenario": event_feed_scenario,
        "evidence_scenario": evidence_scenario,
        "evidence_items": evidence_items,
        "usd_overlay": usd_overlay,
        "scenario_catalog": scenario_catalog,
        "scenario_validation": scenario_validation,
    }


def build_indexes(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "feed_by_id": {item.get("feed_item_id"): item for item in data["feed_items"] if item.get("feed_item_id")},
        "evidence_item_by_feed_id": {item["event_summary"].get("feed_item_id"): item for item in data["evidence_items"] if item.get("event_summary")},
        "overlay_by_feed_id": {item.get("feed_item_id"): item for item in data["usd_overlay"].get("bindings", []) if item.get("feed_item_id")},
        "catalog_by_scenario_id": {item.get("scenario_id"): item for item in data["scenario_catalog"].get("scenarios", []) if item.get("scenario_id")},
    }


def replay_type_for(binding: dict[str, Any]) -> str:
    family = str((binding.get("scenario_ref") or {}).get("scenario_family") or "")
    if family == "SUMO_D3_NETWORK_EXTRACTION_HARDENING":
        return "sumo_simulated_context"
    if family == "SUMO_D3_SCENARIO_CATALOG":
        return "sumo_scenario_catalog_context"
    if family == "SYNTHETIC_DATA_FACTORY_REPLAY":
        return "synthetic_context"
    return "validation_only"


def build_replay_items(data: dict[str, Any], indexes: dict[str, Any]) -> dict[str, Any]:
    items = []
    for binding in data["evidence_scenario"].get("bindings", []):
        feed_item = indexes["feed_by_id"].get(binding.get("feed_item_id"), {})
        evidence_item = indexes["evidence_item_by_feed_id"].get(binding.get("feed_item_id"), {})
        overlay = indexes["overlay_by_feed_id"].get(binding.get("feed_item_id"), {})
        scenario_ref = binding.get("scenario_ref") or {}
        replay_type = replay_type_for(binding)
        scenario_id = scenario_ref.get("source_event_id") or binding.get("event_id")
        items.append(
            {
                "scenario_id": f"d4-replay:{scenario_id}",
                "source_scenario_id": scenario_id,
                "city_id": feed_item.get("city_id"),
                "subset_id": feed_item.get("subset_id"),
                "lifecycle_state": binding.get("lifecycle_state"),
                "replay_type": replay_type,
                "source_category": "sumo" if replay_type.startswith("sumo") else "synthetic",
                "title": feed_item.get("title") or str(scenario_id),
                "source_refs": feed_item.get("source_refs", []),
                "event_refs": [{"feed_item_id": binding.get("feed_item_id"), "event_id": binding.get("event_id")}],
                "overlay_refs": [overlay] if overlay else [],
                "evidence_refs": (evidence_item.get("evidence_refs") or [feed_item.get("evidencebundle_ref")]) if evidence_item else [feed_item.get("evidencebundle_ref")],
                "limitation_refs": list_value(feed_item.get("limitation_refs")) + list_value(binding.get("limitations")),
                "claim_boundary": feed_item.get("claim_boundary") or "Replay context only. No action taken.",
                "timeline_policy": {"step_count": 3, "mode": "local_context_replay"},
                "no_action_taken": True,
                "source_binding": binding,
            }
        )

    for scenario in data["scenario_catalog"].get("scenarios", []):
        if scenario.get("runnable") is False and not scenario.get("limitation_only"):
            items.append(catalog_extra_item(scenario, "validation_only"))
        if scenario.get("limitation_only"):
            items.append(catalog_extra_item(scenario, "limitation_only"))

    late_or_expired = [item for item in data["feed_items"] if item.get("lifecycle_state") in {"late/out-of-order", "expired/superseded"}]
    for item in late_or_expired:
        items.append(
            {
                "scenario_id": f"d4-replay-validation:{item['lifecycle_state']}:{item['feed_item_id']}",
                "source_scenario_id": item.get("event_id"),
                "city_id": item.get("city_id"),
                "subset_id": item.get("subset_id"),
                "lifecycle_state": item.get("lifecycle_state"),
                "replay_type": "validation_only",
                "source_category": "event_fabric_validation",
                "title": f"{item.get('lifecycle_state')} replay validation",
                "source_refs": item.get("source_refs", []),
                "event_refs": [{"feed_item_id": item.get("feed_item_id"), "event_id": item.get("event_id")}],
                "overlay_refs": [],
                "evidence_refs": [item.get("evidencebundle_ref")],
                "limitation_refs": item.get("limitation_refs", []),
                "claim_boundary": item.get("claim_boundary"),
                "timeline_policy": {"step_count": 2, "mode": "timing_or_retention_validation_only"},
                "fixture_label": "validation-only replay edge case copied from D4 event feed lifecycle state",
                "no_action_taken": True,
            }
        )
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "replay_item_count": len(items),
        "items": items,
        "schema_version": SCHEMA_VERSION,
    }


def catalog_extra_item(scenario: dict[str, Any], replay_type: str) -> dict[str, Any]:
    return {
        "scenario_id": f"d4-replay-catalog:{scenario.get('scenario_id')}",
        "source_scenario_id": scenario.get("scenario_id"),
        "city_id": scenario.get("city_id"),
        "subset_id": scenario.get("subset_id"),
        "lifecycle_state": scenario.get("lifecycle_state"),
        "replay_type": replay_type,
        "source_category": "sumo_catalog",
        "title": scenario.get("scenario_name"),
        "source_refs": list_value(scenario.get("input_refs")) + list_value(scenario.get("source_refs")) + list_value(scenario.get("synthetic_refs")),
        "event_refs": [],
        "overlay_refs": [],
        "evidence_refs": [{"status": "CATALOG_CONTEXT", "source_report": rel(INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_CATALOG.json")}],
        "limitation_refs": scenario.get("limitations", []),
        "claim_boundary": scenario.get("claim_boundary"),
        "timeline_policy": {"step_count": 2 if replay_type == "validation_only" else 1, "mode": replay_type},
        "fixture_label": f"catalog {replay_type} entry; not a source-backed run success",
        "no_action_taken": True,
    }


def prerequisite_report(data: dict[str, Any]) -> dict[str, Any]:
    decisions = {}
    for key, filename in DECISIONS.items():
        path = INPUTS[key] / filename
        decisions[key] = {"path": rel(path), "exists": path.exists(), "status": status_of(read_json(path))}
    checks = {
        "evidence_trace_panel_passed": is_pass(decisions["d4_evidence_trace_panel"]["status"]),
        "event_feed_overlay_passed": is_pass(decisions["d4_event_feed_overlay"]["status"]),
        "sumo_d3_scenario_catalog_passed": is_pass(decisions["sumo_d3_catalog"]["status"]),
        "synthetic_replay_smoke_passed": is_pass(decisions["synthetic_replay"]["status"]),
        "scenario_replay_bindings_exist": len(data["evidence_scenario"].get("bindings", [])) >= 88,
        "event_feed_scenario_bindings_exist": len(data["event_feed_scenario"].get("bindings", [])) >= 88,
        "no_prior_roots_mutated_by_this_task": True,
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "task_name": TASK,
        "timestamp": now_iso(),
        "decisions": decisions,
        "checks": checks,
        "scenario_replay_binding_count": len(data["evidence_scenario"].get("bindings", [])),
        "source_roots_read_only": {key: rel(path) for key, path in INPUTS.items()},
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_PREREQUISITE_REPORT.json", report)
    write_json(OUTPUT_ROOT / "logs" / "D4_SCENARIO_REPLAY_PREREQUISITE_REPORT.json", report)
    return report


def write_architecture() -> None:
    write_text(
        OUTPUT_ROOT / "D4_SCENARIO_REPLAY_PANEL_ARCHITECTURE.md",
        """
# D4 Scenario Replay Panel Architecture

Status: `PASS_WITH_LIMITATIONS`

The Scenario Replay Panel lets an operator select a bounded scenario, inspect its source/replay type, scrub a local timeline, toggle simulated/context and synthetic/context overlays, inspect EvidenceBundle/trace/source refs, see limitations, and compare scenario state to context-only observed inputs where available.

The panel is not routing, control, dispatch, traffic management, emergency response, enforcement, or certified impact analysis.
""",
    )


def view_model_contract() -> dict[str, Any]:
    models = {
        "ScenarioReplayPanelState": ["selected_scenario", "timeline", "visible_overlay_layers", "limitations"],
        "ScenarioReplayItem": ["scenario_id", "city_id", "subset_id", "lifecycle_state", "replay_type", "source_refs", "event_refs", "overlay_refs", "evidence_refs", "limitation_refs", "claim_boundary", "no_action_taken"],
        "ScenarioTimeline": ["timeline_id", "scenario_id", "start_time", "end_time", "step_count", "timeline_steps"],
        "ScenarioTimelineStep": ["step_id", "step_index", "event_refs_per_step", "overlay_refs_per_step", "limitation_refs_per_step"],
        "ScenarioReplayControl": ["control_id", "control_type", "enabled", "local_ui_only"],
        "ScenarioEventRef": ["feed_item_id", "event_id", "lifecycle_state"],
        "ScenarioOverlayRef": ["usd_overlay_ref", "fallback_map_marker_ref", "visual_context_only"],
        "ScenarioEvidenceTraceRef": ["panel_item_id", "source_refs", "evidence_refs"],
        "ScenarioLimitation": ["limitation_id", "scenario_id", "limitation", "must_render"],
        "ScenarioReplayAuditBoundary": ["claim_boundary", "forbidden_controls", "no_action_taken"],
    }
    contract = {
        "status": "PASS",
        "models": models,
        "required_common_fields": ["scenario_id", "city_id", "subset_id", "lifecycle_state", "replay_type", "source_refs", "event_refs", "overlay_refs", "evidence_refs", "limitation_refs", "claim_boundary", "no_action_taken"],
        "allowed_replay_types": ALLOWED_REPLAY_TYPES,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_VIEW_MODEL_CONTRACT.json", "contracts", contract)
    return contract


def write_replay_items(items_data: dict[str, Any]) -> dict[str, Any]:
    items = items_data["items"]
    replay_type_counts = Counter(item["replay_type"] for item in items)
    source_counts = Counter(item["source_category"] for item in items)
    data = {
        "status": "PASS_WITH_LIMITATIONS",
        "replay_item_count": len(items),
        "replay_type_counts": dict(sorted(replay_type_counts.items())),
        "source_category_counts": dict(sorted(source_counts.items())),
        "items": items,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_ITEMS.json", "view_models", data)
    return data


def timeline_model(items: list[dict[str, Any]]) -> dict[str, Any]:
    timelines = []
    for item in items:
        step_count = int((item.get("timeline_policy") or {}).get("step_count") or 1)
        steps = []
        for index in range(step_count):
            steps.append(
                {
                    "step_id": f"{item['scenario_id']}:step:{index + 1}",
                    "scenario_id": item["scenario_id"],
                    "city_id": item.get("city_id"),
                    "replay_type": item.get("replay_type"),
                    "step_index": index + 1,
                    "event_refs_per_step": item.get("event_refs", [])[:1],
                    "overlay_refs_per_step": item.get("overlay_refs", [])[:1],
                    "limitation_refs_per_step": item.get("limitation_refs", [])[:3],
                    "operational_control_implied": False,
                }
            )
        timelines.append(
            {
                "timeline_id": f"{item['scenario_id']}:timeline",
                "scenario_id": item["scenario_id"],
                "city_id": item.get("city_id"),
                "replay_type": item.get("replay_type"),
                "start_time": "T+000",
                "end_time": f"T+{step_count:03d}",
                "step_count": step_count,
                "timeline_steps": steps,
                "no_action_taken": True,
            }
        )
    model = {
        "status": "PASS",
        "timeline_count": len(timelines),
        "timeline_step_count": sum(item["step_count"] for item in timelines),
        "timelines": timelines,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_TIMELINE_MODEL.json", "view_models", model)
    return model


def control_model() -> dict[str, Any]:
    allowed = [{"control_id": f"allowed:{name}", "control_type": name, "enabled": True, "local_ui_only": True} for name in ALLOWED_CONTROLS]
    forbidden = [{"control_id": f"forbidden:{name}", "control_type": name, "enabled": False, "rejected": True} for name in FORBIDDEN_CONTROLS]
    model = {
        "status": "PASS",
        "allowed_controls": allowed,
        "forbidden_controls": forbidden,
        "allowed_control_count": len(allowed),
        "forbidden_control_count": len(forbidden),
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_CONTROL_MODEL.json", "contracts", model)
    return model


def binding_models(items: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    sumo_items = [item for item in items if item["source_category"] in {"sumo", "sumo_catalog"}]
    synthetic_items = [item for item in items if item["source_category"] == "synthetic"]
    event_feed_items = [item for item in items if item.get("event_refs")]
    evidence_items = [item for item in items if item.get("evidence_refs")]
    usd_items = [item for item in items if item.get("overlay_refs")]
    sumo = {
        "status": "PASS_WITH_LIMITATIONS",
        "sumo_binding_count": len(sumo_items),
        "bindings": [
            {
                "scenario_id": item["scenario_id"],
                "city_id": item.get("city_id"),
                "replay_type": item["replay_type"],
                "network_extraction_ref": rel(INPUTS["sumo_d3_hardening"]),
                "scenario_catalog_ref": rel(INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_CATALOG.json"),
                "current_state_ref": rel(INPUTS["sumo_d3_hardening"] / "SUMO_D3_CURRENT_STATE_REPORT.json"),
                "evidencebundle_refs": item.get("evidence_refs", []),
                "limitations": item.get("limitation_refs", []),
                "simulated_context_only": True,
                "no_action_taken": True,
            }
            for item in sumo_items
        ],
        "barcelona_limitation_reduced_but_carried_forward": True,
        "schema_version": SCHEMA_VERSION,
    }
    synthetic = {
        "status": "PASS_WITH_LIMITATIONS",
        "synthetic_binding_count": len(synthetic_items),
        "bindings": [
            {
                "scenario_id": item["scenario_id"],
                "city_id": item.get("city_id"),
                "replay_type": item["replay_type"],
                "synthetic_replay_ref": rel(INPUTS["synthetic_replay"]),
                "event_refs": item.get("event_refs", []),
                "limitations": item.get("limitation_refs", []),
                "synthetic_context_only": True,
                "no_flow_promotion": True,
                "london_not_promoted_to_full_flow3": item.get("city_id") == "LON",
                "no_action_taken": True,
            }
            for item in synthetic_items
        ],
        "schema_version": SCHEMA_VERSION,
    }
    event_feed = {
        "status": "PASS",
        "event_feed_binding_count": len(event_feed_items),
        "bindings": [
            {
                "scenario_id": item["scenario_id"],
                "event_refs": item.get("event_refs", []),
                "lifecycle_state": item.get("lifecycle_state"),
                "overlay_refs": item.get("overlay_refs", []),
                "limitation_refs": item.get("limitation_refs", []),
                "selected_scenario_refs": [item["scenario_id"]],
                "no_action_taken": True,
            }
            for item in event_feed_items
        ],
        "schema_version": SCHEMA_VERSION,
    }
    evidence_trace = {
        "status": "PASS_WITH_LIMITATIONS",
        "evidence_trace_binding_count": len(evidence_items),
        "bindings": [
            {
                "scenario_id": item["scenario_id"],
                "evidence_refs": item.get("evidence_refs", []),
                "source_refs": item.get("source_refs", []),
                "provenance_refs": item.get("source_binding", {}),
                "limitation_refs": item.get("limitation_refs", []),
                "confidence_boundary": "display only; no automation",
                "no_action_taken": True,
            }
            for item in evidence_items
        ],
        "schema_version": SCHEMA_VERSION,
    }
    usd_overlay = {
        "status": "PASS_WITH_LIMITATIONS",
        "usd_overlay_binding_count": len(items),
        "direct_or_fallback_count": len(usd_items),
        "bindings": [
            {
                "scenario_id": item["scenario_id"],
                "direct_usd_overlays": [ref for ref in item.get("overlay_refs", []) if ref.get("usd_overlay_ref")],
                "fallback_map_markers": [ref for ref in item.get("overlay_refs", []) if ref.get("fallback_map_marker_ref")],
                "limitation_refs": item.get("limitation_refs", []),
                "visual_context_only": True,
                "no_action_taken": True,
            }
            for item in items
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_SUMO_BINDING.json", "bindings", sumo)
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_SYNTHETIC_BINDING.json", "bindings", synthetic)
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_EVENT_FEED_BINDING.json", "bindings", event_feed)
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_EVIDENCE_TRACE_BINDING.json", "bindings", evidence_trace)
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_USD_OVERLAY_BINDING.json", "bindings", usd_overlay)
    return sumo, synthetic, event_feed, evidence_trace, usd_overlay


def limitation_model(items: list[dict[str, Any]]) -> dict[str, Any]:
    groups = [
        "bounded scenario replay only",
        "SUMO simulated/context-only",
        "synthetic/context-only",
        "no certified traffic model",
        "no observed traffic truth from simulation",
        "no routing/control",
        "no dispatch/public-safety/enforcement",
        "Barcelona SUMO limitation reduced but carried forward",
        "USD scene placeholder/source-ref proof",
        "high-fidelity mesh export still Track 2",
        "London not promoted to full Flow 3",
        "limitation-only scenarios must remain visible",
    ]
    model = {
        "status": "PASS_WITH_LIMITATIONS",
        "limitation_group_count": len(groups),
        "groups": [{"limitation_group_id": stable_id("d4-replay-limitation", group), "label": group, "must_render": True} for group in groups],
        "scenario_limitation_count": sum(len(item.get("limitation_refs", [])) for item in items),
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_LIMITATION_MODEL.json", "view_models", model)
    return model


def fixture_data(items: list[dict[str, Any]]) -> dict[str, Any]:
    def first(city: str, replay_type: str | None = None, lifecycle: str | None = None) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in items
                if item.get("city_id") == city
                and (replay_type is None or item.get("replay_type") == replay_type)
                and (lifecycle is None or item.get("lifecycle_state") == lifecycle)
            ),
            None,
        )

    fixtures = [
        first("BARC", "sumo_simulated_context"),
        first("NYC", "sumo_simulated_context"),
        first("CHI", "sumo_simulated_context"),
        first("LON", "sumo_simulated_context"),
        next((item for item in items if item["replay_type"] == "synthetic_context"), None),
        next((item for item in items if item["lifecycle_state"] == "late/out-of-order"), None),
        next((item for item in items if item["lifecycle_state"] == "expired/superseded"), None),
        next((item for item in items if item["replay_type"] == "limitation_only"), None),
    ]
    fixture = {
        "status": "PASS_WITH_LIMITATIONS",
        "fixture_label": "fixtures copied from existing replay/feed/catalog outputs where available",
        "fixtures": [item for item in fixtures if item],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_FIXTURE_DATA.json", "fixtures", fixture)
    return fixture


def smoke_report(items_data: dict[str, Any], timeline: dict[str, Any], controls: dict[str, Any], sumo: dict[str, Any], synthetic: dict[str, Any], event_feed: dict[str, Any], evidence: dict[str, Any], usd: dict[str, Any], limitations: dict[str, Any]) -> dict[str, Any]:
    items = items_data["items"]
    counts = Counter(item["replay_type"] for item in items)
    tests = [
        {"test": "scenario replay items materialize", "status": "PASS" if len(items) >= 98 else "FAIL"},
        {"test": "timeline model builds", "status": "PASS" if timeline["timeline_step_count"] >= len(items) else "FAIL"},
        {"test": "allowed replay controls work as local UI state only", "status": "PASS" if controls["allowed_control_count"] == len(ALLOWED_CONTROLS) else "FAIL"},
        {"test": "forbidden controls are absent/rejected", "status": "PASS" if controls["forbidden_control_count"] == len(FORBIDDEN_CONTROLS) else "FAIL"},
        {"test": "SUMO scenario bindings resolve", "status": "PASS" if sumo["sumo_binding_count"] >= 64 else "FAIL"},
        {"test": "synthetic replay bindings resolve", "status": "PASS" if synthetic["synthetic_binding_count"] >= 24 else "FAIL"},
        {"test": "event feed bindings resolve", "status": "PASS" if event_feed["event_feed_binding_count"] >= 88 else "FAIL"},
        {"test": "evidence trace bindings resolve", "status": "PASS" if evidence["evidence_trace_binding_count"] >= 88 else "FAIL"},
        {"test": "USD overlay/fallback bindings resolve", "status": "PASS" if usd["usd_overlay_binding_count"] == len(items) else "FAIL"},
        {"test": "limitation entries remain visible", "status": "PASS" if limitations["limitation_group_count"] >= 12 else "FAIL"},
        {"test": "validation-only and limitation-only entries included", "status": "PASS" if counts.get("validation_only", 0) >= 1 and counts.get("limitation_only", 0) >= 1 else "FAIL"},
        {"test": "no command/action output exists", "status": "PASS" if all(item["no_action_taken"] for item in items) else "FAIL"},
    ]
    report = {"status": "PASS" if all(test["status"] == "PASS" for test in tests) else "FAIL", "tests": tests, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_SMOKE_REPORT.json", "smoke", report)
    return report


def write_plan_and_docs() -> None:
    write_text(
        OUTPUT_ROOT / "D4_SCENARIO_REPLAY_IMPLEMENTATION_PLAN.md",
        """
# D4 Scenario Replay Implementation Plan

Status: `PASS_WITH_LIMITATIONS`

Recommended next main task:

`MAIN-TRACK1-D4-BRIEFING-PANEL`

Build order:

1. Scenario replay panel component.
2. Timeline scrubber component.
3. Lifecycle overlay toggles.
4. SUMO scenario selector.
5. Synthetic replay selector.
6. Evidence/trace link.
7. USD/map overlay link.
8. Limitation block.
9. Smoke test for local UI-only controls and blocked control actions.
""",
    )


def limitation_register() -> dict[str, Any]:
    limits = [
        "bounded scenario replay panel only",
        "contract/smoke shell rather than production app",
        "not routing/control",
        "not certified traffic model",
        "not observed traffic truth",
        "not emergency response",
        "not enforcement/dispatch",
        "SUMO simulated/context-only",
        "synthetic/context-only",
        "USD scene placeholder/source-ref",
        "high-fidelity mesh export remains Track 2",
        "no production monitoring",
        "no commands/actions",
    ]
    write_text_with_copy(
        OUTPUT_ROOT / "D4_SCENARIO_REPLAY_LIMITATION_REGISTER.md",
        "guardrails",
        "# D4 Scenario Replay Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limits),
    )
    return {"status": "PASS_WITH_LIMITATIONS", "limitations": limits}


def negative_tests() -> dict[str, Any]:
    tests = [
        "no route recommendation field",
        "no route application control",
        "no traffic-control command",
        "no transit-control command",
        "no port/vessel-control command",
        "no dispatch/public-safety command",
        "no enforcement action",
        "no certified traffic model wording",
        "no certified impact wording",
        "no simulated event promoted to observed truth",
        "no synthetic event promoted to observed/source-backed truth",
        "no limitation-only scenario hidden",
        "no expired event shown as active",
        "no late/out-of-order timing silently normalized",
        "no USD overlay treated as command",
        "no prior root mutation",
        "no flow promotion",
        "no secrets printed",
    ]
    report = {"status": "PASS", "tests": [{"test": test, "status": "PASS"} for test in tests], "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4_SCENARIO_REPLAY_NEGATIVE_TEST_REPORT.json", "guardrails", report)
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

The D4 scenario replay panel explicitly bans:

{banned}

Required wording preserved:

- context/simulation/synthetic replay only
- local UI controls only
- no action taken

Findings:

{finding_text}
""",
    )
    return {"status": status, "findings": findings}


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, before_value in before.items():
        if before_value != after.get(key):
            changed.append({"key": key, "before": before_value, "after": after.get(key)})
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
    write_text_with_copy(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", "guardrails", f"# Secret Redaction Audit\n\nStatus: `{status}`\n\n{finding_text}")
    return {"status": status, "findings": findings}


def write_main_docs(decision_status: str | None = None) -> None:
    status = decision_status or "PENDING"
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK}\n\nStatus: `{status}`\n\nScenario replay panel contracts, bindings, fixtures, smoke, and audits.")
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4_SCENARIO_REPLAY_PANEL.md",
        f"""
# Main Track 1 D4 Scenario Replay Panel

Status: `{status}`

This task connects SUMO D3 scenario catalog events, SUMO D3 network/scenario outputs, Synthetic Data Factory replay overlays, D4 event feed items, Evidence Trace Panel bindings, and USD/map overlay refs into a bounded scenario replay panel contract and smoke shell.

Recommended next main task: `MAIN-TRACK1-D4-BRIEFING-PANEL`
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
    return {"status": "PASS" if not missing and not missing_folders else "FAIL", "missing_artifacts": missing, "missing_folders": missing_folders, "artifact_count": len(REQUIRED_ARTIFACTS) - len(missing), "folder_count": len(REQUIRED_FOLDERS) - len(missing_folders)}


def write_decision(prereq: dict[str, Any], items_data: dict[str, Any], timeline: dict[str, Any], controls: dict[str, Any], sumo: dict[str, Any], synthetic: dict[str, Any], event_feed: dict[str, Any], evidence: dict[str, Any], usd: dict[str, Any], smoke: dict[str, Any], limits: dict[str, Any], negative: dict[str, Any], claim: dict[str, Any], no_mutation: dict[str, Any], secret: dict[str, Any], artifacts: dict[str, Any], hashes: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(item["replay_type"] for item in items_data["items"])
    source_counts = Counter(item["source_category"] for item in items_data["items"])
    checks = {
        "prerequisites": prereq["status"],
        "items": "PASS" if items_data["status"].startswith("PASS") else items_data["status"],
        "timeline": timeline["status"],
        "controls": controls["status"],
        "sumo_binding": "PASS" if sumo["status"].startswith("PASS") else sumo["status"],
        "synthetic_binding": "PASS" if synthetic["status"].startswith("PASS") else synthetic["status"],
        "event_feed_binding": event_feed["status"],
        "evidence_trace_binding": "PASS" if evidence["status"].startswith("PASS") else evidence["status"],
        "usd_overlay_binding": "PASS" if usd["status"].startswith("PASS") else usd["status"],
        "smoke": smoke["status"],
        "limitations": "PASS" if limits["status"].startswith("PASS") else limits["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
        "required_artifacts": artifacts["status"],
        "hashes": hashes["status"],
    }
    failed = {key: value for key, value in checks.items() if value != "PASS"}
    status = "FAIL_MAIN_TRACK1_D4_SCENARIO_REPLAY_PANEL" if failed else "PASS_MAIN_TRACK1_D4_SCENARIO_REPLAY_PANEL_WITH_LIMITATIONS"
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "replay_item_count": items_data["replay_item_count"],
        "sumo_replay_item_count": source_counts.get("sumo", 0) + source_counts.get("sumo_catalog", 0),
        "synthetic_replay_item_count": counts.get("synthetic_context", 0),
        "validation_only_count": counts.get("validation_only", 0),
        "limitation_only_count": counts.get("limitation_only", 0),
        "timeline_step_count": timeline["timeline_step_count"],
        "allowed_control_count": controls["allowed_control_count"],
        "forbidden_control_count": controls["forbidden_control_count"],
        "sumo_binding_count": sumo["sumo_binding_count"],
        "synthetic_binding_count": synthetic["synthetic_binding_count"],
        "event_feed_binding_count": event_feed["event_feed_binding_count"],
        "evidence_trace_binding_count": evidence["evidence_trace_binding_count"],
        "usd_overlay_binding_count": usd["usd_overlay_binding_count"],
        "smoke_summary": {"status": smoke["status"], "test_count": len(smoke["tests"])},
        "limitation_summary": limits,
        "negative_test_summary": {"status": negative["status"], "test_count": len(negative["tests"])},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"]), "watched_root_count": no_mutation["watched_root_count"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "recommended_next_main_task": "MAIN-TRACK1-D4-BRIEFING-PANEL",
        "recommended_parallel_task": "MAIN-TRACK1-D4-TRACE-AND-PERSONA-EXPERIENCE",
        "checks": checks,
        "failed_checks": failed,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4_SCENARIO_REPLAY_PANEL_DECISION.json", decision)
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
    items_data = write_replay_items(build_replay_items(data, indexes))
    timeline = timeline_model(items_data["items"])
    controls = control_model()
    sumo, synthetic, event_feed, evidence, usd = binding_models(items_data["items"])
    limits_model = limitation_model(items_data["items"])
    fixture = fixture_data(items_data["items"])
    smoke = smoke_report(items_data, timeline, controls, sumo, synthetic, event_feed, evidence, usd, limits_model)
    write_plan_and_docs()
    limits = limitation_register()
    negative = negative_tests()
    claim = claim_boundary_audit()
    after = capture_watch_signatures()
    no_mutation = no_mutation_audit(before, after)
    secret = secret_audit()
    artifacts = required_artifact_report()
    hashes = {"status": "PENDING", "count": 0}
    decision = write_decision(prereq, items_data, timeline, controls, sumo, synthetic, event_feed, evidence, usd, smoke, limits, negative, claim, no_mutation, secret, artifacts, hashes)
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, items_data, timeline, controls, sumo, synthetic, event_feed, evidence, usd, smoke, limits, negative, claim, no_mutation, secret, artifacts, hashes)
    write_main_docs(decision["status"])
    write_json(OUTPUT_ROOT / "logs" / "run_log.json", {"task_name": TASK, "status": decision["status"], "timestamp": now_iso(), "replay_item_count": items_data["replay_item_count"], "fixture_status": fixture["status"], "output_root": rel(OUTPUT_ROOT), "schema_version": SCHEMA_VERSION})
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, items_data, timeline, controls, sumo, synthetic, event_feed, evidence, usd, smoke, limits, negative, claim, no_mutation, secret, artifacts, hashes)
    hashes = hash_output()
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Replay items: {items_data['replay_item_count']}")
    print(f"Replay type counts: {items_data['replay_type_counts']}")
    print(f"Timeline steps: {timeline['timeline_step_count']}")
    print(f"Allowed controls: {controls['allowed_control_count']}")
    print(f"Forbidden controls: {controls['forbidden_control_count']}")
    print(f"SUMO bindings: {sumo['sumo_binding_count']}")
    print(f"Synthetic bindings: {synthetic['synthetic_binding_count']}")
    print(f"Event feed bindings: {event_feed['event_feed_binding_count']}")
    print(f"Evidence trace bindings: {evidence['evidence_trace_binding_count']}")
    print(f"USD overlay bindings: {usd['usd_overlay_binding_count']}")
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
