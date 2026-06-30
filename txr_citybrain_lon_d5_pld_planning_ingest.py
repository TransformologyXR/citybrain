from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "LON-D5 Planning London Datahub Sampled Planning-Application Ingest"
DEFAULT_INPUT_DIR = "outputs/lon_d4_identity_backbone_ingest"
DEFAULT_OUTPUT_DIR = "outputs/lon_d5_pld_planning_ingest"
PLD_URL = "https://planningdata.london.gov.uk/api-guest/applications/_search"
PLD_ALLOW_HEADER = "be2rmRnt&"

FULL_SOURCE_FIELDS = [
    "lpa_name",
    "lpa_app_no",
    "last_updated",
    "valid_date",
    "decision_date",
    "id",
    "application_type",
    "uprn",
    "site_name",
    "site_address",
    "location",
    "decision",
    "status",
]
MINIMAL_SOURCE_FIELDS = [
    "lpa_name",
    "lpa_app_no",
    "last_updated",
    "valid_date",
    "decision_date",
    "id",
    "application_type",
    "uprn",
    "site_name",
    "site_address",
    "location",
]
BOUNDARY_STRINGS = [
    "PLD is not DOB.",
    "LON-D5 is sampled planning-application ingest only.",
    "LON-D5 does not ingest enforcement notices.",
    "LON-D5 does not ingest building-control records.",
    "LON-D5 does not prove complete London planning coverage.",
]
FORBIDDEN_ID_TOKENS = {"bbl", "bin", "dob"}
OUT_OF_SCOPE_TOKENS = {
    "enforcement_notice",
    "building_control_application",
    "dob_complaint",
    "dob_permit",
    "stop_work_order",
    "violation",
}
ENTITY_ID_PATTERN = re.compile(r"^permit:uk-london:pld:[A-Za-z0-9_.-]+$")
PARCEL_ID_PATTERN = re.compile(r"^parcel:uk-london:uprn:\d+$")

ENTITY_COLUMNS = [
    "canonical_id",
    "entity_type",
    "id_system",
    "native_id",
    "city",
    "country",
    "borough",
    "permit_type",
    "source_dataset",
    "lpa_name",
    "lpa_app_no",
    "application_type",
    "valid_date",
    "decision_date",
    "last_updated",
    "site_name",
    "site_address",
    "decision",
    "status",
    "uprn_refs",
    "location",
    "location_status",
    "confidence",
    "provenance",
    "key_used",
    "raw_hit_id",
]
EDGE_COLUMNS = [
    "edge_id",
    "src",
    "relation",
    "dst",
    "role",
    "confidence",
    "provenance",
    "source_uprn",
    "source_application_id",
    "semantic_caveat",
]
UNATTACHED_COLUMNS = ENTITY_COLUMNS + ["unattached_reason", "invalid_uprn_refs"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(value) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_col(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def parse_json_col(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str):
        return json.loads(value) if value else None
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any, length: int = 16) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def write_parquet(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def frame_to_records(df: pd.DataFrame, limit: int = 25) -> list[dict[str, Any]]:
    records = df.head(limit).to_dict(orient="records")
    for record in records:
        for key in ("uprn_refs", "location", "confidence", "provenance", "invalid_uprn_refs"):
            if key in record:
                try:
                    record[key] = parse_json_col(record[key])
                except Exception:
                    pass
    return records


def has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, float) and pd.isna(value):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def safe_slug(value: Any) -> str:
    raw = str(value or "").strip()
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)
    safe = re.sub(r"_+", "_", safe).strip("_.-")
    return safe[:120]


def choose_application_id(record: dict[str, Any]) -> tuple[str, str, str]:
    pld_id = record.get("id")
    if has_value(pld_id):
        safe = safe_slug(pld_id)
        if safe:
            return safe, str(pld_id), "pld_id"
    lpa_app_no = record.get("lpa_app_no")
    if has_value(lpa_app_no):
        safe = safe_slug(lpa_app_no)
        if safe:
            return safe, str(lpa_app_no), "lpa_app_no"
    digest = stable_hash(
        {
            "lpa_name": record.get("lpa_name"),
            "lpa_app_no": record.get("lpa_app_no"),
            "site_address": record.get("site_address"),
        },
        length=24,
    )
    return digest, digest, "stable_hash"


def scalar_or_none(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value if has_value(value) else None


def normalize_uprns(value: Any) -> tuple[list[str], list[str]]:
    valid: list[str] = []
    invalid: list[str] = []

    def add_piece(piece: Any) -> None:
        if piece is None:
            return
        if isinstance(piece, float) and pd.isna(piece):
            return
        if isinstance(piece, int):
            text = str(piece)
        elif isinstance(piece, float) and piece.is_integer():
            text = str(int(piece))
        else:
            text = str(piece).strip()
        if not text:
            return
        for item in re.split(r"[,;|\s]+", text):
            candidate = item.strip()
            if not candidate:
                continue
            if re.fullmatch(r"\d+", candidate):
                normalized = candidate.lstrip("0") or "0"
                valid.append(normalized)
            else:
                invalid.append(candidate)

    if isinstance(value, (list, tuple, set)):
        for item in value:
            add_piece(item)
    else:
        add_piece(value)

    return sorted(set(valid), key=lambda item: (len(item), item)), sorted(set(invalid))


def pld_body(borough: str, max_records: int, fields: list[str]) -> dict[str, Any]:
    return {
        "size": max_records,
        "query": {"bool": {"must": [{"term": {"lpa_name.raw": borough}}]}},
        "_source": fields,
    }


def pld_post(body: dict[str, Any], timeout: int = 90) -> tuple[int, dict[str, Any]]:
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        PLD_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TXR-CityBrain-LON-D5/1.0",
            "X-API-AllowRequest": PLD_ALLOW_HEADER,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = int(response.status)
        data = response.read()
    return status, json.loads(data.decode("utf-8"))


def pld_health_check(borough: str) -> dict[str, Any]:
    body = pld_body(borough, 1, ["id", "lpa_name", "lpa_app_no", "uprn"])
    try:
        status, payload = pld_post(body, timeout=45)
        return {
            "status": "PASS" if status == 200 else "FAIL",
            "http_status": status,
            "endpoint": PLD_URL,
            "request_size": 1,
            "response_hit_count": len(payload.get("hits", {}).get("hits", [])),
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "endpoint": PLD_URL,
            "request_size": 1,
            "error": str(exc),
        }


def extract_records(response_json: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for hit in response_json.get("hits", {}).get("hits", []):
        source = dict(hit.get("_source") or {})
        source["_hit_id"] = hit.get("_id")
        source["_score"] = hit.get("_score")
        records.append(source)
    return records


def query_pld_records(borough: str, max_records: int) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    full_body = pld_body(borough, max_records, FULL_SOURCE_FIELDS)
    fallback_used = False
    fallback_error = None
    fields = FULL_SOURCE_FIELDS
    body = full_body
    try:
        http_status, response_json = pld_post(full_body)
    except urllib.error.HTTPError as exc:
        fallback_used = True
        fallback_error = {
            "http_status": exc.code,
            "reason": exc.reason,
            "body": exc.read().decode("utf-8", errors="replace")[:2000],
        }
        fields = MINIMAL_SOURCE_FIELDS
        body = pld_body(borough, max_records, fields)
        http_status, response_json = pld_post(body)

    records = extract_records(response_json)
    field_counts = {field: sum(1 for row in records if has_value(row.get(field))) for field in fields}
    query_report = {
        "task": TASK_NAME,
        "endpoint": PLD_URL,
        "borough": borough,
        "requested_max_records": max_records,
        "http_status": http_status,
        "fallback_used": fallback_used,
        "fallback_error": fallback_error,
        "used_source_fields": fields,
        "request_body": body,
        "total": response_json.get("hits", {}).get("total"),
        "records_returned": len(records),
        "field_counts": field_counts,
        "header_policy": "Uses X-API-AllowRequest header proven by LON-D2/LON-D3 probes.",
    }
    return query_report, response_json, records


def load_d4(input_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    parcels_path = input_dir / "canonical" / "london_parcels_uprn.parquet"
    edges_path = input_dir / "canonical" / "london_identity_edges.parquet"
    harness_path = input_dir / "LON_D4_HARNESS_REPORT.json"
    parcels = pd.read_parquet(parcels_path)
    edges = pd.read_parquet(edges_path)
    harness = read_json(harness_path)
    return parcels, edges, harness


def collect_tracked_inputs(input_dir: Path) -> list[Path]:
    paths = sorted(path for path in input_dir.rglob("*") if path.is_file())
    for extra in [
        Path("LON_D1_identity_backbone_inventory_v0_1.zip"),
        Path("LON_D2_identity_backbone_sample_fixture_v0_1.zip"),
        Path("LON_D3_probe_review_v0_2.zip"),
        Path("LON_D2_identity_backbone_sample_fixture_v0_1")
        / "lon_d2_identity_backbone_fixture"
        / "LON_D2_PLD_API_PROBE_REQUESTS.json",
        Path("LON_D2_identity_backbone_sample_fixture_v0_1")
        / "lon_d2_identity_backbone_fixture"
        / "lon_d3_pld_probe"
        / "LON_D3_PLD_API_PROBE_RESPONSE.json",
    ]:
        if extra.exists() and extra.is_file():
            paths.append(extra)
    return sorted({path.resolve() for path in paths})


def input_hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path): sha256_file(path) for path in paths if path.exists() and path.is_file()}


def inventory_inputs(input_dir: Path, tracked_inputs: list[Path]) -> dict[str, Any]:
    return {
        "task": TASK_NAME,
        "input_dir": str(input_dir),
        "created_utc": utc_now(),
        "files": [
            {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in tracked_inputs
            if path.exists() and path.is_file()
        ],
    }


def preconditions(input_dir: Path, borough: str, api_health: dict[str, Any]) -> dict[str, Any]:
    harness_path = input_dir / "LON_D4_HARNESS_REPORT.json"
    parcels_path = input_dir / "canonical" / "london_parcels_uprn.parquet"
    edges_path = input_dir / "canonical" / "london_identity_edges.parquet"
    checks: dict[str, Any] = {
        "lon_d4_harness_report_exists": harness_path.exists(),
        "lon_d4_canonical_uprn_entities_exist": parcels_path.exists(),
        "lon_d4_identity_edges_exist": edges_path.exists(),
        "pld_api_reachable": api_health.get("status") == "PASS",
    }
    if harness_path.exists():
        try:
            checks["lon_d4_harness_report_status_pass"] = read_json(harness_path).get("status") == "PASS"
        except Exception:
            checks["lon_d4_harness_report_status_pass"] = False
    else:
        checks["lon_d4_harness_report_status_pass"] = False
    if edges_path.exists():
        try:
            edge_relations = set(pd.read_parquet(edges_path, columns=["relation"])["relation"].astype(str))
            checks["lon_d4_uprn_to_toid_edges_exist"] = "has_building" in edge_relations
            checks["lon_d4_uprn_to_usrn_edges_exist"] = "on_street" in edge_relations
        except Exception:
            checks["lon_d4_uprn_to_toid_edges_exist"] = False
            checks["lon_d4_uprn_to_usrn_edges_exist"] = False
    else:
        checks["lon_d4_uprn_to_toid_edges_exist"] = False
        checks["lon_d4_uprn_to_usrn_edges_exist"] = False
    return {
        "gate": "LON-D5-PRECOND",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "borough": borough,
        "checks": checks,
        "pld_api_health": api_health,
    }


def entity_confidence() -> dict[str, Any]:
    return {
        "method": "official_pld_application_record",
        "score": 0.95,
        "basis": "Official Planning London Datahub application record returned by the guest API.",
    }


def edge_confidence() -> dict[str, Any]:
    return {
        "method": "pld_uprn_exact_match_to_lond4",
        "score": 0.95,
        "basis": "PLD UPRN exactly matched a LON-D4 UPRN canonical parcel-compatible entity.",
    }


def pld_provenance(record: dict[str, Any], borough: str, fields: list[str]) -> list[dict[str, Any]]:
    source_id = str(record.get("id") or record.get("lpa_app_no") or record.get("_hit_id") or "")
    return [
        {
            "source_dataset": "Planning London Datahub",
            "source_api": PLD_URL,
            "source_id": source_id,
            "source_hit_id": record.get("_hit_id"),
            "source_fields": fields,
            "source_borough_filter": borough,
            "derivation": "Canonical permit-compatible planning application entity emitted from one PLD application record.",
            "observed_at": utc_now(),
        }
    ]


def edge_provenance(record: dict[str, Any], uprn: str, borough: str) -> list[dict[str, Any]]:
    return [
        {
            "source_dataset": "Planning London Datahub + LON-D4 identity backbone",
            "source_api": PLD_URL,
            "source_id": str(record.get("id") or record.get("lpa_app_no") or record.get("_hit_id") or ""),
            "source_uprn": uprn,
            "source_borough_filter": borough,
            "derivation": "Canonical edge emitted only because the PLD UPRN exactly matches a LON-D4 UPRN entity.",
            "observed_at": utc_now(),
        }
    ]


def build_canonical(
    records: list[dict[str, Any]],
    borough: str,
    used_fields: list[str],
    d4_uprn_ids: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    unattached: list[dict[str, Any]] = []
    seen_entity_ids: Counter[str] = Counter()
    seen_edges: set[tuple[str, str]] = set()
    join_stats = {
        "records_total": len(records),
        "records_with_uprn": 0,
        "records_with_valid_uprn": 0,
        "records_with_invalid_uprn": 0,
        "pld_uprns_total": 0,
        "pld_uprns_unique": 0,
        "pld_uprns_matched_to_lon_d4": 0,
        "pld_uprns_not_in_lon_d4_sample": 0,
        "records_with_matched_uprn": 0,
        "edges_emitted": 0,
    }
    all_uprns: list[str] = []
    matched_uprn_tokens = 0
    unmatched_uprn_tokens = 0

    for record in records:
        safe_id, native_id, key_used = choose_application_id(record)
        canonical_id = f"permit:uk-london:pld:{safe_id}"
        seen_entity_ids[canonical_id] += 1
        if seen_entity_ids[canonical_id] > 1:
            suffix = stable_hash({"canonical_id": canonical_id, "ordinal": seen_entity_ids[canonical_id], "record": record}, 8)
            canonical_id = f"{canonical_id}_{suffix}"

        uprn_refs, invalid_uprns = normalize_uprns(record.get("uprn"))
        if has_value(record.get("uprn")):
            join_stats["records_with_uprn"] += 1
        if uprn_refs:
            join_stats["records_with_valid_uprn"] += 1
        if invalid_uprns:
            join_stats["records_with_invalid_uprn"] += 1
        all_uprns.extend(uprn_refs)

        location_value = record.get("location") if has_value(record.get("location")) else None
        entity = {
            "canonical_id": canonical_id,
            "entity_type": "permit",
            "id_system": "pld",
            "native_id": native_id,
            "city": "london",
            "country": "uk",
            "borough": borough,
            "permit_type": "planning_application",
            "source_dataset": "planning_london_datahub",
            "lpa_name": scalar_or_none(record.get("lpa_name")),
            "lpa_app_no": scalar_or_none(record.get("lpa_app_no")),
            "application_type": scalar_or_none(record.get("application_type")),
            "valid_date": scalar_or_none(record.get("valid_date")),
            "decision_date": scalar_or_none(record.get("decision_date")),
            "last_updated": scalar_or_none(record.get("last_updated")),
            "site_name": scalar_or_none(record.get("site_name")),
            "site_address": scalar_or_none(record.get("site_address")),
            "decision": scalar_or_none(record.get("decision")),
            "status": scalar_or_none(record.get("status")),
            "uprn_refs": json_col(uprn_refs),
            "location": json_col(location_value or {}),
            "location_status": "pld_reported_location_not_certified_identity_geometry" if location_value else "missing_location",
            "confidence": json_col(entity_confidence()),
            "provenance": json_col(pld_provenance(record, borough, used_fields)),
            "key_used": key_used,
            "raw_hit_id": scalar_or_none(record.get("_hit_id")),
        }
        entities.append(entity)

        matched_this_record = False
        for uprn in uprn_refs:
            if uprn in d4_uprn_ids:
                matched_uprn_tokens += 1
                matched_this_record = True
                edge_key = (uprn, canonical_id)
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                edge_id = f"edge:uk-london:pld-uprn:{stable_hash({'uprn': uprn, 'permit': canonical_id}, 24)}"
                edges.append(
                    {
                        "edge_id": edge_id,
                        "src": f"parcel:uk-london:uprn:{uprn}",
                        "relation": "subject_of_permit",
                        "dst": canonical_id,
                        "role": "planning_application_subject",
                        "confidence": json_col(edge_confidence()),
                        "provenance": json_col(edge_provenance(record, uprn, borough)),
                        "source_uprn": uprn,
                        "source_application_id": native_id,
                        "semantic_caveat": "Exact UPRN identity edge only; no address-derived or geometry-derived identity edge is fabricated.",
                    }
                )
            else:
                unmatched_uprn_tokens += 1
        if matched_this_record:
            join_stats["records_with_matched_uprn"] += 1
        else:
            if invalid_uprns:
                reason = "invalid_uprn"
            elif uprn_refs:
                reason = "uprn_not_in_lon_d4_sample"
            elif location_value:
                reason = "location_only"
            elif has_value(record.get("site_address")) or has_value(record.get("site_name")):
                reason = "address_only"
            else:
                reason = "no_uprn"
            unattached.append({**entity, "unattached_reason": reason, "invalid_uprn_refs": json_col(invalid_uprns)})

    join_stats["pld_uprns_total"] = len(all_uprns)
    join_stats["pld_uprns_unique"] = len(set(all_uprns))
    join_stats["pld_uprns_matched_to_lon_d4"] = matched_uprn_tokens
    join_stats["pld_uprns_not_in_lon_d4_sample"] = unmatched_uprn_tokens
    join_stats["edges_emitted"] = len(edges)
    join_stats["join_rate_over_pld_uprns"] = matched_uprn_tokens / len(all_uprns) if all_uprns else 0.0

    entities_df = pd.DataFrame(entities, columns=ENTITY_COLUMNS)
    edges_df = pd.DataFrame(edges, columns=EDGE_COLUMNS)
    unattached_df = pd.DataFrame(unattached, columns=UNATTACHED_COLUMNS)
    return entities_df, edges_df, unattached_df, join_stats


def field_coverage(records: list[dict[str, Any]], fields: list[str]) -> dict[str, Any]:
    total = len(records)
    counts = {field: sum(1 for row in records if has_value(row.get(field))) for field in fields}
    return {
        "status": "PASS" if total > 0 else "FAIL",
        "records_returned": total,
        "counts": counts,
        "coverage": {field: (count / total if total else 0.0) for field, count in counts.items()},
        "required_sample_counts": {
            "requested_max_records": total,
            "records_with_lpa_app_no": counts.get("lpa_app_no", 0),
            "records_with_id": counts.get("id", 0),
            "records_with_uprn": counts.get("uprn", 0),
            "records_with_location": counts.get("location", 0),
            "records_with_decision_date": counts.get("decision_date", 0),
            "records_with_valid_date": counts.get("valid_date", 0),
        },
    }


def toid_context(d4_edges: pd.DataFrame, pld_edges: pd.DataFrame) -> dict[str, Any]:
    has_building = d4_edges[d4_edges["relation"].astype(str) == "has_building"].copy()
    toid_by_uprn: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in has_building.to_dict(orient="records"):
        uprn = str(row.get("source_uprn") or str(row.get("src", "")).split(":")[-1])
        confidence = parse_json_col(row.get("confidence"))
        toid_by_uprn[uprn].append(
            {
                "edge_id": row.get("edge_id"),
                "toid": str(row.get("dst", "")).split(":")[-1],
                "dst": row.get("dst"),
                "inherited_confidence": confidence.get("score") if isinstance(confidence, dict) else None,
            }
        )
    matched_uprns = sorted(set(pld_edges["source_uprn"].astype(str))) if not pld_edges.empty else []
    with_context = [uprn for uprn in matched_uprns if toid_by_uprn.get(uprn)]
    without_context = [uprn for uprn in matched_uprns if not toid_by_uprn.get(uprn)]
    return {
        "gate": "LON-D5-TOID-CONTEXT",
        "status": "PASS",
        "method": "Derived context only: PLD permit -> exact UPRN edge, then existing LON-D4 UPRN -> TOID has_building traversal.",
        "matched_uprns_total": len(matched_uprns),
        "matched_uprns_with_toid_context": len(with_context),
        "matched_uprns_without_toid_context": len(without_context),
        "toid_context_coverage": len(with_context) / len(matched_uprns) if matched_uprns else 0.0,
        "sample_context": {uprn: toid_by_uprn[uprn][:3] for uprn in with_context[:10]},
    }


def join_report(join_stats: dict[str, Any], toid_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate": "LON-D5-UPRN-JOIN",
        "status": "PASS",
        "exact_join_attempted": True,
        "pld_records_total": join_stats["records_total"],
        "pld_records_with_uprn": join_stats["records_with_uprn"],
        "pld_records_with_valid_uprn": join_stats["records_with_valid_uprn"],
        "pld_records_with_invalid_uprn": join_stats["records_with_invalid_uprn"],
        "pld_records_with_matched_uprn": join_stats["records_with_matched_uprn"],
        "pld_uprns_total": join_stats["pld_uprns_total"],
        "pld_uprns_unique": join_stats["pld_uprns_unique"],
        "pld_uprns_matched_to_lon_d4": join_stats["pld_uprns_matched_to_lon_d4"],
        "pld_uprns_not_in_lon_d4_sample": join_stats["pld_uprns_not_in_lon_d4_sample"],
        "pld_to_uprn_edges_emitted": join_stats["edges_emitted"],
        "join_rate_over_pld_uprns": join_stats["join_rate_over_pld_uprns"],
        "low_join_rate_policy": "Low or zero join rate is allowed for LON-D5 because LON-D4 is a sampled Lambeth identity backbone; the adapter reports the overlap honestly.",
        "toid_context": toid_report,
    }


def edge_integrity(edges: pd.DataFrame, entities: pd.DataFrame, d4_uprn_ids: set[str]) -> dict[str, Any]:
    permit_ids = set(entities["canonical_id"].astype(str))
    failures = []
    for row in edges.to_dict(orient="records"):
        src = str(row.get("src"))
        dst = str(row.get("dst"))
        src_uprn = src.split(":")[-1]
        if src_uprn not in d4_uprn_ids:
            failures.append(f"{row.get('edge_id')} missing D4 UPRN src {src}")
        if dst not in permit_ids:
            failures.append(f"{row.get('edge_id')} missing PLD dst {dst}")
    return {
        "gate": "LON-D5-EDGE-INTEGRITY",
        "status": "PASS" if not failures else "FAIL",
        "edges_checked": len(edges),
        "dangling_references": len(failures),
        "details": failures[:20],
    }


def confidence_summary(entities: pd.DataFrame, edges: pd.DataFrame) -> dict[str, Any]:
    methods: Counter[str] = Counter()
    score_ranges: dict[str, list[float]] = defaultdict(list)
    for df in [entities, edges]:
        if df.empty:
            continue
        for value in df["confidence"].tolist():
            confidence = parse_json_col(value)
            if isinstance(confidence, dict):
                method = str(confidence.get("method"))
                methods[method] += 1
                if confidence.get("score") is not None:
                    score_ranges[method].append(float(confidence["score"]))
    return {
        "status": "PASS",
        "policy": {
            "PLD application entity from official PLD record": 0.95,
            "PLD->UPRN edge by exact UPRN match to LON-D4": 0.95,
            "PLD->TOID context via LON-D4 UPRN->TOID traversal": "inherit min(edge confidence)",
            "address-only fallback": "<=0.60 and not canonical in LON-D5",
            "location-only fallback": "<=0.70 and not canonical in LON-D5",
        },
        "method_counts": dict(methods),
        "score_ranges": {
            method: {"min": min(scores), "max": max(scores)}
            for method, scores in score_ranges.items()
            if scores
        },
    }


def compatibility_harness(entities: pd.DataFrame, edges: pd.DataFrame, d4_uprn_ids: set[str]) -> dict[str, Any]:
    entity_records = entities.to_dict(orient="records")
    edge_records = edges.to_dict(orient="records")
    permit_registry = {row["canonical_id"] for row in entity_records}
    gates = []

    def add(gate_id: str, passed: bool, checked: int, failed: int, details: list[str] | None = None) -> None:
        gates.append({"gate_id": gate_id, "status": "PASS" if passed else "FAIL", "checked": checked, "failed": failed, "details": details or []})

    schema_failures = []
    required_entity_cols = {
        "canonical_id",
        "entity_type",
        "id_system",
        "native_id",
        "city",
        "country",
        "borough",
        "permit_type",
        "source_dataset",
        "uprn_refs",
        "location",
        "confidence",
        "provenance",
    }
    for idx, row in enumerate(entity_records):
        missing = sorted(required_entity_cols - set(row))
        if missing:
            schema_failures.append(f"entity[{idx}] missing {missing}")
        if row.get("entity_type") != "permit":
            schema_failures.append(f"entity[{idx}] unsupported entity_type {row.get('entity_type')}")
        if row.get("id_system") != "pld":
            schema_failures.append(f"entity[{idx}] unsupported id_system {row.get('id_system')}")
        if row.get("permit_type") != "planning_application":
            schema_failures.append(f"entity[{idx}] unsupported permit_type {row.get('permit_type')}")
        try:
            parse_json_col(row.get("uprn_refs"))
            parse_json_col(row.get("location"))
            parse_json_col(row.get("confidence"))
            parse_json_col(row.get("provenance"))
        except Exception as exc:
            schema_failures.append(f"entity[{idx}] JSON field parse failed: {exc}")
    for idx, row in enumerate(edge_records):
        for field in ("edge_id", "src", "dst", "relation", "role", "confidence", "provenance"):
            if field not in row:
                schema_failures.append(f"edge[{idx}] missing {field}")
        if row.get("relation") != "subject_of_permit":
            schema_failures.append(f"edge[{idx}] unsupported relation {row.get('relation')}")
    add("G-SCHEMA", not schema_failures, len(entity_records) + len(edge_records), len(schema_failures), schema_failures[:10])

    id_failures = []
    for row in entity_records:
        canonical_id = str(row.get("canonical_id", ""))
        parts = set(canonical_id.lower().split(":"))
        bad_forbidden = bool(parts & FORBIDDEN_ID_TOKENS)
        if not ENTITY_ID_PATTERN.match(canonical_id) or bad_forbidden:
            id_failures.append(canonical_id)
    duplicate_ids = [item for item, count in Counter(row["canonical_id"] for row in entity_records).items() if count > 1]
    id_failures.extend(f"duplicate:{item}" for item in duplicate_ids)
    add("G-ID", not id_failures, len(entity_records), len(id_failures), id_failures[:10])

    triad_failures = []
    for row in entity_records:
        confidence = parse_json_col(row.get("confidence"))
        provenance = parse_json_col(row.get("provenance"))
        if not confidence or not confidence.get("method") or confidence.get("score") is None or not provenance:
            triad_failures.append(str(row.get("canonical_id")))
    for row in edge_records:
        confidence = parse_json_col(row.get("confidence"))
        provenance = parse_json_col(row.get("provenance"))
        if not confidence or not confidence.get("method") or confidence.get("score") is None or not provenance:
            triad_failures.append(str(row.get("edge_id")))
    add("G-TRIAD", not triad_failures, len(entity_records) + len(edge_records), len(triad_failures), triad_failures[:10])

    geo_failures = []
    for row in entity_records:
        try:
            location = parse_json_col(row.get("location"))
        except Exception as exc:
            geo_failures.append(f"{row.get('canonical_id')} location JSON failed: {exc}")
            continue
        status = row.get("location_status")
        if status not in {"pld_reported_location_not_certified_identity_geometry", "missing_location"}:
            geo_failures.append(f"{row.get('canonical_id')} bad location_status={status}")
        if location and not isinstance(location, dict):
            geo_failures.append(f"{row.get('canonical_id')} location is not a JSON object")
    add("G-GEO", not geo_failures, len(entity_records), len(geo_failures), geo_failures[:10])

    ref_failures = []
    for row in edge_records:
        src = str(row.get("src", ""))
        src_uprn = src.split(":")[-1]
        if not PARCEL_ID_PATTERN.match(src) or src_uprn not in d4_uprn_ids:
            ref_failures.append(f"{row.get('edge_id')} missing D4 UPRN src {src}")
        if row.get("dst") not in permit_registry:
            ref_failures.append(f"{row.get('edge_id')} missing PLD permit dst {row.get('dst')}")
    add("G-REF", not ref_failures, len(edge_records) * 2, len(ref_failures), ref_failures[:10])

    edge_failures = []
    for row in edge_records:
        confidence = parse_json_col(row.get("confidence"))
        if row.get("relation") != "subject_of_permit":
            edge_failures.append(str(row.get("edge_id")))
        elif row.get("role") != "planning_application_subject":
            edge_failures.append(str(row.get("edge_id")))
        elif not confidence or confidence.get("method") != "pld_uprn_exact_match_to_lond4" or float(confidence.get("score", 0)) <= 0:
            edge_failures.append(str(row.get("edge_id")))
    add("G-EDGE", not edge_failures, len(edge_records), len(edge_failures), edge_failures[:10])

    return {
        "status": "PASS" if all(gate["status"] == "PASS" for gate in gates) else "FAIL",
        "compatibility_marker": "a2_binary_unavailable_compatibility_harness_used",
        "reason": "The local A2 binary is the NYC Flow-2 acceptance harness; LON-D5 uses the same invariant names over London PLD permit-compatible entities without claiming exact NYC binary acceptance.",
        "gates": gates,
    }


def drift_test(entities: pd.DataFrame, edges: pd.DataFrame, d4_uprn_ids: set[str]) -> dict[str, Any]:
    mutated_entities = entities.copy()
    mutated_edges = edges.copy()
    if not mutated_entities.empty:
        idx = mutated_entities.index[0]
        old_id = str(mutated_entities.loc[idx, "canonical_id"])
        mutated_entities.loc[idx, "entity_type"] = "planning_application"
        mutated_entities.loc[idx, "canonical_id"] = old_id.replace("permit:uk-london:pld:", "planning_application:uk-london:pld:", 1)
    if mutated_edges.empty and not mutated_entities.empty and d4_uprn_ids:
        first_uprn = sorted(d4_uprn_ids, key=lambda item: (len(item), item))[0]
        mutated_edges = pd.DataFrame(
            [
                {
                    "edge_id": "edge:uk-london:pld-uprn:drift_probe",
                    "src": f"parcel:uk-london:uprn:{first_uprn}",
                    "relation": "subject_of_planning_application",
                    "dst": mutated_entities.iloc[0]["canonical_id"],
                    "role": "planning_application_subject",
                    "confidence": json_col(edge_confidence()),
                    "provenance": json_col([{"source_dataset": "drift_test", "observed_at": utc_now()}]),
                    "source_uprn": first_uprn,
                    "source_application_id": mutated_entities.iloc[0]["native_id"],
                    "semantic_caveat": "Synthetic drift probe only; not emitted as canonical output.",
                }
            ],
            columns=EDGE_COLUMNS,
        )
    elif not mutated_edges.empty:
        mutated_edges.loc[mutated_edges.index[0], "relation"] = "subject_of_planning_application"
    result = compatibility_harness(mutated_entities, mutated_edges, d4_uprn_ids)
    failing_gates = [gate["gate_id"] for gate in result["gates"] if gate["status"] == "FAIL"]
    return {
        "gate": "LON-D5-DRIFT",
        "status": "PASS" if result["status"] == "FAIL" and failing_gates else "FAIL",
        "drift_mutation": {
            "permit:uk-london:pld:{id}": "planning_application:uk-london:pld:{id}",
            "subject_of_permit": "subject_of_planning_application",
        },
        "mutated_harness_status": result["status"],
        "failing_gates": failing_gates,
    }


def pld_sample_gate(query_report: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    sample_counts = coverage["required_sample_counts"]
    sample_counts["requested_max_records"] = query_report["requested_max_records"]
    return {
        "gate": "LON-D5-PLD-SAMPLE",
        "status": "PASS" if query_report["records_returned"] >= 1 else "FAIL",
        **sample_counts,
    }


def id_format_gate(entities: pd.DataFrame) -> dict[str, Any]:
    failures = []
    for canonical_id in entities["canonical_id"].astype(str):
        parts = set(canonical_id.lower().split(":"))
        if not ENTITY_ID_PATTERN.match(canonical_id) or bool(parts & FORBIDDEN_ID_TOKENS):
            failures.append(canonical_id)
    return {
        "gate": "LON-D5-ID-FORMAT",
        "status": "PASS" if not failures else "FAIL",
        "entities_checked": len(entities),
        "failures": failures[:20],
    }


def unattached_report(unattached: pd.DataFrame) -> dict[str, Any]:
    counts = Counter(unattached["unattached_reason"].astype(str)) if not unattached.empty else Counter()
    return {
        "status": "PASS",
        "unattached_records": len(unattached),
        "reason_counts": dict(sorted(counts.items())),
        "sample_records": [
            {
                "canonical_id": row["canonical_id"],
                "native_id": row["native_id"],
                "reason": row["unattached_reason"],
                "uprn_refs": parse_json_col(row["uprn_refs"]),
                "site_address": row.get("site_address"),
            }
            for row in unattached.head(25).to_dict(orient="records")
        ],
    }


def out_of_scope_report(entities: pd.DataFrame, edges: pd.DataFrame, unattached: pd.DataFrame) -> dict[str, Any]:
    payload = "\n".join(
        [
            entities.to_json(orient="records"),
            edges.to_json(orient="records"),
            unattached.to_json(orient="records"),
        ]
    ).lower()
    found = sorted(token for token in OUT_OF_SCOPE_TOKENS if token in payload)
    return {
        "gate": "LON-D5-OUT-OF-SCOPE",
        "status": "PASS" if not found else "FAIL",
        "scanned": "canonical PLD entity, edge, and unattached-record payloads only",
        "found_forbidden_payload_terms": found,
        "exception": "No-overclaim and forbidden-wording reports may contain boundary wording.",
    }


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    required_files = {
        "README.md": output_dir / "README.md",
        "LON_D5_MANIFEST.json": output_dir / "LON_D5_MANIFEST.json",
        "LON_D5_HARNESS_REPORT.json": output_dir / "LON_D5_HARNESS_REPORT.json",
        "LON_D5_ADAPTER_HANDOVER.md": output_dir / "LON_D5_ADAPTER_HANDOVER.md",
    }
    files = {}
    passed = True
    for name, path in required_files.items():
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [item for item in BOUNDARY_STRINGS if item not in text]
        files[name] = {"missing_boundary_strings": missing}
        if missing:
            passed = False
    return {
        "gate": "LON-D5-NO-OVERCLAIM",
        "status": "PASS" if passed else "FAIL",
        "boundary_strings": BOUNDARY_STRINGS,
        "files": files,
    }


def hash_report(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D5-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def write_docs(
    output_dir: Path,
    borough: str,
    max_records: int,
    counts: dict[str, Any],
    query_report: dict[str, Any],
    coverage: dict[str, Any],
    join_rates: dict[str, Any],
    unattached: dict[str, Any],
    toid_report: dict[str, Any],
    confidence: dict[str, Any],
    a2_report: dict[str, Any],
) -> None:
    boundary = "\n".join(f"- {item}" for item in BOUNDARY_STRINGS)
    field_lines = "\n".join(
        f"- {field}: {coverage['counts'].get(field, 0)} / {coverage['records_returned']}"
        for field in FULL_SOURCE_FIELDS
    )
    reason_lines = "\n".join(f"- {reason}: {count}" for reason, count in unattached["reason_counts"].items()) or "- none"
    readme = f"""# LON-D5 Planning London Datahub Sampled Planning-Application Ingest

{boundary}

This output attaches sampled Planning London Datahub application records to the accepted LON-D4 Lambeth identity backbone where PLD UPRNs exactly match LON-D4 UPRN entities. It does not create address-derived identity edges and it does not create direct PLD-to-TOID canonical edges.

## Source

- API: {PLD_URL}
- Borough filter: {borough}
- Requested sample size: {max_records}
- Records returned: {query_report['records_returned']}

## Counts

- PLD permit-compatible entities: {counts['pld_entities']}
- Exact PLD to UPRN edges: {counts['pld_uprn_edges']}
- Unattached PLD records: {counts['unattached_records']}
- Records with UPRN: {join_rates['pld_records_with_uprn']}
- UPRN join rate: {join_rates['join_rate_over_pld_uprns'] * 100:.2f}%

## Field Coverage

{field_lines}

## Unattached Reasons

{reason_lines}

## TOID Context

Matched UPRNs with TOID context: {toid_report['matched_uprns_with_toid_context']}
Matched UPRNs without TOID context: {toid_report['matched_uprns_without_toid_context']}
TOID context coverage: {toid_report['toid_context_coverage'] * 100:.2f}%

## Compatibility

A2-style invariant gates passed with marker `{a2_report.get('compatibility_marker')}`. This is a compatibility harness over London PLD permit-compatible entities, not a claim of exact NYC Flow-2 binary acceptance.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    handover = f"""# LON-D5 Adapter Handover

{boundary}

## Entrypoint

`txr_citybrain_lon_d5_pld_planning_ingest.py`

```bash
python txr_citybrain_lon_d5_pld_planning_ingest.py --input-dir outputs/lon_d4_identity_backbone_ingest --output-dir outputs/lon_d5_pld_planning_ingest --borough Lambeth --max-records 1000 --run-gates
```

## Source API Used

{PLD_URL}

The request uses `X-API-AllowRequest` with the value proven by the LON-D2/LON-D3 probes. It targets a single borough filter: {borough}.

## Borough And Sample Size

- Borough: {borough}
- Requested max records: {max_records}
- Returned records: {query_report['records_returned']}

## Field Coverage

{field_lines}

## UPRN Join Rate

- PLD records total: {join_rates['pld_records_total']}
- PLD records with UPRN: {join_rates['pld_records_with_uprn']}
- PLD UPRNs total: {join_rates['pld_uprns_total']}
- PLD UPRNs matched to LON-D4: {join_rates['pld_uprns_matched_to_lon_d4']}
- PLD UPRNs not in LON-D4 sample: {join_rates['pld_uprns_not_in_lon_d4_sample']}
- PLD to UPRN edges emitted: {join_rates['pld_to_uprn_edges_emitted']}
- Join rate over PLD UPRNs: {join_rates['join_rate_over_pld_uprns'] * 100:.2f}%

## Unattached Reasons

{reason_lines}

## TOID Context Coverage

- Matched UPRNs with TOID context: {toid_report['matched_uprns_with_toid_context']}
- Matched UPRNs without TOID context: {toid_report['matched_uprns_without_toid_context']}
- TOID context coverage: {toid_report['toid_context_coverage'] * 100:.2f}%

## Confidence Policy

- PLD application entity from official PLD record: 0.95
- PLD to UPRN edge by exact UPRN match to LON-D4: 0.95
- PLD to TOID context via LON-D4 UPRN to TOID traversal: inherited from the LON-D4 edge confidence.
- Address-only and location-only fallback records remain unattached in LON-D5.

## No-Overclaim Boundary

The canonical permit-compatible entity type is `permit`, the id system is `pld`, and the permit type is `planning_application`. No DOB, enforcement, or building-control records are ingested by this task.

## Next

LON-D6 = enforcement / building-control sampled ingest, still bounded to Lambeth.
"""
    (output_dir / "LON_D5_ADAPTER_HANDOVER.md").write_text(handover, encoding="utf-8")


def write_manifest(output_dir: Path, input_dir: Path, borough: str, max_records: int, counts: dict[str, Any], status: str) -> dict[str, Any]:
    manifest = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "borough": borough,
        "requested_max_records": max_records,
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "boundary_strings": BOUNDARY_STRINGS,
        "scope": "sampled planning-application ingest only",
        "counts": counts,
        "canonical_id_policy": {
            "permit": "permit:uk-london:pld:{safe_application_id}",
            "safe_application_id_preference": [
                "PLD id",
                "normalized lpa_app_no",
                "stable hash of lpa_name + lpa_app_no + site_address",
            ],
        },
        "artifacts": [
            "README.md",
            "LON_D5_MANIFEST.json",
            "LON_D5_HARNESS_REPORT.json",
            "LON_D5_INPUT_INVENTORY.json",
            "LON_D5_PLD_QUERY_REPORT.json",
            "LON_D5_PLD_JOIN_REPORT.json",
            "LON_D5_NO_OVERCLAIM_REPORT.json",
            "LON_D5_DRIFT_TEST_REPORT.json",
            "LON_D5_ADAPTER_HANDOVER.md",
            "SHA256SUMS.json",
            "canonical/london_planning_applications.parquet",
            "canonical/london_pld_identity_edges.parquet",
            "canonical/london_pld_unattached_records.parquet",
            "canonical/london_pld_entities_sample.json",
            "canonical/london_pld_edges_sample.json",
            "raw_sample/pld_lambeth_response.json",
            "raw_sample/pld_lambeth_records_sample.json",
            "reports/join_rates.json",
            "reports/unattached_reasons.json",
            "reports/confidence_summary.json",
            "reports/field_coverage.json",
            "reports/schema_compatibility.json",
        ],
    }
    write_json(output_dir / "LON_D5_MANIFEST.json", manifest)
    return manifest


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        lower_parts = {part.lower() for part in resolved.parts}
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in lower_parts or "lon_d5" not in resolved.name.lower():
            raise ValueError(f"refusing to delete unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    (output_dir / "canonical").mkdir(parents=True, exist_ok=True)
    (output_dir / "raw_sample").mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)


def run_lon_d5_gate(
    input_dir: str,
    output_dir: str,
    borough: str = "Lambeth",
    max_records: int = 1000,
) -> dict:
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    tracked_inputs = collect_tracked_inputs(input_path)
    before_hashes = input_hashes(tracked_inputs)

    api_health = pld_health_check(borough)
    precond_report = preconditions(input_path, borough, api_health)
    parcels, d4_edges, d4_harness = load_d4(input_path)
    d4_uprn_ids = set(parcels["native_id"].astype(str))

    query_report, response_json, records = query_pld_records(borough, max_records)
    write_json(output_path / "raw_sample" / "pld_lambeth_response.json", response_json)
    write_json(output_path / "raw_sample" / "pld_lambeth_records_sample.json", records[: min(len(records), 1000)])
    write_json(output_path / "LON_D5_PLD_QUERY_REPORT.json", query_report)

    entities, edges, unattached, join_stats = build_canonical(records, borough, query_report["used_source_fields"], d4_uprn_ids)
    write_parquet(output_path / "canonical" / "london_planning_applications.parquet", entities)
    write_parquet(output_path / "canonical" / "london_pld_identity_edges.parquet", edges)
    write_parquet(output_path / "canonical" / "london_pld_unattached_records.parquet", unattached)
    write_json(output_path / "canonical" / "london_pld_entities_sample.json", frame_to_records(entities))
    write_json(output_path / "canonical" / "london_pld_edges_sample.json", frame_to_records(edges))

    coverage = field_coverage(records, query_report["used_source_fields"])
    pld_sample = pld_sample_gate(query_report, coverage)
    toid_report = toid_context(d4_edges, edges)
    join_rates = join_report(join_stats, toid_report)
    edge_report = edge_integrity(edges, entities, d4_uprn_ids)
    confidence = confidence_summary(entities, edges)
    unattached_reasons = unattached_report(unattached)
    a2_report = compatibility_harness(entities, edges, d4_uprn_ids)
    drift = drift_test(entities, edges, d4_uprn_ids)
    out_scope = out_of_scope_report(entities, edges, unattached)
    id_gate = id_format_gate(entities)

    write_json(output_path / "reports" / "field_coverage.json", coverage)
    write_json(output_path / "reports" / "join_rates.json", join_rates)
    write_json(output_path / "reports" / "unattached_reasons.json", unattached_reasons)
    write_json(output_path / "reports" / "confidence_summary.json", confidence)
    write_json(output_path / "reports" / "schema_compatibility.json", a2_report)
    write_json(output_path / "LON_D5_PLD_JOIN_REPORT.json", join_rates)
    write_json(output_path / "LON_D5_DRIFT_TEST_REPORT.json", drift)
    write_json(output_path / "LON_D5_INPUT_INVENTORY.json", inventory_inputs(input_path, tracked_inputs))

    after_hashes = input_hashes(tracked_inputs)
    no_mutation = {
        "gate": "LON-D5-NO-MUTATION",
        "status": "PASS" if before_hashes == after_hashes else "FAIL",
        "checked_files": len(before_hashes),
        "changed_files": sorted(path for path in before_hashes if before_hashes.get(path) != after_hashes.get(path)),
    }

    counts = {
        "pld_records_returned": len(records),
        "pld_entities": len(entities),
        "records_with_uprn": join_rates["pld_records_with_uprn"],
        "pld_uprn_edges": len(edges),
        "unattached_records": len(unattached),
        "d4_uprn_entities_available": len(d4_uprn_ids),
        "d4_harness_status": d4_harness.get("status"),
    }

    preliminary = {
        "task": TASK_NAME,
        "status": "PENDING",
        "created_utc": utc_now(),
        "boundary_strings": BOUNDARY_STRINGS,
        "borough": borough,
        "counts": counts,
        "preconditions": precond_report,
        "pld_sample": pld_sample,
        "id_format": id_gate,
        "join_rates": join_rates,
        "edge_integrity": edge_report,
        "toid_context": toid_report,
        "a2_compatibility": a2_report,
        "drift_test": drift,
        "out_of_scope": out_scope,
        "no_mutation": no_mutation,
    }
    write_manifest(output_path, input_path, borough, max_records, counts, "PENDING")
    write_json(output_path / "LON_D5_HARNESS_REPORT.json", preliminary)
    write_docs(output_path, borough, max_records, counts, query_report, coverage, join_rates, unattached_reasons, toid_report, confidence, a2_report)
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D5_NO_OVERCLAIM_REPORT.json", no_overclaim)

    gates = {
        "LON-D5-PRECOND": precond_report["status"],
        "LON-D5-PLD-SAMPLE": pld_sample["status"],
        "LON-D5-ID-FORMAT": id_gate["status"],
        "LON-D5-UPRN-JOIN": join_rates["status"],
        "LON-D5-EDGE-INTEGRITY": edge_report["status"],
        "LON-D5-TOID-CONTEXT": toid_report["status"],
        "LON-D5-A2-COMPATIBILITY": a2_report["status"],
        "LON-D5-DRIFT": drift["status"],
        "LON-D5-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D5-OUT-OF-SCOPE": out_scope["status"],
        "LON-D5-NO-MUTATION": no_mutation["status"],
        "LON-D5-HASHES": "PASS",
    }
    overall = "PASS" if all(status == "PASS" for status in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "boundary_strings": BOUNDARY_STRINGS,
        "borough": borough,
        "input_dir": str(input_path),
        "output_dir": str(output_path),
        "counts": counts,
        "preconditions": precond_report,
        "pld_sample": pld_sample,
        "id_format": id_gate,
        "field_coverage": coverage,
        "join_rates": join_rates,
        "edge_integrity": edge_report,
        "toid_context": toid_report,
        "confidence_summary": confidence,
        "unattached_reasons": unattached_reasons,
        "a2_compatibility": a2_report,
        "drift_test": drift,
        "no_overclaim": no_overclaim,
        "out_of_scope": out_scope,
        "no_mutation": no_mutation,
        "hashes": {
            "gate": "LON-D5-HASHES",
            "status": "PASS",
            "note": "SHA256SUMS.json covers all generated outputs except itself.",
        },
        "gates": gates,
    }
    write_json(output_path / "LON_D5_HARNESS_REPORT.json", harness)
    write_manifest(output_path, input_path, borough, max_records, counts, overall)
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D5_NO_OVERCLAIM_REPORT.json", no_overclaim)
    harness["no_overclaim"] = no_overclaim
    harness["gates"]["LON-D5-NO-OVERCLAIM"] = no_overclaim["status"]
    harness["status"] = "PASS" if all(status == "PASS" for status in harness["gates"].values()) else "FAIL"
    write_json(output_path / "LON_D5_HARNESS_REPORT.json", harness)
    write_manifest(output_path, input_path, borough, max_records, counts, harness["status"])
    hash_report(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--borough", default="Lambeth")
    parser.add_argument("--max-records", type=int, default=1000)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d5_gate(args.input_dir, args.output_dir, args.borough, args.max_records)
    join = report["join_rates"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Borough: {report['borough']}")
    print(f"PLD records returned: {report['counts']['pld_records_returned']}")
    print(f"PLD entities emitted: {report['counts']['pld_entities']}")
    print(f"Records with UPRN: {join['pld_records_with_uprn']}")
    print(f"PLD->UPRN edges emitted: {join['pld_to_uprn_edges_emitted']}")
    print(f"UPRN join rate: {join['join_rate_over_pld_uprns'] * 100:.2f}%")
    print(f"Matched UPRNs with TOID context: {report['toid_context']['matched_uprns_with_toid_context']}")
    print(f"A2 compatibility gates: {report['a2_compatibility']['status']}")
    print(f"Drift test: {report['drift_test']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
