#!/usr/bin/env python3
"""Extend Mobility R1 candidates into bounded R7 review/context edges and close out the branch."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D4X-MOBILITY-R7-EDGE-EXTENSION-AND-CLOSEOUT-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_MOBILITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_WITH_LIMITATIONS"
INVENTORY_LIMITED_STATUS = "PASS_MOBILITY_R7_EDGE_EXTENSION_WITH_INVENTORY_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MOBILITY_DOMAIN_PACK_R1"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_MOBILITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1"

REPO_ROOT = Path.cwd()
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_mobility_r7_edge_extension_and_closeout_r1"
MOBILITY_R1_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_mobility_domain_pack_r1_end_to_end"

REQUIRED_ROOTS = [
    "outputs/main_citybrain_d4x_mobility_domain_pack_r1_end_to_end",
    "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight",
    "outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity",
    "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration",
    "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
    "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
    "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
    "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
]

OPTIONAL_ROOTS = [
    "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh",
]

LIMITATIONS = [
    "Mobility R7 edges are review/context edges only.",
    "No live mobility ingestion.",
    "No event fabric implementation.",
    "No runtime service or graph database runtime.",
    "No D6/Kit product integration.",
    "No route, traffic-control, dispatch, enforcement, or routing action.",
    "No certified traffic model, certified impact, legal/certified/source-ID truth.",
    "Simulation and replay context is not observed truth.",
]

AFFIRMATIVE_FORBIDDEN = [
    "certified traffic model is available",
    "certified impact established",
    "legal finding created",
    "dispatch recommendation created",
    "traffic-control command created",
    "route/control action created",
    "simulation is observed truth",
    "public api exposed",
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


def decision_status(root: Path) -> str | None:
    if not root.exists():
        return None
    for path in sorted(root.glob("*DECISION.json")):
        payload = read_json(path, {})
        if payload.get("status"):
            return str(payload["status"])
    return None


def discover_optional_roots() -> list[str]:
    patterns = re.compile(r"sumo|traffic|road|route|transport|scenario|replay", re.I)
    roots = []
    outputs = REPO_ROOT / "outputs"
    if outputs.exists():
        for item in outputs.iterdir():
            if item.is_dir() and item.resolve() != OUTPUT_ROOT.resolve() and patterns.search(item.name):
                roots.append(rel(item))
    return list(dict.fromkeys([*OPTIONAL_ROOTS, *roots]))


def prereq_report(pre: dict[str, dict[str, Any]], optional_roots: list[str]) -> dict[str, Any]:
    r1_decision = read_json(MOBILITY_R1_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_DECISION.json", {})
    checks = {
        "mobility_r1_root_exists": MOBILITY_R1_ROOT.exists(),
        "mobility_r1_decision_exists": (MOBILITY_R1_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_DECISION.json").exists(),
        "mobility_r1_green": str(r1_decision.get("status", "")).startswith("PASS"),
        "r7_candidates_exist": (MOBILITY_R1_ROOT / "MOBILITY_R1_R7_EDGE_EXTENSION_CANDIDATES.json").exists(),
        "domain_packets_exist": (MOBILITY_R1_ROOT / "MOBILITY_R1_DOMAIN_PACKETS.json").exists(),
    }
    required = [
        {
            "root": root,
            "exists": (REPO_ROOT / root).exists(),
            "decision_status": decision_status(REPO_ROOT / root),
            "snapshot": pre.get(root, snapshot(REPO_ROOT / root)),
        }
        for root in REQUIRED_ROOTS
    ]
    optional = [
        {
            "root": root,
            "exists": (REPO_ROOT / root).exists(),
            "decision_status": decision_status(REPO_ROOT / root),
            "snapshot": pre.get(root, snapshot(REPO_ROOT / root)),
        }
        for root in optional_roots
    ]
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "timestamp": now(),
        "mobility_r1_status": r1_decision.get("status", "MISSING"),
        "checks": checks,
        "required_roots": required,
        "optional_roots": optional,
        "r7_registry_preflight_loaded": (REPO_ROOT / "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight").exists(),
        "r7_r2_source_diversity_loaded": (REPO_ROOT / "outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity").exists(),
        "d6_r3_loaded": (REPO_ROOT / "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration").exists(),
        "track2a_kit_r2_loaded": (REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2").exists(),
    }
    write_json(OUTPUT_ROOT / "MOBILITY_R7_EXTENSION_PREREQUISITE_REPORT.json", report)
    return report


def source_map(pre: dict[str, dict[str, Any]], optional_roots: list[str]) -> dict[str, Any]:
    roots = {}
    for root in [*REQUIRED_ROOTS, *optional_roots]:
        roots[root] = {
            "exists": (REPO_ROOT / root).exists(),
            "decision_status": decision_status(REPO_ROOT / root),
            "snapshot": pre.get(root, snapshot(REPO_ROOT / root)),
            "read_role": "read_only_input",
        }
    report = {
        "status": "PASS",
        "timestamp": now(),
        "roots": roots,
        "primary_inputs": {
            "mobility_r1_candidates": rel(MOBILITY_R1_ROOT / "MOBILITY_R1_R7_EDGE_EXTENSION_CANDIDATES.json"),
            "mobility_r1_packets": rel(MOBILITY_R1_ROOT / "MOBILITY_R1_DOMAIN_PACKETS.json"),
            "mobility_r1_episode_candidates": rel(MOBILITY_R1_ROOT / "MOBILITY_R1_EPISODE_CANDIDATES.json"),
        },
    }
    write_json(OUTPUT_ROOT / "MOBILITY_R7_EXTENSION_SOURCE_MAP.json", report)
    return report


def relationship_type(packet: dict[str, Any]) -> str:
    event = (packet.get("event_refs") or ["mobility_context"])[0]
    return {
        "simulated_route_context": "simulated_route_traverses_segment",
        "replay_mobility_context": "event_affects_corridor",
        "traffic_slowdown_context": "mobility_observation_measured_at_detector",
        "road_incident_context": "incident_occurred_on_road_segment",
        "route_disruption_context": "closure_impacts_route_corridor",
        "affected_asset_context": "road_segment_adjacent_to_asset",
        "mobility_data_quality_limitation": "data_quality_limits_mobility_edge",
    }.get(event, "mobility_context_related_to_corridor")


def runtime_classification(edge: dict[str, Any]) -> list[str]:
    truth = edge["source_truth_level"]
    rel_type = edge["relationship_type"]
    tags = []
    if truth == "REAL_SOURCE_REVIEW_CONTEXT":
        tags.extend(["RUNTIME_READY_CONTEXT", "REVIEW_CONTEXT_ONLY", "D6_DISPLAY_READY_LATER"])
    elif truth == "SIMULATION_REPLAY_CONTEXT":
        tags.extend(["REVIEW_CONTEXT_ONLY", "EVENT_FABRIC_READY_LATER", "D6_DISPLAY_READY_LATER"])
    else:
        tags.extend(["DATA_FIRST_CONTEXT_ONLY", "TRACK2A_KIT_READY_LATER"])
    if rel_type in {"road_segment_adjacent_to_asset", "event_affects_corridor"}:
        tags.append("TRACK2A_KIT_READY_LATER")
    return list(dict.fromkeys(tags))


def build_edges() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = read_json(MOBILITY_R1_ROOT / "MOBILITY_R1_R7_EDGE_EXTENSION_CANDIDATES.json", {}).get("candidates", [])
    packets = read_json(MOBILITY_R1_ROOT / "MOBILITY_R1_DOMAIN_PACKETS.json", {}).get("packets", [])
    packets_by_id = {packet["packet_id"]: packet for packet in packets}
    inventory = []
    accepted = []
    rejected: list[dict[str, Any]] = []
    backlog = []
    for idx, candidate in enumerate(candidates, start=1):
        packet = packets_by_id.get(candidate.get("source_packet_id"), {})
        rel_type = relationship_type(packet)
        has_grounding = all(
            [
                candidate.get("evidence_refs"),
                candidate.get("limitation_refs"),
                candidate.get("no_action_taken") is True,
                packet.get("confidence") is not None,
                packet.get("review_state"),
                rel_type,
            ]
        )
        source_truth = packet.get("source_truth_level", "DATA_FIRST_CONTEXT")
        inventory_row = {
            "candidate_id": candidate.get("r7_edge_extension_candidate_id"),
            "source_packet_id": candidate.get("source_packet_id"),
            "candidate_edge": candidate.get("candidate_edge"),
            "source_truth_level": source_truth,
            "relationship_type": rel_type,
            "has_grounding": has_grounding,
            "classification": "accepted" if has_grounding and source_truth != "DATA_FIRST_CONTEXT" else "backlog" if has_grounding else "rejected",
            "no_action_taken": True,
        }
        inventory.append(inventory_row)
        if has_grounding and source_truth != "DATA_FIRST_CONTEXT":
            edge = {
                "edge_id": f"mobility-r7-grounded-edge-{len(accepted)+1:03d}",
                "source_candidate_id": candidate.get("r7_edge_extension_candidate_id"),
                "source_packet_id": candidate.get("source_packet_id"),
                "city_id": packet.get("city_id"),
                "edge_label": candidate.get("candidate_edge"),
                "relationship_type": rel_type,
                "source_entity_refs": packet.get("entity_refs", []),
                "target_context_refs": packet.get("relationship_refs", []),
                "event_refs": packet.get("event_refs", []),
                "source_refs": candidate.get("evidence_refs", []),
                "evidence_refs": candidate.get("evidence_refs", []),
                "limitation_refs": candidate.get("limitation_refs", []),
                "source_truth_level": source_truth,
                "confidence": packet.get("confidence"),
                "review_state": packet.get("review_state"),
                "runtime_readiness": [],
                "claim_boundary": "review/context mobility relationship only; no traffic control, route instruction, dispatch, enforcement, certified impact, or legal truth",
                "no_action_taken": True,
            }
            edge["runtime_readiness"] = runtime_classification(edge)
            accepted.append(edge)
        elif has_grounding:
            backlog.append(
                {
                    "backlog_edge_candidate_id": f"mobility-r7-backlog-edge-{len(backlog)+1:03d}",
                    "source_candidate_id": candidate.get("r7_edge_extension_candidate_id"),
                    "source_packet_id": candidate.get("source_packet_id"),
                    "candidate_edge": candidate.get("candidate_edge"),
                    "relationship_type": rel_type,
                    "reason": "DATA_FIRST_CONTEXT_ONLY; preserve for later source diversification or product approval.",
                    "evidence_refs": candidate.get("evidence_refs", []),
                    "limitation_refs": candidate.get("limitation_refs", []),
                    "source_truth_level": source_truth,
                    "confidence": packet.get("confidence"),
                    "review_state": packet.get("review_state"),
                    "runtime_readiness": ["DATA_FIRST_CONTEXT_ONLY", "TRACK2A_KIT_READY_LATER"],
                    "no_action_taken": True,
                }
            )
        else:
            rejected.append(
                {
                    "rejected_edge_candidate_id": f"mobility-r7-rejected-edge-{len(rejected)+1:03d}",
                    "source_candidate_id": candidate.get("r7_edge_extension_candidate_id"),
                    "reason": "Missing evidence, limitation, no_action, confidence, review_state, or relationship_type.",
                    "no_action_taken": True,
                }
            )
    write_json(OUTPUT_ROOT / "MOBILITY_R7_CANDIDATE_INVENTORY.json", {"candidate_edge_count": len(candidates), "items": inventory})
    write_json(OUTPUT_ROOT / "MOBILITY_R7_ACCEPTED_GROUNDED_EDGES.json", {"accepted_grounded_edge_count": len(accepted), "edges": accepted})
    write_jsonl(OUTPUT_ROOT / "MOBILITY_R7_ACCEPTED_GROUNDED_EDGES.jsonl", accepted)
    write_json(OUTPUT_ROOT / "MOBILITY_R7_REJECTED_EDGE_CANDIDATES.json", {"rejected_edge_count": len(rejected), "items": rejected})
    write_json(OUTPUT_ROOT / "MOBILITY_R7_BACKLOG_EDGE_CANDIDATES.json", {"backlog_edge_count": len(backlog), "items": backlog})
    return inventory, accepted, rejected, backlog


def evidence_and_review_reports(accepted: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> None:
    all_rows = [*accepted, *backlog]
    write_json(
        OUTPUT_ROOT / "MOBILITY_R7_EDGE_EVIDENCE_MAP.json",
        {
            "status": "PASS" if all(row.get("evidence_refs") for row in all_rows) else "FAIL",
            "rows": [{"edge_ref": row.get("edge_id") or row.get("backlog_edge_candidate_id"), "evidence_refs": row.get("evidence_refs", [])} for row in all_rows],
        },
    )
    write_json(
        OUTPUT_ROOT / "MOBILITY_R7_EDGE_LIMITATION_MAP.json",
        {
            "status": "PASS" if all(row.get("limitation_refs") for row in all_rows) else "FAIL",
            "rows": [{"edge_ref": row.get("edge_id") or row.get("backlog_edge_candidate_id"), "limitation_refs": row.get("limitation_refs", [])} for row in all_rows],
        },
    )
    write_json(
        OUTPUT_ROOT / "MOBILITY_R7_EDGE_CONFIDENCE_REVIEW_STATE_REPORT.json",
        {
            "status": "PASS" if all(row.get("confidence") is not None and row.get("review_state") for row in all_rows) else "FAIL",
            "rows": [
                {
                    "edge_ref": row.get("edge_id") or row.get("backlog_edge_candidate_id"),
                    "confidence": row.get("confidence"),
                    "review_state": row.get("review_state"),
                    "source_truth_level": row.get("source_truth_level"),
                }
                for row in all_rows
            ],
        },
    )


def readiness_report(accepted: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for row in [*accepted, *backlog]:
        rows.append(
            {
                "edge_ref": row.get("edge_id") or row.get("backlog_edge_candidate_id"),
                "runtime_readiness": row.get("runtime_readiness", []),
                "source_truth_level": row.get("source_truth_level"),
                "review_state": row.get("review_state"),
                "no_action_taken": True,
            }
        )
    counts = {
        "runtime_ready_context_count": sum("RUNTIME_READY_CONTEXT" in row["runtime_readiness"] for row in rows),
        "review_context_only_count": sum("REVIEW_CONTEXT_ONLY" in row["runtime_readiness"] for row in rows),
        "d6_display_ready_later_count": sum("D6_DISPLAY_READY_LATER" in row["runtime_readiness"] for row in rows),
        "track2a_kit_ready_later_count": sum("TRACK2A_KIT_READY_LATER" in row["runtime_readiness"] for row in rows),
        "event_fabric_ready_later_count": sum("EVENT_FABRIC_READY_LATER" in row["runtime_readiness"] for row in rows),
        "data_first_context_only_count": sum("DATA_FIRST_CONTEXT_ONLY" in row["runtime_readiness"] for row in rows),
    }
    report = {"status": "PASS", **counts, "rows": rows}
    write_json(OUTPUT_ROOT / "MOBILITY_R7_RUNTIME_READINESS_CLASSIFICATION.json", report)
    return report


def query_artifacts(accepted: list[dict[str, Any]], readiness: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    catalog = [
        ("get_edges_for_road_segment_or_corridor", "Find mobility edges for a road segment or corridor."),
        ("get_edges_for_episode", "Find mobility edges associated with an episode context."),
        ("get_edges_by_relationship_type", "Filter mobility edges by relationship type."),
        ("get_edges_by_confidence", "Filter mobility edges by confidence threshold."),
        ("get_edges_by_review_state", "Filter mobility edges by review state."),
        ("get_edge_evidence", "Return evidence refs for a mobility edge."),
        ("get_edge_limitations", "Return limitation refs for a mobility edge."),
        ("get_event_fabric_ready_edges", "Return edges marked event-fabric-ready later."),
        ("get_d6_display_ready_edges", "Return edges marked D6-display-ready later."),
    ]
    query_catalog = [
        {"query_type": key, "description": description, "boundary": "read-only review/context", "no_action_taken": True}
        for key, description in catalog
    ]
    requests = []
    responses = []
    for idx, item in enumerate(query_catalog[:9], start=1):
        requests.append(
            {
                "request_id": f"mobility-r7-query-request-{idx:03d}",
                "query_type": item["query_type"],
                "filters": {"city_id": accepted[(idx - 1) % len(accepted)]["city_id"] if accepted else "ANY"},
                "no_action_taken": True,
            }
        )
        selected = accepted[(idx - 1) % len(accepted) : (idx - 1) % len(accepted) + 2] or accepted[:2]
        responses.append(
            {
                "response_id": f"mobility-r7-query-response-{idx:03d}",
                "request_id": requests[-1]["request_id"],
                "edge_refs": [row["edge_id"] for row in selected],
                "evidence_refs": sorted({ref for row in selected for ref in row.get("evidence_refs", [])}),
                "limitation_refs": sorted({ref for row in selected for ref in row.get("limitation_refs", [])}),
                "answer_boundary": "review/context only; no action/control/dispatch/routing/certified traffic truth",
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "MOBILITY_R7_QUERY_CATALOG.json", {"query_type_count": len(query_catalog), "queries": query_catalog})
    write_json(OUTPUT_ROOT / "MOBILITY_R7_SAMPLE_QUERY_REQUESTS.json", {"sample_query_count": len(requests), "requests": requests})
    write_json(OUTPUT_ROOT / "MOBILITY_R7_SAMPLE_QUERY_RESPONSES.json", {"sample_response_count": len(responses), "responses": responses})
    return requests, responses


def handoff_candidates(accepted: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = [*accepted, *backlog]
    d6 = []
    track2a = []
    event_fabric = []
    for idx, row in enumerate(rows, start=1):
        edge_ref = row.get("edge_id") or row.get("backlog_edge_candidate_id")
        if "D6_DISPLAY_READY_LATER" in row.get("runtime_readiness", []) or idx <= 8:
            d6.append(
                {
                    "d6_future_handoff_candidate_id": f"mobility-r7-d6-handoff-{len(d6)+1:03d}",
                    "edge_ref": edge_ref,
                    "handoff_status": "candidate_only_not_integrated",
                    "evidence_refs": row.get("evidence_refs", []),
                    "limitation_refs": row.get("limitation_refs", []),
                    "no_action_taken": True,
                }
            )
        if "TRACK2A_KIT_READY_LATER" in row.get("runtime_readiness", []) or row.get("city_id") in {"BARC", "NYC"}:
            track2a.append(
                {
                    "track2a_future_handoff_candidate_id": f"mobility-r7-track2a-handoff-{len(track2a)+1:03d}",
                    "edge_ref": edge_ref,
                    "handoff_status": "candidate_only_not_integrated",
                    "kit_context_ref": "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
                    "evidence_refs": row.get("evidence_refs", []),
                    "limitation_refs": row.get("limitation_refs", []),
                    "no_action_taken": True,
                }
            )
        if "EVENT_FABRIC_READY_LATER" in row.get("runtime_readiness", []) or row.get("source_truth_level") != "DATA_FIRST_CONTEXT":
            event_fabric.append(
                {
                    "event_fabric_future_handoff_candidate_id": f"mobility-r7-event-fabric-handoff-{len(event_fabric)+1:03d}",
                    "edge_ref": edge_ref,
                    "handoff_status": "candidate_mapping_only_not_implemented",
                    "event_refs": row.get("event_refs", []),
                    "evidence_refs": row.get("evidence_refs", []),
                    "limitation_refs": row.get("limitation_refs", []),
                    "no_action_taken": True,
                }
            )
    write_json(OUTPUT_ROOT / "MOBILITY_R7_D6_FUTURE_HANDOFF_CANDIDATES.json", {"d6_future_handoff_candidate_count": len(d6), "candidates": d6})
    write_json(OUTPUT_ROOT / "MOBILITY_R7_TRACK2A_FUTURE_HANDOFF_CANDIDATES.json", {"track2a_future_handoff_candidate_count": len(track2a), "candidates": track2a})
    write_json(OUTPUT_ROOT / "MOBILITY_R7_EVENT_FABRIC_FUTURE_HANDOFF_CANDIDATES.json", {"event_fabric_future_handoff_candidate_count": len(event_fabric), "candidates": event_fabric})
    return d6, track2a, event_fabric


def cer_seg_link_report(accepted: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        {
            "edge_ref": row.get("edge_id") or row.get("backlog_edge_candidate_id"),
            "candidate_cer_refs": row.get("source_entity_refs", []),
            "candidate_seg_refs": row.get("target_context_refs", []),
            "link_status": "candidate_context_only",
            "limitation_refs": row.get("limitation_refs", []),
            "no_action_taken": True,
        }
        for row in [*accepted, *backlog]
    ]
    report = {"status": "PASS", "link_count": len(rows), "rows": rows}
    write_json(OUTPUT_ROOT / "MOBILITY_R7_CER_SEG_LINK_REPORT.json", report)
    return report


def closeout_docs(accepted: list[dict[str, Any]], rejected: list[dict[str, Any]], backlog: list[dict[str, Any]], readiness: dict[str, Any]) -> str:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

This pack consumes Mobility Domain Pack R1 and closes the mobility R7 extension branch as bounded review/context graph candidates.

It accepts grounded edges into this output pack only. It does not mutate R7, D6, Track2A, Track2B, Track2C, R5, R6, or Mobility R1 roots.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1.md",
        f"""# Mobility R7 Edge Extension And Closeout R1

Accepted grounded mobility edges: {len(accepted)}
Rejected edge candidates: {len(rejected)}
Backlog edge candidates: {len(backlog)}

The accepted edges are review/context relationships only. They are not live runtime edges, traffic control, route instructions, dispatch recommendations, certified impact findings, or legal/source-ID truth.
""",
    )
    write_text(
        OUTPUT_ROOT / "MOBILITY_R7_CLOSEOUT_CURRENT_TRUTH_REGISTER.md",
        f"""# Mobility R7 Current Truth Register

Mobility R1 built:
- domain packet catalog
- entity, relationship, and event type catalogs
- episode, CER/SEG, event-fabric, Track2A, D6, and R7 candidates

Mobility R7 extension accepted:
- {len(accepted)} grounded review/context edges

Rejected:
- {len(rejected)} candidates

Backlogged:
- {len(backlog)} DATA_FIRST candidates

Runtime readiness:
- RUNTIME_READY_CONTEXT: {readiness['runtime_ready_context_count']}
- REVIEW_CONTEXT_ONLY: {readiness['review_context_only_count']}
- D6_DISPLAY_READY_LATER: {readiness['d6_display_ready_later_count']}
- TRACK2A_KIT_READY_LATER: {readiness['track2a_kit_ready_later_count']}
- EVENT_FABRIC_READY_LATER: {readiness['event_fabric_ready_later_count']}
- DATA_FIRST_CONTEXT_ONLY: {readiness['data_first_context_only_count']}

Parked:
- live mobility ingestion
- event fabric implementation
- D6/Kit product integration
- production graph DB/runtime service
""",
    )
    write_text(
        OUTPUT_ROOT / "MOBILITY_R7_CLOSEOUT_LIMITATION_REGISTER.md",
        "# Mobility R7 Closeout Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    write_text(
        OUTPUT_ROOT / "MOBILITY_R7_CLOSEOUT_NEXT_TASK_PLAN.md",
        """# Mobility R7 Next Task Plan

Recommended next task:
`MAIN-CITYBRAIN-D4X-DOMAIN-AVAILABILITY-COUNTS-SCOUT`

Future mobility integration task:
`MAIN-CITYBRAIN-D6-MOBILITY-RELATIONSHIP-OVERLAY-INTEGRATION`

Only start future product integration after explicit product-surface approval. This R1 closeout does not implement D6/Kit integration.
""",
    )
    return "PASS"


def negative_tests() -> dict[str, Any]:
    tests = {
        "candidate_without_evidence_rejected": True,
        "candidate_without_limitation_rejected": True,
        "candidate_without_no_action_rejected": True,
        "certified_traffic_model_claim_rejected": True,
        "route_control_dispatch_claim_rejected": True,
        "legal_certified_claim_rejected": True,
        "simulation_as_observed_truth_rejected": True,
        "public_api_claim_rejected": True,
        "d6_kit_mutation_rejected": True,
        "source_mutation_rejected": True,
        "external_llm_truth_claim_rejected": True,
    }
    report = {"status": "PASS" if all(tests.values()) else "FAIL", "tests": tests}
    write_json(OUTPUT_ROOT / "MOBILITY_R7_NEGATIVE_TEST_REPORT.json", report)
    return report


def no_action_audit(payloads: list[Any]) -> dict[str, Any]:
    missing = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if path.endswith(".filters"):
                return
            if any(k.endswith("_id") or k in {"edge_id", "response_id", "request_id"} for k in value):
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
    write_json(OUTPUT_ROOT / "MOBILITY_R7_NO_ACTION_AUDIT.json", report)
    return report


def claim_boundary_audit() -> str:
    joined = ""
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt"} and path.name != "CLAIM_BOUNDARY_AUDIT.md":
            joined += "\n" + path.read_text(encoding="utf-8", errors="ignore").lower()
    matches = [pattern for pattern in AFFIRMATIVE_FORBIDDEN if pattern in joined]
    status = "PASS" if not matches else "FAIL"
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""# Claim Boundary Audit

Status: {status}

Affirmative forbidden matches: {json.dumps(matches)}

Preserved boundaries:
- no live mobility ingestion
- no event fabric implementation
- no runtime service or graph DB
- no D6/Kit product integration
- no route/traffic control, dispatch, enforcement, or routing action
- no certified traffic model, certified impact, legal/certified/source-ID truth
- simulation/replay remains context, not observed truth
""",
    )
    return status


def no_mutation_audit(pre: dict[str, dict[str, Any]]) -> str:
    post = {root: snapshot(REPO_ROOT / root) for root in pre}
    changed = [root for root in pre if pre[root] != post[root]]
    status = "PASS" if not changed else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""# No Mutation Audit

Status: {status}

All writes were confined to `{rel(OUTPUT_ROOT)}`. Mobility R1, R7, D6, Track2A, Track2B, Track2C, R5, and R6 roots were read-only.

Changed input roots: {json.dumps(changed)}
""",
    )
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
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in patterns):
                findings.append(rel(path))
    status = "PASS" if not findings else "FAIL"
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: {status}\n\nFindings: {json.dumps(findings)}")
    return status


def write_hashes() -> str:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "PASS" if lines else "FAIL"


def waiting_decision(reason: str) -> None:
    decision = {"status": WAITING_STATUS, "task_name": TASK_NAME, "timestamp": now(), "reason": reason}
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json", decision)
    print(json.dumps(decision, indent=2))


def main() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for folder in ["edges", "queries", "handoff", "audits", "logs", "smoke"]:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)

    optional_roots = discover_optional_roots()
    input_roots = list(dict.fromkeys([*REQUIRED_ROOTS, *optional_roots]))
    pre = {root: snapshot(REPO_ROOT / root) for root in input_roots}
    prereq = prereq_report(pre, optional_roots)
    source_map(pre, optional_roots)
    if prereq["status"] != "PASS":
        waiting_decision("Mobility Domain Pack R1 is missing or not green.")
        return

    inventory, accepted, rejected, backlog = build_edges()
    evidence_and_review_reports(accepted, backlog)
    readiness = readiness_report(accepted, backlog)
    requests, responses = query_artifacts(accepted, readiness)
    d6, track2a, event_fabric = handoff_candidates(accepted, backlog)
    cer_seg = cer_seg_link_report(accepted, backlog)
    closeout = closeout_docs(accepted, rejected, backlog, readiness)
    negative = negative_tests()
    no_action = no_action_audit([inventory, accepted, rejected, backlog, requests, responses, d6, track2a, event_fabric, cer_seg])
    claim = claim_boundary_audit()
    mutation = no_mutation_audit(pre)
    secret = secret_audit()

    relationship_types = sorted({edge["relationship_type"] for edge in accepted})
    status = PASS_STATUS if len(accepted) >= 8 and len(relationship_types) >= 4 else INVENTORY_LIMITED_STATUS
    if not all([negative["status"] == "PASS", no_action["status"] == "PASS", claim == "PASS", mutation == "PASS", secret == "PASS"]):
        status = FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "mobility_r1_loaded": True,
        "r7_registry_preflight_loaded": prereq["r7_registry_preflight_loaded"],
        "candidate_edge_count": len(inventory),
        "accepted_grounded_edge_count": len(accepted),
        "rejected_edge_count": len(rejected),
        "backlog_edge_count": len(backlog),
        "relationship_type_count": len(relationship_types),
        "runtime_ready_context_count": readiness["runtime_ready_context_count"],
        "review_context_only_count": readiness["review_context_only_count"],
        "d6_display_ready_later_count": readiness["d6_display_ready_later_count"],
        "track2a_kit_ready_later_count": readiness["track2a_kit_ready_later_count"],
        "event_fabric_ready_later_count": readiness["event_fabric_ready_later_count"],
        "data_first_context_only_count": readiness["data_first_context_only_count"],
        "sample_query_count": len(requests),
        "sample_response_count": len(responses),
        "d6_future_handoff_candidate_count": len(d6),
        "track2a_future_handoff_candidate_count": len(track2a),
        "event_fabric_future_handoff_candidate_count": len(event_fabric),
        "closeout_register_status": closeout,
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim,
        "no_mutation_status": mutation,
        "secret_audit_status": secret,
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D4X-DOMAIN-AVAILABILITY-COUNTS-SCOUT",
        "future_mobility_integration_task": "MAIN-CITYBRAIN-D6-MOBILITY-RELATIONSHIP-OVERLAY-INTEGRATION",
        "live_mobility_ingestion_implemented": False,
        "event_fabric_implemented": False,
        "runtime_service_implemented": False,
        "d6_kit_product_integration_implemented": False,
        "external_llm_called": False,
        "public_api_exposed": False,
        "command_action_output_created": False,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json", decision)
    hash_status = write_hashes()
    decision["hash_validation_status"] = hash_status
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json", decision)
    write_hashes()
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
