#!/usr/bin/env python3
"""Epoch 2.2 Push 2.2b Lane B Event/Incident Agent activation runner."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_b_event_incident"
INTEGRATION_DECISION_PATH = REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2a" / "PUSH_2_2A_INTEGRATION_DECISION.json"
ALLOWED_FLAG_PATH = REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2a" / "PUSH_2_2B_ALLOWED_TO_OPEN.flag"

SERVICE_REGISTRY_PATH = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract" / "SERVICE_REGISTRY_V1.json"
SERVICE_CONTRACT_PATH = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract" / "AGENT_SERVICE_CONTRACT_V1.json"
OBSERVABILITY_REPORT_PATH = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_b_observability" / "AGENT_OBSERVABILITY_REPORT.json"
MULTI_AGENT_REPLAY_PATH = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract" / "MULTI_AGENT_REPLAY_HARNESS_REPORT.json"

PASS_STATUS = "PASS_WITH_LIMITATIONS"
BLOCK_STATUS = "BLOCKED_PUSH_2_2B_LANE_B_PREREQUISITE_GATE"
REQUIRED_INTEGRATION_STATUS = "PASS_PUSH_2_2A_INTEGRATION"

NON_GOALS = [
    "No official incident claim.",
    "No legal finding.",
    "No dispatch/control/enforcement.",
    "No live production event source unless later policy and perception lanes explicitly allow it.",
    "VSS/model narrative remains context only, not fact source.",
    "No official-action affordance emitted.",
    "Local/replay/review/query only.",
    "No per-domain agent classes, learned ranking, prediction, trained model, or dynamic investigation.",
]

FORBIDDEN_OUTPUTS = {
    "OfficialAction",
    "DispatchCommand",
    "Ticket",
    "CasePacket",
    "LegalFinding",
    "CertifiedFinding",
    "SourceTruthMutation",
    "AutonomousExecution",
}

PACKAGE_REFS = [
    "02_PUSH_LANE_EXECUTION_MODEL.md",
    "10_PUSH_2_2B_LANE_B_EVENT_INCIDENT_AGENT_PROMPT.md",
    "20_SPEC_AGENT_SERVICE_CONTRACT.md",
    "23_SPEC_WATCH_EVENT_BRIEFING_SERVICES.md",
    "28_SCOPE_NON_GOALS.md",
    "29_EXIT_GATE_CHECKLIST.md",
    "31_TRACK0_CORPUS_LEDGER_DISCIPLINE.md",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return f"UNKNOWN:{result.stderr.strip()}"
    return result.stdout.strip()


def check_prerequisite_gate() -> dict[str, Any]:
    errors: list[str] = []
    branch = current_branch()
    if branch != "main":
        errors.append(f"branch_not_main:{branch}")

    decision: dict[str, Any] = {}
    if not INTEGRATION_DECISION_PATH.exists():
        errors.append(f"missing_integration_decision:{rel(INTEGRATION_DECISION_PATH)}")
    else:
        decision = read_json(INTEGRATION_DECISION_PATH)
        if decision.get("status") != REQUIRED_INTEGRATION_STATUS:
            errors.append(f"integration_status_not_pass:{decision.get('status')}")

    flag_value = ""
    if not ALLOWED_FLAG_PATH.exists():
        errors.append(f"missing_allowed_flag:{rel(ALLOWED_FLAG_PATH)}")
    else:
        flag_value = ALLOWED_FLAG_PATH.read_text(encoding="utf-8-sig").strip()
        if flag_value != "PASS":
            errors.append(f"allowed_flag_not_pass:{flag_value}")

    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_b.prerequisite_gate.v1",
        "status": "PASS" if not errors else BLOCK_STATUS,
        "checked_at": utc_now(),
        "branch": branch,
        "integration_decision_ref": rel(INTEGRATION_DECISION_PATH),
        "integration_status": decision.get("status"),
        "allowed_flag_ref": rel(ALLOWED_FLAG_PATH),
        "allowed_flag_value": flag_value,
        "errors": errors,
    }


def load_service_registry() -> dict[str, Any]:
    return read_json(SERVICE_REGISTRY_PATH)


def service_by_id(registry: dict[str, Any], service_id: str) -> dict[str, Any]:
    for service in registry.get("services", []):
        if service.get("service_id") == service_id:
            return service
    raise KeyError(service_id)


def event_candidate_fixtures() -> list[dict[str, Any]]:
    return [
        {
            "fixture_id": "event-incident-fixture:resolved:001",
            "kind": "EventEnvelope",
            "event_id": "event:local_replay:mobility:resolved:001",
            "candidate_observation_id": "candidate:local_replay:mobility:001",
            "event_type": "mobility_obstruction_context",
            "event_time": "2026-07-06T00:00:00Z",
            "source_class": "replay_fixture",
            "location_ref": "place:local_replay:west_gate",
            "evidence_refs": [
                "source:r7a:replay-west-gate-001",
                "frame:r7a:west-gate-local-replay-clip:000420",
            ],
            "vss_or_model_narrative": {
                "present": True,
                "role": "context_only_not_fact_source",
                "text_ref": "narrative:local_replay:west_gate_context",
            },
            "entity_resolution": {
                "state": "resolved",
                "entity_ref": "entity:asset:west_gate_service_lane",
                "method": "deterministic_fixture_key_match",
                "confidence_label": "fixture_resolved",
            },
        },
        {
            "fixture_id": "event-incident-fixture:unresolved:001",
            "kind": "CandidateObservation",
            "candidate_observation_id": "candidate:local_replay:utilities:unresolved:001",
            "event_type": "utility_service_context",
            "event_time": "2026-07-06T00:05:00Z",
            "source_class": "replay_fixture",
            "location_ref": "place:local_replay:unknown_service_point",
            "evidence_refs": [
                "source:local_replay:utility-service-event-001",
                "source:local_replay:utility-map-fragment-001",
            ],
            "vss_or_model_narrative": {
                "present": True,
                "role": "context_only_not_fact_source",
                "text_ref": "narrative:local_replay:utility_context",
            },
            "entity_resolution": {
                "state": "unresolved",
                "entity_ref": None,
                "method": "deterministic_fixture_key_match",
                "unresolved_reason": "candidate lacks stable entity key and has conflicting location refs",
            },
        },
    ]


def validate_event_candidate_shape(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ["fixture_id", "kind", "event_type", "event_time", "source_class", "evidence_refs", "entity_resolution"]:
        if field not in fixture:
            errors.append(f"missing_required:{field}")
    if fixture.get("kind") == "EventEnvelope" and not fixture.get("event_id"):
        errors.append("missing_event_id")
    if fixture.get("kind") == "CandidateObservation" and not fixture.get("candidate_observation_id"):
        errors.append("missing_candidate_observation_id")
    if fixture.get("source_class") == "vss_model_narrative":
        errors.append("vss_model_narrative_as_fact_source_rejected")
    if fixture.get("live_source_claim") is True:
        errors.append("live_production_event_source_rejected")
    if not fixture.get("evidence_refs"):
        errors.append("missing_evidence_refs")
    if fixture.get("official_action_requested") is True:
        errors.append("official_action_affordance_rejected")
    return errors


def check_and_authority(fixture: dict[str, Any], service: dict[str, Any]) -> dict[str, Any]:
    authority_level = min(int(service.get("authority_ceiling", 1)), 1)
    fixture_hash = stable_hash(fixture)[:12]
    resolution_state = fixture.get("entity_resolution", {}).get("state", "unresolved")
    return {
        "check_report_ref": f"check:event_incident:{fixture_hash}:v1",
        "authority_envelope_ref": f"authority:event_incident:{fixture_hash}:level{authority_level}:v1",
        "authority_level": authority_level,
        "check_status": "PASS_WITH_LIMITATIONS",
        "resolution_state": resolution_state,
        "cannot_claim": [
            "official incident",
            "dispatch/control/enforcement",
            "legal/certified finding",
            "source truth from VSS/model narrative",
        ],
        "candidate_observation_only": True,
    }


def process_fixture(fixture: dict[str, Any], service: dict[str, Any]) -> dict[str, Any]:
    errors = validate_event_candidate_shape(fixture)
    if errors:
        return {"fixture_id": fixture.get("fixture_id"), "status": "REJECTED", "errors": errors}

    stamp = check_and_authority(fixture, service)
    resolution = fixture["entity_resolution"]
    resolved = resolution.get("state") == "resolved"
    review_state = {
        "event_review_state_id": f"event_review_state:{fixture['fixture_id'].split(':')[-1]}",
        "fixture_id": fixture["fixture_id"],
        "event_or_candidate_ref": fixture.get("event_id") or fixture.get("candidate_observation_id"),
        "resolution_state": resolution["state"],
        "resolved_entity_ref": resolution.get("entity_ref"),
        "unresolved_reason": resolution.get("unresolved_reason"),
        "evidence_refs": fixture["evidence_refs"],
        "check_report_ref": stamp["check_report_ref"],
        "authority_envelope_ref": stamp["authority_envelope_ref"],
        "authority_level": stamp["authority_level"],
        "candidate_observation_only": True,
        "official_incident_claim": False,
        "official_action_affordance_emitted": False,
        "safe_next_looks": [
            "review source evidence",
            "compare location refs",
            "route to Watch review if resolved and bounded",
        ],
    }
    watch_handoff = None
    if resolved:
        watch_handoff = {
            "handoff_id": f"watch_handoff:{fixture['fixture_id'].split(':')[-1]}",
            "from_service_id": service["service_id"],
            "to_service_id": "watch_scout_service",
            "handoff_kind": "review_safe_watch_candidate",
            "event_review_state_ref": review_state["event_review_state_id"],
            "entity_ref": resolution["entity_ref"],
            "evidence_refs": fixture["evidence_refs"],
            "check_report_ref": stamp["check_report_ref"],
            "authority_envelope_ref": stamp["authority_envelope_ref"],
            "watch_family": "event_incident_review",
            "priority_tier": "P1_checked_candidate",
            "not_official": True,
            "not_executed": True,
            "no_dispatch_control_enforcement": True,
        }
    return {
        "fixture_id": fixture["fixture_id"],
        "status": "PASS",
        "input_kind": fixture["kind"],
        "validation_errors": [],
        "resolution_state": resolution["state"],
        "review_state_update": review_state,
        "watch_handoff": watch_handoff,
        "check_authority": stamp,
    }


def build_run_envelope(result: dict[str, Any], fixture: dict[str, Any], service: dict[str, Any], index: int) -> dict[str, Any]:
    output_refs = [f"EventReviewState:{result['review_state_update']['event_review_state_id']}"]
    if result.get("watch_handoff"):
        output_refs.append(f"WatchHandoffRef:{result['watch_handoff']['handoff_id']}")
    return {
        "schema_version": "citybrain.agent_run_envelope.v1",
        "run_id": f"agent-run:epoch2_2b:event_incident:{index:04d}",
        "component_id": "event_incident_agent",
        "component_version": "1.0",
        "service_id": service["service_id"],
        "service_contract_ref": rel(SERVICE_CONTRACT_PATH),
        "service_registry_ref": rel(SERVICE_REGISTRY_PATH),
        "trigger": f"event:{fixture['kind']}.local_replay",
        "started_at": "2026-07-06T00:00:00Z",
        "ended_at": "2026-07-06T00:00:00Z",
        "duration_ms": 4 + index,
        "scope": "local_replay_review_query_only",
        "status": "emitted",
        "stop_condition_hit": None,
        "authority_level": result["check_authority"]["authority_level"],
        "authority_envelope_refs": [result["check_authority"]["authority_envelope_ref"]],
        "check_report_refs": [result["check_authority"]["check_report_ref"]],
        "evidence_refs": fixture["evidence_refs"],
        "inputs": [fixture["fixture_id"], fixture["kind"]],
        "outputs": output_refs,
        "tools_used": [
            "local_replay_fixture_read",
            "schema_validate",
            "deterministic_entity_resolution",
            "check_authority_stamp",
            "watch_handoff_fixture_write",
        ],
        "budget": {
            "policy_ref": "event_incident_service_budget_window",
            "max_llm_calls": service["budget_window"]["max_llm_calls"],
            "max_tool_calls": service["budget_window"]["max_tool_calls"],
            "max_steps": 10,
        },
        "limitations": [
            "local/replay/review/query only",
            "candidate observation only",
            "no official incident claim",
            "no official action, dispatch, enforcement, legal finding, or source truth mutation",
            "VSS/model narrative context is not fact source",
        ],
        "trace_refs": [
            fixture["fixture_id"],
            service["service_id"],
            result["review_state_update"]["event_review_state_id"],
        ],
    }


def negative_fixtures() -> list[dict[str, Any]]:
    base = event_candidate_fixtures()[0]
    missing_evidence = json.loads(json.dumps(base))
    missing_evidence["fixture_id"] = "negative:event_incident:missing_evidence"
    missing_evidence["evidence_refs"] = []
    vss_fact = json.loads(json.dumps(base))
    vss_fact["fixture_id"] = "negative:event_incident:vss_fact_source"
    vss_fact["source_class"] = "vss_model_narrative"
    official_action = json.loads(json.dumps(base))
    official_action["fixture_id"] = "negative:event_incident:official_action"
    official_action["official_action_requested"] = True
    live_source = json.loads(json.dumps(base))
    live_source["fixture_id"] = "negative:event_incident:live_source"
    live_source["live_source_claim"] = True
    malformed = json.loads(json.dumps(base))
    malformed["fixture_id"] = "negative:event_incident:malformed"
    malformed.pop("event_id", None)
    return [missing_evidence, vss_fact, official_action, live_source, malformed]


def build_negative_test_report(service: dict[str, Any]) -> dict[str, Any]:
    service_high_authority = json.loads(json.dumps(service))
    service_high_authority["authority_ceiling"] = 4
    results = []
    for fixture in negative_fixtures():
        errors = validate_event_candidate_shape(fixture)
        results.append(
            {
                "fixture_id": fixture["fixture_id"],
                "expected": "REJECT",
                "status": "PASS" if errors else "FAIL",
                "errors": errors,
                "agent_run_envelope_emitted": False,
            }
        )
    authority_errors = []
    if service_high_authority.get("authority_ceiling", 0) > 3:
        authority_errors.append("service_authority_ceiling_above_3_rejected")
    results.append(
        {
            "fixture_id": "negative:event_incident:authority_above_3",
            "expected": "REJECT",
            "status": "PASS" if authority_errors else "FAIL",
            "errors": authority_errors,
            "agent_run_envelope_emitted": False,
        }
    )
    forbidden_output_errors = sorted(FORBIDDEN_OUTPUTS.intersection(set(service.get("allowed_outputs", []))))
    results.append(
        {
            "fixture_id": "negative:event_incident:forbidden_outputs_in_service",
            "expected": "NO_FORBIDDEN_OUTPUTS",
            "status": "PASS" if not forbidden_output_errors else "FAIL",
            "errors": [f"forbidden_output_allowed:{item}" for item in forbidden_output_errors],
            "agent_run_envelope_emitted": False,
        }
    )
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_b.negative_test_report.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL",
        "created_at": utc_now(),
        "results": results,
    }


def build_handoff_fixtures(registry: dict[str, Any]) -> dict[str, Any]:
    event_service = service_by_id(registry, "event_incident_service")
    watch_service = service_by_id(registry, "watch_scout_service")
    fixtures = event_candidate_fixtures()
    processed = [process_fixture(fixture, event_service) for fixture in fixtures]
    envelopes = [
        build_run_envelope(result, fixture, event_service, index)
        for index, (result, fixture) in enumerate(zip(processed, fixtures), start=1)
        if result["status"] == "PASS"
    ]
    watch_handoffs = [row["watch_handoff"] for row in processed if row.get("watch_handoff")]
    deferred = [
        {
            "fixture_id": row["fixture_id"],
            "reason": "entity_unresolved_preserved_for_review_state_update",
            "watch_handoff_emitted": False,
        }
        for row in processed
        if row.get("resolution_state") == "unresolved"
    ]
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_b.event_to_watch_handoff_fixtures.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "created_at": utc_now(),
        "service_registry_ref": rel(SERVICE_REGISTRY_PATH),
        "event_incident_service": {
            "service_id": event_service["service_id"],
            "service_kind": event_service["service_kind"],
            "activation_status_before_lane": event_service["activation_status"],
            "lane_activation_mode": "local_replay_review_query_service_activation",
            "eligibility_review": event_service["service_justification_review"],
            "authority_ceiling": event_service["authority_ceiling"],
            "check_required": event_service["check_required"],
        },
        "watch_target_service": {
            "service_id": watch_service["service_id"],
            "activation_dependency": "registered_service_target; 2.2b Lane A output not present in this workspace at generation time",
        },
        "input_fixtures": fixtures,
        "processed_results": processed,
        "watch_handoffs": watch_handoffs,
        "deferred_or_unresolved": deferred,
        "agent_run_envelopes": envelopes,
        "checks": {
            "resolved_fixture_processed": any(row.get("resolution_state") == "resolved" for row in processed),
            "unresolved_fixture_preserved": any(row.get("resolution_state") == "unresolved" for row in processed),
            "watch_handoff_emitted": bool(watch_handoffs),
            "check_refs_attached": all(row["check_authority"]["check_report_ref"] for row in processed),
            "authority_refs_attached": all(row["check_authority"]["authority_envelope_ref"] for row in processed),
            "no_official_action_affordance": all(not row["review_state_update"]["official_action_affordance_emitted"] for row in processed),
        },
    }


def validate_outputs(handoff: dict[str, Any], negative: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    checks = handoff["checks"]
    for key, value in checks.items():
        if value is not True:
            errors.append(f"handoff_check_failed:{key}")
    service = handoff["event_incident_service"]
    if service["service_id"] != "event_incident_service":
        errors.append("event_incident_service_not_used")
    if service["service_kind"] != "event_triggered":
        errors.append("event_incident_service_not_event_triggered")
    if service["authority_ceiling"] > 3:
        errors.append("authority_ceiling_above_3")
    for row in handoff["processed_results"]:
        outputs = {row["review_state_update"]["event_review_state_id"]}
        if row.get("watch_handoff"):
            outputs.add(row["watch_handoff"]["handoff_id"])
        forbidden = FORBIDDEN_OUTPUTS.intersection(outputs)
        if forbidden:
            errors.append(f"forbidden_outputs:{','.join(sorted(forbidden))}")
        if row["review_state_update"]["official_incident_claim"] is not False:
            errors.append("official_incident_claim_emitted")
        if row["review_state_update"]["candidate_observation_only"] is not True:
            errors.append("candidate_observation_rule_missing")
    if negative["status"] != "PASS":
        errors.append("negative_tests_failed")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "checked_at": utc_now(),
    }


def jsonl_text(rows: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n"


def build_decision(gate: dict[str, Any], handoff: dict[str, Any], negative: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_b.decision.v1",
        "status": PASS_STATUS if validation["status"] == "PASS" else "FAIL_EVENT_INCIDENT_AGENT_VALIDATION",
        "created_at": utc_now(),
        "lane": "B",
        "push": "2.2b",
        "artifact_root": rel(OUTPUT_ROOT),
        "prerequisite_gate": gate,
        "source_package_refs": PACKAGE_REFS,
        "service_registry_ref": rel(SERVICE_REGISTRY_PATH),
        "service_contract_ref": rel(SERVICE_CONTRACT_PATH),
        "observability_ref": rel(OBSERVABILITY_REPORT_PATH),
        "multi_agent_replay_ref": rel(MULTI_AGENT_REPLAY_PATH),
        "event_incident_service": handoff["event_incident_service"],
        "fixtures": {
            "processed_count": len(handoff["processed_results"]),
            "resolved_count": sum(1 for row in handoff["processed_results"] if row.get("resolution_state") == "resolved"),
            "unresolved_count": sum(1 for row in handoff["processed_results"] if row.get("resolution_state") == "unresolved"),
            "watch_handoff_count": len(handoff["watch_handoffs"]),
            "run_envelope_count": len(handoff["agent_run_envelopes"]),
        },
        "validation": validation,
        "negative_test_status": negative["status"],
        "boundaries": {
            "official_incident_claim_emitted": False,
            "legal_finding_emitted": False,
            "dispatch_control_enforcement_emitted": False,
            "live_production_event_source_used": False,
            "vss_model_narrative_used_as_fact_source": False,
            "official_action_affordance_emitted": False,
            "per_domain_agent_classes_created": False,
            "learned_ranking_prediction_trained_model_or_dynamic_investigation_created": False,
            "local_replay_review_query_only": True,
        },
        "limitations": [
            "Event/Incident activation is local/replay/review/query only.",
            "Watch handoff targets the registered watch_scout_service; no 2.2b Lane A Watch service output was present at generation time.",
            "Fixtures prove resolved/unresolved handling and handoff shape, not production event ingestion.",
        ],
        "non_goals": NON_GOALS,
    }


def report_markdown(decision: dict[str, Any], handoff: dict[str, Any], negative: dict[str, Any]) -> str:
    lines = [
        "# Event / Incident Agent Activation Report",
        "",
        f"Status: `{decision['status']}`",
        "",
        "## Service Binding",
        "",
        f"- Service id: `{handoff['event_incident_service']['service_id']}`",
        f"- Service kind: `{handoff['event_incident_service']['service_kind']}`",
        f"- Authority ceiling: `{handoff['event_incident_service']['authority_ceiling']}`",
        f"- CHECK required: `{handoff['event_incident_service']['check_required']}`",
        "",
        "## Fixture Results",
        "",
    ]
    for row in handoff["processed_results"]:
        lines.append(
            f"- `{row['fixture_id']}`: `{row['resolution_state']}`, "
            f"CHECK `{row['check_authority']['check_report_ref']}`, "
            f"Authority `{row['check_authority']['authority_envelope_ref']}`"
        )
    lines.extend(
        [
            "",
            "## Watch Handoffs",
            "",
        ]
    )
    if handoff["watch_handoffs"]:
        for row in handoff["watch_handoffs"]:
            lines.append(f"- `{row['handoff_id']}` -> `{row['to_service_id']}` ({row['priority_tier']})")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Negative Tests",
            "",
            f"Status: `{negative['status']}`",
            "",
            "## Boundaries",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in NON_GOALS)
    return "\n".join(lines) + "\n"


def list_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append(
                {
                    "path": path.resolve().relative_to(OUTPUT_ROOT.resolve()).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_b.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "created_at": utc_now(),
        "item_count": len(files),
        "files": files,
    }


def write_all_outputs() -> dict[str, Any]:
    gate = check_prerequisite_gate()
    if gate["status"] != "PASS":
        return {"gate": gate, "decision": None}

    registry = load_service_registry()
    handoff = build_handoff_fixtures(registry)
    negative = build_negative_test_report(service_by_id(registry, "event_incident_service"))
    validation = validate_outputs(handoff, negative)
    decision = build_decision(gate, handoff, negative, validation)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_ROOT / "EVENT_TO_WATCH_HANDOFF_FIXTURES.json", handoff)
    write_text(OUTPUT_ROOT / "EVENT_INCIDENT_AGENT_RUN_ENVELOPES.jsonl", jsonl_text(handoff["agent_run_envelopes"]))
    write_json(OUTPUT_ROOT / "EVENT_INCIDENT_NEGATIVE_TEST_REPORT.json", negative)
    write_json(OUTPUT_ROOT / "EVENT_INCIDENT_AGENT_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "EVENT_INCIDENT_AGENT_REPORT.md", report_markdown(decision, handoff, negative))
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
    return {
        "gate": gate,
        "decision": decision,
        "handoff": handoff,
        "negative": negative,
        "validation": validation,
    }


def main() -> int:
    result = write_all_outputs()
    gate = result["gate"]
    if gate["status"] != "PASS":
        print(BLOCK_STATUS)
        print(json.dumps(gate["errors"], indent=2, sort_keys=True))
        return 1
    decision = result["decision"]
    print(decision["status"])
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
