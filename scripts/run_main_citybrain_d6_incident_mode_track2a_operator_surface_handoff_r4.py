#!/usr/bin/env python3
"""Build Incident Mode to Track2A operator-surface handoff R4 fixtures."""

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

TASK_NAME = "MAIN-CITYBRAIN-D6-INCIDENT-MODE-TRACK2A-OPERATOR-SURFACE-HANDOFF-R4"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4"

UPSTREAMS = {
    "incident_mode_closeout": {
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
    },
    "incident_mode_runtime_smoke_r3": {
        "root": "outputs/main_citybrain_d6_incident_mode_runtime_smoke_r3",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_RUNTIME_SMOKE_R3_WITH_LIMITATIONS",
    },
    "incident_mode_operator_review_workflow_r2": {
        "root": "outputs/main_citybrain_d6_incident_mode_operator_review_workflow_r2",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_OPERATOR_REVIEW_WORKFLOW_R2_WITH_LIMITATIONS",
    },
    "incident_mode_evidence_bundle_r1": {
        "root": "outputs/main_citybrain_d6_incident_mode_evidence_bundle_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_EVIDENCE_BUNDLE_R1_WITH_LIMITATIONS",
    },
    "d6_d5_local_running_slice_closeout": {
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS",
    },
    "d5_track2_handoff_r4": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_track2_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_WITH_LIMITATIONS",
    },
    "r8_multi_domain_edge_registry_hardening": {
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
    },
    "hero_neighbourhood_twin_preflight": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_twin_preflight",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT_WITH_LIMITATIONS",
    },
}

BOUNDARY = (
    "Incident Mode operator-surface handoff is human-or-replay initiated, local/replay only, "
    "review/query context only, and evidence-bundle/operator-review contextualization only. "
    "It does not create autonomous monitoring, live incident detection, alert push, dispatch, "
    "routing/control, enforcement, official ticket/case creation, legal/certified/confirmed "
    "incident status, automated action, production/public API readiness, production Omniverse "
    "deployment, citywide certified digital twin, or physical/geometric accuracy beyond accepted "
    "source evidence."
)

LIMITATIONS = [
    "handoff contract and fixture task only",
    "local/replay review/query context only",
    "Incident Mode outputs are consumed read-only",
    "Track2A/Omniverse and web companion outputs are handoff targets only",
    "no UI implementation, Omniverse scene generation, source USD mutation, production deployment, public API, alerting, dispatch, routing/control, enforcement, legal/certified outcome, or automated action",
]

DISPLAY_STATES = [
    "review_ready_context",
    "review_only_context",
    "unresolved_context",
    "quarantined_context",
    "safe_next_look_suggestion",
    "not_actionable_without_human_review",
]

ALLOWED_SURFACE_ACTIONS = [
    "view evidence",
    "inspect affected entities",
    "inspect relationship context",
    "inspect limitations",
    "inspect unresolved state",
    "inspect safe-next-look suggestion",
    "open local trace/reference",
]

FORBIDDEN_SURFACE_ACTIONS = [
    "alert",
    "dispatch",
    "route/control",
    "enforce",
    "create official case/ticket",
    "certify/confirm incident",
    "mutate source data",
    "trigger automated workflow",
]

EXPECTED_FILES = [
    "MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_DECISION.json",
    "README.md",
    "INPUT_ARTIFACT_INDEX.json",
    "UPSTREAM_STATUS_SUMMARY.json",
    "OPERATOR_SURFACE_HANDOFF_CONTRACT.json",
    "INCIDENT_OPERATOR_SURFACE_PACKET_SCHEMA.json",
    "OMNIVERSE_OPERATOR_OVERLAY_PACKET_SCHEMA.json",
    "WEB_OPERATOR_COMPANION_PACKET_SCHEMA.json",
    "SAFE_NEXT_LOOK_SURFACE_POLICY.json",
    "REVIEW_STATE_DISPLAY_POLICY.json",
    "CONFIDENCE_DISPLAY_POLICY.json",
    "EVIDENCE_LIMITATION_SURFACE_TRACE_CONTRACT.json",
    "OMNIVERSE_TRACK2A_HANDOFF_IMPACT.md",
    "WEB_COMPANION_HANDOFF_IMPACT.md",
    "HERO_NEIGHBOURHOOD_INTEGRATION_IMPACT.md",
    "OPERATOR_SURFACE_PACKET_FIXTURES.json",
    "OPERATOR_SURFACE_PACKET_FIXTURES.jsonl",
    "PACKET_VALIDATION_RESULTS.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
    "LOCAL_OPEN_INDEX.md",
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


def discover_inputs(pre: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    missing = []
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
                if len(artifacts) >= 18:
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
    report = {
        "status": "PASS" if not missing else "FAIL",
        "timestamp": utc_now(),
        "missing_required_upstreams": missing,
        "discovered_count": sum(row["exists"] for row in branches),
        "required_count": len(branches),
        "branches": branches,
    }
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", report)
    return report, missing


def upstream_summary(input_index: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for branch in input_index["branches"]:
        decision = read_json(REPO_ROOT / branch["decision_path"], {}) if branch.get("decision_path") else {}
        rows.append(
            {
                "branch": branch["branch"],
                "root": branch["root"],
                "green": branch["green"],
                "status": branch["status"],
                "count_fields": {key: value for key, value in decision.items() if isinstance(value, int) and ("count" in key or "packet" in key or "edge" in key)},
                "consumption_role": consumption_role(branch["branch"]),
                "read_only": True,
            }
        )
    report = {"status": "PASS" if all(row["green"] for row in rows) else "FAIL", "rows": rows}
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", report)
    return report


def consumption_role(branch: str) -> str:
    return {
        "incident_mode_closeout": "frozen Incident Mode boundary and closeout truth",
        "incident_mode_runtime_smoke_r3": "local/replay runtime smoke responses and safe failures",
        "incident_mode_operator_review_workflow_r2": "source operator review packets",
        "incident_mode_evidence_bundle_r1": "source evidence bundles",
        "d6_d5_local_running_slice_closeout": "frozen control-room slice boundary",
        "d5_track2_handoff_r4": "Track2/Omniverse/web handoff contract source",
        "r8_multi_domain_edge_registry_hardening": "hardened edge source",
        "hero_neighbourhood_twin_preflight": "future hero-neighbourhood integration source",
    }.get(branch, "source context")


def load_sources() -> dict[str, Any]:
    return {
        "operator_packets": rows_from(read_json(root_path(UPSTREAMS["incident_mode_operator_review_workflow_r2"]["root"]) / "OPERATOR_REVIEW_PACKETS.json", {}), ["packets"]),
        "evidence_bundles": rows_from(read_json(root_path(UPSTREAMS["incident_mode_evidence_bundle_r1"]["root"]) / "INCIDENT_EVIDENCE_BUNDLES.json", {}), ["bundles"]),
        "runtime_responses": rows_from(read_json(root_path(UPSTREAMS["incident_mode_runtime_smoke_r3"]["root"]) / "RUNTIME_SMOKE_RESULTS.json", {}), ["responses"]),
        "trace_rows": rows_from(read_json(root_path(UPSTREAMS["incident_mode_operator_review_workflow_r2"]["root"]) / "TRACEABILITY_MATRIX.json", {}), ["rows"]),
        "r8_edges": rows_from(read_json(root_path(UPSTREAMS["r8_multi_domain_edge_registry_hardening"]["root"]) / "HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.json", {}), ["edges"]),
        "hero_scene": read_json(root_path(UPSTREAMS["hero_neighbourhood_twin_preflight"]["root"]) / "SCENE_IDENTITY_CONTRACT.json", {}),
        "hero_kit": read_json(root_path(UPSTREAMS["hero_neighbourhood_twin_preflight"]["root"]) / "KIT_COMPOSER_HANDOFF_CONTRACT.json", {}),
        "hero_web": read_json(root_path(UPSTREAMS["hero_neighbourhood_twin_preflight"]["root"]) / "WEB_COMPANION_ALIGNMENT_CONTRACT.json", {}),
    }


def bundle_for(sources: dict[str, Any], incident_id: str) -> dict[str, Any]:
    return next((row for row in sources["evidence_bundles"] if row.get("incident_review_id") == incident_id), {})


def trace_for(sources: dict[str, Any], incident_id: str) -> dict[str, Any]:
    return next((row for row in sources["trace_rows"] if row.get("incident_review_id") == incident_id), {})


def edge_refs_for(bundle: dict[str, Any], packet: dict[str, Any]) -> list[str]:
    refs = strings(bundle.get("hardened_edge_refs"))
    for card in packet.get("relationship_context_cards", []):
        refs.extend(strings(card.get("hardened_edge_ref")))
    return list(dict.fromkeys(refs))


def evidence_refs(packet: dict[str, Any], bundle: dict[str, Any]) -> list[str]:
    refs = strings(bundle.get("evidence_refs"))
    refs.extend(card.get("evidence_ref") for card in packet.get("evidence_cards", []) if isinstance(card, dict))
    return [ref for ref in dict.fromkeys(refs) if ref]


def limitation_refs(packet: dict[str, Any], bundle: dict[str, Any]) -> list[str]:
    refs = strings(bundle.get("limitation_refs"))
    refs.extend(card.get("limitation_ref") for card in packet.get("limitation_cards", []) if isinstance(card, dict))
    return [ref for ref in dict.fromkeys(refs) if ref]


def display_state_for(packet: dict[str, Any], bundle: dict[str, Any], fixture_kind: str) -> str:
    state = f"{packet.get('operator_review_state', '')} {bundle.get('review_state', '')}".lower()
    if fixture_kind == "safe_next_look_only_context":
        return "safe_next_look_suggestion"
    if "quarantined" in state:
        return "quarantined_context"
    if "unresolved" in state:
        return "unresolved_context"
    if "ready" in state:
        return "review_ready_context"
    return "review_only_context"


def confidence_summary(packet: dict[str, Any], bundle: dict[str, Any], display_state: str) -> dict[str, Any]:
    return {
        "display_label": "review confidence only",
        "review_state": packet.get("operator_review_state") or bundle.get("review_state") or "review_only_context",
        "display_state": display_state,
        "not_certified_truth": True,
    }


def base_surface_packet(packet: dict[str, Any], bundle: dict[str, Any], fixture_kind: str, packet_type: str, index: int, sources: dict[str, Any]) -> dict[str, Any]:
    incident_id = packet.get("incident_review_id") or bundle.get("incident_review_id") or f"incident-review-r1-{index:03d}"
    display_state = display_state_for(packet, bundle, fixture_kind)
    trace = trace_for(sources, incident_id)
    return {
        "packet_id": f"incident-track2a-r4-{index:03d}-{packet_type.replace('_', '-')}",
        "packet_type": packet_type,
        "fixture_kind": fixture_kind,
        "source_task": TASK_NAME,
        "source_operator_review_packet_ref": packet.get("operator_review_packet_id"),
        "source_evidence_bundle_ref": packet.get("source_evidence_bundle_ref") or f"INCIDENT_EVIDENCE_BUNDLES.json#{incident_id}",
        "incident_context_id": incident_id,
        "event_ref": (bundle.get("event_state_refs") or ["not_available_in_upstream_fixture"])[0],
        "affected_entity_refs": strings(bundle.get("affected_entity_refs")) or [card.get("entity_ref") for card in packet.get("affected_entity_cards", []) if isinstance(card, dict)] or ["not_available_in_upstream_fixture"],
        "edge_refs": edge_refs_for(bundle, packet) or ["not_available_in_upstream_fixture"],
        "evidence_refs": evidence_refs(packet, bundle) or ["not_available_in_upstream_fixture"],
        "limitation_refs": limitation_refs(packet, bundle) or ["not_available_in_upstream_fixture"],
        "review_state": packet.get("operator_review_state") or bundle.get("review_state") or "review_only_context",
        "confidence_summary": confidence_summary(packet, bundle, display_state),
        "display_state": display_state,
        "operator_label": operator_label(display_state, fixture_kind),
        "surface_targets": packet.get("review_surface_targets") or ["web_companion", "omniverse_kit", "local_control_room_packet_viewer"],
        "allowed_surface_actions": ALLOWED_SURFACE_ACTIONS,
        "forbidden_surface_actions": FORBIDDEN_SURFACE_ACTIONS,
        "safe_next_look_refs": strings(packet.get("safe_next_look_candidates") or bundle.get("safe_next_look_candidates")),
        "omniverse_overlay_refs": strings(packet.get("omniverse_overlay_refs") or bundle.get("omniverse_handoff_refs")),
        "web_companion_refs": strings(packet.get("web_companion_refs") or bundle.get("web_companion_refs")),
        "trace_refs": strings(packet.get("trace_refs") or trace.get("trace_refs")) or [f"EVIDENCE_LIMITATION_TRACE.json#{incident_id}"],
        "claim_boundary": BOUNDARY,
        "no_action_taken": True,
    }


def operator_label(display_state: str, fixture_kind: str) -> str:
    labels = {
        "review_ready_context": "Review-ready context",
        "review_only_context": "Review-only context",
        "unresolved_context": "Unresolved context for human review",
        "quarantined_context": "Quarantined context for human review",
        "safe_next_look_suggestion": "Safe next-look suggestion",
        "not_actionable_without_human_review": "Not actionable without human review",
    }
    if fixture_kind == "omniverse_overlay_target_context":
        return "Omniverse overlay review context"
    if fixture_kind == "web_companion_context":
        return "Web companion review context"
    return labels.get(display_state, "Review-only context")


def write_contracts() -> dict[str, Any]:
    common_required = [
        "packet_id",
        "packet_type",
        "source_task",
        "incident_context_id",
        "event_ref",
        "affected_entity_refs",
        "edge_refs",
        "evidence_refs",
        "limitation_refs",
        "review_state",
        "confidence_summary",
        "display_state",
        "operator_label",
        "surface_targets",
        "allowed_surface_actions",
        "forbidden_surface_actions",
        "trace_refs",
        "claim_boundary",
    ]
    handoff = {
        "status": "PASS",
        "contract_name": "OPERATOR_SURFACE_HANDOFF_CONTRACT",
        "source_contexts": [
            "Incident Mode closeout",
            "Incident Mode runtime smoke R3",
            "Incident Mode operator review workflow R2",
            "Incident Mode evidence bundle R1",
            "D5 Track2 handoff R4",
            "R8 hardened edge registry",
            "Hero Neighbourhood preflight",
        ],
        "display_context_classes": DISPLAY_STATES,
        "surface_targets": ["omniverse_kit", "composer_overlay", "web_companion", "local_control_room_packet_viewer"],
        "rules": [
            "preserve evidence refs, limitation refs, trace refs, review state, and safe-next-look semantics",
            "do not promote unresolved or quarantined context",
            "safe next looks are display/review suggestions only",
            "Omniverse and web outputs remain handoff-only",
        ],
        "claim_boundary": BOUNDARY,
    }
    schemas = {
        "INCIDENT_OPERATOR_SURFACE_PACKET_SCHEMA.json": {
            "status": "PASS",
            "packet_type": "incident_operator_surface_packet",
            "required_fields": common_required,
            "allowed_display_states": DISPLAY_STATES,
            "allowed_surface_actions": ALLOWED_SURFACE_ACTIONS,
            "forbidden_surface_actions": FORBIDDEN_SURFACE_ACTIONS,
            "claim_boundary": BOUNDARY,
        },
        "OMNIVERSE_OPERATOR_OVERLAY_PACKET_SCHEMA.json": {
            "status": "PASS",
            "packet_type": "omniverse_operator_overlay_packet",
            "required_fields": common_required + ["omniverse_overlay_refs"],
            "handoff_only": True,
            "scene_mutation_allowed": False,
            "usd_generation_required": False,
            "claim_boundary": BOUNDARY,
        },
        "WEB_OPERATOR_COMPANION_PACKET_SCHEMA.json": {
            "status": "PASS",
            "packet_type": "web_operator_companion_packet",
            "required_fields": common_required + ["web_companion_refs"],
            "handoff_only": True,
            "production_web_app": False,
            "public_api": False,
            "claim_boundary": BOUNDARY,
        },
        "EVIDENCE_LIMITATION_SURFACE_PACKET_SCHEMA.json": {
            "status": "PASS",
            "packet_type": "evidence_limitation_surface_packet",
            "required_fields": common_required,
            "evidence_and_limitations_required": True,
            "claim_boundary": BOUNDARY,
        },
    }
    safe_policy = {
        "status": "PASS",
        "policy_name": "SAFE_NEXT_LOOK_SURFACE_POLICY",
        "allowed_surface_actions": ALLOWED_SURFACE_ACTIONS,
        "forbidden_surface_actions": FORBIDDEN_SURFACE_ACTIONS,
        "safe_next_look_policy": "safe-next-look content is a display/review suggestion only and is not an action instruction",
        "claim_boundary": BOUNDARY,
    }
    review_policy = {
        "status": "PASS",
        "policy_name": "REVIEW_STATE_DISPLAY_POLICY",
        "display_states": DISPLAY_STATES,
        "preservation_rules": [
            "unresolved contexts remain unresolved_context",
            "quarantined contexts remain quarantined_context",
            "review-ready contexts remain review_ready_context and are not upgraded to official outcome",
            "safe-next-look suggestions remain safe_next_look_suggestion",
        ],
        "claim_boundary": BOUNDARY,
    }
    confidence_policy = {
        "status": "PASS",
        "policy_name": "CONFIDENCE_DISPLAY_POLICY",
        "display_label": "review confidence only",
        "rules": [
            "confidence is evidence/review confidence only",
            "confidence is never physical, legal, certified, or official truth",
            "missing confidence is displayed as not_available_in_upstream_fixture with limitation refs",
        ],
        "claim_boundary": BOUNDARY,
    }
    evidence_trace = {
        "status": "PASS",
        "contract_name": "EVIDENCE_LIMITATION_SURFACE_TRACE_CONTRACT",
        "required_refs": ["evidence_refs", "limitation_refs", "trace_refs"],
        "trace_rules": [
            "surface packet must link back to evidence bundle and operator review packet",
            "surface packet must preserve trace refs from R1/R2/R3 where available",
            "surface packet must display limitations beside evidence",
        ],
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "OPERATOR_SURFACE_HANDOFF_CONTRACT.json", handoff)
    for name, payload in schemas.items():
        write_json(OUTPUT_ROOT / name, payload)
    write_json(OUTPUT_ROOT / "SAFE_NEXT_LOOK_SURFACE_POLICY.json", safe_policy)
    write_json(OUTPUT_ROOT / "REVIEW_STATE_DISPLAY_POLICY.json", review_policy)
    write_json(OUTPUT_ROOT / "CONFIDENCE_DISPLAY_POLICY.json", confidence_policy)
    write_json(OUTPUT_ROOT / "EVIDENCE_LIMITATION_SURFACE_TRACE_CONTRACT.json", evidence_trace)
    return {"handoff": handoff, "schemas": schemas, "safe_policy": safe_policy, "review_policy": review_policy, "confidence_policy": confidence_policy, "evidence_trace": evidence_trace}


def select_packet(sources: dict[str, Any], predicate: Any, fallback_index: int = 0) -> dict[str, Any]:
    for packet in sources["operator_packets"]:
        if predicate(packet):
            return packet
    return sources["operator_packets"][min(fallback_index, max(len(sources["operator_packets"]) - 1, 0))] if sources["operator_packets"] else {}


def build_fixtures(sources: dict[str, Any]) -> dict[str, Any]:
    selected = [
        ("directly_resolved_incident_context", "incident_operator_surface_packet", select_packet(sources, lambda p: p.get("operator_review_state") == "ready_for_operator_review" and len(p.get("affected_entity_cards", [])) > 0)),
        ("unresolved_incident_context", "incident_operator_surface_packet", select_packet(sources, lambda p: "unresolved" in str(p.get("operator_review_state", "")))),
        ("quarantined_or_invalid_context", "incident_operator_surface_packet", select_packet(sources, lambda p: "quarantined" in str(p.get("operator_review_state", "")))),
        ("safe_next_look_only_context", "safe_next_look_surface_packet", select_packet(sources, lambda p: len(p.get("safe_next_look_cards", [])) > 0, 0)),
        ("omniverse_overlay_target_context", "omniverse_operator_overlay_packet", select_packet(sources, lambda p: bool(p.get("omniverse_overlay_refs")), 0)),
        ("web_companion_context", "web_operator_companion_packet", select_packet(sources, lambda p: bool(p.get("web_companion_refs")), 0)),
    ]
    packets = []
    for index, (fixture_kind, packet_type, source_packet) in enumerate(selected, start=1):
        if not source_packet:
            packet = {
                "packet_id": f"incident-track2a-r4-{index:03d}-{packet_type.replace('_', '-')}",
                "packet_type": packet_type,
                "fixture_kind": fixture_kind,
                "source_task": TASK_NAME,
                "incident_context_id": "not_available_in_upstream_fixture",
                "event_ref": "not_available_in_upstream_fixture",
                "affected_entity_refs": ["not_available_in_upstream_fixture"],
                "edge_refs": ["not_available_in_upstream_fixture"],
                "evidence_refs": ["not_available_in_upstream_fixture"],
                "limitation_refs": ["not_available_in_upstream_fixture", "upstream category not available; no false incident fabricated"],
                "review_state": "review_only_context",
                "confidence_summary": {"display_label": "not_available_in_upstream_fixture", "not_certified_truth": True},
                "display_state": "review_only_context",
                "operator_label": "Not available in upstream fixture",
                "surface_targets": ["local_control_room_packet_viewer"],
                "allowed_surface_actions": ALLOWED_SURFACE_ACTIONS,
                "forbidden_surface_actions": FORBIDDEN_SURFACE_ACTIONS,
                "trace_refs": ["not_available_in_upstream_fixture"],
                "claim_boundary": BOUNDARY,
                "no_action_taken": True,
            }
        else:
            incident_id = source_packet.get("incident_review_id")
            bundle = bundle_for(sources, incident_id)
            packet = base_surface_packet(source_packet, bundle, fixture_kind, packet_type, index, sources)
        packets.append(packet)
    payload = {
        "status": "PASS",
        "packet_count": len(packets),
        "omniverse_overlay_packet_count": sum(packet["packet_type"] == "omniverse_operator_overlay_packet" for packet in packets),
        "web_companion_packet_count": sum(packet["packet_type"] == "web_operator_companion_packet" for packet in packets),
        "safe_next_look_packet_count": sum(packet["packet_type"] == "safe_next_look_surface_packet" for packet in packets),
        "unresolved_quarantined_preserved_count": sum(packet["display_state"] in {"unresolved_context", "quarantined_context"} for packet in packets),
        "packets": packets,
    }
    write_json(OUTPUT_ROOT / "OPERATOR_SURFACE_PACKET_FIXTURES.json", payload)
    with (OUTPUT_ROOT / "OPERATOR_SURFACE_PACKET_FIXTURES.jsonl").open("w", encoding="utf-8") as handle:
        for packet in packets:
            handle.write(json.dumps(packet, sort_keys=True) + "\n")
    return payload


def write_impact_docs(sources: dict[str, Any]) -> None:
    hero_scene = sources["hero_scene"]
    write_text(
        OUTPUT_ROOT / "OMNIVERSE_TRACK2A_HANDOFF_IMPACT.md",
        f"""# Omniverse Track2A Handoff Impact

This task is handoff-only. It does not mutate a scene, generate USD/USDA, create a production Omniverse deployment, or start Hero Neighbourhood implementation.

Future Track2A consumption should use packet metadata for:

- incident context id
- affected entity refs
- R8 hardened edge refs
- evidence and limitation refs
- review state and confidence labels
- future prim or marker binding metadata
- local trace and audit links

Relationship to Hero Neighbourhood: future implementation may align these packets to `{hero_scene.get('scene_id', 'hero-neighbourhood-preflight-scene-001')}` and its bounded candidate labels.

Relationship to existing Track2A event overlays: reuse existing overlay and sidecar marker patterns; preserve review-state labels and no-action boundaries.

Relationship to D6 control-room product surface: packets remain local/replay review context and can be co-displayed with control-room packet review.

Boundary: {BOUNDARY}
""",
    )
    write_text(
        OUTPUT_ROOT / "WEB_COMPANION_HANDOFF_IMPACT.md",
        f"""# Web Companion Handoff Impact

This task does not create a production web app or public API.

Future web companion display should include:

- evidence list
- limitation list
- affected entity context
- R8 relationship context
- review state labels
- unresolved/quarantined display labels
- safe-next-look display suggestions
- trace and audit links
- executive-safe review-context summary labels

The web surface must not present the packet as an alert, action queue, official ticket/case, enforcement flow, legal/certified outcome, or automated workflow.

Boundary: {BOUNDARY}
""",
    )
    write_text(
        OUTPUT_ROOT / "HERO_NEIGHBOURHOOD_INTEGRATION_IMPACT.md",
        f"""# Hero Neighbourhood Integration Impact

This handoff can later feed Hero Neighbourhood asset binding after the bounded scene implementation task starts.

Integration points:

- scene id: `{hero_scene.get('scene_id', 'hero-neighbourhood-preflight-scene-001')}`
- scene label: `{hero_scene.get('scene_label', 'bounded hero-neighbourhood review scene')}`
- canonical entity refs from Hero Neighbourhood preflight
- R8 hardened edge refs from Hero Neighbourhood preflight and Incident Mode packets
- Incident Mode evidence, limitation, trace, review-state, and safe-next-look metadata

This task does not start Hero Neighbourhood implementation and does not author a citywide/certified/production twin.

Boundary: {BOUNDARY}
""",
    )


def validate_packets(fixtures: dict[str, Any]) -> dict[str, Any]:
    required = [
        "packet_id",
        "packet_type",
        "source_task",
        "incident_context_id",
        "event_ref",
        "affected_entity_refs",
        "edge_refs",
        "evidence_refs",
        "limitation_refs",
        "review_state",
        "confidence_summary",
        "display_state",
        "operator_label",
        "surface_targets",
        "allowed_surface_actions",
        "forbidden_surface_actions",
        "trace_refs",
        "claim_boundary",
    ]
    results = []
    for packet in fixtures["packets"]:
        missing = [field for field in required if packet.get(field) in (None, "", [], {})]
        checks = {
            "schema_required_fields": not missing,
            "evidence_refs_preserved": bool(packet.get("evidence_refs")),
            "limitation_refs_preserved": bool(packet.get("limitation_refs")),
            "trace_refs_preserved": bool(packet.get("trace_refs")),
            "review_state_preserved": bool(packet.get("review_state")),
            "unresolved_quarantined_not_promoted": not (
                packet.get("display_state") in {"unresolved_context", "quarantined_context"}
                and any(word in str(packet.get("operator_label", "")).lower() for word in ["confirmed", "certified", "official"])
            ),
            "safe_next_look_not_action": packet.get("packet_type") != "safe_next_look_surface_packet" or packet.get("display_state") == "safe_next_look_suggestion",
            "allowed_actions_present": set(ALLOWED_SURFACE_ACTIONS).issubset(set(packet.get("allowed_surface_actions", []))),
            "forbidden_actions_present": set(FORBIDDEN_SURFACE_ACTIONS).issubset(set(packet.get("forbidden_surface_actions", []))),
            "omniverse_handoff_only": packet.get("packet_type") != "omniverse_operator_overlay_packet" or packet.get("no_action_taken") is True,
            "web_handoff_only": packet.get("packet_type") != "web_operator_companion_packet" or packet.get("no_action_taken") is True,
        }
        results.append(
            {
                "packet_id": packet["packet_id"],
                "packet_type": packet["packet_type"],
                "fixture_kind": packet["fixture_kind"],
                "status": "PASS" if all(checks.values()) else "FAIL",
                "missing_fields": missing,
                "checks": checks,
            }
        )
    pass_count = sum(row["status"] == "PASS" for row in results)
    fail_count = len(results) - pass_count
    report = {"status": "PASS" if fail_count == 0 else "FAIL", "packet_validation_pass_count": pass_count, "packet_validation_fail_count": fail_count, "results": results}
    write_json(OUTPUT_ROOT / "PACKET_VALIDATION_RESULTS.json", report)
    return report


def audit_claims() -> dict[str, Any]:
    positive_patterns = [
        r'"autonomous_monitoring"\s*:\s*true',
        r'"live_incident_detection"\s*:\s*true',
        r'"alert_push"\s*:\s*true',
        r'"dispatch"\s*:\s*true',
        r'"routing_control"\s*:\s*true',
        r'"enforcement"\s*:\s*true',
        r'"official_ticket"\s*:\s*true',
        r'"legal_certified_confirmed"\s*:\s*true',
        r'"automated_action"\s*:\s*true',
        r'"production_public_api_readiness"\s*:\s*true',
        r'"production_omniverse_deployment"\s*:\s*true',
        r'"citywide_certified_digital_twin"\s*:\s*true',
        r"production ui implementation",
        r"scene generation completed",
        r"official incident status",
    ]
    joined = ""
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name not in {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.json"} and item.suffix.lower() in {".json", ".md", ".txt", ".jsonl"}:
            joined += "\n" + item.read_text(encoding="utf-8", errors="ignore").lower()
    hits = [pattern for pattern in positive_patterns if re.search(pattern, joined)]
    report = {"status": "PASS" if not hits else "FAIL", "positive_forbidden_claim_hits": hits, "claim_boundary": BOUNDARY}
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", report)
    return report


def audit_no_action(fixtures: dict[str, Any]) -> dict[str, Any]:
    bad_packets = []
    for packet in fixtures["packets"]:
        if packet.get("no_action_taken") is not True:
            bad_packets.append(packet["packet_id"])
        if not set(FORBIDDEN_SURFACE_ACTIONS).issubset(set(packet.get("forbidden_surface_actions", []))):
            bad_packets.append(packet["packet_id"])
    report = {
        "status": "PASS" if not bad_packets else "FAIL",
        "bad_packets": sorted(set(bad_packets)),
        "safe_next_look_policy": "display/review only",
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
        if item.is_file() and item.name != "HASH_MANIFEST.json" and item.suffix.lower() in {".json", ".md", ".txt", ".jsonl"}:
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


def write_readme_index(fixtures: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

This pack translates frozen Incident Mode evidence-bundle and operator-review outputs into bounded Track2A/Omniverse and web companion operator-surface handoff packets.

Fixture packets: `{fixtures['packet_count']}`

This is a contract and fixture task only. It does not implement a production UI, public API, Omniverse scene generation, autonomous monitoring, alert push, dispatch, routing/control, enforcement, legal/certified outcome, official ticket/case creation, or automated action.

Boundary: {BOUNDARY}
""",
    )
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Fixture packets: `{fixtures['packet_count']}`",
        "",
        BOUNDARY,
        "",
        "## Artifacts",
        "",
    ]
    files = EXPECTED_FILES + ["EVIDENCE_LIMITATION_SURFACE_PACKET_SCHEMA.json"]
    lines.extend(f"- [{name}]({name})" for name in files)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pre = {meta["root"]: snapshot(root_path(meta["root"])) for meta in UPSTREAMS.values()}
    input_index, missing = discover_inputs(pre)
    upstream = upstream_summary(input_index)
    sources = load_sources()
    contracts = write_contracts()
    write_impact_docs(sources)
    fixtures = build_fixtures(sources)
    validation = validate_packets(fixtures)
    claim = audit_claims()
    no_action = audit_no_action(fixtures)
    mutation = audit_mutation(pre)
    secret = audit_secret()
    write_readme_index(fixtures)

    status = PASS_STATUS
    if not all(
        [
            not missing,
            input_index["status"] == "PASS",
            upstream["status"] == "PASS",
            contracts["handoff"]["status"] == "PASS",
            fixtures["status"] == "PASS",
            validation["status"] == "PASS",
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
        "upstreams_discovered": input_index["discovered_count"],
        "upstreams_required": input_index["required_count"],
        "missing_required_upstreams": missing,
        "operator_surface_packet_count": fixtures["packet_count"],
        "omniverse_overlay_packet_count": fixtures["omniverse_overlay_packet_count"],
        "web_companion_packet_count": fixtures["web_companion_packet_count"],
        "unresolved_quarantined_preserved_count": fixtures["unresolved_quarantined_preserved_count"],
        "safe_next_look_packet_count": fixtures["safe_next_look_packet_count"],
        "packet_validation_pass_count": validation["packet_validation_pass_count"],
        "packet_validation_fail_count": validation["packet_validation_fail_count"],
        "claim_boundary_result": claim["status"],
        "no_action_boundary_result": no_action["status"],
        "no_mutation_result": mutation["status"],
        "secret_audit_result": secret["status"],
        "hash_validation_result": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-ASSET-BINDING-R1",
        "alternative_next_task": "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-PREFLIGHT",
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_DECISION.json", decision)
    manifest = hash_manifest()
    decision["hash_validation_result"] = manifest["status"]
    if manifest["status"] != "PASS":
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
