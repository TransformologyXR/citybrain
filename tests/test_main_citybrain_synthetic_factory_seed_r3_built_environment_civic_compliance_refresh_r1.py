import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_synthetic_factory_seed_r3_built_environment_civic_compliance_refresh_r1.py"
PREFLIGHT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT"
PRODUCT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1"
OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1"
STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R3_BUILT_ENVIRONMENT_CIVIC_COMPLIANCE_REFRESH_R1_WITH_LIMITATIONS"

REQUIRED_OUTPUTS = [
    "SEED_R3_BEE_CIVIC_COMPLIANCE_DECISION.json",
    "SEED_R3_DOMAIN_SELECTION_LEDGER.csv",
    "SEED_R3_SYNTHETIC_ENTITY_REFRESH.jsonl",
    "EVENT_REPLAY_SEED_R3.jsonl",
    "WATCH_SEED_R3.jsonl",
    "ASK_SEED_R3.jsonl",
    "CHECK_SEED_R3.jsonl",
    "BRIEF_SEED_R3.jsonl",
    "SPATIAL_SEED_R3.jsonl",
    "QUALITY_MATURITY_FIXTURES_SEED_R3.jsonl",
    "CROSS_CITY_DONOR_DISTRIBUTION_REPORT.json",
    "BOUNDARY_AND_NO_ACTION_AUDIT.json",
    "SECRET_SCAN_REPORT.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]


def run_refresh_once():
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seed-r3-preflight",
            str(PREFLIGHT),
            "--product-consumption",
            str(PRODUCT),
            "--out",
            str(OUT),
        ],
        cwd=ROOT,
        check=True,
    )


def load_json(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def load_jsonl(name):
    rows = []
    for line in (OUT / name).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_csv(name):
    with (OUT / name).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_refresh_runner_produces_required_outputs():
    run_refresh_once()
    for name in REQUIRED_OUTPUTS:
        assert (OUT / name).exists(), name
    decision = load_json("SEED_R3_BEE_CIVIC_COMPLIANCE_DECISION.json")
    assert decision["status"] == STATUS
    assert decision["readable_name"] == "Seed R3 Built Environment + Civic + Compliance Refresh"
    assert decision["seed_r3_preflight_status"] == "PASS_SYNTHETIC_FACTORY_SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_WITH_LIMITATIONS"


def test_counts_and_domain_coverage_match_contract():
    decision = load_json("SEED_R3_BEE_CIVIC_COMPLIANCE_DECISION.json")
    counts = decision["counts"]
    assert counts["preflight_ledger_rows_consumed"] == 1467
    assert counts["domain_selection_rows"] == 29
    for key in ["entity_refresh_rows", "event_replay_rows", "watch_rows", "ask_rows", "check_rows", "brief_rows", "spatial_rows"]:
        assert counts[key] == 29
    assert counts["quality_maturity_rows"] == 9

    assert set(decision["priority_domains_covered"]) == {
        "property_planning",
        "built_environment",
        "building_compliance",
        "civic_service_311_crm",
        "environment_resilience",
        "data_quality_maturity",
        "identity_graph_eval",
    }
    assert {"barcelona", "nyc", "chicago", "london"}.issubset(set(decision["cities_covered"]))


def test_selection_ledger_uses_city_specific_preflight_counts():
    rows = load_csv("SEED_R3_DOMAIN_SELECTION_LEDGER.csv")
    assert len(rows) == 29
    lookup = {(row["city"], row["domain"]): row for row in rows}
    assert int(lookup[("barcelona", "property_planning")]["landed_features"]) == 715566
    assert int(lookup[("nyc", "building_compliance")]["landed_rows"]) == 15299386
    assert int(lookup[("london", "building_compliance")]["landed_rows"]) == 0
    assert int(lookup[("chicago", "environment_resilience")]["landed_rows"]) == 6598621


def assert_fixture_rows(name, expected):
    rows = load_jsonl(name)
    assert len(rows) == expected
    for row in rows:
        assert row["source_class"] == "cross_city_donor_context"
        assert row["truth_layer"] == "synthetic_replay_donor_derived"
        assert row["donor_refs"]
        assert row["limitation_refs"]
        assert row["not_dubai_truth"] is True
        assert row["synthetic_replay_only"] is True
        assert row["review_only"] is True
        assert row["no_action_claim"] is True
    return rows


def test_product_fixture_jsonl_rows_are_parseable_and_bounded():
    assert_fixture_rows("SEED_R3_SYNTHETIC_ENTITY_REFRESH.jsonl", 29)
    assert_fixture_rows("EVENT_REPLAY_SEED_R3.jsonl", 29)
    assert_fixture_rows("WATCH_SEED_R3.jsonl", 29)
    assert_fixture_rows("ASK_SEED_R3.jsonl", 29)
    check_rows = assert_fixture_rows("CHECK_SEED_R3.jsonl", 29)
    assert {row["claimability"] for row in check_rows} == {"cannot_claim_as_dubai_truth"}
    assert_fixture_rows("BRIEF_SEED_R3.jsonl", 29)
    assert_fixture_rows("SPATIAL_SEED_R3.jsonl", 29)
    assert_fixture_rows("QUALITY_MATURITY_FIXTURES_SEED_R3.jsonl", 9)


def test_donor_report_and_boundary_audits_pass():
    report = load_json("CROSS_CITY_DONOR_DISTRIBUTION_REPORT.json")
    assert report["selection_count"] == 29
    assert report["preflight_verified_landed_rows"] == 144375081
    assert report["preflight_verified_landed_features"] == 715566
    assert report["policy"] == "cross-city corpora are donor/context only and do not become Dubai official truth"
    for domain in [
        "property_planning",
        "built_environment",
        "building_compliance",
        "civic_service_311_crm",
        "environment_resilience",
        "data_quality_maturity",
        "identity_graph_eval",
    ]:
        assert domain in report["by_domain"]

    boundary = load_json("BOUNDARY_AND_NO_ACTION_AUDIT.json")
    for flag in [
        "cross_city_donor_context_only",
        "not_dubai_official_truth",
        "no_human_person_level_records",
        "no_credentials_written",
        "no_raw_bulky_data_packaged",
        "no_live_monitoring_claim",
        "no_public_api_claim",
        "no_production_frontend_claim",
        "no_dispatch_control_enforcement_legal_certified_claim",
        "prior_outputs_read_only",
        "synthetic_replay_review_only",
        "seed_r2_not_replaced",
    ]:
        assert boundary[flag] is True

    secret = load_json("SECRET_SCAN_REPORT.json")
    assert secret["status"] == "PASS"
    assert secret["hits"] == []


def test_hash_manifest_and_validate_only_pass():
    manifest = load_json("HASH_MANIFEST.json")
    hashed = {entry["path"] for entry in manifest["files"]}
    for name in REQUIRED_OUTPUTS:
        if name != "HASH_MANIFEST.json":
            assert name in hashed
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seed-r3-preflight",
            str(PREFLIGHT),
            "--product-consumption",
            str(PRODUCT),
            "--out",
            str(OUT),
            "--validate-only",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "VALIDATE_ONLY_PASS" in result.stdout
