from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_sprint2_event_contract_compatibility_sync.py"
spec = importlib.util.spec_from_file_location("event_contract_sync", SCRIPT)
sync = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(sync)


class Sprint2EventContractCompatibilitySyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.outputs = sync.write_all_outputs()
        cls.report = sync.build_validator_report()

    def test_r0_1_import_map_exists_and_cites_doc05(self) -> None:
        import_map = self.report["import_map"]
        self.assertEqual(import_map["status"], "PASS")
        self.assertTrue(import_map["doc05_present"])
        self.assertGreaterEqual(import_map["doc05_import_refs"], 1)

    def test_shared_r0_1_validator_is_importable_and_passing(self) -> None:
        self.assertTrue(self.report["checks"]["r0_1_validator_importable"])
        self.assertEqual(self.report["shared_r0_1_validator"]["status"], "PASS")

    def test_track2_candidate_event_query_overlay_outputs_validate(self) -> None:
        track2 = self.report["track2"]
        self.assertEqual(track2["status"], "PASS")
        self.assertEqual(track2["candidate_count"], 6)
        self.assertEqual(track2["event_count"], 6)
        self.assertEqual(track2["query_packet_count"], 1)
        self.assertEqual(track2["overlay_packet_count"], 6)

    def test_track3_runtime_accepts_and_materializes_track2_events(self) -> None:
        track3 = self.report["track3"]
        self.assertEqual(track3["status"], "PASS")
        self.assertEqual(track3["track2_events_written"], 6)
        self.assertEqual(track3["materialized_event_count"], 6)

    def test_track1_spatial_surface_consumes_r0_1_query_overlay_packets(self) -> None:
        track1 = self.report["track1"]
        self.assertEqual(track1["status"], "PASS")
        self.assertEqual(track1["query_packet_count"], 8)
        self.assertEqual(track1["overlay_packet_count"], 8)
        self.assertTrue(track1["boundaries_ok"])

    def test_refs_and_boundaries_align_across_tracks(self) -> None:
        checks = self.report["checks"]
        self.assertTrue(checks["evidence_refs_aligned"])
        self.assertTrue(checks["limitation_refs_aligned"])
        self.assertTrue(checks["trace_refs_aligned"])
        self.assertTrue(checks["candidate_review_boundaries_aligned"])
        self.assertTrue(checks["overlay_fields_aligned"])

    def test_vss_not_fact_source_boundary_is_preserved(self) -> None:
        self.assertTrue(self.report["checks"]["vss_not_fact_source_preserved"])
        self.assertEqual(self.report["vss_boundary"]["vss_candidate_observation_result"]["status"], "FAIL")

    def test_required_sync_and_closeout_artifacts_exist(self) -> None:
        required_sync = {
            "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_DECISION.json",
            "SPRINT2_EVENT_CONTRACT_BRANCH_TOPOLOGY.md",
            "SPRINT2_EVENT_CONTRACT_INTEGRATED_COMMIT_MAP.md",
            "SPRINT2_EVENT_CONTRACT_R0_1_STATUS.md",
            "SPRINT2_EVENT_CONTRACT_TRACK_COMPATIBILITY_MATRIX.md",
            "SPRINT2_EVENT_CONTRACT_SOURCE_OF_TRUTH_MATRIX.md",
            "SPRINT2_EVENT_CONTRACT_VALIDATOR_REPORT.json",
            "SPRINT2_EVENT_CONTRACT_UNIFIED_TEST_REPORT.md",
            "SPRINT2_EVENT_CONTRACT_BOUNDARY_AND_NON_CLAIMS.md",
            "SPRINT2_EVENT_CONTRACT_OPEN_GAPS_AND_NEXT_LANES.md",
            "SPRINT2_EVENT_CONTRACT_HASH_MANIFEST.json",
        }
        required_closeout = {
            "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_CLOSEOUT_DECISION.json",
            "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_CLOSEOUT_SUMMARY.md",
            "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_CLOSEOUT_LIMITATIONS.md",
            "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_CLOSEOUT_NEXT_STEPS.md",
            "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_CLOSEOUT_HASH_MANIFEST.json",
        }
        present_sync = {path.name for path in sync.OUTPUT_ROOT.iterdir() if path.is_file()}
        present_closeout = {path.name for path in sync.CLOSEOUT_ROOT.iterdir() if path.is_file()}
        self.assertTrue(required_sync.issubset(present_sync))
        self.assertTrue(required_closeout.issubset(present_closeout))
        self.assertEqual(sync.verify_hash_manifest(sync.OUTPUT_ROOT, "SPRINT2_EVENT_CONTRACT_HASH_MANIFEST.json")["status"], "PASS")
        self.assertEqual(sync.verify_hash_manifest(sync.CLOSEOUT_ROOT, "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_CLOSEOUT_HASH_MANIFEST.json")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
