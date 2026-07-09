import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_synthetic_factory_seed_r3_cross_city_domain_fuel_preflight.py"
OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT"
STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_WITH_LIMITATIONS"
REQUIRED = [
    "SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_DECISION.json",
    "CITY_CORPUS_DISCOVERY_LEDGER.csv",
    "DOMAIN_FUEL_LEDGER.csv",
    "DOMAIN_FUEL_SUMMARY.json",
    "CROSS_CITY_DONOR_POLICY.json",
    "SEED_R3_RECOMMENDED_REFRESH_PLAN.json",
    "SEED_R3_PRODUCT_FIXTURE_REQUIREMENTS.json",
    "SEED_R3_BOUNDARY_AND_SOURCE_CLASS_AUDIT.json",
    "SEED_R3_NO_MUTATION_AUDIT.json",
    "SEED_R3_SECRET_SCAN_REPORT.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]


def run_script_once():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def load_json(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def load_csv(name):
    with (OUT / name).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_runner_produces_required_outputs():
    run_script_once()
    for name in REQUIRED:
        assert (OUT / name).exists(), name
    decision = load_json("SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_DECISION.json")
    assert decision["status"] == STATUS
    assert decision["package_sha256_match"] is True
    assert decision["recommend_seed_r3_refresh"] is True


def test_discovers_four_city_corpora_and_local_count_evidence():
    decision = load_json("SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_DECISION.json")
    city_rows = load_csv("CITY_CORPUS_DISCOVERY_LEDGER.csv")
    cities = {row["city"] for row in city_rows}
    assert {"barcelona", "nyc", "chicago", "london"}.issubset(cities)
    assert decision["city_roots_discovered"] >= 4
    assert decision["domain_fuel_ledger_rows"] > 0
    assert decision["verified_landed_rows"] > 0
    assert decision["verified_landed_features"] > 0
    assert any(int(row["dataset_status_sources"]) > 0 for row in city_rows)
    assert any(int(row["manifest_sources"]) > 0 for row in city_rows)


def test_priority_non_mobility_domains_are_covered():
    summary = load_json("DOMAIN_FUEL_SUMMARY.json")
    coverage = summary["priority_non_mobility_coverage"]
    for domain in [
        "property_planning",
        "built_environment",
        "building_compliance",
        "civic_service_311_crm",
        "environment_resilience",
        "data_quality_maturity",
        "identity_graph_eval",
    ]:
        assert coverage[domain]["present"], domain
    assert summary["priority_non_mobility_domains_present"] == summary["priority_non_mobility_domains_required"]


def test_domain_fuel_ledger_separates_source_classes_and_donor_boundaries():
    rows = load_csv("DOMAIN_FUEL_LEDGER.csv")
    domains = {row["domain"] for row in rows}
    assert "mobility_transport" in domains
    assert "building_compliance" in domains
    assert "property_planning" in domains
    source_classes = {row["source_class"] for row in rows}
    assert "source_record" in source_classes or "donor_context" in source_classes
    policy = load_json("CROSS_CITY_DONOR_POLICY.json")
    assert policy["truth_policy"]["not_dubai_official_truth"] is True
    assert policy["personal_data_policy"]["no_human_person_level_records"] is True


def test_boundary_no_mutation_and_secret_audits_pass():
    boundary = load_json("SEED_R3_BOUNDARY_AND_SOURCE_CLASS_AUDIT.json")
    mutation = load_json("SEED_R3_NO_MUTATION_AUDIT.json")
    secret = load_json("SEED_R3_SECRET_SCAN_REPORT.json")
    assert boundary["status"] == "PASS"
    assert boundary["no_seed_r3_generated_by_this_task"] is True
    assert boundary["no_official_dubai_truth_claim"] is True
    assert boundary["no_dispatch_control_enforcement_legal_certified_claim"] is True
    assert mutation["status"] == "PASS"
    assert mutation["mutated_prior_roots"] == []
    assert secret["status"] == "PASS"
    assert secret["hits"] == []


def test_hash_manifest_and_validate_only_pass():
    manifest = load_json("HASH_MANIFEST.json")
    hashed = {entry["path"] for entry in manifest["files"]}
    for name in REQUIRED:
        if name != "HASH_MANIFEST.json":
            assert name in hashed
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--validate-only"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    validation = json.loads(result.stdout)
    assert validation["validated"] is True
    assert validation["status"] == STATUS
