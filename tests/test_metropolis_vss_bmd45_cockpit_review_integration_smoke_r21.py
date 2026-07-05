from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_main_citybrain_metropolis_vss_bmd45_cockpit_review_integration_smoke_r21.py"
spec = importlib.util.spec_from_file_location("r21_runner", SCRIPT_PATH)
r21 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(r21)


def test_make_frame_cards_keeps_external_media_only() -> None:
    cards = r21.make_frame_cards(
        [
            {
                "dataset_annotation_summary": {"source_class": "dataset_annotation"},
                "external_media_ref": {"external_media_ref": True, "media_url": "https://example.test/frame.png"},
                "frame_replay_id": "frame-1",
                "frame_sequence_index": 0,
                "review_label": "Review",
                "sensor_inferred_summary": {"source_class": "sensor_inferred"},
            }
        ]
    )

    assert cards[0]["media_packaged"] is False
    assert cards[0]["external_media_ref"]["external_media_ref"] is True
    assert cards[0]["source_labels"]["dataset_annotations"] == "dataset_annotation"
    assert cards[0]["source_labels"]["deepstream_metropolis"] == "sensor_inferred"


def test_app_consumption_smoke_passes_required_fields() -> None:
    tile = {
        "source_labels": ["BMD-45 labels: dataset_annotation"],
        "status_label": "Ready",
        "tile_id": "tile-1",
        "title": "Review",
    }
    cards = [
        {
            "external_media_ref": {"external_media_ref": True},
            "human_review_required": True,
            "media_packaged": False,
        }
    ]
    packet = {
        "human_review_required": True,
        "source_classes": {
            "dataset_annotations": "dataset_annotation",
            "deepstream_metropolis": "sensor_inferred",
        },
    }

    smoke = r21.app_consumption_smoke(tile, cards, packet)

    assert smoke["status"] == "PASS"
    assert all(check["passed"] for check in smoke["checks"])


def test_app_consumption_smoke_fails_missing_external_refs() -> None:
    tile = {"source_labels": ["x"], "status_label": "Ready", "tile_id": "tile-1", "title": "Review"}
    cards = [{"external_media_ref": {}, "human_review_required": True, "media_packaged": False}]
    packet = {
        "human_review_required": True,
        "source_classes": {
            "dataset_annotations": "dataset_annotation",
            "deepstream_metropolis": "sensor_inferred",
        },
    }

    smoke = r21.app_consumption_smoke(tile, cards, packet)

    assert smoke["status"] == "FAIL"
    assert any(check["check"] == "frame_card_external_refs_present" and not check["passed"] for check in smoke["checks"])
