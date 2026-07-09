from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_track6_brief_v3_export_hardening.py"

spec = importlib.util.spec_from_file_location("brief_v3_export_hardening", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def setup_module():
    runner.build_outputs()


def test_requested_outputs_exist_and_parse():
    for name in runner.REQUESTED_OUTPUTS:
        path = runner.OUTPUT_ROOT / name
        assert path.exists(), name
        if path.suffix == ".json":
            assert load_json(path)
    assert (runner.OUTPUT_ROOT / "HASH_MANIFEST.json").exists()


def test_packet_has_consistent_json_export_sections():
    packet = load_json(runner.OUTPUT_ROOT / "BRIEF_V3_EXPORT_PACKET.json")
    assert packet["status"] == runner.PASS_STATUS
    assert packet["export_kind"] == "local_replay_review_only"
    assert packet["section_order"] == runner.SECTION_ORDER
    assert set(runner.SECTION_ORDER).issubset(packet["sections"])
    assert packet["source_record_count"] >= 3
    assert packet["ui_polish_performed"] is False
    assert packet["official_action_created"] is False
    assert packet["legal_or_certified_finding_created"] is False


def test_markdown_export_has_required_founder_review_blocks_in_order():
    markdown = (runner.OUTPUT_ROOT / "BRIEF_V3_EXPORT_PACKET.md").read_text(encoding="utf-8")
    headings = [
        "## Source Record Appendix",
        "## CHECK v1 Summary",
        "## Simulation Assumptions",
        "## Event State",
        "## Spatial References",
        "## Cannot Claim",
        "## Review Options",
        "## Limitations",
    ]
    positions = [markdown.index(heading) for heading in headings]
    assert positions == sorted(positions)


def test_check_event_simulation_and_review_blocks_are_boundaried():
    packet = load_json(runner.OUTPUT_ROOT / "BRIEF_V3_EXPORT_PACKET.json")
    sections = packet["sections"]
    check = sections["check_v1_summary"]
    event_state = sections["event_state"]
    simulation = sections["simulation_assumptions"]
    review = sections["review_options"]

    assert check["official_truth_claim_created"] is False
    assert check["raw_ungrounded_graph_shortcuts_allowed"] is False
    assert event_state["active_event_count"] >= 1
    assert event_state["authority_boundary"] == "review_only_no_action"
    assert simulation["recommendation_authority"] is False
    assert simulation["abstain_available"] is True
    assert review["recommendation_authority"] is False
    assert review["abstain_option"]["available"] is True
    assert len(review["options"]) >= 2


def test_source_appendix_and_spatial_refs_are_present_without_certified_geometry_claim():
    packet = load_json(runner.OUTPUT_ROOT / "BRIEF_V3_EXPORT_PACKET.json")
    appendix = packet["sections"]["source_record_appendix"]
    spatial = packet["sections"]["spatial_references"]

    assert appendix["record_count"] >= 3
    assert appendix["missing_source_artifacts"] == []
    assert any(record["source_record_ref"] for record in appendix["records"])
    assert "cer:building:alpha" in spatial["cer_entity_refs"]
    assert spatial["geometry_certified"] is False
    assert spatial["citywide_twin_claim"] is False


def test_contract_line_endings_and_hash_manifest_verify():
    contract = load_json(runner.OUTPUT_ROOT / "BRIEF_V3_EXPORT_CONTRACT.json")
    line_report = load_json(runner.OUTPUT_ROOT / "LINE_ENDING_REPORT.json")
    assert contract["required_section_order"] == runner.SECTION_ORDER
    assert "markdown" in contract["export_formats"]
    assert "json" in contract["export_formats"]
    assert contract["ui_polish_in_scope"] is False
    assert line_report["status"] == "PASS"
    assert runner.validate_outputs() == []
