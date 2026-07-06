import json
import unittest

from scripts.run_epoch_2_1c_lane_a_dubai_synthetic_pack import (
    DOMAINS,
    GENERATED_SOURCE_CLASSES,
    OUTPUT_ROOT,
    PASS_STATUS,
    REQUIRED_ARTIFACTS,
    write_all_outputs,
)


class Epoch21cLaneADubaiSyntheticPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.gate = cls.result["gate"]
        cls.decision = cls.result["decision"]

    def read_artifact(self, name):
        return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))

    def all_records(self):
        records = []
        for name in [
            "dubai_gold_tier_manifest.json",
            "dubai_dirty_source_tier_manifest.json",
            "dubai_challenge_tier_manifest.json",
        ]:
            tier = self.read_artifact(name)
            records.extend(tier["records"])
        return records

    def test_prerequisite_gate_passes(self):
        self.assertEqual("PASS", self.gate["status"], self.gate["errors"])
        self.assertEqual("main", self.gate["branch"])
        self.assertTrue(self.gate["decision_status"].startswith("PASS"))
        self.assertTrue(self.gate["push_2_1c_allowed_to_open"])
        self.assertEqual("PASS", self.gate["flag_value"])

    def test_required_artifacts_exist(self):
        for name in REQUIRED_ARTIFACTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_manifest_uses_all_starter_domain_packs_and_privacy_refs(self):
        manifest = self.read_artifact("dubai_synthetic_pack_manifest_v1.json")
        self.assertEqual("citybrain_dubai_anchored_synthetic_pack", manifest["pack_id"])
        self.assertEqual(set(DOMAINS), set(manifest["input_refs"]["starter_domain_packs"].keys()))
        for domain in DOMAINS:
            row = manifest["input_refs"]["starter_domain_packs"][domain]
            self.assertTrue(row["pack_id"].startswith(f"citybrain_starter_{domain}_domain_pack"))
            self.assertTrue(row["manifest_ref"].endswith(f"domain_packs/{domain}/manifest.json"))
            self.assertTrue(row["source_class_matrix_ref"].endswith(f"domain_packs/{domain}/source_class_matrix.json"))
        self.assertIn("privacy_retention_policy", manifest["input_refs"]["privacy_policy_refs"])
        self.assertFalse(manifest["target_city_context"]["production_truth_claim"])

    def test_gold_dirty_and_challenge_tiers_are_present(self):
        gold = self.read_artifact("dubai_gold_tier_manifest.json")
        dirty = self.read_artifact("dubai_dirty_source_tier_manifest.json")
        challenge = self.read_artifact("dubai_challenge_tier_manifest.json")
        self.assertEqual("dubai_gold_canonical_tier_v1", gold["tier_id"])
        self.assertEqual("dubai_dirty_source_tier_v1", dirty["tier_id"])
        self.assertEqual("dubai_challenge_tier_v1", challenge["tier_id"])
        self.assertGreaterEqual(len(gold["records"]), 4)
        self.assertGreaterEqual(len(dirty["records"]), 4)
        self.assertGreaterEqual(len(challenge["records"]), 5)
        self.assertTrue(any(row["record_kind"] == "replay_event" for row in challenge["records"]))

    def test_source_class_separation_is_strict(self):
        records = self.all_records()
        self.assertTrue(records)
        for record in records:
            self.assertIn(record["source_class"], GENERATED_SOURCE_CLASSES, record["record_id"])
            self.assertIsNone(record["real_anchor_ref"], record["record_id"])
            self.assertEqual("not_present_in_accepted_inputs", record["real_anchor_status"])
            self.assertFalse(record["source_class_separation"]["merge_allowed"], record["record_id"])
            self.assertFalse(record["source_class_separation"]["official_or_source_record_claimed"], record["record_id"])
        replay_records = [record for record in records if record["record_kind"] == "replay_event"]
        self.assertTrue(replay_records)
        self.assertTrue(all(record["source_class"] == "replay" for record in replay_records))
        self.assertFalse(any(record["source_class"] == "model_inferred" for record in records))

    def test_every_generated_record_has_consuming_surface_or_eval(self):
        for record in self.all_records():
            consumed_by = record["consumed_by"]
            self.assertTrue(consumed_by["consumer_refs"] or consumed_by["eval_refs"], record["record_id"])
            self.assertTrue(record["starter_pack_id"].startswith(f"citybrain_starter_{record['domain']}_domain_pack"))
            self.assertIn("local_replay_review_query_only", record["check_expectations"])

    def test_source_class_audit_passes_expected_guards(self):
        audit = self.read_artifact("dubai_synthetic_source_class_audit.json")
        self.assertEqual("PASS_WITH_LIMITATIONS", audit["status"])
        checks = audit["checks"]
        self.assertTrue(checks["starter_packs_loaded"])
        self.assertTrue(checks["privacy_policy_loaded"])
        self.assertTrue(checks["generated_records_have_source_class"])
        self.assertTrue(checks["generated_source_classes_are_allowed"])
        self.assertTrue(checks["no_official_or_source_record_claims_in_generated_pack"])
        self.assertTrue(checks["synthetic_and_real_facts_not_merged"])
        self.assertTrue(checks["replay_events_marked_replay"])
        self.assertTrue(checks["live_dubai_source_ingestion_absent"])
        self.assertTrue(checks["federation_proof_claim_absent"])
        self.assertTrue(checks["production_citywide_truth_claim_absent"])
        self.assertGreater(audit["source_class_counts"]["synthetic"], 0)
        self.assertGreater(audit["source_class_counts"]["replay"], 0)

    def test_validation_report_and_decision_preserve_boundaries(self):
        validation = self.read_artifact("dubai_pack_validation_report.json")
        decision = self.read_artifact("PUSH_2_1C_LANE_A_DECISION.json")
        self.assertEqual("PASS_WITH_LIMITATIONS", validation["status"])
        self.assertEqual(PASS_STATUS, decision["status"])
        self.assertEqual(DOMAINS, decision["starter_domains_used"])
        self.assertTrue(validation["checks"]["every_record_consumed_by_existing_surface_or_eval"])
        self.assertTrue(validation["checks"]["gold_dirty_challenge_only_no_new_demo_packaging"])
        self.assertFalse(decision["boundaries"]["live_dubai_source_ingestion_created"])
        self.assertFalse(decision["boundaries"]["production_citywide_truth_claim_created"])
        self.assertFalse(decision["boundaries"]["federation_proof_created"])
        self.assertFalse(decision["boundaries"]["trained_prediction_model_created"])
        self.assertFalse(decision["boundaries"]["official_action_dispatch_enforcement_created"])
        self.assertFalse(decision["boundaries"]["new_demo_packaging_concept_created"])
        self.assertTrue(decision["boundaries"]["local_replay_review_query_only"])

    def test_hash_manifest_covers_required_artifacts(self):
        manifest = self.read_artifact("HASH_MANIFEST.json")
        paths = {row["path"] for row in manifest["files"]}
        for name in REQUIRED_ARTIFACTS:
            if name != "HASH_MANIFEST.json":
                self.assertIn(name, paths)
        self.assertEqual(len(paths), manifest["item_count"])


if __name__ == "__main__":
    unittest.main()
