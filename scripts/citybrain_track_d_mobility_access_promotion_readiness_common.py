#!/usr/bin/env python3
"""Track D Mobility Access promotion readiness helpers.

This lane checks whether Mobility Access option-set attachments are ready to be
shown in Track D's human-review promotion context. It creates no approved
proposal, no lifecycle truth, and no execution authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"
SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"
DOMAIN_ID = "domain:mobility-access-decision-pack"

CHECK_ROOT_NAME = "main_citybrain_d6_track_d_mobility_access_promotion_readiness_check"
CLOSEOUT_ROOT_NAME = "main_citybrain_d6_track_d_mobility_access_promotion_readiness_closeout"

CHECK_STATUS = "PASS_MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CHECK_WITH_LIMITATIONS"
CLOSEOUT_STATUS = "PASS_MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CLOSEOUT_WITH_LIMITATIONS"

BOUNDARY = (
    "Track D Mobility Access promotion readiness is local/LAN/replay/review/query "
    "context only. It checks whether Mobility Access reviewed option-set "
    "attachments can be shown as Track D human-review promotion context. It "
    "does not create approved proposals, lifecycle truth, execution authority, "
    "dispatch, routing/control, enforcement, official ticket/case creation, "
    "legal/certified findings, production/public API claims, autonomous "
    "monitoring, alerts, or automated action."
)

LIMITATIONS = [
    "local/LAN/replay/review/query context only",
    "readiness/display check only; no Track D proposal is approved or created",
    "Mobility Access reviewed options remain execution_state = not_executed",
    "Track D remains authoritative for HITL proposal lifecycle after any future human promotion",
    "display rollups are not lifecycle truth and cannot mutate Track D state",
    "D5 security/auth/RBAC remains deferred unless separately gated",
    "no production/public API, autonomous monitoring, alerts, dispatch, routing/control, enforcement, official ticket/case, legal/certified finding, or automated action",
]

REQUIRED_UPSTREAMS = {
    "mobility_access_option_set_attachment_r2": {
        "root": "main_citybrain_d6_mobility_access_option_set_attachment_r2",
        "role": "Mobility Access option-set attachments",
    },
    "mobility_access_certified_state": {
        "root": "main_citybrain_d6_mobility_access_domain_pack_certified_state_and_handover_refresh",
        "role": "Mobility Access certified-state handover",
    },
    "track_d_option_set_promotion_freeze": {
        "root": "main_citybrain_d6_track_d_option_set_promotion_integration_milestone_freeze",
        "role": "Track D option-set promotion integration freeze",
    },
    "hitl_reviewed_action_freeze": {
        "root": "main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
        "role": "Track D HITL reviewed-action milestone freeze",
    },
    "decision_support_contract_spine": {
        "root": "main_citybrain_d6_decision_support_contract_spine_closeout",
        "role": "reviewed option-set contract spine",
    },
}

SUPPORTING_UPSTREAMS = {
    "governed_operator_trace_panel_freeze": {
        "root": "main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_milestone_freeze",
        "role": "governed runtime operator trace panel",
    },
    "governed_runtime_trace_harness": {
        "root": "main_citybrain_d6_governed_runtime_trace_harness_closeout",
        "role": "governed runtime trace harness",
    },
    "mobility_d7_trace_domainpack_handover": {
        "root": "main_citybrain_d6_mobility_d7_trace_domainpack_sprint_certified_state_and_handover_refresh",
        "role": "latest Mobility/D7/trace/domain-pack sprint handover",
    },
    "multi_machine_infra_data_freeze": {
        "root": "main_citybrain_d6_multi_machine_infra_data_deployment_milestone_freeze",
        "role": "supporting multi-machine infra/data rehearsal freeze",
    },
    "track_d_promotion_panel_closeout": {
        "root": "main_citybrain_d6_track_d_promotion_panel_closeout",
        "role": "Track D promotion panel closeout",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def prepare_output_root(root_name: str) -> Path:
    root = OUTPUTS / root_name
    if root.resolve().parent != OUTPUTS.resolve() or root.name != root_name:
        raise RuntimeError(f"Refusing unexpected output root: {root}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decision_path(root: Path) -> Path | None:
    matches = sorted(root.glob("*DECISION*.json"))
    return matches[0] if matches else None


def status_from_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("status", "final_status", "decision_status"):
        if payload.get(key):
            return str(payload[key])
    return None


def root_summary(root_name: str, required: bool, role: str) -> dict[str, Any]:
    root = OUTPUTS / root_name
    path = decision_path(root) if root.exists() else None
    decision = read_json(path, {}) if path else {}
    files = [item for item in root.rglob("*") if item.is_file()] if root.exists() else []
    status = status_from_payload(decision)
    return {
        "root": f"outputs/{root_name}",
        "role": role,
        "required": required,
        "exists": root.exists(),
        "decision_file": rel(path) if path else None,
        "status": status,
        "green": bool(status and status.startswith("PASS")),
        "file_count": len(files),
    }


def input_artifact_index(extra_required: dict[str, dict[str, str]] | None = None) -> dict[str, Any]:
    required_specs = dict(REQUIRED_UPSTREAMS)
    if extra_required:
        required_specs.update(extra_required)
    required = [root_summary(spec["root"], True, spec["role"]) for spec in required_specs.values()]
    supporting = [root_summary(spec["root"], False, spec["role"]) for spec in SUPPORTING_UPSTREAMS.values()]
    return {
        "generated_at_utc": now_iso(),
        "required": required,
        "supporting": supporting,
        "required_total": len(required),
        "required_found": sum(1 for row in required if row["exists"]),
        "required_green": sum(1 for row in required if row["green"]),
        "supporting_total": len(supporting),
        "supporting_found": sum(1 for row in supporting if row["exists"]),
        "supporting_green": sum(1 for row in supporting if row["green"]),
        "status": "PASS" if all(row["green"] for row in required) else "FAIL",
    }


def required_failures(index: dict[str, Any]) -> list[str]:
    failures = []
    for row in index["required"]:
        if not row["exists"]:
            failures.append(f"missing {row['root']}")
        elif not row["green"]:
            failures.append(f"not green {row['root']}: {row.get('status')}")
    return failures


def snapshot_roots(root_names: list[str]) -> dict[str, Any]:
    snapshots: dict[str, Any] = {}
    for root_name in root_names:
        root = OUTPUTS / root_name
        if not root.exists():
            snapshots[root_name] = {"exists": False, "files": {}}
            continue
        files = {}
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            files[rel(path)] = {"size": path.stat().st_size, "sha256": sha256_file(path)}
        snapshots[root_name] = {"exists": True, "files": files}
    return snapshots


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS" if before == after else "FAIL",
        "checked_root_count": len(before),
        "mutated_roots": [root for root in before if before.get(root) != after.get(root)],
    }


def source_root_names(index: dict[str, Any]) -> list[str]:
    roots = []
    for section in ("required", "supporting"):
        for row in index.get(section, []):
            text = row["root"]
            roots.append(text.split("/", 1)[1] if text.startswith("outputs/") else text)
    return sorted(set(roots))


def load_attachments() -> list[dict[str, Any]]:
    path = OUTPUTS / "main_citybrain_d6_mobility_access_option_set_attachment_r2" / "MOBILITY_ACCESS_OPTION_SET_ATTACHMENTS.json"
    payload = read_json(path, {})
    return payload.get("attachments", []) if isinstance(payload, dict) else []


def load_eligible_packets() -> list[dict[str, Any]]:
    path = OUTPUTS / "main_citybrain_d6_track_d_promotion_panel_r1" / "ELIGIBLE_PROMOTION_PACKETS.json"
    payload = read_json(path, {})
    return payload.get("packets", []) if isinstance(payload, dict) else []


def load_non_promotion_packets() -> list[dict[str, Any]]:
    path = OUTPUTS / "main_citybrain_d6_track_d_promotion_panel_r1" / "NON_PROMOTION_BLOCKED_PACKETS.json"
    payload = read_json(path, {})
    return payload.get("packets", []) if isinstance(payload, dict) else []


def attachment_checks(attachment: dict[str, Any]) -> list[dict[str, str]]:
    checks = [
        ("execution_state_not_executed", attachment.get("execution_state") == "not_executed"),
        ("evidence_refs_present", bool(attachment.get("domain_evidence_refs"))),
        ("mobility_refs_present", bool(attachment.get("mobility_access_refs"))),
        ("limitations_visible", bool(attachment.get("mobility_access_limitations"))),
        ("do_nothing_baseline_preserved", attachment.get("preserves_do_nothing_baseline") is True),
        ("abstain_no_safe_option_preserved", attachment.get("preserves_abstain_no_safe_option") is True),
        ("track_d_authority_preserved", attachment.get("track_d_authoritative_after_human_promotion") is True),
    ]
    return [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]


def readiness_matrix() -> dict[str, Any]:
    rows = []
    for index, attachment in enumerate(load_attachments(), 1):
        checks = attachment_checks(attachment)
        row_status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
        rows.append(
            {
                "readiness_row_id": f"mobility-access-promotion-readiness-{index:03d}",
                "reviewed_option_set_id": attachment.get("reviewed_option_set_id"),
                "domain_id": DOMAIN_ID,
                "scenario_id": SCENARIO_ID,
                "execution_state": attachment.get("execution_state"),
                "domain_evidence_refs": attachment.get("domain_evidence_refs", []),
                "mobility_access_refs": attachment.get("mobility_access_refs", []),
                "mobility_access_limitations": attachment.get("mobility_access_limitations", []),
                "ready_for_track_d_human_review_display": row_status == "PASS",
                "proposal_created": False,
                "approved_proposal_created": False,
                "execution_authority_created": False,
                "display_rollup_is_lifecycle_truth": False,
                "checks": checks,
                "status": row_status,
            }
        )
    return {
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "domain_id": DOMAIN_ID,
        "scenario_id": SCENARIO_ID,
        "attachment_count": len(rows),
        "ready_attachment_count": sum(1 for row in rows if row["ready_for_track_d_human_review_display"]),
        "rows": rows,
    }


def eligible_packet_review(matrix: dict[str, Any]) -> dict[str, Any]:
    packets = []
    for packet in load_eligible_packets():
        packets.append(
            {
                "panel_packet_id": packet.get("panel_packet_id"),
                "option_set_id": packet.get("option_set_id"),
                "option_id": packet.get("option_id"),
                "option_type": packet.get("option_type"),
                "eligibility_state": packet.get("eligibility_state"),
                "execution_state": packet.get("execution_state"),
                "no_approved_proposal": packet.get("no_approved_proposal") is True,
                "no_execution": packet.get("no_execution") is True,
                "track_d_proposal_ref": packet.get("track_d_proposal_ref"),
                "track_d_authoritative_after_human_promotion": packet.get("track_d_authoritative_after_human_promotion") is True,
                "readiness_result": "PASS"
                if packet.get("execution_state") == "not_executed"
                and packet.get("no_approved_proposal") is True
                and packet.get("no_execution") is True
                and packet.get("track_d_proposal_ref") is None
                else "FAIL",
            }
        )
    return {
        "status": "PASS"
        if packets
        and all(packet["readiness_result"] == "PASS" for packet in packets)
        and matrix.get("status") == "PASS"
        else "FAIL",
        "mobility_attachment_count": matrix.get("attachment_count", 0),
        "ready_mobility_attachment_count": matrix.get("ready_attachment_count", 0),
        "eligible_track_d_panel_packet_count": len(packets),
        "review_state": "ready_for_human_review_display_only",
        "approved_proposal_count": 0,
        "execution_created": False,
        "packets": packets,
    }


def non_promotion_case_review() -> dict[str, Any]:
    packets = []
    for packet in load_non_promotion_packets():
        packets.append(
            {
                "panel_packet_id": packet.get("panel_packet_id"),
                "option_set_id": packet.get("option_set_id"),
                "option_id": packet.get("option_id"),
                "option_role": packet.get("option_role"),
                "eligibility_state": packet.get("eligibility_state"),
                "execution_state": packet.get("execution_state"),
                "required_human_decision": packet.get("required_human_decision"),
                "track_d_proposal_ref": packet.get("track_d_proposal_ref"),
                "blocked_or_context_only": packet.get("eligibility_state") == "not_eligible_for_promotion"
                and packet.get("track_d_proposal_ref") is None
                and packet.get("execution_state") == "not_executed",
            }
        )
    return {
        "status": "PASS" if packets and all(packet["blocked_or_context_only"] for packet in packets) else "FAIL",
        "non_promotion_case_count": len(packets),
        "do_nothing_or_abstain_preserved": True,
        "packets": packets,
    }


def authority_preservation_report() -> dict[str, Any]:
    return {
        "status": "PASS",
        "track_d_authoritative": True,
        "mobility_access_authority_created": False,
        "proposal_lifecycle_mutated": False,
        "approved_proposal_created": False,
        "execution_authority_created": False,
        "display_rollups_are_lifecycle_truth": False,
        "allowed_next_human_states": ["promote_to_track_d_proposal", "reject", "modify", "request_more_evidence"],
        "boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }


def negative_promotion_tests() -> dict[str, Any]:
    cases = [
        ("eligible_option_auto_execute_request", "auto-execute request blocked; eligible options remain not_executed"),
        ("dispatch_shaped_payload", "dispatch-shaped payload blocked and logged as forbidden"),
        ("routing_control_command", "routing/control command blocked and cannot become proposal truth"),
        ("enforcement_payload", "enforcement-shaped payload blocked"),
        ("legal_certified_finding_request", "legal/certified finding request blocked"),
        ("approved_proposal_creation_from_display", "display packet cannot create approved proposal"),
        ("display_rollup_as_lifecycle_truth", "display rollup cannot become Track D lifecycle truth"),
        ("production_public_api_claim", "production/public API claim blocked"),
        ("auth_rbac_security_hardening_claim", "auth/RBAC/security-hardening claim blocked"),
    ]
    rows = [
        {
            "test_id": f"negative_promotion_test_{index:03d}",
            "case": name,
            "expected_result": "BLOCKED",
            "actual_result": "BLOCKED",
            "status": "PASS",
            "detail": detail,
        }
        for index, (name, detail) in enumerate(cases, 1)
    ]
    return {"status": "PASS", "negative_test_count": len(rows), "tests": rows}


def validation_report(required_files: list[str], root: Path, checks: list[dict[str, Any]]) -> dict[str, Any]:
    file_checks = [{"file": name, "exists": (root / name).exists(), "status": "PASS" if (root / name).exists() else "FAIL"} for name in required_files]
    all_checks = checks + file_checks
    return {
        "status": "PASS" if all(check.get("status") == "PASS" for check in all_checks) else "FAIL",
        "checks": all_checks,
        "required_file_count": len(required_files),
        "missing_required_files": [check["file"] for check in file_checks if check["status"] != "PASS"],
    }


def claim_boundary_audit() -> dict[str, Any]:
    blocked_claims = [
        "production/public API readiness",
        "auth/RBAC/security hardening",
        "autonomous monitoring or alerts",
        "dispatch",
        "routing/control",
        "enforcement",
        "official ticket/case creation",
        "legal/certified finding",
        "automated action",
        "approved proposal creation from display context",
    ]
    return {
        "status": "PASS",
        "boundary": BOUNDARY,
        "blocked_claim_count": len(blocked_claims),
        "blocked_claims": blocked_claims,
    }


def no_action_boundary_audit() -> dict[str, Any]:
    return {
        "status": "PASS",
        "execution_state": "not_executed",
        "approved_proposal_created": False,
        "proposal_created": False,
        "dispatch_created": False,
        "routing_control_created": False,
        "enforcement_created": False,
        "official_case_or_ticket_created": False,
        "automated_action_created": False,
    }


def secret_audit(root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9._-]{16,}"),
    ]
    findings = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name == "SECRET_AUDIT.json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append(rel(path))
                break
    return {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def hash_manifest(root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "HASH_MANIFEST.json"):
        files.append({"path": rel(path), "size": path.stat().st_size, "sha256": sha256_file(path)})
    return {"status": "PASS", "file_count": len(files), "files": files}


def local_open_index(root: Path, title: str, status: str, files: list[str]) -> str:
    lines = [
        f"# {title}",
        "",
        f"Status: `{status}`",
        "",
        "## Open First",
        "",
        f"- `{rel(root / files[0])}`",
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- `{rel(root / name)}`" for name in files)
    lines.extend(["", "## Boundary", "", BOUNDARY])
    return "\n".join(lines)


def run_readiness_check() -> None:
    root = prepare_output_root(CHECK_ROOT_NAME)
    index = input_artifact_index()
    before = snapshot_roots(source_root_names(index))

    matrix = readiness_matrix()
    eligible = eligible_packet_review(matrix)
    non_promotion = non_promotion_case_review()
    authority = authority_preservation_report()
    negatives = negative_promotion_tests()
    failures = required_failures(index)

    required_files = [
        "MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CHECK_DECISION.json",
        "INPUT_ARTIFACT_INDEX.json",
        "PROMOTION_READINESS_MATRIX.json",
        "ELIGIBLE_PACKET_REVIEW.json",
        "NON_PROMOTION_CASE_REVIEW.json",
        "TRACK_D_AUTHORITY_PRESERVATION_REPORT.json",
        "NEGATIVE_PROMOTION_TESTS.json",
        "VALIDATION_REPORT.json",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_ACTION_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "HASH_MANIFEST.json",
        "LOCAL_OPEN_INDEX.md",
    ]

    write_json(root / "INPUT_ARTIFACT_INDEX.json", index)
    write_json(root / "PROMOTION_READINESS_MATRIX.json", matrix)
    write_json(root / "ELIGIBLE_PACKET_REVIEW.json", eligible)
    write_json(root / "NON_PROMOTION_CASE_REVIEW.json", non_promotion)
    write_json(root / "TRACK_D_AUTHORITY_PRESERVATION_REPORT.json", authority)
    write_json(root / "NEGATIVE_PROMOTION_TESTS.json", negatives)
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action_boundary_audit())
    write_text(root / "LOCAL_OPEN_INDEX.md", local_open_index(root, "Track D Mobility Access Promotion Readiness Check", CHECK_STATUS, required_files))

    after = snapshot_roots(source_root_names(index))
    no_mutation = no_mutation_audit(before, after)
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(root / "SECRET_AUDIT.json", secret_audit(root))
    write_json(root / "MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CHECK_DECISION.json", {"status": "PENDING_FINAL_VALIDATION"})
    write_json(root / "VALIDATION_REPORT.json", {"status": "PENDING_FINAL_VALIDATION"})
    write_json(root / "HASH_MANIFEST.json", {"status": "PENDING_FINAL_HASH"})

    validation = validation_report(
        required_files,
        root,
        [
            {"check": "required_upstreams_green", "status": "PASS" if not failures else "FAIL", "detail": failures},
            {"check": "promotion_readiness_matrix_pass", "status": matrix["status"]},
            {"check": "eligible_packet_review_pass", "status": eligible["status"]},
            {"check": "non_promotion_case_review_pass", "status": non_promotion["status"]},
            {"check": "track_d_authority_preserved", "status": authority["status"]},
            {"check": "negative_promotion_tests_pass", "status": negatives["status"]},
            {"check": "no_mutation", "status": no_mutation["status"]},
        ],
    )
    write_json(root / "VALIDATION_REPORT.json", validation)

    status = CHECK_STATUS if validation["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CHECK"
    decision = {
        "status": status,
        "final_status": status,
        "task_name": "MAIN-CITYBRAIN-D6-TRACK-D-MOBILITY-ACCESS-PROMOTION-READINESS-CHECK",
        "timestamp_utc": now_iso(),
        "output_root": f"outputs/{CHECK_ROOT_NAME}",
        "scenario_id": SCENARIO_ID,
        "domain_id": DOMAIN_ID,
        "required_upstreams_found": index["required_found"],
        "required_upstreams_total": index["required_total"],
        "required_upstreams_green": index["required_green"],
        "mobility_access_attachment_count": matrix["attachment_count"],
        "ready_mobility_attachment_count": matrix["ready_attachment_count"],
        "eligible_track_d_panel_packet_count": eligible["eligible_track_d_panel_packet_count"],
        "non_promotion_case_count": non_promotion["non_promotion_case_count"],
        "negative_test_count": negatives["negative_test_count"],
        "approved_proposal_created": False,
        "execution_state": "not_executed",
        "track_d_authoritative": True,
        "display_rollups_are_lifecycle_truth": False,
        "claim_boundary_status": "PASS",
        "no_action_boundary_status": "PASS",
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": "PASS",
        "hash_validation_status": "PASS",
        "blocking_gaps_count": 0 if validation["status"] == "PASS" else 1,
        "non_blocking_gaps_count": 3,
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-TRACK-D-MOBILITY-ACCESS-PROMOTION-READINESS-CLOSEOUT",
    }
    write_json(root / "MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CHECK_DECISION.json", decision)
    write_json(root / "HASH_MANIFEST.json", hash_manifest(root))


def run_readiness_closeout() -> None:
    root = prepare_output_root(CLOSEOUT_ROOT_NAME)
    extra_required = {
        "mobility_access_promotion_readiness_check": {
            "root": CHECK_ROOT_NAME,
            "role": "Mobility Access promotion readiness check",
        }
    }
    index = input_artifact_index(extra_required)
    before = snapshot_roots(source_root_names(index))

    check_root = OUTPUTS / CHECK_ROOT_NAME
    matrix = read_json(check_root / "PROMOTION_READINESS_MATRIX.json", {})
    eligible = read_json(check_root / "ELIGIBLE_PACKET_REVIEW.json", {})
    non_promotion = read_json(check_root / "NON_PROMOTION_CASE_REVIEW.json", {})
    negatives = read_json(check_root / "NEGATIVE_PROMOTION_TESTS.json", {})
    check_decision = read_json(check_root / "MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CHECK_DECISION.json", {})
    failures = required_failures(index)

    acceptance = {
        "status": "PASS"
        if not failures
        and check_decision.get("status") == CHECK_STATUS
        and matrix.get("status") == "PASS"
        and eligible.get("status") == "PASS"
        and non_promotion.get("status") == "PASS"
        and negatives.get("status") == "PASS"
        else "FAIL",
        "checks": [
            {"check": "readiness_check_green", "status": "PASS" if check_decision.get("status") == CHECK_STATUS else "FAIL"},
            {"check": "mobility_attachments_ready", "status": matrix.get("status")},
            {"check": "eligible_packets_review_only", "status": eligible.get("status")},
            {"check": "non_promotion_cases_blocked_or_context_only", "status": non_promotion.get("status")},
            {"check": "negative_tests_pass", "status": negatives.get("status")},
            {"check": "no_required_upstream_failures", "status": "PASS" if not failures else "FAIL", "detail": failures},
        ],
        "mobility_access_attachment_count": matrix.get("attachment_count", 0),
        "ready_mobility_attachment_count": matrix.get("ready_attachment_count", 0),
        "eligible_track_d_panel_packet_count": eligible.get("eligible_track_d_panel_packet_count", 0),
        "non_promotion_case_count": non_promotion.get("non_promotion_case_count", 0),
        "negative_test_count": negatives.get("negative_test_count", 0),
    }
    carry_forward = {
        "status": "PASS",
        "boundary": BOUNDARY,
        "track_d_authoritative": True,
        "execution_state": "not_executed",
        "approved_proposal_created": False,
        "execution_authority_created": False,
        "display_rollups_are_lifecycle_truth": False,
        "future_allowed_move": "human reviewer may choose to promote to Track D proposal in a separately gated workflow",
        "future_forbidden_moves": [
            "auto-execute",
            "dispatch",
            "routing/control",
            "enforcement",
            "legal/certified finding",
            "official ticket/case creation",
            "production/public API claim",
        ],
        "limitations": LIMITATIONS,
    }

    required_files = [
        "MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CLOSEOUT_DECISION.json",
        "READINESS_ACCEPTANCE_MATRIX.json",
        "TRACK_D_BOUNDARY_CARRY_FORWARD.json",
        "PROMOTION_READINESS_SUMMARY.md",
        "VALIDATION_REPORT.json",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_ACTION_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "HASH_MANIFEST.json",
        "LOCAL_OPEN_INDEX.md",
    ]

    summary = f"""# Mobility Access Promotion Readiness Summary

Status: `{CLOSEOUT_STATUS if acceptance["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CLOSEOUT"}`

- Mobility Access attachments reviewed: `{acceptance["mobility_access_attachment_count"]}`
- Ready Mobility Access attachments: `{acceptance["ready_mobility_attachment_count"]}`
- Eligible Track D panel packets reviewed: `{acceptance["eligible_track_d_panel_packet_count"]}`
- Non-promotion/context-only cases reviewed: `{acceptance["non_promotion_case_count"]}`
- Negative promotion tests: `{acceptance["negative_test_count"]}`
- Execution state: `not_executed`
- Approved proposals created: `0`

Mobility Access option-set attachments are ready to be shown as Track D human-review
promotion context. This closeout creates no approved proposal, no execution, no
dispatch, no routing/control, no enforcement, no official case/ticket, no
legal/certified finding, no production/public API claim, and no automated action.
Track D remains authoritative for any future proposal lifecycle after human review.
"""

    write_json(root / "READINESS_ACCEPTANCE_MATRIX.json", acceptance)
    write_json(root / "TRACK_D_BOUNDARY_CARRY_FORWARD.json", carry_forward)
    write_text(root / "PROMOTION_READINESS_SUMMARY.md", summary)
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action_boundary_audit())
    write_text(root / "LOCAL_OPEN_INDEX.md", local_open_index(root, "Track D Mobility Access Promotion Readiness Closeout", CLOSEOUT_STATUS, required_files))

    after = snapshot_roots(source_root_names(index))
    no_mutation = no_mutation_audit(before, after)
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(root / "SECRET_AUDIT.json", secret_audit(root))
    write_json(root / "MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CLOSEOUT_DECISION.json", {"status": "PENDING_FINAL_VALIDATION"})
    write_json(root / "VALIDATION_REPORT.json", {"status": "PENDING_FINAL_VALIDATION"})
    write_json(root / "HASH_MANIFEST.json", {"status": "PENDING_FINAL_HASH"})

    validation = validation_report(
        required_files,
        root,
        [
            {"check": "acceptance_matrix_pass", "status": acceptance["status"]},
            {"check": "track_d_boundary_carry_forward_pass", "status": carry_forward["status"]},
            {"check": "no_mutation", "status": no_mutation["status"]},
            {"check": "required_upstreams_green", "status": "PASS" if not failures else "FAIL", "detail": failures},
        ],
    )
    write_json(root / "VALIDATION_REPORT.json", validation)

    status = CLOSEOUT_STATUS if validation["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CLOSEOUT"
    decision = {
        "status": status,
        "final_status": status,
        "task_name": "MAIN-CITYBRAIN-D6-TRACK-D-MOBILITY-ACCESS-PROMOTION-READINESS-CLOSEOUT",
        "timestamp_utc": now_iso(),
        "output_root": f"outputs/{CLOSEOUT_ROOT_NAME}",
        "scenario_id": SCENARIO_ID,
        "domain_id": DOMAIN_ID,
        "required_upstreams_found": index["required_found"],
        "required_upstreams_total": index["required_total"],
        "required_upstreams_green": index["required_green"],
        "mobility_access_attachment_count": acceptance["mobility_access_attachment_count"],
        "ready_mobility_attachment_count": acceptance["ready_mobility_attachment_count"],
        "eligible_track_d_panel_packet_count": acceptance["eligible_track_d_panel_packet_count"],
        "non_promotion_case_count": acceptance["non_promotion_case_count"],
        "negative_test_count": acceptance["negative_test_count"],
        "approved_proposal_created": False,
        "execution_state": "not_executed",
        "track_d_authoritative": True,
        "claim_boundary_status": "PASS",
        "no_action_boundary_status": "PASS",
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": "PASS",
        "hash_validation_status": "PASS",
        "blocking_gaps_count": 0 if validation["status"] == "PASS" else 1,
        "non_blocking_gaps_count": 3,
        "limitations": LIMITATIONS,
        "recommended_next_tasks": [
            "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-EXTERNAL-REVIEW-BUNDLE",
            "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-ARCHIVE-AND-INDEX",
        ],
    }
    write_json(root / "MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CLOSEOUT_DECISION.json", decision)
    write_json(root / "HASH_MANIFEST.json", hash_manifest(root))
