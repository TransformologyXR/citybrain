from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_main_citybrain_metropolis_vss_narration_evidence_join_r8 import (  # noqa: E402
    FAIL_STATUS,
    PASS_STATUS,
    R2_PACKAGE_NAME,
    R2_ROOT,
    R7_PACKAGE_NAME,
    R7_ROOT,
    R7_PASS_STATUS,
    build_evidence_bundle,
    build_join,
    build_review_packet,
    claim_boundary_audit,
    decide_status,
    input_lineage_summary,
    load_inputs,
    no_action_audit,
    prose_conflict_audit,
    source_class_audit,
    stable_json_hash,
    validate_json_outputs,
    validate_zip_package,
)


class MetropolisVssNarrationEvidenceJoinR8Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.r2_package = R2_ROOT / R2_PACKAGE_NAME
        self.r7_package = R7_ROOT / R7_PACKAGE_NAME
        self.inputs = load_inputs(R2_ROOT, R7_ROOT)
        self.r2_validation = validate_zip_package(self.r2_package)
        self.r7_validation = validate_zip_package(self.r7_package)
        if self.r2_validation["status"] != "PASS" or self.r7_validation["status"] != "PASS":
            self.skipTest("requires generated Metropolis/VSS R2 and R7 output packages")
        self.lineage = input_lineage_summary(self.inputs, self.r2_validation, self.r7_validation)
        self.join = build_join(self.inputs, self.lineage)
        self.bundle = build_evidence_bundle(self.inputs, self.lineage, self.join)
        self.review_packet = build_review_packet(self.inputs, self.lineage, self.bundle)

    def test_upstream_packages_validate(self) -> None:
        self.assertEqual(self.r2_validation["status"], "PASS")
        self.assertEqual(self.r7_validation["status"], "PASS")
        self.assertEqual(self.inputs["r7_decision"]["status"], R7_PASS_STATUS)
        self.assertGreaterEqual(self.r7_validation["jsonl_record_counts"].get("VSS_NARRATION_SIDECAR_R7.jsonl", 0), 1)

    def test_candidate_event_hash_is_preserved(self) -> None:
        self.assertEqual(self.lineage["candidate_event_id"], "metropolis-vss-r2-event-001")
        self.assertEqual(stable_json_hash(self.inputs["candidate_event"]), self.lineage["candidate_event_original_hash"])
        self.assertTrue(self.lineage["candidate_event_hash_matches_r7_lineage"])
        self.assertFalse(self.lineage["candidate_event_mutated"])

    def test_join_keeps_vss_sidecar_out_of_sensor_facts(self) -> None:
        self.assertEqual(self.join["sensor_inferred_source"]["source_class"], "sensor_inferred")
        self.assertGreaterEqual(len(self.join["model_generated_narrative_sources"]), 1)
        for sidecar in self.join["model_generated_narrative_sources"]:
            self.assertEqual(sidecar["source_class"], "model_generated_narrative")
            self.assertFalse(sidecar["vss_is_fact_source"])
            self.assertFalse(sidecar["candidate_event_mutated"])
            self.assertTrue(sidecar["human_review_required"])
        self.assertFalse(self.join["vss_is_fact_source"])
        self.assertFalse(self.join["candidate_event_mutated"])

    def test_combined_bundle_has_separate_source_sections(self) -> None:
        self.assertEqual(set(self.bundle["source_sections"]), {"sensor_inferred", "model_generated_narrative"})
        self.assertEqual(self.bundle["source_sections"]["sensor_inferred"][0]["source_class"], "sensor_inferred")
        self.assertEqual(self.bundle["source_sections"]["model_generated_narrative"][0]["source_class"], "model_generated_narrative")
        self.assertGreaterEqual(self.bundle["source_sections"]["sensor_inferred"][0]["candidate_observation_count"], 24)
        self.assertTrue(self.bundle["human_review_required"])

    def test_audits_pass_for_safe_join(self) -> None:
        self.assertEqual(source_class_audit(self.join, self.bundle)["status"], "PASS")
        self.assertEqual(prose_conflict_audit(self.join, self.lineage)["status"], "PASS")
        self.assertEqual(no_action_audit(self.review_packet, self.bundle)["status"], "PASS")
        self.assertEqual(claim_boundary_audit(self.join, self.bundle, self.review_packet)["status"], "PASS")

    def test_boundary_audit_rejects_forbidden_positive_claims(self) -> None:
        bad = claim_boundary_audit(
            {
                "candidate": True,
                "human_review_required": True,
                "vss_is_fact_source": False,
                "summary": "confirmed violation with ticket created and automated action",
            }
        )
        self.assertEqual(bad["status"], "FAIL")
        self.assertIn("confirmed violation", bad["forbidden_claim_hits"])

    def test_decision_logic_passes_and_fails_correctly(self) -> None:
        audits = {
            "source_class_separation": source_class_audit(self.join, self.bundle),
            "prose_vs_detection_conflict": prose_conflict_audit(self.join, self.lineage),
            "check_source_depth": {"status": "PASS"},
            "claim_boundary": claim_boundary_audit(self.join, self.bundle, self.review_packet),
            "no_action": no_action_audit(self.review_packet, self.bundle),
            "secret": {"status": "PASS"},
        }
        json_report = {"status": "PASS"}
        manifest = {"status": "PASS"}
        self.assertEqual(
            decide_status(self.lineage, self.join, self.bundle, self.review_packet, audits, json_report, manifest),
            PASS_STATUS,
        )
        audits["claim_boundary"] = {"status": "FAIL"}
        self.assertEqual(
            decide_status(self.lineage, self.join, self.bundle, self.review_packet, audits, json_report, manifest),
            FAIL_STATUS,
        )

    def test_current_r8_outputs_parse_when_present(self) -> None:
        output_root = ROOT / "outputs" / "main_citybrain_metropolis_vss_narration_evidence_join_r8"
        if output_root.exists():
            report = validate_json_outputs(output_root)
            self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
