import json
import shutil
import unittest
from pathlib import Path

from scripts.run_main_citybrain_r7_kit_handoff_hardening_r1 import (
    CLOSEOUT_ROOT,
    FINAL_ROOT,
    PASS_CLOSEOUT,
    PASS_FINAL,
    PASS_R1,
    PASS_R2,
    PREFLIGHT_ROOT,
    R1_ROOT,
    R2_ROOT,
    REQUIRED_PREFLIGHT,
    verify_hash_manifest,
    verify_preflight,
    run_all,
    write_hash_manifest,
    write_json,
    write_text,
)


ROOT = Path(__file__).resolve().parents[1]


def write_test_preflight_bundle():
    if PREFLIGHT_ROOT.exists():
        shutil.rmtree(PREFLIGHT_ROOT)
    PREFLIGHT_ROOT.mkdir(parents=True, exist_ok=True)
    decision = {
        "schema_version": "main-citybrain-r7-kit-handoff-hardening-preflight.test-fixture.v1",
        "status": "PASS_MAIN_CITYBRAIN_R7_KIT_HANDOFF_HARDENING_PREFLIGHT_WITH_LIMITATIONS",
        "final_decision": "PASS_MAIN_CITYBRAIN_R7_KIT_HANDOFF_HARDENING_PREFLIGHT_WITH_LIMITATIONS",
        "selected_scope": {
            "ask_runtime_changed": False,
            "runtime_behavior_changed": False,
        },
        "fixture_scope": "test_only_clean_worktree_preflight_bundle",
    }
    write_json(PREFLIGHT_ROOT / "R7_KIT_HANDOFF_HARDENING_PREFLIGHT_DECISION.json", decision)
    for name in REQUIRED_PREFLIGHT:
        path = PREFLIGHT_ROOT / name
        if path.name.endswith(".json") or path.exists():
            continue
        write_text(
            path,
            f"# {path.stem}\n\nClean-worktree test fixture for R7 Kit handoff preflight reproducibility.",
        )
    write_hash_manifest(
        PREFLIGHT_ROOT,
        "R7_KIT_HANDOFF_PREFLIGHT_HASH_MANIFEST.json",
        "main-citybrain-r7-kit-handoff-preflight.test-hash-manifest.v1",
    )


class MainCityBrainR7KitHandoffHardeningR1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for root in [R1_ROOT, R2_ROOT, CLOSEOUT_ROOT, FINAL_ROOT]:
            if root.exists():
                shutil.rmtree(root)
        write_test_preflight_bundle()
        cls.result = run_all({"targeted_r1": "TEST_SETUP", "full_discovery": "TEST_SETUP", "test_count": 0})

    def test_b0_preflight_required_artifacts_and_hashes_verify(self):
        preflight = verify_preflight()
        self.assertEqual("PASS", preflight["status"])
        self.assertEqual([], preflight["required_missing"])
        self.assertEqual(len(REQUIRED_PREFLIGHT), 10)
        self.assertEqual("PASS", preflight["hash_manifest"]["status"])
        self.assertFalse(preflight["ask_runtime_changed"])
        self.assertFalse(preflight["runtime_behavior_changed"])

    def test_r1_decision_and_artifacts_exist(self):
        decision = json.loads((R1_ROOT / "R7_KIT_HANDOFF_HARDENING_R1_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(PASS_R1, decision["status"])
        required = [
            "R7_KIT_HANDOFF_HARDENED_FIXTURES.json",
            "R7_KIT_WEBUI_PARITY_RESULTS.json",
            "R7_KIT_HANDOFF_PACKET_CONTRACT_APPLIED.json",
            "R7_KIT_MARKER_LAYER_EXPORT.json",
            "R7_KIT_MARKER_LAYER.usda",
            "R7_KIT_HANDOFF_BOUNDARY_AUDIT.json",
            "R7_KIT_HANDOFF_R1_TEST_LOG.md",
            "R7_KIT_HANDOFF_R1_LIMITATIONS.md",
            "R7_KIT_HANDOFF_R1_HASH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((R1_ROOT / name).exists(), name)

    def test_webui_kit_parity_and_one_truth_fields(self):
        fixture = json.loads((R1_ROOT / "R7_KIT_HANDOFF_HARDENED_FIXTURES.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", fixture["status"])
        self.assertEqual(8, fixture["webui_items"])
        self.assertEqual(8, fixture["kit_items"])
        self.assertEqual(8, fixture["parity_pairs"])
        self.assertEqual(0, fixture["parity_failures"])
        for item in fixture["items"]:
            self.assertEqual("PASS", item["parity_status"])
            self.assertTrue(item["candidate_only"])
            self.assertTrue(item["review_required"])
            self.assertEqual("not_official", item["official_status"])
            self.assertEqual("not_executed", item["execution_status"])
            self.assertTrue(item["webui_packet_hash_present"])
            self.assertTrue(item["kit_packet_hash_present"])
            self.assertEqual(64, len(item["contract_hash"]))
            self.assertGreaterEqual(len(item["limitation_refs"]), 1)
            self.assertGreaterEqual(len(item["trace_refs"]), 1)

    def test_negative_unknown_event_and_action_message_rejection(self):
        unknown = json.loads((R1_ROOT / "R7_KIT_HANDOFF_UNKNOWN_EVENT_NEGATIVE_TEST.json").read_text(encoding="utf-8"))
        action = json.loads((R1_ROOT / "R7_KIT_HANDOFF_ACTION_MESSAGE_REJECTION_TEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", unknown["status"])
        self.assertFalse(unknown["found"])
        self.assertFalse(unknown["fallback_to_live_lookup"])
        self.assertFalse(unknown["kit_control_attempted"])
        self.assertEqual("PASS", action["status"])
        self.assertFalse(action["accepted"])
        self.assertEqual("not_executed", action["execution_status_after_rejection"])
        self.assertFalse(action["official_submission_performed"])
        self.assertFalse(action["kit_live_control_attempted"])

    def test_usda_marker_layer_is_metadata_only(self):
        marker_export = json.loads((R1_ROOT / "R7_KIT_MARKER_LAYER_EXPORT.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", marker_export["status"])
        self.assertEqual(8, marker_export["marker_count"])
        for marker in marker_export["markers"]:
            self.assertTrue(marker["marker_only"])
            self.assertTrue(marker["local_replay_only"])
            self.assertFalse(marker["live_kit_control"])
            self.assertFalse(marker["full_citywide_twin_claim"])
            self.assertFalse(marker["production_omniverse_integration"])
            self.assertEqual("not_executed", marker["execution_status"])
        usda = (R1_ROOT / "R7_KIT_MARKER_LAYER.usda").read_text(encoding="utf-8")
        self.assertIn("local_replay_marker_metadata_only", usda)
        self.assertEqual(8, usda.count("bool marker_only = true"))
        self.assertIn("bool live_kit_control = false", usda)
        self.assertIn("bool full_citywide_twin_claim = false", usda)

    def test_boundaries_preserved(self):
        boundary = json.loads((R1_ROOT / "R7_KIT_HANDOFF_BOUNDARY_AUDIT.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", boundary["status"])
        self.assertTrue(boundary["local_replay_only"])
        self.assertTrue(boundary["no_kit_live_control"])
        self.assertTrue(boundary["no_full_citywide_twin_claim"])
        self.assertTrue(boundary["candidate_only_preserved"])
        self.assertTrue(boundary["review_required_preserved"])
        self.assertTrue(boundary["not_official_preserved"])
        self.assertTrue(boundary["draft_not_submitted_preserved"])
        self.assertTrue(boundary["not_executed_preserved"])
        self.assertFalse(boundary["ask_runtime_changed"])
        self.assertFalse(boundary["r7_runtime_behavior_changed"])

    def test_r2_closeout_and_final_status_created(self):
        r2 = json.loads((R2_ROOT / "R7_KIT_MARKER_PACKET_SMOKE_R2_DECISION.json").read_text(encoding="utf-8"))
        closeout = json.loads((CLOSEOUT_ROOT / "R7_KIT_HANDOFF_HARDENING_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        final = json.loads((FINAL_ROOT / "R7_KIT_HANDOFF_HARDENING_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(PASS_R2, r2["status"])
        self.assertEqual(PASS_CLOSEOUT, closeout["status"])
        self.assertEqual(PASS_FINAL, final["status"])
        self.assertIn("B5_KIT_HANDOFF_HARDENING_FINAL_PUBLISHED_STATUS", final["completed_through"])

    def test_hash_manifests_verify(self):
        manifests = [
            (R1_ROOT, "R7_KIT_HANDOFF_R1_HASH_MANIFEST.json"),
            (R2_ROOT, "R7_KIT_MARKER_PACKET_SMOKE_R2_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "R7_KIT_HANDOFF_HARDENING_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "R7_KIT_HANDOFF_HARDENING_FINAL_STATUS_HASH_MANIFEST.json"),
        ]
        for root, manifest in manifests:
            report = verify_hash_manifest(root, manifest)
            self.assertEqual("PASS", report["status"], f"{root / manifest}: {report}")
            self.assertEqual(report["declared"], report["verified"])


if __name__ == "__main__":
    unittest.main()
