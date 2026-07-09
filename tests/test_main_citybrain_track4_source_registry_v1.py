from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_track4_source_registry_v1.py"

spec = importlib.util.spec_from_file_location("track4_source_registry", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_source_registry_outputs_validate_cleanly():
    runner.build_outputs()
    assert runner.validate_outputs() == []


def test_registry_has_required_normalized_fields():
    registry = load_json(runner.OUTPUT_ROOT / "SOURCE_REGISTRY_V1.json")
    assert registry["schema_version"] == "citybrain.source_registry.v1"
    assert registry["registry_summary"]["source_count"] > 0
    for source in registry["sources"]:
        for field in runner.REQUIRED_SOURCE_FIELDS:
            assert field in source, (source.get("source_id"), field)
        assert source["source_id"].startswith("source:")
        assert isinstance(source["known_limitations"], list)
        assert isinstance(source["consuming_flows"], list)


def test_registry_covers_multiple_cities_domains_and_source_classes():
    registry = load_json(runner.OUTPUT_ROOT / "SOURCE_REGISTRY_V1.json")
    summary = registry["registry_summary"]
    assert len(summary["cities"]) >= 3
    assert len(summary["domains"]) >= 4
    assert len(summary["source_classes"]) >= 3
    assert summary["candidate_only_sources"] >= 1


def test_registry_preserves_maturity_gap_signals():
    registry = load_json(runner.OUTPUT_ROOT / "SOURCE_REGISTRY_V1.json")
    assert any(source["freshness"]["status"] in {"unknown", "stale", "blocked_or_unavailable"} for source in registry["sources"])
    assert any(source["geometry_status"]["status"] != "present" for source in registry["sources"])
    assert any(source["time_coverage"]["status"] != "present" for source in registry["sources"])


def test_flow_map_and_hash_manifest_are_present():
    flow_map = load_json(runner.OUTPUT_ROOT / "SOURCE_REGISTRY_CONSUMING_FLOW_MAP.json")
    manifest = load_json(runner.OUTPUT_ROOT / "HASH_MANIFEST.json")
    assert flow_map["status"] == "PASS_WITH_LIMITATIONS"
    assert "CHECK" in load_json(runner.OUTPUT_ROOT / "SOURCE_REGISTRY_V1.json")["registry_summary"]["trust_consumers"]
    assert manifest["status"] == "PASS"
    assert manifest["entry_count"] >= 6
