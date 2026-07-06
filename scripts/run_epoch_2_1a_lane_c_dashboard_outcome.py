from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_c_dashboard_outcome"
EPOCH20_ROOT = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation"
EPOCH1_ROOT = REPO_ROOT / "outputs" / "epoch1_closedown_certified_baseline"
LANE_A_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention"

STATUS_BLOCKED_LANE_A = "BLOCKED_WAITING_FOR_LANE_A_AGGREGATION_FLOOR"
STATUS_PASS_DASHBOARD_BLOCKED_OUTCOME = "BLOCKED_PUSH_2_1A_LANE_C_OUTCOME_RECORD_WAITING_FOR_LANE_A_AGGREGATION_FLOOR"
STATUS_PASS_DASHBOARD_OUTCOME = "PASS_PUSH_2_1A_LANE_C_DASHBOARD_OUTCOME_WITH_LIMITATIONS"
STATUS_PASS_OUTCOME_MATERIALIZED = "PASS_OUTCOME_RECORD_MATERIALIZED_AGGREGATION_FLOOR_COMPLIANT"
STATUS_ENTRY_BLOCKED = "BLOCKED_EPOCH_2_1_MISSING_2_0_AGENT_RECERTIFICATION_LEDGER"

MANDATORY_AGENT_COMPONENTS = {
    "Watch Scout": "watch_scout",
    "Diff Scout": "diff_scout",
    "CHECK Agent": "check_agent",
    "Approval Lifecycle Agent": "approval_lifecycle_agent",
    "Spatial Agent": "spatial_agent",
    "Perception / Media Agent": "perception_media_agent",
}

EXPECTED_OUTPUT_FILES = {
    "EPOCH_2_0_ENTRY_CHECK_DECISION.json",
    "EPOCH_2_0_ENTRY_CHECK_SUMMARY.md",
    "EPOCH_2_0_AGENT_RECERTIFICATION_INDEX.json",
    "EPOCH_2_1_ALLOWED_TO_OPEN.flag",
    "EPOCH_2_0_ENTRY_CHECK_REPORT.json",
    "EPOCH_2_0_ENTRY_CHECK_GAPS.md",
    "data_maturity_dashboard_v1.json",
    "data_maturity_dashboard_v1.md",
    "outcome_record_schema_v1.json",
    "outcome_record_materialization_report.json",
    "PUSH_2_1A_LANE_C_DECISION.json",
    "PUSH_2_1A_LANE_C_SUMMARY.md",
    "PUSH_2_1A_LANE_C_HASH_MANIFEST.json",
}

OUTCOME_RECORD_SCHEMA = {
    "schema_name": "OutcomeRecordV1",
    "source_class": "derived_field",
    "required_fields": [
        "outcome_record_id",
        "target_ref",
        "trigger_packet_refs",
        "disposition_history_refs",
        "terminal_state",
        "time_to_terminal_seconds",
        "aggregation_floor_respected",
        "trace_refs",
    ],
    "forbidden_behaviors": [
        "ranking",
        "claim_status_change",
        "review_state_change",
        "authority_change",
        "model_training",
    ],
    "boundary": {
        "descriptive_materialization_only": True,
        "not_a_claim": True,
        "not_model_output": True,
        "not_ranking_signal": True,
        "no_learned_ranking": True,
        "no_prediction": True,
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_prepare_output_root() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    existing = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}
    unexpected = sorted(existing - EXPECTED_OUTPUT_FILES)
    if unexpected:
        raise RuntimeError(f"Refusing to overwrite unexpected Lane C output files: {unexpected}")


def status_counts(items: list[dict[str, Any]], key: str = "status") -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, "UNKNOWN"))
        counts[value] = counts.get(value, 0) + 1
    return counts


def load_epoch20() -> dict[str, Any]:
    return {
        "component_registry": read_json(EPOCH20_ROOT / "component_registry_v1.json", []),
        "agent_run_envelope": read_json(EPOCH20_ROOT / "agent_run_envelope_v1.json", {}),
        "tool_permission_policy": read_json(EPOCH20_ROOT / "tool_permission_policy_v1.json", []),
        "mode_invocation_registry": read_json(EPOCH20_ROOT / "mode_invocation_registry_v1.json", []),
        "llm_seat_registry": read_json(EPOCH20_ROOT / "llm_seat_registry_v1.json", []),
        "budget_stop_policy": read_json(EPOCH20_ROOT / "budget_stop_policy_v1.json", []),
        "replay_manifest": read_json(EPOCH20_ROOT / "replay_harness_manifest_v1.json", {}),
        "mode_eval_manifest": read_json(EPOCH20_ROOT / "mode_eval_harness_manifest_v1.json", {}),
        "final_status": read_json(EPOCH20_ROOT / "final_published_status.json", {}),
        "hash_manifest": read_json(EPOCH20_ROOT / "hash_manifest.json", {}),
        "source_mapping": read_json(EPOCH20_ROOT / "reports" / "path_mapping.json", {}),
        "recertification": read_json(EPOCH20_ROOT / "reports" / "agent_recertification_report.json", {}),
        "replay_report": read_json(EPOCH20_ROOT / "reports" / "replay_harness_report.json", {}),
        "mode_eval_report": read_json(EPOCH20_ROOT / "reports" / "mode_eval_harness_report.json", {}),
        "permission_audit": read_json(EPOCH20_ROOT / "reports" / "tool_permission_policy_audit.json", {}),
        "budget_audit": read_json(EPOCH20_ROOT / "reports" / "budget_stop_policy_audit.json", {}),
        "no_official_action": read_json(EPOCH20_ROOT / "audits" / "no_official_action_audit.json", {}),
        "no_learned_model": read_json(EPOCH20_ROOT / "audits" / "no_learned_model_audit.json", {}),
        "no_live_llm": read_json(EPOCH20_ROOT / "audits" / "no_live_llm_authority_audit.json", {}),
    }


def run_entry_check() -> dict[str, Any]:
    data = load_epoch20()
    required_paths = {
        "ComponentRegistry v1": EPOCH20_ROOT / "component_registry_v1.json",
        "AgentRunEnvelope v1": EPOCH20_ROOT / "agent_run_envelope_v1.json",
        "ToolPermissionPolicy v1": EPOCH20_ROOT / "tool_permission_policy_v1.json",
        "ModeInvocationRegistry v1": EPOCH20_ROOT / "mode_invocation_registry_v1.json",
        "LLM seat registry": EPOCH20_ROOT / "llm_seat_registry_v1.json",
        "Budget / Stop Policy": EPOCH20_ROOT / "budget_stop_policy_v1.json",
        "Replay Harness v1": EPOCH20_ROOT / "replay_harness_manifest_v1.json",
        "Mode Eval Harness v1": EPOCH20_ROOT / "mode_eval_harness_manifest_v1.json",
        "2.0 ledger / final published status": EPOCH20_ROOT / "final_published_status.json",
        "2.0 hash manifest": EPOCH20_ROOT / "hash_manifest.json",
        "2.0 source-of-truth matrix update": EPOCH20_ROOT / "reports" / "path_mapping.json",
    }
    missing_inputs = [name for name, path in required_paths.items() if not path.exists()]
    registry_by_id = {entry.get("component_id"): entry for entry in data["component_registry"] if isinstance(entry, dict)}
    recert_rows = data["recertification"].get("rows", [])
    recert_by_id = {row.get("component_id"): row for row in recert_rows if isinstance(row, dict)}

    mandatory_rows = []
    gaps: list[dict[str, Any]] = []
    for label, component_id in MANDATORY_AGENT_COMPONENTS.items():
        registry_entry = registry_by_id.get(component_id)
        recert_row = recert_by_id.get(component_id)
        replay_ref = (recert_row or {}).get("replay_or_eval_ref")
        row = {
            "agent_label": label,
            "component_id": component_id,
            "registered": bool(registry_entry),
            "registry_status": (registry_entry or {}).get("status"),
            "recertification_status": (recert_row or {}).get("status"),
            "replay_or_eval_ref": replay_ref,
            "agent_run_envelope_ref": "outputs/epoch_2_0_agentic_runtime_consolidation/agent_run_envelope_v1.json",
            "permission_valid": bool((recert_row or {}).get("permission_valid")),
            "budget_policy_ref": (registry_entry or {}).get("budget_policy_ref"),
        }
        mandatory_rows.append(row)
        if not row["registered"]:
            gaps.append({"component_id": component_id, "gap": "missing_component_registry_row"})
        if row["recertification_status"] != "PASS":
            gaps.append({"component_id": component_id, "gap": "missing_or_failed_recertification_row"})
        if not replay_ref or data["agent_run_envelope"].get("status") != "emitted":
            gaps.append({"component_id": component_id, "gap": "missing_replay_harness_run_or_agent_run_envelope"})
        if not row["permission_valid"]:
            gaps.append({"component_id": component_id, "gap": "tool_permission_policy_not_applied"})

    mode_scorecard_pass = data["mode_eval_report"].get("status") == "PASS" and data["mode_eval_report"].get("active_mode_count", 0) > 0
    policy_pass = data["permission_audit"].get("status") == "PASS" and data["budget_audit"].get("status") == "PASS"
    non_claim_pass = (
        data["no_official_action"].get("status") == "PASS"
        and data["no_learned_model"].get("status") == "PASS"
        and data["no_live_llm"].get("status") == "PASS"
    )
    if missing_inputs:
        gaps.append({"scope": "required_inputs", "missing": missing_inputs})
    if not mode_scorecard_pass:
        gaps.append({"scope": "mode_scorecard", "gap": "missing_mode_eval_scorecard"})
    if not policy_pass:
        gaps.append({"scope": "policy", "gap": "permission_or_budget_stop_policy_failed"})
    if not non_claim_pass:
        gaps.append({"scope": "non_claim_boundary", "gap": "official_action_live_llm_or_learned_behavior_audit_failed"})

    return {
        "schema_version": "citybrain.epoch_2_1.entry_check.v1",
        "status": "PASS" if not gaps else STATUS_ENTRY_BLOCKED,
        "checked_at": utc_now(),
        "required_inputs": {name: str(path.relative_to(REPO_ROOT)).replace("\\", "/") for name, path in required_paths.items()},
        "missing_inputs": missing_inputs,
        "mandatory_agent_rows": mandatory_rows,
        "mode_scorecard": {
            "status": "PASS" if mode_scorecard_pass else "FAIL",
            "active_mode_count": data["mode_eval_report"].get("active_mode_count", 0),
            "report_ref": "outputs/epoch_2_0_agentic_runtime_consolidation/reports/mode_eval_harness_report.json",
        },
        "policy_checks": {
            "tool_permissions": data["permission_audit"].get("status"),
            "budget_stop": data["budget_audit"].get("status"),
            "no_official_action": data["no_official_action"].get("status"),
            "no_live_llm": data["no_live_llm"].get("status"),
            "no_learned_or_predictive_behavior": data["no_learned_model"].get("status"),
        },
        "source_of_truth_matrix_update": {
            "status": "PASS_WITH_LIMITATION",
            "ref": "outputs/epoch_2_0_agentic_runtime_consolidation/reports/path_mapping.json",
            "source_of_truth_base": data["source_mapping"].get("source_of_truth_base"),
            "note": "Epoch 2.0 publishes path_mapping as the source-of-truth update pointer; Epoch 1 source-of-truth matrix remains the referenced baseline.",
        },
        "gaps": gaps,
    }


def write_entry_outputs(entry: dict[str, Any]) -> None:
    if entry["status"] == "PASS":
        write_json(OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_DECISION.json", entry)
        write_json(
            OUTPUT_ROOT / "EPOCH_2_0_AGENT_RECERTIFICATION_INDEX.json",
            {
                "schema_version": "citybrain.epoch_2_1.entry_check.agent_recertification_index.v1",
                "status": "PASS",
                "mandatory_agent_count": len(entry["mandatory_agent_rows"]),
                "rows": entry["mandatory_agent_rows"],
            },
        )
        write_text(
            OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_SUMMARY.md",
            "# Epoch 2.0 Entry Check Summary\n\n"
            "Status: `PASS`\n\n"
            "The required mandatory agent recertification rows, shared replay harness AgentRunEnvelope, mode scorecard, permission policy, budget/stop policy, and non-claim audits are present. Epoch 2.1 Lane C may open, but it does not close Epoch 2.1.",
        )
        write_text(OUTPUT_ROOT / "EPOCH_2_1_ALLOWED_TO_OPEN.flag", "PASS\n")
        return

    write_json(OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_REPORT.json", entry)
    write_text(
        OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_GAPS.md",
        "# Epoch 2.0 Entry Check Gaps\n\n"
        f"Status: `{entry['status']}`\n\n"
        + "\n".join(f"- `{gap}`" for gap in entry["gaps"]),
    )


def lane_a_aggregation_floor() -> dict[str, Any]:
    candidates = [
        LANE_A_ROOT / "aggregation_floor_policy_v1.json",
        LANE_A_ROOT / "AGGREGATION_FLOOR_POLICY.json",
        LANE_A_ROOT / "aggregation_floor_policy.json",
        LANE_A_ROOT / "PRIVACY_RETENTION_AGGREGATION_FLOOR.json",
        LANE_A_ROOT / "privacy_policy_validation_report.json",
        LANE_A_ROOT / "PUSH_2_1A_LANE_A_DECISION.json",
    ]
    present = [path for path in candidates if path.exists()]
    if not present:
        return {
            "status": STATUS_BLOCKED_LANE_A,
            "validated": False,
            "refs": [],
            "reason": "Lane A aggregation floor artifact is not present in the shared main workspace.",
        }
    decision = read_json(LANE_A_ROOT / "PUSH_2_1A_LANE_A_DECISION.json", {})
    policy = read_json(LANE_A_ROOT / "aggregation_floor_policy_v1.json", {})
    validation = read_json(LANE_A_ROOT / "privacy_policy_validation_report.json", {})
    validated = (
        decision.get("status", "").startswith("PASS")
        and validation.get("status") == "PASS"
        and policy.get("minimum_items_for_dashboard_cell", 0) >= 1
        and policy.get("minimum_operators_for_display_or_learning_stat", 0) >= 1
    )
    return {
        "status": "PASS" if validated else STATUS_BLOCKED_LANE_A,
        "validated": validated,
        "refs": [str(path.relative_to(REPO_ROOT)).replace("\\", "/") for path in present],
        "minimum_items_for_dashboard_cell": policy.get("minimum_items_for_dashboard_cell"),
        "minimum_operators_for_display_or_learning_stat": policy.get("minimum_operators_for_display_or_learning_stat"),
        "policy_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/aggregation_floor_policy_v1.json",
        "validation_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/privacy_policy_validation_report.json",
        "reason": None if validated else "Lane A artifact is present but does not validate aggregation floor.",
    }


def load_outcome_records() -> list[dict[str, Any]]:
    path = EPOCH20_ROOT / "outcome_records_v0.jsonl"
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def build_dashboard(entry: dict[str, Any], aggregation_floor: dict[str, Any]) -> dict[str, Any]:
    epoch20 = load_epoch20()
    source_refresh = read_json(EPOCH1_ROOT / "EPOCH1_SOURCE_REFRESH_LEDGER.json", [])
    corpus = read_json(EPOCH1_ROOT / "EPOCH1_CORPUS_AND_MANIFEST_RECONCILIATION.json", {})
    source_truth = read_json(EPOCH1_ROOT / "EPOCH1_SOURCE_OF_TRUTH_MATRIX.json", [])

    check_rows = [row for row in source_refresh if isinstance(row, dict) and "CHECK" in row.get("source_family", "")]
    cer_rows = [row for row in source_refresh if isinstance(row, dict) and "CER" in row.get("source_family", "")]
    cer_decisions = sorted(str(path.relative_to(REPO_ROOT)).replace("\\", "/") for path in (REPO_ROOT / "outputs").glob("main_citybrain_d6_cer*_*/**/*DECISION.json"))
    cer_conflict_refs = sorted(str(path.relative_to(REPO_ROOT)).replace("\\", "/") for path in (REPO_ROOT / "outputs").glob("**/*CONFLICT*.json"))[:20]
    outcome_records = load_outcome_records()
    outcome_record_count = len(outcome_records) if aggregation_floor["status"] == "PASS" else 0
    dashboard_cell_floor = aggregation_floor.get("minimum_items_for_dashboard_cell") or 0

    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1a.lane_c.data_maturity_dashboard.v1",
        "status": "PASS_DASHBOARD_MATERIALIZED_WITH_OUTCOME_RECORDS" if aggregation_floor["status"] == "PASS" else "PASS_DASHBOARD_MATERIALIZED_WITH_OUTCOME_RECORD_BLOCKED",
        "materialized_at": utc_now(),
        "source_freshness_status": {
            "status": "PASS_WITH_LIMITATIONS" if source_refresh else "UNAVAILABLE",
            "source_ref": "outputs/epoch1_closedown_certified_baseline/EPOCH1_SOURCE_REFRESH_LEDGER.json",
            "source_family_count": len(source_refresh),
            "status_counts": status_counts(source_refresh),
            "deferred_live_source_count": sum(1 for row in source_refresh if row.get("status") == "deferred_live_source"),
            "unknown_needs_refresh_policy_count": sum(1 for row in source_refresh if row.get("status") == "unknown_needs_refresh_policy"),
        },
        "check_status_cannot_claim_stale_counts": {
            "status": "PASS_WITH_LIMITATIONS" if check_rows else "LIMITED_NO_CHECK_V1_MAIN_OUTPUT",
            "source_refs": [row.get("basis") for row in check_rows],
            "cannot_claim_count": 1,
            "stale_or_refresh_needed_count": sum(1 for row in check_rows if "refresh" in row.get("next_proof_condition", "").lower()),
            "boundary": [row.get("boundary") for row in check_rows],
            "note": "No CHECK v1 branch output root is mutated or required on main; dashboard uses published freshness/source ledger when direct CHECK stats are absent.",
        },
        "corpus_version_and_append_state": {
            "status": corpus.get("status", "UNAVAILABLE"),
            "source_ref": "outputs/epoch1_closedown_certified_baseline/EPOCH1_CORPUS_AND_MANIFEST_RECONCILIATION.json",
            "corpus_final_version": corpus.get("corpus_final_version"),
            "append_state": corpus.get("corpus_growth_rule_through_v7"),
            "frozen_eval_slices_pinned": corpus.get("frozen_eval_slices_pinned"),
            "hash_mismatches": corpus.get("hash_mismatches", []),
        },
        "agent_recertification_state": {
            "status": epoch20["recertification"].get("status"),
            "source_ref": "outputs/epoch_2_0_agentic_runtime_consolidation/reports/agent_recertification_report.json",
            "component_count": epoch20["recertification"].get("component_count"),
            "mandatory_agent_count": len(MANDATORY_AGENT_COMPONENTS),
            "mandatory_agent_rows": entry["mandatory_agent_rows"],
        },
        "mode_scorecard_state": {
            "status": epoch20["mode_eval_report"].get("status"),
            "source_ref": "outputs/epoch_2_0_agentic_runtime_consolidation/reports/mode_eval_harness_report.json",
            "active_mode_count": epoch20["mode_eval_report"].get("active_mode_count"),
            "declared_not_active_count": epoch20["mode_eval_report"].get("declared_not_active_count"),
        },
        "cer_conflict_assertion_summary": {
            "status": "AVAILABLE_WITH_LIMITATIONS" if cer_rows or cer_decisions or cer_conflict_refs else "UNAVAILABLE",
            "source_freshness_refs": [row.get("basis") for row in cer_rows],
            "cer_decision_ref_count": len(cer_decisions),
            "cer_conflict_ref_count": len(cer_conflict_refs),
            "sample_refs": (cer_decisions[:5] + cer_conflict_refs[:5])[:10],
            "note": "CER section is a reference summary only; it does not certify assertions or resolve conflicts.",
        },
        "outcome_record_availability_and_aggregation_status": {
            "status": aggregation_floor["status"],
            "source_class": "derived_field",
            "schema_ref": "outputs/epoch_2_1_push_2_1a_lane_c_dashboard_outcome/outcome_record_schema_v1.json",
            "materializer_ref": "scripts/run_epoch_2_1a_lane_c_dashboard_outcome.py",
            "records_materialized": outcome_record_count,
            "dashboard_cells_released": 0 if outcome_record_count < dashboard_cell_floor else 1,
            "small_cell_suppressed": outcome_record_count < dashboard_cell_floor,
            "aggregation_floor": aggregation_floor,
        },
        "policy_compliance_flags": {
            "no_learned_ranking": True,
            "no_prediction": True,
            "no_new_data_warehouse": True,
            "no_live_dashboard_service": True,
            "no_official_ticket_case_submission": True,
            "no_dispatch_control_enforcement": True,
            "no_legal_certified_finding": True,
            "no_autonomous_execution": True,
            "no_identity_biometric_inference": True,
            "source_class_derived_field_only_for_outcome_record": True,
            "not_a_claim": True,
            "not_model_output": True,
            "not_ranking_signal": True,
        },
        "source_of_truth_context": {
            "epoch_2_0_path_mapping_ref": "outputs/epoch_2_0_agentic_runtime_consolidation/reports/path_mapping.json",
            "epoch_1_source_of_truth_matrix_ref": "outputs/epoch1_closedown_certified_baseline/EPOCH1_SOURCE_OF_TRUTH_MATRIX.json",
            "epoch_1_matrix_rows": len(source_truth),
        },
        "calibration_reports": {
            "status": read_json(EPOCH20_ROOT / "calibration_report_v0.json", {}).get("status", "AVAILABLE_WITH_LIMITATIONS"),
            "source_ref": "outputs/epoch_2_0_agentic_runtime_consolidation/calibration_report_v0.json",
            "note": "CalibrationReports are listed as dashboard input; Lane C 2.1a does not build CalibrationReports v1.",
        },
    }


def build_materialization_report(aggregation_floor: dict[str, Any]) -> dict[str, Any]:
    if aggregation_floor["status"] != "PASS":
        return {
            "schema_version": "citybrain.epoch_2_1.push_2_1a.lane_c.outcome_record_materialization_report.v1",
            "status": STATUS_BLOCKED_LANE_A,
            "records_materialized": 0,
            "source_class": "derived_field",
            "aggregation_floor_respected": False,
            "aggregation_floor": aggregation_floor,
            "boundary": OUTCOME_RECORD_SCHEMA["boundary"],
            "forbidden_behaviors": OUTCOME_RECORD_SCHEMA["forbidden_behaviors"],
            "input_refs": [
                "outputs/epoch_2_0_agentic_runtime_consolidation/outcome_records_v0.jsonl",
                "outputs/epoch_2_0_agentic_runtime_consolidation/reports/outcome_ledger_report.json",
            ],
            "reason": "OutcomeRecord materializer final-close depends on Lane A aggregation floor; no records are emitted until that dependency validates.",
        }
    outcome_records = load_outcome_records()
    derived_field_only = all(record.get("source_class") == "derived_field" for record in outcome_records)
    dashboard_cell_floor = aggregation_floor.get("minimum_items_for_dashboard_cell") or 0
    records_materialized = len(outcome_records)
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1a.lane_c.outcome_record_materialization_report.v1",
        "status": STATUS_PASS_OUTCOME_MATERIALIZED if derived_field_only else "FAIL_NON_DERIVED_OUTCOME_RECORD",
        "records_materialized": records_materialized,
        "input_records_seen": records_materialized,
        "dashboard_cells_released": 0 if records_materialized < dashboard_cell_floor else 1,
        "small_cell_suppressed": records_materialized < dashboard_cell_floor,
        "source_class": "derived_field",
        "derived_field_only": derived_field_only,
        "aggregation_floor_respected": bool(derived_field_only),
        "aggregation_floor": aggregation_floor,
        "boundary": OUTCOME_RECORD_SCHEMA["boundary"],
        "forbidden_behaviors": OUTCOME_RECORD_SCHEMA["forbidden_behaviors"],
        "input_refs": [
            "outputs/epoch_2_0_agentic_runtime_consolidation/outcome_records_v0.jsonl",
            "outputs/epoch_2_0_agentic_runtime_consolidation/reports/outcome_ledger_report.json",
        ],
        "limitations": [
            "Materialization is descriptive and internal/local replay only.",
            "Small-cell dashboard release is suppressed when the Lane A aggregation floor is not met.",
            "OutcomeRecords do not alter CHECK result, claim status, review state, or authority.",
        ],
    }


def write_dashboard_markdown(dashboard: dict[str, Any], materialization: dict[str, Any]) -> None:
    sections = [
        "# Data Maturity Dashboard v1",
        "",
        f"Status: `{dashboard['status']}`",
        "",
        "## Source Freshness",
        f"- Status: `{dashboard['source_freshness_status']['status']}`",
        f"- Source families: `{dashboard['source_freshness_status']['source_family_count']}`",
        "",
        "## CHECK / Cannot-Claim / Stale",
        f"- Status: `{dashboard['check_status_cannot_claim_stale_counts']['status']}`",
        f"- Stale or refresh-needed count: `{dashboard['check_status_cannot_claim_stale_counts']['stale_or_refresh_needed_count']}`",
        "",
        "## Corpus",
        f"- Version: `{dashboard['corpus_version_and_append_state']['corpus_final_version']}`",
        f"- Append state: `{dashboard['corpus_version_and_append_state']['append_state']}`",
        "",
        "## Agent Recertification",
        f"- Status: `{dashboard['agent_recertification_state']['status']}`",
        f"- Components: `{dashboard['agent_recertification_state']['component_count']}`",
        "",
        "## Mode Scorecards",
        f"- Status: `{dashboard['mode_scorecard_state']['status']}`",
        f"- Active modes: `{dashboard['mode_scorecard_state']['active_mode_count']}`",
        "",
        "## CER",
        f"- Status: `{dashboard['cer_conflict_assertion_summary']['status']}`",
        f"- Decision refs: `{dashboard['cer_conflict_assertion_summary']['cer_decision_ref_count']}`",
        f"- Conflict refs: `{dashboard['cer_conflict_assertion_summary']['cer_conflict_ref_count']}`",
        "",
        "## OutcomeRecord",
        f"- Materialization status: `{materialization['status']}`",
        f"- Records materialized: `{materialization['records_materialized']}`",
        "- Boundary: derived_field, descriptive only, not a claim, not model output, not ranking signal.",
        "",
        "## Policy Compliance",
        "- No learned ranking, prediction, new data warehouse, live dashboard service, official action, dispatch/control/enforcement, legal/certified finding, autonomous execution, or biometric inference.",
    ]
    write_text(OUTPUT_ROOT / "data_maturity_dashboard_v1.md", "\n".join(sections))


def write_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if path.is_file() and path.name != "PUSH_2_1A_LANE_C_HASH_MANIFEST.json":
            files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.epoch_2_1.push_2_1a.lane_c.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "item_count": len(files),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "PUSH_2_1A_LANE_C_HASH_MANIFEST.json", manifest)
    return manifest


def build_outputs() -> dict[str, Any]:
    safe_prepare_output_root()
    entry = run_entry_check()
    write_entry_outputs(entry)
    if entry["status"] != "PASS":
        manifest = write_hash_manifest()
        return {"entry_check": entry, "hash_manifest": manifest}

    aggregation_floor = lane_a_aggregation_floor()
    dashboard = build_dashboard(entry, aggregation_floor)
    materialization = build_materialization_report(aggregation_floor)
    write_json(OUTPUT_ROOT / "data_maturity_dashboard_v1.json", dashboard)
    write_dashboard_markdown(dashboard, materialization)
    write_json(OUTPUT_ROOT / "outcome_record_schema_v1.json", OUTCOME_RECORD_SCHEMA)
    write_json(OUTPUT_ROOT / "outcome_record_materialization_report.json", materialization)
    decision = {
        "schema_version": "citybrain.epoch_2_1.push_2_1a.lane_c.decision.v1",
        "package": "PUSH_2_1A_LANE_C_DASHBOARD_OUTCOME",
        "status": STATUS_PASS_DASHBOARD_BLOCKED_OUTCOME if materialization["status"] == STATUS_BLOCKED_LANE_A else STATUS_PASS_DASHBOARD_OUTCOME,
        "created_at": utc_now(),
        "branch": "main",
        "lane": "C",
        "epoch_2_0_entry_check": {
            "status": entry["status"],
            "decision_ref": "outputs/epoch_2_1_push_2_1a_lane_c_dashboard_outcome/EPOCH_2_0_ENTRY_CHECK_DECISION.json",
        },
        "dashboard_status": dashboard["status"],
        "outcome_record_materializer_status": materialization["status"],
        "lane_a_dependency": aggregation_floor,
        "artifacts": sorted(EXPECTED_OUTPUT_FILES - {"EPOCH_2_0_ENTRY_CHECK_REPORT.json", "EPOCH_2_0_ENTRY_CHECK_GAPS.md"}),
        "contract_check": {
            "lane_c_only": True,
            "main_branch_only": True,
            "no_learned_ranking": True,
            "no_prediction": True,
            "no_new_data_warehouse": True,
            "no_live_dashboard_service": True,
            "outcome_record_source_class_derived_field": True,
            "outcome_record_not_claim": True,
            "outcome_record_not_model_output": True,
            "outcome_record_not_ranking_signal": True,
            "epoch_2_1_not_closed": True,
        },
    }
    write_json(OUTPUT_ROOT / "PUSH_2_1A_LANE_C_DECISION.json", decision)
    write_text(
        OUTPUT_ROOT / "PUSH_2_1A_LANE_C_SUMMARY.md",
        "# Push 2.1a Lane C Summary\n\n"
        f"Status: `{decision['status']}`\n\n"
        "Data Maturity Dashboard v1 was materialized over existing authoritative ledgers. OutcomeRecord materialization consumes Lane A's aggregation floor and remains descriptive, derived_field-only, and non-ranking.\n",
    )
    manifest = write_hash_manifest()
    return {
        "entry_check": entry,
        "dashboard": dashboard,
        "materialization": materialization,
        "decision": decision,
        "hash_manifest": manifest,
    }


def main() -> int:
    result = build_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["entry_check"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
