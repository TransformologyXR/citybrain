from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1a_foundations"

LANE_A_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention"
LANE_B_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_b_domain_framework"
LANE_C_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_c_dashboard_outcome"

EXPECTED_OUTPUT_FILES = {
    "INTEGRATION_GATE_2_1A_DECISION.json",
    "INTEGRATION_GATE_2_1A_SUMMARY.md",
    "PUSH_2_1B_ALLOWED_TO_OPEN.flag",
    "CONTRACT_CONVERGENCE_REPORT.json",
    "SOURCE_OF_TRUTH_MATRIX_DELTA.md",
    "CORPUS_APPEND_REPORT.json",
    "FINAL_OR_NEXT_BLOCKERS.md",
    "HASH_MANIFEST.json",
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


def prepare_output_root() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    existing = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}
    unexpected = sorted(existing - EXPECTED_OUTPUT_FILES)
    if unexpected:
        raise RuntimeError(f"Refusing to overwrite unexpected integration gate files: {unexpected}")


def verify_lane_hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    manifest_path = root / manifest_name
    manifest = read_json(manifest_path, {})
    files = manifest.get("files", [])
    mismatches = []
    for row in files:
        target = root / row["path"]
        if not target.exists():
            mismatches.append({"path": row["path"], "error": "missing"})
            continue
        actual = sha256_file(target)
        if actual != row.get("sha256"):
            mismatches.append({"path": row["path"], "expected": row.get("sha256"), "actual": actual})
    return {
        "status": "PASS" if manifest_path.exists() and not mismatches else "FAIL",
        "manifest_ref": rel(manifest_path) if manifest_path.exists() else None,
        "item_count": len(files),
        "mismatches": mismatches,
    }


def build_contract_convergence_report(inputs: dict[str, Any], checks: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.integration_gate_2_1a.contract_convergence.v1",
        "status": "PASS" if all(row["status"].startswith("PASS") for row in checks.values()) else "FAIL",
        "created_at": utc_now(),
        "shared_contracts": {
            "component_registry": "outputs/epoch_2_0_agentic_runtime_consolidation/component_registry_v1.json",
            "source_class": {
                "outcome_record": inputs["lane_c_materialization"].get("source_class"),
                "domain_pack_source_class_required": inputs["lane_b_decision"].get("rules", {}).get("source_class_required"),
                "synthetic_real_mixing_allowed": inputs["lane_a_policy"].get("source_class_rules", {}).get("synthetic_and_real_same_source_class_allowed"),
            },
            "retention": {
                "retention_matrix_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/retention_matrix_v1.json",
                "aggregation_floor_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/aggregation_floor_policy_v1.json",
            },
            "corpus": {
                "epoch1_corpus_ref": "outputs/epoch1_closedown_certified_baseline/EPOCH1_CORPUS_AND_MANIFEST_RECONCILIATION.json",
                "append_report_ref": "outputs/epoch_2_1_integration_gate_2_1a_foundations/CORPUS_APPEND_REPORT.json",
            },
            "dashboard_inputs": {
                "dashboard_ref": "outputs/epoch_2_1_push_2_1a_lane_c_dashboard_outcome/data_maturity_dashboard_v1.json",
                "no_new_metric_silo": inputs["lane_c_dashboard"].get("policy_compliance_flags", {}).get("no_new_data_warehouse"),
            },
        },
        "gate_checks": checks,
    }


def build_outputs() -> dict[str, Any]:
    prepare_output_root()

    lane_a_decision = read_json(LANE_A_ROOT / "PUSH_2_1A_LANE_A_DECISION.json", {})
    lane_a_validation = read_json(LANE_A_ROOT / "privacy_policy_validation_report.json", {})
    lane_a_policy = read_json(LANE_A_ROOT / "privacy_retention_policy_v1.json", {})
    aggregation_floor = read_json(LANE_A_ROOT / "aggregation_floor_policy_v1.json", {})
    lane_b_decision = read_json(LANE_B_ROOT / "PUSH_2_1A_LANE_B_DECISION.json", {})
    lane_c_decision = read_json(LANE_C_ROOT / "PUSH_2_1A_LANE_C_DECISION.json", {})
    lane_c_dashboard = read_json(LANE_C_ROOT / "data_maturity_dashboard_v1.json", {})
    lane_c_materialization = read_json(LANE_C_ROOT / "outcome_record_materialization_report.json", {})

    inputs = {
        "lane_a_decision": lane_a_decision,
        "lane_a_validation": lane_a_validation,
        "lane_a_policy": lane_a_policy,
        "aggregation_floor": aggregation_floor,
        "lane_b_decision": lane_b_decision,
        "lane_c_decision": lane_c_decision,
        "lane_c_dashboard": lane_c_dashboard,
        "lane_c_materialization": lane_c_materialization,
    }

    lane_hashes = {
        "lane_a": verify_lane_hash_manifest(LANE_A_ROOT, "HASH_MANIFEST.json"),
        "lane_b": verify_lane_hash_manifest(LANE_B_ROOT, "HASH_MANIFEST.json"),
        "lane_c": verify_lane_hash_manifest(LANE_C_ROOT, "PUSH_2_1A_LANE_C_HASH_MANIFEST.json"),
    }

    checks = {
        "privacy_retention_policy_fixture_tested": {
            "status": "PASS" if lane_a_decision.get("status", "").startswith("PASS") and lane_a_validation.get("status") == "PASS" else "FAIL",
            "refs": [rel(LANE_A_ROOT / "PUSH_2_1A_LANE_A_DECISION.json"), rel(LANE_A_ROOT / "privacy_policy_validation_report.json")],
        },
        "aggregation_floor_used_by_outcome_record_materializer": {
            "status": "PASS"
            if aggregation_floor.get("minimum_items_for_dashboard_cell")
            and lane_c_materialization.get("aggregation_floor", {}).get("status") == "PASS"
            and lane_c_materialization.get("aggregation_floor_respected") is True
            else "FAIL",
            "refs": [rel(LANE_A_ROOT / "aggregation_floor_policy_v1.json"), rel(LANE_C_ROOT / "outcome_record_materialization_report.json")],
            "records_materialized": lane_c_materialization.get("records_materialized"),
            "dashboard_cells_released": lane_c_materialization.get("dashboard_cells_released"),
            "small_cell_suppressed": lane_c_materialization.get("small_cell_suppressed"),
        },
        "domain_pack_framework_rejects_no_consumer": {
            "status": "PASS"
            if lane_b_decision.get("validator_results", {}).get("invalid_no_consumer", {}).get("status") == "FAIL"
            and "no_consuming_capability" in lane_b_decision.get("validator_results", {}).get("invalid_no_consumer", {}).get("errors", [])
            else "FAIL",
            "refs": [rel(LANE_B_ROOT / "domain_pack_validator.py"), rel(LANE_B_ROOT / "PUSH_2_1A_LANE_B_DECISION.json")],
        },
        "ontology_governance_requires_tests_versioning_compatibility": {
            "status": "PASS"
            if lane_b_decision.get("rules", {}).get("eval_fixtures_required")
            and lane_b_decision.get("rules", {}).get("compatibility_versioning_required")
            and lane_b_decision.get("rules", {}).get("rollback_deprecation_required")
            else "FAIL",
            "refs": [rel(LANE_B_ROOT / "domain_ontology_governance_v1.md"), rel(LANE_B_ROOT / "domain_pack_compatibility_policy_v1.md")],
        },
        "dashboard_uses_authoritative_ledgers_not_metric_silo": {
            "status": "PASS"
            if lane_c_dashboard.get("policy_compliance_flags", {}).get("no_new_data_warehouse") is True
            and lane_c_dashboard.get("agent_recertification_state", {}).get("source_ref")
            and lane_c_dashboard.get("source_of_truth_context", {}).get("epoch_2_0_path_mapping_ref")
            else "FAIL",
            "refs": [rel(LANE_C_ROOT / "data_maturity_dashboard_v1.json")],
        },
        "outcome_records_derived_field_only_not_model_or_ranking": {
            "status": "PASS"
            if lane_c_materialization.get("source_class") == "derived_field"
            and lane_c_materialization.get("derived_field_only") is True
            and lane_c_materialization.get("boundary", {}).get("not_model_output") is True
            and lane_c_materialization.get("boundary", {}).get("not_ranking_signal") is True
            else "FAIL",
            "refs": [rel(LANE_C_ROOT / "outcome_record_materialization_report.json"), rel(LANE_C_ROOT / "outcome_record_schema_v1.json")],
        },
        "source_of_truth_matrix_delta_recorded": {
            "status": "PASS_WITH_LIMITATION"
            if lane_c_dashboard.get("source_of_truth_context", {}).get("epoch_2_0_path_mapping_ref")
            else "FAIL",
            "refs": [rel(LANE_C_ROOT / "data_maturity_dashboard_v1.json"), "outputs/epoch_2_0_agentic_runtime_consolidation/reports/path_mapping.json"],
        },
        "corpus_append_reported": {
            "status": "PASS_WITH_LIMITATION",
            "refs": ["outputs/epoch1_closedown_certified_baseline/EPOCH1_CORPUS_AND_MANIFEST_RECONCILIATION.json"],
            "note": "Push 2.1a adds policies/framework/dashboard only; no domain corpus append occurs until Push 2.1b starter packs.",
        },
        "lane_hash_manifests_verified": {
            "status": "PASS" if all(row["status"] == "PASS" for row in lane_hashes.values()) else "FAIL",
            "lane_hashes": lane_hashes,
        },
    }

    contract_report = build_contract_convergence_report(inputs, checks)
    write_json(OUTPUT_ROOT / "CONTRACT_CONVERGENCE_REPORT.json", contract_report)
    write_json(
        OUTPUT_ROOT / "CORPUS_APPEND_REPORT.json",
        {
            "schema_version": "citybrain.epoch_2_1.integration_gate_2_1a.corpus_append_report.v1",
            "status": "PASS_WITH_LIMITATION",
            "created_at": utc_now(),
            "append_performed": False,
            "reason": "Push 2.1a is foundations only. Domain corpus append is deferred to Push 2.1b starter domain packs.",
            "current_corpus_ref": "outputs/epoch1_closedown_certified_baseline/EPOCH1_CORPUS_AND_MANIFEST_RECONCILIATION.json",
        },
    )
    write_text(
        OUTPUT_ROOT / "SOURCE_OF_TRUTH_MATRIX_DELTA.md",
        "# Source Of Truth Matrix Delta\n\n"
        "Status: `PASS_WITH_LIMITATION`\n\n"
        "- Epoch 2.0 source mapping remains the active path-mapping update reference.\n"
        "- Push 2.1a adds privacy/retention, domain-pack framework, and dashboard materialization surfaces.\n"
        "- No frozen upstream output is mutated by this integration gate.\n"
        "- Starter domain-pack corpus/source-of-truth rows are deferred to Push 2.1b.\n",
    )

    failed = {name: row for name, row in checks.items() if not row["status"].startswith("PASS")}
    decision_status = "PASS_PUSH_2_1A_FOUNDATIONS_GATE_WITH_LIMITATIONS" if not failed else "BLOCKED_PUSH_2_1B_FOUNDATION_GATE_FAILED"
    allowed = not failed
    decision = {
        "schema_version": "citybrain.epoch_2_1.integration_gate_2_1a.decision.v1",
        "status": decision_status,
        "created_at": utc_now(),
        "branch": "main",
        "push_2_1b_allowed_to_open": allowed,
        "required_inputs": {
            "lane_a": rel(LANE_A_ROOT),
            "lane_b": rel(LANE_B_ROOT),
            "lane_c": rel(LANE_C_ROOT),
        },
        "gate_checks": checks,
        "limitations": [
            "Source-of-truth delta is a no-mutation pointer update, not a rewrite of frozen Epoch 1 outputs.",
            "OutcomeRecord dashboard cell release is suppressed because materialized count is below Lane A's aggregation floor.",
            "Domain-pack framework is ready for Push 2.1b, but no starter packs are created in Push 2.1a.",
            "This is local/replay/review/query infrastructure only, not production security or live-source activation.",
        ],
        "non_goals_preserved": [
            "No production/public API claim.",
            "No autonomous monitoring/action.",
            "No official ticket/case/dispatch/control/enforcement/legal finding.",
            "No trained ranking, prediction, model output, or learned transfer.",
            "No live camera/source implementation.",
        ],
        "failed_checks": failed,
    }
    write_json(OUTPUT_ROOT / "INTEGRATION_GATE_2_1A_DECISION.json", decision)
    write_text(
        OUTPUT_ROOT / "INTEGRATION_GATE_2_1A_SUMMARY.md",
        "# Integration Gate 2.1a Summary\n\n"
        f"Status: `{decision_status}`\n\n"
        "- Lane A privacy/retention fixtures passed and aggregation floor is published.\n"
        "- Lane B domain-pack framework rejects packs with no consuming capability.\n"
        "- Lane C dashboard consumes authoritative ledgers and OutcomeRecord materialization uses Lane A's aggregation floor.\n"
        "- Push 2.1b may open only while preserving local/replay/review/query boundaries.\n",
    )
    write_text(
        OUTPUT_ROOT / "FINAL_OR_NEXT_BLOCKERS.md",
        "# Final Or Next Blockers\n\n"
        + ("No blocking issues for Push 2.1b opening.\n" if allowed else "\n".join(f"- `{name}`" for name in failed)),
    )
    if allowed:
        write_text(OUTPUT_ROOT / "PUSH_2_1B_ALLOWED_TO_OPEN.flag", "PASS\n")
    else:
        write_text(OUTPUT_ROOT / "PUSH_2_1B_ALLOWED_TO_OPEN.flag", "BLOCKED\n")

    manifest = write_hash_manifest()
    return {"decision": decision, "contract_convergence": contract_report, "hash_manifest": manifest}


def write_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.epoch_2_1.integration_gate_2_1a.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "item_count": len(files),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def main() -> int:
    result = build_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["decision"]["push_2_1b_allowed_to_open"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
