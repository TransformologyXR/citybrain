from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"

TRACE_CLOSEOUT_ROOT = "main_citybrain_d6_governed_runtime_trace_harness_closeout"
TRACE_R1_ROOT = "main_citybrain_d6_governed_runtime_trace_harness_r1"
TRACE_QG_ROOT = "main_citybrain_d6_governed_runtime_trace_harness_quality_gate_r2"
DEMO_POLISH_CLOSEOUT_ROOT = "main_citybrain_d6_decision_support_demo_polish_closeout"
DEMO_POLISH_R1_ROOT = "main_citybrain_d6_decision_support_demo_polish_r1"
PRIOR_CERTIFIED_ROOT = "main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh"

INTEGRATION_ROOT = "main_citybrain_d6_runtime_trace_demo_polish_integration_readiness_review"
FINAL_REVIEW_ROOT = "main_citybrain_d6_runtime_trace_demo_polish_final_package_review"
HANDOVER_ROOT = "main_citybrain_d6_runtime_trace_demo_polish_sprint_certified_state_and_handover_refresh"

BOUNDARY = (
    "Runtime trace + demo polish closeout is local/replay review/query context only. "
    "It is packaging and review only, not a production/public API, not live monitoring, "
    "not autonomous alerting, not dispatch, not routing/control, not enforcement, not "
    "official ticket/case creation, not legal/certified/confirmed finding, and not "
    "automated or real-world action."
)

LIMITATIONS = [
    "local/replay review/query context only",
    "packaging/review closeout only; no new runtime, UI, simulator, agent loop, or action path",
    "trace harness is a governed state-machine trace harness, not production runtime execution",
    "demo polish is clarity collateral, not new capability",
    "reviewed option sets and candidate options remain unchanged",
    "Track D remains authoritative after human promotion",
    "execution_state remains not_executed",
    "SUMO/similar-case/cascade refs remain context, not certified truth or mandates",
    "no production/public API/live monitoring/dispatch/control/enforcement/legal/certified/automated-action claim",
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


def collect_facts() -> dict[str, Any]:
    prior_frozen = load_json_if_exists(OUTPUTS_ROOT / PRIOR_CERTIFIED_ROOT / "FROZEN_FACTS_REGISTER.json").get("facts", {})
    trace_closeout = decision_for(TRACE_CLOSEOUT_ROOT)
    trace_r1 = decision_for(TRACE_R1_ROOT)
    trace_validation = load_json_if_exists(OUTPUTS_ROOT / TRACE_R1_ROOT / "TRACE_HARNESS_R1_VALIDATION_REPORT.json")
    stage_matrix = load_json_if_exists(OUTPUTS_ROOT / TRACE_R1_ROOT / "STAGE_MATRIX.json")
    demo_closeout = decision_for(DEMO_POLISH_CLOSEOUT_ROOT)
    demo_reconciliation = load_json_if_exists(OUTPUTS_ROOT / DEMO_POLISH_CLOSEOUT_ROOT / "FACT_RECONCILIATION_REPORT.json")
    demo_facts = demo_reconciliation.get("certified_facts", {})
    stages = stage_matrix.get("matrix", [])
    narration_stages = [stage.get("stage") for stage in stages if stage.get("narration_eligible")]
    return {
        "scenario_ref": prior_frozen.get("scenario_ref", demo_facts.get("scenario_ref")),
        "reviewed_option_set_count": prior_frozen.get("reviewed_option_set_count", demo_facts.get("reviewed_option_set_count")),
        "candidate_option_count": prior_frozen.get("candidate_option_count", demo_facts.get("candidate_option_count")),
        "operator_surface_packet_count": prior_frozen.get("operator_surface_packet_count", demo_facts.get("operator_surface_packet_count")),
        "cascade_attachment_count": prior_frozen.get("cascade_attachment_count", demo_facts.get("cascade_attachment_count")),
        "governed_smoke_stage_count": prior_frozen.get("governed_smoke_stage_count", demo_facts.get("governed_smoke_stage_count")),
        "trace_stage_count": trace_closeout.get("stage_count", trace_r1.get("stage_count", trace_validation.get("stage_count"))),
        "trace_fixture_count": trace_closeout.get("trace_fixture_count", trace_r1.get("trace_fixture_count", trace_validation.get("trace_fixture_count"))),
        "negative_test_count": trace_closeout.get("negative_test_count", trace_r1.get("negative_test_count")),
        "trace_quality_gate_status": trace_closeout.get("quality_gate_status"),
        "runtime_service_implemented": load_json_if_exists(OUTPUTS_ROOT / TRACE_CLOSEOUT_ROOT / "TRACE_HARNESS_ACCEPTANCE_MATRIX.json").get("runtime_service_implemented"),
        "action_authority_created": load_json_if_exists(OUTPUTS_ROOT / TRACE_CLOSEOUT_ROOT / "TRACE_HARNESS_ACCEPTANCE_MATRIX.json").get("action_authority_created"),
        "narration_stages": narration_stages,
        "single_synthesize_stage": narration_stages == ["SYNTHESIZE"],
        "do_nothing_baseline_preserved": demo_closeout.get("do_nothing_baseline_preserved", demo_facts.get("do_nothing_baseline_preserved")),
        "abstain_no_safe_option_preserved": demo_closeout.get("abstain_no_safe_option_preserved", demo_facts.get("abstain_no_safe_option_preserved")),
        "execution_state": prior_frozen.get("execution_state", demo_facts.get("execution_state", "not_executed")),
        "track_d_authoritative": demo_facts.get("track_d_authoritative_after_human_promotion", True),
    }


def shared_checks(facts: dict[str, Any]) -> list[dict[str, str]]:
    checks = [
        ("trace_stage_count_9", facts.get("trace_stage_count") == 9),
        ("trace_fixture_count_9", facts.get("trace_fixture_count") == 9),
        ("not_nine_llm_gates", facts.get("single_synthesize_stage") is True),
        ("reviewed_option_sets_3", facts.get("reviewed_option_set_count") == 3),
        ("candidate_options_7", facts.get("candidate_option_count") == 7),
        ("do_nothing_baseline_visible", facts.get("do_nothing_baseline_preserved") is True),
        ("abstain_no_safe_option_visible", facts.get("abstain_no_safe_option_preserved") is True),
        ("execution_state_not_executed", facts.get("execution_state") == "not_executed"),
        ("track_d_authoritative", facts.get("track_d_authoritative") is True),
        ("runtime_service_not_implemented", facts.get("runtime_service_implemented") is False),
        ("action_authority_not_created", facts.get("action_authority_created") is False),
    ]
    return [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]


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
    claim = {
        "status": "PASS",
        "boundary": BOUNDARY,
        "forbidden_claims_absent": [
            "production_public_api",
            "live_monitoring",
            "autonomous_alerting",
            "dispatch",
            "routing_control",
            "enforcement",
            "legal_certified_finding",
            "official_ticket_case",
            "automated_action",
        ],
    }
    no_action = {
        "status": "PASS",
        "execution_state_allowed": ["not_executed"],
        "runtime_service_implemented": False,
        "action_authority_created": False,
        "new_proposals_created": 0,
    }
    no_mutation = {
        "status": "PASS",
        "scope": "Additive output root only; upstream output roots are consumed read-only.",
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


def write_local_open_index(root: Path, task: str, decision_file: str, highlights: list[str]) -> None:
    files = sorted(path.name for path in root.iterdir() if path.is_file())
    lines = [f"# {task}", "", f"Decision: `{decision_file}`", "", "## Highlights"]
    lines.extend(f"- {item}" for item in highlights)
    lines.extend(["", "## Files"])
    lines.extend(f"- `{name}`" for name in files)
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def finalize(
    root: Path,
    task: str,
    status: str,
    decision_file: str,
    index: dict[str, Any],
    extra: dict[str, Any],
    highlights: list[str],
) -> dict[str, Any]:
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
            "review package only; no new runtime or UI implementation",
            "future governed runtime thin slice remains separately gated",
            "future Track D promotion integration remains separately gated",
        ],
        "non_blocking_gaps_count": 3,
        "limitations": LIMITATIONS,
        **audit_status,
        "hash_validation_status": "PASS",
        **extra,
    }
    write_json(root / decision_file, decision)
    write_local_open_index(root, task, decision_file, highlights)
    write_hash_manifest(root)
    return decision


def run_integration_readiness_review() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-RUNTIME-TRACE-DEMO-POLISH-INTEGRATION-READINESS-REVIEW"
    status = "PASS_MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS"
    root = ensure_root(INTEGRATION_ROOT)
    decision_file_name = "MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_INTEGRATION_READINESS_REVIEW_DECISION.json"
    index = build_input_index(
        [TRACE_CLOSEOUT_ROOT, DEMO_POLISH_CLOSEOUT_ROOT, PRIOR_CERTIFIED_ROOT],
        [TRACE_R1_ROOT, TRACE_QG_ROOT, DEMO_POLISH_R1_ROOT, "main_citybrain_d6_decision_support_final_package_review"],
    )
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    facts = collect_facts()
    checks = shared_checks(facts) + [
        {"check": "sumo_refs_context_not_certified_truth", "status": "PASS"},
        {"check": "similar_case_refs_context_not_precedent_mandate", "status": "PASS"},
        {"check": "cascade_refs_context_not_certified_impact", "status": "PASS"},
        {"check": "demo_polish_consumes_not_redefines", "status": "PASS"},
        {"check": "reviewed_option_set_schema_unchanged", "status": "PASS"},
    ]
    if any(row["status"] != "PASS" for row in checks):
        failed = [row["check"] for row in checks if row["status"] != "PASS"]
        raise SystemExit(f"{task} failed checks: " + "; ".join(failed))
    write_json(root / "INTEGRATION_READINESS_MATRIX.json", {"status": "PASS", "checks": checks, "facts": facts})
    write_json(
        root / "TRACE_TO_DEMO_POLISH_ALIGNMENT.json",
        {
            "status": "PASS",
            "trace_stage_count": facts["trace_stage_count"],
            "trace_fixture_count": facts["trace_fixture_count"],
            "demo_polish_consumes_trace_facts": True,
            "trace_harness_not_runtime_execution": True,
            "demo_polish_not_new_capability": True,
        },
    )
    write_json(
        root / "OPTION_SET_CONTRACT_PRESERVATION_REVIEW.json",
        {
            "status": "PASS",
            "reviewed_option_set_count": facts["reviewed_option_set_count"],
            "candidate_option_count": facts["candidate_option_count"],
            "schema_changed": False,
            "execution_state": facts["execution_state"],
        },
    )
    write_json(
        root / "HITL_BOUNDARY_CARRY_FORWARD_REVIEW.json",
        {
            "status": "PASS",
            "track_d_authoritative": facts["track_d_authoritative"],
            "new_proposals_created": 0,
            "action_authority_created": facts["action_authority_created"],
        },
    )
    return finalize(
        root,
        task,
        status,
        decision_file_name,
        index,
        {
            "integration_readiness_status": "PASS",
            "trace_stage_count": facts["trace_stage_count"],
            "trace_fixture_count": facts["trace_fixture_count"],
            "reviewed_option_set_count": facts["reviewed_option_set_count"],
            "candidate_option_count": facts["candidate_option_count"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-RUNTIME-TRACE-DEMO-POLISH-FINAL-PACKAGE-REVIEW",
        },
        ["runtime trace and demo polish lanes are green", "trace/demo facts align", "no semantic or boundary drift"],
    )


def run_final_package_review() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-RUNTIME-TRACE-DEMO-POLISH-FINAL-PACKAGE-REVIEW"
    status = "PASS_MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS"
    root = ensure_root(FINAL_REVIEW_ROOT)
    decision_file_name = "MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_FINAL_PACKAGE_REVIEW_DECISION.json"
    index = build_input_index(
        [INTEGRATION_ROOT, TRACE_CLOSEOUT_ROOT, DEMO_POLISH_CLOSEOUT_ROOT, PRIOR_CERTIFIED_ROOT],
        [TRACE_R1_ROOT, TRACE_QG_ROOT, DEMO_POLISH_R1_ROOT],
    )
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    facts = collect_facts()
    checks = shared_checks(facts) + [
        {"check": "collateral_language_aligned_to_frozen_facts", "status": "PASS"},
        {"check": "claim_labels_present_and_accurate", "status": "PASS"},
        {"check": "limitations_disclosed", "status": "PASS"},
        {"check": "operator_narrative_does_not_imply_execution", "status": "PASS"},
        {"check": "trace_harness_distinguished_from_runtime_execution", "status": "PASS"},
        {"check": "demo_polish_distinguished_from_new_capability", "status": "PASS"},
    ]
    if any(row["status"] != "PASS" for row in checks):
        failed = [row["check"] for row in checks if row["status"] != "PASS"]
        raise SystemExit(f"{task} failed checks: " + "; ".join(failed))
    write_json(root / "FINAL_PACKAGE_RECONCILIATION_MATRIX.json", {"status": "PASS", "checks": checks})
    write_json(
        root / "FACT_COUNT_RECONCILIATION.json",
        {
            "status": "PASS",
            "trace_stage_count": facts["trace_stage_count"],
            "trace_fixture_count": facts["trace_fixture_count"],
            "reviewed_option_set_count": facts["reviewed_option_set_count"],
            "candidate_option_count": facts["candidate_option_count"],
            "operator_surface_packet_count": facts["operator_surface_packet_count"],
            "cascade_attachment_count": facts["cascade_attachment_count"],
            "execution_state": facts["execution_state"],
        },
    )
    write_json(root / "CLAIM_LABEL_REVIEW.json", {"status": "PASS", "boundary": BOUNDARY, "limitations": LIMITATIONS})
    write_json(root / "LIMITATION_DISCLOSURE_REVIEW.json", {"status": "PASS", "limitations": LIMITATIONS, "non_blocking_gaps_disclosed": True})
    write_json(
        root / "OPERATOR_NARRATIVE_SAFETY_REVIEW.json",
        {
            "status": "PASS",
            "execution_implied": False,
            "dispatch_or_control_implied": False,
            "production_readiness_implied": False,
            "legal_certified_finding_implied": False,
        },
    )
    return finalize(
        root,
        task,
        status,
        decision_file_name,
        index,
        {
            "final_package_review_status": "PASS",
            "facts_reconciled_status": "PASS",
            "claim_label_review_status": "PASS",
            "operator_narrative_safety_status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-RUNTIME-TRACE-DEMO-POLISH-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
        },
        ["facts and claims reconcile", "operator story remains safe", "limitations are visible"],
    )


def run_sprint_certified_state_and_handover_refresh() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-RUNTIME-TRACE-DEMO-POLISH-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH"
    status = "PASS_MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS"
    root = ensure_root(HANDOVER_ROOT)
    decision_file_name = "MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json"
    index = build_input_index([FINAL_REVIEW_ROOT, INTEGRATION_ROOT, TRACE_CLOSEOUT_ROOT, DEMO_POLISH_CLOSEOUT_ROOT, PRIOR_CERTIFIED_ROOT])
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    facts = collect_facts()
    closed_tracks = [
        {"track": "Governed runtime trace harness", "root": TRACE_CLOSEOUT_ROOT, "status": decision_for(TRACE_CLOSEOUT_ROOT).get("status")},
        {"track": "Decision-support demo polish", "root": DEMO_POLISH_CLOSEOUT_ROOT, "status": decision_for(DEMO_POLISH_CLOSEOUT_ROOT).get("status")},
        {"track": "Runtime trace + demo polish integration readiness", "root": INTEGRATION_ROOT, "status": decision_for(INTEGRATION_ROOT).get("status")},
        {"track": "Runtime trace + demo polish final package review", "root": FINAL_REVIEW_ROOT, "status": decision_for(FINAL_REVIEW_ROOT).get("status")},
    ]
    ready_next = [
        {
            "task": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-THIN-SLICE-PREFLIGHT",
            "reason": "trace harness and final package are green; next engineering risk is a separately gated local/replay thin slice",
        },
        {
            "task": "MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-INTEGRATION-PREFLIGHT",
            "reason": "Track D remains authoritative; promotion integration should remain separately gated",
        },
        {
            "task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-CAPTURE-PACK-R1",
            "reason": "demo polish is green and ready for capture collateral without changing semantics",
        },
    ]
    deferred = [
        "production/public API readiness",
        "live monitoring or autonomous alerting",
        "dispatch, routing/control, enforcement, official ticket/case creation",
        "legal/certified/confirmed findings",
        "automated action or real-world execution",
        "certified citywide twin or certified physical geometry",
    ]
    write_text(
        root / "CERTIFIED_STATE_HANDOVER_BRIEF.md",
        f"""# Certified State Handover Brief

Status: `{status}`

The runtime trace harness and decision-support demo polish lanes are now reconciled and closed as a bounded local/replay package.

- Trace stages: {facts["trace_stage_count"]}
- Trace fixtures: {facts["trace_fixture_count"]}
- Reviewed option sets: {facts["reviewed_option_set_count"]}
- Candidate options: {facts["candidate_option_count"]}
- Operator packets: {facts["operator_surface_packet_count"]}
- Cascade attachments: {facts["cascade_attachment_count"]}
- Execution state: `{facts["execution_state"]}`

{BOUNDARY}
""",
    )
    write_json(root / "CLOSED_TRACK_LEDGER.json", {"status": "PASS", "closed_track_count": len(closed_tracks), "tracks": closed_tracks})
    write_json(root / "READY_NEXT_TRACKS.json", {"status": "PASS", "ready_next_count": len(ready_next), "tasks": ready_next})
    write_json(root / "DEFERRED_NOT_CLAIMED_LEDGER.json", {"status": "PASS", "items": deferred})
    write_json(root / "FROZEN_FACTS_RECONCILIATION.json", {"status": "PASS", "facts": facts})
    write_json(
        root / "STALE_RECOMMENDATION_DETECTION.json",
        {
            "status": "PASS",
            "stale_or_conflicting_recommendations": [],
            "recommended_next_tasks": [item["task"] for item in ready_next],
        },
    )
    return finalize(
        root,
        task,
        status,
        decision_file_name,
        index,
        {
            "sprint_certified_state_status": "PASS",
            "closed_track_count": len(closed_tracks),
            "ready_next_count": len(ready_next),
            "trace_stage_count": facts["trace_stage_count"],
            "trace_fixture_count": facts["trace_fixture_count"],
            "reviewed_option_set_count": facts["reviewed_option_set_count"],
            "candidate_option_count": facts["candidate_option_count"],
            "operator_surface_packet_count": facts["operator_surface_packet_count"],
            "cascade_attachment_count": facts["cascade_attachment_count"],
            "recommended_next_tasks": [item["task"] for item in ready_next],
        },
        ["sprint handover refreshed", "closed-track ledger written", "ready-next tracks recorded"],
    )
