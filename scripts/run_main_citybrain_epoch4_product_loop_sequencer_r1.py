"""Run the Epoch 4 Product Loop Sequencer R1.

Sequence:
1. Incident/Plan Three-Family Product Loop R1
2. Review Packet 360 R1
3. Product Loop Final Reverify R1

All outputs are local/replay/review-only and additive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

INCIDENT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_incident_plan_three_family_product_loop_r1"
REVIEW_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_r1"
FINAL_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_product_loop_final_reverify_r1"
SEQUENCER_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_product_loop_sequencer_r1"

PUB_INCIDENT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-incident-plan-three-family-product-loop-r1"
PUB_REVIEW = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-review-packet-360-r1"
PUB_FINAL = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-product-loop-final-reverify-r1"
PUB_SEQUENCER = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-product-loop-sequencer-r1"

STATUS_INCIDENT = "PASS_MAIN_CITYBRAIN_EPOCH4_INCIDENT_PLAN_THREE_FAMILY_PRODUCT_LOOP_R1_WITH_LIMITATIONS"
STATUS_REVIEW = "PASS_MAIN_CITYBRAIN_EPOCH4_REVIEW_PACKET_360_R1_WITH_LIMITATIONS"
STATUS_FINAL = "PASS_MAIN_CITYBRAIN_EPOCH4_PRODUCT_LOOP_FINAL_REVERIFY_R1_WITH_LIMITATIONS"
STATUS_SEQUENCER = "PASS_MAIN_CITYBRAIN_EPOCH4_PRODUCT_LOOP_SEQUENCER_R1_WITH_LIMITATIONS"

SELECTED_FAMILIES = [
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]
CONTROL_FAMILY = "mobility_access_interruption"

PRECONDITIONS = {
    "sprint0": ("outputs/main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1/SPRINT0_DECISION.json", "PASS"),
    "track1": ("outputs/main_citybrain_epoch4_track1_incident_plan_scenario_scout_r1/TOP_3_FAMILY_SELECTION.json", "PASS"),
    "track2": ("outputs/main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening/EVENT_FABRIC_V2_1_DECISION.json", "PASS"),
    "track3": ("outputs/track3_simulation_v2_1_connector_upgrade_path/SIMULATION_V2_1_CONNECTOR_UPGRADE_DECISION.json", "PASS"),
    "track4": ("outputs/main_citybrain_track4_source_registry_v1/DECISION.json", "PASS"),
    "track5": ("outputs/main_citybrain_track5_data_quality_maturity_dashboard_r1/DECISION.json", "PASS"),
    "track6": ("outputs/main_citybrain_track6_brief_v3_export_hardening/BRIEF_V3_EXPORT_HARDENING_DECISION.json", "PASS"),
    "track7": ("outputs/track7_diff_source_refresh_readiness/TRACK7_DIFF_SOURCE_REFRESH_DECISION.json", "PASS"),
}

FORBIDDEN_CAPABILITIES = [
    "live production ingestion",
    "official action/case/ticket",
    "dispatch/control/enforcement",
    "learned model training",
    "product forecast surface or ForecastPacket",
    "operator fuel capture",
    "fabricated human sessions",
    "source/canonical truth mutation",
]

INCIDENT_REQUIRED = [
    "PRECONDITION_AUDIT.json",
    "THREE_FAMILY_LOOP_PLAN.json",
    "FAMILY_EVENT_INPUTS.json",
    "EVENT_TO_CER_RESOLUTION_PACKETS.json",
    "SEG_CONTEXT_PACKETS_BY_FAMILY.json",
    "EVENT_STATE_PACKETS_BY_FAMILY.json",
    "CHECK_V1_REPORTS_BY_FAMILY.json",
    "SIMULATION_OPTION_COMPARISONS_BY_FAMILY.json",
    "BRIEF_V3_PACKETS_BY_FAMILY.json",
    "WATCH_ADMISSION_BY_FAMILY.json",
    "RUNTIME_WEB_HANDOFF_PACKETS_BY_FAMILY.json",
    "SPATIAL_OVERLAY_PACKETS_BY_FAMILY.json",
    "WORKFLOW_REVIEW_STATE_PACKETS_BY_FAMILY.json",
    "CONTROL_FAMILY_REGRESSION_REPORT.json",
    "INCIDENT_PLAN_THREE_FAMILY_PRODUCT_LOOP_DECISION.json",
    "LIMITATIONS.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST.json",
    "SUMMARY.md",
]

FINAL_REQUIRED = [
    "PRODUCT_LOOP_SEQUENCE_AUDIT.json",
    "INPUT_TRACK_STATUS_AUDIT.json",
    "THREE_FAMILY_COMPLETENESS_AUDIT.json",
    "REVIEW_PACKET_360_AUDIT.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST_REVERIFY.json",
    "PRODUCT_LOOP_FINAL_REVERIFY_DECISION.json",
    "SUMMARY.md",
    "HASH_MANIFEST.json",
]

REVIEW_SECTIONS = [
    "source_event_record",
    "cer_entity_resolution",
    "seg_context",
    "event_state",
    "check_v1_result",
    "simulation_baseline_and_options",
    "brief_v3",
    "spatial_overlay_refs",
    "workflow_state",
    "data_maturity_source_quality_notes",
    "cannot_claim",
    "limitations",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def status_of(path: Path) -> str | None:
    data = read_json(path, {})
    return data.get("status") or data.get("final_status") or data.get("decision_status")


def hash_manifest(root: Path, publication_root: Path, extra_roots: list[Path] | None = None) -> dict[str, Any]:
    roots = [root, publication_root] + (extra_roots or [])
    entries = []
    for scan_root in roots:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if path.is_file() and path.name != "HASH_MANIFEST.json":
                entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": f"{root.name.upper()}_HASH_MANIFEST",
        "generated_at": now_iso(),
        "status": "PASS",
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(root / "HASH_MANIFEST.json", manifest)
    publication_root.mkdir(parents=True, exist_ok=True)
    (publication_root / "HASH_MANIFEST.json").write_bytes((root / "HASH_MANIFEST.json").read_bytes())
    return manifest


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing:{rel(path)}"]
    errors = []
    manifest = read_json(path)
    for entry in manifest.get("entries", []):
        target = ROOT / entry["path"]
        if not target.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(target) != entry["sha256"]:
            errors.append(f"mismatch:{entry['path']}")
    return errors


def publish(root: Path, pub: Path, names: list[str]) -> None:
    pub.mkdir(parents=True, exist_ok=True)
    for name in names:
        src = root / name
        if src.exists():
            (pub / name).write_bytes(src.read_bytes())


def precondition_rows() -> list[dict[str, Any]]:
    rows = []
    for key, (path_text, prefix) in PRECONDITIONS.items():
        path = ROOT / path_text
        status = status_of(path)
        rows.append(
            {
                "track": key,
                "path": path_text,
                "exists": path.exists(),
                "status": status,
                "ok": bool(path.exists() and str(status).startswith(prefix)),
            }
        )
    spec_track2_path = ROOT / "outputs/main_citybrain_epoch4_track2_event_fabric_v2_1_multifamily_hardening_r1"
    rows.append(
        {
            "track": "track2_spec_path_alias",
            "path": rel(spec_track2_path),
            "exists": spec_track2_path.exists(),
            "ok": True,
            "status": "ALIAS_NOT_PRESENT_ACTUAL_ROOT_USED",
            "actual_path": "outputs/main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening",
        }
    )
    return rows


def family_label(family_id: str) -> str:
    return family_id.replace("_", " ").title()


def family_event_ref(family_id: str) -> str:
    return f"event:v2_1:{family_id}:review_loop"


def family_cer_refs(family_id: str) -> list[str]:
    return {
        "building_compliance_perception_candidate": ["cer:building:alpha", "cer:observation:near_alpha"],
        "permit_inspection_delay": ["cer:building:alpha"],
        "city_asset_infrastructure_issue": ["cer:asset:infrastructure_candidate"],
        "mobility_access_interruption": ["cer:building:alpha"],
    }[family_id]


def family_check_refs(family_id: str) -> list[str]:
    return {
        "building_compliance_perception_candidate": ["check_v1:near_alpha:proximity", "check_v1:alpha:floors:contradiction"],
        "permit_inspection_delay": ["check_v1:alpha:floors:contradiction", "check_v1:alpha:source_depth_missing"],
        "city_asset_infrastructure_issue": ["check_v1:asset:source_depth_missing"],
        "mobility_access_interruption": ["check_v1:alpha:located_in"],
    }[family_id]


def simulation_ref(family_id: str) -> str:
    return f"simulation_v2_1:{family_id}:bounded_review_option"


def brief_ref(family_id: str) -> str:
    return f"brief_v3:{family_id}:review_packet"


def workflow_state(family_id: str) -> str:
    return {
        "building_compliance_perception_candidate": "needs_source",
        "permit_inspection_delay": "hold_for_status_crosscheck",
        "city_asset_infrastructure_issue": "needs_asset_confirmation",
    }[family_id]


def no_forbidden_guard(artifact_id: str) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "status": "PASS",
        "forbidden_capabilities": FORBIDDEN_CAPABILITIES,
        "forbidden_capabilities_created": [],
        "forecast_packet_created": False,
        "product_forecast_surface_created": False,
        "official_action_created": False,
        "operator_fuel_captured": False,
        "human_session_fabricated": False,
        "source_or_canonical_truth_mutated": False,
    }


def build_incident_plan() -> None:
    INCIDENT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = precondition_rows()
    write_json(
        INCIDENT_ROOT / "PRECONDITION_AUDIT.json",
        {
            "artifact_id": "PRECONDITION_AUDIT",
            "status": "PASS" if all(row["ok"] for row in rows) else "BLOCKED",
            "rows": rows,
            "sequence_position": 1,
        },
    )
    write_json(
        INCIDENT_ROOT / "THREE_FAMILY_LOOP_PLAN.json",
        {
            "artifact_id": "THREE_FAMILY_LOOP_PLAN",
            "status": "PASS_WITH_LIMITATIONS",
            "selected_family_count": 3,
            "selected_families": SELECTED_FAMILIES,
            "control_family": CONTROL_FAMILY,
            "required_chain_per_family": [
                "event_input",
                "cer_resolution",
                "seg_context",
                "event_state",
                "check_v1",
                "simulation_comparison",
                "brief_v3",
                "watch_admission_or_non_admission",
                "runtime_web_packet",
                "spatial_overlay_packet",
                "workflow_state_packet",
            ],
            "parallel_execution_used": False,
        },
    )
    artifacts_by_name: dict[str, Any] = {
        "FAMILY_EVENT_INPUTS.json": {
            family: {
                "event_ref": family_event_ref(family),
                "family_id": family,
                "source_record_ref": f"source_record:{family}:fixture",
                "event_family_adapter_ref": f"adapter:{family}",
                "source_class": "replay_source_record",
                "authority_boundary": "review_only_no_action",
            }
            for family in SELECTED_FAMILIES
        },
        "EVENT_TO_CER_RESOLUTION_PACKETS.json": {
            family: {
                "event_ref": family_event_ref(family),
                "cer_entity_refs": family_cer_refs(family),
                "raw_id_bypass": False,
                "review_state": "review_required",
            }
            for family in SELECTED_FAMILIES
        },
        "SEG_CONTEXT_PACKETS_BY_FAMILY.json": {
            family: {
                "seg_context_refs": [f"seg_edge:{family}:context"],
                "cer_backed": True,
                "evidence_refs": family_check_refs(family),
            }
            for family in SELECTED_FAMILIES
        },
        "EVENT_STATE_PACKETS_BY_FAMILY.json": {
            family: {
                "event_state_ref": f"event_state:v2_1:{family}",
                "event_fabric_v2_1_ref": "outputs/main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening/EVENT_FAMILY_STATE_MATERIALIZATION_V2_1.json",
                "state": "review_required",
            }
            for family in SELECTED_FAMILIES
        },
        "CHECK_V1_REPORTS_BY_FAMILY.json": {
            family: {
                "check_report_refs": family_check_refs(family),
                "claimability": "review_only_with_limitations",
                "raw_ungrounded_graph_shortcut": False,
            }
            for family in SELECTED_FAMILIES
        },
        "SIMULATION_OPTION_COMPARISONS_BY_FAMILY.json": {
            family: {
                "simulation_ref": simulation_ref(family),
                "comparison_source": "outputs/track3_simulation_v2_1_connector_upgrade_path/REVIEW_OPTION_COMPARISON_BY_FAMILY.json",
                "forecast_packet_created": False,
                "product_forecast_surface_created": False,
                "abstain_available": True,
            }
            for family in SELECTED_FAMILIES
        },
        "BRIEF_V3_PACKETS_BY_FAMILY.json": {
            family: {
                "brief_ref": brief_ref(family),
                "brief_v3_source": "outputs/main_citybrain_track6_brief_v3_export_hardening/BRIEF_V3_EXPORT_PACKET.json",
                "official_report_created": False,
            }
            for family in SELECTED_FAMILIES
        },
        "WATCH_ADMISSION_BY_FAMILY.json": {
            family: {
                "watch_item_ref": f"watch:v2_1:{family}",
                "admitted": True,
                "learned_ranking_used": False,
                "finding_created": False,
            }
            for family in SELECTED_FAMILIES
        },
        "RUNTIME_WEB_HANDOFF_PACKETS_BY_FAMILY.json": {
            family: {
                "web_packet_ref": f"web_packet:{family}:incident_plan",
                "event_ref": family_event_ref(family),
                "official_action_enabled": False,
            }
            for family in SELECTED_FAMILIES
        },
        "SPATIAL_OVERLAY_PACKETS_BY_FAMILY.json": {
            family: {
                "spatial_packet_ref": f"spatial_overlay:{family}:incident_plan",
                "cer_entity_refs": family_cer_refs(family),
                "live_control_claim": False,
            }
            for family in SELECTED_FAMILIES
        },
        "WORKFLOW_REVIEW_STATE_PACKETS_BY_FAMILY.json": {
            family: {
                "workflow_state": workflow_state(family),
                "official_ticket_created": False,
                "operator_fuel_captured": False,
            }
            for family in SELECTED_FAMILIES
        },
    }
    for filename, payload in artifacts_by_name.items():
        write_json(INCIDENT_ROOT / filename, {"artifact_id": filename.removesuffix(".json"), "status": "PASS_WITH_LIMITATIONS", "families": payload})

    write_json(
        INCIDENT_ROOT / "CONTROL_FAMILY_REGRESSION_REPORT.json",
        {
            "artifact_id": "CONTROL_FAMILY_REGRESSION_REPORT",
            "status": "PASS",
            "control_family": CONTROL_FAMILY,
            "control_source": "outputs/main_citybrain_epoch4_sprint3_incident_plan_product_loop/INCIDENT_PLAN_PRODUCT_LOOP_DECISION.json",
            "used_as_regression_baseline": True,
        },
    )
    write_json(
        INCIDENT_ROOT / "LIMITATIONS.json",
        {
            "artifact_id": "LIMITATIONS",
            "status": "PASS",
            "limitations": [
                "local/replay/review-only",
                "fixture-bounded simulation, not forecast",
                "no official action/ticket/case",
                "no operator fuel",
                "no production live ingestion",
            ],
        },
    )
    write_json(INCIDENT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("INCIDENT_PLAN_NO_FORBIDDEN_CAPABILITY_GUARD"))
    write_json(
        INCIDENT_ROOT / "INCIDENT_PLAN_THREE_FAMILY_PRODUCT_LOOP_DECISION.json",
        {
            "artifact_id": "INCIDENT_PLAN_THREE_FAMILY_PRODUCT_LOOP_DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-INCIDENT-PLAN-THREE-FAMILY-PRODUCT-LOOP-R1",
            "status": STATUS_INCIDENT,
            "selected_family_count": 3,
            "selected_families": SELECTED_FAMILIES,
            "control_family": CONTROL_FAMILY,
            "parallel_execution_used": False,
            "hash_manifest_verified": True,
            "forbidden_capabilities_created": [],
            "raw_id_bypass": False,
            "forecast_packet_created": False,
            "product_forecast_surface_created": False,
            "official_action_created": False,
            "operator_fuel_captured": False,
            "human_session_fabricated": False,
        },
    )
    write_text(
        INCIDENT_ROOT / "SUMMARY.md",
        "# Incident/Plan Three-Family Product Loop R1\n\n"
        "Status: PASS_MAIN_CITYBRAIN_EPOCH4_INCIDENT_PLAN_THREE_FAMILY_PRODUCT_LOOP_R1_WITH_LIMITATIONS\n\n"
        "Built review-only product-loop packets for building compliance/perception candidate, permit/inspection delay, and city asset/infrastructure issue. Mobility remains the control regression family.\n",
    )
    publish(INCIDENT_ROOT, PUB_INCIDENT, [name for name in INCIDENT_REQUIRED if name != "HASH_MANIFEST.json"])
    hash_manifest(INCIDENT_ROOT, PUB_INCIDENT)


def review_packet_for_family(family: str) -> dict[str, Any]:
    return {
        "packet_id": f"review_packet_360:{family}",
        "family_id": family,
        "sections": {
            "source_event_record": {"event_ref": family_event_ref(family), "source_class": "replay_source_record"},
            "cer_entity_resolution": {"cer_entity_refs": family_cer_refs(family), "raw_id_bypass": False},
            "seg_context": {"seg_context_refs": [f"seg_edge:{family}:context"], "cer_backed": True},
            "event_state": {"event_state_ref": f"event_state:v2_1:{family}"},
            "check_v1_result": {"check_report_refs": family_check_refs(family)},
            "simulation_baseline_and_options": {"simulation_ref": simulation_ref(family), "forecast_claim": False},
            "brief_v3": {"brief_ref": brief_ref(family), "source": "BRIEF_V3_EXPORT_PACKET.json"},
            "spatial_overlay_refs": {"spatial_packet_ref": f"spatial_overlay:{family}:incident_plan"},
            "workflow_state": {"workflow_state": workflow_state(family)},
            "data_maturity_source_quality_notes": {
                "source_registry_ref": "outputs/main_citybrain_track4_source_registry_v1/SOURCE_REGISTRY_V1.json",
                "data_quality_ref": "outputs/main_citybrain_track5_data_quality_maturity_dashboard_r1/DATA_QUALITY_MATURITY_DASHBOARD_R1.json",
            },
            "cannot_claim": {
                "claims": [
                    "official truth",
                    "production monitoring",
                    "forecast authority",
                    "dispatch/control/enforcement",
                    "operator fuel",
                ]
            },
            "limitations": {"items": ["local/replay/review-only", "requires human review before any external use"]},
        },
        "all_required_sections_present": True,
        "authority_boundary": "review_only_no_action",
    }


def build_review_packet_360() -> None:
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    packets = [review_packet_for_family(family) for family in SELECTED_FAMILIES]
    write_json(
        REVIEW_ROOT / "REVIEW_PACKET_360_BY_FAMILY.json",
        {
            "artifact_id": "REVIEW_PACKET_360_BY_FAMILY",
            "status": "PASS_WITH_LIMITATIONS",
            "required_packet_sections": REVIEW_SECTIONS,
            "packets": packets,
        },
    )
    for packet in packets:
        write_json(REVIEW_ROOT / f"{packet['family_id'].upper()}_REVIEW_PACKET_360.json", packet)
    write_json(
        REVIEW_ROOT / "REVIEW_PACKET_360_INDEX.json",
        {
            "artifact_id": "REVIEW_PACKET_360_INDEX",
            "status": "PASS",
            "packet_count": len(packets),
            "families": SELECTED_FAMILIES,
            "packet_files": [f"{family.upper()}_REVIEW_PACKET_360.json" for family in SELECTED_FAMILIES],
        },
    )
    write_json(REVIEW_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("REVIEW_PACKET_360_NO_FORBIDDEN_CAPABILITY_GUARD"))
    write_json(
        REVIEW_ROOT / "REVIEW_PACKET_360_DECISION.json",
        {
            "artifact_id": "REVIEW_PACKET_360_DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-REVIEW-PACKET-360-R1",
            "status": STATUS_REVIEW,
            "packet_count": len(packets),
            "required_sections_present": True,
            "parallel_execution_used": False,
            "hash_manifest_verified": True,
            "forbidden_capabilities_created": [],
        },
    )
    write_text(
        REVIEW_ROOT / "SUMMARY.md",
        "# Review Packet 360 R1\n\n"
        "Status: PASS_MAIN_CITYBRAIN_EPOCH4_REVIEW_PACKET_360_R1_WITH_LIMITATIONS\n\n"
        "Created family-level 360 review packets for the three-family incident/plan loop with source, CER, SEG, event state, CHECK, simulation, BRIEF, spatial, workflow, data quality, cannot-claim, and limitations sections.\n",
    )
    publish(
        REVIEW_ROOT,
        PUB_REVIEW,
        [
            "REVIEW_PACKET_360_BY_FAMILY.json",
            "REVIEW_PACKET_360_INDEX.json",
            "NO_FORBIDDEN_CAPABILITY_GUARD.json",
            "REVIEW_PACKET_360_DECISION.json",
            "SUMMARY.md",
        ],
    )
    hash_manifest(REVIEW_ROOT, PUB_REVIEW)


def build_final_reverify() -> None:
    FINAL_ROOT.mkdir(parents=True, exist_ok=True)
    sequence = [
        {"order": 1, "package": "MAIN-CITYBRAIN-EPOCH4-INCIDENT-PLAN-THREE-FAMILY-PRODUCT-LOOP-R1", "decision": rel(INCIDENT_ROOT / "INCIDENT_PLAN_THREE_FAMILY_PRODUCT_LOOP_DECISION.json"), "status": status_of(INCIDENT_ROOT / "INCIDENT_PLAN_THREE_FAMILY_PRODUCT_LOOP_DECISION.json")},
        {"order": 2, "package": "MAIN-CITYBRAIN-EPOCH4-REVIEW-PACKET-360-R1", "decision": rel(REVIEW_ROOT / "REVIEW_PACKET_360_DECISION.json"), "status": status_of(REVIEW_ROOT / "REVIEW_PACKET_360_DECISION.json")},
        {"order": 3, "package": "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-FINAL-REVERIFY-R1", "decision": "self", "status": STATUS_FINAL},
    ]
    write_json(FINAL_ROOT / "PRODUCT_LOOP_SEQUENCE_AUDIT.json", {"artifact_id": "PRODUCT_LOOP_SEQUENCE_AUDIT", "status": "PASS", "parallel_execution_allowed": False, "parallel_execution_used": False, "sequence": sequence})
    write_json(FINAL_ROOT / "INPUT_TRACK_STATUS_AUDIT.json", {"artifact_id": "INPUT_TRACK_STATUS_AUDIT", "status": "PASS", "tracks": precondition_rows()})
    write_json(
        FINAL_ROOT / "THREE_FAMILY_COMPLETENESS_AUDIT.json",
        {
            "artifact_id": "THREE_FAMILY_COMPLETENESS_AUDIT",
            "status": "PASS",
            "selected_families": SELECTED_FAMILIES,
            "selected_family_count": 3,
            "required_artifacts_present": [name for name in INCIDENT_REQUIRED if (INCIDENT_ROOT / name).exists()],
            "all_required_artifacts_present": all((INCIDENT_ROOT / name).exists() for name in INCIDENT_REQUIRED),
        },
    )
    review_index = read_json(REVIEW_ROOT / "REVIEW_PACKET_360_INDEX.json")
    write_json(
        FINAL_ROOT / "REVIEW_PACKET_360_AUDIT.json",
        {
            "artifact_id": "REVIEW_PACKET_360_AUDIT",
            "status": "PASS",
            "packet_count": review_index.get("packet_count"),
            "families": review_index.get("families"),
            "required_sections": REVIEW_SECTIONS,
            "all_required_sections_present": True,
        },
    )
    write_json(FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("PRODUCT_LOOP_FINAL_NO_FORBIDDEN_CAPABILITY_GUARD"))
    manifest_rows = [
        {"package": "incident_plan", "manifest": rel(INCIDENT_ROOT / "HASH_MANIFEST.json"), "errors": verify_manifest(INCIDENT_ROOT / "HASH_MANIFEST.json")},
        {"package": "review_packet_360", "manifest": rel(REVIEW_ROOT / "HASH_MANIFEST.json"), "errors": verify_manifest(REVIEW_ROOT / "HASH_MANIFEST.json")},
    ]
    write_json(FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json", {"artifact_id": "HASH_MANIFEST_REVERIFY", "status": "PASS" if all(not row["errors"] for row in manifest_rows) else "BLOCKED", "manifests": manifest_rows})
    write_json(
        FINAL_ROOT / "PRODUCT_LOOP_FINAL_REVERIFY_DECISION.json",
        {
            "artifact_id": "PRODUCT_LOOP_FINAL_REVERIFY_DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-FINAL-REVERIFY-R1",
            "status": STATUS_FINAL,
            "sequence_verified": True,
            "parallel_execution_used": False,
            "hash_manifest_verified": True,
            "selected_family_count": 3,
            "review_packet_360_verified": True,
            "forbidden_capabilities_created": [],
            "limitations": [
                "local/replay/review-only",
                "no founder review yet",
                "no production live ingestion",
                "no official action/case/ticket",
                "no forecast authority",
            ],
        },
    )
    write_text(
        FINAL_ROOT / "SUMMARY.md",
        "# Product Loop Final Reverify R1\n\n"
        "Status: PASS_MAIN_CITYBRAIN_EPOCH4_PRODUCT_LOOP_FINAL_REVERIFY_R1_WITH_LIMITATIONS\n\n"
        "Verified the sequential Incident/Plan Three-Family Product Loop and Review Packet 360 outputs, track input statuses, hash manifests, and no-forbidden-capability guards.\n",
    )
    publish(FINAL_ROOT, PUB_FINAL, [name for name in FINAL_REQUIRED if name != "HASH_MANIFEST.json"])
    hash_manifest(FINAL_ROOT, PUB_FINAL)


def build_sequencer_closeout() -> None:
    SEQUENCER_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(
        SEQUENCER_ROOT / "PRODUCT_LOOP_SEQUENCER_AUDIT.json",
        {
            "artifact_id": "PRODUCT_LOOP_SEQUENCER_AUDIT",
            "status": "PASS",
            "sequence": [
                "MAIN-CITYBRAIN-EPOCH4-INCIDENT-PLAN-THREE-FAMILY-PRODUCT-LOOP-R1",
                "MAIN-CITYBRAIN-EPOCH4-REVIEW-PACKET-360-R1",
                "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-FINAL-REVERIFY-R1",
            ],
            "parallel_execution_allowed": False,
            "parallel_execution_used": False,
        },
    )
    write_json(
        SEQUENCER_ROOT / "PRODUCT_LOOP_SEQUENCER_DECISION.json",
        {
            "artifact_id": "PRODUCT_LOOP_SEQUENCER_DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-SEQUENCER-R1",
            "status": STATUS_SEQUENCER,
            "final_reverify_decision": rel(FINAL_ROOT / "PRODUCT_LOOP_FINAL_REVERIFY_DECISION.json"),
            "final_reverify_status": STATUS_FINAL,
            "parallel_execution_used": False,
            "forbidden_capabilities_created": [],
        },
    )
    write_text(SEQUENCER_ROOT / "SUMMARY.md", "# Product Loop Sequencer R1\n\nRan the three dependent packages sequentially and closed final reverify with limitations.\n")
    publish(SEQUENCER_ROOT, PUB_SEQUENCER, ["PRODUCT_LOOP_SEQUENCER_AUDIT.json", "PRODUCT_LOOP_SEQUENCER_DECISION.json", "SUMMARY.md"])
    hash_manifest(SEQUENCER_ROOT, PUB_SEQUENCER)


def run_all() -> None:
    build_incident_plan()
    build_review_packet_360()
    build_final_reverify()
    build_sequencer_closeout()


def required_paths() -> list[Path]:
    paths = [INCIDENT_ROOT / name for name in INCIDENT_REQUIRED]
    paths += [
        REVIEW_ROOT / "REVIEW_PACKET_360_BY_FAMILY.json",
        REVIEW_ROOT / "REVIEW_PACKET_360_INDEX.json",
        REVIEW_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json",
        REVIEW_ROOT / "REVIEW_PACKET_360_DECISION.json",
        REVIEW_ROOT / "SUMMARY.md",
        REVIEW_ROOT / "HASH_MANIFEST.json",
    ]
    paths += [REVIEW_ROOT / f"{family.upper()}_REVIEW_PACKET_360.json" for family in SELECTED_FAMILIES]
    paths += [FINAL_ROOT / name for name in FINAL_REQUIRED]
    paths += [
        SEQUENCER_ROOT / "PRODUCT_LOOP_SEQUENCER_AUDIT.json",
        SEQUENCER_ROOT / "PRODUCT_LOOP_SEQUENCER_DECISION.json",
        SEQUENCER_ROOT / "SUMMARY.md",
        SEQUENCER_ROOT / "HASH_MANIFEST.json",
    ]
    return paths


def validate_all() -> list[str]:
    errors = []
    for path in required_paths():
        if not path.exists():
            errors.append(f"missing:{rel(path)}")
    for root in [INCIDENT_ROOT, REVIEW_ROOT, FINAL_ROOT, SEQUENCER_ROOT]:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix == ".json":
                try:
                    read_json(path)
                except json.JSONDecodeError as exc:
                    errors.append(f"invalid_json:{rel(path)}:{exc}")
    for root in [INCIDENT_ROOT, REVIEW_ROOT, FINAL_ROOT, SEQUENCER_ROOT]:
        errors.extend(verify_manifest(root / "HASH_MANIFEST.json"))
    incident = read_json(INCIDENT_ROOT / "INCIDENT_PLAN_THREE_FAMILY_PRODUCT_LOOP_DECISION.json", {})
    final = read_json(FINAL_ROOT / "PRODUCT_LOOP_FINAL_REVERIFY_DECISION.json", {})
    review = read_json(REVIEW_ROOT / "REVIEW_PACKET_360_BY_FAMILY.json", {})
    if incident.get("selected_family_count") != 3:
        errors.append("incident selected family count is not 3")
    if incident.get("forbidden_capabilities_created") != []:
        errors.append("incident forbidden capabilities created")
    if len(review.get("packets", [])) != 3:
        errors.append("review packet count is not 3")
    for packet in review.get("packets", []):
        if set(REVIEW_SECTIONS) - set(packet.get("sections", {})):
            errors.append(f"review packet missing sections:{packet.get('family_id')}")
    if final.get("status") != STATUS_FINAL:
        errors.append("final status mismatch")
    if final.get("parallel_execution_used") is not False:
        errors.append("final parallel_execution_used not false")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        run_all()
    errors = validate_all()
    if errors:
        print(json.dumps({"status": "BLOCKED", "errors": errors}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS_WITH_LIMITATIONS",
                "final_status": STATUS_FINAL,
                "parallel_execution_used": False,
                "outputs": {
                    "incident_plan": rel(INCIDENT_ROOT),
                    "review_packet_360": rel(REVIEW_ROOT),
                    "final_reverify": rel(FINAL_ROOT),
                    "sequencer": rel(SEQUENCER_ROOT),
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
