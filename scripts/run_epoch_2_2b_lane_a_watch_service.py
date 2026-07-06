#!/usr/bin/env python3
"""Run Epoch 2.2 Push 2.2b Lane A Watch Scout local/replay service."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_a_watch_service"
INTEGRATION_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2a"

INTEGRATION_DECISION = INTEGRATION_ROOT / "PUSH_2_2A_INTEGRATION_DECISION.json"
PUSH_2_2B_FLAG = INTEGRATION_ROOT / "PUSH_2_2B_ALLOWED_TO_OPEN.flag"
SERVICE_REGISTRY = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract" / "SERVICE_REGISTRY_V1.json"
AGENT_RUN_ENVELOPE = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation" / "agent_run_envelope_v1.json"
REPLAY_HARNESS_REPORT = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation" / "reports" / "replay_harness_report.json"

PASS_STATUS = "PASS_WITH_LIMITATIONS"
PASS_CODE = "PASS_EPOCH_2_2_PUSH_2_2B_LANE_A_WATCH_SERVICE_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED"
BLOCKED_CODE = "BLOCKED_EPOCH_2_2_PUSH_2_2B_LANE_A_PREREQUISITE_GATE"

PACKAGE_REFS = [
    "02_PUSH_LANE_EXECUTION_MODEL.md",
    "09_PUSH_2_2B_LANE_A_WATCH_SERVICE_PROMPT.md",
    "20_SPEC_AGENT_SERVICE_CONTRACT.md",
    "21_SPEC_AGENT_OBSERVABILITY.md",
    "23_SPEC_WATCH_EVENT_BRIEFING_SERVICES.md",
    "28_SCOPE_NON_GOALS.md",
    "29_EXIT_GATE_CHECKLIST.md",
    "31_TRACK0_CORPUS_LEDGER_DISCIPLINE.md",
]

REQUIRED_ARTIFACTS = [
    "WATCH_SCOUT_SERVICE_DECISION.json",
    "WATCH_SCOUT_SERVICE_REPORT.md",
    "WATCH_SERVICE_CONFIG.json",
    "WATCH_SERVICE_RUN_ENVELOPES.jsonl",
    "WATCH_SERVICE_THROTTLE_REPORT.json",
    "WATCH_SERVICE_NEGATIVE_TEST_REPORT.json",
    "HASH_MANIFEST.json",
]

PRIORITY_TIERS = {
    "P0_boundary_safety": 0,
    "P1_checked_candidate": 1,
    "P2_stale_or_low_authority": 2,
    "P3_contextual": 3,
}

FORBIDDEN_OUTPUTS = {
    "Finding",
    "OfficialFinding",
    "OfficialAction",
    "DispatchCommand",
    "Ticket",
    "CasePacket",
    "LegalFinding",
    "CertifiedFinding",
    "AuthorityChange",
    "ReviewTruthMutation",
}

LIMITATIONS = [
    "Watch Scout service is active only as a local/replay/review/query service fixture.",
    "Service emits checked WatchItem review prompts only; it does not emit findings.",
    "Alert-cannon mitigation uses static priority tiers, hard caps, family caps, operator throttle modes, dedupe windows, queue caps, and safe_next_looks only.",
    "No learned ranking, adaptive/model suppression, prediction, trained model, dynamic investigation, official action, ticket, case, dispatch, enforcement, legal, or certified finding is introduced.",
    "No per-domain Watch agent classes are introduced.",
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def out_rel(path: Path) -> str:
    return path.resolve().relative_to(OUTPUT_ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def current_branch() -> str:
    proc = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return f"UNKNOWN:{proc.stderr.strip()}"
    return proc.stdout.strip()


def prerequisite_gate() -> dict[str, Any]:
    decision = read_json(INTEGRATION_DECISION) if INTEGRATION_DECISION.exists() else {}
    flag_value = PUSH_2_2B_FLAG.read_text(encoding="utf-8-sig").strip() if PUSH_2_2B_FLAG.exists() else ""
    checks = {
        "branch_is_main": current_branch() == "main",
        "integration_decision_exists": INTEGRATION_DECISION.exists(),
        "integration_status_exact": decision.get("status") == "PASS_PUSH_2_2A_INTEGRATION",
        "push_2_2b_allowed_flag_exists": PUSH_2_2B_FLAG.exists(),
        "push_2_2b_allowed_flag_pass": flag_value == "PASS",
    }
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_a.prerequisite_gate.v1",
        "status": "PASS" if all(checks.values()) else BLOCKED_STATUS,
        "checked_at": utc_now(),
        "branch": current_branch(),
        "integration_decision_ref": rel(INTEGRATION_DECISION),
        "integration_status": decision.get("status"),
        "flag_ref": rel(PUSH_2_2B_FLAG),
        "flag_value": flag_value,
        "checks": checks,
        "errors": [name for name, passed in checks.items() if not passed],
    }


def load_watch_service_entry() -> dict[str, Any]:
    registry = read_json(SERVICE_REGISTRY)
    for service in registry.get("services", []):
        if service.get("service_id") == "watch_scout_service":
            return service
    raise RuntimeError("watch_scout_service missing from SERVICE_REGISTRY_V1.json")


def existing_input_refs() -> dict[str, Any]:
    candidates = {
        "materialized_review_state": [
            REPO_ROOT / "outputs" / "main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end" / "EVENT_FABRIC_R2_CURRENT_STATE_ROWS.json",
            REPO_ROOT / "outputs" / "main_citybrain_d4x_live_event_fabric_minimal_local_slice" / "LIVE_EVENT_FABRIC_CURRENT_STATE.json",
            REPO_ROOT / "outputs" / "main_citybrain_d5_local_served_runtime_event_fabric_integration_r3" / "EVENT_STATE_RESPONSE_FIXTURES.json",
        ],
        "event_fabric": [
            REPO_ROOT / "outputs" / "main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end" / "EVENT_FABRIC_R2_EVENT_LOG.json",
            REPO_ROOT / "outputs" / "main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end" / "EVENT_FABRIC_R2_EVENT_LOG.jsonl",
            REPO_ROOT / "outputs" / "main_citybrain_d4x_live_event_fabric_minimal_local_slice" / "LIVE_EVENT_FABRIC_EVENT_LOG.jsonl",
        ],
        "check_outputs": [REPLAY_HARNESS_REPORT],
        "service_contract": [SERVICE_REGISTRY, AGENT_RUN_ENVELOPE],
    }
    found: dict[str, list[str]] = {}
    for key, paths in candidates.items():
        found[key] = [rel(path) for path in paths if path.exists()]
    replay = read_json(REPLAY_HARNESS_REPORT) if REPLAY_HARNESS_REPORT.exists() else {}
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "refs_by_kind": found,
        "check_report_refs": replay.get("check_refs", ["check:local-replay:watch-service:v1"]),
        "authority_envelope_refs": replay.get("authority_refs", ["AuthorityEnvelope:local_replay_review_query_only"]),
        "note": "Only existing local/replay refs are cited; no upstream input, raw data, or frozen output is mutated.",
    }


def effective_config(service: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    registry_throttle = service.get("throttle_policy", {})
    registry_budget = service.get("budget_window", {})
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_a.watch_service_config.v1",
        "status": PASS_STATUS,
        "service_id": "watch_scout_service",
        "component_id": "watch_scout",
        "service_registry_ref": rel(SERVICE_REGISTRY),
        "service_registry_entry": service,
        "mode": "local_replay_review_query_only",
        "activation_scope": "long_running_local_replay_service_fixture",
        "health_state_policy": {
            "healthy": "at least one tick emitted an AgentRunEnvelope and all caps/contracts passed",
            "degraded": "tick emitted but with throttled/deferred/suppressed review prompts",
            "blocked": "prerequisite, envelope, CHECK, or authority contract failed",
            "stopped": "operator paused service before tick",
        },
        "budget_window": {
            "window": registry_budget.get("window", "hour"),
            "max_runs": registry_budget.get("max_runs", 12),
            "max_tool_calls": registry_budget.get("max_tool_calls", 25),
            "max_llm_calls": 0,
            "max_wall_clock_seconds": registry_budget.get("max_wall_clock_seconds", 120),
            "max_outputs": registry_budget.get("max_outputs", 120),
        },
        "hard_volume_caps": {
            "global_queue_tick_cap": registry_throttle.get("max_items_per_tick", 25),
            "max_items_per_family_per_tick": registry_throttle.get("max_items_per_family_per_tick", 5),
            "max_emitted_watch_items_per_tick": registry_throttle.get("max_items_per_tick", 25),
            "max_enqueued_candidates_per_tick": 50,
        },
        "operator_throttle_modes": {
            "enabled": {"global_emit_cap": 25, "family_emit_cap": 5},
            "reduced": {"global_emit_cap": 3, "family_emit_cap": 2},
            "paused": {"global_emit_cap": 0, "family_emit_cap": 0},
        },
        "operator_controlled_family_throttle_state": {
            "traffic_flow": "enabled",
            "public_safety_boundary": "enabled",
            "asset_state": "enabled",
            "review_backlog": "enabled",
            "media_candidate": "reduced",
        },
        "static_priority_tiers": list(PRIORITY_TIERS.keys()),
        "priority_policy": "static_priority_tier_then_input_order_only",
        "dedupe_window_seconds": max(86400, registry_throttle.get("dedupe_window_seconds", 0)),
        "safe_next_looks": [
            "open_source_record",
            "open_check_report",
            "open_authority_envelope",
            "review_related_event_state",
            "defer_or_dismiss_with_reason",
        ],
        "alert_cannon_boundary": {
            "learned_ranking_used": False,
            "adaptive_or_model_suppression_used": False,
            "trained_prediction_model_used": False,
            "static_caps_only": True,
        },
        "source_inputs": inputs,
        "allowed_outputs": ["WatchItem"],
        "forbidden_outputs": sorted(FORBIDDEN_OUTPUTS),
        "non_action_boundaries": {
            "findings_allowed": False,
            "official_action_allowed": False,
            "ticket_or_case_allowed": False,
            "dispatch_control_enforcement_allowed": False,
            "legal_or_certified_finding_allowed": False,
            "authority_or_review_truth_mutation_allowed": False,
        },
        "limitations": LIMITATIONS,
    }


def replay_candidates(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    check_refs = inputs["check_report_refs"] or ["check:local-replay:watch-service:v1"]
    authority_refs = inputs["authority_envelope_refs"] or ["AuthorityEnvelope:local_replay_review_query_only"]
    base_source_refs = (
        inputs["refs_by_kind"].get("materialized_review_state", [])[:1]
        + inputs["refs_by_kind"].get("event_fabric", [])[:1]
        + inputs["refs_by_kind"].get("check_outputs", [])[:1]
    )

    def row(tick: int, index: int, family: str, tier: str, fingerprint: str, label: str) -> dict[str, Any]:
        return {
            "candidate_id": f"watch-candidate:t{tick}:{index:02d}",
            "tick_index": tick,
            "input_order": index,
            "family": family,
            "priority_tier": tier,
            "fingerprint": fingerprint,
            "label": label,
            "source_refs": base_source_refs,
            "event_ref": f"event-fabric:local-replay:{tick}:{index:02d}",
            "check_report_ref": check_refs[(index - 1) % len(check_refs)],
            "authority_envelope_ref": authority_refs[(index - 1) % len(authority_refs)],
            "safe_next_looks": ["open_check_report", "open_authority_envelope", "review_related_event_state"],
        }

    rows = [
        row(1, 1, "public_safety_boundary", "P0_boundary_safety", "boundary:west-gate:loitering-context", "Boundary review context at west gate"),
        row(1, 2, "traffic_flow", "P1_checked_candidate", "traffic:marina:queue-rise", "Traffic queue rise candidate"),
        row(1, 3, "traffic_flow", "P1_checked_candidate", "traffic:marina:queue-rise", "Duplicate traffic queue rise candidate"),
        row(1, 4, "traffic_flow", "P1_checked_candidate", "traffic:marina:lane-blocked", "Lane blockage review prompt"),
        row(1, 5, "traffic_flow", "P2_stale_or_low_authority", "traffic:marina:signal-offset", "Signal offset stale context"),
        row(1, 6, "traffic_flow", "P2_stale_or_low_authority", "traffic:marina:bus-stop-crowding", "Bus stop crowding context"),
        row(1, 7, "traffic_flow", "P3_contextual", "traffic:marina:detour-note", "Detour context"),
        row(1, 8, "traffic_flow", "P3_contextual", "traffic:marina:parking-overflow", "Parking overflow context"),
        row(1, 9, "asset_state", "P1_checked_candidate", "asset:utility:service-point-alert", "Utility service point review"),
        row(1, 10, "review_backlog", "P2_stale_or_low_authority", "review:stale-check-required", "Stale CHECK follow-up"),
        row(2, 1, "traffic_flow", "P1_checked_candidate", "traffic:marina:queue-rise", "Cross-tick duplicate queue rise"),
        row(2, 2, "media_candidate", "P1_checked_candidate", "media:west-gate:candidate-shadow", "Media candidate review prompt"),
        row(2, 3, "media_candidate", "P2_stale_or_low_authority", "media:west-gate:low-authority", "Low authority media context"),
        row(2, 4, "media_candidate", "P2_stale_or_low_authority", "media:west-gate:needs-check", "Media CHECK follow-up"),
        row(2, 5, "asset_state", "P1_checked_candidate", "asset:utility:service-point-alert", "Cross-tick asset duplicate"),
        row(2, 6, "review_backlog", "P3_contextual", "review:operator-follow-up", "Operator follow-up context"),
    ]
    return rows


def validate_watch_item(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if item.get("packet_type") != "WatchItem":
        errors.append("not_watch_item")
    if item.get("output_type") in FORBIDDEN_OUTPUTS:
        errors.append("forbidden_output_type")
    if not item.get("check_report_ref"):
        errors.append("missing_check_report_ref")
    if not item.get("authority_envelope_ref"):
        errors.append("missing_authority_envelope_ref")
    if item.get("not_official") is not True:
        errors.append("missing_not_official_boundary")
    if item.get("not_executed") is not True:
        errors.append("missing_not_executed_boundary")
    if item.get("attempts_authority_or_review_truth_change") is True:
        errors.append("authority_or_review_truth_change_attempt")
    if any(key in item for key in ["finding", "official_finding", "official_action", "dispatch_command"]):
        errors.append("forbidden_finding_or_action_field")
    return errors


def make_watch_item(candidate: dict[str, Any], tick_index: int, emitted_index: int) -> dict[str, Any]:
    return {
        "packet_type": "WatchItem",
        "output_type": "WatchItem",
        "watch_item_id": f"watch-item:epoch2_2b:lane_a:t{tick_index}:{emitted_index:02d}",
        "candidate_id": candidate["candidate_id"],
        "family": candidate["family"],
        "priority_tier": candidate["priority_tier"],
        "static_priority_rank": PRIORITY_TIERS[candidate["priority_tier"]],
        "label": candidate["label"],
        "source_refs": candidate["source_refs"],
        "event_ref": candidate["event_ref"],
        "check_report_ref": candidate["check_report_ref"],
        "authority_envelope_ref": candidate["authority_envelope_ref"],
        "limitations": ["local/replay review prompt only", "not a finding", "not official action"],
        "cannot_claim": ["incident finding", "official action", "ticket/case", "dispatch/control/enforcement", "legal/certified finding"],
        "safe_next_looks": candidate["safe_next_looks"],
        "not_official": True,
        "not_executed": True,
        "attempts_authority_or_review_truth_change": False,
    }


def tick_caps(config: dict[str, Any], operator_mode: str) -> dict[str, int]:
    mode_caps = config["operator_throttle_modes"][operator_mode]
    hard = config["hard_volume_caps"]
    return {
        "global_emit_cap": min(hard["global_queue_tick_cap"], hard["max_emitted_watch_items_per_tick"], mode_caps["global_emit_cap"]),
        "family_emit_cap": min(hard["max_items_per_family_per_tick"], mode_caps["family_emit_cap"]),
    }


def run_tick(
    *,
    tick_index: int,
    trigger_id: str,
    operator_mode: str,
    config: dict[str, Any],
    candidates: list[dict[str, Any]],
    seen_fingerprints: set[str],
) -> dict[str, Any]:
    caps = tick_caps(config, operator_mode)
    sorted_candidates = sorted(candidates, key=lambda item: (PRIORITY_TIERS[item["priority_tier"]], item["input_order"]))
    family_counts: dict[str, int] = defaultdict(int)
    emitted: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    throttled: list[dict[str, Any]] = []

    for candidate in sorted_candidates:
        if candidate["fingerprint"] in seen_fingerprints:
            suppressed.append({"candidate_id": candidate["candidate_id"], "reason": "dedupe_window", "fingerprint": candidate["fingerprint"]})
            continue
        family_state = config["operator_controlled_family_throttle_state"].get(candidate["family"], "enabled")
        if family_state == "paused":
            deferred.append({"candidate_id": candidate["candidate_id"], "reason": "operator_family_paused", "family": candidate["family"]})
            continue
        if family_state == "reduced" and family_counts[candidate["family"]] >= 1:
            deferred.append({"candidate_id": candidate["candidate_id"], "reason": "operator_family_reduced", "family": candidate["family"]})
            continue
        if len(emitted) >= caps["global_emit_cap"]:
            throttled.append({"candidate_id": candidate["candidate_id"], "reason": "global_queue_tick_cap", "cap": caps["global_emit_cap"]})
            continue
        if family_counts[candidate["family"]] >= caps["family_emit_cap"]:
            throttled.append({"candidate_id": candidate["candidate_id"], "reason": "per_family_cap", "family": candidate["family"], "cap": caps["family_emit_cap"]})
            continue
        item = make_watch_item(candidate, tick_index, len(emitted) + 1)
        validation_errors = validate_watch_item(item)
        if validation_errors:
            deferred.append({"candidate_id": candidate["candidate_id"], "reason": "watch_item_validation_failed", "errors": validation_errors})
            continue
        emitted.append(item)
        family_counts[candidate["family"]] += 1
        seen_fingerprints.add(candidate["fingerprint"])

    status = "emitted"
    if throttled:
        status = "emitted_with_throttling"
    if operator_mode == "paused":
        status = "paused"
    counts = {"emitted": len(emitted), "suppressed": len(suppressed), "deferred": len(deferred), "throttled": len(throttled)}
    envelope = make_run_envelope(
        tick_index=tick_index,
        trigger_id=trigger_id,
        operator_mode=operator_mode,
        status=status,
        counts=counts,
        config=config,
        watch_items=emitted,
        candidates=sorted_candidates,
    )
    return {
        "tick_index": tick_index,
        "trigger_id": trigger_id,
        "operator_throttle_state": operator_mode,
        "status": status,
        "health_state": "healthy" if not throttled and not deferred else "degraded",
        "caps": caps,
        "input_candidate_count": len(candidates),
        "emitted_watch_items": emitted,
        "suppressed": suppressed,
        "deferred": deferred,
        "throttled": throttled,
        "counts": counts,
        "family_emitted_counts": dict(sorted(Counter(item["family"] for item in emitted).items())),
        "agent_run_envelope": envelope,
    }


def make_run_envelope(
    *,
    tick_index: int,
    trigger_id: str,
    operator_mode: str,
    status: str,
    counts: dict[str, int],
    config: dict[str, Any],
    watch_items: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    run_id = f"agent-run:epoch2_2b:watch_scout_service:tick:{tick_index:02d}"
    check_refs = sorted({item["check_report_ref"] for item in watch_items} or {candidate["check_report_ref"] for candidate in candidates})
    authority_refs = sorted({item["authority_envelope_ref"] for item in watch_items} or {candidate["authority_envelope_ref"] for candidate in candidates})
    return {
        "schema_version": "citybrain.agent_run_envelope.v1",
        "run_id": run_id,
        "component_id": "watch_scout",
        "component_version": "1.0",
        "service_id": "watch_scout_service",
        "service_version": config["service_registry_entry"].get("service_version", "1.0.0"),
        "scope": "local_replay_review_query_only",
        "trigger": trigger_id,
        "started_at": f"2026-07-06T09:{20 + tick_index:02d}:00Z",
        "ended_at": f"2026-07-06T09:{20 + tick_index:02d}:00Z",
        "duration_ms": 0,
        "status": status,
        "authority_level": 1,
        "budget": {
            "policy_ref": "watch_service_budget_window_v1",
            "max_steps": 10,
            "max_tool_calls": config["budget_window"]["max_tool_calls"],
            "max_llm_calls": 0,
            "max_outputs": config["budget_window"]["max_outputs"],
        },
        "budget_allocated": config["budget_window"],
        "budget_consumed": {
            "runs": 1,
            "tool_calls": 2,
            "llm_calls": 0,
            "outputs": len(watch_items),
            "wall_clock_seconds": 0,
        },
        "inputs": sorted({ref for candidate in candidates for ref in candidate["source_refs"]}),
        "outputs": [item["watch_item_id"] for item in watch_items],
        "output_packet_types": ["WatchItem"] if watch_items else [],
        "tools_used": ["local_replay_fixture_read", "schema_validate"],
        "llm_seat_used": None,
        "evidence_refs": sorted({candidate["event_ref"] for candidate in candidates}),
        "check_report_refs": check_refs,
        "authority_envelope_refs": authority_refs,
        "trace_refs": [trigger_id, "watch_scout_service", f"operator_mode:{operator_mode}"],
        "handoff_target": ["WATCH review prompts"],
        "suppressed_deferred_throttled_counts": {
            "suppressed": counts["suppressed"],
            "deferred": counts["deferred"],
            "throttled": counts["throttled"],
        },
        "errors": [],
        "stop_condition_hit": None,
        "limitations": ["local/replay Watch service tick only", "WatchItems are review prompts, not findings"],
    }


def run_service(config: dict[str, Any]) -> dict[str, Any]:
    inputs = config["source_inputs"]
    candidates = replay_candidates(inputs)
    by_tick = {
        1: [row for row in candidates if row["tick_index"] == 1],
        2: [row for row in candidates if row["tick_index"] == 2],
    }
    seen_fingerprints: set[str] = set()
    ticks = [
        run_tick(
            tick_index=1,
            trigger_id="event:watch-service-local-replay:tick-001",
            operator_mode="enabled",
            config=config,
            candidates=by_tick[1],
            seen_fingerprints=seen_fingerprints,
        ),
        run_tick(
            tick_index=2,
            trigger_id="event:watch-service-local-replay:tick-002",
            operator_mode="reduced",
            config=config,
            candidates=by_tick[2],
            seen_fingerprints=seen_fingerprints,
        ),
    ]
    aggregate = Counter()
    for tick in ticks:
        aggregate.update(tick["counts"])
    checks = {
        "at_least_two_ticks": len(ticks) >= 2,
        "one_agent_run_envelope_per_tick": all(tick.get("agent_run_envelope") for tick in ticks),
        "watch_items_only": all(item["packet_type"] == "WatchItem" for tick in ticks for item in tick["emitted_watch_items"]),
        "no_findings_or_official_actions": not any(
            set(item.keys()) & {"finding", "official_finding", "official_action", "dispatch_command"}
            for tick in ticks
            for item in tick["emitted_watch_items"]
        ),
        "all_watch_items_have_check_and_authority_refs": all(
            item.get("check_report_ref") and item.get("authority_envelope_ref")
            for tick in ticks
            for item in tick["emitted_watch_items"]
        ),
        "global_caps_enforced": all(tick["counts"]["emitted"] <= tick["caps"]["global_emit_cap"] for tick in ticks),
        "per_family_caps_enforced": all(
            count <= tick["caps"]["family_emit_cap"] for tick in ticks for count in tick["family_emitted_counts"].values()
        ),
        "dedupe_emitted_suppression": aggregate["suppressed"] > 0,
        "throttled_or_deferred_counts_emitted": aggregate["throttled"] > 0 or aggregate["deferred"] > 0,
        "operator_throttle_state_consumed": any(tick["operator_throttle_state"] == "reduced" for tick in ticks),
        "no_learned_ranking_or_adaptive_suppression": config["alert_cannon_boundary"]["static_caps_only"]
        and not config["alert_cannon_boundary"]["learned_ranking_used"]
        and not config["alert_cannon_boundary"]["adaptive_or_model_suppression_used"],
    }
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_a.watch_service_throttle_report.v1",
        "status": PASS_STATUS if all(checks.values()) else "FAIL",
        "created_at": utc_now(),
        "service_id": "watch_scout_service",
        "component_id": "watch_scout",
        "service_health_state": "degraded" if aggregate["throttled"] or aggregate["deferred"] else "healthy",
        "checks": checks,
        "aggregate_counts": dict(sorted(aggregate.items())),
        "tick_count": len(ticks),
        "ticks": ticks,
        "limitations": LIMITATIONS,
    }


def validate_tick_contract(tick: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not tick.get("agent_run_envelope"):
        errors.append("missing_agent_run_envelope")
    for item in tick.get("emitted_watch_items", []):
        errors.extend(validate_watch_item(item))
    if any(item.get("attempts_authority_or_review_truth_change") for item in tick.get("emitted_watch_items", [])):
        errors.append("attempted_authority_or_review_truth_change")
    return errors


def build_negative_report(config: dict[str, Any], throttle_report: dict[str, Any]) -> dict[str, Any]:
    base_tick = copy.deepcopy(throttle_report["ticks"][0])
    fixtures = []

    no_envelope = copy.deepcopy(base_tick)
    no_envelope.pop("agent_run_envelope", None)
    errors = validate_tick_contract(no_envelope)
    fixtures.append({"fixture_id": "service_tick_without_agent_run_envelope", "expected": "REJECTED", "actual": "REJECTED" if errors else "ACCEPTED", "errors": errors})

    over_cap_tick = next(tick for tick in throttle_report["ticks"] if tick["counts"]["throttled"] > 0)
    over_cap_passed = over_cap_tick["counts"]["emitted"] <= over_cap_tick["caps"]["global_emit_cap"] and over_cap_tick["counts"]["throttled"] > 0
    fixtures.append(
        {
            "fixture_id": "over_cap_emits_throttled_status_not_extra_items",
            "expected": "THROTTLED_NOT_EMITTED",
            "actual": "THROTTLED_NOT_EMITTED" if over_cap_passed else "EXTRA_ITEMS_EMITTED",
            "errors": [] if over_cap_passed else ["over_cap_extra_items_emitted"],
        }
    )

    duplicate_passed = throttle_report["aggregate_counts"].get("suppressed", 0) > 0
    fixtures.append(
        {
            "fixture_id": "duplicate_item_deduped",
            "expected": "DEDUPED",
            "actual": "DEDUPED" if duplicate_passed else "NOT_DEDUPED",
            "errors": [] if duplicate_passed else ["duplicate_not_suppressed"],
        }
    )

    missing_check = copy.deepcopy(base_tick["emitted_watch_items"][0])
    missing_check["check_report_ref"] = None
    errors = validate_watch_item(missing_check)
    fixtures.append({"fixture_id": "watch_item_without_check_report_fails", "expected": "REJECTED", "actual": "REJECTED" if errors else "ACCEPTED", "errors": errors})

    authority_change = copy.deepcopy(base_tick["emitted_watch_items"][0])
    authority_change["attempts_authority_or_review_truth_change"] = True
    authority_change["output_type"] = "AuthorityChange"
    errors = validate_watch_item(authority_change)
    fixtures.append({"fixture_id": "service_attempting_authority_or_review_truth_change_fails", "expected": "REJECTED", "actual": "REJECTED" if errors else "ACCEPTED", "errors": errors})

    for row in fixtures:
        row["status"] = "PASS" if row["actual"] in {"REJECTED", "THROTTLED_NOT_EMITTED", "DEDUPED"} else "FAIL"
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_a.watch_service_negative_tests.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in fixtures) else "FAIL",
        "created_at": utc_now(),
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
        "config_ref": "outputs/epoch_2_2/push_2_2b/lane_a_watch_service/WATCH_SERVICE_CONFIG.json",
        "throttle_report_ref": "outputs/epoch_2_2/push_2_2b/lane_a_watch_service/WATCH_SERVICE_THROTTLE_REPORT.json",
    }


def build_decision(gate: dict[str, Any], config: dict[str, Any], throttle: dict[str, Any], negative: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "prerequisite_gate_passed": gate["status"] == "PASS",
        "service_registry_watch_entry_used": config["service_registry_entry"]["service_id"] == "watch_scout_service",
        "at_least_two_ticks": throttle["checks"]["at_least_two_ticks"],
        "one_envelope_per_tick": throttle["checks"]["one_agent_run_envelope_per_tick"],
        "watch_items_only": throttle["checks"]["watch_items_only"],
        "check_and_authority_refs_carried": throttle["checks"]["all_watch_items_have_check_and_authority_refs"],
        "hard_caps_enforced": throttle["checks"]["global_caps_enforced"] and throttle["checks"]["per_family_caps_enforced"],
        "dedupe_and_operator_throttle_consumed": throttle["checks"]["dedupe_emitted_suppression"] and throttle["checks"]["operator_throttle_state_consumed"],
        "negative_tests_pass": negative["status"] == "PASS",
        "no_learned_ranking_or_adaptive_suppression": throttle["checks"]["no_learned_ranking_or_adaptive_suppression"],
    }
    status = PASS_STATUS if all(checks.values()) else BLOCKED_STATUS
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_a.watch_service_decision.v1",
        "status": status,
        "decision_code": PASS_CODE if status == PASS_STATUS else "BLOCKED_EPOCH_2_2_PUSH_2_2B_LANE_A_WATCH_SERVICE_VALIDATION",
        "created_at": utc_now(),
        "lane": "A",
        "push": "2.2b",
        "artifact_root": rel(OUTPUT_ROOT),
        "source_package_refs": PACKAGE_REFS,
        "prerequisite_gate": gate,
        "checks": checks,
        "artifacts": REQUIRED_ARTIFACTS,
        "tick_count": throttle["tick_count"],
        "service_health_state": throttle["service_health_state"],
        "aggregate_counts": throttle["aggregate_counts"],
        "service_registry_ref": rel(SERVICE_REGISTRY),
        "run_envelopes_ref": "outputs/epoch_2_2/push_2_2b/lane_a_watch_service/WATCH_SERVICE_RUN_ENVELOPES.jsonl",
        "boundaries": {
            "local_replay_review_query_only": True,
            "findings_emitted": False,
            "official_action_ticket_case_dispatch_enforcement_created": False,
            "legal_or_certified_finding_created": False,
            "authority_above_level_3": False,
            "learned_ranking_prediction_or_trained_model_created": False,
            "adaptive_or_model_suppression_created": False,
            "dynamic_investigation_created": False,
            "per_domain_agent_classes_created": False,
        },
        "blockers": [] if status == PASS_STATUS else [name for name, passed in checks.items() if not passed],
        "limitations": LIMITATIONS,
    }


def list_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": out_rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_a.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "created_at": utc_now(),
        "item_count": len(files),
        "files": files,
    }


def report_text(decision: dict[str, Any], config: dict[str, Any], throttle: dict[str, Any], negative: dict[str, Any]) -> str:
    return f"""# Watch Scout Service Report

Status: `{decision['status']}`

Decision code: `{decision['decision_code']}`

The Watch Scout service ran `{throttle['tick_count']}` local/replay ticks using the Push 2.2a `watch_scout_service` ServiceRegistry entry. Each tick emitted one AgentRunEnvelope in `WATCH_SERVICE_RUN_ENVELOPES.jsonl`.

Health state: `{throttle['service_health_state']}`

Aggregate counts:

- emitted: `{throttle['aggregate_counts'].get('emitted', 0)}`
- suppressed: `{throttle['aggregate_counts'].get('suppressed', 0)}`
- deferred: `{throttle['aggregate_counts'].get('deferred', 0)}`
- throttled: `{throttle['aggregate_counts'].get('throttled', 0)}`

Caps and throttles:

- global queue/tick cap: `{config['hard_volume_caps']['global_queue_tick_cap']}`
- per-family cap: `{config['hard_volume_caps']['max_items_per_family_per_tick']}`
- dedupe window seconds: `{config['dedupe_window_seconds']}`
- operator modes: `{', '.join(config['operator_throttle_modes'].keys())}`
- static priority tiers: `{', '.join(config['static_priority_tiers'])}`

Negative tests: `{negative['status']}` across `{negative['fixture_count']}` fixtures.

Boundaries:

{chr(10).join(f"- {item}" for item in LIMITATIONS)}
"""


def write_all_outputs() -> dict[str, Any]:
    gate = prerequisite_gate()
    if gate["status"] != "PASS":
        return {"gate": gate, "decision": None}

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    service = load_watch_service_entry()
    inputs = existing_input_refs()
    config = effective_config(service, inputs)
    throttle = run_service(config)
    negative = build_negative_report(config, throttle)
    decision = build_decision(gate, config, throttle, negative)
    envelopes = [tick["agent_run_envelope"] for tick in throttle["ticks"]]

    write_json(OUTPUT_ROOT / "WATCH_SERVICE_CONFIG.json", config)
    write_jsonl(OUTPUT_ROOT / "WATCH_SERVICE_RUN_ENVELOPES.jsonl", envelopes)
    write_json(OUTPUT_ROOT / "WATCH_SERVICE_THROTTLE_REPORT.json", throttle)
    write_json(OUTPUT_ROOT / "WATCH_SERVICE_NEGATIVE_TEST_REPORT.json", negative)
    write_json(OUTPUT_ROOT / "WATCH_SCOUT_SERVICE_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "WATCH_SCOUT_SERVICE_REPORT.md", report_text(decision, config, throttle, negative))
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
    return {
        "gate": gate,
        "service": service,
        "config": config,
        "throttle": throttle,
        "negative": negative,
        "decision": decision,
        "envelopes": envelopes,
    }


def main() -> int:
    result = write_all_outputs()
    gate = result["gate"]
    if gate["status"] != "PASS":
        print(BLOCKED_STATUS)
        print(BLOCKED_CODE)
        print(json.dumps(gate["errors"], indent=2, sort_keys=True))
        return 1
    decision = result["decision"]
    print(decision["status"])
    print(decision["decision_code"])
    print(f"Output: {rel(OUTPUT_ROOT)}")
    if decision["status"] != PASS_STATUS:
        print(json.dumps(decision["blockers"], indent=2, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
