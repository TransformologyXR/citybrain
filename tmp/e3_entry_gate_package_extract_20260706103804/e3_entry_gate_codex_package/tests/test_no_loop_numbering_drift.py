import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_loop_numbering_is_correct():
    manifest = json.loads((ROOT / "manifests/epoch3_arming_manifest.json").read_text())
    assert manifest["loop_crosswalk"]["L3"] == "causal / counterfactual"
    assert manifest["loop_crosswalk"]["L4"] == "institutional memory"
    assert "L3_COUNTERFACTUAL" in manifest["blocked_until"]
    assert "L4_CASE_MEMORY" in manifest["blocked_until"]


def test_forbidden_l3_case_memory_identifier_absent():
    forbidden = "L3_CASE_MEMORY" + "_LEARNING"
    offenders = []
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".json", ".yaml", ".yml", ".py", ".txt"}:
            if forbidden in path.read_text(errors="ignore"):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
