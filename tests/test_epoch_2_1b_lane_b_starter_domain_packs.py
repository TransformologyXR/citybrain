import json
import unittest

from scripts.run_epoch_2_1a_lane_b_domain_framework import SOURCE_CLASS_ALLOWED_VALUES, validate_domain_pack_manifest
from scripts.run_epoch_2_1b_lane_b_starter_domain_packs import (
    DOMAINS,
    NON_GOALS,
    OUTPUT_ROOT,
    PASS_STATUS,
    check_prerequisite_gate,
    flatten_capability_refs,
    write_all_outputs,
)


class Epoch21bLaneBStarterDomainPacksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.gate = cls.result["gate"]
        cls.decision = cls.result["decision"]

    def test_prerequisite_gate_passes(self):
        self.assertEqual("PASS", self.gate["status"], self.gate["errors"])
        self.assertEqual("main", self.gate["branch"])
        self.assertTrue(self.gate["gate_decision_status"].startswith("PASS"))
        self.assertTrue(self.gate["push_2_1b_allowed_to_open"])
        self.assertEqual("PASS", self.gate["gate_flag_value"])

    def test_required_artifacts_exist(self):
        required_top_level = [
            "starter_domain_pack_validation_report.json",
            "starter_domain_pack_eval_fixtures_report.json",
            "corpus_source_of_truth_append_report.json",
            "PUSH_2_1B_LANE_B_DECISION.json",
            "HASH_MANIFEST.json",
            "SUMMARY.md",
        ]
        for name in required_top_level:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        for domain in DOMAINS:
            for name in ["manifest.json", "consumer_fixtures.json", "eval_fixtures.json", "source_class_matrix.json", "README.md"]:
                self.assertTrue((OUTPUT_ROOT / "domain_packs" / domain / name).exists(), f"{domain}/{name}")

    def test_all_starter_manifests_pass_2_1a_validator(self):
        for domain in DOMAINS:
            manifest = json.loads((OUTPUT_ROOT / "domain_packs" / domain / "manifest.json").read_text(encoding="utf-8"))
            validation = validate_domain_pack_manifest(manifest)
            self.assertEqual("PASS", validation["status"], (domain, validation["errors"]))
            self.assertTrue(flatten_capability_refs(manifest["consuming_capabilities"]), domain)
            self.assertTrue(manifest["eval_fixtures"], domain)
            self.assertTrue(manifest["check_expectations"]["requires_check_report"], domain)
            self.assertTrue(manifest["check_expectations"]["requires_authority_envelope"], domain)
            self.assertTrue(manifest["authority_profile"]["no_execution_authority"], domain)
            self.assertTrue(manifest["source_class_policy"]["source_class_required"], domain)
            self.assertFalse(manifest["source_class_policy"]["vss_as_fact_source_allowed"], domain)
            self.assertTrue(set(manifest["source_class_policy"]["allowed_source_classes"]).issubset(SOURCE_CLASS_ALLOWED_VALUES), domain)
            self.assertIn("freshness_interpretation", manifest["source_class_policy"], domain)
            self.assertTrue(manifest["app_spatial_handoff_profile"]["app_surface_refs"], domain)
            self.assertTrue(manifest["app_spatial_handoff_profile"]["spatial_overlay_profile"], domain)
            self.assertTrue(manifest["compatibility"]["compatibility_version"], domain)
            self.assertTrue(manifest["rollback_ref"], domain)
            self.assertTrue(manifest["deprecation_path"]["replacement_or_removal_path"], domain)

    def test_pack_specific_consumer_surfaces_are_present(self):
        planning = json.loads((OUTPUT_ROOT / "domain_packs" / "planning" / "manifest.json").read_text(encoding="utf-8"))
        mobility = json.loads((OUTPUT_ROOT / "domain_packs" / "mobility" / "manifest.json").read_text(encoding="utf-8"))
        utilities = json.loads((OUTPUT_ROOT / "domain_packs" / "utilities" / "manifest.json").read_text(encoding="utf-8"))
        building = json.loads((OUTPUT_ROOT / "domain_packs" / "building" / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(planning["consuming_capabilities"]["ask_templates"])
        self.assertTrue(planning["consuming_capabilities"]["brief_templates"])
        self.assertTrue(planning["consuming_capabilities"]["watch_families"])
        self.assertTrue(mobility["consuming_capabilities"]["spatial_overlay_fixtures"])
        self.assertTrue(utilities["consuming_capabilities"]["diff_fixtures"])
        self.assertTrue(building["consuming_capabilities"]["perception_review_fixtures"])

    def test_validation_report_negative_guards(self):
        report = json.loads((OUTPUT_ROOT / "starter_domain_pack_validation_report.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", report["status"])
        for domain in DOMAINS:
            self.assertEqual("PASS", report["pack_results"][domain]["status"], domain)
        self.assertIn("no_consuming_capability", report["negative_fixture_results"]["no_consuming_capability"]["errors"])
        self.assertIn("no_eval_fixtures", report["negative_fixture_results"]["no_eval_fixtures"]["errors"])

    def test_decision_preserves_boundaries(self):
        decision = json.loads((OUTPUT_ROOT / "PUSH_2_1B_LANE_B_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(PASS_STATUS, decision["status"])
        self.assertEqual(DOMAINS, decision["starter_domains"])
        self.assertEqual(4, decision["starter_pack_count"])
        self.assertFalse(decision["boundaries"]["dubai_pack_created"])
        self.assertFalse(decision["boundaries"]["live_source_onboarding_created"])
        self.assertFalse(decision["boundaries"]["trained_model_created"])
        self.assertFalse(decision["boundaries"]["ranking_prediction_or_learning_loop_created"])
        self.assertFalse(decision["boundaries"]["domain_autonomous_agents_created"])
        self.assertFalse(decision["boundaries"]["official_legal_or_government_conclusion_created"])
        self.assertTrue(decision["boundaries"]["local_replay_review_query_only"])
        self.assertEqual(NON_GOALS, decision["limitations"])

    def test_corpus_append_report_is_registration_only(self):
        report = json.loads((OUTPUT_ROOT / "corpus_source_of_truth_append_report.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS_WITH_LIMITATIONS", report["status"])
        self.assertFalse(report["mutation_performed"])
        self.assertFalse(report["frozen_upstream_outputs_mutated"])
        self.assertEqual(4, len(report["registration_entries"]))
        self.assertEqual(set(DOMAINS), {row["domain"] for row in report["registration_entries"]})

    def test_hash_manifest_covers_pack_manifests_and_decision(self):
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in manifest["files"]}
        self.assertIn("PUSH_2_1B_LANE_B_DECISION.json", paths)
        self.assertIn("starter_domain_pack_validation_report.json", paths)
        for domain in DOMAINS:
            self.assertIn(f"domain_packs/{domain}/manifest.json", paths)
        self.assertGreaterEqual(manifest["item_count"], 25)


if __name__ == "__main__":
    unittest.main()
