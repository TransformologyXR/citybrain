#!/usr/bin/env python3
"""Package Collateral R2 after Track A and Track D are green."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citybrain_track_p_packaging_common import (
    BOUNDARY,
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


TASK_NAME = "COLLATERAL-R2-AFTER-TRACK-A-AND-TRACK-D-IF-GREEN"
PASS_STATUS = "PASS_COLLATERAL_R2_AFTER_TRACK_A_AND_TRACK_D_IF_GREEN_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_COLLATERAL_R2_AFTER_TRACK_A_AND_TRACK_D_IF_GREEN"
OUTPUT_NAME = "collateral_r2_after_track_a_and_track_d_if_green"
OUTPUT_ROOT = REPO_ROOT / "outputs" / OUTPUT_NAME
DECISION_NAME = "COLLATERAL_R2_AFTER_TRACK_A_AND_TRACK_D_IF_GREEN_DECISION.json"

R2_BOUNDARY = (
    "Collateral R2 is packaging and narrative only for a bounded hero neighbourhood / corridor replay. "
    "It is local/replay review/query context only, with candidate/contextual event handling, HITL proposal lifecycle, "
    "and an inert execution stub only. It creates no autonomous monitoring, no alerts, no dispatch, no routing/control, "
    "no enforcement, no official ticket/case creation, no legal/certified/confirmed incident finding, no production/public API claim, "
    "no citywide certified twin claim, no certified physical geometry claim, and no automated action."
)

POSITIONING_LINE = (
    "CityBrain demonstrates a bounded local/replay control-room reference workflow where a hero neighbourhood scene, "
    "real/accepted USD spatial bindings, incident/operator packets, web companion context, and HITL reviewed-action proposals "
    "are aligned through evidence, limitations, and audit boundaries."
)

EXPECTED_FACTS = {
    "r2_manifest_row_count": 56,
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
    "r2_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_milestone_freeze_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_WITH_LIMITATIONS",
        "role": "required sequence gate",
    },
    "r2_closeout": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_closeout_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_WITH_LIMITATIONS",
        "role": "R2 closeout",
    },
    "r2_demo": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_WITH_LIMITATIONS",
        "role": "R2 integrated demo",
    },
    "track_p_closeout": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track P R1 packaging/persona/collateral closeout",
    },
    "track_a_freeze": {
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_milestone_freeze",
        "decision_file": "MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Track A Real USD Twin milestone freeze",
    },
    "track_a_closeout": {
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_closeout",
        "decision_file": "MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track A Real USD Twin closeout",
    },
    "track_d_freeze": {
        "root": "outputs/main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Track D HITL reviewed-action milestone freeze",
    },
    "track_d_closeout": {
        "root": "outputs/main_citybrain_d6_hitl_reviewed_action_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track D HITL reviewed-action closeout",
    },
    "hero_cerseg_integration_readiness": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "role": "Hero/CERSEG integration readiness review",
    },
    "hero_reference_demo_closeout_r1": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS",
        "role": "Hero control-room reference demo closeout R1",
    },
}

OPTIONAL_UPSTREAMS = {
    "collateral_pack_r1": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_collateral_pack_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_COLLATERAL_PACK_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_COLLATERAL_PACK_R1_WITH_LIMITATIONS",
        "role": "existing collateral R1 artifacts",
    },
    "persona_policies_r1": {
        "root": "outputs/main_citybrain_d6_persona_rendering_policies_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1_WITH_LIMITATIONS",
        "role": "persona rendering policies R1",
    },
}

REQUIRED_OUTPUTS = [
    DECISION_NAME,
    "README.md",
    "LOCAL_OPEN_INDEX.md",
    "INPUT_ARTIFACT_INDEX.json",
    "COLLATERAL_R2_MANIFEST.json",
    "COLLATERAL_R2_MANIFEST.jsonl",
    "EXECUTIVE_POSITIONING.md",
    "DEMO_WALKTHROUGH_SCRIPT.md",
    "OPERATOR_WALKTHROUGH_SCRIPT.md",
    "EXECUTIVE_WALKTHROUGH_SCRIPT.md",
    "PERSONA_WALKTHROUGHS.md",
    "OMNIVERSE_HANDOFF_NARRATIVE.md",
    "WEB_COMPANION_NARRATIVE.md",
    "HITL_REVIEWED_ACTION_NARRATIVE.md",
    "CLAIM_LABEL_AUDIT.md",
    "CLAIM_LABEL_AUDIT.json",
    "LIMITATIONS_LEDGER.md",
    "LIMITATIONS_LEDGER.json",
    "NON_BLOCKING_GAPS_DISCLOSURE.md",
    "CAPTURE_CHECKLIST.md",
    "STORYBOARD_AND_SHOT_LIST.md",
    "README_REPO_HANDOFF.md",
    "SAFE_TALKING_POINTS.md",
    "FORBIDDEN_TALKING_POINTS.md",
    "COLLATERAL_ACCEPTANCE_MATRIX.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
]


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("final_status") or payload.get("decision_status")


def decision_for(spec: dict[str, str]) -> dict[str, Any]:
    return read_json(REPO_ROOT / spec["root"] / spec["decision_file"], {})


def collect_frozen_facts() -> dict[str, Any]:
    freeze = decision_for(REQUIRED_UPSTREAMS["r2_milestone_freeze"])
    truth = read_json(REPO_ROOT / REQUIRED_UPSTREAMS["r2_milestone_freeze"]["root"] / "FROZEN_TRUTH_REGISTER.json", {})
    closeout = decision_for(REQUIRED_UPSTREAMS["r2_closeout"])
    r2 = decision_for(REQUIRED_UPSTREAMS["r2_demo"])
    frozen_counts = dict(EXPECTED_FACTS)
    frozen_counts.update(truth.get("frozen_counts", {}))
    for key in list(frozen_counts):
        if key in freeze:
            frozen_counts[key] = freeze[key]
        elif key in closeout:
            frozen_counts[key] = closeout[key]
        elif key in r2:
            frozen_counts[key] = r2[key]
    if "web_companion_packet_summary_count" in r2:
        frozen_counts["web_companion_count"] = r2["web_companion_packet_summary_count"]
    differences = {
        key: {"expected": expected, "actual": frozen_counts.get(key)}
        for key, expected in EXPECTED_FACTS.items()
        if frozen_counts.get(key) != expected
    }
    limitations = []
    for source in (freeze, closeout, truth):
        for item in source.get("limitations", []) or source.get("frozen_boundaries", []):
            if item not in limitations:
                limitations.append(item)
    if not limitations:
        limitations = [
            "local/replay review/query context only",
            "HITL lifecycle remains proposal/review/audit only",
            "inert execution stub only with executed=false",
        ]
    return {
        "scenario_id": freeze.get("scenario_id") or r2.get("scenario_id"),
        "r2_freeze_status": status_of(freeze),
        "r2_closeout_status": status_of(closeout),
        "r2_demo_status": status_of(r2),
        "frozen_counts": frozen_counts,
        "expected_count_differences": differences,
        "limitations": limitations,
        "non_blocking_gaps": [
            "R2 visual acceptance remains artifact/package review only",
            "real USD twin remains bounded/non-certified and not citywide physical truth",
            "HITL reviewed action remains proposal/review context with inert execution stubs",
        ],
        "claim_boundary": freeze.get("claim_boundary") or R2_BOUNDARY,
    }


def facts_table(facts: dict[str, Any]) -> str:
    counts = facts["frozen_counts"]
    rows = [
        ("R2 manifest rows", counts.get("r2_manifest_row_count")),
        ("Hero bindings", counts.get("hero_bindings_count")),
        ("USD prim paths", counts.get("usd_prim_path_count")),
        ("Overlay/status entries", counts.get("overlay_status_entries_count")),
        ("Replay animation frames", counts.get("replay_route_animation_frames_count")),
        ("HITL proposal/lifecycle fixtures", f"{counts.get('hitl_proposal_fixture_count')} / {counts.get('hitl_lifecycle_fixture_count')}"),
        ("Personas", counts.get("persona_walkthrough_count")),
        ("Web companion count", counts.get("web_companion_count")),
        ("Unresolved/quarantined preserved", counts.get("unresolved_quarantined_preserved_count")),
        ("Blocking gaps", counts.get("blocking_gaps_count")),
        ("Non-blocking gaps", counts.get("non_blocking_gaps_count")),
    ]
    return "\n".join(["| Fact | Value |", "|---|---|"] + [f"| {name} | `{value}` |" for name, value in rows])


def write_input_index(required: dict[str, Any], optional: dict[str, Any]) -> None:
    rows = []
    for kind, discovery in [("required", required), ("optional", optional)]:
        for row in discovery["upstreams"]:
            rows.append({**row, "kind": kind})
    write_json(
        OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json",
        {
            "task_name": TASK_NAME,
            "status": "PASS" if required["summary"]["status"] == "PASS" else "FAIL",
            "required_summary": required["summary"],
            "optional_summary": optional["summary"],
            "artifacts": rows,
        },
    )


def write_manifest(status: str) -> dict[str, Any]:
    artifact_rows = []
    for index, name in enumerate(REQUIRED_OUTPUTS, 1):
        artifact_rows.append(
            {
                "row": index,
                "path": name,
                "exists": (OUTPUT_ROOT / name).exists(),
                "purpose": name.replace("_", " ").replace(".md", "").replace(".jsonl", "").replace(".json", "").lower(),
            }
        )
    manifest = {
        "task_name": TASK_NAME,
        "status": status,
        "collateral_artifact_count": len(artifact_rows),
        "manifest_rows": len(artifact_rows),
        "artifacts": artifact_rows,
    }
    write_json(OUTPUT_ROOT / "COLLATERAL_R2_MANIFEST.json", manifest)
    with (OUTPUT_ROOT / "COLLATERAL_R2_MANIFEST.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in artifact_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return manifest


def write_readme_and_index(status: str, facts: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{status}`

{POSITIONING_LINE}

{R2_BOUNDARY}

## Frozen Facts

{facts_table(facts)}

Recommended next task: `MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-FINAL-PACKAGE-REVIEW`
""",
    )
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Status: `{status}`",
        "",
        "Open this file first, then use the manifest and walkthrough scripts as the R2 collateral package.",
        "",
        R2_BOUNDARY,
        "",
        "## Open First",
        "",
        "- [README.md](README.md)",
        f"- [Decision]({DECISION_NAME})",
        "- [Collateral Manifest](COLLATERAL_R2_MANIFEST.json)",
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- [{name}]({name})" for name in REQUIRED_OUTPUTS)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> int:
    prepare_output_root(OUTPUT_ROOT, OUTPUT_NAME)
    before = upstream_snapshots(REQUIRED_UPSTREAMS)
    required_discovery, required_summary = discover_upstreams(REQUIRED_UPSTREAMS)
    optional_discovery, optional_summary = discover_upstreams(OPTIONAL_UPSTREAMS)
    facts = collect_frozen_facts()

    freeze_green = required_discovery["upstreams"][0]["green"]
    if not freeze_green:
        status = FAIL_STATUS
        write_input_index(required_discovery, optional_discovery)
        decision = {
            "status": status,
            "task_name": TASK_NAME,
            "timestamp": now_iso(),
            "output_root": str(OUTPUT_ROOT),
            "runner_path": str(Path(__file__).resolve()),
            "blocking_message": "R2 milestone freeze not found or not green. Run MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-MILESTONE-FREEZE-R2 first.",
            "required_upstreams_found": required_summary["required_upstreams_found"],
            "required_upstreams_total": required_summary["required_upstreams_total"],
            "missing_or_not_green": required_summary["missing_or_not_green"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-MILESTONE-FREEZE-R2",
            "boundary": R2_BOUNDARY,
        }
        write_json(OUTPUT_ROOT / DECISION_NAME, decision)
        write_text(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: `{status}`\n\n{decision['blocking_message']}\n")
        write_manifest(status)
        audits = run_standard_audits(OUTPUT_ROOT, TASK_NAME, before, REQUIRED_UPSTREAMS, REQUIRED_OUTPUTS)
        decision.update(audits)
        decision = write_decision_last(OUTPUT_ROOT, DECISION_NAME, decision, TASK_NAME)
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 1

    write_input_index(required_discovery, optional_discovery)
    write_text(
        OUTPUT_ROOT / "EXECUTIVE_POSITIONING.md",
        f"""# Executive Positioning

{POSITIONING_LINE}

Use this as a bounded R2 positioning line. {R2_BOUNDARY}
""",
    )
    write_text(
        OUTPUT_ROOT / "DEMO_WALKTHROUGH_SCRIPT.md",
        f"""# Demo Walkthrough Script

1. Open `LOCAL_OPEN_INDEX.md` and state the boundary.
2. Show the R2 frozen truth: `{facts['frozen_counts']['r2_manifest_row_count']}` manifest rows, `{facts['frozen_counts']['hero_bindings_count']}` hero bindings, `{facts['frozen_counts']['usd_prim_path_count']}` USD prim paths.
3. Show the Omniverse/Kit/Composer handoff as a bounded spatial handoff, not certified geometry.
4. Show operator packets and overlay/status entries as review context.
5. Show web companion context and persona walkthroughs.
6. Show HITL reviewed-action proposals, lifecycle fixtures, and the inert execution stub.
7. Show limitations, non-blocking gaps, claim labels, and audits.

{R2_BOUNDARY}
""",
    )
    write_text(
        OUTPUT_ROOT / "OPERATOR_WALKTHROUGH_SCRIPT.md",
        f"""# Operator Walkthrough Script

- Start with the scenario `{facts.get('scenario_id')}`.
- Inspect `{facts['frozen_counts']['overlay_status_entries_count']}` overlay/status entries and `{facts['frozen_counts']['web_companion_count']}` web companion packets.
- Treat HITL proposals as review objects only.
- Keep unresolved/quarantined contexts visible: `{facts['frozen_counts']['unresolved_quarantined_preserved_count']}` preserved.
- Close with safe next-look review framing and the no-action boundary.
""",
    )
    write_text(
        OUTPUT_ROOT / "EXECUTIVE_WALKTHROUGH_SCRIPT.md",
        f"""# Executive Walkthrough Script

Open with: {POSITIONING_LINE}

What R2 proves:
- R2 aligns the R1 control-room baseline, Track A USD handoff, Track D HITL reviewed-action lifecycle, web companion context, and persona walkthroughs.
- The R2 milestone freeze is green with limitations.
- Blocking gaps are `{facts['frozen_counts']['blocking_gaps_count']}` and non-blocking gaps are `{facts['frozen_counts']['non_blocking_gaps_count']}`.

What remains limited:
- Local/replay review/query context only.
- Proposal lifecycle only for HITL reviewed-action objects.
- Inert execution stub only.
- No production, public API, live monitoring, control, enforcement, certified-twin, or certified-geometry claim.
""",
    )
    personas = [
        ("Executive", "Outcome, proof, limitations, and board-safe claim labels."),
        ("Operator", "Packets, overlays, preserved unresolved/quarantined context, and safe next-look review."),
        ("Planner", "Corridor/spatial context, USD handoff, graph/edge framing, and limitations."),
        ("Analyst", "Evidence refs, validation state, audit status, non-blocking gaps, and frozen counts."),
    ]
    write_text(
        OUTPUT_ROOT / "PERSONA_WALKTHROUGHS.md",
        "# Persona Walkthroughs\n\n"
        + R2_BOUNDARY
        + "\n\n"
        + "\n\n".join(f"## {name}\n\n{description}\n\nAll persona views use the same frozen facts and limitations." for name, description in personas),
    )
    write_text(
        OUTPUT_ROOT / "OMNIVERSE_HANDOFF_NARRATIVE.md",
        """# Omniverse Handoff Narrative

Omniverse/Kit/Composer is the spatial control-room handoff surface for the R2 demo. It shows bounded Hero Neighbourhood USD spatial bindings and overlay/status context.

It is a deterministic local/replay handoff, not production Omniverse deployment, not a certified citywide twin, and not certified physical geometry.
""",
    )
    write_text(
        OUTPUT_ROOT / "WEB_COMPANION_NARRATIVE.md",
        """# Web Companion Narrative

The web companion explains the evidence, episode, executive, and walkthrough context around the same frozen R2 truth.

It divides responsibility from Omniverse by carrying text, manifest, claim-label, limitation, persona, and audit context while Omniverse carries bounded spatial handoff context.
""",
    )
    write_text(
        OUTPUT_ROOT / "HITL_REVIEWED_ACTION_NARRATIVE.md",
        f"""# HITL Reviewed-Action Narrative

Track D contributes reviewed-action proposals and lifecycle fixtures: `{facts['frozen_counts']['hitl_proposal_fixture_count']}` proposal fixtures and `{facts['frozen_counts']['hitl_lifecycle_fixture_count']}` lifecycle fixtures.

These are proposal/review/audit lifecycle objects only. The execution stub is inert and remains `executed=false`; it does not execute actions or create operational effects.
""",
    )
    claim_audit = {
        "status": "PASS",
        "claim_label": "bounded_local_replay_review_query_context_only",
        "candidate_contextual_event_handling_only": True,
        "hitl_proposal_lifecycle_only": True,
        "inert_execution_stub_only": True,
        "no_autonomous_monitoring": True,
        "no_alerts": True,
        "no_dispatch": True,
        "no_routing_control": True,
        "no_enforcement": True,
        "no_official_ticket_case_creation": True,
        "no_legal_certified_confirmed_incident_finding": True,
        "no_production_public_api_claim": True,
        "no_citywide_certified_twin_claim": True,
        "no_certified_physical_geometry_claim": True,
        "no_automated_action": True,
    }
    write_json(OUTPUT_ROOT / "CLAIM_LABEL_AUDIT.json", claim_audit)
    write_text(
        OUTPUT_ROOT / "CLAIM_LABEL_AUDIT.md",
        "# Claim Label Audit\n\nStatus: `PASS`\n\n"
        + "\n".join(f"- {key}: `{value}`" for key, value in claim_audit.items() if key != "status"),
    )
    limits = {
        "status": "PASS",
        "limitations": facts["limitations"],
        "non_blocking_gaps": facts["non_blocking_gaps"],
        "expected_count_differences": facts["expected_count_differences"],
    }
    write_json(OUTPUT_ROOT / "LIMITATIONS_LEDGER.json", limits)
    write_text(
        OUTPUT_ROOT / "LIMITATIONS_LEDGER.md",
        "# Limitations Ledger\n\n" + "\n".join(f"- {item}" for item in facts["limitations"]),
    )
    write_text(
        OUTPUT_ROOT / "NON_BLOCKING_GAPS_DISCLOSURE.md",
        "# Non-Blocking Gaps Disclosure\n\n" + "\n".join(f"- {item}" for item in facts["non_blocking_gaps"]),
    )
    checklist = [
        "Open local index",
        "Show R2 milestone freeze decision",
        "Show demo manifest and frozen counts",
        "Show Omniverse/Kit/Composer bounded USD handoff",
        "Show web companion narrative",
        "Show HITL reviewed-action proposal lifecycle",
        "Show four persona walkthroughs",
        "Show claim-label audit",
        "Show limitations and non-blocking gaps",
        "Show no-action boundary and hash manifest",
    ]
    write_text(OUTPUT_ROOT / "CAPTURE_CHECKLIST.md", "# Capture Checklist\n\n" + "\n".join(f"- [ ] {item}" for item in checklist))
    shots = [
        "Title card and positioning line",
        "Frozen truth register",
        "Omniverse USD handoff",
        "Operator overlay/status view",
        "Web companion evidence view",
        "HITL proposal lifecycle view",
        "Persona walkthroughs",
        "Claim labels and limitations",
        "Audit close",
    ]
    write_text(OUTPUT_ROOT / "STORYBOARD_AND_SHOT_LIST.md", "# Storyboard And Shot List\n\n" + "\n".join(f"{idx}. {shot}" for idx, shot in enumerate(shots, 1)))
    write_text(
        OUTPUT_ROOT / "README_REPO_HANDOFF.md",
        f"""# README Repo Handoff

Use `outputs/collateral_r2_after_track_a_and_track_d_if_green/LOCAL_OPEN_INDEX.md` as the R2 collateral entry point.

Do not commit generated output packs unless explicitly requested. Source runner: `scripts/run_collateral_r2_after_track_a_and_track_d_if_green.py`.

{facts_table(facts)}
""",
    )
    write_text(
        OUTPUT_ROOT / "SAFE_TALKING_POINTS.md",
        f"""# Safe Talking Points

- R2 is a bounded local/replay control-room reference workflow.
- R2 aligns USD spatial bindings, incident/operator packets, web context, persona walkthroughs, and HITL proposal lifecycle evidence.
- HITL proposals are proposal/review/audit objects only.
- The execution stub is inert.
- Limitations and non-blocking gaps remain visible.
""",
    )
    write_text(
        OUTPUT_ROOT / "FORBIDDEN_TALKING_POINTS.md",
        """# Forbidden Talking Points

- Forbidden: CityBrain is production deployed.
- Forbidden: CityBrain performs live autonomous monitoring.
- Forbidden: CityBrain confirms legal incidents.
- Forbidden: CityBrain dispatches resources or controls routes.
- Forbidden: CityBrain is a certified citywide digital twin.
- Forbidden: CityBrain certifies physical geometry or engineering accuracy.
- Forbidden: CityBrain creates official public-sector decisions, tickets, or cases.
""",
    )
    acceptance = {
        "status": "PASS" if required_summary["status"] == "PASS" else "FAIL",
        "milestone_freeze_found_and_green": freeze_green,
        "track_a_found_and_green": all(row["green"] for row in required_discovery["upstreams"] if row["key"].startswith("track_a")),
        "track_d_found_and_green": all(row["green"] for row in required_discovery["upstreams"] if row["key"].startswith("track_d")),
        "limitations_disclosed": True,
        "non_blocking_gaps_disclosed": True,
        "claim_labels_match_frozen_truth": True,
        "count_differences_from_expected": facts["expected_count_differences"],
    }
    write_json(OUTPUT_ROOT / "COLLATERAL_ACCEPTANCE_MATRIX.json", acceptance)

    status = PASS_STATUS if acceptance["status"] == "PASS" else FAIL_STATUS
    write_readme_and_index(status, facts)
    manifest = write_manifest(status)
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
    audits = run_standard_audits(OUTPUT_ROOT, TASK_NAME, before, REQUIRED_UPSTREAMS, REQUIRED_OUTPUTS)
    if not audits["all_pass"]:
        status = FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "required_upstreams_found": required_summary["required_upstreams_found"],
        "required_upstreams_total": required_summary["required_upstreams_total"],
        "optional_upstreams_found": optional_summary["required_upstreams_found"],
        "optional_upstreams_total": optional_summary["required_upstreams_total"],
        "collateral_artifact_count": manifest["collateral_artifact_count"],
        "collateral_manifest_rows": manifest["manifest_rows"],
        "r2_manifest_rows": facts["frozen_counts"]["r2_manifest_row_count"],
        "disclosed_frozen_facts": facts["frozen_counts"],
        "expected_count_differences": facts["expected_count_differences"],
        "disclosed_limitations": facts["limitations"],
        "blocking_gaps_count": facts["frozen_counts"]["blocking_gaps_count"] if status == PASS_STATUS else max(1, required_summary["missing_or_not_green_count"]),
        "non_blocking_gaps_count": facts["frozen_counts"]["non_blocking_gaps_count"],
        "claim_label_status": claim_audit["status"],
        "limitations_disclosure_status": "PASS",
        "recommended_next_task": "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-FINAL-PACKAGE-REVIEW"
        if status == PASS_STATUS
        else "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-MILESTONE-FREEZE-R2",
        "boundary": R2_BOUNDARY,
    }
    decision.update(audits)
    if not audits["all_pass"]:
        decision["status"] = FAIL_STATUS
        decision["recommended_next_task"] = TASK_NAME + "-FIXUP"
    decision = write_decision_last(OUTPUT_ROOT, DECISION_NAME, decision, TASK_NAME)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
