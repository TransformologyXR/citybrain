import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_manifest_has_five_lanes_and_track0():
    data = json.loads((ROOT / "manifests/scout_lane_manifest.json").read_text())
    ids = {lane["lane_id"] for lane in data["lanes"]}
    assert {"A", "B", "C", "D", "E", "TRACK0"} <= ids

def test_no_model_boundaries_present():
    text = (ROOT / "NON_GOALS_AND_BOUNDARIES.md").read_text()
    for phrase in [
        "No ranker",
        "No forecast model",
        "No learned predictor",
        "No counterfactual learner",
        "No case-memory learner",
        "No dynamic investigation",
        "No cross-city learned transfer",
    ]:
        assert phrase in text

def test_acceptance_requires_all_five_reports():
    text = (ROOT / "ACCEPTANCE_CRITERIA.md").read_text()
    for phrase in [
        "hidden transition target catalog",
        "CHECK calibration fuel scout report",
        "L4 case-memory fuel scout report",
        "identity/graph eval fuel scout report",
        "LLM/perception usefulness scout report",
    ]:
        assert phrase in text

def test_templates_parse():
    for p in (ROOT / "artifacts_to_add/templates").glob("*.json"):
        json.loads(p.read_text())
