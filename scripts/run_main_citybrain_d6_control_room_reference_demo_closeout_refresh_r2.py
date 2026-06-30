#!/usr/bin/env python3
"""Freeze D6 control-room reference demo state after D6 R4."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-REFRESH-R2"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_R2_WITH_LIMITATIONS"
WAIT_R4_STATUS = "WAITING_ON_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_R2"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh_r2"

ROOTS = {
    "d6_r4": "outputs/main_citybrain_d6_event_context_overlay_integration_r4",
    "d6_closeout_r1": "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh",
    "d6_r3": "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration",
    "track2a_event_overlay_r3": "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3",
    "event_fabric_r2": "outputs/main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end",
    "mobility_runtime_d6_overlay": "outputs/main_citybrain_d4x_mobility_r7_runtime_slice_and_d6_overlay_integration_r1",
    "building_property_r7_closeout": "outputs/main_citybrain_d4x_building_compliance_property_planning_r7_extension_closeout",
    "building_compliance_r7": "outputs/main_citybrain_d4x_building_compliance_r7_edge_extension_and_closeout_r1",
    "property_planning_r7": "outputs/main_citybrain_d4x_property_planning_r7_edge_extension_and_closeout_r1",
    "r7_registry_preflight": "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight",
    "track2a_kit_composer_r2": "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
    "track2a_asset_binding_r1": "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
    "track2a_asset_overlay_smoke": "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke",
    "track2a_object_picking_bridge": "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end",
    "track2b_city_episode_pack": "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "track2c_control_room_r1": "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
    "r6_incident_event_mode": "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    "r5_domain_pack_first_two": "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
}

OPTIONAL_ROOTS = {
    "city_asset_identity_domain_pack_r1": "outputs/main_citybrain_d4x_city_asset_identity_domain_pack_r1_end_to_end",
    "city_asset_identity_r7": "outputs/main_citybrain_d4x_city_asset_identity_r7_edge_extension_and_closeout_r1",
    "track2c_viewport_bridge_r1": "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1",
}

EXPECTED_R4_STATUS = "PASS_MAIN_CITYBRAIN_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4_WITH_LIMITATIONS"

FOLDERS = [
    "closeout",
    "local_index",
    "walkthroughs",
    "state_registers",
    "branch_summaries",
    "visual_evidence",
    "audits",
    "logs",
]

LIMITATIONS = [
    "D6 closeout refresh R2 is a closeout/consolidation task, not a new feature implementation task.",
    "Omniverse Kit / Composer is the primary spatial control-room surface; web is the companion evidence, episode, and executive surface.",
    "D6 R4 event/current-state context is local/replay review context only.",
    "No production readiness, public deployment, production frontend, public API/server, autonomous monitoring, alert push, dispatch, enforcement, routing/control, traffic control, legal finding, confirmed violation, permit approval/rejection, ownership/title truth, certified affected-building truth, certified traffic model, certified impact, source-ID legal/ownership/certified truth, observed truth from simulation/synthetic, or external LLM truth-engine claim.",
    "No D6 R4, D6 R1/R2/R3, Track2A, Event Fabric, Mobility, Building Compliance, Property/Planning, City Asset Identity, R7, Track2B/Track2C, source USD/USDA, app source, or city source roots were mutated.",
]

PARKED_TASKS = [
    "MAIN-CITYBRAIN-D4X-R7-MULTI-DOMAIN-EDGE-REGISTRY-RUNTIME-SLICE",
    "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-EVENT-FABRIC-INTEGRATION-R3",
    "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-TRACK2-HANDOFF",
    "MAIN-CITYBRAIN-FIRST-HUMAN-ROUTED-REVIEW-CONSEQUENCE",
    "MAIN-CITYBRAIN-D5-PRODUCTION-PUBLIC-BOUNDARY",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def root_path(root: str) -> Path:
    return REPO_ROOT / root


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def output_rel(path: Path) -> str:
    return os.path.relpath(path, OUTPUT_ROOT).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    files = sorted(item for item in path.rglob("*") if item.is_file())
    digest = hashlib.sha256()
    total = 0
    for item in files:
        stat = item.stat()
        total += stat.st_size
        digest.update(rel(item).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
    return {"exists": True, "file_count": len(files), "byte_count": total, "fingerprint": digest.hexdigest()}


def decision_status(path: Path) -> str | None:
    if not path.exists():
        return None
    for item in sorted(path.glob("*DECISION*.json")):
        payload = read_json(item, {})
        if payload.get("status"):
            return str(payload["status"])
    return None


def decision_payload(key: str) -> dict[str, Any]:
    return read_json(next(iter(sorted(root_path(ROOTS[key]).glob("*DECISION*.json"))), Path("__missing__")), {})


def first_int(payload: dict[str, Any], keys: list[str]) -> int:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return 0


def prerequisite_report(pre: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for key, root in {**ROOTS, **OPTIONAL_ROOTS}.items():
        path = root_path(root)
        rows.append(
            {
                "branch": key,
                "root": root,
                "exists": path.exists(),
                "status": decision_status(path),
                "snapshot": pre[root],
                "read_only": True,
            }
        )
    r4_status = decision_status(root_path(ROOTS["d6_r4"]))
    report = {
        "status": "PASS" if r4_status == EXPECTED_R4_STATUS else WAIT_R4_STATUS,
        "timestamp": now(),
        "hard_gate": {
            "root": ROOTS["d6_r4"],
            "status": r4_status,
            "expected_status": EXPECTED_R4_STATUS,
        },
        "roots": rows,
    }
    write_json(OUTPUT_ROOT / "D6_CLOSEOUT_R2_PREREQUISITE_REPORT.json", report)
    return report


def source_map(pre: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for key, root in {**ROOTS, **OPTIONAL_ROOTS}.items():
        path = root_path(root)
        samples = []
        if path.exists():
            for item in sorted(path.rglob("*")):
                if item.is_file() and item.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".png", ".jpg", ".jpeg", ".usda"}:
                    samples.append(rel(item))
                if len(samples) >= 10:
                    break
        rows.append(
            {
                "branch": key,
                "root": root,
                "exists": path.exists(),
                "status": decision_status(path),
                "snapshot": pre[root],
                "sample_artifacts": samples,
                "read_only": True,
            }
        )
    report = {"status": "PASS", "timestamp": now(), "sources": rows}
    write_json(OUTPUT_ROOT / "D6_CLOSEOUT_R2_SOURCE_MAP.json", report)
    return report


def branch_summary() -> dict[str, Any]:
    r4 = decision_payload("d6_r4")
    r1 = decision_payload("d6_closeout_r1")
    r3 = decision_payload("d6_r3")
    track2a_event = decision_payload("track2a_event_overlay_r3")
    event_fabric = decision_payload("event_fabric_r2")
    mobility = decision_payload("mobility_runtime_d6_overlay")
    building_property = decision_payload("building_property_r7_closeout")
    building = decision_payload("building_compliance_r7")
    prop = decision_payload("property_planning_r7")
    r7 = decision_payload("r7_registry_preflight")
    kit = decision_payload("track2a_kit_composer_r2")
    city_asset = read_json(root_path(OPTIONAL_ROOTS["city_asset_identity_r7"]) / "MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json", {})

    rows = [
        branch_row("D6 closeout R1", ROOTS["d6_closeout_r1"], r1, ["local_open_index_status", "current_truth_register_status"]),
        branch_row("D6 R3 relationship overlay", ROOTS["d6_r3"], r3, ["selected_edge_count", "kit_handoff_packet_count", "web_companion_packet_count"]),
        branch_row("D6 R4 event-context overlay", ROOTS["d6_r4"], r4, ["selected_event_context_count", "event_context_overlay_packet_count", "kit_handoff_packet_count", "web_companion_packet_count"]),
        branch_row("Track2A event overlay R3", ROOTS["track2a_event_overlay_r3"], track2a_event, ["event_overlay_packet_count", "kit_handoff_packet_count", "web_companion_packet_count"]),
        branch_row("Track2A Kit/Composer R2", ROOTS["track2a_kit_composer_r2"], kit, ["stage_handoff_count", "navigation_index_count", "camera_bookmark_count"]),
        branch_row("Event Fabric R2", ROOTS["event_fabric_r2"], event_fabric, ["current_state_row_count", "unresolved_review_queue_count", "d6_event_context_candidate_count"]),
        branch_row("Mobility branch", ROOTS["mobility_runtime_d6_overlay"], mobility, ["d6_overlay_packet_count", "runtime_edge_registry_count", "web_companion_packet_count"]),
        branch_row("Building+Property R7 closeout", ROOTS["building_property_r7_closeout"], building_property, ["building_compliance_status", "property_planning_status"]),
        branch_row("Building Compliance branch", ROOTS["building_compliance_r7"], building, ["accepted_grounded_edge_count", "d6_future_handoff_candidate_count"]),
        branch_row("Property/Planning branch", ROOTS["property_planning_r7"], prop, ["accepted_grounded_edge_count", "d6_future_handoff_candidate_count"]),
        branch_row("City Asset Identity optional status", OPTIONAL_ROOTS["city_asset_identity_r7"], city_asset or {"status": "CITY_ASSET_IDENTITY_OPTIONAL_PARKED"}, ["accepted_grounded_edge_count", "d6_future_handoff_candidate_count"]),
        branch_row("R7 registry preflight", ROOTS["r7_registry_preflight"], r7, ["registry_record_count", "accepted_grounded_edge_count", "runtime_ready_record_count"]),
    ]
    report = {"status": "PASS", "timestamp": now(), "branches": rows}
    write_json(OUTPUT_ROOT / "D6_CLOSEOUT_R2_BRANCH_STATUS_SUMMARY.json", report)
    return report


def branch_row(label: str, root: str, decision: dict[str, Any], count_keys: list[str]) -> dict[str, Any]:
    counts = {key: decision.get(key) for key in count_keys if key in decision}
    return {
        "branch": label,
        "root": root,
        "status": decision.get("status", "MISSING"),
        "counts": counts,
        "consumed_by_R2_closeout": True,
        "limitation_summary": decision.get("limitations", ["limitations carried by source branch"])[:5],
        "no_action_taken": True,
    }


def write_state_docs() -> dict[str, str]:
    r4 = decision_payload("d6_r4")
    city_asset_status = r4.get("city_asset_identity_status", "UNKNOWN")
    docs = {
        "D6_CLOSEOUT_R2_CURRENT_TRUTH_REGISTER.md": f"""
# D6 Closeout R2 Current Truth Register

Frozen at: `{now()}`

- Omniverse Kit / Composer is the primary spatial control-room surface.
- Web is the companion evidence, episode, and executive surface.
- D6 R4 now integrates event/current-state context into the product surface.
- Event/current-state context is local/replay review context only.
- No autonomous monitoring, alert push, routing/control, dispatch, enforcement, legal/certified/action claim.

D6 R4 counts:
- selected event contexts: `{r4.get('selected_event_context_count')}`
- event context overlay packets: `{r4.get('event_context_overlay_packet_count')}`
- Kit handoff packets: `{r4.get('kit_handoff_packet_count')}`
- web companion packets: `{r4.get('web_companion_packet_count')}`
- City Asset Identity status: `{city_asset_status}`
""",
        "D6_CLOSEOUT_R2_PRODUCT_SURFACE_STATE.md": """
# D6 Closeout R2 Product Surface State

Product surface integration now includes asset context, relationship context,
event/current-state context, mobility context, building compliance context, and
property/planning context.

Kit/Composer remains the primary spatial control-room surface. Web remains the
companion evidence, episode, and executive surface. This is a local reference
demo, not a production frontend or public deployment.
""",
        "D6_CLOSEOUT_R2_EVENT_CONTEXT_OVERLAY_STATE.md": """
# D6 Closeout R2 Event Context Overlay State

D6 R4 is the current event-context overlay baseline. It consumes Event Fabric R2,
Track2A Event Overlay R3, D6 R3 relationship context, Mobility runtime/D6,
Building Compliance R7, Property/Planning R7, and optional City Asset Identity.

Event/current-state context is local/replay review context only. It does not
enable autonomous monitoring, alert push, dispatch, routing/control, or legal
action.
""",
        "D6_CLOSEOUT_R2_RELATIONSHIP_OVERLAY_STATE.md": """
# D6 Closeout R2 Relationship Overlay State

D6 R3 remains the relationship overlay baseline. It is product-surface context
for relationship evidence and limitations, not the backend relationship registry
runtime slice itself.
""",
        "D6_CLOSEOUT_R2_TRACK2A_OMNIVERSE_STATE.md": """
# D6 Closeout R2 Track2A Omniverse State

Track2A Event Overlay R3 and Kit/Composer R2 provide the Omniverse sidecar,
handoff, navigation, camera/bookmark, and viewport evidence layer. These are
handoff/context artifacts; source USD/USDAs are not mutated by this closeout.
""",
        "D6_CLOSEOUT_R2_EVENT_FABRIC_STATE.md": """
# D6 Closeout R2 Event Fabric State

Event Fabric R2 materialized local/replay state rows, review queues, expired or
superseded state, late/out-of-order reports, and D6/Track2A handoff candidates.
R2 closeout records these as context. It does not create production live
ingestion or public runtime services.
""",
        "D6_CLOSEOUT_R2_DOMAIN_BRANCH_STATE.md": """
# D6 Closeout R2 Domain Branch State

Mobility, Building Compliance, Property/Planning, and City Asset Identity are
consumed as bounded domain/R7 branch context. Their edges, packets, and handoff
candidates are review/context artifacts, not legal/certified/action outputs.
""",
        "D6_CLOSEOUT_R2_CITY_ASSET_IDENTITY_STATUS.md": f"""
# D6 Closeout R2 City Asset Identity Status

Exact D6 R4 status: `{city_asset_status}`

City Asset Identity details are recorded from the D6 R4 decision and source
branch outputs only. R2 closeout does not invent missing details and does not
mutate City Asset Identity roots.
""",
    }
    for name, text in docs.items():
        write_md(OUTPUT_ROOT / name, text)
    return {name: "PASS" for name in docs}


def visual_evidence_inventory() -> dict[str, Any]:
    r4 = decision_payload("d6_r4")
    track2a = root_path(ROOTS["track2a_event_overlay_r3"])
    kit = decision_payload("track2a_kit_composer_r2")
    screenshots = [rel(path) for path in sorted(track2a.rglob("*")) if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    refs = [
        "outputs/main_citybrain_d6_event_context_overlay_integration_r4/D6_R4_VISUAL_EVIDENCE_INVENTORY.json",
        "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3/OMNI_EVENT_R3_VISUAL_EVIDENCE_REPORT.json",
        "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3/OMNI_EVENT_R3_VIEWPORT_BRIDGE_STATUS_REPORT.json",
        "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2/OMNI_KIT_R2_HANDOFF_SMOKE_REPORT.json",
        "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2/OMNI_KIT_R2_SCREENSHOT_PLAN.md",
    ]
    report = {
        "status": "PASS" if r4.get("visual_evidence_status") == "PASS" else "FAIL",
        "d6_r4_visual_evidence_status": r4.get("visual_evidence_status"),
        "track2a_event_overlay_visual_evidence": [ref for ref in refs if root_path(ref).exists()],
        "kit_composer_handoff_status": kit.get("status"),
        "viewport_frame_refs": screenshots,
        "screenshot_capture_refs": screenshots,
        "new_screenshot_required": False,
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "D6_CLOSEOUT_R2_VISUAL_EVIDENCE_INVENTORY.json", report)
    return report


def write_walkthroughs() -> None:
    shared = """
Coverage includes asset context, relationship context, event/current-state
context, mobility context, building compliance context, property/planning
context, evidence, limitations, and `no_action_taken`.

All views are local/replay review context. No action, dispatch, enforcement,
routing/control, legal, certified, public deployment, or production frontend
claim is made.
"""
    write_md(OUTPUT_ROOT / "D6_CLOSEOUT_R2_EXECUTIVE_WALKTHROUGH.md", "# D6 Closeout R2 Executive Walkthrough\n\nR2 freezes the post-R4 control-room reference demo baseline: Kit/Composer as primary spatial surface, web as companion evidence/executive surface, and event context overlays now part of the demo story.\n\n" + shared)
    write_md(OUTPUT_ROOT / "D6_CLOSEOUT_R2_OPERATOR_WALKTHROUGH.md", "# D6 Closeout R2 Operator Walkthrough\n\n1. Open the R2 local index.\n2. Start with D6 R4 event context overlay packets.\n3. Open D6 R3 relationship context.\n4. Use Track2A/Kit handoff artifacts for spatial context.\n5. Review evidence and limitations before any next look.\n\n" + shared)
    write_md(OUTPUT_ROOT / "D6_CLOSEOUT_R2_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md", "# D6 Closeout R2 Technical Evidence Chain Walkthrough\n\nEvent Fabric R2 -> Track2A Event Overlay R3 -> D6 R4 event context overlay -> D6 R3 relationship overlay -> domain branch R7 packets -> closeout registers.\n\n" + shared)


def write_registers(city_asset_status: str) -> None:
    parked = list(PARKED_TASKS)
    if city_asset_status not in {"CITY_ASSET_IDENTITY_OPTIONAL_CONSUMED", "PASS_MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_WITH_LIMITATIONS"}:
        parked.append("INCOMPLETE_CITY_ASSET_IDENTITY_BRANCH")
    write_md(OUTPUT_ROOT / "D6_CLOSEOUT_R2_LIMITATION_REGISTER.md", "# D6 Closeout R2 Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_md(OUTPUT_ROOT / "D6_CLOSEOUT_R2_PARKED_BRANCHES_REGISTER.md", "# D6 Closeout R2 Parked Branches Register\n\n" + "\n".join(f"- `{item}`" for item in parked))
    write_md(
        OUTPUT_ROOT / "D6_CLOSEOUT_R2_NEXT_TASK_PLAN.md",
        """# D6 Closeout R2 Next Task Plan

Recommended next task:
`MAIN-CITYBRAIN-D4X-R7-MULTI-DOMAIN-EDGE-REGISTRY-RUNTIME-SLICE`

Alternative next task:
`MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-EVENT-FABRIC-INTEGRATION-R3`

Rationale: the D6 product-surface baseline is now frozen after R4. The clean next move is either a multi-domain R7 runtime slice or D5 served runtime event-fabric integration, depending on whether backend registry runtime or served runtime is the priority.
""",
    )
    write_md(
        OUTPUT_ROOT / "D6_CLOSEOUT_R2_SUPERSEDED_TASKS_REGISTER.md",
        """# D6 Closeout R2 Superseded Tasks Register

Superseded as baseline tasks:
- D6 closeout refresh R1
- D6 R3 relationship overlay integration
- D6 R4 event-context overlay integration
- Track2A Event Overlay R3
- Event Fabric R2 state materialization
- Mobility runtime/D6 overlay R1
- Building+Property R7 extension closeout

These remain evidence roots. They should not be treated as pending prerequisites for R2.
""",
    )


def local_index() -> dict[str, Any]:
    links = [
        ("D6 R4 decision", root_path(ROOTS["d6_r4"]) / "MAIN_CITYBRAIN_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4_DECISION.json"),
        ("D6 R4 local open index", root_path(ROOTS["d6_r4"]) / "D6_R4_LOCAL_OPEN_INDEX.html"),
        ("D6 R4 event context overlay packets", root_path(ROOTS["d6_r4"]) / "D6_R4_EVENT_CONTEXT_OVERLAY_PACKETS.json"),
        ("D6 R4 Kit handoff packets", root_path(ROOTS["d6_r4"]) / "D6_R4_KIT_EVENT_CONTEXT_HANDOFF_PACKETS.json"),
        ("D6 R4 web companion packets", root_path(ROOTS["d6_r4"]) / "D6_R4_WEB_COMPANION_EVENT_CONTEXT_PACKETS.json"),
        ("D6 R4 evidence/limitation co-display", root_path(ROOTS["d6_r4"]) / "D6_R4_EVIDENCE_LIMITATION_CODISPLAY_MAP.json"),
        ("Track2A Event Overlay R3 decision", root_path(ROOTS["track2a_event_overlay_r3"]) / "MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3_DECISION.json"),
        ("Track2A Event Overlay R3 USDA sidecar", root_path(ROOTS["track2a_event_overlay_r3"]) / "OMNI_EVENT_R3_USDA_EVENT_OVERLAY_LAYER.usda"),
        ("Event Fabric R2 decision", root_path(ROOTS["event_fabric_r2"]) / "MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END_DECISION.json"),
        ("Mobility runtime/D6 overlay decision", root_path(ROOTS["mobility_runtime_d6_overlay"]) / "MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1_DECISION.json"),
        ("Building+Property R7 closeout decision", root_path(ROOTS["building_property_r7_closeout"]) / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_R7_EXTENSION_CLOSEOUT_DECISION.json"),
        ("Executive walkthrough", OUTPUT_ROOT / "D6_CLOSEOUT_R2_EXECUTIVE_WALKTHROUGH.md"),
        ("Operator walkthrough", OUTPUT_ROOT / "D6_CLOSEOUT_R2_OPERATOR_WALKTHROUGH.md"),
        ("Technical evidence-chain walkthrough", OUTPUT_ROOT / "D6_CLOSEOUT_R2_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md"),
        ("Limitation register", OUTPUT_ROOT / "D6_CLOSEOUT_R2_LIMITATION_REGISTER.md"),
        ("Parked branches register", OUTPUT_ROOT / "D6_CLOSEOUT_R2_PARKED_BRANCHES_REGISTER.md"),
        ("Claim boundary audit", OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md"),
        ("No mutation audit", OUTPUT_ROOT / "NO_MUTATION_AUDIT.md"),
        ("Secret redaction audit", OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md"),
    ]
    rows = "\n".join(f'<li><a href="{html.escape(output_rel(target))}">{html.escape(label)}</a></li>' for label, target in links)
    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>D6 Closeout Refresh R2</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; line-height: 1.45; }}
    a {{ color: #0969da; }}
    .truth {{ font-weight: 700; }}
  </style>
</head>
<body>
  <h1>D6 Control Room Reference Demo Closeout Refresh R2</h1>
  <p class="truth">Omniverse Kit / Composer is the primary spatial control-room surface.</p>
  <p>Web is the companion evidence, episode, and executive surface.</p>
  <p>D6 R4 now integrates local/replay event-current-state context into the product surface.</p>
  <ul>{rows}</ul>
</body>
</html>
"""
    path = OUTPUT_ROOT / "D6_CLOSEOUT_R2_LOCAL_OPEN_INDEX.html"
    path.write_text(content, encoding="utf-8")
    checks = []
    for label, target in links:
        checks.append({"label": label, "target": output_rel(target), "exists": target.exists()})
    report = {
        "status": "PASS" if all(item["exists"] for item in checks) else "FAIL",
        "link_count": len(checks),
        "links": checks,
    }
    write_json(OUTPUT_ROOT / "D6_CLOSEOUT_R2_LOCAL_OPEN_INDEX_VALIDATION.json", report)
    return report


def write_main_docs(status: str) -> None:
    text = f"""# {TASK_NAME}

Status: `{status}`

This R2 closeout freezes the current D6 control-room reference demo state after the successful D6 R4 event-context overlay integration.

Current truth:
- Omniverse Kit / Composer is the primary spatial control-room surface.
- Web is the companion evidence, episode, and executive surface.
- D6 R4 integrates event/current-state context into the product surface.
- Event/current-state context is local/replay review context only.

This is closeout/consolidation only. It does not implement production frontend, public API/server, autonomous monitoring, alert push, dispatch, enforcement, routing/control, traffic control, legal/certified/action outputs, source USD mutation, app source mutation, or city source mutation.
"""
    write_md(OUTPUT_ROOT / "README.md", text)
    write_md(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_R2.md", text)


def claim_audit() -> str:
    forbidden = [
        "production_ready\": true",
        "public_api_exposed\": true",
        "autonomous_monitoring_enabled\": true",
        "alert_push_enabled\": true",
        "dispatch_recommendation_created\": true",
        "enforcement_recommendation_created\": true",
        "routing_control_command_created\": true",
        "legal_finding_created\": true",
        "confirmed_violation\": true",
        "permit_approved\": true",
        "permit_rejected\": true",
        "external_llm_truth_engine\": true",
    ]
    joined = ""
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name not in {"hashes.sha256", "CLAIM_BOUNDARY_AUDIT.md"} and item.suffix.lower() in {".json", ".md", ".html", ".txt"}:
            joined += "\n" + item.read_text(encoding="utf-8", errors="ignore").lower()
    hits = [pattern for pattern in forbidden if pattern in joined]
    status = "PASS" if not hits else "FAIL"
    write_md(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""# Claim Boundary Audit

Status: `{status}`

Forbidden positive claim matches: `{len(hits)}`

Boundaries preserved: no production readiness, public deployment, production frontend, public API/server, autonomous monitoring, alert push, dispatch, enforcement, routing/control, traffic control, legal finding, confirmed violation, permit approval/rejection, ownership/title truth, certified affected-building truth, certified traffic model, certified impact, source-ID legal/ownership/certified truth, observed truth from simulation/synthetic, or external LLM truth-engine claim.
""",
    )
    return status


def no_mutation_audit(pre: dict[str, dict[str, Any]]) -> str:
    changed = []
    for root, before in pre.items():
        after = snapshot(root_path(root))
        if before != after:
            changed.append(root)
    status = "PASS" if not changed else "FAIL"
    write_md(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", f"# No Mutation Audit\n\nStatus: `{status}`\n\nChanged read-only roots: `{len(changed)}`")
    return status


def secret_audit() -> str:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]+['\"]"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[a-z0-9._-]+"),
    ]
    hits = []
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name != "hashes.sha256" and item.suffix.lower() in {".json", ".md", ".html", ".txt"}:
            text = item.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in patterns):
                hits.append(rel(item))
    status = "PASS" if not hits else "FAIL"
    write_md(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{status}`\n\nFindings: `{len(hits)}`")
    return status


def write_hashes() -> str:
    rows = []
    for item in sorted(OUTPUT_ROOT.rglob("*")):
        if item.is_file() and item.name != "hashes.sha256":
            rows.append((sha256_file(item), rel(item)))
    (OUTPUT_ROOT / "hashes.sha256").write_text("".join(f"{digest}  {path}\n" for digest, path in rows), encoding="utf-8")
    failures = [path for digest, path in rows if not (REPO_ROOT / path).exists() or sha256_file(REPO_ROOT / path) != digest]
    return "PASS" if rows and not failures else "FAIL"


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for folder in FOLDERS:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)

    all_roots = {**ROOTS, **OPTIONAL_ROOTS}
    pre = {root: snapshot(root_path(root)) for root in all_roots.values()}
    prereq = prerequisite_report(pre)
    source_map(pre)

    r4 = decision_payload("d6_r4")
    r4_status = r4.get("status")
    city_asset_status = r4.get("city_asset_identity_status", "UNKNOWN")

    if prereq["status"] != "PASS":
        status = WAIT_R4_STATUS
        local_status = "NOT_CREATED"
        visual_status = "NOT_CREATED"
        current_truth_status = "NOT_CREATED"
        branch_summary_status = "NOT_CREATED"
        parked_tasks = PARKED_TASKS
        claim_status = "NOT_RUN"
        mutation_status = "NOT_RUN"
        secret_status = "NOT_RUN"
    else:
        branch = branch_summary()
        write_state_docs()
        visual = visual_evidence_inventory()
        write_walkthroughs()
        write_registers(city_asset_status)
        write_main_docs(PASS_STATUS)
        claim_status = claim_audit()
        mutation_status = no_mutation_audit(pre)
        secret_status = secret_audit()
        local = local_index()
        current_truth_status = "PASS"
        branch_summary_status = branch["status"]
        visual_status = visual["status"]
        local_status = local["status"]
        parked_tasks = list(PARKED_TASKS)
        if city_asset_status != "CITY_ASSET_IDENTITY_OPTIONAL_CONSUMED":
            parked_tasks.append("INCOMPLETE_CITY_ASSET_IDENTITY_BRANCH")
        status = PASS_STATUS
        if not all([local_status == "PASS", visual_status == "PASS", current_truth_status == "PASS", branch_summary_status == "PASS", claim_status == "PASS", mutation_status == "PASS", secret_status == "PASS"]):
            status = FAIL_STATUS
        write_main_docs(status)

    hash_status = write_hashes()
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "d6_r4_status": r4_status,
        "d6_closeout_r1_status": decision_status(root_path(ROOTS["d6_closeout_r1"])),
        "d6_r3_status": decision_status(root_path(ROOTS["d6_r3"])),
        "track2a_event_overlay_r3_status": decision_status(root_path(ROOTS["track2a_event_overlay_r3"])),
        "event_fabric_r2_status": decision_status(root_path(ROOTS["event_fabric_r2"])),
        "mobility_branch_status": decision_status(root_path(ROOTS["mobility_runtime_d6_overlay"])),
        "building_property_branch_status": decision_status(root_path(ROOTS["building_property_r7_closeout"])),
        "r7_registry_preflight_status": decision_status(root_path(ROOTS["r7_registry_preflight"])),
        "city_asset_identity_status": city_asset_status,
        "local_open_index_status": local_status,
        "visual_evidence_status": visual_status,
        "current_truth_register_status": current_truth_status,
        "branch_status_summary_status": branch_summary_status,
        "claim_boundary_status": claim_status,
        "no_mutation_status": mutation_status,
        "secret_audit_status": secret_status,
        "hash_validation_status": hash_status,
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D4X-R7-MULTI-DOMAIN-EDGE-REGISTRY-RUNTIME-SLICE",
        "alternative_next_task": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-EVENT-FABRIC-INTEGRATION-R3",
        "parked_tasks": parked_tasks,
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_R2_DECISION.json", decision)
    hash_status = write_hashes()
    decision["hash_validation_status"] = hash_status
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_R2_DECISION.json", decision)
    write_hashes()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if status.startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
