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
    if not (runner.PROBE_ROOT / "BOUNDED_FOUNDER_PROBE_SESSION_DECISION.json").exists():
        runner.build_all()


def test_bounded_probe_package_outputs_and_no_fabricated_session_results():
    runner.build_all()
    missing = [runner.rel(runner.PROBE_ROOT / filename) for filename in runner.PROBE_FILES if not (runner.PROBE_ROOT / filename).exists()]
    assert missing == []
    decision = load_json(runner.PROBE_ROOT / "BOUNDED_FOUNDER_PROBE_SESSION_DECISION.json")
    no_capture = load_json(runner.PROBE_ROOT / "NO_FOUNDER_SESSION_CAPTURED_R1.json")
    assert decision["status"] == runner.STATUS_PROBE_NO_SESSION
    assert decision["session_status"] == "NOT_RUN"
    assert decision["session_record_count"] == 0
    assert decision["fabricated_session_results_created"] is False
    assert no_capture["session_status"] == "NOT_RUN"
    assert no_capture["fabricated_session_results_created"] is False


def test_probe_task_queue_and_records_are_founder_internal_when_present():
    ensure_outputs()
    queue = load_json(runner.PROBE_ROOT / "BOUNDED_FOUNDER_PROBE_TASK_QUEUE_R1.json")
    feedback = load_json(runner.PROBE_ROOT / "FOUNDER_INTERNAL_FEEDBACK_REPORT_R1.json")
    assert queue["reviewer_type"] == "founder_internal"
    assert queue["task_count"] == 12
    assert queue["external_operator_validation"] is False
    assert queue["operator_fuel"] is False
    assert queue["training_eligible"] is False
    assert queue["learning_arming_allowed"] is False
    assert feedback["reviewer_type"] == "founder_internal"
    assert feedback["session_status"] == "NOT_RUN"
    assert feedback["record_count"] == 0


def test_probe_fuel_training_arming_and_official_action_guards():
    ensure_outputs()
    fuel = load_json(runner.PROBE_ROOT / "NO_OPERATOR_FUEL_GUARD_R1.json")
    training = load_json(runner.PROBE_ROOT / "NO_TRAINING_ROWS_GUARD_R1.json")
    arming = load_json(runner.PROBE_ROOT / "NO_LEARNED_ARMING_GUARD_R1.json")
    decision = load_json(runner.PROBE_ROOT / "BOUNDED_FOUNDER_PROBE_SESSION_DECISION.json")
    assert fuel["operator_fuel"] is False
    assert fuel["external_operator_validation"] is False
    assert training["training_rows_created"] is False
    assert training["training_eligible"] is False
    assert arming["learning_arming_allowed"] is False
    assert arming["learned_ranking_activated"] is False
    assert decision["operator_fuel"] is False
    assert decision["training_eligible"] is False
    assert decision["learning_arming_allowed"] is False
    assert decision["forbidden_capabilities_created"] == []


def test_probe_hash_manifest_validates():
    ensure_outputs()
    assert runner.verify_manifest(runner.PROBE_ROOT / "HASH_MANIFEST.json") == []
