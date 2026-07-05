from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_main_citybrain_perception_source_registry_r1.py"
spec = importlib.util.spec_from_file_location("perception_registry", SCRIPT_PATH)
registry_mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(registry_mod)


def test_required_source_classes_are_present() -> None:
    expected = {
        "dataset_annotation",
        "sensor_inferred",
        "model_generated_narrative_not_fact_source",
        "manual_review_note",
        "replay_fixture",
        "sample_media_ref",
    }

    assert expected.issubset(set(registry_mod.SOURCE_CLASSES))


def test_registry_blocks_vss_fact_source_and_official_actions() -> None:
    registry = registry_mod.enriched_registry()
    validation = registry_mod.validate_registry(registry)

    assert validation["status"] == "PASS"
    assert all(not source["fact_source"] for source in registry["sources"])
    assert all(not source["dispatch_control_enforcement"] for source in registry["sources"])
    assert all(not source["legal_certified_finding"] for source in registry["sources"])
    assert all(not source["live_camera"] for source in registry["sources"])
    assert all(not source["production_api"] for source in registry["sources"])


def test_registry_validation_fails_malicious_vss_fact_source() -> None:
    registry = registry_mod.enriched_registry()
    for source in registry["sources"]:
        if source["source_class"] == "model_generated_narrative_not_fact_source":
            source["fact_source"] = True

    validation = registry_mod.validate_registry(registry)

    assert validation["status"] == "FAIL"
    assert any(test["test"] == "vss_cannot_be_fact_source" and not test["passed"] for test in validation["tests"])
