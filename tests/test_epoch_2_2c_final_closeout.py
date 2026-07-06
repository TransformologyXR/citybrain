import json
import unittest

from scripts.run_epoch_2_2c_final_closeout import (
    OUTPUT_ROOT,
    PASS_LIMITED_STATUS,
    REQUIRED_OUTPUTS,
    sha256_file,
    write_all_outputs,
)


class Epoch22cFinalCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.decision = cls.result["decision"]
        cls.label_fuel = cls.result["label_fuel"]
        cls.epoch3 = cls.result["epoch3"]
        cls.ledger = cls.result["ledger_row"]

    def read_json(self, name):
        return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_final_status_passes_with_limitations(self):
        self.assertEqual(PASS_LIMITED_STATUS, self.decision["status"], self.decision)
        self.assertEqual("main", self.decision["branch"])
        self.assertFalse(self.decision["blockers"])
        self.assertFalse(self.decision["failures"])

    def test_all_required_technical_checks_pass(self):
        for name, row in self.decision["required_checks"].items():
            self.assertEqual("PASS", row["status"], name)

    def test_label_fuel_is_evaluated_but_not_model_ready(self):
        self.assertEqual("PASS_WITH_LIMITATIONS_LABEL_FUEL_EVALUATED_NOT_MET", self.label_fuel["status"])
        self.assertEqual("BLOCKED_FOR_EPOCH_3_TRAINED_MODEL_WORK", self.label_fuel["training_grade_disposition_status"])
        self.assertEqual(50, self.label_fuel["threshold"]["terminal_dispositions_required"])
        self.assertEqual(0, self.label_fuel["observed"]["eligible_post_fix_terminal_dispositions"])
        self.assertFalse(self.decision["epoch_3_model_work_allowed"])
        self.assertFalse(self.epoch3["model_work_allowed"])

    def test_limitations_are_enumerated_with_owner_and_next_lane(self):
        self.assertGreaterEqual(len(self.decision["limitations"]), 6)
        for limitation in self.decision["limitations"]:
            self.assertTrue(limitation["owner"])
            self.assertTrue(limitation["next_lane"])
            self.assertTrue(limitation["limitation"])

    def test_corpus_and_source_of_truth_deltas_are_output_local(self):
        corpus = self.read_json("EPOCH_2_2_CORPUS_DELTA.json")
        source = self.read_json("EPOCH_2_2_SOURCE_OF_TRUTH_MATRIX_DELTA.json")
        self.assertEqual("PASS_FOCUSED_EPOCH_2_2_CORPUS_WITH_LIMITATIONS", corpus["status"])
        self.assertGreaterEqual(corpus["newly_sealed_fixture_count"], 16)
        self.assertEqual("output_local_delta_no_frozen_upstream_mutation", corpus["append_mode"])
        self.assertEqual("PASS_WITH_LIMITATIONS", source["status"])
        self.assertEqual("output_local_delta_no_frozen_upstream_mutation", source["append_mode"])

    def test_final_non_claims_remain_false(self):
        for key, value in self.decision["non_claims"].items():
            self.assertFalse(value, key)

    def test_ledger_row_has_required_track0_shape(self):
        self.assertEqual(PASS_LIMITED_STATUS, self.ledger["status"])
        for key in ["component", "proof_refs", "what_it_means", "what_it_does_not_prove", "limitations", "next_lane", "corpus_delta", "source_of_truth_delta", "hash_manifest"]:
            self.assertIn(key, self.ledger)
            self.assertTrue(self.ledger[key], key)

    def test_hash_manifest_matches_outputs(self):
        manifest = self.read_json("HASH_MANIFEST.json")
        self.assertEqual(len(REQUIRED_OUTPUTS) - 1, len(manifest["files"]))
        repo_root = OUTPUT_ROOT.parents[2]
        for row in manifest["files"]:
            path = repo_root / row["path"]
            self.assertTrue(path.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(path))


if __name__ == "__main__":
    unittest.main()
