from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW_ROOT = REPO_ROOT / "outputs" / "main_citybrain_epoch4_review_pack_quality_upgrade_r4_r1"
GAP_ROOT = REPO_ROOT / "outputs" / "main_citybrain_epoch4_data_estate_gap_routing_r1"
FINAL_ROOT = REPO_ROOT / "outputs" / "main_citybrain_epoch4_review_quality_global_gap_final_reverify_r1"
SEQ_ROOT = REPO_ROOT / "outputs" / "main_citybrain_epoch4_review_quality_global_gap_sequence_r1"

EXPECTED_GAP_COUNTS = {
    "SOURCE_CLASS_UNKNOWN_TRIAGE_QUEUE.json": 430,
    "FRESHNESS_UNKNOWN_TRIAGE_QUEUE.json": 462,
    "SCHEMA_UNKNOWN_TRIAGE_QUEUE.json": 456,
    "GEOMETRY_UNKNOWN_TRIAGE_QUEUE.json": 526,
    "NO_CONSUMING_FLOW_TRIAGE_QUEUE.json": 273,
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sequence_decision_and_boundaries():
    decision = load_json(SEQ_ROOT / "REVIEW_QUALITY_GLOBAL_GAP_SEQUENCE_DECISION.json")
    assert decision["status"] == "PASS_MAIN_CITYBRAIN_EPOCH4_REVIEW_QUALITY_GLOBAL_GAP_SEQUENCE_R1_WITH_LIMITATIONS"
    assert decision["review_pack_quality_status"] == "GO_FOR_FOUNDER_DIAGNOSTIC_REVIEW_WITH_LIMITATIONS"
    assert decision["data_estate_gap_routing_status"] == "PASS_MAIN_CITYBRAIN_EPOCH4_DATA_ESTATE_GAP_ROUTING_R1_WITH_LIMITATIONS"
    assert decision["final_reverify_status"] == "PASS_MAIN_CITYBRAIN_EPOCH4_REVIEW_QUALITY_GLOBAL_GAP_FINAL_REVERIFY_R1_WITH_LIMITATIONS"
    assert decision["review_cards_r4"] == 16
    assert decision["eval_cases_crosswalked"] == 48
    assert decision["founder_diagnostic_ready_recommended"] is True
    assert decision["product_review_ready_recommended"] is False
    assert decision["next_recommended_move"] == "RUN_FOUNDER_DIAGNOSTIC_REVIEW"
    for key in [
        "founder_session_results_created",
        "operator_fuel_created",
        "training_rows_created",
        "source_truth_mutation",
        "live_ingestion_created",
        "forecast_surface_created",
        "official_action_control_enforcement_created",
    ]:
        assert decision[key] is False, key


def test_review_pack_quality_outputs_and_r4_cards():
    decision = load_json(REVIEW_ROOT / "REVIEW_PACK_QUALITY_DECISION.json")
    assert decision["status"] == "GO_FOR_FOUNDER_DIAGNOSTIC_REVIEW_WITH_LIMITATIONS"
    assert decision["founder_cards_accounted_for"] == 16
    assert decision["eval_cases_crosswalked"] == 48
    assert decision["founder_diagnostic_ready_recommended"] is True
    assert decision["product_review_ready_recommended"] is False

    card_json = sorted((REVIEW_ROOT / "review_cards_r4").glob("*.json"))
    card_md = sorted((REVIEW_ROOT / "review_cards_r4").glob("*.md"))
    assert len(card_json) == 16
    assert len(card_md) == 16
    for path in card_json:
        card = load_json(path)
        assert card["plain_language_case_summary"]
        assert card["provenance"] in {"native_or_replay_review_evidence", "derived_backfill_not_source_truth"}
        assert card["check_v1_actual_outcome"]["actual"]
        assert card["actual_vs_expected"]["status"] == "PASS_EXPLAINED"
        assert card["cer_seg_context_summary"]["cer_missing"] is False
        assert card["cer_seg_context_summary"]["seg_missing"] is False
        assert card["no_action_boundary"] is True
        assert card["not_source_truth"] is True

    scorecard = load_json(REVIEW_ROOT / "REVIEW_CARD_EVIDENCE_QUALITY_SCORECARD.json")
    assert scorecard["all_cards_have_actual_outcome_blocks"] is True
    assert scorecard["all_cards_have_provenance"] is True
    assert len(scorecard["rows"]) == 16

    atlas = load_json(REVIEW_ROOT / "EVAL_CASE_EVIDENCE_ATLAS_48.json")
    assert atlas["case_count"] == 48


def test_negative_cards_and_mobility_provenance_are_not_overclaimed():
    classification = load_json(REVIEW_ROOT / "FOUNDER_CARD_R4_REPAIR_CLASSIFICATION.json")
    counts = classification["classification_counts"]
    assert counts["intentional diagnostic negative/stale/contradiction behavior"] == 12
    assert counts["derived/backfill provenance gap"] >= 1

    product_gate = load_json(REVIEW_ROOT / "PRODUCT_REVIEW_READINESS_GATE.json")
    assert product_gate["status"] == "NOT_READY_WITH_LIMITATIONS"
    assert product_gate["product_review_ready_recommended"] is False

    diagnostic_gate = load_json(REVIEW_ROOT / "DIAGNOSTIC_REVIEW_READINESS_GATE.json")
    assert diagnostic_gate["status"] == "GO_FOR_FOUNDER_DIAGNOSTIC_REVIEW_WITH_LIMITATIONS"
    assert diagnostic_gate["founder_diagnostic_ready_recommended"] is True

    mobility = load_json(REVIEW_ROOT / "MOBILITY_NATIVE_VS_DERIVED_PROVENANCE_REPORT.json")
    assert mobility["derived_backfill_visible"] is True
    assert mobility["native_review_packet_360_found"] is False
    assert mobility["source_truth_mutated"] is False


def test_global_gap_queues_match_deep_audit_counts_and_are_candidate_only():
    gap_decision = load_json(GAP_ROOT / "DATA_ESTATE_GAP_ROUTING_DECISION.json")
    assert gap_decision["status"] == "PASS_MAIN_CITYBRAIN_EPOCH4_DATA_ESTATE_GAP_ROUTING_R1_WITH_LIMITATIONS"
    assert gap_decision["source_registry_source_count"] == 664
    assert gap_decision["queue_counts"] == EXPECTED_GAP_COUNTS
    assert gap_decision["maturity_score_inflation"] is False
    assert gap_decision["source_truth_mutation"] is False

    for name, expected in EXPECTED_GAP_COUNTS.items():
        queue = load_json(GAP_ROOT / name)
        assert queue["status"] == "PASS"
        assert queue["queue_count"] == expected
        assert len(queue["items"]) == expected
        first = queue["items"][0]
        assert first["source_id"]
        assert first["current_gap_type"]
        assert first["non_claim_boundary"] == "candidate queue only; not source truth, not production action"

    overlays = load_json(GAP_ROOT / "SAFE_CANDIDATE_ENRICHMENT_OVERLAYS.json")
    assert overlays["overlay_count"] == 25
    assert all(item["review_state"] == "candidate" for item in overlays["overlays"])
    assert all(item["not_source_truth"] is True for item in overlays["overlays"])


def test_final_reverify_and_guards_pass():
    final_decision = load_json(FINAL_ROOT / "REVIEW_QUALITY_GLOBAL_GAP_FINAL_DECISION.json")
    assert final_decision["status"] == "PASS_MAIN_CITYBRAIN_EPOCH4_REVIEW_QUALITY_GLOBAL_GAP_FINAL_REVERIFY_R1_WITH_LIMITATIONS"
    assert final_decision["next_recommended_move"] == "RUN_FOUNDER_DIAGNOSTIC_REVIEW"
    assert final_decision["product_review_ready_recommended"] is False
    assert final_decision["founder_diagnostic_ready_recommended"] is True

    for root in [REVIEW_ROOT, GAP_ROOT, FINAL_ROOT]:
        guard = load_json(root / "NO_FORBIDDEN_CAPABILITY_GUARD.json")
        assert guard["status"] == "PASS"
        assert guard["founder_session_results_created"] is False
        assert guard["operator_fuel_created"] is False
        assert guard["training_rows_created"] is False
        assert guard["source_truth_mutation"] is False

    source_guard = load_json(GAP_ROOT / "NO_SOURCE_TRUTH_MUTATION_GUARD.json")
    assert source_guard["source_truth_mutation"] is False
    assert source_guard["candidate_overlays_only"] is True


def test_publications_hashes_and_validate_only():
    for root in [REVIEW_ROOT, GAP_ROOT, FINAL_ROOT, SEQ_ROOT]:
        manifest = load_json(root / "HASH_MANIFEST.json")
        assert manifest["status"] == "PASS"
        assert manifest["file_count"] == len(manifest["entries"])
        for entry in manifest["entries"]:
            assert (root / entry["path"]).exists(), entry["path"]

    for pub in [
        REPO_ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-review-pack-quality-upgrade-r4-r1",
        REPO_ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-data-estate-gap-routing-r1",
        REPO_ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-review-quality-global-gap-final-reverify-r1",
        REPO_ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-review-quality-global-gap-sequence-r1",
    ]:
        assert pub.exists()
        assert any(pub.rglob("*"))

    result = subprocess.run(
        [sys.executable, "scripts/run_main_citybrain_epoch4_review_quality_global_gap_sequence_r1.py", "--validate-only"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "PASS_MAIN_CITYBRAIN_EPOCH4_REVIEW_QUALITY_GLOBAL_GAP_SEQUENCE_R1_WITH_LIMITATIONS" in result.stdout
