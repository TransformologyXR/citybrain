import json
import subprocess
import unittest
from pathlib import Path

from scripts.run_main_citybrain_push5_lane_a_spatial_ui_ux import (
    ASK_CONTRACT_PATHS,
    CLOSEOUT_ROOT,
    CLOSEOUT_STATUS,
    FINAL_ROOT,
    FINAL_STATUS,
    OUTPUT_ROOT,
    PASS_STATUS,
    R7_RUNTIME_PATHS,
    build_outputs,
    verify_hash_manifest_for,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush5LaneASpatialUiUxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs({"runner": "TEST_SETUP"})
        cls.decision = json.loads((OUTPUT_ROOT / "SPATIAL_UI_UX_DECISION.json").read_text(encoding="utf-8"))
        cls.panel = json.loads((OUTPUT_ROOT / "KIT_ENTITY_EVIDENCE_PANEL_VIEW_MODEL.json").read_text(encoding="utf-8"))
        cls.manager = json.loads((OUTPUT_ROOT / "SPATIAL_OVERLAY_MANAGER_MANIFEST.json").read_text(encoding="utf-8"))
        cls.events = json.loads((OUTPUT_ROOT / "SPATIAL_EVENT_OVERLAYS.json").read_text(encoding="utf-8"))
        cls.assertions = json.loads((OUTPUT_ROOT / "SPATIAL_ASSERTION_CONFLICT_OVERLAYS.json").read_text(encoding="utf-8"))
        cls.graph = json.loads((OUTPUT_ROOT / "SPATIAL_GRAPH_EDGE_OVERLAYS.json").read_text(encoding="utf-8"))
        cls.media = json.loads((OUTPUT_ROOT / "SPATIAL_MEDIA_EVIDENCE_OVERLAY_REFS.json").read_text(encoding="utf-8"))
        cls.smoke = json.loads((OUTPUT_ROOT / "SPATIAL_UI_UX_STATIC_SMOKE_REPORT.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "SPATIAL_UI_UX_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "SPATIAL_UI_UX_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        required = [
            "SPATIAL_UI_UX_DECISION.json",
            "SPATIAL_UI_UX_CONTRACT.md",
            "KIT_ENTITY_EVIDENCE_PANEL_VIEW_MODEL.json",
            "SPATIAL_OVERLAY_MANAGER_MANIFEST.json",
            "SPATIAL_EVENT_OVERLAYS.json",
            "SPATIAL_ASSERTION_CONFLICT_OVERLAYS.json",
            "SPATIAL_GRAPH_EDGE_OVERLAYS.json",
            "SPATIAL_MEDIA_EVIDENCE_OVERLAY_REFS.json",
            "SPATIAL_UI_UX_STATIC_SMOKE_REPORT.json",
            "SPATIAL_UI_UX_BOUNDARY_AND_NON_CLAIMS.md",
            "SPATIAL_UI_UX_TEST_LOG.md",
            "SPATIAL_UI_UX_HASH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.decision["status"])

    def test_closeout_and_final_status_exist(self):
        for name in [
            "SPATIAL_UI_UX_CLOSEOUT_DECISION.json",
            "SPATIAL_UI_UX_CLOSEOUT_SUMMARY.md",
            "SPATIAL_UI_UX_CLOSEOUT_LIMITATIONS.md",
            "SPATIAL_UI_UX_CLOSEOUT_NEXT_STEPS.md",
            "SPATIAL_UI_UX_CLOSEOUT_HASH_MANIFEST.json",
        ]:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in [
            "SPATIAL_UI_UX_FINAL_STATUS_DECISION.json",
            "SPATIAL_UI_UX_FINAL_STATUS_SUMMARY.md",
            "SPATIAL_UI_UX_FINAL_STATUS_HASH_MANIFEST.json",
        ]:
            self.assertTrue((FINAL_ROOT / name).exists(), name)
        self.assertEqual(CLOSEOUT_STATUS, self.closeout["status"])
        self.assertEqual(FINAL_STATUS, self.final["status"])

    def test_entity_evidence_panel_view_model_exists(self):
        self.assertEqual("PASS", self.panel["status"])
        self.assertEqual(1, self.panel["panel_count"])
        panel = self.panel["panels"][0]
        self.assertTrue(panel["selected_entity_ref"].startswith("cer:"))
        self.assertTrue(panel["attribute_assertion_refs"])
        self.assertTrue(panel["event_overlay_refs"])
        self.assertTrue(panel["media_evidence_overlay_refs"])
        self.assertTrue(panel["marker_metadata_only"])

    def test_overlay_manager_indexes_event_assertion_and_graph_overlays(self):
        self.assertEqual("PASS", self.manager["status"])
        self.assertGreater(self.manager["indexes"]["event_overlay_count"], 0)
        self.assertGreater(self.manager["indexes"]["assertion_conflict_overlay_count"], 0)
        self.assertGreater(self.manager["indexes"]["graph_edge_overlay_count"], 0)
        self.assertTrue(all(layer["indexed"] for layer in self.manager["layers"]))

    def test_check_v1_reports_and_authority_are_visible(self):
        panel = self.panel["panels"][0]
        self.assertTrue(panel["check_v1_visible"])
        self.assertTrue(panel["check_v1_cards"])
        self.assertTrue(panel["authority_envelope_visible"])
        self.assertTrue(panel["authority_envelope_refs"])
        for card in panel["check_v1_cards"]:
            self.assertTrue(card["check_v1_report_ref"])
            self.assertTrue(card["supporting_evidence_refs"])

    def test_graph_edge_overlays_target_cer_and_graph_ids(self):
        self.assertGreater(self.graph["item_count"], 0)
        for item in self.graph["items"]:
            self.assertTrue(item["graph_edge_ref"].startswith("semantic-graph:"))
            self.assertTrue(item["entity_ref"].startswith("cer:"))
            self.assertTrue(item["cer_alignment"]["graph_edges_target_cer_entity_assertion_ids"])
            self.assertTrue(item["marker_metadata_only"])

    def test_every_spatial_item_preserves_required_fields_and_boundaries(self):
        packets = [self.events, self.assertions, self.graph, self.media]
        required = [
            "entity_ref",
            "attribute_assertion_ref",
            "event_ref",
            "watch_item_ref",
            "graph_edge_ref",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "check_report_ref",
            "authority_envelope_ref",
            "review_state",
            "workflow_state",
            "candidate_only",
            "not_official",
            "marker_metadata_only",
            "live_kit_control",
            "full_citywide_twin_claim",
        ]
        for packet in packets:
            for item in packet["items"]:
                for field in required:
                    self.assertIn(field, item)
                self.assertTrue(item["evidence_refs"])
                self.assertTrue(item["limitation_refs"])
                self.assertTrue(item["trace_refs"])
                self.assertTrue(item["check_report_ref"])
                self.assertTrue(item["authority_envelope_ref"])
                self.assertTrue(item["marker_metadata_only"])
                self.assertFalse(item["live_kit_control"])
                self.assertFalse(item["full_citywide_twin_claim"])
                self.assertFalse(item["official_action_created"])
                self.assertFalse(item["dispatch_control_enforcement_created"])
                self.assertFalse(item["legal_certified_finding_created"])

    def test_static_smoke_passes(self):
        self.assertEqual("PASS", self.smoke["status"])
        for name, value in self.smoke["checks"].items():
            self.assertTrue(value, name)
        self.assertGreater(self.smoke["counts"]["media_evidence_overlay_refs"], 0)

    def test_hash_manifests_verify(self):
        for root, name in [
            (OUTPUT_ROOT, "SPATIAL_UI_UX_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "SPATIAL_UI_UX_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "SPATIAL_UI_UX_FINAL_STATUS_HASH_MANIFEST.json"),
        ]:
            report = verify_hash_manifest_for(root, name)
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])

    def test_no_sealed_ask_or_protected_r7_runtime_diff(self):
        ask = subprocess.run(["git", "diff", "--", *ASK_CONTRACT_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        r7 = subprocess.run(["git", "diff", "--", *R7_RUNTIME_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual("", ask.stdout)
        self.assertEqual("", r7.stdout)


if __name__ == "__main__":
    unittest.main()
