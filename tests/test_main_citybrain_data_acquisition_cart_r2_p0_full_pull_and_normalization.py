from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.run_main_citybrain_data_acquisition_cart_r2_p0_full_pull_and_normalization import (
    OUTPUT_ROOT,
    REQUESTED_OUTPUTS,
    STATUS_PASS_LIMITATIONS,
    validate_outputs,
)


def load_json(name: str):
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))


def load_csv(name: str):
    with (OUTPUT_ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_required_r2_result_files_exist_and_parse():
    for name in REQUESTED_OUTPUTS:
        path = OUTPUT_ROOT / name
        assert path.exists(), name
        if path.suffix == ".json":
            assert load_json(name)
    assert validate_outputs() == []


def test_master_decision_passes_acceptance_contract():
    decision = load_json("R2_MASTER_DECISION.json")
    assert decision["status"] == STATUS_PASS_LIMITATIONS
    assert decision["source_count"] == 15
    assert decision["normalized_dataset_count"] >= 9
    assert all(decision["acceptance"].values())
    for dataset_id in [
        "overture_dubai_roads",
        "osm_dubai_aoi_base_features",
        "ms_buildings_dubai_vector_tile_footprints",
        "worldpop_dubai_population_priors_005deg",
        "open_meteo_dubai_hourly_weather",
        "opsd_energy_donor_distribution_sample",
        "jrc_gsw_dubai_occurrence_002deg",
    ]:
        assert dataset_id in decision["normalized_dataset_ids"]


def test_source_ledger_keeps_keyed_and_manual_sources_fail_closed():
    rows = {row["source_id"]: row for row in load_csv("SOURCE_STATUS_LEDGER_R2.csv")}
    assert rows["overture_maps_dubai_aoi"]["r2_status"] == "PASS_NORMALIZED_AOI_SAMPLE"
    assert rows["osm_geofabrik_gcc_states"]["r2_status"].startswith("PASS_OSM_SEED_AOI_NORMALIZED")
    assert rows["ms_buildings_planetary_computer"]["r2_status"] == "PASS_BOUNDED_VECTOR_TILE_NORMALIZED"
    assert rows["jrc_global_surface_water_dubai_tile"]["row_count"] != "0"
    for source_id in [
        "openaq_air_quality",
        "tfl_unified_api",
        "lta_datamall",
        "copernicus_cds_era5",
        "dld_real_estate_data",
        "dubai_municipality_open_data",
        "makani_open_data",
        "geodubai_gis_services",
    ]:
        assert rows[source_id]["r2_status"].startswith("FAIL_CLOSED")
        assert rows[source_id]["row_count"] == "0"


def test_normalized_manifest_points_to_existing_bounded_derivatives():
    manifest = load_json("NORMALIZED_DATASET_MANIFEST.json")
    assert manifest["status"] == STATUS_PASS_LIMITATIONS
    for dataset in manifest["datasets"]:
        assert dataset["row_count"] >= 0
        for ref_key in ["parquet_ref", "jsonl_ref"]:
            path = Path(dataset[ref_key])
            assert path.exists(), dataset
            assert path.stat().st_size > 0


def test_factory_feed_manifest_preserves_boundaries():
    manifest = load_json("DOMAIN_FACTORY_FEED_MANIFEST_R2.json")
    readiness = manifest["factory_seed_readiness"]
    assert readiness["has_geometry_base_city_feed"]
    assert readiness["has_population_prior"]
    assert readiness["has_weather_environment_feed"]
    assert readiness["has_energy_donor_distribution"]
    assert any("No source is promoted as complete city truth" in item for item in manifest["boundaries"])
    assert any("No human/person-level data" in item for item in manifest["boundaries"])


def test_raw_checksum_manifest_hashes_external_files_without_packaging_raw():
    manifest = load_json("RAW_EXTERNAL_CHECKSUM_MANIFEST.json")
    assert manifest["raw_data_packaged_in_repo"] is False
    raw_paths = {row["relative_to_raw_r2_root"] for row in manifest["raw_external_files"]}
    assert any(path.endswith("time_series_60min_singleindex.csv") for path in raw_paths)
    assert any("jrc_global_surface_water" in path and path.endswith(".tif") for path in raw_paths)
    assert any("microsoft_buildings" in path and path.endswith(".mvt") for path in raw_paths)
    assert manifest["normalized_repo_files"]


def test_population_weather_energy_report_labels_opsd_as_donor_only():
    report = load_json("POPULATION_WEATHER_ENERGY_DONOR_REPORT.json")
    assert report["status"] == "PASS"
    assert report["population"]["aggregate_row_count"] > 0
    assert report["weather"]["hourly_rows"] > 0
    assert report["water_remote_sensing"]["aggregate_row_count"] > 0
    assert "Donor distribution only" in report["energy_donor"]["truth_boundary"]
