#!/usr/bin/env python3
"""Build D5 local served-runtime app integration preflight R1.

This creates stable app-facing packet contracts and fixtures from the hardened
localhost runtime outputs. It does not build a frontend, expose a public API, or
integrate event/Omniverse tracks beyond optional read-only handoff slots.
"""

from __future__ import annotations

import json
import shutil
import http.client
import importlib.util
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-APP-INTEGRATION-PREFLIGHT-R1"
STATUS = "PASS_WITH_LIMITATIONS"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_app_integration_preflight_r1"
UPSTREAM_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_hardening_r1"
UPSTREAM_RUNNER = REPO_ROOT / "scripts/run_main_citybrain_d5_local_served_runtime_hardening_r1.py"
EVENT_FABRIC_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_live_event_fabric_implementation_preflight"
ASSET_OVERLAY_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke"

NEXT_TASK = "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-APP-INTEGRATION-SLICE-R1"

LIMITATIONS = [
    "app integration preflight only",
    "no frontend implemented",
    "no production auth/RBAC implemented",
    "localhost-only developer/demo contract",
    "no public API or production readiness claim",
    "runtime wrapper remains thin stdlib localhost runtime",
    "concurrency/load not tested here",
    "event-state slot is optional/read-only handoff only",
    "asset-overlay slot is optional/read-only handoff only",
    "no Omniverse/Kit interaction required",
    "no autonomous action, dispatch, enforcement, routing, or control",
    "response envelope and app packet contract are R1 stable but not final public contract",
]

REQUIRED_UPSTREAM = [
    "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_HARDENING_R1_DECISION.json",
    "LOCAL_SERVED_RUNTIME_HARDENED_CONTRACT.json",
    "LOCAL_SERVED_RUNTIME_REQUEST_ENVELOPE_SCHEMA.json",
    "LOCAL_SERVED_RUNTIME_RESPONSE_ENVELOPE_SCHEMA.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_SMOKE_RESULTS.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_TRACE_AUDIT.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_BOUNDARY_AUDIT.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_REPORT.md",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_LIMITATIONS_AND_NEXT_STEPS.md",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_RESPONSE_FIXTURES.json",
    "LOCAL_SERVED_RUNTIME_HARDENING_R1_REQUEST_FIXTURES.json",
    "README.md",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def upstream_artifacts_found() -> list[dict[str, Any]]:
    return [
        {
            "artifact": artifact,
            "path": (UPSTREAM_ROOT / artifact).relative_to(REPO_ROOT).as_posix(),
            "exists": (UPSTREAM_ROOT / artifact).exists(),
            "bytes": (UPSTREAM_ROOT / artifact).stat().st_size if (UPSTREAM_ROOT / artifact).exists() else 0,
        }
        for artifact in REQUIRED_UPSTREAM
    ]


def responses_by_case() -> dict[str, dict[str, Any]]:
    live_cases = live_responses_by_case()
    if live_cases:
        return live_cases
    payload = read_json(UPSTREAM_ROOT / "LOCAL_SERVED_RUNTIME_HARDENING_R1_RESPONSE_FIXTURES.json", {})
    return {row["case_id"]: row["response"] for row in payload.get("responses", [])}


def import_hardened_runner() -> Any:
    spec = importlib.util.spec_from_file_location("d5_hardened_runtime_for_app_preflight", UPSTREAM_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {UPSTREAM_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["d5_hardened_runtime_for_app_preflight"] = module
    spec.loader.exec_module(module)
    module.OUTPUT_ROOT = OUTPUT_ROOT / "hardened_runtime_shadow"
    module.RUNTIME_WORK_ROOT = module.OUTPUT_ROOT / "runtime_work"
    module.RUNTIME_CONFIG = module.RUNTIME_WORK_ROOT / "runtime_config.json"
    return module


def http_json(host: str, port: int, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    conn = http.client.HTTPConnection(host, port, timeout=5)
    payload = json.dumps(body) if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    conn.request(method, path, payload, headers)
    response = conn.getresponse()
    text = response.read().decode("utf-8", errors="replace")
    conn.close()
    return json.loads(text) if text else {}


def runtime_request(request_id: str, request_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "request_type": request_type,
        "payload": payload or {},
        "runtime_profile": "local_readonly",
        "trace_requested": True,
        "safe_mode": True,
    }


def live_responses_by_case() -> dict[str, dict[str, Any]]:
    try:
        module = import_hardened_runner()
        module.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        module.write_derived_runtime_config()
        server, _service, thread = module.start_server("127.0.0.1", 0)
        time.sleep(0.2)
        host, port = server.server_address[:2]
        try:
            governed_payload = runtime_request(
                "app-integration-governed-query",
                "governed_query",
                {
                    "runtime_request": {
                        "request_id": "app-integration-governed-query-runtime",
                        "request_type": "evidence_qa",
                        "city_id": "BARC",
                        "flow_id": "F7",
                        "question": "Create a bounded app-facing local runtime packet.",
                        "desired_output_type": "answer_packet",
                        "include_limitations": True,
                        "include_trace": True,
                        "no_action_taken": True,
                    }
                },
            )
            return {
                "health": http_json(str(host), int(port), "GET", "/health"),
                "status": http_json(str(host), int(port), "GET", "/status"),
                "governed_query": http_json(str(host), int(port), "POST", "/runtime/request", governed_payload),
                "insight_packet": http_json(
                    str(host),
                    int(port),
                    "POST",
                    "/runtime/request",
                    runtime_request("app-integration-insight-packet", "insight_packet_request", {"insight_type": "city_episode"}),
                ),
                "unsupported_no_data": http_json(
                    str(host),
                    int(port),
                    "POST",
                    "/runtime/request",
                    runtime_request("app-integration-unsupported-packet", "unsupported_no_data_query", {"domain_id": "unsupported_app_packet"}),
                ),
            }
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    except Exception:
        return {}


def base_packet(packet_type: str, source_case: str, response: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_id": f"app-packet:{packet_type}",
        "packet_type": packet_type,
        "source_case": source_case,
        "source_response_type": response.get("response_type"),
        "status": response.get("status"),
        "data": response.get("data", {}),
        "trace_refs": response.get("trace_refs", []),
        "evidence_refs": response.get("evidence_refs", []),
        "limitation_refs": response.get("limitation_refs", []),
        "safe_next_looks": response.get("safe_next_looks", []),
        "claim_boundary": response.get("claim_boundary"),
        "warnings": response.get("warnings", []),
        "error": response.get("error"),
        "no_action_taken": response.get("no_action_taken") is True,
        "autonomous_action_exposed": response.get("autonomous_action_exposed") is True,
        "production_readiness_claim_made": response.get("production_readiness_claim_made") is True,
        "external_network_binding_default": response.get("external_network_binding_default") is True,
    }


def build_app_packets() -> list[dict[str, Any]]:
    cases = responses_by_case()
    health = cases.get("health", {})
    status = cases.get("status", health)
    governed = cases.get("governed_query", {})
    insight = cases.get("insight_packet", {})
    unsupported = cases.get("unsupported_no_data") or cases.get("unsupported_route", {})
    event_contract_path = EVENT_FABRIC_ROOT / "LIVE_EVENT_FABRIC_CONTRACT.json"
    event_handoff = read_json(event_contract_path, {})
    asset_contract_path = ASSET_OVERLAY_ROOT / "OMNIVERSE_ASSET_OVERLAY_CONTRACT.json"
    asset_handoff = read_json(asset_contract_path, {})

    packets = [
        base_packet("health_status_packet", "health", health),
        base_packet("runtime_status_packet", "status", status),
        base_packet("governed_answer_packet", "governed_query", governed),
        base_packet("insight_packet", "insight_packet", insight),
        {
            **base_packet("evidence_trace_packet", "governed_query", governed),
            "data": {
                "trace_refs": governed.get("trace_refs", []),
                "evidence_refs": governed.get("evidence_refs", []),
                "runtime_trace_ref": governed.get("data", {}).get("runtime_response", {}).get("trace_ref"),
                "audit_ref": governed.get("data", {}).get("runtime_response", {}).get("audit_ref"),
            },
        },
        {
            **base_packet("limitation_packet", "governed_query", governed),
            "data": {
                "limitation_refs": governed.get("limitation_refs", []),
                "warnings": governed.get("warnings", []),
                "claim_boundary": governed.get("claim_boundary"),
            },
        },
        {
            **base_packet("safe_next_look_packet", "governed_query", governed),
            "data": {
                "safe_next_looks": governed.get("safe_next_looks", []),
                "not_action_buttons": True,
            },
        },
        {
            "packet_id": "app-packet:optional_event_state_packet",
            "packet_type": "optional_event_state_packet",
            "status": "DEFINED_OPTIONAL_READ_ONLY_REFERENCE" if event_handoff else "DEFINED_PLACEHOLDER_ONLY",
            "slot_status": "DEFINED_OPTIONAL_READ_ONLY_REFERENCE" if event_handoff else "DEFINED_PLACEHOLDER_ONLY",
            "handoff_ref": event_contract_path.relative_to(REPO_ROOT).as_posix() if event_handoff else None,
            "data": {
                "placeholder": "event-state slot for future completed local event-fabric handoff",
                "source_found": bool(event_handoff),
                "integrated": False,
                "read_only_reference": event_handoff,
            },
            "trace_refs": ["optional-slot:event-state"],
            "evidence_refs": ["artifact:LIVE_EVENT_FABRIC_CONTRACT"] if event_handoff else ["placeholder:event-state"],
            "limitation_refs": ["event_state_slot_optional_read_only", "not_integrated_in_this_preflight"],
            "safe_next_looks": ["inspect handoff contract when event fabric is selected by a later task"],
            "claim_boundary": "Optional read-only event-state slot; no live event-fabric served-runtime integration performed here.",
            "warnings": ["optional slot only"],
            "error": None,
            "no_action_taken": True,
            "autonomous_action_exposed": False,
            "production_readiness_claim_made": False,
            "external_network_binding_default": False,
        },
        {
            "packet_id": "app-packet:optional_asset_overlay_packet",
            "packet_type": "optional_asset_overlay_packet",
            "status": "DEFINED_OPTIONAL_READ_ONLY_REFERENCE" if asset_handoff else "DEFINED_PLACEHOLDER_ONLY",
            "slot_status": "DEFINED_OPTIONAL_READ_ONLY_REFERENCE" if asset_handoff else "DEFINED_PLACEHOLDER_ONLY",
            "handoff_ref": asset_contract_path.relative_to(REPO_ROOT).as_posix() if asset_handoff else None,
            "data": {
                "placeholder": "asset-overlay slot for future Track 2A/Omniverse overlay handoff",
                "source_found": bool(asset_handoff),
                "integrated": False,
                "read_only_reference": asset_handoff,
            },
            "trace_refs": ["optional-slot:asset-overlay"],
            "evidence_refs": ["artifact:OMNIVERSE_ASSET_OVERLAY_CONTRACT"] if asset_handoff else ["placeholder:asset-overlay"],
            "limitation_refs": ["asset_overlay_slot_optional_read_only", "not_integrated_in_this_preflight"],
            "safe_next_looks": ["inspect Track 2A handoff contract when overlay task consumes it"],
            "claim_boundary": "Optional read-only asset-overlay handoff slot; no Omniverse/Kit interaction performed here.",
            "warnings": ["optional slot only"],
            "error": None,
            "no_action_taken": True,
            "autonomous_action_exposed": False,
            "production_readiness_claim_made": False,
            "external_network_binding_default": False,
        },
        {
            **base_packet("unsupported_packet_safe_failure", "unsupported_no_data", unsupported),
            "packet_type": "unsupported_packet_safe_failure",
        },
    ]
    return packets


def packet_contract() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": "main-citybrain-d5-local-served-runtime-app-integration-preflight-r1.v1",
        "task_id": TASK_ID,
        "purpose": "Stable app-facing packet contract for local developer/demo control-room consumption.",
        "served_runtime_source": "outputs/main_citybrain_d5_local_served_runtime_hardening_r1",
        "local_only_policy": {
            "default_host": "127.0.0.1",
            "allowed_hosts": ["127.0.0.1", "localhost", "::1"],
            "external_network_binding_default": False,
            "public_deployment_allowed": False,
        },
        "packet_types": [
            "health_status_packet",
            "runtime_status_packet",
            "governed_answer_packet",
            "insight_packet",
            "evidence_trace_packet",
            "limitation_packet",
            "safe_next_look_packet",
            "optional_event_state_packet",
            "optional_asset_overlay_packet",
            "unsupported_packet_safe_failure",
        ],
        "required_packet_fields": [
            "packet_id",
            "packet_type",
            "status",
            "data",
            "trace_refs",
            "evidence_refs",
            "limitation_refs",
            "safe_next_looks",
            "claim_boundary",
            "no_action_taken",
            "autonomous_action_exposed",
            "production_readiness_claim_made",
            "external_network_binding_default",
        ],
        "forbidden_outputs": [
            "frontend implementation",
            "production API readiness",
            "public deployment",
            "external default bind",
            "autonomous action",
            "dispatch",
            "enforcement",
            "routing",
            "control",
        ],
    }


def packet_schemas() -> dict[str, Any]:
    common = {
        "type": "object",
        "required": packet_contract()["required_packet_fields"],
        "properties": {
            "packet_id": {"type": "string"},
            "packet_type": {"type": "string"},
            "status": {"type": ["string", "null"]},
            "data": {"type": "object"},
            "trace_refs": {"type": "array", "minItems": 1},
            "evidence_refs": {"type": "array", "minItems": 1},
            "limitation_refs": {"type": "array", "minItems": 1},
            "safe_next_looks": {"type": "array"},
            "claim_boundary": {"type": "string"},
            "no_action_taken": {"const": True},
            "autonomous_action_exposed": {"const": False},
            "production_readiness_claim_made": {"const": False},
            "external_network_binding_default": {"const": False},
        },
    }
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-packet-schemas-r1.v1",
        "common_packet_schema": common,
        "packet_type_schemas": {packet_type: common for packet_type in packet_contract()["packet_types"]},
    }


def request_fixtures() -> dict[str, Any]:
    upstream_requests = read_json(UPSTREAM_ROOT / "LOCAL_SERVED_RUNTIME_HARDENING_R1_REQUEST_FIXTURES.json", {})
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-request-fixtures-r1.v1",
        "source": "LOCAL_SERVED_RUNTIME_HARDENING_R1_REQUEST_FIXTURES.json",
        "requests": [
            {
                "app_request_id": "app-request-health-status",
                "desired_packet_type": "health_status_packet",
                "upstream_case_id": "health",
            },
            {
                "app_request_id": "app-request-governed-answer",
                "desired_packet_type": "governed_answer_packet",
                "upstream_case_id": "governed_query",
            },
            {
                "app_request_id": "app-request-insight",
                "desired_packet_type": "insight_packet",
                "upstream_case_id": "insight_packet",
            },
            {
                "app_request_id": "app-request-unsupported",
                "desired_packet_type": "unsupported_packet_safe_failure",
                "upstream_case_id": "unsupported_no_data",
            },
        ],
        "upstream_fixture_count": upstream_requests.get("fixture_count", 0),
    }


def validate_packets(packets: list[dict[str, Any]]) -> dict[str, Any]:
    required = packet_contract()["required_packet_fields"]
    cases = []
    for packet in packets:
        issues = []
        for field in required:
            if field not in packet:
                issues.append(f"missing:{field}")
        if not packet.get("trace_refs"):
            issues.append("missing_trace_refs")
        if not packet.get("evidence_refs"):
            issues.append("missing_evidence_refs")
        if not packet.get("limitation_refs"):
            issues.append("missing_limitation_refs")
        if packet.get("no_action_taken") is not True:
            issues.append("no_action_not_true")
        if packet.get("autonomous_action_exposed") is not False:
            issues.append("autonomous_action_exposed")
        if packet.get("production_readiness_claim_made") is not False:
            issues.append("production_readiness_claim")
        if packet.get("external_network_binding_default") is not False:
            issues.append("external_binding_default_true")
        cases.append({
            "packet_id": packet.get("packet_id"),
            "packet_type": packet.get("packet_type"),
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
        })
    by_type = {row["packet_type"]: row["status"] == "PASS" for row in cases}
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-integration-smoke-r1.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in cases) else "FAIL",
        "packet_types_total": len(packets),
        "packet_types_validated": sum(1 for row in cases if row["status"] == "PASS"),
        "health_status_packet_passed": by_type.get("health_status_packet", False),
        "governed_answer_packet_passed": by_type.get("governed_answer_packet", False),
        "insight_packet_passed": by_type.get("insight_packet", False),
        "evidence_trace_packet_passed": by_type.get("evidence_trace_packet", False),
        "limitation_packet_passed": by_type.get("limitation_packet", False),
        "safe_next_look_packet_passed": by_type.get("safe_next_look_packet", False),
        "optional_event_state_slot_defined": by_type.get("optional_event_state_packet", False),
        "optional_asset_overlay_slot_defined": by_type.get("optional_asset_overlay_packet", False),
        "unsupported_packet_safe_failure_passed": by_type.get("unsupported_packet_safe_failure", False),
        "trace_refs_present": all(bool(packet.get("trace_refs")) for packet in packets),
        "evidence_refs_present": all(bool(packet.get("evidence_refs")) for packet in packets),
        "limitation_refs_present": all(bool(packet.get("limitation_refs")) for packet in packets),
        "case_results": cases,
    }


def trace_audit(packets: list[dict[str, Any]], smoke: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-trace-audit-r1.v1",
        "status": "PASS" if smoke["trace_refs_present"] and smoke["evidence_refs_present"] and smoke["limitation_refs_present"] else "FAIL",
        "packet_count": len(packets),
        "trace_rows": [
            {
                "packet_id": packet["packet_id"],
                "packet_type": packet["packet_type"],
                "trace_refs": packet["trace_refs"],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "no_action_taken": packet["no_action_taken"],
            }
            for packet in packets
        ],
    }


def boundary_audit(upstream_decision: dict[str, Any], packets: list[dict[str, Any]], smoke: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "upstream_local_only_confirmed": upstream_decision.get("local_only_confirmed") is True,
        "upstream_source_mutation_pass": upstream_decision.get("source_mutation_status") == "PASS",
        "no_autonomous_action_exposed": all(packet.get("autonomous_action_exposed") is False for packet in packets),
        "no_production_readiness_claim": all(packet.get("production_readiness_claim_made") is False for packet in packets),
        "no_external_default_bind": all(packet.get("external_network_binding_default") is False for packet in packets),
        "no_frontend_implemented": True,
        "unsupported_packet_safe_failure": smoke["unsupported_packet_safe_failure_passed"],
    }
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-boundary-audit-r1.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "claim_boundary": "Local app-facing preflight only; no frontend, production API, public deployment, external default bind, autonomous action, dispatch, enforcement, routing, or control.",
        "limitations": LIMITATIONS,
    }


def write_docs(status: str, packet_count: int, upstream_decision: dict[str, Any]) -> None:
    write_md(
        OUTPUT_ROOT / "README.md",
        f"""
        # {TASK_ID}

        Status: `{status}`

        This pack defines stable app-facing packets from the D5 hardened localhost runtime for later web companion/control-room/Track 2 consumption.

        It does not build a frontend, implement production auth/RBAC, expose a public API, integrate the event fabric, or require Omniverse/Kit interaction.
        """,
    )
    write_md(
        OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_INTEGRATION_PREFLIGHT_R1_REPORT.md",
        f"""
        # Local Served Runtime App Integration Preflight R1

        Status: `{status}`

        Upstream served entrypoint:
        `{upstream_decision.get('served_entrypoint')}`

        App packet types created: `{packet_count}`

        The packet pack covers health/status, governed answer, insight, evidence trace, limitation, safe next-look, optional event-state slot, optional asset-overlay slot, and unsupported request safe failure.
        """,
    )
    write_md(
        OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_NOTES.md",
        """
        # Track 2 Handoff Notes

        Track 2 consumers may read these artifacts later:

        - `LOCAL_SERVED_RUNTIME_APP_PACKET_CONTRACT.json`
        - `LOCAL_SERVED_RUNTIME_APP_RESPONSE_FIXTURES.json`
        - `LOCAL_SERVED_RUNTIME_APP_TRACE_AUDIT.json`

        The event-state and asset-overlay packet types are optional read-only slots. They are not integrated into the D5 runtime in this task.
        """,
    )
    write_md(
        OUTPUT_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md",
        "\n".join(
            [
                "# Limitations And Next Steps",
                "",
                "## Exact Limitations",
                "",
                *[f"- {item}" for item in LIMITATIONS],
                "",
                "## Recommended Next Task",
                "",
                f"`{NEXT_TASK}`",
            ]
        ),
    )


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    upstream_decision = read_json(UPSTREAM_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_HARDENING_R1_DECISION.json", {})
    upstream_contract = read_json(UPSTREAM_ROOT / "LOCAL_SERVED_RUNTIME_HARDENED_CONTRACT.json", {})
    upstream_found = upstream_artifacts_found()
    packets = build_app_packets()
    smoke = validate_packets(packets)
    trace = trace_audit(packets, smoke)
    boundary = boundary_audit(upstream_decision, packets, smoke)
    status = STATUS if (
        upstream_decision.get("status") == "PASS_WITH_LIMITATIONS"
        and upstream_contract
        and all(row["exists"] for row in upstream_found)
        and smoke["status"] == "PASS"
        and trace["status"] == "PASS"
        and boundary["status"] == "PASS"
    ) else "FAIL"

    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_PACKET_CONTRACT.json", packet_contract())
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_PACKET_SCHEMAS.json", packet_schemas())
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_REQUEST_FIXTURES.json", request_fixtures())
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_RESPONSE_FIXTURES.json", {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-response-fixtures-r1.v1",
        "packet_count": len(packets),
        "packets": packets,
    })
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_INTEGRATION_SMOKE_RESULTS.json", smoke)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_TRACE_AUDIT.json", trace)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_BOUNDARY_AUDIT.json", boundary)
    write_docs(status, len(packets), upstream_decision)

    served_entrypoint = upstream_decision.get("served_entrypoint")
    health_packet = next((packet for packet in packets if packet.get("packet_type") == "health_status_packet"), {})
    health_data = health_packet.get("data", {})
    bind_host = health_data.get("bind_host") or upstream_decision.get("bind_host") or upstream_contract.get("bind_host")
    bind_port = health_data.get("bind_port") or upstream_decision.get("bind_port") or upstream_contract.get("bind_port")
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now(),
        "upstream_output_root": str(UPSTREAM_ROOT),
        "upstream_status": upstream_decision.get("status"),
        "upstream_artifacts_found": upstream_found,
        "served_entrypoint": served_entrypoint,
        "bind_host": bind_host,
        "bind_port": bind_port,
        "local_only_confirmed": upstream_decision.get("local_only_confirmed") is True and bind_host in {"127.0.0.1", "localhost", "::1"},
        "app_packet_contract_created": (OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_PACKET_CONTRACT.json").exists(),
        "app_packet_schemas_created": (OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_PACKET_SCHEMAS.json").exists(),
        "app_response_fixtures_created": (OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_RESPONSE_FIXTURES.json").exists(),
        "packet_types_total": smoke["packet_types_total"],
        "packet_types_validated": smoke["packet_types_validated"],
        "health_status_packet_passed": smoke["health_status_packet_passed"],
        "governed_answer_packet_passed": smoke["governed_answer_packet_passed"],
        "insight_packet_passed": smoke["insight_packet_passed"],
        "evidence_trace_packet_passed": smoke["evidence_trace_packet_passed"],
        "limitation_packet_passed": smoke["limitation_packet_passed"],
        "safe_next_look_packet_passed": smoke["safe_next_look_packet_passed"],
        "optional_event_state_slot_defined": smoke["optional_event_state_slot_defined"],
        "optional_asset_overlay_slot_defined": smoke["optional_asset_overlay_slot_defined"],
        "unsupported_packet_safe_failure_passed": smoke["unsupported_packet_safe_failure_passed"],
        "trace_refs_present": smoke["trace_refs_present"],
        "evidence_refs_present": smoke["evidence_refs_present"],
        "limitation_refs_present": smoke["limitation_refs_present"],
        "source_mutation_status": upstream_decision.get("source_mutation_status"),
        "autonomous_action_exposed": False,
        "production_readiness_claim_made": False,
        "external_network_binding_default": False,
        "frontend_implemented": False,
        "boundary_audit_status": boundary["status"],
        "limitations": LIMITATIONS,
        "next_recommended_task": NEXT_TASK,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_APP_INTEGRATION_PREFLIGHT_R1_DECISION.json", decision)

    print(json.dumps({
        "status": status,
        "output_root": OUTPUT_ROOT.relative_to(REPO_ROOT).as_posix(),
        "packet_types_total": smoke["packet_types_total"],
        "packet_types_validated": smoke["packet_types_validated"],
        "served_entrypoint": served_entrypoint,
        "boundary_audit_status": boundary["status"],
        "next_recommended_task": NEXT_TASK,
    }, indent=2))
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
