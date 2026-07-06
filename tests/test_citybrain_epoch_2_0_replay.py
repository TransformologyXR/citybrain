import json
import unittest

from scripts.citybrain_epoch_2_0_common import OUTPUT_ROOT, REPORT_ROOT, write_all_outputs


class CityBrainEpoch20ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_all_outputs()
        cls.replay = json.loads((REPORT_ROOT / "replay_harness_report.json").read_text(encoding="utf-8"))
        cls.mode_eval = json.loads((REPORT_ROOT / "mode_eval_harness_report.json").read_text(encoding="utf-8"))
        cls.envelope = json.loads((OUTPUT_ROOT / "agent_run_envelope_v1.json").read_text(encoding="utf-8"))

    def test_replay_harness_emits_agent_run_envelope(self):
        self.assertEqual("PASS", self.replay["status"], self.replay)
        self.assertEqual("emitted", self.envelope["status"])
        self.assertEqual("epoch2_replay_harness", self.envelope["component_id"])
        self.assertEqual(0, self.envelope["budget"]["max_llm_calls"])
        self.assertGreaterEqual(len(self.envelope["check_report_refs"]), 1)

    def test_mode_eval_has_active_fixture_slots(self):
        self.assertEqual("PASS", self.mode_eval["status"], self.mode_eval)
        self.assertGreaterEqual(self.mode_eval["active_mode_count"], 12)
        slot_ids = {slot["mode_id"] for slot in self.mode_eval["slots"]}
        for expected in {"ASK", "WATCH", "CHECK", "BRIEF", "DIFF", "RECALL", "SPATIAL", "PERCEPTION", "WORKFLOW", "PLAN", "SCHEDULE", "SIMULATE"}:
            self.assertIn(expected, slot_ids)


if __name__ == "__main__":
    unittest.main()
