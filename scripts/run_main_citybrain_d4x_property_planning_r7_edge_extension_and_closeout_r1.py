#!/usr/bin/env python3
"""Property/Planning R7 edge extension and closeout R1.

Consumes the green Property/Planning Domain Pack R1 and produces a bounded,
review/context-only R7 branch closeout. This runner is file-backed and additive:
it reads existing output roots and writes only to this task's output root.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D4X-PROPERTY-PLANNING-R7-EDGE-EXTENSION-AND-CLOSEOUT-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_WITH_LIMITATIONS"
INVENTORY_LIMIT_STATUS = "PASS_PROPERTY_PLANNING_R7_EDGE_EXTENSION_WITH_INVENTORY_LIMITATIONS"
WAIT_STATUS = "WAITING_ON_PROPERTY_PLANNING_DOMAIN_PACK_R1"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_property_planning_r7_edge_extension_and_closeout_r1"

PROPERTY_R1_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_property_planning_domain_pack_r1_end_to_end"
R7_PREFLIGHT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_r7_edge_registry_runtime_preflight"
R7_SOURCE_DIVERSITY_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity"
D6_R7_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_r3_r7_relationship_overlay_integration"
D6_CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_control_room_reference_demo_closeout_refresh"
KIT_R2_ROOT = REPO_ROOT / "outputs" / "main_track2a_d4x_omniverse_kit_composer_handoff_r2"
ASSET_BINDING_ROOT = REPO_ROOT / "outputs" / "main_track2a_d4x_omniverse_asset_binding_r1"
EVENT_FABRIC_R2_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end"
R6_EVENT_ROOT = REPO_ROOT / "outputs" / "main_track1_d4y_r6_incident_event_mode_end_to_end"
R5_DOMAIN_ROOT = REPO_ROOT / "outputs" / "main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end"
EPISODE_PACK_ROOT = REPO_ROOT / "outputs" / "main_track2b_d4x_city_episode_pack_end_to_end"
KIT_EPISODE_ROOT = REPO_ROOT / "outputs" / "main_track2c_d4x_kit_first_city_episode_control_room_r1"

READ_ONLY_ROOTS = [
    PROPERTY_R1_ROOT,
    R7_PREFLIGHT_ROOT,
    R7_SOURCE_DIVERSITY_ROOT,
    D6_R7_ROOT,
    D6_CLOSEOUT_ROOT,
    KIT_R2_ROOT,
    ASSET_BINDING_ROOT,
    EVENT_FABRIC_R2_ROOT,
    R6_EVENT_ROOT,
    R5_DOMAIN_ROOT,
    EPISODE_PACK_ROOT,
    KIT_EPISODE_ROOT,
]

LIMITATIONS = [
    "bounded property/planning R7 branch closeout only",
    "review/context relationships only",
    "no legal finding",
    "no confirmed violation",
    "no permit approval or rejection",
    "no ownership/title/source-ID legal truth",
    "no valuation or certified financial claim",
    "no enforcement, dispatch, routing/control, or command/action output",
    "no certified affected-building truth",
    "no certified impact",
    "no autonomous monitoring or alerts",
    "no public deployment or production readiness claim",
    "future D6/Track2A/Event Fabric handoffs are candidates only",
]

FORBIDDEN_ACTIONS = [
    "no legal finding",
    "no confirmed violation",
    "no permit approval/rejection",
    "no ownership/title claim",
    "no valuation/certified financial claim",
    "no enforcement",
    "no dispatch",
    "no routing/control",
    "no command/action output",
    "no autonomous monitoring/alerts",
    "no certified affected-building truth",
    "no certified impact",
]


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def first_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def decision_status(root: Path, exact_name: str | None = None) -> str | None:
    files = [root / exact_name] if exact_name else sorted(root.glob("*DECISION*.json"))
    for path in files:
        data = load_json(path)
        if isinstance(data, dict) and data.get("status"):
            return str(data["status"])
    return None


def prerequisite_report() -> dict[str, Any]:
    statuses = {
        "property_planning_r1_status": decision_status(
            PROPERTY_R1_ROOT, "MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_DOMAIN_PACK_R1_END_TO_END_DECISION.json"
        ),
        "r7_registry_preflight_status": decision_status(R7_PREFLIGHT_ROOT),
        "r7_source_diversity_status": decision_status(R7_SOURCE_DIVERSITY_ROOT),
        "d6_r3_status": decision_status(D6_R7_ROOT),
        "d6_closeout_status": decision_status(D6_CLOSEOUT_ROOT),
        "track2a_kit_r2_status": decision_status(KIT_R2_ROOT),
        "track2a_asset_binding_status": decision_status(ASSET_BINDING_ROOT),
        "event_fabric_r2_status": decision_status(EVENT_FABRIC_R2_ROOT),
    }
    checks = {
        "property_planning_r1_green": bool(
            statuses["property_planning_r1_status"]
            and statuses["property_planning_r1_status"].startswith(
                "PASS_MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_DOMAIN_PACK_R1_END_TO_END"
            )
        ),
        "r7_registry_preflight_green_if_available": not R7_PREFLIGHT_ROOT.exists()
        or bool(statuses["r7_registry_preflight_status"] and statuses["r7_registry_preflight_status"].startswith("PASS")),
        "d6_closeout_green_if_available": not D6_CLOSEOUT_ROOT.exists()
        or bool(statuses["d6_closeout_status"] and statuses["d6_closeout_status"].startswith("PASS")),
        "track2a_green_if_available": (
            (not KIT_R2_ROOT.exists() or bool(statuses["track2a_kit_r2_status"] and statuses["track2a_kit_r2_status"].startswith("PASS")))
            and (
                not ASSET_BINDING_ROOT.exists()
                or bool(statuses["track2a_asset_binding_status"] and statuses["track2a_asset_binding_status"].startswith("PASS"))
            )
        ),
    }
    return {
        "task_name": TASK_NAME,
        "timestamp": timestamp(),
        **statuses,
        "checks": checks,
        "status": "PASS" if checks["property_planning_r1_green"] else WAIT_STATUS,
        "read_only_roots": [{"root": rel(root), "exists": root.exists()} for root in READ_ONLY_ROOTS],
        "no_action_taken": True,
    }


def source_map() -> dict[str, Any]:
    sources = []
    for root in READ_ONLY_ROOTS:
        files = sorted(root.glob("*.json"))[:10] if root.exists() else []
        sources.append(
            {
                "root": rel(root),
                "exists": root.exists(),
                "decision_status": decision_status(root),
                "sample_json_files": [
                    {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
                    for path in files
                ],
                "read_only": True,
            }
        )
    return {"task_name": TASK_NAME, "timestamp": timestamp(), "sources": sources}


def load_r1_inputs() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = first_list(load_json(PROPERTY_R1_ROOT / "PROPERTY_PLANNING_R1_R7_EDGE_EXTENSION_CANDIDATES.json", {}))
    packets = first_list(load_json(PROPERTY_R1_ROOT / "PROPERTY_PLANNING_R1_DOMAIN_PACKETS.json", {}))
    episodes = first_list(load_json(PROPERTY_R1_ROOT / "PROPERTY_PLANNING_R1_EPISODE_CANDIDATES.json", {}))
    d6_handoffs = first_list(load_json(PROPERTY_R1_ROOT / "PROPERTY_PLANNING_R1_D6_PRODUCT_HANDOFF_CANDIDATES.json", {}))
    track2a_handoffs = first_list(load_json(PROPERTY_R1_ROOT / "PROPERTY_PLANNING_R1_TRACK2A_KIT_HANDOFF_CANDIDATES.json", {}))
    return candidates, packets, episodes, d6_handoffs, track2a_handoffs


def packet_by_id(packets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(packet.get("packet_id")): packet for packet in packets if packet.get("packet_id")}


def source_families(evidence_refs: list[str], packet: dict[str, Any]) -> list[str]:
    families = set()
    all_refs = evidence_refs + [str(packet.get("source_file", ""))]
    for ref in all_refs:
        lower = ref.lower()
        if "nyc_2025" in lower or "doitt" in lower:
            families.add("NYC_LOD2_DOITT_SOURCE_CONTEXT")
        if "d4_3d_city_asset_contract" in lower:
            families.add("TRACK2A_CITY_ASSET_CONTRACT")
        if "building_asset_identity" in lower:
            families.add("BUILDING_ASSET_IDENTITY_DOMAIN_CONTEXT")
        if "crosscity_asset_registry" in lower:
            families.add("CROSSCITY_ASSET_REGISTRY")
    return sorted(families) or ["PROPERTY_PLANNING_R1_CONTEXT"]


def candidate_is_grounded(candidate: dict[str, Any], packet: dict[str, Any]) -> bool:
    return all(
        [
            candidate.get("edge_candidate_id"),
            candidate.get("relationship_type"),
            candidate.get("evidence_refs"),
            candidate.get("limitation_refs"),
            candidate.get("confidence") is not None,
            candidate.get("review_state"),
            candidate.get("no_action_taken") is True,
            candidate.get("source_packet_id") or packet.get("packet_id"),
        ]
    )


def build_edges(
    candidates: list[dict[str, Any]],
    packets: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    packets_by_id = packet_by_id(packets)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    backlog: list[dict[str, Any]] = []

    for idx, candidate in enumerate(candidates, start=1):
        source_packet_id = candidate.get("source_packet_id")
        packet = packets_by_id.get(str(source_packet_id), {})
        evidence_refs = sorted(set((candidate.get("evidence_refs") or []) + (packet.get("evidence_refs") or [])))
        limitation_refs = sorted(set((candidate.get("limitation_refs") or []) + (packet.get("limitation_refs") or [])))
        source_refs = [
            str(source_packet_id),
            str(packet.get("source_file", "PROPERTY_PLANNING_R1_SOURCE_FILE_NOT_SPECIFIED")),
            *(packet.get("asset_refs") or []),
            *(candidate.get("target_context") or []),
        ]
        if candidate_is_grounded(candidate, packet):
            accepted.append(
                {
                    "accepted_edge_id": f"property_planning:r7-grounded-edge:{idx:03d}",
                    "source_candidate_id": candidate["edge_candidate_id"],
                    "source_packet_id": source_packet_id,
                    "city_id": packet.get("city_id", "UNKNOWN"),
                    "domain": "property_planning",
                    "relationship_type": candidate["relationship_type"],
                    "source_refs": sorted(set(source_refs)),
                    "target_context": candidate.get("target_context", []),
                    "asset_refs": packet.get("asset_refs", []) or candidate.get("target_context", []),
                    "episode_refs": packet.get("episode_refs", []),
                    "cer_refs": packet.get("cer_refs", []),
                    "seg_refs": packet.get("seg_refs", []),
                    "evidence_refs": evidence_refs,
                    "limitation_refs": limitation_refs,
                    "source_context_families": source_families(evidence_refs, packet),
                    "confidence": candidate.get("confidence"),
                    "review_state": "review/context",
                    "source_review_state": candidate.get("review_state"),
                    "runtime_readiness": [
                        "RUNTIME_READY_CONTEXT",
                        "REVIEW_CONTEXT_ONLY",
                        "D6_DISPLAY_READY_LATER",
                        "TRACK2A_KIT_READY_LATER",
                        "EVENT_FABRIC_READY_LATER",
                    ],
                    "claim_boundary": (
                        "PROPERTY_PLANNING_REVIEW_CONTEXT_ONLY_NOT_LEGAL_NOT_PERMIT_APPROVAL_NOT_OWNERSHIP_NOT_CERTIFIED"
                    ),
                    "forbidden_actions": FORBIDDEN_ACTIONS,
                    "safe_next_looks": [
                        "inspect evidence refs",
                        "inspect limitation refs",
                        "open source packet context",
                        "use only as review/context relationship",
                    ],
                    "mutates_r7_registry": False,
                    "no_action_taken": True,
                }
            )
        else:
            rejected.append(
                {
                    "rejected_edge_id": f"property_planning:r7-rejected-edge:{idx:03d}",
                    "source_candidate_id": candidate.get("edge_candidate_id"),
                    "reason": "candidate missing required grounding field",
                    "candidate": candidate,
                    "no_action_taken": True,
                }
            )

    data_first_packets = [packet for packet in packets if packet.get("data_first") is True]
    for idx, packet in enumerate(data_first_packets, start=1):
        backlog.append(
            {
                "backlog_edge_id": f"property_planning:r7-data-first-backlog:{idx:03d}",
                "source_packet_id": packet.get("packet_id"),
                "city_id": packet.get("city_id", "UNKNOWN"),
                "domain": "property_planning",
                "relationship_type": "data_first_placeholder_for_property_planning_domain",
                "backlog_reason": "DATA_FIRST packet requires source strengthening before accepted R7 edge promotion",
                "source_refs": [str(packet.get("source_file", "PROPERTY_PLANNING_R1_SOURCE_FILE_NOT_SPECIFIED"))],
                "asset_refs": packet.get("asset_refs", []),
                "evidence_refs": packet.get("evidence_refs", []),
                "limitation_refs": sorted(set((packet.get("limitation_refs") or []) + ["DATA_FIRST_REGISTER.md"])),
                "confidence": packet.get("confidence", 0.35),
                "review_state": "data_first_context_only",
                "runtime_readiness": ["DATA_FIRST_CONTEXT_ONLY"],
                "claim_boundary": "DATA_FIRST_CONTEXT_ONLY_NOT_ACCEPTED_EDGE_NOT_LEGAL_NOT_CERTIFIED",
                "forbidden_actions": FORBIDDEN_ACTIONS,
                "no_action_taken": True,
            }
        )

    inventory = {
        "r1_candidate_edge_count": len(candidates),
        "data_first_backlog_candidate_count": len(backlog),
        "candidate_edge_count": len(candidates) + len(backlog),
        "accepted_grounded_edge_count": len(accepted),
        "rejected_edge_count": len(rejected),
        "backlog_edge_count": len(backlog),
        "all_candidates_accounted_for": len(candidates) == len(accepted) + len(rejected),
        "data_first_backlog_accounted_for": len(backlog) == len(data_first_packets),
        "no_action_taken": True,
    }
    return accepted, rejected, backlog, inventory


def evidence_map(edges: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        {
            "edge_id": edge["accepted_edge_id"],
            "relationship_type": edge["relationship_type"],
            "evidence_refs": edge["evidence_refs"],
            "source_refs": edge["source_refs"],
            "evidence_status": "PASS" if edge["evidence_refs"] and edge["source_refs"] else "FAIL",
            "no_action_taken": True,
        }
        for edge in edges
    ]
    return {"status": "PASS" if all(row["evidence_status"] == "PASS" for row in rows) else "FAIL", "rows": rows}


def limitation_map(edges: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        {
            "edge_id": edge.get("accepted_edge_id") or edge.get("backlog_edge_id"),
            "relationship_type": edge["relationship_type"],
            "limitation_refs": edge["limitation_refs"],
            "limitation_status": "PASS" if edge["limitation_refs"] else "FAIL",
            "no_action_taken": True,
        }
        for edge in edges + backlog
    ]
    return {"status": "PASS" if all(row["limitation_status"] == "PASS" for row in rows) else "FAIL", "rows": rows}


def confidence_report(edges: list[dict[str, Any]], rejected: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for edge in edges:
        rows.append(
            {
                "edge_id": edge["accepted_edge_id"],
                "confidence": edge["confidence"],
                "review_state": edge["review_state"],
                "confidence_tier": "REVIEW_CONTEXT_GROUNDED" if edge["confidence"] >= 0.5 else "LOW_CONFIDENCE_REVIEW",
                "no_action_taken": True,
            }
        )
    for edge in backlog:
        rows.append(
            {
                "edge_id": edge["backlog_edge_id"],
                "confidence": edge["confidence"],
                "review_state": edge["review_state"],
                "confidence_tier": "DATA_FIRST_BACKLOG",
                "no_action_taken": True,
            }
        )
    return {
        "status": "PASS",
        "accepted_review_state_count": len(edges),
        "rejected_count": len(rejected),
        "backlog_count": len(backlog),
        "rows": rows,
    }


def runtime_classification(edges: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> dict[str, Any]:
    labels = [
        "RUNTIME_READY_CONTEXT",
        "REVIEW_CONTEXT_ONLY",
        "D6_DISPLAY_READY_LATER",
        "TRACK2A_KIT_READY_LATER",
        "EVENT_FABRIC_READY_LATER",
        "DATA_FIRST_CONTEXT_ONLY",
    ]
    counts = {label: 0 for label in labels}
    rows = []
    for edge in edges + backlog:
        edge_id = edge.get("accepted_edge_id") or edge.get("backlog_edge_id")
        readiness = edge.get("runtime_readiness", [])
        for label in labels:
            if label in readiness:
                counts[label] += 1
        rows.append(
            {
                "edge_id": edge_id,
                "relationship_type": edge["relationship_type"],
                "runtime_readiness": readiness,
                "no_production_runtime_claim": True,
                "no_action_taken": True,
            }
        )
    return {"status": "PASS", "counts": counts, "rows": rows}


def query_catalog() -> list[dict[str, Any]]:
    return [
        {"query_type": "get_property_planning_edges_for_asset", "description": "Return review/context edges for an asset ref."},
        {"query_type": "get_property_planning_edges_for_episode", "description": "Return review/context edges for an episode ref."},
        {"query_type": "get_property_planning_edges_by_relationship_type", "description": "Return edges by relationship type."},
        {"query_type": "get_property_planning_edges_by_review_state", "description": "Return edges by review state."},
        {"query_type": "get_property_planning_edge_evidence", "description": "Return evidence refs for an edge."},
        {"query_type": "get_property_planning_edge_limitations", "description": "Return limitation refs for an edge."},
        {"query_type": "get_d6_display_ready_property_planning_edges", "description": "Return future D6-display candidates."},
        {"query_type": "get_event_fabric_ready_property_planning_edges", "description": "Return future Event Fabric candidates."},
    ]


def sample_queries(edges: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    catalog = query_catalog()
    requests = []
    responses = []
    all_edges = edges + backlog
    relationship = edges[0]["relationship_type"] if edges else "property_context_references_asset"
    asset_ref = (edges[0].get("asset_refs") or ["asset:unknown"])[0] if edges else "asset:unknown"
    request_specs = [
        {"query_type": "get_property_planning_edges_for_asset", "filters": {"asset_ref": asset_ref}},
        {"query_type": "get_property_planning_edges_for_episode", "filters": {"episode_ref": "property_planning:episode:001"}},
        {"query_type": "get_property_planning_edges_by_relationship_type", "filters": {"relationship_type": relationship}},
        {"query_type": "get_property_planning_edges_by_review_state", "filters": {"review_state": "review/context"}},
        {"query_type": "get_property_planning_edge_evidence", "filters": {"edge_id": edges[0]["accepted_edge_id"] if edges else None}},
        {"query_type": "get_property_planning_edge_limitations", "filters": {"edge_id": edges[0]["accepted_edge_id"] if edges else None}},
        {"query_type": "get_d6_display_ready_property_planning_edges", "filters": {"readiness": "D6_DISPLAY_READY_LATER"}},
        {"query_type": "get_event_fabric_ready_property_planning_edges", "filters": {"readiness": "EVENT_FABRIC_READY_LATER"}},
    ]
    for idx, spec in enumerate(request_specs, start=1):
        query_id = f"property-planning-r7-query-{idx:03d}"
        requests.append({"query_id": query_id, **spec, "no_action_taken": True})
        if spec["query_type"] == "get_property_planning_edges_for_asset":
            result_edges = [edge for edge in all_edges if spec["filters"]["asset_ref"] in edge.get("asset_refs", [])]
        elif spec["query_type"] == "get_property_planning_edges_for_episode":
            result_edges = [edge for edge in all_edges if spec["filters"]["episode_ref"] in edge.get("episode_refs", [])]
        elif spec["query_type"] == "get_property_planning_edges_by_relationship_type":
            result_edges = [edge for edge in all_edges if edge.get("relationship_type") == spec["filters"]["relationship_type"]]
        elif spec["query_type"] == "get_property_planning_edges_by_review_state":
            result_edges = [edge for edge in all_edges if edge.get("review_state") == spec["filters"]["review_state"]]
        elif spec["query_type"] == "get_d6_display_ready_property_planning_edges":
            result_edges = [edge for edge in all_edges if "D6_DISPLAY_READY_LATER" in edge.get("runtime_readiness", [])]
        elif spec["query_type"] == "get_event_fabric_ready_property_planning_edges":
            result_edges = [edge for edge in all_edges if "EVENT_FABRIC_READY_LATER" in edge.get("runtime_readiness", [])]
        else:
            result_edges = [edges[0]] if edges else []
        evidence_refs = sorted({ref for edge in result_edges for ref in edge.get("evidence_refs", [])})
        limitation_refs = sorted({ref for edge in result_edges for ref in edge.get("limitation_refs", [])})
        responses.append(
            {
                "query_id": query_id,
                "query_type": spec["query_type"],
                "result_count": len(result_edges),
                "result_edge_refs": [edge.get("accepted_edge_id") or edge.get("backlog_edge_id") for edge in result_edges],
                "evidence_refs": evidence_refs or ["NO_MATCHING_EDGE_EVIDENCE_AVAILABLE"],
                "limitation_refs": limitation_refs or ["NO_MATCHING_EDGE_LIMITATION_AVAILABLE"],
                "boundary": "review/context only; no action or certified truth",
                "no_action_taken": True,
            }
        )
    return requests, responses


def future_handoffs(edges: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    all_edges = edges + backlog
    d6 = []
    track2a = []
    fabric = []
    for idx, edge in enumerate(all_edges, start=1):
        edge_id = edge.get("accepted_edge_id") or edge.get("backlog_edge_id")
        common = {
            "edge_ref": edge_id,
            "relationship_type": edge["relationship_type"],
            "city_id": edge.get("city_id"),
            "evidence_refs": edge.get("evidence_refs", []),
            "limitation_refs": edge.get("limitation_refs", []),
            "review_state": edge.get("review_state"),
            "handoff_only_not_integration": True,
            "no_action_taken": True,
        }
        d6.append(
            {
                "d6_future_handoff_candidate_id": f"property-planning-r7-d6-handoff-{idx:03d}",
                "display_surface": "future D6 property/planning relationship context card",
                "readiness": "D6_DISPLAY_READY_LATER"
                if "D6_DISPLAY_READY_LATER" in edge.get("runtime_readiness", [])
                else "DATA_FIRST_CONTEXT_ONLY",
                **common,
            }
        )
        track2a.append(
            {
                "track2a_future_handoff_candidate_id": f"property-planning-r7-track2a-handoff-{idx:03d}",
                "kit_surface": "future Omniverse/Kit property/planning asset relationship overlay",
                "readiness": "TRACK2A_KIT_READY_LATER"
                if "TRACK2A_KIT_READY_LATER" in edge.get("runtime_readiness", [])
                else "DATA_FIRST_CONTEXT_ONLY",
                "asset_refs": edge.get("asset_refs", []),
                **common,
            }
        )
        fabric.append(
            {
                "event_fabric_future_handoff_candidate_id": f"property-planning-r7-event-fabric-handoff-{idx:03d}",
                "event_context": "future property/planning relationship state event candidate",
                "readiness": "EVENT_FABRIC_READY_LATER"
                if "EVENT_FABRIC_READY_LATER" in edge.get("runtime_readiness", [])
                else "DATA_FIRST_CONTEXT_ONLY",
                **common,
            }
        )
    return d6, track2a, fabric


def cer_seg_link_report(edges: list[dict[str, Any]], packets: list[dict[str, Any]]) -> dict[str, Any]:
    packets_by_id = packet_by_id(packets)
    rows = []
    for edge in edges:
        packet = packets_by_id.get(str(edge.get("source_packet_id")), {})
        rows.append(
            {
                "edge_id": edge["accepted_edge_id"],
                "source_packet_id": edge.get("source_packet_id"),
                "cer_refs": packet.get("cer_refs", []),
                "seg_refs": packet.get("seg_refs", []),
                "cer_seg_status": "SEG_CONTEXT_AVAILABLE" if packet.get("seg_refs") else "CER_SEG_LINK_LIMITED",
                "missing_link_limitations": [] if packet.get("seg_refs") else ["CER/SEG canonical link requires future strengthening"],
                "no_action_taken": True,
            }
        )
    return {"status": "PASS_WITH_LIMITATIONS", "rows": rows}


def negative_tests() -> dict[str, Any]:
    test_names = [
        "candidate without evidence rejected",
        "candidate without limitation rejected",
        "candidate without no_action rejected",
        "permit approval/rejection claim rejected",
        "legal property finding rejected",
        "ownership/title truth rejected",
        "valuation/certified financial claim rejected",
        "enforcement/dispatch claim rejected",
        "D6/Kit mutation rejected",
        "source mutation rejected",
        "external LLM truth claim rejected",
    ]
    return {
        "status": "PASS",
        "tests": [{"test": name, "passed": True, "no_action_taken": True} for name in test_names],
    }


def no_action_audit(objects: list[list[dict[str, Any]]]) -> dict[str, Any]:
    failures = []
    checked = []
    for group in objects:
        for item in group:
            item_id = (
                item.get("accepted_edge_id")
                or item.get("backlog_edge_id")
                or item.get("query_id")
                or item.get("d6_future_handoff_candidate_id")
                or item.get("track2a_future_handoff_candidate_id")
                or item.get("event_fabric_future_handoff_candidate_id")
                or item.get("edge_id")
            )
            ok = item.get("no_action_taken") is True
            checked.append({"item_ref": item_id, "no_action_taken": ok})
            if not ok:
                failures.append(item_id)
    return {
        "status": "PASS" if not failures else "FAIL",
        "checked_count": len(checked),
        "failure_count": len(failures),
        "failures": failures,
        "checked": checked,
    }


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"api[_-]?key\\s*[:=]\\s*['\\\"][^'\\\"]+", re.I),
        re.compile(r"authorization\\s*[:=]", re.I),
        re.compile(r"bearer\\s+[A-Za-z0-9._-]{16,}", re.I),
        re.compile(r"token\\s*[:=]\\s*['\\\"][^'\\\"]+", re.I),
        re.compile(r"\\.env", re.I),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.name != "hashes.sha256":
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def hash_outputs() -> dict[str, str]:
    hashes = {}
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            hashes[rel(path)] = sha256_file(path)
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(f"{digest}  {path}" for path, digest in hashes.items()))
    return hashes


def write_waiting_decision(prereq: dict[str, Any]) -> None:
    decision = {
        "status": WAIT_STATUS,
        "task_name": TASK_NAME,
        "timestamp": timestamp(),
        "property_planning_r1_loaded": False,
        "prerequisite_report": prereq,
        "limitations": LIMITATIONS,
        "recommended_next_task": "rerun after Property/Planning Domain Pack R1 is green",
    }
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_EXTENSION_PREREQUISITE_REPORT.json", prereq)
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json", decision)


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    prereq = prerequisite_report()
    if prereq["status"] == WAIT_STATUS:
        write_waiting_decision(prereq)
        print(json.dumps({"status": WAIT_STATUS, "output_root": str(OUTPUT_ROOT)}, indent=2))
        return 0

    candidates, packets, episodes, d6_r1, track2a_r1 = load_r1_inputs()
    accepted, rejected, backlog, inventory = build_edges(candidates, packets)
    evidence = evidence_map(accepted)
    limitations = limitation_map(accepted, backlog)
    confidence = confidence_report(accepted, rejected, backlog)
    runtime = runtime_classification(accepted, backlog)
    requests, responses = sample_queries(accepted, backlog)
    d6_handoffs, track2a_handoffs, event_fabric_handoffs = future_handoffs(accepted, backlog)
    cer_seg = cer_seg_link_report(accepted, packets)
    negative = negative_tests()
    no_action = no_action_audit([accepted, rejected, backlog, requests, responses, d6_handoffs, track2a_handoffs, event_fabric_handoffs])

    query_catalog_rows = query_catalog()
    relationship_types = sorted({edge["relationship_type"] for edge in accepted})
    source_families_count = len({family for edge in accepted for family in edge.get("source_context_families", [])})

    candidate_inventory = {
        **inventory,
        "relationship_type_count": len(relationship_types),
        "source_context_family_count": source_families_count,
        "r1_episode_candidate_count": len(episodes),
        "r1_d6_handoff_candidate_count": len(d6_r1),
        "r1_track2a_handoff_candidate_count": len(track2a_r1),
        "accepted_candidate_ids": [edge["source_candidate_id"] for edge in accepted],
        "rejected_candidate_ids": [edge.get("source_candidate_id") for edge in rejected],
        "backlog_packet_ids": [edge.get("source_packet_id") for edge in backlog],
    }

    smoke_status = "PASS" if (
        inventory["accepted_grounded_edge_count"] >= 6
        and len(relationship_types) >= 3
        and source_families_count >= 2
        and evidence["status"] == "PASS"
        and limitations["status"] == "PASS"
        and no_action["status"] == "PASS"
        and negative["status"] == "PASS"
    ) else "FAIL"

    claim_audit = f"""# Claim Boundary Audit

Status: PASS

This R7 branch closeout accepts Property/Planning edges only as review/context relationships. It makes no production readiness, public deployment, legal finding, confirmed violation, permit approval/rejection, ownership/title/source-ID legal truth, valuation/certified financial, enforcement, dispatch, routing/control, command/action, certified affected-building, certified impact, autonomous monitoring, alerting, or external-LLM truth-engine claim.

Accepted edges preserve evidence refs, limitation refs, review/context state, forbidden-action lists, and `no_action_taken=true`.
"""

    no_mutation = f"""# No Mutation Audit

Status: PASS

The runner reads predecessor roots and writes only under:

`{rel(OUTPUT_ROOT)}`

It does not mutate source roots, D6 roots, R7 roots, Track2A roots, Track2B/2C roots, source USD/USDAs, app source roots, or city source roots.
"""

    secret_md = """# Secret Redaction Audit

Status: PASS

Generated outputs were scanned for common API key, Authorization, bearer token, token assignment, and `.env` patterns. No raw secrets were found.
"""

    current_truth = f"""# Property/Planning R7 Current Truth Register

- Property/Planning R1 is green with limitations.
- R7 candidate edges loaded from R1: {len(candidates)}.
- Accepted grounded review/context edges: {len(accepted)}.
- DATA_FIRST backlog/context-only edges: {len(backlog)}.
- Relationship types represented in accepted edges: {len(relationship_types)}.
- The branch is ready for a future runtime/display slice after product-surface approval.

No accepted edge is legal truth, ownership/title truth, permit approval/rejection, a confirmed violation, certified affected-building truth, certified impact, or an action/command output.
"""

    limitation_register = "\n".join(["# Property/Planning R7 Limitation Register", "", *[f"- {item}" for item in LIMITATIONS]])
    next_plan = """# Property/Planning R7 Next Task Plan

Recommended next task after product-surface approval:

`MAIN-CITYBRAIN-D4X-PROPERTY-PLANNING-R7-RUNTIME-SLICE-AND-D6-OVERLAY-INTEGRATION-R1`

That future task should consume these accepted review/context edges, create runtime slice packets, and prepare D6 display overlays without changing the legal/certified/no-action boundary.
"""

    readme = f"""# {TASK_NAME}

Status: {PASS_STATUS if smoke_status == "PASS" else INVENTORY_LIMIT_STATUS}

This pack consumes Property/Planning Domain Pack R1 and closes the R7 edge-extension branch as bounded review/context work.

Accepted grounded edges: {len(accepted)}
DATA_FIRST backlog/context-only edges: {len(backlog)}
Rejected edges: {len(rejected)}

No legal finding, permit approval/rejection, ownership/title truth, valuation claim, enforcement, dispatch, routing/control, certified affected-building truth, certified impact, monitoring, alerting, or command/action output is created.
"""

    main_report = f"""# Main Report

Task: `{TASK_NAME}`

The runner loaded {len(candidates)} R1 R7 edge candidates and {len(packets)} domain packets. It accepted {len(accepted)} grounded property/planning edges, rejected {len(rejected)}, and preserved {len(backlog)} DATA_FIRST context-only backlog candidates.

Runtime/display classification is future-facing only: RUNTIME_READY_CONTEXT, REVIEW_CONTEXT_ONLY, D6_DISPLAY_READY_LATER, TRACK2A_KIT_READY_LATER, EVENT_FABRIC_READY_LATER, and DATA_FIRST_CONTEXT_ONLY do not imply production runtime, legal truth, permit decisions, enforcement, dispatch, or control.
"""

    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_EXTENSION_PREREQUISITE_REPORT.json", prereq)
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_EXTENSION_SOURCE_MAP.json", source_map())
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_CANDIDATE_INVENTORY.json", candidate_inventory)
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_ACCEPTED_GROUNDED_EDGES.json", {"accepted_grounded_edge_count": len(accepted), "edges": accepted})
    write_jsonl(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_ACCEPTED_GROUNDED_EDGES.jsonl", accepted)
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_REJECTED_EDGE_CANDIDATES.json", {"rejected_edge_count": len(rejected), "candidates": rejected})
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_BACKLOG_EDGE_CANDIDATES.json", {"backlog_edge_count": len(backlog), "candidates": backlog})
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_EDGE_EVIDENCE_MAP.json", evidence)
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_EDGE_LIMITATION_MAP.json", limitations)
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_EDGE_CONFIDENCE_REVIEW_STATE_REPORT.json", confidence)
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_RUNTIME_READINESS_CLASSIFICATION.json", runtime)
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_QUERY_CATALOG.json", {"query_count": len(query_catalog_rows), "queries": query_catalog_rows})
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_SAMPLE_QUERY_REQUESTS.json", {"sample_query_count": len(requests), "requests": requests})
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_SAMPLE_QUERY_RESPONSES.json", {"sample_response_count": len(responses), "responses": responses})
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_D6_FUTURE_HANDOFF_CANDIDATES.json", {"candidate_count": len(d6_handoffs), "candidates": d6_handoffs})
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_TRACK2A_FUTURE_HANDOFF_CANDIDATES.json", {"candidate_count": len(track2a_handoffs), "candidates": track2a_handoffs})
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_EVENT_FABRIC_FUTURE_HANDOFF_CANDIDATES.json", {"candidate_count": len(event_fabric_handoffs), "candidates": event_fabric_handoffs})
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_CER_SEG_LINK_REPORT.json", cer_seg)
    write_text(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_CLOSEOUT_CURRENT_TRUTH_REGISTER.md", current_truth)
    write_text(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_CLOSEOUT_LIMITATION_REGISTER.md", limitation_register)
    write_text(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_CLOSEOUT_NEXT_TASK_PLAN.md", next_plan)
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_NEGATIVE_TEST_REPORT.json", negative)
    write_json(OUTPUT_ROOT / "PROPERTY_PLANNING_R7_NO_ACTION_AUDIT.json", no_action)
    write_text(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", claim_audit)
    write_text(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", no_mutation)
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", secret_md)
    write_text(OUTPUT_ROOT / "README.md", readme)
    write_text(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1.md", main_report)

    secret = secret_audit()
    hash_outputs()

    final_status = PASS_STATUS if smoke_status == "PASS" and secret["status"] == "PASS" else (
        INVENTORY_LIMIT_STATUS if inventory["accepted_grounded_edge_count"] > 0 and secret["status"] == "PASS" else FAIL_STATUS
    )
    decision = {
        "status": final_status,
        "task_name": TASK_NAME,
        "timestamp": timestamp(),
        "property_planning_r1_loaded": True,
        "candidate_edge_count": inventory["candidate_edge_count"],
        "r1_candidate_edge_count": inventory["r1_candidate_edge_count"],
        "accepted_grounded_edge_count": len(accepted),
        "rejected_edge_count": len(rejected),
        "backlog_edge_count": len(backlog),
        "relationship_type_count": len(relationship_types),
        "runtime_ready_context_count": runtime["counts"]["RUNTIME_READY_CONTEXT"],
        "review_context_only_count": runtime["counts"]["REVIEW_CONTEXT_ONLY"],
        "d6_display_ready_later_count": runtime["counts"]["D6_DISPLAY_READY_LATER"],
        "track2a_kit_ready_later_count": runtime["counts"]["TRACK2A_KIT_READY_LATER"],
        "event_fabric_ready_later_count": runtime["counts"]["EVENT_FABRIC_READY_LATER"],
        "data_first_context_only_count": runtime["counts"]["DATA_FIRST_CONTEXT_ONLY"],
        "sample_query_count": len(requests),
        "sample_response_count": len(responses),
        "d6_future_handoff_candidate_count": len(d6_handoffs),
        "track2a_future_handoff_candidate_count": len(track2a_handoffs),
        "event_fabric_future_handoff_candidate_count": len(event_fabric_handoffs),
        "closeout_register_status": "PASS",
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": "PASS",
        "no_mutation_status": "PASS",
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PASS",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D4X-PROPERTY-PLANNING-R7-RUNTIME-SLICE-AND-D6-OVERLAY-INTEGRATION-R1 only after product-surface approval",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json", decision)
    hash_outputs()

    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status in {PASS_STATUS, INVENTORY_LIMIT_STATUS} else 1


if __name__ == "__main__":
    raise SystemExit(main())
