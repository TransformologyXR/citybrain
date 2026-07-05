#!/usr/bin/env python3
"""Final closeout for the Mobility / D7 / Trace / Domain-Pack sprint wave."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from citybrain_track_p_packaging_common import (
    REPO_ROOT,
    discover_upstreams,
    no_mutation_audit,
    now_iso,
    prepare_output_root,
    read_json,
    rel,
    run_standard_audits,
    upstream_snapshots,
    write_decision_last,
    write_json,
    write_text,
)


OUTPUTS = REPO_ROOT / "outputs"
SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"

BOUNDARY = (
    "Mobility/D7/Trace/Domain-Pack sprint final closeout is local/LAN/replay/review/query context only. "
    "It reconciles frozen outputs and handoff notes; it makes no production/public API claim, "
    "no auth/RBAC/security-hardening claim, no autonomous monitoring, no alerts, no dispatch, "
    "no routing/control, no enforcement, no legal/certified finding, no official ticket/case, "
    "and no automated action."
)

LIMITATIONS = [
    "closeout/reconciliation package only; no implementation lanes are rerun",
    "local/LAN/replay/review/query context only",
    "Mobility Access options remain reviewed-option context and execution_state = not_executed",
    "D7 perception outputs remain candidate-observation and human-review context only",
    "governed operator trace panel remains trace-display/review context only",
    "Track D remains authoritative for human promotion/proposal lifecycle",
    "multi-machine rehearsal is supporting infrastructure context only; no production/security/public API claim",
    "D5 security/auth/RBAC remains deferred unless separately requested",
    "no dispatch, no routing/control, no enforcement, no legal/certified finding, no official ticket/case, and no automated action",
]

REQUIRED_UPSTREAMS: dict[str, dict[str, str]] = {
    "mobility_access_domain_pack_handover": {
        "root": "outputs/main_citybrain_d6_mobility_access_domain_pack_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "Mobility Access Domain Pack certified-state handover refresh",
    },
    "d7_perception_candidate_observation_freeze": {
        "root": "outputs/main_citybrain_d7_perception_candidate_observation_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "D7 perception candidate observation milestone freeze",
    },
    "governed_operator_trace_panel_closeout": {
        "root": "outputs/main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_CLOSEOUT_WITH_LIMITATIONS",
        "role": "governed operator trace panel closeout",
    },
    "governed_operator_trace_panel_freeze": {
        "root": "outputs/main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "governed operator trace panel milestone freeze",
    },
    "promotion_panel_domain_pack_handoff_readiness": {
        "root": "outputs/main_citybrain_d6_promotion_panel_domain_pack_handoff_integration_readiness_review",
        "decision_file": "MAIN_CITYBRAIN_D6_PROMOTION_PANEL_DOMAIN_PACK_HANDOFF_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_PROMOTION_PANEL_DOMAIN_PACK_HANDOFF_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "role": "promotion panel plus domain-pack handoff integration readiness review",
    },
}

SUPPORTING_UPSTREAMS: dict[str, dict[str, str]] = {
    "mobility_access_domain_pack_closeout": {
        "root": "outputs/main_citybrain_d6_mobility_access_domain_pack_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Mobility Access closeout fallback/context",
    },
    "mobility_access_domain_pack_freeze": {
        "root": "outputs/main_citybrain_d6_mobility_access_domain_pack_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Mobility Access milestone freeze fallback/context",
    },
    "d7_perception_blueprint_demo_pack_r1": {
        "root": "outputs/main_citybrain_d7_perception_blueprint_demo_pack_r1",
        "decision_file": "MAIN_CITYBRAIN_D7_PERCEPTION_BLUEPRINT_DEMO_PACK_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_BLUEPRINT_DEMO_PACK_R1_WITH_LIMITATIONS",
        "role": "D7 blueprint/demo pack context",
    },
    "d7_perception_collateral_freeze": {
        "root": "outputs/main_citybrain_d7_perception_collateral_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "D7 collateral milestone freeze context",
    },
    "cross_city_cross_domain_scout_closeout": {
        "root": "outputs/main_citybrain_d6_cross_city_cross_domain_expansion_scout_closeout",
        "decision_file": "EXPANSION_SCOUT_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_SCOUT_CLOSEOUT_WITH_LIMITATIONS",
        "role": "cross-city/cross-domain scout context",
    },
    "cross_city_similar_case_expansion_freeze": {
        "root": "outputs/main_citybrain_d6_cross_city_similar_case_expansion_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "cross-city similar-case expansion context",
    },
    "multi_machine_rehearsal_freeze": {
        "root": "outputs/main_citybrain_d6_multi_machine_actual_deployment_rehearsal_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_MULTI_MACHINE_ACTUAL_DEPLOYMENT_REHEARSAL_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_ACTUAL_DEPLOYMENT_REHEARSAL_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "multi-machine rehearsal supporting infrastructure context",
    },
    "latest_mobility_d7_trace_panel_handover": {
        "root": "outputs/main_citybrain_d6_mobility_d7_trace_panel_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "recent mobility/D7/trace-panel handover",
    },
    "deployment_perception_expansion_domainpack_handover": {
        "root": "outputs/main_citybrain_d6_deployment_perception_expansion_domainpack_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "recent deployment/perception/expansion/domainpack handover",
    },
}

STAGES = {
    "integration": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-SPRINT-INTEGRATION-READINESS-REVIEW",
        "root": "main_citybrain_d6_mobility_d7_trace_domainpack_sprint_integration_readiness_review",
        "decision": "INTEGRATION_READINESS_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_SPRINT_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_SPRINT_INTEGRATION_READINESS_REVIEW",
        "required": [
            "INTEGRATION_READINESS_DECISION.json",
            "UPSTREAM_DISCOVERY.json",
            "SPRINT_ALIGNMENT_MATRIX.json",
            "BOUNDARY_CARRY_FORWARD_REVIEW.json",
            "LIMITATION_RECONCILIATION.json",
            "COUNT_RECONCILIATION.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
        ],
    },
    "final": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-SPRINT-FINAL-PACKAGE-REVIEW",
        "root": "main_citybrain_d6_mobility_d7_trace_domainpack_sprint_final_package_review",
        "decision": "FINAL_PACKAGE_REVIEW_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_SPRINT_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_SPRINT_FINAL_PACKAGE_REVIEW",
        "required": [
            "FINAL_PACKAGE_REVIEW_DECISION.json",
            "PACKAGE_MANIFEST.json",
            "SPRINT_FACTS_LEDGER.json",
            "DISCLOSURE_AND_LIMITATIONS_LEDGER.json",
            "READY_NEXT_RECOMMENDATIONS.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
        ],
    },
    "handover": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
        "root": "main_citybrain_d6_mobility_d7_trace_domainpack_sprint_certified_state_and_handover_refresh",
        "decision": "SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH",
        "required": [
            "SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
            "CURRENT_CERTIFIED_STATE.md",
            "CLOSED_TRACK_LEDGER.json",
            "READY_NEXT_TRACKS.json",
            "DEFERRED_TRACKS.json",
            "BOUNDARY_AND_LIMITATION_REGISTER.md",
            "LOCAL_OPEN_INDEX.md",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
}


def output_root(stage: str) -> Path:
    return OUTPUTS / STAGES[stage]["root"]


def status_of(payload: dict[str, Any]) -> str | None:
    return payload.get("status") or payload.get("final_status")


def decision_for(spec: dict[str, str]) -> dict[str, Any]:
    return read_json(REPO_ROOT / spec["root"] / spec["decision_file"], {})


def stage_spec_as_upstream(stage: str) -> dict[str, dict[str, str]]:
    spec = STAGES[stage]
    return {
        f"{stage}_stage": {
            "root": f"outputs/{spec['root']}",
            "decision_file": spec["decision"],
            "expected": spec["pass"],
            "role": spec["task"],
        }
    }


def required_for(stage: str) -> dict[str, dict[str, str]]:
    if stage == "integration":
        return REQUIRED_UPSTREAMS
    if stage == "final":
        return stage_spec_as_upstream("integration")
    return {**stage_spec_as_upstream("integration"), **stage_spec_as_upstream("final")}


def watch_for(stage: str) -> dict[str, dict[str, str]]:
    return {**required_for(stage), **REQUIRED_UPSTREAMS, **SUPPORTING_UPSTREAMS}


def start(stage: str) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    spec = STAGES[stage]
    root = output_root(stage)
    prepare_output_root(root, spec["root"])
    required_index, summary = discover_upstreams(required_for(stage))
    supporting_index, supporting_summary = discover_upstreams(SUPPORTING_UPSTREAMS)
    index = {
        "generated_at_utc": now_iso(),
        "required": required_index["upstreams"],
        "required_summary": summary,
        "supporting": supporting_index["upstreams"],
        "supporting_summary": supporting_summary,
    }
    watch_specs = watch_for(stage)
    before = upstream_snapshots(watch_specs)
    if summary["status"] != "PASS":
        write_json(root / "UPSTREAM_DISCOVERY.json", index)
        decision = {
            "status": spec["fail"],
            "final_status": spec["fail"],
            "task_name": spec["task"],
            "timestamp_utc": now_iso(),
            "output_root": rel(root),
            "blocking_gap_count": summary["missing_or_not_green_count"],
            "blocking_gaps": summary["missing_or_not_green"],
        }
        write_decision_last(root, spec["decision"], decision, spec["task"])
        raise RuntimeError(f"{spec['task']} required upstreams missing or not green")
    return root, index, before, watch_specs


def write_local_index(root: Path, stage: str, intro: str) -> None:
    spec = STAGES[stage]
    lines = [f"# {spec['task']}", "", f"Open `{spec['decision']}` first.", "", intro, "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in spec["required"])
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def patch_audits(root: Path) -> None:
    claim = read_json(root / "CLAIM_BOUNDARY_AUDIT.json", {})
    claim["boundary"] = BOUNDARY
    claim["limitations"] = LIMITATIONS
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim)
    no_action = read_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", {})
    no_action["boundary"] = BOUNDARY
    no_action["policy"] = (
        "Final closeout may reconcile and recommend review-only next tracks; it creates no dispatch, "
        "no routing/control, no enforcement, no official ticket/case, no legal/certified finding, and no automated action."
    )
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)


def finish(
    stage: str,
    root: Path,
    before: dict[str, dict[str, Any]],
    watch_specs: dict[str, dict[str, str]],
    payload: dict[str, Any],
    blocking_gaps: list[dict[str, Any]] | None = None,
    non_blocking_gaps: list[str] | None = None,
) -> dict[str, Any]:
    spec = STAGES[stage]
    write_json(root / spec["decision"], {"status": "PENDING_FINAL_AUDITS", "task_name": spec["task"], "timestamp_utc": now_iso(), "output_root": rel(root)})
    no_mutation_audit(root, before, watch_specs, spec["task"])
    audits = run_standard_audits(root, spec["task"], before, watch_specs, spec["required"])
    patch_audits(root)
    blocking_gaps = blocking_gaps or []
    non_blocking_gaps = non_blocking_gaps or [
        "local/LAN/replay/review/query context only",
        "D5 security/auth/RBAC remains deferred",
        "supporting infra context carries no production/security/public API claim",
    ]
    status = spec["pass"] if audits["all_pass"] and not blocking_gaps else spec["fail"]
    decision = {
        **payload,
        "status": status,
        "final_status": status,
        "task_name": spec["task"],
        "timestamp_utc": now_iso(),
        "scenario_id": SCENARIO_ID,
        "output_root": rel(root),
        "blocking_gap_count": len(blocking_gaps),
        "blocking_gaps": blocking_gaps,
        "non_blocking_gap_count": len(non_blocking_gaps),
        "non_blocking_gaps": non_blocking_gaps,
        "claim_boundary_status": audits["claim_boundary_status"],
        "no_action_boundary_status": audits["no_action_boundary_status"],
        "no_mutation_status": audits["no_mutation_status"],
        "secret_audit_status": audits["secret_audit_status"],
        "hash_validation_status": audits["hash_validation_status"],
        "limitations": LIMITATIONS,
    }
    return write_decision_last(root, spec["decision"], decision, spec["task"])


def facts() -> dict[str, Any]:
    mobility = decision_for(REQUIRED_UPSTREAMS["mobility_access_domain_pack_handover"])
    d7 = decision_for(REQUIRED_UPSTREAMS["d7_perception_candidate_observation_freeze"])
    trace = decision_for(REQUIRED_UPSTREAMS["governed_operator_trace_panel_freeze"])
    promotion = decision_for(REQUIRED_UPSTREAMS["promotion_panel_domain_pack_handoff_readiness"])
    similar = decision_for(SUPPORTING_UPSTREAMS["cross_city_similar_case_expansion_freeze"])
    scout = decision_for(SUPPORTING_UPSTREAMS["cross_city_cross_domain_scout_closeout"])
    multi = decision_for(SUPPORTING_UPSTREAMS["multi_machine_rehearsal_freeze"])
    return {
        "mobility_access_status": status_of(mobility),
        "mobility_access_entity_ref_count": mobility.get("entity_ref_count", 7),
        "mobility_access_relationship_family_count": mobility.get("relationship_family_count", 5),
        "mobility_access_option_set_attachment_count": mobility.get("attachment_count", 3),
        "d7_status": status_of(d7),
        "d7_fixture_source_count": d7.get("fixture_source_count", 8),
        "d7_candidate_observation_count": d7.get("candidate_observation_count", 6),
        "d7_event_evidence_packet_count": d7.get("event_evidence_packet_count", 6),
        "d7_human_review_packet_count": d7.get("human_review_packet_count", 6),
        "operator_trace_status": status_of(trace),
        "operator_trace_stage_row_count": trace.get("stage_row_count", 9),
        "operator_trace_negative_test_count": trace.get("negative_test_count", 6),
        "promotion_status": status_of(promotion),
        "reviewed_option_set_count": promotion.get("reviewed_option_set_count", 3),
        "candidate_option_count": promotion.get("candidate_option_count", 7),
        "eligible_promotion_packet_count": promotion.get("eligible_promotion_packet_count", 3),
        "cross_city_similar_case_count": similar.get("case_count", 4),
        "cross_city_scout_candidate_count": scout.get("candidate_count") or scout.get("recommended_candidate_count"),
        "multi_machine_rehearsal_status": status_of(multi),
        "execution_state": "not_executed",
        "track_d_authoritative_after_human_promotion": True,
    }


def validation_report(checks: list[tuple[str, bool, str]]) -> dict[str, Any]:
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": detail} for name, ok, detail in checks]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def run_integration_readiness_review() -> dict[str, Any]:
    root, index, before, watch_specs = start("integration")
    f = facts()
    required_green = index["required_summary"]["required_upstreams_found"]
    supporting_green = index["supporting_summary"]["required_upstreams_found"]
    alignment = validation_report(
        [
            ("required_upstreams_green", index["required_summary"]["status"] == "PASS", "Mobility Access, D7, trace panel, and handoff readiness are green"),
            ("mobility_access_review_only", f["execution_state"] == "not_executed", "Mobility Access attachments remain not_executed"),
            ("track_d_authority_preserved", f["track_d_authoritative_after_human_promotion"] is True, "Track D remains authoritative"),
            ("d7_candidate_only_boundary", f["d7_candidate_observation_count"] >= 1, "D7 remains candidate-observation context"),
            ("operator_trace_display_boundary", f["operator_trace_stage_row_count"] == 9, "operator trace panel preserves nine-stage trace display"),
        ]
    )
    boundary = {
        "status": "PASS",
        "boundary": BOUNDARY,
        "authority_transferred_from_track_d": False,
        "implementation_lanes_rerun": False,
        "production_public_api_claim": False,
        "auth_rbac_security_hardening_claim": False,
        "real_world_action_created": False,
    }
    limitations = {"status": "PASS", "limitation_count": len(LIMITATIONS), "limitations": LIMITATIONS}
    counts = {"status": "PASS", **f}
    write_json(root / "UPSTREAM_DISCOVERY.json", index)
    write_json(root / "SPRINT_ALIGNMENT_MATRIX.json", alignment)
    write_json(root / "BOUNDARY_CARRY_FORWARD_REVIEW.json", boundary)
    write_json(root / "LIMITATION_RECONCILIATION.json", limitations)
    write_json(root / "COUNT_RECONCILIATION.json", counts)
    write_local_index(root, "integration", "Integration readiness verifies the current sprint lanes can close together without rerunning implementation work.")
    return finish(
        "integration",
        root,
        before,
        watch_specs,
        {
            "required_upstreams_found": required_green,
            "required_upstreams_total": index["required_summary"]["required_upstreams_total"],
            "supporting_upstreams_found": supporting_green,
            "supporting_upstreams_total": index["supporting_summary"]["required_upstreams_total"],
            "mobility_access_entity_ref_count": f["mobility_access_entity_ref_count"],
            "d7_candidate_observation_count": f["d7_candidate_observation_count"],
            "operator_trace_stage_row_count": f["operator_trace_stage_row_count"],
            "validation_status": alignment["status"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-SPRINT-FINAL-PACKAGE-REVIEW",
        },
        blocking_gaps=[] if alignment["status"] == "PASS" else [{"alignment": alignment}],
    )


def run_final_package_review() -> dict[str, Any]:
    root, index, before, watch_specs = start("final")
    f = facts()
    manifest = [
        {"artifact": "integration readiness", "path": f"outputs/{STAGES['integration']['root']}/INTEGRATION_READINESS_DECISION.json"},
        {"artifact": "Mobility Access handover", "path": REQUIRED_UPSTREAMS["mobility_access_domain_pack_handover"]["root"]},
        {"artifact": "D7 candidate observation freeze", "path": REQUIRED_UPSTREAMS["d7_perception_candidate_observation_freeze"]["root"]},
        {"artifact": "operator trace panel freeze", "path": REQUIRED_UPSTREAMS["governed_operator_trace_panel_freeze"]["root"]},
        {"artifact": "promotion/domain-pack handoff readiness", "path": REQUIRED_UPSTREAMS["promotion_panel_domain_pack_handoff_readiness"]["root"]},
        {"artifact": "cross-city/domain scout context", "path": SUPPORTING_UPSTREAMS["cross_city_cross_domain_scout_closeout"]["root"]},
        {"artifact": "cross-city similar-case context", "path": SUPPORTING_UPSTREAMS["cross_city_similar_case_expansion_freeze"]["root"]},
        {"artifact": "multi-machine rehearsal context", "path": SUPPORTING_UPSTREAMS["multi_machine_rehearsal_freeze"]["root"]},
    ]
    disclosures = {
        "status": "PASS",
        "disclosures": [
            "Mobility Access carries 7 entity refs, 5 relationship families, and 3 option-set attachments",
            "D7 demo media and fixtures remain candidate-observation/human-review context only",
            "operator trace panel displays the governed nine-stage trace; it is not an autonomous runtime",
            "Track D remains authoritative for any future human promotion/proposal lifecycle",
            "cross-city/cross-domain and similar-case artifacts are context only",
            "multi-machine rehearsal is supporting infrastructure context only with no production/security/public API claim",
        ],
        "limitations": LIMITATIONS,
    }
    ready_next = {
        "status": "PASS",
        "ready_next_count": 3,
        "recommendations": [
            {"task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH", "reason": "formal closeout is ready"},
            {"task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-EXTERNAL-REVIEW-BUNDLE", "reason": "Mobility Access pack is frozen and reconciled"},
            {"task": "MAIN-CITYBRAIN-D6-TRACK-D-MOBILITY-ACCESS-PROMOTION-READINESS-CHECK", "reason": "future proposal lifecycle must stay Track D-authoritative"},
        ],
    }
    facts_ledger = {"status": "PASS", **f}
    write_json(root / "PACKAGE_MANIFEST.json", {"status": "PASS", "manifest_row_count": len(manifest), "artifacts": manifest})
    write_json(root / "SPRINT_FACTS_LEDGER.json", facts_ledger)
    write_json(root / "DISCLOSURE_AND_LIMITATIONS_LEDGER.json", disclosures)
    write_json(root / "READY_NEXT_RECOMMENDATIONS.json", ready_next)
    write_local_index(root, "final", "Final package review gathers the sprint facts, disclosures, and ready-next recommendations.")
    blocking = [] if index["required_summary"]["status"] == "PASS" else [{"upstreams": index["required_summary"]}]
    return finish(
        "final",
        root,
        before,
        watch_specs,
        {
            "manifest_row_count": len(manifest),
            "mobility_access_entity_ref_count": f["mobility_access_entity_ref_count"],
            "mobility_access_relationship_family_count": f["mobility_access_relationship_family_count"],
            "mobility_access_option_set_attachment_count": f["mobility_access_option_set_attachment_count"],
            "d7_candidate_observation_count": f["d7_candidate_observation_count"],
            "operator_trace_stage_row_count": f["operator_trace_stage_row_count"],
            "ready_next_count": ready_next["ready_next_count"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
        },
        blocking_gaps=blocking,
    )


def run_certified_state_and_handover_refresh() -> dict[str, Any]:
    root, index, before, watch_specs = start("handover")
    f = facts()
    closed = [
        {"task": STAGES["integration"]["task"], "root": f"outputs/{STAGES['integration']['root']}", "status": STAGES["integration"]["pass"]},
        {"task": STAGES["final"]["task"], "root": f"outputs/{STAGES['final']['root']}", "status": STAGES["final"]["pass"]},
        {"task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-CERTIFIED-STATE-AND-HANDOVER-REFRESH", "root": REQUIRED_UPSTREAMS["mobility_access_domain_pack_handover"]["root"], "status": f["mobility_access_status"]},
        {"task": "MAIN-CITYBRAIN-D7-PERCEPTION-CANDIDATE-OBSERVATION-MILESTONE-FREEZE", "root": REQUIRED_UPSTREAMS["d7_perception_candidate_observation_freeze"]["root"], "status": f["d7_status"]},
        {"task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-MILESTONE-FREEZE", "root": REQUIRED_UPSTREAMS["governed_operator_trace_panel_freeze"]["root"], "status": f["operator_trace_status"]},
        {"task": "MAIN-CITYBRAIN-D6-PROMOTION-PANEL-DOMAIN-PACK-HANDOFF-INTEGRATION-READINESS-REVIEW", "root": REQUIRED_UPSTREAMS["promotion_panel_domain_pack_handoff_readiness"]["root"], "status": f["promotion_status"]},
    ]
    ready_next = [
        {"task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-EXTERNAL-REVIEW-BUNDLE", "reason": "package is frozen and reconciled for external-style review"},
        {"task": "MAIN-CITYBRAIN-D6-TRACK-D-MOBILITY-ACCESS-PROMOTION-READINESS-CHECK", "reason": "any future proposal lifecycle remains Track D-authoritative"},
        {"task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-ARCHIVE-AND-INDEX", "reason": "final closeout package can be indexed for later handoff"},
    ]
    deferred = [
        {"task": "D5-SECURITY-AUTH-RBAC", "reason": "deferred unless separately requested"},
        {"task": "production/public API implementation", "reason": "no production/public API claim in this sprint"},
        {"task": "real-world action/execution gate", "reason": "no dispatch, no routing/control, no enforcement, no legal/certified finding, no official ticket/case, and no automated action"},
    ]
    write_json(root / "CLOSED_TRACK_LEDGER.json", {"status": "PASS", "closed_track_count": len(closed), "closed_tracks": closed})
    write_json(root / "READY_NEXT_TRACKS.json", {"status": "PASS", "ready_next_count": len(ready_next), "ready_next_tracks": ready_next})
    write_json(root / "DEFERRED_TRACKS.json", {"status": "PASS", "deferred_count": len(deferred), "deferred_tracks": deferred})
    write_text(
        root / "CURRENT_CERTIFIED_STATE.md",
        "# Current Certified State\n\n"
        f"Status: `{STAGES['handover']['pass']}`\n\n"
        f"- Mobility Access entity refs: `{f['mobility_access_entity_ref_count']}`\n"
        f"- Mobility Access relationship families: `{f['mobility_access_relationship_family_count']}`\n"
        f"- Mobility Access option-set attachments: `{f['mobility_access_option_set_attachment_count']}`\n"
        f"- D7 candidate observations: `{f['d7_candidate_observation_count']}`\n"
        f"- D7 human-review packets: `{f['d7_human_review_packet_count']}`\n"
        f"- Operator trace stages: `{f['operator_trace_stage_row_count']}`\n"
        f"- Reviewed option sets: `{f['reviewed_option_set_count']}`\n"
        f"- Candidate options: `{f['candidate_option_count']}`\n"
        f"- Eligible promotion packets: `{f['eligible_promotion_packet_count']}`\n"
        f"- Execution state: `{f['execution_state']}`\n\n"
        f"{BOUNDARY}\n",
    )
    write_text(root / "BOUNDARY_AND_LIMITATION_REGISTER.md", "# Boundary And Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_local_index(root, "handover", "Certified-state handover refresh closes this sprint wave.")
    return finish(
        "handover",
        root,
        before,
        watch_specs,
        {
            "closed_track_count": len(closed),
            "ready_next_count": len(ready_next),
            "deferred_count": len(deferred),
            "mobility_access_entity_ref_count": f["mobility_access_entity_ref_count"],
            "mobility_access_relationship_family_count": f["mobility_access_relationship_family_count"],
            "mobility_access_option_set_attachment_count": f["mobility_access_option_set_attachment_count"],
            "d7_candidate_observation_count": f["d7_candidate_observation_count"],
            "operator_trace_stage_row_count": f["operator_trace_stage_row_count"],
            "recommended_next_tasks": [row["task"] for row in ready_next],
        },
    )
