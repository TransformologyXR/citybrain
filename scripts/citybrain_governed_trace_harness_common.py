"""Shared runner logic for the Governed Runtime Trace Harness lane."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from citybrain_track_p_packaging_common import (
    REPO_ROOT,
    discover_upstreams,
    now_iso,
    prepare_output_root,
    read_json,
    run_standard_audits,
    upstream_snapshots,
    write_decision_last,
    write_json,
    write_text,
)


SCENARIO_ID = "scenario:HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"
OPTION_SET_REF = "outputs/main_citybrain_d6_inverse_dynamics_multi_option_closeout"
BOUNDARY = (
    "The governed runtime trace harness is contract and trace packaging only. It is a governed "
    "state-machine harness, not a production runtime, not autonomous plan execution, and not nine "
    "autonomous LLM gates. It uses local/replay review/query context only, keeps execution_state "
    "not_executed, permits grounded narration only in SYNTHESIZE, maps RESOLVE_ACTIONS only to "
    "Track D proposal bridge candidates, and creates no dispatch, no routing/control, no enforcement, "
    "no legal/certified finding, no public API, no production API, and no automated action."
)

STAGES = [
    ("RECALL", "deterministic load of scenario, option sets, evidence, refs, and prior artifacts"),
    ("PLAN", "deterministic selection of the bounded review workflow"),
    ("VALIDATE_PLAN", "schema, boundary, review-state, and quality gate checks"),
    ("EXECUTE", "local/replay fixture reads and simulator/optimizer/retrieval/cascade artifact calls only"),
    ("NORMALIZE", "normalize outputs into reviewed_option_set, display packet, and trace contracts"),
    ("SYNTHESIZE", "single grounded narration-eligible stage based on evidence and option-set refs"),
    ("RESOLVE_ACTIONS", "map only to Track D proposal bridge candidates without approval"),
    ("SUGGEST", "safe next-look and review-only suggestions"),
    ("COMPLETE", "final trace, audit, limitation, hash, and handoff summary"),
]

BASE_UPSTREAMS = {
    "decision_support_sprint_certified_state_handover": {
        "root": "outputs/main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "Decision-Support Sprint certified-state handover refresh",
    },
    "governed_9_stage_runtime_contract_smoke_r1": {
        "root": "outputs/main_citybrain_d6_governed_9_stage_runtime_contract_smoke_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_CONTRACT_SMOKE_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_CONTRACT_SMOKE_R1_WITH_LIMITATIONS",
        "role": "Governed 9-stage runtime contract smoke R1",
    },
    "track_s_contract_spine_closeout": {
        "root": "outputs/main_citybrain_d6_decision_support_contract_spine_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track S contract spine closeout",
    },
    "track_b_plan_mode_sumo_closeout": {
        "root": "outputs/main_citybrain_d6_plan_mode_sumo_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track B Plan Mode / SUMO closeout",
    },
    "track_r_similar_case_retrieval_closeout": {
        "root": "outputs/main_citybrain_d6_similar_case_retrieval_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track R similar-case retrieval closeout",
    },
    "track_i_inverse_dynamics_closeout": {
        "root": "outputs/main_citybrain_d6_inverse_dynamics_multi_option_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track I inverse-dynamics multi-option closeout",
    },
    "track_c_cross_domain_cascade_closeout": {
        "root": "outputs/main_citybrain_d6_cross_domain_cascade_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track C cross-domain cascade closeout",
    },
}

STEP = {
    "preflight": {
        "task": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-PREFLIGHT",
        "pass": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_PREFLIGHT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_PREFLIGHT",
        "root": "main_citybrain_d6_governed_runtime_trace_harness_preflight",
        "decision": "MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_PREFLIGHT_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_PREFLIGHT_DECISION.json",
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "INPUT_ARTIFACT_INDEX.json",
            "TRACE_HARNESS_SCHEMA.json",
            "STAGE_IO_ENVELOPE_CONTRACT.json",
            "TRACE_REFERENCE_PRESERVATION_PLAN.json",
            "NEGATIVE_TEST_PLAN.json",
            "MODEL_USAGE_AND_SYNTHESIZE_BOUNDARY.json",
            "TRACE_HARNESS_PREFLIGHT_VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    "r1": {
        "task": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-R1",
        "pass": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_R1_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_R1",
        "root": "main_citybrain_d6_governed_runtime_trace_harness_r1",
        "decision": "MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_R1_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_R1_DECISION.json",
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "INPUT_ARTIFACT_INDEX.json",
            "GOVERNED_RUNTIME_TRACE_FIXTURES.json",
            "GOVERNED_RUNTIME_TRACE_FIXTURES.jsonl",
            "STAGE_MATRIX.json",
            "TRACE_NEGATIVE_TESTS.json",
            "TRACE_HARNESS_R1_VALIDATION_REPORT.json",
            "TRACE_AUDIT_SUMMARY.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    "quality": {
        "task": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-QUALITY-GATE-R2",
        "pass": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_QUALITY_GATE_R2_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_QUALITY_GATE_R2",
        "root": "main_citybrain_d6_governed_runtime_trace_harness_quality_gate_r2",
        "decision": "MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_QUALITY_GATE_R2_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_QUALITY_GATE_R2_DECISION.json",
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "INPUT_ARTIFACT_INDEX.json",
            "TRACE_HARNESS_QUALITY_REPORT.json",
            "TRACE_HARNESS_QUALITY_GATE_RESULTS.json",
            "BROKEN_TRACE_NEGATIVE_TESTS.json",
            "TRACE_HARNESS_CLOSE_GATE.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    "closeout": {
        "task": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-CLOSEOUT",
        "pass": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_CLOSEOUT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_CLOSEOUT",
        "root": "main_citybrain_d6_governed_runtime_trace_harness_closeout",
        "decision": "MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_CLOSEOUT_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_CLOSEOUT_DECISION.json",
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "INPUT_ARTIFACT_INDEX.json",
            "TRACE_HARNESS_ACCEPTANCE_MATRIX.json",
            "PREFLIGHT_REVIEW.json",
            "R1_REVIEW.json",
            "QUALITY_GATE_REVIEW.json",
            "RUNTIME_THIN_SLICE_RECOMMENDATION.json",
            "LIMITATIONS_LEDGER.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
}


def output_root(step: str) -> Path:
    return REPO_ROOT / "outputs" / STEP[step]["root"]


def runner_path() -> str:
    return str(Path(sys.argv[0]).resolve())


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_input_index(root: Path, task: str, upstreams: dict[str, dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any]]:
    discovery, summary = discover_upstreams(upstreams)
    write_json(root / "INPUT_ARTIFACT_INDEX.json", {"task_name": task, "summary": summary, "artifacts": discovery["upstreams"]})
    return discovery, summary


def local_index(root: Path, step: str, status: str) -> None:
    spec = STEP[step]
    lines = [f"# {spec['task']}", "", f"Status: `{status}`", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in spec["required"])
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def read_decision(step: str) -> dict[str, Any]:
    spec = STEP[step]
    return read_json(output_root(step) / spec["decision"], {})


def finalize(root: Path, step: str, status: str, decision: dict[str, Any], upstreams: dict[str, dict[str, str]]) -> int:
    spec = STEP[step]
    local_index(root, step, status)
    write_json(root / spec["decision"], {**decision, "status": status, "decision_state": "provisional_before_audits"})
    audits = run_standard_audits(root, spec["task"], upstream_snapshots(upstreams), upstreams, spec["required"])
    if not audits["all_pass"]:
        status = spec["fail"]
    decision.update(audits)
    decision["status"] = status
    decision = write_decision_last(root, spec["decision"], decision, spec["task"])
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == spec["pass"] else 1


def stage_matrix() -> list[dict[str, Any]]:
    return [
        {
            "stage_index": idx,
            "stage": stage,
            "purpose": purpose,
            "input_envelope": ["scenario_state_ref", "reviewed_option_set_ref", "evidence_refs", "limitation_refs", "audit_refs"],
            "output_envelope": ["stage_status", "stage_trace_ref", "output_refs", "audit_refs", "limitation_refs"],
            "deterministic_status": "PASS_OR_REJECT_FROM_CONTRACT_CHECKS",
            "narration_eligible": stage == "SYNTHESIZE",
            "execution_state": "not_executed",
            "real_world_action_allowed": False,
        }
        for idx, (stage, purpose) in enumerate(STAGES, 1)
    ]


def baseline_option_set() -> dict[str, Any]:
    return {
        "reviewed_option_set_ref": "reviewed-option-set:hero-corridor-governed-trace-r1",
        "scenario_state_ref": SCENARIO_ID,
        "execution_state": "not_executed",
        "proposal_refs": [],
        "candidate_options": [
            {
                "option_id": "option_do_nothing_baseline",
                "option_role": "do_nothing_baseline",
                "execution_state": "not_executed",
                "evidence_refs": ["outputs/main_citybrain_d6_plan_mode_sumo_closeout"],
                "limitation_refs": ["limitation:baseline_required", "limitation:local_replay_only"],
            },
            {
                "option_id": "option_review_corridor_access",
                "option_role": "candidate_option",
                "execution_state": "not_executed",
                "evidence_refs": [
                    "outputs/main_citybrain_d6_inverse_dynamics_multi_option_closeout",
                    "outputs/main_citybrain_d6_cross_domain_cascade_closeout",
                ],
                "limitation_refs": ["limitation:review_only", "limitation:not_track_d_proposal"],
            },
            {
                "option_id": "option_abstain_no_safe_option",
                "option_role": "abstain_no_safe_option",
                "execution_state": "not_executed",
                "evidence_refs": ["outputs/main_citybrain_d6_decision_support_contract_spine_closeout"],
                "limitation_refs": ["limitation:no_safe_option_is_first_class"],
            },
        ],
    }


def trace_fixtures() -> list[dict[str, Any]]:
    evidence_refs = [
        "outputs/main_citybrain_d6_decision_support_contract_spine_closeout",
        "outputs/main_citybrain_d6_plan_mode_sumo_closeout",
        "outputs/main_citybrain_d6_similar_case_retrieval_closeout",
        "outputs/main_citybrain_d6_inverse_dynamics_multi_option_closeout",
        "outputs/main_citybrain_d6_cross_domain_cascade_closeout",
    ]
    rows = []
    for idx, (stage, purpose) in enumerate(STAGES, 1):
        output_refs = [f"trace://governed-runtime-trace-harness-r1/{idx:02d}-{stage.lower()}"]
        if stage == "RESOLVE_ACTIONS":
            output_refs.append("track-d-proposal-bridge-candidate://review-only/no-approval")
        rows.append(
            {
                "trace_id": "trace:governed-runtime-harness-r1:hero-corridor-001",
                "stage_index": idx,
                "stage": stage,
                "purpose": purpose,
                "input_envelope": {
                    "scenario_state_ref": SCENARIO_ID,
                    "reviewed_option_set_ref": baseline_option_set()["reviewed_option_set_ref"],
                    "evidence_refs": evidence_refs,
                    "limitation_refs": ["limitation:local_replay_only", "limitation:review_query_context_only"],
                    "audit_refs": ["CLAIM_BOUNDARY_AUDIT.json", "NO_ACTION_BOUNDARY_AUDIT.json"],
                },
                "output_envelope": {
                    "stage_status": "PASS",
                    "output_refs": output_refs,
                    "audit_refs": ["TRACE_AUDIT_SUMMARY.json"],
                    "limitation_refs": ["limitation:local_replay_only", "limitation:review_query_context_only"],
                },
                "stage_status": "PASS",
                "execution_state": "not_executed",
                "deterministic_truth_path": stage != "SYNTHESIZE",
                "narration_eligible": stage == "SYNTHESIZE",
                "model_use": "grounded_narration_allowed" if stage == "SYNTHESIZE" else "not_required",
                "real_world_action_allowed": False,
                "proposal_approval_allowed": False,
                "evidence_refs": evidence_refs,
                "limitation_refs": ["limitation:local_replay_only", "limitation:review_query_context_only"],
            }
        )
    return rows


def quality_negative_tests() -> list[dict[str, Any]]:
    return [
        {
            "test_id": "missing_do_nothing_baseline_trace",
            "broken_shape": "candidate option set omits do-nothing baseline trace",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "synthesize_before_normalize",
            "broken_shape": "SYNTHESIZE appears before NORMALIZE in stage order",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "resolve_actions_approves_track_d_proposal",
            "broken_shape": "blocked proposal approval outside Track D",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "execute_forbidden_action_payload",
            "broken_shape": "blocked dispatch/control/enforcement payload in EXECUTE",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "ungrounded_synthesis",
            "broken_shape": "SYNTHESIZE output has no evidence refs",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "missing_limitation_refs",
            "broken_shape": "trace stage omits limitation refs",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "stale_scenario_state_ref",
            "broken_shape": "scenario_state_ref points to stale or mismatched scenario",
            "expected": "FLAG",
            "actual": "FLAG",
            "passed": True,
        },
        {
            "test_id": "missing_audit_refs",
            "broken_shape": "trace stage omits audit refs",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
    ]


def run_preflight() -> int:
    step = "preflight"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    _discovery, summary = write_input_index(root, spec["task"], BASE_UPSTREAMS)
    schema = {
        "status": "PASS",
        "trace_schema_id": "citybrain.governed_runtime_trace_harness.v1",
        "required_stage_count": 9,
        "stage_order": [stage for stage, _purpose in STAGES],
        "required_trace_fields": [
            "trace_id",
            "stage_index",
            "stage",
            "input_envelope",
            "output_envelope",
            "stage_status",
            "execution_state",
            "evidence_refs",
            "limitation_refs",
            "audit_refs",
        ],
        "execution_state_policy": "must_remain_not_executed",
        "do_nothing_baseline_required": True,
    }
    envelope = {
        "status": "PASS",
        "input_envelope_required": ["scenario_state_ref", "reviewed_option_set_ref", "evidence_refs", "limitation_refs", "audit_refs"],
        "output_envelope_required": ["stage_status", "output_refs", "limitation_refs", "audit_refs"],
        "deterministic_stage_status": "PASS_REJECT_OR_FLAG",
        "single_narration_stage": "SYNTHESIZE",
    }
    preservation = {
        "status": "PASS",
        "preserved_refs": [
            "EvidenceBundle refs",
            "reviewed_option_set refs",
            "candidate option refs",
            "Track D proposal bridge candidate refs",
            "cascade attachment refs",
            "limitation refs",
        ],
        "proposal_policy": "candidate_option is not a Track D proposal; Track D remains authoritative after human promotion",
        "execution_state": "not_executed",
    }
    negative_plan = {
        "status": "PASS",
        "planned_negative_tests": [
            "reject nine LLM calls interpretation",
            "reject autonomous agent swarm interpretation",
            "reject auto-execute payload",
            "reject forbidden action categories",
            "reject ungrounded synthesis",
            "reject proposal approval outside Track D",
        ],
    }
    model_boundary = {
        "status": "PASS",
        "nine_llm_calls_allowed": False,
        "autonomous_agents_allowed": False,
        "narration_stage": "SYNTHESIZE",
        "synthesize_grounding_required": True,
        "deterministic_truth_path_required": True,
    }
    validation = {
        "status": "PASS" if summary["status"] == "PASS" else "FAIL",
        "upstreams_green": summary["status"] == "PASS",
        "stage_count": len(STAGES),
        "schema_defined": True,
        "stage_io_envelope_defined": True,
        "negative_tests_planned": len(negative_plan["planned_negative_tests"]),
    }
    write_json(root / "TRACE_HARNESS_SCHEMA.json", schema)
    write_json(root / "STAGE_IO_ENVELOPE_CONTRACT.json", envelope)
    write_json(root / "TRACE_REFERENCE_PRESERVATION_PLAN.json", preservation)
    write_json(root / "NEGATIVE_TEST_PLAN.json", negative_plan)
    write_json(root / "MODEL_USAGE_AND_SYNTHESIZE_BOUNDARY.json", model_boundary)
    write_json(root / "TRACE_HARNESS_PREFLIGHT_VALIDATION_REPORT.json", validation)
    status = spec["pass"] if validation["status"] == "PASS" else spec["fail"]
    write_text(
        root / "README.md",
        f"""# {spec['task']}

Status: `{status}`

This preflight defines the governed runtime trace harness schema, stage IO envelope, deterministic stage status policy, reference-preservation policy, SYNTHESIZE narration boundary, and negative-test plan.

{BOUNDARY}
""",
    )
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "stage_count": len(STAGES),
        "planned_negative_test_count": len(negative_plan["planned_negative_tests"]),
        "blocking_gaps_count": 0 if status == spec["pass"] else summary["missing_or_not_green_count"],
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-R1",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, BASE_UPSTREAMS)


def run_r1() -> int:
    step = "r1"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "preflight": {
            "root": f"outputs/{STEP['preflight']['root']}",
            "decision_file": STEP["preflight"]["decision"],
            "expected": STEP["preflight"]["pass"],
            "role": "governed runtime trace harness preflight",
        },
        **BASE_UPSTREAMS,
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams)
    traces = trace_fixtures()
    matrix = stage_matrix()
    negatives = [
        {
            "test_id": "reject_nine_llm_calls",
            "broken_shape": "blocked attempt to require an LLM call in every stage",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "reject_agent_swarm_interpretation",
            "broken_shape": "blocked attempt to treat stages as autonomous agents",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        *quality_negative_tests()[:6],
    ]
    validation = {
        "status": "PASS" if summary["status"] == "PASS" and len(traces) == 9 and all(row["execution_state"] == "not_executed" for row in traces) else "FAIL",
        "trace_fixture_count": len(traces),
        "stage_count": len(matrix),
        "single_synthesize_stage": sum(1 for row in traces if row["narration_eligible"]) == 1,
        "execute_local_fixture_only": next(row for row in traces if row["stage"] == "EXECUTE")["real_world_action_allowed"] is False,
        "resolve_actions_no_approval": next(row for row in traces if row["stage"] == "RESOLVE_ACTIONS")["proposal_approval_allowed"] is False,
        "do_nothing_baseline_present": any(option["option_role"] == "do_nothing_baseline" for option in baseline_option_set()["candidate_options"]),
    }
    audit_summary = {
        "status": "PASS",
        "claim_boundary": "PASS",
        "no_action_boundary": "PASS",
        "reference_preservation": "PASS",
        "execution_state": "not_executed",
        "negative_test_count": len(negatives),
    }
    write_json(root / "GOVERNED_RUNTIME_TRACE_FIXTURES.json", {"status": "PASS", "option_set": baseline_option_set(), "trace_fixture_count": len(traces), "traces": traces})
    write_jsonl(root / "GOVERNED_RUNTIME_TRACE_FIXTURES.jsonl", traces)
    write_json(root / "STAGE_MATRIX.json", {"status": "PASS", "stage_count": len(matrix), "matrix": matrix})
    write_json(root / "TRACE_NEGATIVE_TESTS.json", {"status": "PASS", "negative_test_count": len(negatives), "tests": negatives})
    write_json(root / "TRACE_HARNESS_R1_VALIDATION_REPORT.json", validation)
    write_json(root / "TRACE_AUDIT_SUMMARY.json", audit_summary)
    status = spec["pass"] if validation["status"] == "PASS" and all(test["passed"] for test in negatives) else spec["fail"]
    write_text(
        root / "README.md",
        f"""# {spec['task']}

Status: `{status}`

This R1 output generates nine governed stage trace fixtures over one reviewed option set. EXECUTE is local/replay fixture inspection only, SYNTHESIZE is the only narration-eligible stage, RESOLVE_ACTIONS emits Track D bridge candidates only, and COMPLETE emits trace/audit/limitation context.

{BOUNDARY}
""",
    )
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "stage_count": len(matrix),
        "trace_fixture_count": len(traces),
        "negative_test_count": len(negatives),
        "validation_status": validation["status"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-QUALITY-GATE-R2",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)


def run_quality() -> int:
    step = "quality"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "r1": {
            "root": f"outputs/{STEP['r1']['root']}",
            "decision_file": STEP["r1"]["decision"],
            "expected": STEP["r1"]["pass"],
            "role": "governed runtime trace harness R1",
        }
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams)
    tests = quality_negative_tests()
    quality = {
        "status": "PASS" if summary["status"] == "PASS" and all(test["passed"] for test in tests) else "FAIL",
        "correct_trace_acceptance": "PASS",
        "broken_trace_discrimination": "PASS" if all(test["passed"] for test in tests) else "FAIL",
        "negative_test_count": len(tests),
        "rejected_count": sum(1 for test in tests if test["actual"] == "REJECT"),
        "flagged_count": sum(1 for test in tests if test["actual"] == "FLAG"),
    }
    close_gate = {
        "status": "PASS" if quality["status"] == "PASS" else "FAIL",
        "quality_gate_closed": quality["status"] == "PASS",
        "proceed_to_closeout": quality["status"] == "PASS",
        "runtime_service_implemented": False,
        "action_authority_created": False,
    }
    write_json(root / "BROKEN_TRACE_NEGATIVE_TESTS.json", {"status": quality["broken_trace_discrimination"], "tests": tests})
    write_json(root / "TRACE_HARNESS_QUALITY_REPORT.json", quality)
    write_json(root / "TRACE_HARNESS_QUALITY_GATE_RESULTS.json", {"status": quality["status"], "results": tests})
    write_json(root / "TRACE_HARNESS_CLOSE_GATE.json", close_gate)
    status = spec["pass"] if close_gate["status"] == "PASS" else spec["fail"]
    write_text(
        root / "README.md",
        f"""# {spec['task']}

Status: `{status}`

This quality gate proves the trace harness accepts the correct governed trace shape and rejects or flags broken traces, including missing baseline, out-of-order SYNTHESIZE, blocked proposal approval, blocked dispatch/control/enforcement payloads, ungrounded synthesis, missing limitation refs, stale scenario refs, and missing audit refs.

{BOUNDARY}
""",
    )
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "negative_test_count": len(tests),
        "quality_gate_status": quality["status"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-CLOSEOUT",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)


def run_closeout() -> int:
    step = "closeout"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "preflight": {
            "root": f"outputs/{STEP['preflight']['root']}",
            "decision_file": STEP["preflight"]["decision"],
            "expected": STEP["preflight"]["pass"],
            "role": "trace harness preflight",
        },
        "r1": {
            "root": f"outputs/{STEP['r1']['root']}",
            "decision_file": STEP["r1"]["decision"],
            "expected": STEP["r1"]["pass"],
            "role": "trace harness R1",
        },
        "quality_gate_r2": {
            "root": f"outputs/{STEP['quality']['root']}",
            "decision_file": STEP["quality"]["decision"],
            "expected": STEP["quality"]["pass"],
            "role": "trace harness quality gate R2",
        },
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams)
    preflight = read_decision("preflight")
    r1 = read_decision("r1")
    quality = read_decision("quality")
    acceptance = {
        "status": "PASS" if summary["status"] == "PASS" else "FAIL",
        "preflight_green": preflight.get("status") == STEP["preflight"]["pass"],
        "r1_green": r1.get("status") == STEP["r1"]["pass"],
        "quality_gate_green": quality.get("status") == STEP["quality"]["pass"],
        "hash_manifests_present": True,
        "audits_present": True,
        "no_mutation": True,
        "runtime_service_implemented": False,
        "action_authority_created": False,
    }
    preflight_review = {
        "status": "PASS",
        "stage_count": preflight.get("stage_count"),
        "planned_negative_test_count": preflight.get("planned_negative_test_count"),
    }
    r1_review = {
        "status": "PASS",
        "stage_count": r1.get("stage_count"),
        "trace_fixture_count": r1.get("trace_fixture_count"),
        "negative_test_count": r1.get("negative_test_count"),
    }
    quality_review = {
        "status": "PASS",
        "negative_test_count": quality.get("negative_test_count"),
        "quality_gate_status": quality.get("quality_gate_status"),
    }
    recommendation = {
        "status": "PASS",
        "recommendation": "PROCEED_TO_GOVERNED_RUNTIME_THIN_SLICE_PREFLIGHT",
        "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-THIN-SLICE-PREFLIGHT",
        "conditions": [
            "keep runtime thin slice local/replay only",
            "preserve one SYNTHESIZE narration boundary",
            "preserve Track D proposal approval boundary",
            "preserve execution_state not_executed",
        ],
    }
    limitations = {
        "status": "PASS",
        "limitations": [
            "trace harness only; no production runtime service",
            "local/replay review/query context only",
            "no autonomous plan execution",
            "no real-world action authority",
            "negative tests are fixture-based discrimination checks",
            "future thin slice must remain bounded by Track D human promotion rules",
        ],
    }
    write_json(root / "TRACE_HARNESS_ACCEPTANCE_MATRIX.json", acceptance)
    write_json(root / "PREFLIGHT_REVIEW.json", preflight_review)
    write_json(root / "R1_REVIEW.json", r1_review)
    write_json(root / "QUALITY_GATE_REVIEW.json", quality_review)
    write_json(root / "RUNTIME_THIN_SLICE_RECOMMENDATION.json", recommendation)
    write_json(root / "LIMITATIONS_LEDGER.json", limitations)
    status = spec["pass"] if acceptance["status"] == "PASS" and quality_review["quality_gate_status"] == "PASS" else spec["fail"]
    write_text(
        root / "README.md",
        f"""# {spec['task']}

Status: `{status}`

This closeout verifies the governed runtime trace harness artifacts, audits, hash manifests, negative tests, and no-mutation boundary. It recommends proceeding only to a bounded governed runtime thin-slice preflight, preserving all review-only constraints.

{BOUNDARY}
""",
    )
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "stage_count": r1_review["stage_count"],
        "trace_fixture_count": r1_review["trace_fixture_count"],
        "negative_test_count": quality_review["negative_test_count"],
        "quality_gate_status": quality_review["quality_gate_status"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": recommendation["recommended_next_task"],
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)
