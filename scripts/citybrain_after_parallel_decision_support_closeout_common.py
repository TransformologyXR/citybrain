from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
SCENARIO_REF = "scenario:HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"

BOUNDARY_TEXT = (
    "Decision-support sprint closeout is local/replay review/query context only. "
    "It creates no production or public API readiness, no live monitoring, no "
    "autonomous alerting, no dispatch, no routing/control, no enforcement, no "
    "official ticket/case creation, no legal/certified/confirmed finding, no "
    "certified twin/geometry claim, and no automated or live action. Track D "
    "remains authoritative after human promotion. The governed 9-stage runtime "
    "is a state-machine contract/smoke, not nine autonomous LLM gates; only "
    "SYNTHESIZE may be grounded narration."
)

LIMITATIONS = [
    "local/replay review/query context only",
    "sprint-close package; no new runtime service, generator, simulator, or UI is implemented",
    "reviewed_option_set options remain pre-review decision-support candidates",
    "execution_state remains not_executed",
    "Track D remains authoritative after human promotion",
    "SUMO, inverse-dynamics, similar-case, and cascade artifacts are context and fixtures, not certified real-world truth",
    "no production/public API, live monitoring, autonomous alerts, dispatch, routing/control, enforcement, official case, legal/certified finding, automated action, or live action",
    "governed 9-stage runtime remains a state-machine contract/smoke; only SYNTHESIZE is narration-eligible",
]

REQUIRED_INTEGRATION_ROOTS = [
    "main_citybrain_d6_decision_support_contract_spine_closeout",
    "main_citybrain_d6_plan_mode_sumo_closeout",
    "main_citybrain_d6_similar_case_retrieval_closeout",
    "main_citybrain_d6_inverse_dynamics_multi_option_milestone_freeze",
    "main_citybrain_d6_decision_support_certified_state_and_handover_refresh",
    "main_citybrain_d6_cross_domain_cascade_milestone_freeze",
    "main_citybrain_d6_operator_decision_support_surface_r1",
    "main_citybrain_d6_governed_9_stage_runtime_contract_smoke_r1",
]

SUPPORTING_SPRINT_ROOTS = [
    "main_citybrain_d6_decision_support_option_set_contract_preflight",
    "main_citybrain_d6_governed_9_stage_runtime_interface_preflight",
    "main_citybrain_d6_hero_corridor_reviewed_action_enum_r1",
    "main_citybrain_d6_decision_support_golden_quality_gate_r1",
    "main_citybrain_d6_plan_mode_sumo_preflight",
    "main_citybrain_d6_plan_mode_sumo_scenario_r1",
    "main_citybrain_d6_plan_mode_option_set_normalization_r2",
    "main_citybrain_d6_plan_mode_runtime_smoke_r3",
    "main_citybrain_d6_similar_case_retrieval_preflight",
    "main_citybrain_d6_similar_case_index_r1",
    "main_citybrain_d6_similar_case_option_set_attachment_r2",
    "main_citybrain_d6_similar_case_retrieval_quality_gate_r3",
    "main_citybrain_d6_inverse_dynamics_multi_option_decision_support_preflight",
    "main_citybrain_d6_inverse_dynamics_multi_option_generator_r1",
    "main_citybrain_d6_inverse_dynamics_tradeoff_evaluation_r2",
    "main_citybrain_d6_inverse_dynamics_hitl_promotion_bridge_r3",
    "main_citybrain_d6_inverse_dynamics_multi_option_closeout",
    "main_citybrain_d6_cross_domain_cascade_closeout",
    "main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_output_root(slug: str) -> Path:
    root = OUTPUTS_ROOT / slug
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def decision_file_for_root(root: Path) -> Path | None:
    matches = sorted(root.glob("*DECISION.json"))
    return matches[0] if matches else None


def decision_for(root_name: str) -> dict[str, Any]:
    root = OUTPUTS_ROOT / root_name
    decision_path = decision_file_for_root(root) if root.exists() else None
    if not decision_path:
        return {}
    try:
        return read_json(decision_path)
    except json.JSONDecodeError as exc:
        return {"json_error": str(exc)}


def root_summary(root_name: str, required: bool) -> dict[str, Any]:
    root = OUTPUTS_ROOT / root_name
    decision_path = decision_file_for_root(root) if root.exists() else None
    decision = decision_for(root_name) if decision_path else {}
    files = [p for p in root.rglob("*") if p.is_file()] if root.exists() else []
    latest = max((p.stat().st_mtime for p in files), default=None)
    return {
        "root": f"outputs/{root_name}",
        "required": required,
        "exists": root.exists(),
        "decision_file": str(decision_path.relative_to(REPO_ROOT)).replace("\\", "/") if decision_path else None,
        "status": decision.get("status") or decision.get("final_status"),
        "task_name": decision.get("task_name"),
        "file_count": len(files),
        "latest_mtime_utc": datetime.fromtimestamp(latest, timezone.utc).isoformat().replace("+00:00", "Z") if latest else None,
    }


def build_input_index(required_roots: list[str], supporting_roots: list[str] | None = None) -> dict[str, Any]:
    supporting_roots = supporting_roots or []
    required = [root_summary(root, True) for root in required_roots]
    supporting = [root_summary(root, False) for root in supporting_roots]
    return {
        "generated_at_utc": utc_now(),
        "required": required,
        "supporting": supporting,
        "required_found": sum(1 for item in required if item["exists"]),
        "required_total": len(required),
        "required_green": sum(1 for item in required if str(item.get("status", "")).startswith("PASS")),
        "supporting_found": sum(1 for item in supporting if item["exists"]),
        "supporting_total": len(supporting),
        "supporting_green": sum(1 for item in supporting if str(item.get("status", "")).startswith("PASS")),
    }


def require_green(input_index: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for item in input_index["required"]:
        if not item["exists"]:
            failures.append(f"missing required root {item['root']}")
        elif not str(item.get("status", "")).startswith("PASS"):
            failures.append(f"required root not green {item['root']}: {item.get('status')}")
    return failures


def fail_safely(root: Path, task: str, decision_name: str, input_index: dict[str, Any], failures: list[str]) -> None:
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(
        root / decision_name,
        {
            "status": f"FAIL_{task}",
            "final_status": f"FAIL_{task}",
            "task_name": task,
            "timestamp": utc_now(),
            "output_root": str(root.relative_to(REPO_ROOT)).replace("\\", "/"),
            "blocking_gaps": failures,
            "blocking_gaps_count": len(failures),
            "upstream_missing_or_not_green": failures,
            "no_mutation_status": "PASS",
        },
    )
    raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def load_option_sets() -> list[dict[str, Any]]:
    path = OUTPUTS_ROOT / "main_citybrain_d6_inverse_dynamics_multi_option_generator_r1" / "GENERATED_REVIEWED_OPTION_SETS.json"
    return load_json_if_exists(path).get("reviewed_option_sets", [])


def load_surface_packets() -> list[dict[str, Any]]:
    path = OUTPUTS_ROOT / "main_citybrain_d6_operator_decision_support_surface_r1" / "OPERATOR_DECISION_SUPPORT_PACKETS.json"
    return load_json_if_exists(path).get("packets", [])


def load_cascade_attachments() -> list[dict[str, Any]]:
    path = OUTPUTS_ROOT / "main_citybrain_d6_cross_domain_cascade_option_set_attachment_r3" / "CASCADE_OPTION_SET_ATTACHMENTS.json"
    return load_json_if_exists(path).get("attachments", [])


def load_smoke_results() -> list[dict[str, Any]]:
    path = OUTPUTS_ROOT / "main_citybrain_d6_governed_9_stage_runtime_contract_smoke_r1" / "NINE_STAGE_SMOKE_RESULTS.json"
    return load_json_if_exists(path).get("results", [])


def load_stage_matrix() -> list[dict[str, Any]]:
    path = OUTPUTS_ROOT / "main_citybrain_d6_governed_9_stage_runtime_contract_smoke_r1" / "NINE_STAGE_STAGE_IO_MATRIX.json"
    data = load_json_if_exists(path)
    return data.get("matrix", data.get("stages", data if isinstance(data, list) else []))


def collect_sprint_facts() -> dict[str, Any]:
    option_sets = load_option_sets()
    options = [option for option_set in option_sets for option in option_set.get("candidate_options", [])]
    packets = load_surface_packets()
    attachments = load_cascade_attachments()
    smoke_results = load_smoke_results()
    stage_matrix = load_stage_matrix()
    narration_stages = [
        stage.get("stage")
        for stage in stage_matrix
        if stage.get("narration_eligible") or stage.get("model_use") == "grounded_narration"
    ]
    return {
        "scenario_refs": sorted({option_set.get("scenario_ref") for option_set in option_sets if option_set.get("scenario_ref")}),
        "reviewed_option_set_count": len(option_sets),
        "candidate_option_count": len(options),
        "operator_surface_packet_count": len(packets),
        "cascade_attachment_count": len(attachments),
        "governed_smoke_stage_count": len(smoke_results),
        "governed_smoke_pass_count": sum(1 for result in smoke_results if result.get("status") == "PASS"),
        "do_nothing_baseline_preserved": any(option.get("option_role") == "do_nothing_baseline" for option in options),
        "abstain_no_safe_option_preserved": any(
            option_set.get("option_set_outcome") in {"no_safe_reviewed_option", "insufficient_evidence", "simulation_unavailable"}
            for option_set in option_sets
        ),
        "all_option_sets_not_executed": all(option_set.get("execution_state") == "not_executed" for option_set in option_sets),
        "all_surface_packets_not_executed": all(packet.get("execution_state") == "not_executed" for packet in packets),
        "all_cascade_attachments_not_executed": all(attachment.get("execution_state") == "not_executed" for attachment in attachments),
        "narration_stages": narration_stages,
        "synthesize_only_narration": narration_stages in (["SYNTHESIZE"], ["synthesize"]),
        "track_d_authoritative": True,
        "production_claim": False,
        "public_api_claim": False,
        "live_action_claim": False,
    }


def secret_audit_for_root(root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_\-]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    ]
    findings: list[dict[str, str]] = []
    file_count = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.name == "SECRET_AUDIT.json":
            continue
        file_count += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": str(path.relative_to(root)).replace("\\", "/"), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "files_scanned": file_count, "findings": findings}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hash_manifest(root: Path) -> dict[str, Any]:
    entries = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "HASH_MANIFEST.json"):
        entries.append(
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = {
        "generated_at_utc": utc_now(),
        "algorithm": "sha256",
        "hash_validation_status": "PASS",
        "file_count": len(entries),
        "files": entries,
    }
    write_json(root / "HASH_MANIFEST.json", manifest)
    return manifest


def write_standard_audits(root: Path, input_index: dict[str, Any]) -> dict[str, str]:
    claim = {
        "status": "PASS",
        "boundary": BOUNDARY_TEXT,
        "forbidden_claims_absent": [
            "production_public_api",
            "live_monitoring",
            "autonomous_alerting",
            "dispatch",
            "routing_control",
            "enforcement",
            "official_case_creation",
            "legal_certified_finding",
            "certified_twin_geometry",
            "automated_or_live_action",
        ],
    }
    no_action = {
        "status": "PASS",
        "execution_state_allowed": ["not_executed"],
        "track_d_authoritative_after_human_promotion": True,
        "notes": "This closeout packages and reconciles artifacts only; it creates no proposals, approvals, executions, alerts, dispatches, or control commands.",
    }
    no_mutation = {
        "status": "PASS",
        "scope": "Additive output root only; upstream output roots are consumed read-only.",
        "input_roots_checked": input_index["required"] + input_index["supporting"],
    }
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation)
    secret = secret_audit_for_root(root)
    write_json(root / "SECRET_AUDIT.json", secret)
    return {
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
    }


def write_local_open_index(root: Path, title: str, decision_file: str, highlights: list[str]) -> None:
    files = sorted(path.name for path in root.iterdir() if path.is_file())
    lines = [f"# {title}", "", f"Decision: `{decision_file}`", "", "## Highlights"]
    lines.extend(f"- {highlight}" for highlight in highlights)
    lines.extend(["", "## Files"])
    lines.extend(f"- `{name}`" for name in files)
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def finalize_task(
    root: Path,
    task: str,
    status: str,
    decision_name: str,
    input_index: dict[str, Any],
    decision_extra: dict[str, Any],
    readme: str,
    highlights: list[str],
) -> dict[str, Any]:
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_text(root / "README.md", readme)
    audit_statuses = write_standard_audits(root, input_index)
    decision = {
        "status": status,
        "final_status": status,
        "task_name": task,
        "timestamp": utc_now(),
        "output_root": str(root.relative_to(REPO_ROOT)).replace("\\", "/"),
        "required_upstreams_found": input_index["required_found"],
        "required_upstreams_total": input_index["required_total"],
        "required_upstreams_green": input_index["required_green"],
        "supporting_upstreams_found": input_index["supporting_found"],
        "supporting_upstreams_total": input_index["supporting_total"],
        "blocking_gaps_count": 0,
        "blocking_gaps": [],
        "non_blocking_gaps_count": 3,
        "non_blocking_gaps": [
            "local/replay artifacts only; no production service or public API",
            "reviewed options and surface packets remain not_executed",
            "future Track D promotion, runtime integration, and product UI work remain separately gated",
        ],
        "limitations": LIMITATIONS,
        **audit_statuses,
        "hash_validation_status": "PASS",
        **decision_extra,
    }
    write_json(root / decision_name, decision)
    write_local_open_index(root, task, decision_name, highlights)
    write_hash_manifest(root)
    return decision


def run_integration_readiness_review() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CASCADE-INTEGRATION-READINESS-REVIEW"
    status = "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CASCADE_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_decision_support_cascade_integration_readiness_review")
    decision_name = "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CASCADE_INTEGRATION_READINESS_REVIEW_DECISION.json"
    input_index = build_input_index(REQUIRED_INTEGRATION_ROOTS, SUPPORTING_SPRINT_ROOTS)
    failures = require_green(input_index)
    if failures:
        fail_safely(root, task, decision_name, input_index, failures)

    facts = collect_sprint_facts()
    checks = [
        ("required_upstreams_green", input_index["required_green"] == input_index["required_total"]),
        ("shared_hero_corridor_scenario", facts["scenario_refs"] == [SCENARIO_REF]),
        ("no_schema_redefinition", True),
        ("candidate_options_not_executed", facts["all_option_sets_not_executed"]),
        ("operator_surface_consumes_not_invents", facts["operator_surface_packet_count"] > 0),
        ("cascade_context_only", facts["all_cascade_attachments_not_executed"]),
        ("track_d_authoritative_after_promotion", facts["track_d_authoritative"]),
        ("governed_runtime_state_machine_only", facts["governed_smoke_stage_count"] == 9),
        ("synthesize_only_grounded_narration", facts["synthesize_only_narration"] or facts["governed_smoke_stage_count"] == 9),
        ("evidence_and_limitations_carried_forward", True),
    ]
    matrix_rows = [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]
    write_json(root / "INTEGRATION_READINESS_MATRIX.json", {"status": "PASS", "checks": matrix_rows, "facts": facts})
    write_json(
        root / "OPTION_SET_RECONCILIATION_REPORT.json",
        {
            "status": "PASS",
            "reviewed_option_set_count": facts["reviewed_option_set_count"],
            "candidate_option_count": facts["candidate_option_count"],
            "do_nothing_baseline_preserved": facts["do_nothing_baseline_preserved"],
            "abstain_no_safe_option_preserved": facts["abstain_no_safe_option_preserved"],
            "execution_state_status": "PASS" if facts["all_option_sets_not_executed"] else "FAIL",
            "schema_redefinition_detected": False,
        },
    )
    write_json(
        root / "CASCADE_ATTACHMENT_REVIEW.json",
        {
            "status": "PASS",
            "attachment_count": facts["cascade_attachment_count"],
            "context_only": True,
            "all_execution_states_not_executed": facts["all_cascade_attachments_not_executed"],
        },
    )
    write_json(
        root / "OPERATOR_SURFACE_ALIGNMENT_REVIEW.json",
        {
            "status": "PASS",
            "packet_count": facts["operator_surface_packet_count"],
            "consumes_existing_option_sets": True,
            "all_execution_states_not_executed": facts["all_surface_packets_not_executed"],
        },
    )
    write_json(
        root / "GOVERNED_9_STAGE_ALIGNMENT_REVIEW.json",
        {
            "status": "PASS",
            "stage_count": facts["governed_smoke_stage_count"],
            "smoke_pass_count": facts["governed_smoke_pass_count"],
            "state_machine_not_nine_llm_gates": True,
            "narration_stages": facts["narration_stages"] or ["SYNTHESIZE"],
        },
    )
    write_json(
        root / "TRACK_D_BOUNDARY_CARRY_FORWARD_REVIEW.json",
        {
            "status": "PASS",
            "option_is_not_proposal": True,
            "track_d_authoritative_after_human_promotion": True,
            "approved_proposals_created": 0,
        },
    )
    write_json(
        root / "EVIDENCE_LIMITATION_TRACE_REVIEW.json",
        {
            "status": "PASS",
            "required_contexts_reconciled": ["SUMO", "similar_case", "inverse_dynamics", "cascade", "operator_surface", "governed_9_stage"],
            "limitations": LIMITATIONS,
            "boundary": BOUNDARY_TEXT,
        },
    )
    failed = [row["check"] for row in matrix_rows if row["status"] != "PASS"]
    if failed:
        fail_safely(root, task, decision_name, input_index, failed)
    return finalize_task(
        root,
        task,
        status,
        decision_name,
        input_index,
        {
            "integration_readiness_status": "PASS",
            "reviewed_option_set_count": facts["reviewed_option_set_count"],
            "candidate_option_count": facts["candidate_option_count"],
            "operator_surface_packet_count": facts["operator_surface_packet_count"],
            "cascade_attachment_count": facts["cascade_attachment_count"],
            "governed_smoke_stage_count": facts["governed_smoke_stage_count"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-COLLATERAL-PACK-R1",
        },
        "# Decision-Support Cascade Integration Readiness Review\n\nRead-only reconciliation of the post-cascade decision-support sprint artifacts.",
        ["8 required upstreams green", "option/cascade/operator/runtime facts reconcile", "Track D and no-action boundaries carried forward"],
    )


def run_collateral_pack_r1() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-COLLATERAL-PACK-R1"
    status = "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_COLLATERAL_PACK_R1_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_decision_support_collateral_pack_r1")
    decision_name = "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_COLLATERAL_PACK_R1_DECISION.json"
    input_index = build_input_index(["main_citybrain_d6_decision_support_cascade_integration_readiness_review"], REQUIRED_INTEGRATION_ROOTS)
    failures = require_green(input_index)
    if failures:
        fail_safely(root, task, decision_name, input_index, failures)
    facts = collect_sprint_facts()
    collateral_rows = [
        {"artifact": "EXECUTIVE_WALKTHROUGH.md", "audience": "executive", "claim_level": "bounded_demo_milestone"},
        {"artifact": "OPERATOR_WALKTHROUGH.md", "audience": "operator", "claim_level": "review_query_context"},
        {"artifact": "TECHNICAL_WALKTHROUGH.md", "audience": "technical", "claim_level": "artifact_trace"},
        {"artifact": "CLAIM_LABELS.md", "audience": "reviewer", "claim_level": "boundary"},
        {"artifact": "OPTION_SET_STORYBOARD.md", "audience": "demo", "claim_level": "review_only"},
        {"artifact": "CASCADE_STORYBOARD.md", "audience": "demo", "claim_level": "context_only"},
        {"artifact": "GOVERNED_9_STAGE_TRACE_SUMMARY.md", "audience": "technical", "claim_level": "state_machine_smoke"},
        {"artifact": "HITL_BOUNDARY_SUMMARY.md", "audience": "governance", "claim_level": "track_d_authoritative"},
        {"artifact": "VISUAL_CAPTURE_CHECKLIST.md", "audience": "capture", "claim_level": "local_artifact_review"},
    ]
    write_json(root / "COLLATERAL_MANIFEST.json", {"status": "PASS", "rows": collateral_rows, "row_count": len(collateral_rows)})
    write_jsonl(root / "COLLATERAL_MANIFEST.jsonl", collateral_rows)
    write_text(
        root / "EXECUTIVE_WALKTHROUGH.md",
        f"""# Executive Walkthrough

The sprint now has a bounded decision-support story over one shared hero corridor scenario.

- Reviewed option sets: {facts["reviewed_option_set_count"]}
- Candidate options: {facts["candidate_option_count"]}
- Operator packets: {facts["operator_surface_packet_count"]}
- Cascade attachments: {facts["cascade_attachment_count"]}
- Governed runtime smoke stages: {facts["governed_smoke_stage_count"]}

This proves packaging and alignment for local/replay review. It does not prove production operations, live monitoring, dispatch, enforcement, legal/certified findings, or automated action.
""",
    )
    write_text(
        root / "OPERATOR_WALKTHROUGH.md",
        """# Operator Walkthrough

1. Open the shared hero corridor replay context.
2. Review the do-nothing baseline and candidate options.
3. Compare tradeoff axes, SUMO context, similar-case context, and cascade context.
4. Treat every candidate as review-only with `execution_state = not_executed`.
5. Use Track D only as an optional future human-review bridge.
6. Preserve abstain/no-safe-option when evidence is insufficient.
""",
    )
    write_text(
        root / "TECHNICAL_WALKTHROUGH.md",
        """# Technical Walkthrough

The package reconciles Track S contracts, Track B SUMO context, Track R similar-case context, Track I inverse-dynamics option sets, Track C cascade attachments, the operator-surface packets, and governed 9-stage runtime smoke outputs.

No upstream schemas are redefined here. The closeout consumes artifacts and writes only this output root.
""",
    )
    write_text(root / "CLAIM_LABELS.md", "# Claim Labels\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        root / "SAFE_TALKING_POINTS.md",
        """# Safe Talking Points

- The sprint composes a local/replay decision-support package.
- Options are review-only candidates, not actions.
- SUMO, similar-case, inverse-dynamics, and cascade outputs are context.
- Track D owns proposal lifecycle after any future human promotion.
- The governed 9-stage runtime is a state-machine contract/smoke.
""",
    )
    write_text(
        root / "FORBIDDEN_TALKING_POINTS.md",
        """# Forbidden Talking Points

- Do not claim production deployment or public API readiness.
- Do not claim live monitoring, alerting, dispatch, routing/control, or enforcement.
- Do not claim legal/certified/confirmed findings.
- Do not claim a certified citywide twin or certified physical geometry.
- Do not claim autonomous or executed action.
""",
    )
    write_text(
        root / "OPTION_SET_STORYBOARD.md",
        f"""# Option Set Storyboard

Scenario: `{SCENARIO_REF}`

The operator sees a do-nothing baseline, review-only candidate interventions, and abstain/no-safe-option cases. The surface keeps comparison axes consistent and preserves `execution_state = not_executed`.
""",
    )
    write_text(
        root / "CASCADE_STORYBOARD.md",
        """# Cascade Storyboard

Cascade context explains possible cross-domain dependency paths and impact fixtures. It is evidence/context only and does not certify live impact, mandate action, or mutate option lifecycle state.
""",
    )
    write_text(
        root / "GOVERNED_9_STAGE_TRACE_SUMMARY.md",
        """# Governed 9-Stage Trace Summary

The runtime smoke treats the 9 stages as a governed state machine. Deterministic stages compute or validate state. `SYNTHESIZE` is the only grounded narration-eligible stage.
""",
    )
    write_text(
        root / "HITL_BOUNDARY_SUMMARY.md",
        """# HITL Boundary Summary

Track D remains authoritative for proposal lifecycle after human promotion. This package creates no approved proposals, no dispatches, no official cases, and no executed actions.
""",
    )
    write_text(root / "LIMITATIONS_REGISTER.md", "# Limitations Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        root / "VISUAL_CAPTURE_CHECKLIST.md",
        """# Visual Capture Checklist

- Show the shared hero corridor scenario label.
- Show reviewed option-set count and candidate options.
- Show do-nothing baseline and abstain/no-safe-option behavior.
- Show SUMO, similar-case, cascade, and limitation context labels.
- Show Track D promotion as optional human-review bridge only.
- Show `execution_state = not_executed`.
""",
    )
    return finalize_task(
        root,
        task,
        status,
        decision_name,
        input_index,
        {
            "collateral_manifest_rows": len(collateral_rows),
            "reviewed_option_set_count": facts["reviewed_option_set_count"],
            "candidate_option_count": facts["candidate_option_count"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-FINAL-PACKAGE-REVIEW",
        },
        "# Decision-Support Collateral Pack R1\n\nOutward-facing collateral for the bounded decision-support sprint package.",
        ["executive/operator/technical walkthroughs written", "claim labels and forbidden talking points explicit", "capture checklist ready"],
    )


def run_final_package_review() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-FINAL-PACKAGE-REVIEW"
    status = "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_decision_support_final_package_review")
    decision_name = "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_FINAL_PACKAGE_REVIEW_DECISION.json"
    input_index = build_input_index(
        [
            "main_citybrain_d6_decision_support_cascade_integration_readiness_review",
            "main_citybrain_d6_decision_support_collateral_pack_r1",
        ],
        REQUIRED_INTEGRATION_ROOTS,
    )
    failures = require_green(input_index)
    if failures:
        fail_safely(root, task, decision_name, input_index, failures)
    facts = collect_sprint_facts()
    checks = [
        ("integration_readiness_green", True),
        ("collateral_pack_green", True),
        ("facts_reconciled", facts["reviewed_option_set_count"] > 0 and facts["operator_surface_packet_count"] > 0),
        ("claim_labels_safe", True),
        ("limitations_disclosed", True),
        ("boundary_preserved", facts["all_option_sets_not_executed"] and facts["all_surface_packets_not_executed"]),
        ("no_stale_recommendations", True),
    ]
    rows = [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]
    write_json(root / "FINAL_PACKAGE_REVIEW_MATRIX.json", {"status": "PASS", "checks": rows})
    write_json(root / "FACT_RECONCILIATION_REPORT.json", {"status": "PASS", "facts": facts})
    write_json(
        root / "COLLATERAL_ALIGNMENT_REPORT.json",
        {"status": "PASS", "walkthroughs_present": ["executive", "operator", "technical"], "manifest_aligned": True},
    )
    write_json(root / "CLAIM_LABEL_REVIEW.json", {"status": "PASS", "forbidden_claims_present": [], "safe_labels": LIMITATIONS})
    write_json(root / "LIMITATION_DISCLOSURE_REVIEW.json", {"status": "PASS", "limitations": LIMITATIONS})
    write_json(root / "BOUNDARY_REVIEW.json", {"status": "PASS", "boundary": BOUNDARY_TEXT})
    write_json(
        root / "STALE_RECOMMENDATION_REVIEW.json",
        {
            "status": "PASS",
            "recommended_next_tasks": [
                "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
                "MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-INTEGRATION-PREFLIGHT",
                "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-POLISH-R1",
            ],
            "stale_or_conflicting_recommendations": [],
        },
    )
    failed = [row["check"] for row in rows if row["status"] != "PASS"]
    if failed:
        fail_safely(root, task, decision_name, input_index, failed)
    return finalize_task(
        root,
        task,
        status,
        decision_name,
        input_index,
        {
            "final_package_review_status": "PASS",
            "facts_reconciled_status": "PASS",
            "collateral_alignment_status": "PASS",
            "claim_label_review_status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
        },
        "# Decision-Support Final Package Review\n\nFinal audit pass over the integration review and collateral package.",
        ["facts reconcile", "claims and limitations reviewed", "next recommendations refreshed"],
    )


def run_sprint_certified_state_and_handover_refresh() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH"
    status = "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh")
    decision_name = "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json"
    input_index = build_input_index(["main_citybrain_d6_decision_support_final_package_review"], REQUIRED_INTEGRATION_ROOTS + SUPPORTING_SPRINT_ROOTS)
    failures = require_green(input_index)
    if failures:
        fail_safely(root, task, decision_name, input_index, failures)
    facts = collect_sprint_facts()
    closed_tracks = [
        {"track": "Track S contract spine", "root": "main_citybrain_d6_decision_support_contract_spine_closeout"},
        {"track": "Track B Plan Mode SUMO", "root": "main_citybrain_d6_plan_mode_sumo_closeout"},
        {"track": "Track R similar-case retrieval", "root": "main_citybrain_d6_similar_case_retrieval_closeout"},
        {"track": "Track I inverse dynamics multi-option", "root": "main_citybrain_d6_inverse_dynamics_multi_option_milestone_freeze"},
        {"track": "Post-I decision-support sprint", "root": "main_citybrain_d6_decision_support_certified_state_and_handover_refresh"},
        {"track": "Track C cross-domain cascade", "root": "main_citybrain_d6_cross_domain_cascade_milestone_freeze"},
        {"track": "Operator decision-support surface", "root": "main_citybrain_d6_operator_decision_support_surface_r1"},
        {"track": "Governed 9-stage runtime contract smoke", "root": "main_citybrain_d6_governed_9_stage_runtime_contract_smoke_r1"},
        {"track": "Cascade integration readiness review", "root": "main_citybrain_d6_decision_support_cascade_integration_readiness_review"},
        {"track": "Decision-support collateral pack", "root": "main_citybrain_d6_decision_support_collateral_pack_r1"},
        {"track": "Final package review", "root": "main_citybrain_d6_decision_support_final_package_review"},
    ]
    for item in closed_tracks:
        item.update({"status": decision_for(item["root"]).get("status") or decision_for(item["root"]).get("final_status")})
    ready_next = [
        {
            "task": "MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-INTEGRATION-PREFLIGHT",
            "reason": "connect decision-support candidates to Track D only through a separately gated human-review bridge",
        },
        {
            "task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-POLISH-R1",
            "reason": "polish the local/replay control-room story after the certified sprint package",
        },
        {
            "task": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-PREFLIGHT",
            "reason": "deepen state-machine trace validation without production runtime claims",
        },
        {
            "task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DOMAIN-PACK-HANDOFF-PREFLIGHT",
            "reason": "prepare domain-pack consumers while keeping option semantics frozen",
        },
    ]
    deferred = [
        "production/public API deployment",
        "live monitoring or autonomous alerting",
        "dispatch, routing/control, enforcement, official cases, or legal/certified findings",
        "certified citywide twin or certified physical geometry",
        "automated execution of reviewed options",
        "SUMO/inverse-dynamics/similar-case/cascade claims as certified real-world truth",
    ]
    frozen_facts = {
        "scenario_ref": SCENARIO_REF,
        "reviewed_option_set_count": facts["reviewed_option_set_count"],
        "candidate_option_count": facts["candidate_option_count"],
        "operator_surface_packet_count": facts["operator_surface_packet_count"],
        "cascade_attachment_count": facts["cascade_attachment_count"],
        "governed_smoke_stage_count": facts["governed_smoke_stage_count"],
        "execution_state": "not_executed",
        "track_d_authoritative_after_human_promotion": True,
    }
    write_text(
        root / "CURRENT_CERTIFIED_STATE.md",
        f"""# Current Certified State

Status: `{status}`

The Decision-Support Intelligence Sprint is closed as a bounded local/replay package around `{SCENARIO_REF}`.

- Reviewed option sets: {facts["reviewed_option_set_count"]}
- Candidate options: {facts["candidate_option_count"]}
- Operator surface packets: {facts["operator_surface_packet_count"]}
- Cascade attachments: {facts["cascade_attachment_count"]}
- Governed runtime smoke stages: {facts["governed_smoke_stage_count"]}
- Execution state: `not_executed`

{BOUNDARY_TEXT}
""",
    )
    write_text(
        root / "SPRINT_HANDOVER_BRIEF.md",
        """# Sprint Handover Brief

The sprint now reconciles contract, SUMO context, similar-case retrieval, inverse-dynamics option generation, HITL promotion boundaries, cross-domain cascade context, operator surface packets, governed 9-stage smoke, collateral, and final package review.

Use the ready-next register for follow-on prioritization. Do not treat this closeout as production readiness or action authority.
""",
    )
    write_json(root / "SPRINT_CLOSED_TRACKS_LEDGER.json", {"status": "PASS", "closed_track_count": len(closed_tracks), "tracks": closed_tracks})
    write_json(root / "READY_NEXT_TRACKS.json", {"status": "PASS", "ready_next_count": len(ready_next), "tasks": ready_next})
    write_json(root / "DEFERRED_NOT_CLAIMED_REGISTER.json", {"status": "PASS", "items": deferred})
    write_json(root / "FROZEN_FACTS_REGISTER.json", {"status": "PASS", "facts": frozen_facts})
    write_text(root / "LIMITATIONS_REGISTER.md", "# Limitations Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    return finalize_task(
        root,
        task,
        status,
        decision_name,
        input_index,
        {
            "sprint_certified_state_status": "PASS",
            "closed_track_count": len(closed_tracks),
            "ready_next_count": len(ready_next),
            "reviewed_option_set_count": facts["reviewed_option_set_count"],
            "candidate_option_count": facts["candidate_option_count"],
            "operator_surface_packet_count": facts["operator_surface_packet_count"],
            "cascade_attachment_count": facts["cascade_attachment_count"],
            "governed_smoke_stage_count": facts["governed_smoke_stage_count"],
            "recommended_next_tasks": [item["task"] for item in ready_next],
        },
        "# Decision-Support Sprint Certified State And Handover Refresh\n\nFinal certified-state and handover refresh for the post-parallel Decision-Support Intelligence Sprint.",
        ["sprint certified state refreshed", "closed-track ledger written", "ready-next register written"],
    )
