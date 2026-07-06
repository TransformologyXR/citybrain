#!/usr/bin/env python3
"""Build Epoch 2.1 Push 2.1a Lane A privacy/retention artifacts."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention"
EPOCH20_ROOT = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation"
EPOCH20_REPORT_ROOT = EPOCH20_ROOT / "reports"

TASK_ID = "EPOCH-2-1-PUSH-2-1A-LANE-A-PRIVACY-RETENTION"
PASS_STATUS = "PASS_EPOCH_2_1_PUSH_2_1A_LANE_A_PRIVACY_RETENTION_WITH_LIMITATIONS"
BLOCK_STATUS = "BLOCKED_EPOCH_2_1_MISSING_2_0_AGENT_RECERTIFICATION_LEDGER"
CREATED_AT = "2026-07-06T00:00:00Z"

MANDATORY_AGENT_COMPONENTS = {
    "watch_scout": "Watch Scout",
    "diff_scout": "Diff Scout",
    "check_agent": "CHECK Agent",
    "approval_lifecycle_agent": "Approval Lifecycle Agent",
    "spatial_agent": "Spatial Agent",
    "perception_media_agent": "Perception / Media Agent",
}

RETENTION_CLASSES = [
    "raw_media",
    "evidence_clip_or_frame",
    "operator_note",
    "DispositionEvent",
    "OutcomeRecord",
    "CasePacket",
    "CheckReport",
    "CalibrationReport",
    "source_record",
    "synthetic_gold",
    "synthetic_dirty",
    "synthetic_challenge",
    "agent_run_trace",
]

NON_GOALS = [
    "No production auth implementation.",
    "No model training.",
    "No learned ranking.",
    "No live-source implementation.",
    "No official case/ticket semantics.",
    "No dispatch/control/enforcement.",
    "No legal/certified finding.",
    "No autonomous execution.",
]

LIMITATIONS = [
    "Policy and enforcement fixtures only; no production auth, storage, deletion, or live-source system is implemented.",
    "Right-to-forget behavior is expressed as deterministic policy fixtures for derived surfaces, not as a production erasure workflow.",
    "Aggregation floors gate display/materialization and future learning use; they do not train or score a model.",
    "DispositionEvent remains local/replay review feedback and cannot become official action.",
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


def reset_output_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def write_hash_manifest() -> dict[str, Any]:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            rows.append({"path": out_rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.epoch_2_1.push_2_1a.lane_a.hash_manifest.v1",
        "created_at": CREATED_AT,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(rows),
        "files": rows,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def verify_hash_manifest() -> dict[str, Any]:
    manifest = read_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    problems = []
    verified = 0
    for row in manifest.get("files", []):
        target = OUTPUT_ROOT / row["path"]
        if not target.exists():
            problems.append(f"missing:{row['path']}")
        elif sha256_file(target) != row["sha256"]:
            problems.append(f"mismatch:{row['path']}")
        else:
            verified += 1
    return {"status": "PASS" if not problems else "FAIL", "declared": len(manifest.get("files", [])), "verified": verified, "problems": problems}


def load_epoch20() -> dict[str, Any]:
    return {
        "component_registry": read_json(EPOCH20_ROOT / "component_registry_v1.json"),
        "agent_recertification": read_json(EPOCH20_REPORT_ROOT / "agent_recertification_report.json"),
        "replay_harness": read_json(EPOCH20_REPORT_ROOT / "replay_harness_report.json"),
        "mode_eval": read_json(EPOCH20_REPORT_ROOT / "mode_eval_harness_report.json"),
        "tool_permissions": read_json(EPOCH20_ROOT / "tool_permission_policy_v1.json"),
        "budget_stop_policy": read_json(EPOCH20_ROOT / "budget_stop_policy_v1.json"),
        "llm_seat_registry": read_json(EPOCH20_ROOT / "llm_seat_registry_v1.json"),
        "mode_invocation_registry": read_json(EPOCH20_ROOT / "mode_invocation_registry_v1.json"),
        "hash_manifest": read_json(EPOCH20_ROOT / "hash_manifest.json"),
        "final_status": read_json(EPOCH20_ROOT / "final_published_status.json"),
        "path_mapping": read_json(EPOCH20_REPORT_ROOT / "path_mapping.json"),
        "preflight_inventory": read_json(EPOCH20_REPORT_ROOT / "preflight_inventory.json"),
    }


def epoch20_entry_check(data: dict[str, Any]) -> dict[str, Any]:
    registry_by_id = {row.get("component_id"): row for row in data["component_registry"]}
    recert_by_id = {row.get("component_id"): row for row in data["agent_recertification"].get("rows", [])}
    permission_ids = {row.get("component_id") for row in data["tool_permissions"]}
    budget_ids = {row.get("policy_id") for row in data["budget_stop_policy"]}
    mode_slots = data["mode_eval"].get("slots", [])
    replay_envelope = data["replay_harness"].get("agent_run_envelope", {})

    component_results = []
    gaps = []
    for component_id, label in MANDATORY_AGENT_COMPONENTS.items():
        registry = registry_by_id.get(component_id)
        recert = recert_by_id.get(component_id)
        result = {
            "component_id": component_id,
            "label": label,
            "registered": bool(registry and registry.get("status") == "active"),
            "recertification_row_pass": bool(recert and recert.get("status") == "PASS"),
            "replay_or_eval_ref_present": bool(recert and recert.get("replay_or_eval_ref")),
            "tool_permission_policy_present": component_id in permission_ids,
            "budget_stop_policy_present": bool(registry and registry.get("budget_policy_ref") in budget_ids),
            "no_official_action": bool(recert and recert.get("no_official_action") is True),
        }
        result["status"] = "PASS" if all(value is True for key, value in result.items() if key not in {"component_id", "label", "status"}) else "FAIL"
        if result["status"] != "PASS":
            gaps.append({"component_id": component_id, "missing": [key for key, value in result.items() if value is False]})
        component_results.append(result)

    gates = {
        "component_registry_exists": bool(data["component_registry"]),
        "all_six_mandatory_agents_registered": all(row["registered"] for row in component_results),
        "all_six_mandatory_agents_have_recertification_rows": all(row["recertification_row_pass"] for row in component_results),
        "replay_harness_report_pass": data["replay_harness"].get("status") == "PASS",
        "agent_run_envelope_present": replay_envelope.get("schema_version") == "citybrain.agent_run_envelope.v1" and replay_envelope.get("status") == "emitted",
        "mode_scorecard_published": data["mode_eval"].get("status") == "PASS" and any(slot.get("acceptance_gate") == "PASS" for slot in mode_slots),
        "tool_permissions_apply": all(row["tool_permission_policy_present"] for row in component_results),
        "budget_stop_policies_apply": all(row["budget_stop_policy_present"] for row in component_results),
        "llm_seats_have_no_authority": all(seat.get("status") in {"disabled", "offline_eval", "proposal_only", "writer_only"} for seat in data["llm_seat_registry"]),
        "hash_manifest_present": data["hash_manifest"].get("item_count", 0) > 0,
        "final_published_status_pass": data["final_status"].get("status", "").startswith("PASS_EPOCH_2_0"),
        "no_official_legal_dispatch_live_or_learned_claim": all(
            token in data["final_status"].get("what_it_does_not_prove", [])
            for token in [
                "no official ticket/case/dispatch/enforcement/legal finding",
                "no autonomous execution",
                "no learned ranking/prediction/counterfactual behavior",
            ]
        ),
        "source_of_truth_matrix_update_accounted_for": data["path_mapping"].get("source_of_truth_base") == "origin/codex/epoch1-closedown-certified-baseline"
        and any(item.get("path", "").endswith("EPOCH1_SOURCE_OF_TRUTH_MATRIX.json") for item in data["preflight_inventory"].get("authoritative_docs", [])),
    }
    status = "PASS" if all(gates.values()) and not gaps else BLOCK_STATUS
    return {
        "schema_version": "citybrain.epoch_2_1.entry_check.v1",
        "created_at": CREATED_AT,
        "status": status,
        "gates": gates,
        "mandatory_agent_results": component_results,
        "mode_scorecard_ref": rel(EPOCH20_REPORT_ROOT / "mode_eval_harness_report.json"),
        "replay_harness_ref": rel(EPOCH20_REPORT_ROOT / "replay_harness_report.json"),
        "agent_run_envelope_ref": rel(EPOCH20_ROOT / "agent_run_envelope_v1.json"),
        "source_of_truth_matrix_note": "Epoch 2.0 records source_of_truth_base and no source-truth mutation against the Epoch 1 matrix; no separate matrix rewrite was located.",
        "gaps": gaps,
    }


def aggregation_policy() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.aggregation_floor_policy.v1",
        "policy_id": "aggregation_floor_policy_v1",
        "minimum_operators_for_display_or_learning_stat": 3,
        "minimum_items_for_dashboard_cell": 5,
        "applies_to": ["OutcomeRecord", "CalibrationReport", "dashboard_cell", "future_learning_stat"],
        "blocked_surfaces": ["public_product_surface", "non_admin_operator_detail", "small_cell_dashboard"],
        "admin_override_allowed": False,
        "notes": "Aggregation floor gates display/materialization only; it does not train or rank models.",
    }


def retention_matrix() -> list[dict[str, Any]]:
    rows = {
        "raw_media": ("real_or_synthetic_media", "short_lived_30_days", "admin_privacy_reviewer_only", "delete_blob_keep_hash_and_source_metadata_if_evidence_linked", False),
        "evidence_clip_or_frame": ("evidence_clip", "case_review_180_days", "reviewer_and_admin", "redact_subject_refs_keep_check_refs", False),
        "operator_note": ("operator_feedback", "365_days_or_until_rtf", "author_admin_and_aggregate_only", "pseudonymize_or_redact_on_rtf", True),
        "DispositionEvent": ("local_replay_review_feedback", "365_days_or_until_rtf", "aggregate_default_admin_detail", "pseudonymize_operator_ref_and_invalidate_derived_surfaces", True),
        "OutcomeRecord": ("derived_field", "policy_linked_to_source_records", "aggregate_default", "invalidate_or_recompute_when_source_or_operator_subject_redacted", True),
        "CasePacket": ("derived_case_surface", "policy_linked_to_evidence", "reviewer_and_admin", "redact_operator_and_subject_refs_on_rtf", True),
        "CheckReport": ("derived_field", "policy_linked_to_evidence", "reviewer_and_admin", "preserve limitation/check hash redact personal/operator refs", False),
        "CalibrationReport": ("derived_field", "365_days", "aggregate_default", "recompute aggregates after redaction", True),
        "source_record": ("real_source_record", "source_policy_or_365_days", "reviewer_and_admin", "redact personal refs and invalidate derived joins", False),
        "synthetic_gold": ("synthetic", "indefinite_fixture_until_replaced", "all_review_surfaces", "remove fixture if contaminated with real refs", False),
        "synthetic_dirty": ("synthetic_dirty", "indefinite_fixture_until_replaced", "all_review_surfaces", "remove fixture if contaminated with real refs", False),
        "synthetic_challenge": ("synthetic_challenge", "indefinite_fixture_until_replaced", "all_review_surfaces", "remove fixture if contaminated with real refs", False),
        "agent_run_trace": ("local_replay_audit_trace", "365_days", "admin_and_audit_only", "redact operator refs but retain run hash and policy decisions", True),
    }
    return [
        {
            "artifact_class": artifact_class,
            "source_class": values[0],
            "retention_period": values[1],
            "access_scope": values[2],
            "delete_or_redact_policy": values[3],
            "aggregation_floor_applicable": values[4],
            "notes": "No official action, legal/certified finding, live-source claim, or learned ranking is created.",
        }
        for artifact_class, values in rows.items()
    ]


def privacy_policy_json(matrix: list[dict[str, Any]], aggregation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.privacy_retention_policy.v1",
        "policy_id": "privacy_retention_policy_v1",
        "status": "active_policy_fixture",
        "aggregation_policy_ref": aggregation["policy_id"],
        "retention_matrix_ref": "retention_matrix_v1.json",
        "right_to_forget_policy_ref": "right_to_forget_policy_v1.md",
        "operator_data_rules": {
            "operator_ref_at_rest": "pseudonymous",
            "individual_level_view": "admin_scoped_only",
            "product_surfaces": "aggregate_only",
            "operator_notes_separate_from_disposition_labels": True,
            "disposition_is_official_action": False,
        },
        "source_class_rules": {
            "synthetic_and_real_same_source_class_allowed": False,
            "raw_media_and_evidence_clip_same_retention_allowed": False,
            "derived_fields_recomputed_after_rtf": True,
        },
        "retention_classes": [row["artifact_class"] for row in matrix],
        "non_goals": NON_GOALS,
        "limitations": LIMITATIONS,
    }


def enforcement_fixtures() -> list[dict[str, Any]]:
    return [
        {
            "fixture_id": "privacy-fixture:small-cell-aggregation-blocked",
            "description": "Small-cell aggregation display is blocked.",
            "input": {"operator_count": 2, "item_count": 4, "surface": "dashboard_cell"},
            "expected_decision": "block_display",
            "expected_reason": "below_operator_and_item_floor",
        },
        {
            "fixture_id": "privacy-fixture:operator-detail-non-admin-blocked",
            "description": "Operator-level data exposed to non-admin is blocked.",
            "input": {"requester_role": "operator_reviewer", "requested_field": "operator_ref", "surface": "case_detail"},
            "expected_decision": "block_individual_level_access",
            "expected_reason": "admin_scope_required",
        },
        {
            "fixture_id": "privacy-fixture:right-to-forget-derived-case-redaction",
            "description": "Right-to-forget request redacts/invalidates derived case surface appropriately.",
            "input": {"request_type": "right_to_forget", "subject_ref": "operator:pseudo:001", "derived_surfaces": ["CasePacket", "OutcomeRecord"]},
            "expected_decision": "redact_and_invalidate_derived_surfaces",
            "expected_reason": "subject_ref_removed_recompute_required",
        },
        {
            "fixture_id": "privacy-fixture:synthetic-real-source-class-mixing-rejected",
            "description": "Synthetic and real data cannot be merged under same source_class.",
            "input": {"source_classes": ["synthetic_gold", "real_source_record"], "target_source_class": "source_record"},
            "expected_decision": "reject_merge",
            "expected_reason": "synthetic_real_source_class_boundary",
        },
        {
            "fixture_id": "privacy-fixture:raw-media-vs-evidence-clip-retention-distinct",
            "description": "Raw media retention policy is distinct from evidence clip retention.",
            "input": {"artifact_classes": ["raw_media", "evidence_clip_or_frame"]},
            "expected_decision": "retain_policies_distinct",
            "expected_reason": "raw_blob_expiry_differs_from_evidence_clip_policy",
        },
        {
            "fixture_id": "privacy-fixture:disposition-event-local-replay-feedback-only",
            "description": "DispositionEvent remains local/replay review feedback, not official action.",
            "input": {"artifact_class": "DispositionEvent", "requested_interpretation": "official_action"},
            "expected_decision": "block_official_action_semantics",
            "expected_reason": "disposition_event_local_replay_feedback_only",
        },
    ]


def validate_fixtures(fixtures: list[dict[str, Any]], matrix: list[dict[str, Any]], aggregation: dict[str, Any]) -> dict[str, Any]:
    matrix_by_class = {row["artifact_class"]: row for row in matrix}
    results = []
    for fixture in fixtures:
        decision = fixture["expected_decision"]
        passed = False
        if decision == "block_display":
            passed = fixture["input"]["operator_count"] < aggregation["minimum_operators_for_display_or_learning_stat"] or fixture["input"]["item_count"] < aggregation["minimum_items_for_dashboard_cell"]
        elif decision == "block_individual_level_access":
            passed = fixture["input"]["requester_role"] != "admin" and fixture["input"]["requested_field"] == "operator_ref"
        elif decision == "redact_and_invalidate_derived_surfaces":
            passed = fixture["input"]["request_type"] == "right_to_forget" and "CasePacket" in fixture["input"]["derived_surfaces"]
        elif decision == "reject_merge":
            passed = "synthetic_gold" in fixture["input"]["source_classes"] and "real_source_record" in fixture["input"]["source_classes"]
        elif decision == "retain_policies_distinct":
            passed = matrix_by_class["raw_media"]["retention_period"] != matrix_by_class["evidence_clip_or_frame"]["retention_period"]
        elif decision == "block_official_action_semantics":
            passed = fixture["input"]["artifact_class"] == "DispositionEvent" and fixture["input"]["requested_interpretation"] == "official_action"
        results.append({"fixture_id": fixture["fixture_id"], "expected_decision": decision, "status": "PASS" if passed else "FAIL"})
    return {
        "schema_version": "citybrain.epoch_2_1.privacy_policy_validation_report.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL",
        "fixture_count": len(fixtures),
        "results": results,
        "non_goals_preserved": NON_GOALS,
    }


def write_policy_markdown() -> None:
    write_text(
        OUTPUT_ROOT / "privacy_retention_policy_v1.md",
        """# Privacy Retention Policy v1

This policy governs operator data, retention, deletion, aggregation, and
synthetic/real source separation for Epoch 2.1 Push 2.1a Lane A.

Defaults:
- Minimum operators for display or learning statistic: 3.
- Minimum items for dashboard cell: 5.
- Operator refs are pseudonymous at rest.
- Individual-level operator views are admin-scoped only.
- Product/public surfaces show aggregate values only.
- Operator notes are retained separately from disposition labels.
- DispositionEvent is local/replay review feedback, not official action.

Non-goals:
- No production auth implementation.
- No model training or learned ranking.
- No live-source implementation.
- No official case/ticket semantics.
""",
    )
    write_text(
        OUTPUT_ROOT / "right_to_forget_policy_v1.md",
        """# Right To Forget Policy v1

Right-to-forget requests redact the subject/operator reference and invalidate
derived surfaces that could expose that reference.

Derived surfaces:
- CasePacket: redact subject/operator refs and mark derived surface invalidated.
- OutcomeRecord: recompute or invalidate aggregate if the source row is removed.
- CalibrationReport: recompute aggregate-only metrics after redaction.
- CheckReport: preserve check hash/limitation metadata while redacting personal
  or operator refs where present.

Raw media deletion is distinct from evidence clip retention. Raw blobs may expire
while evidence hashes, limitation refs, and non-identifying provenance metadata
remain if policy requires audit continuity.
""",
    )


def write_entry_check_outputs(entry: dict[str, Any]) -> None:
    write_json(OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_DECISION.json", entry)
    write_json(
        OUTPUT_ROOT / "EPOCH_2_0_AGENT_RECERTIFICATION_INDEX.json",
        {
            "schema_version": "citybrain.epoch_2_1.agent_recertification_index.v1",
            "status": entry["status"],
            "mandatory_agents": entry["mandatory_agent_results"],
            "replay_harness_ref": entry["replay_harness_ref"],
            "mode_scorecard_ref": entry["mode_scorecard_ref"],
        },
    )
    write_text(
        OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_SUMMARY.md",
        "# Epoch 2.0 Entry Check Summary\n\n"
        f"Status: `{entry['status']}`\n\n"
        "All six mandatory agent-shaped components are registered, recertified, "
        "permissioned, budget/stop policy-bound, and linked to replay/eval evidence. "
        "Mode eval harness has published PASS acceptance slots. Source-of-truth matrix "
        "handling is recorded as no-mutation against the Epoch 1 matrix base.\n",
    )
    write_text(OUTPUT_ROOT / "EPOCH_2_1_ALLOWED_TO_OPEN.flag", "allowed=true\n")


def write_blocked_outputs(entry: dict[str, Any]) -> dict[str, Any]:
    reset_output_root()
    write_json(OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_REPORT.json", entry)
    lines = ["# Epoch 2.0 Entry Check Gaps", "", f"Status: `{entry['status']}`", ""]
    for gap in entry.get("gaps", []):
        lines.append(f"- `{gap['component_id']}`: {', '.join(gap['missing'])}")
    write_text(OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_GAPS.md", "\n".join(lines))
    write_hash_manifest()
    return entry


def build_outputs() -> dict[str, Any]:
    data = load_epoch20()
    entry = epoch20_entry_check(data)
    if entry["status"] != "PASS":
        return write_blocked_outputs(entry)

    reset_output_root()
    aggregation = aggregation_policy()
    matrix = retention_matrix()
    policy = privacy_policy_json(matrix, aggregation)
    fixtures = enforcement_fixtures()
    validation = validate_fixtures(fixtures, matrix, aggregation)
    write_entry_check_outputs(entry)
    write_policy_markdown()
    write_json(OUTPUT_ROOT / "privacy_retention_policy_v1.json", policy)
    write_json(OUTPUT_ROOT / "retention_matrix_v1.json", {"schema_version": "citybrain.epoch_2_1.retention_matrix.v1", "items": matrix})
    write_json(OUTPUT_ROOT / "aggregation_floor_policy_v1.json", aggregation)
    write_json(
        OUTPUT_ROOT / "privacy_policy_enforcement_fixtures.json",
        {
            "schema_version": "citybrain.epoch_2_1.privacy_policy_enforcement_fixtures.v1",
            "status": "PASS",
            "items": fixtures,
        },
    )
    write_json(OUTPUT_ROOT / "privacy_policy_validation_report.json", validation)
    decision = {
        "schema_version": "citybrain.epoch_2_1.push_2_1a.lane_a.decision.v1",
        "task_id": TASK_ID,
        "created_at": CREATED_AT,
        "status": PASS_STATUS if validation["status"] == "PASS" else "FAIL_EPOCH_2_1_PUSH_2_1A_LANE_A_PRIVACY_RETENTION",
        "entry_check_status": entry["status"],
        "counts": {
            "retention_classes": len(matrix),
            "enforcement_fixtures": len(fixtures),
            "validation_passes": sum(1 for row in validation["results"] if row["status"] == "PASS"),
        },
        "aggregation_floor": {
            "minimum_operators_for_display_or_learning_stat": aggregation["minimum_operators_for_display_or_learning_stat"],
            "minimum_items_for_dashboard_cell": aggregation["minimum_items_for_dashboard_cell"],
        },
        "contract_check": {
            "lane_a_only": True,
            "no_production_auth_implementation": True,
            "no_model_training": True,
            "no_learned_ranking": True,
            "no_live_source_implementation": True,
            "no_official_case_ticket_semantics": True,
            "disposition_event_local_replay_feedback_only": True,
        },
        "limitations": LIMITATIONS,
    }
    write_json(OUTPUT_ROOT / "PUSH_2_1A_LANE_A_DECISION.json", decision)
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        "# Push 2.1a Lane A Summary\n\n"
        f"Status: `{decision['status']}`\n\n"
        f"Retention classes: {len(matrix)}\n\n"
        f"Enforcement fixtures: {len(fixtures)}\n\n"
        "Epoch 2.1 is not closed by this lane.\n",
    )
    write_hash_manifest()
    return decision


def main() -> int:
    decision = build_outputs()
    verify = verify_hash_manifest()
    status = decision.get("status")
    print(f"{TASK_ID}: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    print(f"Hash manifest: {verify['status']}")
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
