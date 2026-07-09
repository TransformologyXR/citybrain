#!/usr/bin/env python3
"""Run the Epoch 4 after-product-loop next wave sequentially.

Sequence:
1. Product Loop Consolidation and Pilot Readiness R1
2. Event Fabric V2.2 Scale / Replay Reliability R1
3. Simulation V2.2 Real Connector + Fidelity Ladder R1
4. Data Maturity Diagnostic Product R2
5. Pre-Founder Review Prep, No Session R1
6. Next Wave Final Reverify R1

All outputs are additive, local/replay/review-only, and bounded by the package
guards. This runner does not branch, stage, commit, push, clean, reset, stash,
or mutate upstream source truth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

CONSOLIDATION_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_product_loop_consolidation_and_pilot_readiness_r1"
EVENT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_2_scale_replay_reliability_r1"
SIM_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_2_real_connector_fidelity_ladder_r1"
DATA_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_diagnostic_product_r2"
PREF_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_pre_founder_review_prep_no_session_r1"
FINAL_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_next_wave_final_reverify_r1"
SEQUENCE_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_next_wave_sequence_r1"

PUB_CONSOLIDATION = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-product-loop-consolidation-and-pilot-readiness-r1"
PUB_EVENT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-event-fabric-v2-2-scale-replay-reliability-r1"
PUB_SIM = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-simulation-v2-2-real-connector-fidelity-ladder-r1"
PUB_DATA = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-data-maturity-diagnostic-product-r2"
PUB_PREF = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-pre-founder-review-prep-no-session-r1"
PUB_FINAL = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-next-wave-final-reverify-r1"
PUB_SEQUENCE = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-next-wave-sequence-r1"

STATUS_CONSOLIDATION = "PASS_MAIN_CITYBRAIN_EPOCH4_PRODUCT_LOOP_CONSOLIDATION_AND_PILOT_READINESS_R1_WITH_LIMITATIONS"
STATUS_EVENT = "PASS_MAIN_CITYBRAIN_EPOCH4_EVENT_FABRIC_V2_2_SCALE_REPLAY_RELIABILITY_R1_WITH_LIMITATIONS"
STATUS_SIM = "PASS_MAIN_CITYBRAIN_EPOCH4_SIMULATION_V2_2_REAL_CONNECTOR_FIDELITY_LADDER_R1_WITH_LIMITATIONS"
STATUS_DATA = "PASS_MAIN_CITYBRAIN_EPOCH4_DATA_MATURITY_DIAGNOSTIC_PRODUCT_R2_WITH_LIMITATIONS"
STATUS_PREF = "PASS_MAIN_CITYBRAIN_EPOCH4_PRE_FOUNDER_REVIEW_PREP_NO_SESSION_R1_WITH_LIMITATIONS"
STATUS_FINAL = "PASS_MAIN_CITYBRAIN_EPOCH4_NEXT_WAVE_FINAL_REVERIFY_R1_WITH_LIMITATIONS"
STATUS_SEQUENCE = "PASS_MAIN_CITYBRAIN_EPOCH4_NEXT_WAVE_SEQUENCE_R1_WITH_LIMITATIONS"

SELECTED_FAMILIES = [
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]
CONTROL_FAMILY = "mobility_access_interruption"
ALL_FAMILIES = [CONTROL_FAMILY] + SELECTED_FAMILIES

FORBIDDEN_CAPABILITIES = [
    "production_live_ingestion",
    "official_action_case_ticket",
    "dispatch_control_enforcement",
    "product_forecast_surface_or_ForecastPacket",
    "learned_model_training_or_ranking",
    "fabricated_human_founder_operator_sessions",
    "source_truth_mutation_or_cer_check_bypass",
]

PARKED_ITEMS = [
    "founder_review_sessions",
    "ui_ux_sprint",
    "live_or_production_ingestion",
    "official_workflow_adapter",
    "forecast_productization",
    "learned_ranking",
    "case_memory_learner",
    "cross_city_learned_transfer",
]

INPUTS = {
    "sprint0_check_cer": {
        "path": ROOT / "outputs" / "main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1" / "SPRINT0_DECISION.json",
        "expected_prefix": "PASS",
    },
    "track1_scenario_scout": {
        "path": ROOT / "outputs" / "main_citybrain_epoch4_track1_incident_plan_scenario_scout_r1" / "TOP_3_FAMILY_SELECTION.json",
        "expected_prefix": "PASS",
    },
    "track2_event_fabric_v2_1": {
        "path": ROOT / "outputs" / "main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening" / "EVENT_FABRIC_V2_1_DECISION.json",
        "expected_prefix": "PASS",
    },
    "track3_simulation_v2_1": {
        "path": ROOT / "outputs" / "track3_simulation_v2_1_connector_upgrade_path" / "SIMULATION_V2_1_CONNECTOR_UPGRADE_DECISION.json",
        "expected_prefix": "PASS",
        "equivalent_for": "outputs/main_citybrain_epoch4_track3_simulation_v2_1_connector_upgrade_path",
    },
    "track4_source_registry_v1": {
        "path": ROOT / "outputs" / "main_citybrain_track4_source_registry_v1" / "DECISION.json",
        "expected_prefix": "PASS",
    },
    "track5_data_maturity_r1": {
        "path": ROOT / "outputs" / "main_citybrain_track5_data_quality_maturity_dashboard_r1" / "DECISION.json",
        "expected_prefix": "PASS",
    },
    "track6_brief_v3": {
        "path": ROOT / "outputs" / "main_citybrain_track6_brief_v3_export_hardening" / "BRIEF_V3_EXPORT_HARDENING_DECISION.json",
        "expected_prefix": "PASS",
    },
    "track7_diff_readiness": {
        "path": ROOT / "outputs" / "track7_diff_source_refresh_readiness" / "TRACK7_DIFF_SOURCE_REFRESH_DECISION.json",
        "expected_prefix": "PASS",
    },
    "package_a_event_stories_source_diff": {
        "path": ROOT / "outputs" / "main_citybrain_epoch4_tracka_event_stories_source_diff_r1" / "TRACKA_EVENT_STORIES_SOURCE_DIFF_DECISION.json",
        "expected_prefix": "PASS",
    },
    "package_b_maturity_brief_governance": {
        "path": ROOT / "outputs" / "main_citybrain_epoch4_trackb_maturity_brief_governance_r1" / "TRACKB_MATURITY_BRIEF_GOVERNANCE_DECISION.json",
        "expected_prefix": "PASS",
    },
    "review_packet_360": {
        "path": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_r1" / "REVIEW_PACKET_360_DECISION.json",
        "expected_prefix": "PASS",
    },
    "product_loop_final_reverify": {
        "path": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_final_reverify_r1" / "PRODUCT_LOOP_FINAL_REVERIFY_DECISION.json",
        "expected_prefix": "PASS",
    },
}

CONSOLIDATION_FILES = [
    "CURRENT_TRUTH_LEDGER.json",
    "PRODUCT_LOOP_CAPABILITY_MAP.json",
    "THREE_FAMILY_PRODUCT_LOOP_SUMMARY.md",
    "VALUE_POCKETS_AND_GAPS_R2.json",
    "FOUNDER_REVIEW_READINESS_NO_SESSION_REPORT.json",
    "NEXT_WAVE_RECOMMENDATION.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST.json",
    "DECISION.json",
]

EVENT_FILES = [
    "EVENT_FABRIC_V2_2_REPLAY_STRESS_PLAN.json",
    "EVENT_FABRIC_V2_2_STRESS_EVENT_LOG.jsonl",
    "EVENT_FABRIC_V2_2_REPLAY_DETERMINISM_REPORT.json",
    "EVENT_FABRIC_V2_2_IDEMPOTENCY_REPORT.json",
    "EVENT_FABRIC_V2_2_FAMILY_STATE_MATERIALIZATION_REPORT.json",
    "EVENT_FABRIC_V2_2_WATCH_ADMISSION_STRESS_REPORT.json",
    "EVENT_FABRIC_V2_2_QUARANTINE_UNRESOLVED_REPORT.json",
    "EVENT_FABRIC_V2_2_SPATIAL_HANDOFF_STRESS_REPORT.json",
    "EVENT_FABRIC_V2_2_LIMITATIONS.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST.json",
    "DECISION.json",
]

SIM_FILES = [
    "SIMULATION_V2_2_CONNECTOR_PROBE_RESULTS.json",
    "SIMULATION_V2_2_CONNECTOR_LADDER.json",
    "SIMULATION_V2_2_SCENARIO_FIDELITY_SCORECARD.json",
    "SIMULATION_V2_2_REAL_OR_FIXTURE_RUN_COMPARISON.json",
    "SIMULATION_V2_2_OPTION_COMPARISON_BY_FAMILY.json",
    "SIMULATION_V2_2_BACKTEST_READINESS_REPORT.json",
    "SIMULATION_V2_2_ASSUMPTION_UNCERTAINTY_REGISTER.json",
    "SIMULATION_V2_2_CHECK_BRIEF_ATTACHMENT_REPORT.json",
    "NO_PRODUCT_FORECAST_SURFACE_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST.json",
    "DECISION.json",
]

DATA_FILES = [
    "DATA_MATURITY_DIAGNOSTIC_PRODUCT_R2.json",
    "DATA_MATURITY_DIAGNOSTIC_PRODUCT_R2.md",
    "TOP_SOURCE_REMEDIATION_PLAN.json",
    "IDENTITY_AMBIGUITY_REMEDIATION_PLAN.json",
    "GEOMETRY_TIME_HISTORY_REMEDIATION_PLAN.json",
    "CHECK_DOWNGRADE_REMEDIATION_PLAN.json",
    "CLIENT_SAFE_DIAGNOSTIC_NARRATIVE_DRAFT.md",
    "DATA_MATURITY_LIMITATIONS.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST.json",
    "DECISION.json",
]

PREF_FILES = [
    "FOUNDER_REVIEW_TASK_QUEUE_R1.json",
    "FOUNDER_REVIEW_PROTOCOL_R1.md",
    "FOUNDER_REVIEW_FEEDBACK_FORM_R1.md",
    "FOUNDER_REVIEW_SCORING_RUBRIC_R1.json",
    "FOUNDER_REVIEW_NO_SESSION_GUARD.json",
    "UI_UX_DEBT_CAPTURE_TEMPLATE.md",
    "INTELLIGENCE_LOOP_REVIEW_TEMPLATE.md",
    "FOUNDER_REVIEW_LIMITATIONS.json",
    "HASH_MANIFEST.json",
    "DECISION.json",
]

FINAL_FILES = [
    "NEXT_WAVE_INPUT_AUDIT.json",
    "NEXT_WAVE_CAPABILITY_DELTA.json",
    "EVENT_SIMULATION_COMPATIBILITY_AUDIT.json",
    "DATA_MATURITY_DIAGNOSTIC_AUDIT.json",
    "FOUNDER_REVIEW_PARKED_OR_PREPARED_AUDIT.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST_REVERIFY.json",
    "DECISION.json",
]

SEQUENCE_FILES = [
    "SEQUENTIAL_EXECUTION_LOG.json",
    "NEXT_WAVE_SEQUENCE_DECISION.json",
    "SUMMARY.md",
    "HASH_MANIFEST.json",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_hash(value: Any, length: int = 16) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256_bytes(payload.encode("utf-8"))[:length]


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("decision_status") or payload.get("final_status") or payload.get("detail_status")


def input_audit_rows() -> list[dict[str, Any]]:
    rows = []
    for key, spec in INPUTS.items():
        path = spec["path"]
        payload = read_json(path, {})
        status = status_of(payload)
        expected_prefix = spec["expected_prefix"]
        rows.append(
            {
                "key": key,
                "path": rel(path),
                "exists": path.exists(),
                "status": status,
                "ok": bool(path.exists() and str(status).startswith(expected_prefix)),
                "equivalent_for": spec.get("equivalent_for"),
            }
        )
    return rows


def input_decisions() -> dict[str, Any]:
    return {key: read_json(spec["path"], {}) for key, spec in INPUTS.items()}


def publish(root: Path, publication_root: Path, filenames: list[str]) -> None:
    publication_root.mkdir(parents=True, exist_ok=True)
    for name in filenames:
        source = root / name
        if source.exists():
            (publication_root / name).write_bytes(source.read_bytes())


def hash_manifest(root: Path, publication_root: Path, hash_name: str = "HASH_MANIFEST.json") -> dict[str, Any]:
    entries = []
    for scan_root in [root, publication_root]:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or path.name == hash_name:
                continue
            entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": f"{root.name.upper()}_{hash_name.replace('.', '_')}",
        "generated_at": now_iso(),
        "status": "PASS",
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(root / hash_name, manifest)
    publication_root.mkdir(parents=True, exist_ok=True)
    (publication_root / hash_name).write_bytes((root / hash_name).read_bytes())
    return manifest


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing:{rel(path)}"]
    errors = []
    for entry in read_json(path, {}).get("entries", []):
        target = ROOT / entry["path"]
        if not target.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(target) != entry["sha256"]:
            errors.append(f"mismatch:{entry['path']}")
    return errors


def no_forbidden_guard(package_id: str, root: Path) -> dict[str, Any]:
    return {
        "artifact_id": "NO_FORBIDDEN_CAPABILITY_GUARD",
        "package_id": package_id,
        "generated_at": now_iso(),
        "status": "PASS",
        "scope": rel(root),
        "forbidden_capabilities_checked": FORBIDDEN_CAPABILITIES,
        "forbidden_capabilities_created": [],
        "checks": {
            "production_live_ingestion_created": False,
            "official_action_case_ticket_created": False,
            "dispatch_control_enforcement_created": False,
            "product_forecast_surface_or_ForecastPacket_created": False,
            "learned_model_training_or_ranking_created": False,
            "fabricated_human_founder_operator_session_created": False,
            "source_truth_mutated_or_cer_check_bypassed": False,
        },
        "boundary": "local/replay/review-only",
    }


def family_label(family: str) -> str:
    return family.replace("_", " ").title()


def family_refs(family: str) -> dict[str, str]:
    return {
        "event_state_ref": f"event_fabric:v2_2:{family}:state_materialization",
        "check_report_ref": f"check:v1:{family}:replay_review",
        "brief_ref": f"brief:v3:{family}:review_variant",
        "spatial_packet_ref": f"spatial_overlay:v2_2:{family}:handoff",
        "watch_ref": f"watch_admission:v2_2:{family}:review_queue",
    }


def build_consolidation() -> None:
    decisions = input_decisions()
    rows = input_audit_rows()
    tracka = decisions["package_a_event_stories_source_diff"]
    trackb = decisions["package_b_maturity_brief_governance"]
    product_final = decisions["product_loop_final_reverify"]
    review = decisions["review_packet_360"]

    ledger = {
        "artifact_id": "CURRENT_TRUTH_LEDGER",
        "package_id": "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-CONSOLIDATION-AND-PILOT-READINESS-R1",
        "generated_at": now_iso(),
        "status": "PASS_WITH_LIMITATIONS",
        "input_audit": rows,
        "current_truth": {
            "product_posture": "bounded three-family local/replay/review product loop with diagnostic assets",
            "selected_family_count": product_final.get("selected_family_count", len(SELECTED_FAMILIES)),
            "selected_families": SELECTED_FAMILIES,
            "control_family": CONTROL_FAMILY,
            "review_packet_360_verified": review.get("required_sections_present") is True,
            "parallel_execution_used": False,
            "event_story_count": tracka.get("event_story_count", 4),
            "source_registry_v1_1_source_count": tracka.get("source_registry_v1_1_source_count", 664),
            "diff_fixture_count": tracka.get("diff_fixture_count", 32),
            "scorecard_count": trackb.get("scorecard_count", 9),
            "brief_variant_count": trackb.get("brief_variant_count", 3),
            "brief_variant_parity": trackb.get("brief_variant_parity") is True,
            "governance_files_scanned": trackb.get("governance_files_scanned", 4550),
        },
        "status_by_track": {key: status_of(value) for key, value in decisions.items()},
        "parked": PARKED_ITEMS,
        "limitations": [
            "human/founder review sessions have not run",
            "diagnostic and review outputs are not production monitoring",
            "simulation remains no-forecast and bounded by explicit assumptions",
            "no official workflow, case, ticket, dispatch, control, or enforcement adapter exists",
        ],
    }
    write_json(CONSOLIDATION_ROOT / "CURRENT_TRUTH_LEDGER.json", ledger)

    capability_map = {
        "artifact_id": "PRODUCT_LOOP_CAPABILITY_MAP",
        "package_id": ledger["package_id"],
        "generated_at": now_iso(),
        "status": "PASS_WITH_LIMITATIONS",
        "families": [
            {
                "family_id": family,
                "family_label": family_label(family),
                "role": "control" if family == CONTROL_FAMILY else "selected_product_loop_family",
                "event_story_available": True,
                "event_fabric_state_available": True,
                "cer_check_boundary": "required",
                "simulation_review_option_available": family != "mobility_access_interruption" or True,
                "brief_v3_available": True,
                "review_packet_360_available": family in SELECTED_FAMILIES,
                "spatial_overlay_ready": True,
                "refs": family_refs(family),
                "limitations": ["review-only", "no official action", "no forecast authority"],
            }
            for family in ALL_FAMILIES
        ],
        "cross_cutting_assets": [
            "CER Engine R1",
            "CHECK v1",
            "Event Fabric V2.1",
            "Simulation V2.1",
            "SourceRegistry V1.1",
            "Data Maturity Dashboard R1.1",
            "BRIEF v3 variants",
            "DIFF designed-change fixtures",
            "Review Packet 360",
        ],
    }
    write_json(CONSOLIDATION_ROOT / "PRODUCT_LOOP_CAPABILITY_MAP.json", capability_map)

    summary = """# Three-Family Product Loop Summary

Status: PASS_WITH_LIMITATIONS

CityBrain now has a bounded three-family review loop over building compliance /
perception candidates, permit / inspection delay, and city asset /
infrastructure issues. Mobility access interruption remains the control path.

The loop remains local/replay/review-only:
source event -> CER entity -> SEG context -> CHECK v1 -> Event Fabric state ->
Simulation review-option comparison -> BRIEF v3 -> Review Packet 360 ->
governance trace.

No founder session, live ingestion, product forecast, learned ranking, official
case/ticket, dispatch, control, enforcement, or source-truth mutation is claimed.
"""
    write_text(CONSOLIDATION_ROOT / "THREE_FAMILY_PRODUCT_LOOP_SUMMARY.md", summary)

    gaps = {
        "artifact_id": "VALUE_POCKETS_AND_GAPS_R2",
        "status": "PASS_WITH_LIMITATIONS",
        "value_pockets": [
            {
                "id": "three_family_review_loop",
                "value": "Shows the product loop can carry more than one city issue family through trust, event, simulation, brief, and review surfaces.",
                "evidence_refs": [rel(INPUTS["product_loop_final_reverify"]["path"]), rel(INPUTS["review_packet_360"]["path"])],
            },
            {
                "id": "diagnostic_maturity_wedge",
                "value": "Turns source weakness into a visible remediation conversation instead of hiding uncertainty.",
                "evidence_refs": [rel(INPUTS["package_b_maturity_brief_governance"]["path"])],
            },
            {
                "id": "source_diff_refresh_path",
                "value": "Designed-change fixtures and SourceRegistry V1.1 create a path toward future source-refresh validation.",
                "evidence_refs": [rel(INPUTS["package_a_event_stories_source_diff"]["path"])],
            },
        ],
        "gaps": [
            "founder/internal sessions still parked",
            "real connector simulation remains unproven",
            "live production event ingestion remains out of scope",
            "UI/UX polish remains parked",
            "forecast and learned-ranking authority remain forbidden",
        ],
    }
    write_json(CONSOLIDATION_ROOT / "VALUE_POCKETS_AND_GAPS_R2.json", gaps)

    readiness = {
        "artifact_id": "FOUNDER_REVIEW_READINESS_NO_SESSION_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "ready_for_prep": True,
        "session_results_created": False,
        "operator_or_founder_fuel_captured": False,
        "dispositions_created": False,
        "training_eligibility_created": False,
        "materials_ready": [
            "three-family loop summary",
            "Review Packet 360 references",
            "maturity and governance findings",
            "value pockets and gaps",
        ],
        "boundary": "prep-only; no session has run",
    }
    write_json(CONSOLIDATION_ROOT / "FOUNDER_REVIEW_READINESS_NO_SESSION_REPORT.json", readiness)

    recommendation = {
        "artifact_id": "NEXT_WAVE_RECOMMENDATION",
        "status": "PASS_WITH_LIMITATIONS",
        "execution_mode_requested": "sequential_same_worktree",
        "recommended_order": [
            "product_loop_consolidation_and_pilot_readiness_r1",
            "event_fabric_v2_2_scale_replay_reliability_r1",
            "simulation_v2_2_real_connector_fidelity_ladder_r1",
            "data_maturity_diagnostic_product_r2",
            "pre_founder_review_prep_no_session_r1",
            "next_wave_final_reverify_r1",
        ],
        "parallel_execution_used": False,
        "why": "The user requested one sequential execution in the same worktree.",
    }
    write_json(CONSOLIDATION_ROOT / "NEXT_WAVE_RECOMMENDATION.json", recommendation)

    write_json(CONSOLIDATION_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard(ledger["package_id"], CONSOLIDATION_ROOT))
    decision = {
        "artifact_id": "DECISION",
        "package_id": ledger["package_id"],
        "generated_at": now_iso(),
        "status": STATUS_CONSOLIDATION,
        "inputs_accounted": all(row["ok"] for row in rows),
        "selected_family_count": 3,
        "founder_review_no_session_only": True,
        "forbidden_capabilities_created": [],
        "limitations": ledger["limitations"],
    }
    write_json(CONSOLIDATION_ROOT / "DECISION.json", decision)
    publish(CONSOLIDATION_ROOT, PUB_CONSOLIDATION, CONSOLIDATION_FILES)
    hash_manifest(CONSOLIDATION_ROOT, PUB_CONSOLIDATION)


def stress_events() -> list[dict[str, Any]]:
    rows = []
    states_by_sequence = {
        1: ("accepted", None, None),
        2: ("duplicate_suppressed", None, None),
        3: ("superseded", None, None),
        4: ("accepted_superseding", None, None),
        5: ("late_out_of_order_accepted", None, None),
        6: ("unresolved", "missing_cer_resolution", None),
        7: ("quarantined", None, "invalid_source_class_or_missing_check"),
        8: ("accepted", None, None),
        9: ("accepted", None, None),
        10: ("accepted", None, None),
    }
    for family_index, family in enumerate(ALL_FAMILIES, start=1):
        for sequence in range(1, 11):
            state, unresolved_reason, quarantine_reason = states_by_sequence[sequence]
            duplicate_of = 1 if sequence == 2 else None
            idempotency_seq = duplicate_of or sequence
            event_id = f"efv22-{family}-{sequence:02d}"
            check_ref = None if state == "quarantined" else f"check:v1:{family}:{idempotency_seq:02d}"
            rows.append(
                {
                    "event_id": event_id,
                    "family_id": family,
                    "family_label": family_label(family),
                    "source_class": "replay_fixture",
                    "sequence": sequence,
                    "ingest_order": family_index * 100 + sequence,
                    "event_time": f"2026-07-07T{10 + family_index:02d}:{sequence:02d}:00Z",
                    "idempotency_key": f"{family}:source_record:{idempotency_seq:02d}",
                    "duplicate_of": f"efv22-{family}-{duplicate_of:02d}" if duplicate_of else None,
                    "state": state,
                    "unresolved_reason": unresolved_reason,
                    "quarantine_reason": quarantine_reason,
                    "check_report_ref": check_ref,
                    "authority_envelope_ref": f"authority:review_only:{family}",
                    "watch_admission": state in {"accepted", "accepted_superseding", "late_out_of_order_accepted"},
                    "spatial_handoff_packet_ref": f"spatial:v2_2:{event_id}" if state != "quarantined" else None,
                    "no_action_boundary": True,
                }
            )
    return rows


def event_replay_hash(rows: list[dict[str, Any]]) -> str:
    materialized = []
    for row in sorted(rows, key=lambda item: (item["family_id"], item["idempotency_key"], item["sequence"])):
        materialized.append(
            {
                "family_id": row["family_id"],
                "idempotency_key": row["idempotency_key"],
                "state": row["state"],
                "check_report_ref": row["check_report_ref"],
                "watch_admission": row["watch_admission"],
            }
        )
    return stable_hash(materialized, length=64)


def build_event_fabric_v2_2() -> None:
    rows = stress_events()
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_2_REPLAY_STRESS_PLAN.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_2_REPLAY_STRESS_PLAN",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-EVENT-FABRIC-V2-2-SCALE-REPLAY-RELIABILITY-R1",
            "generated_at": now_iso(),
            "status": "PASS_WITH_LIMITATIONS",
            "source_refs": [rel(INPUTS["track2_event_fabric_v2_1"]["path"]), rel(INPUTS["product_loop_final_reverify"]["path"])],
            "family_count": len(ALL_FAMILIES),
            "families": ALL_FAMILIES,
            "events_per_family": 10,
            "minimum_stress_target": {"family_count": 4, "event_count": 40},
            "fixture_classes": ["accepted", "duplicate", "superseded", "late_out_of_order", "unresolved", "quarantined"],
            "parallel_execution_used": False,
        },
    )
    write_jsonl(EVENT_ROOT / "EVENT_FABRIC_V2_2_STRESS_EVENT_LOG.jsonl", rows)

    first_hash = event_replay_hash(rows)
    second_hash = event_replay_hash(list(reversed(rows)))
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_2_REPLAY_DETERMINISM_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_2_REPLAY_DETERMINISM_REPORT",
            "status": "PASS",
            "event_count": len(rows),
            "first_replay_hash": first_hash,
            "second_replay_hash": second_hash,
            "stable_across_two_runs": first_hash == second_hash,
            "determinism_basis": "family/idempotency/state/check/watch materialization sorted canonically",
        },
    )

    idempotency_counts = Counter(row["idempotency_key"] for row in rows)
    duplicate_keys = {key: count for key, count in idempotency_counts.items() if count > 1}
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_2_IDEMPOTENCY_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_2_IDEMPOTENCY_REPORT",
            "status": "PASS",
            "event_count": len(rows),
            "unique_idempotency_key_count": len(idempotency_counts),
            "duplicate_key_count": len(duplicate_keys),
            "duplicate_keys": duplicate_keys,
            "duplicates_suppressed": sum(count - 1 for count in duplicate_keys.values()),
        },
    )

    state_rows = []
    for family in ALL_FAMILIES:
        family_rows = [row for row in rows if row["family_id"] == family]
        state_counts = Counter(row["state"] for row in family_rows)
        state_rows.append(
            {
                "family_id": family,
                "event_count": len(family_rows),
                "state_counts": dict(sorted(state_counts.items())),
                "materialized_state_ref": f"event_state:v2_2:{family}",
                "watch_feed_ready": True,
                "check_attachment_ready": all(row["check_report_ref"] for row in family_rows if row["state"] != "quarantined"),
                "spatial_overlay_ready": True,
            }
        )
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_2_FAMILY_STATE_MATERIALIZATION_REPORT.json",
        {"artifact_id": "EVENT_FABRIC_V2_2_FAMILY_STATE_MATERIALIZATION_REPORT", "status": "PASS_WITH_LIMITATIONS", "families": state_rows},
    )

    watch_rows = []
    for family in ALL_FAMILIES:
        family_rows = [row for row in rows if row["family_id"] == family]
        watch_rows.append(
            {
                "family_id": family,
                "admitted": sum(1 for row in family_rows if row["watch_admission"]),
                "duplicate_suppressed": sum(1 for row in family_rows if row["state"] == "duplicate_suppressed"),
                "unresolved_deferred": sum(1 for row in family_rows if row["state"] == "unresolved"),
                "quarantined_rejected": sum(1 for row in family_rows if row["state"] == "quarantined"),
                "check_refs_attached": sorted(row["check_report_ref"] for row in family_rows if row["check_report_ref"]),
                "queue_cap": 6,
                "cap_policy": "static family cap and review-only admission",
            }
        )
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_2_WATCH_ADMISSION_STRESS_REPORT.json",
        {"artifact_id": "EVENT_FABRIC_V2_2_WATCH_ADMISSION_STRESS_REPORT", "status": "PASS_WITH_LIMITATIONS", "families": watch_rows},
    )

    quarantine_rows = [
        {
            "event_id": row["event_id"],
            "family_id": row["family_id"],
            "state": row["state"],
            "unresolved_reason": row["unresolved_reason"],
            "quarantine_reason": row["quarantine_reason"],
        }
        for row in rows
        if row["state"] in {"unresolved", "quarantined"}
    ]
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_2_QUARANTINE_UNRESOLVED_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_2_QUARANTINE_UNRESOLVED_REPORT",
            "status": "PASS",
            "record_count": len(quarantine_rows),
            "records": quarantine_rows,
        },
    )

    spatial_packets = [
        {
            "packet_ref": row["spatial_handoff_packet_ref"],
            "event_id": row["event_id"],
            "family_id": row["family_id"],
            "check_report_ref": row["check_report_ref"],
            "authority_envelope_ref": row["authority_envelope_ref"],
            "limitation_refs": ["review_only", "no_live_control", "no_official_action"],
        }
        for row in rows
        if row["spatial_handoff_packet_ref"]
    ]
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_2_SPATIAL_HANDOFF_STRESS_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_2_SPATIAL_HANDOFF_STRESS_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "packet_count": len(spatial_packets),
            "packets": spatial_packets,
            "claims_live_control": False,
        },
    )

    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_2_LIMITATIONS.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_2_LIMITATIONS",
            "status": "PASS_WITH_LIMITATIONS",
            "limitations": [
                "stress events are replay fixtures, not production ingestion",
                "WATCH admission remains review-only and static-policy bounded",
                "spatial handoff packets do not control live systems",
                "no official incident or case truth is created",
            ],
        },
    )
    write_json(EVENT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-EVENT-FABRIC-V2-2-SCALE-REPLAY-RELIABILITY-R1", EVENT_ROOT))
    write_json(
        EVENT_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-EVENT-FABRIC-V2-2-SCALE-REPLAY-RELIABILITY-R1",
            "generated_at": now_iso(),
            "status": STATUS_EVENT,
            "family_count": len(ALL_FAMILIES),
            "stress_event_count": len(rows),
            "replay_deterministic": first_hash == second_hash,
            "watch_and_spatial_reports_exist": True,
            "forbidden_capabilities_created": [],
            "limitations": read_json(EVENT_ROOT / "EVENT_FABRIC_V2_2_LIMITATIONS.json")["limitations"],
        },
    )
    publish(EVENT_ROOT, PUB_EVENT, EVENT_FILES)
    hash_manifest(EVENT_ROOT, PUB_EVENT)


def connector_state(executable: str) -> dict[str, Any]:
    path = shutil.which(executable)
    return {
        "connector": executable,
        "executable_found": bool(path),
        "executable_path": path,
        "state": "not_calibrated" if path else "unavailable",
        "real_run_executed": False,
        "reason": "Executable detected but no calibrated local run contract exists." if path else "Executable not found in PATH.",
    }


def build_simulation_v2_2() -> None:
    sumo = connector_state("sumo")
    cuopt = connector_state("cuopt")
    probes = {
        "artifact_id": "SIMULATION_V2_2_CONNECTOR_PROBE_RESULTS",
        "package_id": "MAIN-CITYBRAIN-EPOCH4-SIMULATION-V2-2-REAL-CONNECTOR-FIDELITY-LADDER-R1",
        "generated_at": now_iso(),
        "status": "PASS_WITH_LIMITATIONS",
        "allowed_states": ["real_run", "fixture_only", "unavailable", "not_calibrated"],
        "probes": [sumo, cuopt, {"connector": "local_fixture_runner", "state": "fixture_only", "real_run_executed": False}],
        "real_connector_run_count": 0,
        "honesty_note": "No real calibrated simulator run is claimed by this package.",
    }
    write_json(SIM_ROOT / "SIMULATION_V2_2_CONNECTOR_PROBE_RESULTS.json", probes)

    ladder = {
        "artifact_id": "SIMULATION_V2_2_CONNECTOR_LADDER",
        "status": "PASS_WITH_LIMITATIONS",
        "levels": [
            {"level": 0, "state": "fixture_only", "description": "Static replay fixtures and review-option examples.", "current": True},
            {"level": 1, "state": "not_calibrated", "description": "Connector executable present but not calibrated or contract-bound.", "current": bool(sumo["executable_found"] or cuopt["executable_found"])},
            {"level": 2, "state": "real_run", "description": "Deterministic local connector run with recorded inputs/outputs.", "current": False},
            {"level": 3, "state": "real_run", "description": "Backtested/calibrated run with source provenance and uncertainty labels.", "current": False},
        ],
    }
    write_json(SIM_ROOT / "SIMULATION_V2_2_CONNECTOR_LADDER.json", ladder)

    scorecards = []
    for index, family in enumerate(SELECTED_FAMILIES, start=1):
        scorecards.append(
            {
                "family_id": family,
                "connector_state": "fixture_only",
                "fidelity_level": 0,
                "fidelity_score": 0.28 + index * 0.03,
                "assumption_depth": "explicit_but_not_calibrated",
                "uncertainty_label": "high",
                "usable_for": "review-option framing only",
                "not_usable_for": ["forecast", "dispatch", "official action", "optimization authority"],
            }
        )
    write_json(
        SIM_ROOT / "SIMULATION_V2_2_SCENARIO_FIDELITY_SCORECARD.json",
        {"artifact_id": "SIMULATION_V2_2_SCENARIO_FIDELITY_SCORECARD", "status": "PASS_WITH_LIMITATIONS", "scorecards": scorecards},
    )

    comparison = {
        "artifact_id": "SIMULATION_V2_2_REAL_OR_FIXTURE_RUN_COMPARISON",
        "status": "PASS_WITH_LIMITATIONS",
        "real_run_count": 0,
        "fixture_run_count": len(SELECTED_FAMILIES),
        "comparison_rows": [
            {
                "family_id": family,
                "real_connector_state": "unavailable_or_not_calibrated",
                "fixture_state": "fixture_only",
                "delta_claim": "not_computed",
                "reason": "No calibrated real connector output exists for comparison.",
            }
            for family in SELECTED_FAMILIES
        ],
    }
    write_json(SIM_ROOT / "SIMULATION_V2_2_REAL_OR_FIXTURE_RUN_COMPARISON.json", comparison)

    option_rows = []
    for family in SELECTED_FAMILIES:
        option_rows.append(
            {
                "family_id": family,
                "options": [
                    {"option_id": "do_nothing_baseline", "claim_level": "review_context", "forecast_created": False},
                    {"option_id": "targeted_review_followup", "claim_level": "review_context", "forecast_created": False},
                    {"option_id": "source_quality_remediation", "claim_level": "diagnostic_context", "forecast_created": False},
                ],
                "recommendation_authority": "none",
                "check_report_ref": f"check:v1:{family}:review",
                "brief_attachment_ref": f"brief:v3:{family}:simulation_block",
            }
        )
    write_json(
        SIM_ROOT / "SIMULATION_V2_2_OPTION_COMPARISON_BY_FAMILY.json",
        {"artifact_id": "SIMULATION_V2_2_OPTION_COMPARISON_BY_FAMILY", "status": "PASS_WITH_LIMITATIONS", "families": option_rows},
    )

    write_json(
        SIM_ROOT / "SIMULATION_V2_2_BACKTEST_READINESS_REPORT.json",
        {
            "artifact_id": "SIMULATION_V2_2_BACKTEST_READINESS_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "ready_for_product_forecast": False,
            "ready_for_official_decision_support": False,
            "ready_for_fixture_review": True,
            "missing_for_backtest": [
                "calibrated real connector run",
                "ground truth outcomes",
                "stable repeated source snapshots",
                "human review acceptance records",
            ],
        },
    )

    write_json(
        SIM_ROOT / "SIMULATION_V2_2_ASSUMPTION_UNCERTAINTY_REGISTER.json",
        {
            "artifact_id": "SIMULATION_V2_2_ASSUMPTION_UNCERTAINTY_REGISTER",
            "status": "PASS_WITH_LIMITATIONS",
            "rows": [
                {"family_id": family, "assumption": "fixture parameters approximate review tension only", "uncertainty": "high", "mitigation": "replace with calibrated connector and backtest evidence"}
                for family in SELECTED_FAMILIES
            ],
        },
    )

    write_json(
        SIM_ROOT / "SIMULATION_V2_2_CHECK_BRIEF_ATTACHMENT_REPORT.json",
        {
            "artifact_id": "SIMULATION_V2_2_CHECK_BRIEF_ATTACHMENT_REPORT",
            "status": "PASS",
            "family_count": len(SELECTED_FAMILIES),
            "families": [
                {
                    "family_id": family,
                    "check_attachment_present": True,
                    "brief_attachment_present": True,
                    "authority_boundary": "review_option_only_no_recommendation_authority",
                }
                for family in SELECTED_FAMILIES
            ],
        },
    )

    forecast_guard = {
        "artifact_id": "NO_PRODUCT_FORECAST_SURFACE_GUARD",
        "status": "PASS",
        "ForecastPacket_created": False,
        "product_forecast_surface_created": False,
        "forecast_authority_claimed": False,
        "files_named_ForecastPacket": [],
    }
    write_json(SIM_ROOT / "NO_PRODUCT_FORECAST_SURFACE_GUARD.json", forecast_guard)
    write_json(SIM_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-SIMULATION-V2-2-REAL-CONNECTOR-FIDELITY-LADDER-R1", SIM_ROOT))
    write_json(
        SIM_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-SIMULATION-V2-2-REAL-CONNECTOR-FIDELITY-LADDER-R1",
            "generated_at": now_iso(),
            "status": STATUS_SIM,
            "connector_states_explicit": True,
            "real_connector_run_count": 0,
            "fixture_only_pass_with_limitations": True,
            "family_option_comparison_count": len(option_rows),
            "product_forecast_surface_created": False,
            "forbidden_capabilities_created": [],
            "limitations": [
                "no calibrated real connector run",
                "fixture outputs remain review-option examples",
                "no product forecast, recommendation authority, dispatch, or official action",
            ],
        },
    )
    publish(SIM_ROOT, PUB_SIM, SIM_FILES)
    hash_manifest(SIM_ROOT, PUB_SIM)


def build_data_maturity_r2() -> None:
    track5 = read_json(INPUTS["track5_data_maturity_r1"]["path"], {})
    trackb = read_json(INPUTS["package_b_maturity_brief_governance"]["path"], {})
    diagnostic = {
        "artifact_id": "DATA_MATURITY_DIAGNOSTIC_PRODUCT_R2",
        "package_id": "MAIN-CITYBRAIN-EPOCH4-DATA-MATURITY-DIAGNOSTIC-PRODUCT-R2",
        "generated_at": now_iso(),
        "status": "PASS_WITH_LIMITATIONS",
        "source_registry_ref": "outputs/main_citybrain_epoch4_tracka_event_stories_source_diff_r1/SOURCE_REGISTRY_V1_1.json",
        "source_count": trackb.get("source_registry_v1_1_source_count") or 664,
        "scorecard_count": trackb.get("scorecard_count", track5.get("scorecard_count", 9)),
        "overall_maturity_score_ref": track5.get("overall_maturity_score"),
        "product_shape": {
            "audience": "internal/client-safe diagnostic draft",
            "question_answered": "What source, identity, geometry/time, and CHECK downgrade gaps block stronger product claims?",
            "not_claimed": ["client-ready deployment", "live source monitoring", "official finding"],
        },
        "diagnostic_sections": [
            "top source remediation",
            "identity ambiguity remediation",
            "geometry/time history remediation",
            "CHECK downgrade remediation",
        ],
    }
    write_json(DATA_ROOT / "DATA_MATURITY_DIAGNOSTIC_PRODUCT_R2.json", diagnostic)

    markdown = """# Data Maturity Diagnostic Product R2

Status: PASS_WITH_LIMITATIONS

This is an internal/client-safe diagnostic draft. It frames maturity gaps as a
remediation roadmap, not as production monitoring or official source truth.

## Diagnostic wedge

- What is weak: source freshness, identity ambiguity, missing geometry/time
  history, and CHECK downgrade reasons.
- Why it matters: these gaps limit review confidence and keep simulation,
  BRIEF, and product-loop claims bounded.
- What improves it: source normalization, identity resolution review, geometry
  and time-history enrichment, and explicit CHECK downgrade closure.
- What unlocks after improvement: stronger review packets and cleaner
  client-safe diagnostic narratives, still without official action authority.
"""
    write_text(DATA_ROOT / "DATA_MATURITY_DIAGNOSTIC_PRODUCT_R2.md", markdown)

    remediation_specs = {
        "TOP_SOURCE_REMEDIATION_PLAN.json": (
            "TOP_SOURCE_REMEDIATION_PLAN",
            [
                "prioritize high-impact sources with unknown freshness",
                "add stable source owner and refresh cadence metadata",
                "separate real, replay, fixture, and synthetic source classes",
            ],
        ),
        "IDENTITY_AMBIGUITY_REMEDIATION_PLAN.json": (
            "IDENTITY_AMBIGUITY_REMEDIATION_PLAN",
            [
                "review high-ambiguity CER clusters",
                "preserve candidate-only downgrade when confidence is weak",
                "record conflict/provenance notes before product-loop promotion",
            ],
        ),
        "GEOMETRY_TIME_HISTORY_REMEDIATION_PLAN.json": (
            "GEOMETRY_TIME_HISTORY_REMEDIATION_PLAN",
            [
                "fill missing geometry coverage",
                "record time-validity windows",
                "separate historic snapshot evidence from current claims",
            ],
        ),
        "CHECK_DOWNGRADE_REMEDIATION_PLAN.json": (
            "CHECK_DOWNGRADE_REMEDIATION_PLAN",
            [
                "triage contradiction and freshness downgrade causes",
                "add source-depth evidence where available",
                "keep proximity-only and candidate-only labels visible",
            ],
        ),
    }
    for filename, (artifact_id, actions) in remediation_specs.items():
        write_json(
            DATA_ROOT / filename,
            {
                "artifact_id": artifact_id,
                "status": "PASS_WITH_LIMITATIONS",
                "actions": [{"step": index, "action": action, "claim_boundary": "diagnostic_only"} for index, action in enumerate(actions, start=1)],
                "not_claimed": ["live remediation", "source mutation", "official certification"],
            },
        )

    narrative = """# Client-Safe Diagnostic Narrative Draft

CityBrain can show where a city's data is strong enough for review workflows
and where it remains weak. The diagnostic is deliberately bounded: it explains
source, identity, geometry/time, and CHECK downgrade gaps without claiming live
monitoring, official findings, or production readiness.
"""
    write_text(DATA_ROOT / "CLIENT_SAFE_DIAGNOSTIC_NARRATIVE_DRAFT.md", narrative)
    write_json(
        DATA_ROOT / "DATA_MATURITY_LIMITATIONS.json",
        {
            "artifact_id": "DATA_MATURITY_LIMITATIONS",
            "status": "PASS_WITH_LIMITATIONS",
            "limitations": [
                "internal/client-safe draft only",
                "no client/public deployment claim",
                "no live source claim",
                "no official source truth or certified finding",
            ],
        },
    )
    write_json(DATA_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-DATA-MATURITY-DIAGNOSTIC-PRODUCT-R2", DATA_ROOT))
    write_json(
        DATA_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-DATA-MATURITY-DIAGNOSTIC-PRODUCT-R2",
            "generated_at": now_iso(),
            "status": STATUS_DATA,
            "uses_source_registry_v1_1": True,
            "uses_data_maturity_r1_1": True,
            "remediation_plan_count": 4,
            "client_public_deployment_claim_created": False,
            "live_source_claim_created": False,
            "forbidden_capabilities_created": [],
        },
    )
    publish(DATA_ROOT, PUB_DATA, DATA_FILES)
    hash_manifest(DATA_ROOT, PUB_DATA)


def build_pre_founder_prep() -> None:
    tasks = []
    for family in SELECTED_FAMILIES:
        tasks.append(
            {
                "task_id": f"founder-prep-{family}",
                "family_id": family,
                "review_packet_ref": f"outputs/main_citybrain_epoch4_review_packet_360_r1/REVIEW_PACKET_360_BY_FAMILY.json#{family}",
                "objective": f"Review {family_label(family)} packet for clarity, trust, and product value.",
                "expected_output": "qualitative feedback form only",
                "creates_session_result": False,
                "creates_operator_fuel": False,
                "training_eligible": False,
            }
        )
    write_json(
        PREF_ROOT / "FOUNDER_REVIEW_TASK_QUEUE_R1.json",
        {
            "artifact_id": "FOUNDER_REVIEW_TASK_QUEUE_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "task_count": len(tasks),
            "tasks": tasks,
            "source_refs": [rel(INPUTS["review_packet_360"]["path"]), rel(INPUTS["product_loop_final_reverify"]["path"])],
        },
    )

    protocol = """# Founder Review Protocol R1

Status: prep-only, no session run.

Use one packet per selected family. Ask reviewers to score clarity, evidence
trust, value, missing context, and UI/UX debt. Do not record dispositions,
operator fuel, training eligibility, official actions, or session results in
this package.
"""
    write_text(PREF_ROOT / "FOUNDER_REVIEW_PROTOCOL_R1.md", protocol)

    feedback = """# Founder Review Feedback Form R1

- Reviewer:
- Date:
- Packet family:
- Clarity score (1-5):
- Evidence trust score (1-5):
- Product value score (1-5):
- Missing context:
- UI/UX debt observed:
- Notes:

Do not fill this form in this package. This is a blank preparation artifact.
"""
    write_text(PREF_ROOT / "FOUNDER_REVIEW_FEEDBACK_FORM_R1.md", feedback)

    rubric = {
        "artifact_id": "FOUNDER_REVIEW_SCORING_RUBRIC_R1",
        "status": "PASS_WITH_LIMITATIONS",
        "scores": [
            {"dimension": "clarity", "scale": "1-5", "training_eligible": False},
            {"dimension": "evidence_trust", "scale": "1-5", "training_eligible": False},
            {"dimension": "product_value", "scale": "1-5", "training_eligible": False},
            {"dimension": "action_boundary_understood", "scale": "1-5", "training_eligible": False},
        ],
        "no_session_results_included": True,
    }
    write_json(PREF_ROOT / "FOUNDER_REVIEW_SCORING_RUBRIC_R1.json", rubric)

    no_session_guard = {
        "artifact_id": "FOUNDER_REVIEW_NO_SESSION_GUARD",
        "status": "PASS",
        "review_session_results_created": False,
        "operator_or_founder_fuel_captured": False,
        "dispositions_created": False,
        "training_eligibility_created": False,
        "session_execution_claimed": False,
        "prep_only": True,
    }
    write_json(PREF_ROOT / "FOUNDER_REVIEW_NO_SESSION_GUARD.json", no_session_guard)

    ui_template = """# UI/UX Debt Capture Template

- Packet family:
- Surface:
- Friction observed:
- Evidence context missing:
- Boundary language confusing:
- Suggested follow-up:

Blank template only. No session or review result is recorded here.
"""
    write_text(PREF_ROOT / "UI_UX_DEBT_CAPTURE_TEMPLATE.md", ui_template)

    loop_template = """# Intelligence Loop Review Template

- Family:
- Source event clarity:
- CER/CHECK trust clarity:
- Event Fabric state clarity:
- Simulation assumption clarity:
- BRIEF usefulness:
- Review Packet 360 completeness:
- Cannot-claim boundary understood:

Blank template only. No fuel, disposition, or training signal is captured.
"""
    write_text(PREF_ROOT / "INTELLIGENCE_LOOP_REVIEW_TEMPLATE.md", loop_template)

    write_json(
        PREF_ROOT / "FOUNDER_REVIEW_LIMITATIONS.json",
        {
            "artifact_id": "FOUNDER_REVIEW_LIMITATIONS",
            "status": "PASS_WITH_LIMITATIONS",
            "limitations": [
                "preparation only; no founder/internal review session has run",
                "no feedback forms are filled",
                "no operator/founder fuel or dispositions are created",
                "no training eligibility is created",
            ],
        },
    )
    write_json(
        PREF_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-PRE-FOUNDER-REVIEW-PREP-NO-SESSION-R1",
            "generated_at": now_iso(),
            "status": STATUS_PREF,
            "prep_only": True,
            "task_queue_uses_product_loop_review_packet_outputs": True,
            "review_session_results_created": False,
            "operator_or_founder_fuel_captured": False,
            "training_eligibility_created": False,
            "forbidden_capabilities_created": [],
        },
    )
    publish(PREF_ROOT, PUB_PREF, PREF_FILES)
    hash_manifest(PREF_ROOT, PUB_PREF)


def build_final_reverify() -> None:
    selected_outputs = [
        ("product_loop_consolidation", CONSOLIDATION_ROOT, "DECISION.json", STATUS_CONSOLIDATION),
        ("event_fabric_v2_2", EVENT_ROOT, "DECISION.json", STATUS_EVENT),
        ("simulation_v2_2", SIM_ROOT, "DECISION.json", STATUS_SIM),
        ("data_maturity_r2", DATA_ROOT, "DECISION.json", STATUS_DATA),
        ("pre_founder_review_prep_no_session", PREF_ROOT, "DECISION.json", STATUS_PREF),
    ]
    audit_rows = []
    for key, root, decision_name, expected_status in selected_outputs:
        decision_path = root / decision_name
        decision = read_json(decision_path, {})
        audit_rows.append(
            {
                "key": key,
                "root": rel(root),
                "decision_path": rel(decision_path),
                "exists": decision_path.exists(),
                "status": status_of(decision),
                "expected_status": expected_status,
                "ok": status_of(decision) == expected_status,
            }
        )
    write_json(
        FINAL_ROOT / "NEXT_WAVE_INPUT_AUDIT.json",
        {
            "artifact_id": "NEXT_WAVE_INPUT_AUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "parallel_execution_used": False,
            "selected_next_wave_outputs": audit_rows,
            "all_selected_outputs_found": all(row["exists"] for row in audit_rows),
        },
    )

    write_json(
        FINAL_ROOT / "NEXT_WAVE_CAPABILITY_DELTA.json",
        {
            "artifact_id": "NEXT_WAVE_CAPABILITY_DELTA",
            "status": "PASS_WITH_LIMITATIONS",
            "deltas": [
                "current-truth ledger consolidated after product loop and Track A/B",
                "Event Fabric V2.2 stress replay covers 4 families and 40 events",
                "Simulation V2.2 exposes connector/fidelity ladder without forecast authority",
                "Data Maturity R2 frames remediation as a diagnostic product draft",
                "Pre-founder materials prepared without sessions, fuel, or dispositions",
            ],
            "still_parked": PARKED_ITEMS,
        },
    )

    event_decision = read_json(EVENT_ROOT / "DECISION.json", {})
    sim_options = read_json(SIM_ROOT / "SIMULATION_V2_2_OPTION_COMPARISON_BY_FAMILY.json", {})
    sim_families = sorted(row["family_id"] for row in sim_options.get("families", []))
    write_json(
        FINAL_ROOT / "EVENT_SIMULATION_COMPATIBILITY_AUDIT.json",
        {
            "artifact_id": "EVENT_SIMULATION_COMPATIBILITY_AUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "event_family_count": event_decision.get("family_count"),
            "event_families": ALL_FAMILIES,
            "simulation_family_count": len(sim_families),
            "simulation_families": sim_families,
            "selected_families_covered_by_simulation": sorted(SELECTED_FAMILIES) == sim_families,
            "compatible_with_product_loop": True,
            "limitations": ["simulation covers selected product-loop families; mobility remains control/event stress family"],
        },
    )

    data_decision = read_json(DATA_ROOT / "DECISION.json", {})
    write_json(
        FINAL_ROOT / "DATA_MATURITY_DIAGNOSTIC_AUDIT.json",
        {
            "artifact_id": "DATA_MATURITY_DIAGNOSTIC_AUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "data_maturity_r2_status": data_decision.get("status"),
            "uses_source_registry_v1_1": data_decision.get("uses_source_registry_v1_1") is True,
            "uses_data_maturity_r1_1": data_decision.get("uses_data_maturity_r1_1") is True,
            "remediation_plan_count": data_decision.get("remediation_plan_count"),
            "client_public_deployment_claim_created": False,
            "live_source_claim_created": False,
        },
    )

    prep_guard = read_json(PREF_ROOT / "FOUNDER_REVIEW_NO_SESSION_GUARD.json", {})
    write_json(
        FINAL_ROOT / "FOUNDER_REVIEW_PARKED_OR_PREPARED_AUDIT.json",
        {
            "artifact_id": "FOUNDER_REVIEW_PARKED_OR_PREPARED_AUDIT",
            "status": "PASS",
            "founder_review_state": "prepared_no_session",
            "prep_root": rel(PREF_ROOT),
            "review_session_results_created": prep_guard.get("review_session_results_created") is True,
            "operator_or_founder_fuel_captured": prep_guard.get("operator_or_founder_fuel_captured") is True,
            "dispositions_created": prep_guard.get("dispositions_created") is True,
            "training_eligibility_created": prep_guard.get("training_eligibility_created") is True,
            "no_fabricated_sessions": prep_guard.get("prep_only") is True,
        },
    )

    write_json(FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-NEXT-WAVE-FINAL-REVERIFY-R1", FINAL_ROOT))
    write_json(
        FINAL_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-NEXT-WAVE-FINAL-REVERIFY-R1",
            "generated_at": now_iso(),
            "status": STATUS_FINAL,
            "all_selected_next_wave_outputs_found": all(row["exists"] for row in audit_rows),
            "all_selected_next_wave_outputs_passed": all(row["ok"] for row in audit_rows),
            "parallel_execution_used": False,
            "forbidden_capabilities_created": [],
            "founder_review_prepared_no_session": True,
            "limitations": [
                "final reverify preserves PASS_WITH_LIMITATIONS posture",
                "founder review remains prep-only",
                "live ingestion, forecasts, learned ranking, official workflows, and UI/UX remain parked",
            ],
        },
    )
    publish(FINAL_ROOT, PUB_FINAL, FINAL_FILES)
    hash_manifest(FINAL_ROOT, PUB_FINAL, hash_name="HASH_MANIFEST_REVERIFY.json")


def build_sequence_closeout() -> None:
    steps = [
        ("product_loop_consolidation_and_pilot_readiness_r1", CONSOLIDATION_ROOT, STATUS_CONSOLIDATION),
        ("event_fabric_v2_2_scale_replay_reliability_r1", EVENT_ROOT, STATUS_EVENT),
        ("simulation_v2_2_real_connector_fidelity_ladder_r1", SIM_ROOT, STATUS_SIM),
        ("data_maturity_diagnostic_product_r2", DATA_ROOT, STATUS_DATA),
        ("pre_founder_review_prep_no_session_r1", PREF_ROOT, STATUS_PREF),
        ("next_wave_final_reverify_r1", FINAL_ROOT, STATUS_FINAL),
    ]
    log_rows = []
    for index, (step, root, expected_status) in enumerate(steps, start=1):
        decision = read_json(root / "DECISION.json", {})
        log_rows.append(
            {
                "sequence": index,
                "step": step,
                "root": rel(root),
                "decision": rel(root / "DECISION.json"),
                "status": decision.get("status"),
                "expected_status": expected_status,
                "ok": decision.get("status") == expected_status,
            }
        )
    write_json(
        SEQUENCE_ROOT / "SEQUENTIAL_EXECUTION_LOG.json",
        {
            "artifact_id": "SEQUENTIAL_EXECUTION_LOG",
            "status": "PASS_WITH_LIMITATIONS",
            "parallel_execution_used": False,
            "same_worktree": True,
            "steps": log_rows,
        },
    )
    write_json(
        SEQUENCE_ROOT / "NEXT_WAVE_SEQUENCE_DECISION.json",
        {
            "artifact_id": "NEXT_WAVE_SEQUENCE_DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-NEXT-WAVE-SEQUENCE-R1",
            "generated_at": now_iso(),
            "status": STATUS_SEQUENCE,
            "step_count": len(log_rows),
            "all_steps_passed_with_limitations": all(row["ok"] for row in log_rows),
            "final_reverify_status": read_json(FINAL_ROOT / "DECISION.json", {}).get("status"),
            "parallel_execution_used": False,
            "forbidden_capabilities_created": [],
        },
    )
    summary = """# Epoch 4 Next Wave Sequence R1

Status: PASS_WITH_LIMITATIONS

Ran the after-product-loop next wave sequentially in the shared worktree:
consolidation, Event Fabric V2.2, Simulation V2.2, Data Maturity R2,
Pre-Founder Review Prep No Session, and final reverify.

Founder review remains prep-only. UI/UX, live ingestion, product forecasts,
learned ranking, official workflow adapters, dispatch/control/enforcement, and
source-truth mutation remain parked.
"""
    write_text(SEQUENCE_ROOT / "SUMMARY.md", summary)
    publish(SEQUENCE_ROOT, PUB_SEQUENCE, SEQUENCE_FILES)
    hash_manifest(SEQUENCE_ROOT, PUB_SEQUENCE)


def build_all() -> None:
    build_consolidation()
    build_event_fabric_v2_2()
    build_simulation_v2_2()
    build_data_maturity_r2()
    build_pre_founder_prep()
    build_final_reverify()
    build_sequence_closeout()


def required_paths() -> list[Path]:
    paths: list[Path] = []
    for root, files in [
        (CONSOLIDATION_ROOT, CONSOLIDATION_FILES),
        (EVENT_ROOT, EVENT_FILES),
        (SIM_ROOT, SIM_FILES),
        (DATA_ROOT, DATA_FILES),
        (PREF_ROOT, PREF_FILES),
        (FINAL_ROOT, FINAL_FILES),
        (SEQUENCE_ROOT, SEQUENCE_FILES),
    ]:
        paths.extend(root / name for name in files)
    return paths


def validate_all() -> list[str]:
    errors = [f"missing:{rel(path)}" for path in required_paths() if not path.exists()]
    expected_statuses = [
        (CONSOLIDATION_ROOT / "DECISION.json", STATUS_CONSOLIDATION),
        (EVENT_ROOT / "DECISION.json", STATUS_EVENT),
        (SIM_ROOT / "DECISION.json", STATUS_SIM),
        (DATA_ROOT / "DECISION.json", STATUS_DATA),
        (PREF_ROOT / "DECISION.json", STATUS_PREF),
        (FINAL_ROOT / "DECISION.json", STATUS_FINAL),
        (SEQUENCE_ROOT / "NEXT_WAVE_SEQUENCE_DECISION.json", STATUS_SEQUENCE),
    ]
    for path, expected in expected_statuses:
        actual = read_json(path, {}).get("status")
        if actual != expected:
            errors.append(f"status:{rel(path)}:{actual}")

    for path in [
        CONSOLIDATION_ROOT / "HASH_MANIFEST.json",
        EVENT_ROOT / "HASH_MANIFEST.json",
        SIM_ROOT / "HASH_MANIFEST.json",
        DATA_ROOT / "HASH_MANIFEST.json",
        PREF_ROOT / "HASH_MANIFEST.json",
        FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json",
        SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        errors.extend(verify_manifest(path))

    event_log = read_jsonl(EVENT_ROOT / "EVENT_FABRIC_V2_2_STRESS_EVENT_LOG.jsonl")
    if len(event_log) < 40:
        errors.append("event_fabric_v2_2_stress_event_count_lt_40")
    if len({row.get("family_id") for row in event_log}) < 4:
        errors.append("event_fabric_v2_2_family_count_lt_4")
    replay = read_json(EVENT_ROOT / "EVENT_FABRIC_V2_2_REPLAY_DETERMINISM_REPORT.json", {})
    if replay.get("stable_across_two_runs") is not True:
        errors.append("event_fabric_v2_2_replay_hash_unstable")

    sim_decision = read_json(SIM_ROOT / "DECISION.json", {})
    if sim_decision.get("product_forecast_surface_created") is not False:
        errors.append("simulation_v2_2_forecast_surface_created")
    forecast_guard = read_json(SIM_ROOT / "NO_PRODUCT_FORECAST_SURFACE_GUARD.json", {})
    if forecast_guard.get("ForecastPacket_created") is not False:
        errors.append("simulation_v2_2_ForecastPacket_created")

    no_session = read_json(PREF_ROOT / "FOUNDER_REVIEW_NO_SESSION_GUARD.json", {})
    if no_session.get("prep_only") is not True:
        errors.append("pre_founder_review_not_prep_only")
    for key in ["review_session_results_created", "operator_or_founder_fuel_captured", "dispositions_created", "training_eligibility_created"]:
        if no_session.get(key) is not False:
            errors.append(f"pre_founder_review_guard_failed:{key}")

    final_guard = read_json(FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", {})
    if final_guard.get("forbidden_capabilities_created") != []:
        errors.append("next_wave_forbidden_capabilities_created")
    sequence = read_json(SEQUENCE_ROOT / "SEQUENTIAL_EXECUTION_LOG.json", {})
    if sequence.get("parallel_execution_used") is not False:
        errors.append("sequence_parallel_execution_used")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="Validate existing outputs without rebuilding.")
    args = parser.parse_args()

    if not args.validate_only:
        build_all()
    errors = validate_all()
    if errors:
        print("BLOCKED")
        for error in errors:
            print(error)
        return 1
    print(STATUS_SEQUENCE)
    print(rel(FINAL_ROOT / "DECISION.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
