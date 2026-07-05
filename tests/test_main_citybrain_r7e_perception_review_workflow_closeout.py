import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.run_main_citybrain_r7e_perception_review_workflow_closeout import (
    CAPABILITY_STATEMENT,
    NON_CLAIMS,
    OUTPUT_ROOT,
    contract_check,
    load_decisions,
    package_ledger,
    verify_hash_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainR7EPerceptionReviewWorkflowCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, "scripts\\run_main_citybrain_r7e_perception_review_workflow_closeout.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        cls.decision = json.loads((OUTPUT_ROOT / "R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.decisions = load_decisions()
        cls.check = contract_check(cls.decisions)

    def test_required_closeout_artifacts_exist(self):
        required = [
            "R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_DECISION.json",
            "R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_SUMMARY.md",
            "R7E_R7_PACKAGE_LEDGER.md",
            "R7E_BOUNDARY_AND_NON_CLAIMS.md",
            "R7E_TEST_COMMANDS.md",
            "R7E_LIMITATIONS_AND_NEXT_STEPS.md",
            "R7E_HASH_MANIFEST.json",
            "R7E_COMMIT_AND_PUSH_PROMPT.md",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_final_decision_is_pass_with_limitations(self):
        self.assertEqual(
            "PASS_MAIN_CITYBRAIN_R7_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_WITH_LIMITATIONS",
            self.decision["status"],
        )

    def test_package_ledger_covers_r7_through_r7d(self):
        ledger = package_ledger(self.decisions)
        self.assertEqual(["R7", "R7A", "R7B", "R7C", "R7D"], [item["package"] for item in ledger])
        for item in ledger:
            self.assertTrue(item["status"].startswith("PASS"), item)
            self.assertTrue(item["summary"])

    def test_capability_statement_is_careful_and_present(self):
        summary = (OUTPUT_ROOT / "R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_SUMMARY.md").read_text(encoding="utf-8")
        self.assertIn(CAPABILITY_STATEMENT, summary)
        self.assertIn("local/replay", summary)
        self.assertIn("review-only", summary)

    def test_non_claims_are_explicit(self):
        boundary = (OUTPUT_ROOT / "R7E_BOUNDARY_AND_NON_CLAIMS.md").read_text(encoding="utf-8")
        for claim in NON_CLAIMS:
            self.assertIn(claim, boundary)

    def test_boundary_invariants_are_preserved(self):
        self.assertTrue(all(self.check.values()), self.check)
        self.assertTrue(self.decision["contract_check"]["candidate_only_preserved"])
        self.assertTrue(self.decision["contract_check"]["review_required_preserved"])
        self.assertTrue(self.decision["contract_check"]["event_replay_materialization_query_path_closed"])
        self.assertTrue(self.decision["contract_check"]["webui_kit_one_truth_parity_closed"])

    def test_result_counts_close_r7d_parity(self):
        counts = self.decision["result_counts"]
        self.assertEqual(5, counts["packages_closed"])
        self.assertEqual(8, counts["webui_smoke_items"])
        self.assertEqual(8, counts["kit_smoke_items"])
        self.assertEqual(8, counts["parity_pairs_checked"])
        self.assertEqual(0, counts["parity_failures"])

    def test_commit_prompt_is_source_control_only(self):
        prompt = (OUTPUT_ROOT / "R7E_COMMIT_AND_PUSH_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("SOURCE-CONTROL ONLY", prompt)
        self.assertIn("Do not:", prompt)
        self.assertIn("stage unrelated dirty files", prompt)
        self.assertIn("git diff -- packages/ask_v11", prompt)

    def test_no_live_or_official_behavior_is_added_to_closeout_source(self):
        source = (ROOT / "scripts" / "run_main_citybrain_r7e_perception_review_workflow_closeout.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("chat.completions", source)
        self.assertNotIn("fetch(", source)

    def test_ask_runtime_scoped_diff_empty(self):
        result = subprocess.run(
            [
                "git",
                "diff",
                "--",
                "packages/ask_v11",
                "packages/contracts",
                "scripts/run_ask_v11_sealed_eval.py",
                "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertEqual("", result.stdout)

    def test_hash_manifest_verifies_and_includes_chain_artifacts(self):
        manifest = json.loads((OUTPUT_ROOT / "R7E_HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        self.assertEqual(0, manifest["missing_count"])
        self.assertEqual(0, manifest["mismatch_count"])
        paths = {item["path"] for item in manifest["items"]}
        self.assertIn("outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_WEBUI_KIT_EVENT_STATE_SMOKE_DECISION.json", paths)
        self.assertIn("scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py", paths)
        self.assertEqual("PASS", verify_hash_manifest()["status"])


if __name__ == "__main__":
    unittest.main()
