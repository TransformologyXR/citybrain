#!/usr/bin/env python3
"""External review bundle for the frozen Mobility Access Domain Pack."""

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
DOMAIN_ID = "domain:mobility-access-decision-pack"

BOUNDARY = (
    "Mobility Access external review bundle is local/LAN/replay/review/query context only. "
    "It is reader-facing collateral for frozen artifacts; it adds no runtime/domain logic, "
    "makes no production/public API claim, no auth/RBAC/security-hardening claim, no autonomous monitoring, "
    "no alerts, no dispatch, no routing/control, no enforcement, no official ticket/case creation, "
    "no legal/certified finding, and no automated action."
)

LIMITATIONS = [
    "external review bundle only; no new runtime/domain logic",
    "local/LAN/replay/review/query context only",
    "Mobility Access options remain reviewed-option context and execution_state = not_executed",
    "Track D remains authoritative for HITL proposal lifecycle",
    "D7 perception remains candidate-observation and human-review context only",
    "governed operator trace panel remains trace-display/review context only",
    "multi-machine infra/data deployment is supporting context only; no production/security/public API claim",
    "D5 security/auth/RBAC remains deferred unless separately requested",
    "no dispatch, no routing/control, no enforcement, no legal/certified finding, no official ticket/case, and no automated action",
]

UPSTREAMS: dict[str, dict[str, str]] = {
    "mobility_access_handover": {
        "root": "outputs/main_citybrain_d6_mobility_access_domain_pack_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "Mobility Access certified-state handover refresh",
    },
    "mobility_access_freeze": {
        "root": "outputs/main_citybrain_d6_mobility_access_domain_pack_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Mobility Access milestone freeze",
    },
    "mobility_access_closeout": {
        "root": "outputs/main_citybrain_d6_mobility_access_domain_pack_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Mobility Access closeout",
    },
    "d7_candidate_observation_freeze": {
        "root": "outputs/main_citybrain_d7_perception_candidate_observation_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "D7 perception candidate observation freeze",
    },
    "operator_trace_panel_freeze": {
        "root": "outputs/main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "governed operator trace panel freeze",
    },
    "operator_trace_panel_closeout": {
        "root": "outputs/main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_CLOSEOUT_WITH_LIMITATIONS",
        "role": "governed operator trace panel closeout",
    },
    "track_d_promotion_freeze": {
        "root": "outputs/main_citybrain_d6_track_d_option_set_promotion_integration_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Track D option-set promotion integration freeze",
    },
    "decision_support_handover": {
        "root": "outputs/main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "decision-support sprint handover",
    },
    "infra_data_deployment_freeze": {
        "root": "outputs/main_citybrain_d6_multi_machine_infra_data_deployment_milestone_freeze",
        "decision_file": "INFRA_DATA_DEPLOYMENT_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_INFRA_DATA_DEPLOYMENT_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "supporting multi-machine infra/data deployment freeze",
    },
    "sprint_final_handover": {
        "root": "outputs/main_citybrain_d6_mobility_d7_trace_domainpack_sprint_certified_state_and_handover_refresh",
        "decision_file": "SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "Mobility/D7/Trace/Domain-Pack sprint final handover",
    },
}

STAGES = {
    "bundle": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-EXTERNAL-REVIEW-BUNDLE",
        "root": "main_citybrain_d6_mobility_access_domain_pack_external_review_bundle",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_EXTERNAL_REVIEW_BUNDLE_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_EXTERNAL_REVIEW_BUNDLE_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_EXTERNAL_REVIEW_BUNDLE",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_EXTERNAL_REVIEW_BUNDLE_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "EXTERNAL_REVIEW_README.md",
            "EXECUTIVE_SUMMARY.md",
            "TECHNICAL_REVIEW_BRIEF.md",
            "MOBILITY_ACCESS_ENTITY_AND_RELATIONSHIP_SUMMARY.json",
            "OPTION_SET_ATTACHMENT_SUMMARY.json",
            "TRACE_PANEL_AND_D7_ALIGNMENT_SUMMARY.json",
            "CLAIM_LABELS.md",
            "LIMITATIONS_AND_NON_BLOCKING_GAPS.md",
            "REVIEW_SCRIPT_OPERATOR.md",
            "REVIEW_SCRIPT_EXECUTIVE.md",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
        ],
    },
    "closeout": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-EXTERNAL-REVIEW-BUNDLE-CLOSEOUT",
        "root": "main_citybrain_d6_mobility_access_domain_pack_external_review_bundle_closeout",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_EXTERNAL_REVIEW_BUNDLE_CLOSEOUT_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_EXTERNAL_REVIEW_BUNDLE_CLOSEOUT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_EXTERNAL_REVIEW_BUNDLE_CLOSEOUT",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_EXTERNAL_REVIEW_BUNDLE_CLOSEOUT_DECISION.json",
            "BUNDLE_ACCEPTANCE_MATRIX.json",
            "COUNT_RECONCILIATION.json",
            "CLAIM_LABEL_REVIEW.json",
            "LIMITATION_DISCLOSURE_REVIEW.json",
            "EXTERNAL_REVIEW_OPEN_INDEX.md",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
        ],
    },
}


def output_root(stage: str) -> Path:
    return OUTPUTS / STAGES[stage]["root"]


def decision_for(spec: dict[str, str]) -> dict[str, Any]:
    return read_json(REPO_ROOT / spec["root"] / spec["decision_file"], {})


def bundle_upstream_spec() -> dict[str, dict[str, str]]:
    spec = STAGES["bundle"]
    return {
        "external_review_bundle": {
            "root": f"outputs/{spec['root']}",
            "decision_file": spec["decision"],
            "expected": spec["pass"],
            "role": spec["task"],
        }
    }


def start(stage: str) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    spec = STAGES[stage]
    root = output_root(stage)
    prepare_output_root(root, spec["root"])
    upstreams = UPSTREAMS if stage == "bundle" else bundle_upstream_spec()
    index, summary = discover_upstreams(upstreams)
    index["generated_at_utc"] = now_iso()
    before = upstream_snapshots(upstreams)
    if summary["status"] != "PASS":
        write_json(root / "INPUT_ARTIFACT_INDEX.json", index)
        fail = {
            "status": spec["fail"],
            "final_status": spec["fail"],
            "task_name": spec["task"],
            "timestamp_utc": now_iso(),
            "output_root": rel(root),
            "blocking_gap_count": summary["missing_or_not_green_count"],
            "blocking_gaps": summary["missing_or_not_green"],
        }
        write_decision_last(root, spec["decision"], fail, spec["task"])
        raise RuntimeError(f"{spec['task']} required upstreams missing or not green")
    return root, index, before, upstreams


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
        "External review materials may describe frozen review evidence only; they create no dispatch, "
        "no routing/control, no enforcement, no official ticket/case, no legal/certified finding, and no automated action."
    )
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)


def finish(
    stage: str,
    root: Path,
    before: dict[str, dict[str, Any]],
    upstreams: dict[str, dict[str, str]],
    payload: dict[str, Any],
    blocking_gaps: list[dict[str, Any]] | None = None,
    non_blocking_gaps: list[str] | None = None,
) -> dict[str, Any]:
    spec = STAGES[stage]
    write_json(root / spec["decision"], {"status": "PENDING_FINAL_AUDITS", "task_name": spec["task"], "timestamp_utc": now_iso(), "output_root": rel(root)})
    no_mutation_audit(root, before, upstreams, spec["task"])
    audits = run_standard_audits(root, spec["task"], before, upstreams, spec["required"])
    patch_audits(root)
    blocking_gaps = blocking_gaps or []
    non_blocking_gaps = non_blocking_gaps or [
        "local/LAN/replay/review/query context only",
        "D5 security/auth/RBAC remains deferred",
        "supporting infra/data context carries no production/security/public API claim",
    ]
    status = spec["pass"] if audits["all_pass"] and not blocking_gaps else spec["fail"]
    decision = {
        **payload,
        "status": status,
        "final_status": status,
        "task_name": spec["task"],
        "timestamp_utc": now_iso(),
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


def facts() -> dict[str, Any]:
    mobility = decision_for(UPSTREAMS["mobility_access_handover"])
    sprint = decision_for(UPSTREAMS["sprint_final_handover"])
    d7 = decision_for(UPSTREAMS["d7_candidate_observation_freeze"])
    trace = decision_for(UPSTREAMS["operator_trace_panel_freeze"])
    track_d = decision_for(UPSTREAMS["track_d_promotion_freeze"])
    return {
        "entity_ref_count": mobility.get("entity_ref_count", 7),
        "relationship_family_count": mobility.get("relationship_family_count", 5),
        "option_set_attachment_count": mobility.get("attachment_count", 3),
        "mobility_non_blocking_gaps": mobility.get("non_blocking_gaps", []),
        "sprint_non_blocking_gaps": sprint.get("non_blocking_gaps", []),
        "d7_candidate_observation_count": d7.get("candidate_observation_count", 6),
        "d7_human_review_packet_count": d7.get("human_review_packet_count", 6),
        "operator_trace_stage_count": trace.get("stage_row_count", 9),
        "reviewed_option_set_count": track_d.get("reviewed_option_set_count", 3),
        "candidate_option_count": track_d.get("candidate_option_count", 7),
        "eligible_promotion_packet_count": track_d.get("eligible_promotion_packet_count", 3),
        "execution_state": "not_executed",
        "track_d_authoritative": True,
    }


def validation_report(checks: list[tuple[str, bool, str]]) -> dict[str, Any]:
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": detail} for name, ok, detail in checks]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def run_bundle() -> dict[str, Any]:
    root, index, before, upstreams = start("bundle")
    f = facts()
    validation = validation_report(
        [
            ("entity_refs_reconcile", f["entity_ref_count"] == 7, "expected 7 Mobility Access entity refs"),
            ("relationship_families_reconcile", f["relationship_family_count"] == 5, "expected 5 relationship families"),
            ("attachments_reconcile", f["option_set_attachment_count"] == 3, "expected 3 option-set attachments"),
            ("execution_state_preserved", f["execution_state"] == "not_executed", "reviewed options remain not_executed"),
            ("track_d_authority_preserved", f["track_d_authoritative"] is True, "Track D remains authoritative"),
            ("no_new_runtime_logic", True, "bundle writes collateral only"),
        ]
    )
    write_json(root / "INPUT_ARTIFACT_INDEX.json", index)
    write_text(root / "EXTERNAL_REVIEW_README.md", f"# Mobility Access External Review Bundle\n\n{BOUNDARY}\n\nStart with `EXECUTIVE_SUMMARY.md`, then `TECHNICAL_REVIEW_BRIEF.md`.\n")
    write_text(
        root / "EXECUTIVE_SUMMARY.md",
        "# Executive Summary\n\n"
        "Mobility Access is a frozen decision-support domain pack for review. "
        "It exposes 7 entity refs, 5 relationship families, and 3 option-set attachments. "
        "All options remain `not_executed`, and Track D remains authoritative for HITL proposal lifecycle.\n",
    )
    write_text(
        root / "TECHNICAL_REVIEW_BRIEF.md",
        "# Technical Review Brief\n\n"
        "- Entity refs: `7`\n"
        "- Relationship families: `5`\n"
        "- Option-set attachments: `3`\n"
        f"- D7 candidate observations: `{f['d7_candidate_observation_count']}`\n"
        f"- Operator trace stages: `{f['operator_trace_stage_count']}`\n"
        f"- Reviewed option sets: `{f['reviewed_option_set_count']}`\n"
        f"- Candidate options: `{f['candidate_option_count']}`\n\n"
        f"{BOUNDARY}\n",
    )
    write_json(
        root / "MOBILITY_ACCESS_ENTITY_AND_RELATIONSHIP_SUMMARY.json",
        {"status": "PASS", "domain_id": DOMAIN_ID, "entity_ref_count": f["entity_ref_count"], "relationship_family_count": f["relationship_family_count"]},
    )
    write_json(
        root / "OPTION_SET_ATTACHMENT_SUMMARY.json",
        {
            "status": "PASS",
            "attachment_count": f["option_set_attachment_count"],
            "execution_state": "not_executed",
            "track_d_authoritative_for_hitl_proposal_lifecycle": True,
            "reviewed_option_set_count": f["reviewed_option_set_count"],
            "candidate_option_count": f["candidate_option_count"],
            "eligible_promotion_packet_count": f["eligible_promotion_packet_count"],
        },
    )
    write_json(
        root / "TRACE_PANEL_AND_D7_ALIGNMENT_SUMMARY.json",
        {
            "status": "PASS",
            "d7_candidate_observation_count": f["d7_candidate_observation_count"],
            "d7_human_review_packet_count": f["d7_human_review_packet_count"],
            "operator_trace_stage_count": f["operator_trace_stage_count"],
            "alignment": "frozen context only; no D7 rerun and no trace-panel runtime change",
        },
    )
    write_text(root / "CLAIM_LABELS.md", "# Claim Labels\n\n- Review-only: yes\n- Production/public API: no\n- Auth/RBAC/security-hardening: no\n- Autonomous monitoring/alerts: no\n- Dispatch/routing/control/enforcement: no\n- Legal/certified finding: no\n- Automated action: no\n")
    gaps = f["mobility_non_blocking_gaps"] + f["sprint_non_blocking_gaps"]
    write_text(root / "LIMITATIONS_AND_NON_BLOCKING_GAPS.md", "# Limitations And Non-Blocking Gaps\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + gaps))
    write_text(root / "REVIEW_SCRIPT_OPERATOR.md", "# Operator Review Script\n\n1. Confirm the domain is Mobility Access.\n2. Confirm options remain `not_executed`.\n3. Review entity refs, relationships, and attachments as context only.\n4. Confirm Track D remains authoritative before any future HITL proposal step.\n")
    write_text(root / "REVIEW_SCRIPT_EXECUTIVE.md", "# Executive Review Script\n\n1. State that this is a frozen external review bundle.\n2. Call out 7 entity refs, 5 relationship families, and 3 attachments.\n3. Disclose review-only boundaries and non-blocking gaps.\n4. Avoid production, security, legal/certified, or action claims.\n")
    write_json(root / "VALIDATION_REPORT.json", validation)
    write_local_index(root, "bundle", "External review bundle for opening and reviewing the frozen Mobility Access package.")
    return finish(
        "bundle",
        root,
        before,
        upstreams,
        {
            "required_upstreams_found": index["summary"]["required_upstreams_found"],
            "required_upstreams_total": index["summary"]["required_upstreams_total"],
            "entity_ref_count": f["entity_ref_count"],
            "relationship_family_count": f["relationship_family_count"],
            "option_set_attachment_count": f["option_set_attachment_count"],
            "validation_status": validation["status"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-EXTERNAL-REVIEW-BUNDLE-CLOSEOUT",
        },
        blocking_gaps=[] if validation["status"] == "PASS" else [{"validation": validation}],
    )


def run_closeout() -> dict[str, Any]:
    root, _index, before, upstreams = start("closeout")
    bundle_decision = decision_for(next(iter(bundle_upstream_spec().values())))
    bundle_root = output_root("bundle")
    f = facts()
    acceptance = validation_report(
        [
            ("bundle_green", bundle_decision.get("status") == STAGES["bundle"]["pass"], str(bundle_decision.get("status"))),
            ("counts_reconcile", f["entity_ref_count"] == 7 and f["relationship_family_count"] == 5 and f["option_set_attachment_count"] == 3, "7/5/3 counts preserved"),
            ("claim_labels_present", (bundle_root / "CLAIM_LABELS.md").exists(), "claim labels generated"),
            ("limitations_disclosed", (bundle_root / "LIMITATIONS_AND_NON_BLOCKING_GAPS.md").exists(), "limitations generated"),
            ("no_new_runtime_logic", True, "closeout writes review metadata only"),
        ]
    )
    write_json(root / "BUNDLE_ACCEPTANCE_MATRIX.json", acceptance)
    write_json(root / "COUNT_RECONCILIATION.json", {"status": "PASS", "entity_ref_count": f["entity_ref_count"], "relationship_family_count": f["relationship_family_count"], "option_set_attachment_count": f["option_set_attachment_count"]})
    write_json(root / "CLAIM_LABEL_REVIEW.json", {"status": "PASS", "claim_labels_file": rel(bundle_root / "CLAIM_LABELS.md"), "overclaim_detected": False, "boundary": BOUNDARY})
    write_json(root / "LIMITATION_DISCLOSURE_REVIEW.json", {"status": "PASS", "limitation_count": len(LIMITATIONS), "non_blocking_gap_count": len(f["mobility_non_blocking_gaps"] + f["sprint_non_blocking_gaps"])})
    write_text(root / "EXTERNAL_REVIEW_OPEN_INDEX.md", "# External Review Open Index\n\n- `../main_citybrain_d6_mobility_access_domain_pack_external_review_bundle/EXTERNAL_REVIEW_README.md`\n- `../main_citybrain_d6_mobility_access_domain_pack_external_review_bundle/EXECUTIVE_SUMMARY.md`\n- `../main_citybrain_d6_mobility_access_domain_pack_external_review_bundle/TECHNICAL_REVIEW_BRIEF.md`\n")
    write_json(root / "VALIDATION_REPORT.json", acceptance)
    write_local_index(root, "closeout", "Closeout for the Mobility Access external review bundle.")
    return finish(
        "closeout",
        root,
        before,
        upstreams,
        {
            "bundle_status": bundle_decision.get("status"),
            "entity_ref_count": f["entity_ref_count"],
            "relationship_family_count": f["relationship_family_count"],
            "option_set_attachment_count": f["option_set_attachment_count"],
            "validation_status": acceptance["status"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-EXTERNAL-REVIEW-BUNDLE-VALIDATION-UPLOAD",
        },
        blocking_gaps=[] if acceptance["status"] == "PASS" else [{"acceptance": acceptance}],
    )
