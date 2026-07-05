from __future__ import annotations

import json
import unittest
from pathlib import Path

from packages.event_fabric_r0_1_validator import validator
from scripts import run_main_citybrain_event_fabric_r0_1_contract_delta as runner


class EventFabricR01ContractDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = runner.write_outputs()
        runner.write_closeout(cls.report)
        runner.write_final(cls.report)

    def test_import_map_marks_authoritative_imports(self) -> None:
        imports = runner.import_map_json()["imports"]
        names = {row["imported_shape"] for row in imports}
        self.assertIn("CandidateObservation", names)
        self.assertIn("source_class", names)
        self.assertIn("EvidencePacket/evidence_refs", names)
        self.assertIn("trace_refs", names)
        self.assertIn("CHECK/CheckReport", names)
        self.assertIn("AuthorityEnvelope", names)

    def test_r0_1_owns_only_six_shapes(self) -> None:
        self.assertEqual(
            validator.R0_1_OWNED_SHAPES,
            ["EventEnvelope", "EventTypeRegistry", "ReviewState", "MaterializedReviewState", "QueryResultPacket", "OverlayPacket"],
        )

    def test_valid_fixtures_pass_and_invalid_fixtures_fail(self) -> None:
        report = validator.validate_bundle()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["checks"]["valid_fixtures_pass"])
        self.assertTrue(report["checks"]["invalid_fixtures_fail"])

    def test_vss_cannot_instantiate_candidate_observation(self) -> None:
        invalid = validator.invalid_fixtures()["fixtures"]["invalid_vss_as_candidate_observation"]
        result = validator.validate_packet(invalid["shape"], invalid["packet"])
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("VSS/model narrative cannot instantiate CandidateObservation", result["errors"])

    def test_check_authority_and_schema_version_are_required(self) -> None:
        packet = validator.base_event()
        for field in ["schema_version", "check_report_ref", "check_status", "authority_level", "authority_envelope_ref"]:
            self.assertIn(field, packet)
        bad = {key: value for key, value in packet.items() if key != "schema_version"}
        self.assertEqual(validator.validate_packet("EventEnvelope", bad)["status"], "FAIL")
        bad_check = {**packet, "check_status": "passed", "check_report_ref": None}
        self.assertEqual(validator.validate_packet("EventEnvelope", bad_check)["status"], "FAIL")

    def test_forbidden_boundary_fixtures_reject(self) -> None:
        rows = validator.validate_bundle()["invalid_fixture_report"]["rows"]
        rejected = {row["fixture"]: row for row in rows}
        for name in [
            "invalid_official_violation_confirmed",
            "invalid_case_submitted_officially",
            "invalid_dispatch_or_control_executed",
            "invalid_legal_certified_finding",
            "invalid_overlay_live_kit_control",
            "invalid_raw_query_as_authority",
        ]:
            self.assertEqual(rejected[name]["status"], "FAIL", name)

    def test_required_outputs_exist_and_json_parses(self) -> None:
        required = [
            "EVENT_FABRIC_R0_1_CONTRACT_DELTA_DECISION.json",
            "EVENT_FABRIC_R0_1_IMPORT_MAP.json",
            "EVENT_FABRIC_R0_1_EVENT_ENVELOPE_SCHEMA.json",
            "EVENT_FABRIC_R0_1_EVENT_TYPE_REGISTRY.json",
            "EVENT_FABRIC_R0_1_REVIEW_STATE_SCHEMA.json",
            "EVENT_FABRIC_R0_1_MATERIALIZED_REVIEW_STATE_SCHEMA.json",
            "EVENT_FABRIC_R0_1_QUERY_RESULT_PACKET_SCHEMA.json",
            "EVENT_FABRIC_R0_1_OVERLAY_PACKET_SCHEMA.json",
            "EVENT_FABRIC_R0_1_VALID_FIXTURES.json",
            "EVENT_FABRIC_R0_1_INVALID_FIXTURES.json",
            "EVENT_FABRIC_R0_1_VALIDATOR_REPORT.json",
            "EVENT_FABRIC_R0_1_HASH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((runner.OUTPUT_ROOT / name).exists(), name)
        for path in list(runner.OUTPUT_ROOT.glob("*.json")) + list(runner.CLOSEOUT_ROOT.glob("*.json")) + list(runner.FINAL_ROOT.glob("*.json")):
            json.loads(path.read_text(encoding="utf-8"))

    def test_step2_resume_rules_state_r0_superseded(self) -> None:
        delta = (runner.OUTPUT_ROOT / "EVENT_FABRIC_R0_1_DELTA_FROM_R0.md").read_text(encoding="utf-8")
        resume = (runner.OUTPUT_ROOT / "EVENT_FABRIC_R0_1_STEP2_TRACK_RESUME_RULES.md").read_text(encoding="utf-8")
        self.assertIn("R0 is superseded for Step 2 closeout", delta)
        self.assertIn("Track 1", resume)
        self.assertIn("Track 2", resume)
        self.assertIn("Track 3", resume)


if __name__ == "__main__":
    unittest.main()
