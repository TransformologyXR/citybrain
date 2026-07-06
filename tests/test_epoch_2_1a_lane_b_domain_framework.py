import json
import unittest

from scripts.run_epoch_2_1a_lane_b_domain_framework import (
    BLOCK_STATUS,
    CONSUMING_CAPABILITY_FIELDS,
    GOVERNED_ADDITION_TYPES,
    OUTPUT_ROOT,
    PASS_STATUS,
    check_epoch_2_0_entry,
    validate_domain_pack_manifest,
    write_all_outputs,
)


class Epoch21aLaneBDomainFrameworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.entry = cls.result["entry"]

    def test_epoch_2_0_entry_check_passes(self):
        self.assertEqual("PASS", self.entry["status"], self.entry.get("gaps"))
        criteria = self.entry["pass_criteria"]
        self.assertTrue(all(criteria.values()), criteria)
        for label in [
            "Watch Scout",
            "Diff Scout",
            "CHECK Agent",
            "Approval Lifecycle Agent",
            "Spatial Agent",
            "Perception / Media Agent",
        ]:
            self.assertIn(label, self.entry["mandatory_recertification_index"])

    def test_required_artifacts_exist(self):
        required = [
            "EPOCH_2_0_ENTRY_CHECK_DECISION.json",
            "EPOCH_2_0_ENTRY_CHECK_SUMMARY.md",
            "EPOCH_2_0_AGENT_RECERTIFICATION_INDEX.json",
            "EPOCH_2_1_ALLOWED_TO_OPEN.flag",
            "domain_pack_framework_v1.md",
            "domain_pack_manifest_schema_v1.json",
            "domain_pack_validator.py",
            "domain_ontology_governance_v1.md",
            "entity_relationship_addition_policy_v1.md",
            "domain_pack_compatibility_policy_v1.md",
            "PUSH_2_1A_LANE_B_DECISION.json",
            "HASH_MANIFEST.json",
            "SUMMARY.md",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertFalse((OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_GAPS.md").exists())

    def test_decision_preserves_framework_only_boundary(self):
        decision = json.loads((OUTPUT_ROOT / "PUSH_2_1A_LANE_B_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(PASS_STATUS, decision["status"])
        self.assertTrue(decision["framework_only"])
        self.assertEqual(0, decision["starter_packs_created"])
        self.assertEqual(0, decision["dubai_pack_created"])
        self.assertFalse(decision["live_source_created"])
        self.assertFalse(decision["trained_model_created"])
        self.assertFalse(decision["agent_activation_created"])
        self.assertEqual(set(GOVERNED_ADDITION_TYPES), set(decision["governance_coverage"]))

    def test_manifest_schema_requires_pack_safety_fields(self):
        schema = json.loads((OUTPUT_ROOT / "domain_pack_manifest_schema_v1.json").read_text(encoding="utf-8"))
        for field in [
            "source_class_policy",
            "consuming_capabilities",
            "eval_fixtures",
            "check_expectations",
            "authority_profile",
            "app_spatial_handoff_profile",
            "compatibility",
            "rollback_ref",
            "deprecation_path",
        ]:
            self.assertIn(field, schema["required"])
        self.assertIn("no_consuming_capability", schema["must_not_merge_if"])

    def test_validator_rejects_no_consumer_and_no_eval(self):
        valid_manifest = {
            "pack_id": "test_pack",
            "version": "1.0.0",
            "domain": "test",
            "source_class_policy": {
                "allowed_source_classes": ["replay_fixture"],
                "source_class_required": True,
                "vss_as_fact_source_allowed": False,
            },
            "consuming_capabilities": {"watch_families": ["watch:test"]},
            "eval_fixtures": ["eval:test"],
            "check_expectations": {"requires_check_report": True, "requires_authority_envelope": True},
            "authority_profile": {"max_authority_level": 3, "no_execution_authority": True},
            "entity_relationship_refs": {"entity_types": [], "relationship_types": []},
            "app_spatial_handoff_profile": {"app_surface_refs": ["app:test"], "spatial_overlay_profile": "overlay:test"},
            "compatibility": {"manifest_version": "1.0.0", "compatibility_version": "1.0", "breaking_change_policy": "gate_review_required"},
            "limitations": ["test only"],
            "rollback_ref": "rollback:test",
            "deprecation_path": {"owner": "governance", "notice": "test", "replacement_or_removal_path": "remove"},
            "governance_additions": {},
        }
        self.assertEqual("PASS", validate_domain_pack_manifest(valid_manifest)["status"])
        no_consumer = {**valid_manifest, "consuming_capabilities": {}}
        self.assertIn("no_consuming_capability", validate_domain_pack_manifest(no_consumer)["errors"])
        no_eval = {**valid_manifest, "eval_fixtures": []}
        self.assertIn("no_eval_fixtures", validate_domain_pack_manifest(no_eval)["errors"])
        starter = {**valid_manifest, "pack_kind": "starter_pack"}
        self.assertIn("forbidden_pack_kind_in_2_1a_lane_b", validate_domain_pack_manifest(starter)["errors"])

    def test_hash_manifest_covers_outputs(self):
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in manifest["files"]}
        self.assertIn("PUSH_2_1A_LANE_B_DECISION.json", paths)
        self.assertIn("domain_pack_manifest_schema_v1.json", paths)
        self.assertGreaterEqual(manifest["item_count"], 10)


if __name__ == "__main__":
    unittest.main()
