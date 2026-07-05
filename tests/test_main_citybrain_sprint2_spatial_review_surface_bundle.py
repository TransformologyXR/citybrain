from __future__ import annotations

import json
import unittest
from pathlib import Path

from packages.event_fabric_r0_1_validator import validator as r0_1_validator
from scripts import run_main_citybrain_sprint2_spatial_review_surface_bundle as runner


class Sprint2SpatialReviewSurfaceBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = runner.write_bundle()
        cls.closeout = runner.write_closeout(cls.bundle)
        runner.write_final(cls.bundle, cls.closeout)

    def test_r0_1_contract_gate_passes(self) -> None:
        gate = runner.assert_r0_1_ready()
        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["active_contract_commit"], "5ba2dc1")
        self.assertEqual(r0_1_validator.validate_bundle()["status"], "PASS")

    def test_webui_query_packets_pass_shared_validator(self) -> None:
        fixture = json.loads((runner.BUNDLE_ROOT / "SPATIAL_REVIEW_WEBUI_FIXTURE.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(fixture["webui_items"], 8)
        for item in fixture["items"]:
            result = r0_1_validator.validate_packet("QueryResultPacket", item["query_packet"])
            self.assertEqual(result["status"], "PASS", result)

    def test_kit_overlay_packets_pass_shared_validator(self) -> None:
        export = json.loads((runner.BUNDLE_ROOT / "SPATIAL_REVIEW_KIT_MARKER_EXPORT.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(export["kit_markers"], 8)
        for item in export["markers"]:
            result = r0_1_validator.validate_packet("OverlayPacket", item["overlay_packet"])
            self.assertEqual(result["status"], "PASS", result)

    def test_shared_validator_negative_fixtures_still_reject(self) -> None:
        invalid = r0_1_validator.validate_fixture_group(r0_1_validator.invalid_fixtures(), "FAIL")
        rejected = {row["fixture"]: row for row in invalid["rows"]}
        self.assertEqual(rejected["invalid_overlay_live_kit_control"]["status"], "FAIL")
        self.assertEqual(rejected["invalid_raw_query_as_authority"]["status"], "FAIL")

    def test_webui_and_kit_preserve_one_truth_refs(self) -> None:
        parity = json.loads((runner.BUNDLE_ROOT / "SPATIAL_REVIEW_ONE_TRUTH_PARITY.json").read_text(encoding="utf-8"))
        self.assertEqual(parity["status"], "PASS")
        self.assertEqual(parity["parity_failures"], 0)
        self.assertEqual(parity["webui_items"], parity["kit_items"])

    def test_boundary_audit_preserves_local_replay_non_claims(self) -> None:
        audit = json.loads((runner.BUNDLE_ROOT / "SPATIAL_REVIEW_BOUNDARY_AUDIT.json").read_text(encoding="utf-8"))
        self.assertEqual(audit["status"], "PASS")
        checks = audit["checks"]
        self.assertTrue(checks["local_replay_only"])
        self.assertTrue(checks["packet_truth_only"])
        self.assertTrue(checks["marker_metadata_only"])
        self.assertTrue(checks["no_live_kit_control"])
        self.assertTrue(checks["no_full_citywide_twin_claim"])
        self.assertTrue(checks["not_executed_preserved"])

    def test_usda_layer_is_marker_metadata_only(self) -> None:
        usda = (runner.BUNDLE_ROOT / "SPATIAL_REVIEW_KIT_MARKER_LAYER.usda").read_text(encoding="utf-8")
        self.assertIn("citybrain_marker_metadata_only = true", usda)
        self.assertIn("citybrain_live_kit_control = false", usda)
        self.assertIn("citybrain_full_citywide_twin_claim = false", usda)
        self.assertNotIn("dispatch", usda.lower())
        self.assertNotIn("control_executed", usda.lower())

    def test_hash_manifests_exist_and_verify(self) -> None:
        for root, name in [
            (runner.BUNDLE_ROOT, "SPATIAL_REVIEW_HASH_MANIFEST.json"),
            (runner.CLOSEOUT_ROOT, "HASH_MANIFEST.json"),
            (runner.FINAL_ROOT, "HASH_MANIFEST.json"),
        ]:
            manifest = json.loads((root / name).read_text(encoding="utf-8"))
            self.assertGreater(manifest["count"], 0)
            for item in manifest["files"]:
                path = root / item["path"]
                self.assertTrue(path.exists(), path)
                self.assertEqual(runner.sha256_file(path), item["sha256"])


if __name__ == "__main__":
    unittest.main()
