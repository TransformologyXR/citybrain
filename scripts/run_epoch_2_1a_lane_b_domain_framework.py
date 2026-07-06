#!/usr/bin/env python3
"""Epoch 2.1 Push 2.1a Lane B domain-pack framework runner.

The runner performs the Epoch 2.0 entry check first. If the gate fails it emits
only the required entry-check gap report files and stops. If the gate passes it
emits the Lane B framework and ontology-governance artifacts.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_b_domain_framework"
EPOCH20_ROOT = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation"
EPOCH20_REPORTS = EPOCH20_ROOT / "reports"
EPOCH20_AUDITS = EPOCH20_ROOT / "audits"

PASS_STATUS = "PASS_PUSH_2_1A_LANE_B_DOMAIN_FRAMEWORK_WITH_LIMITATIONS"
BLOCK_STATUS = "BLOCKED_EPOCH_2_1_MISSING_2_0_AGENT_RECERTIFICATION_LEDGER"

MANDATORY_COMPONENTS = {
    "Watch Scout": "watch_scout",
    "Diff Scout": "diff_scout",
    "CHECK Agent": "check_agent",
    "Approval Lifecycle Agent": "approval_lifecycle_agent",
    "Spatial Agent": "spatial_agent",
    "Perception / Media Agent": "perception_media_agent",
}

SOURCE_CLASS_ALLOWED_VALUES = [
    "official_record",
    "licensed_open_data",
    "operator_entered",
    "replay_fixture",
    "synthetic_fixture",
    "derived_field",
    "media_evidence",
    "narrative_context",
]

CONSUMING_CAPABILITY_FIELDS = [
    "ask_templates",
    "watch_families",
    "brief_templates",
    "diff_fixtures",
    "recall_matcher_fixtures",
    "spatial_overlay_fixtures",
    "perception_review_fixtures",
    "plan_schedule_simulate_fixtures",
]

GOVERNED_ADDITION_TYPES = [
    "entity_types",
    "relationship_types",
    "source_mappings",
    "tools_connectors",
    "ask_templates",
    "watch_families",
    "brief_templates",
    "spatial_overlays",
    "perception_classes",
]

NON_GOALS = [
    "No starter packs.",
    "No Dubai pack.",
    "No live source.",
    "No trained model.",
    "No agent activation.",
    "No official ticket/case submission.",
    "No dispatch/control/enforcement.",
    "No legal/certified finding.",
    "No autonomous execution.",
    "No live CCTV claim.",
    "No identity/biometric inference.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def reset_output_root() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def list_hash_manifest() -> dict[str, Any]:
    files: list[dict[str, Any]] = []
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
        "schema_version": "citybrain.epoch_2_1.push_2_1a.lane_b.hash_manifest.v1",
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(files),
        "files": files,
    }


def check_epoch_2_0_entry() -> dict[str, Any]:
    required_paths = {
        "ComponentRegistry v1": EPOCH20_ROOT / "component_registry_v1.json",
        "AgentRunEnvelope v1": EPOCH20_ROOT / "agent_run_envelope_v1.json",
        "ToolPermissionPolicy v1": EPOCH20_ROOT / "tool_permission_policy_v1.json",
        "ModeInvocationRegistry v1": EPOCH20_ROOT / "mode_invocation_registry_v1.json",
        "LLM seat registry": EPOCH20_ROOT / "llm_seat_registry_v1.json",
        "Budget / Stop Policy": EPOCH20_ROOT / "budget_stop_policy_v1.json",
        "Replay Harness v1": EPOCH20_ROOT / "replay_harness_manifest_v1.json",
        "Mode Eval Harness v1": EPOCH20_ROOT / "mode_eval_harness_manifest_v1.json",
        "2.0 ledger / final published status": EPOCH20_ROOT / "final_published_status.json",
        "2.0 hash manifest": EPOCH20_ROOT / "hash_manifest.json",
        "2.0 source-of-truth matrix update": EPOCH20_REPORTS / "path_mapping.json",
        "2.0 preflight inventory": EPOCH20_REPORTS / "preflight_inventory.json",
        "Agent recertification report": EPOCH20_REPORTS / "agent_recertification_report.json",
        "Replay harness report": EPOCH20_REPORTS / "replay_harness_report.json",
        "Mode eval harness report": EPOCH20_REPORTS / "mode_eval_harness_report.json",
        "Tool permission audit": EPOCH20_REPORTS / "tool_permission_policy_audit.json",
        "Budget stop policy audit": EPOCH20_REPORTS / "budget_stop_policy_audit.json",
        "No official action audit": EPOCH20_AUDITS / "no_official_action_audit.json",
        "No learned model audit": EPOCH20_AUDITS / "no_learned_model_audit.json",
    }
    missing_paths = [label for label, path in required_paths.items() if not path.exists()]

    component_registry = read_json(required_paths["ComponentRegistry v1"], [])
    if isinstance(component_registry, dict):
        component_rows = component_registry.get("components", component_registry.get("items", []))
    else:
        component_rows = component_registry
    component_ids = {row.get("component_id") for row in component_rows if isinstance(row, dict)}

    recert = read_json(required_paths["Agent recertification report"], {"rows": []})
    recert_rows = {row.get("component_id"): row for row in recert.get("rows", [])}
    replay_report = read_json(required_paths["Replay harness report"], {})
    mode_eval = read_json(required_paths["Mode eval harness report"], {})
    final_status = read_json(required_paths["2.0 ledger / final published status"], {})
    tool_audit = read_json(required_paths["Tool permission audit"], {})
    budget_audit = read_json(required_paths["Budget stop policy audit"], {})
    no_official = read_json(required_paths["No official action audit"], {})
    no_learned = read_json(required_paths["No learned model audit"], {})
    path_mapping = read_json(required_paths["2.0 source-of-truth matrix update"], {})
    preflight = read_json(required_paths["2.0 preflight inventory"], {})

    mandatory_rows: dict[str, dict[str, Any]] = {}
    missing_components: list[str] = []
    missing_recert_rows: list[str] = []
    missing_replay_refs: list[str] = []
    failing_recert_rows: list[str] = []
    for label, component_id in MANDATORY_COMPONENTS.items():
        if component_id not in component_ids:
            missing_components.append(label)
        row = recert_rows.get(component_id)
        if not row:
            missing_recert_rows.append(label)
            continue
        mandatory_rows[label] = row
        if row.get("status") != "PASS":
            failing_recert_rows.append(label)
        if not row.get("replay_or_eval_ref"):
            missing_replay_refs.append(label)

    preflight_paths = [item.get("path") for item in preflight.get("required_inputs", []) if isinstance(item, dict)]
    source_truth_ok = bool(path_mapping.get("source_of_truth_base")) and (
        "outputs/epoch1_closedown_certified_baseline/EPOCH1_SOURCE_OF_TRUTH_MATRIX.json" in preflight_paths
        or (REPO_ROOT / "outputs" / "epoch1_closedown_certified_baseline" / "EPOCH1_SOURCE_OF_TRUTH_MATRIX.json").exists()
    )

    replay_ok = replay_report.get("status") == "PASS" and replay_report.get("agent_run_envelope", {}).get("status") == "emitted"
    mode_scorecard_ok = mode_eval.get("status") == "PASS" and mode_eval.get("active_mode_count", 0) > 0 and bool(mode_eval.get("slots"))
    permissions_ok = tool_audit.get("status") == "PASS" and budget_audit.get("status") == "PASS"
    boundaries_ok = (
        no_official.get("status") == "PASS"
        and no_learned.get("status") == "PASS"
        and final_status.get("data_dependency_changes") is False
        and final_status.get("sealed_artifacts_touched") is False
    )
    final_ok = str(final_status.get("status", "")).startswith("PASS_EPOCH_2_0")
    gaps = {
        "missing_required_inputs": missing_paths,
        "missing_mandatory_components": missing_components,
        "missing_recertification_rows": missing_recert_rows,
        "mandatory_rows_without_replay_or_eval_ref": missing_replay_refs,
        "failing_recertification_rows": failing_recert_rows,
        "replay_harness_not_passing_or_missing_envelope": [] if replay_ok else ["Replay harness report is not PASS or AgentRunEnvelope was not emitted."],
        "mode_scorecard_missing_or_not_passing": [] if mode_scorecard_ok else ["Mode eval harness report is not PASS or has no active slots."],
        "permission_or_budget_policy_not_passing": [] if permissions_ok else ["Tool permission audit or budget/stop policy audit is not PASS."],
        "boundary_audits_not_passing": [] if boundaries_ok else ["No-official-action/no-learned-model/final boundary checks are not PASS."],
        "source_of_truth_matrix_update_missing": [] if source_truth_ok else ["No Epoch 2.0 source-of-truth mapping to the certified matrix was found."],
        "final_status_not_passing": [] if final_ok else ["Epoch 2.0 final published status is not PASS."],
    }
    flat_gaps = [item for values in gaps.values() for item in values]
    return {
        "schema_version": "citybrain.epoch_2_1.entry_check.report.v1",
        "status": "PASS" if not flat_gaps else BLOCK_STATUS,
        "created_at": utc_now(),
        "required_paths": {label: rel(path) for label, path in required_paths.items()},
        "mandatory_components": MANDATORY_COMPONENTS,
        "mandatory_recertification_index": mandatory_rows,
        "mode_scorecard_ref": rel(required_paths["Mode eval harness report"]),
        "replay_harness_ref": rel(required_paths["Replay harness report"]),
        "source_of_truth_ref": rel(required_paths["2.0 source-of-truth matrix update"]),
        "gaps": gaps,
        "pass_criteria": {
            "mandatory_components_registered": not missing_components,
            "mandatory_agents_recertified": not missing_recert_rows and not failing_recert_rows,
            "mandatory_agents_have_replay_or_eval_refs": not missing_replay_refs,
            "replay_harness_emits_agent_run_envelope": replay_ok,
            "mode_scorecard_published": mode_scorecard_ok,
            "tool_permissions_and_budget_stop_apply": permissions_ok,
            "no_official_or_learned_behavior": boundaries_ok,
            "source_of_truth_matrix_update_present": source_truth_ok,
            "final_status_passing": final_ok,
        },
    }


def write_entry_gap_report(entry: dict[str, Any]) -> None:
    write_json(OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_REPORT.json", entry)
    lines = ["# Epoch 2.0 Entry Check Gaps", "", f"Status: `{entry['status']}`", ""]
    for category, values in entry["gaps"].items():
        if values:
            lines.append(f"## {category}")
            lines.extend(f"- {value}" for value in values)
            lines.append("")
    write_text(OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_GAPS.md", "\n".join(lines))


def write_entry_pass_outputs(entry: dict[str, Any]) -> None:
    decision = {
        "schema_version": "citybrain.epoch_2_1.entry_check.decision.v1",
        "status": "PASS_EPOCH_2_0_ENTRY_CHECK",
        "created_at": utc_now(),
        "allowed_to_open_epoch_2_1": True,
        "entry_report_ref": "outputs/epoch_2_1_push_2_1a_lane_b_domain_framework/EPOCH_2_0_ENTRY_CHECK_DECISION.json",
        "pass_criteria": entry["pass_criteria"],
    }
    write_json(OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_DECISION.json", decision)
    write_text(
        OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_SUMMARY.md",
        """# Epoch 2.0 Entry Check Summary

Status: `PASS_EPOCH_2_0_ENTRY_CHECK`

Epoch 2.0 has a published ComponentRegistry, AgentRunEnvelope, ToolPermissionPolicy,
ModeInvocationRegistry, LLM seat registry, budget/stop policy, replay harness,
mode-eval harness, final status, hash manifest, source-of-truth mapping, and
mandatory agent recertification rows.
""",
    )
    write_json(
        OUTPUT_ROOT / "EPOCH_2_0_AGENT_RECERTIFICATION_INDEX.json",
        {
            "schema_version": "citybrain.epoch_2_1.entry_check.agent_recertification_index.v1",
            "status": "PASS",
            "mandatory_components": entry["mandatory_components"],
            "rows": entry["mandatory_recertification_index"],
        },
    )
    write_text(OUTPUT_ROOT / "EPOCH_2_1_ALLOWED_TO_OPEN.flag", "PASS_EPOCH_2_0_ENTRY_CHECK\n")


def domain_pack_manifest_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "DomainPackManifestV1",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "pack_id",
            "version",
            "domain",
            "source_class_policy",
            "consuming_capabilities",
            "eval_fixtures",
            "check_expectations",
            "authority_profile",
            "entity_relationship_refs",
            "app_spatial_handoff_profile",
            "compatibility",
            "limitations",
            "rollback_ref",
            "deprecation_path",
        ],
        "properties": {
            "pack_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_\\-\\.]+$"},
            "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
            "domain": {"type": "string"},
            "source_class_policy": {
                "type": "object",
                "required": ["allowed_source_classes", "source_class_required", "vss_as_fact_source_allowed"],
                "properties": {
                    "allowed_source_classes": {"type": "array", "items": {"enum": SOURCE_CLASS_ALLOWED_VALUES}, "minItems": 1},
                    "source_class_required": {"const": True},
                    "vss_as_fact_source_allowed": {"const": False},
                },
                "additionalProperties": True,
            },
            "consuming_capabilities": {"type": "object", "minProperties": 1},
            "eval_fixtures": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "check_expectations": {"type": "object", "required": ["requires_check_report", "requires_authority_envelope"]},
            "authority_profile": {"type": "object", "required": ["max_authority_level", "no_execution_authority"]},
            "entity_relationship_refs": {"type": "object"},
            "app_spatial_handoff_profile": {"type": "object", "required": ["app_surface_refs", "spatial_overlay_profile"]},
            "compatibility": {"type": "object", "required": ["manifest_version", "compatibility_version", "breaking_change_policy"]},
            "limitations": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "rollback_ref": {"type": "string"},
            "deprecation_path": {"type": "object", "required": ["owner", "notice", "replacement_or_removal_path"]},
            "governance_additions": {"type": "object"},
        },
        "must_not_merge_if": [
            "no_consuming_capability",
            "no_eval_fixtures",
            "unapproved_entity_or_relationship_type",
            "missing_check_expectations",
            "source_class_policy_missing",
            "missing_app_spatial_handoff_profile",
            "missing_compatibility_version",
            "missing_rollback_or_deprecation_path",
        ],
    }


def validate_domain_pack_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    schema = domain_pack_manifest_schema()
    errors: list[str] = []
    for field in schema["required"]:
        if field not in manifest:
            errors.append(f"missing_required:{field}")
    if manifest.get("pack_kind") in {"starter_pack", "dubai_pack"}:
        errors.append("forbidden_pack_kind_in_2_1a_lane_b")
    source_policy = manifest.get("source_class_policy", {})
    if not source_policy.get("source_class_required"):
        errors.append("source_class_required_false")
    allowed_classes = source_policy.get("allowed_source_classes", [])
    if not allowed_classes:
        errors.append("source_class_policy_missing")
    unknown_classes = sorted(set(allowed_classes) - set(SOURCE_CLASS_ALLOWED_VALUES))
    if unknown_classes:
        errors.append(f"unknown_source_class:{','.join(unknown_classes)}")
    if source_policy.get("vss_as_fact_source_allowed") is not False:
        errors.append("vss_as_fact_source_must_be_false")
    consuming = manifest.get("consuming_capabilities", {})
    if not any(consuming.get(field) for field in CONSUMING_CAPABILITY_FIELDS):
        errors.append("no_consuming_capability")
    if not manifest.get("eval_fixtures"):
        errors.append("no_eval_fixtures")
    checks = manifest.get("check_expectations", {})
    if checks.get("requires_check_report") is not True or checks.get("requires_authority_envelope") is not True:
        errors.append("missing_check_or_authority_requirement")
    authority = manifest.get("authority_profile", {})
    if authority.get("no_execution_authority") is not True:
        errors.append("execution_authority_not_blocked")
    if not manifest.get("app_spatial_handoff_profile", {}).get("spatial_overlay_profile"):
        errors.append("missing_app_spatial_handoff_profile")
    compatibility = manifest.get("compatibility", {})
    if not compatibility.get("compatibility_version") or not compatibility.get("breaking_change_policy"):
        errors.append("missing_compatibility_versioning")
    if not manifest.get("rollback_ref") or not manifest.get("deprecation_path"):
        errors.append("missing_rollback_or_deprecation_path")
    additions = manifest.get("governance_additions", {})
    for addition_type, rows in additions.items():
        if addition_type not in GOVERNED_ADDITION_TYPES:
            errors.append(f"unknown_governed_addition_type:{addition_type}")
            continue
        for index, row in enumerate(rows if isinstance(rows, list) else []):
            for required in ["purpose", "source_class_allowed_values", "evidence_requirements", "check_rules", "required_tests", "eval_fixtures", "consumer_surface", "compatibility_version", "rollback_deprecation_path"]:
                if not row.get(required):
                    errors.append(f"governance_addition_missing:{addition_type}:{index}:{required}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "checked_at": utc_now(),
        "manifest_hash": stable_hash(manifest),
    }


def validator_source() -> str:
    return '''"""Deterministic DomainPackManifestV1 validator artifact.

Generated by scripts/run_epoch_2_1a_lane_b_domain_framework.py.
"""

from scripts.run_epoch_2_1a_lane_b_domain_framework import validate_domain_pack_manifest

__all__ = ["validate_domain_pack_manifest"]
'''


def write_lane_b_artifacts(entry: dict[str, Any]) -> dict[str, Any]:
    schema = domain_pack_manifest_schema()
    write_text(
        OUTPUT_ROOT / "domain_pack_framework_v1.md",
        f"""# Domain-Pack Framework v1

Status: framework-only. This lane publishes zero starter packs and zero Dubai pack.

Domain packs are governed vertical bundles over existing CityBrain modes. A pack
is not an agent, not a live source, not a trained model, and not an activation
surface. Pack merge is blocked unless the manifest validates and the pack has a
real consuming capability plus eval fixtures.

## Required Manifest Surfaces

- source_class_policy with one or more allowed source classes and `source_class_required: true`
- check_expectations requiring CHECK reports and AuthorityEnvelope refs
- eval_fixtures
- app_spatial_handoff_profile
- compatibility manifest/version metadata and breaking-change policy
- rollback_ref and deprecation_path

## Consuming Capability Rule

A pack with no consuming capability must not merge. At least one of these must
be present: {", ".join(CONSUMING_CAPABILITY_FIELDS)}.

## Non-Goals

{chr(10).join(f"- {item}" for item in NON_GOALS)}
""",
    )
    write_json(OUTPUT_ROOT / "domain_pack_manifest_schema_v1.json", schema)
    write_text(OUTPUT_ROOT / "domain_pack_validator.py", validator_source())
    write_text(
        OUTPUT_ROOT / "domain_ontology_governance_v1.md",
        f"""# Domain Ontology Governance v1

Governance applies to: {", ".join(GOVERNED_ADDITION_TYPES)}.

Every addition requires purpose, allowed source_class values, evidence
requirements, CHECK rules, required tests, eval fixtures, consumer surface,
compatibility version, and rollback/deprecation path.

No addition can bypass source_class policy, CHECK/Authority requirements,
retention/privacy contracts, or existing CER/SEG/source-class contracts.
""",
    )
    write_text(
        OUTPUT_ROOT / "entity_relationship_addition_policy_v1.md",
        """# Entity and Relationship Addition Policy v1

Entity or relationship additions must define purpose, minimum required fields,
optional fields, primary matching keys, core relationships, data quality tests,
example source mappings, evidence requirements, CHECK rules, eval fixtures,
consumer surface, compatibility version, owner, and rollback/deprecation path.

Unapproved local identity rules, VSS-as-fact-source, live-source claims, and
pack-private ontology forks are blocked.
""",
    )
    write_text(
        OUTPUT_ROOT / "domain_pack_compatibility_policy_v1.md",
        """# Domain Pack Compatibility Policy v1

Compatibility is semantic-versioned at the manifest and pack level. A breaking
change includes removing or renaming governed additions, changing source_class
requirements, weakening CHECK/Authority requirements, removing eval fixtures,
changing app/spatial handoff profiles, or removing a consuming capability.

Breaking changes require a migration note, rollback_ref, deprecation_path, and
gate review before merge.
""",
    )
    valid_fixture = {
        "pack_id": "framework_validation_fixture",
        "version": "1.0.0",
        "domain": "framework-validation-only",
        "source_class_policy": {
            "allowed_source_classes": ["replay_fixture", "derived_field"],
            "source_class_required": True,
            "vss_as_fact_source_allowed": False,
        },
        "consuming_capabilities": {"ask_templates": ["ask:fixture:001"]},
        "eval_fixtures": ["eval:fixture:001"],
        "check_expectations": {"requires_check_report": True, "requires_authority_envelope": True},
        "authority_profile": {"max_authority_level": 3, "no_execution_authority": True},
        "entity_relationship_refs": {"entity_types": [], "relationship_types": []},
        "app_spatial_handoff_profile": {"app_surface_refs": ["app:fixture"], "spatial_overlay_profile": "overlay:fixture"},
        "compatibility": {"manifest_version": "1.0.0", "compatibility_version": "1.0", "breaking_change_policy": "gate_review_required"},
        "limitations": ["validator fixture only; no starter pack"],
        "rollback_ref": "rollback:fixture:001",
        "deprecation_path": {"owner": "governance", "notice": "fixture", "replacement_or_removal_path": "remove fixture"},
        "governance_additions": {
            "entity_types": [
                {
                    "purpose": "validator fixture entity",
                    "source_class_allowed_values": ["replay_fixture"],
                    "evidence_requirements": ["evidence ref"],
                    "check_rules": ["CHECK required"],
                    "required_tests": ["validator test"],
                    "eval_fixtures": ["eval:fixture:001"],
                    "consumer_surface": "ASK",
                    "compatibility_version": "1.0",
                    "rollback_deprecation_path": "remove fixture",
                }
            ]
        },
    }
    invalid_no_consumer = {**valid_fixture, "pack_id": "invalid_no_consumer", "consuming_capabilities": {}}
    invalid_no_eval = {**valid_fixture, "pack_id": "invalid_no_eval", "eval_fixtures": []}
    validator_results = {
        "valid_fixture": validate_domain_pack_manifest(valid_fixture),
        "invalid_no_consumer": validate_domain_pack_manifest(invalid_no_consumer),
        "invalid_no_eval": validate_domain_pack_manifest(invalid_no_eval),
    }
    decision = {
        "schema_version": "citybrain.epoch_2_1.push_2_1a.lane_b.decision.v1",
        "status": PASS_STATUS,
        "created_at": utc_now(),
        "entry_check_status": "PASS_EPOCH_2_0_ENTRY_CHECK",
        "lane": "B",
        "push": "2.1a",
        "artifact_root": rel(OUTPUT_ROOT),
        "artifact_count": 0,
        "framework_only": True,
        "starter_packs_created": 0,
        "dubai_pack_created": 0,
        "live_source_created": False,
        "trained_model_created": False,
        "agent_activation_created": False,
        "validator_results": validator_results,
        "rules": {
            "pack_with_no_consuming_capability_must_not_merge": True,
            "eval_fixtures_required": True,
            "source_class_required": True,
            "check_authority_required": True,
            "app_spatial_handoff_profile_required": True,
            "compatibility_versioning_required": True,
            "rollback_deprecation_required": True,
        },
        "governance_coverage": GOVERNED_ADDITION_TYPES,
        "non_goals": NON_GOALS,
        "limitations": [
            "Framework only; no domain content is certified in this lane.",
            "Future starter packs in Push 2.1b must use this validator before merge.",
        ],
        "entry_check_ref": "outputs/epoch_2_1_push_2_1a_lane_b_domain_framework/EPOCH_2_0_ENTRY_CHECK_DECISION.json",
    }
    write_json(OUTPUT_ROOT / "PUSH_2_1A_LANE_B_DECISION.json", decision)
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        f"""# Push 2.1a Lane B Summary

Status: `{PASS_STATUS}`

Created the domain-pack framework, manifest schema, deterministic validator,
ontology governance, entity/relationship addition policy, and compatibility
policy. No starter packs, Dubai pack, live source, trained model, or agent
activation were created.
""",
    )
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
    return decision


def write_all_outputs() -> dict[str, Any]:
    reset_output_root()
    entry = check_epoch_2_0_entry()
    if entry["status"] != "PASS":
        write_entry_gap_report(entry)
        return {"entry": entry, "decision": None}
    write_entry_pass_outputs(entry)
    decision = write_lane_b_artifacts(entry)
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
    return {"entry": entry, "decision": decision}


def main() -> int:
    result = write_all_outputs()
    if result["entry"]["status"] != "PASS":
        print(BLOCK_STATUS)
        print(f"Output: {rel(OUTPUT_ROOT)}")
        return 1
    print(PASS_STATUS)
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
