import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.run_main_citybrain_push5_lane_b_perception_media_evidence import (
    APPROVED_SOURCE_CLASSES,
    CLOSEOUT_ROOT,
    FINAL_STATUS,
    FINAL_STATUS_ROOT,
    OUTPUT_ROOT,
    PASS_STATUS,
    REQUIRED_OUTPUT_FILES,
    SUFFICIENCY_STATUSES,
    verify_hash_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush5LaneBPerceptionMediaEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, "scripts/run_main_citybrain_push5_lane_b_perception_media_evidence.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        cls.decision = json.loads((OUTPUT_ROOT / "PERCEPTION_MEDIA_EVIDENCE_DECISION.json").read_text(encoding="utf-8"))
        cls.registry = json.loads((OUTPUT_ROOT / "PERCEPTION_SOURCE_REGISTRY_EXPANSION.json").read_text(encoding="utf-8"))
        cls.contract = json.loads((OUTPUT_ROOT / "MEDIA_EVIDENCE_BUNDLE_CONTRACT.json").read_text(encoding="utf-8"))
        cls.bundles = json.loads((OUTPUT_ROOT / "MEDIA_EVIDENCE_BUNDLES.json").read_text(encoding="utf-8"))
        cls.replay = json.loads((OUTPUT_ROOT / "PERCEPTION_REPLAY_SAMPLE_EXPANSION.json").read_text(encoding="utf-8"))
        cls.sufficiency = json.loads((OUTPUT_ROOT / "DETECTION_SUFFICIENCY_REPORTS.json").read_text(encoding="utf-8"))
        cls.vss = json.loads((OUTPUT_ROOT / "VSS_NARRATIVE_SIDECAR_REPORT.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "PERCEPTION_MEDIA_EVIDENCE_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final_status = json.loads((FINAL_STATUS_ROOT / "PERCEPTION_MEDIA_EVIDENCE_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_artifacts_exist(self):
        for name in REQUIRED_OUTPUT_FILES:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertEqual("PASS", self.decision["required_output_status"]["status"])
        self.assertEqual(PASS_STATUS, self.closeout["status"])
        self.assertEqual(FINAL_STATUS, self.final_status["status"])

    def test_push4_gate_is_green(self):
        gate = self.decision["push4_gate"]
        self.assertEqual("PASS", gate["status"])
        checks = gate["checks"]
        self.assertTrue(checks["cer_engine_exists"])
        self.assertTrue(checks["semantic_graph_v2_exists"])
        self.assertTrue(checks["semantic_graph_has_cer_refs"])
        self.assertTrue(checks["check_v1_reports_exist"])
        self.assertTrue(checks["check_v1_consumes_cer"])
        self.assertTrue(checks["contradiction_detection_available"])

    def test_source_registry_expands_without_invalid_source_class(self):
        self.assertEqual("PASS", self.registry["status"])
        self.assertGreater(self.registry["new_source_count"], 0)
        self.assertGreater(self.registry["total_source_count"], self.registry["base_source_count"])
        self.assertFalse(self.registry["invalid_source_class_refs"])
        for source in self.registry["sources"]:
            self.assertIn(source["source_class"], APPROVED_SOURCE_CLASSES)
            self.assertTrue(source["candidate_only"])
            self.assertFalse(source["fact_source"])
            self.assertFalse(source["live_camera"])
            self.assertFalse(source["production_api"])
            self.assertFalse(source["url_fetch"])
            self.assertFalse(source["vss_as_fact_source"])
            self.assertFalse(source["raw_media_dump"])

    def test_media_bundle_contract_and_refs(self):
        for field in [
            "media_bundle_id",
            "source_class",
            "source_ref",
            "media_refs",
            "frame_refs",
            "derived_candidate_observation_refs",
            "vss_narrative_sidecar_refs",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "check_report_ref",
            "authority_envelope_ref",
            "freshness_status",
            "detection_sufficiency_status",
            "cannot_claim",
        ]:
            self.assertIn(field, self.contract["required"])
        self.assertEqual("PASS", self.bundles["status"])
        self.assertGreaterEqual(self.bundles["bundle_count"], 8)
        for bundle in self.bundles["bundles"]:
            self.assertIn(bundle["source_class"], APPROVED_SOURCE_CLASSES)
            self.assertTrue(bundle["media_refs"])
            self.assertTrue(bundle["frame_refs"])
            self.assertTrue(bundle["evidence_refs"])
            self.assertTrue(bundle["limitation_refs"])
            self.assertTrue(bundle["trace_refs"])
            self.assertTrue(bundle["check_report_ref"])
            self.assertTrue(bundle["authority_envelope_ref"])
            self.assertIn(bundle["detection_sufficiency_status"], SUFFICIENCY_STATUSES)
            self.assertTrue(bundle["candidate_only"])
            self.assertFalse(bundle["official_detection"])
            self.assertFalse(bundle["official_violation"])
            self.assertFalse(bundle["legal_certified_finding"])
            self.assertFalse(bundle["raw_media_dump"])

    def test_replay_sample_expansion_goes_beyond_initial_six(self):
        self.assertEqual("PASS", self.replay["status"])
        self.assertEqual(6, self.replay["base_samples"])
        self.assertGreater(self.replay["expanded_samples"], 6)
        self.assertFalse(self.replay["invalid_source_class_sample_ids"])
        self.assertFalse(self.replay["raw_media_dump_sample_ids"])
        for sample in self.replay["samples"]:
            self.assertIn(sample["source_class"], APPROVED_SOURCE_CLASSES)
            self.assertTrue(sample["candidate_only"])
            self.assertFalse(sample["live_camera"])
            self.assertFalse(sample["production_api"])
            self.assertFalse(sample["url_fetch"])
            self.assertFalse(sample["raw_media_dump"])

    def test_vss_sidecars_cannot_create_observations_or_facts(self):
        self.assertEqual("PASS", self.vss["status"])
        self.assertTrue(self.vss["vss_not_fact_source"])
        self.assertGreaterEqual(self.vss["sidecar_count"], 1)
        for sidecar in self.vss["sidecars"]:
            self.assertEqual("model_generated_narrative_not_fact_source", sidecar["source_class"])
            self.assertFalse(sidecar["fact_source"])
            self.assertFalse(sidecar["vss_as_fact_source"])
            self.assertFalse(sidecar["official_detection"])
            self.assertEqual([], sidecar["derived_candidate_observation_refs"])
            self.assertEqual([], sidecar["candidate_observation_refs_created"])
            self.assertEqual([], sidecar["fact_refs_created"])
            self.assertTrue(sidecar["blocked_by_boundary"])

    def test_sensor_inferred_remains_candidate_only(self):
        sensor_sources = [row for row in self.registry["sources"] if row["source_class"] == "sensor_inferred"]
        self.assertTrue(sensor_sources)
        for source in sensor_sources:
            self.assertTrue(source["candidate_only"])
            self.assertFalse(source["fact_source"])
            self.assertFalse(source["official_detection"])
        sensor_bundles = [row for row in self.bundles["bundles"] if row["source_class"] == "sensor_inferred"]
        self.assertTrue(sensor_bundles)
        for bundle in sensor_bundles:
            self.assertTrue(bundle["candidate_only"])
            self.assertFalse(bundle["official_detection"])
            self.assertIn("official detection", bundle["cannot_claim"])

    def test_detection_sufficiency_reports_are_review_only(self):
        self.assertEqual("PASS", self.sufficiency["status"])
        emitted_statuses = {row["detection_sufficiency_status"] for row in self.sufficiency["reports"]}
        self.assertTrue(emitted_statuses.issubset(SUFFICIENCY_STATUSES))
        self.assertTrue(
            {
                "sufficient_for_review_prompt",
                "insufficient_context",
                "stale_media",
                "low_confidence",
                "source_class_not_authoritative",
                "narrative_only_not_detection",
                "blocked_by_boundary",
            }.issubset(emitted_statuses)
        )
        for report in self.sufficiency["reports"]:
            self.assertTrue(report["candidate_only"])
            self.assertTrue(report["review_required"])
            self.assertFalse(report["official_detection"])
            self.assertFalse(report["official_violation"])
            self.assertFalse(report["legal_certified_finding"])
            self.assertFalse(report["dispatch_control_enforcement"])

    def test_no_live_camera_api_url_llm_or_raw_media_dump(self):
        source = (ROOT / "scripts" / "run_main_citybrain_push5_lane_b_perception_media_evidence.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("fetch(", source)
        output_files = [path for path in OUTPUT_ROOT.rglob("*") if path.is_file()]
        forbidden_suffixes = {".mp4", ".mov", ".avi", ".mkv", ".jpg", ".jpeg", ".png", ".webp"}
        self.assertFalse([path.name for path in output_files if path.suffix.lower() in forbidden_suffixes])

    def test_hash_manifests_verify(self):
        reports = [
            verify_hash_manifest(OUTPUT_ROOT, "PERCEPTION_MEDIA_HASH_MANIFEST.json"),
            verify_hash_manifest(CLOSEOUT_ROOT, "PERCEPTION_MEDIA_EVIDENCE_CLOSEOUT_HASH_MANIFEST.json"),
            verify_hash_manifest(FINAL_STATUS_ROOT, "PERCEPTION_MEDIA_EVIDENCE_FINAL_STATUS_HASH_MANIFEST.json"),
        ]
        for report in reports:
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])


if __name__ == "__main__":
    unittest.main()
