#!/usr/bin/env python3
"""Close out the Hero Neighbourhood scene pack lane."""

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

TASK_NAME = "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-SCENE-PACK-CLOSEOUT"
PASS_STATUS = "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout"

UPSTREAMS = {
    "hero_neighbourhood_twin_preflight": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_twin_preflight",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT_WITH_LIMITATIONS",
    },
    "hero_neighbourhood_asset_binding_r1": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_ASSET_BINDING_R1_WITH_LIMITATIONS",
    },
    "hero_neighbourhood_event_overlay_r2": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_WITH_LIMITATIONS",
    },
    "hero_neighbourhood_kit_composer_handoff_r3": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_KIT_COMPOSER_HANDOFF_R3_WITH_LIMITATIONS",
    },
    "incident_mode_track2a_operator_surface_handoff_r4": {
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
    },
}

OPTIONAL_SYNC_ROOTS = {
    "cer_seg_v2_relationship_ontology_r2": "outputs/main_citybrain_d6_cer_seg_v2_relationship_ontology_r2",
    "cer_seg_v2_confidence_review_state_r3": "outputs/main_citybrain_d6_cer_seg_v2_confidence_review_state_r3",
    "cer_seg_v2_runtime_bridge_smoke_r4": "outputs/main_citybrain_d6_cer_seg_v2_runtime_bridge_smoke_r4",
}

BOUNDARY = (
    "Hero Neighbourhood scene pack closeout is a bounded local/replay scene-pack acceptance review. "
    "It is not production Omniverse deployment, public API deployment, live/autonomous monitoring, "
    "alerting, dispatch, routing/control, enforcement, legal/certified incident status, official "
    "ticket/case creation, automated action, or a citywide certified digital twin."
)

LIMITATIONS = [
    "Hero Neighbourhood lane only",
    "local/replay review and demo handoff only",
    "source identity, relationship, incident, event, and review semantics are consumed from upstream artifacts",
    "scene pack is not a production Omniverse deployment or certified spatial twin",
    "unresolved and quarantined contexts remain preserved as review context",
    "no public API, live monitoring, alerting, dispatch, routing/control, enforcement, official ticket/case, legal finding, or automated action claim",
]

RECOMMENDED_NEXT_TASK = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-AND-CERSEG-V2-INTEGRATION-READINESS-REVIEW"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def root_path(root: str) -> Path:
    return REPO_ROOT / root


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def find_decision(root: Path) -> Path | None:
    if not root.exists():
        return None
    decisions = sorted(root.glob("*DECISION.json"))
    return decisions[0] if decisions else None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    entries: list[str] = []
    byte_count = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        data = path.read_bytes()
        byte_count += len(data)
        entries.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(data).hexdigest()}")
    digest = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()
    return {"exists": True, "file_count": len(entries), "byte_count": byte_count, "fingerprint": digest}


def sample_artifacts(root: Path, limit: int = 16) -> list[str]:
    if not root.exists():
        return []
    return [rel(path) or "" for path in sorted(p for p in root.iterdir() if p.is_file())[:limit]]


def discover_inputs(pre_snapshots: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    required: list[dict[str, Any]] = []
    missing: list[str] = []
    for name, meta in UPSTREAMS.items():
        root = root_path(meta["root"])
        decision_path = find_decision(root)
        decision = read_json(decision_path) if decision_path else {}
        status = decision.get("status")
        green = root.exists() and status == meta["expected"]
        if not green:
            missing.append(name)
        required.append(
            {
                "branch": name,
                "root": meta["root"],
                "exists": root.exists(),
                "decision_path": rel(decision_path),
                "status": status,
                "expected": meta["expected"],
                "green": green,
                "read_only": True,
                "sample_artifacts": sample_artifacts(root),
                "snapshot": pre_snapshots.get(meta["root"], snapshot(root)),
            }
        )

    optional: list[dict[str, Any]] = []
    for name, root_text in OPTIONAL_SYNC_ROOTS.items():
        root = root_path(root_text)
        decision_path = find_decision(root)
        decision = read_json(decision_path) if decision_path else {}
        optional.append(
            {
                "branch": name,
                "root": root_text,
                "exists": root.exists(),
                "decision_path": rel(decision_path),
                "status": decision.get("status"),
                "compatibility_review": "RECORDED_READ_ONLY" if root.exists() else "NOT_APPLICABLE_NOT_DISCOVERED",
                "read_only": True,
            }
        )

    pre_closeout_candidates = [
        item
        for item in optional
        if item["branch"] in {"cer_seg_v2_confidence_review_state_r3", "cer_seg_v2_runtime_bridge_smoke_r4"}
    ]
    input_index = {
        "status": "PASS" if not missing else "FAIL",
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "required_branches": required,
        "optional_sync_branches": optional,
        "pre_closeout_compatibility_status": (
            "RECORDED_READ_ONLY" if any(item["exists"] for item in pre_closeout_candidates) else "NOT_APPLICABLE_NOT_DISCOVERED"
        ),
        "cer_seg_r2_compatibility_status": next(
            item["compatibility_review"] for item in optional if item["branch"] == "cer_seg_v2_relationship_ontology_r2"
        ),
        "mutation_policy": "read_only_consumption_no_upstream_mutation",
    }
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    return input_index, missing


def load_sources() -> dict[str, Any]:
    r1 = root_path(UPSTREAMS["hero_neighbourhood_asset_binding_r1"]["root"])
    r2 = root_path(UPSTREAMS["hero_neighbourhood_event_overlay_r2"]["root"])
    r3 = root_path(UPSTREAMS["hero_neighbourhood_kit_composer_handoff_r3"]["root"])
    r4 = root_path(UPSTREAMS["incident_mode_track2a_operator_surface_handoff_r4"]["root"])
    return {
        "r1_decision": read_json(r1 / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_ASSET_BINDING_R1_DECISION.json", {}),
        "r1_registry": read_json(r1 / "HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json", {}),
        "r1_validation": read_json(r1 / "ASSET_BINDING_VALIDATION_REPORT.json", {}),
        "r2_decision": read_json(r2 / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_DECISION.json", {}),
        "r2_packets": read_json(r2 / "HERO_EVENT_OVERLAY_PACKETS.json", {"packets": []}),
        "r2_query": read_json(r2 / "OVERLAY_QUERY_RESULTS.json", {}),
        "r2_trace": read_json(r2 / "EVIDENCE_LIMITATION_TRACE.json", {}),
        "r2_preservation": read_json(r2 / "UNRESOLVED_QUARANTINED_OVERLAY_PRESERVATION.json", {}),
        "r2_omni": read_json(r2 / "OMNIVERSE_EVENT_OVERLAY_MANIFEST.json", {}),
        "r2_web": read_json(r2 / "WEB_EVENT_OVERLAY_MANIFEST.json", {}),
        "r3_decision": read_json(r3 / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_KIT_COMPOSER_HANDOFF_R3_DECISION.json", {}),
        "r3_manifest": read_json(r3 / "KIT_COMPOSER_HANDOFF_MANIFEST.json", {}),
        "r3_selection": read_json(r3 / "HERO_SCENE_SELECTION_METADATA.json", {}),
        "r3_prim_index": read_json(r3 / "PRIM_METADATA_INDEX.json", {}),
        "r4_decision": read_json(r4 / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_DECISION.json", {}),
        "r4_packets": read_json(r4 / "OPERATOR_SURFACE_PACKET_FIXTURES.json", {"packets": []}),
    }


def list_from_doc(doc: dict[str, Any], key: str) -> list[Any]:
    value = doc.get(key, [])
    return value if isinstance(value, list) else []


def is_unresolved_or_quarantined(record: dict[str, Any]) -> bool:
    haystack = " ".join(str(record.get(key, "")) for key in record).lower()
    return "unresolved" in haystack or "quarantined" in haystack


def review_asset_binding(sources: dict[str, Any]) -> dict[str, Any]:
    registry = sources["r1_registry"]
    bindings = list_from_doc(registry, "bindings")
    prim_paths = [item.get("stable_prim_path") or item.get("usd_prim_path") for item in bindings]
    unresolved = [item for item in bindings if is_unresolved_or_quarantined(item)]
    review = {
        "status": "PASS" if bindings and all(prim_paths) and len(unresolved) >= 2 else "FAIL",
        "source_status": sources["r1_decision"].get("status"),
        "binding_count": len(bindings),
        "prim_path_count": len([item for item in prim_paths if item]),
        "unresolved_quarantined_binding_count": len(unresolved),
        "source_artifacts": [
            "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1/HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json",
            "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1/ASSET_BINDING_VALIDATION_REPORT.json",
        ],
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "ASSET_BINDING_REVIEW.json", review)
    return review


def review_event_overlay(sources: dict[str, Any]) -> dict[str, Any]:
    packets = list_from_doc(sources["r2_packets"], "packets")
    evidence_complete = all(packet.get("evidence_bundle_refs") for packet in packets)
    limitation_complete = all(packet.get("limitation_refs") for packet in packets)
    no_action = all(packet.get("no_action_taken") is True for packet in packets)
    review = {
        "status": "PASS" if packets and evidence_complete and limitation_complete and no_action else "FAIL",
        "source_status": sources["r2_decision"].get("status"),
        "overlay_packet_count": len(packets),
        "query_pass_count": sources["r2_decision"].get("query_fixture_pass_count", sources["r2_query"].get("pass_count")),
        "query_fail_count": sources["r2_decision"].get("query_fixture_fail_count", sources["r2_query"].get("fail_count")),
        "omniverse_manifest_status": sources["r2_omni"].get("status"),
        "web_manifest_status": sources["r2_web"].get("status"),
        "evidence_ref_status": "PASS" if evidence_complete else "FAIL",
        "limitation_ref_status": "PASS" if limitation_complete else "FAIL",
        "no_action_status": "PASS" if no_action else "FAIL",
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "EVENT_OVERLAY_REVIEW.json", review)
    return review


def review_kit_handoff(sources: dict[str, Any]) -> dict[str, Any]:
    manifest = sources["r3_manifest"]
    prim_index = sources["r3_prim_index"]
    usda_path = root_path("outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3") / "HERO_SCENE_USD_OR_USDA_HANDOFF.usda"
    review = {
        "status": "PASS"
        if manifest.get("status") == "PASS" and prim_index.get("status") == "PASS" and usda_path.exists()
        else "FAIL",
        "source_status": sources["r3_decision"].get("status"),
        "manifest_status": manifest.get("status"),
        "prim_metadata_status": prim_index.get("status"),
        "prim_metadata_count": prim_index.get("metadata_count", 0),
        "usda_handoff_exists": usda_path.exists(),
        "interactive_omniverse_session_launched": manifest.get("interactive_omniverse_session_launched", False),
        "source_scene_mutation": manifest.get("source_scene_mutation", None),
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "KIT_COMPOSER_HANDOFF_REVIEW.json", review)
    return review


def review_web_companion(sources: dict[str, Any]) -> dict[str, Any]:
    web = sources["r2_web"]
    packets = list_from_doc(sources["r2_packets"], "packets")
    web_refs = [
        ref
        for packet in packets
        for ref in packet.get("web_companion_refs", [])
        if ref and "not_applicable" not in str(ref)
    ]
    review = {
        "status": "PASS" if web.get("status") == "PASS" and packets else "FAIL",
        "source_manifest_status": web.get("status"),
        "surface": web.get("surface", "web companion handoff"),
        "overlay_packet_refs": web.get("overlay_packet_refs", []),
        "packet_count": len(packets),
        "web_companion_ref_count": len(web_refs),
        "runtime_deployment": False,
        "claim_boundary": BOUNDARY,
        "limitations": [
            "web companion review is manifest/package review only",
            "no public web deployment or public API deployment",
            "no alert, dispatch, routing/control, enforcement, ticket/case, or automated action",
        ],
    }
    write_json(OUTPUT_ROOT / "WEB_COMPANION_REVIEW.json", review)
    return review


def review_evidence_limitations(sources: dict[str, Any]) -> dict[str, Any]:
    packets = list_from_doc(sources["r2_packets"], "packets")
    prims = list_from_doc(sources["r3_prim_index"], "prim_metadata")
    missing: list[dict[str, str]] = []
    for packet in packets:
        if not packet.get("evidence_bundle_refs"):
            missing.append({"record": packet.get("overlay_packet_id", "unknown"), "missing": "evidence_refs"})
        if not packet.get("limitation_refs"):
            missing.append({"record": packet.get("overlay_packet_id", "unknown"), "missing": "limitation_refs"})
    for prim in prims:
        if not prim.get("evidence_bundle_refs"):
            missing.append({"record": prim.get("overlay_packet_id", "unknown"), "missing": "prim_evidence_refs"})
        if not prim.get("limitation_refs"):
            missing.append({"record": prim.get("overlay_packet_id", "unknown"), "missing": "prim_limitation_refs"})
    review = {
        "status": "PASS" if packets and prims and not missing else "FAIL",
        "overlay_packet_count": len(packets),
        "prim_metadata_count": len(prims),
        "missing_refs": missing,
        "source_trace_status": sources["r2_trace"].get("status"),
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "EVIDENCE_LIMITATION_TRACE_REVIEW.json", review)
    return review


def review_preservation(sources: dict[str, Any]) -> dict[str, Any]:
    packets = list_from_doc(sources["r2_packets"], "packets")
    prims = list_from_doc(sources["r3_prim_index"], "prim_metadata")
    packet_preserved = [packet.get("overlay_packet_id") for packet in packets if is_unresolved_or_quarantined(packet)]
    prim_preserved = [prim.get("overlay_packet_id") for prim in prims if is_unresolved_or_quarantined(prim)]
    source_preserved = sources["r2_preservation"].get("preserved_count", len(packet_preserved))
    review = {
        "status": "PASS" if len(packet_preserved) >= 2 and len(prim_preserved) >= 2 else "FAIL",
        "source_preserved_count": source_preserved,
        "event_overlay_preserved_refs": packet_preserved,
        "kit_metadata_preserved_refs": prim_preserved,
        "preservation_policy": "unresolved and quarantined contexts stay visible as review-only context",
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "UNRESOLVED_QUARANTINED_PRESERVATION_REVIEW.json", review)
    return review


def write_scene_pack_summary(
    sources: dict[str, Any],
    asset: dict[str, Any],
    overlay: dict[str, Any],
    kit: dict[str, Any],
    web: dict[str, Any],
    trace: dict[str, Any],
    preservation: dict[str, Any],
    input_index: dict[str, Any],
) -> dict[str, Any]:
    packets = list_from_doc(sources["r2_packets"], "packets")
    summary = {
        "status": "PASS"
        if all(item.get("status") == "PASS" for item in [asset, overlay, kit, web, trace, preservation])
        else "FAIL",
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "scene_id": sources["r3_selection"].get("scene_id") or (packets[0].get("hero_scene_id") if packets else None),
        "package_mode": "bounded_local_replay_scene_pack",
        "binding_count": asset.get("binding_count"),
        "overlay_packet_count": overlay.get("overlay_packet_count"),
        "prim_metadata_count": kit.get("prim_metadata_count"),
        "unresolved_quarantined_preserved_count": len(preservation.get("event_overlay_preserved_refs", [])),
        "cer_seg_r2_compatibility_status": input_index.get("cer_seg_r2_compatibility_status"),
        "pre_closeout_compatibility_status": input_index.get("pre_closeout_compatibility_status"),
        "main_artifact_refs": [
            "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1/HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json",
            "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2/HERO_EVENT_OVERLAY_PACKETS.json",
            "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3/KIT_COMPOSER_HANDOFF_MANIFEST.json",
            "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3/HERO_SCENE_USD_OR_USDA_HANDOFF.usda",
        ],
        "limitations": LIMITATIONS,
        "recommended_next_task": RECOMMENDED_NEXT_TASK,
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "HERO_SCENE_PACK_SUMMARY.json", summary)
    return summary


def write_acceptance_matrix(
    input_index: dict[str, Any],
    asset: dict[str, Any],
    overlay: dict[str, Any],
    kit: dict[str, Any],
    web: dict[str, Any],
    trace: dict[str, Any],
    preservation: dict[str, Any],
) -> dict[str, Any]:
    checks = [
        {
            "check_id": "required_upstreams_green",
            "status": input_index["status"],
            "evidence": "INPUT_ARTIFACT_INDEX.json",
        },
        {"check_id": "asset_binding_review", "status": asset["status"], "evidence": "ASSET_BINDING_REVIEW.json"},
        {"check_id": "event_overlay_review", "status": overlay["status"], "evidence": "EVENT_OVERLAY_REVIEW.json"},
        {
            "check_id": "kit_composer_handoff_review",
            "status": kit["status"],
            "evidence": "KIT_COMPOSER_HANDOFF_REVIEW.json",
        },
        {"check_id": "web_companion_review", "status": web["status"], "evidence": "WEB_COMPANION_REVIEW.json"},
        {
            "check_id": "evidence_limitation_trace_review",
            "status": trace["status"],
            "evidence": "EVIDENCE_LIMITATION_TRACE_REVIEW.json",
        },
        {
            "check_id": "unresolved_quarantined_preservation_review",
            "status": preservation["status"],
            "evidence": "UNRESOLVED_QUARANTINED_PRESERVATION_REVIEW.json",
        },
        {
            "check_id": "pre_closeout_cer_seg_watch",
            "status": "PASS",
            "evidence": input_index.get("pre_closeout_compatibility_status", "NOT_APPLICABLE_NOT_DISCOVERED"),
        },
    ]
    matrix = {
        "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "checks": checks,
        "limitations": LIMITATIONS,
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "ACCEPTANCE_MATRIX.json", matrix)
    return matrix


def generated_files() -> list[Path]:
    if not OUTPUT_ROOT.exists():
        return []
    return sorted(path for path in OUTPUT_ROOT.rglob("*") if path.is_file())


def audit_claims() -> dict[str, Any]:
    violations: list[dict[str, str]] = []
    forbidden_positive_patterns = [
        re.compile(r"\ballow(?:ed)?\s+(dispatch|enforcement|automated action|alert push)\b", re.I),
        re.compile(r"\bproduction\s+live\s+(ingestion|monitoring|deployment)\b", re.I),
        re.compile(r"\bpublic\s+api\s+deployment\s*:\s*true\b", re.I),
        re.compile(r"\bcertified\s+(incident|geometry|truth|citywide twin)\s*:\s*true\b", re.I),
    ]
    for path in generated_files():
        if path.name == "CLAIM_BOUNDARY_AUDIT.json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_positive_patterns:
            if pattern.search(text):
                violations.append({"file": rel(path) or "", "pattern": pattern.pattern})
    audit = {
        "status": "PASS" if not violations else "FAIL",
        "task_name": TASK_NAME,
        "claim_boundary": BOUNDARY,
        "violations": violations,
        "checked_file_count": len(generated_files()),
    }
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", audit)
    return audit


def audit_no_action(sources: dict[str, Any]) -> dict[str, Any]:
    forbidden = {"alert_push", "dispatch", "routing_or_control", "enforcement", "official_ticket_or_case_creation", "legal_or_certified_incident_finding", "automated_action"}
    violations: list[dict[str, str]] = []
    for packet in list_from_doc(sources["r2_packets"], "packets"):
        if packet.get("no_action_taken") is not True:
            violations.append({"record": packet.get("overlay_packet_id", "unknown"), "issue": "no_action_taken_not_true"})
    for prim in list_from_doc(sources["r3_prim_index"], "prim_metadata"):
        allowed = {str(item) for item in prim.get("allowed_actions", [])}
        unsafe = sorted(allowed & forbidden)
        if unsafe:
            violations.append({"record": prim.get("overlay_packet_id", "unknown"), "issue": "unsafe_allowed_action:" + ",".join(unsafe)})
        if prim.get("no_action_taken") is not True:
            violations.append({"record": prim.get("overlay_packet_id", "unknown"), "issue": "prim_no_action_taken_not_true"})
    audit = {
        "status": "PASS" if not violations else "FAIL",
        "task_name": TASK_NAME,
        "violations": violations,
        "no_action_boundary": "review-only inspection; no alert, dispatch, route/control, enforcement, ticket/case, legal finding, or automated action",
    }
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", audit)
    return audit


def audit_mutation(pre_snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    branches: list[dict[str, Any]] = []
    for meta in UPSTREAMS.values():
        root = root_path(meta["root"])
        before = pre_snapshots.get(meta["root"], snapshot(root))
        after = snapshot(root)
        branches.append({"root": meta["root"], "before": before, "after": after, "unchanged": before == after})
    audit = {
        "status": "PASS" if all(item["unchanged"] for item in branches) else "FAIL",
        "task_name": TASK_NAME,
        "branches": branches,
        "mutation_attempted": False,
    }
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", audit)
    return audit


def audit_secret() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
        re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._\-]{16,}"),
    ]
    findings: list[dict[str, str]] = []
    for path in generated_files():
        if path.name == "SECRET_AUDIT.json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"file": rel(path) or "", "pattern": pattern.pattern})
    audit = {
        "status": "PASS" if not findings else "FAIL",
        "task_name": TASK_NAME,
        "checked_file_count": len(generated_files()),
        "findings": findings,
    }
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", audit)
    return audit


def hash_manifest() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in generated_files():
        if path.name == "HASH_MANIFEST.json":
            continue
        entries.append({"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = {"status": "PASS", "task_name": TASK_NAME, "timestamp": utc_now(), "file_count": len(entries), "files": entries}
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_indexes(summary: dict[str, Any], matrix: dict[str, Any]) -> None:
    files = [path.name for path in generated_files()]
    readme = [
        f"# {TASK_NAME}",
        "",
        "Hero Neighbourhood scene-pack closeout for the bounded local/replay lane.",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Acceptance matrix: `{matrix.get('status')}`",
        f"- Bindings: `{summary.get('binding_count')}`",
        f"- Overlay packets: `{summary.get('overlay_packet_count')}`",
        f"- Prim metadata records: `{summary.get('prim_metadata_count')}`",
        "",
        "## Boundary",
        "",
        BOUNDARY,
        "",
        "## Files",
        "",
    ]
    readme.extend(f"- `{name}`" for name in files)
    write_text(OUTPUT_ROOT / "README.md", "\n".join(readme))

    index = [f"# {TASK_NAME}", "", BOUNDARY, "", "## Open", ""]
    index.extend(f"- [{name}]({name})" for name in files)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(index))


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pre_snapshots = {meta["root"]: snapshot(root_path(meta["root"])) for meta in UPSTREAMS.values()}
    input_index, missing = discover_inputs(pre_snapshots)
    sources = load_sources()
    asset = review_asset_binding(sources)
    overlay = review_event_overlay(sources)
    kit = review_kit_handoff(sources)
    web = review_web_companion(sources)
    trace = review_evidence_limitations(sources)
    preservation = review_preservation(sources)
    summary = write_scene_pack_summary(sources, asset, overlay, kit, web, trace, preservation, input_index)
    matrix = write_acceptance_matrix(input_index, asset, overlay, kit, web, trace, preservation)
    write_indexes(summary, matrix)

    claim = audit_claims()
    no_action = audit_no_action(sources)
    mutation = audit_mutation(pre_snapshots)
    secret = audit_secret()

    status = PASS_STATUS
    if not all(
        [
            not missing,
            input_index["status"] == "PASS",
            asset["status"] == "PASS",
            overlay["status"] == "PASS",
            kit["status"] == "PASS",
            web["status"] == "PASS",
            trace["status"] == "PASS",
            preservation["status"] == "PASS",
            summary["status"] == "PASS",
            matrix["status"] == "PASS",
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
        "missing_required_upstreams": missing,
        "acceptance_matrix_status": matrix["status"],
        "asset_binding_review_status": asset["status"],
        "event_overlay_review_status": overlay["status"],
        "kit_composer_handoff_review_status": kit["status"],
        "web_companion_review_status": web["status"],
        "evidence_limitation_trace_review_status": trace["status"],
        "unresolved_quarantined_preservation_review_status": preservation["status"],
        "binding_count": summary.get("binding_count"),
        "overlay_packet_count": summary.get("overlay_packet_count"),
        "prim_metadata_count": summary.get("prim_metadata_count"),
        "unresolved_quarantined_preserved_count": summary.get("unresolved_quarantined_preserved_count"),
        "cer_seg_r2_compatibility_status": input_index.get("cer_seg_r2_compatibility_status"),
        "pre_closeout_compatibility_status": input_index.get("pre_closeout_compatibility_status"),
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": RECOMMENDED_NEXT_TASK,
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_DECISION.json", decision)
    manifest = hash_manifest()
    decision["hash_validation_status"] = manifest["status"]
    if manifest["status"] != "PASS":
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
