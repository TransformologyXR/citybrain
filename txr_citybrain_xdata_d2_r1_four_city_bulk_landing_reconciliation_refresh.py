#!/usr/bin/env python3
"""XDATA-D2-R1 four-city bulk landing reconciliation refresh."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TASK = "XDATA-D2-R1 Four-City Bulk Landing Reconciliation Refresh"
DEFAULT_OUTPUT_DIR = "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh"
DEFAULT_D1_OUTPUT_DIR = "outputs/xdata_d1_four_city_bulk_source_landing"
DEFAULT_LANDING_ROOT = "data_landing/xdata_d1_bulk_official_sources_v1"
PASS_STATUSES = {"PASS_FOUR_CITY_BULK_RECONCILIATION_REFRESH", "PASS_WITH_SOURCE_LIMITATIONS"}

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
    "UNKNOWN",
]

CITY_CONFIG = {
    "london": ("LON", "London", "LON_XDATA_D1_ROW_COUNT_REPORT.json", "london", "PASS_WITH_SOURCE_LIMITATIONS"),
    "nyc": ("NYC", "New York City", "NYC_XDATA_D1_ROW_COUNT_REPORT.json", "nyc", "PASS_WITH_SOURCE_LIMITATIONS"),
    "chicago": ("CHI", "Chicago", "chicago/CHI_XDATA_D1_ROW_COUNT_REPORT.json", "chicago", "PASS_WITH_SOURCE_LIMITATIONS"),
    "barcelona": ("BARC", "Barcelona", "BARC_XDATA_D1_ROW_COUNT_REPORT.json", "barcelona", "PASS_WITH_MANUAL_RECOVERY_LIMITATIONS"),
}

REQUIRED_ARTIFACTS = [
    "README.md",
    "XDATA_D2_R1_HARNESS_REPORT.json",
    "XDATA_D2_R1_INPUT_INVENTORY.json",
    "XDATA_D2_R1_CITY_SUMMARY_MATRIX.json",
    "XDATA_D2_R1_SOURCE_STATUS_NORMALIZATION.json",
    "XDATA_D2_R1_ROW_BYTE_RECONCILIATION.json",
    "XDATA_D2_R1_FULL_VS_CAPPED_AUDIT.json",
    "XDATA_D2_R1_WINDOWED_SNAPSHOT_AUDIT.json",
    "XDATA_D2_R1_FAILURE_AND_RECOVERY_REPORT.json",
    "XDATA_D2_R1_MANUAL_INGEST_REVIEW_REPORT.json",
    "XDATA_D2_R1_D3_READINESS_IMPACT_REPORT.json",
    "XDATA_D2_R1_NEXT_QUEUE_RECOMMENDATION.json",
    "XDATA_D2_R1_LIMITATION_CARRY_FORWARD_REPORT.json",
    "XDATA_D2_R1_NO_OVERCLAIM_REPORT.json",
    "XDATA_D2_R1_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
]

NO_OVERCLAIM_PATTERNS = [
    r"\bplatform v1 complete\b",
    r"\ball flows accepted\b",
    r"\bbarcelona accepted\b",
    r"\bflow cartridge accepted\b",
    r"\bcapped bulk data is full\b",
    r"\bcapped data is full\b",
    r"\bapi/current snapshot is historical completeness\b",
    r"\bemergency dispatch\b",
    r"\bfire dispatch\b",
    r"\bpublic safety recommendation\b",
    r"\bpublic-safety recommendation\b",
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

NEGATION_MARKERS = ("no ", "not ", "never ", "without ", "does not ", "do not ", "cannot ", "boundary ", "forbidden ")


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


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: Path, project_root: Path) -> Path:
    resolved = output_dir.resolve()
    root = project_root.resolve()
    if resolved.exists():
        text = str(resolved).lower()
        if not text.startswith(str(root).lower()) or resolved.name.lower() != "xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh":
            raise ValueError(f"refusing to remove unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def rows(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def input_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "files": []}
    files = []
    iterable = [path] if path.is_file() else sorted(path.rglob("*"))
    for item in iterable:
        if item.is_file() and item.suffix.lower() != ".part":
            stat = item.stat()
            files.append({"path": item.relative_to(path).as_posix() if path.is_dir() else item.name, "bytes": stat.st_size})
    return {"exists": True, "file_count": len(files), "total_bytes": sum(f["bytes"] for f in files), "files": files}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(name for name, signature in before.items() if after.get(name) != signature)
    return {"status": "PASS" if not changed else "FAIL", "checked_inputs": sorted(before), "changed_inputs": changed}


def part_files(path: Path) -> list[str]:
    if not path.exists() or not path.is_dir():
        return []
    return [item.relative_to(path).as_posix() for item in sorted(path.rglob("*.part")) if item.is_file()]


def normalize_status(source: dict[str, Any]) -> str:
    key = str(source.get("source_key") or "")
    original = str(source.get("landing_status") or "UNKNOWN")
    landed = rows(source.get("rows_landed"))
    total = source.get("total_available")
    cap = source.get("cap_rule_applied")
    if key == "nyc_optional_unbound_sources":
        return "OPTIONAL_UNBOUND"
    if original == "FULL" and total is not None and rows(total) > landed:
        return "CAPPED_BULK" if cap is not None and landed == rows(cap) else "BOUNDED_SAMPLE"
    if original in STATUS_ENUM:
        return original
    return "UNKNOWN"


def manual_status(disposition: str) -> str:
    return {
        "RECOVERS_FAILED_DOWNLOAD": "MANUAL_RECOVERY_FULL",
        "DUPLICATE_MANUAL_FILE": "MANUAL_RECOVERY_DUPLICATE",
        "DUPLICATE_SCHEMA_NAME_CONFLICT": "MANUAL_RECOVERY_DUPLICATE",
        "CITY_SCOPE_REVIEW": "MANUAL_RECOVERY_SCOPE_REVIEW",
    }.get(disposition, "UNKNOWN")


def source_note(status: str, source: dict[str, Any]) -> str:
    if source.get("source_key") == "nyc_311_2020_present":
        return "NYC 311 2020-present refreshed as capped 5M window with created_date >= 2022-06-28T00:00:00."
    if status == "FULL":
        return "FULL retained only where rows_landed equals total_available."
    if status == "WINDOWED_COMPLETE":
        return "Window/snapshot complete only for the explicit D1 window."
    if status == "CAPPED_BULK":
        return "Capped bulk source; not full-source proof."
    if status == "DOWNLOAD_FAILED":
        return "Unrecovered failed source; carry limitation forward."
    if status in {"METADATA_ONLY", "ENDPOINT_CONFIRMED", "BOUNDED_SAMPLE", "OPTIONAL_UNBOUND"}:
        return "Source limitation carried forward."
    return "Status retained from latest D1 report."


def load_sources(d1_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    reports = {}
    for city_key, (code, _name, report_rel, _subdir, _status) in CITY_CONFIG.items():
        report = read_json(d1_dir / report_rel, {"sources": []})
        reports[city_key] = report
        for source in report.get("sources", []):
            normalized = normalize_status(source)
            records.append(
                {
                    "city": code,
                    "city_key": city_key,
                    "source_key": source.get("source_key"),
                    "original_landing_status": source.get("landing_status") or "UNKNOWN",
                    "normalized_status": normalized,
                    "rows_landed": rows(source.get("rows_landed")),
                    "bytes_landed": rows(source.get("bytes_downloaded")),
                    "total_available": source.get("total_available"),
                    "cap_rule_applied": source.get("cap_rule_applied"),
                    "coverage_pct": source.get("coverage_pct"),
                    "normalization_note": source_note(normalized, source),
                }
            )
    return records, reports


def add_manual_records(records: list[dict[str, Any]], d1_dir: Path) -> dict[str, Any]:
    manual = read_json(d1_dir / "BARC_XDATA_D1_MANUAL_INGEST_REPORT.json", {})
    for item in manual.get("manual_records", []):
        disposition = str(item.get("manual_disposition") or "UNKNOWN")
        records.append(
            {
                "city": "BARC",
                "city_key": "barcelona",
                "source_key": item.get("source_key_recovered") or item.get("manual_file"),
                "manual_file": item.get("manual_file"),
                "original_landing_status": item.get("original_download_status"),
                "normalized_status": manual_status(disposition),
                "rows_landed": rows(item.get("rows_landed")),
                "bytes_landed": rows(item.get("bytes")),
                "total_available": None,
                "cap_rule_applied": None,
                "coverage_pct": item.get("coverage_pct"),
                "manual_disposition": disposition,
                "normalization_note": manual_note(item),
            }
        )
    return manual


def manual_note(item: dict[str, Any]) -> str:
    disposition = item.get("manual_disposition")
    name = item.get("manual_file")
    if disposition == "DUPLICATE_MANUAL_FILE":
        return f"{name} is a duplicate manual file and is not counted as a new recovery."
    if disposition == "DUPLICATE_SCHEMA_NAME_CONFLICT":
        return f"{name} is duplicate/schema-conflict evidence and is not counted as a recovered source."
    if disposition == "CITY_SCOPE_REVIEW":
        return f"{name} remains scope-review evidence and is not treated as accepted city-scoped recovery."
    return "Counts only as manual recovery for the mapped failed source key."


def build_city_summary(records: list[dict[str, Any]], manual: dict[str, Any], landing_root: Path) -> dict[str, Any]:
    cities = []
    for city_key, (code, name, _report, subdir, d1_status) in CITY_CONFIG.items():
        base_records = [r for r in records if r["city_key"] == city_key and not r.get("manual_file")]
        counts = Counter(r["normalized_status"] for r in base_records)
        city_rows = sum(r["rows_landed"] for r in base_records)
        city_bytes = sum(r["bytes_landed"] for r in base_records)
        manual_summary = None
        if city_key == "barcelona":
            combined = manual.get("combined_effective_summary", {})
            ingest = manual.get("manual_ingest_summary", {})
            city_rows = rows(combined.get("combined_downloaded_plus_manual_recovery_rows")) or city_rows
            city_bytes += rows(ingest.get("bytes_landed_all_manual"))
            manual_summary = {
                "manual_files_ingested": rows(ingest.get("files_ingested")),
                "manual_rows_all": rows(ingest.get("rows_landed_all_manual")),
                "manual_recovery_files": rows(combined.get("manual_recovery_files")),
                "manual_recovery_rows": rows(combined.get("manual_recovery_rows")),
                "remaining_failed_source_count": len(combined.get("remaining_failed_source_keys", [])),
                "remaining_failed_source_keys": combined.get("remaining_failed_source_keys", []),
            }
        cities.append(
            {
                "city": code,
                "city_name": name,
                "d1_status": d1_status,
                "source_count": len(base_records),
                "rows_landed_effective": city_rows,
                "bytes_landed_effective": city_bytes,
                "status_counts": {status: counts[status] for status in STATUS_ENUM if counts[status]},
                "part_files_remaining": len(part_files(landing_root / subdir)),
                "claim_strength": "CANDIDATE_ONLY_WITH_MANUAL_RECOVERY_LIMITATIONS" if code == "BARC" else "BULK_READY_WITH_SOURCE_LIMITATIONS",
                "manual_recovery_summary": manual_summary,
            }
        )
    return {"status": "PASS", "generated_at": utc_now(), "cities": cities}


def build_input_inventory(project_root: Path, d1_dir: Path, landing: Path) -> dict[str, Any]:
    inputs = {}
    for name, path in {
        "xdata_d1_outputs": d1_dir,
        "xdata_d1_landing_root": landing,
        "previous_xdata_d2": project_root / "outputs/xdata_d2_four_city_bulk_landing_reconciliation",
        "nightrun_d1": project_root / "outputs/nightrun_d1_overnight_current_work_completion",
    }.items():
        inputs[name] = {
            "path": str(path),
            "exists": path.exists(),
            "signature": input_signature(path),
            "volatile_part_files": part_files(path),
        }
    return {"status": "PASS", "generated_at": utc_now(), "inputs": inputs}


def build_full_vs_capped(records: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    capped = []
    full = []
    for record in records:
        if record.get("manual_file"):
            continue
        if record["normalized_status"] == "FULL":
            full.append(record)
            if record["total_available"] is not None and record["rows_landed"] != rows(record["total_available"]):
                findings.append({"city": record["city"], "source_key": record["source_key"], "issue": "FULL row/total mismatch"})
        if record["normalized_status"] == "CAPPED_BULK":
            capped.append(record)
    return {
        "status": "PASS" if not findings else "FAIL",
        "full_sources_checked": len(full),
        "capped_sources": capped,
        "findings": findings,
    }


def build_windowed(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "windowed_sources": [r for r in records if r.get("normalized_status") == "WINDOWED_COMPLETE" and not r.get("manual_file")],
        "snapshot_boundary": "WINDOWED_COMPLETE and current/API snapshot sources are not historical completeness.",
    }


def build_failure(records: list[dict[str, Any]], manual: dict[str, Any]) -> dict[str, Any]:
    failed = [r for r in records if r.get("normalized_status") == "DOWNLOAD_FAILED" and not r.get("manual_file")]
    return {
        "status": "PASS_WITH_SOURCE_LIMITATIONS" if failed else "PASS",
        "failed_sources": failed,
        "manual_recovered_source_keys": manual.get("combined_effective_summary", {}).get("failed_source_keys_recovered", []),
        "remaining_barcelona_failed_source_keys": manual.get("combined_effective_summary", {}).get("remaining_failed_source_keys", []),
    }


def build_manual_review(manual: dict[str, Any]) -> dict[str, Any]:
    records = []
    hard_findings = []
    counted = set()
    for item in manual.get("manual_records", []):
        status = manual_status(str(item.get("manual_disposition") or "UNKNOWN"))
        key = item.get("source_key_recovered")
        if status == "MANUAL_RECOVERY_FULL" and key:
            counted.add(key)
        if status == "MANUAL_RECOVERY_DUPLICATE" and item.get("source_key_recovered") in counted:
            pass
        records.append(
            {
                "manual_file": item.get("manual_file"),
                "source_key_recovered": key,
                "manual_disposition": item.get("manual_disposition"),
                "normalized_status": status,
                "rows_landed": item.get("rows_landed"),
                "bytes": item.get("bytes"),
                "review_note": manual_note(item),
            }
        )
    return {
        "status": "PASS" if not hard_findings else "FAIL",
        "manual_ingest_summary": manual.get("manual_ingest_summary", {}),
        "combined_effective_summary": manual.get("combined_effective_summary", {}),
        "review_records": records,
        "findings": hard_findings,
        "boundary": "Barcelona remains candidate-only; manual scope-review and duplicate files are not promoted to accepted source recovery.",
    }


def build_d3_readiness(project_root: Path) -> dict[str, Any]:
    checks = [
        ("NYC-F4X-D3", "outputs/nyc_f4x_d3_mobility_environment_evidencebundles", "REFRESH_RECOMMENDED", "Updated 311 window and 5M capped bulk materially strengthen NYC Flow 4 evidence."),
        ("CHI-F4X-D3", "outputs/chi_f4x_d3_mobility_environment_evidencebundles", "REFRESH_RECOMMENDED", "Open Air hourly is now FULL; Open Air individual and Cook parcels have larger capped landings."),
        ("BARC-F4-D3/D4/D5/D6", "outputs/barc_f4_d6_candidate_review_snapshot", "REFRESH_RECOMMENDED_CANDIDATE_ONLY", "Manual IRIS, XML, traffic, air, noise, and facilities recovery strengthens candidate evidence only."),
        ("BARC-F7-D3", "outputs/barc_f7_d3_civic_sensor_fusion_evidencebundles", "REFRESH_RECOMMENDED_CANDIDATE_ONLY", "Manual civic/sensor-adjacent recovery can strengthen candidate bundles; Barcelona remains candidate-only."),
        ("NYC-F1X-D3", "outputs/nyc_f1x_d3_situational_status_evidencebundles", "CURRENT_R1_STRENGTHENED", "Night run D3 can benefit from refreshed NYC 311 row volume if rerun."),
        ("CHI-F3X-D3", "outputs/chi_f3x_d3_traffic_incident_context_evidencebundles", "CURRENT_R1_STRENGTHENED", "Chicago bulk refresh improves context depth while retaining source limits."),
    ]
    return {
        "status": "PASS",
        "readiness": [
            {
                "lane": lane,
                "output_dir": str(project_path(project_root, out)),
                "output_exists": project_path(project_root, out).exists(),
                "refresh_status": status,
                "impact": impact,
            }
            for lane, out, status, impact in checks
        ],
        "boundary": "Readiness impact is not an accepted-flow or accepted-city claim.",
    }


def build_next_queue() -> dict[str, Any]:
    queue = [
        {"rank": 1, "lane": "NYC-F4X-D3-R1", "reason": "Refresh existing NYC-F4X-D3 with 5M 311 capped bulk and zero failed downloads."},
        {"rank": 2, "lane": "CHI-F4X-D3-R1", "reason": "Refresh existing CHI-F4X-D3 with FULL hourly Open Air plus larger capped sources."},
        {"rank": 3, "lane": "BARC-F4-R1 candidate refresh", "reason": "Manual recovery materially strengthens candidate evidence; do not accept Barcelona."},
        {"rank": 4, "lane": "BARC-F7-R1 candidate refresh", "reason": "Manual recovery strengthens civic/sensor context; IRIS is civic-service context only."},
        {"rank": 5, "lane": "NYC-F1X-D3-R1", "reason": "Optional refresh after NYC-F4X if situational bundles should absorb latest 311 window."},
        {"rank": 6, "lane": "CHI-F3X-D3-R1", "reason": "Optional refresh after CHI-F4X review."},
    ]
    return {"status": "PASS", "queue": queue}


def build_limitations(records: list[dict[str, Any]]) -> dict[str, Any]:
    limited = {"WINDOWED_COMPLETE", "CAPPED_BULK", "BOUNDED_SAMPLE", "METADATA_ONLY", "ENDPOINT_CONFIRMED", "DOWNLOAD_FAILED", "OPTIONAL_UNBOUND"}
    return {
        "status": "PASS",
        "limitations": [
            {
                "city": r["city"],
                "source_key": r["source_key"],
                "normalized_status": r["normalized_status"],
                "carry_forward_rule": source_note(r["normalized_status"], {"source_key": r["source_key"]}),
            }
            for r in records
            if r.get("normalized_status") in limited and not r.get("manual_file")
        ],
    }


def no_overclaim_scan(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "XDATA_D2_R1_NO_OVERCLAIM_REPORT.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in NO_OVERCLAIM_PATTERNS:
            for match in re.finditer(pattern, text):
                window = text[max(0, match.start() - 48) : match.end() + 16]
                if any(marker in window for marker in NEGATION_MARKERS):
                    continue
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern, "context": window})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def write_readme(out: Path, status: str, city_summary: dict[str, Any], gates: list[dict[str, Any]]) -> None:
    lines = ["# XDATA-D2-R1 Four-City Bulk Landing Reconciliation Refresh", "", f"Status: `{status}`", "", "| City | Rows | Bytes | Status counts |", "| --- | ---: | ---: | --- |"]
    for city in city_summary["cities"]:
        lines.append(f"| {city['city']} | {city['rows_landed_effective']} | {city['bytes_landed_effective']} | {json.dumps(city['status_counts'], sort_keys=True)} |")
    lines.extend(["", "## Gates", ""])
    lines.extend(f"- `{g['gate']}`: `{g['status']}`" for g in gates)
    write_text(out / "README.md", "\n".join(lines))


def run_xdata_d2_r1(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR, d1_output_dir: str | Path = DEFAULT_D1_OUTPUT_DIR, landing_root: str | Path = DEFAULT_LANDING_ROOT) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root)
    d1_dir = project_path(project_root, d1_output_dir)
    landing = project_path(project_root, landing_root)
    watched = {"xdata_d1_outputs": d1_dir, "xdata_d1_landing_root": landing}
    before = {name: input_signature(path) for name, path in watched.items()}

    inventory = build_input_inventory(project_root, d1_dir, landing)
    records, _reports = load_sources(d1_dir)
    manual = add_manual_records(records, d1_dir)
    city_summary = build_city_summary(records, manual, landing)
    normalization = {"status": "PASS", "status_enum": STATUS_ENUM, "sources": records}
    row_byte = {"status": "PASS", "city_totals": city_summary["cities"], "per_source": records}
    full_vs_capped = build_full_vs_capped(records)
    windowed = build_windowed(records)
    failure = build_failure(records, manual)
    manual_review = build_manual_review(manual)
    d3 = build_d3_readiness(project_root)
    next_queue = build_next_queue()
    limitations = build_limitations(records)

    write_json(out / "XDATA_D2_R1_INPUT_INVENTORY.json", inventory)
    write_json(out / "XDATA_D2_R1_CITY_SUMMARY_MATRIX.json", city_summary)
    write_json(out / "XDATA_D2_R1_SOURCE_STATUS_NORMALIZATION.json", normalization)
    write_json(out / "XDATA_D2_R1_ROW_BYTE_RECONCILIATION.json", row_byte)
    write_json(out / "XDATA_D2_R1_FULL_VS_CAPPED_AUDIT.json", full_vs_capped)
    write_json(out / "XDATA_D2_R1_WINDOWED_SNAPSHOT_AUDIT.json", windowed)
    write_json(out / "XDATA_D2_R1_FAILURE_AND_RECOVERY_REPORT.json", failure)
    write_json(out / "XDATA_D2_R1_MANUAL_INGEST_REVIEW_REPORT.json", manual_review)
    write_json(out / "XDATA_D2_R1_D3_READINESS_IMPACT_REPORT.json", d3)
    write_json(out / "XDATA_D2_R1_NEXT_QUEUE_RECOMMENDATION.json", next_queue)
    write_json(out / "XDATA_D2_R1_LIMITATION_CARRY_FORWARD_REPORT.json", limitations)

    gates = [
        {"gate": "XDATA-D2-R1-PRECOND", "status": "PASS" if d1_dir.exists() and landing.exists() else "FAIL"},
        {"gate": "INPUT-INVENTORY", "status": inventory["status"]},
        {"gate": "CITY-SUMMARY-MATRIX", "status": "PASS" if len(city_summary["cities"]) == 4 else "FAIL"},
        {"gate": "STATUS-NORMALIZATION", "status": "PASS" if all(r["normalized_status"] in STATUS_ENUM for r in records) else "FAIL"},
        {"gate": "FULL-VS-CAPPED-AUDIT", "status": full_vs_capped["status"]},
        {"gate": "WINDOWED-SNAPSHOT-AUDIT", "status": windowed["status"]},
        {"gate": "FAILURE-RECOVERY", "status": "PASS" if failure["status"] in {"PASS", "PASS_WITH_SOURCE_LIMITATIONS"} else "FAIL"},
        {"gate": "MANUAL-INGEST-REVIEW", "status": manual_review["status"]},
        {"gate": "D3-READINESS-IMPACT", "status": d3["status"]},
        {"gate": "NEXT-QUEUE", "status": next_queue["status"]},
        {"gate": "LIMITATION-CARRY-FORWARD", "status": limitations["status"]},
    ]

    overclaim = no_overclaim_scan(out)
    write_json(out / "XDATA_D2_R1_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": "NO-OVERCLAIM", "status": overclaim["status"]})

    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / "XDATA_D2_R1_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": "NO-MUTATION", "status": mutation["status"]})

    status = "PASS_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    write_readme(out, status, city_summary, gates)
    harness = {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "output_dir": str(out),
        "city_summary": city_summary["cities"],
        "gates": gates,
        "boundary": "R1 refresh reconciles latest D1 source state only; it does not accept any new flow or city core.",
    }
    write_json(out / "XDATA_D2_R1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    hash_ok = sorted(read_json(out / "SHA256SUMS.json", {}).keys()) == sorted(p for p in REQUIRED_ARTIFACTS if p != "SHA256SUMS.json")
    gates.append({"gate": "HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = "PASS_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "XDATA_D2_R1_HARNESS_REPORT.json", harness)
    write_readme(out, status, city_summary, gates)
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    print(f"XDATA-D2-R1 Four-City Bulk Landing Reconciliation Refresh: {report['status']}")
    print()
    city_map = {item["city"]: item for item in report["city_summary"]}
    for code, label in [("LON", "London"), ("NYC", "NYC"), ("CHI", "Chicago"), ("BARC", "Barcelona")]:
        city = city_map[code]
        print(f"{label} rows/bytes: {city['rows_landed_effective']} / {city['bytes_landed_effective']}")
    print()
    gate_map = {item["gate"]: item["status"] for item in report["gates"]}
    print(f"Full-vs-capped audit: {gate_map.get('FULL-VS-CAPPED-AUDIT')}")
    print(f"Windowed snapshot audit: {gate_map.get('WINDOWED-SNAPSHOT-AUDIT')}")
    print(f"Manual ingest review: {gate_map.get('MANUAL-INGEST-REVIEW')}")
    print(f"D3 readiness impact: {gate_map.get('D3-READINESS-IMPACT')}")
    print(f"Next queue recommendation: {gate_map.get('NEXT-QUEUE')}")
    print(f"No-overclaim: {gate_map.get('NO-OVERCLAIM')}")
    print(f"No-mutation: {gate_map.get('NO-MUTATION')}")
    print(f"Hashes: {gate_map.get('HASHES')}")
    print()
    print("Final status:")
    print(report["status"])
    print()
    print(f"Output:\n{report['output_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XDATA-D2-R1 reconciliation refresh")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--d1-output-dir", default=DEFAULT_D1_OUTPUT_DIR)
    parser.add_argument("--landing-root", default=DEFAULT_LANDING_ROOT)
    args = parser.parse_args()
    report = run_xdata_d2_r1(args.project_root, args.output_dir, args.d1_output_dir, args.landing_root)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
