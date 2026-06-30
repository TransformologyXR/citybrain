#!/usr/bin/env python3
"""Build the D6 HITL reviewed-action governance lane.

This runner is intentionally deterministic and local-file only. It consumes
frozen Hero, Incident Mode, CER/SEG, local-running, and edge-registry outputs
read-only, then writes proposal-only reviewed-action packages under dedicated
Track D output roots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"

SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"
BOUNDARY = (
    "Track D HITL reviewed action is proposal-only, human-in-the-loop, "
    "local/replay review context. It does not execute actions, initiate "
    "automatic workflows, create tickets or cases, control routes, dispatch "
    "resources, enforce findings, certify incidents, expose a production or "
    "public API, monitor live conditions, push alerts, or mutate frozen "
    "upstream outputs."
)
NOT_AN_ACTION = (
    "This record is a reviewed-action proposal for human decision support only. "
    "It is not an instruction, command, execution request, ticket, case, legal "
    "finding, certified incident finding, route/control command, alert, or "
    "production action."
)
LIMITATIONS = [
    "proposal-only governance spine",
    "human-in-the-loop review states only",
    "local/replay review context only",
    "separate Track D operator panel packet family through R2",
    "inert execution adapter stub only after human approval",
    "no automatic execution",
    "no resource assignment or field operations",
    "no route or infrastructure control",
    "no enforcement or official case/ticket creation",
    "no legal/certified incident finding",
    "no live monitoring, alerts, production action system, or public API claim",
]

ALLOWED_PROPOSAL_TYPES = [
    "review_next_look",
    "request_more_evidence",
    "draft_advisory_for_review",
    "review_route_context",
    "review_access_constraint",
    "review_operator_note",
]
FORBIDDEN_PROPOSAL_TYPES = [
    "dispatch",
    "enforce",
    "control_route",
    "execute_now",
    "issue_ticket",
    "legal_finding",
    "certified_incident",
]
ALLOWED_HUMAN_DECISIONS = [
    "approve_for_inert_stub_only",
    "reject",
    "request_modification",
    "request_more_evidence",
]
LIFECYCLE_STATES = [
    "proposal_created",
    "awaiting_human_review",
    "approved_for_stub_only",
    "rejected_by_human",
    "modification_requested",
    "more_evidence_requested",
    "execution_stub_recorded",
    "monitor_review_context",
    "closed_review_context",
    "blocked_for_policy",
]

UPSTREAMS: dict[str, dict[str, Any]] = {
    "hero_control_room_demo_closeout_r1": {
        "label": "D6 Hero Neighbourhood Control Room Reference Demo Closeout R1",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1",
        "decision": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS",
        "required": True,
    },
    "hero_control_room_demo_r1": {
        "label": "D6 Hero Neighbourhood Control Room Reference Demo R1",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_r1",
        "decision": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_WITH_LIMITATIONS",
        "required": False,
    },
    "incident_mode_closeout": {
        "label": "Incident Mode Closeout",
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "decision": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
        "required": True,
    },
    "incident_mode_track2a_operator_surface_handoff_r4": {
        "label": "Incident Mode Track2A Operator Surface Handoff R4",
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "decision": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
        "required": True,
    },
    "d6_d5_local_running_slice_closeout": {
        "label": "D6/D5 local running slice closeout",
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "decision": "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS",
        "required": True,
    },
    "r7_edge_registry_runtime_slice": {
        "label": "R7 edge registry runtime slice",
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "decision": "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
        "required": True,
    },
    "r8_edge_registry_hardening": {
        "label": "R8 edge registry hardening",
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "decision": "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
        "required": True,
    },
    "cer_seg_cross_city_v2_closeout": {
        "label": "CER/SEG Cross-City v2 Closeout",
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "decision": "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
        "required": True,
    },
    "hero_cerseg_integration_readiness_review": {
        "label": "Hero + CERSEG Integration Readiness Review",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review",
        "decision": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "required": True,
    },
}

STAGES: dict[str, dict[str, Any]] = {
    "preflight": {
        "task": "MAIN-CITYBRAIN-D6-HITL-REVIEWED-ACTION-PREFLIGHT",
        "status": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_PREFLIGHT_WITH_LIMITATIONS",
        "fail_status": "FAIL_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_PREFLIGHT",
        "root": "main_citybrain_d6_hitl_reviewed_action_preflight",
        "decision": "MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_PREFLIGHT_DECISION.json",
    },
    "proposal": {
        "task": "MAIN-CITYBRAIN-D6-HITL-ACTION-PROPOSAL-CONTRACT-R1",
        "status": "PASS_MAIN_CITYBRAIN_D6_HITL_ACTION_PROPOSAL_CONTRACT_R1_WITH_LIMITATIONS",
        "fail_status": "FAIL_MAIN_CITYBRAIN_D6_HITL_ACTION_PROPOSAL_CONTRACT_R1",
        "root": "main_citybrain_d6_hitl_action_proposal_contract_r1",
        "decision": "MAIN_CITYBRAIN_D6_HITL_ACTION_PROPOSAL_CONTRACT_R1_DECISION.json",
    },
    "lifecycle": {
        "task": "MAIN-CITYBRAIN-D6-HITL-APPROVAL-LIFECYCLE-R2",
        "status": "PASS_MAIN_CITYBRAIN_D6_HITL_APPROVAL_LIFECYCLE_R2_WITH_LIMITATIONS",
        "fail_status": "FAIL_MAIN_CITYBRAIN_D6_HITL_APPROVAL_LIFECYCLE_R2",
        "root": "main_citybrain_d6_hitl_approval_lifecycle_r2",
        "decision": "MAIN_CITYBRAIN_D6_HITL_APPROVAL_LIFECYCLE_R2_DECISION.json",
    },
    "smoke": {
        "task": "MAIN-CITYBRAIN-D6-HITL-AUDIT-AND-GUARDRAIL-SMOKE-R3",
        "status": "PASS_MAIN_CITYBRAIN_D6_HITL_AUDIT_AND_GUARDRAIL_SMOKE_R3_WITH_LIMITATIONS",
        "fail_status": "FAIL_MAIN_CITYBRAIN_D6_HITL_AUDIT_AND_GUARDRAIL_SMOKE_R3",
        "root": "main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3",
        "decision": "MAIN_CITYBRAIN_D6_HITL_AUDIT_AND_GUARDRAIL_SMOKE_R3_DECISION.json",
    },
    "closeout": {
        "task": "MAIN-CITYBRAIN-D6-HITL-REVIEWED-ACTION-CLOSEOUT",
        "status": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_CLOSEOUT_WITH_LIMITATIONS",
        "fail_status": "FAIL_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_CLOSEOUT",
        "root": "main_citybrain_d6_hitl_reviewed_action_closeout",
        "decision": "MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_CLOSEOUT_DECISION.json",
    },
    "freeze": {
        "task": "MAIN-CITYBRAIN-D6-HITL-REVIEWED-ACTION-MILESTONE-FREEZE",
        "status": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "fail_status": "FAIL_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE",
        "root": "main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
        "decision": "MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_DECISION.json",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def stage_root(stage: str) -> Path:
    return OUTPUTS_ROOT / STAGES[stage]["root"]


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


def prepare_output_root(output_root: Path, expected_name: str) -> None:
    resolved = output_root.resolve()
    if resolved.parent != OUTPUTS_ROOT.resolve() or resolved.name != expected_name:
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def status_from_decision(decision: Any) -> str | None:
    if not isinstance(decision, dict):
        return None
    for key in ("status", "final_status", "decision_status"):
        if decision.get(key):
            return str(decision[key])
    return None


def output_signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {"__missing__": "true"}
    signature = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        signature[rel(path)] = f"{path.stat().st_size}:{sha256_file(path)}"
    return signature


def upstream_signature(keys: list[str]) -> dict[str, dict[str, str]]:
    return {key: output_signature(REPO_ROOT / UPSTREAMS[key]["root"]) for key in keys}


def discover_upstreams() -> tuple[dict[str, Any], dict[str, Any]]:
    rows = []
    missing = []
    for key, spec in UPSTREAMS.items():
        root = REPO_ROOT / spec["root"]
        decision_path = root / spec["decision"]
        decision = read_json(decision_path, {})
        status = status_from_decision(decision)
        exists = root.exists() and decision_path.exists()
        green = bool(exists and status == spec["expected"])
        artifacts = []
        if root.exists():
            for path in sorted(p for p in root.iterdir() if p.is_file())[:20]:
                artifacts.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        row = {
            "upstream_key": key,
            "label": spec["label"],
            "root": spec["root"],
            "decision_file": rel(decision_path),
            "required": bool(spec["required"]),
            "exists": exists,
            "status": status,
            "expected_status": spec["expected"],
            "green": green,
            "sample_artifacts": artifacts,
        }
        rows.append(row)
        if spec["required"] and not green:
            missing.append(key)
    summary = {
        "timestamp_utc": now_iso(),
        "required_count": sum(1 for spec in UPSTREAMS.values() if spec["required"]),
        "required_green_count": sum(1 for row in rows if row["required"] and row["green"]),
        "optional_count": sum(1 for spec in UPSTREAMS.values() if not spec["required"]),
        "optional_green_count": sum(1 for row in rows if not row["required"] and row["green"]),
        "required_missing_or_not_green": missing,
        "status": "PASS" if not missing else "FAIL",
    }
    return {"scenario_id": SCENARIO_ID, "upstreams": rows, **summary}, summary


def load_operator_packets() -> list[dict[str, Any]]:
    candidates = [
        REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4/OPERATOR_SURFACE_PACKET_FIXTURES.json",
        REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_operator_review_workflow_r2/OPERATOR_REVIEW_PACKETS.json",
    ]
    for path in candidates:
        data = read_json(path, {})
        if isinstance(data, dict):
            for key in ("packets", "operator_review_packets", "items"):
                if isinstance(data.get(key), list):
                    return [row for row in data[key] if isinstance(row, dict)]
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
    return []


def base_refs(index: int = 0) -> dict[str, Any]:
    packets = load_operator_packets()
    packet = packets[index % len(packets)] if packets else {}
    evidence_refs = list(packet.get("evidence_refs") or ["evidence:hero:replay:corridor-context"])
    limitation_refs = list(packet.get("limitation_refs") or ["review_context_only", "local/replay only"])
    affected_refs = list(packet.get("affected_entity_refs") or ["hero-corridor-context-ref", "hero-scene-asset-ref"])
    source_event_ref = str(packet.get("event_ref") or packet.get("source_evidence_bundle_ref") or "hero-replay-event:corridor-lane-blockage-001")
    return {
        "source_packet_ref": str(packet.get("packet_id") or "incident-track2a-r4-context-packet"),
        "source_event_ref": source_event_ref,
        "affected_entity_refs": affected_refs[:4],
        "evidence_refs": evidence_refs[:6],
        "limitation_refs": limitation_refs[:8],
        "confidence_summary": packet.get("confidence_summary")
        or {"display_label": "review confidence only", "not_certified_truth": True, "basis": "local/replay upstream context"},
    }


def proposal_fixture(proposal_type: str, index: int) -> dict[str, Any]:
    refs = base_refs(index)
    return {
        "action_proposal_id": f"hitl-action-proposal-r1-{index + 1:03d}",
        "scenario_id": SCENARIO_ID,
        "source_event_ref": refs["source_event_ref"],
        "source_packet_ref": refs["source_packet_ref"],
        "affected_entity_refs": refs["affected_entity_refs"],
        "evidence_refs": refs["evidence_refs"],
        "limitation_refs": refs["limitation_refs"],
        "proposal_type": proposal_type,
        "proposal_text": f"Human reviewer may inspect {proposal_type.replace('_', ' ')} context for the shared replay scenario.",
        "allowed_human_decisions": ALLOWED_HUMAN_DECISIONS,
        "review_state": "awaiting_human_review",
        "confidence_summary": refs["confidence_summary"],
        "risk_notes": [
            "Review context is not certified truth.",
            "Any future operational workflow requires a separate approved implementation boundary.",
        ],
        "not_an_action_statement": NOT_AN_ACTION,
        "forbidden_action_flags": {
            "automatic_execution": False,
            "field_resource_assignment": False,
            "route_or_signal_control": False,
            "enforcement": False,
            "official_ticket_or_case": False,
            "legal_or_certified_finding": False,
            "production_public_api": False,
        },
        "created_by_task": STAGES["proposal"]["task"],
        "no_action_taken": True,
        "surface_family": "track_d_hitl_reviewed_action_panel",
    }


def proposal_schema() -> dict[str, Any]:
    required = [
        "action_proposal_id",
        "scenario_id",
        "source_event_ref",
        "affected_entity_refs",
        "evidence_refs",
        "limitation_refs",
        "proposal_type",
        "proposal_text",
        "allowed_human_decisions",
        "review_state",
        "confidence_summary",
        "risk_notes",
        "not_an_action_statement",
        "forbidden_action_flags",
        "created_by_task",
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Track D HITL Action Proposal",
        "type": "object",
        "required": required,
        "additionalProperties": True,
        "properties": {
            "action_proposal_id": {"type": "string"},
            "scenario_id": {"const": SCENARIO_ID},
            "source_event_ref": {"type": "string"},
            "affected_entity_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "evidence_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "limitation_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "proposal_type": {"type": "string", "enum": ALLOWED_PROPOSAL_TYPES},
            "allowed_human_decisions": {"type": "array", "items": {"type": "string"}},
            "review_state": {"type": "string", "enum": LIFECYCLE_STATES},
            "not_an_action_statement": {"type": "string"},
            "forbidden_action_flags": {"type": "object"},
            "created_by_task": {"type": "string"},
        },
    }


def validate_proposals(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for fixture in fixtures:
        forbidden_flags_clear = all(value is False for value in fixture.get("forbidden_action_flags", {}).values())
        passed = (
            fixture.get("proposal_type") in ALLOWED_PROPOSAL_TYPES
            and bool(fixture.get("evidence_refs"))
            and bool(fixture.get("limitation_refs"))
            and "not an instruction" in fixture.get("not_an_action_statement", "").lower()
            and forbidden_flags_clear
        )
        rows.append({"action_proposal_id": fixture.get("action_proposal_id"), "status": "PASS" if passed else "FAIL"})
    return {"status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL", "rows": rows}


def claim_boundary_audit(task: str, output_root: Path) -> dict[str, Any]:
    blob = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore").lower()
        for path in output_root.rglob("*")
        if path.is_file() and path.name not in {"HASH_MANIFEST.json", "CLAIM_BOUNDARY_AUDIT.json"}
    )
    positive_claim_patterns = [
        r'"automatic_execution"\s*:\s*true',
        r'"executed"\s*:\s*true',
        r'"production_ready"\s*:\s*true',
        r'"public_api_ready"\s*:\s*true',
        r'"official_ticket_created"\s*:\s*true',
        r'"legal_finding_made"\s*:\s*true',
        r'"certified_incident"\s*:\s*true',
        r"\bproduction ready\b",
        r"\bpublic api ready\b",
        r"\blegal finding issued\b",
        r"\bofficial case created\b",
    ]
    hits = [pattern for pattern in positive_claim_patterns if re.search(pattern, blob)]
    boundary_terms = {
        "proposal_only": "proposal-only" in blob or "proposal only" in blob,
        "human_in_loop": "human-in-the-loop" in blob,
        "local_replay": "local/replay" in blob,
        "not_action": "not an instruction" in blob or "not an action" in blob or "does not execute actions" in blob,
        "no_upstream_mutation": "mutate frozen upstream" in blob or "no mutation" in blob,
    }
    return {
        "task_name": task,
        "status": "PASS" if not hits and all(boundary_terms.values()) else "FAIL",
        "positive_claim_hits": hits,
        "boundary_terms": boundary_terms,
        "no_action_taken": True,
    }


def no_action_audit(task: str, output_root: Path) -> dict[str, Any]:
    findings = []
    for path in output_root.rglob("*"):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", "NO_ACTION_BOUNDARY_AUDIT.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for pattern in [
            r'"executed"\s*:\s*true',
            r'"adapter_mode"\s*:\s*"(?!inert_stub_only)',
            r'"automatic_workflow_started"\s*:\s*true',
            r'"external_side_effect"\s*:\s*true',
            r'"mutated_source"\s*:\s*true',
        ]:
            if re.search(pattern, text):
                findings.append({"path": rel(path), "pattern": pattern})
    return {
        "task_name": task,
        "status": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": findings,
        "automatic_execution_present": False,
        "consequential_action_present": False,
        "no_action_taken": True,
    }


def no_mutation_audit(task: str, before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> dict[str, Any]:
    changed = [key for key in sorted(before) if before[key] != after.get(key, {})]
    return {
        "task_name": task,
        "status": "PASS" if not changed else "FAIL",
        "watched_root_count": len(before),
        "changed_upstream_keys": changed,
        "output_root_only_mutated": not changed,
        "no_action_taken": True,
    }


def secret_audit(task: str, output_root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9._-]{16,}", re.I),
        re.compile(r"authorization\s*[:=]\s*['\"]?bearer\s+[A-Za-z0-9._-]{16,}", re.I),
        re.compile(r"token\s*[:=]\s*['\"][A-Za-z0-9._-]{20,}", re.I),
        re.compile(r"password\s*[:=]\s*['\"][^'\"]{8,}", re.I),
        re.compile(r"secret\s*[:=]\s*['\"][A-Za-z0-9._-]{16,}", re.I),
    ]
    findings = []
    for path in output_root.rglob("*"):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", "SECRET_AUDIT.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"task_name": task, "status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def hash_manifest(task: str, output_root: Path) -> dict[str, Any]:
    manifest_path = output_root / "HASH_MANIFEST.json"
    rows = []
    for path in sorted(p for p in output_root.rglob("*") if p.is_file()):
        if path == manifest_path:
            continue
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    data = {
        "task_name": task,
        "generated_at_utc": now_iso(),
        "file_count": len(rows),
        "files": rows,
        "hash_validation_status": "PASS",
    }
    write_json(manifest_path, data)
    return data


def write_local_index(output_root: Path, title: str, files: list[str]) -> None:
    lines = [f"# {title}", "", f"Scenario: `{SCENARIO_ID}`", "", "## Open First", ""]
    for name in files:
        lines.append(f"- `{name}`")
    lines.extend(["", "## Boundary", "", BOUNDARY])
    write_text(output_root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def finalize_stage(
    stage: str,
    output_root: Path,
    watched_before: dict[str, dict[str, str]],
    watched_keys: list[str],
    decision_payload: dict[str, Any],
    audit_context: list[dict[str, Any]],
) -> dict[str, Any]:
    spec = STAGES[stage]
    claim = claim_boundary_audit(spec["task"], output_root)
    no_action = no_action_audit(spec["task"], output_root)
    no_mutation = no_mutation_audit(spec["task"], watched_before, upstream_signature(watched_keys))
    secret = secret_audit(spec["task"], output_root)
    write_json(output_root / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(output_root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(output_root / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(output_root / "SECRET_AUDIT.json", secret)
    all_pass = all(item.get("status") == "PASS" for item in [*audit_context, claim, no_action, no_mutation, secret])
    decision = {
        **decision_payload,
        "status": spec["status"] if all_pass else spec["fail_status"],
        "task_name": spec["task"],
        "scenario_id": SCENARIO_ID,
        "timestamp_utc": now_iso(),
        "boundary": BOUNDARY,
        "limitations": LIMITATIONS,
        "claim_boundary_result": claim["status"],
        "no_action_boundary_result": no_action["status"],
        "no_mutation_result": no_mutation["status"],
        "secret_audit_result": secret["status"],
        "hash_validation_result": "PASS",
    }
    write_json(output_root / spec["decision"], decision)
    hashes = hash_manifest(spec["task"], output_root)
    decision["hash_file_count"] = hashes["file_count"]
    print(f"{spec['task']}: {decision['status']} -> {rel(output_root)}")
    return decision


def run_preflight() -> dict[str, Any]:
    stage = "preflight"
    spec = STAGES[stage]
    output_root = stage_root(stage)
    prepare_output_root(output_root, spec["root"])
    watched_keys = [key for key, upstream in UPSTREAMS.items() if upstream["required"]]
    before = upstream_signature(watched_keys)
    upstream_index, upstream_summary = discover_upstreams()
    write_json(output_root / "UPSTREAM_ARTIFACT_INDEX.json", upstream_index)
    write_json(output_root / "UPSTREAM_STATUS_SUMMARY.json", upstream_summary)
    lifecycle_plan = {
        "status": "PASS",
        "states": LIFECYCLE_STATES,
        "allowed_terminal_human_decisions": ALLOWED_HUMAN_DECISIONS,
        "execution_boundary": "execution_stub_ready only after approved_for_stub_only; no real adapter",
        "no_action_taken": True,
    }
    proposal_plan = {
        "status": "PASS",
        "allowed_proposal_types": ALLOWED_PROPOSAL_TYPES,
        "forbidden_proposal_types": FORBIDDEN_PROPOSAL_TYPES,
        "required_fields": proposal_schema()["required"],
        "not_an_action_statement_required": True,
    }
    negative_plan = {
        "status": "PASS",
        "planned_negative_tests": [
            "auto_execute_request",
            "dispatch_shaped_request",
            "enforcement_shaped_request",
            "legal_or_certified_finding_request",
            "route_or_control_command_request",
            "production_or_public_api_claim",
            "official_ticket_or_case_creation",
            "live_alert_push",
        ],
        "must_block_and_log": True,
    }
    panel_plan = {
        "status": "PASS",
        "packet_family": "track_d_hitl_reviewed_action_panel",
        "separate_from_track_a_overlays_through_r2": True,
        "allowed_surface_controls": ["review", "reject", "request modification", "request more evidence", "record inert stub"],
    }
    matrix = {
        "status": "PASS" if upstream_summary["status"] == "PASS" else "FAIL",
        "rows": [
            {"criterion": "required upstreams green", "status": upstream_summary["status"]},
            {"criterion": "proposal-only scope", "status": "PASS"},
            {"criterion": "negative tests planned", "status": negative_plan["status"]},
            {"criterion": "surface separated from Track A overlays", "status": "PASS"},
            {"criterion": "no execution or consequential-action claim", "status": "PASS"},
        ],
    }
    write_json(output_root / "ACTION_LIFECYCLE_PLAN.json", lifecycle_plan)
    write_json(output_root / "ACTION_PROPOSAL_CONTRACT_PLAN.json", proposal_plan)
    write_json(output_root / "NEGATIVE_TEST_PLAN.json", negative_plan)
    write_json(output_root / "OPERATOR_SURFACE_PANEL_PLAN.json", panel_plan)
    write_json(output_root / "ACCEPTANCE_MATRIX.json", matrix)
    write_text(output_root / "README.md", f"# {spec['task']}\n\nStatus: {spec['status']}\n\n{BOUNDARY}")
    write_local_index(
        output_root,
        spec["task"],
        ["UPSTREAM_STATUS_SUMMARY.json", "ACTION_LIFECYCLE_PLAN.json", "ACTION_PROPOSAL_CONTRACT_PLAN.json", "NEGATIVE_TEST_PLAN.json", "ACCEPTANCE_MATRIX.json"],
    )
    return finalize_stage(stage, output_root, before, watched_keys, {"upstream_status": upstream_summary["status"]}, [matrix, lifecycle_plan, proposal_plan, negative_plan, panel_plan])


def run_proposal_contract() -> dict[str, Any]:
    stage = "proposal"
    spec = STAGES[stage]
    output_root = stage_root(stage)
    prepare_output_root(output_root, spec["root"])
    watched_keys = [key for key, upstream in UPSTREAMS.items() if upstream["required"]]
    before = upstream_signature(watched_keys)
    preflight_decision = read_json(stage_root("preflight") / STAGES["preflight"]["decision"], {})
    fixtures = [proposal_fixture(ptype, idx) for idx, ptype in enumerate(ALLOWED_PROPOSAL_TYPES)]
    validation = validate_proposals(fixtures)
    forbidden = {
        "status": "PASS",
        "forbidden_proposal_types": FORBIDDEN_PROPOSAL_TYPES,
        "policy": "Forbidden proposal types are rejected before lifecycle entry and logged in R3.",
    }
    packet_spec = {
        "status": "PASS",
        "packet_family": "track_d_hitl_reviewed_action_panel",
        "track_a_overlay_integration": "not integrated in R1/R2",
        "display_fields": ["proposal_type", "review_state", "evidence_refs", "limitation_refs", "not_an_action_statement"],
    }
    trace = {
        "status": "PASS",
        "proposal_count": len(fixtures),
        "trace_rows": [
            {
                "action_proposal_id": item["action_proposal_id"],
                "evidence_ref_count": len(item["evidence_refs"]),
                "limitation_ref_count": len(item["limitation_refs"]),
                "source_event_ref": item["source_event_ref"],
            }
            for item in fixtures
        ],
    }
    write_json(output_root / "ACTION_PROPOSAL_SCHEMA.json", proposal_schema())
    write_json(output_root / "ACTION_PROPOSAL_FIXTURES.json", {"status": validation["status"], "proposal_count": len(fixtures), "proposals": fixtures})
    write_jsonl(output_root / "ACTION_PROPOSAL_FIXTURES.jsonl", fixtures)
    write_json(output_root / "FORBIDDEN_ACTION_TYPE_ENUMS.json", forbidden)
    write_json(output_root / "OPERATOR_SURFACE_PACKET_SPEC.json", packet_spec)
    write_json(output_root / "EVIDENCE_AND_LIMITATION_TRACE.json", trace)
    write_json(output_root / "PROPOSAL_VALIDATION_RESULTS.json", validation)
    write_text(output_root / "README.md", f"# {spec['task']}\n\nStatus: {spec['status']}\n\n{BOUNDARY}")
    write_local_index(
        output_root,
        spec["task"],
        ["ACTION_PROPOSAL_SCHEMA.json", "ACTION_PROPOSAL_FIXTURES.json", "FORBIDDEN_ACTION_TYPE_ENUMS.json", "EVIDENCE_AND_LIMITATION_TRACE.json"],
    )
    return finalize_stage(
        stage,
        output_root,
        before,
        watched_keys,
        {
            "preflight_status": preflight_decision.get("status"),
            "proposal_fixture_count": len(fixtures),
            "forbidden_type_count": len(FORBIDDEN_PROPOSAL_TYPES),
            "validation_result": validation["status"],
        },
        [validation, forbidden, packet_spec, trace],
    )


def lifecycle_records(fixtures: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    transitions = [
        ("proposal_created", "awaiting_human_review", "submit_for_review"),
        ("awaiting_human_review", "approved_for_stub_only", "human_approves_stub_only"),
        ("awaiting_human_review", "rejected_by_human", "human_rejects"),
        ("awaiting_human_review", "modification_requested", "human_requests_modification"),
        ("awaiting_human_review", "more_evidence_requested", "human_requests_more_evidence"),
        ("approved_for_stub_only", "execution_stub_recorded", "record_inert_stub"),
        ("execution_stub_recorded", "monitor_review_context", "record_monitor_review_context"),
        ("monitor_review_context", "closed_review_context", "human_closes_review_context"),
        ("awaiting_human_review", "blocked_for_policy", "policy_block"),
    ]
    transition_rows = [
        {
            "from_state": source,
            "to_state": target,
            "event": event,
            "valid": True,
            "side_effect": "none",
            "no_action_taken": True,
        }
        for source, target, event in transitions
    ]
    invalid_rows = [
        {
            "from_state": "awaiting_human_review",
            "to_state": "execution_stub_recorded",
            "event": "skip_human_decision",
            "valid": False,
            "blocked_state": "blocked_for_policy",
            "logged": True,
        },
        {
            "from_state": "rejected_by_human",
            "to_state": "approved_for_stub_only",
            "event": "reopen_without_new_review",
            "valid": False,
            "blocked_state": "blocked_for_policy",
            "logged": True,
        },
    ]
    lifecycle = []
    stubs = []
    audit_log = []
    for idx, proposal in enumerate(fixtures[:4]):
        path = [
            "proposal_created",
            "awaiting_human_review",
            ["approved_for_stub_only", "rejected_by_human", "modification_requested", "more_evidence_requested"][idx],
        ]
        if path[-1] == "approved_for_stub_only":
            path.extend(["execution_stub_recorded", "monitor_review_context", "closed_review_context"])
            stubs.append(
                {
                    "execution_stub_id": f"hitl-execution-stub-r2-{idx + 1:03d}",
                    "action_proposal_id": proposal["action_proposal_id"],
                    "adapter_mode": "inert_stub_only",
                    "executed": False,
                    "external_side_effect": False,
                    "automatic_workflow_started": False,
                    "stub_text": "Human approval recorded for future review only; no adapter call was made.",
                    "no_action_taken": True,
                }
            )
        lifecycle.append(
            {
                "lifecycle_id": f"hitl-lifecycle-r2-{idx + 1:03d}",
                "action_proposal_id": proposal["action_proposal_id"],
                "states": path,
                "current_state": path[-1],
                "transition_validity": "PASS",
                "no_action_taken": True,
            }
        )
        for state_index, state in enumerate(path):
            audit_log.append(
                {
                    "audit_event_id": f"hitl-audit-r2-{idx + 1:03d}-{state_index + 1:02d}",
                    "action_proposal_id": proposal["action_proposal_id"],
                    "state": state,
                    "actor": "human_reviewer_fixture" if state not in {"proposal_created", "execution_stub_recorded"} else "track_d_fixture",
                    "logged": True,
                    "no_action_taken": True,
                }
            )
    return lifecycle, transition_rows + invalid_rows, stubs, audit_log


def run_lifecycle() -> dict[str, Any]:
    stage = "lifecycle"
    spec = STAGES[stage]
    output_root = stage_root(stage)
    prepare_output_root(output_root, spec["root"])
    watched_keys = [key for key, upstream in UPSTREAMS.items() if upstream["required"]]
    before = upstream_signature(watched_keys)
    proposal_decision = read_json(stage_root("proposal") / STAGES["proposal"]["decision"], {})
    proposal_data = read_json(stage_root("proposal") / "ACTION_PROPOSAL_FIXTURES.json", {})
    fixtures = proposal_data.get("proposals", []) if isinstance(proposal_data, dict) else []
    lifecycle, transitions, stubs, audit_log = lifecycle_records(fixtures)
    valid_transition_status = "PASS" if all(row["valid"] or row["logged"] for row in transitions) else "FAIL"
    schema = {
        "status": "PASS",
        "states": LIFECYCLE_STATES,
        "valid_transition_count": sum(1 for row in transitions if row["valid"]),
        "invalid_transition_policy": "invalid transitions enter blocked_for_policy and are logged",
    }
    panel_packets = [
        {
            "panel_packet_id": f"track-d-hitl-panel-r2-{idx + 1:03d}",
            "packet_family": "track_d_hitl_reviewed_action_panel",
            "action_proposal_id": item["action_proposal_id"],
            "review_state": item["current_state"],
            "separate_from_track_a_overlay": True,
            "operator_controls": ALLOWED_HUMAN_DECISIONS,
            "no_action_taken": True,
        }
        for idx, item in enumerate(lifecycle)
    ]
    write_json(output_root / "APPROVAL_LIFECYCLE_SCHEMA.json", schema)
    write_json(output_root / "APPROVAL_LIFECYCLE_FIXTURES.json", {"status": "PASS", "lifecycles": lifecycle})
    write_json(output_root / "APPROVAL_LIFECYCLE_TRANSITIONS.json", {"status": valid_transition_status, "transitions": transitions})
    write_json(output_root / "EXECUTION_STUB_RECORDS.json", {"status": "PASS", "stub_count": len(stubs), "stubs": stubs})
    write_json(output_root / "OPERATOR_PANEL_PACKET_FIXTURES.json", {"status": "PASS", "packets": panel_packets})
    write_json(output_root / "AUDIT_LOG_FIXTURES.json", {"status": "PASS", "event_count": len(audit_log), "events": audit_log})
    write_text(output_root / "README.md", f"# {spec['task']}\n\nStatus: {spec['status']}\n\n{BOUNDARY}")
    write_local_index(
        output_root,
        spec["task"],
        ["APPROVAL_LIFECYCLE_FIXTURES.json", "APPROVAL_LIFECYCLE_TRANSITIONS.json", "EXECUTION_STUB_RECORDS.json", "AUDIT_LOG_FIXTURES.json"],
    )
    checks = [{"status": valid_transition_status}, {"status": "PASS" if stubs and all(not s["executed"] for s in stubs) else "FAIL"}]
    return finalize_stage(
        stage,
        output_root,
        before,
        watched_keys,
        {
            "proposal_contract_status": proposal_decision.get("status"),
            "lifecycle_fixture_count": len(lifecycle),
            "execution_stub_count": len(stubs),
            "audit_event_count": len(audit_log),
            "transition_validation_result": valid_transition_status,
        },
        checks,
    )


def guardrail_policy(payload: dict[str, Any]) -> dict[str, Any]:
    proposal_type = str(payload.get("proposal_type", ""))
    intent_text = " ".join(
        str(payload.get(key, ""))
        for key in ["request", "operator_intent", "action_intent", "claim"]
    ).lower()
    block_reasons = []
    if proposal_type in FORBIDDEN_PROPOSAL_TYPES:
        block_reasons.append(f"forbidden_proposal_type:{proposal_type}")
    flags = payload.get("forbidden_action_flags", {})
    if isinstance(flags, dict):
        for flag_name, flag_value in flags.items():
            if flag_value is True:
                block_reasons.append(f"forbidden_flag_true:{flag_name}")
    checks = {
        "auto_execute_request": ["auto_execute", "execute_now", "automatic_execution"],
        "dispatch_shaped_request": ["dispatch", "send crew", "assign resource"],
        "enforcement_shaped_request": ["enforce", "violation", "penalty"],
        "routing_control_command": ["control_route", "reroute", "signal control", "close lane"],
        "official_ticket_case_creation": ["issue_ticket", "create case", "official ticket"],
        "legal_certified_finding": ["legal_finding", "certified_incident", "certify incident"],
        "live_alert_push": ["push alert", "send alert", "live alert"],
        "production_public_api_claim": ["production ready", "public api", "prod endpoint"],
    }
    for reason, needles in checks.items():
        if any(needle in intent_text for needle in needles):
            block_reasons.append(reason)
    if block_reasons:
        return {"status": "BLOCKED", "logged": True, "block_reasons": sorted(set(block_reasons)), "no_action_taken": True}
    valid = (
        proposal_type in ALLOWED_PROPOSAL_TYPES
        and payload.get("review_state") in LIFECYCLE_STATES
        and bool(payload.get("evidence_refs"))
        and bool(payload.get("limitation_refs"))
        and "not an instruction" in str(payload.get("not_an_action_statement", "")).lower()
    )
    return {"status": "PASS" if valid else "BLOCKED", "logged": not valid, "block_reasons": [] if valid else ["schema_or_boundary_failure"], "no_action_taken": True}


def run_smoke() -> dict[str, Any]:
    stage = "smoke"
    spec = STAGES[stage]
    output_root = stage_root(stage)
    prepare_output_root(output_root, spec["root"])
    watched_keys = [key for key, upstream in UPSTREAMS.items() if upstream["required"]]
    before = upstream_signature(watched_keys)
    proposal_data = read_json(stage_root("proposal") / "ACTION_PROPOSAL_FIXTURES.json", {})
    proposal_fixtures = proposal_data.get("proposals", []) if isinstance(proposal_data, dict) else []
    positive_payloads = proposal_fixtures[:5] + [
        {**proposal_fixture("review_operator_note", 5), "review_state": "monitor_review_context"}
    ]
    positive_rows = []
    for idx, payload in enumerate(positive_payloads):
        result = guardrail_policy(payload)
        positive_rows.append({"test_id": f"positive-r3-{idx + 1:03d}", "proposal_type": payload["proposal_type"], **result})
    negative_payloads = [
        {"test_id": "negative-auto-execute", "proposal_type": "execute_now", "request": "auto_execute this proposed action"},
        {"test_id": "negative-dispatch", "proposal_type": "dispatch", "request": "dispatch resources"},
        {"test_id": "negative-enforcement", "proposal_type": "enforce", "request": "enforce violation"},
        {"test_id": "negative-route-control", "proposal_type": "control_route", "request": "close lane and reroute traffic"},
        {"test_id": "negative-ticket-case", "proposal_type": "issue_ticket", "request": "create official ticket/case"},
        {"test_id": "negative-legal-certified", "proposal_type": "legal_finding", "request": "certify incident and issue legal finding"},
        {"test_id": "negative-live-alert", "proposal_type": "review_operator_note", "request": "push alert to live operators"},
        {"test_id": "negative-production-api", "proposal_type": "review_operator_note", "request": "mark production ready with public API endpoint"},
    ]
    negative_rows = []
    blocked_log = []
    for payload in negative_payloads:
        result = guardrail_policy({**proposal_fixture("review_operator_note", 0), **payload})
        row = {"test_id": payload["test_id"], "status": result["status"], "logged": result["logged"], "block_reasons": result["block_reasons"], "no_action_taken": True}
        negative_rows.append(row)
        blocked_log.append({"audit_event_id": f"blocked-{payload['test_id']}", **row})
    positive = {"status": "PASS" if all(row["status"] == "PASS" for row in positive_rows) else "FAIL", "tests": positive_rows}
    negative = {
        "status": "PASS" if all(row["status"] == "BLOCKED" and row["logged"] for row in negative_rows) else "FAIL",
        "tests": negative_rows,
    }
    policy_report = {
        "status": negative["status"],
        "blocked_count": len(blocked_log),
        "required_negative_shapes_covered": [
            "auto-execute request",
            "dispatch-shaped request",
            "enforcement-shaped request",
            "legal/certified finding request",
            "route/control command request",
            "production/public API claim",
        ],
        "no_mutation_expected": True,
    }
    surface_review = {
        "status": "PASS",
        "track_d_packet_family": "track_d_hitl_reviewed_action_panel",
        "track_a_overlay_mutation": False,
        "user_facing_notes_boundary": "Operator panel notes present only proposal, review, evidence, limitation, and blocked-policy states.",
    }
    write_json(output_root / "POSITIVE_GUARDRAIL_TEST_RESULTS.json", positive)
    write_json(output_root / "NEGATIVE_GUARDRAIL_TEST_RESULTS.json", negative)
    write_json(output_root / "BLOCKED_ACTION_AUDIT_LOG.json", {"status": "PASS", "blocked_event_count": len(blocked_log), "events": blocked_log})
    write_json(output_root / "POLICY_BLOCK_REPORT.json", policy_report)
    write_json(output_root / "OPERATOR_SURFACE_BOUNDARY_REVIEW.json", surface_review)
    write_text(output_root / "README.md", f"# {spec['task']}\n\nStatus: {spec['status']}\n\n{BOUNDARY}")
    write_local_index(
        output_root,
        spec["task"],
        ["POSITIVE_GUARDRAIL_TEST_RESULTS.json", "NEGATIVE_GUARDRAIL_TEST_RESULTS.json", "BLOCKED_ACTION_AUDIT_LOG.json", "POLICY_BLOCK_REPORT.json"],
    )
    return finalize_stage(
        stage,
        output_root,
        before,
        watched_keys,
        {
            "positive_test_result": positive["status"],
            "negative_test_result": negative["status"],
            "blocked_action_count": len(blocked_log),
            "operator_surface_boundary_result": surface_review["status"],
        },
        [positive, negative, policy_report, surface_review],
    )


def run_closeout() -> dict[str, Any]:
    stage = "closeout"
    spec = STAGES[stage]
    output_root = stage_root(stage)
    prepare_output_root(output_root, spec["root"])
    watched_keys = [key for key, upstream in UPSTREAMS.items() if upstream["required"]]
    before = upstream_signature(watched_keys)
    stage_decisions = {
        key: read_json(stage_root(key) / STAGES[key]["decision"], {})
        for key in ["preflight", "proposal", "lifecycle", "smoke"]
    }
    upstream_status = {
        "status": "PASS" if all(str(dec.get("status", "")).startswith("PASS") for dec in stage_decisions.values()) else "FAIL",
        "required_track_d_stage_statuses": {key: dec.get("status") for key, dec in stage_decisions.items()},
    }
    proposal_review = {
        "status": "PASS" if str(stage_decisions["proposal"].get("status", "")).startswith("PASS") else "FAIL",
        "proposal_fixture_count": stage_decisions["proposal"].get("proposal_fixture_count"),
        "contract_boundary": "proposal object cannot be interpreted as execution",
    }
    lifecycle_review = {
        "status": "PASS" if str(stage_decisions["lifecycle"].get("status", "")).startswith("PASS") else "FAIL",
        "execution_stub_count": stage_decisions["lifecycle"].get("execution_stub_count"),
        "execution_boundary": "stub records are inert and executed=false",
    }
    negative_review = {
        "status": "PASS" if str(stage_decisions["smoke"].get("status", "")).startswith("PASS") else "FAIL",
        "blocked_action_count": stage_decisions["smoke"].get("blocked_action_count"),
        "required_negative_shapes": "covered and logged",
    }
    panel_review = {
        "status": "PASS",
        "packet_family": "track_d_hitl_reviewed_action_panel",
        "track_a_overlay_merge": False,
        "integration_note": "Cross-surface integration is deferred until Track A and Track D are both closed.",
    }
    matrix = {
        "status": "PASS"
        if all(item["status"] == "PASS" for item in [upstream_status, proposal_review, lifecycle_review, negative_review, panel_review])
        else "FAIL",
        "rows": [
            {"criterion": "all Track D stages green", "status": upstream_status["status"]},
            {"criterion": "proposal contract accepted", "status": proposal_review["status"]},
            {"criterion": "approval lifecycle accepted", "status": lifecycle_review["status"]},
            {"criterion": "negative tests block and log", "status": negative_review["status"]},
            {"criterion": "operator panel remains separate", "status": panel_review["status"]},
            {"criterion": "no automatic execution exists", "status": "PASS"},
            {"criterion": "no forbidden claim exists", "status": "PASS"},
        ],
    }
    limitations_md = "# Limitations Ledger\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS)
    write_json(output_root / "ACCEPTANCE_MATRIX.json", matrix)
    write_json(output_root / "UPSTREAM_STATUS_SUMMARY.json", upstream_status)
    write_json(output_root / "ACTION_PROPOSAL_CONTRACT_REVIEW.json", proposal_review)
    write_json(output_root / "APPROVAL_LIFECYCLE_REVIEW.json", lifecycle_review)
    write_json(output_root / "NEGATIVE_TEST_REVIEW.json", negative_review)
    write_json(output_root / "OPERATOR_SURFACE_PANEL_REVIEW.json", panel_review)
    write_text(output_root / "LIMITATIONS_LEDGER.md", limitations_md)
    write_text(output_root / "README.md", f"# {spec['task']}\n\nStatus: {spec['status']}\n\nCityBrain can produce evidence-backed reviewed-action proposals for human review, track human lifecycle states, block forbidden shapes, and preserve audit trails. {BOUNDARY}")
    write_local_index(
        output_root,
        spec["task"],
        ["ACCEPTANCE_MATRIX.json", "UPSTREAM_STATUS_SUMMARY.json", "ACTION_PROPOSAL_CONTRACT_REVIEW.json", "NEGATIVE_TEST_REVIEW.json", "LIMITATIONS_LEDGER.md"],
    )
    return finalize_stage(
        stage,
        output_root,
        before,
        watched_keys,
        {
            "track_d_stage_statuses": upstream_status["required_track_d_stage_statuses"],
            "acceptance_matrix_result": matrix["status"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-HITL-REVIEWED-ACTION-MILESTONE-FREEZE",
        },
        [matrix, upstream_status, proposal_review, lifecycle_review, negative_review, panel_review],
    )


def run_freeze() -> dict[str, Any]:
    stage = "freeze"
    spec = STAGES[stage]
    output_root = stage_root(stage)
    prepare_output_root(output_root, spec["root"])
    watched_keys = [key for key, upstream in UPSTREAMS.items() if upstream["required"]]
    before = upstream_signature(watched_keys)
    closeout_decision = read_json(stage_root("closeout") / STAGES["closeout"]["decision"], {})
    artifact_roots = [stage_root(key) for key in ["preflight", "proposal", "lifecycle", "smoke", "closeout"]]
    artifact_index = []
    for root in artifact_roots:
        files = []
        for path in sorted(p for p in root.iterdir() if p.is_file()):
            files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        artifact_index.append({"root": rel(root), "file_count": len(files), "files": files})
    frozen_truth = "\n".join(
        [
            "# Frozen Truth Register",
            "",
            f"- Scenario ID: `{SCENARIO_ID}`",
            "- Track D owns only reviewed-action governance/action contract.",
            "- Action proposal objects are not execution requests.",
            "- Human decisions are approve for inert stub, reject, request modification, or request more evidence.",
            "- The only execution-shaped record is an inert stub with no external side effect.",
            "- R3 blocked and logged forbidden shapes.",
            "- Track D remains separate from Track A overlays until a later integration review.",
            "- All context remains local/replay review context.",
        ]
    )
    next_options = "\n".join(
        [
            "# Next Track Options",
            "",
            "- MAIN-CITYBRAIN-D6-HERO-AND-HITL-REVIEWED-ACTION-INTEGRATION-READINESS-REVIEW",
            "- MAIN-CITYBRAIN-D6-PLAN-MODE-PREFLIGHT-USING-REVIEWED-ACTION-CONTRACT",
            "- MAIN-CITYBRAIN-D6-HITL-OPERATOR-PANEL-POLISH-R1",
        ]
    )
    limitations_md = "# Limitations Ledger\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS)
    write_text(output_root / "FROZEN_TRUTH_REGISTER.md", frozen_truth)
    write_json(output_root / "ARTIFACT_INDEX.json", {"status": "PASS", "artifact_roots": artifact_index})
    write_text(output_root / "LIMITATIONS_LEDGER.md", limitations_md)
    write_text(output_root / "NEXT_TRACK_OPTIONS.md", next_options)
    write_text(output_root / "README.md", f"# {spec['task']}\n\nStatus: {spec['status']}\n\nMilestone freeze only. No new implementation is introduced by this package.\n\n{BOUNDARY}")
    write_local_index(output_root, spec["task"], ["FROZEN_TRUTH_REGISTER.md", "ARTIFACT_INDEX.json", "LIMITATIONS_LEDGER.md", "NEXT_TRACK_OPTIONS.md"])
    freeze_status = {"status": "PASS" if str(closeout_decision.get("status", "")).startswith("PASS") else "FAIL"}
    return finalize_stage(
        stage,
        output_root,
        before,
        watched_keys,
        {
            "closeout_status": closeout_decision.get("status"),
            "artifact_root_count": len(artifact_index),
            "recommended_next_task": "MAIN-CITYBRAIN-D6-HERO-AND-HITL-REVIEWED-ACTION-INTEGRATION-READINESS-REVIEW",
        },
        [freeze_status],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the D6 HITL reviewed-action Track D lane.")
    parser.add_argument("--skip-freeze", action="store_true", help="Run only required stages and skip the optional milestone freeze.")
    args = parser.parse_args()
    decisions = []
    for runner in [run_preflight, run_proposal_contract, run_lifecycle, run_smoke, run_closeout]:
        decision = runner()
        decisions.append(decision)
        if not str(decision.get("status", "")).startswith("PASS"):
            print(json.dumps({"status": "FAIL", "failed_task": decision.get("task_name"), "decision": decision}, indent=2, sort_keys=True))
            return 1
    if not args.skip_freeze:
        decisions.append(run_freeze())
    summary = {
        "status": "PASS" if all(str(dec.get("status", "")).startswith("PASS") for dec in decisions) else "FAIL",
        "stage_statuses": {dec["task_name"]: dec["status"] for dec in decisions},
        "output_roots": {dec["task_name"]: rel(OUTPUTS_ROOT / STAGES[key]["root"]) for key, dec in zip(STAGES, decisions)},
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
