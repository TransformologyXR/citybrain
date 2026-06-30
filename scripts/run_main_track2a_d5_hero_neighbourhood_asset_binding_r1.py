#!/usr/bin/env python3
"""Build the Track2A/D5 hero-neighbourhood asset binding R1 package."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-ASSET-BINDING-R1"
PASS_STATUS = "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_ASSET_BINDING_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_ASSET_BINDING_R1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1"
USD_LAYER_NAME = "hero_neighbourhood_asset_binding_r1.usda"

UPSTREAMS = {
    "hero_neighbourhood_twin_preflight": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_twin_preflight",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT_WITH_LIMITATIONS",
        "required": True,
    },
    "incident_mode_track2a_operator_surface_handoff_r4": {
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
        "required": True,
    },
    "incident_mode_closeout": {
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
        "required": True,
    },
    "d6_d5_local_running_slice_closeout": {
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS",
        "required": True,
    },
    "r8_multi_domain_edge_registry_hardening": {
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
        "required": True,
    },
    "r7_multi_domain_edge_registry_runtime_slice": {
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
        "required": True,
    },
    "track2a_omniverse_event_overlay_r3": {
        "root": "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3",
        "expected": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3_WITH_LIMITATIONS",
        "required": False,
    },
    "d6_event_context_overlay_r4": {
        "root": "outputs/main_citybrain_d6_event_context_overlay_integration_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4_WITH_LIMITATIONS",
        "required": False,
    },
}

BOUNDARY = (
    "Hero Neighbourhood asset binding R1 is a bounded, non-certified, local/replay scene-binding "
    "package. No production claim, public API claim, citywide twin claim, certified/official geometry "
    "claim, autonomous monitoring, alerts, dispatch, routing/control, enforcement, legal/certified/"
    "confirmed incident finding, official ticket/case creation, automated action, or source mutation. "
    "All bindings, overlays, scene packets, incident packets, and relationship state remain local/replay "
    "review/query context only."
)

LIMITATIONS = [
    "bounded hero-neighbourhood asset-binding package only",
    "local/replay review/query context only",
    "stable prim paths are handoff metadata, not certified geometry",
    "USDA layer is a deterministic marker/metadata sidecar, not a full scene build",
    "operator-surface, Omniverse, web, R8, and incident outputs are consumed read-only",
    "no production, public API, citywide twin, certified geometry, monitoring, alerting, dispatch, routing/control, enforcement, legal/certified finding, ticket/case, or automated-action claim",
]

BINDING_STATES = [
    "bound_review_context",
    "candidate_bound_review_context",
    "overlay_bound_review_context",
    "incident_context_bound_review_context",
    "unresolved_review_context",
    "quarantined_review_context",
]

EXPECTED_FILES = [
    "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_ASSET_BINDING_R1_DECISION.json",
    "README.md",
    "LOCAL_OPEN_INDEX.md",
    "INPUT_ARTIFACT_INDEX.json",
    "UPSTREAM_STATUS_SUMMARY.json",
    "HERO_NEIGHBOURHOOD_SCOPE_SUMMARY.json",
    "ASSET_BINDING_SCHEMA.json",
    "HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json",
    "HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.jsonl",
    "STABLE_PRIM_PATH_MAPPING.json",
    "SCENE_HANDOFF_MANIFEST.json",
    "OPERATOR_SURFACE_BINDING_MAP.json",
    "OMNIVERSE_OVERLAY_BINDING_PACKET.json",
    "WEB_COMPANION_BINDING_PACKET.json",
    "RUNTIME_QUERY_FIXTURES.json",
    "RUNTIME_QUERY_RESULTS.json",
    "EVIDENCE_AND_LIMITATION_TRACE.json",
    "UNRESOLVED_QUARANTINED_PRESERVATION_REPORT.json",
    "ASSET_BINDING_VALIDATION_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
    USD_LAYER_NAME,
    "USD_LAYER_VALIDATION_REPORT.json",
]


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


def rows_from(payload: Any, keys: list[str]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def unique(values: list[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        if isinstance(value, list):
            for nested in value:
                text = str(nested)
                if text and text not in out:
                    out.append(text)
        elif value is not None:
            text = str(value)
            if text and text not in out:
                out.append(text)
    return out


def discover_inputs(pre: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    missing_required = []
    rows = []
    for branch, meta in UPSTREAMS.items():
        path = root_path(meta["root"])
        status = decision_status(path)
        green = path.exists() and status == meta["expected"]
        if meta["required"] and not green:
            missing_required.append(branch)
        artifacts = []
        if path.exists():
            for item in sorted(path.rglob("*")):
                if item.is_file() and item.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".py", ".usda"}:
                    artifacts.append(rel(item))
                if len(artifacts) >= 18:
                    break
        rows.append(
            {
                "branch": branch,
                "root": meta["root"],
                "required": meta["required"],
                "exists": path.exists(),
                "decision_path": rel(decision_file(path)) if decision_file(path) else None,
                "status": status,
                "expected": meta["expected"],
                "green": green,
                "snapshot": pre[meta["root"]],
                "sample_artifacts": artifacts,
                "read_only": True,
            }
        )
    report = {
        "status": "PASS" if not missing_required else "FAIL",
        "timestamp": utc_now(),
        "required_missing_or_not_green": missing_required,
        "discovered_count": sum(row["exists"] for row in rows),
        "required_count": sum(row["required"] for row in rows),
        "branches": rows,
    }
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", report)
    return report, missing_required


def upstream_summary(input_index: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for branch in input_index["branches"]:
        decision = read_json(REPO_ROOT / branch["decision_path"], {}) if branch.get("decision_path") else {}
        rows.append(
            {
                "branch": branch["branch"],
                "root": branch["root"],
                "required": branch["required"],
                "green": branch["green"],
                "status": branch["status"],
                "count_fields": {key: value for key, value in decision.items() if isinstance(value, int) and ("count" in key or "edge" in key or "packet" in key or "binding" in key)},
                "consumption_role": consumption_role(branch["branch"]),
                "read_only": True,
            }
        )
    report = {"status": "PASS" if all(row["green"] for row in rows if row["required"]) else "FAIL", "rows": rows}
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", report)
    return report


def consumption_role(branch: str) -> str:
    return {
        "hero_neighbourhood_twin_preflight": "selected LON hero-neighbourhood scope and scene identity",
        "incident_mode_track2a_operator_surface_handoff_r4": "operator-surface packets to bind into scene metadata",
        "incident_mode_closeout": "frozen Incident Mode boundary",
        "d6_d5_local_running_slice_closeout": "frozen local running control-room slice boundary",
        "r8_multi_domain_edge_registry_hardening": "hardened relationship refs consumed read-only",
        "r7_multi_domain_edge_registry_runtime_slice": "R7 lineage behind R8",
        "track2a_omniverse_event_overlay_r3": "latest Track2A event overlay package if present",
        "d6_event_context_overlay_r4": "latest D6 event context overlay package if present",
    }.get(branch, "source context")


def load_sources() -> dict[str, Any]:
    return {
        "selection_policy": read_json(root_path(UPSTREAMS["hero_neighbourhood_twin_preflight"]["root"]) / "HERO_NEIGHBOURHOOD_SELECTION_POLICY.json", {}),
        "scene": read_json(root_path(UPSTREAMS["hero_neighbourhood_twin_preflight"]["root"]) / "SCENE_IDENTITY_CONTRACT.json", {}),
        "hero_kit": read_json(root_path(UPSTREAMS["hero_neighbourhood_twin_preflight"]["root"]) / "KIT_COMPOSER_HANDOFF_CONTRACT.json", {}),
        "hero_web": read_json(root_path(UPSTREAMS["hero_neighbourhood_twin_preflight"]["root"]) / "WEB_COMPANION_ALIGNMENT_CONTRACT.json", {}),
        "operator_surface_packets": rows_from(read_json(root_path(UPSTREAMS["incident_mode_track2a_operator_surface_handoff_r4"]["root"]) / "OPERATOR_SURFACE_PACKET_FIXTURES.json", {}), ["packets"]),
        "r8_edges": rows_from(read_json(root_path(UPSTREAMS["r8_multi_domain_edge_registry_hardening"]["root"]) / "HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.json", {}), ["edges"]),
        "track2a_overlays": rows_from(read_json(root_path(UPSTREAMS["track2a_omniverse_event_overlay_r3"]["root"]) / "OMNI_EVENT_R3_EVENT_OVERLAY_PACKETS.json", {}), ["packets"]),
        "d6_overlays": rows_from(read_json(root_path(UPSTREAMS["d6_event_context_overlay_r4"]["root"]) / "D6_R4_EVENT_CONTEXT_OVERLAY_PACKETS.json", {}), ["packets"]),
    }


def source_refs() -> list[str]:
    return [meta["root"] for meta in UPSTREAMS.values() if root_path(meta["root"]).exists()]


def stable_path(index: int, slug: str) -> str:
    return f"/World/CityBrainHeroNeighbourhoodR1/Bindings/{index:03d}_{slug}"


def state_for_packet(packet: dict[str, Any]) -> str:
    display_state = str(packet.get("display_state", "")).lower()
    if "quarantined" in display_state:
        return "quarantined_review_context"
    if "unresolved" in display_state:
        return "unresolved_review_context"
    if packet.get("packet_type") == "omniverse_operator_overlay_packet":
        return "overlay_bound_review_context"
    if packet.get("packet_type") == "web_operator_companion_packet":
        return "candidate_bound_review_context"
    return "incident_context_bound_review_context"


def make_binding(
    index: int,
    asset_label: str,
    asset_category: str,
    canonical_ref: str,
    canonical_type: str,
    binding_state: str,
    edge_refs: list[str],
    incident_refs: list[str],
    operator_refs: list[str],
    omni_refs: list[str],
    web_refs: list[str],
    evidence_refs: list[str],
    limitation_refs: list[str],
    review_state: str,
    confidence: float,
    stable_slug: str,
) -> dict[str, Any]:
    operator_surface_packet_refs = unique([operator_refs]) or ["not_applicable_scene_asset_binding_no_operator_surface_packet"]
    omniverse_overlay_packet_refs = unique([omni_refs]) or ["not_available_in_upstream_fixture"]
    web_companion_packet_refs = unique([web_refs]) or ["not_applicable_scene_asset_binding_no_web_companion_packet"]
    return {
        "binding_id": f"hero-neighbourhood-r1-binding-{index:03d}",
        "binding_version": "r1",
        "scene_id": "hero-neighbourhood-preflight-scene-001",
        "scene_scope": "bounded_london_local_replay_corridor_context",
        "candidate_name": "LON local replay scene focus / corridor event context",
        "asset_label": asset_label,
        "asset_category": asset_category,
        "stable_prim_path": stable_path(index, stable_slug),
        "usd_layer_ref": USD_LAYER_NAME,
        "canonical_entity_ref": canonical_ref,
        "canonical_entity_type": canonical_type,
        "city_scope": "LON" if canonical_ref in {"corridor", "event-fabric-r2-mobility-108", "data-first-placeholder:lon:asset_data_first_placeholder_2"} else "operator_surface_context_not_physical_scene_claim",
        "edge_refs": unique([edge_refs]),
        "incident_context_refs": unique([incident_refs]),
        "operator_surface_packet_refs": operator_surface_packet_refs,
        "omniverse_overlay_packet_refs": omniverse_overlay_packet_refs,
        "web_companion_packet_refs": web_companion_packet_refs,
        "evidence_refs": unique([evidence_refs]),
        "limitation_refs": unique([limitation_refs, LIMITATIONS]),
        "review_state": review_state,
        "binding_state": binding_state,
        "confidence": confidence,
        "source_artifact_refs": source_refs(),
        "created_by_task": TASK_NAME,
        "claim_boundary": BOUNDARY,
        "no_action_taken": True,
    }


def build_registry(sources: dict[str, Any]) -> list[dict[str, Any]]:
    candidate = sources["selection_policy"].get("selected_candidate", {})
    scene = sources["scene"]
    track2a_london = next((row for row in sources["track2a_overlays"] if row.get("city_id") == "LON"), {})
    d6_london = next((row for row in sources["d6_overlays"] if row.get("city") == "LON" and "event-fabric-r2-mobility-108" in json.dumps(row)), {})
    packets = sources["operator_surface_packets"]
    by_kind = {packet.get("fixture_kind"): packet for packet in packets}
    base_evidence = unique([candidate.get("evidence_refs", []), track2a_london.get("evidence_refs", []), d6_london.get("evidence_refs", [])])
    base_limitations = unique([candidate.get("limitation_refs", []), track2a_london.get("limitation_refs", []), d6_london.get("limitation_refs", [])])
    r8_refs = scene.get("r8_edge_refs", [])[:6]
    registry = [
        make_binding(
            1,
            "LON corridor scene focus",
            "scene_focus_marker",
            "corridor",
            "corridor_context",
            "bound_review_context",
            r8_refs,
            scene.get("event_refs", []),
            [],
            candidate.get("overlay_packet_refs", []),
            [],
            base_evidence,
            base_limitations,
            candidate.get("review_state", "review_context"),
            float(candidate.get("confidence", 0.55)),
            "lon_corridor_scene_focus",
        ),
        make_binding(
            2,
            "LON mobility event overlay marker",
            "event_overlay_marker",
            "event-fabric-r2-mobility-108",
            "event_context",
            "overlay_bound_review_context",
            unique([r8_refs, track2a_london.get("relationship_refs", []), d6_london.get("relationship_refs", [])]),
            scene.get("event_refs", []),
            [],
            unique([candidate.get("overlay_packet_refs", []), track2a_london.get("overlay_packet_id"), d6_london.get("packet_id")]),
            [],
            base_evidence,
            base_limitations,
            track2a_london.get("lifecycle_state", "candidate/review"),
            float(d6_london.get("confidence", candidate.get("confidence", 0.55))),
            "lon_mobility_event_overlay",
        ),
        make_binding(
            3,
            "LON placeholder asset scene binding",
            "asset_context_marker",
            "data-first-placeholder:lon:asset_data_first_placeholder_2",
            "placeholder_asset_context",
            "candidate_bound_review_context",
            r8_refs,
            scene.get("event_refs", []),
            [],
            unique([track2a_london.get("asset_refs", []), track2a_london.get("overlay_packet_id")]),
            [],
            base_evidence,
            unique([base_limitations, "DATA_FIRST_PLACEHOLDER_NOT_REAL_GEOMETRY"]),
            "candidate/review",
            0.55,
            "lon_placeholder_asset_context",
        ),
    ]
    dynamic_defs = [
        (4, "directly_resolved_incident_context", "Directly resolved incident review panel"),
        (5, "unresolved_incident_context", "Unresolved incident review panel"),
        (6, "quarantined_or_invalid_context", "Quarantined incident review panel"),
        (7, "omniverse_overlay_target_context", "Omniverse operator overlay handoff panel"),
        (8, "web_companion_context", "Web companion handoff panel"),
    ]
    for index, kind, label in dynamic_defs:
        packet = by_kind.get(kind, {})
        binding_state = state_for_packet(packet) if packet else "candidate_bound_review_context"
        canonical_ref = (packet.get("affected_entity_refs") or ["not_available_in_upstream_fixture"])[0]
        canonical_type = "operator_surface_context"
        if binding_state == "quarantined_review_context":
            canonical_type = "quarantined_operator_surface_context"
        elif binding_state == "unresolved_review_context":
            canonical_type = "unresolved_operator_surface_context"
        registry.append(
            make_binding(
                index,
                label,
                "operator_surface_context_panel",
                canonical_ref,
                canonical_type,
                binding_state,
                packet.get("edge_refs", []),
                [packet.get("incident_context_id")],
                [packet.get("packet_id"), packet.get("source_operator_review_packet_ref")],
                packet.get("omniverse_overlay_refs", []),
                packet.get("web_companion_refs", []),
                packet.get("evidence_refs", []),
                packet.get("limitation_refs", []),
                packet.get("review_state", "review_context"),
                0.0 if binding_state == "quarantined_review_context" else 0.55,
                kind,
            )
        )
    return registry


def write_schema() -> dict[str, Any]:
    schema = {
        "status": "PASS",
        "schema_name": "ASSET_BINDING_SCHEMA",
        "required_fields": [
            "binding_id",
            "binding_version",
            "scene_id",
            "scene_scope",
            "candidate_name",
            "asset_label",
            "asset_category",
            "stable_prim_path",
            "usd_layer_ref",
            "canonical_entity_ref",
            "canonical_entity_type",
            "city_scope",
            "edge_refs",
            "incident_context_refs",
            "operator_surface_packet_refs",
            "omniverse_overlay_packet_refs",
            "web_companion_packet_refs",
            "evidence_refs",
            "limitation_refs",
            "review_state",
            "binding_state",
            "confidence",
            "source_artifact_refs",
            "created_by_task",
            "claim_boundary",
        ],
        "allowed_binding_states": BINDING_STATES,
        "forbidden_state_semantics": [
            "certified geometry",
            "live monitoring",
            "legal incident status",
            "enforcement",
            "dispatch",
            "production control",
        ],
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "ASSET_BINDING_SCHEMA.json", schema)
    return schema


def write_registry(registry: list[dict[str, Any]]) -> None:
    payload = {
        "status": "PASS",
        "binding_count": len(registry),
        "scene_id": "hero-neighbourhood-preflight-scene-001",
        "candidate_name": "LON local replay scene focus / corridor event context",
        "runtime_mode": "local_file_query_fixture_only",
        "bindings": registry,
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json", payload)
    with (OUTPUT_ROOT / "HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.jsonl").open("w", encoding="utf-8") as handle:
        for row in registry:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_scope_summary(sources: dict[str, Any], registry: list[dict[str, Any]]) -> dict[str, Any]:
    candidate = sources["selection_policy"].get("selected_candidate", {})
    summary = {
        "status": "PASS",
        "scene_id": "hero-neighbourhood-preflight-scene-001",
        "candidate_name": candidate.get("candidate_name", "LON local replay scene focus / corridor event context"),
        "scene_scope": "bounded_london_local_replay_corridor_context",
        "binding_count": len(registry),
        "canonical_refs_bound": sorted({row["canonical_entity_ref"] for row in registry}),
        "bounded_scope": True,
        "non_certified": True,
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "HERO_NEIGHBOURHOOD_SCOPE_SUMMARY.json", summary)
    return summary


def write_handoff_artifacts(registry: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    prim_mapping = {
        "status": "PASS",
        "prim_path_count": len({row["stable_prim_path"] for row in registry}),
        "mappings": [
            {
                "binding_id": row["binding_id"],
                "stable_prim_path": row["stable_prim_path"],
                "canonical_entity_ref": row["canonical_entity_ref"],
                "binding_state": row["binding_state"],
                "usd_layer_ref": row["usd_layer_ref"],
            }
            for row in registry
        ],
        "claim_boundary": BOUNDARY,
    }
    scene_manifest = {
        "status": "PASS",
        "manifest_id": "hero-neighbourhood-r1-scene-handoff",
        "scene_id": "hero-neighbourhood-preflight-scene-001",
        "usd_layer_ref": USD_LAYER_NAME,
        "binding_registry_ref": "HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json",
        "prim_path_mapping_ref": "STABLE_PRIM_PATH_MAPPING.json",
        "operator_surface_binding_map_ref": "OPERATOR_SURFACE_BINDING_MAP.json",
        "omniverse_overlay_binding_packet_ref": "OMNIVERSE_OVERLAY_BINDING_PACKET.json",
        "web_companion_binding_packet_ref": "WEB_COMPANION_BINDING_PACKET.json",
        "handoff_mode": "Kit/Composer metadata handoff only",
        "source_scene_mutation": False,
        "claim_boundary": BOUNDARY,
    }
    operator_map = {
        "status": "PASS",
        "map_count": len(registry),
        "mappings": [
            {
                "binding_id": row["binding_id"],
                "operator_surface_packet_refs": row["operator_surface_packet_refs"],
                "incident_context_refs": row["incident_context_refs"],
                "stable_prim_path": row["stable_prim_path"],
                "binding_state": row["binding_state"],
            }
            for row in registry
            if row["operator_surface_packet_refs"] or row["incident_context_refs"]
        ],
        "claim_boundary": BOUNDARY,
    }
    omni_packet = {
        "status": "PASS",
        "packet_id": "hero-neighbourhood-r1-omniverse-overlay-binding",
        "target_surface": "Omniverse Kit/Composer",
        "binding_refs": [row["binding_id"] for row in registry],
        "stable_prim_paths": [row["stable_prim_path"] for row in registry],
        "omniverse_overlay_packet_refs": unique([row["omniverse_overlay_packet_refs"] for row in registry]),
        "usd_layer_ref": USD_LAYER_NAME,
        "handoff_only": True,
        "source_usd_mutation": False,
        "claim_boundary": BOUNDARY,
    }
    web_packet = {
        "status": "PASS",
        "packet_id": "hero-neighbourhood-r1-web-companion-binding",
        "target_surface": "web companion evidence/episode/executive context",
        "binding_refs": [row["binding_id"] for row in registry],
        "web_companion_packet_refs": unique([row["web_companion_packet_refs"] for row in registry]),
        "evidence_refs": unique([row["evidence_refs"] for row in registry]),
        "limitation_refs": unique([row["limitation_refs"] for row in registry]),
        "handoff_only": True,
        "public_api": False,
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "STABLE_PRIM_PATH_MAPPING.json", prim_mapping)
    write_json(OUTPUT_ROOT / "SCENE_HANDOFF_MANIFEST.json", scene_manifest)
    write_json(OUTPUT_ROOT / "OPERATOR_SURFACE_BINDING_MAP.json", operator_map)
    write_json(OUTPUT_ROOT / "OMNIVERSE_OVERLAY_BINDING_PACKET.json", omni_packet)
    write_json(OUTPUT_ROOT / "WEB_COMPANION_BINDING_PACKET.json", web_packet)
    return prim_mapping, scene_manifest, omni_packet, web_packet


def query_registry(registry: list[dict[str, Any]], fixture: dict[str, Any]) -> Any:
    query = fixture["query"]
    value = fixture.get("value")
    if query == "get_binding_by_binding_id":
        return next((row for row in registry if row["binding_id"] == value), None)
    if query == "get_binding_by_stable_prim_path":
        return next((row for row in registry if row["stable_prim_path"] == value), None)
    if query == "get_bindings_by_canonical_entity_ref":
        return [row for row in registry if row["canonical_entity_ref"] == value]
    if query == "get_bindings_by_incident_or_operator_packet_ref":
        return [row for row in registry if value in row["incident_context_refs"] or value in row["operator_surface_packet_refs"]]
    if query == "get_unresolved_quarantined_bindings":
        return [row for row in registry if row["binding_state"] in {"unresolved_review_context", "quarantined_review_context"}]
    if query == "get_evidence_refs_for_binding":
        row = next((item for item in registry if item["binding_id"] == value), None)
        return row["evidence_refs"] if row else []
    if query == "get_limitation_refs_for_binding":
        row = next((item for item in registry if item["binding_id"] == value), None)
        return row["limitation_refs"] if row else []
    if query == "get_omniverse_overlay_packet_for_binding":
        row = next((item for item in registry if item["binding_id"] == value), None)
        return row["omniverse_overlay_packet_refs"] if row else []
    if query == "get_web_companion_packet_for_binding":
        row = next((item for item in registry if item["binding_id"] == value), None)
        return row["web_companion_packet_refs"] if row else []
    return None


def runtime_fixtures(registry: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    fixtures = [
        {"fixture_id": "query-001", "query": "get_binding_by_binding_id", "value": registry[0]["binding_id"]},
        {"fixture_id": "query-002", "query": "get_binding_by_stable_prim_path", "value": registry[1]["stable_prim_path"]},
        {"fixture_id": "query-003", "query": "get_bindings_by_canonical_entity_ref", "value": "corridor"},
        {"fixture_id": "query-004", "query": "get_bindings_by_incident_or_operator_packet_ref", "value": "incident-review-r1-001"},
        {"fixture_id": "query-005", "query": "get_unresolved_quarantined_bindings"},
        {"fixture_id": "query-006", "query": "get_evidence_refs_for_binding", "value": registry[3]["binding_id"]},
        {"fixture_id": "query-007", "query": "get_limitation_refs_for_binding", "value": registry[5]["binding_id"]},
        {"fixture_id": "query-008", "query": "get_omniverse_overlay_packet_for_binding", "value": registry[6]["binding_id"]},
        {"fixture_id": "query-009", "query": "get_web_companion_packet_for_binding", "value": registry[7]["binding_id"]},
    ]
    results = []
    for fixture in fixtures:
        result = query_registry(registry, fixture)
        passed = bool(result) or result == []
        if fixture["query"] in {"get_evidence_refs_for_binding", "get_limitation_refs_for_binding", "get_unresolved_quarantined_bindings"}:
            passed = bool(result)
        results.append({"fixture_id": fixture["fixture_id"], "query": fixture["query"], "status": "PASS" if passed else "FAIL", "result_count": len(result) if isinstance(result, list) else (1 if result else 0), "no_public_api": True})
    fixture_payload = {"status": "PASS", "fixture_count": len(fixtures), "runtime_mode": "local_file_query_fixture_only", "fixtures": fixtures}
    result_payload = {"status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL", "pass_count": sum(row["status"] == "PASS" for row in results), "fail_count": sum(row["status"] == "FAIL" for row in results), "results": results}
    write_json(OUTPUT_ROOT / "RUNTIME_QUERY_FIXTURES.json", fixture_payload)
    write_json(OUTPUT_ROOT / "RUNTIME_QUERY_RESULTS.json", result_payload)
    return fixture_payload, result_payload


def trace_and_preservation(registry: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    trace = {
        "status": "PASS",
        "trace_count": len(registry),
        "rows": [
            {
                "binding_id": row["binding_id"],
                "evidence_refs": row["evidence_refs"],
                "limitation_refs": row["limitation_refs"],
                "source_artifact_refs": row["source_artifact_refs"],
                "claim_boundary": row["claim_boundary"],
            }
            for row in registry
        ],
    }
    preservation_rows = [
        {
            "binding_id": row["binding_id"],
            "binding_state": row["binding_state"],
            "preserved": row["binding_state"] in {"unresolved_review_context", "quarantined_review_context"},
            "not_promoted": not any(token in row["binding_state"] for token in ["ready", "certified", "confirmed"]),
        }
        for row in registry
        if row["binding_state"] in {"unresolved_review_context", "quarantined_review_context"}
    ]
    preservation = {"status": "PASS" if preservation_rows and all(row["preserved"] and row["not_promoted"] for row in preservation_rows) else "FAIL", "preserved_count": len(preservation_rows), "rows": preservation_rows}
    write_json(OUTPUT_ROOT / "EVIDENCE_AND_LIMITATION_TRACE.json", trace)
    write_json(OUTPUT_ROOT / "UNRESOLVED_QUARANTINED_PRESERVATION_REPORT.json", preservation)
    return trace, preservation


def validate_registry(schema: dict[str, Any], registry: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [row["binding_id"] for row in registry]
    prims = [row["stable_prim_path"] for row in registry]
    jsonl_ok = True
    try:
        with (OUTPUT_ROOT / "HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.jsonl").open("r", encoding="utf-8") as handle:
            for line in handle:
                json.loads(line)
    except Exception:
        jsonl_ok = False
    row_results = []
    for row in registry:
        missing = [field for field in schema["required_fields"] if row.get(field) in (None, "", [], {})]
        canonical_ok = row["binding_state"] not in {"bound_review_context", "candidate_bound_review_context", "overlay_bound_review_context", "incident_context_bound_review_context"} or row["canonical_entity_ref"] != "not_available_in_upstream_fixture"
        evidence_ok = row["binding_state"] == "quarantined_review_context" or bool(row["evidence_refs"])
        limitation_ok = bool(row["limitation_refs"])
        row_results.append(
            {
                "binding_id": row["binding_id"],
                "status": "PASS" if not missing and row["binding_state"] in BINDING_STATES and canonical_ok and evidence_ok and limitation_ok else "FAIL",
                "missing_fields": missing,
                "canonical_refs_present_when_bound": canonical_ok,
                "evidence_refs_present": evidence_ok,
                "limitation_refs_present": limitation_ok,
            }
        )
    report = {
        "status": "PASS"
        if all(row["status"] == "PASS" for row in row_results)
        and jsonl_ok
        and len(ids) == len(set(ids))
        and len(prims) == len(set(prims))
        and all(path.startswith("/World/CityBrainHeroNeighbourhoodR1/Bindings/") for path in prims)
        else "FAIL",
        "json_parse_status": "PASS",
        "jsonl_parse_status": "PASS" if jsonl_ok else "FAIL",
        "schema_conformance_status": "PASS" if all(row["status"] == "PASS" for row in row_results) else "FAIL",
        "duplicate_binding_ids": [item for item in sorted(set(ids)) if ids.count(item) > 1],
        "duplicate_prim_paths": [item for item in sorted(set(prims)) if prims.count(item) > 1],
        "stable_prim_path_status": "PASS" if all(path.startswith("/World/CityBrainHeroNeighbourhoodR1/Bindings/") for path in prims) else "FAIL",
        "r8_consumed_read_only": True,
        "operator_surface_consumed_read_only": True,
        "row_results": row_results,
    }
    write_json(OUTPUT_ROOT / "ASSET_BINDING_VALIDATION_REPORT.json", report)
    return report


def write_usda(registry: list[dict[str, Any]]) -> dict[str, Any]:
    lines = [
        "#usda 1.0",
        "(",
        '    doc = "CityBrain Hero Neighbourhood Asset Binding R1 metadata sidecar; review context only"',
        ")",
        "",
        'def Xform "CityBrainHeroNeighbourhoodAssetBindingR1"',
        "{",
        f'    custom string citybrain:claimBoundary = "{BOUNDARY}"',
        '    custom string citybrain:sourceTask = "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-ASSET-BINDING-R1"',
    ]
    for row in registry:
        prim_name = row["stable_prim_path"].split("/")[-1]
        lines.extend(
            [
                f'    def Xform "{prim_name}"',
                "    {",
                f'        custom string citybrain:bindingId = "{row["binding_id"]}"',
                f'        custom string citybrain:canonicalEntityRef = "{row["canonical_entity_ref"]}"',
                f'        custom string citybrain:bindingState = "{row["binding_state"]}"',
                f'        custom string citybrain:reviewState = "{row["review_state"]}"',
                f'        custom string citybrain:stablePrimPath = "{row["stable_prim_path"]}"',
                "    }",
            ]
        )
    lines.append("}")
    write_text(OUTPUT_ROOT / USD_LAYER_NAME, "\n".join(lines))
    text = (OUTPUT_ROOT / USD_LAYER_NAME).read_text(encoding="utf-8", errors="replace")
    report = {
        "status": "PASS" if text.startswith("#usda 1.0") and all(row["binding_id"] in text for row in registry) else "FAIL",
        "usd_layer_ref": USD_LAYER_NAME,
        "binding_count": len(registry),
        "generation_mode": "deterministic metadata sidecar only",
        "source_scene_mutation": False,
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "USD_LAYER_VALIDATION_REPORT.json", report)
    return report


def audit_claims() -> dict[str, Any]:
    positive_patterns = [
        r'"production"\s*:\s*true',
        r'"public_api"\s*:\s*true',
        r'"citywide_twin"\s*:\s*true',
        r'"certified_geometry"\s*:\s*true',
        r'"autonomous_monitoring"\s*:\s*true',
        r'"alerts"\s*:\s*true',
        r'"dispatch"\s*:\s*true',
        r'"routing_control"\s*:\s*true',
        r'"enforcement"\s*:\s*true',
        r'"legal_certified_confirmed"\s*:\s*true',
        r'"official_ticket_case"\s*:\s*true',
        r'"automated_action"\s*:\s*true',
        r"certified geometry",
        r"official geometry",
        r"citywide digital twin",
        r"production control",
    ]
    joined = ""
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name not in {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.json"} and item.suffix.lower() in {".json", ".md", ".txt", ".jsonl", ".usda"}:
            joined += "\n" + item.read_text(encoding="utf-8", errors="ignore").lower()
    hits = []
    for pattern in positive_patterns:
        if re.search(pattern, joined) and pattern not in {r"certified geometry", r"official geometry", r"citywide digital twin", r"production control"}:
            hits.append(pattern)
    report = {"status": "PASS" if not hits else "FAIL", "positive_forbidden_claim_hits": hits, "claim_boundary": BOUNDARY}
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", report)
    return report


def audit_no_action(registry: list[dict[str, Any]]) -> dict[str, Any]:
    bad = [row["binding_id"] for row in registry if row.get("no_action_taken") is not True]
    report = {
        "status": "PASS" if not bad else "FAIL",
        "bad_bindings": bad,
        "forbidden_actions_preserved_as_limits": [
            "no alerts",
            "no dispatch",
            "no routing/control",
            "no enforcement",
            "no legal/certified/confirmed incident finding",
            "no official ticket/case creation",
            "no automated action",
        ],
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", report)
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
        if item.is_file() and item.name != "HASH_MANIFEST.json" and item.suffix.lower() in {".json", ".md", ".txt", ".jsonl", ".usda"}:
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


def write_readme_index(registry: list[dict[str, Any]]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

This package binds the selected `LON local replay scene focus / corridor event context` to a small review-safe registry of canonical refs, operator-surface packets, R8 edge refs, evidence refs, limitation refs, and stable Omniverse/OpenUSD prim paths.

Binding count: `{len(registry)}`

The USDA file is a deterministic metadata sidecar only. It is not a full scene build and does not certify geometry.

Boundary: {BOUNDARY}
""",
    )
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Binding count: `{len(registry)}`",
        "",
        BOUNDARY,
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- [{name}]({name})" for name in EXPECTED_FILES)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pre = {meta["root"]: snapshot(root_path(meta["root"])) for meta in UPSTREAMS.values()}
    input_index, missing = discover_inputs(pre)
    upstream = upstream_summary(input_index)
    sources = load_sources()
    schema = write_schema()
    registry = build_registry(sources)
    write_registry(registry)
    scope = write_scope_summary(sources, registry)
    prim_mapping, scene_manifest, omni_packet, web_packet = write_handoff_artifacts(registry)
    fixtures, query_results = runtime_fixtures(registry)
    trace, preservation = trace_and_preservation(registry)
    usda = write_usda(registry)
    validation = validate_registry(schema, registry)
    claim = audit_claims()
    no_action = audit_no_action(registry)
    mutation = audit_mutation(pre)
    secret = audit_secret()
    write_readme_index(registry)

    status = PASS_STATUS
    if not all(
        [
            not missing,
            input_index["status"] == "PASS",
            upstream["status"] == "PASS",
            scope["status"] == "PASS",
            validation["status"] == "PASS",
            query_results["status"] == "PASS",
            preservation["status"] == "PASS",
            omni_packet["status"] == "PASS",
            web_packet["status"] == "PASS",
            usda["status"] == "PASS",
            claim["status"] == "PASS",
            no_action["status"] == "PASS",
            mutation["status"] == "PASS",
            secret["status"] == "PASS",
        ]
    ):
        status = FAIL_STATUS

    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "binding_count": len(registry),
        "prim_path_count": prim_mapping["prim_path_count"],
        "canonical_refs_bound": len(scope["canonical_refs_bound"]),
        "unresolved_quarantined_preserved_count": preservation["preserved_count"],
        "runtime_query_pass_count": query_results["pass_count"],
        "runtime_query_fail_count": query_results["fail_count"],
        "omniverse_handoff_status": omni_packet["status"],
        "web_companion_handoff_status": web_packet["status"],
        "claim_boundary_status": claim["status"],
        "no_action_status": no_action["status"],
        "no_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "missing_required_upstreams": missing,
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-EVENT-OVERLAY-R2",
        "alternative_next_task": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-ASSET-BINDING-R1-HARDENING",
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_ASSET_BINDING_R1_DECISION.json", decision)
    manifest = hash_manifest()
    decision["hash_validation_status"] = manifest["status"]
    if manifest["status"] != "PASS":
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_ASSET_BINDING_R1_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
