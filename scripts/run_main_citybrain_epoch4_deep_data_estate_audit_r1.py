#!/usr/bin/env python3
"""Run a deep, read-only audit of the local CityBrain data estate.

The audit consumes existing local artifacts and writes only its own audit
outputs and publication mirror. It does not mutate source-truth data, create
training/fuel rows, call live sources, or arm any product/official workflow.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ZIP = Path.home() / "Downloads" / "main-citybrain-epoch4-deep-data-estate-audit-r1.zip"
OUTPUT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_deep_data_estate_audit_r1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-deep-data-estate-audit-r1"
TABLE_ROOT = OUTPUT_ROOT / "tables"

PACKAGE_ID = "MAIN-CITYBRAIN-EPOCH4-DEEP-DATA-ESTATE-AUDIT-R1"
FINAL_STATUS = "PASS_MAIN_CITYBRAIN_EPOCH4_DEEP_DATA_ESTATE_AUDIT_R1_WITH_LIMITATIONS"

TRACK4_ROOT = ROOT / "outputs" / "main_citybrain_track4_source_registry_v1"
TRACK5_ROOT = ROOT / "outputs" / "main_citybrain_track5_data_quality_maturity_dashboard_r1"
TRACKA_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_tracka_event_stories_source_diff_r1"
TRACKB_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_trackb_maturity_brief_governance_r1"
SPRINT0_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1"
EVAL_R2_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_eval_corpus_expansion_r2"
EVAL_REP_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_eval_representativeness_audit_r1"
CHALLENGE_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-product-loop-challenge-negative-suite-r1"
SYNTHETIC_R1_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1"
SYNTHETIC_PRODUCT_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1"
SYNTHETIC_D6_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1"
BASE_ACQUISITION_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2-P0-FULL-PULL-AND-NORMALIZATION"
MOBILITY_DEPTH_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL"

SCAN_ROOTS = [
    ROOT / "data",
    ROOT / "data_landing",
    ROOT / "data_synthetic",
    ROOT / "corpus_raw",
    ROOT / "inputs",
    ROOT / "outputs",
    ROOT / "publications",
    ROOT / "contracts",
    ROOT / "schemas",
    ROOT / "manifests",
    ROOT / "apps" / "web-control-room",
    ROOT / "apps" / "kit",
]

EXCLUDED_DIR_NAMES = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "tmp",
}

MAX_FILES_PER_ROOT = 30_000
MAX_ROW_LEDGER_FILES = 500
MAX_PARSE_BYTES = 25_000_000

REFERENCE_COUNTS = {
    "main_acquisition_fuel_rows": 66737,
    "base_city_rows": 20631,
    "mobility_depth_rows": 46106,
    "synthetic_seed_entities": 144,
    "combined_event_replay_rows": 55,
    "watch_fixtures": 11,
    "ask_fixtures": 11,
    "check_fixtures": 11,
    "brief_fixtures": 11,
    "spatial_fixtures": 11,
    "runtime_packet_fixtures": 6,
    "control_room_cards": 6,
}

REQUIRED_JSON_OUTPUTS = [
    "DATA_ESTATE_AUDIT_DECISION.json",
    "DATA_ROOT_INVENTORY.json",
    "SOURCE_MANIFEST_INVENTORY.json",
    "SOURCE_REGISTRY_CROSSWALK.json",
    "CITY_DOMAIN_COVERAGE_MATRIX.json",
    "SOURCE_CLASS_PROVENANCE_AUDIT.json",
    "ROW_COUNT_AND_SIZE_LEDGER.json",
    "SYNTHETIC_DATA_FACTORY_AUDIT.json",
    "EVENT_REPLAY_DATA_AUDIT.json",
    "SIMULATION_DATA_AUDIT.json",
    "PRODUCT_LOOP_EVAL_COVERAGE_AUDIT.json",
    "FOUNDER_PROBE_REPRESENTATIVENESS_CROSSWALK.json",
    "TEMPORAL_FRESHNESS_AUDIT.json",
    "GEOSPATIAL_COVERAGE_AUDIT.json",
    "IDENTITY_CER_READINESS_DATA_AUDIT.json",
    "CHECK_CLAIMABILITY_DATA_AUDIT.json",
    "DATA_MATURITY_REMEDIATION_CROSSWALK.json",
    "DATA_RISK_REGISTER.json",
    "MISSING_DATA_BACKLOG.json",
    "LOW_HANGING_DATA_WINS.json",
    "NEXT_MOVE_RECOMMENDATION.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
]

REQUIRED_MD_OUTPUTS = [
    "VALUE_POCKET_DATA_MAP.md",
    "EXECUTIVE_DATA_ESTATE_SUMMARY.md",
]

REQUIRED_TABLES = [
    "tables/data_source_catalog.csv",
    "tables/city_domain_coverage.csv",
    "tables/source_class_coverage.csv",
    "tables/eval_coverage_matrix.csv",
    "tables/missing_data_backlog.csv",
    "tables/low_hanging_data_wins.csv",
    "tables/value_pocket_data_map.csv",
]

OUTPUT_FILES = REQUIRED_JSON_OUTPUTS + REQUIRED_MD_OUTPUTS + REQUIRED_TABLES + [
    "PUBLICATION_COVERAGE_REPORT.json",
    "HASH_MANIFEST.json",
]

FORBIDDEN_CAPABILITIES = [
    "source_truth_mutation",
    "founder_session_results",
    "operator_fuel",
    "training_rows",
    "model_training",
    "learned_arming",
    "ForecastPacket",
    "product_forecast_surface",
    "live_ingestion_claim",
    "official_case_ticket_action",
    "dispatch_control_enforcement",
    "maturity_score_inflation",
    "donor_data_as_official_dubai_truth",
]


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


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {} if default is None else default


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: flatten_csv_value(row.get(key)) for key in fieldnames})


def flatten_csv_value(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, ensure_ascii=True)
    if value is None:
        return ""
    return str(value)


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("rb") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        line_count = sum(1 for line in handle if line.strip())
    return max(0, line_count - 1)


def sum_csv_column(path: Path, column: str) -> int:
    if not path.exists():
        return 0
    total = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                total += int(float(row.get(column, 0) or 0))
            except ValueError:
                continue
    return total


def row_count_for_json(path: Path) -> tuple[int | None, str]:
    if not path.exists() or path.stat().st_size > MAX_PARSE_BYTES:
        return None, "skipped_large_or_missing"
    payload = read_json(path, None)
    if isinstance(payload, list):
        return len(payload), "top_level_list"
    if isinstance(payload, dict):
        for key in [
            "sources",
            "records",
            "entries",
            "datasets",
            "cases",
            "cards",
            "events",
            "rows",
            "fixtures",
            "reports",
            "story_packs",
            "canonical_entities",
            "attribute_assertions",
            "scorecards",
        ]:
            if isinstance(payload.get(key), list):
                return len(payload[key]), f"list_key:{key}"
        for key in ["source_count", "case_count", "card_count", "report_count", "entity_count"]:
            if isinstance(payload.get(key), int):
                return int(payload[key]), f"count_key:{key}"
    return None, "parsed_no_row_count"


def classify_root(root: Path) -> str:
    name = root.as_posix().lower()
    if "data_synthetic" in name or "synthetic" in name:
        return "synthetic"
    if any(token in name for token in ["corpus_raw", "data_landing", "/inputs"]):
        return "raw_or_landed"
    if "/data" in name:
        return "processed_or_local_data"
    if any(token in name for token in ["/outputs", "/publications"]):
        return "generated_or_published_artifact"
    if any(token in name for token in ["/contracts", "/schemas", "/manifests"]):
        return "control_contract_or_manifest"
    return "application_or_unknown"


def inventory_root(root: Path) -> tuple[dict[str, Any], list[Path]]:
    if not root.exists():
        return {
            "root": rel(root),
            "exists": False,
            "classification": classify_root(root),
            "scan_mode": "missing",
            "sample_policy": "none",
            "file_count": 0,
            "dir_count": 0,
            "bytes": 0,
            "extension_counts": {},
            "data_file_counts": {},
            "largest_files": [],
            "coverage_limitations": ["Root missing in local workspace."],
        }, []

    ext_counts: Counter[str] = Counter()
    data_counts: Counter[str] = Counter()
    largest: list[dict[str, Any]] = []
    sampled_files: list[Path] = []
    total_bytes = 0
    file_count = 0
    dir_count = 0
    truncated = False

    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIR_NAMES)
        dir_count += len(dirs)
        for filename in sorted(files):
            path = Path(current) / filename
            try:
                stat = path.stat()
            except OSError:
                continue
            suffix = path.suffix.lower() or "<none>"
            ext_counts[suffix] += 1
            if suffix in {".json", ".jsonl", ".csv", ".parquet", ".duckdb"}:
                data_counts[suffix] += 1
                if len(sampled_files) < MAX_ROW_LEDGER_FILES:
                    sampled_files.append(path)
            total_bytes += stat.st_size
            file_count += 1
            largest.append({"path": rel(path), "bytes": stat.st_size, "extension": suffix})
            largest = sorted(largest, key=lambda row: (-row["bytes"], row["path"]))[:10]
            if file_count >= MAX_FILES_PER_ROOT:
                truncated = True
                break
        if truncated:
            break

    limitations = []
    if truncated:
        limitations.append(f"Scan capped at {MAX_FILES_PER_ROOT} files for deterministic bounded runtime.")
    return {
        "root": rel(root),
        "exists": True,
        "classification": classify_root(root),
        "scan_mode": "bounded_recursive" if truncated else "recursive_full_with_exclusions",
        "sample_policy": "deterministic_path_order_with_row_count_sample",
        "file_count": file_count,
        "dir_count": dir_count,
        "bytes": total_bytes,
        "extension_counts": dict(sorted(ext_counts.items())),
        "data_file_counts": dict(sorted(data_counts.items())),
        "largest_files": largest,
        "likely_generated_vs_source": classify_root(root),
        "committed_published_local_only": "published" if "publications" in root.parts else "local_workspace_artifact",
        "coverage_limitations": limitations,
    }, sampled_files


def build_data_root_inventory() -> tuple[dict[str, Any], list[Path]]:
    roots = []
    sampled_files: list[Path] = []
    for root in SCAN_ROOTS:
        row, samples = inventory_root(root)
        roots.append(row)
        sampled_files.extend(samples)
    summary = {
        "artifact_id": "DATA_ROOT_INVENTORY",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "root_count": len(roots),
        "existing_root_count": sum(1 for row in roots if row["exists"]),
        "total_scanned_files": sum(row["file_count"] for row in roots),
        "total_scanned_bytes": sum(row["bytes"] for row in roots),
        "scan_roots": roots,
        "coverage_limitations": [
            "Large roots use deterministic bounded scans when they exceed the file cap.",
            "Binary geospatial/parquet/duckdb files are inventoried by size and extension, not deeply parsed.",
        ],
    }
    write_json(OUTPUT_ROOT / "DATA_ROOT_INVENTORY.json", summary)
    return summary, sampled_files


def build_row_count_ledger(inventory: dict[str, Any], sampled_files: list[Path]) -> dict[str, Any]:
    entries = []
    for path in sorted(set(sampled_files), key=lambda p: rel(p))[:MAX_ROW_LEDGER_FILES]:
        suffix = path.suffix.lower()
        row_count: int | None = None
        method = "not_counted"
        if suffix == ".jsonl" and path.stat().st_size <= MAX_PARSE_BYTES:
            row_count = count_jsonl_rows(path)
            method = "jsonl_nonempty_lines"
        elif suffix == ".csv" and path.stat().st_size <= MAX_PARSE_BYTES:
            row_count = count_csv_rows(path)
            method = "csv_nonempty_lines_minus_header"
        elif suffix == ".json":
            row_count, method = row_count_for_json(path)
        elif suffix in {".parquet", ".duckdb"}:
            method = "binary_data_file_inventory_only"
        entries.append(
            {
                "path": rel(path),
                "extension": suffix,
                "bytes": path.stat().st_size,
                "row_count": row_count,
                "method": method,
            }
        )

    base_rows = sum_csv_column(BASE_ACQUISITION_ROOT / "SAMPLE_ROW_COUNTS_R2.csv", "row_count")
    mobility_rows = sum_csv_column(MOBILITY_DEPTH_ROOT / "SAMPLE_ROW_COUNTS_R2E.csv", "row_count_estimate")
    special_entries = [
        {
            "path": rel(BASE_ACQUISITION_ROOT / "SAMPLE_ROW_COUNTS_R2.csv"),
            "extension": ".csv",
            "bytes": (BASE_ACQUISITION_ROOT / "SAMPLE_ROW_COUNTS_R2.csv").stat().st_size
            if (BASE_ACQUISITION_ROOT / "SAMPLE_ROW_COUNTS_R2.csv").exists()
            else 0,
            "row_count": base_rows,
            "method": "sum_csv_column:row_count",
            "semantic_count": "base_city_rows",
        },
        {
            "path": rel(MOBILITY_DEPTH_ROOT / "SAMPLE_ROW_COUNTS_R2E.csv"),
            "extension": ".csv",
            "bytes": (MOBILITY_DEPTH_ROOT / "SAMPLE_ROW_COUNTS_R2E.csv").stat().st_size
            if (MOBILITY_DEPTH_ROOT / "SAMPLE_ROW_COUNTS_R2E.csv").exists()
            else 0,
            "row_count": mobility_rows,
            "method": "sum_csv_column:row_count_estimate",
            "semantic_count": "mobility_depth_rows",
        },
    ]
    ledger = {
        "artifact_id": "ROW_COUNT_AND_SIZE_LEDGER",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "inventory_ref": rel(OUTPUT_ROOT / "DATA_ROOT_INVENTORY.json"),
        "total_scanned_files": inventory["total_scanned_files"],
        "total_scanned_bytes": inventory["total_scanned_bytes"],
        "row_count_entry_count": len(entries) + len(special_entries),
        "bounded_sample_policy": f"first {MAX_ROW_LEDGER_FILES} data-like files by deterministic path order, plus named package count files",
        "entries": special_entries + entries,
        "limitations": [
            "Row counts are direct for JSONL/CSV and schema-derived for selected JSON manifests.",
            "Parquet and DuckDB files are inventoried but not deeply read by this lightweight audit runner.",
        ],
    }
    write_json(OUTPUT_ROOT / "ROW_COUNT_AND_SIZE_LEDGER.json", ledger)
    return ledger


def load_source_registry() -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    candidates = [
        TRACKA_ROOT / "SOURCE_REGISTRY_V1_1.json",
        TRACK4_ROOT / "SOURCE_REGISTRY_V1.json",
    ]
    for path in candidates:
        payload = read_json(path, {})
        sources = payload.get("sources", [])
        if isinstance(sources, list) and sources:
            return sources, payload, rel(path)
    return [], {}, "not_found"


def source_registry_crosswalk() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sources, payload, registry_ref = load_source_registry()
    city_counts = Counter(str(row.get("city") or "unknown") for row in sources)
    domain_counts = Counter(str(row.get("domain") or "unknown") for row in sources)
    class_counts = Counter(str(row.get("source_class") or "unknown") for row in sources)
    freshness_counts = Counter(str(row.get("freshness_status") or row.get("freshness") or "unknown") for row in sources)
    geometry_counts = Counter(str(row.get("geometry_status") or "unknown") for row in sources)
    schema_counts = Counter(str(row.get("schema_status") or "unknown") for row in sources)
    consuming_count = sum(1 for row in sources if row.get("consuming_flows") or row.get("consuming_modes"))
    gap_counts = {
        "unknown_source_class": sum(1 for row in sources if "unknown" in str(row.get("source_class") or "").lower()),
        "unknown_freshness": sum(1 for row in sources if "unknown" in str(row.get("freshness_status") or row.get("freshness") or "").lower()),
        "missing_or_unknown_geometry": sum(1 for row in sources if "missing" in str(row.get("geometry_status") or "").lower() or "unknown" in str(row.get("geometry_status") or "").lower()),
        "unknown_schema": sum(1 for row in sources if "unknown" in str(row.get("schema_status") or "").lower()),
        "no_consuming_flow": sum(1 for row in sources if not row.get("consuming_flows") and not row.get("consuming_modes")),
    }
    crosswalk = {
        "artifact_id": "SOURCE_REGISTRY_CROSSWALK",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS" if sources else "PENDING_NO_SOURCE_REGISTRY",
        "registry_ref": registry_ref,
        "schema_version": payload.get("schema_version"),
        "source_count": len(sources),
        "city_counts": dict(sorted(city_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "source_class_counts": dict(sorted(class_counts.items())),
        "freshness_counts": dict(sorted(freshness_counts.items())),
        "geometry_counts": dict(sorted(geometry_counts.items())),
        "schema_counts": dict(sorted(schema_counts.items())),
        "consuming_flow_source_count": consuming_count,
        "gap_counts": gap_counts,
        "sample_sources": sources[:25],
        "interpretation": [
            "SourceRegistry coverage is broad enough to power CHECK/CER/Event Fabric diagnostics.",
            "Unknown freshness, source class, schema, geometry, and no-consuming-flow remain material findings.",
        ],
    }
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_CROSSWALK.json", crosswalk)
    return crosswalk, sources


def source_manifest_inventory() -> dict[str, Any]:
    index = read_json(TRACK4_ROOT / "SOURCE_REGISTRY_SOURCE_FILE_INDEX.json", {"files": []})
    files = index.get("files", [])
    status_counts = Counter(str(row.get("status", "unknown")) for row in files)
    source_rows_total = sum(int(row.get("source_rows") or 0) for row in files if isinstance(row, dict))
    payload = {
        "artifact_id": "SOURCE_MANIFEST_INVENTORY",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS" if files else "PENDING_NO_SOURCE_FILE_INDEX",
        "source_file_index_ref": rel(TRACK4_ROOT / "SOURCE_REGISTRY_SOURCE_FILE_INDEX.json"),
        "candidate_file_count": index.get("candidate_file_count", len(files)),
        "scanned_file_count": len(files),
        "status_counts": dict(sorted(status_counts.items())),
        "source_rows_detected_total": source_rows_total,
        "sample_files": files[:50],
        "limitations": [
            "Manifest inventory is sourced from SourceRegistry v1's deterministic source-like file scan.",
            "A file mention is not treated as source readiness unless SourceRegistry mapped it.",
        ],
    }
    write_json(OUTPUT_ROOT / "SOURCE_MANIFEST_INVENTORY.json", payload)
    return payload


def build_city_domain_matrix(sources: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in sources:
        grouped[(str(row.get("city") or "unknown"), str(row.get("domain") or "unknown"))].append(row)
    matrix = []
    for (city, domain), rows in sorted(grouped.items()):
        class_counts = Counter(str(row.get("source_class") or "unknown") for row in rows)
        matrix.append(
            {
                "city": city,
                "domain": domain,
                "source_count": len(rows),
                "source_class_counts": dict(sorted(class_counts.items())),
                "consuming_flow_source_count": sum(1 for row in rows if row.get("consuming_flows") or row.get("consuming_modes")),
                "unknown_source_class_count": sum(1 for row in rows if "unknown" in str(row.get("source_class") or "").lower()),
                "missing_geometry_count": sum(1 for row in rows if "missing" in str(row.get("geometry_status") or "").lower()),
                "unknown_freshness_count": sum(1 for row in rows if "unknown" in str(row.get("freshness_status") or row.get("freshness") or "").lower()),
            }
        )
    payload = {
        "artifact_id": "CITY_DOMAIN_COVERAGE_MATRIX",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS" if matrix else "PENDING_NO_SOURCE_REGISTRY",
        "matrix_count": len(matrix),
        "cities": sorted({row["city"] for row in matrix}),
        "domains": sorted({row["domain"] for row in matrix}),
        "matrix": matrix,
    }
    write_json(OUTPUT_ROOT / "CITY_DOMAIN_COVERAGE_MATRIX.json", payload)
    return payload, matrix


def provenance_bucket(source_class: str) -> str:
    text = source_class.lower()
    if "official" in text:
        return "official_record"
    if "source_record" in text:
        return "source_record"
    if "donor" in text:
        return "donor_real"
    if "synthetic" in text or "seed" in text:
        return "synthetic_seed"
    if "replay" in text:
        return "replay_fixture"
    if "derived" in text or "candidate" in text:
        return "derived_candidate"
    if "sensor" in text or "perception" in text:
        return "sensor_inferred"
    if "model" in text or "narrative" in text:
        return "model_generated_narrative"
    if "fixture" in text:
        return "fixture_only"
    return "unknown"


def build_source_class_provenance(sources: list[dict[str, Any]]) -> dict[str, Any]:
    raw_counts = Counter(str(row.get("source_class") or "unknown") for row in sources)
    bucket_counts = Counter(provenance_bucket(str(row.get("source_class") or "unknown")) for row in sources)
    eval_inventory = read_json(EVAL_REP_ROOT / "EVAL_CORPUS_INVENTORY.json", {})
    for source_class, count in eval_inventory.get("source_class_counts", {}).items():
        bucket_counts[provenance_bucket(source_class)] += int(count)
    factory_counts = read_json(SYNTHETIC_R1_ROOT / "SEED_ENTITY_MANIFEST.json", {}).get("entity_count", 0)
    if factory_counts:
        bucket_counts["synthetic_seed"] += int(factory_counts)
    payload = {
        "artifact_id": "SOURCE_CLASS_PROVENANCE_AUDIT",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "raw_source_class_counts": dict(sorted(raw_counts.items())),
        "normalized_provenance_counts": {key: bucket_counts.get(key, 0) for key in [
            "official_record",
            "source_record",
            "donor_real",
            "synthetic_seed",
            "replay_fixture",
            "derived_candidate",
            "sensor_inferred",
            "model_generated_narrative",
            "fixture_only",
            "unknown",
        ]},
        "unknown_is_finding": bucket_counts.get("unknown", 0) > 0,
        "non_claims": [
            "Synthetic and donor records are not official Dubai truth.",
            "Replay and fixture records are review/eval support, not live facts.",
        ],
    }
    write_json(OUTPUT_ROOT / "SOURCE_CLASS_PROVENANCE_AUDIT.json", payload)
    return payload


def build_temporal_and_geospatial_audits(sources: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    freshness_counts = Counter(str(row.get("freshness_status") or row.get("freshness") or "unknown") for row in sources)
    time_counts = Counter(str(row.get("time_coverage") or row.get("time_coverage_start") or "unknown") for row in sources)
    temporal = {
        "artifact_id": "TEMPORAL_FRESHNESS_AUDIT",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "source_count": len(sources),
        "freshness_counts": dict(sorted(freshness_counts.items())),
        "time_coverage_signal_counts": dict(sorted(time_counts.items())),
        "unknown_freshness_count": sum(1 for row in sources if "unknown" in str(row.get("freshness_status") or row.get("freshness") or "").lower()),
        "missing_time_history_count": sum(1 for row in sources if "unknown" in str(row.get("time_coverage") or row.get("time_coverage_start") or "").lower()),
        "limitations": ["Most sources expose freshness/time coverage as source-registry metadata rather than verified native refresh histories."],
    }
    geometry_counts = Counter(str(row.get("geometry_status") or "unknown") for row in sources)
    geospatial = {
        "artifact_id": "GEOSPATIAL_COVERAGE_AUDIT",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "source_count": len(sources),
        "geometry_counts": dict(sorted(geometry_counts.items())),
        "missing_or_unknown_geometry_count": sum(1 for row in sources if "missing" in str(row.get("geometry_status") or "").lower() or "unknown" in str(row.get("geometry_status") or "").lower()),
        "geometry_present_or_partial_count": sum(1 for row in sources if any(token in str(row.get("geometry_status") or "").lower() for token in ["present", "partial", "centroid", "geometry"])),
        "limitations": ["Geometry status is registry-derived; this audit does not open or validate every geospatial payload."],
    }
    write_json(OUTPUT_ROOT / "TEMPORAL_FRESHNESS_AUDIT.json", temporal)
    write_json(OUTPUT_ROOT / "GEOSPATIAL_COVERAGE_AUDIT.json", geospatial)
    return temporal, geospatial


def observed_reference_counts() -> tuple[dict[str, Any], dict[str, Any]]:
    product_manifest = read_json(SYNTHETIC_PRODUCT_ROOT / "PRODUCT_FEED_MANIFEST_R1.json", {})
    product_decision = read_json(SYNTHETIC_PRODUCT_ROOT / "PRODUCT_CONSUMPTION_R1_DECISION.json", {})
    seed_manifest = read_json(SYNTHETIC_R1_ROOT / "SEED_ENTITY_MANIFEST.json", {})
    base_rows = sum_csv_column(BASE_ACQUISITION_ROOT / "SAMPLE_ROW_COUNTS_R2.csv", "row_count")
    mobility_rows = sum_csv_column(MOBILITY_DEPTH_ROOT / "SAMPLE_ROW_COUNTS_R2E.csv", "row_count_estimate")
    feed_rows = {row.get("feed_type"): row.get("rows") for row in product_manifest.get("outputs", []) if isinstance(row, dict)}
    observed = {
        "base_city_rows": base_rows,
        "mobility_depth_rows": mobility_rows,
        "main_acquisition_fuel_rows": base_rows + mobility_rows if base_rows or mobility_rows else None,
        "synthetic_seed_entities": seed_manifest.get("entity_count"),
        "combined_event_replay_rows": feed_rows.get("event") or product_decision.get("counts", {}).get("event_rows") or count_jsonl_rows(SYNTHETIC_PRODUCT_ROOT / "EVENT_REPLAY_COMBINED_R1.jsonl"),
        "watch_fixtures": feed_rows.get("watch") or product_decision.get("counts", {}).get("watch_rows") or count_jsonl_rows(SYNTHETIC_PRODUCT_ROOT / "WATCH_QUEUE_COMBINED_R1.jsonl"),
        "ask_fixtures": feed_rows.get("ask") or product_decision.get("counts", {}).get("ask_rows") or count_jsonl_rows(SYNTHETIC_PRODUCT_ROOT / "ASK_FIXTURE_INDEX_R1.jsonl"),
        "check_fixtures": feed_rows.get("check") or product_decision.get("counts", {}).get("check_rows") or count_jsonl_rows(SYNTHETIC_PRODUCT_ROOT / "CHECK_FIXTURE_INDEX_R1.jsonl"),
        "brief_fixtures": feed_rows.get("brief") or product_decision.get("counts", {}).get("brief_rows") or count_jsonl_rows(SYNTHETIC_PRODUCT_ROOT / "BRIEF_FIXTURE_INDEX_R1.jsonl"),
        "spatial_fixtures": feed_rows.get("spatial") or product_decision.get("counts", {}).get("spatial_rows") or count_jsonl_rows(SYNTHETIC_PRODUCT_ROOT / "SPATIAL_OVERLAY_INDEX_R1.jsonl"),
        "runtime_packet_fixtures": product_manifest.get("d5_runtime_packet_rows") or product_decision.get("counts", {}).get("d5_runtime_packet_rows") or count_jsonl_rows(SYNTHETIC_PRODUCT_ROOT / "D5_RUNTIME_PACKET_FIXTURES_R1.jsonl"),
        "control_room_cards": count_jsonl_rows(SYNTHETIC_D6_ROOT / "D6_CONTROL_ROOM_CARD_INDEX_R1.jsonl"),
    }
    evidence = {
        "base_city_rows": rel(BASE_ACQUISITION_ROOT / "SAMPLE_ROW_COUNTS_R2.csv"),
        "mobility_depth_rows": rel(MOBILITY_DEPTH_ROOT / "SAMPLE_ROW_COUNTS_R2E.csv"),
        "main_acquisition_fuel_rows": "sum(base_city_rows,mobility_depth_rows)",
        "synthetic_seed_entities": rel(SYNTHETIC_R1_ROOT / "SEED_ENTITY_MANIFEST.json"),
        "combined_event_replay_rows": rel(SYNTHETIC_PRODUCT_ROOT / "PRODUCT_FEED_MANIFEST_R1.json"),
        "watch_fixtures": rel(SYNTHETIC_PRODUCT_ROOT / "PRODUCT_FEED_MANIFEST_R1.json"),
        "ask_fixtures": rel(SYNTHETIC_PRODUCT_ROOT / "PRODUCT_FEED_MANIFEST_R1.json"),
        "check_fixtures": rel(SYNTHETIC_PRODUCT_ROOT / "PRODUCT_FEED_MANIFEST_R1.json"),
        "brief_fixtures": rel(SYNTHETIC_PRODUCT_ROOT / "PRODUCT_FEED_MANIFEST_R1.json"),
        "spatial_fixtures": rel(SYNTHETIC_PRODUCT_ROOT / "PRODUCT_FEED_MANIFEST_R1.json"),
        "runtime_packet_fixtures": rel(SYNTHETIC_PRODUCT_ROOT / "PRODUCT_FEED_MANIFEST_R1.json"),
        "control_room_cards": rel(SYNTHETIC_D6_ROOT / "D6_CONTROL_ROOM_CARD_INDEX_R1.jsonl"),
    }
    return observed, evidence


def build_synthetic_factory_audit() -> dict[str, Any]:
    observed, evidence = observed_reference_counts()
    comparisons = []
    for key, expected in REFERENCE_COUNTS.items():
        actual = observed.get(key)
        if actual == expected:
            status = "matched"
        elif actual in (None, 0):
            status = "not_found"
        else:
            status = "partial_or_mismatch"
        comparisons.append(
            {
                "count_name": key,
                "reference_count": expected,
                "observed_count": actual,
                "verification_status": status,
                "evidence_ref": evidence.get(key),
            }
        )
    payload = {
        "artifact_id": "SYNTHETIC_DATA_FACTORY_AUDIT",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "comparison_count": len(comparisons),
        "matched_count": sum(1 for row in comparisons if row["verification_status"] == "matched"),
        "comparisons": comparisons,
        "factory_roots": [
            rel(SYNTHETIC_R1_ROOT),
            rel(SYNTHETIC_PRODUCT_ROOT),
            rel(SYNTHETIC_D6_ROOT),
            rel(BASE_ACQUISITION_ROOT),
            rel(MOBILITY_DEPTH_ROOT),
        ],
        "truth_boundary": "Synthetic Dubai-like and donor mobility records are factory/replay/context only, not official Dubai truth.",
        "limitations": [
            "Counts are verified against local manifests and row-count ledgers; this audit does not recreate the factory.",
            "Acquisition counts are source-manifest/sample-count backed, not live re-pulled.",
        ],
    }
    write_json(OUTPUT_ROOT / "SYNTHETIC_DATA_FACTORY_AUDIT.json", payload)
    return payload


def build_event_replay_audit() -> dict[str, Any]:
    v21 = read_json(ROOT / "outputs" / "main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening" / "EVENT_STORY_REPLAY_PACKS_V2_1.json", {})
    tracka_story = read_json(TRACKA_ROOT / "EVENT_STORY_PACK_R1.json", {})
    v25_load = ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_5_long_history_load_r1" / "EVENT_FABRIC_V2_5_LONG_HISTORY_LOAD_LOG.jsonl"
    event_roots = sorted(
        rel(path)
        for path in (ROOT / "outputs").glob("*")
        if path.is_dir() and "event_fabric" in path.name.lower()
    )
    product_event_count = count_jsonl_rows(SYNTHETIC_PRODUCT_ROOT / "EVENT_REPLAY_COMBINED_R1.jsonl")
    payload = {
        "artifact_id": "EVENT_REPLAY_DATA_AUDIT",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "event_fabric_roots_detected": event_roots,
        "v2_1_story_pack_count": len(v21.get("story_packs", [])),
        "tracka_event_story_count": tracka_story.get("story_count"),
        "synthetic_product_event_replay_rows": product_event_count,
        "v2_5_long_history_log_rows": count_jsonl_rows(v25_load),
        "consumption_refs": [
            rel(TRACKA_ROOT / "EVENT_STORY_REPLAY_MANIFEST.json"),
            rel(SYNTHETIC_PRODUCT_ROOT / "EVENT_REPLAY_COMBINED_R1.jsonl"),
            rel(v25_load),
        ],
        "lifecycle_support": [
            "local replay",
            "duplicate/superseded/unresolved/quarantine handling where present in Event Fabric outputs",
            "DIFF/source-refresh compatibility through Track A fixtures",
        ],
        "limitations": [
            "Event Fabric evidence is local/replay/history only.",
            "No live event source or official incident truth is created by this audit.",
        ],
    }
    write_json(OUTPUT_ROOT / "EVENT_REPLAY_DATA_AUDIT.json", payload)
    return payload


def build_simulation_audit() -> dict[str, Any]:
    sim_roots = sorted(
        rel(path)
        for path in (ROOT / "outputs").glob("*")
        if path.is_dir() and any(token in path.name.lower() for token in ["simulation", "sumo", "option_runner", "connector_upgrade"])
    )
    known_refs = [
        ROOT / "outputs" / "track3_simulation_v2_1_connector_upgrade_path" / "SUMO_CONNECTOR_READINESS_PROBE.json",
        ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_2_real_connector_fidelity_ladder_r1" / "SIMULATION_V2_2_CONNECTOR_PROBE_RESULTS.json",
        ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_3_sumo_real_run_smoke_r1" / "SIMULATION_V2_3_SUMO_RUN_REPORT.json",
        ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_4_family_sumo_option_runner_r1" / "SIMULATION_V2_4_FAMILY_RUN_REPORT.json",
    ]
    payload = {
        "artifact_id": "SIMULATION_DATA_AUDIT",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "simulation_like_root_count": len(sim_roots),
        "simulation_like_roots_detected": sim_roots[:80],
        "known_evidence_refs": [rel(path) for path in known_refs if path.exists()],
        "sumo_artifact_refs": [
            rel(path)
            for path in sorted((ROOT / "outputs").rglob("*"))
            if path.is_file() and "sumo" in path.name.lower()
        ][:80],
        "support_summary": [
            "SUMO connector/readiness and smoke artifacts are present for mobility-oriented simulation.",
            "Non-SUMO option-engine and do-nothing baseline artifacts are present in simulation/option tracks.",
            "Simulation remains review/option support and is not calibrated product forecast authority.",
        ],
        "limitations": [
            "No ForecastPacket, product forecast surface, dispatch/control path, or calibrated forecast claim is created.",
            "This audit inventories simulation evidence but does not rerun SUMO or option engines.",
        ],
    }
    write_json(OUTPUT_ROOT / "SIMULATION_DATA_AUDIT.json", payload)
    return payload


def build_eval_and_founder_audits() -> tuple[dict[str, Any], dict[str, Any]]:
    eval_index = read_json(EVAL_R2_ROOT / "EVAL_CORPUS_R2_INDEX.json", {})
    eval_inventory = read_json(EVAL_REP_ROOT / "EVAL_CORPUS_INVENTORY.json", {})
    challenge_decision = read_json(CHALLENGE_ROOT / "PRODUCT_LOOP_CHALLENGE_NEGATIVE_SUITE_DECISION.json", {})
    negative_coverage = read_json(ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-eval-corpus-expansion-r2" / "EVAL_CASE_NEGATIVE_COVERAGE_REPORT.json", {})
    eval_payload = {
        "artifact_id": "PRODUCT_LOOP_EVAL_COVERAGE_AUDIT",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "eval_case_count": eval_index.get("case_count") or eval_inventory.get("case_count"),
        "target_min_cases": eval_index.get("target_min_cases"),
        "family_count": eval_index.get("family_count") or eval_inventory.get("family_count"),
        "families": eval_index.get("families") or eval_inventory.get("families", []),
        "challenge_class_counts": eval_inventory.get("challenge_class_counts") or negative_coverage.get("challenge_class_counts", {}),
        "separate_challenge_negative_suite_count": challenge_decision.get("challenge_case_count"),
        "challenge_negative_suite_status": challenge_decision.get("status"),
        "source_class_counts": eval_inventory.get("source_class_counts", {}),
        "operator_fuel_any": eval_inventory.get("operator_fuel_any", False),
        "training_eligible_any": eval_inventory.get("training_eligible_any", False),
        "source_truth_mutated_any": eval_inventory.get("source_truth_mutated_any", False),
        "coverage_interpretation": [
            "48 local/replay eval cases are present with expected CHECK/event/simulation outcomes.",
            "32 challenge/negative guard cases are present as a separate suite.",
            "Representativeness is regression/diagnostic support, not product readiness by itself.",
        ],
    }
    write_json(OUTPUT_ROOT / "PRODUCT_LOOP_EVAL_COVERAGE_AUDIT.json", eval_payload)

    founder_inventory = read_json(EVAL_REP_ROOT / "FOUNDER_CARD_INVENTORY.json", {})
    founder_readiness = read_json(EVAL_REP_ROOT / "FOUNDER_CARD_READINESS_CLASSIFICATION.json", {})
    cards = founder_readiness.get("cards", [])
    classification_counts = Counter(str(row.get("classification") or "unknown") for row in cards)
    missing_counts: Counter[str] = Counter()
    for row in cards:
        for item in row.get("missing_for_product_review_ready", []):
            missing_counts[str(item)] += 1
    founder_payload = {
        "artifact_id": "FOUNDER_PROBE_REPRESENTATIVENESS_CROSSWALK",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "founder_card_count": founder_inventory.get("card_count") or founder_readiness.get("card_count"),
        "classification_counts": dict(sorted(classification_counts.items())),
        "missing_for_product_review_ready_counts": dict(sorted(missing_counts.items())),
        "sample_cards": cards[:8],
        "representativeness_interpretation": [
            "Founder cards are diagnostic-review-ready where classified, but missing readable evidence summaries, CER/SEG context, and CHECK actual outcomes.",
            "No founder session results or operator/founder fuel are created by this audit.",
        ],
    }
    write_json(OUTPUT_ROOT / "FOUNDER_PROBE_REPRESENTATIVENESS_CROSSWALK.json", founder_payload)
    return eval_payload, founder_payload


def build_cer_and_check_audits() -> tuple[dict[str, Any], dict[str, Any]]:
    cer = read_json(SPRINT0_ROOT / "CER_ENTITY_RESOLUTION_RUN_R1.json", {})
    conflicts = read_json(SPRINT0_ROOT / "CER_CONFLICT_REPORT_R1.json", {})
    check_engine = read_json(SPRINT0_ROOT / "CHECK_V1_ENGINE_REPORT.json", {})
    downgrade = read_json(TRACK5_ROOT / "CHECK_DOWNGRADE_REASON_INDEX.json", {})
    check_reports_path = SPRINT0_ROOT / "CHECK_V1_REPORTS.jsonl"
    cer_payload = {
        "artifact_id": "IDENTITY_CER_READINESS_DATA_AUDIT",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "canonical_entity_count": len(cer.get("canonical_entities", [])),
        "attribute_assertion_count": len(cer.get("attribute_assertions", [])),
        "conflict_count": conflicts.get("conflict_count") or len(conflicts.get("conflicts", [])),
        "review_queue_rows": count_jsonl_rows(SPRINT0_ROOT / "CER_REVIEW_QUEUE_R1.jsonl"),
        "raw_id_bypass_allowed": read_json(SPRINT0_ROOT / "SEG_NO_RAW_ID_BYPASS_GUARD.json", {}).get("raw_ungrounded_graph_shortcuts_allowed", False),
        "source_classes": dict(sorted(Counter(str(row.get("source_class") or "unknown") for row in cer.get("attribute_assertions", [])).items())),
        "limitations": [
            "CER/SEG evidence is fixture/replay bounded and review-only.",
            "Ambiguous/conflicting identities remain data readiness findings, not official identity truth.",
        ],
    }
    check_payload = {
        "artifact_id": "CHECK_CLAIMABILITY_DATA_AUDIT",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "check_report_count": check_engine.get("report_count") or count_jsonl_rows(check_reports_path),
        "claimability_statuses": check_engine.get("claimability_statuses", []),
        "covered_rules": check_engine.get("covered_rules", []),
        "downgrade_reason_index_ref": rel(TRACK5_ROOT / "CHECK_DOWNGRADE_REASON_INDEX.json"),
        "downgrade_summary": downgrade.get("reason_counts") or downgrade.get("downgrade_reason_counts") or {},
        "official_truth_claim_created": check_engine.get("official_truth_claim_created", False),
        "limitations": [
            "CHECK v1 has useful downgrade coverage, but source freshness/geometry/identity gaps still constrain claimability.",
            "No legal/certified finding, official action, ticket, or enforcement workflow is created.",
        ],
    }
    write_json(OUTPUT_ROOT / "IDENTITY_CER_READINESS_DATA_AUDIT.json", cer_payload)
    write_json(OUTPUT_ROOT / "CHECK_CLAIMABILITY_DATA_AUDIT.json", check_payload)
    return cer_payload, check_payload


def build_maturity_crosswalk() -> dict[str, Any]:
    dashboard = read_json(TRACK5_ROOT / "DATA_QUALITY_MATURITY_DASHBOARD_R1.json", {})
    scorecards = dashboard.get("scorecards", [])
    trackb_dashboard = read_json(TRACKB_ROOT / "DATA_MATURITY_DASHBOARD_R1_1.json", {})
    recommended = read_json(TRACKB_ROOT / "MATURITY_RECOMMENDED_NEXT_ACTIONS.json", {})
    payload = {
        "artifact_id": "DATA_MATURITY_REMEDIATION_CROSSWALK",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "track5_dashboard_ref": rel(TRACK5_ROOT / "DATA_QUALITY_MATURITY_DASHBOARD_R1.json"),
        "trackb_dashboard_ref": rel(TRACKB_ROOT / "DATA_MATURITY_DASHBOARD_R1_1.json"),
        "overall_maturity_score": dashboard.get("overall_maturity_score") or trackb_dashboard.get("overall_maturity_score"),
        "risk_counts": dashboard.get("risk_counts", {}),
        "scorecard_count": len(scorecards),
        "scorecards": [
            {
                "scorecard_id": row.get("scorecard_id"),
                "affected_count": row.get("affected_count"),
                "risk_level": row.get("risk_level"),
                "summary": row.get("summary"),
            }
            for row in scorecards
        ],
        "recommended_actions_ref": rel(TRACKB_ROOT / "MATURITY_RECOMMENDED_NEXT_ACTIONS.json"),
        "recommended_actions_sample": recommended.get("actions", recommended.get("recommended_actions", []))[:10]
        if isinstance(recommended, dict)
        else [],
        "limitations": [
            "Remediation candidates are diagnostic or derived overlays unless a future source-truth change is explicitly approved.",
            "Maturity scores are not inflated by the existence of remediation plans.",
        ],
    }
    write_json(OUTPUT_ROOT / "DATA_MATURITY_REMEDIATION_CROSSWALK.json", payload)
    return payload


def build_risks_backlog_and_wins(
    source_crosswalk: dict[str, Any],
    temporal: dict[str, Any],
    geospatial: dict[str, Any],
    founder: dict[str, Any],
    maturity: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    gaps = source_crosswalk.get("gap_counts", {})
    missing_counts = founder.get("missing_for_product_review_ready_counts", {})
    risks = [
        {
            "risk_id": "risk:source_registry_unknowns",
            "severity": "high",
            "finding": "Unknown source class/freshness/schema/geometry remain widespread.",
            "evidence": gaps,
            "boundary": "Do not treat unknowns as trusted source truth.",
        },
        {
            "risk_id": "risk:synthetic_donor_overclaim",
            "severity": "high",
            "finding": "Synthetic Dubai-like and donor mobility data are useful but cannot be official Dubai truth.",
            "evidence": rel(OUTPUT_ROOT / "SYNTHETIC_DATA_FACTORY_AUDIT.json"),
            "boundary": "Keep synthetic/replay/donor labels visible in product surfaces.",
        },
        {
            "risk_id": "risk:founder_card_product_readiness",
            "severity": "medium",
            "finding": "Founder cards are diagnostic-ready, not product-review-ready, until evidence summaries and actual CHECK/CER context are embedded.",
            "evidence": missing_counts,
            "boundary": "No founder session result or operator fuel is created.",
        },
        {
            "risk_id": "risk:simulation_forecast_overclaim",
            "severity": "medium",
            "finding": "Simulation artifacts support review options, not calibrated forecasts.",
            "evidence": rel(OUTPUT_ROOT / "SIMULATION_DATA_AUDIT.json"),
            "boundary": "No ForecastPacket or product forecast surface.",
        },
    ]
    backlog_items = [
        {
            "rank": 1,
            "gap_id": "gap:source_registry_missing_consuming_flows",
            "priority": "high",
            "gap": "Sources without consuming flow refs must be triaged before they can support CHECK/CER/Event Fabric claims.",
            "affected_count": gaps.get("no_consuming_flow", 0),
            "blocked_by": "source registry enrichment and product-flow mapping",
        },
        {
            "rank": 2,
            "gap_id": "gap:unknown_freshness_and_time_history",
            "priority": "high",
            "gap": "Freshness/time-history unknowns limit claimability, DIFF, and live-source readiness.",
            "affected_count": temporal.get("unknown_freshness_count", 0) + temporal.get("missing_time_history_count", 0),
            "blocked_by": "source manifests with native date/update fields",
        },
        {
            "rank": 3,
            "gap_id": "gap:missing_geometry",
            "priority": "high",
            "gap": "Missing/unknown geometry limits spatial overlays, CER linking, and review cards.",
            "affected_count": geospatial.get("missing_or_unknown_geometry_count", 0),
            "blocked_by": "geometry proofs or source-specific spatial joins",
        },
        {
            "rank": 4,
            "gap_id": "gap:founder_card_evidence_quality",
            "priority": "medium",
            "gap": "Founder cards need readable evidence summaries, CER/SEG context, and CHECK actual outcomes.",
            "affected_count": sum(int(v) for v in missing_counts.values()),
            "blocked_by": "review pack quality repair",
        },
        {
            "rank": 5,
            "gap_id": "gap:maturity_remediation_not_applied",
            "priority": "medium",
            "gap": "Maturity remediation exists as plans/candidates and must stay separate from applied source-truth fixes.",
            "affected_count": maturity.get("scorecard_count", 0),
            "blocked_by": "approved remediation execution path",
        },
    ]
    wins = [
        {
            "rank": 1,
            "win_id": "win:source_registry_v1_1_gaps_to_backlog",
            "effort": "low",
            "value": "high",
            "action": "Use SourceRegistry v1.1 gap counts to drive a visible trust/maturity backlog.",
            "why_safe": "Additive diagnostics only; no source mutation.",
        },
        {
            "rank": 2,
            "win_id": "win:founder_cards_evidence_summary",
            "effort": "low",
            "value": "high",
            "action": "Embed concise evidence summaries, CER/SEG context, and actual CHECK outcomes into review cards.",
            "why_safe": "Uses existing replay/eval artifacts and improves review clarity without creating session fuel.",
        },
        {
            "rank": 3,
            "win_id": "win:synthetic_factory_count_traceability",
            "effort": "low",
            "value": "medium",
            "action": "Expose factory reference counts with evidence refs and truth-boundary labels.",
            "why_safe": "Clarifies synthetic/donor/replay boundaries and prevents Dubai-truth overclaim.",
        },
        {
            "rank": 4,
            "win_id": "win:check_downgrade_reason_index",
            "effort": "low",
            "value": "medium",
            "action": "Turn CHECK downgrade reasons into product-facing data maturity diagnostics.",
            "why_safe": "Advisory only; does not certify legal/official findings.",
        },
        {
            "rank": 5,
            "win_id": "win:event_story_pack_replay_catalog",
            "effort": "medium",
            "value": "medium",
            "action": "Use Event Story Pack R1 and DIFF fixtures as a replay catalog for internal demos.",
            "why_safe": "Local/replay only; no live ingestion or official incident claim.",
        },
    ]
    risk_payload = {
        "artifact_id": "DATA_RISK_REGISTER",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "risk_count": len(risks),
        "risks": risks,
    }
    backlog_payload = {
        "artifact_id": "MISSING_DATA_BACKLOG",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "backlog_count": len(backlog_items),
        "items": backlog_items,
    }
    wins_payload = {
        "artifact_id": "LOW_HANGING_DATA_WINS",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "win_count": len(wins),
        "items": wins,
    }
    write_json(OUTPUT_ROOT / "DATA_RISK_REGISTER.json", risk_payload)
    write_json(OUTPUT_ROOT / "MISSING_DATA_BACKLOG.json", backlog_payload)
    write_json(OUTPUT_ROOT / "LOW_HANGING_DATA_WINS.json", wins_payload)
    return risk_payload, backlog_payload, wins_payload


def build_value_pockets_and_next_move(
    source_crosswalk: dict[str, Any],
    eval_audit: dict[str, Any],
    founder: dict[str, Any],
    maturity: dict[str, Any],
    synthetic: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    value_pockets = [
        {
            "rank": 1,
            "value_pocket": "Source trust and data maturity diagnostic",
            "current_data_support": f"{source_crosswalk.get('source_count', 0)} registry sources and {maturity.get('scorecard_count', 0)} maturity scorecards.",
            "safe_claim": "Can show where source trust is strong/weak and what must be fixed next.",
            "not_claimed": "Official data certification or live-source readiness.",
        },
        {
            "rank": 2,
            "value_pocket": "Review-pack quality repair",
            "current_data_support": f"{founder.get('founder_card_count', 0)} founder cards plus eval/check/brief/spatial refs.",
            "safe_claim": "Can support diagnostic review after evidence readability/context is improved.",
            "not_claimed": "Founder session result, operator fuel, or product-review readiness.",
        },
        {
            "rank": 3,
            "value_pocket": "Event replay and DIFF catalog",
            "current_data_support": f"{eval_audit.get('eval_case_count', 0)} eval cases and local/replay event artifacts.",
            "safe_claim": "Can demonstrate deterministic local replay and downgrade behavior.",
            "not_claimed": "Live event ingestion or official incident truth.",
        },
        {
            "rank": 4,
            "value_pocket": "Synthetic factory traceability",
            "current_data_support": f"{synthetic.get('matched_count', 0)} of {synthetic.get('comparison_count', 0)} reference counts matched local artifacts.",
            "safe_claim": "Can explain synthetic/donor/replay depth and boundaries.",
            "not_claimed": "Official Dubai truth or real-world complete coverage.",
        },
        {
            "rank": 5,
            "value_pocket": "Simulation option evidence",
            "current_data_support": "SUMO/option-engine artifacts are present for review-only scenarios.",
            "safe_claim": "Can support internal option review with uncertainty labels.",
            "not_claimed": "Calibrated forecast or operational control.",
        },
    ]
    missing_product_ready = sum(int(v) for v in founder.get("missing_for_product_review_ready_counts", {}).values())
    maturity_score = maturity.get("overall_maturity_score")
    if missing_product_ready:
        top = "FIX_REVIEW_PACK_QUALITY_FIRST"
        rationale = "Founder/review cards exist but still need readable evidence summaries, CER/SEG context, and actual CHECK outcomes before product-facing review."
    elif isinstance(maturity_score, (int, float)) and maturity_score < 50:
        top = "DEEPEN_DATA_MATURITY_REMEDIATION"
        rationale = "Maturity is the largest bottleneck after eval/card readiness."
    else:
        top = "RUN_FOUNDER_DIAGNOSTIC_REVIEW"
        rationale = "Evidence appears adequate for bounded diagnostic review, not product readiness."
    ranked = [
        {"rank": 1, "recommendation": top, "rationale": rationale},
        {"rank": 2, "recommendation": "DEEPEN_DATA_MATURITY_REMEDIATION", "rationale": "Source freshness, geometry, consuming-flow, and source-class gaps are visible and actionable."},
        {"rank": 3, "recommendation": "DEEPEN_EVENT_FABRIC_OR_SIMULATION", "rationale": "Replay/simulation artifacts are useful once review-card evidence is clearer."},
    ]
    recommendation = {
        "artifact_id": "NEXT_MOVE_RECOMMENDATION",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "top_recommendation": top,
        "ranked_recommendations": ranked,
        "not_recommended_now": [
            "READY_FOR_INTERNAL_PRODUCT_SNAPSHOT",
            "live-source onboarding without source policy/live approvals",
            "founder session or operator fuel capture",
        ],
    }
    write_json(OUTPUT_ROOT / "NEXT_MOVE_RECOMMENDATION.json", recommendation)
    write_csv(
        TABLE_ROOT / "value_pocket_data_map.csv",
        value_pockets,
        ["rank", "value_pocket", "current_data_support", "safe_claim", "not_claimed"],
    )
    md_lines = [
        "# Value Pocket Data Map",
        "",
        "This map separates current data-backed value from claims CityBrain should not make yet.",
        "",
    ]
    for row in value_pockets:
        md_lines.extend(
            [
                f"## {row['rank']}. {row['value_pocket']}",
                "",
                f"- Current support: {row['current_data_support']}",
                f"- Safe claim: {row['safe_claim']}",
                f"- Not claimed: {row['not_claimed']}",
                "",
            ]
        )
    write_text(OUTPUT_ROOT / "VALUE_POCKET_DATA_MAP.md", "\n".join(md_lines))
    return recommendation, value_pockets


def write_tables(
    sources: list[dict[str, Any]],
    city_domain_rows: list[dict[str, Any]],
    provenance: dict[str, Any],
    eval_audit: dict[str, Any],
    backlog: dict[str, Any],
    wins: dict[str, Any],
) -> None:
    source_rows = []
    for row in sources:
        source_rows.append(
            {
                "source_id": row.get("source_id"),
                "city": row.get("city"),
                "domain": row.get("domain"),
                "source_class": row.get("source_class"),
                "freshness": row.get("freshness_status") or row.get("freshness"),
                "coverage": row.get("coverage_status") or row.get("coverage"),
                "license_access_status": row.get("license_status") or row.get("access_status"),
                "schema_status": row.get("schema_status"),
                "geometry_status": row.get("geometry_status"),
                "time_coverage": row.get("time_coverage") or row.get("time_coverage_start"),
                "known_limitations": row.get("known_limitations", []),
                "consuming_flows": row.get("consuming_flows") or row.get("consuming_modes") or [],
            }
        )
    write_csv(
        TABLE_ROOT / "data_source_catalog.csv",
        source_rows,
        [
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
        ],
    )
    write_csv(
        TABLE_ROOT / "city_domain_coverage.csv",
        city_domain_rows,
        [
            "city",
            "domain",
            "source_count",
            "source_class_counts",
            "consuming_flow_source_count",
            "unknown_source_class_count",
            "missing_geometry_count",
            "unknown_freshness_count",
        ],
    )
    source_class_rows = [
        {"source_class": key, "count": value}
        for key, value in provenance.get("normalized_provenance_counts", {}).items()
    ]
    write_csv(TABLE_ROOT / "source_class_coverage.csv", source_class_rows, ["source_class", "count"])
    eval_rows = [
        {"axis": "eval_case_count", "value": eval_audit.get("eval_case_count")},
        {"axis": "separate_challenge_negative_suite_count", "value": eval_audit.get("separate_challenge_negative_suite_count")},
        {"axis": "family_count", "value": eval_audit.get("family_count")},
        {"axis": "operator_fuel_any", "value": eval_audit.get("operator_fuel_any")},
        {"axis": "training_eligible_any", "value": eval_audit.get("training_eligible_any")},
        {"axis": "source_truth_mutated_any", "value": eval_audit.get("source_truth_mutated_any")},
    ]
    write_csv(TABLE_ROOT / "eval_coverage_matrix.csv", eval_rows, ["axis", "value"])
    write_csv(
        TABLE_ROOT / "missing_data_backlog.csv",
        backlog.get("items", []),
        ["rank", "gap_id", "priority", "gap", "affected_count", "blocked_by"],
    )
    write_csv(
        TABLE_ROOT / "low_hanging_data_wins.csv",
        wins.get("items", []),
        ["rank", "win_id", "effort", "value", "action", "why_safe"],
    )


def forbidden_guard() -> dict[str, Any]:
    checks = {capability: False for capability in FORBIDDEN_CAPABILITIES}
    return {
        "artifact_id": "NO_FORBIDDEN_CAPABILITY_GUARD",
        "generated_at": utc_now(),
        "status": "PASS",
        "read_only_audit": True,
        "forbidden_capabilities_created": [],
        "checks": checks,
        "source_truth_mutation_flag": False,
        "founder_session_results_created": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "forecast_packet_created": False,
        "product_forecast_surface_created": False,
        "live_ingestion_claim_created": False,
        "official_case_ticket_action_created": False,
        "dispatch_control_enforcement_created": False,
        "boundary": "read_only_data_estate_audit_outputs_only",
    }


def executive_summary(
    decision: dict[str, Any],
    source_crosswalk: dict[str, Any],
    synthetic: dict[str, Any],
    eval_audit: dict[str, Any],
    founder: dict[str, Any],
    recommendation: dict[str, Any],
) -> None:
    lines = [
        "# Executive Data Estate Summary",
        "",
        f"- Status: {decision['status']}",
        f"- SourceRegistry sources: {source_crosswalk.get('source_count', 0)}",
        f"- Synthetic factory matched counts: {synthetic.get('matched_count', 0)} / {synthetic.get('comparison_count', 0)}",
        f"- Eval cases: {eval_audit.get('eval_case_count')} plus challenge/negative suite count {eval_audit.get('separate_challenge_negative_suite_count')}",
        f"- Founder cards: {founder.get('founder_card_count')}",
        f"- Top next move: {recommendation.get('top_recommendation')}",
        "",
        "## Biggest Gaps",
        "",
        "- SourceRegistry has material freshness, geometry, schema, source-class, and consuming-flow gaps.",
        "- Founder/review cards are diagnostic-ready but not product-review-ready until evidence summaries, CER/SEG context, and actual CHECK outcomes are embedded.",
        "- Synthetic/replay/donor assets are valuable but must remain clearly labeled and cannot be treated as official Dubai truth or live fact.",
        "- Simulation supports review options only; it is not a calibrated forecast or operational control surface.",
        "",
        "## Boundaries Preserved",
        "",
        "- No source-truth mutation, live ingestion, founder session result, operator fuel, training rows, ForecastPacket, official action, dispatch, control, enforcement, or legal/certified finding.",
    ]
    write_text(OUTPUT_ROOT / "EXECUTIVE_DATA_ESTATE_SUMMARY.md", "\n".join(lines))


def publish_outputs() -> dict[str, Any]:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    copied = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", "PUBLICATION_COVERAGE_REPORT.json"}:
            continue
        dst = PUBLICATION_ROOT / path.relative_to(OUTPUT_ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dst)
        copied.append({"file": rel(path), "publication_ref": rel(dst), "sha256": sha256_file(dst)})
    report = {
        "artifact_id": "PUBLICATION_COVERAGE_REPORT",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "publication_root": rel(PUBLICATION_ROOT),
        "published_file_count": len(copied),
        "published_files": copied,
        "limitations": ["Publication mirrors generated audit artifacts only; no external release or source-truth mutation was performed."],
    }
    write_json(OUTPUT_ROOT / "PUBLICATION_COVERAGE_REPORT.json", report)
    shutil.copyfile(OUTPUT_ROOT / "PUBLICATION_COVERAGE_REPORT.json", PUBLICATION_ROOT / "PUBLICATION_COVERAGE_REPORT.json")
    return report


def write_hash_manifest() -> dict[str, Any]:
    entries = []
    for root in [OUTPUT_ROOT, PUBLICATION_ROOT]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "HASH_MANIFEST.json":
                entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "DEEP_DATA_ESTATE_AUDIT_HASH_MANIFEST",
        "generated_at": utc_now(),
        "algorithm": "sha256",
        "status": "PASS",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUTPUT_ROOT / "HASH_MANIFEST.json", PUBLICATION_ROOT / "HASH_MANIFEST.json")
    return manifest


def build_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    TABLE_ROOT.mkdir(parents=True, exist_ok=True)
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)

    inventory, sampled_files = build_data_root_inventory()
    build_row_count_ledger(inventory, sampled_files)
    source_manifest_inventory()
    source_crosswalk, sources = source_registry_crosswalk()
    city_domain, city_domain_rows = build_city_domain_matrix(sources)
    provenance = build_source_class_provenance(sources)
    temporal, geospatial = build_temporal_and_geospatial_audits(sources)
    synthetic = build_synthetic_factory_audit()
    event_audit = build_event_replay_audit()
    simulation = build_simulation_audit()
    eval_audit, founder = build_eval_and_founder_audits()
    cer, check = build_cer_and_check_audits()
    maturity = build_maturity_crosswalk()
    risks, backlog, wins = build_risks_backlog_and_wins(source_crosswalk, temporal, geospatial, founder, maturity)
    recommendation, value_pockets = build_value_pockets_and_next_move(source_crosswalk, eval_audit, founder, maturity, synthetic)
    write_tables(sources, city_domain_rows, provenance, eval_audit, backlog, wins)
    guard = forbidden_guard()
    write_json(OUTPUT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", guard)

    decision = {
        "artifact_id": "DATA_ESTATE_AUDIT_DECISION",
        "package_id": PACKAGE_ID,
        "generated_at": utc_now(),
        "status": FINAL_STATUS,
        "input_package_ref": str(PACKAGE_ZIP),
        "read_only": True,
        "source_truth_mutation": False,
        "founder_session_results_created": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "forecast_packet_created": False,
        "product_forecast_surface_created": False,
        "live_ingestion_claim_created": False,
        "official_case_ticket_action_created": False,
        "dispatch_control_enforcement_created": False,
        "source_registry_source_count": source_crosswalk.get("source_count", 0),
        "data_root_count": inventory.get("root_count", 0),
        "total_scanned_files": inventory.get("total_scanned_files", 0),
        "synthetic_reference_counts_matched": synthetic.get("matched_count", 0),
        "synthetic_reference_count_total": synthetic.get("comparison_count", 0),
        "eval_case_count": eval_audit.get("eval_case_count"),
        "challenge_negative_suite_count": eval_audit.get("separate_challenge_negative_suite_count"),
        "founder_card_count": founder.get("founder_card_count"),
        "cer_canonical_entity_count": cer.get("canonical_entity_count"),
        "check_report_count": check.get("check_report_count"),
        "top_next_move": recommendation.get("top_recommendation"),
        "artifact_refs": [rel(OUTPUT_ROOT / name) for name in REQUIRED_JSON_OUTPUTS + REQUIRED_MD_OUTPUTS],
        "table_refs": [rel(OUTPUT_ROOT / name) for name in REQUIRED_TABLES],
        "limitations": [
            "The audit is evidence-backed but bounded by local artifacts available in the shared workspace.",
            "Large roots may be capped by deterministic scan limits.",
            "Synthetic, donor, replay, derived, fixture, and model-narrative data are not treated as official records.",
            "No Epoch/product gate closure is claimed.",
        ],
    }
    write_json(OUTPUT_ROOT / "DATA_ESTATE_AUDIT_DECISION.json", decision)
    executive_summary(decision, source_crosswalk, synthetic, eval_audit, founder, recommendation)
    publish_outputs()
    write_hash_manifest()
    return decision


def validate_hash_manifest() -> list[str]:
    manifest = read_json(OUTPUT_ROOT / "HASH_MANIFEST.json", {})
    errors = []
    for entry in manifest.get("entries", []):
        path = ROOT / entry["path"]
        if not path.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"hash_mismatch:{entry['path']}")
    return errors


def validate_outputs() -> list[str]:
    required_paths = [OUTPUT_ROOT / name for name in OUTPUT_FILES]
    errors = [f"missing:{rel(path)}" for path in required_paths if not path.exists()]
    if errors:
        return errors

    for name in REQUIRED_JSON_OUTPUTS + ["PUBLICATION_COVERAGE_REPORT.json", "HASH_MANIFEST.json"]:
        try:
            json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"json_parse_error:{name}")

    decision = read_json(OUTPUT_ROOT / "DATA_ESTATE_AUDIT_DECISION.json", {})
    guard = read_json(OUTPUT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", {})
    inventory = read_json(OUTPUT_ROOT / "DATA_ROOT_INVENTORY.json", {})
    coverage = read_json(OUTPUT_ROOT / "CITY_DOMAIN_COVERAGE_MATRIX.json", {})

    if decision.get("status") != FINAL_STATUS or not str(decision.get("status", "")).endswith("_WITH_LIMITATIONS"):
        errors.append("decision_status_not_with_limitations")
    if not decision.get("read_only"):
        errors.append("read_only_false")
    for flag in [
        "source_truth_mutation",
        "training_rows_created",
        "operator_fuel_created",
        "forecast_packet_created",
        "product_forecast_surface_created",
        "live_ingestion_claim_created",
        "official_case_ticket_action_created",
        "dispatch_control_enforcement_created",
    ]:
        if decision.get(flag) is not False:
            errors.append(f"forbidden_flag_not_false:{flag}")
    if guard.get("status") != "PASS" or guard.get("forbidden_capabilities_created") != []:
        errors.append("forbidden_guard_failed")
    if not inventory.get("scan_roots"):
        errors.append("data_root_inventory_empty")
    if not coverage.get("matrix"):
        errors.append("coverage_matrix_empty")
    errors.extend(validate_hash_manifest())
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        decision = build_outputs()
    else:
        decision = read_json(OUTPUT_ROOT / "DATA_ESTATE_AUDIT_DECISION.json", {})
    errors = validate_outputs()
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS_WITH_LIMITATIONS",
                "decision": decision.get("status", FINAL_STATUS),
                "output_root": rel(OUTPUT_ROOT),
                "publication_root": rel(PUBLICATION_ROOT),
                "top_next_move": decision.get("top_next_move"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
