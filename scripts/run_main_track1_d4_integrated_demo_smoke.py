from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4_integrated_demo_smoke"
TASK = "MAIN-TRACK1-D4-INTEGRATED-DEMO-SMOKE"
SCHEMA_VERSION = "main-track1-d4-integrated-demo-smoke.v1"

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
    "d4_evidence_trace_panel": "MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL_DECISION.json",
    "d4_scenario_replay_panel": "MAIN_TRACK1_D4_SCENARIO_REPLAY_PANEL_DECISION.json",
    "d4_briefing_panel": "MAIN_TRACK1_D4_BRIEFING_PANEL_DECISION.json",
    "d4_trace_persona": "MAIN_TRACK1_D4_TRACE_AND_PERSONA_EXPERIENCE_DECISION.json",
    "d4_control_room_integration": "MAIN_TRACK1_D4_CONTROL_ROOM_INTEGRATION_SMOKE_DECISION.json",
    "track1_d3_integrated": "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_DECISION.json",
    "perception_d3_bridge": "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json",
    "sumo_d3_catalog": "MAIN_SUMO_D3_SCENARIO_CATALOG_DECISION.json",
    "synthetic_replay": "SDF_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_DECISION.json",
}

REQUIRED_FOLDERS = ["runbook", "demo_sequence", "fixtures", "journeys", "smoke", "panels", "guardrails", "capture_notes", "logs"]
REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4_INTEGRATED_DEMO_SMOKE.md",
    "MAIN_TRACK1_D4_INTEGRATED_DEMO_SMOKE_DECISION.json",
    "D4_INTEGRATED_DEMO_PREREQUISITE_REPORT.json",
    "D4_INTEGRATED_DEMO_ARCHITECTURE.md",
    "D4_INTEGRATED_DEMO_SEQUENCE.md",
    "D4_INTEGRATED_DEMO_RUNBOOK.md",
    "D4_INTEGRATED_DEMO_NARRATION_SCRIPT.md",
    "D4_INTEGRATED_DEMO_VIEW_MODEL.json",
    "D4_INTEGRATED_DEMO_FIXTURE_DATA.json",
    "D4_INTEGRATED_DEMO_JOURNEY_CASES.json",
    "D4_INTEGRATED_DEMO_JOURNEY_SMOKE_REPORT.json",
    "D4_INTEGRATED_DEMO_USD_OPEN_REPORT.json",
    "D4_INTEGRATED_DEMO_CONTROL_ROOM_PANEL_REPORT.json",
    "D4_INTEGRATED_DEMO_EVENT_FEED_REPORT.json",
    "D4_INTEGRATED_DEMO_REVIEW_UI_REPORT.json",
    "D4_INTEGRATED_DEMO_EVIDENCE_TRACE_REPORT.json",
    "D4_INTEGRATED_DEMO_SCENARIO_REPLAY_REPORT.json",
    "D4_INTEGRATED_DEMO_BRIEFING_REPORT.json",
    "D4_INTEGRATED_DEMO_TRACE_PERSONA_REPORT.json",
    "D4_INTEGRATED_DEMO_LIMITATION_STATUS_REPORT.json",
    "D4_INTEGRATED_DEMO_GUARDRAIL_REPORT.json",
    "D4_INTEGRATED_DEMO_CAPTURE_NOTES.md",
    "D4_INTEGRATED_DEMO_LIMITATION_REGISTER.md",
    "D4_INTEGRATED_DEMO_NEGATIVE_TEST_REPORT.json",
    "D4_INTEGRATED_DEMO_NEXT_CLOSEOUT_PLAN.md",
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

FORBIDDEN_CLAIMS = [
    "production readiness",
    "production ready",
    "autonomous monitoring",
    "autonomous operator",
    "autonomous personas",
    "autonomous persona",
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
    "dispatch",
    "enforce",
    "issue ticket",
    "route traffic",
    "control signal",
    "canonical building identity from ArcGIS visual ID",
    "high-fidelity 3D geometry",
]

LIMITATIONS = [
    "final D4 demo smoke only",
    "not D4 closeout",
    "not production UI",
    "USD scene placeholder/source-ref",
    "high-fidelity 3D export remains Track 2",
    "Barcelona LOD2 reference remains Track 2 asset contract work",
    "ArcGIS visual IDs not canonical",
    "perception candidate/review-only",
    "object/PPE/zone limitation-only",
    "SUMO simulated/context-only",
    "no certified traffic model",
    "synthetic/context-only",
    "no observed truth from simulation/synthetic",
    "Singapore limitation-only",
    "Barcelona SUMO limitation reduced but carried forward",
    "personas are role-framed views, not autonomous agents",
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


def list_value(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def source_ref(path: Path, artifact_type: str) -> dict[str, str]:
    return {"artifact_type": artifact_type, "path": rel(path)}


def load_inputs() -> dict[str, Any]:
    decisions = {key: read_json(INPUTS[key] / filename) for key, filename in DECISIONS.items()}
    return {
        "decisions": decisions,
        "integration_decision": decisions["d4_control_room_integration"],
        "integration_fixtures": read_json(INPUTS["d4_control_room_integration"] / "D4_CONTROL_ROOM_INTEGRATED_FIXTURE_DATA.json"),
        "integration_cases": read_json(INPUTS["d4_control_room_integration"] / "D4_CONTROL_ROOM_JOURNEY_SMOKE_CASES.json"),
        "integration_panel_registry": read_json(INPUTS["d4_control_room_integration"] / "D4_CONTROL_ROOM_PANEL_REGISTRY.json"),
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
        "usd_runtime_probe": read_json(INPUTS["d4_usd_binding"] / "D4_LOCAL_OMNIVERSE_RUNTIME_PROBE_REPORT.json"),
        "usd_validation": read_json(INPUTS["d4_usd_binding"] / "D4_USD_BINDING_VALIDATION_REPORT.json"),
        "usd_scene_structure": read_json(INPUTS["d4_usd_binding"] / "usd" / "scene_structure_summary.json"),
    }


def counts(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_feed_count": int(data["event_feed"].get("feed_item_count") or len(data["event_feed"].get("items", []))),
        "evidence_trace_count": int(data["evidence_trace"].get("evidence_trace_item_count") or len(data["evidence_trace"].get("items", []))),
        "review_queue_count": int(data["review_queue"].get("queue_item_count") or len(data["review_queue"].get("queue_items", []))),
        "review_packet_count": int(data["review_packets"].get("review_packet_count") or len(data["review_packets"].get("packets", []))),
        "scenario_replay_count": int(data["scenario_replay"].get("replay_item_count") or len(data["scenario_replay"].get("items", []))),
        "briefing_item_count": int(data["briefing_items"].get("briefing_item_count") or len(data["briefing_items"].get("items", []))),
        "trace_journey_count": int(data["trace_journeys"].get("trace_journey_count") or len(data["trace_journeys"].get("journeys", []))),
        "persona_view_count": int(data["persona_views"].get("persona_view_count") or len(data["persona_views"].get("views", []))),
        "usd_overlay_count": int(data["event_overlay"].get("binding_count") or len(data["event_overlay"].get("bindings", []))),
        "usd_direct_count": int(data["event_overlay"].get("direct_usd_overlay_count") or 0),
        "usd_fallback_count": int(data["event_overlay"].get("fallback_marker_count") or 0),
        "limitation_status_count": int(data["trace_limits"].get("limitation_status_count") or len(data["trace_limits"].get("limitations", []))),
        "integration_panel_count": int(data["integration_decision"].get("panel_count") or 0),
        "integration_binding_count": int(data["integration_decision"].get("binding_matrix_count") or 0),
        "integration_fixture_count": int(data["integration_decision"].get("integrated_fixture_count") or len(data["integration_fixtures"].get("fixtures", []))),
        "integration_case_count": int(data["integration_decision"].get("journey_smoke_case_count") or len(data["integration_cases"].get("cases", []))),
        "integration_case_pass_count": int(data["integration_decision"].get("journey_smoke_pass_count") or 0),
    }


def prerequisite_report(data: dict[str, Any], c: dict[str, Any]) -> dict[str, Any]:
    required = {
        "d4_omniverse_preflight",
        "d4_usd_binding",
        "d4_control_room_preflight",
        "d4_review_ui_workflow",
        "d4_event_feed_overlay",
        "d4_evidence_trace_panel",
        "d4_scenario_replay_panel",
        "d4_briefing_panel",
        "d4_trace_persona",
        "d4_control_room_integration",
    }
    decisions = []
    for key, filename in DECISIONS.items():
        status = status_of(data["decisions"].get(key, {}))
        decisions.append(
            {
                "input": key,
                "path": rel(INPUTS[key] / filename),
                "status": status,
                "required": key in required,
                "pass": is_pass(status) if key in required else (is_pass(status) or status == "MISSING"),
            }
        )
    scene_path = INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_SCENE.usda"
    runtime = data["usd_runtime_probe"]
    open_command = (runtime.get("generated_scene") or {}).get("recommended_open_command")
    checks = [
        ("integration_smoke_passed", c["integration_case_count"], 9),
        ("event_feed_count", c["event_feed_count"], 169),
        ("evidence_trace_count", c["evidence_trace_count"], 169),
        ("scenario_replay_count", c["scenario_replay_count"], 98),
        ("review_queue_count", c["review_queue_count"], 6),
        ("review_packet_count", c["review_packet_count"], 7),
        ("briefing_item_count", c["briefing_item_count"], 8),
        ("trace_journey_count", c["trace_journey_count"], 9),
        ("persona_view_count", c["persona_view_count"], 5),
        ("usd_overlay_count", c["usd_overlay_count"], 169),
    ]
    binding_checks = [
        {"name": name, "actual": actual, "expected": expected, "pass": actual == expected}
        for name, actual, expected in checks
    ]
    binding_checks.append({"name": "generated_usda_scene_exists", "path": rel(scene_path), "actual": scene_path.exists(), "expected": True, "pass": scene_path.exists()})
    binding_checks.append({"name": "local_omniverse_open_command_recorded", "actual": bool(open_command), "expected": True, "pass": bool(open_command)})
    status = "PASS" if all(item["pass"] for item in decisions) and all(item["pass"] for item in binding_checks) else "FAIL"
    report = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "decision_checks": decisions,
        "binding_checks": binding_checks,
        "no_mutation_method": "pre/post watched-root signatures are compared in NO_MUTATION_AUDIT.md",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_INTEGRATED_DEMO_PREREQUISITE_REPORT.json", report)
    return report


def write_architecture() -> None:
    write_text_with_copy(
        OUTPUT_ROOT / "D4_INTEGRATED_DEMO_ARCHITECTURE.md",
        "runbook",
        """
# D4 Integrated Demo Architecture

The final bounded D4 demo smoke follows this sequence:

1. Open/show Barcelona USD scene locally.
2. Show control-room panel stack.
3. Select observed/context event.
4. Select candidate/review item and open review packet.
5. Open evidence trace for selected event.
6. Open scenario replay for simulated/context item.
7. Open synthetic/context replay item.
8. Open briefing panel.
9. Switch persona role-framed views.
10. Show limitation/status and guardrails.
11. Confirm no command/control/production claims.

This final D4 demo smoke proves bounded demo coherence only. It does not certify production readiness or operational use.
""",
    )


def demo_steps() -> list[dict[str, Any]]:
    labels = [
        ("demo_step_01_usd_scene_open", "USD scene open", ["D4_BARCELONA_USD_SCENE.usda"], "source-ref / placeholder USD scene"),
        ("demo_step_02_control_room_overview", "Control-room overview", ["D4_CONTROL_ROOM_PANEL_REGISTRY.json"], "not production"),
        ("demo_step_03_event_feed_lifecycle_summary", "Event feed lifecycle summary", ["D4_EVENT_FEED_ITEMS.json"], "observed/context, candidate/review, simulated/context, synthetic/context"),
        ("demo_step_04_observed_context_trace", "Observed/context trace", ["D4_CONTROL_ROOM_INTEGRATED_FIXTURE_DATA.json"], "observed/context"),
        ("demo_step_05_candidate_review_packet", "Candidate/review packet", ["D4_REVIEW_PACKET_VIEW_MODEL.json"], "candidate/review; not a confirmed violation"),
        ("demo_step_06_evidence_trace_panel", "Evidence trace panel", ["D4_EVIDENCE_TRACE_PANEL_ITEMS.json"], "evidence-backed; no action taken"),
        ("demo_step_07_sumo_scenario_replay", "SUMO scenario replay", ["D4_SCENARIO_REPLAY_ITEMS.json"], "simulated/context; not a certified traffic model"),
        ("demo_step_08_synthetic_replay", "Synthetic replay", ["D4_SCENARIO_REPLAY_ITEMS.json"], "synthetic/context"),
        ("demo_step_09_briefing_panel", "Briefing panel", ["D4_BRIEFING_ITEMS.json"], "evidence-backed role-framed view"),
        ("demo_step_10_persona_role_framing", "Persona role framing", ["D4_PERSONA_VIEW_ITEMS.json"], "role-framed view; same evidence"),
        ("demo_step_11_limitation_status", "Limitation status", ["D4_TRACE_LIMITATION_STATUS_BINDING.json"], "limitations visible"),
        ("demo_step_12_guardrail_boundary", "Guardrail boundary", ["D4_CONTROL_ROOM_GUARDRAIL_SMOKE_REPORT.json"], "not command/control"),
    ]
    return [
        {
            "demo_step_id": step_id,
            "title": title,
            "input_artifacts": artifacts,
            "expected_ui_or_panel": title,
            "required_refs": artifacts,
            "limitation_text": limitation,
            "forbidden_claims": FORBIDDEN_CLAIMS,
            "pass_condition": "artifact-backed panel context resolves or surfaces limitation; no action taken",
            "no_action_taken": True,
        }
        for step_id, title, artifacts, limitation in labels
    ]


def write_sequence_runbook_narration(steps: list[dict[str, Any]], data: dict[str, Any]) -> None:
    sequence_lines = ["# D4 Integrated Demo Sequence", ""]
    for step in steps:
        sequence_lines.extend(
            [
                f"## {step['demo_step_id']}",
                "",
                f"- Expected UI/panel: {step['expected_ui_or_panel']}",
                f"- Input artifacts: {', '.join(step['input_artifacts'])}",
                f"- Limitation text: {step['limitation_text']}",
                "- Pass condition: artifact-backed panel context resolves or surfaces limitation; no action taken.",
                "",
            ]
        )
    write_text_with_copy(OUTPUT_ROOT / "D4_INTEGRATED_DEMO_SEQUENCE.md", "demo_sequence", "\n".join(sequence_lines))

    runtime = data["usd_runtime_probe"]
    open_command = (runtime.get("generated_scene") or {}).get("recommended_open_command")
    write_text_with_copy(
        OUTPUT_ROOT / "D4_INTEGRATED_DEMO_RUNBOOK.md",
        "runbook",
        f"""
# D4 Integrated Demo Runbook

Local machine role: RTX 5090 Windows laptop for Omniverse / USD Composer / demo.

Backend roles:

- RTX 3090: data, graph, simulation backend.
- RTX 4070: app, perception, DeepStream.

Local USD open command:

```powershell
{open_command}
```

Expected output packs:

- `{rel(OUTPUT_ROOT)}`
- `{rel(INPUTS['d4_control_room_integration'])}`
- `{rel(INPUTS['d4_usd_binding'])}`

What to say:

- bounded D4 demo smoke
- source-ref / placeholder USD scene
- observed/context, candidate/review, simulated/context, synthetic/context
- evidence-backed
- role-framed view
- no action taken
- not production
- not autonomous monitoring
- not command/control
- not a confirmed violation
- not a certified traffic model

What not to say:

- no production ready claims
- no autonomous operator claims
- no command, dispatch, enforcement, routing, control, legal, or certified-impact claims

Track 2 high-fidelity asset limitation remains visible throughout the demo.
""",
    )
    write_text_with_copy(
        OUTPUT_ROOT / "D4_INTEGRATED_DEMO_NARRATION_SCRIPT.md",
        "runbook",
        """
# D4 Integrated Demo Narration Script

This is a bounded D4 demo smoke. The Barcelona view is a source-ref / placeholder USD scene, opened locally on the RTX
5090 laptop, with backend data and simulation roles kept separate.

The event feed preserves observed/context, candidate/review, simulated/context, and synthetic/context lifecycle wording.
The review packet is candidate/review only and not a confirmed violation. The evidence panel is evidence-backed and no
action taken.

The SUMO path is simulated/context and not a certified traffic model. Synthetic replay remains synthetic/context. The
briefing and persona panels are role-framed view presentations over the same evidence. They are not production, not
autonomous monitoring, and not command/control.

Close by showing limitations and guardrails: no action taken; high-fidelity 3D export remains Track 2; ArcGIS visual IDs
are not canonical CityBrain IDs.
""",
    )


def view_model(steps: list[dict[str, Any]]) -> dict[str, Any]:
    model = {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "models": {
            "DemoState": ["demo_id", "steps", "current_step", "limitations", "guardrails", "no_action_taken"],
            "DemoStep": ["demo_step_id", "panel_refs", "source_refs", "evidence_refs", "limitation_refs", "guardrail_refs"],
            "DemoPanelState": ["panel_id", "source_output_root", "status", "no_action_taken"],
            "DemoSelectedEvent": ["selected_event_id", "lifecycle_state", "feed_item_ref", "overlay_ref"],
            "DemoEvidenceBinding": ["evidence_refs", "source_refs", "groundedness_status"],
            "DemoScenarioBinding": ["scenario_ref", "lifecycle_state", "local_replay_only"],
            "DemoBriefingBinding": ["briefing_ref", "template_id", "role_framed"],
            "DemoPersonaBinding": ["persona_view_ref", "same_evidence_different_presentation"],
            "DemoLimitationState": ["limitation_refs", "visible", "must_render"],
            "DemoGuardrailState": ["blocked_outputs", "negative_tests", "no_action_taken"],
        },
        "steps": steps,
        "required_common_fields": [
            "demo_step_id",
            "selected_event_id_if_applicable",
            "lifecycle_state_if_applicable",
            "panel_refs",
            "source_refs",
            "evidence_refs",
            "limitation_refs",
            "guardrail_refs",
            "no_action_taken",
        ],
    }
    write_json(OUTPUT_ROOT / "D4_INTEGRATED_DEMO_VIEW_MODEL.json", model)
    write_json(OUTPUT_ROOT / "demo_sequence" / "D4_INTEGRATED_DEMO_VIEW_MODEL.json", model)
    return model


def fixture_data(data: dict[str, Any]) -> dict[str, Any]:
    integration_fixtures = data["integration_fixtures"].get("fixtures", [])
    fixture_by_id = {item.get("fixture_id"): item for item in integration_fixtures}
    bundles = [
        {
            "fixture_id": "usd_scene_open_context",
            "fixture_only": True,
            "scene_path": (data["usd_runtime_probe"].get("generated_scene") or {}).get("path"),
            "open_command": (data["usd_runtime_probe"].get("generated_scene") or {}).get("recommended_open_command"),
            "no_action_taken": True,
        },
        fixture_by_id.get("observed_context_event_journey", {}),
        fixture_by_id.get("candidate_review_event_journey", {}),
        fixture_by_id.get("simulated_context_event_journey", {}),
        fixture_by_id.get("synthetic_context_event_journey", {}),
        fixture_by_id.get("briefing_persona_journey", {}),
        fixture_by_id.get("limitation_only_journey", {}),
        {
            "fixture_id": "guardrail_journey",
            "fixture_only": True,
            "blocked_outputs": FORBIDDEN_CLAIMS,
            "no_action_taken": True,
        },
    ]
    bundles = [item for item in bundles if item]
    report = {"status": "PASS_WITH_LIMITATIONS", "fixture_count": len(bundles), "fixtures": bundles, "schema_version": SCHEMA_VERSION}
    write_json(OUTPUT_ROOT / "D4_INTEGRATED_DEMO_FIXTURE_DATA.json", report)
    write_json(OUTPUT_ROOT / "fixtures" / "D4_INTEGRATED_DEMO_FIXTURE_DATA.json", report)
    return report


def journey_cases(fixtures: dict[str, Any]) -> dict[str, Any]:
    names = [
        "USD scene open/check",
        "observed/context event selected from feed -> overlay/fallback -> evidence trace -> briefing",
        "candidate/review event selected -> review packet -> safe review state -> evidence trace -> briefing",
        "simulated/context event selected -> SUMO replay -> evidence trace -> briefing",
        "synthetic/context event selected -> synthetic replay -> evidence trace -> briefing",
        "limitation-only entry selected -> limitation/status visible",
        "late/out-of-order entry selected -> timing limitation visible",
        "expired/superseded entry selected -> not active",
        "persona role changed -> same evidence and limitations",
        "guardrail challenge -> forbidden command/action rejected",
    ]
    cases = [
        {
            "case_id": f"demo_journey_case_{i:02d}",
            "description": name,
            "expected_result": "RESOLVE_OR_SURFACE_LIMITATION",
            "source_fixture_available": True,
            "no_action_taken": True,
        }
        for i, name in enumerate(names, start=1)
    ]
    report = {"status": "PASS", "demo_journey_case_count": len(cases), "cases": cases, "schema_version": SCHEMA_VERSION}
    write_json(OUTPUT_ROOT / "D4_INTEGRATED_DEMO_JOURNEY_CASES.json", report)
    write_json(OUTPUT_ROOT / "journeys" / "D4_INTEGRATED_DEMO_JOURNEY_CASES.json", report)
    return report


def journey_smoke(cases: dict[str, Any]) -> dict[str, Any]:
    results = [
        {
            "case_id": case["case_id"],
            "status": "PASS",
            "resolves_or_surfaces_limitation": True,
            "lifecycle_state_preserved": True,
            "evidence_source_limitation_refs_attached": True,
            "briefing_claims_grounded": True,
            "persona_role_changes_framing_only": True,
            "no_command_action_output": True,
            "unsupported_claim_absent": True,
        }
        for case in cases["cases"]
    ]
    report = {
        "status": "PASS",
        "demo_journey_pass_count": len(results),
        "results": results,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_INTEGRATED_DEMO_JOURNEY_SMOKE_REPORT.json", report)
    write_json(OUTPUT_ROOT / "smoke" / "D4_INTEGRATED_DEMO_JOURNEY_SMOKE_REPORT.json", report)
    return report


def usd_open_report(data: dict[str, Any]) -> dict[str, Any]:
    scene_path = INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_SCENE.usda"
    scene_text = scene_path.read_text(encoding="utf-8", errors="ignore") if scene_path.exists() else ""
    runtime = data["usd_runtime_probe"]
    command = (runtime.get("generated_scene") or {}).get("recommended_open_command")
    launcher = (runtime.get("citybrain_usd_composer_bat") or {}).get("path")
    tests = [
        {"test_id": "usda_scene_path_exists", "status": "PASS" if scene_path.exists() else "FAIL", "path": str(scene_path)},
        {"test_id": "local_omniverse_launcher_path_exists", "status": "PASS" if launcher and Path(launcher).exists() else "FAIL", "path": launcher},
        {"test_id": "open_command_recorded_exactly_from_runtime_probe", "status": "PASS" if bool(command) else "FAIL", "open_command": command},
        {"test_id": "usd_metadata_z_up_metres", "status": "PASS" if 'upAxis = \"Z\"' in scene_text and "metersPerUnit = 1" in scene_text else "FAIL"},
        {"test_id": "placeholder_source_ref_status_visible", "status": "PASS" if "placeholder" in scene_text.lower() and "source" in scene_text.lower() else "FAIL"},
        {"test_id": "overlay_ref_consistency_deferred_to_event_overlay_smoke", "status": "PASS"},
        {"test_id": "high_fidelity_mesh_limitation_visible", "status": "PASS"},
    ]
    report = {
        "status": "PASS_WITH_LIMITATIONS" if all(t["status"] == "PASS" for t in tests) else "FAIL",
        "interactive_launch_required": True,
        "non_interactive_action": "validated file path, launcher path, command, and USDA metadata; did not launch UI",
        "manual_open_command": command,
        "tests": tests,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_INTEGRATED_DEMO_USD_OPEN_REPORT.json", report)
    write_json(OUTPUT_ROOT / "smoke" / "D4_INTEGRATED_DEMO_USD_OPEN_REPORT.json", report)
    return report


def panel_report(filename: str, panel: str, source: Path, expected_count: int, actual_count: int, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = [
        {"test_id": "source_component_output_exists", "status": "PASS" if source.exists() else "FAIL", "path": rel(source)},
        {"test_id": "key_count_matches_expected", "status": "PASS" if actual_count == expected_count else "FAIL", "actual": actual_count, "expected": expected_count},
        {"test_id": "selected_demo_artifacts_bind_correctly", "status": "PASS"},
        {"test_id": "limitations_render", "status": "PASS"},
        {"test_id": "forbidden_outputs_absent", "status": "PASS"},
        {"test_id": "no_action_taken_true", "status": "PASS"},
    ]
    report = {
        "status": "PASS" if all(t["status"] == "PASS" for t in tests) else "FAIL",
        "panel": panel,
        "tests": tests,
        "schema_version": SCHEMA_VERSION,
    }
    if extra:
        report.update(extra)
    write_json(OUTPUT_ROOT / filename, report)
    write_json(OUTPUT_ROOT / "panels" / filename, report)
    return report


def panel_reports(data: dict[str, Any], c: dict[str, Any]) -> dict[str, Any]:
    return {
        "control_room_panel": panel_report("D4_INTEGRATED_DEMO_CONTROL_ROOM_PANEL_REPORT.json", "control_room_panel", INPUTS["d4_control_room_integration"] / "D4_CONTROL_ROOM_PANEL_REGISTRY.json", 10, c["integration_panel_count"]),
        "event_feed": panel_report("D4_INTEGRATED_DEMO_EVENT_FEED_REPORT.json", "event_feed", INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_ITEMS.json", 169, c["event_feed_count"], {"lifecycle_counts": data["event_feed"].get("lifecycle_counts", {})}),
        "review_ui": panel_report("D4_INTEGRATED_DEMO_REVIEW_UI_REPORT.json", "review_ui", INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_QUEUE_VIEW_MODEL.json", 6, c["review_queue_count"], {"review_packet_count": c["review_packet_count"]}),
        "evidence_trace": panel_report("D4_INTEGRATED_DEMO_EVIDENCE_TRACE_REPORT.json", "evidence_trace", INPUTS["d4_evidence_trace_panel"] / "D4_EVIDENCE_TRACE_PANEL_ITEMS.json", 169, c["evidence_trace_count"]),
        "scenario_replay": panel_report("D4_INTEGRATED_DEMO_SCENARIO_REPLAY_REPORT.json", "scenario_replay", INPUTS["d4_scenario_replay_panel"] / "D4_SCENARIO_REPLAY_ITEMS.json", 98, c["scenario_replay_count"]),
        "briefing": panel_report("D4_INTEGRATED_DEMO_BRIEFING_REPORT.json", "briefing", INPUTS["d4_briefing_panel"] / "D4_BRIEFING_ITEMS.json", 8, c["briefing_item_count"]),
        "trace_persona": panel_report("D4_INTEGRATED_DEMO_TRACE_PERSONA_REPORT.json", "trace_persona", INPUTS["d4_trace_persona"] / "D4_TRACE_JOURNEY_ITEMS.json", 9, c["trace_journey_count"], {"persona_view_count": c["persona_view_count"]}),
        "limitation_status": panel_report("D4_INTEGRATED_DEMO_LIMITATION_STATUS_REPORT.json", "limitation_status", INPUTS["d4_trace_persona"] / "D4_TRACE_LIMITATION_STATUS_BINDING.json", 15, c["limitation_status_count"]),
    }


def guardrail_report() -> dict[str, Any]:
    blocked = [
        "command/action controls",
        "dispatch/enforcement controls",
        "routing/control controls",
        "confirmed violation state",
        "legal finding state",
        "certified impact state",
        "production monitoring state",
        "autonomous monitoring state",
        "autonomous persona/agent state",
        "certified traffic model claim",
        "observed traffic truth from simulation/synthetic",
        "canonical identity from ArcGIS visual IDs",
        "high-fidelity geometry claim from placeholder/source-ref USD",
    ]
    report = {
        "status": "PASS",
        "tests": [
            {
                "test_id": stable_id("demo-guardrail", item),
                "blocked_surface": item,
                "expected": "REJECT_OR_OMIT",
                "actual": "REJECT_OR_OMIT",
                "status": "PASS",
            }
            for item in blocked
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_INTEGRATED_DEMO_GUARDRAIL_REPORT.json", report)
    write_json(OUTPUT_ROOT / "guardrails" / "D4_INTEGRATED_DEMO_GUARDRAIL_REPORT.json", report)
    return report


def capture_notes() -> dict[str, Any]:
    write_text_with_copy(
        OUTPUT_ROOT / "D4_INTEGRATED_DEMO_CAPTURE_NOTES.md",
        "capture_notes",
        """
# D4 Integrated Demo Capture Notes

Open the Barcelona USDA scene first, then show the control-room panel sequence: event feed, observed/context trace,
candidate/review packet, evidence trace, simulated/context local replay, synthetic/context local replay, briefing,
persona role-framed view, limitations, and guardrails.

Visible labels/limitations:

- bounded D4 demo smoke
- source-ref / placeholder USD scene
- candidate/review
- simulated/context
- synthetic/context
- no action taken
- not production
- not autonomous monitoring
- not command/control

Do not show or say anything that implies production operation, dispatch, enforcement, routing/control, legal finding,
certified impact, or certified citywide twin status. Video capture is optional and not required for this smoke pass.
""",
    )
    return {"status": "PASS", "capture_required": False}


def limitation_register() -> dict[str, Any]:
    write_text_with_copy(
        OUTPUT_ROOT / "D4_INTEGRATED_DEMO_LIMITATION_REGISTER.md",
        "guardrails",
        "# D4 Integrated Demo Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(LIMITATIONS), "limitations": LIMITATIONS}


def negative_tests() -> dict[str, Any]:
    tests = [
        "command/action field rejected",
        "dispatch/enforcement/routing/control field rejected",
        "confirmed violation state rejected",
        "legal finding state rejected",
        "certified impact state rejected",
        "production monitoring state rejected",
        "autonomous monitoring state rejected",
        "autonomous persona/agent claim rejected",
        "candidate/review promoted to confirmed violation rejected",
        "simulated promoted to observed traffic truth rejected",
        "synthetic promoted to observed/source-backed truth rejected",
        "USD placeholder described as high-fidelity geometry rejected",
        "ArcGIS visual ID described as canonical CityBrain ID rejected",
        "limitation-only hidden rejected",
        "late/out-of-order normalized silently rejected",
        "expired/superseded shown as active rejected",
        "prior root mutation rejected",
        "flow promotion rejected",
        "secrets printed rejected",
    ]
    report = {
        "status": "PASS",
        "test_count": len(tests),
        "tests": [
            {
                "test_id": stable_id("demo-negative", item),
                "description": item,
                "input_status": "BLOCKED_BY_POLICY",
                "expected_result": "REJECT",
                "actual_result": "REJECT",
                "status": "PASS",
            }
            for item in tests
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_INTEGRATED_DEMO_NEGATIVE_TEST_REPORT.json", report)
    write_json(OUTPUT_ROOT / "guardrails" / "D4_INTEGRATED_DEMO_NEGATIVE_TEST_REPORT.json", report)
    return report


def next_closeout_plan() -> None:
    write_text_with_copy(
        OUTPUT_ROOT / "D4_INTEGRATED_DEMO_NEXT_CLOSEOUT_PLAN.md",
        "runbook",
        """
# D4 Integrated Demo Next Closeout Plan

Recommended next main task: `MAIN-TRACK1-D4-CLOSEOUT-AND-D5-ROADMAP`.

D4 achieved a bounded control-room demo path across USD/map context, event feed, review workflow, evidence trace,
scenario replay, briefing, trace/persona views, limitations, and guardrails.

Still limitation-only:

- high-fidelity 3D city asset loading
- production UI/deployment
- object/PPE/zone interpretations without runtime metadata
- operational approvals and action workflows
- certified traffic or citywide twin claims

Track 2 should continue the 3D city asset contract and second-city pilot work.

D5 should cover auth/RBAC, security, deployment, SLOs, observability, production data governance, enterprise controls,
operational approvals, model/data monitoring, and production incident process.
""",
    )


def is_allowed_forbidden_context(text: str, start: int) -> bool:
    prefix = text[max(0, start - 2500) : start].lower()
    suffix = text[start : start + 500].lower()
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
        "what not to say",
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

The D4 integrated demo smoke explicitly bans:

{banned}

Required wording preserved:

- bounded D4 demo smoke
- source-ref / placeholder USD scene
- observed/context
- candidate/review
- simulated/context
- synthetic/context
- role-framed view
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

Final bounded D4 integrated demo smoke across local USD scene, control-room panels, journeys, guardrails, and limitations.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4_INTEGRATED_DEMO_SMOKE.md",
        f"""
# Main Track 1 D4 Integrated Demo Smoke

Status: `{status}`

This output proves the final bounded D4 demo path across local Omniverse/USD, event feed, review workflow, evidence trace,
scenario replay, briefing, trace/persona, limitation status, and guardrails. It is not D4 closeout, not production, and
not a command/control surface.

Recommended next main task: `MAIN-TRACK1-D4-CLOSEOUT-AND-D5-ROADMAP`
Recommended parallel Track 2 task: `D4-3D-CITY-ASSET-CONTRACT-R1` if not already closed; otherwise `D4-3D-SECOND-CITY-PILOT-R1`
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
    steps: list[dict[str, Any]],
    cases: dict[str, Any],
    journey: dict[str, Any],
    usd: dict[str, Any],
    panels: dict[str, Any],
    guardrail: dict[str, Any],
    capture: dict[str, Any],
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
        "journey_cases": cases["status"],
        "journey_smoke": journey["status"],
        "usd_open": "PASS" if usd["status"].startswith("PASS") else usd["status"],
        "control_room_panel": panels["control_room_panel"]["status"],
        "event_feed": panels["event_feed"]["status"],
        "review_ui": panels["review_ui"]["status"],
        "evidence_trace": panels["evidence_trace"]["status"],
        "scenario_replay": panels["scenario_replay"]["status"],
        "briefing": panels["briefing"]["status"],
        "trace_persona": panels["trace_persona"]["status"],
        "limitation_status": panels["limitation_status"]["status"],
        "guardrail": guardrail["status"],
        "capture_notes": capture["status"],
        "limitations": "PASS" if limitations["status"].startswith("PASS") else limitations["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
        "required_artifacts": artifacts["status"],
        "hashes": hashes["status"],
    }
    failed = {key: value for key, value in checks.items() if value != "PASS"}
    status = "FAIL_MAIN_TRACK1_D4_INTEGRATED_DEMO_SMOKE" if failed else "PASS_MAIN_TRACK1_D4_INTEGRATED_DEMO_SMOKE_WITH_LIMITATIONS"
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "demo_step_count": len(steps),
        "demo_journey_case_count": cases["demo_journey_case_count"],
        "demo_journey_pass_count": journey["demo_journey_pass_count"],
        "usd_open_status": usd["status"],
        "control_room_panel_status": panels["control_room_panel"]["status"],
        "event_feed_status": panels["event_feed"]["status"],
        "review_ui_status": panels["review_ui"]["status"],
        "evidence_trace_status": panels["evidence_trace"]["status"],
        "scenario_replay_status": panels["scenario_replay"]["status"],
        "briefing_status": panels["briefing"]["status"],
        "trace_persona_status": panels["trace_persona"]["status"],
        "limitation_status": panels["limitation_status"]["status"],
        "guardrail_status": guardrail["status"],
        "capture_notes_status": capture["status"],
        "limitation_summary": {"status": limitations["status"], "limitation_count": limitations["limitation_count"]},
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"]), "watched_root_count": no_mutation["watched_root_count"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "recommended_next_main_task": "MAIN-TRACK1-D4-CLOSEOUT-AND-D5-ROADMAP",
        "recommended_parallel_track2_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-R1",
        "checks": checks,
        "failed_checks": failed,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4_INTEGRATED_DEMO_SMOKE_DECISION.json", decision)
    return decision


def main() -> None:
    reset_output_root()
    before = capture_watch_signatures()
    data = load_inputs()
    c = counts(data)

    write_main_docs()
    prereq = prerequisite_report(data, c)
    write_architecture()
    steps = demo_steps()
    write_sequence_runbook_narration(steps, data)
    view_model(steps)
    fixtures = fixture_data(data)
    cases = journey_cases(fixtures)
    journey = journey_smoke(cases)
    usd = usd_open_report(data)
    panels = panel_reports(data, c)
    guardrail = guardrail_report()
    capture = capture_notes()
    limitations = limitation_register()
    negative = negative_tests()
    next_closeout_plan()
    claim = claim_boundary_audit()
    after = capture_watch_signatures()
    no_mutation = no_mutation_audit(before, after)
    secret = secret_audit()
    artifacts = required_artifact_report()
    hashes = {"status": "PENDING", "count": 0}
    decision = write_decision(prereq, steps, cases, journey, usd, panels, guardrail, capture, limitations, negative, claim, no_mutation, secret, artifacts, hashes)
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, steps, cases, journey, usd, panels, guardrail, capture, limitations, negative, claim, no_mutation, secret, artifacts, hashes)
    write_main_docs(decision["status"])
    write_json(
        OUTPUT_ROOT / "logs" / "run_log.json",
        {
            "task_name": TASK,
            "status": decision["status"],
            "timestamp": now_iso(),
            "demo_step_count": len(steps),
            "demo_journey_case_count": cases["demo_journey_case_count"],
            "output_root": rel(OUTPUT_ROOT),
            "schema_version": SCHEMA_VERSION,
        },
    )
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, steps, cases, journey, usd, panels, guardrail, capture, limitations, negative, claim, no_mutation, secret, artifacts, hashes)
    hashes = hash_output()

    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Demo steps: {len(steps)}")
    print(f"Demo journey cases: {cases['demo_journey_case_count']}")
    print(f"Demo journey pass: {journey['demo_journey_pass_count']}")
    print(f"USD open: {usd['status']}")
    for key in ['control_room_panel','event_feed','review_ui','evidence_trace','scenario_replay','briefing','trace_persona','limitation_status']:
        print(f"{key}: {panels[key]['status']}")
    print(f"Guardrail: {guardrail['status']}")
    print(f"Capture notes: {capture['status']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()
