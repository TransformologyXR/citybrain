import json
import unittest

from scripts.run_track7_diff_source_refresh_readiness import (
    CLASSIFICATIONS,
    OUTPUT_ROOT,
    STATUS_PASS_LIMITATIONS,
    build_outputs,
    sha256_file,
)


class Track7DiffSourceRefreshReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "TRACK7_DIFF_SOURCE_REFRESH_DECISION.json").read_text(encoding="utf-8"))
        cls.inventory = json.loads((OUTPUT_ROOT / "SNAPSHOT_INVENTORY.json").read_text(encoding="utf-8"))
        cls.refresh = json.loads((OUTPUT_ROOT / "SOURCE_REFRESH_STATUS.json").read_text(encoding="utf-8"))
        cls.detector = json.loads((OUTPUT_ROOT / "COMPARABLE_SNAPSHOT_DETECTOR.json").read_text(encoding="utf-8"))
        cls.fixture = json.loads((OUTPUT_ROOT / "DESIGNED_CHANGE_FIXTURE.json").read_text(encoding="utf-8"))
        cls.classifier = json.loads((OUTPUT_ROOT / "CHANGE_CLASSIFIER_REPORT.json").read_text(encoding="utf-8"))
        cls.entity_report = json.loads((OUTPUT_ROOT / "ENTITY_LEVEL_DIFF_REPORT.json").read_text(encoding="utf-8"))
        cls.source_report = json.loads((OUTPUT_ROOT / "SOURCE_LEVEL_DIFF_REPORT.json").read_text(encoding="utf-8"))

    def test_decision_passes_with_limitations(self):
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.result["status"])
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.decision["status"])
        self.assertEqual("Track 7", self.decision["track"])
        self.assertEqual([], self.decision["blockers"])
        for key, value in self.decision["contract_check"].items():
            self.assertTrue(value, key)

    def test_snapshot_inventory_covers_four_city_ledgers(self):
        self.assertEqual(4, self.inventory["snapshot_count"])
        self.assertGreater(self.inventory["total_source_count"], 0)
        cities = {row["city"] for row in self.inventory["source_snapshots"]}
        self.assertEqual({"nyc", "london", "chicago", "barcelona"}, cities)
        for snapshot in self.inventory["source_snapshots"]:
            self.assertTrue(snapshot["ledger_exists"])
            self.assertTrue(snapshot["ledger_sha256"])
            self.assertGreater(snapshot["source_count"], 0)
            self.assertTrue(snapshot["sample_sources"])

    def test_source_refresh_status_is_built_without_live_refresh(self):
        self.assertTrue(self.refresh["readiness"]["has_snapshot_inventory"])
        self.assertTrue(self.refresh["readiness"]["has_multi_city_coverage"])
        self.assertTrue(self.refresh["readiness"]["can_prepare_future_snapshot_diff"])
        self.assertTrue(self.refresh["readiness"]["requires_future_real_changed_snapshot"])
        self.assertTrue(self.refresh["city_refresh_status_counts"])
        self.assertTrue(self.refresh["sample_source_rows"])

    def test_comparable_snapshot_detector_contract(self):
        contract = self.detector["detector_contract"]
        self.assertTrue(contract["requires_snapshot_id"])
        self.assertTrue(contract["requires_observed_at"])
        self.assertTrue(contract["requires_stable_entity_or_source_id"])
        self.assertTrue(contract["compares_content_hash"])
        self.assertTrue(contract["compares_refresh_cadence_for_stale"])
        self.assertTrue(contract["does_not_claim_live_current_truth"])
        self.assertTrue(self.detector["designed_fixture_detection"]["classification_contract_pass"])
        self.assertGreaterEqual(self.detector["designed_fixture_detection"]["comparable_source_count"], 1)

    def test_designed_change_fixture_has_expected_snapshots(self):
        self.assertEqual("PASS", self.fixture["status"])
        self.assertIn("baseline_snapshot", self.fixture)
        self.assertIn("target_snapshot", self.fixture)
        self.assertGreaterEqual(len(self.fixture["baseline_snapshot"]["sources"]), 1)
        self.assertGreaterEqual(len(self.fixture["target_snapshot"]["sources"]), 1)
        self.assertGreaterEqual(len(self.fixture["baseline_snapshot"]["entities"]), 1)
        self.assertGreaterEqual(len(self.fixture["target_snapshot"]["entities"]), 1)

    def test_classifier_proves_all_required_classes(self):
        self.assertEqual("PASS", self.classifier["status"])
        self.assertEqual(CLASSIFICATIONS, self.classifier["classification_order"])
        self.assertTrue(self.classifier["expected_counts_match"])
        self.assertEqual({"changed": 2, "expired": 1, "new": 1, "stale": 1, "unchanged": 1}, self.classifier["entity_counts"])
        self.assertEqual({"changed": 1, "expired": 1, "new": 1, "stale": 1, "unchanged": 1}, self.classifier["source_counts"])

    def test_entity_and_source_diff_reports_include_new_changed_expired_stale(self):
        for report in [self.entity_report, self.source_report]:
            self.assertEqual("PASS", report["status"])
            for classification in ["new", "changed", "expired", "stale"]:
                self.assertIn(classification, report["counts"])
                self.assertGreater(report["counts"][classification], 0)
            for row in report["diffs"]:
                self.assertIn(row["classification"], CLASSIFICATIONS)
                self.assertTrue(row["reasons"])
                self.assertIn("baseline_present", row)
                self.assertIn("target_present", row)

    def test_hash_manifest_verifies(self):
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        manifest_paths = {row["path"] for row in manifest["files"]}
        for name in [
            "SNAPSHOT_INVENTORY.json",
            "SOURCE_REFRESH_STATUS.json",
            "COMPARABLE_SNAPSHOT_DETECTOR.json",
            "DESIGNED_CHANGE_FIXTURE.json",
            "CHANGE_CLASSIFIER_REPORT.json",
            "ENTITY_LEVEL_DIFF_REPORT.json",
            "SOURCE_LEVEL_DIFF_REPORT.json",
            "TRACK7_DIFF_SOURCE_REFRESH_DECISION.json",
            "SUMMARY.md",
        ]:
            self.assertIn(name, manifest_paths)
        for row in manifest["files"]:
            target = OUTPUT_ROOT / row["path"]
            self.assertTrue(target.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(target), row)


if __name__ == "__main__":
    unittest.main()
