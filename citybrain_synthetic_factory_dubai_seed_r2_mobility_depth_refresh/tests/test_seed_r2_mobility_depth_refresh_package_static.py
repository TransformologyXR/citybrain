from __future__ import annotations

import json
import py_compile
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_package_expected_files_present():
    expected = [
        "README.md",
        "CODEX_HANDOFF.md",
        "docs/BOUNDARY_POLICY.md",
        "manifests/INPUT_CONTRACT.json",
        "manifests/EXPECTED_OUTPUTS.json",
        "prompts/CODEX_TASK_PROMPT.md",
        "scripts/run_main_citybrain_synthetic_factory_dubai_seed_r2_mobility_depth_refresh.py",
    ]
    for rel in expected:
        assert (PACKAGE_ROOT / rel).exists(), rel


def test_contracts_parse_clean():
    for rel in ["manifests/INPUT_CONTRACT.json", "manifests/EXPECTED_OUTPUTS.json", "PACKAGE_DECISION.json", "SECRET_SCAN_REPORT.json"]:
        with (PACKAGE_ROOT / rel).open("r", encoding="utf-8") as f:
            json.load(f)


def test_runner_compiles():
    py_compile.compile(str(PACKAGE_ROOT / "scripts/run_main_citybrain_synthetic_factory_dubai_seed_r2_mobility_depth_refresh.py"), doraise=True)


def test_no_obvious_secret_material_in_package_text():
    text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in PACKAGE_ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".json", ".py", ".txt"}
    )
    forbidden_literals = ["Primary" + " key", "Secondary" + " key", "Account" + " Key:", "app_key=" + "2", "app_key=" + "e"]
    for lit in forbidden_literals:
        assert lit not in text
    assert "app_key=REDACTED" in text or "REDACTED" in text


def test_expected_outputs_include_product_fixtures():
    outputs = json.loads((PACKAGE_ROOT / "manifests/EXPECTED_OUTPUTS.json").read_text(encoding="utf-8"))["expected_outputs"]
    required = {
        "EVENT_REPLAY_TAPE_MOBILITY_REFRESH_R2.jsonl",
        "WATCH_MOBILITY_DEPTH_QUEUE_R2.jsonl",
        "ASK_MOBILITY_ENTITY_PROFILE_FIXTURES_R2.jsonl",
        "CHECK_MOBILITY_DEPTH_FIXTURES_R2.jsonl",
        "BRIEF_MOBILITY_PACKET_FIXTURES_R2.jsonl",
        "SPATIAL_MOBILITY_OVERLAY_FIXTURES_R2.jsonl",
    }
    assert required.issubset(set(outputs))
