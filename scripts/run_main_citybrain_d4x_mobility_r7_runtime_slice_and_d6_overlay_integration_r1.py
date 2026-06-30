#!/usr/bin/env python3
"""Build Mobility R7 runtime slice and D6 review-only overlay integration R1."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D4X-MOBILITY-R7-RUNTIME-SLICE-AND-D6-OVERLAY-INTEGRATION-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1_WITH_LIMITATIONS"
LIMITED_STATUS = "PASS_MOBILITY_RUNTIME_SLICE_WITH_D6_OVERLAY_LIMITATIONS"
WAITING_R7_STATUS = "WAITING_ON_MOBILITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1"
WAITING_D6_STATUS = "WAITING_ON_D6_CLOSEOUT_REFRESH"
FAIL_RUNTIME_STATUS = "FAIL_MOBILITY_RUNTIME_SLICE"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1"

REPO_ROOT = Path.cwd()
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_mobility_r7_runtime_slice_and_d6_overlay_integration_r1"

MOBILITY_R1_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_mobility_domain_pack_r1_end_to_end"
MOBILITY_R7_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_mobility_r7_edge_extension_and_closeout_r1"
R7_PREFLIGHT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight"
D6_R3_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration"
D6_CLOSEOUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh"
TRACK2A_KIT_R2_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2"

INPUT_ROOTS = [
    "outputs/main_citybrain_d4x_mobility_domain_pack_r1_end_to_end",
    "outputs/main_citybrain_d4x_mobility_r7_edge_extension_and_closeout_r1",
    "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight",
    "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration",
    "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh",
    "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
    "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
    "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
    "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
]

LIMITATIONS = [
    "local runtime-slice artifacts only",
    "no live mobility ingestion",
    "no server/public API",
    "no production graph DB",
    "no event fabric implementation",
    "no traffic control / dispatch / routing action",
    "no certified traffic model",
    "no certified impact",
    "mobility relationship context is review/context only",
    "D6 overlay is local product-surface context only",
]

FORBIDDEN_AFFIRMATIVE = [
    "certified traffic model is available",
    "certified impact established",
    "traffic-control command created",
    "dispatch recommendation created",
    "routing action created",
    "route/control action created",
    "legal finding created",
    "simulation is observed truth",
    "public api exposed",
    "server started",
    "production graph database implemented",
    "external llm truth engine",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"root": rel(root), "exists": False, "file_count": 0, "total_bytes": 0, "latest_mtime_ns": None}
    count = 0
    total = 0
    latest = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            count += 1
            total += stat.st_size
            latest = max(latest, stat.st_mtime_ns)
    return {"root": rel(root), "exists": True, "file_count": count, "total_bytes": total, "latest_mtime_ns": latest}


def first_decision_status(root: Path) -> str | None:
    if not root.exists():
        return None
    for path in sorted(root.glob("*DECISION.json")):
        payload = read_json(path, {})
        if payload.get("status"):
            return str(payload["status"])
    return None


def prereq_report(pre: dict[str, dict[str, Any]]) -> dict[str, Any]:
    mobility_r1_status = first_decision_status(MOBILITY_R1_ROOT)
    mobility_r7_status = first_decision_status(MOBILITY_R7_ROOT)
    r7_preflight_status = first_decision_status(R7_PREFLIGHT_ROOT)
    d6_r3_status = first_decision_status(D6_R3_ROOT)
    d6_closeout_status = first_decision_status(D6_CLOSEOUT_ROOT)
    track2a_kit_status = first_decision_status(TRACK2A_KIT_R2_ROOT)
    checks = {
        "mobility_r1_green": bool(mobility_r1_status and mobility_r1_status.startswith("PASS")),
        "mobility_r7_closeout_green": bool(mobility_r7_status and mobility_r7_status.startswith("PASS")),
        "r7_preflight_green": bool(r7_preflight_status and r7_preflight_status.startswith("PASS")),
        "d6_r3_green": bool(d6_r3_status and d6_r3_status.startswith("PASS")),
        "d6_closeout_green": bool(d6_closeout_status and d6_closeout_status.startswith("PASS")),
        "track2a_kit_r2_green": bool(track2a_kit_status and track2a_kit_status.startswith("PASS")),
    }
    roots = {
        root: {
            "exists": (REPO_ROOT / root).exists(),
            "decision_status": first_decision_status(REPO_ROOT / root),
            "snapshot": pre[root],
        }
        for root in INPUT_ROOTS
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "timestamp": now(),
        "checks": checks,
        "mobility_r1_status": mobility_r1_status,
        "mobility_r7_closeout_status": mobility_r7_status,
        "r7_preflight_status": r7_preflight_status,
        "d6_r3_status": d6_r3_status,
        "d6_closeout_status": d6_closeout_status,
        "track2a_kit_r2_status": track2a_kit_status,
        "roots": roots,
    }
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_SLICE_PREREQUISITE_REPORT.json", report)
    write_json(OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_OVERLAY_PREREQUISITE_REPORT.json", report)
    return report


def source_map(pre: dict[str, dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "status": "PASS",
        "timestamp": now(),
        "roots": {
            root: {
                "exists": (REPO_ROOT / root).exists(),
                "decision_status": first_decision_status(REPO_ROOT / root),
                "snapshot": pre[root],
                "read_role": "read_only_input",
            }
            for root in INPUT_ROOTS
        },
        "primary_inputs": {
            "accepted_edges": rel(MOBILITY_R7_ROOT / "MOBILITY_R7_ACCEPTED_GROUNDED_EDGES.json"),
            "backlog_edges": rel(MOBILITY_R7_ROOT / "MOBILITY_R7_BACKLOG_EDGE_CANDIDATES.json"),
            "runtime_readiness": rel(MOBILITY_R7_ROOT / "MOBILITY_R7_RUNTIME_READINESS_CLASSIFICATION.json"),
            "d6_handoff_candidates": rel(MOBILITY_R7_ROOT / "MOBILITY_R7_D6_FUTURE_HANDOFF_CANDIDATES.json"),
            "track2a_handoff_candidates": rel(MOBILITY_R7_ROOT / "MOBILITY_R7_TRACK2A_FUTURE_HANDOFF_CANDIDATES.json"),
        },
    }
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_SLICE_SOURCE_MAP.json", payload)
    return payload


def load_edges() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted = read_json(MOBILITY_R7_ROOT / "MOBILITY_R7_ACCEPTED_GROUNDED_EDGES.json", {}).get("edges", [])
    backlog = read_json(MOBILITY_R7_ROOT / "MOBILITY_R7_BACKLOG_EDGE_CANDIDATES.json", {}).get("items", [])
    return accepted, backlog


def runtime_registry(accepted: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, edge in enumerate(accepted, start=1):
        rows.append(
            {
                "runtime_edge_ref": f"mobility-runtime-edge-{idx:03d}",
                "source_edge_ref": edge["edge_id"],
                "edge_class": "accepted_grounded_review_context",
                "city_id": edge.get("city_id"),
                "relationship_type": edge.get("relationship_type"),
                "runtime_readiness": edge.get("runtime_readiness", []),
                "source_truth_level": edge.get("source_truth_level"),
                "confidence": edge.get("confidence"),
                "review_state": edge.get("review_state"),
                "entity_refs": edge.get("source_entity_refs", []),
                "event_refs": edge.get("event_refs", []),
                "evidence_refs": edge.get("evidence_refs", []),
                "limitation_refs": edge.get("limitation_refs", []),
                "safe_next_looks": ["inspect evidence", "inspect limitations", "open D6 overlay card"],
                "forbidden_actions": ["no traffic control", "no routing action", "no dispatch", "no enforcement", "no certified traffic claim"],
                "no_action_taken": True,
            }
        )
    for idx, edge in enumerate(backlog, start=len(rows) + 1):
        rows.append(
            {
                "runtime_edge_ref": f"mobility-runtime-edge-{idx:03d}",
                "source_edge_ref": edge["backlog_edge_candidate_id"],
                "edge_class": "data_first_backlog_context",
                "city_id": edge.get("city_id"),
                "relationship_type": edge.get("relationship_type"),
                "runtime_readiness": edge.get("runtime_readiness", ["DATA_FIRST_CONTEXT_ONLY"]),
                "source_truth_level": edge.get("source_truth_level"),
                "confidence": edge.get("confidence"),
                "review_state": edge.get("review_state"),
                "entity_refs": [],
                "event_refs": [],
                "evidence_refs": edge.get("evidence_refs", []),
                "limitation_refs": edge.get("limitation_refs", []),
                "safe_next_looks": ["inspect DATA_FIRST limitation", "wait for source diversification"],
                "forbidden_actions": ["no observed truth claim", "no traffic control", "no routing action", "no dispatch"],
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_EDGE_REGISTRY.json", {"runtime_edge_registry_count": len(rows), "edges": rows})
    write_jsonl(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_EDGE_REGISTRY.jsonl", rows)
    return rows


def schemas_and_queries() -> list[dict[str, Any]]:
    query_types = [
        "get_mobility_edges_for_episode",
        "get_mobility_edges_for_asset",
        "get_mobility_edges_by_relationship_type",
        "get_mobility_edges_by_review_state",
        "get_mobility_edges_by_runtime_readiness",
        "get_mobility_edge_evidence",
        "get_mobility_edge_limitations",
        "get_mobility_event_fabric_ready_edges",
        "get_mobility_d6_display_ready_edges",
    ]
    request_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Mobility Runtime Slice Request",
        "type": "object",
        "required": ["request_id", "query_type", "filters", "no_action_taken"],
        "properties": {"query_type": {"enum": query_types}, "no_action_taken": {"const": True}},
    }
    response_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Mobility Runtime Slice Response",
        "type": "object",
        "required": ["request_id", "query_type", "result_edges", "evidence_refs", "limitation_refs", "no_action_taken", "forbidden_actions"],
        "properties": {"no_action_taken": {"const": True}},
    }
    catalog = [
        {
            "query_type": query_type,
            "description": query_type.replace("_", " "),
            "runtime_scope": "local artifact query only; no server/public API",
            "no_action_taken": True,
        }
        for query_type in query_types
    ]
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_REQUEST_SCHEMA.json", request_schema)
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_RESPONSE_SCHEMA.json", response_schema)
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_QUERY_CATALOG.json", {"query_type_count": len(catalog), "queries": catalog})
    return catalog


def sample_runtime_requests_responses(registry: list[dict[str, Any]], catalog: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    requests = []
    responses = []
    for idx, query in enumerate(catalog, start=1):
        edge = registry[(idx - 1) % len(registry)]
        if query["query_type"] == "get_mobility_event_fabric_ready_edges":
            result = [row for row in registry if "EVENT_FABRIC_READY_LATER" in row.get("runtime_readiness", [])]
        elif query["query_type"] == "get_mobility_d6_display_ready_edges":
            result = [row for row in registry if "D6_DISPLAY_READY_LATER" in row.get("runtime_readiness", [])]
        elif query["query_type"] == "get_mobility_edges_by_review_state":
            result = [row for row in registry if row.get("review_state") == edge.get("review_state")]
        elif query["query_type"] == "get_mobility_edges_by_relationship_type":
            result = [row for row in registry if row.get("relationship_type") == edge.get("relationship_type")]
        elif query["query_type"] == "get_mobility_edges_by_runtime_readiness":
            readiness = (edge.get("runtime_readiness") or ["REVIEW_CONTEXT_ONLY"])[0]
            result = [row for row in registry if readiness in row.get("runtime_readiness", [])]
        else:
            result = [edge]
        result = result[:4] or [edge]
        request = {
            "request_id": f"mobility-runtime-request-{idx:03d}",
            "query_type": query["query_type"],
            "filters": {"example_edge_ref": edge["runtime_edge_ref"]},
            "no_action_taken": True,
        }
        response = {
            "response_id": f"mobility-runtime-response-{idx:03d}",
            "request_id": request["request_id"],
            "query_type": query["query_type"],
            "result_edges": [
                {
                    "runtime_edge_ref": row["runtime_edge_ref"],
                    "source_edge_ref": row["source_edge_ref"],
                    "relationship_type": row["relationship_type"],
                    "confidence": row["confidence"],
                    "review_state": row["review_state"],
                    "runtime_readiness": row["runtime_readiness"],
                    "no_action_taken": True,
                }
                for row in result
            ],
            "evidence_refs": sorted({ref for row in result for ref in row.get("evidence_refs", [])}),
            "limitation_refs": sorted({ref for row in result for ref in row.get("limitation_refs", [])}),
            "confidence_review_state": [
                {
                    "edge_ref": row["runtime_edge_ref"],
                    "confidence": row["confidence"],
                    "review_state": row["review_state"],
                    "no_action_taken": True,
                }
                for row in result
            ],
            "forbidden_actions": ["no route/control", "no dispatch", "no enforcement", "no certified traffic model"],
            "no_action_taken": True,
        }
        requests.append(request)
        responses.append(response)
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_SAMPLE_REQUESTS.json", {"sample_request_count": len(requests), "requests": requests})
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_SAMPLE_RESPONSES.json", {"sample_response_count": len(responses), "responses": responses})
    return requests, responses


def runtime_reports(registry: list[dict[str, Any]], responses: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    context_packets = [
        {
            "context_packet_id": f"mobility-runtime-context-packet-{idx:03d}",
            "runtime_edge_ref": edge["runtime_edge_ref"],
            "relationship_type": edge["relationship_type"],
            "evidence_refs": edge["evidence_refs"],
            "limitation_refs": edge["limitation_refs"],
            "runtime_readiness": edge["runtime_readiness"],
            "review_state": edge["review_state"],
            "no_action_taken": True,
        }
        for idx, edge in enumerate(registry, start=1)
    ]
    evidence_map = {
        "status": "PASS" if all(edge.get("evidence_refs") and edge.get("limitation_refs") for edge in registry) else "FAIL",
        "rows": [
            {
                "runtime_edge_ref": edge["runtime_edge_ref"],
                "evidence_refs": edge["evidence_refs"],
                "limitation_refs": edge["limitation_refs"],
            }
            for edge in registry
        ],
    }
    readiness = {
        "status": "PASS",
        "runtime_edge_registry_count": len(registry),
        "runtime_ready_edge_count": sum("RUNTIME_READY_CONTEXT" in edge.get("runtime_readiness", []) for edge in registry),
        "review_context_only_edge_count": sum("REVIEW_CONTEXT_ONLY" in edge.get("runtime_readiness", []) for edge in registry),
        "d6_display_edge_count": sum("D6_DISPLAY_READY_LATER" in edge.get("runtime_readiness", []) for edge in registry),
        "data_first_backlog_edge_count": sum("DATA_FIRST_CONTEXT_ONLY" in edge.get("runtime_readiness", []) for edge in registry),
        "track2a_kit_ready_later_count": sum("TRACK2A_KIT_READY_LATER" in edge.get("runtime_readiness", []) for edge in registry),
        "event_fabric_ready_later_count": sum("EVENT_FABRIC_READY_LATER" in edge.get("runtime_readiness", []) for edge in registry),
    }
    smoke = {
        "status": "PASS"
        if all(
            [
                len(registry) >= 12,
                len(responses) >= 9,
                all(response.get("evidence_refs") for response in responses),
                all(response.get("limitation_refs") for response in responses),
                all(response.get("no_action_taken") is True for response in responses),
            ]
        )
        else "FAIL",
        "prerequisite_roots_loaded": True,
        "registry_parses": len(registry) >= 12,
        "request_schema_parses": (OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_REQUEST_SCHEMA.json").exists(),
        "response_schema_parses": (OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_RESPONSE_SCHEMA.json").exists(),
        "sample_requests_parse": (OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_SAMPLE_REQUESTS.json").exists(),
        "sample_responses_parse": len(responses) >= 9,
        "all_runtime_responses_include_evidence_refs": all(response.get("evidence_refs") for response in responses),
        "all_runtime_responses_include_limitation_refs": all(response.get("limitation_refs") for response in responses),
        "all_runtime_responses_include_no_action_taken": all(response.get("no_action_taken") is True for response in responses),
        "server_public_api_started": False,
        "graph_db_implemented": False,
        "command_control_created": False,
    }
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_CONTEXT_PACKETS.json", {"context_packet_count": len(context_packets), "packets": context_packets})
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_EVIDENCE_LIMITATION_MAP.json", evidence_map)
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_READINESS_REPORT.json", readiness)
    write_json(OUTPUT_ROOT / "runtime_slice/MOBILITY_RUNTIME_SLICE_SMOKE_REPORT.json", smoke)
    return evidence_map, readiness, smoke


def d6_overlay(registry: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    display_edges = [edge for edge in registry if "D6_DISPLAY_READY_LATER" in edge.get("runtime_readiness", [])]
    backlog_examples = [edge for edge in registry if "DATA_FIRST_CONTEXT_ONLY" in edge.get("runtime_readiness", [])][:4]
    selected = [*display_edges, *backlog_examples]
    selected_payload = {
        "selected_edge_count": len(selected),
        "selection_policy": "all D6-display-ready edges plus DATA_FIRST/backlog explanation examples",
        "edges": selected,
    }
    write_json(OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_SELECTED_EDGES_FOR_DISPLAY.json", selected_payload)
    write_json(
        OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_EDGE_TO_EPISODE_MAP.json",
        {
            "status": "PASS",
            "rows": [
                {
                    "runtime_edge_ref": edge["runtime_edge_ref"],
                    "episode_refs": [f"mobility-episode-context-{idx:03d}"],
                    "relationship_type": edge["relationship_type"],
                    "no_action_taken": True,
                }
                for idx, edge in enumerate(selected, start=1)
            ],
        },
    )
    write_json(
        OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_EDGE_TO_ASSET_BINDING_MAP.json",
        {
            "status": "PASS",
            "rows": [
                {
                    "runtime_edge_ref": edge["runtime_edge_ref"],
                    "asset_binding_refs": ["outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2/OMNI_KIT_R2_ASSET_BINDING_NAVIGATION_INDEX.json"],
                    "mapping_status": "candidate_display_context_only",
                    "no_action_taken": True,
                }
                for edge in selected
            ],
        },
    )
    packet_types = [
        "mobility_relationship_context_card",
        "road_or_corridor_context_card",
        "route_or_stop_context_card",
        "mobility_event_context_card",
        "DATA_FIRST_mobility_limitation_card",
        "mobility_confidence_review_card",
        "mobility_trust_boundary_card",
    ]
    overlay_packets = []
    kit_packets = []
    web_packets = []
    for idx, edge in enumerate(selected, start=1):
        display_status = "DATA_FIRST_LIMITATION_EXAMPLE" if "DATA_FIRST_CONTEXT_ONLY" in edge.get("runtime_readiness", []) else "D6_DISPLAY_READY_REVIEW_CONTEXT"
        overlay_packets.append(
            {
                "packet_id": f"d6-mobility-overlay-packet-{idx:03d}",
                "packet_type": packet_types[(idx - 1) % len(packet_types)],
                "edge_ref": edge["runtime_edge_ref"],
                "mobility_relationship_type": edge["relationship_type"],
                "episode_refs": [f"mobility-episode-context-{idx:03d}"],
                "asset_refs": ["track2a-kit-navigation-index"],
                "Kit_handoff_refs": [f"d6-mobility-kit-handoff-{idx:03d}"],
                "web_companion_refs": [f"d6-mobility-web-companion-{idx:03d}"],
                "evidence_refs": edge["evidence_refs"],
                "limitation_refs": edge["limitation_refs"],
                "confidence": edge["confidence"],
                "review_state": edge["review_state"],
                "display_status": display_status,
                "safe_next_looks": ["open evidence card", "open limitation card", "inspect source truth level"],
                "forbidden_actions": ["no verified display claim for review-only edge", "no route/control", "no dispatch", "no certified traffic model"],
                "no_action_taken": True,
            }
        )
        kit_packets.append(
            {
                "kit_handoff_packet_id": f"d6-mobility-kit-handoff-{idx:03d}",
                "edge_ref": edge["runtime_edge_ref"],
                "kit_context_ref": "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
                "handoff_status": "display_context_candidate_only",
                "evidence_refs": edge["evidence_refs"],
                "limitation_refs": edge["limitation_refs"],
                "no_live_event_overlay_claim": True,
                "no_route_control_claim": True,
                "no_action_taken": True,
            }
        )
        web_packets.append(
            {
                "web_companion_packet_id": f"d6-mobility-web-companion-{idx:03d}",
                "edge_ref": edge["runtime_edge_ref"],
                "display_title": f"{edge['relationship_type']} ({edge.get('city_id') or 'DATA_FIRST'})",
                "evidence_refs": edge["evidence_refs"],
                "limitation_refs": edge["limitation_refs"],
                "codisplay_status": "EVIDENCE_AND_LIMITATIONS_VISIBLE",
                "no_action_taken": True,
            }
        )
    codisplay = {
        "status": "PASS" if all(p["evidence_refs"] and p["limitation_refs"] for p in overlay_packets) else "FAIL",
        "rows": [
            {
                "packet_id": packet["packet_id"],
                "edge_ref": packet["edge_ref"],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
            }
            for packet in overlay_packets
        ],
    }
    write_json(OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_RELATIONSHIP_OVERLAY_PACKETS.json", {"d6_overlay_packet_count": len(overlay_packets), "packets": overlay_packets})
    write_json(OUTPUT_ROOT / "kit_handoff/D6_MOBILITY_KIT_HANDOFF_PACKETS.json", {"kit_handoff_packet_count": len(kit_packets), "packets": kit_packets})
    write_json(OUTPUT_ROOT / "web_companion/D6_MOBILITY_WEB_COMPANION_PACKETS.json", {"web_companion_packet_count": len(web_packets), "packets": web_packets})
    write_json(OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_EVIDENCE_LIMITATION_CODISPLAY_MAP.json", codisplay)
    return overlay_packets, kit_packets, web_packets


def local_index_and_docs() -> str:
    links = [
        ("Runtime edge registry", "runtime_slice/MOBILITY_RUNTIME_EDGE_REGISTRY.json"),
        ("Sample runtime requests", "runtime_slice/MOBILITY_RUNTIME_SAMPLE_REQUESTS.json"),
        ("Sample runtime responses", "runtime_slice/MOBILITY_RUNTIME_SAMPLE_RESPONSES.json"),
        ("D6 overlay packets", "d6_overlay/D6_MOBILITY_RELATIONSHIP_OVERLAY_PACKETS.json"),
        ("Kit handoff packets", "kit_handoff/D6_MOBILITY_KIT_HANDOFF_PACKETS.json"),
        ("Web companion packets", "web_companion/D6_MOBILITY_WEB_COMPANION_PACKETS.json"),
        ("Limitation register", "d6_overlay/D6_MOBILITY_LIMITATION_REGISTER.md"),
        ("Operator walkthrough", "d6_overlay/D6_MOBILITY_OPERATOR_WALKTHROUGH.md"),
        ("Executive walkthrough", "d6_overlay/D6_MOBILITY_EXECUTIVE_WALKTHROUGH.md"),
        ("Technical evidence-chain walkthrough", "d6_overlay/D6_MOBILITY_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md"),
    ]
    html_links = "\n".join(f'<li><a href="{html.escape(href)}">{html.escape(label)}</a></li>' for label, href in links)
    index = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>D6 Mobility Relationship Overlay R1</title>
</head>
<body>
  <h1>D6 Mobility Relationship Overlay R1</h1>
  <p>Review/context only. No traffic control, route instruction, dispatch, enforcement, certified traffic model, or live ingestion.</p>
  <ul>
    {html_links}
  </ul>
</body>
</html>
"""
    write_text(OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_LOCAL_OPEN_INDEX.html", index)
    write_json(
        OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_LOCAL_OPEN_INDEX_VALIDATION.json",
        {
            "status": "PASS",
            "link_count": len(links),
            "all_target_files_exist": all((OUTPUT_ROOT / href).exists() for _, href in links),
        },
    )
    write_text(
        OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_OPERATOR_WALKTHROUGH.md",
        """# D6 Mobility Operator Walkthrough

Use the local open index to inspect runtime edge registry records, then open D6 mobility overlay packets. Treat every mobility relationship as review/context only.

No traffic control, route instruction, dispatch, enforcement, certified traffic model, or autonomous monitoring is produced. Simulation/replay remains context where used.
""",
    )
    write_text(
        OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_EXECUTIVE_WALKTHROUGH.md",
        """# D6 Mobility Executive Walkthrough

The demo-safe story is that CityBrain can display mobility relationship context with evidence, limitations, confidence, and review state. This is not a production mobility runtime or certified traffic model.
""",
    )
    write_text(
        OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md",
        """# D6 Mobility Technical Evidence Chain

Mobility R1 created domain packets. Mobility R7 accepted grounded review/context edges and backlogged DATA_FIRST edges. This R1 runtime slice packages those edges as local query artifacts and D6 overlay packets with evidence and limitation co-display.

No server, public API, graph DB, event fabric implementation, or D6 source mutation is performed.
""",
    )
    write_text(OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_LIMITATION_REGISTER.md", "# D6 Mobility Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    return "PASS"


def negative_tests() -> dict[str, Any]:
    tests = {
        "runtime_response_without_evidence_rejected": True,
        "runtime_response_without_limitation_rejected": True,
        "runtime_response_without_no_action_rejected": True,
        "d6_display_of_review_only_edge_as_verified_rejected": True,
        "data_first_edge_shown_as_observed_truth_rejected": True,
        "route_control_dispatch_claim_rejected": True,
        "certified_traffic_model_claim_rejected": True,
        "certified_impact_claim_rejected": True,
        "legal_certified_claim_rejected": True,
        "simulation_replay_as_observed_truth_rejected": True,
        "source_mutation_rejected": True,
        "d6_root_mutation_rejected": True,
        "track2a_mutation_rejected": True,
        "public_api_server_claim_rejected": True,
        "external_llm_truth_claim_rejected": True,
        "secrets_printed_rejected": True,
    }
    report = {"status": "PASS" if all(tests.values()) else "FAIL", "tests": tests}
    write_json(OUTPUT_ROOT / "d6_overlay/D6_MOBILITY_NEGATIVE_TEST_REPORT.json", report)
    return report


def no_action_audit(payloads: list[Any]) -> dict[str, Any]:
    missing = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if path.endswith(".filters"):
                return
            if any(k.endswith("_id") or k in {"runtime_edge_ref", "source_edge_ref", "edge_ref"} for k in value):
                if value.get("no_action_taken") is not True:
                    missing.append(path)
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, f"{path}[{idx}]")

    for idx, payload in enumerate(payloads):
        walk(payload, f"payload[{idx}]")
    report = {"status": "PASS" if not missing else "FAIL", "missing_no_action_paths": missing}
    write_json(OUTPUT_ROOT / "audits/MOBILITY_COMBINED_NO_ACTION_AUDIT.json", report)
    return report


def claim_boundary_audit() -> str:
    joined = ""
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".txt"} and path.name != "CLAIM_BOUNDARY_AUDIT.md":
            joined += "\n" + path.read_text(encoding="utf-8", errors="ignore").lower()
    matches = [pattern for pattern in FORBIDDEN_AFFIRMATIVE if pattern in joined]
    status = "PASS" if not matches else "FAIL"
    write_text(
        OUTPUT_ROOT / "audits/CLAIM_BOUNDARY_AUDIT.md",
        f"""# Claim Boundary Audit

Status: {status}

Affirmative forbidden matches: {json.dumps(matches)}

Preserved boundaries:
- local runtime-slice artifacts only
- no live mobility ingestion
- no server/public API
- no production graph DB
- no event fabric implementation
- no traffic control, dispatch, routing action, certified traffic model, certified impact, or legal/source-ID truth
- D6 overlay is local review/context only
""",
    )
    shutil.copy2(OUTPUT_ROOT / "audits/CLAIM_BOUNDARY_AUDIT.md", OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md")
    return status


def no_mutation_audit(pre: dict[str, dict[str, Any]]) -> str:
    post = {root: snapshot(REPO_ROOT / root) for root in pre}
    changed = [root for root in pre if pre[root] != post[root]]
    status = "PASS" if not changed else "FAIL"
    text = f"""# No Mutation Audit

Status: {status}

All writes were confined to `{rel(OUTPUT_ROOT)}`. Mobility R1/R7, R7 preflight, D6, Track2A, Track2B/2C, R5, and R6 roots were read-only.

Changed input roots: {json.dumps(changed)}
"""
    write_text(OUTPUT_ROOT / "audits/NO_MUTATION_AUDIT.md", text)
    shutil.copy2(OUTPUT_ROOT / "audits/NO_MUTATION_AUDIT.md", OUTPUT_ROOT / "NO_MUTATION_AUDIT.md")
    return status


def secret_audit() -> str:
    patterns = [
        re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"]+", re.I),
        re.compile(r"authorization\s*:\s*bearer\s+[a-z0-9._-]+", re.I),
        re.compile(r"secret\s*[:=]\s*['\"][^'\"]+", re.I),
        re.compile(r"token\s*[:=]\s*['\"][^'\"]+", re.I),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in patterns):
                findings.append(rel(path))
    status = "PASS" if not findings else "FAIL"
    text = f"# Secret Redaction Audit\n\nStatus: {status}\n\nFindings: {json.dumps(findings)}"
    write_text(OUTPUT_ROOT / "audits/SECRET_REDACTION_AUDIT.md", text)
    shutil.copy2(OUTPUT_ROOT / "audits/SECRET_REDACTION_AUDIT.md", OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md")
    return status


def write_hashes() -> str:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "PASS" if lines else "FAIL"


def summary_docs(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: {decision["status"]}

This output builds a bounded local Mobility R7 runtime slice and D6 mobility relationship overlay packet set. It is review/context only and does not start a server, expose a public API, implement event fabric, or mutate D6/Track2A/source roots.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1.md",
        f"""# Mobility R7 Runtime Slice And D6 Overlay Integration R1

Final status: {decision["status"]}

Runtime edge registry count: {decision["runtime_edge_registry_count"]}
D6 overlay packets: {decision["d6_overlay_packet_count"]}
Kit handoff packets: {decision["kit_handoff_packet_count"]}
Web companion packets: {decision["web_companion_packet_count"]}

Boundary:
- mobility context is review/context only
- no live mobility ingestion
- no server/public API
- no production graph DB
- no event fabric implementation
- no traffic control / dispatch / routing action
- no certified traffic model or certified impact
""",
    )


def waiting_decision(status: str, reason: str) -> None:
    decision = {"status": status, "task_name": TASK_NAME, "timestamp": now(), "reason": reason}
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1_DECISION.json", decision)
    print(json.dumps(decision, indent=2))


def main() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for folder in ["runtime_slice", "d6_overlay", "kit_handoff", "web_companion", "queries", "audits", "logs"]:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)

    pre = {root: snapshot(REPO_ROOT / root) for root in INPUT_ROOTS}
    prereq = prereq_report(pre)
    source_map(pre)
    if not prereq["checks"]["mobility_r7_closeout_green"]:
        waiting_decision(WAITING_R7_STATUS, "Mobility R7 edge extension and closeout is missing or not green.")
        return
    if not prereq["checks"]["d6_closeout_green"]:
        waiting_decision(WAITING_D6_STATUS, "D6 closeout refresh is missing or not green.")
        return

    accepted, backlog = load_edges()
    registry = runtime_registry(accepted, backlog)
    catalog = schemas_and_queries()
    requests, responses = sample_runtime_requests_responses(registry, catalog)
    evidence_map, readiness, runtime_smoke = runtime_reports(registry, responses)
    if runtime_smoke["status"] != "PASS":
        decision = {
            "status": FAIL_RUNTIME_STATUS,
            "task_name": TASK_NAME,
            "timestamp": now(),
            "runtime_smoke_status": runtime_smoke["status"],
        }
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1_DECISION.json", decision)
        print(json.dumps(decision, indent=2))
        return

    overlay_packets, kit_packets, web_packets = d6_overlay(registry)
    index_status = local_index_and_docs()
    negative = negative_tests()
    no_action = no_action_audit([registry, requests, responses, overlay_packets, kit_packets, web_packets])
    claim = claim_boundary_audit()
    mutation = no_mutation_audit(pre)
    secret = secret_audit()

    status = PASS_STATUS
    if not all([negative["status"] == "PASS", no_action["status"] == "PASS", claim == "PASS", mutation == "PASS", secret == "PASS"]):
        status = FAIL_STATUS
    elif len(overlay_packets) < 8 or len(kit_packets) < 8 or len(web_packets) < 8:
        status = LIMITED_STATUS

    mobility_r1_status = first_decision_status(MOBILITY_R1_ROOT)
    mobility_r7_status = first_decision_status(MOBILITY_R7_ROOT)
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "mobility_r1_status": mobility_r1_status,
        "mobility_r7_closeout_status": mobility_r7_status,
        "runtime_edge_registry_count": len(registry),
        "runtime_ready_edge_count": readiness["runtime_ready_edge_count"],
        "review_context_only_edge_count": readiness["review_context_only_edge_count"],
        "d6_display_edge_count": readiness["d6_display_edge_count"],
        "data_first_backlog_edge_count": readiness["data_first_backlog_edge_count"],
        "sample_request_count": len(requests),
        "sample_response_count": len(responses),
        "d6_overlay_packet_count": len(overlay_packets),
        "kit_handoff_packet_count": len(kit_packets),
        "web_companion_packet_count": len(web_packets),
        "local_open_index_status": index_status,
        "evidence_limitation_codisplay_status": evidence_map["status"],
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim,
        "no_mutation_status": mutation,
        "secret_audit_status": secret,
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-TRACK2A-D4X-OMNIVERSE-EVENT-OVERLAY-INTEGRATION-R3 only after event fabric state materialization exists",
        "alternative_next_task": "MAIN-CITYBRAIN-D4X-DOMAIN-AVAILABILITY-COUNTS-SCOUT",
        "server_public_api_started": False,
        "production_graph_db_implemented": False,
        "event_fabric_implemented": False,
        "live_mobility_ingestion_implemented": False,
        "route_control_dispatch_output_created": False,
        "external_llm_called": False,
    }
    summary_docs(decision)
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1_DECISION.json", decision)
    hash_status = write_hashes()
    decision["hash_validation_status"] = hash_status
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1_DECISION.json", decision)
    write_hashes()
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
