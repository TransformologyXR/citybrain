import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_synthetic_factory_seed_r3_loop_convergence_event_adapter_r1.py"
PREFLIGHT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT"
PRODUCT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1"
REFRESH = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1"
OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-LOOP-CONVERGENCE-EVENT-ADAPTER-R1"
STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_R1_WITH_LIMITATIONS"
LOOP_FAMILIES = [
    "mobility_access",
    "building_compliance",
    "permit_inspection_delay",
    "asset_infrastructure",
]
REQUIRED_FILES = [
    "SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_DECISION.json",
    "LOOP_FAMILY_ALIGNMENT_REPORT.json",
    "LOOP_FAMILY_ALIAS_MAP_R1.json",
    "EVENT_FABRIC_SOURCE_ADAPTER_FEED_R1.jsonl",
    "SOURCE_ADAPTER_MANIFEST_R1.json",
    "PRODUCT_CONSUMPTION_READINESS_R1.json",
    "RESOLVER_STRESS_CASES_R1.jsonl",
    "EXPECTED_UNRESOLVED_AND_QUARANTINE_CASES_R1.jsonl",
    "CADENCE_REPLAY_PLAN_R1.json",
    "EVENT_FABRIC_INGESTION_CONTRACT_R1.json",
    "AI_DIAGNOSTIC_REVIEW_GATE_R1.md",
    "BOUNDARY_AND_NO_ACTION_AUDIT.json",
    "SECRET_SCAN_REPORT.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]


def run_adapter_once():
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seed-r3-preflight",
            str(PREFLIGHT),
            "--product-consumption",
            str(PRODUCT),
            "--seed-r3-refresh",
            str(REFRESH),
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


def test_runner_produces_required_event_adapter_outputs():
    run_adapter_once()
    for name in REQUIRED_FILES:
        assert (OUT / name).exists(), name
    decision = load_json("SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_DECISION.json")
    assert decision["status"] == STATUS
    assert decision["event_adapter_rows"] == 16
    assert decision["resolver_stress_cases"] == 8
    assert decision["expected_unresolved_or_quarantine_cases"] == 8
    assert decision["loop_families"] == LOOP_FAMILIES
    assert decision["canonical_family_alias_map"] == {
        "mobility_access": "mobility_access_interruption_v0",
        "building_compliance": "building_compliance_perception_candidate",
        "permit_inspection_delay": "permit_inspection_delay",
        "asset_infrastructure": "city_asset_infrastructure_issue",
    }
    assert decision["canonical_family_ids"] == [
        "mobility_access_interruption_v0",
        "building_compliance_perception_candidate",
        "permit_inspection_delay",
        "city_asset_infrastructure_issue",
    ]
    assert decision["input_summary"]["preflight_ledger_rows"] == 1467
    assert decision["input_summary"]["verified_landed_rows"] == 144375081
    assert decision["input_summary"]["verified_landed_features"] == 715566
    assert decision["input_summary"]["product_event_rows"] == 55
    assert decision["input_summary"]["product_watch_rows"] == 11
    assert decision["input_summary"]["product_check_rows"] == 11
    assert decision["input_summary"]["product_brief_rows"] == 11
    assert decision["input_summary"]["product_spatial_rows"] == 11
    assert decision["input_summary"]["optional_refresh_present"] is True
    assert decision["watch_check_brief_spatial_consumption_readiness"]["status"] == "PASS"


def test_event_fabric_adapter_feed_schema_and_loop_alignment():
    rows = load_jsonl("EVENT_FABRIC_SOURCE_ADAPTER_FEED_R1.jsonl")
    assert len(rows) == 16
    assert {row["loop_family"] for row in rows} == set(LOOP_FAMILIES)
    assert {row["canonical_loop_family_id"] for row in rows} == {
        "mobility_access_interruption_v0",
        "building_compliance_perception_candidate",
        "permit_inspection_delay",
        "city_asset_infrastructure_issue",
    }
    assert {row["truth_layer"] for row in rows} == {"gold", "dirty_source", "challenge", "scenario"}
    assert {row["source_adapter"] for row in rows} == {"synthetic_factory_seed_r3"}
    assert {row["schema_version"] for row in rows} == {"event_fabric_source_adapter.v1"}
    assert {row["expected_resolution_state"] for row in rows} == {
        "resolved",
        "unresolved_review",
        "quarantine_expected",
    }
    for row in rows:
        assert row["event_id"].startswith("seed-r3-adapter:")
        assert row["canonical_loop_family_id"]
        assert row["donor_refs"]
        assert row["candidate_entity_refs"]
        assert row["synthetic_truth_ref"].startswith("truth:seed-r3:")
        assert row["not_dubai_truth"] is True
        assert row["local_replay_only"] is True
        assert row["no_action_or_control"] is True
        assert "NOT_DUBAI_OFFICIAL_TRUTH" in row["limitation_refs"]
        assert "NO_ACTION_OR_CONTROL" in row["limitation_refs"]
        assert row["source_class"] in {
            "synthetic_gold",
            "synthetic_dirty_source",
            "synthetic_challenge",
            "synthetic_scenario",
        }


def test_reports_preserve_four_family_convergence_and_no_fixture_bypass():
    alignment = load_json("LOOP_FAMILY_ALIGNMENT_REPORT.json")
    alias_map = load_json("LOOP_FAMILY_ALIAS_MAP_R1.json")
    manifest = load_json("SOURCE_ADAPTER_MANIFEST_R1.json")
    contract = load_json("EVENT_FABRIC_INGESTION_CONTRACT_R1.json")
    assert alignment["status"] == "PASS"
    assert alignment["required_families"] == LOOP_FAMILIES
    assert alignment["all_required_families_present"] is True
    assert alignment["family_counts"] == {family: 4 for family in LOOP_FAMILIES}
    assert alignment["canonical_family_alias_map"] == alias_map["alias_map"]
    assert alignment["all_canonical_families_present"] is True
    assert alias_map["status"] == "PASS"
    assert alias_map["emitted_fields"] == ["loop_family", "canonical_loop_family_id"]
    assert manifest["source_adapter"] == "synthetic_factory_seed_r3"
    assert manifest["event_feed"] == "EVENT_FABRIC_SOURCE_ADAPTER_FEED_R1.jsonl"
    assert manifest["event_count"] == 16
    assert manifest["expected_resolution_counts"] == {
        "resolved": 8,
        "unresolved_review": 4,
        "quarantine_expected": 4,
    }
    assert contract["allowed_loop_families"] == LOOP_FAMILIES
    assert contract["canonical_family_alias_map"] == alias_map["alias_map"]
    assert "canonical_loop_family_id" in contract["required_fields"]
    assert "direct_D5_response" in contract["forbidden_bypass"]
    assert "direct_D6_card_without_event_fabric_ingest" in contract["forbidden_bypass"]


def test_resolver_stress_and_quarantine_cases_are_expected():
    stress = load_jsonl("RESOLVER_STRESS_CASES_R1.jsonl")
    quarantine = load_jsonl("EXPECTED_UNRESOLVED_AND_QUARANTINE_CASES_R1.jsonl")
    assert len(stress) == 8
    assert len(quarantine) == 8
    assert {case["stress_type"] for case in stress} == {"alias_collision", "weak_geometry_overlap"}
    assert {case["expected_bucket"] for case in quarantine} == {
        "unresolved_review",
        "quarantine_expected",
    }
    for case in stress:
        assert case["must_preserve_source_records"] is True
        assert case["must_not_merge_without_evidence"] is True
        assert case["loop_family"] in LOOP_FAMILIES
        assert case["canonical_loop_family_id"] in {
            "mobility_access_interruption_v0",
            "building_compliance_perception_candidate",
            "permit_inspection_delay",
            "city_asset_infrastructure_issue",
        }
    for case in quarantine:
        assert case["must_surface_in_quality_report"] is True
        assert case["loop_family"] in LOOP_FAMILIES
        assert case["canonical_loop_family_id"] in {
            "mobility_access_interruption_v0",
            "building_compliance_perception_candidate",
            "permit_inspection_delay",
            "city_asset_infrastructure_issue",
        }


def test_cadence_and_ai_gate_are_replay_diagnostic_only():
    cadence = load_json("CADENCE_REPLAY_PLAN_R1.json")
    assert cadence["status"] == "PLAN_READY_LOCAL_REPLAY_ONLY"
    assert cadence["not_live_ingestion"] is True
    assert {mode["mode"] for mode in cadence["modes"]} == {
        "batch",
        "10x",
        "60x",
        "wall_clock_simulated",
    }
    gate = (OUT / "AI_DIAGNOSTIC_REVIEW_GATE_R1.md").read_text(encoding="utf-8")
    assert "diagnostic gate only" in gate
    assert "training fuel" in gate
    assert "founder review" in gate


def test_watch_check_brief_spatial_consumption_readiness_is_context_not_bypass():
    readiness = load_json("PRODUCT_CONSUMPTION_READINESS_R1.json")
    assert readiness["status"] == "PASS"
    assert readiness["direct_fixture_bypass_allowed"] is False
    assert readiness["counts"] == {
        "WATCH": 11,
        "CHECK": 11,
        "BRIEF": 11,
        "SPATIAL": 11,
        "EVENT_REPLAY": 55,
    }
    assert readiness["surface_readiness"] == {
        "WATCH": True,
        "CHECK": True,
        "BRIEF": True,
        "SPATIAL": True,
    }
    assert "must still enter through Event Fabric" in readiness["limitation"]


def test_boundary_secret_and_hash_audits_pass():
    boundary = load_json("BOUNDARY_AND_NO_ACTION_AUDIT.json")
    for flag in [
        "seed_r3_preflight_read_only",
        "product_consumption_read_only",
        "seed_r3_refresh_read_only_if_present",
        "factory_as_event_fabric_adapter",
        "local_replay_only",
        "synthetic_replay_donor_context_only",
        "not_dubai_official_truth",
        "no_live_monitoring_claim",
        "no_public_api_claim",
        "no_production_frontend_claim",
        "no_dispatch_control_enforcement_legal_certified_claim",
        "no_human_person_level_records",
        "no_raw_provider_payloads_packaged",
        "no_credentials_written",
    ]:
        assert boundary[flag] is True
    assert boundary["standalone_fixture_only"] is False

    secret = load_json("SECRET_SCAN_REPORT.json")
    assert secret["status"] == "PASS"
    assert secret["finding_count"] == 0

    manifest = load_json("HASH_MANIFEST.json")
    assert manifest["file_count"] == len(REQUIRED_FILES) - 1
    for entry in manifest["files"]:
        path = OUT / entry["path"]
        assert path.exists(), entry["path"]
        assert path.stat().st_size == entry["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seed-r3-preflight",
            str(PREFLIGHT),
            "--product-consumption",
            str(PRODUCT),
            "--seed-r3-refresh",
            str(REFRESH),
            "--out",
            str(OUT),
            "--validate-only",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    validation = json.loads(result.stdout)
    assert validation["validated"] is True
    assert validation["status"] == STATUS
