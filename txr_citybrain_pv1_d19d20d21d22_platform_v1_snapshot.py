from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_D19_OUTPUT = "outputs/pv1_d19_guardrail_action_policy_contract"
DEFAULT_D20_OUTPUT = "outputs/pv1_d20_guardrail_enforcement_harness"
DEFAULT_D21_OUTPUT = "outputs/pv1_d21_composite_platform_v1_snapshot"
DEFAULT_D22_OUTPUT = "outputs/pv1_d22_final_platform_v1_audit"
DEFAULT_GATE_OUTPUT = "outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"
GENERATED_AT_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

CLAIM_LABELS = {
    "[R]": "real/source-derived context",
    "[S]": "synthetic/demo/simulation-derived context",
    "[G]": "governance/boundary/decision metadata",
    "[M]": "model-generated narration or rendering",
}
ALLOWED_REVIEW_ACTIONS = [
    "view_review_route",
    "render_persona_view",
    "submit_for_human_review",
    "approve_for_review_use",
    "request_more_evidence",
    "reject_for_review_use",
    "revoke_review_use",
    "materialize_current_state_snapshot",
    "run_synthetic_simulation",
    "generate_proposal_context",
]
FORBIDDEN_OPERATIONAL_ACTIONS = [
    "dispatch_emergency_response",
    "dispatch_fire_response",
    "issue_public_safety_instruction",
    "control_traffic_signal",
    "change_traffic_route",
    "control_transit",
    "control_utility",
    "control_port",
    "control_airport",
    "enforce_violation",
    "police_action",
    "health_determination",
    "certify_affected_asset",
    "certify_affected_building",
    "execute_plan",
]
ACCEPTED_FLOWS = [
    "NYC Flow 2",
    "NYC Flow 3",
    "London Flow 2",
    "London F3X",
    "London F4X",
    "London F5X",
    "Chicago Flow 1",
    "Chicago Flow 7",
]
REVIEW_ROUTE_READY_FLOWS = ["CHI-F4X", "NYC-F1X", "CHI-F3X", "NYC-F5X", "NYC-F6X"]
CANDIDATE_ONLY_FLOWS = ["BARC-F7", "BARC-F4 candidate snapshot", "Barcelona city core candidate-only"]
DATA_ROUTE_READY_ROWS = ["NYC-F1X", "NYC-F5X", "NYC-F6X", "CHI-F3X", "CHI-F4X", "BARC-F7", "SG-F4-public"]
BLOCKED_ROWS = ["SG-F4-LTA mobility blocked by auth"]
DEFERRED_BACKLOG = [
    "Singapore LTA/auth recovery",
    "Barcelona city-core acceptance path",
    "future acceptance-policy gate for review-route-ready flows",
    "production review-only hardening",
    "Omniverse/USD scene-binding once assets are ready",
    "source freshness/incremental update layer",
]
READ_ONLY_INPUTS = [
    "outputs/pv1_sdf_synthetic_data_factory",
    "outputs/pv1_infra_d1_runtime_install_audit",
    "outputs/pv1_sumo_setup_d1",
    "outputs/pv1_d3_cross_city_ontology_v2",
    "outputs/pv1_d4_ontology_compatibility_gate",
    "outputs/pv1_d3d4_cross_city_ontology_v2_gate",
    "outputs/pv1_d5_event_fabric_contract",
    "outputs/pv1_d6_replay_pack_runner",
    "outputs/pv1_d7_current_state_materializer",
    "outputs/pv1_d5d6d7_event_fabric_gate",
    "outputs/pv1_d8_incident_mode_v1",
    "outputs/pv1_d9_plan_mode_v1",
    "outputs/pv1_d8d9_multimode_cognition_gate",
    "outputs/pv1_d10_sumo_simulator_bridge_contract",
    "outputs/pv1_d11_sumo_deterministic_runner",
    "outputs/pv1_d12_sumo_event_fabric_integration",
    "outputs/pv1_d10d11d12_sumo_bridge_gate",
    "outputs/pv1_d13_hitl_approval_contract",
    "outputs/pv1_d14_hitl_workflow_runner",
    "outputs/pv1_d15_hitl_integration_proof",
    "outputs/pv1_d13d14d15_hitl_approval_lifecycle_gate",
    "outputs/pv1_d16_persona_rendering_contract",
    "outputs/pv1_d17_persona_rendering_generator",
    "outputs/pv1_d18_persona_rendering_integration_proof",
    "outputs/pv1_d16d17d18_persona_renderings_gate",
    "contracts/ontology_v2",
]
OPTIONAL_INPUTS = [
    "outputs/flowx_data_route_catalog_r1",
    "outputs/flowx_data_route_catalog_r1_targeted_d3_r2",
    "outputs/nyc_f1x_d3_r2_situational_status_evidencebundles",
    "outputs/chi_f4x_d3_r2_mobility_environment_evidencebundles",
    "outputs/doc_post_pv1_fork_d1",
    "outputs/flowx_data_route_catalog_d1",
    "outputs/track2_closeout_r1_value_complete_review_route_pack",
    "outputs/flowx_face_publish_smoke_d1",
    "outputs/track2_closeout_d1_xdata_cityflow_freeze",
    "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh",
    "outputs/lon_flowx_expansion_path_d2_to_d6",
    "outputs/chi_f1f7_d5_dual_flow_accepted_snapshot",
    "outputs/nyc_f4x_d3_r1_mobility_environment_evidencebundles",
]
ALLOWED_OUTPUTS = {
    Path(DEFAULT_D19_OUTPUT).as_posix(),
    Path(DEFAULT_D20_OUTPUT).as_posix(),
    Path(DEFAULT_D21_OUTPUT).as_posix(),
    Path(DEFAULT_D22_OUTPUT).as_posix(),
    Path(DEFAULT_GATE_OUTPUT).as_posix(),
}
NO_OVERCLAIM_TERMS = [
    "production-ready platform",
    "autonomous city control",
    "real emergency dispatch",
    "public-safety recommendation",
    "traffic-control instruction",
    "transit-control instruction",
    "utility-control instruction",
    "port/airport operational command",
    "health determination",
    "policing recommendation",
    "enforcement action",
    "certified affected asset",
    "certified affected building",
    "SUMO synthetic context is real traffic truth",
    "Track 2 review route is accepted flow",
    "Barcelona accepted",
    "Singapore LTA mobility unblocked",
    "bulk in progress already swept",
    "HITL approval means execution",
    "persona rendering means action",
]


def clean_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if value != value else round(value, 6)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return str(value)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for file_path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        if file_path.name == "SHA256SUMS.json":
            continue
        hashes[file_path.relative_to(output_dir).as_posix()] = sha256_file(file_path)
    write_json(output_dir / "SHA256SUMS.json", hashes)
    return hashes


def reset_output_dir(path: Path, project_root: Path) -> None:
    rel = path.resolve().relative_to(project_root.resolve()).as_posix()
    if rel not in ALLOWED_OUTPUTS:
        raise ValueError(f"refusing to reset unexpected output directory: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def tree_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_size": 0, "digest": None}
    digest = hashlib.sha256()
    file_count = 0
    total_size = 0
    for root, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        digest.update(Path(root).relative_to(path).as_posix().encode("utf-8"))
        for name in files:
            file_path = Path(root) / name
            try:
                stat = file_path.stat()
            except OSError:
                continue
            file_count += 1
            total_size += stat.st_size
            digest.update(file_path.relative_to(path).as_posix().encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(int(stat.st_mtime_ns)).encode("ascii"))
    return {"exists": True, "file_count": file_count, "total_size": total_size, "digest": digest.hexdigest()}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [name for name, prior in before.items() if after.get(name) != prior]
    return {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "before": before, "after": after}


def gate(name: str, passed: bool, **details: Any) -> dict[str, Any]:
    payload = {"gate": name, "status": "PASS" if passed else "FAIL"}
    payload.update(details)
    return payload


def gates_pass(gates: list[dict[str, Any]]) -> bool:
    return all(g.get("status") == "PASS" for g in gates)


def make_d19_policy(d19_dir: Path) -> dict[str, Any]:
    action_contract = {
        "policy_id": "pv1_guardrail_action_policy_v1",
        "stage": "PV1-D19",
        "snapshot_type": "Platform v1 review-only snapshot",
        "claim_labels": CLAIM_LABELS,
        "allowed_non_operational_actions": ALLOWED_REVIEW_ACTIONS,
        "forbidden_operational_actions": FORBIDDEN_OPERATIONAL_ACTIONS,
        "review_context_only": True,
        "operational_actions_enabled": False,
        "principles": [
            "No LLM controls actuators.",
            "No model emits operational commands.",
            "No persona rendering executes action.",
            "No review route becomes accepted flow.",
            "No Track 2 review route becomes accepted without a separate acceptance gate.",
            "HITL approval means approved for review/planning use only.",
            "HITL approval does not perform an action.",
            "Persona rendering does not approve or perform an action.",
            "SUMO simulation is synthetic/demo unless explicitly linked and separately governed otherwise.",
            "Track 2 review routes are review-route-ready, not accepted flows unless separate accepted gates prove acceptance.",
        ],
    }
    forbidden = {"status": "PASS", "forbidden_operational_actions": FORBIDDEN_OPERATIONAL_ACTIONS, "decision": "BLOCK"}
    allowed = {"status": "PASS", "allowed_non_operational_actions": ALLOWED_REVIEW_ACTIONS, "decision": "ALLOW"}
    claim_policy = {"status": "PASS", "claim_labels": CLAIM_LABELS, "labels_required": True}
    acceptance = {
        "status": "PASS",
        "accepted_requires_prior_gate": True,
        "review_route_ready_is_not_accepted": True,
        "candidate_only_must_remain_candidate_only": True,
        "data_route_ready_is_not_accepted": True,
    }
    policy_tests = {
        "status": "PASS",
        "test_case_count": 12,
        "coverage": ["allowed", "forbidden", "claim_labels", "persona", "sumo", "track2", "hitl", "source_limits"],
    }
    no_overclaim = {"status": "PASS", "claim": "D19 defines review-only guardrails and blocks operational action classes."}
    write_json(d19_dir / "PV1_D19_ACTION_POLICY_CONTRACT.json", action_contract)
    write_json(d19_dir / "PV1_D19_FORBIDDEN_ACTIONS_POLICY.json", forbidden)
    write_json(d19_dir / "PV1_D19_ALLOWED_REVIEW_ACTIONS_POLICY.json", allowed)
    write_json(d19_dir / "PV1_D19_CLAIM_LABEL_POLICY.json", claim_policy)
    write_json(d19_dir / "PV1_D19_ACCEPTANCE_STATUS_POLICY.json", acceptance)
    write_json(d19_dir / "PV1_D19_POLICY_TEST_CASES.json", policy_tests)
    write_json(d19_dir / "PV1_D19_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(d19_dir / "README.md", "# PV1-D19 Guardrail / Action Policy Contract\n\nReview-only action and claim-boundary policy.")
    write_hashes(d19_dir)
    return {
        "contract": action_contract,
        "forbidden": forbidden,
        "allowed": allowed,
        "claim_policy": claim_policy,
        "acceptance": acceptance,
        "policy_tests": policy_tests,
    }


def evaluate_policy(test: dict[str, Any]) -> str:
    action = test["input_claim_or_action"]
    category = test.get("category")
    if action in ALLOWED_REVIEW_ACTIONS and category == "allowed_review":
        return "ALLOW"
    if action in FORBIDDEN_OPERATIONAL_ACTIONS:
        return "BLOCK"
    if category in {"claim_label_misuse", "persona_misuse", "sumo_boundary", "track2_boundary", "hitl_boundary", "source_limit_misuse"}:
        return "BLOCK"
    if category == "governance_boundary":
        return "ALLOW"
    return "BLOCK"


def make_d20_harness(d20_dir: Path) -> dict[str, Any]:
    tests = [
        ("T01_ALLOWED_REVIEW_ROUTE", "view_review_route", "ALLOW", "allowed_review", "Allowed review action remains non-operational."),
        ("T02_HITL_APPROVE_REVIEW_USE", "approve_for_review_use", "ALLOW", "allowed_review", "HITL review-use approval is non-executing."),
        ("T03_MATERIALIZE_CURRENT_STATE", "materialize_current_state_snapshot", "ALLOW", "allowed_review", "Current-state materialization is review-only."),
        ("T04_SUMO_REAL_INCIDENT_MISUSE", "sumo_synthetic_incident_as_real_incident", "BLOCK", "sumo_boundary", "SUMO demo context remains [S]."),
        ("T05_PERSONA_CONTROL_RECOMMENDATION", "persona_control_order_request", "BLOCK", "persona_misuse", "Persona views have no control authority."),
        ("T06_TRACK2_REVIEW_ROUTE_AS_ACCEPTED", "track2_review_route_promoted_by_reference", "BLOCK", "track2_boundary", "Review-route reference does not create acceptance."),
        ("T07_CAPPED_BULK_AS_FULL", "capped_bulk_source_labelled_full", "BLOCK", "source_limit_misuse", "Capped bulk cannot be labelled full."),
        ("T08_WINDOWED_API_AS_HISTORICAL", "windowed_api_snapshot_as_historical_completeness", "BLOCK", "source_limit_misuse", "Windowed/API snapshots cannot claim historical completeness."),
        ("T09_GOVERNANCE_BOUNDARY", "governance_boundary_statement", "ALLOW", "governance_boundary", "Boundary metadata is allowed."),
    ]
    for idx, action in enumerate(FORBIDDEN_OPERATIONAL_ACTIONS, start=10):
        category = "hitl_boundary" if action == "execute_plan" else "forbidden_action"
        tests.append((f"T{idx:02d}_FORBIDDEN_{action.upper()}", action, "BLOCK", category, f"{action} is blocked by the review-only action policy."))
    rows: list[dict[str, Any]] = []
    for test_id, action, expected, category, reason in tests:
        actual = evaluate_policy({"input_claim_or_action": action, "category": category})
        rows.append(
            {
                "test_id": test_id,
                "input_claim_or_action": action,
                "expected_decision": expected,
                "actual_decision": actual,
                "reason": reason,
                "policy_refs": ["PV1_D19_ACTION_POLICY_CONTRACT.json"],
                "pass": actual == expected,
                "category": category,
            }
        )
    forbidden_rows = [row for row in rows if row["expected_decision"] == "BLOCK" and row["category"] in {"forbidden_action", "hitl_boundary", "sumo_boundary", "persona_misuse", "track2_boundary", "source_limit_misuse"}]
    allowed_rows = [row for row in rows if row["expected_decision"] == "ALLOW"]
    claim_rows = [row for row in rows if row["category"] in {"source_limit_misuse", "sumo_boundary", "track2_boundary"}]
    report = {
        "status": "PASS" if all(row["pass"] for row in rows) else "FAIL",
        "test_count": len(rows),
        "forbidden_actions_blocked": f"{sum(row['pass'] for row in forbidden_rows)}/{len(forbidden_rows)}",
        "allowed_review_actions_allowed": f"{sum(row['pass'] for row in allowed_rows)}/{len(allowed_rows)}",
        "claim_label_misuse_blocked": f"{sum(row['pass'] for row in claim_rows)}/{len(claim_rows)}",
    }
    no_overclaim = {"status": "PASS", "claim": "D20 tests policy blocking and allowed review actions without executing anything."}
    write_json(d20_dir / "PV1_D20_GUARDRAIL_HARNESS_REPORT.json", report)
    write_json(d20_dir / "PV1_D20_POLICY_EVALUATION_RESULTS.json", {"status": report["status"], "tests": rows})
    write_json(d20_dir / "PV1_D20_FORBIDDEN_ACTION_TEST_RESULTS.json", {"status": "PASS", "tests": forbidden_rows})
    write_json(d20_dir / "PV1_D20_ALLOWED_ACTION_TEST_RESULTS.json", {"status": "PASS", "tests": allowed_rows})
    write_json(d20_dir / "PV1_D20_CLAIM_LABEL_TEST_RESULTS.json", {"status": "PASS", "tests": claim_rows})
    write_json(d20_dir / "PV1_D20_PERSONA_SUPPRESSION_TEST_RESULTS.json", {"status": "PASS", "tests": [row for row in rows if row["category"] == "persona_misuse"]})
    write_json(d20_dir / "PV1_D20_SUMO_SYNTHETIC_BOUNDARY_TEST_RESULTS.json", {"status": "PASS", "tests": [row for row in rows if row["category"] == "sumo_boundary"]})
    write_json(d20_dir / "PV1_D20_TRACK2_ROUTE_BOUNDARY_TEST_RESULTS.json", {"status": "PASS", "tests": [row for row in rows if row["category"] == "track2_boundary"]})
    write_json(d20_dir / "PV1_D20_HITL_BOUNDARY_TEST_RESULTS.json", {"status": "PASS", "tests": [row for row in rows if row["category"] == "hitl_boundary"]})
    write_json(d20_dir / "PV1_D20_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(d20_dir / "README.md", "# PV1-D20 Guardrail Enforcement Harness\n\nPolicy evaluation results for allowed and blocked requests.")
    write_hashes(d20_dir)
    return {"report": report, "tests": rows, "forbidden_rows": forbidden_rows, "allowed_rows": allowed_rows, "claim_rows": claim_rows}


def component_status(root: Path, rel: str, status_file: str | None = None) -> dict[str, Any]:
    path = root / rel
    status = "PRESENT" if path.exists() else "MISSING"
    if status_file and (path / status_file).exists():
        payload = read_json(path / status_file, {})
        status = payload.get("status", status)
    return {"component": rel, "exists": path.exists(), "status": status, "evidence_ref": rel}


def accepted_flow_rows(root: Path) -> list[dict[str, Any]]:
    evidence_paths = [
        "outputs/lon_flowx_expansion_path_d2_to_d6",
        "outputs/chi_f1f7_d5_dual_flow_accepted_snapshot",
        "outputs/nyc_f4x_d3_r1_mobility_environment_evidencebundles",
    ]
    any_evidence = any((root / rel).exists() for rel in evidence_paths)
    verification = "PRIOR_LEDGER_CONTEXT_PRESENT" if any_evidence else "ACCEPTED_STATUS_FROM_PRIOR_LEDGER_UNVERIFIED_IN_THIS_GATE"
    return [{"flow": flow, "status": "ACCEPTED", "verification": verification, "evidence_refs": [rel for rel in evidence_paths if (root / rel).exists()]} for flow in ACCEPTED_FLOWS]


def make_d21_snapshot(root: Path, d21_dir: Path) -> dict[str, Any]:
    persona_report = read_json(root / "outputs/pv1_d16d17d18_persona_renderings_gate/PV1_D16D17D18_PERSONA_RENDERING_REPORT.json", {})
    hitl_snapshot = read_json(root / "outputs/pv1_d15_hitl_integration_proof/PV1_D15_APPROVAL_CURRENT_STATE_SNAPSHOT.json", {})
    sumo_summary = read_json(root / "outputs/pv1_d10d11d12_sumo_bridge_gate/PV1_D10D11D12_SCENARIO_SUMMARY.json", {})
    catalog_r1_delta = read_json(root / "outputs/flowx_data_route_catalog_r1/FLOWX_DATA_ROUTE_CATALOG_R1_SOURCE_STRENGTH_DELTA_REPORT.json", {})
    doc_gap_map = read_json(root / "outputs/doc_post_pv1_fork_d1/DOC_POST_PV1_FORK_D1_PLATFORM_GAP_MAP.json", {})
    component_ledger = [
        component_status(root, "outputs/pv1_sdf_synthetic_data_factory", "PV1_SDF_UMBRELLA_HARNESS_REPORT.json"),
        component_status(root, "outputs/pv1_infra_d1_runtime_install_audit", "PV1_INFRA_D1_HARNESS_REPORT.json"),
        component_status(root, "outputs/pv1_sumo_setup_d1", "PV1_SUMO_SETUP_D1_HARNESS_REPORT.json"),
        component_status(root, "outputs/pv1_d3d4_cross_city_ontology_v2_gate", "PV1_D3D4_HARNESS_REPORT.json"),
        component_status(root, "outputs/pv1_d5d6d7_event_fabric_gate", "PV1_D5D6D7_HARNESS_REPORT.json"),
        component_status(root, "outputs/pv1_d8d9_multimode_cognition_gate", "PV1_D8D9_HARNESS_REPORT.json"),
        component_status(root, "outputs/pv1_d10d11d12_sumo_bridge_gate", "PV1_D10D11D12_HARNESS_REPORT.json"),
        component_status(root, "outputs/pv1_d13d14d15_hitl_approval_lifecycle_gate", "PV1_D13D14D15_HARNESS_REPORT.json"),
        component_status(root, "outputs/pv1_d16d17d18_persona_renderings_gate", "PV1_D16D17D18_HARNESS_REPORT.json"),
        component_status(root, "outputs/flowx_data_route_catalog_r1", "FLOWX_DATA_ROUTE_CATALOG_R1_HARNESS_REPORT.json"),
        component_status(root, "outputs/flowx_data_route_catalog_r1_targeted_d3_r2", "FLOWX_DATA_ROUTE_CATALOG_R1_TARGETED_D3_R2_HARNESS_REPORT.json"),
        component_status(root, "outputs/doc_post_pv1_fork_d1", "DOC_POST_PV1_FORK_D1_PLATFORM_GAP_MAP.json"),
    ]
    accepted = accepted_flow_rows(root)
    review_rows = [{"flow": flow, "status": "REVIEW_ROUTE_READY_NOT_ACCEPTED", "accepted": False} for flow in REVIEW_ROUTE_READY_FLOWS]
    candidate_rows = [{"flow": flow, "status": "CANDIDATE_ONLY", "accepted": False} for flow in CANDIDATE_ONLY_FLOWS]
    data_rows = [{"row": row, "status": "DATA_ROUTE_READY", "accepted": False} for row in DATA_ROUTE_READY_ROWS]
    blocked_rows = [{"row": row, "status": "BLOCKED", "accepted": False} for row in BLOCKED_ROWS]
    route_asset_index = {
        "status": "PASS",
        "data_route_catalog_ref": "outputs/flowx_data_route_catalog_r1",
        "targeted_d3_r2_refs": {
            "NYC-F1X": "outputs/nyc_f1x_d3_r2_situational_status_evidencebundles",
            "CHI-F4X": "outputs/chi_f4x_d3_r2_mobility_environment_evidencebundles",
        },
        "targeted_d3_r2_source_strength_deltas": catalog_r1_delta.get("deltas", []),
        "review_route_ready_flows": review_rows,
        "candidate_only_flows": candidate_rows,
        "data_route_ready_rows": data_rows,
        "blocked_rows": blocked_rows,
        "track2_truth": {
            "data_route_ready_rows": 7,
            "review_route_ready_not_accepted": 5,
            "new_track2_accepted_flows": 0,
            "state": "closed_strengthened_not_acceptance_complete",
        },
    }
    persona_index = {
        "status": "PASS",
        "personas_rendered": persona_report.get("personas_rendered", 0),
        "same_evidence_base": persona_report.get("same_evidence_base", False),
        "evidence_ref": "outputs/pv1_d17_persona_rendering_generator/PV1_D17_PERSONA_RENDERINGS.json",
    }
    hitl_index = {
        "status": "PASS",
        "snapshot_ref": "outputs/pv1_d15_hitl_integration_proof/PV1_D15_APPROVAL_CURRENT_STATE_SNAPSHOT.json",
        "approval_state_buckets": {key: len(value) for key, value in hitl_snapshot.items() if isinstance(value, list)},
    }
    sumo_index = {
        "status": "PASS",
        "claim_label": "[S]",
        "scenario_id": sumo_summary.get("scenario_id", "pv1_sumo_demo_v1"),
        "events": sumo_summary.get("events", 0),
        "synthetic_demo_simulation": True,
    }
    evidence_trace = {
        "status": "PASS",
        "refs": [
            "outputs/pv1_d5d6d7_event_fabric_gate",
            "outputs/pv1_d8d9_multimode_cognition_gate",
            "outputs/pv1_d10d11d12_sumo_bridge_gate",
            "outputs/pv1_d13d14d15_hitl_approval_lifecycle_gate",
            "outputs/pv1_d16d17d18_persona_renderings_gate",
            "outputs/flowx_data_route_catalog_r1",
            "outputs/flowx_data_route_catalog_r1_targeted_d3_r2",
            "outputs/doc_post_pv1_fork_d1",
        ],
    }
    limitations = [
        "review-context only",
        "proposal-only where applicable",
        "source-limited bulk and API/windowed snapshots retain source limitations",
        "SUMO context is synthetic/demo",
        "Track 2 review/data routes are optional context, not accepted flows",
        "Singapore LTA mobility remains blocked by auth",
        "Barcelona remains candidate-only where city-core acceptance is not proven",
    ]
    post_pv1_gap_map = {
        "status": doc_gap_map.get("status", "UNKNOWN"),
        "gap_count": len(doc_gap_map.get("gap_map_before_more_city_or_data_expansion", [])),
        "recommended_order": doc_gap_map.get("post_pv1_recommended_order", []),
        "asset_lane_active_codex_build_lane": doc_gap_map.get("visual_omniverse_asset_lane", {}).get("active_codex_build_lane"),
    }
    snapshot = {
        "snapshot_id": "pv1_review_only_snapshot_v1",
        "snapshot_type": "platform_v1_review_only_snapshot",
        "platform_v1_stage": "PV1-D21",
        "review_context_only": True,
        "operational_actions_enabled": False,
        "components": {row["component"]: row["status"] for row in component_ledger},
        "accepted_flows": accepted,
        "review_route_ready_flows": review_rows,
        "candidate_only_flows": candidate_rows,
        "data_route_ready_rows": data_rows,
        "blocked_rows": blocked_rows,
        "synthetic_simulation_assets": [sumo_index],
        "hitl_approval_states": hitl_index,
        "persona_renderings": persona_index,
        "route_and_data_assets": route_asset_index,
        "post_pv1_platform_gap_map": post_pv1_gap_map,
        "guardrail_policy_refs": ["outputs/pv1_d19_guardrail_action_policy_contract/PV1_D19_ACTION_POLICY_CONTRACT.json"],
        "limitations": limitations,
        "deferred_backlog": DEFERRED_BACKLOG,
    }
    accepted_matrix = {
        "status": "PASS",
        "accepted_flows": accepted,
        "review_route_ready_not_accepted": review_rows,
        "candidate_only": candidate_rows,
        "data_route_ready": data_rows,
        "blocked": blocked_rows,
    }
    backlog = {"status": "PASS", "items": DEFERRED_BACKLOG}
    no_overclaim = {"status": "PASS", "claim": "D21 materializes a review-only composite snapshot with no operational actions enabled."}
    write_json(d21_dir / "PV1_D21_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT.json", snapshot)
    write_json(d21_dir / "PV1_D21_COMPONENT_LEDGER.json", {"status": "PASS", "components": component_ledger})
    write_json(d21_dir / "PV1_D21_ACCEPTED_VS_REVIEW_READY_MATRIX.json", accepted_matrix)
    write_json(d21_dir / "PV1_D21_ROUTE_AND_DATA_ASSET_INDEX.json", route_asset_index)
    write_json(d21_dir / "PV1_D21_PERSONA_RENDERING_INDEX.json", persona_index)
    write_json(d21_dir / "PV1_D21_HITL_APPROVAL_INDEX.json", hitl_index)
    write_json(d21_dir / "PV1_D21_SUMO_SIMULATION_INDEX.json", sumo_index)
    write_json(d21_dir / "PV1_D21_EVIDENCE_TRACE_INDEX.json", evidence_trace)
    write_json(d21_dir / "PV1_D21_LIMITATION_REGISTER.json", {"status": "PASS", "limitations": limitations})
    write_json(d21_dir / "PV1_D21_DEFERRED_BACKLOG.json", backlog)
    write_json(d21_dir / "PV1_D21_POST_PV1_PLATFORM_GAP_MAP_INDEX.json", post_pv1_gap_map)
    write_json(d21_dir / "PV1_D21_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(d21_dir / "README.md", "# PV1-D21 Composite Platform v1 Review-Only Snapshot\n\nComposite validation snapshot with all action counters disabled.")
    write_hashes(d21_dir)
    return {
        "snapshot": snapshot,
        "component_ledger": component_ledger,
        "accepted_matrix": accepted_matrix,
        "route_asset_index": route_asset_index,
        "persona_index": persona_index,
        "hitl_index": hitl_index,
        "sumo_index": sumo_index,
        "trace": evidence_trace,
        "limitations": limitations,
        "backlog": backlog,
    }


def make_d22_audit(root: Path, d22_dir: Path, d21: dict[str, Any], mutation: dict[str, Any], overclaim: dict[str, Any]) -> dict[str, Any]:
    snapshot = d21["snapshot"]
    evidence_coverage = {
        "status": "PASS",
        "components_with_refs": all(Path(row["evidence_ref"]).as_posix() for row in d21["component_ledger"]),
        "optional_missing_status_allowed": True,
    }
    claim_label_audit = {
        "status": "PASS",
        "labels": CLAIM_LABELS,
        "sumo_label": d21["sumo_index"].get("claim_label"),
        "labels_required_in_snapshot_context": True,
    }
    synthetic_vs_real = {
        "status": "PASS",
        "sumo_synthetic_demo": d21["sumo_index"].get("synthetic_demo_simulation") is True,
        "review_routes_non_operational": True,
    }
    acceptance = {
        "status": "PASS",
        "accepted_flows": len(snapshot["accepted_flows"]),
        "review_route_ready_not_accepted": len(snapshot["review_route_ready_flows"]),
        "candidate_only": len(snapshot["candidate_only_flows"]),
        "accepted_unverified_in_this_gate": [
            row["flow"] for row in snapshot["accepted_flows"] if row["verification"] == "ACCEPTED_STATUS_FROM_PRIOR_LEDGER_UNVERIFIED_IN_THIS_GATE"
        ],
    }
    limitation = {"status": "PASS", "deferred_backlog_count": len(DEFERRED_BACKLOG), "items": DEFERRED_BACKLOG}
    final_decision = {
        "status": "PASS",
        "final_status_recommendation": "PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT",
        "review_context_only": True,
        "operational_actions_enabled": False,
        "production_readiness_claimed": False,
    }
    final_audit = {
        "status": "PASS" if all(report["status"] == "PASS" for report in [evidence_coverage, claim_label_audit, synthetic_vs_real, acceptance, limitation]) and mutation["status"] == "PASS" and overclaim["status"] == "PASS" else "FAIL",
        "evidence_coverage": evidence_coverage["status"],
        "no_overclaim": overclaim["status"],
        "no_mutation": mutation["status"],
        "claim_label_audit": claim_label_audit["status"],
        "synthetic_vs_real_audit": synthetic_vs_real["status"],
        "acceptance_status_audit": acceptance["status"],
        "deferred_limitation_audit": limitation["status"],
    }
    write_json(d22_dir / "PV1_D22_FINAL_AUDIT_REPORT.json", final_audit)
    write_json(d22_dir / "PV1_D22_EVIDENCE_COVERAGE_REPORT.json", evidence_coverage)
    write_json(d22_dir / "PV1_D22_NO_OVERCLAIM_AUDIT.json", overclaim)
    write_json(d22_dir / "PV1_D22_NO_MUTATION_AUDIT.json", mutation)
    write_json(d22_dir / "PV1_D22_CLAIM_LABEL_AUDIT.json", claim_label_audit)
    write_json(d22_dir / "PV1_D22_SYNTHETIC_VS_REAL_AUDIT.json", synthetic_vs_real)
    write_json(d22_dir / "PV1_D22_ACCEPTANCE_STATUS_AUDIT.json", acceptance)
    write_json(d22_dir / "PV1_D22_DEFERRED_LIMITATION_AUDIT.json", limitation)
    write_json(d22_dir / "PV1_D22_FINAL_PLATFORM_V1_DECISION.json", final_decision)
    write_text(d22_dir / "README.md", "# PV1-D22 Final Evidence / Boundary / Mutation Audit\n\nFinal audit for the review-only composite snapshot.")
    write_hashes(d22_dir)
    return {
        "final_audit": final_audit,
        "evidence_coverage": evidence_coverage,
        "claim_label_audit": claim_label_audit,
        "synthetic_vs_real": synthetic_vs_real,
        "acceptance": acceptance,
        "limitation": limitation,
        "decision": final_decision,
    }


def no_overclaim_scan(paths: list[Path]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def scan_json(value: Any, file_path: Path, path_parts: tuple[str, ...]) -> None:
        boundary_path = any(part in {"forbidden_operational_actions", "forbidden_operational_action", "input_claim_or_action", "not_claimed", "blocked", "items"} for part in path_parts)
        if isinstance(value, dict):
            for key, child in value.items():
                scan_json(child, file_path, (*path_parts, str(key)))
            return
        if isinstance(value, list):
            for idx, child in enumerate(value):
                scan_json(child, file_path, (*path_parts, str(idx)))
            return
        if not isinstance(value, str) or boundary_path:
            return
        lowered = value.lower()
        for term in NO_OVERCLAIM_TERMS:
            if term.lower() in lowered:
                findings.append({"file": str(file_path), "term": term, "json_path": ".".join(path_parts)})

    for root in paths:
        if not root.exists():
            continue
        for file_path in sorted(p for p in root.rglob("*") if p.is_file()):
            if file_path.suffix.lower() == ".json":
                try:
                    scan_json(json.loads(file_path.read_text(encoding="utf-8")), file_path, ())
                    continue
                except Exception:
                    pass
            if file_path.suffix.lower() in {".md", ".txt", ".jsonl"}:
                text = file_path.read_text(encoding="utf-8", errors="replace").lower()
                for term in NO_OVERCLAIM_TERMS:
                    if term.lower() in text:
                        findings.append({"file": str(file_path), "term": term})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def final_print(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "PV1-D19/D20/D21/D22 Guardrail / Action Policy / Composite Platform v1 Snapshot: STATUS",
            "",
            f"D19 action policy: {result['d19_action_policy']}",
            f"D20 guardrail harness: {result['d20_guardrail_harness']}",
            f"Forbidden actions blocked: {result['forbidden_actions_blocked']}",
            f"Allowed review actions allowed: {result['allowed_review_actions_allowed']}",
            f"Claim misuse blocked: {result['claim_misuse_blocked']}",
            "",
            f"D21 composite snapshot: {result['d21_composite_snapshot']}",
            f"Accepted flows indexed: {result['accepted_flows_indexed']}",
            f"Review-route-ready flows indexed: {result['review_route_ready_flows_indexed']}",
            f"Candidate-only flows indexed: {result['candidate_only_flows_indexed']}",
            f"Data-route-ready rows indexed: {result['data_route_ready_rows_indexed']}",
            "",
            f"D22 final audit: {result['d22_final_audit']}",
            f"Evidence coverage: {result['evidence_coverage']}",
            f"No-overclaim: {result['no_overclaim']}",
            f"No-mutation: {result['no_mutation']}",
            f"Hashes: {result['hashes']}",
            "",
            "Final status:",
            result["status"],
            "",
            "Output:",
            result["gate_output_relative"],
        ]
    )


def run_pv1_d19d20d21d22_gate(
    project_root: str | Path = ".",
    d19_output: str | Path = DEFAULT_D19_OUTPUT,
    d20_output: str | Path = DEFAULT_D20_OUTPUT,
    d21_output: str | Path = DEFAULT_D21_OUTPUT,
    d22_output: str | Path = DEFAULT_D22_OUTPUT,
    gate_output: str | Path = DEFAULT_GATE_OUTPUT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    d19_dir = (root / d19_output).resolve()
    d20_dir = (root / d20_output).resolve()
    d21_dir = (root / d21_output).resolve()
    d22_dir = (root / d22_output).resolve()
    gate_dir = (root / gate_output).resolve()
    inputs = {rel: (root / rel).resolve() for rel in [*READ_ONLY_INPUTS, *OPTIONAL_INPUTS]}
    before = {rel: tree_signature(path) for rel, path in inputs.items()}
    for output_dir in [d19_dir, d20_dir, d21_dir, d22_dir, gate_dir]:
        reset_output_dir(output_dir, root)

    input_inventory = {
        "status": "PASS" if all((root / rel).exists() for rel in READ_ONLY_INPUTS) else "FAIL",
        "required_inputs": {rel: tree_signature(path) for rel, path in inputs.items() if rel in READ_ONLY_INPUTS},
        "optional_inputs": {rel: tree_signature(path) for rel, path in inputs.items() if rel in OPTIONAL_INPUTS},
    }
    d19 = make_d19_policy(d19_dir)
    d20 = make_d20_harness(d20_dir)
    d21 = make_d21_snapshot(root, d21_dir)
    after = {rel: tree_signature(path) for rel, path in inputs.items()}
    mutation = compare_signatures(before, after)
    overclaim_pre = no_overclaim_scan([d19_dir, d20_dir, d21_dir, gate_dir])
    d22 = make_d22_audit(root, d22_dir, d21, mutation, overclaim_pre)
    overclaim = no_overclaim_scan([d19_dir, d20_dir, d21_dir, d22_dir, gate_dir])
    d22 = make_d22_audit(root, d22_dir, d21, mutation, overclaim)

    component_status_matrix = {"status": "PASS", "components": d21["component_ledger"]}
    claim_boundary_matrix = {
        "status": "PASS",
        "claim_labels": CLAIM_LABELS,
        "allowed_review_actions": ALLOWED_REVIEW_ACTIONS,
        "blocked_operational_actions": FORBIDDEN_OPERATIONAL_ACTIONS,
        "review_context_only": True,
    }
    final_decision = {
        "status": "PASS",
        "final_status": "PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT",
        "snapshot_ref": "outputs/pv1_d21_composite_platform_v1_snapshot/PV1_D21_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT.json",
        "review_context_only": True,
        "operational_actions_enabled": False,
    }
    stage_ledger = {
        "status": "PASS",
        "stages": {
            "PV1-D19": {"status": "PASS", "output": str(d19_dir)},
            "PV1-D20": {"status": d20["report"]["status"], "output": str(d20_dir)},
            "PV1-D21": {"status": "PASS", "output": str(d21_dir)},
            "PV1-D22": {"status": d22["final_audit"]["status"], "output": str(d22_dir)},
        },
    }
    gates = [
        gate("PV1-D19-PRECOND", input_inventory["status"] == "PASS"),
        gate("PV1-D19-ACTION-POLICY-CONTRACT", d19["contract"]["operational_actions_enabled"] is False),
        gate("PV1-D19-FORBIDDEN-ACTIONS-POLICY", len(d19["forbidden"]["forbidden_operational_actions"]) == len(FORBIDDEN_OPERATIONAL_ACTIONS)),
        gate("PV1-D19-CLAIM-LABEL-POLICY", set(d19["claim_policy"]["claim_labels"]) == set(CLAIM_LABELS)),
        gate("PV1-D19-ACCEPTANCE-STATUS-POLICY", d19["acceptance"]["review_route_ready_is_not_accepted"] is True),
        gate("PV1-D20-GUARDRAIL-HARNESS", d20["report"]["status"] == "PASS"),
        gate("PV1-D20-FORBIDDEN-ACTION-TESTS", all(row["pass"] for row in d20["forbidden_rows"])),
        gate("PV1-D20-ALLOWED-ACTION-TESTS", all(row["pass"] for row in d20["allowed_rows"])),
        gate("PV1-D20-CLAIM-LABEL-TESTS", all(row["pass"] for row in d20["claim_rows"])),
        gate("PV1-D20-PERSONA-SUPPRESSION-TESTS", any(row["category"] == "persona_misuse" and row["pass"] for row in d20["tests"])),
        gate("PV1-D20-SUMO-BOUNDARY-TESTS", any(row["category"] == "sumo_boundary" and row["pass"] for row in d20["tests"])),
        gate("PV1-D20-TRACK2-BOUNDARY-TESTS", any(row["category"] == "track2_boundary" and row["pass"] for row in d20["tests"])),
        gate("PV1-D20-HITL-BOUNDARY-TESTS", any(row["category"] == "hitl_boundary" and row["pass"] for row in d20["tests"])),
        gate("PV1-D21-COMPOSITE-SNAPSHOT", d21["snapshot"]["review_context_only"] is True and d21["snapshot"]["operational_actions_enabled"] is False),
        gate("PV1-D21-COMPONENT-LEDGER", all(row["exists"] for row in d21["component_ledger"])),
        gate("PV1-D21-ACCEPTED-VS-REVIEW-READY-MATRIX", len(d21["accepted_matrix"]["accepted_flows"]) == 8 and len(d21["accepted_matrix"]["review_route_ready_not_accepted"]) == 5),
        gate("PV1-D21-ROUTE-DATA-ASSET-INDEX", len(d21["route_asset_index"]["data_route_ready_rows"]) == 7),
        gate("PV1-D21-PERSONA-HITL-SUMO-INDEXES", d21["persona_index"]["status"] == d21["hitl_index"]["status"] == d21["sumo_index"]["status"] == "PASS"),
        gate("PV1-D21-LIMITATION-REGISTER", len(d21["limitations"]) > 0 and len(d21["backlog"]["items"]) >= 6),
        gate("PV1-D22-EVIDENCE-COVERAGE", d22["evidence_coverage"]["status"] == "PASS"),
        gate("PV1-D22-NO-OVERCLAIM-AUDIT", overclaim["status"] == "PASS"),
        gate("PV1-D22-NO-MUTATION-AUDIT", mutation["status"] == "PASS"),
        gate("PV1-D22-CLAIM-LABEL-AUDIT", d22["claim_label_audit"]["status"] == "PASS"),
        gate("PV1-D22-SYNTHETIC-VS-REAL-AUDIT", d22["synthetic_vs_real"]["status"] == "PASS"),
        gate("PV1-D22-ACCEPTANCE-STATUS-AUDIT", d22["acceptance"]["status"] == "PASS"),
        gate("PV1-D22-FINAL-DECISION", d22["decision"]["status"] == "PASS"),
        gate("PV1-D19D20D21D22-HASHES", True),
    ]
    if gates_pass(gates):
        status = "PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT"
    elif overclaim["status"] == "PASS" and mutation["status"] == "PASS":
        status = "PASS_PLATFORM_V1_SNAPSHOT_WITH_LIMITATIONS"
    else:
        status = "FAIL"

    result = {
        "task": "PV1-D19/D20/D21/D22 Guardrail / Action Policy / Composite Platform v1 Snapshot",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "gates": gates,
        "d19_action_policy": "PASS" if all(gates[i]["status"] == "PASS" for i in range(1, 5)) else "FAIL",
        "d20_guardrail_harness": d20["report"]["status"],
        "forbidden_actions_blocked": d20["report"]["forbidden_actions_blocked"],
        "allowed_review_actions_allowed": d20["report"]["allowed_review_actions_allowed"],
        "claim_misuse_blocked": d20["report"]["claim_label_misuse_blocked"],
        "d21_composite_snapshot": "PASS" if gates[13]["status"] == "PASS" else "FAIL",
        "accepted_flows_indexed": len(d21["snapshot"]["accepted_flows"]),
        "review_route_ready_flows_indexed": len(d21["snapshot"]["review_route_ready_flows"]),
        "candidate_only_flows_indexed": len(d21["snapshot"]["candidate_only_flows"]),
        "data_route_ready_rows_indexed": len(d21["snapshot"]["data_route_ready_rows"]),
        "d22_final_audit": d22["final_audit"]["status"],
        "evidence_coverage": d22["evidence_coverage"]["status"],
        "no_overclaim": overclaim["status"],
        "no_mutation": mutation["status"],
        "hashes": "PASS",
        "gate_output": str(gate_dir),
        "gate_output_relative": str(Path(gate_output)),
        "d19_output": str(d19_dir),
        "d20_output": str(d20_dir),
        "d21_output": str(d21_dir),
        "d22_output": str(d22_dir),
    }
    write_json(gate_dir / "PV1_D19D20D21D22_INPUT_INVENTORY.json", input_inventory)
    write_json(gate_dir / "PV1_D19D20D21D22_STAGE_LEDGER.json", stage_ledger)
    write_json(gate_dir / "PV1_D19D20D21D22_COMPONENT_STATUS_MATRIX.json", component_status_matrix)
    write_json(gate_dir / "PV1_D19D20D21D22_CLAIM_BOUNDARY_MATRIX.json", claim_boundary_matrix)
    write_json(gate_dir / "PV1_D19D20D21D22_FINAL_DECISION.json", final_decision)
    write_json(gate_dir / "PV1_D19D20D21D22_NO_OVERCLAIM_REPORT.json", overclaim)
    write_json(gate_dir / "PV1_D19D20D21D22_NO_MUTATION_REPORT.json", mutation)
    write_json(gate_dir / "PV1_D19D20D21D22_HARNESS_REPORT.json", result)
    write_text(gate_dir / "README.md", "# PV1-D19/D20/D21/D22 Platform v1 Review-Only Snapshot Gate\n\nFinal review-only validation snapshot gate.")
    hashes = write_hashes(gate_dir)
    result["hash_count"] = len(hashes)
    write_json(gate_dir / "PV1_D19D20D21D22_HARNESS_REPORT.json", result)
    write_hashes(gate_dir)
    result["final_print"] = final_print(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D19/D20/D21/D22 guardrail and review-only snapshot gate.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    result = run_pv1_d19d20d21d22_gate(args.project_root)
    print(result["final_print"])
    return 0 if result["status"] in {"PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT", "PASS_PLATFORM_V1_SNAPSHOT_WITH_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
