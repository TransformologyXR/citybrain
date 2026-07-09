from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_derived_fix_and_founder_input_sequence_r1.py"

spec = importlib.util.spec_from_file_location("derived_fix_founder_input_sequence", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.SEQUENCE_ROOT / "DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_DECISION.json").exists():
        runner.build_all()


def test_required_outputs_exist():
    runner.build_all()
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []


def test_derived_fix_overlay_register_has_50_derived_only_entries():
    ensure_outputs()
    decision = load_json(runner.OVERLAY_ROOT / "DERIVED_FIX_PROMOTION_OVERLAY_DECISION.json")
    register = load_json(runner.OVERLAY_ROOT / "DERIVED_FIX_OVERLAY_REGISTER.json")
    mutation = load_json(runner.OVERLAY_ROOT / "SOURCE_TRUTH_NO_MUTATION_AUDIT.json")
    score = load_json(runner.OVERLAY_ROOT / "NO_SCORE_INFLATION_GUARD.json")
    fuel = load_json(runner.OVERLAY_ROOT / "NO_FUEL_NO_TRAINING_GUARD.json")
    assert decision["status"] == runner.STATUS_OVERLAY
    assert decision["overlay_count"] == 50
    assert register["overlay_count"] == 50
    assert all(row["permitted_scope"] == "derived_overlay_only" for row in register["overlays"])
    assert all(row["requires_review"] is True for row in register["overlays"])
    assert all(row["promoted_to_source_truth"] is False for row in register["overlays"])
    assert all(row["promoted_to_canonical_truth"] is False for row in register["overlays"])
    assert mutation["source_truth_mutated"] is False
    assert mutation["canonical_truth_mutated"] is False
    assert score["maturity_score_inflation_as_fact"] is False
    assert fuel["operator_fuel_created"] is False
    assert fuel["training_rows_created"] is False


def test_founder_probe_input_kit_has_cards_templates_schema_and_no_session():
    ensure_outputs()
    decision = load_json(runner.KIT_ROOT / "FOUNDER_PROBE_INPUT_KIT_DECISION.json")
    cards = load_json(runner.KIT_ROOT / "FOUNDER_PROBE_TASK_CARD_SET.json")
    template = load_json(runner.KIT_ROOT / "FOUNDER_PROBE_RESPONSE_TEMPLATE.json")
    schema = load_json(runner.KIT_ROOT / "FOUNDER_PROBE_IMPORT_SCHEMA.json")
    guard = load_json(runner.KIT_ROOT / "FOUNDER_PROBE_SESSION_NOT_RUN_GUARD.json")
    assert decision["status"] == runner.STATUS_KIT
    assert 12 <= decision["card_count"] <= 16
    assert cards["reviewer_type"] == "founder_internal"
    assert len(cards["cards"]) == decision["card_count"]
    assert set(runner.RESPONSE_FIELDS).issubset(set(template["fields"]))
    assert schema["reviewer_type_allowed"] == ["founder_internal"]
    assert schema["training_eligible"] is False
    assert guard["session_results_created"] is False
    assert guard["fabricated_review_input_created"] is False
    assert guard["operator_fuel_created"] is False
    assert guard["training_rows_created"] is False
    assert (runner.KIT_ROOT / "FOUNDER_PROBE_RESPONSE_TEMPLATE.csv").exists()
    assert (runner.KIT_ROOT / "FOUNDER_PROBE_TASK_CARDS.md").exists()


def test_no_session_reverify_and_sequence_guards():
    ensure_outputs()
    reverify = load_json(runner.REVERIFY_ROOT / "NO_SESSION_PROBE_READINESS_REVERIFY_DECISION.json")
    no_session = load_json(runner.REVERIFY_ROOT / "NO_SESSION_NO_FUEL_REVERIFY.json")
    guard = load_json(runner.REVERIFY_ROOT / "FORBIDDEN_CAPABILITY_GUARD.json")
    sequence = load_json(runner.SEQUENCE_ROOT / "DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_DECISION.json")
    audit = load_json(runner.SEQUENCE_ROOT / "DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_AUDIT.json")
    assert reverify["status"] == runner.STATUS_REVERIFY
    assert reverify["session_results_created"] is False
    assert reverify["operator_fuel_created"] is False
    assert reverify["training_rows_created"] is False
    assert no_session["dispositions_created"] is False
    assert no_session["operator_fuel_created"] is False
    assert no_session["training_rows_created"] is False
    assert guard["forbidden_capabilities_created"] == []
    assert guard["checks"]["source_truth_mutated"] is False
    assert guard["checks"]["ForecastPacket_or_product_forecast_created"] is False
    assert sequence["status"] == runner.STATUS_SEQUENCE
    assert sequence["parallel_execution_used"] is False
    assert sequence["source_truth_mutated"] is False
    assert sequence["session_results_created"] is False
    assert audit["parallel_execution_used"] is False
    assert [step["package_id"] for step in audit["steps"]] == [
        "MAIN-CITYBRAIN-EPOCH4-DERIVED-FIX-PROMOTION-OVERLAY-R1",
        "MAIN-CITYBRAIN-EPOCH4-FOUNDER-PROBE-INPUT-KIT-R2",
        "MAIN-CITYBRAIN-EPOCH4-NO-SESSION-PROBE-READINESS-REVERIFY-R1",
    ]


def test_hash_manifests_and_validate_all_pass():
    ensure_outputs()
    for path in [
        runner.OVERLAY_ROOT / "HASH_MANIFEST.json",
        runner.KIT_ROOT / "HASH_MANIFEST.json",
        runner.REVERIFY_ROOT / "HASH_MANIFEST.json",
        runner.SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        assert runner.verify_manifest(path) == []
    assert runner.validate_all() == []
