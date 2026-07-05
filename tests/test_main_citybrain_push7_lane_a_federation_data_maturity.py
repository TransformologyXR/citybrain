import json
import subprocess
import unittest
from pathlib import Path

from packages.federation import (
    boundary_scan,
    validate_cross_city_recall_fixture,
    validate_data_maturity_score,
    validate_department_local_node,
    validate_federated_packet_envelope,
    validate_source_refresh_policy,
    validate_source_refresh_run_record,
    validate_synthetic_city_pack,
)
from scripts.run_main_citybrain_push7_lane_a_federation_data_maturity import (
    ASK_CONTRACT_PATHS,
    CLOSEOUT_ROOT,
    FINAL_ROOT,
    FINAL_STATUS,
    OUTPUT_ROOT,
    PASS_STATUS,
    R7_RUNTIME_PATHS,
    REQUIRED_CLOSEOUT_OUTPUTS,
    REQUIRED_FINAL_OUTPUTS,
    REQUIRED_OUTPUTS,
    verify_hash_manifest,
    build_outputs,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush7LaneAFederationDataMaturityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = build_outputs({"runner": "TEST_SETUP"})
        cls.decision = json.loads((OUTPUT_ROOT / "FEDERATION_DATA_MATURITY_DECISION.json").read_text(encoding="utf-8"))
        cls.nodes = json.loads((OUTPUT_ROOT / "DEPARTMENT_NODE_MANIFESTS.json").read_text(encoding="utf-8"))
        cls.scores = json.loads((OUTPUT_ROOT / "DATA_MATURITY_SCORES.json").read_text(encoding="utf-8"))
        cls.policies = json.loads((OUTPUT_ROOT / "SOURCE_REFRESH_POLICIES.json").read_text(encoding="utf-8"))
        cls.runs = json.loads((OUTPUT_ROOT / "SOURCE_REFRESH_RUN_RECORDS.json").read_text(encoding="utf-8"))
        cls.envelopes = json.loads((OUTPUT_ROOT / "FEDERATED_PACKET_ENVELOPES.json").read_text(encoding="utf-8"))
        cls.dubai = json.loads((OUTPUT_ROOT / "DUBAI_SYNTHETIC_PACK_MANIFEST.json").read_text(encoding="utf-8"))
        cls.cross_city = json.loads((OUTPUT_ROOT / "CROSS_CITY_RECALL_BOUNDARY_FIXTURES.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        for name in REQUIRED_CLOSEOUT_OUTPUTS:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in REQUIRED_FINAL_OUTPUTS:
            self.assertTrue((FINAL_ROOT / name).exists(), name)

    def test_department_nodes_validate(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertEqual(4, len(self.nodes["department_local_nodes"]))
        self.assertEqual(4, len(self.nodes["node_capability_manifests"]))
        for node in self.nodes["department_local_nodes"]:
            report = validate_department_local_node(node)
            self.assertEqual("PASS", report["status"], report)
            self.assertTrue(node["evidence_refs"])
            self.assertTrue(node["limitation_refs"])
            self.assertTrue(node["trace_refs"])

    def test_data_maturity_scores_validate_and_reject_forbidden_bands(self):
        self.assertEqual("PASS", self.scores["status"])
        self.assertEqual(8, len(self.scores["items"]))
        forbidden = set(self.scores["forbidden_score_bands"])
        for score in self.scores["items"]:
            report = validate_data_maturity_score(score)
            self.assertEqual("PASS", report["status"], report)
            self.assertNotIn(score["score_band"], forbidden)
        probe = dict(self.scores["items"][0])
        probe["score_band"] = "production_live"
        self.assertEqual("FAIL", validate_data_maturity_score(probe)["status"])

    def test_federated_envelopes_preserve_evidence_limitation_trace_check_authority(self):
        self.assertEqual("PASS", self.envelopes["status"])
        self.assertEqual(6, len(self.envelopes["items"]))
        self.assertEqual(6, len(self.envelopes["federation_boundary_decisions"]))
        for envelope in self.envelopes["items"]:
            report = validate_federated_packet_envelope(envelope)
            self.assertEqual("PASS", report["status"], report)
            self.assertTrue(envelope["evidence_refs"])
            self.assertTrue(envelope["limitation_refs"])
            self.assertTrue(envelope["trace_refs"])
            self.assertTrue(envelope["check_report_ref"])
            self.assertTrue(envelope["authority_envelope_ref"])

    def test_source_refresh_records_are_local_replay_only(self):
        self.assertEqual("PASS", self.policies["status"])
        self.assertEqual("PASS", self.runs["status"])
        for policy in self.policies["items"]:
            self.assertEqual("PASS", validate_source_refresh_policy(policy)["status"])
            self.assertFalse(policy["production_api_used"])
            self.assertFalse(policy["url_fetch_used"])
            self.assertFalse(policy["live_retrieval_used"])
        for run in self.runs["items"]:
            self.assertEqual("PASS", validate_source_refresh_run_record(run)["status"])
            self.assertEqual("not_executed", run["execution_status"])
            self.assertFalse(run["production_api_used"])
            self.assertFalse(run["url_fetch_used"])
            self.assertFalse(run["live_retrieval_used"])

    def test_dubai_pack_is_synthetic_only(self):
        report = validate_synthetic_city_pack(self.dubai)
        self.assertEqual("PASS", report["status"], report)
        self.assertEqual("dubai_synthetic", self.dubai["synthetic_city_id"])
        self.assertFalse(self.dubai["real_dubai_coverage_claimed"])
        self.assertFalse(self.dubai["real_government_source_integration_claimed"])
        self.assertFalse(self.dubai["production_twin_claimed"])

    def test_cross_city_recall_fixtures_boundary_safe_and_non_authoritative(self):
        self.assertEqual("PASS", self.cross_city["status"])
        self.assertFalse(self.cross_city["real_cross_city_claim"])
        self.assertEqual(2, len(self.cross_city["items"]))
        for fixture in self.cross_city["items"]:
            report = validate_cross_city_recall_fixture(fixture)
            self.assertEqual("PASS", report["status"], report)
            self.assertTrue(fixture["synthetic_fixture_only"])
            self.assertFalse(fixture["real_cross_city_claim"])
            self.assertEqual("non_authoritative_fixture", fixture["authority_status"])

    def test_no_production_federation_api_live_retrieval_or_real_cross_city_claim(self):
        payload = {
            "nodes": self.nodes,
            "scores": self.scores,
            "policies": self.policies,
            "runs": self.runs,
            "envelopes": self.envelopes,
            "dubai": self.dubai,
            "cross_city": self.cross_city,
        }
        scan = boundary_scan(payload)
        self.assertEqual("PASS", scan["status"], scan)
        contract = self.decision["contract_check"]["gates"]
        self.assertTrue(contract["no_real_cross_city_claim"])
        self.assertTrue(contract["no_production_federation_api_live_retrieval"])
        self.assertTrue(contract["no_official_certified_live_maturity_band"])

    def test_hashes_closeout_final_and_protected_diffs(self):
        closeout = json.loads((CLOSEOUT_ROOT / "FEDERATION_DATA_MATURITY_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        final = json.loads((FINAL_ROOT / "FEDERATION_DATA_MATURITY_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(PASS_STATUS, closeout["status"])
        self.assertEqual(FINAL_STATUS, final["status"])
        for root, name in [
            (OUTPUT_ROOT, "FEDERATION_DATA_MATURITY_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "FEDERATION_DATA_MATURITY_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "FEDERATION_DATA_MATURITY_FINAL_STATUS_HASH_MANIFEST.json"),
        ]:
            report = verify_hash_manifest(root, name)
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])

        ask = subprocess.run(["git", "diff", "--", *ASK_CONTRACT_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        r7 = subprocess.run(["git", "diff", "--", *R7_RUNTIME_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual("", ask.stdout)
        self.assertEqual("", r7.stdout)


if __name__ == "__main__":
    unittest.main()
