from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1c_final_closeout"

EXPECTED_OUTPUT_FILES = {
    "EPOCH_2_1_FINAL_DECISION.json",
    "EPOCH_2_1_FINAL_PUBLISHED_STATUS.md",
    "EPOCH_2_1_LEDGER_ROWS.json",
    "EPOCH_2_1_SOURCE_OF_TRUTH_MATRIX_DELTA.md",
    "EPOCH_2_1_CORPUS_APPEND_REPORT.json",
    "EPOCH_2_1_HASH_MANIFEST",
    "EPOCH_2_2_ENTRY_BRIDGE.md",
    "EPOCH_3_PREREQ_DELTA.md",
}

PASS_STATUS = "PASS_EPOCH_2_1_FINAL_CLOSEOUT_WITH_LIMITATIONS"
BLOCK_STATUS = "BLOCKED_EPOCH_2_1_FINAL_CLOSEOUT"

ROOTS = {
    "epoch_2_0": REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation",
    "gate_2_1a": REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1a_foundations",
    "gate_2_1b": REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1b_content_hardening",
    "lane_2_1a_a": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention",
    "lane_2_1a_b": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_b_domain_framework",
    "lane_2_1a_c": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_c_dashboard_outcome",
    "lane_2_1b_a": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_a_rbac_audit_observability",
    "lane_2_1b_b": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_b_starter_domain_packs",
    "lane_2_1b_c": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_c_calibration_kit_ux",
    "lane_2_1c_a": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1c_lane_a_dubai_synthetic_pack",
    "lane_2_1c_b": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1c_lane_b_live_source_department_node_policy",
    "lane_2_1c_c": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1c_lane_c_federation_query_v0",
}

MANIFESTS = {
    "gate_2_1a": "HASH_MANIFEST.json",
    "gate_2_1b": "HASH_MANIFEST.json",
    "lane_2_1a_a": "HASH_MANIFEST.json",
    "lane_2_1a_b": "HASH_MANIFEST.json",
    "lane_2_1a_c": "PUSH_2_1A_LANE_C_HASH_MANIFEST.json",
    "lane_2_1b_a": "HASH_MANIFEST.json",
    "lane_2_1b_b": "HASH_MANIFEST.json",
    "lane_2_1b_c": "HASH_MANIFEST.json",
    "lane_2_1c_a": "HASH_MANIFEST.json",
    "lane_2_1c_b": "HASH_MANIFEST.json",
    "lane_2_1c_c": "HASH_MANIFEST.json",
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


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def current_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def prepare_output_root() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    existing = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}
    unexpected = sorted(existing - EXPECTED_OUTPUT_FILES)
    if unexpected:
        raise RuntimeError(f"Refusing to overwrite unexpected final closeout files: {unexpected}")


def verify_hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    manifest_path = root / manifest_name
    manifest = read_json(manifest_path, {})
    mismatches: list[dict[str, Any]] = []
    files = manifest.get("files", [])
    for row in files:
        target = root / row["path"]
        if not target.exists():
            mismatches.append({"path": row["path"], "error": "missing"})
            continue
        actual = sha256_file(target)
        if actual != row.get("sha256"):
            mismatches.append({"path": row["path"], "expected": row.get("sha256"), "actual": actual})
    return {
        "status": "PASS" if manifest_path.exists() and manifest.get("status") == "PASS" and not mismatches else "FAIL",
        "manifest_ref": rel(manifest_path) if manifest_path.exists() else None,
        "item_count": len(files),
        "mismatches": mismatches,
    }


def load_inputs() -> dict[str, Any]:
    return {
        "epoch_2_0_final": read_json(ROOTS["epoch_2_0"] / "decision.json", {}),
        "epoch_2_0_published_status": read_json(ROOTS["epoch_2_0"] / "final_published_status.json", {}),
        "gate_2_1a": read_json(ROOTS["gate_2_1a"] / "INTEGRATION_GATE_2_1A_DECISION.json", {}),
        "gate_2_1b": read_json(ROOTS["gate_2_1b"] / "INTEGRATION_GATE_2_1B_DECISION.json", {}),
        "privacy_decision": read_json(ROOTS["lane_2_1a_a"] / "PUSH_2_1A_LANE_A_DECISION.json", {}),
        "privacy_validation": read_json(ROOTS["lane_2_1a_a"] / "privacy_policy_validation_report.json", {}),
        "aggregation_floor": read_json(ROOTS["lane_2_1a_a"] / "aggregation_floor_policy_v1.json", {}),
        "domain_framework_decision": read_json(ROOTS["lane_2_1a_b"] / "PUSH_2_1A_LANE_B_DECISION.json", {}),
        "dashboard": read_json(ROOTS["lane_2_1a_c"] / "data_maturity_dashboard_v1.json", {}),
        "outcome_report": read_json(ROOTS["lane_2_1a_c"] / "outcome_record_materialization_report.json", {}),
        "rbac_decision": read_json(ROOTS["lane_2_1b_a"] / "PUSH_2_1B_LANE_A_DECISION.json", {}),
        "rbac_validation": read_json(ROOTS["lane_2_1b_a"] / "rbac_audit_validation_report.json", {}),
        "starter_decision": read_json(ROOTS["lane_2_1b_b"] / "PUSH_2_1B_LANE_B_DECISION.json", {}),
        "starter_validation": read_json(ROOTS["lane_2_1b_b"] / "starter_domain_pack_validation_report.json", {}),
        "starter_eval": read_json(ROOTS["lane_2_1b_b"] / "starter_domain_pack_eval_fixtures_report.json", {}),
        "starter_append": read_json(ROOTS["lane_2_1b_b"] / "corpus_source_of_truth_append_report.json", {}),
        "calibration_decision": read_json(ROOTS["lane_2_1b_c"] / "PUSH_2_1B_LANE_C_DECISION.json", {}),
        "calibration_generation": read_json(ROOTS["lane_2_1b_c"] / "calibration_report_generation_report.json", {}),
        "kit_audit": read_json(ROOTS["lane_2_1b_c"] / "native_kit_ux_boundary_audit.json", {}),
        "dubai_decision": read_json(ROOTS["lane_2_1c_a"] / "PUSH_2_1C_LANE_A_DECISION.json", {}),
        "dubai_validation": read_json(ROOTS["lane_2_1c_a"] / "dubai_pack_validation_report.json", {}),
        "dubai_source_audit": read_json(ROOTS["lane_2_1c_a"] / "dubai_synthetic_source_class_audit.json", {}),
        "live_policy_decision": read_json(ROOTS["lane_2_1c_b"] / "PUSH_2_1C_LANE_B_DECISION.json", {}),
        "live_policy_validation": read_json(ROOTS["lane_2_1c_b"] / "live_source_department_policy_validation_report.json", {}),
        "federation_decision": read_json(ROOTS["lane_2_1c_c"] / "PUSH_2_1C_LANE_C_DECISION.json", {}),
        "federation_results": read_json(ROOTS["lane_2_1c_c"] / "federation_query_nyc_london_fixture_results.json", {}),
        "federation_id_audit": read_json(ROOTS["lane_2_1c_c"] / "federation_city_scoped_id_audit.json", {}),
        "federation_boundary_audit": read_json(ROOTS["lane_2_1c_c"] / "federation_non_claim_boundary_audit.json", {}),
    }


def build_checks(inputs: dict[str, Any], hash_checks: dict[str, Any]) -> dict[str, Any]:
    pack_results = inputs["starter_validation"].get("pack_results", {})
    expected_domains = {"planning", "mobility", "utilities", "building"}
    starter_pack_checks = [
        domain in pack_results
        and pack_results[domain].get("status") == "PASS"
        and pack_results[domain].get("consumer_ref_count", 0) > 0
        and pack_results[domain].get("eval_fixture_count", 0) > 0
        for domain in expected_domains
    ]
    policy_scope = inputs["live_policy_decision"].get("policy_scope", {})
    final_non_goals = [
        inputs["dubai_decision"].get("boundaries", {}).get("trained_prediction_model_created") is False,
        inputs["dubai_decision"].get("boundaries", {}).get("federation_proof_created") is False,
        inputs["live_policy_decision"].get("boundaries", {}).get("live_camera_source_implementation_created") is False,
        inputs["live_policy_decision"].get("boundaries", {}).get("agent_activation_created") is False,
        inputs["federation_decision"].get("contract_check", {}).get("no_cross_city_learned_transfer") is True,
        inputs["federation_decision"].get("contract_check", {}).get("no_dubai_synthetic_proof_dependency") is True,
        inputs["federation_decision"].get("contract_check", {}).get("no_federated_write_approval_or_action") is True,
        inputs["calibration_decision"].get("contract_check", {}).get("no_trained_model_or_learning_state") is True,
        inputs["rbac_decision"].get("contract_check", {}).get("no_autonomous_monitoring_or_action") is True,
    ]
    return {
        "epoch_2_0_entry_check_passed": {
            "status": "PASS"
            if inputs["epoch_2_0_final"].get("status", "").startswith("PASS")
            and inputs["epoch_2_0_published_status"].get("status", "").startswith("PASS")
            else "FAIL",
            "refs": [
                rel(ROOTS["epoch_2_0"] / "decision.json"),
                rel(ROOTS["epoch_2_0"] / "final_published_status.json"),
            ],
        },
        "integration_gate_2_1a_passed": {
            "status": "PASS" if inputs["gate_2_1a"].get("status", "").startswith("PASS") else "FAIL",
            "refs": [rel(ROOTS["gate_2_1a"] / "INTEGRATION_GATE_2_1A_DECISION.json")],
        },
        "integration_gate_2_1b_passed": {
            "status": "PASS" if inputs["gate_2_1b"].get("status", "").startswith("PASS") else "FAIL",
            "refs": [rel(ROOTS["gate_2_1b"] / "INTEGRATION_GATE_2_1B_DECISION.json")],
        },
        "privacy_retention_and_aggregation_published": {
            "status": "PASS"
            if inputs["privacy_decision"].get("status", "").startswith("PASS")
            and inputs["privacy_validation"].get("status") == "PASS"
            and inputs["aggregation_floor"].get("minimum_items_for_dashboard_cell")
            and (ROOTS["lane_2_1a_a"] / "right_to_forget_policy_v1.md").exists()
            else "FAIL",
            "refs": [
                rel(ROOTS["lane_2_1a_a"] / "privacy_retention_policy_v1.json"),
                rel(ROOTS["lane_2_1a_a"] / "privacy_policy_validation_report.json"),
                rel(ROOTS["lane_2_1a_a"] / "aggregation_floor_policy_v1.json"),
                rel(ROOTS["lane_2_1a_a"] / "right_to_forget_policy_v1.md"),
            ],
        },
        "domain_pack_framework_and_ontology_governance_published": {
            "status": "PASS"
            if inputs["domain_framework_decision"].get("status", "").startswith("PASS")
            and (ROOTS["lane_2_1a_b"] / "domain_ontology_governance_v1.md").exists()
            and (ROOTS["lane_2_1a_b"] / "domain_pack_manifest_schema_v1.json").exists()
            else "FAIL",
            "refs": [
                rel(ROOTS["lane_2_1a_b"] / "domain_pack_framework_v1.md"),
                rel(ROOTS["lane_2_1a_b"] / "domain_ontology_governance_v1.md"),
            ],
        },
        "four_starter_packs_certified_with_consuming_capabilities": {
            "status": "PASS"
            if inputs["starter_decision"].get("status", "").startswith("PASS")
            and inputs["starter_decision"].get("starter_pack_count") == 4
            and all(starter_pack_checks)
            else "FAIL",
            "refs": [
                rel(ROOTS["lane_2_1b_b"] / "starter_domain_pack_validation_report.json"),
                rel(ROOTS["lane_2_1b_b"] / "starter_domain_pack_eval_fixtures_report.json"),
            ],
        },
        "dubai_synthetic_pack_certified_with_source_class_separation": {
            "status": "PASS"
            if inputs["dubai_decision"].get("status", "").startswith("PASS")
            and inputs["dubai_validation"].get("status", "").startswith("PASS")
            and inputs["dubai_source_audit"].get("status", "").startswith("PASS")
            and inputs["dubai_source_audit"].get("checks", {}).get("synthetic_and_real_facts_not_merged") is True
            and inputs["dubai_decision"].get("boundaries", {}).get("federation_proof_created") is False
            else "FAIL",
            "refs": [
                rel(ROOTS["lane_2_1c_a"] / "dubai_pack_validation_report.json"),
                rel(ROOTS["lane_2_1c_a"] / "dubai_synthetic_source_class_audit.json"),
            ],
        },
        "data_maturity_dashboard_and_outcome_records_flowing": {
            "status": "PASS"
            if inputs["dashboard"].get("status") == "PASS_DASHBOARD_MATERIALIZED_WITH_OUTCOME_RECORDS"
            and inputs["dashboard"].get("agent_recertification_state", {}).get("status") == "PASS"
            and inputs["dashboard"].get("mode_scorecard_state", {}).get("status") == "PASS"
            and inputs["outcome_report"].get("status") == "PASS_OUTCOME_RECORD_MATERIALIZED_AGGREGATION_FLOOR_COMPLIANT"
            and inputs["outcome_report"].get("source_class") == "derived_field"
            else "FAIL",
            "refs": [
                rel(ROOTS["lane_2_1a_c"] / "data_maturity_dashboard_v1.json"),
                rel(ROOTS["lane_2_1a_c"] / "outcome_record_materialization_report.json"),
            ],
        },
        "calibration_reports_v1_flowing_as_derived_field": {
            "status": "PASS"
            if inputs["calibration_generation"].get("status", "").startswith("PASS")
            and inputs["calibration_generation"].get("source_class") == "derived_field"
            and inputs["calibration_generation"].get("reports_generated") == 5
            else "FAIL",
            "refs": [rel(ROOTS["lane_2_1b_c"] / "calibration_report_generation_report.json")],
        },
        "rbac_audit_observability_baseline_hardened": {
            "status": "PASS"
            if inputs["rbac_decision"].get("status", "").startswith("PASS")
            and inputs["rbac_validation"].get("status") == "PASS"
            else "FAIL",
            "refs": [
                rel(ROOTS["lane_2_1b_a"] / "PUSH_2_1B_LANE_A_DECISION.json"),
                rel(ROOTS["lane_2_1b_a"] / "rbac_audit_validation_report.json"),
            ],
        },
        "live_source_and_department_node_policy_published_no_implementation": {
            "status": "PASS"
            if inputs["live_policy_decision"].get("status", "").startswith("PASS")
            and inputs["live_policy_validation"].get("status") == "PASS"
            and inputs["live_policy_decision"].get("boundaries", {}).get("live_camera_source_implementation_created") is False
            and all(policy_scope.values())
            else "FAIL",
            "refs": [
                rel(ROOTS["lane_2_1c_b"] / "live_source_department_policy_validation_report.json"),
                rel(ROOTS["lane_2_1c_b"] / "department_local_node_strategy_v1.md"),
            ],
        },
        "native_kit_ux_polish_landed_with_boundaries": {
            "status": "PASS"
            if inputs["kit_audit"].get("status", "").startswith("PASS")
            and inputs["kit_audit"].get("boundary", {}).get("no_official_action") is True
            and inputs["kit_audit"].get("boundary", {}).get("no_live_control") is True
            else "FAIL",
            "refs": [
                rel(ROOTS["lane_2_1b_c"] / "native_kit_ux_boundary_audit.json"),
                rel(ROOTS["lane_2_1b_c"] / "native_kit_ux_polish_report.md"),
            ],
        },
        "federation_query_v0_proven_on_nyc_london": {
            "status": "PASS"
            if inputs["federation_decision"].get("status", "").startswith("PASS")
            and inputs["federation_results"].get("status", "").startswith("PASS")
            and set(inputs["federation_results"].get("proof", {}).get("proof_cities", [])) == {"nyc", "london"}
            and inputs["federation_boundary_audit"].get("status") == "PASS"
            else "FAIL",
            "refs": [
                rel(ROOTS["lane_2_1c_c"] / "federation_query_nyc_london_fixture_results.json"),
                rel(ROOTS["lane_2_1c_c"] / "federation_non_claim_boundary_audit.json"),
            ],
        },
        "no_learned_trained_or_actionable_behavior_introduced": {
            "status": "PASS" if all(final_non_goals) else "FAIL",
            "refs": [
                rel(ROOTS["lane_2_1c_a"] / "PUSH_2_1C_LANE_A_DECISION.json"),
                rel(ROOTS["lane_2_1c_b"] / "PUSH_2_1C_LANE_B_DECISION.json"),
                rel(ROOTS["lane_2_1c_c"] / "PUSH_2_1C_LANE_C_DECISION.json"),
            ],
        },
        "source_of_truth_matrix_current": {
            "status": "PASS_WITH_LIMITATION"
            if inputs["starter_append"].get("status", "").startswith("PASS")
            and inputs["gate_2_1b"].get("gate_checks", {}).get("source_of_truth_matrix_current", {}).get("status", "").startswith("PASS")
            else "FAIL",
            "refs": [
                rel(ROOTS["gate_2_1b"] / "SOURCE_OF_TRUTH_MATRIX_DELTA.md"),
                rel(ROOTS["lane_2_1b_b"] / "corpus_source_of_truth_append_report.json"),
            ],
        },
        "regression_corpus_appended": {
            "status": "PASS_WITH_LIMITATION" if inputs["starter_append"].get("status", "").startswith("PASS") else "FAIL",
            "refs": [rel(ROOTS["lane_2_1b_b"] / "corpus_source_of_truth_append_report.json")],
            "note": "Append rows are published as no-mutation registration evidence; frozen upstream corpus files are not rewritten.",
        },
        "hash_manifest_clean": {
            "status": "PASS" if all(row["status"] == "PASS" for row in hash_checks.values()) else "FAIL",
            "hash_checks": hash_checks,
        },
    }


def build_ledger_rows(inputs: dict[str, Any], checks: dict[str, Any], final_status: str) -> list[dict[str, Any]]:
    rows = [
        ("epoch_2_0_entry", inputs["epoch_2_0_final"].get("status"), ROOTS["epoch_2_0"] / "decision.json"),
        ("integration_2_1a", inputs["gate_2_1a"].get("status"), ROOTS["gate_2_1a"] / "INTEGRATION_GATE_2_1A_DECISION.json"),
        ("integration_2_1b", inputs["gate_2_1b"].get("status"), ROOTS["gate_2_1b"] / "INTEGRATION_GATE_2_1B_DECISION.json"),
        ("push_2_1a_lane_a_privacy_retention", inputs["privacy_decision"].get("status"), ROOTS["lane_2_1a_a"] / "PUSH_2_1A_LANE_A_DECISION.json"),
        ("push_2_1a_lane_b_domain_framework", inputs["domain_framework_decision"].get("status"), ROOTS["lane_2_1a_b"] / "PUSH_2_1A_LANE_B_DECISION.json"),
        ("push_2_1a_lane_c_dashboard_outcome", inputs["dashboard"].get("status"), ROOTS["lane_2_1a_c"] / "PUSH_2_1A_LANE_C_DECISION.json"),
        ("push_2_1b_lane_a_rbac_audit_observability", inputs["rbac_decision"].get("status"), ROOTS["lane_2_1b_a"] / "PUSH_2_1B_LANE_A_DECISION.json"),
        ("push_2_1b_lane_b_starter_domain_packs", inputs["starter_decision"].get("status"), ROOTS["lane_2_1b_b"] / "PUSH_2_1B_LANE_B_DECISION.json"),
        ("push_2_1b_lane_c_calibration_kit_ux", inputs["calibration_decision"].get("status"), ROOTS["lane_2_1b_c"] / "PUSH_2_1B_LANE_C_DECISION.json"),
        ("push_2_1c_lane_a_dubai_synthetic_pack", inputs["dubai_decision"].get("status"), ROOTS["lane_2_1c_a"] / "PUSH_2_1C_LANE_A_DECISION.json"),
        ("push_2_1c_lane_b_live_source_department_node_policy", inputs["live_policy_decision"].get("status"), ROOTS["lane_2_1c_b"] / "PUSH_2_1C_LANE_B_DECISION.json"),
        ("push_2_1c_lane_c_federation_query_v0", inputs["federation_decision"].get("status"), ROOTS["lane_2_1c_c"] / "PUSH_2_1C_LANE_C_DECISION.json"),
        ("epoch_2_1_final_closeout", final_status, OUTPUT_ROOT / "EPOCH_2_1_FINAL_DECISION.json"),
    ]
    return [
        {
            "row_id": row_id,
            "status": status,
            "ref": rel(path),
            "included_in_epoch_2_1_closeout": True,
            "blocking": False if str(status).startswith("PASS") else row_id != "epoch_2_1_final_closeout",
        }
        for row_id, status, path in rows
    ]


def build_outputs() -> dict[str, Any]:
    prepare_output_root()
    inputs = load_inputs()
    hash_checks = {name: verify_hash_manifest(ROOTS[name], manifest_name) for name, manifest_name in MANIFESTS.items()}
    checks = build_checks(inputs, hash_checks)
    failed = {name: row for name, row in checks.items() if not row["status"].startswith("PASS")}
    final_status = PASS_STATUS if not failed and current_branch() == "main" else BLOCK_STATUS
    ledger_rows = build_ledger_rows(inputs, checks, final_status)

    write_json(
        OUTPUT_ROOT / "EPOCH_2_1_LEDGER_ROWS.json",
        {
            "schema_version": "citybrain.epoch_2_1.final_closeout.ledger_rows.v1",
            "status": "PASS" if final_status == PASS_STATUS else "FAIL",
            "created_at": utc_now(),
            "row_count": len(ledger_rows),
            "rows": ledger_rows,
        },
    )
    write_json(
        OUTPUT_ROOT / "EPOCH_2_1_CORPUS_APPEND_REPORT.json",
        {
            "schema_version": "citybrain.epoch_2_1.final_closeout.corpus_append_report.v1",
            "status": checks["regression_corpus_appended"]["status"],
            "created_at": utc_now(),
            "append_performed": False,
            "frozen_upstream_outputs_mutated": False,
            "registration_sources": [
                rel(ROOTS["lane_2_1b_b"] / "corpus_source_of_truth_append_report.json"),
                rel(ROOTS["gate_2_1b"] / "CORPUS_APPEND_REPORT.json"),
            ],
            "note": checks["regression_corpus_appended"]["note"],
        },
    )
    write_text(
        OUTPUT_ROOT / "EPOCH_2_1_SOURCE_OF_TRUTH_MATRIX_DELTA.md",
        "# Epoch 2.1 Source Of Truth Matrix Delta\n\n"
        "Status: `PASS_WITH_LIMITATION`\n\n"
        "- Epoch 2.1 keeps frozen upstream matrices immutable.\n"
        "- Starter domain packs are represented by no-mutation registration rows from Push 2.1b.\n"
        "- Dubai synthetic pack, live-source policy, and federation query v0 are additive local/replay artifacts.\n"
        "- Epoch 2.2 may consume these rows as the current local source-of-truth bridge.\n",
    )
    write_text(
        OUTPUT_ROOT / "EPOCH_2_2_ENTRY_BRIDGE.md",
        "# Epoch 2.2 Entry Bridge\n\n"
        f"Status: `{final_status}`\n\n"
        "Epoch 2.2 may start from the four starter domain packs, Native Kit UX boundary audit, "
        "Dubai synthetic pack, live-source onboarding policy, department-local node strategy, "
        "and federation query v0 proof, while preserving local/replay/review/query boundaries.\n\n"
        "Required carry-forward limitations:\n"
        "- No live-source implementation without a later separate gate.\n"
        "- No agent activation without consuming surfaces, RBAC/audit checks, and human approval gates.\n"
        "- No learned ranking, prediction, cross-city transfer, or trained model behavior.\n"
        "- No production/public API, dispatch, enforcement, official ticket/case, or legal finding.\n",
    )
    write_text(
        OUTPUT_ROOT / "EPOCH_3_PREREQ_DELTA.md",
        "# Epoch 3 Prereq Delta\n\n"
        "Deferred to Epoch 3 or later:\n"
        "- Trained ranking, prediction, counterfactual, learned memory, and cross-city learned transfer.\n"
        "- Model evaluation/release discipline for any learned component.\n"
        "- Live-source activation, production connector deployment, and production IAM.\n"
        "- Agent activation beyond local/replay/review/query fixture surfaces.\n",
    )

    decision = {
        "schema_version": "citybrain.epoch_2_1.final_closeout.decision.v1",
        "status": final_status,
        "created_at": utc_now(),
        "branch": current_branch(),
        "failed_checks": failed,
        "gate_checks": checks,
        "ledger_rows_ref": rel(OUTPUT_ROOT / "EPOCH_2_1_LEDGER_ROWS.json"),
        "source_of_truth_matrix_delta_ref": rel(OUTPUT_ROOT / "EPOCH_2_1_SOURCE_OF_TRUTH_MATRIX_DELTA.md"),
        "corpus_append_report_ref": rel(OUTPUT_ROOT / "EPOCH_2_1_CORPUS_APPEND_REPORT.json"),
        "epoch_2_2_entry_bridge_ref": rel(OUTPUT_ROOT / "EPOCH_2_2_ENTRY_BRIDGE.md"),
        "epoch_3_prereq_delta_ref": rel(OUTPUT_ROOT / "EPOCH_3_PREREQ_DELTA.md"),
        "limitations": [
            "Final closeout is local/replay/review/query only; it is not a production/public API claim.",
            "Source-of-truth and corpus updates are no-mutation append/delta artifacts, not rewrites of frozen upstream outputs.",
            "Live-source/camera onboarding is policy only, with no implementation or feed exception.",
            "Federation proof is query-only over NYC and London corpus ledgers; Dubai synthetic pack is not federation proof.",
            "No learned/trained model, ranking, prediction, cross-city learned transfer, or agent activation is introduced.",
        ],
    }
    write_json(OUTPUT_ROOT / "EPOCH_2_1_FINAL_DECISION.json", decision)
    write_text(
        OUTPUT_ROOT / "EPOCH_2_1_FINAL_PUBLISHED_STATUS.md",
        "# Epoch 2.1 Final Published Status\n\n"
        f"Status: `{final_status}`\n\n"
        "Epoch 2.1 closes with limitations. The closeout includes privacy/retention, domain-pack framework, "
        "four starter packs, data maturity dashboard, OutcomeRecord materializer, CalibrationReports v1, "
        "RBAC/audit/observability, Native Kit UX audit, Dubai synthetic pack, live-source policy, "
        "department-local node strategy, and NYC/London federation query v0.\n\n"
        "No production, live-source, autonomous action, official-action, learned-model, or public API claim is made.\n",
    )
    manifest = write_epoch_hash_manifest()
    return {"decision": decision, "ledger_rows": ledger_rows, "hash_manifest": manifest}


def write_epoch_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if path.is_file() and path.name != "EPOCH_2_1_HASH_MANIFEST":
            files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.epoch_2_1.final_closeout.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "item_count": len(files),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "EPOCH_2_1_HASH_MANIFEST", manifest)
    return manifest


def main() -> int:
    result = build_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["decision"]["status"] == PASS_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
