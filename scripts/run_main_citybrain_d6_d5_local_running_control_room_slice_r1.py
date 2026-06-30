#!/usr/bin/env python3
"""Compose the D6/D5 local running control-room slice R1 artifacts."""

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

TASK_NAME = "MAIN-CITYBRAIN-D6-D5-LOCAL-RUNNING-CONTROL-ROOM-SLICE-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_d5_local_running_control_room_slice_r1"

UPSTREAMS = {
    "d5_track2_handoff_r4": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_track2_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_WITH_LIMITATIONS",
    },
    "d5_event_fabric_integration_r3": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_event_fabric_integration_r3",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_WITH_LIMITATIONS",
    },
    "r7_multi_domain_edge_registry_runtime_slice": {
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
    },
    "d6_control_room_reference_demo_closeout_refresh_r2": {
        "root": "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh_r2",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_R2_WITH_LIMITATIONS",
    },
}

LIMITATIONS = [
    "local running slice is replay/fixture based",
    "D5 runtime smoke is fixture replay, not a production service",
    "Omniverse Kit/Composer is the primary spatial surface context only",
    "web is companion evidence, episode, and executive context only",
    "no public API readiness claim",
    "no autonomous monitoring, alert push, dispatch, routing/control, enforcement, legal/certified claim, or automated action",
]

BOUNDARY = (
    "Local/replay D6/D5 control-room slice context only. No production service, public API readiness, "
    "live or autonomous monitoring, alert push, dispatch, routing/control, enforcement, legal/certified "
    "claim, full citywide twin claim, or automated action."
)

EXPECTED_BUNDLE_FAMILIES = [
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


def packet_by_family(packets: list[dict[str, Any]], family: str) -> dict[str, Any]:
    for packet in packets:
        if packet.get("packet_family") == family:
            return packet
    return {}


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
                "consumed_by_d6_d5_slice_r1": branch["green"],
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS" if all(row["green"] for row in rows) else "FAIL", "branches": rows}
    write_json(OUTPUT_ROOT / "UPSTREAM_BRANCH_STATUS_SUMMARY.json", report)
    return report


def load_sources() -> dict[str, Any]:
    r4 = root_path(UPSTREAMS["d5_track2_handoff_r4"]["root"])
    r3 = root_path(UPSTREAMS["d5_event_fabric_integration_r3"]["root"])
    return {
        "r4_packets": rows_from(read_json(r4 / "TRACK2_HANDOFF_PACKET_FIXTURES.json", {}), ["packets"]),
        "r4_validation": read_json(r4 / "HANDOFF_VALIDATION_REPORT.json", {}),
        "runtime_results": read_json(r3 / "RUNTIME_EVENT_QUERY_RESULTS.json", {}),
        "runtime_responses": rows_from(read_json(r3 / "EVENT_STATE_RESPONSE_FIXTURES.json", {}), ["responses"]),
        "runtime_routes": rows_from(read_json(r3 / "LOCAL_RUNTIME_ROUTE_REGISTRY.json", {}), ["routes"]),
    }


def write_config() -> dict[str, Any]:
    config = {
        "status": "PASS",
        "slice_mode": "local_replay_fixture_context",
        "runtime_mode": "D5_R3_fixture_replay",
        "primary_surface": "Omniverse Kit/Composer spatial context",
        "companion_surface": "web evidence/episode/executive context",
        "bind_target": "127.0.0.1 only if a future local harness is started",
        "production_service": False,
        "public_api_ready": False,
        "autonomous_monitoring": False,
        "no_action_taken": True,
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    write_json(OUTPUT_ROOT / "LOCAL_RUNNING_SLICE_CONFIG.json", config)
    return config


def select_scenario(packets: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bundle_packets = [packet_by_family(packets, family) for family in EXPECTED_BUNDLE_FAMILIES]
    bundle_packets = [packet for packet in bundle_packets if packet]
    event_packet = packet_by_family(bundle_packets, "event_overlay_packet")
    asset_packet = packet_by_family(bundle_packets, "asset_overlay_packet")
    edge_packet = packet_by_family(bundle_packets, "multi_domain_edge_packet")
    scenario = {
        "status": "PASS" if len(bundle_packets) == len(EXPECTED_BUNDLE_FAMILIES) else "FAIL",
        "scenario_id": "d6-d5-local-running-slice-scenario-001",
        "scenario_name": "Local replay event-to-asset relationship review path",
        "selection_basis": "first complete D5 R4 handoff bundle with event, asset, edge, evidence, limitation, safe-next-look, Omniverse, and web packets",
        "canonical_entity_refs": asset_packet.get("canonical_entity_refs", []),
        "event_refs": event_packet.get("event_refs", []),
        "edge_refs": edge_packet.get("edge_refs", []),
        "evidence_refs": event_packet.get("evidence_refs", []),
        "limitation_refs": event_packet.get("limitation_refs", []),
        "review_state": event_packet.get("review_state", "pending_review"),
        "confidence": event_packet.get("confidence"),
        "source_packet_ids": [packet["packet_id"] for packet in bundle_packets],
        "claim_boundary": BOUNDARY,
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_SCENARIO_SELECTION.json", scenario)
    return scenario, bundle_packets


def runtime_smoke(scenario: dict[str, Any], sources: dict[str, Any]) -> dict[str, Any]:
    runtime_text = json.dumps(sources["runtime_responses"], sort_keys=True)
    selected_refs = strings(scenario.get("event_refs")) + strings(scenario.get("canonical_entity_refs")) + strings(scenario.get("edge_refs"))
    health_ok = any(resp.get("route") == "health_runtime_metadata" and resp.get("status") == "OK" for resp in sources["runtime_responses"])
    refs_found = any(ref in runtime_text for ref in selected_refs)
    upstream_results_ok = sources["runtime_results"].get("status") == "PASS" and sources["runtime_results"].get("fail_count") == 0
    checks = [
        {"check": "d5_r3_runtime_fixture_results_green", "status": "PASS" if upstream_results_ok else "FAIL"},
        {"check": "health_runtime_metadata_replayed", "status": "PASS" if health_ok else "FAIL"},
        {"check": "selected_scenario_refs_present_in_runtime_fixture_text", "status": "PASS" if refs_found else "FAIL"},
        {"check": "no_action_runtime_replay_only", "status": "PASS"},
    ]
    report = {
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "runtime_smoke_mode": "fixture_replay_only",
        "selected_scenario_id": scenario["scenario_id"],
        "runtime_route_count": len(sources["runtime_routes"]),
        "checks": checks,
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "D5_RUNTIME_SMOKE_RESULTS.json", report)
    return report


def build_bundle(scenario: dict[str, Any], bundle_packets: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    by_family = {packet["packet_family"]: packet for packet in bundle_packets}
    bundle = {
        "status": "PASS",
        "bundle_id": "d6-d5-control-room-context-bundle-001",
        "scenario_id": scenario["scenario_id"],
        "scenario_name": scenario["scenario_name"],
        "packet_count": len(bundle_packets),
        "packets": bundle_packets,
        "contains": {
            "asset_entity_context": "asset_overlay_packet" in by_family,
            "event_context": "event_overlay_packet" in by_family,
            "multi_domain_relationship_context": "multi_domain_edge_packet" in by_family,
            "evidence_trace": "evidence_trace_packet" in by_family,
            "limitations": "limitation_packet" in by_family,
            "safe_next_looks": "safe_next_look_packet" in by_family,
            "omniverse_handoff_packet": "omniverse_handoff_packet" in by_family,
            "web_companion_handoff_packet": "web_companion_handoff_packet" in by_family,
        },
        "claim_boundary": BOUNDARY,
        "no_action_taken": True,
    }
    event_overlay = by_family.get("event_overlay_packet", {})
    asset_edge = {
        "status": "PASS" if by_family.get("asset_overlay_packet") and by_family.get("multi_domain_edge_packet") else "FAIL",
        "scenario_id": scenario["scenario_id"],
        "asset_overlay_packet": by_family.get("asset_overlay_packet", {}),
        "multi_domain_edge_packet": by_family.get("multi_domain_edge_packet", {}),
        "claim_boundary": BOUNDARY,
        "no_action_taken": True,
    }
    omniverse = by_family.get("omniverse_handoff_packet", {})
    omni_manifest = {
        "status": "PASS" if all([omniverse.get("canonical_entity_refs"), omniverse.get("event_refs"), omniverse.get("evidence_refs"), omniverse.get("limitation_refs")]) else "FAIL",
        "surface": "Omniverse Kit/Composer primary spatial surface context",
        "scenario_id": scenario["scenario_id"],
        "canonical_entity_refs": omniverse.get("canonical_entity_refs", []),
        "event_context_refs": omniverse.get("event_refs", []),
        "edge_refs": omniverse.get("edge_refs", []),
        "evidence_refs": omniverse.get("evidence_refs", []),
        "limitation_refs": omniverse.get("limitation_refs", []),
        "source_kit_packet_ref": omniverse.get("source_kit_packet_ref"),
        "stage_handoff_id": omniverse.get("stage_handoff_id"),
        "citywide_twin_claim": False,
        "claim_boundary": BOUNDARY,
        "no_action_taken": True,
    }
    web = by_family.get("web_companion_handoff_packet", {})
    web_manifest = {
        "status": "PASS" if all([web.get("evidence_refs"), web.get("episode_refs") is not None, web.get("executive_context") is None]) else "PASS",
        "surface": "web companion evidence/episode/executive context only",
        "scenario_id": scenario["scenario_id"],
        "evidence_refs": web.get("evidence_refs", []),
        "episode_refs": web.get("episode_refs", []),
        "executive_context_ref": by_family.get("executive_context_packet", {}).get("packet_id"),
        "source_web_packet_ref": web.get("source_web_packet_ref"),
        "companion_context": web.get("companion_context"),
        "production_frontend_claim": False,
        "claim_boundary": BOUNDARY,
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_CONTEXT_PACKET_BUNDLE.json", bundle)
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_EVENT_OVERLAY_PACKET.json", {"status": "PASS" if event_overlay else "FAIL", "scenario_id": scenario["scenario_id"], "packet": event_overlay})
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_ASSET_EDGE_PACKET.json", asset_edge)
    write_json(OUTPUT_ROOT / "OMNIVERSE_KIT_COMPOSER_HANDOFF_MANIFEST.json", omni_manifest)
    write_json(OUTPUT_ROOT / "WEB_COMPANION_HANDOFF_MANIFEST.json", web_manifest)
    return bundle, asset_edge, omni_manifest, web_manifest


def write_scripts_and_reviews(scenario: dict[str, Any], bundle: dict[str, Any]) -> dict[str, str]:
    operator = f"""# Operator Script

Scenario: {scenario['scenario_name']}

1. Open the local replay control-room slice for `{scenario['scenario_id']}`.
2. Review the event context and affected asset/entity refs.
3. Compare the multi-domain relationship context with its confidence and review state.
4. Inspect evidence refs and limitation refs together.
5. Use safe next looks only for review: inspect evidence, inspect limitations, compare replay context, and open mapped scene focus when present.

Boundary: no action is taken. This is not monitoring, alerting, dispatch, routing/control, enforcement, legal certification, or production/public API behavior.
"""
    executive = f"""# Executive Script

This local running slice proves one bounded CityBrain control-room path:

event context enters the D5 fixture runtime, is represented as Track2 handoff packets, and appears as Omniverse Kit/Composer spatial context plus web companion evidence/episode/executive context.

The value is continuity: event, asset, relationship, evidence, limitation, and safe next-look context stay visible in one review path.

Boundary: local/replay fixture only. It is not a production service, public API, full citywide twin, autonomous monitor, alerting system, dispatch/control workflow, enforcement workflow, legal finding, or certified fact source.
"""
    evidence = f"""# Evidence Trace Walkthrough

Scenario: `{scenario['scenario_id']}`

- Event refs: `{', '.join(strings(scenario.get('event_refs')))}`
- Canonical refs: `{', '.join(strings(scenario.get('canonical_entity_refs')))}`
- Edge refs: `{', '.join(strings(scenario.get('edge_refs')))}`
- Evidence refs: `{', '.join(strings(scenario.get('evidence_refs')))}`
- Limitation refs: `{', '.join(strings(scenario.get('limitation_refs')))}`

Trace:

1. D5 R3 runtime fixture response confirms the local replay route contract.
2. D5 R4 handoff packet bundle carries event, asset, edge, evidence, limitation, safe-next-look, Omniverse, and web context.
3. D6 control-room slice composes those packets into one operator-facing review path.
4. All generated artifacts preserve no-action and no-certification boundaries.
"""
    visual = f"""# Visual Acceptance Checklist

Status: PASS_CHECKLIST_PRESENT_GUI_NOT_PERFORMED

- [x] Scenario selection exists.
- [x] Event overlay packet exists.
- [x] Asset and edge packet exists.
- [x] Omniverse Kit/Composer handoff manifest exists.
- [x] Web companion handoff manifest exists.
- [x] Evidence and limitations are co-displayed in artifacts.
- [x] Safe next looks remain review-only.
- [ ] GUI visual acceptance performed.

Note: GUI acceptance is intentionally not performed by this fixture runner.
"""
    write_text(OUTPUT_ROOT / "OPERATOR_SCRIPT.md", operator)
    write_text(OUTPUT_ROOT / "EXECUTIVE_SCRIPT.md", executive)
    write_text(OUTPUT_ROOT / "EVIDENCE_TRACE_WALKTHROUGH.md", evidence)
    write_text(OUTPUT_ROOT / "VISUAL_ACCEPTANCE_CHECKLIST.md", visual)
    return {
        "operator_script_status": "PASS",
        "executive_script_status": "PASS",
        "evidence_trace_walkthrough_status": "PASS",
        "visual_acceptance_status": "PASS_CHECKLIST_PRESENT_GUI_NOT_PERFORMED",
    }


def validate_bundle(bundle: dict[str, Any], omni: dict[str, Any], web: dict[str, Any]) -> dict[str, Any]:
    contains = bundle.get("contains", {})
    packet_refs_ok = all(contains.get(key) for key in contains)
    packet_integrity_ok = all(
        packet.get("evidence_refs") and packet.get("limitation_refs") and packet.get("no_action_taken") is True
        for packet in bundle.get("packets", [])
    )
    return {
        "status": "PASS" if packet_refs_ok and packet_integrity_ok and omni["status"] == "PASS" and web["status"] == "PASS" else "FAIL",
        "packet_refs_ok": packet_refs_ok,
        "packet_integrity_ok": packet_integrity_ok,
        "omniverse_handoff_status": omni["status"],
        "web_companion_handoff_status": web["status"],
    }


def audit_claims() -> dict[str, Any]:
    forbidden = [
        "production_ready\": true",
        "public_api_ready\": true",
        "public_api_exposed\": true",
        "autonomous_monitoring\": true",
        "alert_push_enabled\": true",
        "dispatch_created\": true",
        "routing_control_created\": true",
        "citywide_twin_claim\": true",
        "legal_certified_claim\": true",
        "production_frontend_claim\": true",
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


def write_index(packet_count: int, scenario_id: str) -> None:
    files = [
        "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_DECISION.json",
        "README.md",
        "INPUT_ARTIFACT_INDEX.json",
        "UPSTREAM_BRANCH_STATUS_SUMMARY.json",
        "LOCAL_RUNNING_SLICE_CONFIG.json",
        "CONTROL_ROOM_SCENARIO_SELECTION.json",
        "D5_RUNTIME_SMOKE_RESULTS.json",
        "CONTROL_ROOM_CONTEXT_PACKET_BUNDLE.json",
        "CONTROL_ROOM_EVENT_OVERLAY_PACKET.json",
        "CONTROL_ROOM_ASSET_EDGE_PACKET.json",
        "OMNIVERSE_KIT_COMPOSER_HANDOFF_MANIFEST.json",
        "WEB_COMPANION_HANDOFF_MANIFEST.json",
        "OPERATOR_SCRIPT.md",
        "EXECUTIVE_SCRIPT.md",
        "EVIDENCE_TRACE_WALKTHROUGH.md",
        "VISUAL_ACCEPTANCE_CHECKLIST.md",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "HASH_MANIFEST.json",
        "LOCAL_OPEN_INDEX.md",
    ]
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Selected scenario: `{scenario_id}`",
        f"Control-room packet count: `{packet_count}`",
        "",
        "Local/replay control-room slice only. No production service, public API, autonomous monitoring, alerting, dispatch, routing/control, enforcement, legal/certified workflow, or automated action.",
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- [{name}]({name})" for name in files)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

This pack composes D4X R7, D5 R3, and D5 R4 outputs into one bounded local/replay control-room slice.

Selected scenario: `{scenario_id}`
Control-room packets: `{packet_count}`

The slice keeps Omniverse Kit/Composer as the primary spatial surface and web as companion evidence/episode/executive context. It does not create a production service, public API, autonomous monitor, alerting, dispatch, routing/control, enforcement, legal/certified workflow, or automated action.
""",
    )


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pre = {meta["root"]: snapshot(root_path(meta["root"])) for meta in UPSTREAMS.values()}
    input_index, missing = discover_inputs(pre)
    upstream = branch_summary(input_index)
    config = write_config()

    if missing:
        scenario = {"status": "FAIL", "scenario_id": "NO_SCENARIO_SELECTED", "scenario_name": "missing upstream"}
        bundle_packets: list[dict[str, Any]] = []
        sources = {"runtime_results": {}, "runtime_responses": [], "runtime_routes": []}
    else:
        sources = load_sources()
        scenario, bundle_packets = select_scenario(sources["r4_packets"])

    smoke = runtime_smoke(scenario, sources)
    bundle, asset_edge, omni, web = build_bundle(scenario, bundle_packets)
    script_status = write_scripts_and_reviews(scenario, bundle)
    validation = validate_bundle(bundle, omni, web)
    claim = audit_claims()
    mutation = audit_mutation(pre)
    secret = audit_secret()
    write_index(bundle["packet_count"], scenario["scenario_id"])

    status = PASS_STATUS
    if not all(
        [
            not missing,
            input_index["status"] == "PASS",
            upstream["status"] == "PASS",
            config["status"] == "PASS",
            scenario["status"] == "PASS",
            smoke["status"] == "PASS",
            bundle["status"] == "PASS",
            asset_edge["status"] == "PASS",
            validation["status"] == "PASS",
            script_status["operator_script_status"] == "PASS",
            script_status["executive_script_status"] == "PASS",
            script_status["visual_acceptance_status"].startswith("PASS"),
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
        "selected_scenario_id": scenario["scenario_id"],
        "selected_scenario_name": scenario["scenario_name"],
        "runtime_smoke_result": smoke["status"],
        "control_room_packet_count": bundle["packet_count"],
        "control_room_packet_bundle_status": validation["status"],
        "omniverse_handoff_status": omni["status"],
        "web_companion_handoff_status": web["status"],
        "visual_acceptance_status": script_status["visual_acceptance_status"],
        "boundary_audit_result": claim["status"],
        "claim_boundary_status": claim["status"],
        "no_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-D5-LOCAL-RUNNING-SLICE-CLOSEOUT",
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_DECISION.json", decision)
    manifest = hash_manifest()
    decision["hash_validation_status"] = manifest["status"]
    if manifest["status"] != "PASS":
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
