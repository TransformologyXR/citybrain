import json
import unittest
from pathlib import Path

from scripts.run_main_citybrain_epoch1_closedown_certified_baseline import (
    OUTPUT_ROOT,
    PASS_WITH_LIMITATIONS,
    REQUIRED_OUTPUTS,
    TARGET_REF,
    verify_local_hash_manifest,
    write_all_outputs,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainEpoch1ClosedownCertifiedBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = write_all_outputs()
        cls.final = json.loads((OUTPUT_ROOT / "EPOCH1_CLOSEDOWN_FINAL_DECISION.json").read_text(encoding="utf-8"))
        cls.ledger = json.loads((OUTPUT_ROOT / "EPOCH1_MASTER_LEDGER_ROWS.json").read_text(encoding="utf-8"))
        cls.waivers = json.loads((OUTPUT_ROOT / "EPOCH1_WAIVER_REGISTER_RECONCILIATION.json").read_text(encoding="utf-8"))
        cls.corpus = json.loads((OUTPUT_ROOT / "EPOCH1_CORPUS_AND_MANIFEST_RECONCILIATION.json").read_text(encoding="utf-8"))
        cls.canonical = json.loads((OUTPUT_ROOT / "EPOCH1_CANONICAL_STATE_RECONCILIATION.json").read_text(encoding="utf-8"))
        cls.track0 = json.loads((OUTPUT_ROOT / "EPOCH1_TRACK0_DEBT_RECONCILIATION.json").read_text(encoding="utf-8"))
        cls.freshness = json.loads((OUTPUT_ROOT / "EPOCH1_DATA_FRESHNESS_RECONCILIATION.json").read_text(encoding="utf-8"))
        cls.parked = json.loads((OUTPUT_ROOT / "EPOCH1_PARKED_REGISTER_REVALIDATION.json").read_text(encoding="utf-8"))
        cls.certified = json.loads((OUTPUT_ROOT / "EPOCH1_CERTIFIED_STATE_UPDATE.json").read_text(encoding="utf-8"))
        cls.doc07 = json.loads((OUTPUT_ROOT / "EPOCH1_DOC07_OPEN_QUESTION_ASSIGNMENTS.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_target_selected_and_ledger_rows_exist(self):
        self.assertEqual(TARGET_REF, self.final["target"]["chosen_target"])
        self.assertFalse(self.final["target"]["canonical_main_not_closed"])
        self.assertTrue(self.final["target"]["main_contains_push7"])
        self.assertTrue(self.final["target"]["validation_branch_exists"])
        self.assertGreaterEqual(len(self.ledger), 27)
        push_rows = [row for row in self.ledger if isinstance(row["push"], int) and 2 <= row["push"] <= 7]
        self.assertEqual(24, len(push_rows))
        self.assertEqual([], self.final["ledger"]["missing_rows"])

    def test_ask_waiver_closed_or_carried_with_proof(self):
        self.assertIn(self.waivers["ask_contradiction_waiver_status"], {"closed", "carried"})
        if self.waivers["ask_contradiction_waiver_status"] == "closed":
            self.assertGreaterEqual(len(self.waivers["ask_contradiction_waiver_proof"]), 3)
        else:
            carried = [item for item in self.waivers["waivers"] if item["waiver_id"] == "ASK_REAL_CORPUS_CONTRADICTION_WAIVER"]
            self.assertEqual("CARRIED", carried[0]["status"])
            self.assertIn("Epoch 2.0", carried[0]["deadline"])

    def test_corpus_manifest_canonical_track0_and_freshness_exist(self):
        self.assertEqual("PASS_WITH_LIMITATIONS", self.corpus["status"])
        self.assertGreater(self.corpus["hash_manifests_checked"], 0)
        self.assertEqual([], self.corpus["hash_mismatches"])
        self.assertTrue(self.canonical["source_of_truth_matrix_current"])
        self.assertGreaterEqual(self.canonical["frozen_shapes_indexed"], 25)
        self.assertGreaterEqual(self.track0["debt_carried"], 1)
        self.assertTrue(self.freshness["source_refresh_ledger_current"])
        self.assertTrue(self.freshness["maturity_dashboard_ready_input"])

    def test_parked_certified_state_and_doc07(self):
        self.assertGreaterEqual(self.parked["items_revalidated"], 14)
        self.assertEqual(self.parked["items_revalidated"], self.parked["still_parked"])
        self.assertGreaterEqual(self.certified["mode_agent_rows"], 23)
        self.assertTrue(self.certified["Epoch2_baseline_ready"])
        self.assertTrue(self.certified["no_m4_plus_overclaim"])
        self.assertEqual(6, len(self.doc07["assignments"]))
        self.assertTrue(self.doc07["Doc07_future_track_only"])
        self.assertTrue(self.doc07["no_learning_runtime_authorized"])

    def test_contract_boundaries_and_hash_manifest(self):
        self.assertEqual(PASS_WITH_LIMITATIONS, self.final["status"])
        contract = self.final["contract_check"]
        self.assertTrue(contract["formal closedown gate only"])
        self.assertTrue(contract["no feature implementation"])
        self.assertTrue(contract["no Doc07 learning runtime"])
        self.assertTrue(contract["no sealed ASK drift"])
        self.assertTrue(contract["no protected R7 drift"])
        self.assertTrue(contract["no live/API/URL/LLM"])
        self.assertTrue(contract["no official/dispatch/control/legal/certified/autonomy claim"])
        self.assertTrue(contract["no secrets/raw/media/caches committed"])
        hash_report = verify_local_hash_manifest()
        self.assertEqual("PASS", hash_report["status"], hash_report)


if __name__ == "__main__":
    unittest.main()
