from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_review_packet_360_native_evidence_completeness_gate_r1.py"

spec = importlib.util.spec_from_file_location("review_packet_gate", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.DEFAULT_OUT / "REVIEW_PACKET_360_NATIVE_EVIDENCE_COMPLETENESS_DECISION.json").exists():
        runner.build(runner.DEFAULT_OUT)


def test_required_outputs_exist():
    runner.build(runner.DEFAULT_OUT)
    assert [runner.rel(path) for path in runner.required_paths(runner.DEFAULT_OUT) if not path.exists()] == []


def test_all_four_families_are_classified():
    ensure_outputs()
    inventory = load_json(runner.DEFAULT_OUT / "REVIEW_PACKET_360_FAMILY_INVENTORY.json")
    assert inventory["all_four_canonical_families_present"] is True
    assert set(inventory["canonical_families_present"]) == set(runner.FAMILIES)
    assert len(inventory["family_rows"]) == 4
    for row in inventory["family_rows"]:
        assert row["native_packet_status"] in {
            "native_packet_complete",
            "native_packet_partial",
            "derived_backfill_only",
            "missing_native_packet",
            "unknown",
        }
        assert row["review_readiness"] in {"diagnostic_ready", "product_review_ready", "not_ready"}
        assert row["evidence_kind"]


def test_mobility_is_explicit_derived_backfill_and_repair_scope_is_mobility_only():
    ensure_outputs()
    mobility = load_json(runner.DEFAULT_OUT / "REVIEW_PACKET_360_MOBILITY_NATIVE_PACKET_FINDING.json")
    repair = load_json(runner.DEFAULT_OUT / "REVIEW_PACKET_360_ALL_FAMILY_REPAIR_PLAN.json")
    decision = load_json(runner.DEFAULT_OUT / "REVIEW_PACKET_360_NATIVE_EVIDENCE_COMPLETENESS_DECISION.json")
    assert mobility["native_packet_status"] == "derived_backfill_only"
    assert mobility["derived_backfill_used"] is True
    assert mobility["product_review_blocked"] is True
    assert repair["mobility_only_native_gap"] is True
    assert repair["all_family_packet_weakness_detected"] is False
    assert repair["recommendation"] == "MOBILITY_NATIVE_PACKET_REPAIR_ONLY"
    assert decision["mobility_only_native_gap"] is True


def test_crosswalk_has_context_and_actuals_for_16_cards():
    ensure_outputs()
    crosswalk = load_json(runner.DEFAULT_OUT / "REVIEW_PACKET_360_FOUNDER_CARD_CROSSWALK.json")
    assert crosswalk["card_count"] == 16
    assert crosswalk["all_cards_have_cer_seg_context"] is True
    assert crosswalk["all_cards_have_actual_outcome"] is True
    assert crosswalk["family_counts"]["mobility_access_interruption_v0"] == 4


def test_diagnostic_ready_but_product_review_closed():
    ensure_outputs()
    gate = load_json(runner.DEFAULT_OUT / "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_GATE.json")
    no_client = load_json(runner.DEFAULT_OUT / "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json")
    assert gate["founder_diagnostic_review_allowed_with_limitations"] is True
    assert gate["product_review_ready"] is False
    assert gate["client_ready_claim_allowed"] is False
    assert gate["mobility_derived_backfill_only_blocks_product_review"] is True
    assert no_client["client_ready_claim_created"] is False
    assert no_client["product_review_ready_claim_created"] is False


def test_guards_and_manifest_validate():
    ensure_outputs()
    fuel = load_json(runner.DEFAULT_OUT / "NO_FOUNDER_SESSION_FUEL_GUARD.json")
    source = load_json(runner.DEFAULT_OUT / "NO_SOURCE_TRUTH_MUTATION_GUARD.json")
    boundary = load_json(runner.DEFAULT_OUT / "BOUNDARY_NO_ACTION_AUDIT.json")
    assert fuel["founder_session_results_created"] is False
    assert fuel["operator_fuel_created"] is False
    assert fuel["training_rows_created"] is False
    assert source["source_truth_mutated"] is False
    assert source["raw_provider_payload_rewritten"] is False
    assert boundary["forecast_packet_created"] is False
    assert boundary["official_action_case_dispatch_control_enforcement_created"] is False
    assert runner.verify_manifest(runner.DEFAULT_OUT / "HASH_MANIFEST.sha256") == []
    assert runner.validate(runner.DEFAULT_OUT) == []
