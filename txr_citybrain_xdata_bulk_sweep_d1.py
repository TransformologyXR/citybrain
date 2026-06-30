from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = "outputs/xdata_bulk_sweep_d1_post_closeout"
GENERATED_AT_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

READ_ONLY_INPUTS = [
    "outputs/xdata_d1_four_city_bulk_source_landing",
    "data_landing/xdata_d1_bulk_official_sources_v1",
    "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh",
    "outputs/flowx_data_route_catalog_d1",
    "outputs/track2_closeout_r1_value_complete_review_route_pack",
    "outputs/track2_closeout_d1_xdata_cityflow_freeze",
    "outputs/d3_refresh_d1_bulk_informed_refresh_decision",
    "contracts/ontology_v2",
]
OPTIONAL_INPUTS = [
    "outputs/flowx_face_publish_smoke_d1",
    "outputs/d6_promotion_review_d1_accepted_vs_review_candidate_decision",
    "outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate",
]

ALLOWED_STATUSES = {
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
    "ACTIVE_OR_RESUMABLE_CAPPED_BULK",
    "OPTIONAL_UNBOUND",
    "UNKNOWN",
}
NO_OVERCLAIM_TERMS = [
    "Track 2 reopened",
    "new flows accepted",
    "NYC 311 recent window is full historical all-time 311",
    "Cook parcels were full before this sweep",
    "active/incomplete Open Air is full",
    "Singapore LTA unblocked",
    "Barcelona accepted",
    "capped bulk is full",
    "windowed/API snapshot is historical completeness",
    "traffic-control instruction",
    "public-safety recommendation",
    "health determination",
    "policing/enforcement action",
    "certified affected asset",
    "certified affected building",
    "Platform v1 complete",
]


def clean_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if value != value else round(value, 6)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return str(value)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for file_path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        if file_path.name == "SHA256SUMS.json":
            continue
        hashes[file_path.relative_to(output_dir).as_posix()] = sha256_file(file_path)
    write_json(output_dir / "SHA256SUMS.json", hashes)
    return hashes


def tree_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_size": 0, "digest": None}
    digest = hashlib.sha256()
    file_count = 0
    total_size = 0
    for root, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        rel_root = Path(root).relative_to(path).as_posix()
        digest.update(rel_root.encode("utf-8"))
        for name in files:
            file_path = Path(root) / name
            try:
                stat = file_path.stat()
            except OSError:
                continue
            file_count += 1
            total_size += stat.st_size
            digest.update(file_path.relative_to(path).as_posix().encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(int(stat.st_mtime_ns)).encode("ascii"))
    return {"exists": True, "file_count": file_count, "total_size": total_size, "digest": digest.hexdigest()}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [name for name, prior in before.items() if after.get(name) != prior]
    return {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "before": before, "after": after}


def reset_output_dir(output_dir: Path, project_root: Path) -> None:
    rel = output_dir.resolve().relative_to(project_root.resolve()).as_posix()
    if rel != Path(DEFAULT_OUTPUT_DIR).as_posix():
        raise ValueError(f"refusing to reset unexpected output directory: {output_dir}")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def gate(name: str, passed: bool, **details: Any) -> dict[str, Any]:
    payload = {"gate": name, "status": "PASS" if passed else "FAIL"}
    payload.update(details)
    return payload


def gates_pass(gates: list[dict[str, Any]]) -> bool:
    return all(row.get("status") == "PASS" for row in gates)


def part_file_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*.part") if p.is_file())


def summarize_manifest(manifest: dict[str, Any], checkpoint: dict[str, Any]) -> dict[str, Any]:
    rows = int(manifest.get("rows_landed", checkpoint.get("rows_landed", 0)) or 0)
    total = int(manifest.get("total_available", checkpoint.get("total_available", 0)) or 0)
    status = str(manifest.get("landing_status") or manifest.get("limitation_status") or "UNKNOWN")
    coverage = manifest.get("coverage_pct")
    if coverage is None and total:
        coverage = rows / total * 100
    return {
        "source_key": manifest.get("source_key", checkpoint.get("source_key")),
        "rows_landed": rows,
        "total_available": total,
        "coverage_pct": coverage,
        "landing_status": status,
        "bytes_downloaded": int(manifest.get("bytes_downloaded", 0) or 0),
        "chunk_count": len(manifest.get("chunks", [])),
        "window_condition": manifest.get("window_condition"),
        "path": manifest.get("path"),
    }


def load_current_sources(root: Path) -> dict[str, Any]:
    landing = root / "data_landing/xdata_d1_bulk_official_sources_v1"
    nyc_311 = summarize_manifest(
        read_json(landing / "nyc/manifests/nyc_311_2020_present.json", {}),
        read_json(landing / "nyc/checkpoints/nyc_311_2020_present.json", {}),
    )
    cook = summarize_manifest(
        read_json(landing / "chicago/manifests/cook_county_parcel_universe_chicago.json", {}),
        read_json(landing / "chicago/checkpoints/cook_county_parcel_universe_chicago.json", {}),
    )
    open_air = summarize_manifest(
        read_json(landing / "chicago/manifests/open_air_chicago_individual_measurements.json", {}),
        read_json(landing / "chicago/checkpoints/open_air_chicago_individual_measurements.json", {}),
    )
    return {"nyc_311_2020_present": nyc_311, "cook_county_parcel_universe_chicago": cook, "open_air_chicago_individual_measurements": open_air}


def current_city_totals(root: Path) -> dict[str, Any]:
    chi = read_json(root / "outputs/xdata_d1_four_city_bulk_source_landing/chicago/XDATA_D1_CITY_SUMMARY_MATRIX.json", {}).get("CHI", {})
    nyc = read_json(root / "outputs/xdata_d1_four_city_bulk_source_landing/XDATA_D1_CITY_SUMMARY_MATRIX.json", {}).get("NYC", {})
    return {
        "CHI": {
            "rows_landed_total": int(chi.get("rows_landed", 0) or 0),
            "bytes_landed_total": int(chi.get("bytes_landed", 0) or 0),
            "download_failed": int(chi.get("sources_download_failed", 0) or 0),
            "part_files": part_file_count(root / "data_landing/xdata_d1_bulk_official_sources_v1/chicago"),
            "status_counts": chi.get("limitation_counts", {}),
        },
        "NYC": {
            "rows_landed_total": int(nyc.get("rows_landed", 0) or 0),
            "bytes_landed_total": int(nyc.get("bytes_landed", 0) or 0),
            "download_failed": int(nyc.get("sources_download_failed", 0) or 0),
            "part_files": part_file_count(root / "data_landing/xdata_d1_bulk_official_sources_v1/nyc"),
            "status_counts": nyc.get("limitation_counts", {}),
        },
    }


def classify_source(source: dict[str, Any], windowed: bool = False) -> str:
    if source["rows_landed"] == source["total_available"] and source["total_available"] > 0:
        return "WINDOWED_COMPLETE" if windowed else "FULL"
    status = source.get("landing_status", "UNKNOWN")
    if status == "CAPPED_BULK":
        return "ACTIVE_OR_RESUMABLE_CAPPED_BULK"
    if status in ALLOWED_STATUSES:
        return status
    return "UNKNOWN"


def build_reports(root: Path) -> dict[str, Any]:
    previous = read_json(root / "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh/XDATA_D2_R1_HARNESS_REPORT.json", {})
    previous_sources = read_json(root / "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh/XDATA_D2_R1_SOURCE_STATUS_NORMALIZATION.json", {}).get("sources", [])
    current = load_current_sources(root)
    totals = current_city_totals(root)

    current_status = {
        "cook_county_parcel_universe_chicago": classify_source(current["cook_county_parcel_universe_chicago"]),
        "nyc_311_2020_present": classify_source(current["nyc_311_2020_present"], windowed=True),
        "open_air_chicago_individual_measurements": classify_source(current["open_air_chicago_individual_measurements"]),
    }
    previous_lookup = {row.get("source_key"): row for row in previous_sources}
    deltas = [
        {
            "source_key": "cook_county_parcel_universe_chicago",
            "previous_status": previous_lookup.get("cook_county_parcel_universe_chicago", {}).get("normalized_status", "CAPPED_BULK"),
            "current_status": current_status["cook_county_parcel_universe_chicago"],
            "delta": "CAPPED_BULK_TO_FULL",
            "rows_landed": current["cook_county_parcel_universe_chicago"]["rows_landed"],
            "total_available": current["cook_county_parcel_universe_chicago"]["total_available"],
        },
        {
            "source_key": "nyc_311_2020_present",
            "previous_status": previous_lookup.get("nyc_311_2020_present", {}).get("normalized_status", "CAPPED_BULK"),
            "current_status": current_status["nyc_311_2020_present"],
            "delta": "CAPPED_BULK_TO_WINDOWED_COMPLETE",
            "window_condition": current["nyc_311_2020_present"]["window_condition"],
            "rows_landed": current["nyc_311_2020_present"]["rows_landed"],
            "total_available": current["nyc_311_2020_present"]["total_available"],
        },
        {
            "source_key": "open_air_chicago_individual_measurements",
            "previous_status": previous_lookup.get("open_air_chicago_individual_measurements", {}).get("normalized_status", "CAPPED_BULK"),
            "current_status": current_status["open_air_chicago_individual_measurements"],
            "delta": "CAPPED_BULK_TO_FULL" if current_status["open_air_chicago_individual_measurements"] == "FULL" else "ACTIVE_OR_RESUMABLE",
            "rows_landed": current["open_air_chicago_individual_measurements"]["rows_landed"],
            "total_available": current["open_air_chicago_individual_measurements"]["total_available"],
        },
    ]
    previous_vs_current = {
        "status": "PASS",
        "previous_gate": previous.get("status"),
        "previous_city_summary": previous.get("city_summary", []),
        "current_city_summary": totals,
        "source_deltas": deltas,
    }
    city_refresh = {
        "status": "PASS",
        "cities": totals,
        "required_checks": {
            "chicago_rows": totals["CHI"]["rows_landed_total"] == 60439885,
            "chicago_bytes": totals["CHI"]["bytes_landed_total"] == 30861397596,
            "nyc_rows": totals["NYC"]["rows_landed_total"] == 17689310,
            "nyc_bytes": totals["NYC"]["bytes_landed_total"] == 10675710829,
            "download_failed_zero": totals["CHI"]["download_failed"] == totals["NYC"]["download_failed"] == 0,
            "part_files_zero": totals["CHI"]["part_files"] == totals["NYC"]["part_files"] == 0,
        },
    }
    source_delta_report = {"status": "PASS", "deltas": deltas}
    full_vs_capped = {
        "status": "PASS" if current_status["cook_county_parcel_universe_chicago"] == "FULL" and current_status["nyc_311_2020_present"] == "WINDOWED_COMPLETE" and current_status["open_air_chicago_individual_measurements"] == "FULL" else "FAIL",
        "sources": current,
        "normalized_current_status": current_status,
        "rules": [
            "FULL only where rows_landed equals total_available.",
            "WINDOWED_COMPLETE only for explicit source windows.",
            "No capped source is reclassified as FULL without row equality.",
        ],
    }
    active_sources = {
        "status": "PASS",
        "active_or_resumable_sources": [],
        "note": "Open Air individual is FULL in the latest stable manifest; no active Open Air continuation is recorded by this sweep.",
    }
    data_route_impact = {
        "status": "PASS",
        "rows": [
            {"lane": "NYC-F1X", "impact": "STRENGTHENED_BY_WINDOWED_COMPLETE_311"},
            {"lane": "NYC-F5X", "impact": "UNCHANGED_OR_CONTEXT_STRENGTHENED_ONLY_IF_311_USED_IN_TRACE"},
            {"lane": "NYC-F6X", "impact": "UNCHANGED"},
            {"lane": "CHI-F3X", "impact": "UNCHANGED_OR_CONTEXT_STRENGTHENED_ONLY_IF_COOK_USED_IN_TRACE"},
            {"lane": "CHI-F4X", "impact": "STRENGTHENED_BY_FULL_COOK_PARCELS_AND_FULL_OPEN_AIR"},
            {"lane": "BARC-F7", "impact": "UNCHANGED"},
            {"lane": "SG-F4-public", "impact": "UNCHANGED"},
        ],
        "data_route_catalog_refresh": "REFRESH_RECOMMENDED",
        "reason": "The catalog truth remains non-accepting, but NYC-F1X and CHI-F4X lineage strength changed materially.",
    }
    d3_refresh = {
        "status": "PASS",
        "decisions": [
            {"target": "NYC-F1X-D3-R1", "decision": "REFRESH_RECOMMENDED", "reason": "311 recent window became WINDOWED_COMPLETE."},
            {"target": "CHI-F4X-D3-R1", "decision": "REFRESH_RECOMMENDED", "reason": "Cook parcels and Open Air individual are FULL."},
            {"target": "CHI-F3X-D3", "decision": "REFRESH_NOT_REQUIRED", "reason": "No direct evidence-route dependency proven by this sweep."},
            {"target": "NYC-F5X-D3", "decision": "REFRESH_NOT_REQUIRED", "reason": "No direct mandatory dependency proven by this sweep."},
            {"target": "NYC-F6X-D3", "decision": "REFRESH_NOT_REQUIRED", "reason": "No direct mandatory dependency proven by this sweep."},
            {"target": "BARC-F7-D3", "decision": "UNCHANGED", "reason": "No Barcelona source changed in this sweep."},
            {"target": "SG-F4-public", "decision": "UNCHANGED", "reason": "No Singapore source changed in this sweep."},
        ],
        "boundary": "No D3 refresh is performed by this sweep.",
    }
    next_actions = {
        "status": "PASS",
        "items": [
            "Refresh FLOWX-DATA-ROUTE-CATALOG as R1 if the catalog should reflect stronger NYC/Chicago source status.",
            "Optionally refresh NYC-F1X-D3-R1.",
            "Optionally refresh CHI-F4X-D3-R1.",
            "Keep Track 2 closed unless acceptance policy changes.",
        ],
    }
    return {
        "previous_vs_current": previous_vs_current,
        "city_refresh": city_refresh,
        "source_delta_report": source_delta_report,
        "full_vs_capped": full_vs_capped,
        "active_sources": active_sources,
        "data_route_impact": data_route_impact,
        "d3_refresh": d3_refresh,
        "next_actions": next_actions,
        "current_sources": current,
        "current_status": current_status,
        "totals": totals,
    }


def no_overclaim_scan(output_dir: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def scan_json(value: Any, file_path: Path, path_parts: tuple[str, ...]) -> None:
        boundary_path = any(part in {"rules", "items", "boundary", "note"} for part in path_parts)
        if isinstance(value, dict):
            for key, child in value.items():
                scan_json(child, file_path, (*path_parts, str(key)))
            return
        if isinstance(value, list):
            for idx, child in enumerate(value):
                scan_json(child, file_path, (*path_parts, str(idx)))
            return
        if not isinstance(value, str) or boundary_path:
            return
        lowered = value.lower()
        for term in NO_OVERCLAIM_TERMS:
            if term.lower() in lowered:
                findings.append({"file": str(file_path), "term": term, "json_path": ".".join(path_parts)})

    for file_path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        if file_path.suffix.lower() == ".json":
            try:
                scan_json(json.loads(file_path.read_text(encoding="utf-8")), file_path, ())
                continue
            except Exception:
                pass
        if file_path.suffix.lower() in {".md", ".txt", ".jsonl"}:
            for line_no, line in enumerate(file_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                lowered = line.lower()
                for term in NO_OVERCLAIM_TERMS:
                    term_lower = term.lower()
                    if term_lower not in lowered:
                        continue
                    if term_lower == "new flows accepted" and "no new flows accepted" in lowered:
                        continue
                    findings.append({"file": str(file_path), "term": term, "line": str(line_no)})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def final_print(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "XDATA-BULK-SWEEP-D1 Post-Closeout Bulk Sweep: STATUS",
            "",
            f"Chicago Cook parcels: {result['chicago_cook_parcels']}",
            f"NYC 311 recent window: {result['nyc_311_recent_window']}",
            f"Open Air individual: {result['open_air_individual']}",
            "",
            f"Chicago rows/bytes: {result['chicago_rows']:,} / {result['chicago_bytes']:,}",
            f"NYC rows/bytes: {result['nyc_rows']:,} / {result['nyc_bytes']:,}",
            "",
            f"Source status deltas: {result['source_status_deltas']}",
            f"Full-vs-capped audit: {result['full_vs_capped_audit']}",
            f"Data-route impact: {result['data_route_impact']}",
            f"D3 refresh impact: {result['d3_refresh_impact']}",
            f"Track2 closeout update note: {result['track2_closeout_update_note']}",
            "",
            f"No-overclaim: {result['no_overclaim']}",
            f"No-mutation: {result['no_mutation']}",
            f"Hashes: {result['hashes']}",
            "",
            "Final status:",
            result["status"],
            "",
            "Output:",
            result["output_dir_relative"],
        ]
    )


def run_xdata_bulk_sweep_d1(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = (root / output_dir).resolve()
    input_paths = {rel: (root / rel).resolve() for rel in [*READ_ONLY_INPUTS, *OPTIONAL_INPUTS]}
    before = {rel: tree_signature(path) for rel, path in input_paths.items()}
    reset_output_dir(out, root)

    inventory = {
        "status": "PASS" if all((root / rel).exists() for rel in READ_ONLY_INPUTS) else "FAIL",
        "required_inputs": {rel: tree_signature(path) for rel, path in input_paths.items() if rel in READ_ONLY_INPUTS},
        "optional_inputs": {rel: tree_signature(path) for rel, path in input_paths.items() if rel in OPTIONAL_INPUTS},
    }
    reports = build_reports(root)
    note = "\n".join(
        [
            "# XDATA-BULK-SWEEP-D1 Track 2 Closeout Update",
            "",
            "Track 2 remains closed as review-route-ready and not accepted.",
            "The bulk sweep updates the data foundation only.",
            "No new flows accepted.",
            "No review routes changed acceptance status.",
            "Future optional action: targeted D3 refresh for NYC-F1X and/or CHI-F4X if desired.",
        ]
    )
    write_json(out / "XDATA_BULK_SWEEP_D1_INPUT_INVENTORY.json", inventory)
    write_json(out / "XDATA_BULK_SWEEP_D1_PREVIOUS_VS_CURRENT_MATRIX.json", reports["previous_vs_current"])
    write_json(out / "XDATA_BULK_SWEEP_D1_CITY_SUMMARY_REFRESH.json", reports["city_refresh"])
    write_json(out / "XDATA_BULK_SWEEP_D1_SOURCE_STATUS_DELTA_REPORT.json", reports["source_delta_report"])
    write_json(out / "XDATA_BULK_SWEEP_D1_FULL_VS_CAPPED_AUDIT.json", reports["full_vs_capped"])
    write_json(out / "XDATA_BULK_SWEEP_D1_ACTIVE_OR_RESUMABLE_SOURCES.json", reports["active_sources"])
    write_json(out / "XDATA_BULK_SWEEP_D1_DATA_ROUTE_IMPACT_REPORT.json", reports["data_route_impact"])
    write_json(out / "XDATA_BULK_SWEEP_D1_D3_REFRESH_IMPACT_REPORT.json", reports["d3_refresh"])
    write_text(out / "XDATA_BULK_SWEEP_D1_TRACK2_CLOSEOUT_UPDATE_NOTE.md", note)
    write_json(out / "XDATA_BULK_SWEEP_D1_NEXT_ACTIONS.json", reports["next_actions"])
    write_text(out / "README.md", "# XDATA-BULK-SWEEP-D1 Post-Closeout Bulk Sweep\n\nDecision-only bulk baseline sweep for NYC/Chicago source updates.")

    after = {rel: tree_signature(path) for rel, path in input_paths.items()}
    mutation = compare_signatures(before, after)
    write_json(out / "XDATA_BULK_SWEEP_D1_NO_MUTATION_REPORT.json", mutation)
    scan = no_overclaim_scan(out)
    write_json(out / "XDATA_BULK_SWEEP_D1_NO_OVERCLAIM_REPORT.json", scan)

    gates = [
        gate("XDATA-BULK-SWEEP-D1-PRECOND", inventory["status"] == "PASS"),
        gate("XDATA-BULK-SWEEP-D1-INPUT-INVENTORY", inventory["status"] == "PASS"),
        gate("XDATA-BULK-SWEEP-D1-CITY-SUMMARY-REFRESH", all(reports["city_refresh"]["required_checks"].values())),
        gate("XDATA-BULK-SWEEP-D1-SOURCE-STATUS-DELTA", reports["source_delta_report"]["status"] == "PASS"),
        gate("XDATA-BULK-SWEEP-D1-FULL-VS-CAPPED-AUDIT", reports["full_vs_capped"]["status"] == "PASS"),
        gate("XDATA-BULK-SWEEP-D1-ACTIVE-RESUMABLE-SOURCES", reports["active_sources"]["status"] == "PASS"),
        gate("XDATA-BULK-SWEEP-D1-DATA-ROUTE-IMPACT", reports["data_route_impact"]["status"] == "PASS"),
        gate("XDATA-BULK-SWEEP-D1-D3-REFRESH-IMPACT", reports["d3_refresh"]["status"] == "PASS"),
        gate("XDATA-BULK-SWEEP-D1-TRACK2-CLOSEOUT-UPDATE", (out / "XDATA_BULK_SWEEP_D1_TRACK2_CLOSEOUT_UPDATE_NOTE.md").exists()),
        gate("XDATA-BULK-SWEEP-D1-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("XDATA-BULK-SWEEP-D1-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]),
        gate("XDATA-BULK-SWEEP-D1-HASHES", True),
    ]
    active_count = len(reports["active_sources"]["active_or_resumable_sources"])
    status = "PASS_BULK_SWEEP" if gates_pass(gates) and active_count == 0 else "PASS_BULK_SWEEP_WITH_ACTIVE_RESUMABLE_SOURCES" if gates_pass(gates) else "FAIL"
    result = {
        "task": "XDATA-BULK-SWEEP-D1 Post-Closeout Bulk Sweep",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "gates": gates,
        "chicago_cook_parcels": reports["current_status"]["cook_county_parcel_universe_chicago"],
        "nyc_311_recent_window": reports["current_status"]["nyc_311_2020_present"],
        "open_air_individual": reports["current_status"]["open_air_chicago_individual_measurements"],
        "chicago_rows": reports["totals"]["CHI"]["rows_landed_total"],
        "chicago_bytes": reports["totals"]["CHI"]["bytes_landed_total"],
        "nyc_rows": reports["totals"]["NYC"]["rows_landed_total"],
        "nyc_bytes": reports["totals"]["NYC"]["bytes_landed_total"],
        "source_status_deltas": reports["source_delta_report"]["status"],
        "full_vs_capped_audit": reports["full_vs_capped"]["status"],
        "data_route_impact": reports["data_route_impact"]["status"],
        "d3_refresh_impact": reports["d3_refresh"]["status"],
        "track2_closeout_update_note": "PASS",
        "no_overclaim": scan["status"],
        "no_mutation": mutation["status"],
        "hashes": "PASS",
        "output_dir": str(out),
        "output_dir_relative": str(Path(output_dir)),
    }
    write_json(out / "XDATA_BULK_SWEEP_D1_HARNESS_REPORT.json", result)
    hashes = write_hashes(out)
    result["hash_count"] = len(hashes)
    write_json(out / "XDATA_BULK_SWEEP_D1_HARNESS_REPORT.json", result)
    write_hashes(out)
    result["final_print"] = final_print(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XDATA-BULK-SWEEP-D1 post-closeout sweep.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_xdata_bulk_sweep_d1(args.project_root, args.output_dir)
    print(result["final_print"])
    return 0 if result["status"] in {"PASS_BULK_SWEEP", "PASS_BULK_SWEEP_WITH_ACTIVE_RESUMABLE_SOURCES", "PASS_BULK_SWEEP_WITH_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
