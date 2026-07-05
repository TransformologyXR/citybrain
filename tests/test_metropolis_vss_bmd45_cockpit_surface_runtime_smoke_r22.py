from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_main_citybrain_metropolis_vss_bmd45_cockpit_surface_runtime_smoke_r22.py"
spec = importlib.util.spec_from_file_location("r22_runner", SCRIPT_PATH)
r22 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(r22)


def test_render_surface_html_preserves_review_labels_and_external_refs() -> None:
    packet = {
        "boundary_labels": r22.BOUNDARY_LABELS,
        "external_media_refs": [{"external_media_ref": True, "packaged_file": False}],
        "frame_cards": [
            {
                "dataset_annotation_summary": {
                    "annotation_count": 2,
                    "source_class": "dataset_annotation",
                    "unmatched_annotation_count": 1,
                },
                "external_media_ref": {
                    "external_media_ref": True,
                    "file_name": "images_000/example.png",
                    "media_url": "https://example.test/example.png",
                    "sha256": "a" * 64,
                },
                "frame_replay_id": "frame-1",
                "frame_sequence_index": 0,
                "media_packaged": False,
                "review_label": "Review unmatched candidates",
                "sensor_inferred_summary": {
                    "candidate_count": 3,
                    "class_counts": {"car": 2, "person": 1},
                    "source_class": "sensor_inferred",
                    "unmatched_sensor_detection_count": 1,
                },
                "thumbnail_policy": "external_reference_only_no_packaged_media",
            }
        ],
        "packet_id": "packet-1",
        "review_only": True,
        "source_class_legend": r22.SOURCE_CLASSES,
        "source_packet_id": "source-1",
        "surface_title": "BMD-45 Review",
        "tile": {"actions_forbidden": ["no dispatch or action"], "status_label": "Ready"},
    }

    html = r22.render_surface_html(packet)
    check = r22.inspect_rendered_surface(html, expected_card_count=1, expected_external_refs=1)

    assert "dataset_annotation" in html
    assert "sensor_inferred" in html
    assert "model_generated_narrative_not_fact_source" in html
    assert check["result"] == "PASS"
    assert check["media_checks"]["no_embedded_images"]


def test_inspect_rendered_surface_fails_missing_external_refs() -> None:
    html = """
    <html><body data-review-only="true" data-dataset-source="dataset_annotation" data-sensor-source="sensor_inferred"
    data-vss-source="model_generated_narrative_not_fact_source">
    <article class="review-card">human review required candidate review only not production live CCTV no dispatch or action no ticket not an official finding</article>
    </body></html>
    """

    check = r22.inspect_rendered_surface(html, expected_card_count=1, expected_external_refs=1)

    assert check["result"] == "FAIL"
    assert not check["media_checks"]["expected_external_ref_count"]


def test_surface_consumption_smoke_passes_static_surface(tmp_path: Path) -> None:
    html_path = tmp_path / "surface.html"
    html_path.write_text("surface", encoding="utf-8")
    surface_packet = {
        "external_media_refs": [{"external_media_ref": True}],
        "frame_cards": [{"frame_replay_id": f"frame-{index}"} for index in range(8)],
        "review_only": True,
    }
    rendered_check = {
        "boundary_checks": {"required": True},
        "card_count": 8,
        "external_ref_count": 1,
        "media_checks": {"external": True},
        "source_class_checks": {"dataset_annotation": True, "sensor_inferred": True},
    }
    smoke = r22.surface_consumption_smoke(
        surface_packet,
        html_path,
        {"selected_surface_mode": "static_render_fixture"},
        rendered_check,
    )

    assert smoke["result"] == "PASS"
    assert all(check["passed"] for check in smoke["checks"])
