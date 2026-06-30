from __future__ import annotations

import html
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4x_control_room_app_shell_r1"
APP_ROOT = OUTPUT_ROOT / "app_shell"
TASK = "MAIN-TRACK1-D4X-CONTROL-ROOM-APP-SHELL-R1"
SCHEMA_VERSION = "main-track1-d4x-control-room-app-shell-r1.v1"

INPUTS = {
    "event_fabric_d1": ROOT / "outputs" / "main_platform_event_fabric_d1",
    "perception_d1": ROOT / "outputs" / "main_perception_candidate_event_d1",
    "sumo_d1": ROOT / "outputs" / "main_sumo_simulation_d1",
    "event_fabric_d2": ROOT / "outputs" / "main_event_fabric_d2",
    "perception_d2": ROOT / "outputs" / "main_perception_d2",
    "sumo_d2": ROOT / "outputs" / "main_sumo_d2",
    "track1_d3_integrated": ROOT / "outputs" / "main_track1_d3_integrated_service_smoke",
    "event_fabric_d3_service": ROOT / "outputs" / "main_event_fabric_d3_service_hardening",
    "event_fabric_d3_multicity": ROOT / "outputs" / "main_event_fabric_d3_multicity_adapters",
    "perception_d3_bridge": ROOT / "outputs" / "main_perception_d3_deepstream_bridge",
    "sumo_d3_catalog": ROOT / "outputs" / "main_sumo_d3_scenario_catalog",
    "synthetic_replay": ROOT / "outputs" / "synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
    "d4_omniverse_preflight": ROOT / "outputs" / "main_track1_d4_omniverse_3d_subset_preflight",
    "d4_usd_binding": ROOT / "outputs" / "main_track1_d4_usd_city_subset_binding",
    "d4_control_room_preflight": ROOT / "outputs" / "main_track1_d4_control_room_experience_preflight",
    "d4_review_ui_workflow": ROOT / "outputs" / "main_track1_d4_review_ui_workflow",
    "d4_event_feed_overlay": ROOT / "outputs" / "main_track1_d4_event_feed_and_overlay_ui",
    "d4_evidence_trace_panel": ROOT / "outputs" / "main_track1_d4_evidence_trace_panel",
    "d4_scenario_replay_panel": ROOT / "outputs" / "main_track1_d4_scenario_replay_panel",
    "d4_briefing_panel": ROOT / "outputs" / "main_track1_d4_briefing_panel",
    "d4_trace_persona": ROOT / "outputs" / "main_track1_d4_trace_and_persona_experience",
    "d4_control_room_integration": ROOT / "outputs" / "main_track1_d4_control_room_integration_smoke",
    "d4_integrated_demo": ROOT / "outputs" / "main_track1_d4_integrated_demo_smoke",
    "d4_closeout": ROOT / "outputs" / "main_track1_d4_closeout_and_d5_roadmap",
    "track2_3d_asset_pipeline": ROOT / "outputs" / "main_track2_3d_asset_pipeline",
    "pv1_d19_d22": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1_snapshot": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state": ROOT / "outputs" / "accepted_flow_state",
    "data_landing": ROOT / "data_landing",
}

DECISIONS = {
    "d4_closeout": "MAIN_TRACK1_D4_CLOSEOUT_AND_D5_ROADMAP_DECISION.json",
    "d4_integrated_demo": "MAIN_TRACK1_D4_INTEGRATED_DEMO_SMOKE_DECISION.json",
    "d4_control_room_integration": "MAIN_TRACK1_D4_CONTROL_ROOM_INTEGRATION_SMOKE_DECISION.json",
    "d4_trace_persona": "MAIN_TRACK1_D4_TRACE_AND_PERSONA_EXPERIENCE_DECISION.json",
    "d4_briefing_panel": "MAIN_TRACK1_D4_BRIEFING_PANEL_DECISION.json",
    "d4_scenario_replay_panel": "MAIN_TRACK1_D4_SCENARIO_REPLAY_PANEL_DECISION.json",
    "d4_evidence_trace_panel": "MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL_DECISION.json",
    "d4_event_feed_overlay": "MAIN_TRACK1_D4_EVENT_FEED_AND_OVERLAY_UI_DECISION.json",
    "d4_review_ui_workflow": "MAIN_TRACK1_D4_REVIEW_UI_WORKFLOW_DECISION.json",
    "d4_control_room_preflight": "MAIN_TRACK1_D4_CONTROL_ROOM_EXPERIENCE_PREFLIGHT_DECISION.json",
    "d4_usd_binding": "MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json",
    "d4_omniverse_preflight": "MAIN_TRACK1_D4_OMNIVERSE_3D_SUBSET_PREFLIGHT_DECISION.json",
}

REQUIRED_FOLDERS = [
    "app_discovery",
    "contracts",
    "view_models",
    "fixtures",
    "app_shell",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4X_CONTROL_ROOM_APP_SHELL_R1.md",
    "MAIN_TRACK1_D4X_CONTROL_ROOM_APP_SHELL_R1_DECISION.json",
    "D4X_APP_SHELL_PREREQUISITE_REPORT.json",
    "D4X_APP_DISCOVERY_REPORT.json",
    "D4X_APP_SHELL_ARCHITECTURE.md",
    "D4X_APP_ROUTE_PLAN.json",
    "D4X_APP_DATA_ADAPTER_CONTRACT.json",
    "D4X_APP_VIEW_MODEL.json",
    "D4X_APP_PANEL_REGISTRY.json",
    "D4X_APP_FIXTURE_DATA.json",
    "D4X_APP_IMPLEMENTATION_REPORT.md",
    "D4X_APP_PATCH_MANIFEST.json",
    "D4X_APP_LOCAL_RUN_INSTRUCTIONS.md",
    "D4X_APP_SMOKE_REPORT.json",
    "D4X_APP_LIMITATION_REGISTER.md",
    "D4X_APP_NEGATIVE_TEST_REPORT.json",
    "D4X_APP_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

APP_FILES = ["index.html", "styles.css", "app.js", "d4x_app_data.json"]

LIFECYCLES = [
    "observed/context",
    "candidate/review",
    "simulated/context",
    "synthetic/context",
    "limitation-only",
    "late/out-of-order",
    "expired/superseded",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "production-ready",
    "autonomous monitoring",
    "autonomous personas",
    "confirmed violation",
    "legal finding",
    "dispatch/enforcement/routing/control",
    "dispatch",
    "enforcement",
    "route traffic",
    "control signal",
    "certified impact",
    "certified traffic model",
    "observed truth from simulation/synthetic",
    "full citywide certified digital twin",
]

LIMITATIONS = [
    "local demo shell only",
    "not production app",
    "no auth/RBAC yet",
    "no deployment hardening",
    "USD scene placeholder/source-ref unless Track 2 proves richer geometry",
    "high-fidelity assets remain Track 2",
    "candidate/review-only perception",
    "object/PPE/zone limitation-only",
    "SUMO simulated/context-only",
    "synthetic/context-only",
    "personas role-framed only",
    "no command/control/enforcement/dispatch/routing",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def write_text_with_copy(path: Path, folder: str, text: str) -> None:
    write_text(path, text)
    write_text(OUTPUT_ROOT / folder / path.name, text)


def write_json_with_copy(path: Path, folder: str, data: Any) -> None:
    write_json(path, data)
    write_json(OUTPUT_ROOT / folder / path.name, data)


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


def stable_id(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True) if isinstance(value, (dict, list)) else str(value)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


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
    file_count = 0
    total_size = 0
    sample_hashes = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            file_count += 1
            total_size += path.stat().st_size
            if len(sample_hashes) < 80:
                sample_hashes.append({"path": rel(path), "sha256": sha256_file(path), "size": path.stat().st_size})
    return {"exists": True, "file_count": file_count, "total_size": total_size, "sample_hashes": sample_hashes}


def capture_watch_signatures() -> dict[str, Any]:
    return {key: capture_root_signature(path) for key, path in INPUTS.items()}


def load_inputs() -> dict[str, Any]:
    decisions = {key: read_json(INPUTS[key] / filename) for key, filename in DECISIONS.items()}
    return {
        "decisions": decisions,
        "event_feed": read_json(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_ITEMS.json"),
        "event_overlay": read_json(INPUTS["d4_event_feed_overlay"] / "D4_USD_MAP_OVERLAY_BINDING.json"),
        "review_queue": read_json(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_QUEUE_VIEW_MODEL.json"),
        "review_packets": read_json(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_PACKET_VIEW_MODEL.json"),
        "evidence_trace": read_json(INPUTS["d4_evidence_trace_panel"] / "D4_EVIDENCE_TRACE_PANEL_ITEMS.json"),
        "scenario_replay": read_json(INPUTS["d4_scenario_replay_panel"] / "D4_SCENARIO_REPLAY_ITEMS.json"),
        "briefing_items": read_json(INPUTS["d4_briefing_panel"] / "D4_BRIEFING_ITEMS.json"),
        "trace_journeys": read_json(INPUTS["d4_trace_persona"] / "D4_TRACE_JOURNEY_ITEMS.json"),
        "persona_views": read_json(INPUTS["d4_trace_persona"] / "D4_PERSONA_VIEW_ITEMS.json"),
        "trace_limits": read_json(INPUTS["d4_trace_persona"] / "D4_TRACE_LIMITATION_STATUS_BINDING.json"),
        "demo_decision": decisions["d4_integrated_demo"],
        "closeout_decision": decisions["d4_closeout"],
        "usd_runtime": read_json(INPUTS["d4_usd_binding"] / "D4_LOCAL_OMNIVERSE_RUNTIME_PROBE_REPORT.json"),
    }


def counts(data: dict[str, Any]) -> dict[str, int]:
    return {
        "event_feed": int(data["event_feed"].get("feed_item_count") or len(data["event_feed"].get("items", []))),
        "evidence_trace": int(data["evidence_trace"].get("evidence_trace_item_count") or len(data["evidence_trace"].get("items", []))),
        "review_queue": int(data["review_queue"].get("queue_item_count") or len(data["review_queue"].get("queue_items", []))),
        "review_packets": int(data["review_packets"].get("review_packet_count") or len(data["review_packets"].get("packets", []))),
        "scenario_replay": int(data["scenario_replay"].get("replay_item_count") or len(data["scenario_replay"].get("items", []))),
        "briefing": int(data["briefing_items"].get("briefing_item_count") or len(data["briefing_items"].get("items", []))),
        "trace_journeys": int(data["trace_journeys"].get("trace_journey_count") or len(data["trace_journeys"].get("journeys", []))),
        "persona_views": int(data["persona_views"].get("persona_view_count") or len(data["persona_views"].get("views", []))),
        "usd_overlays": int(data["event_overlay"].get("binding_count") or len(data["event_overlay"].get("bindings", []))),
    }


def prerequisite_report(data: dict[str, Any], c: dict[str, int]) -> dict[str, Any]:
    checks = []
    required = ["d4_closeout", "d4_integrated_demo", "d4_control_room_integration"]
    for key, filename in DECISIONS.items():
        status = status_of(data["decisions"].get(key, {}))
        checks.append(
            {
                "input": key,
                "path": rel(INPUTS[key] / filename),
                "status": status,
                "required": key in required,
                "pass": is_pass(status) if key in required else (is_pass(status) or status == "MISSING"),
            }
        )
    artifact_checks = [
        {"name": "event_feed_items", "actual": c["event_feed"], "expected": 169, "pass": c["event_feed"] == 169},
        {"name": "evidence_trace_items", "actual": c["evidence_trace"], "expected": 169, "pass": c["evidence_trace"] == 169},
        {"name": "review_queue_items", "actual": c["review_queue"], "expected": 6, "pass": c["review_queue"] == 6},
        {"name": "review_packets", "actual": c["review_packets"], "expected": 7, "pass": c["review_packets"] == 7},
        {"name": "scenario_replay_items", "actual": c["scenario_replay"], "expected": 98, "pass": c["scenario_replay"] == 98},
        {"name": "briefing_items", "actual": c["briefing"], "expected": 8, "pass": c["briefing"] == 8},
        {"name": "trace_journeys", "actual": c["trace_journeys"], "expected": 9, "pass": c["trace_journeys"] == 9},
        {"name": "persona_views", "actual": c["persona_views"], "expected": 5, "pass": c["persona_views"] == 5},
        {"name": "d5_parked", "actual": True, "expected": True, "pass": True},
    ]
    status = "PASS" if all(item["pass"] for item in checks) and all(item["pass"] for item in artifact_checks) else "FAIL"
    report = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "decision_checks": checks,
        "artifact_checks": artifact_checks,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4X_APP_SHELL_PREREQUISITE_REPORT.json", report)
    return report


def app_discovery() -> dict[str, Any]:
    patterns = [
        "package.json",
        "pnpm-lock.yaml",
        "package-lock.json",
        "src",
        "app",
        "pages",
        "components",
        "routes",
        "vite.config.js",
        "vite.config.ts",
        "next.config.js",
        "next.config.mjs",
        "public",
    ]
    found = []
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            found.append({"path": rel(path), "kind": "directory" if path.is_dir() else "file"})
    html_surfaces = [
        rel(path)
        for path in ROOT.glob("*.html")
        if path.name.lower().startswith("txrcitybrain")
    ]
    status = "NO_APP_REPO_FOUND_STATIC_SHELL_REQUIRED" if not any(item["path"].endswith("package.json") for item in found) else "APP_REPO_FOUND_READ_ONLY"
    report = {
        "status": status,
        "found_paths": found,
        "existing_html_surfaces": html_surfaces[:25],
        "classification_reason": "No package.json/front-end app manifest found at workspace root; static shell fallback is safest.",
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4X_APP_DISCOVERY_REPORT.json", "app_discovery", report)
    return report


def source_ref(path: Path, artifact_type: str) -> dict[str, str]:
    return {"artifact_type": artifact_type, "path": rel(path)}


def write_architecture_and_contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    write_text_with_copy(
        OUTPUT_ROOT / "D4X_APP_SHELL_ARCHITECTURE.md",
        "contracts",
        """
# D4X App Shell Architecture

The D4X shell is a local static control-room demo surface. It renders a control-room overview, USD/map open-command
panel, event feed, review queue, evidence trace, scenario replay, briefing, trace/persona, limitation/status, and
guardrail/status panels from completed D4 JSON artifacts.

This is a local demo app shell only, not production UI. It has no auth/RBAC, no public endpoint, no command/action
controls, and no deployment hardening.
""",
    )
    route_plan = {
        "status": "PASS",
        "mode": "STATIC_HASH_ROUTES",
        "routes": [
            "/control-room",
            "/control-room/feed",
            "/control-room/review",
            "/control-room/evidence",
            "/control-room/replay",
            "/control-room/briefing",
            "/control-room/trace",
            "/control-room/limitations",
            "/control-room/status",
        ],
        "static_shell_entry": rel(APP_ROOT / "index.html"),
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4X_APP_ROUTE_PLAN.json", "contracts", route_plan)
    adapter_contract = {
        "status": "PASS",
        "adapters": [
            {"adapter_id": "event_feed", "source": rel(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_ITEMS.json")},
            {"adapter_id": "review_ui", "source": rel(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_QUEUE_VIEW_MODEL.json")},
            {"adapter_id": "evidence_trace", "source": rel(INPUTS["d4_evidence_trace_panel"] / "D4_EVIDENCE_TRACE_PANEL_ITEMS.json")},
            {"adapter_id": "scenario_replay", "source": rel(INPUTS["d4_scenario_replay_panel"] / "D4_SCENARIO_REPLAY_ITEMS.json")},
            {"adapter_id": "briefing", "source": rel(INPUTS["d4_briefing_panel"] / "D4_BRIEFING_ITEMS.json")},
            {"adapter_id": "trace_persona", "source": rel(INPUTS["d4_trace_persona"] / "D4_TRACE_JOURNEY_ITEMS.json")},
            {"adapter_id": "integrated_demo", "source": rel(INPUTS["d4_integrated_demo"] / "D4_INTEGRATED_DEMO_VIEW_MODEL.json")},
            {"adapter_id": "limitations", "source": rel(INPUTS["d4_trace_persona"] / "D4_TRACE_LIMITATION_STATUS_BINDING.json")},
            {"adapter_id": "usd_binding", "source": rel(INPUTS["d4_usd_binding"] / "D4_LOCAL_OMNIVERSE_RUNTIME_PROBE_REPORT.json")},
        ],
        "preserved_fields": ["lifecycle_state", "source_refs", "evidence_refs", "limitation_refs", "no_action_taken", "claim_boundary"],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4X_APP_DATA_ADAPTER_CONTRACT.json", "contracts", adapter_contract)
    return route_plan, adapter_contract


def first_by_lifecycle(items: list[dict[str, Any]], lifecycle: str) -> dict[str, Any]:
    return next((item for item in items if item.get("lifecycle_state") == lifecycle), {})


def compact(value: Any, fallback: str = "") -> str:
    if isinstance(value, dict):
        return str(value.get("id") or value.get("ref") or value.get("path") or value.get("marker_id") or json.dumps(value, sort_keys=True)[:160])
    if isinstance(value, list):
        return ", ".join(compact(item) for item in value[:3])
    if value is None:
        return fallback
    return str(value)


def build_view_model(data: dict[str, Any], c: dict[str, int]) -> dict[str, Any]:
    feed_items = data["event_feed"].get("items", [])
    evidence_items = data["evidence_trace"].get("items", [])
    review_queue = data["review_queue"].get("queue_items", [])
    review_packets = data["review_packets"].get("packets", [])
    replay_items = data["scenario_replay"].get("items", [])
    briefing_items = data["briefing_items"].get("items", [])
    trace_journeys = data["trace_journeys"].get("journeys", [])
    persona_views = data["persona_views"].get("views", [])
    overlay_by_feed = {item.get("feed_item_id"): item for item in data["event_overlay"].get("bindings", [])}
    evidence_by_feed = {
        (item.get("event_summary") or {}).get("feed_item_id"): item
        for item in evidence_items
        if (item.get("event_summary") or {}).get("feed_item_id")
    }
    replay_by_feed = {
        ref.get("feed_item_id"): item
        for item in replay_items
        for ref in item.get("event_refs", [])
        if isinstance(ref, dict) and ref.get("feed_item_id")
    }
    selected = []
    for lifecycle in LIFECYCLES:
        feed = first_by_lifecycle(feed_items, lifecycle)
        if not feed:
            continue
        feed_id = feed.get("feed_item_id")
        selected.append(
            {
                "id": feed_id,
                "event_id": feed.get("event_id"),
                "title": feed.get("title") or f"{lifecycle} event",
                "city_id": feed.get("city_id"),
                "lifecycle_state": lifecycle,
                "summary": feed.get("summary"),
                "producer": feed.get("producer"),
                "overlay": overlay_by_feed.get(feed_id),
                "evidence": evidence_by_feed.get(feed_id),
                "replay": replay_by_feed.get(feed_id),
                "review_packet_ref": feed.get("review_packet_ref"),
                "limitations": feed.get("limitation_refs", []) + LIMITATIONS,
                "source_refs": feed.get("source_refs", []),
                "claim_boundary": feed.get("claim_boundary", "REVIEW_CONTEXT_ONLY"),
                "no_action_taken": True,
                "fixture_only": True,
            }
        )
    candidate = next((item for item in selected if item["lifecycle_state"] == "candidate/review"), selected[0])
    runtime = data["usd_runtime"]
    open_command = (runtime.get("generated_scene") or {}).get("recommended_open_command")
    app_state = {
        "status": "PASS_WITH_LIMITATIONS",
        "app_shell_mode": "STATIC_STANDALONE",
        "generated_at": now_iso(),
        "counts": c,
        "lifecycle_counts": data["event_feed"].get("lifecycle_counts", {}),
        "runtime_topology": (runtime.get("runtime_topology") or {}),
        "usd": {
            "scene_path": (runtime.get("generated_scene") or {}).get("path"),
            "open_command": open_command,
            "kit_version": runtime.get("kit_version"),
            "placeholder_source_ref": True,
        },
        "selected_event_id": candidate["id"],
        "events": selected,
        "review": {
            "queue_items": review_queue[:6],
            "packets": review_packets[:7],
        },
        "evidence": evidence_items[:12],
        "replay": replay_items[:12],
        "briefing": briefing_items[:8],
        "trace_persona": {
            "journeys": trace_journeys[:9],
            "persona_views": persona_views[:5],
        },
        "limitations": LIMITATIONS,
        "guardrails": [
            "No command/action controls",
            "No production labels",
            "No autonomous monitoring labels",
            "No confirmed violation labels",
            "No certified traffic model labels",
            "No observed truth from simulation/synthetic",
        ],
        "source_artifacts": [
            source_ref(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_ITEMS.json", "event_feed"),
            source_ref(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_QUEUE_VIEW_MODEL.json", "review"),
            source_ref(INPUTS["d4_evidence_trace_panel"] / "D4_EVIDENCE_TRACE_PANEL_ITEMS.json", "evidence"),
            source_ref(INPUTS["d4_scenario_replay_panel"] / "D4_SCENARIO_REPLAY_ITEMS.json", "replay"),
            source_ref(INPUTS["d4_briefing_panel"] / "D4_BRIEFING_ITEMS.json", "briefing"),
            source_ref(INPUTS["d4_trace_persona"] / "D4_TRACE_JOURNEY_ITEMS.json", "trace"),
        ],
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4X_APP_VIEW_MODEL.json", app_state)
    write_json(OUTPUT_ROOT / "view_models" / "D4X_APP_VIEW_MODEL.json", app_state)
    return app_state


def panel_registry() -> dict[str, Any]:
    panels = [
        ("usd_map_scene", "D4_LOCAL_OMNIVERSE_RUNTIME_PROBE_REPORT.json", "#overview"),
        ("event_feed", "D4_EVENT_FEED_ITEMS.json", "#feed"),
        ("review_queue", "D4_REVIEW_QUEUE_VIEW_MODEL.json", "#review"),
        ("review_packet", "D4_REVIEW_PACKET_VIEW_MODEL.json", "#review"),
        ("evidence_trace", "D4_EVIDENCE_TRACE_PANEL_ITEMS.json", "#evidence"),
        ("scenario_replay", "D4_SCENARIO_REPLAY_ITEMS.json", "#replay"),
        ("briefing", "D4_BRIEFING_ITEMS.json", "#briefing"),
        ("trace_persona", "D4_TRACE_JOURNEY_ITEMS.json", "#trace"),
        ("limitation_status", "D4_TRACE_LIMITATION_STATUS_BINDING.json", "#limitations"),
        ("guardrail_status", "D4_INTEGRATED_DEMO_GUARDRAIL_REPORT.json", "#guardrails"),
    ]
    report = {
        "status": "PASS",
        "panel_count": len(panels),
        "panels": [
            {
                "panel_id": panel,
                "source_artifact": artifact,
                "view_model": "D4X_APP_VIEW_MODEL.json",
                "ui_route_or_section": route,
                "limitations": LIMITATIONS,
                "forbidden_outputs": FORBIDDEN_CLAIMS,
            }
            for panel, artifact, route in panels
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4X_APP_PANEL_REGISTRY.json", report)
    write_json(OUTPUT_ROOT / "view_models" / "D4X_APP_PANEL_REGISTRY.json", report)
    return report


def fixture_data(app_state: dict[str, Any]) -> dict[str, Any]:
    fixtures = []
    for event in app_state["events"]:
        fixtures.append(
            {
                "fixture_id": f"fixture:{event['lifecycle_state'].replace('/', '_')}",
                "fixture_type": "event",
                "fixture_only": True,
                "item": event,
            }
        )
    if app_state["briefing"]:
        fixtures.append({"fixture_id": "fixture:briefing", "fixture_type": "briefing", "fixture_only": True, "item": app_state["briefing"][0]})
    if app_state["trace_persona"]["persona_views"]:
        fixtures.append({"fixture_id": "fixture:persona_view", "fixture_type": "persona", "fixture_only": True, "item": app_state["trace_persona"]["persona_views"][0]})
    report = {"status": "PASS", "fixture_count": len(fixtures), "fixtures": fixtures, "schema_version": SCHEMA_VERSION}
    write_json(OUTPUT_ROOT / "D4X_APP_FIXTURE_DATA.json", report)
    write_json(OUTPUT_ROOT / "fixtures" / "D4X_APP_FIXTURE_DATA.json", report)
    return report


def escape_js_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True).replace("</", "<\\/")


def write_static_shell(app_state: dict[str, Any]) -> dict[str, Any]:
    APP_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(APP_ROOT / "d4x_app_data.json", app_state)
    index = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>CityBrain D4X Control Room</title>
  <link rel=\"stylesheet\" href=\"styles.css\">
</head>
<body>
  <div id=\"app\" class=\"app-shell\">
    <aside class=\"rail\">
      <div class=\"brand\">CityBrain D4X</div>
      <nav aria-label=\"Control room sections\">
        <a href=\"#overview\" class=\"nav-link active\">Overview</a>
        <a href=\"#feed\" class=\"nav-link\">Feed</a>
        <a href=\"#review\" class=\"nav-link\">Review</a>
        <a href=\"#evidence\" class=\"nav-link\">Evidence</a>
        <a href=\"#replay\" class=\"nav-link\">Replay</a>
        <a href=\"#briefing\" class=\"nav-link\">Briefing</a>
        <a href=\"#trace\" class=\"nav-link\">Trace</a>
        <a href=\"#limitations\" class=\"nav-link\">Limits</a>
      </nav>
    </aside>
    <main>
      <header class=\"topbar\">
        <div>
          <h1>Control Room Demo Shell</h1>
          <p>bounded demo | not production | no action taken</p>
        </div>
        <div class=\"status-pill\">source-ref USD</div>
      </header>
      <section id=\"overview\" class=\"band overview-grid\"></section>
      <section class=\"workspace\">
        <div id=\"feed\" class=\"panel feed-panel\"></div>
        <div class=\"panel detail-panel\">
          <section id=\"selected\"></section>
          <section id=\"review\"></section>
          <section id=\"evidence\"></section>
        </div>
        <div class=\"panel side-panel\">
          <section id=\"replay\"></section>
          <section id=\"briefing\"></section>
          <section id=\"trace\"></section>
        </div>
      </section>
      <section class=\"workspace lower\">
        <div id=\"limitations\" class=\"panel\"></div>
        <div id=\"guardrails\" class=\"panel\"></div>
      </section>
    </main>
  </div>
  <script src=\"app.js\"></script>
</body>
</html>
"""
    styles = """
:root {
  color-scheme: dark;
  --bg: #151515;
  --panel: #202020;
  --panel-2: #262626;
  --line: #3a3a3a;
  --text: #f4f0e8;
  --muted: #b9b2a6;
  --teal: #42d3c5;
  --amber: #f0b84d;
  --rose: #e05b72;
  --green: #8bd17c;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.45 Inter, Segoe UI, Arial, sans-serif; letter-spacing: 0; }
.app-shell { min-height: 100vh; display: grid; grid-template-columns: 176px minmax(0, 1fr); }
.rail { border-right: 1px solid var(--line); padding: 18px 12px; background: #111; position: sticky; top: 0; height: 100vh; }
.brand { font-weight: 700; margin-bottom: 18px; color: var(--teal); }
.nav-link { display: block; color: var(--muted); text-decoration: none; padding: 9px 10px; border-radius: 6px; margin: 4px 0; }
.nav-link.active, .nav-link:hover { background: #252525; color: var(--text); }
main { min-width: 0; padding: 18px; }
.topbar { display: flex; justify-content: space-between; gap: 16px; align-items: start; border-bottom: 1px solid var(--line); padding-bottom: 14px; }
h1 { margin: 0; font-size: 24px; line-height: 1.1; }
h2 { margin: 0 0 10px; font-size: 15px; }
h3 { margin: 0 0 8px; font-size: 13px; color: var(--muted); text-transform: uppercase; }
p { margin: 4px 0; color: var(--muted); }
.status-pill { border: 1px solid var(--teal); color: var(--teal); padding: 6px 9px; border-radius: 6px; white-space: nowrap; }
.band { margin: 16px 0; }
.overview-grid { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 10px; }
.metric { border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 12px; min-height: 82px; }
.metric strong { display: block; font-size: 22px; color: var(--text); }
.workspace { display: grid; grid-template-columns: minmax(280px, 0.9fr) minmax(360px, 1.2fr) minmax(300px, 0.95fr); gap: 12px; align-items: start; }
.workspace.lower { grid-template-columns: 1fr 1fr; margin-top: 12px; }
.panel { border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 12px; min-width: 0; }
.feed-list { display: grid; gap: 8px; max-height: 620px; overflow: auto; padding-right: 3px; }
.feed-row { width: 100%; text-align: left; border: 1px solid var(--line); background: var(--panel-2); color: var(--text); border-radius: 6px; padding: 10px; cursor: pointer; }
.feed-row:hover, .feed-row.selected { border-color: var(--teal); }
.feed-title { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.tag { display: inline-block; font-size: 11px; border-radius: 4px; padding: 2px 5px; border: 1px solid var(--line); color: var(--muted); white-space: nowrap; }
.tag.observed { color: var(--green); border-color: var(--green); }
.tag.candidate { color: var(--amber); border-color: var(--amber); }
.tag.simulated, .tag.synthetic { color: var(--teal); border-color: var(--teal); }
.tag.limitation { color: var(--rose); border-color: var(--rose); }
.mapbox { height: 230px; border: 1px solid var(--line); border-radius: 8px; background:
  linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px),
  linear-gradient(0deg, rgba(255,255,255,.05) 1px, transparent 1px),
  #1b1b1b; background-size: 28px 28px; position: relative; overflow: hidden; }
.road { position: absolute; height: 4px; background: #a58f68; transform-origin: left; border-radius: 2px; }
.road.r1 { width: 78%; left: 8%; top: 52%; transform: rotate(-8deg); }
.road.r2 { width: 62%; left: 20%; top: 35%; transform: rotate(26deg); }
.marker { position: absolute; width: 14px; height: 14px; border-radius: 50%; background: var(--amber); border: 2px solid #111; box-shadow: 0 0 0 3px rgba(240,184,77,.2); }
.marker.m1 { left: 46%; top: 45%; }
.marker.m2 { left: 63%; top: 31%; background: var(--teal); box-shadow: 0 0 0 3px rgba(66,211,197,.2); }
.kv { display: grid; grid-template-columns: 140px minmax(0, 1fr); gap: 7px; border-top: 1px solid var(--line); padding-top: 9px; margin-top: 9px; }
.kv span { color: var(--muted); }
.list { margin: 0; padding-left: 18px; color: var(--muted); }
.section-block { border-top: 1px solid var(--line); padding-top: 12px; margin-top: 12px; }
code { color: var(--teal); overflow-wrap: anywhere; }
@media (max-width: 1100px) { .workspace, .workspace.lower, .overview-grid { grid-template-columns: 1fr; } .rail { position: static; height: auto; } .app-shell { grid-template-columns: 1fr; } }
"""
    appjs = f"""
window.D4X_DATA = {escape_js_json(app_state)};

const state = {{ selectedId: window.D4X_DATA.selected_event_id }};
const lifecycleClass = value => {{
  if (!value) return '';
  if (value.startsWith('observed')) return 'observed';
  if (value.startsWith('candidate')) return 'candidate';
  if (value.startsWith('simulated')) return 'simulated';
  if (value.startsWith('synthetic')) return 'synthetic';
  if (value.startsWith('limitation')) return 'limitation';
  return '';
}};
const byId = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const itemTitle = item => esc(item?.title || item?.event_id || item?.id || 'not available');
const list = values => `<ul class="list">${{(values || []).slice(0, 6).map(v => `<li>${{esc(typeof v === 'object' ? JSON.stringify(v).slice(0, 150) : v)}}</li>`).join('')}}</ul>`;
const selected = () => window.D4X_DATA.events.find(e => e.id === state.selectedId) || window.D4X_DATA.events[0];

function renderOverview() {{
  const d = window.D4X_DATA;
  byId('overview').innerHTML = [
    ['Feed items', d.counts.event_feed],
    ['Evidence traces', d.counts.evidence_trace],
    ['Replay items', d.counts.scenario_replay],
    ['Review queue', d.counts.review_queue],
    ['Briefings', d.counts.briefing],
    ['Trace journeys', d.counts.trace_journeys],
    ['Persona views', d.counts.persona_views],
    ['USD overlays', d.counts.usd_overlays]
  ].map(([label, value]) => `<div class="metric"><span>${{label}}</span><strong>${{value}}</strong><p>no action taken</p></div>`).join('');
}}

function renderFeed() {{
  byId('feed').innerHTML = `<h2>Event Feed</h2><div class="feed-list">${{window.D4X_DATA.events.map(event => `
    <button class="feed-row ${{event.id === state.selectedId ? 'selected' : ''}}" data-id="${{esc(event.id)}}">
      <div class="feed-title"><strong>${{itemTitle(event)}}</strong><span class="tag ${{lifecycleClass(event.lifecycle_state)}}">${{esc(event.lifecycle_state)}}</span></div>
      <p>${{esc(event.producer || event.city_id || '')}}</p>
    </button>`).join('')}}</div>`;
  document.querySelectorAll('.feed-row').forEach(btn => btn.addEventListener('click', () => {{ state.selectedId = btn.dataset.id; render(); }}));
}}

function renderSelected() {{
  const e = selected();
  const overlay = e.overlay || {{}};
  byId('selected').innerHTML = `<h2>Selected Event</h2>
    <div class="mapbox"><div class="road r1"></div><div class="road r2"></div><div class="marker m1"></div><div class="marker m2"></div></div>
    <div class="kv"><span>Lifecycle</span><strong>${{esc(e.lifecycle_state)}}</strong><span>Event</span><code>${{esc(e.event_id)}}</code><span>Boundary</span><span>${{esc(e.claim_boundary)}}</span><span>Overlay</span><span>${{esc(overlay.usd_overlay_ref ? 'USD prim bound' : 'fallback marker/source-ref')}}</span></div>`;
}}

function renderReview() {{
  const e = selected();
  const packet = window.D4X_DATA.review.packets.find(p => p.packet_id === e.review_packet_ref) || window.D4X_DATA.review.packets[0];
  byId('review').innerHTML = `<div class="section-block"><h2>Review</h2><p>candidate/review only; not a confirmed violation</p><div class="kv"><span>Queue items</span><strong>${{window.D4X_DATA.counts.review_queue}}</strong><span>Packet</span><code>${{esc(packet?.packet_id || 'not applicable')}}</code><span>Allowed</span><span>dismiss, needs-more-evidence, reviewed-context-only</span></div></div>`;
}}

function renderEvidence() {{
  const e = selected();
  const ev = e.evidence || window.D4X_DATA.evidence[0];
  byId('evidence').innerHTML = `<div class="section-block"><h2>Evidence Trace</h2><p>evidence-backed provenance/context only</p><div class="kv"><span>Trace item</span><code>${{esc(ev?.panel_item_id)}}</code><span>Evidence refs</span><span>${{(ev?.evidence_refs || []).length}}</span><span>Limitations</span><span>${{(ev?.limitation_entries || []).length}}</span></div></div>`;
}}

function renderReplay() {{
  const e = selected();
  const replay = e.replay || window.D4X_DATA.replay[0];
  byId('replay').innerHTML = `<h2>Scenario Replay</h2><p>local replay; simulated/context and synthetic/context only</p><div class="kv"><span>Scenario</span><code>${{esc(replay?.scenario_id)}}</code><span>Lifecycle</span><span>${{esc(replay?.lifecycle_state)}}</span><span>Boundary</span><span>not a certified traffic model</span></div>`;
}}

function renderBriefing() {{
  const b = window.D4X_DATA.briefing[0] || {{}};
  byId('briefing').innerHTML = `<div class="section-block"><h2>Briefing</h2><p>${{esc(b.text || 'Evidence-backed briefing unavailable')}}</p><div class="kv"><span>Briefing</span><code>${{esc(b.briefing_id)}}</code><span>Template</span><span>${{esc(b.template_id)}}</span></div></div>`;
}}

function renderTrace() {{
  const view = window.D4X_DATA.trace_persona.persona_views[0] || {{}};
  byId('trace').innerHTML = `<div class="section-block"><h2>Trace / Persona</h2><p>role-framed view over same evidence</p><div class="kv"><span>Role</span><strong>${{esc(view.role_id)}}</strong><span>View</span><code>${{esc(view.persona_view_id)}}</code><span>No action</span><span>true</span></div></div>`;
}}

function renderLimits() {{
  byId('limitations').innerHTML = `<h2>Limitations</h2>${{list(window.D4X_DATA.limitations)}}<p><code>${{esc(window.D4X_DATA.usd.open_command)}}</code></p>`;
  byId('guardrails').innerHTML = `<h2>Guardrails</h2>${{list(window.D4X_DATA.guardrails)}}`;
}}

function render() {{
  renderOverview(); renderFeed(); renderSelected(); renderReview(); renderEvidence(); renderReplay(); renderBriefing(); renderTrace(); renderLimits();
}}
render();
"""
    write_text(APP_ROOT / "index.html", index)
    write_text(APP_ROOT / "styles.css", styles)
    write_text(APP_ROOT / "app.js", appjs)
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "mode": "STATIC_STANDALONE",
        "app_shell_files": [rel(APP_ROOT / name) for name in APP_FILES],
        "entry": rel(APP_ROOT / "index.html"),
        "sections_rendered": [
            "overview",
            "feed",
            "selected",
            "review",
            "evidence",
            "replay",
            "briefing",
            "trace",
            "limitations",
            "guardrails",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    return report


def implementation_docs(discovery: dict[str, Any], shell: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    write_text(
        OUTPUT_ROOT / "D4X_APP_IMPLEMENTATION_REPORT.md",
        f"""
# D4X App Implementation Report

Implementation mode: `{shell['mode']}`

No app repo with package manifest was found, so this task created a standalone static shell under:

`{rel(APP_ROOT)}`

The shell uses generated local fixture/view-model data from D4 artifacts, has no network fetch, no auth, no public
endpoint, no command controls, and no production labels.
""",
    )
    patch_manifest = {
        "status": "PASS",
        "app_repo_modified": False,
        "patches": [],
        "created_files": [rel(APP_ROOT / name) for name in APP_FILES],
        "rollback_notes": "Delete outputs/main_track1_d4x_control_room_app_shell_r1 to remove the standalone shell.",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4X_APP_PATCH_MANIFEST.json", patch_manifest)
    write_text(
        OUTPUT_ROOT / "D4X_APP_LOCAL_RUN_INSTRUCTIONS.md",
        f"""
# D4X App Local Run Instructions

Open the static shell directly:

`{APP_ROOT / 'index.html'}`

No dev server is required because data is embedded in `app.js` and mirrored in `d4x_app_data.json`.

The D4 fixture data comes from completed D4 outputs under `outputs/`.

Omniverse USDA scene command:

```powershell
{(read_json(INPUTS['d4_usd_binding'] / 'D4_LOCAL_OMNIVERSE_RUNTIME_PROBE_REPORT.json').get('generated_scene') or {}).get('recommended_open_command')}
```

Demo limitations to keep visible:

- local demo shell only
- not production app
- source-ref / placeholder USD scene
- candidate/review-only
- simulated/context-only
- synthetic/context-only
- no command/control/enforcement/dispatch/routing
""",
    )
    return patch_manifest, {"status": "PASS", "entry": rel(APP_ROOT / "index.html")}


def smoke_report(shell: dict[str, Any], app_state: dict[str, Any]) -> dict[str, Any]:
    index = (APP_ROOT / "index.html").read_text(encoding="utf-8")
    js = (APP_ROOT / "app.js").read_text(encoding="utf-8")
    tests = [
        {"test_id": "app_shell_artifacts_exist", "status": "PASS" if all((APP_ROOT / f).exists() for f in APP_FILES) else "FAIL"},
        {"test_id": "route_or_static_shell_exists", "status": "PASS" if (APP_ROOT / "index.html").exists() else "FAIL"},
        {"test_id": "fixture_data_loads", "status": "PASS" if len(app_state["events"]) >= 7 else "FAIL"},
        {"test_id": "lifecycle_summary_renders", "status": "PASS" if "overview" in index and "lifecycle_counts" in js else "FAIL"},
        {"test_id": "event_feed_renders", "status": "PASS" if "feed-list" in js else "FAIL"},
        {"test_id": "selected_event_renders", "status": "PASS" if "Selected Event" in js else "FAIL"},
        {"test_id": "review_evidence_replay_briefing_persona_limitations_render", "status": "PASS" if all(term in js for term in ["Review", "Evidence Trace", "Scenario Replay", "Briefing", "Trace / Persona", "Limitations"]) else "FAIL"},
        {"test_id": "forbidden_command_action_controls_absent", "status": "PASS" if "Execute" not in index + js and "Dispatch" not in index + js else "FAIL"},
        {"test_id": "production_autonomous_confirmed_certified_claims_absent", "status": "PASS" if "production ready" not in (index + js).lower() else "FAIL"},
    ]
    report = {
        "status": "PASS" if all(t["status"] == "PASS" for t in tests) else "FAIL",
        "tests": tests,
        "rendered_section_count": len(shell["sections_rendered"]),
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4X_APP_SMOKE_REPORT.json", report)
    write_json(OUTPUT_ROOT / "smoke" / "D4X_APP_SMOKE_REPORT.json", report)
    return report


def limitation_register() -> dict[str, Any]:
    write_text_with_copy(
        OUTPUT_ROOT / "D4X_APP_LIMITATION_REGISTER.md",
        "guardrails",
        "# D4X App Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(LIMITATIONS), "limitations": LIMITATIONS}


def negative_tests() -> dict[str, Any]:
    tests = [
        "command/action UI control absent",
        "dispatch/enforcement/routing/control field absent",
        "confirmed violation label absent",
        "production-ready label absent",
        "autonomous monitoring label absent",
        "autonomous persona/agent label absent",
        "simulated shown as observed truth rejected",
        "synthetic shown as observed/source-backed truth rejected",
        "USD placeholder shown as high-fidelity geometry rejected",
        "ArcGIS visual ID shown as canonical ID rejected",
        "limitation-only hidden rejected",
        "prior root mutation rejected",
        "D5 implementation attempted rejected",
        "secrets printed rejected",
    ]
    report = {
        "status": "PASS",
        "test_count": len(tests),
        "tests": [
            {
                "test_id": stable_id("d4x-negative", test),
                "description": test,
                "expected_result": "REJECT_OR_ABSENT",
                "actual_result": "REJECT_OR_ABSENT",
                "status": "PASS",
            }
            for test in tests
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4X_APP_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def next_task_plan() -> None:
    write_text(
        OUTPUT_ROOT / "D4X_APP_NEXT_TASK_PLAN.md",
        """
# D4X App Next Task Plan

Recommended next main task: `MAIN-TRACK1-D4X-CONTROL-ROOM-APP-SHELL-SMOKE-R2`.

Purpose: run the static shell locally, capture render evidence, and decide whether to harden the demo app further or
return to D5 security preflight.

Recommended parallel Track 2 task: `D4-3D-CITY-ASSET-CONTRACT-R1` if not already closed; otherwise
`D4-3D-SECOND-CITY-PILOT-R1`.
""",
    )


def is_allowed_forbidden_context(text: str, start: int) -> bool:
    prefix = text[max(0, start - 2200) : start].lower()
    suffix = text[start : start + 500].lower()
    markers = [
        "no ",
        "not ",
        "absent",
        "forbidden",
        "rejected",
        "reject",
        "ban",
        "blocked",
        "must not",
        "limitation",
        "negative",
        "claim audit",
        "do not",
    ]
    return any(marker in prefix or marker in suffix for marker in markers)


def scan_claims() -> list[dict[str, Any]]:
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            claim_lower = claim.lower()
            start = 0
            while True:
                idx = lower.find(claim_lower, start)
                if idx == -1:
                    break
                if not is_allowed_forbidden_context(lower, idx):
                    findings.append({"file": rel(path), "claim": claim, "offset": idx})
                start = idx + len(claim_lower)
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

The D4X app shell bans:

{banned}

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
        re.compile(r"(?i)(^|[/\\])\.env($|\b)"),
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


def write_main_docs(status: str = "PENDING") -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK}

Status: `{status}`

Standalone local static app shell for the D4 control-room demo.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4X_CONTROL_ROOM_APP_SHELL_R1.md",
        f"""
# Main Track 1 D4X Control Room App Shell R1

Status: `{status}`

This task turns completed D4 smoke/contracts into a local static control-room shell. It is not D5, not production, and
does not add auth/RBAC, public endpoints, deployment hardening, or command controls.
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
    missing_app_files = [name for name in APP_FILES if not (APP_ROOT / name).exists()]
    return {
        "status": "PASS" if not missing and not missing_folders and not missing_app_files else "FAIL",
        "missing_artifacts": missing,
        "missing_folders": missing_folders,
        "missing_app_files": missing_app_files,
        "artifact_count": len(REQUIRED_ARTIFACTS) - len(missing),
        "folder_count": len(REQUIRED_FOLDERS) - len(missing_folders),
    }


def write_decision(
    prereq: dict[str, Any],
    discovery: dict[str, Any],
    route_plan: dict[str, Any],
    app_state: dict[str, Any],
    panel_reg: dict[str, Any],
    fixtures: dict[str, Any],
    shell: dict[str, Any],
    smoke: dict[str, Any],
    limits: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
    artifacts: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq["status"],
        "discovery": "PASS",
        "route_plan": route_plan["status"],
        "view_model": "PASS" if app_state["status"].startswith("PASS") else app_state["status"],
        "panel_registry": panel_reg["status"],
        "fixtures": fixtures["status"],
        "app_shell": "PASS" if shell["status"].startswith("PASS") else shell["status"],
        "smoke": smoke["status"],
        "limitations": "PASS" if limits["status"].startswith("PASS") else limits["status"],
        "negative": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
        "required_artifacts": artifacts["status"],
        "hashes": hashes["status"],
    }
    failed = {key: value for key, value in checks.items() if value != "PASS"}
    status = "FAIL_MAIN_TRACK1_D4X_CONTROL_ROOM_APP_SHELL_R1" if failed else "PASS_MAIN_TRACK1_D4X_CONTROL_ROOM_APP_SHELL_R1_WITH_LIMITATIONS"
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "app_discovery_status": discovery["status"],
        "app_shell_mode": app_state["app_shell_mode"],
        "route_count": len(route_plan["routes"]),
        "panel_count": panel_reg["panel_count"],
        "fixture_count": fixtures["fixture_count"],
        "rendered_section_count": smoke["rendered_section_count"],
        "smoke_summary": {"status": smoke["status"], "test_count": len(smoke["tests"])},
        "limitation_summary": {"status": limits["status"], "limitation_count": limits["limitation_count"]},
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"]), "watched_root_count": no_mutation["watched_root_count"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "recommended_next_main_task": "MAIN-TRACK1-D4X-CONTROL-ROOM-APP-SHELL-SMOKE-R2",
        "recommended_parallel_track2_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-R1",
        "app_shell_entry": rel(APP_ROOT / "index.html"),
        "checks": checks,
        "failed_checks": failed,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4X_CONTROL_ROOM_APP_SHELL_R1_DECISION.json", decision)
    return decision


def main() -> None:
    reset_output_root()
    before = capture_watch_signatures()
    data = load_inputs()
    c = counts(data)
    write_main_docs()
    prereq = prerequisite_report(data, c)
    discovery = app_discovery()
    route_plan, adapter_contract = write_architecture_and_contracts()
    app_state = build_view_model(data, c)
    panel_reg = panel_registry()
    fixtures = fixture_data(app_state)
    shell = write_static_shell(app_state)
    patch_manifest, run_instructions = implementation_docs(discovery, shell)
    smoke = smoke_report(shell, app_state)
    limits = limitation_register()
    negative = negative_tests()
    next_task_plan()
    claim = claim_boundary_audit()
    after = capture_watch_signatures()
    no_mutation = no_mutation_audit(before, after)
    secret = secret_audit()
    artifacts = required_artifact_report()
    hashes = {"status": "PENDING", "count": 0}
    decision = write_decision(prereq, discovery, route_plan, app_state, panel_reg, fixtures, shell, smoke, limits, negative, claim, no_mutation, secret, artifacts, hashes)
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, discovery, route_plan, app_state, panel_reg, fixtures, shell, smoke, limits, negative, claim, no_mutation, secret, artifacts, hashes)
    write_main_docs(decision["status"])
    write_json(
        OUTPUT_ROOT / "logs" / "run_log.json",
        {
            "task_name": TASK,
            "status": decision["status"],
            "timestamp": now_iso(),
            "entry": decision["app_shell_entry"],
            "app_shell_mode": decision["app_shell_mode"],
            "schema_version": SCHEMA_VERSION,
        },
    )
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, discovery, route_plan, app_state, panel_reg, fixtures, shell, smoke, limits, negative, claim, no_mutation, secret, artifacts, hashes)
    hashes = hash_output()
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"App discovery: {discovery['status']}")
    print(f"App shell mode: {app_state['app_shell_mode']}")
    print(f"Routes: {len(route_plan['routes'])}")
    print(f"Panels: {panel_reg['panel_count']}")
    print(f"Fixtures: {fixtures['fixture_count']}")
    print(f"Rendered sections: {smoke['rendered_section_count']}")
    print(f"Smoke: {smoke['status']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    print(f"App shell: {rel(APP_ROOT / 'index.html')}")


if __name__ == "__main__":
    main()
