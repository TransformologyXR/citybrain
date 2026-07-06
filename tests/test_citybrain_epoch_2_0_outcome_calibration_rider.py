import json
import unittest

from scripts.citybrain_epoch_2_0_common import OUTPUT_ROOT, REPORT_ROOT, write_all_outputs


class CityBrainEpoch20OutcomeCalibrationRiderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_all_outputs()
        cls.outcome_report = json.loads((REPORT_ROOT / "outcome_ledger_report.json").read_text(encoding="utf-8"))
        cls.calibration = json.loads((OUTPUT_ROOT / "calibration_report_v0.json").read_text(encoding="utf-8"))
        cls.outcomes = [
            json.loads(line)
            for line in (OUTPUT_ROOT / "outcome_records_v0.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_outcome_records_are_derived_fields(self):
        self.assertEqual("PASS", self.outcome_report["status"], self.outcome_report)
        self.assertGreaterEqual(self.outcome_report["disposition_events_found"], 1)
        self.assertGreaterEqual(len(self.outcomes), 1)
        self.assertTrue(all(row["source_class"] == "derived_field" for row in self.outcomes))

    def test_calibration_report_is_descriptive_not_model(self):
        self.assertEqual("derived_field", self.calibration["source_class"])
        self.assertGreaterEqual(self.calibration["sample_size"], 1)
        text = json.dumps(self.calibration).lower()
        for forbidden in ["score adjustment", "prediction", "learned ranker", "model registry release"]:
            self.assertIn(forbidden, text)
        self.assertNotIn('"forecast"', text)


if __name__ == "__main__":
    unittest.main()
