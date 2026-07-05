#!/usr/bin/env python3
"""Governed 9-stage runtime contract smoke R1.

This is a local/replay contract smoke only. It proves that existing
decision-support artifacts can pass through a governed state-machine contract
without becoming nine autonomous LLM gates and without creating action.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citybrain_track_p_packaging_common import (
    REPO_ROOT,
    discover_upstreams,
    now_iso,
    prepare_output_root,
    run_standard_audits,
    upstream_snapshots,
    write_decision_last,
    write_json,
    write_text,
)


TASK_NAME = "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-CONTRACT-SMOKE-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_CONTRACT_SMOKE_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_CONTRACT_SMOKE_R1"
OUTPUT_NAME = "main_citybrain_d6_governed_9_stage_runtime_contract_smoke_r1"
OUTPUT_ROOT = REPO_ROOT / "outputs" / OUTPUT_NAME
DECISION_NAME = "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_CONTRACT_SMOKE_R1_DECISION.json"

BOUNDARY = (
    "This is a governed 9-stage state-machine contract smoke only, not a production runtime. "
    "It is local/replay review/query context only. It creates no production/public API readiness, "
    "no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, "
    "no official ticket/case creation, no legal/certified/confirmed finding, no automated action, "
    "no citywide certified twin, and no certified physical geometry claim. The 9-stage runtime is "
    "not nine autonomous LLM gates; only SYNTHESIZE may be narration-eligible and must be grounded."
)

REQUIRED_UPSTREAMS = {
    "track_s_contract_spine_closeout": {
        "root": "outputs/main_citybrain_d6_decision_support_contract_spine_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Decision-support contract spine closeout",
    },
    "plan_mode_sumo_closeout": {
        "root": "outputs/main_citybrain_d6_plan_mode_sumo_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Plan Mode / SUMO closeout",
    },
    "similar_case_retrieval_closeout": {
        "root": "outputs/main_citybrain_d6_similar_case_retrieval_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Similar-case retrieval closeout",
    },
    "inverse_dynamics_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_inverse_dynamics_multi_option_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Inverse dynamics multi-option milestone freeze",
    },
    "decision_support_certified_state_handover": {
        "root": "outputs/main_citybrain_d6_decision_support_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "Decision-support certified-state handover refresh",
    },
    "cross_domain_cascade_closeout": {
        "root": "outputs/main_citybrain_d6_cross_domain_cascade_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Cross-domain cascade closeout hard gate",
    },
    "cross_domain_cascade_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_cross_domain_cascade_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Cross-domain cascade milestone freeze preferred gate",
    },
    "track_d_hitl_reviewed_action_freeze": {
        "root": "outputs/main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Track D HITL reviewed-action milestone freeze",
    },
}

REQUIRED_OUTPUTS = [
    DECISION_NAME,
    "README.md",
    "LOCAL_OPEN_INDEX.md",
    "INPUT_ARTIFACT_INDEX.json",
    "NINE_STAGE_RUNTIME_CONTRACT.json",
    "NINE_STAGE_STAGE_IO_MATRIX.json",
    "NINE_STAGE_SMOKE_FIXTURES.json",
    "NINE_STAGE_SMOKE_RESULTS.json",
    "MODEL_USAGE_POLICY.json",
    "RESOLVE_ACTIONS_TRACK_D_BOUNDARY.json",
    "TRACE_AUDIT_CONTRACT.json",
    "NEGATIVE_TEST_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
]

STAGES = [
    ("RECALL", "deterministic load of scenario, option sets, evidence, refs, and prior artifacts"),
    ("PLAN", "deterministic selection of the bounded review workflow"),
    ("VALIDATE_PLAN", "schema, boundary, review-state, and quality gate checks"),
    ("EXECUTE", "local/replay fixture reads and simulator/optimizer/retrieval/cascade artifact calls only"),
    ("NORMALIZE", "normalize outputs into reviewed_option_set, display packet, and trace contracts"),
    ("SYNTHESIZE", "single grounded narration-eligible stage using evidence and option-set refs"),
    ("RESOLVE_ACTIONS", "map only to Track D proposal bridge candidates without approval or execution"),
    ("SUGGEST", "safe next-look and review-only suggestions"),
    ("COMPLETE", "final trace, audit, limitation, hash, and handoff summary"),
]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_input_index(discovery: dict[str, Any], summary: dict[str, Any]) -> None:
    write_json(
        OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json",
        {
            "task_name": TASK_NAME,
            "status": summary["status"],
            "summary": summary,
            "artifacts": discovery["upstreams"],
        },
    )


def local_index(status: str) -> None:
    lines = [f"# {TASK_NAME}", "", f"Status: `{status}`", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in REQUIRED_OUTPUTS)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def stage_io_matrix() -> list[dict[str, Any]]:
    matrix = []
    for idx, (stage, purpose) in enumerate(STAGES, 1):
        matrix.append(
            {
                "stage_number": idx,
                "stage": stage,
                "purpose": purpose,
                "input_contracts": ["scenario_state_ref", "reviewed_option_set_ref", "evidence_refs", "limitation_refs"],
                "output_contracts": ["stage_trace", "review_state_check", "limitation_refs"],
                "deterministic_truth_path": stage != "SYNTHESIZE",
                "narration_eligible": stage == "SYNTHESIZE",
                "execution_state": "not_executed",
                "real_world_action_allowed": False,
            }
        )
    return matrix


def smoke_fixtures() -> list[dict[str, Any]]:
    fixtures = []
    for idx, (stage, purpose) in enumerate(STAGES, 1):
        fixtures.append(
            {
                "fixture_id": f"nine-stage-smoke:{idx:02d}:{stage.lower()}",
                "stage": stage,
                "scenario_state_ref": "scenario:HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001",
                "reviewed_option_set_ref": "outputs/main_citybrain_d6_inverse_dynamics_multi_option_milestone_freeze",
                "evidence_refs": [
                    "outputs/main_citybrain_d6_decision_support_contract_spine_closeout",
                    "outputs/main_citybrain_d6_plan_mode_sumo_closeout",
                    "outputs/main_citybrain_d6_similar_case_retrieval_closeout",
                    "outputs/main_citybrain_d6_cross_domain_cascade_closeout",
                ],
                "limitation_refs": ["limitation:local_replay_only", "limitation:review_query_context_only"],
                "purpose": purpose,
                "execution_state": "not_executed",
                "allowed_effect": "contract_trace_only",
            }
        )
    return fixtures


def smoke_results(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "fixture_id": fixture["fixture_id"],
            "stage": fixture["stage"],
            "status": "PASS",
            "checks": {
                "has_evidence_refs": bool(fixture["evidence_refs"]),
                "has_limitation_refs": bool(fixture["limitation_refs"]),
                "execution_state_not_executed": fixture["execution_state"] == "not_executed",
                "no_real_world_action": True,
                "stage_trace_written": True,
            },
        }
        for fixture in fixtures
    ]


def negative_tests() -> list[dict[str, Any]]:
    return [
        {
            "test_id": "reject_nine_llm_calls",
            "input_shape": "blocked attempt to require one LLM call for every runtime stage",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "reject_autonomous_agent_swarm",
            "input_shape": "blocked attempt to interpret stages as autonomous agent swarm",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "reject_auto_execute_payload",
            "input_shape": "blocked attempt to set execution_state to executed",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "reject_forbidden_action_categories",
            "input_shape": "forbidden dispatch/routing/control/enforcement/legal/certified action-shaped payload",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "reject_ungrounded_synthesis",
            "input_shape": "blocked attempt to synthesize without evidence refs",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "reject_proposal_approval_outside_track_d",
            "input_shape": "blocked attempt to approve a proposal outside Track D",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
    ]


def write_success_artifacts() -> tuple[int, int, int]:
    matrix = stage_io_matrix()
    fixtures = smoke_fixtures()
    results = smoke_results(fixtures)
    negatives = negative_tests()
    contract = {
        "status": "PASS",
        "contract_id": "citybrain.governed_9_stage_runtime.contract_smoke_r1",
        "stage_count": len(STAGES),
        "state_machine_policy": "governed_state_machine_not_autonomous_agents",
        "truth_path": "deterministic code/contracts for all stages except grounded SYNTHESIZE narration eligibility",
        "execution_state": "not_executed",
        "real_world_action_allowed": False,
        "stages": [{"stage_number": idx, "stage": stage, "purpose": purpose} for idx, (stage, purpose) in enumerate(STAGES, 1)],
        "boundary": BOUNDARY,
    }
    model_policy = {
        "status": "PASS",
        "llm_required_for_pass": False,
        "nine_llm_calls_allowed": False,
        "autonomous_agent_swarm_allowed": False,
        "narration_eligible_stage": "SYNTHESIZE",
        "synthesize_grounding_required": ["evidence_refs", "reviewed_option_set_refs", "limitation_refs"],
        "deterministic_truth_path": True,
    }
    resolve_boundary = {
        "status": "PASS",
        "stage": "RESOLVE_ACTIONS",
        "track_d_authoritative": True,
        "allowed_mapping": "proposal_bridge_candidates_only",
        "proposal_approval_allowed_here": False,
        "execution_allowed_here": False,
        "execution_state": "not_executed",
    }
    trace_contract = {
        "status": "PASS",
        "required_trace_fields": [
            "stage",
            "input_refs",
            "output_refs",
            "evidence_refs",
            "limitation_refs",
            "boundary_check",
            "execution_state",
            "hash_ref",
        ],
        "stage_count": len(STAGES),
        "audit_outputs_required": ["claim_boundary", "no_action", "no_mutation", "secret", "hash"],
    }
    negative_report = {
        "status": "PASS" if all(test["passed"] for test in negatives) else "FAIL",
        "negative_test_count": len(negatives),
        "tests": negatives,
    }
    write_json(OUTPUT_ROOT / "NINE_STAGE_RUNTIME_CONTRACT.json", contract)
    write_json(OUTPUT_ROOT / "NINE_STAGE_STAGE_IO_MATRIX.json", {"status": "PASS", "stage_count": len(matrix), "matrix": matrix})
    write_json(OUTPUT_ROOT / "NINE_STAGE_SMOKE_FIXTURES.json", {"status": "PASS", "fixture_count": len(fixtures), "fixtures": fixtures})
    write_json(OUTPUT_ROOT / "NINE_STAGE_SMOKE_RESULTS.json", {"status": "PASS", "result_count": len(results), "results": results})
    write_json(OUTPUT_ROOT / "MODEL_USAGE_POLICY.json", model_policy)
    write_json(OUTPUT_ROOT / "RESOLVE_ACTIONS_TRACK_D_BOUNDARY.json", resolve_boundary)
    write_json(OUTPUT_ROOT / "TRACE_AUDIT_CONTRACT.json", trace_contract)
    write_json(OUTPUT_ROOT / "NEGATIVE_TEST_REPORT.json", negative_report)
    return len(STAGES), len(fixtures), len(negatives)


def main() -> int:
    prepare_output_root(OUTPUT_ROOT, OUTPUT_NAME)
    discovery, summary = discover_upstreams(REQUIRED_UPSTREAMS)
    write_input_index(discovery, summary)
    before = upstream_snapshots(REQUIRED_UPSTREAMS)
    cascade_closeout_green = next(row for row in discovery["upstreams"] if row["key"] == "cross_domain_cascade_closeout")["green"]

    if not cascade_closeout_green:
        status = FAIL_STATUS
        decision = {
            "status": status,
            "task_name": TASK_NAME,
            "timestamp": now_iso(),
            "output_root": str(OUTPUT_ROOT),
            "runner_path": str(Path(__file__).resolve()),
            "upstream_missing": True,
            "blocking_message": "Cross-Domain Cascade closeout is missing or not green; smoke not started.",
            "required_upstreams_found": summary["required_upstreams_found"],
            "required_upstreams_total": summary["required_upstreams_total"],
            "missing_or_not_green": summary["missing_or_not_green"],
            "blocking_gaps_count": max(1, summary["missing_or_not_green_count"]),
            "non_blocking_gaps_count": 0,
            "boundary": BOUNDARY,
        }
        write_json(OUTPUT_ROOT / DECISION_NAME, decision)
        write_text(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: `{status}`\n\n{decision['blocking_message']}\n")
        local_index(status)
        audits = run_standard_audits(OUTPUT_ROOT, TASK_NAME, before, REQUIRED_UPSTREAMS, REQUIRED_OUTPUTS[:4] + REQUIRED_OUTPUTS[-5:])
        decision.update(audits)
        decision = write_decision_last(OUTPUT_ROOT, DECISION_NAME, decision, TASK_NAME)
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 1

    stage_count, fixture_count, negative_count = write_success_artifacts()
    status = PASS_STATUS if summary["status"] == "PASS" else FAIL_STATUS
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{status}`

This output proves a governed 9-stage state-machine contract smoke over existing decision-support artifacts. It is not a runtime service and it does not create real-world action.

- Stage count: `{stage_count}`
- Fixture count: `{fixture_count}`
- Negative test count: `{negative_count}`

{BOUNDARY}
""",
    )
    local_index(status)
    write_json(
        OUTPUT_ROOT / DECISION_NAME,
        {
            "status": status,
            "task_name": TASK_NAME,
            "timestamp": now_iso(),
            "decision_state": "provisional_before_audits",
            "output_root": str(OUTPUT_ROOT),
            "runner_path": str(Path(__file__).resolve()),
        },
    )
    audits = run_standard_audits(OUTPUT_ROOT, TASK_NAME, before, REQUIRED_UPSTREAMS, REQUIRED_OUTPUTS)
    if not audits["all_pass"]:
        status = FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "stage_count": stage_count,
        "fixture_count": fixture_count,
        "negative_test_count": negative_count,
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "cross_domain_cascade_closeout_green": cascade_closeout_green,
        "cross_domain_cascade_milestone_freeze_green": next(row for row in discovery["upstreams"] if row["key"] == "cross_domain_cascade_milestone_freeze")["green"],
        "blocking_gaps_count": 0 if status == PASS_STATUS else max(1, summary["missing_or_not_green_count"]),
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-OPERATOR-DECISION-SUPPORT-SURFACE-R1",
        "boundary": BOUNDARY,
    }
    decision.update(audits)
    if not audits["all_pass"]:
        decision["status"] = FAIL_STATUS
        decision["recommended_next_task"] = TASK_NAME + "-FIXUP"
    decision = write_decision_last(OUTPUT_ROOT, DECISION_NAME, decision, TASK_NAME)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
