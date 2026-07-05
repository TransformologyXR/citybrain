from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_main_citybrain_metropolis_vss_sprint_closeout_r9 import (  # noqa: E402
    FAIL_STATUS,
    PASS_STATUS,
    REQUIRED_SPINE,
    audit_boundary,
    audit_feature_freeze,
    audit_no_action,
    audit_source_class,
    audit_vss_not_fact_source,
    build_human_review_handoff,
    build_lineage,
    decide_status,
    hash_manifest,
    known_limitations,
    next_recommendations,
    positive_forbidden_hits,
    validate_json_outputs,
    validate_zip_package,
)


class MetropolisVssSprintCloseoutR9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lineage = build_lineage()
        cls.limitations = known_limitations()
        cls.recommendations = next_recommendations()
        cls.missing_generated_spine = [
            label
            for label, item in cls.lineage["required_pass_spine"].items()
            if not item["present"] or item["package_validation"] != "PASS"
        ]

    def require_generated_spine(self) -> None:
        if self.missing_generated_spine:
            self.skipTest(
                "requires generated Metropolis/VSS milestone output packages: "
                + ", ".join(self.missing_generated_spine)
            )

    def test_required_spine_is_present_and_validated(self) -> None:
        self.require_generated_spine()
        spine = self.lineage["required_pass_spine"]
        self.assertEqual(set(spine), REQUIRED_SPINE)
        for label, item in spine.items():
            with self.subTest(label=label):
                self.assertTrue(item["present"])
                self.assertTrue(str(item["decision_status"]).startswith("PASS"))
                self.assertEqual(item["package_validation"], "PASS")

    def test_final_truth_preserves_r2_r7_r8_boundary(self) -> None:
        self.require_generated_spine()
        truth = self.lineage["final_truth"]
        self.assertEqual(truth["candidate_event_id"], "metropolis-vss-r2-event-001")
        self.assertEqual(truth["candidate_observation_count"], 24)
        self.assertEqual(truth["vss_narration_sidecars_joined"], 1)
        self.assertEqual(truth["r2_source_class"], "sensor_inferred")
        self.assertEqual(truth["r7_vss_source_class"], "model_generated_narrative")
        self.assertFalse(truth["vss_is_fact_source"])
        self.assertFalse(truth["candidate_event_mutated"])

    def test_runtime_host_allocation_is_final_boundary(self) -> None:
        host = self.lineage["final_host_allocation"]
        self.assertEqual(host["deepstream_metropolis"]["active_host"], "txr-4070")
        self.assertEqual(host["deepstream_metropolis"]["source_class"], "sensor_inferred")
        self.assertEqual(host["spark_vss"]["active_host"], "spark-2445")
        self.assertEqual(host["spark_vss"]["source_class"], "model_generated_narrative")
        self.assertTrue(host["spark_vss"]["not_fact_source"])
        self.assertFalse(host["txr_3090"]["active_for_this_chain"])

    def test_audits_pass_for_current_lineage(self) -> None:
        self.require_generated_spine()
        self.assertEqual(audit_source_class(self.lineage)["status"], "PASS")
        self.assertEqual(audit_boundary(self.lineage, self.limitations, self.recommendations)["status"], "PASS")
        self.assertEqual(audit_no_action(self.lineage)["status"], "PASS")
        self.assertEqual(audit_vss_not_fact_source(self.lineage)["status"], "PASS")
        self.assertEqual(audit_feature_freeze(self.lineage)["status"], "PASS")
        handoff = build_human_review_handoff(self.lineage)
        self.assertTrue(handoff["human_review_required"])
        self.assertFalse(handoff["vss_is_fact_source"])

    def test_boundary_audit_rejects_positive_forbidden_claims(self) -> None:
        bad = {
            "summary": "confirmed violation with ticket created and automated action taken",
            "human_review_required": False,
        }
        hits = positive_forbidden_hits(bad)
        self.assertIn("confirmed_violation", hits)
        self.assertIn("ticket_created", hits)
        self.assertIn("automated_action", hits)

    def test_all_milestone_packages_validate(self) -> None:
        self.require_generated_spine()
        for item in self.lineage["milestones"]:
            with self.subTest(label=item["label"]):
                package_path = ROOT / item["root"] / item["package"]
                self.assertEqual(validate_zip_package(package_path)["status"], "PASS")

    def test_decision_logic_passes_and_fails_correctly(self) -> None:
        self.require_generated_spine()
        audits = {
            "source_class_separation": audit_source_class(self.lineage),
            "boundary": audit_boundary(self.lineage, self.limitations, self.recommendations),
            "no_action_human_review": audit_no_action(self.lineage),
            "vss_not_fact_source": audit_vss_not_fact_source(self.lineage),
            "feature_freeze": audit_feature_freeze(self.lineage),
            "secret": {"status": "PASS"},
        }
        tests = {"targeted_r9": "PASS", "full_discovery": "PASS"}
        self.assertEqual(decide_status(audits, {"status": "PASS"}, {"status": "PASS"}, tests), PASS_STATUS)
        audits["boundary"] = {"status": "FAIL"}
        self.assertEqual(decide_status(audits, {"status": "PASS"}, {"status": "PASS"}, tests), FAIL_STATUS)

    def test_current_r9_outputs_parse_when_present(self) -> None:
        output_root = ROOT / "outputs" / "main_citybrain_metropolis_vss_sprint_closeout_r9"
        if output_root.exists():
            self.assertEqual(validate_json_outputs(output_root)["status"], "PASS")
            manifest = hash_manifest(output_root)
            self.assertEqual(manifest["status"], "PASS")
            if (output_root / "METROPOLIS_VSS_SPRINT_CLOSEOUT_R9_PACKAGE.zip").exists():
                required_files = {
                    "SPRINT_CLOSEOUT_DECISION_R9.json",
                    "R1_R9_LINEAGE_SUMMARY_R9.json",
                    "RUNTIME_HOST_ALLOCATION_FINAL_R9.json",
                    "SOURCE_CLASS_SEPARATION_FINAL_AUDIT_R9.json",
                    "CLAIM_BOUNDARY_FINAL_AUDIT_R9.json",
                    "NO_ACTION_FINAL_AUDIT_R9.json",
                    "VSS_NOT_FACT_SOURCE_FINAL_AUDIT_R9.json",
                    "HUMAN_REVIEW_HANDOFF_FINAL_R9.json",
                    "KNOWN_LIMITATIONS_R9.md",
                    "NEXT_SPRINT_RECOMMENDATIONS_R9.md",
                    "R9_JSON_PARSE_REPORT.json",
                    "HASH_MANIFEST.json",
                    "METROPOLIS_VSS_SPRINT_CLOSEOUT_R9_PACKAGE.zip",
                }
                present = {path.name for path in output_root.iterdir() if path.is_file()}
                self.assertTrue(required_files.issubset(present))


if __name__ == "__main__":
    unittest.main()
