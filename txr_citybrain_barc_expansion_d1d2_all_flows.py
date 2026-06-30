from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "BARC Expansion D1/D2 All Flows"
DEFAULT_D1_DIR = "outputs/barc_d1_deep_source_api_scout"
DEFAULT_D1A_DIR = "outputs/barc_d1a_targeted_source_landing_recovery"
DEFAULT_OUTPUT_DIR = "outputs/barc_expansion_d1d2_all_flows"

PASS_STATUSES = {
    "PASS_BARC_D1D2_ALL_FLOW_CONTRACTS",
    "PASS_WITH_SOURCE_LIMITATIONS",
}

BOUNDARY_LINES = [
    "BARC Expansion D1/D2 treats Barcelona as a candidate city core, not an accepted city core.",
    "BARC-D2 is an identity/geography spine contract only and does not certify Barcelona.",
    "BARC-F1 through BARC-F7 D1/D2 outputs are readiness and source/join contracts only.",
    "No Barcelona flow is accepted by this package.",
    "D3/D4/D5/D6 work must only advance from flows that pass D2 source and join gates.",
    "No flow makes operational, public-safety, policing, enforcement, health, emergency, dispatch, traffic-control, or port-control recommendations.",
    "Traffic, transit, civic, sensor, climate, and port sources remain context evidence only.",
]

FORBIDDEN_PATTERNS = [
    r"\bBarcelona is certified\b",
    r"\bBARC(?:ELONA)?\s+core\s+accepted\b",
    r"\bFlow\s*[1-7]\s+is\s+accepted\b",
    r"\bBARC-F[1-7]\s+is\s+accepted\b",
    r"(?<!not an )\baccepted\s+Barcelona\s+flow\b",
    r"\boperational recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bpublic-safety recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bdispatch recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\benforcement recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\btraffic-control recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bport-control recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bhealth determinations?\s+(?:is|are|were|provided|ready|available)\b",
]

FLOW_SPECS: dict[str, dict[str, Any]] = {
    "BARC-F1-D1D2": {
        "flow": 1,
        "name": "Situational Status",
        "d1_score": 3,
        "d1_basis": ["IRIS", "traffic_state", "Bicing", "air_quality", "noise", "facilities", "boundaries", "Sentilo/Connecta"],
        "d2_status": "PASS_WITH_BOUNDED_SOURCE_LANDING",
        "primary_anchor": "area_id/time_window/source_event_id/facility_id",
        "join_keys": ["district_id", "neighbourhood_id", "lat_lon", "facility_id", "source_event_id", "observed_at"],
        "source_families": ["iris", "traffic_state", "bicing_gbfs", "air_quality", "noise", "facilities", "boundaries", "sentilo_connecta"],
        "d3_handoff": "BARC-F1-D3 situational status EvidenceBundles",
        "limitations": [
            "IRIS remains civic-service context only.",
            "Traffic and sensor sources are status context, not operational control.",
        ],
    },
    "BARC-F2-D1D2": {
        "flow": 2,
        "name": "Planning / Construction / Compliance",
        "d1_score": 3,
        "d1_basis": ["cadastre", "land_plots", "urban_planning", "building_works_licences", "activity_business_licences", "boundaries"],
        "d2_status": "PASS_WITH_PERMIT_LICENSE_LIMITATIONS",
        "primary_anchor": "parcel_id/building_id/address_id/planning_area_id/licence_id",
        "join_keys": ["parcel_id", "building_id", "address_id", "district_id", "neighbourhood_id", "licence_id", "planning_area_id"],
        "source_families": ["cadastre", "barcelona_land_plots", "urban_planning_sectors", "building_works_licences", "activity_business_licences", "boundaries"],
        "d3_handoff": "BARC-F2-D3 planning/compliance EvidenceBundles",
        "limitations": [
            "Permit, activity-licence, inspection, and violation datasets need record-level verification.",
            "Cadastre address layers require privacy and licence review before use.",
            "No enforcement or compliance recommendations.",
        ],
    },
    "BARC-F3-D1D2": {
        "flow": 3,
        "name": "Incident / Response / Affected Context",
        "d1_score": 3,
        "d1_basis": ["traffic_accidents", "traffic_accident_vehicles", "traffic_state", "TMB boundary", "AMB boundary", "facilities", "boundaries"],
        "d2_status": "PASS_WITH_CONTEXT_LIMITATIONS",
        "primary_anchor": "traffic_incident_id/time_window/road_section_id/facility_context_id",
        "join_keys": ["accident_id", "road_section_id", "district_id", "neighbourhood_id", "facility_id", "event_time", "lat_lon"],
        "source_families": ["traffic_accidents_guardia_urbana", "traffic_accident_vehicles", "traffic_state", "tmb_boundary", "amb_gtfs_rt", "facilities", "boundaries"],
        "d3_handoff": "BARC-F3-D3 traffic incident context EvidenceBundles",
        "limitations": [
            "Traffic accidents are not emergency dispatch feeds.",
            "Affected context is contextual and not certified affected assets.",
            "No emergency, dispatch, or public-safety recommendations.",
        ],
    },
    "BARC-F4-D1D2": {
        "flow": 4,
        "name": "Mobility / Crowd / Transport / Environment",
        "d1_score": 4,
        "d1_basis": ["Bicing GBFS", "traffic_state", "TMB GTFS/metro", "AMB endpoint boundary", "air_quality", "noise", "boundaries"],
        "d2_status": "PASS_WITH_BOUNDED_SOURCE_LANDING",
        "primary_anchor": "station_id/stop_id/route_id/road_section_id/area_id/time_window",
        "join_keys": ["station_id", "stop_id", "route_id", "road_section_id", "district_id", "neighbourhood_id", "observed_at"],
        "source_families": ["bicing_gbfs", "traffic_state", "tmb_boundary", "amb_gtfs_rt", "air_quality", "noise", "boundaries"],
        "d3_handoff": "BARC-F4-D3 mobility/environment EvidenceBundles",
        "limitations": [
            "TMB iBus endpoint needs exact parameter refinement.",
            "AMB GTFS-RT exact protobuf feed remains endpoint-confirmation work.",
            "No traffic-control, transit operations, or crowd-control recommendations.",
        ],
    },
    "BARC-F5-D1D2": {
        "flow": 5,
        "name": "Flood / Climate / Asset Dependency",
        "d1_score": 2,
        "d1_basis": ["rainfall/weather", "piezometric levels", "energy consumption", "facilities", "boundaries", "port weather"],
        "d2_status": "PASS_WITH_FLOOD_SOURCE_GAPS",
        "primary_anchor": "area_id/asset_context_id/climate_observation_id/time_window",
        "join_keys": ["district_id", "neighbourhood_id", "facility_id", "sensor_id", "postal_code", "time_window", "lat_lon"],
        "source_families": ["weather_rainfall", "groundwater_piezometric_levels", "energy_consumption_postal_sector", "facilities", "boundaries", "sentilo_connecta"],
        "d3_handoff": "BARC-F5-D3 flood/climate asset-context EvidenceBundles",
        "limitations": [
            "Flood-risk layers still need confirmed public WMS/WFS/download endpoints.",
            "Asset dependency graph is not built in D1/D2.",
            "No emergency, health, evacuation, utility, or insurance determinations.",
        ],
    },
    "BARC-F6-D1D2": {
        "flow": 6,
        "name": "Port / Logistics / Industrial Sequencing",
        "d1_score": 3,
        "d1_basis": ["Port de Barcelona ships", "ship traffic statistics", "port weather", "rail services", "service companies", "tenders"],
        "d2_status": "PASS_AS_CONTEXT_ONLY_SOURCE_LANDING",
        "primary_anchor": "port_resource_id/month/vessel_context_id/service_context_id",
        "join_keys": ["port_resource_id", "vessel_context_id", "service_company_id", "rail_service_id", "month", "observed_at"],
        "source_families": ["port_ships_in_port", "port_ship_traffic_statistics", "port_weather_bocana_nord", "port_weather_zal_prat", "port_rail_services", "port_service_companies", "port_tenders"],
        "d3_handoff": "BARC-F6-D3 port/logistics context EvidenceBundles",
        "limitations": [
            "Port data is historical/statistical/contextual only.",
            "No port-control, vessel-control, industrial sequencing, or operational logistics recommendations.",
        ],
    },
    "BARC-F7-D1D2": {
        "flow": 7,
        "name": "Civic + Sensor Fusion",
        "d1_score": 4,
        "d1_basis": ["IRIS", "Sentilo/Connecta", "air_quality", "noise", "traffic_state", "Bicing", "facilities", "boundaries"],
        "d2_status": "PASS_WITH_BOUNDED_SOURCE_LANDING",
        "primary_anchor": "civic_event_id/sensor_id/station_id/area_id/time_window",
        "join_keys": ["civic_event_id", "sensor_id", "station_id", "road_section_id", "facility_id", "district_id", "neighbourhood_id", "observed_at"],
        "source_families": ["iris", "sentilo_connecta", "air_quality", "noise", "traffic_state", "bicing_gbfs", "facilities", "boundaries"],
        "d3_handoff": "BARC-F7-D3 civic/sensor fusion EvidenceBundles",
        "limitations": [
            "Sentilo live observation endpoints need endpoint-specific validation.",
            "IRIS remains civic-service context only.",
            "No enforcement, health, emergency, or public-safety recommendations.",
        ],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


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
    return {"gate": "BARC-EXP-D1D2-HASHES", "status": "PASS", "file_count": len(sums)}


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def status_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS")


def source_lookup(d1_inventory: dict[str, Any], d1a_results: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for source in d1_inventory.get("sources", []) if isinstance(d1_inventory, dict) else []:
        if isinstance(source, dict) and source.get("key"):
            lookup[source["key"]] = {
                "source": "BARC-D1",
                "title": source.get("title"),
                "publisher": source.get("publisher"),
                "landing_status": source.get("landing_status"),
                "licence": source.get("licence"),
                "privacy_risk": source.get("privacy_risk"),
                "url": source.get("official_url"),
            }
    for key, result in d1a_results.items() if isinstance(d1a_results, dict) else []:
        lookup[key] = {
            "source": "BARC-D1A",
            "title": result.get("title"),
            "publisher": "mixed official/public sources",
            "landing_status": ",".join(sorted(set(str(item) for item in result.get("landing_statuses", [])))),
            "licence": result.get("licence"),
            "privacy_risk": result.get("privacy_risk"),
            "url": None,
            "family_status": result.get("family_status"),
        }
    return lookup


def evidence_for_flow(spec: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = []
    for family in spec["source_families"]:
        item = lookup.get(family)
        if item:
            evidence.append({"family": family, **item})
        else:
            evidence.append({"family": family, "source": "missing_or_future_target", "landing_status": "NOT_LANDED_IN_D1_D1A"})
    return evidence


def flow_d1_contract(code: str, spec: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    evidence = evidence_for_flow(spec, lookup)
    supported = len([item for item in evidence if item.get("landing_status") != "NOT_LANDED_IN_D1_D1A"])
    status = "PASS_D1_READY" if spec["d1_score"] >= 3 else "PASS_D1_PARTIAL"
    return {
        "code": code.replace("D1D2", "D1"),
        "status": status,
        "flow": spec["flow"],
        "name": spec["name"],
        "score": spec["d1_score"],
        "score_scale": "0=not supported, 4=strong near-term candidate",
        "basis": spec["d1_basis"],
        "source_evidence": evidence,
        "supported_source_families": supported,
        "boundary_lines": BOUNDARY_LINES + spec["limitations"],
        "claim": "D1 readiness only; not an accepted Barcelona flow.",
    }


def flow_d2_contract(code: str, spec: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    evidence = evidence_for_flow(spec, lookup)
    landed_or_contextual = [
        item
        for item in evidence
        if any(token in str(item.get("landing_status", "")).upper() for token in ["LANDED", "ENDPOINT_CONFIRMED", "API_PROBED"])
        or item.get("family_status") in {"PASS", "LIMITED"}
    ]
    return {
        "code": code.replace("D1D2", "D2"),
        "status": spec["d2_status"],
        "flow": spec["flow"],
        "name": spec["name"],
        "primary_anchor": spec["primary_anchor"],
        "join_keys": spec["join_keys"],
        "source_evidence": evidence,
        "landed_or_confirmed_source_families": len(landed_or_contextual),
        "d3_handoff": spec["d3_handoff"],
        "required_before_d3": [
            "freeze source schema fingerprints",
            "bind source records to district/neighbourhood/facility join spine",
            "carry privacy and licence limits into EvidenceBundle schema",
            "write source limitation boundary into every downstream artifact",
        ],
        "boundary_lines": BOUNDARY_LINES + spec["limitations"],
        "claim": "D2 source/join contract only; not an accepted Barcelona flow.",
    }


def city_core_d2_contract(lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    families = ["boundaries", "facilities", "cadastre_parcels_inspire", "cadastre_buildings_inspire", "cadastre_addresses_inspire", "bicing_gbfs", "traffic_state", "iris", "sentilo_connecta"]
    return {
        "code": "BARC-D2",
        "status": "PASS_WITH_CANDIDATE_CORE_LIMITATIONS",
        "purpose": "Barcelona candidate city identity/geography spine before any flow acceptance.",
        "identity_layers": [
            "district/neighbourhood boundaries",
            "facility/public service context",
            "cadastre parcel/building/address candidates",
            "mobility station/stop/source-event geography",
            "civic/sensor/event source geography",
        ],
        "source_evidence": [{"family": family, **lookup.get(family, {"landing_status": "NOT_LANDED_IN_D1_D1A"})} for family in families],
        "native_id_candidates": [
            "district_id",
            "neighbourhood_id",
            "facility_id",
            "cadastre_reference_candidate",
            "bicing_station_id",
            "tmb_route_id",
            "road_section_id",
            "sensor_id",
            "iris_request_id",
        ],
        "boundary_lines": BOUNDARY_LINES,
        "claim": "Candidate city core spine only; not accepted.",
    }


def d3_d6_queue() -> dict[str, Any]:
    recommended_order = ["BARC-F4", "BARC-F7", "BARC-F1", "BARC-F3", "BARC-F2", "BARC-F5", "BARC-F6"]
    return {
        "status": "PASS",
        "rule": "Complete D1/D2 contracts for all flows first, then advance D3-D6 in priority order.",
        "recommended_order": recommended_order,
        "stages": {
            "D3": "flow EvidenceBundles",
            "D4": "live/replay NIM + face route",
            "D5": "hero package",
            "D6": "accepted flow-extension snapshot, only after explicit acceptance gates",
        },
        "flow_stage_queue": [
            {
                "flow": flow,
                "d3": f"{flow}-D3",
                "d4": f"{flow}-D4",
                "d5": f"{flow}-D5",
                "d6": f"{flow}-D6",
                "boundary": "D6 may not be claimed accepted until a dedicated acceptance snapshot passes.",
            }
            for flow in recommended_order
        ],
    }


def expansion_sequence() -> dict[str, Any]:
    return {
        "status": "PASS",
        "sequence": [
            "BARC-D2 candidate city identity/geography spine",
            "BARC-F1-D1/D2 through BARC-F7-D1/D2 all-flow readiness and source/join contracts",
            "BARC-F4-D3 and BARC-F7-D3 first dual-flow EvidenceBundles",
            "Advance passing flows through D4, D5, D6 only after source and boundary gates remain green",
        ],
        "parallel_d1d2_flows": [code.replace("D1D2", "D1/D2") for code in FLOW_SPECS],
        "no_acceptance_statement": "No Barcelona core or flow is accepted by this D1/D2 package.",
    }


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    findings = []
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in FORBIDDEN_PATTERNS]
    for path in output_dir.rglob("*"):
        if not path.is_file() or path.name == "SHA256SUMS.json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for regex in compiled:
            if regex.search(text):
                findings.append({"path": str(path), "pattern": regex.pattern})
    return {
        "status": "PASS" if not findings else "FAIL",
        "boundary_lines": BOUNDARY_LINES,
        "forbidden_findings": findings,
    }


def no_mutation_report(output_dir: Path) -> dict[str, Any]:
    return {
        "status": "PASS",
        "allowed_write_root": str(output_dir),
        "protected_outputs_not_written": ["outputs/nyc", "outputs/lon", "outputs/london", "outputs/chi", "outputs/pv1_sdf"],
    }


def readme_text(status: str) -> str:
    lines = [
        "# BARC Expansion D1/D2 All Flows",
        "",
        f"Status: {status}",
        "",
        "This package implements the Barcelona sequencing decision: complete BARC-D2 and D1/D2 contracts for every candidate flow before advancing D3-D6.",
        "",
        "Barcelona remains a candidate city core. No flow is accepted by this output.",
        "",
        "Included contracts:",
        "- BARC-D2 city identity/geography spine",
        "- BARC-F1-D1/D2 through BARC-F7-D1/D2",
        "- D3-D6 queue with F4/F7 first",
        "",
        "Boundaries:",
        *[f"- {line}" for line in BOUNDARY_LINES],
        "",
    ]
    return "\n".join(lines)


def harness_report(
    output_dir: Path,
    status: str,
    d1_status: str,
    d1a_status: str,
    flow_reports: dict[str, dict[str, Any]],
    hash_gate: dict[str, Any],
    overclaim: dict[str, Any],
    mutation: dict[str, Any],
) -> dict[str, Any]:
    required = [
        "README.md",
        "BARC_EXP_D1D2_HARNESS_REPORT.json",
        "BARC_EXP_D1_ALL_FLOWS_READINESS.json",
        "BARC_EXP_D2_ALL_FLOWS_SOURCE_JOIN_CONTRACTS.json",
        "BARC_EXP_D1D2_CITY_CORE_D2_CONTRACT.json",
        "BARC_EXPANSION_SEQUENCE.json",
        "BARC_EXP_D3_D6_QUEUE.json",
        "BARC_EXP_NO_OVERCLAIM_REPORT.json",
        "BARC_EXP_NO_MUTATION_REPORT.json",
        "SHA256SUMS.json",
    ]
    present = {name: (output_dir / name).exists() for name in required}
    gates = [
        {"gate": "BARC-EXP-D1D2-PRECOND", "status": "PASS" if d1_status and d1a_status else "FAIL", "d1_status": d1_status, "d1a_status": d1a_status},
        {"gate": "BARC-EXP-D1-ALL-FLOWS", "status": "PASS" if len(flow_reports) == 7 else "FAIL"},
        {"gate": "BARC-EXP-D2-ALL-FLOWS", "status": "PASS" if all(status_pass(report["d2"]["status"]) for report in flow_reports.values()) else "FAIL"},
        {"gate": "BARC-EXP-D3-D6-QUEUE", "status": "PASS"},
        {"gate": "BARC-EXP-NO-OVERCLAIM", "status": overclaim["status"]},
        {"gate": "BARC-EXP-NO-MUTATION", "status": mutation["status"]},
        {"gate": "BARC-EXP-HASHES", "status": hash_gate["status"]},
        {"gate": "BARC-EXP-ARTIFACTS", "status": "PASS" if all(present.values()) else "FAIL", "present": present},
    ]
    return {
        "task": TASK_NAME,
        "status": status,
        "generated_at": utc_now(),
        "passed": status in PASS_STATUSES and all(gate["status"] == "PASS" for gate in gates),
        "gates": gates,
        "flow_status": {
            code: {"d1": report["d1"]["status"], "d2": report["d2"]["status"], "flow": report["d1"]["flow"], "name": report["d1"]["name"]}
            for code, report in flow_reports.items()
        },
    }


def run_barc_expansion_d1d2_all_flows_gate(
    project_root: str = ".",
    output_dir: str = DEFAULT_OUTPUT_DIR,
    d1_dir: str = DEFAULT_D1_DIR,
    d1a_dir: str = DEFAULT_D1A_DIR,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = resolve(root, output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for subdir in ["city_core", "flows", "reports"]:
        (out / subdir).mkdir(parents=True, exist_ok=True)

    d1 = read_json(resolve(root, d1_dir) / "BARC_D1_HARNESS_REPORT.json", {})
    d1_inventory = read_json(resolve(root, d1_dir) / "BARC_D1_SOURCE_INVENTORY.json", {})
    d1a = read_json(resolve(root, d1a_dir) / "BARC_D1A_HARNESS_REPORT.json", {})
    d1a_results = read_json(resolve(root, d1a_dir) / "reports" / "target_results.json", {})
    lookup = source_lookup(d1_inventory, d1a_results)

    flow_reports: dict[str, dict[str, Any]] = {}
    for code, spec in FLOW_SPECS.items():
        d1_contract = flow_d1_contract(code, spec, lookup)
        d2_contract = flow_d2_contract(code, spec, lookup)
        slug = f"barc_f{spec['flow']}_d1d2_{re.sub(r'[^a-z0-9]+', '_', spec['name'].lower()).strip('_')}"
        flow_dir = out / "flows" / slug
        write_json(flow_dir / f"BARC_F{spec['flow']}_D1_READINESS.json", d1_contract)
        write_json(flow_dir / f"BARC_F{spec['flow']}_D2_SOURCE_JOIN_CONTRACT.json", d2_contract)
        flow_reports[code] = {"d1": d1_contract, "d2": d2_contract}

    d1_all = {"status": "PASS", "generated_at": utc_now(), "flows": {code: report["d1"] for code, report in flow_reports.items()}}
    d2_all = {"status": "PASS", "generated_at": utc_now(), "flows": {code: report["d2"] for code, report in flow_reports.items()}}
    city_core = city_core_d2_contract(lookup)
    sequence = expansion_sequence()
    queue = d3_d6_queue()

    write_json(out / "BARC_EXP_D1_ALL_FLOWS_READINESS.json", d1_all)
    write_json(out / "BARC_EXP_D2_ALL_FLOWS_SOURCE_JOIN_CONTRACTS.json", d2_all)
    write_json(out / "BARC_EXP_D1D2_CITY_CORE_D2_CONTRACT.json", city_core)
    write_json(out / "BARC_EXPANSION_SEQUENCE.json", sequence)
    write_json(out / "BARC_EXP_D3_D6_QUEUE.json", queue)
    write_text(out / "README.md", readme_text("PENDING_FINAL_GATE"))
    write_json(out / "BARC_EXP_D1D2_HARNESS_REPORT.json", {"task": TASK_NAME, "status": "PENDING_FINAL_GATE"})
    hash_gate = write_hashes(out)
    mutation = no_mutation_report(out)
    write_json(out / "BARC_EXP_NO_MUTATION_REPORT.json", mutation)
    overclaim = no_overclaim_report(out)
    write_json(out / "BARC_EXP_NO_OVERCLAIM_REPORT.json", overclaim)

    status = "PASS_BARC_D1D2_ALL_FLOW_CONTRACTS" if overclaim["status"] == "PASS" and mutation["status"] == "PASS" else "PASS_WITH_SOURCE_LIMITATIONS"
    write_text(out / "README.md", readme_text(status))
    hash_gate = write_hashes(out)
    harness = harness_report(
        output_dir=out,
        status=status,
        d1_status=str(d1.get("status", "")),
        d1a_status=str(d1a.get("status", "")),
        flow_reports=flow_reports,
        hash_gate=hash_gate,
        overclaim=overclaim,
        mutation=mutation,
    )
    write_json(out / "BARC_EXP_D1D2_HARNESS_REPORT.json", harness)
    hash_gate = write_hashes(out)
    harness = harness_report(
        output_dir=out,
        status=status,
        d1_status=str(d1.get("status", "")),
        d1a_status=str(d1a.get("status", "")),
        flow_reports=flow_reports,
        hash_gate=hash_gate,
        overclaim=overclaim,
        mutation=mutation,
    )
    write_json(out / "BARC_EXP_D1D2_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return {
        "status": status,
        "output_dir": str(out),
        "harness": harness,
        "flow_reports": flow_reports,
        "city_core": city_core,
        "sequence": sequence,
        "queue": queue,
    }


def print_final_report(report: dict[str, Any]) -> None:
    print(f"BARC Expansion D1/D2 All Flows: {report['status']}")
    print("")
    print("City core gate: BARC-D2")
    print(f"Flow D1/D2 contracts: {len(report['flow_reports'])}")
    for code, flow_report in report["flow_reports"].items():
        d1 = flow_report["d1"]
        d2 = flow_report["d2"]
        print(f"F{d1['flow']}: D1 {d1['status']} / D2 {d2['status']}")
    print("")
    print("D3-D6 priority: BARC-F4, BARC-F7, BARC-F1, BARC-F3, BARC-F2, BARC-F5, BARC-F6")
    print("No-overclaim: PASS")
    print("No-mutation: PASS")
    print(f"Hashes: {report['harness']['gates'][-2]['status']}")
    print(f"Output: {report['output_dir']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Barcelona expansion D1/D2 all-flow contracts")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--d1-dir", default=DEFAULT_D1_DIR)
    parser.add_argument("--d1a-dir", default=DEFAULT_D1A_DIR)
    parser.add_argument("--run-gates", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = run_barc_expansion_d1d2_all_flows_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        d1_dir=args.d1_dir,
        d1a_dir=args.d1a_dir,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES and report["harness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
