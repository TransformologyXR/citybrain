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
    if not (runner.FINAL_ROOT / "PRE_PROBE_FINAL_REVERIFY_DECISION.json").exists():
        runner.build_all()


def test_pre_probe_final_reverify_outputs_and_status():
    runner.build_all()
    missing = [runner.rel(runner.FINAL_ROOT / filename) for filename in runner.FINAL_FILES if not (runner.FINAL_ROOT / filename).exists()]
    assert missing == []
    decision = load_json(runner.FINAL_ROOT / "PRE_PROBE_FINAL_REVERIFY_DECISION.json")
    assert decision["status"] == runner.STATUS_FINAL
    assert decision["active_path"] == "no_session_path"
    assert decision["eval_rerun_case_count"] == 12
    assert decision["eval_rerun_pass_count"] == 12


def test_final_reverify_confirms_targeted_fixes_eval_and_session_labels():
    ensure_outputs()
    targeted = load_json(runner.FINAL_ROOT / "PRE_PROBE_TARGETED_FIX_REVERIFY_R1.json")
    rerun = load_json(runner.FINAL_ROOT / "EVAL_RERUN_REVERIFY_R1.json")
    session = load_json(runner.FINAL_ROOT / "FOUNDER_SESSION_LABEL_REVERIFY_R1.json")
    current = load_json(runner.FINAL_ROOT / "CURRENT_STATE_AFTER_PRE_PROBE_R1.json")
    assert targeted["targeted_fixes_are_derived_candidate_only"] is True
    assert targeted["source_truth_mutated"] is False
    assert rerun["case_count"] == 12
    assert rerun["case_pass_count"] == 12
    assert rerun["failures_are_blockers"] is False
    assert session["active_path"] == "no_session_path"
    assert session["reviewer_type"] == "founder_internal"
    assert session["operator_fuel"] is False
    assert session["training_eligible"] is False
    assert current["bounded_founder_probe_package_run"] is True
    assert current["source_truth_mutated"] is False


def test_final_reverify_forbidden_capability_guard_and_validate_all():
    ensure_outputs()
    guard = load_json(runner.FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD_R1.json")
    decision = load_json(runner.FINAL_ROOT / "PRE_PROBE_FINAL_REVERIFY_DECISION.json")
    assert guard["forbidden_capabilities_created"] == []
    assert guard["checks"]["live_ingestion_created"] is False
    assert guard["checks"]["ForecastPacket_created"] is False
    assert guard["checks"]["official_case_ticket_action_created"] is False
    assert guard["checks"]["source_truth_mutated"] is False
    assert decision["external_operator_validation_created"] is False
    assert decision["operator_fuel_created"] is False
    assert decision["training_rows_created"] is False
    assert decision["learning_arming_allowed"] is False
    assert decision["source_truth_mutated"] is False
    assert runner.validate_all() == []


def test_final_hash_manifest_validates():
    ensure_outputs()
    assert runner.verify_manifest(runner.FINAL_ROOT / "HASH_MANIFEST.json") == []
