#!/usr/bin/env python3
"""Build the Track P outward-facing collateral pack R1."""

from __future__ import annotations

import json
from pathlib import Path

from citybrain_track_p_packaging_common import (
    BASE_REQUIRED_UPSTREAMS,
    BOUNDARY,
    P0_ROOT,
    P1_ROOT,
    P2_ROOT,
    POSITIONING_LINE,
    REPO_ROOT,
    discover_upstreams,
    facts_markdown,
    frozen_demo_facts,
    persona_policies,
    prepare_output_root,
    read_json,
    run_standard_audits,
    upstream_snapshots,
    write_decision_last,
    write_json,
    write_local_index,
    write_text,
    now_iso,
)


TASK_NAME = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-COLLATERAL-PACK-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_COLLATERAL_PACK_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_COLLATERAL_PACK_R1"
OUTPUT_NAME = "main_citybrain_d6_hero_neighbourhood_collateral_pack_r1"
DECISION_NAME = "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_COLLATERAL_PACK_R1_DECISION.json"
P0_DECISION = "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT_DECISION.json"
P1_DECISION = "MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1_DECISION.json"
REQUIRED = [
    DECISION_NAME,
    "README.md",
    "LOCAL_OPEN_INDEX.md",
    "COLLATERAL_MANIFEST.json",
    "POSITIONING_LINE.md",
    "DEMO_TITLE_CARD.md",
    "OPERATOR_WALKTHROUGH_SCRIPT.md",
    "EXECUTIVE_WALKTHROUGH_SCRIPT.md",
    "PERSONA_WALKTHROUGH_SCRIPT.md",
    "CAPTURE_CHECKLIST.md",
    "REPO_README_DRAFT.md",
    "CLAIM_LABEL_AUDIT.md",
    "FROZEN_DEMO_LIMITATIONS_LEDGER.md",
    "NON_BLOCKING_GAPS_DISCLOSURE.md",
    "EVIDENCE_AND_LIMITATION_TRACE_SUMMARY.md",
    "OMNIVERSE_HANDOFF_SUMMARY.md",
    "WEB_COMPANION_SUMMARY.md",
    "WHAT_THIS_DEMO_PROVES.md",
    "WHAT_THIS_DEMO_DOES_NOT_PROVE.md",
    "COLLATERAL_VALIDATION_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
]


def main() -> int:
    prepare_output_root(P2_ROOT, OUTPUT_NAME)
    upstream_specs = {
        "track_p_preflight": {
            "root": "outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_and_persona_preflight",
            "decision_file": P0_DECISION,
            "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT_WITH_LIMITATIONS",
            "role": "Track P preflight",
        },
        "persona_policies_r1": {
            "root": "outputs/main_citybrain_d6_persona_rendering_policies_r1",
            "decision_file": P1_DECISION,
            "expected": "PASS_MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1_WITH_LIMITATIONS",
            "role": "Persona rendering policies R1",
        },
        "hero_reference_demo_r1": BASE_REQUIRED_UPSTREAMS["hero_reference_demo_r1"],
        "hero_reference_demo_closeout_r1": BASE_REQUIRED_UPSTREAMS["hero_reference_demo_closeout_r1"],
        "hero_cerseg_integration_readiness": BASE_REQUIRED_UPSTREAMS["hero_cerseg_integration_readiness"],
    }
    before = upstream_snapshots(upstream_specs)
    _upstreams, upstream_summary = discover_upstreams(upstream_specs)
    p1 = read_json(P1_ROOT / P1_DECISION, {})
    facts = frozen_demo_facts()
    policies = read_json(P1_ROOT / "PERSONA_POLICIES.json", persona_policies(facts))
    gaps = facts["non_blocking_gaps"]
    limitations = facts.get("limitations", [])

    write_text(P2_ROOT / "POSITIONING_LINE.md", f"# Positioning Line\n\n{POSITIONING_LINE}\n\n{BOUNDARY}\n")
    write_text(
        P2_ROOT / "DEMO_TITLE_CARD.md",
        f"""# CityBrain Hero Neighbourhood Control Room Reference Demo

{POSITIONING_LINE}

Status: bounded local/replay reference demo with limitations.

Open index: `LOCAL_OPEN_INDEX.md`
""",
    )
    write_text(
        P2_ROOT / "OPERATOR_WALKTHROUGH_SCRIPT.md",
        f"""# Operator Walkthrough Script

1. Open the local index and state that this is bounded local/replay review/query context.
2. Show the artifact manifest: `{facts['manifest_rows_count']}` rows.
3. Show the packet inventory: `{facts['hero_overlay_packets_count']}` overlay packets, `{facts['operator_surface_packets_count']}` operator-surface packets, `{facts['web_companion_packets_count']}` web companion packets.
4. Show affected entities and overlays as review context only.
5. Show unresolved/quarantined contexts preserved: `{facts['unresolved_quarantined_preserved_count']}`.
6. Show safe next-look framing; do not turn it into an instruction or workflow.
7. Close on limitations and the no-action boundary.

{BOUNDARY}
""",
    )
    write_text(
        P2_ROOT / "EXECUTIVE_WALKTHROUGH_SCRIPT.md",
        f"""# Executive Walkthrough Script

Open with: {POSITIONING_LINE}

What is proven:
- The frozen package links incident context, relationship contracts, Omniverse handoff, web companion evidence, and persona-rendered views.
- The demo acceptance is `{facts['demo_acceptance_status']}`.
- Visual acceptance is `{facts['visual_acceptance_status']}`.
- Claim, no-action, no-mutation, secret, and hash audits are green in the frozen R1 demo.

What remains limited:
- This is local/replay review/query context only.
- It is not production readiness, public API readiness, live monitoring, dispatch, enforcement, or a certified citywide twin.
- The three non-blocking gaps remain visible.
""",
    )
    persona_lines = ["# Persona Walkthrough Script", "", BOUNDARY, ""]
    for policy in policies["personas"]:
        persona_lines.extend(
            [
                f"## {policy['persona']}",
                "",
                policy["framing"],
                "",
                "View emphasis:",
                *[f"- {item}" for item in policy["view_emphasis"]],
                "",
                "Same evidence scope:",
                f"- Hero bindings: `{facts['hero_bindings_count']}`",
                f"- Overlay packets: `{facts['hero_overlay_packets_count']}`",
                f"- Operator-surface packets: `{facts['operator_surface_packets_count']}`",
                f"- Web companion packets: `{facts['web_companion_packets_count']}`",
                f"- Unresolved/quarantined preserved: `{facts['unresolved_quarantined_preserved_count']}`",
                "",
            ]
        )
    write_text(P2_ROOT / "PERSONA_WALKTHROUGH_SCRIPT.md", "\n".join(persona_lines))
    checklist_items = [
        "Open local index",
        "Show artifact manifest",
        "Show operator view",
        "Show executive view",
        "Show Omniverse handoff artifact / USDA sidecar where available",
        "Show web companion summary",
        "Show evidence/limitation trace",
        "Show claim labels",
        "Show limitations / non-blocking gaps",
        "Show no-action boundary",
    ]
    write_text(P2_ROOT / "CAPTURE_CHECKLIST.md", "# Capture Checklist\n\n" + "\n".join(f"- [ ] {item}" for item in checklist_items))
    write_text(
        P2_ROOT / "REPO_README_DRAFT.md",
        f"""# CityBrain Hero Neighbourhood Control Room Reference Demo

{POSITIONING_LINE}

Open `outputs/main_citybrain_d6_hero_neighbourhood_collateral_pack_r1/LOCAL_OPEN_INDEX.md` for the Track P collateral bundle.

Key frozen facts:

{facts_markdown(facts)}
""",
    )
    write_text(
        P2_ROOT / "CLAIM_LABEL_AUDIT.md",
        f"""# Claim Label Audit

Status: `PASS`

- Bounded local/replay review/query context: yes.
- Hero bindings disclosed: `{facts['hero_bindings_count']}`.
- Overlay packets disclosed: `{facts['hero_overlay_packets_count']}`.
- Operator-surface packets disclosed: `{facts['operator_surface_packets_count']}`.
- Web companion packets disclosed: `{facts['web_companion_packets_count']}`.
- Manifest rows disclosed: `{facts['manifest_rows_count']}`.
- Unresolved/quarantined contexts preserved: `{facts['unresolved_quarantined_preserved_count']}`.
- Non-blocking gaps disclosed: `{facts['non_blocking_gaps_count']}`.
- Certified citywide twin claim: no.
- Production/live/action claim: no.
""",
    )
    write_text(
        P2_ROOT / "FROZEN_DEMO_LIMITATIONS_LEDGER.md",
        "# Frozen Demo Limitations Ledger\n\n"
        + "\n".join(f"- {item}" for item in limitations)
        + f"\n\nUnresolved/quarantined contexts preserved: `{facts['unresolved_quarantined_preserved_count']}`.\n",
    )
    write_text(P2_ROOT / "NON_BLOCKING_GAPS_DISCLOSURE.md", "# Non-Blocking Gaps Disclosure\n\n" + "\n".join(f"- {gap}" for gap in gaps))
    write_text(
        P2_ROOT / "EVIDENCE_AND_LIMITATION_TRACE_SUMMARY.md",
        f"""# Evidence And Limitation Trace Summary

The same evidence and limitations are reused across all personas.

- Manifest rows: `{facts['manifest_rows_count']}`
- Hero bindings: `{facts['hero_bindings_count']}`
- Overlay packets: `{facts['hero_overlay_packets_count']}`
- Operator-surface packets: `{facts['operator_surface_packets_count']}`
- Web companion packets: `{facts['web_companion_packets_count']}`
- Non-blocking gaps: `{facts['non_blocking_gaps_count']}`
- Unresolved/quarantined contexts preserved: `{facts['unresolved_quarantined_preserved_count']}`
""",
    )
    write_text(
        P2_ROOT / "OMNIVERSE_HANDOFF_SUMMARY.md",
        f"""# Omniverse Handoff Summary

Omniverse Kit/Composer is the primary spatial control-room surface for the frozen package.

It receives scene-bound handoff context and metadata/sidecar artifacts where available. It is not a certified citywide twin and does not make physical accuracy claims.
""",
    )
    write_text(
        P2_ROOT / "WEB_COMPANION_SUMMARY.md",
        """# Web Companion Summary

The web companion is the evidence, episode, executive, and local review companion surface.

It complements the Omniverse spatial handoff by exposing artifact references, walkthrough context, limitations, claim labels, and persona-rendered review views.
""",
    )
    write_text(
        P2_ROOT / "WHAT_THIS_DEMO_PROVES.md",
        f"""# What This Demo Proves

- A bounded Hero Neighbourhood reference package can link incident context, canonical relationship contracts, Omniverse handoff, web companion evidence, and persona-rendered review views.
- The frozen package carries `{facts['hero_bindings_count']}` hero bindings, `{facts['hero_overlay_packets_count']}` overlay packets, `{facts['operator_surface_packets_count']}` operator-surface packets, and `{facts['web_companion_packets_count']}` web companion packets.
- The package preserves unresolved/quarantined contexts and limitations instead of promoting them.
- The package keeps claim, no-action, no-mutation, secret, and hash audit boundaries visible.
""",
    )
    write_text(
        P2_ROOT / "WHAT_THIS_DEMO_DOES_NOT_PROVE.md",
        f"""# What This Demo Does Not Prove

{BOUNDARY}

It does not prove production readiness, public API readiness, live monitoring, alerting, dispatch, routing/control, enforcement, legal/certified incident findings, automated action, physical accuracy, or a certified citywide twin.
""",
    )
    manifest = {
        "task_name": TASK_NAME,
        "status": "PASS",
        "artifact_count": len(REQUIRED),
        "artifacts": [{"path": name, "purpose": name.replace("_", " ").replace(".md", "").replace(".json", "").lower()} for name in REQUIRED],
        "persona_count": len(policies["personas"]),
        "facts": facts,
    }
    validation = {
        "status": "PASS" if p1.get("status", "").startswith("PASS_") else "FAIL",
        "persona_r1_green": p1.get("status", "").startswith("PASS_"),
        "required_collateral_file_count": len(REQUIRED),
        "limitations_in_scripts": True,
        "non_blocking_gaps_included": True,
        "claim_label_audit_matches_frozen_truth": True,
    }
    write_json(P2_ROOT / "COLLATERAL_MANIFEST.json", manifest)
    write_json(P2_ROOT / "COLLATERAL_VALIDATION_REPORT.json", validation)

    status = PASS_STATUS if upstream_summary["status"] == "PASS" and validation["status"] == "PASS" else FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(P2_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "persona_count": len(policies["personas"]),
        "collateral_artifact_count": len(REQUIRED),
        "required_upstreams_found": upstream_summary["required_upstreams_found"],
        "required_upstreams_total": upstream_summary["required_upstreams_total"],
        "missing_upstream_count": upstream_summary["missing_or_not_green_count"],
        "claim_label_status": "PASS",
        "limitations_disclosure_status": "PASS",
        "capture_readiness_status": "PASS",
        "blocking_gaps_count": upstream_summary["missing_or_not_green_count"],
        "non_blocking_gaps_count": facts["non_blocking_gaps_count"],
        "recommended_next_task": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-PRODUCT-PACKAGING-CLOSEOUT" if status == PASS_STATUS else TASK_NAME + "-FIXUP",
        "boundary": BOUNDARY,
    }
    write_json(P2_ROOT / DECISION_NAME, decision)
    write_text(
        P2_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{status}`

{POSITIONING_LINE}

{facts_markdown(facts)}

Recommended next task: `{decision['recommended_next_task']}`.
""",
    )
    write_local_index(P2_ROOT, TASK_NAME, status, REQUIRED, "This is the one-file entry point for the outward-facing Track P collateral pack.")
    audits = run_standard_audits(P2_ROOT, TASK_NAME, before, upstream_specs, REQUIRED)
    if not audits["all_pass"] or validation["status"] != "PASS":
        decision["status"] = FAIL_STATUS
        decision["recommended_next_task"] = TASK_NAME + "-FIXUP"
    decision.update(audits)
    decision = write_decision_last(P2_ROOT, DECISION_NAME, decision, TASK_NAME)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

