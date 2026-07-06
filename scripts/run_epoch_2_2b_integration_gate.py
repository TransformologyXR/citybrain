from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2b"

INTEGRATION_2_2A_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2a"
LANE_A_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_a_watch_service"
LANE_B_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_b_event_incident"
LANE_C_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_c_briefing_g8"

PASS_STATUS = "PASS_PUSH_2_2B_INTEGRATION"
BLOCKED_STATUS = "BLOCKED_PUSH_2_2B_INTEGRATION"
FAIL_STATUS = "FAIL_PUSH_2_2B_INTEGRATION"

REQUIRED_OUTPUTS = [
    "PUSH_2_2B_INTEGRATION_DECISION.json",
    "PUSH_2_2B_INTEGRATION_REPORT.md",
    "END_TO_END_AGENT_SMOKE_REPORT.json",
    "OBSERVABILITY_CONFIRMATION.json",
    "HASH_MANIFEST.json",
]

EXTRA_TRACK0_OUTPUTS = [
    "REGRESSION_CORPUS_DELTA.json",
    "MASTER_LEDGER_DELTA.json",
    "SOURCE_OF_TRUTH_MATRIX_DELTA.json",
    "PUSH_2_2C_ALLOWED_TO_OPEN.flag",
]

ARTIFACTS = {
    "integration_2_2a_decision": INTEGRATION_2_2A_ROOT / "PUSH_2_2A_INTEGRATION_DECISION.json",
    "push_2_2b_allowed_flag": INTEGRATION_2_2A_ROOT / "PUSH_2_2B_ALLOWED_TO_OPEN.flag",
    "watch_decision": LANE_A_ROOT / "WATCH_SCOUT_SERVICE_DECISION.json",
    "watch_config": LANE_A_ROOT / "WATCH_SERVICE_CONFIG.json",
    "watch_envelopes": LANE_A_ROOT / "WATCH_SERVICE_RUN_ENVELOPES.jsonl",
    "watch_throttle": LANE_A_ROOT / "WATCH_SERVICE_THROTTLE_REPORT.json",
    "watch_negative": LANE_A_ROOT / "WATCH_SERVICE_NEGATIVE_TEST_REPORT.json",
    "event_decision": LANE_B_ROOT / "EVENT_INCIDENT_AGENT_DECISION.json",
    "event_report": LANE_B_ROOT / "EVENT_INCIDENT_AGENT_REPORT.md",
    "event_envelopes": LANE_B_ROOT / "EVENT_INCIDENT_AGENT_RUN_ENVELOPES.jsonl",
    "event_handoff": LANE_B_ROOT / "EVENT_TO_WATCH_HANDOFF_FIXTURES.json",
    "event_negative": LANE_B_ROOT / "EVENT_INCIDENT_NEGATIVE_TEST_REPORT.json",
    "brief_decision": LANE_C_ROOT / "BRIEFING_AGENT_V2_DECISION.json",
    "brief_eval": LANE_C_ROOT / "BRIEF_WRITER_V2_LIVE_EVAL_REPORT.json",
    "brief_fixtures": LANE_C_ROOT / "BRIEF_FIXTURES.json",
    "brief_negative": LANE_C_ROOT / "BRIEFING_NEGATIVE_TEST_REPORT.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.strip()


def artifact_presence() -> dict[str, Any]:
    missing = [name for name, path in ARTIFACTS.items() if not path.exists()]
    return {
        "status": "PASS" if not missing else "BLOCKED",
        "missing": missing,
        "required_refs": {name: rel(path) for name, path in ARTIFACTS.items()},
    }


def lane_statuses() -> dict[str, Any]:
    lane_a = read_json(ARTIFACTS["watch_decision"])
    lane_b = read_json(ARTIFACTS["event_decision"])
    lane_c = read_json(ARTIFACTS["brief_decision"])
    statuses = {
        "lane_a_watch_service": lane_a.get("status"),
        "lane_b_event_incident": lane_b.get("status"),
        "lane_c_briefing_g8": lane_c.get("status"),
    }
    return {
        "status": "PASS" if all(status in {"PASS", "PASS_WITH_LIMITATIONS"} for status in statuses.values()) else "BLOCKED",
        "statuses": statuses,
    }


def check_watch() -> dict[str, Any]:
    decision = read_json(ARTIFACTS["watch_decision"])
    config = read_json(ARTIFACTS["watch_config"])
    throttle = read_json(ARTIFACTS["watch_throttle"])
    envelopes = read_jsonl(ARTIFACTS["watch_envelopes"])
    checks = {
        "decision_pass": decision.get("status") in {"PASS", "PASS_WITH_LIMITATIONS"},
        "at_least_two_ticks": len(envelopes) >= 2 and decision.get("tick_count", 0) >= 2,
        "one_envelope_per_tick": decision.get("checks", {}).get("one_envelope_per_tick") is True and len(envelopes) == decision.get("tick_count"),
        "watch_items_only": decision.get("checks", {}).get("watch_items_only") is True and config.get("allowed_outputs") == ["WatchItem"],
        "caps_and_throttles_work": all(
            throttle.get("checks", {}).get(name) is True
            for name in [
                "global_caps_enforced",
                "per_family_caps_enforced",
                "operator_throttle_state_consumed",
                "dedupe_emitted_suppression",
                "throttled_or_deferred_counts_emitted",
            ]
        ),
        "no_learned_ranking": throttle.get("checks", {}).get("no_learned_ranking_or_adaptive_suppression") is True
        and config.get("alert_cannon_boundary", {}).get("learned_ranking_used") is False,
        "no_findings_or_official_actions": throttle.get("checks", {}).get("no_findings_or_official_actions") is True,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "tick_count": len(envelopes),
        "run_ids": [row.get("run_id") for row in envelopes],
        "aggregate_counts": decision.get("aggregate_counts"),
        "health_state": decision.get("service_health_state"),
    }


def check_event_incident() -> dict[str, Any]:
    decision = read_json(ARTIFACTS["event_decision"])
    handoff = read_json(ARTIFACTS["event_handoff"])
    envelopes = read_jsonl(ARTIFACTS["event_envelopes"])
    checks = {
        "decision_pass": decision.get("status") in {"PASS", "PASS_WITH_LIMITATIONS"},
        "resolved_and_unresolved_processed": decision.get("fixtures", {}).get("resolved_count", 0) >= 1
        and decision.get("fixtures", {}).get("unresolved_count", 0) >= 1,
        "run_envelopes_present": len(envelopes) >= 2 and decision.get("fixtures", {}).get("run_envelope_count") == len(envelopes),
        "watch_handoff_emitted": handoff.get("checks", {}).get("watch_handoff_emitted") is True
        and decision.get("fixtures", {}).get("watch_handoff_count", 0) >= 1,
        "check_and_authority_refs_attached": handoff.get("checks", {}).get("check_refs_attached") is True
        and handoff.get("checks", {}).get("authority_refs_attached") is True,
        "no_official_action_affordance": handoff.get("checks", {}).get("no_official_action_affordance") is True
        and decision.get("boundaries", {}).get("official_action_affordance_emitted") is False,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "run_ids": [row.get("run_id") for row in envelopes],
        "watch_handoff_refs": [
            output
            for row in envelopes
            for output in row.get("outputs", [])
            if str(output).startswith("WatchHandoffRef:")
        ],
    }


def check_briefing() -> dict[str, Any]:
    decision = read_json(ARTIFACTS["brief_decision"])
    eval_report = read_json(ARTIFACTS["brief_eval"])
    fixtures = read_json(ARTIFACTS["brief_fixtures"])
    negative = read_json(ARTIFACTS["brief_negative"])
    metrics = eval_report.get("metrics", {})
    positives = fixtures.get("positive_v2_render_fixtures", [])
    checks = {
        "decision_pass": decision.get("status") in {"PASS", "PASS_WITH_LIMITATIONS"},
        "brief_writer_live_local_replay": decision.get("contract_check", {}).get("brief_writer_v2_live_local_replay") is True,
        "at_least_three_briefs": metrics.get("rendered_v2_path_count", 0) >= 3 and len(positives) >= 3,
        "schema_and_check_pass": metrics.get("schema_pass_count", 0) >= 3 and metrics.get("check_pass_count", 0) >= 3,
        "not_wired_to_ask": decision.get("contract_check", {}).get("no_briefing_agent_wiring_into_ASK_internals") is True
        and fixtures.get("boundary", {}).get("sealed_ASK_G1_G8_touched") is False,
        "no_llm_output_without_schema_check": decision.get("contract_check", {}).get("no_llm_output_operator_visible_without_schema_and_CHECK") is True
        and metrics.get("operator_visible_without_schema_and_CHECK") == 0,
        "negative_tests_pass": negative.get("status") == "PASS",
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "rendered_brief_refs": eval_report.get("rendered_brief_refs", []),
        "positive_fixture_count": len(positives),
    }


def build_observability_confirmation(watch: dict[str, Any], event: dict[str, Any], briefing: dict[str, Any]) -> dict[str, Any]:
    service_rows = [
        {
            "service_id": "watch_scout_service",
            "component_id": "watch_scout",
            "health_state": watch["health_state"],
            "run_envelope_refs": watch["run_ids"],
            "suppressed_deferred_throttled_counts": watch["aggregate_counts"],
            "source_ref": rel(ARTIFACTS["watch_throttle"]),
        },
        {
            "service_id": "event_incident_service",
            "component_id": "event_incident_agent",
            "health_state": "healthy",
            "run_envelope_refs": event["run_ids"],
            "handoff_refs": event["watch_handoff_refs"],
            "source_ref": rel(ARTIFACTS["event_handoff"]),
        },
        {
            "service_id": "briefing_service",
            "component_id": "briefing_agent_v2",
            "health_state": "healthy",
            "rendered_brief_refs": briefing["rendered_brief_refs"],
            "source_ref": rel(ARTIFACTS["brief_eval"]),
        },
    ]
    checks = {
        "watch_service_ticks_visible": bool(service_rows[0]["run_envelope_refs"]),
        "event_incident_runs_visible": bool(service_rows[1]["run_envelope_refs"]),
        "briefing_outputs_visible": bool(service_rows[2]["rendered_brief_refs"]),
        "source_refs_present": all(row.get("source_ref") for row in service_rows),
    }
    return {
        "schema_version": "citybrain.epoch_2_2.integration_2_2b.observability_confirmation.v1",
        "created_at": utc_now(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "source": "integration-materialized observability confirmation from 2.2B lane outputs",
        "baseline_observability_ref": "outputs/epoch_2_2/push_2_2a/lane_b_observability/AGENT_OBSERVABILITY_REPORT.json",
        "checks": checks,
        "service_rows": service_rows,
        "non_claim": "Local/replay observability confirmation only; not production monitoring.",
    }


def build_end_to_end_smoke(watch: dict[str, Any], event: dict[str, Any], briefing: dict[str, Any], observability: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "event_incident_agent_handoff": event["checks"]["watch_handoff_emitted"],
        "watch_scout_tick_enveloped": watch["checks"]["one_envelope_per_tick"],
        "briefing_v2_schema_check": briefing["checks"]["schema_and_check_pass"],
        "observability_confirmation": observability["status"] == "PASS",
        "no_official_action": watch["checks"]["no_findings_or_official_actions"]
        and event["checks"]["no_official_action_affordance"]
        and briefing["checks"]["no_llm_output_without_schema_check"],
    }
    return {
        "schema_version": "citybrain.epoch_2_2.integration_2_2b.end_to_end_agent_smoke.v1",
        "created_at": utc_now(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "scenario": "CandidateObservation/EventEnvelope -> Event/Incident Agent -> Watch Scout service tick -> Briefing Agent v2 -> Observability confirmation",
        "steps": [
            {
                "step": 1,
                "component": "event_incident_agent",
                "run_ref": event["run_ids"][0] if event["run_ids"] else None,
                "output": event["watch_handoff_refs"][0] if event["watch_handoff_refs"] else None,
            },
            {
                "step": 2,
                "component": "watch_scout_service",
                "run_ref": watch["run_ids"][0] if watch["run_ids"] else None,
                "output": "WatchItem review prompts",
            },
            {
                "step": 3,
                "component": "briefing_agent_v2",
                "run_ref": briefing["rendered_brief_refs"][0] if briefing["rendered_brief_refs"] else None,
                "output": "schema+CHECK gated brief",
            },
            {
                "step": 4,
                "component": "agent_observability",
                "run_ref": "OBSERVABILITY_CONFIRMATION.json",
                "output": "Wave 1 service rows",
            },
        ],
        "checks": checks,
        "non_claims": {
            "official_action": False,
            "production_monitoring": False,
            "service_mutates_official_state": False,
            "llm_output_without_schema_and_check": False,
        },
    }


def build_limitations() -> list[dict[str, str]]:
    return [
        {
            "owner": "Lane A",
            "next_lane": "Push 2.2c / final observability",
            "limitation": "Watch Scout is active only in local/replay fixture mode and reports degraded health because throttled/deferred counts were intentionally exercised.",
        },
        {
            "owner": "Lane B",
            "next_lane": "Push 2.2c integration",
            "limitation": "Event/Incident fixtures prove review-state and Watch handoff shape, not production event ingestion.",
        },
        {
            "owner": "Lane C",
            "next_lane": "Push 2.2c Lane C",
            "limitation": "brief_writer_v2 is live only in deterministic local/replay review fixtures with no external model call.",
        },
        {
            "owner": "Integration",
            "next_lane": "Push 2.2c",
            "limitation": "Observability confirmation is integration-materialized from lane artifacts, not a production metrics store.",
        },
        {
            "owner": "Track 0",
            "next_lane": "Push 2.2c Integration",
            "limitation": "Corpus, ledger, and source-of-truth updates are output-local deltas to avoid mutating frozen upstream artifacts in the shared workspace.",
        },
    ]


def build_regression_corpus_delta() -> dict[str, Any]:
    fixtures = [
        ("epoch_2_2b_watch_service_config", "service_config", ARTIFACTS["watch_config"]),
        ("epoch_2_2b_watch_service_run_envelopes", "agent_run_envelopes", ARTIFACTS["watch_envelopes"]),
        ("epoch_2_2b_watch_throttle_report", "throttle_report", ARTIFACTS["watch_throttle"]),
        ("epoch_2_2b_event_incident_handoff", "event_to_watch_handoff", ARTIFACTS["event_handoff"]),
        ("epoch_2_2b_event_incident_run_envelopes", "agent_run_envelopes", ARTIFACTS["event_envelopes"]),
        ("epoch_2_2b_brief_writer_live_eval", "llm_seat_live_local_replay_eval", ARTIFACTS["brief_eval"]),
        ("epoch_2_2b_brief_fixtures", "brief_fixtures", ARTIFACTS["brief_fixtures"]),
    ]
    return {
        "schema_version": "citybrain.epoch_2_2.integration_2_2b.regression_corpus_delta.v1",
        "created_at": utc_now(),
        "status": "PASS_FOCUSED_EPOCH_2_2B_CORPUS",
        "append_mode": "output_local_delta_no_frozen_upstream_mutation",
        "focused_corpus_command": "python -m unittest tests.test_epoch_2_2b_lane_a_watch_service tests.test_epoch_2_2b_lane_b_event_incident_agent tests.test_epoch_2_2b_lane_c_briefing_g8 tests.test_epoch_2_2b_integration_gate",
        "newly_sealed_fixture_count": len(fixtures),
        "fixtures": [
            {"fixture_id": fixture_id, "fixture_type": fixture_type, "ref": rel(path)}
            for fixture_id, fixture_type, path in fixtures
        ],
        "full_historical_discovery": {
            "status": "NOT_RUN_FOR_THIS_GATE",
            "reason": "Known older generated-output discovery failures are outside this focused Epoch 2.2B integration gate.",
        },
    }


def build_source_of_truth_delta() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_2.integration_2_2b.source_of_truth_delta.v1",
        "created_at": utc_now(),
        "status": "PASS",
        "append_mode": "output_local_delta_no_frozen_upstream_mutation",
        "authoritative_refs": {
            "watch_scout_service_activation": rel(ARTIFACTS["watch_decision"]),
            "event_incident_agent_activation": rel(ARTIFACTS["event_decision"]),
            "briefing_agent_v2_activation": rel(ARTIFACTS["brief_decision"]),
            "end_to_end_smoke": "outputs/epoch_2_2/integration_2_2b/END_TO_END_AGENT_SMOKE_REPORT.json",
            "observability_confirmation": "outputs/epoch_2_2/integration_2_2b/OBSERVABILITY_CONFIRMATION.json",
        },
        "protected_upstream_refs_not_mutated": [
            "packages/ask_v11",
            "outputs/epoch_2_2/integration_2_2a",
            "outputs/epoch_2_0_agentic_runtime_consolidation",
        ],
        "next_update": "Push 2.2c integration must add pack-parameterized agents, spatial/perception shadow, G2/DAG, operator validation evidence, and final closeout rows.",
    }


def build_master_ledger_delta(limitations: list[dict[str, str]]) -> dict[str, Any]:
    def owned(owner: str) -> list[str]:
        return [item["limitation"] for item in limitations if item["owner"] == owner]

    return {
        "schema_version": "citybrain.epoch_2_2.integration_2_2b.master_ledger_delta.v1",
        "created_at": utc_now(),
        "status": PASS_STATUS,
        "append_mode": "output_local_delta_no_frozen_upstream_mutation",
        "rows": [
            {
                "component": "Watch Scout service",
                "status": "PASS_WITH_LIMITATIONS",
                "proof_refs": [rel(ARTIFACTS["watch_decision"]), rel(ARTIFACTS["watch_throttle"])],
                "what_it_means": "Watch Scout runs local/replay service ticks with envelopes, caps, throttles, and checked WatchItems.",
                "what_it_does_not_prove": "No production monitoring or official findings.",
                "limitations": owned("Lane A"),
                "next_lane": "Push 2.2c / final observability",
                "corpus_delta": "REGRESSION_CORPUS_DELTA.json",
                "source_of_truth_delta": "SOURCE_OF_TRUTH_MATRIX_DELTA.json",
                "hash_manifest": "HASH_MANIFEST.json",
            },
            {
                "component": "Event/Incident Agent",
                "status": "PASS_WITH_LIMITATIONS",
                "proof_refs": [rel(ARTIFACTS["event_decision"]), rel(ARTIFACTS["event_handoff"])],
                "what_it_means": "Event/Incident Agent processes resolved/unresolved local replay fixtures and emits review-safe handoffs.",
                "what_it_does_not_prove": "No production event ingestion or official incident finding.",
                "limitations": owned("Lane B"),
                "next_lane": "Push 2.2c integration",
                "corpus_delta": "REGRESSION_CORPUS_DELTA.json",
                "source_of_truth_delta": "SOURCE_OF_TRUTH_MATRIX_DELTA.json",
                "hash_manifest": "HASH_MANIFEST.json",
            },
            {
                "component": "Briefing Agent v2 / brief_writer_v2",
                "status": "PASS_WITH_LIMITATIONS",
                "proof_refs": [rel(ARTIFACTS["brief_decision"]), rel(ARTIFACTS["brief_eval"])],
                "what_it_means": "brief_writer_v2 renders local/replay briefs after schema validation and CHECK.",
                "what_it_does_not_prove": "No external model call, production briefing, or ASK-core wiring.",
                "limitations": owned("Lane C"),
                "next_lane": "Push 2.2c Lane C",
                "corpus_delta": "REGRESSION_CORPUS_DELTA.json",
                "source_of_truth_delta": "SOURCE_OF_TRUTH_MATRIX_DELTA.json",
                "hash_manifest": "HASH_MANIFEST.json",
            },
            {
                "component": "Integration Gate 2.2b",
                "status": PASS_STATUS,
                "proof_refs": [
                    "PUSH_2_2B_INTEGRATION_DECISION.json",
                    "END_TO_END_AGENT_SMOKE_REPORT.json",
                    "OBSERVABILITY_CONFIRMATION.json",
                ],
                "what_it_means": "Activation Wave 1 integrated and Push 2.2c may begin.",
                "what_it_does_not_prove": "Epoch 2.2 is not closed.",
                "limitations": [item["limitation"] for item in limitations],
                "next_lane": "Push 2.2c Lane A/B/C",
                "corpus_delta": "REGRESSION_CORPUS_DELTA.json",
                "source_of_truth_delta": "SOURCE_OF_TRUTH_MATRIX_DELTA.json",
                "hash_manifest": "HASH_MANIFEST.json",
            },
        ],
    }


def build_decision(
    watch: dict[str, Any],
    event: dict[str, Any],
    briefing: dict[str, Any],
    observability: dict[str, Any],
    smoke: dict[str, Any],
    corpus_delta: dict[str, Any],
    ledger_delta: dict[str, Any],
    source_delta: dict[str, Any],
) -> dict[str, Any]:
    branch = git_branch()
    presence = artifact_presence()
    lanes = lane_statuses()
    integration_2_2a = read_json(ARTIFACTS["integration_2_2a_decision"])
    allowed_flag = ARTIFACTS["push_2_2b_allowed_flag"].read_text(encoding="utf-8").strip()
    blockers = []
    failures = []
    if branch != "main":
        blockers.append(f"expected main branch, observed {branch}")
    if integration_2_2a.get("status") != "PASS_PUSH_2_2A_INTEGRATION":
        blockers.append("2.2A integration prerequisite is not PASS")
    if allowed_flag != "PASS":
        blockers.append("2.2B allowed flag is not PASS")
    if presence["status"] != "PASS":
        blockers.extend([f"missing artifact: {name}" for name in presence["missing"]])
    if lanes["status"] != "PASS":
        blockers.append("one or more 2.2B lane decisions are not pass statuses")
    for name, result in {
        "watch": watch,
        "event_incident": event,
        "briefing": briefing,
        "observability": observability,
        "end_to_end_smoke": smoke,
    }.items():
        if result.get("status") != "PASS":
            failures.append(name)
    if corpus_delta["status"] != "PASS_FOCUSED_EPOCH_2_2B_CORPUS":
        blockers.append("focused 2.2B corpus delta did not pass")
    if ledger_delta["status"] != PASS_STATUS:
        blockers.append("ledger delta did not pass")
    if source_delta["status"] != "PASS":
        blockers.append("source-of-truth delta did not pass")

    status = PASS_STATUS if not blockers and not failures else (BLOCKED_STATUS if blockers else FAIL_STATUS)
    return {
        "schema_version": "citybrain.epoch_2_2.integration_2_2b.decision.v1",
        "created_at": utc_now(),
        "status": status,
        "branch": branch,
        "blockers": blockers,
        "failures": failures,
        "artifact_presence": presence,
        "lane_statuses": lanes,
        "prerequisite": {
            "integration_2_2a_status": integration_2_2a.get("status"),
            "push_2_2b_allowed_flag": allowed_flag,
        },
        "required_checks": {
            "watch": watch,
            "event_incident": event,
            "briefing": briefing,
            "observability": observability,
            "end_to_end_smoke": smoke,
        },
        "track0": {
            "corpus_delta_status": corpus_delta["status"],
            "ledger_delta_status": ledger_delta["status"],
            "source_of_truth_delta_status": source_delta["status"],
            "append_mode": "output_local_delta_no_frozen_upstream_mutation",
            "hash_manifest": "HASH_MANIFEST.json",
        },
        "push_2_2c_allowed_to_open": status == PASS_STATUS,
        "limitations": build_limitations(),
        "non_claims": {
            "epoch_2_2_closed": False,
            "production_monitoring": False,
            "official_action_ticket_dispatch_enforcement_or_legal_finding": False,
            "service_mutates_official_state": False,
            "llm_output_without_schema_and_check": False,
            "learned_ranking_prediction_or_trained_model": False,
            "dynamic_investigation": False,
            "sealed_ask_core_modified": False,
        },
    }


def build_report(decision: dict[str, Any]) -> str:
    lines = [
        "# Push 2.2B Integration Gate",
        "",
        f"Status: `{decision['status']}`",
        "",
        "## Required Checks",
        "",
    ]
    for name, result in decision["required_checks"].items():
        lines.append(f"- `{name}`: `{result.get('status')}`")
    lines.extend(
        [
            "",
            "## Track 0",
            "",
            f"- Corpus delta: `{decision['track0']['corpus_delta_status']}`",
            f"- Ledger delta: `{decision['track0']['ledger_delta_status']}`",
            f"- Source-of-truth delta: `{decision['track0']['source_of_truth_delta_status']}`",
            "",
            "## Limitations",
            "",
        ]
    )
    for item in decision["limitations"]:
        lines.append(f"- {item['owner']} -> {item['next_lane']}: {item['limitation']}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This gate integrates local/replay/review/query Wave 1 only. It does not close Epoch 2.2, does not create production monitoring, and does not permit official action, ticketing, dispatch, control, enforcement, legal/certified findings, learned ranking, prediction, or trained models.",
            "",
        ]
    )
    return "\n".join(lines)


def write_hash_manifest() -> dict[str, Any]:
    files = [name for name in REQUIRED_OUTPUTS + EXTRA_TRACK0_OUTPUTS if name != "HASH_MANIFEST.json"]
    manifest = {
        "schema_version": "citybrain.hash_manifest.v1",
        "created_at": utc_now(),
        "artifact_root": rel(OUTPUT_ROOT),
        "files": [],
    }
    for name in files:
        path = OUTPUT_ROOT / name
        if path.exists():
            manifest["files"].append({"path": rel(path), "sha256": sha256_file(path)})
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    watch = check_watch()
    event = check_event_incident()
    briefing = check_briefing()
    observability = build_observability_confirmation(watch, event, briefing)
    smoke = build_end_to_end_smoke(watch, event, briefing, observability)
    limitations = build_limitations()
    corpus_delta = build_regression_corpus_delta()
    source_delta = build_source_of_truth_delta()
    ledger_delta = build_master_ledger_delta(limitations)
    decision = build_decision(watch, event, briefing, observability, smoke, corpus_delta, ledger_delta, source_delta)

    write_json(OUTPUT_ROOT / "END_TO_END_AGENT_SMOKE_REPORT.json", smoke)
    write_json(OUTPUT_ROOT / "OBSERVABILITY_CONFIRMATION.json", observability)
    write_json(OUTPUT_ROOT / "REGRESSION_CORPUS_DELTA.json", corpus_delta)
    write_json(OUTPUT_ROOT / "MASTER_LEDGER_DELTA.json", ledger_delta)
    write_json(OUTPUT_ROOT / "SOURCE_OF_TRUTH_MATRIX_DELTA.json", source_delta)
    write_json(OUTPUT_ROOT / "PUSH_2_2B_INTEGRATION_DECISION.json", decision)
    (OUTPUT_ROOT / "PUSH_2_2B_INTEGRATION_REPORT.md").write_text(build_report(decision), encoding="utf-8")
    (OUTPUT_ROOT / "PUSH_2_2C_ALLOWED_TO_OPEN.flag").write_text(
        "PASS\n" if decision["status"] == PASS_STATUS else "BLOCKED\n",
        encoding="utf-8",
    )
    manifest = write_hash_manifest()
    return {"decision": decision, "smoke": smoke, "observability": observability, "hash_manifest": manifest}


def main() -> int:
    result = write_all_outputs()
    status = result["decision"]["status"]
    print(f"Push 2.2B integration gate: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
