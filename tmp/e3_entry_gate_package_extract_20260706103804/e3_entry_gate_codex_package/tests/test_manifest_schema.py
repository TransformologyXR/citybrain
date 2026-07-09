import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text())


def iter_requirements(manifest):
    for group in ["conditionally_armed", "blocked_until"]:
        for increment, block in manifest[group].items():
            for req in block.get("requires", []):
                yield group, increment, req


def test_manifest_has_required_top_level_sections():
    manifest = load("manifests/epoch3_arming_manifest.json")
    for key in ["gate_id", "loop_crosswalk", "armed_now", "conditionally_armed", "blocked_until", "not_armed_initial"]:
        assert key in manifest


def test_all_requirements_are_structured_not_prose():
    manifest = load("manifests/epoch3_arming_manifest.json")
    for _, _, req in iter_requirements(manifest):
        assert isinstance(req, dict)
        assert {"id", "metric", "op", "value"}.issubset(req.keys())
        assert isinstance(req["metric"], str)
        assert req["op"] in {"==", "!=", ">=", ">", "<=", "<", "contains_all", "exists", "not_exists"}


def test_day_one_exposure_logging_is_armed():
    manifest = load("manifests/epoch3_arming_manifest.json")
    assert "L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING" in manifest["armed_now"]
    assert "L1.R0_WATCH_EXPLORATION_FLOOR_INFRA" in manifest["armed_now"]


def test_no_official_action_non_claim_present():
    manifest = load("manifests/epoch3_arming_manifest.json")
    assert "no_official_action" in manifest["non_claims"]
    assert "no_dispatch" in manifest["non_claims"]
    assert "no_enforcement" in manifest["non_claims"]
