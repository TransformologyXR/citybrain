import json
import unittest

from scripts.citybrain_epoch_2_0_common import AUDIT_ROOT, audit_no_sealed_drift, write_all_outputs


class CityBrainEpoch20NoSealedDriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_all_outputs()

    def test_no_sealed_ask_or_r7_drift(self):
        report = audit_no_sealed_drift()
        self.assertEqual("PASS", report["status"], report)
        self.assertTrue(report["ask_diff_empty"])
        self.assertTrue(report["r7_diff_empty"])
        audit = json.loads((AUDIT_ROOT / "no_sealed_artifact_drift_audit.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", audit["status"])

    def test_no_official_or_learned_model_claims(self):
        official = json.loads((AUDIT_ROOT / "no_official_action_audit.json").read_text(encoding="utf-8"))
        learned = json.loads((AUDIT_ROOT / "no_learned_model_audit.json").read_text(encoding="utf-8"))
        data = json.loads((AUDIT_ROOT / "no_new_data_dependency_audit.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", official["status"], official)
        self.assertEqual("PASS", learned["status"], learned)
        self.assertEqual("PASS", data["status"], data)


if __name__ == "__main__":
    unittest.main()
