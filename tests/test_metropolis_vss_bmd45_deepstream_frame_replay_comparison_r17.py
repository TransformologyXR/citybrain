from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_main_citybrain_metropolis_vss_bmd45_deepstream_frame_replay_comparison_r17.py"
spec = importlib.util.spec_from_file_location("r17_runner", SCRIPT_PATH)
r17 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(r17)


def test_class_family_mapping_keeps_sources_separate() -> None:
    assert r17.map_class_family("Two-wheeler", "dataset_annotation") == "vehicle_family:two_wheeler"
    assert r17.map_class_family("bicycle", "sensor_inferred") == "vehicle_family:two_wheeler"
    assert r17.map_class_family("person", "sensor_inferred") == "non_vehicle_family:person"
    assert r17.map_class_family("mystery", "dataset_annotation") == "vehicle_family:unknown_vehicle"


def test_compute_iou_pixel_xywh() -> None:
    a = {"x": 0, "y": 0, "w": 100, "h": 100}
    b = {"x": 50, "y": 50, "w": 100, "h": 100}
    assert round(r17.compute_iou(a, b), 4) == 0.1429
    assert r17.compute_iou(a, {"x": 200, "y": 200, "w": 10, "h": 10}) == 0.0


def test_compare_matches_only_compatible_class_families() -> None:
    dataset_rows = [
        {
            "annotation_id": 1,
            "bbox": {"x": 10, "y": 10, "w": 40, "h": 40},
            "candidate_observation_id": "dataset-1",
            "class_family": "vehicle_family:two_wheeler",
            "class_label": "Two-wheeler",
            "frame_sequence_index": 0,
            "source_class": "dataset_annotation",
        }
    ]
    sensor_rows = [
        {
            "bbox": {"x": 12, "y": 12, "w": 38, "h": 38},
            "candidate_observation_id": "sensor-1",
            "class_label": "bicycle",
            "frame_sequence_index": 0,
            "source_class": "sensor_inferred",
        },
        {
            "bbox": {"x": 12, "y": 12, "w": 38, "h": 38},
            "candidate_observation_id": "sensor-2",
            "class_label": "car",
            "frame_sequence_index": 0,
            "source_class": "sensor_inferred",
        },
    ]

    report, records = r17.compare_annotations_to_sensor_detections(dataset_rows, sensor_rows)

    assert report["sensor_detection_count"] == 2
    assert report["metrics"]["matches_at_threshold"]["0.5"] == 1
    assert records[0]["matches"][0]["candidate_observation_id"] == "sensor-1"
    assert records[0]["unmatched_sensor_detections"][0]["candidate_observation_id"] == "sensor-2"
