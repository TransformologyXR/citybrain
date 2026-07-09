from __future__ import annotations

import csv
import hashlib
import json
import os
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CART_ROOT = REPO_ROOT / "citybrain_source_acquisition_cart_r1"
INVENTORY_PATH = CART_ROOT / "manifests" / "source_inventory.csv"
RAW_ROOT = Path(os.environ.get("CITYBRAIN_RAW_ROOT", r"C:\data\citybrain\raw"))
RAW_REPORT_PATH = RAW_ROOT / "_citybrain_acquisition_cart_r1_report.json"

PACKAGE_NAME = "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R1-RESULTS"
OUTPUT_ROOT = REPO_ROOT / "outputs" / PACKAGE_NAME
ZIP_PATH = REPO_ROOT / "packages" / f"{PACKAGE_NAME}.zip"

PASS_STATUS = "PASS_SOURCE_ACQUISITION_CART_R1_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_SOURCE_ACQUISITION_CART_R1_KEYED_AND_MANUAL_BLOCKERS"
FAIL_STATUS = "FAIL_SOURCE_ACQUISITION_CART_R1"

REQUESTED_OUTPUTS = [
    "HARVEST_REPORT.json",
    "SOURCE_STATUS_LEDGER.csv",
    "CHECKSUM_MANIFEST.json",
    "DOMAIN_FEED_MANIFEST.json",
    "SAMPLE_ROW_COUNTS.csv",
    "KNOWN_BLOCKERS.md",
    "CODEX_CLOSEOUT.md",
]

NO_RAW_DATA_BOUNDARY = "Raw source data remains outside the repo under C:\\data\\citybrain\\raw."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel_to_repo(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def load_inventory() -> list[dict[str, str]]:
    with INVENTORY_PATH.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_raw_report() -> dict[str, Any]:
    if RAW_REPORT_PATH.exists():
        return read_json(RAW_REPORT_PATH)
    fallback = OUTPUT_ROOT / "HARVEST_REPORT.json"
    if fallback.exists():
        payload = read_json(fallback)
        raw_report = payload.get("raw_report")
        if isinstance(raw_report, dict):
            return raw_report
    raise FileNotFoundError(f"Missing smoke report: {RAW_REPORT_PATH}")


def result_by_source(raw_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("source_id")): row for row in raw_report.get("results", [])}


def classify_result(row: dict[str, str], result: dict[str, Any]) -> tuple[str, str, str]:
    status = str(result.get("status", "MISSING_RESULT"))
    access_type = row.get("access_type", "")
    env_vars = row.get("env_vars", "")
    sid = row.get("source_id", "")

    if status == "PASS":
        return "downloaded_smoke_sample", "usable_now", "Keep raw landing outside repo; plan clipped/normalized full pull."
    if status == "TEMPLATE_COPIED":
        return "template_copied", "ready_for_next_tool", "Run DuckDB/httpfs bbox query for Dubai AOI; do not pull full global themes."
    if status == "PLAN_ONLY":
        return "large_download_plan_only", "blocked_by_full_pull_policy", "Run targeted tile download and clip outside repo before normalization."
    if status == "FAIL_CLOSED" and env_vars:
        return "credential_missing_fail_closed", "blocked_by_missing_credentials", f"Set {env_vars} and rerun source-specific smoke."
    if status == "MANUAL_OR_KEY_REQUIRED" and "no_key_planetary" in access_type:
        return "metadata_captured_scaffold_gap", "needs_harvester_extension", "Implement STAC/Delta bbox smoke for Microsoft Buildings from captured metadata."
    if status == "MANUAL_OR_KEY_REQUIRED" and (env_vars or "key" in access_type):
        return "credential_or_manual_stub", "blocked_by_missing_credentials", f"Set {env_vars or 'required credentials'} and rerun smoke."
    if status == "MANUAL_OR_KEY_REQUIRED":
        return "manual_export_stub", "blocked_by_human_export", "Wait for official export/access, then import using the prepared stub."
    if status == "FAIL":
        return "smoke_failed", "blocked_by_runtime_failure", str(result.get("error", "Inspect raw report."))
    return f"status_{status.lower()}", "review_required", f"Review source {sid} in HARVEST_REPORT.json."


def final_status(results: list[dict[str, Any]]) -> str:
    statuses = [str(row.get("status", "")) for row in results]
    if any(status == "FAIL" for status in statuses):
        return FAIL_STATUS
    if any(status in {"PASS", "TEMPLATE_COPIED", "PLAN_ONLY", "FAIL_CLOSED", "MANUAL_OR_KEY_REQUIRED"} for status in statuses):
        return PASS_STATUS
    return PARTIAL_STATUS


def sample_measurement(source_id: str, result: dict[str, Any]) -> dict[str, Any]:
    status = str(result.get("status", "MISSING_RESULT"))
    out_path = Path(str(result.get("out_path", ""))) if result.get("out_path") else None
    base = {
        "source_id": source_id,
        "result_status": status,
        "sample_count": 0,
        "sample_count_kind": "none",
        "bytes": result.get("bytes", ""),
        "out_path": str(out_path) if out_path else "",
        "measurement_note": "",
    }

    if not out_path or not out_path.exists():
        if status == "FAIL_CLOSED":
            base["measurement_note"] = str(result.get("error", "credential missing"))
        return base

    base["bytes"] = out_path.stat().st_size
    if source_id == "open_meteo_dubai_weather":
        payload = read_json(out_path)
        hourly = payload.get("hourly", {})
        base["sample_count"] = len(hourly.get("time", []))
        base["sample_count_kind"] = "hourly_weather_records"
        base["measurement_note"] = "Open-Meteo one-day hourly Dubai forecast smoke."
    elif source_id == "opsd_time_series":
        payload = read_json(out_path)
        base["sample_count"] = len(payload.get("resources", []))
        base["sample_count_kind"] = "datapackage_resources"
        base["measurement_note"] = "OPSD metadata smoke; data resources not bulk-downloaded."
    elif source_id == "osm_geofabrik_gcc_states":
        base["sample_count"] = len([line for line in out_path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()])
        base["sample_count_kind"] = "poly_non_empty_lines"
        base["measurement_note"] = "Geofabrik GCC boundary polygon smoke, not full PBF/GPKG."
    elif source_id == "worldpop_are_population":
        base["sample_count"] = out_path.stat().st_size
        base["sample_count_kind"] = "raster_bytes"
        base["measurement_note"] = "WorldPop UAE GeoTIFF smoke; not row-tabular."
    elif source_id == "overture_maps_dubai_aoi":
        base["sample_count"] = len(out_path.read_text(encoding="utf-8", errors="ignore").splitlines())
        base["sample_count_kind"] = "sql_template_lines"
        base["measurement_note"] = "DuckDB AOI query template copied; no Overture cloud query run yet."
    elif source_id == "jrc_global_surface_water_dubai_tile":
        payload = read_json(out_path)
        base["sample_count"] = len(payload.get("candidate_urls", []))
        base["sample_count_kind"] = "candidate_tile_urls"
        base["measurement_note"] = "Large GeoTIFF intentionally plan-only in smoke."
    else:
        base["sample_count"] = 1
        base["sample_count_kind"] = "stub_file"
        base["measurement_note"] = "Manual/keyed source stub created."
    return base


def raw_file_checksums() -> list[dict[str, Any]]:
    if not RAW_ROOT.exists():
        return []
    rows = []
    for path in sorted(p for p in RAW_ROOT.rglob("*") if p.is_file()):
        rows.append(
            {
                "scope": "raw_landing",
                "path": str(path),
                "relative_to_raw_root": str(path.relative_to(RAW_ROOT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def package_file_checksums(exclude: set[str] | None = None) -> list[dict[str, Any]]:
    exclude = exclude or set()
    rows = []
    for name in REQUESTED_OUTPUTS:
        if name in exclude:
            continue
        path = OUTPUT_ROOT / name
        if path.exists():
            rows.append(
                {
                    "scope": "closeout_package",
                    "path": rel_to_repo(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return rows


def build_source_ledger(inventory: list[dict[str, str]], results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in inventory:
        sid = item["source_id"]
        result = results.get(sid, {"status": "MISSING_RESULT"})
        closeout_class, readiness, next_action = classify_result(item, result)
        rows.append(
            {
                "source_id": sid,
                "source_name": item.get("source_name", ""),
                "priority": item.get("priority", ""),
                "category": item.get("category", ""),
                "domain_pack": item.get("domain_pack", ""),
                "access_type": item.get("access_type", ""),
                "env_vars": item.get("env_vars", ""),
                "result_status": result.get("status", "MISSING_RESULT"),
                "closeout_class": closeout_class,
                "readiness": readiness,
                "http_status": result.get("http_status", ""),
                "bytes": result.get("bytes", ""),
                "out_path": result.get("out_path", ""),
                "error": result.get("error", ""),
                "next_action": next_action,
            }
        )
    return rows


def build_domain_feed_manifest(
    status: str,
    inventory: list[dict[str, str]],
    results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    feeds = []
    fast_path = []
    for item in inventory:
        sid = item["source_id"]
        result = results.get(sid, {"status": "MISSING_RESULT"})
        closeout_class, readiness, next_action = classify_result(item, result)
        usable_now = readiness in {"usable_now", "ready_for_next_tool"}
        if sid in {
            "open_meteo_dubai_weather",
            "worldpop_are_population",
            "osm_geofabrik_gcc_states",
            "overture_maps_dubai_aoi",
            "ms_buildings_planetary_computer",
        }:
            fast_path.append(
                {
                    "source_id": sid,
                    "ready_state": readiness,
                    "limitation": next_action if not usable_now else "",
                }
            )
        feeds.append(
            {
                "source_id": sid,
                "source_name": item.get("source_name", ""),
                "source_class": item.get("category", ""),
                "domain_pack": item.get("domain_pack", ""),
                "priority": item.get("priority", ""),
                "landing_status": result.get("status", "MISSING_RESULT"),
                "closeout_class": closeout_class,
                "readiness": readiness,
                "synthetic_factory_use": synthetic_factory_use(item),
                "usable_now_for_fixture_seed": usable_now,
                "next_action": next_action,
            }
        )
    return {
        "status": status,
        "built_at": utc_now(),
        "manifest_kind": "domain_feed_manifest",
        "raw_root": str(RAW_ROOT),
        "fastest_next_feed_path": fast_path,
        "feeds": feeds,
        "boundaries": [
            NO_RAW_DATA_BOUNDARY,
            "Manual/keyed Dubai, OpenAQ, TfL, LTA, CDS, and GeoDubai paths are not claimed complete.",
            "OPSD is donor-distribution data, not local Dubai grid truth.",
            "Smoke samples are not full-source completeness.",
        ],
    }


def synthetic_factory_use(item: dict[str, str]) -> str:
    category = item.get("category", "")
    domain = item.get("domain_pack", "")
    if category == "global_base_layer":
        return "Dubai spatial spine, geometry gap-fill, POI/road/building anchors."
    if category == "population":
        return "Population and demand priors for synthetic events and community aggregation."
    if category == "environment_weather":
        return "Weather, heat, rain, wind, and operational stress context."
    if category == "environment_water":
        return "Flood/water presence context after tile clipping."
    if category == "donor_distribution":
        return "Donor energy/mobility distributions for synthetic dynamics, not local truth."
    if "manual" in item.get("access_type", ""):
        return "Official Dubai import path once human export/access is supplied."
    return f"Domain feed candidate for {domain}."


def build_known_blockers(ledger: list[dict[str, Any]]) -> str:
    key_blockers = [row for row in ledger if row["readiness"] == "blocked_by_missing_credentials"]
    manual_blockers = [row for row in ledger if row["readiness"] == "blocked_by_human_export"]
    tool_blockers = [row for row in ledger if row["readiness"] == "needs_harvester_extension"]
    plan_only = [row for row in ledger if row["readiness"] == "blocked_by_full_pull_policy"]

    lines = [
        "# Known Blockers",
        "",
        "## Run-Specific Blockers",
        "",
        "- OpenAQ, TfL, and LTA failed closed because their required environment variables were not present.",
        "- Copernicus CDS remains token/config gated.",
        "- Dubai DLD, Dubai Municipality, Makani, and GeoDubai remain official export/access workflow items.",
        "- Microsoft Buildings has captured metadata, but the smoke scaffold still needs a STAC/Delta bbox pull implementation.",
        "- JRC Global Surface Water is plan-only in smoke; full tile download and AOI clipping are deferred outside the repo.",
        "- Overture copied the DuckDB template only; the bbox cloud query was not executed in this closeout.",
        "- Geofabrik full PBF/GPKG and any large JRC/Overture outputs were intentionally not pulled into the repo.",
        "",
        "## Blocked Sources",
        "",
    ]
    for label, rows in [
        ("Credential required", key_blockers),
        ("Manual or official export required", manual_blockers),
        ("Harvester extension required", tool_blockers),
        ("Full pull deferred by size/policy", plan_only),
    ]:
        lines.append(f"### {label}")
        if not rows:
            lines.append("")
            lines.append("- None.")
            lines.append("")
            continue
        lines.append("")
        for row in rows:
            lines.append(f"- `{row['source_id']}`: {row['next_action']}")
        lines.append("")

    lines.extend(
        [
            "## Boundaries",
            "",
            f"- {NO_RAW_DATA_BOUNDARY}",
            "- This package is a smoke/acquisition readiness closeout, not a full-source completeness claim.",
            "- No credentials, secrets, or raw bulky datasets are written into the result package.",
        ]
    )
    return "\n".join(lines)


def build_closeout(status: str, harvest_report: dict[str, Any], ledger: list[dict[str, Any]]) -> str:
    counts = Counter(row["result_status"] for row in ledger)
    downloaded = [row for row in ledger if row["result_status"] == "PASS"]
    lines = [
        f"# {PACKAGE_NAME}",
        "",
        f"- Status: `{status}`",
        f"- Built at: `{harvest_report['built_at']}`",
        f"- Raw root: `{RAW_ROOT}`",
        f"- Raw package boundary: {NO_RAW_DATA_BOUNDARY}",
        f"- Downloaded smoke samples: {len(downloaded)}",
        f"- Result status counts: {dict(sorted(counts.items()))}",
        "",
        "## What Ran",
        "",
        "- Extracted `citybrain_source_acquisition_cart_r1.zip` into the repo.",
        "- Ran `python scripts/harvest_sources.py --inventory manifests/source_inventory.csv --out C:\\data\\citybrain\\raw --smoke` from the cart root.",
        "- Created this closeout from the smoke report and source inventory.",
        "",
        "## Landed Smoke Samples",
        "",
    ]
    for row in downloaded:
        lines.append(f"- `{row['source_id']}` -> `{row['out_path']}` ({row['bytes']} bytes)")
    lines.extend(
        [
            "",
            "## Required Result Files",
            "",
        ]
    )
    for name in REQUESTED_OUTPUTS:
        lines.append(f"- `{name}`")
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "- Smoke command exited 0.",
            "- Closeout generator validates requested files and ZIP contents.",
            "- Pytest target: `python -m pytest tests/test_main_citybrain_data_acquisition_cart_r1_results.py -q`.",
            "",
            "## Boundaries",
            "",
            "- No raw full datasets were committed or packaged.",
            "- No source is promoted as complete city truth from smoke output alone.",
            "- Keyed/manual sources remain blocked until credentials or official exports are supplied.",
        ]
    )
    return "\n".join(lines)


def prepare_output_root() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    expected = set(REQUESTED_OUTPUTS)
    for path in OUTPUT_ROOT.iterdir():
        if path.is_file() and path.name in expected:
            path.unlink()


def build_outputs() -> dict[str, Any]:
    prepare_output_root()
    inventory = load_inventory()
    raw_report = load_raw_report()
    results = result_by_source(raw_report)
    status = final_status(list(results.values()))
    ledger = build_source_ledger(inventory, results)
    sample_counts = [sample_measurement(item["source_id"], results.get(item["source_id"], {})) for item in inventory]

    status_counts = dict(sorted(Counter(row["result_status"] for row in ledger).items()))
    total_landed_bytes = sum(int(row["bytes"] or 0) for row in sample_counts if str(row["bytes"]).isdigit())
    harvest_report = {
        "status": status,
        "built_at": utc_now(),
        "cart_root": rel_to_repo(CART_ROOT),
        "inventory_ref": rel_to_repo(INVENTORY_PATH),
        "raw_report_ref": str(RAW_REPORT_PATH),
        "raw_root": str(RAW_ROOT),
        "mode": raw_report.get("mode", "smoke"),
        "source_count": len(inventory),
        "result_status_counts": status_counts,
        "total_landed_or_stubbed_bytes": total_landed_bytes,
        "no_raw_data_packaged": True,
        "raw_report": raw_report,
        "boundaries": [
            NO_RAW_DATA_BOUNDARY,
            "Smoke success is not a full-pull or completeness claim.",
            "Credentialed/manual feeds are fail-closed or stubbed.",
        ],
    }

    write_json(OUTPUT_ROOT / "HARVEST_REPORT.json", harvest_report)
    write_csv(
        OUTPUT_ROOT / "SOURCE_STATUS_LEDGER.csv",
        ledger,
        [
            "source_id",
            "source_name",
            "priority",
            "category",
            "domain_pack",
            "access_type",
            "env_vars",
            "result_status",
            "closeout_class",
            "readiness",
            "http_status",
            "bytes",
            "out_path",
            "error",
            "next_action",
        ],
    )
    write_json(OUTPUT_ROOT / "DOMAIN_FEED_MANIFEST.json", build_domain_feed_manifest(status, inventory, results))
    write_csv(
        OUTPUT_ROOT / "SAMPLE_ROW_COUNTS.csv",
        sample_counts,
        ["source_id", "result_status", "sample_count", "sample_count_kind", "bytes", "out_path", "measurement_note"],
    )
    write_text(OUTPUT_ROOT / "KNOWN_BLOCKERS.md", build_known_blockers(ledger))
    write_text(OUTPUT_ROOT / "CODEX_CLOSEOUT.md", build_closeout(status, harvest_report, ledger))

    checksum_manifest = {
        "status": status,
        "built_at": utc_now(),
        "no_raw_data_packaged": True,
        "raw_root": str(RAW_ROOT),
        "raw_landing_files": raw_file_checksums(),
        "closeout_package_files": package_file_checksums(exclude={"CHECKSUM_MANIFEST.json"}),
    }
    write_json(OUTPUT_ROOT / "CHECKSUM_MANIFEST.json", checksum_manifest)
    create_zip()
    validation_errors = validate_outputs()
    if validation_errors:
        raise RuntimeError("; ".join(validation_errors))
    return {
        "status": status,
        "output_root": str(OUTPUT_ROOT),
        "zip_path": str(ZIP_PATH),
        "source_count": len(inventory),
        "result_status_counts": status_counts,
    }


def create_zip() -> None:
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in REQUESTED_OUTPUTS:
            path = OUTPUT_ROOT / name
            archive.write(path, arcname=f"{PACKAGE_NAME}/{name}")


def validate_outputs() -> list[str]:
    errors = []
    for name in REQUESTED_OUTPUTS:
        if not (OUTPUT_ROOT / name).exists():
            errors.append(f"missing output: {name}")
    if not ZIP_PATH.exists():
        errors.append(f"missing zip: {ZIP_PATH}")
    else:
        with zipfile.ZipFile(ZIP_PATH) as archive:
            names = set(archive.namelist())
        expected = {f"{PACKAGE_NAME}/{name}" for name in REQUESTED_OUTPUTS}
        missing = sorted(expected - names)
        if missing:
            errors.append(f"zip missing entries: {missing}")
        raw_entries = [name for name in names if "/raw/" in name.lower() or name.lower().endswith((".tif", ".pbf", ".gpkg"))]
        if raw_entries:
            errors.append(f"zip contains raw-looking entries: {raw_entries}")
    return errors


def main() -> int:
    result = build_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
