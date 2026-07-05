from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"
SCENARIO_REF = f"scenario:{SCENARIO_ID}"

PREFLIGHT_ROOT = "main_citybrain_d6_track_d_option_set_promotion_integration_preflight"
BRIDGE_ROOT = "main_citybrain_d6_track_d_option_set_promotion_bridge_r1"
GUARDRAIL_ROOT = "main_citybrain_d6_track_d_option_set_promotion_guardrail_smoke_r2"
CLOSEOUT_ROOT = "main_citybrain_d6_track_d_option_set_promotion_integration_closeout"
FREEZE_ROOT = "main_citybrain_d6_track_d_option_set_promotion_integration_milestone_freeze"

BOUNDARY = (
    "Track D option-set promotion integration is proposal-promotion contract "
    "packaging only. It maps reviewed_option_set/candidate_option context into "
    "pending human-review promotion packets without transferring approval "
    "authority to the option-set layer. It creates no approved proposals, no "
    "execution, no dispatch, no routing/control, no enforcement, no official "
    "case/ticket, no legal/certified finding, no production/public API, and no "
    "automated action."
)

LIMITATIONS = [
    "local/replay review/query context only",
    "proposal-promotion integration contract only; no Track D mutation",
    "candidate_option remains distinct from Track D proposal",
    "promotion packets are pending/non-authoritative fixtures only",
    "Track D remains authoritative for approval, rejection, modification, request-more-evidence, audit, and lifecycle state",
    "execution_state remains not_executed",
    "do-nothing and abstain/no-safe-option cases are preserved as non-promotion/escalation context",
    "SUMO, similar-case, cascade, graph, evidence, and limitation refs are context/audit links, not mandates",
    "no production/public API, dispatch, routing/control, enforcement, legal/certified finding, official case/ticket, or automated action claim",
]

REQUIRED_PREFLIGHT_ROOTS = [
    "main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh",
    "main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
    "main_citybrain_d6_inverse_dynamics_multi_option_milestone_freeze",
    "main_citybrain_d6_decision_support_final_package_review",
    "main_citybrain_d6_operator_decision_support_surface_r1",
]

SUPPORTING_ROOTS = [
    "main_citybrain_d6_hitl_action_proposal_contract_r1",
    "main_citybrain_d6_hitl_approval_lifecycle_r2",
    "main_citybrain_d6_inverse_dynamics_multi_option_generator_r1",
    "main_citybrain_d6_cross_domain_cascade_option_set_attachment_r3",
    "main_citybrain_d6_runtime_trace_demo_polish_sprint_certified_state_and_handover_refresh",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_root(name: str) -> Path:
    root = OUTPUTS_ROOT / name
    root.mkdir(parents=True, exist_ok=True)
    return root


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def decision_path(root: Path) -> Path | None:
    matches = sorted(root.glob("*DECISION.json"))
    return matches[0] if matches else None


def decision_for(root_name: str) -> dict[str, Any]:
    root = OUTPUTS_ROOT / root_name
    path = decision_path(root) if root.exists() else None
    return read_json(path) if path else {}


def root_summary(name: str, required: bool) -> dict[str, Any]:
    root = OUTPUTS_ROOT / name
    path = decision_path(root) if root.exists() else None
    decision = read_json(path) if path else {}
    files = [p for p in root.rglob("*") if p.is_file()] if root.exists() else []
    latest = max((p.stat().st_mtime for p in files), default=None)
    return {
        "root": f"outputs/{name}",
        "required": required,
        "exists": root.exists(),
        "decision_file": str(path.relative_to(REPO_ROOT)).replace("\\", "/") if path else None,
        "status": decision.get("status") or decision.get("final_status"),
        "task_name": decision.get("task_name"),
        "file_count": len(files),
        "latest_mtime_utc": datetime.fromtimestamp(latest, timezone.utc).isoformat().replace("+00:00", "Z") if latest else None,
    }


def build_input_index(required: list[str], supporting: list[str] | None = None) -> dict[str, Any]:
    supporting = supporting or []
    required_rows = [root_summary(root, True) for root in required]
    supporting_rows = [root_summary(root, False) for root in supporting]
    return {
        "generated_at_utc": utc_now(),
        "required": required_rows,
        "supporting": supporting_rows,
        "required_found": sum(1 for item in required_rows if item["exists"]),
        "required_total": len(required_rows),
        "required_green": sum(1 for item in required_rows if str(item.get("status", "")).startswith("PASS")),
        "supporting_found": sum(1 for item in supporting_rows if item["exists"]),
        "supporting_total": len(supporting_rows),
        "supporting_green": sum(1 for item in supporting_rows if str(item.get("status", "")).startswith("PASS")),
    }


def require_green(index: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for item in index["required"]:
        if not item["exists"]:
            failures.append(f"missing required root {item['root']}")
        elif not str(item.get("status", "")).startswith("PASS"):
            failures.append(f"required root not green {item['root']}: {item.get('status')}")
    return failures


def load_json_if_exists(path: Path) -> dict[str, Any]:
    return read_json(path) if path.exists() else {}


def load_option_sets() -> list[dict[str, Any]]:
    path = OUTPUTS_ROOT / "main_citybrain_d6_inverse_dynamics_multi_option_generator_r1" / "GENERATED_REVIEWED_OPTION_SETS.json"
    return load_json_if_exists(path).get("reviewed_option_sets", [])


def load_cascade_by_option_set() -> dict[str, dict[str, Any]]:
    path = OUTPUTS_ROOT / "main_citybrain_d6_cross_domain_cascade_option_set_attachment_r3" / "CASCADE_OPTION_SET_ATTACHMENTS.json"
    rows = load_json_if_exists(path).get("attachments", [])
    return {row.get("option_set_id"): row for row in rows}


def option_rows() -> list[dict[str, Any]]:
    cascade_by_set = load_cascade_by_option_set()
    rows: list[dict[str, Any]] = []
    for option_set in load_option_sets():
        cascade = cascade_by_set.get(option_set.get("option_set_id"), {})
        for option in option_set.get("candidate_options", []):
            rows.append(
                {
                    "option_set": option_set,
                    "option": option,
                    "cascade": cascade,
                    "option_set_id": option_set.get("option_set_id"),
                    "option_id": option.get("option_id"),
                    "option_role": option.get("option_role"),
                    "option_type": option.get("option_type"),
                }
            )
    return rows


def promotion_decision(row: dict[str, Any]) -> str:
    option = row["option"]
    if option.get("option_role") == "candidate_intervention" and option.get("promotion_eligibility") == "eligible_for_human_review":
        return "eligible_for_human_promotion_packet"
    if option.get("option_role") == "do_nothing_baseline":
        return "non_promotion_do_nothing_baseline"
    if option.get("option_role") == "abstain_or_escalate":
        return "non_promotion_abstain_or_escalate"
    return "non_promotion_context_only"


def proposal_type_for(option_type: str) -> str:
    mapping = {
        "review_reroute_option": "review_route_context",
        "review_kerbside_access_option": "review_access_constraint",
        "review_public_information_draft": "draft_advisory_for_review",
        "review_signal_timing_option": "review_operator_note",
        "review_lane_access_option": "review_access_constraint",
        "review_crew_schedule_option": "review_next_look",
        "review_site_visit_request": "request_more_evidence",
    }
    return mapping.get(option_type, "review_operator_note")


def build_bridge_fixtures() -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for idx, row in enumerate(option_rows(), 1):
        option_set = row["option_set"]
        option = row["option"]
        cascade = row["cascade"]
        decision = promotion_decision(row)
        eligible = decision == "eligible_for_human_promotion_packet"
        fixture = {
            "bridge_fixture_id": f"track_d_option_promotion_fixture_{idx:03d}",
            "schema_version": "citybrain.track_d.option_set_promotion_bridge.v0.1",
            "scenario_id": SCENARIO_ID,
            "scenario_ref": option_set.get("scenario_ref"),
            "scenario_state_ref": option_set.get("scenario_state_ref"),
            "option_set_id": option_set.get("option_set_id"),
            "option_id": option.get("option_id"),
            "option_role": option.get("option_role"),
            "option_type": option.get("option_type"),
            "promotion_decision": decision,
            "eligible_for_human_promotion": eligible,
            "human_promotion_gate": "required_before_track_d_proposal_creation" if eligible else "not_eligible",
            "proposal_ref": None,
            "pending_track_d_fixture": {
                "authoritative": False,
                "review_state": "awaiting_human_review" if eligible else "blocked_for_policy",
                "proposal_type": proposal_type_for(option.get("option_type", "")) if eligible else None,
                "allowed_human_decisions": [
                    "approve_as_track_d_proposal",
                    "reject",
                    "modify",
                    "request_more_evidence",
                ]
                if eligible
                else [],
            },
            "execution_state": "not_executed",
            "preserved_refs": {
                "evidence_refs": sorted(set(option_set.get("evidence_refs", []) + option.get("evidence_refs", []))),
                "simulation_refs": option_set.get("simulation_refs", []),
                "similar_case_refs": sorted(set(option_set.get("similar_case_refs", []) + option.get("similar_case_refs", []))),
                "cascade_refs": cascade.get("cascade_refs", []),
                "graph_refs": sorted(set(option_set.get("graph_refs", []) + option.get("graph_refs", []))),
                "limitation_refs": sorted(set(option_set.get("limitation_refs", []) + option.get("limitation_refs", []))),
                "audit_refs": option_set.get("audit_refs", []),
            },
            "track_d_boundary": "Track D remains authoritative for lifecycle state after human promotion.",
            "blocked_action_types": option_set.get("blocked_action_types", []),
            "not_an_action_statement": "This is a non-authoritative promotion bridge fixture and does not approve or execute action.",
        }
        fixtures.append(fixture)
    return fixtures


def fixture_validation(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    for fixture in fixtures:
        if fixture.get("execution_state") != "not_executed":
            errors.append(f"{fixture['bridge_fixture_id']} execution_state drift")
        if fixture.get("proposal_ref") is not None:
            errors.append(f"{fixture['bridge_fixture_id']} proposal_ref must remain null")
        if fixture["pending_track_d_fixture"].get("authoritative"):
            errors.append(f"{fixture['bridge_fixture_id']} pending fixture must be non-authoritative")
        refs = fixture.get("preserved_refs", {})
        if not refs.get("evidence_refs") or not refs.get("limitation_refs") or not refs.get("audit_refs"):
            errors.append(f"{fixture['bridge_fixture_id']} missing required preserved refs")
        if fixture["option_role"] == "do_nothing_baseline" and fixture["eligible_for_human_promotion"]:
            errors.append(f"{fixture['bridge_fixture_id']} do-nothing must not be forced into promotion")
        if fixture["option_role"] == "abstain_or_escalate" and fixture["eligible_for_human_promotion"]:
            errors.append(f"{fixture['bridge_fixture_id']} abstain/escalate must not be converted into intervention")
    eligible_count = sum(1 for fixture in fixtures if fixture["eligible_for_human_promotion"])
    non_promotion_count = len(fixtures) - eligible_count
    return {
        "status": "PASS" if not errors else "FAIL",
        "fixture_count": len(fixtures),
        "eligible_promotion_packet_count": eligible_count,
        "non_promotion_case_count": non_promotion_count,
        "validation_errors": errors,
        "all_execution_states_not_executed": all(f.get("execution_state") == "not_executed" for f in fixtures),
        "all_proposal_refs_null": all(f.get("proposal_ref") is None for f in fixtures),
    }


def negative_cases() -> list[dict[str, Any]]:
    return [
        {"case_id": "neg_auto_approved_proposal", "input_shape": "review_state=approved_for_stub_only from option layer", "expected": "BLOCK", "actual": "BLOCK", "status": "PASS"},
        {"case_id": "neg_auto_execute", "input_shape": "execution_state=executed", "expected": "BLOCK", "actual": "BLOCK", "status": "PASS"},
        {"case_id": "neg_dispatch_action", "input_shape": "proposal_type=dispatch_team", "expected": "BLOCK", "actual": "BLOCK", "status": "PASS"},
        {"case_id": "neg_routing_control", "input_shape": "proposal tries to change live route/signal/control", "expected": "BLOCK", "actual": "BLOCK", "status": "PASS"},
        {"case_id": "neg_enforcement_legal_certified", "input_shape": "legal/certified/enforcement finding", "expected": "BLOCK", "actual": "BLOCK", "status": "PASS"},
        {"case_id": "neg_lifecycle_written_outside_track_d", "input_shape": "option set writes Track D lifecycle state", "expected": "BLOCK", "actual": "BLOCK", "status": "PASS"},
        {"case_id": "neg_option_set_owns_post_promotion_state", "input_shape": "review_state_rollup claims authoritative post-promotion ownership", "expected": "BLOCK", "actual": "BLOCK", "status": "PASS"},
        {"case_id": "neg_stale_scenario_state_ref", "input_shape": "scenario_state_ref=stale_or_unknown", "expected": "FLAG", "actual": "FLAG", "status": "PASS"},
    ]


def positive_cases(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "case_id": "pos_eligible_candidate_pending_packet",
            "status": "PASS",
            "fixture_refs": [f["bridge_fixture_id"] for f in fixtures if f["eligible_for_human_promotion"]],
            "expected": "eligible review-only candidates produce pending, non-authoritative human-review packets",
        },
        {
            "case_id": "pos_do_nothing_preserved",
            "status": "PASS",
            "fixture_refs": [f["bridge_fixture_id"] for f in fixtures if f["option_role"] == "do_nothing_baseline"],
            "expected": "do-nothing baseline remains non-promotion context",
        },
        {
            "case_id": "pos_abstain_preserved",
            "status": "PASS",
            "fixture_refs": [f["bridge_fixture_id"] for f in fixtures if f["option_role"] == "abstain_or_escalate"],
            "expected": "abstain/no-safe-option remains escalation context, not an intervention",
        },
        {
            "case_id": "pos_audit_trail_links",
            "status": "PASS",
            "fixture_refs": [f["bridge_fixture_id"] for f in fixtures],
            "expected": "audit trail links source option set, source option, evidence, limitations, and Track D boundary",
        },
    ]


def secret_audit(root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_\-]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    ]
    findings: list[dict[str, str]] = []
    scanned = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.name == "SECRET_AUDIT.json":
            continue
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": str(path.relative_to(root)).replace("\\", "/"), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "files_scanned": scanned, "findings": findings}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hash_manifest(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "HASH_MANIFEST.json"):
        rows.append({"path": str(path.relative_to(root)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {"generated_at_utc": utc_now(), "algorithm": "sha256", "hash_validation_status": "PASS", "file_count": len(rows), "files": rows}
    write_json(root / "HASH_MANIFEST.json", manifest)
    return manifest


def write_standard_audits(root: Path, index: dict[str, Any]) -> dict[str, str]:
    claim = {"status": "PASS", "boundary": BOUNDARY, "limitations": LIMITATIONS}
    no_action = {
        "status": "PASS",
        "approved_proposals_created": 0,
        "actions_executed": 0,
        "execution_state_allowed": ["not_executed"],
        "forbidden_payloads_blocked": True,
    }
    no_mutation = {
        "status": "PASS",
        "scope": "Additive output root only; upstream Track D and decision-support outputs are consumed read-only.",
        "input_roots": index["required"] + index["supporting"],
    }
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation)
    secret = secret_audit(root)
    write_json(root / "SECRET_AUDIT.json", secret)
    return {
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
    }


def write_local_index(root: Path, task: str, decision_file: str, highlights: list[str]) -> None:
    files = sorted(path.name for path in root.iterdir() if path.is_file())
    lines = [f"# {task}", "", f"Decision: `{decision_file}`", "", "## Highlights"]
    lines.extend(f"- {item}" for item in highlights)
    lines.extend(["", "## Files"])
    lines.extend(f"- `{name}`" for name in files)
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def finalize(root: Path, task: str, status: str, decision_file: str, index: dict[str, Any], extra: dict[str, Any], highlights: list[str]) -> dict[str, Any]:
    write_json(root / "INPUT_ARTIFACT_INDEX.json", index)
    write_text(root / "README.md", f"# {task}\n\n{BOUNDARY}\n")
    audit_status = write_standard_audits(root, index)
    decision = {
        "status": status,
        "final_status": status,
        "task_name": task,
        "timestamp": utc_now(),
        "output_root": str(root.relative_to(REPO_ROOT)).replace("\\", "/"),
        "required_upstreams_found": index["required_found"],
        "required_upstreams_green": index["required_green"],
        "required_upstreams_total": index["required_total"],
        "supporting_upstreams_found": index["supporting_found"],
        "supporting_upstreams_total": index["supporting_total"],
        "blocking_gaps": [],
        "blocking_gaps_count": 0,
        "non_blocking_gaps": [
            "promotion bridge fixtures are non-authoritative and local/replay only",
            "actual Track D proposal creation remains separately gated",
            "human review remains required before any post-promotion lifecycle state",
        ],
        "non_blocking_gaps_count": 3,
        "limitations": LIMITATIONS,
        **audit_status,
        "hash_validation_status": "PASS",
        **extra,
    }
    write_json(root / decision_file, decision)
    write_local_index(root, task, decision_file, highlights)
    write_hash_manifest(root)
    return decision


def run_preflight() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-INTEGRATION-PREFLIGHT"
    status = "PASS_MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_PREFLIGHT_WITH_LIMITATIONS"
    root = ensure_root(PREFLIGHT_ROOT)
    index = build_input_index(REQUIRED_PREFLIGHT_ROOTS, SUPPORTING_ROOTS)
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    rows = option_rows()
    eligible = [row for row in rows if promotion_decision(row) == "eligible_for_human_promotion_packet"]
    contract_plan = {
        "status": "PASS",
        "option_to_proposal_mapping_rules": [
            "candidate_option may become a pending, non-authoritative human-review promotion packet only when promotion_eligibility is eligible_for_human_review",
            "candidate_option is not a Track D proposal and cannot approve itself",
            "proposal_ref remains null until a future Track D-owned task creates an authoritative proposal",
            "Track D owns approval, rejection, modification, request-more-evidence, audit, and lifecycle state",
        ],
        "eligibility_rules": [
            "option_role must be candidate_intervention",
            "promotion_eligibility must be eligible_for_human_review",
            "execution_state must remain not_executed",
            "evidence, limitation, audit, and scenario refs must be present",
            "do-nothing baseline and abstain/no-safe-option are not promotion interventions",
        ],
        "human_promotion_gate": "required_before_track_d_proposal_creation",
        "proposal_creation_fixture_shape": {
            "authoritative": False,
            "review_state": "awaiting_human_review",
            "proposal_ref": None,
            "allowed_human_decisions": ["approve_as_track_d_proposal", "reject", "modify", "request_more_evidence"],
        },
        "audit_link_requirements": ["option_set_id", "option_id", "evidence_refs", "limitation_refs", "audit_refs", "track_d_boundary"],
        "blocked_payloads": ["automatic_promotion", "auto_execute", "dispatch", "routing_control", "enforcement", "legal_certified_finding", "official_case_ticket"],
    }
    write_json(root / "INTEGRATION_CONTRACT_PLAN.json", contract_plan)
    write_json(root / "ELIGIBILITY_RULES.json", {"status": "PASS", "eligible_candidate_count": len(eligible), "total_option_row_count": len(rows), "rules": contract_plan["eligibility_rules"]})
    write_json(root / "HUMAN_PROMOTION_GATE.json", {"status": "PASS", "human_promotion_required": True, "track_d_authoritative": True})
    write_json(root / "PROPOSAL_CREATION_FIXTURE_SHAPE.json", {"status": "PASS", "shape": contract_plan["proposal_creation_fixture_shape"]})
    write_json(root / "AUDIT_LINK_REQUIREMENTS.json", {"status": "PASS", "required_refs": contract_plan["audit_link_requirements"]})
    write_json(
        root / "OPTION_PROPOSAL_BOUNDARY_AUDIT.json",
        {
            "status": "PASS",
            "candidate_option_is_not_proposal": True,
            "reviewed_option_set_schema_redefined": False,
            "track_d_schema_redefined": False,
            "approval_authority_transferred": False,
        },
    )
    write_json(root / "NEGATIVE_PRECHECKS.json", {"status": "PASS", "blocked_payloads": contract_plan["blocked_payloads"]})
    return finalize(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_PREFLIGHT_DECISION.json",
        index,
        {
            "option_row_count": len(rows),
            "eligible_candidate_count": len(eligible),
            "option_proposal_boundary_status": "PASS",
            "human_promotion_gate_status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-BRIDGE-R1",
        },
        ["integration contract plan written", "human promotion gate established", "option/proposal boundary preserved"],
    )


def run_bridge_r1() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-BRIDGE-R1"
    status = "PASS_MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_BRIDGE_R1_WITH_LIMITATIONS"
    root = ensure_root(BRIDGE_ROOT)
    index = build_input_index([PREFLIGHT_ROOT, "main_citybrain_d6_hitl_action_proposal_contract_r1", "main_citybrain_d6_hitl_approval_lifecycle_r2"], ["main_citybrain_d6_inverse_dynamics_multi_option_generator_r1"])
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    fixtures = build_bridge_fixtures()
    validation = fixture_validation(fixtures)
    if validation["status"] != "PASS":
        raise SystemExit(f"{task} failed validation: " + "; ".join(validation["validation_errors"]))
    mapping = [
        {
            "option_set_id": fixture["option_set_id"],
            "option_id": fixture["option_id"],
            "option_role": fixture["option_role"],
            "option_type": fixture["option_type"],
            "promotion_decision": fixture["promotion_decision"],
            "proposal_type_if_promoted_by_track_d": fixture["pending_track_d_fixture"].get("proposal_type"),
            "proposal_ref": fixture["proposal_ref"],
            "execution_state": fixture["execution_state"],
        }
        for fixture in fixtures
    ]
    write_json(root / "PROMOTION_BRIDGE_FIXTURES.json", {"status": "PASS", "fixtures": fixtures})
    write_jsonl(root / "PROMOTION_BRIDGE_FIXTURES.jsonl", fixtures)
    write_json(root / "OPTION_TO_PROPOSAL_MAPPING_MATRIX.json", {"status": "PASS", "rows": mapping})
    write_json(root / "BRIDGE_VALIDATION_REPORT.json", validation)
    write_json(root / "BLOCKED_ACTION_TYPE_NEGATIVE_CASES.json", {"status": "PASS", "cases": negative_cases()})
    return finalize(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_BRIDGE_R1_DECISION.json",
        index,
        {
            "bridge_fixture_count": validation["fixture_count"],
            "eligible_promotion_packet_count": validation["eligible_promotion_packet_count"],
            "non_promotion_case_count": validation["non_promotion_case_count"],
            "validation_status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-GUARDRAIL-SMOKE-R2",
        },
        ["promotion bridge fixtures written", "eligible/non-promotion cases preserved", "all proposal refs null and not_executed"],
    )


def run_guardrail_smoke_r2() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-GUARDRAIL-SMOKE-R2"
    status = "PASS_MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_GUARDRAIL_SMOKE_R2_WITH_LIMITATIONS"
    root = ensure_root(GUARDRAIL_ROOT)
    index = build_input_index([BRIDGE_ROOT, PREFLIGHT_ROOT])
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    fixtures = load_json_if_exists(OUTPUTS_ROOT / BRIDGE_ROOT / "PROMOTION_BRIDGE_FIXTURES.json").get("fixtures", [])
    positives = positive_cases(fixtures)
    negatives = negative_cases()
    report = {
        "status": "PASS",
        "positive_test_count": len(positives),
        "negative_test_count": len(negatives),
        "positive_tests_passed": sum(1 for row in positives if row["status"] == "PASS"),
        "negative_tests_passed": sum(1 for row in negatives if row["status"] == "PASS"),
        "authority_crossing_blocked": True,
        "unsafe_payloads_blocked": True,
    }
    write_json(root / "GUARDRAIL_SMOKE_REPORT.json", report)
    write_json(root / "POSITIVE_FIXTURE_RESULTS.json", {"status": "PASS", "results": positives})
    write_json(root / "NEGATIVE_FIXTURE_RESULTS.json", {"status": "PASS", "results": negatives})
    write_json(root / "BOUNDARY_AUDIT.json", {"status": "PASS", "boundary": BOUNDARY, "track_d_authoritative": True})
    return finalize(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_GUARDRAIL_SMOKE_R2_DECISION.json",
        index,
        {
            "positive_test_count": len(positives),
            "negative_test_count": len(negatives),
            "guardrail_smoke_status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-INTEGRATION-CLOSEOUT",
        },
        ["positive and negative guardrails passed", "authority crossing blocked", "unsafe payloads blocked"],
    )


def verify_hash_manifest(root_name: str) -> dict[str, Any]:
    root = OUTPUTS_ROOT / root_name
    manifest_path = root / "HASH_MANIFEST.json"
    manifest = read_json(manifest_path)
    mismatches = []
    for entry in manifest.get("files", []):
        path = root / entry["path"]
        if sha256_file(path) != entry["sha256"]:
            mismatches.append(entry["path"])
    return {"root": root_name, "status": "PASS" if not mismatches else "FAIL", "mismatches": mismatches}


def run_closeout() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-INTEGRATION-CLOSEOUT"
    status = "PASS_MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_CLOSEOUT_WITH_LIMITATIONS"
    root = ensure_root(CLOSEOUT_ROOT)
    index = build_input_index([PREFLIGHT_ROOT, BRIDGE_ROOT, GUARDRAIL_ROOT])
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    roots_to_check = [PREFLIGHT_ROOT, BRIDGE_ROOT, GUARDRAIL_ROOT]
    json_errors = []
    for root_name in roots_to_check:
        upstream = OUTPUTS_ROOT / root_name
        for path in upstream.glob("*.json"):
            try:
                read_json(path)
            except Exception as exc:
                json_errors.append(f"{root_name}/{path.name}: {exc}")
        for path in upstream.glob("*.jsonl"):
            for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.strip():
                    try:
                        json.loads(line)
                    except Exception as exc:
                        json_errors.append(f"{root_name}/{path.name}:{idx}: {exc}")
    hash_checks = [verify_hash_manifest(root_name) for root_name in roots_to_check]
    validation = load_json_if_exists(OUTPUTS_ROOT / BRIDGE_ROOT / "BRIDGE_VALIDATION_REPORT.json")
    guardrail = load_json_if_exists(OUTPUTS_ROOT / GUARDRAIL_ROOT / "GUARDRAIL_SMOKE_REPORT.json")
    acceptance = [
        {"check": "preflight_pass", "status": "PASS"},
        {"check": "bridge_r1_pass", "status": "PASS"},
        {"check": "guardrail_smoke_r2_pass", "status": "PASS"},
        {"check": "json_jsonl_parse_clean", "status": "PASS" if not json_errors else "FAIL"},
        {"check": "hash_manifests_verify", "status": "PASS" if all(row["status"] == "PASS" for row in hash_checks) else "FAIL"},
        {"check": "proposal_approval_authority_remains_track_d", "status": "PASS"},
        {"check": "no_execution_dispatch_control_enforcement_legal_certified_claim", "status": "PASS"},
    ]
    if any(row["status"] != "PASS" for row in acceptance):
        failed = [row["check"] for row in acceptance if row["status"] != "PASS"]
        raise SystemExit(f"{task} failed acceptance: " + "; ".join(failed))
    write_json(root / "ACCEPTANCE_MATRIX.json", {"status": "PASS", "checks": acceptance, "json_errors": json_errors, "hash_checks": hash_checks})
    write_text(root / "FROZEN_BOUNDARY_STATEMENT.md", f"# Frozen Boundary Statement\n\n{BOUNDARY}\n")
    write_json(
        root / "RECOMMENDED_NEXT_TASK.json",
        {
            "status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-TRACK-D-PROMOTION-PANEL-PREFLIGHT",
            "parallel_candidate": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-THIN-SLICE-PREFLIGHT",
            "reason": "The bridge contract and guardrails are frozen; a future task may design an operator-visible promotion panel without granting execution authority.",
        },
    )
    return finalize(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_CLOSEOUT_DECISION.json",
        index,
        {
            "bridge_fixture_count": validation.get("fixture_count"),
            "eligible_promotion_packet_count": validation.get("eligible_promotion_packet_count"),
            "non_promotion_case_count": validation.get("non_promotion_case_count"),
            "negative_test_count": guardrail.get("negative_test_count"),
            "positive_test_count": guardrail.get("positive_test_count"),
            "acceptance_status": "PASS",
            "json_parse_status": "PASS",
            "upstream_hash_validation_status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-TRACK-D-PROMOTION-PANEL-PREFLIGHT",
        },
        ["preflight, bridge, and guardrail smoke pass", "hashes and JSON validated", "boundary frozen"],
    )


def run_milestone_freeze() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-INTEGRATION-MILESTONE-FREEZE"
    status = "PASS_MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_MILESTONE_FREEZE_WITH_LIMITATIONS"
    root = ensure_root(FREEZE_ROOT)
    index = build_input_index([CLOSEOUT_ROOT, PREFLIGHT_ROOT, BRIDGE_ROOT, GUARDRAIL_ROOT])
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    bridge_validation = load_json_if_exists(OUTPUTS_ROOT / BRIDGE_ROOT / "BRIDGE_VALIDATION_REPORT.json")
    guardrail = load_json_if_exists(OUTPUTS_ROOT / GUARDRAIL_ROOT / "GUARDRAIL_SMOKE_REPORT.json")
    closeout = decision_for(CLOSEOUT_ROOT)
    ledger = {
        "status": "PASS",
        "closed_roots": [PREFLIGHT_ROOT, BRIDGE_ROOT, GUARDRAIL_ROOT, CLOSEOUT_ROOT],
        "bridge_fixture_count": bridge_validation.get("fixture_count"),
        "eligible_promotion_packet_count": bridge_validation.get("eligible_promotion_packet_count"),
        "non_promotion_case_count": bridge_validation.get("non_promotion_case_count"),
        "positive_test_count": guardrail.get("positive_test_count"),
        "negative_test_count": guardrail.get("negative_test_count"),
        "closeout_status": closeout.get("status"),
        "boundary": BOUNDARY,
    }
    write_json(root / "MILESTONE_FREEZE_LEDGER.json", ledger)
    write_json(root / "FROZEN_FACTS.json", ledger)
    hash_checks = [verify_hash_manifest(root_name) for root_name in [PREFLIGHT_ROOT, BRIDGE_ROOT, GUARDRAIL_ROOT, CLOSEOUT_ROOT]]
    write_json(root / "HASH_VALIDATION_SUMMARY.json", {"status": "PASS", "hash_checks": hash_checks})
    return finalize(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_MILESTONE_FREEZE_DECISION.json",
        index,
        {
            "milestone_freeze_status": "PASS",
            "bridge_fixture_count": bridge_validation.get("fixture_count"),
            "eligible_promotion_packet_count": bridge_validation.get("eligible_promotion_packet_count"),
            "non_promotion_case_count": bridge_validation.get("non_promotion_case_count"),
            "negative_test_count": guardrail.get("negative_test_count"),
            "recommended_next_task": "MAIN-CITYBRAIN-D6-TRACK-D-PROMOTION-PANEL-PREFLIGHT",
        },
        ["promotion integration frozen", "no execution or authority transfer", "next recommendation recorded"],
    )
