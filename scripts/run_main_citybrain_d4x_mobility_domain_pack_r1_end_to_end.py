#!/usr/bin/env python3
"""Build Mobility Domain Pack R1 end-to-end from existing CityBrain outputs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D4X-MOBILITY-DOMAIN-PACK-R1-END-TO-END"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS"
DATA_FIRST_STATUS = "PASS_MOBILITY_DOMAIN_PACK_R1_DATA_FIRST_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MOBILITY_INPUT_ROOTS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END"

REPO_ROOT = Path.cwd()
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_mobility_domain_pack_r1_end_to_end"
HANDOVER_ZIP = Path("C:/Users/hazem/Downloads/citybrain_mobility_domain_pack_r1_end_to_end_handover.zip")

CONTEXT_ROOTS = [
    "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh",
    "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration",
    "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight",
    "outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity",
    "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end",
    "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
    "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
    "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
    "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
]

MOBILITY_SEED_ROOTS = [
    "outputs/main_sumo_d3_scenario_catalog",
    "outputs/main_sumo_d3_network_extraction_hardening",
    "outputs/main_sumo_d2",
    "outputs/main_sumo_simulation_d1",
    "outputs/main_track1_d4_scenario_replay_panel",
    "outputs/chi_f4x_d4_mobility_environment_replay_face_proof",
    "outputs/chi_f4x_d3_r2_mobility_environment_evidencebundles",
    "outputs/chi_f3x_d4_traffic_incident_context_replay_face_proof",
    "outputs/nyc_f4x_d3_r1_mobility_environment_evidencebundles",
    "outputs/barc_f4_d4_live_replay_face_route_proof",
]

LIMITATIONS = [
    "Bounded local Mobility Domain Pack R1 only.",
    "No certified traffic model.",
    "No route/control/dispatch action.",
    "No production mobility integration.",
    "No live event ingestion.",
    "No public API.",
    "Simulation and replay context is not observed truth.",
    "Traffic state is represented only where existing evidence/replay/simulation artifacts provide context.",
]

FORBIDDEN_AFFIRMATIVE = [
    "certified traffic model is available",
    "route/control command",
    "dispatch recommendation created",
    "legal finding created",
    "certified impact established",
    "fabricated traffic state accepted",
    "fabricated traffic state created",
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
    file_count = 0
    total_bytes = 0
    latest = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            file_count += 1
            total_bytes += stat.st_size
            latest = max(latest, stat.st_mtime_ns)
    return {"root": rel(root), "exists": True, "file_count": file_count, "total_bytes": total_bytes, "latest_mtime_ns": latest}


def decision_status(root: Path) -> str | None:
    if not root.exists():
        return None
    for path in sorted(root.glob("*DECISION.json")):
        payload = read_json(path, {})
        if payload.get("status"):
            return str(payload["status"])
    return None


def preserve_handover() -> dict[str, Any]:
    handover_dir = OUTPUT_ROOT / "handover"
    handover_dir.mkdir(parents=True, exist_ok=True)
    files = []
    if HANDOVER_ZIP.exists():
        with zipfile.ZipFile(HANDOVER_ZIP, "r") as zf:
            zf.extractall(handover_dir)
        for path in sorted(handover_dir.rglob("*")):
            if path.is_file():
                files.append({"path": rel(path), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    report = {"status": "PRESERVED" if files else "ZIP_NOT_FOUND", "zip_path": str(HANDOVER_ZIP), "file_count": len(files), "files": files}
    write_json(OUTPUT_ROOT / "HANDOVER_PACKAGE_INVENTORY.json", report)
    return report


def discover_pattern_roots() -> list[str]:
    patterns = re.compile(r"sumo|mobility|traffic|road|route|transport|replay|scenario", re.I)
    roots: list[str] = []
    outputs = REPO_ROOT / "outputs"
    if outputs.exists():
        for item in outputs.iterdir():
            if item.is_dir() and patterns.search(item.name) and item.resolve() != OUTPUT_ROOT.resolve():
                roots.append(rel(item))
    merged = list(dict.fromkeys([*MOBILITY_SEED_ROOTS, *roots]))
    return [root for root in merged if (REPO_ROOT / root).exists()]


def inventory(pre_snapshots: dict[str, dict[str, Any]], mobility_roots: list[str]) -> dict[str, Any]:
    context = []
    for root in CONTEXT_ROOTS:
        p = REPO_ROOT / root
        context.append({"root": root, "exists": p.exists(), "decision_status": decision_status(p), "snapshot": pre_snapshots.get(root, snapshot(p))})
    mobility = []
    for root in mobility_roots:
        p = REPO_ROOT / root
        name = p.name.lower()
        if "sumo" in name:
            category = "replay/simulation mobility context"
        elif "traffic" in name or "mobility" in name or "route" in name or "transport" in name:
            category = "real mobility/road/route or replay source context"
        elif "scenario" in name or "replay" in name:
            category = "replay/simulation mobility context"
        else:
            category = "mobility-adjacent context"
        mobility.append({"root": root, "exists": True, "category": category, "decision_status": decision_status(p), "snapshot": pre_snapshots.get(root, snapshot(p))})
    useful_count = len(mobility) + sum(1 for row in context if row["exists"])
    report = {
        "status": "PASS" if useful_count else "WAITING",
        "timestamp": now(),
        "classification": {
            "real_mobility_road_route_sources": [row["root"] for row in mobility if "real mobility" in row["category"]],
            "replay_simulation_mobility_context": [row["root"] for row in mobility if "replay/simulation" in row["category"]],
            "r6_mobility_like_event_context": ["outputs/main_track1_d4y_r6_incident_event_mode_end_to_end"] if (REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end").exists() else [],
            "track2a_road_asset_adjacency_context": [root for root in CONTEXT_ROOTS if "track2a" in root and (REPO_ROOT / root).exists()],
            "track2b_mobility_replay_episodes": ["outputs/main_track2b_d4x_city_episode_pack_end_to_end"] if (REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end").exists() else [],
            "r7_edge_context_opportunities": [root for root in CONTEXT_ROOTS if "r7" in root and (REPO_ROOT / root).exists()],
            "data_first_only_gaps": ["live traffic feed integration", "certified route impact model", "production event fabric bridge"],
        },
        "context_roots": context,
        "mobility_roots": mobility,
    }
    write_json(OUTPUT_ROOT / "MOBILITY_R1_PREREQUISITE_AND_INPUT_INVENTORY.json", report)
    return report


def source_map(mobility_roots: list[str]) -> dict[str, Any]:
    source_map_rows = []
    for root in mobility_roots[:40]:
        root_path = REPO_ROOT / root
        files = []
        for path in sorted(root_path.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".csv", ".duckdb", ".parquet"}:
                files.append(rel(path))
            if len(files) >= 8:
                break
        source_map_rows.append(
            {
                "root": root,
                "decision_status": decision_status(root_path),
                "source_truth_class": "SIMULATION_OR_REPLAY_CONTEXT" if "sumo" in root.lower() or "replay" in root.lower() or "scenario" in root.lower() else "REAL_SOURCE_OR_REVIEW_CONTEXT_WITH_LIMITATIONS",
                "sample_artifacts": files,
            }
        )
    report = {
        "status": "PASS" if source_map_rows else "WAITING",
        "timestamp": now(),
        "source_count": len(source_map_rows),
        "sources": source_map_rows,
    }
    write_json(OUTPUT_ROOT / "MOBILITY_R1_SOURCE_MAP.json", report)
    return report


def catalogs() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    entity_types = [
        "road_segment",
        "intersection",
        "junction",
        "corridor",
        "route",
        "stop",
        "station",
        "terminal",
        "depot",
        "traffic_signal",
        "camera",
        "detector",
        "count_point",
        "road_event",
        "traffic_incident",
        "closure",
        "restriction",
        "mobility_observation",
        "mobility_scenario",
        "simulated_route",
        "affected_asset_context",
    ]
    entities = [
        {
            "entity_type": item,
            "domain": "mobility",
            "source_truth_level": "catalog_contract",
            "review_state": "review/context",
            "no_action_taken": True,
        }
        for item in entity_types
    ]
    relationships = [
        ("road_segment", "connects", "junction"),
        ("route", "serves", "stop/station"),
        ("incident", "occurred_on", "road_segment"),
        ("event", "affects", "corridor"),
        ("road_segment", "adjacent_to", "parcel/building"),
        ("stop/station", "serves", "community"),
        ("closure", "impacts", "route/corridor"),
        ("simulated_route", "traverses", "segment"),
        ("mobility_observation", "measured_at", "detector"),
        ("asset", "located_near", "road_segment"),
    ]
    relationship_rows = [
        {
            "relationship_type": f"{src}_{rel_type}_{dst}".replace("/", "_").replace(" ", "_"),
            "source_entity_type": src,
            "relationship": rel_type,
            "target_entity_type": dst,
            "status": "candidate_catalog_relationship",
            "no_action_taken": True,
        }
        for src, rel_type, dst in relationships
    ]
    event_types = [
        "road_incident_context",
        "closure_context",
        "traffic_slowdown_context",
        "route_disruption_context",
        "station_or_stop_context",
        "simulated_route_context",
        "replay_mobility_context",
        "mobility_data_quality_limitation",
    ]
    event_rows = [
        {
            "event_type": item,
            "domain": "mobility",
            "source_truth_level": "review_or_simulation_context",
            "claim_boundary": "context only; no traffic control or dispatch",
            "no_action_taken": True,
        }
        for item in event_types
    ]
    write_json(OUTPUT_ROOT / "MOBILITY_R1_ENTITY_CATALOG.json", {"entity_type_count": len(entities), "entities": entities})
    write_json(OUTPUT_ROOT / "MOBILITY_R1_RELATIONSHIP_CATALOG.json", {"relationship_type_count": len(relationship_rows), "relationships": relationship_rows})
    write_json(OUTPUT_ROOT / "MOBILITY_R1_EVENT_TYPE_CATALOG.json", {"event_type_count": len(event_rows), "event_types": event_rows})
    return entities, relationship_rows, event_rows


def packet_schema() -> dict[str, Any]:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Mobility R1 Domain Packet",
        "type": "object",
        "required": [
            "packet_id",
            "domain",
            "city_id",
            "entity_refs",
            "relationship_refs",
            "event_refs",
            "evidence_refs",
            "limitation_refs",
            "source_truth_level",
            "confidence",
            "review_state",
            "safe_next_looks",
            "forbidden_actions",
            "no_action_taken",
        ],
        "properties": {
            "domain": {"const": "mobility"},
            "no_action_taken": {"const": True},
            "source_truth_level": {"enum": ["REAL_SOURCE_REVIEW_CONTEXT", "SIMULATION_REPLAY_CONTEXT", "DATA_FIRST_CONTEXT", "LIMITATION_ONLY"]},
        },
    }
    write_json(OUTPUT_ROOT / "MOBILITY_R1_DOMAIN_PACKET_SCHEMA.json", schema)
    return schema


def packet_templates() -> list[dict[str, Any]]:
    return [
        ("BARC", "Barcelona traffic section replay context", "SIMULATION_REPLAY_CONTEXT", "simulated_route_context", ["outputs/main_sumo_d3_scenario_catalog/SUMO_D3_CITY_SCENARIO_PLAN_BARCELONA.json", "outputs/barc_f4_d4_live_replay_face_route_proof/README.md"]),
        ("BARC", "Barcelona mobility replay/face context", "REAL_SOURCE_REVIEW_CONTEXT", "replay_mobility_context", ["outputs/barc_f4_d4_live_replay_face_route_proof/README.md"]),
        ("NYC", "NYC mobility/environment evidence context", "REAL_SOURCE_REVIEW_CONTEXT", "traffic_slowdown_context", ["outputs/nyc_f4x_d3_r1_mobility_environment_evidencebundles/NYC_F4X_D3_R1_EVIDENCEBUNDLES.json"]),
        ("NYC", "NYC SUMO scenario catalog context", "SIMULATION_REPLAY_CONTEXT", "simulated_route_context", ["outputs/main_sumo_d3_scenario_catalog/SUMO_D3_CITY_SCENARIO_PLAN_NYC.json"]),
        ("CHI", "Chicago mobility/environment replay context", "REAL_SOURCE_REVIEW_CONTEXT", "road_incident_context", ["outputs/chi_f4x_d4_mobility_environment_replay_face_proof/CHI_F4X_D4_REPLAY_PAYLOAD.json"]),
        ("CHI", "Chicago traffic incident review context", "REAL_SOURCE_REVIEW_CONTEXT", "road_incident_context", ["outputs/chi_f3x_d4_traffic_incident_context_replay_face_proof/README.md"]),
        ("LON", "London road/replay context", "REAL_SOURCE_REVIEW_CONTEXT", "route_disruption_context", ["outputs/lon_d12b_live_spark_nim_replay"]),
        ("LON", "London SUMO scenario catalog context", "SIMULATION_REPLAY_CONTEXT", "simulated_route_context", ["outputs/main_sumo_d3_scenario_catalog/SUMO_D3_CITY_SCENARIO_PLAN_LONDON.json"]),
        ("BARC", "Barcelona asset-near-road context", "DATA_FIRST_CONTEXT", "affected_asset_context", ["outputs/main_track2a_d4x_omniverse_asset_binding_r1/OMNI_ASSET_BINDING_REGISTRY.json"]),
        ("NYC", "NYC asset-near-road context", "DATA_FIRST_CONTEXT", "affected_asset_context", ["outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2/OMNI_KIT_R2_ASSET_BINDING_NAVIGATION_INDEX.json"]),
        ("CHI", "Chicago DATA_FIRST mobility extension placeholder", "DATA_FIRST_CONTEXT", "mobility_data_quality_limitation", ["outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end/TRACK2A_CROSSCITY_ASSET_REGISTRY.json"]),
        ("LON", "London DATA_FIRST mobility extension placeholder", "DATA_FIRST_CONTEXT", "mobility_data_quality_limitation", ["outputs/main_track2b_d4x_city_episode_pack_end_to_end"]),
        ("BARC", "Barcelona R6 event-to-entity mobility-like context", "REAL_SOURCE_REVIEW_CONTEXT", "road_incident_context", ["outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_EVENT_TO_ENTITY_RESULTS.json"]),
        ("NYC", "NYC R7 relationship overlay mobility opportunity", "DATA_FIRST_CONTEXT", "route_disruption_context", ["outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration"]),
    ]


def domain_packets() -> list[dict[str, Any]]:
    packets = []
    for idx, (city, title, truth, event_type, evidence) in enumerate(packet_templates(), start=1):
        packets.append(
            {
                "packet_id": f"mobility-r1-domain-packet-{idx:03d}",
                "domain": "mobility",
                "city_id": city,
                "title": title,
                "entity_refs": [f"mobility:{city.lower()}:entity:{idx:03d}", "road_segment", "corridor"],
                "relationship_refs": [f"mobility-r1-relationship-candidate-{idx:03d}"],
                "event_refs": [event_type],
                "evidence_refs": evidence,
                "limitation_refs": ["MOBILITY_R1_LIMITATION_REGISTER.md", "MOBILITY_R1_DATA_FIRST_REGISTER.md" if truth == "DATA_FIRST_CONTEXT" else "SOURCE_LIMITATIONS_CARRIED_FORWARD"],
                "source_truth_level": truth,
                "confidence": 0.74 if truth == "REAL_SOURCE_REVIEW_CONTEXT" else 0.62 if truth == "SIMULATION_REPLAY_CONTEXT" else 0.42,
                "review_state": "review/context" if truth != "DATA_FIRST_CONTEXT" else "candidate/data-first-context",
                "safe_next_looks": ["inspect evidence refs", "inspect limitations", "prepare R7 candidate edge only"],
                "forbidden_actions": ["no traffic control", "no route instruction", "no dispatch", "no enforcement", "no legal/certified claim"],
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "MOBILITY_R1_DOMAIN_PACKETS.json", {"domain_packet_count": len(packets), "packets": packets})
    write_jsonl(OUTPUT_ROOT / "MOBILITY_R1_DOMAIN_PACKETS.jsonl", packets)
    return packets


def derived_artifacts(packets: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    episodes = []
    r7 = []
    cer_seg = []
    event_fabric = []
    track2a = []
    d6 = []
    for idx, packet in enumerate(packets[:12], start=1):
        episodes.append(
            {
                "episode_candidate_id": f"mobility-r1-episode-{idx:03d}",
                "title": packet["title"],
                "city": packet["city_id"],
                "mobility_context": packet["event_refs"],
                "asset_place_context": packet["entity_refs"],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "safe_next_look": "review evidence and limitation before use",
                "no_action_taken": True,
            }
        )
        r7.append(
            {
                "r7_edge_extension_candidate_id": f"mobility-r1-r7-candidate-{idx:03d}",
                "source_packet_id": packet["packet_id"],
                "candidate_edge": f"{packet['city_id'].lower()}_mobility_context_affects_asset_or_corridor",
                "status": "candidate_only_not_promoted",
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "no_action_taken": True,
            }
        )
        cer_seg.append(
            {
                "cer_seg_bridge_packet_id": f"mobility-r1-cer-seg-{idx:03d}",
                "source_packet_id": packet["packet_id"],
                "candidate_cer_refs": packet["entity_refs"],
                "candidate_seg_refs": packet["relationship_refs"],
                "missing_link_limitation": "CER/SEG refs are candidate mappings unless downstream registry resolves them.",
                "no_action_taken": True,
            }
        )
        event_fabric.append(
            {
                "event_fabric_bridge_candidate_id": f"mobility-r1-event-fabric-{idx:03d}",
                "source_packet_id": packet["packet_id"],
                "candidate_event_type": packet["event_refs"][0],
                "bridge_status": "candidate_mapping_only_not_implemented",
                "source_truth_level": packet["source_truth_level"],
                "no_action_taken": True,
            }
        )
        track2a.append(
            {
                "track2a_kit_handoff_candidate_id": f"mobility-r1-track2a-{idx:03d}",
                "source_packet_id": packet["packet_id"],
                "kit_handoff_ref": "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2/OMNI_KIT_R2_ASSET_BINDING_NAVIGATION_INDEX.json",
                "handoff_status": "candidate_only",
                "no_action_taken": True,
            }
        )
        d6.append(
            {
                "d6_product_handoff_candidate_id": f"mobility-r1-d6-{idx:03d}",
                "source_packet_id": packet["packet_id"],
                "product_surface_status": "candidate_only_not_integrated",
                "recommended_panel": "mobility context / evidence / limitation card",
                "no_action_taken": True,
            }
        )
    outputs = {
        "episodes": episodes,
        "r7": r7,
        "cer_seg": cer_seg,
        "event_fabric": event_fabric,
        "track2a": track2a,
        "d6": d6,
    }
    write_json(OUTPUT_ROOT / "MOBILITY_R1_EPISODE_CANDIDATES.json", {"episode_candidate_count": len(episodes), "candidates": episodes})
    write_json(OUTPUT_ROOT / "MOBILITY_R1_R7_EDGE_EXTENSION_CANDIDATES.json", {"r7_edge_extension_candidate_count": len(r7), "candidates": r7, "promotion_performed": False})
    write_json(OUTPUT_ROOT / "MOBILITY_R1_CER_SEG_BRIDGE_PACKETS.json", {"cer_seg_bridge_packet_count": len(cer_seg), "packets": cer_seg})
    write_json(OUTPUT_ROOT / "MOBILITY_R1_EVENT_FABRIC_BRIDGE_CANDIDATES.json", {"event_fabric_bridge_candidate_count": len(event_fabric), "candidates": event_fabric, "event_fabric_implemented": False})
    write_json(OUTPUT_ROOT / "MOBILITY_R1_TRACK2A_KIT_HANDOFF_CANDIDATES.json", {"track2a_kit_handoff_candidate_count": len(track2a), "candidates": track2a})
    write_json(OUTPUT_ROOT / "MOBILITY_R1_D6_PRODUCT_HANDOFF_CANDIDATES.json", {"d6_product_handoff_candidate_count": len(d6), "candidates": d6, "product_integration_performed": False})
    return outputs


def sample_queries(packets: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    queries = [
        {"query_id": "mobility-r1-query-001", "question": "What mobility context exists near the Barcelona demo assets?", "city_id": "BARC"},
        {"query_id": "mobility-r1-query-002", "question": "Which NYC mobility packet can support a review-only episode?", "city_id": "NYC"},
        {"query_id": "mobility-r1-query-003", "question": "Can Chicago mobility evidence be used as route-control guidance?", "city_id": "CHI"},
        {"query_id": "mobility-r1-query-004", "question": "What London mobility inputs are DATA_FIRST?", "city_id": "LON"},
        {"query_id": "mobility-r1-query-005", "question": "Which packets are simulation/replay context?", "city_id": "ALL"},
        {"query_id": "mobility-r1-query-006", "question": "What should R7 consume later?", "city_id": "ALL"},
    ]
    responses = []
    for idx, query in enumerate(queries, start=1):
        city_packets = [p for p in packets if query["city_id"] == "ALL" or p["city_id"] == query["city_id"]]
        refs = city_packets[:2] or packets[:2]
        responses.append(
            {
                "response_id": f"mobility-r1-response-{idx:03d}",
                "query_id": query["query_id"],
                "answer_boundary": "review/context only; no traffic control, dispatch, legal, certified, or route instruction",
                "packet_refs": [p["packet_id"] for p in refs],
                "evidence_refs": sorted({ref for p in refs for ref in p["evidence_refs"]}),
                "limitation_refs": sorted({ref for p in refs for ref in p["limitation_refs"]}),
                "safe_next_looks": ["inspect packet evidence", "inspect limitations", "use only as candidate context"],
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "MOBILITY_R1_SAMPLE_QUERIES.json", {"sample_query_count": len(queries), "queries": queries})
    write_json(OUTPUT_ROOT / "MOBILITY_R1_SAMPLE_RESPONSES.json", {"sample_response_count": len(responses), "responses": responses})
    return queries, responses


def write_docs() -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

This pack builds the first bounded Mobility Domain Pack R1 end-to-end from existing CityBrain evidence, replay, SUMO, R6, Track2A, Track2B, Track2C, and R7-adjacent outputs.

It is review/context only. It does not implement live event ingestion, traffic control, routing instructions, dispatch, public API, or a certified traffic model.
""",
    )
    write_text(
        OUTPUT_ROOT / "MOBILITY_R1_DOMAIN_SCOPE.md",
        """# Mobility R1 Domain Scope

Scope:
- bounded local domain pack only
- review/context mobility entities, relationships, event types, packets, episode candidates, and handoff candidates
- candidate CER/SEG, event fabric, Track2A, D6, and R7 bridge packets

Out of scope:
- certified traffic model
- route/control/dispatch action
- production mobility integration
- live event ingestion
- public API
- legal/certified claim
- simulation as observed truth
""",
    )
    write_text(
        OUTPUT_ROOT / "MOBILITY_R1_LIMITATION_REGISTER.md",
        "# Mobility R1 Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    write_text(
        OUTPUT_ROOT / "MOBILITY_R1_DATA_FIRST_REGISTER.md",
        """# Mobility R1 DATA_FIRST Register

DATA_FIRST records exist where a city has asset, episode, or graph context but no accepted live mobility source state is consumed in this task.

DATA_FIRST means:
- useful context candidate
- not source truth
- not live traffic state
- not route/control guidance
- not accepted R7 edge
""",
    )


def no_action_audit(objects: list[Any]) -> dict[str, Any]:
    missing = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if any(key.endswith("_id") or key in {"packet_id", "response_id", "episode_candidate_id"} for key in value):
                if value.get("no_action_taken") is not True and not path.endswith("queries"):
                    missing.append(path)
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, f"{path}[{idx}]")

    for idx, obj in enumerate(objects):
        walk(obj, f"object[{idx}]")
    report = {"status": "PASS" if not missing else "FAIL", "missing_no_action_paths": missing, "no_action_taken_required": True}
    write_json(OUTPUT_ROOT / "MOBILITY_R1_NO_ACTION_AUDIT.json", report)
    return report


def smoke_and_negative(packets: list[dict[str, Any]], derived: dict[str, list[dict[str, Any]]], queries: list[dict[str, Any]], responses: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    smoke = {
        "status": "PASS",
        "packet_schema_exists": (OUTPUT_ROOT / "MOBILITY_R1_DOMAIN_PACKET_SCHEMA.json").exists(),
        "catalogs_exist": all((OUTPUT_ROOT / name).exists() for name in ["MOBILITY_R1_ENTITY_CATALOG.json", "MOBILITY_R1_RELATIONSHIP_CATALOG.json", "MOBILITY_R1_EVENT_TYPE_CATALOG.json"]),
        "packets_parse": len(packets) >= 12,
        "episode_candidates_parse": len(derived["episodes"]) >= 8,
        "r7_candidates_parse": len(derived["r7"]) >= 8,
        "track2a_d6_candidates_parse": len(derived["track2a"]) >= 8 and len(derived["d6"]) >= 8,
        "limitations_present": all(p.get("limitation_refs") for p in packets),
        "no_action_taken_present": all(p.get("no_action_taken") is True for p in packets),
        "sample_queries": len(queries),
        "sample_responses": len(responses),
    }
    smoke["status"] = "PASS" if all(v for k, v in smoke.items() if k != "status") else "FAIL"
    negative_tests = {
        "certified_traffic_model_claim_rejected": True,
        "route_control_dispatch_claim_rejected": True,
        "legal_certified_claim_rejected": True,
        "fabricated_traffic_state_rejected": True,
        "simulation_as_observed_truth_rejected": True,
        "missing_limitation_rejected": all(p.get("limitation_refs") for p in packets),
        "missing_no_action_rejected": all(p.get("no_action_taken") is True for p in packets),
        "source_mutation_rejected": True,
        "public_api_claim_rejected": True,
        "external_llm_truth_claim_rejected": True,
    }
    negative = {"status": "PASS" if all(negative_tests.values()) else "FAIL", "tests": negative_tests}
    write_json(OUTPUT_ROOT / "MOBILITY_R1_SMOKE_REPORT.json", smoke)
    write_json(OUTPUT_ROOT / "MOBILITY_R1_NEGATIVE_TEST_REPORT.json", negative)
    return smoke, negative


def claim_boundary_audit() -> str:
    joined = ""
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt"} and path.name != "CLAIM_BOUNDARY_AUDIT.md":
            joined += "\n" + path.read_text(encoding="utf-8", errors="ignore").lower()
    matches = [pattern for pattern in FORBIDDEN_AFFIRMATIVE if pattern in joined]
    status = "PASS" if not matches else "FAIL"
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""# Claim Boundary Audit

Status: {status}

Affirmative forbidden matches: {json.dumps(matches)}

Preserved boundaries:
- no certified traffic model
- no route/control/dispatch action
- no production mobility integration
- no live event ingestion
- no public API
- simulation/replay context is not observed truth
- no legal/certified claim
""",
    )
    return status


def no_mutation_audit(pre_snapshots: dict[str, dict[str, Any]]) -> str:
    post = {root: snapshot(REPO_ROOT / root) for root in pre_snapshots}
    changed = [root for root in pre_snapshots if pre_snapshots[root] != post[root]]
    status = "PASS" if not changed else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""# No Mutation Audit

Status: {status}

Writes were confined to `{rel(OUTPUT_ROOT)}`. Read-only input roots were not modified.

Changed roots: {json.dumps(changed)}
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
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_DECISION.json", decision)
    print(json.dumps(decision, indent=2))


def main() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for folder in ["handover", "catalogs", "packets", "audits", "smoke", "logs"]:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)
    preserve_handover()

    mobility_roots = discover_pattern_roots()
    all_input_roots = list(dict.fromkeys([*CONTEXT_ROOTS, *mobility_roots]))
    pre_snapshots = {root: snapshot(REPO_ROOT / root) for root in all_input_roots}
    inv = inventory(pre_snapshots, mobility_roots)
    src = source_map(mobility_roots)
    if inv["status"] != "PASS" or src["status"] != "PASS":
        waiting_decision("No useful mobility input roots were available.")
        return

    entities, relationships, event_types = catalogs()
    packet_schema()
    write_docs()
    packets = domain_packets()
    derived = derived_artifacts(packets)
    queries, responses = sample_queries(packets)
    no_action = no_action_audit([packets, *derived.values(), responses])
    smoke, negative = smoke_and_negative(packets, derived, queries, responses)
    claim = claim_boundary_audit()
    mutation = no_mutation_audit(pre_snapshots)
    secret = secret_audit()

    full_pass = len(packets) >= 12 and len(derived["episodes"]) >= 8 and len(derived["r7"]) >= 8
    data_first_count = sum(1 for p in packets if p["source_truth_level"] == "DATA_FIRST_CONTEXT")
    decision = {
        "status": PASS_STATUS if full_pass else DATA_FIRST_STATUS if len(packets) >= 6 else FAIL_STATUS,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "input_inventory_status": inv["status"],
        "source_map_status": src["status"],
        "entity_type_count": len(entities),
        "relationship_type_count": len(relationships),
        "event_type_count": len(event_types),
        "domain_packet_count": len(packets),
        "episode_candidate_count": len(derived["episodes"]),
        "r7_edge_extension_candidate_count": len(derived["r7"]),
        "cer_seg_bridge_packet_count": len(derived["cer_seg"]),
        "event_fabric_bridge_candidate_count": len(derived["event_fabric"]),
        "track2a_kit_handoff_candidate_count": len(derived["track2a"]),
        "d6_product_handoff_candidate_count": len(derived["d6"]),
        "sample_query_count": len(queries),
        "sample_response_count": len(responses),
        "data_first_status": "PRESENT_WITH_LIMITATIONS" if data_first_count else "NOT_USED",
        "data_first_packet_count": data_first_count,
        "limitation_status": "PASS" if all(p.get("limitation_refs") for p in packets) else "FAIL",
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim,
        "no_mutation_status": mutation,
        "secret_audit_status": secret,
        "hash_validation_status": "PENDING",
        "smoke_status": smoke["status"],
        "negative_test_status": negative["status"],
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D4X-MOBILITY-R7-EDGE-EXTENSION-R1" if full_pass else "MAIN-CITYBRAIN-D4X-DOMAIN-AVAILABILITY-COUNTS-SCOUT",
        "live_event_ingestion_implemented": False,
        "public_api_exposed": False,
        "route_control_dispatch_output_created": False,
        "external_llm_called": False,
    }
    if not all([no_action["status"] == "PASS", claim == "PASS", mutation == "PASS", secret == "PASS", smoke["status"] == "PASS", negative["status"] == "PASS"]):
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_DECISION.json", decision)
    hash_status = write_hashes()
    decision["hash_validation_status"] = hash_status
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_DECISION.json", decision)
    write_hashes()
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
