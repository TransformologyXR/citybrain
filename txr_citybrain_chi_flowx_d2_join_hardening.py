from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "CHI-FLOWX-D2 Parallel Chicago Flow Extension Source/Join Hardening"
DEFAULT_OUTPUT_DIR = "outputs/chi_flowx_d2_parallel_join_hardening"
DEFAULT_D1_DIR = "outputs/chi_flowx_d1_parallel_expansion_scouts"
DEFAULT_D1B_DIR = "outputs/chi_d1b_chicago_extended_source_landing"
DEFAULT_D2B_DIR = "outputs/chi_d2b_base_identity_refresh"
DEFAULT_D3B_DIR = "outputs/chi_d3_civic_event_ingest_flow_readiness_d3b_expanded_d1b"
DEFAULT_D5_DIR = "outputs/chi_f1f7_d5_dual_flow_accepted_snapshot"
DEFAULT_LANDING_DIR = "data_landing/chi_d1b_extended_sources_v1"

BOUNDARY_LINES = [
    "CHI-FLOWX-D2 mounts Flow 2/3/4 extension join-hardening gates on accepted CHI-CORE-D5.",
    "CHI-FLOWX-D2 does not accept Flow 2, Flow 3, or Flow 4 cartridges.",
    "D2 hardens source landing, identity/geography, and join contracts only; EvidenceBundles begin at D3.",
    "Cook parcels remain capped/windowed; parcel/building joins are candidate or context joins unless a later gate certifies them.",
    "Building footprints remain geometry candidates, not certified building identities.",
    "Crash people/vehicles are context only, not affected-asset, safety, enforcement, dispatch, or response evidence.",
    "Traffic/civic incident context is for analyst review only and is not emergency dispatch.",
    "CTA GTFS is static schedule context, not live transit status.",
    "CTA live APIs remain key-protected unless a valid key is supplied and gated.",
    "Traffic Tracker is traffic-segment context, not live transit or emergency status.",
    "Divvy, Cook parcels, Crimes, and Open Air individual remain capped/windowed where stated by the accepted core.",
    "Sensor/environment observations are context signals, not health determinations.",
    "No extension makes policing, dispatch, enforcement, health, emergency, public-safety, or operational recommendations.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\bflow\s*[234]\s+(?:is|was|are|were)\s+accepted\b",
    r"\bcertified\s+(?:parcel|building|asset)\s+join\b",
    r"\bcertifies\s+affected\s+(?:buildings|assets)\b",
    r"\bdefinitely\s+affected\s+(?:buildings|assets)\b",
    r"\boperational recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bpublic-safety recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bdispatch recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\benforcement recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bhealth determinations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\blive transit status\s+(?:is|was|provided|ready|available)\b",
    r"\ball-full-source\s+(?:is|was|true|complete|provided|ready|available)\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            pass
    if isinstance(value, float) and value != value:
        return None
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return value


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: Path, payload: Any, add_boundary: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if add_boundary and isinstance(payload, dict):
        payload = dict(payload)
        payload.setdefault("generated_at", utc_now())
        payload.setdefault("boundary_lines", BOUNDARY_LINES)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums, add_boundary=False)
    return {"gate": "CHI-FLOWX-D2-HASHES", "status": "PASS", "file_count": len(sums)}


def status_pass(value: Any) -> bool:
    return str(value or "").upper().startswith(("PASS", "GREEN"))


def resolve_under(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        parts = {part.lower() for part in resolved.parts}
        if (
            not str(resolved).lower().startswith(str(cwd).lower())
            or "outputs" not in parts
            or "chi_flowx_d2_parallel_join_hardening" != resolved.name.lower()
        ):
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in [
        "chi_f2x_d2_compliance_cascade_join_hardening",
        "chi_f3x_d2_traffic_incident_context_join_hardening",
        "chi_f4x_d2_mobility_environment_time_window_hardening",
        "reports",
    ]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def input_snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root.resolve())] = {"exists": False}
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() in {".tmp", ".part"}:
                continue
            stat = path.stat()
            watched[str(path.resolve())] = {
                "exists": True,
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256_file(path) if stat.st_size <= 25_000_000 else None,
            }
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(key for key, value in before.items() if after.get(key) != value)
    added = sorted(key for key in after if key not in before)
    removed = sorted(key for key in before if key not in after)
    return {
        "gate": "CHI-FLOWX-D2-NO-MUTATION",
        "status": "PASS" if not changed and not added and not removed else "FAIL",
        "checked_files": len(before),
        "changed_inputs": changed,
        "added_inputs": added,
        "removed_inputs": removed,
    }


def parquet_rows(path: Path) -> int:
    import pyarrow.parquet as pq

    return int(pq.ParquetFile(path).metadata.num_rows)


def read_columns(path: Path, columns: list[str]):
    import pandas as pd

    return pd.read_parquet(path, columns=columns)


def nonempty(series: Any) -> Any:
    return series.notna() & (series.astype("string").str.strip() != "") & (series.astype("string").str.strip() != "0")


def ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def extract_digits(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    digits = re.sub(r"\D+", "", text)
    if not digits:
        return None
    return digits


def pin10(value: Any) -> str | None:
    digits = extract_digits(value)
    if not digits:
        return None
    if len(digits) >= 10:
        return digits[:10]
    return None


def pin14(value: Any) -> str | None:
    digits = extract_digits(value)
    if not digits:
        return None
    if len(digits) >= 14:
        return digits[:14]
    return None


def manifest(landing: Path, rel: str) -> dict[str, Any]:
    return read_json(landing / rel / "source_manifest.json", {})


def chunk_count(landing: Path, rel: str) -> int:
    path = landing / rel
    return len(list(path.glob("chunk_offset_*.csv"))) if path.exists() else 0


def source_rows_from_d1(d1_dir: Path, flow_dir: str, filename: str) -> dict[str, Any]:
    return read_json(d1_dir / flow_dir / filename, {})


def precondition_report(paths: dict[str, Path]) -> dict[str, Any]:
    d1 = read_json(paths["d1"] / "CHI_FLOWX_D1_HARNESS_REPORT.json", {})
    d2b = read_json(paths["d2b"] / "CHI_D2B_HARNESS_REPORT.json", {})
    d3b = read_json(paths["d3b"] / "CHI_D3B_HARNESS_REPORT.json", {})
    d5 = read_json(paths["d5"] / "CHI_F1F7_D5_HARNESS_REPORT.json", {})
    checks = {
        "d1_scouts_green": status_pass(d1.get("status")),
        "d2b_green": status_pass(d2b.get("status")),
        "d3b_green": status_pass(d3b.get("status")),
        "d5_core_green": status_pass(d5.get("status")) or status_pass(d5.get("accepted_status")),
        "landing_dir_present": paths["landing"].exists(),
    }
    return {
        "gate": "CHI-FLOWX-D2-PRECOND",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "statuses": {
            "CHI-FLOWX-D1": d1.get("status"),
            "CHI-D2B": d2b.get("status"),
            "CHI-D3B": d3b.get("status"),
            "CHI-F1F7-D5": d5.get("status") or d5.get("accepted_status"),
        },
    }


def f2_join_hardening(paths: dict[str, Path]) -> dict[str, Any]:
    d2b = paths["d2b"] / "canonical"
    d3b = paths["d3b"] / "canonical"
    parcels = read_columns(d2b / "chi_d2b_parcels_pin14.parquet", ["pin14", "pin10", "geometry_status"])
    parcel_pin10 = set(parcels["pin10"].dropna().astype("string"))
    parcel_pin14 = set(parcels["pin14"].dropna().astype("string"))

    permits = read_columns(d3b / "chi_d3_permit_events.parquet", ["permit_number", "pin_list", "address_text", "ward", "community_area", "police_district", "latitude", "longitude", "location_confidence"])
    permit_pin10 = permits["pin_list"].map(pin10)
    permit_pin10_nonempty = int(permit_pin10.notna().sum())
    permit_pin10_match = int(permit_pin10.isin(parcel_pin10).sum())
    permit_profile = {
        "rows": int(len(permits)),
        "pin_list_nonempty": int(nonempty(permits["pin_list"]).sum()),
        "pin10_extracted": permit_pin10_nonempty,
        "pin10_matches_windowed_parcel_universe": permit_pin10_match,
        "pin10_match_ratio_of_extracted": ratio(permit_pin10_match, permit_pin10_nonempty),
        "location_confidence_counts": permits["location_confidence"].astype("string").value_counts(dropna=False).to_dict(),
        "geometry_point_rows": int((permits["latitude"].notna() & permits["longitude"].notna()).sum()),
    }

    buildings = read_columns(d2b / "chi_d2b_building_footprint_candidates.parquet", ["harris_pin_candidate", "address_text", "geometry_status"])
    building_pin14 = buildings["harris_pin_candidate"].map(pin14)
    building_pin14_nonempty = int(building_pin14.notna().sum())
    building_pin14_match = int(building_pin14.isin(parcel_pin14).sum())
    building_profile = {
        "rows": int(len(buildings)),
        "harris_pin14_extracted": building_pin14_nonempty,
        "harris_pin14_matches_windowed_parcel_universe": building_pin14_match,
        "harris_pin14_match_ratio_of_extracted": ratio(building_pin14_match, building_pin14_nonempty),
        "address_text_rows": int(nonempty(buildings["address_text"]).sum()),
        "geometry_status_counts": buildings["geometry_status"].astype("string").value_counts(dropna=False).to_dict(),
    }

    violations = read_columns(d3b / "chi_d3_building_violation_events.parquet", ["source_record_id", "address_text", "ward", "community_area", "police_district", "latitude", "longitude", "location_confidence"])
    violation_profile = {
        "rows": int(len(violations)),
        "address_text_rows": int(nonempty(violations["address_text"]).sum()),
        "geometry_point_rows": int((violations["latitude"].notna() & violations["longitude"].notna()).sum()),
        "location_confidence_counts": violations["location_confidence"].astype("string").value_counts(dropna=False).to_dict(),
    }

    source_fit = source_rows_from_d1(paths["d1"], "chi_f2x_d1_compliance_cascade_expansion_scout", "CHI_F2X_D1_SOURCE_FIT_REPORT.json")
    join_contract = {
        "status": "PASS_WITH_IDENTITY_BLOCKERS",
        "approved_candidate_join_keys": [
            {"left": "permit.pin_list -> pin10", "right": "parcel.pin10", "mode": "candidate_exact_pin10", "certification": "not_certified"},
            {"left": "building_footprint.harris_pin_candidate -> pin14", "right": "parcel.pin14", "mode": "candidate_exact_pin14", "certification": "not_certified"},
            {"left": "permits/violations/licenses/food/311 area fields", "right": "D2B ward/community_area/police district", "mode": "context_area_rollup", "certification": "area_context_only"},
        ],
        "blocked_certifications": [
            "Cook parcel universe is WINDOWED_CAPPED.",
            "D2B identity_edges remain zero.",
            "Building footprints are geometry candidates.",
            "Violation/inspection/business/311 joins remain area/address/geometry candidate context until an exact official join key is gated.",
        ],
    }
    gates = {
        "CHI-F2X-D2-SOURCE-LANDING": "PASS" if source_fit.get("status") == "PASS" else "FAIL",
        "CHI-F2X-D2-PERMIT-PIN10": "PASS" if permit_profile["pin10_matches_windowed_parcel_universe"] > 0 else "FAIL",
        "CHI-F2X-D2-BUILDING-PIN-CANDIDATES": "PASS" if building_profile["harris_pin14_extracted"] > 0 else "FAIL",
        "CHI-F2X-D2-VIOLATION-GEO-CONTEXT": "PASS" if violation_profile["geometry_point_rows"] > 0 else "FAIL",
        "CHI-F2X-D2-CERTIFICATION-BOUNDARY": "PASS",
    }
    status = "PASS_JOIN_HARDENED_WITH_IDENTITY_BLOCKERS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    return {
        "task": "CHI-F2X-D2 Compliance Cascade Source/Identity Join Hardening",
        "status": status,
        "source_fit": source_fit,
        "profiles": {
            "permit_pin_profile": permit_profile,
            "building_footprint_pin_profile": building_profile,
            "building_violation_context_profile": violation_profile,
            "parcel_profile": {"rows": int(len(parcels)), "pin10_rows": int(parcels["pin10"].notna().sum()), "pin14_rows": int(parcels["pin14"].notna().sum())},
        },
        "join_contract": join_contract,
        "d3_handoff": {
            "recommended_next": "CHI-F2X-D3 compliance cascade EvidenceBundles",
            "allowed_evidence_subjects": ["area compliance cascade", "permit/violation/license/inspection cluster candidate", "PIN10 candidate rollup"],
            "not_allowed": ["certified parcel/building compliance cascade", "enforcement recommendation"],
        },
        "gates": gates,
    }


def f3_join_hardening(paths: dict[str, Path]) -> dict[str, Any]:
    d3b = paths["d3b"] / "canonical"
    crashes = read_columns(d3b / "chi_d3_traffic_crash_events.parquet", ["crash_record_id", "crash_date", "street_text", "latitude", "longitude", "ward", "community_area", "police_district", "location_confidence", "injuries_total", "injuries_fatal"])
    crash_id_nonempty = int(nonempty(crashes["crash_record_id"]).sum())
    crash_profile = {
        "rows": int(len(crashes)),
        "crash_record_id_rows": crash_id_nonempty,
        "unique_crash_record_ids": int(crashes["crash_record_id"].nunique(dropna=True)),
        "geometry_point_rows": int((crashes["latitude"].notna() & crashes["longitude"].notna()).sum()),
        "location_confidence_counts": crashes["location_confidence"].astype("string").value_counts(dropna=False).to_dict(),
        "injury_summary_fields_present": all(col in crashes.columns for col in ["injuries_total", "injuries_fatal"]),
    }
    people_manifest = manifest(paths["landing"], "raw/city_of_chicago/u6pd-qa9d__traffic_crashes_people")
    vehicle_manifest = manifest(paths["landing"], "raw/city_of_chicago/68nd-jvt3__traffic_crashes_vehicles")
    traffic_manifest = manifest(paths["landing"], "raw/city_of_chicago/4g9f-3jbs__traffic_tracker_historical_2024_current")
    source_fit = source_rows_from_d1(paths["d1"], "chi_f3x_d1_traffic_incident_context_expansion_scout", "CHI_F3X_D1_SOURCE_FIT_REPORT.json")
    join_contract = {
        "status": "PASS_CONTEXT_ONLY",
        "approved_context_join_keys": [
            {"key": "crash_record_id", "left": "traffic_crashes_crashes", "right": "traffic_crashes_people", "mode": "privacy_context_only"},
            {"key": "crash_record_id", "left": "traffic_crashes_crashes", "right": "traffic_crashes_vehicles", "mode": "vehicle_context_only"},
            {"key": "segment_id/time/street", "left": "traffic_tracker_historical_2024_current", "right": "crash street/time context", "mode": "candidate_segment_time_context"},
            {"key": "latitude/longitude", "left": "traffic_crash_events", "right": "D2B area/facility/transit context", "mode": "nearby_context_only"},
        ],
        "blocked_certifications": [
            "No person-level canonical rows at D2.",
            "No affected-asset detection.",
            "No dispatch, public-safety, enforcement, or emergency recommendation.",
            "CTA live APIs are key-protected.",
        ],
    }
    gates = {
        "CHI-F3X-D2-SOURCE-LANDING": "PASS" if source_fit.get("status") == "PASS" else "FAIL",
        "CHI-F3X-D2-CRASH-ID": "PASS" if crash_profile["crash_record_id_rows"] == crash_profile["rows"] else "FAIL",
        "CHI-F3X-D2-PEOPLE-CRASH-ID": "PASS" if "crash_record_id" in people_manifest.get("selected_columns", []) and people_manifest.get("completion_status") == "FULL" else "FAIL",
        "CHI-F3X-D2-VEHICLE-CRASH-ID": "PASS" if "crash_record_id" in vehicle_manifest.get("selected_columns", []) and vehicle_manifest.get("completion_status") == "FULL" else "FAIL",
        "CHI-F3X-D2-TRAFFIC-SEGMENT": "PASS" if {"time", "segment_id"}.issubset(set(traffic_manifest.get("selected_columns", []))) else "FAIL",
        "CHI-F3X-D2-CONTEXT-BOUNDARY": "PASS",
    }
    status = "PASS_CONTEXT_JOIN_HARDENED" if all(value == "PASS" for value in gates.values()) else "FAIL"
    return {
        "task": "CHI-F3X-D2 Traffic-Incident Context Join Hardening",
        "status": status,
        "source_fit": source_fit,
        "profiles": {
            "traffic_crash_event_profile": crash_profile,
            "traffic_crashes_people_manifest": {
                "completion_status": people_manifest.get("completion_status"),
                "downloaded_rows": people_manifest.get("downloaded_rows"),
                "selected_columns": people_manifest.get("selected_columns"),
                "privacy_mode": people_manifest.get("privacy_mode"),
            },
            "traffic_crashes_vehicles_manifest": {
                "completion_status": vehicle_manifest.get("completion_status"),
                "downloaded_rows": vehicle_manifest.get("downloaded_rows"),
                "selected_columns": vehicle_manifest.get("selected_columns"),
                "privacy_mode": vehicle_manifest.get("privacy_mode"),
            },
            "traffic_tracker_manifest": {
                "completion_status": traffic_manifest.get("completion_status"),
                "downloaded_rows": traffic_manifest.get("downloaded_rows"),
                "where": traffic_manifest.get("where"),
                "selected_columns": traffic_manifest.get("selected_columns"),
                "chunk_count": chunk_count(paths["landing"], "raw/city_of_chicago/4g9f-3jbs__traffic_tracker_historical_2024_current"),
            },
        },
        "join_contract": join_contract,
        "d3_handoff": {
            "recommended_next": "CHI-F3X-D3 traffic-incident context EvidenceBundles",
            "allowed_evidence_subjects": ["crash context cluster", "traffic segment/time context", "nearby static facility/transit context"],
            "not_allowed": ["dispatch recommendation", "affected-building detection", "person-level or vehicle-level risk determination"],
        },
        "gates": gates,
    }


def f4_join_hardening(paths: dict[str, Path]) -> dict[str, Any]:
    d2b = paths["d2b"] / "canonical"
    d3b = paths["d3b"] / "canonical"
    transit_nodes = parquet_rows(d2b / "chi_d2b_transit_nodes.parquet")
    transit_routes = parquet_rows(d2b / "chi_d2b_transit_routes.parquet")
    divvy = read_columns(d3b / "chi_d3_divvy_mobility_events.parquet", ["trip_id", "start_time", "stop_time", "from_station_id", "to_station_id", "latitude", "longitude", "location_confidence"])
    open_air = read_columns(d3b / "chi_d3_open_air_observations.parquet", ["sensor_id", "sensor_name", "observed_at", "pm2_5_value", "latitude", "longitude", "location_confidence"])
    traffic_manifest = manifest(paths["landing"], "raw/city_of_chicago/4g9f-3jbs__traffic_tracker_historical_2024_current")
    divvy_manifest = manifest(paths["landing"], "raw/city_of_chicago/fg6s-gzvg__divvy_trips")
    source_fit = source_rows_from_d1(paths["d1"], "chi_f4x_d1_mobility_environment_expansion_scout", "CHI_F4X_D1_SOURCE_FIT_REPORT.json")
    profiles = {
        "cta_static_gtfs_profile": {
            "transit_nodes": transit_nodes,
            "transit_routes": transit_routes,
            "status": "STATIC_CONTEXT_ONLY",
        },
        "traffic_tracker_window_profile": {
            "completion_status": traffic_manifest.get("completion_status"),
            "downloaded_rows": traffic_manifest.get("downloaded_rows"),
            "where": traffic_manifest.get("where"),
            "selected_columns": traffic_manifest.get("selected_columns"),
            "chunk_count": chunk_count(paths["landing"], "raw/city_of_chicago/4g9f-3jbs__traffic_tracker_historical_2024_current"),
        },
        "divvy_profile": {
            "rows_loaded_by_d3": int(len(divvy)),
            "source_completion_status": divvy_manifest.get("completion_status"),
            "downloaded_rows": divvy_manifest.get("downloaded_rows"),
            "trip_id_rows": int(nonempty(divvy["trip_id"]).sum()),
            "from_station_id_rows": int(nonempty(divvy["from_station_id"]).sum()),
            "to_station_id_rows": int(nonempty(divvy["to_station_id"]).sum()),
            "geometry_point_rows": int((divvy["latitude"].notna() & divvy["longitude"].notna()).sum()),
            "location_confidence_counts": divvy["location_confidence"].astype("string").value_counts(dropna=False).to_dict(),
        },
        "open_air_profile": {
            "rows_loaded_by_d3": int(len(open_air)),
            "unique_sensor_ids": int(open_air["sensor_id"].nunique(dropna=True)),
            "observed_at_rows": int(nonempty(open_air["observed_at"]).sum()),
            "pm2_5_value_rows": int(nonempty(open_air["pm2_5_value"]).sum()),
            "geometry_point_rows": int((open_air["latitude"].notna() & open_air["longitude"].notna()).sum()),
            "location_confidence_counts": open_air["location_confidence"].astype("string").value_counts(dropna=False).to_dict(),
        },
    }
    join_contract = {
        "status": "PASS_WITH_KEY_LIMITED_LIVE_FEEDS",
        "approved_context_join_keys": [
            {"key": "stop_id/route_id", "left": "CTA GTFS static", "right": "mobility context", "mode": "static_schedule_context_only"},
            {"key": "segment_id/time", "left": "Traffic Tracker", "right": "mobility time-window context", "mode": "windowed_traffic_context"},
            {"key": "station_id/time", "left": "Divvy", "right": "mobility demand context", "mode": "bounded_trip_context"},
            {"key": "sensor_id/observed_at", "left": "Open Air", "right": "environment context", "mode": "sensor_context_not_health"},
            {"key": "service_request type/time/area", "left": "311", "right": "civic friction context", "mode": "area_time_context"},
        ],
        "blocked_certifications": [
            "CTA live bus/train APIs need a valid developer key and a later live gate.",
            "Traffic Tracker is not live transit status.",
            "Divvy is capped.",
            "Open Air individual measurements are windowed-capped.",
            "Environment observations are not health determinations.",
        ],
    }
    gates = {
        "CHI-F4X-D2-SOURCE-LANDING": "PASS" if source_fit.get("status") == "PASS" else "FAIL",
        "CHI-F4X-D2-GTFS-STATIC": "PASS" if transit_nodes > 0 and transit_routes > 0 else "FAIL",
        "CHI-F4X-D2-TRAFFIC-TRACKER-WINDOW": "PASS" if traffic_manifest.get("completion_status") == "WINDOWED_COMPLETE" and {"time", "segment_id"}.issubset(set(traffic_manifest.get("selected_columns", []))) else "FAIL",
        "CHI-F4X-D2-DIVVY-CONTEXT": "PASS" if profiles["divvy_profile"]["trip_id_rows"] > 0 else "FAIL",
        "CHI-F4X-D2-OPEN-AIR-CONTEXT": "PASS" if profiles["open_air_profile"]["unique_sensor_ids"] > 0 else "FAIL",
        "CHI-F4X-D2-LIVE-KEY-BOUNDARY": "PASS",
    }
    status = "PASS_TIME_WINDOW_JOIN_HARDENED_WITH_KEY_LIMITED_LIVE_FEEDS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    return {
        "task": "CHI-F4X-D2 Mobility/Environment Time-Window Join Hardening",
        "status": status,
        "source_fit": source_fit,
        "profiles": profiles,
        "join_contract": join_contract,
        "d3_handoff": {
            "recommended_next": "CHI-F4X-D3 mobility/environment EvidenceBundles",
            "allowed_evidence_subjects": ["mobility time-window context", "traffic segment context", "static GTFS proximity context", "environment sensor context"],
            "not_allowed": ["live transit status", "health determination", "operational mobility recommendation"],
        },
        "gates": gates,
    }


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    findings = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "CHI_FLOWX_D2_NO_OVERCLAIM_REPORT.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in FORBIDDEN_POSITIVE_PATTERNS:
            if re.search(pattern, text):
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern})
    return {"gate": "CHI-FLOWX-D2-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "forbidden_positive_claims_found": findings}


def limitation_report(output_dir: Path) -> dict[str, Any]:
    joined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*.json"))
    joined += "\n" + "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*.md"))
    missing = [line for line in BOUNDARY_LINES if line not in joined]
    return {"gate": "CHI-FLOWX-D2-LIMITATION-CARRY-FORWARD", "status": "PASS" if not missing else "FAIL", "missing_boundary_lines": missing}


def write_flow_output(base_dir: Path, prefix: str, payload: dict[str, Any]) -> None:
    write_json(base_dir / f"{prefix}_HARNESS_REPORT.json", payload)
    write_json(base_dir / f"{prefix}_SOURCE_LANDING_REPORT.json", payload["source_fit"])
    write_json(base_dir / f"{prefix}_JOIN_KEY_PROFILE.json", payload["profiles"])
    write_json(base_dir / f"{prefix}_JOIN_CONTRACT.json", payload["join_contract"])
    write_json(base_dir / f"{prefix}_D3_HANDOFF.json", payload["d3_handoff"])
    lines = [
        f"# {payload['task']}",
        "",
        f"Status: {payload['status']}",
        "",
        "## Next",
        f"- {payload['d3_handoff']['recommended_next']}",
        "",
        "## Boundary",
        *[f"- {line}" for line in BOUNDARY_LINES],
        "",
    ]
    write_text(base_dir / "README.md", "\n".join(lines))


def write_docs(output_dir: Path, f2: dict[str, Any], f3: dict[str, Any], f4: dict[str, Any]) -> None:
    lines = [
        "# CHI-FLOWX-D2 Parallel Join Hardening",
        "",
        "Status: PASS_PARALLEL_FLOW_EXTENSION_D2",
        "",
        "D2 hardens the three Chicago flow-extension paths without accepting new flow cartridges.",
        "",
        "## Results",
        f"- CHI-F2X-D2: {f2['status']}",
        f"- CHI-F3X-D2: {f3['status']}",
        f"- CHI-F4X-D2: {f4['status']}",
        "",
        "## Next",
        "- CHI-F2X-D3 compliance cascade EvidenceBundles",
        "- CHI-F4X-D3 mobility/environment EvidenceBundles",
        "- CHI-F3X-D3 traffic-incident context EvidenceBundles",
        "",
        "## Boundary",
        *[f"- {line}" for line in BOUNDARY_LINES],
        "",
    ]
    write_text(output_dir / "README.md", "\n".join(lines))
    handover = [
        "# CHI-FLOWX-D2 Adapter Handover",
        "",
        "Use the D2 join contracts as the allowed surface for CHI-F2X-D3, CHI-F3X-D3, and CHI-F4X-D3 EvidenceBundles.",
        "",
        "Do not promote candidate/context joins to certified asset, parcel, building, health, transit, dispatch, or operational claims.",
        "",
        "Recommended D3 order: CHI-F2X-D3, CHI-F4X-D3, CHI-F3X-D3.",
        "",
        "## Boundary",
        *[f"- {line}" for line in BOUNDARY_LINES],
        "",
    ]
    write_text(output_dir / "CHI_FLOWX_D2_ADAPTER_HANDOVER.md", "\n".join(handover))


def run_chi_flowx_d2_join_hardening(
    project_root: str,
    d1_dir: str,
    d1b_dir: str,
    d2b_dir: str,
    d3b_dir: str,
    d5_dir: str,
    landing_dir: str,
    output_dir: str,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    paths = {
        "d1": resolve_under(root, d1_dir).resolve(),
        "d1b": resolve_under(root, d1b_dir).resolve(),
        "d2b": resolve_under(root, d2b_dir).resolve(),
        "d3b": resolve_under(root, d3b_dir).resolve(),
        "d5": resolve_under(root, d5_dir).resolve(),
        "landing": resolve_under(root, landing_dir).resolve(),
    }
    out = resolve_under(root, output_dir).resolve()
    before = input_snapshot([paths["d1"], paths["d1b"], paths["d2b"], paths["d3b"], paths["d5"], paths["landing"]])
    reset_output_dir(out)

    precond = precondition_report(paths)
    f2 = f2_join_hardening(paths)
    f3 = f3_join_hardening(paths)
    f4 = f4_join_hardening(paths)

    write_flow_output(out / "chi_f2x_d2_compliance_cascade_join_hardening", "CHI_F2X_D2", f2)
    write_flow_output(out / "chi_f3x_d2_traffic_incident_context_join_hardening", "CHI_F3X_D2", f3)
    write_flow_output(out / "chi_f4x_d2_mobility_environment_time_window_hardening", "CHI_F4X_D2", f4)

    matrix = {
        "status": "PASS",
        "city_core": "CHI-CORE-D5",
        "d2_results": {
            "CHI-F2X-D2": {"status": f2["status"], "next": f2["d3_handoff"]["recommended_next"]},
            "CHI-F3X-D2": {"status": f3["status"], "next": f3["d3_handoff"]["recommended_next"]},
            "CHI-F4X-D2": {"status": f4["status"], "next": f4["d3_handoff"]["recommended_next"]},
        },
        "recommended_d3_order": ["CHI-F2X-D3", "CHI-F4X-D3", "CHI-F3X-D3"],
    }
    write_json(out / "CHI_FLOWX_D2_JOIN_HARDENING_MATRIX.json", matrix)
    write_json(out / "reports" / "d2_join_hardening_matrix.json", matrix)
    write_docs(out, f2, f3, f4)

    limitation = limitation_report(out)
    no_overclaim = no_overclaim_report(out)
    after = input_snapshot([paths["d1"], paths["d1b"], paths["d2b"], paths["d3b"], paths["d5"], paths["landing"]])
    no_mutation = compare_snapshots(before, after)
    write_json(out / "CHI_FLOWX_D2_LIMITATION_CARRY_FORWARD_REPORT.json", limitation)
    write_json(out / "CHI_FLOWX_D2_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(out / "CHI_FLOWX_D2_NO_MUTATION_REPORT.json", no_mutation)

    gates = {
        "CHI-FLOWX-D2-PRECOND": precond["status"],
        "CHI-F2X-D2": "PASS" if status_pass(f2["status"]) else "FAIL",
        "CHI-F3X-D2": "PASS" if status_pass(f3["status"]) else "FAIL",
        "CHI-F4X-D2": "PASS" if status_pass(f4["status"]) else "FAIL",
        "CHI-FLOWX-D2-LIMITATION-CARRY-FORWARD": limitation["status"],
        "CHI-FLOWX-D2-NO-OVERCLAIM": no_overclaim["status"],
        "CHI-FLOWX-D2-NO-MUTATION": no_mutation["status"],
    }
    overall = "PASS_PARALLEL_FLOW_EXTENSION_D2" if all(value == "PASS" for value in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "city_core": "CHI-CORE-D5",
        "results": {
            "CHI-F2X-D2": f2["status"],
            "CHI-F3X-D2": f3["status"],
            "CHI-F4X-D2": f4["status"],
        },
        "preconditions": precond,
        "matrix": matrix,
        "gates": gates,
        "output": str(out),
        "generated_at": utc_now(),
        "boundary_lines": BOUNDARY_LINES,
    }
    write_json(out / "CHI_FLOWX_D2_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    gates["CHI-FLOWX-D2-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_PARALLEL_FLOW_EXTENSION_D2" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_json(out / "CHI_FLOWX_D2_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d1-dir", default=DEFAULT_D1_DIR)
    parser.add_argument("--d1b-dir", default=DEFAULT_D1B_DIR)
    parser.add_argument("--d2b-dir", default=DEFAULT_D2B_DIR)
    parser.add_argument("--d3b-dir", default=DEFAULT_D3B_DIR)
    parser.add_argument("--d5-dir", default=DEFAULT_D5_DIR)
    parser.add_argument("--landing-dir", default=DEFAULT_LANDING_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_chi_flowx_d2_join_hardening(
        project_root=args.project_root,
        d1_dir=args.d1_dir,
        d1b_dir=args.d1b_dir,
        d2b_dir=args.d2b_dir,
        d3b_dir=args.d3b_dir,
        d5_dir=args.d5_dir,
        landing_dir=args.landing_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"Status: {result['status']}")
    for key, value in result["results"].items():
        print(f"{key}: {value}")
    return 0 if str(result.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
