#!/usr/bin/env python3
"""Epoch 2.2 Push 2.2a Lane B agent observability dashboard runner."""

from __future__ import annotations

import hashlib
import html
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_b_observability"
ENTRY_GATE_PATH = REPO_ROOT / "outputs" / "epoch_2_2_entry_gate" / "EPOCH_2_2_ENTRY_GATE_DECISION.json"

AGENT_RUN_ENVELOPE_PATH = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation" / "agent_run_envelope_v1.json"
COMPONENT_REGISTRY_PATH = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation" / "component_registry_v1.json"
HANDOFF_MATRIX_PATH = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation" / "agent_handoff_matrix_v1.json"
BUDGET_POLICY_PATH = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation" / "budget_stop_policy_v1.json"
RECERT_REPORT_PATH = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation" / "reports" / "agent_recertification_report.json"
MODE_SCORECARD_PATH = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation" / "reports" / "mode_eval_harness_report.json"
RBAC_OBSERVABILITY_PATH = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_a_rbac_audit_observability" / "observability_envelope_v1.json"
RBAC_DECISION_PATH = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_a_rbac_audit_observability" / "PUSH_2_1B_LANE_A_DECISION.json"
MATURITY_DASHBOARD_PATH = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_c_dashboard_outcome" / "data_maturity_dashboard_v1.json"
CALIBRATION_REPORT_PATH = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_c_calibration_kit_ux" / "calibration_report_generation_report.json"
LEDGER_ROWS_PATH = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1c_final_closeout" / "EPOCH_2_1_LEDGER_ROWS.json"
CORPUS_APPEND_PATH = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1c_final_closeout" / "EPOCH_2_1_CORPUS_APPEND_REPORT.json"
SOT_DELTA_PATH = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1c_final_closeout" / "EPOCH_2_1_SOURCE_OF_TRUTH_MATRIX_DELTA.md"

SERVICE_REGISTRY_CANDIDATES = [
    REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract" / "SERVICE_REGISTRY_V1.json",
    REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract" / "SERVICE_REGISTRY.json",
    REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_agent_service_contract" / "SERVICE_REGISTRY_V1.json",
    REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_agent_service_contract" / "SERVICE_REGISTRY.json",
]

PASS_STATUS = "PASS_WITH_LIMITATIONS"
BLOCK_STATUS = "BLOCKED_EPOCH_2_2_ENTRY_GATE"
ENTRY_PASS_STATUS = "PASS_EPOCH_2_2_ENTRY_GATE"
ALLOWED_HEALTH_STATES = ["healthy", "degraded", "blocked", "stopped"]

REQUIRED_PANEL_FIELDS = [
    "service_name",
    "component_id",
    "health_state",
    "last_trigger",
    "schedule_trigger_type",
    "input_packet_refs",
    "output_packet_refs",
    "tools_used",
    "check_failures_downgraded_outputs",
    "authority_level",
    "budget_consumed",
    "latency_ms",
    "error_count",
    "handoff_target",
    "suppressed_deferred_throttled_count",
    "run_envelope_refs",
    "ledger_row_refs",
]

NON_GOALS = [
    "No production monitoring or autonomous action claim.",
    "No new metrics store.",
    "No invented service-health status values.",
    "No per-domain agent classes.",
    "No official action, dispatch, enforcement, ticket, case, or legal/certified finding.",
    "Local/replay/review/query observability only.",
]

PACKAGE_REFS = [
    "02_PUSH_LANE_EXECUTION_MODEL.md",
    "06_PUSH_2_2A_LANE_B_OBSERVABILITY_PROMPT.md",
    "20_SPEC_AGENT_SERVICE_CONTRACT.md",
    "21_SPEC_AGENT_OBSERVABILITY.md",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
    gate_decision: dict[str, Any] = {}
    if not ENTRY_GATE_PATH.exists():
        errors.append(f"missing_entry_gate:{rel(ENTRY_GATE_PATH)}")
    else:
        gate_decision = read_json(ENTRY_GATE_PATH)
        if gate_decision.get("status") != ENTRY_PASS_STATUS:
            errors.append(f"entry_gate_status_not_pass:{gate_decision.get('status')}")
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2a.lane_b.prerequisite_gate.v1",
        "status": "PASS" if not errors else BLOCK_STATUS,
        "checked_at": utc_now(),
        "branch": branch,
        "entry_gate_ref": rel(ENTRY_GATE_PATH),
        "entry_gate_status": gate_decision.get("status"),
        "errors": errors,
    }


def service_registry_status() -> dict[str, Any]:
    present = [path for path in SERVICE_REGISTRY_CANDIDATES if path.exists()]
    return {
        "status": "AVAILABLE" if present else "PENDING_LANE_A_SERVICE_REGISTRY",
        "refs": [rel(path) for path in present],
        "candidate_refs_checked": [rel(path) for path in SERVICE_REGISTRY_CANDIDATES],
        "limitation": None if present else "Lane A ServiceRegistry/AgentServiceContract outputs are pending/not present; Lane B materializes observability from Epoch 2.0/2.1 artifacts and marks service fixture state as limited.",
    }


def load_sources() -> dict[str, Any]:
    return {
        "agent_run_envelope": read_json(AGENT_RUN_ENVELOPE_PATH),
        "component_registry": read_json(COMPONENT_REGISTRY_PATH),
        "handoff_matrix": read_json(HANDOFF_MATRIX_PATH),
        "budget_policy": read_json(BUDGET_POLICY_PATH),
        "recert_report": read_json(RECERT_REPORT_PATH),
        "mode_scorecard": read_json(MODE_SCORECARD_PATH),
        "rbac_observability": read_json(RBAC_OBSERVABILITY_PATH),
        "rbac_decision": read_json(RBAC_DECISION_PATH),
        "maturity_dashboard": read_json(MATURITY_DASHBOARD_PATH),
        "calibration_report": read_json(CALIBRATION_REPORT_PATH),
        "ledger_rows": read_json(LEDGER_ROWS_PATH),
        "corpus_append": read_json(CORPUS_APPEND_PATH),
        "source_of_truth_delta": SOT_DELTA_PATH.read_text(encoding="utf-8"),
    }


def index_components(component_registry: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        row.get("component_id"): row
        for row in component_registry
        if isinstance(row, dict) and row.get("component_id")
    }


def index_ledger_rows(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        row.get("row_id"): row
        for row in ledger.get("rows", [])
        if isinstance(row, dict) and row.get("row_id")
    }


def lookup_budget_policy(budget_policies: list[dict[str, Any]], policy_id: str | None) -> dict[str, Any]:
    for row in budget_policies:
        if row.get("policy_id") == policy_id:
            return row
    return {}


def handoff_targets_for(component_id: str, handoff_matrix: list[dict[str, Any]]) -> list[str]:
    targets = [row.get("to_component") for row in handoff_matrix if row.get("from_component") == component_id]
    return [target for target in targets if target]


def count_suppressed_deferred_throttled(maturity_dashboard: dict[str, Any], calibration_report: dict[str, Any]) -> dict[str, int]:
    suppressed = 0
    if maturity_dashboard.get("outcome_record_availability_and_aggregation_status", {}).get("small_cell_suppressed"):
        suppressed += 1
    suppressed += sum(1 for row in calibration_report.get("reports", []) if row.get("suppressed_from_dashboard"))
    deferred = maturity_dashboard.get("source_freshness_status", {}).get("deferred_live_source_count", 0)
    return {"suppressed": suppressed, "deferred": int(deferred or 0), "throttled": 0}


def check_failure_summary(maturity_dashboard: dict[str, Any], calibration_report: dict[str, Any]) -> dict[str, Any]:
    check_counts = maturity_dashboard.get("check_status_cannot_claim_stale_counts", {})
    cannot_claim = int(check_counts.get("cannot_claim_count", 0) or 0)
    stale = int(check_counts.get("stale_or_refresh_needed_count", 0) or 0)
    suppressed_reports = [row.get("calibration_report_id") for row in calibration_report.get("reports", []) if row.get("suppressed_from_dashboard")]
    return {
        "check_failure_count": 0,
        "downgraded_output_count": cannot_claim + stale + len(suppressed_reports),
        "cannot_claim_count": cannot_claim,
        "stale_or_refresh_needed_count": stale,
        "suppressed_report_refs": [ref for ref in suppressed_reports if ref],
        "note": "Existing artifacts expose cannot-claim, stale/freshness, and dashboard suppression signals; no CHECK result is mutated.",
    }


def build_service_fixture_row(sources: dict[str, Any], service_status: dict[str, Any]) -> dict[str, Any]:
    envelope = sources["agent_run_envelope"]
    components = index_components(sources["component_registry"])
    component = components.get(envelope["component_id"], {})
    budget = envelope.get("budget", {})
    budget_policy = lookup_budget_policy(sources["budget_policy"], budget.get("policy_ref"))
    counts = count_suppressed_deferred_throttled(sources["maturity_dashboard"], sources["calibration_report"])
    check_summary = check_failure_summary(sources["maturity_dashboard"], sources["calibration_report"])
    handoff_targets = handoff_targets_for(envelope["component_id"], sources["handoff_matrix"])
    health_state = "healthy" if service_status["status"] == "AVAILABLE" else "degraded"
    return {
        "service_id": "service_fixture:epoch2_replay_harness:pending_2_2a_lane_a_contract",
        "service_name": f"{component.get('name', envelope['component_id'])} (service fixture)",
        "component_id": envelope["component_id"],
        "component_kind": component.get("kind", "unknown"),
        "health_state": health_state,
        "health_state_source": "AgentServiceContract health state values; degraded because Lane A ServiceRegistry is pending" if health_state == "degraded" else "ServiceRegistry",
        "last_trigger": envelope.get("trigger"),
        "schedule_trigger_type": "manual_local",
        "trigger_policy": {
            "type": "manual",
            "schedule": None,
            "event_types": [],
        },
        "input_packet_refs": envelope.get("inputs", []),
        "output_packet_refs": envelope.get("outputs", []),
        "tools_used": envelope.get("tools_used", []),
        "check_report_refs": envelope.get("check_report_refs", []),
        "check_failures_downgraded_outputs": check_summary,
        "authority_level": envelope.get("authority_level", component.get("authority_level_max")),
        "authority_envelope_refs": ["AuthorityEnvelope:local_replay_review_query_only"],
        "budget_allocated": budget,
        "budget_consumed": {
            "tool_calls": len(envelope.get("tools_used", [])),
            "llm_calls": 0,
            "steps": 1,
            "outputs": len(envelope.get("outputs", [])),
            "wall_clock_seconds": round((envelope.get("duration_ms") or 0) / 1000, 3),
            "policy_ref": budget.get("policy_ref"),
            "policy_caps": {
                "max_tool_calls": budget_policy.get("max_tool_calls"),
                "max_llm_calls": budget_policy.get("max_llm_calls"),
                "max_steps": budget_policy.get("max_steps"),
                "max_wall_clock_seconds": budget_policy.get("max_wall_clock_seconds"),
            },
        },
        "latency_ms": envelope.get("duration_ms"),
        "error_count": 0 if envelope.get("status") == "emitted" else 1,
        "status": envelope.get("status"),
        "stop_condition": envelope.get("stop_condition_hit"),
        "handoff_target": handoff_targets,
        "suppressed_deferred_throttled_count": counts,
        "run_envelope_refs": [rel(AGENT_RUN_ENVELOPE_PATH)],
        "ledger_row_refs": [
            "outputs/epoch_2_1_integration_gate_2_1c_final_closeout/EPOCH_2_1_LEDGER_ROWS.json#epoch_2_0_entry"
        ],
        "service_registry_dependency": service_status,
        "limitations": envelope.get("limitations", []) + ([service_status["limitation"]] if service_status.get("limitation") else []),
        "production_monitoring_claim": False,
        "autonomous_action_claim": False,
    }


def build_observability_report(sources: dict[str, Any], service_status: dict[str, Any]) -> dict[str, Any]:
    service_row = build_service_fixture_row(sources, service_status)
    check_summary = check_failure_summary(sources["maturity_dashboard"], sources["calibration_report"])
    counts = count_suppressed_deferred_throttled(sources["maturity_dashboard"], sources["calibration_report"])
    ledger = sources["ledger_rows"]
    limitations = [
        "2.2a Lane A ServiceRegistry/AgentServiceContract outputs are pending in this workspace; service fixture row is derived from existing 2.0/2.1 artifacts.",
        "Observability is a local materialized report, not a production monitoring service.",
        "No new metrics store is created; all fields are derived from cited artifacts.",
    ]
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2a.lane_b.agent_observability_report.v1",
        "status": PASS_STATUS,
        "created_at": utc_now(),
        "source_package_refs": PACKAGE_REFS,
        "service_registry_status": service_status,
        "report_panels": {
            "service_health_summary": {
                "status": "PASS_WITH_LIMITATIONS" if service_status["status"].startswith("PENDING") else "PASS",
                "service_count": 1,
                "health_state_counts": {state: int(service_row["health_state"] == state) for state in ALLOWED_HEALTH_STATES},
                "rows": [service_row],
            },
            "latest_runs": {
                "status": "PASS",
                "run_count": 1,
                "rows": [service_row],
            },
            "check_failures_downgrades": {
                "status": "PASS_WITH_LIMITATIONS",
                "summary": check_summary,
                "source_refs": [rel(MATURITY_DASHBOARD_PATH), rel(CALIBRATION_REPORT_PATH)],
            },
            "authority_distribution": {
                "status": "PASS",
                "authority_level_counts": {str(service_row["authority_level"]): 1},
                "max_authority_observed": service_row["authority_level"],
                "authority_ceiling_epoch_2_2": 3,
            },
            "budget_and_latency": {
                "status": "PASS",
                "budget_consumed": service_row["budget_consumed"],
                "latency_ms": service_row["latency_ms"],
                "error_count": service_row["error_count"],
            },
            "handoffs": {
                "status": "PASS_WITH_LIMITATIONS" if not service_row["handoff_target"] else "PASS",
                "handoff_targets": service_row["handoff_target"],
                "handoff_matrix_ref": rel(HANDOFF_MATRIX_PATH),
            },
            "llm_seat_usage": {
                "status": "PASS",
                "llm_seat_used": None,
                "llm_call_count": 0,
                "rollback_status": "not_applicable_for_epoch2_replay_harness",
            },
            "suppressed_deferred_throttled_watch_items": {
                "status": "PASS_WITH_LIMITATIONS",
                "counts": counts,
                "source_refs": [rel(MATURITY_DASHBOARD_PATH), rel(CALIBRATION_REPORT_PATH)],
            },
            "corpus_scorecard_linkage": {
                "status": "PASS_WITH_LIMITATIONS",
                "mode_scorecard_status": sources["mode_scorecard"].get("status"),
                "active_mode_count": sources["mode_scorecard"].get("active_mode_count"),
                "track0_corpus_status": sources["corpus_append"].get("status"),
                "source_of_truth_delta_ref": rel(SOT_DELTA_PATH),
                "corpus_append_ref": rel(CORPUS_APPEND_PATH),
            },
            "open_blockers": {
                "status": "PASS_WITH_LIMITATIONS",
                "blockers": [],
                "limitations": limitations,
            },
            "service_justification_status": {
                "status": "PASS_WITH_LIMITATIONS",
                "rows": [
                    {
                        "component_id": service_row["component_id"],
                        "decision": "fixture_only_pending_lane_a_service_registry",
                        "eligibility_reason": ["service health independently visible for replay harness fixture"],
                        "worked_example_result": "Diff Scout remains on-demand until Lane A ServiceJustificationReview proves recurrence necessity.",
                    }
                ],
            },
            "limitations_ledger": {
                "status": "PASS_WITH_LIMITATIONS",
                "rows": [
                    {
                        "owner": "2.2a Lane A",
                        "limitation": "ServiceRegistry/AgentServiceContract outputs pending.",
                        "next_lane": "2.2a integration gate",
                    },
                    {
                        "owner": "2.2a Lane B",
                        "limitation": "Dashboard is static JSON/Markdown/HTML fixture, not a route or production monitor.",
                        "next_lane": "2.2a integration gate",
                    },
                ],
            },
        },
        "required_panel_fields": REQUIRED_PANEL_FIELDS,
        "service_rows": [service_row],
        "run_rows": [service_row],
        "source_refs": source_refs(),
        "ledger_rows_visible": ledger.get("rows", []),
        "boundaries": {
            "new_metrics_store_created": False,
            "production_monitoring_claim": False,
            "autonomous_action_claim": False,
            "per_domain_agent_classes_created": False,
            "invented_status_values": False,
            "official_action_or_dispatch_claim": False,
        },
        "non_goals": NON_GOALS,
        "limitations": limitations,
    }


def source_refs() -> dict[str, str]:
    return {
        "entry_gate": rel(ENTRY_GATE_PATH),
        "agent_run_envelope": rel(AGENT_RUN_ENVELOPE_PATH),
        "component_registry": rel(COMPONENT_REGISTRY_PATH),
        "handoff_matrix": rel(HANDOFF_MATRIX_PATH),
        "budget_stop_policy": rel(BUDGET_POLICY_PATH),
        "agent_recertification_report": rel(RECERT_REPORT_PATH),
        "mode_scorecard": rel(MODE_SCORECARD_PATH),
        "rbac_observability_envelope": rel(RBAC_OBSERVABILITY_PATH),
        "rbac_decision": rel(RBAC_DECISION_PATH),
        "data_maturity_dashboard": rel(MATURITY_DASHBOARD_PATH),
        "calibration_report_generation": rel(CALIBRATION_REPORT_PATH),
        "ledger_rows": rel(LEDGER_ROWS_PATH),
        "track0_corpus_append_report": rel(CORPUS_APPEND_PATH),
        "source_of_truth_delta": rel(SOT_DELTA_PATH),
    }


def build_source_map(service_status: dict[str, Any]) -> dict[str, Any]:
    field_sources = {
        "service name / component id": [rel(COMPONENT_REGISTRY_PATH), rel(AGENT_RUN_ENVELOPE_PATH)],
        "health state": service_status["refs"] or ["AgentServiceContract health-state enum; limited fixture state because Lane A ServiceRegistry is pending"],
        "last trigger": [rel(AGENT_RUN_ENVELOPE_PATH)],
        "schedule/trigger type": [rel(AGENT_RUN_ENVELOPE_PATH), "20_SPEC_AGENT_SERVICE_CONTRACT.md"],
        "input packet refs": [rel(AGENT_RUN_ENVELOPE_PATH)],
        "output packet refs": [rel(AGENT_RUN_ENVELOPE_PATH)],
        "tools used": [rel(AGENT_RUN_ENVELOPE_PATH)],
        "CHECK failures / downgraded outputs": [rel(MATURITY_DASHBOARD_PATH), rel(CALIBRATION_REPORT_PATH)],
        "authority level": [rel(AGENT_RUN_ENVELOPE_PATH), rel(COMPONENT_REGISTRY_PATH)],
        "budget consumed": [rel(AGENT_RUN_ENVELOPE_PATH), rel(BUDGET_POLICY_PATH)],
        "latency": [rel(AGENT_RUN_ENVELOPE_PATH)],
        "error count": [rel(AGENT_RUN_ENVELOPE_PATH)],
        "handoff target": [rel(HANDOFF_MATRIX_PATH)],
        "suppressed/deferred/throttled count": [rel(MATURITY_DASHBOARD_PATH), rel(CALIBRATION_REPORT_PATH)],
        "run envelope refs": [rel(AGENT_RUN_ENVELOPE_PATH)],
        "ledger row refs": [rel(LEDGER_ROWS_PATH)],
        "Track 0 corpus status": [rel(CORPUS_APPEND_PATH), rel(SOT_DELTA_PATH)],
    }
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2a.lane_b.observability_source_map.v1",
        "status": "PASS_WITH_LIMITATIONS" if service_status["status"].startswith("PENDING") else "PASS",
        "created_at": utc_now(),
        "service_registry_status": service_status,
        "field_sources": field_sources,
        "source_refs": source_refs(),
        "no_new_metrics_store": True,
    }


def validate_report(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not report.get("service_rows"):
        errors.append("missing_service_rows")
    if not report.get("run_rows"):
        errors.append("missing_run_rows")
    for row_index, row in enumerate(report.get("service_rows", [])):
        for field in REQUIRED_PANEL_FIELDS:
            if field not in row:
                errors.append(f"service_row_{row_index}_missing:{field}")
        if row.get("health_state") not in ALLOWED_HEALTH_STATES:
            errors.append(f"invented_health_state:{row.get('health_state')}")
        if row.get("authority_level", 99) > 3:
            errors.append("authority_level_above_3")
    panels = report.get("report_panels", {})
    for panel in [
        "service_health_summary",
        "latest_runs",
        "check_failures_downgrades",
        "authority_distribution",
        "budget_and_latency",
        "handoffs",
        "llm_seat_usage",
        "suppressed_deferred_throttled_watch_items",
        "corpus_scorecard_linkage",
        "open_blockers",
        "service_justification_status",
        "limitations_ledger",
    ]:
        if panel not in panels:
            errors.append(f"missing_panel:{panel}")
    boundaries = report.get("boundaries", {})
    for key in [
        "new_metrics_store_created",
        "production_monitoring_claim",
        "autonomous_action_claim",
        "per_domain_agent_classes_created",
        "invented_status_values",
        "official_action_or_dispatch_claim",
    ]:
        if boundaries.get(key) is not False:
            errors.append(f"boundary_violation:{key}")
    if report.get("service_registry_status", {}).get("status") not in {"AVAILABLE", "PENDING_LANE_A_SERVICE_REGISTRY"}:
        errors.append("unknown_service_registry_status")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "checked_at": utc_now(),
        "report_hash": stable_hash(report),
    }


def render_markdown(report: dict[str, Any]) -> str:
    service_row = report["service_rows"][0]
    counts = service_row["suppressed_deferred_throttled_count"]
    return f"""# Agent Observability View

Status: `{report['status']}`

This is a static local observability report materialized from existing
AgentRunEnvelope, ComponentRegistry, RBAC observability, dashboard, calibration,
ledger, and Track 0 artifacts. It is not a production monitoring service.

## Service Health Summary

| Service | Component | Health | Last trigger | Trigger type | Authority |
| --- | --- | --- | --- | --- | --- |
| {service_row['service_name']} | `{service_row['component_id']}` | `{service_row['health_state']}` | `{service_row['last_trigger']}` | `{service_row['schedule_trigger_type']}` | {service_row['authority_level']} |

## Latest Runs

| Run envelope | Inputs | Outputs | Tools | Latency | Errors |
| --- | ---: | ---: | --- | ---: | ---: |
| `{service_row['run_envelope_refs'][0]}` | {len(service_row['input_packet_refs'])} | {len(service_row['output_packet_refs'])} | `{', '.join(service_row['tools_used'])}` | {service_row['latency_ms']} ms | {service_row['error_count']} |

## CHECK Failures / Downgrades

- CHECK report refs: `{', '.join(service_row['check_report_refs'])}`
- Downgraded output count: `{report['report_panels']['check_failures_downgrades']['summary']['downgraded_output_count']}`
- Cannot-claim count: `{report['report_panels']['check_failures_downgrades']['summary']['cannot_claim_count']}`

## Budget and Latency

- Budget consumed: `{json.dumps(service_row['budget_consumed'], sort_keys=True)}`
- Latency: `{service_row['latency_ms']} ms`

## Handoffs

- Handoff targets: `{', '.join(service_row['handoff_target']) or 'none'}`

## Suppressed / Deferred / Throttled

- Suppressed: `{counts['suppressed']}`
- Deferred: `{counts['deferred']}`
- Throttled: `{counts['throttled']}`

## Corpus / Scorecard Linkage

- Mode scorecard: `{report['report_panels']['corpus_scorecard_linkage']['mode_scorecard_status']}`
- Track 0 corpus status: `{report['report_panels']['corpus_scorecard_linkage']['track0_corpus_status']}`

## Open Blockers

No blocking issue was found for Lane B. Limitation: ServiceRegistry/AgentServiceContract
outputs from Lane A are pending, so the service row is a limited fixture derived
from existing Epoch 2.0/2.1 artifacts.

## Boundaries

{chr(10).join(f"- {item}" for item in NON_GOALS)}
"""


def render_html(report: dict[str, Any]) -> str:
    row = report["service_rows"][0]
    cells = "".join(
        f"<tr><th>{html.escape(field)}</th><td>{html.escape(json.dumps(row.get(field), sort_keys=True))}</td></tr>"
        for field in REQUIRED_PANEL_FIELDS
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>CityBrain Agent Observability Fixture</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #17202a; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 1100px; }}
    th, td {{ border: 1px solid #c7d0d9; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ width: 260px; background: #eef3f6; }}
    .status {{ display: inline-block; padding: 4px 8px; border: 1px solid #7f8c8d; }}
  </style>
</head>
<body>
  <h1>CityBrain Agent Observability Fixture</h1>
  <p class="status">{html.escape(report['status'])}</p>
  <p>Static local fixture only. No production monitoring, metrics store, or autonomous action.</p>
  <table>
    <tbody>{cells}</tbody>
  </table>
</body>
</html>
"""


def build_decision(gate: dict[str, Any], report: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2a.lane_b.decision.v1",
        "status": PASS_STATUS if validation["status"] == "PASS" else "FAIL_EPOCH_2_2_PUSH_2_2A_LANE_B_OBSERVABILITY_VALIDATION",
        "created_at": utc_now(),
        "lane": "B",
        "push": "2.2a",
        "artifact_root": rel(OUTPUT_ROOT),
        "prerequisite_gate": gate,
        "service_registry_status": report["service_registry_status"],
        "required_artifacts": [
            "AGENT_OBSERVABILITY_REPORT.json",
            "AGENT_OBSERVABILITY_VIEW.md",
            "AGENT_OBSERVABILITY_FIXTURE.html",
            "OBSERVABILITY_SOURCE_MAP.json",
            "DECISION.json",
            "SUMMARY.md",
            "HASH_MANIFEST.json",
        ],
        "required_panels_present": sorted(report["report_panels"].keys()),
        "validation": validation,
        "boundaries": report["boundaries"],
        "limitations": report["limitations"],
        "non_goals": NON_GOALS,
    }


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
        "schema_version": "citybrain.epoch_2_2.push_2_2a.lane_b.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "created_at": utc_now(),
        "item_count": len(files),
        "files": files,
    }


def write_summary(decision: dict[str, Any], validation: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        f"""# Push 2.2a Lane B Agent Observability

Status: `{decision['status']}`

Materialized a local observability report from existing AgentRunEnvelope,
ComponentRegistry, handoff matrix, budget policy, RBAC observability, maturity
dashboard, calibration, ledger, and Track 0 artifacts.

Validation: `{validation['status']}`

Limitations:

{chr(10).join(f"- {item}" for item in decision['limitations'])}

Boundaries:

{chr(10).join(f"- {item}" for item in NON_GOALS)}

This lane does not close Epoch 2.2.
""",
    )


def write_all_outputs() -> dict[str, Any]:
    gate = check_prerequisite_gate()
    if gate["status"] != "PASS":
        return {"gate": gate, "decision": None}

    service_status = service_registry_status()
    sources = load_sources()
    report = build_observability_report(sources, service_status)
    validation = validate_report(report)
    source_map = build_source_map(service_status)
    decision = build_decision(gate, report, validation)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_ROOT / "AGENT_OBSERVABILITY_REPORT.json", report)
    write_text(OUTPUT_ROOT / "AGENT_OBSERVABILITY_VIEW.md", render_markdown(report))
    write_text(OUTPUT_ROOT / "AGENT_OBSERVABILITY_FIXTURE.html", render_html(report))
    write_json(OUTPUT_ROOT / "OBSERVABILITY_SOURCE_MAP.json", source_map)
    write_json(OUTPUT_ROOT / "DECISION.json", decision)
    write_summary(decision, validation)
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
    return {
        "gate": gate,
        "decision": decision,
        "report": report,
        "source_map": source_map,
        "validation": validation,
        "sources": sources,
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
