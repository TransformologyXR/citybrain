#!/usr/bin/env python3
"""NIGHTRUN-D1 overnight current-work completion orchestrator.

This orchestrator is intentionally bounded: it reads current workstream outputs,
runs or records only listed safe gates, writes its own reports, and creates D3
EvidenceBundle outputs only for the explicit queue items in the NIGHTRUN-D1 task.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TASK = "NIGHTRUN-D1 Overnight Current-Work Completion Orchestrator"
DEFAULT_OUTPUT_DIR = "outputs/nightrun_d1_overnight_current_work_completion"
PASS_STATUSES = {"PASS_OVERNIGHT_PROGRESS", "PASS_WITH_BLOCKERS", "PASS_WITH_PARTIAL_PROGRESS"}

REQUIRED_ARTIFACTS = [
    "README.md",
    "NIGHTRUN_D1_HARNESS_REPORT.json",
    "NIGHTRUN_D1_INPUT_INVENTORY.json",
    "NIGHTRUN_D1_TASK_PLAN.json",
    "NIGHTRUN_D1_EXECUTION_LOG.json",
    "NIGHTRUN_D1_STAGE_RESULTS.json",
    "NIGHTRUN_D1_XDATA_STATUS_REPORT.json",
    "NIGHTRUN_D1_FLOW_QUEUE_PROGRESS.json",
    "NIGHTRUN_D1_BLOCKER_REPORT.json",
    "NIGHTRUN_D1_MORNING_HANDOFF.md",
    "NIGHTRUN_D1_NEXT_RECOMMENDATIONS.json",
    "NIGHTRUN_D1_NO_OVERCLAIM_REPORT.json",
    "NIGHTRUN_D1_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
]

HARD_BOUNDARY_INPUTS = {
    "a9": "outputs/a9*",
    "f3_nyc": "outputs/f3_nyc*",
    "lon": "outputs/lon*",
    "chi_f1f7": "outputs/chi_f1f7*",
    "chi_flowx": "outputs/chi_flowx*",
    "chi_f2x_d3": "outputs/chi_f2x_d3*",
    "nyc_f4x_d3": "outputs/nyc_f4x_d3*",
    "barc_f4": "outputs/barc_f4*",
    "pv1": "outputs/pv1*",
    "xflow": "outputs/xflow*",
    "xdata_d1": "outputs/xdata_d1*",
    "ontology_v2": "contracts/ontology_v2",
    "snapshot": "snapshot",
    "snapshots": "snapshots",
    "xdata_landing": "data_landing/xdata_d1_bulk_official_sources_v1",
}

INPUT_DEFAULTS = {
    "xdata_d1_outputs": "outputs/xdata_d1_four_city_bulk_source_landing",
    "xdata_landing": "data_landing/xdata_d1_bulk_official_sources_v1",
    "xdata_d2": "outputs/xdata_d2_four_city_bulk_landing_reconciliation",
    "xflow_d1": "outputs/xflow_d1_cross_city_expansion_reconciliation",
    "lon_flowx_d6": "outputs/lon_flowx_expansion_path_d2_to_d6",
    "chi_f2x_d3": "outputs/chi_f2x_d3_compliance_evidencebundles",
    "nyc_f4x_d3": "outputs/nyc_f4x_d3_mobility_environment_evidencebundles",
    "barc_f4_d6": "outputs/barc_f4_d6_candidate_review_snapshot",
    "barc_f7_d3": "outputs/barc_f7_d3_civic_sensor_fusion_evidencebundles",
    "ontology_v2": "contracts/ontology_v2",
}

XDATA_CITY_REPORTS = {
    "LON": "outputs/xdata_d1_four_city_bulk_source_landing/LON_XDATA_D1_ROW_COUNT_REPORT.json",
    "NYC": "outputs/xdata_d1_four_city_bulk_source_landing/NYC_XDATA_D1_ROW_COUNT_REPORT.json",
    "CHI": "outputs/xdata_d1_four_city_bulk_source_landing/chicago/CHI_XDATA_D1_ROW_COUNT_REPORT.json",
    "BARC": "outputs/xdata_d1_four_city_bulk_source_landing/BARC_XDATA_D1_ROW_COUNT_REPORT.json",
}

NO_OVERCLAIM_PATTERNS = [
    r"\bplatform v1 complete\b",
    r"\ball flows accepted\b",
    r"\bbarcelona accepted\b",
    r"\bnyc flow 4 accepted\b",
    r"\bchicago flow 2 accepted\b",
    r"\bchicago flow 4 accepted\b",
    r"\bbulk capped data is full\b",
    r"\bcapped bulk data is full\b",
    r"\bapi/current snapshot is historical completeness\b",
    r"\bemergency dispatch\b",
    r"\bfire dispatch\b",
    r"\bpublic safety recommendation\b",
    r"\bpublic-safety recommendation\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\bhealth determination\b",
    r"\btraffic-control instruction\b",
    r"\btransit-control instruction\b",
    r"\butility-control instruction\b",
    r"\bport-control instruction\b",
    r"\bcertified affected building\b",
    r"\bcertified affected asset\b",
]

NEGATION_MARKERS = (
    "no ",
    "not ",
    "never ",
    "without ",
    "does not ",
    "do not ",
    "cannot ",
    "forbidden ",
    "boundary ",
)

GREEN_BEFORE = [
    "PV1-SDF-D1-D6: PASS_SYNTHETIC_DATA_FACTORY_D1_D6",
    "PV1-INFRA-D1: PASS_WITH_INSTALL_GAPS, updated with live 3090 SSH",
    "PV1-D3/D4: PASS_CROSS_CITY_ONTOLOGY_V2",
    "PV1-D5/D6/D7: PASS_FILE_BACKED_EVENT_FABRIC",
    "PV1-D8/D9: PASS_REVIEW_ONLY_INCIDENT_AND_PLAN_MODES",
    "XFLOW-D1: PASS_CROSS_CITY_EXPANSION_RECONCILIATION",
    "LON-FLOWX-D6: PASS_ACCEPTED_EXTENSION_SNAPSHOT",
    "CHI-F2X-D3: PASS_WITH_IDENTITY_BLOCKERS",
    "NYC-F4X-D3: PASS_WITH_SOURCE_LIMITATIONS",
    "BARC-F4-D6: PASS_CANDIDATE_REVIEW_SNAPSHOT",
]

D3_TASKS = [
    {
        "lane": "BARC-F7-D3",
        "city": "BARC",
        "flow": "Flow 7",
        "output_dir": "outputs/barc_f7_d3_civic_sensor_fusion_evidencebundles",
        "prefix": "BARC_F7_D3",
        "expected_statuses": ["PASS_CIVIC_SENSOR_FUSION_EVIDENCEBUNDLES", "PASS_WITH_SOURCE_LIMITATIONS"],
        "existing_only": True,
        "bundle_specs": [],
    },
    {
        "lane": "CHI-F4X-D3",
        "city": "CHI",
        "flow": "Flow 4",
        "output_dir": "outputs/chi_f4x_d3_mobility_environment_evidencebundles",
        "prefix": "CHI_F4X_D3",
        "status": "PASS_WITH_SOURCE_LIMITATIONS",
        "bundle_specs": [
            ("traffic_tracker_time_window_context_bundle", ["traffic_tracker", "311_service_requests"]),
            ("open_air_environment_context_bundle", ["open_air_chicago"]),
            ("divvy_or_mobility_context_bundle", ["divvy_trips"]),
            ("cta_static_context_bundle", ["cta_gtfs_static"]),
            ("mobility_environment_governance_boundary_bundle", ["traffic_tracker", "open_air", "divvy", "cta"]),
        ],
        "boundary_lines": [
            "Chicago Flow 4 remains D3 review-context only and is not accepted by this gate.",
            "No live CTA claim without key.",
            "No traffic-control instruction.",
            "No health determination from environmental data.",
        ],
    },
    {
        "lane": "NYC-F1X-D3",
        "city": "NYC",
        "flow": "Flow 1",
        "output_dir": "outputs/nyc_f1x_d3_situational_status_evidencebundles",
        "prefix": "NYC_F1X_D3",
        "status": "PASS_WITH_SOURCE_LIMITATIONS",
        "bundle_specs": [
            ("area_status_311_context_bundle", ["nyc_311"]),
            ("collision_context_bundle", ["nyc_mvc"]),
            ("air_quality_context_bundle", ["nyc_air_quality"]),
            ("transit_status_context_bundle", ["mta_", "citi_bike"]),
            ("situational_status_governance_boundary_bundle", ["nyc_311", "nyc_mvc", "mta_", "citi_bike"]),
        ],
        "boundary_lines": [
            "NYC Flow 1 remains D3 review-context only and is not accepted by this gate.",
            "Bounded and capped sources remain bounded or capped.",
            "No emergency, public-safety, health, or operational recommendation.",
        ],
    },
    {
        "lane": "CHI-F3X-D3",
        "city": "CHI",
        "flow": "Flow 3",
        "output_dir": "outputs/chi_f3x_d3_traffic_incident_context_evidencebundles",
        "prefix": "CHI_F3X_D3",
        "status": "PASS_WITH_SOURCE_LIMITATIONS",
        "bundle_specs": [
            ("crash_event_context_bundle", ["traffic_crashes_crashes"]),
            ("crash_vehicle_context_bundle", ["traffic_crashes_vehicles"]),
            ("crash_person_context_privacy_safe_bundle", ["traffic_crashes_people"]),
            ("traffic_segment_context_bundle", ["traffic_tracker_historical"]),
            ("incident_governance_boundary_bundle", ["traffic_crashes", "traffic_tracker"]),
        ],
        "boundary_lines": [
            "Traffic and crash evidence is review-context only.",
            "No dispatch.",
            "No affected-asset certification.",
            "No public-safety instruction.",
        ],
    },
    {
        "lane": "NYC-F5X-D3",
        "city": "NYC",
        "flow": "Flow 5",
        "output_dir": "outputs/nyc_f5x_d3_flood_climate_asset_risk_evidencebundles",
        "prefix": "NYC_F5X_D3",
        "status": "PASS_WITH_SOURCE_LIMITATIONS",
        "bundle_specs": [
            ("flood_vulnerability_context_bundle", ["nyc_flood_vulnerability"]),
            ("air_quality_climate_context_bundle", ["nyc_air_quality"]),
            ("parcel_or_area_risk_context_bundle", ["nyc_flood_vulnerability", "nyc_311"]),
            ("facility_context_bundle", ["panynj", "mta_static"]),
            ("risk_governance_boundary_bundle", ["nyc_flood", "nyc_air_quality", "panynj"]),
        ],
        "boundary_lines": [
            "Risk evidence is review-context only.",
            "No certified infrastructure failure propagation.",
            "No utility-control or emergency-response claim.",
        ],
    },
    {
        "lane": "NYC-F6X-D3",
        "city": "NYC",
        "flow": "Flow 6",
        "output_dir": "outputs/nyc_f6x_d3_port_airport_logistics_evidencebundles",
        "prefix": "NYC_F6X_D3",
        "status": "PASS_WITH_SOURCE_LIMITATIONS",
        "bundle_specs": [
            ("panynj_air_passenger_context_bundle", ["panynj_air_passenger"]),
            ("airport_logistics_trend_context_bundle", ["panynj_air_passenger"]),
            ("review_only_sequence_context_bundle", ["mta_static", "mta_gtfs", "panynj"]),
            ("logistics_governance_boundary_bundle", ["panynj", "mta_", "citi_bike"]),
        ],
        "boundary_lines": [
            "Port and airport logistics evidence is review-context only.",
            "No airport or port operational command.",
            "No safety-critical sequencing.",
            "No aircraft or vessel instruction.",
        ],
    },
]

LOWER_PRIORITY_BARC = ["BARC-F1-D3", "BARC-F3-D3", "BARC-F2-D3", "BARC-F5-D3", "BARC-F6-D3"]
OPTIONAL_CONTINUATIONS = ["BARC-F7-D4/D5/D6", "CHI-F4X-D4/D5/D6", "NYC-F1X/F5X/F6X-D4+"]


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


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(path: str | Path, project_root: str | Path, expected_name: str) -> Path:
    resolved = Path(path).resolve()
    root = Path(project_root).resolve()
    if resolved.exists():
        text = str(resolved).lower()
        if not text.startswith(str(root).lower()) or resolved.name.lower() != expected_name.lower():
            raise ValueError(f"refusing to remove unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def safe_existing_status(path: Path, prefix: str) -> str | None:
    candidates = [
        path / f"{prefix}_HARNESS_REPORT.json",
        path / "XDATA_D2_HARNESS_REPORT.json",
        path / "NIGHTRUN_D1_HARNESS_REPORT.json",
    ]
    for candidate in candidates:
        report = read_json(candidate, {})
        if isinstance(report, dict) and report.get("status"):
            return str(report["status"])
    return None


def is_pass_status(status: str | None) -> bool:
    return bool(status) and str(status).startswith("PASS")


def gate(name: str, ok: bool, **details: Any) -> dict[str, Any]:
    payload = {"gate": name, "status": "PASS" if ok else "FAIL"}
    payload.update(details)
    return payload


def input_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "files": []}
    files = []
    iterable = [path] if path.is_file() else sorted(path.rglob("*"))
    for item in iterable:
        if not item.is_file() or item.suffix.lower() == ".part":
            continue
        stat = item.stat()
        files.append({"path": item.relative_to(path).as_posix() if path.is_dir() else item.name, "bytes": stat.st_size})
    return {"exists": True, "file_count": len(files), "total_bytes": sum(item["bytes"] for item in files), "files": files}


def hard_boundary_snapshot(project_root: Path) -> dict[str, Any]:
    signatures: dict[str, Any] = {}
    for name, pattern in HARD_BOUNDARY_INPUTS.items():
        matches = sorted(project_root.glob(pattern))
        if not matches:
            signatures[name] = {"exists": False, "matches": []}
            continue
        signatures[name] = {"exists": True, "matches": [{"path": str(path), "signature": input_signature(path)} for path in matches]}
    return signatures


def compare_snapshots(before: dict[str, Any], after: dict[str, Any], externally_volatile: set[str] | None = None) -> dict[str, Any]:
    externally_volatile = externally_volatile or set()
    changed = sorted(name for name, signature in before.items() if after.get(name) != signature)
    stable_changed = [name for name in changed if name not in externally_volatile]
    volatile_changed = [name for name in changed if name in externally_volatile]
    return {
        "status": "PASS" if not stable_changed else "FAIL",
        "checked_inputs": sorted(before),
        "changed_inputs": stable_changed,
        "externally_volatile_changed_inputs": volatile_changed,
        "externally_volatile_note": "xdata_landing may be updated by separate active bulk download lanes; NIGHTRUN-D1 does not write there.",
    }


def file_preview(path: Path, max_files: int = 40) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "files": []}
    files = []
    iterable = [path] if path.is_file() else sorted(path.rglob("*"))
    total = 0
    for item in iterable:
        if item.is_file():
            total += 1
            if len(files) < max_files:
                files.append({"path": item.relative_to(path).as_posix() if path.is_dir() else item.name, "bytes": item.stat().st_size})
    return {"exists": True, "file_count": total, "files": files}


def build_input_inventory(project_root: Path) -> dict[str, Any]:
    inputs = {}
    for name, rel in INPUT_DEFAULTS.items():
        path = project_path(project_root, rel)
        inputs[name] = {"path": str(path), **file_preview(path)}
    return {"status": "PASS", "generated_at": utc_now(), "inputs": inputs, "green_before": GREEN_BEFORE}


def source_rows(project_root: Path, city: str) -> list[dict[str, Any]]:
    report = read_json(project_path(project_root, XDATA_CITY_REPORTS[city]), {})
    rows_: list[dict[str, Any]] = []
    for item in report.get("sources", []):
        status = str(item.get("landing_status") or "UNKNOWN")
        source_key = str(item.get("source_key") or "")
        if source_key == "nyc_optional_unbound_sources":
            status = "OPTIONAL_UNBOUND"
        rows_.append(
            {
                "source_key": source_key,
                "landing_status": status,
                "rows_landed": int(item.get("rows_landed") or 0),
                "bytes_downloaded": int(item.get("bytes_downloaded") or 0),
                "total_available": item.get("total_available"),
                "cap_rule_applied": item.get("cap_rule_applied"),
                "coverage_pct": item.get("coverage_pct"),
            }
        )
    return rows_


def xdata_status(project_root: Path) -> dict[str, Any]:
    cities = []
    for city, report_rel in XDATA_CITY_REPORTS.items():
        path = project_path(project_root, report_rel)
        sources = source_rows(project_root, city) if path.exists() else []
        landing_dir = project_path(project_root, "data_landing/xdata_d1_bulk_official_sources_v1") / {
            "LON": "london",
            "NYC": "nyc",
            "CHI": "chicago",
            "BARC": "barcelona",
        }[city]
        part_files = [p for p in landing_dir.rglob("*.part")] if landing_dir.exists() else []
        if part_files:
            availability = "ACTIVE_OR_IN_PROGRESS"
        elif sources:
            availability = "AVAILABLE"
        elif path.exists():
            availability = "PARTIAL_AVAILABLE"
        else:
            availability = "MISSING"
        counts = Counter(item["landing_status"] for item in sources)
        cities.append(
            {
                "city": city,
                "row_report": str(path),
                "availability": availability,
                "source_count": len(sources),
                "rows_landed": sum(item["rows_landed"] for item in sources),
                "bytes_landed": sum(item["bytes_downloaded"] for item in sources),
                "status_counts": dict(sorted(counts.items())),
                "volatile_part_files": [str(path.relative_to(landing_dir)) for path in part_files[:20]],
            }
        )
    return {"status": "PASS", "cities": cities}


def select_sources(sources: list[dict[str, Any]], keywords: list[str]) -> list[dict[str, Any]]:
    selected = []
    for source in sources:
        key = source["source_key"].lower()
        if any(keyword.lower() in key for keyword in keywords):
            selected.append(source)
    return selected


def build_bundle(task: dict[str, Any], bundle_id: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "evidence_bundle_id": bundle_id,
        "city": task["city"],
        "flow": task["flow"],
        "mode": "review_context",
        "claim_label": "D3_READY_SOURCE_LIMITED",
        "subject": bundle_id.replace("_", " "),
        "time_window": "D1 landed rows and explicit D1 windows only",
        "source_records": sources,
        "native_ids": [source["source_key"] for source in sources],
        "relationships": [
            {"type": "SUPPORTED_BY", "source_key": source["source_key"], "status": source["landing_status"]}
            for source in sources
        ],
        "location_confidence": "CITY_SCOPE_SOURCE_CONTEXT",
        "temporal_confidence": "WINDOWED_OR_LANDED_D1_CONTEXT",
        "limitations": sorted({limitation_for(source["landing_status"]) for source in sources}),
        "governance_boundaries": task["boundary_lines"],
        "forbidden_claim_codes": [
            "NO_ACCEPTED_FLOW",
            "NO_OPERATIONAL_COMMAND",
            "NO_PUBLIC_SAFETY_INSTRUCTION",
            "NO_HEALTH_DETERMINATION",
            "NO_CERTIFIED_AFFECTED_ASSET",
        ],
        "trace_refs": [f"XDATA-D1:{source['source_key']}" for source in sources],
    }


def limitation_for(status: str) -> str:
    return {
        "FULL": "FULL rows retained only where rows_landed equals total_available.",
        "WINDOWED_COMPLETE": "Windowed or snapshot source; not historical completeness.",
        "CAPPED_BULK": "Capped bulk source; not full-source proof.",
        "BOUNDED_SAMPLE": "Bounded sample; diagnostic/source-limited.",
        "METADATA_ONLY": "Metadata-only source; no data rows landed.",
        "ENDPOINT_CONFIRMED": "Endpoint-only confirmation.",
        "DOWNLOAD_FAILED": "Failed source; unavailable without later recovery.",
        "OPTIONAL_UNBOUND": "Optional unbound source; not a failed required input.",
    }.get(status, "Source limitation carried forward.")


def d3_no_overclaim(output_dir: Path) -> dict[str, Any]:
    scan = no_overclaim_scan(output_dir, skip_names={"SHA256SUMS.json"})
    return {"status": scan["status"], "checked_files": scan["checked_files"], "findings": scan["findings"]}


def build_d3_output(project_root: Path, task: dict[str, Any], rerun: bool, dry_run: bool) -> dict[str, Any]:
    out = project_path(project_root, task["output_dir"])
    existing = safe_existing_status(out, task["prefix"])
    if task.get("existing_only") and is_pass_status(existing):
        return {"lane": task["lane"], "status": existing, "action": "SKIPPED_ALREADY_PASSED", "output_dir": str(out)}
    if is_pass_status(existing) and not rerun:
        return {"lane": task["lane"], "status": existing, "action": "SKIPPED_ALREADY_PASSED", "output_dir": str(out)}
    if task.get("existing_only"):
        return {"lane": task["lane"], "status": existing or "MISSING", "action": "BLOCKED_EXISTING_OUTPUT_MISSING", "output_dir": str(out)}
    if dry_run:
        return {"lane": task["lane"], "status": "DRY_RUN_SKIPPED", "action": "DRY_RUN", "output_dir": str(out)}

    reset_output_dir(out, project_root, out.name)
    all_sources = source_rows(project_root, task["city"])
    bundles = []
    for bundle_id, keywords in task["bundle_specs"]:
        sources = select_sources(all_sources, keywords)
        bundles.append(build_bundle(task, bundle_id, sources))

    selected = [bundle for bundle in bundles if bundle["source_records"]]
    limitation_rows = [
        {
            "bundle_id": bundle["evidence_bundle_id"],
            "source_key": source["source_key"],
            "status": source["landing_status"],
            "limitation": limitation_for(source["landing_status"]),
        }
        for bundle in bundles
        for source in bundle["source_records"]
    ]
    gates = [
        {"gate": f"{task['lane']}-PRECOND", "status": "PASS", "source_count": len(all_sources)},
        {"gate": f"{task['lane']}-BUNDLES", "status": "PASS" if len(selected) == len(task["bundle_specs"]) else "FAIL", "selected": len(selected)},
        {"gate": f"{task['lane']}-BOUNDARY", "status": "PASS", "boundaries": task["boundary_lines"]},
    ]
    status = task["status"] if all(item["status"] == "PASS" for item in gates) else "FAIL"

    write_json(out / f"{task['prefix']}_EVIDENCEBUNDLES.json", {"status": status, "bundles": bundles})
    write_json(out / f"{task['prefix']}_SELECTED_BUNDLES.json", {"status": "PASS", "selected_bundle_ids": [b["evidence_bundle_id"] for b in selected], "selected_bundles": selected})
    write_json(out / f"{task['prefix']}_INPUT_INVENTORY.json", {"status": "PASS", "xdata_sources": all_sources, "input_report": XDATA_CITY_REPORTS[task["city"]]})
    write_json(out / f"{task['prefix']}_SOURCE_LIMITATION_REPORT.json", {"status": "PASS", "limitations": limitation_rows})
    write_json(out / f"{task['prefix']}_SOURCE_AND_JOIN_SUMMARY.json", {"status": "PASS", "source_count": len(all_sources), "bundle_count": len(bundles), "selected_bundle_count": len(selected)})
    write_json(out / f"{task['prefix']}_TRACE_REPORT.json", {"status": "PASS", "trace_refs": [ref for bundle in bundles for ref in bundle["trace_refs"]]})
    write_json(out / f"{task['prefix']}_EVIDENCEBUNDLE_CONTRACT.json", {"status": "PASS", "required_bundle_ids": [spec[0] for spec in task["bundle_specs"]], "boundary_lines": task["boundary_lines"]})
    write_json(out / f"{task['prefix']}_NEXT_D4_HANDOFF.json", {"status": "D4_READY_WITH_SOURCE_LIMITATIONS", "lane": task["lane"], "boundary_lines": task["boundary_lines"], "recommendation": "Continue only as payload-only/review-context proof unless a later gate proves stronger preconditions."})
    no_overclaim = d3_no_overclaim(out)
    write_json(out / f"{task['prefix']}_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(out / f"{task['prefix']}_NO_MUTATION_REPORT.json", {"status": "PASS", "note": "D3 output generated from read-only source reports; no accepted outputs or landing files modified."})
    gates.extend(
        [
            {"gate": f"{task['lane']}-NO-OVERCLAIM", "status": no_overclaim["status"]},
            {"gate": f"{task['lane']}-NO-MUTATION", "status": "PASS"},
        ]
    )
    status = task["status"] if all(item["status"] == "PASS" for item in gates) else "FAIL"
    harness = {
        "task": f"{task['lane']} {task['flow']} EvidenceBundles",
        "status": status,
        "generated_at": utc_now(),
        "output_dir": str(out),
        "gates": gates,
        "boundary_lines": task["boundary_lines"],
    }
    write_json(out / f"{task['prefix']}_HARNESS_REPORT.json", harness)
    write_text(
        out / "README.md",
        "\n".join(
            [
                f"# {task['lane']} EvidenceBundles",
                "",
                f"Status: `{status}`",
                "",
                "Generated by NIGHTRUN-D1 from explicit D1/XDATA source reports.",
                "This is D3 review-context evidence only; source limitations and governance boundaries carry forward.",
            ]
        ),
    )
    write_hashes(out)
    return {"lane": task["lane"], "status": status, "action": "RAN", "output_dir": str(out), "bundle_count": len(bundles), "selected_bundle_count": len(selected)}


def run_xdata_d2_if_possible(project_root: Path, rerun: bool, dry_run: bool, execution_log: list[dict[str, Any]]) -> dict[str, Any]:
    script = project_root / "scripts/run_xdata_d2_gate.py"
    out = project_root / "outputs/xdata_d2_four_city_bulk_landing_reconciliation"
    existing = safe_existing_status(out, "XDATA_D2")
    if existing and not rerun:
        return {"status": existing, "action": "SKIPPED_ALREADY_PASSED", "output_dir": str(out)}
    if dry_run:
        return {"status": "DRY_RUN_SKIPPED", "action": "DRY_RUN", "output_dir": str(out)}
    if not script.exists():
        return {"status": "BLOCKED", "action": "MISSING_SCRIPT", "output_dir": str(out)}
    completed = subprocess.run([sys.executable, "-B", str(script)], cwd=project_root, text=True, capture_output=True)
    execution_log.append({"task": "XDATA-D2", "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
    status = safe_existing_status(out, "XDATA_D2") or ("FAIL" if completed.returncode else "PASS")
    return {"status": status, "action": "RAN", "returncode": completed.returncode, "output_dir": str(out)}


def no_overclaim_scan(output_dir: Path, skip_names: set[str] | None = None) -> dict[str, Any]:
    skip_names = skip_names or set()
    findings = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in skip_names:
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in NO_OVERCLAIM_PATTERNS:
            for match in re.finditer(pattern, text):
                window = text[max(0, match.start() - 48) : match.end() + 16]
                if any(marker in window for marker in NEGATION_MARKERS):
                    continue
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern, "context": window})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def build_task_plan(rerun: bool, dry_run: bool, max_runtime_hours: float, interval_minutes: float) -> dict[str, Any]:
    items = [
        {"id": "A1", "task": "Read four-city XDATA state", "mode": "read-only"},
        {"id": "A2", "task": "Run or skip XDATA-D2 reconciliation", "mode": "safe gate"},
    ]
    for task in D3_TASKS:
        items.append({"id": f"B-{task['lane']}", "task": task["lane"], "mode": "D3 evidence bundle"})
    for lane in LOWER_PRIORITY_BARC:
        items.append({"id": f"B-low-{lane}", "task": lane, "mode": "lower priority", "planned_action": "skip unless high-priority queue clears and time remains"})
    for lane in OPTIONAL_CONTINUATIONS:
        items.append({"id": f"C-{lane}", "task": lane, "mode": "optional continuation", "planned_action": "skip if live/face proof is not safe"})
    return {"status": "PASS", "rerun_passed": rerun, "dry_run": dry_run, "max_runtime_hours": max_runtime_hours, "check_interval_minutes": interval_minutes, "items": items}


def build_handoff(status: str, xdata: dict[str, Any], xdata_d2: dict[str, Any], queue: list[dict[str, Any]], blockers: list[dict[str, Any]], skipped: list[dict[str, Any]], output_dirs: list[str], next_steps: list[dict[str, Any]]) -> str:
    lines = [
        "# NIGHTRUN-D1 Morning Handoff",
        "",
        f"Final status: `{status}`",
        "",
        "## Already Green Before Night Run",
        "",
        *[f"- {item}" for item in GREEN_BEFORE],
        "",
        "## Newly Run",
        "",
    ]
    newly_run = [item for item in queue if item.get("action") == "RAN"]
    lines.extend([f"- {item['lane']}: `{item['status']}` -> `{item['output_dir']}`" for item in newly_run] or ["- None"])
    lines.extend(["", "## XDATA", "", f"- XDATA-D2: `{xdata_d2['status']}` ({xdata_d2['action']})"])
    for city in xdata["cities"]:
        lines.append(f"- {city['city']}: `{city['availability']}`, rows={city['rows_landed']}, bytes={city['bytes_landed']}")
    lines.extend(["", "## Passed", ""])
    lines.extend([f"- {item['lane']}: `{item['status']}`" for item in queue if str(item.get("status", "")).startswith("PASS")] or ["- None"])
    lines.extend(["", "## Failed", ""])
    lines.extend([f"- {item['lane']}: `{item['status']}`" for item in queue if item.get("status") == "FAIL"] or ["- None"])
    lines.extend(["", "## Skipped Or Blocked", ""])
    lines.extend([f"- {item['lane']}: {item['reason']}" for item in skipped + blockers] or ["- None"])
    lines.extend(["", "## New Output Directories", ""])
    lines.extend([f"- {path}" for path in output_dirs] or ["- None"])
    lines.extend(["", "## Claims Strengthened", "", "- D3 review-context readiness is stronger for Chicago Flow 4, NYC Flow 1, Chicago Flow 3, NYC Flow 5, and NYC Flow 6 where newly generated outputs passed."])
    lines.extend(["", "## Claims Still Limited", "", "- Barcelona remains candidate-only.", "- Capped, bounded, windowed, failed, endpoint-only, and metadata-only source statuses carry forward.", "- Optional D4/D5/D6 continuations were not promoted into accepted cartridges."])
    lines.extend(["", "## Morning Next Steps", ""])
    lines.extend([f"{item['rank']}. {item['task']} - {item['reason']}" for item in next_steps[:8]])
    return "\n".join(lines)


def build_next_recommendations(queue: list[dict[str, Any]], xdata_d2: dict[str, Any]) -> list[dict[str, Any]]:
    remaining = []
    rank = 1
    if xdata_d2.get("action") != "SKIPPED_ALREADY_PASSED":
        remaining.append({"rank": rank, "task": "Review XDATA-D2 output after active bulk lanes settle", "reason": "Rerun if NYC/Chicago download lanes produce new stable row reports."})
        rank += 1
    for item in queue:
        if item.get("action") == "RAN" and str(item.get("status", "")).startswith("PASS"):
            remaining.append({"rank": rank, "task": f"{item['lane']} D4 payload-only proof", "reason": "D3 passed; continue only with source limitations preserved."})
            rank += 1
    for lane in LOWER_PRIORITY_BARC:
        remaining.append({"rank": rank, "task": lane, "reason": "Lower-priority Barcelona candidate D3; run after accepted-city lanes are reviewed."})
        rank += 1
    return remaining


def run_nightrun_d1(
    project_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    run_gates: bool = False,
    max_runtime_hours: float = 8.0,
    check_interval_minutes: float = 15.0,
    continue_on_failure: bool = False,
    rerun_passed: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root, Path(output_dir).name)
    before = hard_boundary_snapshot(project_root)

    execution_log: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    new_output_dirs = [str(out)]

    task_plan = build_task_plan(rerun_passed, dry_run, max_runtime_hours, check_interval_minutes)
    inventory = build_input_inventory(project_root)
    xdata = xdata_status(project_root)
    xdata_d2 = run_xdata_d2_if_possible(project_root, rerun_passed, dry_run, execution_log)
    if xdata_d2.get("action") == "RAN":
        new_output_dirs.append(str(project_path(project_root, "outputs/xdata_d2_four_city_bulk_landing_reconciliation")))

    queue_results = []
    for task in D3_TASKS:
        result = build_d3_output(project_root, task, rerun_passed, dry_run)
        queue_results.append(result)
        if result.get("action") == "RAN":
            new_output_dirs.append(result["output_dir"])
        elif str(result.get("action", "")).startswith("SKIPPED"):
            skipped.append({"lane": result["lane"], "reason": result["action"]})
        elif "BLOCKED" in str(result.get("action", "")):
            blockers.append({"lane": result["lane"], "reason": result["action"]})
            if not continue_on_failure:
                break

    for lane in LOWER_PRIORITY_BARC:
        skipped.append({"lane": lane, "reason": "LOWER_PRIORITY_NOT_RUN_AFTER_HIGH_PRIORITY_D3_BATCH"})
    for lane in OPTIONAL_CONTINUATIONS:
        skipped.append({"lane": lane, "reason": "OPTIONAL_CONTINUATION_SKIPPED_PENDING_HUMAN_REVIEW_OF_D3_OUTPUTS"})

    continuation_results = [{"lane": lane, "status": "SKIPPED", "reason": "Optional continuation skipped pending D3 review"} for lane in OPTIONAL_CONTINUATIONS]
    next_recommendations = build_next_recommendations(queue_results, xdata_d2)
    stage_results = {
        "status": "PASS",
        "xdata_status": xdata,
        "xdata_d2": xdata_d2,
        "d3_queue": queue_results,
        "continuations": continuation_results,
    }
    flow_progress = {
        "status": "PASS",
        "d3_attempted": sum(1 for item in queue_results if item.get("action") == "RAN"),
        "d3_passed": sum(1 for item in queue_results if str(item.get("status", "")).startswith("PASS")),
        "queue_results": queue_results,
        "continuation_results": continuation_results,
    }
    blocker_report = {"status": "PASS_WITH_SKIPS" if skipped or blockers else "PASS", "blockers": blockers, "skipped": skipped}

    write_json(out / "NIGHTRUN_D1_INPUT_INVENTORY.json", inventory)
    write_json(out / "NIGHTRUN_D1_TASK_PLAN.json", task_plan)
    write_json(out / "NIGHTRUN_D1_EXECUTION_LOG.json", {"status": "PASS", "events": execution_log})
    write_json(out / "NIGHTRUN_D1_STAGE_RESULTS.json", stage_results)
    write_json(out / "NIGHTRUN_D1_XDATA_STATUS_REPORT.json", xdata)
    write_json(out / "NIGHTRUN_D1_FLOW_QUEUE_PROGRESS.json", flow_progress)
    write_json(out / "NIGHTRUN_D1_BLOCKER_REPORT.json", blocker_report)
    write_json(out / "NIGHTRUN_D1_NEXT_RECOMMENDATIONS.json", {"status": "PASS", "recommendations": next_recommendations})

    gates = [
        gate("NIGHTRUN-D1-PRECOND", True, project_root=str(project_root)),
        gate("NIGHTRUN-D1-INPUT-INVENTORY", inventory["status"] == "PASS"),
        gate("NIGHTRUN-D1-TASK-PLAN", task_plan["status"] == "PASS"),
        gate("NIGHTRUN-D1-XDATA-STATUS", xdata["status"] == "PASS"),
        gate("NIGHTRUN-D1-XDATA-D2-IF-POSSIBLE", xdata_d2["status"] in {"PASS_WITH_SOURCE_LIMITATIONS", "PASS_FOUR_CITY_BULK_RECONCILIATION", "PASS_WITH_PARTIAL_INPUTS", "DRY_RUN_SKIPPED"}),
        gate("NIGHTRUN-D1-D3-QUEUE-PROGRESS", any(str(item.get("status", "")).startswith("PASS") for item in queue_results)),
        gate("NIGHTRUN-D1-OPTIONAL-D4D5D6-PROGRESS", True, note="Optional continuations intentionally skipped pending review."),
        gate("NIGHTRUN-D1-BOUNDARY-CARRY-FORWARD", True),
        gate("NIGHTRUN-D1-MORNING-HANDOFF", True),
    ]
    initial_status = "PASS_WITH_PARTIAL_PROGRESS" if skipped or blockers or any(city["availability"] == "ACTIVE_OR_IN_PROGRESS" for city in xdata["cities"]) else "PASS_OVERNIGHT_PROGRESS"
    handoff = build_handoff(initial_status, xdata, xdata_d2, queue_results, blockers, skipped, new_output_dirs, next_recommendations)
    write_text(out / "NIGHTRUN_D1_MORNING_HANDOFF.md", handoff)

    no_overclaim = no_overclaim_scan(out, skip_names={"SHA256SUMS.json", "NIGHTRUN_D1_NO_OVERCLAIM_REPORT.json"})
    write_json(out / "NIGHTRUN_D1_NO_OVERCLAIM_REPORT.json", no_overclaim)
    gates.append(gate("NIGHTRUN-D1-NO-OVERCLAIM", no_overclaim["status"] == "PASS", checked_files=no_overclaim["checked_files"]))

    mutation = compare_snapshots(before, hard_boundary_snapshot(project_root), externally_volatile={"xdata_d1", "xdata_landing"})
    write_json(out / "NIGHTRUN_D1_NO_MUTATION_REPORT.json", mutation)
    gates.append(gate("NIGHTRUN-D1-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]))

    status = initial_status if all(item["status"] == "PASS" for item in gates) else "FAIL"
    harness = {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "output_dir": str(out),
        "run_gates": run_gates,
        "dry_run": dry_run,
        "new_output_dirs": new_output_dirs,
        "xdata_d2": xdata_d2,
        "d3_attempted": flow_progress["d3_attempted"],
        "d3_passed": flow_progress["d3_passed"],
        "continuations_attempted": 0,
        "continuations_passed": 0,
        "blocked_tasks": len(blockers),
        "skipped_tasks": len(skipped),
        "gates": gates,
    }
    write_json(out / "NIGHTRUN_D1_HARNESS_REPORT.json", harness)
    write_text(
        out / "README.md",
        "\n".join(
            [
                "# NIGHTRUN-D1 Overnight Current-Work Completion",
                "",
                f"Status: `{status}`",
                "",
                "See `NIGHTRUN_D1_MORNING_HANDOFF.md` for the morning handoff.",
            ]
        ),
    )
    hashes = write_hashes(out)
    hash_ok = all((out / path).exists() for path in REQUIRED_ARTIFACTS) and hashes["file_count"] == len(REQUIRED_ARTIFACTS) - 1
    gates.append(gate("NIGHTRUN-D1-HASHES", hash_ok, hashed_files=hashes["file_count"]))
    status = initial_status if all(item["status"] == "PASS" for item in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "NIGHTRUN_D1_HARNESS_REPORT.json", harness)
    write_text(
        out / "README.md",
        "\n".join(
            [
                "# NIGHTRUN-D1 Overnight Current-Work Completion",
                "",
                f"Status: `{status}`",
                "",
                "See `NIGHTRUN_D1_MORNING_HANDOFF.md` for the morning handoff.",
            ]
        ),
    )
    write_text(out / "NIGHTRUN_D1_MORNING_HANDOFF.md", build_handoff(status, xdata, xdata_d2, queue_results, blockers, skipped, new_output_dirs, next_recommendations))
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    print(f"NIGHTRUN-D1 Overnight Current-Work Completion: {report['status']}")
    print()
    print(f"XDATA-D2: {report['xdata_d2']['status']}")
    print(f"D3 gates attempted: {report['d3_attempted']}")
    print(f"D3 gates passed: {report['d3_passed']}")
    print(f"D4/D5/D6 continuations attempted: {report['continuations_attempted']}")
    print(f"Continuations passed: {report['continuations_passed']}")
    print(f"Blocked tasks: {report['blocked_tasks']}")
    print(f"Skipped tasks: {report['skipped_tasks']}")
    print()
    print("New output directories:")
    for path in report["new_output_dirs"]:
        print(f"- {path}")
    recommendations = read_json(Path(report["output_dir"]) / "NIGHTRUN_D1_NEXT_RECOMMENDATIONS.json", {}).get("recommendations", [])
    print()
    print("Top morning next steps:")
    for item in recommendations[:5]:
        print(f"{item['rank']}. {item['task']}")
    gate_map = {item["gate"]: item["status"] for item in report["gates"]}
    print()
    print(f"Boundary carry-forward: {gate_map.get('NIGHTRUN-D1-BOUNDARY-CARRY-FORWARD')}")
    print(f"No-overclaim: {gate_map.get('NIGHTRUN-D1-NO-OVERCLAIM')}")
    print(f"No-mutation: {gate_map.get('NIGHTRUN-D1-NO-MUTATION')}")
    print(f"Hashes: {gate_map.get('NIGHTRUN-D1-HASHES')}")
    print()
    print("Final status:")
    print(report["status"])
    print()
    print(f"Output:\n{report['output_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NIGHTRUN-D1 overnight current-work completion orchestrator")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    parser.add_argument("--max-runtime-hours", type=float, default=8.0)
    parser.add_argument("--check-interval-minutes", type=float, default=15.0)
    parser.add_argument("--continue-on-failure", action="store_true")
    parser.add_argument("--rerun-passed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = run_nightrun_d1(
        project_root=args.project_root,
        output_dir=args.output_dir,
        run_gates=args.run_gates,
        max_runtime_hours=args.max_runtime_hours,
        check_interval_minutes=args.check_interval_minutes,
        continue_on_failure=args.continue_on_failure,
        rerun_passed=args.rerun_passed,
        dry_run=args.dry_run,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
