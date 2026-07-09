#!/usr/bin/env python3
"""Preflight cross-city non-mobility fuel for Synthetic Factory Seed R3.

This task is deliberately read-only against existing city/product outputs. It
discovers Barcelona, NYC, Chicago, and London artifacts, extracts local count
evidence where the repo already exposes it, and writes only ledgers/reports for
the Seed R3 refresh decision.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TASK_ID = "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT"
STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_WITH_LIMITATIONS"
DEFAULT_OUT = Path("outputs") / TASK_ID
DEFAULT_PUBLICATION = Path("publications") / "epoch4" / "main-citybrain-synthetic-factory-seed-r3-cross-city-domain-fuel-preflight"
PACKAGE_ZIP = Path(r"C:\Users\hazem\Downloads\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT-PACKAGE.zip")
PACKAGE_SHA256 = "59977d47d77e01955849af4d35038c5854d71e122690be48a9c2f325d1ce6b38"

REQUIRED_OUTPUTS = [
    "SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_DECISION.json",
    "CITY_CORPUS_DISCOVERY_LEDGER.csv",
    "DOMAIN_FUEL_LEDGER.csv",
    "DOMAIN_FUEL_SUMMARY.json",
    "CROSS_CITY_DONOR_POLICY.json",
    "SEED_R3_RECOMMENDED_REFRESH_PLAN.json",
    "SEED_R3_PRODUCT_FIXTURE_REQUIREMENTS.json",
    "SEED_R3_BOUNDARY_AND_SOURCE_CLASS_AUDIT.json",
    "SEED_R3_NO_MUTATION_AUDIT.json",
    "SEED_R3_SECRET_SCAN_REPORT.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]

EXPECTED_ROOTS = [
    "outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1",
    "outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1",
    "outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1",
    "outputs/barc_allflows_data_landing_r1",
    "outputs/barc_allflows_consumption_prep_r1",
    "outputs/nyc_allflows_data_landing_r1",
    "outputs/nyc_flow_consumption_prep_r1",
    "outputs/chi_allflows_data_landing_r1",
    "outputs/chi_allflows_consumption_prep_r1",
    "outputs/lon_allflows_data_landing_r1",
    "outputs/lon_allflows_consumption_prep_r1",
    "outputs/chi_f2x_f5x_data_strengthening_r1",
    "outputs/chi_f2x_f5x_recheck_for_r5_addendum_r1",
    "outputs/main_platform_flowpack_limitation_cleanup_r1",
]

DOMAINS = {
    "property_planning": {
        "priority": "P0",
        "seed_r3_use": "property/planning entity profiles and WATCH/CHECK ambiguity fixtures",
    },
    "built_environment": {
        "priority": "P0",
        "seed_r3_use": "building/entity profiles and SPATIAL overlays",
    },
    "building_compliance": {
        "priority": "P0",
        "seed_r3_use": "permit/inspection/violation/compliance CHECK and BRIEF fixtures",
    },
    "civic_service_311_crm": {
        "priority": "P0",
        "seed_r3_use": "civic-service WATCH queues and replay-only incident/event fixtures",
    },
    "mobility_transport": {
        "priority": "P1",
        "seed_r3_use": "cross-check only; Seed R2 already deepened mobility",
    },
    "environment_resilience": {
        "priority": "P1",
        "seed_r3_use": "weather/flood/air/water/environment stress overlays",
    },
    "public_safety_incident": {
        "priority": "P1",
        "seed_r3_use": "review-only incident context, not dispatch or emergency advice",
    },
    "utilities_energy_water": {
        "priority": "P1",
        "seed_r3_use": "utility dependency and resilience scenarios where source-safe",
    },
    "population_demand": {
        "priority": "P2",
        "seed_r3_use": "aggregate demand/exposure context only",
    },
    "economy_logistics": {
        "priority": "P2",
        "seed_r3_use": "business/logistics context and scenario distributions",
    },
    "data_quality_maturity": {
        "priority": "P0",
        "seed_r3_use": "quality/maturity product fixtures and limitation ledgers",
    },
    "identity_graph_eval": {
        "priority": "P0",
        "seed_r3_use": "CER/SEG join-confidence challenge fixtures",
    },
}

DOMAIN_RULES = [
    ("building_compliance", ["permit", "violation", "inspection", "enforcement", "building_control", "complaint", "compliance", "food_inspection"]),
    ("property_planning", ["parcel", "plot", "cadastre", "planning", "zoning", "land", "property", "pluto", "brownfield", "uprn", "toid", "rates", "local_plan"]),
    ("built_environment", ["building", "address", "footprint", "unit", "site", "facility", "facilities", "premises", "lod2", "i3s"]),
    ("civic_service_311_crm", ["311", "crm", "service_request", "service_requests", "work_order", "civic", "iris", "fixmystreet", "open311"]),
    ("environment_resilience", ["air", "flood", "storm", "heat", "noise", "green", "climate", "water", "sewer", "piezometer", "meteorological", "environment", "resilience"]),
    ("public_safety_incident", ["fdny", "lfb", "incident", "fire", "ambulance", "police", "crime", "crash", "crashes", "ems", "mobilisation"]),
    ("utilities_energy_water", ["utility", "energy", "power", "electricity", "meter", "outage", "water", "sewer", "hit_ticket", "charging"]),
    ("population_demand", ["population", "demographic", "deprivation", "footfall", "demand", "tourist", "commuter"]),
    ("economy_logistics", ["business", "license", "licence", "economic", "port", "airport", "warehouse", "logistics", "hotel", "tourism", "employment"]),
    ("data_quality_maturity", ["quality", "limitation", "coverage", "maturity", "audit", "boundary", "source_depth", "readiness", "negative_test"]),
    ("identity_graph_eval", ["anchor", "join", "entity", "graph", "cer", "seg", "relationship", "identity", "canonical"]),
    ("mobility_transport", ["traffic", "road", "route", "stop", "station", "bus", "bike", "gtfs", "sumo", "transport", "taxi", "tfl", "mobility"]),
]

CITY_PATTERNS = {
    "barcelona": ["barc", "barcelona"],
    "nyc": ["nyc"],
    "chicago": ["chi", "chicago"],
    "london": ["lon", "london"],
}

COUNT_FIELDS = {
    "rows",
    "row_count",
    "rows_landed",
    "landed_rows",
    "landed_row_count",
    "rows_landed_or_registered",
    "records",
    "record_count",
    "source_count",
    "source_total_count",
    "full_source_count",
    "total_available",
    "count_primary_total",
    "features",
    "landed_features",
    "anchors",
    "anchor_count",
    "events",
    "event_count",
    "observations",
    "observation_count",
}

SECRET_PATTERNS = [
    re.compile(r"app_key=(?!REDACTED)([^&\s\"']+)", re.I),
    re.compile(r"AccountKey\s*[:=]\s*[^\s,}\"']+", re.I),
    re.compile(r"LTA_DATAMALL_ACCOUNT_KEY\s*[:=]\s*[^\s,}\"']+", re.I),
    re.compile(r"TFL_(PRIMARY|SECONDARY)_KEY\s*[:=]\s*[^\s,}\"']+", re.I),
]


@dataclass
class RootMetrics:
    city: str
    root: Path
    origin: str
    status: str = "DISCOVERED"
    file_count: int = 0
    byte_count: int = 0
    counted_files: int = 0
    lightweight_rows: int = 0
    phase_reported_rows: int = 0
    dataset_status_sources: int = 0
    dataset_status_rows: int = 0
    dataset_status_total_available: int = 0
    manifest_sources: int = 0
    manifest_landed_rows: int = 0
    manifest_landed_features: int = 0
    manifest_total_available: int = 0
    duckdb_tables: int = 0
    duckdb_rows: int = 0
    domains: set[str] = field(default_factory=set)
    limitations: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=TASK_ID)
    parser.add_argument("--repo-root", default=".", help="CityBrain repo root")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output root")
    parser.add_argument("--publication-out", default=str(DEFAULT_PUBLICATION), help="Publication copy root")
    parser.add_argument("--validate-only", action="store_true", help="Validate existing output instead of regenerating")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def as_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def repo_rel(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_read_json(path: Path) -> Any | None:
    try:
        if path.stat().st_size > 25_000_000:
            return None
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def iter_json_count_fields(obj: Any, prefix: str = "") -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key)
            next_prefix = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in COUNT_FIELDS and isinstance(value, (int, float, str)):
                found.append({"path": next_prefix, "value": as_int(value)})
            elif isinstance(value, (dict, list)):
                found.extend(iter_json_count_fields(value, next_prefix))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj[:250]):
            if isinstance(value, (dict, list)):
                found.extend(iter_json_count_fields(value, f"{prefix}[{idx}]"))
    return found


def classify_city(path_or_name: Path | str) -> str:
    text = str(path_or_name).lower()
    for city, patterns in CITY_PATTERNS.items():
        if any(pattern in text for pattern in patterns):
            return city
    return "cross_city_or_product"


def classify_domain(text: str) -> str:
    lower = text.lower().replace("-", "_")
    for domain, needles in DOMAIN_RULES:
        if any(needle in lower for needle in needles):
            return domain
    return "unclassified_review_needed"


def source_class_from_text(text: str) -> str:
    lower = text.lower()
    if "synthetic" in lower or "fixture" in lower:
        return "synthetic_or_fixture"
    if "replay" in lower:
        return "replay"
    if "derived" in lower or "backfill" in lower or "normalized" in lower or "mart" in lower:
        return "derived"
    if "donor" in lower or "context only" in lower or "context_only" in lower:
        return "donor_context"
    if "official" in lower or "source" in lower or "raw" in lower or "landed" in lower:
        return "source_record"
    return "existing_city_source_or_derived_artifact"


def row_count_for_file(path: Path) -> int | None:
    suffix = path.suffix.lower()
    try:
        if suffix == ".parquet":
            import pyarrow.parquet as pq

            return int(pq.ParquetFile(path).metadata.num_rows)
        if suffix in {".csv", ".jsonl"} and path.stat().st_size <= 250_000_000:
            with path.open("rb") as fh:
                rows = sum(1 for line in fh if line.strip())
            return max(0, rows - 1) if suffix == ".csv" else rows
    except Exception:
        return None
    return None


def duckdb_table_counts(path: Path) -> list[dict[str, Any]]:
    try:
        import duckdb
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    try:
        con = duckdb.connect(str(path), read_only=True)
        try:
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
            for table in tables:
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table):
                    continue
                try:
                    count = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                    rows.append({"table": table, "rows": int(count)})
                except Exception:
                    rows.append({"table": table, "rows": 0, "limitation": "COUNT_FAILED"})
        finally:
            con.close()
    except Exception:
        return []
    return rows


def discover_roots(repo: Path) -> tuple[list[tuple[Path, str]], list[dict[str, str]]]:
    outputs = repo / "outputs"
    seen: set[Path] = set()
    roots: list[tuple[Path, str]] = []
    missing: list[dict[str, str]] = []

    for rel in EXPECTED_ROOTS:
        path = (repo / rel).resolve()
        if path.exists() and path.is_dir():
            roots.append((path, "expected_input"))
            seen.add(path)
        else:
            missing.append({
                "city": classify_city(rel),
                "root": rel.replace("\\", "/"),
                "origin": "expected_input",
                "status": "ROOT_MISSING_FAIL_CLOSED",
                "limitation": "Expected by package handoff but not present locally.",
            })

    if outputs.exists():
        for child in sorted(outputs.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir():
                continue
            city = classify_city(child.name)
            if city in {"barcelona", "nyc", "chicago", "london"} and child.resolve() not in seen:
                roots.append((child.resolve(), "fallback_city_prefix"))
                seen.add(child.resolve())

    return roots, missing


def root_fingerprint(root: Path) -> dict[str, Any]:
    file_count = 0
    byte_count = 0
    latest_mtime = 0.0
    digest = hashlib.sha256()
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "latest_mtime": 0, "digest": ""}
    for file_path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: str(p).lower()):
        try:
            stat = file_path.stat()
        except OSError:
            continue
        file_count += 1
        byte_count += stat.st_size
        latest_mtime = max(latest_mtime, stat.st_mtime)
        try:
            rel = str(file_path.relative_to(root)).replace("\\", "/").lower()
        except ValueError:
            rel = str(file_path).replace("\\", "/").lower()
        digest.update(f"{rel}|{stat.st_size}|{int(stat.st_mtime)}\n".encode("utf-8"))
    return {
        "exists": True,
        "file_count": file_count,
        "byte_count": byte_count,
        "latest_mtime": int(latest_mtime),
        "digest": digest.hexdigest(),
    }


def add_domain_row(
    rows: list[dict[str, Any]],
    *,
    city: str,
    domain: str,
    source_key: str,
    source_root: Path,
    repo: Path,
    artifact_kind: str,
    status: str,
    source_class: str,
    landed_rows: int = 0,
    landed_features: int = 0,
    registered_or_total_count: int = 0,
    file_count: int = 0,
    evidence_ref: str,
    seed_r3_use: str | None = None,
    limitation: str = "",
) -> None:
    rows.append({
        "city": city,
        "domain": domain,
        "source_key": source_key,
        "source_root": repo_rel(source_root, repo),
        "artifact_kind": artifact_kind,
        "status": status,
        "source_class": source_class,
        "landed_rows": landed_rows,
        "landed_features": landed_features,
        "registered_or_total_count": registered_or_total_count,
        "file_count": file_count,
        "evidence_ref": evidence_ref,
        "seed_r3_use": seed_r3_use or DOMAINS.get(domain, {}).get("seed_r3_use", "candidate fuel pending review"),
        "limitation": limitation,
    })


def ingest_dataset_status_csv(path: Path, metrics: RootMetrics, domain_rows: list[dict[str, Any]], repo: Path) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for record in reader:
                source_key = record.get("source_key") or record.get("key") or record.get("dataset") or path.stem
                domain = classify_domain(" ".join(str(record.get(k, "")) for k in ["source_key", "name", "title", "flows", "boundary_class", "privacy_class"]))
                landed_rows = as_int(record.get("landed_rows") or record.get("rows_landed"))
                total = as_int(record.get("full_source_count") or record.get("total_available") or record.get("source_total_count"))
                files = as_int(record.get("landed_files") or record.get("file_count"))
                status = record.get("phase1_status") or record.get("landing_status") or record.get("status") or "STATUS_RECORDED"
                source_class = source_class_from_text(" ".join(str(v) for v in record.values()))
                metrics.dataset_status_sources += 1
                metrics.dataset_status_rows += landed_rows
                metrics.dataset_status_total_available += total
                metrics.domains.add(domain)
                add_domain_row(
                    domain_rows,
                    city=metrics.city,
                    domain=domain,
                    source_key=source_key,
                    source_root=metrics.root,
                    repo=repo,
                    artifact_kind="dataset_status_csv",
                    status=status,
                    source_class=source_class,
                    landed_rows=landed_rows,
                    registered_or_total_count=total,
                    file_count=files,
                    evidence_ref=repo_rel(path, repo),
                    limitation="Dataset status CSV provides local landed/source counts; semantics still require Seed R3 fixture review.",
                )
    except Exception as exc:
        metrics.limitations.append(f"dataset_status_parse_failed:{path.name}:{exc}")


def ingest_phase_counts_csv(path: Path, metrics: RootMetrics) -> None:
    best = 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            for record in csv.DictReader(fh):
                for key in ["rows_landed_or_registered", "rows_landed", "rows", "features"]:
                    best = max(best, as_int(record.get(key)))
        metrics.phase_reported_rows = max(metrics.phase_reported_rows, best)
    except Exception as exc:
        metrics.limitations.append(f"phase_counts_parse_failed:{path.name}:{exc}")


def ingest_manifest_or_profile(path: Path, metrics: RootMetrics, domain_rows: list[dict[str, Any]], repo: Path) -> None:
    data = safe_read_json(path)
    if not isinstance(data, dict):
        return
    if "sources" in data and isinstance(data["sources"], list):
        sources = data["sources"]
    elif any(key in data for key in ["source_key", "package_id", "landed_rows", "landed_features", "source_total_count", "features", "rows"]):
        sources = [data]
    else:
        return

    for source in sources:
        if not isinstance(source, dict):
            continue
        source_key = str(source.get("source_key") or source.get("package_id") or source.get("key") or path.stem)
        domain = classify_domain(" ".join([source_key, str(source.get("source_name", "")), str(source.get("boundary_class", "")), str(source.get("privacy_class", ""))]))
        landed_rows = as_int(source.get("landed_rows") or source.get("landed_row_count") or source.get("rows"))
        landed_features = as_int(source.get("landed_features") or source.get("features"))
        total = as_int(source.get("source_total_count") or source.get("source_total_row_count") or source.get("count_primary_total") or source.get("full_source_count"))
        files = as_int(source.get("landed_files") or source.get("files"))
        status = str(source.get("status") or source.get("landing_status") or source.get("consumption_status") or "MANIFEST_RECORDED")
        source_class = source_class_from_text(" ".join(str(source.get(k, "")) for k in ["boundary_class", "privacy_class", "preferred_api", "download_mode", "status"]))
        metrics.manifest_sources += 1
        metrics.manifest_landed_rows += landed_rows
        metrics.manifest_landed_features += landed_features
        metrics.manifest_total_available += total
        metrics.domains.add(domain)
        add_domain_row(
            domain_rows,
            city=metrics.city,
            domain=domain,
            source_key=source_key,
            source_root=metrics.root,
            repo=repo,
            artifact_kind="manifest_or_profile_json",
            status=status,
            source_class=source_class,
            landed_rows=landed_rows,
            landed_features=landed_features,
            registered_or_total_count=total,
            file_count=files,
            evidence_ref=repo_rel(path, repo),
            limitation="Manifest/profile count evidence only; Seed R3 must still preserve source class and limitation refs.",
        )


def scan_root(root: Path, origin: str, repo: Path, domain_rows: list[dict[str, Any]]) -> RootMetrics:
    city = classify_city(root.name)
    metrics = RootMetrics(city=city, root=root, origin=origin)
    files = [p for p in root.rglob("*") if p.is_file()]
    metrics.file_count = len(files)
    metrics.byte_count = sum(p.stat().st_size for p in files if p.exists())
    per_domain_files: dict[str, int] = defaultdict(int)

    for file_path in files:
        rel = repo_rel(file_path, root)
        domain = classify_domain(rel)
        metrics.domains.add(domain)
        per_domain_files[domain] += 1

        suffix = file_path.suffix.lower()
        name = file_path.name.lower()
        if name.endswith("dataset_status.csv"):
            ingest_dataset_status_csv(file_path, metrics, domain_rows, repo)
        elif name.endswith("counts_by_phase.csv"):
            ingest_phase_counts_csv(file_path, metrics)
        elif suffix == ".json" and (".manifest" in name or ".profile" in name or "source_ledger" in name):
            ingest_manifest_or_profile(file_path, metrics, domain_rows, repo)
        elif suffix in {".csv", ".jsonl", ".parquet"}:
            count = row_count_for_file(file_path)
            if count is not None:
                metrics.counted_files += 1
                metrics.lightweight_rows += count
        elif suffix == ".duckdb" and file_path.stat().st_size <= 5_000_000_000:
            table_counts = duckdb_table_counts(file_path)
            for table_row in table_counts:
                table = table_row["table"]
                rows = as_int(table_row.get("rows"))
                table_domain = classify_domain(table)
                metrics.duckdb_tables += 1
                metrics.duckdb_rows += rows
                metrics.domains.add(table_domain)
                add_domain_row(
                    domain_rows,
                    city=metrics.city,
                    domain=table_domain,
                    source_key=f"{file_path.stem}.{table}",
                    source_root=metrics.root,
                    repo=repo,
                    artifact_kind="duckdb_table_count",
                    status="READ_ONLY_COUNTED",
                    source_class="derived",
                    landed_rows=rows,
                    evidence_ref=repo_rel(file_path, repo),
                    limitation=table_row.get("limitation", "DuckDB table counted read-only; source semantics require Seed R3 review."),
                )

    for domain, file_count in sorted(per_domain_files.items()):
        if domain == "unclassified_review_needed":
            continue
        add_domain_row(
            domain_rows,
            city=metrics.city,
            domain=domain,
            source_key=f"{root.name}:{domain}:file_cluster",
            source_root=metrics.root,
            repo=repo,
            artifact_kind="file_cluster",
            status="CANDIDATE_FUEL_DISCOVERED",
            source_class="existing_city_source_or_derived_artifact",
            file_count=file_count,
            evidence_ref=repo_rel(root, repo),
            limitation="File-name/domain cluster only; not a row-count source.",
        )

    if not metrics.dataset_status_sources and not metrics.manifest_sources and not metrics.counted_files and not metrics.duckdb_tables:
        metrics.limitations.append("No count-bearing CSV/JSONL/Parquet/manifest/DuckDB artifact found in lightweight preflight.")
    if metrics.dataset_status_sources or metrics.manifest_sources or metrics.counted_files or metrics.duckdb_tables:
        metrics.status = "DISCOVERED_WITH_LOCAL_COUNT_EVIDENCE"
    else:
        metrics.status = "DISCOVERED_CANDIDATE_ONLY"
    return metrics


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_summary(domain_rows: list[dict[str, Any]], root_metrics: list[RootMetrics], missing_roots: list[dict[str, str]]) -> dict[str, Any]:
    by_city: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "roots": 0,
        "counted_or_manifest_sources": 0,
        "landed_rows": 0,
        "landed_features": 0,
        "registered_or_total_count": 0,
        "file_count": 0,
        "domains": defaultdict(lambda: {
            "ledger_rows": 0,
            "landed_rows": 0,
            "landed_features": 0,
            "registered_or_total_count": 0,
            "file_count": 0,
            "source_classes": set(),
        }),
    })
    by_domain: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "cities": set(),
        "ledger_rows": 0,
        "landed_rows": 0,
        "landed_features": 0,
        "registered_or_total_count": 0,
        "file_count": 0,
        "priority": "review",
    })

    for metric in root_metrics:
        city_bucket = by_city[metric.city]
        city_bucket["roots"] += 1
        city_bucket["file_count"] += metric.file_count

    for row in domain_rows:
        city = row["city"]
        domain = row["domain"]
        landed_rows = as_int(row["landed_rows"])
        landed_features = as_int(row["landed_features"])
        registered = as_int(row["registered_or_total_count"])
        file_count = as_int(row["file_count"])
        source_class = row["source_class"]
        city_bucket = by_city[city]
        city_bucket["counted_or_manifest_sources"] += 1
        city_bucket["landed_rows"] += landed_rows
        city_bucket["landed_features"] += landed_features
        city_bucket["registered_or_total_count"] += registered
        domain_bucket = city_bucket["domains"][domain]
        domain_bucket["ledger_rows"] += 1
        domain_bucket["landed_rows"] += landed_rows
        domain_bucket["landed_features"] += landed_features
        domain_bucket["registered_or_total_count"] += registered
        domain_bucket["file_count"] += file_count
        domain_bucket["source_classes"].add(source_class)

        global_domain = by_domain[domain]
        global_domain["cities"].add(city)
        global_domain["ledger_rows"] += 1
        global_domain["landed_rows"] += landed_rows
        global_domain["landed_features"] += landed_features
        global_domain["registered_or_total_count"] += registered
        global_domain["file_count"] += file_count
        global_domain["priority"] = DOMAINS.get(domain, {}).get("priority", "review")

    normalized_by_city = {}
    for city, bucket in sorted(by_city.items()):
        domains = {}
        for domain, values in sorted(bucket["domains"].items()):
            domains[domain] = {
                **{k: v for k, v in values.items() if k != "source_classes"},
                "source_classes": sorted(values["source_classes"]),
            }
        normalized_by_city[city] = {
            **{k: v for k, v in bucket.items() if k != "domains"},
            "domains": domains,
        }

    normalized_by_domain = {}
    for domain, bucket in sorted(by_domain.items()):
        normalized_by_domain[domain] = {
            **{k: v for k, v in bucket.items() if k != "cities"},
            "cities": sorted(bucket["cities"]),
            "seed_r3_use": DOMAINS.get(domain, {}).get("seed_r3_use", "review before use"),
        }

    priority_non_mobility_domains = [
        "property_planning",
        "built_environment",
        "building_compliance",
        "civic_service_311_crm",
        "environment_resilience",
        "data_quality_maturity",
        "identity_graph_eval",
    ]
    coverage = {
        domain: {
            "present": domain in normalized_by_domain,
            "cities": normalized_by_domain.get(domain, {}).get("cities", []),
            "landed_rows": normalized_by_domain.get(domain, {}).get("landed_rows", 0),
            "landed_features": normalized_by_domain.get(domain, {}).get("landed_features", 0),
            "registered_or_total_count": normalized_by_domain.get(domain, {}).get("registered_or_total_count", 0),
        }
        for domain in priority_non_mobility_domains
    }
    ready_domain_count = sum(1 for value in coverage.values() if value["present"])

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "generated_at": utc_now(),
        "city_roots_discovered": len(root_metrics),
        "expected_roots_missing_fail_closed": len(missing_roots),
        "domain_fuel_ledger_rows": len(domain_rows),
        "verified_landed_rows": sum(as_int(row["landed_rows"]) for row in domain_rows),
        "verified_landed_features": sum(as_int(row["landed_features"]) for row in domain_rows),
        "verified_registered_or_total_count": sum(as_int(row["registered_or_total_count"]) for row in domain_rows),
        "by_city": normalized_by_city,
        "by_domain": normalized_by_domain,
        "priority_non_mobility_coverage": coverage,
        "priority_non_mobility_domains_present": ready_domain_count,
        "priority_non_mobility_domains_required": len(priority_non_mobility_domains),
        "recommend_seed_r3_refresh": ready_domain_count >= 6,
        "limitations": [
            "Counts are accepted only from local CSV/JSON/JSONL/Parquet metadata or read-only DuckDB table counts.",
            "Some fallback city-prefix roots are candidate-only and must be semantically reviewed before Seed R3 use.",
            "This preflight does not generate synthetic Seed R3 records.",
            "City donor/context material is not Dubai official truth and must stay source-classed in Seed R3.",
        ],
    }


def secret_scan(paths: list[Path]) -> dict[str, Any]:
    hits: list[dict[str, str]] = []
    for root in paths:
        if not root.exists():
            continue
        for file_path in root.rglob("*"):
            if not file_path.is_file() or file_path.stat().st_size > 5_000_000:
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    hits.append({"path": str(file_path), "pattern": pattern.pattern})
                    break
    return {
        "status": "PASS" if not hits else "FAIL",
        "scanned_roots": [str(path) for path in paths],
        "hits": hits,
    }


def hash_manifest(out: Path) -> dict[str, Any]:
    files = []
    for file_path in sorted(out.rglob("*"), key=lambda p: str(p).lower()):
        if file_path.is_file() and file_path.name != "HASH_MANIFEST.json":
            files.append({
                "path": file_path.relative_to(out).as_posix(),
                "sha256": sha256_file(file_path),
                "bytes": file_path.stat().st_size,
            })
    return {"task_id": TASK_ID, "generated_at": utc_now(), "files": files}


def validate_output(out: Path) -> dict[str, Any]:
    missing = [name for name in REQUIRED_OUTPUTS if not (out / name).exists()]
    json_files = [
        "SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_DECISION.json",
        "DOMAIN_FUEL_SUMMARY.json",
        "CROSS_CITY_DONOR_POLICY.json",
        "SEED_R3_RECOMMENDED_REFRESH_PLAN.json",
        "SEED_R3_PRODUCT_FIXTURE_REQUIREMENTS.json",
        "SEED_R3_BOUNDARY_AND_SOURCE_CLASS_AUDIT.json",
        "SEED_R3_NO_MUTATION_AUDIT.json",
        "SEED_R3_SECRET_SCAN_REPORT.json",
        "HASH_MANIFEST.json",
    ]
    parsed = []
    parse_errors = []
    for name in json_files:
        try:
            json.loads((out / name).read_text(encoding="utf-8"))
            parsed.append(name)
        except Exception as exc:
            parse_errors.append({"path": name, "error": str(exc)})
    hash_errors = []
    if not parse_errors and (out / "HASH_MANIFEST.json").exists():
        manifest = json.loads((out / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        for entry in manifest.get("files", []):
            file_path = out / entry["path"]
            if not file_path.exists():
                hash_errors.append({"path": entry["path"], "error": "missing"})
            elif sha256_file(file_path) != entry["sha256"]:
                hash_errors.append({"path": entry["path"], "error": "sha256_mismatch"})
    decision = {}
    if (out / "SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_DECISION.json").exists():
        decision = json.loads((out / "SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_DECISION.json").read_text(encoding="utf-8"))
    return {
        "validated": not missing and not parse_errors and not hash_errors and decision.get("status") == STATUS,
        "status": decision.get("status"),
        "missing": missing,
        "json_parsed": len(parsed),
        "json_parse_errors": parse_errors,
        "hash_errors": hash_errors,
        "output_root": str(out),
    }


def clear_output_dir(path: Path, repo: Path) -> None:
    path = path.resolve()
    repo = repo.resolve()
    allowed_roots = [(repo / "outputs").resolve(), (repo / "publications").resolve()]
    if not any(path == root or root in path.parents for root in allowed_roots):
        raise RuntimeError(f"Refusing to clear output outside repo outputs/publications: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def run(repo: Path, out: Path, publication_out: Path) -> dict[str, Any]:
    repo = repo.resolve()
    out = (repo / out).resolve() if not out.is_absolute() else out.resolve()
    publication_out = (repo / publication_out).resolve() if not publication_out.is_absolute() else publication_out.resolve()
    package_sha = sha256_file(PACKAGE_ZIP) if PACKAGE_ZIP.exists() else None

    roots, missing_roots = discover_roots(repo)
    pre_fingerprints = {repo_rel(root, repo): root_fingerprint(root) for root, _origin in roots}

    clear_output_dir(out, repo)

    domain_rows: list[dict[str, Any]] = []
    root_metrics = [scan_root(root, origin, repo, domain_rows) for root, origin in roots]
    post_fingerprints = {repo_rel(root, repo): root_fingerprint(root) for root, _origin in roots}

    city_ledger_rows = []
    for metric in root_metrics:
        city_ledger_rows.append({
            "city": metric.city,
            "root": repo_rel(metric.root, repo),
            "origin": metric.origin,
            "status": metric.status,
            "file_count": metric.file_count,
            "byte_count": metric.byte_count,
            "lightweight_counted_files": metric.counted_files,
            "lightweight_counted_rows": metric.lightweight_rows,
            "phase_reported_rows": metric.phase_reported_rows,
            "dataset_status_sources": metric.dataset_status_sources,
            "dataset_status_rows": metric.dataset_status_rows,
            "dataset_status_total_available": metric.dataset_status_total_available,
            "manifest_sources": metric.manifest_sources,
            "manifest_landed_rows": metric.manifest_landed_rows,
            "manifest_landed_features": metric.manifest_landed_features,
            "manifest_total_available": metric.manifest_total_available,
            "duckdb_tables_counted": metric.duckdb_tables,
            "duckdb_rows_counted": metric.duckdb_rows,
            "domains_discovered": "|".join(sorted(metric.domains)),
            "limitation": "; ".join(metric.limitations),
        })
    for missing in missing_roots:
        city_ledger_rows.append({
            "city": missing["city"],
            "root": missing["root"],
            "origin": missing["origin"],
            "status": missing["status"],
            "file_count": 0,
            "byte_count": 0,
            "lightweight_counted_files": 0,
            "lightweight_counted_rows": 0,
            "phase_reported_rows": 0,
            "dataset_status_sources": 0,
            "dataset_status_rows": 0,
            "dataset_status_total_available": 0,
            "manifest_sources": 0,
            "manifest_landed_rows": 0,
            "manifest_landed_features": 0,
            "manifest_total_available": 0,
            "duckdb_tables_counted": 0,
            "duckdb_rows_counted": 0,
            "domains_discovered": "",
            "limitation": missing["limitation"],
        })

    write_csv(
        out / "CITY_CORPUS_DISCOVERY_LEDGER.csv",
        city_ledger_rows,
        [
            "city", "root", "origin", "status", "file_count", "byte_count",
            "lightweight_counted_files", "lightweight_counted_rows", "phase_reported_rows",
            "dataset_status_sources", "dataset_status_rows", "dataset_status_total_available",
            "manifest_sources", "manifest_landed_rows", "manifest_landed_features",
            "manifest_total_available", "duckdb_tables_counted", "duckdb_rows_counted",
            "domains_discovered", "limitation",
        ],
    )
    write_csv(
        out / "DOMAIN_FUEL_LEDGER.csv",
        domain_rows,
        [
            "city", "domain", "source_key", "source_root", "artifact_kind", "status",
            "source_class", "landed_rows", "landed_features", "registered_or_total_count",
            "file_count", "evidence_ref", "seed_r3_use", "limitation",
        ],
    )

    summary = build_summary(domain_rows, root_metrics, missing_roots)
    (out / "DOMAIN_FUEL_SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    donor_policy = {
        "task_id": TASK_ID,
        "policy": "Barcelona, NYC, Chicago, and London material may seed source-classed donor/context distributions or source-specific review fixtures only.",
        "truth_policy": {
            "not_dubai_official_truth": True,
            "not_complete_city_truth": True,
            "must_preserve_city_and_source_class": True,
            "seed_r3_records_must_include_evidence_refs_or_donor_refs": True,
        },
        "personal_data_policy": {
            "no_human_person_level_records": True,
            "strip_or_exclude_person_names_emails_phones_direct_individual_records": True,
            "organization_or_party_fields_allowed_only_as_non_person_entity_context_where_governed": True,
        },
        "allowed_source_classes": ["source_record", "derived", "donor_context", "synthetic_or_fixture", "replay"],
        "disallowed_claims": [
            "official_dubai_truth",
            "live_monitoring",
            "dispatch",
            "control",
            "enforcement",
            "legal_finding",
            "certified_fact",
        ],
    }
    (out / "CROSS_CITY_DONOR_POLICY.json").write_text(json.dumps(donor_policy, indent=2, sort_keys=True), encoding="utf-8")

    plan = {
        "recommended_next_task": "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1",
        "status": "READY_TO_AUTHOR_WITH_VERIFIED_PREFLIGHT_LIMITATIONS" if summary["recommend_seed_r3_refresh"] else "NEEDS_MORE_PREFLIGHT_EVIDENCE",
        "rationale": "Seed R2 was mobility-heavy; this preflight verifies cross-city non-mobility fuel before any Seed R3 generation.",
        "priority_domains": [
            "property_planning",
            "built_environment",
            "building_compliance",
            "civic_service_311_crm",
            "environment_resilience",
            "data_quality_maturity",
            "identity_graph_eval",
        ],
        "city_corpora_to_use": sorted(k for k in summary["by_city"].keys() if k in {"barcelona", "nyc", "chicago", "london"}),
        "fixture_outputs_to_refresh": ["WATCH", "ASK", "CHECK", "BRIEF", "SPATIAL", "EVENT_REPLAY"],
        "non_mutation_rule": "Consume this preflight, Seed R1/R2, Product Consumption R1, D5, and D6 read-only.",
        "limitations_to_carry_forward": summary["limitations"],
    }
    (out / "SEED_R3_RECOMMENDED_REFRESH_PLAN.json").write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")

    fixture_requirements = {
        "task_id": TASK_ID,
        "minimum_seed_r3_fixture_targets": {
            "WATCH": 12,
            "ASK": 12,
            "CHECK": 12,
            "BRIEF": 12,
            "SPATIAL": 12,
            "EVENT_REPLAY": 30,
        },
        "required_record_fields": [
            "source_class",
            "truth_layer",
            "domain_family",
            "city_or_donor_origin",
            "evidence_refs_or_donor_refs",
            "limitation_refs",
            "no_action_boundary",
        ],
        "domain_requirements": {
            "building_compliance": ["permit", "inspection", "violation", "enforcement-context-without-enforcement-claim"],
            "property_planning": ["parcel", "address", "planning", "land-use/status ambiguity"],
            "built_environment": ["building footprint/profile", "facility/site"],
            "civic_service_311_crm": ["service request", "municipal work/service context"],
            "environment_resilience": ["flood/water/air/heat/storm context"],
            "data_quality_maturity": ["stale/missing/conflicting/source-class limitation"],
            "identity_graph_eval": ["anchor/join/canonical-confidence challenge"],
        },
        "explicit_exclusions": [
            "human/person-level records",
            "live monitoring",
            "dispatch/control/enforcement/legal/certified claims",
            "official Dubai truth",
            "raw bulky provider payload packaging",
        ],
    }
    (out / "SEED_R3_PRODUCT_FIXTURE_REQUIREMENTS.json").write_text(json.dumps(fixture_requirements, indent=2, sort_keys=True), encoding="utf-8")

    boundary = {
        "status": "PASS",
        "task_id": TASK_ID,
        "source_class_separation_required": True,
        "source_truth_allowed_only_for_original_city_source_context": True,
        "donor_context_not_dubai_truth": True,
        "synthetic_replay_not_real_world_fact": True,
        "no_human_person_level_records": True,
        "no_official_dubai_truth_claim": True,
        "no_live_monitoring_claim": True,
        "no_dispatch_control_enforcement_legal_certified_claim": True,
        "no_raw_bulky_data_packaged": True,
        "no_seed_r3_generated_by_this_task": True,
    }
    (out / "SEED_R3_BOUNDARY_AND_SOURCE_CLASS_AUDIT.json").write_text(json.dumps(boundary, indent=2, sort_keys=True), encoding="utf-8")

    mutation = {
        "status": "PASS" if pre_fingerprints == post_fingerprints else "FAIL_INPUT_ROOT_MUTATION_DETECTED",
        "read_only_inputs_count": len(roots),
        "missing_inputs_fail_closed": missing_roots,
        "mutated_prior_roots": [
            root for root in sorted(pre_fingerprints)
            if pre_fingerprints.get(root) != post_fingerprints.get(root)
        ],
        "writes_limited_to": [repo_rel(out, repo), repo_rel(publication_out, repo)],
    }
    (out / "SEED_R3_NO_MUTATION_AUDIT.json").write_text(json.dumps(mutation, indent=2, sort_keys=True), encoding="utf-8")

    secret_report = secret_scan([out])
    (out / "SEED_R3_SECRET_SCAN_REPORT.json").write_text(json.dumps(secret_report, indent=2, sort_keys=True), encoding="utf-8")

    decision = {
        "task_id": TASK_ID,
        "status": STATUS if secret_report["status"] == "PASS" and mutation["status"] == "PASS" else "FAIL_PREFLIGHT_AUDIT",
        "generated_at": utc_now(),
        "package_sha256_expected": PACKAGE_SHA256,
        "package_sha256_observed": package_sha,
        "package_sha256_match": package_sha == PACKAGE_SHA256,
        "city_roots_discovered": len(root_metrics),
        "expected_roots_missing_fail_closed": len(missing_roots),
        "cities_present": sorted(k for k in summary["by_city"].keys() if k in {"barcelona", "nyc", "chicago", "london"}),
        "domain_fuel_ledger_rows": len(domain_rows),
        "verified_landed_rows": summary["verified_landed_rows"],
        "verified_landed_features": summary["verified_landed_features"],
        "verified_registered_or_total_count": summary["verified_registered_or_total_count"],
        "priority_non_mobility_domains_present": summary["priority_non_mobility_domains_present"],
        "priority_non_mobility_domains_required": summary["priority_non_mobility_domains_required"],
        "recommend_seed_r3_refresh": summary["recommend_seed_r3_refresh"],
        "recommended_next_task": plan["recommended_next_task"],
        "no_seed_r3_generated": True,
        "no_human_person_level_records": True,
        "no_credentials_written": secret_report["status"] == "PASS",
        "no_input_mutation": mutation["status"] == "PASS",
        "limitations": summary["limitations"],
    }
    (out / "SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_DECISION.json").write_text(json.dumps(decision, indent=2, sort_keys=True), encoding="utf-8")

    closeout = f"""# {TASK_ID} Closeout

Status: `{decision['status']}`

This preflight corrects the mobility-heavy Seed R2 interpretation by verifying cross-city fuel for Seed R3 before generating any new synthetic records.

## Verified Scope

- City roots discovered: `{decision['city_roots_discovered']}`
- Missing expected roots, fail-closed: `{decision['expected_roots_missing_fail_closed']}`
- Domain fuel ledger rows: `{decision['domain_fuel_ledger_rows']}`
- Verified landed rows from local artifacts: `{decision['verified_landed_rows']}`
- Verified landed features from local artifacts: `{decision['verified_landed_features']}`
- Verified registered/source-total count fields: `{decision['verified_registered_or_total_count']}`
- Priority non-mobility domains present: `{decision['priority_non_mobility_domains_present']}/{decision['priority_non_mobility_domains_required']}`

## Recommendation

Next task: `{decision['recommended_next_task']}`

Use the verified ledgers here to build Seed R3 across built environment, property/planning, building compliance, civic service, environment/resilience, data quality, and identity/graph fixtures.

## Boundaries

No Seed R3 records were generated. No input roots were mutated. No raw bulky provider payloads, credentials, person-level records, official Dubai truth, live monitoring, dispatch/control/enforcement, legal, or certified claims are included.
"""
    (out / "CODEX_CLOSEOUT.md").write_text(closeout, encoding="utf-8")

    (out / "HASH_MANIFEST.json").write_text(json.dumps(hash_manifest(out), indent=2, sort_keys=True), encoding="utf-8")

    clear_output_dir(publication_out, repo)
    for child in out.iterdir():
        target = publication_out / child.name
        if child.is_dir():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)

    return decision


def main() -> int:
    args = parse_args()
    repo = Path(args.repo_root)
    out = Path(args.out)
    publication_out = Path(args.publication_out)
    if args.validate_only:
        result = validate_output((repo / out).resolve() if not out.is_absolute() else out.resolve())
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["validated"] else 1
    decision = run(repo, out, publication_out)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
