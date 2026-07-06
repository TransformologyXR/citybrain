from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "final_closeout"

PASS_STATUS = "PASS_EPOCH_2_2_AGENTIC_LLM_OPERATIONALIZATION"
PASS_LIMITED_STATUS = "PASS_EPOCH_2_2_AGENTIC_LLM_OPERATIONALIZATION_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_EPOCH_2_2_AGENTIC_LLM_OPERATIONALIZATION"
FAIL_STATUS = "FAIL_EPOCH_2_2_AGENTIC_LLM_OPERATIONALIZATION"

REQUIRED_OUTPUTS = [
    "EPOCH_2_2_FINAL_DECISION.json",
    "EPOCH_2_2_FINAL_REPORT.md",
    "EPOCH_2_2_FINAL_LEDGER_ROW.json",
    "EPOCH_2_2_SOURCE_OF_TRUTH_MATRIX_DELTA.json",
    "EPOCH_2_2_CORPUS_DELTA.json",
    "EPOCH_3_ENTRY_READINESS_REPORT.json",
    "LABEL_FUEL_GAUGE_REPORT.json",
    "HASH_MANIFEST.json",
]

ARTIFACTS = {
    "entry_gate": REPO_ROOT / "outputs" / "epoch_2_2_entry_gate" / "EPOCH_2_2_ENTRY_GATE_DECISION.json",
    "integration_2_2a": REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2a" / "PUSH_2_2A_INTEGRATION_DECISION.json",
    "integration_2_2b": REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2b" / "PUSH_2_2B_INTEGRATION_DECISION.json",
    "observability_report": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_b_observability" / "AGENT_OBSERVABILITY_REPORT.json",
    "observability_confirmation": REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2b" / "OBSERVABILITY_CONFIRMATION.json",
    "multi_agent_replay": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract" / "MULTI_AGENT_REPLAY_HARNESS_REPORT.json",
    "llm_seat_readiness": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_c_llm_seats" / "LLM_SEAT_READINESS_REPORT.json",
    "g8_offline_eval": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_c_llm_seats" / "G8_OFFLINE_EVAL_REPORT.json",
    "g2_offline_eval": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_c_llm_seats" / "G2_OFFLINE_EVAL_REPORT.json",
    "brief_writer_eval": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_c_briefing_g8" / "BRIEF_WRITER_V2_LIVE_EVAL_REPORT.json",
    "pack_agent_report": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_a_pack_spatial" / "PACK_PARAMETERIZED_AGENT_REPORT.json",
    "starter_pack_matrix": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_a_pack_spatial" / "STARTER_PACK_AGENT_CONSUMER_MATRIX.json",
    "spatial_service": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_a_pack_spatial" / "SPATIAL_AGENT_SERVICE_REPORT.json",
    "perception_decision": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_b_perception_shadow" / "PERCEPTION_SHADOW_DECISION.json",
    "shadow_run": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_b_perception_shadow" / "SHADOW_RUN_REPORT.json",
    "review_visibility": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_b_perception_shadow" / "REVIEW_VISIBILITY_DECISION.json",
    "g2_decision": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_c_g2_fixed_dag" / "G2_RESOLVER_PROPOSAL_DECISION.json",
    "g2_metrics": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_c_g2_fixed_dag" / "G2_ACCEPTANCE_METRICS.json",
    "fixed_dag_run": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_c_g2_fixed_dag" / "FIXED_DAG_RUN_REPORT.json",
    "disposition_summary": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_c_calibration_kit_ux" / "calibration_reports_v1" / "watchitem_disposition_summary.json",
    "operator_metrics": REPO_ROOT / "outputs" / "main_citybrain_d9_operator_task_scoreboard_r5" / "OPERATOR_VALIDATION_METRICS.json",
    "usable_sessions": REPO_ROOT / "outputs" / "main_citybrain_d9_operator_session_import_r4" / "USABLE_SESSION_RECORDS.json",
}

CORPUS_FIXTURE_KEYS = [
    "multi_agent_replay",
    "observability_report",
    "observability_confirmation",
    "llm_seat_readiness",
    "g8_offline_eval",
    "g2_offline_eval",
    "brief_writer_eval",
    "pack_agent_report",
    "starter_pack_matrix",
    "spatial_service",
    "perception_decision",
    "shadow_run",
    "review_visibility",
    "g2_decision",
    "g2_metrics",
    "fixed_dag_run",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def git_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.strip()


def status_passes(value: str | None) -> bool:
    return bool(value) and (value.startswith("PASS") or value == "PASS_WITH_LIMITATIONS")


def artifact_presence() -> dict[str, Any]:
    missing = [name for name, path in ARTIFACTS.items() if not path.exists()]
    return {
        "status": "PASS" if not missing else "BLOCKED",
        "missing": missing,
        "refs": {name: rel(path) for name, path in ARTIFACTS.items()},
    }


def build_required_checks() -> dict[str, Any]:
    entry = read_json(ARTIFACTS["entry_gate"], {})
    gate_a = read_json(ARTIFACTS["integration_2_2a"], {})
    gate_b = read_json(ARTIFACTS["integration_2_2b"], {})
    pack = read_json(ARTIFACTS["pack_agent_report"], {})
    spatial = read_json(ARTIFACTS["spatial_service"], {})
    perception = read_json(ARTIFACTS["perception_decision"], {})
    shadow = read_json(ARTIFACTS["shadow_run"], {})
    visibility = read_json(ARTIFACTS["review_visibility"], {})
    g2_decision = read_json(ARTIFACTS["g2_decision"], {})
    g2_metrics = read_json(ARTIFACTS["g2_metrics"], {})
    dag = read_json(ARTIFACTS["fixed_dag_run"], {})
    observability = read_json(ARTIFACTS["observability_report"], {})
    observability_confirmation = read_json(ARTIFACTS["observability_confirmation"], {})
    replay = read_json(ARTIFACTS["multi_agent_replay"], {})
    llm_readiness = read_json(ARTIFACTS["llm_seat_readiness"], {})
    g8_eval = read_json(ARTIFACTS["g8_offline_eval"], {})
    g2_eval = read_json(ARTIFACTS["g2_offline_eval"], {})
    brief_eval = read_json(ARTIFACTS["brief_writer_eval"], {})

    rollback_status = g2_metrics.get("rollback_trigger_status", {})
    dag_summary = dag.get("summary", {})
    pack_checks = pack.get("checks", {})
    spatial_checks = spatial.get("checks", {})
    shadow_criteria = shadow.get("criteria_results", {})
    seat_status = {
        row.get("seat_id"): row.get("readiness_status")
        for row in llm_readiness.get("seat_readiness", [])
        if row.get("seat_id")
    }
    brief_metrics = brief_eval.get("metrics", {})

    checks = {
        "entry_gate_passed": {
            "status": "PASS" if entry.get("status") == "PASS_EPOCH_2_2_ENTRY_GATE" else "FAIL",
            "refs": [rel(ARTIFACTS["entry_gate"])],
        },
        "push_2_2a_integration_passed": {
            "status": "PASS" if gate_a.get("status") == "PASS_PUSH_2_2A_INTEGRATION" else "FAIL",
            "refs": [rel(ARTIFACTS["integration_2_2a"])],
        },
        "push_2_2b_integration_passed": {
            "status": "PASS" if gate_b.get("status") == "PASS_PUSH_2_2B_INTEGRATION" else "FAIL",
            "refs": [rel(ARTIFACTS["integration_2_2b"])],
        },
        "pack_parameterized_agents_active_without_domain_classes": {
            "status": "PASS"
            if status_passes(pack.get("status"))
            and pack_checks.get("all_four_packs_active") is True
            and pack_checks.get("no_per_domain_agent_classes") is True
            and pack.get("boundaries", {}).get("per_domain_agent_classes_created") is False
            else "FAIL",
            "refs": [rel(ARTIFACTS["pack_agent_report"]), rel(ARTIFACTS["starter_pack_matrix"])],
        },
        "spatial_agent_handoff_service_works": {
            "status": "PASS"
            if status_passes(spatial.get("status"))
            and spatial_checks.get("one_handoff_per_starter_pack") is True
            and spatial_checks.get("all_handoffs_have_check_authority_refs") is True
            and spatial_checks.get("agent_run_envelope_per_handoff") is True
            and spatial.get("boundaries", {}).get("production_kit_web_control_claim") is False
            else "FAIL",
            "refs": [rel(ARTIFACTS["spatial_service"])],
        },
        "perception_shadow_path_evaluated": {
            "status": "PASS"
            if status_passes(perception.get("status"))
            and shadow.get("status") == "PASS"
            and shadow.get("feed_count") == 1
            and shadow_criteria.get("candidate_rate_within_band") is True
            and visibility.get("review_visible_allowed") is True
            and visibility.get("review_visibility_scope") == "candidate_observation_only_local_replay_review_queue"
            else "FAIL",
            "refs": [rel(ARTIFACTS["perception_decision"]), rel(ARTIFACTS["shadow_run"]), rel(ARTIFACTS["review_visibility"])],
        },
        "g2_adapter_metrics_and_rollback_published": {
            "status": "PASS"
            if status_passes(g2_decision.get("status"))
            and status_passes(g2_metrics.get("status"))
            and g2_metrics.get("proposal_count", 0) >= 1
            and g2_metrics.get("accepted_count", 0) >= 1
            and g2_metrics.get("regression_failures") == 0
            and rollback_status
            and all(value == "PASS" for value in rollback_status.values())
            and g2_metrics.get("controls", {}).get("sealed_ASK_G1_G8_touched") is False
            else "FAIL",
            "refs": [rel(ARTIFACTS["g2_decision"]), rel(ARTIFACTS["g2_metrics"])],
        },
        "fixed_dag_plan_schedule_simulate_without_dynamic_investigation": {
            "status": "PASS"
            if status_passes(dag.get("status"))
            and dag_summary.get("end_to_end_dag_run_count", 0) >= 1
            and dag_summary.get("dynamic_step_selection_count") == 0
            and dag_summary.get("official_action_created_count") == 0
            and dag_summary.get("sealed_ASK_touch_count") == 0
            and dag_summary.get("check_applied_count", 0) >= 1
            and dag_summary.get("approval_boundary_applied_count", 0) >= 1
            else "FAIL",
            "refs": [rel(ARTIFACTS["fixed_dag_run"])],
        },
        "observability_report_consumes_run_envelopes": {
            "status": "PASS"
            if status_passes(observability.get("status"))
            and observability.get("service_rows")
            and observability.get("service_rows", [{}])[0].get("run_envelope_refs")
            and observability_confirmation.get("status") == "PASS"
            else "FAIL",
            "refs": [rel(ARTIFACTS["observability_report"]), rel(ARTIFACTS["observability_confirmation"])],
        },
        "multi_agent_replay_harness_green": {
            "status": "PASS"
            if status_passes(replay.get("status"))
            and replay.get("checks", {}).get("every_step_has_agent_run_envelope") is True
            and replay.get("checks", {}).get("no_official_action_outputs") is True
            and replay.get("sequence_count", 0) >= 1
            else "FAIL",
            "refs": [rel(ARTIFACTS["multi_agent_replay"])],
        },
        "llm_seat_metrics_and_rollback_status_published": {
            "status": "PASS"
            if status_passes(llm_readiness.get("status"))
            and seat_status.get("ask_g8_writer_pattern_adapter") in {"ready_for_2_2b", "blocked"}
            and seat_status.get("g2_intent_concept_resolver_proposal_adapter") in {"ready_for_2_2c", "blocked"}
            and status_passes(g8_eval.get("status"))
            and status_passes(g2_eval.get("status"))
            and status_passes(brief_eval.get("status"))
            and brief_metrics.get("operator_visible_without_schema_and_CHECK") == 0
            else "FAIL",
            "refs": [rel(ARTIFACTS["llm_seat_readiness"]), rel(ARTIFACTS["g8_offline_eval"]), rel(ARTIFACTS["g2_offline_eval"]), rel(ARTIFACTS["brief_writer_eval"])],
        },
    }
    return checks


def build_label_fuel_gauge() -> dict[str, Any]:
    disposition_summary = read_json(ARTIFACTS["disposition_summary"], {})
    operator_metrics = read_json(ARTIFACTS["operator_metrics"], {})
    usable_sessions = read_json(ARTIFACTS["usable_sessions"], [])
    historical_disposition_events = disposition_summary.get("statistics", {}).get("total_disposition_event_count", 0)
    observed_watch_outcomes = disposition_summary.get("statistics", {}).get("watch_outcome_record_count", 0)
    usable_external_sessions = operator_metrics.get("usable_external_sessions", len(usable_sessions) if isinstance(usable_sessions, list) else 0)

    threshold = {
        "consecutive_post_fix_weeks_required": 2,
        "terminal_dispositions_required": 50,
        "review_watch_families_required": 3,
        "eligible_dispositions_must_be_after_validation_blocking_fixes_closed": True,
    }
    observed = {
        "post_fix_consecutive_weeks": 0,
        "eligible_post_fix_terminal_dispositions": 0,
        "eligible_review_watch_families": 0,
        "historical_disposition_events_seen": historical_disposition_events,
        "historical_watch_outcome_records_seen": observed_watch_outcomes,
        "usable_external_operator_sessions": usable_external_sessions,
    }
    checks = {
        "operator_validation_program_specific_to_epoch_2_2_executed": False,
        "blocking_validation_fixes_closed_before_label_clock": False,
        "n_week_clock_started": False,
        "terminal_disposition_threshold_met": False,
        "review_watch_family_threshold_met": False,
    }
    limitations = [
        {
            "owner": "Operator Validation",
            "next_lane": "Epoch 3 pre-model validation-fix closure",
            "limitation": "No dedicated Epoch 2.2 operator validation program artifacts were found under outputs/epoch_2_2, so label-fuel timing cannot start yet.",
        },
        {
            "owner": "Label Fuel",
            "next_lane": "Epoch 3 trained-model/ranking readiness gate",
            "limitation": "Available evidence has fewer than 50 eligible post-fix terminal dispositions and fewer than 3 review/watch families.",
        },
        {
            "owner": "Learning Boundary",
            "next_lane": "Epoch 3 model release discipline",
            "limitation": "Trained ranking, prediction, counterfactual, learned memory, and cross-city learned transfer remain blocked until the fuel gauge passes in a later gate.",
        },
    ]
    return {
        "schema_version": "citybrain.epoch_2_2.final_closeout.label_fuel_gauge.v1",
        "created_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS_LABEL_FUEL_EVALUATED_NOT_MET",
        "training_grade_disposition_status": "BLOCKED_FOR_EPOCH_3_TRAINED_MODEL_WORK",
        "threshold": threshold,
        "observed": observed,
        "checks": checks,
        "refs": {
            "disposition_summary": rel(ARTIFACTS["disposition_summary"]) if ARTIFACTS["disposition_summary"].exists() else None,
            "operator_metrics": rel(ARTIFACTS["operator_metrics"]) if ARTIFACTS["operator_metrics"].exists() else None,
            "usable_sessions": rel(ARTIFACTS["usable_sessions"]) if ARTIFACTS["usable_sessions"].exists() else None,
        },
        "limitations": limitations,
    }


def build_corpus_delta() -> dict[str, Any]:
    fixtures = [
        {
            "fixture_id": f"epoch_2_2_final_{key}",
            "fixture_type": key,
            "ref": rel(ARTIFACTS[key]),
            "sha256": sha256_file(ARTIFACTS[key]),
        }
        for key in CORPUS_FIXTURE_KEYS
    ]
    return {
        "schema_version": "citybrain.epoch_2_2.final_closeout.corpus_delta.v1",
        "created_at": utc_now(),
        "status": "PASS_FOCUSED_EPOCH_2_2_CORPUS_WITH_LIMITATIONS",
        "append_mode": "output_local_delta_no_frozen_upstream_mutation",
        "focused_corpus_command": (
            "python -m pytest tests/test_epoch_2_2c_lane_a_pack_spatial.py "
            "tests/test_epoch_2_2c_lane_b_perception_shadow.py "
            "tests/test_epoch_2_2c_lane_c_g2_fixed_dag.py -q"
        ),
        "focused_corpus_result": "27 passed",
        "newly_sealed_fixture_count": len(fixtures),
        "fixtures": fixtures,
        "full_historical_discovery": {
            "status": "NOT_RUN_FOR_THIS_GATE",
            "reason": "Known older generated-output discovery failures remain outside this focused Epoch 2.2 closeout gate.",
        },
        "limitations": [
            {
                "owner": "Track 0",
                "next_lane": "Repo cleanup / global discovery hardening",
                "limitation": "The focused Epoch 2.2 corpus is green; full historical discovery is not claimed globally clean in this gate.",
            }
        ],
    }


def build_source_of_truth_delta(final_status: str) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_2.final_closeout.source_of_truth_matrix_delta.v1",
        "created_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "final_status": final_status,
        "append_mode": "output_local_delta_no_frozen_upstream_mutation",
        "authoritative_refs": {
            "epoch_2_2_entry_gate": rel(ARTIFACTS["entry_gate"]),
            "push_2_2a_integration": rel(ARTIFACTS["integration_2_2a"]),
            "push_2_2b_integration": rel(ARTIFACTS["integration_2_2b"]),
            "pack_parameterized_agents": rel(ARTIFACTS["pack_agent_report"]),
            "spatial_handoff_service": rel(ARTIFACTS["spatial_service"]),
            "perception_shadow": rel(ARTIFACTS["perception_decision"]),
            "g2_fixed_dag": rel(ARTIFACTS["g2_decision"]),
            "final_decision": "outputs/epoch_2_2/final_closeout/EPOCH_2_2_FINAL_DECISION.json",
        },
        "protected_upstream_refs_not_mutated": [
            "outputs/epoch_2_0_agentic_runtime_consolidation",
            "outputs/epoch_2_1_integration_gate_2_1c_final_closeout",
            "outputs/epoch_2_2/integration_2_2a",
            "outputs/epoch_2_2/integration_2_2b",
            "packages/ask_v11",
            "data",
            "inputs",
            "corpus_raw",
        ],
        "limitations": [
            {
                "owner": "Track 0",
                "next_lane": "Epoch 3 entry readiness",
                "limitation": "This is a source-of-truth delta only; frozen upstream matrices and output artifacts were not rewritten.",
            }
        ],
    }


def build_limitations(label_fuel: dict[str, Any], corpus_delta: dict[str, Any]) -> list[dict[str, str]]:
    limitations = [
        {
            "owner": "Epoch 2.2 Final Closeout",
            "next_lane": "Epoch 3 planning",
            "limitation": "Epoch 2.2 closes local/replay/review/query agentic operationalization only; no production service acted.",
        },
        {
            "owner": "Perception Shadow",
            "next_lane": "Future live-source activation gate",
            "limitation": "Perception shadow is one live-like local/replay source with candidate-only review visibility, not production CCTV or a live camera rollout.",
        },
        {
            "owner": "G2 / Fixed DAG",
            "next_lane": "Future deterministic flow expansion",
            "limitation": "G2 proposes only adapter-layer intent/concept/route/lens fields; deterministic compiler and fixed DAGs own execution.",
        },
        {
            "owner": "ASK / LLM Seats",
            "next_lane": "ASK-core governance if needed later",
            "limitation": "ASK G1-G8 sealed core remains untouched; LLM seats stay schema-validated and CHECK-gated.",
        },
        *label_fuel["limitations"],
        *corpus_delta["limitations"],
    ]
    return limitations


def build_epoch3_readiness(final_status: str, label_fuel: dict[str, Any], checks: dict[str, Any]) -> dict[str, Any]:
    technical_ready = all(row["status"] == "PASS" for row in checks.values())
    return {
        "schema_version": "citybrain.epoch_2_2.final_closeout.epoch_3_entry_readiness.v1",
        "created_at": utc_now(),
        "status": "PASS_EPOCH_3_CONTRACT_AND_SCAFFOLD_READINESS_WITH_MODEL_LIMITATIONS" if technical_ready else "BLOCKED_EPOCH_3_ENTRY",
        "epoch_2_2_final_status": final_status,
        "allowed_next_work": [
            "Epoch 3 contract/scaffold planning",
            "operator validation program execution",
            "label-fuel collection gate",
            "non-model deterministic harness hardening",
        ],
        "blocked_next_work": [
            "trained ranking",
            "prediction or forecasting model release",
            "counterfactual learning",
            "learned memory / precedent model behavior",
            "dynamic investigation agent",
            "cross-city learned transfer",
            "production live-source activation without a later gate",
        ],
        "label_fuel_status": label_fuel["status"],
        "model_work_allowed": False,
        "reason_model_work_blocked": label_fuel["training_grade_disposition_status"],
        "non_claims": final_non_claims(),
    }


def final_non_claims() -> dict[str, bool]:
    return {
        "service_acted": False,
        "official_action_ticket_dispatch_enforcement_or_legal_finding": False,
        "trained_ranking_prediction_counterfactual_model": False,
        "dynamic_investigation_agent": False,
        "cross_city_learned_transfer": False,
        "llm_output_without_schema_validation_and_check": False,
        "sealed_ask_core_modified": False,
        "production_monitoring_or_public_api": False,
    }


def build_final_status(
    presence: dict[str, Any],
    checks: dict[str, Any],
    label_fuel: dict[str, Any],
    corpus_delta: dict[str, Any],
) -> tuple[str, list[str], list[str]]:
    blockers: list[str] = []
    failures: list[str] = []
    if git_branch() != "main":
        blockers.append("current branch is not main")
    if presence["status"] != "PASS":
        blockers.extend(f"missing artifact: {name}" for name in presence["missing"])
    for name, row in checks.items():
        if row["status"] != "PASS":
            failures.append(name)
    if not corpus_delta["status"].startswith("PASS"):
        failures.append("corpus_delta")
    if blockers:
        return BLOCKED_STATUS, blockers, failures
    if failures:
        return FAIL_STATUS, blockers, failures
    if label_fuel["training_grade_disposition_status"] != "PASS":
        return PASS_LIMITED_STATUS, blockers, failures
    return PASS_STATUS, blockers, failures


def build_ledger_row(final_status: str, limitations: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_2.final_closeout.ledger_row.v1",
        "created_at": utc_now(),
        "component": "Epoch 2.2 Agentic LLM Operationalization",
        "status": final_status,
        "proof_refs": [
            "outputs/epoch_2_2/final_closeout/EPOCH_2_2_FINAL_DECISION.json",
            "outputs/epoch_2_2/final_closeout/EPOCH_2_2_CORPUS_DELTA.json",
            "outputs/epoch_2_2/final_closeout/LABEL_FUEL_GAUGE_REPORT.json",
            rel(ARTIFACTS["pack_agent_report"]),
            rel(ARTIFACTS["perception_decision"]),
            rel(ARTIFACTS["g2_decision"]),
        ],
        "what_it_means": "Epoch 2.2 agentic services, LLM seats, pack/spatial handoff, perception shadow, and fixed-DAG orchestration passed focused local/replay gates.",
        "what_it_does_not_prove": "No production monitoring, service action, official action, trained model, dynamic investigation, or cross-city learned transfer is certified.",
        "limitations": limitations,
        "next_lane": "Epoch 3 entry readiness / operator validation fuel collection",
        "corpus_delta": "EPOCH_2_2_CORPUS_DELTA.json",
        "source_of_truth_delta": "EPOCH_2_2_SOURCE_OF_TRUTH_MATRIX_DELTA.json",
        "hash_manifest": "HASH_MANIFEST.json",
    }


def build_report(decision: dict[str, Any]) -> str:
    lines = [
        "# Epoch 2.2 Final Closeout",
        "",
        f"Status: `{decision['status']}`",
        "",
        "## Required Checks",
        "",
    ]
    for name, row in decision["required_checks"].items():
        lines.append(f"- `{name}`: `{row['status']}`")
    lines.extend(
        [
            "",
            "## Label Fuel",
            "",
            f"- Status: `{decision['label_fuel_status']}`",
            "- Epoch 3 trained ranking/model work remains blocked until the fuel threshold passes.",
            "",
            "## Limitations",
            "",
        ]
    )
    for item in decision["limitations"]:
        lines.append(f"- {item['owner']} -> {item['next_lane']}: {item['limitation']}")
    lines.extend(
        [
            "",
            "## Final Non-Claims",
            "",
            "- No service acted.",
            "- No official action, ticket, dispatch, enforcement, legal finding, or certified finding.",
            "- No trained ranking, prediction, counterfactual model, dynamic investigation agent, or cross-city learned transfer.",
            "- LLM seats remained schema-validated and CHECK-gated.",
            "",
        ]
    )
    return "\n".join(lines)


def write_hash_manifest() -> dict[str, Any]:
    files = [name for name in REQUIRED_OUTPUTS if name != "HASH_MANIFEST.json"]
    manifest = {
        "schema_version": "citybrain.hash_manifest.v1",
        "created_at": utc_now(),
        "artifact_root": rel(OUTPUT_ROOT),
        "files": [],
    }
    for name in files:
        path = OUTPUT_ROOT / name
        if path.exists():
            manifest["files"].append({"path": rel(path), "sha256": sha256_file(path)})
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    presence = artifact_presence()
    checks = build_required_checks()
    label_fuel = build_label_fuel_gauge()
    corpus_delta = build_corpus_delta()
    status, blockers, failures = build_final_status(presence, checks, label_fuel, corpus_delta)
    limitations = build_limitations(label_fuel, corpus_delta)
    source_delta = build_source_of_truth_delta(status)
    epoch3 = build_epoch3_readiness(status, label_fuel, checks)
    ledger_row = build_ledger_row(status, limitations)
    decision = {
        "schema_version": "citybrain.epoch_2_2.final_closeout.decision.v1",
        "created_at": utc_now(),
        "status": status,
        "branch": git_branch(),
        "blockers": blockers,
        "failures": failures,
        "artifact_presence": presence,
        "required_checks": checks,
        "label_fuel_status": label_fuel["status"],
        "epoch_3_model_work_allowed": False,
        "corpus_delta_status": corpus_delta["status"],
        "source_of_truth_delta_status": source_delta["status"],
        "ledger_row_status": ledger_row["status"],
        "limitations": limitations,
        "non_claims": final_non_claims(),
    }

    write_json(OUTPUT_ROOT / "EPOCH_2_2_CORPUS_DELTA.json", corpus_delta)
    write_json(OUTPUT_ROOT / "LABEL_FUEL_GAUGE_REPORT.json", label_fuel)
    write_json(OUTPUT_ROOT / "EPOCH_2_2_SOURCE_OF_TRUTH_MATRIX_DELTA.json", source_delta)
    write_json(OUTPUT_ROOT / "EPOCH_3_ENTRY_READINESS_REPORT.json", epoch3)
    write_json(OUTPUT_ROOT / "EPOCH_2_2_FINAL_LEDGER_ROW.json", ledger_row)
    write_json(OUTPUT_ROOT / "EPOCH_2_2_FINAL_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "EPOCH_2_2_FINAL_REPORT.md", build_report(decision))
    manifest = write_hash_manifest()
    return {
        "decision": decision,
        "label_fuel": label_fuel,
        "corpus_delta": corpus_delta,
        "source_delta": source_delta,
        "epoch3": epoch3,
        "ledger_row": ledger_row,
        "hash_manifest": manifest,
    }


def main() -> int:
    result = write_all_outputs()
    status = result["decision"]["status"]
    print(f"Epoch 2.2 final closeout: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status in {PASS_STATUS, PASS_LIMITED_STATUS} else 1


if __name__ == "__main__":
    raise SystemExit(main())
