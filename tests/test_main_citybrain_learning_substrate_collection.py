import json
import unittest

from scripts.run_main_citybrain_learning_substrate_collection import (
    DECISION_STATUS,
    FULL_VALIDATION_ROOT,
    LOOP_SEEDS,
    NO_BUILD_FORBIDDEN_NAMES,
    OUTPUT_ROOT,
    write_all_outputs,
)


class MainCityBrainLearningSubstrateCollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = write_all_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "LEARNING_SUBSTRATE_COLLECTION_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.inventory = json.loads((OUTPUT_ROOT / "LEARNING_LOOP_SEED_INVENTORY.json").read_text(encoding="utf-8"))
        cls.rules = json.loads((OUTPUT_ROOT / "DOC07_RULE_COMPLIANCE_SCAN.json").read_text(encoding="utf-8"))
        cls.corpus = json.loads((OUTPUT_ROOT / "LEARNING_REGRESSION_CORPUS_SEED_PLAN.json").read_text(encoding="utf-8"))

    def test_doc07_captured(self):
        self.assertTrue((OUTPUT_ROOT / "07_CITYBRAIN_LEARNING_AND_PREDICTIVE_INTELLIGENCE.md").exists())
        self.assertEqual("PASS", self.reports["doc"]["status"])
        self.assertFalse(self.reports["doc"]["modifies_sealed_contracts"])
        self.assertTrue(self.reports["doc"]["sha256"])

    def test_all_five_loop_sections_exist(self):
        self.assertEqual(set(LOOP_SEEDS), set(self.inventory["loops"]))
        for loop, item in self.inventory["loops"].items():
            self.assertTrue(item["seed_available"], loop)
            self.assertIn(item["score"], {"M0_seeded", "M1_partial", "M1_ready_for_contract", "M1_partial", "blocked"})

    def test_no_learning_runtime_was_built(self):
        self.assertEqual(DECISION_STATUS, self.decision["status"])
        self.assertTrue(self.decision["no_learning_runtime_built"])
        self.assertTrue(self.decision["no_model_trained_evaluated_released"])
        self.assertTrue(self.decision["no_learned_output_claims_or_acts"])
        self.assertTrue(self.decision["no_authority_review_claim_state_changed"])
        for forbidden in NO_BUILD_FORBIDDEN_NAMES:
            self.assertIsInstance(forbidden, str)

    def test_required_reports_exist(self):
        required = [
            "DOC07_SOURCE_CAPTURE.md",
            "DOC07_SOURCE_CAPTURE.json",
            "LEARNING_LOOP_SEED_INVENTORY.md",
            "LEARNING_LOOP_SEED_INVENTORY.json",
            "DOC07_RULE_COMPLIANCE_SCAN.md",
            "DOC07_RULE_COMPLIANCE_SCAN.json",
            "LEARNING_REGRESSION_CORPUS_SEED_PLAN.md",
            "LEARNING_REGRESSION_CORPUS_SEED_PLAN.json",
            "MODEL_ACCEPTANCE_READINESS_REPORT.md",
            "MODEL_ACCEPTANCE_READINESS_REPORT.json",
            "OPERATOR_DATA_GOVERNANCE_READINESS.md",
            "OPERATOR_DATA_GOVERNANCE_READINESS.json",
            "UNCERTAINTY_CONTRACT_DELTA_READINESS.md",
            "UNCERTAINTY_CONTRACT_DELTA_READINESS.json",
            "LEARNING_SUBSTRATE_READINESS_SCORECARD.md",
            "LEARNING_SUBSTRATE_READINESS_SCORECARD.json",
            "LEARNING_SUBSTRATE_COLLECTION_HASH_MANIFEST.json",
            "LEARNING_SUBSTRATE_COLLECTION_CLOSEOUT_DECISION.json",
            "LEARNING_SUBSTRATE_COLLECTION_CLOSEOUT_SUMMARY.md",
            "LEARNING_SUBSTRATE_COLLECTION_LIMITATIONS.md",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_regression_corpus_seed_plan_has_negative_fixtures(self):
        self.assertGreaterEqual(len(self.corpus["candidates"]), 10)
        negative = [item for item in self.corpus["candidates"] if item["positive_or_negative"] == "negative"]
        self.assertGreaterEqual(len(negative), 4)

    def test_pointer_created_when_full_validation_root_exists(self):
        self.assertTrue((FULL_VALIDATION_ROOT / "LEARNING_SUBSTRATE_ADDENDUM_POINTER.md").exists())


if __name__ == "__main__":
    unittest.main()
