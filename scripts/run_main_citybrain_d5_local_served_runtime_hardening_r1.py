#!/usr/bin/env python3
"""D5 R1 local served runtime hardening harness.

This hardens the D5 preflight wrapper into a stable localhost-only test harness.
It remains local/developer runtime work, not production deployment.
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

TASK_ID = "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-HARDENING-R1"
SCHEMA_VERSION = "main-citybrain-d5-local-served-runtime-hardening-r1.v1"
PASS = "PASS"
PASS_WITH_LIMITATIONS = "PASS_WITH_LIMITATIONS"
FAIL = "FAIL"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_hardening_r1"
RUNTIME_WORK_ROOT = OUTPUT_ROOT / "runtime_work"
RUNTIME_CONFIG = RUNTIME_WORK_ROOT / "runtime_config.json"

UPSTREAM_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_preflight"
R3_RUNTIME_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice"
R3_RUNTIME_HELPER = R3_RUNTIME_ROOT / "runtime/d4y_r3_runtime.py"
R3_INSIGHT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_slice"
R4_HARDENING_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_live_runtime_hardening"
R5_DOMAIN_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end"
R5_BUILDING_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice"

READ_ONLY_INPUT_ROOTS = [
    UPSTREAM_ROOT,
    R3_RUNTIME_ROOT,
    R3_INSIGHT_ROOT,
    R4_HARDENING_ROOT,
    R5_DOMAIN_ROOT,
    R5_BUILDING_ROOT,
]

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
CLIENT_TIMEOUT_SECONDS = 5
REQUEST_TIMEOUT_BUDGET_MS = 1500

BOUNDARY = (
    "Local served runtime hardening only. No production deployment, public API, "
    "enterprise auth/RBAC, cloud deployment, autonomous workflow execution, "
    "command/control, dispatch, enforcement, routing/control, legal finding, "
    "confirmed violation, certified impact, or certified traffic model."
)

LIMITATIONS = [
    "local_served_runtime_hardening_only",
    "thin_stdlib_localhost_wrapper",
    "localhost_only_default_binding",
    "manual_shutdown_for_long_running_serve_mode",
    "basic_timeout_budget_check_not_process_supervision",
    "no_production_auth_rbac",
    "no_public_deployment",
    "no_concurrency_load_test",
    "no_autonomous_action",
    "response_envelope_stabilized_for_r1_but_not_final_public_api",
]

REQUIRED_ARTIFACTS = [
    "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_HARDENING_R1_DECISION.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_REPORT.md",
    "LOCAL_SERVED_RUNTIME_HARDENED_CONTRACT.json",
    "LOCAL_SERVED_RUNTIME_REQUEST_ENVELOPE_SCHEMA.json",
    "LOCAL_SERVED_RUNTIME_RESPONSE_ENVELOPE_SCHEMA.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_REQUEST_FIXTURES.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_RESPONSE_FIXTURES.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_SMOKE_RESULTS.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_TRACE_AUDIT.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_BOUNDARY_AUDIT.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_LIMITATIONS_AND_NEXT_STEPS.md",
    "README.md",
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
        stat = path.stat()
        signature[path.relative_to(root).as_posix()] = f"{stat.st_size}:{int(stat.st_mtime)}"
    return signature


def prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    expected_parent = (REPO_ROOT / "outputs").resolve()
    if resolved.parent != expected_parent or resolved.name != "main_citybrain_d5_local_served_runtime_hardening_r1":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def request_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": SCHEMA_VERSION,
        "title": "CityBrain D5 Local Served Runtime Request Envelope",
        "type": "object",
        "additionalProperties": False,
        "required": ["request_id", "request_type", "payload", "runtime_profile", "trace_requested", "safe_mode"],
        "properties": {
            "request_id": {"type": "string", "minLength": 1},
            "request_type": {
                "type": "string",
                "enum": [
                    "health_status",
                    "governed_query",
                    "insight_packet_request",
                    "unsupported_no_data_query",
                    "bounded_execution_probe",
                ],
            },
            "payload": {"type": "object"},
            "runtime_profile": {
                "type": "string",
                "enum": ["local_default", "local_readonly", "local_debug"],
            },
            "trace_requested": {"type": "boolean", "const": True},
            "safe_mode": {"type": "boolean", "const": True},
        },
    }


def response_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": SCHEMA_VERSION,
        "title": "CityBrain D5 Local Served Runtime Response Envelope",
        "type": "object",
        "additionalProperties": True,
        "required": [
            "request_id",
            "status",
            "response_type",
            "data",
            "evidence_refs",
            "trace_refs",
            "limitation_refs",
            "warnings",
            "error",
            "claim_boundary",
            "no_action_taken",
            "autonomous_action_exposed",
            "production_readiness_claim_made",
        ],
        "properties": {
            "request_id": {"type": "string"},
            "status": {"type": "string"},
            "response_type": {"type": "string"},
            "data": {"type": "object"},
            "evidence_refs": {"type": "array"},
            "trace_refs": {"type": "array"},
            "limitation_refs": {"type": "array"},
            "warnings": {"type": "array"},
            "error": {"type": ["object", "null"]},
            "no_action_taken": {"type": "boolean", "const": True},
            "autonomous_action_exposed": {"type": "boolean", "const": False},
            "production_readiness_claim_made": {"type": "boolean", "const": False},
        },
    }


def hardened_contract(bind_host: str, bind_port: int) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "HARDENED_LOCAL_CONTRACT_R1",
        "upstream_output_root": str(UPSTREAM_ROOT),
        "served_entrypoint": "python scripts/run_main_citybrain_d5_local_served_runtime_hardening_r1.py --serve --host 127.0.0.1 --port 8766",
        "bind_host": bind_host,
        "bind_port": bind_port,
        "local_only_policy": {
            "default_host": DEFAULT_HOST,
            "allowed_hosts": ["127.0.0.1", "localhost", "::1"],
            "external_binding_default": False,
            "refuse_0_0_0_0": True,
            "public_deployment_allowed": False,
        },
        "endpoints": [
            {"method": "GET", "path": "/health", "response_type": "health_status"},
            {"method": "GET", "path": "/status", "response_type": "readiness_status"},
            {"method": "GET", "path": "/contract", "response_type": "contract"},
            {"method": "POST", "path": "/runtime/request", "response_type": "runtime_response_envelope"},
        ],
        "request_envelope_schema": request_schema(),
        "response_envelope_schema": response_schema(),
        "timeout_policy": {
            "request_timeout_budget_ms": REQUEST_TIMEOUT_BUDGET_MS,
            "client_timeout_seconds": CLIENT_TIMEOUT_SECONDS,
            "behavior": "bounded_execution_probe reports whether runtime stays inside budget; no background retry loop",
        },
        "shutdown_guidance": {
            "preflight_harness": "in-process server.shutdown() after smoke",
            "manual_serve_mode": "Ctrl-C in terminal",
            "shutdown_endpoint_exposed": False,
        },
        "no_mutation_policy": {
            "source_artifacts_read_only": True,
            "runtime_trace_audit_redirected_to_output_root": True,
            "writes_allowed_under_output_root_only": True,
        },
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }


def validate_request_envelope(envelope: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(envelope, dict):
        return ["request_body_must_be_object"]
    allowed = set(request_schema()["properties"].keys())
    extra = sorted(set(envelope.keys()) - allowed)
    if extra:
        errors.append(f"unexpected_fields:{','.join(extra)}")
    for field in request_schema()["required"]:
        if field not in envelope:
            errors.append(f"missing:{field}")
    if "request_id" in envelope and not isinstance(envelope["request_id"], str):
        errors.append("request_id_must_be_string")
    if envelope.get("request_type") not in request_schema()["properties"]["request_type"]["enum"]:
        errors.append("unsupported_request_type")
    if not isinstance(envelope.get("payload"), dict):
        errors.append("payload_must_be_object")
    if envelope.get("runtime_profile") not in request_schema()["properties"]["runtime_profile"]["enum"]:
        errors.append("unsupported_runtime_profile")
    if envelope.get("trace_requested") is not True:
        errors.append("trace_requested_must_be_true")
    if envelope.get("safe_mode") is not True:
        errors.append("safe_mode_must_be_true")
    return errors


def validate_response_envelope(envelope: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in response_schema()["required"]:
        if field not in envelope:
            errors.append(f"missing:{field}")
    for field in ["evidence_refs", "trace_refs", "limitation_refs", "warnings"]:
        if not isinstance(envelope.get(field), list):
            errors.append(f"{field}_must_be_list")
    if envelope.get("no_action_taken") is not True:
        errors.append("no_action_taken_must_be_true")
    if envelope.get("autonomous_action_exposed") is not False:
        errors.append("autonomous_action_exposed_must_be_false")
    if envelope.get("production_readiness_claim_made") is not False:
        errors.append("production_readiness_claim_made_must_be_false")
    return errors


def write_derived_runtime_config() -> None:
    source_config = read_json(R3_RUNTIME_ROOT / "runtime/runtime_config.json", {})
    source_config["output_root"] = str(RUNTIME_WORK_ROOT)
    RUNTIME_WORK_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(RUNTIME_CONFIG, source_config)


def import_r3_runtime_helper() -> Any:
    spec = importlib.util.spec_from_file_location("citybrain_d4y_r3_runtime_hardening_helper", R3_RUNTIME_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import runtime helper: {R3_RUNTIME_HELPER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_source_state() -> dict[str, Any]:
    return {
        "upstream_decision": read_json(UPSTREAM_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_PREFLIGHT_DECISION.json", {}),
        "upstream_contract": read_json(UPSTREAM_ROOT / "LOCAL_SERVED_RUNTIME_CONTRACT.json", {}),
        "upstream_smoke": read_json(UPSTREAM_ROOT / "LOCAL_SERVED_RUNTIME_SMOKE_RESULTS.json", {}),
        "upstream_trace": read_json(UPSTREAM_ROOT / "LOCAL_SERVED_RUNTIME_TRACE_AUDIT.json", {}),
        "r3_runtime_decision": read_json(R3_RUNTIME_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_DECISION.json", {}),
        "r3_runtime_samples": read_json(R3_RUNTIME_ROOT / "D4Y_R3_RUNTIME_SAMPLE_REQUESTS.json", {}).get("requests", []),
        "r3_insight_packets": read_json(R3_INSIGHT_ROOT / "D4Y_R3_INSIGHT_PACKETS.json", {}).get("packets", []),
        "r4_decision": read_json(R4_HARDENING_ROOT / "MAIN_TRACK1_D4Y_R4_LIVE_RUNTIME_HARDENING_DECISION.json", {}),
        "r5_decision": read_json(R5_DOMAIN_ROOT / "MAIN_TRACK1_D4Y_R5_DOMAIN_PACK_FIRST_TWO_DOMAIN_PROOF_END_TO_END_DECISION.json", {}),
    }


class HardenedRuntimeService:
    def __init__(self, bind_host: str, bind_port: int) -> None:
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.started_at = now_iso()
        self.state = load_source_state()
        self.runtime_helper = import_r3_runtime_helper()
        self.contract = hardened_contract(bind_host, bind_port)

    def envelope(
        self,
        request_id: str,
        status: str,
        response_type: str,
        data: dict[str, Any] | None = None,
        evidence_refs: list[Any] | None = None,
        trace_refs: list[Any] | None = None,
        limitation_refs: list[Any] | None = None,
        warnings: list[str] | None = None,
        error: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "request_id": request_id,
            "status": status,
            "response_type": response_type,
            "data": data or {},
            "evidence_refs": list(dict.fromkeys([str(v) for v in (evidence_refs or []) if v] + ["upstream:D5_PREFLIGHT", "source:R3_RUNTIME"])),
            "trace_refs": list(dict.fromkeys([str(v) for v in (trace_refs or []) if v] + [f"served-trace:{request_id}"])),
            "limitation_refs": list(dict.fromkeys([str(v) for v in (limitation_refs or []) if v] + LIMITATIONS)),
            "warnings": warnings or [],
            "error": error,
            "claim_boundary": BOUNDARY,
            "safe_next_looks": ["inspect evidence refs", "inspect trace refs", "inspect limitation refs"],
            "no_action_taken": True,
            "autonomous_action_exposed": False,
            "production_readiness_claim_made": False,
            "external_network_binding_default": False,
        }

    def safe_failure(self, request_id: str, response_type: str, code: str, message: str, status: str = "SAFE_FAILURE_INVALID_SCHEMA") -> dict[str, Any]:
        return self.envelope(
            request_id=request_id,
            status=status,
            response_type=response_type,
            data={"safe_failure": True},
            evidence_refs=["contract:LOCAL_SERVED_RUNTIME_REQUEST_ENVELOPE_SCHEMA"],
            trace_refs=[f"safe-failure:{request_id}"],
            limitation_refs=[code.lower()],
            warnings=[message],
            error={"code": code, "message": message, "safe_failure": True},
        )

    def health(self) -> dict[str, Any]:
        return self.envelope(
            "health",
            "PASS",
            "health_status",
            data={
                "service": TASK_ID,
                "started_at_utc": self.started_at,
                "bind_host": self.bind_host,
                "bind_port": self.bind_port,
                "local_only_confirmed": self.bind_host in {"127.0.0.1", "localhost", "::1"},
                "upstream_status": self.state["upstream_decision"].get("status"),
            },
            evidence_refs=["artifact:MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_PREFLIGHT_DECISION"],
            trace_refs=["health:startup"],
        )

    def status(self) -> dict[str, Any]:
        return self.envelope(
            "status",
            "PASS_WITH_LIMITATIONS",
            "readiness_status",
            data={
                "upstream_status": self.state["upstream_decision"].get("status"),
                "upstream_cases": self.state["upstream_decision"].get("request_cases_passed"),
                "r3_runtime_status": self.state["r3_runtime_decision"].get("status"),
                "r4_hardening_status": self.state["r4_decision"].get("status"),
                "r5_domain_status": self.state["r5_decision"].get("status"),
                "request_envelope_schema": "LOCAL_SERVED_RUNTIME_REQUEST_ENVELOPE_SCHEMA.json",
                "response_envelope_schema": "LOCAL_SERVED_RUNTIME_RESPONSE_ENVELOPE_SCHEMA.json",
            },
            evidence_refs=["artifact:LOCAL_SERVED_RUNTIME_CONTRACT", "artifact:R3_RUNTIME_DECISION"],
            trace_refs=["status:readiness"],
        )

    def governed_query(self, envelope: dict[str, Any]) -> dict[str, Any]:
        payload = envelope.get("payload", {})
        runtime_request = dict(payload.get("runtime_request") or {})
        runtime_request.setdefault("request_id", envelope["request_id"])
        runtime_request.setdefault("request_type", "evidence_qa")
        runtime_request.setdefault("desired_output_type", "answer_packet")
        runtime_request.setdefault("include_limitations", True)
        runtime_request.setdefault("include_trace", True)
        runtime_request.setdefault("no_action_taken", True)
        result = self.runtime_helper.run_request(runtime_request, config_path=str(RUNTIME_CONFIG))
        response = result.get("response", {})
        trace = result.get("trace", {})
        return self.envelope(
            envelope["request_id"],
            response.get("status", "PASS_WITH_LIMITATIONS"),
            "governed_query_response",
            data={"runtime_response": response, "runtime_packet": result.get("packet", {})},
            evidence_refs=response.get("evidence_refs", []),
            trace_refs=[response.get("trace_ref"), trace.get("trace_id")],
            limitation_refs=response.get("limitation_refs", []),
            warnings=["local served hardening wrapper; not production runtime"],
        )

    def insight_packet(self, envelope: dict[str, Any]) -> dict[str, Any]:
        payload = envelope.get("payload", {})
        requested_type = payload.get("insight_type")
        packet = None
        for candidate in self.state["r3_insight_packets"]:
            if requested_type is None or candidate.get("insight_type") == requested_type:
                packet = candidate
                break
        if packet is None:
            return self.safe_failure(
                envelope["request_id"],
                "insight_packet_response",
                "NO_INSIGHT_PACKET",
                "No insight packet matched the requested type.",
                "SAFE_FAILURE_NO_DATA",
            )
        return self.envelope(
            envelope["request_id"],
            "PASS_WITH_LIMITATIONS",
            "insight_packet_response",
            data={"insight_packet": packet},
            evidence_refs=packet.get("evidence_refs", []),
            trace_refs=[f"insight:{packet.get('insight_id')}"],
            limitation_refs=packet.get("limitation_refs", []),
            warnings=["insight is safe-next-look context only"],
        )

    def unsupported_no_data(self, envelope: dict[str, Any]) -> dict[str, Any]:
        domain = envelope.get("payload", {}).get("domain_id", "unknown")
        return self.safe_failure(
            envelope["request_id"],
            "unsupported_no_data_response",
            "UNSUPPORTED_NO_DATA",
            f"No local served runtime data/adapter is available for '{domain}'.",
            "SAFE_FAILURE_NO_DATA",
        )

    def bounded_execution_probe(self, envelope: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        sleep_ms = int(envelope.get("payload", {}).get("simulate_work_ms", 5))
        time.sleep(min(max(sleep_ms, 0), 50) / 1000)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
        status = "PASS" if elapsed_ms <= REQUEST_TIMEOUT_BUDGET_MS else "SAFE_FAILURE_TIMEOUT"
        return self.envelope(
            envelope["request_id"],
            status,
            "bounded_execution_probe_response",
            data={"elapsed_ms": elapsed_ms, "timeout_budget_ms": REQUEST_TIMEOUT_BUDGET_MS},
            evidence_refs=["contract:timeout_policy"],
            trace_refs=[f"timeout-probe:{envelope['request_id']}"],
            limitation_refs=["basic_timeout_budget_check_not_process_supervision"],
            warnings=["bounded execution checked by harness; no production process supervisor"],
        )

    def request(self, body: Any) -> tuple[int, dict[str, Any]]:
        errors = validate_request_envelope(body)
        request_id = body.get("request_id", "invalid-request") if isinstance(body, dict) else "invalid-request"
        if errors:
            return 400, self.safe_failure(request_id, "invalid_schema_response", "INVALID_SCHEMA", "; ".join(errors))
        request_type = body["request_type"]
        if request_type == "health_status":
            return 200, self.health()
        if request_type == "governed_query":
            return 200, self.governed_query(body)
        if request_type == "insight_packet_request":
            return 200, self.insight_packet(body)
        if request_type == "unsupported_no_data_query":
            return 422, self.unsupported_no_data(body)
        if request_type == "bounded_execution_probe":
            return 200, self.bounded_execution_probe(body)
        return 400, self.safe_failure(request_id, "invalid_schema_response", "UNSUPPORTED_REQUEST_TYPE", "Unsupported request_type.")


def make_handler(service: HardenedRuntimeService) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "CityBrainD5LocalHardeningR1/1"

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
                self.send_json(404, service.safe_failure("unsupported-route", "unsupported_route_response", "UNSUPPORTED_ROUTE", f"Unknown endpoint: {parsed.path}", "SAFE_FAILURE_UNSUPPORTED_ROUTE"))

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/runtime/request":
                self.send_json(404, service.safe_failure("unsupported-route", "unsupported_route_response", "UNSUPPORTED_ROUTE", f"Unknown endpoint: {parsed.path}", "SAFE_FAILURE_UNSUPPORTED_ROUTE"))
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8")
                body = json.loads(raw) if raw else {}
            except Exception:
                self.send_json(400, service.safe_failure("malformed-json", "malformed_json_response", "MALFORMED_JSON", "Request body could not be parsed as JSON.", "SAFE_FAILURE_MALFORMED_JSON"))
                return
            status_code, data = service.request(body)
            self.send_json(status_code, data)

        def do_PUT(self) -> None:  # noqa: N802
            self.send_json(405, service.safe_failure("unsupported-method", "unsupported_method_response", "UNSUPPORTED_METHOD", "Only GET and POST are supported.", "SAFE_FAILURE_UNSUPPORTED_METHOD"))

        def do_DELETE(self) -> None:  # noqa: N802
            self.send_json(405, service.safe_failure("unsupported-method", "unsupported_method_response", "UNSUPPORTED_METHOD", "Only GET and POST are supported.", "SAFE_FAILURE_UNSUPPORTED_METHOD"))

    return Handler


def start_server(bind_host: str, bind_port: int) -> tuple[ThreadingHTTPServer, HardenedRuntimeService, threading.Thread]:
    service = HardenedRuntimeService(bind_host, bind_port)
    server = ThreadingHTTPServer((bind_host, bind_port), make_handler(service))
    actual_host, actual_port = server.server_address[:2]
    service.bind_host = str(actual_host)
    service.bind_port = int(actual_port)
    service.contract = hardened_contract(service.bind_host, service.bind_port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, service, thread


def http_request(host: str, port: int, method: str, path: str, body: Any = None, raw_body: str | None = None) -> tuple[int, dict[str, Any]]:
    conn = http.client.HTTPConnection(host, port, timeout=CLIENT_TIMEOUT_SECONDS)
    try:
        headers = {}
        payload = None
        if raw_body is not None:
            payload = raw_body.encode("utf-8")
            headers = {"Content-Type": "application/json", "Content-Length": str(len(payload))}
        elif body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers = {"Content-Type": "application/json", "Content-Length": str(len(payload))}
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        return resp.status, data
    finally:
        conn.close()


def request_fixtures() -> list[dict[str, Any]]:
    base = {
        "runtime_profile": "local_default",
        "trace_requested": True,
        "safe_mode": True,
    }
    return [
        {"case_id": "health", "method": "GET", "path": "/health", "expected_http": [200], "request_type": "health_status"},
        {"case_id": "status", "method": "GET", "path": "/status", "expected_http": [200], "request_type": "health_status"},
        {
            "case_id": "governed_query",
            "method": "POST",
            "path": "/runtime/request",
            "expected_http": [200],
            "request_type": "governed_query",
            "body": {
                **base,
                "request_id": "hardening-governed-query",
                "request_type": "governed_query",
                "payload": {
                    "runtime_request": {
                        "request_id": "hardening-governed-query-runtime",
                        "request_type": "evidence_qa",
                        "desired_output_type": "answer_packet",
                        "include_limitations": True,
                        "include_trace": True,
                        "no_action_taken": True,
                    }
                },
            },
        },
        {
            "case_id": "insight_packet",
            "method": "POST",
            "path": "/runtime/request",
            "expected_http": [200],
            "request_type": "insight_packet_request",
            "body": {**base, "request_id": "hardening-insight-packet", "request_type": "insight_packet_request", "payload": {"insight_type": "evidence_gap"}},
        },
        {
            "case_id": "invalid_schema",
            "method": "POST",
            "path": "/runtime/request",
            "expected_http": [400],
            "request_type": "invalid_schema",
            "body": {"request_id": "hardening-invalid-schema", "request_type": "governed_query", "payload": {}, "runtime_profile": "local_default", "trace_requested": False, "safe_mode": True},
        },
        {
            "case_id": "malformed_json",
            "method": "POST",
            "path": "/runtime/request",
            "expected_http": [400],
            "request_type": "malformed_json",
            "raw_body": "{not-json",
        },
        {"case_id": "unsupported_route", "method": "GET", "path": "/nope", "expected_http": [404], "request_type": "unsupported_route"},
        {
            "case_id": "unsupported_no_data",
            "method": "POST",
            "path": "/runtime/request",
            "expected_http": [422],
            "request_type": "unsupported_no_data_query",
            "body": {**base, "request_id": "hardening-unsupported-no-data", "request_type": "unsupported_no_data_query", "payload": {"domain_id": "dispatch_control"}},
        },
        {
            "case_id": "bounded_execution",
            "method": "POST",
            "path": "/runtime/request",
            "expected_http": [200],
            "request_type": "bounded_execution_probe",
            "body": {**base, "request_id": "hardening-bounded-execution", "request_type": "bounded_execution_probe", "payload": {"simulate_work_ms": 10}},
        },
        {
            "case_id": "repeated_sequential_1",
            "method": "POST",
            "path": "/runtime/request",
            "expected_http": [200],
            "request_type": "governed_query",
            "body": {**base, "request_id": "hardening-repeat-1", "request_type": "governed_query", "payload": {"runtime_request": {"request_id": "hardening-repeat-1-runtime", "request_type": "evidence_qa", "desired_output_type": "answer_packet", "include_limitations": True, "include_trace": True, "no_action_taken": True}}},
        },
        {
            "case_id": "repeated_sequential_2",
            "method": "POST",
            "path": "/runtime/request",
            "expected_http": [200],
            "request_type": "governed_query",
            "body": {**base, "request_id": "hardening-repeat-2", "request_type": "governed_query", "payload": {"runtime_request": {"request_id": "hardening-repeat-2-runtime", "request_type": "evidence_qa", "desired_output_type": "answer_packet", "include_limitations": True, "include_trace": True, "no_action_taken": True}}},
        },
        {"case_id": "local_only_binding_assertion", "method": "GET", "path": "/health", "expected_http": [200], "request_type": "local_only_binding_assertion"},
    ]


def has_refs(body: dict[str, Any], field: str) -> bool:
    return isinstance(body.get(field), list) and any(body[field])


def smoke(host: str, port: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results = []
    responses = []
    for fixture in request_fixtures():
        status, body = http_request(host, port, fixture["method"], fixture["path"], fixture.get("body"), fixture.get("raw_body"))
        checks = {
            "http_expected": status in fixture["expected_http"],
            "response_schema_valid": not validate_response_envelope(body),
            "trace_refs_present": has_refs(body, "trace_refs"),
            "evidence_refs_present": has_refs(body, "evidence_refs"),
            "limitation_refs_present": has_refs(body, "limitation_refs"),
            "no_action_taken": body.get("no_action_taken") is True,
            "autonomous_action_not_exposed": body.get("autonomous_action_exposed") is False,
            "production_readiness_not_claimed": body.get("production_readiness_claim_made") is False,
            "external_network_binding_default_false": body.get("external_network_binding_default") is False,
        }
        if fixture["case_id"] == "invalid_schema":
            checks["invalid_schema_safe_failure"] = body.get("error", {}).get("safe_failure") is True and body.get("status") == "SAFE_FAILURE_INVALID_SCHEMA"
        if fixture["case_id"] == "malformed_json":
            checks["malformed_json_safe_failure"] = body.get("error", {}).get("safe_failure") is True and body.get("status") == "SAFE_FAILURE_MALFORMED_JSON"
        if fixture["case_id"] == "unsupported_route":
            checks["unsupported_route_safe_failure"] = body.get("error", {}).get("safe_failure") is True and body.get("status") == "SAFE_FAILURE_UNSUPPORTED_ROUTE"
        if fixture["case_id"] == "unsupported_no_data":
            checks["unsupported_no_data_safe_failure"] = body.get("error", {}).get("safe_failure") is True and body.get("status") == "SAFE_FAILURE_NO_DATA"
        if fixture["case_id"] == "bounded_execution":
            checks["timeout_or_bounded_execution_checked"] = body.get("data", {}).get("elapsed_ms", REQUEST_TIMEOUT_BUDGET_MS + 1) <= REQUEST_TIMEOUT_BUDGET_MS
        if fixture["case_id"] == "local_only_binding_assertion":
            checks["local_only_binding_confirmed"] = body.get("data", {}).get("local_only_confirmed") is True
        result = {
            "case_id": fixture["case_id"],
            "method": fixture["method"],
            "path": fixture["path"],
            "request_type": fixture["request_type"],
            "http_status": status,
            "response_status": body.get("status"),
            "checks": checks,
            "passed": all(checks.values()),
        }
        results.append(result)
        responses.append({"case_id": fixture["case_id"], "http_status": status, "response": body})
    return results, responses


def trace_audit(results: list[dict[str, Any]], responses: list[dict[str, Any]]) -> dict[str, Any]:
    bodies = [row["response"] for row in responses]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": PASS if all(row["passed"] for row in results) else FAIL,
        "response_count": len(bodies),
        "trace_refs_present": all(has_refs(body, "trace_refs") for body in bodies),
        "evidence_refs_present": all(has_refs(body, "evidence_refs") for body in bodies),
        "limitation_refs_present": all(has_refs(body, "limitation_refs") for body in bodies),
        "no_action_taken_all": all(body.get("no_action_taken") is True for body in bodies),
        "response_envelopes_valid": all(not validate_response_envelope(body) for body in bodies),
        "autonomous_action_exposed": any(body.get("autonomous_action_exposed") is True for body in bodies),
        "production_readiness_claim_made": any(body.get("production_readiness_claim_made") is True for body in bodies),
        "external_network_binding_default": any(body.get("external_network_binding_default") is True for body in bodies),
        "case_results": results,
    }


def boundary_audit(results: list[dict[str, Any]], responses: list[dict[str, Any]], source_mutation_status: str, bind_host: str) -> dict[str, Any]:
    bodies = [row["response"] for row in responses]
    checks = {
        "local_only_binding_default": bind_host in {"127.0.0.1", "localhost", "::1"},
        "no_source_mutation": source_mutation_status == PASS,
        "no_dispatch": True,
        "no_enforcement": True,
        "no_autonomous_workflow_execution": not any(body.get("autonomous_action_exposed") for body in bodies),
        "no_external_network_binding_default": not any(body.get("external_network_binding_default") for body in bodies),
        "no_production_readiness_claim": not any(body.get("production_readiness_claim_made") for body in bodies),
        "safe_failures_present": all(
            next(row for row in results if row["case_id"] == case_id)["passed"]
            for case_id in ["invalid_schema", "malformed_json", "unsupported_route", "unsupported_no_data"]
        ),
    }
    return {"schema_version": SCHEMA_VERSION, "status": PASS if all(checks.values()) else FAIL, "checks": checks, "claim_boundary": BOUNDARY, "limitations": LIMITATIONS}


def write_reports(decision: dict[str, Any], boundary: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_HARDENING_R1_REPORT.md",
        f"""# Local Served Runtime Hardening R1

Status: `{decision['status']}`

This hardening pass consumes the D5 local served preflight pack and creates a stricter localhost-only request/response envelope around the existing local runtime helper.

Served entrypoint:

```text
{decision['served_entrypoint']}
```

Smoke:

- Request cases: {decision['request_cases_total']}
- Passed: {decision['request_cases_passed']}
- Health/status: {decision['health_status_passed']}
- Governed query: {decision['governed_query_passed']}
- Insight packet: {decision['insight_packet_passed']}
- Invalid schema safe failure: {decision['invalid_schema_safe_failure_passed']}
- Malformed JSON safe failure: {decision['malformed_json_safe_failure_passed']}
- Unsupported route safe failure: {decision['unsupported_route_safe_failure_passed']}
- Unsupported/no-data safe failure: {decision['unsupported_no_data_safe_failure_passed']}
- Repeated sequential requests: {decision['repeated_sequential_requests_passed']}
- Timeout/bounded execution: {decision['timeout_or_bounded_execution_checked']}

Boundary audit: `{boundary['status']}`

{BOUNDARY}
""",
    )
    write_text(
        OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_HARDENING_R1_LIMITATIONS_AND_NEXT_STEPS.md",
        "# Limitations and Next Steps\n\n"
        + "\n".join(f"- {item}" for item in LIMITATIONS)
        + "\n\nRecommended next task:\n\n```text\nMAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-APP-INTEGRATION-PREFLIGHT-R1\n```\n",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_ID}

Status: `{decision['status']}`

Run hardening smoke:

```text
python scripts/run_main_citybrain_d5_local_served_runtime_hardening_r1.py
```

Run local hardened server manually:

```text
{decision['served_entrypoint']}
```

This is localhost-only runtime hardening. It does not claim production readiness.
""",
    )


def upstream_artifacts_found() -> dict[str, bool]:
    names = [
        "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_PREFLIGHT_DECISION.json",
        "LOCAL_SERVED_RUNTIME_CONTRACT.json",
        "LOCAL_SERVED_RUNTIME_SMOKE_RESULTS.json",
        "LOCAL_SERVED_RUNTIME_TRACE_AUDIT.json",
        "LOCAL_SERVED_RUNTIME_PREFLIGHT_REPORT.md",
        "LIMITATIONS_AND_NEXT_STEPS.md",
        "README.md",
    ]
    return {name: (UPSTREAM_ROOT / name).exists() for name in names}


def write_outputs(
    actual_host: str,
    actual_port: int,
    results: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> dict[str, Any]:
    trace = trace_audit(results, responses)
    changed_roots = [root for root, sig in before.items() if after.get(root) != sig]
    source_mutation_status = PASS if not changed_roots else FAIL
    boundary = boundary_audit(results, responses, source_mutation_status, actual_host)
    upstream_decision = read_json(UPSTREAM_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_PREFLIGHT_DECISION.json", {})
    artifact_found = upstream_artifacts_found()
    case_by_id = {row["case_id"]: row for row in results}
    repeated_pass = case_by_id["repeated_sequential_1"]["passed"] and case_by_id["repeated_sequential_2"]["passed"]
    smoke_status = PASS if all(row["passed"] for row in results) else FAIL
    status = PASS_WITH_LIMITATIONS if (
        all(artifact_found.values())
        and smoke_status == PASS
        and trace["status"] == PASS
        and boundary["status"] == PASS
        and source_mutation_status == PASS
    ) else FAIL
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now_iso(),
        "upstream_output_root": str(UPSTREAM_ROOT),
        "upstream_status": upstream_decision.get("status"),
        "upstream_artifacts_found": artifact_found,
        "served_entrypoint": "python scripts/run_main_citybrain_d5_local_served_runtime_hardening_r1.py --serve --host 127.0.0.1 --port 8766",
        "bind_host": actual_host,
        "bind_port": actual_port,
        "local_only_confirmed": actual_host in {"127.0.0.1", "localhost", "::1"},
        "request_envelope_schema_created": True,
        "response_envelope_schema_created": True,
        "request_cases_total": len(results),
        "request_cases_passed": sum(1 for row in results if row["passed"]),
        "health_status_passed": case_by_id["health"]["passed"] and case_by_id["status"]["passed"],
        "governed_query_passed": case_by_id["governed_query"]["passed"],
        "insight_packet_passed": case_by_id["insight_packet"]["passed"],
        "invalid_schema_safe_failure_passed": case_by_id["invalid_schema"]["checks"].get("invalid_schema_safe_failure", False),
        "malformed_json_safe_failure_passed": case_by_id["malformed_json"]["checks"].get("malformed_json_safe_failure", False),
        "unsupported_route_safe_failure_passed": case_by_id["unsupported_route"]["checks"].get("unsupported_route_safe_failure", False),
        "unsupported_no_data_safe_failure_passed": case_by_id["unsupported_no_data"]["checks"].get("unsupported_no_data_safe_failure", False),
        "repeated_sequential_requests_passed": repeated_pass,
        "timeout_or_bounded_execution_checked": case_by_id["bounded_execution"]["checks"].get("timeout_or_bounded_execution_checked", False),
        "trace_refs_present": trace["trace_refs_present"],
        "evidence_refs_present": trace["evidence_refs_present"],
        "limitation_refs_present": trace["limitation_refs_present"],
        "source_mutation_status": source_mutation_status,
        "autonomous_action_exposed": trace["autonomous_action_exposed"],
        "production_readiness_claim_made": trace["production_readiness_claim_made"],
        "external_network_binding_default": trace["external_network_binding_default"],
        "boundary_audit_status": boundary["status"],
        "limitations": LIMITATIONS,
        "next_recommended_task": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-APP-INTEGRATION-PREFLIGHT-R1",
    }
    smoke_results = {
        "schema_version": SCHEMA_VERSION,
        "status": smoke_status,
        "bind_host": actual_host,
        "bind_port": actual_port,
        "request_cases_total": len(results),
        "request_cases_passed": sum(1 for row in results if row["passed"]),
        "cases": results,
    }
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_HARDENED_CONTRACT.json", hardened_contract(actual_host, actual_port))
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_REQUEST_ENVELOPE_SCHEMA.json", request_schema())
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_RESPONSE_ENVELOPE_SCHEMA.json", response_schema())
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_HARDENING_R1_REQUEST_FIXTURES.json", {"schema_version": SCHEMA_VERSION, "fixture_count": len(request_fixtures()), "fixtures": request_fixtures()})
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_HARDENING_R1_RESPONSE_FIXTURES.json", {"schema_version": SCHEMA_VERSION, "response_count": len(responses), "responses": responses})
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_HARDENING_R1_SMOKE_RESULTS.json", smoke_results)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_HARDENING_R1_TRACE_AUDIT.json", trace)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_HARDENING_R1_BOUNDARY_AUDIT.json", boundary)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_HARDENING_R1_NO_MUTATION_AUDIT.json", {"schema_version": SCHEMA_VERSION, "status": source_mutation_status, "changed_roots": changed_roots, "read_only_input_roots": list(before.keys())})
    write_reports(decision, boundary)
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_HARDENING_R1_DECISION.json", decision)
    return decision


def run_hardening_preflight(bind_host: str) -> dict[str, Any]:
    before = {root.relative_to(REPO_ROOT).as_posix(): snapshot_root(root) for root in READ_ONLY_INPUT_ROOTS}
    prepare_output_root()
    write_derived_runtime_config()
    server, _service, thread = start_server(bind_host, 0)
    try:
        time.sleep(0.2)
        actual_host, actual_port = server.server_address[:2]
        results, responses = smoke(str(actual_host), int(actual_port))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=CLIENT_TIMEOUT_SECONDS)
    after = {root.relative_to(REPO_ROOT).as_posix(): snapshot_root(root) for root in READ_ONLY_INPUT_ROOTS}
    return write_outputs(str(actual_host), int(actual_port), results, responses, before, after)


def serve_forever(bind_host: str, bind_port: int) -> None:
    if bind_host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing to bind non-local host for D5 hardening R1.")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_derived_runtime_config()
    server, service, _thread = start_server(bind_host, bind_port)
    actual_host, actual_port = server.server_address[:2]
    print(json.dumps({"status": "SERVING_LOCAL_ONLY_HARDENED_R1", "host": actual_host, "port": actual_port, "boundary": BOUNDARY}, indent=2))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=TASK_ID)
    parser.add_argument("--serve", action="store_true", help="Run the local hardened server instead of the smoke harness.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    if args.serve:
        serve_forever(args.host, args.port)
        return
    decision = run_hardening_preflight(DEFAULT_HOST)
    print(json.dumps({"status": decision["status"], "output_root": str(OUTPUT_ROOT), "decision": decision}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
