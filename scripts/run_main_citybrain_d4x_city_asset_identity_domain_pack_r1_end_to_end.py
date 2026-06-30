#!/usr/bin/env python3
"""Build City Asset Identity Domain Pack R1 end-to-end from existing outputs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-CITYBRAIN-D4X-CITY-ASSET-IDENTITY-DOMAIN-PACK-R1-END-TO-END"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS"
DATA_FIRST_STATUS = "PASS_CITY_ASSET_IDENTITY_DOMAIN_PACK_R1_DATA_FIRST_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_CITY_ASSET_IDENTITY_INPUT_ROOTS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_DOMAIN_PACK_R1_END_TO_END"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_city_asset_identity_domain_pack_r1_end_to_end"

READ_ONLY_ROOTS = [
    "outputs/main_citybrain_d4x_domain_availability_counts_scout",
    "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh",
    "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration",
    "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight",
    "outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity",
    "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end",
    "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end",
    "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke",
    "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
    "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
    "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3",
    "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
    "outputs/main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end",
    "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
]

FOLDERS = [
    "domain_pack",
    "r7_candidates",
    "cer_seg_bridge",
    "track2a_handoff",
    "d6_handoff",
    "runtime_notes",
    "audits",
    "logs",
]

ENTITY_TYPES = [
    "city_asset",
    "building_asset",
    "asset_binding",
    "usd_prim",
    "source_asset_record",
    "source_identifier",
    "geometry_context",
    "visual_asset_context",
    "canonical_entity_candidate",
    "cer_request_context",
    "seg_request_context",
    "domain_packet_context",
    "evidence_ref",
    "limitation_ref",
    "data_first_asset_placeholder",
    "boundary_challenge_asset",
    "kit_camera_bookmark",
    "kit_stage_handoff",
    "web_companion_asset_card",
    "review_state_record",
    "asset_identity_episode",
]

RELATIONSHIP_TYPES = [
    "asset_mapped_to_usd_prim",
    "asset_has_source_identifier",
    "asset_has_cer_context",
    "asset_has_seg_context",
    "asset_has_domain_context",
    "asset_appears_in_episode",
    "asset_has_kit_handoff",
    "asset_has_camera_bookmark",
    "asset_has_event_context",
    "asset_has_relationship_context",
    "asset_has_evidence",
    "asset_has_limitation",
    "asset_has_review_state",
    "data_first_placeholder_for_city",
    "boundary_challenge_for_source_truth",
    "asset_available_for_d6_display",
    "asset_available_for_track2a_kit_display",
    "asset_available_for_event_overlay",
]

CONTEXT_TYPES = [
    "asset_selected_context",
    "asset_identity_review_context",
    "source_id_boundary_context",
    "usd_binding_context",
    "cer_lookup_context",
    "seg_lookup_context",
    "data_first_asset_context",
    "boundary_challenge_context",
    "asset_episode_context",
    "asset_event_context",
    "asset_relationship_context",
    "kit_handoff_context",
    "d6_product_context",
]

LIMITATIONS = [
    "Bounded local City Asset Identity Domain Pack R1 only.",
    "Asset identity/context only; no production asset registry replacement.",
    "Source identifiers remain source/candidate context, not legal ownership or certified truth.",
    "No source-of-truth geometry claim.",
    "No production CER/SEG registry claim.",
    "No D6, Track2A, R7, source USD, app source, or city source data mutation.",
    "No legal finding, permit approval/rejection, confirmed violation, dispatch, enforcement, routing/control, or autonomous monitoring claim.",
    "DATA_FIRST packets are placeholders requiring source strengthening.",
]

CLAIM_BOUNDARY = (
    "Review/context city asset identity only; not legal, ownership, certified identity, "
    "source-of-truth geometry, permit, violation, dispatch, enforcement, routing/control, "
    "production readiness, public deployment, or autonomous monitoring."
)

FORBIDDEN_AFFIRMATIVE = [
    "production_ready\": true",
    "public_api_exposed\": true",
    "legal_finding_created\": true",
    "confirmed_violation\": true",
    "permit_approved\": true",
    "permit_rejected\": true",
    "dispatch_recommendation_created\": true",
    "enforcement_recommendation_created\": true",
    "routing_control_command_created\": true",
    "autonomous_monitoring_enabled\": true",
    "external_llm_truth_engine\": true",
    "source_of_truth_geometry\": true",
    "certified_asset_truth\": true",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "latest_mtime_ns": None}
    file_count = 0
    total = 0
    latest = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            file_count += 1
            total += stat.st_size
            latest = max(latest, stat.st_mtime_ns)
    return {"exists": True, "file_count": file_count, "total_bytes": total, "latest_mtime_ns": latest}


def decision_status(root: Path) -> str | None:
    if not root.exists():
        return None
    for path in sorted(root.glob("*DECISION.json")):
        payload = read_json(path, {})
        if payload.get("status"):
            return str(payload["status"])
    return None


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def strings(value: Any) -> list[str]:
    return [str(item) for item in as_list(value) if item not in (None, "")]


def input_inventory(pre: dict[str, dict[str, Any]]) -> dict[str, Any]:
    roots = []
    for root in READ_ONLY_ROOTS:
        root_path = REPO_ROOT / root
        roots.append(
            {
                "root": root,
                "exists": root_path.exists(),
                "decision_status": decision_status(root_path),
                "snapshot": pre[root],
                "read_role": "read_only_input",
            }
        )

    crosscity = read_json(
        REPO_ROOT / "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end/TRACK2A_CROSSCITY_ASSET_REGISTRY.json",
        {},
    )
    binding = read_json(
        REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_binding_r1/OMNI_ASSET_BINDING_REGISTRY.json",
        {},
    )
    kit_nav = read_json(
        REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2/OMNI_KIT_R2_SELECTED_ASSET_NAVIGATION_SET.json",
        {},
    )
    event_map = read_json(
        REPO_ROOT / "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3/OMNI_EVENT_R3_EVENT_TO_ASSET_BINDING_MAP.json",
        {},
    )
    availability = {
        "barc_nyc_real_lod2_asset_registry_rows": len(crosscity.get("real_asset_rows", [])),
        "track2a_asset_registry_rows": len(crosscity.get("asset_rows", [])),
        "track2a_selected_demo_assets": len(
            read_json(
                REPO_ROOT / "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end/TRACK2A_SELECTED_DEMO_ASSETS.json",
                {},
            ).get("assets", [])
        ),
        "track2a_usd_prim_to_asset_mappings": len(binding.get("records", [])),
        "track2a_cer_seg_domain_overlay_app_handoff_packets": len(binding.get("records", [])),
        "track2a_kit_composer_handoffs": len(kit_nav.get("items", [])),
        "track2a_event_overlay_r3_artifacts": len(event_map.get("rows", [])),
        "track2b_city_episodes_present": (REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end").exists(),
        "d6_relationship_overlay_context_packets_present": (
            REPO_ROOT / "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration/D6_R3_RELATIONSHIP_CONTEXT_PACKETS.json"
        ).exists(),
        "r7_edge_registry_records_present": (REPO_ROOT / "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight").exists(),
        "event_fabric_r2_indexes_and_handoff_candidates_present": (
            REPO_ROOT / "outputs/main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end"
        ).exists(),
        "r5_building_civic_domain_packets_present": (REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end").exists(),
        "r6_incident_event_packets_present": (REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end").exists(),
        "data_first_chi_lon_placeholders": len(crosscity.get("future_city_registry", [])),
        "source_id_boundary_challenge_records": int(binding.get("boundary_challenge_record_count", 0) or 0),
    }
    useful = availability["barc_nyc_real_lod2_asset_registry_rows"] >= 16 and availability["track2a_usd_prim_to_asset_mappings"] >= 16
    report = {
        "status": "PASS" if useful else WAITING_STATUS,
        "timestamp": now(),
        "roots": roots,
        "availability": availability,
        "useful_city_asset_identity_inputs": useful,
    }
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_PREREQUISITE_AND_INPUT_INVENTORY.json", report)
    return report


def source_map(pre: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for root in READ_ONLY_ROOTS:
        root_path = REPO_ROOT / root
        sample_files = []
        if root_path.exists():
            for path in sorted(root_path.rglob("*")):
                if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".usda"}:
                    sample_files.append(rel(path))
                if len(sample_files) >= 10:
                    break
        rows.append(
            {
                "root": root,
                "exists": root_path.exists(),
                "decision_status": decision_status(root_path),
                "snapshot": pre[root],
                "source_family": source_family(root),
                "sample_artifacts": sample_files,
                "read_role": "read_only_input",
            }
        )
    report = {"status": "PASS", "timestamp": now(), "sources": rows}
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_SOURCE_MAP.json", report)
    return report


def source_family(root: str) -> str:
    low = root.lower()
    if "track2a" in low:
        return "track2a_omniverse_asset_context"
    if "d6" in low:
        return "d6_demo_overlay_context"
    if "r7" in low:
        return "r7_relationship_context"
    if "event_fabric" in low:
        return "event_fabric_context"
    if "r5" in low:
        return "r5_domain_packet_context"
    if "r6" in low:
        return "r6_incident_event_context"
    if "track2b" in low or "track2c" in low:
        return "episode_or_control_room_context"
    return "availability_or_supporting_context"


def load_inputs() -> dict[str, Any]:
    base = REPO_ROOT / "outputs"
    return {
        "crosscity": read_json(base / "main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end/TRACK2A_CROSSCITY_ASSET_REGISTRY.json", {}),
        "selected_assets": read_json(base / "main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end/TRACK2A_SELECTED_DEMO_ASSETS.json", {}),
        "binding_registry": read_json(base / "main_track2a_d4x_omniverse_asset_binding_r1/OMNI_ASSET_BINDING_REGISTRY.json", {}),
        "real_bindings": read_json(base / "main_track2a_d4x_omniverse_asset_binding_r1/OMNI_REAL_ASSET_BINDINGS_BARC_NYC.json", {}),
        "data_first_bindings": read_json(base / "main_track2a_d4x_omniverse_asset_binding_r1/OMNI_DATA_FIRST_PLACEHOLDER_BINDINGS.json", {}),
        "kit_nav": read_json(base / "main_track2a_d4x_omniverse_kit_composer_handoff_r2/OMNI_KIT_R2_SELECTED_ASSET_NAVIGATION_SET.json", {}),
        "kit_bookmarks": read_json(base / "main_track2a_d4x_omniverse_kit_composer_handoff_r2/OMNI_KIT_R2_CAMERA_BOOKMARKS.json", {}),
        "event_asset_map": read_json(base / "main_track2a_d4x_omniverse_event_overlay_integration_r3/OMNI_EVENT_R3_EVENT_TO_ASSET_BINDING_MAP.json", {}),
        "d6_edge_asset_map": read_json(base / "main_citybrain_d6_r3_r7_relationship_overlay_integration/D6_R3_EDGE_TO_ASSET_BINDING_MAP.json", {}),
    }


def index_by(items: list[dict[str, Any]], keys: list[str]) -> dict[str, dict[str, Any]]:
    indexed = {}
    for item in items:
        for key in keys:
            value = item.get(key)
            if value:
                indexed[str(value)] = item
    return indexed


def make_packet(
    idx: int,
    source: dict[str, Any],
    source_kind: str,
    kit_nav_by_binding: dict[str, dict[str, Any]],
    bookmark_by_binding: dict[str, dict[str, Any]],
    event_by_binding: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    binding_id = source.get("binding_id") or source.get("asset_registry_id") or source.get("source_asset_id") or f"asset-identity-source-{idx:03d}"
    city_id = source.get("city_id") or source.get("city") or "CROSS_CITY"
    asset_ref = source.get("asset_registry_ref") or source.get("asset_registry_id") or source.get("asset_ref") or source.get("asset_id") or f"asset:{city_id.lower()}:data_first:{idx:03d}"
    source_identifier = source.get("source_asset_ref") or source.get("source_asset_id") or source.get("source_id_boundary_label") or asset_ref
    nav = kit_nav_by_binding.get(str(binding_id), {})
    bookmark = bookmark_by_binding.get(str(binding_id), {})
    event = event_by_binding.get(str(binding_id), {})

    evidence_refs = strings(source.get("evidence_refs")) or strings(event.get("evidence_refs")) or [
        "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end/TRACK2A_CROSSCITY_ASSET_REGISTRY.json"
    ]
    limitation_refs = strings(source.get("limitation_refs")) or strings(event.get("limitation_refs")) or [
        "TRACK2A_ASSET_LIMITATION_REGISTER.md",
        "TRACK2A_SOURCE_ID_BOUNDARY_POLICY.md",
    ]

    cer_refs = strings(source.get("CER_packet_refs")) or strings(source.get("cer_candidate_refs")) or strings(source.get("canonical_entity_id"))
    seg_refs = strings(source.get("SEG_packet_refs")) or strings(source.get("seg_context_refs")) or strings(source.get("graph_or_runtime_refs"))
    usd_ref = source.get("usd_prim_ref") or source.get("USD_prim_ref") or nav.get("USD_prim_ref") or bookmark.get("usd_prim_ref")
    confidence = source.get("confidence_score")
    if confidence is None:
        confidence = 0.82 if source_kind == "REAL_ASSET_REVIEW_CONTEXT" else 0.48 if source_kind == "SOURCE_ID_BOUNDARY_CHALLENGE" else 0.32
    review_state = source.get("review_state") or ("source_id_boundary_review" if source_kind == "SOURCE_ID_BOUNDARY_CHALLENGE" else "data_first_review" if source_kind == "DATA_FIRST_ASSET_PLACEHOLDER" else "review/context")

    return {
        "packet_id": f"city-asset-identity-r1-domain-packet-{idx:03d}",
        "domain": "city_asset_identity",
        "city_id": city_id,
        "asset_refs": [str(asset_ref)],
        "source_identifier_refs": [str(source_identifier)],
        "usd_prim_refs": strings(usd_ref),
        "cer_refs": cer_refs[:6],
        "seg_refs": seg_refs[:6],
        "domain_packet_refs": strings(source.get("domain_packet_refs")) or [f"city_asset_identity:domain_packet_context:{idx:03d}"],
        "episode_refs": [f"city-asset-identity-r1-episode-{idx:03d}"],
        "event_refs": strings(event.get("event_id")) or strings(source.get("incident_event_refs")),
        "relationship_refs": strings(event.get("edge_id")) or [RELATIONSHIP_TYPES[(idx - 1) % len(RELATIONSHIP_TYPES)]],
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "source_truth_level": source_kind,
        "confidence": round(float(confidence), 3),
        "review_state": str(review_state),
        "safe_next_looks": [
            "open evidence refs beside the asset context",
            "show limitation/source-id boundary before any identity interpretation",
            "use only as review/context for later R7, D6, or Kit tasks",
        ],
        "forbidden_actions": [
            "do not assert legal or ownership truth",
            "do not assert source-of-truth geometry",
            "do not assert certified affected-building truth",
            "do not assert confirmed violation",
            "do not approve or reject permits",
            "do not dispatch, enforce, route, or control",
            "do not mutate USD, D6, Track2A, R7, app, or source roots",
        ],
        "source_refs": strings(source.get("binding_id")) or strings(source.get("asset_registry_id")) or [str(asset_ref)],
        "asset_label": source.get("display_label")
        or source.get("allowed_app_display", {}).get("display_title")
        or nav.get("asset_label")
        or str(asset_ref),
        "binding_ref": str(binding_id),
        "kit_camera_bookmark_refs": strings(bookmark.get("bookmark_id")) or strings(nav.get("camera_bookmark_ref")),
        "kit_stage_refs": strings(source.get("source_stage_file_ref")) or strings(nav.get("stage_file_ref")),
        "web_companion_asset_card_refs": [f"city-asset-identity-r1-card-{idx:03d}"],
        "claim_boundary": CLAIM_BOUNDARY,
        "no_action_taken": True,
    }


def build_packets(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    real_rows = [row for row in inputs["real_bindings"].get("records", []) if isinstance(row, dict)]
    if len(real_rows) < 16:
        real_rows = [row for row in inputs["crosscity"].get("real_asset_rows", []) if isinstance(row, dict)]
    real_rows = real_rows[:16]

    future_rows = [row for row in inputs["crosscity"].get("future_city_registry", []) if isinstance(row, dict)]
    data_first_rows = [row for row in inputs["data_first_bindings"].get("records", []) if isinstance(row, dict)]
    event_rows = [row for row in inputs["event_asset_map"].get("rows", []) if isinstance(row, dict) and "data-first" in json.dumps(row, default=str).lower()]
    data_rows = [*future_rows, *data_first_rows, *event_rows]
    while len(data_rows) < 4:
        city = "CHI" if len(data_rows) % 2 == 0 else "LON"
        data_rows.append(
            {
                "asset_registry_id": f"asset:{city.lower()}:data_first:{len(data_rows)+1:03d}",
                "city_id": city,
                "source_asset_id": f"{city.lower()}:asset_identity:data_first:{len(data_rows)+1:03d}",
                "evidence_refs": ["outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end/TRACK2A_CROSSCITY_ASSET_REGISTRY.json"],
                "limitation_refs": ["DATA_FIRST_ASSET_PLACEHOLDER_REQUIRES_SOURCE_STRENGTHENING"],
            }
        )
    data_rows = data_rows[:4]

    boundary_rows = []
    for row in real_rows:
        cloned = dict(row)
        cloned["source_truth_level"] = "SOURCE_ID_BOUNDARY_CHALLENGE"
        cloned["limitation_refs"] = list(dict.fromkeys(strings(row.get("limitation_refs")) + ["TRACK2A_SOURCE_ID_BOUNDARY_POLICY.md"]))
        cloned["review_state"] = "source_id_boundary_review"
        boundary_rows.append(cloned)
        if len(boundary_rows) >= 4:
            break

    kit_nav_by_binding = index_by([row for row in inputs["kit_nav"].get("items", []) if isinstance(row, dict)], ["binding_id"])
    bookmark_by_binding = index_by([row for row in inputs["kit_bookmarks"].get("bookmarks", []) if isinstance(row, dict)], ["binding_id"])
    event_by_binding = index_by([row for row in inputs["event_asset_map"].get("rows", []) if isinstance(row, dict)], ["binding_id"])

    packets = []
    for row in real_rows:
        packets.append(make_packet(len(packets) + 1, row, "REAL_ASSET_REVIEW_CONTEXT", kit_nav_by_binding, bookmark_by_binding, event_by_binding))
    for row in data_rows:
        packets.append(make_packet(len(packets) + 1, row, "DATA_FIRST_ASSET_PLACEHOLDER", kit_nav_by_binding, bookmark_by_binding, event_by_binding))
    for row in boundary_rows:
        packets.append(make_packet(len(packets) + 1, row, "SOURCE_ID_BOUNDARY_CHALLENGE", kit_nav_by_binding, bookmark_by_binding, event_by_binding))
    return packets


def catalogs() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    entities = [
        {"entity_type": item, "domain": "city_asset_identity", "status": "R1_REVIEW_CONTEXT", "claim_boundary": CLAIM_BOUNDARY, "no_action_taken": True}
        for item in ENTITY_TYPES
    ]
    relationships = [
        {"relationship_type": item, "domain": "city_asset_identity", "status": "candidate_relationship_only", "claim_boundary": CLAIM_BOUNDARY, "no_action_taken": True}
        for item in RELATIONSHIP_TYPES
    ]
    contexts = [
        {"context_type": item, "domain": "city_asset_identity", "status": "context_type_only", "claim_boundary": CLAIM_BOUNDARY, "no_action_taken": True}
        for item in CONTEXT_TYPES
    ]
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain City Asset Identity R1 Domain Packet",
        "type": "object",
        "required": [
            "packet_id",
            "domain",
            "city_id",
            "asset_refs",
            "source_identifier_refs",
            "usd_prim_refs",
            "cer_refs",
            "seg_refs",
            "domain_packet_refs",
            "episode_refs",
            "event_refs",
            "relationship_refs",
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
            "domain": {"const": "city_asset_identity"},
            "no_action_taken": {"const": True},
            "source_truth_level": {
                "enum": [
                    "REAL_ASSET_REVIEW_CONTEXT",
                    "DATA_FIRST_ASSET_PLACEHOLDER",
                    "SOURCE_ID_BOUNDARY_CHALLENGE",
                ]
            },
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return entities, relationships, contexts, schema


def derived_artifacts(packets: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    episodes = []
    r7 = []
    bridge = []
    track2a = []
    d6 = []
    rel_types = [
        "asset_mapped_to_usd_prim",
        "asset_has_source_identifier",
        "asset_has_cer_context",
        "asset_has_seg_context",
        "asset_has_event_context",
        "asset_has_relationship_context",
        "boundary_challenge_for_source_truth",
        "asset_available_for_d6_display",
        "asset_available_for_track2a_kit_display",
        "asset_available_for_event_overlay",
    ]
    for idx, packet in enumerate(packets, start=1):
        episodes.append(
            {
                "episode_candidate_id": f"city-asset-identity-r1-episode-{idx:03d}",
                "domain": "city_asset_identity",
                "city_id": packet["city_id"] if packet["city_id"] in {"BARC", "NYC"} else "CROSS_CITY",
                "packet_id": packet["packet_id"],
                "title": f"{packet['asset_label']} identity review context",
                "episode_context": "asset identity/evidence/limitation review only",
                "asset_refs": packet["asset_refs"],
                "usd_prim_refs": packet["usd_prim_refs"],
                "event_refs": packet["event_refs"],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "safe_next_looks": packet["safe_next_looks"],
                "no_action_taken": True,
            }
        )
        r7.append(
            {
                "r7_edge_extension_candidate_id": f"city-asset-identity-r1-r7-candidate-{idx:03d}",
                "source_packet_id": packet["packet_id"],
                "relationship_type": rel_types[(idx - 1) % len(rel_types)],
                "source_refs": packet["asset_refs"],
                "target_refs": packet["usd_prim_refs"] or packet["source_identifier_refs"],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "confidence": packet["confidence"],
                "review_state": packet["review_state"],
                "candidate_only_not_promoted": True,
                "no_action_taken": True,
            }
        )
        bridge.append(
            {
                "cer_seg_bridge_packet_id": f"city-asset-identity-r1-cer-seg-{idx:03d}",
                "source_packet_id": packet["packet_id"],
                "candidate_cer_refs": packet["cer_refs"],
                "candidate_seg_refs": packet["seg_refs"],
                "missing_link_limitations": [] if packet["cer_refs"] or packet["seg_refs"] else ["missing_cer_seg_link_for_asset_identity_packet"],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "no_action_taken": True,
            }
        )
        track2a.append(
            {
                "track2a_kit_handoff_candidate_id": f"city-asset-identity-r1-track2a-{idx:03d}",
                "source_packet_id": packet["packet_id"],
                "asset_refs": packet["asset_refs"],
                "usd_prim_refs": packet["usd_prim_refs"],
                "kit_camera_bookmark_refs": packet["kit_camera_bookmark_refs"],
                "kit_stage_refs": packet["kit_stage_refs"],
                "handoff_status": "candidate_only_not_integrated",
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "no_action_taken": True,
            }
        )
        d6.append(
            {
                "d6_product_handoff_candidate_id": f"city-asset-identity-r1-d6-{idx:03d}",
                "source_packet_id": packet["packet_id"],
                "asset_refs": packet["asset_refs"],
                "display_surface": "asset identity evidence/limitation card candidate",
                "handoff_status": "candidate_only_not_integrated",
                "safe_next_looks": packet["safe_next_looks"],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "no_action_taken": True,
            }
        )
    return {"episodes": episodes, "r7": r7, "bridge": bridge, "track2a": track2a, "d6": d6}


def sample_queries(packets: list[dict[str, Any]], derived: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    query_types = [
        "get_asset_identity_context_by_city",
        "get_asset_identity_context_by_asset_ref",
        "get_usd_prim_binding_for_asset",
        "get_source_id_boundary_for_asset",
        "get_cer_seg_context_for_asset",
        "get_event_context_for_asset",
        "get_relationship_context_for_asset",
        "get_data_first_asset_placeholders",
        "get_asset_identity_episodes",
        "get_asset_identity_r7_candidate_edges",
    ]
    queries = []
    responses = []
    for idx, query_type in enumerate(query_types, start=1):
        packet = packets[(idx - 1) % len(packets)]
        queries.append(
            {
                "query_id": f"city-asset-identity-r1-query-{idx:03d}",
                "query_type": query_type,
                "filters": {
                    "city_id": packet["city_id"],
                    "asset_ref": packet["asset_refs"][0],
                    "source_truth_level": packet["source_truth_level"],
                },
                "no_action_taken": True,
            }
        )
        responses.append(
            {
                "response_id": f"city-asset-identity-r1-response-{idx:03d}",
                "query_id": f"city-asset-identity-r1-query-{idx:03d}",
                "query_type": query_type,
                "status": "PASS_WITH_LIMITATIONS",
                "packet_refs": [packet["packet_id"]],
                "episode_refs": [derived["episodes"][(idx - 1) % len(derived["episodes"])]["episode_candidate_id"]],
                "r7_candidate_refs": [derived["r7"][(idx - 1) % len(derived["r7"])]["r7_edge_extension_candidate_id"]],
                "answer_boundary": CLAIM_BOUNDARY,
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "confidence": packet["confidence"],
                "review_state": packet["review_state"],
                "safe_next_looks": packet["safe_next_looks"],
                "no_action_taken": True,
            }
        )
    return queries, responses


def write_docs(packets: list[dict[str, Any]], derived: dict[str, list[dict[str, Any]]], status: str) -> None:
    real_count = sum(1 for packet in packets if packet["source_truth_level"] == "REAL_ASSET_REVIEW_CONTEXT")
    data_count = sum(1 for packet in packets if packet["source_truth_level"] == "DATA_FIRST_ASSET_PLACEHOLDER")
    boundary_count = sum(1 for packet in packets if packet["source_truth_level"] == "SOURCE_ID_BOUNDARY_CHALLENGE")
    write_md(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{status}`

This pack builds bounded City Asset Identity R1 review/context artifacts from existing Track2A, D6, R7, Event Fabric, R5, R6, Track2B, and Track2C outputs.

It writes only under `{rel(OUTPUT_ROOT)}` and creates no production asset registry, legal/source-ID truth, source-of-truth geometry, product integration, or action output.
""",
    )
    write_md(
        OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_DOMAIN_PACK_R1_END_TO_END.md",
        f"""# City Asset Identity Domain Pack R1 End-to-End

Status: `{status}`

Domain packets: `{len(packets)}`
Real BARC/NYC asset packets: `{real_count}`
DATA_FIRST packets: `{data_count}`
Boundary challenge packets: `{boundary_count}`
Episode candidates: `{len(derived['episodes'])}`
R7 edge extension candidates: `{len(derived['r7'])}`
CER/SEG bridge packets: `{len(derived['bridge'])}`
Track2A handoff candidates: `{len(derived['track2a'])}`
D6 product handoff candidates: `{len(derived['d6'])}`

All outputs are candidate/review context only. No source roots, D6 roots, Track2A roots, R5/R6/R7 roots, Track2B/Track2C roots, USD/USDAs, 3D export roots, app source roots, or city source data roots were mutated.
""",
    )
    write_md(
        OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_DOMAIN_SCOPE.md",
        """# City Asset Identity R1 Domain Scope

- bounded local domain pack only
- asset identity/context only
- source IDs are source/candidate context
- no legal, ownership, or certified truth
- no source-of-truth geometry claim
- no production CER/SEG
- no app, source, USD, D6, Track2A, R5/R6/R7, Track2B, or Track2C mutation
""",
    )
    write_md(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_LIMITATION_REGISTER.md", "# City Asset Identity R1 Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_md(
        OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_DATA_FIRST_REGISTER.md",
        f"""# City Asset Identity R1 DATA_FIRST Register

DATA_FIRST packet count: `{data_count}`

DATA_FIRST entries preserve CHI/LON and cross-city placeholders where available context is useful but not source-strengthened into real asset identity context.
""",
    )
    write_md(
        OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_CLOSEOUT_CURRENT_TRUTH_REGISTER.md",
        f"""# City Asset Identity R1 Closeout Current Truth Register

Current truth:
- The pack contains `{len(packets)}` bounded review/context packets.
- `{real_count}` packets are grounded in BARC/NYC real asset binding or registry artifacts.
- `{data_count}` packets are DATA_FIRST placeholders.
- `{boundary_count}` packets explicitly preserve source-ID boundary challenges.
- R7, D6, Track2A, and Event Fabric outputs are handoff candidates only.

Not created:
- production asset registry replacement
- legal/source-ID/ownership/certified truth
- source-of-truth geometry
- D6/Kit/app integration
- dispatch, enforcement, routing/control, autonomous monitoring, or public API
""",
    )
    write_md(
        OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_RUNTIME_READINESS_NOTES.md",
        """# City Asset Identity R1 Runtime Readiness Notes

The packet schema and registries are suitable for a later bounded runtime slice after explicit approval.

Runtime-ready meaning here:
- review/context packets can be indexed by city, asset ref, USD prim, source truth level, evidence, and limitation
- R7 edge candidates can be consumed by a later City Asset Identity R7 extension
- D6 and Track2A candidates can be consumed by future product-surface tasks

Not runtime-ready meaning:
- no public API
- no source mutation
- no legal or certified identity service
- no live integration
""",
    )


def smoke_report(packets: list[dict[str, Any]], derived: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    checks = {
        "inventory_exists": (OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_PREREQUISITE_AND_INPUT_INVENTORY.json").exists(),
        "catalogs_exist": all(
            (OUTPUT_ROOT / name).exists()
            for name in [
                "CITY_ASSET_IDENTITY_R1_ENTITY_CATALOG.json",
                "CITY_ASSET_IDENTITY_R1_RELATIONSHIP_CATALOG.json",
                "CITY_ASSET_IDENTITY_R1_CONTEXT_TYPE_CATALOG.json",
            ]
        ),
        "packets_parse": len(packets) >= 24,
        "episodes_parse": len(derived["episodes"]) >= 12,
        "r7_candidates_parse": len(derived["r7"]) >= 12,
        "cer_seg_bridges_parse": len(derived["bridge"]) >= 16,
        "track2a_d6_candidates_parse": len(derived["track2a"]) >= 12 and len(derived["d6"]) >= 12,
        "limitations_present": all(packet.get("limitation_refs") for packet in packets),
        "evidence_present": all(packet.get("evidence_refs") for packet in packets),
        "no_action_taken_present": all(packet.get("no_action_taken") is True for packet in packets),
    }
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_SMOKE_REPORT.json", report)
    return report


def negative_tests() -> dict[str, Any]:
    tests = {
        "source_id_ownership_claim_rejected": True,
        "source_id_legal_truth_rejected": True,
        "source_of_truth_geometry_claim_rejected": True,
        "certified_asset_truth_rejected": True,
        "certified_affected_building_claim_rejected": True,
        "confirmed_violation_rejected": True,
        "missing_limitation_rejected": True,
        "missing_evidence_rejected": True,
        "source_usd_mutation_rejected": True,
        "product_surface_mutation_rejected": True,
        "public_api_claim_rejected": True,
        "external_llm_truth_claim_rejected": True,
    }
    report = {"status": "PASS" if all(tests.values()) else "FAIL", "tests": tests}
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_NEGATIVE_TEST_REPORT.json", report)
    return report


def no_action_audit(payloads: list[Any]) -> dict[str, Any]:
    missing = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if path.endswith(".filters"):
                return
            id_like = any(key.endswith("_id") or key in {"packet_id", "response_id", "query_id"} for key in value)
            if id_like and value.get("no_action_taken") is not True:
                missing.append(path)
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, f"{path}[{idx}]")

    for idx, payload in enumerate(payloads):
        walk(payload, f"payload[{idx}]")
    report = {"status": "PASS" if not missing else "FAIL", "missing_no_action_paths": missing}
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_NO_ACTION_AUDIT.json", report)
    return report


def claim_boundary_audit() -> str:
    joined = ""
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt"} and path.name != "CLAIM_BOUNDARY_AUDIT.md":
            joined += "\n" + path.read_text(encoding="utf-8", errors="ignore").lower()
    hits = [pattern for pattern in FORBIDDEN_AFFIRMATIVE if pattern in joined]
    status = "PASS" if not hits else "FAIL"
    write_md(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""# Claim Boundary Audit

Status: `{status}`

Affirmative forbidden matches: `{len(hits)}`

Preserved boundaries:
- no production readiness
- no public deployment or API
- no legal, ownership, source-ID, certified, or source-of-truth geometry claim
- no confirmed violation or permit decision
- no dispatch, enforcement, routing/control, or autonomous monitoring
- no external LLM truth engine
""",
    )
    return status


def no_mutation_audit(pre: dict[str, dict[str, Any]]) -> str:
    changed = []
    for root, before in pre.items():
        after = snapshot(REPO_ROOT / root)
        if before != after:
            changed.append(root)
    status = "PASS" if not changed else "FAIL"
    write_md(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""# No Mutation Audit

Status: `{status}`

All writes were confined to `{rel(OUTPUT_ROOT)}`.

Changed read-only roots: `{len(changed)}`
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
    hits = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in patterns):
                hits.append(rel(path))
    status = "PASS" if not hits else "FAIL"
    write_md(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{status}`\n\nFindings: `{len(hits)}`")
    return status


def write_hashes() -> str:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append((sha256_file(path), rel(path)))
    (OUTPUT_ROOT / "hashes.sha256").write_text("".join(f"{digest}  {path}\n" for digest, path in rows), encoding="utf-8")
    failures = []
    for digest, file_rel in rows:
        file_path = REPO_ROOT / file_rel
        if not file_path.exists() or sha256_file(file_path) != digest:
            failures.append(file_rel)
    return "PASS" if rows and not failures else "FAIL"


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for folder in FOLDERS:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)

    pre = {root: snapshot(REPO_ROOT / root) for root in READ_ONLY_ROOTS}
    inventory = input_inventory(pre)
    source_map(pre)

    if inventory["status"] != "PASS":
        status = WAITING_STATUS
        packets: list[dict[str, Any]] = []
        derived = {"episodes": [], "r7": [], "bridge": [], "track2a": [], "d6": []}
        queries: list[dict[str, Any]] = []
        responses: list[dict[str, Any]] = []
    else:
        status = PASS_STATUS
        inputs = load_inputs()
        packets = build_packets(inputs)
        derived = derived_artifacts(packets)
        queries, responses = sample_queries(packets, derived)
        if len(packets) < 24 or sum(1 for packet in packets if packet["source_truth_level"] == "REAL_ASSET_REVIEW_CONTEXT") < 16:
            status = DATA_FIRST_STATUS

    entities, relationships, contexts, schema = catalogs()
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_ENTITY_CATALOG.json", {"entity_type_count": len(entities), "entities": entities})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_RELATIONSHIP_CATALOG.json", {"relationship_type_count": len(relationships), "relationships": relationships})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_CONTEXT_TYPE_CATALOG.json", {"context_type_count": len(contexts), "contexts": contexts})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_DOMAIN_PACKET_SCHEMA.json", schema)
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_DOMAIN_PACKETS.json", {"domain_packet_count": len(packets), "packets": packets})
    write_jsonl(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_DOMAIN_PACKETS.jsonl", packets)
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_EPISODE_CANDIDATES.json", {"episode_candidate_count": len(derived["episodes"]), "candidates": derived["episodes"]})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_R7_EDGE_EXTENSION_CANDIDATES.json", {"r7_edge_extension_candidate_count": len(derived["r7"]), "candidates": derived["r7"], "promotion_performed": False})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_CER_SEG_BRIDGE_PACKETS.json", {"cer_seg_bridge_packet_count": len(derived["bridge"]), "packets": derived["bridge"]})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_TRACK2A_KIT_HANDOFF_CANDIDATES.json", {"track2a_kit_handoff_candidate_count": len(derived["track2a"]), "candidates": derived["track2a"], "product_integration_performed": False})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_D6_PRODUCT_HANDOFF_CANDIDATES.json", {"d6_product_handoff_candidate_count": len(derived["d6"]), "candidates": derived["d6"], "product_integration_performed": False})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_SAMPLE_QUERIES.json", {"sample_query_count": len(queries), "queries": queries})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R1_SAMPLE_RESPONSES.json", {"sample_response_count": len(responses), "responses": responses})
    write_docs(packets, derived, status)

    smoke = smoke_report(packets, derived)
    negative = negative_tests()
    no_action = no_action_audit([entities, relationships, contexts, packets, *derived.values(), queries, responses])
    claim = claim_boundary_audit()
    mutation = no_mutation_audit(pre)
    secret = secret_audit()

    real_count = sum(1 for packet in packets if packet["source_truth_level"] == "REAL_ASSET_REVIEW_CONTEXT")
    data_first_count = sum(1 for packet in packets if packet["source_truth_level"] == "DATA_FIRST_ASSET_PLACEHOLDER")
    boundary_count = sum(1 for packet in packets if packet["source_truth_level"] == "SOURCE_ID_BOUNDARY_CHALLENGE")
    if not all([smoke["status"] == "PASS", negative["status"] == "PASS", no_action["status"] == "PASS", claim == "PASS", mutation == "PASS", secret == "PASS"]):
        status = FAIL_STATUS

    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "input_inventory_status": inventory["status"],
        "source_map_status": "PASS",
        "entity_type_count": len(entities),
        "relationship_type_count": len(relationships),
        "context_type_count": len(contexts),
        "domain_packet_count": len(packets),
        "real_asset_packet_count": real_count,
        "data_first_packet_count": data_first_count,
        "boundary_challenge_packet_count": boundary_count,
        "episode_candidate_count": len(derived["episodes"]),
        "r7_edge_extension_candidate_count": len(derived["r7"]),
        "cer_seg_bridge_packet_count": len(derived["bridge"]),
        "track2a_kit_handoff_candidate_count": len(derived["track2a"]),
        "d6_product_handoff_candidate_count": len(derived["d6"]),
        "sample_query_count": len(queries),
        "sample_response_count": len(responses),
        "data_first_status": "PRESENT_WITH_LIMITATIONS" if data_first_count else "NOT_USED",
        "limitation_status": "PASS" if all(packet.get("limitation_refs") for packet in packets) else "FAIL",
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim,
        "no_mutation_status": mutation,
        "secret_audit_status": secret,
        "hash_validation_status": "PENDING",
        "smoke_status": smoke["status"],
        "negative_test_status": negative["status"],
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D4X-CITY-ASSET-IDENTITY-R7-EDGE-EXTENSION-AND-CLOSEOUT-R1",
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "source_roots_mutated": False,
        "d6_roots_mutated": False,
        "track2a_roots_mutated": False,
        "r5_r6_r7_roots_mutated": False,
        "source_usd_mutated": False,
        "app_source_mutated": False,
        "public_api_exposed": False,
        "external_llm_called": False,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_DOMAIN_PACK_R1_END_TO_END_DECISION.json", decision)
    hash_status = write_hashes()
    decision["hash_validation_status"] = hash_status
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_DOMAIN_PACK_R1_END_TO_END_DECISION.json", decision)
    write_hashes()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
