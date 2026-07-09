from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_bounded_probe_next_pack_r1.py"

spec = importlib.util.spec_from_file_location("bounded_probe_next_pack", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.TARGETED_ROOT / "PRE_PROBE_TARGETED_FIX_SEQUENCE_DECISION.json").exists():
        runner.build_all()


def test_pre_probe_targeted_fix_sequence_outputs_and_status():
    runner.build_all()
    missing = [runner.rel(runner.TARGETED_ROOT / filename) for filename in runner.TARGETED_FILES if not (runner.TARGETED_ROOT / filename).exists()]
    assert missing == []
    decision = load_json(runner.TARGETED_ROOT / "PRE_PROBE_TARGETED_FIX_SEQUENCE_DECISION.json")
    assert decision["status"] == runner.STATUS_TARGETED
    assert decision["derived_fix_count"] == 50
    assert decision["eval_rerun_case_count"] == 12
    assert decision["eval_rerun_pass_count"] == 12


def test_targeted_fixes_are_derived_candidate_only_and_do_not_mutate_source_truth():
    ensure_outputs()
    selection = load_json(runner.TARGETED_ROOT / "TARGETED_FIX_CANDIDATE_SELECTION_R1.json")
    application = load_json(runner.TARGETED_ROOT / "DERIVED_TARGETED_FIX_APPLICATION_R1.json")
    mutation = load_json(runner.TARGETED_ROOT / "SOURCE_TRUTH_NO_MUTATION_AUDIT.json")
    assert selection["candidate_count_selected"] == 50
    assert selection["selection_policy"].startswith("derived/candidate-only")
    assert application["application_mode"] == "derived_artifact_overlay_only"
    assert application["source_truth_mutated"] is False
    assert all(row["non_authoritative"] is True for row in application["fixes"])
    assert all(row["source_truth_mutated"] is False for row in application["fixes"])
    assert mutation["source_records_mutated"] is False
    assert mutation["source_registry_mutated"] is False
    assert mutation["canonical_truth_mutated"] is False


def test_eval_rerun_covers_twelve_cases_and_no_session_or_fuel_is_created():
    ensure_outputs()
    rerun = load_json(runner.TARGETED_ROOT / "PRODUCT_LOOP_EVAL_RERUN_R2.json")
    readiness = load_json(runner.TARGETED_ROOT / "BOUNDED_PROBE_READINESS_REFRESH_R1.json")
    queue = load_json(runner.TARGETED_ROOT / "FOUNDER_PROBE_TASK_QUEUE_REFRESH_R1.json")
    decision = load_json(runner.TARGETED_ROOT / "PRE_PROBE_TARGETED_FIX_SEQUENCE_DECISION.json")
    assert rerun["case_count"] == 12
    assert rerun["case_pass_count"] == 12
    assert all(case["source_truth_mutated"] is False for case in rerun["cases"])
    assert readiness["founder_session_run"] is False
    assert readiness["operator_fuel_created"] is False
    assert queue["task_count"] == 12
    assert queue["operator_fuel"] is False
    assert queue["training_eligible"] is False
    assert decision["founder_session_run"] is False
    assert decision["training_rows_created"] is False
    assert decision["status"].endswith("WITH_LIMITATIONS")


def test_targeted_hash_manifest_validates():
    ensure_outputs()
    assert runner.verify_manifest(runner.TARGETED_ROOT / "HASH_MANIFEST.json") == []
