#!/usr/bin/env python3
"""D5 local served runtime preflight for CityBrain.

This is a bounded localhost-only HTTP wrapper around the existing local callable
runtime artifacts. It is deliberately not a production service.
"""

from __future__ import annotations

import argparse
import http.client
import importlib.util
import json
import shutil
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


sys.dont_write_bytecode = True

TASK_ID = "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-PREFLIGHT"
SCHEMA_VERSION = "main-citybrain-d5-local-served-runtime-preflight.v1"
PASS = "PASS"
PASS_WITH_LIMITATIONS = "PASS_WITH_LIMITATIONS"
FAIL = "FAIL"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_preflight"
D5_RUNTIME_WORK_ROOT = OUTPUT_ROOT / "runtime_work"
D5_RUNTIME_CONFIG = D5_RUNTIME_WORK_ROOT / "runtime_config.json"

R3_RUNTIME_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice"
R3_RUNTIME_HELPER = R3_RUNTIME_ROOT / "runtime/d4y_r3_runtime.py"
R3_INSIGHT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_slice"
R4_HARDENING_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_live_runtime_hardening"
R5_DOMAIN_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end"
R5_BUILDING_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice"

READ_ONLY_INPUT_ROOTS = [
    R3_RUNTIME_ROOT,
    R3_INSIGHT_ROOT,
    R4_HARDENING_ROOT,
    R5_DOMAIN_ROOT,
    R5_BUILDING_ROOT,
]

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
CLIENT_TIMEOUT_SECONDS = 5

BOUNDARY = (
    "Local served runtime preflight only. No production deployment, public API, "
    "autonomous workflow execution, command/control, dispatch, enforcement, "
    "routing/control, legal finding, confirmed violation, certified impact, "
    "or certified traffic model."
)

BASE_LIMITATIONS = [
    "local_served_runtime_preflight_only",
    "localhost_only",
    "not_production_deployment",
    "no_auth_rbac_in_this_preflight",
    "no_public_network_interface",
    "no_autonomous_action",
    "no_command_control_dispatch_enforcement_routing",
    "response_contract_needs_followup_stabilization",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, str):
        return value.encode("ascii", "ignore").decode("ascii")
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    return value


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return clean(json.loads(path.read_text(encoding="utf-8")))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(clean(text).rstrip() + "\n", encoding="utf-8")


def snapshot_root(root: Path) -> dict[str, str]:
    if not root.exists():
        return {"__missing__": "true"}
    signature: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        stat = path.stat()
        signature[rel] = f"{stat.st_size}:{int(stat.st_mtime)}"
    return signature


def prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    expected_parent = (REPO_ROOT / "outputs").resolve()
    if resolved.parent != expected_parent or resolved.name != "main_citybrain_d5_local_served_runtime_preflight":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def write_derived_runtime_config() -> None:
    source_config = read_json(R3_RUNTIME_ROOT / "runtime/runtime_config.json", {})
    source_config["output_root"] = str(D5_RUNTIME_WORK_ROOT)
    D5_RUNTIME_WORK_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(D5_RUNTIME_CONFIG, source_config)


def import_r3_runtime_helper() -> Any:
    spec = importlib.util.spec_from_file_location("citybrain_d4y_r3_runtime_helper", R3_RUNTIME_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import runtime helper: {R3_RUNTIME_HELPER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_source_state() -> dict[str, Any]:
    return {
        "r3_runtime_decision": read_json(R3_RUNTIME_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json", {}),
        "r3_runtime_request_schema": read_json(R3_RUNTIME_ROOT / "D4Y_R3_RUNTIME_REQUEST_SCHEMA.json", {}),
        "r3_runtime_response_schema": read_json(R3_RUNTIME_ROOT / "D4Y_R3_RUNTIME_RESPONSE_SCHEMA.json", {}),
        "r3_runtime_sample_requests": read_json(R3_RUNTIME_ROOT / "D4Y_R3_RUNTIME_SAMPLE_REQUESTS.json", {}).get("requests", []),
        "r3_runtime_sample_responses": read_json(R3_RUNTIME_ROOT / "D4Y_R3_RUNTIME_SAMPLE_RESPONSES.json", {}).get("responses", []),
        "r3_insight_decision": read_json(R3_INSIGHT_ROOT / "MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_DECISION.json", {}),
        "r3_insight_packets": read_json(R3_INSIGHT_ROOT / "D4Y_R3_INSIGHT_PACKETS.json", {}).get("packets", []),
        "r3_insight_ranked_feeds": read_json(R3_INSIGHT_ROOT / "D4Y_R3_INSIGHT_RANKED_FEEDS.json", {}).get("feeds", []),
        "r4_decision": read_json(R4_HARDENING_ROOT / "MAIN_TRACK1_D4Y_R4_LIVE_RUNTIME_HARDENING_DECISION.json", {}),
        "r5_decision": read_json(R5_DOMAIN_ROOT / "MAIN_TRACK1_D4Y_R5_DOMAIN_PACK_FIRST_TWO_DOMAIN_PROOF_END_TO_END_DECISION.json", {}),
        "r5_building_packets": read_json(R5_BUILDING_ROOT / "R5_BUILDING_ASSET_APP_HANDOFF_PACKETS.json", {}).get("packets", []),
        "r5_civic_packets": read_json(R5_DOMAIN_ROOT / "R5_CIVIC_SERVICE_RUNTIME_SLICE_APP_HANDOFF_PACKETS.json", {}).get("packets", []),
    }


def contract(bind_host: str, bind_port: int) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "LOCAL_SERVED_RUNTIME_CONTRACT_DRAFT",
        "served_entrypoint": "python scripts/run_main_citybrain_d5_local_served_runtime_preflight.py --serve --host 127.0.0.1 --port 8765",
        "bind_host": bind_host,
        "bind_port": bind_port,
        "local_only_policy": {
            "allowed_hosts": ["127.0.0.1", "localhost", "::1"],
            "default_host": DEFAULT_HOST,
            "external_interfaces_allowed": False,
            "public_deployment_allowed": False,
        },
        "endpoints": [
            {"method": "GET", "path": "/health", "purpose": "Health/status check with local-only boundary."},
            {"method": "GET", "path": "/status", "purpose": "Version/build/source metadata."},
            {"method": "GET", "path": "/contract", "purpose": "Return this served runtime contract."},
            {"method": "POST", "path": "/runtime/request", "purpose": "Bounded local runtime request envelope."},
        ],
        "request_schema": {
            "type": "object",
            "required": ["request_class", "no_action_taken"],
            "properties": {
                "request_class": {
                    "enum": [
                        "governed_query",
                        "insight_packet_request",
                        "unsupported_domain",
                    ]
                },
                "request": {"type": "object"},
                "insight_type": {"type": "string"},
                "domain_id": {"type": "string"},
                "include_trace": {"const": True},
                "include_limitations": {"const": True},
                "no_action_taken": {"const": True},
            },
            "additionalProperties": True,
        },
        "response_schema": {
            "type": "object",
            "required": [
                "served_response_id",
                "status",
                "request_class",
                "trace_refs",
                "evidence_refs",
                "limitation_refs",
                "claim_boundary",
                "no_action_taken",
                "autonomous_action_exposed",
                "production_readiness_claim_made",
            ],
            "properties": {
                "status": {"type": "string"},
                "trace_refs": {"type": "array"},
                "evidence_refs": {"type": "array"},
                "limitation_refs": {"type": "array"},
                "confidence_or_grounding_label": {"type": "string"},
                "error": {"type": ["object", "null"]},
            },
        },
        "error_envelope": {
            "status": "SAFE_FAILURE_*",
            "error": {
                "code": "string",
                "message": "bounded explanation",
                "safe_failure": True,
            },
            "no_action_taken": True,
            "limitation_refs": BASE_LIMITATIONS,
        },
        "timeout_behavior": {
            "client_timeout_seconds": CLIENT_TIMEOUT_SECONDS,
            "server_request_timeout_policy": "bounded smoke client timeout; no background retry loop",
        },
        "no_mutation_policy": {
            "source_artifacts_read_only": True,
            "writes_allowed_under_output_root_only": True,
            "autonomous_workflows_allowed": False,
        },
        "claim_boundary": BOUNDARY,
    }


class RuntimeService:
    def __init__(self, bind_host: str, bind_port: int) -> None:
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.started_at = now_iso()
        self.state = load_source_state()
        self.runtime_helper = import_r3_runtime_helper()
        self.contract = contract(bind_host, bind_port)

    def base_envelope(self, request_class: str, status: str, trace_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "served_response_id": f"served-response:{trace_id}",
            "status": status,
            "request_class": request_class,
            "trace_refs": [f"served-runtime-trace:{trace_id}"],
            "evidence_refs": ["source-artifact:LOCAL_SERVED_RUNTIME_CONTRACT", "source-artifact:R3_RUNTIME"],
            "limitation_refs": list(BASE_LIMITATIONS),
            "claim_boundary": BOUNDARY,
            "confidence_or_grounding_label": "grounded_in_existing_local_artifacts",
            "safe_next_looks": ["inspect trace refs", "inspect evidence refs", "inspect limitation refs"],
            "no_action_taken": True,
            "autonomous_action_exposed": False,
            "production_readiness_claim_made": False,
            "command_action_output_created": False,
            "error": None,
        }

    def health(self) -> dict[str, Any]:
        out = self.base_envelope("health_status", "OK", "health")
        out.update(
            {
                "service": TASK_ID,
                "version": SCHEMA_VERSION,
                "started_at_utc": self.started_at,
                "bind_host": self.bind_host,
                "bind_port": self.bind_port,
                "local_only_confirmed": self.bind_host in {"127.0.0.1", "localhost", "::1"},
                "source_statuses": {
                    "r3_runtime": self.state["r3_runtime_decision"].get("status"),
                    "r3_insight": self.state["r3_insight_decision"].get("status"),
                    "r4_hardening": self.state["r4_decision"].get("status"),
                    "r5_domain": self.state["r5_decision"].get("status"),
                },
            }
        )
        return out

    def status(self) -> dict[str, Any]:
        out = self.base_envelope("health_status", "OK", "status")
        out.update(
            {
                "runtime_entrypoint": str(R3_RUNTIME_HELPER.relative_to(REPO_ROOT)).replace("\\", "/"),
                "runtime_sample_request_count": len(self.state["r3_runtime_sample_requests"]),
                "runtime_sample_response_count": len(self.state["r3_runtime_sample_responses"]),
                "insight_packet_count": len(self.state["r3_insight_packets"]),
                "r5_building_packet_count": len(self.state["r5_building_packets"]),
                "r5_civic_packet_count": len(self.state["r5_civic_packets"]),
            }
        )
        return out

    def safe_error(self, request_class: str, trace_id: str, code: str, message: str, status: str = "SAFE_FAILURE_INVALID_REQUEST") -> dict[str, Any]:
        out = self.base_envelope(request_class, status, trace_id)
        out["confidence_or_grounding_label"] = "safe_failure_grounded_in_contract"
        out["limitation_refs"] = list(dict.fromkeys(BASE_LIMITATIONS + [code.lower()]))
        out["error"] = {"code": code, "message": message, "safe_failure": True}
        return out

    def governed_query(self, body: dict[str, Any]) -> dict[str, Any]:
        request = dict(body.get("request") or {})
        request.setdefault("request_id", "d5-served-governed-query")
        request.setdefault("request_type", "evidence_qa")
        request.setdefault("desired_output_type", "answer_packet")
        request.setdefault("include_limitations", True)
        request.setdefault("include_trace", True)
        request.setdefault("no_action_taken", True)
        if request.get("no_action_taken") is not True:
            return self.safe_error("governed_query", str(request.get("request_id") or "invalid"), "NO_ACTION_REQUIRED", "Runtime requests must keep no_action_taken=true.")
        result = self.runtime_helper.run_request(request, config_path=str(D5_RUNTIME_CONFIG))
        response = result.get("response", {})
        trace = result.get("trace", {})
        out = self.base_envelope("governed_query", response.get("status", "PASS_WITH_LIMITATIONS"), request["request_id"])
        out.update(
            {
                "runtime_response": response,
                "runtime_packet": result.get("packet"),
                "trace": trace,
                "trace_refs": list(dict.fromkeys(out["trace_refs"] + [response.get("trace_ref"), trace.get("trace_id")])),
                "evidence_refs": list(dict.fromkeys(response.get("evidence_refs", []) + out["evidence_refs"])),
                "limitation_refs": list(dict.fromkeys(response.get("limitation_refs", []) + out["limitation_refs"])),
                "source_refs": response.get("source_refs", []),
                "confidence_or_grounding_label": "deterministic_runtime_response_existing_refs",
            }
        )
        return out

    def insight_packet(self, body: dict[str, Any]) -> dict[str, Any]:
        requested_type = body.get("insight_type")
        packets = self.state["r3_insight_packets"]
        packet = None
        for candidate in packets:
            if requested_type is None or candidate.get("insight_type") == requested_type:
                packet = candidate
                break
        if not packet:
            return self.safe_error("insight_packet_request", "insight-no-data", "NO_INSIGHT_PACKET", "No insight packet matched the requested type.", "SAFE_FAILURE_NO_DATA")
        trace_id = str(body.get("request_id") or f"d5-insight-{packet.get('insight_id')}")
        out = self.base_envelope("insight_packet_request", "PASS_WITH_LIMITATIONS", trace_id)
        out.update(
            {
                "insight_packet": packet,
                "trace_refs": list(dict.fromkeys(out["trace_refs"] + [f"insight-trace:{packet.get('insight_id')}"])),
                "evidence_refs": list(dict.fromkeys(packet.get("evidence_refs", []) + out["evidence_refs"])),
                "limitation_refs": list(dict.fromkeys(packet.get("limitation_refs", []) + out["limitation_refs"])),
                "confidence_or_grounding_label": packet.get("confidence_or_strength_label") or "context_strength_unknown",
            }
        )
        return out

    def unsupported_domain(self, body: dict[str, Any]) -> dict[str, Any]:
        domain_id = str(body.get("domain_id") or "unknown_domain")
        return self.safe_error(
            "unsupported_domain",
            f"unsupported-domain-{domain_id}",
            "UNSUPPORTED_DOMAIN_OR_NO_DATA",
            f"Domain '{domain_id}' is not served by this local preflight wrapper.",
            "SAFE_FAILURE_NO_DATA",
        )

    def request(self, body: Any) -> tuple[int, dict[str, Any]]:
        if not isinstance(body, dict):
            return 400, self.safe_error("invalid_request", "invalid-json-body", "INVALID_JSON_BODY", "Request body must be a JSON object.")
        request_class = body.get("request_class")
        if body.get("no_action_taken") is not True:
            return 400, self.safe_error(str(request_class or "invalid_request"), "missing-no-action", "NO_ACTION_REQUIRED", "Served requests must include no_action_taken=true.")
        if request_class == "governed_query":
            return 200, self.governed_query(body)
        if request_class == "insight_packet_request":
            return 200, self.insight_packet(body)
        if request_class == "unsupported_domain":
            return 422, self.unsupported_domain(body)
        return 400, self.safe_error(str(request_class or "invalid_request"), "unknown-request-class", "UNKNOWN_REQUEST_CLASS", "Unknown request_class.")


def make_handler(service: RuntimeService) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "CityBrainD5LocalServedPreflight/1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def send_json(self, status_code: int, data: dict[str, Any]) -> None:
            payload = json.dumps(clean(data), indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self.send_json(200, service.health())
            elif parsed.path == "/status":
                self.send_json(200, service.status())
            elif parsed.path == "/contract":
                self.send_json(200, service.contract)
            else:
                self.send_json(404, service.safe_error("invalid_request", "not-found", "NOT_FOUND", f"Unknown endpoint: {parsed.path}"))

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/runtime/request":
                self.send_json(404, service.safe_error("invalid_request", "not-found", "NOT_FOUND", f"Unknown endpoint: {parsed.path}"))
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8")
                body = json.loads(raw) if raw else {}
            except Exception:
                self.send_json(400, service.safe_error("invalid_request", "invalid-json", "INVALID_JSON", "Request body could not be parsed as JSON."))
                return
            status_code, data = service.request(body)
            self.send_json(status_code, data)

    return Handler


def start_server(bind_host: str, bind_port: int) -> tuple[ThreadingHTTPServer, RuntimeService, threading.Thread]:
    service = RuntimeService(bind_host, bind_port)
    server = ThreadingHTTPServer((bind_host, bind_port), make_handler(service))
    actual_host, actual_port = server.server_address[:2]
    service.bind_host = str(actual_host)
    service.bind_port = int(actual_port)
    service.contract = contract(service.bind_host, service.bind_port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, service, thread


def http_get(host: str, port: int, path: str) -> tuple[int, dict[str, Any]]:
    conn = http.client.HTTPConnection(host, port, timeout=CLIENT_TIMEOUT_SECONDS)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        return resp.status, data
    finally:
        conn.close()


def http_post(host: str, port: int, path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    conn = http.client.HTTPConnection(host, port, timeout=CLIENT_TIMEOUT_SECONDS)
    try:
        payload = json.dumps(body).encode("utf-8")
        conn.request("POST", path, body=payload, headers={"Content-Type": "application/json", "Content-Length": str(len(payload))})
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        return resp.status, data
    finally:
        conn.close()


def request_fixtures() -> list[dict[str, Any]]:
    return [
        {"case_id": "d5-health", "method": "GET", "path": "/health", "request_class": "health_status", "expected_status_codes": [200]},
        {"case_id": "d5-status", "method": "GET", "path": "/status", "request_class": "health_status", "expected_status_codes": [200]},
        {
            "case_id": "d5-governed-query",
            "method": "POST",
            "path": "/runtime/request",
            "request_class": "governed_query",
            "expected_status_codes": [200],
            "body": {
                "request_class": "governed_query",
                "no_action_taken": True,
                "include_trace": True,
                "include_limitations": True,
                "request": {
                    "request_id": "d5-served-governed-query",
                    "request_type": "evidence_qa",
                    "desired_output_type": "answer_packet",
                    "include_limitations": True,
                    "include_trace": True,
                    "no_action_taken": True,
                },
            },
        },
        {
            "case_id": "d5-insight-packet",
            "method": "POST",
            "path": "/runtime/request",
            "request_class": "insight_packet_request",
            "expected_status_codes": [200],
            "body": {
                "request_class": "insight_packet_request",
                "request_id": "d5-served-insight-request",
                "insight_type": "evidence_gap",
                "include_trace": True,
                "include_limitations": True,
                "no_action_taken": True,
            },
        },
        {
            "case_id": "d5-invalid-request",
            "method": "POST",
            "path": "/runtime/request",
            "request_class": "invalid_request",
            "expected_status_codes": [400],
            "body": {
                "request_class": "governed_query",
                "no_action_taken": False,
                "request": {"request_id": "d5-invalid-no-action", "request_type": "evidence_qa"},
            },
        },
        {
            "case_id": "d5-no-data-unsupported-domain",
            "method": "POST",
            "path": "/runtime/request",
            "request_class": "unsupported_domain",
            "expected_status_codes": [422],
            "body": {
                "request_class": "unsupported_domain",
                "domain_id": "public_safety_dispatch",
                "include_trace": True,
                "include_limitations": True,
                "no_action_taken": True,
            },
        },
    ]


def has_refs(response: dict[str, Any], key: str) -> bool:
    refs = response.get(key)
    return isinstance(refs, list) and len([r for r in refs if r]) > 0


def smoke(host: str, port: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases = []
    responses = []
    for fixture in request_fixtures():
        if fixture["method"] == "GET":
            status_code, body = http_get(host, port, fixture["path"])
        else:
            status_code, body = http_post(host, port, fixture["path"], fixture["body"])
        checks = {
            "status_code_expected": status_code in fixture["expected_status_codes"],
            "trace_refs_present": has_refs(body, "trace_refs"),
            "evidence_refs_present": has_refs(body, "evidence_refs"),
            "limitation_refs_present": has_refs(body, "limitation_refs"),
            "no_action_taken": body.get("no_action_taken") is True,
            "autonomous_action_not_exposed": body.get("autonomous_action_exposed") is False,
            "production_readiness_not_claimed": body.get("production_readiness_claim_made") is False,
        }
        if fixture["case_id"] == "d5-invalid-request":
            checks["invalid_request_safe_failure"] = body.get("error", {}).get("safe_failure") is True and str(body.get("status", "")).startswith("SAFE_FAILURE")
        if fixture["case_id"] == "d5-no-data-unsupported-domain":
            checks["no_data_safe_failure"] = body.get("error", {}).get("safe_failure") is True and body.get("status") == "SAFE_FAILURE_NO_DATA"
        cases.append(
            {
                "case_id": fixture["case_id"],
                "method": fixture["method"],
                "path": fixture["path"],
                "request_class": fixture["request_class"],
                "http_status": status_code,
                "response_status": body.get("status"),
                "checks": checks,
                "passed": all(checks.values()),
            }
        )
        responses.append({"case_id": fixture["case_id"], "http_status": status_code, "response": body})
    return cases, responses


def trace_audit(cases: list[dict[str, Any]], responses: list[dict[str, Any]]) -> dict[str, Any]:
    response_bodies = [row["response"] for row in responses]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(row["passed"] for row in cases) else "FAIL",
        "response_count": len(response_bodies),
        "trace_refs_present": all(has_refs(row, "trace_refs") for row in response_bodies),
        "evidence_refs_present": all(has_refs(row, "evidence_refs") for row in response_bodies),
        "limitation_refs_present": all(has_refs(row, "limitation_refs") for row in response_bodies),
        "no_action_taken_all": all(row.get("no_action_taken") is True for row in response_bodies),
        "autonomous_action_exposed": any(row.get("autonomous_action_exposed") is True for row in response_bodies),
        "production_readiness_claim_made": any(row.get("production_readiness_claim_made") is True for row in response_bodies),
        "case_results": cases,
    }


def write_reports(decision: dict[str, Any], smoke_results: dict[str, Any], trace_report: dict[str, Any], mutation_report: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_PREFLIGHT_REPORT.md",
        f"""# Local Served Runtime Preflight

Status: `{decision['status']}`

This is a local served runtime readiness gate. It is not cloud deployment, not production hardening, not enterprise auth/RBAC, and not a public API.

Served entrypoint:

```text
{decision['served_entrypoint']}
```

Bind: `{decision['bind_host']}:{decision['bind_port']}`

Smoke:

- Request cases: {decision['request_cases_total']}
- Passed: {decision['request_cases_passed']}
- Health check: {decision['health_check_passed']}
- Invalid request safe failure: {decision['invalid_request_safe_failure_passed']}
- No-data safe failure: {decision['no_data_safe_failure_passed']}

Trace/evidence/limitations:

- Trace refs present: {decision['trace_refs_present']}
- Evidence refs present: {decision['evidence_refs_present']}
- Limitation refs present: {decision['limitation_refs_present']}

Boundary:

{BOUNDARY}

Mutation:

- Status: {mutation_report['status']}
- Changed input roots: {mutation_report['changed_roots']}
""",
    )
    write_text(
        OUTPUT_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md",
        """# Limitations and Next Steps

Limitations:

- Localhost-only preflight wrapper.
- Uses Python standard-library HTTP server for smoke.
- No production auth/RBAC.
- No public deployment.
- No long-running process manager.
- No OpenAPI generation beyond the contract artifact.
- Served response schema should be stabilized in the next hardening pass.
- Existing runtime remains deterministic/file-backed; no autonomous workflows are added.

Recommended next task:

```text
MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-HARDENING-R1
```
""",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_ID}

Status: `{decision['status']}`

Run preflight:

```text
python scripts/run_main_citybrain_d5_local_served_runtime_preflight.py
```

Run local server manually:

```text
{decision['served_entrypoint']}
```

This is a localhost-only served runtime preflight. It does not claim production readiness.
""",
    )


def write_outputs(
    bind_host: str,
    bind_port: int,
    actual_host: str,
    actual_port: int,
    cases: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> dict[str, Any]:
    smoke_results = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(case["passed"] for case in cases) else "FAIL",
        "bind_host": actual_host,
        "bind_port": actual_port,
        "request_cases_total": len(cases),
        "request_cases_passed": sum(1 for case in cases if case["passed"]),
        "cases": cases,
    }
    trace_report = trace_audit(cases, responses)
    changed_roots = [root for root, sig in before.items() if after.get(root) != sig]
    mutation_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not changed_roots else "FAIL",
        "changed_roots": changed_roots,
        "read_only_input_roots": list(before.keys()),
        "writes_allowed_under_output_root_only": True,
    }
    invalid_case = next(case for case in cases if case["case_id"] == "d5-invalid-request")
    no_data_case = next(case for case in cases if case["case_id"] == "d5-no-data-unsupported-domain")
    health_case = next(case for case in cases if case["case_id"] == "d5-health")
    status = PASS_WITH_LIMITATIONS if smoke_results["status"] == "PASS" and trace_report["status"] == "PASS" and mutation_report["status"] == "PASS" else FAIL
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now_iso(),
        "served_entrypoint": "python scripts/run_main_citybrain_d5_local_served_runtime_preflight.py --serve --host 127.0.0.1 --port 8765",
        "bind_host": actual_host,
        "bind_port": actual_port,
        "local_only_confirmed": actual_host in {"127.0.0.1", "localhost", "::1"} and bind_host not in {"0.0.0.0", "::"},
        "health_check_passed": health_case["passed"],
        "request_cases_total": smoke_results["request_cases_total"],
        "request_cases_passed": smoke_results["request_cases_passed"],
        "invalid_request_safe_failure_passed": invalid_case["checks"].get("invalid_request_safe_failure", False),
        "no_data_safe_failure_passed": no_data_case["checks"].get("no_data_safe_failure", False),
        "trace_refs_present": trace_report["trace_refs_present"],
        "evidence_refs_present": trace_report["evidence_refs_present"],
        "limitation_refs_present": trace_report["limitation_refs_present"],
        "autonomous_action_exposed": trace_report["autonomous_action_exposed"],
        "production_readiness_claim_made": trace_report["production_readiness_claim_made"],
        "source_mutation_status": mutation_report["status"],
        "served_wrapper_mode": "thin_stdlib_http_wrapper_over_existing_local_runtime",
        "limitations": BASE_LIMITATIONS,
        "next_recommended_task": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-HARDENING-R1",
    }
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_CONTRACT.json", contract(actual_host, actual_port))
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_REQUEST_FIXTURES.json", {"schema_version": SCHEMA_VERSION, "fixtures": request_fixtures(), "fixture_count": len(request_fixtures())})
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_RESPONSE_FIXTURES.json", {"schema_version": SCHEMA_VERSION, "responses": responses, "response_count": len(responses)})
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_SMOKE_RESULTS.json", smoke_results)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_TRACE_AUDIT.json", trace_report)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_NO_MUTATION_AUDIT.json", mutation_report)
    write_reports(decision, smoke_results, trace_report, mutation_report)
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_PREFLIGHT_DECISION.json", decision)
    return decision


def run_preflight(bind_host: str) -> dict[str, Any]:
    before = {root.relative_to(REPO_ROOT).as_posix(): snapshot_root(root) for root in READ_ONLY_INPUT_ROOTS}
    prepare_output_root()
    write_derived_runtime_config()
    server, service, thread = start_server(bind_host, 0)
    try:
        time.sleep(0.2)
        actual_host, actual_port = server.server_address[:2]
        cases, responses = smoke(str(actual_host), int(actual_port))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=CLIENT_TIMEOUT_SECONDS)
    after = {root.relative_to(REPO_ROOT).as_posix(): snapshot_root(root) for root in READ_ONLY_INPUT_ROOTS}
    decision = write_outputs(bind_host, 0, str(actual_host), int(actual_port), cases, responses, before, after)
    return decision


def serve_forever(bind_host: str, bind_port: int) -> None:
    if bind_host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing to bind non-local host for D5 preflight.")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_derived_runtime_config()
    server, service, _thread = start_server(bind_host, bind_port)
    actual_host, actual_port = server.server_address[:2]
    print(json.dumps({"status": "SERVING_LOCAL_ONLY", "host": actual_host, "port": actual_port, "boundary": BOUNDARY}, indent=2))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=TASK_ID)
    parser.add_argument("--serve", action="store_true", help="Run the local served wrapper instead of the preflight smoke.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    if args.serve:
        serve_forever(args.host, args.port)
        return
    decision = run_preflight(DEFAULT_HOST)
    print(json.dumps({"status": decision["status"], "output_root": str(OUTPUT_ROOT), "decision": decision}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
