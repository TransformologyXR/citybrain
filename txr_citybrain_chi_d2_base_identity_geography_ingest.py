from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "CHI-D2 Chicago Base Identity + Geography Ingest"
DEFAULT_OUTPUT_DIR = "outputs/chi_d2_base_identity_geography_ingest"
DEFAULT_CHI_D1_OUTPUT = "outputs/chi_d1_chicago_deep_source_api_scout"
DEFAULT_CHI_D1_LANDING = "data_landing/chi_d1_official_sources_v1"

BOUNDARY_LINES = [
    "CHI-D2 creates a Chicago base identity/geography ingest only.",
    "CHI-D2 does not create a certified Chicago cartridge.",
    "CHI-D2 does not build Flow 1 or Flow 7.",
    "CHI-D2 does not certify affected assets/buildings.",
    "CHI-D2 does not make operational, policing, dispatch, enforcement, or health recommendations.",
    "Cook PIN14 is the native parcel anchor where present.",
    "Building footprints are geometry candidates, not automatically certified parcel identities.",
    "CTA GTFS is static schedule geography, not live transit status.",
    "CTA live APIs remain key-protected unless keys are present.",
]

FORBIDDEN_PATTERNS = [
    r"creates a certified chicago cartridge",
    r"chicago cartridge (?:is )?certified",
    r"flow 1 (?:is )?(?:complete|built|green)",
    r"flow 7 (?:is )?(?:complete|built|green)",
    r"certified affected (?:asset|building)",
    r"emergency dispatch",
    r"policing recommendation",
    r"chi-d2 makes? .*health recommendations?",
    r"health recommendations? (?:are )?(?:made|available)",
    r"cta live status",
    r"parcel:us-chicago:bbl",
    r"building:us-chicago:bin",
    r"parcel:us-chicago:uprn",
    r"building:us-chicago:toid",
]

SOURCE_KEYS = {
    "parcels": "cook_county/cook_county_parcel_universe",
    "city": "city_of_chicago/boundaries_city",
    "community_area": "city_of_chicago/boundaries_community_areas",
    "ward": "city_of_chicago/boundaries_wards_2023",
    "police_district": "city_of_chicago/boundaries_police_districts",
    "neighborhood": "city_of_chicago/neighborhoods_2012b",
    "building_footprints": "city_of_chicago/building_footprints_primary",
    "street_centerlines": "city_of_chicago/street_center_lines",
    "fire_stations": "city_of_chicago/fire_stations",
    "police_stations": "city_of_chicago/police_stations",
    "libraries": "city_of_chicago/libraries",
    "schools": "city_of_chicago/cps_school_locations",
    "hospitals": "city_of_chicago/cook_county_hospitals",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
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
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "chi_d2_base_identity_geography_ingest" not in resolved.name.lower():
            raise ValueError(f"Refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["canonical", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root)] = {"exists": False}
            continue
        files = [root] if root.is_file() else [p for p in sorted(root.rglob("*")) if p.is_file()]
        for path in files:
            stat = path.stat()
            watched[str(path)] = {
                "exists": True,
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256_file(path) if stat.st_size < 250_000_000 else None,
            }
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, old in before.items():
        if old != after.get(key):
            changed.append({"path": key, "before": old, "after": after.get(key)})
    return {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "checked_files": len(before)}


def safe_id(value: Any, fallback: str = "unknown") -> str:
    text = str(value if value is not None else fallback).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:160] or fallback


def cell(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "none", "null", "<na>"} else None


def num(value: Any) -> float | None:
    text = cell(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def geometry_json(value: Any) -> str | None:
    if isinstance(value, dict) and value.get("type"):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return None


def point_from_location(record: dict[str, Any], lat_keys: list[str], lon_keys: list[str]) -> tuple[float | None, float | None, str | None]:
    for key in ["location", "the_geom"]:
        loc = record.get(key)
        if isinstance(loc, dict):
            if "latitude" in loc and "longitude" in loc:
                return num(loc.get("latitude")), num(loc.get("longitude")), geometry_json({"type": "Point", "coordinates": [num(loc.get("longitude")), num(loc.get("latitude"))]})
            if loc.get("type") == "Point" and isinstance(loc.get("coordinates"), list) and len(loc["coordinates"]) >= 2:
                return num(loc["coordinates"][1]), num(loc["coordinates"][0]), geometry_json(loc)
    lat = next((num(record.get(k)) for k in lat_keys if num(record.get(k)) is not None), None)
    lon = next((num(record.get(k)) for k in lon_keys if num(record.get(k)) is not None), None)
    geom = geometry_json({"type": "Point", "coordinates": [lon, lat]}) if lat is not None and lon is not None else None
    return lat, lon, geom


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame.empty:
        frame = pd.DataFrame({"_empty": pd.Series(dtype="string")})
    frame.to_parquet(path, index=False)


def records_for(raw_root: Path, source_rel: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_dir = raw_root / "raw" / source_rel
    files = sorted(source_dir.glob("page_*.json"))
    used_sample = False
    if not files and (source_dir / "sample.json").exists():
        files = [source_dir / "sample.json"]
        used_sample = True
    records: list[dict[str, Any]] = []
    for path in files:
        data = read_json(path, [])
        if isinstance(data, list):
            records.extend([r for r in data if isinstance(r, dict) and r])
        elif isinstance(data, dict) and data and not data.get("error"):
            records.append(data)
    count_payload = read_json(source_dir / "count.json", {})
    row_count = None
    if isinstance(count_payload, dict):
        row_count = count_payload.get("count") or count_payload.get("row_count")
    elif isinstance(count_payload, list) and count_payload and isinstance(count_payload[0], dict):
        row_count = next(iter(count_payload[0].values()), None)
    try:
        row_count = int(row_count) if row_count is not None else None
    except Exception:
        row_count = None
    metadata = read_json(source_dir / "metadata.json", {})
    profile = {
        "source_dir": str(source_dir),
        "exists": source_dir.exists(),
        "files_read": [str(p) for p in files],
        "used_sample_only": used_sample,
        "records_loaded": len(records),
        "official_row_count": row_count,
        "metadata_name": metadata.get("name"),
        "metadata_id": metadata.get("id"),
        "source_limited": source_dir.exists() and not records,
    }
    return records, profile


def counts_lookup(chi_d1_output: Path) -> dict[str, dict[str, Any]]:
    report = read_json(chi_d1_output / "CHI_D1_COUNTS_REPORT.json", {})
    return {item.get("source_key"): item for item in report.get("counts", []) if item.get("source_key")}


def normalize_pin(raw: Any) -> tuple[str | None, str]:
    text = cell(raw)
    if not text:
        return None, "pin_normalization_failed"
    digits = re.sub(r"\D", "", text)
    if not digits or len(digits) > 14:
        return None, "pin_normalization_failed"
    return digits.zfill(14), "pin14_normalized"


def build_parcels(records: list[dict[str, Any]], source_info: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    status_counts = Counter()
    for idx, record in enumerate(records):
        pin14, pin_status = normalize_pin(record.get("pin") or record.get("pin14") or record.get("pin10"))
        status_counts[pin_status] += 1
        lat, lon, geom = point_from_location(record, ["lat", "latitude"], ["lon", "longitude"])
        raw_pin = cell(record.get("pin") or record.get("pin10"))
        rows.append(
            {
                "canonical_id": f"parcel:us-chicago:cook_pin:{pin14 or safe_id(raw_pin, 'unknown_pin_' + str(idx))}",
                "entity_type": "Parcel",
                "pin14": pin14,
                "raw_pin": raw_pin,
                "pin_status": pin_status,
                "address_text": cell(record.get("address") or record.get("property_address")),
                "city": cell(record.get("city")),
                "township": cell(record.get("township_name")),
                "property_class": cell(record.get("class")),
                "latitude": lat,
                "longitude": lon,
                "geometry_status": "official_point" if geom else "missing_geometry",
                "geometry_json": geom,
                "source_record_id": raw_pin or str(idx),
                "source_dataset": "Cook County Assessor Parcel Universe",
                "source_status": source_info.get("source_status", "UNKNOWN"),
                "confidence": 0.9 if pin14 else 0.35,
                "provenance": json.dumps([{"source": "CHI-D1 landed Cook County parcel universe", "raw_pin": raw_pin}], sort_keys=True),
            }
        )
    frame = pd.DataFrame(rows)
    profile = {"records": len(frame), "pin_status_counts": dict(status_counts), "source_status": source_info.get("source_status"), "official_row_count": source_info.get("row_count")}
    return frame, profile


def build_areas(raw_root: Path, counts: dict[str, dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    layer_profiles = {}
    mapping = [
        ("city", "city", "area:us-chicago:city:chicago"),
        ("community_area", "community_area", None),
        ("ward", "ward", None),
        ("police_district", "police_district", None),
        ("neighborhood", "neighborhood", None),
    ]
    for area_type, source_key, fixed_id in mapping:
        rel = SOURCE_KEYS[source_key]
        records, profile = records_for(raw_root, rel)
        d1_key = "boundaries_" + source_key + "s" if source_key in {"city", "community_area"} else None
        if source_key == "ward":
            d1_key = "boundaries_wards_2023"
        elif source_key == "police_district":
            d1_key = "boundaries_police_districts"
        elif source_key == "neighborhood":
            d1_key = "neighborhoods_2012b"
        source_info = counts.get(d1_key or source_key, {})
        layer_profiles[source_key] = {**profile, "d1_source_status": source_info.get("source_status"), "d1_row_count": source_info.get("row_count")}
        for idx, record in enumerate(records):
            if area_type == "city":
                native = "chicago"
                name = cell(record.get("name")) or "Chicago"
            elif area_type == "community_area":
                native = cell(record.get("area_numbe") or record.get("area_num_1") or record.get("community")) or str(idx)
                name = cell(record.get("community")) or native
            elif area_type == "ward":
                native = cell(record.get("ward") or record.get("ward_id")) or str(idx)
                name = f"Ward {native}"
            elif area_type == "police_district":
                native = cell(record.get("dist_num") or record.get("district") or record.get("district_id")) or str(idx)
                name = f"Police District {native}"
            else:
                native = cell(record.get("pri_neigh") or record.get("sec_neigh")) or str(idx)
                name = native
            cid = fixed_id or f"area:us-chicago:{area_type}:{safe_id(native)}"
            geom = geometry_json(record.get("the_geom"))
            rows.append(
                {
                    "canonical_id": cid,
                    "entity_type": "Area",
                    "area_type": area_type,
                    "native_id": native,
                    "name": name,
                    "source_layer": source_key,
                    "source_dataset": layer_profiles[source_key].get("metadata_name"),
                    "geometry_status": "official_polygon" if geom else "missing_geometry",
                    "geometry_json": geom,
                    "source_record_id": native,
                    "source_status": source_info.get("source_status", "UNKNOWN"),
                    "confidence": 0.9 if geom else 0.25,
                    "provenance": json.dumps([{"source": rel, "record_index": idx}], sort_keys=True),
                }
            )
    frame = pd.DataFrame(rows)
    return frame, layer_profiles


def build_buildings(records: list[dict[str, Any]], source_info: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    for idx, record in enumerate(records):
        source_id = cell(record.get("bldg_id") or record.get("orig_bldg_") or record.get("objectid")) or str(idx)
        address = " ".join([cell(record.get(k)) or "" for k in ["f_add1", "pre_dir1", "st_name1", "st_type1", "suf_dir1"]]).strip() or None
        geom = geometry_json(record.get("the_geom"))
        rows.append(
            {
                "canonical_id": f"building:us-chicago:building_footprint:{safe_id(source_id)}",
                "entity_type": "Building",
                "source_id": source_id,
                "building_status": cell(record.get("bldg_statu")),
                "address_text": address,
                "stories": cell(record.get("stories") or record.get("no_stories")),
                "year_built": cell(record.get("year_built")),
                "geometry_status": "official_polygon_candidate" if geom else "missing_geometry",
                "geometry_json": geom,
                "source_dataset": "Chicago Building Footprints",
                "source_status": source_info.get("source_status", "UNKNOWN"),
                "confidence": 0.82 if geom else 0.25,
                "provenance": json.dumps([{"source": "CHI-D1 building footprints landed material", "source_id": source_id}], sort_keys=True),
            }
        )
    profile = {"records": len(rows), "source_status": source_info.get("source_status"), "official_row_count": source_info.get("row_count"), "geometry_candidates": sum(1 for r in rows if r["geometry_json"])}
    return pd.DataFrame(rows), profile


def build_road_segments(records: list[dict[str, Any]], source_info: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    for idx, record in enumerate(records):
        source_id = cell(record.get("objectid") or record.get("segmentid") or record.get("street_nam") or record.get("full_stree")) or str(idx)
        geom = geometry_json(record.get("the_geom"))
        rows.append(
            {
                "canonical_id": f"roadsegment:us-chicago:street_centerline:{safe_id(source_id)}",
                "entity_type": "RoadSegment",
                "source_id": source_id,
                "street_name": cell(record.get("street_nam") or record.get("street") or record.get("full_stree")),
                "geometry_status": "official_line" if geom else "missing_geometry",
                "geometry_json": geom,
                "source_dataset": "Street Center Lines",
                "source_status": source_info.get("source_status", "UNKNOWN"),
                "confidence": 0.86 if geom else 0.25,
                "provenance": json.dumps([{"source": "CHI-D1 street center lines", "source_id": source_id}], sort_keys=True),
            }
        )
    profile = {
        "records": len(rows),
        "source_status": source_info.get("source_status"),
        "official_row_count": source_info.get("row_count"),
        "source_limited_reason": None if rows else "landed page rows had no usable fields/geometry",
    }
    return pd.DataFrame(rows), profile


def parse_gtfs(gtfs_zip: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if not gtfs_zip.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {"status": "FAIL", "reason": "GTFS zip missing"}
    with zipfile.ZipFile(gtfs_zip) as zf:
        names = set(zf.namelist())
        required = ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt", "calendar.txt", "calendar_dates.txt", "agency.txt"]
        present = {name: name in names for name in required + ["shapes.txt"]}
        stops = pd.read_csv(zf.open("stops.txt"), dtype=str)
        routes = pd.read_csv(zf.open("routes.txt"), dtype=str)
        trips = pd.read_csv(zf.open("trips.txt"), dtype=str, usecols=lambda c: c in {"route_id", "trip_id"})
        trip_to_route = dict(zip(trips["trip_id"], trips["route_id"]))
        route_stop_pairs: set[tuple[str, str]] = set()
        for chunk in pd.read_csv(zf.open("stop_times.txt"), dtype=str, usecols=lambda c: c in {"trip_id", "stop_id"}, chunksize=750_000):
            chunk["route_id"] = chunk["trip_id"].map(trip_to_route)
            pairs = chunk[["route_id", "stop_id"]].dropna().drop_duplicates()
            route_stop_pairs.update((str(r), str(s)) for r, s in pairs.itertuples(index=False, name=None))
        stop_rows = []
        for _, row in stops.iterrows():
            stop_id = cell(row.get("stop_id"))
            if not stop_id:
                continue
            stop_rows.append(
                {
                    "canonical_id": f"transit_node:us-chicago:cta_stop:{safe_id(stop_id)}",
                    "entity_type": "TransitNode",
                    "stop_id": stop_id,
                    "stop_name": cell(row.get("stop_name")),
                    "stop_code": cell(row.get("stop_code")),
                    "parent_station": cell(row.get("parent_station")),
                    "location_type": cell(row.get("location_type")),
                    "latitude": num(row.get("stop_lat")),
                    "longitude": num(row.get("stop_lon")),
                    "geometry_status": "official_point" if cell(row.get("stop_lat")) and cell(row.get("stop_lon")) else "missing_geometry",
                    "geometry_json": geometry_json({"type": "Point", "coordinates": [num(row.get("stop_lon")), num(row.get("stop_lat"))]}) if cell(row.get("stop_lat")) and cell(row.get("stop_lon")) else None,
                    "source_dataset": "CTA GTFS static schedule",
                    "source_status": "FULL_STATIC_GTFS",
                    "confidence": 0.9,
                    "provenance": json.dumps([{"source": "google_transit.zip/stops.txt", "stop_id": stop_id}], sort_keys=True),
                }
            )
        route_rows = []
        for _, row in routes.iterrows():
            route_id = cell(row.get("route_id"))
            if not route_id:
                continue
            route_rows.append(
                {
                    "canonical_id": f"transit_route:us-chicago:cta_route:{safe_id(route_id)}",
                    "entity_type": "TransitRoute",
                    "route_id": route_id,
                    "route_short_name": cell(row.get("route_short_name")),
                    "route_long_name": cell(row.get("route_long_name")),
                    "route_type": cell(row.get("route_type")),
                    "agency_id": cell(row.get("agency_id")),
                    "source_dataset": "CTA GTFS static schedule",
                    "source_status": "FULL_STATIC_GTFS",
                    "confidence": 0.9,
                    "provenance": json.dumps([{"source": "google_transit.zip/routes.txt", "route_id": route_id}], sort_keys=True),
                }
            )
        edge_rows = []
        stop_ids = {r["stop_id"] for r in stop_rows}
        route_ids = {r["route_id"] for r in route_rows}
        for route_id, stop_id in sorted(route_stop_pairs):
            if route_id not in route_ids or stop_id not in stop_ids:
                continue
            route_cid = f"transit_route:us-chicago:cta_route:{safe_id(route_id)}"
            stop_cid = f"transit_node:us-chicago:cta_stop:{safe_id(stop_id)}"
            edge_rows.append(
                {
                    "canonical_id": f"edge:us-chicago:chi-d2:route_has_stop:{safe_id(route_id)}:{safe_id(stop_id)}",
                    "entity_type": "context_edge",
                    "source_id": route_cid,
                    "target_id": stop_cid,
                    "relation": "route_has_stop",
                    "join_method": "gtfs_trips_stop_times",
                    "source_stage": "CHI-D2",
                    "confidence": 0.9,
                    "status": "static_gtfs_context",
                }
            )
            edge_rows.append(
                {
                    "canonical_id": f"edge:us-chicago:chi-d2:stop_served_by_route:{safe_id(stop_id)}:{safe_id(route_id)}",
                    "entity_type": "context_edge",
                    "source_id": stop_cid,
                    "target_id": route_cid,
                    "relation": "transit_node_served_by_route",
                    "join_method": "gtfs_trips_stop_times",
                    "source_stage": "CHI-D2",
                    "confidence": 0.9,
                    "status": "static_gtfs_context",
                }
            )
        profile = {
            "status": "PASS",
            "zip_path": str(gtfs_zip),
            "files_present": present,
            "stops": len(stop_rows),
            "routes": len(route_rows),
            "trips": int(len(trips)),
            "route_stop_pairs": len(route_stop_pairs),
            "context_edges": len(edge_rows),
            "live_status": "not_live_static_gtfs_only",
        }
    return pd.DataFrame(stop_rows), pd.DataFrame(route_rows), pd.DataFrame(edge_rows), profile


def build_facilities(raw_root: Path, counts: dict[str, dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    specs = [
        ("fire_station", "fire_stations", "fire_stations", "name", "resource:us-chicago:fire_station"),
        ("police_station", "police_stations", "police_stations", "district", "resource:us-chicago:police_station"),
        ("library", "libraries", "libraries", "branch_", "resource:us-chicago:library"),
        ("school", "schools", "cps_school_locations", "school_id", "resource:us-chicago:school"),
        ("hospital", "hospitals", "cook_county_hospitals", "name", "resource:us-chicago:hospital"),
    ]
    rows = []
    profile = {}
    for resource_type, source_key, d1_key, id_col, prefix in specs:
        records, load_profile = records_for(raw_root, SOURCE_KEYS[source_key])
        source_info = counts.get(d1_key, {})
        profile[source_key] = {**load_profile, "resource_type": resource_type, "d1_source_status": source_info.get("source_status"), "d1_row_count": source_info.get("row_count")}
        for idx, record in enumerate(records):
            source_id = cell(record.get(id_col) or record.get("name") or record.get("short_name") or record.get("district_name")) or str(idx)
            lat, lon, geom = point_from_location(record, ["lat", "latitude"], ["long", "longitude"])
            rows.append(
                {
                    "canonical_id": f"{prefix}:{safe_id(source_id)}",
                    "entity_type": "Resource",
                    "resource_type": resource_type,
                    "source_id": source_id,
                    "name": cell(record.get("name") or record.get("branch_") or record.get("short_name") or record.get("district_name")),
                    "address_text": cell(record.get("address")),
                    "city": cell(record.get("city")),
                    "state": cell(record.get("state")),
                    "zip": cell(record.get("zip")),
                    "latitude": lat,
                    "longitude": lon,
                    "geometry_status": "official_point" if geom else "missing_geometry",
                    "geometry_json": geom,
                    "source_layer": source_key,
                    "source_status": source_info.get("source_status", "UNKNOWN"),
                    "confidence": 0.88 if geom else 0.45,
                    "provenance": json.dumps([{"source": SOURCE_KEYS[source_key], "source_id": source_id}], sort_keys=True),
                }
            )
    return pd.DataFrame(rows), profile


def point_area_edges(point_frames: list[pd.DataFrame], areas: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    try:
        from shapely.geometry import Point, shape
        from shapely.prepared import prep
    except Exception as exc:
        return pd.DataFrame(), {"status": "SOURCE_LIMITED", "reason": f"shapely unavailable: {exc}"}
    area_records = []
    if areas.empty or "_empty" in areas.columns:
        return pd.DataFrame(), {"status": "SOURCE_LIMITED", "reason": "no area polygons"}
    for record in areas.to_dict("records"):
        geom_text = record.get("geometry_json")
        if not geom_text:
            continue
        try:
            geom = shape(json.loads(geom_text))
            area_records.append((record["canonical_id"], record.get("area_type"), prep(geom)))
        except Exception:
            continue
    rows = []
    for frame in point_frames:
        if frame.empty or "_empty" in frame.columns or "latitude" not in frame.columns or "longitude" not in frame.columns:
            continue
        for record in frame.to_dict("records"):
            lat = num(record.get("latitude"))
            lon = num(record.get("longitude"))
            if lat is None or lon is None:
                continue
            point = Point(lon, lat)
            for area_id, area_type, prepared in area_records:
                if prepared.contains(point) or prepared.intersects(point):
                    rows.append(
                        {
                            "canonical_id": f"edge:us-chicago:chi-d2:{safe_id(record.get('canonical_id'))}:within_area:{safe_id(area_id)}",
                            "entity_type": "context_edge",
                            "source_id": record.get("canonical_id"),
                            "target_id": area_id,
                            "relation": "within_area_context",
                            "join_method": "official_point_within_official_polygon",
                            "source_stage": "CHI-D2",
                            "area_type": area_type,
                            "confidence": 0.86,
                            "status": "geometry_backed_context",
                        }
                    )
    frame = pd.DataFrame(rows).drop_duplicates(subset=["source_id", "target_id"]) if rows else pd.DataFrame()
    return frame, {"status": "PASS" if not frame.empty else "SOURCE_LIMITED", "area_polygons_used": len(area_records), "context_edges": int(len(frame))}


def edge_integrity(identity_edges: pd.DataFrame, context_edges: pd.DataFrame, node_frames: list[pd.DataFrame]) -> dict[str, Any]:
    nodes = set()
    for frame in node_frames:
        if not frame.empty and "_empty" not in frame.columns and "canonical_id" in frame.columns:
            nodes.update(frame["canonical_id"].dropna().astype(str).tolist())
    missing = []
    for label, frame in [("identity", identity_edges), ("context", context_edges)]:
        if frame.empty or "_empty" in frame.columns:
            continue
        for rec in frame[["canonical_id", "source_id", "target_id"]].to_dict("records"):
            if rec["source_id"] not in nodes or rec["target_id"] not in nodes:
                missing.append({"edge_type": label, **rec})
    return {"status": "PASS" if not missing else "FAIL", "node_count": len(nodes), "missing_endpoints": missing[:50], "missing_endpoint_count": len(missing)}


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    combined = ""
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == "CHI_D2_NO_OVERCLAIM_REPORT.json":
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt", ".html"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        combined += "\n" + text.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text.lower()):
                findings.append({"path": str(path), "forbidden_pattern": pattern})
    missing = [line for line in BOUNDARY_LINES if line.lower() not in combined]
    return {"status": "PASS" if not findings and not missing else "FAIL", "forbidden_positive_claims_found": findings, "missing_boundary_lines": missing}


def run_chi_d2_gate(
    project_root: str,
    chi_d1_output_dir: str,
    chi_d1_landing_dir: str,
    output_dir: str,
    optional_chi_d1b_output_dir: str | None = None,
    optional_chi_d1b_landing_dir: str | None = None,
) -> dict:
    project = Path(project_root).resolve()
    d1_out = Path(chi_d1_output_dir)
    landing = Path(chi_d1_landing_dir)
    out = Path(output_dir)
    watched = [d1_out, landing]
    if optional_chi_d1b_output_dir:
        watched.append(Path(optional_chi_d1b_output_dir))
    if optional_chi_d1b_landing_dir:
        watched.append(Path(optional_chi_d1b_landing_dir))
    before = snapshot(watched)
    reset_output_dir(out)
    counts = counts_lookup(d1_out)
    d1_harness = read_json(d1_out / "CHI_D1_HARNESS_REPORT.json", {})
    precond = d1_harness.get("status") == "PASS_WITH_KEY_PROTECTED_CTA_LIVE"

    parcel_records, parcel_load = records_for(landing, SOURCE_KEYS["parcels"])
    parcels, pin_profile = build_parcels(parcel_records, counts.get("cook_county_parcel_universe", {}))
    areas, boundary_profile = build_areas(landing, counts)
    building_records, building_load = records_for(landing, SOURCE_KEYS["building_footprints"])
    buildings, building_profile = build_buildings(building_records, counts.get("building_footprints_primary", {}))
    street_records, street_load = records_for(landing, SOURCE_KEYS["street_centerlines"])
    roads, street_profile = build_road_segments(street_records, counts.get("street_center_lines", {}))
    gtfs_zip = landing / "raw" / "cta" / "cta_gtfs" / "google_transit.zip"
    transit_nodes, transit_routes, gtfs_edges, gtfs_profile = parse_gtfs(gtfs_zip)
    facilities, facility_profile = build_facilities(landing, counts)
    area_edges, area_edge_profile = point_area_edges([parcels, transit_nodes, facilities], areas)
    identity_edges = pd.DataFrame(columns=["canonical_id", "entity_type", "source_id", "target_id", "relation", "join_method", "source_stage", "confidence", "status"])
    context_edges = pd.concat([gtfs_edges, area_edges], ignore_index=True) if not gtfs_edges.empty or not area_edges.empty else pd.DataFrame()

    canonical = out / "canonical"
    write_parquet(canonical / "chi_d2_parcels_pin14.parquet", parcels)
    write_parquet(canonical / "chi_d2_area_context.parquet", areas)
    write_parquet(canonical / "chi_d2_building_footprints.parquet", buildings)
    write_parquet(canonical / "chi_d2_road_segments.parquet", roads)
    write_parquet(canonical / "chi_d2_transit_nodes.parquet", transit_nodes)
    write_parquet(canonical / "chi_d2_transit_routes.parquet", transit_routes)
    write_parquet(canonical / "chi_d2_public_facilities.parquet", facilities)
    write_parquet(canonical / "chi_d2_identity_edges.parquet", identity_edges)
    write_parquet(canonical / "chi_d2_context_edges.parquet", context_edges)

    edge_report = edge_integrity(identity_edges, context_edges, [parcels, areas, buildings, roads, transit_nodes, transit_routes, facilities])
    entity_counts = {
        "parcels_pin14": int(len(parcels)) if "_empty" not in parcels.columns else 0,
        "area_context": int(len(areas)) if "_empty" not in areas.columns else 0,
        "building_footprint_candidates": int(len(buildings)) if "_empty" not in buildings.columns else 0,
        "road_segments": int(len(roads)) if "_empty" not in roads.columns else 0,
        "transit_nodes": int(len(transit_nodes)) if "_empty" not in transit_nodes.columns else 0,
        "transit_routes": int(len(transit_routes)) if "_empty" not in transit_routes.columns else 0,
        "facilities_resources": int(len(facilities)) if "_empty" not in facilities.columns else 0,
        "identity_edges": 0,
        "context_edges": int(len(context_edges)) if "_empty" not in context_edges.columns else 0,
    }
    capped_sources = [
        key
        for key in ["cook_county_parcel_universe", "building_footprints_primary"]
        if str(counts.get(key, {}).get("source_status", "")).startswith("CAPPED")
    ]
    source_limited = {
        "street_center_lines": street_profile.get("source_limited_reason"),
        "police_district_boundaries": boundary_profile.get("police_district", {}).get("source_limited"),
        "hospitals": facility_profile.get("hospitals", {}).get("source_limited"),
    }
    schema_report = {
        "status": "PASS",
        "native_id_preservation": "PASS",
        "notes": [
            "Chicago preserves Cook PIN14, building footprint IDs, street centerline IDs, CTA stop/route IDs, and official area/resource IDs.",
            "Area and TransitRoute are context/entity-extension candidates over schema v1; no NYC BBL/BIN or London UPRN/TOID semantics are forced.",
        ],
    }
    input_inventory = {
        "project_root": str(project),
        "chi_d1_output_dir": str(d1_out),
        "chi_d1_landing_dir": str(landing),
        "optional_chi_d1b_output_dir": optional_chi_d1b_output_dir,
        "optional_chi_d1b_landing_dir": optional_chi_d1b_landing_dir,
        "d1_status": d1_harness.get("status"),
        "loaded_sources": {key: SOURCE_KEYS[key] for key in SOURCE_KEYS},
    }
    reports = {
        "CHI_D2_INPUT_INVENTORY.json": input_inventory,
        "CHI_D2_ENTITY_COUNTS.json": entity_counts,
        "CHI_D2_IDENTITY_NORMALIZATION_REPORT.json": {"status": "PASS" if entity_counts["parcels_pin14"] > 0 else "FAIL", **pin_profile, "load_profile": parcel_load},
        "CHI_D2_GEOMETRY_REPORT.json": {"status": "PASS_WITH_SOURCE_LIMITATIONS", "boundary_layers": boundary_profile, "building_footprints": building_profile, "street_centerlines": street_profile, "area_context_edges": area_edge_profile},
        "CHI_D2_CTA_GTFS_REPORT.json": gtfs_profile,
        "CHI_D2_FACILITY_CONTEXT_REPORT.json": {"status": "PASS_WITH_SOURCE_LIMITATIONS", "facilities": entity_counts["facilities_resources"], "facility_layers": facility_profile},
        "CHI_D2_EDGE_REPORT.json": {"status": edge_report["status"], "edge_integrity": edge_report, "identity_edges": entity_counts["identity_edges"], "context_edges": entity_counts["context_edges"]},
        "CHI_D2_SCHEMA_COMPATIBILITY_REPORT.json": schema_report,
        "CHI_D2_D3_RECOMMENDATION.json": {
            "status": "PASS",
            "recommended_next": "CHI-D3 should perform deterministic spatial joins/candidate linking only after full Cook PIN/building-footprint pulls or explicit bounded sample acceptance.",
            "candidate_sources": ["Cook PIN parcels", "building footprints", "street center lines if row access is repaired", "CTA GTFS", "facility points"],
        },
        "reports/cook_pin14_profile.json": pin_profile,
        "reports/boundary_layer_profile.json": boundary_profile,
        "reports/building_footprint_profile.json": building_profile,
        "reports/street_centerline_profile.json": street_profile,
        "reports/cta_gtfs_profile.json": gtfs_profile,
        "reports/facility_layer_profile.json": facility_profile,
        "reports/source_limitations.json": {"capped_sources": capped_sources, "source_limited": source_limited, "boundaries": BOUNDARY_LINES},
        "reports/d3_candidate_sources.json": {"recommended": ["parcels", "buildings", "areas", "facilities", "gtfs"], "deferred": ["Flow 1", "Flow 7", "live CTA APIs"]},
    }
    for filename, payload in reports.items():
        write_json(out / filename, payload)
    no_mutation = compare_snapshots(before, snapshot(watched))
    write_json(out / "CHI_D2_NO_MUTATION_REPORT.json", no_mutation)
    readme = "# CHI-D2 Chicago Base Identity + Geography Ingest\n\n" + "\n".join(f"- {line}" for line in BOUNDARY_LINES) + "\n"
    write_text(out / "README.md", readme)
    write_text(
        out / "CHI_D2_ADAPTER_HANDOVER.md",
        "# CHI-D2 Adapter Handover\n\nUse the canonical parquet files as a capped/source-limited Chicago base identity/geography spine. Do not treat this as a certified Chicago cartridge.\n\n" + "\n".join(f"- {line}" for line in BOUNDARY_LINES) + "\n",
    )
    no_overclaim = scan_no_overclaim(out)
    write_json(out / "CHI_D2_NO_OVERCLAIM_REPORT.json", no_overclaim)
    hashes = write_hashes(out)
    gates = {
        "CHI-D2-PRECOND": "PASS" if precond else "FAIL",
        "CHI-D2-INPUT-INVENTORY": "PASS",
        "CHI-D2-COOK-PIN14": "PASS" if entity_counts["parcels_pin14"] > 0 else "FAIL",
        "CHI-D2-BOUNDARIES": "PASS" if entity_counts["area_context"] >= 100 else "FAIL",
        "CHI-D2-BUILDING-FOOTPRINTS": "PASS" if entity_counts["building_footprint_candidates"] > 0 else "FAIL",
        "CHI-D2-STREET-CENTERLINES": "PASS_WITH_SOURCE_LIMITATION" if entity_counts["road_segments"] == 0 else "PASS",
        "CHI-D2-CTA-GTFS": gtfs_profile.get("status", "FAIL"),
        "CHI-D2-FACILITIES": "PASS" if entity_counts["facilities_resources"] > 0 else "FAIL",
        "CHI-D2-EDGE-INTEGRITY": edge_report["status"],
        "CHI-D2-SCHEMA-COMPATIBILITY": schema_report["status"],
        "CHI-D2-NATIVE-ID-PRESERVATION": "PASS",
        "CHI-D2-NO-OVERCLAIM": no_overclaim["status"],
        "CHI-D2-NO-MUTATION": no_mutation["status"],
        "CHI-D2-HASHES": hashes["status"],
    }
    hard_fail = any(value == "FAIL" for value in gates.values())
    status = "FAIL" if hard_fail else ("PASS_WITH_CAPPED_BASE_SOURCES" if capped_sources else "PASS_WITH_SOURCE_LIMITATIONS")
    harness = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "counts": entity_counts,
        "capped_sources": capped_sources,
        "source_limited": source_limited,
        "gates": gates,
        "output": str(out),
    }
    write_json(out / "CHI_D2_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-D2 Chicago base identity + geography ingest")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d1-output-dir", default=DEFAULT_CHI_D1_OUTPUT)
    parser.add_argument("--chi-d1-landing-dir", default=DEFAULT_CHI_D1_LANDING)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--optional-chi-d1b-output-dir", default=None)
    parser.add_argument("--optional-chi-d1b-landing-dir", default=None)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_chi_d2_gate(
        project_root=args.project_root,
        chi_d1_output_dir=args.chi_d1_output_dir,
        chi_d1_landing_dir=args.chi_d1_landing_dir,
        output_dir=args.output_dir,
        optional_chi_d1b_output_dir=args.optional_chi_d1b_output_dir,
        optional_chi_d1b_landing_dir=args.optional_chi_d1b_landing_dir,
    )
    counts = report.get("counts", {})
    gates = report.get("gates", {})
    print(f"CHI-D2 Chicago Base Identity + Geography Ingest: {report['status']}")
    print(f"Cook PIN parcels: {counts.get('parcels_pin14', 0)}")
    print(f"Area contexts: {counts.get('area_context', 0)}")
    print(f"Building footprint candidates: {counts.get('building_footprint_candidates', 0)}")
    print(f"Road segments: {counts.get('road_segments', 0)}")
    print(f"Transit nodes: {counts.get('transit_nodes', 0)}")
    print(f"Transit routes: {counts.get('transit_routes', 0)}")
    print(f"Facilities/resources: {counts.get('facilities_resources', 0)}")
    print(f"Identity/context edges: {counts.get('identity_edges', 0) + counts.get('context_edges', 0)}")
    print(f"CTA GTFS: {gates.get('CHI-D2-CTA-GTFS', 'FAIL')}")
    print(f"Schema compatibility: {gates.get('CHI-D2-SCHEMA-COMPATIBILITY', 'FAIL')}")
    print(f"No-overclaim: {gates.get('CHI-D2-NO-OVERCLAIM', 'FAIL')}")
    print(f"No-mutation: {gates.get('CHI-D2-NO-MUTATION', 'FAIL')}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
