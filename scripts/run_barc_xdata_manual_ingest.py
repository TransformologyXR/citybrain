from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from txr_citybrain_xdata_d1_four_city_bulk_landing import (  # noqa: E402
    DEFAULT_LANDING_ROOT,
    DEFAULT_OUTPUT_DIR,
    FULL,
    METADATA_ONLY,
    read_json,
    safe_name,
    sha256_file,
    utc_now,
    write_json,
    write_text,
    inspect_rows,
)


MANUAL_MAP: dict[str, dict[str, Any]] = {
    "airstations.csv": {
        "family": "air_quality",
        "source_key_recovered": "barc_air_quality_qualitat-aire-estacions-bcn_1",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual air-quality station CSV; recovers the timed-out Open Data BCN station download.",
    },
    "2026_01_Gener_qualitat_aire_BCN.csv": {
        "family": "air_quality",
        "source_key_recovered": "barc_air_quality_qualitat-aire-detall-bcn_2",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual January 2026 air-quality detail CSV.",
    },
    "2026_02_Febrer_qualitat_aire_BCN.csv": {
        "family": "air_quality",
        "source_key_recovered": "barc_air_quality_qualitat-aire-detall-bcn_3",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual February 2026 air-quality detail CSV.",
    },
    "2025_IRIS_Peticions_Ciutadanes_OpenData.csv": {
        "family": "iris",
        "source_key_recovered": "barc_iris_iris_1",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual 2025 IRIS citizen-petition CSV; civic-service context only.",
    },
    "2026_IRIS_Peticions_Ciutadanes_OpenData.csv": {
        "family": "iris",
        "source_key_recovered": "barc_iris_iris_2",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual 2026 IRIS citizen-petition CSV; civic-service context only.",
    },
    "2025_IRIS_Peticions_Ciutadanes_OpenData (1).xml": {
        "family": "iris",
        "source_key_recovered": "barc_iris_iris_3",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual 2025 IRIS citizen-petition XML; civic-service context only.",
    },
    "download (1).csv": {
        "family": "traffic_state",
        "source_key_recovered": "barc_traffic_state_transit-relacio-trams_1",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual traffic road-section CSV.",
    },
    "download (2).csv": {
        "family": "traffic_state",
        "source_key_recovered": "barc_traffic_state_transit-relacio-trams_1",
        "manual_disposition": "DUPLICATE_MANUAL_FILE",
        "notes": "Duplicate of the traffic road-section CSV; ingested by hash but not counted as another recovered source.",
    },
    "download (3).csv": {
        "family": "traffic_state",
        "source_key_recovered": "barc_traffic_state_transit-relacio-trams_2",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual traffic road-section long-format CSV.",
    },
    "2026_01_Gener_ITINERARIS_ITINERARIS (1).csv": {
        "family": "traffic_state",
        "source_key_recovered": "barc_traffic_state_itineraris_3",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual January 2026 traffic-itineraries CSV.",
    },
    "XarxaSoroll_EquipsMonitor_Instal (1).csv": {
        "family": "noise",
        "source_key_recovered": "barc_noise_xarxasoroll-equipsmonitor-instal_3",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual noise-monitor equipment installation CSV.",
    },
    "transprt facilities.json": {
        "family": "facilities",
        "source_key_recovered": "barc_facilities_equipament-transports-i-serveis-relacionats_1",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual transport/services facilities JSON.",
    },
    "Utilityservice companies facilities.json": {
        "family": "facilities",
        "source_key_recovered": "barc_facilities_equipament-companyies-de-serveis_2",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual utility/service-company facilities JSON.",
    },
    "Media services facilities JSON.json": {
        "family": "facilities",
        "source_key_recovered": "barc_facilities_equipament-mitjans-de-comunicacio-i-serveis-relacionats_3",
        "manual_disposition": "RECOVERS_FAILED_DOWNLOAD",
        "notes": "Manual media/services facilities JSON.",
    },
    "IRIS 2025.json": {
        "family": "facilities",
        "source_key_recovered": None,
        "manual_disposition": "DUPLICATE_SCHEMA_NAME_CONFLICT",
        "notes": "Filename says IRIS, but schema/hash match the media/services facilities JSON. Ingested and flagged; not counted as IRIS recovery.",
    },
    "BikePoint.json": {
        "family": "scope_review",
        "source_key_recovered": None,
        "manual_disposition": "CITY_SCOPE_REVIEW",
        "notes": "Manual file name/schema suggests a BikePoint feed; ingested but not counted as Barcelona source recovery until provenance is confirmed.",
    },
}


def read_manifest_records(output_dir: Path) -> list[dict[str, Any]]:
    payload = read_json(output_dir / "BARC_XDATA_D1_DOWNLOAD_MANIFEST.json", {})
    if isinstance(payload, dict):
        return payload.get("sources") or payload.get("downloads") or []
    return []


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row.get("landing_status") or "UNKNOWN") for row in records)
    return {
        "sources": len(records),
        "rows_landed": sum(int(row.get("rows_landed") or 0) for row in records),
        "bytes_landed": sum(int(row.get("bytes_downloaded") or row.get("bytes") or 0) for row in records),
        "status_counts": dict(sorted(counts.items())),
    }


def build_manual_record(
    source_path: Path,
    landing_file: Path,
    manifest_records: dict[str, dict[str, Any]],
    seen_hashes: dict[str, str],
) -> dict[str, Any]:
    metadata = MANUAL_MAP.get(source_path.name, {})
    digest = sha256_file(source_path)
    rows, columns = inspect_rows(source_path)
    recovered_key = metadata.get("source_key_recovered")
    source_manifest = manifest_records.get(recovered_key or "", {})
    duplicate_of = seen_hashes.get(digest)
    manual_disposition = metadata.get("manual_disposition", "UNMAPPED_MANUAL_FILE")
    seen_hashes.setdefault(digest, source_path.name)
    return {
        "manual_file": source_path.name,
        "manual_source_path": str(source_path),
        "landing_path": str(landing_file),
        "sha256": digest,
        "bytes": source_path.stat().st_size,
        "row_count": rows,
        "columns": columns[:100],
        "column_count": len(columns),
        "landing_status": FULL if rows is not None else "METADATA_ONLY",
        "total_available": rows,
        "rows_landed": rows or 0,
        "coverage_pct": 100.0 if rows is not None else None,
        "family": metadata.get("family", "manual_unmapped"),
        "source_key_recovered": recovered_key,
        "original_download_status": source_manifest.get("landing_status"),
        "original_download_error": source_manifest.get("error"),
        "original_url": source_manifest.get("url"),
        "manual_disposition": manual_disposition,
        "duplicate_of": duplicate_of,
        "notes": metadata.get("notes", "Manual file ingested; provenance needs review."),
        "boundary": "manual official/public-source recovery only; no operational, dispatch, enforcement, health, or certified affected-asset claim",
    }


def render_markdown(report: dict[str, Any]) -> str:
    manual = report["manual_ingest_summary"]
    downloaded = report["downloaded_summary"]
    effective = report["combined_effective_summary"]
    lines = [
        "# BARC XDATA-D1 Combined Download + Manual Ingest Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Codex-downloaded sources: {downloaded['sources']} sources, {downloaded['rows_landed']:,} rows, {downloaded['bytes_landed']:,} bytes.",
        f"- Manual files ingested: {manual['files_ingested']} files, {manual['rows_landed_all_manual']:,} rows, {manual['bytes_landed_all_manual']:,} bytes.",
        f"- Manual effective recovery: {effective['manual_recovery_files']} files, {effective['manual_recovery_rows']:,} rows.",
        f"- Unique failed source keys recovered by manual files: {effective['failed_sources_recovered_count']}.",
        f"- Remaining unresolved failed source keys: {len(effective['remaining_failed_source_keys'])}.",
        "",
        "## Manual Files",
        "",
        "| File | Disposition | Recovered source | Rows | Bytes | Notes |",
        "|---|---:|---|---:|---:|---|",
    ]
    for row in report["manual_records"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["manual_file"],
                    row["manual_disposition"],
                    row.get("source_key_recovered") or "",
                    f"{row.get('rows_landed') or 0:,}",
                    f"{row.get('bytes') or 0:,}",
                    str(row.get("notes") or "").replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Remaining Failed Sources",
            "",
        ]
    )
    for key in effective["remaining_failed_source_keys"]:
        lines.append(f"- `{key}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Manual files are registered by hash and copied into the Barcelona XDATA landing root.",
            "- Duplicate and city-scope-review files are preserved but not counted as recovered Barcelona failed sources.",
            "- No flow cartridge acceptance is implied.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(
    project_root: str | Path = ".",
    manual_dir: str | Path = "bcn manual",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    landing_root: str | Path = DEFAULT_LANDING_ROOT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    manual_root = (root / manual_dir).resolve() if not Path(manual_dir).is_absolute() else Path(manual_dir).resolve()
    out = (root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    landing = (root / landing_root).resolve() if not Path(landing_root).is_absolute() else Path(landing_root).resolve()
    city_landing = landing / "barcelona"
    manual_raw = city_landing / "manual" / "raw"
    manual_manifests = city_landing / "manual" / "manifests"
    manual_raw.mkdir(parents=True, exist_ok=True)
    manual_manifests.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    if not manual_root.exists():
        raise FileNotFoundError(f"Manual directory not found: {manual_root}")

    manifest_records_list = read_manifest_records(out)
    manifest_records = {str(row.get("source_key")): row for row in manifest_records_list if row.get("source_key")}
    failed_before = {key for key, row in manifest_records.items() if row.get("landing_status") == "DOWNLOAD_FAILED"}

    manual_records: list[dict[str, Any]] = []
    seen_hashes: dict[str, str] = {}
    for source_path in sorted(path for path in manual_root.iterdir() if path.is_file()):
        landing_file = manual_raw / safe_name(source_path.name)
        shutil.copy2(source_path, landing_file)
        record = build_manual_record(source_path, landing_file, manifest_records, seen_hashes)
        manual_records.append(record)
        write_json(manual_manifests / f"{safe_name(source_path.stem)}.json", record)

    def is_effective_recovery(row: dict[str, Any]) -> bool:
        return (
            row.get("manual_disposition") == "RECOVERS_FAILED_DOWNLOAD"
            and bool(row.get("source_key_recovered"))
            and row.get("landing_status") != METADATA_ONLY
            and int(row.get("rows_landed") or 0) > 0
        )

    recovered = {str(row["source_key_recovered"]) for row in manual_records if is_effective_recovery(row)}
    remaining_failed = sorted(failed_before - recovered)
    recovery_rows = sum(int(row.get("rows_landed") or 0) for row in manual_records if is_effective_recovery(row))
    recovery_files = sum(1 for row in manual_records if is_effective_recovery(row))
    manual_counts = Counter(str(row.get("manual_disposition")) for row in manual_records)
    report = {
        "task": "BARC XDATA-D1 Manual Ingest + Combined Report",
        "generated_at": utc_now(),
        "status": "PASS_WITH_MANUAL_RECOVERY_LIMITATIONS",
        "manual_dir": str(manual_root),
        "manual_landing_root": str(manual_raw),
        "downloaded_summary": summarize_records(manifest_records_list),
        "manual_ingest_summary": {
            "files_ingested": len(manual_records),
            "rows_landed_all_manual": sum(int(row.get("rows_landed") or 0) for row in manual_records),
            "bytes_landed_all_manual": sum(int(row.get("bytes") or 0) for row in manual_records),
            "disposition_counts": dict(sorted(manual_counts.items())),
        },
        "combined_effective_summary": {
            "downloaded_rows": summarize_records(manifest_records_list)["rows_landed"],
            "manual_recovery_rows": recovery_rows,
            "combined_downloaded_plus_manual_recovery_rows": summarize_records(manifest_records_list)["rows_landed"] + recovery_rows,
            "manual_recovery_files": recovery_files,
            "failed_sources_before_manual_count": len(failed_before),
            "failed_sources_recovered_count": len(recovered),
            "failed_source_keys_recovered": sorted(recovered),
            "remaining_failed_source_keys": remaining_failed,
        },
        "manual_records": manual_records,
    }
    write_json(out / "BARC_XDATA_D1_MANUAL_INGEST_REPORT.json", report)
    write_json(out / "BARC_XDATA_D1_COMBINED_DOWNLOAD_MANUAL_REPORT.json", report)
    write_text(out / "BARC_XDATA_D1_COMBINED_DOWNLOAD_MANUAL_REPORT.md", render_markdown(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest manually supplied Barcelona XDATA files and write combined report.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--manual-dir", default="bcn manual")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--landing-root", default=DEFAULT_LANDING_ROOT)
    args = parser.parse_args()
    report = run(args.project_root, args.manual_dir, args.output_dir, args.landing_root)
    effective = report["combined_effective_summary"]
    print("BARC XDATA-D1 manual ingest: " + report["status"])
    print(f"Manual files ingested: {report['manual_ingest_summary']['files_ingested']}")
    print(f"Manual recovery rows: {effective['manual_recovery_rows']:,}")
    print(f"Recovered failed sources: {effective['failed_sources_recovered_count']}")
    print(f"Remaining failed sources: {len(effective['remaining_failed_source_keys'])}")
    print("Output:")
    print(Path(args.output_dir).resolve() if Path(args.output_dir).is_absolute() else (Path(args.project_root).resolve() / args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
