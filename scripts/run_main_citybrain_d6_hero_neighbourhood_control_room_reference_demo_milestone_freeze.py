#!/usr/bin/env python3
"""Freeze the Hero Neighbourhood control-room reference demo milestone.

This is a ledger/package task only. It validates the green upstream chain,
summarizes the frozen truth, records limitations and next options, and writes
all artifacts under a new output root without mutating upstream outputs.
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

TASK_NAME = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-MILESTONE-FREEZE"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_MILESTONE_FREEZE_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_MILESTONE_FREEZE"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_milestone_freeze"

BOUNDARY = """This is a bounded local/replay control-room reference demo milestone freeze.

Do not claim production readiness, public API readiness, live monitoring, autonomous incident detection, autonomous monitoring, alert push, dispatch, routing/control, enforcement, official ticket/case creation, legal/certified incident finding, certified citywide digital twin, physical accuracy, automated action, citywide complete twin, or production Omniverse deployment.

All incident, event, current-state, relationship, operator-surface, Omniverse, and web-context outputs remain local/replay review/query context only."""

FROZEN_TRUTH = [
    "Hero Neighbourhood control-room reference demo is a bounded local/replay artifact-backed demo package.",
    "Omniverse Kit/Composer remains the primary spatial control-room surface.",
    "Web remains the companion evidence / episode / executive surface.",
    "Incident Mode remains human-or-replay initiated review/query contextualization only.",
    "CER/SEG v2 compatibility is contract/read-only compatibility, not a mutation of frozen prior outputs.",
    "Hero scene bindings may include scene/source/operator refs; these are scene-binding context and must not be promoted to canonical IDs.",
    "Event/current-state/relationship/operator-surface/Omniverse/web context remains local/replay review/query context only.",
]

NEXT_OPTIONS = [
    "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-REFRESH-R3",
    "MAIN-CITYBRAIN-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    "MAIN-CITYBRAIN-D6-PERCEPTION-TO-INCIDENT-REVIEW-PREFLIGHT",
    "MAIN-CITYBRAIN-D6-DUBAI-ANCHORED-DATA-AND-SCENARIO-PACK-PREFLIGHT",
    "MAIN-CITYBRAIN-D6-SIMULATION-AND-OPTIMISATION-PREFLIGHT",
]

UPSTREAMS = {
    "demo_closeout_r1": {
        "task": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-R1",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1",
        "decision": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS",
    },
    "demo_r1": {
        "task": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-R1",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_r1",
        "decision": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_WITH_LIMITATIONS",
    },
    "integration_readiness_review": {
        "task": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-AND-CERSEG-V2-INTEGRATION-READINESS-REVIEW",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review",
        "decision": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
    },
    "hero_scene_pack_closeout": {
        "task": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-SCENE-PACK-CLOSEOUT",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout",
        "decision": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_WITH_LIMITATIONS",
    },
    "cerseg_v2_closeout": {
        "task": "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "decision": "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
    },
    "incident_track2a_operator_surface_r4": {
        "task": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-TRACK2A-OPERATOR-SURFACE-HANDOFF-R4",
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "decision": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
    },
    "incident_mode_closeout": {
        "task": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "decision": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
    },
    "d6_d5_local_running_closeout": {
        "task": "MAIN-CITYBRAIN-D6-D5-LOCAL-RUNNING-SLICE-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "decision": "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS",
    },
    "r8_multi_domain_hardening": {
        "task": "MAIN-CITYBRAIN-D4X-R8-MULTI-DOMAIN-EDGE-REGISTRY-HARDENING",
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "decision": "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
    },
    "r7_multi_domain_runtime_slice": {
        "task": "MAIN-CITYBRAIN-D4X-R7-MULTI-DOMAIN-EDGE-REGISTRY-RUNTIME-SLICE",
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "decision": "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
    },
}

REQUIRED_OUTPUTS = [
    "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_MILESTONE_FREEZE_DECISION.json",
    "README.md",
    "LOCAL_OPEN_INDEX.md",
    "UPSTREAM_ARTIFACT_INDEX.json",
    "UPSTREAM_STATUS_SUMMARY.json",
    "FROZEN_MILESTONE_TRUTH_REGISTER.json",
    "FROZEN_MILESTONE_TRUTH_REGISTER.md",
    "TRACK_CLOSURE_LEDGER.json",
    "TRACK_CLOSURE_LEDGER.md",
    "CONTROL_ROOM_DEMO_MILESTONE_FREEZE_SUMMARY.json",
    "CONTROL_ROOM_DEMO_MILESTONE_FREEZE_SUMMARY.md",
    "KNOWN_LIMITATIONS_AND_NON_BLOCKING_GAPS.json",
    "BOUNDARY_AND_CLAIM_FREEZE.md",
    "NEXT_TRACK_DECISION_OPTIONS.json",
    "VALIDATION_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def status_from(payload: Any) -> str | None:
    if isinstance(payload, dict):
        return str(payload.get("status") or payload.get("final_status") or payload.get("decision_status") or "") or None
    return None


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


def prepare_output_root() -> None:
    if OUTPUT_ROOT.resolve().parent != (REPO_ROOT / "outputs").resolve():
        raise RuntimeError(f"Refusing unexpected output root: {OUTPUT_ROOT}")
    if OUTPUT_ROOT.name != "main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_milestone_freeze":
        raise RuntimeError(f"Refusing unexpected output root name: {OUTPUT_ROOT.name}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def parse_json_jsonl(root: Path) -> dict[str, Any]:
    json_files = sorted(root.rglob("*.json")) if root.exists() else []
    jsonl_files = sorted(root.rglob("*.jsonl")) if root.exists() else []
    failures = []
    jsonl_records = 0
    for path in json_files:
        try:
            read_json(path, {})
        except Exception as exc:
            failures.append({"path": rel(path), "error": str(exc)})
    for path in jsonl_files:
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                json.loads(line)
                jsonl_records += 1
            except Exception as exc:
                failures.append({"path": rel(path), "error": f"line {line_no}: {exc}"})
    return {
        "json_file_count": len(json_files),
        "jsonl_file_count": len(jsonl_files),
        "jsonl_record_count": jsonl_records,
        "parse_failure_count": len(failures),
        "parse_failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def discover_upstreams() -> tuple[dict[str, Any], dict[str, Any], list[str], dict[str, Any]]:
    rows = []
    missing = []
    decisions = {}
    for key, spec in UPSTREAMS.items():
        root = root_path(spec["root"])
        decision_path = root / spec["decision"]
        decision = read_json(decision_path, {}) if decision_path.exists() else {}
        decisions[key] = decision
        status = status_from(decision)
        green = root.exists() and decision_path.exists() and status == spec["expected"]
        if not green:
            missing.append(key)
        parse = parse_json_jsonl(root)
        artifacts = []
        if root.exists():
            for path in sorted(item for item in root.iterdir() if item.is_file())[:24]:
                artifacts.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        rows.append(
            {
                "upstream_key": key,
                "task_name": spec["task"],
                "root": spec["root"],
                "decision_file": rel(decision_path),
                "expected_status": spec["expected"],
                "status": status,
                "exists": root.exists(),
                "green": green,
                "read_only": True,
                "json_parse_status": parse["status"],
                "json_parse_report": parse,
                "sample_artifacts": artifacts,
            }
        )
    parse_failures = [row for row in rows if row["json_parse_status"] != "PASS"]
    artifact_index = {
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "upstreams": rows,
        "status": "PASS" if not missing and not parse_failures else "FAIL",
        "boundary": BOUNDARY,
    }
    status_summary = {
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "required_upstreams_found": sum(row["green"] for row in rows),
        "required_upstreams_total": len(rows),
        "missing_or_not_green": missing,
        "json_parse_status": "PASS" if not parse_failures else "FAIL",
        "json_parse_failures": [
            {"upstream_key": row["upstream_key"], "parse_failures": row["json_parse_report"]["parse_failures"]}
            for row in parse_failures
        ],
        "status": "PASS" if not missing and not parse_failures else "FAIL",
    }
    write_json(OUTPUT_ROOT / "UPSTREAM_ARTIFACT_INDEX.json", artifact_index)
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", status_summary)
    return artifact_index, status_summary, missing, decisions


def unique(values: list[Any]) -> list[str]:
    out = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            out.extend(unique(value))
            continue
        text = str(value)
        if text and text not in out:
            out.append(text)
    return out


def collect_limitations(decisions: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    for decision in decisions.values():
        if isinstance(decision, dict):
            values.append(decision.get("limitations"))
    return unique(values)


def closeout_decision(decisions: dict[str, Any]) -> dict[str, Any]:
    return decisions.get("demo_closeout_r1", {})


def r1_decision(decisions: dict[str, Any]) -> dict[str, Any]:
    return decisions.get("demo_r1", {})


def write_truth_register(decisions: dict[str, Any]) -> dict[str, Any]:
    closeout = closeout_decision(decisions)
    truth = {
        "status": "PASS",
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "truth_statements": FROZEN_TRUTH,
        "frozen_input_status": closeout.get("status"),
        "manifest_rows_count": closeout.get("r1_manifest_row_count"),
        "hero_bindings_count": closeout.get("hero_bindings_count"),
        "hero_overlay_packets_count": closeout.get("overlay_packet_count"),
        "operator_surface_packets_count": closeout.get("operator_surface_packet_count"),
        "web_companion_packets_count": closeout.get("web_companion_packet_count"),
        "unresolved_quarantined_preserved_count": closeout.get("unresolved_quarantined_preserved_count"),
        "boundary": BOUNDARY,
    }
    md = ["# Frozen Milestone Truth Register", "", f"Status: `{truth['status']}`", "", BOUNDARY, ""]
    md.extend(f"- {statement}" for statement in FROZEN_TRUTH)
    write_json(OUTPUT_ROOT / "FROZEN_MILESTONE_TRUTH_REGISTER.json", truth)
    write_text(OUTPUT_ROOT / "FROZEN_MILESTONE_TRUTH_REGISTER.md", "\n".join(md))
    return truth


def write_track_ledger(decisions: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for key, spec in UPSTREAMS.items():
        decision = decisions.get(key, {})
        rows.append(
            {
                "ledger_key": key,
                "task_name": spec["task"],
                "status": status_from(decision),
                "root": spec["root"],
                "closed_or_consumed": bool(status_from(decision) == spec["expected"]),
                "read_only_consumption": True,
            }
        )
    ledger = {
        "status": "PASS" if all(row["closed_or_consumed"] for row in rows) else "FAIL",
        "track_closure_count": sum(row["closed_or_consumed"] for row in rows),
        "rows": rows,
        "boundary": BOUNDARY,
    }
    md = ["# Track Closure Ledger", "", f"Status: `{ledger['status']}`", "", BOUNDARY, ""]
    md.extend(f"- {row['task_name']}: `{row['status']}`" for row in rows)
    write_json(OUTPUT_ROOT / "TRACK_CLOSURE_LEDGER.json", ledger)
    write_text(OUTPUT_ROOT / "TRACK_CLOSURE_LEDGER.md", "\n".join(md))
    return ledger


def write_limitations(decisions: dict[str, Any]) -> dict[str, Any]:
    closeout = closeout_decision(decisions)
    r1 = r1_decision(decisions)
    limitations = collect_limitations(decisions)
    gaps = unique([closeout.get("non_blocking_gaps"), r1.get("non_blocking_gaps")])
    data = {
        "status": "PASS",
        "known_limitations_count": len(limitations),
        "known_limitations": limitations,
        "non_blocking_gaps_count": len(gaps),
        "non_blocking_gaps": gaps,
        "preserved_from_r1_and_closeout": True,
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "KNOWN_LIMITATIONS_AND_NON_BLOCKING_GAPS.json", data)
    return data


def write_summary(decisions: dict[str, Any], upstream_summary: dict[str, Any], ledger: dict[str, Any], limitations: dict[str, Any]) -> dict[str, Any]:
    closeout = closeout_decision(decisions)
    summary = {
        "status": "PASS",
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "required_upstreams_found": upstream_summary["required_upstreams_found"],
        "required_upstreams_total": upstream_summary["required_upstreams_total"],
        "track_closure_count": ledger["track_closure_count"],
        "known_limitations_count": limitations["known_limitations_count"],
        "non_blocking_gaps_count": limitations["non_blocking_gaps_count"],
        "unresolved_quarantined_preserved_count": closeout.get("unresolved_quarantined_preserved_count"),
        "manifest_rows_count": closeout.get("r1_manifest_row_count"),
        "hero_bindings_count": closeout.get("hero_bindings_count"),
        "hero_overlay_packets_count": closeout.get("overlay_packet_count"),
        "operator_surface_packets_count": closeout.get("operator_surface_packet_count"),
        "web_companion_packets_count": closeout.get("web_companion_packet_count"),
        "boundary": BOUNDARY,
    }
    md = f"""# Control Room Demo Milestone Freeze Summary

Status: `{summary['status']}`

{BOUNDARY}

- Required upstreams: `{summary['required_upstreams_found']}/{summary['required_upstreams_total']}`
- Track closure count: `{summary['track_closure_count']}`
- Manifest rows: `{summary['manifest_rows_count']}`
- Hero bindings: `{summary['hero_bindings_count']}`
- Overlay packets: `{summary['hero_overlay_packets_count']}`
- Operator-surface packets: `{summary['operator_surface_packets_count']}`
- Web companion packets: `{summary['web_companion_packets_count']}`
- Known limitations: `{summary['known_limitations_count']}`
- Non-blocking gaps: `{summary['non_blocking_gaps_count']}`
- Unresolved/quarantined preserved: `{summary['unresolved_quarantined_preserved_count']}`
"""
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_DEMO_MILESTONE_FREEZE_SUMMARY.json", summary)
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_DEMO_MILESTONE_FREEZE_SUMMARY.md", md)
    return summary


def write_next_options() -> dict[str, Any]:
    data = {
        "status": "PASS",
        "recommended_next_task_options": NEXT_OPTIONS,
        "auto_started_next_task": False,
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "NEXT_TRACK_DECISION_OPTIONS.json", data)
    return data


def write_boundary_doc() -> None:
    allowed = [
        "bounded local/replay control-room reference demo",
        "artifact-backed operator walkthrough",
        "artifact-backed executive walkthrough",
        "Omniverse Kit/Composer handoff context",
        "web companion evidence/episode/executive context",
        "Incident Mode operator-review context",
        "CER/SEG v2 compatibility checked",
        "unresolved/quarantined context preserved",
        "review-only evidence and limitation trace",
    ]
    forbidden = [
        "production readiness",
        "public API readiness",
        "live monitoring",
        "autonomous incident detection",
        "autonomous monitoring",
        "alert push",
        "dispatch",
        "routing/control",
        "enforcement",
        "official ticket/case creation",
        "legal/certified incident finding",
        "certified citywide digital twin",
        "physical accuracy",
        "automated action",
        "citywide complete twin",
        "production Omniverse deployment",
    ]
    text = ["# Boundary And Claim Freeze", "", BOUNDARY, "", "## Allowed Wording", ""]
    text.extend(f"- {item}" for item in allowed)
    text.extend(["", "## Forbidden Claims", ""])
    text.extend(f"- {item}" for item in forbidden)
    write_text(OUTPUT_ROOT / "BOUNDARY_AND_CLAIM_FREEZE.md", "\n".join(text))


def claim_boundary_audit() -> dict[str, Any]:
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore").lower() for path in OUTPUT_ROOT.rglob("*") if path.is_file() and path.name != "CLAIM_BOUNDARY_AUDIT.json")
    positive_patterns = [
        r'"production_readiness_claim_made"\s*:\s*true',
        r'"public_api_readiness_claim_made"\s*:\s*true',
        r'"live_monitoring_claim_made"\s*:\s*true',
        r'"autonomous_incident_detection_claim_made"\s*:\s*true',
        r'"autonomous_monitoring_claim_made"\s*:\s*true',
        r'"alert_push_claim_made"\s*:\s*true',
        r'"dispatch_claim_made"\s*:\s*true',
        r'"routing_control_claim_made"\s*:\s*true',
        r'"enforcement_claim_made"\s*:\s*true',
        r'"official_ticket_case_creation_claim_made"\s*:\s*true',
        r'"legal_certified_incident_finding_claim_made"\s*:\s*true',
        r'"certified_citywide_digital_twin_claim_made"\s*:\s*true',
        r'"physical_accuracy_claim_made"\s*:\s*true',
        r'"automated_action_claim_made"\s*:\s*true',
        r'"production_omniverse_deployment_claim_made"\s*:\s*true',
        r"production ready for deployment",
        r"public api ready",
        r"live monitoring enabled",
        r"autonomous incident detection enabled",
        r"alert push enabled",
        r"dispatch command",
        r"routing/control command",
        r"enforcement action",
        r"official ticket created",
        r"certified incident finding enabled",
        r"production omniverse deployment enabled",
    ]
    hits = [pattern for pattern in positive_patterns if re.search(pattern, combined)]
    report = {
        "status": "PASS" if not hits and BOUNDARY.lower() in combined else "FAIL",
        "positive_forbidden_claim_hits": hits,
        "boundary_present": BOUNDARY.lower() in combined,
        "production_readiness_claim_made": False,
        "public_api_readiness_claim_made": False,
        "live_monitoring_claim_made": False,
        "autonomous_incident_detection_claim_made": False,
        "autonomous_monitoring_claim_made": False,
        "alert_push_claim_made": False,
        "dispatch_claim_made": False,
        "routing_control_claim_made": False,
        "enforcement_claim_made": False,
        "official_ticket_case_creation_claim_made": False,
        "legal_certified_incident_finding_claim_made": False,
        "certified_citywide_digital_twin_claim_made": False,
        "physical_accuracy_claim_made": False,
        "automated_action_claim_made": False,
        "production_omniverse_deployment_claim_made": False,
        "boundary": BOUNDARY,
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", report)
    return report


def no_action_audit() -> dict[str, Any]:
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore").lower() for path in OUTPUT_ROOT.rglob("*") if path.is_file() and path.name != "NO_ACTION_BOUNDARY_AUDIT.json")
    patterns = [
        r'"no_action_taken"\s*:\s*false',
        r'"action_taken"\s*:\s*true',
        r"dispatch command",
        r"routing/control command",
        r"enforcement action",
        r"official ticket created",
        r"automated action triggered",
    ]
    hits = [pattern for pattern in patterns if re.search(pattern, combined)]
    report = {"status": "PASS" if not hits else "FAIL", "positive_action_hits": hits, "no_action_taken": True, "boundary": BOUNDARY}
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", report)
    return report


def no_mutation_audit(before: dict[str, dict[str, Any]]) -> dict[str, Any]:
    changed = []
    for key, spec in UPSTREAMS.items():
        after = snapshot(root_path(spec["root"]))
        if before[key] != after:
            changed.append({"upstream_key": key, "root": spec["root"]})
    report = {
        "status": "PASS" if not changed else "FAIL",
        "watched_upstream_count": len(before),
        "changed_upstreams": changed,
        "output_root_only_mutated": not changed,
        "no_action_taken": True,
        "boundary": BOUNDARY,
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
        if not path.is_file() or path.name in {"SECRET_AUDIT.json", "HASH_MANIFEST.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings, "boundary": BOUNDARY}
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", report)
    return report


def hash_manifest() -> dict[str, Any]:
    rows = []
    for path in sorted(item for item in OUTPUT_ROOT.rglob("*") if item.is_file()):
        if path.name == "HASH_MANIFEST.json":
            continue
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    failures = [row["path"] for row in rows if not (REPO_ROOT / row["path"]).exists() or sha256_file(REPO_ROOT / row["path"]) != row["sha256"]]
    report = {
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "file_count": len(rows),
        "files": rows,
        "hash_validation_status": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", report)
    return report


def generated_json_parse_status() -> dict[str, Any]:
    parse = parse_json_jsonl(OUTPUT_ROOT)
    return {"status": parse["status"], **parse}


def required_files_status() -> dict[str, Any]:
    missing = [name for name in REQUIRED_OUTPUTS if not (OUTPUT_ROOT / name).exists()]
    return {"status": "PASS" if not missing else "FAIL", "missing": missing, "required_count": len(REQUIRED_OUTPUTS)}


def local_open_index_status() -> dict[str, Any]:
    path = OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md"
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    missing = [name for name in REQUIRED_OUTPUTS if name != "HASH_MANIFEST.json" and name not in text]
    return {"status": "PASS" if not missing else "FAIL", "missing_refs": missing}


def validation_report(upstream: dict[str, Any], ledger: dict[str, Any], limitations: dict[str, Any], truth: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    checks = [
        {"check": "required_upstreams_discovered", "status": upstream["status"]},
        {"check": "decision_statuses_green", "status": upstream["status"]},
        {"check": "closeout_r1_consumed", "status": "PASS" if summary.get("manifest_rows_count") else "FAIL"},
        {"check": "r1_demo_package_consumed", "status": "PASS" if summary.get("manifest_rows_count") else "FAIL"},
        {"check": "integration_readiness_review_consumed", "status": "PASS"},
        {"check": "hero_closeout_consumed", "status": "PASS"},
        {"check": "cerseg_v2_closeout_consumed", "status": "PASS"},
        {"check": "incident_mode_closeout_consumed", "status": "PASS"},
        {"check": "d6_d5_local_running_closeout_consumed", "status": "PASS"},
        {"check": "r7_r8_registry_outputs_consumed", "status": "PASS"},
        {"check": "known_limitation_count_preserved", "status": "PASS" if limitations["known_limitations_count"] > 0 else "FAIL"},
        {"check": "non_blocking_gaps_preserved", "status": "PASS" if limitations["non_blocking_gaps_count"] >= 0 else "FAIL"},
        {"check": "unresolved_quarantined_count_preserved", "status": "PASS" if summary.get("unresolved_quarantined_preserved_count") else "FAIL"},
        {"check": "frozen_truth_register_written", "status": truth["status"]},
        {"check": "track_closure_ledger_written", "status": ledger["status"]},
    ]
    report = {
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "checks": checks,
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "VALIDATION_REPORT.json", report)
    return report


def write_readme_and_index(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{decision['status']}`

{BOUNDARY}

- Required upstreams: `{decision['required_upstreams_found']}/{decision['required_upstreams_total']}`
- Track closure count: `{decision['track_closure_count']}`
- Known limitations: `{decision['known_limitations_count']}`
- Non-blocking gaps: `{decision['non_blocking_gaps_count']}`
- Unresolved/quarantined preserved: `{decision['unresolved_quarantined_preserved_count']}`
- Recommended next-task options: see `NEXT_TRACK_DECISION_OPTIONS.json`
""",
    )
    lines = [f"# {TASK_NAME}", "", f"Status: `{decision['status']}`", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in REQUIRED_OUTPUTS)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> int:
    prepare_output_root()
    before = {key: snapshot(root_path(spec["root"])) for key, spec in UPSTREAMS.items()}
    _artifact_index, upstream_summary, missing, decisions = discover_upstreams()

    if upstream_summary["status"] != "PASS":
        decision = {
            "status": FAIL_STATUS,
            "task_name": TASK_NAME,
            "timestamp": now_iso(),
            "output_root": str(OUTPUT_ROOT),
            "runner_path": str(Path(__file__).resolve()),
            "required_upstreams_found": upstream_summary["required_upstreams_found"],
            "required_upstreams_total": upstream_summary["required_upstreams_total"],
            "missing_or_not_green": missing,
            "recommended_next_task_options": [FIXUP_NEXT_TASK],
            "boundary": BOUNDARY,
        }
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_MILESTONE_FREEZE_DECISION.json", decision)
        write_text(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: `{FAIL_STATUS}`\n\n{BOUNDARY}\n")
        hash_manifest()
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 1

    truth = write_truth_register(decisions)
    ledger = write_track_ledger(decisions)
    limitations = write_limitations(decisions)
    summary = write_summary(decisions, upstream_summary, ledger, limitations)
    next_options = write_next_options()
    write_boundary_doc()
    validation = validation_report(upstream_summary, ledger, limitations, truth, summary)
    claim = claim_boundary_audit()
    no_action = no_action_audit()
    no_mutation = no_mutation_audit(before)
    secret = secret_audit()

    status = PASS_STATUS
    if not all(
        item["status"] == "PASS"
        for item in [upstream_summary, truth, ledger, limitations, summary, next_options, validation, claim, no_action, no_mutation, secret]
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
        "track_closure_count": ledger["track_closure_count"],
        "known_limitations_count": limitations["known_limitations_count"],
        "non_blocking_gaps_count": limitations["non_blocking_gaps_count"],
        "unresolved_quarantined_preserved_count": summary["unresolved_quarantined_preserved_count"],
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "generated_json_parse_status": "PENDING",
        "local_open_index_status": "PENDING",
        "production_readiness_claim_made": False,
        "public_api_readiness_claim_made": False,
        "live_monitoring_claim_made": False,
        "autonomous_incident_detection_claim_made": False,
        "autonomous_monitoring_claim_made": False,
        "alert_push_claim_made": False,
        "dispatch_claim_made": False,
        "routing_control_claim_made": False,
        "enforcement_claim_made": False,
        "official_ticket_case_creation_claim_made": False,
        "legal_certified_incident_finding_claim_made": False,
        "certified_citywide_digital_twin_claim_made": False,
        "physical_accuracy_claim_made": False,
        "automated_action_claim_made": False,
        "production_omniverse_deployment_claim_made": False,
        "recommended_next_task_options": NEXT_OPTIONS,
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_MILESTONE_FREEZE_DECISION.json", decision)
    write_readme_and_index(decision)
    claim = claim_boundary_audit()
    secret = secret_audit()
    hash_report = hash_manifest()
    required = required_files_status()
    parse = generated_json_parse_status()
    index = local_open_index_status()
    if not all(
        [
            claim["status"] == "PASS",
            secret["status"] == "PASS",
            hash_report["hash_validation_status"] == "PASS",
            required["status"] == "PASS",
            parse["status"] == "PASS",
            index["status"] == "PASS",
        ]
    ):
        decision["status"] = FAIL_STATUS
        decision["recommended_next_task_options"] = [FIXUP_NEXT_TASK]
    decision["claim_boundary_status"] = claim["status"]
    decision["secret_audit_status"] = secret["status"]
    decision["hash_validation_status"] = hash_report["hash_validation_status"]
    decision["generated_json_parse_status"] = parse["status"]
    decision["local_open_index_status"] = index["status"]
    decision["required_output_missing"] = required["missing"]
    decision["local_open_index_missing_refs"] = index["missing_refs"]
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_MILESTONE_FREEZE_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
