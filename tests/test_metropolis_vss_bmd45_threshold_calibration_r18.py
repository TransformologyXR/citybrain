from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_main_citybrain_metropolis_vss_bmd45_threshold_calibration_and_sample_expansion_r18.py"
spec = importlib.util.spec_from_file_location("r18_runner", SCRIPT_PATH)
r18 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(r18)


def test_r18_dataset_class_family_expansion() -> None:
    assert r18.family_for_dataset_label("Hatchback") == "vehicle_family:car"
    assert r18.family_for_dataset_label("Mini-bus") == "vehicle_family:bus"
    assert r18.family_for_dataset_label("LCV") == "vehicle_family:truck"
    assert r18.family_for_dataset_label("Bicycle") == "vehicle_family:two_wheeler"


def test_r18_compare_uses_075_threshold() -> None:
    dataset_rows = [
        {
            "annotation_id": 1,
            "bbox": {"x": 0, "y": 0, "w": 100, "h": 100},
            "class_family": "vehicle_family:car",
            "class_label": "Sedan",
            "frame_sequence_index": 0,
            "source_class": "dataset_annotation",
        }
    ]
    sensor_rows = [
        {
            "bbox": {"x": 2, "y": 2, "w": 96, "h": 96},
            "candidate_observation_id": "sensor-1",
            "class_family": "vehicle_family:car",
            "class_label": "car",
            "confidence": 0.42,
            "frame_sequence_index": 0,
            "source_class": "sensor_inferred",
        }
    ]
    report, _records, false_positive, missed = r18.compare_rows(dataset_rows, sensor_rows)

    assert report["metrics"]["matches_at_threshold"]["0.75"] == 1
    assert false_positive == []
    assert missed == []


def test_r18_calibration_distribution_bands() -> None:
    sensor_rows = [
        {"bbox": {"x": 0, "y": 0, "w": 1, "h": 1}, "class_family": "vehicle_family:car", "class_label": "car", "confidence": 0.2},
        {"bbox": {"x": 0, "y": 0, "w": 1, "h": 1}, "class_family": "vehicle_family:car", "class_label": "car", "confidence": 0.3},
        {"bbox": {"x": 0, "y": 0, "w": 1, "h": 1}, "class_family": "vehicle_family:bus", "class_label": "bus", "confidence": 0.6},
    ]
    report = r18.calibration_report(sensor_rows, {"metrics": {"matches_at_threshold": {"0.25": 1}}})

    assert report["confidence_distribution"]["bands"]["lt_0_25"] == 1
    assert report["confidence_distribution"]["bands"]["0_25_to_lt_0_35"] == 1
    assert report["confidence_distribution"]["bands"]["gte_0_50"] == 1
    assert report["per_class_candidate_counts"] == {"bus": 1, "car": 2}
