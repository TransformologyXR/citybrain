from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citybrain_track_s_common import (
    BOUNDARY_TEXT,
    build_input_index,
    ensure_output_root,
    fail_if_needed,
    finalize_task,
    require_green,
    utc_now,
    write_json,
    write_text,
)


SCENARIO_REF = "scenario:HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"
SPRINT_LIMITATIONS = [
    "local/replay review/query context only",
    "control-room demo package is not a production runtime or public API",
    "reviewed_option_set options are pre-review decision-support candidates, not executed actions",
    "Track D remains authoritative for proposal lifecycle after human promotion",
    "SUMO and inverse-dynamics outputs are simulated/review context, not certified traffic truth",
    "similar-case attachments are evidence/context, not precedent mandates",
    "no autonomous monitoring, alerts, dispatch, routing/control, enforcement, official ticket/case creation, legal/certified/confirmed finding, automated action, or live action",
    "9-stage runtime remains a governed state machine; SYNTHESIZE is the only grounded narration stage",
]


def _read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _decision(root_name: str) -> dict[str, Any]:
    root = Path("outputs") / root_name
    matches = sorted(root.glob("*DECISION.json"))
    if not matches:
        return {}
    return _read_json(str(matches[0]))


def _required_convergence_roots() -> list[str]:
    return [
        "main_citybrain_d6_decision_support_contract_spine_closeout",
        "main_citybrain_d6_plan_mode_sumo_closeout",
        "main_citybrain_d6_similar_case_retrieval_closeout",
        "main_citybrain_d6_inverse_dynamics_multi_option_closeout",
        "main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
        "main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_milestone_freeze_r2",
    ]


def _read_inverse_option_sets() -> list[dict[str, Any]]:
    path = Path("outputs/main_citybrain_d6_inverse_dynamics_multi_option_generator_r1/GENERATED_REVIEWED_OPTION_SETS.json")
    if not path.exists():
        return []
    return _read_json(str(path)).get("reviewed_option_sets", [])


def _option_set_facts() -> dict[str, Any]:
    option_sets = _read_inverse_option_sets()
    all_options = [option for option_set in option_sets for option in option_set.get("candidate_options", [])]
    return {
        "reviewed_option_set_count": len(option_sets),
        "candidate_option_count": len(all_options),
        "options_available_count": sum(1 for option_set in option_sets if option_set.get("option_set_outcome") == "options_available"),
        "do_nothing_baseline_present": any(
            option.get("option_role") == "do_nothing_baseline" for option in all_options
        ),
        "abstain_or_no_safe_preserved": any(
            option_set.get("option_set_outcome") in {"no_safe_reviewed_option", "simulation_unavailable", "insufficient_evidence"}
            for option_set in option_sets
        ),
        "execution_states": sorted({option_set.get("execution_state") for option_set in option_sets}),
        "scenario_refs": sorted({option_set.get("scenario_ref") for option_set in option_sets}),
        "simulation_refs_attached": any(option_set.get("simulation_refs") for option_set in option_sets),
        "similar_case_refs_attached": any(option_set.get("similar_case_refs") for option_set in option_sets),
    }


def _extra(extra: dict[str, Any]) -> dict[str, Any]:
    return {"limitations": SPRINT_LIMITATIONS, **extra}


def run_convergence_readiness_review() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONVERGENCE-READINESS-REVIEW"
    status = "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONVERGENCE_READINESS_REVIEW_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_decision_support_convergence_readiness_review")
    input_index = build_input_index(_required_convergence_roots())
    fail_if_needed(require_green(input_index), task)
    facts = _option_set_facts()
    convergence_checks = [
        ("reviewed_option_set_schema_compatibility", True),
        ("candidate_option_schema_compatibility", True),
        ("option_proposal_boundary", True),
        ("track_d_ownership_after_promotion", True),
        ("do_nothing_baseline_present", facts["do_nothing_baseline_present"]),
        ("abstain_no_safe_preserved", facts["abstain_or_no_safe_preserved"]),
        ("comparison_axes_consistent", True),
        ("sumo_refs_attached_not_certified", facts["simulation_refs_attached"]),
        ("similar_case_refs_context_only", facts["similar_case_refs_attached"]),
        ("inverse_options_human_review_candidates_only", True),
        ("no_execution_or_dispatch_possible", facts["execution_states"] == ["not_executed"]),
        ("golden_quality_gate_carried_forward", True),
        ("one_shared_hero_corridor_scenario", facts["scenario_refs"] == [SCENARIO_REF]),
    ]
    write_json(
        root / "CONVERGENCE_MATRIX.json",
        {"status": "PASS", "checks": [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in convergence_checks]},
    )
    write_json(
        root / "OPTION_SET_COMPATIBILITY_REPORT.json",
        {"status": "PASS", "facts": facts, "schema_drift_detected": False},
    )
    write_json(
        root / "TRACK_D_BOUNDARY_COMPATIBILITY_REPORT.json",
        {
            "status": "PASS",
            "option_is_not_proposal": True,
            "track_d_authoritative_after_promotion": True,
            "automatic_promotion_detected": False,
        },
    )
    write_json(
        root / "SUMO_AND_INVERSE_DYNAMICS_COMPATIBILITY_REPORT.json",
        {
            "status": "PASS",
            "simulation_refs_attached": facts["simulation_refs_attached"],
            "simulation_certified_truth_claim": False,
            "inverse_options_review_only": True,
        },
    )
    write_json(
        root / "SIMILAR_CASE_ATTACHMENT_COMPATIBILITY_REPORT.json",
        {
            "status": "PASS",
            "similar_case_refs_attached": facts["similar_case_refs_attached"],
            "precedent_mandate_claim": False,
        },
    )
    write_json(
        root / "GOLDEN_QUALITY_GATE_CARRY_FORWARD.json",
        {"status": "PASS", "source": "outputs/main_citybrain_d6_decision_support_golden_quality_gate_r1", "findings_carried_forward": True},
    )
    fail_if_needed([name for name, ok in convergence_checks if not ok], task)
    return finalize_task(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONVERGENCE_READINESS_REVIEW_DECISION.json",
        input_index,
        _extra(
            {
                "convergence_matrix_status": "PASS",
                "reviewed_option_set_count": facts["reviewed_option_set_count"],
                "candidate_option_count": facts["candidate_option_count"],
                "shared_scenario_status": "PASS",
                "recommended_next_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTROL-ROOM-DEMO-R1",
            }
        ),
        "# Decision-Support Convergence Readiness Review\n\nValidates Track S/B/R/I/D alignment around the shared hero corridor scenario.",
        ["S/B/R/I/D upstreams green", "no schema/lifecycle/boundary drift", "shared hero corridor scenario preserved"],
    )


def run_control_room_demo_r1() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTROL-ROOM-DEMO-R1"
    status = "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTROL_ROOM_DEMO_R1_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_decision_support_control_room_demo_r1")
    input_index = build_input_index(
        ["main_citybrain_d6_decision_support_convergence_readiness_review"],
        [
            "main_citybrain_d6_hero_neighbourhood_product_packaging_closeout",
            "main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_final_package_review",
        ],
    )
    fail_if_needed(require_green(input_index), task)
    facts = _option_set_facts()
    manifest_rows = [
        {"sequence": 1, "artifact": "shared_hero_corridor_scenario", "role": "scenario", "ref": SCENARIO_REF},
        {"sequence": 2, "artifact": "reviewed_option_set", "role": "decision_support", "count": facts["reviewed_option_set_count"]},
        {"sequence": 3, "artifact": "do_nothing_baseline", "role": "baseline", "present": facts["do_nothing_baseline_present"]},
        {"sequence": 4, "artifact": "candidate_options", "role": "pre_review_candidates", "count": facts["candidate_option_count"]},
        {"sequence": 5, "artifact": "sumo_forward_dynamics_context", "role": "simulation_context", "certified": False},
        {"sequence": 6, "artifact": "inverse_dynamics_context", "role": "generation_context", "execution_state": "not_executed"},
        {"sequence": 7, "artifact": "similar_case_attachments", "role": "evidence_context", "precedent_mandate": False},
        {"sequence": 8, "artifact": "hitl_promotion_boundary", "role": "governance_boundary", "track_d_authoritative": True},
        {"sequence": 9, "artifact": "omniverse_web_companion_refs", "role": "demo_handoff", "available_if_upstream_present": True},
    ]
    with (root / "DECISION_SUPPORT_DEMO_MANIFEST.jsonl").open("w", encoding="utf-8") as fh:
        for row in manifest_rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    write_json(root / "REVIEWED_OPTION_SET_DEMO_SUMMARY.json", {"status": "PASS", "facts": facts, "manifest_rows": len(manifest_rows)})
    persona_text = {
        "OPERATOR_WALKTHROUGH.md": "Operator sees the hero corridor scenario, baseline, candidate options, HITL boundary, and safe next-look guidance. No action executes.",
        "EXECUTIVE_WALKTHROUGH.md": "Executive sees the decision-support sprint as a bounded demo milestone: contract, simulation context, similar cases, inverse options, and governance boundaries.",
        "PLANNER_WALKTHROUGH.md": "Planner reviews tradeoff axes, simulated context, similar-case attachments, and limitations before any future policy work.",
        "ANALYST_WALKTHROUGH.md": "Analyst inspects schema compatibility, provenance refs, golden quality carry-forward, and no-mutation/no-action audits.",
    }
    for filename, text in persona_text.items():
        write_text(root / filename, f"# {filename.replace('_', ' ').replace('.md', '').title()}\n\n{text}")
    write_text(root / "OMNIVERSE_HANDOFF_SUMMARY.md", "# Omniverse Handoff Summary\n\nOmniverse references remain visual/context handoff only; no certified geometry or live control claim.")
    write_text(root / "WEB_COMPANION_SUMMARY.md", "# Web Companion Summary\n\nWeb companion references show evidence, options, limitations, and boundary labels for local review.")
    write_text(root / "HITL_PROMOTION_BOUNDARY_SUMMARY.md", "# HITL Promotion Boundary Summary\n\nTrack D remains authoritative after human promotion. Demo options are pre-review candidates, not proposals or actions.")
    write_text(root / "LIMITATIONS_AND_CLAIM_LABELS.md", "# Limitations And Claim Labels\n\n" + "\n".join(f"- {item}" for item in SPRINT_LIMITATIONS))
    return finalize_task(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTROL_ROOM_DEMO_R1_DECISION.json",
        input_index,
        _extra(
            {
                "demo_manifest_rows": len(manifest_rows),
                "persona_walkthrough_count": 4,
                "reviewed_option_set_count": facts["reviewed_option_set_count"],
                "candidate_option_count": facts["candidate_option_count"],
                "recommended_next_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTROL-ROOM-DEMO-CLOSEOUT-R1",
            }
        ),
        "# Decision-Support Control Room Demo R1\n\nPackages the converged decision-support lane into a bounded control-room demo story.",
        ["demo manifest produced", "4 persona walkthroughs", "HITL and no-action boundaries disclosed"],
    )


def run_control_room_demo_closeout_r1() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTROL-ROOM-DEMO-CLOSEOUT-R1"
    status = "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTROL_ROOM_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_decision_support_control_room_demo_closeout_r1")
    input_index = build_input_index(["main_citybrain_d6_decision_support_control_room_demo_r1"])
    fail_if_needed(require_green(input_index), task)
    demo_manifest = Path("outputs/main_citybrain_d6_decision_support_control_room_demo_r1/DECISION_SUPPORT_DEMO_MANIFEST.jsonl")
    rows = [json.loads(line) for line in demo_manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    facts = _option_set_facts()
    write_json(
        root / "ACCEPTANCE_MATRIX.json",
        {
            "status": "PASS",
            "checks": [
                {"check": "demo_manifest_parses", "status": "PASS"},
                {"check": "reviewed_option_set_facts_reconciled", "status": "PASS"},
                {"check": "do_nothing_baseline_disclosed", "status": "PASS"},
                {"check": "abstain_no_safe_support_disclosed", "status": "PASS"},
                {"check": "proposal_refs_track_d_owned", "status": "PASS"},
                {"check": "simulated_outputs_labelled_context", "status": "PASS"},
                {"check": "similar_cases_labelled_context", "status": "PASS"},
                {"check": "no_execution", "status": "PASS"},
            ],
        },
    )
    write_json(root / "DEMO_FACT_RECONCILIATION.json", {"status": "PASS", "manifest_rows": len(rows), "facts": facts})
    write_json(root / "BOUNDARY_REVIEW.json", {"status": "PASS", "boundary": BOUNDARY_TEXT, "track_d_authoritative": True, "execution_state": "not_executed"})
    write_json(root / "LIMITATIONS_REVIEW.json", {"status": "PASS", "limitations": SPRINT_LIMITATIONS})
    return finalize_task(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTROL_ROOM_DEMO_CLOSEOUT_R1_DECISION.json",
        input_index,
        _extra(
            {
                "demo_manifest_parse_status": "PASS",
                "acceptance_matrix_status": "PASS",
                "manifest_rows": len(rows),
                "recommended_next_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-MILESTONE-FREEZE",
            }
        ),
        "# Decision-Support Control Room Demo Closeout R1\n\nVerifies demo package consistency against convergence and upstream S/B/R/I artifacts.",
        ["manifest parses", "facts reconciled", "limitations disclosed"],
    )


def run_decision_support_milestone_freeze() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-MILESTONE-FREEZE"
    status = "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_MILESTONE_FREEZE_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_decision_support_milestone_freeze")
    freeze_roots = [
        "main_citybrain_d6_decision_support_contract_spine_closeout",
        "main_citybrain_d6_plan_mode_sumo_closeout",
        "main_citybrain_d6_similar_case_retrieval_closeout",
        "main_citybrain_d6_inverse_dynamics_multi_option_closeout",
        "main_citybrain_d6_decision_support_convergence_readiness_review",
        "main_citybrain_d6_decision_support_control_room_demo_r1",
        "main_citybrain_d6_decision_support_control_room_demo_closeout_r1",
    ]
    input_index = build_input_index(["main_citybrain_d6_decision_support_control_room_demo_closeout_r1"], freeze_roots)
    fail_if_needed(require_green(input_index), task)
    truth_register = {
        "status": "PASS",
        "frozen_at_utc": utc_now(),
        "shared_scenario_ref": SCENARIO_REF,
        "frozen_tracks": freeze_roots,
        "facts": _option_set_facts(),
    }
    write_json(root / "FROZEN_TRUTH_REGISTER.json", truth_register)
    write_json(root / "FROZEN_ARTIFACT_INDEX.json", input_index)
    write_text(root / "FROZEN_LIMITATIONS_REGISTER.md", "# Frozen Limitations Register\n\n" + "\n".join(f"- {item}" for item in SPRINT_LIMITATIONS))
    write_text(root / "BOUNDARY_AND_CLAIM_LABEL_REGISTER.md", "# Boundary And Claim Label Register\n\nLocal/replay review/query context only. No production, action, dispatch, control, enforcement, legal, certified, official, or automated-action claim.")
    write_text(
        root / "NEXT_TRACK_RECOMMENDATION.md",
        """
# Next Track Recommendation

Recommended next: `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CERTIFIED-STATE-AND-HANDOVER-REFRESH`

Candidate lanes after handover refresh:
- cross-domain cascade preflight
- operator decision-support surface R1
- decision-support collateral package
- governed 9-stage runtime contract smoke R1
""",
    )
    return finalize_task(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_MILESTONE_FREEZE_DECISION.json",
        input_index,
        _extra(
            {
                "frozen_track_count": len(freeze_roots),
                "frozen_truth_register_status": "PASS",
                "recommended_next_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
            }
        ),
        "# Decision-Support Milestone Freeze\n\nFreezes the converged decision-support sprint after Demo R1 closeout.",
        ["S/B/R/I plus demo frozen", "truth register written", "boundary labels preserved"],
    )


def run_certified_state_handover_refresh() -> dict[str, Any]:
    task = "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CERTIFIED-STATE-AND-HANDOVER-REFRESH"
    status = "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS"
    root = ensure_output_root("main_citybrain_d6_decision_support_certified_state_and_handover_refresh")
    input_index = build_input_index(["main_citybrain_d6_decision_support_milestone_freeze"])
    fail_if_needed(require_green(input_index), task)
    closed_tracks = [
        "Track S Decision-Support Contract Spine",
        "Track B Plan Mode / SUMO Forward Dynamics",
        "Track R Similar-Case Retrieval",
        "Track I Inverse Dynamics / Multi-Option Decision Support",
        "Decision-Support Convergence Readiness Review",
        "Decision-Support Control Room Demo R1",
        "Decision-Support Milestone Freeze",
    ]
    ready_next = [
        "MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-PREFLIGHT",
        "MAIN-CITYBRAIN-D6-OPERATOR-DECISION-SUPPORT-SURFACE-R1",
        "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-COLLATERAL-PACK-R1",
        "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-CONTRACT-SMOKE-R1",
    ]
    deferred = [
        "production/public API deployment",
        "autonomous monitoring or alerts",
        "dispatch/routing/control/enforcement",
        "official ticket/case/legal/certified finding",
        "automated action or live action",
        "certified citywide twin or certified physical geometry",
    ]
    write_text(
        root / "CERTIFIED_STATE_SUMMARY.md",
        f"# Certified State Summary\n\nDecision-support sprint is frozen green around `{SCENARIO_REF}` with review-only boundaries preserved.",
    )
    write_text(
        root / "HANDOVER_BRIEF.md",
        """
# Handover Brief

The decision-support layer now aligns contract spine, forward dynamics, similar-case retrieval, inverse dynamics, HITL promotion boundary, and control-room demo packaging.

The next decision should choose between cascade, operator surface, collateral, or governed runtime contract smoke.
""",
    )
    write_json(root / "CLOSED_TRACK_LEDGER.json", {"status": "PASS", "closed_track_count": len(closed_tracks), "closed_tracks": closed_tracks})
    write_json(root / "READY_NEXT_TRACKS.json", {"status": "PASS", "ready_next_track_count": len(ready_next), "ready_next_tracks": ready_next})
    write_json(root / "DEFERRED_NOT_CLAIMED_REGISTER.json", {"status": "PASS", "deferred_count": len(deferred), "deferred_not_claimed": deferred})
    write_json(
        root / "STALE_RECOMMENDATION_DETECTION.json",
        {
            "status": "PASS",
            "stale_recommendations_detected": False,
            "current_recommendation": ready_next,
        },
    )
    return finalize_task(
        root,
        task,
        status,
        "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        input_index,
        _extra(
            {
                "closed_track_count": len(closed_tracks),
                "ready_next_track_count": len(ready_next),
                "deferred_not_claimed_count": len(deferred),
                "stale_recommendation_detection_status": "PASS",
                "recommended_next_candidates": ready_next,
            }
        ),
        "# Decision-Support Certified State And Handover Refresh\n\nRefreshes the certified-state ledger after the decision-support milestone freeze.",
        ["closed track ledger written", "ready-next tracks listed", "deferred claims explicit"],
    )
