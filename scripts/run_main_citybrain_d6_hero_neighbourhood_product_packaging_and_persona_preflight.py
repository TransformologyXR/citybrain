#!/usr/bin/env python3
"""Preflight Track P product packaging and persona rendering scope."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citybrain_track_p_packaging_common import (
    BASE_REQUIRED_UPSTREAMS,
    BOUNDARY,
    P0_ROOT,
    REPO_ROOT,
    discover_upstreams,
    facts_markdown,
    frozen_demo_facts,
    now_iso,
    prepare_output_root,
    run_standard_audits,
    upstream_snapshots,
    write_decision_last,
    write_json,
    write_local_index,
    write_text,
)


TASK_NAME = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-PRODUCT-PACKAGING-AND-PERSONA-PREFLIGHT"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT"
OUTPUT_NAME = "main_citybrain_d6_hero_neighbourhood_product_packaging_and_persona_preflight"
DECISION_NAME = "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT_DECISION.json"
REQUIRED = [
    DECISION_NAME,
    "README.md",
    "LOCAL_OPEN_INDEX.md",
    "UPSTREAM_DISCOVERY.json",
    "FROZEN_DEMO_FACTS.json",
    "TRACK_P_SCOPE_CONTRACT.json",
    "PERSONA_RENDERING_SCOPE.md",
    "COLLATERAL_SCOPE.md",
    "NON_BLOCKING_GAPS_CARRY_FORWARD.md",
    "CLAIM_LABEL_BASELINE.md",
    "VALIDATION_PLAN.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
]


def main() -> int:
    prepare_output_root(P0_ROOT, OUTPUT_NAME)
    before = upstream_snapshots(BASE_REQUIRED_UPSTREAMS)
    upstreams, upstream_summary = discover_upstreams(BASE_REQUIRED_UPSTREAMS)
    facts = frozen_demo_facts()

    scope_contract: dict[str, Any] = {
        "task_name": TASK_NAME,
        "status": "SCOPE_DEFINED",
        "scope": "Track P is packaging and narrative, not new platform functionality.",
        "persona_scope": "Personas are deterministic rendering policies over the same evidence bundle and packets.",
        "persona_truth_policy": "Persona policies must not create separate agents or separate truth paths.",
        "collateral_scope": "Collateral carries forward frozen demo facts, limitations, unresolved/quarantined contexts, and non-blocking gaps.",
        "capture_dependency": "Final video/collateral capture should wait until Persona R1 is green.",
        "parallel_lanes": "Track A and Track D may be future/deepening lanes, but they are not Track P dependencies.",
        "boundary": BOUNDARY,
        "non_blocking_gaps": facts["non_blocking_gaps"],
        "unresolved_quarantined_preserved_count": facts["unresolved_quarantined_preserved_count"],
    }
    validation_plan = {
        "task_name": TASK_NAME,
        "checks": [
            "required upstreams discovered",
            "frozen demo status is green",
            "integration readiness review is green",
            "non-blocking gaps copied forward",
            "no production/public API/certified twin/live/action claim",
            "no upstream mutation",
            "no secrets",
            "hash manifest validates generated artifacts",
        ],
    }

    write_json(P0_ROOT / "UPSTREAM_DISCOVERY.json", upstreams)
    write_json(P0_ROOT / "FROZEN_DEMO_FACTS.json", facts)
    write_json(P0_ROOT / "TRACK_P_SCOPE_CONTRACT.json", scope_contract)
    write_json(P0_ROOT / "VALIDATION_PLAN.json", validation_plan)
    write_text(
        P0_ROOT / "PERSONA_RENDERING_SCOPE.md",
        f"""# Persona Rendering Scope

{BOUNDARY}

Personas are deterministic rendering policies over the same frozen evidence, packets, limitations, unresolved/quarantined contexts, and claim boundaries.

They differ only in framing, level of detail, and recommended view emphasis. They are not agents, autonomous actors, or separate truth paths.

Required Persona R1 policies: Executive, Operator, Planner, Analyst.
""",
    )
    write_text(
        P0_ROOT / "COLLATERAL_SCOPE.md",
        f"""# Collateral Scope

{BOUNDARY}

Track P packages the frozen Hero Neighbourhood Control Room Reference Demo into outward-facing walkthrough and handoff materials.

It does not build platform functionality, mutate upstreams, add action/governance semantics, or depend on Track A or Track D.
""",
    )
    gaps_md = "\n".join(f"- {gap}" for gap in facts["non_blocking_gaps"])
    write_text(
        P0_ROOT / "NON_BLOCKING_GAPS_CARRY_FORWARD.md",
        f"""# Non-Blocking Gaps Carry Forward

The following non-blocking gaps are carried forward unchanged:

{gaps_md}

Blocking gaps: `{facts['blocking_gaps_count']}`.
""",
    )
    write_text(
        P0_ROOT / "CLAIM_LABEL_BASELINE.md",
        f"""# Claim Label Baseline

{BOUNDARY}

- Claim class: bounded local/replay review/query context only.
- Visual acceptance: `{facts['visual_acceptance_status']}`.
- Unresolved/quarantined contexts preserved: `{facts['unresolved_quarantined_preserved_count']}`.
- Certified citywide twin claim: no.
- Production/live/action claim: no.
""",
    )

    status = PASS_STATUS if upstream_summary["status"] == "PASS" and facts["demo_status"] and facts["integration_readiness_status"] else FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(P0_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "upstream_discovery_count": upstream_summary["required_upstreams_found"],
        "required_upstreams_total": upstream_summary["required_upstreams_total"],
        "missing_upstream_count": upstream_summary["missing_or_not_green_count"],
        "missing_or_not_green": upstream_summary["missing_or_not_green"],
        "frozen_demo_facts_summary": facts,
        "blocking_gaps_count": 0 if status == PASS_STATUS else upstream_summary["missing_or_not_green_count"],
        "non_blocking_gaps_count": facts["non_blocking_gaps_count"],
        "recommended_next_task": "MAIN-CITYBRAIN-D6-PERSONA-RENDERING-POLICIES-R1" if status == PASS_STATUS else TASK_NAME + "-FIXUP",
        "boundary": BOUNDARY,
    }
    write_json(P0_ROOT / DECISION_NAME, decision)
    write_text(
        P0_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{status}`

This preflight establishes Track P as a packaging/persona/collateral lane over the frozen Hero Neighbourhood demo.

{facts_markdown(facts)}

Recommended next task: `{decision['recommended_next_task']}`.
""",
    )
    write_local_index(P0_ROOT, TASK_NAME, status, REQUIRED, "Open this file first, then review the scope contract and frozen demo facts.")

    audits = run_standard_audits(P0_ROOT, TASK_NAME, before, BASE_REQUIRED_UPSTREAMS, REQUIRED)
    if not audits["all_pass"]:
        decision["status"] = FAIL_STATUS
        decision["blocking_gaps_count"] += len(audits["required_missing"])
        decision["recommended_next_task"] = TASK_NAME + "-FIXUP"
    decision.update(audits)
    decision = write_decision_last(P0_ROOT, DECISION_NAME, decision, TASK_NAME)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

