from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_tracka_event_stories_source_diff_r1.py"

spec = importlib.util.spec_from_file_location("tracka_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_decision_exists_and_has_with_limitations():
    runner.build_outputs()
    decision = load_json(runner.OUTPUT_ROOT / "TRACKA_EVENT_STORIES_SOURCE_DIFF_DECISION.json")
    assert decision["status"] == runner.FINAL_STATUS
    assert decision["status"].endswith("_WITH_LIMITATIONS")


def test_event_story_pack_has_at_least_three_stories():
    story_pack = load_json(runner.OUTPUT_ROOT / "EVENT_STORY_PACK_R1.json")
    assert story_pack["story_count"] >= 3
    for story in story_pack["stories"]:
        assert story["story_id"]
        assert story["event_family"]
        assert story["cannot_claim"]
        assert story["review_only_state"]
        assert story["replay_steps"]


def test_source_registry_v1_1_preserves_or_exceeds_source_count():
    source_v1 = load_json(runner.SOURCE_REGISTRY_ROOT / "SOURCE_REGISTRY_V1.json")
    source_v1_1 = load_json(runner.OUTPUT_ROOT / "SOURCE_REGISTRY_V1_1.json")
    assert len(source_v1_1["sources"]) >= len(source_v1["sources"])
    sample = source_v1_1["sources"][0]
    for field in [
        "source_id",
        "source_name",
        "city",
        "domain",
        "source_class",
        "access_status",
        "license_status",
        "freshness_status",
        "geometry_status",
        "schema_status",
        "coverage_status",
        "known_limitations",
        "consuming_flows",
        "consuming_modes",
        "maturity_flags",
        "evidence_refs",
    ]:
        assert field in sample


def test_diff_fixtures_cover_at_least_three_selected_families():
    rows = load_jsonl(runner.OUTPUT_ROOT / "DIFF_DESIGNED_CHANGE_FIXTURES.jsonl")
    families = {row["family_id"] for row in rows}
    change_types = {row["change_type"] for row in rows}
    assert len(families) >= 3
    assert set(runner.CHANGE_TYPES).issubset(change_types)
    assert all(row["expected_classification"] for row in rows)


def test_no_forbidden_capabilities_are_created():
    guard = load_json(runner.OUTPUT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json")
    assert guard["status"] == "PASS"
    assert guard["forbidden_capabilities_created"] == []
    assert all(value is False for value in guard["checks"].values())


def test_hash_manifest_covers_packaged_outputs():
    manifest = load_json(runner.OUTPUT_ROOT / "HASH_MANIFEST.json")
    paths = {entry["path"] for entry in manifest["entries"]}
    for name in runner.OUTPUT_FILES:
        if name != "HASH_MANIFEST.json":
            assert f"outputs/main_citybrain_epoch4_tracka_event_stories_source_diff_r1/{name}" in paths
    assert runner.validate_outputs() == []
