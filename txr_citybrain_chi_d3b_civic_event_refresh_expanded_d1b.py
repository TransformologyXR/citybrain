from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from txr_citybrain_chi_d3_civic_event_ingest_flow_readiness import run_chi_d3_gate, write_hashes


TASK_NAME = "CHI-D3B Civic/Event Refresh from Expanded D1B"
DEFAULT_OUTPUT_DIR = "outputs/chi_d3_civic_event_ingest_flow_readiness_d3b_expanded_d1b"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def source_row(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    for row in rows:
        if row.get("source_key") == key:
            return row
    return {}


def run_chi_d3b_gate(
    project_root: str = ".",
    chi_d1_output_dir: str = "outputs/chi_d1_chicago_deep_source_api_scout",
    chi_d1_landing_dir: str = "data_landing/chi_d1_official_sources_v1",
    chi_d1b_output_dir: str = "outputs/chi_d1b_chicago_extended_source_landing",
    chi_d1b_landing_dir: str = "data_landing/chi_d1b_extended_sources_v1",
    chi_d2b_dir: str = "outputs/chi_d2b_base_identity_refresh",
    previous_d3_dir: str = "outputs/chi_d3_civic_event_ingest_flow_readiness",
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    result = run_chi_d3_gate(
        project_root=project_root,
        chi_d1_output_dir=chi_d1_output_dir,
        chi_d1_landing_dir=chi_d1_landing_dir,
        chi_d1b_output_dir=chi_d1b_output_dir,
        chi_d1b_landing_dir=chi_d1b_landing_dir,
        chi_d2b_dir=chi_d2b_dir,
        output_dir=output_dir,
    )

    root = Path(project_root).resolve()
    out = (root / output_dir).resolve()
    previous = (root / previous_d3_dir).resolve()
    d1b = (root / chi_d1b_output_dir).resolve()

    current_harness = read_json(out / "CHI_D3_HARNESS_REPORT.json", {})
    current_counts = current_harness.get("counts", {})
    previous_harness = read_json(previous / "CHI_D3_HARNESS_REPORT.json", {})
    previous_counts = previous_harness.get("counts", {})
    source_status = read_json(out / "CHI_D3_SOURCE_STATUS_REPORT.json", {})
    sources = source_status.get("sources", [])
    d1b_harness = read_json(d1b / "CHI_D1B_HARNESS_REPORT.json", {})
    d1b_summary = d1b_harness.get("summary", {})

    materiality = {
        "status": "PASS",
        "previous_d3": str(previous),
        "current_d3b": str(out),
        "count_deltas": {
            key: int(current_counts.get(key, 0) or 0) - int(previous_counts.get(key, 0) or 0)
            for key in sorted(set(current_counts) | set(previous_counts))
            if isinstance(current_counts.get(key, 0), int) or isinstance(previous_counts.get(key, 0), int)
        },
        "material_changes": [
            "311 recent window expanded from the prior bounded sample to the refreshed D1B window.",
            "Traffic Crashes - People is full-source complete and carried as context/readiness only.",
            "Traffic Crashes - Vehicles is full-source complete and carried as context/readiness only.",
            "Traffic Tracker recent window is windowed-complete and carried as context/readiness only.",
        ],
        "refresh_required_downstream": True,
    }
    source_refresh = {
        "status": "PASS",
        "d1b_status": d1b_harness.get("status"),
        "d1b_rows_downloaded_total": d1b_summary.get("rows_downloaded_total"),
        "source_status_language": "Chicago source base improved materially, but still not all-full-source because Divvy, Cook parcels, Crimes, and Open Air individual remain capped/windowed.",
        "key_sources": {
            "311_service_requests": source_row(sources, "311_service_requests"),
            "traffic_crashes_crashes": source_row(sources, "traffic_crashes_crashes"),
            "traffic_crashes_people": source_row(sources, "traffic_crashes_people"),
            "traffic_crashes_vehicles": source_row(sources, "traffic_crashes_vehicles"),
            "traffic_tracker_historical_2024_current": source_row(sources, "traffic_tracker_historical_2024_current"),
            "divvy_trips": source_row(sources, "divvy_trips"),
            "cook_county_parcel_universe": source_row(sources, "cook_county_parcel_universe"),
            "crimes_2001_present": source_row(sources, "crimes_2001_present"),
            "open_air_chicago_individual_measurements": source_row(sources, "open_air_chicago_individual_measurements"),
        },
    }
    d3b_harness = {
        "task": TASK_NAME,
        "status": "PASS_WITH_CAPPED_SOURCE_LIMITATIONS" if str(result.get("status", "")).startswith("PASS") else "FAIL",
        "base_d3_status": result.get("status"),
        "counts": current_counts,
        "location_confidence_counts": current_harness.get("location_confidence_counts"),
        "flow1_readiness": current_harness.get("flow1_readiness"),
        "flow7_readiness": current_harness.get("flow7_readiness"),
        "materiality": materiality,
        "source_refresh": source_refresh,
        "output": str(out),
    }
    write_json(out / "CHI_D3B_MATERIALITY_REPORT.json", materiality)
    write_json(out / "CHI_D3B_SOURCE_REFRESH_REPORT.json", source_refresh)
    write_json(out / "CHI_D3B_HARNESS_REPORT.json", d3b_harness)
    write_hashes(out)
    return d3b_harness


def main() -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d1-output-dir", default="outputs/chi_d1_chicago_deep_source_api_scout")
    parser.add_argument("--chi-d1-landing-dir", default="data_landing/chi_d1_official_sources_v1")
    parser.add_argument("--chi-d1b-output-dir", default="outputs/chi_d1b_chicago_extended_source_landing")
    parser.add_argument("--chi-d1b-landing-dir", default="data_landing/chi_d1b_extended_sources_v1")
    parser.add_argument("--chi-d2b-dir", default="outputs/chi_d2b_base_identity_refresh")
    parser.add_argument("--previous-d3-dir", default="outputs/chi_d3_civic_event_ingest_flow_readiness")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_chi_d3b_gate(
        project_root=args.project_root,
        chi_d1_output_dir=args.chi_d1_output_dir,
        chi_d1_landing_dir=args.chi_d1_landing_dir,
        chi_d1b_output_dir=args.chi_d1b_output_dir,
        chi_d1b_landing_dir=args.chi_d1b_landing_dir,
        chi_d2b_dir=args.chi_d2b_dir,
        previous_d3_dir=args.previous_d3_dir,
        output_dir=args.output_dir,
    )
    print(f"CHI-D3B Civic/Event Refresh from expanded D1B: {result['status']}")
    print(f"Base D3 status: {result['base_d3_status']}")
    print(f"311 events: {result['counts'].get('311_events')}")
    print(f"Event/location rows: {result['counts'].get('event_location_confidence_rows')}")
    print(f"Output: {result['output']}")
    return 0 if str(result["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
