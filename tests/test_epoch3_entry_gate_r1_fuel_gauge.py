import json
import unittest
from pathlib import Path

from scripts.evaluate_arming_status import evaluate
from scripts.run_epoch3_entry_gate_r1_fuel_gauge import (
    DAY_ONE_ARMED,
    NOT_ARMED_INITIAL,
    OUTPUT_ROOT,
    REQUIRED_OUTPUTS,
    STATUS,
    sha256_file,
    write_all_outputs,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "manifests" / "epoch3_arming_manifest.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def flatten_requirements(obj):
    if isinstance(obj, dict):
        if {"id", "metric", "op"}.issubset(obj.keys()):
            yield obj
        for value in obj.values():
            yield from flatten_requirements(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from flatten_requirements(item)


class Epoch3EntryGateR1FuelGaugeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.decision = cls.result["decision"]
        cls.report = cls.result["arming_status_report"]
        cls.metrics = cls.result["baseline_metrics"]
        cls.manifest = load_json(MANIFEST_PATH)

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_gate_status_and_atomic_publication(self):
        self.assertEqual(STATUS, self.decision["status"], self.decision["blockers"])
        self.assertEqual("MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE", self.decision["gate_id"])
        self.assertEqual("epoch3_arming_status", self.decision["evaluator_id"])
        publication = self.decision["atomic_publication"]
        self.assertEqual("PASS", publication["status"])
        for key in ["report_ref", "arming_manifest_ref", "evaluator_ref", "hash_manifest_ref", "ledger_row_ref"]:
            self.assertTrue(publication[key], key)

    def test_day_one_armed_and_blocked_sets(self):
        self.assertEqual(DAY_ONE_ARMED, set(self.report["armed_now"]))
        self.assertTrue(NOT_ARMED_INITIAL.issubset(set(self.report["not_armed"])))
        self.assertEqual("not_armed", self.report["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["state"])
        self.assertEqual("not_armed", self.report["conditionally_armed"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["state"])
        self.assertEqual("not_armed", self.report["conditionally_armed"]["L2.R2_FORECAST_MODEL"]["state"])
        self.assertEqual("not_armed", self.report["blocked_until"]["L3_COUNTERFACTUAL"]["state"])
        self.assertEqual("not_armed", self.report["blocked_until"]["L4_CASE_MEMORY"]["state"])

    def test_metrics_reconcile_training_fuel_from_watch_service_readiness(self):
        self.assertEqual(0, self.metrics["outcome"]["terminal_dispositions"]["count"])
        self.assertEqual(0, self.metrics["outcome"]["operator_refs"]["distinct_count"])
        self.assertEqual(0, self.metrics["watch"]["families"]["eligible_training_fuel_count"])
        self.assertGreaterEqual(self.metrics["watch"]["families"]["distinct_count"], 3)
        self.assertIn("traffic_flow", self.metrics["watch"]["families"]["emitted_in_watch_service"])
        self.assertEqual(2, self.metrics["watch"]["historical_disposition_events_seen"])

        reconciliation = load_json(OUTPUT_ROOT / "E3_METRICS_RECONCILIATION_REPORT.json")
        self.assertEqual("PASS_RECONCILED_WITH_LIMITATIONS", reconciliation["status"])
        self.assertTrue(
            any(row["id"] == "E3_METRIC_RECONCILE_LABEL_FUEL_VS_WATCH_SERVICE_FAMILIES"
                for row in reconciliation["reconciliations"])
        )

    def test_policy_fixture_enforcement_is_split_from_floor_satisfaction(self):
        self.assertTrue(self.metrics["policy"]["case_retention"]["enforced"])
        self.assertTrue(self.metrics["policy"]["right_to_forget_or_delete_path"]["enforced"])
        self.assertFalse(self.metrics["policy"]["case_retention"]["runtime_case_artifact_enforced"])
        self.assertFalse(self.metrics["policy"]["right_to_forget_or_delete_path"]["production_erasure_workflow"])
        self.assertTrue(self.metrics["operator_data"]["aggregation_floor"]["policy_enforced"])
        self.assertFalse(self.metrics["operator_data"]["aggregation_floor"]["satisfied"])

        row = load_json(OUTPUT_ROOT / "E3_POLICY_AND_AGGREGATION_RECONCILIATION_ROW.json")
        self.assertEqual("PASS_RECONCILED_WITH_LIMITATIONS", row["status"])
        self.assertTrue(row["metrics"]["operator_data.aggregation_floor.policy_enforced"])
        self.assertFalse(row["metrics"]["operator_data.aggregation_floor.satisfied"])

    def test_corpus_scope_is_focused_not_full_discovery(self):
        row = load_json(OUTPUT_ROOT / "E3_CORPUS_SCOPE_RECONCILIATION_ROW.json")
        self.assertEqual(16, row["fixture_count"])
        self.assertFalse(row["full_corpus_greenness_claimed"])
        self.assertEqual("NOT_RUN_FOR_THIS_GATE", row["full_historical_discovery"]["status"])
        self.assertEqual("NOT_RUN_FOR_THIS_GATE", row["full_discovery"]["status"])
        self.assertEqual("E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json", row["track0_debt_row_ref"])

    def test_all_requirements_are_machine_evaluable(self):
        for group in ["conditionally_armed", "blocked_until"]:
            for block in self.manifest[group].values():
                for req in block["requires"]:
                    self.assertIsInstance(req, dict)
                    self.assertTrue({"id", "metric", "op", "value"}.issubset(req))
                    self.assertIn(req["op"], {"==", "!=", ">=", ">", "<=", "<", "contains_all", "exists", "not_exists"})

    def test_loop_numbering_is_correct(self):
        self.assertEqual("causal / counterfactual", self.manifest["loop_crosswalk"]["L3"])
        self.assertEqual("institutional memory", self.manifest["loop_crosswalk"]["L4"])
        self.assertIn("L3_COUNTERFACTUAL", self.manifest["blocked_until"])
        self.assertIn("L4_CASE_MEMORY", self.manifest["blocked_until"])

    def test_reference_fixture_expectations(self):
        fixtures = REPO_ROOT / "fixtures"
        day_one = evaluate(self.manifest, load_json(fixtures / "metrics_day_one.json"))
        r3a = evaluate(self.manifest, load_json(fixtures / "metrics_pass_l1_r3a.json"), previous=day_one)
        r3b = evaluate(self.manifest, load_json(fixtures / "metrics_pass_l1_r3b.json"))
        operator_fail = evaluate(self.manifest, load_json(fixtures / "metrics_fail_operator_diversity.json"))
        propensity_fail = evaluate(self.manifest, load_json(fixtures / "metrics_fail_propensity_unknown.json"))

        self.assertEqual("not_armed", day_one["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["state"])
        self.assertEqual("armed", r3a["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["state"])
        self.assertEqual("not_armed", r3a["conditionally_armed"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["state"])
        self.assertEqual("armed", r3b["conditionally_armed"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["state"])
        self.assertEqual("L1.R3A_OFFLINE_RANKER_EXPERIMENT", r3a["threshold_crossings"][0]["increment_id"])
        self.assertFalse(r3a["threshold_crossings"][0]["auto_started_work"])

        self.assertIn(
            "R3B_OPERATOR_DIVERSITY",
            operator_fail["conditionally_armed"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["failed_requirement_ids"],
        )
        self.assertIn(
            "R3A_TOTAL_DISPOSITIONS",
            propensity_fail["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["failed_requirement_ids"],
        )

    def test_e2_2_label_fuel_reconciliation_row_is_explicitly_limited(self):
        row = load_json(OUTPUT_ROOT / "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json")
        self.assertEqual("PASS_RECONCILED", row["status"])
        self.assertEqual("EXPLICITLY_LIMITED", row["e2_2_label_fuel_claim_type"])
        self.assertIsNone(row["retroactive_limitation_row_ref"])
        self.assertEqual(0, row["e3_reconciled_metrics"]["terminal_dispositions"])
        self.assertEqual(2, row["e3_reconciled_metrics"]["historical_disposition_events_seen"])
        self.assertFalse((OUTPUT_ROOT / "E2_2_RETROACTIVE_LABEL_FUEL_LIMITATION_ROW.json").exists())

    def test_l4_case_memory_does_not_arm_on_fixture_policy_only(self):
        fixture = load_json(REPO_ROOT / "fixtures" / "metrics_l4_fixture_policy_true_runtime_false.json")
        report = evaluate(self.manifest, fixture)
        l4 = report["blocked_until"]["L4_CASE_MEMORY"]
        self.assertEqual("not_armed", l4["state"])
        self.assertFalse(l4["passed"])
        failed = set(l4["failed_requirement_ids"])
        self.assertIn("L4_CASE_RETENTION_RUNTIME", failed)
        self.assertIn("L4_DELETE_PATH_RUNTIME", failed)
        self.assertNotIn("L4_CASE_RETENTION", failed)
        self.assertNotIn("L4_DELETE_PATH", failed)

    def test_arming_manifest_no_legacy_l4_fixture_policy_paths(self):
        l4_reqs = self.manifest["blocked_until"]["L4_CASE_MEMORY"]["requires"]
        l4_metrics = {req["metric"] for req in l4_reqs}
        self.assertNotIn("policy.case_retention.enforced", l4_metrics)
        self.assertNotIn("policy.right_to_forget_or_delete_path.enforced", l4_metrics)
        self.assertIn("policy.case_retention.runtime_case_artifact_enforced", l4_metrics)
        self.assertIn("policy.right_to_forget_or_delete_path.production_erasure_workflow", l4_metrics)

    def test_r3a_requires_full_corpus_discovery_green(self):
        current = self.report["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]
        reqs = {req["id"]: req for req in current["requirements"]}
        self.assertEqual("corpus.full_discovery.status", reqs["R3A_FULL_CORPUS_DISCOVERY_GREEN"]["metric"])
        self.assertEqual("green", reqs["R3A_FULL_CORPUS_DISCOVERY_GREEN"]["expected"])
        self.assertIn("R3A_FULL_CORPUS_DISCOVERY_GREEN", current["failed_requirement_ids"])

        fixture = load_json(REPO_ROOT / "fixtures" / "metrics_r3a_all_ready_except_full_corpus_not_green.json")
        report = evaluate(self.manifest, fixture)
        r3a = report["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]
        self.assertEqual("not_armed", r3a["state"])
        self.assertEqual(["R3A_FULL_CORPUS_DISCOVERY_GREEN"], r3a["failed_requirement_ids"])

    def test_aggregation_floor_arming_uses_current_sample_satisfaction(self):
        reqs = list(flatten_requirements(self.manifest))
        sample_gate_ids = {"R3B_AGGREGATION_FLOOR", "L4_AGGREGATION_FLOOR_CURRENT"}
        relevant = [req for req in reqs if req.get("id") in sample_gate_ids]
        self.assertTrue(relevant)
        for req in relevant:
            self.assertEqual("operator_data.aggregation_floor.satisfied", req["metric"])

    def test_track0_debt_and_arming_audit_are_published(self):
        debt = load_json(OUTPUT_ROOT / "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json")
        self.assertEqual("OPEN", debt["status"])
        self.assertEqual("Track 0 / regression corpus owner", debt["owner"])
        self.assertEqual("before L1.R3A_OFFLINE_RANKER_EXPERIMENT may arm", debt["deadline"])
        self.assertIn("L1.R3A_OFFLINE_RANKER_EXPERIMENT", debt["blocks"])
        self.assertEqual("corpus.full_discovery.status", debt["required_exit"]["metric"])
        self.assertEqual("green", debt["required_exit"]["expected"])

        audit = load_json(OUTPUT_ROOT / "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json")
        self.assertEqual("PASS", audit["status"])
        self.assertTrue(audit["checks"]["legacy_l4_fixture_policy_paths_removed"])
        self.assertTrue(audit["checks"]["r3a_full_corpus_discovery_green_required"])
        self.assertIn(
            "R3A_FULL_CORPUS_DISCOVERY_GREEN",
            audit["current_failed_requirement_ids"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"],
        )
        self.assertIn("L4_CASE_RETENTION_RUNTIME", audit["current_failed_requirement_ids"]["L4_CASE_MEMORY"])
        self.assertIn("L4_DELETE_PATH_RUNTIME", audit["current_failed_requirement_ids"]["L4_CASE_MEMORY"])

    def test_learned_component_registry_example_is_offline_only(self):
        examples = load_json(OUTPUT_ROOT / "E3_LEARNED_COMPONENT_REGISTRY_EXPERIMENTAL_EXAMPLES.json")
        rankers = [row for row in examples["examples"] if row["component_kind"] == "ranker"]
        self.assertTrue(rankers)
        for row in rankers:
            self.assertEqual("experimental", row["status"])
            self.assertEqual([], row["consuming_surfaces"])
            self.assertEqual("offline_eval_only", row["authority"])

    def test_exposure_log_sample_marks_unknown_legacy_records(self):
        lines = (REPO_ROOT / "fixtures" / "exposure_log_sample.jsonl").read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line.strip()]
        self.assertTrue(any(row["propensity_status"] == "known" for row in rows))
        self.assertTrue(any(row["propensity_status"] == "propensity_unknown" for row in rows))

    def test_no_forbidden_claims_or_loop_drift(self):
        for value in self.decision["non_claims"].values():
            self.assertFalse(value)
        scanned_roots = [REPO_ROOT / "manifests", REPO_ROOT / "schemas", REPO_ROOT / "specs", OUTPUT_ROOT]
        offenders = []
        forbidden = "L3_CASE_MEMORY" + "_LEARNING"
        for root in scanned_roots:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix in {".json", ".md", ".yaml", ".yml", ".py", ".txt"}:
                    if forbidden in path.read_text(encoding="utf-8", errors="ignore"):
                        offenders.append(str(path.relative_to(REPO_ROOT)))
        self.assertEqual([], offenders)

    def test_hash_manifest_matches_outputs(self):
        manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
        self.assertEqual(len(REQUIRED_OUTPUTS) - 1, len(manifest["files"]))
        for row in manifest["files"]:
            path = REPO_ROOT / row["path"]
            self.assertTrue(path.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(path))

    def test_line_ending_stability_report_is_published(self):
        report = load_json(OUTPUT_ROOT / "E3_HASH_LINE_ENDING_STABILITY_REPORT.json")
        self.assertTrue(report["gitattributes_present"])
        self.assertFalse(report["commit_performed"])
        self.assertEqual([], report["crlf_paths"])


if __name__ == "__main__":
    unittest.main()
