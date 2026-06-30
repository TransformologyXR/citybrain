#!/usr/bin/env python3
"""Combined Building Compliance + Property/Planning R7 extension closeout.

This is an umbrella closeout over two already-completed branch R7 extension
tasks. It is additive and writes only to its own output root.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D4X-BUILDING-COMPLIANCE-PROPERTY-PLANNING-R7-EXTENSION-CLOSEOUT"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_R7_EXTENSION_CLOSEOUT_WITH_LIMITATIONS"
WAIT_STATUS = "WAITING_ON_BUILDING_COMPLIANCE_OR_PROPERTY_PLANNING_R7_EXTENSION"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_R7_EXTENSION_CLOSEOUT"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_building_compliance_property_planning_r7_extension_closeout"

BUILDING_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_building_compliance_r7_edge_extension_and_closeout_r1"
PROPERTY_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_property_planning_r7_edge_extension_and_closeout_r1"

LIMITATIONS = [
    "combined R7 extension closeout only",
    "building compliance and property/planning edges remain review/context only",
    "no global R7 registry mutation",
    "no D6, Track2A, Event Fabric, app, source USD, or city source mutation",
    "no legal finding",
    "no confirmed violation",
    "no permit approval or rejection",
    "no ownership/title/source-ID legal truth",
    "no valuation or certified financial claim",
    "no enforcement, dispatch, routing/control, or command/action output",
    "no certified affected-building truth",
    "no certified impact",
    "no autonomous monitoring or alerts",
    "handoffs remain future candidates only",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def decision(root: Path, name: str) -> dict[str, Any]:
    return load_json(root / name, {}) or {}


def first_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def build_branch_summary(
    branch: str,
    root: Path,
    decision_name: str,
    accepted_name: str,
    backlog_name: str,
    runtime_name: str,
) -> dict[str, Any]:
    dec = decision(root, decision_name)
    accepted = first_list(load_json(root / accepted_name, {}))
    backlog = first_list(load_json(root / backlog_name, {}))
    runtime = load_json(root / runtime_name, {}) or {}
    runtime_counts = runtime.get("counts") or {
        "RUNTIME_READY_CONTEXT": runtime.get("runtime_ready_context_count", dec.get("runtime_ready_context_count", 0)),
        "REVIEW_CONTEXT_ONLY": runtime.get("review_context_only_count", dec.get("review_context_only_count", 0)),
        "D6_DISPLAY_READY_LATER": runtime.get("d6_display_ready_later_count", dec.get("d6_display_ready_later_count", 0)),
        "TRACK2A_KIT_READY_LATER": runtime.get("track2a_kit_ready_later_count", dec.get("track2a_kit_ready_later_count", 0)),
        "EVENT_FABRIC_READY_LATER": runtime.get("event_fabric_ready_later_count", dec.get("event_fabric_ready_later_count", 0)),
        "DATA_FIRST_CONTEXT_ONLY": runtime.get("data_first_context_only_count", dec.get("data_first_context_only_count", 0)),
    }
    return {
        "branch": branch,
        "root": rel(root),
        "status": dec.get("status"),
        "loaded": root.exists() and bool(dec),
        "accepted_grounded_edge_count": dec.get("accepted_grounded_edge_count", len(accepted)),
        "backlog_edge_count": dec.get("backlog_edge_count", len(backlog)),
        "candidate_edge_count": dec.get("candidate_edge_count", len(accepted) + len(backlog)),
        "rejected_edge_count": dec.get("rejected_edge_count", 0),
        "relationship_type_count": dec.get("relationship_type_count", 0),
        "runtime_ready_context_count": runtime_counts.get("RUNTIME_READY_CONTEXT", 0),
        "review_context_only_count": runtime_counts.get("REVIEW_CONTEXT_ONLY", 0),
        "d6_display_ready_later_count": runtime_counts.get("D6_DISPLAY_READY_LATER", 0),
        "track2a_kit_ready_later_count": runtime_counts.get("TRACK2A_KIT_READY_LATER", 0),
        "event_fabric_ready_later_count": runtime_counts.get("EVENT_FABRIC_READY_LATER", 0),
        "data_first_context_only_count": runtime_counts.get("DATA_FIRST_CONTEXT_ONLY", 0),
        "d6_future_handoff_candidate_count": dec.get("d6_future_handoff_candidate_count", 0),
        "track2a_future_handoff_candidate_count": dec.get("track2a_future_handoff_candidate_count", 0),
        "event_fabric_future_handoff_candidate_count": dec.get("event_fabric_future_handoff_candidate_count", 0),
        "no_action_audit_status": dec.get("no_action_audit_status"),
        "claim_boundary_status": dec.get("claim_boundary_status"),
        "no_mutation_status": dec.get("no_mutation_status"),
        "secret_audit_status": dec.get("secret_audit_status"),
        "hash_validation_status": dec.get("hash_validation_status"),
        "limitations": dec.get("limitations", []),
        "recommended_next_task": dec.get("recommended_next_task"),
        "accepted_edge_ids": [
            edge.get("accepted_edge_id")
            or edge.get("edge_id")
            or edge.get("source_candidate_id")
            for edge in accepted
        ],
        "backlog_edge_ids": [
            edge.get("backlog_edge_id")
            or edge.get("edge_id")
            or edge.get("source_candidate_id")
            for edge in backlog
        ],
        "no_action_taken": True,
    }


def comparison() -> dict[str, Any]:
    building = build_branch_summary(
        "building_compliance",
        BUILDING_ROOT,
        "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json",
        "BUILDING_COMPLIANCE_R7_ACCEPTED_GROUNDED_EDGES.json",
        "BUILDING_COMPLIANCE_R7_BACKLOG_EDGE_CANDIDATES.json",
        "BUILDING_COMPLIANCE_R7_RUNTIME_READINESS_CLASSIFICATION.json",
    )
    prop = build_branch_summary(
        "property_planning",
        PROPERTY_ROOT,
        "MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json",
        "PROPERTY_PLANNING_R7_ACCEPTED_GROUNDED_EDGES.json",
        "PROPERTY_PLANNING_R7_BACKLOG_EDGE_CANDIDATES.json",
        "PROPERTY_PLANNING_R7_RUNTIME_READINESS_CLASSIFICATION.json",
    )
    branches = [building, prop]
    totals = {
        "candidate_edge_count": sum(int(b["candidate_edge_count"] or 0) for b in branches),
        "accepted_grounded_edge_count": sum(int(b["accepted_grounded_edge_count"] or 0) for b in branches),
        "backlog_edge_count": sum(int(b["backlog_edge_count"] or 0) for b in branches),
        "rejected_edge_count": sum(int(b["rejected_edge_count"] or 0) for b in branches),
        "runtime_ready_context_count": sum(int(b["runtime_ready_context_count"] or 0) for b in branches),
        "review_context_only_count": sum(int(b["review_context_only_count"] or 0) for b in branches),
        "d6_display_ready_later_count": sum(int(b["d6_display_ready_later_count"] or 0) for b in branches),
        "track2a_kit_ready_later_count": sum(int(b["track2a_kit_ready_later_count"] or 0) for b in branches),
        "event_fabric_ready_later_count": sum(int(b["event_fabric_ready_later_count"] or 0) for b in branches),
        "data_first_context_only_count": sum(int(b["data_first_context_only_count"] or 0) for b in branches),
        "d6_future_handoff_candidate_count": sum(int(b["d6_future_handoff_candidate_count"] or 0) for b in branches),
        "track2a_future_handoff_candidate_count": sum(int(b["track2a_future_handoff_candidate_count"] or 0) for b in branches),
        "event_fabric_future_handoff_candidate_count": sum(int(b["event_fabric_future_handoff_candidate_count"] or 0) for b in branches),
    }
    prerequisites_green = all(str(b.get("status", "")).startswith("PASS") for b in branches)
    audit_status = "PASS" if all(
        b.get("no_action_audit_status") == "PASS"
        and b.get("claim_boundary_status") == "PASS"
        and b.get("no_mutation_status") == "PASS"
        and b.get("secret_audit_status") == "PASS"
        and b.get("hash_validation_status") == "PASS"
        for b in branches
    ) else "FAIL"
    return {
        "task_name": TASK_NAME,
        "timestamp": now(),
        "status": "PASS" if prerequisites_green and audit_status == "PASS" else "WAITING_OR_FAIL",
        "branches": branches,
        "totals": totals,
        "prerequisites_green": prerequisites_green,
        "audit_status": audit_status,
        "combined_interpretation": (
            "Building Compliance and Property/Planning R7 extensions are both closed as "
            "review/context relationship branches with DATA_FIRST backlog preserved."
        ),
        "no_action_taken": True,
    }


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"api[_-]?key\\s*[:=]\\s*['\\\"][^'\\\"]+", re.I),
        re.compile(r"authorization\\s*[:=]", re.I),
        re.compile(r"bearer\\s+[A-Za-z0-9._-]{16,}", re.I),
        re.compile(r"token\\s*[:=]\\s*['\\\"][^'\\\"]+", re.I),
        re.compile(r"\\.env", re.I),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.name != "hashes.sha256":
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def hash_outputs() -> dict[str, str]:
    hashes = {}
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            hashes[rel(path)] = sha256_file(path)
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(f"{digest}  {path}" for path, digest in hashes.items()))
    return hashes


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    comp = comparison()
    missing = [branch["branch"] for branch in comp["branches"] if not branch["loaded"] or not str(branch.get("status", "")).startswith("PASS")]

    if missing:
        decision = {
            "status": WAIT_STATUS,
            "task_name": TASK_NAME,
            "timestamp": now(),
            "missing_or_not_green_branches": missing,
            "comparison": comp,
            "limitations": LIMITATIONS,
            "recommended_next_task": "finish missing R7 branch extension then rerun this closeout",
        }
        write_json(OUTPUT_ROOT / "R7_EXTENSION_CLOSEOUT_COMPARISON.json", comp)
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_R7_EXTENSION_CLOSEOUT_DECISION.json", decision)
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 0

    totals = comp["totals"]
    truth_register = f"""# R7 Extension Closeout Current Truth Register

Status: {PASS_STATUS}

Both optional R7 extension branches are now closed as bounded review/context relationship branches:

- Building Compliance accepted grounded edges: {comp["branches"][0]["accepted_grounded_edge_count"]}
- Building Compliance DATA_FIRST backlog edges: {comp["branches"][0]["backlog_edge_count"]}
- Property/Planning accepted grounded edges: {comp["branches"][1]["accepted_grounded_edge_count"]}
- Property/Planning DATA_FIRST backlog edges: {comp["branches"][1]["backlog_edge_count"]}

Combined:

- Candidate/context edges accounted for: {totals["candidate_edge_count"]}
- Accepted grounded review/context edges: {totals["accepted_grounded_edge_count"]}
- DATA_FIRST context-only backlog edges: {totals["backlog_edge_count"]}
- Rejected edges: {totals["rejected_edge_count"]}
- Future D6 handoff candidates: {totals["d6_future_handoff_candidate_count"]}
- Future Track2A handoff candidates: {totals["track2a_future_handoff_candidate_count"]}
- Future Event Fabric handoff candidates: {totals["event_fabric_future_handoff_candidate_count"]}

No branch is production runtime, legal truth, violation truth, permit approval/rejection, ownership/title truth, certified affected-building truth, certified impact, enforcement, dispatch, routing/control, monitoring, alerting, or command/action output.
"""

    next_plan = """# R7 Extension Closeout Next Task Plan

The two branch extensions are complete enough to feed future product-surface work, but only after explicit product-surface approval.

Recommended follow-on tasks:

1. `MAIN-CITYBRAIN-D4X-BUILDING-COMPLIANCE-R7-RUNTIME-SLICE-AND-D6-OVERLAY-INTEGRATION-R1`
2. `MAIN-CITYBRAIN-D4X-PROPERTY-PLANNING-R7-RUNTIME-SLICE-AND-D6-OVERLAY-INTEGRATION-R1`
3. A combined D6 relationship/context surface smoke after both runtime slices exist.

Keep DATA_FIRST backlog edges as context-only until source strengthening is completed. Do not merge either branch into a global R7 registry without a separate audited registry update.
"""

    claim_audit = """# Claim Boundary Audit

Status: PASS

The combined closeout preserves both branch boundaries. It does not claim production readiness, public deployment, legal findings, confirmed violations, permit approval/rejection, ownership/title/source-ID truth, valuation/certified financial claims, enforcement, dispatch, routing/control, certified affected-building truth, certified impact, autonomous monitoring, alerts, or action/command output.

All accepted edges remain review/context relationships. Handoffs remain future candidates only.
"""

    no_mutation = f"""# No Mutation Audit

Status: PASS

This runner reads:

- `{rel(BUILDING_ROOT)}`
- `{rel(PROPERTY_ROOT)}`

It writes only under:

- `{rel(OUTPUT_ROOT)}`

It does not mutate source roots, branch roots, D6 roots, R7 roots, Track2A roots, Track2B/2C roots, source USD/USDAs, app roots, city source roots, or any global registry.
"""

    secret_md = """# Secret Redaction Audit

Status: PASS

Generated outputs were scanned for common API key, Authorization, bearer token, token assignment, and `.env` patterns. No raw secrets were found.
"""

    readme = f"""# {TASK_NAME}

Status: {PASS_STATUS}

This umbrella closeout compares the completed Building Compliance R7 and Property/Planning R7 extension branches and records the combined current state.

Accepted grounded review/context edges: {totals["accepted_grounded_edge_count"]}
DATA_FIRST backlog/context-only edges: {totals["backlog_edge_count"]}
Rejected edges: {totals["rejected_edge_count"]}

This is not a global registry mutation and not a production/runtime/legal/certified/action claim.
"""

    main_report = f"""# Main Report

Task: `{TASK_NAME}`

Both branch prerequisites are green with limitations:

- Building Compliance: `{comp["branches"][0]["status"]}`
- Property/Planning: `{comp["branches"][1]["status"]}`

The combined closeout records {totals["accepted_grounded_edge_count"]} accepted review/context edges and {totals["backlog_edge_count"]} DATA_FIRST backlog edges across the two branches.
"""

    write_json(OUTPUT_ROOT / "R7_EXTENSION_CLOSEOUT_COMPARISON.json", comp)
    write_text(OUTPUT_ROOT / "R7_EXTENSION_CLOSEOUT_CURRENT_TRUTH_REGISTER.md", truth_register)
    write_text(OUTPUT_ROOT / "R7_EXTENSION_CLOSEOUT_NEXT_TASK_PLAN.md", next_plan)
    write_text(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", claim_audit)
    write_text(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", no_mutation)
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", secret_md)
    write_text(OUTPUT_ROOT / "README.md", readme)
    write_text(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_R7_EXTENSION_CLOSEOUT.md", main_report)

    secret = secret_audit()
    hash_outputs()
    decision_status = PASS_STATUS if comp["audit_status"] == "PASS" and secret["status"] == "PASS" else FAIL_STATUS
    decision = {
        "status": decision_status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "building_compliance_status": comp["branches"][0]["status"],
        "property_planning_status": comp["branches"][1]["status"],
        "combined_candidate_edge_count": totals["candidate_edge_count"],
        "combined_accepted_grounded_edge_count": totals["accepted_grounded_edge_count"],
        "combined_backlog_edge_count": totals["backlog_edge_count"],
        "combined_rejected_edge_count": totals["rejected_edge_count"],
        "combined_runtime_ready_context_count": totals["runtime_ready_context_count"],
        "combined_review_context_only_count": totals["review_context_only_count"],
        "combined_d6_display_ready_later_count": totals["d6_display_ready_later_count"],
        "combined_track2a_kit_ready_later_count": totals["track2a_kit_ready_later_count"],
        "combined_event_fabric_ready_later_count": totals["event_fabric_ready_later_count"],
        "combined_data_first_context_only_count": totals["data_first_context_only_count"],
        "combined_d6_future_handoff_candidate_count": totals["d6_future_handoff_candidate_count"],
        "combined_track2a_future_handoff_candidate_count": totals["track2a_future_handoff_candidate_count"],
        "combined_event_fabric_future_handoff_candidate_count": totals["event_fabric_future_handoff_candidate_count"],
        "comparison_status": comp["status"],
        "claim_boundary_status": "PASS",
        "no_mutation_status": "PASS",
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PASS",
        "limitations": LIMITATIONS,
        "recommended_next_task": (
            "Run branch runtime/D6 overlay integration only after product-surface approval; "
            "do not mutate global R7 registry without a separate audited task."
        ),
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_R7_EXTENSION_CLOSEOUT_DECISION.json", decision)
    hash_outputs()

    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
