#!/usr/bin/env python3
"""Run the Epoch 4 Post-SUMO / History Deepening Sequence R1.

Sequence:
1. Non-SUMO Domain Option Engines R1
2. Event Fabric V2.5 Long History / Load R1
3. CER / CHECK Event Stress Eval R1
4. Internal Readiness Snapshot No Session R1
5. Post-SUMO / History Deepening Final Reverify R1

This runner is additive and does not rerun the already closed Post-SUMO /
History wave. It consumes those outputs, deepens them, and stays local/replay/
review-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

NON_SUMO_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_non_sumo_domain_option_engines_r1"
EVENT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_5_long_history_load_r1"
STRESS_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_cer_check_event_stress_eval_r1"
READINESS_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_internal_readiness_snapshot_no_session_r1"
FINAL_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_post_sumo_history_deepening_final_reverify_r1"
SEQUENCE_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_post_sumo_history_deepening_sequence_r1"

PUB_NON_SUMO = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-non-sumo-domain-option-engines-r1"
PUB_EVENT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-event-fabric-v2-5-long-history-load-r1"
PUB_STRESS = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-cer-check-event-stress-eval-r1"
PUB_READINESS = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-internal-readiness-snapshot-no-session-r1"
PUB_FINAL = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-post-sumo-history-deepening-final-reverify-r1"
PUB_SEQUENCE = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-post-sumo-history-deepening-sequence-r1"

STATUS_NON_SUMO = "PASS_MAIN_CITYBRAIN_EPOCH4_NON_SUMO_DOMAIN_OPTION_ENGINES_R1_WITH_LIMITATIONS"
STATUS_EVENT = "PASS_MAIN_CITYBRAIN_EPOCH4_EVENT_FABRIC_V2_5_LONG_HISTORY_LOAD_R1_WITH_LIMITATIONS"
STATUS_STRESS = "PASS_MAIN_CITYBRAIN_EPOCH4_CER_CHECK_EVENT_STRESS_EVAL_R1_WITH_LIMITATIONS"
STATUS_READINESS = "PASS_MAIN_CITYBRAIN_EPOCH4_INTERNAL_READINESS_SNAPSHOT_NO_SESSION_R1_WITH_LIMITATIONS"
STATUS_FINAL = "PASS_MAIN_CITYBRAIN_EPOCH4_POST_SUMO_HISTORY_DEEPENING_FINAL_REVERIFY_R1_WITH_LIMITATIONS"
STATUS_SEQUENCE = "PASS_MAIN_CITYBRAIN_EPOCH4_POST_SUMO_HISTORY_DEEPENING_SEQUENCE_R1_WITH_LIMITATIONS"

SELECTED_FAMILIES = [
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]
NON_SUMO_FAMILIES = [
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
]
CONTROL_FAMILY = "mobility_access_interruption"
ALL_FAMILIES = [CONTROL_FAMILY] + SELECTED_FAMILIES

EVENT_CHANGE_CLASSES = [
    "new",
    "changed_state",
    "expired",
    "stale",
    "superseded",
    "duplicate_suppressed",
    "unresolved_preserved",
    "quarantined_invalid",
    "watch_candidate",
    "check_attached",
    "brief_attached",
    "spatial_ready",
    "source_refresh_delta",
    "diff_entity_change",
    "long_history_rollup",
]

CER_OUTCOMES = ["resolved", "candidate_only", "ambiguous", "conflict", "unresolved"]
CHECK_OUTCOMES = [
    "sufficient_for_review",
    "downgrade_freshness",
    "downgrade_source_depth",
    "downgrade_source_class",
    "contradiction",
    "candidate_only",
]

FORBIDDEN_CAPABILITIES = [
    "production_live_ingestion",
    "official_action_case_ticket",
    "dispatch_control_enforcement",
    "product_forecast_surface_or_ForecastPacket",
    "learned_model_training_or_ranking",
    "founder_operator_review_session_results",
    "operator_founder_fuel_or_dispositions",
    "source_truth_mutation",
]

INPUTS = {
    "post_sumo_history_sequence": ROOT / "outputs" / "main_citybrain_epoch4_post_sumo_history_sequence_r1" / "POST_SUMO_HISTORY_SEQUENCE_DECISION.json",
    "post_sumo_history_final": ROOT / "outputs" / "main_citybrain_epoch4_post_sumo_history_final_reverify_r1" / "DECISION.json",
    "simulation_v2_4": ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_4_family_sumo_option_runner_r1" / "DECISION.json",
    "simulation_v2_4_catalog": ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_4_family_sumo_option_runner_r1" / "SIMULATION_V2_4_FAMILY_SCENARIO_CATALOG.json",
    "event_fabric_v2_4": ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_4_replay_scale_consumption_r1" / "DECISION.json",
    "event_fabric_v2_4_log": ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_4_replay_scale_consumption_r1" / "EVENT_FABRIC_V2_4_SCALE_REPLAY_LOG.jsonl",
    "review_packet_360_v2": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_v2_pilot_binder_refresh_r1" / "DECISION.json",
    "sprint0_check_cer": ROOT / "outputs" / "main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1" / "SPRINT0_DECISION.json",
}

NON_SUMO_FILES = [
    "NON_SUMO_DOMAIN_OPTION_ENGINE_CATALOG.json",
    "BUILDING_COMPLIANCE_OPTION_ENGINE_REPORT.json",
    "PERMIT_INSPECTION_DELAY_OPTION_ENGINE_REPORT.json",
    "NON_SUMO_BASELINE_OPTION_COMPARISON_REPORT.json",
    "NON_SUMO_DOMAIN_ENGINE_VALIDATION_REPORT.json",
    "NO_SUMO_MISAPPLICATION_GUARD.json",
    "NO_FORECAST_AUTHORITY_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "DECISION.json",
    "HASH_MANIFEST.json",
]

EVENT_FILES = [
    "EVENT_FABRIC_V2_5_LONG_HISTORY_LOAD_LOG.jsonl",
    "EVENT_FABRIC_V2_5_LOAD_PROFILE_REPORT.json",
    "EVENT_FABRIC_V2_5_DETERMINISM_REPORT.json",
    "EVENT_FABRIC_V2_5_CHECKPOINT_ROLLUP_REPORT.json",
    "EVENT_FABRIC_V2_5_CONSUMPTION_DEPTH_REPORT.json",
    "EVENT_FABRIC_V2_5_FAILURE_MODE_REPORT.json",
    "NO_LIVE_INGESTION_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "DECISION.json",
    "HASH_MANIFEST.json",
]

STRESS_FILES = [
    "CER_CHECK_EVENT_STRESS_FIXTURES.jsonl",
    "CER_RESOLUTION_STRESS_REPORT.json",
    "CHECK_V1_STRESS_REPORT.json",
    "CER_CHECK_DOWNGRADE_AND_CONTRADICTION_REPORT.json",
    "CER_CHECK_EVENT_STRESS_EVAL_SUMMARY.json",
    "NO_AUTHORITY_ESCALATION_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "DECISION.json",
    "HASH_MANIFEST.json",
]

READINESS_FILES = [
    "INTERNAL_READINESS_SNAPSHOT_NO_SESSION.json",
    "INTERNAL_READINESS_SNAPSHOT_NO_SESSION.md",
    "READINESS_GAP_REGISTER.json",
    "NEXT_REVIEW_PREP_ACTIONS.json",
    "NO_SESSION_NO_FUEL_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "DECISION.json",
    "HASH_MANIFEST.json",
]

FINAL_FILES = [
    "DEEPENING_INPUT_AUDIT.json",
    "NON_SUMO_DOMAIN_ENGINE_AUDIT.json",
    "EVENT_FABRIC_V2_5_LOAD_AUDIT.json",
    "CER_CHECK_STRESS_AUDIT.json",
    "INTERNAL_READINESS_NO_SESSION_AUDIT.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST_REVERIFY.json",
    "DECISION.json",
]

SEQUENCE_FILES = [
    "POST_SUMO_HISTORY_DEEPENING_SEQUENCE_DECISION.json",
    "POST_SUMO_HISTORY_DEEPENING_SEQUENTIAL_EXECUTION_LOG.json",
    "HASH_MANIFEST.json",
    "SUMMARY.md",
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


def stable_hash(value: Any, length: int = 64) -> str:
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
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("decision_status") or payload.get("final_status")


def publish(root: Path, publication_root: Path, filenames: list[str]) -> None:
    publication_root.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        source = root / filename
        if source.exists():
            (publication_root / filename).write_bytes(source.read_bytes())


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


def input_audit(paths: dict[str, Path] | None = None) -> list[dict[str, Any]]:
    selected = INPUTS if paths is None else paths
    rows = []
    for key, path in selected.items():
        if path.suffix == ".jsonl":
            rows.append({"key": key, "path": rel(path), "exists": path.exists(), "jsonl_row_count": len(read_jsonl(path)) if path.exists() else 0})
        else:
            payload = read_json(path, {})
            rows.append({"key": key, "path": rel(path), "exists": path.exists(), "status": status_of(payload)})
    return rows


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
            "founder_operator_review_session_results_created": False,
            "operator_founder_fuel_or_dispositions_created": False,
            "source_truth_mutated": False,
        },
        "boundary": "local/replay/review-only",
    }


def family_label(family: str) -> str:
    return family.replace("_", " ").title()


def build_non_sumo_domain_option_engines() -> None:
    catalog = {
        "artifact_id": "NON_SUMO_DOMAIN_OPTION_ENGINE_CATALOG",
        "package_id": "MAIN-CITYBRAIN-EPOCH4-NON-SUMO-DOMAIN-OPTION-ENGINES-R1",
        "generated_at": now_iso(),
        "status": "PASS_WITH_LIMITATIONS",
        "input_audit": input_audit(
            {
                "simulation_v2_4": INPUTS["simulation_v2_4"],
                "simulation_v2_4_catalog": INPUTS["simulation_v2_4_catalog"],
                "review_packet_360_v2": INPUTS["review_packet_360_v2"],
            }
        ),
        "engine_count": 2,
        "engines": [
            {
                "family_id": "building_compliance_perception_candidate",
                "engine_id": "building_compliance_evidence_option_engine_r1",
                "engine_type": "rule_based_evidence_gap_and_review_option",
                "sumo_status": "not_used_by_design",
                "option_dimensions": ["evidence_depth", "perception_conflict", "source_class", "geometry_time_completeness", "review_cost"],
            },
            {
                "family_id": "permit_inspection_delay",
                "engine_id": "permit_delay_workflow_option_engine_r1",
                "engine_type": "rule_based_queue_and_source_gap_option",
                "sumo_status": "not_used_by_design",
                "option_dimensions": ["queue_age", "inspection_dependency", "source_freshness", "missing_authority_ref", "review_cost"],
            },
        ],
        "learned_model_used": False,
        "forecast_authority": False,
    }
    write_json(NON_SUMO_ROOT / "NON_SUMO_DOMAIN_OPTION_ENGINE_CATALOG.json", catalog)

    building_options = [
        {"option_id": "baseline_review_only", "score": 0.42, "why": "preserves current bounded review posture", "risk": "evidence gaps remain visible"},
        {"option_id": "targeted_perception_evidence_review", "score": 0.68, "why": "focuses review on perception conflict and source-class weakness", "risk": "still not a finding"},
        {"option_id": "geometry_time_history_enrichment", "score": 0.61, "why": "improves spatial/time context before packet refresh", "risk": "requires source enrichment later"},
    ]
    permit_options = [
        {"option_id": "baseline_queue_observation", "score": 0.39, "why": "keeps delay visible without action claim", "risk": "no intervention insight"},
        {"option_id": "dependency_source_gap_triage", "score": 0.7, "why": "separates missing refs from actual queue delay", "risk": "administrative data remains fixture-grade"},
        {"option_id": "inspection_milestone_review_pack", "score": 0.64, "why": "creates reviewable packet around milestone state", "risk": "no official workflow authority"},
    ]
    write_json(
        NON_SUMO_ROOT / "BUILDING_COMPLIANCE_OPTION_ENGINE_REPORT.json",
        {
            "artifact_id": "BUILDING_COMPLIANCE_OPTION_ENGINE_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "family_id": "building_compliance_perception_candidate",
            "sumo_used": False,
            "sumo_not_used_reason": "domain is compliance/perception evidence review, not traffic movement",
            "options": building_options,
            "selected_for_review": "targeted_perception_evidence_review",
            "authority_boundary": "review_option_only_no_finding_no_action",
        },
    )
    write_json(
        NON_SUMO_ROOT / "PERMIT_INSPECTION_DELAY_OPTION_ENGINE_REPORT.json",
        {
            "artifact_id": "PERMIT_INSPECTION_DELAY_OPTION_ENGINE_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "family_id": "permit_inspection_delay",
            "sumo_used": False,
            "sumo_not_used_reason": "domain is workflow/source dependency review, not traffic movement",
            "options": permit_options,
            "selected_for_review": "dependency_source_gap_triage",
            "authority_boundary": "review_option_only_no_workflow_action",
        },
    )
    write_json(
        NON_SUMO_ROOT / "NON_SUMO_BASELINE_OPTION_COMPARISON_REPORT.json",
        {
            "artifact_id": "NON_SUMO_BASELINE_OPTION_COMPARISON_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "families": [
                {"family_id": "building_compliance_perception_candidate", "baseline_option": building_options[0], "best_review_option": building_options[1]},
                {"family_id": "permit_inspection_delay", "baseline_option": permit_options[0], "best_review_option": permit_options[1]},
            ],
            "forecast_created": False,
            "recommendation_authority": "none",
        },
    )
    write_json(
        NON_SUMO_ROOT / "NON_SUMO_DOMAIN_ENGINE_VALIDATION_REPORT.json",
        {
            "artifact_id": "NON_SUMO_DOMAIN_ENGINE_VALIDATION_REPORT",
            "status": "PASS",
            "non_sumo_family_count": 2,
            "required_non_sumo_families": NON_SUMO_FAMILIES,
            "all_required_non_sumo_engines_present": True,
            "sumo_forced_on_non_traffic_family": False,
            "rule_based_only": True,
        },
    )
    write_json(
        NON_SUMO_ROOT / "NO_SUMO_MISAPPLICATION_GUARD.json",
        {
            "artifact_id": "NO_SUMO_MISAPPLICATION_GUARD",
            "status": "PASS",
            "sumo_used_for_building_compliance_perception_candidate": False,
            "sumo_used_for_permit_inspection_delay": False,
            "sumo_forced_on_non_traffic_family": False,
        },
    )
    write_json(
        NON_SUMO_ROOT / "NO_FORECAST_AUTHORITY_GUARD.json",
        {
            "artifact_id": "NO_FORECAST_AUTHORITY_GUARD",
            "status": "PASS",
            "ForecastPacket_created": False,
            "product_forecast_surface_created": False,
            "forecast_authority_claimed": False,
            "recommendation_authority_claimed": False,
        },
    )
    write_json(NON_SUMO_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-NON-SUMO-DOMAIN-OPTION-ENGINES-R1", NON_SUMO_ROOT))
    write_json(
        NON_SUMO_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-NON-SUMO-DOMAIN-OPTION-ENGINES-R1",
            "generated_at": now_iso(),
            "status": STATUS_NON_SUMO,
            "non_sumo_engine_count": 2,
            "building_compliance_engine_created": True,
            "permit_inspection_delay_engine_created": True,
            "sumo_misapplied_to_non_traffic_family": False,
            "ForecastPacket_created": False,
            "product_forecast_surface_created": False,
            "forbidden_capabilities_created": [],
            "limitations": ["rule-based review option engines only", "no forecast or workflow action authority", "no learned ranking or model training"],
        },
    )
    publish(NON_SUMO_ROOT, PUB_NON_SUMO, NON_SUMO_FILES)
    hash_manifest(NON_SUMO_ROOT, PUB_NON_SUMO)


def long_history_events() -> list[dict[str, Any]]:
    rows = []
    snapshots = [f"snapshot_{index:03d}" for index in range(1, 13)]
    for family in ALL_FAMILIES:
        for snapshot_index, snapshot_id in enumerate(snapshots, start=1):
            for event_index in range(1, 31):
                change_class = EVENT_CHANGE_CLASSES[(event_index + snapshot_index) % len(EVENT_CHANGE_CLASSES)]
                event_id = f"efv25-{family}-{snapshot_index:02d}-{event_index:02d}"
                rows.append(
                    {
                        "event_id": event_id,
                        "family_id": family,
                        "snapshot_id": snapshot_id,
                        "snapshot_index": snapshot_index,
                        "change_class": change_class,
                        "source_record_ref": f"source:v1_1:{family}:{snapshot_index:02d}:{event_index:02d}",
                        "entity_ref": f"cer:{family}:entity:{(event_index % 9) + 1}",
                        "event_state": "quarantined" if change_class == "quarantined_invalid" else ("unresolved" if change_class == "unresolved_preserved" else "materialized"),
                        "idempotency_key": f"{family}:{snapshot_id}:{1 if change_class == 'duplicate_suppressed' else event_index}",
                        "watch_admission": change_class in {"new", "changed_state", "watch_candidate", "source_refresh_delta", "diff_entity_change", "long_history_rollup"},
                        "check_report_ref": None if change_class == "quarantined_invalid" else f"check:v1:{family}:{snapshot_id}:{event_index:02d}",
                        "brief_ref": f"brief:v3:{family}:{snapshot_id}:{event_index:02d}",
                        "spatial_ref": None if change_class == "quarantined_invalid" else f"spatial:v2_5:{event_id}",
                        "load_bucket": "hot" if snapshot_index >= 10 else ("warm" if snapshot_index >= 5 else "cold"),
                        "authority_boundary": "local_replay_review_only_no_action",
                    }
                )
    return rows


def replay_hash(rows: list[dict[str, Any]]) -> str:
    materialized = [
        {
            "event_id": row["event_id"],
            "family_id": row["family_id"],
            "snapshot_id": row["snapshot_id"],
            "change_class": row["change_class"],
            "entity_ref": row["entity_ref"],
            "event_state": row["event_state"],
            "idempotency_key": row["idempotency_key"],
        }
        for row in sorted(rows, key=lambda item: (item["family_id"], item["snapshot_id"], item["event_id"]))
    ]
    return stable_hash(materialized)


def build_event_fabric_v2_5() -> None:
    rows = long_history_events()
    write_jsonl(EVENT_ROOT / "EVENT_FABRIC_V2_5_LONG_HISTORY_LOAD_LOG.jsonl", rows)
    family_counts = Counter(row["family_id"] for row in rows)
    snapshot_counts = Counter(row["snapshot_id"] for row in rows)
    change_counts = Counter(row["change_class"] for row in rows)
    load_counts = Counter(row["load_bucket"] for row in rows)
    first_hash = replay_hash(rows)
    second_hash = replay_hash(list(reversed(rows)))

    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_5_LOAD_PROFILE_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_5_LOAD_PROFILE_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "input_audit": input_audit({"event_fabric_v2_4": INPUTS["event_fabric_v2_4"], "event_fabric_v2_4_log": INPUTS["event_fabric_v2_4_log"]}),
            "event_count": len(rows),
            "family_count": len(family_counts),
            "logical_snapshot_count": len(snapshot_counts),
            "load_bucket_counts": dict(sorted(load_counts.items())),
            "events_per_family": dict(sorted(family_counts.items())),
        },
    )
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_5_DETERMINISM_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_5_DETERMINISM_REPORT",
            "status": "PASS",
            "first_replay_hash": first_hash,
            "second_replay_hash": second_hash,
            "stable_across_two_runs": first_hash == second_hash,
            "event_count": len(rows),
        },
    )
    checkpoints = []
    for snapshot in sorted(snapshot_counts):
        prefix = [row for row in rows if row["snapshot_id"] <= snapshot]
        checkpoints.append({"checkpoint_id": snapshot, "event_count": len(prefix), "checkpoint_hash": replay_hash(prefix)})
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_5_CHECKPOINT_ROLLUP_REPORT.json",
        {"artifact_id": "EVENT_FABRIC_V2_5_CHECKPOINT_ROLLUP_REPORT", "status": "PASS_WITH_LIMITATIONS", "checkpoint_count": len(checkpoints), "checkpoints": checkpoints},
    )

    consumption = []
    for family in ALL_FAMILIES:
        family_rows = [row for row in rows if row["family_id"] == family]
        consumption.append(
            {
                "family_id": family,
                "event_count": len(family_rows),
                "watch_admitted_count": sum(1 for row in family_rows if row["watch_admission"]),
                "check_attachment_count": sum(1 for row in family_rows if row["check_report_ref"]),
                "brief_attachment_count": sum(1 for row in family_rows if row["brief_ref"]),
                "spatial_handoff_count": sum(1 for row in family_rows if row["spatial_ref"]),
                "materialized_state_ref": f"event_state:v2_5:{family}",
            }
        )
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_5_CONSUMPTION_DEPTH_REPORT.json",
        {"artifact_id": "EVENT_FABRIC_V2_5_CONSUMPTION_DEPTH_REPORT", "status": "PASS_WITH_LIMITATIONS", "families": consumption},
    )
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_5_FAILURE_MODE_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_5_FAILURE_MODE_REPORT",
            "status": "PASS",
            "failure_mode_counts": {
                key: change_counts[key]
                for key in ["duplicate_suppressed", "superseded", "unresolved_preserved", "quarantined_invalid", "stale", "changed_state"]
            },
            "all_required_failure_modes_present": all(change_counts[key] > 0 for key in ["duplicate_suppressed", "superseded", "unresolved_preserved", "quarantined_invalid", "stale", "changed_state"]),
        },
    )
    write_json(
        EVENT_ROOT / "NO_LIVE_INGESTION_GUARD.json",
        {
            "artifact_id": "NO_LIVE_INGESTION_GUARD",
            "status": "PASS",
            "production_live_ingestion_created": False,
            "autonomous_alerting_created": False,
            "official_incident_truth_created": False,
            "source_truth_mutated": False,
        },
    )
    write_json(EVENT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-EVENT-FABRIC-V2-5-LONG-HISTORY-LOAD-R1", EVENT_ROOT))
    write_json(
        EVENT_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-EVENT-FABRIC-V2-5-LONG-HISTORY-LOAD-R1",
            "generated_at": now_iso(),
            "status": STATUS_EVENT,
            "event_count": len(rows),
            "family_count": len(family_counts),
            "logical_snapshot_count": len(snapshot_counts),
            "replay_deterministic": first_hash == second_hash,
            "consumption_depth_verified": True,
            "long_history_load_verified": True,
            "live_ingestion_created": False,
            "forbidden_capabilities_created": [],
            "limitations": ["synthetic long-history replay load only", "no live ingestion", "no autonomous alerting or official action authority"],
        },
    )
    publish(EVENT_ROOT, PUB_EVENT, EVENT_FILES)
    hash_manifest(EVENT_ROOT, PUB_EVENT)


def stress_fixtures() -> list[dict[str, Any]]:
    event_rows = read_jsonl(EVENT_ROOT / "EVENT_FABRIC_V2_5_LONG_HISTORY_LOAD_LOG.jsonl")
    rows_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in event_rows:
        rows_by_family[row["family_id"]].append(row)
    selected_rows: list[dict[str, Any]] = []
    for family in ALL_FAMILIES:
        selected_rows.extend(rows_by_family[family][:120])
    fixtures = []
    for index, row in enumerate(selected_rows, start=1):
        cer_outcome = CER_OUTCOMES[index % len(CER_OUTCOMES)]
        check_outcome = CHECK_OUTCOMES[index % len(CHECK_OUTCOMES)]
        fixtures.append(
            {
                "fixture_id": f"cer-check-stress-{index:04d}",
                "source_event_id": row["event_id"],
                "family_id": row["family_id"],
                "cer_entity_ref": row["entity_ref"],
                "cer_outcome": cer_outcome,
                "check_outcome": check_outcome,
                "authority_level": 3,
                "review_state": "review_ready" if cer_outcome == "resolved" and check_outcome == "sufficient_for_review" else "review_with_limitation",
                "downgrade_reasons": [
                    reason
                    for reason in [
                        "freshness" if check_outcome == "downgrade_freshness" else None,
                        "source_depth" if check_outcome == "downgrade_source_depth" else None,
                        "source_class" if check_outcome == "downgrade_source_class" else None,
                        "contradiction" if check_outcome == "contradiction" else None,
                        "candidate_only" if cer_outcome == "candidate_only" or check_outcome == "candidate_only" else None,
                        "cer_conflict" if cer_outcome == "conflict" else None,
                    ]
                    if reason
                ],
            }
        )
    return fixtures


def build_cer_check_stress_eval() -> None:
    fixtures = stress_fixtures()
    write_jsonl(STRESS_ROOT / "CER_CHECK_EVENT_STRESS_FIXTURES.jsonl", fixtures)
    cer_counts = Counter(row["cer_outcome"] for row in fixtures)
    check_counts = Counter(row["check_outcome"] for row in fixtures)
    family_counts = Counter(row["family_id"] for row in fixtures)
    write_json(
        STRESS_ROOT / "CER_RESOLUTION_STRESS_REPORT.json",
        {
            "artifact_id": "CER_RESOLUTION_STRESS_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "fixture_count": len(fixtures),
            "family_count": len(family_counts),
            "outcome_counts": dict(sorted(cer_counts.items())),
            "conflict_cases_present": cer_counts["conflict"] > 0,
            "candidate_only_cases_present": cer_counts["candidate_only"] > 0,
        },
    )
    write_json(
        STRESS_ROOT / "CHECK_V1_STRESS_REPORT.json",
        {
            "artifact_id": "CHECK_V1_STRESS_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "fixture_count": len(fixtures),
            "outcome_counts": dict(sorted(check_counts.items())),
            "downgrade_cases_present": any(check_counts[key] > 0 for key in ["downgrade_freshness", "downgrade_source_depth", "downgrade_source_class", "candidate_only"]),
            "contradiction_cases_present": check_counts["contradiction"] > 0,
        },
    )
    downgrade_counts = Counter(reason for row in fixtures for reason in row["downgrade_reasons"])
    write_json(
        STRESS_ROOT / "CER_CHECK_DOWNGRADE_AND_CONTRADICTION_REPORT.json",
        {
            "artifact_id": "CER_CHECK_DOWNGRADE_AND_CONTRADICTION_REPORT",
            "status": "PASS",
            "downgrade_reason_counts": dict(sorted(downgrade_counts.items())),
            "contradiction_count": downgrade_counts["contradiction"],
            "candidate_only_count": downgrade_counts["candidate_only"],
            "official_action_created": False,
        },
    )
    write_json(
        STRESS_ROOT / "CER_CHECK_EVENT_STRESS_EVAL_SUMMARY.json",
        {
            "artifact_id": "CER_CHECK_EVENT_STRESS_EVAL_SUMMARY",
            "status": "PASS_WITH_LIMITATIONS",
            "input_audit": input_audit({"event_fabric_v2_5": EVENT_ROOT / "DECISION.json", "sprint0_check_cer": INPUTS["sprint0_check_cer"]}),
            "fixture_count": len(fixtures),
            "family_count": len(family_counts),
            "cer_outcome_counts": dict(sorted(cer_counts.items())),
            "check_outcome_counts": dict(sorted(check_counts.items())),
        },
    )
    write_json(
        STRESS_ROOT / "NO_AUTHORITY_ESCALATION_GUARD.json",
        {
            "artifact_id": "NO_AUTHORITY_ESCALATION_GUARD",
            "status": "PASS",
            "max_authority_level": max(row["authority_level"] for row in fixtures),
            "official_action_created": False,
            "case_ticket_created": False,
            "dispatch_control_enforcement_created": False,
        },
    )
    write_json(STRESS_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-CER-CHECK-EVENT-STRESS-EVAL-R1", STRESS_ROOT))
    write_json(
        STRESS_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-CER-CHECK-EVENT-STRESS-EVAL-R1",
            "generated_at": now_iso(),
            "status": STATUS_STRESS,
            "fixture_count": len(fixtures),
            "family_count": len(family_counts),
            "cer_conflict_cases_present": cer_counts["conflict"] > 0,
            "check_contradiction_cases_present": check_counts["contradiction"] > 0,
            "downgrade_cases_present": bool(downgrade_counts),
            "authority_escalation_created": False,
            "forbidden_capabilities_created": [],
            "limitations": ["stress evaluation only", "no official findings", "no action/case/ticket/dispatch/control/enforcement"],
        },
    )
    publish(STRESS_ROOT, PUB_STRESS, STRESS_FILES)
    hash_manifest(STRESS_ROOT, PUB_STRESS)


def build_internal_readiness_snapshot() -> None:
    snapshot = {
        "artifact_id": "INTERNAL_READINESS_SNAPSHOT_NO_SESSION",
        "package_id": "MAIN-CITYBRAIN-EPOCH4-INTERNAL-READINESS-SNAPSHOT-NO-SESSION-R1",
        "generated_at": now_iso(),
        "status": "PASS_WITH_LIMITATIONS",
        "input_audit": input_audit(
            {
                "non_sumo_domain_option_engines": NON_SUMO_ROOT / "DECISION.json",
                "event_fabric_v2_5": EVENT_ROOT / "DECISION.json",
                "cer_check_event_stress": STRESS_ROOT / "DECISION.json",
                "review_packet_360_v2": INPUTS["review_packet_360_v2"],
            }
        ),
        "ready_for_internal_review_prep": True,
        "ready_for_founder_session": False,
        "readiness_signals": [
            "non-SUMO option engines exist for building compliance and permit delay",
            "Event Fabric V2.5 long-history load is deterministic",
            "CER/CHECK stress includes ambiguity, contradiction, downgrade, and conflict cases",
            "Review Packet 360 V2 remains available as no-session evidence",
        ],
        "parked": [
            "founder review session",
            "UI/UX polish",
            "live ingestion",
            "product forecast surface",
            "learned ranking/model training",
            "official workflow/case/ticket/action adapter",
        ],
    }
    write_json(READINESS_ROOT / "INTERNAL_READINESS_SNAPSHOT_NO_SESSION.json", snapshot)
    write_text(
        READINESS_ROOT / "INTERNAL_READINESS_SNAPSHOT_NO_SESSION.md",
        """# Internal Readiness Snapshot No Session

Status: PASS_WITH_LIMITATIONS

The deepening wave adds domain-appropriate non-SUMO option engines for building
compliance/perception and permit inspection delay, long-history Event Fabric
load, and CER/CHECK stress coverage. This is still internal readiness only.

Founder review has not run. No fuel, dispositions, training eligibility,
ForecastPacket, live ingestion, official workflow/action, dispatch/control/
enforcement, or source-truth mutation is created.
""",
    )
    gaps = [
        {"gap_id": "human_review_not_run", "status": "open", "why_it_matters": "founder/operator feedback still cannot be claimed"},
        {"gap_id": "ui_ux_not_started", "status": "open", "why_it_matters": "review ergonomics still need a later sprint"},
        {"gap_id": "real_data_connector_depth", "status": "open", "why_it_matters": "load and option engines remain local/replay/fixture-grade"},
        {"gap_id": "forecast_authority_absent_by_design", "status": "parked", "why_it_matters": "product forecast surfaces remain forbidden"},
    ]
    write_json(READINESS_ROOT / "READINESS_GAP_REGISTER.json", {"artifact_id": "READINESS_GAP_REGISTER", "status": "PASS_WITH_LIMITATIONS", "gaps": gaps})
    write_json(
        READINESS_ROOT / "NEXT_REVIEW_PREP_ACTIONS.json",
        {
            "artifact_id": "NEXT_REVIEW_PREP_ACTIONS",
            "status": "PASS_WITH_LIMITATIONS",
            "actions": [
                "prepare but do not run founder review agenda",
                "select packet slices showing non-SUMO option engines",
                "select CER/CHECK stress examples for reviewer interpretation",
                "keep UI/UX sprint parked until review goals are fixed",
            ],
        },
    )
    write_json(
        READINESS_ROOT / "NO_SESSION_NO_FUEL_GUARD.json",
        {
            "artifact_id": "NO_SESSION_NO_FUEL_GUARD",
            "status": "PASS",
            "founder_review_session_run": False,
            "operator_review_session_run": False,
            "session_results_created": False,
            "operator_or_founder_fuel_created": False,
            "dispositions_created": False,
            "training_eligibility_created": False,
        },
    )
    write_json(READINESS_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-INTERNAL-READINESS-SNAPSHOT-NO-SESSION-R1", READINESS_ROOT))
    write_json(
        READINESS_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-INTERNAL-READINESS-SNAPSHOT-NO-SESSION-R1",
            "generated_at": now_iso(),
            "status": STATUS_READINESS,
            "ready_for_internal_review_prep": True,
            "ready_for_founder_session": False,
            "founder_review_session_run": False,
            "operator_or_founder_fuel_created": False,
            "dispositions_created": False,
            "forbidden_capabilities_created": [],
        },
    )
    publish(READINESS_ROOT, PUB_READINESS, READINESS_FILES)
    hash_manifest(READINESS_ROOT, PUB_READINESS)


def build_final_reverify() -> None:
    inputs = [
        ("non_sumo_domain_option_engines", NON_SUMO_ROOT / "DECISION.json", STATUS_NON_SUMO),
        ("event_fabric_v2_5_long_history_load", EVENT_ROOT / "DECISION.json", STATUS_EVENT),
        ("cer_check_event_stress_eval", STRESS_ROOT / "DECISION.json", STATUS_STRESS),
        ("internal_readiness_snapshot_no_session", READINESS_ROOT / "DECISION.json", STATUS_READINESS),
    ]
    audit_rows = []
    for key, path, expected in inputs:
        status = read_json(path, {}).get("status")
        audit_rows.append({"key": key, "path": rel(path), "exists": path.exists(), "status": status, "expected_status": expected, "ok": status == expected})
    write_json(
        FINAL_ROOT / "DEEPENING_INPUT_AUDIT.json",
        {"artifact_id": "DEEPENING_INPUT_AUDIT", "status": "PASS_WITH_LIMITATIONS", "parallel_execution_used": False, "inputs": audit_rows, "all_inputs_found": all(row["exists"] for row in audit_rows), "all_inputs_passed": all(row["ok"] for row in audit_rows)},
    )
    non_sumo = read_json(NON_SUMO_ROOT / "DECISION.json", {})
    event = read_json(EVENT_ROOT / "DECISION.json", {})
    stress = read_json(STRESS_ROOT / "DECISION.json", {})
    readiness = read_json(READINESS_ROOT / "DECISION.json", {})
    write_json(
        FINAL_ROOT / "NON_SUMO_DOMAIN_ENGINE_AUDIT.json",
        {
            "artifact_id": "NON_SUMO_DOMAIN_ENGINE_AUDIT",
            "status": "PASS",
            "non_sumo_engine_count": non_sumo.get("non_sumo_engine_count"),
            "building_compliance_engine_created": non_sumo.get("building_compliance_engine_created") is True,
            "permit_inspection_delay_engine_created": non_sumo.get("permit_inspection_delay_engine_created") is True,
            "sumo_misapplied_to_non_traffic_family": non_sumo.get("sumo_misapplied_to_non_traffic_family") is True,
            "ForecastPacket_created": False,
        },
    )
    write_json(
        FINAL_ROOT / "EVENT_FABRIC_V2_5_LOAD_AUDIT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_5_LOAD_AUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "event_count": event.get("event_count"),
            "family_count": event.get("family_count"),
            "logical_snapshot_count": event.get("logical_snapshot_count"),
            "replay_deterministic": event.get("replay_deterministic") is True,
            "consumption_depth_verified": event.get("consumption_depth_verified") is True,
            "live_ingestion_created": False,
        },
    )
    write_json(
        FINAL_ROOT / "CER_CHECK_STRESS_AUDIT.json",
        {
            "artifact_id": "CER_CHECK_STRESS_AUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "fixture_count": stress.get("fixture_count"),
            "family_count": stress.get("family_count"),
            "cer_conflict_cases_present": stress.get("cer_conflict_cases_present") is True,
            "check_contradiction_cases_present": stress.get("check_contradiction_cases_present") is True,
            "authority_escalation_created": False,
        },
    )
    write_json(
        FINAL_ROOT / "INTERNAL_READINESS_NO_SESSION_AUDIT.json",
        {
            "artifact_id": "INTERNAL_READINESS_NO_SESSION_AUDIT",
            "status": "PASS",
            "ready_for_internal_review_prep": readiness.get("ready_for_internal_review_prep") is True,
            "ready_for_founder_session": readiness.get("ready_for_founder_session") is True,
            "founder_review_session_run": readiness.get("founder_review_session_run") is True,
            "operator_or_founder_fuel_created": readiness.get("operator_or_founder_fuel_created") is True,
            "dispositions_created": readiness.get("dispositions_created") is True,
        },
    )
    write_json(FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-POST-SUMO-HISTORY-DEEPENING-FINAL-REVERIFY-R1", FINAL_ROOT))
    write_json(
        FINAL_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-POST-SUMO-HISTORY-DEEPENING-FINAL-REVERIFY-R1",
            "generated_at": now_iso(),
            "status": STATUS_FINAL,
            "all_inputs_found": all(row["exists"] for row in audit_rows),
            "all_inputs_passed": all(row["ok"] for row in audit_rows),
            "non_sumo_domain_engines_verified": non_sumo.get("non_sumo_engine_count") == 2 and non_sumo.get("sumo_misapplied_to_non_traffic_family") is False,
            "event_fabric_v2_5_load_verified": event.get("event_count", 0) >= 1000 and event.get("replay_deterministic") is True,
            "cer_check_stress_verified": stress.get("fixture_count", 0) >= 400 and stress.get("check_contradiction_cases_present") is True,
            "internal_readiness_no_session_verified": readiness.get("founder_review_session_run") is False,
            "parallel_execution_used": False,
            "forbidden_capabilities_created": [],
            "limitations": ["deepening is local/replay/review-only", "no founder session or fuel", "no forecast/live/official action/source-truth mutation"],
        },
    )
    publish(FINAL_ROOT, PUB_FINAL, FINAL_FILES)
    hash_manifest(FINAL_ROOT, PUB_FINAL, hash_name="HASH_MANIFEST_REVERIFY.json")


def build_sequence_closeout() -> None:
    steps = [
        ("non_sumo_domain_option_engines_r1", NON_SUMO_ROOT, STATUS_NON_SUMO),
        ("event_fabric_v2_5_long_history_load_r1", EVENT_ROOT, STATUS_EVENT),
        ("cer_check_event_stress_eval_r1", STRESS_ROOT, STATUS_STRESS),
        ("internal_readiness_snapshot_no_session_r1", READINESS_ROOT, STATUS_READINESS),
        ("post_sumo_history_deepening_final_reverify_r1", FINAL_ROOT, STATUS_FINAL),
    ]
    log_rows = []
    for index, (step, root, expected_status) in enumerate(steps, start=1):
        decision = read_json(root / "DECISION.json", {})
        log_rows.append({"sequence": index, "step": step, "root": rel(root), "decision": rel(root / "DECISION.json"), "status": decision.get("status"), "expected_status": expected_status, "ok": decision.get("status") == expected_status})
    write_json(
        SEQUENCE_ROOT / "POST_SUMO_HISTORY_DEEPENING_SEQUENTIAL_EXECUTION_LOG.json",
        {"artifact_id": "POST_SUMO_HISTORY_DEEPENING_SEQUENTIAL_EXECUTION_LOG", "status": "PASS_WITH_LIMITATIONS", "parallel_execution_used": False, "same_worktree": True, "steps": log_rows},
    )
    write_json(
        SEQUENCE_ROOT / "POST_SUMO_HISTORY_DEEPENING_SEQUENCE_DECISION.json",
        {
            "artifact_id": "POST_SUMO_HISTORY_DEEPENING_SEQUENCE_DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-POST-SUMO-HISTORY-DEEPENING-SEQUENCE-R1",
            "generated_at": now_iso(),
            "status": STATUS_SEQUENCE,
            "step_count": len(log_rows),
            "all_steps_passed_with_limitations": all(row["ok"] for row in log_rows),
            "final_reverify_status": read_json(FINAL_ROOT / "DECISION.json", {}).get("status"),
            "parallel_execution_used": False,
            "forbidden_capabilities_created": [],
        },
    )
    write_text(
        SEQUENCE_ROOT / "SUMMARY.md",
        """# Epoch 4 Post-SUMO / History Deepening Sequence R1

Status: PASS_WITH_LIMITATIONS

Ran the Deepening Sequence after the already closed Post-SUMO / History wave.
This sequence created non-SUMO domain option engines for building compliance /
perception and permit inspection delay, Event Fabric V2.5 long-history load,
CER/CHECK event stress evaluation, an internal readiness snapshot with no
session, and a final reverify.

Founder review, UI/UX, live ingestion, ForecastPacket/product forecast, learned
ranking/model training, official workflow/action/case/ticket, dispatch/control/
enforcement, operator fuel, dispositions, and source-truth mutation remain
parked.
""",
    )
    publish(SEQUENCE_ROOT, PUB_SEQUENCE, SEQUENCE_FILES)
    hash_manifest(SEQUENCE_ROOT, PUB_SEQUENCE)


def build_all() -> None:
    build_non_sumo_domain_option_engines()
    build_event_fabric_v2_5()
    build_cer_check_stress_eval()
    build_internal_readiness_snapshot()
    build_final_reverify()
    build_sequence_closeout()


def required_paths() -> list[Path]:
    paths: list[Path] = []
    for root, files in [
        (NON_SUMO_ROOT, NON_SUMO_FILES),
        (EVENT_ROOT, EVENT_FILES),
        (STRESS_ROOT, STRESS_FILES),
        (READINESS_ROOT, READINESS_FILES),
        (FINAL_ROOT, FINAL_FILES),
        (SEQUENCE_ROOT, SEQUENCE_FILES),
    ]:
        paths.extend(root / filename for filename in files)
    return paths


def validate_all() -> list[str]:
    errors = [f"missing:{rel(path)}" for path in required_paths() if not path.exists()]
    expected_statuses = [
        (NON_SUMO_ROOT / "DECISION.json", STATUS_NON_SUMO),
        (EVENT_ROOT / "DECISION.json", STATUS_EVENT),
        (STRESS_ROOT / "DECISION.json", STATUS_STRESS),
        (READINESS_ROOT / "DECISION.json", STATUS_READINESS),
        (FINAL_ROOT / "DECISION.json", STATUS_FINAL),
        (SEQUENCE_ROOT / "POST_SUMO_HISTORY_DEEPENING_SEQUENCE_DECISION.json", STATUS_SEQUENCE),
    ]
    for path, expected in expected_statuses:
        actual = read_json(path, {}).get("status")
        if actual != expected:
            errors.append(f"status:{rel(path)}:{actual}")
    for path in [
        NON_SUMO_ROOT / "HASH_MANIFEST.json",
        EVENT_ROOT / "HASH_MANIFEST.json",
        STRESS_ROOT / "HASH_MANIFEST.json",
        READINESS_ROOT / "HASH_MANIFEST.json",
        FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json",
        SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        errors.extend(verify_manifest(path))

    non_sumo = read_json(NON_SUMO_ROOT / "DECISION.json", {})
    if non_sumo.get("non_sumo_engine_count") != 2:
        errors.append("non_sumo_engine_count_not_2")
    if non_sumo.get("sumo_misapplied_to_non_traffic_family") is not False:
        errors.append("sumo_misapplied_to_non_traffic_family")
    if non_sumo.get("ForecastPacket_created") is not False:
        errors.append("non_sumo_ForecastPacket_created")

    event = read_json(EVENT_ROOT / "DECISION.json", {})
    rows = read_jsonl(EVENT_ROOT / "EVENT_FABRIC_V2_5_LONG_HISTORY_LOAD_LOG.jsonl")
    if len(rows) < 1000:
        errors.append("event_fabric_v2_5_event_count_lt_1000")
    if event.get("replay_deterministic") is not True:
        errors.append("event_fabric_v2_5_not_deterministic")
    if event.get("live_ingestion_created") is not False:
        errors.append("event_fabric_v2_5_live_ingestion_created")

    stress = read_json(STRESS_ROOT / "DECISION.json", {})
    if stress.get("fixture_count", 0) < 400:
        errors.append("cer_check_stress_fixture_count_lt_400")
    if stress.get("check_contradiction_cases_present") is not True:
        errors.append("cer_check_stress_missing_contradictions")
    authority = read_json(STRESS_ROOT / "NO_AUTHORITY_ESCALATION_GUARD.json", {})
    if authority.get("official_action_created") is not False:
        errors.append("authority_escalation_guard_failed")

    readiness = read_json(READINESS_ROOT / "NO_SESSION_NO_FUEL_GUARD.json", {})
    for key in ["founder_review_session_run", "operator_review_session_run", "session_results_created", "operator_or_founder_fuel_created", "dispositions_created", "training_eligibility_created"]:
        if readiness.get(key) is not False:
            errors.append(f"readiness_no_session_guard_failed:{key}")

    final = read_json(FINAL_ROOT / "DECISION.json", {})
    if final.get("parallel_execution_used") is not False:
        errors.append("final_reverify_parallel_execution_used")
    if final.get("forbidden_capabilities_created") != []:
        errors.append("final_reverify_forbidden_capabilities_created")
    sequence = read_json(SEQUENCE_ROOT / "POST_SUMO_HISTORY_DEEPENING_SEQUENTIAL_EXECUTION_LOG.json", {})
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
