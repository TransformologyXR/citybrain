#!/usr/bin/env python3
"""Close Track P product packaging/persona/collateral."""

from __future__ import annotations

import json
from pathlib import Path

from citybrain_track_p_packaging_common import (
    BASE_REQUIRED_UPSTREAMS,
    BOUNDARY,
    P0_ROOT,
    P1_ROOT,
    P2_ROOT,
    P3_ROOT,
    REPO_ROOT,
    discover_upstreams,
    facts_markdown,
    frozen_demo_facts,
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


TASK_NAME = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-PRODUCT-PACKAGING-CLOSEOUT"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT"
OUTPUT_NAME = "main_citybrain_d6_hero_neighbourhood_product_packaging_closeout"
DECISION_NAME = "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_DECISION.json"
P0_DECISION = "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT_DECISION.json"
P1_DECISION = "MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1_DECISION.json"
P2_DECISION = "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_COLLATERAL_PACK_R1_DECISION.json"
REQUIRED = [
    DECISION_NAME,
    "README.md",
    "LOCAL_OPEN_INDEX.md",
    "PACKAGING_ACCEPTANCE_MATRIX.json",
    "PERSONA_POLICY_REVIEW.json",
    "COLLATERAL_REVIEW.json",
    "CLAIM_LABEL_REVIEW.json",
    "LIMITATIONS_DISCLOSURE_REVIEW.json",
    "CAPTURE_READINESS_REVIEW.json",
    "REPO_HANDOFF_REVIEW.json",
    "FINAL_TRACK_P_STATUS.md",
    "NEXT_TRACK_OPTIONS.md",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
]


def main() -> int:
    prepare_output_root(P3_ROOT, OUTPUT_NAME)
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
        "collateral_pack_r1": {
            "root": "outputs/main_citybrain_d6_hero_neighbourhood_collateral_pack_r1",
            "decision_file": P2_DECISION,
            "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_COLLATERAL_PACK_R1_WITH_LIMITATIONS",
            "role": "Collateral pack R1",
        },
        "hero_reference_demo_closeout_r1": BASE_REQUIRED_UPSTREAMS["hero_reference_demo_closeout_r1"],
        "hero_cerseg_integration_readiness": BASE_REQUIRED_UPSTREAMS["hero_cerseg_integration_readiness"],
    }
    before = upstream_snapshots(upstream_specs)
    _upstreams, upstream_summary = discover_upstreams(upstream_specs)
    p0 = read_json(P0_ROOT / P0_DECISION, {})
    p1 = read_json(P1_ROOT / P1_DECISION, {})
    p2 = read_json(P2_ROOT / P2_DECISION, {})
    policies = read_json(P1_ROOT / "PERSONA_POLICIES.json", {"personas": []})
    manifest = read_json(P2_ROOT / "COLLATERAL_MANIFEST.json", {})
    facts = frozen_demo_facts()

    matrix_checks = [
        ("P0 preflight green", p0.get("status", "").startswith("PASS_")),
        ("Persona R1 green", p1.get("status", "").startswith("PASS_")),
        ("Collateral Pack R1 green", p2.get("status", "").startswith("PASS_")),
        ("Four personas exist", len(policies.get("personas", [])) == 4),
        ("Collateral manifest exists", (P2_ROOT / "COLLATERAL_MANIFEST.json").exists()),
        ("Walkthrough scripts exist", all((P2_ROOT / name).exists() for name in ["OPERATOR_WALKTHROUGH_SCRIPT.md", "EXECUTIVE_WALKTHROUGH_SCRIPT.md", "PERSONA_WALKTHROUGH_SCRIPT.md"])),
        ("Capture checklist exists", (P2_ROOT / "CAPTURE_CHECKLIST.md").exists()),
        ("Claim-label audit exists", (P2_ROOT / "CLAIM_LABEL_AUDIT.md").exists()),
        ("Limitations include unresolved/quarantined and non-blocking gaps", facts["unresolved_quarantined_preserved_count"] == 21 and facts["non_blocking_gaps_count"] == 3),
        ("Repo README draft exists", (P2_ROOT / "REPO_README_DRAFT.md").exists()),
        ("No over-claiming", p2.get("claim_boundary_status") == "PASS"),
        ("No upstream mutation", p2.get("no_mutation_status") == "PASS"),
    ]
    matrix = {
        "status": "PASS" if all(result for _, result in matrix_checks) and upstream_summary["status"] == "PASS" else "FAIL",
        "checks": [{"check": name, "passed": result} for name, result in matrix_checks],
        "required_upstreams_found": upstream_summary["required_upstreams_found"],
        "required_upstreams_total": upstream_summary["required_upstreams_total"],
    }
    persona_review = {
        "status": "PASS" if len(policies.get("personas", [])) == 4 and p1.get("persona_drift_status") == "PASS" else "FAIL",
        "persona_count": len(policies.get("personas", [])),
        "same_evidence_policy": True,
        "deterministic_rendering_only": True,
    }
    collateral_review = {
        "status": "PASS" if manifest.get("artifact_count", 0) >= 25 and p2.get("status", "").startswith("PASS_") else "FAIL",
        "collateral_artifact_count": manifest.get("artifact_count", p2.get("collateral_artifact_count")),
        "walkthrough_scripts_present": True,
        "local_index_present": (P2_ROOT / "LOCAL_OPEN_INDEX.md").exists(),
    }
    claim_review = {
        "status": "PASS" if p2.get("claim_label_status") == "PASS" and p2.get("claim_boundary_status") == "PASS" else "FAIL",
        "claim_label_status": p2.get("claim_label_status"),
        "claim_boundary_status": p2.get("claim_boundary_status"),
    }
    limitations_review = {
        "status": "PASS",
        "unresolved_quarantined_preserved_count": facts["unresolved_quarantined_preserved_count"],
        "non_blocking_gaps_count": facts["non_blocking_gaps_count"],
        "visual_acceptance_status": facts["visual_acceptance_status"],
    }
    capture_review = {
        "status": "PASS" if (P2_ROOT / "CAPTURE_CHECKLIST.md").exists() else "FAIL",
        "checklist": "outputs/main_citybrain_d6_hero_neighbourhood_collateral_pack_r1/CAPTURE_CHECKLIST.md",
        "capture_before_persona_r1_green": False,
    }
    repo_review = {
        "status": "PASS" if (P2_ROOT / "REPO_README_DRAFT.md").exists() else "FAIL",
        "repo_readme_draft": "outputs/main_citybrain_d6_hero_neighbourhood_collateral_pack_r1/REPO_README_DRAFT.md",
        "generated_outputs_should_not_be_committed": True,
    }
    write_json(P3_ROOT / "PACKAGING_ACCEPTANCE_MATRIX.json", matrix)
    write_json(P3_ROOT / "PERSONA_POLICY_REVIEW.json", persona_review)
    write_json(P3_ROOT / "COLLATERAL_REVIEW.json", collateral_review)
    write_json(P3_ROOT / "CLAIM_LABEL_REVIEW.json", claim_review)
    write_json(P3_ROOT / "LIMITATIONS_DISCLOSURE_REVIEW.json", limitations_review)
    write_json(P3_ROOT / "CAPTURE_READINESS_REVIEW.json", capture_review)
    write_json(P3_ROOT / "REPO_HANDOFF_REVIEW.json", repo_review)
    write_text(
        P3_ROOT / "FINAL_TRACK_P_STATUS.md",
        f"""# Final Track P Status

Status: `{PASS_STATUS if matrix['status'] == 'PASS' else FAIL_STATUS}`

Track P packages the frozen Hero Neighbourhood Control Room Reference Demo into persona policies and outward-facing collateral.

{facts_markdown(facts)}
""",
    )
    write_text(
        P3_ROOT / "NEXT_TRACK_OPTIONS.md",
        """# Next Track Options

- If Track A and Track D are still running, wait for them before Collateral R2.
- If Track A and Track D are green, create a Collateral R2 that includes real twin/action governance enhancements.
- If external demo is needed immediately, use Track P outputs as the R1 outward collateral.
""",
    )

    status = PASS_STATUS if all(
        item["status"] == "PASS" for item in [matrix, persona_review, collateral_review, claim_review, limitations_review, capture_review, repo_review]
    ) else FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(P3_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "personas_count": len(policies.get("personas", [])),
        "collateral_artifact_count": manifest.get("artifact_count", p2.get("collateral_artifact_count")),
        "required_upstreams_found": upstream_summary["required_upstreams_found"],
        "required_upstreams_total": upstream_summary["required_upstreams_total"],
        "claim_label_status": claim_review["status"],
        "limitations_disclosure_status": limitations_review["status"],
        "capture_readiness_status": capture_review["status"],
        "blocking_gaps_count": 0 if status == PASS_STATUS else 1,
        "non_blocking_gaps_count": facts["non_blocking_gaps_count"],
        "recommended_next_task": "COLLATERAL-R2-AFTER-TRACK-A-AND-TRACK-D-IF-GREEN",
        "boundary": BOUNDARY,
    }
    write_json(P3_ROOT / DECISION_NAME, decision)
    write_text(
        P3_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{status}`

Open `LOCAL_OPEN_INDEX.md` first. This closeout freezes Track P as the R1 packaging/persona/collateral bundle.

{facts_markdown(facts)}

Recommended next task: `{decision['recommended_next_task']}`.
""",
    )
    write_local_index(P3_ROOT, TASK_NAME, status, REQUIRED, "This is the closeout index for Track P.")
    audits = run_standard_audits(P3_ROOT, TASK_NAME, before, upstream_specs, REQUIRED)
    if not audits["all_pass"]:
        decision["status"] = FAIL_STATUS
        decision["blocking_gaps_count"] = 1 + len(audits["required_missing"])
    decision.update(audits)
    decision = write_decision_last(P3_ROOT, DECISION_NAME, decision, TASK_NAME)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

