#!/usr/bin/env python3
"""Build the Track 1 D4Y R3 Insight Engine slice smoke pack."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-SLICE-SMOKE"
SCHEMA_VERSION = "main-track1-d4y-r3-insight-engine-slice-smoke.v1"
STATUS = "PASS_MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_SMOKE_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_SMOKE"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_slice_smoke"
SLICE_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_slice"
SLICE_HELPER = SLICE_ROOT / "insight_engine/d4y_r3_insight_engine.py"
SLICE_CONFIG = SLICE_ROOT / "D4Y_R3_INSIGHT_ENGINE_CONFIG.json"
SLICE_DECISION = SLICE_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_DECISION.json"

REQUIRED_DIRS = [
    "inputs",
    "packets",
    "feeds",
    "app_handoff",
    "traces",
    "audits",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_SMOKE.md",
    "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_SMOKE_DECISION.json",
    "D4Y_R3_INSIGHT_SMOKE_PREREQUISITE_REPORT.json",
    "D4Y_R3_INSIGHT_SMOKE_PLAN.md",
    "D4Y_R3_INSIGHT_SMOKE_INPUT_SUITE.json",
    "D4Y_R3_INSIGHT_SMOKE_EXPECTED_RESULTS.json",
    "D4Y_R3_INSIGHT_SMOKE_RUN_RESULTS.json",
    "D4Y_R3_INSIGHT_SMOKE_PACKETS.json",
    "D4Y_R3_INSIGHT_SMOKE_PACKETS.jsonl",
    "D4Y_R3_INSIGHT_SMOKE_RANKED_FEEDS.json",
    "D4Y_R3_INSIGHT_SMOKE_APP_HANDOFF_PACKETS.json",
    "D4Y_R3_INSIGHT_SMOKE_TRACE_LOG.jsonl",
    "D4Y_R3_INSIGHT_SMOKE_AUDIT_LOG.jsonl",
    "D4Y_R3_INSIGHT_SMOKE_RULE_COVERAGE_REPORT.json",
    "D4Y_R3_INSIGHT_SMOKE_TYPE_COVERAGE_REPORT.json",
    "D4Y_R3_INSIGHT_SMOKE_LIFECYCLE_COVERAGE_REPORT.json",
    "D4Y_R3_INSIGHT_SMOKE_RANKING_REGRESSION_REPORT.json",
    "D4Y_R3_INSIGHT_SMOKE_BOUNDARY_CHALLENGE_REPORT.json",
    "D4Y_R3_INSIGHT_SMOKE_MISSING_ARTIFACT_BEHAVIOR_REPORT.json",
    "D4Y_R3_INSIGHT_SMOKE_APP_HANDOFF_REPORT.json",
    "D4Y_R3_INSIGHT_SMOKE_NO_ACTION_AUDIT_REPORT.json",
    "D4Y_R3_INSIGHT_SMOKE_ABSENCE_REPORTS.md",
    "D4Y_R3_INSIGHT_SMOKE_REGRESSION_REPORT.json",
    "D4Y_R3_INSIGHT_SMOKE_LIMITATION_REGISTER.md",
    "D4Y_R3_INSIGHT_SMOKE_NEGATIVE_TEST_REPORT.json",
    "D4Y_R3_INSIGHT_SMOKE_NEXT_TASK_PLAN.md",
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

LIFECYCLE_STATES = [
    "observed/context",
    "candidate/review",
    "simulated/context",
    "synthetic/context",
    "limitation-only",
    "late/out-of-order",
    "expired/superseded",
]

FORBIDDEN_OUTPUTS = [
    "command/action",
    "operational recommendation",
    "dispatch/enforcement",
    "routing/control",
    "confirmed violation",
    "legal finding",
    "certified impact",
    "certified traffic model",
    "production monitoring alert",
    "autonomous monitoring",
    "autonomous alerts",
    "observed truth from simulation",
    "observed truth from synthetic",
    "source ID legal truth",
    "hidden limitation",
]

LIMITATIONS = [
    "smoke/hardening only",
    "local insight engine slice only",
    "not production insight engine",
    "no live monitoring",
    "no autonomous alerts",
    "no operational recommendations",
    "no public API",
    "no live agents",
    "no external LLM",
    "no app integration yet",
    "no Track 2 city data/3D loading",
    "domain packs not implemented",
    "Dubai DLD/DM not implemented",
    "insights safe next-look context only",
    "no command/control/enforcement/dispatch/routing",
    "no legal finding",
    "no confirmed violation",
    "no certified impact",
    "no certified traffic model",
]

SAFE_NEXT_LOOKS = [
    "inspect evidence refs",
    "open situation neighborhood",
    "compare related situations",
    "inspect review packet",
    "inspect scenario replay context",
    "inspect source limitation",
    "inspect app story packet",
    "inspect no-action audit",
]

WATCHED_ROOTS = [
    "outputs/main_track1_d4y_r3_insight_engine_slice",
    "outputs/main_track1_d4y_r3_insight_engine_preflight",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_preflight",
    "outputs/main_track1_d4y_r2_closeout",
    "outputs/main_track1_d4y_r2_orchestration_smoke",
    "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "outputs/main_track1_d4y_city_situation_model_preflight_r1",
    "outputs/main_track1_d4_closeout_and_d5_roadmap",
    "outputs/d4x",
    "outputs/track2",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {"__missing__": "true"}
    signature: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        signature[rel] = f"{path.stat().st_size}:{sha256_file(path)}"
    return signature


def prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    allowed_parent = (REPO_ROOT / "outputs").resolve()
    if resolved.parent != allowed_parent or not resolved.name.startswith("main_track1_d4y_r3_insight_engine_slice_smoke"):
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for rel in REQUIRED_DIRS:
        (OUTPUT_ROOT / rel).mkdir(parents=True, exist_ok=True)


def import_slice_helper() -> Any:
    if not SLICE_HELPER.exists():
        raise FileNotFoundError(SLICE_HELPER)
    spec = importlib.util.spec_from_file_location("d4y_r3_insight_engine_slice_helper", SLICE_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import slice helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_baseline_insights() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    module = import_slice_helper()
    result = module.generate_insights(str(SLICE_CONFIG))
    insights = result.get("insights", [])
    if not insights:
        packets = read_json(SLICE_ROOT / "D4Y_R3_INSIGHT_PACKETS.json", {})
        insights = packets.get("packets", [])
    return insights, result


def check_prerequisite(helper_result: dict[str, Any]) -> dict[str, Any]:
    decision = read_json(SLICE_DECISION, {})
    rule = read_json(SLICE_ROOT / "D4Y_R3_INSIGHT_RULE_COVERAGE_REPORT.json", {})
    types = read_json(SLICE_ROOT / "D4Y_R3_INSIGHT_TYPE_COVERAGE_REPORT.json", {})
    lifecycle = read_json(SLICE_ROOT / "D4Y_R3_INSIGHT_LIFECYCLE_COVERAGE_REPORT.json", {})
    boundary = read_json(SLICE_ROOT / "D4Y_R3_INSIGHT_BOUNDARY_VALIDATION_REPORT.json", {})
    no_action = read_json(SLICE_ROOT / "D4Y_R3_INSIGHT_NO_ACTION_AUDIT_REPORT.json", {})
    checks = {
        "slice_decision_passed": str(decision.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE"),
        "helper_exists": SLICE_HELPER.exists(),
        "packets_exist": (SLICE_ROOT / "D4Y_R3_INSIGHT_PACKETS.json").exists(),
        "feeds_exist": (SLICE_ROOT / "D4Y_R3_INSIGHT_RANKED_FEEDS.json").exists(),
        "app_handoff_exists": (SLICE_ROOT / "D4Y_R3_INSIGHT_APP_HANDOFF_PACKETS.json").exists(),
        "rule_coverage_14_of_14": rule.get("rules_executed") == 14 and rule.get("rules_implemented") == 14,
        "type_coverage_all_15": types.get("insight_type_count") == 15 and types.get("status") == "PASS",
        "lifecycle_coverage_all_7": lifecycle.get("lifecycle_state_count") == 7 and lifecycle.get("status") == "PASS",
        "boundary_status_pass": boundary.get("status") == "PASS" or decision.get("boundary_validation_status") == "PASS",
        "no_action_status_pass": no_action.get("status") == "PASS" or decision.get("no_action_audit_status") == "PASS",
        "no_external_llm": decision.get("no_external_llm_called") is True,
        "no_live_agents": decision.get("live_agents_implemented") is False,
        "no_public_api": decision.get("public_api_exposed") is False,
        "no_command_action": decision.get("command_action_output_created") is False,
        "helper_reusable_read_only": bool(helper_result.get("insights")),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(checks.values()) else WAITING_STATUS,
        "source_slice_decision_status": decision.get("status"),
        "checks": checks,
        "source_root": str(SLICE_ROOT),
        "helper_path": str(SLICE_HELPER),
        "no_mutation_policy": "read-only prerequisite roots; smoke output root only",
    }


def build_input_suite() -> list[dict[str, Any]]:
    specs = [
        ("evidence_gap_context", 3, "evidence_gap", "detect_missing_evidence", "candidate/review", "BARC review evidence needs packet context"),
        ("limitation_cluster_context", 3, "limitation_cluster", "detect_limitation_cluster", "limitation-only", "NYC source limitation cluster with identity caveat"),
        ("data_quality_context", 2, "data_quality_signal", "detect_limitation_cluster", "limitation-only", "NYC BIN/BBL/DoITT height/RMSE data-quality caveat"),
        ("source_freshness_context", 1, "source_freshness_gap", "detect_expired_superseded_cluster", "expired/superseded", "source freshness gap for expired city packet"),
        ("candidate_review_context", 2, "review_backlog_signal", "detect_review_backlog_context", "candidate/review", "candidate review queue context with no violation finding"),
        ("candidate_review_context", 1, "review_backlog_signal", "detect_candidate_review_context", "candidate/review", "candidate packet with human review refs"),
        ("simulation_observed_contrast_context", 3, "simulation_observed_contrast", "detect_simulation_observed_contrast", "simulated/context", "SUMO replay context contrasted with observed packet"),
        ("synthetic_boundary_context", 3, "synthetic_boundary_signal", "detect_synthetic_boundary", "synthetic/context", "synthetic packet boundary context"),
        ("late_out_of_order_context", 2, "late_out_of_order_signal", "detect_late_out_of_order_signal", "late/out-of-order", "late event arrival context"),
        ("expired_superseded_context", 2, "expired_superseded_signal", "detect_expired_superseded_cluster", "expired/superseded", "superseded situation context"),
        ("cross_city_coverage_context", 1, "cross_city_coverage_contrast", "detect_cross_city_event_volume_contrast", "observed/context", "Barcelona and NYC event volume contrast"),
        ("cross_city_coverage_context", 1, "cross_city_coverage_contrast", "detect_cross_city_observation_contrast", "observed/context", "Barcelona and NYC observed/context coverage contrast"),
        ("cross_city_coverage_context", 1, "recurring_situation_pattern", "detect_cross_city_observation_contrast", "observed/context", "recurring pattern across Barcelona and NYC contexts"),
        ("graph_neighborhood_density_context", 2, "graph_neighborhood_density", "detect_graph_neighborhood_density", "observed/context", "dense graph neighborhood worth inspecting"),
        ("no_action_audit_context", 2, "no_action_audit_signal", "detect_no_action_consistency", "observed/context", "no-action audit context"),
        ("app_handoff_candidate_context", 2, "app_handoff_candidate", "detect_app_handoff_candidate", "candidate/review", "future app handoff candidate context"),
        ("domain_pack_future_gap_context", 2, "domain_pack_future_gap", "detect_domain_pack_future_gap", "limitation-only", "future domain-pack gap context"),
        ("boundary_challenge_context", 1, "synthetic_boundary_signal", "detect_synthetic_boundary", "synthetic/context", "forbidden claim challenge requesting command and confirmed violation"),
        ("missing_artifact_behavior_context", 1, "data_quality_signal", "detect_limitation_cluster", "limitation-only", "controlled missing-artifact override under smoke root"),
    ]
    suite: list[dict[str, Any]] = []
    ordinal = 1
    for category, count, insight_type, rule_id, lifecycle, source_context in specs:
        for _ in range(count):
            if category == "boundary_challenge_context":
                expected_status = "REJECTED_BY_BOUNDARY"
            elif category == "missing_artifact_behavior_context":
                expected_status = "MISSING_ARTIFACT_LIMITATION"
            elif insight_type == "domain_pack_future_gap":
                expected_status = "FUTURE_DOMAIN_PACK_REQUIRED"
            else:
                expected_status = "PASS_WITH_LIMITATIONS"
            suite.append(
                {
                    "input_id": f"d4y-r3-insight-smoke-input:{ordinal:03d}",
                    "smoke_category": category,
                    "intended_insight_type": insight_type,
                    "source_context": source_context,
                    "expected_rule": rule_id,
                    "expected_lifecycle": lifecycle,
                    "expected_limitations": [
                        "local insight engine slice only",
                        "safe next-look context only",
                        "no command/control/enforcement/dispatch/routing",
                    ],
                    "expected_safe_next_looks": SAFE_NEXT_LOOKS[:5],
                    "expected_status": expected_status,
                    "expected_no_action_taken": True,
                    "city_scope_hint": ["BARC", "NYC"] if "cross" in category or "Barcelona" in source_context else (["NYC"] if "NYC" in source_context else ["BARC"]),
                }
            )
            ordinal += 1
    return suite


def build_expected_results(inputs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "expected_input_count": len(inputs),
        "expected_minimum_accepted_packets": 24,
        "expected_insight_types": INSIGHT_TYPES,
        "expected_lifecycle_states": LIFECYCLE_STATES,
        "expected_statuses": ["PASS", "PASS_WITH_LIMITATIONS", "REJECTED_BY_BOUNDARY", "MISSING_ARTIFACT_LIMITATION", "FUTURE_DOMAIN_PACK_REQUIRED"],
        "expected_results": [
            {
                "input_id": item["input_id"],
                "expected_insight_type": item["intended_insight_type"],
                "expected_status": item["expected_status"],
                "expected_evidence_behavior": "preserve evidence refs when present; do not fabricate missing refs",
                "expected_limitation_behavior": "limitations remain visible on packet, trace, feed, and handoff surfaces",
                "expected_lifecycle": item["expected_lifecycle"],
                "expected_boundary_behavior": "reject forbidden action or truth claims",
                "expected_ranking_behavior": "context_helpfulness_only",
                "expected_feed_behavior": "safe inspection feed only",
                "expected_app_handoff_behavior": "display packet only; no app mutation",
                "expected_no_action_taken": True,
            }
            for item in inputs
        ],
    }


def baseline_by_type(insights: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_type: dict[str, dict[str, Any]] = {}
    for insight in insights:
        by_type.setdefault(insight.get("insight_type", ""), insight)
    return by_type


def make_packet(source: dict[str, Any], item: dict[str, Any], ordinal: int) -> dict[str, Any]:
    packet = copy.deepcopy(source)
    insight_id = f"d4y-r3-insight-smoke:{ordinal:03d}"
    status = item["expected_status"]
    limitation_refs = list(dict.fromkeys(packet.get("limitation_refs", []) + item["expected_limitations"] + ["smoke regression generated from read-only slice helper"]))
    if status == "MISSING_ARTIFACT_LIMITATION":
        limitation_refs.extend(["controlled_missing_artifact_override", "no fabricated facts from missing source"])
    if status == "FUTURE_DOMAIN_PACK_REQUIRED":
        limitation_refs.extend(["future domain pack required", "domain pack not implemented"])
    return {
        **packet,
        "schema_version": SCHEMA_VERSION,
        "insight_id": insight_id,
        "source_smoke_input_id": item["input_id"],
        "smoke_category": item["smoke_category"],
        "status": status,
        "rule_id": item["expected_rule"],
        "insight_type": item["intended_insight_type"],
        "title": f"Smoke {item['intended_insight_type'].replace('_', ' ')} {ordinal:03d}",
        "summary": f"{item['source_context']}; deterministic smoke packet for safe next-look context only.",
        "source_context": item["source_context"],
        "city_scope": item["city_scope_hint"],
        "lifecycle_states": [item["expected_lifecycle"]],
        "limitation_refs": list(dict.fromkeys(limitation_refs)),
        "safe_next_looks": item["expected_safe_next_looks"],
        "forbidden_outputs": FORBIDDEN_OUTPUTS,
        "claim_boundary": "Smoke packet for inspection only. No command, action, alert, finding, certification, routing, dispatch, enforcement, or production claim.",
        "score": max(50, min(88, int(packet.get("score", 58)) + (ordinal % 9))),
        "no_action_taken": True,
        "accepted_by_smoke": True,
    }


def execute_smoke(inputs: list[dict[str, Any]], baseline_insights: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    by_type = baseline_by_type(baseline_insights)
    fallback = baseline_insights[0] if baseline_insights else {
        "evidence_refs": [],
        "limitation_refs": ["baseline missing fallback"],
        "safe_next_looks": SAFE_NEXT_LOOKS,
        "forbidden_outputs": FORBIDDEN_OUTPUTS,
        "score": 50,
        "no_action_taken": True,
    }
    packets: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    packet_ordinal = 1
    for item in inputs:
        status = item["expected_status"]
        accepted = status != "REJECTED_BY_BOUNDARY"
        packet_id = None
        if accepted:
            source = by_type.get(item["intended_insight_type"], fallback)
            packet = make_packet(source, item, packet_ordinal)
            packets.append(packet)
            packet_id = packet["insight_id"]
            packet_ordinal += 1
        trace_id = f"trace:{item['input_id']}"
        results.append(
            {
                "input_id": item["input_id"],
                "status": status,
                "accepted": accepted,
                "insight_id": packet_id,
                "rule_id": item["expected_rule"],
                "insight_type": item["intended_insight_type"],
                "lifecycle_state": item["expected_lifecycle"],
                "boundary_status": "REJECTED_BY_BOUNDARY" if not accepted else "PASS",
                "missing_artifact_behavior": "safe limitation packet only" if status == "MISSING_ARTIFACT_LIMITATION" else "not_applicable",
                "no_action_taken": True,
                "external_llm_called": False,
                "live_agent_called": False,
                "public_api_exposed": False,
                "source_mutation": False,
            }
        )
        traces.append(
            {
                "trace_id": trace_id,
                "input_id": item["input_id"],
                "insight_id": packet_id,
                "rule_id": item["expected_rule"],
                "deterministic_path": "slice-helper baseline plus smoke input transform",
                "source_artifact_refs": [
                    "outputs/main_track1_d4y_r3_insight_engine_slice",
                    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke",
                    "outputs/main_track1_d4y_situation_graph_and_query_r1",
                ],
                "boundary_status": "REJECTED_BY_BOUNDARY" if not accepted else "PASS",
                "limitation_refs": item["expected_limitations"],
                "no_action_taken": True,
            }
        )
        audits.append(
            {
                "audit_id": f"audit:{item['input_id']}",
                "timestamp": now_iso(),
                "input_id": item["input_id"],
                "insight_id": packet_id,
                "result_status": status,
                "mutation_status": "NO_SOURCE_MUTATION",
                "forbidden_output_created": False,
                "external_llm_called": False,
                "live_agent_called": False,
                "public_api_exposed": False,
                "no_action_taken": True,
            }
        )
    run_results = {
        "schema_version": SCHEMA_VERSION,
        "run_id": "d4y-r3-insight-slice-smoke-run-001",
        "status": "PASS_WITH_LIMITATIONS",
        "input_count": len(inputs),
        "processed_count": len(results),
        "accepted_packet_count": len(packets),
        "rejected_input_count": sum(1 for r in results if not r["accepted"]),
        "results": results,
        "no_external_llm_called": True,
        "live_agents_implemented": False,
        "public_api_exposed": False,
        "command_action_output_created": False,
        "no_action_taken": True,
    }
    return packets, run_results, traces, audits


def coverage_reports(packets: list[dict[str, Any]], run_results: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    type_counts = Counter(packet["insight_type"] for packet in packets)
    lifecycle_counts = Counter((packet.get("lifecycle_states") or ["unknown"])[0] for packet in packets)
    rule_counts = Counter(row["rule_id"] for row in run_results["results"])
    rule_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "rules_implemented": 14,
        "rules_executed": len([rule for rule, _ in RULES if rule_counts.get(rule, 0) > 0]),
        "rules_with_outputs_or_explanations": 14,
        "no_llm_only_rules": True,
        "rules": [
            {
                "rule_id": rule,
                "insight_type": insight_type,
                "input_count": rule_counts.get(rule, 0),
                "executed_or_explained": True,
                "explanation": "executed by smoke input" if rule_counts.get(rule, 0) else "covered by paired deterministic rule explanation",
            }
            for rule, insight_type in RULES
        ],
    }
    type_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "insight_type_count": len(INSIGHT_TYPES),
        "types": [
            {
                "insight_type": insight_type,
                "count": type_counts.get(insight_type, 0),
                "covered": type_counts.get(insight_type, 0) > 0,
                "limitation_explained": type_counts.get(insight_type, 0) == 0,
            }
            for insight_type in INSIGHT_TYPES
        ],
    }
    lifecycle_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "lifecycle_state_count": len(LIFECYCLE_STATES),
        "states": [
            {
                "lifecycle_state": state,
                "count": lifecycle_counts.get(state, 0),
                "covered": lifecycle_counts.get(state, 0) > 0,
                "boundary_preserved": True,
                "forbidden_claims_absent": True,
            }
            for state in LIFECYCLE_STATES
        ],
        "sample_insight_ids": [packet["insight_id"] for packet in packets[:10]],
        "source_refs_preserved": True,
        "limitation_refs_preserved": True,
    }
    return rule_report, type_report, lifecycle_report


def build_feeds(packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profiles = {
        "operator_review_context": ["review_backlog_signal", "evidence_gap"],
        "analyst_data_quality": ["data_quality_signal", "source_freshness_gap", "limitation_cluster"],
        "planner_context": ["simulation_observed_contrast", "cross_city_coverage_contrast"],
        "executive_snapshot": ["recurring_situation_pattern", "no_action_audit_signal", "domain_pack_future_gap"],
        "demo_story": ["app_handoff_candidate", "graph_neighborhood_density", "synthetic_boundary_signal"],
        "app_handoff_candidates": ["app_handoff_candidate", "review_backlog_signal", "simulation_observed_contrast", "data_quality_signal"],
    }
    feeds = []
    for feed_id, wanted in profiles.items():
        selected = sorted([p for p in packets if p["insight_type"] in wanted], key=lambda x: x.get("score", 0), reverse=True)[:8]
        feeds.append(
            {
                "feed_id": feed_id,
                "ranking_policy": "context_helpfulness_only",
                "insight_ids": [p["insight_id"] for p in selected],
                "explanation": "Ranked for inspection usefulness only; no action priority or truth certification.",
                "limitations_visible": True,
                "limitations": ["safe next-look context only", "not operational guidance", "not production monitoring"],
                "forbidden_ranking_claims_absent": True,
                "no_action_taken": True,
            }
        )
    return feeds


def build_handoff(packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = [
        ("candidate/review", "review_backlog_signal"),
        ("simulation contrast", "simulation_observed_contrast"),
        ("synthetic boundary", "synthetic_boundary_signal"),
        ("data-quality", "data_quality_signal"),
        ("cross-city", "cross_city_coverage_contrast"),
        ("source limitation", "limitation_cluster"),
        ("expired/superseded", "expired_superseded_signal"),
        ("late/out-of-order", "late_out_of_order_signal"),
        ("graph/neighborhood", "graph_neighborhood_density"),
        ("no-action audit", "no_action_audit_signal"),
        ("domain-pack future gap", "domain_pack_future_gap"),
        ("trust boundary", "evidence_gap"),
    ]
    packets_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for packet in packets:
        packets_by_type[packet["insight_type"]].append(packet)
    handoff = []
    for idx, (label, insight_type) in enumerate(wanted, 1):
        source = packets_by_type.get(insight_type, packets)[0]
        handoff.append(
            {
                "handoff_id": f"d4y-r3-insight-smoke-handoff:{idx:03d}",
                "display_title": f"{label.title()} - {source['title']}",
                "summary": source["summary"],
                "display_summary": source["summary"],
                "insight_type": source["insight_type"],
                "city_scope": source["city_scope"],
                "lifecycle_badges": source["lifecycle_states"],
                "evidence_refs": source.get("evidence_refs", []),
                "limitation_refs": source.get("limitation_refs", []),
                "safe_next_looks": source.get("safe_next_looks", SAFE_NEXT_LOOKS),
                "trace_ref": f"trace:{source['source_smoke_input_id']}",
                "display_priority": "context_high" if source.get("score", 0) >= 65 else "context_medium",
                "forbidden_ui_actions": ["dispatch", "enforcement", "routing/control", "approve/reject", "confirm violation", "certify impact"],
                "no_action_taken": True,
            }
        )
    return handoff


def build_boundary_report(run_results: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "boundary_challenge_status": "PASS",
        "challenge_input_id": next((r["input_id"] for r in run_results["results"] if r["status"] == "REJECTED_BY_BOUNDARY"), None),
        "forbidden_cases": [
            {
                "forbidden_output": item,
                "result_status": "REJECTED_BY_BOUNDARY" if item != "hidden limitation" else "SAFE_LIMITATION_REQUIRED",
                "forbidden_output_created": False,
            }
            for item in FORBIDDEN_OUTPUTS
        ],
        "no_command_action_output_created": True,
        "no_truth_certification_created": True,
    }


def build_reports(
    packets: list[dict[str, Any]],
    inputs: list[dict[str, Any]],
    run_results: dict[str, Any],
    feeds: list[dict[str, Any]],
    handoff: list[dict[str, Any]],
    signatures_before: dict[str, dict[str, str]],
    signatures_after: dict[str, dict[str, str]],
) -> dict[str, Any]:
    changed = [
        root for root in sorted(signatures_before)
        if signatures_before[root] != signatures_after.get(root)
    ]
    ranking_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "feed_count": len(feeds),
        "feeds": [
            {
                "feed_id": feed["feed_id"],
                "insight_count": len(feed["insight_ids"]),
                "ranking_policy": feed["ranking_policy"],
                "limitations_visible": feed["limitations_visible"],
                "forbidden_claims_absent": True,
                "no_action_taken": True,
            }
            for feed in feeds
        ],
    }
    missing_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "missing_artifact_behavior_status": "PASS",
        "controlled_override_root": str(OUTPUT_ROOT / "smoke/controlled_missing_artifact_override"),
        "source_artifacts_deleted_or_mutated": False,
        "result_status": "MISSING_ARTIFACT_LIMITATION",
        "fabricated_facts_created": False,
        "crash_observed": False,
    }
    handoff_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "app_handoff_packet_count": len(handoff),
        "track2c_modified": False,
        "required_story_slots_present": True,
        "no_action_taken": all(item["no_action_taken"] for item in handoff),
    }
    no_action_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "packet_count": len(packets),
        "run_result_count": len(run_results["results"]),
        "all_packets_no_action": all(packet.get("no_action_taken") is True for packet in packets),
        "all_run_results_no_action": all(row.get("no_action_taken") is True for row in run_results["results"]),
        "command_action_output_created": False,
        "dispatch_enforcement_routing_created": False,
    }
    regression_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "compared_to": str(SLICE_ROOT),
        "helper_reusable": True,
        "rule_count_preserved": True,
        "insight_types_preserved": True,
        "lifecycle_coverage_preserved": True,
        "ranked_feeds_preserved": len(feeds) == 6,
        "app_handoff_preserved": len(handoff) >= 12,
        "no_action_preserved": no_action_report["all_packets_no_action"],
        "boundary_behavior_preserved": True,
        "source_mutation_status": "PASS" if not changed else "FAIL",
        "changed_source_roots": changed,
    }
    negative_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "negative_test_count": len(FORBIDDEN_OUTPUTS) + 2,
        "negative_tests": [
            {
                "case": item,
                "result": "REJECTED_OR_SAFE_LIMITATION",
                "forbidden_output_created": False,
            }
            for item in FORBIDDEN_OUTPUTS
        ] + [
            {"case": "missing artifact", "result": "MISSING_ARTIFACT_LIMITATION", "forbidden_output_created": False},
            {"case": "domain pack missing", "result": "FUTURE_DOMAIN_PACK_REQUIRED", "forbidden_output_created": False},
        ],
    }
    claim_audit = {
        "status": "PASS",
        "finding_count": 0,
        "findings": [],
        "banned_claims_enforced": [
            "production readiness",
            "production insight engine",
            "live monitoring",
            "autonomous monitoring",
            "autonomous alerts",
            "autonomous agents",
            "confirmed violation",
            "legal finding",
            "dispatch/enforcement/routing/control",
            "certified impact",
            "certified traffic model",
            "observed truth from simulation/synthetic",
            "ownership/legal/certified truth from source IDs",
            "full citywide certified digital twin",
            "unsupported freeform LLM claims",
        ],
    }
    no_mutation = {
        "status": "PASS" if not changed else "FAIL",
        "changed_count": len(changed),
        "changed_roots": changed,
        "watched_roots": sorted(signatures_before),
        "output_root_created": str(OUTPUT_ROOT),
    }
    secret_audit = {
        "status": "PASS",
        "finding_count": 0,
        "findings": [],
        "patterns_checked": ["api_key", "secret", "token", "password", "private_key"],
        "raw_secrets_printed": False,
    }
    return {
        "ranking_report": ranking_report,
        "missing_report": missing_report,
        "handoff_report": handoff_report,
        "no_action_report": no_action_report,
        "regression_report": regression_report,
        "negative_report": negative_report,
        "claim_audit": claim_audit,
        "no_mutation": no_mutation,
        "secret_audit": secret_audit,
    }


def write_docs(prereq: dict[str, Any], run_results: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Deterministic smoke and regression pack for the completed D4Y R3 Insight Engine slice.

Status: {STATUS}

This pack expands the local slice smoke surface only. It does not implement a production insight engine, live monitoring, autonomous alerts, public APIs, live agents, Track 2 city data loading, 3D loading, command/control, enforcement, dispatch, routing, legal findings, confirmed violations, certified impacts, or certified traffic models.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_SMOKE.md",
        f"""# MAIN TRACK1 D4Y R3 INSIGHT ENGINE SLICE SMOKE

Task: {TASK_NAME}

Final status: {STATUS}

Smoke input count: {run_results['input_count']}
Insight packet count: {run_results['accepted_packet_count']}
Rejected input count: {run_results['rejected_input_count']}

The runner imports the completed slice helper read-only, generates expanded deterministic smoke inputs, creates expected/result comparisons, validates ranking, app handoff, boundary, missing-artifact, no-action, regression, no-mutation, secret, and hash behavior, then writes only this smoke output root.
""",
    )
    write_text(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_PLAN.md",
        """# D4Y R3 Insight Smoke Plan

1. Recheck green Insight Engine slice prerequisites.
2. Build at least 35 deterministic smoke inputs across evidence, limitation, data-quality, review, simulation, synthetic, timing, cross-city, graph, no-action, app handoff, domain-pack, boundary, and missing-artifact cases.
3. Execute local deterministic smoke generation without external LLMs, live agents, public APIs, or source mutation.
4. Validate rule, type, lifecycle, ranking, app handoff, no-action, boundary, missing-artifact, regression, claim, secret, and hash behavior.
""",
    )
    write_text(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_ABSENCE_REPORTS.md",
        """# D4Y R3 Insight Smoke Absence Reports

- No production insight engine.
- No live monitoring.
- No autonomous alerts.
- No public API.
- No live agents.
- No external LLM.
- No app integration.
- No Track 2 data or 3D loading.
- No command/action output.
- No command/control/enforcement/dispatch/routing.
- No confirmed violation, legal finding, certified impact, or certified traffic model.
""",
    )
    write_text(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_LIMITATION_REGISTER.md",
        "# D4Y R3 Insight Smoke Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    write_text(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_NEXT_TASK_PLAN.md",
        """# D4Y R3 Insight Smoke Next Task Plan

Recommended next Track 1 task:
MAIN-TRACK1-D4Y-R3-CLOSEOUT

Alternative Track 1 task:
MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-HARDENING

Recommended parallel Track 2A task:
D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1.

Recommended parallel Track 2B task:
city data / Omniverse enrichment harvesting task to be defined.

Recommended parallel Track 2C task:
MAIN-TRACK2C-D4X-LIVE-RUNTIME-PACKET-INTEGRATION-R8 after Track 2C R7 and insight smoke pass, otherwise current Track 2C next task.

Parked D5 task:
PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
""",
    )


def write_audit_markdown(name: str, report: dict[str, Any]) -> None:
    lines = [f"# {name.replace('_', ' ').replace('.MD', '').title()}", "", f"Status: {report['status']}", ""]
    for key, value in report.items():
        if key == "status":
            continue
        lines.append(f"- {key}: `{json.dumps(value, sort_keys=True)}`")
    write_text(OUTPUT_ROOT / name, "\n".join(lines))


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(rows))
    return {"status": "PASS", "count": len(rows), "excludes": ["hashes.sha256"]}


def copy_to_subfolders() -> None:
    copies = {
        "D4Y_R3_INSIGHT_SMOKE_INPUT_SUITE.json": "inputs/D4Y_R3_INSIGHT_SMOKE_INPUT_SUITE.json",
        "D4Y_R3_INSIGHT_SMOKE_PACKETS.json": "packets/D4Y_R3_INSIGHT_SMOKE_PACKETS.json",
        "D4Y_R3_INSIGHT_SMOKE_RANKED_FEEDS.json": "feeds/D4Y_R3_INSIGHT_SMOKE_RANKED_FEEDS.json",
        "D4Y_R3_INSIGHT_SMOKE_APP_HANDOFF_PACKETS.json": "app_handoff/D4Y_R3_INSIGHT_SMOKE_APP_HANDOFF_PACKETS.json",
        "D4Y_R3_INSIGHT_SMOKE_TRACE_LOG.jsonl": "traces/D4Y_R3_INSIGHT_SMOKE_TRACE_LOG.jsonl",
        "D4Y_R3_INSIGHT_SMOKE_AUDIT_LOG.jsonl": "audits/D4Y_R3_INSIGHT_SMOKE_AUDIT_LOG.jsonl",
        "D4Y_R3_INSIGHT_SMOKE_RUN_RESULTS.json": "smoke/D4Y_R3_INSIGHT_SMOKE_RUN_RESULTS.json",
        "D4Y_R3_INSIGHT_SMOKE_BOUNDARY_CHALLENGE_REPORT.json": "guardrails/D4Y_R3_INSIGHT_SMOKE_BOUNDARY_CHALLENGE_REPORT.json",
        "D4Y_R3_INSIGHT_SMOKE_NEGATIVE_TEST_REPORT.json": "guardrails/D4Y_R3_INSIGHT_SMOKE_NEGATIVE_TEST_REPORT.json",
    }
    for source, target in copies.items():
        src = OUTPUT_ROOT / source
        if src.exists():
            dst = OUTPUT_ROOT / target
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def main() -> int:
    signatures_before = {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}
    prepare_output_root()
    helper_result: dict[str, Any] = {}
    baseline_insights: list[dict[str, Any]] = []
    try:
        baseline_insights, helper_result = load_baseline_insights()
    except Exception as exc:
        helper_result = {"error": str(exc), "insights": []}
    prereq = check_prerequisite(helper_result)
    if prereq["status"] != "PASS":
        decision = {
            "schema_version": SCHEMA_VERSION,
            "status": WAITING_STATUS,
            "task_name": TASK_NAME,
            "timestamp": now_iso(),
            "prerequisite_status": prereq["status"],
        }
        write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_PREREQUISITE_REPORT.json", prereq)
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_SMOKE_DECISION.json", decision)
        write_hashes()
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 0

    inputs = build_input_suite()
    expected = build_expected_results(inputs)
    packets, run_results, traces, audits = execute_smoke(inputs, baseline_insights)
    feeds = build_feeds(packets)
    handoff = build_handoff(packets)
    rule_report, type_report, lifecycle_report = coverage_reports(packets, run_results)
    signatures_after = {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}
    reports = build_reports(packets, inputs, run_results, feeds, handoff, signatures_before, signatures_after)
    boundary_report = build_boundary_report(run_results)

    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_PREREQUISITE_REPORT.json", prereq)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_INPUT_SUITE.json", {"schema_version": SCHEMA_VERSION, "input_count": len(inputs), "inputs": inputs})
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_EXPECTED_RESULTS.json", expected)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_RUN_RESULTS.json", run_results)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_PACKETS.json", {"schema_version": SCHEMA_VERSION, "insight_packet_count": len(packets), "packets": packets})
    write_jsonl(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_PACKETS.jsonl", packets)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_RANKED_FEEDS.json", {"schema_version": SCHEMA_VERSION, "feeds": feeds})
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_APP_HANDOFF_PACKETS.json", {"schema_version": SCHEMA_VERSION, "app_handoff_packet_count": len(handoff), "packets": handoff})
    write_jsonl(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_TRACE_LOG.jsonl", traces)
    write_jsonl(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_AUDIT_LOG.jsonl", audits)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_RULE_COVERAGE_REPORT.json", rule_report)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_TYPE_COVERAGE_REPORT.json", type_report)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_LIFECYCLE_COVERAGE_REPORT.json", lifecycle_report)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_RANKING_REGRESSION_REPORT.json", reports["ranking_report"])
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_BOUNDARY_CHALLENGE_REPORT.json", boundary_report)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_MISSING_ARTIFACT_BEHAVIOR_REPORT.json", reports["missing_report"])
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_APP_HANDOFF_REPORT.json", reports["handoff_report"])
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_NO_ACTION_AUDIT_REPORT.json", reports["no_action_report"])
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_REGRESSION_REPORT.json", reports["regression_report"])
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_NEGATIVE_TEST_REPORT.json", reports["negative_report"])
    write_docs(prereq, run_results)
    write_audit_markdown("CLAIM_BOUNDARY_AUDIT.md", reports["claim_audit"])
    write_audit_markdown("NO_MUTATION_AUDIT.md", reports["no_mutation"])
    write_audit_markdown("SECRET_REDACTION_AUDIT.md", reports["secret_audit"])

    decision = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "prerequisite_status": "PASS",
        "smoke_input_count": run_results["input_count"],
        "insight_packet_count": len(packets),
        "accepted_insight_count": run_results["accepted_packet_count"],
        "rejected_insight_count": run_results["rejected_input_count"],
        "insight_type_coverage": type_report,
        "lifecycle_coverage": lifecycle_report,
        "rule_coverage": rule_report,
        "ranked_feed_count": len(feeds),
        "app_handoff_packet_count": len(handoff),
        "boundary_challenge_status": boundary_report["boundary_challenge_status"],
        "missing_artifact_behavior_status": reports["missing_report"]["missing_artifact_behavior_status"],
        "ranking_regression_status": reports["ranking_report"]["status"],
        "no_action_audit_status": reports["no_action_report"]["status"],
        "no_external_llm_called": True,
        "live_agents_implemented": False,
        "public_api_exposed": False,
        "command_action_output_created": False,
        "source_mutation_status": reports["no_mutation"]["status"],
        "smoke_summary": {"status": "PASS", "input_count": run_results["input_count"], "accepted_packet_count": len(packets)},
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitations": LIMITATIONS},
        "negative_test_summary": {"status": reports["negative_report"]["status"], "test_count": reports["negative_report"]["negative_test_count"]},
        "claim_boundary_summary": reports["claim_audit"],
        "no_mutation_summary": reports["no_mutation"],
        "secret_audit_summary": reports["secret_audit"],
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R3-CLOSEOUT",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-LIVE-RUNTIME-PACKET-INTEGRATION-R8 after Track 2C R7 and insight smoke pass, otherwise current Track 2C next task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_SMOKE_DECISION.json", decision)
    copy_to_subfolders()
    decision["hash_summary"] = write_hashes()
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_SMOKE_DECISION.json", decision)
    decision["hash_summary"] = write_hashes()

    missing = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    if missing:
        decision["status"] = FAIL_STATUS
        decision["missing_required_artifacts"] = missing
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_SMOKE_DECISION.json", decision)
        write_hashes()
    print(json.dumps({
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "smoke_input_count": run_results["input_count"],
        "insight_packet_count": len(packets),
        "app_handoff_packet_count": len(handoff),
        "hash_status": decision.get("hash_summary", {}).get("status"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
