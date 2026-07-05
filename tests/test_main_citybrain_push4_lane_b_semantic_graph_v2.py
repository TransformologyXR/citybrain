import json
import subprocess
import sys
import unittest
from pathlib import Path

from packages.semantic_graph import query_graph, validate_graph_bundle
from scripts.run_main_citybrain_push4_lane_b_semantic_graph_v2 import (
    CLOSEOUT_ROOT,
    FINAL_STATUS_ROOT,
    OUTPUT_ROOT,
    PASS_STATUS,
    REQUIRED_OUTPUT_FILES,
    STOP_STATUS,
    verify_hash_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush4LaneBSemanticGraphV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, "scripts/run_main_citybrain_push4_lane_b_semantic_graph_v2.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        cls.decision = json.loads((OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_DECISION.json").read_text(encoding="utf-8"))
        cls.alignment = json.loads((OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_CER_ALIGNMENT_REPORT.json").read_text(encoding="utf-8"))
        cls.graph = json.loads((OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_EDGE_FIXTURES.json").read_text(encoding="utf-8"))
        cls.queries = json.loads((OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_QUERY_FIXTURES.json").read_text(encoding="utf-8"))
        cls.edge_schema = json.loads((OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_EDGE_SCHEMA.json").read_text(encoding="utf-8"))
        cls.dependency_schema = json.loads((OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_DEPENDENCY_EDGE_SCHEMA.json").read_text(encoding="utf-8"))

    def test_required_artifacts_exist(self):
        for name in REQUIRED_OUTPUT_FILES:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertIn(self.decision["status"], {STOP_STATUS, PASS_STATUS})
        self.assertEqual("PASS", self.decision["required_output_status"]["status"])

    def test_stops_before_final_status_when_lane_a_cer_is_missing(self):
        if self.decision["lane_a_cer_status"] == "missing":
            self.assertEqual(STOP_STATUS, self.decision["status"])
            self.assertTrue(self.decision["cer_refs_are_provisional"])
            self.assertFalse(self.alignment["cer_aligned_to_lane_a"])
            self.assertFalse(self.alignment["final_closeout_allowed"])
            self.assertFalse(CLOSEOUT_ROOT.exists())
            self.assertFalse(FINAL_STATUS_ROOT.exists())

    def test_contract_defines_required_graph_shapes(self):
        required_terms = {
            "GraphNodeRef",
            "GraphEdge",
            "DependencyEdge",
            "SourceBackedRelationship",
            "GraphQueryResult",
            "GraphReviewState",
        }
        overview = (OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_CONTRACT_OVERVIEW.md").read_text(encoding="utf-8")
        for term in required_terms:
            self.assertIn(term, overview)
        self.assertIn("edge_type", self.edge_schema["required"])
        self.assertIn("DependencyEdge", self.dependency_schema["title"])

    def test_graph_edges_use_cer_entity_or_assertion_ids(self):
        edges = self.graph["edges"]
        self.assertGreaterEqual(len(edges), 7)
        cer_ref_kinds = {"cer_entity", "attribute_assertion"}
        for edge in edges:
            refs = {edge["from_ref"]["ref_kind"], edge["to_ref"]["ref_kind"]}
            self.assertTrue(refs & cer_ref_kinds, edge["edge_id"])
            self.assertNotIn("entity_shape", json.dumps(edge).lower())
        assertion_edges = [
            edge
            for edge in edges
            if edge["from_ref"]["ref_kind"] == "attribute_assertion" or edge["to_ref"]["ref_kind"] == "attribute_assertion"
        ]
        self.assertGreaterEqual(len(assertion_edges), 3)
        self.assertTrue(self.alignment["cer_entity_assertion_ids_used"])
        self.assertTrue(self.alignment["no_pre_assertion_entity_shape_dependency"])

    def test_edges_preserve_evidence_limit_trace_check_and_authority_refs(self):
        for edge in self.graph["edges"]:
            self.assertTrue(edge["evidence_refs"], edge["edge_id"])
            self.assertTrue(edge["limitation_refs"], edge["edge_id"])
            self.assertTrue(edge["trace_refs"], edge["edge_id"])
            self.assertTrue(edge["check_report_ref"], edge["edge_id"])
            self.assertTrue(edge["authority_envelope_ref"], edge["edge_id"])
        for relationship in self.graph["source_backed_relationships"]:
            self.assertTrue(relationship["evidence_refs"])
            self.assertTrue(relationship["limitation_refs"])
            self.assertTrue(relationship["trace_refs"])
            self.assertFalse(relationship["official_or_certified_claim"])

    def test_cross_domain_edges_are_review_context_not_causal_or_certified_claims(self):
        expected_families = {
            "entity_to_source_record",
            "entity_to_candidate_observation",
            "entity_to_watch_item",
            "entity_to_spatial_overlay",
            "entity_to_attribute_assertion",
            "candidate_dependency_context",
            "service_or_asset_context",
        }
        actual_families = {edge["edge_type"] for edge in self.graph["edges"]}
        self.assertEqual(expected_families, actual_families)
        for edge in self.graph["edges"]:
            self.assertTrue(edge["dependency_context_only"])
            self.assertFalse(edge["causal_claim"])
            self.assertFalse(edge["certified_relationship_claim"])
            self.assertFalse(edge["official_dependency_claim"])
            self.assertFalse(edge["cross_city_claim"])
            self.assertIn("certified dependency", edge["cannot_claim"])
        for dep in self.graph["dependency_edges"]:
            self.assertTrue(dep["review_only"])
            self.assertFalse(dep["causal_claim"])
            self.assertFalse(dep["certified_relationship_claim"])

    def test_query_fixtures_return_review_safe_results(self):
        edge_ids = {edge["edge_id"] for edge in self.graph["edges"]}
        self.assertEqual(3, self.queries["query_count"])
        for query in self.queries["queries"]:
            self.assertTrue(query["local_replay_only"])
            self.assertTrue(query["edge_ids"], query["query_id"])
            self.assertTrue(set(query["edge_ids"]).issubset(edge_ids))
            self.assertIn("certified dependency", query["cannot_claim"])
        cer_ref = self.graph["nodes"][0]["ref_id"]
        self.assertTrue(query_graph(self.graph, "edges_for_cer_ref", cer_ref))

    def test_validator_accepts_current_graph_bundle(self):
        validation = validate_graph_bundle(self.graph)
        self.assertEqual("PASS", validation["status"], validation)
        self.assertEqual(len(self.graph["edges"]), validation["cer_anchored_edges"])
        self.assertGreaterEqual(validation["attribute_assertion_edges"], 1)

    def test_no_live_retrieval_production_api_or_llm_source(self):
        source = (ROOT / "scripts" / "run_main_citybrain_push4_lane_b_semantic_graph_v2.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("chat.completions", source)
        self.assertNotIn("fetch(", source)

    def test_hash_manifest_verifies(self):
        report = verify_hash_manifest(OUTPUT_ROOT, "SEMANTIC_GRAPH_V2_HASH_MANIFEST.json")
        self.assertEqual("PASS", report["status"], report)
        self.assertEqual(report["declared"], report["verified"])


if __name__ == "__main__":
    unittest.main()
