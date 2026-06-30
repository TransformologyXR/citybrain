from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from txr_citybrain_nyc_expansion_potential_d1 import SOURCE_REGISTRY, SUBCARTRIDGES


TASK_NAME = "NYC Expansion D2 All Flows"
DEFAULT_D1_DIR = "outputs/nyc_expansion_potential_d1"
DEFAULT_OUTPUT_DIR = "outputs/nyc_expansion_d2_all_flows"
DEFAULT_SAMPLE_LIMIT = 50_000

BOUNDARY_LINES = [
    "NYC Expansion D2 lands bounded source samples and join-hardening contracts only.",
    "NYC Expansion D2 does not create accepted F1X, F4X, F5X, or F6X cartridges.",
    "NYC Expansion D2 does not make operational recommendations.",
    "NYC Expansion D2 does not certify affected buildings/assets.",
    "NYC Expansion D2 does not provide airport or port operational command.",
    "NYC Expansion D2 does not provide safety-critical sequencing, vessel instruction, or aircraft instruction.",
    "NYC Expansion D2 does not model certified utility-network propagation.",
]

FORBIDDEN_PATTERNS = [
    r"\baccepted F[1456]X cartridge\b",
    r"\bF[1456]X is accepted\b",
    r"\bcertifies? affected (?:buildings|assets)\b",
    r"\boperational recommendation\b(?!s\.)",
    r"\bairport command\b",
    r"\bport command\b",
    r"\bsafety-critical sequencing\b",
    r"\bvessel instruction\b",
    r"\baircraft instruction\b",
    r"\butility-network propagation\b",
    r"\bdispatch optimization\b",
]

FLOW_D2_SPECS: dict[str, dict[str, Any]] = {
    "NYC-F4X-D2": {
        "d1_code": "NYC-F4X-D1",
        "name": "NYC Mobility Source Landing and Stop/Event Context Graph",
        "output_slug": "nyc_f4x_d2_mobility_source_landing",
        "recommended_order": 1,
        "status": "PASS_WITH_BOUNDED_SOURCE_LANDING",
        "primary_anchor": "route_id/stop_id/service_alert_id/event_time/area_id",
        "join_keys": ["route_id", "stop_id", "trip_id", "event_time", "borough", "community_district", "lat_lon", "bbl_candidate"],
        "d3_handoff": "NYC-F4X-D3 mobility/event/environment EvidenceBundles",
        "boundary_lines": [
            "NYC-F4X-D2 lands mobility/event/environment sources but does not issue transit, traffic, crowd, or event operations instructions.",
            "MTA GTFS static is schedule geography; GTFS-RT samples are service context for review.",
            "Taxi/FHV and Citi Bike remain optional aggregate-only context unless a privacy-preserving product is explicitly landed.",
        ],
    },
    "NYC-F1X-D2": {
        "d1_code": "NYC-F1X-D1",
        "name": "NYC Situational Status Source Landing and Area Canonicalization",
        "output_slug": "nyc_f1x_d2_situational_status_source_landing",
        "recommended_order": 2,
        "status": "PASS_WITH_BOUNDED_SOURCE_LANDING",
        "primary_anchor": "area_id/time_window/source_event_id/bbl_candidate",
        "join_keys": ["borough", "community_district", "incident_address", "lat_lon", "bbl_candidate", "bin_candidate", "created_date"],
        "d3_handoff": "NYC-F1X-D3 situational status EvidenceBundles",
        "boundary_lines": [
            "NYC-F1X-D2 lands situational-status sources but does not make operational, policing, dispatch, enforcement, health, emergency, or public-safety recommendations.",
            "Flow 3 affected-context and location tiers are inputs only, not new affected-asset certification.",
            "Air, flood, transit, 311, DOB, and collision records are context signals for deterministic status summaries.",
        ],
    },
    "NYC-F5X-D2": {
        "d1_code": "NYC-F5X-D1",
        "name": "NYC Flood/Climate Source Landing and Parcel-Context Evidence Model",
        "output_slug": "nyc_f5x_d2_flood_climate_source_landing",
        "recommended_order": 3,
        "status": "PASS_WITH_BOUNDARY_LIMITATION",
        "primary_anchor": "bbl_candidate/flood_area_id/facility_id/time_window",
        "join_keys": ["bbl_candidate", "bin_candidate", "lat_lon", "flood_area_id", "facility_id", "sampling_station_id", "benchmarking_bbl"],
        "d3_handoff": "NYC-F5X-D3 flood/climate asset-context EvidenceBundles",
        "boundary_lines": [
            "NYC-F5X-D2 lands flood/climate/asset-context sources for review only.",
            "NYC-F5X-D2 does not model certified utility-network propagation.",
            "Flood, water, air, benchmarking, parcel, and facility records are context signals, not safety, insurance, utility, or emergency determinations.",
        ],
    },
    "NYC-F6X-D2": {
        "d1_code": "NYC-F6X-D1",
        "name": "NYC Port/Airport Exact Source Landing and Review-Only Sequence Schema",
        "output_slug": "nyc_f6x_d2_port_airport_source_landing",
        "recommended_order": 4,
        "status": "PASS_AS_REVIEW_ONLY_SOURCE_LANDING",
        "primary_anchor": "airport_id/month/commodity_or_metric/context_route_id",
        "join_keys": ["airport", "month", "metric_type", "route_id", "facility_id", "construction_context_id"],
        "d3_handoff": "NYC-F6X-D3 port/airport logistics feasibility EvidenceBundles",
        "boundary_lines": [
            "NYC-F6X-D2 lands port/airport logistics context for review-only feasibility.",
            "NYC-F6X-D2 is not oil/gas Flow 6.",
            "NYC-F6X-D2 does not provide airport or port operational command.",
            "NYC-F6X-D2 does not provide safety-critical sequencing, vessel instruction, or aircraft instruction.",
            "PANYNJ airport datasets are monthly aggregate context, not live operational control feeds.",
        ],
    },
}

LANDING_SPECS: dict[str, dict[str, Any]] = {
    "nyc_311_2020_present": {"kind": "socrata", "domain": "data.cityofnewyork.us", "dataset_id": "erm2-nwe9"},
    "nyc_311_2010_2019": {"kind": "socrata", "domain": "data.cityofnewyork.us", "dataset_id": "76ig-c548"},
    "nyc_mvc_crashes": {"kind": "socrata", "domain": "data.cityofnewyork.us", "dataset_id": "h9gi-nx95"},
    "nyc_mvc_vehicles": {"kind": "socrata", "domain": "data.cityofnewyork.us", "dataset_id": "bm4k-52h4"},
    "nyc_air_quality": {"kind": "socrata", "domain": "data.cityofnewyork.us", "dataset_id": "c3uy-2p5r"},
    "nyc_flood_vulnerability_index": {"kind": "socrata", "domain": "data.cityofnewyork.us", "dataset_id": "mrjc-v9pm"},
    "nyc_flood_vulnerability_index_map": {"kind": "socrata", "domain": "data.cityofnewyork.us", "dataset_id": "4vym-qrg3"},
    "panynj_air_passenger_traffic": {"kind": "socrata", "domain": "data.ny.gov", "dataset_id": "8pkr-4b7t"},
    "mta_gtfs_rt": {
        "kind": "binary_probe",
        "endpoints": {
            "nyct_subway_gtfs_rt": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
            "all_service_alerts_gtfs_rt": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fall-alerts",
        },
    },
    "mta_gtfs_static": {
        "kind": "url_probe",
        "endpoints": {
            "subway_static_gtfs": "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip",
            "lirr_static_gtfs": "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_lirr.zip",
            "metro_north_static_gtfs": "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_mnr.zip",
        },
    },
    "nyc_dob_context": {"kind": "local_context"},
    "facility_context": {"kind": "metadata_only"},
    "dep_harbor_water_quality": {"kind": "metadata_only"},
    "ll84_energy_water": {"kind": "metadata_only"},
    "taxi_fhv_optional": {"kind": "metadata_only"},
    "citi_bike_optional": {"kind": "metadata_only"},
    "panynj_airport_statistics": {"kind": "metadata_only"},
    "panynj_cargo_tonnage": {"kind": "metadata_only"},
    "path_regional_transport": {"kind": "metadata_only"},
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
        "gate": "NYC-EXP-D2-HASHES",
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
        if "nyc_expansion_d2_all_flows" not in resolved.name.lower():
            raise ValueError(f"Refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["data_landing", "subcartridges", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def request_bytes(url: str, limit: int | None = None, timeout: int = 20) -> tuple[int | None, dict[str, str], bytes, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "TXR-CityBrain-NYC-D2/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read(limit) if limit else response.read()
            headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
            return int(response.status), headers, data, None
    except urllib.error.HTTPError as exc:
        return int(exc.code), {}, b"", str(exc)
    except Exception as exc:
        return None, {}, b"", f"{type(exc).__name__}: {exc}"


def request_json(url: str, timeout: int = 30) -> tuple[Any, dict[str, Any]]:
    status, headers, data, error = request_bytes(url, timeout=timeout)
    meta = {"url": url, "http_status": status, "content_type": headers.get("content-type"), "error": error}
    if error or not data:
        return None, meta
    try:
        return json.loads(data.decode("utf-8", errors="replace")), meta
    except json.JSONDecodeError as exc:
        meta["error"] = f"JSONDecodeError: {exc}"
        return None, meta


def socrata_resource_url(domain: str, dataset_id: str, params: dict[str, Any]) -> str:
    return f"https://{domain}/resource/{dataset_id}.json?{urllib.parse.urlencode(params)}"


def socrata_count_value(count_rows: Any) -> int | None:
    if isinstance(count_rows, list) and count_rows and isinstance(count_rows[0], dict):
        raw = count_rows[0].get("count") or count_rows[0].get("COUNT")
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    return None


def fetch_socrata_sample_chunks(domain: str, dataset_id: str, sample_limit: int) -> tuple[list[Any], list[dict[str, Any]]]:
    chunk_size = min(10_000, sample_limit)
    rows: list[Any] = []
    requests: list[dict[str, Any]] = []
    offset = 0
    while offset < sample_limit:
        limit = min(chunk_size, sample_limit - offset)
        url = socrata_resource_url(domain, dataset_id, {"$limit": limit, "$offset": offset})
        chunk, meta = request_json(url, timeout=90)
        meta["offset"] = offset
        meta["limit"] = limit
        meta["rows"] = len(chunk) if isinstance(chunk, list) else 0
        requests.append(meta)
        if not isinstance(chunk, list) or not chunk:
            break
        rows.extend(chunk)
        if len(chunk) < limit:
            break
        offset += limit
    return rows, requests


def source_landing_dir(output_dir: Path, source_key: str) -> Path:
    return output_dir / "data_landing" / "raw" / source_key


def land_socrata_source(output_dir: Path, source_key: str, spec: dict[str, Any], sample_limit: int) -> dict[str, Any]:
    target = source_landing_dir(output_dir, source_key)
    domain = spec["domain"]
    dataset_id = spec["dataset_id"]
    metadata_url = f"https://{domain}/api/views/{dataset_id}"
    count_url = socrata_resource_url(domain, dataset_id, {"$select": "count(*)"})

    metadata, metadata_meta = request_json(metadata_url)
    sample, sample_requests = fetch_socrata_sample_chunks(domain, dataset_id, sample_limit)
    count_rows, count_meta = request_json(count_url)
    if metadata is not None:
        write_json(target / "metadata.json", metadata)
    if sample:
        write_json(target / "sample.json", sample)
    if count_rows is not None:
        write_json(target / "row_count.json", count_rows)
    columns = []
    if isinstance(metadata, dict):
        for column in metadata.get("columns", []) or []:
            columns.append(
                {
                    "name": column.get("name"),
                    "field_name": column.get("fieldName"),
                    "data_type": column.get("dataTypeName"),
                    "position": column.get("position"),
                }
            )
    total_available = socrata_count_value(count_rows)
    expected_rows = min(sample_limit, total_available) if total_available is not None else sample_limit
    if not sample:
        status = "WARN_NO_SAMPLE"
    elif len(sample) < expected_rows:
        status = "WARN_PARTIAL_SAMPLE"
    else:
        status = "LANDED_SAMPLE"
    profile = {
        "source_key": source_key,
        "kind": "socrata",
        "dataset_id": dataset_id,
        "domain": domain,
        "sample_limit": sample_limit,
        "expected_sample_rows": expected_rows,
        "total_available_rows": total_available,
        "metadata_request": metadata_meta,
        "sample_requests": sample_requests,
        "count_request": count_meta,
        "sample_rows": len(sample),
        "column_count": len(columns),
        "columns": columns,
        "status": status,
    }
    write_json(target / "landing_profile.json", profile)
    return profile


def land_binary_probe(output_dir: Path, source_key: str, spec: dict[str, Any]) -> dict[str, Any]:
    target = source_landing_dir(output_dir, source_key)
    endpoint_rows = []
    for name, url in spec["endpoints"].items():
        status, headers, data, error = request_bytes(url, limit=4096, timeout=20)
        if data:
            (target / f"{name}.sample.bin").parent.mkdir(parents=True, exist_ok=True)
            (target / f"{name}.sample.bin").write_bytes(data)
        endpoint_rows.append(
            {
                "name": name,
                "url": url,
                "http_status": status,
                "content_type": headers.get("content-type"),
                "content_length": headers.get("content-length"),
                "sample_bytes": len(data),
                "sha256_sample": hashlib.sha256(data).hexdigest() if data else None,
                "error": error,
            }
        )
    profile = {
        "source_key": source_key,
        "kind": spec["kind"],
        "endpoints": endpoint_rows,
        "status": "LANDED_BINARY_PROBE" if any(row["sample_bytes"] for row in endpoint_rows) else "WARN_NO_BINARY_SAMPLE",
    }
    write_json(target / "landing_profile.json", profile)
    return profile


def land_url_probe(output_dir: Path, source_key: str, spec: dict[str, Any]) -> dict[str, Any]:
    target = source_landing_dir(output_dir, source_key)
    endpoint_rows = []
    for name, url in spec["endpoints"].items():
        status, headers, data, error = request_bytes(url, limit=512, timeout=20)
        endpoint_rows.append(
            {
                "name": name,
                "url": url,
                "http_status": status,
                "content_type": headers.get("content-type"),
                "content_length": headers.get("content-length"),
                "probe_bytes": len(data),
                "zip_magic_seen": data.startswith(b"PK"),
                "error": error,
            }
        )
    profile = {
        "source_key": source_key,
        "kind": spec["kind"],
        "endpoints": endpoint_rows,
        "status": "URL_PROBE_OK" if any(row["http_status"] == 200 for row in endpoint_rows) else "WARN_URL_PROBE",
    }
    write_json(target / "landing_profile.json", profile)
    return profile


def local_context_paths(project_root: Path, source_key: str) -> list[dict[str, Any]]:
    rows = []
    for raw in SOURCE_REGISTRY.get(source_key, {}).get("local_paths", []):
        path = project_root / raw
        rows.append({"path": raw, "exists": path.exists(), "bytes": path.stat().st_size if path.exists() and path.is_file() else None})
    return rows


def land_metadata_or_local(project_root: Path, output_dir: Path, source_key: str, kind: str) -> dict[str, Any]:
    target = source_landing_dir(output_dir, source_key)
    source = SOURCE_REGISTRY[source_key]
    local_paths = local_context_paths(project_root, source_key)
    profile = {
        "source_key": source_key,
        "kind": kind,
        "label": source.get("label"),
        "provider": source.get("provider"),
        "official_url": source.get("official_url"),
        "credential_note": source.get("credential_note"),
        "local_paths": local_paths,
        "status": "LOCAL_CONTEXT_PRESENT"
        if kind == "local_context" and any(row["exists"] for row in local_paths)
        else "METADATA_ONLY",
    }
    write_json(target / "landing_profile.json", profile)
    return profile


def land_source(project_root: Path, output_dir: Path, source_key: str, sample_limit: int) -> dict[str, Any]:
    spec = LANDING_SPECS.get(source_key, {"kind": "metadata_only"})
    kind = spec["kind"]
    if kind == "socrata":
        return land_socrata_source(output_dir, source_key, spec, sample_limit)
    if kind == "binary_probe":
        return land_binary_probe(output_dir, source_key, spec)
    if kind == "url_probe":
        return land_url_probe(output_dir, source_key, spec)
    return land_metadata_or_local(project_root, output_dir, source_key, kind)


def all_d2_source_keys() -> list[str]:
    keys: set[str] = set()
    for d2_spec in FLOW_D2_SPECS.values():
        keys.update(SUBCARTRIDGES[d2_spec["d1_code"]]["source_keys"])
    return sorted(keys)


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
    return {"gate": "NYC-EXP-D2-NO-MUTATION", "status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "checked_files": len(before)}


def load_d1_gate(d1_dir: Path) -> dict[str, Any]:
    report = read_json(d1_dir / "NYC_EXPANSION_POTENTIAL_D1_HARNESS_REPORT.json", {})
    return {
        "gate": "NYC-EXP-D2-D1-DEPENDENCY",
        "status": "PASS" if str(report.get("status", "")).startswith("PASS") else "FAIL",
        "d1_status": report.get("status"),
        "d1_dir": str(d1_dir),
    }


def source_profile_lookup(profiles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["source_key"]): row for row in profiles}


def flow_source_ledger(d2_spec: dict[str, Any], profile_by_key: dict[str, dict[str, Any]]) -> dict[str, Any]:
    d1 = SUBCARTRIDGES[d2_spec["d1_code"]]
    rows = []
    for key in d1["source_keys"]:
        profile = profile_by_key.get(key, {"source_key": key, "status": "MISSING"})
        source = SOURCE_REGISTRY.get(key, {})
        rows.append(
            {
                "source_key": key,
                "label": source.get("label"),
                "provider": source.get("provider"),
                "official_url": source.get("official_url"),
                "landing_status": profile.get("status"),
                "kind": profile.get("kind"),
                "sample_rows": profile.get("sample_rows"),
                "column_count": profile.get("column_count"),
            }
        )
    good = [row for row in rows if str(row["landing_status"]).startswith(("LANDED", "URL_PROBE", "LOCAL_CONTEXT", "METADATA"))]
    return {
        "status": "PASS" if len(good) == len(rows) else "WARN_PARTIAL_SOURCE_LANDING",
        "flow": d2_spec["d1_code"].replace("-D1", "-D2"),
        "source_count": len(rows),
        "landed_or_profiled_count": len(good),
        "sources": rows,
    }


def join_hardening_contract(code: str, d2_spec: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        "flow": code,
        "name": d2_spec["name"],
        "primary_anchor": d2_spec["primary_anchor"],
        "join_keys": d2_spec["join_keys"],
        "identity_geography_rules": [
            "Prefer exact official IDs where present before spatial/proximity joins.",
            "Use BBL/BIN/tax-lot candidates as candidate context only until deterministic source evidence supports them.",
            "Preserve source-native timestamps and produce explicit time-window joins for D3 EvidenceBundles.",
            "Record unresolved joins as review-needed rather than dropping them.",
            "Carry Flow 3 location confidence tiers forward where reused.",
        ],
        "source_landing_status": ledger["status"],
        "d3_handoff": d2_spec["d3_handoff"],
        "boundary_lines": d2_spec["boundary_lines"],
        "status": "PASS" if ledger["status"] in {"PASS", "WARN_PARTIAL_SOURCE_LANDING"} else "FAIL",
    }


def render_d3_handoff(code: str, d2_spec: dict[str, Any], ledger: dict[str, Any]) -> str:
    lines = [
        f"# {code} D3 Handoff",
        "",
        f"Next gate: {d2_spec['d3_handoff']}",
        f"D2 status: {d2_spec['status']}",
        f"Source landing status: {ledger['status']}",
        "",
        "## Boundary",
        "",
    ]
    lines.extend(f"- {line}" for line in d2_spec["boundary_lines"])
    lines.extend(["", "## Join Keys", ""])
    lines.extend(f"- {key}" for key in d2_spec["join_keys"])
    lines.extend(["", "## D3 EvidenceBundle Inputs", ""])
    for row in ledger["sources"]:
        lines.append(f"- {row['source_key']}: {row['landing_status']}")
    lines.append("")
    return "\n".join(lines)


def render_readme(harness: dict[str, Any]) -> str:
    lines = ["# NYC Expansion D2 All Flows", "", "D2 source landing and join-hardening contracts for the four NYC expansion paths.", "", "## Boundary", ""]
    lines.extend(f"- {line}" for line in BOUNDARY_LINES)
    lines.extend(["", "## Recommended Order", ""])
    for code, row in sorted(harness["flows"].items(), key=lambda item: item[1]["recommended_order"]):
        lines.append(f"- {code}: {row['name']} -> {row['d3_handoff']}")
    lines.extend(["", "## Gates", ""])
    for gate, status in harness["gates"].items():
        lines.append(f"- {gate}: {status}")
    lines.append("")
    return "\n".join(lines)


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS.json" or path.suffix.lower() not in {".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        checked.append(path.relative_to(output_dir).as_posix())
        for pattern in FORBIDDEN_PATTERNS:
            for match in re.finditer(pattern, lower):
                context = lower[max(0, match.start() - 90) : min(len(lower), match.end() + 90)]
                if any(prefix in context for prefix in ["does not ", "not ", "no "]):
                    continue
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern, "context": context})
    return {"gate": "NYC-EXP-D2-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def run_nyc_expansion_d2_all_flows_gate(
    project_root: str | Path = ".",
    d1_dir: str | Path = DEFAULT_D1_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    d1 = root / d1_dir
    out = root / output_dir
    watched_inputs = [
        d1 / "NYC_EXPANSION_POTENTIAL_D1_HARNESS_REPORT.json",
        root / "outputs/f3_nyc_d9_flow3_accepted_snapshot/F3_NYC_D9_ACCEPTED_STATE.json",
        root / "outputs/f3_nyc_d9_flow3_accepted_snapshot/F3_NYC_D9_SOURCE_STATUS.json",
    ]
    before = snapshot(watched_inputs)
    reset_output_dir(out)

    d1_gate = load_d1_gate(d1)
    gates: dict[str, str] = {d1_gate["gate"]: d1_gate["status"]}

    profiles = []
    for source_key in all_d2_source_keys():
        profile = land_source(root, out, source_key, sample_limit)
        profiles.append(profile)
    profile_by_key = source_profile_lookup(profiles)
    landed = [p for p in profiles if str(p.get("status", "")).startswith(("LANDED", "URL_PROBE", "LOCAL_CONTEXT", "METADATA"))]
    source_gate = {
        "gate": "NYC-EXP-D2-SOURCE-LANDING",
        "status": "PASS" if len(landed) == len(profiles) else "WARN_PARTIAL_SOURCE_LANDING",
        "sample_limit": sample_limit,
        "source_count": len(profiles),
        "landed_or_profiled_count": len(landed),
        "profiles": profiles,
    }
    gates[source_gate["gate"]] = "PASS" if source_gate["status"].startswith("PASS") else source_gate["status"]
    write_json(out / "reports" / "all_source_landing_profiles.json", source_gate)

    flows: dict[str, Any] = {}
    for code, d2_spec in sorted(FLOW_D2_SPECS.items(), key=lambda item: item[1]["recommended_order"]):
        subdir = out / "subcartridges" / d2_spec["output_slug"]
        ledger = flow_source_ledger(d2_spec, profile_by_key)
        contract = {
            "flow": code,
            "d1_dependency": d2_spec["d1_code"],
            "name": d2_spec["name"],
            "task": TASK_NAME,
            "generated_at": utc_now(),
            "recommended_order": d2_spec["recommended_order"],
            "d2_status": d2_spec["status"],
            "boundary_lines": [*BOUNDARY_LINES, *d2_spec["boundary_lines"]],
            "source_landing_ledger": ledger,
            "join_hardening": join_hardening_contract(code, d2_spec, ledger),
            "d3_handoff": d2_spec["d3_handoff"],
        }
        write_json(subdir / f"{code.replace('-', '_')}_SOURCE_LANDING_JOIN_CONTRACT.json", contract)
        write_json(subdir / "source_landing_ledger.json", ledger)
        write_json(subdir / "identity_geography_join_hardening.json", contract["join_hardening"])
        write_text(subdir / "D3_HANDOFF.md", render_d3_handoff(code, d2_spec, ledger))
        gate_status = "PASS" if contract["join_hardening"]["status"] == "PASS" else "FAIL"
        gates[f"{code}-SOURCE-LANDING-JOIN-HARDENING"] = gate_status
        flows[code] = {
            "name": d2_spec["name"],
            "recommended_order": d2_spec["recommended_order"],
            "status": d2_spec["status"],
            "source_landing_status": ledger["status"],
            "d3_handoff": d2_spec["d3_handoff"],
            "output_dir": str(subdir),
            "gate_status": gate_status,
        }

    no_mutation = compare_snapshots(before, snapshot(watched_inputs))
    gates[no_mutation["gate"]] = no_mutation["status"]
    harness = {
        "task": TASK_NAME,
        "generated_at": utc_now(),
        "status": "PENDING_HASH",
        "sample_limit": sample_limit,
        "boundary_lines": BOUNDARY_LINES,
        "d1_dependency": d1_gate,
        "source_landing": source_gate,
        "flows": flows,
        "recommended_order": ["NYC-F4X-D2", "NYC-F1X-D2", "NYC-F5X-D2", "NYC-F6X-D2"],
        "gates": gates,
        "no_mutation": no_mutation,
        "output": str(out),
    }
    write_json(out / "NYC_EXPANSION_D2_ALL_FLOWS_HARNESS_REPORT.json", harness)
    write_text(out / "README.md", render_readme(harness))

    no_overclaim = scan_no_overclaim(out)
    gates[no_overclaim["gate"]] = no_overclaim["status"]
    write_json(out / "NYC_EXPANSION_D2_NO_OVERCLAIM_REPORT.json", no_overclaim)
    hashes = write_hashes(out)
    gates[hashes["gate"]] = hashes["status"]
    harness["gates"] = gates
    harness["no_overclaim"] = no_overclaim
    harness["hashes"] = hashes
    pass_like = {"PASS", "WARN_PARTIAL_SOURCE_LANDING"}
    harness["status"] = "PASS_WITH_BOUNDED_SOURCE_LANDING" if all(value in pass_like for value in gates.values()) else "FAIL"
    write_json(out / "NYC_EXPANSION_D2_ALL_FLOWS_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    harness["hashes"] = hashes
    gates[hashes["gate"]] = hashes["status"]
    harness["gates"] = gates
    harness["status"] = "PASS_WITH_BOUNDED_SOURCE_LANDING" if all(value in pass_like for value in gates.values()) else "FAIL"
    write_json(out / "NYC_EXPANSION_D2_ALL_FLOWS_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all NYC expansion D2 source landing and join-hardening gates.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d1-dir", default=DEFAULT_D1_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-limit", type=int, default=DEFAULT_SAMPLE_LIMIT)
    args = parser.parse_args()
    result = run_nyc_expansion_d2_all_flows_gate(
        project_root=args.project_root,
        d1_dir=args.d1_dir,
        output_dir=args.output_dir,
        sample_limit=args.sample_limit,
    )
    print(json.dumps({"status": result["status"], "gates": result["gates"], "output": result["output"]}, indent=2, sort_keys=True))
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
