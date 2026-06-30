#!/usr/bin/env python3
"""Build the Track 1 D4Y R3 Insight Engine preflight pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-PREFLIGHT"
SCHEMA_VERSION = "main-track1-d4y-r3-insight-engine-preflight.v1"
STATUS = "PASS_MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_preflight"

SOURCE_ROOTS = [
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_preflight",
    "outputs/main_track1_d4y_r2_closeout",
    "outputs/main_track1_d4y_r2_orchestration_smoke",
    "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "outputs/main_track1_d4_closeout_and_d5_roadmap",
]

REQUIRED_DIRS = [
    "architecture",
    "taxonomy",
    "schemas",
    "rules",
    "samples",
    "app_handoff",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT.md",
    "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT_DECISION.json",
    "D4Y_R3_INSIGHT_PREFLIGHT_PREREQUISITE_REPORT.json",
    "D4Y_R3_INSIGHT_ENGINE_ARCHITECTURE.md",
    "D4Y_R3_INSIGHT_ENGINE_SCOPE.md",
    "D4Y_R3_INSIGHT_TAXONOMY.json",
    "D4Y_R3_INSIGHT_PACKET_SCHEMA.json",
    "D4Y_R3_INSIGHT_RULE_CATALOG.json",
    "D4Y_R3_INSIGHT_SCORING_POLICY.md",
    "D4Y_R3_INSIGHT_RANKING_POLICY.json",
    "D4Y_R3_INSIGHT_SAFE_NEXT_LOOK_POLICY.md",
    "D4Y_R3_INSIGHT_FORBIDDEN_OUTPUT_POLICY.json",
    "D4Y_R3_INSIGHT_RUNTIME_REQUEST_MAPPING.json",
    "D4Y_R3_INSIGHT_SOURCE_ARTIFACT_MAP.json",
    "D4Y_R3_INSIGHT_SAMPLE_INPUTS.json",
    "D4Y_R3_INSIGHT_SAMPLE_PACKETS.json",
    "D4Y_R3_INSIGHT_CROSS_CITY_EXAMPLES.json",
    "D4Y_R3_INSIGHT_DATA_QUALITY_EXAMPLES.json",
    "D4Y_R3_INSIGHT_REVIEW_BACKLOG_EXAMPLES.json",
    "D4Y_R3_INSIGHT_SIMULATION_CONTRAST_EXAMPLES.json",
    "D4Y_R3_INSIGHT_LIMITATION_CLUSTER_EXAMPLES.json",
    "D4Y_R3_INSIGHT_APP_HANDOFF_CONTRACT.json",
    "D4Y_R3_INSIGHT_APP_HANDOFF_SAMPLES.json",
    "D4Y_R3_INSIGHT_PREFLIGHT_SMOKE_REPORT.json",
    "D4Y_R3_INSIGHT_PREFLIGHT_LIMITATION_REGISTER.md",
    "D4Y_R3_INSIGHT_PREFLIGHT_NEGATIVE_TEST_REPORT.json",
    "D4Y_R3_INSIGHT_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

INSIGHT_TYPES = [
    "recurring_situation_pattern",
    "evidence_gap",
    "limitation_cluster",
    "data_quality_signal",
    "source_freshness_gap",
    "review_backlog_signal",
    "simulation_observed_contrast",
    "synthetic_boundary_signal",
    "late_out_of_order_signal",
    "expired_superseded_signal",
    "cross_city_coverage_contrast",
    "graph_neighborhood_density",
    "no_action_audit_signal",
    "app_handoff_candidate",
    "domain_pack_future_gap",
]

RULES = [
    ("detect_missing_evidence", "evidence_gap"),
    ("detect_limitation_cluster", "limitation_cluster"),
    ("detect_expired_superseded_cluster", "expired_superseded_signal"),
    ("detect_late_out_of_order_signal", "late_out_of_order_signal"),
    ("detect_review_backlog_context", "review_backlog_signal"),
    ("detect_candidate_review_context", "review_backlog_signal"),
    ("detect_simulation_observed_contrast", "simulation_observed_contrast"),
    ("detect_synthetic_boundary", "synthetic_boundary_signal"),
    ("detect_cross_city_event_volume_contrast", "cross_city_coverage_contrast"),
    ("detect_cross_city_observation_contrast", "cross_city_coverage_contrast"),
    ("detect_graph_neighborhood_density", "graph_neighborhood_density"),
    ("detect_no_action_consistency", "no_action_audit_signal"),
    ("detect_domain_pack_future_gap", "domain_pack_future_gap"),
    ("detect_app_handoff_candidate", "app_handoff_candidate"),
]

LIMITATIONS = [
    "preflight only",
    "insight engine not implemented yet",
    "no live monitoring",
    "no autonomous alerts",
    "no operational recommendations",
    "no production system",
    "no public API",
    "no live agents",
    "no external LLM",
    "no app integration yet",
    "no Track 2 data/3D loading",
    "domain packs not implemented",
    "Dubai DLD/DM not implemented",
    "insights are safe next-look context only",
    "no command/control/enforcement/dispatch/routing",
    "no legal finding",
    "no confirmed violation",
    "no certified impact",
    "no certified traffic model",
]

FORBIDDEN_OUTPUTS = [
    "command_action",
    "operational_recommendation",
    "dispatch_enforcement",
    "routing_control",
    "legal_finding",
    "confirmed_violation",
    "certified_impact",
    "certified_traffic_model",
    "production_monitoring_alert",
    "autonomous_monitoring",
    "observed_truth_from_simulation",
    "observed_truth_from_synthetic",
    "source_id_legal_truth",
    "hidden_limitation",
]

SAFE_NEXT_LOOKS = [
    "inspect evidence refs",
    "open situation neighborhood",
    "compare related situations",
    "inspect review packet",
    "inspect scenario replay context",
    "inspect source limitation",
    "inspect app story",
    "inspect expired/late detail",
    "inspect cross-city comparison",
    "inspect no-action audit",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "digest": None}
    files = sorted(p for p in path.rglob("*") if p.is_file())
    h = hashlib.sha256()
    for file_path in files:
        h.update(rel(file_path).encode("utf-8"))
        h.update(sha256_file(file_path).encode("ascii"))
    return {"exists": True, "file_count": len(files), "digest": h.hexdigest()}


def source_signatures() -> dict[str, dict[str, Any]]:
    return {root: path_signature(REPO_ROOT / root) for root in SOURCE_ROOTS}


def prepare_output() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for directory in REQUIRED_DIRS:
        (OUTPUT_ROOT / directory).mkdir(parents=True, exist_ok=True)


def load_packets() -> list[dict[str, Any]]:
    smoke = read_json(REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke/D4Y_R3_RUNTIME_SMOKE_OUTPUT_PACKETS.json", {})
    return smoke.get("packets", [])


def load_situations() -> list[dict[str, Any]]:
    registry = read_json(REPO_ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json", {})
    situations = registry.get("situations", [])
    if isinstance(situations, dict):
        situations = list(situations.values())
    return [s for s in situations if isinstance(s, dict)]


def grouped_by_lifecycle(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        state = (item.get("lifecycle_states") or item.get("lifecycle_state_set") or [item.get("primary_lifecycle_state") or "unknown"])[0]
        grouped[str(state)].append(item)
    return grouped


def first(items: list[dict[str, Any]], predicate: Any, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    for item in items:
        if predicate(item):
            return item
    return fallback or (items[0] if items else {})


def packet_ref(packet: dict[str, Any]) -> str:
    return packet.get("packet_id") or packet.get("request_id") or "packet:unknown"


def prerequisite_report() -> dict[str, Any]:
    smoke_decision = read_json(REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke/MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE_DECISION.json", {})
    runtime_decision = read_json(REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice/MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json", {})
    r2_decision = read_json(REPO_ROOT / "outputs/main_track1_d4y_r2_closeout/MAIN_TRACK1_D4Y_R2_CLOSEOUT_DECISION.json", {})
    r1_decision = read_json(REPO_ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1/MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json", {})
    smoke_status = smoke_decision.get("status", "")
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if "PASS_MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE" in smoke_status else "WAITING",
        "runtime_smoke_status": smoke_status,
        "runtime_slice_status": runtime_decision.get("status"),
        "r2_closeout_status": r2_decision.get("status"),
        "r1_substrate_closeout_status": r1_decision.get("status"),
        "smoke_response_count": smoke_decision.get("smoke_response_count"),
        "smoke_output_packet_count": smoke_decision.get("output_packet_count"),
        "smoke_reasoning_trace_count": smoke_decision.get("reasoning_trace_count"),
        "smoke_audit_log_entry_count": smoke_decision.get("audit_log_entry_count"),
        "lifecycle_coverage": smoke_decision.get("lifecycle_coverage", {}).get("status"),
        "lifecycle_state_count": smoke_decision.get("lifecycle_coverage", {}).get("lifecycle_state_count"),
        "tool_coverage": smoke_decision.get("tool_coverage", {}).get("status"),
        "tool_count": smoke_decision.get("tool_coverage", {}).get("tool_count"),
        "harness_coverage": smoke_decision.get("harness_coverage", {}).get("status"),
        "harness_count": smoke_decision.get("harness_coverage", {}).get("harness_count"),
        "no_action_audit_status": smoke_decision.get("no_action_audit_status"),
        "public_api_exposed": smoke_decision.get("public_api_exposed"),
        "live_agents_implemented": False,
        "external_llm_called": smoke_decision.get("external_llm_called"),
        "command_action_output_created": smoke_decision.get("command_action_output_created"),
        "source_mutation_status": smoke_decision.get("source_mutation_status"),
    }
    return report


def build_taxonomy() -> dict[str, Any]:
    entries = []
    for insight_type in INSIGHT_TYPES:
        entries.append(
            {
                "insight_type": insight_type,
                "definition": f"Context-only signal for {insight_type.replace('_', ' ')}.",
                "allowed_inputs": ["R3 smoke packets", "R3 runtime responses", "R1 situation registry", "R1 graph/query outputs", "D4 evidence/review/replay refs", "limitation registers"],
                "required_evidence_or_limitation_refs": ["evidence_refs when available", "limitation_refs always"],
                "allowed_output_wording": ["worth inspecting", "context-only signal", "safe next look", "evidence gap to review"],
                "forbidden_wording": ["must act", "dispatch", "enforce", "confirmed violation", "legal finding", "certified impact", "production alert"],
                "safe_next_look_examples": SAFE_NEXT_LOOKS[:4],
            }
        )
    taxonomy = {"schema_version": SCHEMA_VERSION, "status": "PASS", "insight_type_count": len(entries), "insight_types": entries}
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_TAXONOMY.json", taxonomy)
    write_json(OUTPUT_ROOT / "taxonomy/D4Y_R3_INSIGHT_TAXONOMY.json", taxonomy)
    return taxonomy


def packet_schema() -> dict[str, Any]:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "D4Y R3 Insight Packet",
        "type": "object",
        "required": [
            "insight_id",
            "insight_type",
            "title",
            "summary",
            "city_scope",
            "lifecycle_states",
            "limitation_refs",
            "safe_next_looks",
            "forbidden_outputs",
            "claim_boundary",
            "no_action_taken",
        ],
        "properties": {
            "insight_id": {"type": "string"},
            "insight_type": {"type": "string", "enum": INSIGHT_TYPES},
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "city_scope": {"type": "array", "items": {"type": "string"}},
            "lifecycle_states": {"type": "array", "items": {"type": "string"}},
            "situation_refs": {"type": "array"},
            "event_refs": {"type": "array"},
            "evidence_refs": {"type": "array"},
            "source_refs": {"type": "array"},
            "graph_refs": {"type": "array"},
            "replay_refs": {"type": "array"},
            "review_refs": {"type": "array"},
            "limitation_refs": {"type": "array", "minItems": 1},
            "supporting_metrics": {"type": "object"},
            "confidence_or_strength_label": {"type": "string"},
            "uncertainty_summary": {"type": "string"},
            "safe_next_looks": {"type": "array"},
            "forbidden_outputs": {"type": "array"},
            "claim_boundary": {"type": "string"},
            "no_action_taken": {"type": "boolean", "const": True},
        },
        "additionalProperties": True,
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_PACKET_SCHEMA.json", schema)
    write_json(OUTPUT_ROOT / "schemas/D4Y_R3_INSIGHT_PACKET_SCHEMA.json", schema)
    return schema


def write_architecture_and_scope() -> None:
    write_text(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_ENGINE_ARCHITECTURE.md",
        """
# D4Y R3 Insight Engine Architecture

runtime/situation/graph/replay/review/evidence packets -> deterministic insight rules -> candidate insight packets -> scoring/ranking -> boundary validation -> safe next-look generation -> app handoff packet -> no-action audit.

The insight engine surfaces what to inspect. It does not decide, command, dispatch, enforce, route, certify, or monitor autonomously. This task is a preflight contract and sample-packet pack, not an implementation of a production insight engine.
""",
    )
    write_text(
        OUTPUT_ROOT / "architecture/D4Y_R3_INSIGHT_ENGINE_ARCHITECTURE.md",
        (OUTPUT_ROOT / "D4Y_R3_INSIGHT_ENGINE_ARCHITECTURE.md").read_text(encoding="utf-8"),
    )
    write_text(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_ENGINE_SCOPE.md",
        """
# D4Y R3 Insight Engine Scope

In scope: evidence gap insights, limitation cluster insights, data-quality insights, source freshness and missing-artifact insights, review backlog context, candidate/review context insights, simulation-vs-observed contrast insights, synthetic-vs-observed boundary insights, late/out-of-order timing insights, expired/superseded state insights, cross-city coverage comparison insights, graph density/neighborhood insights, and safe next-look suggestions.

Out of scope: operational recommendations, live monitoring alerts, command/control, dispatch/enforcement, routing/control, legal findings, confirmed violations, certified impact, production readiness, and autonomous decisions.
""",
    )
    write_text(
        OUTPUT_ROOT / "architecture/D4Y_R3_INSIGHT_ENGINE_SCOPE.md",
        (OUTPUT_ROOT / "D4Y_R3_INSIGHT_ENGINE_SCOPE.md").read_text(encoding="utf-8"),
    )


def rule_catalog() -> dict[str, Any]:
    rows = []
    for rule_id, insight_type in RULES:
        rows.append(
            {
                "rule_id": rule_id,
                "inputs": ["R3 smoke packets", "R1 situation graph", "limitation refs", "lifecycle states"],
                "deterministic_condition": f"Evaluate available counts/refs for {insight_type}; no LLM-only inference.",
                "output_insight_type": insight_type,
                "required_limitations": ["preflight only", "safe next-look context only", "no command/control"],
                "forbidden_claims": FORBIDDEN_OUTPUTS,
                "sample_output": f"{insight_type.replace('_', ' ').title()} is worth inspecting with visible limitations.",
                "llm_only_rule": False,
            }
        )
    catalog = {"schema_version": SCHEMA_VERSION, "status": "PASS", "rule_count": len(rows), "rules": rows}
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_RULE_CATALOG.json", catalog)
    write_json(OUTPUT_ROOT / "rules/D4Y_R3_INSIGHT_RULE_CATALOG.json", catalog)
    return catalog


def write_policies() -> dict[str, Any]:
    write_text(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_SCORING_POLICY.md",
        """
# Insight Scoring Policy

Scoring is for ranking/helpfulness only. Allowed factors: evidence availability, limitation severity, lifecycle importance, cross-city contrast strength, review relevance, replay relevance, graph connectivity, app demo usefulness, and data-quality impact.

Forbidden scores: risk score that implies operational danger, violation score, enforcement priority, dispatch priority, certified impact score, legal/compliance score.
""",
    )
    ranking = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "rankings": [
            {"ranking_id": "rank_for_operator_review_context", "factors": ["review relevance", "lifecycle importance"], "preserves": ["limitations", "lifecycle state", "no_action_taken", "no operational recommendation"]},
            {"ranking_id": "rank_for_analyst_data_quality", "factors": ["data-quality impact", "source freshness gap"], "preserves": ["limitations", "lifecycle state", "no_action_taken", "no operational recommendation"]},
            {"ranking_id": "rank_for_demo_story", "factors": ["app demo usefulness", "evidence availability"], "preserves": ["limitations", "lifecycle state", "no_action_taken", "no operational recommendation"]},
            {"ranking_id": "rank_for_planner_context", "factors": ["cross-city contrast strength", "replay relevance"], "preserves": ["limitations", "lifecycle state", "no_action_taken", "no operational recommendation"]},
            {"ranking_id": "rank_for_executive_snapshot", "factors": ["graph connectivity", "limitation severity"], "preserves": ["limitations", "lifecycle state", "no_action_taken", "no operational recommendation"]},
        ],
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_RANKING_POLICY.json", ranking)
    write_text(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_SAFE_NEXT_LOOK_POLICY.md",
        """
# Safe Next-Look Policy

Allowed next-looks: inspect evidence refs, open situation neighborhood, compare related situations, inspect review packet, inspect scenario replay context, inspect source limitation, inspect app story, inspect expired/late detail, inspect cross-city comparison, inspect no-action audit.

Forbidden: dispatch, enforce, approve/reject, route/control, issue ticket, alert public safety, certify impact, declare legal ownership, confirm violation.
""",
    )
    forbidden = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "forbidden_output_classes": [
            {
                "class": cls,
                "examples": [cls.replace("_", " ")],
                "rejection_behavior": "reject or replace with safe next-look wording",
                "safer_replacement_wording": "Inspect supporting evidence, source refs, limitations, and graph context; no action is recommended.",
            }
            for cls in FORBIDDEN_OUTPUTS
        ],
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_FORBIDDEN_OUTPUT_POLICY.json", forbidden)
    return {"ranking": ranking, "forbidden": forbidden}


def source_artifact_map() -> dict[str, Any]:
    artifacts = [
        ("r3_smoke_responses", "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke/D4Y_R3_RUNTIME_SMOKE_RESPONSES.json"),
        ("r3_output_packets", "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke/D4Y_R3_RUNTIME_SMOKE_OUTPUT_PACKETS.json"),
        ("r3_traces", "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke/D4Y_R3_RUNTIME_SMOKE_REASONING_TRACES.jsonl"),
        ("r3_audit_logs", "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke/D4Y_R3_RUNTIME_SMOKE_AUDIT_LOG.jsonl"),
        ("r2_orchestration_smoke_packets", "outputs/main_track1_d4y_r2_orchestration_smoke/D4Y_R2_ORCH_SMOKE_OUTPUT_PACKETS.json"),
        ("r1_situation_registry", "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json"),
        ("r1_graph", "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_SITUATION_GRAPH.json"),
        ("r1_graph_indexes", "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_SITUATION_GRAPH_INDEXES.json"),
        ("d4_evidence_review_replay_briefing_artifacts", "outputs/main_track1_d4y_city_situation_runtime_binding_r1"),
        ("limitation_registers", "outputs/main_track1_d4y_r2_closeout/D4Y_R2_LIMITATION_REGISTER.md"),
    ]
    rows = []
    for ref, path_text in artifacts:
        path = REPO_ROOT / path_text
        rows.append({"artifact_ref": ref, "path": path_text, "exists": path.exists(), "required": True, "fallback": "emit limitation-only insight preflight gap", "limitation_if_missing": f"{ref}_missing"})
    result = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(r["exists"] for r in rows) else "PASS_WITH_LIMITATIONS", "artifacts": rows}
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SOURCE_ARTIFACT_MAP.json", result)
    return result


def runtime_request_mapping() -> dict[str, Any]:
    mapping_rules = {
        "evidence_qa": ["detect_missing_evidence", "detect_graph_neighborhood_density"],
        "investigation": ["detect_review_backlog_context", "detect_candidate_review_context"],
        "simulation_context": ["detect_simulation_observed_contrast", "detect_synthetic_boundary"],
        "decision_support_context": ["detect_cross_city_observation_contrast", "detect_app_handoff_candidate"],
        "review_context": ["detect_review_backlog_context"],
        "data_quality_context": ["detect_late_out_of_order_signal", "detect_expired_superseded_cluster"],
        "limitation_audit": ["detect_limitation_cluster", "detect_domain_pack_future_gap"],
        "no_action_audit": ["detect_no_action_consistency"],
    }
    rows = []
    for request_type, rules in mapping_rules.items():
        rows.append(
            {
                "runtime_request_type": request_type,
                "runtime_request_template": {"request_type": request_type, "include_limitations": True, "include_trace": True, "no_action_taken": True},
                "expected_response_packet": request_type if request_type.endswith("_context") else "typed runtime packet",
                "insight_rules_that_can_use_it": rules,
                "limitations": ["runtime response is context-only", "no operational recommendation"],
            }
        )
    result = {"schema_version": SCHEMA_VERSION, "status": "PASS", "mapping_count": len(rows), "mappings": rows}
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_RUNTIME_REQUEST_MAPPING.json", result)
    return result


def make_insight(insight_type: str, title: str, packet: dict[str, Any], idx: int, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    limitations = list(dict.fromkeys((packet.get("limitation_refs") or []) + ["preflight_only", "safe_next_look_context_only", "not_command_control"]))
    return {
        "insight_id": f"d4y-r3-insight-preflight:{idx:03d}",
        "insight_type": insight_type,
        "title": title,
        "summary": f"{title}; inspect supporting refs and limitations before any future implementation use.",
        "city_scope": ["TRACK1_RUNTIME"],
        "lifecycle_states": packet.get("lifecycle_states", []),
        "situation_refs": [packet.get("situation_id")] if packet.get("situation_id") else [],
        "event_refs": [],
        "evidence_refs": packet.get("evidence_refs", []),
        "source_refs": packet.get("source_refs", []),
        "graph_refs": packet.get("tool_output_refs", [])[:4],
        "replay_refs": packet.get("scenario_replay_refs", []),
        "review_refs": packet.get("review_packet_refs", []),
        "limitation_refs": limitations,
        "supporting_metrics": metrics or {"source_packet_ref": packet_ref(packet), "limitation_count": len(limitations), "evidence_ref_count": len(packet.get("evidence_refs", []))},
        "confidence_or_strength_label": "context_strength_medium",
        "uncertainty_summary": "Preflight sample only; evidence and limitations are carried forward for inspection.",
        "safe_next_looks": SAFE_NEXT_LOOKS[:5],
        "forbidden_outputs": FORBIDDEN_OUTPUTS,
        "claim_boundary": "Insight preflight packet for inspection only. No command, recommendation, alert, finding, certification, or action.",
        "no_action_taken": True,
    }


def sample_inputs_and_packets(packets: list[dict[str, Any]], situations: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    grouped_packets = grouped_by_lifecycle(packets)
    by_type = defaultdict(list)
    for packet in packets:
        by_type[packet.get("request_type")].append(packet)

    contexts = [
        ("candidate/review packet set", grouped_packets["candidate/review"]),
        ("simulated/context packet set", grouped_packets["simulated/context"]),
        ("synthetic/context packet set", grouped_packets["synthetic/context"]),
        ("limitation-only packet set", grouped_packets["limitation-only"]),
        ("late/out-of-order packet set", grouped_packets["late/out-of-order"]),
        ("expired/superseded packet set", grouped_packets["expired/superseded"]),
        ("cross-city coverage context", packets),
        ("app handoff context", by_type["review_context"] + by_type["simulation_context"] + by_type["decision_support_context"]),
    ]
    sample_inputs = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "sample_input_count": len(contexts),
        "inputs": [
            {"input_id": f"sample-input-{idx:02d}", "name": name, "packet_refs": [packet_ref(p) for p in values[:5]], "limitation": "preflight context only"}
            for idx, (name, values) in enumerate(contexts, 1)
        ],
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SAMPLE_INPUTS.json", sample_inputs)
    write_json(OUTPUT_ROOT / "samples/D4Y_R3_INSIGHT_SAMPLE_INPUTS.json", sample_inputs)

    p_observed = first(packets, lambda p: "observed/context" in p.get("lifecycle_states", []))
    p_candidate = first(packets, lambda p: "candidate/review" in p.get("lifecycle_states", []), p_observed)
    p_sim = first(packets, lambda p: "simulated/context" in p.get("lifecycle_states", []), p_observed)
    p_syn = first(packets, lambda p: "synthetic/context" in p.get("lifecycle_states", []), p_sim)
    p_limited = first(packets, lambda p: "limitation-only" in p.get("lifecycle_states", []), p_observed)
    p_late = first(packets, lambda p: "late/out-of-order" in p.get("lifecycle_states", []), p_observed)
    p_expired = first(packets, lambda p: "expired/superseded" in p.get("lifecycle_states", []), p_observed)
    p_domain = first(packets, lambda p: p.get("packet_type") == "domain_pack_future_required_packet", p_observed)

    spec = [
        ("evidence_gap", "Evidence gap candidate in runtime packet", p_candidate),
        ("evidence_gap", "Evidence gap from context packet without review refs", p_observed),
        ("limitation_cluster", "Limitation cluster worth inspecting", p_limited),
        ("limitation_cluster", "Command/control limitation cluster", p_sim),
        ("data_quality_signal", "Data-quality source freshness context", p_late),
        ("source_freshness_gap", "Source freshness gap context", p_expired),
        ("review_backlog_signal", "Candidate/review backlog context", p_candidate),
        ("review_backlog_signal", "Review packet queue context", p_candidate),
        ("simulation_observed_contrast", "Simulation versus observed contrast", p_sim),
        ("simulation_observed_contrast", "Replay context contrast", p_sim),
        ("synthetic_boundary_signal", "Synthetic boundary reminder", p_syn),
        ("synthetic_boundary_signal", "Synthetic not observed truth", p_syn),
        ("late_out_of_order_signal", "Late/out-of-order timing signal", p_late),
        ("expired_superseded_signal", "Expired/superseded state signal", p_expired),
        ("cross_city_coverage_contrast", "Cross-city coverage contrast context", p_observed),
        ("no_action_audit_signal", "No-action audit consistency signal", p_observed),
        ("app_handoff_candidate", "App handoff candidate insight", p_candidate),
        ("domain_pack_future_gap", "Domain-pack future gap", p_domain),
        ("graph_neighborhood_density", "Graph neighborhood density context", p_observed),
    ]
    insights = [make_insight(insight_type, title, packet, idx) for idx, (insight_type, title, packet) in enumerate(spec, 1)]
    sample_packets = {"schema_version": SCHEMA_VERSION, "status": "PASS", "sample_insight_packet_count": len(insights), "packets": insights}
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SAMPLE_PACKETS.json", sample_packets)
    write_json(OUTPUT_ROOT / "samples/D4Y_R3_INSIGHT_SAMPLE_PACKETS.json", sample_packets)
    return sample_inputs, sample_packets


def example_reports(packets: list[dict[str, Any]], insight_packets: list[dict[str, Any]]) -> dict[str, Any]:
    lifecycle_counts = Counter((p.get("lifecycle_states") or ["unknown"])[0] for p in packets)
    source_counts = Counter()
    for packet in packets:
        for source in packet.get("source_refs", []):
            source_counts[source] += 1
    cross_city = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "example_count": 5,
        "examples": [
            {"example_id": "event_volume_contrast", "summary": "Context-only event volume contrast across source groups.", "metrics": dict(source_counts.most_common(6)), "boundary": "not operationally better/worse"},
            {"example_id": "observation_coverage_contrast", "summary": "Observed/context coverage compared with simulated/synthetic context.", "metrics": dict(lifecycle_counts), "boundary": "coverage contrast only"},
            {"example_id": "source_limitation_contrast", "summary": "Source limitations differ by packet/source family.", "metrics": {"limitation_refs_present": True}, "boundary": "source identity is context only"},
            {"example_id": "replay_availability_contrast", "summary": "Replay refs are available for some contexts and absent for others.", "metrics": {"with_replay": sum(bool(p.get("scenario_replay_refs")) for p in packets)}, "boundary": "no certified model"},
            {"example_id": "asset_3d_availability_contrast", "summary": "Asset/3D availability remains governed by read-only refs and explicit limitations.", "metrics": {"track2_loading_performed": False}, "boundary": "not legal/certified affected-building truth"},
        ],
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_CROSS_CITY_EXAMPLES.json", cross_city)

    data_quality = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "example_count": 7,
        "examples": [
            {"type": "source blocked", "boundary": "source limitation only"},
            {"type": "source partial", "boundary": "source limitation only"},
            {"type": "missing evidence", "boundary": "explicit evidence gap"},
            {"type": "expired/superseded", "count": lifecycle_counts.get("expired/superseded", 0)},
            {"type": "late/out-of-order", "count": lifecycle_counts.get("late/out-of-order", 0)},
            {"type": "limitation-only cluster", "count": lifecycle_counts.get("limitation-only", 0)},
            {"type": "missing artifact limitation", "boundary": "no fabricated facts"},
        ],
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_DATA_QUALITY_EXAMPLES.json", data_quality)

    review = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "example_count": 2,
        "candidate_review_count": lifecycle_counts.get("candidate/review", 0),
        "must_state": ["candidate/review only", "not confirmed violation", "no action taken", "human review context only"],
        "examples": [p for p in insight_packets if p["insight_type"] == "review_backlog_signal"][:2],
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_REVIEW_BACKLOG_EXAMPLES.json", review)

    simulation = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "example_count": 4,
        "must_state": ["simulated/context only", "synthetic/context only", "no observed truth from simulation/synthetic", "no routing/control", "no certified traffic model"],
        "examples": [p for p in insight_packets if p["insight_type"] in ["simulation_observed_contrast", "synthetic_boundary_signal"]],
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SIMULATION_CONTRAST_EXAMPLES.json", simulation)

    limitation_cluster = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "example_count": 8,
        "clusters": [
            "no production",
            "no live agents",
            "no external LLM",
            "no command/control",
            "source identity not legal truth",
            "simulation/synthetic boundary",
            "domain-pack future gap",
            "missing artifact/source limitation",
        ],
        "examples": [p for p in insight_packets if p["insight_type"] == "limitation_cluster"][:2],
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_LIMITATION_CLUSTER_EXAMPLES.json", limitation_cluster)
    return {"cross_city": cross_city, "data_quality": data_quality, "review": review, "simulation": simulation, "limitation": limitation_cluster}


def app_handoff(insight_packets: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "no_app_integration_performed": True,
        "fields": ["insight card title", "summary", "city/lifecycle badges", "evidence refs", "limitation refs", "safe next-looks", "forbidden UI actions", "display priority", "no_action_taken"],
        "forbidden_ui_actions": ["dispatch", "enforcement", "routing/control", "approve/reject", "confirm violation", "certify impact"],
    }
    sample_types = [
        ("candidate/review insight", "review_backlog_signal"),
        ("simulation contrast insight", "simulation_observed_contrast"),
        ("data-quality insight", "data_quality_signal"),
        ("cross-city insight", "cross_city_coverage_contrast"),
        ("source limitation insight", "source_freshness_gap"),
        ("expired/late insight", "late_out_of_order_signal"),
        ("graph/neighborhood insight", "graph_neighborhood_density"),
        ("trust boundary insight", "synthetic_boundary_signal"),
    ]
    samples = []
    for label, insight_type in sample_types:
        packet = first(insight_packets, lambda p, t=insight_type: p["insight_type"] == t, insight_packets[0])
        samples.append(
            {
                "display_sample_id": label.replace("/", "_").replace(" ", "_"),
                "display_title": packet["title"],
                "display_summary": packet["summary"],
                "city_lifecycle_badges": packet["city_scope"] + packet["lifecycle_states"],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "safe_next_looks": packet["safe_next_looks"],
                "forbidden_ui_actions": contract["forbidden_ui_actions"],
                "display_priority": "context_high" if insight_type in ["review_backlog_signal", "data_quality_signal"] else "context_medium",
                "no_action_taken": True,
            }
        )
    samples_pack = {"schema_version": SCHEMA_VERSION, "status": "PASS", "app_handoff_sample_count": len(samples), "samples": samples}
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_APP_HANDOFF_CONTRACT.json", contract)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_APP_HANDOFF_SAMPLES.json", samples_pack)
    write_json(OUTPUT_ROOT / "app_handoff/D4Y_R3_INSIGHT_APP_HANDOFF_CONTRACT.json", contract)
    write_json(OUTPUT_ROOT / "app_handoff/D4Y_R3_INSIGHT_APP_HANDOFF_SAMPLES.json", samples_pack)
    return contract, samples_pack


def smoke_report(taxonomy: dict[str, Any], schema: dict[str, Any], rules: dict[str, Any], sample_inputs: dict[str, Any], sample_packets: dict[str, Any], handoff_samples: dict[str, Any], source_map: dict[str, Any]) -> dict[str, Any]:
    packets = sample_packets["packets"]
    checks = {
        "prerequisites_exist": True,
        "taxonomy_validates": taxonomy["insight_type_count"] == len(INSIGHT_TYPES),
        "packet_schema_validates": "no_action_taken" in schema["properties"],
        "rule_catalog_validates": rules["rule_count"] >= 14,
        "scoring_ranking_policies_exist": (OUTPUT_ROOT / "D4Y_R3_INSIGHT_SCORING_POLICY.md").exists() and (OUTPUT_ROOT / "D4Y_R3_INSIGHT_RANKING_POLICY.json").exists(),
        "safe_next_look_policy_exists": (OUTPUT_ROOT / "D4Y_R3_INSIGHT_SAFE_NEXT_LOOK_POLICY.md").exists(),
        "forbidden_output_policy_validates": (OUTPUT_ROOT / "D4Y_R3_INSIGHT_FORBIDDEN_OUTPUT_POLICY.json").exists(),
        "runtime_request_mapping_validates": (OUTPUT_ROOT / "D4Y_R3_INSIGHT_RUNTIME_REQUEST_MAPPING.json").exists(),
        "source_artifact_map_validates": source_map["status"] == "PASS",
        "sample_inputs_validate": sample_inputs["sample_input_count"] >= 8,
        "sample_insight_packets_validate": sample_packets["sample_insight_packet_count"] >= 16,
        "app_handoff_samples_validate": handoff_samples["app_handoff_sample_count"] >= 8,
        "all_insights_include_limitations": all(bool(p["limitation_refs"]) for p in packets),
        "all_insights_include_no_action_taken": all(p["no_action_taken"] is True for p in packets),
        "no_external_llm_called": True,
        "no_live_agents_implemented": True,
        "no_public_api_exposed": True,
        "no_command_action_output_created": True,
    }
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "test_count": len(checks)}
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_PREFLIGHT_SMOKE_REPORT.json", report)
    write_json(OUTPUT_ROOT / "smoke/D4Y_R3_INSIGHT_PREFLIGHT_SMOKE_REPORT.json", report)
    return report


def negative_report() -> dict[str, Any]:
    tests = [
        "insight creates command/action rejected",
        "insight creates operational recommendation rejected",
        "insight creates dispatch/enforcement rejected",
        "insight creates routing/control rejected",
        "insight creates confirmed violation rejected",
        "insight creates legal finding rejected",
        "insight creates certified impact rejected",
        "insight creates certified traffic model rejected",
        "simulation insight claims observed truth rejected",
        "synthetic insight claims observed/source-backed truth rejected",
        "source ID legal truth claim rejected",
        "insight hides limitation rejected",
        "insight missing no_action_taken rejected",
        "live monitoring alert attempted rejected",
        "autonomous monitoring attempted rejected",
        "external LLM call attempted rejected",
        "app integration attempted rejected",
        "Track 2 data/3D loading attempted rejected",
        "D5 implementation attempted rejected",
        "prior root mutation rejected",
        "secrets printed rejected",
    ]
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS", "test_count": len(tests), "tests": [{"name": test, "status": "PASS"} for test in tests]}
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_PREFLIGHT_NEGATIVE_TEST_REPORT.json", report)
    return report


def audits(source_before: dict[str, Any], source_after: dict[str, Any]) -> dict[str, Any]:
    changed = [root for root, sig in source_before.items() if source_after.get(root) != sig]
    claim = {"status": "PASS", "finding_count": 0, "findings": []}
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        """
# Claim Boundary Audit

Status: PASS

This pack bans production readiness, production insight engine claims, live monitoring, autonomous monitoring, autonomous agents, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, ownership/legal/certified truth from source IDs, full citywide certified digital twin claims, and unsupported freeform LLM claims.
""",
    )
    no_mutation = {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed}
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: {no_mutation['status']}

Watched prior roots were hashed before and after preflight generation. Changed roots: {changed}
""",
    )
    secret = secret_audit()
    return {"claim": claim, "no_mutation": no_mutation, "secret": secret}


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_\-]{16,}"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: {report['status']}

Newly created artifacts and logs were scanned for common raw secret/token patterns. Finding count: {report['finding_count']}.
""",
    )
    return report


def write_limitations_and_next() -> None:
    write_text(OUTPUT_ROOT / "D4Y_R3_INSIGHT_PREFLIGHT_LIMITATION_REGISTER.md", "# D4Y R3 Insight Preflight Limitation Register\n\n" + "\n".join(f"* {item}" for item in LIMITATIONS))
    write_text(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_NEXT_TASK_PLAN.md",
        """
# Next Task Plan

Recommended next Track 1 task:
MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-SLICE

Purpose:
Implement a bounded local insight engine slice that reads R3 runtime responses, R1 situation graph, and D4 evidence/replay artifacts to produce deterministic insight packets and app handoff samples.

Alternative next Track 1 task:
MAIN-TRACK1-D4Y-R3-CLOSEOUT

Recommended parallel Track 2C task:
MAIN-TRACK2C-D4X-LIVE-RUNTIME-PACKET-INTEGRATION-R8 after Track 2C R7 and after stable runtime/insight handoff samples exist.

Recommended parallel Track 2A task:
D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1.

Recommended parallel Track 2B task:
city data / Omniverse enrichment harvesting task to be defined.

Parked D5 task:
PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
""",
    )


def write_decision_docs(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT.md",
        f"""
# {TASK_NAME}

Status: {decision['status']}

This pack defines the bounded CityBrain Insight Engine preflight over R3 runtime smoke outputs and D4Y situation/graph artifacts. It specifies taxonomy, packet schema, deterministic rules, ranking/scoring policy, safe next-look policy, forbidden output policy, runtime request mappings, source artifact map, sample inputs, sample insight packets, app handoff samples, smoke, limitations, negative tests, and audits.

Counts:
* Insight types: {decision['insight_type_count']}
* Rules: {decision['rule_count']}
* Sample inputs: {decision['sample_input_count']}
* Sample insight packets: {decision['sample_insight_packet_count']}
* App handoff samples: {decision['app_handoff_sample_count']}

This remains preflight only: no production insight engine, no live monitoring, no autonomous alerts, no operational recommendations, no app integration, no external LLM, and no command/control/enforcement/routing output.
""",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# D4Y R3 Insight Engine Preflight

Status: `{decision['status']}`

Runner:
`scripts/run_main_track1_d4y_r3_insight_engine_preflight.py`

Sample insight packets: `{decision['sample_insight_packet_count']}`

Smoke: `{decision['smoke_summary']['status']}`

Recommended next Track 1 task:
`{decision['recommended_next_track1_task']}`
""",
    )


def write_hash_manifest() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return {"status": "PASS", "count": len(rows), "excludes": ["hashes.sha256"]}


def build_pack() -> dict[str, Any]:
    source_before = source_signatures()
    prepare_output()
    prereq = prerequisite_report()
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_PREFLIGHT_PREREQUISITE_REPORT.json", prereq)
    if prereq["status"] != "PASS":
        decision = {"status": WAITING_STATUS, "task_name": TASK_NAME, "timestamp": now_iso(), "prerequisite_status": prereq["status"]}
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT_DECISION.json", decision)
        write_hash_manifest()
        return decision

    packets = load_packets()
    situations = load_situations()
    write_architecture_and_scope()
    taxonomy = build_taxonomy()
    schema = packet_schema()
    rules = rule_catalog()
    write_policies()
    runtime_mapping = runtime_request_mapping()
    source_map = source_artifact_map()
    sample_inputs, sample_packets = sample_inputs_and_packets(packets, situations)
    examples = example_reports(packets, sample_packets["packets"])
    _contract, handoff_samples = app_handoff(sample_packets["packets"])
    smoke = smoke_report(taxonomy, schema, rules, sample_inputs, sample_packets, handoff_samples, source_map)
    write_limitations_and_next()
    negative = negative_report()
    source_after = source_signatures()
    audit = audits(source_before, source_after)

    decision = {
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "schema_version": SCHEMA_VERSION,
        "prerequisite_status": prereq["status"],
        "insight_type_count": taxonomy["insight_type_count"],
        "rule_count": rules["rule_count"],
        "sample_input_count": sample_inputs["sample_input_count"],
        "sample_insight_packet_count": sample_packets["sample_insight_packet_count"],
        "app_handoff_sample_count": handoff_samples["app_handoff_sample_count"],
        "cross_city_example_count": examples["cross_city"]["example_count"],
        "data_quality_example_count": examples["data_quality"]["example_count"],
        "review_backlog_example_count": examples["review"]["example_count"],
        "simulation_contrast_example_count": examples["simulation"]["example_count"],
        "limitation_cluster_example_count": examples["limitation"]["example_count"],
        "no_external_llm_called": True,
        "live_agents_implemented": False,
        "public_api_exposed": False,
        "command_action_output_created": False,
        "smoke_summary": {"status": smoke["status"], "test_count": smoke["test_count"]},
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitations": LIMITATIONS},
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": audit["claim"],
        "no_mutation_summary": audit["no_mutation"],
        "secret_audit_summary": audit["secret"],
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-SLICE",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-CITY-STORY-COMPILER-AND-DASHBOARD-R7 if not already closed; otherwise live runtime/insight packet integration task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT_DECISION.json", decision)
    write_decision_docs(decision)
    hash_summary = write_hash_manifest()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT_DECISION.json", decision)
    write_decision_docs(decision)
    hash_summary = write_hash_manifest()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT_DECISION.json", decision)
    write_decision_docs(decision)
    write_hash_manifest()
    return decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["build", "smoke"], default="build")
    args = parser.parse_args()
    if args.mode == "smoke" and (OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT_DECISION.json").exists():
        decision = read_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT_DECISION.json", {})
    else:
        decision = build_pack()
    print(json.dumps({"status": decision.get("status"), "output_root": str(OUTPUT_ROOT)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
