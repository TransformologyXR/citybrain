#!/usr/bin/env python3
"""Build SourceRegistry v1 from existing CityBrain source manifests.

The runner is intentionally read-only with respect to upstream artifacts. It
scans source-like manifest JSON/JSONL files and writes a normalized registry
under its own output root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_citybrain_track4_source_registry_v1"

FINAL_STATUS = "PASS_MAIN_CITYBRAIN_TRACK4_SOURCE_REGISTRY_V1_WITH_LIMITATIONS"
MAX_CANDIDATE_BYTES = 12_000_000

SCAN_ROOTS = [
    ROOT / "outputs",
    ROOT / "publications",
    ROOT / "manifests",
    ROOT / "packages" / "fixtures",
]

EXCLUDED_PATH_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "corpus_raw",
    "data",
    "data_landing",
    "inputs",
    "tmp",
}

EXCLUDED_NAME_TOKENS = {
    "hash_manifest",
    "sha256sums",
    "secret_audit",
    "no_mutation_audit",
    "no_action_audit",
    "no_fact_invention_audit",
    "claim_boundary_audit",
}

SOURCE_FILE_TOKENS = {
    "source",
    "sources",
    "registry",
    "ledger",
    "inventory",
    "manifest",
    "catalog",
    "matrix",
}

SOURCE_LIST_KEYS = {
    "sources",
    "source_registry",
    "source_ledger",
    "source_records",
    "records",
    "entries",
    "source_refs",
    "source_ref",
    "datasets",
    "resources",
}

REQUIRED_SOURCE_FIELDS = [
    "source_id",
    "city",
    "domain",
    "source_class",
    "freshness",
    "coverage",
    "license_access_status",
    "schema_status",
    "geometry_status",
    "time_coverage",
    "known_limitations",
    "consuming_flows",
]

SOURCE_SIGNAL_KEYS = {
    "source_id",
    "source_key",
    "key",
    "dataset_id",
    "resource_id",
    "source_url",
    "human_url",
    "api_url",
    "url",
    "source_class",
    "source_type",
    "columns",
    "column_count",
    "schema_fingerprint",
    "flows",
    "flow",
    "geo_fields",
    "date_fields",
    "row_count",
    "source_status",
    "scan_status",
    "official_title",
    "metadata_name",
    "source_record_ref",
}

GEOMETRY_TOKENS = {
    "geometry",
    "geom",
    "the_geom",
    "location",
    "point",
    "multipolygon",
    "polygon",
    "latitude",
    "longitude",
    "lat",
    "lon",
    "lng",
    "shape",
    "x_coordinate",
    "y_coordinate",
}

TIME_TOKENS = {
    "date",
    "time",
    "timestamp",
    "created",
    "closed",
    "updated",
    "start",
    "end",
    "year",
    "month",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_id(value: Any, length: int = 12) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256_bytes(payload.encode("utf-8"))[:length]


def safe_slug(value: Any, fallback: str = "unknown") -> str:
    text = str(value or fallback).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:96] or fallback


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def parse_datetime(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        # Socrata timestamps in the repo are usually epoch seconds.
        if value > 10_000_000_000:
            value = value / 1000
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        except (OSError, OverflowError, ValueError):
            return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def age_days(iso_value: str | None) -> int | None:
    if not iso_value:
        return None
    text = iso_value[:-1] + "+00:00" if iso_value.endswith("Z") else iso_value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    now = datetime.now(timezone.utc)
    return max(0, (now - parsed.astimezone(timezone.utc)).days)


def first_present(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def listify(value: Any) -> list[Any]:
    if value in (None, "", {}):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def flatten_strings(value: Any, limit: int = 12) -> list[str]:
    values: list[str] = []
    for item in listify(value):
        if isinstance(item, dict):
            text = first_present(item, ["field_name", "fieldName", "name", "id", "key", "title", "url"])
            if text:
                values.append(str(text))
        else:
            values.append(str(item))
        if len(values) >= limit:
            break
    return sorted({item for item in values if item})


def path_is_excluded(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    if lowered_parts & EXCLUDED_PATH_PARTS:
        return True
    lowered = path.as_posix().lower()
    return "main_citybrain_track4_source_registry_v1" in lowered or "main_citybrain_track5_data_quality_maturity_dashboard_r1" in lowered


def is_candidate_file(path: Path) -> bool:
    if path.suffix.lower() not in {".json", ".jsonl"}:
        return False
    if path_is_excluded(path):
        return False
    name = path.name.lower()
    if any(token in name for token in EXCLUDED_NAME_TOKENS):
        return False
    if not any(token in name for token in SOURCE_FILE_TOKENS):
        return False
    return "source" in path.as_posix().lower() or any(token in name for token in {"inventory", "manifest", "ledger", "catalog", "registry", "matrix"})


def discover_candidate_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and is_candidate_file(path):
                files.append(path)
    return files


def load_candidate_payload(path: Path) -> tuple[Any | None, str | None]:
    try:
        if path.stat().st_size > MAX_CANDIDATE_BYTES:
            return None, f"skipped_too_large:{path.stat().st_size}"
        if path.suffix.lower() == ".jsonl":
            rows = []
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
            return rows, None
        return json.loads(path.read_text(encoding="utf-8")), None
    except (UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
        return None, f"parse_error:{exc.__class__.__name__}"


def looks_like_source(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    keys = {str(key) for key in row}
    lower = {key.lower() for key in keys}
    if not (lower & SOURCE_SIGNAL_KEYS):
        return False
    if {"path", "sha256", "bytes"} <= lower and len(lower) <= 6:
        return False
    return True


def iter_source_rows(payload: Any, path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(row: dict[str, Any], container: str) -> None:
        if looks_like_source(row):
            source = dict(row)
            source["_source_registry_container"] = container
            rows.append(source)

    if looks_like_source(payload):
        add(payload, "top_level")

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                add(item, "top_level_list")

    if not isinstance(payload, dict):
        return rows

    for key, value in payload.items():
        key_lower = str(key).lower()
        if isinstance(value, list) and (key_lower in SOURCE_LIST_KEYS or "source" in key_lower):
            for item in value:
                if isinstance(item, dict):
                    add(item, key_lower)
        elif isinstance(value, dict) and "source" in key_lower:
            add(value, key_lower)

    return rows


def infer_city(row: dict[str, Any], path: Path) -> str:
    explicit = first_present(row, ["city", "city_code", "city_id", "city_name"])
    if explicit:
        text = str(explicit).lower()
    else:
        text = f"{path.as_posix()} {json.dumps({k: row.get(k) for k in ['key', 'source_key', 'name', 'domain', 'host'] if k in row}, ensure_ascii=True)}".lower()
    patterns = [
        ("nyc", ["nyc", "new_york", "newyork", "data.cityofnewyork", "data.ny.gov"]),
        ("chicago", ["chi_", "chicago", "data.cityofchicago"]),
        ("london", ["lon_", "london", "tfl", "havering"]),
        ("barcelona", ["barc", "bcn", "barcelona"]),
        ("helsinki", ["helsinki", "kalasatama"]),
        ("singapore", ["singapore", "sg_"]),
        ("dubai", ["dubai"]),
        ("multi_city", ["fourcity", "cross_city", "crosscity", "multi_city"]),
    ]
    for city, needles in patterns:
        if any(needle in text for needle in needles):
            return city
    alias = safe_slug(explicit, "unknown") if explicit else "unknown"
    return {
        "chi": "chicago",
        "lon": "london",
        "barc": "barcelona",
        "bcn": "barcelona",
        "sg": "singapore",
    }.get(alias, alias)


def infer_domain(row: dict[str, Any], path: Path) -> str:
    seed_parts = [
        str(first_present(row, ["domain", "category", "family", "source_type", "use", "purpose", "name", "official_title"]) or ""),
        path.as_posix(),
    ]
    text = " ".join(seed_parts).lower()
    domain_map = [
        ("planning", ["planning", "permit", "zoning", "land use", "land_use", "dob", "building"]),
        ("mobility", ["mobility", "transit", "traffic", "gtfs", "mta", "cta", "road", "street", "taxi", "vehicle", "collision"]),
        ("utilities", ["utility", "utilities", "ev", "charging", "water", "power", "energy", "sewer"]),
        ("environment", ["environment", "air", "flood", "climate", "heat", "sensor"]),
        ("public_safety_events", ["incident", "event", "fire", "ems", "police", "complaint", "311", "dispatch"]),
        ("perception_media", ["camera", "video", "media", "perception", "deepstream", "vss", "cctv"]),
        ("spatial_base", ["boundary", "boundaries", "parcel", "cadastre", "address", "geometry", "3d", "i3s", "tiles"]),
        ("health", ["health", "restaurant", "inspection", "dohmh"]),
        ("logistics", ["port", "airport", "cargo", "logistics"]),
        ("governance", ["governance", "rbac", "authority", "check"]),
    ]
    for domain, needles in domain_map:
        if any(needle in text for needle in needles):
            return domain
    explicit = first_present(row, ["category", "family"])
    return safe_slug(explicit, "general")


def infer_source_class(row: dict[str, Any], path: Path) -> str:
    explicit = first_present(row, ["source_class", "class"])
    if explicit:
        return safe_slug(explicit, "unknown_or_unclassified")
    text = (
        f"{path.as_posix()} {row.get('source_type', '')} {row.get('boundary', '')} "
        f"{row.get('name', '')} {row.get('use', '')} {row.get('url', '')} "
        f"{row.get('source_url', '')} {row.get('human_url', '')} {row.get('license', '')} "
        f"{row.get('attribution', '')} {row.get('publisher', '')}"
    ).lower()
    if any(token in text for token in ["vss", "narrative", "model_generated"]):
        return "model_generated_narrative_not_fact_source"
    if any(token in text for token in ["camera", "deepstream", "sensor", "perception", "cctv"]):
        return "sensor_inferred"
    if any(token in text for token in ["synthetic", "fixture", "replay", "sample"]):
        return "replay"
    if "source_record" in text:
        return "source_record"
    if any(token in text for token in ["data.city", ".gov", ".cat", "official", "socrata", "opendata", "open data", "open_data"]):
        return "official_record"
    if any(token in text for token in ["derived", "projection", "summary"]):
        return "derived"
    return "unknown_or_unclassified"


def infer_access(row: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(str(first_present(row, [key]) or "") for key in ["status", "source_status", "scan_status", "access", "license", "boundary", "privacy_boundary"]).lower()
    if "key_missing" in text or "key required" in text:
        status = "key_required"
    elif "restricted" in text or "private" in text:
        status = "restricted_or_unknown"
    elif row.get("source_class") in {"replay", "synthetic"} or "fixture" in text:
        status = "local_fixture"
    elif any(row.get(key) for key in ["source_url", "human_url", "api_url", "url"]) or "public" in text or "official" in text:
        status = "open_public_or_documented"
    else:
        status = "unknown"
    return {
        "status": status,
        "license": first_present(row, ["license", "licence", "license_status"]),
        "access": first_present(row, ["access", "access_status", "source_status", "scan_status", "status"]),
        "attribution": first_present(row, ["attribution", "owner", "agency", "publisher"]),
        "boundary": first_present(row, ["boundary", "privacy_boundary", "claim_boundary"]),
    }


def infer_schema_status(row: dict[str, Any]) -> dict[str, Any]:
    columns = flatten_strings(first_present(row, ["columns", "fields", "schema", "sample_fields_present"]), limit=40)
    column_count = first_present(row, ["column_count", "columns_count"])
    if not column_count and columns:
        column_count = len(columns)
    if columns or column_count or row.get("schema_fingerprint"):
        status = "present"
    elif row.get("scan_status") in {"DIRECT_METADATA_ONLY", "METADATA_ONLY"}:
        status = "metadata_only"
    else:
        status = "unknown"
    return {
        "status": status,
        "column_count": column_count,
        "schema_fingerprint": row.get("schema_fingerprint"),
        "sample_fields": columns[:20],
    }


def infer_geometry_status(row: dict[str, Any], schema_status: dict[str, Any]) -> dict[str, Any]:
    geo_fields = flatten_strings(first_present(row, ["geo_fields", "geometry_fields", "spatial_fields"]), limit=20)
    schema_fields = [field.lower() for field in schema_status.get("sample_fields", [])]
    sample_row = row.get("sample_row") if isinstance(row.get("sample_row"), dict) else {}
    sample_keys = [str(key).lower() for key in sample_row]
    all_fields = " ".join(geo_fields + schema_fields + sample_keys).lower()
    present = bool(geo_fields) or any(token in all_fields for token in GEOMETRY_TOKENS)
    if present:
        status = "present"
    elif any(token in all_fields for token in ["address", "borough", "ward", "zip", "postcode", "street"]):
        status = "indirect_location_only"
    else:
        status = "missing_or_unknown"
    return {
        "status": status,
        "geo_fields": geo_fields,
    }


def infer_time_coverage(row: dict[str, Any], schema_status: dict[str, Any]) -> dict[str, Any]:
    date_fields = flatten_strings(first_present(row, ["date_fields", "time_fields", "temporal_fields"]), limit=20)
    schema_fields = [field.lower() for field in schema_status.get("sample_fields", [])]
    if not date_fields:
        date_fields = sorted({field for field in schema_fields if any(token in field for token in TIME_TOKENS)})[:20]
    last_updated = parse_datetime(first_present(row, ["last_updated", "metadata_updated_at", "generated_at", "generated_utc", "timestamp", "updated_at", "rows_updated_at"]))
    if date_fields:
        status = "present"
    elif last_updated:
        status = "snapshot_only"
    else:
        status = "missing_or_unknown"
    return {
        "status": status,
        "date_fields": date_fields,
        "last_updated": last_updated,
        "age_days": age_days(last_updated),
    }


def infer_freshness(row: dict[str, Any], time_coverage: dict[str, Any]) -> dict[str, Any]:
    declared = first_present(row, ["freshness", "freshness_claim", "refresh", "pull_policy"])
    text = " ".join(str(first_present(row, [key]) or "") for key in ["status", "source_status", "scan_status", "freshness"]).lower()
    if "key_missing" in text or "error" in text:
        status = "blocked_or_unavailable"
    elif declared and "current" in str(declared).lower():
        status = "current_or_active"
    elif time_coverage.get("age_days") is not None and time_coverage["age_days"] <= 45:
        status = "fresh_recent_snapshot"
    elif time_coverage.get("age_days") is not None and time_coverage["age_days"] > 365:
        status = "stale"
    elif time_coverage.get("last_updated"):
        status = "dated_snapshot"
    else:
        status = "unknown"
    return {
        "status": status,
        "declared": declared,
        "last_updated": time_coverage.get("last_updated"),
        "age_days": time_coverage.get("age_days"),
    }


def infer_coverage(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_count": first_present(row, ["row_count", "rows", "record_count", "count"]),
        "column_count": first_present(row, ["column_count", "columns_count"]),
        "priority": row.get("priority"),
        "view_type": row.get("view_type"),
        "source_status": first_present(row, ["source_status", "scan_status", "status"]),
        "coverage": first_present(row, ["coverage", "geographic_coverage", "spatial_coverage"]),
        "flows": flatten_strings(row.get("flows"), limit=20),
    }


def infer_identity_status(row: dict[str, Any]) -> dict[str, Any]:
    native_ids = flatten_strings(first_present(row, ["native_id_candidates", "native_ids", "primary_keys", "id_fields", "join_hints"]), limit=20)
    text = " ".join(native_ids).lower()
    if native_ids and any(token in text for token in ["bbl", "bin", "uprn", "toid", "id", "key", "resource"]):
        status = "candidate_native_ids_present"
    elif native_ids:
        status = "join_hints_only"
    else:
        status = "missing_or_unknown"
    return {
        "status": status,
        "native_id_candidates": native_ids,
    }


def infer_consuming_flows(row: dict[str, Any]) -> list[str]:
    flows: set[str] = set()
    for flow in listify(row.get("flows")):
        flows.add(f"flow:{flow}")
    for key, value in row.items():
        key_text = str(key).lower()
        if key_text.startswith("flow") and key_text.endswith("_candidate") and value is True:
            flows.add(key_text.replace("_candidate", ""))
    for value in flatten_strings(first_present(row, ["consuming_flows", "allowed_use", "use", "purpose", "domain_pack_refs"]), limit=20):
        flows.add(f"use:{value}")
    return sorted(flows)


def infer_candidate_only(row: dict[str, Any], source_class: str) -> bool:
    text = " ".join(str(first_present(row, [key]) or "") for key in ["boundary", "claim_boundary", "use", "notes"]).lower()
    if row.get("candidate_only") is True:
        return True
    if source_class in {"sensor_inferred", "model_generated_narrative_not_fact_source", "replay", "synthetic"}:
        return True
    return "review-context only" in text or "candidate" in text or "no operational command" in text


def infer_limitations(row: dict[str, Any], schema_status: dict[str, Any], geometry_status: dict[str, Any], time_coverage: dict[str, Any]) -> list[str]:
    limits: list[str] = []
    for key in ["known_limitations", "limitations", "notes", "boundary", "sample_error", "missing_expected_files", "privacy_boundary"]:
        value = row.get(key)
        if value in (None, "", [], {}):
            continue
        if isinstance(value, list):
            limits.extend(str(item) for item in value if item)
        else:
            limits.append(str(value))
    status = str(first_present(row, ["source_status", "scan_status", "status"]) or "")
    if status and status.upper() not in {"PASS", "OK", "FULL"}:
        limits.append(f"source status: {status}")
    if schema_status["status"] != "present":
        limits.append(f"schema status: {schema_status['status']}")
    if geometry_status["status"] != "present":
        limits.append(f"geometry status: {geometry_status['status']}")
    if time_coverage["status"] == "missing_or_unknown":
        limits.append("time coverage missing or unknown")
    return sorted({limit[:300] for limit in limits if limit})


def normalize_source_row(row: dict[str, Any], path: Path, ordinal: int) -> dict[str, Any]:
    city = infer_city(row, path)
    domain = infer_domain(row, path)
    source_class = infer_source_class(row, path)
    title = first_present(row, ["name", "official_title", "metadata_name", "expected_title", "source_label", "title", "key", "source_key", "resource_id", "dataset_id"])
    source_key = first_present(row, ["source_id", "source_key", "key", "resource_id", "dataset_id", "source_record_ref"])
    url = first_present(row, ["source_url", "human_url", "api_url", "url", "metadata_url", "soda2_json_endpoint"])
    explicit_id = str(row.get("source_id")) if row.get("source_id") else None
    source_id = explicit_id or f"source:{city}:{safe_slug(source_key or title or path.stem)}"
    if not source_id.startswith("source:"):
        source_id = f"source:{city}:{safe_slug(source_id)}"
    if source_id.endswith(":unknown"):
        source_id = f"{source_id}:{ordinal:04d}"

    schema_status = infer_schema_status(row)
    geometry_status = infer_geometry_status(row, schema_status)
    time_coverage = infer_time_coverage(row, schema_status)
    normalized = {
        "source_id": source_id,
        "city": city,
        "domain": domain,
        "source_class": source_class,
        "source_name": str(title or source_key or path.stem),
        "source_key": source_key,
        "url": url,
        "freshness": infer_freshness(row, time_coverage),
        "coverage": infer_coverage(row),
        "license_access_status": infer_access({**row, "source_class": source_class}),
        "schema_status": schema_status,
        "geometry_status": geometry_status,
        "time_coverage": time_coverage,
        "identity_status": infer_identity_status(row),
        "known_limitations": [],
        "consuming_flows": infer_consuming_flows(row),
        "candidate_only": infer_candidate_only(row, source_class),
        "manifest_refs": [rel(path)],
        "manifest_containers": [row.get("_source_registry_container", "unknown")],
        "lineage": {
            "normalizer": "main_citybrain_track4_source_registry_v1",
            "source_manifest_ref": rel(path),
            "source_manifest_sha256": sha256_file(path),
        },
    }
    normalized["known_limitations"] = infer_limitations(row, schema_status, geometry_status, time_coverage)
    return normalized


def dedupe_key(source: dict[str, Any]) -> str:
    if source.get("source_id"):
        return f"source_id|{str(source['source_id']).lower()}"
    url = source.get("url")
    key = source.get("source_key")
    if url:
        return f"{source['city']}|url|{str(url).lower()}"
    if key:
        return f"{source['city']}|key|{str(key).lower()}"
    return f"{source['city']}|name|{source.get('source_name', source['source_id']).lower()}"


def merge_values(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    for field in ["manifest_refs", "manifest_containers", "known_limitations", "consuming_flows"]:
        merged[field] = sorted({*listify(left.get(field)), *listify(right.get(field))})
    for scalar in ["url", "source_key", "source_name"]:
        if not merged.get(scalar) and right.get(scalar):
            merged[scalar] = right[scalar]
    merged["candidate_only"] = bool(left.get("candidate_only") or right.get("candidate_only"))
    for nested in ["freshness", "coverage", "license_access_status", "schema_status", "geometry_status", "time_coverage", "identity_status"]:
        current = dict(left.get(nested) or {})
        incoming = right.get(nested) or {}
        for key, value in incoming.items():
            if current.get(key) in (None, "", [], {}, "unknown", "missing_or_unknown") and value not in (None, "", [], {}):
                current[key] = value
        merged[nested] = current
    return merged


def build_registry() -> tuple[dict[str, Any], dict[str, Any]]:
    candidate_files = discover_candidate_files()
    file_rows: list[dict[str, Any]] = []
    normalized: dict[str, dict[str, Any]] = {}
    total_rows = 0

    for path in candidate_files:
        payload, error = load_candidate_payload(path)
        if error:
            file_rows.append({"path": rel(path), "status": "SKIPPED", "reason": error, "source_rows": 0})
            continue
        rows = iter_source_rows(payload, path)
        file_rows.append({"path": rel(path), "status": "SCANNED", "source_rows": len(rows), "bytes": path.stat().st_size})
        for ordinal, row in enumerate(rows, start=1):
            total_rows += 1
            source = normalize_source_row(row, path, ordinal)
            key = dedupe_key(source)
            if key in normalized:
                normalized[key] = merge_values(normalized[key], source)
            else:
                normalized[key] = source

    sources = sorted(normalized.values(), key=lambda item: (item["city"], item["domain"], item["source_id"]))
    for source in sources:
        source["source_id"] = source["source_id"] if source["source_id"].startswith("source:") else f"source:{source['city']}:{safe_slug(source['source_id'])}"
        if not source["known_limitations"]:
            source["known_limitations"] = ["No known limitations were recorded in the source manifest."]

    by_city = Counter(source["city"] for source in sources)
    by_domain = Counter(source["domain"] for source in sources)
    by_class = Counter(source["source_class"] for source in sources)
    registry = {
        "schema_version": "citybrain.source_registry.v1",
        "artifact_id": "SOURCE_REGISTRY_V1",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "registry_summary": {
            "source_count": len(sources),
            "raw_source_rows_seen": total_rows,
            "source_manifest_files_scanned": sum(1 for row in file_rows if row["status"] == "SCANNED"),
            "source_manifest_files_skipped": sum(1 for row in file_rows if row["status"] == "SKIPPED"),
            "cities": dict(sorted(by_city.items())),
            "domains": dict(sorted(by_domain.items())),
            "source_classes": dict(sorted(by_class.items())),
            "candidate_only_sources": sum(1 for source in sources if source.get("candidate_only")),
            "trust_consumers": ["CHECK", "CER", "Event Fabric", "DIFF", "data maturity", "client diagnostics", "future live-source onboarding"],
        },
        "required_fields": REQUIRED_SOURCE_FIELDS,
        "sources": sources,
    }
    index = {
        "artifact_id": "SOURCE_REGISTRY_SOURCE_FILE_INDEX",
        "generated_at": registry["generated_at"],
        "candidate_file_count": len(candidate_files),
        "scanned_file_count": registry["registry_summary"]["source_manifest_files_scanned"],
        "skipped_file_count": registry["registry_summary"]["source_manifest_files_skipped"],
        "files": file_rows,
    }
    return registry, index


def registry_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain SourceRegistry v1",
        "type": "object",
        "required": ["schema_version", "registry_summary", "sources"],
        "properties": {
            "schema_version": {"const": "citybrain.source_registry.v1"},
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": REQUIRED_SOURCE_FIELDS,
                    "properties": {
                        "source_id": {"type": "string"},
                        "city": {"type": "string"},
                        "domain": {"type": "string"},
                        "source_class": {"type": "string"},
                        "freshness": {"type": "object"},
                        "coverage": {"type": "object"},
                        "license_access_status": {"type": "object"},
                        "schema_status": {"type": "object"},
                        "geometry_status": {"type": "object"},
                        "time_coverage": {"type": "object"},
                        "known_limitations": {"type": "array", "items": {"type": "string"}},
                        "consuming_flows": {"type": "array", "items": {"type": "string"}},
                    },
                    "additionalProperties": True,
                },
            },
        },
        "additionalProperties": True,
    }


def consuming_flow_map(registry: dict[str, Any]) -> dict[str, Any]:
    flow_map: dict[str, list[str]] = defaultdict(list)
    unmapped: list[str] = []
    for source in registry["sources"]:
        flows = source.get("consuming_flows") or []
        if not flows:
            unmapped.append(source["source_id"])
        for flow in flows:
            flow_map[str(flow)].append(source["source_id"])
    return {
        "artifact_id": "SOURCE_REGISTRY_CONSUMING_FLOW_MAP",
        "status": "PASS_WITH_LIMITATIONS",
        "flow_count": len(flow_map),
        "unmapped_source_count": len(unmapped),
        "flows": {key: sorted(values) for key, values in sorted(flow_map.items())},
        "unmapped_sources": sorted(unmapped),
    }


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    source_ids: set[str] = set()
    for source in registry.get("sources", []):
        for field in REQUIRED_SOURCE_FIELDS:
            if field not in source:
                errors.append(f"missing_field:{source.get('source_id', 'unknown')}:{field}")
        source_id = source.get("source_id")
        if source_id in source_ids:
            errors.append(f"duplicate_source_id:{source_id}")
        source_ids.add(source_id)
        if source.get("source_class") == "unknown_or_unclassified":
            warnings.append(f"unknown_source_class:{source_id}")
        if source.get("freshness", {}).get("status") == "unknown":
            warnings.append(f"unknown_freshness:{source_id}")
        if source.get("geometry_status", {}).get("status") == "missing_or_unknown":
            warnings.append(f"missing_geometry:{source_id}")
        if source.get("time_coverage", {}).get("status") == "missing_or_unknown":
            warnings.append(f"missing_time_coverage:{source_id}")
    if not registry.get("sources"):
        errors.append("no_sources_normalized")
    status = "PASS_WITH_LIMITATIONS" if not errors else "BLOCKED"
    return {
        "artifact_id": "SOURCE_REGISTRY_VALIDATION_REPORT",
        "generated_at": utc_now(),
        "status": status,
        "errors": errors,
        "warning_count": len(warnings),
        "warnings_sample": warnings[:200],
        "required_fields": REQUIRED_SOURCE_FIELDS,
        "source_count": len(registry.get("sources", [])),
    }


def write_hash_manifest() -> dict[str, Any]:
    entries = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "TRACK4_SOURCE_REGISTRY_HASH_MANIFEST",
        "generated_at": utc_now(),
        "algorithm": "sha256",
        "status": "PASS",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_summary(registry: dict[str, Any], validation: dict[str, Any]) -> None:
    summary = registry["registry_summary"]
    top_cities = ", ".join(f"{city}={count}" for city, count in sorted(summary["cities"].items())[:12])
    top_domains = ", ".join(f"{domain}={count}" for domain, count in sorted(summary["domains"].items())[:12])
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        f"""# Track 4 SourceRegistry v1

Status: `{validation['status']}`

Normalized `{summary['source_count']}` sources from `{summary['source_manifest_files_scanned']}` source-like manifest files.

Cities: {top_cities}

Domains: {top_domains}

This registry is a trust substrate for CHECK, CER, Event Fabric, DIFF, data maturity, client diagnostics, and future live-source onboarding. It is intentionally registry-only: no upstream data, raw artifacts, live connectors, or official truth were mutated.
""",
    )


def build_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    registry, index = build_registry()
    validation = validate_registry(registry)
    flow_map = consuming_flow_map(registry)

    registry["status"] = validation["status"]
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_V1.json", registry)
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_SCHEMA_V1.json", registry_schema())
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_VALIDATION_REPORT.json", validation)
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_SOURCE_FILE_INDEX.json", index)
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_CONSUMING_FLOW_MAP.json", flow_map)
    write_summary(registry, validation)
    decision = {
        "artifact_id": "TRACK4_SOURCE_REGISTRY_V1_DECISION",
        "status": FINAL_STATUS if validation["status"] == "PASS_WITH_LIMITATIONS" else "BLOCKED",
        "generated_at": utc_now(),
        "output_root": rel(OUTPUT_ROOT),
        "source_count": registry["registry_summary"]["source_count"],
        "source_manifest_files_scanned": registry["registry_summary"]["source_manifest_files_scanned"],
        "validation_status": validation["status"],
        "validation_errors": validation["errors"],
        "warning_count": validation["warning_count"],
        "limitations": [
            "The registry normalizes existing manifest metadata only; it does not certify source truth.",
            "Unknown freshness, geometry, schema, and time coverage are preserved as maturity gaps.",
            "No live connector, production API call, source mutation, or raw data mutation is performed.",
        ],
    }
    write_json(OUTPUT_ROOT / "DECISION.json", decision)
    write_hash_manifest()
    return decision


def validate_outputs() -> list[str]:
    required = [
        "SOURCE_REGISTRY_V1.json",
        "SOURCE_REGISTRY_SCHEMA_V1.json",
        "SOURCE_REGISTRY_VALIDATION_REPORT.json",
        "SOURCE_REGISTRY_SOURCE_FILE_INDEX.json",
        "SOURCE_REGISTRY_CONSUMING_FLOW_MAP.json",
        "SUMMARY.md",
        "DECISION.json",
        "HASH_MANIFEST.json",
    ]
    errors = [f"missing:{name}" for name in required if not (OUTPUT_ROOT / name).exists()]
    if errors:
        return errors
    registry = read_json(OUTPUT_ROOT / "SOURCE_REGISTRY_V1.json")
    validation = read_json(OUTPUT_ROOT / "SOURCE_REGISTRY_VALIDATION_REPORT.json")
    decision = read_json(OUTPUT_ROOT / "DECISION.json")
    if not registry.get("sources"):
        errors.append("registry_has_no_sources")
    for source in registry.get("sources", []):
        for field in REQUIRED_SOURCE_FIELDS:
            if field not in source:
                errors.append(f"source_missing_required_field:{source.get('source_id')}:{field}")
    if validation.get("status") != "PASS_WITH_LIMITATIONS":
        errors.append("validation_not_pass_with_limitations")
    if decision.get("status") != FINAL_STATUS:
        errors.append("decision_status_not_final_pass")
    manifest = read_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    for entry in manifest.get("entries", []):
        path = ROOT / entry["path"]
        if not path.exists():
            errors.append(f"hash_missing:{entry['path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"hash_mismatch:{entry['path']}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        decision = build_outputs()
    else:
        decision = read_json(OUTPUT_ROOT / "DECISION.json", {})
    errors = validate_outputs()
    if errors:
        print(json.dumps({"status": "BLOCKED", "errors": errors}, indent=2, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS_WITH_LIMITATIONS",
                "decision": decision.get("status", FINAL_STATUS),
                "output_root": rel(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
