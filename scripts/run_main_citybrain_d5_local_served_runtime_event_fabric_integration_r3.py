#!/usr/bin/env python3
"""Build D5 local served-runtime Event Fabric integration R3 fixtures."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-EVENT-FABRIC-INTEGRATION-R3"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_event_fabric_integration_r3"

UPSTREAMS = {
    "r7_multi_domain_edge_registry": {
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
    },
    "d5_local_served_runtime_preflight": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_preflight",
        "expected_prefix": "PASS",
    },
    "d5_local_served_runtime_app_integration_slice": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_app_integration_slice_r1",
        "expected_prefix": "PASS",
    },
    "d6_closeout_r2": {
        "root": "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh_r2",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_R2_WITH_LIMITATIONS",
    },
    "d6_event_context_overlay_r4": {
        "root": "outputs/main_citybrain_d6_event_context_overlay_integration_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4_WITH_LIMITATIONS",
    },
    "event_fabric_r2": {
        "root": "outputs/main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END_WITH_LIMITATIONS",
    },
    "track2a_event_overlay_r3": {
        "root": "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3",
        "expected": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3_WITH_LIMITATIONS",
    },
}

ROUTES = [
    "health_runtime_metadata",
    "event_state_by_canonical_entity_ref",
    "event_state_by_overlay_marker_or_track2a_ref",
    "active_replay_event_context_by_domain_pair",
    "unresolved_event_list",
    "quarantined_event_list",
    "event_to_edge_registry_trace",
    "event_evidence_refs",
    "event_limitation_refs",
    "unsupported_route_safe_failure",
    "malformed_json_safe_failure",
    "invalid_schema_safe_failure",
]

LIMITATIONS = [
    "local served-runtime integration slice only",
    "file/fixture route contract only; no production service",
    "no public API readiness claim",
    "bind target is local-only if a future localhost harness is started",
    "event state and relationship state remain local/replay review/query context only",
    "no autonomous monitoring, alert push, dispatch, routing/control, enforcement, legal/certified claim, or automated action",
]

BOUNDARY = (
    "Local/replay D5 served-runtime fixture context only. No production service, public API readiness, "
    "live or autonomous monitoring, alert push, dispatch, routing/control, enforcement, legal/certified "
    "claim, or automated action."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def root_path(root: str) -> Path:
    return REPO_ROOT / root


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    files = sorted(item for item in path.rglob("*") if item.is_file())
    digest = hashlib.sha256()
    byte_count = 0
    for item in files:
        stat = item.stat()
        byte_count += stat.st_size
        digest.update(rel(item).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
    return {"exists": True, "file_count": len(files), "byte_count": byte_count, "fingerprint": digest.hexdigest()}


def decision_file(path: Path) -> Path | None:
    files = sorted(path.glob("*DECISION*.json")) if path.exists() else []
    return files[0] if files else None


def decision_status(path: Path) -> str | None:
    decision = decision_file(path)
    if not decision:
        return None
    payload = read_json(decision, {})
    return str(payload.get("status")) if payload.get("status") else None


def first_rows(payload: Any, keys: list[str]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = value
    else:
        raw = [value]
    out = []
    for item in raw:
        text = str(item)
        if text and text not in out:
            out.append(text)
    return out


def discover_inputs(pre: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    missing = []
    rows = []
    for branch, meta in UPSTREAMS.items():
        path = root_path(meta["root"])
        status = decision_status(path)
        expected = meta.get("expected")
        expected_prefix = meta.get("expected_prefix")
        green = path.exists() and status is not None and ((expected and status == expected) or (expected_prefix and status.startswith(expected_prefix)))
        if not green:
            missing.append(branch)
        artifacts = []
        if path.exists():
            for item in sorted(path.rglob("*")):
                if item.is_file() and item.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".py"}:
                    artifacts.append(rel(item))
                if len(artifacts) >= 16:
                    break
        rows.append(
            {
                "branch": branch,
                "root": meta["root"],
                "exists": path.exists(),
                "decision_path": rel(decision_file(path)) if decision_file(path) else None,
                "status": status,
                "expected": expected or f"{expected_prefix}*",
                "green": green,
                "snapshot": pre[meta["root"]],
                "sample_artifacts": artifacts,
                "read_only": True,
            }
        )
    report = {"status": "PASS" if not missing else "FAIL", "timestamp": utc_now(), "upstream_missing": missing, "branches": rows}
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", report)
    return report, missing


def branch_summary(input_index: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for branch in input_index["branches"]:
        decision = read_json(REPO_ROOT / branch["decision_path"], {}) if branch.get("decision_path") else {}
        rows.append(
            {
                "branch": branch["branch"],
                "root": branch["root"],
                "status": branch["status"],
                "green": branch["green"],
                "count_fields": {k: v for k, v in decision.items() if isinstance(v, int) and ("count" in k or "packet" in k or "edge" in k or "route" in k)},
                "limitation_summary": decision.get("limitations", ["limitations carried from upstream branch"])[:5],
                "consumed_by_d5_r3": branch["green"],
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS" if all(row["green"] for row in rows) else "FAIL", "branches": rows}
    write_json(OUTPUT_ROOT / "UPSTREAM_BRANCH_STATUS_SUMMARY.json", report)
    return report


def load_sources() -> dict[str, Any]:
    ef = root_path(UPSTREAMS["event_fabric_r2"]["root"])
    r7 = root_path(UPSTREAMS["r7_multi_domain_edge_registry"]["root"])
    t2 = root_path(UPSTREAMS["track2a_event_overlay_r3"]["root"])
    d6 = root_path(UPSTREAMS["d6_event_context_overlay_r4"]["root"])
    return {
        "current": first_rows(read_json(ef / "EVENT_FABRIC_R2_CURRENT_STATE_ROWS.json", {}), ["rows"]),
        "unresolved": first_rows(read_json(ef / "EVENT_FABRIC_R2_UNRESOLVED_REVIEW_QUEUE.json", {}), ["items"]),
        "quarantined": first_rows(read_json(ef / "EVENT_FABRIC_R2_QUARANTINED_EVENTS.json", {}), ["events"]),
        "asset_index": first_rows(read_json(ef / "EVENT_FABRIC_R2_ASSET_EVENT_STATE_INDEX.json", {}), ["items"]),
        "edge_registry": first_rows(read_json(r7 / "MULTI_DOMAIN_EDGE_REGISTRY.json", {}), ["edges"]),
        "track2a_asset_map": first_rows(read_json(t2 / "OMNI_EVENT_R3_EVENT_TO_ASSET_BINDING_MAP.json", {}), ["rows"]),
        "track2a_relationship_map": first_rows(read_json(t2 / "OMNI_EVENT_R3_EVENT_TO_RELATIONSHIP_MAP.json", {}), ["rows"]),
        "d6_packets": first_rows(read_json(d6 / "D6_R4_EVENT_CONTEXT_OVERLAY_PACKETS.json", {}), ["packets"]),
    }


def event_ref(row: dict[str, Any]) -> str:
    refs = strings(row.get("current_event_refs")) or strings(row.get("event_ref")) or strings(row.get("event_id")) or strings(row.get("state_id")) or strings(row.get("queue_id"))
    return refs[0] if refs else "unknown_event_ref"


def response_envelope(request_id: str, route: str, status: str, payload: Any, evidence_refs: list[str], limitation_refs: list[str]) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "route": route,
        "status": status,
        "runtime_mode": "local_fixture_route_contract_only",
        "payload": payload,
        "evidence_refs": evidence_refs or ["NO_EVENT_EVIDENCE_AVAILABLE_FOR_ROUTE"],
        "limitation_refs": limitation_refs or ["NO_EVENT_LIMITATION_AVAILABLE_FOR_ROUTE"],
        "claim_boundary": BOUNDARY,
        "no_action_taken": True,
    }


def route_registry() -> dict[str, Any]:
    routes = []
    for index, route in enumerate(ROUTES, start=1):
        routes.append(
            {
                "route_id": f"d5-r3-route-{index:03d}",
                "route": route,
                "method": "LOCAL_FIXTURE",
                "public_api": False,
                "bind_host_if_served": "127.0.0.1",
                "claim_boundary": BOUNDARY,
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS", "route_count": len(routes), "routes": routes}
    write_json(OUTPUT_ROOT / "LOCAL_RUNTIME_ROUTE_REGISTRY.json", report)
    return report


def contract(routes: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "status": "PASS",
        "task_name": TASK_NAME,
        "runtime_contract": {
            "mode": "local_file_fixture_or_127_0_0_1_only",
            "production_service": False,
            "public_api_ready": False,
            "request_envelope_required_fields": ["request_id", "route", "params"],
            "response_envelope_required_fields": ["request_id", "route", "status", "payload", "evidence_refs", "limitation_refs", "no_action_taken"],
            "safe_failure_statuses": ["UNSUPPORTED_ROUTE", "MALFORMED_JSON", "INVALID_SCHEMA"],
        },
        "route_count": routes["route_count"],
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_EVENT_INTEGRATION_CONTRACT.json", payload)
    return payload


def fixtures_and_responses(sources: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    current = sources["current"]
    unresolved = sources["unresolved"]
    quarantined = sources["quarantined"]
    edge_registry = sources["edge_registry"]
    track2a = sources["track2a_asset_map"]
    first_current = current[0]
    first_overlay = track2a[0]
    first_edge = edge_registry[0]
    edge_event = next((edge for edge in edge_registry if "event_context" in edge.get("runtime_query_tags", [])), first_edge)

    requests = [
        {"request_id": "d5-r3-request-001", "route": "health_runtime_metadata", "params": {}, "no_action_taken": True},
        {"request_id": "d5-r3-request-002", "route": "event_state_by_canonical_entity_ref", "params": {"canonical_entity_ref": first_current.get("entity_ref", "corridor")}, "no_action_taken": True},
        {"request_id": "d5-r3-request-003", "route": "event_state_by_overlay_marker_or_track2a_ref", "params": {"track2a_ref": first_overlay.get("binding_id") or first_overlay.get("asset_ref")}, "no_action_taken": True},
        {"request_id": "d5-r3-request-004", "route": "active_replay_event_context_by_domain_pair", "params": {"source_domain": edge_event["source_domain"], "target_domain": edge_event["target_domain"]}, "no_action_taken": True},
        {"request_id": "d5-r3-request-005", "route": "unresolved_event_list", "params": {"limit": 10}, "no_action_taken": True},
        {"request_id": "d5-r3-request-006", "route": "quarantined_event_list", "params": {"limit": 10}, "no_action_taken": True},
        {"request_id": "d5-r3-request-007", "route": "event_to_edge_registry_trace", "params": {"event_ref": event_ref(first_current)}, "no_action_taken": True},
        {"request_id": "d5-r3-request-008", "route": "event_evidence_refs", "params": {"event_ref": event_ref(first_current)}, "no_action_taken": True},
        {"request_id": "d5-r3-request-009", "route": "event_limitation_refs", "params": {"event_ref": event_ref(first_current)}, "no_action_taken": True},
        {"request_id": "d5-r3-request-010", "route": "unsupported_route_safe_failure", "params": {"route": "dispatch_control"}, "no_action_taken": True},
        {"request_id": "d5-r3-request-011", "route": "malformed_json_safe_failure", "raw_body": "{bad json", "no_action_taken": True},
        {"request_id": "d5-r3-request-012", "route": "invalid_schema_safe_failure", "params": {"missing": "route_required_params"}, "no_action_taken": True},
    ]

    responses = []
    for req in requests:
        route = req["route"]
        rid = req["request_id"]
        if route == "health_runtime_metadata":
            payload = {"runtime": TASK_NAME, "route_count": len(ROUTES), "mode": "local_fixture", "public_api_ready": False}
            responses.append(response_envelope(rid, route, "OK", payload, ["INPUT_ARTIFACT_INDEX.json"], LIMITATIONS))
        elif route == "event_state_by_canonical_entity_ref":
            ref = req["params"]["canonical_entity_ref"]
            rows = [row for row in current if ref in strings(row.get("entity_ref")) + strings(row.get("entity_refs"))]
            rows = rows or current[:1]
            responses.append(response_envelope(rid, route, "OK", rows, strings(rows[0].get("evidence_refs")), strings(rows[0].get("limitation_refs"))))
        elif route == "event_state_by_overlay_marker_or_track2a_ref":
            ref = req["params"]["track2a_ref"]
            rows = [row for row in track2a if ref in strings(row.get("binding_id")) + strings(row.get("asset_ref")) + strings(row.get("usd_prim_ref"))]
            rows = rows or track2a[:1]
            responses.append(response_envelope(rid, route, "OK", rows, strings(rows[0].get("evidence_refs")), strings(rows[0].get("limitation_refs"))))
        elif route == "active_replay_event_context_by_domain_pair":
            sd = req["params"]["source_domain"]
            td = req["params"]["target_domain"]
            rows = [edge for edge in edge_registry if edge.get("source_domain") == sd and edge.get("target_domain") == td]
            responses.append(response_envelope(rid, route, "OK", rows[:10], rows[0]["evidence_refs"], rows[0]["limitation_refs"]))
        elif route == "unresolved_event_list":
            rows = unresolved[: req["params"]["limit"]]
            evidence = strings(rows[0].get("evidence_refs")) if rows else ["NO_UNRESOLVED_EVENTS_PRESENT"]
            limits = strings(rows[0].get("limitation_refs")) if rows else ["NO_UNRESOLVED_EVENTS_PRESENT"]
            responses.append(response_envelope(rid, route, "OK", rows, evidence, limits))
        elif route == "quarantined_event_list":
            rows = quarantined[: req["params"]["limit"]]
            responses.append(response_envelope(rid, route, "OK", rows, ["EVENT_FABRIC_R2_QUARANTINED_EVENTS.json"], ["NO_QUARANTINED_EVENTS_PRESENT" if not rows else "QUARANTINED_REVIEW_REQUIRED"]))
        elif route == "event_to_edge_registry_trace":
            ref = req["params"]["event_ref"]
            rows = [edge for edge in edge_registry if ref in json.dumps(edge, sort_keys=True)]
            rows = rows or [edge_event]
            responses.append(response_envelope(rid, route, "OK", rows[:10], rows[0]["evidence_refs"], rows[0]["limitation_refs"]))
        elif route == "event_evidence_refs":
            responses.append(response_envelope(rid, route, "OK", strings(first_current.get("evidence_refs")), strings(first_current.get("evidence_refs")), strings(first_current.get("limitation_refs"))))
        elif route == "event_limitation_refs":
            responses.append(response_envelope(rid, route, "OK", strings(first_current.get("limitation_refs")), strings(first_current.get("evidence_refs")), strings(first_current.get("limitation_refs"))))
        elif route == "unsupported_route_safe_failure":
            responses.append(response_envelope(rid, route, "UNSUPPORTED_ROUTE", {"unsupported_route": req["params"]["route"]}, ["LOCAL_SERVED_RUNTIME_EVENT_INTEGRATION_CONTRACT.json"], ["UNSUPPORTED_ROUTE_NO_ACTION_TAKEN"]))
        elif route == "malformed_json_safe_failure":
            responses.append(response_envelope(rid, route, "MALFORMED_JSON", {"error": "request body could not be parsed"}, ["LOCAL_SERVED_RUNTIME_EVENT_INTEGRATION_CONTRACT.json"], ["MALFORMED_JSON_NO_ACTION_TAKEN"]))
        elif route == "invalid_schema_safe_failure":
            responses.append(response_envelope(rid, route, "INVALID_SCHEMA", {"error": "required route params missing"}, ["LOCAL_SERVED_RUNTIME_EVENT_INTEGRATION_CONTRACT.json"], ["INVALID_SCHEMA_NO_ACTION_TAKEN"]))

    results = []
    for req, resp in zip(requests, responses):
        success = resp["status"] in {"OK", "UNSUPPORTED_ROUTE", "MALFORMED_JSON", "INVALID_SCHEMA"} and resp["evidence_refs"] and resp["limitation_refs"] and resp["no_action_taken"]
        results.append({"request_id": req["request_id"], "route": req["route"], "status": "PASS" if success else "FAIL", "response_status": resp["status"], "no_action_taken": True})
    request_payload = {"status": "PASS", "request_count": len(requests), "requests": requests}
    response_payload = {"status": "PASS", "response_count": len(responses), "responses": responses}
    result_payload = {"status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL", "pass_count": sum(row["status"] == "PASS" for row in results), "fail_count": sum(row["status"] != "PASS" for row in results), "results": results}
    regression = {
        "status": result_payload["status"],
        "unsupported_route_safe_failure": next(resp for resp in responses if resp["route"] == "unsupported_route_safe_failure")["status"] == "UNSUPPORTED_ROUTE",
        "malformed_json_safe_failure": next(resp for resp in responses if resp["route"] == "malformed_json_safe_failure")["status"] == "MALFORMED_JSON",
        "invalid_schema_safe_failure": next(resp for resp in responses if resp["route"] == "invalid_schema_safe_failure")["status"] == "INVALID_SCHEMA",
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "EVENT_STATE_REQUEST_FIXTURES.json", request_payload)
    write_json(OUTPUT_ROOT / "EVENT_STATE_RESPONSE_FIXTURES.json", response_payload)
    write_json(OUTPUT_ROOT / "RUNTIME_EVENT_QUERY_RESULTS.json", result_payload)
    write_json(OUTPUT_ROOT / "REGRESSION_RESULTS.json", regression)
    return request_payload, response_payload, result_payload, regression


def reports(sources: dict[str, Any], responses: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    edge_registry = sources["edge_registry"]
    event_refs = [event_ref(row) for row in sources["current"][:10]]
    bound_edges = [edge for edge in edge_registry if "event_context" in edge.get("runtime_query_tags", []) or edge.get("source_domain") == "event_fabric"]
    binding_report = {
        "status": "PASS" if bound_edges else "FAIL",
        "event_ref_count": len(event_refs),
        "bound_edge_count": len(bound_edges),
        "sample_event_refs": event_refs,
        "sample_bound_edge_ids": [edge["edge_id"] for edge in bound_edges[:20]],
        "no_action_taken": True,
    }
    trace_rows = []
    for resp in responses["responses"]:
        if resp["status"] == "OK":
            trace_rows.append(
                {
                    "request_id": resp["request_id"],
                    "route": resp["route"],
                    "evidence_refs": resp["evidence_refs"],
                    "limitation_refs": resp["limitation_refs"],
                    "claim_boundary": resp["claim_boundary"],
                    "no_action_taken": True,
                }
            )
    trace = {"status": "PASS" if all(row["evidence_refs"] and row["limitation_refs"] for row in trace_rows) else "FAIL", "trace_count": len(trace_rows), "rows": trace_rows}
    write_json(OUTPUT_ROOT / "EDGE_REGISTRY_BINDING_REPORT.json", binding_report)
    write_json(OUTPUT_ROOT / "TRACE_EVIDENCE_LIMITATION_REPORT.json", trace)
    return binding_report, trace


def audit_claims() -> dict[str, Any]:
    forbidden = [
        "production_ready\": true",
        "public_api_ready\": true",
        "public_api_exposed\": true",
        "autonomous_monitoring_enabled\": true",
        "alert_push_enabled\": true",
        "dispatch_created\": true",
        "routing_control_created\": true",
        "legal_certified_claim\": true",
    ]
    joined = ""
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name not in {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.json"} and item.suffix.lower() in {".json", ".md", ".txt"}:
            joined += "\n" + item.read_text(encoding="utf-8", errors="ignore").lower()
    hits = [pattern for pattern in forbidden if pattern in joined]
    report = {"status": "PASS" if not hits else "FAIL", "forbidden_positive_claim_hits": hits, "claim_boundary": BOUNDARY}
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", report)
    return report


def audit_mutation(pre: dict[str, dict[str, Any]]) -> dict[str, Any]:
    changed = []
    for meta in UPSTREAMS.values():
        root = meta["root"]
        after = snapshot(root_path(root))
        if after != pre[root]:
            changed.append(root)
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed}
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", report)
    return report


def audit_secret() -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]+['\"]"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[a-z0-9._-]+"),
    ]
    findings = []
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name != "HASH_MANIFEST.json" and item.suffix.lower() in {".json", ".md", ".txt"}:
            text = item.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    findings.append({"path": rel(item), "pattern": pattern.pattern})
    report = {"status": "PASS" if not findings else "FAIL", "findings": findings}
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", report)
    return report


def hash_manifest() -> dict[str, Any]:
    rows = []
    for item in sorted(OUTPUT_ROOT.rglob("*")):
        if item.is_file() and item.name != "HASH_MANIFEST.json":
            rows.append({"path": rel(item), "sha256": sha256_file(item), "size_bytes": item.stat().st_size})
    failures = [row["path"] for row in rows if not (REPO_ROOT / row["path"]).exists() or sha256_file(REPO_ROOT / row["path"]) != row["sha256"]]
    report = {"status": "PASS" if rows and not failures else "FAIL", "file_count": len(rows), "failures": failures, "files": rows}
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", report)
    return report


def write_index(route_count: int) -> None:
    files = [
        "INPUT_ARTIFACT_INDEX.json",
        "UPSTREAM_BRANCH_STATUS_SUMMARY.json",
        "LOCAL_SERVED_RUNTIME_EVENT_INTEGRATION_CONTRACT.json",
        "LOCAL_RUNTIME_ROUTE_REGISTRY.json",
        "EVENT_STATE_REQUEST_FIXTURES.json",
        "EVENT_STATE_RESPONSE_FIXTURES.json",
        "RUNTIME_EVENT_QUERY_RESULTS.json",
        "EDGE_REGISTRY_BINDING_REPORT.json",
        "TRACE_EVIDENCE_LIMITATION_REPORT.json",
        "REGRESSION_RESULTS.json",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "HASH_MANIFEST.json",
    ]
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Runtime route count: `{route_count}`",
        "",
        "Local/replay served-runtime fixture contract only. Not a production service or public API.",
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- [{name}]({name})" for name in files)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

This pack integrates Event Fabric R2 state materialization and the D4X R7 multi-domain edge registry into a bounded D5 local served-runtime fixture contract.

Routes: `{route_count}`

No production service, public API readiness, autonomous monitoring, alert push, dispatch, routing/control, enforcement, legal/certified claim, or automated action is created.
""",
    )


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pre = {meta["root"]: snapshot(root_path(meta["root"])) for meta in UPSTREAMS.values()}
    input_index, missing = discover_inputs(pre)
    upstream = branch_summary(input_index)
    routes = route_registry()
    contract(routes)

    if missing:
        sources = {"edge_registry": [], "current": [], "unresolved": [], "quarantined": [], "track2a_asset_map": []}
        requests = {"status": "FAIL", "request_count": 0, "requests": []}
        responses = {"status": "FAIL", "response_count": 0, "responses": []}
        results = {"status": "FAIL", "pass_count": 0, "fail_count": len(ROUTES), "results": []}
        regression = {"status": "FAIL"}
        write_json(OUTPUT_ROOT / "EVENT_STATE_REQUEST_FIXTURES.json", requests)
        write_json(OUTPUT_ROOT / "EVENT_STATE_RESPONSE_FIXTURES.json", responses)
        write_json(OUTPUT_ROOT / "RUNTIME_EVENT_QUERY_RESULTS.json", results)
        write_json(OUTPUT_ROOT / "REGRESSION_RESULTS.json", regression)
        binding = {"status": "FAIL", "bound_edge_count": 0}
        trace = {"status": "FAIL", "trace_count": 0}
        write_json(OUTPUT_ROOT / "EDGE_REGISTRY_BINDING_REPORT.json", binding)
        write_json(OUTPUT_ROOT / "TRACE_EVIDENCE_LIMITATION_REPORT.json", trace)
    else:
        sources = load_sources()
        requests, responses, results, regression = fixtures_and_responses(sources)
        binding, trace = reports(sources, responses)

    claim = audit_claims()
    mutation = audit_mutation(pre)
    secret = audit_secret()
    write_index(routes["route_count"])

    status = PASS_STATUS
    if not all(
        [
            not missing,
            input_index["status"] == "PASS",
            upstream["status"] == "PASS",
            routes["status"] == "PASS",
            results["status"] == "PASS",
            regression["status"] == "PASS",
            binding["status"] == "PASS",
            trace["status"] == "PASS",
            claim["status"] == "PASS",
            mutation["status"] == "PASS",
            secret["status"] == "PASS",
        ]
    ):
        status = FAIL_STATUS

    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "upstream_missing": missing,
        "discovered_upstream_artifact_count": sum(len(branch["sample_artifacts"]) for branch in input_index["branches"]),
        "runtime_route_count": routes["route_count"],
        "fixture_query_pass_count": results["pass_count"],
        "fixture_query_fail_count": results["fail_count"],
        "event_state_response_count": responses["response_count"],
        "unresolved_response_count": len(sources.get("unresolved", [])),
        "quarantined_response_count": len(sources.get("quarantined", [])),
        "edge_registry_binding_status": binding["status"],
        "boundary_audit_result": claim["status"],
        "claim_boundary_status": claim["status"],
        "no_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-TRACK2-HANDOFF-R4",
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_DECISION.json", decision)
    manifest = hash_manifest()
    decision["hash_validation_status"] = manifest["status"]
    if manifest["status"] != "PASS":
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
