from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_review_packet_360_mobility_native_repair_r1.py"

spec = importlib.util.spec_from_file_location("mobility_native_repair", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.DEFAULT_OUT / "MOBILITY_REVIEW_PACKET_360_NATIVE_REPAIR_DECISION.json").exists():
        runner.build(
            runner.DEFAULT_PACKET_GATE_ROOT,
            runner.DEFAULT_EXPANDED_CORPUS_ROOT,
            runner.DEFAULT_EXPANDED_CADENCE_ROOT,
            runner.DEFAULT_OUT,
        )


def test_required_outputs_exist():
    runner.build(
        runner.DEFAULT_PACKET_GATE_ROOT,
        runner.DEFAULT_EXPANDED_CORPUS_ROOT,
        runner.DEFAULT_EXPANDED_CADENCE_ROOT,
        runner.DEFAULT_OUT,
    )
    assert [runner.rel(path) for path in runner.required_paths(runner.DEFAULT_OUT) if not path.exists()] == []


def test_decision_repairs_mobility_with_native_packet():
    ensure_outputs()
    decision = load_json(runner.DEFAULT_OUT / "MOBILITY_REVIEW_PACKET_360_NATIVE_REPAIR_DECISION.json")
    packet = load_json(runner.DEFAULT_OUT / "MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET.json")
    assert decision["status"] in {runner.STATUS_PASS, runner.STATUS_BLOCKED}
    assert decision["status"] == runner.STATUS_PASS
    assert decision["mobility_native_packet_status"] == "native_packet_complete"
    assert packet["family_id"] == runner.FAMILY
    assert packet["native_packet_status"] == "native_packet_complete"
    assert len(packet["native_event_fabric_refs"]) == 20
    assert packet["derived_backfill_comparison"]["used_as_native_evidence"] is False


def test_evidence_ledger_keeps_native_and_derived_provenance_separate():
    ensure_outputs()
    ledger = runner.read_jsonl(runner.DEFAULT_OUT / "MOBILITY_REVIEW_PACKET_360_NATIVE_EVIDENCE_LEDGER.jsonl")
    provenance = load_json(runner.DEFAULT_OUT / "MOBILITY_REVIEW_PACKET_360_NATIVE_VS_DERIVED_PROVENANCE_AUDIT.json")
    native_rows = [row for row in ledger if row["native_evidence"]]
    derived_rows = [row for row in ledger if row["derived_backfill"]]
    assert native_rows
    assert derived_rows
    assert provenance["derived_backfill_relabelled_as_native"] is False
    assert provenance["derived_backfill_used_as_comparison_only"] is True


def test_all_four_family_status_after_repair_and_product_stays_closed():
    ensure_outputs()
    family = load_json(runner.DEFAULT_OUT / "REVIEW_PACKET_360_FAMILY_STATUS_AFTER_MOBILITY_REPAIR.json")
    product = load_json(runner.DEFAULT_OUT / "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_RECHECK.json")
    assert family["all_four_families_inventoried"] is True
    assert family["family_native_status_counts"]["native_packet_complete"] == 4
    assert product["mobility_native_repair_status"] == "native_packet_complete"
    assert product["founder_diagnostic_review_allowed_with_limitations"] is True
    assert product["product_review_ready"] is False
    assert product["client_ready"] is False


def test_blockers_file_and_refresh_candidates_exist_without_session_results():
    ensure_outputs()
    blockers = load_json(runner.DEFAULT_OUT / "MOBILITY_REVIEW_PACKET_360_MISSING_NATIVE_EVIDENCE_BLOCKERS.json")
    refresh = load_json(runner.DEFAULT_OUT / "FOUNDER_CARD_MOBILITY_REFRESH_CANDIDATES.json")
    assert blockers["blocker_count"] == 0
    assert blockers["status"] == "NO_BLOCKERS"
    assert refresh["candidate_count"] == 4
    assert refresh["status"] == "CANDIDATES_ONLY_NO_SESSION_RESULT"
    assert all(row["session_result_created"] is False for row in refresh["rows"])


def test_guards_manifest_and_validate():
    ensure_outputs()
    source = load_json(runner.DEFAULT_OUT / "NO_SOURCE_TRUTH_MUTATION_GUARD.json")
    fuel = load_json(runner.DEFAULT_OUT / "NO_FOUNDER_SESSION_FUEL_GUARD.json")
    client = load_json(runner.DEFAULT_OUT / "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json")
    boundary = load_json(runner.DEFAULT_OUT / "BOUNDARY_NO_ACTION_AUDIT.json")
    assert source["source_truth_mutated"] is False
    assert source["derived_backfill_relabelled_as_native"] is False
    assert fuel["founder_session_results_created"] is False
    assert fuel["operator_fuel_created"] is False
    assert fuel["training_rows_created"] is False
    assert client["client_ready_claim_created"] is False
    assert client["product_review_ready_claim_created"] is False
    assert boundary["forecast_packet_created"] is False
    assert boundary["official_workflow_case_action_created"] is False
    assert runner.verify_manifest(runner.DEFAULT_OUT / "HASH_MANIFEST.sha256") == []
    assert runner.validate(runner.DEFAULT_OUT) == []
