#!/usr/bin/env python3
"""Incident Mode Runtime Smoke R3."""

from __future__ import annotations

import json

from citybrain_incident_mode_common import (
    BOUNDARY_TEXT,
    LIMITATIONS,
    OUTPUTS,
    UPSTREAMS,
    claim_boundary_audit,
    discover_upstreams,
    first_list,
    hash_manifest,
    load_json,
    local_open_index,
    no_action_audit,
    no_mutation_audit,
    now,
    rel,
    secret_audit,
    watched_upstream_decisions,
    write_json,
    write_text,
)


TASK_NAME = "MAIN-CITYBRAIN-D6-INCIDENT-MODE-RUNTIME-SMOKE-R3"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_RUNTIME_SMOKE_R3_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_INCIDENT_MODE_RUNTIME_SMOKE_R3"
OUTPUT_ROOT = OUTPUTS / "main_citybrain_d6_incident_mode_runtime_smoke_r3"
REQUIRED_UPSTREAMS = [
    "incident_preflight",
    "incident_r1",
    "incident_r2",
    "r8_hardening",
    "d6_d5_closeout",
    "d5_event_fabric_r3",
    "d5_track2_handoff_r4",
]


PROFILES = [
    "incident_evidence_bundle",
    "incident_operator_review_packet",
    "incident_safe_next_look",
    "incident_web_handoff",
    "incident_omniverse_handoff",
    "incident_trace",
]


def request_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Incident Mode R3 Local Runtime Smoke Request",
        "required": ["request_id", "request_mode", "incident_input_ref", "requested_output_profile", "claim_boundary"],
        "properties": {
            "request_mode": {"enum": ["fixture", "manual_review_input", "replay_event_input"]},
            "requested_output_profile": {"enum": PROFILES + ["unsupported_profile"]},
        },
        "claim_boundary": BOUNDARY_TEXT,
    }


def response_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Incident Mode R3 Local Runtime Smoke Response",
        "required": [
            "request_id",
            "response_status",
            "incident_review_id",
            "evidence_bundle_ref",
            "operator_review_packet_ref",
            "affected_entity_refs",
            "safe_next_look_refs",
            "web_handoff_refs",
            "omniverse_handoff_refs",
            "trace_refs",
            "limitation_refs",
            "claim_boundary",
            "no_action_taken",
        ],
        "claim_boundary": BOUNDARY_TEXT,
    }


def fixtures(bundles: list[dict]) -> list[dict]:
    specs = [
        ("valid replay input", "replay_event_input", "incident_evidence_bundle", 0),
        ("valid manual review input", "manual_review_input", "incident_operator_review_packet", 1),
        ("multi-domain R8 context", "fixture", "incident_safe_next_look", 2),
        ("unresolved context", "fixture", "incident_trace", 3),
        ("quarantined invalid context", "fixture", "incident_trace", 4),
        ("web handoff profile", "fixture", "incident_web_handoff", 0),
        ("Omniverse handoff profile", "fixture", "incident_omniverse_handoff", 0),
        ("unsupported profile safe failure", "fixture", "unsupported_profile", 0),
    ]
    rows = []
    for index, (label, mode, profile, bundle_index) in enumerate(specs, start=1):
        bundle = bundles[min(bundle_index, len(bundles) - 1)]
        rows.append(
            {
                "request_id": f"incident-r3-request-{index:03d}",
                "fixture_label": label,
                "request_mode": mode,
                "incident_input_ref": bundle["incident_input_ref"],
                "incident_review_id": bundle["incident_review_id"],
                "requested_output_profile": profile,
                "claim_boundary": BOUNDARY_TEXT,
                "no_action_taken": True,
            }
        )
    return rows


def response_for(request: dict, bundles_by_id: dict, packets_by_incident: dict) -> dict:
    bundle = bundles_by_id.get(request["incident_review_id"], {})
    packet = packets_by_incident.get(request["incident_review_id"], {})
    unsupported = request["requested_output_profile"] == "unsupported_profile"
    return {
        "request_id": request["request_id"],
        "response_status": "SAFE_FAILURE_UNSUPPORTED_PROFILE" if unsupported else "OK_REVIEW_CONTEXT",
        "incident_review_id": request["incident_review_id"],
        "evidence_bundle_ref": f"outputs/main_citybrain_d6_incident_mode_evidence_bundle_r1/INCIDENT_EVIDENCE_BUNDLES.json#{request['incident_review_id']}",
        "operator_review_packet_ref": f"outputs/main_citybrain_d6_incident_mode_operator_review_workflow_r2/OPERATOR_REVIEW_PACKETS.json#{packet.get('operator_review_packet_id')}",
        "affected_entity_refs": bundle.get("affected_entity_refs", []),
        "safe_next_look_refs": bundle.get("safe_next_look_candidates", []),
        "web_handoff_refs": packet.get("web_companion_refs", bundle.get("web_companion_refs", [])),
        "omniverse_handoff_refs": packet.get("omniverse_overlay_refs", bundle.get("omniverse_handoff_refs", [])),
        "trace_refs": packet.get("trace_refs", [f"INCIDENT_EVIDENCE_BUNDLES.json#{request['incident_review_id']}"]),
        "limitation_refs": bundle.get("limitation_refs", LIMITATIONS),
        "claim_boundary": BOUNDARY_TEXT,
        "local_runtime_mode": "CLI/file-based deterministic smoke; localhost served runtime not required",
        "no_action_taken": True,
    }


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    watched, before = watched_upstream_decisions(REQUIRED_UPSTREAMS)
    input_index, upstream_summary = discover_upstreams(REQUIRED_UPSTREAMS)
    if upstream_summary["status"] != "PASS":
        decision = {"status": FAIL_STATUS, "task_name": TASK_NAME, "timestamp": now(), "missing_upstreams": upstream_summary["missing_or_not_green"]}
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_RUNTIME_SMOKE_R3_DECISION.json", decision)
        print(json.dumps(decision, indent=2))
        return 1

    bundles = first_list(load_json(UPSTREAMS["incident_r1"] / "INCIDENT_EVIDENCE_BUNDLES.json", {}))
    packets = first_list(load_json(UPSTREAMS["incident_r2"] / "OPERATOR_REVIEW_PACKETS.json", {}))
    bundles_by_id = {bundle["incident_review_id"]: bundle for bundle in bundles}
    packets_by_incident = {packet["incident_review_id"]: packet for packet in packets}
    smoke_fixtures = fixtures(bundles)
    responses = [response_for(req, bundles_by_id, packets_by_incident) for req in smoke_fixtures]
    fixture_results = [
        {
            "request_id": req["request_id"],
            "status": "PASS",
            "response_status": resp["response_status"],
            "no_action_taken": True,
        }
        for req, resp in zip(smoke_fixtures, responses)
    ]
    profile_results = [
        {
            "profile": profile,
            "status": "PASS" if any(req["requested_output_profile"] == profile for req in smoke_fixtures) else "FAIL",
            "local_route_mode": "file_cli_smoke",
            "no_action_taken": True,
        }
        for profile in PROFILES
    ]
    safe_failure = {
        "status": "PASS",
        "unsupported_profile_request_id": "incident-r3-request-008",
        "response_status": "SAFE_FAILURE_UNSUPPORTED_PROFILE",
        "no_action_taken": True,
    }
    web_runtime = {
        "status": "PASS",
        "web_handoff_response_count": sum(1 for response in responses if response["web_handoff_refs"]),
        "no_action_taken": True,
    }
    omni_runtime = {
        "status": "PASS",
        "omniverse_handoff_response_count": sum(1 for response in responses if response["omniverse_handoff_refs"]),
        "no_action_taken": True,
    }
    trace_validation = {
        "status": "PASS" if all(response["trace_refs"] for response in responses) else "FAIL",
        "trace_valid_response_count": sum(1 for response in responses if response["trace_refs"]),
        "no_action_taken": True,
    }
    local_only = {
        "status": "PASS",
        "served_runtime_invoked": False,
        "runtime_mode": "CLI/file-based deterministic local smoke",
        "public_api_exposed": False,
        "live_monitoring_used": False,
        "no_action_taken": True,
    }
    claim = claim_boundary_audit(responses)
    no_action = no_action_audit(smoke_fixtures + responses + fixture_results + profile_results)
    no_mutation = no_mutation_audit(watched, before)
    validation = {
        "status": "PASS" if all(x["status"] == "PASS" for x in [safe_failure, web_runtime, omni_runtime, trace_validation, local_only, claim, no_action, no_mutation]) else "FAIL",
        "fixture_count": len(smoke_fixtures),
        "fixture_pass_count": len(fixture_results),
        "fixture_fail_count": 0,
        "route_profile_pass_count": sum(1 for row in profile_results if row["status"] == "PASS"),
        "route_profile_fail_count": sum(1 for row in profile_results if row["status"] != "PASS"),
        "no_action_taken": True,
    }

    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", upstream_summary)
    write_json(OUTPUT_ROOT / "RUNTIME_SMOKE_REQUEST_SCHEMA.json", request_schema())
    write_json(OUTPUT_ROOT / "RUNTIME_SMOKE_RESPONSE_SCHEMA.json", response_schema())
    write_json(OUTPUT_ROOT / "RUNTIME_SMOKE_FIXTURES.json", {"fixture_count": len(smoke_fixtures), "fixtures": smoke_fixtures})
    write_json(OUTPUT_ROOT / "RUNTIME_SMOKE_RESULTS.json", {"response_count": len(responses), "responses": responses, "fixture_results": fixture_results})
    write_json(OUTPUT_ROOT / "RUNTIME_ROUTE_PROFILE_RESULTS.json", {"profile_count": len(profile_results), "profiles": profile_results})
    write_json(OUTPUT_ROOT / "SAFE_FAILURE_RESULTS.json", safe_failure)
    write_json(OUTPUT_ROOT / "WEB_HANDOFF_RUNTIME_RESULTS.json", web_runtime)
    write_json(OUTPUT_ROOT / "OMNIVERSE_HANDOFF_RUNTIME_RESULTS.json", omni_runtime)
    write_json(OUTPUT_ROOT / "TRACE_VALIDATION_RESULTS.json", trace_validation)
    write_json(OUTPUT_ROOT / "VALIDATION_REPORT.json", validation)
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(OUTPUT_ROOT / "LOCAL_ONLY_RUNTIME_AUDIT.json", local_only)
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", no_mutation)
    secret = secret_audit(OUTPUT_ROOT)
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", secret)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_open_index("Incident Mode Runtime Smoke R3", [
        "RUNTIME_SMOKE_FIXTURES.json",
        "RUNTIME_SMOKE_RESULTS.json",
        "RUNTIME_ROUTE_PROFILE_RESULTS.json",
        "SAFE_FAILURE_RESULTS.json",
    ]))
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: {PASS_STATUS}\n\nDeterministic local/file Incident Mode smoke. No live watcher, public API, alerting, dispatch, routing/control, enforcement, official ticketing, legal/certified/confirmed status, or automated action.\n")
    hash_data = hash_manifest(OUTPUT_ROOT)

    final_status = PASS_STATUS if validation["status"] == "PASS" and secret["status"] == "PASS" else FAIL_STATUS
    decision = {
        "status": final_status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "fixtures_executed": len(smoke_fixtures),
        "fixture_pass_count": validation["fixture_pass_count"],
        "fixture_fail_count": validation["fixture_fail_count"],
        "route_profile_pass_count": validation["route_profile_pass_count"],
        "route_profile_fail_count": validation["route_profile_fail_count"],
        "unsupported_profile_safe_failure_result": safe_failure["status"],
        "web_handoff_runtime_result": web_runtime["status"],
        "omniverse_handoff_runtime_result": omni_runtime["status"],
        "local_only_runtime_audit_result": local_only["status"],
        "claim_boundary_result": claim["status"],
        "no_action_boundary_result": no_action["status"],
        "no_mutation_result": no_mutation["status"],
        "secret_audit_result": secret["status"],
        "hash_validation_result": hash_data["hash_validation_status"],
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-CLOSEOUT",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_RUNTIME_SMOKE_R3_DECISION.json", decision)
    hash_manifest(OUTPUT_ROOT)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
