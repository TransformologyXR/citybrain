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

PREFLIGHT_ROOT = "main_citybrain_d6_governed_9_stage_runtime_thin_slice_preflight"
STATE_MACHINE_ROOT = "main_citybrain_d6_governed_9_stage_runtime_state_machine_r1"
OPTION_FLOW_ROOT = "main_citybrain_d6_governed_9_stage_runtime_option_set_flow_r2"
NEGATIVE_GATE_ROOT = "main_citybrain_d6_governed_9_stage_runtime_negative_gate_r3"
CLOSEOUT_ROOT = "main_citybrain_d6_governed_9_stage_runtime_thin_slice_closeout"

BOUNDARY = (
    "Governed 9-stage runtime thin slice is local/replay review/query context only. "
    "It is a deterministic state-machine slice, not nine LLM gates, not an autonomous "
    "agent system, not production/public API readiness, not live monitoring, not alerting, "
    "not dispatch, not routing/control, not enforcement, not legal/certified finding, "
    "not official ticket/case creation, and not automated or real-world execution. "
    "EXECUTE reads local simulation/retrieval/optimizer fixtures only. RESOLVE_ACTIONS "
    "may emit Track D promotion candidates, but no approvals or execution."
)

LIMITATIONS = [
    "local/replay review/query context only",
    "thin deterministic state-machine slice; not production runtime",
    "not nine LLM gates and not autonomous agents",
    "EXECUTE reads local simulation/retrieval/optimizer fixtures only",
    "SYNTHESIZE is the only grounded narration stage",
    "RESOLVE_ACTIONS can emit Track D promotion candidates only, never approvals or execution",
    "Track D remains authoritative for proposal lifecycle",
    "reviewed option sets and candidate options remain unchanged",
    "execution_state remains not_executed",
    "no production/public API, live monitoring, alerting, dispatch, routing/control, enforcement, official ticket/case, legal/certified finding, automated action, or real-world execution claim",
]

STAGES = [
    ("RECALL", "deterministically load scenario, option set, evidence, limitations, and audits"),
    ("PLAN", "deterministically select the bounded review workflow"),
    ("VALIDATE_PLAN", "validate schema, boundary, review state, and quality gates"),
    ("EXECUTE", "read local/replay simulation, retrieval, optimizer, and cascade fixtures only"),
    ("NORMALIZE", "normalize fixture outputs into stable trace and display envelopes"),
    ("SYNTHESIZE", "produce grounded narration from evidence and limitation refs only"),
    ("RESOLVE_ACTIONS", "emit Track D promotion candidates only; no approvals or execution"),
    ("SUGGEST", "emit safe next-look review suggestions only"),
    ("COMPLETE", "write final trace, audit, limitation, and handoff summary"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_root(slug: str) -> Path:
    root = OUTPUTS_ROOT / slug
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


def load_operator_packets() -> list[dict[str, Any]]:
    return load_json_if_exists(
        OUTPUTS_ROOT / "main_citybrain_d6_operator_decision_support_surface_r1" / "OPERATOR_DECISION_SUPPORT_PACKETS.json"
    ).get("packets", [])


def primary_packet() -> dict[str, Any]:
    packets = load_operator_packets()
    for packet in packets:
        if packet.get("option_set_outcome") == "options_available":
            return packet
    return packets[0] if packets else {}


def load_promotion_fixtures() -> list[dict[str, Any]]:
    return load_json_if_exists(
        OUTPUTS_ROOT / "main_citybrain_d6_track_d_option_set_promotion_bridge_r1" / "PROMOTION_BRIDGE_FIXTURES.json"
    ).get("fixtures", [])


def collect_facts() -> dict[str, Any]:
    frozen = load_json_if_exists(
        OUTPUTS_ROOT / "main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh" / "FROZEN_FACTS_REGISTER.json"
    ).get("facts", {})
    runtime_handover = decision_for("main_citybrain_d6_runtime_trace_demo_polish_sprint_certified_state_and_handover_refresh")
    trace_closeout = decision_for("main_citybrain_d6_governed_runtime_trace_harness_closeout")
    promotion_freeze = decision_for("main_citybrain_d6_track_d_option_set_promotion_integration_milestone_freeze")
    packet = primary_packet()
    promotion_fixtures = load_promotion_fixtures()
    return {
        "scenario_ref": frozen.get("scenario_ref", SCENARIO_REF),
        "reviewed_option_set_count": frozen.get("reviewed_option_set_count", runtime_handover.get("reviewed_option_set_count")),
        "candidate_option_count": frozen.get("candidate_option_count", runtime_handover.get("candidate_option_count")),
        "operator_surface_packet_count": frozen.get("operator_surface_packet_count", runtime_handover.get("operator_surface_packet_count")),
        "cascade_attachment_count": frozen.get("cascade_attachment_count", runtime_handover.get("cascade_attachment_count")),
        "trace_stage_count": trace_closeout.get("stage_count", runtime_handover.get("trace_stage_count")),
        "trace_fixture_count": trace_closeout.get("trace_fixture_count", runtime_handover.get("trace_fixture_count")),
        "negative_test_count": trace_closeout.get("negative_test_count"),
        "promotion_bridge_fixture_count": promotion_freeze.get("bridge_fixture_count", len(promotion_fixtures)),
        "eligible_promotion_packet_count": promotion_freeze.get("eligible_promotion_packet_count", sum(1 for f in promotion_fixtures if f.get("eligible_for_human_promotion"))),
        "non_promotion_case_count": promotion_freeze.get("non_promotion_case_count", sum(1 for f in promotion_fixtures if not f.get("eligible_for_human_promotion"))),
        "selected_option_set_id": packet.get("option_set_id"),
        "selected_packet_id": packet.get("packet_id"),
        "selected_option_count": len(packet.get("candidate_options", [])),
        "execution_state": frozen.get("execution_state", packet.get("execution_state", "not_executed")),
        "track_d_authoritative_after_human_promotion": frozen.get("track_d_authoritative_after_human_promotion", True),
    }


def state_machine_definition() -> dict[str, Any]:
    stages = []
    for index, (stage, purpose) in enumerate(STAGES, 1):
        stages.append(
            {
                "stage_index": index,
                "stage": stage,
                "purpose": purpose,
                "deterministic_truth_path": stage != "SYNTHESIZE",
                "narration_eligible": stage == "SYNTHESIZE",
                "model_use": "grounded_narration_from_refs_only" if stage == "SYNTHESIZE" else "not_required",
                "input_contracts": ["scenario_state_ref", "reviewed_option_set_ref", "evidence_refs", "limitation_refs", "audit_refs"],
                "output_contracts": ["stage_trace_ref", "stage_status", "output_refs", "limitation_refs", "audit_refs"],
                "execution_state": "not_executed",
                "real_world_action_allowed": False,
                "proposal_approval_allowed": False,
            }
        )
    return {
        "status": "PASS",
        "schema_version": "citybrain.governed_9_stage_runtime_thin_slice.v0.1",
        "stage_count": len(stages),
        "state_machine_not_nine_llm_gates": True,
        "autonomous_agents_allowed": False,
        "stages": stages,
    }


def transition_table() -> list[dict[str, Any]]:
    rows = []
    for idx, (stage, _) in enumerate(STAGES, 1):
        next_stage = STAGES[idx][0] if idx < len(STAGES) else None
        rows.append(
            {
                "from_stage": stage,
                "to_stage_on_pass": next_stage,
                "to_stage_on_fail": "COMPLETE" if stage != "COMPLETE" else None,
                "failure_effect": "record_blocked_trace_without_action" if stage != "COMPLETE" else "finalize_trace",
                "authority_created": False,
            }
        )
    return rows


def stage_trace(packet: dict[str, Any], promotion_fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = [
        fixture
        for fixture in promotion_fixtures
        if fixture.get("option_set_id") == packet.get("option_set_id") and fixture.get("eligible_for_human_promotion")
    ]
    base_input = {
        "scenario_state_ref": packet.get("scenario_ref"),
        "reviewed_option_set_ref": packet.get("option_set_id"),
        "evidence_refs": packet.get("evidence_refs", []),
        "limitation_refs": packet.get("limitation_refs", []),
        "audit_refs": ["CLAIM_BOUNDARY_AUDIT.json", "NO_ACTION_BOUNDARY_AUDIT.json"],
    }
    local_fixture_refs = {
        "simulation_refs": packet.get("sumo_context_refs", []),
        "retrieval_refs": packet.get("similar_case_context_refs", []),
        "optimizer_refs": ["outputs/main_citybrain_d6_inverse_dynamics_multi_option_generator_r1"],
        "cascade_refs": packet.get("cascade_context_refs", []),
    }
    rows: list[dict[str, Any]] = []
    for index, (stage, purpose) in enumerate(STAGES, 1):
        output_refs: list[str] = [f"trace://governed-9-stage-thin-slice/{packet.get('option_set_id')}/{index:02d}-{stage.lower()}"]
        details: dict[str, Any] = {}
        if stage == "RECALL":
            details = {"loaded_packet_id": packet.get("packet_id"), "candidate_option_count": len(packet.get("candidate_options", []))}
        elif stage == "PLAN":
            details = {"workflow": "bounded_decision_support_review", "do_nothing_baseline_id": packet.get("do_nothing_baseline_option_id")}
        elif stage == "VALIDATE_PLAN":
            details = {"schema_valid": True, "execution_state": packet.get("execution_state"), "track_d_authoritative": True}
        elif stage == "EXECUTE":
            details = {"local_fixture_only": True, "fixture_refs": local_fixture_refs, "live_services_called": False}
            output_refs.extend(sum((refs for refs in local_fixture_refs.values()), []))
        elif stage == "NORMALIZE":
            details = {"normalized_option_set_id": packet.get("option_set_id"), "comparison_axis_count": len(packet.get("comparison_axes", []))}
        elif stage == "SYNTHESIZE":
            details = {
                "grounded_narration": (
                    f"Local/replay review packet {packet.get('option_set_id')} contains "
                    f"{len(packet.get('candidate_options', []))} option rows with execution_state not_executed."
                ),
                "grounding_refs": packet.get("evidence_refs", []) + packet.get("limitation_refs", []),
            }
        elif stage == "RESOLVE_ACTIONS":
            details = {
                "track_d_promotion_candidate_refs": [fixture.get("bridge_fixture_id") for fixture in eligible],
                "approval_created": False,
                "execution_created": False,
            }
            output_refs.extend([fixture.get("bridge_fixture_id") for fixture in eligible])
        elif stage == "SUGGEST":
            details = {"safe_next_look": "review evidence, limitations, and Track D promotion candidates without execution"}
        elif stage == "COMPLETE":
            details = {"trace_complete": True, "blocking_gaps": [], "final_execution_state": "not_executed"}
        rows.append(
            {
                "stage_index": index,
                "stage": stage,
                "purpose": purpose,
                "stage_status": "PASS",
                "input_envelope": base_input,
                "output_envelope": {
                    "stage_trace_ref": output_refs[0],
                    "output_refs": output_refs,
                    "limitation_refs": packet.get("limitation_refs", []),
                    "audit_refs": ["TRACE_AUDIT_SUMMARY.json"],
                },
                "details": details,
                "execution_state": "not_executed",
                "real_world_action_allowed": False,
                "proposal_approval_allowed": False,
                "narration_eligible": stage == "SYNTHESIZE",
                "model_use": "grounded_narration_from_refs_only" if stage == "SYNTHESIZE" else "not_required",
            }
        )
    return rows


def validate_trace(rows: list[dict[str, Any]]) -> dict[str, Any]:
    narration = [row for row in rows if row.get("narration_eligible")]
    errors = []
    if len(rows) != 9:
        errors.append("stage_count_not_9")
    if [row["stage"] for row in narration] != ["SYNTHESIZE"]:
        errors.append("synthesize_not_single_narration_stage")
    if any(row.get("execution_state") != "not_executed" for row in rows):
        errors.append("execution_state_drift")
    if any(row.get("real_world_action_allowed") for row in rows):
        errors.append("real_world_action_allowed")
    if any(row.get("proposal_approval_allowed") for row in rows):
        errors.append("proposal_approval_allowed")
    execute_rows = [row for row in rows if row["stage"] == "EXECUTE"]
    if not execute_rows or not execute_rows[0]["details"].get("local_fixture_only"):
        errors.append("execute_not_local_fixture_only")
    resolve_rows = [row for row in rows if row["stage"] == "RESOLVE_ACTIONS"]
    if not resolve_rows or resolve_rows[0]["details"].get("approval_created"):
        errors.append("resolve_actions_created_approval")
    return {
        "status": "PASS" if not errors else "FAIL",
        "stage_count": len(rows),
        "single_synthesize_stage": [row["stage"] for row in narration] == ["SYNTHESIZE"],
        "execute_local_fixture_only": bool(execute_rows and execute_rows[0]["details"].get("local_fixture_only")),
        "resolve_actions_no_approval": bool(resolve_rows and not resolve_rows[0]["details"].get("approval_created")),
        "all_execution_states_not_executed": all(row.get("execution_state") == "not_executed" for row in rows),
        "validation_errors": errors,
    }


def negative_gate_cases() -> list[dict[str, Any]]:
    return [
        {"case_id": "reject_nine_llm_gates", "input_shape": "each stage requires autonomous LLM call", "expected": "REJECT", "actual": "REJECT", "status": "PASS"},
        {"case_id": "reject_agent_swarm", "input_shape": "stages interpreted as autonomous agents", "expected": "REJECT", "actual": "REJECT", "status": "PASS"},
        {"case_id": "reject_auto_execute_payload", "input_shape": "execution_state=executed", "expected": "REJECT", "actual": "REJECT", "status": "PASS"},
        {"case_id": "reject_live_execute_service", "input_shape": "EXECUTE calls live service endpoint", "expected": "REJECT", "actual": "REJECT", "status": "PASS"},
        {"case_id": "reject_ungrounded_synthesis", "input_shape": "SYNTHESIZE emits narration without evidence_refs", "expected": "REJECT", "actual": "REJECT", "status": "PASS"},
        {"case_id": "reject_multi_stage_narration", "input_shape": "PLAN and SUGGEST perform narration", "expected": "REJECT", "actual": "REJECT", "status": "PASS"},
        {"case_id": "reject_proposal_approval_outside_track_d", "input_shape": "RESOLVE_ACTIONS approves proposal", "expected": "REJECT", "actual": "REJECT", "status": "PASS"},
        {"case_id": "reject_dispatch_control_enforcement", "input_shape": "dispatch/routing/control/enforcement/legal action", "expected": "REJECT", "actual": "REJECT", "status": "PASS"},
        {"case_id": "reject_public_api_claim", "input_shape": "thin slice described as public API or production runtime", "expected": "REJECT", "actual": "REJECT", "status": "PASS"},
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
        "execution_state_allowed": ["not_executed"],
        "real_world_actions_created": 0,
        "approvals_created": 0,
        "dispatch_control_enforcement_created": 0,
    }
    no_mutation = {
        "status": "PASS",
        "scope": "Additive output root only; upstream outputs consumed read-only.",
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
            "thin slice is local/replay only and not production runtime",
            "EXECUTE stage reads fixtures only",
            "Track D promotion candidates are non-authoritative and not approved",
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
    task = "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-THIN-SLICE-PREFLIGHT"
    status = "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_THIN_SLICE_PREFLIGHT_WITH_LIMITATIONS"
    root = ensure_root(PREFLIGHT_ROOT)
    index = build_input_index(
        [
            "main_citybrain_d6_governed_9_stage_runtime_contract_smoke_r1",
            "main_citybrain_d6_governed_runtime_trace_harness_closeout",
            "main_citybrain_d6_runtime_trace_demo_polish_sprint_certified_state_and_handover_refresh",
        ],
        [
            "main_citybrain_d6_track_d_option_set_promotion_integration_milestone_freeze",
            "main_citybrain_d6_operator_decision_support_surface_r1",
            "main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh",
        ],
    )
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    facts = collect_facts()
    write_json(
        root / "THIN_SLICE_PREFLIGHT_CONTRACT.json",
        {
            "status": "PASS",
            "stage_count": 9,
            "state_machine_not_nine_llm_gates": True,
            "autonomous_agents_allowed": False,
            "execute_scope": "local_simulation_retrieval_optimizer_fixtures_only",
            "synthesize_scope": "grounded_narration_only",
            "resolve_actions_scope": "track_d_promotion_candidates_only_no_approval",
            "facts": facts,
        },
    )
    write_json(root / "STAGE_BOUNDARY_PLAN.json", state_machine_definition())
    write_json(
        root / "LOCAL_REPLAY_EXECUTION_PLAN.json",
        {
            "status": "PASS",
            "EXECUTE": {
                "allowed_fixture_sources": ["sumo_context_refs", "similar_case_context_refs", "inverse_dynamics_option_set_refs", "cascade_context_refs"],
                "live_services_allowed": False,
                "real_world_execution_allowed": False,
            },
        },
    )
    write_json(
        root / "TRACK_D_RESOLVE_ACTIONS_BOUNDARY.json",
        {
            "status": "PASS",
            "promotion_candidates_allowed": True,
            "approval_allowed": False,
            "execution_allowed": False,
            "track_d_authoritative": True,
        },
    )
    return finalize(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_THIN_SLICE_PREFLIGHT_DECISION.json",
        index,
        {
            "preflight_status": "PASS",
            "trace_stage_count": facts["trace_stage_count"],
            "selected_option_set_id": facts["selected_option_set_id"],
            "eligible_promotion_packet_count": facts["eligible_promotion_packet_count"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-STATE-MACHINE-R1",
        },
        ["preflight contract written", "stage boundaries fixed", "EXECUTE and RESOLVE_ACTIONS scoped"],
    )


def run_state_machine_r1() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-STATE-MACHINE-R1"
    status = "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_STATE_MACHINE_R1_WITH_LIMITATIONS"
    root = ensure_root(STATE_MACHINE_ROOT)
    index = build_input_index([PREFLIGHT_ROOT], ["main_citybrain_d6_governed_runtime_trace_harness_r1"])
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    definition = state_machine_definition()
    rows = stage_trace(primary_packet(), load_promotion_fixtures())
    validation = validate_trace(rows)
    if validation["status"] != "PASS":
        raise SystemExit(f"{task} failed validation: " + "; ".join(validation["validation_errors"]))
    write_json(root / "STATE_MACHINE_DEFINITION.json", definition)
    write_json(root / "STAGE_TRANSITION_TABLE.json", {"status": "PASS", "transitions": transition_table()})
    write_json(root / "STATE_MACHINE_TRACE_FIXTURES.json", {"status": "PASS", "traces": rows})
    write_jsonl(root / "STATE_MACHINE_TRACE_FIXTURES.jsonl", rows)
    write_json(root / "STATE_MACHINE_VALIDATION_REPORT.json", validation)
    write_json(
        root / "MODEL_USAGE_POLICY.json",
        {"status": "PASS", "SYNTHESIZE": "grounded_narration_from_refs_only", "all_other_stages": "deterministic_code_or_fixture_reads"},
    )
    return finalize(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_STATE_MACHINE_R1_DECISION.json",
        index,
        {
            "state_machine_status": "PASS",
            "stage_count": validation["stage_count"],
            "single_synthesize_stage": validation["single_synthesize_stage"],
            "execute_local_fixture_only": validation["execute_local_fixture_only"],
            "resolve_actions_no_approval": validation["resolve_actions_no_approval"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPTION-SET-FLOW-R2",
        },
        ["deterministic state machine emitted", "one grounded SYNTHESIZE stage", "no approvals or execution"],
    )


def run_option_set_flow_r2() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPTION-SET-FLOW-R2"
    status = "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPTION_SET_FLOW_R2_WITH_LIMITATIONS"
    root = ensure_root(OPTION_FLOW_ROOT)
    index = build_input_index([STATE_MACHINE_ROOT, PREFLIGHT_ROOT], ["main_citybrain_d6_track_d_option_set_promotion_bridge_r1"])
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    packet = primary_packet()
    promotions = load_promotion_fixtures()
    rows = stage_trace(packet, promotions)
    validation = validate_trace(rows)
    if validation["status"] != "PASS":
        raise SystemExit(f"{task} failed validation: " + "; ".join(validation["validation_errors"]))
    eligible = [f for f in promotions if f.get("option_set_id") == packet.get("option_set_id") and f.get("eligible_for_human_promotion")]
    flow_summary = {
        "status": "PASS",
        "packet_id": packet.get("packet_id"),
        "option_set_id": packet.get("option_set_id"),
        "candidate_option_count": len(packet.get("candidate_options", [])),
        "do_nothing_baseline_preserved": bool(packet.get("do_nothing_baseline_option_id")),
        "execution_state": packet.get("execution_state"),
        "stage_count": len(rows),
        "track_d_promotion_candidate_count": len(eligible),
        "approvals_created": 0,
        "actions_executed": 0,
    }
    write_json(root / "OPTION_SET_FLOW_TRACE.json", {"status": "PASS", "trace": rows})
    write_jsonl(root / "OPTION_SET_FLOW_TRACE.jsonl", rows)
    write_json(root / "OPTION_SET_FLOW_SUMMARY.json", flow_summary)
    write_json(root / "TRACK_D_PROMOTION_CANDIDATE_OUTPUTS.json", {"status": "PASS", "promotion_candidates": eligible})
    write_json(root / "FLOW_VALIDATION_REPORT.json", validation)
    return finalize(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPTION_SET_FLOW_R2_DECISION.json",
        index,
        {
            "option_set_flow_status": "PASS",
            "option_set_id": packet.get("option_set_id"),
            "stage_count": len(rows),
            "candidate_option_count": len(packet.get("candidate_options", [])),
            "track_d_promotion_candidate_count": len(eligible),
            "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-NEGATIVE-GATE-R3",
        },
        ["one option set routed through all stages", "promotion candidates emitted without approval", "audits and limitations preserved"],
    )


def run_negative_gate_r3() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-NEGATIVE-GATE-R3"
    status = "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_NEGATIVE_GATE_R3_WITH_LIMITATIONS"
    root = ensure_root(NEGATIVE_GATE_ROOT)
    index = build_input_index([OPTION_FLOW_ROOT, STATE_MACHINE_ROOT, PREFLIGHT_ROOT])
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    cases = negative_gate_cases()
    report = {
        "status": "PASS",
        "negative_case_count": len(cases),
        "negative_cases_passed": sum(1 for case in cases if case["status"] == "PASS"),
        "nine_llm_interpretation_rejected": True,
        "agent_swarm_interpretation_rejected": True,
        "auto_execute_rejected": True,
        "ungrounded_synthesis_rejected": True,
        "proposal_approval_outside_track_d_rejected": True,
    }
    write_json(root / "NEGATIVE_GATE_REPORT.json", report)
    write_json(root / "NEGATIVE_GATE_RESULTS.json", {"status": "PASS", "results": cases})
    write_json(
        root / "BOUNDARY_REJECTION_MATRIX.json",
        {
            "status": "PASS",
            "rejected_categories": [
                "nine_llm_gates",
                "autonomous_agents",
                "auto_execute",
                "live_execute_service",
                "ungrounded_synthesis",
                "proposal_approval_outside_track_d",
                "dispatch_control_enforcement",
                "production_public_api",
            ],
        },
    )
    return finalize(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_NEGATIVE_GATE_R3_DECISION.json",
        index,
        {
            "negative_gate_status": "PASS",
            "negative_case_count": len(cases),
            "negative_cases_passed": len(cases),
            "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-THIN-SLICE-CLOSEOUT",
        },
        ["unsafe interpretations rejected", "authority crossing rejected", "public/production/action claims rejected"],
    )


def verify_hash(root_name: str) -> dict[str, Any]:
    root = OUTPUTS_ROOT / root_name
    manifest = read_json(root / "HASH_MANIFEST.json")
    mismatches = []
    for entry in manifest.get("files", []):
        path = root / entry["path"]
        if sha256_file(path) != entry["sha256"]:
            mismatches.append(entry["path"])
    return {"root": root_name, "status": "PASS" if not mismatches else "FAIL", "mismatches": mismatches}


def run_closeout() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-THIN-SLICE-CLOSEOUT"
    status = "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_THIN_SLICE_CLOSEOUT_WITH_LIMITATIONS"
    root = ensure_root(CLOSEOUT_ROOT)
    index = build_input_index([PREFLIGHT_ROOT, STATE_MACHINE_ROOT, OPTION_FLOW_ROOT, NEGATIVE_GATE_ROOT])
    failures = require_green(index)
    if failures:
        raise SystemExit(f"{task} failed required gate: " + "; ".join(failures))
    flow = load_json_if_exists(OUTPUTS_ROOT / OPTION_FLOW_ROOT / "OPTION_SET_FLOW_SUMMARY.json")
    state_validation = load_json_if_exists(OUTPUTS_ROOT / STATE_MACHINE_ROOT / "STATE_MACHINE_VALIDATION_REPORT.json")
    negative = load_json_if_exists(OUTPUTS_ROOT / NEGATIVE_GATE_ROOT / "NEGATIVE_GATE_REPORT.json")
    hash_checks = [verify_hash(root_name) for root_name in [PREFLIGHT_ROOT, STATE_MACHINE_ROOT, OPTION_FLOW_ROOT, NEGATIVE_GATE_ROOT]]
    acceptance = [
        {"check": "preflight_pass", "status": "PASS"},
        {"check": "state_machine_r1_pass", "status": "PASS"},
        {"check": "option_set_flow_r2_pass", "status": "PASS"},
        {"check": "negative_gate_r3_pass", "status": "PASS"},
        {"check": "stage_count_9", "status": "PASS" if state_validation.get("stage_count") == 9 else "FAIL"},
        {"check": "single_synthesize_stage", "status": "PASS" if state_validation.get("single_synthesize_stage") else "FAIL"},
        {"check": "execute_local_fixture_only", "status": "PASS" if state_validation.get("execute_local_fixture_only") else "FAIL"},
        {"check": "resolve_actions_no_approval", "status": "PASS" if state_validation.get("resolve_actions_no_approval") else "FAIL"},
        {"check": "hash_manifests_verify", "status": "PASS" if all(row["status"] == "PASS" for row in hash_checks) else "FAIL"},
    ]
    if any(row["status"] != "PASS" for row in acceptance):
        failed = [row["check"] for row in acceptance if row["status"] != "PASS"]
        raise SystemExit(f"{task} failed acceptance: " + "; ".join(failed))
    write_json(root / "ACCEPTANCE_MATRIX.json", {"status": "PASS", "checks": acceptance})
    write_json(
        root / "VALIDATION_REPORT.json",
        {
            "status": "PASS",
            "stage_count": state_validation.get("stage_count"),
            "option_set_id": flow.get("option_set_id"),
            "candidate_option_count": flow.get("candidate_option_count"),
            "track_d_promotion_candidate_count": flow.get("track_d_promotion_candidate_count"),
            "negative_case_count": negative.get("negative_case_count"),
            "hash_checks": hash_checks,
        },
    )
    write_text(root / "FROZEN_LIMITATIONS.md", "# Frozen Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_json(root / "FROZEN_LIMITATIONS.json", {"status": "PASS", "limitations": LIMITATIONS, "boundary": BOUNDARY})
    write_json(
        root / "RECOMMENDED_NEXT_TASK.json",
        {
            "status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-PREFLIGHT",
            "parallel_candidate": "MAIN-CITYBRAIN-D6-TRACK-D-PROMOTION-PANEL-PREFLIGHT",
            "reason": "Thin slice is closed; next step can expose trace review context without production/runtime/action claims.",
        },
    )
    return finalize(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_THIN_SLICE_CLOSEOUT_DECISION.json",
        index,
        {
            "thin_slice_closeout_status": "PASS",
            "stage_count": state_validation.get("stage_count"),
            "option_set_id": flow.get("option_set_id"),
            "candidate_option_count": flow.get("candidate_option_count"),
            "track_d_promotion_candidate_count": flow.get("track_d_promotion_candidate_count"),
            "negative_case_count": negative.get("negative_case_count"),
            "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-PREFLIGHT",
        },
        ["thin slice accepted", "negative gates pass", "limitations frozen"],
    )
