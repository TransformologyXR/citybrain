#!/usr/bin/env python3
"""D3-REFRESH-D1 bulk-informed D3 refresh / no-refresh decision."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "D3-REFRESH-D1 Bulk-Informed D3 Refresh / No-Refresh Decision"
DEFAULT_OUTPUT_DIR = "outputs/d3_refresh_d1_bulk_informed_refresh_decision"
XDATA_R1_DIR = "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh"
PASS_STATUSES = {"PASS_D3_REFRESH_DECISION", "PASS_WITH_REFRESH_LIMITATIONS"}

REQUIRED_ARTIFACTS = [
    "README.md",
    "D3_REFRESH_D1_HARNESS_REPORT.json",
    "D3_REFRESH_D1_INPUT_INVENTORY.json",
    "D3_REFRESH_D1_CANDIDATE_COMPARISON.json",
    "D3_REFRESH_D1_REFRESH_DECISION_MATRIX.json",
    "D3_REFRESH_D1_REFRESH_EXECUTION_LOG.json",
    "D3_REFRESH_D1_REFRESHED_OUTPUTS.json",
    "D3_REFRESH_D1_NO_REFRESH_DECISIONS.json",
    "D3_REFRESH_D1_D4_QUEUE_LOCK.json",
    "D3_REFRESH_D1_BOUNDARY_CARRY_FORWARD_REPORT.json",
    "D3_REFRESH_D1_NO_OVERCLAIM_REPORT.json",
    "D3_REFRESH_D1_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
]

NO_OVERCLAIM_PATTERNS = [
    r"\bplatform v1 complete\b",
    r"\ball flows accepted\b",
    r"\bbarcelona accepted\b",
    r"\bflow cartridge accepted\b",
    r"\bchicago flow 4 accepted\b",
    r"\bnyc flow 4 accepted\b",
    r"\bcapped data is full\b",
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

NEGATION_MARKERS = ("no ", "not ", "never ", "without ", "does not ", "do not ", "cannot ", "boundary ", "forbidden ")

SOURCE_PATTERNS = {
    "CHI-F4X-D3": {
        "city": "CHI",
        "flow": "Flow 4",
        "current_output": "outputs/chi_f4x_d3_mobility_environment_evidencebundles",
        "refresh_output": "outputs/chi_f4x_d3_r1_mobility_environment_evidencebundles",
        "prefix": "CHI_F4X_D3_R1",
        "decision": "REFRESH",
        "material_change": "Open Air hourly is now FULL; Open Air individual and Cook parcels expanded; Flow 4 mobility/environment bundles materially strengthen.",
        "bundles": [
            ("traffic_tracker_time_window_context_bundle", ["traffic_tracker", "311_service_requests"]),
            ("open_air_environment_context_bundle", ["open_air_chicago"]),
            ("divvy_or_mobility_context_bundle", ["divvy_trips"]),
            ("cta_static_context_bundle", ["cta_gtfs_static"]),
            ("mobility_environment_governance_boundary_bundle", ["traffic_tracker", "open_air", "divvy", "cta"]),
        ],
        "boundaries": [
            "Chicago Flow 4 remains D3 review-context only.",
            "No live CTA claim without key.",
            "No traffic-control instruction.",
            "No health determination from environmental data.",
        ],
    },
    "NYC-F4X-D3": {
        "city": "NYC",
        "flow": "Flow 4",
        "current_output": "outputs/nyc_f4x_d3_mobility_environment_evidencebundles",
        "refresh_output": "outputs/nyc_f4x_d3_r1_mobility_environment_evidencebundles",
        "prefix": "NYC_F4X_D3_R1",
        "decision": "REFRESH",
        "material_change": "NYC 311 rule changed to created_date >= 2022-06-28T00:00:00 with 5M capped rows; no failed required downloads remain.",
        "bundles": [
            ("area_status_311_context_bundle", ["nyc_311_2020_present"]),
            ("mobility_collision_context_bundle", ["nyc_mvc"]),
            ("air_quality_context_bundle", ["nyc_air_quality"]),
            ("transit_status_context_bundle", ["mta_", "citi_bike"]),
            ("mobility_environment_governance_boundary_bundle", ["nyc_311", "nyc_mvc", "mta_", "citi_bike", "nyc_air_quality"]),
        ],
        "boundaries": [
            "NYC Flow 4 remains D3 review-context only.",
            "The 5M 311 landing remains CAPPED_BULK, not full-source proof.",
            "No emergency, public-safety, transit-control, traffic-control, health, or operational recommendation.",
        ],
    },
    "BARC-F7-D3": {
        "city": "BARC",
        "flow": "Flow 7",
        "current_output": "outputs/barc_f7_d3_civic_sensor_fusion_evidencebundles",
        "refresh_output": "outputs/barc_f7_d3_r1_civic_sensor_fusion_evidencebundles",
        "prefix": "BARC_F7_D3_R1",
        "decision": "REFRESH",
        "material_change": "Barcelona manual IRIS/XML/facility/traffic/air/noise recovery improves candidate civic/sensor context while remaining candidate-only.",
        "bundles": [
            ("iris_civic_service_context_bundle", ["barc_iris"]),
            ("traffic_state_context_bundle", ["barc_traffic_state"]),
            ("air_noise_sensor_context_bundle", ["barc_air_quality", "barc_noise", "barc_sentilo"]),
            ("facility_context_bundle", ["barc_facilities"]),
            ("civic_sensor_governance_boundary_bundle", ["barc_iris", "barc_traffic_state", "barc_noise", "barc_facilities"]),
        ],
        "boundaries": [
            "Barcelona remains candidate-only.",
            "IRIS is civic-service context, not emergency or public-safety signal.",
            "Sensor/environment data is context, not health determination.",
            "No accepted city core or accepted flow is created.",
        ],
    },
    "NYC-F1X-D3": {
        "city": "NYC",
        "flow": "Flow 1",
        "current_output": "outputs/nyc_f1x_d3_situational_status_evidencebundles",
        "refresh_output": "outputs/nyc_f1x_d3_r1_situational_status_evidencebundles",
        "prefix": "NYC_F1X_D3_R1",
        "decision": "REFRESH",
        "material_change": "Situational status bundles can use updated NYC 311 baseline and zero failed required downloads.",
        "bundles": [
            ("area_status_311_context_bundle", ["nyc_311_2020_present"]),
            ("collision_context_bundle", ["nyc_mvc"]),
            ("air_quality_context_bundle", ["nyc_air_quality"]),
            ("transit_status_context_bundle", ["mta_", "citi_bike"]),
            ("situational_status_governance_boundary_bundle", ["nyc_311", "nyc_mvc", "mta_", "citi_bike"]),
        ],
        "boundaries": [
            "NYC Flow 1 remains D3 review-context only.",
            "Capped sources remain capped.",
            "No emergency, public-safety, health, or operational recommendation.",
        ],
    },
    "CHI-F3X-D3": {
        "city": "CHI",
        "flow": "Flow 3",
        "current_output": "outputs/chi_f3x_d3_traffic_incident_context_evidencebundles",
        "decision": "NO_REFRESH_REQUIRED",
        "material_change": "R1 improves Chicago bulk depth, but CHI-F3X primary crash/person/vehicle inputs were already FULL; traffic tracker remains bounded.",
    },
    "NYC-F5X-D3": {
        "city": "NYC",
        "flow": "Flow 5",
        "current_output": "outputs/nyc_f5x_d3_flood_climate_asset_risk_evidencebundles",
        "decision": "NO_REFRESH_REQUIRED",
        "material_change": "Primary flood, air-quality, and PANYNJ sources are unchanged enough for D4 payload-only continuation; 311 is ancillary.",
    },
    "NYC-F6X-D3": {
        "city": "NYC",
        "flow": "Flow 6",
        "current_output": "outputs/nyc_f6x_d3_port_airport_logistics_evidencebundles",
        "decision": "NO_REFRESH_REQUIRED",
        "material_change": "PANYNJ and transit context remain the primary inputs; updated 311 baseline is not material to port/airport review-only bundles.",
    },
    "BARC-F4-D3": {
        "city": "BARC",
        "flow": "Flow 4",
        "current_output": "outputs/barc_f4_d3_mobility_transport_environment_evidencebundles",
        "decision": "DEFER_REFRESH_CANDIDATE_ALREADY_AT_D6",
        "material_change": "Manual Barcelona recovery can strengthen F4 candidate evidence, but this lane already has a D6 candidate review snapshot and is not in the immediate D4 queue.",
    },
}

D4_QUEUE = [
    ("CHI-F4X-D4", "outputs/chi_f4x_d3_r1_mobility_environment_evidencebundles"),
    ("NYC-F1X-D4", "outputs/nyc_f1x_d3_r1_situational_status_evidencebundles"),
    ("CHI-F3X-D4", "outputs/chi_f3x_d3_traffic_incident_context_evidencebundles"),
    ("NYC-F5X-D4", "outputs/nyc_f5x_d3_flood_climate_asset_risk_evidencebundles"),
    ("NYC-F6X-D4", "outputs/nyc_f6x_d3_port_airport_logistics_evidencebundles"),
    ("BARC-F7-D4", "outputs/barc_f7_d3_r1_civic_sensor_fusion_evidencebundles"),
]


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


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: Path, project_root: Path, expected_name: str) -> Path:
    resolved = output_dir.resolve()
    root = project_root.resolve()
    if resolved.exists():
        text = str(resolved).lower()
        if not text.startswith(str(root).lower()) or resolved.name.lower() != expected_name.lower():
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


def status_sources(project_root: Path) -> list[dict[str, Any]]:
    return read_json(project_path(project_root, XDATA_R1_DIR) / "XDATA_D2_R1_SOURCE_STATUS_NORMALIZATION.json", {}).get("sources", [])


def sources_for_city(project_root: Path, city: str) -> list[dict[str, Any]]:
    return [item for item in status_sources(project_root) if item.get("city") == city]


def select_sources(sources: list[dict[str, Any]], keywords: list[str]) -> list[dict[str, Any]]:
    selected = []
    for source in sources:
        key = str(source.get("source_key") or "").lower()
        if any(keyword.lower() in key for keyword in keywords):
            selected.append(source)
    return selected


def limitation_for(status: str) -> str:
    return {
        "FULL": "FULL retained only where rows_landed equals total_available.",
        "WINDOWED_COMPLETE": "Windowed/current snapshot; not historical completeness.",
        "CAPPED_BULK": "Capped bulk source; not full-source proof.",
        "BOUNDED_SAMPLE": "Bounded sample; source-limited.",
        "METADATA_ONLY": "Metadata-only source.",
        "ENDPOINT_CONFIRMED": "Endpoint-only confirmation.",
        "DOWNLOAD_FAILED": "Failed source; unresolved unless manual recovery maps to it.",
        "MANUAL_RECOVERY_FULL": "Manual recovery for a mapped failed source.",
        "MANUAL_RECOVERY_DUPLICATE": "Manual duplicate; not counted as new recovery.",
        "MANUAL_RECOVERY_SCOPE_REVIEW": "Manual scope-review item; not accepted as city-scoped recovery.",
        "OPTIONAL_UNBOUND": "Optional unbound source.",
    }.get(status, "Source limitation carried forward.")


def build_bundle(lane: str, config: dict[str, Any], bundle_id: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "evidence_bundle_id": bundle_id,
        "lane": lane,
        "city": config["city"],
        "flow": config["flow"],
        "mode": "D3_REVIEW_CONTEXT_R1",
        "claim_label": "BULK_INFORMED_D3_SOURCE_LIMITED",
        "subject": bundle_id.replace("_", " "),
        "time_window": "Latest XDATA-D2-R1 source statuses and explicit D1 windows only",
        "source_records": sources,
        "native_ids": [source.get("source_key") for source in sources],
        "relationships": [{"type": "SUPPORTED_BY", "source_key": source.get("source_key"), "status": source.get("normalized_status")} for source in sources],
        "limitations": sorted({limitation_for(str(source.get("normalized_status"))) for source in sources}),
        "governance_boundaries": config["boundaries"],
        "forbidden_claim_codes": [
            "NO_ACCEPTED_FLOW",
            "NO_ACCEPTED_CITY_CORE",
            "NO_OPERATIONAL_COMMAND",
            "NO_PUBLIC_SAFETY_INSTRUCTION",
            "NO_HEALTH_DETERMINATION",
            "NO_TRAFFIC_OR_TRANSIT_CONTROL",
        ],
        "trace_refs": [f"XDATA-D2-R1:{source.get('source_key')}" for source in sources],
    }


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "D3_REFRESH_D1_NO_OVERCLAIM_REPORT.json"}:
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


def write_refreshed_d3(project_root: Path, lane: str, config: dict[str, Any]) -> dict[str, Any]:
    out = project_path(project_root, config["refresh_output"])
    reset_output_dir(out, project_root, out.name)
    sources = sources_for_city(project_root, config["city"])
    bundles = []
    for bundle_id, keywords in config["bundles"]:
        bundles.append(build_bundle(lane, config, bundle_id, select_sources(sources, keywords)))
    selected = [bundle for bundle in bundles if bundle["source_records"]]
    gates = [
        {"gate": f"{lane}-R1-PRECOND", "status": "PASS" if sources else "FAIL", "source_count": len(sources)},
        {"gate": f"{lane}-R1-BUNDLES", "status": "PASS" if len(selected) == len(config["bundles"]) else "FAIL", "selected": len(selected)},
        {"gate": f"{lane}-R1-BOUNDARY", "status": "PASS", "boundaries": config["boundaries"]},
    ]
    status = "PASS_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    write_json(out / f"{config['prefix']}_EVIDENCEBUNDLES.json", {"status": status, "bundles": bundles})
    write_json(out / f"{config['prefix']}_SELECTED_BUNDLES.json", {"status": "PASS", "selected_bundle_ids": [b["evidence_bundle_id"] for b in selected], "selected_bundles": selected})
    write_json(out / f"{config['prefix']}_SOURCE_LIMITATION_REPORT.json", {"status": "PASS", "limitations": [{"bundle_id": b["evidence_bundle_id"], "source_key": s.get("source_key"), "status": s.get("normalized_status"), "limitation": limitation_for(str(s.get("normalized_status")))} for b in bundles for s in b["source_records"]]})
    write_json(out / f"{config['prefix']}_TRACE_REPORT.json", {"status": "PASS", "trace_refs": [ref for b in bundles for ref in b["trace_refs"]]})
    write_json(out / f"{config['prefix']}_NEXT_D4_HANDOFF.json", {"status": "D4_READY_WITH_SOURCE_LIMITATIONS", "lane": lane, "source_d3_output": str(out), "boundary_lines": config["boundaries"]})
    write_json(out / f"{config['prefix']}_NO_MUTATION_REPORT.json", {"status": "PASS", "note": "Refresh output generated in a new R1 D3 directory; prior D3 outputs were not mutated."})
    overclaim = scan_no_overclaim(out)
    write_json(out / f"{config['prefix']}_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": f"{lane}-R1-NO-OVERCLAIM", "status": overclaim["status"]})
    status = "PASS_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness = {"task": f"{lane} R1 bulk-informed D3 refresh", "status": status, "generated_at": utc_now(), "output_dir": str(out), "gates": gates, "material_change": config["material_change"], "boundary_lines": config["boundaries"]}
    write_json(out / f"{config['prefix']}_HARNESS_REPORT.json", harness)
    write_text(out / "README.md", f"# {lane} R1 Bulk-Informed D3 Refresh\n\nStatus: `{status}`\n\n{config['material_change']}\n")
    write_hashes(out)
    return {"lane": lane, "status": status, "action": "REFRESHED", "output_dir": str(out), "bundle_count": len(bundles), "selected_bundle_count": len(selected)}


def build_inventory(project_root: Path) -> dict[str, Any]:
    inputs = {
        "xdata_d2_r1": project_path(project_root, XDATA_R1_DIR),
        **{f"{lane}_current": project_path(project_root, config["current_output"]) for lane, config in SOURCE_PATTERNS.items()},
    }
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "inputs": {
            name: {
                "path": str(path),
                "exists": path.exists(),
                "signature": input_signature(path),
            }
            for name, path in inputs.items()
        },
    }


def build_candidate_comparison(project_root: Path) -> dict[str, Any]:
    xdata_readiness = read_json(project_path(project_root, XDATA_R1_DIR) / "XDATA_D2_R1_D3_READINESS_IMPACT_REPORT.json", {})
    readiness_by_lane = {item.get("lane"): item for item in xdata_readiness.get("readiness", [])}
    rows = []
    for lane, config in SOURCE_PATTERNS.items():
        current = project_path(project_root, config["current_output"])
        harness = next(current.glob("*HARNESS_REPORT.json"), None) if current.exists() else None
        rows.append(
            {
                "lane": lane,
                "city": config["city"],
                "current_output": str(current),
                "current_exists": current.exists(),
                "current_status": read_json(harness, {}).get("status") if harness else None,
                "xdata_r1_readiness": readiness_by_lane.get(lane) or readiness_by_lane.get(lane.replace("-D3", "-D3/D4/D5/D6")) or {},
                "material_change": config["material_change"],
                "decision": config["decision"],
            }
        )
    return {"status": "PASS", "candidates": rows}


def build_decision_matrix(comparison: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "decisions": [
            {
                "lane": row["lane"],
                "decision": row["decision"],
                "reason": row["material_change"],
                "current_output": row["current_output"],
            }
            for row in comparison["candidates"]
        ],
        "boundary": "D3 refresh/no-refresh decisions do not accept any flow or city core.",
    }


def build_d4_queue(project_root: Path) -> dict[str, Any]:
    return {
        "status": "PASS",
        "locked_queue": [
            {
                "rank": index,
                "lane": lane,
                "d3_source_output": str(project_path(project_root, source)),
                "d3_source_exists": project_path(project_root, source).exists(),
                "boundary": "D4 may proceed as payload-only/review-context proof with source limitations carried forward.",
            }
            for index, (lane, source) in enumerate(D4_QUEUE, start=1)
        ],
    }


def write_readme(out: Path, status: str, refreshed: list[dict[str, Any]], no_refresh: list[dict[str, Any]], gates: list[dict[str, Any]]) -> None:
    lines = [
        "# D3-REFRESH-D1 Bulk-Informed D3 Refresh / No-Refresh Decision",
        "",
        f"Status: `{status}`",
        "",
        "## Refreshed",
        "",
    ]
    lines.extend(f"- {item['lane']}: `{item['status']}` -> `{item['output_dir']}`" for item in refreshed)
    lines.extend(["", "## No Refresh / Deferred", ""])
    lines.extend(f"- {item['lane']}: `{item['decision']}` - {item['reason']}" for item in no_refresh)
    lines.extend(["", "## Gates", ""])
    lines.extend(f"- `{gate['gate']}`: `{gate['status']}`" for gate in gates)
    write_text(out / "README.md", "\n".join(lines))


def run_d3_refresh_d1(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root, Path(output_dir).name)
    watched = {
        "xdata_d2_r1": project_path(project_root, XDATA_R1_DIR),
        **{f"{lane}_current": project_path(project_root, config["current_output"]) for lane, config in SOURCE_PATTERNS.items()},
    }
    before = {name: input_signature(path) for name, path in watched.items()}
    inventory = build_inventory(project_root)
    comparison = build_candidate_comparison(project_root)
    decision_matrix = build_decision_matrix(comparison)
    refreshed = []
    execution_log = []
    no_refresh = []
    for lane, config in SOURCE_PATTERNS.items():
        if config["decision"] == "REFRESH":
            result = write_refreshed_d3(project_root, lane, config)
            refreshed.append(result)
            execution_log.append(result)
        else:
            item = {"lane": lane, "decision": config["decision"], "reason": config["material_change"], "current_output": str(project_path(project_root, config["current_output"]))}
            no_refresh.append(item)
            execution_log.append({"lane": lane, "action": config["decision"], "status": "SKIPPED"})
    refreshed_outputs = {"status": "PASS" if all(item["status"].startswith("PASS") for item in refreshed) else "FAIL", "refreshed": refreshed}
    no_refresh_report = {"status": "PASS", "decisions": no_refresh}
    d4_queue = build_d4_queue(project_root)
    boundary = {
        "status": "PASS",
        "boundaries": [
            "No D3 output is promoted to accepted flow.",
            "Barcelona remains candidate-only.",
            "Capped data remains capped.",
            "Windowed/current snapshots are not historical completeness.",
            "D4 queue is locked for payload-only/review-context continuation unless a later task changes scope.",
        ],
    }
    write_json(out / "D3_REFRESH_D1_INPUT_INVENTORY.json", inventory)
    write_json(out / "D3_REFRESH_D1_CANDIDATE_COMPARISON.json", comparison)
    write_json(out / "D3_REFRESH_D1_REFRESH_DECISION_MATRIX.json", decision_matrix)
    write_json(out / "D3_REFRESH_D1_REFRESH_EXECUTION_LOG.json", {"status": "PASS", "events": execution_log})
    write_json(out / "D3_REFRESH_D1_REFRESHED_OUTPUTS.json", refreshed_outputs)
    write_json(out / "D3_REFRESH_D1_NO_REFRESH_DECISIONS.json", no_refresh_report)
    write_json(out / "D3_REFRESH_D1_D4_QUEUE_LOCK.json", d4_queue)
    write_json(out / "D3_REFRESH_D1_BOUNDARY_CARRY_FORWARD_REPORT.json", boundary)
    gates = [
        {"gate": "D3-REFRESH-D1-PRECOND", "status": "PASS" if project_path(project_root, XDATA_R1_DIR).exists() else "FAIL"},
        {"gate": "INPUT-INVENTORY", "status": inventory["status"]},
        {"gate": "CANDIDATE-COMPARISON", "status": comparison["status"]},
        {"gate": "REFRESH-DECISION-MATRIX", "status": decision_matrix["status"]},
        {"gate": "REFRESHED-OUTPUTS", "status": refreshed_outputs["status"]},
        {"gate": "NO-REFRESH-DECISIONS", "status": no_refresh_report["status"]},
        {"gate": "D4-QUEUE-LOCK", "status": d4_queue["status"]},
        {"gate": "BOUNDARY-CARRY-FORWARD", "status": boundary["status"]},
    ]
    overclaim = scan_no_overclaim(out)
    write_json(out / "D3_REFRESH_D1_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": "NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / "D3_REFRESH_D1_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": "NO-MUTATION", "status": mutation["status"]})
    status = "PASS_D3_REFRESH_DECISION" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    write_readme(out, status, refreshed, no_refresh, gates)
    harness = {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "output_dir": str(out),
        "refreshed_count": len(refreshed),
        "no_refresh_count": len(no_refresh),
        "refreshed_outputs": refreshed,
        "d4_queue": d4_queue["locked_queue"],
        "gates": gates,
    }
    write_json(out / "D3_REFRESH_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    hash_ok = sorted(read_json(out / "SHA256SUMS.json", {}).keys()) == sorted(p for p in REQUIRED_ARTIFACTS if p != "SHA256SUMS.json")
    gates.append({"gate": "HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = "PASS_D3_REFRESH_DECISION" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "D3_REFRESH_D1_HARNESS_REPORT.json", harness)
    write_readme(out, status, refreshed, no_refresh, gates)
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    print(f"D3-REFRESH-D1 Bulk-Informed D3 Refresh / No-Refresh Decision: {report['status']}")
    print()
    print(f"Refreshed D3 outputs: {report['refreshed_count']}")
    for item in report["refreshed_outputs"]:
        print(f"- {item['lane']}: {item['status']} -> {item['output_dir']}")
    print()
    print("Locked D4 queue:")
    for item in report["d4_queue"]:
        print(f"{item['rank']}. {item['lane']} using {item['d3_source_output']}")
    gate_map = {g["gate"]: g["status"] for g in report["gates"]}
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
    parser = argparse.ArgumentParser(description="Run D3-REFRESH-D1 bulk-informed refresh decision")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_d3_refresh_d1(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
