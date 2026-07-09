from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_story_arc_review_provenance_gate_repair_r1.py"

spec = importlib.util.spec_from_file_location("story_arc_review_provenance_repair", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.DEFAULT_OUT / "STORY_ARC_REVIEW_PROVENANCE_GATE_REPAIR_DECISION.json").exists():
        runner.build(runner.DEFAULT_STORY_ROOT, runner.DEFAULT_REVIEW_INPUT_ROOT, runner.DEFAULT_OUT)


def test_required_outputs_exist_and_validate():
    runner.build(runner.DEFAULT_STORY_ROOT, runner.DEFAULT_REVIEW_INPUT_ROOT, runner.DEFAULT_OUT)
    assert [path.name for path in runner.required_paths(runner.DEFAULT_OUT) if not path.exists()] == []
    assert runner.validate(runner.DEFAULT_OUT) == []


def test_semantics_overlay_corrects_gate_label_without_inflation():
    ensure_outputs()
    overlay = load_json(runner.DEFAULT_OUT / "CROSS_DOMAIN_SHARED_ENTITY_SEMANTICS_OVERLAY.json")
    fields = overlay["replacement_fields"]
    assert overlay["deprecated_field"] == "shared_canonical_entity_3plus_gate_met"
    assert fields["shared_canonical_entity_family_span_gate_met"] is True
    assert fields["shared_canonical_entity_family_span_minimum"] == 3
    assert fields["shared_canonical_entity_family_span"] == 3
    assert fields["shared_canonical_entity_count"] == 1
    assert fields["shared_canonical_entity_refs"] == ["cer:building:alpha"]
    assert set(fields["families_spanned_by_primary_shared_entity"]) == {
        "building_compliance_perception_candidate",
        "mobility_access_interruption_v0",
        "permit_inspection_delay",
    }
    assert fields["asset_infrastructure_link_type"] == "corridor_context_not_same_entity"
    assert "one shared canonical entity spans three families" in overlay["overclaim_guard"]


def test_review_provenance_contract_rejects_review_of_review():
    ensure_outputs()
    contract = load_json(runner.DEFAULT_OUT / "AI_DIAGNOSTIC_REVIEW_PROVENANCE_CONTRACT.json")
    required = contract["independent_review_required_fields"]
    assert required["independent_artifact_review"] is True
    assert required["review_of_review"] is False
    assert required["artifact_availability_confirmed"] is True
    assert "review_of_review=true" in contract["not_independent_if"]
    assert "actual artifacts absent" in contract["not_independent_if"]


def test_claude_classification_and_concordance_guard_wait():
    ensure_outputs()
    claude = load_json(runner.DEFAULT_OUT / "CLAUDE_REVIEW_OF_REVIEW_CLASSIFICATION.json")
    guard = load_json(runner.DEFAULT_OUT / "CONCORDANCE_IMPORT_GUARD_R2.json")
    assert claude["true_second_independent_ai_artifact_review_count"] == 0
    assert guard["review_of_review_counts_as_second_review"] is False
    assert guard["concordance_import_allowed"] is False
    assert guard["decision"] == runner.WAIT_DECISION


def test_founder_and_product_readiness_remain_closed():
    ensure_outputs()
    founder = load_json(runner.DEFAULT_OUT / "FOUNDER_DIAGNOSTIC_READINESS_AFTER_REPAIR.json")
    decision = load_json(runner.DEFAULT_OUT / "STORY_ARC_REVIEW_PROVENANCE_GATE_REPAIR_DECISION.json")
    assert founder["founder_diagnostic_review_allowed"] is False
    assert founder["founder_product_review_allowed"] is False
    assert founder["product_review_ready"] is False
    assert founder["client_ready"] is False
    assert decision["operator_fuel_created"] is False
    assert decision["training_rows_created"] is False
    assert decision["forecast_packet_created"] is False
    assert decision["source_truth_mutated"] is False


def test_source_artifacts_not_rewritten_manifest_publication():
    ensure_outputs()
    decision = load_json(runner.DEFAULT_OUT / "STORY_ARC_REVIEW_PROVENANCE_GATE_REPAIR_DECISION.json")
    assert decision["source_artifacts_rewritten"] is False
    assert decision["source_artifact_hashes_before"] == decision["source_artifact_hashes_after"]
    assert runner.verify_manifest(runner.DEFAULT_OUT / "HASH_MANIFEST.sha256") == []
    assert (runner.PUBLICATION_ROOT / "CROSS_DOMAIN_SHARED_ENTITY_SEMANTICS_OVERLAY.json").exists()
