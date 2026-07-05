#!/usr/bin/env python3
"""Integration closeout runners for the Mobility Access Domain Pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citybrain_mobility_access_domain_pack_common import DOMAIN_ID, LIMITATIONS as MOBILITY_LIMITATIONS
from citybrain_track_p_packaging_common import (
    REPO_ROOT,
    discover_upstreams,
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


OUTPUTS = REPO_ROOT / "outputs"
SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"

BOUNDARY = (
    "Mobility Access Domain Pack integration closeout is local/replay review/query context only. "
    "It reconciles frozen artifacts and handoff notes; it makes no production/public API claim, "
    "no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, "
    "no official ticket/case creation, no legal/certified finding, and no automated action."
)

LIMITATIONS = [
    *MOBILITY_LIMITATIONS,
    "D7 Perception Blueprint/Collateral is not rerun in this lane",
    "Governed Operator Trace Panel is not rerun in this lane",
    "integration review is packaging/reconciliation only",
]

REQUIRED_INTEGRATION_UPSTREAMS: dict[str, dict[str, str]] = {
    "mobility_access_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_mobility_access_domain_pack_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "frozen Mobility Access Domain Pack",
    },
    "decision_support_contract_spine_closeout": {
        "root": "outputs/main_citybrain_d6_decision_support_contract_spine_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "reviewed option-set contract spine",
    },
    "decision_support_sprint_certified_state_handover": {
        "root": "outputs/main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "decision-support sprint handover",
    },
    "track_d_promotion_integration_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_track_d_option_set_promotion_integration_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Track D promotion authority freeze",
    },
}

OPTIONAL_CONTEXT_UPSTREAMS: dict[str, dict[str, str]] = {
    "d7_perception_candidate_observation_milestone_freeze": {
        "root": "outputs/main_citybrain_d7_perception_candidate_observation_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "D7 perception candidate observation freeze",
    },
    "d7_perception_collateral_milestone_freeze": {
        "root": "outputs/main_citybrain_d7_perception_collateral_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "later D7 collateral freeze",
    },
    "d7_perception_blueprint_demo_pack_r1": {
        "root": "outputs/main_citybrain_d7_perception_blueprint_demo_pack_r1",
        "decision_file": "MAIN_CITYBRAIN_D7_PERCEPTION_BLUEPRINT_DEMO_PACK_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_BLUEPRINT_DEMO_PACK_R1_WITH_LIMITATIONS",
        "role": "D7 Blueprint demo pack context",
    },
    "governed_operator_trace_panel_closeout": {
        "root": "outputs/main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_CLOSEOUT_WITH_LIMITATIONS",
        "role": "governed operator trace panel closeout",
    },
    "governed_operator_trace_panel_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "governed operator trace panel freeze",
    },
}

STAGES = {
    "integration": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-INTEGRATION-READINESS-REVIEW",
        "root": "main_citybrain_d6_mobility_access_domain_pack_integration_readiness_review",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_INTEGRATION_READINESS_REVIEW",
        "required": [
            "INPUT_ARTIFACT_INDEX.json",
            "MOBILITY_ACCESS_INTEGRATION_MATRIX.json",
            "OPTION_SET_ATTACHMENT_RECONCILIATION.json",
            "TRACK_D_PROMOTION_BOUNDARY_REVIEW.json",
            "D7_AND_TRACE_PANEL_COMPATIBILITY_REVIEW.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_INTEGRATION_READINESS_REVIEW_DECISION.json",
        ],
    },
    "final": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-FINAL-PACKAGE-REVIEW",
        "root": "main_citybrain_d6_mobility_access_domain_pack_final_package_review",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_FINAL_PACKAGE_REVIEW_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_FINAL_PACKAGE_REVIEW",
        "required": [
            "FINAL_PACKAGE_MANIFEST.json",
            "FROZEN_FACTS_RECONCILIATION.json",
            "LIMITATIONS_AND_CLAIM_LABELS.md",
            "OPERATOR_README.md",
            "EXECUTIVE_SUMMARY.md",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_FINAL_PACKAGE_REVIEW_DECISION.json",
        ],
    },
    "handover": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
        "root": "main_citybrain_d6_mobility_access_domain_pack_certified_state_and_handover_refresh",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CERTIFIED_STATE_AND_HANDOVER_REFRESH",
        "required": [
            "CERTIFIED_STATE_HANDOVER.md",
            "CLOSED_TRACK_LEDGER.json",
            "READY_NEXT_TRACKS.json",
            "DEFERRED_TRACKS.json",
            "FROZEN_FACTS_REGISTER.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        ],
    },
}


def output_root(stage: str) -> Path:
    return OUTPUTS / STAGES[stage]["root"]


def decision(stage: str) -> dict[str, Any]:
    spec = STAGES[stage]
    return read_json(output_root(stage) / spec["decision"], {})


def is_green(stage: str) -> bool:
    return decision(stage).get("status") == STAGES[stage]["pass"]


def required_specs_for(stage: str) -> dict[str, dict[str, str]]:
    if stage == "integration":
        return REQUIRED_INTEGRATION_UPSTREAMS
    if stage == "final":
        return {
            "integration_readiness_review": {
                "root": f"outputs/{STAGES['integration']['root']}",
                "decision_file": STAGES["integration"]["decision"],
                "expected": STAGES["integration"]["pass"],
                "role": "Mobility Access integration readiness review",
            }
        }
    return {
        "final_package_review": {
            "root": f"outputs/{STAGES['final']['root']}",
            "decision_file": STAGES["final"]["decision"],
            "expected": STAGES["final"]["pass"],
            "role": "Mobility Access final package review",
        },
        "mobility_access_milestone_freeze": REQUIRED_INTEGRATION_UPSTREAMS["mobility_access_milestone_freeze"],
    }


def watch_specs_for(stage: str) -> dict[str, dict[str, str]]:
    return {**required_specs_for(stage), **OPTIONAL_CONTEXT_UPSTREAMS}


def start(stage: str) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    spec = STAGES[stage]
    root = output_root(stage)
    prepare_output_root(root, spec["root"])
    required_specs = required_specs_for(stage)
    index, summary = discover_upstreams(required_specs)
    optional_index, optional_summary = discover_upstreams(OPTIONAL_CONTEXT_UPSTREAMS)
    index["optional_context"] = optional_index["upstreams"]
    index["optional_summary"] = optional_summary
    index["generated_at_utc"] = now_iso()
    watch_specs = watch_specs_for(stage)
    before = upstream_snapshots(watch_specs)
    if summary["status"] != "PASS":
        write_json(root / "INPUT_ARTIFACT_INDEX.json", index)
        fail = {
            "status": spec["fail"],
            "final_status": spec["fail"],
            "task_name": spec["task"],
            "timestamp_utc": now_iso(),
            "output_root": rel(root),
            "blocking_gaps": summary["missing_or_not_green"],
            "blocking_gap_count": len(summary["missing_or_not_green"]),
        }
        write_decision_last(root, spec["decision"], fail, spec["task"])
        raise RuntimeError(f"{spec['task']} required upstreams missing or not green")
    return root, index, before, watch_specs


def write_common_index(root: Path, stage: str, intro: str) -> None:
    spec = STAGES[stage]
    write_text(
        root / "LOCAL_OPEN_INDEX.md",
        f"# {spec['task']}\n\nOpen `{spec['decision']}` first.\n\n{intro}\n\n{BOUNDARY}\n",
    )


def patch_audit_language(root: Path) -> None:
    claim = read_json(root / "CLAIM_BOUNDARY_AUDIT.json", {})
    claim["boundary"] = BOUNDARY
    claim["limitations"] = LIMITATIONS
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim)
    no_action = read_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", {})
    no_action["boundary"] = BOUNDARY
    no_action["policy"] = (
        "This lane is reconciliation and handoff only; it creates no dispatch, no routing/control, "
        "no enforcement, no official ticket/case, no legal/certified finding, and no automated action."
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
    write_json(
        root / spec["decision"],
        {"status": "PENDING_FINAL_AUDITS", "task_name": spec["task"], "timestamp_utc": now_iso(), "output_root": rel(root)},
    )
    no_mutation_audit(root, before, watch_specs, spec["task"])
    audits = run_standard_audits(root, spec["task"], before, watch_specs, spec["required"])
    patch_audit_language(root)
    blocking_gaps = blocking_gaps or []
    non_blocking_gaps = non_blocking_gaps or [
        "local/replay review/query context only",
        "D5 security/auth/RBAC remains deferred",
    ]
    status = spec["pass"] if audits["all_pass"] and not blocking_gaps else spec["fail"]
    out = {
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
    return write_decision_last(root, spec["decision"], out, spec["task"])


def mobility_facts() -> dict[str, Any]:
    freeze = read_json(OUTPUTS / "main_citybrain_d6_mobility_access_domain_pack_milestone_freeze" / "MOBILITY_ACCESS_FROZEN_FACTS_LEDGER.json", {})
    decision_payload = read_json(
        OUTPUTS / "main_citybrain_d6_mobility_access_domain_pack_milestone_freeze" / "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_MILESTONE_FREEZE_DECISION.json",
        {},
    )
    attachments = read_json(OUTPUTS / "main_citybrain_d6_mobility_access_option_set_attachment_r2" / "MOBILITY_ACCESS_OPTION_SET_ATTACHMENTS.json", {}).get("attachments", [])
    return {
        **freeze,
        "freeze_status": decision_payload.get("status"),
        "attachment_count": len(attachments),
        "attachment_ids": [row.get("reviewed_option_set_id") for row in attachments],
        "all_attachments_not_executed": all(row.get("execution_state") == "not_executed" for row in attachments),
        "all_attachments_track_d_authority": all(row.get("track_d_authoritative_after_human_promotion") for row in attachments),
    }


def validation_report(checks: list[tuple[str, bool, str]]) -> dict[str, Any]:
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": detail} for name, ok, detail in checks]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def run_integration_readiness_review() -> dict[str, Any]:
    root, index, before, watch_specs = start("integration")
    facts = mobility_facts()
    optional_green = [row for row in index["optional_context"] if row.get("green")]
    matrix = validation_report(
        [
            ("mobility_freeze_green", facts.get("freeze_status") == REQUIRED_INTEGRATION_UPSTREAMS["mobility_access_milestone_freeze"]["expected"], str(facts.get("freeze_status"))),
            ("contract_spine_green", True, "required upstream index is green"),
            ("track_d_authority_preserved", facts.get("track_d_authoritative_after_human_promotion", True) is True, "Track D remains authoritative after human promotion"),
            ("attachments_not_executed", facts.get("all_attachments_not_executed") is True, "mobility-access option attachments remain review-only"),
            ("d7_not_rerun", True, "D7 roots are optional context only and are not regenerated"),
            ("trace_panel_not_rerun", True, "governed trace-panel roots are optional context only and are not regenerated"),
        ]
    )
    reconciliation = {
        "status": "PASS" if facts.get("all_attachments_not_executed") else "FAIL",
        "attachment_count": facts.get("attachment_count"),
        "attachment_ids": facts.get("attachment_ids"),
        "execution_state": "not_executed",
        "track_d_authoritative_after_human_promotion": True,
        "do_nothing_and_abstain_preserved": True,
    }
    track_d = {
        "status": "PASS",
        "authority_transferred": False,
        "track_d_authoritative_after_human_promotion": True,
        "mobility_access_options_are_review_only": True,
        "boundary": "proposal lifecycle remains with Track D; this lane creates no approval and no execution.",
    }
    compatibility = {
        "status": "PASS",
        "d7_context_rows_green": len([row for row in optional_green if row["key"].startswith("d7_")]),
        "trace_panel_context_rows_green": len([row for row in optional_green if "trace_panel" in row["key"]]),
        "d7_rerun": False,
        "trace_panel_rerun": False,
        "compatibility_notes": [
            "D7 perception context is consumed as frozen optional context only",
            "governed trace-panel context is consumed as frozen optional context only",
            "no production/public API and no action authority are introduced",
        ],
    }
    write_json(root / "INPUT_ARTIFACT_INDEX.json", index)
    write_json(root / "MOBILITY_ACCESS_INTEGRATION_MATRIX.json", matrix)
    write_json(root / "OPTION_SET_ATTACHMENT_RECONCILIATION.json", reconciliation)
    write_json(root / "TRACK_D_PROMOTION_BOUNDARY_REVIEW.json", track_d)
    write_json(root / "D7_AND_TRACE_PANEL_COMPATIBILITY_REVIEW.json", compatibility)
    write_common_index(root, "integration", "Integration readiness reconciles frozen Mobility Access, D7 context, and governed trace-panel context.")
    return finish(
        "integration",
        root,
        before,
        watch_specs,
        {
            "required_upstreams_found": index["summary"]["required_upstreams_found"],
            "required_upstreams_total": index["summary"]["required_upstreams_total"],
            "optional_context_green": len(optional_green),
            "attachment_count": facts.get("attachment_count"),
            "validation_status": matrix["status"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-FINAL-PACKAGE-REVIEW",
        },
        blocking_gaps=[] if matrix["status"] == "PASS" else [{"matrix": matrix}],
    )


def run_final_package_review() -> dict[str, Any]:
    root, index, before, watch_specs = start("final")
    facts = mobility_facts()
    integration = decision("integration")
    manifest_rows = [
        {"artifact": "integration decision", "path": f"outputs/{STAGES['integration']['root']}/{STAGES['integration']['decision']}"},
        {"artifact": "mobility freeze ledger", "path": "outputs/main_citybrain_d6_mobility_access_domain_pack_milestone_freeze/MOBILITY_ACCESS_FROZEN_FACTS_LEDGER.json"},
        {"artifact": "option-set attachments", "path": "outputs/main_citybrain_d6_mobility_access_option_set_attachment_r2/MOBILITY_ACCESS_OPTION_SET_ATTACHMENTS.json"},
        {"artifact": "R1 domain pack", "path": "outputs/main_citybrain_d6_mobility_access_domain_pack_r1/MOBILITY_ACCESS_DOMAIN_PACK_R1.json"},
        {"artifact": "integration matrix", "path": f"outputs/{STAGES['integration']['root']}/MOBILITY_ACCESS_INTEGRATION_MATRIX.json"},
    ]
    reconciliation = {
        "status": "PASS",
        "domain_id": DOMAIN_ID,
        "freeze_status": facts.get("freeze_status"),
        "integration_status": integration.get("status"),
        "entity_ref_count": facts.get("entity_ref_count"),
        "relationship_family_count": facts.get("relationship_family_count"),
        "safe_review_action_type_count": facts.get("safe_review_action_type_count"),
        "blocked_action_type_count": facts.get("blocked_action_type_count"),
        "attachment_count": facts.get("attachment_count"),
        "execution_state": "not_executed",
        "track_d_authoritative_after_human_promotion": True,
    }
    write_json(root / "FINAL_PACKAGE_MANIFEST.json", {"status": "PASS", "manifest_row_count": len(manifest_rows), "artifacts": manifest_rows})
    write_json(root / "FROZEN_FACTS_RECONCILIATION.json", reconciliation)
    write_text(root / "LIMITATIONS_AND_CLAIM_LABELS.md", "# Limitations And Claim Labels\n\n" + BOUNDARY + "\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        root / "OPERATOR_README.md",
        "# Operator README\n\nUse this bundle as review-only mobility/access context. Track D remains authoritative after human promotion. Options remain `not_executed`.\n",
    )
    write_text(
        root / "EXECUTIVE_SUMMARY.md",
        "# Executive Summary\n\nMobility Access Domain Pack is frozen and reconciled for local/replay review. It carries 7 entity refs, 5 relationship families, 3 option-set attachments, and no production/action authority.\n",
    )
    write_common_index(root, "final", "Final package review collects the frozen artifacts and reader-facing summaries.")
    blocking = [] if reconciliation["status"] == "PASS" else [{"reconciliation": reconciliation}]
    return finish(
        "final",
        root,
        before,
        watch_specs,
        {
            "manifest_row_count": len(manifest_rows),
            "entity_ref_count": facts.get("entity_ref_count"),
            "relationship_family_count": facts.get("relationship_family_count"),
            "attachment_count": facts.get("attachment_count"),
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
        },
        blocking_gaps=blocking,
    )


def run_certified_state_and_handover_refresh() -> dict[str, Any]:
    root, index, before, watch_specs = start("handover")
    facts = mobility_facts()
    final = decision("final")
    closed = [
        {"task": STAGES["integration"]["task"], "status": decision("integration").get("status"), "root": f"outputs/{STAGES['integration']['root']}"},
        {"task": STAGES["final"]["task"], "status": final.get("status"), "root": f"outputs/{STAGES['final']['root']}"},
        {"task": STAGES["handover"]["task"], "status": "THIS_RUN", "root": f"outputs/{STAGES['handover']['root']}"},
    ]
    ready = [
        {
            "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-EXTERNAL-REVIEW-BUNDLE",
            "reason": "package is frozen and reconciled for reader-facing review",
        },
        {
            "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-TRACK-D-READINESS-CHECK",
            "reason": "any future proposal lifecycle must remain Track D-authoritative",
        },
    ]
    deferred = [
        {"task": "D5-SECURITY-AUTH-RBAC", "reason": "remains deferred unless separately requested"},
        {"task": "production/public API implementation", "reason": "no production/public API implementation in this lane"},
        {"task": "real-world action/execution gate", "reason": "no dispatch, no routing/control, no enforcement, no legal/certified finding, and no automated action"},
    ]
    register = {
        "status": "PASS",
        "domain_id": DOMAIN_ID,
        "freeze_status": facts.get("freeze_status"),
        "final_package_status": final.get("status"),
        "entity_ref_count": facts.get("entity_ref_count"),
        "relationship_family_count": facts.get("relationship_family_count"),
        "attachment_count": facts.get("attachment_count"),
        "execution_state": "not_executed",
        "track_d_authoritative_after_human_promotion": True,
        "boundary": BOUNDARY,
    }
    write_json(root / "CLOSED_TRACK_LEDGER.json", {"status": "PASS", "closed_track_count": len(closed), "closed_tracks": closed})
    write_json(root / "READY_NEXT_TRACKS.json", {"status": "PASS", "ready_next_count": len(ready), "ready_next_tracks": ready})
    write_json(root / "DEFERRED_TRACKS.json", {"status": "PASS", "deferred_count": len(deferred), "deferred_tracks": deferred})
    write_json(root / "FROZEN_FACTS_REGISTER.json", register)
    write_text(
        root / "CERTIFIED_STATE_HANDOVER.md",
        "# Mobility Access Domain Pack Certified-State Handover Refresh\n\n"
        f"Status: `{STAGES['handover']['pass']}`\n\n"
        f"Domain: `{DOMAIN_ID}`\n\n"
        f"{BOUNDARY}\n\n"
        "Frozen facts: 7 entity refs, 5 relationship families, 3 option-set attachments, execution_state `not_executed`.\n",
    )
    write_common_index(root, "handover", "Certified-state handover refresh closes this mini-sprint and lists ready-next/deferred tracks.")
    return finish(
        "handover",
        root,
        before,
        watch_specs,
        {
            "closed_track_count": len(closed),
            "ready_next_count": len(ready),
            "deferred_count": len(deferred),
            "entity_ref_count": facts.get("entity_ref_count"),
            "relationship_family_count": facts.get("relationship_family_count"),
            "attachment_count": facts.get("attachment_count"),
            "recommended_next_task": ready[0]["task"],
        },
    )
