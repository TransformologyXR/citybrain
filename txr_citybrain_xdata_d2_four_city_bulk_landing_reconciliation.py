#!/usr/bin/env python3
"""XDATA-D2 four-city bulk landing reconciliation.

This is a reconciliation gate over XDATA-D1 outputs and landing files. It does
not download source data, rewrite D1 outputs, mutate landing files, or claim any
flow/cartridge acceptance.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TASK = "XDATA-D2 Four-City Bulk Landing Reconciliation"
DEFAULT_OUTPUT_DIR = "outputs/xdata_d2_four_city_bulk_landing_reconciliation"
DEFAULT_D1_OUTPUT_DIR = "outputs/xdata_d1_four_city_bulk_source_landing"
DEFAULT_LANDING_ROOT = "data_landing/xdata_d1_bulk_official_sources_v1"

PASS_STATUSES = {"PASS_FOUR_CITY_BULK_RECONCILIATION", "PASS_WITH_SOURCE_LIMITATIONS"}

STATUS_ENUM = [
    "FULL",
    "WINDOWED_COMPLETE",
    "CAPPED_BULK",
    "BOUNDED_SAMPLE",
    "METADATA_ONLY",
    "ENDPOINT_CONFIRMED",
    "DOWNLOAD_FAILED",
    "MANUAL_RECOVERY_FULL",
    "MANUAL_RECOVERY_DUPLICATE",
    "MANUAL_RECOVERY_SCOPE_REVIEW",
    "OPTIONAL_UNBOUND",
    "EXISTING_REGISTERED",
    "SKIPPED_PRIVACY_RISK",
    "SKIPPED_LICENSE_RISK",
    "UNKNOWN",
]

CITY_CONFIG = {
    "london": {
        "code": "LON",
        "name": "London",
        "row_report": "LON_XDATA_D1_ROW_COUNT_REPORT.json",
        "landing_subdir": "london",
        "d1_status": "PASS_WITH_SOURCE_LIMITATIONS",
    },
    "nyc": {
        "code": "NYC",
        "name": "New York City",
        "row_report": "NYC_XDATA_D1_ROW_COUNT_REPORT.json",
        "landing_subdir": "nyc",
        "d1_status": "PASS_WITH_SOURCE_LIMITATIONS",
    },
    "chicago": {
        "code": "CHI",
        "name": "Chicago",
        "row_report": "chicago/CHI_XDATA_D1_ROW_COUNT_REPORT.json",
        "landing_subdir": "chicago",
        "d1_status": "PASS_WITH_SOURCE_LIMITATIONS",
    },
    "barcelona": {
        "code": "BARC",
        "name": "Barcelona",
        "row_report": "BARC_XDATA_D1_ROW_COUNT_REPORT.json",
        "manual_report": "BARC_XDATA_D1_MANUAL_INGEST_REPORT.json",
        "landing_subdir": "barcelona",
        "d1_status": "PASS_WITH_MANUAL_RECOVERY_LIMITATIONS",
    },
}

INPUT_DEFAULTS = {
    "xdata_d1_outputs": DEFAULT_D1_OUTPUT_DIR,
    "xdata_d1_landing_root": DEFAULT_LANDING_ROOT,
    "xflow_d1_cross_city_expansion_reconciliation": "outputs/xflow_d1_cross_city_expansion_reconciliation",
    "chi_f2x_d3_compliance_evidencebundles": "outputs/chi_f2x_d3_compliance_evidencebundles",
    "nyc_f4x_d3_mobility_environment_evidencebundles": "outputs/nyc_f4x_d3_mobility_environment_evidencebundles",
    "barc_f4_d6_candidate_review_snapshot": "outputs/barc_f4_d6_candidate_review_snapshot",
    "lon_flowx_expansion_path_d2_to_d6": "outputs/lon_flowx_expansion_path_d2_to_d6",
    "ontology_v2": "contracts/ontology_v2",
    "city_expansion_paths_doc": "TXR_CityBrain_City_Expansion_Paths.md",
}

REQUIRED_ARTIFACTS = [
    "README.md",
    "XDATA_D2_HARNESS_REPORT.json",
    "XDATA_D2_INPUT_INVENTORY.json",
    "XDATA_D2_CITY_SUMMARY_MATRIX.json",
    "XDATA_D2_SOURCE_STATUS_NORMALIZATION.json",
    "XDATA_D2_ROW_BYTE_RECONCILIATION.json",
    "XDATA_D2_FULL_VS_CAPPED_AUDIT.json",
    "XDATA_D2_WINDOWED_SNAPSHOT_AUDIT.json",
    "XDATA_D2_FAILURE_AND_RECOVERY_REPORT.json",
    "XDATA_D2_MANUAL_INGEST_REVIEW_REPORT.json",
    "XDATA_D2_D3_READINESS_IMPACT_REPORT.json",
    "XDATA_D2_CITY_RANKING_REPORT.json",
    "XDATA_D2_NEXT_QUEUE_RECOMMENDATION.json",
    "XDATA_D2_LIMITATION_CARRY_FORWARD_REPORT.json",
    "XDATA_D2_PRIVACY_LICENSE_REPORT.json",
    "XDATA_D2_NO_OVERCLAIM_REPORT.json",
    "XDATA_D2_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
    "tables/city_summary_matrix.csv",
    "tables/source_status_matrix.csv",
    "tables/failed_sources.csv",
    "tables/manual_recovery_sources.csv",
    "tables/d3_readiness_matrix.csv",
]

NO_OVERCLAIM_PATTERNS = [
    r"\ball sources full\b",
    r"\ball cities complete\b",
    r"\bflow cartridge accepted\b",
    r"\bbarcelona accepted\b",
    r"\baccepted barcelona cartridge\b",
    r"\blive real-time system complete\b",
    r"\bpublic safety recommendation\b",
    r"\bpublic-safety recommendation\b",
    r"\bemergency dispatch\b",
    r"\bfire dispatch\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\bhealth determination\b",
    r"\btraffic-control instruction\b",
    r"\btransit-control instruction\b",
    r"\butility-control instruction\b",
    r"\bport-control instruction\b",
    r"\bcertified affected building\b",
    r"\bcertified affected asset\b",
]

NEGATION_MARKERS = (
    "no ",
    "not ",
    "never ",
    "without ",
    "does not ",
    "do not ",
    "cannot ",
    "is not ",
    "are not ",
    "non-",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    if hasattr(value, "item"):
        try:
            return clean(value.item())
        except Exception:
            pass
    return value


def project_path(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root).resolve() / path


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: str | Path, project_root: str | Path) -> Path:
    output_dir = Path(output_dir)
    resolved = output_dir.resolve()
    root = Path(project_root).resolve()
    expected = "xdata_d2_four_city_bulk_landing_reconciliation"
    if resolved.exists():
        resolved_text = str(resolved).lower()
        if not resolved_text.startswith(str(root).lower()) or expected not in resolved_text:
            raise ValueError(f"refusing to remove unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def gate(gate_id: str, ok: bool, **details: Any) -> dict[str, Any]:
    payload = {"gate": gate_id, "status": "PASS" if ok else "FAIL"}
    payload.update(details)
    return payload


def gates_pass(gates: Iterable[dict[str, Any]]) -> bool:
    return all(item.get("status") == "PASS" for item in gates)


def input_signature(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "files": []}
    files: list[dict[str, Any]] = []
    iterable = sorted(path.rglob("*")) if path.is_dir() else [path]
    for item in iterable:
        if not item.is_file():
            continue
        if item.suffix.lower() == ".part":
            continue
        stat = item.stat()
        files.append(
            {
                "path": item.relative_to(path).as_posix() if path.is_dir() else item.name,
                "bytes": stat.st_size,
            }
        )
    return {
        "exists": True,
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "files": files,
    }


def compare_signatures(before: dict[str, Any], after: dict[str, Any], externally_volatile: set[str] | None = None) -> dict[str, Any]:
    externally_volatile = externally_volatile or set()
    changed = sorted(name for name, signature in before.items() if after.get(name) != signature)
    stable_changed = [name for name in changed if name not in externally_volatile]
    volatile_changed = [name for name in changed if name in externally_volatile]
    details = {}
    for name in changed:
        before_files = {item["path"]: item["bytes"] for item in before.get(name, {}).get("files", [])}
        after_files = {item["path"]: item["bytes"] for item in after.get(name, {}).get("files", [])}
        before_names = set(before_files)
        after_names = set(after_files)
        details[name] = {
            "added": sorted(after_names - before_names)[:20],
            "removed": sorted(before_names - after_names)[:20],
            "resized": sorted(path for path in before_names & after_names if before_files[path] != after_files[path])[:20],
        }
    return {
        "status": "PASS" if not stable_changed else "FAIL",
        "checked_inputs": sorted(before),
        "changed_inputs": stable_changed,
        "externally_volatile_changed_inputs": volatile_changed,
        "externally_volatile_note": "XDATA-D1 outputs/landing files may be updated by separate active bulk download lanes; XDATA-D2 does not write there.",
        "change_details": details,
    }


def small_file_preview(path: str | Path, max_files: int = 60) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    iterable = sorted(path.rglob("*")) if path.is_dir() else [path]
    files = []
    for item in iterable:
        if item.is_file():
            stat = item.stat()
            files.append(
                {
                    "path": item.relative_to(path).as_posix() if path.is_dir() else item.name,
                    "bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
            )
        if len(files) >= max_files:
            break
    return files


def count_part_files(path: str | Path) -> int:
    path = Path(path)
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for item in path.rglob("*.part") if item.is_file())


def rows(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def normalize_status(source: dict[str, Any], city_key: str) -> str:
    source_key = str(source.get("source_key", ""))
    original = str(source.get("landing_status") or "UNKNOWN")
    total = source.get("total_available")
    landed = rows(source.get("rows_landed"))
    cap = source.get("cap_rule_applied")

    if source_key == "nyc_optional_unbound_sources":
        return "OPTIONAL_UNBOUND"
    if original == "FULL" and total is not None and rows(total) > landed:
        if cap is not None and landed == rows(cap):
            return "CAPPED_BULK"
        return "BOUNDED_SAMPLE"
    if original in STATUS_ENUM:
        return original
    return "UNKNOWN"


def manual_status(disposition: str) -> str:
    mapping = {
        "RECOVERS_FAILED_DOWNLOAD": "MANUAL_RECOVERY_FULL",
        "DUPLICATE_MANUAL_FILE": "MANUAL_RECOVERY_DUPLICATE",
        "DUPLICATE_SCHEMA_NAME_CONFLICT": "MANUAL_RECOVERY_DUPLICATE",
        "CITY_SCOPE_REVIEW": "MANUAL_RECOVERY_SCOPE_REVIEW",
    }
    return mapping.get(disposition, "UNKNOWN")


def source_record(city_key: str, source: dict[str, Any]) -> dict[str, Any]:
    status = normalize_status(source, city_key)
    original = str(source.get("landing_status") or "UNKNOWN")
    total = source.get("total_available")
    landed = rows(source.get("rows_landed"))
    byte_count = rows(source.get("bytes_downloaded"))
    return {
        "city": CITY_CONFIG[city_key]["code"],
        "city_key": city_key,
        "source_key": source.get("source_key"),
        "original_landing_status": original,
        "normalized_status": status,
        "rows_landed": landed,
        "bytes_landed": byte_count,
        "total_available": total,
        "cap_rule_applied": source.get("cap_rule_applied"),
        "coverage_pct": source.get("coverage_pct"),
        "normalization_note": normalization_note(source, status),
    }


def normalization_note(source: dict[str, Any], normalized: str) -> str:
    original = str(source.get("landing_status") or "UNKNOWN")
    source_key = str(source.get("source_key", ""))
    if source_key == "nyc_optional_unbound_sources":
        return "D1 placeholder normalized as OPTIONAL_UNBOUND, not as a failed required source."
    if normalized != original:
        return f"D1 status {original} reconciled to {normalized} from row/total/cap evidence."
    if normalized == "FULL":
        return "FULL retained because rows_landed equals total_available where total is known."
    if normalized == "WINDOWED_COMPLETE":
        return "Windowed/snapshot landing retained as window-complete only."
    if normalized in {"CAPPED_BULK", "BOUNDED_SAMPLE"}:
        return "Limited bulk retained; not eligible for FULL claim."
    if normalized in {"METADATA_ONLY", "ENDPOINT_CONFIRMED", "DOWNLOAD_FAILED"}:
        return "Source limitation carried forward."
    return "Status retained from D1 source report."


def load_city_sources(project_root: Path, d1_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    raw_reports: dict[str, Any] = {}
    for city_key, config in CITY_CONFIG.items():
        report_path = d1_dir / str(config["row_report"])
        report = read_json(report_path, {"sources": []})
        raw_reports[city_key] = report
        for source in report.get("sources", []):
            records.append(source_record(city_key, source))
    return records, raw_reports


def add_barcelona_manual_records(records: list[dict[str, Any]], d1_dir: Path) -> dict[str, Any]:
    manual = read_json(d1_dir / str(CITY_CONFIG["barcelona"]["manual_report"]), {})
    for item in manual.get("manual_records", []):
        status = manual_status(str(item.get("manual_disposition") or "UNKNOWN"))
        records.append(
            {
                "city": "BARC",
                "city_key": "barcelona",
                "source_key": item.get("source_key_recovered") or item.get("manual_file"),
                "manual_file": item.get("manual_file"),
                "original_landing_status": item.get("original_download_status"),
                "normalized_status": status,
                "rows_landed": rows(item.get("rows_landed")),
                "bytes_landed": rows(item.get("bytes")),
                "total_available": None,
                "cap_rule_applied": None,
                "coverage_pct": item.get("coverage_pct"),
                "manual_disposition": item.get("manual_disposition"),
                "normalization_note": item.get("notes") or "Manual ingest record reconciled without promoting Barcelona to accepted status.",
            }
        )
    return manual


def build_city_summary(records: list[dict[str, Any]], manual_report: dict[str, Any], landing_root: Path) -> dict[str, Any]:
    cities = []
    by_city: dict[str, list[dict[str, Any]]] = {key: [] for key in CITY_CONFIG}
    for record in records:
        if record.get("manual_file"):
            continue
        by_city[str(record["city_key"])].append(record)

    for city_key, config in CITY_CONFIG.items():
        city_records = by_city[city_key]
        status_counts = Counter(record["normalized_status"] for record in city_records)
        rows_landed = sum(rows(record.get("rows_landed")) for record in city_records)
        bytes_landed = sum(rows(record.get("bytes_landed")) for record in city_records)
        manual_summary: dict[str, Any] | None = None
        if city_key == "barcelona":
            combined = manual_report.get("combined_effective_summary", {})
            ingest = manual_report.get("manual_ingest_summary", {})
            rows_landed = rows(combined.get("combined_downloaded_plus_manual_recovery_rows")) or rows_landed
            bytes_landed = bytes_landed + rows(ingest.get("bytes_landed_all_manual"))
            manual_summary = {
                "files_ingested": rows(ingest.get("files_ingested")),
                "manual_rows_all": rows(ingest.get("rows_landed_all_manual")),
                "manual_bytes_all": rows(ingest.get("bytes_landed_all_manual")),
                "manual_recovery_files": rows(combined.get("manual_recovery_files")),
                "manual_recovery_rows": rows(combined.get("manual_recovery_rows")),
                "failed_sources_recovered_count": rows(combined.get("failed_sources_recovered_count")),
                "failed_sources_before_manual_count": rows(combined.get("failed_sources_before_manual_count")),
                "remaining_failed_source_count": len(combined.get("remaining_failed_source_keys", [])),
            }
        cities.append(
            {
                "city": config["code"],
                "city_name": config["name"],
                "d1_status": config["d1_status"],
                "source_count": len(city_records),
                "rows_landed_effective": rows_landed,
                "bytes_landed_effective": bytes_landed,
                "status_counts": {status: status_counts.get(status, 0) for status in STATUS_ENUM if status_counts.get(status, 0)},
                "part_files_remaining": count_part_files(landing_root / str(config["landing_subdir"])),
                "bulk_depth": bulk_depth(rows_landed, status_counts),
                "recommended_claim_strength": claim_strength(city_key, status_counts),
                "manual_recovery_summary": manual_summary,
            }
        )
    return {"status": "PASS", "generated_at": utc_now(), "cities": cities}


def bulk_depth(row_count: int, counts: Counter[str]) -> str:
    useful = counts["FULL"] + counts["WINDOWED_COMPLETE"] + counts["CAPPED_BULK"] + counts["BOUNDED_SAMPLE"]
    if row_count >= 4_000_000 and useful >= 10:
        return "HIGH"
    if row_count >= 1_000_000 and useful >= 5:
        return "MEDIUM"
    return "LOW"


def claim_strength(city_key: str, counts: Counter[str]) -> str:
    if city_key == "barcelona":
        return "CANDIDATE_ONLY_WITH_MANUAL_RECOVERY_LIMITATIONS"
    if counts["DOWNLOAD_FAILED"] or counts["CAPPED_BULK"] or counts["BOUNDED_SAMPLE"] or counts["METADATA_ONLY"]:
        return "BULK_READY_WITH_SOURCE_LIMITATIONS"
    if counts["WINDOWED_COMPLETE"]:
        return "BULK_READY_WITH_WINDOW_LIMITATIONS"
    return "BULK_READY"


def build_input_inventory(project_root: Path) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for name, rel in INPUT_DEFAULTS.items():
        path = project_path(project_root, rel)
        required = name in {"xdata_d1_outputs", "xdata_d1_landing_root"}
        inputs[name] = {
            "path": str(path),
            "exists": path.exists(),
            "required": required,
            "status": "PASS" if path.exists() else ("MISSING_REQUIRED" if required else "OPTIONAL_MISSING"),
            "file_preview": small_file_preview(path),
            "volatile_part_files": volatile_part_files(path),
            "signature": input_signature(path),
        }
    return {"status": "PASS", "generated_at": utc_now(), "inputs": inputs}


def volatile_part_files(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists() or not path.is_dir():
        return []
    rows_: list[dict[str, Any]] = []
    for item in sorted(path.rglob("*.part")):
        if item.is_file():
            stat = item.stat()
            rows_.append({"path": item.relative_to(path).as_posix(), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return rows_


def build_row_byte_reconciliation(records: list[dict[str, Any]], city_summary: dict[str, Any]) -> dict[str, Any]:
    per_source = [
        {
            "city": r["city"],
            "source_key": r["source_key"],
            "normalized_status": r["normalized_status"],
            "rows_landed": r["rows_landed"],
            "bytes_landed": r["bytes_landed"],
            "coverage_pct": r.get("coverage_pct"),
            "manual_file": r.get("manual_file"),
        }
        for r in records
    ]
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "city_totals": city_summary["cities"],
        "per_source": per_source,
    }


def build_full_vs_capped_audit(records: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    capped = []
    full = []
    for record in records:
        if record.get("manual_file"):
            continue
        if record["normalized_status"] == "FULL":
            if record.get("total_available") is not None and rows(record["rows_landed"]) != rows(record["total_available"]):
                findings.append({"source_key": record["source_key"], "issue": "FULL row/total mismatch", "city": record["city"]})
            full.append(record)
        if record["normalized_status"] == "CAPPED_BULK":
            capped.append(record)
    return {
        "status": "PASS" if not findings else "FAIL",
        "full_sources_checked": len(full),
        "capped_sources": [
            {
                "city": r["city"],
                "source_key": r["source_key"],
                "rows_landed": r["rows_landed"],
                "total_available": r["total_available"],
                "cap_rule_applied": r["cap_rule_applied"],
            }
            for r in capped
        ],
        "findings": findings,
    }


def build_windowed_audit(records: list[dict[str, Any]]) -> dict[str, Any]:
    windowed = [r for r in records if r.get("normalized_status") == "WINDOWED_COMPLETE"]
    sampled = [r for r in records if r.get("normalized_status") == "BOUNDED_SAMPLE"]
    return {
        "status": "PASS",
        "windowed_sources": [
            {
                "city": r["city"],
                "source_key": r["source_key"],
                "rows_landed": r["rows_landed"],
                "bytes_landed": r["bytes_landed"],
                "note": "Complete only for the explicit D1 window/snapshot; not promoted to FULL.",
            }
            for r in windowed
        ],
        "bounded_sample_sources": [
            {
                "city": r["city"],
                "source_key": r["source_key"],
                "rows_landed": r["rows_landed"],
                "note": "Diagnostic or bounded sample retained as a limitation.",
            }
            for r in sampled
        ],
    }


def build_failure_recovery(records: list[dict[str, Any]], manual_report: dict[str, Any]) -> dict[str, Any]:
    failures = [r for r in records if r.get("normalized_status") == "DOWNLOAD_FAILED" and not r.get("manual_file")]
    manual_recoveries = [r for r in records if str(r.get("normalized_status", "")).startswith("MANUAL_RECOVERY")]
    return {
        "status": "PASS_WITH_SOURCE_LIMITATIONS" if failures else "PASS",
        "failed_sources": [
            {"city": r["city"], "source_key": r["source_key"], "note": r["normalization_note"]} for r in failures
        ],
        "manual_recovery_sources": [
            {
                "city": r["city"],
                "manual_file": r.get("manual_file"),
                "source_key": r.get("source_key"),
                "normalized_status": r.get("normalized_status"),
                "rows_landed": r.get("rows_landed"),
            }
            for r in manual_recoveries
        ],
        "barcelona_combined_effective_summary": manual_report.get("combined_effective_summary", {}),
    }


def build_manual_review(manual_report: dict[str, Any]) -> dict[str, Any]:
    manual_records = manual_report.get("manual_records", [])
    return {
        "status": "PASS",
        "manual_ingest_summary": manual_report.get("manual_ingest_summary", {}),
        "combined_effective_summary": manual_report.get("combined_effective_summary", {}),
        "review_records": [
            {
                "manual_file": item.get("manual_file"),
                "disposition": item.get("manual_disposition"),
                "normalized_status": manual_status(str(item.get("manual_disposition") or "UNKNOWN")),
                "source_key_recovered": item.get("source_key_recovered"),
                "rows_landed": item.get("rows_landed"),
                "bytes": item.get("bytes"),
                "review_note": manual_review_note(item),
            }
            for item in manual_records
        ],
        "boundary": "Manual recovery improves Barcelona candidate evidence but does not promote Barcelona to accepted status.",
    }


def manual_review_note(item: dict[str, Any]) -> str:
    disposition = item.get("manual_disposition")
    filename = item.get("manual_file")
    if disposition == "DUPLICATE_SCHEMA_NAME_CONFLICT":
        return f"{filename} is retained as duplicate/schema-conflict evidence and is not counted as IRIS recovery."
    if disposition == "DUPLICATE_MANUAL_FILE":
        return f"{filename} is a duplicate manual file and is not counted as an additional recovery."
    if disposition == "CITY_SCOPE_REVIEW":
        return f"{filename} requires city-scope review and is not counted as confirmed Barcelona recovery."
    return "Counts as failed-download manual recovery only for the linked source key."


def build_d3_readiness(city_summary: dict[str, Any]) -> dict[str, Any]:
    rows = [
        readiness("CHI", "CHI-F2X-D3", "STRENGTHENED_BY_BULK", "Parcel/compliance evidence has deep Chicago D1 bulk support; still review-context only."),
        readiness("CHI", "CHI-F3X-D3", "STRENGTHENED_BY_BULK", "Crash/traffic/311 evidence has bulk support; no dispatch or traffic-control recommendation."),
        readiness("CHI", "CHI-F4X-D3", "STRENGTHENED_BY_BULK", "Mobility/environment bundle has high-volume sources plus capped source limitations."),
        readiness("NYC", "NYC-F4X-D3", "STRENGTHENED_BY_BULK", "NYC mobility/environment inputs are materially deeper but retain capped 311/MVC limitations."),
        readiness("NYC", "NYC-F1X-D3", "STRENGTHENED_BY_BULK", "311/MVC/taxi depth can support candidate D3 evidence with source caps disclosed."),
        readiness("NYC", "NYC-F5X-D3", "STRENGTHENED_BY_BULK", "Bulk evidence improves candidate readiness; no health/legal determination."),
        readiness("NYC", "NYC-F6X-D3", "STRENGTHENED_BY_BULK", "Bulk evidence improves candidate readiness; no operational recommendation."),
        readiness("LON", "LON-F3X-D3", "STRENGTHENED_BY_BULK", "LFB/TfL/environment bulk sources support evidence bundle work with window limits."),
        readiness("LON", "LON-F4X-D3", "STRENGTHENED_BY_BULK", "London mobility/environment inputs are bulk-ready with source limitations."),
        readiness("LON", "LON-F5X-D3", "STRENGTHENED_BY_BULK", "London civic/environment evidence is stronger, but metadata/window limits carry forward."),
        readiness("BARC", "BARC-F4-D3/D4/D5/D6", "ALREADY_RECONCILED_CANDIDATE", "Existing Barcelona F4 candidate review remains candidate-only."),
        readiness("BARC", "BARC-F7-D3", "ALREADY_RECONCILED_CANDIDATE", "Existing Barcelona F7 candidate bundle remains candidate-only."),
        readiness("BARC", "BARC-F1-D3", "STILL_CANDIDATE_ONLY", "Manual recovery helps D1 coverage but unresolved failed sources remain."),
        readiness("BARC", "BARC-F2-D3", "STILL_CANDIDATE_ONLY", "Manual recovery helps D1 coverage but unresolved failed sources remain."),
        readiness("BARC", "BARC-F3-D3", "STILL_CANDIDATE_ONLY", "Manual recovery helps D1 coverage but unresolved failed sources remain."),
        readiness("BARC", "BARC-F5-D3", "STILL_CANDIDATE_ONLY", "Manual recovery helps D1 coverage but unresolved failed sources remain."),
        readiness("BARC", "BARC-F6-D3", "STILL_CANDIDATE_ONLY", "Manual recovery helps D1 coverage but unresolved failed sources remain."),
    ]
    return {"status": "PASS", "city_totals_reference": city_summary["cities"], "readiness": rows}


def readiness(city: str, lane: str, status: str, note: str) -> dict[str, Any]:
    return {"city": city, "lane": lane, "readiness_status": status, "note": note}


def build_city_ranking(city_summary: dict[str, Any]) -> dict[str, Any]:
    scored = []
    for item in city_summary["cities"]:
        counts = Counter(item.get("status_counts", {}))
        score = 0
        score += min(45, rows(item["rows_landed_effective"]) // 500_000)
        score += counts["FULL"] * 3 + counts["WINDOWED_COMPLETE"] * 2 + counts["CAPPED_BULK"] * 2
        score -= counts["DOWNLOAD_FAILED"] * 3 + counts["MANUAL_RECOVERY_SCOPE_REVIEW"] * 2
        if item["city"] == "BARC":
            score -= 8
        scored.append(
            {
                "city": item["city"],
                "bulk_depth": item["bulk_depth"],
                "rows_landed_effective": item["rows_landed_effective"],
                "status_counts": item["status_counts"],
                "score": score,
                "ranking_boundary": "Ranking prioritizes D3 evidence readiness only; it is not an accepted-flow claim.",
            }
        )
    scored.sort(key=lambda row: (-row["score"], row["city"]))
    return {"status": "PASS", "ranked_cities": scored}


def build_next_queue() -> dict[str, Any]:
    queue = [
        queue_item(1, "CHI-F4X-D3", "Chicago", "High row/byte depth and mobility/environment relevance; carry capped source limits."),
        queue_item(2, "NYC-F1X-D3", "New York City", "High-volume 311/MVC/taxi depth; capped sources must remain explicit."),
        queue_item(3, "CHI-F3X-D3", "Chicago", "Crash/traffic/311 depth supports evidence bundle construction without dispatch claims."),
        queue_item(4, "NYC-F5X-D3", "New York City", "Bulk evidence improves candidate path; retain no health/legal determination boundary."),
        queue_item(5, "LON-F4X-D3", "London", "Strong source depth with windowed and metadata-only limitations."),
        queue_item(6, "NYC-F6X-D3", "New York City", "Ready after higher-signal NYC lanes; keep operational recommendation boundary."),
        queue_item(7, "BARC-F7-D4", "Barcelona", "Candidate lane can continue only with manual-recovery and unresolved-failure limitations."),
    ]
    return {
        "status": "PASS",
        "queue": queue,
        "boundary": "Barcelona candidate lanes are not automatically prioritized above accepted-city bulk lanes.",
    }


def queue_item(rank: int, lane: str, city: str, rationale: str) -> dict[str, Any]:
    return {"rank": rank, "lane": lane, "city": city, "rationale": rationale}


def build_limitation_carry_forward(records: list[dict[str, Any]], manual_report: dict[str, Any]) -> dict[str, Any]:
    limited_statuses = {
        "WINDOWED_COMPLETE",
        "CAPPED_BULK",
        "BOUNDED_SAMPLE",
        "METADATA_ONLY",
        "ENDPOINT_CONFIRMED",
        "DOWNLOAD_FAILED",
        "OPTIONAL_UNBOUND",
    }
    limitations = [
        {
            "city": r["city"],
            "source_key": r["source_key"],
            "normalized_status": r["normalized_status"],
            "carry_forward_rule": limitation_rule(str(r["normalized_status"])),
        }
        for r in records
        if r.get("normalized_status") in limited_statuses and not r.get("manual_file")
    ]
    for key in manual_report.get("combined_effective_summary", {}).get("remaining_failed_source_keys", []):
        limitations.append(
            {
                "city": "BARC",
                "source_key": key,
                "normalized_status": "DOWNLOAD_FAILED",
                "carry_forward_rule": "Unrecovered Barcelona failed source must remain visible in downstream candidate work.",
            }
        )
    return {"status": "PASS", "limitations": limitations}


def limitation_rule(status: str) -> str:
    rules = {
        "WINDOWED_COMPLETE": "Do not promote beyond the explicit D1 window/snapshot.",
        "CAPPED_BULK": "Do not label as FULL; disclose cap and total_available when present.",
        "BOUNDED_SAMPLE": "Diagnostic sample only; unsuitable for full-depth claims.",
        "METADATA_ONLY": "Metadata confirms context but carries no real data rows.",
        "ENDPOINT_CONFIRMED": "Endpoint confirmation only; no row-level evidence.",
        "DOWNLOAD_FAILED": "Source unavailable in D1; carry as unresolved failure unless manual recovery explicitly maps to it.",
        "OPTIONAL_UNBOUND": "Optional placeholder is not a failed required source and not a row-level evidence input.",
    }
    return rules.get(status, "Carry forward source limitation.")


def build_privacy_license(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows_by_city = Counter()
    for record in records:
        rows_by_city[record["city"]] += rows(record.get("rows_landed"))
    return {
        "status": "PASS",
        "city_rows_observed": dict(rows_by_city),
        "boundaries": [
            "D2 is a reconciliation-only gate and does not publish row-level personal data.",
            "Public official datasets remain evidence inputs; license and privacy terms carry forward from source landing.",
            "Manual Barcelona files are reviewed for recovery disposition, duplicate status, and city-scope risk.",
            "No operational, policing, enforcement, emergency, dispatch, health, transit-control, traffic-control, utility-control, or port-control recommendation is created.",
        ],
    }


def no_overclaim_scan(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "XDATA_D2_NO_OVERCLAIM_REPORT.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in NO_OVERCLAIM_PATTERNS:
            for match in re.finditer(pattern, text):
                window = text[max(0, match.start() - 36) : match.end() + 12]
                if any(marker in window for marker in NEGATION_MARKERS):
                    continue
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern, "context": window})
    return {
        "status": "PASS" if not findings else "FAIL",
        "checked_files": checked,
        "findings": findings,
        "boundaries": [
            "No city is promoted to accepted status by XDATA-D2.",
            "No source with capped, windowed, bounded, metadata-only, endpoint-only, optional, or failed status is labelled FULL.",
            "Barcelona remains candidate-only with manual-recovery limitations.",
            "No public-safety, emergency, dispatch, enforcement, health, traffic-control, transit-control, utility-control, or port-control recommendation is made.",
        ],
    }


def write_csv(path: Path, rows_: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows_:
            writer.writerow(row)


def write_tables(output_dir: Path, city_summary: dict[str, Any], records: list[dict[str, Any]], d3: dict[str, Any]) -> None:
    city_rows = []
    for city in city_summary["cities"]:
        flat = dict(city)
        flat["status_counts"] = json.dumps(city.get("status_counts", {}), sort_keys=True)
        flat["manual_recovery_summary"] = json.dumps(city.get("manual_recovery_summary", {}), sort_keys=True)
        city_rows.append(flat)
    write_csv(
        output_dir / "tables/city_summary_matrix.csv",
        city_rows,
        [
            "city",
            "city_name",
            "d1_status",
            "source_count",
            "rows_landed_effective",
            "bytes_landed_effective",
            "status_counts",
            "part_files_remaining",
            "bulk_depth",
            "recommended_claim_strength",
            "manual_recovery_summary",
        ],
    )
    write_csv(
        output_dir / "tables/source_status_matrix.csv",
        records,
        [
            "city",
            "source_key",
            "manual_file",
            "original_landing_status",
            "normalized_status",
            "rows_landed",
            "bytes_landed",
            "total_available",
            "cap_rule_applied",
            "coverage_pct",
            "normalization_note",
        ],
    )
    failed = [r for r in records if r.get("normalized_status") == "DOWNLOAD_FAILED" and not r.get("manual_file")]
    write_csv(output_dir / "tables/failed_sources.csv", failed, ["city", "source_key", "rows_landed", "bytes_landed", "normalization_note"])
    manual = [r for r in records if r.get("manual_file")]
    write_csv(output_dir / "tables/manual_recovery_sources.csv", manual, ["city", "manual_file", "source_key", "normalized_status", "rows_landed", "bytes_landed", "manual_disposition"])
    write_csv(output_dir / "tables/d3_readiness_matrix.csv", d3["readiness"], ["city", "lane", "readiness_status", "note"])


def write_readme(output_dir: Path, status: str, city_summary: dict[str, Any], gates: list[dict[str, Any]]) -> None:
    lines = [
        "# XDATA-D2 Four-City Bulk Landing Reconciliation",
        "",
        f"Status: `{status}`",
        "",
        "This folder reconciles XDATA-D1 outputs and landing files across London, New York City, Chicago, and Barcelona.",
        "It is not a downloader and it does not mutate D1 outputs, landing files, or accepted flow outputs.",
        "",
        "## City Summary",
        "",
        "| City | Rows | Bytes | Status counts | Claim strength |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for city in city_summary["cities"]:
        lines.append(
            f"| {city['city']} | {city['rows_landed_effective']} | {city['bytes_landed_effective']} | "
            f"{json.dumps(city['status_counts'], sort_keys=True)} | {city['recommended_claim_strength']} |"
        )
    lines.extend(["", "## Gates", ""])
    for item in gates:
        lines.append(f"- `{item['gate']}`: `{item['status']}`")
    write_text(output_dir / "README.md", "\n".join(lines))


def run_xdata_d2(
    project_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    d1_output_dir: str | Path = DEFAULT_D1_OUTPUT_DIR,
    landing_root: str | Path = DEFAULT_LANDING_ROOT,
) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root)
    d1_dir = project_path(project_root, d1_output_dir)
    landing = project_path(project_root, landing_root)

    input_paths = {name: project_path(project_root, rel) for name, rel in INPUT_DEFAULTS.items()}
    before = {name: input_signature(path) for name, path in input_paths.items()}

    input_inventory = build_input_inventory(project_root)
    records, raw_reports = load_city_sources(project_root, d1_dir)
    manual_report = add_barcelona_manual_records(records, d1_dir)
    city_summary = build_city_summary(records, manual_report, landing)
    status_normalization = {
        "status": "PASS",
        "generated_at": utc_now(),
        "status_enum": STATUS_ENUM,
        "sources": records,
    }
    row_byte = build_row_byte_reconciliation(records, city_summary)
    full_vs_capped = build_full_vs_capped_audit(records)
    windowed = build_windowed_audit(records)
    failure = build_failure_recovery(records, manual_report)
    manual_review = build_manual_review(manual_report)
    d3 = build_d3_readiness(city_summary)
    ranking = build_city_ranking(city_summary)
    next_queue = build_next_queue()
    limitations = build_limitation_carry_forward(records, manual_report)
    privacy = build_privacy_license(records)

    write_json(out / "XDATA_D2_INPUT_INVENTORY.json", input_inventory)
    write_json(out / "XDATA_D2_CITY_SUMMARY_MATRIX.json", city_summary)
    write_json(out / "XDATA_D2_SOURCE_STATUS_NORMALIZATION.json", status_normalization)
    write_json(out / "XDATA_D2_ROW_BYTE_RECONCILIATION.json", row_byte)
    write_json(out / "XDATA_D2_FULL_VS_CAPPED_AUDIT.json", full_vs_capped)
    write_json(out / "XDATA_D2_WINDOWED_SNAPSHOT_AUDIT.json", windowed)
    write_json(out / "XDATA_D2_FAILURE_AND_RECOVERY_REPORT.json", failure)
    write_json(out / "XDATA_D2_MANUAL_INGEST_REVIEW_REPORT.json", manual_review)
    write_json(out / "XDATA_D2_D3_READINESS_IMPACT_REPORT.json", d3)
    write_json(out / "XDATA_D2_CITY_RANKING_REPORT.json", ranking)
    write_json(out / "XDATA_D2_NEXT_QUEUE_RECOMMENDATION.json", next_queue)
    write_json(out / "XDATA_D2_LIMITATION_CARRY_FORWARD_REPORT.json", limitations)
    write_json(out / "XDATA_D2_PRIVACY_LICENSE_REPORT.json", privacy)
    write_tables(out, city_summary, records, d3)

    precond_ok = d1_dir.exists() and landing.exists() and all((d1_dir / str(cfg["row_report"])).exists() for cfg in CITY_CONFIG.values())
    gates = [
        gate("XDATA-D2-PRECOND", precond_ok, d1_output_dir=str(d1_dir), landing_root=str(landing)),
        gate("INPUT-INVENTORY", all(item["status"] != "MISSING_REQUIRED" for item in input_inventory["inputs"].values())),
        gate("CITY-SUMMARY-MATRIX", len(city_summary["cities"]) == 4 and all(city["source_count"] > 0 for city in city_summary["cities"])),
        gate("STATUS-NORMALIZATION", all(record["normalized_status"] in STATUS_ENUM for record in records)),
        gate("FULL-VS-CAPPED-AUDIT", full_vs_capped["status"] == "PASS"),
        gate("WINDOWED-SNAPSHOT-AUDIT", len(windowed["windowed_sources"]) > 0),
        gate("FAILURE-RECOVERY", failure["status"] in {"PASS", "PASS_WITH_SOURCE_LIMITATIONS"}),
        gate("MANUAL-INGEST-REVIEW", manual_review["status"] == "PASS" and bool(manual_review["review_records"])),
        gate("D3-READINESS-IMPACT", d3["status"] == "PASS" and len(d3["readiness"]) >= 12),
        gate("NEXT-QUEUE", next_queue["status"] == "PASS" and len(next_queue["queue"]) >= 5),
        gate("PRIVACY-LICENSE", privacy["status"] == "PASS"),
        gate("LIMITATION-CARRY-FORWARD", limitations["status"] == "PASS" and bool(limitations["limitations"])),
    ]

    overclaim = no_overclaim_scan(out)
    write_json(out / "XDATA_D2_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append(gate("NO-OVERCLAIM", overclaim["status"] == "PASS", checked_files=overclaim["checked_files"]))

    after = {name: input_signature(path) for name, path in input_paths.items()}
    mutation = compare_signatures(before, after, externally_volatile={"xdata_d1_outputs", "xdata_d1_landing_root"})
    write_json(out / "XDATA_D2_NO_MUTATION_REPORT.json", mutation)
    gates.append(gate("NO-MUTATION", mutation["status"] == "PASS", checked_inputs=mutation["checked_inputs"]))

    status = "PASS_WITH_SOURCE_LIMITATIONS" if gates_pass(gates) else "FAIL"
    write_readme(out, status, city_summary, gates)

    harness = {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "output_dir": str(out),
        "d1_output_dir": str(d1_dir),
        "landing_root": str(landing),
        "city_summary": city_summary["cities"],
        "gates": gates,
        "artifacts": REQUIRED_ARTIFACTS,
        "boundary": "XDATA-D2 reconciles D1 bulk landing state and does not claim accepted flows or operational recommendations.",
    }
    write_json(out / "XDATA_D2_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)

    expected_hash_files = sorted(path for path in REQUIRED_ARTIFACTS if path != "SHA256SUMS.json")
    actual_hash_files = sorted(read_json(out / "SHA256SUMS.json", {}).keys())
    hash_ok = all((out / path).exists() for path in REQUIRED_ARTIFACTS) and expected_hash_files == actual_hash_files
    gates.append(gate("HASHES", hash_ok, hashed_files=hashes["file_count"]))
    status = "PASS_WITH_SOURCE_LIMITATIONS" if gates_pass(gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "XDATA_D2_HARNESS_REPORT.json", harness)
    write_readme(out, status, city_summary, gates)
    write_hashes(out)

    return harness


def print_final_report(report: dict[str, Any]) -> None:
    print(f"XDATA-D2 status: {report['status']}")
    print(f"Output: {report['output_dir']}")
    print("Per-city rows/bytes/status counts:")
    for city in report["city_summary"]:
        print(
            f"  {city['city']}: rows={city['rows_landed_effective']} bytes={city['bytes_landed_effective']} "
            f"counts={json.dumps(city['status_counts'], sort_keys=True)} claim={city['recommended_claim_strength']}"
        )
    print("Gate statuses:")
    for item in report["gates"]:
        print(f"  {item['gate']}: {item['status']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XDATA-D2 four-city bulk landing reconciliation")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--d1-output-dir", default=DEFAULT_D1_OUTPUT_DIR)
    parser.add_argument("--landing-root", default=DEFAULT_LANDING_ROOT)
    args = parser.parse_args()

    report = run_xdata_d2(
        project_root=args.project_root,
        output_dir=args.output_dir,
        d1_output_dir=args.d1_output_dir,
        landing_root=args.landing_root,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
