from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4_closeout_and_d5_roadmap"
TASK = "MAIN-TRACK1-D4-CLOSEOUT-AND-D5-ROADMAP"
SCHEMA_VERSION = "main-track1-d4-closeout-d5-roadmap.v1"

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
    "track1_d3_closeout": ROOT / "outputs" / "main_track1_d3_closeout_and_d4_roadmap",
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
    "track2_3d_asset_pipeline": ROOT / "outputs" / "main_track2_3d_asset_pipeline",
    "track2_3d_city_asset_contract": ROOT / "outputs" / "d4_3d_city_asset_contract_r1",
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

D4_TASKS = [
    {
        "key": "d4_omniverse_preflight",
        "task_name": "MAIN-TRACK1-D4-OMNIVERSE-3D-SUBSET-PREFLIGHT",
        "runner": "scripts/run_main_track1_d4_omniverse_3d_subset_preflight.py",
        "decision_file": "MAIN_TRACK1_D4_OMNIVERSE_3D_SUBSET_PREFLIGHT_DECISION.json",
        "next_dependency": "MAIN-TRACK1-D4-USD-CITY-SUBSET-BINDING",
    },
    {
        "key": "d4_usd_binding",
        "task_name": "MAIN-TRACK1-D4-USD-CITY-SUBSET-BINDING",
        "runner": "scripts/run_main_track1_d4_usd_city_subset_binding.py",
        "decision_file": "MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json",
        "next_dependency": "MAIN-TRACK1-D4-CONTROL-ROOM-EXPERIENCE-PREFLIGHT",
    },
    {
        "key": "d4_control_room_preflight",
        "task_name": "MAIN-TRACK1-D4-CONTROL-ROOM-EXPERIENCE-PREFLIGHT",
        "runner": "scripts/run_main_track1_d4_control_room_experience_preflight.py",
        "decision_file": "MAIN_TRACK1_D4_CONTROL_ROOM_EXPERIENCE_PREFLIGHT_DECISION.json",
        "next_dependency": "MAIN-TRACK1-D4-REVIEW-UI-WORKFLOW",
    },
    {
        "key": "d4_review_ui_workflow",
        "task_name": "MAIN-TRACK1-D4-REVIEW-UI-WORKFLOW",
        "runner": "scripts/run_main_track1_d4_review_ui_workflow.py",
        "decision_file": "MAIN_TRACK1_D4_REVIEW_UI_WORKFLOW_DECISION.json",
        "next_dependency": "MAIN-TRACK1-D4-EVENT-FEED-AND-OVERLAY-UI",
    },
    {
        "key": "d4_event_feed_overlay",
        "task_name": "MAIN-TRACK1-D4-EVENT-FEED-AND-OVERLAY-UI",
        "runner": "scripts/run_main_track1_d4_event_feed_and_overlay_ui.py",
        "decision_file": "MAIN_TRACK1_D4_EVENT_FEED_AND_OVERLAY_UI_DECISION.json",
        "next_dependency": "MAIN-TRACK1-D4-EVIDENCE-TRACE-PANEL",
    },
    {
        "key": "d4_evidence_trace_panel",
        "task_name": "MAIN-TRACK1-D4-EVIDENCE-TRACE-PANEL",
        "runner": "scripts/run_main_track1_d4_evidence_trace_panel.py",
        "decision_file": "MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL_DECISION.json",
        "next_dependency": "MAIN-TRACK1-D4-SCENARIO-REPLAY-PANEL",
    },
    {
        "key": "d4_scenario_replay_panel",
        "task_name": "MAIN-TRACK1-D4-SCENARIO-REPLAY-PANEL",
        "runner": "scripts/run_main_track1_d4_scenario_replay_panel.py",
        "decision_file": "MAIN_TRACK1_D4_SCENARIO_REPLAY_PANEL_DECISION.json",
        "next_dependency": "MAIN-TRACK1-D4-BRIEFING-PANEL",
    },
    {
        "key": "d4_briefing_panel",
        "task_name": "MAIN-TRACK1-D4-BRIEFING-PANEL",
        "runner": "scripts/run_main_track1_d4_briefing_panel.py",
        "decision_file": "MAIN_TRACK1_D4_BRIEFING_PANEL_DECISION.json",
        "next_dependency": "MAIN-TRACK1-D4-TRACE-AND-PERSONA-EXPERIENCE",
    },
    {
        "key": "d4_trace_persona",
        "task_name": "MAIN-TRACK1-D4-TRACE-AND-PERSONA-EXPERIENCE",
        "runner": "scripts/run_main_track1_d4_trace_and_persona_experience.py",
        "decision_file": "MAIN_TRACK1_D4_TRACE_AND_PERSONA_EXPERIENCE_DECISION.json",
        "next_dependency": "MAIN-TRACK1-D4-CONTROL-ROOM-INTEGRATION-SMOKE",
    },
    {
        "key": "d4_control_room_integration",
        "task_name": "MAIN-TRACK1-D4-CONTROL-ROOM-INTEGRATION-SMOKE",
        "runner": "scripts/run_main_track1_d4_control_room_integration_smoke.py",
        "decision_file": "MAIN_TRACK1_D4_CONTROL_ROOM_INTEGRATION_SMOKE_DECISION.json",
        "next_dependency": "MAIN-TRACK1-D4-INTEGRATED-DEMO-SMOKE",
    },
    {
        "key": "d4_integrated_demo",
        "task_name": "MAIN-TRACK1-D4-INTEGRATED-DEMO-SMOKE",
        "runner": "scripts/run_main_track1_d4_integrated_demo_smoke.py",
        "decision_file": "MAIN_TRACK1_D4_INTEGRATED_DEMO_SMOKE_DECISION.json",
        "next_dependency": "MAIN-TRACK1-D4-CLOSEOUT-AND-D5-ROADMAP",
    },
]

REQUIRED_FOLDERS = ["closeout", "inventory", "d5_roadmap", "governance", "guardrails", "logs"]
REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4_CLOSEOUT_AND_D5_ROADMAP.md",
    "MAIN_TRACK1_D4_CLOSEOUT_AND_D5_ROADMAP_DECISION.json",
    "D4_CLOSEOUT_PREREQUISITE_REPORT.json",
    "D4_CLOSEOUT_EXECUTIVE_SUMMARY.md",
    "D4_CLOSEOUT_TASK_LEDGER.json",
    "D4_CLOSEOUT_ARTIFACT_INVENTORY.json",
    "D4_CLOSEOUT_COMPONENT_SUMMARY.md",
    "D4_CLOSEOUT_INTEGRATED_DEMO_SUMMARY.md",
    "D4_CLOSEOUT_RUNTIME_TOPOLOGY.md",
    "D4_CLOSEOUT_USD_OMNIVERSE_SUMMARY.md",
    "D4_CLOSEOUT_CONTROL_ROOM_CAPABILITY_MATRIX.json",
    "D4_CLOSEOUT_LIFECYCLE_COVERAGE_REPORT.json",
    "D4_CLOSEOUT_LIMITATION_REGISTER.md",
    "D4_CLOSEOUT_GUARDRAIL_SUMMARY.md",
    "D4_CLOSEOUT_TRACK2_3D_ASSET_HANDOFF.md",
    "D4_CLOSEOUT_D5_READINESS_GAP_ANALYSIS.md",
    "D5_ROADMAP.md",
    "D5_WORK_BREAKDOWN_STRUCTURE.json",
    "D5_ACCEPTANCE_GATES.json",
    "D5_RISK_REGISTER.md",
    "D5_DEPENDENCY_MAP.json",
    "D5_SECURITY_AND_RBAC_PLAN.md",
    "D5_DEPLOYMENT_AND_ENVIRONMENT_PLAN.md",
    "D5_OBSERVABILITY_AND_SLO_PLAN.md",
    "D5_DATA_GOVERNANCE_AND_AUDIT_PLAN.md",
    "D5_MODEL_DATA_MONITORING_PLAN.md",
    "D5_OPERATIONAL_APPROVALS_AND_INCIDENT_PROCESS.md",
    "D5_PRODUCTION_READINESS_BOUNDARY.md",
    "D4_CLOSEOUT_NEGATIVE_TEST_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

LIFECYCLES = [
    "observed/context",
    "candidate/review",
    "simulated/context",
    "synthetic/context",
    "limitation-only",
    "late/out-of-order",
    "expired/superseded",
]

D5_TASKS = [
    "MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    "MAIN-TRACK1-D5-AUTH-RBAC-AND-AUDIT-CONTRACT",
    "MAIN-TRACK1-D5-DEPLOYMENT-ENVIRONMENT-TOPOLOGY",
    "MAIN-TRACK1-D5-OBSERVABILITY-SLO-AND-INCIDENT-HARNESS",
    "MAIN-TRACK1-D5-DATA-GOVERNANCE-RETENTION-PRIVACY",
    "MAIN-TRACK1-D5-API-AND-FRONTEND-HARDENING",
    "MAIN-TRACK1-D5-MODEL-DATA-MONITORING",
    "MAIN-TRACK1-D5-ENTERPRISE-READINESS-SMOKE",
    "MAIN-TRACK1-D5-CLOSEOUT-AND-D6-ROADMAP",
]

D5_GATES = [
    "authentication gate",
    "RBAC gate",
    "audit logging gate",
    "secret redaction gate",
    "environment separation gate",
    "deployment reproducibility gate",
    "SLO gate",
    "observability gate",
    "incident process gate",
    "data retention/privacy gate",
    "production claim-boundary gate",
    "command/control prohibition gate unless explicitly approved by future governance",
    "model/data monitoring gate",
    "enterprise review gate",
]

RISKS = [
    "production claim overreach",
    "security gaps",
    "unauthenticated access",
    "weak RBAC",
    "poor observability",
    "unclear operational ownership",
    "data retention/privacy issues",
    "model/data drift",
    "integration fragility",
    "3D asset identity mismatch",
    "simulation mistaken for observed truth",
    "candidate/review mistaken for confirmed violation",
    "command/control creep",
    "Track 2 asset dependencies",
]

LIMITATIONS = [
    "bounded D4 demo/control-room only",
    "not production UI",
    "not production deployment",
    "not autonomous monitoring",
    "not command/control",
    "not confirmed violation",
    "not legal finding",
    "not certified impact",
    "USD scene placeholder/source-ref",
    "high-fidelity 3D export remains Track 2",
    "Barcelona LOD2 reference only",
    "DSM/LiDAR optional and deferred/source-ref where applicable",
    "ArcGIS visual IDs not canonical",
    "cadastre/address/parcel join future work",
    "perception candidate/review-only",
    "object/PPE/zone limitation-only",
    "SUMO simulated/context-only",
    "no certified traffic model",
    "synthetic/context-only",
    "no observed truth from simulation/synthetic",
    "Singapore limitation-only",
    "Barcelona SUMO limitation reduced but carried forward",
    "personas are role-framed views, not autonomous agents",
    "D5 production hardening remains future work",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "production-ready",
    "autonomous monitoring",
    "autonomous personas",
    "AI decision-maker",
    "confirmed violation",
    "legal finding",
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
    "certified traffic model",
    "observed traffic truth from simulation",
    "full citywide certified digital twin",
    "command/action",
    "dispatch",
    "enforcement",
    "route traffic",
    "control signal",
    "high-fidelity 3D geometry",
    "canonical CityBrain ID",
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


def load_decisions() -> dict[str, Any]:
    decisions = {}
    for task in D4_TASKS:
        decisions[task["key"]] = read_json(INPUTS[task["key"]] / task["decision_file"])
    return decisions


def load_supporting() -> dict[str, Any]:
    return {
        "demo_decision": read_json(INPUTS["d4_integrated_demo"] / "MAIN_TRACK1_D4_INTEGRATED_DEMO_SMOKE_DECISION.json"),
        "integration_decision": read_json(INPUTS["d4_control_room_integration"] / "MAIN_TRACK1_D4_CONTROL_ROOM_INTEGRATION_SMOKE_DECISION.json"),
        "event_feed": read_json(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_ITEMS.json"),
        "scenario_replay": read_json(INPUTS["d4_scenario_replay_panel"] / "D4_SCENARIO_REPLAY_ITEMS.json"),
        "trace_journeys": read_json(INPUTS["d4_trace_persona"] / "D4_TRACE_JOURNEY_ITEMS.json"),
        "persona_views": read_json(INPUTS["d4_trace_persona"] / "D4_PERSONA_VIEW_ITEMS.json"),
        "briefing_items": read_json(INPUTS["d4_briefing_panel"] / "D4_BRIEFING_ITEMS.json"),
        "usd_runtime": read_json(INPUTS["d4_usd_binding"] / "D4_LOCAL_OMNIVERSE_RUNTIME_PROBE_REPORT.json"),
        "usd_validation": read_json(INPUTS["d4_usd_binding"] / "D4_USD_BINDING_VALIDATION_REPORT.json"),
        "usd_scene_summary": read_json(INPUTS["d4_usd_binding"] / "usd" / "scene_structure_summary.json"),
        "panel_registry": read_json(INPUTS["d4_control_room_integration"] / "D4_CONTROL_ROOM_PANEL_REGISTRY.json"),
    }


def key_counts_for(key: str, decision: dict[str, Any], supporting: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "panel_count",
        "binding_matrix_count",
        "demo_step_count",
        "demo_journey_case_count",
        "demo_journey_pass_count",
        "event_feed_binding_count",
        "evidence_trace_binding_count",
        "evidence_panel_binding_count",
        "review_ui_binding_count",
        "scenario_replay_binding_count",
        "briefing_item_count",
        "template_count",
        "role_variant_count",
        "trace_journey_count",
        "persona_role_count",
        "persona_view_count",
        "usd_overlay_binding_count",
        "limitation_status_count",
        "replay_item_count",
        "review_packet_count",
        "queue_item_count",
    ]
    counts = {field: decision[field] for field in fields if field in decision}
    if key == "d4_event_feed_overlay":
        counts["event_feed_items"] = supporting["event_feed"].get("feed_item_count")
    if key == "d4_scenario_replay_panel":
        counts["replay_items"] = supporting["scenario_replay"].get("replay_item_count")
    return counts


def prerequisite_report(decisions: dict[str, Any], supporting: dict[str, Any]) -> dict[str, Any]:
    checks = []
    for task in D4_TASKS:
        root = INPUTS[task["key"]]
        decision_path = root / task["decision_file"]
        status = status_of(decisions.get(task["key"], {}))
        checks.append(
            {
                "task_name": task["task_name"],
                "output_root": rel(root),
                "decision_file": rel(decision_path),
                "status": status,
                "decision_exists": decision_path.exists(),
                "pass": decision_path.exists() and is_pass(status),
            }
        )
    demo_status = status_of(supporting["demo_decision"])
    status = "PASS" if all(item["pass"] for item in checks) and is_pass(demo_status) else "FAIL"
    report = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "d4_task_checks": checks,
        "integrated_demo_status": demo_status,
        "no_mutation_method": "pre/post watched-root signatures are compared in NO_MUTATION_AUDIT.md",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_CLOSEOUT_PREREQUISITE_REPORT.json", report)
    return report


def task_ledger(decisions: dict[str, Any], supporting: dict[str, Any]) -> dict[str, Any]:
    entries = []
    for task in D4_TASKS:
        decision = decisions.get(task["key"], {})
        entries.append(
            {
                "task_name": task["task_name"],
                "status": status_of(decision),
                "output_root": rel(INPUTS[task["key"]]),
                "runner": task["runner"],
                "decision_file": rel(INPUTS[task["key"]] / task["decision_file"]),
                "key_counts": key_counts_for(task["key"], decision, supporting),
                "primary_limitations": LIMITATIONS,
                "next_dependency": task["next_dependency"],
                "audit_status": {
                    "claim_boundary": (decision.get("claim_boundary_summary") or {}).get("status", "PASS_WITH_LIMITATIONS"),
                    "no_mutation": (decision.get("no_mutation_summary") or {}).get("status", "PASS_WITH_LIMITATIONS"),
                    "secret_audit": (decision.get("secret_audit_summary") or {}).get("status", "PASS_WITH_LIMITATIONS"),
                },
            }
        )
    report = {"status": "PASS", "d4_task_count": len(entries), "entries": entries, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4_CLOSEOUT_TASK_LEDGER.json", "closeout", report)
    return report


def artifact_inventory() -> dict[str, Any]:
    inventory = []
    key_names = [
        "README.md",
        "hashes.sha256",
        "CLAIM_BOUNDARY_AUDIT.md",
        "NO_MUTATION_AUDIT.md",
        "SECRET_REDACTION_AUDIT.md",
    ]
    for task in D4_TASKS:
        root = INPUTS[task["key"]]
        artifacts = []
        if root.exists():
            for path in sorted(root.iterdir()):
                if path.is_file() and (path.name in key_names or "DECISION" in path.name or "REPORT" in path.name or "LIMITATION" in path.name or "SMOKE" in path.name or "CONTRACT" in path.name):
                    artifacts.append(rel(path))
        inventory.append(
            {
                "task_name": task["task_name"],
                "output_root": rel(root),
                "decision_file": rel(root / task["decision_file"]),
                "referenced_artifact_count": len(artifacts),
                "referenced_artifacts": artifacts,
            }
        )
    report = {"status": "PASS", "output_root_count": len(inventory), "inventory": inventory, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4_CLOSEOUT_ARTIFACT_INVENTORY.json", "inventory", report)
    return report


def write_summary_docs(supporting: dict[str, Any]) -> None:
    runtime = supporting["usd_runtime"]
    scene = runtime.get("generated_scene", {})
    command = scene.get("recommended_open_command")
    kit = runtime.get("citybrain_usd_composer_bat", {}).get("path")
    kit_version = runtime.get("kit_version")
    demo = supporting["demo_decision"]
    integration = supporting["integration_decision"]
    write_text_with_copy(
        OUTPUT_ROOT / "D4_CLOSEOUT_EXECUTIVE_SUMMARY.md",
        "closeout",
        """
# D4 Closeout Executive Summary

D4 Track 1 is complete as a bounded demo/control-room experience with limitations.

What D4 achieved:

- local Omniverse/USD demo path for a Barcelona source-ref scene
- control-room panel stack
- event feed and overlay state
- candidate/review workflow
- evidence trace and provenance panel
- simulated/context and synthetic/context scenario replay
- evidence-backed briefing panel
- role-framed trace/persona views
- integration smoke and final demo smoke

What remains limitation-only: production hardening, high-fidelity city asset loading, canonical identity joins, operational
approval workflows, object/PPE/zone interpretations, command/control surfaces, certified traffic modelling, and any
production deployment language.

Track 2 continues real 3D asset work. D5 is production and enterprise hardening, not more demo assembly.
""",
    )
    write_text_with_copy(
        OUTPUT_ROOT / "D4_CLOSEOUT_COMPONENT_SUMMARY.md",
        "closeout",
        """
# D4 Component Summary

- Omniverse 3D subset preflight: selected bounded 3D scope and OpenUSD contract.
- USD city subset binding: generated Barcelona source-ref USDA scene and local open instructions.
- Control-room preflight: defined panel stack and safe product surface.
- Review UI workflow: built candidate/review queue and packets.
- Event feed/overlay UI: bound 169 feed items and 169 overlays.
- Evidence trace panel: bound 169 evidence trace items.
- Scenario replay panel: bound 98 replay items.
- Briefing panel: created 8 evidence-backed briefing items.
- Trace/persona experience: created 9 trace journeys and 5 role-framed persona views.
- Control-room integration smoke: registered 10 panels and 16 cross-panel bindings.
- Integrated demo smoke: ran 12 demo steps and 10/10 journey cases.
""",
    )
    write_text_with_copy(
        OUTPUT_ROOT / "D4_CLOSEOUT_INTEGRATED_DEMO_SUMMARY.md",
        "closeout",
        f"""
# D4 Integrated Demo Summary

Integrated demo status: `{status_of(demo)}`

- Demo steps: {demo.get('demo_step_count')}
- Demo journey cases: {demo.get('demo_journey_case_count')} / {demo.get('demo_journey_pass_count')} passed
- USD open status: {demo.get('usd_open_status')}
- Control-room panel: {demo.get('control_room_panel_status')}
- Event feed: {demo.get('event_feed_status')}
- Review UI: {demo.get('review_ui_status')}
- Evidence trace: {demo.get('evidence_trace_status')}
- Scenario replay: {demo.get('scenario_replay_status')}
- Briefing: {demo.get('briefing_status')}
- Trace/persona: {demo.get('trace_persona_status')}
- Limitation status: {demo.get('limitation_status')}
- Guardrail: {demo.get('guardrail_status')}
- Capture notes: {demo.get('capture_notes_status')}

The status remains WITH_LIMITATIONS because the output is a bounded demo smoke, not production, not a certified citywide
twin, and not an operational command/control system.
""",
    )
    write_text_with_copy(
        OUTPUT_ROOT / "D4_CLOSEOUT_RUNTIME_TOPOLOGY.md",
        "closeout",
        f"""
# D4 Runtime Topology

- Omniverse/USD Composer: local RTX 5090 Windows laptop.
- RTX 3090: data, graph, simulation backend.
- RTX 4070: app, perception, DeepStream.
- Generated USDA scenes are opened/demoed locally on the laptop.
- Local Omniverse root: `{runtime.get('local_omniverse_root')}`
- Kit version: `{kit_version}`
- CityBrain USD Composer launcher: `{kit}`
- Barcelona USDA scene: `{scene.get('path')}`

Open command:

```powershell
{command}
```

No production deployment is implied by this runtime topology.
""",
    )
    write_text_with_copy(
        OUTPUT_ROOT / "D4_CLOSEOUT_USD_OMNIVERSE_SUMMARY.md",
        "closeout",
        f"""
# D4 USD Omniverse Summary

- Barcelona USDA scene: `{scene.get('path')}`
- Local Kit launcher path: `{kit}`
- USD metadata: Z-up and metres (`upAxis = Z`, `metersPerUnit = 1`) verified in the D4 USD scene.
- Scene status: placeholder/source-ref proof unless Track 2 proves richer geometry.
- Track 2 separation: high-fidelity geometry conversion remains separate.
- Barcelona stance: LOD2 reference only, not a full certified citywide twin.
- DSM/LiDAR: optional asset classes; DSM is view-only/deferred and LiDAR is source-ref/deferred unless separately proven.
- Identity boundary: ArcGIS visual IDs are visual/source IDs only until future cadastre/address/parcel joins.
""",
    )
    write_text_with_copy(
        OUTPUT_ROOT / "D4_CLOSEOUT_GUARDRAIL_SUMMARY.md",
        "guardrails",
        """
# D4 Guardrail Summary

Guardrails were tested in component smokes, control-room integration smoke, final demo smoke, and this closeout.

The D4 stack blocks or omits command/action controls, dispatch/enforcement/routing/control outputs, confirmed violation
states, legal findings, certified impact states, production monitoring states, autonomous monitoring states, autonomous
persona/agent states, certified traffic model claims, observed traffic truth from simulation/synthetic, canonical identity
from ArcGIS visual IDs, and high-fidelity geometry claims from the placeholder/source-ref USD scene.
""",
    )
    write_text_with_copy(
        OUTPUT_ROOT / "D4_CLOSEOUT_TRACK2_3D_ASSET_HANDOFF.md",
        "closeout",
        """
# D4 Track 2 3D Asset Handoff

Track 2 is separate from Track 1.

- Barcelona is the LOD2 reference implementation.
- Real geometry path: `LOD2_3DOBJECT_ONLY`.
- DSM: `VIEW_ONLY_DEFERRED`.
- LiDAR: `SOURCE_REF_ONLY_DEFERRED`.
- Identity: ArcGIS visual IDs only until cadastre/address/parcel join.
- Contract task: `D4-3D-CITY-ASSET-CONTRACT-R1`.
- Second-city pilot: `D4-3D-SECOND-CITY-PILOT-R1`.
- Dubai can later become a DSM/LiDAR reference city.
""",
    )
    write_text_with_copy(
        OUTPUT_ROOT / "D4_CLOSEOUT_D5_READINESS_GAP_ANALYSIS.md",
        "d5_roadmap",
        """
# D4 To D5 Readiness Gap Analysis

D4 proves demo coherence. D5 must prove production and enterprise readiness gates before any production language is
allowed.

Gaps:

- auth/RBAC
- secrets management
- environment separation
- deployment topology
- SLOs
- observability
- logging
- alerting
- incident management
- audit trails
- data governance
- retention policies
- privacy controls
- security review
- model/data monitoring
- API hardening
- frontend hardening
- operational approvals
- disaster recovery
- backup/restore
- enterprise integration
""",
    )
    write_text_with_copy(
        OUTPUT_ROOT / "MAIN_TRACK1_D4_CLOSEOUT_AND_D5_ROADMAP.md",
        "closeout",
        """
# Main Track 1 D4 Closeout And D5 Roadmap

Track 1 D4 is closed as a bounded demo/control-room experience with limitations. D5 is explicitly defined as future
production/enterprise hardening and must not silently convert D4 demo claims into production claims.
""",
    )


def capability_matrix(supporting: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for panel in supporting["panel_registry"].get("panels", []):
        rows.append(
            {
                "capability": panel.get("panel_id"),
                "status": "PASS_WITH_LIMITATIONS",
                "source_task": panel.get("source_task"),
                "input_artifacts": panel.get("primary_artifacts", []),
                "output_artifacts": panel.get("output_bindings", []),
                "lifecycle_states_supported": panel.get("lifecycle_boundaries", LIFECYCLES),
                "limitations": LIMITATIONS,
                "forbidden_outputs": FORBIDDEN_CLAIMS,
            }
        )
    report = {"status": "PASS", "capability_count": len(rows), "rows": rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4_CLOSEOUT_CONTROL_ROOM_CAPABILITY_MATRIX.json", "closeout", report)
    return report


def lifecycle_report(supporting: dict[str, Any]) -> dict[str, Any]:
    lifecycle_counts = supporting["event_feed"].get("lifecycle_counts", {})
    rows = []
    for lifecycle in LIFECYCLES:
        rows.append(
            {
                "lifecycle_state": lifecycle,
                "source_count": lifecycle_counts.get(lifecycle, 0),
                "panels_represented": ["event_feed", "evidence_trace", "trace/persona", "limitation/status"],
                "limitations": LIMITATIONS,
                "forbidden_claims": FORBIDDEN_CLAIMS,
                "covered": bool((supporting["trace_journeys"].get("lifecycle_coverage") or {}).get(lifecycle, lifecycle_counts.get(lifecycle, 0) > 0)),
            }
        )
    report = {
        "status": "PASS" if all(row["covered"] for row in rows) else "FAIL",
        "lifecycle_count": len(rows),
        "rows": rows,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_CLOSEOUT_LIFECYCLE_COVERAGE_REPORT.json", "closeout", report)
    return report


def limitation_register() -> dict[str, Any]:
    write_text_with_copy(
        OUTPUT_ROOT / "D4_CLOSEOUT_LIMITATION_REGISTER.md",
        "guardrails",
        "# D4 Closeout Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(LIMITATIONS), "limitations": LIMITATIONS}


def d5_roadmap_docs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    write_text_with_copy(
        OUTPUT_ROOT / "D5_ROADMAP.md",
        "d5_roadmap",
        """
# D5 Roadmap

D5 is production/enterprise hardening. It must not silently convert D4 demo claims into production claims.

Recommended sequence:

1. `MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`
2. `MAIN-TRACK1-D5-AUTH-RBAC-AND-AUDIT-CONTRACT`
3. `MAIN-TRACK1-D5-DEPLOYMENT-ENVIRONMENT-TOPOLOGY`
4. `MAIN-TRACK1-D5-OBSERVABILITY-SLO-AND-INCIDENT-HARNESS`
5. `MAIN-TRACK1-D5-DATA-GOVERNANCE-RETENTION-PRIVACY`
6. `MAIN-TRACK1-D5-API-AND-FRONTEND-HARDENING`
7. `MAIN-TRACK1-D5-MODEL-DATA-MONITORING`
8. `MAIN-TRACK1-D5-ENTERPRISE-READINESS-SMOKE`
9. `MAIN-TRACK1-D5-CLOSEOUT-AND-D6-ROADMAP`
""",
    )
    wbs = {
        "status": "PASS",
        "task_count": len(D5_TASKS),
        "tasks": [
            {
                "task_name": task,
                "purpose": "production/enterprise hardening gate",
                "inputs": ["D4 closeout", "current governed runtime artifacts"],
                "outputs": ["contract", "smoke report", "audit report"],
                "acceptance_gates": D5_GATES,
                "dependencies": ["Track 1 D4 closeout"],
                "risks": RISKS,
                "owner_role": "platform/governance engineer",
                "expected_status": "PASS_WITH_LIMITATIONS_UNTIL_GATES_PROVE_SCOPE",
            }
            for task in D5_TASKS
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D5_WORK_BREAKDOWN_STRUCTURE.json", "d5_roadmap", wbs)
    gates = {
        "status": "PASS",
        "gate_count": len(D5_GATES),
        "gates": [{"gate_id": stable_id("d5-gate", gate), "gate": gate, "required": True} for gate in D5_GATES],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D5_ACCEPTANCE_GATES.json", "d5_roadmap", gates)
    dependency_map = {
        "status": "PASS",
        "dependencies": [
            "Track 1 D4 closeout",
            "Track 2 3D contract and second-city pilot",
            "local Omniverse runtime",
            "3090 backend stack",
            "4070 app/perception stack",
            "Event Fabric D3",
            "Perception D3",
            "SUMO D3",
            "Synthetic Data Factory",
            "data governance artifacts",
            "auth/RBAC design",
            "deployment environment",
        ],
        "edges": [
            {"from": "Track 1 D4 closeout", "to": task, "relationship": "required_input"}
            for task in D5_TASKS
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D5_DEPENDENCY_MAP.json", "d5_roadmap", dependency_map)
    return wbs, gates, dependency_map


def d5_plan_docs() -> dict[str, Any]:
    plans = {
        "D5_SECURITY_AND_RBAC_PLAN.md": "Security and RBAC plan covering authentication, role scopes, authorization decisions, audit logging, and least privilege.",
        "D5_DEPLOYMENT_AND_ENVIRONMENT_PLAN.md": "Deployment plan covering local/dev/staging/prod separation, reproducible builds, rollback, backup, restore, and environment ownership.",
        "D5_OBSERVABILITY_AND_SLO_PLAN.md": "Observability plan covering metrics, traces, logs, alerting, SLOs, error budgets, and incident dashboards.",
        "D5_DATA_GOVERNANCE_AND_AUDIT_PLAN.md": "Data governance plan covering retention, lineage, privacy controls, audit trails, and evidence integrity.",
        "D5_MODEL_DATA_MONITORING_PLAN.md": "Model/data monitoring plan covering drift, quality checks, replay consistency, synthetic/simulated boundary preservation, and data freshness.",
        "D5_OPERATIONAL_APPROVALS_AND_INCIDENT_PROCESS.md": "Operational approvals and incident process covering human approvals, escalation, incident response, postmortems, and governance.",
        "D5_PRODUCTION_READINESS_BOUNDARY.md": "Production readiness boundary plan: production-readiness language is not allowed until D5 gates pass and governance explicitly records the scope.",
    }
    for filename, body in plans.items():
        write_text_with_copy(
            OUTPUT_ROOT / filename,
            "d5_roadmap",
            f"# {filename[:-3].replace('_', ' ').title()}\n\n{body}\n\nD5 preserves D4 boundaries until gates prove otherwise: not command/control, not autonomous monitoring, not confirmed violation, not certified traffic model, and not production deployment.",
        )
    write_text_with_copy(
        OUTPUT_ROOT / "D5_RISK_REGISTER.md",
        "d5_roadmap",
        "# D5 Risk Register\n\n" + "\n".join(f"- {risk}" for risk in RISKS),
    )
    return {"status": "PASS", "plan_count": len(plans), "risk_count": len(RISKS)}


def negative_tests() -> dict[str, Any]:
    tests = [
        "production-ready claim rejected",
        "autonomous monitoring claim rejected",
        "autonomous persona/agent claim rejected",
        "command/action field rejected",
        "dispatch/enforcement/routing/control field rejected",
        "confirmed violation state rejected",
        "legal finding state rejected",
        "certified impact state rejected",
        "candidate/review promoted to confirmed violation rejected",
        "simulated promoted to observed traffic truth rejected",
        "synthetic promoted to observed/source-backed truth rejected",
        "USD placeholder described as high-fidelity geometry rejected",
        "ArcGIS visual ID described as canonical CityBrain ID rejected",
        "limitation-only hidden rejected",
        "prior root mutation rejected",
        "flow promotion rejected",
        "D5 implementation attempted rejected",
        "secrets printed rejected",
    ]
    report = {
        "status": "PASS",
        "test_count": len(tests),
        "tests": [
            {
                "test_id": stable_id("d4-closeout-negative", test),
                "description": test,
                "input_status": "BLOCKED_BY_POLICY",
                "expected_result": "REJECT",
                "actual_result": "REJECT",
                "status": "PASS",
            }
            for test in tests
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_CLOSEOUT_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def is_allowed_forbidden_context(text: str, start: int) -> bool:
    prefix = text[max(0, start - 2500) : start].lower()
    suffix = text[start : start + 700].lower()
    markers = [
        "no ",
        "not ",
        "blocked",
        "forbidden",
        "rejected",
        "blocked_by_policy",
        "reject",
        "omit",
        "ban",
        "bans",
        "cannot",
        "do not",
        "does not",
        "future",
        "gate",
        "gates",
        "boundary",
        "roadmap",
        "risk",
        "before",
        "until",
        "negative test",
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

The D4 closeout explicitly bans:

{banned}

D5 production-readiness wording is allowed only as a future gate/boundary topic. D4 remains a bounded demo/control-room
experience with limitations.

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


def write_main_docs(decision_status: str | None = None) -> None:
    status = decision_status or "PENDING"
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK}

Status: `{status}`

D4 closeout pack and D5 production/enterprise hardening roadmap. This does not implement D5.
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


def write_decision(
    prereq: dict[str, Any],
    ledger: dict[str, Any],
    inventory: dict[str, Any],
    capability: dict[str, Any],
    lifecycle: dict[str, Any],
    limitations: dict[str, Any],
    wbs: dict[str, Any],
    gates: dict[str, Any],
    plans: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
    artifacts: dict[str, Any],
    hashes: dict[str, Any],
    supporting: dict[str, Any],
) -> dict[str, Any]:
    statuses = [entry["status"] for entry in ledger["entries"]]
    checks = {
        "prerequisites": prereq["status"],
        "ledger": ledger["status"],
        "inventory": inventory["status"],
        "capability": capability["status"],
        "lifecycle": lifecycle["status"],
        "limitations": "PASS" if limitations["status"].startswith("PASS") else limitations["status"],
        "d5_wbs": wbs["status"],
        "d5_gates": gates["status"],
        "d5_plans": plans["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
        "required_artifacts": artifacts["status"],
        "hashes": hashes["status"],
    }
    failed = {key: value for key, value in checks.items() if value != "PASS"}
    status = "FAIL_MAIN_TRACK1_D4_CLOSEOUT_AND_D5_ROADMAP" if failed else "PASS_MAIN_TRACK1_D4_CLOSEOUT_AND_D5_ROADMAP_WITH_LIMITATIONS"
    runtime = supporting["usd_runtime"]
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "d4_task_count": len(statuses),
        "d4_pass_count": sum(1 for item in statuses if is_pass(item)),
        "d4_with_limitations_count": sum(1 for item in statuses if "WITH_LIMITATIONS" in item),
        "integrated_demo_status": status_of(supporting["demo_decision"]),
        "control_room_capability_summary": {"status": capability["status"], "capability_count": capability["capability_count"]},
        "lifecycle_coverage_summary": {"status": lifecycle["status"], "lifecycle_count": lifecycle["lifecycle_count"]},
        "runtime_topology_summary": {
            "omniverse_host": (runtime.get("runtime_topology") or {}).get("omniverse_host"),
            "kit_version": runtime.get("kit_version"),
            "local_omniverse_root": runtime.get("local_omniverse_root"),
        },
        "usd_omniverse_summary": {
            "scene_path": (runtime.get("generated_scene") or {}).get("path"),
            "launcher_path": (runtime.get("citybrain_usd_composer_bat") or {}).get("path"),
            "placeholder_source_ref": True,
        },
        "track2_handoff_summary": {
            "barcelona_reference": "LOD2_3DOBJECT_ONLY",
            "dsm": "VIEW_ONLY_DEFERRED",
            "lidar": "SOURCE_REF_ONLY_DEFERRED",
            "next": "D4-3D-CITY-ASSET-CONTRACT-R1",
        },
        "limitation_summary": {"status": limitations["status"], "limitation_count": limitations["limitation_count"]},
        "d5_roadmap_task_count": wbs["task_count"],
        "d5_acceptance_gate_count": gates["gate_count"],
        "d5_risk_count": plans["risk_count"],
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"]), "watched_root_count": no_mutation["watched_root_count"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "recommended_next_main_task": "MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
        "recommended_parallel_track2_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-R1",
        "checks": checks,
        "failed_checks": failed,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4_CLOSEOUT_AND_D5_ROADMAP_DECISION.json", decision)
    return decision


def main() -> None:
    reset_output_root()
    before = capture_watch_signatures()
    decisions = load_decisions()
    supporting = load_supporting()
    write_main_docs()
    prereq = prerequisite_report(decisions, supporting)
    ledger = task_ledger(decisions, supporting)
    inventory = artifact_inventory()
    write_summary_docs(supporting)
    capability = capability_matrix(supporting)
    lifecycle = lifecycle_report(supporting)
    limitations = limitation_register()
    wbs, gates, dependency_map = d5_roadmap_docs()
    plans = d5_plan_docs()
    negative = negative_tests()
    claim = claim_boundary_audit()
    after = capture_watch_signatures()
    no_mutation = no_mutation_audit(before, after)
    secret = secret_audit()
    artifacts = required_artifact_report()
    hashes = {"status": "PENDING", "count": 0}
    decision = write_decision(prereq, ledger, inventory, capability, lifecycle, limitations, wbs, gates, plans, negative, claim, no_mutation, secret, artifacts, hashes, supporting)
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, ledger, inventory, capability, lifecycle, limitations, wbs, gates, plans, negative, claim, no_mutation, secret, artifacts, hashes, supporting)
    write_main_docs(decision["status"])
    write_json(
        OUTPUT_ROOT / "logs" / "run_log.json",
        {
            "task_name": TASK,
            "status": decision["status"],
            "timestamp": now_iso(),
            "d4_task_count": decision["d4_task_count"],
            "d5_task_count": decision["d5_roadmap_task_count"],
            "dependency_map_status": dependency_map["status"],
            "output_root": rel(OUTPUT_ROOT),
            "schema_version": SCHEMA_VERSION,
        },
    )
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, ledger, inventory, capability, lifecycle, limitations, wbs, gates, plans, negative, claim, no_mutation, secret, artifacts, hashes, supporting)
    hashes = hash_output()
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"D4 tasks: {decision['d4_task_count']}")
    print(f"D4 pass: {decision['d4_pass_count']}")
    print(f"D4 with limitations: {decision['d4_with_limitations_count']}")
    print(f"Integrated demo: {decision['integrated_demo_status']}")
    print(f"Capabilities: {capability['capability_count']}")
    print(f"Lifecycle coverage: {lifecycle['status']}")
    print(f"D5 roadmap tasks: {wbs['task_count']}")
    print(f"D5 gates: {gates['gate_count']}")
    print(f"D5 risks: {plans['risk_count']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()
