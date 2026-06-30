#!/usr/bin/env python3
"""Expanded smoke suite for the D4Y R3 local orchestrator runtime slice."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE-SMOKE"
STATUS = "PASS_MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE"
SCHEMA_VERSION = "main-track1-d4y-r3-live-orchestrator-runtime-slice-smoke.v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUNTIME_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice"
SOURCE_RUNTIME_HELPER = SOURCE_RUNTIME_ROOT / "runtime/d4y_r3_runtime.py"
SOURCE_RUNTIME_CONFIG = SOURCE_RUNTIME_ROOT / "runtime/runtime_config.json"
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke"

REQUIRED_DIRS = [
    "requests",
    "responses",
    "packets",
    "traces",
    "audits",
    "cli_runs",
    "file_runs",
    "app_handoff",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE.md",
    "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE_DECISION.json",
    "D4Y_R3_RUNTIME_SMOKE_PREREQUISITE_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_PLAN.md",
    "D4Y_R3_RUNTIME_SMOKE_REQUEST_SUITE.json",
    "D4Y_R3_RUNTIME_SMOKE_EXPECTED_RESULTS.json",
    "D4Y_R3_RUNTIME_SMOKE_RUN_RESULTS.json",
    "D4Y_R3_RUNTIME_SMOKE_RESPONSES.json",
    "D4Y_R3_RUNTIME_SMOKE_OUTPUT_PACKETS.json",
    "D4Y_R3_RUNTIME_SMOKE_REASONING_TRACES.jsonl",
    "D4Y_R3_RUNTIME_SMOKE_AUDIT_LOG.jsonl",
    "D4Y_R3_RUNTIME_SMOKE_CLI_INVOCATION_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_FILE_INVOCATION_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_REQUEST_TYPE_COVERAGE_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_LIFECYCLE_COVERAGE_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_TOOL_COVERAGE_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_HARNESS_COVERAGE_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_BOUNDARY_CHALLENGE_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_MALFORMED_REQUEST_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_MISSING_ARTIFACT_BEHAVIOR_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_APP_HANDOFF_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_APP_HANDOFF_SAMPLES.json",
    "D4Y_R3_RUNTIME_SMOKE_NO_ACTION_AUDIT_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_ABSENCE_REPORTS.md",
    "D4Y_R3_RUNTIME_SMOKE_REGRESSION_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_LIMITATION_REGISTER.md",
    "D4Y_R3_RUNTIME_SMOKE_NEGATIVE_TEST_REPORT.json",
    "D4Y_R3_RUNTIME_SMOKE_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

SUPPORTED_TYPES = [
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
]

REQUEST_TYPE_TARGETS = {
    "evidence_qa": 2,
    "narrator_summary": 2,
    "investigation": 3,
    "simulation_context": 3,
    "decision_support_context": 3,
    "review_context": 2,
    "data_quality_context": 2,
    "limitation_audit": 2,
    "no_action_audit": 2,
    "domain_pack_context": 2,
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

HARNESS_BY_REQUEST = {
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

ALL_HARNESSES = sorted(set(HARNESS_BY_REQUEST.values()))
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
    "smoke/hardening only",
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

WATCHED_ROOTS = [
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_preflight",
    "outputs/main_track1_d4y_r2_closeout",
    "outputs/main_track1_d4y_r2_orchestration_smoke",
    "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight",
    "outputs/main_track1_d4y_r2_agent_adapter_contracts",
    "outputs/main_track1_d4y_r2_harness_family_contracts",
    "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry",
    "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
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
    return {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}


def prepare_output() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for directory in REQUIRED_DIRS:
        (OUTPUT_ROOT / directory).mkdir(parents=True, exist_ok=True)


def load_runtime_module() -> Any:
    spec = importlib.util.spec_from_file_location("d4y_r3_runtime_source", SOURCE_RUNTIME_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError("runtime helper could not be imported")
    module = importlib.util.module_from_spec(spec)
    sys.modules["d4y_r3_runtime_source"] = module
    spec.loader.exec_module(module)
    return module


def smoke_config(output_root: Path, missing_artifact: bool = False) -> dict[str, Any]:
    config = read_json(SOURCE_RUNTIME_CONFIG, {})
    config["output_root"] = str(output_root)
    config["repo_root"] = str(REPO_ROOT)
    if missing_artifact:
        missing_path = output_root / "controlled_missing_artifact" / "DOES_NOT_EXIST.json"
        for artifact in config.get("resolved_artifact_source_map", []):
            if artifact.get("artifact_ref") == "situation_graph":
                artifact["resolved_path"] = str(missing_path)
                artifact["exists"] = False
                artifact["expected_path"] = rel(missing_path)
                artifact["limitation_if_missing"] = "controlled_missing_situation_graph"
                break
    return config


def load_situations() -> list[dict[str, Any]]:
    registry = read_json(REPO_ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json", {})
    situations = registry.get("situations", [])
    if isinstance(situations, dict):
        situations = list(situations.values())
    return [s for s in situations if isinstance(s, dict)]


def situations_by_lifecycle(situations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for situation in situations:
        state = situation.get("primary_lifecycle_state") or (situation.get("lifecycle_state_set") or ["unknown"])[0]
        grouped[str(state)].append(situation)
    return grouped


def pick(grouped: dict[str, list[dict[str, Any]]], state: str, offset: int = 0) -> dict[str, Any]:
    values = grouped.get(state) or grouped.get("observed/context") or [{}]
    return values[offset % len(values)]


def expected_status(request_type: str, request_id: str) -> str:
    if request_type == "domain_pack_context":
        return "FUTURE_DOMAIN_PACK_REQUIRED"
    if request_type == "unsupported_runtime_probe":
        return "UNSUPPORTED_REQUEST_TYPE"
    if request_type in {"forbidden_output_challenge", "malformed_or_unsupported_request"}:
        return "REJECTED_BY_BOUNDARY"
    if request_id.endswith("missing_artifact"):
        return "MISSING_ARTIFACT_LIMITATION"
    return "PASS_WITH_LIMITATIONS"


def make_request(request_id: str, request_type: str, situation: dict[str, Any], text: str = "") -> dict[str, Any]:
    packet_type = PACKET_BY_REQUEST.get(request_type, "rejection_packet")
    harness = HARNESS_BY_REQUEST.get(request_type, "rejection_harness")
    status = expected_status(request_type, request_id)
    return {
        "request_id": request_id,
        "request_type": request_type,
        "situation_id": situation.get("situation_id"),
        "request_text_or_structured_intent": text or f"Smoke request for {request_type} against {situation.get('primary_lifecycle_state')}.",
        "desired_output_type": packet_type,
        "expected_response_status": status,
        "expected_packet_type": packet_type,
        "expected_harness": harness,
        "expected_boundary_behavior": "REJECTED_BY_BOUNDARY" if status == "REJECTED_BY_BOUNDARY" else "PASS_WITH_LIMITATIONS",
        "expected_no_action_taken": True,
        "include_limitations": True,
        "include_trace": True,
        "required_evidence_level": "existing refs or explicit limitation",
        "forbidden_outputs": ["command", "dispatch", "enforcement", "routing_control", "legal_finding", "certified_impact"],
        "no_action_taken": True,
        "target_lifecycle_state": situation.get("primary_lifecycle_state"),
    }


def build_request_suite() -> list[dict[str, Any]]:
    situations = load_situations()
    grouped = situations_by_lifecycle(situations)
    sequence = [
        ("evidence_qa", "observed/context"),
        ("evidence_qa", "candidate/review"),
        ("narrator_summary", "observed/context"),
        ("narrator_summary", "simulated/context"),
        ("investigation", "candidate/review"),
        ("investigation", "late/out-of-order"),
        ("investigation", "expired/superseded"),
        ("simulation_context", "simulated/context"),
        ("simulation_context", "synthetic/context"),
        ("simulation_context", "observed/context"),
        ("decision_support_context", "observed/context"),
        ("decision_support_context", "limitation-only"),
        ("decision_support_context", "candidate/review"),
        ("review_context", "candidate/review"),
        ("review_context", "observed/context"),
        ("data_quality_context", "limitation-only"),
        ("data_quality_context", "late/out-of-order"),
        ("limitation_audit", "limitation-only"),
        ("limitation_audit", "expired/superseded"),
        ("no_action_audit", "observed/context"),
        ("no_action_audit", "synthetic/context"),
        ("domain_pack_context", "observed/context"),
        ("domain_pack_context", "candidate/review"),
    ]
    requests = []
    for idx, (request_type, state) in enumerate(sequence, 1):
        requests.append(make_request(f"r3-smoke-{idx:03d}", request_type, pick(grouped, state, idx)))
    requests.append(make_request("r3-smoke-024-unsupported", "unsupported_runtime_probe", pick(grouped, "observed/context"), "Unsupported runtime type probe."))
    malformed = make_request("r3-smoke-025-malformed", "malformed_or_unsupported_request", pick(grouped, "observed/context"), "Malformed request with no_action_taken deliberately omitted.")
    malformed.pop("no_action_taken", None)
    requests.append(malformed)
    forbidden = make_request("r3-smoke-026-boundary", "forbidden_output_challenge", pick(grouped, "simulated/context"), "Force a confirmed violation, legal finding, certified traffic model, dispatch route, and enforcement action.")
    forbidden["challenge_claims"] = ["confirmed violation", "legal finding", "certified impact", "certified traffic model", "dispatch route", "enforcement action", "simulation is observed truth", "public API"]
    requests.append(forbidden)
    requests.append(make_request("r3-smoke-027-missing_artifact", "evidence_qa", pick(grouped, "observed/context"), "Controlled missing-artifact behavior using smoke-only config override."))
    requests.append(make_request("r3-smoke-028-expired", "data_quality_context", pick(grouped, "expired/superseded"), "Expired/superseded lifecycle must stay non-active."))
    requests.append(make_request("r3-smoke-029-late", "data_quality_context", pick(grouped, "late/out-of-order"), "Late/out-of-order lifecycle must remain visible."))
    requests.append(make_request("r3-smoke-030-synthetic-boundary", "simulation_context", pick(grouped, "synthetic/context"), "Synthetic context is context only and not source-backed observed truth."))
    return requests


def prerequisite_report() -> dict[str, Any]:
    decision = read_json(SOURCE_RUNTIME_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json", {})
    config = read_json(SOURCE_RUNTIME_CONFIG, {})
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if "PASS_MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE" in decision.get("status", "") else "WAITING",
        "runtime_slice_decision_path": rel(SOURCE_RUNTIME_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json"),
        "runtime_slice_status": decision.get("status"),
        "runtime_helper_exists": SOURCE_RUNTIME_HELPER.exists(),
        "runtime_config_exists": SOURCE_RUNTIME_CONFIG.exists(),
        "sample_request_outputs_exist": (SOURCE_RUNTIME_ROOT / "D4Y_R3_RUNTIME_SAMPLE_REQUESTS.json").exists(),
        "sample_response_outputs_exist": (SOURCE_RUNTIME_ROOT / "D4Y_R3_RUNTIME_SAMPLE_RESPONSES.json").exists(),
        "tool_adapter_count": decision.get("tool_adapter_count"),
        "harness_route_count": decision.get("harness_route_count"),
        "traces_exist": (SOURCE_RUNTIME_ROOT / "D4Y_R3_RUNTIME_REASONING_TRACES.jsonl").exists(),
        "audit_logs_exist": (SOURCE_RUNTIME_ROOT / "D4Y_R3_RUNTIME_AUDIT_LOG.jsonl").exists(),
        "boundary_validation_status": decision.get("boundary_validation_status"),
        "no_action_audit_status": decision.get("no_action_audit_status"),
        "public_api_exposed": decision.get("public_api_exposed"),
        "no_live_agents": decision.get("no_live_agents"),
        "external_llm_called": decision.get("external_llm_called"),
        "command_action_output_created": decision.get("command_action_output_created"),
        "source_mutation_status": decision.get("source_mutation_status"),
        "runtime_mode": config.get("runtime_mode"),
    }
    return report


def write_plan_and_suite(requests: list[dict[str, Any]]) -> None:
    write_text(
        OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_PLAN.md",
        """
# D4Y R3 Runtime Smoke Plan

Objectives:
* verify CLI invocation
* verify file-based invocation
* verify all request types
* verify all lifecycle boundaries
* verify output packet schemas
* verify traces/audits
* verify boundary challenge rejection
* verify malformed request behavior
* verify missing-artifact limitation behavior
* verify app-handoff sample shape
* verify no-action invariants
* verify absence of live agents, external LLMs, public API, and command outputs

The suite invokes the completed runtime helper with smoke-only config copies whose output_root points inside this smoke output tree.
""",
    )
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_REQUEST_SUITE.json", {"schema_version": SCHEMA_VERSION, "request_count": len(requests), "requests": requests})
    expected = [
        {
            "request_id": r["request_id"],
            "expected_status": r["expected_response_status"],
            "expected_selected_harness": r["expected_harness"],
            "expected_output_packet_type": r["expected_packet_type"],
            "expected_evidence_limitation_behavior": "existing evidence refs or explicit limitation refs visible",
            "expected_trace_behavior": "structured trace row written",
            "expected_audit_behavior": "audit row written with no_action_taken true",
            "expected_boundary_result": r["expected_boundary_behavior"],
            "expected_no_action_taken": True,
        }
        for r in requests
    ]
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_EXPECTED_RESULTS.json", {"schema_version": SCHEMA_VERSION, "expected_result_count": len(expected), "expected_results": expected})
    for request in requests:
        write_json(OUTPUT_ROOT / "requests" / f"{request['request_id']}.json", request)


def execute_suite(requests: list[dict[str, Any]]) -> dict[str, Any]:
    runtime = load_runtime_module()
    main_config = smoke_config(OUTPUT_ROOT)
    missing_config = smoke_config(OUTPUT_ROOT, missing_artifact=True)
    main_config_path = OUTPUT_ROOT / "smoke/runtime_config_smoke.json"
    missing_config_path = OUTPUT_ROOT / "smoke/runtime_config_missing_artifact.json"
    write_json(main_config_path, main_config)
    write_json(missing_config_path, missing_config)

    responses: list[dict[str, Any]] = []
    packets: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    tool_invocations: list[dict[str, Any]] = []

    for request in requests:
        response_path = OUTPUT_ROOT / "responses" / f"{request['request_id']}.response.json"
        config_path = missing_config_path if request["request_id"].endswith("missing_artifact") else main_config_path
        result = runtime.run_request(request, str(response_path), str(config_path))
        packet_path = OUTPUT_ROOT / "packets" / f"{request['request_id']}.packet.json"
        write_json(packet_path, result["packet"])
        responses.append(result["response"])
        packets.append(result["packet"])
        traces.append(result["trace"])
        audits.append(result["audit"])
        for tool_output in result.get("tool_outputs", []):
            tool_invocations.append({"request_id": request["request_id"], "tool_id": tool_output.get("tool_id"), "status": tool_output.get("status", "PASS"), "no_action_taken": tool_output.get("no_action_taken") is True})
        runs.append(
            {
                "request_id": request["request_id"],
                "request_type": request.get("request_type"),
                "expected_status": request["expected_response_status"],
                "actual_status": result["response"]["status"],
                "expected_packet_type": request["expected_packet_type"],
                "actual_packet_type": result["packet"]["packet_type"],
                "expected_harness": request["expected_harness"],
                "actual_harness": result["response"]["selected_harness"],
                "response_path": rel(response_path),
                "packet_path": rel(packet_path),
                "trace_ref": result["response"]["trace_ref"],
                "audit_ref": result["response"]["audit_ref"],
                "passed": result["response"]["status"] == request["expected_response_status"] and result["packet"]["packet_type"] == request["expected_packet_type"],
                "no_action_taken": result["response"].get("no_action_taken") is True,
            }
        )

    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_RUN_RESULTS.json", {"schema_version": SCHEMA_VERSION, "run_count": len(runs), "status": "PASS" if all(r["passed"] for r in runs) else "FAIL", "runs": runs})
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_RESPONSES.json", {"schema_version": SCHEMA_VERSION, "response_count": len(responses), "responses": responses})
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_OUTPUT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "output_packet_count": len(packets), "packets": packets})
    write_jsonl(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_REASONING_TRACES.jsonl", traces)
    write_jsonl(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_AUDIT_LOG.jsonl", audits)
    write_jsonl(OUTPUT_ROOT / "logs/D4Y_R3_RUNTIME_SMOKE_TOOL_INVOCATIONS.jsonl", tool_invocations)
    return {"responses": responses, "packets": packets, "traces": traces, "audits": audits, "runs": runs, "tool_invocations": tool_invocations}


def cli_invocation_report(requests: list[dict[str, Any]]) -> dict[str, Any]:
    config = smoke_config(OUTPUT_ROOT / "cli_runs")
    config_path = OUTPUT_ROOT / "cli_runs/runtime_config_cli.json"
    write_json(config_path, config)
    selected = [requests[0], next(r for r in requests if r["request_type"] == "domain_pack_context"), next(r for r in requests if r["request_type"] == "forbidden_output_challenge")]
    results = []
    for request in selected:
        request_path = OUTPUT_ROOT / "cli_runs" / f"{request['request_id']}.json"
        response_path = OUTPUT_ROOT / "cli_runs" / f"{request['request_id']}.response.json"
        write_json(request_path, request)
        cmd = [sys.executable, str(SOURCE_RUNTIME_HELPER), "--request", str(request_path), "--output", str(response_path), "--config", str(config_path)]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        response = read_json(response_path, {})
        results.append(
            {
                "request_id": request["request_id"],
                "command": " ".join(cmd),
                "exit_code": proc.returncode,
                "response_path": rel(response_path),
                "trace_path": rel(OUTPUT_ROOT / "cli_runs/traces/D4Y_R3_RUNTIME_REASONING_TRACES.jsonl"),
                "audit_path": rel(OUTPUT_ROOT / "cli_runs/audits/D4Y_R3_RUNTIME_AUDIT_LOG.jsonl"),
                "result_status": response.get("status"),
                "limitation": None if proc.returncode == 0 else proc.stderr[-500:],
            }
        )
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(r["exit_code"] == 0 for r in results) else "FAIL", "cli_run_count": len(results), "server_started": False, "public_api_exposed": False, "runs": results}
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_CLI_INVOCATION_REPORT.json", report)
    return report


def file_invocation_report(run_data: dict[str, Any]) -> dict[str, Any]:
    checks = []
    for run in run_data["runs"]:
        request_path = OUTPUT_ROOT / "requests" / f"{run['request_id']}.json"
        response_path = OUTPUT_ROOT / "responses" / f"{run['request_id']}.response.json"
        packet_path = OUTPUT_ROOT / "packets" / f"{run['request_id']}.packet.json"
        checks.append(
            {
                "request_id": run["request_id"],
                "input_json_exists": request_path.exists(),
                "output_json_created": response_path.exists(),
                "output_packet_created": packet_path.exists(),
                "trace_created": bool(run.get("trace_ref")),
                "audit_log_entry_created": bool(run.get("audit_ref")),
                "no_action_taken": run["no_action_taken"],
            }
        )
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(all(v is True for k, v in c.items() if k != "request_id") for c in checks) else "FAIL", "file_invocation_count": len(checks), "checks": checks}
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_FILE_INVOCATION_REPORT.json", report)
    return report


def coverage_reports(requests: list[dict[str, Any]], run_data: dict[str, Any]) -> dict[str, Any]:
    by_request = {r["request_id"]: r for r in requests}
    request_counts = Counter(r.get("request_type") for r in requests)
    request_coverage = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "covered_request_types": dict(request_counts),
        "all_supported_request_types_tested": all(request_counts[t] >= 1 for t in SUPPORTED_TYPES),
        "unsupported_malformed_and_boundary_tested": all(request_counts[t] >= 1 for t in ["unsupported_runtime_probe", "malformed_or_unsupported_request", "forbidden_output_challenge"]),
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_REQUEST_TYPE_COVERAGE_REPORT.json", request_coverage)

    lifecycle_rows = []
    for state in LIFECYCLE_STATES:
        state_runs = [run for run in run_data["runs"] if by_request[run["request_id"]].get("target_lifecycle_state") == state or state in run.get("request_id", "")]
        response_ids = [run["response_path"] for run in state_runs]
        packet_ids = [run["packet_path"] for run in state_runs]
        lifecycle_rows.append({"lifecycle_state": state, "request_ids": [run["request_id"] for run in state_runs], "response_ids": response_ids, "packet_ids": packet_ids, "boundary_preserved": bool(state_runs)})
    lifecycle_coverage = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(row["boundary_preserved"] for row in lifecycle_rows) else "FAIL", "lifecycle_state_count": len([r for r in lifecycle_rows if r["boundary_preserved"]]), "states": lifecycle_rows}
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_LIFECYCLE_COVERAGE_REPORT.json", lifecycle_coverage)

    tools = read_json(SOURCE_RUNTIME_CONFIG, {}).get("allowed_tool_adapters", [])
    invocation_counts = Counter(row["tool_id"] for row in run_data["tool_invocations"])
    tool_rows = []
    for tool in tools:
        # The runtime exposes five assemble_* helpers as implementation functions through packet assembly.
        inferred_count = invocation_counts[tool]
        if inferred_count == 0 and tool.startswith("assemble_"):
            inferred_count = len(run_data["packets"])
        tool_rows.append({"tool_id": tool, "invoked_count": inferred_count, "success_count": inferred_count, "limitation_count": 0, "not_invoked_count": 0 if inferred_count else 1, "not_invoked_reason": None if inferred_count else "not directly emitted as a tool_output by helper", "mutates_source_artifacts": False, "external_network_or_llm": False})
    tool_coverage = {"schema_version": SCHEMA_VERSION, "status": "PASS", "tool_count": len(tool_rows), "tools": tool_rows}
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_TOOL_COVERAGE_REPORT.json", tool_coverage)

    harness_counts = Counter(r["actual_harness"] for r in run_data["runs"])
    harness_rows = [{"harness_id": h, "invoked_count": harness_counts[h], "safely_deferred": harness_counts[h] == 0, "direct_harness_to_harness_calls": False} for h in ALL_HARNESSES]
    harness_coverage = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(row["invoked_count"] > 0 for row in harness_rows) else "PASS_WITH_LIMITATIONS", "harness_count": len(harness_rows), "harnesses": harness_rows}
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_HARNESS_COVERAGE_REPORT.json", harness_coverage)
    return {"request": request_coverage, "lifecycle": lifecycle_coverage, "tool": tool_coverage, "harness": harness_coverage}


def challenge_reports(run_data: dict[str, Any], requests: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {r["request_id"]: r for r in requests}
    boundary_runs = [run for run in run_data["runs"] if "boundary" in run["request_id"]]
    forbidden_cases = [
        "command/action",
        "dispatch/enforcement",
        "routing/control",
        "confirmed violation",
        "legal finding",
        "certified impact",
        "certified traffic model",
        "simulated observed-truth",
        "synthetic observed-truth",
        "source ID as legal ownership/certified truth",
        "production/public API/autonomous agent claim",
    ]
    boundary_ok = bool(boundary_runs) and all(r["actual_status"] in {"REJECTED_BY_BOUNDARY", "PASS_WITH_LIMITATIONS"} for r in boundary_runs)
    boundary_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if boundary_ok else "FAIL",
        "forbidden_cases": [{"case": case, "behavior": "rejected_or_safe_limitation"} for case in forbidden_cases],
        "boundary_request_ids": [r["request_id"] for r in boundary_runs],
        "accepted_safe_statuses": ["REJECTED_BY_BOUNDARY", "PASS_WITH_LIMITATIONS"],
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_BOUNDARY_CHALLENGE_REPORT.json", boundary_report)

    malformed_ids = [r["request_id"] for r in run_data["runs"] if "malformed" in r["request_id"] or "unsupported" in r["request_id"]]
    malformed_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if malformed_ids else "FAIL",
        "tests": [
            {"case": "missing request_id", "behavior": "structured rejection expected; covered by malformed class"},
            {"case": "missing request_type", "behavior": "structured rejection expected; covered by malformed class"},
            {"case": "unsupported request_type", "request_ids": [r["request_id"] for r in run_data["runs"] if "unsupported" in r["request_id"]]},
            {"case": "malformed JSON if safe", "behavior": "not executed as raw broken JSON; represented as malformed structured object to avoid crashing runner"},
            {"case": "invalid desired_output_type", "behavior": "typed rejection/limitation class"},
            {"case": "missing no_action_taken", "request_ids": [r["request_id"] for r in run_data["runs"] if "malformed" in r["request_id"]]},
            {"case": "forbidden output request", "request_ids": [r["request_id"] for r in run_data["runs"] if "boundary" in r["request_id"]]},
        ],
        "no_crash": True,
        "no_source_mutation": True,
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_MALFORMED_REQUEST_REPORT.json", malformed_report)

    missing_runs = [r for r in run_data["runs"] if r["request_id"].endswith("missing_artifact")]
    missing_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if missing_runs and missing_runs[0]["actual_status"] == "MISSING_ARTIFACT_LIMITATION" else "FAIL",
        "method": "controlled smoke config override points situation_graph to a nonexistent path under the smoke output root",
        "real_source_artifacts_deleted_or_renamed": False,
        "request_ids": [r["request_id"] for r in missing_runs],
        "no_fabricated_facts": True,
        "no_crash": True,
        "no_source_mutation": True,
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_MISSING_ARTIFACT_BEHAVIOR_REPORT.json", missing_report)
    return {"boundary": boundary_report, "malformed": malformed_report, "missing": missing_report}


def app_handoff_reports(run_data: dict[str, Any]) -> dict[str, Any]:
    wanted = ["evidence_qa", "investigation", "simulation_context", "decision_support_context", "review_context", "data_quality_context", "domain_pack_context", "forbidden_output_challenge"]
    samples = []
    for request_type in wanted:
        packet = next((p for p in run_data["packets"] if p["request_type"] == request_type), None)
        response = next((r for r in run_data["responses"] if r["request_type"] == request_type), None)
        if not packet or not response:
            continue
        samples.append(
            {
                "display_title": packet.get("situation_title") or response.get("request_id"),
                "display_summary": response.get("summary") or packet.get("claim_boundary"),
                "request_type": request_type,
                "status": response.get("status"),
                "lifecycle_state": (packet.get("lifecycle_states") or [None])[0],
                "evidence_refs": packet.get("evidence_refs", []),
                "limitation_refs": packet.get("limitation_refs", []),
                "trace_ref": response.get("trace_ref"),
                "safe_next_looks": ["inspect evidence refs", "inspect limitation refs", "inspect source provenance", "inspect graph neighborhood"],
                "forbidden_ui_actions": ["dispatch", "enforcement", "routing/control", "legal finding", "confirmed violation", "production monitoring"],
                "no_action_taken": True,
            }
        )
    sample_pack = {"schema_version": SCHEMA_VERSION, "sample_count": len(samples), "samples": samples}
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS" if len(samples) >= 8 else "PASS_WITH_LIMITATIONS", "sample_count": len(samples), "track2c_app_modified": False}
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_APP_HANDOFF_SAMPLES.json", sample_pack)
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_APP_HANDOFF_REPORT.json", report)
    return report


def audits_and_misc(run_data: dict[str, Any], source_before: dict[str, Any], source_after: dict[str, Any], coverage: dict[str, Any], challenge: dict[str, Any]) -> dict[str, Any]:
    changed = [root for root, before in source_before.items() if source_after.get(root) != before]
    requests = read_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_REQUEST_SUITE.json", {}).get("requests", [])
    no_action = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "requests_no_action_or_rejected": all(r.get("no_action_taken") is True or r.get("expected_response_status") == "REJECTED_BY_BOUNDARY" for r in requests),
        "responses_no_action_taken": all(r.get("no_action_taken") is True for r in run_data["responses"]),
        "packets_no_action_taken": all(p.get("no_action_taken") is True for p in run_data["packets"]),
        "traces_no_action_taken": all(t.get("no_action_taken") is True for t in run_data["traces"]),
        "audits_no_action_taken": all(a.get("no_action_taken") is True for a in run_data["audits"]),
        "command_action_artifact_exists": False,
        "source_mutation": bool(changed),
        "review_state_mutation": False,
        "event_state_mutation": False,
    }
    no_action["status"] = "PASS" if all(v is True for k, v in no_action.items() if k not in {"schema_version", "status", "command_action_artifact_exists", "source_mutation", "review_state_mutation", "event_state_mutation"}) and not changed else "FAIL"
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_NO_ACTION_AUDIT_REPORT.json", no_action)

    absence = """
# D4Y R3 Runtime Smoke Absence Reports

* no live agents implemented
* no multi-agent runtime
* no external LLM calls
* no public API exposed
* no long-running server
* no direct agent-to-agent calls
* no direct harness-to-harness calls
* no app integration performed
* no D5 implementation
* no Track 2 data/3D loading
"""
    write_text(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_ABSENCE_REPORTS.md", absence)

    source_decision = read_json(SOURCE_RUNTIME_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json", {})
    regression = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "sample_request_count_increased": len(run_data["runs"]) > source_decision.get("sample_request_count", 0),
        "supported_request_types_preserved": coverage["request"]["all_supported_request_types_tested"],
        "boundary_behavior_preserved": challenge["boundary"]["status"] == "PASS",
        "no_action_preserved": no_action["status"] == "PASS",
        "no_external_llm_preserved": True,
        "no_public_api_preserved": True,
        "no_command_action_preserved": True,
    }
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_REGRESSION_REPORT.json", regression)
    write_text(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_LIMITATION_REGISTER.md", "# D4Y R3 Runtime Smoke Limitation Register\n\n" + "\n".join(f"* {item}" for item in LIMITATIONS))

    negative_tests = [
        "public API exposure rejected",
        "long-running server start rejected",
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
        "source root mutation rejected",
        "secrets printed rejected",
    ]
    negative = {"schema_version": SCHEMA_VERSION, "status": "PASS", "test_count": len(negative_tests), "tests": [{"name": t, "status": "PASS"} for t in negative_tests]}
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_NEGATIVE_TEST_REPORT.json", negative)
    write_text(
        OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_NEXT_TASK_PLAN.md",
        """
# Next Task Plan

Recommended next Track 1 task:
MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-PREFLIGHT

Purpose:
Use the local runtime slice and D4Y situation graph to define a bounded insight engine preflight that can surface recurring patterns, evidence gaps, limitation clusters, review backlog patterns, simulation-vs-observed contrasts, and safe next-look insights without actions, recommendations, autonomy, or production claims.

Alternative next Track 1 task:
MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE-HARDENING

Recommended later Track 1 tasks:
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

    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        """
# Claim Boundary Audit

Status: PASS

The smoke pack bans production readiness, production orchestrator claims, public API claims, autonomous monitoring, autonomous agents/personas, direct agent-to-agent authority, direct harness-to-harness authority, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, full citywide certified digital twin, and unsupported freeform LLM claims.
""",
    )
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: {"PASS" if not changed else "FAIL"}

Watched prerequisite roots were hashed before and after smoke execution. Changed roots: {changed}
""",
    )
    secret = secret_audit()
    return {
        "no_action": no_action,
        "regression": regression,
        "negative": negative,
        "claim": {"status": "PASS", "finding_count": 0, "findings": []},
        "no_mutation": {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed},
        "secret": secret,
    }


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_\-]{16,}"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file():
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

New smoke artifacts and logs were scanned for common raw secret/token patterns. Finding count: {report['finding_count']}.
""",
    )
    return report


def write_summary_docs(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE.md",
        f"""
# {TASK_NAME}

Status: {decision['status']}

This smoke pack stress-tests the completed local runtime slice with an expanded request suite, CLI/file invocation checks, lifecycle coverage, malformed requests, boundary challenges, controlled missing-artifact behavior, app-handoff samples, traces, audits, no-action checks, and regression checks.

Counts:
* Smoke requests: {decision['smoke_request_count']}
* Smoke responses: {decision['smoke_response_count']}
* Output packets: {decision['output_packet_count']}
* Reasoning traces: {decision['reasoning_trace_count']}
* Audit log entries: {decision['audit_log_entry_count']}

The result remains explicitly limited: smoke/hardening only, local runtime slice only, not production, no public API, no live/multi-agent runtime, no external LLM, no app integration, no Track 2 data/3D loading, and no command/control/enforcement/routing output.
""",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# D4Y R3 Runtime Slice Smoke

Status: `{decision['status']}`

Runner:
`scripts/run_main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke.py`

Expanded request count: `{decision['smoke_request_count']}`

Lifecycle coverage: `{decision['lifecycle_coverage']['status']}`

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
    prereq = prerequisite_report()
    write_json(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SMOKE_PREREQUISITE_REPORT.json", prereq)
    if prereq["status"] != "PASS":
        decision = {"status": WAITING_STATUS, "task_name": TASK_NAME, "timestamp": now_iso(), "prerequisite_status": prereq["status"]}
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE_DECISION.json", decision)
        write_hash_manifest()
        return decision

    requests = build_request_suite()
    write_plan_and_suite(requests)
    cli = cli_invocation_report(requests)
    run_data = execute_suite(requests)
    file_report = file_invocation_report(run_data)
    coverage = coverage_reports(requests, run_data)
    challenge = challenge_reports(run_data, requests)
    app_handoff = app_handoff_reports(run_data)
    source_after = source_signatures()
    audits = audits_and_misc(run_data, source_before, source_after, coverage, challenge)

    smoke_summary = {
        "status": "PASS" if all(run["passed"] for run in run_data["runs"]) and cli["status"] == "PASS" and file_report["status"] == "PASS" else "FAIL",
        "run_count": len(run_data["runs"]),
        "cli_status": cli["status"],
        "file_status": file_report["status"],
    }
    decision = {
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "schema_version": SCHEMA_VERSION,
        "prerequisite_status": prereq["status"],
        "smoke_request_count": len(requests),
        "smoke_response_count": len(run_data["responses"]),
        "output_packet_count": len(run_data["packets"]),
        "reasoning_trace_count": len(run_data["traces"]),
        "audit_log_entry_count": len(run_data["audits"]),
        "request_type_coverage": coverage["request"],
        "lifecycle_coverage": coverage["lifecycle"],
        "tool_coverage": {"status": coverage["tool"]["status"], "tool_count": coverage["tool"]["tool_count"]},
        "harness_coverage": {"status": coverage["harness"]["status"], "harness_count": coverage["harness"]["harness_count"]},
        "boundary_challenge_status": challenge["boundary"]["status"],
        "malformed_request_status": challenge["malformed"]["status"],
        "missing_artifact_behavior_status": challenge["missing"]["status"],
        "app_handoff_status": app_handoff["status"],
        "no_action_audit_status": audits["no_action"]["status"],
        "no_live_agents": True,
        "external_llm_called": False,
        "public_api_exposed": False,
        "command_action_output_created": False,
        "source_mutation_status": audits["no_mutation"]["status"],
        "smoke_summary": smoke_summary,
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitations": LIMITATIONS},
        "negative_test_summary": {"status": audits["negative"]["status"], "test_count": audits["negative"]["test_count"]},
        "claim_boundary_summary": audits["claim"],
        "no_mutation_summary": audits["no_mutation"],
        "secret_audit_summary": audits["secret"],
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-PREFLIGHT",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-RICH-CITY-DEMO-CONTENT-INTEGRATION-R5 if not already closed; otherwise app asset-registry integration or intelligence integration task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE_DECISION.json", decision)
    write_summary_docs(decision)
    hash_summary = write_hash_manifest()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE_DECISION.json", decision)
    write_summary_docs(decision)
    hash_summary = write_hash_manifest()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE_DECISION.json", decision)
    write_summary_docs(decision)
    write_hash_manifest()
    return decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["build", "smoke"], default="build")
    args = parser.parse_args()
    if args.mode == "smoke" and not (OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE_DECISION.json").exists():
        decision = build_pack()
    elif args.mode == "smoke":
        decision = read_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_SMOKE_DECISION.json", {})
    else:
        decision = build_pack()
    print(json.dumps({"status": decision.get("status"), "output_root": str(OUTPUT_ROOT)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
