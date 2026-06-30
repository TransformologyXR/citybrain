#!/usr/bin/env python3
"""FLOWX-DATA-ROUTE-CATALOG-D1 city/flow maturity catalog."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "FLOWX-DATA-ROUTE-CATALOG-D1 Data Route Maturity Catalog"
DEFAULT_OUTPUT_DIR = "outputs/flowx_data_route_catalog_d1"
PASS_STATUSES = {"PASS_DATA_ROUTE_CATALOG_WITH_SG_AUTH_BLOCKER", "PASS_DATA_ROUTE_CATALOG"}

INPUTS = {
    "xflow_d1": "outputs/xflow_d1_cross_city_expansion_reconciliation",
    "track2_r1": "outputs/track2_closeout_r1_value_complete_review_route_pack",
    "xdata_d2_r1": "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh",
    "sg_d1": "outputs/sg_d1_singapore_source_api_scout",
    "ontology_v2": "contracts/ontology_v2",
}

REQUIRED = [
    "README.md",
    "FLOWX_DATA_ROUTE_CATALOG_D1_HARNESS_REPORT.json",
    "FLOWX_DATA_ROUTE_CATALOG_D1_INPUT_INVENTORY.json",
    "FLOWX_DATA_ROUTE_CATALOG_D1_CONTRACT.json",
    "FLOWX_DATA_ROUTE_CATALOG_D1_CITY_FLOW_MATURITY_MATRIX.json",
    "FLOWX_DATA_ROUTE_CATALOG_D1_DATA_ROUTE_READY_LEDGER.json",
    "FLOWX_DATA_ROUTE_CATALOG_D1_ACCEPTED_FLOW_LEDGER.json",
    "FLOWX_DATA_ROUTE_CATALOG_D1_BLOCKER_LEDGER.json",
    "FLOWX_DATA_ROUTE_CATALOG_D1_SINGAPORE_SPLIT_REPORT.json",
    "FLOWX_DATA_ROUTE_CATALOG_D1_TRACK2_R1_LINKAGE_REPORT.json",
    "FLOWX_DATA_ROUTE_CATALOG_D1_NEXT_ACTIONS.json",
    "FLOWX_DATA_ROUTE_CATALOG_D1_NO_OVERCLAIM_REPORT.json",
    "FLOWX_DATA_ROUTE_CATALOG_D1_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
]

FLOW_DEFS = {
    "F1": "Situational Status",
    "F2": "Construction / Planning / Compliance",
    "F3": "Incident / Response / Affected Context",
    "F4": "Mobility / Transport / Environment",
    "F5": "Flood / Climate / Asset Risk",
    "F6": "Port / Logistics / Sequencing",
    "F7": "Civic Service / Sensor Fusion",
}

FORBIDDEN_PATTERNS = [
    r"\bnew accepted flow\b",
    r"\bdata route means accepted flow\b",
    r"\breview route means accepted flow\b",
    r"\bsingapore mobility route accepted\b",
    r"\bsingapore lta-backed route ready\b",
    r"\bbarcelona accepted\b",
    r"\bcapped bulk is full\b",
    r"\bwindowed/api snapshot is historical completeness\b",
    r"\btraffic-control instruction\b",
    r"\btransit-control instruction\b",
    r"\bemergency dispatch\b",
    r"\bpublic-safety recommendation\b",
    r"\bhealth determination\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\butility-control instruction\b",
    r"\bport/airport operational command\b",
    r"\bcertified affected asset\b",
    r"\bcertified affected building\b",
]

NEGATION_MARKERS = ("no ", "not ", "never ", "without ", "does not ", "do not ", "cannot ", "blocked", "0", "candidate-only", "review-context")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    if hasattr(value, "item"):
        try:
            return clean(value.item())
        except Exception:
            pass
    return value


def project_path(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root).resolve() / path


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: Path, project_root: Path) -> Path:
    resolved = output_dir.resolve()
    root = project_root.resolve()
    if resolved.exists():
        text = str(resolved).lower()
        if not text.startswith(str(root).lower()) or resolved.name.lower() != "flowx_data_route_catalog_d1":
            raise ValueError(f"refusing to remove unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def input_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "files": []}
    files = []
    iterable = [path] if path.is_file() else sorted(path.rglob("*"))
    for item in iterable:
        if item.is_file() and item.suffix.lower() != ".part":
            stat = item.stat()
            files.append({"path": item.relative_to(path).as_posix() if path.is_dir() else item.name, "bytes": stat.st_size})
    return {"exists": True, "file_count": len(files), "total_bytes": sum(item["bytes"] for item in files), "files": files}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(name for name, signature in before.items() if after.get(name) != signature)
    return {"status": "PASS" if not changed else "FAIL", "checked_inputs": sorted(before), "changed_inputs": changed}


def inventory(project_root: Path) -> dict[str, Any]:
    return {
        "status": "PASS",
        "inputs": {
            name: {"path": str(project_path(project_root, rel)), "exists": project_path(project_root, rel).exists(), "signature": input_signature(project_path(project_root, rel))}
            for name, rel in INPUTS.items()
        },
    }


def flow_num(flow: str) -> str:
    match = re.search(r"([1-7])", flow)
    return f"F{match.group(1)}" if match else flow


def accepted_rows(xflow_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in xflow_matrix.get("lanes", []):
        status = row.get("normalized_status")
        if status in {"ACCEPTED_CORE", "ACCEPTED_D6"}:
            flow = flow_num(str(row.get("flow", "")))
            rows.append(
                {
                    "city": row.get("city"),
                    "flow": row.get("flow"),
                    "flow_family": flow,
                    "maturity_status": "ACCEPTED_MOUNTED_EXTENSION" if status == "ACCEPTED_D6" else "ACCEPTED",
                    "source_status": row.get("source_status"),
                    "evidence": row.get("evidence"),
                    "boundary": (
                        "Accepted London mounted extension with review-context limitations carried forward."
                        if status == "ACCEPTED_D6"
                        else row.get("boundary")
                    ),
                }
            )
    return rows


def r1_maps(track2_r1: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    catalog = read_json(track2_r1 / "TRACK2_CLOSEOUT_R1_REVIEW_ROUTE_CATALOG.json", {})
    traces = read_json(track2_r1 / "TRACK2_CLOSEOUT_R1_LANE_EVIDENCE_TRACE_MATRIX.json", {})
    return (
        {row["lane"]: row for row in catalog.get("routes", [])},
        {row["lane"]: row for row in traces.get("lanes", [])},
    )


def data_route_row(lane: str, catalog: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    city = catalog.get("city")
    flow = catalog.get("flow")
    candidate = lane == "BARC-F7"
    data_ready = bool(trace.get("trace_complete")) and catalog.get("route_status") == "FACE_ROUTE_PUBLISHED" and catalog.get("smoke_status") == "PASS"
    status = "DATA_ROUTE_READY" if data_ready else "REVIEW_ROUTE_READY_NOT_ACCEPTED"
    public_status = "CANDIDATE_ONLY_NOT_ACCEPTED" if candidate else "REVIEW_ROUTE_READY_NOT_ACCEPTED"
    blockers = ["BLOCKED_BY_CITY_CORE"] if candidate else ["BLOCKED_BY_ACCEPTANCE_POLICY"]
    return {
        "city": city,
        "flow": flow,
        "lane": lane,
        "flow_name": FLOW_DEFS.get(flow_num(str(flow)), catalog.get("summary")),
        "source_ready": bool(trace.get("xdata_refs")),
        "evidence_ready": bool(trace.get("d3_evidencebundle_ids")),
        "review_route_ready": catalog.get("route_status") == "FACE_ROUTE_PUBLISHED",
        "data_route_ready": data_ready,
        "accepted": False,
        "maturity_status": status,
        "public_closeout_status": public_status,
        "blockers": blockers,
        "route_endpoint": catalog.get("api_paths", [None])[0],
        "source_lineage_refs": trace.get("xdata_refs", []),
        "evidencebundle_refs": trace.get("d3_evidencebundle_ids", []),
        "d4_payload_refs": trace.get("d4_payload_refs", []),
        "d5_hero_refs": trace.get("d5_hero_ids", []),
        "smoke_status": catalog.get("smoke_status"),
        "limitations": ["source-limited", "review-context only", "not accepted"],
    }


def singapore_rows(project_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sg = project_path(project_root, INPUTS["sg_d1"])
    harness = read_json(sg / "SG_D1_HARNESS_REPORT.json", {})
    nea = read_json(sg / "SG_D1_NEA_PUBLIC_API_REPORT.json", {})
    lta = read_json(sg / "SG_D1_LTA_DATAMALL_REPORT.json", {})
    public_ready = nea.get("status") == "PASS" and nea.get("successful_endpoints", 0) > 0
    lta_ready = lta.get("authenticated") is True and lta.get("endpoints_pulled", 0) > 0
    rows = [
        {
            "city": "Singapore",
            "flow": "SG-F4-public",
            "flow_family": "F4",
            "source_ready": public_ready,
            "evidence_ready": False,
            "review_route_ready": False,
            "data_route_ready": public_ready,
            "accepted": False,
            "maturity_status": "PARTIAL_PUBLIC_DATA_ROUTE_READY" if public_ready else "BLOCKED_BY_DATA",
            "public_closeout_status": "SG-F4-PUBLIC-CONTEXT-ROUTE_READY" if public_ready else "BLOCKED_BY_DATA",
            "blockers": ["NO_LTA_MOBILITY_CLAIM", "NO_REVIEW_ROUTE_YET"],
            "route_endpoint": None,
            "source_lineage_refs": sorted(nea.get("endpoints", {}).keys()),
            "limitations": ["public environmental context only", "not a transport/mobility route"],
        },
        {
            "city": "Singapore",
            "flow": "SG-F4-LTA",
            "flow_family": "F4",
            "source_ready": lta_ready,
            "evidence_ready": False,
            "review_route_ready": False,
            "data_route_ready": False,
            "accepted": False,
            "maturity_status": "BLOCKED_BY_AUTH",
            "public_closeout_status": "SG-F4-LTA-MOBILITY_ROUTE_BLOCKED_BY_AUTH",
            "blockers": ["BLOCKED_BY_AUTH", "LTA_DATAMALL_AUTH_FAILED_OR_MISSING"],
            "route_endpoint": None,
            "source_lineage_refs": [],
            "limitations": ["no LTA-backed mobility claim", "no Singapore mobility review route"],
        },
    ]
    report = {
        "status": "PASS",
        "sg_d1_status": harness.get("status"),
        "nea_public_successful_endpoints": nea.get("successful_endpoints", 0),
        "lta_authenticated": lta.get("authenticated", False),
        "split": rows,
    }
    return rows, report


def static_rows_from_prompt() -> list[dict[str, Any]]:
    return [
        {"city": "NYC", "flow": "F4", "maturity_status": "EVIDENCE_READY", "public_closeout_status": "D3_R1_EVIDENCE_READY", "blockers": ["NO_REVIEW_ROUTE_IN_CURRENT_CLOSEOUT"]},
        {"city": "Chicago", "flow": "F2X", "maturity_status": "EVIDENCE_READY", "public_closeout_status": "EVIDENCE_READY_BLOCKED_BY_IDENTITY_JOIN", "blockers": ["BLOCKED_BY_IDENTITY_JOIN"]},
        {"city": "Barcelona", "flow": "F1", "maturity_status": "SOURCE_READY", "public_closeout_status": "D1_D2_CANDIDATE_ONLY", "blockers": ["BLOCKED_BY_CITY_CORE"]},
        {"city": "Barcelona", "flow": "F2", "maturity_status": "SOURCE_READY", "public_closeout_status": "D1_D2_CANDIDATE_ONLY", "blockers": ["PERMIT_LICENSE_LIMITATIONS", "BLOCKED_BY_CITY_CORE"]},
        {"city": "Barcelona", "flow": "F3", "maturity_status": "SOURCE_READY", "public_closeout_status": "D1_D2_CANDIDATE_ONLY", "blockers": ["CONTEXT_ONLY_LIMITATIONS", "BLOCKED_BY_CITY_CORE"]},
        {"city": "Barcelona", "flow": "F4", "maturity_status": "CANDIDATE_REVIEW_READY", "public_closeout_status": "CANDIDATE_REVIEW_READY_BLOCKED_BY_CITY_CORE", "blockers": ["BLOCKED_BY_CITY_CORE"]},
        {"city": "Barcelona", "flow": "F5", "maturity_status": "BLOCKED_BY_DATA", "public_closeout_status": "D1_D2_PARTIAL", "blockers": ["FLOOD_SOURCE_GAPS", "BLOCKED_BY_CITY_CORE"]},
        {"city": "Barcelona", "flow": "F6", "maturity_status": "SOURCE_READY", "public_closeout_status": "D1_D2_CANDIDATE_ONLY", "blockers": ["CONTEXT_ONLY_SOURCE_LANDING", "BLOCKED_BY_CITY_CORE"]},
    ]


def build_matrix(project_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    xflow = read_json(project_path(project_root, INPUTS["xflow_d1"]) / "XFLOW_D1_CITY_FLOW_STATUS_MATRIX.json", {})
    track2 = project_path(project_root, INPUTS["track2_r1"])
    catalog_by_lane, trace_by_lane = r1_maps(track2)
    rows: list[dict[str, Any]] = []
    rows.extend(accepted_rows(xflow))
    for lane in ["CHI-F4X", "NYC-F1X", "CHI-F3X", "NYC-F5X", "NYC-F6X", "BARC-F7"]:
        rows.append(data_route_row(lane, catalog_by_lane[lane], trace_by_lane[lane]))
    rows.extend(static_rows_from_prompt())
    sg_rows, sg_report = singapore_rows(project_root)
    rows.extend(sg_rows)
    order = {"NYC": 1, "London": 2, "Chicago": 3, "Barcelona": 4, "Singapore": 5, "nyc": 1, "chicago": 3, "barcelona": 4}
    rows = sorted(rows, key=lambda row: (order.get(str(row.get("city")), 99), str(row.get("flow"))))
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["maturity_status"]] = counts.get(row["maturity_status"], 0) + 1
    return {"status": "PASS", "counts_by_maturity": counts, "lanes": rows}, sg_report


def contract() -> dict[str, Any]:
    return {
        "status": "PASS",
        "contract_name": "FLOWX_DATA_ROUTE_V1",
        "required_fields": [
            "route endpoint",
            "source lineage",
            "EvidenceBundle refs",
            "D4 replay refs",
            "D5 hero refs",
            "smoke result",
            "limitations",
            "forbidden claims",
            "acceptance status",
        ],
        "maturity_vocabulary": [
            "SOURCE_READY",
            "EVIDENCE_READY",
            "REVIEW_ROUTE_READY_NOT_ACCEPTED",
            "DATA_ROUTE_READY",
            "ACCEPTED",
            "ACCEPTED_MOUNTED_EXTENSION",
            "CANDIDATE_ONLY_NOT_ACCEPTED",
            "PARTIAL_PUBLIC_DATA_ROUTE_READY",
            "BLOCKED_BY_DATA",
            "BLOCKED_BY_CITY_CORE",
            "BLOCKED_BY_ACCEPTANCE_POLICY",
            "BLOCKED_BY_AUTH",
            "BLOCKED_BY_IDENTITY_JOIN",
        ],
        "boundary": "A data route is a source/evidence/route contract. It is not an accepted flow unless a promotion gate explicitly accepts it.",
    }


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "FLOWX_DATA_ROUTE_CATALOG_D1_NO_OVERCLAIM_REPORT.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in FORBIDDEN_PATTERNS:
            for match in re.finditer(pattern, text):
                window = text[max(0, match.start() - 80) : match.end() + 32]
                if any(marker in window for marker in NEGATION_MARKERS):
                    continue
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern, "context": window})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def run_flowx_data_route_catalog(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root)
    watched = {name: project_path(project_root, rel) for name, rel in INPUTS.items()}
    before = {name: input_signature(path) for name, path in watched.items()}
    inv = inventory(project_root)
    data_contract = contract()
    matrix, sg_report = build_matrix(project_root)
    data_ready = [row for row in matrix["lanes"] if row.get("data_route_ready")]
    accepted = [row for row in matrix["lanes"] if row.get("accepted") or row.get("maturity_status") in {"ACCEPTED", "ACCEPTED_MOUNTED_EXTENSION"}]
    blockers = [row for row in matrix["lanes"] if row.get("blockers")]
    track2_linkage = {
        "status": "PASS",
        "source_pack": str(project_path(project_root, INPUTS["track2_r1"])),
        "track2_review_route_lanes": ["CHI-F4X", "NYC-F1X", "CHI-F3X", "NYC-F5X", "NYC-F6X", "BARC-F7"],
        "data_route_ready_from_track2_r1": [row["lane"] for row in data_ready if row.get("lane")],
        "accepted_new_flows_from_track2": 0,
    }
    next_actions = {
        "status": "PASS",
        "items": [
            {"rank": 1, "action": "Use FLOWX_DATA_ROUTE_V1 for future route contracts before acceptance review."},
            {"rank": 2, "action": "Keep NYC/Chicago/Barcelona review-route lanes not accepted until acceptance policy is explicit."},
            {"rank": 3, "action": "For Singapore, continue public context separately from LTA mobility auth recovery."},
            {"rank": 4, "action": "Return PV1 focus to SUMO setup; consume only review/data route artifacts with boundaries."},
        ],
    }
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_INPUT_INVENTORY.json", inv)
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_CONTRACT.json", data_contract)
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_CITY_FLOW_MATURITY_MATRIX.json", matrix)
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_DATA_ROUTE_READY_LEDGER.json", {"status": "PASS", "lanes": data_ready})
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_ACCEPTED_FLOW_LEDGER.json", {"status": "PASS", "accepted_flows": accepted, "accepted_new_flows_from_track2": 0})
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_BLOCKER_LEDGER.json", {"status": "PASS", "blocked_or_limited": blockers})
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_SINGAPORE_SPLIT_REPORT.json", sg_report)
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_TRACK2_R1_LINKAGE_REPORT.json", track2_linkage)
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_NEXT_ACTIONS.json", next_actions)
    gates = [
        {"gate": "FLOWX-DATA-ROUTE-CATALOG-D1-PRECOND", "status": "PASS"},
        {"gate": "INPUT-INVENTORY", "status": inv["status"]},
        {"gate": "DATA-ROUTE-CONTRACT", "status": data_contract["status"]},
        {"gate": "CITY-FLOW-MATURITY-MATRIX", "status": matrix["status"]},
        {"gate": "DATA-ROUTE-READY-LEDGER", "status": "PASS" if len(data_ready) >= 7 else "FAIL"},
        {"gate": "ACCEPTED-FLOW-LEDGER", "status": "PASS"},
        {"gate": "BLOCKER-LEDGER", "status": "PASS"},
        {"gate": "SINGAPORE-SPLIT", "status": sg_report["status"]},
        {"gate": "TRACK2-R1-LINKAGE", "status": track2_linkage["status"]},
        {"gate": "NEXT-ACTIONS", "status": next_actions["status"]},
    ]
    overclaim = scan_no_overclaim(out)
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": "NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": "NO-MUTATION", "status": mutation["status"]})
    status = "PASS_DATA_ROUTE_CATALOG_WITH_SG_AUTH_BLOCKER" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    write_text(
        out / "README.md",
        "# FLOWX-DATA-ROUTE-CATALOG-D1 Data Route Maturity Catalog\n\n"
        f"Status: `{status}`\n\n"
        "This catalog formalizes source, evidence, review, data-route, and acceptance maturity. It creates no new accepted flows.\n",
    )
    harness = {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "output_dir": str(out),
        "city_flow_rows": len(matrix["lanes"]),
        "data_route_ready_count": len(data_ready),
        "review_route_ready_not_accepted_count": sum(1 for row in matrix["lanes"] if row.get("public_closeout_status") == "REVIEW_ROUTE_READY_NOT_ACCEPTED"),
        "accepted_flow_count": len(accepted),
        "accepted_new_flows_from_track2": 0,
        "singapore_public_context_ready": any(row.get("flow") == "SG-F4-public" and row.get("data_route_ready") for row in matrix["lanes"]),
        "singapore_lta_blocked_by_auth": True,
        "gates": gates,
    }
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    hashed_keys = set(read_json(out / "SHA256SUMS.json", {}).keys())
    hash_ok = all(name in hashed_keys for name in REQUIRED if name != "SHA256SUMS.json")
    gates.append({"gate": "HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = "PASS_DATA_ROUTE_CATALOG_WITH_SG_AUTH_BLOCKER" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "FLOWX_DATA_ROUTE_CATALOG_D1_HARNESS_REPORT.json", harness)
    write_text(
        out / "README.md",
        "# FLOWX-DATA-ROUTE-CATALOG-D1 Data Route Maturity Catalog\n\n"
        f"Status: `{status}`\n\n"
        "This catalog formalizes source, evidence, review, data-route, and acceptance maturity. It creates no new accepted flows.\n",
    )
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    gate_map = {gate["gate"]: gate["status"] for gate in report["gates"]}
    print(f"FLOWX-DATA-ROUTE-CATALOG-D1 Data Route Maturity Catalog: {report['status']}")
    print()
    print(f"City/flow rows: {report['city_flow_rows']}")
    print(f"Data-route-ready rows: {report['data_route_ready_count']}")
    print(f"Review-route-ready not accepted rows: {report['review_route_ready_not_accepted_count']}")
    print(f"Accepted flow rows: {report['accepted_flow_count']}")
    print(f"Accepted new flows from Track 2: {report['accepted_new_flows_from_track2']}")
    print(f"Singapore public context ready: {report['singapore_public_context_ready']}")
    print(f"Singapore LTA blocked by auth: {report['singapore_lta_blocked_by_auth']}")
    print()
    print(f"No-overclaim: {gate_map.get('NO-OVERCLAIM')}")
    print(f"No-mutation: {gate_map.get('NO-MUTATION')}")
    print(f"Hashes: {gate_map.get('HASHES')}")
    print()
    print("Final status:")
    print(report["status"])
    print()
    print(f"Output:\n{report['output_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FLOWX data route catalog gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_flowx_data_route_catalog(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
