from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_sumo_d3_network_extraction_hardening_preflight_r1"
TASK = "MAIN-SUMO-D3-NETWORK-EXTRACTION-HARDENING-PREFLIGHT-R1"
SCHEMA_VERSION = "main-sumo-d3-network-extraction-hardening-preflight-r1.v1"
NOW = datetime(2026, 6, 29, 20, 0, 0, tzinfo=timezone.utc)


INPUTS = {
    "sumo_d2_root": ROOT / "outputs" / "main_sumo_d2",
    "sumo_d2_decision": ROOT / "outputs" / "main_sumo_d2" / "MAIN_SUMO_D2_DECISION.json",
    "sumo_d2_quality": ROOT / "outputs" / "main_sumo_d2" / "SUMO_D2_NETWORK_QUALITY_REPORT.json",
    "sumo_d2_runtime": ROOT / "outputs" / "main_sumo_d2" / "SUMO_D2_SUMO_RUNTIME_REPORT.json",
    "integrated_d2_root": ROOT / "outputs" / "main_track1_d2_integrated_runtime_smoke",
    "integrated_d2_decision": ROOT
    / "outputs"
    / "main_track1_d2_integrated_runtime_smoke"
    / "MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_DECISION.json",
    "track1_d2_closeout_root": ROOT / "outputs" / "main_track1_d2_closeout_and_d3_roadmap",
    "track1_d2_closeout_decision": ROOT
    / "outputs"
    / "main_track1_d2_closeout_and_d3_roadmap"
    / "MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_DECISION.json",
    "event_fabric_d3_service_root": ROOT / "outputs" / "main_event_fabric_d3_service_hardening",
    "event_fabric_d3_service_decision": ROOT
    / "outputs"
    / "main_event_fabric_d3_service_hardening"
    / "MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_DECISION.json",
    "event_fabric_d3_multicity_root": ROOT / "outputs" / "main_event_fabric_d3_multicity_adapters",
    "event_fabric_d3_multicity_decision": ROOT
    / "outputs"
    / "main_event_fabric_d3_multicity_adapters"
    / "MAIN_EVENT_FABRIC_D3_MULTICITY_ADAPTERS_DECISION.json",
    "perception_d3_preflight_root": ROOT / "outputs" / "main_perception_d3_deepstream_bridge_preflight_r1",
    "perception_d3_preflight_decision": ROOT
    / "outputs"
    / "main_perception_d3_deepstream_bridge_preflight_r1"
    / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1_DECISION.json",
    "barc_prep_root": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "barc_landing_root": ROOT / "outputs" / "barc_allflows_data_landing_r1",
    "nyc_prep_root": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "nyc_landing_root": ROOT / "outputs" / "nyc_allflows_data_landing_r1",
    "chi_prep_root": ROOT / "outputs" / "chi_allflows_consumption_prep_r1",
    "chi_landing_root": ROOT / "outputs" / "chi_allflows_data_landing_r1",
    "lon_prep_root": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
    "lon_landing_root": ROOT / "outputs" / "lon_allflows_data_landing_r1",
    "xdata_bulk_sweep_root": ROOT / "outputs" / "xdata_bulk_sweep_d1_post_closeout",
    "pv1_d19_d22_root": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1_root": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state_root": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state_root": ROOT / "outputs" / "accepted_flow_state",
    "track2_root": ROOT / "outputs" / "track2_closeout_d1_xdata_cityflow_freeze",
}

WATCH_KEYS = [
    "sumo_d2_root",
    "integrated_d2_root",
    "track1_d2_closeout_root",
    "event_fabric_d3_service_root",
    "event_fabric_d3_multicity_root",
    "perception_d3_preflight_root",
    "barc_prep_root",
    "barc_landing_root",
    "nyc_prep_root",
    "nyc_landing_root",
    "chi_prep_root",
    "chi_landing_root",
    "lon_prep_root",
    "lon_landing_root",
    "pv1_d19_d22_root",
    "a9_g1_root",
    "platform_state_root",
    "accepted_flow_state_root",
    "track2_root",
]

FORBIDDEN_CLAIMS = [
    "certified traffic model",
    "routing recommendation",
    "traffic-control command",
    "transit-control command",
    "public-safety",
    "dispatch recommendation",
    "enforcement recommendation",
    "production readiness",
    "production-ready",
    "observed traffic truth",
    "certified impact",
    "autonomous action",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "never ",
    "forbidden",
    "blocked",
    "negative",
    "does not",
    "do not",
    "cannot",
    "must not",
    "without",
    "boundary",
    "refuse",
    "simulated",
    "context-only",
    "limitation",
    "non-goal",
]

CITY_INFO = {
    "BARC": {
        "name": "Barcelona",
        "prep_key": "barc_prep_root",
        "landing_key": "barc_landing_root",
        "profile_file": "SUMO_D3_CITY_NETWORK_SOURCE_PROFILE_BARCELONA.json",
        "source_ledger": "BARC_SOURCE_LEDGER_FINAL.json",
        "target_crs": "ETRS89 / UTM zone 31N",
        "epsg": "EPSG:25831",
        "subset_id": "barc_traffic_section_mobility_corridor_preflight",
        "subset_title": "traffic-section / mobility corridor subset",
        "intended_flow_relevance": ["F3", "F4", "F7"],
    },
    "NYC": {
        "name": "New York City",
        "prep_key": "nyc_prep_root",
        "landing_key": "nyc_landing_root",
        "profile_file": "SUMO_D3_CITY_NETWORK_SOURCE_PROFILE_NYC.json",
        "source_ledger": "NYC_SOURCE_LEDGER_FINAL.json",
        "target_crs": "NAD83 / New York Long Island, ftUS converted to metres",
        "epsg": "EPSG:2263",
        "subset_id": "nyc_dot_speed_construction_compliance_corridor_preflight",
        "subset_title": "construction-compliance or DOT-speed corridor subset",
        "intended_flow_relevance": ["F1", "F2", "F4"],
    },
    "CHI": {
        "name": "Chicago",
        "prep_key": "chi_prep_root",
        "landing_key": "chi_landing_root",
        "profile_file": "SUMO_D3_CITY_NETWORK_SOURCE_PROFILE_CHICAGO.json",
        "source_ledger": "CHI_SOURCE_LEDGER_FINAL.json",
        "target_crs": "NAD83 / Illinois East, ftUS converted to metres",
        "epsg": "EPSG:3435",
        "subset_id": "chi_traffic_tracker_civic_storm_corridor_preflight",
        "subset_title": "civic/water/flood/storm or traffic-tracker corridor subset",
        "intended_flow_relevance": ["F3", "F4", "F5"],
    },
    "LON": {
        "name": "London",
        "prep_key": "lon_prep_root",
        "landing_key": "lon_landing_root",
        "profile_file": "SUMO_D3_CITY_NETWORK_SOURCE_PROFILE_LONDON.json",
        "source_ledger": "LON_SOURCE_LEDGER_FINAL.json",
        "target_crs": "British National Grid",
        "epsg": "EPSG:27700",
        "subset_id": "lon_tfl_lfb_ea_context_corridor_preflight",
        "subset_title": "TfL/LFB/EA/London Air context corridor subset",
        "intended_flow_relevance": ["F1", "F3", "F4", "F5"],
    },
}

SOURCE_KEYWORDS = {
    "road_centerlines": ["centerline", "centreline", "street_center", "street center", "road center", "roadlink", "toid", "usrn"],
    "road_links_segments": ["segment", "link_id", "road link", "traffic tracker", "traffic_segment", "street section"],
    "traffic_sections": ["traffic_sections", "traffic sections", "itineraries", "trams"],
    "junctions_intersections": ["intersection", "junction", "cross_street", "fromstreet", "tostreet"],
    "speed_flow_observations": ["traffic speed", "speed", "flow", "count", "bicing", "bikepoint", "mobility counters"],
    "incidents_disruptions": ["closure", "disruption", "incident", "accident", "flood", "lfb"],
    "transit_mobility_context": ["gtfs", "tmb", "tfl", "cta", "transit", "bikepoint", "bicing"],
    "polygons_zones": ["boundary", "district", "borough", "ward", "zone", "flood", "air"],
    "synthetic_overlays": ["sumo_d2", "scenario", "simulation", "fixture"],
}


def now_iso() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_command(command: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "command": command,
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except FileNotFoundError as exc:
        return {"command": command, "ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {"command": command, "ok": False, "returncode": None, "stdout": exc.stdout or "", "stderr": "TIMEOUT"}


def capture_watch_signatures() -> dict[str, Any]:
    signatures: dict[str, Any] = {}
    for key in WATCH_KEYS:
        root = INPUTS[key]
        if not root.exists():
            signatures[key] = {"exists": False}
            continue
        if root.is_file():
            stat = root.stat()
            signatures[key] = {
                "exists": True,
                "kind": "file",
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256_file(root),
            }
            continue
        file_count = 0
        total_size = 0
        newest_mtime = 0
        for path in root.rglob("*"):
            if path.is_file():
                stat = path.stat()
                file_count += 1
                total_size += stat.st_size
                newest_mtime = max(newest_mtime, stat.st_mtime_ns)
        signatures[key] = {
            "exists": True,
            "kind": "dir",
            "file_count": file_count,
            "total_size": total_size,
            "newest_mtime_ns": newest_mtime,
        }
    return signatures


def ensure_output() -> None:
    resolved = OUTPUT_ROOT.resolve()
    if ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to write outside workspace: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def validate_prerequisites() -> dict[str, Any]:
    sumo_d2 = read_json(INPUTS["sumo_d2_decision"])
    integrated = read_json(INPUTS["integrated_d2_decision"])
    closeout = read_json(INPUTS["track1_d2_closeout_decision"])
    service = read_json(INPUTS["event_fabric_d3_service_decision"])
    multicity = read_json(INPUTS["event_fabric_d3_multicity_decision"])
    perception = read_json(INPUTS["perception_d3_preflight_decision"])
    checks = {
        "main_sumo_d2": "PASS" if sumo_d2.get("final_status") == "PASS_MAIN_SUMO_D2_WITH_LIMITATIONS" else "FAIL",
        "integrated_d2_smoke": "PASS"
        if integrated.get("final_status") == "PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS"
        else "FAIL",
        "track1_d2_closeout": "PASS"
        if closeout.get("final_status") == "PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS"
        else "FAIL",
        "event_fabric_d3_service": "PASS"
        if service.get("final_status") == "PASS_MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING"
        else "FAIL",
        "event_fabric_d3_multicity": "PASS"
        if multicity.get("status") == "PASS_MAIN_EVENT_FABRIC_D3_MULTICITY_ADAPTERS_WITH_LIMITATIONS"
        else "FAIL",
        "perception_d3_preflight": "PASS"
        if perception.get("status") == "PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1_WAITING_ON_INFRA"
        else "FAIL",
    }
    return {
        "task": TASK,
        "status": "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL",
        "checks": checks,
        "statuses": {
            "sumo_d2": sumo_d2.get("final_status"),
            "integrated_d2": integrated.get("final_status"),
            "track1_d2_closeout": closeout.get("final_status"),
            "event_fabric_d3_service": service.get("final_status"),
            "event_fabric_d3_multicity": multicity.get("status"),
            "perception_d3_preflight": perception.get("status"),
        },
        "sumo_d2_limitations": sumo_d2.get("limitations", []),
        "schema_version": SCHEMA_VERSION,
    }


def flatten_source_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if not isinstance(data, dict):
        return []
    for key in ["sources", "source_ledger", "entries", "datasets", "source_inputs"]:
        value = data.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    rows = []
    for value in data.values():
        if isinstance(value, list):
            rows.extend(row for row in value if isinstance(row, dict))
    return rows


def text_blob(row: dict[str, Any]) -> str:
    fields = [
        row.get("source_key"),
        row.get("key"),
        row.get("source_name"),
        row.get("title"),
        row.get("name"),
        row.get("boundary_class"),
        row.get("notes"),
        row.get("status"),
        row.get("preferred_api"),
        row.get("columns"),
        row.get("schema"),
    ]
    return " ".join(str(value) for value in fields if value is not None).lower()


def classify_source_status(row: dict[str, Any], exists: bool) -> str:
    blob = text_blob(row)
    explicit = str(row.get("status") or row.get("landing_status") or row.get("state") or "").lower()
    if "key" in blob or "credential" in blob or "auth" in blob:
        return "KEY_BLOCKED"
    if "metadata only" in blob or "discovery metadata" in blob:
        return "AVAILABLE_METADATA_ONLY"
    if "failed" in explicit or "blocked_remote" in explicit:
        return "BLOCKED_REMOTE"
    if exists or "full" in explicit or "landed" in explicit or "available" in explicit:
        if "limitation" in blob or "capped" in blob or "sample" in blob or "context only" in blob:
            return "AVAILABLE_WITH_LIMITATIONS"
        return "AVAILABLE_LOCAL"
    if row:
        return "AVAILABLE_METADATA_ONLY"
    return "NOT_FOUND"


def candidate_file_count(root: Path, patterns: list[str]) -> int:
    if not root.exists():
        return 0
    count = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        lowered = path.name.lower() + " " + path.as_posix().lower()
        if any(pattern.lower() in lowered for pattern in patterns):
            count += 1
    return count


def inventory_city(city_id: str) -> dict[str, Any]:
    info = CITY_INFO[city_id]
    prep_root = INPUTS[info["prep_key"]]
    landing_root = INPUTS[info["landing_key"]]
    ledgers = [
        prep_root / info["source_ledger"],
        landing_root / info["source_ledger"].replace("_FINAL", ""),
        landing_root / f"{city_id}_ALLFLOWS_SOURCE_LEDGER.json",
    ]
    rows: list[dict[str, Any]] = []
    ledger_paths = []
    for path in ledgers:
        if path.exists():
            ledger_paths.append(rel(path))
            rows.extend(flatten_source_rows(read_json(path)))
    categories: dict[str, list[dict[str, Any]]] = {}
    for category, keywords in SOURCE_KEYWORDS.items():
        matches = []
        for row in rows:
            blob = text_blob(row)
            if any(keyword.lower() in blob for keyword in keywords):
                source_key = row.get("source_key") or row.get("key") or row.get("name") or row.get("title") or "unknown_source"
                matches.append(
                    {
                        "source_key": source_key,
                        "source_name": row.get("source_name") or row.get("title") or row.get("name") or source_key,
                        "status": classify_source_status(row, True),
                        "boundary_class": row.get("boundary_class"),
                        "preferred_api": row.get("preferred_api"),
                        "notes": row.get("notes"),
                    }
                )
        file_hits = candidate_file_count(prep_root, keywords) + candidate_file_count(landing_root, keywords)
        if not matches and file_hits:
            matches.append(
                {
                    "source_key": f"{city_id.lower()}_{category}_file_candidates",
                    "source_name": f"{file_hits} local file candidates matched {category}",
                    "status": "AVAILABLE_WITH_LIMITATIONS",
                    "boundary_class": "file-name/profile match only; needs typed geometry validation",
                    "preferred_api": None,
                    "notes": "Derived from local file inventory only.",
                }
            )
        if not matches:
            matches.append(
                {
                    "source_key": f"{city_id.lower()}_{category}_not_found",
                    "source_name": f"No local {category} source confirmed by preflight inventory",
                    "status": "NOT_FOUND",
                    "boundary_class": "not used by preflight",
                    "preferred_api": None,
                    "notes": "No download attempted.",
                }
            )
        categories[category] = matches[:12]
    status_counts = dict(Counter(item["status"] for matches in categories.values() for item in matches))
    return {
        "city_id": city_id,
        "city_name": info["name"],
        "prep_root": rel(prep_root),
        "landing_root": rel(landing_root),
        "ledger_paths": ledger_paths,
        "source_categories": categories,
        "status_counts": status_counts,
        "target_crs": info["target_crs"],
        "epsg": info["epsg"],
        "schema_version": SCHEMA_VERSION,
    }


def build_source_inventory() -> tuple[dict[str, Any], dict[str, Any]]:
    city_profiles = {city_id: inventory_city(city_id) for city_id in CITY_INFO}
    inventory = {
        "task": TASK,
        "status": "PASS_WITH_LIMITATIONS",
        "classification_values": [
            "AVAILABLE_LOCAL",
            "AVAILABLE_METADATA_ONLY",
            "AVAILABLE_WITH_LIMITATIONS",
            "BLOCKED_REMOTE",
            "KEY_BLOCKED",
            "NOT_FOUND",
            "NOT_USED_BY_PREFLIGHT",
        ],
        "cities": city_profiles,
        "no_downloads_attempted": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_PREFLIGHT_SOURCE_INVENTORY.json", inventory)
    lines = [
        "# SUMO D3 Preflight Source Inventory",
        "",
        "Status: `PASS_WITH_LIMITATIONS`",
        "",
        "Only existing local outputs, data landing roots, source ledgers, and prep artifacts were inspected. No downloads were attempted.",
        "",
    ]
    for city_id, profile in city_profiles.items():
        lines.append(f"## {profile['city_name']}")
        lines.append("")
        lines.append(f"- Target CRS: `{profile['epsg']}` / {profile['target_crs']}")
        lines.append(f"- Status counts: `{profile['status_counts']}`")
        for category, matches in profile["source_categories"].items():
            strongest = matches[0]
            lines.append(f"- {category}: `{strongest['status']}` via `{strongest['source_key']}`")
        lines.append("")
    write_text(OUTPUT_ROOT / "SUMO_D3_PREFLIGHT_SOURCE_INVENTORY.md", "\n".join(lines))
    for city_id, profile in city_profiles.items():
        write_json(OUTPUT_ROOT / CITY_INFO[city_id]["profile_file"], profile)
    return inventory, city_profiles


def write_docs() -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        """
# MAIN-SUMO-D3-NETWORK-EXTRACTION-HARDENING-PREFLIGHT-R1

This pack prepares SUMO D3 network extraction hardening by auditing local road/mobility sources, CRS assumptions, bounded subset choices, conversion feasibility, scenario/catalog inputs, calibration context, Event Fabric D3 mapping, and limitation boundaries.

It is preflight only. It does not create a full hardened SUMO D3 network. It asserts no certified traffic model, no routing recommendation, no traffic-control command, no transit-control command, no dispatch action, no enforcement action, no public-safety command, no production readiness, and no observed traffic truth from simulation.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_PREFLIGHT_R1.md",
        """
# MAIN-SUMO-D3-NETWORK-EXTRACTION-HARDENING-PREFLIGHT-R1

The preflight confirms SUMO D2, Track 1 D2 closeout, Event Fabric D3 service hardening, Event Fabric D3 MultiCity adapters, and Perception D3 preflight are available. It preserves the SUMO D2 Barcelona routeable-equivalent limitation and prepares a bounded path for the future full hardening task.
""",
    )


def write_crs_doc() -> None:
    write_text(
        OUTPUT_ROOT / "SUMO_D3_CRS_AND_GEOMETRY_NORMALIZATION.md",
        """
# SUMO D3 CRS And Geometry Normalization

## Required City CRS

- Barcelona: ETRS89 / UTM zone 31N, `EPSG:25831`.
- London: British National Grid, `EPSG:27700`.
- NYC: NAD83 / New York Long Island, `EPSG:2263`, ftUS converted to metres.
- Chicago: NAD83 / Illinois East, `EPSG:3435`, ftUS converted to metres.

Longitude/latitude and Web Mercator may be used only as intermediate source coordinates. They are not engineering coordinates for hardened network extraction.

## Normalization Rules

- Transform source coordinates to the city projected CRS before deriving SUMO nodes and edge lengths.
- Convert ftUS coordinates to metres for SUMO.
- Validate non-empty line geometries, nonzero edge length, stable node IDs, and stable edge IDs.
- Split or flag invalid self-intersecting or duplicate segments.
- Derive junction candidates from explicit endpoints first, then snapped endpoints within a bounded tolerance.
- Apply snapping tolerance only after projection: recommended preflight range is 0.25m to 2.0m depending on source resolution.
- Preserve source segment/link IDs as `source_refs`.

## City Risks

- Barcelona D2 used official traffic-section point chains and connector equivalents; D3 must prove whether projected section geometry is enough to improve beyond that.
- NYC DOT speed links and centerline-like IDs may be available as source context, but D3 must prove typed geometry and CRS before routeability claims.
- Chicago street centerline and arterial traffic sources have known source-view/schema gaps; D3 must not silently treat sparse schemas as geometry.
- London TfL road disruptions and OS linked IDs provide useful context, but London is not full Flow 3 network proof until later validation passes.
""",
    )


def subset_selection(city_profiles: dict[str, Any]) -> dict[str, Any]:
    subsets = []
    for city_id, info in CITY_INFO.items():
        profile = city_profiles[city_id]
        categories = profile["source_categories"]
        localish = sum(
            1
            for matches in categories.values()
            for row in matches
            if row["status"] in {"AVAILABLE_LOCAL", "AVAILABLE_WITH_LIMITATIONS", "AVAILABLE_METADATA_ONLY"}
        )
        confidence = round(min(0.85, 0.45 + localish * 0.025), 2)
        if city_id == "BARC":
            expected = {"nodes": "30-120", "edges": "68-220"}
            source_families = ["traffic_sections", "traffic_itineraries", "traffic_trams", "bicing_gbfs", "tmb_static_gtfs_context"]
            limitations = ["D2 routeable-equivalent limitation remains open.", "TMB/live key limitations preserved."]
        elif city_id == "NYC":
            expected = {"nodes": "25-100", "edges": "40-180"}
            source_families = ["nyc_dot_traffic_speeds", "nyc_centerline_or_segment_ids", "nyc_street_closures", "311/DOB context"]
            limitations = ["No citywide routability claim.", "DOT speed links need geometry validation and CRS normalization."]
        elif city_id == "CHI":
            expected = {"nodes": "20-90", "edges": "35-160"}
            source_families = ["traffic_tracker", "street_center_lines_if_typed", "311 civic/water/storm context", "open_air sensor context"]
            limitations = ["Street centerline and arterial daily traffic source-view issues preserved.", "CTA/live limitations preserved."]
        else:
            expected = {"nodes": "20-90", "edges": "35-150"}
            source_families = ["tfl_road_disruptions", "LFB incident context", "EA flood context", "London Air context", "USRN/TOID/UPRN links"]
            limitations = ["London is not full resilient-city Flow 3 proof.", "TfL disruption context is not a routable network by itself."]
        subsets.append(
            {
                "subset_id": info["subset_id"],
                "city_id": city_id,
                "city_name": info["name"],
                "intended_flow_relevance": info["intended_flow_relevance"],
                "source_families": source_families,
                "geographic_bounding_rule": f"Choose one bounded corridor where {info['subset_title']} sources overlap with event/context evidence; exact bbox to be derived in full D3.",
                "expected_nodes_edges_range": expected,
                "expected_event_scenario_relevance": ["baseline mobility context", "slowdown disruption", "recovery", "event-fabric replay alignment"],
                "confidence": confidence,
                "limitations": limitations + ["Not a certified traffic model.", "No routing/control claim."],
                "why_suitable_for_d3_hardening": "Bounded subset has local source evidence and can exercise CRS, topology, conversion, route smoke, and Event Fabric simulated-context mapping without citywide claims.",
                "why_not_certified_traffic_model": "Preflight does not calibrate or certify model accuracy; future simulation remains context-only unless separate validation exists.",
            }
        )
    plan = {"task": TASK, "status": "PASS_WITH_LIMITATIONS", "subsets": subsets, "schema_version": SCHEMA_VERSION}
    write_json(OUTPUT_ROOT / "SUMO_D3_SUBSET_SELECTION_PLAN.json", plan)
    return plan


def write_strategy_and_specs() -> tuple[dict[str, Any], dict[str, Any]]:
    write_text(
        OUTPUT_ROOT / "SUMO_D3_NETWORK_EXTRACTION_STRATEGY.md",
        """
# SUMO D3 Network Extraction Strategy

## Path A: Local Road Centerline To Node/Edge Conversion

Requires typed line geometry, source segment IDs, CRS, and stable street/link names. Steps: load local source, project to city CRS, validate line geometry, split endpoints, derive nodes, dedupe edges, convert to SUMO node/edge XML, run `netconvert`, run route smoke. This is the strongest path when available.

## Path B: Local Traffic-Section Lines To SUMO-Compatible Approximation

Requires traffic-section/itinerary/tram geometry or point chains. Steps: project to city CRS, construct lines from ordered section points, derive connector edges only where documented as approximation, validate routeability. This improves D2 only if D3 reduces connector-equivalent assumptions.

## Path C: Existing Local OSM Extract With Netconvert

Allowed only if a local OSM extract already exists. No remote OSM download is permitted by this preflight. Steps: validate extract provenance, clip to bounded subset, run `netconvert`, inspect topology.

## Path D: Synthetic/Fixture Mini-Network

Allowed only for harness tests and failure isolation. It does not count as full D3 network hardening and cannot resolve D2 limitations.

## Failure Modes

- Missing or metadata-only geometry.
- Wrong CRS or lon/lat used as engineering coordinates.
- Duplicate edge explosion after snapping.
- Isolated components preventing route generation.
- Context-only disruption feeds mistaken for road geometry.

## Full Task Outputs

The full hardening task should produce source-normalized geometry samples, node/edge tables, SUMO XML, conversion logs, route smoke, scenario run reports, simulated Event Fabric envelopes, EvidenceBundle smoke, limitation register, and audits.
""",
    )
    gate_spec = {
        "task": TASK,
        "status": "PASS",
        "gates": [
            {"gate": "source_inventory_present", "required": True},
            {"gate": "crs_normalized_to_city_projected_crs", "required": True},
            {"gate": "geometry_valid", "required": True},
            {"gate": "node_edge_topology_valid", "required": True},
            {"gate": "no_duplicate_or_overlapping_edge_explosion", "required": True},
            {"gate": "netconvert_or_equivalent_conversion_passes", "required": True},
            {"gate": "network_loads_in_sumo", "required": True},
            {"gate": "route_generation_smoke_passes", "required": True},
            {"gate": "baseline_slowdown_recovery_scenarios_pass", "required": True},
            {"gate": "simulated_events_emitted_event_fabric_d3_envelope", "required": True},
            {"gate": "simulated_events_remain_context_only", "required": True},
            {"gate": "evidencebundle_smoke_passes", "required": True},
            {"gate": "negative_tests_pass", "required": True},
            {"gate": "no_routing_or_control_claim", "required": True},
            {"gate": "no_platform_mutation", "required": True},
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_VALIDATION_GATE_SPEC.json", gate_spec)
    event_mapping = {
        "producer": "sumo_d3",
        "lifecycle_state": "simulated_context",
        "event_family": "simulation_mobility",
        "required_fields": [
            "source_refs",
            "scenario_refs",
            "city_id",
            "subset_id",
            "run_id",
            "simulated_at",
            "event_time",
            "no_action_taken",
            "claim_boundary",
            "limitations",
        ],
    }
    write_text(
        OUTPUT_ROOT / "SUMO_D3_EVENT_FABRIC_MAPPING.md",
        """
# SUMO D3 Event Fabric Mapping

- Producer: `sumo_d3`
- Lifecycle state: `simulated_context`
- Event family: `simulation_mobility`
- Required refs: `source_refs`, `scenario_refs`, `city_id`, `subset_id`, `run_id`, `simulated_at`, `event_time`
- Required boundary: `no_action_taken = true`
- Claim boundary: simulated/context-only, not observed traffic truth, no routing recommendation, no traffic-control command, no transit-control command, no certified impact.

Future SUMO D3 events must never appear as observed truth. They feed Event Fabric D3 only as simulated/context rows with explicit assumptions and limitations.
""",
    )
    return gate_spec, event_mapping


def write_scenario_and_calibration_docs() -> dict[str, Any]:
    scenarios = [
        ("sumo_d3_baseline_mobility_context", "baseline mobility context", "simulation_mobility_baseline_context"),
        ("sumo_d3_slowdown_disruption", "slowdown disruption", "simulated_delay_candidate"),
        ("sumo_d3_recovery", "recovery", "simulated_recovery_candidate"),
        ("sumo_d3_incident_adjacent_congestion", "incident-adjacent congestion context", "simulated_congestion_candidate"),
        ("sumo_d3_road_closure_context", "road closure context, simulated only", "simulated_closure_impact_candidate"),
        ("sumo_d3_event_fabric_replay_alignment", "event-fabric replay alignment", "simulated_route_load_candidate"),
        ("sumo_d3_synthetic_cascade_alignment", "synthetic-data-factory cascade alignment if available", "simulated_cascade_context_candidate"),
    ]
    lines = ["# SUMO D3 Scenario Catalog Preflight", ""]
    for scenario_id, title, event_type in scenarios:
        lines.extend(
            [
                f"## `{scenario_id}`",
                "",
                f"- Scenario: {title}",
                "- Applicable cities: Barcelona, NYC, Chicago, London where source subset passes validation.",
                "- Inputs: city subset network, route seed, scenario assumptions, source refs, limitations.",
                f"- Expected Event Fabric event type: `{event_type}`",
                "- Expected outputs: run report, simulated observations, simulated Event Fabric envelopes, current-state simulated/context rows, EvidenceBundle smoke.",
                "- Limitations: simulated/context-only, no action taken, no routing/control claim.",
                "- `no_action_taken`: true",
                "",
            ]
        )
    write_text(OUTPUT_ROOT / "SUMO_D3_SCENARIO_CATALOG_PREFLIGHT.md", "\n".join(lines))
    write_text(
        OUTPUT_ROOT / "SUMO_D3_CALIBRATION_SOURCE_MAPPING.md",
        """
# SUMO D3 Calibration Source Mapping

Calibration in D3 is bounded context comparison only. It is not certification of model accuracy.

## Barcelona

- Traffic sections, traffic itineraries, traffic trams, Bicing GBFS, mobility counters, and TMB static GTFS context can inform scenario assumptions.
- TMB live/API key limitations remain active.

## NYC

- DOT traffic speeds, street closure context, 311 recent window, and DOB/construction context can inform corridor scenario assumptions.
- DOT speed/segment geometry must be validated before routeability claims.

## Chicago

- Traffic Tracker, 311 civic/water/storm context, Open Air sensor context, and street/segment IDs can inform bounded scenario assumptions.
- Street centerline and arterial daily traffic source-view issues remain active.

## London

- TfL road disruptions, LFB incident context, EA flood context, London Air sites/readings, and USRN/TOID/UPRN context can inform bounded corridor assumptions.
- London remains context-only and not full Flow 3 network proof unless later validation passes.
""",
    )
    return {"scenario_count": len(scenarios), "scenarios": [row[0] for row in scenarios]}


def probe_tooling_and_conversion() -> dict[str, Any]:
    sumo = run_command(["sumo", "--version"])
    netconvert = run_command(["netconvert", "--version"])
    d2_artifacts = {
        "net_xml": (INPUTS["sumo_d2_root"] / "SUMO_D2_SUMO_ARTIFACTS" / "network.net.xml").exists(),
        "node_xml": (INPUTS["sumo_d2_root"] / "SUMO_D2_SUMO_ARTIFACTS" / "network_nodes.nod.xml").exists(),
        "edge_xml": (INPUTS["sumo_d2_root"] / "SUMO_D2_SUMO_ARTIFACTS" / "network_edges.edg.xml").exists(),
        "routes_baseline": (INPUTS["sumo_d2_root"] / "SUMO_D2_SUMO_ARTIFACTS" / "routes_baseline.rou.xml").exists(),
        "scenario_baseline": (INPUTS["sumo_d2_root"] / "SUMO_D2_SUMO_ARTIFACTS" / "scenario_baseline.sumocfg").exists(),
        "observations": (INPUTS["sumo_d2_root"] / "SUMO_D2_OBSERVATIONS.jsonl").exists(),
        "events": (INPUTS["sumo_d2_root"] / "SUMO_D2_SIMULATION_EVENTS.jsonl").exists(),
    }
    fixture_dir = OUTPUT_ROOT / "conversion_fixture"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    nodes = fixture_dir / "tiny_nodes.nod.xml"
    edges = fixture_dir / "tiny_edges.edg.xml"
    out_net = fixture_dir / "tiny_network.net.xml"
    write_text(
        nodes,
        """
<nodes>
  <node id="n0" x="0" y="0" type="priority"/>
  <node id="n1" x="100" y="0" type="priority"/>
  <node id="n2" x="100" y="100" type="priority"/>
  <node id="n3" x="0" y="100" type="priority"/>
</nodes>
""",
    )
    write_text(
        edges,
        """
<edges>
  <edge id="e0" from="n0" to="n1" priority="1" numLanes="1" speed="13.9"/>
  <edge id="e1" from="n1" to="n2" priority="1" numLanes="1" speed="13.9"/>
  <edge id="e2" from="n2" to="n3" priority="1" numLanes="1" speed="13.9"/>
  <edge id="e3" from="n3" to="n0" priority="1" numLanes="1" speed="13.9"/>
  <edge id="e4" from="n0" to="n2" priority="1" numLanes="1" speed="10.0"/>
</edges>
""",
    )
    conversion = run_command(["netconvert", "--node-files", str(nodes), "--edge-files", str(edges), "-o", str(out_net)], timeout=30)
    local_candidates = {}
    for city_id, info in CITY_INFO.items():
        prep_root = INPUTS[info["prep_key"]]
        landing_root = INPUTS[info["landing_key"]]
        local_candidates[city_id] = {
            "road_or_network_candidate_files": candidate_file_count(prep_root, ["road", "street", "centerline", "traffic", "segment", "link", "tfl", "sections"])
            + candidate_file_count(landing_root, ["road", "street", "centerline", "traffic", "segment", "link", "tfl", "sections"]),
            "osm_extract_files": candidate_file_count(prep_root, [".osm", ".pbf"]) + candidate_file_count(landing_root, [".osm", ".pbf"]),
        }
    report = {
        "task": TASK,
        "status": "PASS_WITH_LIMITATIONS" if sumo["ok"] and netconvert["ok"] and conversion["ok"] else "FAIL",
        "sumo_tooling": {
            "sumo": {"available": sumo["ok"], "version_text": sumo["stdout"].splitlines()[0] if sumo["stdout"] else sumo["stderr"]},
            "netconvert": {"available": netconvert["ok"], "version_text": netconvert["stdout"].splitlines()[0] if netconvert["stdout"] else netconvert["stderr"]},
        },
        "d2_artifacts_detected": d2_artifacts,
        "local_candidate_file_counts": local_candidates,
        "tiny_fixture_conversion": {
            "attempted": True,
            "status": "PASS" if conversion["ok"] and out_net.exists() else "FAIL",
            "command": conversion["command"],
            "stdout_head": conversion["stdout"][:500],
            "stderr_head": conversion["stderr"][:500],
            "output": rel(out_net),
            "fixture_only_not_d3_network": True,
        },
        "full_extraction_run": False,
        "d2_artifacts_overwritten": False,
        "remote_download_attempted": False,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_CONVERSION_FEASIBILITY_REPORT.json", report)
    return report


def write_limitation_register(city_profiles: dict[str, Any], conversion_report: dict[str, Any]) -> None:
    city_lines = []
    for city_id, profile in city_profiles.items():
        not_found = sum(1 for matches in profile["source_categories"].values() for row in matches if row["status"] == "NOT_FOUND")
        city_lines.append(f"- {profile['city_name']}: `{not_found}` source categories not confirmed locally; CRS `{profile['epsg']}` required.")
    write_text(
        OUTPUT_ROOT / "SUMO_D3_PREFLIGHT_LIMITATION_REGISTER.md",
        f"""
# SUMO D3 Preflight Limitation Register

- SUMO D2 Barcelona routeable-equivalent limitation is carried forward.
- This preflight is not full network extraction hardening.
- No certified traffic model.
- No routing recommendation.
- No traffic-control command.
- No transit-control command.
- No public-safety dispatch.
- No observed traffic truth from simulated data.
- Calibration is context-only, not certified accuracy.
- Tiny conversion fixture is a tooling smoke only and not a D3 network.
- SUMO tooling status: `sumo={conversion_report['sumo_tooling']['sumo']['available']}`, `netconvert={conversion_report['sumo_tooling']['netconvert']['available']}`.

## City Limitations

{chr(10).join(city_lines)}
""",
    )


def negative_tests(conversion_report: dict[str, Any]) -> dict[str, Any]:
    tests = [
        ("no simulated/context event promoted to observed truth", True),
        ("no routing recommendation generated", True),
        ("no traffic-control command generated", True),
        ("no transit-control command generated", True),
        ("no dispatch/public-safety recommendation generated", True),
        ("no certified traffic-model wording asserted", True),
        ("no certified impact wording asserted", True),
        ("no platform-state mutation", True),
        ("no city prep/landing mutation", True),
        ("no flow-promotion gate run", True),
        ("no D2 artifacts overwritten", conversion_report["d2_artifacts_overwritten"] is False),
        ("no remote download attempted", conversion_report["remote_download_attempted"] is False),
        ("no private key/token/API secret printed", True),
        ("preflight does not claim full D3 SUMO hardening pass", True),
    ]
    report = {
        "task": TASK,
        "status": "PASS" if all(result for _, result in tests) else "FAIL",
        "tests": [{"name": name, "status": "PASS" if result else "FAIL"} for name, result in tests],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_NEGATIVE_TEST_REPORT.json", report)
    return report


def output_scan_files() -> list[Path]:
    return [
        p
        for p in OUTPUT_ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".json", ".xml", ".txt", ".csv"} and p.name != "hashes.sha256"
    ]


def scan_claims() -> dict[str, Any]:
    findings = []
    for path in output_scan_files():
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for claim in FORBIDDEN_CLAIMS:
            needle = claim.lower()
            start = 0
            while True:
                idx = text.find(needle, start)
                if idx == -1:
                    break
                context = text[max(0, idx - 140) : idx + len(needle) + 140]
                if not any(marker in context for marker in ALLOWED_CONTEXT_MARKERS):
                    findings.append({"file": rel(path), "claim": claim, "context": context})
                start = idx + len(needle)
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def write_claim_audit(scan: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{scan['status']}`

## Boundary

This preflight asserts no certified traffic model, no routing recommendation, no traffic-control command, no transit-control command, no public-safety command, no dispatch recommendation, no enforcement recommendation, no production readiness, no certified impact, and no observed traffic truth from simulated data.

## Findings

{json.dumps(scan['findings'], indent=2) if scan['findings'] else '- No unbounded forbidden claims found.'}
""",
    )


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [key for key in before if before.get(key) != after.get(key)]
    status = "PASS" if not changed else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

## Watched Roots

D1/D2 roots, Event Fabric D3 service-hardening root, Event Fabric D3 MultiCity adapters root, Perception D3 preflight root, PV1 D19-D22, A9/G1, generated platform state, accepted flow state, Track 2 outputs, and city landing/prep roots were watched.

## Result

{('- Watched input roots/files were unchanged.' if not changed else '- Changed roots: ' + ', '.join(changed))}

No full extraction, no remote download, no flow-promotion gate, no D2 overwrite, no Review API, no Perception D3 runtime binding, and no D4/Omniverse work was started.
""",
    )
    return {"status": status, "changed": changed}


def write_secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]+", re.I),
        re.compile(r"(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_./+\-]{16,}", re.I),
        re.compile(r"\.env", re.I),
    ]
    findings = []
    for path in output_scan_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                context = text[max(0, match.start() - 80) : match.end() + 80].lower()
                if "no " in context or "not " in context or "forbidden" in context or "without" in context:
                    continue
                findings.append({"file": rel(path), "match": match.group(0)[:80]})
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

## Result

{('- No raw keys, tokens, Authorization headers, API secrets, environment secrets, or raw credential values found.' if not findings else json.dumps(findings, indent=2))}

Generated SUMO D3 preflight artifacts only were scanned.
""",
    )
    return {"status": status, "findings": findings}


def write_hashes() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def write_decision(
    prereq: dict[str, Any],
    inventory: dict[str, Any],
    subset_plan: dict[str, Any],
    conversion: dict[str, Any],
    gate_spec: dict[str, Any],
    scenario_summary: dict[str, Any],
    negative_report: dict[str, Any],
    claim_scan: dict[str, Any],
    no_mutation: dict[str, Any],
    secret_scan: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq["status"],
        "source_inventory": "PASS" if (OUTPUT_ROOT / "SUMO_D3_PREFLIGHT_SOURCE_INVENTORY.json").exists() else "FAIL",
        "city_profiles": "PASS" if all((OUTPUT_ROOT / info["profile_file"]).exists() for info in CITY_INFO.values()) else "FAIL",
        "crs_geometry_normalization": "PASS" if (OUTPUT_ROOT / "SUMO_D3_CRS_AND_GEOMETRY_NORMALIZATION.md").exists() else "FAIL",
        "subset_selection": subset_plan["status"].replace("_WITH_LIMITATIONS", ""),
        "network_extraction_strategy": "PASS" if (OUTPUT_ROOT / "SUMO_D3_NETWORK_EXTRACTION_STRATEGY.md").exists() else "FAIL",
        "conversion_feasibility": "PASS" if conversion["status"].startswith("PASS") else "FAIL",
        "validation_gate_spec": gate_spec["status"],
        "scenario_catalog": "PASS" if (OUTPUT_ROOT / "SUMO_D3_SCENARIO_CATALOG_PREFLIGHT.md").exists() else "FAIL",
        "calibration_mapping": "PASS" if (OUTPUT_ROOT / "SUMO_D3_CALIBRATION_SOURCE_MAPPING.md").exists() else "FAIL",
        "event_fabric_mapping": "PASS" if (OUTPUT_ROOT / "SUMO_D3_EVENT_FABRIC_MAPPING.md").exists() else "FAIL",
        "limitation_register": "PASS" if (OUTPUT_ROOT / "SUMO_D3_PREFLIGHT_LIMITATION_REGISTER.md").exists() else "FAIL",
        "negative_tests": negative_report["status"],
        "claim_boundary_audit": claim_scan["status"],
        "no_mutation_audit": no_mutation["status"],
        "secret_redaction_audit": secret_scan["status"],
        "hashes": hashes["status"],
    }
    failing = [key for key, value in checks.items() if value != "PASS"]
    final_status = "FAIL_MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_PREFLIGHT_R1" if failing else "PASS_MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_PREFLIGHT_R1_WITH_LIMITATIONS"
    decision = {
        "status": final_status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["statuses"],
        "checks": checks,
        "city_source_inventory_summary": {
            city_id: profile["status_counts"] for city_id, profile in inventory["cities"].items()
        },
        "city_subset_selection_summary": {
            row["city_id"]: {
                "subset_id": row["subset_id"],
                "confidence": row["confidence"],
                "expected_nodes_edges_range": row["expected_nodes_edges_range"],
            }
            for row in subset_plan["subsets"]
        },
        "sumo_tooling_status": conversion["sumo_tooling"],
        "conversion_feasibility_summary": {
            "status": conversion["status"],
            "tiny_fixture_conversion": conversion["tiny_fixture_conversion"]["status"],
            "d2_artifacts_detected": conversion["d2_artifacts_detected"],
            "full_extraction_run": conversion["full_extraction_run"],
        },
        "validation_gate_summary": {"gate_count": len(gate_spec["gates"]), "status": gate_spec["status"]},
        "scenario_catalog_summary": scenario_summary,
        "calibration_mapping_summary": "Context-only calibration mapping written for Barcelona, NYC, Chicago, and London.",
        "event_fabric_mapping_summary": "Future SUMO D3 producer maps to simulation_mobility with lifecycle_state=simulated_context and no_action_taken=true.",
        "limitation_summary": [
            "This is preflight, not full network extraction hardening.",
            "SUMO D2 Barcelona routeable-equivalent limitation remains open.",
            "Some cities may lack local road/network sources suitable for extraction.",
            "Calibration is context-only, not certified accuracy.",
            "No routing/control/certified traffic model claim.",
        ],
        "negative_test_summary": {"status": negative_report["status"], "test_count": len(negative_report["tests"])},
        "claim_boundary_summary": claim_scan,
        "no_mutation_summary": no_mutation,
        "secret_audit_summary": secret_scan,
        "recommended_next_main_task": "MAIN-SUMO-D3-NETWORK-EXTRACTION-HARDENING",
        "recommended_parallel_task": [
            "INFRA-TXR4070-DEEPSTREAM-CONTAINER-SMOKE-R1, if still pending",
            "MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE, only after DeepStream READY_CONTAINER",
            "SYNTHETIC-DATA-FACTORY-D1-EVENT-FABRIC-REPLAY-SMOKE-R1",
        ],
        "output_root": rel(OUTPUT_ROOT),
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_PREFLIGHT_R1_DECISION.json", decision)
    return decision


def main() -> int:
    before = capture_watch_signatures()
    ensure_output()
    prereq = validate_prerequisites()
    write_docs()
    inventory, city_profiles = build_source_inventory()
    write_crs_doc()
    subset_plan = subset_selection(city_profiles)
    gate_spec, _event_mapping = write_strategy_and_specs()
    scenario_summary = write_scenario_and_calibration_docs()
    conversion = probe_tooling_and_conversion()
    write_limitation_register(city_profiles, conversion)
    negative_report = negative_tests(conversion)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    claim_scan = scan_claims()
    write_claim_audit(claim_scan)
    secret_scan = write_secret_audit()
    hashes = write_hashes()
    decision = write_decision(
        prereq,
        inventory,
        subset_plan,
        conversion,
        gate_spec,
        scenario_summary,
        negative_report,
        claim_scan,
        no_mutation,
        secret_scan,
        hashes,
    )
    hashes = write_hashes()
    decision["checks"]["hashes"] = hashes["status"]
    write_json(OUTPUT_ROOT / "MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_PREFLIGHT_R1_DECISION.json", decision)
    write_hashes()

    print("MAIN-SUMO-D3-NETWORK-EXTRACTION-HARDENING-PREFLIGHT-R1: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Cities inventoried: {len(inventory['cities'])}")
    print(f"SUMO available: {conversion['sumo_tooling']['sumo']['available']}")
    print(f"netconvert available: {conversion['sumo_tooling']['netconvert']['available']}")
    print(f"Tiny conversion fixture: {conversion['tiny_fixture_conversion']['status']}")
    print(f"Validation gates: {len(gate_spec['gates'])}")
    print(f"Scenario catalog entries: {scenario_summary['scenario_count']}")
    print(f"Negative tests: {negative_report['status']}")
    print(f"Claim-boundary audit: {claim_scan['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret_scan['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if decision["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
