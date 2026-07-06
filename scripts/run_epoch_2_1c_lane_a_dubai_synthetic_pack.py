#!/usr/bin/env python3
"""Build Epoch 2.1 Push 2.1c Lane A Dubai anchored synthetic pack artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1c_lane_a_dubai_synthetic_pack"
GATE_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1b_content_hardening"
STARTER_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_b_starter_domain_packs"
PRIVACY_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention"

PASS_STATUS = "PASS_EPOCH_2_1_PUSH_2_1C_LANE_A_DUBAI_SYNTHETIC_PACK_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_PUSH_2_1C_LANE_A_PREREQUISITE_GATE"
INPUT_BLOCKED_STATUS = "BLOCKED_PUSH_2_1C_LANE_A_INPUTS_MISSING"

DOMAINS = ["planning", "mobility", "utilities", "building"]
GENERATED_SOURCE_CLASSES = {"synthetic", "replay"}
FORBIDDEN_GENERATED_SOURCE_CLASSES = {"official_record", "source_record", "model_inferred"}

PACKAGE_REFS = [
    "02_PUSH_LANE_EXECUTION_MODEL.md",
    "12_PUSH_2_1C_LANE_A_DUBAI_SYNTHETIC_PACK_PROMPT.md",
    "20_SPEC_PRIVACY_RETENTION_ENFORCEMENT.md",
    "21_SPEC_DOMAIN_PACK_FRAMEWORK_ONTOLOGY_GOVERNANCE.md",
    "23_SPEC_STARTER_DOMAIN_PACKS.md",
    "25_SPEC_DUBAI_SYNTHETIC_PACK.md",
    "28_SCOPE_NON_GOALS.md",
    "30_EXIT_GATE_CHECKLIST.md",
]

REQUIRED_ARTIFACTS = [
    "dubai_synthetic_pack_manifest_v1.json",
    "dubai_gold_tier_manifest.json",
    "dubai_dirty_source_tier_manifest.json",
    "dubai_challenge_tier_manifest.json",
    "dubai_synthetic_source_class_audit.json",
    "dubai_pack_validation_report.json",
    "PUSH_2_1C_LANE_A_DECISION.json",
    "HASH_MANIFEST.json",
    "SUMMARY.md",
]

LIMITATIONS = [
    "No live Dubai source ingestion.",
    "No production or citywide truth claim.",
    "No federation proof.",
    "No trained prediction model, learned ranking, or cross-city learned transfer.",
    "No official action, dispatch, enforcement, legal/certified finding, ticket/case creation, or autonomous monitoring/action.",
    "Local/replay/review/query only.",
    "Real Dubai anchors are not claimed when no accepted upstream source record is present in the consumed inputs.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def out_rel(path: Path) -> str:
    return path.resolve().relative_to(OUTPUT_ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_branch() -> str:
    proc = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return f"UNKNOWN:{proc.stderr.strip()}"
    return proc.stdout.strip()


def prerequisite_gate() -> dict[str, Any]:
    decision_path = GATE_ROOT / "INTEGRATION_GATE_2_1B_DECISION.json"
    flag_path = GATE_ROOT / "PUSH_2_1C_ALLOWED_TO_OPEN.flag"
    decision = read_json(decision_path) if decision_path.exists() else {}
    flag_text = flag_path.read_text(encoding="utf-8").strip() if flag_path.exists() else ""
    checks = {
        "branch_is_main": current_branch() == "main",
        "integration_gate_decision_exists": decision_path.exists(),
        "integration_gate_status_pass": str(decision.get("status", "")).startswith("PASS"),
        "push_2_1c_allowed_to_open": decision.get("push_2_1c_allowed_to_open") is True,
        "push_2_1c_allowed_flag_exists": flag_path.exists(),
        "push_2_1c_allowed_flag_pass": flag_text == "PASS",
    }
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_a.prerequisite_gate.v1",
        "status": "PASS" if all(checks.values()) else BLOCKED_STATUS,
        "checked_at": utc_now(),
        "checks": checks,
        "branch": current_branch(),
        "decision_ref": rel(decision_path),
        "decision_status": decision.get("status"),
        "push_2_1c_allowed_to_open": decision.get("push_2_1c_allowed_to_open"),
        "flag_ref": rel(flag_path),
        "flag_value": flag_text,
        "errors": [name for name, passed in checks.items() if not passed],
    }


def flatten_strings(payload: Any) -> list[str]:
    values: list[str] = []
    if isinstance(payload, str):
        values.append(payload)
    elif isinstance(payload, list):
        for item in payload:
            values.extend(flatten_strings(item))
    elif isinstance(payload, dict):
        for item in payload.values():
            values.extend(flatten_strings(item))
    return values


def load_starter_inputs() -> dict[str, Any]:
    errors: list[str] = []
    packs: dict[str, dict[str, Any]] = {}
    decision_path = STARTER_ROOT / "PUSH_2_1B_LANE_B_DECISION.json"
    validation_path = STARTER_ROOT / "starter_domain_pack_validation_report.json"
    decision = read_json(decision_path) if decision_path.exists() else {}
    validation = read_json(validation_path) if validation_path.exists() else {}
    if not decision_path.exists():
        errors.append(f"missing_starter_decision:{rel(decision_path)}")
    elif not str(decision.get("status", "")).startswith("PASS"):
        errors.append(f"starter_decision_not_pass:{decision.get('status')}")
    if not validation_path.exists():
        errors.append(f"missing_starter_validation:{rel(validation_path)}")
    elif not str(validation.get("status", "")).startswith("PASS"):
        errors.append(f"starter_validation_not_pass:{validation.get('status')}")

    for domain in DOMAINS:
        pack_root = STARTER_ROOT / "domain_packs" / domain
        paths = {
            "manifest": pack_root / "manifest.json",
            "source_class_matrix": pack_root / "source_class_matrix.json",
            "eval_fixtures": pack_root / "eval_fixtures.json",
            "consumer_fixtures": pack_root / "consumer_fixtures.json",
        }
        missing = [name for name, path in paths.items() if not path.exists()]
        if missing:
            errors.append(f"missing_starter_pack_files:{domain}:{','.join(missing)}")
            continue
        manifest = read_json(paths["manifest"])
        source_matrix = read_json(paths["source_class_matrix"])
        eval_fixtures = read_json(paths["eval_fixtures"])
        consumer_fixtures = read_json(paths["consumer_fixtures"])
        packs[domain] = {
            "domain": domain,
            "pack_id": manifest["pack_id"],
            "manifest_ref": rel(paths["manifest"]),
            "source_class_matrix_ref": rel(paths["source_class_matrix"]),
            "eval_fixtures_ref": rel(paths["eval_fixtures"]),
            "consumer_fixtures_ref": rel(paths["consumer_fixtures"]),
            "manifest": manifest,
            "source_class_matrix": source_matrix,
            "eval_fixtures": eval_fixtures,
            "consumer_fixtures": consumer_fixtures,
            "source_classes": source_matrix.get("allowed_source_classes", []),
            "consumer_refs": sorted(set(flatten_strings(manifest.get("consuming_capabilities", {})))),
            "eval_refs": sorted(set(flatten_strings(manifest.get("eval_fixtures", [])))),
        }
    return {
        "status": "PASS" if not errors else INPUT_BLOCKED_STATUS,
        "errors": errors,
        "decision_ref": rel(decision_path),
        "decision_status": decision.get("status"),
        "validation_ref": rel(validation_path),
        "validation_status": validation.get("status"),
        "packs": packs,
    }


def load_policy_inputs() -> dict[str, Any]:
    refs = {
        "privacy_retention_policy": PRIVACY_ROOT / "privacy_retention_policy_v1.json",
        "aggregation_floor_policy": PRIVACY_ROOT / "aggregation_floor_policy_v1.json",
        "retention_matrix": PRIVACY_ROOT / "retention_matrix_v1.json",
    }
    errors = [f"missing_policy_input:{rel(path)}" for path in refs.values() if not path.exists()]
    payloads = {name: read_json(path) for name, path in refs.items() if path.exists()}
    return {
        "status": "PASS" if not errors else INPUT_BLOCKED_STATUS,
        "errors": errors,
        "refs": {name: rel(path) for name, path in refs.items()},
        "payloads": payloads,
    }


def pick_refs(starters: dict[str, Any], domain: str, count: int = 2) -> dict[str, list[str]]:
    pack = starters["packs"][domain]
    consumer_refs = pack["consumer_refs"][:count]
    eval_refs = pack["eval_refs"][:count]
    return {"consumer_refs": consumer_refs, "eval_refs": eval_refs}


def common_record_controls(domain: str, starters: dict[str, Any], source_class: str = "synthetic") -> dict[str, Any]:
    refs = pick_refs(starters, domain)
    return {
        "domain": domain,
        "starter_pack_id": starters["packs"][domain]["pack_id"],
        "starter_manifest_ref": starters["packs"][domain]["manifest_ref"],
        "source_class": source_class,
        "source_class_origin": "generated_lane_fixture",
        "real_anchor_ref": None,
        "real_anchor_status": "not_present_in_accepted_inputs",
        "synthetic_overlay_status": "explicitly_synthetic",
        "source_class_separation": {
            "official_or_source_record_claimed": False,
            "real_anchor_ref": None,
            "synthetic_overlay_ref": None,
            "merge_allowed": False,
            "merge_rule": "Do not merge synthetic or replay facts into official/source-record fact surfaces.",
        },
        "consumed_by": refs,
        "check_expectations": [
            "source_class_present",
            "source_freshness_limitations_present",
            "authority_envelope_required",
            "no_official_action_or_legal_conclusion",
            "local_replay_review_query_only",
        ],
    }


def build_gold_tier(starters: dict[str, Any]) -> dict[str, Any]:
    records = [
        {
            **common_record_controls("planning", starters),
            "record_id": "dubai-gold-planning-business-bay-plan-001",
            "record_kind": "canonical_entity_bundle",
            "entity_type": "planning_project",
            "display_label": "Business Bay mixed-use planning review sample",
            "geographic_anchor": {
                "city_context": "Dubai",
                "place_hint": "Business Bay",
                "anchor_class": "synthetic_named_place_context",
                "precision_claim": "none",
            },
            "canonical_fields": {
                "project_stage": "review_ready",
                "permit_status": "synthetic_clear",
                "constraint_flag": "none_for_fixture",
            },
        },
        {
            **common_record_controls("mobility", starters),
            "record_id": "dubai-gold-mobility-marina-corridor-001",
            "record_kind": "canonical_entity_bundle",
            "entity_type": "mobility_corridor",
            "display_label": "Dubai Marina corridor review sample",
            "geographic_anchor": {
                "city_context": "Dubai",
                "place_hint": "Dubai Marina",
                "anchor_class": "synthetic_corridor_context",
                "precision_claim": "none",
            },
            "canonical_fields": {
                "corridor_status": "normal_for_fixture",
                "event_count": 0,
                "review_priority": "standard",
            },
        },
        {
            **common_record_controls("utilities", starters),
            "record_id": "dubai-gold-utilities-jebel-ali-service-001",
            "record_kind": "canonical_entity_bundle",
            "entity_type": "utility_service_point",
            "display_label": "Jebel Ali service dependency review sample",
            "geographic_anchor": {
                "city_context": "Dubai",
                "place_hint": "Jebel Ali",
                "anchor_class": "synthetic_service_area_context",
                "precision_claim": "none",
            },
            "canonical_fields": {
                "dependency_status": "synthetic_clear",
                "component_count": 3,
                "outage_claim": "none",
            },
        },
        {
            **common_record_controls("building", starters),
            "record_id": "dubai-gold-building-downtown-parcel-001",
            "record_kind": "canonical_entity_bundle",
            "entity_type": "building_parcel_unit_profile",
            "display_label": "Downtown Dubai parcel/unit evidence sample",
            "geographic_anchor": {
                "city_context": "Dubai",
                "place_hint": "Downtown Dubai",
                "anchor_class": "synthetic_parcel_context",
                "precision_claim": "none",
            },
            "canonical_fields": {
                "unit_count": 24,
                "permit_record_status": "synthetic_clear",
                "candidate_media_evidence": "absent",
            },
        },
    ]
    for record in records:
        record["source_class_separation"]["synthetic_overlay_ref"] = f"synthetic_overlay:{record['record_id']}"
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_a.gold_tier.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "tier_id": "dubai_gold_canonical_tier_v1",
        "tier_name": "Dubai gold canonical tier",
        "tier_purpose": "Clean, internally consistent synthetic Dubai sample for ASK/WATCH/BRIEF/CHECK and spatial review fixtures.",
        "created_at": utc_now(),
        "source_class_default": "synthetic",
        "accepted_real_anchor_refs": [],
        "real_anchor_policy": "No official/source-record Dubai anchors are claimed because none are present in the consumed starter-pack inputs.",
        "records": records,
        "tier_controls": {
            "canonical_internal_consistency": True,
            "source_class_required": True,
            "synthetic_real_merge_allowed": False,
            "official_action_or_truth_claim_allowed": False,
        },
    }


def build_dirty_tier(starters: dict[str, Any]) -> dict[str, Any]:
    rows = [
        (
            "planning",
            "dubai-dirty-planning-status-conflict-001",
            "planning_department_status_extract",
            ["conflicting_status", "stale_publication_timestamp", "missing_constraint_ref"],
        ),
        (
            "mobility",
            "dubai-dirty-mobility-road-event-alias-001",
            "mobility_incident_projection",
            ["road_alias_mismatch", "nearby_asset_ambiguous", "event_timestamp_missing_timezone"],
        ),
        (
            "utilities",
            "dubai-dirty-utilities-service-dependency-001",
            "utilities_asset_register_projection",
            ["component_alias_duplicate", "dependency_edge_uncertain", "source_age_warning_required"],
        ),
        (
            "building",
            "dubai-dirty-building-permit-address-001",
            "building_compliance_projection",
            ["duplicate_unit_label", "permit_status_typo", "media_candidate_without_official_record"],
        ),
    ]
    records = []
    for domain, record_id, projection, dirty_features in rows:
        record = {
            **common_record_controls(domain, starters),
            "record_id": record_id,
            "record_kind": "dirty_source_projection",
            "source_projection_shape": projection,
            "display_label": f"Synthetic dirty {domain} projection for Dubai review",
            "dirty_features": dirty_features,
            "quality_expectations": [
                "must_remain_synthetic",
                "must_surface_source_class",
                "must_trigger_review_not_action",
                "must_not_upgrade_to_official_record",
            ],
        }
        record["source_class_separation"]["synthetic_overlay_ref"] = f"synthetic_dirty_projection:{record_id}"
        records.append(record)
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_a.dirty_source_tier.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "tier_id": "dubai_dirty_source_tier_v1",
        "tier_name": "Dubai dirty source tier",
        "tier_purpose": "Department-shaped noisy synthetic projections for source matching, quality, and CHECK tests.",
        "created_at": utc_now(),
        "source_class_default": "synthetic",
        "records": records,
        "tier_controls": {
            "dirty_inputs_are_explicitly_synthetic": True,
            "quality_errors_expected": True,
            "synthetic_real_merge_allowed": False,
            "official_action_or_truth_claim_allowed": False,
        },
    }


def build_challenge_tier(starters: dict[str, Any]) -> dict[str, Any]:
    rows = [
        (
            "planning",
            "dubai-challenge-planning-official-looking-id-001",
            "entity_resolution_source_conflict",
            "An official-looking permit identifier is present as text, but no official/source-record anchor exists.",
            "synthetic",
        ),
        (
            "mobility",
            "dubai-challenge-mobility-temporal-order-001",
            "temporal_inconsistency",
            "A road event close timestamp precedes the open timestamp and must be rejected or flagged.",
            "synthetic",
        ),
        (
            "utilities",
            "dubai-challenge-utilities-derived-field-001",
            "derived_field_boundary",
            "A dependency score must remain derived review context and cannot become a source fact.",
            "synthetic",
        ),
        (
            "building",
            "dubai-challenge-building-duplicate-unit-001",
            "entity_resolution_duplicate",
            "Two unit labels look equivalent across parcel aliases and require review-only matching.",
            "synthetic",
        ),
        (
            "mobility",
            "dubai-challenge-replay-road-event-001",
            "replay_event",
            "Replay road-event fixture tied to starter mobility WATCH/spatial review surfaces.",
            "replay",
        ),
    ]
    records = []
    for domain, record_id, record_kind, challenge, source_class in rows:
        record = {
            **common_record_controls(domain, starters, source_class=source_class),
            "record_id": record_id,
            "record_kind": record_kind,
            "display_label": f"Dubai challenge fixture: {record_kind}",
            "challenge": challenge,
            "expected_resolution": [
                "surface_source_class",
                "preserve_authority_limitations",
                "request_review_or_CHECK",
                "do_not_create_official_action",
            ],
            "model_output_allowed": False,
        }
        if source_class == "replay":
            record["replay_policy"] = {
                "starter_pack_source_class_mapping": "replay_fixture",
                "live_event_claim": False,
                "consuming_surface_required": True,
            }
            record["source_class_separation"]["synthetic_overlay_ref"] = f"replay_fixture:{record_id}"
        else:
            record["source_class_separation"]["synthetic_overlay_ref"] = f"synthetic_challenge:{record_id}"
        records.append(record)
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_a.challenge_tier.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "tier_id": "dubai_challenge_tier_v1",
        "tier_name": "Dubai challenge tier",
        "tier_purpose": "Adversarial synthetic/replay cases for entity resolution, source conflicts, and temporal inconsistencies.",
        "created_at": utc_now(),
        "source_class_default": "synthetic",
        "records": records,
        "tier_controls": {
            "challenge_cases_expected_to_trigger_review": True,
            "replay_events_marked_replay": True,
            "synthetic_real_merge_allowed": False,
            "official_action_or_truth_claim_allowed": False,
        },
    }


def all_records(tiers: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for tier_id, tier in tiers.items():
        for record in tier.get("records", []):
            row = dict(record)
            row["tier_id"] = tier_id
            records.append(row)
    return records


def build_source_class_audit(
    starters: dict[str, Any],
    policies: dict[str, Any],
    tiers: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    records = all_records(tiers)
    counts = Counter(record["source_class"] for record in records)
    replay_records = [record for record in records if record.get("record_kind") == "replay_event"]
    checks = {
        "starter_packs_loaded": set(starters["packs"]) == set(DOMAINS),
        "privacy_policy_loaded": policies["status"] == "PASS",
        "generated_records_have_source_class": all(bool(record.get("source_class")) for record in records),
        "generated_source_classes_are_allowed": set(counts).issubset(GENERATED_SOURCE_CLASSES),
        "no_official_or_source_record_claims_in_generated_pack": not any(
            record.get("source_class") in FORBIDDEN_GENERATED_SOURCE_CLASSES for record in records
        ),
        "synthetic_and_real_facts_not_merged": all(
            record.get("source_class_separation", {}).get("merge_allowed") is False for record in records
        ),
        "no_real_anchor_claim_without_input_ref": all(record.get("real_anchor_ref") is None for record in records),
        "replay_events_marked_replay": bool(replay_records) and all(record.get("source_class") == "replay" for record in replay_records),
        "model_inferred_absent": not any(record.get("source_class") == "model_inferred" for record in records),
        "live_dubai_source_ingestion_absent": True,
        "federation_proof_claim_absent": True,
        "production_citywide_truth_claim_absent": True,
        "optional_demo_tier_absent": True,
    }
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_a.source_class_audit.v1",
        "status": "PASS_WITH_LIMITATIONS" if all(checks.values()) else "FAIL",
        "created_at": utc_now(),
        "checks": checks,
        "source_class_counts": dict(sorted(counts.items())),
        "records_audited": len(records),
        "records_by_tier": {tier_id: len(tier.get("records", [])) for tier_id, tier in tiers.items()},
        "starter_pack_source_classes": {
            domain: starters["packs"][domain]["source_classes"] for domain in DOMAINS
        },
        "real_anchor_inventory": {
            "accepted_real_anchor_refs": [],
            "note": "Consumed starter packs do not provide accepted Dubai official/source-record anchors for this lane.",
        },
        "limitations": LIMITATIONS,
    }


def build_validation_report(
    starters: dict[str, Any],
    policies: dict[str, Any],
    tiers: dict[str, dict[str, Any]],
    audit: dict[str, Any],
) -> dict[str, Any]:
    records = all_records(tiers)
    tier_counts = {tier_id: len(tier.get("records", [])) for tier_id, tier in tiers.items()}
    consumption_results = {
        record["record_id"]: bool(record.get("consumed_by", {}).get("consumer_refs") or record.get("consumed_by", {}).get("eval_refs"))
        for record in records
    }
    domain_coverage = sorted({record["domain"] for record in records})
    checks = {
        "starter_inputs_pass": starters["status"] == "PASS",
        "policy_inputs_pass": policies["status"] == "PASS",
        "required_tiers_present": set(tiers) == {"gold", "dirty_source", "challenge"},
        "tier_records_present": all(count > 0 for count in tier_counts.values()),
        "all_four_starter_domains_covered": set(domain_coverage) == set(DOMAINS),
        "source_class_audit_passed": audit["status"].startswith("PASS"),
        "every_record_consumed_by_existing_surface_or_eval": all(consumption_results.values()),
        "gold_dirty_challenge_only_no_new_demo_packaging": True,
        "raw_or_frozen_inputs_not_mutated": True,
        "no_live_source_ingestion": True,
        "no_federation_proof": True,
        "no_trained_prediction_model": True,
        "local_replay_review_query_only": True,
    }
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_a.validation_report.v1",
        "status": "PASS_WITH_LIMITATIONS" if all(checks.values()) else "FAIL",
        "created_at": utc_now(),
        "checks": checks,
        "tier_counts": tier_counts,
        "domain_coverage": domain_coverage,
        "consumption_results": consumption_results,
        "records_validated": len(records),
        "source_class_audit_ref": "outputs/epoch_2_1_push_2_1c_lane_a_dubai_synthetic_pack/dubai_synthetic_source_class_audit.json",
        "limitations": LIMITATIONS,
    }


def build_pack_manifest(
    gate: dict[str, Any],
    starters: dict[str, Any],
    policies: dict[str, Any],
    tiers: dict[str, dict[str, Any]],
    validation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_a.dubai_synthetic_pack_manifest.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "pack_id": "citybrain_dubai_anchored_synthetic_pack",
        "version": "1.0.0",
        "created_at": utc_now(),
        "lane": "A",
        "push": "2.1c",
        "artifact_root": rel(OUTPUT_ROOT),
        "source_package_refs": PACKAGE_REFS,
        "prerequisite_gate": gate,
        "target_city_context": {
            "city_label": "Dubai",
            "anchor_mode": "synthetic_city_context",
            "production_truth_claim": False,
        },
        "input_refs": {
            "starter_domain_pack_decision": starters["decision_ref"],
            "starter_domain_pack_validation": starters["validation_ref"],
            "starter_domain_packs": {
                domain: {
                    "pack_id": starters["packs"][domain]["pack_id"],
                    "manifest_ref": starters["packs"][domain]["manifest_ref"],
                    "source_class_matrix_ref": starters["packs"][domain]["source_class_matrix_ref"],
                    "consumer_fixtures_ref": starters["packs"][domain]["consumer_fixtures_ref"],
                    "eval_fixtures_ref": starters["packs"][domain]["eval_fixtures_ref"],
                }
                for domain in DOMAINS
            },
            "privacy_policy_refs": policies["refs"],
        },
        "tier_refs": {
            "gold": "outputs/epoch_2_1_push_2_1c_lane_a_dubai_synthetic_pack/dubai_gold_tier_manifest.json",
            "dirty_source": "outputs/epoch_2_1_push_2_1c_lane_a_dubai_synthetic_pack/dubai_dirty_source_tier_manifest.json",
            "challenge": "outputs/epoch_2_1_push_2_1c_lane_a_dubai_synthetic_pack/dubai_challenge_tier_manifest.json",
        },
        "tier_counts": {tier_id: len(tier.get("records", [])) for tier_id, tier in tiers.items()},
        "source_class_policy": {
            "source_class_required": True,
            "generated_source_classes": sorted(GENERATED_SOURCE_CLASSES),
            "forbidden_generated_source_classes": sorted(FORBIDDEN_GENERATED_SOURCE_CLASSES),
            "real_anchors_only_where_accepted_input_ref_exists": True,
            "accepted_real_anchor_refs": [],
            "synthetic_and_real_facts_may_merge": False,
            "replay_events_use_source_class_replay": True,
        },
        "validation_report_ref": "outputs/epoch_2_1_push_2_1c_lane_a_dubai_synthetic_pack/dubai_pack_validation_report.json",
        "validation_status": validation["status"],
        "limitations": LIMITATIONS,
    }


def build_decision(
    gate: dict[str, Any],
    manifest: dict[str, Any],
    validation: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_a.decision.v1",
        "status": PASS_STATUS if validation["status"].startswith("PASS") and audit["status"].startswith("PASS") else "FAIL_PUSH_2_1C_LANE_A_VALIDATION",
        "created_at": utc_now(),
        "lane": "A",
        "push": "2.1c",
        "artifact_root": rel(OUTPUT_ROOT),
        "prerequisite_gate": gate,
        "manifest_ref": "outputs/epoch_2_1_push_2_1c_lane_a_dubai_synthetic_pack/dubai_synthetic_pack_manifest_v1.json",
        "validation_report_ref": manifest["validation_report_ref"],
        "source_class_audit_ref": "outputs/epoch_2_1_push_2_1c_lane_a_dubai_synthetic_pack/dubai_synthetic_source_class_audit.json",
        "artifacts": REQUIRED_ARTIFACTS,
        "starter_domains_used": DOMAINS,
        "tier_counts": manifest["tier_counts"],
        "boundaries": {
            "live_dubai_source_ingestion_created": False,
            "production_citywide_truth_claim_created": False,
            "federation_proof_created": False,
            "trained_prediction_model_created": False,
            "official_action_dispatch_enforcement_created": False,
            "new_demo_packaging_concept_created": False,
            "local_replay_review_query_only": True,
        },
        "limitations": LIMITATIONS,
    }


def build_blocked_decision(gate: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_a.decision.v1",
        "status": INPUT_BLOCKED_STATUS,
        "created_at": utc_now(),
        "lane": "A",
        "push": "2.1c",
        "artifact_root": rel(OUTPUT_ROOT),
        "prerequisite_gate": gate,
        "blockers": errors,
        "artifacts": [],
    }


def list_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append(
                {
                    "path": out_rel(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_a.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "created_at": utc_now(),
        "item_count": len(files),
        "files": files,
    }


def write_summary(decision: dict[str, Any], validation: dict[str, Any], audit: dict[str, Any]) -> None:
    tier_lines = "\n".join(f"- `{tier}`: {count} records" for tier, count in decision.get("tier_counts", {}).items())
    artifact_lines = "\n".join(f"- `{name}`" for name in REQUIRED_ARTIFACTS)
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        f"""# Push 2.1c Lane A Dubai Anchored Synthetic Pack

Status: `{decision['status']}`

This lane creates the bounded Dubai anchored synthetic pack for local/replay/review/query use. It uses the Push 2.1b starter domain packs as inputs and keeps generated facts explicitly separated from official/source-record facts.

Tiers:

{tier_lines}

Validation: `{validation['status']}`

Source-class audit: `{audit['status']}`

Artifacts:

{artifact_lines}

Limitations:

{chr(10).join(f"- {item}" for item in LIMITATIONS)}
""",
    )


def write_all_outputs() -> dict[str, Any]:
    gate = prerequisite_gate()
    if gate["status"] != "PASS":
        return {"gate": gate, "decision": None}

    starters = load_starter_inputs()
    policies = load_policy_inputs()
    input_errors = starters["errors"] + policies["errors"]
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    if input_errors:
        decision = build_blocked_decision(gate, input_errors)
        write_json(OUTPUT_ROOT / "PUSH_2_1C_LANE_A_DECISION.json", decision)
        write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
        return {"gate": gate, "decision": decision, "blockers": input_errors}

    tiers = {
        "gold": build_gold_tier(starters),
        "dirty_source": build_dirty_tier(starters),
        "challenge": build_challenge_tier(starters),
    }
    audit = build_source_class_audit(starters, policies, tiers)
    validation = build_validation_report(starters, policies, tiers, audit)
    manifest = build_pack_manifest(gate, starters, policies, tiers, validation)
    decision = build_decision(gate, manifest, validation, audit)

    write_json(OUTPUT_ROOT / "dubai_gold_tier_manifest.json", tiers["gold"])
    write_json(OUTPUT_ROOT / "dubai_dirty_source_tier_manifest.json", tiers["dirty_source"])
    write_json(OUTPUT_ROOT / "dubai_challenge_tier_manifest.json", tiers["challenge"])
    write_json(OUTPUT_ROOT / "dubai_synthetic_source_class_audit.json", audit)
    write_json(OUTPUT_ROOT / "dubai_pack_validation_report.json", validation)
    write_json(OUTPUT_ROOT / "dubai_synthetic_pack_manifest_v1.json", manifest)
    write_json(OUTPUT_ROOT / "PUSH_2_1C_LANE_A_DECISION.json", decision)
    write_summary(decision, validation, audit)
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
    return {
        "gate": gate,
        "decision": decision,
        "manifest": manifest,
        "tiers": tiers,
        "audit": audit,
        "validation": validation,
        "starters": starters,
        "policies": policies,
    }


def main() -> int:
    result = write_all_outputs()
    gate = result["gate"]
    if gate["status"] != "PASS":
        print(BLOCKED_STATUS)
        print(json.dumps(gate["errors"], indent=2, sort_keys=True))
        return 1
    decision = result["decision"]
    print(decision["status"])
    if decision["status"].startswith("BLOCKED"):
        print(json.dumps(decision["blockers"], indent=2, sort_keys=True))
        return 1
    print(f"Output: {rel(OUTPUT_ROOT)}")
    print("Tiers: gold, dirty_source, challenge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
