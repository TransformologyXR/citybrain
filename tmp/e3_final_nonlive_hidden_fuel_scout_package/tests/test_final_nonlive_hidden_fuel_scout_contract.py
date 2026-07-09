import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_decision_template_locks_finality_and_nonlive():
    p = ROOT / "artifacts_to_add/templates/E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_DECISION.template.json"
    data = json.loads(p.read_text())
    assert data["package_id"] == "MAIN-CITYBRAIN-EPOCH3-FINAL-NONLIVE-HIDDEN-FUEL-SCOUT-R1"
    assert data["status"] == "PASS_E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_R1_WITH_LIMITATIONS"
    assert data["non_live_assumption"] is True
    assert data["promotion_status"] == "candidate_inventory_and_backlog_only"
    assert data["finality_rule"] == "NO_MORE_PRE_CLOSEOUT_SCOUTS_UNLESS_HUMAN_REOPENS"

def test_no_model_guard_blocks_forbidden_capabilities():
    p = ROOT / "artifacts_to_add/templates/E3_FINAL_NONLIVE_NO_MODEL_GUARD_REPORT.template.json"
    data = json.loads(p.read_text())
    assert data["status"] == "PASS"
    assert data["new_training_rows_created"] == 0
    assert data["new_learned_registry_entries"] == 0
    for k, v in data.items():
        if k.endswith("_created") or k.endswith("_transfer_created"):
            assert v is False

def test_publication_home_recommendation_present():
    p = ROOT / "artifacts_to_add/templates/E3_PUBLICATION_HOME_RECOMMENDATION_ROW.template.json"
    data = json.loads(p.read_text())
    assert data["recommended_tracked_path"] == "publications/epoch3/"
    assert "hash_manifests" in data["governance_artifacts_to_track"]

def test_backlog_schema_has_final_classifications():
    schema = json.loads((ROOT / "schemas/backlog_item.schema.json").read_text())
    classification = schema["properties"]["classification"]["enum"]
    assert "closeout_affecting" in classification
    assert "epoch4_backlog" in classification
    assert "not_promotable" in classification
