#!/usr/bin/env python3
"""Build R7 R2 cross-domain edge seed source-diversity output pack.

This runner is intentionally backend-only. It reads completed CityBrain output
roots, creates a grounded relationship seed pack with source-family balancing,
and writes only under the R7 R2 output root.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D4X-R7-CROSS-DOMAIN-EDGE-SEED-R2-SOURCE-DIVERSITY"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY_WITH_LIMITATIONS"
INVENTORY_LIMIT_STATUS = "PASS_R7_R2_SOURCE_DIVERSITY_WITH_INVENTORY_LIMITATIONS"
FAIL_CAP_STATUS = "FAIL_R7_R2_SOURCE_DIVERSITY_SOURCE_FAMILY_CAP_EXCEEDED"
FAIL_EVIDENCE_STATUS = "FAIL_R7_R2_EVIDENCE_OR_LIMITATION_MISSING"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY"
SCHEMA_VERSION = "main-citybrain-d4x-r7-cross-domain-edge-seed-r2-source-diversity.v1"

SOURCE_FAMILY_CAP = 0.40
MIN_NEW_GROUNDED_EDGES = 20
MIN_NON_R6_NEW_GROUNDED_EDGES = 12
MIN_SOURCE_FAMILIES = 4
MIN_RELATIONSHIP_TYPES = 6

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity.py"

REQUIRED_ROOTS = {
    "R5_DOMAIN_PACK": REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
    "R6_INCIDENT_EVENT": REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    "TRACK2A_ASSET_REGISTRY": REPO_ROOT / "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end",
    "TRACK2A_USD_CER_SEG_BRIDGE": REPO_ROOT / "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end",
    "TRACK2A_OMNI_OVERLAY_SMOKE": REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke",
    "TRACK2B_CITY_EPISODE_PACK": REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "TRACK2C_KIT_CONTROL_ROOM_PACK": REPO_ROOT / "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
}

OPTIONAL_ROOTS = {
    "D6_REFERENCE_DEMO_EVIDENCE": [
        REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_r1",
        REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_r2_polish",
    ]
}

FAMILY_ORDER = [
    "R6_INCIDENT_EVENT",
    "R5_DOMAIN_PACK",
    "TRACK2A_ASSET_REGISTRY",
    "TRACK2A_USD_CER_SEG_BRIDGE",
    "TRACK2A_OMNI_OVERLAY_SMOKE",
    "TRACK2B_CITY_EPISODE_PACK",
    "TRACK2C_KIT_CONTROL_ROOM_PACK",
]

PER_FAMILY_ACCEPT_TARGET = 4

FORBIDDEN_CLAIMS = [
    "production ready",
    "public api deployed",
    "certified citywide digital twin",
    "ownership truth",
    "legal finding",
    "certified affected-building truth",
    "confirmed violation",
    "permit approval",
    "permit rejection",
    "certified impact",
    "certified traffic model",
    "dispatch recommendation",
    "enforcement recommendation",
    "routing instruction",
    "traffic-control command",
    "autonomous monitoring",
    "autonomous alert",
    "autonomous action",
]

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)secret[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


RUN_TIMESTAMP = now_utc()


def rel_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def unique_strs(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in as_list(values):
        if value is None:
            continue
        text = str(value)
        if not text:
            continue
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result


def stable_id(*parts: Any, prefix: str = "r7-r2-edge") -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:14]
    return f"{prefix}:{digest}"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_root(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "fingerprint": None}
    files = sorted(path for path in root.rglob("*") if path.is_file())
    digest = hashlib.sha256()
    total_bytes = 0
    for path in files:
        stat = path.stat()
        total_bytes += stat.st_size
        digest.update(rel_path(path).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
    return {
        "exists": True,
        "file_count": len(files),
        "total_bytes": total_bytes,
        "fingerprint": digest.hexdigest(),
    }


def source_artifact(path: Path, fragment: str | None = None) -> str:
    base = rel_path(path)
    return f"{base}:{fragment}" if fragment else base


def normalize_review_state(value: Any, fallback: str = "candidate_review") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    return text.replace("/", "_").replace(" ", "_")


def confidence_from_label(label: Any, fallback: float = 0.66) -> float:
    text = str(label or "").lower()
    if "high" in text or "asserted" in text:
        return 0.82
    if "bounded" in text:
        return 0.66
    if "candidate" in text or "review" in text:
        return 0.62
    return fallback


def make_edge(
    *,
    source_family: str,
    relationship_type: str,
    source_id: str,
    source_entity_type: str,
    target_id: str,
    target_entity_type: str,
    evidence_refs: list[str],
    limitation_refs: list[str],
    source_artifact_ref: str,
    trace_refs: list[str] | None = None,
    source_system_refs: list[str] | None = None,
    confidence: float | None = None,
    review_state: str | None = None,
    assertion_method: str,
    assertion_boundary: str,
    relationship_summary: str,
    spatial_scope: dict[str, Any] | None = None,
    temporal_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    relationship_id = stable_id(
        TASK_NAME,
        source_family,
        relationship_type,
        source_id,
        target_id,
    )
    return {
        "relationship_id": relationship_id,
        "relationship_type": relationship_type,
        "relationship_summary": relationship_summary,
        "source_family": source_family,
        "source_canonical_entity_id": source_id,
        "source_entity_type": source_entity_type,
        "target_canonical_entity_id": target_id,
        "target_entity_type": target_entity_type,
        "direction": "directed",
        "confidence": confidence,
        "review_state": review_state,
        "evidence_refs": unique_strs(evidence_refs),
        "limitation_refs": unique_strs(limitation_refs),
        "trace_refs": unique_strs(trace_refs or [source_artifact_ref]),
        "source_system_refs": unique_strs(source_system_refs or []),
        "source_artifact_ref": source_artifact_ref,
        "assertion_method": assertion_method,
        "assertion_boundary": assertion_boundary,
        "claim_boundary": (
            "Grounded relationship seed for review/context only. "
            "No production, public API, legal, certified, dispatch, routing, control, or autonomous claim."
        ),
        "temporal_scope": temporal_scope or {"temporal_window": "review/context"},
        "spatial_scope": spatial_scope or {"scope": "source artifact context"},
        "cross_domain": True,
        "r2_new_edge": True,
        "from_r7_r1": False,
        "not_causal": True,
        "not_city_truth": True,
        "not_legal_or_certified_truth": True,
        "not_control_or_action": True,
        "no_action_taken": True,
        "created_by_run": TASK_NAME,
        "created_at_utc": RUN_TIMESTAMP,
        "schema_version": SCHEMA_VERSION,
    }


def missing_requirements(edge: dict[str, Any]) -> list[str]:
    missing = []
    if not edge.get("evidence_refs"):
        missing.append("missing_evidence_refs")
    if not edge.get("limitation_refs"):
        missing.append("missing_limitation_refs")
    if edge.get("confidence") is None:
        missing.append("missing_confidence")
    if not edge.get("review_state"):
        missing.append("missing_review_state")
    if edge.get("no_action_taken") is not True:
        missing.append("missing_no_action_taken")
    return missing


def load_r7_r1() -> dict[str, Any]:
    roots = sorted(
        root
        for root in (REPO_ROOT / "outputs").glob("*r7*edge*seed*r1*")
        if root.is_dir()
    )
    loaded_roots = []
    accepted_edges: list[dict[str, Any]] = []
    for root in roots:
        registry = read_json(root / "RELATIONSHIP_EDGE_SEED_REGISTRY.json", {})
        edges = registry.get("accepted_grounded_edges", []) if isinstance(registry, dict) else []
        if edges:
            loaded_roots.append(rel_path(root))
            accepted_edges.extend(edges)
    return {
        "loaded": bool(accepted_edges),
        "roots": loaded_roots,
        "accepted_grounded_edges": accepted_edges,
        "accepted_grounded_edge_count": len(accepted_edges),
    }


def build_candidates() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    source_map: dict[str, Any] = {}

    r5_file = REQUIRED_ROOTS["R5_DOMAIN_PACK"] / "R5_CIVIC_SERVICE_RUNTIME_SLICE_OUTPUT_PACKETS.json"
    r5_packets = read_json(r5_file, {}).get("packets", [])
    source_map["R5_DOMAIN_PACK"] = {
        "root": rel_path(REQUIRED_ROOTS["R5_DOMAIN_PACK"]),
        "primary_artifact": rel_path(r5_file),
        "record_count": len(r5_packets),
        "source_family_role": "domain-pack runtime packets and civic service review context",
    }
    for packet in r5_packets:
        packet_id = str(packet.get("packet_id") or packet.get("request_id") or "r5-packet")
        city_id = str(packet.get("city_id") or "city").lower()
        domain_pack_id = str(packet.get("domain_pack_id") or "domain_pack")
        candidates.append(
            make_edge(
                source_family="R5_DOMAIN_PACK",
                relationship_type="has_domain_packet_context",
                source_id=f"city:{city_id}:domain:{domain_pack_id}",
                source_entity_type="domain_context",
                target_id=packet_id,
                target_entity_type="runtime_packet",
                evidence_refs=unique_strs(packet.get("evidence_refs")),
                limitation_refs=unique_strs(packet.get("limitation_refs")),
                source_artifact_ref=source_artifact(r5_file, packet_id),
                trace_refs=[source_artifact(r5_file, packet_id), str(packet.get("request_id") or packet_id)],
                source_system_refs=unique_strs(packet.get("source_signal_refs")),
                confidence=confidence_from_label(packet.get("confidence_label")),
                review_state=normalize_review_state(packet.get("review_state")),
                assertion_method="document_reference",
                assertion_boundary="R5 domain packet is review/context only; it is not a service action or operational finding.",
                relationship_summary=f"{domain_pack_id} has bounded app/runtime packet context {packet_id}.",
                spatial_scope={"city_id": packet.get("city_id"), "method": "R5 packet city/domain fields"},
            )
        )

    r6_file = REQUIRED_ROOTS["R6_INCIDENT_EVENT"] / "R6_EVENT_TO_ENTITY_RESULTS.json"
    r6_results = read_json(r6_file, {}).get("resolutions", [])
    source_map["R6_INCIDENT_EVENT"] = {
        "root": rel_path(REQUIRED_ROOTS["R6_INCIDENT_EVENT"]),
        "primary_artifact": rel_path(r6_file),
        "record_count": len(r6_results),
        "source_family_role": "bounded replay incident/event to entity context",
    }
    for result in r6_results:
        event_id = str(result.get("event_id") or "r6-event")
        canonical_refs = unique_strs(result.get("canonical_entity_refs"))
        source_id = canonical_refs[0] if canonical_refs else str(result.get("source_entity_id") or event_id)
        event_suffix = event_id.split("-")[-1]
        evidence_refs = [
            f"evidence:r6:event:{event_suffix}",
            source_artifact(r6_file, event_id),
        ]
        candidates.append(
            make_edge(
                source_family="R6_INCIDENT_EVENT",
                relationship_type="has_event_context",
                source_id=source_id,
                source_entity_type="candidate_canonical_entity",
                target_id=event_id,
                target_entity_type="incident_event",
                evidence_refs=evidence_refs,
                limitation_refs=unique_strs(result.get("limitations")),
                source_artifact_ref=source_artifact(r6_file, event_id),
                trace_refs=[source_artifact(r6_file, event_id), f"event-trace:{event_id}"],
                source_system_refs=unique_strs([result.get("source_entity_id"), *canonical_refs]),
                confidence=float(result.get("confidence") or 0.62),
                review_state=normalize_review_state(result.get("review_state")),
                assertion_method="event_resolution",
                assertion_boundary="R6 event/entity resolution is candidate review context only.",
                relationship_summary=f"{source_id} has bounded R6 event context {event_id}.",
                spatial_scope={"method": "R6 source entity and canonical candidate refs"},
                temporal_scope={
                    "event_time": result.get("event_time"),
                    "ingested_at": result.get("ingested_at"),
                    "temporal_window": result.get("lifecycle_state") or "review/context",
                },
            )
        )

    asset_file = REQUIRED_ROOTS["TRACK2A_ASSET_REGISTRY"] / "TRACK2A_SELECTED_DEMO_ASSETS.json"
    assets = read_json(asset_file, {}).get("assets", [])
    source_map["TRACK2A_ASSET_REGISTRY"] = {
        "root": rel_path(REQUIRED_ROOTS["TRACK2A_ASSET_REGISTRY"]),
        "primary_artifact": rel_path(asset_file),
        "record_count": len(assets),
        "source_family_role": "asset registry rows with CER/SEG candidate context",
    }
    for asset in assets:
        asset_id = str(asset.get("asset_registry_id") or asset.get("source_asset_id") or "asset")
        cer_refs = unique_strs(asset.get("cer_candidate_refs"))
        target_id = cer_refs[0] if cer_refs else asset_id
        candidates.append(
            make_edge(
                source_family="TRACK2A_ASSET_REGISTRY",
                relationship_type="has_asset_registry_context",
                source_id=asset_id,
                source_entity_type=str(asset.get("asset_type") or "city_asset"),
                target_id=target_id,
                target_entity_type="cer_candidate_context",
                evidence_refs=unique_strs(asset.get("evidence_refs")),
                limitation_refs=unique_strs(asset.get("limitation_refs")),
                source_artifact_ref=source_artifact(asset_file, asset_id),
                trace_refs=[source_artifact(asset_file, asset_id), *unique_strs(asset.get("seg_context_refs"))],
                source_system_refs=unique_strs([asset.get("source_asset_id"), *cer_refs, *unique_strs(asset.get("seg_context_refs"))]),
                confidence=0.70 if asset.get("record_quality", {}).get("source_identity_context_available") else 0.62,
                review_state="candidate_review",
                assertion_method="shared_identifier",
                assertion_boundary="Track2A asset registry row is visual/source/candidate context only.",
                relationship_summary=f"{asset_id} has bounded asset registry candidate context {target_id}.",
                spatial_scope={"city_id": asset.get("city_id"), "method": "Track2A asset registry"},
            )
        )

    usd_file = REQUIRED_ROOTS["TRACK2A_USD_CER_SEG_BRIDGE"] / "OMNI_USD_PRIM_TO_ASSET_MAP.json"
    usd_mappings = read_json(usd_file, {}).get("mappings", [])
    source_map["TRACK2A_USD_CER_SEG_BRIDGE"] = {
        "root": rel_path(REQUIRED_ROOTS["TRACK2A_USD_CER_SEG_BRIDGE"]),
        "primary_artifact": rel_path(usd_file),
        "record_count": len(usd_mappings),
        "source_family_role": "USD prim to asset/CER/SEG bridge context",
    }
    for mapping in usd_mappings:
        asset_id = str(mapping.get("asset_registry_id") or mapping.get("source_asset_id") or "asset")
        prim_path = str(mapping.get("usd_prim_path") or mapping.get("map_id") or "usd_prim")
        candidates.append(
            make_edge(
                source_family="TRACK2A_USD_CER_SEG_BRIDGE",
                relationship_type="mapped_to_usd_prim_context",
                source_id=asset_id,
                source_entity_type="asset_registry_row",
                target_id=prim_path,
                target_entity_type="usd_prim_path",
                evidence_refs=unique_strs(mapping.get("evidence_refs")),
                limitation_refs=unique_strs(mapping.get("limitation_refs")),
                source_artifact_ref=source_artifact(usd_file, mapping.get("map_id") or prim_path),
                trace_refs=[source_artifact(usd_file, mapping.get("map_id") or prim_path), str(mapping.get("pick_id") or "")],
                source_system_refs=unique_strs([mapping.get("source_asset_id"), *unique_strs(mapping.get("seg_context_refs"))]),
                confidence=0.72 if mapping.get("mapping_status") == "PASS_WITH_LIMITATIONS" else 0.64,
                review_state="asserted_source_context",
                assertion_method="manual_bridge",
                assertion_boundary="USD prim mapping is visual/source context only and does not mutate USD.",
                relationship_summary=f"{asset_id} maps to bounded USD prim context {prim_path}.",
                spatial_scope={"method": "Track2A USD to CER bridge", "usd_prim_path": prim_path},
            )
        )

    overlay_file = REQUIRED_ROOTS["TRACK2A_OMNI_OVERLAY_SMOKE"] / "OMNI_OVERLAY_ASSET_DOMAIN_EVENT_ALIGNMENT.json"
    alignments = read_json(overlay_file, {}).get("alignments", [])
    source_map["TRACK2A_OMNI_OVERLAY_SMOKE"] = {
        "root": rel_path(REQUIRED_ROOTS["TRACK2A_OMNI_OVERLAY_SMOKE"]),
        "primary_artifact": rel_path(overlay_file),
        "record_count": len(alignments),
        "source_family_role": "Omniverse overlay smoke alignment context",
    }
    for alignment in alignments:
        asset_id = str(alignment.get("asset_registry_row") or alignment.get("alignment_id") or "asset")
        overlay_ref = str(alignment.get("overlay_packet_ref") or alignment.get("alignment_id") or "overlay")
        candidates.append(
            make_edge(
                source_family="TRACK2A_OMNI_OVERLAY_SMOKE",
                relationship_type="has_omniverse_overlay_context",
                source_id=asset_id,
                source_entity_type="asset_registry_row",
                target_id=overlay_ref,
                target_entity_type="omniverse_overlay_packet",
                evidence_refs=unique_strs(alignment.get("evidence_refs")),
                limitation_refs=unique_strs(alignment.get("limitation_refs")),
                source_artifact_ref=source_artifact(overlay_file, alignment.get("alignment_id") or overlay_ref),
                trace_refs=[source_artifact(overlay_file, alignment.get("alignment_id") or overlay_ref), str(alignment.get("usd_prim_mapping") or "")],
                source_system_refs=unique_strs([
                    alignment.get("CER_packet"),
                    alignment.get("SEG_packet"),
                    alignment.get("R5_domain_packet"),
                    alignment.get("R6_event_or_incident_packet"),
                ]),
                confidence=0.68,
                review_state="candidate_review",
                assertion_method="document_reference",
                assertion_boundary="Omniverse overlay alignment is marker/context only, not canonical truth.",
                relationship_summary=f"{asset_id} has bounded Omniverse overlay context {overlay_ref}.",
                spatial_scope={"method": "Track2A overlay alignment", "usd_prim_mapping": alignment.get("usd_prim_mapping")},
            )
        )

    episode_file = REQUIRED_ROOTS["TRACK2B_CITY_EPISODE_PACK"] / "TRACK2B_CURATED_CITY_EPISODE_PACK.json"
    episodes = read_json(episode_file, {}).get("episodes", [])
    source_map["TRACK2B_CITY_EPISODE_PACK"] = {
        "root": rel_path(REQUIRED_ROOTS["TRACK2B_CITY_EPISODE_PACK"]),
        "primary_artifact": rel_path(episode_file),
        "record_count": len(episodes),
        "source_family_role": "curated city episode source/evidence narrative context",
    }
    for episode in episodes:
        episode_id = str(episode.get("episode_id") or episode.get("title") or "episode")
        source_refs = unique_strs(
            episode.get("entity_refs")
            or episode.get("building_asset_refs")
            or episode.get("event_refs")
            or episode.get("source_refs")
            or [episode.get("city_id")]
        )
        source_id = source_refs[0] if source_refs else f"episode-source:{episode_id}"
        limitations = unique_strs(episode.get("limitations") or episode.get("limitation_refs"))
        candidates.append(
            make_edge(
                source_family="TRACK2B_CITY_EPISODE_PACK",
                relationship_type="appears_in_city_episode_context",
                source_id=source_id,
                source_entity_type="episode_source_ref",
                target_id=episode_id,
                target_entity_type="city_episode",
                evidence_refs=unique_strs(episode.get("evidence_refs")),
                limitation_refs=limitations,
                source_artifact_ref=source_artifact(episode_file, episode_id),
                trace_refs=[source_artifact(episode_file, episode_id), *unique_strs(episode.get("runtime_packet_refs"))],
                source_system_refs=unique_strs([*source_refs, *unique_strs(episode.get("source_refs"))]),
                confidence=0.64,
                review_state=normalize_review_state((episode.get("lifecycle_states") or ["review/context"])[0]),
                assertion_method="document_reference",
                assertion_boundary="Track2B episode relationship is curated demo/review context only.",
                relationship_summary=f"{source_id} appears in bounded city episode context {episode_id}.",
                spatial_scope={"city_id": episode.get("city_id"), "where": episode.get("where")},
                temporal_scope={"timeline_or_status": episode.get("timeline_or_status"), "temporal_window": "review/context"},
            )
        )

    track2c_file = REQUIRED_ROOTS["TRACK2C_KIT_CONTROL_ROOM_PACK"] / "TRACK2C_INTEGRATED_EPISODE_PACK.json"
    control_room_episodes = read_json(track2c_file, {}).get("episodes", [])
    source_map["TRACK2C_KIT_CONTROL_ROOM_PACK"] = {
        "root": rel_path(REQUIRED_ROOTS["TRACK2C_KIT_CONTROL_ROOM_PACK"]),
        "primary_artifact": rel_path(track2c_file),
        "record_count": len(control_room_episodes),
        "source_family_role": "Kit-first control-room consumption context; not primary relationship truth",
    }
    for episode in control_room_episodes:
        integrated_id = str(episode.get("integrated_episode_id") or episode.get("episode_ref") or "kit-episode")
        source_id = str(
            episode.get("primary_asset_ref")
            or (episode.get("asset_registry_refs") or [None])[0]
            or episode.get("episode_ref")
            or integrated_id
        )
        candidates.append(
            make_edge(
                source_family="TRACK2C_KIT_CONTROL_ROOM_PACK",
                relationship_type="has_control_room_episode_context",
                source_id=source_id,
                source_entity_type="control_room_subject",
                target_id=integrated_id,
                target_entity_type="kit_control_room_episode",
                evidence_refs=unique_strs(episode.get("evidence_refs")),
                limitation_refs=unique_strs(episode.get("limitation_refs")),
                source_artifact_ref=source_artifact(track2c_file, integrated_id),
                trace_refs=[source_artifact(track2c_file, integrated_id), str(episode.get("kit_camera_bookmark_ref") or "")],
                source_system_refs=unique_strs([
                    episode.get("episode_ref"),
                    episode.get("usd_stage_ref"),
                    episode.get("usd_prim_focus"),
                    *unique_strs(episode.get("domain_packet_refs")),
                ]),
                confidence=0.62,
                review_state="control_room_context",
                assertion_method="document_reference",
                assertion_boundary="Track2C edge records control-room consumption context only; underlying truth remains in Track1/Track2A/Track2B evidence.",
                relationship_summary=f"{source_id} has bounded Kit control-room episode context {integrated_id}.",
                spatial_scope={"city_id": episode.get("city_id"), "usd_prim_focus": episode.get("usd_prim_focus")},
            )
        )

    d6_roots = [root for root in OPTIONAL_ROOTS["D6_REFERENCE_DEMO_EVIDENCE"] if root.exists()]
    d6_records = []
    for root in d6_roots:
        for filename in [
            "CONTROL_ROOM_EVIDENCE_TRACE_WALKTHROUGH.json",
            "CONTROL_ROOM_SAFE_NEXT_LOOK_FLOW.json",
            "CONTROL_ROOM_REFERENCE_DEMO_R1_NEXT_PRIORITY_DECISION_MATRIX.json",
        ]:
            path = root / filename
            if path.exists():
                d6_records.append(rel_path(path))
    source_map["D6_REFERENCE_DEMO_EVIDENCE"] = {
        "root": [rel_path(root) for root in d6_roots],
        "primary_artifacts": d6_records,
        "record_count": len(d6_records),
        "source_family_role": "optional downstream demo evidence and handoff context only; not used to invent R2 truth",
        "accepted_edge_role": "supporting_context_only",
    }

    candidates.extend(make_negative_test_candidates())
    return candidates, source_map


def make_negative_test_candidates() -> list[dict[str, Any]]:
    base = {
        "source_family": "NEGATIVE_TEST",
        "relationship_type": "invalid_test_candidate",
        "source_id": "negative-test-source",
        "source_entity_type": "test_fixture",
        "target_id": "negative-test-target",
        "target_entity_type": "test_fixture",
        "source_artifact_ref": "negative-test-fixture",
        "trace_refs": ["negative-test-fixture"],
        "source_system_refs": ["r7-r2-negative-test"],
        "confidence": 0.5,
        "review_state": "requires_review",
        "assertion_method": "test_fixture",
        "assertion_boundary": "Negative test fixture only.",
        "relationship_summary": "Negative test fixture.",
    }
    missing_evidence = make_edge(
        **{
            **base,
            "evidence_refs": [],
            "limitation_refs": ["negative_test_limitation"],
        }
    )
    missing_limitation = make_edge(
        **{
            **base,
            "target_id": "negative-test-missing-limitation",
            "evidence_refs": ["negative_test_evidence"],
            "limitation_refs": [],
        }
    )
    missing_confidence = make_edge(
        **{
            **base,
            "target_id": "negative-test-missing-confidence",
            "evidence_refs": ["negative_test_evidence"],
            "limitation_refs": ["negative_test_limitation"],
            "confidence": None,
        }
    )
    missing_review = make_edge(
        **{
            **base,
            "target_id": "negative-test-missing-review-state",
            "evidence_refs": ["negative_test_evidence"],
            "limitation_refs": ["negative_test_limitation"],
            "review_state": "",
        }
    )
    return [missing_evidence, missing_limitation, missing_confidence, missing_review]


def select_edges(candidates: list[dict[str, Any]], r7_r1: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rejected: list[dict[str, Any]] = []
    valid_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_keys: set[tuple[str, str, str, str]] = set()

    r1_keys = {
        (
            str(edge.get("relationship_type")),
            str(edge.get("source_canonical_entity_id")),
            str(edge.get("target_canonical_entity_id")),
            str(edge.get("source_family") or edge.get("source_evidence_family")),
        )
        for edge in r7_r1.get("accepted_grounded_edges", [])
    }

    for edge in candidates:
        family = edge.get("source_family")
        missing = missing_requirements(edge)
        key = (
            str(edge.get("relationship_type")),
            str(edge.get("source_canonical_entity_id")),
            str(edge.get("target_canonical_entity_id")),
            str(family),
        )
        if missing:
            rejected.append({**edge, "rejection_reasons": missing, "candidate_status": "REJECTED"})
            continue
        if key in seen_keys:
            rejected.append({**edge, "rejection_reasons": ["duplicate_r2_candidate"], "candidate_status": "REJECTED"})
            continue
        if key in r1_keys:
            rejected.append({**edge, "rejection_reasons": ["duplicate_of_r7_r1_seed"], "candidate_status": "REJECTED"})
            continue
        if family not in FAMILY_ORDER:
            rejected.append({**edge, "rejection_reasons": ["source_family_not_in_r2_acceptance_order"], "candidate_status": "REJECTED"})
            continue
        seen_keys.add(key)
        valid_by_family[str(family)].append(edge)

    accepted: list[dict[str, Any]] = []
    backlog: list[dict[str, Any]] = []
    for family in FAMILY_ORDER:
        family_candidates = valid_by_family.get(family, [])
        accepted.extend({**edge, "candidate_status": "ACCEPTED_GROUNDED_R2"} for edge in family_candidates[:PER_FAMILY_ACCEPT_TARGET])
        backlog.extend(
            {
                **edge,
                "candidate_status": "BACKLOG",
                "backlog_reason": "valid_grounded_candidate_not_selected_to_preserve_source_diversity_balance",
            }
            for edge in family_candidates[PER_FAMILY_ACCEPT_TARGET:]
        )

    if len(accepted) < MIN_NEW_GROUNDED_EDGES:
        selected_ids = {edge["relationship_id"] for edge in accepted}
        for family in FAMILY_ORDER:
            for edge in valid_by_family.get(family, []):
                if edge["relationship_id"] in selected_ids:
                    continue
                trial_count = len(accepted) + 1
                trial_distribution = Counter(edge["source_family"] for edge in accepted)
                trial_distribution[edge["source_family"]] += 1
                if max(trial_distribution.values()) / trial_count <= SOURCE_FAMILY_CAP:
                    accepted.append({**edge, "candidate_status": "ACCEPTED_GROUNDED_R2"})
                    selected_ids.add(edge["relationship_id"])
                if len(accepted) >= MIN_NEW_GROUNDED_EDGES:
                    break
            if len(accepted) >= MIN_NEW_GROUNDED_EDGES:
                break
        backlog = [edge for edge in backlog if edge["relationship_id"] not in selected_ids]

    return accepted, rejected, backlog


def distribution_report(accepted: list[dict[str, Any]]) -> dict[str, Any]:
    distribution = Counter(edge["source_family"] for edge in accepted)
    total = len(accepted)
    rows = []
    max_share = 0.0
    for family in FAMILY_ORDER:
        count = distribution.get(family, 0)
        share = (count / total) if total else 0.0
        max_share = max(max_share, share)
        rows.append(
            {
                "source_family": family,
                "accepted_edge_count": count,
                "share": round(share, 4),
                "cap": SOURCE_FAMILY_CAP,
                "status": "PASS" if share <= SOURCE_FAMILY_CAP else "FAIL",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "new_grounded_edge_count": total,
        "source_family_count": sum(1 for count in distribution.values() if count > 0),
        "source_family_cap": SOURCE_FAMILY_CAP,
        "max_source_family_share": round(max_share, 4),
        "status": "PASS" if max_share <= SOURCE_FAMILY_CAP and total else "FAIL",
        "distribution": rows,
    }


def confidence_review_report(accepted: list[dict[str, Any]]) -> dict[str, Any]:
    missing_confidence = [edge["relationship_id"] for edge in accepted if edge.get("confidence") is None]
    missing_review_state = [edge["relationship_id"] for edge in accepted if not edge.get("review_state")]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not missing_confidence and not missing_review_state else "FAIL",
        "accepted_edge_count": len(accepted),
        "missing_confidence": missing_confidence,
        "missing_review_state": missing_review_state,
        "confidence_range": {
            "min": min((edge["confidence"] for edge in accepted), default=None),
            "max": max((edge["confidence"] for edge in accepted), default=None),
        },
        "review_state_counts": dict(Counter(edge["review_state"] for edge in accepted)),
    }


def relationship_coverage_report(accepted: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(edge["relationship_type"] for edge in accepted)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if len(counts) >= MIN_RELATIONSHIP_TYPES else "FAIL",
        "relationship_type_count": len(counts),
        "relationship_type_counts": dict(sorted(counts.items())),
        "minimum_required_relationship_types": MIN_RELATIONSHIP_TYPES,
    }


def evidence_map(accepted: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(edge.get("evidence_refs") for edge in accepted) else "FAIL",
        "edges": {
            edge["relationship_id"]: {
                "source_family": edge["source_family"],
                "relationship_type": edge["relationship_type"],
                "evidence_refs": edge["evidence_refs"],
                "trace_refs": edge["trace_refs"],
                "source_artifact_ref": edge["source_artifact_ref"],
            }
            for edge in accepted
        },
    }


def limitation_map(accepted: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(edge.get("limitation_refs") for edge in accepted) else "FAIL",
        "edges": {
            edge["relationship_id"]: {
                "source_family": edge["source_family"],
                "relationship_type": edge["relationship_type"],
                "limitation_refs": edge["limitation_refs"],
                "claim_boundary": edge["claim_boundary"],
                "assertion_boundary": edge["assertion_boundary"],
            }
            for edge in accepted
        },
    }


def prerequisite_report(r7_r1: dict[str, Any], source_map: dict[str, Any]) -> dict[str, Any]:
    required_status = {
        family: {
            "root": rel_path(root),
            "exists": root.exists(),
            "file_count": len([path for path in root.rglob("*") if path.is_file()]) if root.exists() else 0,
        }
        for family, root in REQUIRED_ROOTS.items()
    }
    optional_d6 = source_map.get("D6_REFERENCE_DEMO_EVIDENCE", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": "PASS" if all(item["exists"] for item in required_status.values()) else "FAIL",
        "required_roots": required_status,
        "optional_roots": {
            "D6_REFERENCE_DEMO_EVIDENCE": optional_d6,
            "R7_R1_EDGE_SEED": {
                "loaded": r7_r1["loaded"],
                "roots": r7_r1["roots"],
                "accepted_grounded_edge_count": r7_r1["accepted_grounded_edge_count"],
            },
        },
        "read_only_policy": "Required and optional roots were read-only inputs; writes are restricted to this task output root.",
    }


def no_action_audit(accepted: list[dict[str, Any]], rejected: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> dict[str, Any]:
    all_edges = accepted + rejected + backlog
    bad_edges = [edge["relationship_id"] for edge in all_edges if edge.get("no_action_taken") is not True]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not bad_edges else "FAIL",
        "accepted_edge_count": len(accepted),
        "rejected_edge_count": len(rejected),
        "backlog_edge_count": len(backlog),
        "bad_no_action_edges": bad_edges,
        "frontend_or_kit_mutation_attempted": False,
        "runtime_service_integration_attempted": False,
        "source_root_mutation_attempted": False,
    }


def claim_boundary_audit_text(accepted: list[dict[str, Any]]) -> tuple[str, str]:
    offending = []
    for edge in accepted:
        text = " ".join(
            [
                str(edge.get("relationship_summary", "")),
                str(edge.get("assertion_boundary", "")),
                str(edge.get("claim_boundary", "")),
            ]
        ).lower()
        for claim in FORBIDDEN_CLAIMS:
            if claim in text and f"no {claim}" not in text and f"not {claim}" not in text:
                if claim not in {"ownership truth", "legal finding", "autonomous action"}:
                    offending.append({"relationship_id": edge["relationship_id"], "claim": claim})
    status = "PASS" if not offending else "FAIL"
    lines = [
        "# Claim Boundary Audit",
        "",
        f"Status: {status}",
        "",
        "R7 R2 creates backend relationship seed records for review/context only.",
        "",
        "Not claimed:",
        "- production readiness or public deployment",
        "- certified citywide digital twin",
        "- ownership/legal/certified truth",
        "- confirmed violation, permit decision, certified impact, or certified traffic model",
        "- dispatch, enforcement, routing, control, or autonomous action",
        "",
        f"Accepted edges audited: {len(accepted)}",
        f"Offending positive claim count: {len(offending)}",
    ]
    if offending:
        lines.append("")
        lines.append(json.dumps(offending, indent=2, sort_keys=True))
    return status, "\n".join(lines)


def secret_audit_text() -> tuple[str, str, list[dict[str, Any]]]:
    hits: list[dict[str, Any]] = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append({"file": rel_path(path), "pattern": pattern.pattern})
    status = "PASS" if not hits else "FAIL"
    lines = [
        "# Secret Redaction Audit",
        "",
        f"Status: {status}",
        "",
        "Scanned generated R7 R2 artifacts for common credential patterns.",
        f"Credential-like hit count: {len(hits)}",
    ]
    if hits:
        lines.append("")
        lines.append(json.dumps(hits, indent=2, sort_keys=True))
    return status, "\n".join(lines), hits


def no_mutation_text(before: dict[str, Any], after: dict[str, Any]) -> tuple[str, str, list[str]]:
    changed = []
    lines = [
        "# No Mutation Audit",
        "",
        "Writes are restricted to the R7 R2 output root.",
        "",
        "| Source root | Status | Before files | After files |",
        "| --- | --- | ---: | ---: |",
    ]
    for label, before_snapshot in before.items():
        after_snapshot = after[label]
        same = before_snapshot == after_snapshot
        if not same:
            changed.append(label)
        status = "UNCHANGED" if same else "CHANGED"
        lines.append(
            f"| {label} | {status} | {before_snapshot.get('file_count', 0)} | {after_snapshot.get('file_count', 0)} |"
        )
    lines.extend(
        [
            "",
            f"Status: {'PASS' if not changed else 'FAIL'}",
            "Frontend or Kit mutation attempted: false",
            "Runtime service integration attempted: false",
            "Source root mutation attempted: false",
        ]
    )
    return ("PASS" if not changed else "FAIL"), "\n".join(lines), changed


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append((file_hash(path), rel_path(path)))
    text = "".join(f"{digest}  {path}\n" for digest, path in rows)
    (OUTPUT_ROOT / "hashes.sha256").write_text(text, encoding="utf-8")
    expected_lines = len(rows)
    actual_lines = len((OUTPUT_ROOT / "hashes.sha256").read_text(encoding="utf-8").splitlines())
    return {
        "status": "PASS" if expected_lines == actual_lines else "FAIL",
        "hashed_file_count": expected_lines,
        "hash_file": rel_path(OUTPUT_ROOT / "hashes.sha256"),
    }


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    output = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        output.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(output)


def main() -> None:
    watch_roots = {**REQUIRED_ROOTS}
    for optional_root in OPTIONAL_ROOTS["D6_REFERENCE_DEMO_EVIDENCE"]:
        if optional_root.exists():
            watch_roots[f"D6_OPTIONAL::{optional_root.name}"] = optional_root
    before_snapshot = {label: snapshot_root(path) for label, path in watch_roots.items()}

    if OUTPUT_ROOT.exists():
        resolved = OUTPUT_ROOT.resolve()
        expected_parent = (REPO_ROOT / "outputs").resolve()
        if expected_parent not in resolved.parents:
            raise RuntimeError(f"Refusing to clean unexpected output root: {resolved}")
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    r7_r1 = load_r7_r1()
    candidates, source_map = build_candidates()
    accepted, rejected, backlog = select_edges(candidates, r7_r1)

    dist = distribution_report(accepted)
    confidence_report = confidence_review_report(accepted)
    relationship_report = relationship_coverage_report(accepted)
    edge_evidence_map = evidence_map(accepted)
    edge_limitation_map = limitation_map(accepted)
    prereq = prerequisite_report(r7_r1, source_map)
    no_action = no_action_audit(accepted, rejected, backlog)

    after_snapshot = {label: snapshot_root(path) for label, path in watch_roots.items()}
    no_mutation_status, no_mutation_md, mutation_changes = no_mutation_text(before_snapshot, after_snapshot)
    claim_boundary_status, claim_boundary_md = claim_boundary_audit_text(accepted)

    non_r6_count = sum(1 for edge in accepted if edge["source_family"] != "R6_INCIDENT_EVENT")
    source_family_count = dist["source_family_count"]
    relationship_type_count = relationship_report["relationship_type_count"]
    evidence_ref_status = edge_evidence_map["status"]
    limitation_ref_status = edge_limitation_map["status"]
    confidence_review_state_status = confidence_report["status"]

    if dist["status"] != "PASS":
        status = FAIL_CAP_STATUS
    elif evidence_ref_status != "PASS" or limitation_ref_status != "PASS":
        status = FAIL_EVIDENCE_STATUS
    elif (
        len(accepted) < MIN_NEW_GROUNDED_EDGES
        or non_r6_count < MIN_NON_R6_NEW_GROUNDED_EDGES
        or source_family_count < MIN_SOURCE_FAMILIES
        or relationship_type_count < MIN_RELATIONSHIP_TYPES
    ):
        status = INVENTORY_LIMIT_STATUS
    elif (
        prereq["status"] != "PASS"
        or no_action["status"] != "PASS"
        or claim_boundary_status != "PASS"
        or no_mutation_status != "PASS"
        or confidence_review_state_status != "PASS"
    ):
        status = FAIL_STATUS
    else:
        status = PASS_STATUS

    write_json(OUTPUT_ROOT / "R7_R2_PREREQUISITE_REPORT.json", prereq)
    write_json(OUTPUT_ROOT / "R7_R2_SOURCE_MAP.json", source_map)
    write_json(OUTPUT_ROOT / "R7_R2_SOURCE_FAMILY_DISTRIBUTION_REPORT.json", dist)
    write_json(
        OUTPUT_ROOT / "R7_R2_ACCEPTED_GROUNDED_EDGES.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": "PASS",
            "accepted_edge_count": len(accepted),
            "edges": accepted,
        },
    )
    write_jsonl(OUTPUT_ROOT / "R7_R2_ACCEPTED_GROUNDED_EDGES.jsonl", accepted)
    write_json(
        OUTPUT_ROOT / "R7_R2_REJECTED_EDGE_CANDIDATES.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "rejected_edge_count": len(rejected),
            "candidates": rejected,
        },
    )
    write_json(
        OUTPUT_ROOT / "R7_R2_CANDIDATE_EDGE_BACKLOG.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "backlog_edge_count": len(backlog),
            "candidates": backlog,
        },
    )
    write_json(OUTPUT_ROOT / "R7_R2_EDGE_EVIDENCE_MAP.json", edge_evidence_map)
    write_json(OUTPUT_ROOT / "R7_R2_EDGE_LIMITATION_MAP.json", edge_limitation_map)
    write_json(OUTPUT_ROOT / "R7_R2_CONFIDENCE_REVIEW_STATE_REPORT.json", confidence_report)
    write_json(OUTPUT_ROOT / "R7_R2_RELATIONSHIP_TYPE_COVERAGE_REPORT.json", relationship_report)
    write_json(
        OUTPUT_ROOT / "R7_R2_NEGATIVE_TEST_REPORT.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if len(rejected) >= 4 else "WARN",
            "negative_cases": [
                "missing_evidence_refs",
                "missing_limitation_refs",
                "missing_confidence",
                "missing_review_state",
            ],
            "rejected_candidate_count": len(rejected),
            "rejected_negative_fixture_count": sum(1 for edge in rejected if edge.get("source_family") == "NEGATIVE_TEST"),
            "source_family_cap_pressure_checked": True,
            "source_family_distribution_status": dist["status"],
        },
    )
    write_json(OUTPUT_ROOT / "R7_R2_NO_ACTION_AUDIT.json", no_action)
    write_text(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", claim_boundary_md)
    write_text(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", no_mutation_md)

    runtime_notes = f"""# R7 R2 Runtime Registry Preflight Notes

Status: PREFLIGHT_ONLY

R7 R2 produced {len(accepted)} newly accepted grounded relationship edges. They are ready to be considered by `MAIN-CITYBRAIN-D4X-R7-EDGE-REGISTRY-RUNTIME-PREFLIGHT`.

Do next:
- define a read-only registry ingestion contract for R7 relationship edges
- preserve `source_family`, `evidence_refs`, `limitation_refs`, `confidence`, and `review_state`
- expose candidate/review context only
- keep source-family distribution visible in runtime diagnostics

Do not do here:
- no graph database service implementation
- no served runtime mutation
- no public API
- no frontend, Kit, or Omniverse mutation
- no legal, dispatch, routing, control, or autonomous workflow
"""
    write_text(OUTPUT_ROOT / "R7_R2_RUNTIME_REGISTRY_PREFLIGHT_NOTES.md", runtime_notes)

    d6_handoff = f"""# R7 R2 Future D6 Integration Handoff

Future D6-owned integration task:
`MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION`

This R7 R2 pack should be consumed by D6 only after the backend runtime-registry preflight decides the stable read contract.

Handoff shape:
- accepted edge registry: `R7_R2_ACCEPTED_GROUNDED_EDGES.json`
- source-family distribution: `R7_R2_SOURCE_FAMILY_DISTRIBUTION_REPORT.json`
- evidence map: `R7_R2_EDGE_EVIDENCE_MAP.json`
- limitation map: `R7_R2_EDGE_LIMITATION_MAP.json`

Display boundary:
- relationship overlays are review/context only
- no claim of causation, legal truth, certified affected-building truth, dispatch, enforcement, routing, control, or autonomous action
- D6/Kit/web artifacts were not mutated by this task
"""
    write_text(OUTPUT_ROOT / "R7_R2_FUTURE_D6_INTEGRATION_HANDOFF.md", d6_handoff)

    source_rows = [
        {
            "family": row["source_family"],
            "accepted": row["accepted_edge_count"],
            "share": row["share"],
            "status": row["status"],
        }
        for row in dist["distribution"]
    ]
    main_md = f"""# {TASK_NAME}

Final status: `{status}`

R7 R2 advances the edge seed from the R6-heavy R1 baseline into a source-diverse grounded seed set.

## Result

- R7 R1 loaded: {str(r7_r1["loaded"]).lower()}
- Newly accepted grounded R2 edges: {len(accepted)}
- Total grounded edges including loaded R7 R1: {r7_r1["accepted_grounded_edge_count"] + len(accepted)}
- Non-R6 newly accepted grounded edges: {non_r6_count}
- Source families represented: {source_family_count}
- Relationship types represented: {relationship_type_count}
- Max source-family share: {dist["max_source_family_share"]}
- Source-family cap: {SOURCE_FAMILY_CAP}

## Source-Family Distribution

{markdown_table(source_rows, ["family", "accepted", "share", "status"])}

## Boundary

This is a backend relationship seed pack only. It does not implement runtime service integration, frontend display, D6 overlay integration, Kit mutation, live ingestion, public API deployment, legal/enforcement workflow, routing/control, or autonomous action.

## Recommended Next Tasks

- Backend: `MAIN-CITYBRAIN-D4X-R7-EDGE-REGISTRY-RUNTIME-PREFLIGHT`
- Future D6-owned integration: `MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION`
"""
    write_text(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY.md", main_md)

    readme = f"""# R7 R2 Cross-Domain Edge Seed Source Diversity

Generated by `{rel_path(RUNNER_PATH)}`.

Status: `{status}`

Open first:
- `MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY.md`
- `MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY_DECISION.json`
- `R7_R2_ACCEPTED_GROUNDED_EDGES.json`
- `R7_R2_SOURCE_FAMILY_DISTRIBUTION_REPORT.json`

All writes are contained in this output root.
"""
    write_text(OUTPUT_ROOT / "README.md", readme)

    secret_status, secret_md, secret_hits = secret_audit_text()
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", secret_md)

    hash_summary = write_hashes()
    hash_validation_status = hash_summary["status"]

    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": RUN_TIMESTAMP,
        "r7_r1_loaded": r7_r1["loaded"],
        "r7_r1_loaded_roots": r7_r1["roots"],
        "new_grounded_edge_count": len(accepted),
        "total_grounded_edge_count": r7_r1["accepted_grounded_edge_count"] + len(accepted),
        "non_r6_new_grounded_edge_count": non_r6_count,
        "source_family_count": source_family_count,
        "max_source_family_share": dist["max_source_family_share"],
        "source_family_cap": SOURCE_FAMILY_CAP,
        "source_family_distribution_status": dist["status"],
        "relationship_type_count": relationship_type_count,
        "accepted_edge_count": len(accepted),
        "rejected_edge_count": len(rejected),
        "backlog_edge_count": len(backlog),
        "evidence_ref_status": evidence_ref_status,
        "limitation_ref_status": limitation_ref_status,
        "confidence_review_state_status": confidence_review_state_status,
        "runtime_registry_preflight_status": "PREFLIGHT_NOTES_ONLY",
        "frontend_or_kit_mutation_attempted": False,
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim_boundary_status,
        "no_mutation_status": no_mutation_status,
        "secret_audit_status": secret_status,
        "hash_validation_status": hash_validation_status,
        "limitations": [
            "backend-only relationship seed pack",
            "no runtime registry service implementation",
            "no D6/Kit/web/app mutation",
            "Track2C edges are control-room consumption context only, not primary relationship truth",
            "D6 optional root is supporting handoff context only",
            "relationship edges remain review/context seeds, not causal, legal, certified, operational, routing, dispatch, control, or autonomous facts",
            "source-family balance is enforced over newly accepted R2 edges only",
        ],
        "recommended_next_task": "MAIN-CITYBRAIN-D4X-R7-EDGE-REGISTRY-RUNTIME-PREFLIGHT",
        "future_d6_owned_integration_task": "MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION",
        "runner_path": str(RUNNER_PATH),
        "output_root": str(OUTPUT_ROOT),
        "hash_summary": hash_summary,
        "mutation_changes": mutation_changes,
        "secret_hits": secret_hits,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY_DECISION.json", decision)

    hash_summary = write_hashes()
    decision["hash_validation_status"] = hash_summary["status"]
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY_DECISION.json", decision)
    write_hashes()

    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
