from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "NYC Expansion Potential D1"
DEFAULT_F3_ACCEPTED_DIR = "outputs/f3_nyc_d9_flow3_accepted_snapshot"
DEFAULT_HARVEST_DIR = "outputs/nyc_harvest_prep_v0_2"
DEFAULT_OUTPUT_DIR = "outputs/nyc_expansion_potential_d1"

ROOT_BOUNDARY_LINES = [
    "NYC Expansion Potential D1 creates readiness and feasibility contracts only.",
    "NYC Expansion Potential D1 does not ingest new live sources.",
    "NYC Expansion Potential D1 does not certify any new Flow as accepted.",
    "NYC Flow 3 remains the accepted incident/candidate-context/operator-review spine.",
    "All proposed Flow 6 logistics outputs are review-only and non-operational.",
]

F3_SPINE_REQUIRED_LANGUAGE = [
    "NYC Flow 3 is green as a governed incident-response / candidate-asset / operator-review cartridge over the current capped working-set source base.",
    "D3 candidate tax-lot context is not certified affected buildings/assets.",
    "D4 route plans are operator-review itineraries, not emergency dispatch or navigable routing.",
]

FORBIDDEN_PATTERNS = [
    r"\bcertifies? affected (?:buildings|assets)\b",
    r"\bcertified affected (?:buildings|assets)\b",
    r"\boperational command\b",
    r"\bairport command\b",
    r"\bport command\b",
    r"\bvessel instruction\b",
    r"\baircraft instruction\b",
    r"\bsafety-critical sequencing\b",
    r"\butility-network propagation\b",
    r"\bdispatch optimization\b",
    r"\bflow [1456] is accepted\b",
]

SOURCE_REGISTRY: dict[str, dict[str, Any]] = {
    "nyc_311_2020_present": {
        "label": "311 Service Requests from 2020 to Present",
        "provider": "NYC Open Data",
        "official_url": "https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9",
        "credential_note": "Public Socrata dataset; backend API names are stable per NYC Open Data update note.",
        "local_paths": [],
    },
    "nyc_311_2010_2019": {
        "label": "311 Service Requests from 2010 to 2019",
        "provider": "NYC Open Data",
        "official_url": "https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-2019/76ig-c548",
        "credential_note": "Public Socrata dataset.",
        "local_paths": [],
    },
    "nyc_mvc_crashes": {
        "label": "Motor Vehicle Collisions - Crashes",
        "provider": "NYC Open Data",
        "official_url": "https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95",
        "credential_note": "Public Socrata dataset.",
        "local_paths": [
            "outputs/f3_nyc_d9_flow3_accepted_snapshot/F3_NYC_D9_SOURCE_STATUS.json",
            "data/processed/nyc_flow2/collision_4486635.parquet",
        ],
    },
    "nyc_mvc_vehicles": {
        "label": "Motor Vehicle Collisions - Vehicles",
        "provider": "NYC Open Data",
        "official_url": "https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Vehicles/bm4k-52h4",
        "credential_note": "Public Socrata dataset; vehicle table is context, not the primary crash event table.",
        "local_paths": ["Motor_Vehicle_Collisions_-_Vehicles.csv"],
    },
    "nyc_dob_context": {
        "label": "DOB permits, filings, complaints, and PLUTO building context",
        "provider": "NYC Open Data / NYC Planning / NYC DOB",
        "official_url": "https://www.nyc.gov/site/planning/data-maps/open-data/dwn-pluto-mappluto.page",
        "credential_note": "Public building and parcel context. DOB/PLUTO context supports review, not asset certification.",
        "local_paths": [
            "nyc_pluto_25v4_arc_csv/pluto_25v4.csv",
            "data/processed/nyc/harvest_v0_2/discovery_staging/dob_complaints.parquet",
            "data/processed/nyc/harvest_v0_2/discovery_staging/dob_permit_issuance.parquet",
            "data/processed/nyc/harvest_v0_2/discovery_staging/dob_now_filings.parquet",
        ],
    },
    "mta_gtfs_rt": {
        "label": "MTA GTFS-RT feeds and service alerts",
        "provider": "MTA",
        "official_url": "https://api.mta.info/",
        "credential_note": "MTA says accounts and API keys are no longer required for NYC Subway, LIRR, Metro-North, and service-alert GTFS-RT feeds.",
        "local_paths": [],
    },
    "mta_gtfs_static": {
        "label": "MTA static GTFS schedules, routes, stops, and related data",
        "provider": "MTA",
        "official_url": "https://new.mta.info/developers",
        "credential_note": "Static GTFS supports schedule geography and service design context.",
        "local_paths": [],
    },
    "nyc_air_quality": {
        "label": "Air Quality",
        "provider": "NYC Open Data / NYC Health",
        "official_url": "https://data.cityofnewyork.us/Environment/Air-Quality/c3uy-2p5r",
        "credential_note": "Public environmental observations; context only, not health determinations.",
        "local_paths": [],
    },
    "nyc_flood_vulnerability_index": {
        "label": "New York City's Flood Vulnerability Index",
        "provider": "NYC Open Data / NYC Health",
        "official_url": "https://data.cityofnewyork.us/Environment/New-York-City-s-Flood-Vulnerability-Index/mrjc-v9pm",
        "credential_note": "Public flood vulnerability context for policy and resilience review.",
        "local_paths": [],
    },
    "nyc_flood_vulnerability_index_map": {
        "label": "New York City's Flood Vulnerability Index Map",
        "provider": "NYC Open Data / NYC Health",
        "official_url": "https://data.cityofnewyork.us/Environment/New-York-City-s-Flood-Vulnerability-Index-Map/4vym-qrg3",
        "credential_note": "Public flood vulnerability geometry/context.",
        "local_paths": [],
    },
    "dep_harbor_water_quality": {
        "label": "DEP harbor water quality and sampling station context",
        "provider": "NYC DEP / NYC Open Data",
        "official_url": "https://data.cityofnewyork.us/browse?q=harbor%20water%20quality",
        "credential_note": "Public water quality context; advisory interpretation remains outside this D1 contract.",
        "local_paths": [],
    },
    "ll84_energy_water": {
        "label": "Local Law 84 energy and water benchmarking",
        "provider": "NYC Open Data",
        "official_url": "https://data.cityofnewyork.us/browse?q=energy%20and%20water%20data%20disclosure",
        "credential_note": "Public annual benchmarking context for large buildings.",
        "local_paths": [],
    },
    "facility_context": {
        "label": "Public facilities and civic place context",
        "provider": "NYC Open Data",
        "official_url": "https://data.cityofnewyork.us/browse?q=facilities",
        "credential_note": "Facility context supports situational and proximity review only.",
        "local_paths": [],
    },
    "taxi_fhv_optional": {
        "label": "Taxi and FHV trip context",
        "provider": "NYC TLC / NYC Open Data",
        "official_url": "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page",
        "credential_note": "Optional mobility demand context. Use aggregated privacy-preserving views only.",
        "local_paths": [],
    },
    "citi_bike_optional": {
        "label": "Citi Bike system data",
        "provider": "Citi Bike / Lyft",
        "official_url": "https://citibikenyc.com/system-data",
        "credential_note": "Optional bikeshare context. Use aggregate station/trip products where appropriate.",
        "local_paths": [],
    },
    "panynj_air_passenger_traffic": {
        "label": "Air Passenger Traffic per Month, Port Authority of NY NJ",
        "provider": "Data NY / PANYNJ",
        "official_url": "https://data.ny.gov/Transportation/Air-Passenger-Traffic-per-Month-Port-Authority-of-/8pkr-4b7t",
        "credential_note": "Monthly aggregated passenger, cargo, flight, and aircraft-equipment-type airport traffic data.",
        "local_paths": [],
    },
    "panynj_airport_statistics": {
        "label": "PANYNJ airport traffic statistics",
        "provider": "Port Authority of New York and New Jersey",
        "official_url": "https://www.panynj.gov/airports/en/statistics-general-info.html",
        "credential_note": "PANYNJ says airport traffic data is available from January 2000-present.",
        "local_paths": [],
    },
    "panynj_cargo_tonnage": {
        "label": "PANYNJ cargo tonnage by airport",
        "provider": "Port Authority of New York and New Jersey / Data NY",
        "official_url": "https://data.ny.gov/browse?q=Port%20Authority%20cargo%20tonnage%20airport",
        "credential_note": "Candidate monthly cargo-tonnage context; landing step must bind an exact dataset endpoint before use.",
        "local_paths": [],
    },
    "path_regional_transport": {
        "label": "PATH and regional transport context",
        "provider": "PANYNJ",
        "official_url": "https://www.panynj.gov/path/en/schedules-maps.html",
        "credential_note": "Regional transport context only; not operational railway control.",
        "local_paths": [],
    },
}

SUBCARTRIDGES: dict[str, dict[str, Any]] = {
    "NYC-F1X-D1": {
        "name": "NYC Situational Status Expansion",
        "candidate_strength": "very_high",
        "output_slug": "nyc_f1x_d1_situational_status_expansion",
        "status": "PASS_WITH_SOURCE_LANDING_REQUIRED",
        "source_keys": [
            "nyc_311_2020_present",
            "nyc_311_2010_2019",
            "nyc_mvc_crashes",
            "nyc_mvc_vehicles",
            "nyc_dob_context",
            "mta_gtfs_rt",
            "nyc_air_quality",
            "nyc_flood_vulnerability_index",
            "facility_context",
        ],
        "dependencies": ["F3-NYC-D9 accepted snapshot", "NYC harvest prep v0.2", "Flow 3 incident/location context"],
        "boundary_lines": [
            "NYC-F1X-D1 is a situational-status expansion contract, not an accepted Flow 1 cartridge.",
            "NYC-F1X-D1 does not make operational recommendations.",
            "NYC-F1X-D1 does not make policing, dispatch, enforcement, health, emergency, or public-safety recommendations.",
            "NYC-F1X-D1 does not certify affected buildings/assets.",
            "MTA GTFS-RT is live transit context; service interpretation remains context for operator review.",
            "Air quality and flood observations are context signals, not health or emergency determinations.",
        ],
        "next_gate": "NYC-F1X-D2 source landing and area-status canonicalization",
        "acceptance_conditions": [
            "Bind 311, MVC, DOB/PLUTO, MTA, air, flood, and facility sources to canonical source manifests.",
            "Reuse Flow 3 affected-context and location confidence tiers as input context only.",
            "Produce deterministic borough/community-district/tax-lot status summaries with evidence bundles.",
            "Pass no-overclaim and no-mutation gates before any accepted Flow 1 claim.",
        ],
    },
    "NYC-F4X-D1": {
        "name": "NYC Mobility / Event / Environment Expansion",
        "candidate_strength": "very_high",
        "output_slug": "nyc_f4x_d1_mobility_event_environment_expansion",
        "status": "PASS_WITH_SOURCE_LANDING_REQUIRED",
        "source_keys": [
            "mta_gtfs_static",
            "mta_gtfs_rt",
            "nyc_mvc_crashes",
            "nyc_mvc_vehicles",
            "taxi_fhv_optional",
            "citi_bike_optional",
            "nyc_air_quality",
            "nyc_311_2020_present",
            "nyc_311_2010_2019",
        ],
        "dependencies": ["MTA static/GTFS-RT source landing", "MVC event context", "311 civic context"],
        "boundary_lines": [
            "NYC-F4X-D1 is a mobility/event/environment expansion contract, not an accepted Flow 4 cartridge.",
            "NYC-F4X-D1 does not issue transit, traffic, crowd, or event operations instructions.",
            "NYC-F4X-D1 does not optimize dispatch, routing, policing, or emergency response.",
            "Taxi/FHV and Citi Bike sources are optional and must use aggregate privacy-preserving products.",
            "MTA GTFS static is schedule geography; MTA GTFS-RT is service context for review.",
            "Air quality observations are context signals, not health determinations.",
        ],
        "next_gate": "NYC-F4X-D2 mobility source landing and stop/event context graph",
        "acceptance_conditions": [
            "Land exact MTA GTFS static and GTFS-RT feed manifests, including feed freshness checks.",
            "Build stop/route/service-alert context tied to NYC geography without operational instructions.",
            "Join collisions, 311, and environment signals to area/time windows with evidence bundles.",
            "Keep taxi/FHV and Citi Bike optional until aggregation/privacy contract is explicit.",
        ],
    },
    "NYC-F5X-D1": {
        "name": "NYC Flood / Climate / Asset-Risk Expansion",
        "candidate_strength": "high",
        "output_slug": "nyc_f5x_d1_flood_climate_asset_risk_expansion",
        "status": "PASS_WITH_BOUNDARY_LIMITATION",
        "source_keys": [
            "nyc_flood_vulnerability_index",
            "nyc_flood_vulnerability_index_map",
            "dep_harbor_water_quality",
            "ll84_energy_water",
            "nyc_air_quality",
            "nyc_dob_context",
            "facility_context",
        ],
        "dependencies": ["DOB/PLUTO building context", "flood and environment source landing"],
        "boundary_lines": [
            "NYC-F5X-D1 is a flood/climate/asset-context expansion contract, not an accepted Flow 5 cartridge.",
            "NYC-F5X-D1 provides flood/climate risk context only.",
            "NYC-F5X-D1 does not model certified utility-network propagation.",
            "NYC-F5X-D1 does not certify building safety, insurance, utility, or emergency determinations.",
            "Harbor water quality, rainfall, air quality, and benchmarking are context signals for analyst review.",
            "Building/parcel/facility context is proximity evidence, not affected-asset certification.",
        ],
        "next_gate": "NYC-F5X-D2 flood/climate source landing and parcel-context evidence model",
        "acceptance_conditions": [
            "Bind FVI/FVI map, DEP water quality, benchmarking, air, DOB/PLUTO, and facility sources to manifests.",
            "Separate hazard/vulnerability context from any certified utility or emergency conclusion.",
            "Generate parcel/facility context summaries with evidence provenance and limitation language.",
            "Pass explicit utility-network non-propagation boundary checks.",
        ],
    },
    "NYC-F6X-D1": {
        "name": "Port/Airport Logistics Sequencing Feasibility",
        "candidate_strength": "medium_high",
        "output_slug": "nyc_f6x_d1_port_airport_logistics_sequencing_feasibility",
        "status": "PASS_AS_REVIEW_ONLY_FEASIBILITY",
        "source_keys": [
            "panynj_air_passenger_traffic",
            "panynj_airport_statistics",
            "panynj_cargo_tonnage",
            "path_regional_transport",
            "mta_gtfs_static",
            "mta_gtfs_rt",
            "nyc_dob_context",
        ],
        "dependencies": ["PANYNJ monthly traffic/cargo source landing", "regional transport context", "construction/road-closure context if added"],
        "boundary_lines": [
            "NYC-F6X-D1 is a port/airport logistics feasibility contract, not an accepted Flow 6 cartridge.",
            "NYC-F6X-D1 is not oil/gas Flow 6.",
            "NYC-F6X-D1 is review-only operational plan proposal context.",
            "NYC-F6X-D1 does not provide airport or port operational command.",
            "NYC-F6X-D1 does not provide safety-critical sequencing.",
            "NYC-F6X-D1 does not provide vessel or aircraft instruction.",
            "PANYNJ airport datasets are monthly aggregated context, not live operational control feeds.",
        ],
        "next_gate": "NYC-F6X-D2 exact PANYNJ source landing and review-only sequence schema",
        "acceptance_conditions": [
            "Bind exact PANYNJ passenger, cargo, flight, and aircraft-equipment datasets to manifests.",
            "Define review-only plan proposal records that cannot be interpreted as command instructions.",
            "Use MTA/PATH and construction context as dependency/context signals only.",
            "Pass explicit no-command, no-vessel-instruction, and no-aircraft-instruction gates.",
        ],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except Exception:
            pass
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    files = sorted(path for path in output_dir.rglob("*") if path.is_file() and path.name != "SHA256SUMS.json")
    sums = {path.relative_to(output_dir).as_posix(): sha256_file(path) for path in files}
    write_json(output_dir / "SHA256SUMS.json", sums)
    expected = {path.relative_to(output_dir).as_posix() for path in files}
    return {
        "gate": "NYC-EXP-D1-HASHES",
        "status": "PASS" if sorted(sums) == sorted(expected) else "FAIL",
        "file_count": len(sums),
        "missing": sorted(expected - set(sums)),
        "extra": sorted(set(sums) - expected),
    }


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()):
            raise ValueError(f"Refusing to remove output outside workspace: {resolved}")
        if "nyc_expansion_potential_d1" not in resolved.name.lower():
            raise ValueError(f"Refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    output_dir.mkdir(parents=True, exist_ok=True)


def snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root.resolve())] = {"exists": False}
            continue
        files = [root] if root.is_file() else [p for p in sorted(root.rglob("*")) if p.is_file()]
        for path in files:
            stat = path.stat()
            entry = {"exists": True, "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
            if stat.st_size <= 5_000_000:
                entry["sha256"] = sha256_file(path)
            watched[str(path.resolve())] = entry
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, old in before.items():
        if old != after.get(key):
            changed.append({"path": key, "before": old, "after": after.get(key)})
    return {
        "gate": "NYC-EXP-D1-NO-MUTATION",
        "status": "PASS" if not changed else "FAIL",
        "checked_files": len(before),
        "changed_inputs": changed,
    }


def source_local_status(project_root: Path, source: dict[str, Any]) -> dict[str, Any]:
    paths = []
    landed = False
    for raw_path in source.get("local_paths", []):
        path = project_root / raw_path
        exists = path.exists()
        landed = landed or exists
        paths.append({"path": raw_path, "exists": exists})
    if not paths:
        status = "official_source_identified_not_landed"
    elif landed:
        status = "local_context_present"
    else:
        status = "local_path_declared_missing"
    return {"local_status": status, "local_paths": paths}


def build_source_ledger(project_root: Path, source_keys: list[str]) -> dict[str, Any]:
    rows = []
    for key in source_keys:
        source = dict(SOURCE_REGISTRY[key])
        source.update(source_local_status(project_root, source))
        rows.append({"source_key": key, **source})
    present = [row for row in rows if row["local_status"] == "local_context_present"]
    identified = [row for row in rows if row["local_status"] == "official_source_identified_not_landed"]
    missing = [row for row in rows if row["local_status"] == "local_path_declared_missing"]
    return {
        "status": "PASS" if rows and not missing else "WARN_WITH_MISSING_DECLARED_LOCAL_PATHS",
        "sources": rows,
        "local_context_present": len(present),
        "official_sources_identified_not_landed": len(identified),
        "missing_declared_local_paths": len(missing),
    }


def check_f3_spine(f3_dir: Path) -> dict[str, Any]:
    state_path = f3_dir / "F3_NYC_D9_ACCEPTED_STATE.json"
    state = read_json(state_path, {})
    headline = str(state.get("headline", ""))
    limitations = [str(item) for item in state.get("limitations", [])]
    status = str(state.get("status", ""))
    required_text = "\n".join([headline, *limitations])
    missing = [line for line in F3_SPINE_REQUIRED_LANGUAGE if line not in required_text]
    return {
        "gate": "NYC-EXP-D1-F3-SPINE",
        "status": "PASS" if state_path.exists() and status.startswith("PASS") and not missing else "FAIL",
        "f3_state_path": str(state_path),
        "f3_status": status,
        "missing_required_language": missing,
    }


def subcartridge_gate(code: str, output_dir: Path, spec: dict[str, Any], source_ledger: dict[str, Any]) -> dict[str, Any]:
    boundary_ok = bool(spec["boundary_lines"])
    source_ok = str(source_ledger.get("status", "")).startswith("PASS")
    acceptance_ok = len(spec.get("acceptance_conditions", [])) >= 3 and bool(spec.get("next_gate"))
    return {
        "gate": f"{code}-READINESS-CONTRACT",
        "status": "PASS" if boundary_ok and source_ok and acceptance_ok else "FAIL",
        "output_dir": str(output_dir),
        "candidate_strength": spec["candidate_strength"],
        "readiness_status": spec["status"],
        "checks": {
            "boundary_lines_present": boundary_ok,
            "source_ledger_present": source_ok,
            "acceptance_conditions_present": acceptance_ok,
        },
    }


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    checked = []
    findings = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS.json" or path.suffix.lower() not in {".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        checked.append(path.relative_to(output_dir).as_posix())
        lower = text.lower()
        for pattern in FORBIDDEN_PATTERNS:
            for match in re.finditer(pattern, lower):
                finding = text[max(0, match.start() - 80) : min(len(text), match.end() + 80)]
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern, "context": finding})
    allowed_patterns = {
        r"\boperational command\b",
        r"\bsafety-critical sequencing\b",
        r"\butility-network propagation\b",
        r"\bvessel instruction\b",
        r"\baircraft instruction\b",
    }
    filtered = []
    for finding in findings:
        context = finding["context"].lower()
        pattern = finding["pattern"]
        if pattern in allowed_patterns and any(prefix in context for prefix in ["does not provide", "does not model", "no "]):
            continue
        filtered.append(finding)
    return {
        "gate": "NYC-EXP-D1-NO-OVERCLAIM",
        "status": "PASS" if not filtered else "FAIL",
        "checked_files": checked,
        "findings": filtered,
    }


def render_acceptance_plan(code: str, spec: dict[str, Any], source_ledger: dict[str, Any]) -> str:
    lines = [
        f"# {code} - {spec['name']}",
        "",
        f"Candidate strength: {spec['candidate_strength']}",
        f"Readiness status: {spec['status']}",
        f"Next gate: {spec['next_gate']}",
        "",
        "## Boundary",
        "",
    ]
    lines.extend(f"- {line}" for line in spec["boundary_lines"])
    lines.extend(["", "## Acceptance Conditions", ""])
    lines.extend(f"- {line}" for line in spec["acceptance_conditions"])
    lines.extend(["", "## Source Landing Summary", ""])
    lines.append(f"- Local context present: {source_ledger['local_context_present']}")
    lines.append(f"- Official sources identified but not landed: {source_ledger['official_sources_identified_not_landed']}")
    lines.append(f"- Missing declared local paths: {source_ledger['missing_declared_local_paths']}")
    lines.extend(["", "## Dependencies", ""])
    lines.extend(f"- {item}" for item in spec["dependencies"])
    lines.append("")
    return "\n".join(lines)


def render_root_readme(harness: dict[str, Any]) -> str:
    lines = [
        "# NYC Expansion Potential D1",
        "",
        "This pack turns the NYC expansion recommendation into governed readiness contracts.",
        "",
        "## Boundary",
        "",
    ]
    lines.extend(f"- {line}" for line in ROOT_BOUNDARY_LINES)
    lines.extend(["", "## Run Summary", ""])
    for code, row in harness["subcartridges"].items():
        lines.append(f"- {code}: {row['name']} - {row['readiness_status']} ({row['candidate_strength']})")
    lines.extend(["", "## Gates", ""])
    for gate, status in harness["gates"].items():
        lines.append(f"- {gate}: {status}")
    lines.append("")
    return "\n".join(lines)


def run_nyc_expansion_potential_d1_gate(
    project_root: str | Path = ".",
    f3_accepted_dir: str | Path = DEFAULT_F3_ACCEPTED_DIR,
    harvest_dir: str | Path = DEFAULT_HARVEST_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    f3_dir = root / f3_accepted_dir
    harvest = root / harvest_dir
    out = root / output_dir

    watched_inputs = [
        f3_dir / "F3_NYC_D9_ACCEPTED_STATE.json",
        f3_dir / "F3_NYC_D9_SOURCE_STATUS.json",
        harvest / "harvest_prep_summary.json",
        harvest / "raw_harvest_inventory.json",
    ]
    before = snapshot(watched_inputs)
    reset_output_dir(out)

    f3_spine = check_f3_spine(f3_dir)
    gates: dict[str, str] = {f3_spine["gate"]: f3_spine["status"]}
    subcartridge_rows: dict[str, Any] = {}

    for code, spec in SUBCARTRIDGES.items():
        subdir = out / spec["output_slug"]
        source_ledger = build_source_ledger(root, spec["source_keys"])
        contract = {
            "cartridge": code,
            "name": spec["name"],
            "task": TASK_NAME,
            "generated_at": utc_now(),
            "candidate_strength": spec["candidate_strength"],
            "readiness_status": spec["status"],
            "dependencies": spec["dependencies"],
            "source_keys": spec["source_keys"],
            "next_gate": spec["next_gate"],
            "acceptance_conditions": spec["acceptance_conditions"],
            "boundary_lines": spec["boundary_lines"],
            "f3_spine_dependency": {
                "accepted_dir": str(f3_dir),
                "gate_status": f3_spine["status"],
            },
        }
        write_json(subdir / f"{code.replace('-', '_')}_READINESS_CONTRACT.json", contract)
        write_json(subdir / "source_ledger.json", source_ledger)
        write_json(subdir / "boundary_register.json", {"cartridge": code, "boundary_lines": spec["boundary_lines"]})
        write_text(subdir / "ACCEPTANCE_PLAN.md", render_acceptance_plan(code, spec, source_ledger))
        gate = subcartridge_gate(code, subdir, spec, source_ledger)
        gates[gate["gate"]] = gate["status"]
        subcartridge_rows[code] = {
            "name": spec["name"],
            "candidate_strength": spec["candidate_strength"],
            "readiness_status": spec["status"],
            "output_dir": str(subdir),
            "next_gate": spec["next_gate"],
            "source_ledger_status": source_ledger["status"],
            "gate_status": gate["status"],
            "local_context_present": source_ledger["local_context_present"],
            "official_sources_identified_not_landed": source_ledger["official_sources_identified_not_landed"],
        }

    no_mutation = compare_snapshots(before, snapshot(watched_inputs))
    gates[no_mutation["gate"]] = no_mutation["status"]

    harness = {
        "task": TASK_NAME,
        "generated_at": utc_now(),
        "status": "PENDING_HASH",
        "boundary_lines": ROOT_BOUNDARY_LINES,
        "f3_spine": f3_spine,
        "subcartridges": subcartridge_rows,
        "gates": gates,
        "no_mutation": no_mutation,
        "output": str(out),
    }
    write_json(out / "NYC_EXPANSION_POTENTIAL_D1_HARNESS_REPORT.json", harness)
    write_text(out / "README.md", render_root_readme(harness))

    no_overclaim = scan_no_overclaim(out)
    gates[no_overclaim["gate"]] = no_overclaim["status"]
    write_json(out / "NYC_EXPANSION_POTENTIAL_D1_NO_OVERCLAIM_REPORT.json", no_overclaim)

    hashes = write_hashes(out)
    gates[hashes["gate"]] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["no_overclaim"] = no_overclaim
    harness["status"] = "PASS_WITH_EXPANSION_CONTRACTS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_json(out / "NYC_EXPANSION_POTENTIAL_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    harness["hashes"] = hashes
    gates[hashes["gate"]] = hashes["status"]
    harness["gates"] = gates
    harness["status"] = "PASS_WITH_EXPANSION_CONTRACTS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_json(out / "NYC_EXPANSION_POTENTIAL_D1_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NYC expansion potential D1 readiness contracts.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--f3-accepted-dir", default=DEFAULT_F3_ACCEPTED_DIR)
    parser.add_argument("--harvest-dir", default=DEFAULT_HARVEST_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = run_nyc_expansion_potential_d1_gate(
        project_root=args.project_root,
        f3_accepted_dir=args.f3_accepted_dir,
        harvest_dir=args.harvest_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps({"status": result["status"], "gates": result["gates"], "output": result["output"]}, indent=2, sort_keys=True))
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
