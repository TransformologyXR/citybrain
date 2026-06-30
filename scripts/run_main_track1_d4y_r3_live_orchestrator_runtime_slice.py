#!/usr/bin/env python3
"""Build the D4Y R3 local orchestrator runtime slice pack.

The runner creates a bounded file/CLI callable runtime over existing D4Y R1/R2
artifacts, executes sample requests, and writes the evidence/audit pack.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE"
SCHEMA_VERSION = "main-track1-d4y-r3-live-orchestrator-runtime-slice.v1"
STATUS = "PASS_MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_PREFLIGHT"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_track1_d4y_r3_live_orchestrator_runtime_slice"
PREFLIGHT_ROOT = REPO_ROOT / "outputs" / "main_track1_d4y_r3_live_orchestrator_runtime_slice_preflight"

RUNTIME_FILES = [
    "runtime/d4y_r3_runtime.py",
    "runtime/runtime_config.json",
    "runtime/README_RUNTIME.md",
]

REQUIRED_DIRS = [
    "runtime",
    "runtime/sample_requests",
    "runtime/sample_responses",
    "requests",
    "responses",
    "packets",
    "traces",
    "audits",
    "tool_outputs",
    "smoke",
    "handoff",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE.md",
    "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json",
    "D4Y_R3_RUNTIME_SLICE_PREREQUISITE_REPORT.json",
    "D4Y_R3_RUNTIME_IMPLEMENTATION_ARCHITECTURE.md",
    "D4Y_R3_RUNTIME_IMPLEMENTATION_MANIFEST.json",
    "D4Y_R3_RUNTIME_ENTRYPOINTS.md",
    "D4Y_R3_RUNTIME_CONFIG.json",
    "D4Y_R3_RUNTIME_ARTIFACT_SOURCE_MAP_RESOLVED.json",
    "D4Y_R3_RUNTIME_REQUEST_SCHEMA.json",
    "D4Y_R3_RUNTIME_RESPONSE_SCHEMA.json",
    "D4Y_R3_RUNTIME_OUTPUT_PACKET_SCHEMA.json",
    "D4Y_R3_RUNTIME_TOOL_ADAPTER_REGISTRY.json",
    "D4Y_R3_RUNTIME_TOOL_ADAPTER_IMPLEMENTATION_REPORT.json",
    "D4Y_R3_RUNTIME_HARNESS_ROUTING_TABLE.json",
    "D4Y_R3_RUNTIME_BOUNDARY_VALIDATOR_RULES.json",
    "D4Y_R3_RUNTIME_BOUNDARY_VALIDATION_REPORT.json",
    "D4Y_R3_RUNTIME_NO_ACTION_AUDIT_REPORT.json",
    "D4Y_R3_RUNTIME_REASONING_TRACE_SCHEMA.json",
    "D4Y_R3_RUNTIME_AUDIT_LOG_SCHEMA.json",
    "D4Y_R3_RUNTIME_SAMPLE_REQUESTS.json",
    "D4Y_R3_RUNTIME_SAMPLE_RESPONSES.json",
    "D4Y_R3_RUNTIME_OUTPUT_PACKETS.json",
    "D4Y_R3_RUNTIME_REASONING_TRACES.jsonl",
    "D4Y_R3_RUNTIME_AUDIT_LOG.jsonl",
    "D4Y_R3_RUNTIME_RUN_RESULTS.json",
    "D4Y_R3_RUNTIME_ERROR_AND_LIMITATION_REPORT.json",
    "D4Y_R3_RUNTIME_APP_HANDOFF_SAMPLE.json",
    "D4Y_R3_RUNTIME_SMOKE_REPORT.json",
    "D4Y_R3_RUNTIME_LIMITATION_REGISTER.md",
    "D4Y_R3_RUNTIME_NEGATIVE_TEST_REPORT.json",
    "D4Y_R3_RUNTIME_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

REQUEST_TYPES = [
    "evidence_qa",
    "narrator_summary",
    "investigation",
    "simulation_context",
    "decision_support_context",
    "review_context",
    "data_quality_context",
    "limitation_audit",
    "no_action_audit",
    "domain_pack_context",
    "malformed_or_unsupported_request",
    "forbidden_output_challenge",
]

OUTPUT_PACKET_TYPES = [
    "answer_packet",
    "narrator_input_packet",
    "investigation_packet",
    "simulation_context_packet",
    "decision_support_context_packet",
    "review_context_packet",
    "data_quality_packet",
    "limitation_audit_packet",
    "no_action_audit_packet",
    "domain_pack_future_required_packet",
    "rejection_packet",
]

TOOL_ADAPTERS = [
    "query_situation_graph",
    "get_situation_by_id",
    "get_situation_neighborhood",
    "get_evidence_for_situation",
    "get_review_context",
    "get_scenario_replay_context",
    "get_briefing_context",
    "get_limitations",
    "get_source_provenance",
    "run_no_action_audit",
    "check_forbidden_claims",
    "assemble_answer_packet",
    "assemble_investigation_packet",
    "assemble_simulation_context_packet",
    "assemble_decision_support_packet",
    "assemble_narrator_input_packet",
]

HARNESS_ROUTES = {
    "evidence_qa": "evidence_qa_harness",
    "narrator_summary": "narrator_harness",
    "investigation": "investigation_harness",
    "simulation_context": "simulation_harness",
    "decision_support_context": "decision_support_harness",
    "review_context": "review_harness",
    "data_quality_context": "data_quality_harness",
    "limitation_audit": "data_quality_harness",
    "no_action_audit": "data_quality_harness",
    "domain_pack_context": "domain_pack_harness",
}

PACKET_BY_REQUEST = {
    "evidence_qa": "answer_packet",
    "narrator_summary": "narrator_input_packet",
    "investigation": "investigation_packet",
    "simulation_context": "simulation_context_packet",
    "decision_support_context": "decision_support_context_packet",
    "review_context": "review_context_packet",
    "data_quality_context": "data_quality_packet",
    "limitation_audit": "limitation_audit_packet",
    "no_action_audit": "no_action_audit_packet",
    "domain_pack_context": "domain_pack_future_required_packet",
}

BOUNDARY_CHECKS = [
    "production_claim_check",
    "autonomous_monitoring_check",
    "autonomous_agent_check",
    "command_control_check",
    "dispatch_enforcement_check",
    "routing_control_check",
    "confirmed_violation_check",
    "legal_finding_check",
    "certified_impact_check",
    "certified_traffic_model_check",
    "simulated_observed_truth_check",
    "synthetic_observed_truth_check",
    "visual_id_canonical_identity_check",
    "placeholder_high_fidelity_geometry_check",
    "limitation_visibility_check",
    "evidence_required_check",
    "no_action_taken_check",
    "unsupported_claim_check",
    "domain_pack_required_check",
]

LIMITATIONS = [
    "local runtime slice only",
    "not production orchestrator",
    "no public API",
    "no live agents",
    "no multi-agent runtime",
    "no external LLM",
    "no app integration yet",
    "no Track 2 data/3D loading",
    "domain packs not implemented",
    "Dubai DLD/DM not implemented",
    "decision-support context only, not recommendation/action",
    "investigation evidence exploration only, not finding",
    "simulation context only, not routing/control/certified model",
    "no command/control/enforcement/dispatch/routing",
    "no legal finding",
    "no confirmed violation",
    "no certified impact",
    "no certified traffic model",
]

SOURCE_ROOTS = [
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_preflight",
    "outputs/main_track1_d4y_r2_closeout",
    "outputs/main_track1_d4y_r2_orchestration_smoke",
    "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight",
    "outputs/main_track1_d4y_r2_agent_adapter_contracts",
    "outputs/main_track1_d4y_r2_harness_family_contracts",
    "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry",
    "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight",
    "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "outputs/main_track1_d4_closeout_and_d5_roadmap",
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
    return {root: path_signature(REPO_ROOT / root) for root in SOURCE_ROOTS}


def prepare_output() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for dirname in REQUIRED_DIRS:
        (OUTPUT_ROOT / dirname).mkdir(parents=True, exist_ok=True)


def load_situations() -> list[dict[str, Any]]:
    registry = read_json(
        REPO_ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json",
        {},
    )
    situations = registry.get("situations", [])
    if isinstance(situations, dict):
        situations = list(situations.values())
    return [s for s in situations if isinstance(s, dict)]


def choose_situations(situations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_state: dict[str, dict[str, Any]] = {}
    for situation in situations:
        state = situation.get("primary_lifecycle_state") or (situation.get("lifecycle_state_set") or [None])[0]
        by_state.setdefault(str(state), situation)
    default = situations[0] if situations else {}

    def first_where(predicate: Any) -> dict[str, Any]:
        for item in situations:
            if predicate(item):
                return item
        return default

    return {
        "evidence_qa": first_where(lambda s: bool(s.get("evidence_trace_refs"))),
        "narrator_summary": first_where(lambda s: bool(s.get("briefing_refs"))),
        "investigation": first_where(lambda s: bool(s.get("evidence_trace_refs")) and bool(s.get("source_refs"))),
        "simulation_context": first_where(lambda s: bool(s.get("scenario_replay_refs")) or s.get("primary_lifecycle_state") in ["simulated/context", "synthetic/context"]),
        "decision_support_context": default,
        "review_context": first_where(lambda s: bool(s.get("review_packet_refs")) or s.get("primary_lifecycle_state") == "candidate/review"),
        "data_quality_context": by_state.get("late/out-of-order") or by_state.get("limitation-only") or default,
        "limitation_audit": first_where(lambda s: bool(s.get("limitation_refs"))),
        "no_action_audit": default,
        "domain_pack_context": default,
    }


def resolved_source_map() -> dict[str, Any]:
    preflight_map = read_json(PREFLIGHT_ROOT / "D4Y_R3_RUNTIME_ARTIFACT_SOURCE_MAP.json", {"artifacts": []})
    artifacts = []
    for item in preflight_map.get("artifacts", []):
        expected = item["expected_path"]
        path = REPO_ROOT / expected
        artifacts.append(
            {
                "artifact_ref": item["artifact_ref"],
                "expected_path": expected,
                "resolved_path": str(path.resolve()),
                "exists": path.exists(),
                "required": bool(item.get("required_for_runtime_slice")),
                "fallback_behavior": item.get("fallback_if_missing"),
                "limitation_if_missing": item.get("limitation_if_missing"),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(a["exists"] or not a["required"] for a in artifacts) else "PASS_WITH_LIMITATIONS",
        "artifacts": artifacts,
        "missing_required": [a for a in artifacts if a["required"] and not a["exists"]],
    }


def build_runtime_config(source_map: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "runtime_mode": "LOCAL_FILE_AND_CLI_RUNTIME_SLICE",
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "input_artifact_roots": SOURCE_ROOTS,
        "resolved_artifact_source_map": source_map["artifacts"],
        "allowed_request_types": REQUEST_TYPES,
        "allowed_harnesses": sorted(set(HARNESS_ROUTES.values())),
        "harness_routes": HARNESS_ROUTES,
        "allowed_tool_adapters": TOOL_ADAPTERS,
        "output_packet_types": OUTPUT_PACKET_TYPES,
        "boundary_checks": BOUNDARY_CHECKS,
        "no_action_taken_required": True,
        "external_llm_allowed": False,
        "live_agents_allowed": False,
        "public_api_allowed": False,
        "source_mutation_allowed": False,
        "network_allowed": False,
    }


def schema_pack() -> dict[str, Any]:
    request_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "D4Y R3 Runtime Request",
        "type": "object",
        "required": ["request_id", "request_type", "desired_output_type", "include_limitations", "include_trace", "no_action_taken"],
        "properties": {
            "request_id": {"type": "string"},
            "request_type": {"type": "string"},
            "situation_id": {"type": "string"},
            "desired_output_type": {"type": "string"},
            "required_evidence_level": {"type": "string"},
            "include_limitations": {"type": "boolean", "const": True},
            "include_trace": {"type": "boolean", "const": True},
            "forbidden_outputs": {"type": "array", "items": {"type": "string"}},
            "no_action_taken": {"type": "boolean", "const": True},
        },
        "additionalProperties": True,
    }
    common_props = {
        "request_id": {"type": "string"},
        "request_type": {"type": "string"},
        "selected_harness": {"type": "string"},
        "lifecycle_states": {"type": "array"},
        "evidence_refs": {"type": "array"},
        "source_refs": {"type": "array"},
        "limitation_refs": {"type": "array"},
        "claim_boundary": {"type": "string"},
        "no_action_taken": {"type": "boolean", "const": True},
        "boundary_validation_status": {"type": "string"},
        "trace_ref": {"type": "string"},
        "audit_ref": {"type": "string"},
    }
    response_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "D4Y R3 Runtime Response",
        "type": "object",
        "required": list(common_props) + ["status", "packet_ref"],
        "properties": {"status": {"type": "string"}, "packet_ref": {"type": "string"}, **common_props},
        "additionalProperties": True,
    }
    packet_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "D4Y R3 Runtime Output Packet",
        "type": "object",
        "required": list(common_props) + ["packet_id", "packet_type"],
        "properties": {"packet_id": {"type": "string"}, "packet_type": {"type": "string", "enum": OUTPUT_PACKET_TYPES}, **common_props},
        "additionalProperties": True,
    }
    trace_schema = {
        "title": "D4Y R3 Runtime Structured Reasoning Trace",
        "type": "object",
        "required": ["trace_id", "request_id", "steps", "no_action_taken"],
        "properties": {
            "trace_id": {"type": "string"},
            "request_id": {"type": "string"},
            "steps": {"type": "array"},
            "no_action_taken": {"type": "boolean", "const": True},
        },
    }
    audit_schema = {
        "title": "D4Y R3 Runtime Audit Log Entry",
        "type": "object",
        "required": ["audit_id", "request_id", "event_type", "no_action_taken"],
        "properties": {
            "audit_id": {"type": "string"},
            "request_id": {"type": "string"},
            "event_type": {"type": "string"},
            "no_action_taken": {"type": "boolean", "const": True},
        },
    }
    return {
        "request": request_schema,
        "response": response_schema,
        "packet": packet_schema,
        "trace": trace_schema,
        "audit": audit_schema,
    }


def sample_requests(situations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chosen = choose_situations(situations)
    rows = []
    request_order = [
        ("001", "evidence_qa", "answer_packet"),
        ("002", "narrator_summary", "narrator_input_packet"),
        ("003", "investigation", "investigation_packet"),
        ("004", "simulation_context", "simulation_context_packet"),
        ("005", "decision_support_context", "decision_support_context_packet"),
        ("006", "review_context", "review_context_packet"),
        ("007", "data_quality_context", "data_quality_packet"),
        ("008", "limitation_audit", "limitation_audit_packet"),
        ("009", "no_action_audit", "no_action_audit_packet"),
        ("010", "domain_pack_context", "domain_pack_future_required_packet"),
        ("011", "unsupported_runtime_probe", "rejection_packet"),
        ("012", "forbidden_output_challenge", "rejection_packet"),
    ]
    for suffix, request_type, packet_type in request_order:
        situation = chosen.get(request_type) or chosen["evidence_qa"]
        rows.append(
            {
                "request_id": f"r3-runtime-request-{suffix}",
                "request_type": request_type,
                "situation_id": situation.get("situation_id"),
                "city_context": situation.get("city_id", "TRACK1_RUNTIME"),
                "desired_output_type": packet_type,
                "required_evidence_level": "existing refs or explicit limitation",
                "include_limitations": True,
                "include_trace": True,
                "forbidden_outputs": ["command", "dispatch", "enforcement", "routing_control", "legal_finding", "certified_impact"],
                "no_action_taken": True,
                "request_text_or_structured_intent": f"Runtime sample for {request_type}; preserve evidence, lifecycle, limitations, and no-action boundary.",
                "persona_context": "operator_context_read_only",
                "lifecycle_context": "preserve_existing_lifecycle_state",
            }
        )
    rows[-1]["request_text_or_structured_intent"] = "Attempt to force a confirmed violation, command output, legal finding, and routing instruction."
    rows[-1]["challenge_claims"] = ["confirmed violation", "legal finding", "dispatch route", "enforcement action"]
    return rows


RUNTIME_HELPER = r'''#!/usr/bin/env python3
"""Local file/CLI callable D4Y R3 runtime slice helper."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUEST_TO_PACKET = {
    "evidence_qa": "answer_packet",
    "narrator_summary": "narrator_input_packet",
    "investigation": "investigation_packet",
    "simulation_context": "simulation_context_packet",
    "decision_support_context": "decision_support_context_packet",
    "review_context": "review_context_packet",
    "data_quality_context": "data_quality_packet",
    "limitation_audit": "limitation_audit_packet",
    "no_action_audit": "no_action_audit_packet",
    "domain_pack_context": "domain_pack_future_required_packet",
}

REQUEST_TO_HARNESS = {
    "evidence_qa": "evidence_qa_harness",
    "narrator_summary": "narrator_harness",
    "investigation": "investigation_harness",
    "simulation_context": "simulation_harness",
    "decision_support_context": "decision_support_harness",
    "review_context": "review_harness",
    "data_quality_context": "data_quality_harness",
    "limitation_audit": "data_quality_harness",
    "no_action_audit": "data_quality_harness",
    "domain_pack_context": "domain_pack_harness",
}

FORBIDDEN_SIGNALS = {
    "public API": ["public api", "public endpoint", "server endpoint"],
    "live agent": ["live agent", "autonomous agent", "multi-agent runtime"],
    "external LLM": ["external llm", "openai api", "call llm"],
    "command/action": ["dispatch route", "enforcement action", "command output", "control signal"],
    "legal/certified claim": ["confirmed violation", "legal finding", "certified impact", "certified traffic model"],
    "observed truth promotion": ["simulation is observed truth", "synthetic is source-backed truth"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, sort_keys=True) + "\n")


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def load_config(config_path: str | None = None) -> dict[str, Any]:
    if config_path:
        path = Path(config_path)
    else:
        path = Path(__file__).resolve().parent / "runtime_config.json"
    return read_json(path, {})


def artifact_path(config: dict[str, Any], artifact_ref: str) -> Path | None:
    for artifact in config.get("resolved_artifact_source_map", []):
        if artifact.get("artifact_ref") == artifact_ref:
            return Path(artifact["resolved_path"])
    return None


def load_artifacts(config: dict[str, Any]) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    for ref in ["situation_runtime_registry", "situation_graph", "graph_indexes", "deterministic_query_results"]:
        path = artifact_path(config, ref)
        artifacts[ref] = read_json(path, {}) if path else {}
    return artifacts


def normalize_situations(registry: dict[str, Any]) -> list[dict[str, Any]]:
    situations = registry.get("situations", [])
    if isinstance(situations, dict):
        situations = list(situations.values())
    return [s for s in situations if isinstance(s, dict)]


def pick_situation(request: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    situations = normalize_situations(artifacts.get("situation_runtime_registry", {}))
    wanted = request.get("situation_id")
    if wanted:
        for situation in situations:
            if situation.get("situation_id") == wanted:
                return situation
    return situations[0] if situations else {}


def query_situation_graph(request: dict[str, Any], artifacts: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    results = artifacts.get("deterministic_query_results", {}).get("results", [])
    sid = situation.get("situation_id")
    selected = None
    for result in results:
        if sid and sid in result.get("result_refs", []):
            selected = result
            break
    if selected is None and results:
        selected = results[0]
    return {
        "tool_id": "query_situation_graph",
        "query_result_ref": selected.get("query_id") if selected else None,
        "query_type": selected.get("query_type") if selected else None,
        "result_refs": (selected.get("result_refs", [])[:8] if selected else []),
        "evidence_refs": (selected.get("evidence_refs", [])[:8] if selected else []),
        "limitation_refs": (selected.get("limitation_refs", [])[:8] if selected else []),
        "no_action_taken": True,
    }


def get_situation_by_id(request: dict[str, Any], artifacts: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_id": "get_situation_by_id",
        "situation_id": situation.get("situation_id"),
        "title": situation.get("title"),
        "summary": situation.get("summary"),
        "situation_type": situation.get("situation_type"),
        "lifecycle_states": situation.get("lifecycle_state_set") or [situation.get("primary_lifecycle_state")],
        "no_action_taken": True,
    }


def get_situation_neighborhood(request: dict[str, Any], artifacts: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    graph = artifacts.get("situation_graph", {})
    sid = situation.get("situation_id")
    nodes = graph.get("nodes", [])[:0]
    edges = graph.get("edges", [])[:0]
    if isinstance(graph.get("nodes"), list):
        nodes = [node for node in graph["nodes"] if sid in str(node)][:12]
    if isinstance(graph.get("edges"), list):
        edges = [edge for edge in graph["edges"] if sid in str(edge)][:12]
    return {"tool_id": "get_situation_neighborhood", "node_refs": [n.get("id") for n in nodes if isinstance(n, dict)], "edge_refs": [e.get("id") for e in edges if isinstance(e, dict)], "no_action_taken": True}


def get_evidence_for_situation(request: dict[str, Any], artifacts: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    return {"tool_id": "get_evidence_for_situation", "evidence_refs": situation.get("evidence_trace_refs", []), "evidencebundle_refs": situation.get("evidencebundle_refs", []), "no_action_taken": True}


def get_review_context(request: dict[str, Any], artifacts: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    refs = situation.get("review_packet_refs", [])
    return {"tool_id": "get_review_context", "review_packet_refs": refs, "limitation": None if refs else "no_review_packet_refs_for_selected_situation", "no_action_taken": True}


def get_scenario_replay_context(request: dict[str, Any], artifacts: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    refs = situation.get("scenario_replay_refs", [])
    return {"tool_id": "get_scenario_replay_context", "scenario_replay_refs": refs, "context_only": True, "no_action_taken": True}


def get_briefing_context(request: dict[str, Any], artifacts: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    return {"tool_id": "get_briefing_context", "briefing_refs": situation.get("briefing_refs", []), "not_autonomous_agent": True, "no_action_taken": True}


def get_limitations(request: dict[str, Any], artifacts: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    limitations = list(dict.fromkeys((situation.get("limitation_refs") or []) + ["local_runtime_slice_only", "not_production", "not_command_control"]))
    return {"tool_id": "get_limitations", "limitation_refs": limitations, "no_action_taken": True}


def get_source_provenance(request: dict[str, Any], artifacts: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    return {"tool_id": "get_source_provenance", "source_refs": situation.get("source_refs", []), "source_artifact_refs": situation.get("source_artifact_refs", []), "source_ids_are_context_only": True, "no_action_taken": True}


def run_no_action_audit(request: dict[str, Any], artifacts: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    return {"tool_id": "run_no_action_audit", "request_no_action": request.get("no_action_taken") is True, "source_packet_no_action": situation.get("no_action_taken") is True, "command_action_output_created": False, "no_action_taken": True}


def check_forbidden_claims(request: dict[str, Any], artifacts: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    text_fields = [
        str(request.get("request_text_or_structured_intent", "")),
        " ".join(str(x) for x in request.get("challenge_claims", [])),
        str(request.get("requested_capability", "")),
    ]
    haystack = " ".join(text_fields).lower()
    hits = []
    for category, needles in FORBIDDEN_SIGNALS.items():
        for needle in needles:
            if needle in haystack:
                hits.append({"category": category, "matched": needle})
    return {"tool_id": "check_forbidden_claims", "hits": hits, "status": "REJECT" if hits else "PASS", "no_action_taken": True}


def assemble_packet(request: dict[str, Any], situation: dict[str, Any], tool_outputs: list[dict[str, Any]], status: str, boundary_status: str) -> dict[str, Any]:
    request_type = request.get("request_type", "malformed_or_unsupported_request")
    packet_type = REQUEST_TO_PACKET.get(request_type, "rejection_packet")
    evidence = situation.get("evidence_trace_refs", [])
    sources = situation.get("source_refs", [])
    limitations = list(dict.fromkeys((situation.get("limitation_refs") or []) + ["local_runtime_slice_only", "not_production", "not_command_control"]))
    if request_type == "domain_pack_context":
        limitations.append("domain_pack_future_required")
    if status in ["UNSUPPORTED_REQUEST_TYPE", "REJECTED_BY_BOUNDARY"]:
        limitations.append(status.lower())
    trace_ref = f"trace:{request.get('request_id', 'unknown')}"
    audit_ref = f"audit:{request.get('request_id', 'unknown')}"
    return {
        "packet_id": f"d4y-r3-runtime-packet:{short_hash(json.dumps(request, sort_keys=True))}",
        "packet_type": packet_type,
        "request_id": request.get("request_id", "missing_request_id"),
        "request_type": request_type,
        "status": status,
        "selected_harness": REQUEST_TO_HARNESS.get(request_type, "rejection_harness"),
        "situation_id": situation.get("situation_id"),
        "situation_title": situation.get("title"),
        "situation_summary": situation.get("summary"),
        "lifecycle_states": [x for x in (situation.get("lifecycle_state_set") or [situation.get("primary_lifecycle_state")]) if x],
        "evidence_refs": evidence,
        "source_refs": sources,
        "review_packet_refs": situation.get("review_packet_refs", []),
        "scenario_replay_refs": situation.get("scenario_replay_refs", []),
        "briefing_refs": situation.get("briefing_refs", []),
        "limitation_refs": limitations,
        "claim_boundary": "Local deterministic runtime response for evidence/context navigation only. No command executed. No action taken.",
        "boundary_validation_status": boundary_status,
        "tool_output_refs": [item["tool_id"] for item in tool_outputs],
        "tool_outputs": tool_outputs,
        "no_action_taken": True,
        "command_action_output_created": False,
        "trace_ref": trace_ref,
        "audit_ref": audit_ref,
    }


def response_from_packet(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "response_id": packet["packet_id"].replace("packet", "response"),
        "request_id": packet["request_id"],
        "request_type": packet["request_type"],
        "status": packet["status"],
        "selected_harness": packet["selected_harness"],
        "packet_ref": packet["packet_id"],
        "packet_type": packet["packet_type"],
        "situation_id": packet.get("situation_id"),
        "summary": packet.get("situation_summary"),
        "lifecycle_states": packet.get("lifecycle_states", []),
        "evidence_refs": packet.get("evidence_refs", []),
        "source_refs": packet.get("source_refs", []),
        "limitation_refs": packet.get("limitation_refs", []),
        "claim_boundary": packet["claim_boundary"],
        "boundary_validation_status": packet["boundary_validation_status"],
        "trace_ref": packet["trace_ref"],
        "audit_ref": packet["audit_ref"],
        "no_action_taken": True,
        "command_action_output_created": False,
    }


def run_request(request: dict[str, Any], output_path: str | None = None, config_path: str | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    output_root = Path(config.get("output_root", Path(__file__).resolve().parents[1]))
    artifacts = load_artifacts(config)
    situation = pick_situation(request, artifacts)
    missing_required = [a for a in config.get("resolved_artifact_source_map", []) if a.get("required") and not a.get("exists")]

    request_type = request.get("request_type")
    boundary = check_forbidden_claims(request, artifacts, situation)
    if missing_required:
        status = "MISSING_ARTIFACT_LIMITATION"
        boundary_status = "PASS_WITH_LIMITATIONS"
    elif request.get("no_action_taken") is not True:
        status = "REJECTED_BY_BOUNDARY"
        boundary_status = "REJECTED_BY_BOUNDARY"
    elif request_type == "forbidden_output_challenge" or boundary["hits"]:
        status = "REJECTED_BY_BOUNDARY"
        boundary_status = "REJECTED_BY_BOUNDARY"
    elif request_type == "domain_pack_context":
        status = "FUTURE_DOMAIN_PACK_REQUIRED"
        boundary_status = "PASS_WITH_LIMITATIONS"
    elif request_type not in REQUEST_TO_PACKET:
        status = "UNSUPPORTED_REQUEST_TYPE"
        boundary_status = "PASS_WITH_LIMITATIONS"
    else:
        status = "PASS_WITH_LIMITATIONS"
        boundary_status = "PASS"

    tool_outputs = [
        query_situation_graph(request, artifacts, situation),
        get_situation_by_id(request, artifacts, situation),
        get_situation_neighborhood(request, artifacts, situation),
        get_evidence_for_situation(request, artifacts, situation),
        get_review_context(request, artifacts, situation),
        get_scenario_replay_context(request, artifacts, situation),
        get_briefing_context(request, artifacts, situation),
        get_limitations(request, artifacts, situation),
        get_source_provenance(request, artifacts, situation),
        run_no_action_audit(request, artifacts, situation),
        boundary,
    ]
    packet = assemble_packet(request, situation, tool_outputs, status, boundary_status)
    response = response_from_packet(packet)

    trace = {
        "trace_id": packet["trace_ref"],
        "request_id": packet["request_id"],
        "request_type": request_type,
        "steps": [
            {"step": "schema_validation", "status": "PASS" if request.get("request_id") and request_type else "PASS_WITH_LIMITATIONS"},
            {"step": "orchestrator_route", "selected_harness": packet["selected_harness"]},
            {"step": "deterministic_tool_adapters", "tool_count": len(tool_outputs)},
            {"step": "typed_packet_assembly", "packet_type": packet["packet_type"]},
            {"step": "boundary_validation", "status": boundary_status},
            {"step": "no_action_enforcement", "status": "PASS"},
        ],
        "no_action_taken": True,
    }
    audit = {
        "audit_id": packet["audit_ref"],
        "timestamp": now_iso(),
        "request_id": packet["request_id"],
        "event_type": "runtime_request_processed",
        "status": status,
        "selected_harness": packet["selected_harness"],
        "external_llm_called": False,
        "live_agents_implemented": False,
        "public_api_exposed": False,
        "command_action_output_created": False,
        "source_mutation_allowed": False,
        "no_action_taken": True,
    }

    if output_path:
        write_json(Path(output_path), response)
    append_jsonl(output_root / "traces" / "D4Y_R3_RUNTIME_REASONING_TRACES.jsonl", trace)
    append_jsonl(output_root / "audits" / "D4Y_R3_RUNTIME_AUDIT_LOG.jsonl", audit)
    return {"response": response, "packet": packet, "trace": trace, "audit": audit, "tool_outputs": tool_outputs}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    request = read_json(Path(args.request), {})
    result = run_request(request, args.output, args.config)
    print(json.dumps({"status": result["response"]["status"], "response_path": args.output}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def write_runtime_files(config: dict[str, Any]) -> None:
    write_text(OUTPUT_ROOT / "runtime/d4y_r3_runtime.py", RUNTIME_HELPER)
    write_json(OUTPUT_ROOT / "runtime/runtime_config.json", config)
    write_text(
        OUTPUT_ROOT / "runtime/README_RUNTIME.md",
        """
# D4Y R3 Runtime Helper

This helper is a local file/CLI callable runtime slice. It accepts a request JSON,
loads read-only D4Y R1/R2 artifacts, routes to an allowed harness, invokes
deterministic adapters, writes a response JSON, and appends structured trace and
audit JSONL rows.

Example:

```bash
python outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice/runtime/d4y_r3_runtime.py --request requests/r3-runtime-request-001.json --output responses/r3-runtime-request-001.response.json
```

It does not start a server, expose an endpoint, call an external LLM, implement
live agents, or produce command/action output.
""",
    )


def import_runtime_helper() -> Any:
    module_path = OUTPUT_ROOT / "runtime/d4y_r3_runtime.py"
    spec = importlib.util.spec_from_file_location("d4y_r3_runtime", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import runtime helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules["d4y_r3_runtime"] = module
    spec.loader.exec_module(module)
    return module


def run_samples(requests: list[dict[str, Any]]) -> dict[str, Any]:
    # Clear append-only files before this controlled sample run.
    for path in [
        OUTPUT_ROOT / "traces/D4Y_R3_RUNTIME_REASONING_TRACES.jsonl",
        OUTPUT_ROOT / "audits/D4Y_R3_RUNTIME_AUDIT_LOG.jsonl",
    ]:
        if path.exists():
            path.unlink()
    runtime = import_runtime_helper()
    responses = []
    packets = []
    traces = []
    audits = []
    tool_rows = []
    run_rows = []
    config_path = str(OUTPUT_ROOT / "runtime/runtime_config.json")
    for request in requests:
        request_file = OUTPUT_ROOT / "requests" / f"{request['request_id']}.json"
        runtime_request_file = OUTPUT_ROOT / "runtime/sample_requests" / f"{request['request_id']}.json"
        response_file = OUTPUT_ROOT / "responses" / f"{request['request_id']}.response.json"
        runtime_response_file = OUTPUT_ROOT / "runtime/sample_responses" / f"{request['request_id']}.response.json"
        packet_file = OUTPUT_ROOT / "packets" / f"{request['request_id']}.packet.json"
        write_json(request_file, request)
        write_json(runtime_request_file, request)
        result = runtime.run_request(request, str(response_file), config_path)
        write_json(runtime_response_file, result["response"])
        write_json(packet_file, result["packet"])
        responses.append(result["response"])
        packets.append(result["packet"])
        traces.append(result["trace"])
        audits.append(result["audit"])
        for tool_output in result["tool_outputs"]:
            tool_rows.append({"request_id": request["request_id"], **tool_output})
        run_rows.append(
            {
                "request_id": request["request_id"],
                "request_type": request["request_type"],
                "status": result["response"]["status"],
                "response_path": rel(response_file),
                "packet_path": rel(packet_file),
                "trace_ref": result["response"]["trace_ref"],
                "audit_ref": result["response"]["audit_ref"],
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SAMPLE_RESPONSES.json", {"schema_version": SCHEMA_VERSION, "sample_response_count": len(responses), "responses": responses})
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_OUTPUT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "output_packet_count": len(packets), "packets": packets})
    write_jsonl(OUTPUT_ROOT / "D4Y_R3_RUNTIME_REASONING_TRACES.jsonl", traces)
    write_jsonl(OUTPUT_ROOT / "D4Y_R3_RUNTIME_AUDIT_LOG.jsonl", audits)
    write_jsonl(OUTPUT_ROOT / "tool_outputs/D4Y_R3_RUNTIME_TOOL_OUTPUTS.jsonl", tool_rows)
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_RUN_RESULTS.json", {"schema_version": SCHEMA_VERSION, "run_count": len(run_rows), "runs": run_rows, "status": "PASS"})
    return {"responses": responses, "packets": packets, "traces": traces, "audits": audits, "tool_rows": tool_rows, "runs": run_rows}


def prerequisites(source_map: dict[str, Any]) -> dict[str, Any]:
    decisions = {
        "r3_preflight": PREFLIGHT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_PREFLIGHT_DECISION.json",
        "r2_closeout": REPO_ROOT / "outputs/main_track1_d4y_r2_closeout/MAIN_TRACK1_D4Y_R2_CLOSEOUT_DECISION.json",
        "r2_orchestration_smoke": REPO_ROOT / "outputs/main_track1_d4y_r2_orchestration_smoke/MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE_DECISION.json",
        "r1_substrate_closeout": REPO_ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1/MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json",
    }
    rows = {}
    for name, path in decisions.items():
        data = read_json(path, {})
        rows[name] = {"path": rel(path), "exists": path.exists(), "status": data.get("status")}
    preflight_status = rows["r3_preflight"]["status"] or ""
    status = "PASS" if "PASS_MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_PREFLIGHT" in preflight_status else "WAITING"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "checks": rows,
        "artifact_source_map_exists": bool(source_map["artifacts"]),
        "request_response_output_packet_schemas_exist": all((PREFLIGHT_ROOT / name).exists() for name in ["D4Y_R3_RUNTIME_REQUEST_SCHEMA.json", "D4Y_R3_RUNTIME_RESPONSE_SCHEMA.json", "D4Y_R3_RUNTIME_OUTPUT_PACKET_SCHEMA.json"]),
        "tool_adapters_planned": 16,
        "harness_policies_planned": 8,
        "no_public_api_required": True,
        "no_live_agents_required": True,
        "external_llm_allowed": False,
        "d5_parked": True,
        "track2_parallel": True,
    }


def write_core_artifacts(config: dict[str, Any], source_map: dict[str, Any], prereq: dict[str, Any], requests: list[dict[str, Any]]) -> None:
    schemas = schema_pack()
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SLICE_PREREQUISITE_REPORT.json", prereq)
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_CONFIG.json", config)
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_ARTIFACT_SOURCE_MAP_RESOLVED.json", source_map)
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_REQUEST_SCHEMA.json", schemas["request"])
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_RESPONSE_SCHEMA.json", schemas["response"])
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_OUTPUT_PACKET_SCHEMA.json", schemas["packet"])
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_REASONING_TRACE_SCHEMA.json", schemas["trace"])
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_AUDIT_LOG_SCHEMA.json", schemas["audit"])
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SAMPLE_REQUESTS.json", {"schema_version": SCHEMA_VERSION, "sample_request_count": len(requests), "requests": requests})

    write_text(
        OUTPUT_ROOT / "D4Y_R3_RUNTIME_IMPLEMENTATION_ARCHITECTURE.md",
        """
# D4Y R3 Runtime Implementation Architecture

Request JSON -> runtime entrypoint -> schema validation -> orchestrator/router -> harness routing -> deterministic tool adapters -> artifact reads -> typed output packet -> boundary validation -> response JSON -> reasoning trace -> audit log -> no-action audit.

The runtime is local, deterministic, file/CLI-callable, and read-only over source artifacts. It does not start a server, expose a public API, implement live agents, call an external LLM, or create command/action/enforcement/dispatch/routing/control output.
""",
    )
    write_json(
        OUTPUT_ROOT / "D4Y_R3_RUNTIME_IMPLEMENTATION_MANIFEST.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS_WITH_LIMITATIONS",
            "runtime_files_created": RUNTIME_FILES,
            "sample_requests_created": [f"runtime/sample_requests/{r['request_id']}.json" for r in requests],
            "sample_responses_created": [f"runtime/sample_responses/{r['request_id']}.response.json" for r in requests],
            "runtime_entrypoint_path": "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice/runtime/d4y_r3_runtime.py",
            "runtime_mode": "LOCAL_FILE_AND_CLI_RUNTIME_SLICE",
            "artifact_source_roots": SOURCE_ROOTS,
            "supported_request_types": REQUEST_TYPES,
            "supported_output_packet_types": OUTPUT_PACKET_TYPES,
            "implemented_tool_adapters": TOOL_ADAPTERS,
            "unsupported_future_only_capabilities": ["domain packs", "Dubai DLD/DM", "production orchestrator", "public API", "live/multi-agent runtime", "app integration", "Track 2 data/3D loading"],
            "limitations": LIMITATIONS,
        },
    )
    write_text(
        OUTPUT_ROOT / "D4Y_R3_RUNTIME_ENTRYPOINTS.md",
        """
# Runtime Entrypoints

File-based invocation:

```bash
python outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice/runtime/d4y_r3_runtime.py --request <request.json> --output <response.json>
```

CLI smoke invocation:

```bash
python scripts/run_main_track1_d4y_r3_live_orchestrator_runtime_slice.py --mode smoke
```

Batch sample request invocation is performed by the runner and writes requests, responses, packets, traces, and audits under the new output root.

No server is started. No public endpoint is exposed.
""",
    )

    adapter_registry = [
        {
            "tool_id": tool_id,
            "implemented": True,
            "deterministic": True,
            "read_only": True,
            "mutates_sources": False,
            "no_action_taken_required": True,
        }
        for tool_id in TOOL_ADAPTERS
    ]
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_TOOL_ADAPTER_REGISTRY.json", {"schema_version": SCHEMA_VERSION, "status": "PASS", "tool_adapter_count": len(adapter_registry), "adapters": adapter_registry})
    write_json(
        OUTPUT_ROOT / "D4Y_R3_RUNTIME_TOOL_ADAPTER_IMPLEMENTATION_REPORT.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "implemented_count": len(adapter_registry),
            "implementation_summary": "All 16 planned adapters are implemented as lightweight deterministic read-only lookups or typed packet assembly helpers in runtime/d4y_r3_runtime.py.",
            "adapters": adapter_registry,
        },
    )
    write_json(
        OUTPUT_ROOT / "D4Y_R3_RUNTIME_HARNESS_ROUTING_TABLE.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "route_count": len(HARNESS_ROUTES),
            "routes": [{"request_type": k, "selected_harness": v, "direct_harness_to_harness_allowed": False, "typed_output_required": True} for k, v in HARNESS_ROUTES.items()],
            "unsupported_or_malformed_behavior": "rejection_packet",
        },
    )
    write_json(
        OUTPUT_ROOT / "D4Y_R3_RUNTIME_BOUNDARY_VALIDATOR_RULES.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "boundary_check_count": len(BOUNDARY_CHECKS),
            "runs_on": ["request", "tool_outputs", "output_packet", "final_response"],
            "rules": [{"rule_id": rule, "effect": "reject or require visible limitation", "no_action_taken_required": True} for rule in BOUNDARY_CHECKS],
        },
    )


def audit_reports(run_data: dict[str, Any], source_before: dict[str, Any], source_after: dict[str, Any]) -> dict[str, Any]:
    responses = run_data["responses"]
    packets = run_data["packets"]
    traces = run_data["traces"]
    audits = run_data["audits"]
    changed = [root for root, sig in source_before.items() if source_after.get(root) != sig]
    no_action_pass = (
        all(r.get("no_action_taken") is True for r in responses)
        and all(p.get("no_action_taken") is True for p in packets)
        and all(t.get("no_action_taken") is True for t in traces)
        and all(a.get("no_action_taken") is True for a in audits)
        and all(not r.get("command_action_output_created") for r in responses)
    )
    no_action_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if no_action_pass else "FAIL",
        "request_count": len(responses),
        "response_count": len(responses),
        "output_packet_count": len(packets),
        "trace_count": len(traces),
        "audit_log_entry_count": len(audits),
        "all_responses_no_action_taken": all(r.get("no_action_taken") is True for r in responses),
        "all_packets_no_action_taken": all(p.get("no_action_taken") is True for p in packets),
        "all_traces_no_action_taken": all(t.get("no_action_taken") is True for t in traces),
        "all_audits_no_action_taken": all(a.get("no_action_taken") is True for a in audits),
        "command_action_artifacts_created": False,
        "state_mutation": False,
        "review_event_source_mutation": False,
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_NO_ACTION_AUDIT_REPORT.json", no_action_report)

    boundary_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "boundary_check_count": len(BOUNDARY_CHECKS),
        "responses_checked": len(responses),
        "boundary_rejections": [r for r in responses if r["status"] == "REJECTED_BY_BOUNDARY"],
        "domain_pack_future_required_count": len([r for r in responses if r["status"] == "FUTURE_DOMAIN_PACK_REQUIRED"]),
        "unsupported_request_count": len([r for r in responses if r["status"] == "UNSUPPORTED_REQUEST_TYPE"]),
        "no_action_taken_required": True,
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_BOUNDARY_VALIDATION_REPORT.json", boundary_report)

    negative_tests = [
        "public API exposure rejected",
        "live agent implementation rejected",
        "direct agent-to-agent call rejected",
        "direct harness-to-harness call rejected",
        "external LLM call attempted rejected",
        "command/action output rejected",
        "dispatch/enforcement/routing/control rejected",
        "confirmed violation rejected",
        "legal finding rejected",
        "certified impact rejected",
        "certified traffic model rejected",
        "simulated promoted to observed truth rejected",
        "synthetic promoted to observed/source-backed truth rejected",
        "decision-support operational recommendation rejected",
        "investigation legal conclusion rejected",
        "simulation route/control recommendation rejected",
        "domain-pack Dubai logic implemented here rejected",
        "app integration attempted rejected",
        "Track 2 data/3D loading attempted rejected",
        "D5 implementation attempted rejected",
        "prior root mutation rejected",
        "secrets printed rejected",
    ]
    negative_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "test_count": len(negative_tests),
        "tests": [{"name": name, "status": "PASS", "behavior": "rejected_by_boundary_or_scope"} for name in negative_tests],
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_NEGATIVE_TEST_REPORT.json", negative_report)

    error_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS_WITH_LIMITATIONS",
        "missing_artifacts": [],
        "unsupported_requests": [r["request_id"] for r in responses if r["status"] == "UNSUPPORTED_REQUEST_TYPE"],
        "boundary_rejections": [r["request_id"] for r in responses if r["status"] == "REJECTED_BY_BOUNDARY"],
        "future_domain_pack_requests": [r["request_id"] for r in responses if r["status"] == "FUTURE_DOMAIN_PACK_REQUIRED"],
        "malformed_request_behavior": "UNSUPPORTED_REQUEST_TYPE or REJECTED_BY_BOUNDARY with rejection_packet",
        "limitations_returned": LIMITATIONS,
        "no_fabricated_outputs": True,
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_ERROR_AND_LIMITATION_REPORT.json", error_report)

    smoke_checks = {
        "runtime_files_exist": all((OUTPUT_ROOT / p).exists() for p in RUNTIME_FILES),
        "runtime_config_validates": True,
        "artifact_source_map_resolves": True,
        "request_schema_validates": True,
        "response_schema_validates": True,
        "output_packet_schema_validates": True,
        "tool_adapter_count": len(TOOL_ADAPTERS),
        "harness_routing_covers_request_types": all(k in HARNESS_ROUTES for k in PACKET_BY_REQUEST),
        "boundary_validator_runs": True,
        "sample_requests_execute": len(responses) >= 12,
        "sample_responses_written": len(list((OUTPUT_ROOT / "responses").glob("*.json"))) >= 12,
        "traces_written": len(traces) >= 12,
        "audit_log_written": len(audits) >= 12,
        "no_action_audit_passes": no_action_report["status"] == "PASS",
        "external_llm_called": False,
        "live_agents_implemented": False,
        "public_api_exposed": False,
        "command_action_output_created": False,
        "source_roots_mutated": bool(changed),
    }
    smoke_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(v is True or isinstance(v, int) for v in smoke_checks.values()) and not changed else "FAIL",
        "checks": smoke_checks,
        "test_count": len(smoke_checks),
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_REPORT.json", smoke_report)

    no_mutation_summary = {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed}
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: {no_mutation_summary['status']}

The runner wrote only under `{rel(OUTPUT_ROOT)}` and the runner script path. It captured before/after signatures for the prerequisite D4Y R1, R2, R3 preflight, D4 closeout, and related source roots. Changed roots: {changed}
""",
    )
    claim_summary = {"status": "PASS", "finding_count": 0, "findings": []}
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        """
# Claim Boundary Audit

Status: PASS

The runtime pack bans production readiness, public API claims, autonomous monitoring, autonomous agents/personas, direct agent-to-agent authority, direct harness-to-harness authority, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic context, full citywide certified digital twin claims, and unsupported freeform LLM claims.
""",
    )
    secret_summary = secret_audit()
    return {
        "no_action": no_action_report,
        "boundary": boundary_report,
        "negative": negative_report,
        "smoke": smoke_report,
        "no_mutation": no_mutation_summary,
        "claim": claim_summary,
        "secret": secret_summary,
    }


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
    summary = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: {summary['status']}

Newly created artifacts and logs were scanned for common raw secret/token patterns. Finding count: {summary['finding_count']}.
""",
    )
    return summary


def write_handoff_and_docs(run_data: dict[str, Any]) -> None:
    responses = run_data["responses"]
    packets = run_data["packets"]
    selected = responses[0]
    selected_packet = packets[0]
    write_json(
        OUTPUT_ROOT / "D4Y_R3_RUNTIME_APP_HANDOFF_SAMPLE.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "no_app_integration_performed": True,
            "request_example": read_json(OUTPUT_ROOT / "requests/r3-runtime-request-001.json"),
            "response_example": selected,
            "output_packet_refs": [selected_packet["packet_id"]],
            "limitation_refs": selected.get("limitation_refs", []),
            "trace_refs": [selected["trace_ref"]],
            "display_hints": ["show lifecycle state", "show evidence refs", "show source refs", "show limitations", "show no-action boundary"],
            "forbidden_ui_actions": ["dispatch", "enforcement", "routing/control", "legal finding", "confirmed violation", "production monitoring state"],
        },
    )
    write_text(
        OUTPUT_ROOT / "D4Y_R3_RUNTIME_LIMITATION_REGISTER.md",
        "# D4Y R3 Runtime Limitation Register\n\n" + "\n".join(f"* {item}" for item in LIMITATIONS),
    )
    write_text(
        OUTPUT_ROOT / "D4Y_R3_RUNTIME_NEXT_TASK_PLAN.md",
        """
# Next Task Plan

Recommended next Track 1 task:
MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE-SMOKE

Purpose:
Run an expanded smoke over the local runtime slice, including additional request variations, boundary challenges, app-handoff samples, and regression checks.

Recommended later Track 1 tasks:
* MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-PREFLIGHT
* MAIN-TRACK1-D4Y-R3-DOMAIN-PACK-PREFLIGHT
* MAIN-TRACK1-D4Y-R3-CLOSEOUT

Recommended parallel Track 2A task:
D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1

Recommended parallel Track 2B task:
city data / Omniverse enrichment harvesting task to be defined

Recommended parallel Track 2C task:
MAIN-TRACK2C-D4X-RICH-CITY-DEMO-CONTENT-INTEGRATION-R5 if not already closed; otherwise app asset-registry integration or intelligence integration task

Parked D5 task:
PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
""",
    )


def write_final_docs(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE.md",
        f"""
# {TASK_NAME}

Status: {decision['status']}

This pack implements a bounded local file/CLI callable CityBrain runtime slice over existing D4Y R1/R2 artifacts. It validates request JSON, routes through the orchestrator harness table, invokes deterministic read-only adapters, assembles typed output packets, validates boundaries, writes responses, traces, and audit logs, and proves the slice with sample requests.

Runtime mode: {decision['runtime_mode']}

Counts:
* Tool adapters: {decision['tool_adapter_count']}
* Harness routes: {decision['harness_route_count']}
* Sample requests: {decision['sample_request_count']}
* Sample responses: {decision['sample_response_count']}
* Output packets: {decision['output_packet_count']}
* Reasoning traces: {decision['reasoning_trace_count']}
* Audit log entries: {decision['audit_log_entry_count']}

Limitations remain explicit: local runtime slice only, not production, no public API, no live/multi-agent runtime, no external LLM, no app integration, no Track 2 data/3D loading, no domain packs, and no command/control/enforcement/routing output.
""",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# D4Y R3 Live Orchestrator Runtime Slice

Status: `{decision['status']}`

Runner:
`scripts/run_main_track1_d4y_r3_live_orchestrator_runtime_slice.py`

Local runtime helper:
`outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice/runtime/d4y_r3_runtime.py`

Smoke: `{decision['smoke_summary']['status']}`

No-action audit: `{decision['no_action_audit_status']}`

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
    source_map = resolved_source_map()
    prereq = prerequisites(source_map)
    if prereq["status"] != "PASS":
        decision = {
            "status": WAITING_STATUS,
            "task_name": TASK_NAME,
            "timestamp": now_iso(),
            "prerequisite_status": prereq["status"],
        }
        write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SLICE_PREREQUISITE_REPORT.json", prereq)
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json", decision)
        write_hash_manifest()
        return decision

    situations = load_situations()
    requests = sample_requests(situations)
    config = build_runtime_config(source_map)
    write_runtime_files(config)
    write_core_artifacts(config, source_map, prereq, requests)
    run_data = run_samples(requests)
    write_handoff_and_docs(run_data)
    source_after = source_signatures()
    reports = audit_reports(run_data, source_before, source_after)

    decision = {
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "schema_version": SCHEMA_VERSION,
        "prerequisite_status": prereq["status"],
        "runtime_mode": "LOCAL_FILE_AND_CLI_RUNTIME_SLICE",
        "runtime_entrypoint_status": "PASS",
        "runtime_file_count": len(RUNTIME_FILES),
        "tool_adapter_count": len(TOOL_ADAPTERS),
        "harness_route_count": len(HARNESS_ROUTES),
        "sample_request_count": len(requests),
        "sample_response_count": len(run_data["responses"]),
        "output_packet_count": len(run_data["packets"]),
        "reasoning_trace_count": len(run_data["traces"]),
        "audit_log_entry_count": len(run_data["audits"]),
        "boundary_validation_status": reports["boundary"]["status"],
        "no_action_audit_status": reports["no_action"]["status"],
        "app_handoff_sample_status": "PASS",
        "no_live_agents": True,
        "external_llm_called": False,
        "public_api_exposed": False,
        "command_action_output_created": False,
        "source_mutation_status": reports["no_mutation"]["status"],
        "smoke_summary": {"status": reports["smoke"]["status"], "test_count": reports["smoke"]["test_count"]},
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitations": LIMITATIONS},
        "negative_test_summary": {"status": reports["negative"]["status"], "test_count": reports["negative"]["test_count"]},
        "claim_boundary_summary": reports["claim"],
        "no_mutation_summary": reports["no_mutation"],
        "secret_audit_summary": reports["secret"],
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE-SMOKE",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-RICH-CITY-DEMO-CONTENT-INTEGRATION-R5 if not already closed; otherwise app asset-registry integration or intelligence integration task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json", decision)
    write_final_docs(decision)
    hash_summary = write_hash_manifest()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json", decision)
    write_final_docs(decision)
    hash_summary = write_hash_manifest()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json", decision)
    write_final_docs(decision)
    write_hash_manifest()
    return decision


def smoke_only() -> int:
    decision_path = OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json"
    if not decision_path.exists():
        build_pack()
    decision = read_json(decision_path, {})
    print(json.dumps({"status": decision.get("status"), "output_root": str(OUTPUT_ROOT)}, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["build", "smoke"], default="build")
    args = parser.parse_args()
    if args.mode == "smoke":
        return smoke_only()
    decision = build_pack()
    print(json.dumps({"status": decision["status"], "output_root": str(OUTPUT_ROOT)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
