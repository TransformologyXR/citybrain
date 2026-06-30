#!/usr/bin/env python3
"""Define the D6 Incident Mode preflight contracts."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-CITYBRAIN-D6-INCIDENT-MODE-PREFLIGHT"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_PREFLIGHT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_INCIDENT_MODE_PREFLIGHT"
HOLD_STATUS = "HOLD_MAIN_CITYBRAIN_D6_INCIDENT_MODE_PREFLIGHT_FROZEN_CHAIN_NOT_PRESERVED"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_preflight"

UPSTREAMS = {
    "r7_multi_domain_edge_registry_runtime_slice": {
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
    },
    "d5_event_fabric_integration_r3": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_event_fabric_integration_r3",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_WITH_LIMITATIONS",
    },
    "d5_track2_handoff_r4": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_track2_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_WITH_LIMITATIONS",
    },
    "d6_d5_local_running_control_room_slice_r1": {
        "root": "outputs/main_citybrain_d6_d5_local_running_control_room_slice_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_WITH_LIMITATIONS",
    },
    "d6_d5_local_running_slice_closeout": {
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS",
    },
}

FROZEN_RUNNERS = [
    "scripts/run_main_citybrain_d5_local_served_runtime_event_fabric_integration_r3.py",
    "scripts/run_main_citybrain_d5_local_served_runtime_track2_handoff_r4.py",
    "scripts/run_main_citybrain_d6_d5_local_running_control_room_slice_r1.py",
    "scripts/run_main_citybrain_d6_d5_local_running_slice_closeout.py",
]

MANDATORY_BOUNDARY = (
    "Incident Mode is human-or-replay initiated. CityBrain does not watch live streams, "
    "autonomously detect incidents, push alerts, dispatch resources, control routes/assets, "
    "enforce rules, or make legal/certified decisions. It contextualizes supplied/replayed "
    "events for operator review only."
)

LIMITATIONS = [
    "preflight and contract task only",
    "human-provided, replay, or fixture event inputs only",
    "review-context assembly only",
    "no live monitoring or autonomous incident detection",
    "no alert push, dispatch, routing/control, enforcement, legal/certified claim, or automated action",
    "no production service or public API readiness claim",
]

SAFE_INPUT_MODES = [
    "human_submitted_review_event",
    "replay_event_reference",
    "fixture_event_reference",
]

FORBIDDEN_INPUT_MODES = [
    "autonomous_detection",
    "live_monitoring",
    "alert_push",
    "dispatch",
    "enforcement",
    "control",
]

ALLOWED_REVIEW_STATES = [
    "draft_review_context",
    "pending_operator_review",
    "reviewed_context",
    "needs_more_evidence",
    "unresolved_context",
    "quarantined_context",
    "dismissed_review_context",
]

FORBIDDEN_REVIEW_STATES = [
    "confirmed_incident",
    "certified_incident",
    "legal_violation",
    "alert_sent",
    "dispatched",
    "route_controlled",
    "enforced",
    "auto_resolved",
]

SAFE_NEXT_LOOKS = [
    "inspect evidence refs",
    "inspect entity relationship context",
    "compare related event state",
    "open Omniverse overlay context",
    "open web companion evidence context",
    "review unresolved candidates",
    "review limitations",
]

FORBIDDEN_NEXT_LOOKS = [
    "dispatch",
    "route",
    "control",
    "enforce",
    "notify as alert",
    "certify incident",
    "confirm legal violation",
    "trigger automated workflow",
    "mutate source system",
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


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8", errors="replace")


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


def run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False)
        return (result.stdout + result.stderr).strip()
    except Exception as exc:
        return f"GIT_COMMAND_FAILED: {exc}"


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
                if len(artifacts) >= 24:
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


def preservation_gate(pre: dict[str, dict[str, Any]]) -> dict[str, Any]:
    closeout_root = root_path(UPSTREAMS["d6_d5_local_running_slice_closeout"]["root"])
    closeout_decision = read_json(closeout_root / "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json", {})
    hash_validation = read_json(closeout_root / "HASH_VALIDATION_REPORT.json", {})
    closeout_manifest = read_json(closeout_root / "HASH_MANIFEST.json", {})
    tracked_runners = []
    missing_tracked_runners = []
    for runner in FROZEN_RUNNERS:
        tracked = bool(run_git(["ls-files", "--error-unmatch", runner])) and "error:" not in run_git(["ls-files", "--error-unmatch", runner]).lower()
        if tracked:
            tracked_runners.append(runner)
        else:
            missing_tracked_runners.append(runner)
    output_ignore_probe = run_git(
        [
            "check-ignore",
            "-v",
            "outputs/main_citybrain_d6_d5_local_running_slice_closeout/MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json",
            "outputs/main_citybrain_d6_d5_local_running_slice_closeout/HASH_MANIFEST.json",
        ]
    )
    closeout_green = closeout_decision.get("status") == UPSTREAMS["d6_d5_local_running_slice_closeout"]["expected"]
    closeout_hash_green = hash_validation.get("status") == "PASS" and closeout_manifest.get("status") == "PASS"
    code_preserved = not missing_tracked_runners
    output_preserved = closeout_root.exists() and closeout_hash_green and bool(output_ignore_probe)
    gate_status = "PASS" if closeout_green and code_preserved and output_preserved else "HOLD"
    report = {
        "status": gate_status,
        "timestamp": utc_now(),
        "latest_commit": run_git(["log", "-1", "--oneline"]),
        "git_status_short": run_git(["status", "--short"]),
        "tracked_frozen_runners": tracked_runners,
        "missing_tracked_frozen_runners": missing_tracked_runners,
        "frozen_output_artifacts_are_gitignored": bool(output_ignore_probe),
        "output_ignore_probe": output_ignore_probe,
        "closeout_status": closeout_decision.get("status"),
        "closeout_hash_validation_status": hash_validation.get("status"),
        "closeout_hash_manifest_status": closeout_manifest.get("status"),
        "frozen_chain_preservation_basis": [
            "runner code is tracked in git",
            "closeout output pack is intentionally ignored by git",
            "closeout output pack has PASS hash validation and PASS hash manifest",
            "this preflight writes a new output root and consumes frozen roots read-only",
        ],
        "pre_snapshots": pre,
        "hold_reason": None if gate_status == "PASS" else "frozen closeout chain is not committed or locally hash-preserved",
    }
    write_json(OUTPUT_ROOT / "PRESERVATION_GATE_REPORT.json", report)
    return report


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
                "consumed_by_incident_mode_preflight": branch["green"],
                "read_only": True,
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS" if all(row["green"] for row in rows) else "FAIL", "branches": rows}
    write_json(OUTPUT_ROOT / "FROZEN_CHAIN_CONSUMPTION_REGISTER.json", report)
    return report


def write_scope() -> None:
    write_text(
        OUTPUT_ROOT / "INCIDENT_MODE_SCOPE_AND_BOUNDARY.md",
        f"""# Incident Mode Scope And Boundary

{MANDATORY_BOUNDARY}

Incident Mode preflight defines contracts for:

- human-provided event inputs
- replay or fixture event references
- affected entity resolution
- event/state/relationship context retrieval
- evidence bundle assembly
- operator review briefing packets
- safe next-look suggestions

It does not implement a live service, live monitor, autonomous detector, alerting system, dispatch workflow, enforcement flow, production API, or automated action.
""",
    )


def write_contracts() -> dict[str, Any]:
    incident_input = {
        "status": "PASS",
        "contract_name": "INCIDENT_INPUT_CONTRACT",
        "contract_mode": "review_only_preflight",
        "required_fields": [
            "incident_review_input_id",
            "input_mode",
            "source_event_ref",
            "event_family",
            "event_context_type",
            "submitted_by_context",
            "event_time",
            "received_time",
            "location_ref",
            "candidate_entity_refs",
            "narrative_hint",
            "evidence_refs",
            "limitation_refs",
            "claim_boundary",
        ],
        "input_mode_enum": SAFE_INPUT_MODES,
        "forbidden_input_modes": FORBIDDEN_INPUT_MODES,
        "example_fixture": {
            "incident_review_input_id": "incident-preflight-input-001",
            "input_mode": "fixture_event_reference",
            "source_event_ref": "event-fabric-r2-current-001",
            "event_family": "local_replay_event_context",
            "event_context_type": "operator_review_context",
            "submitted_by_context": "developer_demo_fixture",
            "event_time": "replay_time_from_source_event",
            "received_time": utc_now(),
            "location_ref": "scene_focus_or_event_location_ref",
            "candidate_entity_refs": ["candidate_entity_ref_from_runtime_packet"],
            "narrative_hint": "Review supplied/replayed event context only.",
            "evidence_refs": ["source_runtime_fixture_or_packet_ref"],
            "limitation_refs": ["review_context_only"],
            "claim_boundary": MANDATORY_BOUNDARY,
        },
        "claim_boundary": MANDATORY_BOUNDARY,
    }
    affected_entity = {
        "status": "PASS",
        "contract_name": "AFFECTED_ENTITY_RESOLUTION_CONTRACT",
        "source_contexts": [
            "Event Fabric R2/D5 R3 materialized event state",
            "D4X R7 multi-domain edge registry",
            "D5 R4 Track2 handoff packets",
            "D6/D5 control-room packets",
        ],
        "resolution_classes": {
            "directly_referenced_entities": "candidate refs supplied by incident input or D5 runtime packet",
            "edge_neighbour_context": "R7 edge-neighbour refs kept as relationship context",
            "overlay_context": "Track2/D6 overlay refs kept as scene or companion context",
            "unresolved_candidates": "kept as unresolved_context and never promoted to verified truth",
            "quarantined_candidates": "kept as quarantined_context and never promoted to verified truth",
            "unsupported_or_missing_context": "returned as unsupported/missing context with limitation refs",
        },
        "truth_promotion_policy": "unresolved, quarantined, candidate, and review-only context must not be promoted into verified, certified, legal, or official truth",
        "claim_boundary": MANDATORY_BOUNDARY,
    }
    evidence_bundle = {
        "status": "PASS",
        "contract_name": "INCIDENT_EVIDENCE_BUNDLE_CONTRACT",
        "required_fields": [
            "incident_review_bundle_id",
            "input_ref",
            "resolved_entity_refs",
            "event_state_refs",
            "edge_refs",
            "runtime_packet_refs",
            "omniverse_overlay_refs",
            "web_companion_refs",
            "evidence_refs",
            "limitation_refs",
            "uncertainty_summary",
            "review_state",
            "claim_boundary",
        ],
        "review_state_enum": ALLOWED_REVIEW_STATES,
        "evidence_policy": "evidence_refs and limitation_refs are mandatory and co-displayed",
        "claim_boundary": MANDATORY_BOUNDARY,
    }
    operator_packet = {
        "status": "PASS",
        "contract_name": "OPERATOR_REVIEW_PACKET_CONTRACT",
        "required_fields": [
            "operator_review_packet_id",
            "incident_review_bundle_ref",
            "review_summary",
            "affected_entities",
            "event_context",
            "relationship_context",
            "evidence_summary",
            "limitations",
            "uncertainties",
            "safe_next_looks",
            "forbidden_actions",
            "review_state",
            "claim_boundary",
        ],
        "phrasing_policy": "packet text must be review context only and must not be phrased as an alert, action instruction, dispatch instruction, control command, enforcement decision, legal finding, certification, or automated workflow trigger",
        "safe_next_looks": SAFE_NEXT_LOOKS,
        "forbidden_actions": FORBIDDEN_NEXT_LOOKS,
        "claim_boundary": MANDATORY_BOUNDARY,
    }
    safe_next_policy = {
        "status": "PASS",
        "policy_name": "SAFE_NEXT_LOOK_POLICY",
        "allowed_review_suggestions": SAFE_NEXT_LOOKS,
        "forbidden_action_suggestions": FORBIDDEN_NEXT_LOOKS,
        "policy": "safe next looks are optional review suggestions only; they must not instruct action or mutate a source system",
        "claim_boundary": MANDATORY_BOUNDARY,
    }
    review_state_model = {
        "status": "PASS",
        "model_name": "INCIDENT_REVIEW_STATE_MODEL",
        "allowed_review_states": ALLOWED_REVIEW_STATES,
        "forbidden_review_states": FORBIDDEN_REVIEW_STATES,
        "state_policy": "states describe review posture only and carry no operational, legal, certified, alerting, dispatch, control, enforcement, or automated outcome",
        "claim_boundary": MANDATORY_BOUNDARY,
    }
    runtime_plan = {
        "status": "PASS",
        "plan_name": "D5_D6_RUNTIME_INTEGRATION_PLAN",
        "integration_mode": "future local/replay fixture integration only",
        "planned_steps": [
            "accept safe incident input contract",
            "query D5 R3 local runtime fixture routes for event state",
            "query R7 relationship context as review-only edge context",
            "assemble D5 R4 handoff packet refs",
            "compose D6 control-room review bundle",
            "emit operator review packet with evidence, limitations, uncertainties, and safe next looks",
        ],
        "not_implemented": [
            "production service",
            "public API",
            "live stream watcher",
            "autonomous detector",
            "alert push",
            "dispatch workflow",
            "routing/control workflow",
            "enforcement workflow",
            "legal/certified decision workflow",
        ],
        "claim_boundary": MANDATORY_BOUNDARY,
    }
    handoff_impact = {
        "status": "PASS",
        "impact_name": "OMNIVERSE_WEB_HANDOFF_IMPACT",
        "omniverse": {
            "surface": "Kit/Composer overlay context",
            "impact": "Incident review packets may reference overlay context and affected scene focus only.",
            "full_citywide_twin_claim": False,
        },
        "web": {
            "surface": "companion evidence/episode/executive context",
            "impact": "Incident review packets may reference evidence bundle, uncertainty, limitation, and executive context.",
            "production_frontend_claim": False,
        },
        "claim_boundary": MANDATORY_BOUNDARY,
    }
    validation_plan = {
        "status": "PASS",
        "plan_name": "INCIDENT_MODE_VALIDATION_PLAN",
        "checks": [
            "upstream frozen chain discovered",
            "closeout status is green",
            "preservation gate is recorded",
            "incident input contract contains only safe allowed input modes",
            "affected-entity contract preserves unresolved/quarantined/review-only status",
            "evidence bundle contract includes evidence and limitation refs",
            "operator packet contract remains review context only",
            "safe-next-look policy contains no allowed action instructions",
            "review-state model contains no forbidden allowed states",
            "forbidden claim audit passes",
            "no-action boundary audit passes",
            "no-mutation audit passes",
            "secret audit passes",
            "hash manifest validates generated artifacts",
            "local open index is present",
        ],
        "claim_boundary": MANDATORY_BOUNDARY,
    }
    payloads = {
        "INCIDENT_INPUT_CONTRACT.json": incident_input,
        "AFFECTED_ENTITY_RESOLUTION_CONTRACT.json": affected_entity,
        "INCIDENT_EVIDENCE_BUNDLE_CONTRACT.json": evidence_bundle,
        "OPERATOR_REVIEW_PACKET_CONTRACT.json": operator_packet,
        "SAFE_NEXT_LOOK_POLICY.json": safe_next_policy,
        "INCIDENT_REVIEW_STATE_MODEL.json": review_state_model,
        "D5_D6_RUNTIME_INTEGRATION_PLAN.json": runtime_plan,
        "OMNIVERSE_WEB_HANDOFF_IMPACT.json": handoff_impact,
        "INCIDENT_MODE_VALIDATION_PLAN.json": validation_plan,
    }
    for name, payload in payloads.items():
        write_json(OUTPUT_ROOT / name, payload)
    return payloads


def validate_contracts(payloads: dict[str, Any], input_index: dict[str, Any], preservation: dict[str, Any]) -> dict[str, Any]:
    incident_input = payloads["INCIDENT_INPUT_CONTRACT.json"]
    affected_entity = payloads["AFFECTED_ENTITY_RESOLUTION_CONTRACT.json"]
    evidence_bundle = payloads["INCIDENT_EVIDENCE_BUNDLE_CONTRACT.json"]
    operator_packet = payloads["OPERATOR_REVIEW_PACKET_CONTRACT.json"]
    safe_policy = payloads["SAFE_NEXT_LOOK_POLICY.json"]
    review_model = payloads["INCIDENT_REVIEW_STATE_MODEL.json"]
    closeout_green = next(
        (branch.get("status") == UPSTREAMS["d6_d5_local_running_slice_closeout"]["expected"] for branch in input_index["branches"] if branch["branch"] == "d6_d5_local_running_slice_closeout"),
        False,
    )
    checks = [
        {"check": "upstream_frozen_chain_discovered", "status": "PASS" if input_index["status"] == "PASS" else "FAIL"},
        {"check": "closeout_status_green", "status": "PASS" if closeout_green else "FAIL"},
        {"check": "preservation_gate_recorded", "status": "PASS" if preservation["status"] == "PASS" else "FAIL"},
        {"check": "incident_input_allowed_modes_safe", "status": "PASS" if not set(incident_input["input_mode_enum"]) & set(FORBIDDEN_INPUT_MODES) else "FAIL"},
        {"check": "affected_entity_preserves_review_states", "status": "PASS" if all(token in json.dumps(affected_entity) for token in ["unresolved_context", "quarantined_context", "review-only"]) else "FAIL"},
        {"check": "evidence_bundle_has_evidence_and_limitations", "status": "PASS" if {"evidence_refs", "limitation_refs"}.issubset(set(evidence_bundle["required_fields"])) else "FAIL"},
        {"check": "operator_packet_review_context_only", "status": "PASS" if "review context only" in operator_packet["phrasing_policy"] else "FAIL"},
        {"check": "safe_next_look_allowed_terms_safe", "status": "PASS" if not any(item in safe_policy["allowed_review_suggestions"] for item in FORBIDDEN_NEXT_LOOKS) else "FAIL"},
        {"check": "review_state_allowed_terms_safe", "status": "PASS" if not set(review_model["allowed_review_states"]) & set(FORBIDDEN_REVIEW_STATES) else "FAIL"},
    ]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL", "checks": checks}


def audit_forbidden_claims() -> dict[str, Any]:
    positive_patterns = [
        r'"production_service"\s*:\s*true',
        r'"public_api_ready"\s*:\s*true',
        r'"autonomous_monitoring"\s*:\s*true',
        r'"autonomous_detection"\s*:\s*true',
        r'"live_monitoring"\s*:\s*true',
        r'"alert_push"\s*:\s*true',
        r'"dispatch"\s*:\s*true',
        r'"routing_control"\s*:\s*true',
        r'"enforcement"\s*:\s*true',
        r'"legal_certification"\s*:\s*true',
        r'"full_citywide_twin_claim"\s*:\s*true',
        r'"production_frontend_claim"\s*:\s*true',
        r"confirmed_incident['\"]?\s*:",
        r"certified_incident['\"]?\s*:",
        r"alert_sent['\"]?\s*:",
        r"dispatched['\"]?\s*:",
        r"route_controlled['\"]?\s*:",
        r"enforced['\"]?\s*:",
    ]
    joined = ""
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name not in {"FORBIDDEN_CLAIM_AUDIT.json", "HASH_MANIFEST.json"} and item.suffix.lower() in {".json", ".md", ".txt"}:
            joined += "\n" + item.read_text(encoding="utf-8", errors="ignore").lower()
    hits = []
    for pattern in positive_patterns:
        if re.search(pattern, joined):
            hits.append(pattern)
    report = {"status": "PASS" if not hits else "FAIL", "positive_forbidden_claim_hits": hits, "claim_boundary": MANDATORY_BOUNDARY}
    write_json(OUTPUT_ROOT / "FORBIDDEN_CLAIM_AUDIT.json", report)
    return report


def audit_no_action_boundary(payloads: dict[str, Any]) -> dict[str, Any]:
    boundary_files = [
        "README.md",
        "INCIDENT_MODE_SCOPE_AND_BOUNDARY.md",
        "INCIDENT_INPUT_CONTRACT.json",
        "AFFECTED_ENTITY_RESOLUTION_CONTRACT.json",
        "INCIDENT_EVIDENCE_BUNDLE_CONTRACT.json",
        "OPERATOR_REVIEW_PACKET_CONTRACT.json",
        "SAFE_NEXT_LOOK_POLICY.json",
        "INCIDENT_REVIEW_STATE_MODEL.json",
        "D5_D6_RUNTIME_INTEGRATION_PLAN.json",
        "OMNIVERSE_WEB_HANDOFF_IMPACT.json",
        "INCIDENT_MODE_VALIDATION_PLAN.json",
    ]
    missing_boundary = []
    for name in boundary_files:
        text = read_text(OUTPUT_ROOT / name)
        if MANDATORY_BOUNDARY not in text:
            missing_boundary.append(name)
    safe_policy = payloads["SAFE_NEXT_LOOK_POLICY.json"]
    operator_packet = payloads["OPERATOR_REVIEW_PACKET_CONTRACT.json"]
    allowed_safe = not any(item in safe_policy["allowed_review_suggestions"] for item in FORBIDDEN_NEXT_LOOKS)
    operator_review_only = "review context only" in operator_packet["phrasing_policy"]
    report = {
        "status": "PASS" if not missing_boundary and allowed_safe and operator_review_only else "FAIL",
        "missing_boundary_files": missing_boundary,
        "safe_next_looks_are_review_only": allowed_safe,
        "operator_packet_review_only": operator_review_only,
        "claim_boundary": MANDATORY_BOUNDARY,
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


def write_readme_and_index() -> None:
    artifact_names = [
        "MAIN_CITYBRAIN_D6_INCIDENT_MODE_PREFLIGHT_DECISION.json",
        "README.md",
        "INPUT_ARTIFACT_INDEX.json",
        "FROZEN_CHAIN_CONSUMPTION_REGISTER.json",
        "PRESERVATION_GATE_REPORT.json",
        "INCIDENT_MODE_SCOPE_AND_BOUNDARY.md",
        "INCIDENT_INPUT_CONTRACT.json",
        "AFFECTED_ENTITY_RESOLUTION_CONTRACT.json",
        "INCIDENT_EVIDENCE_BUNDLE_CONTRACT.json",
        "OPERATOR_REVIEW_PACKET_CONTRACT.json",
        "SAFE_NEXT_LOOK_POLICY.json",
        "INCIDENT_REVIEW_STATE_MODEL.json",
        "D5_D6_RUNTIME_INTEGRATION_PLAN.json",
        "OMNIVERSE_WEB_HANDOFF_IMPACT.json",
        "INCIDENT_MODE_VALIDATION_PLAN.json",
        "FORBIDDEN_CLAIM_AUDIT.json",
        "NO_ACTION_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "HASH_MANIFEST.json",
        "LOCAL_OPEN_INDEX.md",
    ]
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

{MANDATORY_BOUNDARY}

This pack defines Incident Mode as a bounded preflight and contract layer over the frozen local/replay CityBrain control-room spine.

It produces contracts for incident input, affected-entity resolution, evidence bundle assembly, operator review packet shape, safe next-look policy, review states, runtime integration planning, and Omniverse/web handoff impact.

No live service, production/public API, autonomous detector, alert push, dispatch, routing/control, enforcement, legal/certified decision, full citywide twin claim, source mutation, or automated action is created.
""",
    )
    lines = [
        f"# {TASK_NAME}",
        "",
        "Incident Mode preflight output index.",
        "",
        MANDATORY_BOUNDARY,
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- [{name}]({name})" for name in artifact_names)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pre = {meta["root"]: snapshot(root_path(meta["root"])) for meta in UPSTREAMS.values()}
    input_index, missing = discover_inputs(pre)
    preservation = preservation_gate(pre)
    chain = branch_summary(input_index)
    write_scope()
    payloads = write_contracts()
    write_readme_and_index()
    validation = validate_contracts(payloads, input_index, preservation)
    forbidden = audit_forbidden_claims()
    no_action = audit_no_action_boundary(payloads)
    mutation = audit_mutation(pre)
    secret = audit_secret()

    status = PASS_STATUS
    if preservation["status"] != "PASS":
        status = HOLD_STATUS
    elif not all(
        [
            not missing,
            input_index["status"] == "PASS",
            chain["status"] == "PASS",
            validation["status"] == "PASS",
            forbidden["status"] == "PASS",
            no_action["status"] == "PASS",
            mutation["status"] == "PASS",
            secret["status"] == "PASS",
        ]
    ):
        status = FAIL_STATUS

    contracts_produced = [
        "INCIDENT_INPUT_CONTRACT.json",
        "AFFECTED_ENTITY_RESOLUTION_CONTRACT.json",
        "INCIDENT_EVIDENCE_BUNDLE_CONTRACT.json",
        "OPERATOR_REVIEW_PACKET_CONTRACT.json",
        "SAFE_NEXT_LOOK_POLICY.json",
        "INCIDENT_REVIEW_STATE_MODEL.json",
        "D5_D6_RUNTIME_INTEGRATION_PLAN.json",
        "OMNIVERSE_WEB_HANDOFF_IMPACT.json",
        "INCIDENT_MODE_VALIDATION_PLAN.json",
    ]
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "upstream_artifacts_discovered": len(input_index["branches"]) - len(missing),
        "upstream_artifacts_missing": missing,
        "preservation_gate_status": preservation["status"],
        "frozen_chain_consumption_status": chain["status"],
        "contract_validation_status": validation["status"],
        "contracts_produced": contracts_produced,
        "forbidden_claim_audit_result": forbidden["status"],
        "no_action_boundary_audit_result": no_action["status"],
        "no_mutation_audit_result": mutation["status"],
        "secret_audit_result": secret["status"],
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-EVIDENCE-BUNDLE-R1",
        "parallel_backend_task": "MAIN-CITYBRAIN-D4X-R8-MULTI-DOMAIN-EDGE-REGISTRY-HARDENING",
        "claim_boundary": MANDATORY_BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_PREFLIGHT_DECISION.json", decision)
    manifest = hash_manifest()
    decision["hash_validation_status"] = manifest["status"]
    if manifest["status"] != "PASS" and decision["status"] == PASS_STATUS:
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_PREFLIGHT_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
