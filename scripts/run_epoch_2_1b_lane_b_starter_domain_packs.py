#!/usr/bin/env python3
"""Epoch 2.1 Push 2.1b Lane B starter domain-pack runner."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_epoch_2_1a_lane_b_domain_framework import (  # noqa: E402
    CONSUMING_CAPABILITY_FIELDS,
    SOURCE_CLASS_ALLOWED_VALUES,
    stable_hash,
    validate_domain_pack_manifest,
)


OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_b_starter_domain_packs"
GATE_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1a_foundations"
GATE_DECISION_PATH = GATE_ROOT / "INTEGRATION_GATE_2_1A_DECISION.json"
GATE_FLAG_PATH = GATE_ROOT / "PUSH_2_1B_ALLOWED_TO_OPEN.flag"

PASS_STATUS = "PASS_PUSH_2_1B_LANE_B_STARTER_DOMAIN_PACKS_WITH_LIMITATIONS"
BLOCK_STATUS = "BLOCKED_PUSH_2_1B_LANE_B_PREREQUISITE_GATE"
DOMAINS = ["planning", "mobility", "utilities", "building"]

PACKAGE_REFS = [
    "02_PUSH_LANE_EXECUTION_MODEL.md",
    "09_PUSH_2_1B_LANE_B_STARTER_DOMAIN_PACKS_PROMPT.md",
    "21_SPEC_DOMAIN_PACK_FRAMEWORK_ONTOLOGY_GOVERNANCE.md",
    "23_SPEC_STARTER_DOMAIN_PACKS.md",
    "28_SCOPE_NON_GOALS.md",
    "30_EXIT_GATE_CHECKLIST.md",
]

NON_GOALS = [
    "No Dubai synthetic pack.",
    "No live source onboarding.",
    "No trained model, ranking, prediction, learning loop, or cross-city learned transfer.",
    "No domain autonomous agents.",
    "No official legal, government, dispatch, enforcement, or certified conclusion.",
    "Local/replay/review/query only.",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return f"UNKNOWN:{result.stderr.strip()}"
    return result.stdout.strip()


def check_prerequisite_gate() -> dict[str, Any]:
    errors: list[str] = []
    branch = current_branch()
    if branch != "main":
        errors.append(f"branch_not_main:{branch}")

    gate_decision: dict[str, Any] = {}
    if not GATE_DECISION_PATH.exists():
        errors.append(f"missing_gate_decision:{rel(GATE_DECISION_PATH)}")
    else:
        gate_decision = read_json(GATE_DECISION_PATH)
        if not str(gate_decision.get("status", "")).startswith("PASS"):
            errors.append(f"gate_status_not_pass:{gate_decision.get('status')}")
        if gate_decision.get("push_2_1b_allowed_to_open") is not True:
            errors.append("push_2_1b_allowed_to_open_not_true")

    flag_value = ""
    if not GATE_FLAG_PATH.exists():
        errors.append(f"missing_gate_flag:{rel(GATE_FLAG_PATH)}")
    else:
        flag_value = GATE_FLAG_PATH.read_text(encoding="utf-8").strip()
        if flag_value != "PASS":
            errors.append(f"gate_flag_not_pass:{flag_value}")

    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_b.prerequisite_gate.v1",
        "status": "PASS" if not errors else BLOCK_STATUS,
        "checked_at": utc_now(),
        "branch": branch,
        "gate_decision_ref": rel(GATE_DECISION_PATH),
        "gate_decision_status": gate_decision.get("status"),
        "push_2_1b_allowed_to_open": gate_decision.get("push_2_1b_allowed_to_open"),
        "gate_flag_ref": rel(GATE_FLAG_PATH),
        "gate_flag_value": flag_value,
        "errors": errors,
    }


def domain_configs() -> dict[str, dict[str, Any]]:
    return {
        "planning": {
            "display_name": "Planning Starter Domain Pack",
            "summary": "Review planning projects, permits, constraints, source depth, stale records, and status packets.",
            "entities": ["planning_project", "planning_application", "planning_constraint_area"],
            "relationships": [
                "planning_application_relates_to_parcel",
                "planning_project_has_status_record",
                "planning_constraint_applies_to_place",
            ],
            "core_refs": ["entity:place", "entity:parcel", "entity:source_record", "relationship:has_evidence"],
            "source_classes": ["official_record", "licensed_open_data", "operator_entered", "replay_fixture", "derived_field"],
            "source_freshness": {
                "official_record": "Interpret record timestamps as the source publication/update time, not as CityBrain truth.",
                "licensed_open_data": "Flag as stale when the dataset publication date is older than 30 days unless the source declares a slower cadence.",
                "operator_entered": "Requires reviewer timestamp and provenance; never upgrades candidate claims to official findings.",
                "derived_field": "Derived only from cited source records and recomputed during replay.",
            },
            "consuming_capabilities": {
                "ask_templates": [
                    "ask:planning:permit_project_source_depth:v1",
                    "ask:planning:project_status_evidence:v1",
                ],
                "brief_templates": ["brief:planning:status_packet:v1"],
                "watch_families": ["watch:planning:stale_or_contradictory_records:v1"],
                "plan_schedule_simulate_fixtures": ["plan:planning:hearing_schedule_review_fixture:v1"],
            },
            "app_surfaces": ["ask", "brief", "watch", "plan_review"],
            "spatial_overlays": ["overlay:planning:application_parcel_context:v1", "overlay:planning:constraint_area_context:v1"],
            "evals": [
                ("eval:planning:permit_project_source_depth:v1", "ASK", "Answers must separate candidate status from cited official and licensed source records."),
                ("eval:planning:status_packet_brief:v1", "BRIEF", "Briefs must include limitations, freshness, CHECK refs, and no official conclusion."),
                ("eval:planning:stale_record_watch:v1", "WATCH", "Watches must flag stale or contradictory records for review only."),
                ("eval:planning:hearing_schedule_review:v1", "PLAN", "Schedule review fixture must remain local/replay and non-executing."),
            ],
        },
        "mobility": {
            "display_name": "Mobility Starter Domain Pack",
            "summary": "Review road, route, stop, incident, and event context with spatial overlays for operator query/replay.",
            "entities": ["mobility_corridor", "mobility_event", "transit_stop_context"],
            "relationships": [
                "mobility_event_affects_corridor",
                "route_serves_stop_context",
                "incident_near_transport_asset",
            ],
            "core_refs": ["entity:road_segment", "entity:place", "entity:event", "relationship:near"],
            "source_classes": ["official_record", "licensed_open_data", "operator_entered", "replay_fixture", "derived_field", "media_evidence"],
            "source_freshness": {
                "official_record": "Official incident or works timestamps are treated as source-published time only.",
                "licensed_open_data": "Scheduled route or asset datasets must surface the feed date and stale-feed warning.",
                "media_evidence": "Media may support review context but cannot be the sole fact source.",
                "derived_field": "Distance and overlay joins are replay-derived and must preserve source links.",
            },
            "consuming_capabilities": {
                "ask_templates": [
                    "ask:mobility:route_road_incident_context:v1",
                    "ask:mobility:event_near_asset_context:v1",
                ],
                "watch_families": ["watch:mobility:event_near_road_or_asset:v1"],
                "spatial_overlay_fixtures": ["overlay_fixture:mobility:road_event_context:v1"],
            },
            "app_surfaces": ["ask", "watch", "spatial_review"],
            "spatial_overlays": ["overlay:mobility:road_event_context:v1", "overlay:mobility:route_stop_context:v1"],
            "evals": [
                ("eval:mobility:route_road_incident_context:v1", "ASK", "Answers must cite source class, source age, and confidence limits."),
                ("eval:mobility:event_near_asset_watch:v1", "WATCH", "Watch output must request review rather than dispatch or control."),
                ("eval:mobility:road_event_overlay:v1", "SPATIAL", "Overlay fixture must preserve geometry source refs and no live traffic claim."),
            ],
        },
        "utilities": {
            "display_name": "Utilities Starter Domain Pack",
            "summary": "Review service points, facilities, components, service events, and dependency context without operational control.",
            "entities": ["utility_service_point", "utility_facility", "utility_component"],
            "relationships": [
                "service_point_connected_to_facility",
                "component_part_of_utility_network",
                "service_event_affects_component",
            ],
            "core_refs": ["entity:asset", "entity:event", "entity:source_record", "relationship:depends_on"],
            "source_classes": ["official_record", "licensed_open_data", "operator_entered", "replay_fixture", "derived_field"],
            "source_freshness": {
                "official_record": "Asset and event registers carry their own validity date; CityBrain exposes that date and does not certify current service.",
                "licensed_open_data": "Network or facility datasets require publication cadence and stale warning.",
                "operator_entered": "Operator notes are review context only and require CHECK before surfaced claims.",
                "derived_field": "Dependency joins are replay-derived and may not imply outage prediction.",
            },
            "consuming_capabilities": {
                "ask_templates": [
                    "ask:utilities:service_point_facility_component_context:v1",
                    "ask:utilities:dependency_source_depth:v1",
                ],
                "watch_families": ["watch:utilities:unresolved_service_event_context:v1"],
                "diff_fixtures": ["diff:utilities:dependency_graph_review_fixture:v1"],
            },
            "app_surfaces": ["ask", "watch", "diff_review"],
            "spatial_overlays": ["overlay:utilities:service_point_facility_context:v1"],
            "evals": [
                ("eval:utilities:service_point_context:v1", "ASK", "Answers must distinguish registered asset facts from derived dependency context."),
                ("eval:utilities:unresolved_service_event_watch:v1", "WATCH", "Watch fixture must identify review gaps without dispatch or repair action."),
                ("eval:utilities:dependency_graph_diff:v1", "DIFF", "Diff fixture must expose changed relationships and rollback path."),
            ],
        },
        "building": {
            "display_name": "Building and Permits Starter Domain Pack",
            "summary": "Review building, parcel, unit, permit, media evidence, and candidate-vs-verified claim packets.",
            "entities": ["building_record", "building_unit_context", "building_permit_event"],
            "relationships": [
                "building_record_relates_to_parcel",
                "permit_event_updates_building_record",
                "media_evidence_observes_building_candidate",
            ],
            "core_refs": ["entity:building", "entity:parcel", "entity:media_evidence", "relationship:has_evidence"],
            "source_classes": ["official_record", "licensed_open_data", "operator_entered", "replay_fixture", "derived_field", "media_evidence"],
            "source_freshness": {
                "official_record": "Permit and building records expose filing, issue, update, and source retrieval dates separately.",
                "licensed_open_data": "Parcel/building datasets must surface publication cadence and stale warnings.",
                "media_evidence": "Media evidence supports candidate review only and requires source record linkage.",
                "derived_field": "Candidate-vs-verified splits are replay-derived and must cite CHECK refs.",
            },
            "consuming_capabilities": {
                "ask_templates": [
                    "ask:building:parcel_unit_profile:v1",
                    "ask:building:permit_record_evidence_depth:v1",
                ],
                "brief_templates": ["brief:building:evidence_packet:v1"],
                "perception_review_fixtures": ["perception:building:candidate_vs_verified_review_fixture:v1"],
            },
            "app_surfaces": ["ask", "brief", "perception_review", "spatial_review"],
            "spatial_overlays": ["overlay:building:parcel_unit_context:v1"],
            "evals": [
                ("eval:building:parcel_unit_profile:v1", "ASK", "Answers must cite official/derived/media source classes separately."),
                ("eval:building:evidence_packet_brief:v1", "BRIEF", "Brief fixture must preserve limitations and no legal conclusion."),
                ("eval:building:candidate_vs_verified_check:v1", "CHECK", "CHECK fixture must keep candidate media observations separate from verified records."),
            ],
        },
    }


def flatten_capability_refs(consuming: dict[str, list[str]]) -> list[str]:
    refs: list[str] = []
    for field in CONSUMING_CAPABILITY_FIELDS:
        refs.extend(consuming.get(field, []))
    return refs


def governance_row(
    domain: str,
    addition_type: str,
    ref: str,
    purpose: str,
    source_classes: list[str],
    consumer_surface: str,
    eval_fixture_ids: list[str],
) -> dict[str, Any]:
    return {
        "ref": ref,
        "purpose": purpose,
        "source_class_allowed_values": source_classes,
        "evidence_requirements": [
            "Every surfaced claim must cite source_record_id, source_class, and retrieval_or_publication timestamp.",
            "Candidate claims require CHECK review before being represented as verified context.",
        ],
        "check_rules": [
            "requires_check_report",
            "requires_authority_envelope",
            "source_freshness_review_required",
            "no_official_action_or_legal_conclusion",
        ],
        "required_tests": [
            f"tests/test_epoch_2_1b_lane_b_starter_domain_packs.py::{domain}_manifest_validation",
            f"eval_fixture_presence:{domain}",
        ],
        "eval_fixtures": eval_fixture_ids,
        "consumer_surface": consumer_surface,
        "compatibility_version": "2.1b-starter-v1",
        "rollback_deprecation_path": f"rollback:{domain}:{ref}:remove_or_replace:v1",
    }


def build_manifest(domain: str, config: dict[str, Any]) -> dict[str, Any]:
    eval_fixture_ids = [row[0] for row in config["evals"]]
    consuming = config["consuming_capabilities"]
    capability_refs = flatten_capability_refs(consuming)
    governance_additions = {
        "entity_types": [
            governance_row(
                domain,
                "entity_types",
                f"entity:{entity}",
                f"Domain starter entity for {config['display_name']}: {entity}.",
                config["source_classes"],
                "ontology",
                eval_fixture_ids,
            )
            for entity in config["entities"]
        ],
        "relationship_types": [
            governance_row(
                domain,
                "relationship_types",
                f"relationship:{relationship}",
                f"Domain starter relationship for {config['display_name']}: {relationship}.",
                config["source_classes"],
                "ontology",
                eval_fixture_ids,
            )
            for relationship in config["relationships"]
        ],
        "source_mappings": [
            governance_row(
                domain,
                "source_mappings",
                f"source_mapping:{domain}:starter_records:v1",
                f"Maps replay and registered source records into the {domain} starter pack without onboarding live sources.",
                config["source_classes"],
                "source_registry",
                eval_fixture_ids,
            )
        ],
        "ask_templates": [
            governance_row(domain, "ask_templates", ref, f"ASK template for {domain} starter review.", config["source_classes"], "ASK", eval_fixture_ids)
            for ref in consuming.get("ask_templates", [])
        ],
        "watch_families": [
            governance_row(domain, "watch_families", ref, f"WATCH family for {domain} review-only monitoring.", config["source_classes"], "WATCH", eval_fixture_ids)
            for ref in consuming.get("watch_families", [])
        ],
        "brief_templates": [
            governance_row(domain, "brief_templates", ref, f"BRIEF template for {domain} evidence packet generation.", config["source_classes"], "BRIEF", eval_fixture_ids)
            for ref in consuming.get("brief_templates", [])
        ],
        "spatial_overlays": [
            governance_row(domain, "spatial_overlays", ref, f"Spatial overlay handoff for {domain} review context.", config["source_classes"], "SPATIAL", eval_fixture_ids)
            for ref in config["spatial_overlays"]
        ],
    }
    if consuming.get("perception_review_fixtures"):
        governance_additions["perception_classes"] = [
            governance_row(
                domain,
                "perception_classes",
                ref,
                f"Perception review class fixture for {domain} candidate evidence.",
                config["source_classes"],
                "PERCEPTION_REVIEW",
                eval_fixture_ids,
            )
            for ref in consuming["perception_review_fixtures"]
        ]
    if any(ref.startswith("tool:") or ref.startswith("connector:") for ref in capability_refs):
        governance_additions["tools_connectors"] = [
            governance_row(domain, "tools_connectors", ref, f"Connector reference for {domain}.", config["source_classes"], "CONNECTOR", eval_fixture_ids)
            for ref in capability_refs
            if ref.startswith("tool:") or ref.startswith("connector:")
        ]

    return {
        "pack_id": f"citybrain_starter_{domain}_domain_pack",
        "version": "1.0.0",
        "domain": domain,
        "source_class_policy": {
            "allowed_source_classes": config["source_classes"],
            "source_class_required": True,
            "vss_as_fact_source_allowed": False,
            "freshness_interpretation": config["source_freshness"],
            "missing_or_stale_source_policy": "surface as unknown_or_stale_with_limitations; do not upgrade to current fact",
            "live_source_onboarding_allowed": False,
        },
        "consuming_capabilities": consuming,
        "eval_fixtures": eval_fixture_ids,
        "check_expectations": {
            "requires_check_report": True,
            "requires_authority_envelope": True,
            "candidate_vs_verified_split_required": True,
            "source_freshness_review_required": True,
            "source_limitations_required": True,
            "official_or_legal_conclusion_allowed": False,
        },
        "authority_profile": {
            "max_authority_level": 3,
            "no_execution_authority": True,
            "allowed_modes": ["ASK", "WATCH", "BRIEF", "CHECK", "DIFF", "SPATIAL_REVIEW", "REPLAY"],
            "forbidden_actions": ["official_submission", "dispatch", "control", "enforcement", "legal_finding"],
        },
        "entity_relationship_refs": {
            "core_refs": config["core_refs"],
            "entity_type_additions": [f"entity:{entity}" for entity in config["entities"]],
            "relationship_type_additions": [f"relationship:{relationship}" for relationship in config["relationships"]],
            "source_mapping_refs": [f"source_mapping:{domain}:starter_records:v1"],
        },
        "app_spatial_handoff_profile": {
            "app_surface_refs": [f"app:{surface}" for surface in config["app_surfaces"]],
            "spatial_overlay_profile": {
                "overlay_refs": config["spatial_overlays"],
                "handoff_mode": "review_only",
                "requires_source_record_clickthrough": True,
                "no_live_control_or_dispatch": True,
            },
        },
        "compatibility": {
            "manifest_version": "1.0.0",
            "compatibility_version": "2.1b-starter-v1",
            "breaking_change_policy": "integration_gate_review_required_for_source_class, ontology, consumer, eval, check, authority, or handoff changes",
        },
        "limitations": [
            config["summary"],
            "Starter pack only; it registers framework-governed domain surfaces and replay/eval fixtures.",
            "No live source onboarding, production deployment, official submission, dispatch, control, enforcement, or legal conclusion.",
            "No trained model, ranking, prediction, learning loop, or autonomous domain agent.",
            "Source freshness is interpreted from cited source metadata and surfaced as limitations, not certified current truth.",
        ],
        "rollback_ref": f"rollback:starter_domain_pack:{domain}:v1",
        "deprecation_path": {
            "owner": "CityBrain domain-pack governance",
            "notice": f"Deprecating {domain} starter pack requires a replacement/removal note and gate review.",
            "replacement_or_removal_path": f"Remove or replace {domain} manifests, fixtures, source mappings, consumer refs, and registration rows in a new governed push.",
        },
        "governance_additions": governance_additions,
    }


def build_consumer_fixture(domain: str, config: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_b.consumer_fixtures.v1",
        "domain": domain,
        "pack_id": manifest["pack_id"],
        "consuming_capabilities": manifest["consuming_capabilities"],
        "fixture_rules": {
            "must_have_at_least_one_consumer": True,
            "all_consumers_are_review_query_or_replay_only": True,
            "must_preserve_check_and_authority_refs": True,
            "must_surface_source_freshness_limitations": True,
        },
        "mode_fixture_refs": [row[0] for row in config["evals"]],
    }


def build_eval_fixture(domain: str, config: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_b.eval_fixtures.v1",
        "domain": domain,
        "pack_id": manifest["pack_id"],
        "fixtures": [
            {
                "fixture_id": fixture_id,
                "mode": mode,
                "purpose": purpose,
                "expected_controls": [
                    "source_class_present",
                    "check_report_required",
                    "authority_envelope_required",
                    "source_freshness_limitations_present",
                    "no_official_action_or_legal_conclusion",
                ],
            }
            for fixture_id, mode, purpose in config["evals"]
        ],
    }


def build_source_class_matrix(domain: str, config: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_b.source_class_matrix.v1",
        "domain": domain,
        "pack_id": manifest["pack_id"],
        "allowed_source_classes": manifest["source_class_policy"]["allowed_source_classes"],
        "source_class_required": True,
        "vss_as_fact_source_allowed": False,
        "freshness_interpretation": manifest["source_class_policy"]["freshness_interpretation"],
        "requirements": [
            "Every source row requires source_class.",
            "Every answer or packet must disclose freshness, source limitations, and CHECK/Authority requirements.",
            "Media evidence and derived fields cannot stand alone as official fact sources.",
            "Replay fixture data is local/replay only and must not be presented as live source onboarding.",
        ],
    }


def readme_text(domain: str, config: dict[str, Any], manifest: dict[str, Any]) -> str:
    capability_refs = flatten_capability_refs(manifest["consuming_capabilities"])
    return f"""# {config['display_name']}

Status: starter domain pack, local/replay/review/query only.

Pack id: `{manifest['pack_id']}`

This pack registers the starter ontology refs/additions, source-class policy,
consumer capability refs, eval fixtures, CHECK/Authority expectations,
app/spatial handoff profile, compatibility metadata, and rollback/deprecation
path for `{domain}`.

Consuming capability refs:

{chr(10).join(f"- `{ref}`" for ref in capability_refs)}

Limitations:

{chr(10).join(f"- {item}" for item in manifest['limitations'])}
"""


def write_domain_pack(domain: str, config: dict[str, Any]) -> dict[str, Any]:
    manifest = build_manifest(domain, config)
    pack_root = OUTPUT_ROOT / "domain_packs" / domain
    write_json(pack_root / "manifest.json", manifest)
    write_json(pack_root / "consumer_fixtures.json", build_consumer_fixture(domain, config, manifest))
    write_json(pack_root / "eval_fixtures.json", build_eval_fixture(domain, config, manifest))
    write_json(pack_root / "source_class_matrix.json", build_source_class_matrix(domain, config, manifest))
    write_text(pack_root / "README.md", readme_text(domain, config, manifest))
    return manifest


def validate_generated_manifests(manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pack_results = {}
    for domain, manifest in manifests.items():
        validation = validate_domain_pack_manifest(manifest)
        pack_results[domain] = {
            "status": validation["status"],
            "errors": validation["errors"],
            "manifest_hash": validation["manifest_hash"],
            "manifest_ref": f"outputs/epoch_2_1_push_2_1b_lane_b_starter_domain_packs/domain_packs/{domain}/manifest.json",
            "consumer_ref_count": len(flatten_capability_refs(manifest["consuming_capabilities"])),
            "eval_fixture_count": len(manifest["eval_fixtures"]),
            "source_class_count": len(manifest["source_class_policy"]["allowed_source_classes"]),
            "check_authority_required": (
                manifest["check_expectations"]["requires_check_report"] is True
                and manifest["check_expectations"]["requires_authority_envelope"] is True
            ),
        }

    negative_base = next(iter(manifests.values()))
    no_consumer = json.loads(json.dumps(negative_base))
    no_consumer["pack_id"] = "negative_no_consumer_starter_pack"
    no_consumer["consuming_capabilities"] = {}
    no_eval = json.loads(json.dumps(negative_base))
    no_eval["pack_id"] = "negative_no_eval_starter_pack"
    no_eval["eval_fixtures"] = []
    negative_results = {
        "no_consuming_capability": validate_domain_pack_manifest(no_consumer),
        "no_eval_fixtures": validate_domain_pack_manifest(no_eval),
    }
    all_packs_pass = all(row["status"] == "PASS" for row in pack_results.values())
    negative_guards_pass = (
        "no_consuming_capability" in negative_results["no_consuming_capability"]["errors"]
        and "no_eval_fixtures" in negative_results["no_eval_fixtures"]["errors"]
    )
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_b.validation_report.v1",
        "status": "PASS" if all_packs_pass and negative_guards_pass else "FAIL",
        "created_at": utc_now(),
        "validator_ref": "outputs/epoch_2_1_push_2_1a_lane_b_domain_framework/domain_pack_validator.py",
        "pack_results": pack_results,
        "negative_fixture_results": negative_results,
    }


def build_eval_fixtures_report(manifests: dict[str, dict[str, Any]], configs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_b.eval_fixtures_report.v1",
        "status": "PASS",
        "created_at": utc_now(),
        "domains": {
            domain: {
                "pack_id": manifests[domain]["pack_id"],
                "mode_fixture_refs": [row[0] for row in configs[domain]["evals"]],
                "mode_coverage": sorted({row[1] for row in configs[domain]["evals"]}),
                "consuming_capability_refs": flatten_capability_refs(manifests[domain]["consuming_capabilities"]),
                "check_authority_and_source_freshness_expected": True,
            }
            for domain in DOMAINS
        },
    }


def build_corpus_append_report(manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for domain in DOMAINS:
        manifest = manifests[domain]
        rows.append(
            {
                "domain": domain,
                "pack_id": manifest["pack_id"],
                "manifest_ref": f"outputs/epoch_2_1_push_2_1b_lane_b_starter_domain_packs/domain_packs/{domain}/manifest.json",
                "registration_kind": "starter_domain_pack_manifest",
                "source_of_truth_append_row": {
                    "artifact_type": "domain_pack_manifest",
                    "status": "proposed_registration_only",
                    "source_class_policy_ref": f"outputs/epoch_2_1_push_2_1b_lane_b_starter_domain_packs/domain_packs/{domain}/source_class_matrix.json",
                    "consumer_fixture_ref": f"outputs/epoch_2_1_push_2_1b_lane_b_starter_domain_packs/domain_packs/{domain}/consumer_fixtures.json",
                    "eval_fixture_ref": f"outputs/epoch_2_1_push_2_1b_lane_b_starter_domain_packs/domain_packs/{domain}/eval_fixtures.json",
                },
                "mutation_performed": False,
            }
        )
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_b.corpus_source_of_truth_append_report.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "created_at": utc_now(),
        "mutation_performed": False,
        "frozen_upstream_outputs_mutated": False,
        "note": "Registration rows are emitted as an append report only; frozen corpus/source-of-truth files are not modified in this lane.",
        "registration_entries": rows,
    }


def build_decision(gate: dict[str, Any], manifests: dict[str, dict[str, Any]], validation_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_b.decision.v1",
        "status": PASS_STATUS if validation_report["status"] == "PASS" else "FAIL_PUSH_2_1B_LANE_B_STARTER_DOMAIN_PACKS_VALIDATION",
        "created_at": utc_now(),
        "lane": "B",
        "push": "2.1b",
        "artifact_root": rel(OUTPUT_ROOT),
        "prerequisite_gate": gate,
        "source_package_refs": PACKAGE_REFS,
        "starter_domains": DOMAINS,
        "starter_pack_count": len(manifests),
        "starter_pack_ids": {domain: manifest["pack_id"] for domain, manifest in manifests.items()},
        "validation_report_ref": "outputs/epoch_2_1_push_2_1b_lane_b_starter_domain_packs/starter_domain_pack_validation_report.json",
        "eval_fixtures_report_ref": "outputs/epoch_2_1_push_2_1b_lane_b_starter_domain_packs/starter_domain_pack_eval_fixtures_report.json",
        "corpus_source_of_truth_append_report_ref": "outputs/epoch_2_1_push_2_1b_lane_b_starter_domain_packs/corpus_source_of_truth_append_report.json",
        "rules": {
            "used_2_1a_domain_pack_validator": True,
            "pack_with_no_consuming_capability_must_not_merge": True,
            "eval_fixtures_required": True,
            "source_class_required": True,
            "check_authority_required": True,
            "source_freshness_limitations_required": True,
            "app_spatial_handoff_profile_required": True,
            "compatibility_versioning_required": True,
            "rollback_deprecation_required": True,
        },
        "boundaries": {
            "dubai_pack_created": False,
            "live_source_onboarding_created": False,
            "trained_model_created": False,
            "ranking_prediction_or_learning_loop_created": False,
            "domain_autonomous_agents_created": False,
            "official_legal_or_government_conclusion_created": False,
            "local_replay_review_query_only": True,
        },
        "limitations": NON_GOALS,
    }


def list_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append(
                {
                    "path": path.resolve().relative_to(OUTPUT_ROOT.resolve()).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_b.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "created_at": utc_now(),
        "item_count": len(files),
        "files": files,
    }


def write_summary(decision: dict[str, Any], validation_report: dict[str, Any]) -> None:
    pack_lines = "\n".join(
        f"- `{domain}`: `{pack_id}`"
        for domain, pack_id in decision["starter_pack_ids"].items()
    )
    validation_lines = "\n".join(
        f"- `{domain}`: `{row['status']}` ({row['consumer_ref_count']} consumers, {row['eval_fixture_count']} eval fixtures)"
        for domain, row in validation_report["pack_results"].items()
    )
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        f"""# Push 2.1b Lane B Starter Domain Packs

Status: `{decision['status']}`

Created the allowed starter domain packs only:

{pack_lines}

Validation:

{validation_lines}

Boundaries preserved:

{chr(10).join(f"- {item}" for item in NON_GOALS)}

This lane does not close Epoch 2.1.
""",
    )


def write_all_outputs() -> dict[str, Any]:
    gate = check_prerequisite_gate()
    if gate["status"] != "PASS":
        return {"gate": gate, "decision": None}

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    configs = domain_configs()
    manifests = {domain: write_domain_pack(domain, configs[domain]) for domain in DOMAINS}
    validation_report = validate_generated_manifests(manifests)
    eval_report = build_eval_fixtures_report(manifests, configs)
    corpus_report = build_corpus_append_report(manifests)
    write_json(OUTPUT_ROOT / "starter_domain_pack_validation_report.json", validation_report)
    write_json(OUTPUT_ROOT / "starter_domain_pack_eval_fixtures_report.json", eval_report)
    write_json(OUTPUT_ROOT / "corpus_source_of_truth_append_report.json", corpus_report)
    decision = build_decision(gate, manifests, validation_report)
    write_json(OUTPUT_ROOT / "PUSH_2_1B_LANE_B_DECISION.json", decision)
    write_summary(decision, validation_report)
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
    return {
        "gate": gate,
        "decision": decision,
        "manifests": manifests,
        "validation_report": validation_report,
        "eval_report": eval_report,
        "corpus_report": corpus_report,
    }


def main() -> int:
    result = write_all_outputs()
    gate = result["gate"]
    if gate["status"] != "PASS":
        print(BLOCK_STATUS)
        print(json.dumps(gate["errors"], indent=2, sort_keys=True))
        return 1
    decision = result["decision"]
    print(decision["status"])
    print(f"Output: {rel(OUTPUT_ROOT)}")
    print(f"Starter packs: {', '.join(DOMAINS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
