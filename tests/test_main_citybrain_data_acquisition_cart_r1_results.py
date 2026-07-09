from __future__ import annotations

import csv
import json
import zipfile

from scripts.run_main_citybrain_data_acquisition_cart_r1_results import (
    OUTPUT_ROOT,
    PASS_STATUS,
    RAW_ROOT,
    REQUESTED_OUTPUTS,
    ZIP_PATH,
    build_outputs,
    sha256_file,
    validate_outputs,
)


def load_json(name: str):
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))


def load_csv(name: str):
    with (OUTPUT_ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def setup_module():
    build_outputs()


def test_requested_closeout_files_and_zip_exist():
    for name in REQUESTED_OUTPUTS:
        assert (OUTPUT_ROOT / name).exists(), name
    assert ZIP_PATH.exists()
    assert validate_outputs() == []


def test_harvest_report_records_smoke_run_and_boundaries():
    report = load_json("HARVEST_REPORT.json")
    assert report["status"] == PASS_STATUS
    assert report["mode"] == "smoke"
    assert report["source_count"] == 15
    assert report["no_raw_data_packaged"] is True
    assert str(RAW_ROOT) == report["raw_root"]
    assert report["result_status_counts"]["PASS"] >= 4
    assert "FAIL_CLOSED" in report["result_status_counts"]


def test_source_status_ledger_preserves_expected_blockers():
    rows = {row["source_id"]: row for row in load_csv("SOURCE_STATUS_LEDGER.csv")}
    assert rows["open_meteo_dubai_weather"]["result_status"] == "PASS"
    assert rows["worldpop_are_population"]["result_status"] == "PASS"
    assert rows["openaq_air_quality"]["closeout_class"] == "credential_missing_fail_closed"
    assert rows["tfl_unified_api"]["readiness"] == "blocked_by_missing_credentials"
    assert rows["dld_real_estate_data"]["readiness"] == "blocked_by_human_export"
    assert rows["ms_buildings_planetary_computer"]["closeout_class"] == "metadata_captured_scaffold_gap"


def test_domain_feed_manifest_marks_fast_path_without_completeness_claim():
    manifest = load_json("DOMAIN_FEED_MANIFEST.json")
    fast_path_ids = {row["source_id"] for row in manifest["fastest_next_feed_path"]}
    assert {
        "open_meteo_dubai_weather",
        "worldpop_are_population",
        "osm_geofabrik_gcc_states",
        "overture_maps_dubai_aoi",
        "ms_buildings_planetary_computer",
    }.issubset(fast_path_ids)
    assert any("Smoke samples are not full-source completeness" in boundary for boundary in manifest["boundaries"])
    assert not next(row for row in manifest["feeds"] if row["source_id"] == "ms_buildings_planetary_computer")[
        "usable_now_for_fixture_seed"
    ]


def test_sample_counts_measure_downloaded_smoke_artifacts():
    rows = {row["source_id"]: row for row in load_csv("SAMPLE_ROW_COUNTS.csv")}
    assert int(rows["open_meteo_dubai_weather"]["sample_count"]) > 0
    assert rows["open_meteo_dubai_weather"]["sample_count_kind"] == "hourly_weather_records"
    assert int(rows["worldpop_are_population"]["sample_count"]) > 1_000_000
    assert rows["worldpop_are_population"]["sample_count_kind"] == "raster_bytes"
    assert int(rows["opsd_time_series"]["sample_count"]) > 0


def test_checksum_manifest_hashes_raw_files_but_zip_excludes_raw_data():
    manifest = load_json("CHECKSUM_MANIFEST.json")
    assert manifest["no_raw_data_packaged"] is True
    assert any(row["relative_to_raw_root"].endswith("smoke_forecast.json") for row in manifest["raw_landing_files"])
    for row in manifest["closeout_package_files"]:
        target = OUTPUT_ROOT / row["path"].split("/")[-1]
        assert target.exists(), row
        assert row["sha256"] == sha256_file(target)

    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = archive.namelist()
    assert all(not name.lower().endswith((".tif", ".pbf", ".gpkg")) for name in names)
    assert {f"{ZIP_PATH.stem}/{name}" for name in REQUESTED_OUTPUTS}.issubset(set(names))
