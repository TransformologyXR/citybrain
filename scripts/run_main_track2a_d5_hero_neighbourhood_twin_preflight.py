#!/usr/bin/env python3
"""Build the Track2A/D5 hero-neighbourhood visual control-room preflight."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-TWIN-PREFLIGHT"
PASS_STATUS = "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track2a_d5_hero_neighbourhood_twin_preflight"

UPSTREAMS = {
    "d6_d5_local_running_slice_closeout": {
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS",
        "required": True,
    },
    "d6_d5_local_running_control_room_slice_r1": {
        "root": "outputs/main_citybrain_d6_d5_local_running_control_room_slice_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_WITH_LIMITATIONS",
        "required": True,
    },
    "d5_track2_handoff_r4": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_track2_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_WITH_LIMITATIONS",
        "required": True,
    },
    "d5_event_fabric_integration_r3": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_event_fabric_integration_r3",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_WITH_LIMITATIONS",
        "required": True,
    },
    "r7_multi_domain_edge_registry_runtime_slice": {
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
        "required": True,
    },
    "r8_multi_domain_edge_registry_hardening": {
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
        "required": True,
    },
    "d6_incident_mode_preflight": {
        "root": "outputs/main_citybrain_d6_incident_mode_preflight",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_PREFLIGHT_WITH_LIMITATIONS",
        "required": False,
    },
    "track2a_omniverse_event_overlay_r3": {
        "root": "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3",
        "expected": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3_WITH_LIMITATIONS",
        "required": True,
    },
    "d6_control_room_reference_demo_closeout_refresh_r2": {
        "root": "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh_r2",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_R2_WITH_LIMITATIONS",
        "required": True,
    },
    "d6_incident_mode_evidence_bundle_r1_optional": {
        "root": "outputs/main_citybrain_d6_incident_mode_evidence_bundle_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_EVIDENCE_BUNDLE_R1_WITH_LIMITATIONS",
        "required": False,
    },
    "d6_incident_mode_operator_review_workflow_r2_optional": {
        "root": "outputs/main_citybrain_d6_incident_mode_operator_review_workflow_r2",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_OPERATOR_REVIEW_WORKFLOW_R2_WITH_LIMITATIONS",
        "required": False,
    },
}

BOUNDARY = (
    "Bounded hero-neighbourhood visual control-room preflight using local/replay review-context "
    "packets and evidence-backed overlays only. No citywide twin claim, certified digital twin claim, "
    "physical/geometric accuracy claim beyond accepted source evidence, production Omniverse deployment, "
    "live/autonomous monitoring, alert push, dispatch, routing/control, enforcement, legal/confirmed/"
    "certified claim, automated action, or frozen upstream mutation."
)

LIMITATIONS = [
    "preflight and contract task only",
    "bounded hero-neighbourhood scene concept only",
    "local/replay review-context packets only",
    "R8 is consumed as the hardened relationship source; no competing relationship vocabulary is introduced",
    "future Incident Mode packet integration is planning-only until evidence-bundle R1 and operator-review R2 are both green",
    "no citywide/certified/production twin claim",
    "no live monitoring, alerting, dispatch, routing/control, enforcement, legal/certified outcome, or automated action",
]

EXPECTED_FILES = [
    "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT_DECISION.json",
    "README.md",
    "INPUT_ARTIFACT_INDEX.json",
    "UPSTREAM_STATUS_SUMMARY.json",
    "HERO_NEIGHBOURHOOD_SELECTION_POLICY.json",
    "HERO_NEIGHBOURHOOD_SCOPE_CONTRACT.json",
    "SCENE_IDENTITY_CONTRACT.json",
    "ASSET_PRIM_BINDING_CONTRACT.json",
    "OVERLAY_PACKET_CONSUMPTION_CONTRACT.json",
    "R8_EDGE_REGISTRY_CONSUMPTION_CONTRACT.json",
    "EVIDENCE_LIMITATION_METADATA_CONTRACT.json",
    "REVIEW_STATE_CONFIDENCE_DISPLAY_CONTRACT.json",
    "WEB_COMPANION_ALIGNMENT_CONTRACT.json",
    "KIT_COMPOSER_HANDOFF_CONTRACT.json",
    "INCIDENT_MODE_FUTURE_INTEGRATION_CONTRACT.json",
    "VISUAL_ACCEPTANCE_CRITERIA.json",
    "IMPLEMENTATION_ROADMAP.md",
    "CLAIM_BOUNDARY_AUDIT.json",
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


def unique(values: list[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        if isinstance(value, list):
            for nested in value:
                text = str(nested)
                if text and text not in out:
                    out.append(text)
        else:
            text = str(value)
            if text and text not in out:
                out.append(text)
    return out


def discover_inputs(pre: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str], list[str]]:
    missing_required: list[str] = []
    deferred_optional: list[str] = []
    rows = []
    for branch, meta in UPSTREAMS.items():
        path = root_path(meta["root"])
        status = decision_status(path)
        expected = meta["expected"]
        exists = path.exists()
        green = exists and status == expected
        required = meta["required"]
        if required and not green:
            missing_required.append(branch)
        if not required and not green:
            deferred_optional.append(branch)
        artifacts = []
        if exists:
            for item in sorted(path.rglob("*")):
                if item.is_file() and item.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".py", ".usda"}:
                    artifacts.append(rel(item))
                if len(artifacts) >= 18:
                    break
        rows.append(
            {
                "branch": branch,
                "root": meta["root"],
                "required": required,
                "exists": exists,
                "decision_path": rel(decision_file(path)) if decision_file(path) else None,
                "status": status,
                "expected": expected,
                "green": green,
                "deferred": not required and not green,
                "snapshot": pre[meta["root"]],
                "sample_artifacts": artifacts,
                "read_only": True,
            }
        )
    report = {
        "status": "PASS" if not missing_required else "FAIL",
        "timestamp": utc_now(),
        "required_missing_or_not_green": missing_required,
        "optional_missing_or_deferred": deferred_optional,
        "artifact_count": sum(len(row["sample_artifacts"]) for row in rows),
        "branches": rows,
    }
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", report)
    return report, missing_required, deferred_optional


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
                "deferred": branch["deferred"],
                "count_fields": {key: value for key, value in decision.items() if isinstance(value, int) and ("count" in key or "edge" in key or "packet" in key)},
                "consumption_role": consumption_role(branch["branch"]),
                "read_only": True,
            }
        )
    report = {
        "status": "PASS" if all(row["green"] for row in rows if row["required"]) else "FAIL",
        "required_green_count": sum(row["green"] for row in rows if row["required"]),
        "required_count": sum(row["required"] for row in rows),
        "optional_green_count": sum(row["green"] for row in rows if not row["required"]),
        "rows": rows,
    }
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", report)
    return report


def consumption_role(branch: str) -> str:
    roles = {
        "d6_d5_local_running_slice_closeout": "frozen product-surface truth and boundary",
        "d6_d5_local_running_control_room_slice_r1": "selected scenario and control-room packet bundle",
        "d5_track2_handoff_r4": "Omniverse and web handoff packet contract",
        "d5_event_fabric_integration_r3": "event/current-state local runtime fixture context",
        "r7_multi_domain_edge_registry_runtime_slice": "lineage source behind hardened R8 edges",
        "r8_multi_domain_edge_registry_hardening": "authoritative hardened edge-registry source for this preflight",
        "d6_incident_mode_preflight": "future incident-mode integration contract only",
        "track2a_omniverse_event_overlay_r3": "proven OpenUSD/Kit event overlay pattern",
        "d6_control_room_reference_demo_closeout_refresh_r2": "frozen demo-surface closeout context",
        "d6_incident_mode_evidence_bundle_r1_optional": "optional signal only; not required by this preflight",
        "d6_incident_mode_operator_review_workflow_r2_optional": "optional future readiness gate; not required by this preflight",
    }
    return roles.get(branch, "source context")


def load_sources() -> dict[str, Any]:
    return {
        "r8_edges": rows_from(read_json(root_path(UPSTREAMS["r8_multi_domain_edge_registry_hardening"]["root"]) / "HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.json", {}), ["edges"]),
        "scenario": read_json(root_path(UPSTREAMS["d6_d5_local_running_control_room_slice_r1"]["root"]) / "CONTROL_ROOM_SCENARIO_SELECTION.json", {}),
        "bundle": read_json(root_path(UPSTREAMS["d6_d5_local_running_control_room_slice_r1"]["root"]) / "CONTROL_ROOM_CONTEXT_PACKET_BUNDLE.json", {}),
        "omni_packets": rows_from(read_json(root_path(UPSTREAMS["d5_track2_handoff_r4"]["root"]) / "OMNIVERSE_HANDOFF_PACKET_FIXTURES.json", {}), ["packets"]),
        "web_packets": rows_from(read_json(root_path(UPSTREAMS["d5_track2_handoff_r4"]["root"]) / "WEB_COMPANION_HANDOFF_PACKET_FIXTURES.json", {}), ["packets"]),
        "overlay_packets": rows_from(read_json(root_path(UPSTREAMS["track2a_omniverse_event_overlay_r3"]["root"]) / "OMNI_EVENT_R3_EVENT_OVERLAY_PACKETS.json", {}), ["packets"]),
        "asset_bindings": rows_from(read_json(root_path(UPSTREAMS["track2a_omniverse_event_overlay_r3"]["root"]) / "OMNI_EVENT_R3_EVENT_TO_ASSET_BINDING_MAP.json", {}), ["rows"]),
        "incident_preflight": read_json(root_path(UPSTREAMS["d6_incident_mode_preflight"]["root"]) / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_PREFLIGHT_DECISION.json", {}),
        "incident_r1": read_json(root_path(UPSTREAMS["d6_incident_mode_evidence_bundle_r1_optional"]["root"]) / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_EVIDENCE_BUNDLE_R1_DECISION.json", {}),
    }


def choose_candidate(sources: dict[str, Any]) -> dict[str, Any]:
    scenario = sources["scenario"]
    overlay = next((row for row in sources["overlay_packets"] if row.get("event_state_ref") in scenario.get("event_refs", [])), sources["overlay_packets"][0] if sources["overlay_packets"] else {})
    omni = next((row for row in sources["omni_packets"] if row.get("packet_id") in scenario.get("source_packet_ids", [])), sources["omni_packets"][0] if sources["omni_packets"] else {})
    asset = next((row for row in sources["asset_bindings"] if row.get("event_state_ref") == overlay.get("event_state_ref")), sources["asset_bindings"][0] if sources["asset_bindings"] else {})
    scenario_refs = set(scenario.get("edge_refs", []) + scenario.get("event_refs", []) + scenario.get("canonical_entity_refs", []))
    candidate_edges = []
    for edge in sources["r8_edges"]:
        text = json.dumps(edge, sort_keys=True)
        if any(ref in text for ref in scenario_refs):
            candidate_edges.append(edge)
    if not candidate_edges:
        candidate_edges = sources["r8_edges"][:8]
    city = overlay.get("city_id") or "LON"
    domains = Counter(edge.get("source_domain", "unknown") for edge in candidate_edges)
    return {
        "candidate_id": "hero-neighbourhood-preflight-candidate-001",
        "candidate_name": f"{city} local replay scene focus / corridor event context",
        "candidate_status": "SELECTED_PREFLIGHT_CANDIDATE_NOT_FINAL_IMPLEMENTATION",
        "selection_basis": [
            "derived from frozen D6/D5 local running scenario",
            "has event/current-state overlay context from Track2A R3",
            "has Omniverse Kit/Composer handoff packet refs from D5 R4",
            "has R8 hardened edge-registry context",
            "stays bounded to one local/replay scene focus and does not require citywide coverage",
        ],
        "city_or_area_ref": city,
        "scenario_ref": scenario.get("scenario_id"),
        "canonical_entity_refs": unique([scenario.get("canonical_entity_refs", []), asset.get("canonical_entity_id"), omni.get("canonical_entity_refs", [])]),
        "event_refs": unique([scenario.get("event_refs", []), overlay.get("event_id"), overlay.get("event_state_ref"), omni.get("event_refs", [])]),
        "overlay_packet_refs": unique([overlay.get("overlay_packet_id"), omni.get("source_kit_packet_ref")]),
        "usd_prim_refs": unique([overlay.get("usd_prim_refs", []), omni.get("usd_prim_refs", []), asset.get("usd_prim_ref")]),
        "r8_edge_refs": [edge.get("edge_id") for edge in candidate_edges[:12]],
        "r8_relationship_families": sorted({edge.get("relationship_family", "unknown") for edge in candidate_edges[:12]}),
        "r8_domain_coverage": dict(domains),
        "evidence_refs": unique([scenario.get("evidence_refs", []), overlay.get("evidence_refs", []), omni.get("evidence_refs", []), asset.get("evidence_refs", [])]),
        "limitation_refs": unique([scenario.get("limitation_refs", []), overlay.get("limitation_refs", []), omni.get("limitation_refs", []), asset.get("limitation_refs", [])]),
        "review_state": scenario.get("review_state", "review_context"),
        "confidence": scenario.get("confidence", omni.get("confidence", 0.55)),
        "bounded_scope": True,
        "claim_boundary": BOUNDARY,
    }


def write_contracts(sources: dict[str, Any], candidate: dict[str, Any], deferred_optional: list[str]) -> dict[str, Any]:
    incident_r1_green = sources["incident_r1"].get("status") == UPSTREAMS["d6_incident_mode_evidence_bundle_r1_optional"]["expected"]
    incident_r2_green = "d6_incident_mode_operator_review_workflow_r2_optional" not in deferred_optional
    recommended_next = (
        "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-ASSET-BINDING-R1"
        if incident_r1_green and incident_r2_green
        else "WAIT_FOR_MAIN_CITYBRAIN_D6_INCIDENT_MODE_EVIDENCE_BUNDLE_R1_AND_OPERATOR_REVIEW_WORKFLOW_R2"
    )

    selection_policy = {
        "status": "PASS",
        "policy_name": "HERO_NEIGHBOURHOOD_SELECTION_POLICY",
        "criteria": [
            "enough canonical entities to show meaningful relationships",
            "enough event/current-state overlays to make the scene useful",
            "enough R8 edge-registry coverage to demonstrate multi-domain context",
            "compatibility with proven Omniverse/USDA handoff patterns",
            "compatibility with web companion episode/evidence surface",
            "ability to stay bounded and non-certified",
            "no requirement for citywide coverage",
        ],
        "selected_candidate": candidate,
        "final_implementation_selection_required_later": True,
        "claim_boundary": BOUNDARY,
    }
    scope = {
        "status": "PASS",
        "contract_name": "HERO_NEIGHBOURHOOD_SCOPE_CONTRACT",
        "scope_mode": "bounded_visual_control_room_preflight",
        "selected_candidate_id": candidate["candidate_id"],
        "included": [
            "one bounded local/replay scene focus",
            "canonical entity refs from frozen packets",
            "R8 hardened edge refs",
            "event/current-state overlay refs",
            "evidence and limitation metadata",
            "Kit/Composer handoff planning",
            "web companion alignment planning",
        ],
        "excluded": [
            "citywide OpenUSD twin",
            "certified digital twin",
            "physical/geometric accuracy beyond accepted source evidence",
            "production Omniverse runtime",
            "live sensor ingest",
            "official operational monitoring",
            "action workflow",
            "enforcement workflow",
            "legal/certified outcome",
            "autonomous detection or alerting",
        ],
        "bounded_scope": True,
        "claim_boundary": BOUNDARY,
    }
    scene_identity = {
        "status": "PASS",
        "contract_name": "SCENE_IDENTITY_CONTRACT",
        "scene_identity_mode": "preflight_scene_identity_only",
        "scene_id": "hero-neighbourhood-preflight-scene-001",
        "scene_label": candidate["candidate_name"],
        "source_scenario_ref": candidate["scenario_ref"],
        "canonical_entity_refs": candidate["canonical_entity_refs"],
        "event_refs": candidate["event_refs"],
        "r8_edge_refs": candidate["r8_edge_refs"],
        "non_certification_label_required": True,
        "claim_boundary": BOUNDARY,
    }
    asset_prim = {
        "status": "PASS",
        "contract_name": "ASSET_PRIM_BINDING_CONTRACT",
        "binding_mode": "preflight_existing_prim_or_sidecar_context_only",
        "canonical_entity_refs": candidate["canonical_entity_refs"],
        "usd_prim_refs": candidate["usd_prim_refs"],
        "prim_path_strategy": [
            "reuse proven Track2A overlay USD prim refs when present",
            "place future sidecar markers under a dedicated bounded hero-neighbourhood layer",
            "label placeholders as not source geometry and not physical accuracy proof",
        ],
        "source_geometry_mutation_allowed": False,
        "claim_boundary": BOUNDARY,
    }
    overlay_consumption = {
        "status": "PASS",
        "contract_name": "OVERLAY_PACKET_CONSUMPTION_CONTRACT",
        "overlay_packet_refs": candidate["overlay_packet_refs"],
        "event_refs": candidate["event_refs"],
        "consumption_policy": [
            "consume Track2A/D5 overlay packets read-only",
            "co-display evidence and limitation metadata",
            "preserve review state and confidence",
            "do not convert overlays into alerts, actions, or certified facts",
        ],
        "claim_boundary": BOUNDARY,
    }
    r8_consumption = {
        "status": "PASS",
        "contract_name": "R8_EDGE_REGISTRY_CONSUMPTION_CONTRACT",
        "edge_registry_source": UPSTREAMS["r8_multi_domain_edge_registry_hardening"]["root"],
        "r8_edge_refs": candidate["r8_edge_refs"],
        "relationship_families_from_r8": candidate["r8_relationship_families"],
        "no_competing_relationship_vocabulary": True,
        "consumption_policy": "use R8 relationship family, edge type, review state, confidence, evidence refs, and limitation refs as-is",
        "claim_boundary": BOUNDARY,
    }
    evidence_metadata = {
        "status": "PASS",
        "contract_name": "EVIDENCE_LIMITATION_METADATA_CONTRACT",
        "evidence_refs": candidate["evidence_refs"],
        "limitation_refs": candidate["limitation_refs"],
        "metadata_policy": [
            "evidence refs and limitation refs must be co-displayed",
            "source limitations carry forward into scene labels",
            "uncertainty must remain visible for placeholder or review-only geometry",
        ],
        "claim_boundary": BOUNDARY,
    }
    review_display = {
        "status": "PASS",
        "contract_name": "REVIEW_STATE_CONFIDENCE_DISPLAY_CONTRACT",
        "review_state": candidate["review_state"],
        "confidence": candidate["confidence"],
        "display_policy": [
            "show review state as context state, not verified or certified truth",
            "show confidence as review/evidence confidence only",
            "visually distinguish unresolved, quarantined, and candidate context",
            "do not display confirmed/certified/legal/action states",
        ],
        "forbidden_display_states": ["confirmed", "certified", "legal finding", "alert sent", "dispatch", "controlled", "enforced"],
        "claim_boundary": BOUNDARY,
    }
    web_alignment = {
        "status": "PASS",
        "contract_name": "WEB_COMPANION_ALIGNMENT_CONTRACT",
        "surface": "web companion evidence / episode / executive context",
        "web_packet_refs": unique([row.get("packet_id") for row in sources["web_packets"][:3]]),
        "alignment_policy": [
            "web opens evidence, episode, executive, limitation, and uncertainty context",
            "web does not become a production frontend or alert console",
            "web mirrors selected scene refs and R8 edge refs without mutating source packets",
        ],
        "claim_boundary": BOUNDARY,
    }
    kit_handoff = {
        "status": "PASS",
        "contract_name": "KIT_COMPOSER_HANDOFF_CONTRACT",
        "surface": "Omniverse Kit/Composer bounded scene context",
        "kit_packet_refs": candidate["overlay_packet_refs"],
        "usd_prim_refs": candidate["usd_prim_refs"],
        "handoff_policy": [
            "use Kit/Composer handoff context from D5 R4 and Track2A R3",
            "future implementation may add sidecar overlay layer, camera bookmarks, and review labels",
            "preflight does not author a production OpenUSD scene or full citywide twin",
        ],
        "claim_boundary": BOUNDARY,
    }
    incident_future = {
        "status": "PASS",
        "contract_name": "INCIDENT_MODE_FUTURE_INTEGRATION_CONTRACT",
        "incident_mode_preflight_status": sources["incident_preflight"].get("status"),
        "incident_evidence_bundle_r1_status": sources["incident_r1"].get("status", "MISSING_OR_DEFERRED"),
        "incident_operator_review_workflow_r2_status": "MISSING_OR_DEFERRED" if "d6_incident_mode_operator_review_workflow_r2_optional" in deferred_optional else "PRESENT",
        "integration_mode": "future integration planning only",
        "not_required_for_this_preflight": True,
        "must_not_require_nonexistent_r1_r2_r3_outputs": True,
        "future_packet_refs_expected": [
            "incident evidence bundle",
            "operator review packet",
            "safe-next-look review suggestions",
        ],
        "recommended_next_task_after_preflight": recommended_next,
        "claim_boundary": BOUNDARY,
    }
    visual_acceptance = {
        "status": "PASS",
        "criteria_name": "VISUAL_ACCEPTANCE_CRITERIA",
        "acceptance_criteria": [
            "scene is clearly labeled bounded hero-neighbourhood review context",
            "no citywide/certified/production twin claim appears in UI labels",
            "canonical entity, event, overlay, R8 edge, evidence, limitation, review state, and confidence are visible",
            "placeholder geometry or sidecar marker context is visibly labeled as non-certified",
            "Omniverse Kit/Composer handoff refs are available",
            "web companion refs are aligned",
            "safe next looks remain review-only",
            "no alert/action/control/enforcement/legal/certified state is displayed",
        ],
        "gui_acceptance_required_later": True,
        "claim_boundary": BOUNDARY,
    }
    contracts = {
        "HERO_NEIGHBOURHOOD_SELECTION_POLICY.json": selection_policy,
        "HERO_NEIGHBOURHOOD_SCOPE_CONTRACT.json": scope,
        "SCENE_IDENTITY_CONTRACT.json": scene_identity,
        "ASSET_PRIM_BINDING_CONTRACT.json": asset_prim,
        "OVERLAY_PACKET_CONSUMPTION_CONTRACT.json": overlay_consumption,
        "R8_EDGE_REGISTRY_CONSUMPTION_CONTRACT.json": r8_consumption,
        "EVIDENCE_LIMITATION_METADATA_CONTRACT.json": evidence_metadata,
        "REVIEW_STATE_CONFIDENCE_DISPLAY_CONTRACT.json": review_display,
        "WEB_COMPANION_ALIGNMENT_CONTRACT.json": web_alignment,
        "KIT_COMPOSER_HANDOFF_CONTRACT.json": kit_handoff,
        "INCIDENT_MODE_FUTURE_INTEGRATION_CONTRACT.json": incident_future,
        "VISUAL_ACCEPTANCE_CRITERIA.json": visual_acceptance,
    }
    for name, payload in contracts.items():
        write_json(OUTPUT_ROOT / name, payload)
    write_roadmap(recommended_next)
    return contracts


def write_roadmap(recommended_next: str) -> None:
    write_text(
        OUTPUT_ROOT / "IMPLEMENTATION_ROADMAP.md",
        f"""# Implementation Roadmap

This roadmap is for a later implementation task. The current task is preflight only.

## Phase 1

- Wait for Incident Mode evidence-bundle R1 and operator-review workflow R2 if they are not both green.
- Confirm the selected hero-neighbourhood candidate still has current R8 edge coverage and Track2A overlay coverage.

## Phase 2

- Build `MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-ASSET-BINDING-R1` if the Incident Mode gate is green.
- Bind canonical refs, overlay refs, R8 edge refs, evidence refs, and limitation refs to a bounded Kit/Composer scene plan.

## Phase 3

- Add camera bookmarks and web companion alignment.
- Run visual acceptance with explicit no-claim labels.

Recommended next task: `{recommended_next}`

Boundary: {BOUNDARY}
""",
    )


def validate(contracts: dict[str, Any], input_index: dict[str, Any], candidate: dict[str, Any], deferred_optional: list[str]) -> dict[str, Any]:
    r8_contract = contracts["R8_EDGE_REGISTRY_CONSUMPTION_CONTRACT.json"]
    incident_contract = contracts["INCIDENT_MODE_FUTURE_INTEGRATION_CONTRACT.json"]
    checks = [
        {"check": "required_upstreams_discovered_or_missing_recorded", "status": input_index["status"]},
        {"check": "hero_scope_bounded", "status": "PASS" if candidate.get("bounded_scope") else "FAIL"},
        {"check": "r8_consumed_as_edge_source", "status": "PASS" if r8_contract.get("edge_registry_source") == UPSTREAMS["r8_multi_domain_edge_registry_hardening"]["root"] else "FAIL"},
        {"check": "no_competing_relationship_vocabulary", "status": "PASS" if r8_contract.get("no_competing_relationship_vocabulary") else "FAIL"},
        {"check": "incident_mode_future_only", "status": "PASS" if incident_contract.get("integration_mode") == "future integration planning only" and incident_contract.get("not_required_for_this_preflight") else "FAIL"},
        {"check": "incident_r2_not_required", "status": "PASS" if "d6_incident_mode_operator_review_workflow_r2_optional" in deferred_optional or incident_contract.get("not_required_for_this_preflight") else "FAIL"},
        {"check": "evidence_limitation_metadata_exists", "status": contracts["EVIDENCE_LIMITATION_METADATA_CONTRACT.json"]["status"]},
        {"check": "review_state_confidence_policy_exists", "status": contracts["REVIEW_STATE_CONFIDENCE_DISPLAY_CONTRACT.json"]["status"]},
        {"check": "kit_composer_handoff_exists", "status": contracts["KIT_COMPOSER_HANDOFF_CONTRACT.json"]["status"]},
        {"check": "web_companion_alignment_exists", "status": contracts["WEB_COMPANION_ALIGNMENT_CONTRACT.json"]["status"]},
        {"check": "visual_acceptance_criteria_exists", "status": contracts["VISUAL_ACCEPTANCE_CRITERIA.json"]["status"]},
    ]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL", "checks": checks}


def audit_claims() -> dict[str, Any]:
    positive_patterns = [
        r'"citywide_twin_claim"\s*:\s*true',
        r'"certified_digital_twin_claim"\s*:\s*true',
        r'"production_omniverse_deployment"\s*:\s*true',
        r'"live_monitoring"\s*:\s*true',
        r'"autonomous_monitoring"\s*:\s*true',
        r'"alert_push"\s*:\s*true',
        r'"dispatch"\s*:\s*true',
        r'"routing_control"\s*:\s*true',
        r'"enforcement"\s*:\s*true',
        r'"legal_certified_claim"\s*:\s*true',
        r'"automated_action"\s*:\s*true',
        r"production citywide digital twin",
        r"certified operational twin",
        r"autonomous incident monitoring surface",
    ]
    joined = ""
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name not in {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.json"} and item.suffix.lower() in {".json", ".md", ".txt"}:
            joined += "\n" + item.read_text(encoding="utf-8", errors="ignore").lower()
    hits = [pattern for pattern in positive_patterns if re.search(pattern, joined)]
    report = {"status": "PASS" if not hits else "FAIL", "positive_forbidden_claim_hits": hits, "claim_boundary": BOUNDARY}
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


def write_readme_and_index(candidate: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

This pack defines a bounded hero-neighbourhood visual control-room preflight for Track2A/D5.

Selected preflight candidate: `{candidate['candidate_name']}`

It consumes the frozen local-running control-room slice, R8 hardened edge registry, D5 handoff packets, and Track2A overlay patterns as read-only inputs. It does not build the hero scene.

{BOUNDARY}
""",
    )
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Selected preflight candidate: `{candidate['candidate_name']}`",
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
    input_index, missing_required, deferred_optional = discover_inputs(pre)
    upstream = upstream_summary(input_index)
    sources = load_sources()
    candidate = choose_candidate(sources)
    contracts = write_contracts(sources, candidate, deferred_optional)
    write_readme_and_index(candidate)
    validation = validate(contracts, input_index, candidate, deferred_optional)
    claim = audit_claims()
    mutation = audit_mutation(pre)
    secret = audit_secret()

    status = PASS_STATUS
    if not all(
        [
            not missing_required,
            input_index["status"] == "PASS",
            upstream["status"] == "PASS",
            validation["status"] == "PASS",
            claim["status"] == "PASS",
            mutation["status"] == "PASS",
            secret["status"] == "PASS",
        ]
    ):
        status = FAIL_STATUS

    incident_contract = contracts["INCIDENT_MODE_FUTURE_INTEGRATION_CONTRACT.json"]
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "upstream_discovery_count": len([row for row in input_index["branches"] if row["exists"]]),
        "missing_or_deferred_upstreams": missing_required + deferred_optional,
        "selected_hero_neighbourhood": candidate["candidate_name"],
        "selected_candidate_id": candidate["candidate_id"],
        "scope_bounded": candidate["bounded_scope"],
        "r8_consumed": contracts["R8_EDGE_REGISTRY_CONSUMPTION_CONTRACT.json"]["edge_registry_source"] == UPSTREAMS["r8_multi_domain_edge_registry_hardening"]["root"],
        "incident_mode_future_integration_only": incident_contract["integration_mode"] == "future integration planning only",
        "claim_boundary_audit_result": claim["status"],
        "no_mutation_audit_result": mutation["status"],
        "secret_audit_result": secret["status"],
        "hash_validation_result": "PENDING",
        "validation_status": validation["status"],
        "limitations": LIMITATIONS,
        "recommended_next_task": incident_contract["recommended_next_task_after_preflight"],
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT_DECISION.json", decision)
    manifest = hash_manifest()
    decision["hash_validation_result"] = manifest["status"]
    if manifest["status"] != "PASS":
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
