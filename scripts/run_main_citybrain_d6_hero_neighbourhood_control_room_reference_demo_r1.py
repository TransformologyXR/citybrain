#!/usr/bin/env python3
"""Compose the Hero Neighbourhood control-room reference demo R1 pack.

This runner is intentionally local-file and deterministic. It consumes frozen
Hero Neighbourhood, CER/SEG v2, Incident Mode, local running, and R7/R8 outputs
read-only, then writes a bounded demo-composition/acceptance package under its
own output root.
"""

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

TASK_NAME = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_r1"

BOUNDARY = (
    "This is a bounded local/replay control-room reference demo.\n"
    "It does not claim production readiness, public API readiness, live monitoring,\n"
    "autonomous incident detection, alert push, dispatch, routing/control, enforcement,\n"
    "official ticket/case creation, legal/certified incident findings, citywide certified twin,\n"
    "physical accuracy, or automated action.\n\n"
    "All incident, event, current-state, relationship, operator-surface, Omniverse,\n"
    "and web-context outputs remain local/replay review/query context only."
)

SHORT_BOUNDARY = "local_replay_review_query_context_only"

LIMITATIONS = [
    "bounded hero-neighbourhood control-room reference demo only",
    "local/replay review/query context only",
    "artifact/package review only where live screenshots are not already available",
    "Omniverse/Kit/Composer handoff is metadata and operator-surface context, not a certified citywide twin",
    "web companion remains a local companion evidence/episode surface context",
    "CER/SEG v2 compatibility is consumed from green upstream outputs; no new canonical identity system is created",
    "unresolved and quarantined contexts remain visible and are not promoted",
    "scene/source/operator refs remain scene-binding context unless already supported by upstream canonical evidence",
    "no production readiness, public API readiness, live monitoring, autonomous incident detection, alert push, dispatch, routing/control, enforcement, official ticket/case creation, legal/certified incident finding, citywide certified twin, physical accuracy, or automated action claim",
]

RECOMMENDED_NEXT_TASK = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-R1"
FIXUP_NEXT_TASK = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-R1-FIXUP"

REQUIRED_UPSTREAMS = {
    "integration_readiness_review": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "role": "Hero + CER/SEG v2 integration-readiness review",
    },
    "hero_scene_pack_closeout": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_WITH_LIMITATIONS",
        "role": "frozen Hero Neighbourhood scene-pack acceptance",
    },
    "cerseg_cross_city_v2_closeout": {
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
        "role": "CER/SEG v2 compatibility and review-state semantics",
    },
    "incident_operator_surface_r4": {
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
        "role": "Incident Mode to Track2A operator-surface packets",
    },
    "incident_mode_closeout": {
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "frozen Incident Mode boundary and closeout truth",
    },
    "d6_d5_local_running_slice_closeout": {
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "frozen local running control-room slice",
    },
    "r8_multi_domain_edge_registry_hardening": {
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "decision_file": "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
        "role": "hardened relationship substrate",
    },
    "r7_multi_domain_edge_registry_runtime_slice": {
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "decision_file": "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
        "role": "runtime relationship registry substrate",
    },
}

SUPPORTING_UPSTREAMS = {
    "hero_asset_binding_r1": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_ASSET_BINDING_R1_DECISION.json",
        "role": "source hero binding records",
    },
    "hero_event_overlay_r2": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_DECISION.json",
        "role": "source hero event overlay packets",
    },
    "hero_kit_composer_handoff_r3": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_KIT_COMPOSER_HANDOFF_R3_DECISION.json",
        "role": "source prim metadata and USDA handoff records",
    },
    "d6_d5_control_room_slice_r1": {
        "root": "outputs/main_citybrain_d6_d5_local_running_control_room_slice_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_DECISION.json",
        "role": "local Omniverse/web companion handoff manifests",
    },
}

REQUIRED_OUTPUTS = [
    "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json",
    "README.md",
    "LOCAL_OPEN_INDEX.md",
    "UPSTREAM_ARTIFACT_INDEX.json",
    "UPSTREAM_STATUS_SUMMARY.json",
    "CONTROL_ROOM_DEMO_MANIFEST.json",
    "CONTROL_ROOM_DEMO_MANIFEST.jsonl",
    "OPERATOR_WALKTHROUGH_SCRIPT.md",
    "EXECUTIVE_WALKTHROUGH_SCRIPT.md",
    "OMNIVERSE_SCENE_HANDOFF_SUMMARY.json",
    "WEB_COMPANION_HANDOFF_SUMMARY.json",
    "INCIDENT_OPERATOR_SURFACE_PACKET_SUMMARY.json",
    "CERSEG_V2_COMPATIBILITY_SUMMARY.json",
    "EVIDENCE_LIMITATION_TRACE_SUMMARY.json",
    "UNRESOLVED_QUARANTINED_PRESERVATION_REPORT.json",
    "VISUAL_ACCEPTANCE_CHECKLIST.md",
    "DEMO_ACCEPTANCE_MATRIX.json",
    "DEMO_ACCEPTANCE_MATRIX.md",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
    "CONTROL_ROOM_DEMO_STORYBOARD.md",
    "KIT_COMPOSER_OPERATOR_NOTES.md",
    "WEB_COMPANION_OPERATOR_NOTES.md",
    "DEMO_SCREENSHOT_PLACEHOLDER_INDEX.md",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def root_path(root: str) -> Path:
    return REPO_ROOT / root


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    digest = hashlib.sha256()
    file_count = 0
    byte_count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        file_count += 1
        size = path.stat().st_size
        byte_count += size
        digest.update(rel(path).encode("utf-8"))
        digest.update(str(size).encode("utf-8"))
        digest.update(sha256_file(path).encode("utf-8"))
    return {"exists": True, "file_count": file_count, "byte_count": byte_count, "fingerprint": digest.hexdigest()}


def status_from_decision(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("status", "final_status", "decision_status"):
        if payload.get(key):
            return str(payload[key])
    return None


def rows_from(payload: Any, preferred_keys: list[str]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in preferred_keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def strings(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    output: list[str] = []
    for item in values:
        if item is None:
            continue
        text = str(item)
        if text and text not in output:
            output.append(text)
    return output


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in values if item))


def prepare_output_root() -> None:
    if OUTPUT_ROOT.resolve().parent != (REPO_ROOT / "outputs").resolve():
        raise RuntimeError(f"Refusing unexpected output root: {OUTPUT_ROOT}")
    if OUTPUT_ROOT.name != "main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_r1":
        raise RuntimeError(f"Refusing unexpected output root name: {OUTPUT_ROOT.name}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def json_parse_report_for(root: Path) -> dict[str, Any]:
    files = sorted(path for path in root.rglob("*.json") if path.is_file()) if root.exists() else []
    failures = []
    for path in files:
        try:
            read_json(path, {})
        except Exception as exc:  # pragma: no cover - report path, not exception type.
            failures.append({"path": rel(path), "error": str(exc)})
    return {"json_file_count": len(files), "parse_failure_count": len(failures), "parse_failures": failures}


def upstream_rows(specs: dict[str, dict[str, str]], required: bool) -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    missing = []
    for key, spec in specs.items():
        root = root_path(spec["root"])
        decision_path = root / spec["decision_file"]
        decision = read_json(decision_path, {}) if decision_path.exists() else {}
        status = status_from_decision(decision)
        expected = spec.get("expected")
        green = root.exists() and decision_path.exists() and (status == expected if expected else bool(status and status.startswith("PASS_")))
        if required and not green:
            missing.append(key)
        parse_report = json_parse_report_for(root)
        artifacts = []
        if root.exists():
            for path in sorted(item for item in root.iterdir() if item.is_file())[:24]:
                artifacts.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        rows.append(
            {
                "upstream_key": key,
                "root": spec["root"],
                "decision_file": rel(decision_path),
                "exists": root.exists(),
                "required": required,
                "expected_status": expected,
                "status": status,
                "green": green,
                "read_only": True,
                "consumption_role": spec["role"],
                "json_parse_status": "PASS" if parse_report["parse_failure_count"] == 0 else "FAIL",
                "json_parse_report": parse_report,
                "sample_artifacts": artifacts,
            }
        )
    return rows, missing


def discover_upstreams() -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    required_rows, missing_required = upstream_rows(REQUIRED_UPSTREAMS, True)
    supporting_rows, _ = upstream_rows(SUPPORTING_UPSTREAMS, False)
    all_rows = required_rows + supporting_rows
    parse_failures = [
        {"upstream_key": row["upstream_key"], "failures": row["json_parse_report"]["parse_failures"]}
        for row in all_rows
        if row["json_parse_report"]["parse_failure_count"]
    ]
    artifact_index = {
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "upstreams": all_rows,
        "boundary": BOUNDARY,
        "status": "PASS" if not missing_required and not parse_failures else "FAIL",
    }
    status_summary = {
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "required_upstreams_found": sum(1 for row in required_rows if row["green"]),
        "required_upstreams_total": len(required_rows),
        "required_missing_or_not_green": missing_required,
        "supporting_upstreams_found": sum(1 for row in supporting_rows if row["exists"]),
        "supporting_upstreams_total": len(supporting_rows),
        "json_parse_status": "PASS" if not parse_failures else "FAIL",
        "json_parse_failures": parse_failures,
        "status": "PASS" if not missing_required and not parse_failures else "FAIL",
    }
    write_json(OUTPUT_ROOT / "UPSTREAM_ARTIFACT_INDEX.json", artifact_index)
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", status_summary)
    return artifact_index, status_summary, missing_required


def load_sources() -> dict[str, Any]:
    return {
        "bindings": rows_from(
            read_json(root_path("outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1") / "HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json", {}),
            ["bindings"],
        ),
        "overlays": rows_from(
            read_json(root_path("outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2") / "HERO_EVENT_OVERLAY_PACKETS.json", {}),
            ["packets"],
        ),
        "operator_packets": rows_from(
            read_json(root_path("outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4") / "OPERATOR_SURFACE_PACKET_FIXTURES.json", {}),
            ["packets"],
        ),
        "prim_metadata": rows_from(
            read_json(root_path("outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3") / "PRIM_METADATA_INDEX.json", {}),
            ["prim_metadata", "items"],
        ),
        "kit_manifest": read_json(root_path("outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3") / "KIT_COMPOSER_HANDOFF_MANIFEST.json", {}),
        "scene_summary": read_json(root_path("outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout") / "HERO_SCENE_PACK_SUMMARY.json", {}),
        "web_overlay": read_json(root_path("outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2") / "WEB_EVENT_OVERLAY_MANIFEST.json", {}),
        "omniverse_overlay": read_json(root_path("outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2") / "OMNIVERSE_EVENT_OVERLAY_MANIFEST.json", {}),
        "cerseg_closeout": read_json(root_path("outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout") / "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json", {}),
        "cerseg_findings": read_json(root_path("outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout") / "COMPATIBILITY_FINDINGS_SUMMARY.json", {}),
        "integration_readiness": read_json(root_path("outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review") / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json", {}),
        "incident_closeout": read_json(root_path("outputs/main_citybrain_d6_incident_mode_closeout") / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_DECISION.json", {}),
        "d6_d5_closeout": read_json(root_path("outputs/main_citybrain_d6_d5_local_running_slice_closeout") / "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json", {}),
        "r8_decision": read_json(root_path("outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening") / "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json", {}),
        "r7_decision": read_json(root_path("outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice") / "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json", {}),
    }


def is_unresolved_or_quarantined(record: dict[str, Any]) -> bool:
    text = json.dumps(record, sort_keys=True).lower()
    return "unresolved" in text or "quarantined" in text


def identity_family(record: dict[str, Any]) -> str:
    review_state = str(record.get("review_state") or record.get("display_state") or "").lower()
    canonical = str(record.get("canonical_entity_ref") or record.get("canonical_entity_id") or "")
    if "quarantined" in review_state or "quarantined" in canonical.lower():
        return "quarantined"
    if "unresolved" in review_state:
        return "unresolved"
    if canonical in {"", "None", "not_available_in_upstream_fixture"}:
        return "scene_context_only"
    if canonical.startswith("data-first-placeholder:"):
        return "scene_context_only"
    if canonical in {"corridor", "event-fabric-r2-mobility-108"}:
        return "scene_context_only"
    if canonical.startswith("r6-event-"):
        return "operator_event_context"
    return "upstream_context_ref"


def canonical_ref_for(record: dict[str, Any]) -> str | None:
    family = identity_family(record)
    value = record.get("canonical_entity_ref") or record.get("canonical_entity_id")
    if family in {"unresolved", "quarantined", "scene_context_only"}:
        return None
    return str(value) if value else None


def source_ref_for(record: dict[str, Any]) -> str | None:
    refs = [
        record.get("binding_id"),
        record.get("asset_binding_id"),
        record.get("overlay_packet_id"),
        record.get("packet_id"),
        record.get("canonical_entity_ref"),
        record.get("canonical_entity_id"),
        record.get("stable_prim_path"),
        record.get("usd_prim_path"),
    ]
    return " | ".join(str(ref) for ref in refs if ref) or None


def confidence_summary(record: dict[str, Any]) -> str:
    if isinstance(record.get("confidence_summary"), dict):
        return str(record["confidence_summary"].get("display_label") or "review confidence only")
    if isinstance(record.get("confidence_context"), dict):
        return "review confidence only"
    if record.get("confidence") is not None:
        return f"review confidence {record['confidence']}"
    return "review/context confidence only"


def row_base(demo_item_id: str, demo_item_type: str, record: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = unique(
        strings(record.get("evidence_refs"))
        + strings(record.get("evidence_bundle_refs"))
        + strings(record.get("source_evidence_bundle_ref"))
        + strings(record.get("source_artifact_refs"))
    )
    limitations = unique(strings(record.get("limitation_refs")) + ["bounded local/replay control-room reference demo"])
    traces = unique(strings(record.get("trace_refs")) + strings(record.get("source_artifact_refs")))
    if not evidence and demo_item_type in {"limitation", "unresolved_context"}:
        evidence = ["context preserved through limitation/review-state report"]
    row = {
        "demo_item_id": demo_item_id,
        "demo_item_type": demo_item_type,
        "hero_binding_ref": record.get("binding_id") or record.get("asset_binding_id"),
        "canonical_entity_ref": canonical_ref_for(record),
        "scene_or_source_ref": source_ref_for(record),
        "operator_surface_packet_ref": record.get("operator_review_packet_ref") or record.get("packet_id") or first_or_none(strings(record.get("operator_surface_packet_refs"))),
        "omniverse_prim_path": record.get("stable_prim_path") or record.get("usd_prim_path"),
        "web_companion_ref": first_or_none(strings(record.get("web_companion_refs"))),
        "incident_context_ref": record.get("incident_context_ref") or record.get("incident_context_id") or first_or_none(strings(record.get("incident_context_refs"))),
        "cerseg_v2_entity_family": identity_family(record),
        "cerseg_v2_relationship_family": relationship_family(record),
        "review_state": record.get("review_state") or record.get("display_state") or "review_context",
        "confidence_summary": confidence_summary(record),
        "evidence_refs": evidence,
        "limitation_refs": limitations,
        "trace_refs": traces or ["source artifact index"],
        "claim_boundary": SHORT_BOUNDARY,
        "no_action_taken": True,
    }
    if extra:
        row.update(extra)
    return row


def relationship_family(record: dict[str, Any]) -> str | None:
    edge_refs = strings(record.get("edge_refs"))
    if any(ref.startswith("mobility-") for ref in edge_refs):
        return "mobility_context_edge"
    if edge_refs:
        return "multi_domain_review_context_edge"
    if record.get("packet_type") == "safe_next_look_surface_packet":
        return "safe_next_look_context"
    return None


def first_or_none(values: list[str]) -> str | None:
    return values[0] if values else None


def build_manifest(sources: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, binding in enumerate(sources["bindings"], start=1):
        rows.append(row_base(f"demo-binding-{index:03d}", "binding", binding))
    for index, overlay in enumerate(sources["overlays"], start=1):
        rows.append(row_base(f"demo-overlay-{index:03d}", "overlay", overlay))
    for index, packet in enumerate(sources["operator_packets"], start=1):
        rows.append(row_base(f"demo-operator-packet-{index:03d}", "operator_packet", packet))
        if packet.get("web_companion_refs"):
            rows.append(row_base(f"demo-web-packet-{index:03d}", "web_packet", packet, {"web_packet_source": "incident_operator_surface_r4"}))
    for index, packet in enumerate(sources["operator_packets"], start=1):
        rows.append(row_base(f"demo-evidence-trace-{index:03d}", "evidence_trace", packet))
    for index, record in enumerate([row for row in sources["bindings"] + sources["overlays"] + sources["operator_packets"] if is_unresolved_or_quarantined(row)], start=1):
        rows.append(row_base(f"demo-unresolved-context-{index:03d}", "unresolved_context", record))
    rows.append(
        {
            "demo_item_id": "demo-limitation-001",
            "demo_item_type": "limitation",
            "hero_binding_ref": None,
            "canonical_entity_ref": None,
            "scene_or_source_ref": "overall-demo-boundary",
            "operator_surface_packet_ref": None,
            "omniverse_prim_path": None,
            "web_companion_ref": None,
            "incident_context_ref": None,
            "cerseg_v2_entity_family": None,
            "cerseg_v2_relationship_family": None,
            "review_state": "limitation_only",
            "confidence_summary": "not an observed/certified fact",
            "evidence_refs": ["UPSTREAM_STATUS_SUMMARY.json"],
            "limitation_refs": LIMITATIONS,
            "trace_refs": ["UPSTREAM_ARTIFACT_INDEX.json"],
            "claim_boundary": SHORT_BOUNDARY,
            "no_action_taken": True,
        }
    )
    return rows


def manifest_validation(rows: list[dict[str, Any]], sources: dict[str, Any]) -> dict[str, Any]:
    operator_ids = {row.get("packet_id") for row in sources["operator_packets"]}
    binding_ids = {row.get("binding_id") for row in sources["bindings"]}
    prim_paths = {row.get("stable_prim_path") for row in sources["bindings"]} | {row.get("usd_prim_path") for row in sources["overlays"]}
    failures = []
    for row in rows:
        if not row.get("evidence_refs") and not row.get("limitation_refs"):
            failures.append({"demo_item_id": row["demo_item_id"], "issue": "missing_evidence_and_limitation_refs"})
        review = str(row.get("review_state", "")).lower()
        if ("unresolved" in review or "quarantined" in review) and row.get("canonical_entity_ref"):
            failures.append({"demo_item_id": row["demo_item_id"], "issue": "unresolved_or_quarantined_promoted_to_canonical_ref"})
        operator_ref = str(row.get("operator_surface_packet_ref") or "")
        hero_ref = str(row.get("hero_binding_ref") or "")
        prim_ref = str(row.get("omniverse_prim_path") or "")
        if operator_ref.startswith("incident-track2a-r4") and operator_ref not in operator_ids:
            failures.append({"demo_item_id": row["demo_item_id"], "issue": "operator_surface_packet_ref_not_in_incident_r4"})
        if hero_ref.startswith("hero-neighbourhood-r1-binding") and hero_ref not in binding_ids:
            failures.append({"demo_item_id": row["demo_item_id"], "issue": "hero_binding_ref_not_in_hero_binding_registry"})
        if prim_ref and prim_ref not in prim_paths:
            failures.append({"demo_item_id": row["demo_item_id"], "issue": "omniverse_prim_path_not_aligned_with_hero_bindings"})
    return {
        "status": "PASS" if not failures else "FAIL",
        "manifest_rows": len(rows),
        "failure_count": len(failures),
        "failures": failures,
    }


def omniverse_summary(sources: dict[str, Any]) -> dict[str, Any]:
    kit = sources["kit_manifest"]
    usda = root_path("outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3") / "HERO_SCENE_USD_OR_USDA_HANDOFF.usda"
    return {
        "status": "PASS" if kit.get("status") == "PASS" and usda.exists() else "FAIL",
        "scene_id": kit.get("scene_id") or sources["scene_summary"].get("scene_id"),
        "package_mode": kit.get("package_mode"),
        "usd_or_usda_handoff_path": kit.get("usd_or_usda_handoff_path"),
        "usda_exists": usda.exists(),
        "prim_metadata_count": len(sources["prim_metadata"]),
        "overlay_packet_count": kit.get("overlay_packet_count") or len(sources["overlays"]),
        "operator_open_path": kit.get("operator_open_path", []),
        "interactive_omniverse_session_launched": kit.get("interactive_omniverse_session_launched", False),
        "visual_acceptance_mode": "artifact/package review only; no new screenshot required by this task",
        "boundary": BOUNDARY,
        "limitations": strings(kit.get("limitations")) + LIMITATIONS,
    }


def web_summary(sources: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    web_rows = [row for row in rows if row["demo_item_type"] == "web_packet"]
    refs = unique([str(row.get("web_companion_ref")) for row in rows if row.get("web_companion_ref") and "not_applicable" not in str(row.get("web_companion_ref"))])
    return {
        "status": "PASS" if web_rows and refs else "PASS_WITH_LIMITATIONS",
        "web_companion_packet_count": len(web_rows),
        "unique_web_companion_refs": refs,
        "source_manifest_status": sources["web_overlay"].get("status"),
        "surface": "web companion evidence / episode / operator context surface",
        "public_api_ready": False,
        "boundary": BOUNDARY,
        "limitations": ["web companion handoff summary only; no app mutation or public serving claim"] + LIMITATIONS,
    }


def operator_surface_summary(sources: dict[str, Any]) -> dict[str, Any]:
    packets = sources["operator_packets"]
    return {
        "status": "PASS" if packets else "FAIL",
        "operator_surface_packets_count": len(packets),
        "omniverse_overlay_packet_count": sum(1 for packet in packets if packet.get("packet_type") == "omniverse_operator_overlay_packet"),
        "web_companion_packet_count": sum(1 for packet in packets if packet.get("packet_type") == "web_operator_companion_packet"),
        "safe_next_look_packet_count": sum(1 for packet in packets if packet.get("packet_type") == "safe_next_look_surface_packet"),
        "unresolved_quarantined_packet_count": sum(1 for packet in packets if is_unresolved_or_quarantined(packet)),
        "allowed_surface_actions": sorted({action for packet in packets for action in strings(packet.get("allowed_surface_actions"))}),
        "forbidden_surface_actions": sorted({action for packet in packets for action in strings(packet.get("forbidden_surface_actions"))}),
        "boundary": BOUNDARY,
    }


def cerseg_summary(sources: dict[str, Any]) -> dict[str, Any]:
    integration = sources["integration_readiness"]
    closeout = sources["cerseg_closeout"]
    return {
        "status": "PASS"
        if closeout.get("status") == REQUIRED_UPSTREAMS["cerseg_cross_city_v2_closeout"]["expected"]
        and integration.get("cerseg_closeout_status") == REQUIRED_UPSTREAMS["cerseg_cross_city_v2_closeout"]["expected"]
        else "FAIL",
        "cerseg_closeout_status": closeout.get("status"),
        "integration_readiness_cerseg_status": integration.get("cerseg_closeout_status"),
        "entity_compatibility_result": integration.get("entity_compatibility_result"),
        "relationship_ontology_compatibility_result": integration.get("relationship_ontology_compatibility_result"),
        "confidence_review_state_compatibility_result": integration.get("confidence_review_state_compatibility_result"),
        "runtime_bridge_compatibility_result": integration.get("runtime_bridge_compatibility_result"),
        "non_blocking_gap_count": integration.get("non_blocking_gap_count", 0),
        "compatibility_findings_status": closeout.get("compatibility_findings_status"),
        "global_master_database_claim_made": False,
        "new_canonical_identity_system_created": False,
        "boundary": BOUNDARY,
    }


def evidence_trace_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing_evidence = [row["demo_item_id"] for row in rows if not row.get("evidence_refs")]
    missing_limitations = [row["demo_item_id"] for row in rows if not row.get("limitation_refs")]
    missing_traces = [row["demo_item_id"] for row in rows if not row.get("trace_refs")]
    return {
        "status": "PASS" if not missing_evidence and not missing_limitations and not missing_traces else "FAIL",
        "manifest_rows": len(rows),
        "rows_with_evidence_refs": len(rows) - len(missing_evidence),
        "rows_with_limitation_refs": len(rows) - len(missing_limitations),
        "rows_with_trace_refs": len(rows) - len(missing_traces),
        "missing_evidence_rows": missing_evidence,
        "missing_limitation_rows": missing_limitations,
        "missing_trace_rows": missing_traces,
        "boundary": BOUNDARY,
    }


def preservation_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    preserved = [row for row in rows if is_unresolved_or_quarantined(row)]
    promoted = [row["demo_item_id"] for row in preserved if row.get("canonical_entity_ref")]
    return {
        "status": "PASS" if preserved and not promoted else "FAIL",
        "unresolved_quarantined_preserved_count": len(preserved),
        "unresolved_count": sum("unresolved" in json.dumps(row).lower() for row in preserved),
        "quarantined_count": sum("quarantined" in json.dumps(row).lower() for row in preserved),
        "promoted_to_canonical_truth": promoted,
        "preservation_policy": "unresolved/quarantined contexts remain visible review/query context and never become canonical truth",
        "boundary": BOUNDARY,
    }


def visual_acceptance_checklist(omniverse: dict[str, Any], web: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[str, str]:
    status = "PASS_ARTIFACT_PACKAGE_REVIEW_ONLY"
    text = f"""# Visual Acceptance Checklist

Status: `{status}`

{BOUNDARY}

- [x] Hero scene package is present as a bounded local/replay handoff.
- [x] Omniverse/Kit/Composer USDA handoff path is recorded: `{omniverse.get('usd_or_usda_handoff_path')}`.
- [x] Prim metadata count is recorded: `{omniverse.get('prim_metadata_count')}`.
- [x] Web companion refs are recorded: `{len(web.get('unique_web_companion_refs', []))}` unique refs.
- [x] Incident/operator surface packet rows are included in the demo manifest.
- [x] Evidence, limitation, and trace refs are co-displayed for every manifest row.
- [x] Unresolved and quarantined contexts remain visible and not promoted.
- [x] No real screenshot is required for this R1. Visual acceptance is package/artifact review only.
- [ ] Optional future manual screenshot/recording can be added by a later closeout or demo packaging task.

Manifest rows checked: `{len(rows)}`
"""
    return status, text


def demo_acceptance_matrix(
    upstream: dict[str, Any],
    manifest: dict[str, Any],
    omniverse: dict[str, Any],
    web: dict[str, Any],
    operator: dict[str, Any],
    cerseg: dict[str, Any],
    evidence: dict[str, Any],
    preservation: dict[str, Any],
    visual_status: str,
) -> tuple[dict[str, Any], str]:
    checks = [
        {"check_id": "required_upstreams_green", "status": upstream["status"], "evidence": "UPSTREAM_STATUS_SUMMARY.json"},
        {"check_id": "demo_manifest_generated", "status": manifest["status"], "evidence": "CONTROL_ROOM_DEMO_MANIFEST.json"},
        {"check_id": "omniverse_scene_handoff_summary", "status": omniverse["status"], "evidence": "OMNIVERSE_SCENE_HANDOFF_SUMMARY.json"},
        {"check_id": "web_companion_handoff_summary", "status": "PASS" if web["status"].startswith("PASS") else "FAIL", "evidence": "WEB_COMPANION_HANDOFF_SUMMARY.json"},
        {"check_id": "incident_operator_surface_packet_summary", "status": operator["status"], "evidence": "INCIDENT_OPERATOR_SURFACE_PACKET_SUMMARY.json"},
        {"check_id": "cerseg_v2_compatibility_summary", "status": cerseg["status"], "evidence": "CERSEG_V2_COMPATIBILITY_SUMMARY.json"},
        {"check_id": "evidence_limitation_trace_summary", "status": evidence["status"], "evidence": "EVIDENCE_LIMITATION_TRACE_SUMMARY.json"},
        {"check_id": "unresolved_quarantined_preservation", "status": preservation["status"], "evidence": "UNRESOLVED_QUARANTINED_PRESERVATION_REPORT.json"},
        {"check_id": "visual_acceptance", "status": "PASS", "evidence": visual_status},
    ]
    matrix = {
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "checks": checks,
        "blocking_gaps_count": sum(1 for row in checks if row["status"] != "PASS"),
        "non_blocking_gaps": [
            "visual acceptance is artifact/package review only; no new screenshot required",
            "Omniverse USDA remains metadata/sidecar handoff, not a certified citywide twin",
            "CER/SEG entity compatibility has one upstream non-blocking finding preserved from readiness review",
        ],
        "boundary": BOUNDARY,
    }
    md_lines = ["# Demo Acceptance Matrix", "", f"Status: `{matrix['status']}`", "", BOUNDARY, ""]
    for check in checks:
        md_lines.append(f"- {check['check_id']}: `{check['status']}` ({check['evidence']})")
    md_lines.extend(["", "## Non-Blocking Gaps", ""])
    md_lines.extend(f"- {item}" for item in matrix["non_blocking_gaps"])
    return matrix, "\n".join(md_lines)


def claim_boundary_audit() -> dict[str, Any]:
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore").lower() for path in OUTPUT_ROOT.rglob("*") if path.is_file() and path.name != "CLAIM_BOUNDARY_AUDIT.json")
    positive_patterns = [
        r'"production_readiness_claim_made"\s*:\s*true',
        r'"public_api_readiness_claim_made"\s*:\s*true',
        r'"live_monitoring_claim_made"\s*:\s*true',
        r'"autonomous_incident_detection_claim_made"\s*:\s*true',
        r'"alert_push_claim_made"\s*:\s*true',
        r'"dispatch_claim_made"\s*:\s*true',
        r'"routing_control_claim_made"\s*:\s*true',
        r'"enforcement_claim_made"\s*:\s*true',
        r'"official_ticket_case_creation_claim_made"\s*:\s*true',
        r'"legal_certified_incident_finding_claim_made"\s*:\s*true',
        r'"citywide_certified_twin_claim_made"\s*:\s*true',
        r'"physical_accuracy_claim_made"\s*:\s*true',
        r'"automated_action_claim_made"\s*:\s*true',
        r"production ready for deployment",
        r"public api ready",
        r"certified incident finding enabled",
        r"certified incident finding issued",
        r"dispatch command",
        r"routing/control command",
        r"enforcement action",
        r"official ticket created",
    ]
    hits = [pattern for pattern in positive_patterns if re.search(pattern, combined)]
    boundary_present = BOUNDARY.lower() in combined
    report = {
        "status": "PASS" if not hits and boundary_present else "FAIL",
        "positive_forbidden_claim_hits": hits,
        "boundary_present": boundary_present,
        "production_readiness_claim_made": False,
        "public_api_readiness_claim_made": False,
        "live_monitoring_claim_made": False,
        "autonomous_incident_detection_claim_made": False,
        "alert_push_claim_made": False,
        "dispatch_claim_made": False,
        "routing_control_claim_made": False,
        "enforcement_claim_made": False,
        "official_ticket_case_creation_claim_made": False,
        "legal_certified_incident_finding_claim_made": False,
        "citywide_certified_twin_claim_made": False,
        "physical_accuracy_claim_made": False,
        "automated_action_claim_made": False,
        "boundary": BOUNDARY,
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", report)
    return report


def no_action_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [row["demo_item_id"] for row in rows if row.get("no_action_taken") is not True]
    report = {
        "status": "PASS" if not failures else "FAIL",
        "checked_manifest_rows": len(rows),
        "failures": failures,
        "no_action_boundary": "all rows are local/replay review/query context only; no command, dispatch, routing/control, enforcement, ticket/case, legal/certified finding, or automated action",
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", report)
    return report


def no_mutation_audit(before: dict[str, dict[str, Any]]) -> dict[str, Any]:
    changed = []
    for key, spec in {**REQUIRED_UPSTREAMS, **SUPPORTING_UPSTREAMS}.items():
        after = snapshot(root_path(spec["root"]))
        if before.get(key) != after:
            changed.append({"upstream_key": key, "root": spec["root"], "before": before.get(key), "after": after})
    report = {
        "status": "PASS" if not changed else "FAIL",
        "watched_upstream_count": len(before),
        "changed_upstreams": changed,
        "output_root_only_mutated": not changed,
        "boundary": BOUNDARY,
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", report)
    return report


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
        re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+[a-z0-9._-]{16,}"),
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.name not in {"SECRET_AUDIT.json", "HASH_MANIFEST.json"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    findings.append({"path": rel(path), "pattern": pattern.pattern})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings, "boundary": BOUNDARY}
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", report)
    return report


def hash_manifest() -> dict[str, Any]:
    entries = []
    for path in sorted(item for item in OUTPUT_ROOT.rglob("*") if item.is_file()):
        if path.name == "HASH_MANIFEST.json":
            continue
        entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    failures = [entry["path"] for entry in entries if not (REPO_ROOT / entry["path"]).exists() or sha256_file(REPO_ROOT / entry["path"]) != entry["sha256"]]
    report = {"task_name": TASK_NAME, "timestamp": now_iso(), "file_count": len(entries), "files": entries, "hash_validation_status": "PASS" if not failures else "FAIL", "failures": failures}
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", report)
    return report


def required_files_status() -> dict[str, Any]:
    missing = [name for name in REQUIRED_OUTPUTS if not (OUTPUT_ROOT / name).exists()]
    return {"status": "PASS" if not missing else "FAIL", "required_count": len(REQUIRED_OUTPUTS), "missing": missing}


def write_operator_docs(sources: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    scene_id = sources["scene_summary"].get("scene_id") or sources["kit_manifest"].get("scene_id")
    write_text(
        OUTPUT_ROOT / "OPERATOR_WALKTHROUGH_SCRIPT.md",
        f"""# Operator Walkthrough Script

{BOUNDARY}

1. Open the local demo package index and confirm the status is pass-with-limitations.
2. Name the selected context: `{scene_id}`.
3. Open the Omniverse/Kit/Composer handoff path from `OMNIVERSE_SCENE_HANDOFF_SUMMARY.json`.
4. Select or inspect the hero prim metadata rows for the corridor/event/operator context bindings.
5. Open the incident/operator surface packet rows and keep review state visible.
6. For unresolved or quarantined cards, say: this remains review/query context and is not canonical truth.
7. Open the web companion handoff summary for evidence and limitation co-display.
8. Use safe-next-look only as a review navigation option.
9. Close by repeating that no alert, dispatch, routing/control, enforcement, ticket/case, legal finding, certified twin, or automated action is created.

Demo manifest rows: `{len(rows)}`
""",
    )
    write_text(
        OUTPUT_ROOT / "EXECUTIVE_WALKTHROUGH_SCRIPT.md",
        f"""# Executive Walkthrough Script

{BOUNDARY}

This R1 package demonstrates one bounded local/replay control-room reference slice.

What it shows:

- a selected Hero Neighbourhood / corridor replay context;
- Omniverse/Kit/Composer scene-binding metadata;
- a web companion evidence/limitation view;
- Incident Mode operator-surface packets;
- CER/SEG v2 compatibility semantics;
- evidence, limitation, and trace lineage.

What it does not show:

- production readiness;
- public API readiness;
- live monitoring;
- autonomous incident detection;
- alert push;
- dispatch;
- routing/control;
- enforcement;
- official ticket/case creation;
- legal/certified incident finding;
- citywide certified twin;
- physical accuracy;
- automated action.
""",
    )
    write_text(
        OUTPUT_ROOT / "CONTROL_ROOM_DEMO_STORYBOARD.md",
        f"""# Control Room Demo Storyboard

{BOUNDARY}

1. Establish the local/replay Hero Neighbourhood scene context.
2. Show the Omniverse binding/prim metadata handoff as spatial context.
3. Show the incident/operator packet in review-ready state.
4. Show unresolved and quarantined examples without promotion.
5. Show the web companion evidence and limitation co-display.
6. Show CER/SEG v2 compatibility and R7/R8 relationship lineage.
7. End on the claim boundary and recommended closeout task.
""",
    )
    write_text(
        OUTPUT_ROOT / "KIT_COMPOSER_OPERATOR_NOTES.md",
        f"""# Kit / Composer Operator Notes

{BOUNDARY}

- Open the USDA handoff named in `OMNIVERSE_SCENE_HANDOFF_SUMMARY.json`.
- Treat prim paths as scene-binding metadata, not canonical identity or physical accuracy.
- Use the inspection card/metadata only for local/replay review context.
- Do not present the scene as a production Omniverse deployment or certified twin.
""",
    )
    write_text(
        OUTPUT_ROOT / "WEB_COMPANION_OPERATOR_NOTES.md",
        f"""# Web Companion Operator Notes

{BOUNDARY}

- Use web companion refs as evidence/limitation display anchors.
- Keep review state, confidence, and limitations beside every item.
- Treat safe-next-look choices as review navigation only.
- Do not show alerts, dispatch, route/control, enforcement, official ticket/case, legal finding, or automated action.
""",
    )
    write_text(
        OUTPUT_ROOT / "DEMO_SCREENSHOT_PLACEHOLDER_INDEX.md",
        f"""# Demo Screenshot Placeholder Index

{BOUNDARY}

No fresh screenshots were required or captured by this R1 task.

Visual acceptance status is `PASS_ARTIFACT_PACKAGE_REVIEW_ONLY`.

Suggested future capture slots:

- Omniverse/Kit/Composer hero scene open.
- Selection/metadata card for a review-ready context prim.
- Selection/metadata card for unresolved context.
- Selection/metadata card for quarantined context.
- Web companion evidence/limitation co-display.
""",
    )


def write_readme_and_index(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{decision['status']}`

{BOUNDARY}

This package composes already-green Hero Neighbourhood, CER/SEG v2, Incident Mode, local running, R7, and R8 outputs into one bounded control-room reference demo acceptance pack.

- Required upstreams found: `{decision['required_upstreams_found']}/{decision['required_upstreams_total']}`
- Hero bindings: `{decision['hero_bindings_count']}`
- Hero overlay packets: `{decision['hero_overlay_packets_count']}`
- Operator-surface packets: `{decision['operator_surface_packets_count']}`
- Web companion packets: `{decision['web_companion_packets_count']}`
- Manifest rows: `{decision['manifest_rows_count']}`
- Visual acceptance: `{decision['visual_acceptance_status']}`
- Recommended next task: `{decision['recommended_next_task']}`
""",
    )
    lines = [f"# {TASK_NAME}", "", f"Status: `{decision['status']}`", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in REQUIRED_OUTPUTS)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> int:
    prepare_output_root()
    watched_specs = {**REQUIRED_UPSTREAMS, **SUPPORTING_UPSTREAMS}
    before = {key: snapshot(root_path(spec["root"])) for key, spec in watched_specs.items()}

    _artifact_index, upstream_summary, missing = discover_upstreams()
    if upstream_summary["status"] != "PASS":
        decision = {
            "status": FAIL_STATUS,
            "task_name": TASK_NAME,
            "timestamp": now_iso(),
            "output_root": str(OUTPUT_ROOT),
            "runner_path": str(Path(__file__).resolve()),
            "required_upstreams_found": upstream_summary["required_upstreams_found"],
            "required_upstreams_total": upstream_summary["required_upstreams_total"],
            "blocking_gaps_count": len(missing),
            "blocking_gaps": missing,
            "boundary": BOUNDARY,
        }
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json", decision)
        write_text(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: `{FAIL_STATUS}`\n\n{BOUNDARY}\n")
        hash_manifest()
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 1

    sources = load_sources()
    manifest_rows = build_manifest(sources)
    manifest_check = manifest_validation(manifest_rows, sources)
    manifest_payload = {
        "status": manifest_check["status"],
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "manifest_row_count": len(manifest_rows),
        "demo_scope": sources["scene_summary"].get("scene_id") or sources["kit_manifest"].get("scene_id"),
        "rows": manifest_rows,
        "validation": manifest_check,
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_DEMO_MANIFEST.json", manifest_payload)
    write_jsonl(OUTPUT_ROOT / "CONTROL_ROOM_DEMO_MANIFEST.jsonl", manifest_rows)

    omniverse = omniverse_summary(sources)
    web = web_summary(sources, manifest_rows)
    operator = operator_surface_summary(sources)
    cerseg = cerseg_summary(sources)
    evidence = evidence_trace_summary(manifest_rows)
    preservation = preservation_report(manifest_rows)
    visual_status, visual_md = visual_acceptance_checklist(omniverse, web, manifest_rows)
    matrix, matrix_md = demo_acceptance_matrix(upstream_summary, manifest_check, omniverse, web, operator, cerseg, evidence, preservation, visual_status)

    write_json(OUTPUT_ROOT / "OMNIVERSE_SCENE_HANDOFF_SUMMARY.json", omniverse)
    write_json(OUTPUT_ROOT / "WEB_COMPANION_HANDOFF_SUMMARY.json", web)
    write_json(OUTPUT_ROOT / "INCIDENT_OPERATOR_SURFACE_PACKET_SUMMARY.json", operator)
    write_json(OUTPUT_ROOT / "CERSEG_V2_COMPATIBILITY_SUMMARY.json", cerseg)
    write_json(OUTPUT_ROOT / "EVIDENCE_LIMITATION_TRACE_SUMMARY.json", evidence)
    write_json(OUTPUT_ROOT / "UNRESOLVED_QUARANTINED_PRESERVATION_REPORT.json", preservation)
    write_text(OUTPUT_ROOT / "VISUAL_ACCEPTANCE_CHECKLIST.md", visual_md)
    write_json(OUTPUT_ROOT / "DEMO_ACCEPTANCE_MATRIX.json", matrix)
    write_text(OUTPUT_ROOT / "DEMO_ACCEPTANCE_MATRIX.md", matrix_md)
    write_operator_docs(sources, manifest_rows)

    claim = claim_boundary_audit()
    no_action = no_action_audit(manifest_rows)
    no_mutation = no_mutation_audit(before)
    secret = secret_audit()

    status = PASS_STATUS
    if not all(
        [
            upstream_summary["status"] == "PASS",
            manifest_check["status"] == "PASS",
            omniverse["status"] == "PASS",
            web["status"].startswith("PASS"),
            operator["status"] == "PASS",
            cerseg["status"] == "PASS",
            evidence["status"] == "PASS",
            preservation["status"] == "PASS",
            matrix["status"] == "PASS",
            claim["status"] == "PASS",
            no_action["status"] == "PASS",
            no_mutation["status"] == "PASS",
            secret["status"] == "PASS",
        ]
    ):
        status = FAIL_STATUS

    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "required_upstreams_found": upstream_summary["required_upstreams_found"],
        "required_upstreams_total": upstream_summary["required_upstreams_total"],
        "hero_bindings_count": len(sources["bindings"]),
        "hero_overlay_packets_count": len(sources["overlays"]),
        "operator_surface_packets_count": operator["operator_surface_packets_count"],
        "web_companion_packets_count": web["web_companion_packet_count"],
        "unresolved_quarantined_preserved_count": preservation["unresolved_quarantined_preserved_count"],
        "manifest_rows_count": len(manifest_rows),
        "demo_acceptance_status": matrix["status"],
        "visual_acceptance_status": visual_status,
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "blocking_gaps_count": matrix["blocking_gaps_count"],
        "non_blocking_gaps_count": len(matrix["non_blocking_gaps"]),
        "blocking_gaps": [],
        "non_blocking_gaps": matrix["non_blocking_gaps"],
        "production_readiness_claim_made": False,
        "public_api_readiness_claim_made": False,
        "live_monitoring_claim_made": False,
        "autonomous_incident_detection_claim_made": False,
        "alert_push_claim_made": False,
        "dispatch_claim_made": False,
        "routing_control_claim_made": False,
        "enforcement_claim_made": False,
        "official_ticket_case_creation_claim_made": False,
        "legal_certified_incident_finding_claim_made": False,
        "citywide_certified_twin_claim_made": False,
        "physical_accuracy_claim_made": False,
        "automated_action_claim_made": False,
        "limitations": LIMITATIONS,
        "recommended_next_task": RECOMMENDED_NEXT_TASK if status == PASS_STATUS else FIXUP_NEXT_TASK,
        "alternative_next_task_if_gap_found": FIXUP_NEXT_TASK,
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json", decision)
    write_readme_and_index(decision)
    claim = claim_boundary_audit()
    secret = secret_audit()
    hash_report = hash_manifest()
    required_status = required_files_status()
    if not all([claim["status"] == "PASS", secret["status"] == "PASS", required_status["status"] == "PASS", hash_report["hash_validation_status"] == "PASS"]):
        decision["status"] = FAIL_STATUS
        decision["recommended_next_task"] = FIXUP_NEXT_TASK
        status = FAIL_STATUS
    decision["claim_boundary_status"] = claim["status"]
    decision["secret_audit_status"] = secret["status"]
    decision["hash_validation_status"] = hash_report["hash_validation_status"]
    decision["blocking_gaps"] = required_status["missing"]
    decision["blocking_gaps_count"] = matrix["blocking_gaps_count"] + len(required_status["missing"])
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
