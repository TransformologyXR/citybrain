from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from scripts.run_epoch3_phase2_live_exposure_coverage_and_hardening_r1 import (
    OUTPUT_ROOT,
    STATUS,
    write_all_outputs,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


class Epoch3Phase2LiveExposureCoverageAndHardeningR1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.decision = cls.result["decision"]
        cls.rows = load_jsonl(OUTPUT_ROOT / "fixtures" / "exposure_events_replay.jsonl")

    def test_decision_status_and_boundaries(self):
        self.assertEqual(STATUS, self.decision["status"], self.decision["blockers"])
        self.assertEqual(0, len(self.decision["blockers"]))
        self.assertIn("L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING", self.decision["armed_now"])
        for blocked in [
            "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
            "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
            "L2.R2_FORECAST_MODEL",
            "L3_COUNTERFACTUAL",
            "L4_CASE_MEMORY",
            "DYNAMIC_INVESTIGATION_AGENT",
            "CROSS_CITY_LEARNED_TRANSFER",
        ]:
            self.assertIn(blocked, self.decision["still_blocked"])

    def test_surfaced_definition_is_payload_inclusion_not_raw_emission(self):
        row = load_json(OUTPUT_ROOT / "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json")
        self.assertEqual("operator_visible_payload_inclusion", row["surfaced_definition"])
        self.assertEqual("operator_visible_payload_items_count", row["denominator"])
        self.assertEqual("watch_service_emitted_candidate_items_count", row["not_denominator"])
        self.assertEqual("new_exposure_event_per_payload_inclusion", row["reexposure_rule"])
        self.assertEqual("per_run_envelope", row["coverage_scope"])
        self.assertEqual("standing_health_vacuous_pass", row["empty_tick_policy"])
        self.assertIn("viewport", row["limitation"])

    def test_reexposure_fixture_uses_new_event_per_payload_inclusion(self):
        asset_rows = [row for row in self.rows if row["watch_item_id"] == "watch:item:asset_state:001"]
        self.assertEqual(2, len(asset_rows))
        self.assertEqual(2, len({row["exposure_id"] for row in asset_rows}))
        self.assertEqual(2, len({row["run_envelope_ref"] for row in asset_rows}))
        self.assertTrue(all(row["reexposure_semantics"] == "new_event_per_payload_inclusion" for row in asset_rows))

    def test_live_coverage_verification_is_per_run_and_non_empty(self):
        report = load_json(OUTPUT_ROOT / "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json")
        self.assertEqual("agent-run:e3-phase2:watch-replay:001", report["watch_run_envelope_ref"])
        self.assertEqual(3, report["operator_visible_payload_items_count"])
        self.assertEqual(3, report["exposure_events_count"])
        self.assertEqual(1.0, report["coverage_ratio"])
        self.assertTrue(report["coverage_passed"])
        self.assertTrue(report["phase2_verification_non_empty_payload"])
        self.assertEqual(0, report["orphan_exposure_events_count"])
        self.assertEqual(0, report["missing_required_field_count"])

    def test_exposure_events_have_required_links_and_payload_metadata(self):
        required = {
            "exposure_id",
            "watch_item_id",
            "run_envelope_ref",
            "surface_kind",
            "surface_policy",
            "surface_reason",
            "operator_visible_payload_ref",
            "payload_position",
            "surfaced_definition",
            "training_eligibility",
        }
        self.assertEqual(len(self.rows), len({row["exposure_id"] for row in self.rows}))
        for row in self.rows:
            self.assertTrue(required.issubset(row))
            self.assertEqual("operator_visible_payload_inclusion", row["surfaced_definition"])
            self.assertEqual("operator_visible_review_payload", row["surface_kind"])

    def test_empty_tick_vacuous_pass_but_not_phase2_verification(self):
        empty_tick = load_json(OUTPUT_ROOT / "fixtures" / "empty_tick_vacuous_pass_fixture.json")
        self.assertEqual(0, empty_tick["operator_visible_payload_items_count"])
        self.assertEqual(0, empty_tick["exposure_events_count"])
        self.assertEqual(1.0, empty_tick["coverage_ratio"])
        self.assertEqual("PASS_VACUOUS_EMPTY_TICK", empty_tick["standing_health_result"])
        self.assertFalse(empty_tick["phase2_verification_eligible"])

    def test_training_eligibility_includes_unverified_exposure_and_excludes_r3(self):
        exposure_schema = load_json(REPO_ROOT / "schemas" / "exposure_event.schema.json")
        outcome_schema = load_json(REPO_ROOT / "schemas" / "outcome_ledger_event.schema.json")
        exposure_reasons = exposure_schema["properties"]["training_eligibility"]["properties"]["reason"]["enum"]
        outcome_reasons = outcome_schema["properties"]["training_eligibility"]["properties"]["reason"]["enum"]
        self.assertIn("unverified_exposure", exposure_reasons)
        self.assertIn("unverified_exposure", outcome_reasons)
        unverified_rows = [
            row for row in self.rows if row["training_eligibility"]["reason"] == "unverified_exposure"
        ]
        self.assertTrue(unverified_rows)
        self.assertTrue(all(not row["training_eligibility"]["eligible_for_r3_fuel"] for row in unverified_rows))

        outcome = load_json(OUTPUT_ROOT / "E3_OUTCOME_LEDGER_HARDENING_START_REPORT.json")
        self.assertTrue(outcome["eligibility_rules"]["requires_verified_exposure_linkage"])
        self.assertTrue(outcome["eligibility_rules"]["unverified_exposure_excluded_from_r3_fuel"])
        self.assertEqual(0, outcome["eligible_terminal_dispositions"])
        self.assertFalse(outcome["true_learning_fuel_claimed"])

    def test_scheduled_tick_pending_has_overdue_watcher(self):
        row = load_json(OUTPUT_ROOT / "E3_SCHEDULED_TICK_EXPOSURE_VERIFICATION_ROW.json")
        self.assertIn(row["status"], {"PASS_FIRST_SCHEDULED_TICK_VERIFIED", "PENDING_FIRST_SCHEDULED_TICK"})
        self.assertEqual("E3.ARMING_STATUS_WATCH_FAMILY / Watch service owner", row["owner"])
        self.assertTrue(row["arming_status_watch_item_on_overdue"])
        self.assertEqual("E3.ARMING_STATUS_WATCH_FAMILY", row["overdue_watcher"]["component_id"])
        self.assertEqual("review_backlog", row["review_item_family"])

    def test_watch_service_delta_is_additive(self):
        row = load_json(OUTPUT_ROOT / "E3_WATCH_SERVICE_COVERAGE_CRITERION_DELTA_ROW.json")
        self.assertEqual("additive_health_and_closeout_criterion", row["delta_kind"])
        self.assertEqual("Epoch2.2 Watch service", row["target_service"])
        self.assertIn("exposure coverage per operator-visible payload", row["change"]["add_health_criterion"])
        self.assertTrue(row["change"]["phase2_verification_requires_non_empty_payload"])
        self.assertIn("not a silent edit", row["reason"])

    def test_corpus_delta_registers_coverage_fixture_and_frozen_artifacts(self):
        row = load_json(OUTPUT_ROOT / "E3_PHASE2_CORPUS_DELTA.json")
        self.assertEqual("coverage_regression_append", row["delta_kind"])
        for required in [
            "fixtures/watch_run_envelope_replay.json",
            "fixtures/operator_visible_payload_replay.json",
            "fixtures/exposure_events_replay.jsonl",
            "fixtures/reexposure_run_envelope_002.json",
            "fixtures/operator_visible_payload_reexposure_002.json",
            "fixtures/empty_tick_vacuous_pass_fixture.json",
        ]:
            self.assertIn(required, row["fixtures_added"])
            self.assertTrue((OUTPUT_ROOT / required).exists())
        self.assertIn("E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json", row["frozen_artifacts_added"])

    def test_holdout_rationale_and_second_holdout_rule(self):
        row = load_json(OUTPUT_ROOT / "E3_HOLDOUT_FAMILY_RATIONALE_ROW.json")
        self.assertEqual("media_candidate", row["holdout_family"])
        self.assertIn("perception-heavy", row["rationale"])
        self.assertIn("non-perception", row["future_rule_before_r3b"])

    def test_no_model_guard_and_template(self):
        template = load_json(OUTPUT_ROOT / "E3_STANDING_NO_MODEL_GUARD_TEMPLATE.json")
        guard = load_json(OUTPUT_ROOT / "E3_NO_MODEL_GUARD_REPORT.json")
        self.assertEqual(0, template["pre_r3a_invariant"]["new_learned_component_registry_entries"])
        self.assertEqual([], template["post_r3a_allowed_shape"]["consuming_surfaces"])
        self.assertIsNone(template["post_r3a_allowed_shape"]["release_ledger_row"])
        self.assertEqual("PASS", guard["status"])
        self.assertEqual([], guard["violations"])
        self.assertEqual([], guard["pre_r3a_invariant"]["forbidden_capabilities_armed"])

    def test_fuel_snapshot_is_first_chained_snapshot(self):
        snap = load_json(OUTPUT_ROOT / "E3_FUEL_GAUGE_DELTA_SNAPSHOT.json")
        self.assertEqual("fuel-snapshot:e3:phase2:r1:0001", snap["snapshot_id"])
        self.assertIsNone(snap["previous_snapshot_ref"])
        self.assertEqual("E3.ARMING_STATUS_WATCH_FAMILY", snap["emitter"])
        self.assertEqual("NOT_ARMED", snap["arming_status"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"])
        self.assertEqual(1, snap["metrics"]["unverified_exposure_exclusions"])
        self.assertEqual(1, snap["metrics"]["propensity_unknown_exclusions"])

    def test_reconciliation_citations_present(self):
        decision = load_json(OUTPUT_ROOT / "E3_PHASE2_LIVE_EXPOSURE_COVERAGE_DECISION.json")
        refs = "\n".join(decision["source_refs"])
        self.assertIn("E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json", refs)
        self.assertIn("E3_ARMING_REQUIREMENT_AUDIT_REPORT.json", refs)
        self.assertIn("E3_DAY1_DECISION.json", refs)

    def test_calibration_remains_descriptive(self):
        row = load_json(OUTPUT_ROOT / "E3_CALIBRATION_HARDENING_START_REPORT.json")
        self.assertEqual(0, row["sample_depth"])
        self.assertFalse(row["true_calibration_claimed"])
        self.assertTrue(row["descriptive_only"])

    def test_hash_manifest_verifies(self):
        manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
        self.assertTrue(manifest["files"])
        for row in manifest["files"]:
            path = REPO_ROOT / row["path"]
            data = path.read_bytes()
            self.assertEqual(row["bytes"], len(data))
            self.assertEqual(row["sha256"], hashlib.sha256(data).hexdigest())

    def test_lf_report_has_no_crlf_paths(self):
        report = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")
        self.assertEqual("PASS_LF_STABLE_FOR_E3_PHASE2_PUBLICATION", report["status"])
        self.assertEqual([], report["crlf_paths"])
        for path in OUTPUT_ROOT.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"\r\n", path.read_bytes(), path)


if __name__ == "__main__":
    unittest.main()
