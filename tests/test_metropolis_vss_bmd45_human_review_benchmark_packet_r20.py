from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_main_citybrain_metropolis_vss_bmd45_human_review_benchmark_packet_r20.py"
spec = importlib.util.spec_from_file_location("r20_runner", SCRIPT_PATH)
r20 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(r20)


def test_frame_cards_preserve_source_labels() -> None:
    frame_records = [
        {
            "annotation_count": 2,
            "frame_sequence_index": 0,
            "matches": [{"iou": 0.6, "candidate_observation_id": "sensor-1"}],
            "sensor_detection_count": 2,
            "unmatched_annotation_count": 1,
            "unmatched_sensor_detection_count": 1,
        }
    ]
    candidates = [
        {"class_label": "car", "confidence": 0.4, "frame_sequence_index": 0},
        {"class_label": "person", "confidence": 0.2, "frame_sequence_index": 0},
    ]
    refs = [{"frame_replay_id": "frame-0", "sequence_index": 0}]

    cards = r20.frame_cards(frame_records, candidates, refs, {"recommended_confidence_threshold_bands": {}})

    assert cards[0]["dataset_annotation_summary"]["source_class"] == "dataset_annotation"
    assert cards[0]["sensor_inferred_summary"]["source_class"] == "sensor_inferred"
    assert cards[0]["review_label"] == "Review unmatched candidates and missed annotations"


def test_review_lists_do_not_call_items_findings() -> None:
    frame_records = [
        {
            "frame_sequence_index": 0,
            "matches": [{"annotation_id": 1, "candidate_observation_id": "sensor-1"}],
            "unmatched_annotation_count": 1,
        }
    ]
    candidates = [
        {"candidate_observation_id": "sensor-1", "frame_sequence_index": 0, "source_class": "sensor_inferred"},
        {"candidate_observation_id": "sensor-2", "frame_sequence_index": 0, "source_class": "sensor_inferred"},
    ]

    false_positive, missed = r20.review_lists(frame_records, candidates)

    assert false_positive[0]["candidate_observation_id"] == "sensor-2"
    assert false_positive[0]["source_class"] == "sensor_inferred"
    assert "candidate review only" in false_positive[0]["review_note"]
    assert missed[0]["source_class"] == "dataset_annotation"
