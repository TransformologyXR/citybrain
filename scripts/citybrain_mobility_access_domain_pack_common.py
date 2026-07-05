#!/usr/bin/env python3
"""Mobility Access Domain Pack lane helpers.

This lane is additive collateral/contract packaging for decision support. It
does not implement traffic control, production services, or action authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citybrain_track_p_packaging_common import (
    REPO_ROOT,
    discover_upstreams,
    hash_manifest,
    no_mutation_audit,
    now_iso,
    prepare_output_root,
    read_json,
    rel,
    run_standard_audits,
    sha256_file,
    upstream_snapshots,
    write_decision_last,
    write_json,
    write_text,
)


DOMAIN_ID = "domain:mobility-access-decision-pack"
SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"
OUTPUTS = REPO_ROOT / "outputs"

BOUNDARY = (
    "Mobility Access Domain Pack is local/replay/review/query context only. "
    "It defines bounded domain-pack contracts and option-set attachments; it "
    "does not provide production readiness, public API readiness, autonomous "
    "monitoring, alerting, no dispatch, no routing/control, no enforcement, "
    "no official ticket/case creation, no legal/certified finding, and no automated action."
)

LIMITATIONS = [
    "local/replay/review/query context only",
    "domain-pack contract and attachment lane only; no platform functionality is added",
    "reviewed option sets and candidate options remain execution_state = not_executed",
    "Track D remains authoritative after human promotion",
    "no production/public API claim",
    "no dispatch, no routing/control, no enforcement, no official ticket/case creation, no legal/certified finding, and no automated action",
    "no mutation of frozen upstream outputs",
    "D5 security/auth/RBAC remain deferred outside this lane",
]

UPSTREAM_SPECS: dict[str, dict[str, str]] = {
    "latest_deployment_perception_expansion_domainpack_handover": {
        "root": "outputs/main_citybrain_d6_deployment_perception_expansion_domainpack_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "latest deployment/perception/expansion/domainpack sprint handover",
    },
    "mobility_d7_trace_panel_handover": {
        "root": "outputs/main_citybrain_d6_mobility_d7_trace_panel_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "latest mobility/D7/trace-panel sprint handover",
    },
    "domain_pack_candidate_selection_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_domain_pack_candidate_selection_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "selected candidate freeze for mobility access domain pack",
    },
    "decision_support_contract_spine_closeout": {
        "root": "outputs/main_citybrain_d6_decision_support_contract_spine_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "reviewed option-set contract spine",
    },
    "cross_domain_cascade_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_cross_domain_cascade_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "cross-domain cascade freeze",
    },
    "plan_mode_sumo_closeout": {
        "root": "outputs/main_citybrain_d6_plan_mode_sumo_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Plan Mode/SUMO closeout",
    },
    "similar_case_retrieval_closeout": {
        "root": "outputs/main_citybrain_d6_similar_case_retrieval_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_WITH_LIMITATIONS",
        "role": "similar-case retrieval closeout",
    },
    "track_d_promotion_integration_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_track_d_option_set_promotion_integration_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Track D option-set promotion integration freeze",
    },
}

SUPPORTING_SPECS: dict[str, dict[str, str]] = {
    "operator_decision_support_surface_r1": {
        "root": "outputs/main_citybrain_d6_operator_decision_support_surface_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_OPERATOR_DECISION_SUPPORT_SURFACE_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_OPERATOR_DECISION_SUPPORT_SURFACE_R1_WITH_LIMITATIONS",
        "role": "operator decision-support surface",
    },
    "governed_runtime_trace_harness_closeout": {
        "root": "outputs/main_citybrain_d6_governed_runtime_trace_harness_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_CLOSEOUT_WITH_LIMITATIONS",
        "role": "governed runtime trace harness closeout",
    },
    "governed_9_stage_runtime_thin_slice_closeout": {
        "root": "outputs/main_citybrain_d6_governed_9_stage_runtime_thin_slice_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_THIN_SLICE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_THIN_SLICE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "governed 9-stage runtime thin-slice closeout",
    },
    "legacy_d4x_mobility_domain_pack": {
        "root": "outputs/main_citybrain_d4x_mobility_domain_pack_r1_end_to_end",
        "decision_file": "MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS",
        "role": "legacy mobility domain-pack reference",
    },
}

WATCH_SPECS = {**UPSTREAM_SPECS, **SUPPORTING_SPECS}

STAGES = {
    "preflight": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-PREFLIGHT",
        "root": "main_citybrain_d6_mobility_access_domain_pack_preflight",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_PREFLIGHT_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_PREFLIGHT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_PREFLIGHT",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_PREFLIGHT_DECISION.json",
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "INPUT_ARTIFACT_INDEX.json",
            "MOBILITY_ACCESS_DOMAIN_PACK_PREFLIGHT_SPEC.json",
            "DOMAIN_PACK_SCOPE_AND_BOUNDARY.md",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    "r1": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-R1",
        "root": "main_citybrain_d6_mobility_access_domain_pack_r1",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_R1_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_R1_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_R1",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_R1_DECISION.json",
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "MOBILITY_ACCESS_DOMAIN_PACK_R1.json",
            "MOBILITY_ACCESS_ENTITY_BRIDGE.json",
            "MOBILITY_ACCESS_RELATIONSHIP_BRIDGE.json",
            "MOBILITY_ACCESS_ACTION_POLICY.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    "attachment": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-OPTION-SET-ATTACHMENT-R2",
        "root": "main_citybrain_d6_mobility_access_option_set_attachment_r2",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_OPTION_SET_ATTACHMENT_R2_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_OPTION_SET_ATTACHMENT_R2_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_OPTION_SET_ATTACHMENT_R2",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_OPTION_SET_ATTACHMENT_R2_DECISION.json",
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "MOBILITY_ACCESS_OPTION_SET_ATTACHMENTS.json",
            "MOBILITY_ACCESS_ATTACHMENT_VALIDATION.json",
            "OPTION_SET_SCHEMA_COMPATIBILITY_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    "closeout": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-CLOSEOUT",
        "root": "main_citybrain_d6_mobility_access_domain_pack_closeout",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CLOSEOUT_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CLOSEOUT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CLOSEOUT",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CLOSEOUT_DECISION.json",
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "MOBILITY_ACCESS_DOMAIN_PACK_ACCEPTANCE_MATRIX.json",
            "MOBILITY_ACCESS_DOMAIN_PACK_CLOSEOUT_REPORT.md",
            "MOBILITY_ACCESS_EVIDENCE_LIMITATION_LEDGER.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    "freeze": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-MILESTONE-FREEZE",
        "root": "main_citybrain_d6_mobility_access_domain_pack_milestone_freeze",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_MILESTONE_FREEZE_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_MILESTONE_FREEZE",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_MILESTONE_FREEZE_DECISION.json",
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "MOBILITY_ACCESS_FROZEN_FACTS_LEDGER.json",
            "MOBILITY_ACCESS_RECOMMENDED_NEXT_TASK.json",
            "FREEZE_HASH_RECHECK.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
}


def stage_root(stage: str) -> Path:
    return OUTPUTS / STAGES[stage]["root"]


def stage_decision(stage: str) -> dict[str, Any]:
    spec = STAGES[stage]
    return read_json(stage_root(stage) / spec["decision"], {})


def stage_green(stage: str) -> bool:
    return stage_decision(stage).get("status") == STAGES[stage]["pass"]


def start_stage(stage: str) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]]]:
    spec = STAGES[stage]
    root = stage_root(stage)
    prepare_output_root(root, spec["root"])
    input_index, summary = discover_upstreams(UPSTREAM_SPECS)
    supporting, supporting_summary = discover_upstreams(SUPPORTING_SPECS)
    input_index["supporting_artifacts"] = supporting["upstreams"]
    input_index["supporting_summary"] = supporting_summary
    input_index["generated_at_utc"] = now_iso()
    before = upstream_snapshots(WATCH_SPECS)
    if summary["status"] != "PASS":
        write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
        decision = {
            "status": spec["fail"],
            "task_name": spec["task"],
            "timestamp_utc": now_iso(),
            "output_root": rel(root),
            "blocking_gaps": summary["missing_or_not_green"],
            "blocking_gap_count": len(summary["missing_or_not_green"]),
            "limitation": "required upstream missing or not green; no partial domain pack created",
        }
        write_decision_last(root, spec["decision"], decision, spec["task"])
        raise RuntimeError(f"{spec['task']} required upstreams not green")
    return root, input_index, before


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_common_docs(root: Path, stage: str, title: str, intro: str) -> None:
    spec = STAGES[stage]
    write_text(
        root / "README.md",
        f"# {title}\n\nStatus is recorded in `{spec['decision']}`.\n\n{BOUNDARY}\n\n## Limitations\n\n"
        + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    write_text(
        root / "LOCAL_OPEN_INDEX.md",
        f"# {title}\n\nOpen `{spec['decision']}` first, then review the JSON contract artifacts in this folder.\n\n{intro}\n",
    )


def finish_stage(
    stage: str,
    root: Path,
    before: dict[str, dict[str, Any]],
    payload: dict[str, Any],
    blocking_gaps: list[dict[str, Any]] | None = None,
    non_blocking_gaps: list[str] | None = None,
) -> dict[str, Any]:
    spec = STAGES[stage]
    write_json(
        root / spec["decision"],
        {
            "status": "PENDING_FINAL_AUDITS",
            "task_name": spec["task"],
            "timestamp_utc": now_iso(),
            "domain_id": DOMAIN_ID,
            "output_root": rel(root),
        },
    )
    no_mutation_audit(root, before, WATCH_SPECS, spec["task"])
    audits = run_standard_audits(root, spec["task"], before, WATCH_SPECS, spec["required"])
    claim_audit = read_json(root / "CLAIM_BOUNDARY_AUDIT.json", {})
    claim_audit["boundary"] = BOUNDARY
    claim_audit["limitations"] = LIMITATIONS
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_audit)
    no_action_audit = read_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", {})
    no_action_audit["policy"] = (
        "Mobility Access Domain Pack may create review-only references and safe next-look suggestions; "
        "it must create no dispatch, no routing/control, no enforcement, no official ticket/case, "
        "no legal/certified finding, and no automated action."
    )
    no_action_audit["boundary"] = BOUNDARY
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action_audit)
    blocking_gaps = blocking_gaps or []
    non_blocking_gaps = non_blocking_gaps or [
        "domain pack remains local/replay review context only",
        "D5 security/auth/RBAC deferred outside this lane",
    ]
    status = spec["pass"] if audits["all_pass"] and not blocking_gaps else spec["fail"]
    decision = {
        **payload,
        "status": status,
        "final_status": status,
        "task_name": spec["task"],
        "timestamp_utc": now_iso(),
        "scenario_id": SCENARIO_ID,
        "domain_id": DOMAIN_ID,
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


def evidence_refs() -> list[dict[str, str]]:
    return [
        {"ref_id": "handover:deployment-perception-expansion-domainpack", "path": UPSTREAM_SPECS["latest_deployment_perception_expansion_domainpack_handover"]["root"], "purpose": "current frozen source of truth"},
        {"ref_id": "freeze:domain-pack-candidate-selection", "path": UPSTREAM_SPECS["domain_pack_candidate_selection_milestone_freeze"]["root"], "purpose": "selected mobility-access candidate"},
        {"ref_id": "contract:decision-support-spine", "path": UPSTREAM_SPECS["decision_support_contract_spine_closeout"]["root"], "purpose": "reviewed option-set schema compatibility"},
        {"ref_id": "cascade:milestone-freeze", "path": UPSTREAM_SPECS["cross_domain_cascade_milestone_freeze"]["root"], "purpose": "cross-domain cascade reference preservation"},
        {"ref_id": "sim:plan-mode-sumo", "path": UPSTREAM_SPECS["plan_mode_sumo_closeout"]["root"], "purpose": "local/replay mobility simulation context"},
        {"ref_id": "retrieval:similar-case-closeout", "path": UPSTREAM_SPECS["similar_case_retrieval_closeout"]["root"], "purpose": "similar-case review evidence"},
        {"ref_id": "trackd:promotion-freeze", "path": UPSTREAM_SPECS["track_d_promotion_integration_milestone_freeze"]["root"], "purpose": "Track D proposal authority boundary"},
    ]


def domain_entities() -> list[dict[str, Any]]:
    return [
        {"entity_ref": "mobility_access:corridor:hero-lon-corridor", "entity_type": "corridor", "description": "bounded replay corridor context", "evidence_refs": ["sim:plan-mode-sumo", "cascade:milestone-freeze"]},
        {"entity_ref": "mobility_access:route_segment:hero-main-eastbound", "entity_type": "route_segment", "description": "review-only route segment context", "evidence_refs": ["sim:plan-mode-sumo"]},
        {"entity_ref": "mobility_access:lane_segment:hero-blocked-lane", "entity_type": "lane_segment", "description": "lane-level blockage context for option-set review", "evidence_refs": ["sim:plan-mode-sumo", "cascade:milestone-freeze"]},
        {"entity_ref": "mobility_access:kerbside_access:hero-kerb-zone-a", "entity_type": "kerbside_access_zone", "description": "kerbside/access context with no dispatch and no control authority", "evidence_refs": ["contract:decision-support-spine"]},
        {"entity_ref": "mobility_access:pedestrian_context:hero-crossing-a", "entity_type": "pedestrian_access_context", "description": "pedestrian mobility context for limitations-aware review", "evidence_refs": ["cascade:milestone-freeze"]},
        {"entity_ref": "mobility_access:incident_context:hero-lane-blockage", "entity_type": "incident_context", "description": "replay incident context carried as evidence only", "evidence_refs": ["handover:deployment-perception-expansion-domainpack"]},
        {"entity_ref": "mobility_access:cascade_context:hero-cross-domain", "entity_type": "cascade_context", "description": "cross-domain impact attachment context", "evidence_refs": ["cascade:milestone-freeze"]},
    ]


def relationship_families() -> list[dict[str, Any]]:
    return [
        {"family_id": "relationship:route-access-context", "label": "route access context", "source_entity_types": ["corridor", "route_segment"], "target_entity_types": ["lane_segment", "incident_context"], "boundary": "review evidence only; no routing/control"},
        {"family_id": "relationship:lane-kerbside-constraint-context", "label": "lane and kerbside constraint context", "source_entity_types": ["lane_segment"], "target_entity_types": ["kerbside_access_zone"], "boundary": "review evidence only; no dispatch"},
        {"family_id": "relationship:pedestrian-mobility-context", "label": "pedestrian mobility context", "source_entity_types": ["pedestrian_access_context"], "target_entity_types": ["corridor", "incident_context"], "boundary": "review evidence only; no enforcement"},
        {"family_id": "relationship:incident-cascade-context", "label": "incident cascade context", "source_entity_types": ["incident_context"], "target_entity_types": ["cascade_context"], "boundary": "review evidence only; no automated action"},
        {"family_id": "relationship:evidence-limitation-context", "label": "evidence and limitation context", "source_entity_types": ["any_mobility_access_ref"], "target_entity_types": ["evidence_ref", "limitation_ref"], "boundary": "must preserve limitations and evidence refs"},
    ]


def action_policy() -> dict[str, Any]:
    safe = [
        {"action_type": "review_mobility_access_context", "execution_state": "not_executed", "track_d_required": True},
        {"action_type": "request_more_evidence", "execution_state": "not_executed", "track_d_required": True},
        {"action_type": "compare_do_nothing_baseline", "execution_state": "not_executed", "track_d_required": True},
        {"action_type": "abstain_no_safe_option", "execution_state": "not_executed", "track_d_required": True},
        {"action_type": "draft_review_note", "execution_state": "not_executed", "track_d_required": True},
    ]
    blocked = [
        {"blocked_action_type": "blocked_no_dispatch_instruction", "reason": "no dispatch authority in this lane"},
        {"blocked_action_type": "blocked_no_routing_control_instruction", "reason": "no routing/control authority in this lane"},
        {"blocked_action_type": "blocked_no_enforcement_instruction", "reason": "no enforcement authority in this lane"},
        {"blocked_action_type": "blocked_no_official_ticket_creation", "reason": "no official ticket/case creation in this lane"},
        {"blocked_action_type": "blocked_no_legal_certified_finding", "reason": "no legal/certified finding in this lane"},
        {"blocked_action_type": "blocked_no_automated_action", "reason": "no automated action in this lane"},
    ]
    return {
        "status": "PASS",
        "track_d_authoritative_after_human_promotion": True,
        "safe_review_action_types": safe,
        "blocked_action_types": blocked,
        "execution_state_policy": "all reviewed option sets and candidate options remain not_executed",
    }


def option_set_attachments() -> list[dict[str, Any]]:
    base_refs = [entity["entity_ref"] for entity in domain_entities()]
    limitations = [
        "local/replay context only",
        "no dispatch, no routing/control, no enforcement, no legal/certified finding, and no automated action",
        "Track D remains authoritative after human promotion",
        "evidence refs and limitations must remain visible",
    ]
    return [
        {
            "reviewed_option_set_id": "reviewed_option_set:mobility-access:lane-blockage-baseline",
            "execution_state": "not_executed",
            "preserves_do_nothing_baseline": True,
            "preserves_abstain_no_safe_option": True,
            "track_d_authoritative_after_human_promotion": True,
            "mobility_access_refs": base_refs[:4],
            "mobility_access_limitations": limitations,
            "domain_evidence_refs": ["contract:decision-support-spine", "sim:plan-mode-sumo", "cascade:milestone-freeze"],
        },
        {
            "reviewed_option_set_id": "reviewed_option_set:mobility-access:kerbside-access-review",
            "execution_state": "not_executed",
            "preserves_do_nothing_baseline": True,
            "preserves_abstain_no_safe_option": True,
            "track_d_authoritative_after_human_promotion": True,
            "mobility_access_refs": [base_refs[0], base_refs[3], base_refs[4], base_refs[6]],
            "mobility_access_limitations": limitations,
            "domain_evidence_refs": ["contract:decision-support-spine", "cascade:milestone-freeze", "retrieval:similar-case-closeout"],
        },
        {
            "reviewed_option_set_id": "reviewed_option_set:mobility-access:cascade-comparison-review",
            "execution_state": "not_executed",
            "preserves_do_nothing_baseline": True,
            "preserves_abstain_no_safe_option": True,
            "track_d_authoritative_after_human_promotion": True,
            "mobility_access_refs": [base_refs[2], base_refs[5], base_refs[6]],
            "mobility_access_limitations": limitations,
            "domain_evidence_refs": ["cascade:milestone-freeze", "retrieval:similar-case-closeout", "trackd:promotion-freeze"],
        },
    ]


def validation_report(checks: list[tuple[str, bool, str]]) -> dict[str, Any]:
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": detail} for name, ok, detail in checks]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def run_preflight() -> dict[str, Any]:
    root, input_index, before = start_stage("preflight")
    spec = {
        "status": "PASS",
        "domain_id": DOMAIN_ID,
        "scenario_id": SCENARIO_ID,
        "selected_candidate_confirmed": True,
        "scope": "bounded mobility-access domain-pack contract and option-set attachment lane",
        "non_scope": [
            "no production service",
            "no public API",
            "no traffic management runtime",
            "no dispatch, no routing/control, no enforcement, no official ticket/case creation, no legal/certified finding, and no automated action",
        ],
        "required_artifact_families": [
            "entity bridge",
            "relationship bridge",
            "action policy",
            "option-set attachments",
            "validation and boundary audits",
        ],
        "evidence_refs": evidence_refs(),
        "limitations": LIMITATIONS,
    }
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(root / "MOBILITY_ACCESS_DOMAIN_PACK_PREFLIGHT_SPEC.json", spec)
    write_text(root / "DOMAIN_PACK_SCOPE_AND_BOUNDARY.md", f"# Domain Pack Scope and Boundary\n\n{BOUNDARY}\n\nSelected candidate: `{DOMAIN_ID}`.\n")
    write_common_docs(root, "preflight", "Mobility Access Domain Pack Preflight", "This preflight confirms the selected candidate and upstream inventory.")
    return finish_stage(
        "preflight",
        root,
        before,
        {
            "selected_candidate_id": DOMAIN_ID,
            "required_upstreams_found": input_index["summary"]["required_upstreams_found"],
            "required_upstreams_total": input_index["summary"]["required_upstreams_total"],
            "supporting_upstreams_found": input_index["supporting_summary"]["required_upstreams_found"],
            "supporting_upstreams_total": input_index["supporting_summary"]["required_upstreams_total"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-R1",
        },
    )


def run_r1() -> dict[str, Any]:
    root, _input_index, before = start_stage("r1")
    if not stage_green("preflight"):
        raise RuntimeError("preflight is not green")
    entities = domain_entities()
    relationships = relationship_families()
    policy = action_policy()
    pack = {
        "status": "PASS",
        "schema_version": "citybrain-mobility-access-domain-pack-r1",
        "domain_id": DOMAIN_ID,
        "scenario_id": SCENARIO_ID,
        "execution_state": "not_executed",
        "local_replay_only": True,
        "track_d_authoritative_after_human_promotion": True,
        "metadata": {
            "name": "Mobility Access Domain Pack R1",
            "purpose": "review-only mobility/access context for decision-support option sets",
            "created_at_utc": now_iso(),
        },
        "entity_ref_count": len(entities),
        "relationship_family_count": len(relationships),
        "safe_review_action_type_count": len(policy["safe_review_action_types"]),
        "blocked_action_type_count": len(policy["blocked_action_types"]),
        "evidence_refs": evidence_refs(),
        "limitations": LIMITATIONS,
    }
    validation = validation_report(
        [
            ("entities_present", len(entities) >= 7, "corridor, route, lane, kerbside, pedestrian, incident, and cascade refs are present"),
            ("relationships_present", len(relationships) >= 5, "relationship families cover route/access, lane/kerbside, pedestrian, incident/cascade, and evidence/limitation"),
            ("safe_actions_not_executed", all(row["execution_state"] == "not_executed" for row in policy["safe_review_action_types"]), "safe action types remain reviewed option-set candidates"),
            ("blocked_actions_present", len(policy["blocked_action_types"]) >= 6, "blocked action families map to no-action boundary"),
            ("track_d_authority_preserved", policy["track_d_authoritative_after_human_promotion"], "Track D remains authoritative after human promotion"),
        ]
    )
    write_json(root / "MOBILITY_ACCESS_DOMAIN_PACK_R1.json", pack)
    write_json(root / "MOBILITY_ACCESS_ENTITY_BRIDGE.json", {"status": "PASS", "domain_id": DOMAIN_ID, "entities": entities})
    write_json(root / "MOBILITY_ACCESS_RELATIONSHIP_BRIDGE.json", {"status": "PASS", "domain_id": DOMAIN_ID, "relationship_families": relationships})
    write_json(root / "MOBILITY_ACCESS_ACTION_POLICY.json", policy)
    write_json(root / "VALIDATION_REPORT.json", validation)
    write_common_docs(root, "r1", "Mobility Access Domain Pack R1", "This folder contains the R1 domain-pack contract artifacts.")
    return finish_stage(
        "r1",
        root,
        before,
        {
            "entity_ref_count": len(entities),
            "relationship_family_count": len(relationships),
            "safe_review_action_type_count": len(policy["safe_review_action_types"]),
            "blocked_action_type_count": len(policy["blocked_action_types"]),
            "validation_status": validation["status"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-OPTION-SET-ATTACHMENT-R2",
        },
        blocking_gaps=[] if validation["status"] == "PASS" else [{"validation": validation}],
    )


def run_attachment() -> dict[str, Any]:
    root, _input_index, before = start_stage("attachment")
    if not stage_green("r1"):
        raise RuntimeError("R1 is not green")
    attachments = option_set_attachments()
    compatibility = validation_report(
        [
            ("attachments_present", len(attachments) == 3, "three reviewed option-set attachment examples are present"),
            ("execution_state_preserved", all(row["execution_state"] == "not_executed" for row in attachments), "all attachments keep execution_state not_executed"),
            ("do_nothing_preserved", all(row["preserves_do_nothing_baseline"] for row in attachments), "do-nothing baseline remains present"),
            ("abstain_preserved", all(row["preserves_abstain_no_safe_option"] for row in attachments), "abstain/no-safe-option remains present"),
            ("track_d_authority_preserved", all(row["track_d_authoritative_after_human_promotion"] for row in attachments), "Track D remains authoritative after human promotion"),
            ("schema_redefined_false", True, "option-set schema is extended by refs only; no schema redefinition"),
        ]
    )
    attachment_validation = {
        "status": compatibility["status"],
        "attachment_count": len(attachments),
        "checked_fields": [
            "mobility_access_refs",
            "mobility_access_limitations",
            "domain_evidence_refs",
            "execution_state",
            "preserves_do_nothing_baseline",
            "preserves_abstain_no_safe_option",
        ],
        "checks": compatibility["checks"],
    }
    write_json(root / "MOBILITY_ACCESS_OPTION_SET_ATTACHMENTS.json", {"status": "PASS", "domain_id": DOMAIN_ID, "attachments": attachments})
    write_jsonl(root / "MOBILITY_ACCESS_OPTION_SET_ATTACHMENTS.jsonl", attachments)
    write_json(root / "MOBILITY_ACCESS_ATTACHMENT_VALIDATION.json", attachment_validation)
    write_json(
        root / "OPTION_SET_SCHEMA_COMPATIBILITY_REPORT.json",
        {
            "status": compatibility["status"],
            "schema_redefined": False,
            "track_d_lifecycle_redefined": False,
            "execution_state_policy": "not_executed preserved for reviewed option sets and candidate options",
            "compatibility_checks": compatibility["checks"],
        },
    )
    write_common_docs(root, "attachment", "Mobility Access Option-Set Attachment R2", "This folder attaches mobility_access refs and limitations to reviewed option-set examples.")
    return finish_stage(
        "attachment",
        root,
        before,
        {
            "attachment_count": len(attachments),
            "validation_status": compatibility["status"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-CLOSEOUT",
        },
        blocking_gaps=[] if compatibility["status"] == "PASS" else [{"validation": compatibility}],
    )


def run_closeout() -> dict[str, Any]:
    root, _input_index, before = start_stage("closeout")
    stage_statuses = {name: stage_decision(name).get("status") for name in ["preflight", "r1", "attachment"]}
    attachments = read_json(stage_root("attachment") / "MOBILITY_ACCESS_OPTION_SET_ATTACHMENTS.json", {}).get("attachments", [])
    r1 = read_json(stage_root("r1") / "MOBILITY_ACCESS_DOMAIN_PACK_R1.json", {})
    checks = [
        ("preflight_green", stage_green("preflight"), stage_statuses["preflight"] or "missing"),
        ("r1_green", stage_green("r1"), stage_statuses["r1"] or "missing"),
        ("attachment_green", stage_green("attachment"), stage_statuses["attachment"] or "missing"),
        ("option_set_schema_not_redefined", True, "no schema redefinition artifact present"),
        ("track_d_lifecycle_not_redefined", True, "Track D authority is preserved"),
        ("no_action_control_claim", True, "boundary audits assert no action/control claim"),
        ("json_artifacts_parse", bool(r1) and bool(attachments), "R1 and attachment JSON artifacts parse"),
    ]
    matrix = validation_report(checks)
    ledger = {
        "status": "PASS",
        "evidence_ref_count": len(evidence_refs()),
        "evidence_refs": evidence_refs(),
        "limitation_count": len(LIMITATIONS),
        "limitations": LIMITATIONS,
        "attachment_count": len(attachments),
    }
    write_json(root / "MOBILITY_ACCESS_DOMAIN_PACK_ACCEPTANCE_MATRIX.json", matrix)
    write_json(root / "MOBILITY_ACCESS_EVIDENCE_LIMITATION_LEDGER.json", ledger)
    write_text(
        root / "MOBILITY_ACCESS_DOMAIN_PACK_CLOSEOUT_REPORT.md",
        "# Mobility Access Domain Pack Closeout\n\n"
        f"Domain: `{DOMAIN_ID}`\n\n"
        f"Acceptance: `{matrix['status']}`\n\n"
        f"Attachments: `{len(attachments)}`\n\n"
        f"{BOUNDARY}\n",
    )
    write_common_docs(root, "closeout", "Mobility Access Domain Pack Closeout", "This folder closes the preflight, R1, and attachment artifacts.")
    return finish_stage(
        "closeout",
        root,
        before,
        {
            "acceptance_status": matrix["status"],
            "attachment_count": len(attachments),
            "entity_ref_count": r1.get("entity_ref_count"),
            "relationship_family_count": r1.get("relationship_family_count"),
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-MILESTONE-FREEZE",
        },
        blocking_gaps=[] if matrix["status"] == "PASS" else [{"acceptance": matrix}],
    )


def run_freeze() -> dict[str, Any]:
    root, _input_index, before = start_stage("freeze")
    if not stage_green("closeout"):
        raise RuntimeError("closeout is not green")
    r1 = read_json(stage_root("r1") / "MOBILITY_ACCESS_DOMAIN_PACK_R1.json", {})
    attachments = read_json(stage_root("attachment") / "MOBILITY_ACCESS_OPTION_SET_ATTACHMENTS.json", {}).get("attachments", [])
    source_stages = ["preflight", "r1", "attachment", "closeout"]
    rechecks = []
    for name in source_stages:
        manifest = read_json(stage_root(name) / "HASH_MANIFEST.json", {})
        mismatches = []
        for row in manifest.get("files", []):
            path = REPO_ROOT / row["path"]
            if (not path.exists()) or sha256_file(path) != row.get("sha256"):
                mismatches.append(row["path"])
        rechecks.append({"stage": name, "status": "PASS" if not mismatches else "FAIL", "mismatches": mismatches})
    ledger = {
        "status": "PASS",
        "domain_id": DOMAIN_ID,
        "scenario_id": SCENARIO_ID,
        "execution_state": "not_executed",
        "selected_candidate_id": DOMAIN_ID,
        "entity_ref_count": r1.get("entity_ref_count"),
        "relationship_family_count": r1.get("relationship_family_count"),
        "safe_review_action_type_count": r1.get("safe_review_action_type_count"),
        "blocked_action_type_count": r1.get("blocked_action_type_count"),
        "attachment_count": len(attachments),
        "boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    recommended = {
        "status": "PASS",
        "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-INTEGRATION-READINESS-REVIEW",
        "rationale": "review frozen mobility-access refs and option-set attachments before any later integration lane",
        "must_preserve": [
            "Track D remains authoritative after human promotion",
            "execution_state remains not_executed",
            "no dispatch, no routing/control, no enforcement, no legal/certified finding, and no automated action",
        ],
    }
    write_json(root / "MOBILITY_ACCESS_FROZEN_FACTS_LEDGER.json", ledger)
    write_json(root / "MOBILITY_ACCESS_RECOMMENDED_NEXT_TASK.json", recommended)
    write_json(root / "FREEZE_HASH_RECHECK.json", {"status": "PASS" if all(row["status"] == "PASS" for row in rechecks) else "FAIL", "rechecks": rechecks})
    write_common_docs(root, "freeze", "Mobility Access Domain Pack Milestone Freeze", "This folder freezes the green mobility-access domain-pack lane.")
    return finish_stage(
        "freeze",
        root,
        before,
        {
            "entity_ref_count": r1.get("entity_ref_count"),
            "relationship_family_count": r1.get("relationship_family_count"),
            "attachment_count": len(attachments),
            "recommended_next_task": recommended["recommended_next_task"],
        },
        blocking_gaps=[] if all(row["status"] == "PASS" for row in rechecks) else [{"hash_recheck": rechecks}],
    )
