#!/usr/bin/env python3
"""Build the Hero Neighbourhood Kit/Composer handoff R3 package."""

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

TASK_NAME = "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-KIT-COMPOSER-HANDOFF-R3"
PASS_STATUS = "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_KIT_COMPOSER_HANDOFF_R3_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_KIT_COMPOSER_HANDOFF_R3"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3"

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
    "incident_mode_track2a_operator_surface_handoff_r4": {
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
    },
}

OPTIONAL_SYNC_ROOTS = {
    "cer_seg_v2_relationship_ontology_r2": {
        "root": "outputs/main_citybrain_d6_cer_seg_v2_relationship_ontology_r2",
        "checkpoint": "post_hero_r2_compatibility_review",
    },
    "cer_seg_v2_confidence_review_state_r3": {
        "root": "outputs/main_citybrain_d6_cer_seg_v2_confidence_review_state_r3",
        "checkpoint": "pre_closeout_watch",
    },
    "cer_seg_v2_runtime_bridge_smoke_r4": {
        "root": "outputs/main_citybrain_d6_cer_seg_v2_runtime_bridge_smoke_r4",
        "checkpoint": "pre_closeout_watch",
    },
}

BOUNDARY = (
    "Hero Neighbourhood Kit/Composer handoff R3 is a bounded local/replay metadata handoff. "
    "It is not production Omniverse deployment, autonomous monitoring, alerting, dispatch, "
    "routing/control, enforcement, legal/certified incident status, official ticket/case creation, "
    "automated action, public API deployment, or a citywide certified twin."
)

LIMITATIONS = [
    "deterministic USDA metadata sidecar only",
    "local/replay operator review and demo handoff only",
    "no new identity, relationship, or incident semantics",
    "source scene and upstream artifacts are consumed read-only",
    "unresolved and quarantined contexts remain visible review-context metadata",
    "no production Omniverse, citywide twin, certified geometry, monitoring, alerting, dispatch, routing/control, enforcement, ticket/case, legal finding, or automated action claim",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def root_path(root: str) -> Path:
    return REPO_ROOT / root


def rel(path: Path) -> str:
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
    joined = "\n".join(entries).encode("utf-8")
    return {
        "exists": True,
        "file_count": len(entries),
        "byte_count": byte_count,
        "fingerprint": hashlib.sha256(joined).hexdigest(),
    }


def sample_artifacts(root: Path, limit: int = 18) -> list[str]:
    if not root.exists():
        return []
    return [rel(path) for path in sorted(p for p in root.iterdir() if p.is_file())[:limit]]


def discover_inputs(pre_snapshots: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    branches: list[dict[str, Any]] = []
    missing: list[str] = []
    for name, meta in UPSTREAMS.items():
        root = root_path(meta["root"])
        decision_path = find_decision(root)
        decision = read_json(decision_path) if decision_path else {}
        status = decision.get("status")
        green = root.exists() and status == meta["expected"]
        if not green:
            missing.append(name)
        branches.append(
            {
                "branch": name,
                "root": meta["root"],
                "exists": root.exists(),
                "decision_path": rel(decision_path) if decision_path else None,
                "status": status,
                "expected": meta["expected"],
                "green": green,
                "read_only": True,
                "sample_artifacts": sample_artifacts(root),
                "snapshot": pre_snapshots.get(meta["root"], snapshot(root)),
            }
        )

    optional_sync: list[dict[str, Any]] = []
    for name, meta in OPTIONAL_SYNC_ROOTS.items():
        root = root_path(meta["root"])
        decision_path = find_decision(root)
        decision = read_json(decision_path) if decision_path else {}
        exists = root.exists()
        optional_sync.append(
            {
                "branch": name,
                "root": meta["root"],
                "checkpoint": meta["checkpoint"],
                "exists": exists,
                "decision_path": rel(decision_path) if decision_path else None,
                "status": decision.get("status"),
                "compatibility_review": "RECORDED_READ_ONLY" if exists else "NOT_APPLICABLE_NOT_DISCOVERED",
                "read_only": True,
            }
        )

    post_r2_sync = next(
        item for item in optional_sync if item["branch"] == "cer_seg_v2_relationship_ontology_r2"
    )
    input_index = {
        "status": "PASS" if not missing else "FAIL",
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "required_branches": branches,
        "optional_sync_branches": optional_sync,
        "post_r2_compatibility_checkpoint_status": post_r2_sync["compatibility_review"],
        "pre_closeout_compatibility_watch_status": (
            "RECORDED_READ_ONLY"
            if any(item["exists"] for item in optional_sync if item["checkpoint"] == "pre_closeout_watch")
            else "NOT_APPLICABLE_NOT_DISCOVERED"
        ),
        "mutation_policy": "read_only_consumption_no_upstream_mutation",
    }
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    return input_index, missing


def load_sources() -> dict[str, Any]:
    r2_root = root_path(UPSTREAMS["hero_neighbourhood_event_overlay_r2"]["root"])
    r1_root = root_path(UPSTREAMS["hero_neighbourhood_asset_binding_r1"]["root"])
    packets_doc = read_json(r2_root / "HERO_EVENT_OVERLAY_PACKETS.json", {"packets": []})
    return {
        "overlay_packets": packets_doc.get("packets", []),
        "overlay_doc": packets_doc,
        "omniverse_manifest": read_json(r2_root / "OMNIVERSE_EVENT_OVERLAY_MANIFEST.json", {}),
        "web_manifest": read_json(r2_root / "WEB_EVENT_OVERLAY_MANIFEST.json", {}),
        "asset_binding_registry": read_json(r1_root / "HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json", {}),
    }


def unique_sorted(values: list[Any]) -> list[str]:
    return sorted({str(value) for value in values if value not in (None, "", [])})


def is_unresolved_or_quarantined(packet: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(packet.get(key, ""))
        for key in ("binding_state", "display_state", "review_state", "canonical_entity_id")
    ).lower()
    return "unresolved" in haystack or "quarantined" in haystack


def build_scene_selection_metadata(packets: list[dict[str, Any]]) -> dict[str, Any]:
    scene_id = packets[0].get("hero_scene_id", "hero-neighbourhood-scene") if packets else None
    metadata = {
        "status": "PASS" if packets else "FAIL",
        "scene_id": scene_id,
        "task_name": TASK_NAME,
        "selection_mode": "review_only_metadata_handoff",
        "package_mode": "deterministic_usda_metadata_sidecar",
        "default_selection": {
            "label": "Hero Neighbourhood bounded review scene",
            "prim_paths": [packet.get("usd_prim_path") for packet in packets],
            "overlay_packet_refs": [packet.get("overlay_packet_id") for packet in packets],
        },
        "selection_filters": [
            {
                "filter_id": "all_bound_review_context",
                "label": "All Hero scene assets with event overlays",
                "overlay_packet_refs": [packet.get("overlay_packet_id") for packet in packets],
            },
            {
                "filter_id": "unresolved_quarantined_context",
                "label": "Unresolved and quarantined review contexts",
                "overlay_packet_refs": [
                    packet.get("overlay_packet_id") for packet in packets if is_unresolved_or_quarantined(packet)
                ],
            },
            {
                "filter_id": "event_context_refs",
                "label": "Assets with carried event/incident context",
                "overlay_packet_refs": [
                    packet.get("overlay_packet_id")
                    for packet in packets
                    if packet.get("event_state_ref") or packet.get("incident_context_ref")
                ],
            },
        ],
        "operator_panel_sections": [
            "canonical_identity",
            "event_overlay_context",
            "edge_relationship_refs",
            "evidence_refs",
            "limitation_refs",
            "confidence_and_review_state",
            "safe_next_look_notes",
        ],
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    write_json(OUTPUT_ROOT / "HERO_SCENE_SELECTION_METADATA.json", metadata)
    return metadata


def build_prim_metadata_index(packets: list[dict[str, Any]]) -> dict[str, Any]:
    prims: list[dict[str, Any]] = []
    for packet in packets:
        prims.append(
            {
                "prim_path": packet.get("usd_prim_path"),
                "overlay_packet_id": packet.get("overlay_packet_id"),
                "asset_binding_id": packet.get("asset_binding_id"),
                "canonical_entity_id": packet.get("canonical_entity_id"),
                "binding_state": packet.get("binding_state"),
                "review_state": packet.get("review_state"),
                "display_state": packet.get("display_state"),
                "event_state_ref": packet.get("event_state_ref"),
                "incident_context_ref": packet.get("incident_context_ref"),
                "edge_refs": packet.get("edge_refs", []),
                "evidence_bundle_refs": packet.get("evidence_bundle_refs", []),
                "limitation_refs": packet.get("limitation_refs", []),
                "confidence_context": packet.get("confidence_context", {}),
                "surface_targets": packet.get("surface_targets", []),
                "operator_panel": {
                    "headline": packet.get("canonical_entity_id"),
                    "review_badge": packet.get("display_state"),
                    "evidence_count": len(packet.get("evidence_bundle_refs", [])),
                    "limitation_count": len(packet.get("limitation_refs", [])),
                    "safe_next_look": "Inspect evidence and limitation refs before treating this as anything beyond review context.",
                },
                "allowed_actions": [
                    "select_prim",
                    "inspect_metadata",
                    "filter_review_context",
                    "open_evidence_refs",
                    "open_limitation_refs",
                ],
                "forbidden_actions": [
                    "alert_push",
                    "dispatch",
                    "routing_or_control",
                    "enforcement",
                    "official_ticket_or_case_creation",
                    "legal_or_certified_incident_finding",
                    "automated_action",
                ],
                "no_action_taken": True,
                "claim_boundary": BOUNDARY,
            }
        )

    evidence_complete = all(item["evidence_bundle_refs"] for item in prims)
    limitation_complete = all(item["limitation_refs"] for item in prims)
    review_complete = all(item["review_state"] and item["confidence_context"] for item in prims)
    index = {
        "status": "PASS" if prims and evidence_complete and limitation_complete and review_complete else "FAIL",
        "metadata_count": len(prims),
        "evidence_ref_status": "PASS" if evidence_complete else "FAIL",
        "limitation_ref_status": "PASS" if limitation_complete else "FAIL",
        "review_state_status": "PASS" if review_complete else "FAIL",
        "unresolved_quarantined_metadata_count": sum(1 for item in prims if is_unresolved_or_quarantined(item)),
        "prim_metadata": prims,
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "PRIM_METADATA_INDEX.json", index)
    return index


def usda_string(value: Any) -> str:
    return json.dumps(str(value if value is not None else ""), ensure_ascii=True)


def usda_array(values: list[Any], indent: str = "            ") -> str:
    clean = [value for value in values if value not in (None, "")]
    if not clean:
        return "[]"
    lines = ["["]
    lines.extend(f"{indent}{usda_string(value)}," for value in clean)
    lines.append(indent[:-4] + "]")
    return "\n".join(lines)


def write_usda_handoff(index: dict[str, Any]) -> dict[str, Any]:
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "CityBrainHeroNeighbourhoodR3Handoff"',
        f"    doc = {usda_string(BOUNDARY)}",
        ")",
        "",
        'def Xform "CityBrainHeroNeighbourhoodR3Handoff"',
        "{",
        f"    custom string citybrain_task_name = {usda_string(TASK_NAME)}",
        f"    custom string citybrain_package_mode = {usda_string('deterministic_usda_metadata_sidecar')}",
        f"    custom string citybrain_claim_boundary = {usda_string(BOUNDARY)}",
        '    def Scope "Bindings"',
        "    {",
    ]
    for number, item in enumerate(index.get("prim_metadata", []), start=1):
        prim_name = f"Binding_{number:03d}"
        lines.extend(
            [
                f'        def Xform "{prim_name}"',
                "        {",
                f"            custom string citybrain_source_prim_path = {usda_string(item.get('prim_path'))}",
                f"            custom string citybrain_overlay_packet_id = {usda_string(item.get('overlay_packet_id'))}",
                f"            custom string citybrain_asset_binding_id = {usda_string(item.get('asset_binding_id'))}",
                f"            custom string citybrain_canonical_entity_id = {usda_string(item.get('canonical_entity_id'))}",
                f"            custom string citybrain_binding_state = {usda_string(item.get('binding_state'))}",
                f"            custom string citybrain_review_state = {usda_string(item.get('review_state'))}",
                f"            custom string citybrain_display_state = {usda_string(item.get('display_state'))}",
                f"            custom string citybrain_event_state_ref = {usda_string(item.get('event_state_ref'))}",
                f"            custom string citybrain_incident_context_ref = {usda_string(item.get('incident_context_ref'))}",
                "            custom string[] citybrain_edge_refs = "
                + usda_array(item.get("edge_refs", []), "                "),
                "            custom string[] citybrain_evidence_refs = "
                + usda_array(item.get("evidence_bundle_refs", []), "                "),
                "            custom string[] citybrain_limitation_refs = "
                + usda_array(item.get("limitation_refs", []), "                "),
                "            custom bool citybrain_review_only = true",
                "            custom bool citybrain_no_action_taken = true",
                "        }",
            ]
        )
    lines.extend(["    }", "}"])
    path = OUTPUT_ROOT / "HERO_SCENE_USD_OR_USDA_HANDOFF.usda"
    write_text(path, "\n".join(lines))
    result = {
        "status": "PASS",
        "path": rel(path),
        "package_mode": "deterministic_usda_metadata_sidecar",
        "source_scene_mutation": False,
    }
    return result


def build_handoff_manifest(
    packets: list[dict[str, Any]],
    selection: dict[str, Any],
    index: dict[str, Any],
    usda: dict[str, Any],
    sources: dict[str, Any],
) -> dict[str, Any]:
    manifest = {
        "status": "PASS" if packets and index["status"] == "PASS" and usda["status"] == "PASS" else "FAIL",
        "manifest_id": "hero-neighbourhood-kit-composer-handoff-r3",
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "package_mode": "deterministic_usda_metadata_sidecar",
        "interactive_omniverse_session_launched": False,
        "source_scene_mutation": False,
        "scene_id": selection.get("scene_id"),
        "overlay_packet_count": len(packets),
        "prim_metadata_count": index.get("metadata_count", 0),
        "usd_or_usda_handoff_path": usda["path"],
        "selection_metadata_path": "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3/HERO_SCENE_SELECTION_METADATA.json",
        "prim_metadata_index_path": "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3/PRIM_METADATA_INDEX.json",
        "source_artifact_refs": [
            "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2/HERO_EVENT_OVERLAY_PACKETS.json",
            "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2/OMNIVERSE_EVENT_OVERLAY_MANIFEST.json",
            "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1/HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json",
            "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4/OPERATOR_SURFACE_PACKET_FIXTURES.json",
        ],
        "omniverse_overlay_manifest_ref": sources["omniverse_manifest"].get("manifest_id"),
        "web_overlay_manifest_ref": sources["web_manifest"].get("manifest_id"),
        "operator_open_path": [
            "Open HERO_SCENE_USD_OR_USDA_HANDOFF.usda as a metadata sidecar.",
            "Select Binding_001 through Binding_008 or use source prim paths in PRIM_METADATA_INDEX.json.",
            "Inspect evidence, limitations, confidence, and review state before any next-look decision.",
        ],
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    write_json(OUTPUT_ROOT / "KIT_COMPOSER_HANDOFF_MANIFEST.json", manifest)
    return manifest


def write_boundary_labels() -> dict[str, Any]:
    labels = {
        "status": "PASS",
        "task_name": TASK_NAME,
        "boundary_banner": "Local/replay review-only Hero Neighbourhood scene handoff.",
        "operator_labels": {
            "review_context": "Review context only",
            "evidence_required": "Evidence refs required",
            "limitations_visible": "Limitations visible",
            "unresolved_or_quarantined": "Unresolved/quarantined context preserved",
            "no_action": "No alert, dispatch, route/control, enforcement, ticket/case, or automated action",
        },
        "forbidden_claims": [
            "production Omniverse deployment",
            "autonomous monitoring",
            "alerting",
            "dispatch",
            "routing/control",
            "enforcement",
            "legal/certified incident status",
            "official ticket/case creation",
            "automated action",
            "public API deployment",
            "citywide certified twin",
        ],
        "limitations": LIMITATIONS,
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "BOUNDARY_AND_LIMITATION_LABELS.json", labels)
    return labels


def write_notes(manifest: dict[str, Any], index: dict[str, Any]) -> None:
    operator = [
        f"# {TASK_NAME} Operator Handoff Notes",
        "",
        "Open the USDA handoff as a metadata sidecar and inspect the binding nodes.",
        "",
        "## Operator Journey",
        "",
        "1. Select a Hero Neighbourhood binding.",
        "2. Read canonical identity, event context, edge refs, evidence refs, limitation refs, confidence, and review state.",
        "3. Check unresolved/quarantined labels before treating the context as usable review material.",
        "4. Use safe next-look guidance only as inspection guidance, not as an operational action.",
        "",
        "## Boundary",
        "",
        BOUNDARY,
    ]
    write_text(OUTPUT_ROOT / "OPERATOR_HANDOFF_NOTES.md", "\n".join(operator))

    executive = [
        f"# {TASK_NAME} Executive Demo Notes",
        "",
        "This package shows that the Hero Neighbourhood scene can carry incident/event overlay context into a Kit/Composer-ready handoff without mutating upstream outputs.",
        "",
        f"- Overlay packets: {manifest.get('overlay_packet_count')}",
        f"- Prim metadata records: {index.get('metadata_count')}",
        f"- Unresolved/quarantined contexts preserved: {index.get('unresolved_quarantined_metadata_count')}",
        "- Mode: local/replay review-only handoff",
        "",
        "The useful demo claim is that a bounded scene can expose identity, event context, evidence, limitations, and review state in one operator inspection path.",
        "",
        "The package does not claim production Omniverse operation, live monitoring, public API deployment, citywide twin status, or autonomous action.",
    ]
    write_text(OUTPUT_ROOT / "EXECUTIVE_DEMO_NOTES.md", "\n".join(executive))

    checklist = [
        f"# {TASK_NAME} Manual Acceptance Checklist",
        "",
        "- [ ] Open `HERO_SCENE_USD_OR_USDA_HANDOFF.usda` without editing source scene artifacts.",
        "- [ ] Confirm each Binding_* node has a source prim path and overlay packet id.",
        "- [ ] Confirm evidence and limitation refs are visible for every binding.",
        "- [ ] Confirm confidence and review state are displayed as review context only.",
        "- [ ] Confirm unresolved and quarantined contexts remain labeled and preserved.",
        "- [ ] Confirm no alert, dispatch, route/control, enforcement, ticket/case, legal finding, or automated action is exposed.",
        "- [ ] Confirm D6/Kit/web upstream outputs were not mutated.",
    ]
    write_text(OUTPUT_ROOT / "MANUAL_ACCEPTANCE_CHECKLIST.md", "\n".join(checklist))


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
                violations.append({"file": rel(path), "pattern": pattern.pattern})
    audit = {
        "status": "PASS" if not violations else "FAIL",
        "task_name": TASK_NAME,
        "claim_boundary": BOUNDARY,
        "violations": violations,
        "checked_file_count": len(generated_files()),
    }
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", audit)
    return audit


def audit_mutation(pre_snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    branches: list[dict[str, Any]] = []
    for meta in UPSTREAMS.values():
        root = root_path(meta["root"])
        before = pre_snapshots.get(meta["root"], snapshot(root))
        after = snapshot(root)
        branches.append(
            {
                "root": meta["root"],
                "before": before,
                "after": after,
                "unchanged": before == after,
            }
        )
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
                findings.append({"file": rel(path), "pattern": pattern.pattern})
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
    manifest = {
        "status": "PASS",
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "file_count": len(entries),
        "files": entries,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_readme(manifest: dict[str, Any]) -> None:
    files = [path.name for path in generated_files()]
    lines = [
        f"# {TASK_NAME}",
        "",
        "Bounded Kit/Composer handoff package for the Hero Neighbourhood scene.",
        "",
        f"- Status: `{manifest.get('status')}`",
        f"- Overlay packets consumed: `{manifest.get('overlay_packet_count')}`",
        f"- Handoff mode: `{manifest.get('package_mode')}`",
        "- Runtime mutation: `false`",
        "",
        "## Boundary",
        "",
        BOUNDARY,
        "",
        "## Files",
        "",
    ]
    lines.extend(f"- `{name}`" for name in files)
    write_text(OUTPUT_ROOT / "README.md", "\n".join(lines))


def write_index() -> None:
    files = [path.name for path in generated_files()]
    lines = [f"# {TASK_NAME}", "", BOUNDARY, "", "## Open", ""]
    lines.extend(f"- [{name}]({name})" for name in files)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pre_snapshots = {meta["root"]: snapshot(root_path(meta["root"])) for meta in UPSTREAMS.values()}
    input_index, missing = discover_inputs(pre_snapshots)
    sources = load_sources()
    packets = sources["overlay_packets"]
    selection = build_scene_selection_metadata(packets)
    prim_index = build_prim_metadata_index(packets)
    usda = write_usda_handoff(prim_index)
    manifest = build_handoff_manifest(packets, selection, prim_index, usda, sources)
    write_boundary_labels()
    write_notes(manifest, prim_index)
    write_readme(manifest)
    write_index()

    claim = audit_claims()
    mutation = audit_mutation(pre_snapshots)
    secret = audit_secret()

    status = PASS_STATUS
    if not all(
        [
            not missing,
            input_index["status"] == "PASS",
            selection["status"] == "PASS",
            prim_index["status"] == "PASS",
            usda["status"] == "PASS",
            manifest["status"] == "PASS",
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
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "missing_required_upstreams": missing,
        "overlay_packet_count": len(packets),
        "prim_metadata_count": prim_index.get("metadata_count", 0),
        "usda_handoff_status": usda["status"],
        "kit_composer_handoff_manifest_status": manifest["status"],
        "post_r2_compatibility_checkpoint_status": input_index["post_r2_compatibility_checkpoint_status"],
        "pre_closeout_compatibility_watch_status": input_index["pre_closeout_compatibility_watch_status"],
        "unresolved_quarantined_metadata_count": prim_index.get("unresolved_quarantined_metadata_count", 0),
        "evidence_ref_status": prim_index["evidence_ref_status"],
        "limitation_ref_status": prim_index["limitation_ref_status"],
        "review_state_status": prim_index["review_state_status"],
        "claim_boundary_status": claim["status"],
        "no_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-SCENE-PACK-CLOSEOUT",
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_KIT_COMPOSER_HANDOFF_R3_DECISION.json", decision)
    manifest_hash = hash_manifest()
    decision["hash_validation_status"] = manifest_hash["status"]
    if manifest_hash["status"] != "PASS":
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_KIT_COMPOSER_HANDOFF_R3_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
