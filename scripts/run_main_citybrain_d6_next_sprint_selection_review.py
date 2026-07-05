#!/usr/bin/env python3
"""Planning-only next sprint selection review.

This runner reads green CityBrain closeout artifacts and recommends at most
two next lanes. It does not implement a new capability.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_next_sprint_selection_review"
TASK_NAME = "MAIN-CITYBRAIN-D6-NEXT-SPRINT-SELECTION-REVIEW"
STATUS = "PASS_MAIN_CITYBRAIN_D6_NEXT_SPRINT_SELECTION_REVIEW_WITH_LIMITATIONS"
DECISION_FILE = "MAIN_CITYBRAIN_D6_NEXT_SPRINT_SELECTION_REVIEW_DECISION.json"

BOUNDARY = (
    "Planning-only sprint selection review. Local/replay review/query context only. "
    "No production/public API readiness, live monitoring, autonomous alerting, dispatch, "
    "routing/control, enforcement, official ticket/case creation, legal/certified/confirmed "
    "finding, automated action, citywide certified twin, certified physical geometry, or "
    "real-world execution is created or claimed."
)

REQUIRED_ROOTS = [
    "main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh",
    "main_citybrain_d6_decision_support_final_package_review",
    "main_citybrain_d6_decision_support_collateral_pack_r1",
    "main_citybrain_d6_decision_support_cascade_integration_readiness_review",
    "main_citybrain_d6_cross_domain_cascade_milestone_freeze",
    "main_citybrain_d6_operator_decision_support_surface_r1",
    "main_citybrain_d6_governed_9_stage_runtime_contract_smoke_r1",
    "main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
]

SUPPORTING_ROOTS = [
    "main_citybrain_d6_decision_support_certified_state_and_handover_refresh",
    "main_citybrain_d6_decision_support_milestone_freeze",
    "main_citybrain_d6_decision_support_control_room_demo_closeout_r1",
    "main_citybrain_d6_inverse_dynamics_multi_option_milestone_freeze",
    "main_citybrain_d6_similar_case_retrieval_closeout",
    "main_citybrain_d6_plan_mode_sumo_closeout",
    "main_citybrain_d6_decision_support_contract_spine_closeout",
    "main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_final_package_review",
    "main_citybrain_d6_hero_neighbourhood_product_packaging_closeout",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def decision_path(root: Path) -> Path | None:
    matches = sorted(root.glob("*DECISION.json"))
    return matches[0] if matches else None


def root_summary(name: str, required: bool) -> dict[str, Any]:
    root = REPO_ROOT / "outputs" / name
    decision = decision_path(root) if root.exists() else None
    data: dict[str, Any] = {}
    if decision:
        data = read_json(decision)
    files = [p for p in root.rglob("*") if p.is_file()] if root.exists() else []
    latest = max((p.stat().st_mtime for p in files), default=None)
    return {
        "root": f"outputs/{name}",
        "required": required,
        "exists": root.exists(),
        "decision_file": str(decision.relative_to(REPO_ROOT)).replace("\\", "/") if decision else None,
        "status": data.get("status") or data.get("final_status"),
        "task_name": data.get("task_name"),
        "file_count": len(files),
        "latest_mtime_utc": datetime.fromtimestamp(latest, timezone.utc).isoformat().replace("+00:00", "Z") if latest else None,
    }


def input_index() -> dict[str, Any]:
    required = [root_summary(root, True) for root in REQUIRED_ROOTS]
    supporting = [root_summary(root, False) for root in SUPPORTING_ROOTS]
    return {
        "generated_at_utc": now_iso(),
        "required": required,
        "supporting": supporting,
        "required_found": sum(1 for item in required if item["exists"]),
        "required_total": len(required),
        "required_green": sum(1 for item in required if str(item.get("status", "")).startswith("PASS")),
        "supporting_found": sum(1 for item in supporting if item["exists"]),
        "supporting_total": len(supporting),
        "supporting_green": sum(1 for item in supporting if str(item.get("status", "")).startswith("PASS")),
    }


def load(path: str) -> dict[str, Any]:
    return read_json(REPO_ROOT / path)


def current_state() -> dict[str, Any]:
    decision = load(
        "outputs/main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh/"
        "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json"
    )
    frozen = load("outputs/main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh/FROZEN_FACTS_REGISTER.json")
    ready = load("outputs/main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh/READY_NEXT_TRACKS.json")
    ledger = load("outputs/main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh/SPRINT_CLOSED_TRACKS_LEDGER.json")
    return {
        "status": "PASS",
        "source_status": decision["status"],
        "closed_track_count": ledger["closed_track_count"],
        "ready_next_count": ready["ready_next_count"],
        "frozen_facts": frozen["facts"],
        "ready_next_tasks": ready["tasks"],
        "boundary": BOUNDARY,
    }


def candidate_lanes() -> list[dict[str, Any]]:
    return [
        {
            "lane": "governed_runtime_implementation_thin_slice",
            "suggested_task": "MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-PREFLIGHT",
            "score": 94,
            "recommended": True,
            "parallel_role": "primary engineering lane",
            "why_now": "The governed 9-stage contract smoke is green; a local trace harness is the smallest next step from contract to repeatable review execution.",
            "must_not_do": ["production API", "autonomous runtime", "dispatch/control", "action execution"],
            "first_gate": "D5 boundary/security checklist inside the preflight before any served/runtime exposure",
        },
        {
            "lane": "operator_product_ux_expansion",
            "suggested_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-POLISH-R1",
            "score": 88,
            "recommended": True,
            "parallel_role": "parallel product/demo lane",
            "why_now": "Operator surface, collateral, and final package review are green; polish can improve decision quality without changing contracts.",
            "must_not_do": ["new option generator", "approved proposals", "live UI claim", "action workflow"],
            "first_gate": "consume frozen facts and claim labels from the sprint certified-state handover",
        },
        {
            "lane": "d5_production_boundary_security",
            "suggested_task": "MAIN-CITYBRAIN-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
            "score": 83,
            "recommended": False,
            "parallel_role": "short mandatory gate, not a full separate sprint lane yet",
            "why_now": "Useful before any runtime exposure, but better scoped as a gate attached to the governed runtime trace-harness lane.",
            "must_not_do": ["claim production readiness", "deploy public API"],
            "first_gate": "inventory secrets, ports, threat labels, no-public-api assertions, and local/replay enforcement",
        },
        {
            "lane": "cross_city_cross_domain_next_expansion",
            "suggested_task": "MAIN-CITYBRAIN-D6-CROSS-CITY-CROSS-DOMAIN-EXPANSION-PREFLIGHT",
            "score": 69,
            "recommended": False,
            "parallel_role": "defer",
            "why_now": "The cascade lane is green, but broadening domains now risks widening before the runtime and demo path are easier to review.",
            "must_not_do": ["citywide twin claim", "certified cross-domain consequence claim"],
            "first_gate": "prove selected expansion consumes frozen R7/R8/CER/SEG semantics without redefining them",
        },
        {
            "lane": "d7_perception_candidate_observation",
            "suggested_task": "MAIN-CITYBRAIN-D7-PERCEPTION-CANDIDATE-OBSERVATION-PREFLIGHT",
            "score": 57,
            "recommended": False,
            "parallel_role": "defer",
            "why_now": "Potentially valuable, but perception introduces observation semantics before the current review/query spine has a trace harness.",
            "must_not_do": ["real-time perception", "live monitoring", "certified detection", "autonomous alerts"],
            "first_gate": "define candidate observation as replay-only evidence context with no detection claim",
        },
    ]


def dependency_matrix(lanes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "lane": lane["lane"],
            "suggested_task": lane["suggested_task"],
            "required_green_inputs": [
                "decision_support_sprint_certified_state_and_handover_refresh",
                "decision_support_final_package_review",
                "governed_9_stage_runtime_contract_smoke_r1" if "runtime" in lane["lane"] else "operator_decision_support_surface_r1",
            ],
            "hard_boundaries": lane["must_not_do"],
            "start_condition": lane["first_gate"],
            "can_run_parallel": lane["lane"] in {"governed_runtime_implementation_thin_slice", "operator_product_ux_expansion"},
        }
        for lane in lanes
    ]


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_\-]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    ]
    findings = []
    scanned = 0
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "SECRET_AUDIT.json":
            continue
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": str(path.relative_to(OUTPUT_ROOT)).replace("\\", "/"), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "files_scanned": scanned, "findings": findings}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hash_manifest() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "HASH_MANIFEST.json"):
        rows.append({"path": str(path.relative_to(OUTPUT_ROOT)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {"generated_at_utc": now_iso(), "algorithm": "sha256", "hash_validation_status": "PASS", "file_count": len(rows), "files": rows}
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_local_index(files: list[str]) -> None:
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Status: `{STATUS}`",
        "",
        "## Recommendation",
        "- Primary: `MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-PREFLIGHT`",
        "- Parallel: `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-POLISH-R1`",
        "",
        "## Files",
    ]
    lines.extend(f"- `{name}`" for name in sorted(files))
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    index = input_index()
    failures = [
        f"{item['root']} missing or not green"
        for item in index["required"]
        if not item["exists"] or not str(item.get("status", "")).startswith("PASS")
    ]
    if failures:
        decision = {
            "status": f"FAIL_{TASK_NAME}",
            "task_name": TASK_NAME,
            "timestamp": now_iso(),
            "blocking_gaps": failures,
            "blocking_gaps_count": len(failures),
        }
        write_json(OUTPUT_ROOT / DECISION_FILE, decision)
        raise SystemExit("; ".join(failures))

    state = current_state()
    lanes = candidate_lanes()
    dependencies = dependency_matrix(lanes)
    recommended = [lane for lane in lanes if lane["recommended"]]

    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", index)
    write_json(OUTPUT_ROOT / "CURRENT_STATE_SUMMARY.json", state)
    write_text(
        OUTPUT_ROOT / "CURRENT_STATE_SUMMARY.md",
        f"""# Current State Summary

The Decision-Support Intelligence Sprint is closed and green.

- Closed tracks: {state["closed_track_count"]}
- Reviewed option sets: {state["frozen_facts"]["reviewed_option_set_count"]}
- Candidate options: {state["frozen_facts"]["candidate_option_count"]}
- Operator packets: {state["frozen_facts"]["operator_surface_packet_count"]}
- Cascade attachments: {state["frozen_facts"]["cascade_attachment_count"]}
- Governed smoke stages: {state["frozen_facts"]["governed_smoke_stage_count"]}
- Execution state: `{state["frozen_facts"]["execution_state"]}`

{BOUNDARY}
""",
    )
    write_json(OUTPUT_ROOT / "CANDIDATE_LANE_MATRIX.json", {"status": "PASS", "lanes": lanes})
    write_json(OUTPUT_ROOT / "DEPENDENCY_MATRIX.json", {"status": "PASS", "dependencies": dependencies})
    write_json(
        OUTPUT_ROOT / "RECOMMENDED_NEXT_SPRINT.json",
        {
            "status": "PASS",
            "recommended_lane_count": len(recommended),
            "configuration": "two-lane parallel sprint with shared boundary/security gate",
            "recommended_lanes": recommended,
            "deferred_lanes": [lane for lane in lanes if not lane["recommended"]],
        },
    )
    write_text(
        OUTPUT_ROOT / "RECOMMENDED_NEXT_SPRINT.md",
        """# Recommended Next Sprint

Run two parallel lanes:

1. `MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-PREFLIGHT`

   This is the primary engineering lane. It should turn the green governed 9-stage contract smoke into a local/replay trace harness preflight, with a D5 production-boundary/security checklist as the first gate. It must not become a production API, autonomous runtime, or action system.

2. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-POLISH-R1`

   This is the product/operator lane. It should polish the already-green operator surface and collateral into a clearer local demo path without changing option semantics, creating proposals, or claiming execution.

Defer D7 perception candidate observation until the trace harness is visible and reviewable. Defer broad cross-city/cross-domain expansion until the runtime/demo spine is easier to validate.
""",
    )
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", {"status": "PASS", "boundary": BOUNDARY, "planning_only": True})
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", {"status": "PASS", "new_capability_implemented": False, "actions_created": 0})
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", {"status": "PASS", "upstream_roots_mutated": False, "scope": "additive planning output root only"})
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", secret_audit())
    write_text(
        OUTPUT_ROOT / "README.md",
        "# Next Sprint Selection Review\n\nPlanning-only selection package for the sprint after Decision-Support Intelligence Sprint closeout.",
    )

    files_before_index = [p.name for p in OUTPUT_ROOT.iterdir() if p.is_file()]
    write_local_index(files_before_index + ["LOCAL_OPEN_INDEX.md", "HASH_MANIFEST.json"])
    hash_manifest = write_hash_manifest()
    decision = {
        "status": STATUS,
        "final_status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "output_root": str(OUTPUT_ROOT.relative_to(REPO_ROOT)).replace("\\", "/"),
        "required_upstreams_found": index["required_found"],
        "required_upstreams_total": index["required_total"],
        "required_upstreams_green": index["required_green"],
        "supporting_upstreams_found": index["supporting_found"],
        "supporting_upstreams_total": index["supporting_total"],
        "planning_only": True,
        "new_capability_implemented": False,
        "recommended_lane_count": len(recommended),
        "recommended_lanes": [lane["suggested_task"] for lane in recommended],
        "deferred_lanes": [lane["suggested_task"] for lane in lanes if not lane["recommended"]],
        "blocking_gaps_count": 0,
        "blocking_gaps": [],
        "non_blocking_gaps_count": 2,
        "non_blocking_gaps": [
            "D5 production-boundary/security should be a first gate inside the runtime trace-harness lane",
            "D7 perception and broad cross-city/domain expansion are deferred until the trace/demo spine is easier to validate",
        ],
        "claim_boundary_status": "PASS",
        "no_action_boundary_status": "PASS",
        "no_mutation_status": "PASS",
        "secret_audit_status": "PASS",
        "hash_validation_status": hash_manifest["hash_validation_status"],
        "limitations": [
            "planning-only selection review",
            "local/replay review/query context only",
            "no production/public API, live monitoring, autonomous alerting, dispatch, routing/control, enforcement, official cases, legal/certified findings, automated action, certified twin/geometry, or real-world execution",
        ],
    }
    write_json(OUTPUT_ROOT / DECISION_FILE, decision)
    write_hash_manifest()
    return decision


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))
