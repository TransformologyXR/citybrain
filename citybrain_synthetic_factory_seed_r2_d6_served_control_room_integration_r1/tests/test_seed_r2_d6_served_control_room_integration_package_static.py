import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_json_manifests_parse():
    for path in (ROOT / "manifests").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    json.loads((ROOT / "PACKAGE_DECISION.json").read_text(encoding="utf-8"))
    json.loads((ROOT / "SECRET_SCAN_REPORT.json").read_text(encoding="utf-8"))


def test_runner_exists_and_has_local_only_policy():
    script = ROOT / "scripts" / "run_main_citybrain_synthetic_factory_seed_r2_d6_served_control_room_integration_r1.py"
    text = script.read_text(encoding="utf-8")
    assert "no external network calls" in text.lower()
    assert "SECRET_ENV_NAMES" in text
    assert "app_key=(?!REDACTED|redacted)" in text


def test_boundary_policy_contains_required_denials():
    text = (ROOT / "docs" / "BOUNDARY_POLICY.md").read_text(encoding="utf-8").lower()
    for phrase in [
        "production frontend",
        "live monitoring",
        "dispatch",
        "official dubai truth",
        "credentials",
    ]:
        assert phrase in text


def test_no_literal_secret_examples_are_packaged():
    # Do not place real credentials in this test. The generation step runs an
    # exact scan against known values before packaging; this test only checks
    # that obvious placeholder-key strings are not present outside this test.
    all_text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in ROOT.rglob("*")
        if p.is_file()
        and "__pycache__" not in str(p)
        and ".pytest_cache" not in str(p)
        and p.name != Path(__file__).name
    )
    forbidden = [
        "PLACE_" + "REAL_" + "KEY_" + "HERE",
        "TFL_" + "PRIMARY_" + "KEY_" + "VALUE",
        "LTA_" + "DATAMALL_" + "ACCOUNT_" + "KEY_" + "VALUE",
    ]
    for token in forbidden:
        assert token not in all_text


def test_runner_smoke_with_temp_fixture(tmp_path):
    d5 = tmp_path / "d5"
    d5.mkdir()
    (d5 / "D5_SERVED_RUNTIME_INTEGRATION_R1_DECISION.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    rows = []
    for i, mode in enumerate(["watch", "ask", "check", "brief", "spatial", "event"], 1):
        rows.append({
            "response_id": f"served_response:{i:02d}",
            "request_packet_id": f"d5_runtime_fixture:{mode}:r1",
            "runtime_surface": "d5_localhost_served_runtime_fixture",
            "http_status": 200,
            "served_bind": "127.0.0.1",
            "status": "PASS",
            "limitations": ["LOCALHOST_ONLY", "SYNTHETIC_REPLAY_DONOR_CONTEXT_ONLY", "NO_DISPATCH_CONTROL_ENFORCEMENT_LEGAL_CERTIFIED_CLAIM"],
            "synthetic_replay_donor_context_only": True,
            "not_dubai_official_truth": True,
            "no_action_or_certified_claim": True,
            "external_network_calls": 0,
            "trace_refs": [],
        })
    (d5 / "D5_RUNTIME_REQUEST_RESPONSE_SMOKE_R1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    (d5 / "D5_RUNTIME_ENDPOINT_AUDIT_R1.json").write_text(json.dumps({
        "bind_host": "127.0.0.1",
        "bind_localhost_only": True,
        "external_network_calls": 0,
    }), encoding="utf-8")
    (d5 / "RUNTIME_BOUNDARY_AND_NO_ACTION_AUDIT_R1.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")

    out = tmp_path / "out"
    script = ROOT / "scripts" / "run_main_citybrain_synthetic_factory_seed_r2_d6_served_control_room_integration_r1.py"
    subprocess.check_call([sys.executable, str(script), "--d5-served-runtime", str(d5), "--out", str(out)])
    decision = json.loads((out / "D6_SERVED_CONTROL_ROOM_INTEGRATION_R1_DECISION.json").read_text(encoding="utf-8"))
    assert decision["status"].startswith("PASS_SYNTHETIC_FACTORY_SEED_R2_D6")
    assert decision["counts"]["served_runtime_cards"] == 6
    assert (out / "D6_SERVED_CONTROL_ROOM_LOCAL_INDEX_R1.html").exists()
