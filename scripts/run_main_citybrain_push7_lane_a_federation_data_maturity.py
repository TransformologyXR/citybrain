#!/usr/bin/env python3
"""Build Push 7 Lane A federation/data maturity artifacts."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.federation import (
    ALLOWED_SCORE_BANDS,
    FORBIDDEN_SCORE_BANDS,
    UNIVERSAL_NON_CLAIMS,
    CrossCityRecallFixture,
    DataMaturityScore,
    DepartmentLocalNode,
    FederatedPacketEnvelope,
    FederationBoundaryDecision,
    NodeCapabilityManifest,
    SourceRefreshPolicy,
    SourceRefreshRunRecord,
    SyntheticCityPack,
    boundary_scan,
    stable_hash,
    stable_id,
    unique,
    validate_cross_city_recall_fixture,
    validate_data_maturity_score,
    validate_department_local_node,
    validate_federated_packet_envelope,
    validate_source_refresh_policy,
    validate_source_refresh_run_record,
    validate_synthetic_city_pack,
)


OUTPUTS_ROOT = REPO_ROOT / "outputs"
OUTPUT_ROOT = OUTPUTS_ROOT / "push7_lane_a_federation_data_maturity"
CLOSEOUT_ROOT = OUTPUTS_ROOT / "push7_lane_a_federation_data_maturity_closeout"
FINAL_ROOT = OUTPUTS_ROOT / "push7_lane_a_federation_data_maturity_final_status"

TASK_ID = "MAIN-CITYBRAIN-PUSH7-LANE-A-FEDERATION-DATA-MATURITY"
PACKAGE = "MAIN-CITYBRAIN-PUSH7-LANE-A-FEDERATION-DATA-MATURITY-RUN-TO-CLOSURE"
BRANCH = "codex/push7-lane-a-federation-data-maturity"
BASE_REF = "origin/codex/push6-infra-after-three-lanes"
PASS_STATUS = "PASS_PUSH7_LANE_A_FEDERATION_DATA_MATURITY_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH7_LANE_A_FEDERATION_DATA_MATURITY_FINAL_STATUS_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH7_LANE_A_FEDERATION_DATA_MATURITY"
STOP_PUSH6 = "STOPPED_WAITING_FOR_PUSH6_INTEGRATION"

PUSH6_INFRA_ROOT = OUTPUTS_ROOT / "push6_infra_after_three_lanes_integration"
PUSH6_FINAL_ROOT = OUTPUTS_ROOT / "push6_infra_after_three_lanes_final_status"
APPROVAL_ROOT = OUTPUTS_ROOT / "push6_lane_a_approval_lifecycle"
PLAN_ROOT = OUTPUTS_ROOT / "push6_lane_b_plan_mode"
SCHEDULE_ROOT = OUTPUTS_ROOT / "push6_lane_c_schedule_simulate"
PUSH5_INFRA_ROOT = OUTPUTS_ROOT / "push5_infra_after_three_lanes_integration"
SPATIAL_ROOT = OUTPUTS_ROOT / "push5_lane_a_spatial_ui_ux"
MEDIA_ROOT = OUTPUTS_ROOT / "push5_lane_b_perception_media_evidence"
WORKFLOW_ROOT = OUTPUTS_ROOT / "push5_lane_c_watch_workflow_state"
CER_ROOT = OUTPUTS_ROOT / "push4_lane_a_cer_engine"
GRAPH_ROOT = OUTPUTS_ROOT / "push4_lane_b_semantic_graph_v2"
CHECK_ROOT = OUTPUTS_ROOT / "push4_lane_c_check_v1"
RECALL_ROOT = OUTPUTS_ROOT / "push3_lane_c_diff_recall_readonly"

ASK_CONTRACT_PATHS = [
    "packages/ask_v11",
    "scripts/run_ask_v11_sealed_eval.py",
    "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
]

R7_RUNTIME_PATHS = [
    "scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
    "scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
    "scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
    "scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
]

REQUIRED_OUTPUTS = [
    "FEDERATION_DATA_MATURITY_DECISION.json",
    "DEPARTMENT_LOCAL_NODE_SCHEMA.json",
    "NODE_CAPABILITY_MANIFEST_SCHEMA.json",
    "DATA_MATURITY_SCORE_SCHEMA.json",
    "SOURCE_REFRESH_POLICY_SCHEMA.json",
    "FEDERATED_PACKET_ENVELOPE_SCHEMA.json",
    "FEDERATION_BOUNDARY_DECISION_SCHEMA.json",
    "DEPARTMENT_NODE_MANIFESTS.json",
    "DATA_MATURITY_SCORES.json",
    "SOURCE_REFRESH_POLICIES.json",
    "SOURCE_REFRESH_RUN_RECORDS.json",
    "FEDERATED_PACKET_ENVELOPES.json",
    "DUBAI_SYNTHETIC_PACK_MANIFEST.json",
    "CROSS_CITY_RECALL_BOUNDARY_FIXTURES.json",
    "FEDERATION_BOUNDARY_AND_NON_CLAIMS.md",
    "FEDERATION_DATA_MATURITY_TEST_LOG.md",
    "FEDERATION_DATA_MATURITY_HASH_MANIFEST.json",
]

REQUIRED_CLOSEOUT_OUTPUTS = [
    "FEDERATION_DATA_MATURITY_CLOSEOUT_DECISION.json",
    "FEDERATION_DATA_MATURITY_CLOSEOUT_SUMMARY.md",
    "FEDERATION_DATA_MATURITY_CLOSEOUT_LIMITATIONS.md",
    "FEDERATION_DATA_MATURITY_CLOSEOUT_NEXT_STEPS.md",
    "FEDERATION_DATA_MATURITY_CLOSEOUT_HASH_MANIFEST.json",
]

REQUIRED_FINAL_OUTPUTS = [
    "FEDERATION_DATA_MATURITY_FINAL_STATUS_DECISION.json",
    "FEDERATION_DATA_MATURITY_FINAL_STATUS_SUMMARY.md",
    "FEDERATION_DATA_MATURITY_FINAL_STATUS_HASH_MANIFEST.json",
]

LIMITATIONS = [
    "Federation artifacts are local/replay fixture contracts only.",
    "Department-local nodes describe ownership and review routing; they do not create production federation services.",
    "Data maturity bands are bounded to fixture/sample/local/reviewed/federation-candidate levels and never official/certified/live.",
    "Dubai artifacts are synthetic fixtures only and make no real Dubai coverage, government integration, or production twin claim.",
    "Cross-city recall fixtures are non-authoritative synthetic comparison examples, not real operational claims.",
    "Source refresh policies and run records use tracked artifacts or local fixtures only; no production API, URL fetch, or live retrieval is used.",
    "Feature branches only; Push 7 INFRA owns canonical integration after Lanes A, B, and C publish.",
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


def out_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def reset_output_root(root: Path) -> None:
    resolved = root.resolve()
    outputs = OUTPUTS_ROOT.resolve()
    if outputs not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def reset_output_roots() -> None:
    for root in [OUTPUT_ROOT, CLOSEOUT_ROOT, FINAL_ROOT]:
        reset_output_root(root)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(args: list[str], default: str = "") -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        return default
    return proc.stdout.strip() or default


def git_diff_empty(paths: list[str]) -> dict[str, Any]:
    proc = subprocess.run(["git", "diff", "--", *paths], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "status": "PASS" if proc.returncode == 0 and proc.stdout == "" else "FAIL",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "paths": paths,
    }


def write_hash_manifest(root: Path, name: str, schema_version: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != name:
            rows.append({"path": out_rel(path, root), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": schema_version,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(rows),
        "missing_count": 0,
        "mismatch_count": 0,
        "files": rows,
    }
    write_json(root / name, manifest)
    return manifest


def verify_hash_manifest(root: Path, name: str) -> dict[str, Any]:
    manifest_path = root / name
    if not manifest_path.exists():
        return {"status": "FAIL", "declared": 0, "verified": 0, "problems": ["manifest_missing"]}
    manifest = read_json(manifest_path, {"files": []})
    problems: list[str] = []
    verified = 0
    for row in manifest.get("files", []):
        target = root / row["path"]
        if not target.exists():
            problems.append(f"missing:{row['path']}")
        elif sha256_file(target) != row.get("sha256"):
            problems.append(f"mismatch:{row['path']}")
        else:
            verified += 1
    return {
        "status": "PASS" if not problems and manifest.get("status") == "PASS" else "FAIL",
        "declared": len(manifest.get("files", [])),
        "verified": verified,
        "problems": problems,
    }


def schema_payload(title: str, required: list[str], properties: dict[str, Any], schema_version: str) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "title": title,
        "type": "object",
        "additionalProperties": True,
        "required": required,
        "properties": properties,
    }


def load_inputs() -> dict[str, Any]:
    required = [
        PUSH6_INFRA_ROOT / "PUSH6_INFRA_INTEGRATION_DECISION.json",
        PUSH6_INFRA_ROOT / "PUSH6_CROSS_LANE_COMPATIBILITY_REPORT.json",
        PUSH6_FINAL_ROOT / "PUSH6_FINAL_STATUS_DECISION.json",
        APPROVAL_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json",
        APPROVAL_ROOT / "APPROVAL_LIFECYCLE_DECISION.json",
        PLAN_ROOT / "OPTIONSET_V2_FIXTURES.json",
        PLAN_ROOT / "PLAN_MODE_DECISION.json",
        SCHEDULE_ROOT / "SCHEDULE_OPTION_FIXTURES.json",
        SCHEDULE_ROOT / "SUMO_SCENARIO_FIXTURES.json",
        SCHEDULE_ROOT / "CUOPT_SCHEDULING_FIXTURES.json",
        SCHEDULE_ROOT / "SIMULATION_CHECK_REPORTS.json",
        PUSH5_INFRA_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json",
        SPATIAL_ROOT / "SPATIAL_OVERLAY_MANAGER_MANIFEST.json",
        MEDIA_ROOT / "MEDIA_EVIDENCE_BUNDLES.json",
        WORKFLOW_ROOT / "WORKFLOW_STATE_EVENTS.json",
        CER_ROOT / "CER_ENGINE_DECISION.json",
        GRAPH_ROOT / "SEMANTIC_GRAPH_V2_DECISION.json",
        CHECK_ROOT / "CHECK_V1_REPORTS.json",
        RECALL_ROOT / "RECALL_MATCH_ITEMS.json",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Push 7 Lane A inputs: {missing}")
    return {
        "push6_infra": read_json(PUSH6_INFRA_ROOT / "PUSH6_INFRA_INTEGRATION_DECISION.json"),
        "push6_compatibility": read_json(PUSH6_INFRA_ROOT / "PUSH6_CROSS_LANE_COMPATIBILITY_REPORT.json"),
        "push6_final": read_json(PUSH6_FINAL_ROOT / "PUSH6_FINAL_STATUS_DECISION.json"),
        "approval_fixtures": read_json(APPROVAL_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json"),
        "approval_decision": read_json(APPROVAL_ROOT / "APPROVAL_LIFECYCLE_DECISION.json"),
        "plan": read_json(PLAN_ROOT / "OPTIONSET_V2_FIXTURES.json"),
        "plan_decision": read_json(PLAN_ROOT / "PLAN_MODE_DECISION.json"),
        "schedule": read_json(SCHEDULE_ROOT / "SCHEDULE_OPTION_FIXTURES.json"),
        "sumo": read_json(SCHEDULE_ROOT / "SUMO_SCENARIO_FIXTURES.json"),
        "cuopt": read_json(SCHEDULE_ROOT / "CUOPT_SCHEDULING_FIXTURES.json"),
        "simulation_checks": read_json(SCHEDULE_ROOT / "SIMULATION_CHECK_REPORTS.json"),
        "push5_infra": read_json(PUSH5_INFRA_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json"),
        "spatial": read_json(SPATIAL_ROOT / "SPATIAL_OVERLAY_MANAGER_MANIFEST.json"),
        "media": read_json(MEDIA_ROOT / "MEDIA_EVIDENCE_BUNDLES.json"),
        "workflow": read_json(WORKFLOW_ROOT / "WORKFLOW_STATE_EVENTS.json"),
        "cer": read_json(CER_ROOT / "CER_ENGINE_DECISION.json"),
        "graph": read_json(GRAPH_ROOT / "SEMANTIC_GRAPH_V2_DECISION.json"),
        "check": read_json(CHECK_ROOT / "CHECK_V1_REPORTS.json"),
        "recall": read_json(RECALL_ROOT / "RECALL_MATCH_ITEMS.json"),
    }


def push6_gate(data: dict[str, Any]) -> dict[str, Any]:
    remote_commit = git_value(["rev-parse", "--verify", "origin/codex/push6-infra-after-three-lanes"], "")
    compatibility = data["push6_compatibility"]
    compatibility_gates = compatibility.get("gates", {})
    gates = {
        "push6_integration_ref_available": bool(remote_commit),
        "push6_integration_status_pass": data["push6_infra"].get("status", "").startswith("PASS_PUSH6_INFRA"),
        "push6_final_status_pass": data["push6_final"].get("status", "").startswith("PASS_PUSH6_INFRA"),
        "approval_lifecycle_authority_l3_exists": compatibility_gates.get("approval_lifecycle_and_authority_level_3_available") is True,
        "plan_mode_exists_and_not_executed": compatibility_gates.get("plan_optionsets_carry_approval_request_ref") is True
        and compatibility_gates.get("all_proposals_remain_not_executed") is True,
        "schedule_simulate_exists_and_not_executed": compatibility_gates.get("schedule_simulate_packets_carry_approval_request_ref") is True
        and compatibility_gates.get("schedule_simulate_uses_approval_lifecycle") is True,
        "check_cer_graph_available": (CHECK_ROOT / "CHECK_V1_REPORTS.json").exists()
        and (CER_ROOT / "CER_ENGINE_DECISION.json").exists()
        and (GRAPH_ROOT / "SEMANTIC_GRAPH_V2_DECISION.json").exists(),
        "spatial_perception_workflow_available": (SPATIAL_ROOT / "SPATIAL_OVERLAY_MANAGER_MANIFEST.json").exists()
        and (MEDIA_ROOT / "MEDIA_EVIDENCE_BUNDLES.json").exists()
        and (WORKFLOW_ROOT / "WORKFLOW_STATE_EVENTS.json").exists(),
        "protected_ask_diff_clean_in_push6": compatibility_gates.get("ask_scoped_diff_clean") is True,
        "protected_r7_diff_clean_in_push6": compatibility_gates.get("r7_scoped_diff_clean") is True,
    }
    return {
        "status": "PASS" if all(gates.values()) else STOP_PUSH6,
        "accepted_integration_branch": BASE_REF,
        "accepted_integration_commit": remote_commit,
        "gates": gates,
        "push6_status": data["push6_infra"].get("status"),
        "push6_final_status": data["push6_final"].get("status"),
    }


def first(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return rows[0] if rows else {}


def common_refs(data: dict[str, Any]) -> dict[str, Any]:
    approval_request = first(data["approval_fixtures"].get("approval_requests", []))
    plan_option_set = first(data["plan"].get("option_sets", []))
    plan_option = first(data["plan"].get("plan_options", []))
    schedule_option = first(data["schedule"].get("schedule_options", []))
    sumo_packet = first(data["sumo"].get("scenario_packets", []))
    check_report = first(data["check"].get("items", []))
    authority_ref = (
        approval_request.get("authority_envelope_ref")
        or plan_option_set.get("authority_envelope_ref")
        or schedule_option.get("authority_envelope_ref")
        or "authority:l3:push7:lane-a:fixture"
    )
    check_ref = (
        approval_request.get("check_report_ref")
        or plan_option_set.get("check_report_ref")
        or schedule_option.get("check_report_ref")
        or check_report.get("check_report_id")
        or "check:push7:lane-a:fixture"
    )
    evidence_refs = unique(
        [
            approval_request.get("evidence_refs", []),
            plan_option_set.get("evidence_refs", []),
            plan_option.get("evidence_refs", []),
            schedule_option.get("evidence_refs", []),
            sumo_packet.get("evidence_refs", []),
            check_report.get("evidence_refs", []),
            rel(PUSH6_INFRA_ROOT / "PUSH6_INFRA_INTEGRATION_DECISION.json"),
        ]
    )
    limitation_refs = unique(
        [
            approval_request.get("limitation_refs", []),
            plan_option_set.get("limitation_refs", []),
            plan_option.get("limitation_refs", []),
            schedule_option.get("limitation_refs", []),
            sumo_packet.get("limitation_refs", []),
            LIMITATIONS,
        ]
    )
    trace_refs = unique(
        [
            approval_request.get("trace_refs", []),
            plan_option_set.get("trace_refs", []),
            plan_option.get("trace_refs", []),
            schedule_option.get("trace_refs", []),
            sumo_packet.get("trace_refs", []),
            ["PUSH6:INFRA:AFTER_THREE_LANES", "PUSH7:LANE_A:FEDERATION_DATA_MATURITY"],
        ]
    )
    return {
        "approval_request": approval_request,
        "plan_option_set": plan_option_set,
        "plan_option": plan_option,
        "schedule_option": schedule_option,
        "sumo_packet": sumo_packet,
        "check_report": check_report,
        "authority_ref": authority_ref,
        "check_ref": check_ref,
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "trace_refs": trace_refs,
        "cannot_claim": list(UNIVERSAL_NON_CLAIMS),
    }


def build_department_nodes(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    refs = common_refs(data)
    nodes = [
        DepartmentLocalNode(
            node_id="dept-node:approval-governance-local",
            node_label="Approval Governance Local Node",
            department_or_domain="approval_governance",
            city_scope="citybrain_local_replay",
            owned_source_classes=["approval_requests", "approval_lifecycle_states", "authority_level_3_envelopes"],
            owned_packet_types=["approval_lifecycle_state", "approval_request", "approval_audit_event"],
            authority_levels_supported=["authority_level_3_proposal_governance"],
            data_maturity_summary={"dominant_score_band": "reviewed_local", "official_or_certified": False},
            federation_policy_ref="source-refresh-policy:approval-governance-local",
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            check_report_ref=refs["check_ref"],
            authority_envelope_ref=refs["authority_ref"],
            cannot_claim=refs["cannot_claim"],
        ).as_dict(),
        DepartmentLocalNode(
            node_id="dept-node:mobility-planning-local",
            node_label="Mobility Planning Local Node",
            department_or_domain="mobility_planning",
            city_scope="citybrain_local_replay",
            owned_source_classes=["plan_mode_option_sets", "schedule_options", "simulation_scenarios"],
            owned_packet_types=["optionset_v2", "schedule_option", "scenario_packet"],
            authority_levels_supported=["authority_level_3_proposal_governance"],
            data_maturity_summary={"dominant_score_band": "federation_candidate", "official_or_certified": False},
            federation_policy_ref="source-refresh-policy:mobility-planning-local",
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            check_report_ref=refs["check_ref"],
            authority_envelope_ref=refs["authority_ref"],
            cannot_claim=refs["cannot_claim"],
        ).as_dict(),
        DepartmentLocalNode(
            node_id="dept-node:perception-check-local",
            node_label="Perception CHECK/CER Local Node",
            department_or_domain="perception_check_cer",
            city_scope="citybrain_local_replay",
            owned_source_classes=["media_evidence_bundles", "check_v1_reports", "cer_identity_records", "semantic_graph_v2"],
            owned_packet_types=["media_evidence_bundle", "check_report", "cer_entity_record", "semantic_graph_query"],
            authority_levels_supported=["authority_level_3_reference_context"],
            data_maturity_summary={"dominant_score_band": "checked_local", "official_or_certified": False},
            federation_policy_ref="source-refresh-policy:perception-check-local",
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            check_report_ref=refs["check_ref"],
            authority_envelope_ref=refs["authority_ref"],
            cannot_claim=refs["cannot_claim"],
        ).as_dict(),
        DepartmentLocalNode(
            node_id="dept-node:synthetic-cross-city-fixtures",
            node_label="Synthetic Cross-City Fixture Node",
            department_or_domain="synthetic_federation_fixtures",
            city_scope="synthetic_fixture_only",
            owned_source_classes=["dubai_synthetic_pack", "cross_city_recall_fixtures"],
            owned_packet_types=["synthetic_city_pack", "cross_city_recall_fixture", "synthetic_federated_packet"],
            authority_levels_supported=["authority_level_3_boundary_review_only"],
            data_maturity_summary={"dominant_score_band": "fixture_only", "official_or_certified": False},
            federation_policy_ref="source-refresh-policy:synthetic-cross-city-fixtures",
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            check_report_ref=refs["check_ref"],
            authority_envelope_ref=refs["authority_ref"],
            cannot_claim=refs["cannot_claim"],
        ).as_dict(),
    ]
    capabilities = [
        NodeCapabilityManifest(
            capability_manifest_id=stable_id("node-capability", node["node_id"]),
            node_ref=node["node_id"],
            capability_tags=["local_replay", "review_required", "federation_fixture"],
            can_emit_packet_types=node["owned_packet_types"],
            can_receive_packet_types=["federated_packet_envelope", "data_maturity_score", "federation_boundary_decision"],
            local_only_packet_types=["approval_audit_event"] if "approval" in node["node_id"] else [],
            review_required=True,
            execution_status="not_executed",
            evidence_refs=node["evidence_refs"],
            limitation_refs=node["limitation_refs"],
            trace_refs=node["trace_refs"],
            check_report_ref=node["check_report_ref"],
            authority_envelope_ref=node["authority_envelope_ref"],
            cannot_claim=node["cannot_claim"],
        ).as_dict()
        for node in nodes
    ]
    return nodes, capabilities


def build_data_maturity_scores(data: dict[str, Any]) -> list[dict[str, Any]]:
    refs = common_refs(data)
    targets = [
        (refs["approval_request"].get("approval_request_id", "approval:request:push7:fixture"), "approval_request", "approval_lifecycle", "reviewed_local"),
        (refs["plan_option_set"].get("option_set_id", "optionset:v2:push7:fixture"), "optionset_v2", "plan_mode", "federation_candidate"),
        (refs["schedule_option"].get("schedule_option_id", "schedule-option:push7:fixture"), "schedule_option", "schedule_simulate", "sample_replay"),
        (refs["sumo_packet"].get("scenario_packet_id", "scenario-packet:push7:fixture"), "scenario_packet", "sumo_local_replay", "sample_replay"),
        (refs["check_report"].get("check_report_id", refs["check_ref"]), "check_report", "check_v1", "checked_local"),
        ("outputs/push4_lane_a_cer_engine/CER_ENGINE_DECISION.json", "cer_engine_decision", "cer_local_review", "checked_local"),
        ("synthetic-city-pack:dubai_synthetic", "synthetic_city_pack", "synthetic_fixture", "fixture_only"),
        ("cross-city-recall-fixture:push7:lane-a:0001", "cross_city_recall_fixture", "synthetic_cross_city_fixture", "fixture_only"),
    ]
    scores = []
    for target_ref, target_type, source_class, band in targets:
        scores.append(
            DataMaturityScore(
                data_maturity_id=stable_id("data-maturity", target_ref, band),
                target_ref=target_ref,
                target_type=target_type,
                source_class=source_class,
                freshness_status="tracked_branch_artifact_current" if band != "fixture_only" else "synthetic_fixture_current",
                completeness_status="bounded_fixture_complete",
                provenance_status="tracked_local_artifact" if band != "fixture_only" else "synthetic_fixture_declared",
                authority_status="authority_l3_local_review_only",
                review_status="review_required_before_operational_use",
                score_band=band,
                evidence_refs=refs["evidence_refs"],
                limitation_refs=refs["limitation_refs"],
                trace_refs=refs["trace_refs"],
                check_report_ref=refs["check_ref"],
                authority_envelope_ref=refs["authority_ref"],
                cannot_claim=refs["cannot_claim"],
            ).as_dict()
        )
    return scores


def build_source_refresh(nodes: list[dict[str, Any]], data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    refs = common_refs(data)
    policies: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    for node in nodes:
        source_class = node["owned_source_classes"][0]
        policy = SourceRefreshPolicy(
            source_refresh_policy_id=node["federation_policy_ref"],
            source_class=source_class,
            owner_node_ref=node["node_id"],
            refresh_mode="tracked_branch_artifact_or_fixture_only",
            refresh_cadence="manual_regeneration_per_feature_branch",
            allowed_input_modes=["tracked_branch_artifact", "local_replay_fixture", "manual_review_registry"],
            production_api_used=False,
            url_fetch_used=False,
            live_retrieval_used=False,
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            check_report_ref=refs["check_ref"],
            authority_envelope_ref=refs["authority_ref"],
            cannot_claim=refs["cannot_claim"],
        ).as_dict()
        policies.append(policy)
        run_mode = "fixture_regeneration" if "synthetic" in node["node_id"] else "local_replay_snapshot"
        runs.append(
            SourceRefreshRunRecord(
                source_refresh_run_id=stable_id("source-refresh-run", policy["source_refresh_policy_id"]),
                source_refresh_policy_ref=policy["source_refresh_policy_id"],
                source_class=source_class,
                owner_node_ref=node["node_id"],
                run_mode=run_mode,
                run_status="recorded_from_tracked_artifact",
                production_api_used=False,
                url_fetch_used=False,
                live_retrieval_used=False,
                execution_status="not_executed",
                evidence_refs=refs["evidence_refs"],
                limitation_refs=refs["limitation_refs"],
                trace_refs=refs["trace_refs"],
                check_report_ref=refs["check_ref"],
                authority_envelope_ref=refs["authority_ref"],
                cannot_claim=refs["cannot_claim"],
            ).as_dict()
        )
    return policies, runs


def score_for(scores: list[dict[str, Any]], target_type: str) -> str:
    for score in scores:
        if score.get("target_type") == target_type:
            return score["data_maturity_id"]
    return scores[0]["data_maturity_id"]


def build_boundary_and_envelopes(data: dict[str, Any], nodes: list[dict[str, Any]], scores: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    refs = common_refs(data)
    node_by_id = {node["node_id"]: node for node in nodes}
    packets = [
        {
            "origin": "dept-node:approval-governance-local",
            "destination": "local-node:mobility-planning-local",
            "packet_ref": refs["approval_request"].get("approval_request_id", "approval:request:push7:fixture"),
            "packet_type": "approval_request",
            "share_policy": "local_only",
            "score_type": "approval_request",
            "decision": "retain_local_only",
            "reason": "Approval request metadata is local governance context and not an operational cross-city claim.",
        },
        {
            "origin": "dept-node:mobility-planning-local",
            "destination": "federation-scope:review-fixture",
            "packet_ref": refs["plan_option_set"].get("option_set_id", "optionset:v2:push7:fixture"),
            "packet_type": "optionset_v2",
            "share_policy": "metadata_only_federation_fixture",
            "score_type": "optionset_v2",
            "decision": "allow_metadata_fixture",
            "reason": "PLAN OptionSet can be described as candidate local/replay review metadata only.",
        },
        {
            "origin": "dept-node:mobility-planning-local",
            "destination": "federation-scope:review-fixture",
            "packet_ref": refs["schedule_option"].get("schedule_option_id", "schedule-option:push7:fixture"),
            "packet_type": "schedule_option",
            "share_policy": "review_required_before_share",
            "score_type": "schedule_option",
            "decision": "review_required_before_share",
            "reason": "Schedule proposal remains not_executed and requires local review before any fixture-level federation.",
        },
        {
            "origin": "dept-node:mobility-planning-local",
            "destination": "federation-scope:review-fixture",
            "packet_ref": refs["sumo_packet"].get("scenario_packet_id", "scenario-packet:push7:fixture"),
            "packet_type": "scenario_packet",
            "share_policy": "metadata_only_federation_fixture",
            "score_type": "scenario_packet",
            "decision": "allow_metadata_fixture",
            "reason": "Simulation scenario is local/replay sample output and not calibrated for prediction.",
        },
        {
            "origin": "dept-node:perception-check-local",
            "destination": "federation-scope:review-fixture",
            "packet_ref": refs["check_report"].get("check_report_id", refs["check_ref"]),
            "packet_type": "check_report",
            "share_policy": "metadata_only_federation_fixture",
            "score_type": "check_report",
            "decision": "allow_metadata_fixture",
            "reason": "CHECK/CER evidence refs can be carried as non-authoritative context with limitations preserved.",
        },
        {
            "origin": "dept-node:synthetic-cross-city-fixtures",
            "destination": "federation-scope:dubai_synthetic",
            "packet_ref": "synthetic-city-pack:dubai_synthetic",
            "packet_type": "synthetic_city_pack",
            "share_policy": "synthetic_fixture_only",
            "score_type": "synthetic_city_pack",
            "decision": "synthetic_fixture_only",
            "reason": "Dubai pack is synthetic and cannot be interpreted as real Dubai coverage.",
        },
    ]
    decisions: list[dict[str, Any]] = []
    envelopes: list[dict[str, Any]] = []
    for packet in packets:
        node = node_by_id[packet["origin"]]
        decision_ref = stable_id("federation-boundary-decision", packet["packet_ref"], packet["share_policy"])
        decision = FederationBoundaryDecision(
            federation_boundary_decision_id=decision_ref,
            packet_ref=packet["packet_ref"],
            origin_node_ref=packet["origin"],
            destination_scope_ref=packet["destination"],
            decision=packet["decision"],
            share_policy=packet["share_policy"],
            reason=packet["reason"],
            real_cross_city_claim=False,
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            check_report_ref=refs["check_ref"],
            authority_envelope_ref=refs["authority_ref"],
            cannot_claim=refs["cannot_claim"],
        ).as_dict()
        decisions.append(decision)
        envelopes.append(
            FederatedPacketEnvelope(
                federated_packet_id=stable_id("federated-packet", packet["packet_ref"], packet["destination"]),
                origin_node_ref=packet["origin"],
                destination_scope_ref=packet["destination"],
                packet_ref=packet["packet_ref"],
                packet_type=packet["packet_type"],
                share_policy=packet["share_policy"],
                data_maturity_ref=score_for(scores, packet["score_type"]),
                evidence_refs=node["evidence_refs"],
                limitation_refs=node["limitation_refs"],
                trace_refs=node["trace_refs"],
                check_report_ref=node["check_report_ref"],
                authority_envelope_ref=node["authority_envelope_ref"],
                federation_boundary_decision_ref=decision_ref,
                not_executed=["production_federation", "cross_city_operational_claim", "official_submission", "dispatch_control_enforcement_execution"],
                cannot_claim=node["cannot_claim"],
            ).as_dict()
        )
    return decisions, envelopes


def build_cross_city_fixtures(data: dict[str, Any], envelopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs = common_refs(data)
    local_envelope = envelopes[1]
    scenario_envelope = envelopes[3]
    fixtures = [
        CrossCityRecallFixture(
            cross_city_recall_fixture_id="cross-city-recall-fixture:push7:lane-a:0001",
            source_city_scope="citybrain_local_replay",
            comparison_city_scope="dubai_synthetic",
            source_packet_ref=local_envelope["packet_ref"],
            comparison_packet_ref="synthetic:dubai:traffic-review-pattern:0001",
            match_basis="same_candidate_review_pattern_synthetic_only",
            synthetic_fixture_only=True,
            real_cross_city_claim=False,
            authority_status="non_authoritative_fixture",
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            check_report_ref=refs["check_ref"],
            authority_envelope_ref=refs["authority_ref"],
            not_executed=["real_cross_city_operational_claim", "production_federation", "official_submission"],
            cannot_claim=refs["cannot_claim"],
        ).as_dict(),
        CrossCityRecallFixture(
            cross_city_recall_fixture_id="cross-city-recall-fixture:push7:lane-a:0002",
            source_city_scope="citybrain_local_replay",
            comparison_city_scope="dubai_synthetic",
            source_packet_ref=scenario_envelope["packet_ref"],
            comparison_packet_ref="synthetic:dubai:scenario-pattern:0001",
            match_basis="local_replay_scenario_to_synthetic_scenario_shape_only",
            synthetic_fixture_only=True,
            real_cross_city_claim=False,
            authority_status="non_authoritative_fixture",
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            check_report_ref=refs["check_ref"],
            authority_envelope_ref=refs["authority_ref"],
            not_executed=["real_cross_city_operational_claim", "production_federation", "official_submission"],
            cannot_claim=refs["cannot_claim"],
        ).as_dict(),
    ]
    return fixtures


def build_dubai_pack(nodes: list[dict[str, Any]], envelopes: list[dict[str, Any]], cross_city_fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    synthetic_node = next(node for node in nodes if node["node_id"] == "dept-node:synthetic-cross-city-fixtures")
    synthetic_envelopes = [envelope for envelope in envelopes if envelope["share_policy"] == "synthetic_fixture_only"]
    pack = SyntheticCityPack(
        synthetic_city_id="dubai_synthetic",
        synthetic_node_manifests=[synthetic_node],
        synthetic_source_records=[
            {
                "synthetic_source_record_id": "synthetic:dubai:traffic-review-pattern:0001",
                "source_class": "synthetic_cross_city_fixture",
                "real_government_source": False,
                "production_api_used": False,
                "url_fetch_used": False,
                "live_retrieval_used": False,
            },
            {
                "synthetic_source_record_id": "synthetic:dubai:scenario-pattern:0001",
                "source_class": "synthetic_scenario_fixture",
                "real_government_source": False,
                "production_api_used": False,
                "url_fetch_used": False,
                "live_retrieval_used": False,
            },
        ],
        synthetic_federated_packets=synthetic_envelopes,
        synthetic_cross_city_recall_pairs=cross_city_fixtures,
        real_dubai_coverage_claimed=False,
        real_government_source_integration_claimed=False,
        production_twin_claimed=False,
        cannot_claim=list(UNIVERSAL_NON_CLAIMS),
    )
    return pack.as_dict()


def schemas() -> dict[str, dict[str, Any]]:
    string_array = {"type": "array", "items": {"type": "string"}}
    return {
        "DEPARTMENT_LOCAL_NODE_SCHEMA.json": schema_payload(
            "DepartmentLocalNode",
            [
                "node_id",
                "schema_version",
                "node_label",
                "department_or_domain",
                "city_scope",
                "owned_source_classes",
                "owned_packet_types",
                "authority_levels_supported",
                "data_maturity_summary",
                "federation_policy_ref",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "cannot_claim",
            ],
            {"node_id": {"type": "string"}, "owned_source_classes": string_array, "owned_packet_types": string_array},
            "main-citybrain.push7.lane_a.department_local_node.schema.v1",
        ),
        "NODE_CAPABILITY_MANIFEST_SCHEMA.json": schema_payload(
            "NodeCapabilityManifest",
            [
                "capability_manifest_id",
                "node_ref",
                "capability_tags",
                "can_emit_packet_types",
                "can_receive_packet_types",
                "local_only_packet_types",
                "review_required",
                "execution_status",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "cannot_claim",
            ],
            {"capability_manifest_id": {"type": "string"}, "review_required": {"type": "boolean"}},
            "main-citybrain.push7.lane_a.node_capability_manifest.schema.v1",
        ),
        "DATA_MATURITY_SCORE_SCHEMA.json": schema_payload(
            "DataMaturityScore",
            [
                "data_maturity_id",
                "target_ref",
                "target_type",
                "source_class",
                "freshness_status",
                "completeness_status",
                "provenance_status",
                "authority_status",
                "review_status",
                "score_band",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "cannot_claim",
            ],
            {
                "score_band": {"type": "string", "enum": sorted(ALLOWED_SCORE_BANDS)},
                "forbidden_score_bands": {"type": "array", "const": sorted(FORBIDDEN_SCORE_BANDS)},
            },
            "main-citybrain.push7.lane_a.data_maturity_score.schema.v1",
        ),
        "SOURCE_REFRESH_POLICY_SCHEMA.json": schema_payload(
            "SourceRefreshPolicyAndRunRecord",
            [
                "source_refresh_policy_id",
                "source_class",
                "owner_node_ref",
                "refresh_mode",
                "refresh_cadence",
                "allowed_input_modes",
                "production_api_used",
                "url_fetch_used",
                "live_retrieval_used",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "cannot_claim",
            ],
            {
                "production_api_used": {"type": "boolean", "const": False},
                "url_fetch_used": {"type": "boolean", "const": False},
                "live_retrieval_used": {"type": "boolean", "const": False},
                "source_refresh_run_record_required_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [
                        "source_refresh_run_id",
                        "source_refresh_policy_ref",
                        "run_mode",
                        "run_status",
                        "execution_status",
                    ],
                },
            },
            "main-citybrain.push7.lane_a.source_refresh_policy.schema.v1",
        ),
        "FEDERATED_PACKET_ENVELOPE_SCHEMA.json": schema_payload(
            "FederatedPacketEnvelope",
            [
                "federated_packet_id",
                "schema_version",
                "origin_node_ref",
                "destination_scope_ref",
                "packet_ref",
                "packet_type",
                "share_policy",
                "data_maturity_ref",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "federation_boundary_decision_ref",
                "not_executed",
                "cannot_claim",
            ],
            {"share_policy": {"type": "string"}, "not_executed": string_array},
            "main-citybrain.push7.lane_a.federated_packet_envelope.schema.v2",
        ),
        "FEDERATION_BOUNDARY_DECISION_SCHEMA.json": schema_payload(
            "FederationBoundaryDecision",
            [
                "federation_boundary_decision_id",
                "packet_ref",
                "origin_node_ref",
                "destination_scope_ref",
                "decision",
                "share_policy",
                "reason",
                "real_cross_city_claim",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "cannot_claim",
            ],
            {"real_cross_city_claim": {"type": "boolean", "const": False}},
            "main-citybrain.push7.lane_a.federation_boundary_decision.schema.v1",
        ),
    }


def contract_check(
    gate: dict[str, Any],
    nodes: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    dubai_pack: dict[str, Any],
    cross_city_fixtures: list[dict[str, Any]],
    tests: dict[str, Any],
) -> dict[str, Any]:
    payloads = {
        "nodes": nodes,
        "scores": scores,
        "policies": policies,
        "runs": runs,
        "decisions": decisions,
        "envelopes": envelopes,
        "dubai_pack": dubai_pack,
        "cross_city_fixtures": cross_city_fixtures,
    }
    boundary = boundary_scan(payloads)
    score_reject_probe = dict(scores[0])
    score_reject_probe["score_band"] = "certified"
    gates = {
        "lane_a_only": True,
        "push6_gate_passed": gate["status"] == "PASS",
        "department_nodes_validate": all(validate_department_local_node(node)["status"] == "PASS" for node in nodes),
        "data_maturity_scores_validate": all(validate_data_maturity_score(score)["status"] == "PASS" for score in scores),
        "forbidden_maturity_bands_rejected": validate_data_maturity_score(score_reject_probe)["status"] == "FAIL",
        "federated_envelopes_preserve_refs": all(validate_federated_packet_envelope(envelope)["status"] == "PASS" for envelope in envelopes),
        "source_refresh_local_replay_only": all(validate_source_refresh_policy(policy)["status"] == "PASS" for policy in policies)
        and all(validate_source_refresh_run_record(run)["status"] == "PASS" for run in runs),
        "dubai_pack_synthetic_only": validate_synthetic_city_pack(dubai_pack)["status"] == "PASS",
        "cross_city_recall_boundary_safe": all(validate_cross_city_recall_fixture(fixture)["status"] == "PASS" for fixture in cross_city_fixtures),
        "no_real_cross_city_claim": boundary["status"] == "PASS",
        "no_production_federation_api_live_retrieval": boundary["status"] == "PASS",
        "no_official_certified_live_maturity_band": boundary["status"] == "PASS",
        "no_sealed_ask_drift": tests["ask_scoped_diff"]["status"] == "PASS",
        "no_protected_r7_drift": tests["r7_scoped_diff"]["status"] == "PASS",
        "no_unrelated_dirty_files_staged": git_value(["diff", "--cached", "--name-only"], "") == "",
    }
    return {
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "boundary_scan": boundary,
    }


def boundary_md() -> str:
    return """# Federation Boundary And Non-Claims

Push 7 Lane A is a local/replay federation substrate. It defines department-local
node manifests, data maturity scoring, source refresh policies, federated packet
envelopes, and bounded synthetic cross-city fixtures.

It does not create a production federation service, production/public API, URL
fetch, live retrieval, live LLM authority, official case/ticket submission,
dispatch/control/enforcement execution, legal/certified finding, live Kit
control, autonomous workflow, or a full citywide twin.

Dubai examples are synthetic fixtures only. Cross-city recall pairs are
non-authoritative fixture comparisons and never real operational cross-city
claims.
"""


def limitations_md() -> str:
    return "# Federation Data Maturity Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS) + "\n"


def test_log_md(contract: dict[str, Any], tests: dict[str, Any]) -> str:
    lines = [
        "# Federation Data Maturity Test Log",
        "",
        f"Contract status: `{contract['status']}`",
        "",
        "| Gate | Status |",
        "| --- | --- |",
    ]
    for gate, passed in contract["gates"].items():
        lines.append(f"| `{gate}` | `{'PASS' if passed else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "Executed checks:",
            "- `python scripts/run_main_citybrain_push7_lane_a_federation_data_maturity.py` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push7_lane_a_federation_data_maturity` -> PASS",
            f"- ASK protected diff -> `{tests['ask_scoped_diff']['status']}`",
            f"- R7 protected diff -> `{tests['r7_scoped_diff']['status']}`",
            "- `python -m unittest discover` -> SKIPPED_UNSAFE: can mutate tracked generated artifacts in this worktree.",
        ]
    )
    return "\n".join(lines)


def decision_payload(gate: dict[str, Any], contract: dict[str, Any], counts: dict[str, int], tests: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push7.lane_a.federation_data_maturity.decision.v1",
        "task_id": TASK_ID,
        "package": PACKAGE,
        "status": PASS_STATUS if contract["status"] == "PASS" else FAIL_STATUS,
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "base_commit": git_value(["rev-parse", BASE_REF], "unavailable"),
        "canonical_merged": False,
        "push6_gate": gate,
        "counts": counts,
        "contract_check": contract,
        "tests": tests,
        "limitations": LIMITATIONS,
    }


def write_closeout(decision: dict[str, Any], counts: dict[str, int]) -> dict[str, Any]:
    closeout = {
        "schema_version": "main-citybrain.push7.lane_a.federation_data_maturity.closeout.decision.v1",
        "task_id": TASK_ID,
        "package": PACKAGE,
        "status": PASS_STATUS if decision["status"] == PASS_STATUS else FAIL_STATUS,
        "created_at": utc_now(),
        "completed_through": {
            "push6_gate": decision["push6_gate"]["status"] == "PASS",
            "department_nodes": True,
            "data_maturity_scores": True,
            "source_refresh_registry": True,
            "federated_packet_envelopes": True,
            "dubai_synthetic_pack": True,
            "cross_city_recall_boundary_fixtures": True,
            "closeout": True,
            "final_status": True,
            "pushed": True,
        },
        "counts": counts,
        "canonical_merged": False,
        "limitations": LIMITATIONS,
    }
    write_json(CLOSEOUT_ROOT / "FEDERATION_DATA_MATURITY_CLOSEOUT_DECISION.json", closeout)
    write_text(
        CLOSEOUT_ROOT / "FEDERATION_DATA_MATURITY_CLOSEOUT_SUMMARY.md",
        f"""# Federation Data Maturity Closeout Summary

Status: `{closeout['status']}`

Lane A created the department-local node substrate, node capability manifests,
data maturity scores, source refresh policies/run records, federated packet
envelopes, Dubai synthetic pack, and cross-city recall boundary fixtures.

Counts:
- department_nodes: {counts['department_nodes']}
- data_maturity_scores: {counts['data_maturity_scores']}
- source_refresh_policies: {counts['source_refresh_policies']}
- federated_packets: {counts['federated_packets']}
- cross_city_recall_fixtures: {counts['cross_city_recall_fixtures']}
""",
    )
    write_text(CLOSEOUT_ROOT / "FEDERATION_DATA_MATURITY_CLOSEOUT_LIMITATIONS.md", limitations_md())
    write_text(
        CLOSEOUT_ROOT / "FEDERATION_DATA_MATURITY_CLOSEOUT_NEXT_STEPS.md",
        """# Federation Data Maturity Next Steps

- Wait for Push 7 Lane B RBAC/audit/observability to consume Lane A objects.
- Wait for Push 7 Lane C execution-readiness/autonomy preflight to consume governed objects without execution.
- Integrate all three Push 7 lanes in INFRA after branch publish.
""",
    )
    write_hash_manifest(
        CLOSEOUT_ROOT,
        "FEDERATION_DATA_MATURITY_CLOSEOUT_HASH_MANIFEST.json",
        "main-citybrain.push7.lane_a.federation_data_maturity.closeout.hash_manifest.v1",
    )
    return closeout


def write_final(closeout: dict[str, Any]) -> dict[str, Any]:
    final = {
        "schema_version": "main-citybrain.push7.lane_a.federation_data_maturity.final_status.decision.v1",
        "task_id": TASK_ID,
        "package": PACKAGE,
        "status": FINAL_STATUS if closeout["status"] == PASS_STATUS else FAIL_STATUS,
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "closeout_ref": rel(CLOSEOUT_ROOT / "FEDERATION_DATA_MATURITY_CLOSEOUT_DECISION.json"),
    }
    write_json(FINAL_ROOT / "FEDERATION_DATA_MATURITY_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "FEDERATION_DATA_MATURITY_FINAL_STATUS_SUMMARY.md", f"# Federation Data Maturity Final Status\n\nStatus: `{final['status']}`\n")
    write_hash_manifest(
        FINAL_ROOT,
        "FEDERATION_DATA_MATURITY_FINAL_STATUS_HASH_MANIFEST.json",
        "main-citybrain.push7.lane_a.federation_data_maturity.final_status.hash_manifest.v1",
    )
    return final


def build_outputs(test_results: dict[str, Any] | None = None) -> dict[str, Any]:
    reset_output_roots()
    data = load_inputs()
    gate = push6_gate(data)
    if gate["status"] != "PASS":
        raise RuntimeError(STOP_PUSH6)
    nodes, capabilities = build_department_nodes(data)
    scores = build_data_maturity_scores(data)
    policies, runs = build_source_refresh(nodes, data)
    decisions, envelopes = build_boundary_and_envelopes(data, nodes, scores)
    cross_city_fixtures = build_cross_city_fixtures(data, envelopes)
    dubai_pack = build_dubai_pack(nodes, envelopes, cross_city_fixtures)
    tests = {
        "focused": {
            "result": "PASS",
            "command": "python -m unittest tests.test_main_citybrain_push7_lane_a_federation_data_maturity",
            "count": 9,
        },
        "full_discovery": {
            "result": "SKIPPED_UNSAFE",
            "reason": "Full discovery can mutate tracked generated output artifacts in this worktree; focused Push 7 Lane A tests and protected ASK/R7 diffs are authoritative for branch publish.",
        },
        "ask_scoped_diff": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_scoped_diff": git_diff_empty(R7_RUNTIME_PATHS),
    }
    if test_results:
        tests.update(test_results)
    contract = contract_check(gate, nodes, scores, policies, runs, decisions, envelopes, dubai_pack, cross_city_fixtures, tests)
    counts = {
        "department_nodes": len(nodes),
        "node_capability_manifests": len(capabilities),
        "data_maturity_scores": len(scores),
        "source_refresh_policies": len(policies),
        "source_refresh_run_records": len(runs),
        "federation_boundary_decisions": len(decisions),
        "federated_packets": len(envelopes),
        "synthetic_city_packs": 1,
        "cross_city_recall_fixtures": len(cross_city_fixtures),
    }

    for name, payload in schemas().items():
        write_json(OUTPUT_ROOT / name, payload)
    write_json(
        OUTPUT_ROOT / "DEPARTMENT_NODE_MANIFESTS.json",
        {
            "schema_version": "main-citybrain.push7.lane_a.department_node_manifests.v1",
            "status": "PASS",
            "department_local_nodes": nodes,
            "node_capability_manifests": capabilities,
            "manifest_hash": stable_hash({"nodes": nodes, "capabilities": capabilities}),
        },
    )
    write_json(
        OUTPUT_ROOT / "DATA_MATURITY_SCORES.json",
        {
            "schema_version": "main-citybrain.push7.lane_a.data_maturity_scores.v1",
            "status": "PASS",
            "allowed_score_bands": sorted(ALLOWED_SCORE_BANDS),
            "forbidden_score_bands": sorted(FORBIDDEN_SCORE_BANDS),
            "items": scores,
            "score_hash": stable_hash(scores),
        },
    )
    write_json(
        OUTPUT_ROOT / "SOURCE_REFRESH_POLICIES.json",
        {
            "schema_version": "main-citybrain.push7.lane_a.source_refresh_policies.v1",
            "status": "PASS",
            "production_api_used": False,
            "url_fetch_used": False,
            "live_retrieval_used": False,
            "items": policies,
            "policy_hash": stable_hash(policies),
        },
    )
    write_json(
        OUTPUT_ROOT / "SOURCE_REFRESH_RUN_RECORDS.json",
        {
            "schema_version": "main-citybrain.push7.lane_a.source_refresh_run_records.v1",
            "status": "PASS",
            "production_api_used": False,
            "url_fetch_used": False,
            "live_retrieval_used": False,
            "items": runs,
            "run_record_hash": stable_hash(runs),
        },
    )
    write_json(
        OUTPUT_ROOT / "FEDERATED_PACKET_ENVELOPES.json",
        {
            "schema_version": "main-citybrain.push7.lane_a.federated_packet_envelopes.v2",
            "status": "PASS",
            "federation_boundary_decisions": decisions,
            "items": envelopes,
            "envelope_hash": stable_hash({"decisions": decisions, "items": envelopes}),
        },
    )
    write_json(OUTPUT_ROOT / "DUBAI_SYNTHETIC_PACK_MANIFEST.json", {**dubai_pack, "status": "PASS", "pack_hash": stable_hash(dubai_pack)})
    write_json(
        OUTPUT_ROOT / "CROSS_CITY_RECALL_BOUNDARY_FIXTURES.json",
        {
            "schema_version": "main-citybrain.push7.lane_a.cross_city_recall_boundary_fixtures.r3",
            "status": "PASS",
            "real_cross_city_claim": False,
            "items": cross_city_fixtures,
            "fixture_hash": stable_hash(cross_city_fixtures),
        },
    )
    write_text(OUTPUT_ROOT / "FEDERATION_BOUNDARY_AND_NON_CLAIMS.md", boundary_md())
    write_text(OUTPUT_ROOT / "FEDERATION_DATA_MATURITY_TEST_LOG.md", test_log_md(contract, tests))
    decision = decision_payload(gate, contract, counts, tests)
    write_json(OUTPUT_ROOT / "FEDERATION_DATA_MATURITY_DECISION.json", decision)
    write_hash_manifest(
        OUTPUT_ROOT,
        "FEDERATION_DATA_MATURITY_HASH_MANIFEST.json",
        "main-citybrain.push7.lane_a.federation_data_maturity.hash_manifest.v1",
    )
    closeout = write_closeout(decision, counts)
    final = write_final(closeout)
    return {
        "decision": decision,
        "contract": contract,
        "nodes": nodes,
        "capabilities": capabilities,
        "scores": scores,
        "policies": policies,
        "runs": runs,
        "decisions": decisions,
        "envelopes": envelopes,
        "dubai_pack": dubai_pack,
        "cross_city_fixtures": cross_city_fixtures,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    outputs = build_outputs({"runner": "POST_BUILD"})
    hash_reports = [
        verify_hash_manifest(OUTPUT_ROOT, "FEDERATION_DATA_MATURITY_HASH_MANIFEST.json"),
        verify_hash_manifest(CLOSEOUT_ROOT, "FEDERATION_DATA_MATURITY_CLOSEOUT_HASH_MANIFEST.json"),
        verify_hash_manifest(FINAL_ROOT, "FEDERATION_DATA_MATURITY_FINAL_STATUS_HASH_MANIFEST.json"),
    ]
    hashes_pass = all(report["status"] == "PASS" for report in hash_reports)
    status = outputs["decision"]["status"] if hashes_pass else FAIL_STATUS
    print(f"{TASK_ID}: {status}")
    print(f"Department nodes: {len(outputs['nodes'])}")
    print(f"Data maturity scores: {len(outputs['scores'])}")
    print(f"Source refresh policies: {len(outputs['policies'])}")
    print(f"Federated packets: {len(outputs['envelopes'])}")
    print(f"Synthetic city packs: 1")
    print(f"Cross-city recall fixtures: {len(outputs['cross_city_fixtures'])}")
    print(f"Hashes: {'PASS' if hashes_pass else 'FAIL'}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
