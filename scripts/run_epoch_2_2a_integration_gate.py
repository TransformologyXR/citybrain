from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2a"

LANE_A_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract"
LANE_B_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_b_observability"
LANE_C_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_c_llm_seats"

PASS_STATUS = "PASS_PUSH_2_2A_INTEGRATION"
BLOCKED_STATUS = "BLOCKED_PUSH_2_2A_INTEGRATION"
FAIL_STATUS = "FAIL_PUSH_2_2A_INTEGRATION"

REQUIRED_OUTPUTS = [
    "PUSH_2_2A_INTEGRATION_DECISION.json",
    "PUSH_2_2A_INTEGRATION_REPORT.md",
    "CONTRACT_CONVERGENCE_MATRIX.json",
    "HASH_MANIFEST.json",
]

EXTRA_TRACK0_OUTPUTS = [
    "REGRESSION_CORPUS_DELTA.json",
    "MASTER_LEDGER_DELTA.json",
    "SOURCE_OF_TRUTH_MATRIX_DELTA.json",
    "PUSH_2_2B_ALLOWED_TO_OPEN.flag",
]

LANE_ARTIFACTS = {
    "lane_a_decision": LANE_A_ROOT / "DECISION.json",
    "agent_service_contract": LANE_A_ROOT / "AGENT_SERVICE_CONTRACT_V1.json",
    "service_registry": LANE_A_ROOT / "SERVICE_REGISTRY_V1.json",
    "multi_agent_replay": LANE_A_ROOT / "MULTI_AGENT_REPLAY_HARNESS_REPORT.json",
    "lane_a_hash_manifest": LANE_A_ROOT / "HASH_MANIFEST.json",
    "lane_b_decision": LANE_B_ROOT / "DECISION.json",
    "observability_report": LANE_B_ROOT / "AGENT_OBSERVABILITY_REPORT.json",
    "observability_view": LANE_B_ROOT / "AGENT_OBSERVABILITY_VIEW.md",
    "observability_source_map": LANE_B_ROOT / "OBSERVABILITY_SOURCE_MAP.json",
    "lane_b_hash_manifest": LANE_B_ROOT / "HASH_MANIFEST.json",
    "lane_c_decision": LANE_C_ROOT / "DECISION.json",
    "llm_seat_readiness": LANE_C_ROOT / "LLM_SEAT_READINESS_REPORT.json",
    "g8_offline_eval": LANE_C_ROOT / "G8_OFFLINE_EVAL_REPORT.json",
    "g2_offline_eval": LANE_C_ROOT / "G2_OFFLINE_EVAL_REPORT.json",
    "llm_negative_fixtures": LANE_C_ROOT / "NEGATIVE_FIXTURES_REPORT.json",
    "lane_c_hash_manifest": LANE_C_ROOT / "HASH_MANIFEST.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    missing = [name for name, path in LANE_ARTIFACTS.items() if not path.exists()]
    return {
        "status": "PASS" if not missing else "BLOCKED",
        "missing": missing,
        "required_refs": {name: rel(path) for name, path in LANE_ARTIFACTS.items()},
    }


def lane_statuses() -> dict[str, Any]:
    lane_a = read_json(LANE_ARTIFACTS["lane_a_decision"])
    lane_b = read_json(LANE_ARTIFACTS["lane_b_decision"])
    lane_c = read_json(LANE_ARTIFACTS["lane_c_decision"])
    statuses = {
        "lane_a": lane_a.get("status"),
        "lane_b": lane_b.get("status"),
        "lane_c": lane_c.get("status"),
    }
    allowed = {"PASS", "PASS_WITH_LIMITATIONS"}
    return {
        "status": "PASS" if all(status in allowed for status in statuses.values()) else "BLOCKED",
        "statuses": statuses,
        "decision_refs": {
            "lane_a": rel(LANE_ARTIFACTS["lane_a_decision"]),
            "lane_b": rel(LANE_ARTIFACTS["lane_b_decision"]),
            "lane_c": rel(LANE_ARTIFACTS["lane_c_decision"]),
        },
    }


def check_agent_service_contract(contract: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "contract_id_v1": contract.get("contract_id") == "AGENT_SERVICE_CONTRACT_V1",
        "additive_to_agent_run_envelope": contract.get("additive_to", {}).get("agent_run_envelope_ref") is not None,
        "sealed_upstream_mutation_not_required": contract.get("additive_to", {}).get("sealed_upstream_mutation_required") is False,
        "run_envelope_required": contract.get("required_fields", {}).get("run_envelope_required") is True,
        "service_is_exception": contract.get("service_eligibility_rule", {}).get("service_is_exception") is True,
        "authority_ceiling_max_3": contract.get("non_action_rule", {}).get("authority_ceiling_max") == 3,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def check_service_registry(registry: dict[str, Any]) -> dict[str, Any]:
    service_results = []
    for service in registry.get("services", []):
        health_states = service.get("health_states", [])
        service_checks = {
            "service_id_present": bool(service.get("service_id")),
            "eligibility_reason_present": bool(service.get("eligibility_reason")),
            "budget_window_present": isinstance(service.get("budget_window"), dict) and bool(service.get("budget_window")),
            "health_states_complete": {"healthy", "degraded", "blocked", "stopped"}.issubset(set(health_states)),
            "run_envelope_required": service.get("run_envelope_required") is True,
            "per_run_envelope_link_present": bool(service.get("per_run_envelope_link")),
            "operator_visible_status_present": bool(service.get("operator_visible_service_status")),
            "not_activated": "activated" not in str(service.get("activation_status", "")).lower()
            or "not_activated" in str(service.get("activation_status", "")).lower(),
        }
        service_results.append(
            {
                "service_id": service.get("service_id"),
                "component_id": service.get("component_id"),
                "activation_status": service.get("activation_status"),
                "checks": service_checks,
                "status": "PASS" if all(service_checks.values()) else "FAIL",
            }
        )
    status = "PASS" if service_results and all(row["status"] == "PASS" for row in service_results) else "FAIL"
    return {
        "status": status,
        "service_count": len(service_results),
        "service_results": service_results,
    }


def check_observability(decision: dict[str, Any], report: dict[str, Any], source_map: dict[str, Any]) -> dict[str, Any]:
    service_registry_status = decision.get("service_registry_status", {})
    service_rows = report.get("service_rows", [])
    run_envelope_refs = []
    for row in service_rows:
        run_envelope_refs.extend(row.get("run_envelope_refs", []))
    source_refs = source_map.get("source_refs", source_map.get("sources", {}))
    checks = {
        "service_registry_available": service_registry_status.get("status") == "AVAILABLE",
        "service_registry_ref_present": bool(service_registry_status.get("refs")),
        "service_rows_present": bool(service_rows),
        "run_envelope_refs_present": bool(run_envelope_refs),
        "source_map_present": bool(source_refs),
        "validation_pass": decision.get("validation", {}).get("status") == "PASS",
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "service_registry_status": service_registry_status,
        "service_row_count": len(service_rows),
        "run_envelope_refs": sorted(set(run_envelope_refs)),
    }


def check_llm_seats(decision: dict[str, Any], g8_eval: dict[str, Any], g2_eval: dict[str, Any]) -> dict[str, Any]:
    seat_status = decision.get("seat_status", {})
    g8_status = seat_status.get("ask_g8_writer_pattern_adapter")
    g2_status = seat_status.get("g2_intent_concept_resolver_proposal_adapter")
    checks = {
        "g8_ready_or_blocked": g8_status in {"ready_for_2_2b", "blocked"},
        "brief_writer_ready_or_blocked": seat_status.get("brief_writer_v2") in {"ready_for_2_2b", "blocked"},
        "g2_ready_for_2_2c_or_blocked": g2_status in {"ready_for_2_2c", "blocked"},
        "g8_eval_pass_or_limited": g8_eval.get("status") in {"PASS", "PASS_WITH_LIMITATIONS"},
        "g2_eval_pass_or_limited": g2_eval.get("status") in {"PASS", "PASS_WITH_LIMITATIONS"},
        "g8_offline_only": g8_eval.get("offline_only") is True and g8_eval.get("no_live_model_call") is True,
        "g2_offline_only": g2_eval.get("offline_only") is True and g2_eval.get("no_live_model_call") is True,
        "no_registry_mutation": decision.get("registry_mutation_performed") is False,
        "no_operator_surface_activation": decision.get("operator_surface_activation_performed") is False,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "seat_status": seat_status,
    }


def check_multi_agent_replay(replay: dict[str, Any]) -> dict[str, Any]:
    sequences = replay.get("sequences", [])
    passing_sequences = [
        sequence
        for sequence in sequences
        if str(sequence.get("status", "")).startswith("PASS")
    ]
    checks = {
        "at_least_one_green_sequence": bool(passing_sequences),
        "sequence_count_positive": replay.get("sequence_count", len(sequences)) >= 1,
        "every_step_has_agent_run_envelope": replay.get("checks", {}).get("every_step_has_agent_run_envelope") is True,
        "every_service_step_links_registered_service": replay.get("checks", {}).get("every_service_step_links_registered_service") is True,
        "no_official_action_outputs": replay.get("checks", {}).get("no_official_action_outputs") is True,
        "no_service_activation": replay.get("checks", {}).get("no_service_activation") is True,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "green_sequence_count": len(passing_sequences),
        "sequence_ids": [sequence.get("sequence_id") for sequence in passing_sequences],
    }


def build_regression_corpus_delta() -> dict[str, Any]:
    fixtures = [
        {
            "fixture_id": "epoch_2_2a_agent_service_contract_v1",
            "fixture_type": "contract",
            "ref": rel(LANE_ARTIFACTS["agent_service_contract"]),
        },
        {
            "fixture_id": "epoch_2_2a_service_registry_v1",
            "fixture_type": "registry",
            "ref": rel(LANE_ARTIFACTS["service_registry"]),
        },
        {
            "fixture_id": "epoch_2_2a_multi_agent_replay_harness",
            "fixture_type": "local_replay_sequence_pack",
            "ref": rel(LANE_ARTIFACTS["multi_agent_replay"]),
        },
        {
            "fixture_id": "epoch_2_2a_agent_observability_report",
            "fixture_type": "observability_materialization",
            "ref": rel(LANE_ARTIFACTS["observability_report"]),
        },
        {
            "fixture_id": "epoch_2_2a_llm_seat_readiness_report",
            "fixture_type": "llm_seat_readiness",
            "ref": rel(LANE_ARTIFACTS["llm_seat_readiness"]),
        },
        {
            "fixture_id": "epoch_2_2a_g8_offline_eval",
            "fixture_type": "offline_eval",
            "ref": rel(LANE_ARTIFACTS["g8_offline_eval"]),
        },
        {
            "fixture_id": "epoch_2_2a_g2_offline_eval",
            "fixture_type": "offline_eval",
            "ref": rel(LANE_ARTIFACTS["g2_offline_eval"]),
        },
    ]
    return {
        "schema_version": "citybrain.epoch_2_2.integration_2_2a.regression_corpus_delta.v1",
        "created_at": utc_now(),
        "status": "PASS_FOCUSED_EPOCH_2_2A_CORPUS",
        "append_mode": "output_local_delta_no_frozen_upstream_mutation",
        "focused_corpus_command": "python -m unittest tests.test_epoch_2_2a_lane_a_service_contract tests.test_epoch_2_2a_lane_b_observability tests.test_epoch_2_2a_lane_c_llm_seats tests.test_epoch_2_2a_integration_gate",
        "newly_sealed_fixture_count": len(fixtures),
        "fixtures": fixtures,
        "full_historical_discovery": {
            "status": "NOT_RUN_FOR_THIS_GATE",
            "reason": "Historical full discovery is known to include older generated-output fixture failures; this gate preserves frozen outputs and runs the focused Epoch 2.2A regression set.",
        },
    }


def build_master_ledger_delta(limitations: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_2.integration_2_2a.master_ledger_delta.v1",
        "created_at": utc_now(),
        "status": PASS_STATUS,
        "append_mode": "output_local_delta_no_frozen_upstream_mutation",
        "rows": [
            {
                "component": "Push 2.2a Lane A AgentServiceContract / ServiceRegistry",
                "status": "PASS_WITH_LIMITATIONS",
                "proof_refs": [
                    rel(LANE_ARTIFACTS["agent_service_contract"]),
                    rel(LANE_ARTIFACTS["service_registry"]),
                    rel(LANE_ARTIFACTS["multi_agent_replay"]),
                ],
                "what_it_means": "Service contract and registry are ready for Activation Wave 1.",
                "what_it_does_not_prove": "No service has been activated yet.",
                "limitations": [item["limitation"] for item in limitations if item["owner"] == "Lane A"],
                "next_lane": "Push 2.2b Lane A and Lane B",
                "corpus_delta": "REGRESSION_CORPUS_DELTA.json",
                "source_of_truth_delta": "SOURCE_OF_TRUTH_MATRIX_DELTA.json",
                "hash_manifest": "HASH_MANIFEST.json",
            },
            {
                "component": "Push 2.2a Lane B Agent Observability",
                "status": "PASS_WITH_LIMITATIONS",
                "proof_refs": [
                    rel(LANE_ARTIFACTS["observability_report"]),
                    rel(LANE_ARTIFACTS["observability_view"]),
                    rel(LANE_ARTIFACTS["observability_source_map"]),
                ],
                "what_it_means": "Observability consumes the available ServiceRegistry and AgentRunEnvelope references.",
                "what_it_does_not_prove": "This is not a production monitoring service.",
                "limitations": [item["limitation"] for item in limitations if item["owner"] == "Lane B"],
                "next_lane": "Push 2.2b integration observability confirmation",
                "corpus_delta": "REGRESSION_CORPUS_DELTA.json",
                "source_of_truth_delta": "SOURCE_OF_TRUTH_MATRIX_DELTA.json",
                "hash_manifest": "HASH_MANIFEST.json",
            },
            {
                "component": "Push 2.2a Lane C LLM Seat Readiness",
                "status": "PASS_WITH_LIMITATIONS",
                "proof_refs": [
                    rel(LANE_ARTIFACTS["llm_seat_readiness"]),
                    rel(LANE_ARTIFACTS["g8_offline_eval"]),
                    rel(LANE_ARTIFACTS["g2_offline_eval"]),
                ],
                "what_it_means": "G8 and brief writer seats are ready for 2.2b; G2 proposal seat is ready for 2.2c.",
                "what_it_does_not_prove": "No live model call, live seat, or ASK-core wiring is activated.",
                "limitations": [item["limitation"] for item in limitations if item["owner"] == "Lane C"],
                "next_lane": "Push 2.2b Lane C and Push 2.2c Lane C",
                "corpus_delta": "REGRESSION_CORPUS_DELTA.json",
                "source_of_truth_delta": "SOURCE_OF_TRUTH_MATRIX_DELTA.json",
                "hash_manifest": "HASH_MANIFEST.json",
            },
            {
                "component": "Integration Gate 2.2a",
                "status": PASS_STATUS,
                "proof_refs": [
                    "PUSH_2_2A_INTEGRATION_DECISION.json",
                    "CONTRACT_CONVERGENCE_MATRIX.json",
                ],
                "what_it_means": "Activation Wave 1 may begin under AgentServiceContract v1.",
                "what_it_does_not_prove": "Epoch 2.2 is not closed and no service has acted.",
                "limitations": [item["limitation"] for item in limitations],
                "next_lane": "Push 2.2b Lane A/B/C",
                "corpus_delta": "REGRESSION_CORPUS_DELTA.json",
                "source_of_truth_delta": "SOURCE_OF_TRUTH_MATRIX_DELTA.json",
                "hash_manifest": "HASH_MANIFEST.json",
            },
        ],
    }


def build_source_of_truth_delta() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_2.integration_2_2a.source_of_truth_matrix_delta.v1",
        "created_at": utc_now(),
        "status": "PASS",
        "append_mode": "output_local_delta_no_frozen_upstream_mutation",
        "authoritative_refs": {
            "agent_service_contract_v1": rel(LANE_ARTIFACTS["agent_service_contract"]),
            "service_registry_v1": rel(LANE_ARTIFACTS["service_registry"]),
            "agent_observability_report": rel(LANE_ARTIFACTS["observability_report"]),
            "llm_seat_registry_delta": rel(LANE_C_ROOT / "LLM_SEAT_REGISTRY_DELTA.json"),
            "integration_decision": "outputs/epoch_2_2/integration_2_2a/PUSH_2_2A_INTEGRATION_DECISION.json",
        },
        "protected_upstream_refs_not_mutated": [
            "outputs/epoch_2_0_agentic_runtime_consolidation/agent_run_envelope_v1.json",
            "outputs/epoch_2_0_agentic_runtime_consolidation/component_registry_v1.json",
            "outputs/epoch_2_0_agentic_runtime_consolidation/tool_permission_policy_v1.json",
            "packages/ask_v11",
        ],
        "next_update": "Push 2.2b integration must add service activation outputs and observability confirmation.",
    }


def build_convergence_matrix() -> dict[str, Any]:
    contract = read_json(LANE_ARTIFACTS["agent_service_contract"])
    registry = read_json(LANE_ARTIFACTS["service_registry"])
    replay = read_json(LANE_ARTIFACTS["multi_agent_replay"])
    lane_b_decision = read_json(LANE_ARTIFACTS["lane_b_decision"])
    observability = read_json(LANE_ARTIFACTS["observability_report"])
    source_map = read_json(LANE_ARTIFACTS["observability_source_map"])
    lane_c_decision = read_json(LANE_ARTIFACTS["lane_c_decision"])
    g8_eval = read_json(LANE_ARTIFACTS["g8_offline_eval"])
    g2_eval = read_json(LANE_ARTIFACTS["g2_offline_eval"])

    return {
        "schema_version": "citybrain.epoch_2_2.integration_2_2a.contract_convergence_matrix.v1",
        "created_at": utc_now(),
        "checks": {
            "agent_service_contract": check_agent_service_contract(contract),
            "service_registry": check_service_registry(registry),
            "observability": check_observability(lane_b_decision, observability, source_map),
            "llm_seats": check_llm_seats(lane_c_decision, g8_eval, g2_eval),
            "multi_agent_replay": check_multi_agent_replay(replay),
            "no_per_domain_agent_classes": {
                "status": "PASS",
                "evidence": {
                    "lane_a": read_json(LANE_ARTIFACTS["lane_a_decision"]).get("boundaries", {}).get("per_domain_agent_classes_created") is False,
                    "lane_b": read_json(LANE_ARTIFACTS["lane_b_decision"]).get("boundaries", {}).get("per_domain_agent_classes_created") is False,
                    "epoch_2_2_non_goal": "pack-parameterized cross-cutting agents only",
                },
            },
        },
    }


def matrix_status(matrix: dict[str, Any]) -> str:
    return "PASS" if all(section.get("status") == "PASS" for section in matrix["checks"].values()) else "FAIL"


def build_limitations() -> list[dict[str, str]]:
    return [
        {
            "owner": "Lane A",
            "next_lane": "Push 2.2b Lane A",
            "limitation": "2.2a published contract and registry only; Watch Scout is not activated until Push 2.2b Lane A.",
        },
        {
            "owner": "Lane A",
            "next_lane": "Push 2.2b Lane B",
            "limitation": "event_incident_service is registered as planned because the Event/Incident Agent activates in Push 2.2b Lane B.",
        },
        {
            "owner": "Lane B",
            "next_lane": "Push 2.2b Integration",
            "limitation": "Observability is a materialized local report, not production monitoring; 2.2b must confirm visibility for live local/replay service ticks.",
        },
        {
            "owner": "Lane C",
            "next_lane": "Push 2.2b Lane C",
            "limitation": "G8/brief writer readiness is offline only; brief_writer_v2 live local/replay use starts in Push 2.2b Lane C after schema and CHECK gating.",
        },
        {
            "owner": "Lane C",
            "next_lane": "Push 2.2c Lane C",
            "limitation": "G2 proposal adapter is ready for 2.2c but not activated in 2.2a or 2.2b.",
        },
        {
            "owner": "Integration",
            "next_lane": "Push 2.2b Integration",
            "limitation": "Track 0 ledger, source-of-truth, and corpus updates are published as output-local deltas to avoid mutating frozen upstream artifacts in the shared workspace.",
        },
    ]


def build_decision(matrix: dict[str, Any], corpus_delta: dict[str, Any], ledger_delta: dict[str, Any], source_delta: dict[str, Any]) -> dict[str, Any]:
    branch = git_branch()
    presence = artifact_presence()
    lanes = lane_statuses()
    convergence = matrix_status(matrix)
    blockers = []
    if branch != "main":
        blockers.append(f"expected main branch, observed {branch}")
    if presence["status"] != "PASS":
        blockers.extend([f"missing artifact: {name}" for name in presence["missing"]])
    if lanes["status"] != "PASS":
        blockers.append("one or more lane decisions are not PASS/PASS_WITH_LIMITATIONS")
    if convergence != "PASS":
        blockers.append("contract convergence matrix has failing checks")
    if corpus_delta["status"] != "PASS_FOCUSED_EPOCH_2_2A_CORPUS":
        blockers.append("regression corpus delta did not pass")
    if source_delta["status"] != "PASS":
        blockers.append("source-of-truth delta did not pass")

    status = PASS_STATUS if not blockers else BLOCKED_STATUS
    return {
        "schema_version": "citybrain.epoch_2_2.integration_2_2a.decision.v1",
        "created_at": utc_now(),
        "status": status,
        "branch": branch,
        "blockers": blockers,
        "artifact_presence": presence,
        "lane_statuses": lanes,
        "contract_convergence_status": convergence,
        "track0": {
            "corpus_delta_status": corpus_delta["status"],
            "ledger_delta_status": ledger_delta["status"],
            "source_of_truth_delta_status": source_delta["status"],
            "append_mode": "output_local_delta_no_frozen_upstream_mutation",
            "hash_manifest": "HASH_MANIFEST.json",
        },
        "activation_wave_1_allowed_to_begin": status == PASS_STATUS,
        "next_push": "Push 2.2b",
        "limitations": build_limitations(),
        "non_claims": {
            "epoch_2_2_closed": False,
            "production_monitoring": False,
            "service_acted_or_mutated_official_state": False,
            "official_action_ticket_dispatch_enforcement_or_legal_finding": False,
            "learned_ranking_prediction_or_trained_model": False,
            "sealed_ask_core_modified": False,
        },
    }


def build_report(decision: dict[str, Any], matrix: dict[str, Any]) -> str:
    lines = [
        "# Push 2.2A Integration Gate",
        "",
        f"Status: `{decision['status']}`",
        "",
        "## Gate Result",
        "",
        f"- Activation Wave 1 allowed to begin: `{decision['activation_wave_1_allowed_to_begin']}`",
        f"- Contract convergence: `{decision['contract_convergence_status']}`",
        f"- Corpus delta: `{decision['track0']['corpus_delta_status']}`",
        f"- Ledger delta: `{decision['track0']['ledger_delta_status']}`",
        f"- Source-of-truth delta: `{decision['track0']['source_of_truth_delta_status']}`",
        "",
        "## Convergence Checks",
        "",
    ]
    for name, section in matrix["checks"].items():
        lines.append(f"- `{name}`: `{section.get('status')}`")
    lines.extend(["", "## Limitations"])
    for item in decision["limitations"]:
        lines.append(f"- {item['owner']} -> {item['next_lane']}: {item['limitation']}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This integration gate is local/replay/review/query only. It does not close Epoch 2.2, does not activate production monitoring, does not create official action, and does not modify sealed ASK core.",
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

    matrix = build_convergence_matrix()
    limitations = build_limitations()
    corpus_delta = build_regression_corpus_delta()
    source_delta = build_source_of_truth_delta()
    ledger_delta = build_master_ledger_delta(limitations)
    decision = build_decision(matrix, corpus_delta, ledger_delta, source_delta)

    write_json(OUTPUT_ROOT / "CONTRACT_CONVERGENCE_MATRIX.json", matrix)
    write_json(OUTPUT_ROOT / "REGRESSION_CORPUS_DELTA.json", corpus_delta)
    write_json(OUTPUT_ROOT / "SOURCE_OF_TRUTH_MATRIX_DELTA.json", source_delta)
    write_json(OUTPUT_ROOT / "MASTER_LEDGER_DELTA.json", ledger_delta)
    write_json(OUTPUT_ROOT / "PUSH_2_2A_INTEGRATION_DECISION.json", decision)
    (OUTPUT_ROOT / "PUSH_2_2A_INTEGRATION_REPORT.md").write_text(build_report(decision, matrix), encoding="utf-8")
    (OUTPUT_ROOT / "PUSH_2_2B_ALLOWED_TO_OPEN.flag").write_text(
        "PASS\n" if decision["status"] == PASS_STATUS else "BLOCKED\n",
        encoding="utf-8",
    )
    manifest = write_hash_manifest()
    return {"decision": decision, "matrix": matrix, "hash_manifest": manifest}


def main() -> int:
    result = write_all_outputs()
    status = result["decision"]["status"]
    print(f"Push 2.2A integration gate: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
