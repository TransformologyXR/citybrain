from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1b_content_hardening"

LANE_A_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_a_rbac_audit_observability"
LANE_B_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_b_starter_domain_packs"
LANE_C_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_c_calibration_kit_ux"

EXPECTED_OUTPUT_FILES = {
    "INTEGRATION_GATE_2_1B_DECISION.json",
    "INTEGRATION_GATE_2_1B_SUMMARY.md",
    "PUSH_2_1C_ALLOWED_TO_OPEN.flag",
    "CONTENT_HARDENING_CONVERGENCE_REPORT.json",
    "SOURCE_OF_TRUTH_MATRIX_DELTA.md",
    "CORPUS_APPEND_REPORT.json",
    "FINAL_OR_NEXT_BLOCKERS.md",
    "HASH_MANIFEST.json",
}

PASS_STATUS = "PASS_PUSH_2_1B_CONTENT_HARDENING_GATE_WITH_LIMITATIONS"
BLOCK_STATUS = "BLOCKED_PUSH_2_1C_CONTENT_HARDENING_GATE_FAILED"


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
        raise RuntimeError(f"Refusing to overwrite unexpected integration gate files: {unexpected}")


def verify_lane_hash_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "HASH_MANIFEST.json"
    manifest = read_json(manifest_path, {})
    files = manifest.get("files", [])
    mismatches: list[dict[str, Any]] = []
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


def all_true(values: list[bool]) -> bool:
    return all(value is True for value in values)


def build_checks(inputs: dict[str, Any], lane_hashes: dict[str, Any]) -> dict[str, Any]:
    lane_a_decision = inputs["lane_a_decision"]
    lane_a_validation = inputs["lane_a_validation"]
    lane_a_rbac = inputs["lane_a_rbac"]
    lane_a_observability = inputs["lane_a_observability"]
    lane_b_decision = inputs["lane_b_decision"]
    lane_b_validation = inputs["lane_b_validation"]
    lane_b_eval = inputs["lane_b_eval"]
    lane_b_append = inputs["lane_b_append"]
    lane_c_decision = inputs["lane_c_decision"]
    lane_c_generation = inputs["lane_c_generation"]
    lane_c_ux = inputs["lane_c_ux"]

    pack_results = lane_b_validation.get("pack_results", {})
    eval_domains = lane_b_eval.get("domains", {})
    expected_domains = {"planning", "mobility", "utilities", "building"}
    pack_checks = [
        domain in pack_results
        and pack_results[domain].get("status") == "PASS"
        and pack_results[domain].get("consumer_ref_count", 0) > 0
        and pack_results[domain].get("eval_fixture_count", 0) > 0
        for domain in expected_domains
    ]
    eval_checks = [
        domain in eval_domains
        and len(eval_domains[domain].get("consuming_capability_refs", [])) > 0
        and len(eval_domains[domain].get("mode_fixture_refs", [])) > 0
        for domain in expected_domains
    ]

    ux_required = lane_c_ux.get("required_display_element_audit", {})
    ux_keys = [
        "evidence_refs",
        "source_class",
        "check_report_summary",
        "authority_envelope_summary",
        "cannot_claim_visibility",
        "not_executed_visibility",
        "safe_next_looks",
        "limitations",
        "review_state_display",
    ]

    lane_a_contract = lane_a_decision.get("contract_check", {})
    lane_b_boundaries = lane_b_decision.get("boundaries", {})
    lane_c_contract = lane_c_decision.get("contract_check", {})

    append_entries = lane_b_append.get("registration_entries", [])

    return {
        "rbac_audit_baseline_fixture_tested": {
            "status": "PASS"
            if lane_a_decision.get("status", "").startswith("PASS")
            and lane_a_validation.get("status") == "PASS"
            and lane_a_rbac.get("status") == "PASS"
            and lane_a_observability.get("environment_scope") == "local_replay_review_query"
            and all(row.get("status") == "PASS" for row in lane_a_validation.get("fixture_results", []))
            else "FAIL",
            "refs": [
                rel(LANE_A_ROOT / "PUSH_2_1B_LANE_A_DECISION.json"),
                rel(LANE_A_ROOT / "rbac_audit_validation_report.json"),
                rel(LANE_A_ROOT / "rbac_policy_matrix_v1.json"),
                rel(LANE_A_ROOT / "observability_envelope_v1.json"),
            ],
        },
        "four_starter_packs_pass_domain_pack_validator": {
            "status": "PASS"
            if lane_b_decision.get("status", "").startswith("PASS")
            and lane_b_decision.get("starter_pack_count") == 4
            and set(lane_b_decision.get("starter_domains", [])) == expected_domains
            and lane_b_validation.get("status") == "PASS"
            and all_true(pack_checks)
            else "FAIL",
            "domains": sorted(expected_domains),
            "refs": [
                rel(LANE_B_ROOT / "PUSH_2_1B_LANE_B_DECISION.json"),
                rel(LANE_B_ROOT / "starter_domain_pack_validation_report.json"),
            ],
        },
        "starter_packs_have_consuming_capability_and_eval_fixtures": {
            "status": "PASS" if all_true(eval_checks) else "FAIL",
            "domains": sorted(expected_domains),
            "refs": [
                rel(LANE_B_ROOT / "starter_domain_pack_eval_fixtures_report.json"),
                rel(LANE_B_ROOT / "domain_packs"),
            ],
        },
        "calibration_reports_are_derived_field_and_dashboard_consumed": {
            "status": "PASS"
            if lane_c_decision.get("status", "").startswith("PASS")
            and lane_c_generation.get("status", "").startswith("PASS")
            and lane_c_generation.get("source_class") == "derived_field"
            and lane_c_generation.get("reports_generated") == 5
            and any(row.get("dashboard_cell_released") is True for row in lane_c_generation.get("reports", []))
            and all(row.get("suppressed_from_dashboard") is True or row.get("dashboard_cell_released") is True for row in lane_c_generation.get("reports", []))
            else "FAIL",
            "reports_generated": lane_c_generation.get("reports_generated"),
            "refs": [
                rel(LANE_C_ROOT / "PUSH_2_1B_LANE_C_DECISION.json"),
                rel(LANE_C_ROOT / "calibration_report_generation_report.json"),
            ],
        },
        "native_kit_ux_displays_evidence_source_check_authority_no_action_boundaries": {
            "status": "PASS"
            if lane_c_ux.get("status", "").startswith("PASS")
            and all(ux_required.get(key, {}).get("status") == "PASS" for key in ux_keys)
            and lane_c_ux.get("boundary", {}).get("no_official_action") is True
            and lane_c_ux.get("boundary", {}).get("no_live_control") is True
            and lane_c_ux.get("boundary", {}).get("no_public_api") is True
            else "FAIL",
            "audited_display_elements": ux_keys,
            "refs": [
                rel(LANE_C_ROOT / "native_kit_ux_boundary_audit.json"),
                rel(LANE_C_ROOT / "native_kit_ux_polish_report.md"),
            ],
        },
        "no_trained_model_live_source_official_action_or_agent_activation_introduced": {
            "status": "PASS"
            if all_true(
                [
                    lane_a_contract.get("no_auth_rbac_runtime_implementation"),
                    lane_a_contract.get("no_autonomous_monitoring_or_action"),
                    lane_a_contract.get("no_official_action_dispatch_enforcement_legal_ticket_case"),
                    lane_b_boundaries.get("live_source_onboarding_created") is False,
                    lane_b_boundaries.get("trained_model_created") is False,
                    lane_b_boundaries.get("ranking_prediction_or_learning_loop_created") is False,
                    lane_b_boundaries.get("domain_autonomous_agents_created") is False,
                    lane_b_boundaries.get("official_legal_or_government_conclusion_created") is False,
                    lane_c_contract.get("no_trained_model_or_learning_state"),
                    lane_c_contract.get("no_official_action_affordance"),
                    lane_c_contract.get("no_live_kit_control"),
                    lane_c_contract.get("no_public_api_or_production_auth"),
                ]
            )
            else "FAIL",
            "refs": [
                rel(LANE_A_ROOT / "PUSH_2_1B_LANE_A_DECISION.json"),
                rel(LANE_B_ROOT / "PUSH_2_1B_LANE_B_DECISION.json"),
                rel(LANE_C_ROOT / "PUSH_2_1B_LANE_C_DECISION.json"),
            ],
        },
        "corpus_appended_and_manifests_updated": {
            "status": "PASS_WITH_LIMITATION"
            if lane_b_append.get("status", "").startswith("PASS")
            and len(append_entries) == 4
            and lane_b_append.get("mutation_performed") is False
            and lane_b_append.get("frozen_upstream_outputs_mutated") is False
            else "FAIL",
            "registration_count": len(append_entries),
            "note": "Starter-pack registration rows are emitted as an append report; frozen upstream corpus/source-of-truth files are not mutated.",
            "refs": [rel(LANE_B_ROOT / "corpus_source_of_truth_append_report.json")],
        },
        "source_of_truth_matrix_current": {
            "status": "PASS_WITH_LIMITATION"
            if len(append_entries) == 4 and all(row.get("source_of_truth_append_row", {}).get("status") == "proposed_registration_only" for row in append_entries)
            else "FAIL",
            "note": "Current state is represented by no-mutation registration rows for 2.1b starter packs plus the 2.1a source-of-truth delta.",
            "refs": [
                rel(LANE_B_ROOT / "corpus_source_of_truth_append_report.json"),
                "outputs/epoch_2_1_integration_gate_2_1a_foundations/SOURCE_OF_TRUTH_MATRIX_DELTA.md",
            ],
        },
        "lane_hash_manifests_verified": {
            "status": "PASS" if all(row["status"] == "PASS" for row in lane_hashes.values()) else "FAIL",
            "lane_hashes": lane_hashes,
        },
    }


def build_outputs() -> dict[str, Any]:
    prepare_output_root()

    inputs = {
        "lane_a_decision": read_json(LANE_A_ROOT / "PUSH_2_1B_LANE_A_DECISION.json", {}),
        "lane_a_validation": read_json(LANE_A_ROOT / "rbac_audit_validation_report.json", {}),
        "lane_a_rbac": read_json(LANE_A_ROOT / "rbac_policy_matrix_v1.json", {}),
        "lane_a_observability": read_json(LANE_A_ROOT / "observability_envelope_v1.json", {}),
        "lane_b_decision": read_json(LANE_B_ROOT / "PUSH_2_1B_LANE_B_DECISION.json", {}),
        "lane_b_validation": read_json(LANE_B_ROOT / "starter_domain_pack_validation_report.json", {}),
        "lane_b_eval": read_json(LANE_B_ROOT / "starter_domain_pack_eval_fixtures_report.json", {}),
        "lane_b_append": read_json(LANE_B_ROOT / "corpus_source_of_truth_append_report.json", {}),
        "lane_c_decision": read_json(LANE_C_ROOT / "PUSH_2_1B_LANE_C_DECISION.json", {}),
        "lane_c_generation": read_json(LANE_C_ROOT / "calibration_report_generation_report.json", {}),
        "lane_c_ux": read_json(LANE_C_ROOT / "native_kit_ux_boundary_audit.json", {}),
    }
    lane_hashes = {
        "lane_a": verify_lane_hash_manifest(LANE_A_ROOT),
        "lane_b": verify_lane_hash_manifest(LANE_B_ROOT),
        "lane_c": verify_lane_hash_manifest(LANE_C_ROOT),
    }
    checks = build_checks(inputs, lane_hashes)
    failed = {name: row for name, row in checks.items() if not row["status"].startswith("PASS")}
    allowed = not failed and current_branch() == "main"
    decision_status = PASS_STATUS if allowed else BLOCK_STATUS

    convergence = {
        "schema_version": "citybrain.epoch_2_1.integration_gate_2_1b.content_hardening_convergence.v1",
        "status": "PASS" if allowed else "FAIL",
        "created_at": utc_now(),
        "lane_inputs": {
            "lane_a": rel(LANE_A_ROOT),
            "lane_b": rel(LANE_B_ROOT),
            "lane_c": rel(LANE_C_ROOT),
        },
        "gate_checks": checks,
        "content_hardening_summary": {
            "roles": inputs["lane_a_decision"].get("counts", {}).get("roles"),
            "audit_event_types": inputs["lane_a_decision"].get("counts", {}).get("audit_event_types"),
            "starter_pack_count": inputs["lane_b_decision"].get("starter_pack_count"),
            "starter_domains": inputs["lane_b_decision"].get("starter_domains", []),
            "calibration_reports_generated": inputs["lane_c_generation"].get("reports_generated"),
            "kit_review_items_audited": inputs["lane_c_ux"].get("review_items_seen"),
        },
    }
    write_json(OUTPUT_ROOT / "CONTENT_HARDENING_CONVERGENCE_REPORT.json", convergence)

    corpus_report = {
        "schema_version": "citybrain.epoch_2_1.integration_gate_2_1b.corpus_append_report.v1",
        "status": checks["corpus_appended_and_manifests_updated"]["status"],
        "created_at": utc_now(),
        "append_performed": False,
        "frozen_upstream_outputs_mutated": False,
        "registration_count": checks["corpus_appended_and_manifests_updated"]["registration_count"],
        "source_ref": rel(LANE_B_ROOT / "corpus_source_of_truth_append_report.json"),
        "note": checks["corpus_appended_and_manifests_updated"]["note"],
    }
    write_json(OUTPUT_ROOT / "CORPUS_APPEND_REPORT.json", corpus_report)
    write_text(
        OUTPUT_ROOT / "SOURCE_OF_TRUTH_MATRIX_DELTA.md",
        "# Source Of Truth Matrix Delta\n\n"
        "Status: `PASS_WITH_LIMITATION`\n\n"
        "- Push 2.1b adds four starter domain-pack registration rows as no-mutation append evidence.\n"
        "- Frozen upstream source-of-truth matrices and corpus outputs are not modified by this gate.\n"
        "- Push 2.1c may consume these rows as current local/replay registration evidence.\n",
    )

    decision = {
        "schema_version": "citybrain.epoch_2_1.integration_gate_2_1b.decision.v1",
        "status": decision_status,
        "created_at": utc_now(),
        "branch": current_branch(),
        "push_2_1c_allowed_to_open": allowed,
        "required_inputs": {
            "lane_a": rel(LANE_A_ROOT),
            "lane_b": rel(LANE_B_ROOT),
            "lane_c": rel(LANE_C_ROOT),
        },
        "gate_checks": checks,
        "failed_checks": failed,
        "limitations": [
            "Corpus/source-of-truth updates are represented as no-mutation append reports, not writes into frozen upstream outputs.",
            "Calibration report dashboard consumption suppresses small WatchItem disposition cells under the aggregation floor.",
            "Native Kit UX work is a local boundary audit and polish report, not live control or production surface activation.",
            "RBAC/audit/observability remains policy/config and fixture validation only, not production IAM.",
        ],
        "non_goals_preserved": [
            "No trained model, ranking, prediction, cross-city learned transfer, or learning loop.",
            "No live source onboarding implementation.",
            "No production/public API exposure.",
            "No autonomous monitoring/action, official action, dispatch, enforcement, legal finding, ticket, or case creation.",
            "No agent activation.",
        ],
    }
    write_json(OUTPUT_ROOT / "INTEGRATION_GATE_2_1B_DECISION.json", decision)
    write_text(
        OUTPUT_ROOT / "INTEGRATION_GATE_2_1B_SUMMARY.md",
        "# Integration Gate 2.1b Summary\n\n"
        f"Status: `{decision_status}`\n\n"
        "- RBAC/audit baseline exists and fixture validation passed.\n"
        "- Four starter domain packs pass the domain-pack validator and include consuming capabilities plus eval fixtures.\n"
        "- CalibrationReports v1 are derived_field descriptive statistics with dashboard consumption and aggregation-floor suppression.\n"
        "- Native Kit UX boundary audit displays evidence/source/CHECK/authority/no-action boundaries.\n"
        "- Push 2.1c may open if the flag is `PASS`.\n",
    )
    write_text(
        OUTPUT_ROOT / "FINAL_OR_NEXT_BLOCKERS.md",
        "# Final Or Next Blockers\n\n"
        + ("No blocking issues for Push 2.1c opening.\n" if allowed else "\n".join(f"- `{name}`" for name in failed)),
    )
    write_text(OUTPUT_ROOT / "PUSH_2_1C_ALLOWED_TO_OPEN.flag", "PASS\n" if allowed else "BLOCKED\n")
    manifest = write_hash_manifest()
    return {"decision": decision, "content_hardening_convergence": convergence, "hash_manifest": manifest}


def write_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.epoch_2_1.integration_gate_2_1b.hash_manifest.v1",
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
    return 0 if result["decision"]["push_2_1c_allowed_to_open"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
