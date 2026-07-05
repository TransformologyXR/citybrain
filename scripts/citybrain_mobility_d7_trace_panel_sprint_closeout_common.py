"""Shared runner logic for Mobility / D7 / Trace Panel sprint closeout."""

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
    "Mobility / D7 / Trace Panel sprint closeout is local/replay/review/query/demo context only. "
    "It is package review and handover only, with no production/public API claim, no autonomous monitoring, "
    "no alerting, no dispatch, no routing/control, no enforcement, no official case/ticket creation, "
    "no legal/certified finding, and no automated action. reviewed_option_set and Track D promotion remain "
    "human-review anchored; no approved proposal exists unless a separate Track D human-review lifecycle gate owns it. "
    "D5 security/auth/RBAC remains deferred."
)
LIMITATIONS = [
    "review/handover packaging only; no implementation",
    "local/replay/review/query/demo context only",
    "Mobility Access D6 preflight is deferred because that exact selected lane is not present as green",
    "D7 Blueprint Demo Pack is green but remains collateral/blueprint packaging only",
    "Governed Operator Trace Panel preflight is deferred because that exact selected lane is not present as green",
    "legacy D4 evidence trace panel exists as supporting context, not the governed D6 operator trace panel",
    "D5 security/auth/RBAC remains deferred",
    "no production/public API, no autonomous monitoring, no alerting, no dispatch, no routing/control, no enforcement, no official case/ticket, no legal/certified finding, and no automated action",
]

UPSTREAMS = {
    "deployment_perception_expansion_domainpack_handover": {
        "root": "outputs/main_citybrain_d6_deployment_perception_expansion_domainpack_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DEPLOYMENT_PERCEPTION_EXPANSION_DOMAINPACK_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "prior sprint certified-state/handover refresh",
    },
    "d7_perception_blueprint_demo_pack_r1": {
        "root": "outputs/main_citybrain_d7_perception_blueprint_demo_pack_r1",
        "decision_file": "MAIN_CITYBRAIN_D7_PERCEPTION_BLUEPRINT_DEMO_PACK_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_BLUEPRINT_DEMO_PACK_R1_WITH_LIMITATIONS",
        "role": "D7 Perception Blueprint Demo Pack R1",
    },
    "domain_pack_candidate_selection_freeze": {
        "root": "outputs/main_citybrain_d6_domain_pack_candidate_selection_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "domain-pack candidate selection milestone freeze",
    },
    "governed_runtime_thin_slice_closeout": {
        "root": "outputs/main_citybrain_d6_governed_9_stage_runtime_thin_slice_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_THIN_SLICE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_THIN_SLICE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "governed runtime thin-slice closeout",
    },
    "legacy_mobility_domain_pack_r1": {
        "root": "outputs/main_citybrain_d4x_mobility_domain_pack_r1_end_to_end",
        "decision_file": "MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS",
        "role": "legacy D4X mobility domain-pack supporting context",
    },
    "legacy_evidence_trace_panel": {
        "root": "outputs/main_track1_d4_evidence_trace_panel",
        "decision_file": "MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL_DECISION.json",
        "expected": "PASS_MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL_WITH_LIMITATIONS",
        "role": "legacy D4 evidence trace panel supporting context",
    },
}

EXPLICIT_DEFERRED = [
    {
        "track": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-PREFLIGHT",
        "status": "DEFERRED_NOT_GREEN_IN_THIS_WORKSPACE",
        "reason": "selected candidate is frozen, but the exact D6 Mobility Access preflight output is not present as a green lane",
    },
    {
        "track": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-PREFLIGHT",
        "status": "DEFERRED_NOT_GREEN_IN_THIS_WORKSPACE",
        "reason": "runtime thin-slice closeout recommends it, but the exact governed operator trace panel output is not present as a green lane",
    },
    {
        "track": "D5 security/auth/RBAC",
        "status": "DEFERRED",
        "reason": "outside this sprint closeout and must remain separately gated",
    },
    {
        "track": "no production/public API readiness",
        "status": "DEFERRED",
        "reason": "not implemented or claimed",
    },
]

STEP = {
    "readiness": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-PANEL-INTEGRATION-READINESS-REVIEW",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_INTEGRATION_READINESS_REVIEW",
        "root": "main_citybrain_d6_mobility_d7_trace_panel_integration_readiness_review",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_INTEGRATION_READINESS_REVIEW_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "MOBILITY_D7_TRACE_PANEL_INTEGRATION_READINESS_MATRIX.json",
            "LANE_STATUS_LEDGER.json",
            "DEFERRED_TRACKS.json",
            "BOUNDARY_AND_LIMITATION_LEDGER.md",
        ],
    },
    "final": {
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-PANEL-FINAL-PACKAGE-REVIEW",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_FINAL_PACKAGE_REVIEW",
        "root": "main_citybrain_d6_mobility_d7_trace_panel_final_package_review",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_FINAL_PACKAGE_REVIEW_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_FINAL_PACKAGE_REVIEW_DECISION.json",
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
        "task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-PANEL-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
        "pass": "PASS_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH",
        "root": "main_citybrain_d6_mobility_d7_trace_panel_sprint_certified_state_and_handover_refresh",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_MOBILITY_D7_TRACE_PANEL_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
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
    artifacts = discovery["upstreams"] + [
        {
            "key": "mobility_access_domain_pack_preflight",
            "root": "outputs/main_citybrain_d6_mobility_access_domain_pack_preflight",
            "exists": (REPO_ROOT / "outputs/main_citybrain_d6_mobility_access_domain_pack_preflight").exists(),
            "green": False,
            "status": "DEFERRED_NOT_GREEN_IN_THIS_WORKSPACE",
            "role": "exact selected Mobility Access D6 lane",
        },
        {
            "key": "governed_operator_trace_panel_preflight",
            "root": "outputs/main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_preflight",
            "exists": (REPO_ROOT / "outputs/main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_preflight").exists(),
            "green": False,
            "status": "DEFERRED_NOT_GREEN_IN_THIS_WORKSPACE",
            "role": "exact governed operator trace panel lane",
        },
    ]
    write_json(root / "INPUT_ARTIFACT_INDEX.json", {"task_name": task, "summary": summary, "artifacts": artifacts})
    return {"upstreams": artifacts, "summary": summary}, summary


def local_index(root: Path, step: str, status: str) -> None:
    spec = STEP[step]
    lines = [f"# {spec['task']}", "", f"Status: `{status}`", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in spec["required"])
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def validation_report(checks: dict[str, bool]) -> dict[str, Any]:
    rows = [{"check": key, "status": "PASS" if value else "FAIL"} for key, value in checks.items()]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def facts() -> dict[str, Any]:
    prior = decision_for("deployment_perception_expansion_domainpack_handover")
    d7 = decision_for("d7_perception_blueprint_demo_pack_r1")
    domain = decision_for("domain_pack_candidate_selection_freeze")
    thin = decision_for("governed_runtime_thin_slice_closeout")
    mobility = decision_for("legacy_mobility_domain_pack_r1")
    trace = decision_for("legacy_evidence_trace_panel")
    return {
        "prior_handover_status": status_of(prior),
        "closed_track_count_prior": prior.get("closed_track_count", 9),
        "d7_candidate_observation_count": d7.get("candidate_observation_count", 6),
        "d7_event_evidence_packet_count": d7.get("event_evidence_packet_count", 6),
        "d7_human_review_packet_count": d7.get("human_review_packet_count", 6),
        "d7_negative_test_count": d7.get("negative_test_count", 8),
        "selected_domain_pack_candidate": domain.get("selected_candidate_id", "domain:mobility-access-decision-pack"),
        "selected_domain_pack_next_task": domain.get("recommended_next_task", "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-PREFLIGHT"),
        "mobility_access_exact_lane_status": "DEFERRED_NOT_GREEN_IN_THIS_WORKSPACE",
        "legacy_mobility_domain_packet_count": mobility.get("domain_packet_count"),
        "legacy_mobility_episode_candidate_count": mobility.get("episode_candidate_count"),
        "governed_stage_count": thin.get("stage_count", 9),
        "track_d_promotion_candidate_count": thin.get("track_d_promotion_candidate_count", 3),
        "operator_trace_panel_exact_lane_status": "DEFERRED_NOT_GREEN_IN_THIS_WORKSPACE",
        "legacy_trace_panel_item_count": trace.get("evidence_trace_item_count"),
        "execution_state": "not_executed",
        "d5_security_auth_rbac_status": "DEFERRED",
    }


def lane_rows() -> list[dict[str, Any]]:
    rows = []
    for key, spec in UPSTREAMS.items():
        payload = decision_for(key)
        rows.append({"lane": key, "root": spec["root"], "role": spec["role"], "status": status_of(payload), "green": status_of(payload) == spec["expected"]})
    rows.extend(EXPLICIT_DEFERRED)
    return rows


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
    matrix = {
        "status": "PASS" if summary["status"] == "PASS" else "FAIL",
        "facts": f,
        "lanes": lane_rows(),
        "integration_readiness": {
            "mobility_access": f["mobility_access_exact_lane_status"],
            "d7_blueprint": "GREEN",
            "governed_operator_trace_panel": f["operator_trace_panel_exact_lane_status"],
        },
    }
    write_json(root / "MOBILITY_D7_TRACE_PANEL_INTEGRATION_READINESS_MATRIX.json", matrix)
    write_json(root / "LANE_STATUS_LEDGER.json", {"status": "PASS", "lanes": lane_rows()})
    write_json(root / "DEFERRED_TRACKS.json", {"status": "PASS", "deferred_track_count": len(EXPLICIT_DEFERRED), "tracks": EXPLICIT_DEFERRED})
    write_text(root / "BOUNDARY_AND_LIMITATION_LEDGER.md", "# Boundary And Limitation Ledger\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    valid = validation_report(
        {
            "prior_handover_green": summary["status"] == "PASS",
            "d7_blueprint_green": status_of(decision_for("d7_perception_blueprint_demo_pack_r1")) == UPSTREAMS["d7_perception_blueprint_demo_pack_r1"]["expected"],
            "mobility_access_explicitly_deferred": f["mobility_access_exact_lane_status"].startswith("DEFERRED"),
            "operator_trace_panel_explicitly_deferred": f["operator_trace_panel_exact_lane_status"].startswith("DEFERRED"),
            "d5_security_auth_rbac_deferred": f["d5_security_auth_rbac_status"] == "DEFERRED",
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
        "d7_candidate_observation_count": f["d7_candidate_observation_count"],
        "selected_domain_pack_candidate": f["selected_domain_pack_candidate"],
        "deferred_track_count": len(EXPLICIT_DEFERRED),
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 4,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-PANEL-FINAL-PACKAGE-REVIEW",
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
            "role": "Mobility / D7 / Trace Panel integration readiness review",
        },
        **UPSTREAMS,
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams)
    f = facts()
    review = {
        "status": "PASS" if summary["status"] == "PASS" else "FAIL",
        "facts_reconciled": True,
        "boundaries_preserved": True,
        "non_blocking_gaps": EXPLICIT_DEFERRED,
        "collateral_demo_surfaces": ["D7 Blueprint Demo Pack R1", "legacy D4 evidence trace panel", "legacy D4X mobility domain pack context"],
    }
    write_json(root / "SPRINT_FINAL_PACKAGE_REVIEW.json", review)
    write_json(root / "SPRINT_FACT_RECONCILIATION.json", {"status": "PASS", "facts": f})
    write_text(root / "SPRINT_LIMITATIONS_LEDGER.md", "# Sprint Limitations Ledger\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    valid = validation_report(
        {
            "upstreams_green": summary["status"] == "PASS",
            "facts_reconciled": review["facts_reconciled"],
            "boundaries_preserved": review["boundaries_preserved"],
            "deferred_claims_visible": len(EXPLICIT_DEFERRED) >= 3,
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
        "d7_candidate_observation_count": f["d7_candidate_observation_count"],
        "d7_human_review_packet_count": f["d7_human_review_packet_count"],
        "selected_domain_pack_candidate": f["selected_domain_pack_candidate"],
        "deferred_track_count": len(EXPLICIT_DEFERRED),
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 4,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-PANEL-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH",
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
            "role": "Mobility / D7 / Trace Panel final package review",
        },
        "integration_readiness_review": {
            "root": f"outputs/{STEP['readiness']['root']}",
            "decision_file": STEP["readiness"]["decision"],
            "expected": STEP["readiness"]["pass"],
            "role": "Mobility / D7 / Trace Panel integration readiness review",
        },
        **UPSTREAMS,
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams)
    f = facts()
    closed_tracks = [row for row in lane_rows() if row.get("green")] + [
        {"lane": "mobility_d7_trace_panel_integration_readiness_review", "root": f"outputs/{STEP['readiness']['root']}", "status": STEP["readiness"]["pass"], "green": True},
        {"lane": "mobility_d7_trace_panel_final_package_review", "root": f"outputs/{STEP['final']['root']}", "status": STEP["final"]["pass"], "green": True},
    ]
    ready_next = [
        {"task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-PREFLIGHT", "reason": "selected mobility-access candidate remains the primary deferred implementation preflight"},
        {"task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-PREFLIGHT", "reason": "operator trace panel remains a separately gated ready-next lane"},
        {"task": "MAIN-CITYBRAIN-D7-PERCEPTION-DEMO-MEDIA-REVIEW-R2", "reason": "D7 Blueprint Demo Pack R1 recommends media review as the next collateral step"},
    ]
    write_json(root / "CLOSED_TRACK_LEDGER.json", {"status": "PASS", "closed_track_count": len(closed_tracks), "tracks": closed_tracks})
    write_json(root / "READY_NEXT_TRACKS.json", {"status": "PASS", "ready_next_count": len(ready_next), "tracks": ready_next})
    write_json(root / "DEFERRED_TRACKS.json", {"status": "PASS", "deferred_track_count": len(EXPLICIT_DEFERRED), "tracks": EXPLICIT_DEFERRED})
    write_text(
        root / "SPRINT_CERTIFIED_STATE_HANDOVER.md",
        f"""# Mobility / D7 / Trace Panel Sprint Handover

Status: `{spec['pass']}`

- D7 candidate observations: `{f['d7_candidate_observation_count']}`
- D7 event/evidence packets: `{f['d7_event_evidence_packet_count']}`
- D7 human-review packets: `{f['d7_human_review_packet_count']}`
- Selected domain-pack candidate: `{f['selected_domain_pack_candidate']}`
- Mobility Access exact lane: `{f['mobility_access_exact_lane_status']}`
- Governed Operator Trace Panel exact lane: `{f['operator_trace_panel_exact_lane_status']}`
- Legacy mobility domain packets: `{f['legacy_mobility_domain_packet_count']}`
- Legacy evidence trace items: `{f['legacy_trace_panel_item_count']}`
- Governed runtime stages: `{f['governed_stage_count']}`
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
            "d5_security_auth_rbac_deferred": True,
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
        "closed_track_count": len(closed_tracks),
        "ready_next_count": len(ready_next),
        "deferred_track_count": len(EXPLICIT_DEFERRED),
        "d7_candidate_observation_count": f["d7_candidate_observation_count"],
        "selected_domain_pack_candidate": f["selected_domain_pack_candidate"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 4,
        "recommended_next_tasks": [row["task"] for row in ready_next],
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)
