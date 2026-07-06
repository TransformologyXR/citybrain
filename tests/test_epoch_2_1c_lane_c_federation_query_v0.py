import json
import unittest

from scripts.run_epoch_2_1c_lane_c_federation_query_v0 import (
    OUTPUT_ROOT,
    PROOF_CITIES,
    STATUS_PASS_LIMITATIONS,
    build_outputs,
    sha256_file,
)


class Epoch21cLaneCFederationQueryV0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs()
        cls.envelope = json.loads((OUTPUT_ROOT / "federation_query_envelope_v0.json").read_text(encoding="utf-8"))
        cls.results = json.loads((OUTPUT_ROOT / "federation_query_nyc_london_fixture_results.json").read_text(encoding="utf-8"))
        cls.id_audit = json.loads((OUTPUT_ROOT / "federation_city_scoped_id_audit.json").read_text(encoding="utf-8"))
        cls.boundary_audit = json.loads((OUTPUT_ROOT / "federation_non_claim_boundary_audit.json").read_text(encoding="utf-8"))
        cls.decision = json.loads((OUTPUT_ROOT / "PUSH_2_1C_LANE_C_DECISION.json").read_text(encoding="utf-8"))

    def test_prerequisite_gate_and_decision_pass_with_limitations(self):
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.result["status"])
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.decision["status"])
        self.assertEqual("main", self.decision["branch"])
        self.assertEqual("PASS", self.decision["prerequisite_gate"]["status"])
        self.assertTrue(self.decision["contract_check"]["epoch_2_1_not_closed"])

    def test_envelope_preserves_query_only_contract(self):
        for field in [
            "query_id",
            "query_type",
            "city_scope",
            "evidence_refs_required",
            "source_class_policy",
            "authority_level",
        ]:
            self.assertIn(field, self.envelope)
        self.assertEqual(PROOF_CITIES, self.envelope["city_scope"])
        self.assertTrue(self.envelope["evidence_refs_required"])
        self.assertEqual("preserve_city_scope", self.envelope["source_class_policy"])
        self.assertEqual("observe_or_explain_only", self.envelope["authority_level"])
        self.assertIn("no_global_canonical_identity", self.envelope["non_claims"])
        self.assertIn("dubai", self.envelope["excluded_as_proof"])

    def test_fixture_results_cover_required_query_shapes_on_nyc_london(self):
        self.assertEqual(PROOF_CITIES, self.results["proof"]["proof_cities"])
        self.assertTrue(self.results["proof"]["uses_only_real_corpora"])
        self.assertFalse(self.results["proof"]["dubai_synthetic_dependency"])
        query_types = {query["query_type"] for query in self.results["queries"]}
        for query_type in [
            "comparable_entity_types",
            "entity_profile",
            "maturity_compare",
            "domain_pack_presence",
            "source_freshness",
            "corpus_state",
        ]:
            self.assertIn(query_type, query_types)
        comparable = next(query for query in self.results["queries"] if query["query_type"] == "comparable_entity_types")
        self.assertGreater(comparable["result_count"], 0)
        profiles = next(query for query in self.results["queries"] if query["query_type"] == "entity_profile")
        self.assertEqual(2, profiles["result_count"])
        self.assertEqual({"nyc", "london"}, {row["source_city"] for row in profiles["results"]})

    def test_domain_pack_presence_has_city_support_without_global_merge(self):
        query = next(query for query in self.results["queries"] if query["query_type"] == "domain_pack_presence")
        self.assertEqual(4, query["result_count"])
        for row in query["results"]:
            self.assertEqual("PASS", row["validator_status"])
            self.assertTrue(row["source_class_policy_present"])
            self.assertTrue(row["available_in_both_proof_cities"], row)
            self.assertFalse(row["global_identity_merge"])

    def test_city_scoped_id_audit_rejects_global_or_dubai_ids(self):
        self.assertEqual("PASS", self.id_audit["status"])
        self.assertGreater(self.id_audit["city_scoped_id_count"], 0)
        self.assertEqual([], self.id_audit["invalid_city_scoped_ids"])
        self.assertEqual([], self.id_audit["missing_or_unapproved_city_prefix"])
        self.assertEqual([], self.id_audit["dubai_or_synthetic_proof_refs"])
        self.assertEqual(0, self.id_audit["global_canonical_merge_attempts"])
        for sample_id in self.id_audit["sample_ids"]:
            self.assertTrue(sample_id.startswith("nyc:") or sample_id.startswith("london:"), sample_id)

    def test_non_claim_boundary_audit(self):
        self.assertEqual("PASS", self.boundary_audit["status"])
        checks = self.boundary_audit["checks"]
        for key in [
            "query_only",
            "evidence_refs_required",
            "authority_level_observe_or_explain_only",
            "no_cross_city_learned_case_transfer",
            "no_global_canonical_id_merge",
            "no_federated_write_approval_or_action",
            "no_dubai_proof_dependency",
            "no_production_federation_deployment_claim",
            "local_replay_review_query_only",
        ]:
            self.assertTrue(checks[key], key)

    def test_hash_manifest_verifies(self):
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        manifest_paths = {row["path"] for row in manifest["files"]}
        for name in [
            "federation_query_envelope_v0.json",
            "federation_query_runner_or_fixture_v0.py",
            "federation_query_nyc_london_fixture_results.json",
            "federation_city_scoped_id_audit.json",
            "federation_non_claim_boundary_audit.json",
            "PUSH_2_1C_LANE_C_DECISION.json",
            "SUMMARY.md",
        ]:
            self.assertIn(name, manifest_paths)
        for row in manifest["files"]:
            target = OUTPUT_ROOT / row["path"]
            self.assertTrue(target.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(target), row)


if __name__ == "__main__":
    unittest.main()
