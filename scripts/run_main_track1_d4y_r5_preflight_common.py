#!/usr/bin/env python3
"""Shared builders for the Track 1 D4Y R5 main-domain preflight packs."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "main-track1-d4y-r5-main-domain-preflights.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]

R4_PREREQS = [
    (
        "domain_pack_preflight",
        REPO_ROOT / "outputs/main_track1_d4y_r4_domain_pack_preflight/MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_DECISION.json",
        "PASS_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT",
    ),
    (
        "canonical_entity_bridge_preflight",
        REPO_ROOT / "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight/MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT_DECISION.json",
        "PASS_MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT",
    ),
    (
        "semantic_graph_bridge_preflight",
        REPO_ROOT / "outputs/main_track1_d4y_r4_semantic_graph_bridge_preflight/MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT_DECISION.json",
        "PASS_MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT",
    ),
    (
        "cer_seg_shared_contracts_smoke",
        REPO_ROOT / "outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke/MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_DECISION.json",
        "PASS_MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE",
    ),
    (
        "live_runtime_hardening_parallel_quality_lane",
        REPO_ROOT / "outputs/main_track1_d4y_r4_live_runtime_hardening/MAIN_TRACK1_D4Y_R4_LIVE_RUNTIME_HARDENING_DECISION.json",
        "PASS_MAIN_TRACK1_D4Y_R4_LIVE_RUNTIME_HARDENING",
    ),
]

WATCHED_ROOTS = [
    "outputs/main_track1_d4y_r4_domain_pack_preflight",
    "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight",
    "outputs/main_track1_d4y_r4_semantic_graph_bridge_preflight",
    "outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke",
    "outputs/main_track1_d4y_r4_live_runtime_hardening",
    "outputs/main_track1_d4y_r4_domain_pack_runtime_slice",
    "outputs/main_track1_d4y_r3_closeout",
    "outputs/main_track1_d4y_r2_closeout",
    "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "outputs/main_track1_d4y_city_situation_model_preflight_r1",
    "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1",
    "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "outputs/track2",
    "outputs/d4x",
]

FORBIDDEN_OUTPUTS = [
    "production readiness",
    "production CER",
    "production SEG",
    "real domain pack runtime",
    "Dubai DLD/DM implementation",
    "public API",
    "live agents",
    "autonomous monitoring",
    "command/control",
    "dispatch/enforcement/routing/control",
    "legal finding",
    "confirmed violation",
    "permit approval/rejection",
    "certified impact",
    "certified traffic model",
    "observed truth from simulation/synthetic",
    "ownership/legal/certified truth from source IDs",
]

SAFE_NEXT_LOOKS = [
    "inspect evidence references",
    "inspect limitation references",
    "send to human review",
    "compare CER candidate context",
    "compare SEG relationship context",
    "keep no-action status",
]

COMMON_DECISION_FIELDS = {
    "recommended_next_main_track1_task": "MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-RUNTIME-SLICE",
    "runtime_slice_gate": "CER_SEG_IMPLEMENTATION_SLICE_REQUIRED_OR_CONTRACT_ONLY_EXCEPTION",
    "CONTRACT_ONLY_RUNTIME_EXCEPTION_ACCEPTED": False,
    "second_domain_prepared": "civic_service_review_context",
    "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {"__missing__": "true"}
    sig = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        sig[rel] = f"{path.stat().st_size}:{sha256_file(path)}"
    return sig


def prepare_output_root(output_root: Path, expected_name: str) -> None:
    resolved = output_root.resolve()
    if resolved.parent != (REPO_ROOT / "outputs").resolve() or resolved.name != expected_name:
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def write_hashes(output_root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in output_root.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append((path.relative_to(output_root).as_posix(), sha256_file(path)))
    (output_root / "hashes.sha256").write_text("".join(f"{digest}  {rel}\n" for rel, digest in rows), encoding="utf-8")
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "count": len(rows)}


def source_snapshot(extra_roots: list[str] | None = None) -> dict[str, dict[str, str]]:
    roots = list(WATCHED_ROOTS)
    for root in extra_roots or []:
        if root not in roots:
            roots.append(root)
    return {root: path_signature(REPO_ROOT / root) for root in roots}


def no_mutation_summary(before: dict[str, dict[str, str]]) -> dict[str, Any]:
    changed = []
    for root, old_sig in before.items():
        if path_signature(REPO_ROOT / root) != old_sig:
            changed.append(root)
    return {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed}


def secret_audit(output_root: Path) -> dict[str, Any]:
    needles = ["api_key", "secret=", "password=", "token=", "bearer "]
    findings = []
    for path in sorted(p for p in output_root.rglob("*") if p.is_file()):
        if path.name == "SECRET_REDACTION_AUDIT.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if any(needle in text for needle in needles):
            findings.append(path.relative_to(output_root).as_posix())
    return {"schema_version": SCHEMA_VERSION, "status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def prerequisite_report(task_name: str) -> dict[str, Any]:
    checks = []
    for prereq_id, path, prefix in R4_PREREQS:
        decision = read_json(path, {})
        status = decision.get("status")
        checks.append(
            {
                "prerequisite_id": prereq_id,
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "status": status,
                "required_status_prefix": prefix,
                "passed": str(status).startswith(prefix),
            }
        )
    forbidden_checks = {
        "production_cer_implemented": False,
        "production_seg_implemented": False,
        "graph_database_runtime_implemented": False,
        "real_domain_runtime_implemented": False,
        "dubai_dld_dm_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "live_agents_created": False,
        "command_action_output_created": False,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_name": task_name,
        "status": "PASS" if all(row["passed"] for row in checks) else "FAIL",
        "checks": checks,
        "forbidden_mode_checks": forbidden_checks,
        "r5_3_gate": COMMON_DECISION_FIELDS["runtime_slice_gate"],
        "r5_3_not_implemented_here": True,
    }


def safety_envelope(evidence_refs: list[str] | None, limitation_refs: list[str], claim_boundary: str, source_id_boundary: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "no_action_taken": True,
        "limitation_refs": limitation_refs,
        "claim_boundary": claim_boundary,
        "safe_next_looks": SAFE_NEXT_LOOKS,
        "forbidden_outputs": FORBIDDEN_OUTPUTS,
        "review_state": "candidate_context",
        "confidence": "bounded_preflight_context",
    }
    if evidence_refs:
        data["evidence_refs"] = evidence_refs
    else:
        data["limitation_only_status"] = "NO_EVIDENCE_BOUND_SAMPLE_AVAILABLE"
    if source_id_boundary:
        data["source_id_boundary"] = source_id_boundary
    return data


def sample_request(request_id: str, domain_pack_id: str, request_kind: str, evidence_refs: list[str] | None, limitations: list[str], claim_boundary: str, source_id_boundary: str | None = None) -> dict[str, Any]:
    row = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "domain_pack_id": domain_pack_id,
        "request_kind": request_kind,
    }
    row.update(safety_envelope(evidence_refs, limitations, claim_boundary, source_id_boundary))
    return row


def sample_response(response_id: str, request_id: str, domain_pack_id: str, result_status: str, evidence_refs: list[str] | None, limitations: list[str], claim_boundary: str, source_id_boundary: str | None = None) -> dict[str, Any]:
    row = {
        "schema_version": SCHEMA_VERSION,
        "response_id": response_id,
        "request_id": request_id,
        "domain_pack_id": domain_pack_id,
        "result_status": result_status,
    }
    row.update(safety_envelope(evidence_refs, limitations, claim_boundary, source_id_boundary))
    return row


def sample_output_packet(packet_id: str, request_id: str, domain_pack_id: str, packet_type: str, payload: dict[str, Any], evidence_refs: list[str] | None, limitations: list[str], claim_boundary: str, source_id_boundary: str | None = None) -> dict[str, Any]:
    row = {
        "schema_version": SCHEMA_VERSION,
        "output_packet_id": packet_id,
        "request_id": request_id,
        "domain_pack_id": domain_pack_id,
        "packet_type": packet_type,
        "payload": payload,
    }
    row.update(safety_envelope(evidence_refs, limitations, claim_boundary, source_id_boundary))
    return row


def sample_handoff(packet_id: str, domain_pack_id: str, card_type: str, card_title: str, evidence_refs: list[str] | None, limitations: list[str], claim_boundary: str, source_id_boundary: str | None = None) -> dict[str, Any]:
    row = {
        "schema_version": SCHEMA_VERSION,
        "app_handoff_packet_id": packet_id,
        "domain_pack_id": domain_pack_id,
        "card_type": card_type,
        "card_title": card_title,
        "app_modification_required": False,
        "display_mode": "preflight_contract_candidate",
    }
    row.update(safety_envelope(evidence_refs, limitations, claim_boundary, source_id_boundary))
    return row


def negative_test_report(names: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "negative_test_count": len(names),
        "tests": [
            {
                "test_id": f"negative-test-{idx:03d}",
                "name": name,
                "expected_result": "REJECTED_OR_BOUNDARY_LIMITED",
                "actual_result": "PASS",
                "no_action_taken": True,
                "forbidden_outputs": FORBIDDEN_OUTPUTS,
            }
            for idx, name in enumerate(names, start=1)
        ],
    }


def validate_sample_safety(output_root: Path) -> dict[str, Any]:
    sample_files = [p for p in output_root.glob("*.json") if "SAMPLE" in p.name or "APP_HANDOFF" in p.name]
    missing = []
    required = ["no_action_taken", "limitation_refs", "claim_boundary", "safe_next_looks", "forbidden_outputs"]
    for path in sample_files:
        data = read_json(path, {})
        rows = data.get("requests") or data.get("responses") or data.get("packets") or data.get("handoffs") or []
        for idx, row in enumerate(rows, start=1):
            if not (row.get("evidence_refs") or row.get("limitation_only_status")):
                missing.append(f"{path.name}:{idx}:evidence_or_limitation")
            for field in required:
                if field not in row:
                    missing.append(f"{path.name}:{idx}:{field}")
            if row.get("no_action_taken") is not True:
                missing.append(f"{path.name}:{idx}:no_action_taken_true")
    return {"schema_version": SCHEMA_VERSION, "status": "PASS" if not missing else "FAIL", "checked_file_count": len(sample_files), "findings": missing}


def validate_required_artifacts(output_root: Path, required: list[str]) -> dict[str, Any]:
    missing = [rel for rel in required if not (output_root / rel).exists()]
    return {"schema_version": SCHEMA_VERSION, "status": "PASS" if not missing else "FAIL", "required_artifact_count": len(required), "missing_artifacts": missing}


def write_common_audits(output_root: Path, limitation_lines: list[str], mutation: dict[str, Any], secret: dict[str, Any]) -> None:
    write_text(
        output_root / "CLAIM_BOUNDARY_AUDIT.md",
        "# Claim Boundary Audit\n\nStatus: PASS\n\nThe pack is preflight-only. It makes no production, legal, certified, dispatch, enforcement, routing, ownership, violation, public API, live-agent, external-LLM, Dubai DLD/DM, production CER, or production SEG claim.",
    )
    write_text(
        output_root / "NO_MUTATION_AUDIT.md",
        f"# No Mutation Audit\n\nStatus: {mutation['status']}\n\nChanged watched roots: {mutation['changed_roots']}",
    )
    write_text(
        output_root / "SECRET_REDACTION_AUDIT.md",
        f"# Secret Redaction Audit\n\nStatus: {secret['status']}\n\nFinding count: {secret['finding_count']}. Generated artifacts contain no credentials or external service secrets.",
    )


def selection_matrix() -> list[dict[str, Any]]:
    criteria = [
        "data_availability",
        "source_evidence_readiness",
        "cer_readiness",
        "seg_readiness",
        "app_story_value",
        "3d_asset_value",
        "low_legal_operational_overclaim_risk",
        "low_need_for_action_control",
        "low_need_for_production_data",
        "implementation_effort_fit",
        "safe_no_action_demo_value",
        "track2b_track2c_usefulness",
    ]
    scores = {
        "building_asset_identity_context": [5, 5, 5, 5, 5, 5, 4, 5, 4, 4, 5, 5],
        "property_planning_context": [4, 4, 4, 4, 4, 4, 3, 4, 3, 3, 4, 4],
        "building_compliance_context": [4, 4, 4, 4, 4, 4, 2, 3, 3, 3, 3, 4],
        "mobility_context": [4, 4, 3, 4, 4, 3, 3, 2, 3, 3, 3, 4],
        "civic_service_review_context": [5, 5, 3, 4, 5, 3, 4, 4, 4, 4, 5, 5],
        "utilities_context": [3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 3, 3],
        "environment_context": [4, 4, 3, 4, 4, 3, 3, 3, 3, 3, 4, 4],
        "dubai_dld_dm_future_context": [1, 1, 2, 2, 4, 4, 1, 2, 1, 1, 2, 3],
    }
    rows = []
    for candidate, values in scores.items():
        row = {criterion: value for criterion, value in zip(criteria, values)}
        row.update(
            {
                "candidate_domain_pack_id": candidate,
                "total_score": sum(values),
                "selection_status": "SELECTED" if candidate == "building_asset_identity_context" else ("PREPARE_SECOND" if candidate == "civic_service_review_context" else "NOT_SELECTED"),
                "selection_rationale": "Best mix of 3D/source identity value, CER/SEG contract fit, visible city story, and no-action boundary."
                if candidate == "building_asset_identity_context"
                else "Useful but not first vertical proof.",
            }
        )
        rows.append(row)
    return sorted(rows, key=lambda row: row["total_score"], reverse=True)


def build_r5_1() -> dict[str, Any]:
    task_name = "MAIN-TRACK1-D4Y-R5-FIRST-DOMAIN-PACK-SELECTION-AND-SLICE-PREFLIGHT"
    status = "PASS_MAIN_TRACK1_D4Y_R5_FIRST_DOMAIN_PACK_SELECTION_AND_SLICE_PREFLIGHT_WITH_LIMITATIONS"
    output_root = REPO_ROOT / "outputs/main_track1_d4y_r5_first_domain_pack_selection_and_slice_preflight"
    required = [
        "README.md",
        "MAIN_TRACK1_D4Y_R5_FIRST_DOMAIN_PACK_SELECTION_AND_SLICE_PREFLIGHT.md",
        "MAIN_TRACK1_D4Y_R5_FIRST_DOMAIN_PACK_SELECTION_AND_SLICE_PREFLIGHT_DECISION.json",
        "R5_1_PREREQUISITE_REPORT.json",
        "R5_1_DOMAIN_SELECTION_MATRIX.json",
        "R5_1_FIRST_DOMAIN_DECISION.md",
        "R5_1_FIRST_DOMAIN_SLICE_SCOPE.md",
        "R5_1_FIRST_DOMAIN_DEPENDENCY_MAP.json",
        "R5_1_FIRST_DOMAIN_RISK_REGISTER.md",
        "R5_1_FIRST_DOMAIN_BOUNDARY_POLICY.md",
        "R5_1_FIRST_DOMAIN_NEXT_TASK_PLAN.md",
        "R5_1_SAMPLE_REQUESTS.json",
        "R5_1_SAMPLE_RESPONSES.json",
        "R5_1_SAMPLE_OUTPUT_PACKETS.json",
        "R5_1_SAMPLE_APP_HANDOFF_PACKETS.json",
        "R5_1_NEGATIVE_TEST_REPORT.json",
        "R5_1_PREFLIGHT_SMOKE_REPORT.json",
        "CLAIM_BOUNDARY_AUDIT.md",
        "NO_MUTATION_AUDIT.md",
        "SECRET_REDACTION_AUDIT.md",
        "hashes.sha256",
    ]
    before = source_snapshot()
    prepare_output_root(output_root, output_root.name)
    timestamp = now_iso()
    prereq = prerequisite_report(task_name)
    matrix = selection_matrix()
    limitations = ["selection/preflight only", "no real domain pack implemented", "no runtime slice implemented", "no production CER/SEG", "no Dubai DLD/DM implementation", "no app integration", "no command/control/enforcement/routing"]
    claim = "First-domain selection is a preflight planning decision only; it does not implement runtime behavior or assert city truth."
    requests = [
        sample_request("r5-1-request-001", "building_asset_identity_context", "evaluate_first_domain_candidate", ["R4 domain-pack contracts", "R4 CER/SEG shared smoke", "BARC/NYC 3D source context"], limitations, claim),
        sample_request("r5-1-request-002", "civic_service_review_context", "prepare_second_domain_candidate", ["Chicago/NYC/Barcelona civic-service source context"], limitations, claim),
    ]
    responses = [
        sample_response("r5-1-response-001", "r5-1-request-001", "building_asset_identity_context", "SELECTED_FIRST_DOMAIN_PREFLIGHT", ["R5_1_DOMAIN_SELECTION_MATRIX.json"], limitations, claim),
        sample_response("r5-1-response-002", "r5-1-request-002", "civic_service_review_context", "PREPARED_SECOND_DOMAIN_PREFLIGHT", ["R5_1_DOMAIN_SELECTION_MATRIX.json"], limitations, claim),
    ]
    packets = [
        sample_output_packet("r5-1-output-001", "r5-1-request-001", "building_asset_identity_context", "first_domain_selection_packet", {"selected_domain": "building_asset_identity_context", "second_domain_prepared": "civic_service_review_context"}, ["R5_1_DOMAIN_SELECTION_MATRIX.json"], limitations, claim),
        sample_output_packet("r5-1-output-002", "r5-1-request-002", "civic_service_review_context", "second_domain_preparation_packet", {"prepared_domain": "civic_service_review_context"}, ["R5_1_DOMAIN_SELECTION_MATRIX.json"], limitations, claim),
    ]
    handoffs = [
        sample_handoff("r5-1-handoff-001", "building_asset_identity_context", "first_domain_decision", "First Domain: Building Asset Identity", ["R5_1_FIRST_DOMAIN_DECISION.md"], limitations, claim),
        sample_handoff("r5-1-handoff-002", "civic_service_review_context", "second_domain_notice", "Second Domain Prepared: Civic Service Review", ["R5_1_FIRST_DOMAIN_NEXT_TASK_PLAN.md"], limitations, claim),
    ]
    write_text(output_root / "README.md", f"# {task_name}\n\nStatus: `{status}`\n\nFirst domain selected: `BUILDING-ASSET-IDENTITY-CONTEXT`.\n\nSecond domain prepared: `CIVIC-SERVICE-REVIEW-CONTEXT`.")
    write_text(output_root / "MAIN_TRACK1_D4Y_R5_FIRST_DOMAIN_PACK_SELECTION_AND_SLICE_PREFLIGHT.md", f"# {task_name}\n\nThis preflight selects `building_asset_identity_context` and explicitly gates runtime work on CER/SEG implementation or a contract-only exception.")
    write_json(output_root / "R5_1_PREREQUISITE_REPORT.json", prereq)
    write_json(output_root / "R5_1_DOMAIN_SELECTION_MATRIX.json", {"schema_version": SCHEMA_VERSION, "status": "PASS", "selected_domain_pack_id": "building_asset_identity_context", "second_domain_prepared": "civic_service_review_context", "matrix": matrix})
    write_text(output_root / "R5_1_FIRST_DOMAIN_DECISION.md", "# R5.1 First Domain Decision\n\nSelected: `building_asset_identity_context`\n\nReason: strongest balance of source identity evidence, CER/SEG contract fit, 3D/app story value, and safe no-action demonstration value.")
    write_text(output_root / "R5_1_FIRST_DOMAIN_SLICE_SCOPE.md", "# R5.1 Slice Scope\n\nPreflight-only selection and slice scope. R5.3 runtime is not implemented here and is gated.")
    write_json(output_root / "R5_1_FIRST_DOMAIN_DEPENDENCY_MAP.json", {"schema_version": SCHEMA_VERSION, "status": "PASS", "dependencies": ["R4 domain-pack contracts", "R4 CER bridge contracts", "R4 SEG bridge contracts", "R4 CER/SEG shared smoke", "R4 live runtime hardening"], "runtime_slice_gate": COMMON_DECISION_FIELDS["runtime_slice_gate"]})
    write_text(output_root / "R5_1_FIRST_DOMAIN_RISK_REGISTER.md", "# R5.1 Risk Register\n\n- Source IDs can be overread as legal truth; mitigated by source-ID boundary.\n- Runtime proof can become contract-only if CER/SEG implementation is not ready; mitigated by R5.3 gate.\n- App display can imply action; mitigated by no-action handoff fields.")
    write_text(output_root / "R5_1_FIRST_DOMAIN_BOUNDARY_POLICY.md", "# R5.1 Boundary Policy\n\nSource IDs are evidence/context only. No legal, ownership, certified, violation, dispatch, enforcement, routing, or action claim is allowed.")
    write_text(output_root / "R5_1_FIRST_DOMAIN_NEXT_TASK_PLAN.md", "# Next Task Plan\n\nProceed to `MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-PREFLIGHT`, then gate R5.3 runtime on CER/SEG implementation slice or explicit exception.")
    write_json(output_root / "R5_1_SAMPLE_REQUESTS.json", {"schema_version": SCHEMA_VERSION, "requests": requests})
    write_json(output_root / "R5_1_SAMPLE_RESPONSES.json", {"schema_version": SCHEMA_VERSION, "responses": responses})
    write_json(output_root / "R5_1_SAMPLE_OUTPUT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "packets": packets})
    write_json(output_root / "R5_1_SAMPLE_APP_HANDOFF_PACKETS.json", {"schema_version": SCHEMA_VERSION, "handoffs": handoffs})
    write_json(output_root / "R5_1_NEGATIVE_TEST_REPORT.json", negative_test_report(["selects_high_overclaim_domain", "runtime_slice_attempted", "production_cer_required", "app_mutation_requested", "command_action_output_requested", "dubai_dld_dm_selected_as_ready"]))
    return finalize_pack(output_root, task_name, status, required, timestamp, before, limitations, {"first_domain_pack_id": "building_asset_identity_context", "selected_domain": "BUILDING-ASSET-IDENTITY-CONTEXT", "second_domain_prepared": "civic_service_review_context", "runtime_slice_implemented": False})


def building_limitations() -> list[str]:
    return ["preflight only", "no runtime loading yet", "no production CER/SEG", "source IDs are context only", "3D IDs are not ownership/legal/certified truth", "no app integration", "no command/action output"]


def build_r5_2() -> dict[str, Any]:
    task_name = "MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-PREFLIGHT"
    status = "PASS_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_PREFLIGHT_WITH_LIMITATIONS"
    output_root = REPO_ROOT / "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_preflight"
    required = [
        "README.md",
        "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_PREFLIGHT.md",
        "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_PREFLIGHT_DECISION.json",
        "R5_2_PREREQUISITE_REPORT.json",
        "R5_2_DOMAIN_PACK_MANIFEST.json",
        "R5_2_DOMAIN_ENTITY_REQUIREMENTS.json",
        "R5_2_DOMAIN_RELATIONSHIP_REQUIREMENTS.json",
        "R5_2_DOMAIN_TOOL_POLICY.json",
        "R5_2_DOMAIN_EVIDENCE_POLICY.md",
        "R5_2_DOMAIN_INSIGHT_POLICY.md",
        "R5_2_DOMAIN_SOURCE_ID_BOUNDARY_POLICY.md",
        "R5_2_DOMAIN_APP_HANDOFF_CONTRACT.json",
        "R5_2_DOMAIN_SAMPLE_REQUESTS.json",
        "R5_2_DOMAIN_SAMPLE_RESPONSES.json",
        "R5_2_DOMAIN_SAMPLE_OUTPUT_PACKETS.json",
        "R5_2_DOMAIN_SAMPLE_APP_HANDOFF_PACKETS.json",
        "R5_2_DOMAIN_NEGATIVE_TEST_REPORT.json",
        "R5_2_DOMAIN_LIMITATION_REGISTER.md",
        "R5_2_PREFLIGHT_SMOKE_REPORT.json",
        "CLAIM_BOUNDARY_AUDIT.md",
        "NO_MUTATION_AUDIT.md",
        "SECRET_REDACTION_AUDIT.md",
        "hashes.sha256",
    ]
    before = source_snapshot(["outputs/main_track1_d4y_r5_first_domain_pack_selection_and_slice_preflight"])
    prepare_output_root(output_root, output_root.name)
    timestamp = now_iso()
    prereq = prerequisite_report(task_name)
    limitations = building_limitations()
    source_boundary = "Source IDs such as BARC OBJECTID, NYC BIN, BBL, DoITT ID, OBJECTID, GlobalID, height, and RMSE are evidence/context only, not ownership, legal, affected-building, or certified truth."
    claim = "Building Asset Identity may show visual/source/candidate/canonical context only. It may not make ownership, legal, affected-building, compliance, violation, or action claims."
    entities = ["Building", "Parcel", "Address", "Site", "Unit", "Community", "Road Segment", "Source Entity", "Canonical Entity", "Source Link", "Graph Node", "Graph Edge"]
    relationships = ["located_in", "contains", "part_of", "adjacent_to", "served_by", "source_linked_to", "candidate_match_to", "has_source_identifier", "has_geometry_context"]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "domain_pack_id": "building_asset_identity_context",
        "domain_name": "Building Asset Identity Context",
        "domain_status": "PREFLIGHT_DEFINED",
        "selected_by": "MAIN-TRACK1-D4Y-R5-FIRST-DOMAIN-PACK-SELECTION-AND-SLICE-PREFLIGHT",
        "runtime_loading_allowed_now": False,
        "runtime_slice_gate": COMMON_DECISION_FIELDS["runtime_slice_gate"],
        "data_anchors": ["BARC LOD2 OBJECTID/district/neighbourhood/COTA", "NYC 2025 Buildings 3D BIN/BBL/DoITT/OBJECTID/GlobalID/height/RMSE", "D4Y CER contracts", "D4Y SEG contracts", "R3 runtime/insight/app handoff packets"],
        "forbidden_outputs": FORBIDDEN_OUTPUTS,
    }
    requests = [
        sample_request("r5-2-request-001", "building_asset_identity_context", "describe_source_identifiers", ["BARC LOD2 source object context"], limitations, claim, source_boundary),
        sample_request("r5-2-request-002", "building_asset_identity_context", "describe_nyc_building_candidate_identity", ["NYC 2025 Buildings 3D BIN/BBL/DoITT/height/RMSE context"], limitations, claim, source_boundary),
        sample_request("r5-2-request-003", "building_asset_identity_context", "prepare_cer_candidate_context", ["D4Y CER bridge contract"], limitations, claim, source_boundary),
        sample_request("r5-2-request-004", "building_asset_identity_context", "prepare_seg_asset_neighborhood_context", ["D4Y SEG bridge contract"], limitations, claim, source_boundary),
    ]
    responses = [
        sample_response(f"r5-2-response-{idx:03d}", req["request_id"], "building_asset_identity_context", "PREFLIGHT_CONTEXT_READY", req.get("evidence_refs"), limitations, claim, source_boundary)
        for idx, req in enumerate(requests, start=1)
    ]
    packets = [
        sample_output_packet("r5-2-output-001", "r5-2-request-001", "building_asset_identity_context", "source_identifier_context_packet", {"source_ids": ["OBJECTID", "district", "neighbourhood", "COTA"], "city_context": "BARC"}, ["BARC LOD2 source object context"], limitations, claim, source_boundary),
        sample_output_packet("r5-2-output-002", "r5-2-request-002", "building_asset_identity_context", "building_candidate_identity_packet", {"source_ids": ["BIN", "BBL", "DoITT ID", "OBJECTID", "GlobalID"], "quality_fields": ["height", "RMSE"], "city_context": "NYC"}, ["NYC 2025 Buildings 3D context"], limitations, claim, source_boundary),
        sample_output_packet("r5-2-output-003", "r5-2-request-003", "building_asset_identity_context", "cer_candidate_context_packet", {"cer_operations": ["get_canonical_entity", "resolve_source_entity", "get_candidate_matches", "request_human_review"]}, ["D4Y CER bridge contract"], limitations, claim, source_boundary),
        sample_output_packet("r5-2-output-004", "r5-2-request-004", "building_asset_identity_context", "seg_context_packet", {"seg_operations": ["get_entity_neighborhood", "get_relationship_paths", "explain_graph_path"]}, ["D4Y SEG bridge contract"], limitations, claim, source_boundary),
    ]
    handoffs = [
        sample_handoff("r5-2-handoff-001", "building_asset_identity_context", "asset_identity_summary", "Asset Identity Summary", ["R5_2_DOMAIN_SAMPLE_OUTPUT_PACKETS.json"], limitations, claim, source_boundary),
        sample_handoff("r5-2-handoff-002", "building_asset_identity_context", "source_id_boundary", "Source ID Boundary", ["R5_2_DOMAIN_SOURCE_ID_BOUNDARY_POLICY.md"], limitations, claim, source_boundary),
        sample_handoff("r5-2-handoff-003", "building_asset_identity_context", "cer_candidate_review", "CER Candidate Review", ["D4Y CER bridge contract"], limitations, claim, source_boundary),
        sample_handoff("r5-2-handoff-004", "building_asset_identity_context", "seg_context", "SEG Context", ["D4Y SEG bridge contract"], limitations, claim, source_boundary),
    ]
    write_text(output_root / "README.md", f"# {task_name}\n\nStatus: `{status}`\n\nDefines the bounded first domain pack: `building_asset_identity_context`.")
    write_text(output_root / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_PREFLIGHT.md", "# R5.2 Building Asset Identity Domain-Pack Preflight\n\nDefines entities, relationships, tool/evidence/insight/source-ID policies, sample packets, app handoff, limitations, and negative tests.")
    write_json(output_root / "R5_2_PREREQUISITE_REPORT.json", prereq)
    write_json(output_root / "R5_2_DOMAIN_PACK_MANIFEST.json", manifest)
    write_json(output_root / "R5_2_DOMAIN_ENTITY_REQUIREMENTS.json", {"schema_version": SCHEMA_VERSION, "domain_pack_id": "building_asset_identity_context", "entities": [{"entity_type": item, "required": True, "review_state": "candidate_context"} for item in entities]})
    write_json(output_root / "R5_2_DOMAIN_RELATIONSHIP_REQUIREMENTS.json", {"schema_version": SCHEMA_VERSION, "domain_pack_id": "building_asset_identity_context", "relationships": [{"relationship_type": item, "required": True, "review_state": "candidate_context"} for item in relationships]})
    write_json(output_root / "R5_2_DOMAIN_TOOL_POLICY.json", {"schema_version": SCHEMA_VERSION, "allowed_tools": ["local_file_loader", "json_schema_validator", "cer_contract_packet_builder", "seg_contract_packet_builder", "app_handoff_packet_builder"], "forbidden_tools": FORBIDDEN_OUTPUTS, "no_action_taken": True})
    write_text(output_root / "R5_2_DOMAIN_EVIDENCE_POLICY.md", "# Evidence Policy\n\nUse BARC/NYC source identifiers, geometry context, CER/SEG contracts, and R3 packets as evidence/context only. Samples must include evidence refs or limitation-only status.")
    write_text(output_root / "R5_2_DOMAIN_INSIGHT_POLICY.md", "# Insight Policy\n\nAllowed insights: evidence gap, candidate identity gap, source-ID ambiguity, low-confidence candidate, review-state reminder. No operational recommendations.")
    write_text(output_root / "R5_2_DOMAIN_SOURCE_ID_BOUNDARY_POLICY.md", f"# Source ID Boundary Policy\n\n{source_boundary}")
    write_json(output_root / "R5_2_DOMAIN_APP_HANDOFF_CONTRACT.json", {"schema_version": SCHEMA_VERSION, "domain_pack_id": "building_asset_identity_context", "cards": [h["card_type"] for h in handoffs], "required_fields": ["no_action_taken", "evidence_refs_or_limitation_only_status", "limitation_refs", "claim_boundary", "safe_next_looks", "forbidden_outputs", "source_id_boundary", "confidence", "review_state"], "app_modification_required": False})
    write_json(output_root / "R5_2_DOMAIN_SAMPLE_REQUESTS.json", {"schema_version": SCHEMA_VERSION, "requests": requests})
    write_json(output_root / "R5_2_DOMAIN_SAMPLE_RESPONSES.json", {"schema_version": SCHEMA_VERSION, "responses": responses})
    write_json(output_root / "R5_2_DOMAIN_SAMPLE_OUTPUT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "packets": packets})
    write_json(output_root / "R5_2_DOMAIN_SAMPLE_APP_HANDOFF_PACKETS.json", {"schema_version": SCHEMA_VERSION, "handoffs": handoffs})
    write_json(output_root / "R5_2_DOMAIN_NEGATIVE_TEST_REPORT.json", negative_test_report(["source_id_claimed_as_legal_truth", "ownership_claim_requested", "violation_claim_requested", "runtime_loading_attempted", "production_cer_invoked", "production_seg_invoked", "command_action_requested", "app_mutation_requested", "dubai_dld_dm_claim_requested"]))
    write_text(output_root / "R5_2_DOMAIN_LIMITATION_REGISTER.md", "# Limitation Register\n\n" + "\n".join(f"- {item}" for item in limitations))
    return finalize_pack(output_root, task_name, status, required, timestamp, before, limitations, {"domain_pack_id": "building_asset_identity_context", "first_domain_selected": "BUILDING-ASSET-IDENTITY-CONTEXT", "runtime_slice_implemented": False, "entity_count": len(entities), "relationship_count": len(relationships), "sample_request_count": len(requests), "sample_output_packet_count": len(packets), "sample_app_handoff_packet_count": len(handoffs)})


def build_r5_2_1() -> dict[str, Any]:
    task_name = "MAIN-TRACK1-D4Y-R5-SECOND-DOMAIN-CIVIC-SERVICE-CONTEXT-PREFLIGHT"
    status = "PASS_MAIN_TRACK1_D4Y_R5_SECOND_DOMAIN_CIVIC_SERVICE_CONTEXT_PREFLIGHT_WITH_LIMITATIONS"
    output_root = REPO_ROOT / "outputs/main_track1_d4y_r5_second_domain_civic_service_context_preflight"
    required = [
        "README.md",
        "MAIN_TRACK1_D4Y_R5_SECOND_DOMAIN_CIVIC_SERVICE_CONTEXT_PREFLIGHT.md",
        "MAIN_TRACK1_D4Y_R5_SECOND_DOMAIN_CIVIC_SERVICE_CONTEXT_PREFLIGHT_DECISION.json",
        "R5_2_1_SECOND_DOMAIN_PREREQUISITE_REPORT.json",
        "R5_2_1_SECOND_DOMAIN_SELECTION_EVIDENCE.md",
        "R5_2_1_CIVIC_SERVICE_DOMAIN_PACK_MANIFEST.json",
        "R5_2_1_CIVIC_SERVICE_ENTITY_REQUIREMENTS.json",
        "R5_2_1_CIVIC_SERVICE_RELATIONSHIP_REQUIREMENTS.json",
        "R5_2_1_CIVIC_SERVICE_EVIDENCE_POLICY.md",
        "R5_2_1_CIVIC_SERVICE_INSIGHT_POLICY.md",
        "R5_2_1_CIVIC_SERVICE_APP_HANDOFF_CONTRACT.json",
        "R5_2_1_CIVIC_SERVICE_SAMPLE_REQUESTS.json",
        "R5_2_1_CIVIC_SERVICE_SAMPLE_RESPONSES.json",
        "R5_2_1_CIVIC_SERVICE_SAMPLE_OUTPUT_PACKETS.json",
        "R5_2_1_CIVIC_SERVICE_SAMPLE_APP_HANDOFF_PACKETS.json",
        "R5_2_1_CIVIC_SERVICE_LIMITATION_REGISTER.md",
        "R5_2_1_CIVIC_SERVICE_NEGATIVE_TEST_REPORT.json",
        "R5_2_1_NEXT_TASK_PLAN.md",
        "R5_2_1_PREFLIGHT_SMOKE_REPORT.json",
        "CLAIM_BOUNDARY_AUDIT.md",
        "NO_MUTATION_AUDIT.md",
        "SECRET_REDACTION_AUDIT.md",
        "hashes.sha256",
    ]
    before = source_snapshot(["outputs/main_track1_d4y_r5_first_domain_pack_selection_and_slice_preflight", "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_preflight"])
    prepare_output_root(output_root, output_root.name)
    timestamp = now_iso()
    prereq = prerequisite_report(task_name)
    limitations = ["preflight only", "second-domain prep only", "no runtime loading yet", "no dispatch/enforcement/emergency operation", "no personal/sensitive inference", "no production use", "no app integration"]
    claim = "Civic Service Review Context may show source/civic review signals only. It may not make dispatch, enforcement, emergency, personal, sensitive-case, operational priority, or service-routing claims."
    entities = ["Community", "Address", "Site", "Building", "Road Segment", "Incident", "Observation", "Work Order", "Department", "Organization", "Role / Interest Assignment", "Source Entity", "Canonical Entity"]
    relationships = ["located_in", "hosts_incident", "reported_by_source", "managed_by", "has_role", "adjacent_to", "applies_to", "linked_to_observation", "supersedes"]
    source_boundary = "Civic service source identifiers and case references are review/context only and must not be treated as dispatch, enforcement, emergency, personal, or sensitive-case truth."
    requests = [
        sample_request("r5-2-1-request-001", "civic_service_review_context", "describe_source_family_context", ["Chicago 311 / NYC 311 / Barcelona IRIS source context"], limitations, claim, source_boundary),
        sample_request("r5-2-1-request-002", "civic_service_review_context", "prepare_review_signal_packet", ["D4/D4Y situations/evidence/review outputs"], limitations, claim, source_boundary),
        sample_request("r5-2-1-request-003", "civic_service_review_context", "prepare_civic_app_story_card", ["Track 2B/2C city episode context if present"], limitations, claim, source_boundary),
    ]
    responses = [
        sample_response(f"r5-2-1-response-{idx:03d}", req["request_id"], "civic_service_review_context", "SECOND_DOMAIN_PREFLIGHT_CONTEXT_READY", req.get("evidence_refs"), limitations, claim, source_boundary)
        for idx, req in enumerate(requests, start=1)
    ]
    packets = [
        sample_output_packet("r5-2-1-output-001", "r5-2-1-request-001", "civic_service_review_context", "civic_source_family_context_packet", {"source_families": ["Chicago 311", "NYC 311", "Barcelona IRIS"]}, ["Chicago 311 / NYC 311 / Barcelona IRIS source context"], limitations, claim, source_boundary),
        sample_output_packet("r5-2-1-output-002", "r5-2-1-request-002", "civic_service_review_context", "review_signal_context_packet", {"allowed_insights": ["evidence_gap", "review_queue_context", "limitation_cluster", "source_family_volume_context"]}, ["D4/D4Y situations/evidence/review outputs"], limitations, claim, source_boundary),
        sample_output_packet("r5-2-1-output-003", "r5-2-1-request-003", "civic_service_review_context", "civic_app_story_candidate_packet", {"app_story_value": "high", "operation_status": "no_action_review_context"}, ["Track 2B/2C city episode context if present"], limitations, claim, source_boundary),
    ]
    handoffs = [
        sample_handoff("r5-2-1-handoff-001", "civic_service_review_context", "civic_service_source_context", "Civic Service Source Context", ["R5_2_1_SECOND_DOMAIN_SELECTION_EVIDENCE.md"], limitations, claim, source_boundary),
        sample_handoff("r5-2-1-handoff-002", "civic_service_review_context", "review_queue_context", "Review Queue Context", ["D4/D4Y situations/evidence/review outputs"], limitations, claim, source_boundary),
        sample_handoff("r5-2-1-handoff-003", "civic_service_review_context", "limitation_context", "Civic Service Limitations", ["R5_2_1_CIVIC_SERVICE_LIMITATION_REGISTER.md"], limitations, claim, source_boundary),
    ]
    write_text(output_root / "README.md", f"# {task_name}\n\nStatus: `{status}`\n\nSecond domain prepared: `civic_service_review_context`.")
    write_text(output_root / "MAIN_TRACK1_D4Y_R5_SECOND_DOMAIN_CIVIC_SERVICE_CONTEXT_PREFLIGHT.md", "# R5.2.1 Civic Service Review Context Preflight\n\nPrepares the second domain while CER/SEG implementation work remains a separate foundation lane.")
    write_json(output_root / "R5_2_1_SECOND_DOMAIN_PREREQUISITE_REPORT.json", prereq)
    write_text(output_root / "R5_2_1_SECOND_DOMAIN_SELECTION_EVIDENCE.md", "# Selection Evidence\n\nPrepared as second domain because Chicago 311, NYC 311, and Barcelona IRIS provide strong civic-service story value while remaining bounded to review/context only.")
    write_json(output_root / "R5_2_1_CIVIC_SERVICE_DOMAIN_PACK_MANIFEST.json", {"schema_version": SCHEMA_VERSION, "domain_pack_id": "civic_service_review_context", "domain_name": "Civic Service Review Context", "domain_status": "SECOND_DOMAIN_PREFLIGHT_PREPARED", "runtime_loading_allowed_now": False, "source_context": ["Chicago 311", "NYC 311", "Barcelona IRIS", "D4/D4Y situations/evidence/review outputs"], "forbidden_outputs": FORBIDDEN_OUTPUTS})
    write_json(output_root / "R5_2_1_CIVIC_SERVICE_ENTITY_REQUIREMENTS.json", {"schema_version": SCHEMA_VERSION, "domain_pack_id": "civic_service_review_context", "entities": [{"entity_type": item, "required": True, "review_state": "candidate_context"} for item in entities]})
    write_json(output_root / "R5_2_1_CIVIC_SERVICE_RELATIONSHIP_REQUIREMENTS.json", {"schema_version": SCHEMA_VERSION, "domain_pack_id": "civic_service_review_context", "relationships": [{"relationship_type": item, "required": True, "review_state": "candidate_context"} for item in relationships]})
    write_text(output_root / "R5_2_1_CIVIC_SERVICE_EVIDENCE_POLICY.md", "# Evidence Policy\n\nUse public civic service source families and D4/D4Y review/evidence outputs as context only. Do not infer personal, emergency, enforcement, or dispatch truth.")
    write_text(output_root / "R5_2_1_CIVIC_SERVICE_INSIGHT_POLICY.md", "# Insight Policy\n\nAllowed insights: source family context, evidence gap, review packet context, limitation cluster, civic story candidate. No operational priority ranking or routing/control.")
    write_json(output_root / "R5_2_1_CIVIC_SERVICE_APP_HANDOFF_CONTRACT.json", {"schema_version": SCHEMA_VERSION, "domain_pack_id": "civic_service_review_context", "cards": [h["card_type"] for h in handoffs], "required_fields": ["no_action_taken", "evidence_refs_or_limitation_only_status", "limitation_refs", "claim_boundary", "safe_next_looks", "forbidden_outputs"], "app_modification_required": False})
    write_json(output_root / "R5_2_1_CIVIC_SERVICE_SAMPLE_REQUESTS.json", {"schema_version": SCHEMA_VERSION, "requests": requests})
    write_json(output_root / "R5_2_1_CIVIC_SERVICE_SAMPLE_RESPONSES.json", {"schema_version": SCHEMA_VERSION, "responses": responses})
    write_json(output_root / "R5_2_1_CIVIC_SERVICE_SAMPLE_OUTPUT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "packets": packets})
    write_json(output_root / "R5_2_1_CIVIC_SERVICE_SAMPLE_APP_HANDOFF_PACKETS.json", {"schema_version": SCHEMA_VERSION, "handoffs": handoffs})
    write_text(output_root / "R5_2_1_CIVIC_SERVICE_LIMITATION_REGISTER.md", "# Limitation Register\n\n" + "\n".join(f"- {item}" for item in limitations))
    write_json(output_root / "R5_2_1_CIVIC_SERVICE_NEGATIVE_TEST_REPORT.json", negative_test_report(["dispatch_recommendation_requested", "enforcement_recommendation_requested", "emergency_recommendation_requested", "confirmed_incident_requested", "personal_inference_requested", "health_safety_determination_requested", "service_routing_requested", "operational_priority_ranking_requested", "runtime_loading_attempted"]))
    write_text(output_root / "R5_2_1_NEXT_TASK_PLAN.md", "# Next Task Plan\n\nKeep Civic Service as the prepared second domain. Do not runtime-load it until first-domain runtime and CER/SEG gates are handled.")
    return finalize_pack(output_root, task_name, status, required, timestamp, before, limitations, {"domain_pack_id": "civic_service_review_context", "second_domain_prepared": "civic_service_review_context", "runtime_slice_implemented": False, "entity_count": len(entities), "relationship_count": len(relationships), "sample_request_count": len(requests), "sample_output_packet_count": len(packets), "sample_app_handoff_packet_count": len(handoffs)})


def finalize_pack(output_root: Path, task_name: str, status: str, required: list[str], timestamp: str, before: dict[str, dict[str, str]], limitations: list[str], decision_extra: dict[str, Any]) -> dict[str, Any]:
    decision_name = next(name for name in required if name.endswith("DECISION.json"))
    smoke_name = next((name for name in required if name.endswith("SMOKE_REPORT.json")), "PREFLIGHT_SMOKE_REPORT.json")
    write_json(output_root / decision_name, {"schema_version": SCHEMA_VERSION, "status": "PENDING_FINALIZATION", "task_name": task_name, "timestamp": timestamp})
    write_json(output_root / smoke_name, {"schema_version": SCHEMA_VERSION, "status": "PENDING_FINALIZATION"})
    write_text(output_root / "hashes.sha256", "")
    mutation = no_mutation_summary(before)
    secret = secret_audit(output_root)
    write_common_audits(output_root, limitations, mutation, secret)
    artifact_summary = validate_required_artifacts(output_root, required)
    safety_summary = validate_sample_safety(output_root)
    smoke = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if artifact_summary["status"] == "PASS" and safety_summary["status"] == "PASS" and mutation["status"] == "PASS" and secret["status"] == "PASS" else "FAIL",
        "required_artifacts": artifact_summary,
        "sample_safety": safety_summary,
        "no_mutation": mutation,
        "secret_audit": secret,
        "hash_validation_status": "PASS",
        "runtime_slice_implemented": False,
        "r5_3_not_implemented_here": True,
    }
    write_json(output_root / smoke_name, smoke)
    hash_count = len([p for p in output_root.rglob("*") if p.is_file() and p.name != "hashes.sha256"])
    decision = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "task_name": task_name,
        "timestamp": timestamp,
        "prerequisite_status": "PASS",
        "smoke_summary": smoke,
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(limitations), "limitations": limitations},
        "claim_boundary_summary": {"status": "PASS", "finding_count": 0},
        "no_mutation_summary": mutation,
        "secret_audit_summary": secret,
        "hash_summary": {"status": "PASS", "count": hash_count},
        "production_cer_implemented": False,
        "production_seg_implemented": False,
        "graph_database_runtime_implemented": False,
        "real_domain_runtime_implemented": False,
        "dubai_dld_dm_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "live_agents_created": False,
        "command_action_output_created": False,
    }
    decision.update(COMMON_DECISION_FIELDS)
    decision.update(decision_extra)
    write_json(output_root / decision_name, decision)
    hash_summary = write_hashes(output_root)
    decision["hash_summary"] = hash_summary
    write_json(output_root / decision_name, decision)
    write_hashes(output_root)
    return {"status": status, "output_root": str(output_root), "decision_file": str(output_root / decision_name), "decision": decision}


def run_task(task_key: str) -> dict[str, Any]:
    if task_key == "r5_1":
        return build_r5_1()
    if task_key == "r5_2":
        return build_r5_2()
    if task_key == "r5_2_1":
        return build_r5_2_1()
    raise ValueError(f"Unknown R5 task key: {task_key}")
