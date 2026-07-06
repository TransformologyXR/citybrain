import json
import unittest

from scripts.run_epoch_2_2b_lane_c_briefing_g8 import (
    BRIEF_REQUIRED_FIELDS,
    FORBIDDEN_WRITER_ROLES,
    OUTPUT_ROOT,
    STATUS_PASS_LIMITATIONS,
    build_outputs,
    sha256_file,
)


class Epoch22bLaneCBriefingG8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "BRIEFING_AGENT_V2_DECISION.json").read_text(encoding="utf-8"))
        cls.fixtures = json.loads((OUTPUT_ROOT / "BRIEF_FIXTURES.json").read_text(encoding="utf-8"))
        cls.live_eval = json.loads((OUTPUT_ROOT / "BRIEF_WRITER_V2_LIVE_EVAL_REPORT.json").read_text(encoding="utf-8"))
        cls.negative = json.loads((OUTPUT_ROOT / "BRIEFING_NEGATIVE_TEST_REPORT.json").read_text(encoding="utf-8"))

    def test_prerequisite_and_decision_pass_with_limitations(self):
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.result["status"])
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.decision["status"])
        self.assertEqual("main", self.decision["branch"])
        self.assertEqual("PASS", self.decision["prerequisite_gate"]["status"])
        self.assertEqual("PASS", self.decision["dependency_status"]["push_2_2a_integration"])
        self.assertEqual("ready_for_2_2b", self.decision["dependency_status"]["brief_writer_v2_readiness"])
        self.assertTrue(self.decision["contract_check"]["epoch_2_2_not_closed"])

    def test_three_briefs_render_through_v2_path_with_required_fields(self):
        positives = self.fixtures["positive_v2_render_fixtures"]
        self.assertEqual(3, len(positives))
        self.assertEqual(3, self.live_eval["metrics"]["rendered_v2_path_count"])
        for row in positives:
            self.assertFalse(row["fallback_used"])
            self.assertTrue(row["schema_validation"]["valid"])
            self.assertTrue(row["check_gate"]["passed"])
            self.assertTrue(row["llm_output_operator_visible"])
            brief = row["rendered_brief"]
            for field in BRIEF_REQUIRED_FIELDS:
                self.assertIn(field, brief)
            self.assertEqual("brief_writer_v2", brief["seat_id"])
            self.assertTrue(brief["evidence_refs"])
            self.assertTrue(brief["limitation_refs"])
            self.assertTrue(brief["cannot_claim"])
            self.assertTrue(brief["check_report_ref"])
            self.assertTrue(brief["authority_envelope_ref"])
            self.assertTrue(brief["no_official_action_boundary"]["not_official"])
            self.assertFalse(brief["no_official_action_boundary"]["official_action_created"])

    def test_writer_seat_boundaries(self):
        self.assertEqual("brief_writer_v2", self.live_eval["seat_id"])
        self.assertEqual("writer", self.live_eval["allowed_role"])
        self.assertEqual(FORBIDDEN_WRITER_ROLES, self.live_eval["forbidden_roles"])
        controls = self.live_eval["controls"]
        self.assertTrue(controls["deterministic_evidence_assembly_before_writer"])
        self.assertTrue(controls["registered_output_schema_validation"])
        self.assertTrue(controls["CHECK_before_operator_visibility"])
        self.assertTrue(controls["fallback_if_writer_or_model_blocked"])
        self.assertTrue(controls["brief_writer_v2_not_sealed_ASK_G8"])
        self.assertTrue(controls["briefing_agent_not_wired_into_ASK_internals"])
        self.assertTrue(controls["writer_does_not_source_facts_compute_CHECK_grant_authority_or_mutate_packets"])
        boundary = self.fixtures["boundary"]
        self.assertFalse(boundary["sealed_ASK_G1_G8_touched"])
        self.assertFalse(boundary["briefing_agent_wired_into_ASK_internals"])

    def test_no_llm_output_operator_visible_without_schema_and_check(self):
        metrics = self.live_eval["metrics"]
        self.assertEqual(0, metrics["operator_visible_without_schema_and_CHECK"])
        self.assertEqual(0, metrics["unsupported_facts_operator_visible"])
        for row in self.fixtures["positive_v2_render_fixtures"]:
            self.assertTrue(row["schema_validation"]["valid"])
            self.assertTrue(row["check_gate"]["passed"])
            self.assertTrue(row["llm_output_operator_visible"])

    def test_negative_cases_fail_or_fallback_correctly(self):
        self.assertEqual("PASS", self.negative["status"])
        by_type = {row["fixture_type"]: row for row in self.negative["tests"]}
        self.assertTrue(by_type["negative_unsupported_fact"]["passed"])
        self.assertIn("unsupported_statement_without_evidence_ref", by_type["negative_unsupported_fact"]["check_fail_reasons"])
        self.assertFalse(by_type["negative_unsupported_fact"]["llm_output_operator_visible"])

        self.assertTrue(by_type["negative_omits_cannot_claim"]["passed"])
        self.assertEqual("FAIL_SCHEMA", by_type["negative_omits_cannot_claim"]["schema_status"])
        self.assertFalse(by_type["negative_omits_cannot_claim"]["llm_output_operator_visible"])

        self.assertTrue(by_type["negative_official_language_without_authority"]["passed"])
        self.assertIn(
            "official_or_legal_language_without_authority",
            by_type["negative_official_language_without_authority"]["check_fail_reasons"],
        )
        self.assertFalse(by_type["negative_official_language_without_authority"]["llm_output_operator_visible"])

        self.assertTrue(by_type["negative_model_unavailable"]["passed"])
        self.assertTrue(by_type["negative_model_unavailable"]["fallback_used"])
        self.assertTrue(by_type["negative_model_unavailable"]["operator_visible_after_safe_fallback"])

    def test_no_official_action_or_dynamic_learning_claim(self):
        checks = self.decision["contract_check"]
        self.assertTrue(checks["no_official_action_ticket_dispatch_control_enforcement"])
        self.assertTrue(checks["local_replay_review_only"])
        self.assertTrue(checks["no_learned_ranking_prediction_trained_model_or_dynamic_investigation"])
        self.assertTrue(checks["sealed_ASK_G1_G8_untouched"])
        for row in self.fixtures["positive_v2_render_fixtures"]:
            boundary = row["rendered_brief"]["no_official_action_boundary"]
            self.assertFalse(boundary["official_action_created"])
            self.assertFalse(boundary["ticket_created"])
            self.assertFalse(boundary["dispatch_control_enforcement"])
            self.assertFalse(boundary["legal_or_certified_finding"])

    def test_hash_manifest_verifies(self):
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        manifest_paths = {row["path"] for row in manifest["files"]}
        for name in [
            "BRIEFING_AGENT_V2_DECISION.json",
            "BRIEFING_AGENT_V2_REPORT.md",
            "BRIEF_WRITER_V2_LIVE_EVAL_REPORT.json",
            "BRIEF_FIXTURES.json",
            "BRIEFING_NEGATIVE_TEST_REPORT.json",
        ]:
            self.assertIn(name, manifest_paths)
        for row in manifest["files"]:
            target = OUTPUT_ROOT / row["path"]
            self.assertTrue(target.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(target), row)


if __name__ == "__main__":
    unittest.main()
