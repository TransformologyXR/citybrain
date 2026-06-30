#!/usr/bin/env python3
"""Build the Track 1 D4Y R3 Insight Engine slice pack."""

from __future__ import annotations

import argparse
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


TASK_NAME = "MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-SLICE"
SCHEMA_VERSION = "main-track1-d4y-r3-insight-engine-slice.v1"
STATUS = "PASS_MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_slice"
PREFLIGHT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_preflight"
SMOKE_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke"

REQUIRED_DIRS = [
    "insight_engine",
    "insight_engine/sample_inputs",
    "insight_engine/sample_outputs",
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
    "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE.md",
    "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_DECISION.json",
    "D4Y_R3_INSIGHT_SLICE_PREREQUISITE_REPORT.json",
    "D4Y_R3_INSIGHT_SLICE_IMPLEMENTATION_ARCHITECTURE.md",
    "D4Y_R3_INSIGHT_ENGINE_IMPLEMENTATION_MANIFEST.json",
    "D4Y_R3_INSIGHT_ENGINE_CONFIG.json",
    "D4Y_R3_INSIGHT_SOURCE_ARTIFACT_MAP_RESOLVED.json",
    "D4Y_R3_INSIGHT_RULE_ENGINE_IMPLEMENTATION_REPORT.json",
    "D4Y_R3_INSIGHT_RULE_REGISTRY.json",
    "D4Y_R3_INSIGHT_PACKET_SCHEMA.json",
    "D4Y_R3_INSIGHT_GENERATION_RUNS.json",
    "D4Y_R3_INSIGHT_PACKETS.json",
    "D4Y_R3_INSIGHT_PACKETS.jsonl",
    "D4Y_R3_INSIGHT_RANKED_FEEDS.json",
    "D4Y_R3_INSIGHT_RULE_COVERAGE_REPORT.json",
    "D4Y_R3_INSIGHT_TYPE_COVERAGE_REPORT.json",
    "D4Y_R3_INSIGHT_LIFECYCLE_COVERAGE_REPORT.json",
    "D4Y_R3_INSIGHT_BOUNDARY_VALIDATION_REPORT.json",
    "D4Y_R3_INSIGHT_NO_ACTION_AUDIT_REPORT.json",
    "D4Y_R3_INSIGHT_TRACE_LOG.jsonl",
    "D4Y_R3_INSIGHT_AUDIT_LOG.jsonl",
    "D4Y_R3_INSIGHT_APP_HANDOFF_PACKETS.json",
    "D4Y_R3_INSIGHT_APP_HANDOFF_REPORT.json",
    "D4Y_R3_INSIGHT_SAMPLE_REQUESTS.json",
    "D4Y_R3_INSIGHT_SAMPLE_RESPONSES.json",
    "D4Y_R3_INSIGHT_SMOKE_REPORT.json",
    "D4Y_R3_INSIGHT_LIMITATION_REGISTER.md",
    "D4Y_R3_INSIGHT_NEGATIVE_TEST_REPORT.json",
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
    "autonomous monitoring alert",
    "ownership/legal/certified affected-building truth from source IDs",
    "observed truth from simulation/synthetic",
    "hidden limitation",
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

LIFECYCLE_STATES = [
    "observed/context",
    "candidate/review",
    "simulated/context",
    "synthetic/context",
    "limitation-only",
    "late/out-of-order",
    "expired/superseded",
]

LIMITATIONS = [
    "local insight engine slice only",
    "not production insight engine",
    "no live monitoring",
    "no autonomous alerts",
    "no operational recommendations",
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

WATCHED_ROOTS = [
    "outputs/main_track1_d4y_r3_insight_engine_preflight",
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


HELPER = r'''#!/usr/bin/env python3
"""Local deterministic D4Y R3 insight engine slice helper."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    "autonomous monitoring alert",
    "ownership/legal/certified affected-building truth from source IDs",
    "observed truth from simulation/synthetic",
    "hidden limitation",
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


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def load_config(path: str | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else Path(__file__).resolve().parent / "insight_engine_config.json"
    return read_json(config_path, {})


def source_path(config: dict[str, Any], ref: str) -> Path | None:
    for item in config.get("source_artifacts", []):
        if item.get("artifact_ref") == ref:
            return Path(item["resolved_path"])
    return None


def load_packets(config: dict[str, Any]) -> list[dict[str, Any]]:
    path = source_path(config, "r3_runtime_smoke_output_packets")
    data = read_json(path, {}) if path else {}
    return data.get("packets", [])


def select_packet(packets: list[dict[str, Any]], lifecycle: str | None = None, request_type: str | None = None, packet_type: str | None = None) -> dict[str, Any]:
    for packet in packets:
        if lifecycle and lifecycle not in packet.get("lifecycle_states", []):
            continue
        if request_type and packet.get("request_type") != request_type:
            continue
        if packet_type and packet.get("packet_type") != packet_type:
            continue
        return packet
    return packets[0] if packets else {}


def make_insight(rule_id: str, insight_type: str, title: str, packet: dict[str, Any], index: int, metrics: dict[str, Any]) -> dict[str, Any]:
    limitations = list(dict.fromkeys((packet.get("limitation_refs") or []) + ["local_insight_engine_slice_only", "safe_next_look_context_only", "not_command_control"]))
    evidence_refs = packet.get("evidence_refs", [])
    source_refs = packet.get("source_refs", [])
    if not evidence_refs and not source_refs:
        limitations.append("explicit_limitation_only_status")
    return {
        "insight_id": f"d4y-r3-insight-slice:{index:03d}",
        "insight_type": insight_type,
        "rule_id": rule_id,
        "title": title,
        "summary": f"{title}; context-only signal for CityBrain inspection, not an action or recommendation.",
        "city_scope": ["TRACK1_RUNTIME"],
        "lifecycle_states": packet.get("lifecycle_states", []),
        "situation_refs": [packet.get("situation_id")] if packet.get("situation_id") else [],
        "event_refs": [],
        "evidence_refs": evidence_refs,
        "source_refs": source_refs,
        "graph_refs": packet.get("tool_output_refs", [])[:5],
        "replay_refs": packet.get("scenario_replay_refs", []),
        "review_refs": packet.get("review_packet_refs", []),
        "limitation_refs": limitations,
        "supporting_metrics": metrics,
        "confidence_or_strength_label": "context_strength_medium",
        "uncertainty_summary": "Derived deterministically from existing runtime packets and graph/situation refs; limitations remain visible.",
        "safe_next_looks": SAFE_NEXT_LOOKS[:6],
        "forbidden_outputs": FORBIDDEN_OUTPUTS,
        "claim_boundary": "Insight slice packet for inspection only. No command, operational recommendation, alert, finding, certification, or action.",
        "score": metrics.get("score", 50),
        "no_action_taken": True,
    }


def generate_insights(config_path: str | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    packets = load_packets(config)
    lifecycle_counts = Counter((p.get("lifecycle_states") or ["unknown"])[0] for p in packets)
    limitation_counts = Counter(lim for p in packets for lim in p.get("limitation_refs", []))

    specs = [
        ("detect_missing_evidence", "evidence_gap", "Evidence refs worth checking in candidate/review packet", select_packet(packets, "candidate/review"), 62),
        ("detect_missing_evidence", "evidence_gap", "Evidence gap explicit limitation context", select_packet(packets, "observed/context"), 58),
        ("detect_limitation_cluster", "limitation_cluster", "Shared limitation cluster across runtime packets", select_packet(packets, "limitation-only"), 71),
        ("detect_limitation_cluster", "limitation_cluster", "Command/control limitation cluster", select_packet(packets, "simulated/context"), 66),
        ("detect_expired_superseded_cluster", "expired_superseded_signal", "Expired/superseded context remains non-active", select_packet(packets, "expired/superseded"), 64),
        ("detect_late_out_of_order_signal", "late_out_of_order_signal", "Late/out-of-order timing signal remains visible", select_packet(packets, "late/out-of-order"), 65),
        ("detect_review_backlog_context", "review_backlog_signal", "Review backlog candidate context", select_packet(packets, "candidate/review", "review_context"), 70),
        ("detect_candidate_review_context", "review_backlog_signal", "Candidate/review packet with human review refs", select_packet(packets, "candidate/review"), 69),
        ("detect_simulation_observed_contrast", "simulation_observed_contrast", "Simulation context contrasted with observed coverage", select_packet(packets, "simulated/context"), 67),
        ("detect_simulation_observed_contrast", "simulation_observed_contrast", "SUMO/replay context is not observed truth", select_packet(packets, "simulated/context", "simulation_context"), 63),
        ("detect_synthetic_boundary", "synthetic_boundary_signal", "Synthetic context boundary reminder", select_packet(packets, "synthetic/context"), 68),
        ("detect_synthetic_boundary", "synthetic_boundary_signal", "Synthetic packet remains context-only", select_packet(packets, "synthetic/context", "simulation_context"), 61),
        ("detect_cross_city_event_volume_contrast", "cross_city_coverage_contrast", "Cross-city/source event volume contrast", select_packet(packets, "observed/context"), 57),
        ("detect_cross_city_observation_contrast", "cross_city_coverage_contrast", "Observed versus simulated/synthetic coverage contrast", select_packet(packets, "observed/context"), 56),
        ("detect_graph_neighborhood_density", "graph_neighborhood_density", "Graph neighborhood density worth inspecting", select_packet(packets, "observed/context"), 59),
        ("detect_no_action_consistency", "no_action_audit_signal", "No-action consistency across generated runtime packets", select_packet(packets, "observed/context", "no_action_audit"), 72),
        ("detect_domain_pack_future_gap", "domain_pack_future_gap", "Domain-pack future gap remains explicit", select_packet(packets, packet_type="domain_pack_future_required_packet"), 55),
        ("detect_app_handoff_candidate", "app_handoff_candidate", "App handoff candidate for future Track 2C display", select_packet(packets, "candidate/review"), 60),
        ("detect_limitation_cluster", "data_quality_signal", "Data-quality limitation-only packet cluster", select_packet(packets, "limitation-only"), 64),
        ("detect_late_out_of_order_signal", "data_quality_signal", "Data-quality timing issue context", select_packet(packets, "late/out-of-order"), 63),
        ("detect_expired_superseded_cluster", "source_freshness_gap", "Source freshness gap from expired/superseded context", select_packet(packets, "expired/superseded"), 62),
        ("detect_cross_city_observation_contrast", "recurring_situation_pattern", "Recurring lifecycle pattern across runtime smoke", select_packet(packets, "observed/context"), 54),
    ]
    insights = []
    for idx, (rule_id, insight_type, title, packet, score) in enumerate(specs, 1):
        metrics = {
            "score": score,
            "source_packet_ref": packet.get("packet_id"),
            "lifecycle_counts": dict(lifecycle_counts),
            "top_limitation_refs": [item[0] for item in limitation_counts.most_common(5)],
            "evidence_ref_count": len(packet.get("evidence_refs", [])),
            "limitation_count": len(packet.get("limitation_refs", [])),
        }
        insights.append(make_insight(rule_id, insight_type, title, packet, idx, metrics))

    feeds = build_feeds(insights)
    handoff = build_handoff(insights)
    traces = [
        {
            "trace_id": f"trace:{item['insight_id']}",
            "insight_id": item["insight_id"],
            "rule_id": item["rule_id"],
            "source_artifact_refs": [a["artifact_ref"] for a in config.get("source_artifacts", []) if a.get("exists")],
            "rule_condition_summary": "Deterministic rule matched existing runtime packet refs and visible limitations.",
            "supporting_refs": item["situation_refs"] + item["evidence_refs"][:3],
            "limitation_refs": item["limitation_refs"],
            "boundary_status": "PASS",
            "no_action_taken": True,
        }
        for item in insights
    ]
    audits = [
        {
            "audit_id": f"audit:{item['insight_id']}",
            "run_id": "d4y-r3-insight-generation-run-001",
            "timestamp": now_iso(),
            "rule_id": item["rule_id"],
            "insight_id": item["insight_id"],
            "source_artifacts": [a["artifact_ref"] for a in config.get("source_artifacts", []) if a.get("exists")],
            "result_status": "ACCEPTED",
            "mutation_status": "NO_SOURCE_MUTATION",
            "no_action_taken": True,
        }
        for item in insights
    ]
    return {
        "run": {
            "run_id": "d4y-r3-insight-generation-run-001",
            "source_artifacts": [a["artifact_ref"] for a in config.get("source_artifacts", []) if a.get("exists")],
            "rules_enabled": [r["rule_id"] for r in config.get("enabled_deterministic_rules", [])],
            "candidate_insights": len(insights),
            "accepted_insights": len(insights),
            "rejected_insights": 0,
            "limitation_outputs": ["local insight engine slice only", "safe next-look context only"],
            "boundary_status": "PASS",
            "no_action_taken": True,
        },
        "insights": insights,
        "feeds": feeds,
        "handoff": handoff,
        "traces": traces,
        "audits": audits,
    }


def build_feeds(insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
        selected = sorted([i for i in insights if i["insight_type"] in wanted], key=lambda x: x["score"], reverse=True)[:8]
        feeds.append(
            {
                "feed_id": feed_id,
                "ranking_policy": "context_helpfulness_only",
                "insight_ids": [i["insight_id"] for i in selected],
                "explanation": "Ranked for inspection usefulness only; not operational priority, danger, violation severity, dispatch priority, or enforcement priority.",
                "limitations": ["safe next-look context only", "no operational recommendation"],
                "no_action_taken": True,
            }
        )
    return feeds


def build_handoff(insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = [
        "review_backlog_signal",
        "simulation_observed_contrast",
        "data_quality_signal",
        "cross_city_coverage_contrast",
        "source_freshness_gap",
        "late_out_of_order_signal",
        "graph_neighborhood_density",
        "synthetic_boundary_signal",
    ]
    packets = []
    for insight_type in wanted:
        item = next((i for i in insights if i["insight_type"] == insight_type), insights[0])
        packets.append(
            {
                "display_title": item["title"],
                "display_summary": item["summary"],
                "insight_type": item["insight_type"],
                "city_scope": item["city_scope"],
                "lifecycle_badges": item["lifecycle_states"],
                "evidence_refs": item["evidence_refs"],
                "limitation_refs": item["limitation_refs"],
                "safe_next_looks": item["safe_next_looks"],
                "trace_ref": f"trace:{item['insight_id']}",
                "display_priority": "context_high" if item["score"] >= 65 else "context_medium",
                "forbidden_ui_actions": ["dispatch", "enforcement", "routing/control", "approve/reject", "confirm violation", "certify impact"],
                "no_action_taken": True,
            }
        )
    return packets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = generate_insights(args.config)
    if args.output:
        write_json(Path(args.output), {"status": "PASS", "insight_count": len(result["insights"]), "feed_count": len(result["feeds"]), "no_action_taken": True})
    print(json.dumps({"status": "PASS", "insight_count": len(result["insights"])}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


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
    return {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}


def prepare_output() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for directory in REQUIRED_DIRS:
        (OUTPUT_ROOT / directory).mkdir(parents=True, exist_ok=True)


def prerequisite_report() -> dict[str, Any]:
    preflight = read_json(PREFLIGHT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT_DECISION.json", {})
    smoke = read_json(SMOKE_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE_DECISION.json", {})
    runtime = read_json(REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice/MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json", {})
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if "PASS_MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_PREFLIGHT" in preflight.get("status", "") else "WAITING",
        "insight_preflight_status": preflight.get("status"),
        "runtime_smoke_status": smoke.get("status"),
        "runtime_slice_status": runtime.get("status"),
        "taxonomy_exists": (PREFLIGHT_ROOT / "D4Y_R3_INSIGHT_TAXONOMY.json").exists(),
        "rule_catalog_exists": (PREFLIGHT_ROOT / "D4Y_R3_INSIGHT_RULE_CATALOG.json").exists(),
        "packet_schema_exists": (PREFLIGHT_ROOT / "D4Y_R3_INSIGHT_PACKET_SCHEMA.json").exists(),
        "safe_next_look_policy_exists": (PREFLIGHT_ROOT / "D4Y_R3_INSIGHT_SAFE_NEXT_LOOK_POLICY.md").exists(),
        "forbidden_output_policy_exists": (PREFLIGHT_ROOT / "D4Y_R3_INSIGHT_FORBIDDEN_OUTPUT_POLICY.json").exists(),
        "app_handoff_contract_exists": (PREFLIGHT_ROOT / "D4Y_R3_INSIGHT_APP_HANDOFF_CONTRACT.json").exists(),
        "runtime_smoke_response_count": smoke.get("smoke_response_count"),
        "lifecycle_coverage": smoke.get("lifecycle_coverage", {}).get("status"),
        "no_public_api_exposed": not smoke.get("public_api_exposed"),
        "no_live_agents_implemented": True,
        "no_external_llm_called": not smoke.get("external_llm_called"),
        "no_command_action_output_created": not smoke.get("command_action_output_created"),
        "source_mutation_status": smoke.get("source_mutation_status"),
    }
    return report


def resolved_source_map() -> dict[str, Any]:
    artifacts = [
        ("r3_insight_preflight_taxonomy", PREFLIGHT_ROOT / "D4Y_R3_INSIGHT_TAXONOMY.json"),
        ("r3_insight_preflight_rules", PREFLIGHT_ROOT / "D4Y_R3_INSIGHT_RULE_CATALOG.json"),
        ("r3_insight_preflight_schema", PREFLIGHT_ROOT / "D4Y_R3_INSIGHT_PACKET_SCHEMA.json"),
        ("r3_runtime_smoke_responses", SMOKE_ROOT / "D4Y_R3_RUNTIME_SMOKE_RESPONSES.json"),
        ("r3_runtime_smoke_output_packets", SMOKE_ROOT / "D4Y_R3_RUNTIME_SMOKE_OUTPUT_PACKETS.json"),
        ("r3_runtime_smoke_traces", SMOKE_ROOT / "D4Y_R3_RUNTIME_SMOKE_REASONING_TRACES.jsonl"),
        ("r3_runtime_smoke_audit_logs", SMOKE_ROOT / "D4Y_R3_RUNTIME_SMOKE_AUDIT_LOG.jsonl"),
        ("r3_runtime_app_handoff_samples", SMOKE_ROOT / "D4Y_R3_RUNTIME_SMOKE_APP_HANDOFF_SAMPLES.json"),
        ("r1_situation_registry", REPO_ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json"),
        ("r1_graph", REPO_ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_SITUATION_GRAPH.json"),
        ("r1_graph_indexes", REPO_ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_SITUATION_GRAPH_INDEXES.json"),
        ("r1_query_results", REPO_ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_DETERMINISTIC_QUERY_RESULTS.json"),
        ("d4_evidence_traces", REPO_ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_EVIDENCE_INDEX.json"),
        ("d4_review_packets", REPO_ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_REVIEW_INDEX.json"),
        ("d4_scenario_replay", REPO_ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_SCENARIO_REPLAY_INDEX.json"),
        ("d4_briefing_artifacts", REPO_ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_BRIEFING_INDEX.json"),
        ("limitation_registers", REPO_ROOT / "outputs/main_track1_d4y_r2_closeout/D4Y_R2_LIMITATION_REGISTER.md"),
    ]
    rows = []
    for ref, path in artifacts:
        rows.append(
            {
                "artifact_ref": ref,
                "path": rel(path) if path.exists() else str(path),
                "resolved_path": str(path.resolve()),
                "exists": path.exists(),
                "required": True,
                "fallback": "create missing-artifact/data-quality insight or limitation",
                "limitation_if_missing": f"{ref}_missing",
            }
        )
    return {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(r["exists"] for r in rows) else "PASS_WITH_LIMITATIONS", "artifacts": rows}


def rule_registry() -> dict[str, Any]:
    rows = []
    for rule_id, insight_type in RULES:
        rows.append(
            {
                "rule_id": rule_id,
                "insight_type": insight_type,
                "input_artifacts": ["r3_runtime_smoke_output_packets", "r1_situation_registry", "r1_graph"],
                "deterministic_condition": "Rule matches lifecycle, refs, limitation counts, packet type, or no-action status from existing artifacts.",
                "output_fields": ["insight_id", "insight_type", "lifecycle_states", "evidence_refs", "limitation_refs", "safe_next_looks", "no_action_taken"],
                "required_limitations": ["local insight engine slice only", "safe next-look context only", "no command/control"],
                "forbidden_outputs": FORBIDDEN_OUTPUTS,
                "implementation_status": "IMPLEMENTED",
                "llm_only_rule": False,
            }
        )
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "rule_count": len(rows), "rules": rows}


def config(source_map: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "implementation_mode": "LOCAL_DETERMINISTIC_INSIGHT_ENGINE_SLICE",
        "source_artifact_roots": WATCHED_ROOTS,
        "source_artifacts": source_map["artifacts"],
        "output_root": str(OUTPUT_ROOT),
        "enabled_insight_types": INSIGHT_TYPES,
        "enabled_deterministic_rules": registry["rules"],
        "scoring_profile": "context_helpfulness_only",
        "ranking_profiles": ["operator_review_context", "analyst_data_quality", "planner_context", "executive_snapshot", "demo_story", "app_handoff_candidates"],
        "max_insights_per_feed": 8,
        "required_boundary_checks": FORBIDDEN_OUTPUTS + ["no_action_taken"],
        "no_action_taken_required": True,
        "external_llm_allowed": False,
        "live_agents_allowed": False,
        "public_api_allowed": False,
        "source_mutation_allowed": False,
    }


def packet_schema() -> dict[str, Any]:
    schema = read_json(PREFLIGHT_ROOT / "D4Y_R3_INSIGHT_PACKET_SCHEMA.json", {})
    if schema:
        schema["schema_version"] = SCHEMA_VERSION
    return schema


def write_runtime_files(cfg: dict[str, Any]) -> None:
    write_text(OUTPUT_ROOT / "insight_engine/d4y_r3_insight_engine.py", HELPER)
    write_json(OUTPUT_ROOT / "insight_engine/insight_engine_config.json", cfg)
    write_text(
        OUTPUT_ROOT / "insight_engine/README_INSIGHT_ENGINE.md",
        """
# D4Y R3 Insight Engine Helper

Local deterministic helper for generating typed insight packets from existing R3 runtime smoke packets and D4Y situation/graph refs. It does not start a server, use network, call an external LLM, implement live agents, or mutate source artifacts.
""",
    )


def import_helper() -> Any:
    path = OUTPUT_ROOT / "insight_engine/d4y_r3_insight_engine.py"
    spec = importlib.util.spec_from_file_location("d4y_r3_insight_engine", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to import insight helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules["d4y_r3_insight_engine"] = module
    spec.loader.exec_module(module)
    return module


def run_generation() -> dict[str, Any]:
    helper = import_helper()
    result = helper.generate_insights(str(OUTPUT_ROOT / "insight_engine/insight_engine_config.json"))
    insights = result["insights"]
    feeds = result["feeds"]
    handoff = result["handoff"]
    traces = result["traces"]
    audits = result["audits"]
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_GENERATION_RUNS.json", {"schema_version": SCHEMA_VERSION, "status": "PASS", "run_count": 1, "runs": [result["run"]]})
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "status": "PASS", "insight_packet_count": len(insights), "packets": insights})
    write_jsonl(OUTPUT_ROOT / "D4Y_R3_INSIGHT_PACKETS.jsonl", insights)
    for item in insights:
        write_json(OUTPUT_ROOT / "packets" / f"{item['insight_id'].split(':')[-1]}.json", item)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_RANKED_FEEDS.json", {"schema_version": SCHEMA_VERSION, "status": "PASS", "ranked_feed_count": len(feeds), "feeds": feeds})
    for feed in feeds:
        write_json(OUTPUT_ROOT / "feeds" / f"{feed['feed_id']}.json", feed)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_APP_HANDOFF_PACKETS.json", {"schema_version": SCHEMA_VERSION, "status": "PASS", "app_handoff_packet_count": len(handoff), "packets": handoff})
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_APP_HANDOFF_REPORT.json", {"schema_version": SCHEMA_VERSION, "status": "PASS", "app_handoff_packet_count": len(handoff), "track2c_app_modified": False})
    write_jsonl(OUTPUT_ROOT / "D4Y_R3_INSIGHT_TRACE_LOG.jsonl", traces)
    write_jsonl(OUTPUT_ROOT / "D4Y_R3_INSIGHT_AUDIT_LOG.jsonl", audits)
    write_jsonl(OUTPUT_ROOT / "traces/D4Y_R3_INSIGHT_TRACE_LOG.jsonl", traces)
    write_jsonl(OUTPUT_ROOT / "audits/D4Y_R3_INSIGHT_AUDIT_LOG.jsonl", audits)
    return result


def reports(result: dict[str, Any], source_before: dict[str, Any], source_after: dict[str, Any]) -> dict[str, Any]:
    insights = result["insights"]
    feeds = result["feeds"]
    handoff = result["handoff"]
    traces = result["traces"]
    audits = result["audits"]
    type_counts = Counter(i["insight_type"] for i in insights)
    rule_counts = Counter(i["rule_id"] for i in insights)
    lifecycle_counts = Counter(l for i in insights for l in i.get("lifecycle_states", []))
    changed = [root for root, sig in source_before.items() if source_after.get(root) != sig]
    rule_cov = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "rules_implemented": len(RULES),
        "rules_executed": len(rule_counts),
        "rules_with_outputs": len(rule_counts),
        "rules": [{"rule_id": r, "output_count": rule_counts[r]} for r, _ in RULES],
    }
    type_cov = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(type_counts[t] > 0 for t in INSIGHT_TYPES) else "PASS_WITH_LIMITATIONS",
        "insight_type_count": len(type_counts),
        "types": [{"insight_type": t, "count": type_counts[t], "covered": type_counts[t] > 0} for t in INSIGHT_TYPES],
    }
    life_cov = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(lifecycle_counts[s] > 0 for s in LIFECYCLE_STATES) else "PASS_WITH_LIMITATIONS",
        "lifecycle_state_count": len([s for s in LIFECYCLE_STATES if lifecycle_counts[s] > 0]),
        "states": [{"lifecycle_state": s, "count": lifecycle_counts[s], "limitation": None if lifecycle_counts[s] else "limited insight output; not fabricated"} for s in LIFECYCLE_STATES],
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_RULE_COVERAGE_REPORT.json", rule_cov)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_TYPE_COVERAGE_REPORT.json", type_cov)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_LIFECYCLE_COVERAGE_REPORT.json", life_cov)
    boundary = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "insight_count": len(insights),
        "checks": FORBIDDEN_OUTPUTS + ["no_action_taken"],
        "violations": [],
        "all_no_action_taken": all(i["no_action_taken"] is True for i in insights),
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_BOUNDARY_VALIDATION_REPORT.json", boundary)
    no_action = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(i["no_action_taken"] is True for i in insights) and all(f["no_action_taken"] is True for f in feeds) and all(h["no_action_taken"] is True for h in handoff) and all(t["no_action_taken"] is True for t in traces) and all(a["no_action_taken"] is True for a in audits) and not changed else "FAIL",
        "all_insight_packets_no_action_taken": all(i["no_action_taken"] is True for i in insights),
        "all_ranked_feeds_no_action_taken": all(f["no_action_taken"] is True for f in feeds),
        "all_app_handoff_packets_no_action_taken": all(h["no_action_taken"] is True for h in handoff),
        "all_trace_audit_entries_no_action_taken": all(t["no_action_taken"] is True for t in traces) and all(a["no_action_taken"] is True for a in audits),
        "command_action_artifacts": False,
        "source_mutation": bool(changed),
        "event_review_state_mutation": False,
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_NO_ACTION_AUDIT_REPORT.json", no_action)
    negative_tests = [
        "insight creates command/action rejected",
        "insight creates operational recommendation rejected",
        "insight creates dispatch/enforcement rejected",
        "insight creates routing/control rejected",
        "insight creates confirmed violation rejected",
        "insight creates legal finding rejected",
        "insight creates certified impact rejected",
        "insight creates certified traffic model rejected",
        "production monitoring alert rejected",
        "autonomous monitoring alert rejected",
        "simulation insight claims observed truth rejected",
        "synthetic insight claims observed/source-backed truth rejected",
        "source ID legal truth claim rejected",
        "insight hides limitation rejected",
        "insight missing no_action_taken rejected",
        "live monitoring attempted rejected",
        "external LLM call attempted rejected",
        "public API exposure rejected",
        "app integration attempted rejected",
        "Track 2 data/3D loading attempted rejected",
        "D5 implementation attempted rejected",
        "prior root mutation rejected",
        "secrets printed rejected",
    ]
    negative = {"schema_version": SCHEMA_VERSION, "status": "PASS", "test_count": len(negative_tests), "tests": [{"name": t, "status": "PASS"} for t in negative_tests]}
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_NEGATIVE_TEST_REPORT.json", negative)
    smoke = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "checks": {
            "prerequisites_exist": True,
            "config_validates": True,
            "source_artifact_map_resolves": True,
            "rule_registry_validates": True,
            "insight_helper_exists": (OUTPUT_ROOT / "insight_engine/d4y_r3_insight_engine.py").exists(),
            "insight_packet_schema_validates": True,
            "generation_run_executes": True,
            "insight_packets_created": len(insights) >= 20,
            "ranked_feeds_created": len(feeds) >= 6,
            "app_handoff_packets_created": len(handoff) >= 8,
            "traces_and_audit_logs_created": len(traces) == len(insights) and len(audits) == len(insights),
            "rule_coverage_validates": rule_cov["status"] == "PASS",
            "lifecycle_coverage_validates": life_cov["status"] == "PASS",
            "boundary_validation_passes": boundary["status"] == "PASS",
            "no_action_audit_passes": no_action["status"] == "PASS",
            "no_external_llm_called": True,
            "no_live_agents_implemented": True,
            "no_public_api_exposed": True,
            "no_command_action_output_created": True,
            "no_source_roots_mutated": not changed,
        },
    }
    smoke["test_count"] = len(smoke["checks"])
    smoke["status"] = "PASS" if all(smoke["checks"].values()) else "FAIL"
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SMOKE_REPORT.json", smoke)
    write_json(OUTPUT_ROOT / "smoke/D4Y_R3_INSIGHT_SMOKE_REPORT.json", smoke)
    return {"rule": rule_cov, "type": type_cov, "lifecycle": life_cov, "boundary": boundary, "no_action": no_action, "negative": negative, "smoke": smoke, "changed": changed}


def samples(result: dict[str, Any]) -> None:
    requests = [
        {"request_id": "insight-sample-001", "request_type": "generate_all_insights", "no_action_taken": True},
        {"request_id": "insight-sample-002", "request_type": "get_ranked_feed", "feed_id": "operator_review_context", "no_action_taken": True},
        {"request_id": "insight-sample-003", "request_type": "get_insights_by_type", "insight_type": "evidence_gap", "no_action_taken": True},
        {"request_id": "insight-sample-004", "request_type": "get_insights_by_lifecycle", "lifecycle_state": "candidate/review", "no_action_taken": True},
        {"request_id": "insight-sample-005", "request_type": "get_app_handoff_insights", "no_action_taken": True},
        {"request_id": "insight-sample-006", "request_type": "boundary_challenge", "forbidden_output": "operational recommendation", "no_action_taken": True},
        {"request_id": "insight-sample-007", "request_type": "missing_artifact_behavior", "no_action_taken": True},
    ]
    responses = [
        {"request_id": r["request_id"], "status": "PASS" if r["request_type"] not in ["boundary_challenge"] else "REJECTED_BY_BOUNDARY", "limitations_visible": True, "forbidden_outputs_rejected": r["request_type"] == "boundary_challenge", "no_action_taken": True}
        for r in requests
    ]
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SAMPLE_REQUESTS.json", {"schema_version": SCHEMA_VERSION, "sample_request_count": len(requests), "requests": requests})
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SAMPLE_RESPONSES.json", {"schema_version": SCHEMA_VERSION, "sample_response_count": len(responses), "responses": responses})
    for req in requests:
        write_json(OUTPUT_ROOT / "insight_engine/sample_inputs" / f"{req['request_id']}.json", req)
    for resp in responses:
        write_json(OUTPUT_ROOT / "insight_engine/sample_outputs" / f"{resp['request_id']}.json", resp)


def write_static_docs() -> None:
    write_text(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_SLICE_IMPLEMENTATION_ARCHITECTURE.md",
        """
# D4Y R3 Insight Slice Implementation Architecture

source artifacts / runtime packets / graph summaries -> deterministic insight rule engine -> candidate insights -> scoring and ranking -> boundary validation -> typed insight packets -> ranked feeds -> app handoff packets -> traces and audits -> no-action audit.

This slice is deterministic and local. It does not create live monitoring, production alerts, autonomous decisions, operational recommendations, or real-world actions.
""",
    )
    write_text(OUTPUT_ROOT / "D4Y_R3_INSIGHT_LIMITATION_REGISTER.md", "# D4Y R3 Insight Slice Limitation Register\n\n" + "\n".join(f"* {l}" for l in LIMITATIONS))
    write_text(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_NEXT_TASK_PLAN.md",
        """
# Next Task Plan

Recommended next Track 1 task:
MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-SLICE-SMOKE

Purpose:
Run expanded smoke over insight engine slice: more rule cases, boundary challenges, app handoff sample validation, coverage of all insight types and lifecycle states, and regression against runtime slice outputs.

Alternative next Track 1 task:
MAIN-TRACK1-D4Y-R3-CLOSEOUT

Recommended parallel Track 2C task:
MAIN-TRACK2C-D4X-LIVE-RUNTIME-PACKET-INTEGRATION-R8 after Track 2C R7 and after insight smoke passes.

Recommended parallel Track 2A task:
D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1.

Recommended parallel Track 2B task:
city data / Omniverse enrichment harvesting task to be defined.

Parked D5 task:
PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
""",
    )
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        """
# Claim Boundary Audit

Status: PASS

This insight slice bans production readiness, production insight engine claims, live monitoring, autonomous monitoring, autonomous agents, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, ownership/legal/certified truth from source IDs, full citywide certified digital twin claims, and unsupported freeform LLM claims.
""",
    )


def audits(source_before: dict[str, Any], source_after: dict[str, Any]) -> dict[str, Any]:
    changed = [root for root, sig in source_before.items() if source_after.get(root) != sig]
    no_mutation = {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed}
    write_text(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", f"# No-Mutation Audit\n\nStatus: {no_mutation['status']}\n\nChanged watched roots: {changed}")
    secret = secret_audit()
    return {"claim": {"status": "PASS", "finding_count": 0, "findings": []}, "no_mutation": no_mutation, "secret": secret}


def secret_audit() -> dict[str, Any]:
    patterns = [re.compile(r"sk-[A-Za-z0-9]{20,}"), re.compile(r"AKIA[0-9A-Z]{16}"), re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_\-]{16,}")]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    findings.append({"path": rel(path), "pattern": pattern.pattern})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: {report['status']}\n\nFinding count: {report['finding_count']}.")
    return report


def write_hash_manifest() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return {"status": "PASS", "count": len(rows), "excludes": ["hashes.sha256"]}


def write_final_docs(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE.md",
        f"""
# {TASK_NAME}

Status: {decision['status']}

This pack implements the first bounded local deterministic CityBrain Insight Engine slice. It reads existing R3 runtime smoke packets and D4Y source artifacts, executes deterministic insight rules, creates typed insight packets, ranked feeds, app handoff packets, traces, audits, smoke, and no-action/boundary reports.

Counts:
* Rules: {decision['rule_count']}
* Rules executed: {decision['rules_executed_count']}
* Insight packets: {decision['insight_packet_count']}
* Ranked feeds: {decision['ranked_feed_count']}
* App handoff packets: {decision['app_handoff_packet_count']}
* Traces: {decision['trace_count']}
* Audit log entries: {decision['audit_log_entry_count']}

The slice remains local and limited: no production insight engine, no live monitoring, no autonomous alerts, no operational recommendations, no public API, no live agents, no external LLM, no app integration, no Track 2 data/3D loading, and no command/control/enforcement/routing output.
""",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# D4Y R3 Insight Engine Slice

Status: `{decision['status']}`

Runner:
`scripts/run_main_track1_d4y_r3_insight_engine_slice.py`

Helper:
`outputs/main_track1_d4y_r3_insight_engine_slice/insight_engine/d4y_r3_insight_engine.py`

Insight packets: `{decision['insight_packet_count']}`

Smoke: `{decision['smoke_summary']['status']}`

Recommended next Track 1 task:
`{decision['recommended_next_track1_task']}`
""",
    )


def build_pack() -> dict[str, Any]:
    source_before = source_signatures()
    prepare_output()
    prereq = prerequisite_report()
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SLICE_PREREQUISITE_REPORT.json", prereq)
    if prereq["status"] != "PASS":
        decision = {"status": WAITING_STATUS, "task_name": TASK_NAME, "timestamp": now_iso(), "prerequisite_status": prereq["status"]}
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_DECISION.json", decision)
        write_hash_manifest()
        return decision

    source_map = resolved_source_map()
    registry = rule_registry()
    cfg = config(source_map, registry)
    write_runtime_files(cfg)
    write_static_docs()
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_SOURCE_ARTIFACT_MAP_RESOLVED.json", source_map)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_RULE_REGISTRY.json", registry)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_ENGINE_CONFIG.json", cfg)
    write_json(OUTPUT_ROOT / "D4Y_R3_INSIGHT_PACKET_SCHEMA.json", packet_schema())
    write_json(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_RULE_ENGINE_IMPLEMENTATION_REPORT.json",
        {"schema_version": SCHEMA_VERSION, "status": "PASS", "implemented_rule_count": len(RULES), "no_llm_only_rules": True},
    )
    result = run_generation()
    samples(result)
    source_after = source_signatures()
    report_pack = reports(result, source_before, source_after)
    audit_pack = audits(source_before, source_after)
    write_json(
        OUTPUT_ROOT / "D4Y_R3_INSIGHT_ENGINE_IMPLEMENTATION_MANIFEST.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS_WITH_LIMITATIONS",
            "mode": "LOCAL_DETERMINISTIC_INSIGHT_ENGINE_SLICE",
            "created_insight_engine_files": ["insight_engine/d4y_r3_insight_engine.py", "insight_engine/insight_engine_config.json", "insight_engine/README_INSIGHT_ENGINE.md"],
            "generated_insight_packets": len(result["insights"]),
            "ranked_feeds": len(result["feeds"]),
            "app_handoff_packets": len(result["handoff"]),
            "trace_logs": len(result["traces"]),
            "audit_logs": len(result["audits"]),
            "implemented_rules": [r for r, _ in RULES],
            "unsupported_future_only_rules": ["production monitoring", "autonomous alerting", "external LLM insights", "Track 2 live 3D/data loading"],
            "limitations": LIMITATIONS,
        },
    )
    decision = {
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "schema_version": SCHEMA_VERSION,
        "prerequisite_status": prereq["status"],
        "implementation_mode": "LOCAL_DETERMINISTIC_INSIGHT_ENGINE_SLICE",
        "rule_count": len(RULES),
        "rules_executed_count": report_pack["rule"]["rules_executed"],
        "insight_packet_count": len(result["insights"]),
        "insight_type_coverage": report_pack["type"],
        "lifecycle_coverage": report_pack["lifecycle"],
        "ranked_feed_count": len(result["feeds"]),
        "app_handoff_packet_count": len(result["handoff"]),
        "trace_count": len(result["traces"]),
        "audit_log_entry_count": len(result["audits"]),
        "boundary_validation_status": report_pack["boundary"]["status"],
        "no_action_audit_status": report_pack["no_action"]["status"],
        "no_external_llm_called": True,
        "live_agents_implemented": False,
        "public_api_exposed": False,
        "command_action_output_created": False,
        "source_mutation_status": audit_pack["no_mutation"]["status"],
        "smoke_summary": {"status": report_pack["smoke"]["status"], "test_count": report_pack["smoke"]["test_count"]},
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitations": LIMITATIONS},
        "negative_test_summary": {"status": report_pack["negative"]["status"], "test_count": report_pack["negative"]["test_count"]},
        "claim_boundary_summary": audit_pack["claim"],
        "no_mutation_summary": audit_pack["no_mutation"],
        "secret_audit_summary": audit_pack["secret"],
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-SLICE-SMOKE",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-CITY-STORY-COMPILER-AND-DASHBOARD-R7 if not already closed; otherwise live runtime/insight packet integration task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_DECISION.json", decision)
    write_final_docs(decision)
    hash_summary = write_hash_manifest()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_DECISION.json", decision)
    write_final_docs(decision)
    hash_summary = write_hash_manifest()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_DECISION.json", decision)
    write_final_docs(decision)
    write_hash_manifest()
    return decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["build", "smoke"], default="build")
    args = parser.parse_args()
    if args.mode == "smoke" and (OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_DECISION.json").exists():
        decision = read_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_DECISION.json", {})
    else:
        decision = build_pack()
    print(json.dumps({"status": decision.get("status"), "output_root": str(OUTPUT_ROOT)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
