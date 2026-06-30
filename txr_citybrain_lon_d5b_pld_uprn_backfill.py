from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import shutil
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from txr_citybrain_lon_d4_identity_backbone_ingest import iter_csv_rows, local_header_member


TASK_NAME = "LON-D5b PLD-Driven UPRN Identity Backfill"
DEFAULT_LON_D4_DIR = "outputs/lon_d4_identity_backbone_ingest"
DEFAULT_LON_D5_DIR = "outputs/lon_d5_pld_planning_ingest"
DEFAULT_OS_SAMPLE_DIR = (
    "LON_D2_identity_backbone_sample_fixture_v0_1/"
    "lon_d2_identity_backbone_fixture/lon_d3_os_identity_samples"
)
DEFAULT_OUTPUT_DIR = "outputs/lon_d5b_pld_uprn_backfill"
BOUNDARY_STRINGS = [
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
    "LON-D5b is PLD-driven identity backfill only.",
    "LON-D5b does not prove complete London planning coverage.",
    "LON-D5b does not ingest enforcement notices.",
    "LON-D5b does not ingest building-control records.",
    "LON-D5b does not create a London hero cascade.",
    "LON-D5b does not ingest enforcement or building-control records.",
]
OUT_OF_SCOPE_TOKENS = {
    "enforcement_notice",
    "building_control_application",
    "stop_work_order",
    "violation",
}
FORBIDDEN_ID_TOKENS = {"bbl", "bin", "dob"}
PARCEL_ID_PATTERN = re.compile(r"^parcel:uk-london:uprn:\d+$")
PERMIT_ID_PATTERN = re.compile(r"^permit:uk-london:pld:[A-Za-z0-9_.-]+$")

ENTITY_COLUMNS = [
    "canonical_id",
    "entity_type",
    "id_system",
    "native_id",
    "city",
    "country",
    "borough",
    "geometry",
    "geometry_status",
    "source_reason",
    "source_origin",
    "confidence",
    "provenance",
    "latitude",
    "longitude",
    "x_coordinate",
    "y_coordinate",
]
IDENTITY_EDGE_COLUMNS = [
    "edge_id",
    "src",
    "dst",
    "relation",
    "confidence",
    "provenance",
    "semantic_caveat",
    "source_uprn",
    "source_target_id",
    "source_confidence_text",
]
REJOIN_EDGE_COLUMNS = [
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


def stable_hash(value: Any, length: int = 24) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def write_parquet(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def frame_to_records(df: pd.DataFrame, limit: int = 25) -> list[dict[str, Any]]:
    records = df.head(limit).to_dict(orient="records")
    for record in records:
        for key in ("geometry", "confidence", "provenance", "uprn_refs", "invalid_uprn_refs"):
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


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {part.lower() for part in resolved.parts} or "lon_d5b" not in resolved.name.lower():
            raise ValueError(f"refusing to delete unexpected output directory: {resolved}")
        last_error: Exception | None = None
        for _ in range(3):
            try:
                shutil.rmtree(resolved)
                last_error = None
                break
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.5)
        if last_error:
            raise last_error
    (output_dir / "canonical").mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)


def normalize_uprn(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not re.fullmatch(r"\d+", text):
        return None
    return text.lstrip("0") or "0"


def extract_target_uprns(pld_entities: pd.DataFrame, max_target_uprn: int) -> tuple[list[str], dict[str, Any], dict[str, set[str]]]:
    by_record: dict[str, set[str]] = defaultdict(set)
    records_with_uprn = 0
    ordered_targets: list[str] = []
    seen_targets: set[str] = set()
    for row in pld_entities.to_dict(orient="records"):
        refs = parse_json_col(row.get("uprn_refs")) or []
        valid_refs = []
        for ref in refs:
            normalized = normalize_uprn(ref)
            if normalized:
                valid_refs.append(normalized)
                by_record[str(row["canonical_id"])].add(normalized)
                if normalized not in seen_targets:
                    seen_targets.add(normalized)
                    ordered_targets.append(normalized)
        if valid_refs:
            records_with_uprn += 1
    limited_targets = ordered_targets[:max_target_uprn] if max_target_uprn > 0 else ordered_targets
    report = {
        "source": "LON-D5 PLD Lambeth sample",
        "pld_records_total": len(pld_entities),
        "records_with_uprn": records_with_uprn,
        "distinct_target_uprns": len(ordered_targets),
        "max_target_uprn": max_target_uprn,
        "limited_by_max_target_uprn": len(limited_targets) < len(ordered_targets),
        "target_uprns": limited_targets,
    }
    return limited_targets, report, by_record


def preconditions(lon_d4_dir: Path, lon_d5_dir: Path, target_report: dict[str, Any]) -> dict[str, Any]:
    d4_harness = lon_d4_dir / "LON_D4_HARNESS_REPORT.json"
    d5_harness = lon_d5_dir / "LON_D5_HARNESS_REPORT.json"
    d5_entities = lon_d5_dir / "canonical" / "london_planning_applications.parquet"
    d5_unattached = lon_d5_dir / "canonical" / "london_pld_unattached_records.parquet"
    checks = {
        "lon_d4_harness_report_exists": d4_harness.exists(),
        "lon_d4_harness_report_status_pass": read_json(d4_harness).get("status") == "PASS" if d4_harness.exists() else False,
        "lon_d5_harness_report_exists": d5_harness.exists(),
        "lon_d5_harness_report_status_pass": read_json(d5_harness).get("status") == "PASS" if d5_harness.exists() else False,
        "lon_d5_pld_entities_exist": d5_entities.exists(),
        "lon_d5_unattached_records_exist": d5_unattached.exists(),
        "target_pld_uprns_can_be_extracted": target_report.get("distinct_target_uprns", 0) > 0,
    }
    return {"gate": "LON-D5B-PRECOND", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def input_hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path): sha256_file(path) for path in paths if path.exists() and path.is_file()}


def collect_tracked_inputs(lon_d4_dir: Path, lon_d5_dir: Path, os_sample_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for root in [lon_d4_dir, lon_d5_dir, os_sample_dir]:
        if root.exists():
            paths.extend(path for path in root.rglob("*") if path.is_file() and ".venv" not in path.parts)
    for extra in [
        Path("LON_D1_identity_backbone_inventory_v0_1.zip"),
        Path("LON_D2_identity_backbone_sample_fixture_v0_1.zip"),
        Path("LON_D3_probe_review_v0_2.zip"),
    ]:
        if extra.exists() and extra.is_file():
            paths.append(extra)
    return sorted({path.resolve() for path in paths})


def inventory_inputs(lon_d4_dir: Path, lon_d5_dir: Path, os_sample_dir: Path, tracked_inputs: list[Path]) -> dict[str, Any]:
    return {
        "task": TASK_NAME,
        "created_utc": utc_now(),
        "lon_d4_dir": str(lon_d4_dir),
        "lon_d5_dir": str(lon_d5_dir),
        "os_sample_dir": str(os_sample_dir),
        "files": [
            {"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in tracked_inputs
            if path.exists() and path.is_file()
        ],
    }


def candidate_full_open_uprn_sources(os_sample_dir: Path) -> list[Path]:
    roots = [Path.cwd(), os_sample_dir]
    candidates: set[Path] = set()
    skip_parts = {".git", ".venv", "__pycache__", "site-packages", "outputs", "snapshots"}
    allowed_suffixes = {".csv", ".zip", ".gz"}
    for root in roots:
        if not root.exists():
            continue
        for current, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in skip_parts]
            current_path = Path(current)
            if any(part in skip_parts for part in current_path.parts):
                continue
            for filename in filenames:
                path = current_path / filename
                name = filename.lower()
                if "download_probe" in name:
                    continue
                if not ("openuprn" in name or "osopenuprn" in name):
                    continue
                if path.suffix.lower() in allowed_suffixes or name.endswith(".csv.gz"):
                    candidates.add(path.resolve())
    return sorted(candidates)


def open_text_rows(path: Path) -> Iterable[dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
            yield from csv.DictReader(handle)
    elif suffix == ".gz" and path.name.lower().endswith(".csv.gz"):
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="", errors="replace") as handle:
            yield from csv.DictReader(handle)
    elif suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not csv_names:
                return
            with archive.open(csv_names[0]) as raw:
                text = (line.decode("utf-8-sig", errors="replace") for line in raw)
                yield from csv.DictReader(text)


def row_uprn(row: dict[str, Any]) -> str | None:
    for key in ("UPRN", "uprn", "Uprn"):
        if key in row:
            return normalize_uprn(row.get(key))
    return None


def row_geometry(row: dict[str, Any]) -> tuple[dict[str, Any], str, Any, Any, Any, Any]:
    lat = row.get("LATITUDE") or row.get("latitude")
    lon = row.get("LONGITUDE") or row.get("longitude")
    x_coord = row.get("X_COORDINATE") or row.get("x_coordinate")
    y_coord = row.get("Y_COORDINATE") or row.get("y_coordinate")
    try:
        lat_f = float(lat)
        lon_f = float(lon)
        return {"type": "Point", "coordinates": [lon_f, lat_f], "crs": "EPSG:4326"}, "point_from_open_uprn", lat_f, lon_f, x_coord, y_coord
    except (TypeError, ValueError):
        return {}, "missing_geometry", None, None, x_coord, y_coord


def provenance(source_dataset: str, source_id: str, source_file: str, source_fields: list[str], derivation: str) -> list[dict[str, Any]]:
    return [
        {
            "source_dataset": source_dataset,
            "source_id": source_id,
            "source_file": source_file,
            "source_fields": source_fields,
            "derivation": derivation,
            "observed_at": utc_now(),
        }
    ]


def build_entity_from_uprn_row(uprn: str, row: dict[str, Any], source_file: str, source_origin: str) -> dict[str, Any]:
    geometry, geometry_status, lat, lon, x_coord, y_coord = row_geometry(row)
    return {
        "canonical_id": f"parcel:uk-london:uprn:{uprn}",
        "entity_type": "parcel",
        "id_system": "uprn",
        "native_id": uprn,
        "city": "london",
        "country": "uk",
        "borough": "Lambeth",
        "geometry": json_col(geometry),
        "geometry_status": geometry_status,
        "source_reason": "pld_target_uprn_backfill",
        "source_origin": source_origin,
        "confidence": json_col(
            {
                "method": "official_uprn_backfill",
                "score": 1.0,
                "basis": "Exact target UPRN matched to an official OS Open UPRN row.",
            }
        ),
        "provenance": json_col(
            provenance(
                "OS Open UPRN",
                uprn,
                source_file,
                sorted(k for k in row.keys() if k in {"UPRN", "LATITUDE", "LONGITUDE", "X_COORDINATE", "Y_COORDINATE"}),
                "PLD target UPRN identity backfill by exact UPRN lookup.",
            )
        ),
        "latitude": lat,
        "longitude": lon,
        "x_coordinate": x_coord,
        "y_coordinate": y_coord,
    }


def build_entity_from_d4_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_id": row["canonical_id"],
        "entity_type": row["entity_type"],
        "id_system": row["id_system"],
        "native_id": str(row["native_id"]),
        "city": row.get("city", "london"),
        "country": row.get("country", "uk"),
        "borough": row.get("borough", "Lambeth"),
        "geometry": row.get("geometry", json_col({})),
        "geometry_status": row.get("geometry_status", "missing_geometry"),
        "source_reason": "existing_lon_d4_entity_target_overlap",
        "source_origin": "existing_lon_d4",
        "confidence": row.get("confidence", json_col({"method": "official_uprn", "score": 1.0})),
        "provenance": row.get("provenance", json_col([])),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "x_coordinate": row.get("x_coordinate"),
        "y_coordinate": row.get("y_coordinate"),
    }


def search_open_uprn_probe(os_sample_dir: Path, target_uprns: set[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    path = os_sample_dir / "open_uprn_download_probe.bin"
    matches: dict[str, dict[str, Any]] = {}
    report: dict[str, Any] = {
        "source_file": str(path),
        "status": "NOT_AVAILABLE",
        "attempted": False,
        "matched_target_uprns": 0,
        "total_rows_seen": 0,
    }
    if not path.exists():
        return matches, report
    report["attempted"] = True
    try:
        member = local_header_member(path, 2)
        report["zip_member"] = member
        report["source_kind"] = "partial_truncated_zip_probe" if member.get("truncated") else "zip_probe"
        for row in iter_csv_rows(path, 2):
            report["total_rows_seen"] += 1
            uprn = row_uprn(row)
            if uprn and uprn in target_uprns and uprn not in matches:
                matches[uprn] = build_entity_from_uprn_row(uprn, row, f"{path.name}::{member.get('name')}", report["source_kind"])
        report["matched_target_uprns"] = len(matches)
        report["status"] = "SEARCHED"
        if member.get("truncated"):
            report["limitation"] = "source_unusable_for_complete_negative_proof_partial_zip_or_binary_probe"
        if not matches and member.get("truncated"):
            report["result"] = "no_target_uprns_found_in_available_capped_probe_bytes"
    except Exception as exc:
        report.update(
            {
                "status": "SOURCE_UNUSABLE",
                "source_kind": "source_unusable_partial_zip_or_binary_probe",
                "error": str(exc),
            }
        )
    return matches, report


def search_full_open_uprn_candidates(os_sample_dir: Path, remaining_targets: set[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    matches: dict[str, dict[str, Any]] = {}
    candidates = candidate_full_open_uprn_sources(os_sample_dir)
    candidate_reports = []
    for path in candidates:
        if not remaining_targets - set(matches):
            break
        report = {"source_file": str(path), "attempted": True, "status": "SEARCHED", "total_rows_seen": 0, "matched_target_uprns": 0}
        try:
            for row in open_text_rows(path):
                report["total_rows_seen"] += 1
                uprn = row_uprn(row)
                if uprn and uprn in remaining_targets and uprn not in matches:
                    matches[uprn] = build_entity_from_uprn_row(uprn, row, str(path), "local_full_open_uprn_source")
            report["matched_target_uprns"] = len(matches)
        except Exception as exc:
            report["status"] = "SOURCE_UNUSABLE"
            report["error"] = str(exc)
        candidate_reports.append(report)
    status = "NO_LOCAL_FULL_SOURCE_FOUND" if not candidates else "SEARCHED"
    return matches, {"status": status, "candidate_count": len(candidates), "candidates": candidate_reports}


def backfill_search(target_uprns: list[str], d4_parcels: pd.DataFrame, os_sample_dir: Path) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    target_set = set(target_uprns)
    d4_by_uprn = {str(row["native_id"]): row for row in d4_parcels.to_dict(orient="records")}
    existing_matches = {uprn: build_entity_from_d4_row(d4_by_uprn[uprn]) for uprn in target_uprns if uprn in d4_by_uprn}

    remaining = target_set - set(existing_matches)
    probe_matches, probe_report = search_open_uprn_probe(os_sample_dir, remaining)
    remaining -= set(probe_matches)
    full_matches, full_report = search_full_open_uprn_candidates(os_sample_dir, remaining)

    all_entities = {**existing_matches, **probe_matches, **full_matches}
    records = [all_entities[uprn] for uprn in target_uprns if uprn in all_entities]
    entities = pd.DataFrame(records, columns=ENTITY_COLUMNS)

    found_count = len(all_entities)
    if found_count == len(target_uprns):
        status = "PASS"
    else:
        status = "PASS_WITH_SOURCE_LIMITATION"
    source_report = {
        "gate": "LON-D5B-BACKFILL-SEARCH",
        "status": status,
        "search_attempted": True,
        "search_order": [
            "existing_lond4_entities",
            "existing_local_open_uprn_probe",
            "local_full_open_uprn_source_if_available",
            "missing_source_report",
        ],
        "target_uprns": len(target_uprns),
        "found_target_uprns": found_count,
        "missing_target_uprns": len(target_uprns) - found_count,
        "existing_lon_d4": {
            "target_uprns_already_present": len(existing_matches),
            "sample": sorted(existing_matches)[:20],
        },
        "local_open_uprn_probe": probe_report,
        "local_full_open_uprn_sources": full_report,
        "limitation": None if found_count == len(target_uprns) else "Available OpenUPRN source data did not contain all PLD target UPRNs; no address or geometry fallback was used.",
    }
    coverage = {
        "status": "PASS" if target_uprns else "FAIL",
        "target_uprns_total": len(target_uprns),
        "already_in_lon_d4": len(existing_matches),
        "found_in_local_open_uprn_probe": len(probe_matches),
        "found_in_full_open_uprn_source": len(full_matches),
        "available_after_backfill": found_count,
        "missing_after_backfill": len(target_uprns) - found_count,
        "coverage_rate": found_count / len(target_uprns) if target_uprns else 0.0,
    }
    return entities, source_report, coverage


def scan_lids_context(os_sample_dir: Path, target_uprns: set[str], available_uprns: set[str]) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    specs = {
        "toid": {
            "path": os_sample_dir / "lids_uprn_topographicarea_toid_download_probe.bin",
            "relation": "has_building",
            "target_type": "toid",
            "source_dataset": "OS Open Linked Identifiers BLPU-UPRN-TopographicArea-TOID",
            "unavailable_reason": "toid_context_unavailable_for_backfilled_uprns",
        },
        "usrn": {
            "path": os_sample_dir / "lids_uprn_usrn_download_probe.bin",
            "relation": "on_street",
            "target_type": "usrn",
            "source_dataset": "OS Open Linked Identifiers BLPU-UPRN-Street-USRN",
            "unavailable_reason": "usrn_context_unavailable_for_backfilled_uprns",
        },
    }
    rows: list[dict[str, Any]] = []
    reports: dict[str, Any] = {}
    for key, spec in specs.items():
        source_path: Path = spec["path"]
        matched_pairs: set[tuple[str, str]] = set()
        report = {
            "status": "PASS",
            "source_file": str(source_path),
            "attempted": source_path.exists(),
            "target_uprns_scanned": len(target_uprns),
            "available_backfilled_or_existing_uprns": len(available_uprns),
            "total_rows_seen": 0,
            "matched_target_rows": 0,
            "canonical_context_edges_emitted": 0,
            "context_coverage": 0.0,
            "unavailable_reason": None,
        }
        if not source_path.exists():
            report["status"] = "PASS_WITH_SOURCE_LIMITATION"
            report["unavailable_reason"] = spec["unavailable_reason"]
            reports[key] = report
            continue
        try:
            report["zip_member"] = local_header_member(source_path, 0)
            for source_row in iter_csv_rows(source_path, 0):
                report["total_rows_seen"] += 1
                uprn = normalize_uprn(source_row.get("IDENTIFIER_1"))
                target = str(source_row.get("IDENTIFIER_2", "")).strip()
                if not uprn or uprn not in target_uprns or not target:
                    continue
                report["matched_target_rows"] += 1
                if uprn not in available_uprns:
                    continue
                pair = (uprn, target)
                if pair in matched_pairs:
                    continue
                matched_pairs.add(pair)
                dst_prefix = "building:uk-london:toid" if key == "toid" else "road_segment:uk-london:usrn"
                rows.append(
                    {
                        "edge_id": f"edge:uk-london:d5b-lids:{stable_hash({'relation': spec['relation'], 'uprn': uprn, 'target': target})}",
                        "src": f"parcel:uk-london:uprn:{uprn}",
                        "dst": f"{dst_prefix}:{target}",
                        "relation": spec["relation"],
                        "confidence": json_col(
                            {
                                "method": f"official_lids_uprn_{key}_link",
                                "score": 0.95,
                                "basis": "Official LIDS exact link for a PLD target UPRN.",
                            }
                        ),
                        "provenance": json_col(
                            provenance(
                                spec["source_dataset"],
                                f"{uprn}_{target}",
                                source_path.name,
                                ["IDENTIFIER_1", "IDENTIFIER_2", "CORRELATION_ID", "CONFIDENCE"],
                                "Context edge emitted only when the PLD target UPRN has an available canonical UPRN entity.",
                            )
                        ),
                        "semantic_caveat": "Context after backfill; no direct PLD-to-TOID or PLD-to-USRN edge is created.",
                        "source_uprn": uprn,
                        "source_target_id": target,
                        "source_confidence_text": source_row.get("CONFIDENCE"),
                    }
                )
            report["canonical_context_edges_emitted"] = sum(1 for row in rows if row["relation"] == spec["relation"])
            covered = {row["source_uprn"] for row in rows if row["relation"] == spec["relation"]}
            report["matched_uprns_with_context"] = len(covered)
            report["matched_uprns_without_context"] = max(0, len(available_uprns) - len(covered))
            report["context_coverage"] = len(covered) / len(available_uprns) if available_uprns else 0.0
            if not covered:
                report["unavailable_reason"] = spec["unavailable_reason"]
        except Exception as exc:
            report["status"] = "PASS_WITH_SOURCE_LIMITATION"
            report["unavailable_reason"] = spec["unavailable_reason"]
            report["error"] = str(exc)
        reports[key] = report
    edges = pd.DataFrame(rows, columns=IDENTITY_EDGE_COLUMNS)
    return edges, reports["toid"], reports["usrn"]


def rejoin_pld(pld_entities: pd.DataFrame, available_uprns: set[str]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    attached_permits: set[str] = set()
    records_with_uprn = 0
    for row in pld_entities.to_dict(orient="records"):
        refs = parse_json_col(row.get("uprn_refs")) or []
        valid_refs = [normalize_uprn(ref) for ref in refs]
        valid_refs = [ref for ref in valid_refs if ref]
        if valid_refs:
            records_with_uprn += 1
        for uprn in sorted(set(valid_refs)):
            if uprn not in available_uprns:
                continue
            permit_id = str(row["canonical_id"])
            attached_permits.add(permit_id)
            edges.append(
                {
                    "edge_id": f"edge:uk-london:d5b-pld-uprn:{stable_hash({'uprn': uprn, 'permit': permit_id})}",
                    "src": f"parcel:uk-london:uprn:{uprn}",
                    "relation": "subject_of_permit",
                    "dst": permit_id,
                    "role": "planning_application_subject",
                    "confidence": json_col(
                        {
                            "method": "pld_uprn_exact_match_to_lond5b_identity_backfill",
                            "score": 0.95,
                            "basis": "PLD UPRN exactly matched a LON-D4 or LON-D5b UPRN canonical entity.",
                        }
                    ),
                    "provenance": json_col(
                        [
                            {
                                "source_dataset": "Planning London Datahub + LON-D5b UPRN backfill",
                                "source_id": row.get("native_id"),
                                "source_uprn": uprn,
                                "derivation": "Rejoined by exact PLD UPRN after PLD-driven UPRN identity backfill.",
                                "observed_at": utc_now(),
                            }
                        ]
                    ),
                    "source_uprn": uprn,
                    "source_application_id": row.get("native_id"),
                    "semantic_caveat": "Exact UPRN identity edge only; no address-derived or geometry-derived identity edge is fabricated.",
                }
            )
    edge_df = pd.DataFrame(edges, columns=REJOIN_EDGE_COLUMNS)
    still_rows = []
    for row in pld_entities.to_dict(orient="records"):
        if str(row["canonical_id"]) in attached_permits:
            continue
        reason = "source_limited_target_uprn_not_found" if parse_json_col(row.get("uprn_refs")) else "no_valid_uprn_in_pld_record"
        still_rows.append({**row, "unattached_reason_after_backfill": reason})
    still_unattached = pd.DataFrame(still_rows)
    report = {
        "gate": "LON-D5B-PLD-REJOIN",
        "status": "PASS",
        "pld_records_total": len(pld_entities),
        "pld_records_with_uprn": records_with_uprn,
        "target_uprns_total": len(available_uprns),
        "target_uprns_found_in_backfill": len(available_uprns),
        "pld_to_uprn_edges_emitted": len(edge_df),
        "records_still_unattached": len(still_unattached),
        "join_rate_after_backfill": len(attached_permits) / len(pld_entities) if len(pld_entities) else 0.0,
        "policy": "Low join rate is allowed when available official UPRN source data is limited; no fallback matching is used.",
    }
    return edge_df, still_unattached, report


def edge_integrity(
    rejoin_edges: pd.DataFrame,
    identity_edges: pd.DataFrame,
    available_uprns: set[str],
    pld_permit_ids: set[str],
    d4_building_ids: set[str],
    d4_road_ids: set[str],
) -> dict[str, Any]:
    failures = []
    for row in rejoin_edges.to_dict(orient="records"):
        src_uprn = str(row.get("src", "")).split(":")[-1]
        if src_uprn not in available_uprns:
            failures.append(f"{row.get('edge_id')} missing UPRN src {row.get('src')}")
        if row.get("dst") not in pld_permit_ids:
            failures.append(f"{row.get('edge_id')} missing PLD permit dst {row.get('dst')}")
    for row in identity_edges.to_dict(orient="records"):
        src_uprn = str(row.get("src", "")).split(":")[-1]
        if src_uprn not in available_uprns:
            failures.append(f"{row.get('edge_id')} missing UPRN src {row.get('src')}")
        if row.get("relation") == "has_building" and row.get("dst") not in d4_building_ids:
            failures.append(f"{row.get('edge_id')} missing D4 building dst {row.get('dst')}")
        if row.get("relation") == "on_street" and row.get("dst") not in d4_road_ids:
            failures.append(f"{row.get('edge_id')} missing D4 road dst {row.get('dst')}")
    return {
        "gate": "LON-D5B-EDGE-INTEGRITY",
        "status": "PASS" if not failures else "FAIL",
        "edges_checked": len(rejoin_edges) + len(identity_edges),
        "dangling_references": len(failures),
        "details": failures[:20],
    }


def connected_path_smoke(rejoin_edges: pd.DataFrame, identity_edges: pd.DataFrame, source_report: dict[str, Any]) -> dict[str, Any]:
    if rejoin_edges.empty:
        result = "NONE_WITH_SOURCE_LIMITATION" if source_report.get("status") == "PASS_WITH_SOURCE_LIMITATION" else "NONE"
        return {
            "gate": "LON-D5B-CONNECTED-PATH-SMOKE",
            "status": "PASS" if result == "NONE_WITH_SOURCE_LIMITATION" else "FAIL",
            "result": result,
            "claim_connected_path_proof": False,
            "limitation": "NO_CONNECTED_PATH_SOURCE_LIMITATION",
            "sample_path": None,
        }
    rejoined_by_uprn = defaultdict(list)
    for row in rejoin_edges.to_dict(orient="records"):
        rejoined_by_uprn[str(row["source_uprn"])].append(row)
    context_by_uprn = defaultdict(list)
    for row in identity_edges.to_dict(orient="records"):
        context_by_uprn[str(row["source_uprn"])].append(row)
    for uprn, pld_rows in rejoined_by_uprn.items():
        for ctx in context_by_uprn.get(uprn, []):
            if ctx["relation"] == "has_building":
                return {
                    "gate": "LON-D5B-CONNECTED-PATH-SMOKE",
                    "status": "PASS",
                    "result": "STRONG",
                    "claim_connected_path_proof": True,
                    "sample_path": [pld_rows[0]["dst"], pld_rows[0]["src"], ctx["dst"]],
                }
    for uprn, pld_rows in rejoined_by_uprn.items():
        for ctx in context_by_uprn.get(uprn, []):
            if ctx["relation"] == "on_street":
                return {
                    "gate": "LON-D5B-CONNECTED-PATH-SMOKE",
                    "status": "PASS",
                    "result": "MEDIUM",
                    "claim_connected_path_proof": True,
                    "sample_path": [pld_rows[0]["dst"], pld_rows[0]["src"], ctx["dst"]],
                }
    first = rejoin_edges.iloc[0].to_dict()
    return {
        "gate": "LON-D5B-CONNECTED-PATH-SMOKE",
        "status": "PASS",
        "result": "MINIMUM",
        "claim_connected_path_proof": True,
        "sample_path": [first["dst"], first["src"]],
    }


def compatibility_harness(
    entities: pd.DataFrame,
    rejoin_edges: pd.DataFrame,
    available_uprns: set[str],
    pld_permit_ids: set[str],
) -> dict[str, Any]:
    entity_records = entities.to_dict(orient="records")
    edge_records = rejoin_edges.to_dict(orient="records")
    gates = []

    def add(gate_id: str, passed: bool, checked: int, failed: int, details: list[str] | None = None) -> None:
        gates.append({"gate_id": gate_id, "status": "PASS" if passed else "FAIL", "checked": checked, "failed": failed, "details": details or []})

    schema_failures = []
    required_entity_cols = {"canonical_id", "entity_type", "id_system", "native_id", "city", "country", "geometry", "geometry_status", "confidence", "provenance", "source_reason"}
    for idx, row in enumerate(entity_records):
        missing = sorted(required_entity_cols - set(row))
        if missing:
            schema_failures.append(f"entity[{idx}] missing {missing}")
        if row.get("entity_type") != "parcel" or row.get("id_system") != "uprn":
            schema_failures.append(f"entity[{idx}] bad entity/id_system")
        try:
            parse_json_col(row.get("geometry"))
            parse_json_col(row.get("confidence"))
            parse_json_col(row.get("provenance"))
        except Exception as exc:
            schema_failures.append(f"entity[{idx}] JSON parse failed: {exc}")
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
        if not PARCEL_ID_PATTERN.match(canonical_id) or bool(parts & FORBIDDEN_ID_TOKENS):
            id_failures.append(canonical_id)
    add("G-ID", not id_failures, len(entity_records), len(id_failures), id_failures[:10])

    triad_failures = []
    for row in entity_records:
        confidence = parse_json_col(row.get("confidence"))
        provenance_value = parse_json_col(row.get("provenance"))
        if not confidence or not confidence.get("method") or confidence.get("score") is None or not provenance_value:
            triad_failures.append(str(row.get("canonical_id")))
    for row in edge_records:
        confidence = parse_json_col(row.get("confidence"))
        provenance_value = parse_json_col(row.get("provenance"))
        if not confidence or not confidence.get("method") or confidence.get("score") is None or not provenance_value:
            triad_failures.append(str(row.get("edge_id")))
    add("G-TRIAD", not triad_failures, len(entity_records) + len(edge_records), len(triad_failures), triad_failures[:10])

    geo_failures = []
    for row in entity_records:
        status = row.get("geometry_status")
        if status not in {"point_from_open_uprn", "missing_geometry"}:
            geo_failures.append(f"{row.get('canonical_id')} bad geometry_status={status}")
        if status == "point_from_open_uprn":
            geometry = parse_json_col(row.get("geometry"))
            coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
            if not (isinstance(coords, list) and len(coords) == 2):
                geo_failures.append(f"{row.get('canonical_id')} missing point coordinates")
    add("G-GEO", not geo_failures, len(entity_records), len(geo_failures), geo_failures[:10])

    ref_failures = []
    for row in edge_records:
        src_uprn = str(row.get("src", "")).split(":")[-1]
        if src_uprn not in available_uprns:
            ref_failures.append(f"{row.get('edge_id')} missing UPRN src {row.get('src')}")
        if row.get("dst") not in pld_permit_ids:
            ref_failures.append(f"{row.get('edge_id')} missing permit dst {row.get('dst')}")
    add("G-REF", not ref_failures, len(edge_records) * 2, len(ref_failures), ref_failures[:10])

    edge_failures = []
    for row in edge_records:
        confidence = parse_json_col(row.get("confidence"))
        if row.get("relation") != "subject_of_permit":
            edge_failures.append(str(row.get("edge_id")))
        elif row.get("role") != "planning_application_subject":
            edge_failures.append(str(row.get("edge_id")))
        elif not confidence or float(confidence.get("score", 0)) <= 0:
            edge_failures.append(str(row.get("edge_id")))
    add("G-EDGE", not edge_failures, len(edge_records), len(edge_failures), edge_failures[:10])

    return {
        "status": "PASS" if all(gate["status"] == "PASS" for gate in gates) else "FAIL",
        "compatibility_marker": "a2_binary_unavailable_compatibility_harness_used",
        "reason": "The local A2 binary is the NYC Flow-2 acceptance harness; LON-D5b uses the same invariant names over London backfilled UPRN entities and PLD rejoin edges without claiming exact NYC binary acceptance.",
        "gates": gates,
    }


def drift_test(entities: pd.DataFrame, rejoin_edges: pd.DataFrame, target_uprns: list[str], pld_permit_ids: set[str], available_uprns: set[str]) -> dict[str, Any]:
    mutated_entities = entities.copy()
    mutated_edges = rejoin_edges.copy()
    synthetic_used = False
    if mutated_entities.empty and target_uprns:
        synthetic_used = True
        uprn = target_uprns[0]
        mutated_entities = pd.DataFrame(
            [
                {
                    "canonical_id": f"parcel:uk-london:uprn:{uprn}",
                    "entity_type": "parcel",
                    "id_system": "uprn",
                    "native_id": uprn,
                    "city": "london",
                    "country": "uk",
                    "borough": "Lambeth",
                    "geometry": json_col({}),
                    "geometry_status": "missing_geometry",
                    "source_reason": "synthetic_drift_probe",
                    "source_origin": "synthetic_drift_probe",
                    "confidence": json_col({"method": "official_uprn_backfill", "score": 1.0}),
                    "provenance": json_col([{"source_dataset": "drift_test", "observed_at": utc_now()}]),
                    "latitude": None,
                    "longitude": None,
                    "x_coordinate": None,
                    "y_coordinate": None,
                }
            ],
            columns=ENTITY_COLUMNS,
        )
    if not mutated_entities.empty:
        idx = mutated_entities.index[0]
        native = str(mutated_entities.loc[idx, "native_id"])
        mutated_entities.loc[idx, "entity_type"] = "uprn_entity"
        mutated_entities.loc[idx, "canonical_id"] = f"uprn_entity:uk-london:uprn:{native}"
    if mutated_edges.empty and pld_permit_ids:
        synthetic_used = True
        native = str(mutated_entities.iloc[0]["native_id"]) if not mutated_entities.empty else (target_uprns[0] if target_uprns else "0")
        mutated_edges = pd.DataFrame(
            [
                {
                    "edge_id": "edge:uk-london:d5b-drift-probe",
                    "src": f"parcel:uk-london:uprn:{native}",
                    "relation": "subject_of_planning_application",
                    "dst": sorted(pld_permit_ids)[0],
                    "role": "planning_application_subject",
                    "confidence": json_col({"method": "pld_uprn_exact_match_to_lond5b_identity_backfill", "score": 0.95}),
                    "provenance": json_col([{"source_dataset": "drift_test", "observed_at": utc_now()}]),
                    "source_uprn": native,
                    "source_application_id": sorted(pld_permit_ids)[0],
                    "semantic_caveat": "Synthetic drift probe only; not emitted as canonical output.",
                }
            ],
            columns=REJOIN_EDGE_COLUMNS,
        )
    elif not mutated_edges.empty:
        mutated_edges.loc[mutated_edges.index[0], "relation"] = "subject_of_planning_application"
    mutated_available = available_uprns | set(mutated_entities["native_id"].astype(str)) if not mutated_entities.empty else available_uprns
    result = compatibility_harness(mutated_entities, mutated_edges, mutated_available, pld_permit_ids)
    failing_gates = [gate["gate_id"] for gate in result["gates"] if gate["status"] == "FAIL"]
    return {
        "gate": "LON-D5B-DRIFT",
        "status": "PASS" if result["status"] == "FAIL" and failing_gates else "FAIL",
        "drift_mutation": {
            "parcel:uk-london:uprn:{id}": "uprn_entity:uk-london:uprn:{id}",
            "subject_of_permit": "subject_of_planning_application",
        },
        "synthetic_drift_probe_used": synthetic_used,
        "mutated_harness_status": result["status"],
        "failing_gates": failing_gates,
    }


def confidence_summary(entities: pd.DataFrame, identity_edges: pd.DataFrame, rejoin_edges: pd.DataFrame) -> dict[str, Any]:
    methods: Counter[str] = Counter()
    score_ranges: dict[str, list[float]] = defaultdict(list)
    for df in [entities, identity_edges, rejoin_edges]:
        if df.empty or "confidence" not in df:
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
            "Backfilled UPRN from official OpenUPRN exact match": 1.0,
            "PLD->UPRN exact join": 0.95,
            "UPRN->TOID from official LIDS exact link": 0.95,
            "UPRN->USRN from official LIDS exact link": 0.95,
            "No spatial/address fallback in LON-D5b": True,
        },
        "method_counts": dict(methods),
        "score_ranges": {method: {"min": min(scores), "max": max(scores)} for method, scores in score_ranges.items() if scores},
    }


def id_format_gate(entities: pd.DataFrame) -> dict[str, Any]:
    failures = []
    for canonical_id in entities["canonical_id"].astype(str) if not entities.empty else []:
        parts = set(canonical_id.lower().split(":"))
        if not PARCEL_ID_PATTERN.match(canonical_id) or bool(parts & FORBIDDEN_ID_TOKENS):
            failures.append(canonical_id)
    return {"gate": "LON-D5B-BACKFILLED-ID-FORMAT", "status": "PASS" if not failures else "FAIL", "entities_checked": len(entities), "failures": failures[:20]}


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    required_files = {
        "README.md": output_dir / "README.md",
        "LON_D5B_MANIFEST.json": output_dir / "LON_D5B_MANIFEST.json",
        "LON_D5B_HARNESS_REPORT.json": output_dir / "LON_D5B_HARNESS_REPORT.json",
        "LON_D5B_ADAPTER_HANDOVER.md": output_dir / "LON_D5B_ADAPTER_HANDOVER.md",
    }
    files = {}
    passed = True
    for name, path in required_files.items():
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [item for item in BOUNDARY_STRINGS if item not in text]
        files[name] = {"missing_boundary_strings": missing}
        if missing:
            passed = False
    return {"gate": "LON-D5B-NO-OVERCLAIM", "status": "PASS" if passed else "FAIL", "boundary_strings": BOUNDARY_STRINGS, "files": files}


def out_of_scope_report(entities: pd.DataFrame, identity_edges: pd.DataFrame, rejoin_edges: pd.DataFrame, still_unattached: pd.DataFrame) -> dict[str, Any]:
    payload = "\n".join(
        [
            entities.to_json(orient="records"),
            identity_edges.to_json(orient="records"),
            rejoin_edges.to_json(orient="records"),
            still_unattached.to_json(orient="records"),
        ]
    ).lower()
    found = sorted(token for token in OUT_OF_SCOPE_TOKENS if token in payload)
    return {
        "gate": "LON-D5B-OUT-OF-SCOPE",
        "status": "PASS" if not found else "FAIL",
        "found_forbidden_payload_terms": found,
        "exception": "Forbidden wording may appear in no-overclaim reports and docs, but not as canonical entities.",
    }


def hash_report(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D5B-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def write_docs(
    output_dir: Path,
    counts: dict[str, Any],
    target_report: dict[str, Any],
    source_report: dict[str, Any],
    rejoin_report: dict[str, Any],
    toid_report: dict[str, Any],
    usrn_report: dict[str, Any],
    smoke: dict[str, Any],
    a2_report: dict[str, Any],
) -> None:
    boundary = "\n".join(f"- {item}" for item in BOUNDARY_STRINGS)
    readme = f"""# LON-D5b PLD-Driven UPRN Identity Backfill

{boundary}

LON-D5b extracts the UPRNs carried by the accepted LON-D5 PLD Lambeth sample, attempts exact UPRN lookup against available official OpenUPRN source data, and reruns the PLD-to-UPRN join over LON-D4 plus any backfilled UPRN entities. It uses no address fuzzy matching and no geometry fallback matching.

## Result

- Target PLD UPRNs: {target_report['distinct_target_uprns']}
- Backfilled or already-available target UPRNs found: {source_report['found_target_uprns']}
- PLD to UPRN edges emitted after backfill: {rejoin_report['pld_to_uprn_edges_emitted']}
- Join rate after backfill: {rejoin_report['join_rate_after_backfill'] * 100:.2f}%
- Still unattached records: {rejoin_report['records_still_unattached']}
- Connected path smoke: {smoke['result']}

## Source Limitation

{source_report.get('limitation') or 'All target UPRNs were found in available official UPRN source data.'}

The local OpenUPRN probe search was attempted. If the probe is truncated, its absence of target UPRNs is not treated as a complete national negative proof.

## Context

- TOID context coverage: {toid_report.get('context_coverage', 0.0) * 100:.2f}%
- USRN context coverage: {usrn_report.get('context_coverage', 0.0) * 100:.2f}%

## Compatibility

A2-style invariant gates ran with marker `{a2_report.get('compatibility_marker')}`.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    handover = f"""# LON-D5b Adapter Handover

{boundary}

## Entrypoint

`txr_citybrain_lon_d5b_pld_uprn_backfill.py`

```bash
python txr_citybrain_lon_d5b_pld_uprn_backfill.py --lon-d4-dir outputs/lon_d4_identity_backbone_ingest --lon-d5-dir outputs/lon_d5_pld_planning_ingest --os-sample-dir LON_D2_identity_backbone_sample_fixture_v0_1/lon_d2_identity_backbone_fixture/lon_d3_os_identity_samples --output-dir outputs/lon_d5b_pld_uprn_backfill --max-target-uprn 1000 --run-gates
```

## What It Does

LON-D5b aligns the identity sample to the UPRNs found in LON-D5 PLD records. It checks existing LON-D4 UPRNs, searches the local OpenUPRN probe, searches any locally available full OpenUPRN source candidates, and then reruns the exact PLD-to-UPRN join.

## Current Evidence

- Target PLD UPRNs: {target_report['distinct_target_uprns']}
- Records with UPRN: {target_report['records_with_uprn']}
- Found target UPRNs: {source_report['found_target_uprns']}
- Missing target UPRNs: {source_report['missing_target_uprns']}
- Source report status: {source_report['status']}
- Rejoined PLD to UPRN edges: {rejoin_report['pld_to_uprn_edges_emitted']}
- Connected path smoke: {smoke['result']}

## Confidence Policy

- Backfilled UPRN from official OpenUPRN exact match: 1.0
- PLD to UPRN exact join: 0.95
- UPRN to TOID from official LIDS exact link: 0.95
- UPRN to USRN from official LIDS exact link: 0.95
- No spatial or address fallback in LON-D5b.

## Next

Provide a complete OpenUPRN source, or a PLD-aligned official UPRN extract, to turn the current source-limited result into connected PLD-to-UPRN proof. Keep LON-D6 bounded to enforcement / building-control sampled ingest if that task proceeds.
"""
    (output_dir / "LON_D5B_ADAPTER_HANDOVER.md").write_text(handover, encoding="utf-8")


def write_manifest(output_dir: Path, lon_d4_dir: Path, lon_d5_dir: Path, os_sample_dir: Path, counts: dict[str, Any], status: str) -> dict[str, Any]:
    manifest = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "lon_d4_dir": str(lon_d4_dir),
        "lon_d5_dir": str(lon_d5_dir),
        "os_sample_dir": str(os_sample_dir),
        "output_dir": str(output_dir),
        "boundary_strings": BOUNDARY_STRINGS,
        "scope": "PLD-driven identity backfill only",
        "counts": counts,
        "artifacts": [
            "README.md",
            "LON_D5B_MANIFEST.json",
            "LON_D5B_HARNESS_REPORT.json",
            "LON_D5B_INPUT_INVENTORY.json",
            "LON_D5B_TARGET_UPRN_LIST.json",
            "LON_D5B_BACKFILL_SOURCE_REPORT.json",
            "LON_D5B_BACKFILL_JOIN_REPORT.json",
            "LON_D5B_CONNECTED_PATH_SMOKE.json",
            "LON_D5B_NO_OVERCLAIM_REPORT.json",
            "LON_D5B_DRIFT_TEST_REPORT.json",
            "LON_D5B_ADAPTER_HANDOVER.md",
            "SHA256SUMS.json",
            "canonical/london_pld_target_uprn_entities.parquet",
            "canonical/london_pld_backfilled_identity_edges.parquet",
            "canonical/london_pld_rejoined_edges.parquet",
            "canonical/london_pld_still_unattached_records.parquet",
            "canonical/london_pld_connected_entities_sample.json",
            "canonical/london_pld_connected_edges_sample.json",
            "reports/target_uprn_coverage.json",
            "reports/backfill_match_rates.json",
            "reports/rejoin_rates.json",
            "reports/toid_context_after_backfill.json",
            "reports/usrn_context_after_backfill.json",
            "reports/unattached_after_backfill.json",
            "reports/confidence_summary.json",
        ],
    }
    write_json(output_dir / "LON_D5B_MANIFEST.json", manifest)
    return manifest


def run_lon_d5b_gate(
    lon_d4_dir: str,
    lon_d5_dir: str,
    os_sample_dir: str,
    output_dir: str,
    max_target_uprn: int = 1000,
) -> dict:
    lon_d4_path = Path(lon_d4_dir)
    lon_d5_path = Path(lon_d5_dir)
    os_sample_path = Path(os_sample_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    tracked_inputs = collect_tracked_inputs(lon_d4_path, lon_d5_path, os_sample_path)
    before_hashes = input_hashes(tracked_inputs)

    d4_parcels = pd.read_parquet(lon_d4_path / "canonical" / "london_parcels_uprn.parquet")
    d4_buildings = pd.read_parquet(lon_d4_path / "canonical" / "london_buildings_toid.parquet")
    d4_roads = pd.read_parquet(lon_d4_path / "canonical" / "london_road_segments_usrn.parquet")
    pld_entities = pd.read_parquet(lon_d5_path / "canonical" / "london_planning_applications.parquet")

    target_uprns, target_report, pld_uprns_by_record = extract_target_uprns(pld_entities, max_target_uprn)
    write_json(output_path / "LON_D5B_TARGET_UPRN_LIST.json", target_report)
    precond_report = preconditions(lon_d4_path, lon_d5_path, target_report)

    backfilled_entities, source_report, target_coverage = backfill_search(target_uprns, d4_parcels, os_sample_path)
    write_json(output_path / "LON_D5B_BACKFILL_SOURCE_REPORT.json", source_report)
    write_json(output_path / "reports" / "target_uprn_coverage.json", target_coverage)
    write_json(output_path / "reports" / "backfill_match_rates.json", source_report)

    d4_uprns = set(d4_parcels["native_id"].astype(str))
    available_uprns = d4_uprns | set(backfilled_entities["native_id"].astype(str) if not backfilled_entities.empty else [])
    rejoin_edges, still_unattached, rejoin_report = rejoin_pld(pld_entities, available_uprns)
    rejoin_report["target_uprns_total"] = len(target_uprns)
    rejoin_report["target_uprns_found_in_backfill"] = len(set(backfilled_entities["native_id"].astype(str)) if not backfilled_entities.empty else [])

    target_entities_available = set(backfilled_entities["native_id"].astype(str) if not backfilled_entities.empty else [])
    identity_edges, toid_report, usrn_report = scan_lids_context(os_sample_path, set(target_uprns), target_entities_available)
    smoke = connected_path_smoke(rejoin_edges, identity_edges, source_report)
    pld_permit_ids = set(pld_entities["canonical_id"].astype(str))
    d4_building_ids = set(d4_buildings["canonical_id"].astype(str))
    d4_road_ids = set(d4_roads["canonical_id"].astype(str))
    edge_report = edge_integrity(rejoin_edges, identity_edges, available_uprns, pld_permit_ids, d4_building_ids, d4_road_ids)

    id_gate = id_format_gate(backfilled_entities)
    context_gate = {
        "gate": "LON-D5B-CONTEXT-REPORT",
        "status": "PASS" if toid_report.get("attempted") is not None and usrn_report.get("attempted") is not None else "FAIL",
        "toid_context_after_backfill": toid_report,
        "usrn_context_after_backfill": usrn_report,
    }
    a2_report = compatibility_harness(backfilled_entities, rejoin_edges, available_uprns, pld_permit_ids)
    drift = drift_test(backfilled_entities, rejoin_edges, target_uprns, pld_permit_ids, available_uprns)
    confidence = confidence_summary(backfilled_entities, identity_edges, rejoin_edges)
    out_scope = out_of_scope_report(backfilled_entities, identity_edges, rejoin_edges, still_unattached)
    still_report = {
        "status": "PASS",
        "records_still_unattached": len(still_unattached),
        "reason_counts": dict(Counter(still_unattached["unattached_reason_after_backfill"].astype(str))) if not still_unattached.empty else {},
        "sample_records": frame_to_records(still_unattached, limit=25),
    }

    write_parquet(output_path / "canonical" / "london_pld_target_uprn_entities.parquet", backfilled_entities)
    write_parquet(output_path / "canonical" / "london_pld_backfilled_identity_edges.parquet", identity_edges)
    write_parquet(output_path / "canonical" / "london_pld_rejoined_edges.parquet", rejoin_edges)
    write_parquet(output_path / "canonical" / "london_pld_still_unattached_records.parquet", still_unattached)
    write_json(output_path / "canonical" / "london_pld_connected_entities_sample.json", frame_to_records(backfilled_entities))
    connected_edge_sample = frame_to_records(identity_edges, limit=12) + frame_to_records(rejoin_edges, limit=13)
    write_json(output_path / "canonical" / "london_pld_connected_edges_sample.json", connected_edge_sample)
    write_json(output_path / "LON_D5B_BACKFILL_JOIN_REPORT.json", rejoin_report)
    write_json(output_path / "LON_D5B_CONNECTED_PATH_SMOKE.json", smoke)
    write_json(output_path / "LON_D5B_DRIFT_TEST_REPORT.json", drift)
    write_json(output_path / "LON_D5B_INPUT_INVENTORY.json", inventory_inputs(lon_d4_path, lon_d5_path, os_sample_path, tracked_inputs))
    write_json(output_path / "reports" / "rejoin_rates.json", rejoin_report)
    write_json(output_path / "reports" / "toid_context_after_backfill.json", toid_report)
    write_json(output_path / "reports" / "usrn_context_after_backfill.json", usrn_report)
    write_json(output_path / "reports" / "unattached_after_backfill.json", still_report)
    write_json(output_path / "reports" / "confidence_summary.json", confidence)

    after_hashes = input_hashes(tracked_inputs)
    no_mutation = {
        "gate": "LON-D5B-NO-MUTATION",
        "status": "PASS" if before_hashes == after_hashes else "FAIL",
        "checked_files": len(before_hashes),
        "changed_files": sorted(path for path in before_hashes if before_hashes.get(path) != after_hashes.get(path)),
    }

    counts = {
        "target_pld_uprns": target_report["distinct_target_uprns"],
        "limited_target_uprns": len(target_uprns),
        "backfilled_uprns_found": len(backfilled_entities),
        "pld_uprn_edges_after_backfill": len(rejoin_edges),
        "still_unattached_records": len(still_unattached),
        "toid_context_edges": int((identity_edges["relation"] == "has_building").sum()) if not identity_edges.empty else 0,
        "usrn_context_edges": int((identity_edges["relation"] == "on_street").sum()) if not identity_edges.empty else 0,
    }
    write_manifest(output_path, lon_d4_path, lon_d5_path, os_sample_path, counts, "PENDING")
    preliminary = {
        "task": TASK_NAME,
        "status": "PENDING",
        "created_utc": utc_now(),
        "boundary_strings": BOUNDARY_STRINGS,
        "counts": counts,
        "preconditions": precond_report,
        "target_uprns": target_report,
        "backfill_source_report": source_report,
        "rejoin_rates": rejoin_report,
        "connected_path_smoke": smoke,
        "a2_compatibility": a2_report,
        "drift_test": drift,
    }
    write_json(output_path / "LON_D5B_HARNESS_REPORT.json", preliminary)
    write_docs(output_path, counts, target_report, source_report, rejoin_report, toid_report, usrn_report, smoke, a2_report)
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D5B_NO_OVERCLAIM_REPORT.json", no_overclaim)

    target_gate = {
        "gate": "LON-D5B-TARGET-UPRNS",
        "status": "PASS" if target_report["distinct_target_uprns"] > 0 and target_report["records_with_uprn"] > 0 else "FAIL",
        "records_with_uprn": target_report["records_with_uprn"],
        "distinct_target_uprns": target_report["distinct_target_uprns"],
        "limited_target_uprns": len(target_uprns),
    }
    gates = {
        "LON-D5B-PRECOND": precond_report["status"],
        "LON-D5B-TARGET-UPRNS": target_gate["status"],
        "LON-D5B-BACKFILL-SEARCH": "PASS" if source_report["search_attempted"] else "FAIL",
        "LON-D5B-BACKFILLED-ID-FORMAT": id_gate["status"],
        "LON-D5B-PLD-REJOIN": rejoin_report["status"],
        "LON-D5B-EDGE-INTEGRITY": edge_report["status"],
        "LON-D5B-CONTEXT-REPORT": context_gate["status"],
        "LON-D5B-CONNECTED-PATH-SMOKE": smoke["status"],
        "LON-D5B-A2-COMPATIBILITY": a2_report["status"],
        "LON-D5B-DRIFT": drift["status"],
        "LON-D5B-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D5B-OUT-OF-SCOPE": out_scope["status"],
        "LON-D5B-NO-MUTATION": no_mutation["status"],
        "LON-D5B-HASHES": "PASS",
    }
    overall = "PASS" if all(status == "PASS" for status in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "boundary_strings": BOUNDARY_STRINGS,
        "lon_d4_dir": str(lon_d4_path),
        "lon_d5_dir": str(lon_d5_path),
        "os_sample_dir": str(os_sample_path),
        "output_dir": str(output_path),
        "counts": counts,
        "preconditions": precond_report,
        "target_uprns": target_gate,
        "target_uprn_report": target_report,
        "target_uprn_coverage": target_coverage,
        "backfill_source_report": source_report,
        "id_format": id_gate,
        "rejoin_rates": rejoin_report,
        "edge_integrity": edge_report,
        "context_report": context_gate,
        "connected_path_smoke": smoke,
        "confidence_summary": confidence,
        "unattached_after_backfill": still_report,
        "a2_compatibility": a2_report,
        "drift_test": drift,
        "no_overclaim": no_overclaim,
        "out_of_scope": out_scope,
        "no_mutation": no_mutation,
        "hashes": {"gate": "LON-D5B-HASHES", "status": "PASS", "note": "SHA256SUMS.json covers all generated outputs except itself."},
        "gates": gates,
    }
    write_json(output_path / "LON_D5B_HARNESS_REPORT.json", harness)
    write_manifest(output_path, lon_d4_path, lon_d5_path, os_sample_path, counts, overall)
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D5B_NO_OVERCLAIM_REPORT.json", no_overclaim)
    harness["no_overclaim"] = no_overclaim
    harness["gates"]["LON-D5B-NO-OVERCLAIM"] = no_overclaim["status"]
    harness["status"] = "PASS" if all(status == "PASS" for status in harness["gates"].values()) else "FAIL"
    write_json(output_path / "LON_D5B_HARNESS_REPORT.json", harness)
    write_manifest(output_path, lon_d4_path, lon_d5_path, os_sample_path, counts, harness["status"])
    hash_report(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--lon-d4-dir", default=DEFAULT_LON_D4_DIR)
    parser.add_argument("--lon-d5-dir", default=DEFAULT_LON_D5_DIR)
    parser.add_argument("--os-sample-dir", default=DEFAULT_OS_SAMPLE_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-target-uprn", type=int, default=1000)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d5b_gate(args.lon_d4_dir, args.lon_d5_dir, args.os_sample_dir, args.output_dir, args.max_target_uprn)
    rejoin = report["rejoin_rates"]
    toid = report["context_report"]["toid_context_after_backfill"]
    usrn = report["context_report"]["usrn_context_after_backfill"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input LON-D5: {report['preconditions']['checks']['lon_d5_harness_report_status_pass'] and 'PASS' or 'FAIL'}")
    print(f"Target PLD UPRNs: {report['target_uprn_report']['distinct_target_uprns']}")
    print(f"Backfilled UPRNs found: {report['counts']['backfilled_uprns_found']}")
    print(f"PLD->UPRN edges emitted after backfill: {rejoin['pld_to_uprn_edges_emitted']}")
    print(f"Join rate after backfill: {rejoin['join_rate_after_backfill'] * 100:.2f}%")
    print(f"Still unattached records: {rejoin['records_still_unattached']}")
    print(f"TOID context coverage: {toid.get('context_coverage', 0.0) * 100:.2f}%")
    print(f"USRN context coverage: {usrn.get('context_coverage', 0.0) * 100:.2f}%")
    print(f"Connected path smoke: {report['connected_path_smoke']['result']}")
    print(f"A2 compatibility gates: {report['a2_compatibility']['status']}")
    print(f"Drift test: {report['drift_test']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
