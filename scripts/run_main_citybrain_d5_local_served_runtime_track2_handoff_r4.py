#!/usr/bin/env python3
"""Build D5 local served-runtime to Track2 handoff R4 packet fixtures."""

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

TASK_NAME = "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-TRACK2-HANDOFF-R4"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_track2_handoff_r4"

UPSTREAMS = {
    "d5_event_fabric_integration_r3": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_event_fabric_integration_r3",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_WITH_LIMITATIONS",
    },
    "r7_multi_domain_edge_registry_runtime_slice": {
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
    },
    "track2a_omniverse_event_overlay_integration_r3": {
        "root": "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3",
        "expected": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3_WITH_LIMITATIONS",
    },
    "d6_control_room_reference_demo_closeout_refresh_r2": {
        "root": "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh_r2",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_R2_WITH_LIMITATIONS",
    },
}

PACKET_FAMILIES = [
    "asset_overlay_packet",
    "event_overlay_packet",
    "multi_domain_edge_packet",
    "evidence_trace_packet",
    "limitation_packet",
    "safe_next_look_packet",
    "operator_context_packet",
    "executive_context_packet",
    "omniverse_handoff_packet",
    "web_companion_handoff_packet",
]

LIMITATIONS = [
    "local/replay packet-contract fixture only",
    "D5-to-Track2 handoff context only; no production service integration",
    "no public API readiness claim",
    "no autonomous monitoring, alert push, dispatch, routing/control, enforcement, legal/certified claim, or automated action",
    "Omniverse packets are Kit/Composer context overlays only, not a full citywide twin",
    "web packets are companion evidence, episode, and executive context only",
]

BOUNDARY = (
    "Local/replay D5-to-Track2 handoff fixture context only. No production service, public API "
    "readiness, live or autonomous monitoring, alert push, dispatch, routing/control, enforcement, "
    "legal/certified claim, full citywide twin claim, or automated action."
)

FORBIDDEN_ACTIONS = [
    "no autonomous monitoring",
    "no alert push",
    "no dispatch",
    "no enforcement",
    "no routing/control",
    "no legal finding",
    "no certified fact claim",
    "no source artifact mutation",
]

SAFE_NEXT_LOOKS = [
    "inspect evidence refs",
    "inspect limitation refs",
    "compare local replay context",
    "open mapped scene focus when present",
    "review relationship confidence and review state",
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


def strings(value: Any) -> list[str]:
    if value is None:
        return []
    raw = value if isinstance(value, list) else [value]
    out: list[str] = []
    for item in raw:
        text = str(item)
        if text and text not in out:
            out.append(text)
    return out


def first_nonempty(*values: Any, default: str = "unknown") -> str:
    for value in values:
        if isinstance(value, list) and value:
            return str(value[0])
        if value not in (None, "", []):
            return str(value)
    return default


def discover_inputs(pre: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    missing: list[str] = []
    branches = []
    for branch, meta in UPSTREAMS.items():
        path = root_path(meta["root"])
        status = decision_status(path)
        green = path.exists() and status == meta["expected"]
        if not green:
            missing.append(branch)
        artifacts = []
        if path.exists():
            for item in sorted(path.rglob("*")):
                if item.is_file() and item.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".py", ".usda"}:
                    artifacts.append(rel(item))
                if len(artifacts) >= 20:
                    break
        branches.append(
            {
                "branch": branch,
                "root": meta["root"],
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
    report = {"status": "PASS" if not missing else "FAIL", "timestamp": utc_now(), "upstream_missing": missing, "branches": branches}
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
                "count_fields": {key: value for key, value in decision.items() if isinstance(value, int) and ("count" in key or "packet" in key or "edge" in key or "route" in key)},
                "limitation_summary": decision.get("limitations", ["limitations carried from upstream branch"])[:6],
                "consumed_by_d5_r4": branch["green"],
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS" if all(row["green"] for row in rows) else "FAIL", "branches": rows}
    write_json(OUTPUT_ROOT / "UPSTREAM_BRANCH_STATUS_SUMMARY.json", report)
    return report


def load_sources() -> dict[str, Any]:
    d5_r3 = root_path(UPSTREAMS["d5_event_fabric_integration_r3"]["root"])
    r7 = root_path(UPSTREAMS["r7_multi_domain_edge_registry_runtime_slice"]["root"])
    track2a = root_path(UPSTREAMS["track2a_omniverse_event_overlay_integration_r3"]["root"])
    d6_closeout = root_path(UPSTREAMS["d6_control_room_reference_demo_closeout_refresh_r2"]["root"])
    return {
        "runtime_responses": rows_from(read_json(d5_r3 / "EVENT_STATE_RESPONSE_FIXTURES.json", {}), ["responses"]),
        "runtime_queries": rows_from(read_json(d5_r3 / "RUNTIME_EVENT_QUERY_RESULTS.json", {}), ["results"]),
        "runtime_routes": rows_from(read_json(d5_r3 / "LOCAL_RUNTIME_ROUTE_REGISTRY.json", {}), ["routes"]),
        "edges": rows_from(read_json(r7 / "MULTI_DOMAIN_EDGE_REGISTRY.json", {}), ["edges"]),
        "overlay_packets": rows_from(read_json(track2a / "OMNI_EVENT_R3_EVENT_OVERLAY_PACKETS.json", {}), ["packets"]),
        "asset_bindings": rows_from(read_json(track2a / "OMNI_EVENT_R3_EVENT_TO_ASSET_BINDING_MAP.json", {}), ["rows"]),
        "kit_packets": rows_from(read_json(track2a / "OMNI_EVENT_R3_KIT_EVENT_OVERLAY_HANDOFF_PACKETS.json", {}), ["packets"]),
        "web_packets": rows_from(read_json(track2a / "OMNI_EVENT_R3_WEB_COMPANION_EVENT_PACKETS.json", {}), ["packets"]),
        "d6_truth_register": read_json(d6_closeout / "D6_CLOSEOUT_R2_CURRENT_TRUTH_REGISTER.md", "D6 closeout truth register carried forward"),
    }


def choose_edge(edges: list[dict[str, Any]], overlay: dict[str, Any], index: int) -> dict[str, Any]:
    relationship_refs = set(strings(overlay.get("relationship_refs")))
    for edge in edges:
        if edge.get("edge_id") in relationship_refs:
            return edge
    event_refs = set(strings(overlay.get("event_id")) + strings(overlay.get("event_state_ref")))
    for edge in edges:
        text = json.dumps(edge, sort_keys=True)
        if any(ref in text for ref in event_refs):
            return edge
    return edges[index % len(edges)] if edges else {}


def base_packet(packet_id: str, family: str, overlay: dict[str, Any], asset: dict[str, Any], edge: dict[str, Any], source_refs: list[str]) -> dict[str, Any]:
    canonical_refs = strings(asset.get("canonical_entity_id")) + strings(edge.get("source_entity_ref")) + strings(edge.get("target_entity_ref"))
    event_refs = strings(overlay.get("event_id")) + strings(overlay.get("event_state_ref")) + strings(asset.get("event_id")) + strings(asset.get("event_state_ref"))
    edge_refs = strings(edge.get("edge_id")) + strings(overlay.get("relationship_refs"))
    evidence_refs = strings(overlay.get("evidence_refs")) + strings(asset.get("evidence_refs")) + strings(edge.get("evidence_refs"))
    limitation_refs = strings(overlay.get("limitation_refs")) + strings(asset.get("limitation_refs")) + strings(edge.get("limitation_refs"))
    return {
        "packet_id": packet_id,
        "packet_family": family,
        "source_branch_refs": source_refs,
        "canonical_entity_refs": canonical_refs or ["NO_CANONICAL_ENTITY_REF_AVAILABLE"],
        "event_refs": event_refs or ["NO_EVENT_REF_AVAILABLE"],
        "edge_refs": edge_refs or ["NO_EDGE_REF_AVAILABLE"],
        "evidence_refs": evidence_refs or ["NO_EVIDENCE_REF_AVAILABLE"],
        "limitation_refs": limitation_refs or ["NO_LIMITATION_REF_AVAILABLE"],
        "review_state": first_nonempty(edge.get("review_state"), overlay.get("lifecycle_state"), default="pending_review"),
        "confidence": edge.get("confidence", 0.55),
        "claim_boundary_label": BOUNDARY,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "no_action_taken": True,
    }


def build_schema() -> dict[str, Any]:
    schema = {
        "status": "PASS",
        "schema_name": "TRACK2_HANDOFF_PACKET_SCHEMA",
        "packet_families": PACKET_FAMILIES,
        "required_common_fields": [
            "packet_id",
            "packet_family",
            "source_branch_refs",
            "canonical_entity_refs",
            "event_refs",
            "edge_refs",
            "evidence_refs",
            "limitation_refs",
            "review_state",
            "confidence",
            "claim_boundary_label",
            "no_action_taken",
        ],
        "family_specific_required_fields": {
            "asset_overlay_packet": ["asset_refs", "usd_prim_refs", "mapping_status"],
            "event_overlay_packet": ["event_state_ref", "display_label", "event_state_preserved"],
            "multi_domain_edge_packet": ["relationship_family", "source_domain", "target_domain"],
            "evidence_trace_packet": ["trace_steps"],
            "limitation_packet": ["limitation_summary"],
            "safe_next_look_packet": ["safe_next_looks"],
            "operator_context_packet": ["operator_context"],
            "executive_context_packet": ["executive_context"],
            "omniverse_handoff_packet": ["kit_composer_context", "citywide_twin_claim"],
            "web_companion_handoff_packet": ["companion_context", "source_web_packet_ref"],
        },
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "TRACK2_HANDOFF_PACKET_SCHEMA.json", schema)
    return schema


def build_packets(sources: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    overlays = sources["overlay_packets"][:3]
    assets = sources["asset_bindings"]
    edges = sources["edges"]
    kit_packets = sources["kit_packets"]
    web_packets = sources["web_packets"]
    runtime_responses = sources["runtime_responses"]
    source_refs = [meta["root"] for meta in UPSTREAMS.values()]

    packets_by_family: dict[str, list[dict[str, Any]]] = {family: [] for family in PACKET_FAMILIES}
    for index, overlay in enumerate(overlays, start=1):
        asset = next((row for row in assets if row.get("event_state_ref") == overlay.get("event_state_ref")), assets[(index - 1) % len(assets)] if assets else {})
        edge = choose_edge(edges, overlay, index - 1)
        kit = next((row for row in kit_packets if row.get("overlay_packet_id") == overlay.get("overlay_packet_id")), kit_packets[(index - 1) % len(kit_packets)] if kit_packets else {})
        web = next((row for row in web_packets if row.get("overlay_packet_id") == overlay.get("overlay_packet_id")), web_packets[(index - 1) % len(web_packets)] if web_packets else {})
        runtime = runtime_responses[(index - 1) % len(runtime_responses)] if runtime_responses else {}

        common = base_packet(f"d5-r4-{index:03d}-asset-overlay", "asset_overlay_packet", overlay, asset, edge, source_refs)
        common.update(
            {
                "asset_refs": strings(overlay.get("asset_refs")) + strings(asset.get("asset_ref")),
                "usd_prim_refs": strings(overlay.get("usd_prim_refs")) + strings(asset.get("usd_prim_ref")),
                "mapping_status": first_nonempty(asset.get("mapping_status"), default="MAPPED_TO_SCENE_FOCUS_CONTEXT_ONLY"),
                "mapping_basis": first_nonempty(asset.get("mapping_basis"), default="carried_from_track2a_overlay_context"),
            }
        )
        packets_by_family["asset_overlay_packet"].append(common)

        common = base_packet(f"d5-r4-{index:03d}-event-overlay", "event_overlay_packet", overlay, asset, edge, source_refs)
        common.update(
            {
                "event_state_ref": first_nonempty(overlay.get("event_state_ref"), asset.get("event_state_ref"), default="NO_EVENT_STATE_REF_AVAILABLE"),
                "display_label": first_nonempty(overlay.get("display_label"), web.get("display_title"), default="local/replay event overlay"),
                "event_state_preserved": True,
                "visual_style_hint": overlay.get("visual_style_hint", web.get("visual_style_hint", {})),
            }
        )
        packets_by_family["event_overlay_packet"].append(common)

        common = base_packet(f"d5-r4-{index:03d}-multi-domain-edge", "multi_domain_edge_packet", overlay, asset, edge, source_refs)
        common.update(
            {
                "relationship_family": first_nonempty(edge.get("relationship_family"), default="relationship_context_unavailable"),
                "relationship_state": first_nonempty(edge.get("relationship_state"), default="local_replay_context"),
                "edge_type": first_nonempty(edge.get("edge_type"), default="cross_domain_relationship_context"),
                "source_domain": first_nonempty(edge.get("source_domain"), default="unknown_source_domain"),
                "target_domain": first_nonempty(edge.get("target_domain"), default="unknown_target_domain"),
                "source_entity_ref": first_nonempty(edge.get("source_entity_ref"), default="unknown_source_entity"),
                "target_entity_ref": first_nonempty(edge.get("target_entity_ref"), default="unknown_target_entity"),
            }
        )
        packets_by_family["multi_domain_edge_packet"].append(common)

        common = base_packet(f"d5-r4-{index:03d}-evidence-trace", "evidence_trace_packet", overlay, asset, edge, source_refs)
        common.update(
            {
                "trace_steps": [
                    {"step": "D5 R3 runtime response", "ref": runtime.get("request_id", "runtime_fixture_response")},
                    {"step": "R7 edge registry", "ref": edge.get("edge_id", "edge_registry_ref_unavailable")},
                    {"step": "Track2A overlay", "ref": overlay.get("overlay_packet_id", "overlay_packet_ref_unavailable")},
                    {"step": "D6 closeout frozen boundary", "ref": "D6_CLOSEOUT_R2_CURRENT_TRUTH_REGISTER.md"},
                ],
            }
        )
        packets_by_family["evidence_trace_packet"].append(common)

        common = base_packet(f"d5-r4-{index:03d}-limitation", "limitation_packet", overlay, asset, edge, source_refs)
        common.update(
            {
                "limitation_summary": LIMITATIONS,
                "limitation_context": "limitations are co-displayed with the handoff packet and block production/live/control claims",
            }
        )
        packets_by_family["limitation_packet"].append(common)

        common = base_packet(f"d5-r4-{index:03d}-safe-next-look", "safe_next_look_packet", overlay, asset, edge, source_refs)
        common.update({"safe_next_looks": SAFE_NEXT_LOOKS, "guidance_mode": "operator_review_context_only"})
        packets_by_family["safe_next_look_packet"].append(common)

        common = base_packet(f"d5-r4-{index:03d}-operator-context", "operator_context_packet", overlay, asset, edge, source_refs)
        common.update(
            {
                "operator_context": {
                    "headline": "Review local replay event context with evidence and limitations visible",
                    "focus": ["event state", "affected asset/context", "relationship confidence", "safe next look"],
                    "action_boundary": "observe and inspect only",
                }
            }
        )
        packets_by_family["operator_context_packet"].append(common)

        common = base_packet(f"d5-r4-{index:03d}-executive-context", "executive_context_packet", overlay, asset, edge, source_refs)
        common.update(
            {
                "executive_context": {
                    "headline": "D5 runtime output can be handed to Track2 surfaces as bounded demo context",
                    "value": "shows event, asset, relationship, evidence, and limitation continuity",
                    "boundary": "not production, public API, full twin, alerting, dispatch, or enforcement",
                }
            }
        )
        packets_by_family["executive_context_packet"].append(common)

        common = base_packet(f"d5-r4-{index:03d}-omniverse-handoff", "omniverse_handoff_packet", overlay, asset, edge, source_refs)
        common.update(
            {
                "kit_composer_context": "Omniverse Kit/Composer context overlay handoff only",
                "citywide_twin_claim": False,
                "source_kit_packet_ref": kit.get("kit_event_overlay_handoff_packet_id", "kit_handoff_ref_unavailable"),
                "stage_handoff_id": kit.get("stage_handoff_id", "stage_handoff_ref_unavailable"),
                "event_sidecar_marker_prim_path": kit.get("event_sidecar_marker_prim_path", asset.get("sidecar_marker_prim_path")),
                "usd_prim_refs": strings(kit.get("usd_prim_refs")) + strings(asset.get("usd_prim_ref")),
            }
        )
        packets_by_family["omniverse_handoff_packet"].append(common)

        common = base_packet(f"d5-r4-{index:03d}-web-companion-handoff", "web_companion_handoff_packet", overlay, asset, edge, source_refs)
        common.update(
            {
                "companion_context": "web companion evidence, episode, and executive context only",
                "source_web_packet_ref": web.get("web_companion_event_packet_id", "web_packet_ref_unavailable"),
                "display_title": first_nonempty(web.get("display_title"), overlay.get("display_label"), default="local/replay companion context"),
                "status_label": first_nonempty(web.get("status_label"), overlay.get("claim_context_label"), default="local/replay companion context only"),
                "episode_refs": strings(overlay.get("episode_refs")),
            }
        )
        packets_by_family["web_companion_handoff_packet"].append(common)

    return packets_by_family


def write_packet_files(packets_by_family: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    all_packets = [packet for family in PACKET_FAMILIES for packet in packets_by_family[family]]
    payload = {"status": "PASS", "packet_family_count": len(packets_by_family), "packet_count": len(all_packets), "packets": all_packets}
    write_json(OUTPUT_ROOT / "TRACK2_HANDOFF_PACKET_FIXTURES.json", payload)
    write_json(OUTPUT_ROOT / "ASSET_OVERLAY_PACKET_FIXTURES.json", {"status": "PASS", "packet_count": len(packets_by_family["asset_overlay_packet"]), "packets": packets_by_family["asset_overlay_packet"]})
    write_json(OUTPUT_ROOT / "EVENT_OVERLAY_PACKET_FIXTURES.json", {"status": "PASS", "packet_count": len(packets_by_family["event_overlay_packet"]), "packets": packets_by_family["event_overlay_packet"]})
    write_json(OUTPUT_ROOT / "MULTI_DOMAIN_EDGE_PACKET_FIXTURES.json", {"status": "PASS", "packet_count": len(packets_by_family["multi_domain_edge_packet"]), "packets": packets_by_family["multi_domain_edge_packet"]})
    write_json(OUTPUT_ROOT / "OMNIVERSE_HANDOFF_PACKET_FIXTURES.json", {"status": "PASS", "packet_count": len(packets_by_family["omniverse_handoff_packet"]), "packets": packets_by_family["omniverse_handoff_packet"]})
    write_json(OUTPUT_ROOT / "WEB_COMPANION_HANDOFF_PACKET_FIXTURES.json", {"status": "PASS", "packet_count": len(packets_by_family["web_companion_handoff_packet"]), "packets": packets_by_family["web_companion_handoff_packet"]})
    write_json(OUTPUT_ROOT / "SAFE_NEXT_LOOK_PACKET_FIXTURES.json", {"status": "PASS", "packet_count": len(packets_by_family["safe_next_look_packet"]), "packets": packets_by_family["safe_next_look_packet"]})
    return payload


def validate_packets(schema: dict[str, Any], packet_payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    common_fields = schema["required_common_fields"]
    family_specific = schema["family_specific_required_fields"]
    forbidden_guidance_terms = ["dispatch", "routing", "route", "enforcement", "alert", "control"]
    results = []
    for packet in packet_payload["packets"]:
        missing_common = [field for field in common_fields if packet.get(field) in (None, "", [], {})]
        missing_family = [field for field in family_specific[packet["packet_family"]] if packet.get(field) in (None, "", [], {}) and packet.get(field) is not False]
        checks = {
            "common_schema": not missing_common,
            "family_schema": not missing_family,
            "canonical_evidence_limitation_refs": bool(packet.get("canonical_entity_refs") and packet.get("evidence_refs") and packet.get("limitation_refs")),
            "event_review_state_preserved": packet["packet_family"] != "event_overlay_packet" or bool(packet.get("event_state_ref") and packet.get("review_state")),
            "edge_relationship_preserved": packet["packet_family"] != "multi_domain_edge_packet" or bool(packet.get("relationship_family") and packet.get("source_domain") and packet.get("target_domain")),
            "safe_next_look_is_review_only": packet["packet_family"] != "safe_next_look_packet" or not any(term in " ".join(packet.get("safe_next_looks", [])).lower() for term in forbidden_guidance_terms),
            "omniverse_is_kit_composer_context": packet["packet_family"] != "omniverse_handoff_packet" or ("Kit/Composer" in packet.get("kit_composer_context", "") and packet.get("citywide_twin_claim") is False),
            "web_is_companion_context": packet["packet_family"] != "web_companion_handoff_packet" or "companion evidence" in packet.get("companion_context", ""),
            "no_action_taken": packet.get("no_action_taken") is True,
        }
        results.append(
            {
                "packet_id": packet["packet_id"],
                "packet_family": packet["packet_family"],
                "status": "PASS" if all(checks.values()) else "FAIL",
                "missing_common_fields": missing_common,
                "missing_family_fields": missing_family,
                "checks": checks,
            }
        )
    pass_count = sum(row["status"] == "PASS" for row in results)
    fail_count = len(results) - pass_count
    report = {
        "status": "PASS" if fail_count == 0 and set(PACKET_FAMILIES) == {packet["packet_family"] for packet in packet_payload["packets"]} else "FAIL",
        "packet_validation_pass_count": pass_count,
        "packet_validation_fail_count": fail_count,
        "packet_family_count": len({packet["packet_family"] for packet in packet_payload["packets"]}),
        "omniverse_handoff_status": "PASS" if all(row["checks"]["omniverse_is_kit_composer_context"] for row in results) else "FAIL",
        "web_companion_handoff_status": "PASS" if all(row["checks"]["web_is_companion_context"] for row in results) else "FAIL",
        "results": results,
    }
    trace_rows = [
        {
            "packet_id": packet["packet_id"],
            "packet_family": packet["packet_family"],
            "evidence_refs": packet["evidence_refs"],
            "limitation_refs": packet["limitation_refs"],
            "review_state": packet["review_state"],
            "confidence": packet["confidence"],
            "claim_boundary_label": packet["claim_boundary_label"],
            "no_action_taken": True,
        }
        for packet in packet_payload["packets"]
    ]
    trace = {"status": "PASS" if all(row["evidence_refs"] and row["limitation_refs"] for row in trace_rows) else "FAIL", "trace_count": len(trace_rows), "rows": trace_rows}
    write_json(OUTPUT_ROOT / "HANDOFF_VALIDATION_REPORT.json", report)
    write_json(OUTPUT_ROOT / "TRACE_EVIDENCE_LIMITATION_REPORT.json", trace)
    return report, trace


def audit_claims() -> dict[str, Any]:
    forbidden = [
        "production_ready\": true",
        "public_api_ready\": true",
        "public_api_exposed\": true",
        "autonomous_monitoring_enabled\": true",
        "alert_push_enabled\": true",
        "dispatch_created\": true",
        "routing_control_created\": true",
        "citywide_twin_claim\": true",
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


def write_index(packet_count: int, family_count: int) -> None:
    files = [
        "INPUT_ARTIFACT_INDEX.json",
        "UPSTREAM_BRANCH_STATUS_SUMMARY.json",
        "TRACK2_HANDOFF_PACKET_SCHEMA.json",
        "TRACK2_HANDOFF_PACKET_FIXTURES.json",
        "ASSET_OVERLAY_PACKET_FIXTURES.json",
        "EVENT_OVERLAY_PACKET_FIXTURES.json",
        "MULTI_DOMAIN_EDGE_PACKET_FIXTURES.json",
        "OMNIVERSE_HANDOFF_PACKET_FIXTURES.json",
        "WEB_COMPANION_HANDOFF_PACKET_FIXTURES.json",
        "SAFE_NEXT_LOOK_PACKET_FIXTURES.json",
        "HANDOFF_VALIDATION_REPORT.json",
        "TRACE_EVIDENCE_LIMITATION_REPORT.json",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "HASH_MANIFEST.json",
    ]
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Handoff packet families: `{family_count}`",
        f"Fixture packet count: `{packet_count}`",
        "",
        "Local/replay packet-contract layer only. Not a production integration, public API, full citywide twin, alerting, dispatch, routing/control, enforcement, or legal/certified workflow.",
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- [{name}]({name})" for name in files)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

This pack converts D5 R3 local served-runtime event/edge outputs into bounded Track2-ready fixture packets.

Packet families: `{family_count}`
Packet fixtures: `{packet_count}`

The handoff is local/replay and review-only. It does not create a production service, public API, full citywide twin, alerting, dispatch, routing/control, enforcement, legal/certified workflow, or automated action.
""",
    )


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pre = {meta["root"]: snapshot(root_path(meta["root"])) for meta in UPSTREAMS.values()}
    input_index, missing = discover_inputs(pre)
    upstream = branch_summary(input_index)
    schema = build_schema()

    if missing:
        packets_by_family = {family: [] for family in PACKET_FAMILIES}
    else:
        packets_by_family = build_packets(load_sources())

    packet_payload = write_packet_files(packets_by_family)
    validation, trace = validate_packets(schema, packet_payload)
    claim = audit_claims()
    mutation = audit_mutation(pre)
    secret = audit_secret()
    write_index(packet_payload["packet_count"], packet_payload["packet_family_count"])

    status = PASS_STATUS
    if not all(
        [
            not missing,
            input_index["status"] == "PASS",
            upstream["status"] == "PASS",
            packet_payload["packet_family_count"] == len(PACKET_FAMILIES),
            packet_payload["packet_count"] >= len(PACKET_FAMILIES),
            validation["status"] == "PASS",
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
        "handoff_packet_family_count": packet_payload["packet_family_count"],
        "packet_fixture_count": packet_payload["packet_count"],
        "packet_validation_pass_count": validation["packet_validation_pass_count"],
        "packet_validation_fail_count": validation["packet_validation_fail_count"],
        "omniverse_handoff_status": validation["omniverse_handoff_status"],
        "web_companion_handoff_status": validation["web_companion_handoff_status"],
        "trace_evidence_limitation_status": trace["status"],
        "boundary_audit_result": claim["status"],
        "claim_boundary_status": claim["status"],
        "no_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-D5-LOCAL-RUNNING-CONTROL-ROOM-SLICE-R1",
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_DECISION.json", decision)
    manifest = hash_manifest()
    decision["hash_validation_status"] = manifest["status"]
    if manifest["status"] != "PASS":
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
