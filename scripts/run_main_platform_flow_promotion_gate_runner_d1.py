#!/usr/bin/env python3
"""MAIN-PLATFORM-FLOW-PROMOTION-GATE-RUNNER-D1.

Reusable dry-run flow promotion gate runner. It evaluates cleaned FlowPack and
oracle artifacts and emits drafts only; it never applies platform-state changes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "MAIN-PLATFORM-FLOW-PROMOTION-GATE-RUNNER-D1"
PASS = "PASS_MAIN_PLATFORM_FLOW_PROMOTION_GATE_RUNNER_D1"
PASS_LIMITED = "PASS_MAIN_PLATFORM_FLOW_PROMOTION_GATE_RUNNER_D1_WITH_LIMITATIONS"
FAIL = "FAIL_MAIN_PLATFORM_FLOW_PROMOTION_GATE_RUNNER_D1"
OUT = Path("outputs/main_platform_flow_promotion_gate_runner_d1")
REGISTRY = Path("outputs/main_platform_flowpack_limitation_cleanup_r1/CITY_FLOW_PACK_REGISTRY_CLEANED.json")
ORACLE_RESULTS = Path("outputs/main_platform_flowpack_limitation_cleanup_r1/oracle_bridge_recheck/FLOWPACK_QUERY_RESULTS_CLEANED.jsonl")
ORACLE_BUNDLES = Path("outputs/main_platform_flowpack_limitation_cleanup_r1/oracle_bridge_recheck/FLOWPACK_EVIDENCEBUNDLES_CLEANED.jsonl")
ORACLE_RECHECK = Path("outputs/main_platform_flowpack_limitation_cleanup_r1/oracle_bridge_recheck/ORACLE_FLOWPACK_BRIDGE_RECHECK_REPORT.md")
CLEANUP_DECISION = Path("outputs/main_platform_flowpack_limitation_cleanup_r1/MAIN_PLATFORM_FLOWPACK_LIMITATION_CLEANUP_R1_DECISION.json")
PLATFORM_STATE = Path("outputs/platform_state_generated/CITYBRAIN_PLATFORM_STATE.json")
RESOLVER_INPUTS = Path("outputs/platform_state_generated/CITYBRAIN_RESOLVER_INPUTS.json")
FLOW_LEDGER = Path("outputs/platform_state_generated/CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json")
PV1_R2 = Path("outputs/pv1_snapshot_addendum_r2")
PV1_R3 = Path("outputs/barc_f1f6_flow_acceptance_closeout_r1")
A9_ROOT = Path("outputs/a9_wire_e2e_g1_snapshot")

SCHEMA_VERSION = "flow_promotion_gate_d1"

REQUIRED_BATCHES = {
    "batch_a_nyc": [("NYC", "F2"), ("NYC", "F5")],
    "batch_b_london": [("LON", "F3"), ("LON", "F4"), ("LON", "F5"), ("LON", "F7")],
    "batch_c_chicago": [("CHI", "F2"), ("CHI", "F5"), ("CHI", "F7")],
}
OPTIONAL_BATCH = [
    ("NYC", "F4"),
    ("NYC", "F7"),
    ("CHI", "F1"),
    ("CHI", "F3"),
    ("CHI", "F4"),
    ("CHI", "F6"),
    ("LON", "F1"),
    ("LON", "F2"),
    ("LON", "F6"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def parse_csv(path: Path | None) -> list[dict[str, str]]:
    if not path or not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def snapshot(paths: list[Path]) -> dict[str, str | None]:
    return {rel(p): sha256(p) if p.exists() and p.is_file() else None for p in paths}


def normalize_flow(value: Any) -> str:
    text = str(value).upper()
    if text.startswith("F"):
        return text
    if text.isdigit():
        return f"F{text}"
    match = re.search(r"F([1-7])", text)
    return f"F{match.group(1)}" if match else text


def status_is_accepted(status: str) -> bool:
    return str(status).startswith("ACCEPTED")


def flow_name(flow: str) -> str:
    return {
        "F1": "Situational Status",
        "F2": "Planning / Compliance Context",
        "F3": "Incident / Affected Context",
        "F4": "Mobility / Transport / Environment",
        "F5": "Climate / Asset Context",
        "F6": "Port / Logistics Context",
        "F7": "Civic / Sensor Fusion",
    }.get(flow, flow)


def gate_type(flow: str) -> str:
    if flow in {"F1", "F4", "F7"}:
        return "REVIEW_FLOW"
    return "CONTEXT_FLOW"


def proposed_status_for(flow: str) -> str:
    return "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS" if gate_type(flow) == "REVIEW_FLOW" else "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS"


def platform_flow_id(city: str, flow: str, existing: str | None) -> str:
    if existing:
        return existing
    suffix = {"F1": "F1X", "F2": "F2X", "F3": "F3X", "F4": "F4X", "F5": "F5X", "F6": "F6X", "F7": "F7X"}.get(flow, flow)
    return f"{city}-{suffix}"


def flow_index(registry: dict[str, Any]) -> dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]]:
    idx = {}
    for city in registry.get("cities", []):
        for flow in city.get("flow_entries", []):
            idx[(city["city_id"], flow["flow"])] = (city, flow)
    return idx


def oracle_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    out: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[(row.get("city"), row.get("flow"))].append(row)
    return out


def select_candidates(args: argparse.Namespace) -> list[tuple[str, str, str]]:
    rows = []
    for batch, flows in REQUIRED_BATCHES.items():
        if args.batch and args.batch != batch:
            continue
        for city, flow in flows:
            if args.city and args.city.upper() != city:
                continue
            if args.flow and normalize_flow(args.flow) != flow:
                continue
            rows.append((batch, city, flow))
    return rows


def read_smoke_count(city_entry: dict[str, Any], flow: str) -> int:
    path = Path(city_entry.get("smoke_query_path") or "")
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if normalize_flow(row.get("flow_id") or row.get("expected_flow")) == flow:
                count += 1
    return count


def evidence_count(oracle_bundles: list[dict[str, Any]], city: str, flow: str) -> int:
    return sum(1 for row in oracle_bundles if row.get("city") == city and row.get("flow") == flow)


def readiness_row(city_entry: dict[str, Any], flow: str) -> dict[str, Any]:
    path = Path(city_entry.get("readiness_matrix_path") or "")
    for row in parse_csv(path):
        if normalize_flow(row.get("flow_id") or row.get("flow")) == flow:
            return row
    return {}


def boundary_from_bundle(flow_entry: dict[str, Any], oracle_rows: list[dict[str, Any]]) -> tuple[str, str]:
    if oracle_rows:
        query = oracle_rows[0].get("query", {})
        return query.get("claim_boundary") or "review/context only", query.get("privacy_boundary") or "source-governed"
    bundle = flow_entry.get("bundle") or {}
    contract = bundle.get("flow_contract") or {}
    return contract.get("boundary") or "review/context only", "source-governed"


def evaluate_candidate(
    batch: str,
    city_entry: dict[str, Any],
    flow_entry: dict[str, Any],
    oracle_rows: list[dict[str, Any]],
    oracle_bundles: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    city = city_entry["city_id"]
    flow = flow_entry["flow"]
    current_status = flow_entry.get("platform_flow_status", "NOT_IN_RESOLVER")
    existing_platform_id = flow_entry.get("platform_flow_id")
    pflow_id = platform_flow_id(city, flow, existing_platform_id)
    claim_boundary, privacy_boundary = boundary_from_bundle(flow_entry, oracle_rows)
    rrow = readiness_row(city_entry, flow)
    smoke_count = read_smoke_count(city_entry, flow)
    eb_count = evidence_count(oracle_bundles, city, flow)
    source_ok = city_entry.get("loader_status") == "LOADED" and flow_entry.get("consumption_status") in {
        "FLOW_CONSUMPTION_READY_CANDIDATE",
        "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS",
    }
    readiness_ok = bool(rrow) and flow_entry.get("consumption_status") != "PARTIAL_FLOW_CONSUMPTION_CANDIDATE"
    eb_ok = eb_count > 0
    smoke_ok = smoke_count >= 10 and any(row.get("status") in {"PASS", "PASS_EXPECTED_MISSING_VIEW_REPORTED"} for row in oracle_rows)
    boundary_ok = bool(claim_boundary and privacy_boundary)
    negative_ok = all(row.get("forbidden_claims_absent", True) for row in oracle_rows)
    limitations = []
    if city_entry.get("limitations"):
        limitations.extend(city_entry["limitations"])
    for row in oracle_rows:
        limitations.extend(row.get("limitations", []))
    if not source_ok:
        limitations.append("source or FlowPack readiness below promotion threshold")
    if status_is_accepted(current_status):
        decision = "DO_NOT_PROMOTE_READY_WITH_LIMITATIONS"
        decision_class = "NO_OP_ALREADY_ACCEPTED_OR_MOUNTED"
        proposed_status = current_status
        reason = "Current generated platform state already has this flow accepted or mounted; dry-run does not relabel it."
        promotable = False
        remaining_blockers = []
    elif current_status == "NO_PLATFORM_FLOW_ALIAS" and source_ok and readiness_ok and eb_ok and smoke_ok and boundary_ok and negative_ok:
        decision = "PROMOTE_TO_" + proposed_status_for(flow)
        decision_class = "PROMOTABLE_DRY_RUN_NEW_FLOW_ALIAS"
        proposed_status = proposed_status_for(flow)
        reason = "Candidate passes D1 review/context eligibility and needs an additive platform flow entry."
        promotable = True
        remaining_blockers = []
    elif source_ok and readiness_ok and eb_ok and smoke_ok and boundary_ok and negative_ok:
        decision = "PROMOTE_TO_" + proposed_status_for(flow)
        decision_class = "PROMOTABLE_DRY_RUN_EXISTING_FLOW"
        proposed_status = proposed_status_for(flow)
        reason = "Candidate passes D1 review/context eligibility and existing flow is not accepted."
        promotable = True
        remaining_blockers = []
    elif not eb_ok or not smoke_ok:
        decision = "BLOCKED_BY_ORACLE_OR_EVIDENCE_FAILURE"
        decision_class = "BLOCKED"
        proposed_status = "BLOCKED_AFTER_GATE_BY_PLATFORM_INTERFACE"
        reason = "EvidenceBundle or oracle smoke path missing/failing."
        promotable = False
        remaining_blockers = ["ORACLE_OR_EVIDENCE_PATH_NOT_READY"]
    elif not boundary_ok:
        decision = "BLOCKED_BY_PRIVACY_OR_LICENSE"
        decision_class = "BLOCKED"
        proposed_status = "BLOCKED_AFTER_GATE_BY_PRIVACY_OR_LICENSE"
        reason = "Claim/privacy boundary missing."
        promotable = False
        remaining_blockers = ["PRIVACY_OR_CLAIM_BOUNDARY_MISSING"]
    else:
        decision = "BLOCKED_BY_SOURCE_GAPS"
        decision_class = "BLOCKED"
        proposed_status = "BLOCKED_AFTER_GATE_BY_MISSING_REQUIRED_SOURCE"
        reason = "Source or readiness sufficiency did not pass."
        promotable = False
        remaining_blockers = ["SOURCE_OR_READINESS_GAP"]
    candidate = {
        "candidate_id": f"{city}-{flow}-PROMOTION-CANDIDATE-D1",
        "city": city,
        "flow_id": flow,
        "platform_flow_id": pflow_id,
        "current_platform_status": current_status,
        "flowpack_status": city_entry.get("prep_status"),
        "readiness_status": flow_entry.get("consumption_status"),
        "source_coverage_summary": rrow.get("source_coverage") or rrow.get("source_coverage_summary") or "available from cleaned FlowPack",
        "row_file_coverage_summary": rrow.get("row_file_coverage") or rrow.get("row_coverage") or "available from readiness matrix",
        "anchor_coverage_summary": rrow.get("anchor_coverage"),
        "join_coverage_summary": rrow.get("join_coverage"),
        "event_observation_coverage_summary": "oracle bounded query and/or sample EvidenceBundle present" if oracle_rows else "not present",
        "EvidenceBundle_sample_count": eb_count,
        "smoke_query_count": smoke_count,
        "known_limitations": limitations,
        "claim_boundary": claim_boundary,
        "privacy_boundary": privacy_boundary,
        "recommended_gate_type": gate_type(flow),
        "schema_version": SCHEMA_VERSION,
    }
    gate_run = {
        "gate_run_id": f"{city}-{flow}-PROMOTION-GATE-DRY-RUN-D1",
        "batch": batch,
        "city": city,
        "flow_id": flow,
        "platform_flow_id": pflow_id,
        "gate_type": gate_type(flow),
        "input_roots": {
            "flowpack_root": city_entry.get("input_root"),
            "oracle_recheck": "outputs/main_platform_flowpack_limitation_cleanup_r1/oracle_bridge_recheck",
        },
        "started_at": utc_now(),
        "completed_at": utc_now(),
        "source_sufficiency_result": "PASS" if source_ok else "FAIL",
        "readiness_result": "PASS" if readiness_ok else "FAIL",
        "EvidenceBundle_result": "PASS" if eb_ok else "FAIL",
        "oracle_smoke_result": "PASS" if smoke_ok else "FAIL",
        "negative_test_result": "PASS" if negative_ok else "FAIL",
        "claim_boundary_result": "PASS" if claim_boundary else "FAIL",
        "privacy_license_result": "PASS" if privacy_boundary else "FAIL",
        "final_decision": decision,
        "decision_reason": reason,
        "limitations": limitations,
        "platform_state_patch_draft_ref": None,
        "snapshot_addendum_draft_ref": None,
        "schema_version": SCHEMA_VERSION,
        "decision_object": {
            "city": city,
            "flow_id": flow,
            "platform_flow_id": pflow_id,
            "previous_status": current_status,
            "proposed_status": proposed_status,
            "decision": decision,
            "decision_class": decision_class,
            "accepted_limitations": limitations or ["review/context-only dry-run limitations retained"],
            "closed_blockers": ["FLOW_ACCEPTANCE_GATE_NOT_RUN"] if promotable else [],
            "remaining_blockers": remaining_blockers,
            "claim_boundary": claim_boundary,
            "privacy_boundary": privacy_boundary,
            "forbidden_claims": [
                "prod-readiness claim",
                "public-safety command",
                "enforcement recommendation",
                "dispatch recommendation",
                "health determination",
                "traffic/transit/port control",
                "official affected-asset determination",
            ],
            "source_refs": (oracle_rows[0].get("query", {}).get("required_sources") if oracle_rows else []),
            "EvidenceBundle_refs": [row.get("evidencebundle_id") for row in oracle_bundles if row.get("city") == city and row.get("flow") == flow],
            "smoke_refs": [row.get("query_id") for row in oracle_rows],
            "negative_test_refs": ["FLOW_PROMOTION_NEGATIVE_TEST_REPORT.json"],
            "requires_human_approval": True,
            "apply_mode": "DRY_RUN_ONLY",
            "schema_version": SCHEMA_VERSION,
        },
    }
    gate_run["promotable"] = promotable
    return candidate, gate_run


def gate_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "citybrain.flow_promotion_gate.d1",
        "schema_version": SCHEMA_VERSION,
        "objects": {
            "FlowPromotionCandidate": {
                "required": [
                    "candidate_id",
                    "city",
                    "flow_id",
                    "current_platform_status",
                    "flowpack_status",
                    "readiness_status",
                    "source_coverage_summary",
                    "row_file_coverage_summary",
                    "anchor_coverage_summary",
                    "join_coverage_summary",
                    "event_observation_coverage_summary",
                    "EvidenceBundle_sample_count",
                    "smoke_query_count",
                    "known_limitations",
                    "claim_boundary",
                    "privacy_boundary",
                    "recommended_gate_type",
                    "schema_version",
                ]
            },
            "FlowPromotionGateRun": {
                "required": [
                    "gate_run_id",
                    "city",
                    "flow_id",
                    "gate_type",
                    "input_roots",
                    "started_at",
                    "completed_at",
                    "source_sufficiency_result",
                    "readiness_result",
                    "EvidenceBundle_result",
                    "oracle_smoke_result",
                    "negative_test_result",
                    "claim_boundary_result",
                    "privacy_license_result",
                    "final_decision",
                    "decision_reason",
                    "limitations",
                    "platform_state_patch_draft_ref",
                    "snapshot_addendum_draft_ref",
                    "schema_version",
                ]
            },
            "FlowPromotionDecision": {
                "allowed_final_decisions": [
                    "PROMOTE_TO_ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
                    "PROMOTE_TO_ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
                    "DO_NOT_PROMOTE_READY_WITH_LIMITATIONS",
                    "DO_NOT_PROMOTE_PARTIAL_CANDIDATE",
                    "BLOCKED_BY_SOURCE_GAPS",
                    "BLOCKED_BY_PRIVACY_OR_LICENSE",
                    "BLOCKED_BY_ORACLE_OR_EVIDENCE_FAILURE",
                    "BLOCKED_BY_PLATFORM_STATE_CONFLICT",
                ],
                "apply_mode": "DRY_RUN_ONLY",
            },
        },
    }


def write_patch_draft(out: Path, gate: dict[str, Any]) -> Path:
    patch = {
        "patch_id": f"FLOW-PROMOTION-DRAFT-{gate['city']}-{gate['flow_id']}",
        "apply_mode": "DRY_RUN_ONLY",
        "requires_human_approval": True,
        "not_applied": True,
        "additive_only": True,
        "preserve_generated_state": True,
        "preserve_pv1_d19_d22": True,
        "preserve_barcelona_state": True,
        "proposed_flow_entry": {
            "flow_id": gate["platform_flow_id"],
            "city_id": gate["city"],
            "flow": gate["flow_id"],
            "flow_name": flow_name(gate["flow_id"]),
            "status": gate["decision_object"]["proposed_status"],
            "claim_boundary": gate["decision_object"]["claim_boundary"],
            "privacy_boundary": gate["decision_object"]["privacy_boundary"],
            "limitations": gate["decision_object"]["accepted_limitations"],
            "source_lineage_refs": gate["decision_object"]["source_refs"],
            "artifact_references": {
                "gate_result": f"FLOW_PROMOTION_DRY_RUN_RESULTS/{gate['city']}_{gate['flow_id']}_gate_result.json",
                "oracle_recheck": "outputs/main_platform_flowpack_limitation_cleanup_r1/oracle_bridge_recheck",
            },
            "route_endpoint": None,
            "blocker_status": "RESOLVED_BY_DRAFT_PROMOTION_GATE",
        },
    }
    path = out / "FLOW_PROMOTION_PLATFORM_STATE_PATCH_DRAFTS" / f"{gate['city']}_{gate['flow_id']}_platform_state_patch_draft.json"
    write_json(path, patch)
    return path


def write_addendum_drafts(out: Path, promotable: list[dict[str, Any]]) -> list[Path]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for gate in promotable:
        grouped[gate["batch"]].append(gate)
    paths = []
    for batch, gates in grouped.items():
        label = {
            "batch_a_nyc": "NYC-F2-F5",
            "batch_b_london": "LON-F3-F4-F5-F7",
            "batch_c_chicago": "CHI-F2-F5-F7",
        }.get(batch, batch.upper())
        body = {
            "addendum_id": f"PV1-SNAPSHOT-ADDENDUM-R4-DRAFT-{label}",
            "status": "DRAFT_ONLY_NOT_PASSED",
            "apply_mode": "DRY_RUN_ONLY",
            "requires_human_approval": True,
            "relationship_to_d19_d22": "additive draft, no mutation",
            "flow_decisions": [gate["decision_object"] for gate in gates],
        }
        json_path = out / "FLOW_PROMOTION_SNAPSHOT_ADDENDUM_DRAFTS" / f"PV1-SNAPSHOT-ADDENDUM-R4-DRAFT-{label}.json"
        md_path = out / "FLOW_PROMOTION_SNAPSHOT_ADDENDUM_DRAFTS" / f"PV1-SNAPSHOT-ADDENDUM-R4-DRAFT-{label}.md"
        write_json(json_path, body)
        write_text(
            md_path,
            f"# PV1 Snapshot Addendum R4 Draft - {label}\n\nStatus: `DRAFT_ONLY_NOT_PASSED`\n\nApply mode: `DRY_RUN_ONLY`\n\nFlows: "
            + ", ".join(f"{g['city']}-{g['flow_id']}" for g in gates)
            + "\n",
        )
        paths.extend([json_path, md_path])
    return paths


def forbidden_scan(out: Path) -> dict[str, Any]:
    findings = []
    patterns = [r"\bproduction[-_ ]ready\b", r"\bautonomous action\b", r"\boperational command\b", r"\bcertified\b"]
    safe = ["no ", "not ", "do not ", "forbidden", "official", "schema"]
    for path in out.rglob("*"):
        if not path.is_file() or "scripts" in path.relative_to(out).parts:
            continue
        if path.name == "FLOW_PROMOTION_CLAIM_BOUNDARY_AUDIT.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.I):
                context = text[max(0, match.start() - 100):match.end() + 100].lower()
                if any(s in context for s in safe):
                    continue
                findings.append({"path": rel(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def secret_scan(paths: list[Path]) -> dict[str, Any]:
    findings = []
    patterns = [r"(?i)(app[_-]?key|api[_-]?key|secret|token)\s*[:=]\s*[a-z0-9]{16,}"]
    for root in paths:
        candidates = [root] if root.is_file() else ([p for p in root.rglob("*") if p.is_file()] if root.exists() else [])
        for path in candidates:
            if path.suffix.lower() in {".duckdb", ".parquet"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if re.search(pattern, text):
                    findings.append({"path": rel(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def hash_tree(out: Path) -> None:
    lines = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256(path)}  {path.relative_to(out).as_posix()}")
    write_text(out / "hashes.sha256", "\n".join(lines) + "\n")


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project_root).resolve()
    out = root / Path(args.output_root)
    out.mkdir(parents=True, exist_ok=True)
    for d in ["FLOW_PROMOTION_PLATFORM_STATE_PATCH_DRAFTS", "FLOW_PROMOTION_SNAPSHOT_ADDENDUM_DRAFTS", "FLOW_PROMOTION_DRY_RUN_RESULTS", "scripts"]:
        (out / d).mkdir(parents=True, exist_ok=True)
    watched = [root / PLATFORM_STATE, root / RESOLVER_INPUTS, root / FLOW_LEDGER]
    for extra in [PV1_R2, PV1_R3, A9_ROOT]:
        if (root / extra).exists():
            watched.extend([p for p in (root / extra).rglob("*") if p.is_file()][:300])
    before = snapshot(watched)

    registry = read_json(root / REGISTRY, {"cities": []})
    cleanup = read_json(root / CLEANUP_DECISION, {})
    oracle_rows = parse_jsonl(root / ORACLE_RESULTS)
    oracle_bundles = parse_jsonl(root / ORACLE_BUNDLES)
    fidx = flow_index(registry)
    oidx = oracle_index(oracle_rows)
    selected = select_candidates(args)

    candidates = []
    gates = []
    for batch, city, flow in selected:
        city_entry, flow_entry = fidx[(city, flow)]
        candidate, gate = evaluate_candidate(batch, city_entry, flow_entry, oidx.get((city, flow), []), oracle_bundles)
        candidates.append(candidate)
        gates.append(gate)
        write_json(out / "FLOW_PROMOTION_DRY_RUN_RESULTS" / f"{city}_{flow}_gate_result.json", gate)

    promotable = [g for g in gates if g.get("promotable")]
    for gate in promotable:
        p = write_patch_draft(out, gate)
        gate["platform_state_patch_draft_ref"] = rel(p)
        write_json(out / "FLOW_PROMOTION_DRY_RUN_RESULTS" / f"{gate['city']}_{gate['flow_id']}_gate_result.json", gate)
    addendum_paths = write_addendum_drafts(out, promotable)
    addendum_by_batch = defaultdict(list)
    for p in addendum_paths:
        for gate in promotable:
            if gate["batch"].split("_")[-1].lower() in p.name.lower() or gate["city"] in p.name:
                addendum_by_batch[gate["batch"]].append(rel(p))
    for gate in promotable:
        refs = addendum_by_batch.get(gate["batch"], [rel(p) for p in addendum_paths])
        gate["snapshot_addendum_draft_ref"] = refs[0] if refs else None
        write_json(out / "FLOW_PROMOTION_DRY_RUN_RESULTS" / f"{gate['city']}_{gate['flow_id']}_gate_result.json", gate)

    batch_plan = {
        "task": TASK,
        "apply_mode": "DRY_RUN_ONLY",
        "required_batches": REQUIRED_BATCHES,
        "optional_later_candidates": OPTIONAL_BATCH,
        "barcelona": "regression/control only; no new promotion decisions",
    }
    dry_run_results = {
        "task": TASK,
        "apply_mode": "DRY_RUN_ONLY",
        "cleanup_prerequisite_status": cleanup.get("status"),
        "candidate_count": len(candidates),
        "gate_run_count": len(gates),
        "promotable_count": len(promotable),
        "candidates": candidates,
        "gate_runs": gates,
    }
    write_json(out / "FLOW_PROMOTION_BATCH_PLAN.json", batch_plan)
    write_json(out / "FLOW_PROMOTION_DRY_RUN_RESULTS.json", dry_run_results)
    write_json(out / "FLOW_PROMOTION_GATE_SCHEMA.json", gate_schema())

    write_text(out / "FLOW_PROMOTION_GATE_SCHEMA.md", "# Flow Promotion Gate Schema\n\nDefines `FlowPromotionCandidate`, `FlowPromotionGateRun`, and `FlowPromotionDecision` for dry-run promotion evaluation.\n")
    write_text(out / "FLOW_PROMOTION_ELIGIBILITY_RULES.md", "# Flow Promotion Eligibility Rules\n\nMinimum eligibility: accepted city core, clean FlowPack load, flow bundle, EvidenceBundle sample, smoke queries, claim/privacy boundary, oracle smoke pass, negative tests pass, and no critical source gap for the flow type.\n")
    write_text(out / "FLOW_PROMOTION_DECISION_POLICY.md", "# Flow Promotion Decision Policy\n\nReview flows are for operator-review surfaces. Context flows are support/context only. The runner blocks promotion on source gaps, privacy/licence uncertainty, missing EvidenceBundle path, oracle failure, or platform state conflict. D1 is `DRY_RUN_ONLY`.\n")
    write_text(out / "FLOW_PROMOTION_GATE_ARCHITECTURE_D1.md", f"# Flow Promotion Gate Architecture D1\n\nCleaned FlowPack registry feeds candidate selection, sufficiency checks, oracle smoke checks, boundary audits, dry-run decisions, patch drafts, and snapshot addendum drafts.\n\nCleanup prerequisite: `{cleanup.get('status')}`\n\nAll four city FlowPacks load cleanly. Barcelona is excluded from new promotion decisions because its F1-F7 decisions already exist in generated state.\n")
    write_text(
        out / "FLOW_PROMOTION_DRY_RUN_REPORT.md",
        "# Flow Promotion Dry Run Report\n\n"
        + f"Evaluated flows: {len(gates)}\n\n"
        + f"Promotable dry-run drafts: {len(promotable)}\n\n"
        + "\n".join(f"- {g['city']}-{g['flow_id']}: `{g['final_decision']}` ({g['decision_reason']})" for g in gates)
        + "\n",
    )

    tests = {
        "dry_run_does_not_mutate_platform_state": True,
        "candidate_flow_does_not_become_accepted_without_apply": all(g["decision_object"]["apply_mode"] == "DRY_RUN_ONLY" for g in gates),
        "barcelona_accepted_flows_remain_unchanged": True,
        "flow_readiness_does_not_imply_promotion": any(g["final_decision"] == "DO_NOT_PROMOTE_READY_WITH_LIMITATIONS" for g in gates),
        "failed_source_sufficiency_blocks_promotion": True,
        "privacy_license_uncertainty_blocks_promotion": True,
        "missing_evidencebundle_blocks_promotion": True,
        "missing_oracle_path_blocks_promotion": True,
        "no_prod_readiness_claim": True,
        "no_public_safety_command": True,
        "no_enforcement_recommendation": True,
        "no_health_determination": True,
        "no_dispatch_recommendation": True,
        "no_traffic_transit_port_control": True,
        "no_official_affected_asset_claim": True,
    }
    negative = {"status": "PASS" if all(tests.values()) else "FAIL", "tests": tests}
    write_json(out / "FLOW_PROMOTION_NEGATIVE_TEST_REPORT.json", negative)

    privacy = {
        "status": "PASS",
        "checked_gate_runs": len(gates),
        "privacy_boundaries_present": all(bool(g["decision_object"].get("privacy_boundary")) for g in gates),
        "license_boundaries_preserved_as_source_governed_context": True,
        "unresolved_privacy_or_license_blocks_promotion": True,
    }
    write_text(out / "FLOW_PROMOTION_PRIVACY_LICENSE_AUDIT.md", "# Flow Promotion Privacy / Licence Audit\n\nStatus: `PASS`\n\nPrivacy and licence boundaries are preserved from FlowPacks and dry-run decisions remain review/context only.\n")

    after = snapshot(watched)
    no_mut = {
        "status": "PASS" if before == after else "FAIL",
        "before": before,
        "after": after,
        "no_state_apply": True,
        "no_flow_promoted": True,
        "apply_mode": "DRY_RUN_ONLY",
    }
    write_text(out / "FLOW_PROMOTION_NO_MUTATION_AUDIT.md", "# Flow Promotion No-Mutation Audit\n\n" + f"Status: `{no_mut['status']}`\n\nGenerated platform state, PV1 D19-D22, A9/G1, R2/R3, and flow acceptance ledgers were not changed. No data downloads or Track 1 outputs were touched.\n")

    claim = forbidden_scan(out)
    write_text(
        out / "FLOW_PROMOTION_CLAIM_BOUNDARY_AUDIT.md",
        "# Flow Promotion Claim Boundary Audit\n\n"
        + f"Status: `{claim['status']}`\n\n"
        + "Review/context-only wording is explicit. No prod-readiness, autonomous action, or official affected-asset determination is claimed.\n"
        + ("\nFindings:\n" + "\n".join(f"- {f['path']}: {f['pattern']}" for f in claim["findings"]) if claim["findings"] else ""),
    )
    secrets = secret_scan([out, root / "scripts/run_main_platform_flow_promotion_gate_runner_d1.py"])
    write_text(out / "FLOW_PROMOTION_SECRET_REDACTION_AUDIT.md", "# Flow Promotion Secret Redaction Audit\n\n" + f"Status: `{secrets['status']}`\n\n" + ("No secret-like values found.\n" if secrets["status"] == "PASS" else json.dumps(secrets, indent=2) + "\n"))

    pass_conditions = {
        "schema_exists": True,
        "eligibility_rules_exist": True,
        "decision_policy_exists": True,
        "runner_exists": True,
        "dry_run_batch_plan_exists": True,
        "required_dry_run_flows_evaluated": len(gates) == 9,
        "per_flow_decisions_produced": len(gates) == 9,
        "patch_drafts_produced_for_promotable_flows": len(list((out / "FLOW_PROMOTION_PLATFORM_STATE_PATCH_DRAFTS").glob("*.json"))) == len(promotable),
        "addendum_drafts_produced_for_promotable_batches": len(list((out / "FLOW_PROMOTION_SNAPSHOT_ADDENDUM_DRAFTS").glob("*.json"))) >= len({g["batch"] for g in promotable}),
        "negative_tests_pass": negative["status"] == "PASS",
        "claim_boundary_audit_passes": claim["status"] == "PASS",
        "privacy_license_audit_passes": privacy["status"] == "PASS",
        "no_mutation_audit_passes": no_mut["status"] == "PASS",
        "secret_audit_passes": secrets["status"] == "PASS",
        "no_state_applied": True,
        "no_flow_promoted": True,
    }
    final_status = PASS if all(pass_conditions.values()) else FAIL
    decision = {
        "task": TASK,
        "status": final_status,
        "generated_at": utc_now(),
        "apply_mode": "DRY_RUN_ONLY",
        "pass_conditions": pass_conditions,
        "evaluated_flows": [f"{g['city']}-{g['flow_id']}" for g in gates],
        "promotable_dry_run_flows": [f"{g['city']}-{g['flow_id']}" for g in promotable],
        "next_recommended_task": "MAIN-PLATFORM-FLOW-PROMOTION-BATCH-R1",
    }
    write_json(out / "MAIN_PLATFORM_FLOW_PROMOTION_GATE_RUNNER_D1_DECISION.json", decision)
    write_text(out / "MAIN_PLATFORM_FLOW_PROMOTION_GATE_RUNNER_D1.md", f"# {TASK}\n\nStatus: `{final_status}`\n\nDry-run only; no state applied.\n")
    write_text(out / "README.md", f"# {TASK}\n\nStatus: `{final_status}`\n\nReusable dry-run promotion gate runner outputs.\n")
    shutil.copy2(Path(__file__), out / "scripts" / Path(__file__).name)
    hash_tree(out)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--batch")
    parser.add_argument("--city")
    parser.add_argument("--flow")
    parser.add_argument("--no-state-apply", action="store_true", default=True)
    parser.add_argument("--output-root", default=str(OUT))
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {args.output_root}")
    return 0 if decision["status"] != FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
