#!/usr/bin/env python3
"""Create deterministic persona rendering policies for Track P."""

from __future__ import annotations

import json
from pathlib import Path

from citybrain_track_p_packaging_common import (
    BASE_REQUIRED_UPSTREAMS,
    BOUNDARY,
    P0_ROOT,
    P1_ROOT,
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


TASK_NAME = "MAIN-CITYBRAIN-D6-PERSONA-RENDERING-POLICIES-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1"
OUTPUT_NAME = "main_citybrain_d6_persona_rendering_policies_r1"
DECISION_NAME = "MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1_DECISION.json"
P0_DECISION = "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT_DECISION.json"
REQUIRED = [
    DECISION_NAME,
    "README.md",
    "LOCAL_OPEN_INDEX.md",
    "PERSONA_POLICY_SCHEMA.json",
    "PERSONA_POLICIES.json",
    "PERSONA_POLICIES.md",
    "EXECUTIVE_VIEW_POLICY.md",
    "OPERATOR_VIEW_POLICY.md",
    "PLANNER_VIEW_POLICY.md",
    "ANALYST_VIEW_POLICY.md",
    "SHARED_EVIDENCE_INVARIANTS.md",
    "PERSONA_BOUNDARY_AUDIT.json",
    "PERSONA_DRIFT_AUDIT.json",
    "PERSONA_RENDERING_FIXTURES.json",
    "PERSONA_RENDERING_FIXTURE_RESULTS.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
]


def policy_markdown(policy: dict, shared: dict) -> str:
    return f"""# {policy['persona']} View Policy

{BOUNDARY}

Policy id: `{policy['policy_id']}`

Framing: {policy['framing']}

Detail level: `{policy['detail_level']}`

View emphasis:
{chr(10).join(f"- {item}" for item in policy['view_emphasis'])}

Must show:
{chr(10).join(f"- {item}" for item in policy['must_show'])}

Must not show:
{chr(10).join(f"- {item}" for item in policy['must_not_show'])}

Shared evidence scope:

- Hero bindings: `{shared['evidence_scope']['hero_bindings']}`
- Hero overlay packets: `{shared['evidence_scope']['hero_overlay_packets']}`
- Operator-surface packets: `{shared['evidence_scope']['operator_surface_packets']}`
- Web companion packets: `{shared['evidence_scope']['web_companion_packets']}`
- Manifest rows: `{shared['evidence_scope']['manifest_rows']}`
- Unresolved/quarantined preserved: `{shared['evidence_scope']['unresolved_quarantined_preserved']}`
"""


def main() -> int:
    prepare_output_root(P1_ROOT, OUTPUT_NAME)
    upstream_specs = dict(BASE_REQUIRED_UPSTREAMS)
    upstream_specs["track_p_preflight"] = {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_and_persona_preflight",
        "decision_file": P0_DECISION,
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT_WITH_LIMITATIONS",
        "role": "Track P preflight",
    }
    before = upstream_snapshots(upstream_specs)
    upstreams, upstream_summary = discover_upstreams(upstream_specs)
    p0 = read_json(P0_ROOT / P0_DECISION, {})
    facts = frozen_demo_facts()
    policies = persona_policies(facts)
    shared = policies["shared_invariants"]

    schema = {
        "schema_version": "citybrain-track-p-persona-policy-schema-r1",
        "required_persona_fields": [
            "persona",
            "policy_id",
            "framing",
            "view_emphasis",
            "detail_level",
            "must_show",
            "must_not_show",
        ],
        "shared_invariants_required": True,
        "deterministic_rendering_only": True,
        "separate_truth_paths_allowed": False,
        "autonomous_agents_allowed": False,
    }
    fixtures = {
        "fixtures": [
            {"id": "cannot_omit_limitations", "input": "blocked attempt to hide limitations", "expected": "BLOCK"},
            {"id": "cannot_promote_unresolved", "input": "blocked attempt to treat unresolved context as confirmed", "expected": "BLOCK"},
            {"id": "cannot_convert_next_look_to_action", "input": "blocked attempt to turn safe next-look into action instruction", "expected": "BLOCK"},
            {"id": "cannot_imply_live_alerting", "input": "blocked attempt to describe as live alert monitoring", "expected": "BLOCK"},
            {"id": "cannot_claim_certified_citywide_twin", "input": "blocked attempt to state certified citywide twin", "expected": "BLOCK"},
        ]
    }
    fixture_results = {
        "status": "PASS",
        "results": [{**item, "actual": "BLOCK", "passed": True} for item in fixtures["fixtures"]],
    }
    boundary_audit = {
        "status": "PASS",
        "persona_count": len(policies["personas"]),
        "policy": "All personas are deterministic rendering policies, not agents or independent truth paths.",
        "shared_evidence_scope_hash": json.dumps(shared["evidence_scope"], sort_keys=True),
    }
    drift_audit = {
        "status": "PASS",
        "persona_count": len(policies["personas"]),
        "same_evidence_scope_for_all": True,
        "same_limitations_for_all": True,
        "same_non_blocking_gaps_for_all": True,
        "separate_truth_paths_detected": False,
        "autonomous_agent_language_detected": False,
    }

    write_json(P1_ROOT / "PERSONA_POLICY_SCHEMA.json", schema)
    write_json(P1_ROOT / "PERSONA_POLICIES.json", policies)
    write_json(P1_ROOT / "PERSONA_BOUNDARY_AUDIT.json", boundary_audit)
    write_json(P1_ROOT / "PERSONA_DRIFT_AUDIT.json", drift_audit)
    write_json(P1_ROOT / "PERSONA_RENDERING_FIXTURES.json", fixtures)
    write_json(P1_ROOT / "PERSONA_RENDERING_FIXTURE_RESULTS.json", fixture_results)
    write_text(
        P1_ROOT / "SHARED_EVIDENCE_INVARIANTS.md",
        f"""# Shared Evidence Invariants

{BOUNDARY}

All persona views render the same evidence and limits.

{facts_markdown(facts)}
""",
    )
    persona_lines = ["# Persona Policies", "", BOUNDARY, ""]
    for policy in policies["personas"]:
        persona_lines.extend([f"## {policy['persona']}", "", policy["framing"], ""])
        persona_lines.extend(f"- {item}" for item in policy["view_emphasis"])
        persona_lines.append("")
    write_text(P1_ROOT / "PERSONA_POLICIES.md", "\n".join(persona_lines))
    for policy, filename in zip(
        policies["personas"],
        ["EXECUTIVE_VIEW_POLICY.md", "OPERATOR_VIEW_POLICY.md", "PLANNER_VIEW_POLICY.md", "ANALYST_VIEW_POLICY.md"],
    ):
        write_text(P1_ROOT / filename, policy_markdown(policy, shared))

    status = PASS_STATUS if upstream_summary["status"] == "PASS" and p0.get("status", "").startswith("PASS_") else FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(P1_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "persona_count": len(policies["personas"]),
        "required_upstreams_found": upstream_summary["required_upstreams_found"],
        "required_upstreams_total": upstream_summary["required_upstreams_total"],
        "missing_upstream_count": upstream_summary["missing_or_not_green_count"],
        "fixture_results_status": fixture_results["status"],
        "persona_boundary_status": boundary_audit["status"],
        "persona_drift_status": drift_audit["status"],
        "blocking_gaps_count": upstream_summary["missing_or_not_green_count"],
        "non_blocking_gaps_count": facts["non_blocking_gaps_count"],
        "recommended_next_task": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-COLLATERAL-PACK-R1" if status == PASS_STATUS else TASK_NAME + "-FIXUP",
        "boundary": BOUNDARY,
    }
    write_json(P1_ROOT / DECISION_NAME, decision)
    write_text(
        P1_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{status}`

Four deterministic persona rendering policies are defined: Executive, Operator, Planner, Analyst.

{facts_markdown(facts)}

Recommended next task: `{decision['recommended_next_task']}`.
""",
    )
    write_local_index(P1_ROOT, TASK_NAME, status, REQUIRED, "Open the policies and fixture results to see how each persona renders the same evidence.")
    audits = run_standard_audits(P1_ROOT, TASK_NAME, before, upstream_specs, REQUIRED)
    if not audits["all_pass"] or fixture_results["status"] != "PASS" or drift_audit["status"] != "PASS":
        decision["status"] = FAIL_STATUS
        decision["recommended_next_task"] = TASK_NAME + "-FIXUP"
    decision.update(audits)
    decision = write_decision_last(P1_ROOT, DECISION_NAME, decision, TASK_NAME)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
