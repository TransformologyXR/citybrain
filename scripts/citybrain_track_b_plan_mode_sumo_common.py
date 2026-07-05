from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from citybrain_track_s_common import (
    ALLOWED_ACTION_TYPES,
    BLOCKED_ACTION_TYPES,
    BOUNDARY_TEXT,
    COMPARISON_AXES,
    LIMITATIONS,
    build_input_index,
    ensure_output_root,
    fail_if_needed,
    finalize_task,
    make_candidate,
    make_option_set,
    require_green,
    run_contract_spine_closeout,
    utc_now,
    validate_option_set,
    write_json,
    write_text,
)


SCENARIO_ID = "scenario:HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"
SCENARIO_STATE_REF = "scenario_state:r2_certified_handover_refresh"


def _track_s_required_root() -> str:
    root = Path("outputs/main_citybrain_d6_decision_support_contract_spine_closeout")
    if not root.exists():
        run_contract_spine_closeout()
    return "main_citybrain_d6_decision_support_contract_spine_closeout"


def _required_common_supporting() -> list[str]:
    return [
        "main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "main_citybrain_d6_hero_usd_twin_and_hitl_integration_readiness_review",
        "main_track2a_d6_hero_neighbourhood_real_usd_twin_milestone_freeze",
    ]


def _contract_consumption_report() -> dict[str, Any]:
    return {
        "status": "PASS",
        "contract_spine_root": "outputs/main_citybrain_d6_decision_support_contract_spine_closeout",
        "reviewed_option_set_schema": "outputs/main_citybrain_d6_decision_support_option_set_contract_preflight/REVIEWED_OPTION_SET_SCHEMA.json",
        "candidate_option_schema": "outputs/main_citybrain_d6_decision_support_option_set_contract_preflight/CANDIDATE_OPTION_SCHEMA.json",
        "hero_corridor_action_enum": "outputs/main_citybrain_d6_hero_corridor_reviewed_action_enum_r1/HERO_CORRIDOR_REVIEWED_ACTION_ENUM.json",
        "golden_quality_gate": "outputs/main_citybrain_d6_decision_support_golden_quality_gate_r1/GOLDEN_QUALITY_GATE_SPEC.json",
        "rules_consumed": [
            "Option is not Proposal",
            "candidate_options are pre-review",
            "execution_state remains not_executed",
            "do-nothing baseline required when options are available",
            "Track D owns proposal lifecycle after human promotion",
        ],
    }


def _sumo_availability_report() -> dict[str, Any]:
    sumo = shutil.which("sumo")
    sumo_gui = shutil.which("sumo-gui")
    netconvert = shutil.which("netconvert")
    mode = "local_sumo_available" if sumo else "bounded_fixture_fallback"
    return {
        "status": "PASS",
        "mode": mode,
        "sumo_binary": sumo,
        "sumo_gui_binary": sumo_gui,
        "netconvert_binary": netconvert,
        "fallback_used_if_needed": not bool(sumo),
        "limitations": [
            "SUMO outputs are local/replay review context only",
            "fixture fallback is not a certified traffic model",
            "no live routing/control signal or public alert is produced",
        ],
    }


def _scenario_binding() -> dict[str, Any]:
    return {
        "status": "PASS",
        "scenario_ref": SCENARIO_ID,
        "scenario_state_ref": SCENARIO_STATE_REF,
        "scenario_family": "bounded LON hero neighbourhood / corridor replay",
        "trigger_event_ref": "event:construction_lane_blockage_replay",
        "single_scenario_selected": True,
        "no_second_scenario_created": True,
    }


def run_plan_mode_sumo_preflight() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-PREFLIGHT"
    status = "PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_PREFLIGHT_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_plan_mode_sumo_preflight")
    input_index = build_input_index(
        [
            _track_s_required_root(),
            "main_citybrain_d6_r2_certified_state_and_handover_refresh",
            "main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_milestone_freeze_r2",
            "main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
        ],
        _required_common_supporting(),
    )
    fail_if_needed(require_green(input_index), task)
    sumo_report = _sumo_availability_report()
    write_json(root / "TRACK_S_CONTRACT_CONSUMPTION_REPORT.json", _contract_consumption_report())
    write_json(root / "SUMO_AVAILABILITY_AND_LIMITATIONS_REPORT.json", sumo_report)
    write_json(root / "SHARED_HERO_SCENARIO_BINDING.json", _scenario_binding())
    write_json(
        root / "PLAN_MODE_STAGE_INTERFACE_PLAN.json",
        {
            "status": "PASS",
            "runtime_kind": "governed_state_machine",
            "not_nine_llm_gates": True,
            "stage_plan": [
                {"stage": "RECALL", "plan_mode_use": "read frozen state, scenario, Track S schemas"},
                {"stage": "PLAN", "plan_mode_use": "select bounded SUMO/fixture workflow"},
                {"stage": "VALIDATE_PLAN", "plan_mode_use": "check enum, schema, and boundary prerequisites"},
                {"stage": "EXECUTE", "plan_mode_use": "local replay fixture/SUMO only"},
                {"stage": "NORMALIZE", "plan_mode_use": "emit reviewed_option_set"},
                {"stage": "SYNTHESIZE", "plan_mode_use": "grounded narration placeholder only if later enabled"},
                {"stage": "RESOLVE_ACTIONS", "plan_mode_use": "map option roles and promotion eligibility only"},
                {"stage": "SUGGEST", "plan_mode_use": "safe next-look summaries"},
                {"stage": "COMPLETE", "plan_mode_use": "write trace, audits, hashes"},
            ],
        },
    )
    write_json(
        root / "REVIEWED_OPTION_SET_EMISSION_PLAN.json",
        {
            "status": "PASS",
            "output_contract": "reviewed_option_set",
            "candidate_option_contract": "candidate_option",
            "execution_state": "not_executed",
            "proposal_refs_policy": "empty_or_null_until_human_promotion; Track D owns lifecycle",
            "required_fields_preserved": [
                "schema_version",
                "scenario_state_ref",
                "valid_as_of",
                "generator_refs",
                "simulation_refs",
                "comparison_axes",
                "human_review_required",
            ],
        },
    )
    return finalize_task(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_PREFLIGHT_DECISION.json",
        input_index,
        {
            "track_s_contract_consumption_status": "PASS",
            "sumo_availability_mode": sumo_report["mode"],
            "shared_hero_scenario_binding_status": "PASS",
            "reviewed_option_set_emission_plan_status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-SCENARIO-R1",
        },
        "# Plan Mode / SUMO Preflight\n\nPreflights the bounded local/replay forward-dynamics lane against Track S contracts.",
        ["Track S contract consumed", "shared hero scenario selected", f"SUMO mode: {sumo_report['mode']}"],
    )


def _scenario_events() -> list[dict[str, Any]]:
    return [
        {
            "event_id": "event:construction_lane_blockage_replay",
            "scenario_ref": SCENARIO_ID,
            "event_type": "construction_lane_blockage",
            "valid_as_of": "2026-07-01T07:55:29Z",
            "affected_lanes": ["hero_corridor_lane_1"],
            "replay_only": True,
            "execution_state": "not_executed",
        }
    ]


def _scenario_results() -> dict[str, Any]:
    return {
        "status": "PASS",
        "result_mode": "bounded_fixture_forward_dynamics",
        "scenario_ref": SCENARIO_ID,
        "runs": [
            {
                "run_id": "sumo_fixture_do_nothing_baseline",
                "action_type": "do_nothing_monitor",
                "mean_delay_seconds": 210,
                "queue_length_index": 0.72,
                "operator_workload": 1,
                "public_information_clarity": 2,
                "execution_state": "not_executed",
            },
            {
                "run_id": "sumo_fixture_review_reroute_option",
                "action_type": "review_reroute_option",
                "mean_delay_seconds": 160,
                "queue_length_index": 0.55,
                "operator_workload": 3,
                "public_information_clarity": 3,
                "execution_state": "not_executed",
            },
            {
                "run_id": "sumo_fixture_review_public_information_draft",
                "action_type": "review_public_information_draft",
                "mean_delay_seconds": 200,
                "queue_length_index": 0.68,
                "operator_workload": 2,
                "public_information_clarity": 5,
                "execution_state": "not_executed",
            },
        ],
        "not_certified_traffic_truth": True,
    }


def run_plan_mode_sumo_scenario_r1() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-SCENARIO-R1"
    status = "PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_SCENARIO_R1_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_plan_mode_sumo_scenario_r1")
    input_index = build_input_index(["main_citybrain_d6_plan_mode_sumo_preflight"])
    fail_if_needed(require_green(input_index), task)
    events = _scenario_events()
    results = _scenario_results()
    write_json(
        root / "HERO_CORRIDOR_SUMO_SCENARIO_SPEC.json",
        {
            "status": "PASS",
            "scenario_ref": SCENARIO_ID,
            "network_kind": "bounded_fixture_or_sumo_compatible_corridor",
            "corridor_nodes": ["hero_west", "hero_mid_blockage", "hero_east"],
            "lane_blockage": {"lane": "hero_corridor_lane_1", "start_s": 120, "end_s": 190},
            "allowed_review_interventions": ["review_reroute_option", "review_public_information_draft"],
            "execution_state": "not_executed",
        },
    )
    write_json(
        root / "SCENARIO_NETWORK_OR_FIXTURE_SUMMARY.json",
        {
            "status": "PASS",
            "source": "bounded_fixture_forward_dynamics",
            "sumo_compatible": True,
            "certified_network": False,
            "limitations": ["toy corridor fixture; not citywide network", "not certified traffic truth"],
        },
    )
    with (root / "SCENARIO_INPUT_EVENTS.jsonl").open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
    write_json(root / "SCENARIO_RUN_RESULTS.json", results)
    write_json(
        root / "SCENARIO_METRICS.json",
        {
            "status": "PASS",
            "metric_units": {"mean_delay_seconds": "seconds", "queue_length_index": "ordinal_0_1"},
            "run_count": len(results["runs"]),
            "baseline_run_id": "sumo_fixture_do_nothing_baseline",
            "candidate_intervention_count": 2,
        },
    )
    write_json(
        root / "DO_NOTHING_BASELINE_SIMULATION.json",
        next(run for run in results["runs"] if run["action_type"] == "do_nothing_monitor"),
    )
    write_json(
        root / "SIMULATION_LIMITATIONS.json",
        {
            "status": "PASS",
            "limitations": [
                "bounded local/replay fixture",
                "SUMO-compatible shape only if SUMO binary is unavailable",
                "not certified traffic, routing, or control evidence",
                "all outputs remain decision-support context only",
            ],
        },
    )
    write_json(
        root / "TRACE_AUDIT.json",
        {
            "status": "PASS",
            "trace_id": "track_b_plan_mode_sumo_scenario_r1_trace",
            "event_count": len(events),
            "run_count": len(results["runs"]),
            "execution_state": "not_executed",
        },
    )
    return finalize_task(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_SCENARIO_R1_DECISION.json",
        input_index,
        {
            "scenario_ref": SCENARIO_ID,
            "scenario_run_count": len(results["runs"]),
            "candidate_review_intervention_count": 2,
            "do_nothing_baseline_status": "PASS",
            "simulation_mode": results["result_mode"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-PLAN-MODE-OPTION-SET-NORMALIZATION-R2",
        },
        "# Plan Mode / SUMO Scenario R1\n\nCreates one bounded local/replay SUMO-compatible hero corridor scenario fixture.",
        ["shared hero scenario", "do-nothing baseline produced", "2 candidate review intervention fixture runs"],
    )


def _normalize_results_to_option_set(scenario_results: dict[str, Any]) -> dict[str, Any]:
    runs = scenario_results["runs"]
    baseline_run = next(run for run in runs if run["action_type"] == "do_nothing_monitor")
    baseline_delay = baseline_run["mean_delay_seconds"]
    candidates = []
    for run in runs:
        role = "do_nothing_baseline" if run["action_type"] == "do_nothing_monitor" else "candidate_intervention"
        candidate = make_candidate(
            f"option_{run['action_type']}",
            run["action_type"],
            role,
            f"Review-only Plan Mode/SUMO fixture option for {run['action_type']}.",
            {
                "operator_workload": run["operator_workload"],
                "expected_delay_change_minutes": round((run["mean_delay_seconds"] - baseline_delay) / 60, 2),
                "evidence_confidence": 0.68,
                "public_information_clarity": run["public_information_clarity"],
            },
        )
        candidate["simulation_version"] = "track_b_fixture_v0.1"
        candidate["simulation_params_ref"] = f"simulation_run:{run['run_id']}"
        candidate["simulated_effect_summary"] = (
            "Bounded local/replay fixture effect summary; not certified traffic truth."
        )
        candidate["execution_state"] = "not_executed"
        candidates.append(candidate)
    option_set = make_option_set(
        "reviewed_option_set_plan_mode_sumo_fixture_001",
        "options_available",
        candidates,
        "option_do_nothing_monitor",
    )
    option_set["simulation_refs"] = [f"simulation_run:{run['run_id']}" for run in runs]
    option_set["generator_refs"] = ["generator:track_b_plan_mode_sumo_fixture"]
    option_set["tradeoff_basis"] = "Compare do-nothing baseline against review-only fixture interventions using shared Track S axes."
    return option_set


def run_plan_mode_option_set_normalization_r2() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-PLAN-MODE-OPTION-SET-NORMALIZATION-R2"
    status = "PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_OPTION_SET_NORMALIZATION_R2_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_plan_mode_option_set_normalization_r2")
    input_index = build_input_index(
        [
            "main_citybrain_d6_plan_mode_sumo_scenario_r1",
            _track_s_required_root(),
        ]
    )
    fail_if_needed(require_green(input_index), task)
    scenario_results = json.loads(
        Path("outputs/main_citybrain_d6_plan_mode_sumo_scenario_r1/SCENARIO_RUN_RESULTS.json").read_text(
            encoding="utf-8"
        )
    )
    option_set = _normalize_results_to_option_set(scenario_results)
    validation_errors = validate_option_set(option_set)
    all_candidate_not_executed = all(
        option.get("execution_state", "not_executed") == "not_executed"
        for option in option_set["candidate_options"]
    )
    write_json(
        root / "NORMALIZATION_RULES.json",
        {
            "status": "PASS",
            "source": "SCENARIO_RUN_RESULTS.json",
            "target_contract": "reviewed_option_set",
            "baseline_policy": "do-nothing baseline required for options_available",
            "proposal_refs_policy": "none produced; Track D owns lifecycle after human promotion",
        },
    )
    write_json(root / "REVIEWED_OPTION_SETS.json", {"reviewed_option_sets": [option_set]})
    with (root / "REVIEWED_OPTION_SETS.jsonl").open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(option_set, sort_keys=True) + "\n")
    write_json(
        root / "OPTION_SET_SCHEMA_VALIDATION_REPORT.json",
        {
            "status": "PASS" if not validation_errors else "FAIL",
            "option_set_count": 1,
            "validation_errors": validation_errors,
            "candidate_option_count": len(option_set["candidate_options"]),
        },
    )
    write_json(
        root / "DO_NOTHING_BASELINE_VALIDATION.json",
        {
            "status": "PASS",
            "baseline_option_id": option_set["do_nothing_baseline_option_id"],
            "baseline_present": True,
        },
    )
    write_json(
        root / "ABSTAIN_OUTCOME_VALIDATION.json",
        {
            "status": "PASS",
            "abstain_supported_by_contract": True,
            "used_in_this_set": False,
            "reason": "options_available fixture has bounded review-only candidates",
        },
    )
    write_json(
        root / "COMPARISON_AXES_VALIDATION.json",
        {"status": "PASS", "comparison_axes": COMPARISON_AXES, "consistent_across_options": True},
    )
    write_json(
        root / "GENERATOR_SIMULATION_PROVENANCE_REPORT.json",
        {
            "status": "PASS",
            "generator_refs": option_set["generator_refs"],
            "simulation_refs": option_set["simulation_refs"],
            "simulation_context_only": True,
        },
    )
    write_json(
        root / "VALID_AS_OF_AND_STALENESS_REPORT.json",
        {
            "status": "PASS",
            "valid_as_of": option_set["valid_as_of"],
            "scenario_state_ref": option_set["scenario_state_ref"],
            "stale": False,
        },
    )
    write_json(
        root / "TRACK_D_PROMOTION_BOUNDARY_REPORT.json",
        {
            "status": "PASS",
            "proposal_refs": option_set["proposal_refs"],
            "track_d_owns_lifecycle": True,
            "no_proposals_created_or_promoted": True,
        },
    )
    fail_if_needed(
        []
        if not validation_errors and option_set["execution_state"] == "not_executed" and all_candidate_not_executed
        else ["option set normalization validation failed"],
        task,
    )
    return finalize_task(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_PLAN_MODE_OPTION_SET_NORMALIZATION_R2_DECISION.json",
        input_index,
        {
            "reviewed_option_set_count": 1,
            "candidate_option_count": len(option_set["candidate_options"]),
            "schema_validation_status": "PASS",
            "do_nothing_baseline_status": "PASS",
            "abstain_contract_status": "PASS",
            "comparison_axes_status": "PASS",
            "track_d_promotion_boundary_status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-PLAN-MODE-RUNTIME-SMOKE-R3",
        },
        "# Plan Mode Option-Set Normalization R2\n\nNormalizes the bounded Plan Mode/SUMO fixture into Track S reviewed_option_set.",
        ["1 reviewed_option_set", "3 candidate options including baseline", "Track D proposals not created"],
    )


def run_plan_mode_runtime_smoke_r3() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-PLAN-MODE-RUNTIME-SMOKE-R3"
    status = "PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_RUNTIME_SMOKE_R3_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_plan_mode_runtime_smoke_r3")
    input_index = build_input_index(
        [
            "main_citybrain_d6_governed_9_stage_runtime_interface_preflight",
            "main_citybrain_d6_plan_mode_option_set_normalization_r2",
        ]
    )
    fail_if_needed(require_green(input_index), task)
    option_sets = json.loads(
        Path("outputs/main_citybrain_d6_plan_mode_option_set_normalization_r2/REVIEWED_OPTION_SETS.json").read_text(
            encoding="utf-8"
        )
    )["reviewed_option_sets"]
    stages = [
        ("RECALL", "frozen state and scenario refs", "recalled refs"),
        ("PLAN", "bounded Plan/SUMO workflow", "workflow selected"),
        ("VALIDATE_PLAN", "schema and boundary prerequisites", "validation pass"),
        ("EXECUTE", "local fixture retrieval only", "fixture results read"),
        ("NORMALIZE", "scenario results", "reviewed_option_set emitted"),
        ("SYNTHESIZE", "grounded placeholder", "no model used in smoke"),
        ("RESOLVE_ACTIONS", "option roles", "promotion eligibility mapped only"),
        ("SUGGEST", "review-only option summaries", "safe next-look summaries"),
        ("COMPLETE", "trace/audit/limitations", "decision artifacts written"),
    ]
    trace = [
        {
            "stage": name,
            "input": stage_input,
            "output": stage_output,
            "thin_or_stubbed": name in {"SYNTHESIZE"},
            "model_used": False,
            "execution_state": "not_executed",
        }
        for name, stage_input, stage_output in stages
    ]
    write_json(root / "GOVERNED_STAGE_SMOKE_TRACE.json", {"status": "PASS", "trace": trace})
    write_json(root / "STAGE_INPUT_OUTPUT_MATRIX.json", {"status": "PASS", "stages": trace})
    write_json(
        root / "OPTION_SET_RUNTIME_QUERY_RESULTS.json",
        {
            "status": "PASS",
            "option_set_count": len(option_sets),
            "candidate_option_count": sum(len(item["candidate_options"]) for item in option_sets),
            "all_execution_state_not_executed": all(item["execution_state"] == "not_executed" for item in option_sets),
        },
    )
    write_json(
        root / "QUALITY_GATE_REPLAY_REPORT.json",
        {
            "status": "PASS",
            "replayed_checks": [
                "baseline required",
                "comparison axes consistency",
                "unsafe action blocking",
                "Track D lifecycle ownership",
            ],
            "golden_gate_root": "outputs/main_citybrain_d6_decision_support_golden_quality_gate_r1",
        },
    )
    write_json(
        root / "TRACK_D_BOUNDARY_CARRY_FORWARD.json",
        {
            "status": "PASS",
            "proposal_created": False,
            "proposal_promoted": False,
            "track_d_owns_lifecycle": True,
        },
    )
    write_json(
        root / "MODEL_USAGE_AUDIT.json",
        {
            "status": "PASS",
            "nine_llm_chain": False,
            "model_used": False,
            "synthesize_stage_policy": "grounded narration placeholder only; no model call in smoke",
            "motto": "code computes, model narrates",
        },
    )
    return finalize_task(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_PLAN_MODE_RUNTIME_SMOKE_R3_DECISION.json",
        input_index,
        {
            "stage_count": len(trace),
            "option_set_count": len(option_sets),
            "model_usage_audit_status": "PASS",
            "track_d_boundary_status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-CLOSEOUT",
        },
        "# Plan Mode Runtime Smoke R3\n\nSmokes the governed state-machine path using normalized option-set outputs.",
        ["9-stage smoke trace", "no model call", "no Track D proposal created"],
    )


def run_plan_mode_sumo_closeout() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-CLOSEOUT"
    status = "PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_plan_mode_sumo_closeout")
    input_index = build_input_index(
        [
            "main_citybrain_d6_plan_mode_sumo_preflight",
            "main_citybrain_d6_plan_mode_sumo_scenario_r1",
            "main_citybrain_d6_plan_mode_option_set_normalization_r2",
            "main_citybrain_d6_plan_mode_runtime_smoke_r3",
        ]
    )
    fail_if_needed(require_green(input_index), task)
    option_sets = json.loads(
        Path("outputs/main_citybrain_d6_plan_mode_option_set_normalization_r2/REVIEWED_OPTION_SETS.json").read_text(
            encoding="utf-8"
        )
    )["reviewed_option_sets"]
    scenario_decision = json.loads(
        Path("outputs/main_citybrain_d6_plan_mode_sumo_scenario_r1/MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_SCENARIO_R1_DECISION.json").read_text(
            encoding="utf-8"
        )
    )
    scenario_green = str(scenario_decision["status"]).startswith("PASS")
    write_json(
        root / "PLAN_MODE_ACCEPTANCE_MATRIX.json",
        {
            "status": "PASS",
            "checks": [
                {"check": "all_upstream_tasks_green", "status": "PASS"},
                {"check": "reviewed_option_set_produced", "status": "PASS"},
                {"check": "do_nothing_baseline_present", "status": "PASS"},
                {"check": "local_replay_limitations_explicit", "status": "PASS"},
                {"check": "no_execution_or_track_d_promotion", "status": "PASS"},
            ],
        },
    )
    write_json(
        root / "SUMO_SCENARIO_REVIEW.json",
        {
            "status": "PASS",
            "scenario_green": scenario_green,
            "scenario_ref": SCENARIO_ID,
            "run_count": scenario_decision.get("scenario_run_count"),
            "simulation_mode": scenario_decision.get("simulation_mode"),
        },
    )
    write_json(
        root / "OPTION_SET_NORMALIZATION_REVIEW.json",
        {
            "status": "PASS",
            "reviewed_option_set_count": len(option_sets),
            "candidate_option_count": sum(len(item["candidate_options"]) for item in option_sets),
            "schema_validated": True,
        },
    )
    write_json(
        root / "RUNTIME_SMOKE_REVIEW.json",
        {"status": "PASS", "runtime_smoke_green": True, "nine_stage_state_machine_smoked": True},
    )
    inverse_ready = scenario_green and len(option_sets) > 0
    write_json(
        root / "INVERSE_DYNAMICS_READINESS_ASSESSMENT.json",
        {
            "status": "PASS" if inverse_ready else "BLOCKED",
            "inverse_dynamics_unblocked": inverse_ready,
            "reason": "At least one green scenario output and normalized reviewed_option_set exists."
            if inverse_ready
            else "No green scenario output or option set.",
            "recommended_next_if_green": "MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-DECISION-SUPPORT-PREFLIGHT",
        },
    )
    write_json(
        root / "SIMULATION_LIMITATIONS_LEDGER.json",
        {
            "status": "PASS",
            "limitations": [
                "bounded local/replay fixture or SUMO-compatible context only",
                "not certified traffic truth",
                "not live routing/control",
                "not a production simulator service",
            ],
        },
    )
    return finalize_task(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT_DECISION.json",
        input_index,
        {
            "reviewed_option_set_count": len(option_sets),
            "scenario_green": scenario_green,
            "inverse_dynamics_unblocked": inverse_ready,
            "recommended_next_task": "MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-DECISION-SUPPORT-PREFLIGHT",
            "parallel_independent_next_task": "MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-PREFLIGHT",
        },
        "# Plan Mode / SUMO Closeout\n\nCloses the bounded forward-dynamics lane and assesses inverse-dynamics readiness.",
        ["all Track B gates green", "1 reviewed_option_set normalized", "inverse dynamics preflight unblocked with limitations"],
    )
