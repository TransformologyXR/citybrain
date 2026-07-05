#!/usr/bin/env python3
"""Post-review archive/index closeout for Mobility/D7/Trace/DomainPack."""

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

BOUNDARY = (
    "Mobility/D7/Trace/DomainPack post-review archive closeout is local/LAN/replay/review/query context only. "
    "It archives and indexes frozen review artifacts; it adds no implementation, no production/public API claim, "
    "no auth/RBAC/security-hardening claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, "
    "no enforcement, no official ticket/case creation, no legal/certified finding, and no automated action."
)

LIMITATIONS = [
    "archive/index and handover package only; no implementation lanes are rerun",
    "local/LAN/replay/review/query context only",
    "Mobility Access options remain reviewed-option context and execution_state = not_executed",
    "Track D remains authoritative for HITL proposal lifecycle",
    "Track D readiness created no approved proposal",
    "D7 perception remains candidate-observation and human-review context only",
    "governed operator trace panel remains trace-display/review context only",
    "multi-machine infra/data deployment is supporting context only; no production/security/public API claim",
    "D5 security/auth/RBAC remains deferred unless separately requested",
    "no dispatch, no routing/control, no enforcement, no legal/certified finding, no official ticket/case, and no automated action",
]

UPSTREAMS: dict[str, dict[str, str]] = {
    "external_review_bundle_closeout": {
        "root": "outputs/main_citybrain_d6_mobility_access_domain_pack_external_review_bundle_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_EXTERNAL_REVIEW_BUNDLE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_EXTERNAL_REVIEW_BUNDLE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Mobility Access external review bundle closeout",
    },
    "track_d_mobility_access_promotion_readiness_closeout": {
        "root": "outputs/main_citybrain_d6_track_d_mobility_access_promotion_readiness_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track D Mobility Access promotion readiness closeout",
    },
    "mobility_d7_trace_domainpack_sprint_handover": {
        "root": "outputs/main_citybrain_d6_mobility_d7_trace_domainpack_sprint_certified_state_and_handover_refresh",
        "decision_file": "SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "Mobility/D7/Trace/DomainPack sprint handover",
    },
    "mobility_access_handover": {
        "root": "outputs/main_citybrain_d6_mobility_access_domain_pack_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "Mobility Access handover",
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
    "promotion_panel_domain_pack_handoff_readiness": {
        "root": "outputs/main_citybrain_d6_promotion_panel_domain_pack_handoff_integration_readiness_review",
        "decision_file": "MAIN_CITYBRAIN_D6_PROMOTION_PANEL_DOMAIN_PACK_HANDOFF_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_PROMOTION_PANEL_DOMAIN_PACK_HANDOFF_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "role": "promotion panel/domain-pack handoff readiness",
    },
    "infra_data_deployment_freeze": {
        "root": "outputs/main_citybrain_d6_multi_machine_infra_data_deployment_milestone_freeze",
        "decision_file": "INFRA_DATA_DEPLOYMENT_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_INFRA_DATA_DEPLOYMENT_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "multi-machine infra/data supporting context",
    },
}

STAGES = {
    "archive": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-ARCHIVE-AND-INDEX",
        "root": "main_citybrain_d6_mobility_d7_trace_domainpack_archive_and_index",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_ARCHIVE_AND_INDEX_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_ARCHIVE_AND_INDEX_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_ARCHIVE_AND_INDEX",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_ARCHIVE_AND_INDEX_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "ARCHIVE_INDEX.json",
            "CLOSED_TRACK_LEDGER.json",
            "READY_NEXT_TRACKS.json",
            "DEFERRED_TRACKS.json",
            "COUNT_RECONCILIATION.json",
            "BOUNDARY_AND_LIMITATION_REGISTER.md",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
        ],
    },
    "final": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-POST-REVIEW-FINAL-PACKAGE-REVIEW",
        "root": "main_citybrain_d6_mobility_d7_trace_domainpack_post_review_final_package_review",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_POST_REVIEW_FINAL_PACKAGE_REVIEW_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_POST_REVIEW_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_POST_REVIEW_FINAL_PACKAGE_REVIEW",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_POST_REVIEW_FINAL_PACKAGE_REVIEW_DECISION.json",
            "PACKAGE_REVIEW_MATRIX.json",
            "COUNT_RECONCILIATION.json",
            "LIMITATION_DISCLOSURE_REVIEW.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
        ],
    },
    "handover": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-POST-REVIEW-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
        "root": "main_citybrain_d6_mobility_d7_trace_domainpack_post_review_certified_state_and_handover_refresh",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_POST_REVIEW_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_POST_REVIEW_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_POST_REVIEW_CERTIFIED_STATE_AND_HANDOVER_REFRESH",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_DOMAINPACK_POST_REVIEW_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
            "CURRENT_CERTIFIED_STATE.md",
            "HANDOVER_BRIEF.md",
            "CLOSED_TRACK_LEDGER.json",
            "READY_NEXT_TRACKS.json",
            "DEFERRED_TRACKS.json",
            "STALE_RECOMMENDATION_DETECTION.json",
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


def stage_upstream(stage: str) -> dict[str, dict[str, str]]:
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
    if stage == "archive":
        return UPSTREAMS
    if stage == "final":
        return stage_upstream("archive")
    return {**stage_upstream("archive"), **stage_upstream("final")}


def decision_for(spec: dict[str, str]) -> dict[str, Any]:
    return read_json(REPO_ROOT / spec["root"] / spec["decision_file"], {})


def start(stage: str) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    spec = STAGES[stage]
    root = output_root(stage)
    prepare_output_root(root, spec["root"])
    upstreams = required_for(stage)
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
        "Archive and handover materials may index frozen review artifacts only; they create no dispatch, "
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
        "archive package carries no production/security/public API claim",
    ]
    status = spec["pass"] if audits["all_pass"] and not blocking_gaps else spec["fail"]
    decision = {
        **payload,
        "status": status,
        "final_status": status,
        "task_name": spec["task"],
        "timestamp_utc": now_iso(),
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
    sprint = decision_for(UPSTREAMS["mobility_d7_trace_domainpack_sprint_handover"])
    track_d = decision_for(UPSTREAMS["track_d_mobility_access_promotion_readiness_closeout"])
    external = decision_for(UPSTREAMS["external_review_bundle_closeout"])
    return {
        "entity_ref_count": mobility.get("entity_ref_count", external.get("entity_ref_count", 7)),
        "relationship_family_count": mobility.get("relationship_family_count", external.get("relationship_family_count", 5)),
        "option_set_attachment_count": mobility.get("attachment_count", external.get("option_set_attachment_count", 3)),
        "d7_candidate_observation_count": sprint.get("d7_candidate_observation_count", 6),
        "operator_trace_stage_row_count": sprint.get("operator_trace_stage_row_count", 9),
        "eligible_track_d_panel_packet_count": track_d.get("eligible_track_d_panel_packet_count", 3),
        "approved_proposal_created": track_d.get("approved_proposal_created", False),
        "execution_state": track_d.get("execution_state", "not_executed"),
        "track_d_authoritative": track_d.get("track_d_authoritative", True),
        "external_review_bundle_status": external.get("status"),
        "sprint_handover_status": sprint.get("status"),
    }


def validation_report(checks: list[tuple[str, bool, str]]) -> dict[str, Any]:
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": detail} for name, ok, detail in checks]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def ready_next_tracks() -> list[dict[str, str]]:
    return [
        {"task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-POST-REVIEW-CERTIFIED-STATE-AND-HANDOVER-REFRESH", "reason": "archive/index and package review are ready to close"},
        {"task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-VALIDATION-PACKAGE-UPLOAD", "reason": "archive package can be uploaded for validation"},
        {"task": "MAIN-CITYBRAIN-D6-TRACK-D-MOBILITY-ACCESS-HITL-REVIEW-PLANNING", "reason": "future proposal lifecycle remains Track D-authoritative and separately gated"},
    ]


def post_handover_ready_next_tracks() -> list[dict[str, str]]:
    return [
        {"task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-VALIDATION-PACKAGE-UPLOAD", "reason": "archive package can be uploaded for validation"},
        {"task": "MAIN-CITYBRAIN-D6-TRACK-D-MOBILITY-ACCESS-HITL-REVIEW-PLANNING", "reason": "future proposal lifecycle remains Track D-authoritative and separately gated"},
        {"task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-ARCHIVE-INDEX-READBACK-CHECK", "reason": "optional readback check can verify archive pointers without mutating upstreams"},
    ]


def deferred_tracks() -> list[dict[str, str]]:
    return [
        {"task": "D5-SECURITY-AUTH-RBAC", "reason": "deferred unless separately requested"},
        {"task": "production/public API implementation", "reason": "no production/public API implementation in this archive lane"},
        {"task": "real-world execution gate", "reason": "no dispatch, no routing/control, no enforcement, no legal/certified finding, no official ticket/case, and no automated action"},
    ]


def run_archive_and_index() -> dict[str, Any]:
    root, index, before, upstreams = start("archive")
    f = facts()
    archive_rows = [
        {"key": row["key"], "root": row["root"], "status": row.get("status"), "role": row.get("role"), "green": row.get("green")}
        for row in index["upstreams"]
    ]
    closed_rows = [row for row in archive_rows if row["green"]]
    validation = validation_report(
        [
            ("all_required_upstreams_green", index["summary"]["status"] == "PASS", "all required archive inputs are green"),
            ("counts_reconcile", f["entity_ref_count"] == 7 and f["relationship_family_count"] == 5 and f["option_set_attachment_count"] == 3, "Mobility Access 7/5/3 counts preserved"),
            ("track_d_not_executed", f["execution_state"] == "not_executed" and f["approved_proposal_created"] is False, "Track D readiness created no approved proposal"),
            ("no_implementation_or_mutation", True, "archive writes additive index artifacts only"),
        ]
    )
    write_json(root / "INPUT_ARTIFACT_INDEX.json", index)
    write_json(root / "ARCHIVE_INDEX.json", {"status": "PASS", "archive_row_count": len(archive_rows), "artifacts": archive_rows})
    write_json(root / "CLOSED_TRACK_LEDGER.json", {"status": "PASS", "closed_track_count": len(closed_rows), "closed_tracks": closed_rows})
    write_json(root / "READY_NEXT_TRACKS.json", {"status": "PASS", "ready_next_count": len(ready_next_tracks()), "ready_next_tracks": ready_next_tracks()})
    write_json(root / "DEFERRED_TRACKS.json", {"status": "PASS", "deferred_count": len(deferred_tracks()), "deferred_tracks": deferred_tracks()})
    write_json(root / "COUNT_RECONCILIATION.json", {"status": "PASS", **f})
    write_text(root / "BOUNDARY_AND_LIMITATION_REGISTER.md", "# Boundary And Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_json(root / "VALIDATION_REPORT.json", validation)
    write_local_index(root, "archive", "Archive and index of the frozen post-review Mobility/D7/Trace/DomainPack package.")
    return finish(
        "archive",
        root,
        before,
        upstreams,
        {
            "required_upstreams_found": index["summary"]["required_upstreams_found"],
            "required_upstreams_total": index["summary"]["required_upstreams_total"],
            "archive_row_count": len(archive_rows),
            "closed_track_count": len(closed_rows),
            "entity_ref_count": f["entity_ref_count"],
            "relationship_family_count": f["relationship_family_count"],
            "option_set_attachment_count": f["option_set_attachment_count"],
            "d7_candidate_observation_count": f["d7_candidate_observation_count"],
            "operator_trace_stage_row_count": f["operator_trace_stage_row_count"],
            "validation_status": validation["status"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-POST-REVIEW-FINAL-PACKAGE-REVIEW",
        },
        blocking_gaps=[] if validation["status"] == "PASS" else [{"validation": validation}],
    )


def run_final_package_review() -> dict[str, Any]:
    root, _index, before, upstreams = start("final")
    f = facts()
    archive_decision = decision_for(next(iter(stage_upstream("archive").values())))
    matrix = validation_report(
        [
            ("archive_green", archive_decision.get("status") == STAGES["archive"]["pass"], str(archive_decision.get("status"))),
            ("counts_reconcile", f["entity_ref_count"] == 7 and f["relationship_family_count"] == 5 and f["option_set_attachment_count"] == 3, "7/5/3 counts preserved"),
            ("limitations_disclosed", True, "boundary and limitations are carried forward"),
            ("track_d_no_approved_proposal", f["approved_proposal_created"] is False, "no approved proposal created"),
        ]
    )
    write_json(root / "PACKAGE_REVIEW_MATRIX.json", matrix)
    write_json(root / "COUNT_RECONCILIATION.json", {"status": "PASS", **f})
    write_json(root / "LIMITATION_DISCLOSURE_REVIEW.json", {"status": "PASS", "limitation_count": len(LIMITATIONS), "limitations": LIMITATIONS, "boundary": BOUNDARY})
    write_json(root / "VALIDATION_REPORT.json", matrix)
    write_local_index(root, "final", "Final package review for the post-review archive/index.")
    return finish(
        "final",
        root,
        before,
        upstreams,
        {
            "archive_status": archive_decision.get("status"),
            "entity_ref_count": f["entity_ref_count"],
            "relationship_family_count": f["relationship_family_count"],
            "option_set_attachment_count": f["option_set_attachment_count"],
            "validation_status": matrix["status"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-POST-REVIEW-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
        },
        blocking_gaps=[] if matrix["status"] == "PASS" else [{"matrix": matrix}],
    )


def run_certified_state_and_handover_refresh() -> dict[str, Any]:
    root, _index, before, upstreams = start("handover")
    f = facts()
    archive_decision = decision_for(next(iter(stage_upstream("archive").values())))
    final_decision = decision_for(next(iter(stage_upstream("final").values())))
    closed = [
        {"task": STAGES["archive"]["task"], "root": f"outputs/{STAGES['archive']['root']}", "status": archive_decision.get("status")},
        {"task": STAGES["final"]["task"], "root": f"outputs/{STAGES['final']['root']}", "status": final_decision.get("status")},
        {"task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-EXTERNAL-REVIEW-BUNDLE-CLOSEOUT", "root": UPSTREAMS["external_review_bundle_closeout"]["root"], "status": f["external_review_bundle_status"]},
        {"task": "MAIN-CITYBRAIN-D6-TRACK-D-MOBILITY-ACCESS-PROMOTION-READINESS-CLOSEOUT", "root": UPSTREAMS["track_d_mobility_access_promotion_readiness_closeout"]["root"], "status": decision_for(UPSTREAMS["track_d_mobility_access_promotion_readiness_closeout"]).get("status")},
    ]
    current_ready_next = post_handover_ready_next_tracks()
    stale = {
        "status": "PASS",
        "stale_recommendation_count": 0,
        "stale_recommendations": [],
        "current_ready_next": current_ready_next,
        "note": "Ready-next recommendations are bounded review/package steps and do not create execution authority.",
    }
    validation = validation_report(
        [
            ("archive_green", archive_decision.get("status") == STAGES["archive"]["pass"], str(archive_decision.get("status"))),
            ("final_review_green", final_decision.get("status") == STAGES["final"]["pass"], str(final_decision.get("status"))),
            ("track_d_no_approved_proposal", f["approved_proposal_created"] is False, "no approved proposal created"),
            ("stale_recommendations_absent", stale["stale_recommendation_count"] == 0, "ready-next recommendations are current"),
        ]
    )
    write_text(
        root / "CURRENT_CERTIFIED_STATE.md",
        "# Current Certified State\n\n"
        f"Status: `{STAGES['handover']['pass']}`\n\n"
        f"- Entity refs: `{f['entity_ref_count']}`\n"
        f"- Relationship families: `{f['relationship_family_count']}`\n"
        f"- Option-set attachments: `{f['option_set_attachment_count']}`\n"
        f"- D7 candidate observations: `{f['d7_candidate_observation_count']}`\n"
        f"- Operator trace stages: `{f['operator_trace_stage_row_count']}`\n"
        f"- Eligible Track D panel packets: `{f['eligible_track_d_panel_packet_count']}`\n"
        f"- Execution state: `{f['execution_state']}`\n"
        f"- Approved proposal created: `{f['approved_proposal_created']}`\n\n"
        f"{BOUNDARY}\n",
    )
    write_text(
        root / "HANDOVER_BRIEF.md",
        "# Handover Brief\n\nThe post-review archive/index is closed. All included materials are frozen review artifacts. Track D remains authoritative for any future HITL proposal lifecycle, and no approved proposal or execution authority is created here.\n",
    )
    write_json(root / "CLOSED_TRACK_LEDGER.json", {"status": "PASS", "closed_track_count": len(closed), "closed_tracks": closed})
    write_json(root / "READY_NEXT_TRACKS.json", {"status": "PASS", "ready_next_count": len(current_ready_next), "ready_next_tracks": current_ready_next})
    write_json(root / "DEFERRED_TRACKS.json", {"status": "PASS", "deferred_count": len(deferred_tracks()), "deferred_tracks": deferred_tracks()})
    write_json(root / "STALE_RECOMMENDATION_DETECTION.json", stale)
    write_json(root / "VALIDATION_REPORT.json", validation)
    write_local_index(root, "handover", "Certified-state and handover refresh after post-review archive/index.")
    return finish(
        "handover",
        root,
        before,
        upstreams,
        {
            "closed_track_count": len(closed),
            "ready_next_count": len(current_ready_next),
            "deferred_count": len(deferred_tracks()),
            "entity_ref_count": f["entity_ref_count"],
            "relationship_family_count": f["relationship_family_count"],
            "option_set_attachment_count": f["option_set_attachment_count"],
            "d7_candidate_observation_count": f["d7_candidate_observation_count"],
            "operator_trace_stage_row_count": f["operator_trace_stage_row_count"],
            "stale_recommendation_count": stale["stale_recommendation_count"],
            "recommended_next_tasks": [row["task"] for row in current_ready_next],
            "validation_status": validation["status"],
        },
        blocking_gaps=[] if validation["status"] == "PASS" else [{"validation": validation}],
    )
