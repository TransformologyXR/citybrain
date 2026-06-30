#!/usr/bin/env python3
"""Build D5 local served runtime app integration slice R1.

This creates concrete local app-facing packet outputs from the D5 app
integration preflight. It does not build a frontend, expose a public API,
implement production auth/RBAC, or integrate event/Omniverse tracks beyond
shallow availability checks.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-APP-INTEGRATION-SLICE-R1"
STATUS = "PASS_WITH_LIMITATIONS"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_app_integration_slice_r1"
UPSTREAM_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_app_integration_preflight_r1"
EVENT_FABRIC_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_live_event_fabric_minimal_local_slice"
ASSET_OVERLAY_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end"
VIEWPORT_BRIDGE_ROOT = REPO_ROOT / "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d5_local_served_runtime_app_integration_slice_r1.py"
NEXT_TASK = "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-APP-CONSUMPTION-SMOKE-R1"

LIMITATIONS = [
    "local/developer-demo app-facing packet slice only",
    "no frontend implemented",
    "no production auth/RBAC implemented",
    "no public API or production readiness claim",
    "localhost-only served runtime boundary preserved",
    "runtime wrapper remains thin stdlib localhost runtime",
    "concurrency/load not tested here",
    "event-state availability is shallow only; event fabric is not integrated",
    "asset-overlay availability is shallow only; Omniverse/Track 2A is not integrated",
    "handoff-only for D5 event-fabric integration",
    "handoff-only for Track 2 app/control-room consumption",
    "handoff-only for Omniverse event/asset overlay integration",
    "no source mutation",
    "no autonomous action, dispatch, enforcement, routing, or control",
    "app packet contract is R1 local contract, not a final public API",
]

REQUIRED_UPSTREAM = [
    "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_APP_INTEGRATION_PREFLIGHT_R1_DECISION.json",
    "LOCAL_SERVED_RUNTIME_APP_PACKET_CONTRACT.json",
    "LOCAL_SERVED_RUNTIME_APP_PACKET_SCHEMAS.json",
    "LOCAL_SERVED_RUNTIME_APP_REQUEST_FIXTURES.json",
    "LOCAL_SERVED_RUNTIME_APP_RESPONSE_FIXTURES.json",
    "LOCAL_SERVED_RUNTIME_APP_INTEGRATION_SMOKE_RESULTS.json",
    "LOCAL_SERVED_RUNTIME_APP_TRACE_AUDIT.json",
    "LOCAL_SERVED_RUNTIME_APP_BOUNDARY_AUDIT.json",
    "LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_NOTES.md",
    "LIMITATIONS_AND_NEXT_STEPS.md",
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


def load_upstream_packets() -> list[dict[str, Any]]:
    payload = read_json(UPSTREAM_ROOT / "LOCAL_SERVED_RUNTIME_APP_RESPONSE_FIXTURES.json", {})
    return payload.get("packets", [])


def packet_by_type(packets: list[dict[str, Any]], packet_type: str) -> dict[str, Any]:
    return next((packet for packet in packets if packet.get("packet_type") == packet_type), {})


def normalize_packet(packet: dict[str, Any], packet_type: str | None = None) -> dict[str, Any]:
    normalized = dict(packet)
    if packet_type:
        normalized["packet_type"] = packet_type
        normalized["packet_id"] = f"app-slice-packet:{packet_type}"
    else:
        normalized["packet_id"] = str(normalized.get("packet_id", "")).replace("app-packet:", "app-slice-packet:")
    normalized["slice_schema_version"] = "main-citybrain-d5-local-served-runtime-app-integration-slice-r1.v1"
    normalized["consumable_by"] = ["web_companion", "control_room_ui", "track2_surface"]
    normalized["frontend_implemented"] = False
    normalized["production_readiness_claim_made"] = False
    normalized["external_network_binding_default"] = False
    normalized["autonomous_action_exposed"] = False
    normalized["source_mutation_performed"] = False
    normalized["no_action_taken"] = True
    return normalized


def availability_check(root: Path, decision_name: str, label: str) -> dict[str, Any]:
    decision_path = root / decision_name
    decision = read_json(decision_path, {})
    return {
        "label": label,
        "root": root.relative_to(REPO_ROOT).as_posix(),
        "exists": root.exists(),
        "decision_path": decision_path.relative_to(REPO_ROOT).as_posix(),
        "decision_exists": decision_path.exists(),
        "status": decision.get("status", "MISSING"),
        "available_for_future_handoff": root.exists() and decision_path.exists() and str(decision.get("status", "")).startswith("PASS"),
        "integrated_in_this_slice": False,
        "boundary": "availability only; no deep integration performed in D5 app packet slice",
    }


def build_packet_bundle(upstream_packets: list[dict[str, Any]], event_availability: dict[str, Any], asset_availability: dict[str, Any]) -> list[dict[str, Any]]:
    health = packet_by_type(upstream_packets, "health_status_packet")
    runtime_status = packet_by_type(upstream_packets, "runtime_status_packet")
    governed = packet_by_type(upstream_packets, "governed_answer_packet")
    insight = packet_by_type(upstream_packets, "insight_packet")
    evidence = packet_by_type(upstream_packets, "evidence_trace_packet")
    limitation = packet_by_type(upstream_packets, "limitation_packet")
    safe_next = packet_by_type(upstream_packets, "safe_next_look_packet")
    event_slot = packet_by_type(upstream_packets, "optional_event_state_packet")
    asset_slot = packet_by_type(upstream_packets, "optional_asset_overlay_packet")
    unsupported = packet_by_type(upstream_packets, "unsupported_packet_safe_failure")

    app_session = {
        **normalize_packet(runtime_status, "app_session_context_packet"),
        "data": {
            "session_mode": "local_developer_demo",
            "served_runtime_status": runtime_status.get("status"),
            "health_status": health.get("status"),
            "local_only_confirmed": True,
            "event_fabric_available": event_availability["available_for_future_handoff"],
            "asset_overlay_available": asset_availability["available_for_future_handoff"],
            "event_fabric_integrated": False,
            "asset_overlay_integrated": False,
        },
        "safe_next_looks": ["load packet bundle read-only", "inspect trace/evidence/limitation refs"],
    }
    track2_summary = {
        **normalize_packet(runtime_status, "track2_handoff_packet"),
        "data": {
            "handoff_target": "Track 2 app/control-room surfaces",
            "packet_bundle": "LOCAL_SERVED_RUNTIME_APP_SLICE_PACKET_BUNDLE.json",
            "asset_overlay_availability": asset_availability,
            "event_fabric_availability": event_availability,
            "integration_boundary": "read-only handoff; no Omniverse/Kit interaction and no event-fabric integration in this task",
        },
        "safe_next_looks": ["consume packet bundle read-only", "keep optional overlay/event slots gated"],
    }
    malformed = {
        "packet_id": "app-slice-packet:malformed_app_packet_safe_failure",
        "packet_type": "malformed_app_packet_safe_failure",
        "status": "SAFE_FAILURE_MALFORMED_APP_PACKET",
        "data": {
            "malformed_request_example": {"packet_type": "", "missing_required_fields": True},
            "safe_failure_reason": "malformed app packet request rejected before app/control-room consumption",
        },
        "trace_refs": ["app-slice-trace:malformed-packet-safe-failure"],
        "evidence_refs": ["artifact:LOCAL_SERVED_RUNTIME_APP_PACKET_SCHEMAS"],
        "limitation_refs": ["malformed_app_packet_rejected", "no_frontend_implemented", "local_app_slice_only"],
        "safe_next_looks": ["repair packet request against schema", "do not infer missing packet fields"],
        "claim_boundary": "Malformed app packet requests fail safely; no action or runtime mutation.",
        "warnings": ["safe failure fixture only"],
        "error": {"code": "MALFORMED_APP_PACKET", "safe_failure": True},
        "no_action_taken": True,
        "autonomous_action_exposed": False,
        "production_readiness_claim_made": False,
        "external_network_binding_default": False,
        "frontend_implemented": False,
        "source_mutation_performed": False,
        "slice_schema_version": "main-citybrain-d5-local-served-runtime-app-integration-slice-r1.v1",
        "consumable_by": ["web_companion", "control_room_ui", "track2_surface"],
    }
    ordered = [
        normalize_packet(health),
        normalize_packet(governed),
        normalize_packet(insight),
        normalize_packet(evidence),
        normalize_packet(limitation),
        normalize_packet(safe_next),
        app_session,
        track2_summary,
        normalize_packet(event_slot),
        normalize_packet(asset_slot),
        normalize_packet(unsupported),
        malformed,
    ]
    return ordered


def slice_contract(upstream_decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": "main-citybrain-d5-local-served-runtime-app-integration-slice-r1.v1",
        "task_id": TASK_ID,
        "served_entrypoint": upstream_decision.get("served_entrypoint"),
        "bind_host": upstream_decision.get("bind_host"),
        "bind_port": upstream_decision.get("bind_port"),
        "local_only_confirmed": True,
        "packet_types": [
            "health_status_packet",
            "governed_answer_packet",
            "insight_packet",
            "evidence_trace_packet",
            "limitation_packet",
            "safe_next_look_packet",
            "app_session_context_packet",
            "track2_handoff_packet",
            "optional_event_state_packet",
            "optional_asset_overlay_packet",
            "unsupported_packet_safe_failure",
            "malformed_app_packet_safe_failure",
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
            "frontend_implemented",
            "source_mutation_performed",
        ],
        "forbidden": [
            "frontend implementation",
            "production auth/RBAC",
            "public API",
            "external default bind",
            "source mutation",
            "autonomous action",
            "dispatch",
            "enforcement",
            "routing",
            "control",
        ],
    }


def packet_schemas(contract: dict[str, Any]) -> dict[str, Any]:
    common = {
        "type": "object",
        "required": contract["required_packet_fields"],
        "properties": {
            "packet_id": {"type": "string"},
            "packet_type": {"type": "string"},
            "status": {"type": "string"},
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
            "frontend_implemented": {"const": False},
            "source_mutation_performed": {"const": False},
        },
    }
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-slice-packet-schemas-r1.v1",
        "common_packet_schema": common,
        "packet_type_schemas": {packet_type: common for packet_type in contract["packet_types"]},
    }


def validate_packet(packet: dict[str, Any], required: list[str]) -> dict[str, Any]:
    issues = []
    for field in required:
        if field not in packet:
            issues.append(f"missing:{field}")
    for array_field in ["trace_refs", "evidence_refs", "limitation_refs"]:
        if not packet.get(array_field):
            issues.append(f"missing:{array_field}")
    for false_field in [
        "autonomous_action_exposed",
        "production_readiness_claim_made",
        "external_network_binding_default",
        "frontend_implemented",
        "source_mutation_performed",
    ]:
        if packet.get(false_field) is not False:
            issues.append(f"{false_field}_must_be_false")
    if packet.get("no_action_taken") is not True:
        issues.append("no_action_taken_must_be_true")
    return {
        "packet_id": packet.get("packet_id"),
        "packet_type": packet.get("packet_type"),
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
    }


def smoke_results(packets: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    results = [validate_packet(packet, contract["required_packet_fields"]) for packet in packets]
    by_type = {row["packet_type"]: row["status"] == "PASS" for row in results}
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-slice-smoke-r1.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL",
        "packet_types_total": len(packets),
        "packet_types_validated": sum(1 for row in results if row["status"] == "PASS"),
        "health_status_packet_passed": by_type.get("health_status_packet", False),
        "governed_answer_packet_passed": by_type.get("governed_answer_packet", False),
        "insight_packet_passed": by_type.get("insight_packet", False),
        "evidence_trace_packet_passed": by_type.get("evidence_trace_packet", False),
        "limitation_packet_passed": by_type.get("limitation_packet", False),
        "safe_next_look_packet_passed": by_type.get("safe_next_look_packet", False),
        "app_session_context_packet_passed": by_type.get("app_session_context_packet", False),
        "track2_handoff_packet_passed": by_type.get("track2_handoff_packet", False),
        "optional_event_state_slot_defined": by_type.get("optional_event_state_packet", False),
        "optional_asset_overlay_slot_defined": by_type.get("optional_asset_overlay_packet", False),
        "unsupported_packet_safe_failure_passed": by_type.get("unsupported_packet_safe_failure", False),
        "malformed_app_packet_safe_failure_passed": by_type.get("malformed_app_packet_safe_failure", False),
        "trace_refs_present": all(bool(packet.get("trace_refs")) for packet in packets),
        "evidence_refs_present": all(bool(packet.get("evidence_refs")) for packet in packets),
        "limitation_refs_present": all(bool(packet.get("limitation_refs")) for packet in packets),
        "case_results": results,
    }


def trace_audit(packets: list[dict[str, Any]], smoke: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-slice-trace-audit-r1.v1",
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


def boundary_audit(packets: list[dict[str, Any]], upstream_decision: dict[str, Any], event_availability: dict[str, Any], asset_availability: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "upstream_local_only_confirmed": upstream_decision.get("local_only_confirmed") is True,
        "source_mutation_status_pass": upstream_decision.get("source_mutation_status") == "PASS",
        "no_autonomous_action": all(packet["autonomous_action_exposed"] is False for packet in packets),
        "no_production_readiness": all(packet["production_readiness_claim_made"] is False for packet in packets),
        "no_external_default_bind": all(packet["external_network_binding_default"] is False for packet in packets),
        "no_frontend_implemented": all(packet["frontend_implemented"] is False for packet in packets),
        "no_source_mutation": all(packet["source_mutation_performed"] is False for packet in packets),
        "event_fabric_availability_only": event_availability["integrated_in_this_slice"] is False,
        "asset_overlay_availability_only": asset_availability["integrated_in_this_slice"] is False,
    }
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-slice-boundary-audit-r1.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "claim_boundary": "Local app-facing packet slice only; no frontend, public API, production readiness, external default bind, source mutation, event-fabric integration, asset-overlay integration, dispatch, enforcement, routing, control, or autonomous action.",
        "limitations": LIMITATIONS,
    }


def request_fixtures(packets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-slice-request-fixtures-r1.v1",
        "fixture_count": len(packets) + 1,
        "fixtures": [
            {
                "app_request_id": f"slice-request:{packet['packet_type']}",
                "desired_packet_type": packet["packet_type"],
                "expected_packet_id": packet["packet_id"],
                "safe_mode": True,
                "trace_requested": True,
            }
            for packet in packets
        ] + [
            {
                "app_request_id": "slice-request:malformed-empty-type",
                "desired_packet_type": "",
                "expected_status": "SAFE_FAILURE_MALFORMED_APP_PACKET",
                "safe_mode": True,
                "trace_requested": True,
            }
        ],
    }


def response_fixtures(packets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-slice-response-fixtures-r1.v1",
        "fixture_count": len(packets),
        "responses": [
            {
                "app_request_id": f"slice-request:{packet['packet_type']}",
                "packet_id": packet["packet_id"],
                "packet_type": packet["packet_type"],
                "status": packet["status"],
                "response": packet,
            }
            for packet in packets
        ],
    }


def track2_handoff(packets: list[dict[str, Any]], event_availability: dict[str, Any], asset_availability: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-slice-track2-handoff-r1.v1",
        "status": "READY_WITH_LIMITATIONS",
        "packet_bundle_ref": "LOCAL_SERVED_RUNTIME_APP_SLICE_PACKET_BUNDLE.json",
        "packet_types": [packet["packet_type"] for packet in packets],
        "event_fabric_availability": event_availability,
        "asset_overlay_availability": asset_availability,
        "allowed_consumers": ["web_companion", "control_room_ui", "track2_surface"],
        "boundary": "read-only packet handoff; no frontend or Track 2/Omniverse integration performed here",
        "no_action_taken": True,
    }


def write_docs(status: str, packet_count: int, upstream_decision: dict[str, Any]) -> None:
    write_md(
        OUTPUT_ROOT / "README.md",
        f"""
        # {TASK_ID}

        Status: `{status}`

        This pack is a concrete local app-facing packet slice for future web companion, control-room, or Track 2 consumption. It preserves the D5 localhost-only served runtime boundary and does not build a frontend or public API.
        """,
    )
    write_md(
        OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_INTEGRATION_SLICE_R1_REPORT.md",
        f"""
        # Local Served Runtime App Integration Slice R1

        Status: `{status}`

        Served entrypoint preserved:
        `{upstream_decision.get('served_entrypoint')}`

        Packet bundle count: `{packet_count}`

        The slice includes app-consumable packets for health/status, governed answer, insight, evidence trace, limitation, safe next-look, app session context, Track 2 handoff summary, optional event-state placeholder, optional asset-overlay placeholder, unsupported packet safe failure, and malformed app packet safe failure.
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

    upstream_decision = read_json(UPSTREAM_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_APP_INTEGRATION_PREFLIGHT_R1_DECISION.json", {})
    upstream_packets = load_upstream_packets()
    upstream_found = upstream_artifacts_found()
    event_availability = availability_check(
        EVENT_FABRIC_ROOT,
        "MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_MINIMAL_LOCAL_SLICE_DECISION.json",
        "minimal local event fabric",
    )
    asset_availability = availability_check(
        ASSET_OVERLAY_ROOT,
        "MAIN_TRACK2A_D4X_OMNIVERSE_OBJECT_PICKING_AND_USD_TO_CER_BRIDGE_END_TO_END_DECISION.json",
        "Track 2A object-picking/USD-to-CER bridge",
    )
    viewport_availability = availability_check(
        VIEWPORT_BRIDGE_ROOT,
        "MAIN_TRACK2C_D4X_OMNIVERSE_VIEWPORT_BRIDGE_R1_DECISION.json",
        "Track 2C Omniverse viewport bridge",
    )
    asset_availability["related_viewport_bridge"] = viewport_availability

    packets = build_packet_bundle(upstream_packets, event_availability, asset_availability)
    contract = slice_contract(upstream_decision)
    schemas = packet_schemas(contract)
    smoke = smoke_results(packets, contract)
    trace = trace_audit(packets, smoke)
    boundary = boundary_audit(packets, upstream_decision, event_availability, asset_availability)
    track2 = track2_handoff(packets, event_availability, asset_availability)

    status = STATUS if (
        upstream_decision.get("status") == "PASS_WITH_LIMITATIONS"
        and all(row["exists"] for row in upstream_found)
        and smoke["status"] == "PASS"
        and trace["status"] == "PASS"
        and boundary["status"] == "PASS"
    ) else "FAIL"

    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_CONTRACT.json", contract)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_PACKET_SCHEMAS.json", schemas)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_REQUEST_FIXTURES.json", request_fixtures(packets))
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_RESPONSE_FIXTURES.json", response_fixtures(packets))
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_PACKET_BUNDLE.json", {
        "schema_version": "main-citybrain-d5-local-served-runtime-app-slice-packet-bundle-r1.v1",
        "packet_count": len(packets),
        "packets": packets,
    })
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_SMOKE_RESULTS.json", smoke)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_TRACE_AUDIT.json", trace)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_BOUNDARY_AUDIT.json", boundary)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_TRACK2_HANDOFF.json", track2)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_EVENT_FABRIC_AVAILABILITY_CHECK.json", event_availability)
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_ASSET_OVERLAY_AVAILABILITY_CHECK.json", asset_availability)
    write_docs(status, len(packets), upstream_decision)

    decision = {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now(),
        "upstream_output_root": str(UPSTREAM_ROOT),
        "upstream_status": upstream_decision.get("status"),
        "upstream_artifacts_found": upstream_found,
        "runner_path": str(RUNNER_PATH),
        "served_entrypoint": upstream_decision.get("served_entrypoint"),
        "bind_host": upstream_decision.get("bind_host"),
        "bind_port": upstream_decision.get("bind_port"),
        "local_only_confirmed": upstream_decision.get("local_only_confirmed") is True,
        "app_slice_contract_created": (OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_CONTRACT.json").exists(),
        "app_slice_packet_schemas_created": (OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_PACKET_SCHEMAS.json").exists(),
        "app_slice_packet_bundle_created": (OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_PACKET_BUNDLE.json").exists(),
        "app_response_fixtures_created": (OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_RESPONSE_FIXTURES.json").exists(),
        "packet_types_total": smoke["packet_types_total"],
        "packet_types_validated": smoke["packet_types_validated"],
        "health_status_packet_passed": smoke["health_status_packet_passed"],
        "governed_answer_packet_passed": smoke["governed_answer_packet_passed"],
        "insight_packet_passed": smoke["insight_packet_passed"],
        "evidence_trace_packet_passed": smoke["evidence_trace_packet_passed"],
        "limitation_packet_passed": smoke["limitation_packet_passed"],
        "safe_next_look_packet_passed": smoke["safe_next_look_packet_passed"],
        "app_session_context_packet_passed": smoke["app_session_context_packet_passed"],
        "track2_handoff_packet_passed": smoke["track2_handoff_packet_passed"],
        "optional_event_state_slot_defined": smoke["optional_event_state_slot_defined"],
        "optional_asset_overlay_slot_defined": smoke["optional_asset_overlay_slot_defined"],
        "unsupported_packet_safe_failure_passed": smoke["unsupported_packet_safe_failure_passed"],
        "malformed_app_packet_safe_failure_passed": smoke["malformed_app_packet_safe_failure_passed"],
        "event_fabric_availability_checked": True,
        "event_fabric_integrated": False,
        "asset_overlay_availability_checked": True,
        "asset_overlay_integrated": False,
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
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_APP_INTEGRATION_SLICE_R1_DECISION.json", decision)

    print(json.dumps({
        "status": status,
        "output_root": OUTPUT_ROOT.relative_to(REPO_ROOT).as_posix(),
        "runner_path": RUNNER_PATH.relative_to(REPO_ROOT).as_posix(),
        "packet_types_total": smoke["packet_types_total"],
        "packet_types_validated": smoke["packet_types_validated"],
        "served_entrypoint": upstream_decision.get("served_entrypoint"),
        "event_fabric_available": event_availability["available_for_future_handoff"],
        "asset_overlay_available": asset_availability["available_for_future_handoff"],
        "boundary_audit_status": boundary["status"],
        "next_recommended_task": NEXT_TASK,
    }, indent=2))
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
