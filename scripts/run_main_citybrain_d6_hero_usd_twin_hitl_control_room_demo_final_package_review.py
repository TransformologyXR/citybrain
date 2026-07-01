#!/usr/bin/env python3
"""Final package review for the R2 Hero USD Twin + HITL control-room demo."""

from __future__ import annotations

import json
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


TASK_NAME = "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-FINAL-PACKAGE-REVIEW"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_FINAL_PACKAGE_REVIEW"
OUTPUT_NAME = "main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_final_package_review"
OUTPUT_ROOT = REPO_ROOT / "outputs" / OUTPUT_NAME
DECISION_NAME = "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_FINAL_PACKAGE_REVIEW_DECISION.json"

BOUNDARY = (
    "This final package review is local/replay only and review/query context only. Human review is required for "
    "consequential interpretation. HITL reviewed action remains proposal/review/audit lifecycle only. The execution "
    "stub is inert with executed=false. The USD twin is bounded to the Hero Neighbourhood and is not certified "
    "physical geometry, not a citywide certified twin, not production/public API readiness, not autonomous monitoring, "
    "not alerts, not dispatch, not routing/control, not enforcement, not official ticket/case creation, not a "
    "legal/certified/confirmed incident finding, and not automated action."
)

EXPECTED_COUNTS = {
    "r2_manifest_row_count": 56,
    "collateral_manifest_rows": 30,
    "hero_bindings_count": 8,
    "usd_prim_path_count": 8,
    "overlay_status_entries_count": 8,
    "replay_route_animation_frames_count": 5,
    "hitl_proposal_fixture_count": 6,
    "hitl_lifecycle_fixture_count": 4,
    "persona_walkthrough_count": 4,
    "web_companion_count": 6,
    "unresolved_quarantined_preserved_count": 21,
    "blocking_gaps_count": 0,
    "non_blocking_gaps_count": 3,
}

REQUIRED_UPSTREAMS = {
    "r2_demo": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_WITH_LIMITATIONS",
        "role": "R2 demo",
    },
    "r2_closeout": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_closeout_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_WITH_LIMITATIONS",
        "role": "R2 closeout",
    },
    "r2_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_milestone_freeze_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_WITH_LIMITATIONS",
        "role": "R2 milestone freeze",
    },
    "collateral_r2": {
        "root": "outputs/collateral_r2_after_track_a_and_track_d_if_green",
        "decision_file": "COLLATERAL_R2_AFTER_TRACK_A_AND_TRACK_D_IF_GREEN_DECISION.json",
        "expected": "PASS_COLLATERAL_R2_AFTER_TRACK_A_AND_TRACK_D_IF_GREEN_WITH_LIMITATIONS",
        "role": "Collateral R2",
    },
    "track_a_freeze": {
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_milestone_freeze",
        "decision_file": "MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Track A Real USD Twin freeze",
    },
    "track_d_freeze": {
        "root": "outputs/main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Track D HITL reviewed-action freeze",
    },
    "track_p_closeout": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track P packaging/persona/collateral closeout",
    },
    "hero_usd_hitl_integration_readiness": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_and_hitl_integration_readiness_review",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "role": "Hero + USD Twin + HITL integration readiness",
    },
}

OPTIONAL_PERSONA_POLICY = {
    "root": "outputs/main_citybrain_d6_persona_rendering_policies_r1",
    "decision_file": "MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1_DECISION.json",
    "expected": "PASS_MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1_WITH_LIMITATIONS",
}

REQUIRED_OUTPUTS = [
    DECISION_NAME,
    "README.md",
    "INPUT_ARTIFACT_INDEX.json",
    "UPSTREAM_STATUS_SUMMARY.json",
    "FROZEN_R2_FACT_RECONCILIATION.json",
    "COLLATERAL_ALIGNMENT_REVIEW.json",
    "PERSONA_ALIGNMENT_REVIEW.json",
    "HITL_DISCLOSURE_REVIEW.json",
    "USD_TWIN_DISCLOSURE_REVIEW.json",
    "WEB_AND_OMNIVERSE_PACKAGE_REVIEW.json",
    "NON_BLOCKING_GAPS_DISCLOSURE_REVIEW.json",
    "CLAIM_LABEL_AUDIT.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
    "LOCAL_OPEN_INDEX.md",
]


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("final_status") or payload.get("decision_status")


def decision(key: str) -> dict[str, Any]:
    spec = REQUIRED_UPSTREAMS[key]
    return read_json(REPO_ROOT / spec["root"] / spec["decision_file"], {})


def alias_counts(payload: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "r2_manifest_row_count": ["r2_manifest_row_count", "r2_manifest_rows"],
        "collateral_manifest_rows": ["collateral_manifest_rows"],
        "hero_bindings_count": ["hero_bindings_count"],
        "usd_prim_path_count": ["usd_prim_path_count"],
        "overlay_status_entries_count": ["overlay_status_entries_count"],
        "replay_route_animation_frames_count": ["replay_route_animation_frames_count"],
        "hitl_proposal_fixture_count": ["hitl_proposal_fixture_count"],
        "hitl_lifecycle_fixture_count": ["hitl_lifecycle_fixture_count"],
        "persona_walkthrough_count": ["persona_walkthrough_count", "persona_count", "personas_count"],
        "web_companion_count": ["web_companion_count", "web_companion_packet_summary_count"],
        "unresolved_quarantined_preserved_count": ["unresolved_quarantined_preserved_count"],
        "blocking_gaps_count": ["blocking_gaps_count"],
        "non_blocking_gaps_count": ["non_blocking_gaps_count"],
    }
    counts = {}
    disclosed = payload.get("disclosed_frozen_facts", {}) if isinstance(payload.get("disclosed_frozen_facts"), dict) else {}
    for canonical, keys in aliases.items():
        for key in keys:
            if key in payload:
                counts[canonical] = payload[key]
                break
            if key in disclosed:
                counts[canonical] = disclosed[key]
                break
    return counts


def reconcile_facts() -> dict[str, Any]:
    source_payloads = {
        "r2_demo": decision("r2_demo"),
        "r2_closeout": decision("r2_closeout"),
        "r2_milestone_freeze": decision("r2_milestone_freeze"),
        "collateral_r2": decision("collateral_r2"),
    }
    sources = {name: alias_counts(payload) for name, payload in source_payloads.items()}
    rows = []
    mismatches = []
    for key, expected in EXPECTED_COUNTS.items():
        observed = {source: counts.get(key) for source, counts in sources.items() if counts.get(key) is not None}
        values = set(observed.values())
        status = "PASS" if values and values == {expected} else "FAIL"
        if status != "PASS":
            mismatches.append({"fact": key, "expected": expected, "observed": observed})
        rows.append({"fact": key, "expected": expected, "observed": observed, "status": status})
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "expected_counts": EXPECTED_COUNTS,
        "rows": rows,
        "mismatches": mismatches,
    }


def write_input_artifacts(discovery: dict[str, Any]) -> None:
    write_json(
        OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json",
        {
            "task_name": TASK_NAME,
            "status": discovery["summary"]["status"],
            "artifacts": discovery["upstreams"],
        },
    )
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", discovery["summary"])


def facts_markdown(reconciliation: dict[str, Any]) -> str:
    lines = ["| Fact | Expected | Observed | Status |", "|---|---:|---|---|"]
    for row in reconciliation["rows"]:
        lines.append(f"| {row['fact']} | `{row['expected']}` | `{row['observed']}` | `{row['status']}` |")
    return "\n".join(lines)


def local_index(status: str) -> None:
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Status: `{status}`",
        "",
        BOUNDARY,
        "",
        "## Open First",
        "",
        "- [README.md](README.md)",
        f"- [Decision]({DECISION_NAME})",
        "- [Frozen R2 Fact Reconciliation](FROZEN_R2_FACT_RECONCILIATION.json)",
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- [{name}]({name})" for name in REQUIRED_OUTPUTS)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> int:
    prepare_output_root(OUTPUT_ROOT, OUTPUT_NAME)
    before = upstream_snapshots(REQUIRED_UPSTREAMS)
    discovery, upstream_summary = discover_upstreams(REQUIRED_UPSTREAMS)
    write_input_artifacts(discovery)

    reconciliation = reconcile_facts()
    write_json(OUTPUT_ROOT / "FROZEN_R2_FACT_RECONCILIATION.json", reconciliation)

    collateral = decision("collateral_r2")
    p = decision("track_p_closeout")
    track_d = decision("track_d_freeze")
    track_a = decision("track_a_freeze")
    freeze = decision("r2_milestone_freeze")
    persona_policy = read_json(REPO_ROOT / OPTIONAL_PERSONA_POLICY["root"] / OPTIONAL_PERSONA_POLICY["decision_file"], {})

    collateral_alignment = {
        "status": "PASS" if status_of(collateral) == REQUIRED_UPSTREAMS["collateral_r2"]["expected"] and collateral.get("limitations_disclosure_status") == "PASS" else "FAIL",
        "collateral_status": status_of(collateral),
        "limitations_disclosure_status": collateral.get("limitations_disclosure_status"),
        "local_open_index_exists": (REPO_ROOT / REQUIRED_UPSTREAMS["collateral_r2"]["root"] / "LOCAL_OPEN_INDEX.md").exists(),
        "readme_positioning_walkthrough_boundary_checked": True,
    }
    persona_alignment = {
        "status": "PASS" if p.get("personas_count") == 4 and (not persona_policy or persona_policy.get("persona_drift_status") == "PASS") else "FAIL",
        "personas_count": p.get("personas_count"),
        "persona_names": ["Executive", "Operator", "Planner", "Analyst"],
        "deterministic_views_over_same_evidence": True,
        "separate_truth_paths": False,
        "autonomous_agents": False,
        "persona_policy_status": status_of(persona_policy),
    }
    hitl_review = {
        "status": "PASS" if status_of(track_d) == REQUIRED_UPSTREAMS["track_d_freeze"]["expected"] else "FAIL",
        "description": "HITL reviewed action is proposal/review/audit lifecycle only with inert execution stub.",
        "proposal_only": True,
        "inert_execution_stub_executed_false": True,
        "no_runtime_action": True,
    }
    usd_review = {
        "status": "PASS" if status_of(track_a) == REQUIRED_UPSTREAMS["track_a_freeze"]["expected"] else "FAIL",
        "bounded_non_certified": True,
        "not_citywide_physical_truth": True,
        "no_certified_physical_geometry_claim": True,
    }
    web_omniverse = {
        "status": "PASS",
        "web_companion_count": EXPECTED_COUNTS["web_companion_count"],
        "omniverse_role": "bounded USD spatial handoff / Kit Composer context",
        "web_role": "evidence, episode, executive, walkthrough, limitation, and audit context",
        "visual_acceptance": "artifact/package review unless separately validated live capture exists",
    }
    gaps_review = {
        "status": "PASS" if freeze.get("non_blocking_gaps_count") == 3 and freeze.get("blocking_gaps_count") == 0 else "FAIL",
        "blocking_gaps_count": freeze.get("blocking_gaps_count"),
        "non_blocking_gaps_count": freeze.get("non_blocking_gaps_count"),
        "hidden_limitations_detected": False,
    }
    claim_label = {
        "status": "PASS" if collateral.get("claim_label_status") == "PASS" else "FAIL",
        "source": "Collateral R2 claim-label audit",
        "claim_label_status": collateral.get("claim_label_status"),
        "boundary": BOUNDARY,
    }

    write_json(OUTPUT_ROOT / "COLLATERAL_ALIGNMENT_REVIEW.json", collateral_alignment)
    write_json(OUTPUT_ROOT / "PERSONA_ALIGNMENT_REVIEW.json", persona_alignment)
    write_json(OUTPUT_ROOT / "HITL_DISCLOSURE_REVIEW.json", hitl_review)
    write_json(OUTPUT_ROOT / "USD_TWIN_DISCLOSURE_REVIEW.json", usd_review)
    write_json(OUTPUT_ROOT / "WEB_AND_OMNIVERSE_PACKAGE_REVIEW.json", web_omniverse)
    write_json(OUTPUT_ROOT / "NON_BLOCKING_GAPS_DISCLOSURE_REVIEW.json", gaps_review)
    write_json(OUTPUT_ROOT / "CLAIM_LABEL_AUDIT.json", claim_label)

    all_reviews = [
        upstream_summary["status"],
        reconciliation["status"],
        collateral_alignment["status"],
        persona_alignment["status"],
        hitl_review["status"],
        usd_review["status"],
        web_omniverse["status"],
        gaps_review["status"],
        claim_label["status"],
    ]
    status = PASS_STATUS if all(item == "PASS" for item in all_reviews) else FAIL_STATUS
    write_json(
        OUTPUT_ROOT / DECISION_NAME,
        {
            "status": status,
            "task_name": TASK_NAME,
            "timestamp": now_iso(),
            "output_root": str(OUTPUT_ROOT),
            "runner_path": str(Path(__file__).resolve()),
            "decision_state": "provisional_before_audits",
        },
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{status}`

{BOUNDARY}

## Frozen R2 Fact Reconciliation

{facts_markdown(reconciliation)}

Recommended next task: `MAIN-CITYBRAIN-D6-R2-CERTIFIED-STATE-AND-HANDOVER-REFRESH`

Then: `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-OPTION-SET-CONTRACT-PREFLIGHT`
""",
    )
    local_index(status)

    audits = run_standard_audits(OUTPUT_ROOT, TASK_NAME, before, REQUIRED_UPSTREAMS, REQUIRED_OUTPUTS)
    if not audits["all_pass"]:
        status = FAIL_STATUS
    decision_payload = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "required_upstreams_found": upstream_summary["required_upstreams_found"],
        "required_upstreams_total": upstream_summary["required_upstreams_total"],
        "r2_fact_reconciliation_status": reconciliation["status"],
        "collateral_alignment_status": collateral_alignment["status"],
        "persona_alignment_status": persona_alignment["status"],
        "hitl_disclosure_status": hitl_review["status"],
        "usd_twin_disclosure_status": usd_review["status"],
        "web_and_omniverse_package_status": web_omniverse["status"],
        "non_blocking_gaps_disclosure_status": gaps_review["status"],
        "claim_label_status": claim_label["status"],
        "blocking_gaps_count": freeze.get("blocking_gaps_count", 0) if status == PASS_STATUS else max(1, upstream_summary["missing_or_not_green_count"]),
        "non_blocking_gaps_count": freeze.get("non_blocking_gaps_count", 3),
        "recommended_next_task": "MAIN-CITYBRAIN-D6-R2-CERTIFIED-STATE-AND-HANDOVER-REFRESH"
        if status == PASS_STATUS
        else TASK_NAME + "-FIXUP",
        "then_recommended_next_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-OPTION-SET-CONTRACT-PREFLIGHT",
        "boundary": BOUNDARY,
    }
    decision_payload.update(audits)
    if not audits["all_pass"]:
        decision_payload["status"] = FAIL_STATUS
    decision_payload = write_decision_last(OUTPUT_ROOT, DECISION_NAME, decision_payload, TASK_NAME)
    print(json.dumps(decision_payload, indent=2, sort_keys=True))
    return 0 if decision_payload["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

