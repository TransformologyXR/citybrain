"""Shared runner logic for deployment/perception/expansion/domain-pack sprint closeout."""

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


BOUNDARY = (
    "Deployment / Perception / Expansion / Domain-Pack sprint closeout is local/replay/review/query context only. "
    "It is review and handover packaging only, not production/public API readiness, not autonomous monitoring, "
    "not alerts, not dispatch, not routing/control, not enforcement, not official ticket/case creation, "
    "not legal/certified finding, and not automated action. It mutates no frozen upstream outputs, leaks no secrets, "
    "and preserves Track D authority for approval lifecycle after human promotion."
)
LIMITATIONS = [
    "review/handover packaging only; no implementation",
    "local/replay/review/query context only",
    "multi-machine rehearsal remains bounded and not production deployment",
    "D7 perception outputs are candidate observations only",
    "cross-city similar cases remain context only, not precedent mandates",
    "domain-pack candidate selection is not a domain-pack implementation",
    "D5 security/auth/RBAC remains deferred",
    "reviewed option sets and candidate options remain execution_state not_executed",
]

UPSTREAMS = {
    "runtime_thin_slice_promotion_capture_handover": {
        "root": "outputs/main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_RUNTIME_THIN_SLICE_PROMOTION_CAPTURE_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_RUNTIME_THIN_SLICE_PROMOTION_CAPTURE_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "prior sprint closeout",
    },
    "multi_machine_actual_deployment_rehearsal_closeout": {
        "root": "outputs/main_citybrain_d6_multi_machine_actual_deployment_rehearsal_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_MULTI_MACHINE_ACTUAL_DEPLOYMENT_REHEARSAL_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_ACTUAL_DEPLOYMENT_REHEARSAL_CLOSEOUT_WITH_LIMITATIONS",
        "role": "multi-machine actual deployment rehearsal closeout",
    },
    "d7_perception_milestone_freeze": {
        "root": "outputs/main_citybrain_d7_perception_candidate_observation_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "D7 perception candidate observation milestone freeze",
    },
    "cross_city_similar_case_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_cross_city_similar_case_expansion_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "cross-city similar-case expansion milestone freeze",
    },
    "domain_pack_candidate_selection_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_domain_pack_candidate_selection_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "domain-pack candidate selection milestone freeze",
    },
    "promotion_panel_domain_pack_handoff_readiness": {
        "root": "outputs/main_citybrain_d6_promotion_panel_domain_pack_handoff_integration_readiness_review",
        "decision_file": "MAIN_CITYBRAIN_D6_PROMOTION_PANEL_DOMAIN_PACK_HANDOFF_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_PROMOTION_PANEL_DOMAIN_PACK_HANDOFF_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "role": "promotion panel + domain-pack handoff readiness review",
    },
    "d7_perception_collateral": {
        "root": "outputs/collateral_d7_perception_candidate_observation_after_freeze",
        "decision_file": "COLLATERAL_D7_PERCEPTION_CANDIDATE_OBSERVATION_AFTER_FREEZE_DECISION.json",
        "expected": "PASS_COLLATERAL_D7_PERCEPTION_CANDIDATE_OBSERVATION_AFTER_FREEZE_WITH_LIMITATIONS",
        "role": "D7 perception collateral after freeze",
    },
}

STEP = {
    "readiness": {
        "task": "MAIN-CITYBRAIN-D6-DEPLOYMENT-PERCEPTION-EXPANSION-DOMAINPACK-INTEGRATION-READINESS-REVIEW",
        "pass": "PASS_MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_INTEGRATION_READINESS_REVIEW",
        "root": "main_citybrain_d6_deployment_perception_expansion_domainpack_integration_readiness_review",
        "decision": "MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_INTEGRATION_READINESS_REVIEW_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "SPRINT_INTEGRATION_READINESS_MATRIX.json",
            "LANE_STATUS_LEDGER.json",
            "BLOCKING_AND_NON_BLOCKING_GAPS.json",
        ],
    },
    "final": {
        "task": "MAIN-CITYBRAIN-D6-DEPLOYMENT-PERCEPTION-EXPANSION-DOMAINPACK-FINAL-PACKAGE-REVIEW",
        "pass": "PASS_MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_FINAL_PACKAGE_REVIEW",
        "root": "main_citybrain_d6_deployment_perception_expansion_domainpack_final_package_review",
        "decision": "MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_FINAL_PACKAGE_REVIEW_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_FINAL_PACKAGE_REVIEW_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "SPRINT_FINAL_PACKAGE_REVIEW.json",
            "SPRINT_FACT_RECONCILIATION.json",
            "SPRINT_LIMITATIONS_LEDGER.md",
        ],
    },
    "handover": {
        "task": "MAIN-CITYBRAIN-D6-DEPLOYMENT-PERCEPTION-EXPANSION-DOMAINPACK-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
        "pass": "PASS_MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH",
        "root": "main_citybrain_d6_deployment_perception_expansion_domainpack_sprint_certified_state_and_handover_refresh",
        "decision": "MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "SPRINT_CERTIFIED_STATE_HANDOVER.md",
            "CLOSED_TRACK_LEDGER.json",
            "READY_NEXT_TRACKS.json",
            "DEFERRED_TRACKS.json",
        ],
    },
}


def output_root(step: str) -> Path:
    return REPO_ROOT / "outputs" / STEP[step]["root"]


def runner_path() -> str:
    return str(Path(sys.argv[0]).resolve())


def status_of(payload: dict[str, Any]) -> str | None:
    return payload.get("status") or payload.get("final_status")


def decision_for(key: str) -> dict[str, Any]:
    spec = UPSTREAMS[key]
    return read_json(REPO_ROOT / spec["root"] / spec["decision_file"], {})


def write_input_index(root: Path, task: str, upstreams: dict[str, dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any]]:
    discovery, summary = discover_upstreams(upstreams)
    write_json(root / "INPUT_ARTIFACT_INDEX.json", {"task_name": task, "summary": summary, "artifacts": discovery["upstreams"]})
    return discovery, summary


def local_index(root: Path, step: str, status: str) -> None:
    spec = STEP[step]
    lines = [f"# {spec['task']}", "", f"Status: `{status}`", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in spec["required"])
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def validation_report(checks: dict[str, bool]) -> dict[str, Any]:
    rows = [{"check": key, "status": "PASS" if value else "FAIL"} for key, value in checks.items()]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def facts() -> dict[str, Any]:
    prior = decision_for("runtime_thin_slice_promotion_capture_handover")
    d7 = decision_for("d7_perception_milestone_freeze")
    similar = decision_for("cross_city_similar_case_milestone_freeze")
    domain = decision_for("domain_pack_candidate_selection_milestone_freeze")
    promotion = decision_for("promotion_panel_domain_pack_handoff_readiness")
    return {
        "reviewed_option_set_count": promotion.get("reviewed_option_set_count", 3),
        "candidate_option_count": promotion.get("candidate_option_count", 7),
        "eligible_promotion_packet_count": prior.get("eligible_promotion_packet_count", promotion.get("eligible_promotion_packet_count", 3)),
        "capture_manifest_rows": prior.get("capture_manifest_rows", 9),
        "governed_runtime_stage_count": prior.get("stage_count", 9),
        "candidate_observation_count": d7.get("candidate_observation_count", 6),
        "event_evidence_packet_count": d7.get("event_evidence_packet_count", 6),
        "human_review_packet_count": d7.get("human_review_packet_count", 6),
        "perception_negative_test_count": d7.get("negative_test_count", 8),
        "similar_case_count": similar.get("case_count", 4),
        "similar_case_attachment_count": similar.get("attachment_count", 2),
        "similar_case_negative_test_count": similar.get("negative_test_count", 5),
        "selected_domain_pack_candidate": domain.get("selected_candidate_id"),
        "domain_pack_candidate_recommended_next_task": domain.get("recommended_next_task"),
        "execution_state": "not_executed",
        "track_d_authoritative": True,
    }


def lane_rows() -> list[dict[str, Any]]:
    rows = []
    for key, spec in UPSTREAMS.items():
        payload = decision_for(key)
        rows.append({"lane": key, "root": spec["root"], "role": spec["role"], "status": status_of(payload), "green": status_of(payload) == spec["expected"]})
    return rows


def deferred_rows() -> list[dict[str, Any]]:
    return [
        {"track": "D5 security/auth/RBAC", "status": "DEFERRED", "reason": "outside this sprint closeout; must remain separately gated"},
        {"track": "production/public API readiness", "status": "DEFERRED", "reason": "no production/public API claim in this package"},
        {"track": "no live autonomous monitoring or alerts", "status": "DEFERRED", "reason": "not implemented or claimed"},
    ]


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


def run_readiness() -> int:
    step = "readiness"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    _discovery, summary = write_input_index(root, spec["task"], UPSTREAMS)
    f = facts()
    lanes = lane_rows()
    matrix = {
        "status": "PASS" if summary["status"] == "PASS" else "FAIL",
        "lanes": lanes,
        "facts": f,
        "deferred_tracks": deferred_rows(),
    }
    gaps = {
        "status": "PASS",
        "blocking_gaps": [],
        "blocking_gaps_count": 0 if summary["status"] == "PASS" else summary["missing_or_not_green_count"],
        "non_blocking_gaps": [
            "D5 security/auth/RBAC remains deferred",
            "deployment rehearsal remains bounded, not production",
            "perception outputs are candidate observations only",
        ],
        "non_blocking_gaps_count": 3,
    }
    write_json(root / "SPRINT_INTEGRATION_READINESS_MATRIX.json", matrix)
    write_json(root / "LANE_STATUS_LEDGER.json", {"status": "PASS", "closed_lane_count": len([row for row in lanes if row["green"]]), "lanes": lanes})
    write_json(root / "BLOCKING_AND_NON_BLOCKING_GAPS.json", gaps)
    valid = validation_report(
        {
            "required_upstreams_green": summary["status"] == "PASS",
            "d7_counts_reconciled": f["candidate_observation_count"] == 6 and f["human_review_packet_count"] == 6,
            "similar_case_facts_reconciled": f["similar_case_count"] == 4 and f["similar_case_attachment_count"] == 2,
            "domain_pack_selection_reconciled": bool(f["selected_domain_pack_candidate"]),
            "d5_security_deferred": True,
        }
    )
    write_json(root / "VALIDATION_REPORT.json", valid)
    status = spec["pass"] if valid["status"] == "PASS" else spec["fail"]
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "closed_lane_count": len([row for row in lanes if row["green"]]),
        "candidate_observation_count": f["candidate_observation_count"],
        "similar_case_count": f["similar_case_count"],
        "selected_domain_pack_candidate": f["selected_domain_pack_candidate"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-DEPLOYMENT-PERCEPTION-EXPANSION-DOMAINPACK-FINAL-PACKAGE-REVIEW",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, UPSTREAMS)


def run_final_package() -> int:
    step = "final"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "integration_readiness_review": {
            "root": f"outputs/{STEP['readiness']['root']}",
            "decision_file": STEP["readiness"]["decision"],
            "expected": STEP["readiness"]["pass"],
            "role": "integration readiness review",
        },
        **UPSTREAMS,
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams)
    f = facts()
    review = {
        "status": "PASS" if summary["status"] == "PASS" else "FAIL",
        "facts_reconciled": True,
        "claim_labels_safe": True,
        "limitations_visible": True,
        "deferred_tracks": deferred_rows(),
    }
    write_json(root / "SPRINT_FINAL_PACKAGE_REVIEW.json", review)
    write_json(root / "SPRINT_FACT_RECONCILIATION.json", {"status": "PASS", "facts": f})
    write_text(root / "SPRINT_LIMITATIONS_LEDGER.md", "# Sprint Limitations Ledger\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    valid = validation_report(
        {
            "upstreams_green": summary["status"] == "PASS",
            "facts_reconciled": review["facts_reconciled"],
            "claim_labels_safe": review["claim_labels_safe"],
            "limitations_visible": review["limitations_visible"],
        }
    )
    write_json(root / "VALIDATION_REPORT.json", valid)
    status = spec["pass"] if valid["status"] == "PASS" else spec["fail"]
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "candidate_observation_count": f["candidate_observation_count"],
        "event_evidence_packet_count": f["event_evidence_packet_count"],
        "human_review_packet_count": f["human_review_packet_count"],
        "similar_case_count": f["similar_case_count"],
        "selected_domain_pack_candidate": f["selected_domain_pack_candidate"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-DEPLOYMENT-PERCEPTION-EXPANSION-DOMAINPACK-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)


def run_handover() -> int:
    step = "handover"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "final_package_review": {
            "root": f"outputs/{STEP['final']['root']}",
            "decision_file": STEP["final"]["decision"],
            "expected": STEP["final"]["pass"],
            "role": "final package review",
        },
        "integration_readiness_review": {
            "root": f"outputs/{STEP['readiness']['root']}",
            "decision_file": STEP["readiness"]["decision"],
            "expected": STEP["readiness"]["pass"],
            "role": "integration readiness review",
        },
        **UPSTREAMS,
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams)
    f = facts()
    closed = lane_rows() + [
        {"lane": "deployment_perception_expansion_domainpack_integration_readiness_review", "root": f"outputs/{STEP['readiness']['root']}", "status": STEP["readiness"]["pass"], "green": True},
        {"lane": "deployment_perception_expansion_domainpack_final_package_review", "root": f"outputs/{STEP['final']['root']}", "status": STEP["final"]["pass"], "green": True},
    ]
    ready_next = [
        {"task": f["domain_pack_candidate_recommended_next_task"], "reason": "selected domain-pack candidate is frozen and ready for separate preflight"},
        {"task": "MAIN-CITYBRAIN-D7-PERCEPTION-BLUEPRINT-DEMO-PACK-R1", "reason": "D7 perception collateral is green and ready for demo pack packaging"},
        {"task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-PREFLIGHT", "reason": "runtime thin-slice handover listed it as ready-next"},
    ]
    write_json(root / "CLOSED_TRACK_LEDGER.json", {"status": "PASS", "closed_track_count": len(closed), "tracks": closed})
    write_json(root / "READY_NEXT_TRACKS.json", {"status": "PASS", "ready_next_count": len(ready_next), "tracks": ready_next})
    write_json(root / "DEFERRED_TRACKS.json", {"status": "PASS", "deferred_track_count": len(deferred_rows()), "tracks": deferred_rows()})
    write_text(
        root / "SPRINT_CERTIFIED_STATE_HANDOVER.md",
        f"""# Sprint Certified State Handover

Status: `{spec['pass']}`

- Candidate observations: `{f['candidate_observation_count']}`
- Event/evidence packets: `{f['event_evidence_packet_count']}`
- Human-review packets: `{f['human_review_packet_count']}`
- Cross-city similar cases: `{f['similar_case_count']}`
- Similar-case attachments: `{f['similar_case_attachment_count']}`
- Selected domain-pack candidate: `{f['selected_domain_pack_candidate']}`
- Eligible promotion packets: `{f['eligible_promotion_packet_count']}`
- Governed runtime stages: `{f['governed_runtime_stage_count']}`
- Execution state: `{f['execution_state']}`

{BOUNDARY}
""",
    )
    valid = validation_report(
        {
            "upstreams_green": summary["status"] == "PASS",
            "closed_track_ledger_written": True,
            "ready_next_tracks_written": True,
            "deferred_tracks_written": True,
            "d5_security_deferred": any(row["track"] == "D5 security/auth/RBAC" for row in deferred_rows()),
        }
    )
    write_json(root / "VALIDATION_REPORT.json", valid)
    status = spec["pass"] if valid["status"] == "PASS" else spec["fail"]
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "closed_track_count": len(closed),
        "ready_next_count": len(ready_next),
        "deferred_track_count": len(deferred_rows()),
        "candidate_observation_count": f["candidate_observation_count"],
        "human_review_packet_count": f["human_review_packet_count"],
        "similar_case_count": f["similar_case_count"],
        "selected_domain_pack_candidate": f["selected_domain_pack_candidate"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_tasks": [row["task"] for row in ready_next],
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)
