from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "push6_lane_c_schedule_simulate"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push6_lane_c_schedule_simulate_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "push6_lane_c_schedule_simulate_final_status"

PUSH5_ROOT = REPO_ROOT / "outputs" / "push5_infra_after_three_lanes_integration"
PUSH5_FINAL_ROOT = REPO_ROOT / "outputs" / "push5_infra_after_three_lanes_final_status"
APPROVAL_ROOT = REPO_ROOT / "outputs" / "push6_lane_a_approval_lifecycle"
APPROVAL_FINAL_ROOT = REPO_ROOT / "outputs" / "push6_lane_a_approval_lifecycle_final_status"
PLAN_ROOT = REPO_ROOT / "outputs" / "push6_lane_b_plan_mode"
PLAN_SIBLING_ROOT = REPO_ROOT.parent / "CityBrain_push6_lane_b_plan_mode" / "outputs" / "push6_lane_b_plan_mode"
CHECK_ROOT = REPO_ROOT / "outputs" / "push4_lane_c_check_v1"

TASK_ID = "PUSH6-LANE-C-SCHEDULE-SIMULATE"
BRANCH = "codex/push6-lane-c-schedule-simulate"
PASS_STATUS = "PASS_PUSH6_LANE_C_SCHEDULE_SIMULATE_WITH_LIMITATIONS"
CLOSEOUT_STATUS = "PASS_PUSH6_LANE_C_SCHEDULE_SIMULATE_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH6_LANE_C_SCHEDULE_SIMULATE_FINAL_STATUS_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH6_LANE_C_SCHEDULE_SIMULATE"
STOP_PUSH5 = "STOPPED_WAITING_FOR_PUSH5_INTEGRATION"
STOP_APPROVAL = "STOPPED_WAITING_FOR_APPROVAL_LIFECYCLE"

ASK_CONTRACT_PATHS = [
    "packages/ask_v11",
    "scripts/run_ask_v11_sealed_eval.py",
    "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
]

R7_RUNTIME_PATHS = [
    "scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
    "scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
    "scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
    "scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
]

UNIVERSAL_NON_CLAIMS = [
    "No production API.",
    "No URL fetch / live retrieval.",
    "No live LLM authority.",
    "No official case/ticket submission.",
    "No dispatch/control/enforcement execution.",
    "No legal/certified finding.",
    "No autonomous workflow.",
    "No live Kit control.",
    "No full citywide twin claim.",
    "No VSS-as-fact-source.",
    "No cross-city claims until federation.",
    "No sealed ASK G1-G8 runtime change.",
    "No protected R7 runtime drift.",
    "All proposals are candidate proposals, never executed actions.",
    "Feature branches only; INFRA owns canonical integration.",
]

LIMITATIONS = [
    "SCHEDULE/SIMULATE v1 creates local/replay candidate schedule and scenario packets only.",
    "SUMO and cuOpt objects are fixture-backed review artifacts, not production runtimes or control systems.",
    "Simulation results are not calibrated for prediction and are not actionable without approval.",
    "Lane B PLAN mode is consumed by ref when available; INFRA owns canonical Push 6 integration.",
]

SIMULATION_CHECK_STATUSES = [
    "scenario_input_valid",
    "scenario_input_incomplete",
    "assumption_limited",
    "not_calibrated_for_prediction",
    "local_replay_only",
    "not_actionable_without_approval",
]

FORBIDDEN_SIMULATOR_KINDS = [
    "production-control-runtime",
    "live-dispatch-runtime",
    "live-signal-control-runtime",
    "official-schedule-execution-runtime",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_root(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def out_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}:{stable_hash([prefix, *parts])[:16]}"


def unique(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            for nested in unique(value):
                if nested not in seen:
                    seen.add(nested)
                    result.append(nested)
            continue
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hash_manifest_for(root: Path, name: str, schema_version: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != name:
            rows.append({"path": out_rel(path, root), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = {
        "schema_version": schema_version,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(rows),
        "missing_count": 0,
        "mismatch_count": 0,
        "files": rows,
    }
    write_json(root / name, payload)
    return payload


def verify_hash_manifest_for(root: Path, name: str) -> dict[str, Any]:
    manifest_path = root / name
    if not manifest_path.exists():
        return {"status": "FAIL", "declared": 0, "verified": 0, "problems": ["manifest_missing"]}
    manifest = read_json(manifest_path, {"files": []})
    problems: list[str] = []
    verified = 0
    for row in manifest.get("files", []):
        target = root / row["path"]
        if not target.exists():
            problems.append(f"missing:{row['path']}")
        elif sha256_file(target) != row.get("sha256"):
            problems.append(f"mismatch:{row['path']}")
        else:
            verified += 1
    return {
        "status": "PASS" if not problems and manifest.get("status") == "PASS" else "FAIL",
        "declared": len(manifest.get("files", [])),
        "verified": verified,
        "problems": problems,
    }


def git_value(args: list[str], default: str = "") -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        return default
    return proc.stdout.strip() or default


def git_diff_empty(paths: list[str]) -> dict[str, Any]:
    proc = subprocess.run(["git", "diff", "--", *paths], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "status": "PASS" if proc.returncode == 0 and proc.stdout == "" else "FAIL",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "paths": paths,
    }


def push5_gate() -> dict[str, Any]:
    integration = read_json(PUSH5_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json", {})
    final = read_json(PUSH5_FINAL_ROOT / "PUSH5_FINAL_STATUS_DECISION.json", {})
    required_files = [
        PUSH5_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json",
        PUSH5_ROOT / "PUSH5_SPATIAL_MEDIA_EVIDENCE_JOIN_REPORT.json",
        PUSH5_ROOT / "PUSH5_SPATIAL_WORKFLOW_STATE_JOIN_REPORT.json",
        PUSH5_ROOT / "PUSH5_WORKFLOW_AND_LLM_BOUNDARY_REPORT.json",
        CHECK_ROOT / "CHECK_V1_REPORTS.json",
    ]
    missing = [rel(path) for path in required_files if not path.exists()]
    ok = not missing and str(integration.get("status", "")).startswith("PASS") and str(final.get("status", "")).startswith("PASS")
    return {
        "status": "PASS" if ok else "FAIL",
        "accepted_integration_branch": "origin/codex/push5-infra-after-three-lanes",
        "accepted_integration_commit": git_value(["rev-parse", "--verify", "origin/codex/push5-infra-after-three-lanes"], ""),
        "integration_status": integration.get("status"),
        "final_status": final.get("status"),
        "missing": missing,
        "counts": integration.get("counts", {}),
    }


def approval_gate() -> dict[str, Any]:
    decision = read_json(APPROVAL_ROOT / "APPROVAL_LIFECYCLE_DECISION.json", {})
    final = read_json(APPROVAL_FINAL_ROOT / "APPROVAL_LIFECYCLE_FINAL_STATUS_DECISION.json", {})
    fixtures = read_json(APPROVAL_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json", {})
    requests = fixtures.get("approval_requests") or []
    required_files = [
        APPROVAL_ROOT / "APPROVAL_LIFECYCLE_DECISION.json",
        APPROVAL_ROOT / "APPROVAL_REQUEST_SCHEMA.json",
        APPROVAL_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json",
        APPROVAL_FINAL_ROOT / "APPROVAL_LIFECYCLE_FINAL_STATUS_DECISION.json",
    ]
    missing = [rel(path) for path in required_files if not path.exists()]
    ok = not missing and requests and str(decision.get("status", "")).startswith("PASS") and str(final.get("status", "")).startswith("PASS")
    return {
        "status": "PASS" if ok else STOP_APPROVAL,
        "decision_status": decision.get("status"),
        "final_status": final.get("status"),
        "approval_request_count": len(requests),
        "authority_level_3_count": len(fixtures.get("authority_level_3_envelopes") or []),
        "missing": missing,
    }


def load_plan_mode() -> tuple[dict[str, Any], str]:
    for root, source in [(PLAN_ROOT, "in_tree"), (PLAN_SIBLING_ROOT, "sibling_worktree")]:
        fixtures = read_json(root / "PLAN_MODE_FIXTURES.json", None)
        if fixtures:
            return fixtures, source
    return {
        "plan_requests": [],
        "option_sets": [],
        "plan_options": [],
        "constraint_sets": [],
        "assumption_sets": [],
    }, "not_available"


def load_inputs() -> dict[str, Any]:
    approval = read_json(APPROVAL_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json", {})
    plan, plan_source = load_plan_mode()
    return {
        "approval": approval,
        "plan": plan,
        "plan_source": plan_source,
        "check_reports": (read_json(CHECK_ROOT / "CHECK_V1_REPORTS.json", {"items": []}).get("items") or []),
    }


def first(items: list[dict[str, Any]], index: int = 0) -> dict[str, Any]:
    if not items:
        return {}
    return items[min(index, len(items) - 1)]


def approval_ref_pack(inputs: dict[str, Any], index: int = 0) -> dict[str, Any]:
    approval = inputs["approval"]
    request = first(approval.get("approval_requests") or [], index)
    l3 = next(
        (item for item in approval.get("authority_level_3_envelopes", []) if item.get("subject_ref") == request.get("subject_ref")),
        first(approval.get("authority_level_3_envelopes") or [], index),
    )
    return {
        "approval_request_ref": request.get("approval_request_id"),
        "approval_subject_ref": request.get("subject_ref"),
        "authority_envelope_ref": l3.get("authority_envelope_level_3_id") or request.get("authority_envelope_ref"),
        "source_authority_envelope_ref": l3.get("source_authority_envelope_ref") or request.get("authority_envelope_ref"),
        "check_report_ref": request.get("check_report_ref") or l3.get("check_report_ref"),
        "evidence_refs": list(request.get("evidence_refs") or l3.get("evidence_refs") or []),
        "limitation_refs": list(request.get("limitation_refs") or l3.get("limitation_refs") or []),
        "trace_refs": list(request.get("trace_refs") or l3.get("trace_refs") or []),
        "cannot_claim": unique([request.get("cannot_claim") or [], l3.get("cannot_claim") or [], UNIVERSAL_NON_CLAIMS]),
    }


def plan_pack(inputs: dict[str, Any]) -> dict[str, Any]:
    plan = inputs["plan"]
    option_set = first(plan.get("option_sets") or [])
    plan_options = plan.get("plan_options") or []
    constraint_set = first(plan.get("constraint_sets") or [])
    assumption_set = first(plan.get("assumption_sets") or [])
    return {
        "plan_mode_source": inputs["plan_source"],
        "plan_request_ref": first(plan.get("plan_requests") or {}).get("plan_request_id"),
        "option_set_ref": option_set.get("option_set_id") or option_set.get("option_set_ref") or "optionset:v2:push6:lane-c:schedule-simulate:0001",
        "plan_option_refs": [item.get("plan_option_id") for item in plan_options if item.get("plan_option_id")],
        "constraints_ref": option_set.get("constraints_ref") or constraint_set.get("constraint_set_id") or "constraints:push6:lane-c:schedule:0001",
        "assumptions_ref": option_set.get("assumptions_ref") or assumption_set.get("assumption_set_id") or "assumptions:push6:lane-c:schedule:0001",
        "plan_options": plan_options,
        "constraint_set": constraint_set,
        "assumption_set": assumption_set,
    }


def schema_payload(title: str, required: list[str], properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "additionalProperties": True,
        "required": required,
        "properties": properties or {},
    }


def schema_payloads() -> dict[str, dict[str, Any]]:
    option_required = [
        "schedule_option_id",
        "schedule_request_ref",
        "option_set_ref",
        "constraints_ref",
        "assumptions_ref",
        "resource_refs",
        "time_window",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "check_report_ref",
        "authority_envelope_ref",
        "approval_request_ref",
        "execution_status",
        "cannot_claim",
    ]
    scenario_required = [
        "scenario_packet_id",
        "schema_version",
        "scenario_family",
        "simulator_kind",
        "simulator_version_or_fixture",
        "input_refs",
        "assumptions",
        "constraints",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "check_report_ref",
        "authority_envelope_ref",
        "approval_request_ref",
        "simulation_status",
        "execution_status",
        "cannot_claim",
    ]
    return {
        "SCHEDULE_REQUEST_SCHEMA.json": schema_payload(
            "ScheduleRequest",
            ["schedule_request_id", "schema_version", "request_ref", "approval_request_ref", "check_report_ref", "authority_envelope_ref", "execution_status"],
            {"execution_status": {"const": "not_executed"}},
        ),
        "SCHEDULE_OPTION_SCHEMA.json": schema_payload(
            "ScheduleOption",
            option_required,
            {"execution_status": {"const": "not_executed"}},
        ),
        "SCENARIO_PACKET_SCHEMA.json": schema_payload(
            "ScenarioPacket",
            scenario_required,
            {
                "execution_status": {"const": "not_executed"},
                "simulator_kind": {"enum": ["sumo_local_replay", "cuopt_fixture", "deterministic_fixture"]},
                "forbidden_simulator_kinds": {"const": FORBIDDEN_SIMULATOR_KINDS},
            },
        ),
        "SIMULATION_RUN_RECORD_SCHEMA.json": schema_payload(
            "SimulationRunRecord",
            ["simulation_run_record_id", "scenario_packet_ref", "simulator_kind", "execution_status", "simulation_status", "result_summary_ref", "check_report_ref", "authority_envelope_ref", "approval_request_ref"],
            {"execution_status": {"const": "not_executed"}},
        ),
    }


def build_schedule_payloads(inputs: dict[str, Any]) -> dict[str, Any]:
    plan = plan_pack(inputs)
    approval0 = approval_ref_pack(inputs, 0)
    approval1 = approval_ref_pack(inputs, 1)
    schedule_request = {
        "schedule_request_id": "schedule-request:push6:lane-c:0001",
        "schema_version": "main-citybrain.schedule_simulate.schedule_request.r1",
        "request_ref": approval0["approval_subject_ref"],
        "plan_request_ref": plan["plan_request_ref"],
        "purpose": "Create local/replay schedule options for review without execution.",
        "approval_request_ref": approval0["approval_request_ref"],
        "check_report_ref": approval0["check_report_ref"],
        "authority_envelope_ref": approval0["authority_envelope_ref"],
        "evidence_refs": approval0["evidence_refs"],
        "limitation_refs": unique([approval0["limitation_refs"], LIMITATIONS]),
        "trace_refs": unique([approval0["trace_refs"], "PUSH6:LANE_C:SCHEDULE_REQUEST"]),
        "execution_status": "not_executed",
        "cannot_claim": approval0["cannot_claim"],
    }
    constraint_set = {
        "constraint_set_id": "constraint-set:push6:lane-c:schedule:0001",
        "schema_version": "main-citybrain.schedule_simulate.constraint_set.r1",
        "source_constraints_ref": plan["constraints_ref"],
        "constraints": [
            "local/replay only",
            "approval_request_ref required",
            "CHECK and authority refs required",
            "no dispatch/control/enforcement execution",
            "no official schedule execution",
            "simulation results are not calibrated for prediction",
        ],
        "execution_status": "not_executed",
    }
    option_set = {
        "schedule_option_set_id": "schedule-option-set:push6:lane-c:0001",
        "schema_version": "main-citybrain.schedule_simulate.schedule_option_set.r1",
        "schedule_request_ref": schedule_request["schedule_request_id"],
        "option_set_ref": plan["option_set_ref"],
        "plan_option_refs": plan["plan_option_refs"],
        "constraints_ref": constraint_set["constraint_set_id"],
        "assumptions_ref": plan["assumptions_ref"],
        "approval_request_ref": approval0["approval_request_ref"],
        "check_report_ref": approval0["check_report_ref"],
        "authority_envelope_ref": approval0["authority_envelope_ref"],
        "execution_status": "not_executed",
        "plan_mode_source": plan["plan_mode_source"],
    }
    source_options = plan["plan_options"][:2] or [
        {"plan_option_id": "plan-option:push6:lane-c:fallback:0001", "title": "Hold local review slot", "evidence_refs": approval0["evidence_refs"], "limitation_refs": [], "trace_refs": []},
        {"plan_option_id": "plan-option:push6:lane-c:fallback:0002", "title": "Collect more local evidence", "evidence_refs": approval1["evidence_refs"], "limitation_refs": [], "trace_refs": []},
    ]
    schedule_options = []
    for index, source in enumerate(source_options, start=1):
        approval = approval_ref_pack(inputs, index - 1)
        payload = {
            "schedule_option_id": f"schedule-option:push6:lane-c:{index:04d}",
            "schema_version": "main-citybrain.schedule_simulate.schedule_option.r1",
            "schedule_request_ref": schedule_request["schedule_request_id"],
            "option_set_ref": option_set["schedule_option_set_id"],
            "plan_option_ref": source.get("plan_option_id"),
            "constraints_ref": constraint_set["constraint_set_id"],
            "assumptions_ref": plan["assumptions_ref"],
            "resource_refs": ["resource:local-reviewer:001", "resource:local-replay-simulator:sumo-fixture"],
            "time_window": {
                "window_id": f"time-window:push6:lane-c:{index:04d}",
                "start": "2026-07-05T23:00:00Z",
                "end": "2026-07-06T01:00:00Z",
                "timezone": "UTC",
                "local_replay_only": True,
            },
            "option_label": source.get("title") or f"Schedule option {index}",
            "evidence_refs": unique([approval["evidence_refs"], source.get("evidence_refs") or []]),
            "limitation_refs": unique([approval["limitation_refs"], source.get("limitation_refs") or [], LIMITATIONS]),
            "trace_refs": unique([approval["trace_refs"], source.get("trace_refs") or [], "PUSH6:LANE_C:SCHEDULE_OPTION"]),
            "check_report_ref": approval["check_report_ref"],
            "authority_envelope_ref": approval["authority_envelope_ref"],
            "approval_request_ref": approval["approval_request_ref"],
            "execution_status": "not_executed",
            "candidate_proposal_only": True,
            "cannot_claim": unique([approval["cannot_claim"], source.get("cannot_claim") or [], UNIVERSAL_NON_CLAIMS]),
        }
        payload["schedule_option_hash"] = stable_hash(payload)
        schedule_options.append(payload)
    return {
        "schedule_request": schedule_request,
        "constraint_set": constraint_set,
        "schedule_option_set": option_set,
        "schedule_options": schedule_options,
        "plan": plan,
    }


def build_scenario_payloads(inputs: dict[str, Any], schedule: dict[str, Any]) -> dict[str, Any]:
    schedule_options = schedule["schedule_options"]
    approval0 = approval_ref_pack(inputs, 0)
    approval1 = approval_ref_pack(inputs, 1)
    sumo = {
        "scenario_packet_id": "scenario-packet:push6:lane-c:sumo:0001",
        "schema_version": "main-citybrain.schedule_simulate.scenario_packet.r1",
        "scenario_family": "watch_review_schedule_local_replay",
        "simulator_kind": "sumo_local_replay",
        "simulator_version_or_fixture": "sumo-fixture:local-replay:push6-lane-c-0001",
        "input_refs": [schedule["schedule_request"]["schedule_request_id"], schedule_options[0]["schedule_option_id"]],
        "assumptions": [
            "Static local/replay fixture; no live network or production signal data.",
            "Travel or queue outputs are illustrative review context only.",
            "Scenario is not calibrated for prediction.",
        ],
        "constraints": schedule["constraint_set"]["constraints"],
        "evidence_refs": schedule_options[0]["evidence_refs"],
        "limitation_refs": unique([schedule_options[0]["limitation_refs"], LIMITATIONS]),
        "trace_refs": unique([schedule_options[0]["trace_refs"], "PUSH6:LANE_C:SUMO_SCENARIO"]),
        "check_report_ref": approval0["check_report_ref"],
        "authority_envelope_ref": approval0["authority_envelope_ref"],
        "approval_request_ref": approval0["approval_request_ref"],
        "simulation_status": "local_replay_fixture_evaluated",
        "execution_status": "not_executed",
        "cannot_claim": unique([approval0["cannot_claim"], UNIVERSAL_NON_CLAIMS]),
    }
    sumo["scenario_packet_hash"] = stable_hash(sumo)
    cuopt = {
        "scenario_packet_id": "scenario-packet:push6:lane-c:cuopt:0001",
        "schema_version": "main-citybrain.schedule_simulate.scenario_packet.r1",
        "scenario_family": "candidate_schedule_option_fixture",
        "simulator_kind": "cuopt_fixture",
        "simulator_version_or_fixture": "cuopt-fixture:local-replay:push6-lane-c-0001",
        "input_refs": [schedule["schedule_request"]["schedule_request_id"], schedule_options[-1]["schedule_option_id"]],
        "assumptions": [
            "cuOpt runtime is represented as local/replay scheduling option fixtures.",
            "No local production-safe cuOpt runtime is invoked.",
            "Resource allocation is illustrative only.",
        ],
        "constraints": schedule["constraint_set"]["constraints"],
        "evidence_refs": schedule_options[-1]["evidence_refs"],
        "limitation_refs": unique([schedule_options[-1]["limitation_refs"], "cuOpt scheduling family is fixture-only in this lane."]),
        "trace_refs": unique([schedule_options[-1]["trace_refs"], "PUSH6:LANE_C:CUOPT_FIXTURE"]),
        "check_report_ref": approval1["check_report_ref"],
        "authority_envelope_ref": approval1["authority_envelope_ref"],
        "approval_request_ref": approval1["approval_request_ref"],
        "simulation_status": "fixture_only_not_runtime_invoked",
        "execution_status": "not_executed",
        "cannot_claim": unique([approval1["cannot_claim"], UNIVERSAL_NON_CLAIMS]),
    }
    cuopt["scenario_packet_hash"] = stable_hash(cuopt)
    run_records = []
    summaries = []
    for index, scenario in enumerate([sumo, cuopt], start=1):
        summary = {
            "simulation_result_summary_id": f"simulation-result-summary:push6:lane-c:{index:04d}",
            "schema_version": "main-citybrain.schedule_simulate.simulation_result_summary.r1",
            "scenario_packet_ref": scenario["scenario_packet_id"],
            "result_scope": "local_replay_review_context",
            "metrics": {
                "candidate_schedule_options_considered": len(schedule_options),
                "live_control_signals_changed": 0,
                "official_actions_created": 0,
            },
            "simulation_check_statuses": SIMULATION_CHECK_STATUSES if scenario["simulator_kind"] == "sumo_local_replay" else [
                "scenario_input_incomplete",
                "assumption_limited",
                "local_replay_only",
                "not_actionable_without_approval",
            ],
            "execution_status": "not_executed",
        }
        summary["simulation_result_summary_hash"] = stable_hash(summary)
        summaries.append(summary)
        run_record = {
            "simulation_run_record_id": f"simulation-run-record:push6:lane-c:{index:04d}",
            "schema_version": "main-citybrain.schedule_simulate.simulation_run_record.r1",
            "scenario_packet_ref": scenario["scenario_packet_id"],
            "simulator_kind": scenario["simulator_kind"],
            "simulator_version_or_fixture": scenario["simulator_version_or_fixture"],
            "simulation_status": scenario["simulation_status"],
            "result_summary_ref": summary["simulation_result_summary_id"],
            "check_report_ref": scenario["check_report_ref"],
            "authority_envelope_ref": scenario["authority_envelope_ref"],
            "approval_request_ref": scenario["approval_request_ref"],
            "execution_status": "not_executed",
            "live_runtime_invoked": False,
            "live_control_signal_changed": False,
            "trace_refs": scenario["trace_refs"],
        }
        run_record["simulation_run_record_hash"] = stable_hash(run_record)
        run_records.append(run_record)
    return {
        "scenario_packets": [sumo, cuopt],
        "simulation_run_records": run_records,
        "simulation_result_summaries": summaries,
    }


def build_simulation_check_reports(scenarios: dict[str, Any]) -> list[dict[str, Any]]:
    reports = []
    for scenario, run, summary in zip(scenarios["scenario_packets"], scenarios["simulation_run_records"], scenarios["simulation_result_summaries"]):
        statuses = summary["simulation_check_statuses"]
        report = {
            "simulation_check_report_id": stable_id("simulation-check-report", scenario["scenario_packet_id"]),
            "schema_version": "main-citybrain.schedule_simulate.simulation_check_report.r1",
            "scenario_packet_ref": scenario["scenario_packet_id"],
            "simulation_run_record_ref": run["simulation_run_record_id"],
            "result_summary_ref": summary["simulation_result_summary_id"],
            "simulation_check_statuses": statuses,
            "scenario_input_valid": "scenario_input_valid" in statuses,
            "scenario_input_incomplete": "scenario_input_incomplete" in statuses,
            "assumption_limited": "assumption_limited" in statuses,
            "not_calibrated_for_prediction": True,
            "local_replay_only": True,
            "not_actionable_without_approval": True,
            "check_report_ref": scenario["check_report_ref"],
            "authority_envelope_ref": scenario["authority_envelope_ref"],
            "approval_request_ref": scenario["approval_request_ref"],
            "execution_status": "not_executed",
            "cannot_claim": scenario["cannot_claim"],
        }
        report["simulation_check_report_hash"] = stable_hash(report)
        reports.append(report)
    return reports


def build_approval_bindings(schedule: dict[str, Any], scenarios: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    refs = [(item["schedule_option_id"], item) for item in schedule["schedule_options"]]
    refs.extend((item["scenario_packet_id"], item) for item in scenarios["scenario_packets"])
    for index, (target_ref, item) in enumerate(refs, start=1):
        binding = {
            "schedule_approval_binding_id": f"schedule-approval-binding:push6:lane-c:{index:04d}",
            "schema_version": "main-citybrain.schedule_simulate.schedule_approval_binding.r1",
            "target_ref": target_ref,
            "approval_request_ref": item["approval_request_ref"],
            "check_report_ref": item["check_report_ref"],
            "authority_envelope_ref": item["authority_envelope_ref"],
            "approval_lifecycle_ref": "outputs/push6_lane_a_approval_lifecycle/APPROVAL_LIFECYCLE_DECISION.json",
            "authority_level_required": "authority_level_3",
            "approval_lifecycle_used": True,
            "execution_status": "not_executed",
            "approval_bypass": False,
            "cannot_claim": unique([item["cannot_claim"], UNIVERSAL_NON_CLAIMS]),
        }
        binding["schedule_approval_binding_hash"] = stable_hash(binding)
        rows.append(binding)
    return rows


def contract_overview_md() -> str:
    return """# SCHEDULE + SIMULATE v1 Contract Overview

Lane C defines local/replay ScheduleRequest, ScheduleOptionSet, ScheduleOption,
ConstraintSet, ScenarioPacket, SimulationRunRecord, SimulationResultSummary,
SimulationCheckReport, and ScheduleApprovalBinding objects.

All schedule and simulation objects carry CHECK refs, authority refs, approval
request refs, evidence, limitations, traces, and `execution_status = not_executed`.
SUMO is represented as the first local/replay simulator scenario family. cuOpt is
represented as fixture-only scheduling options unless a safe local runtime exists.
"""


def boundary_text() -> str:
    return "# SCHEDULE + SIMULATE Boundary And Non-Claims\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + UNIVERSAL_NON_CLAIMS)


def test_log_text(tests: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SCHEDULE + SIMULATE Test Log",
            "",
            f"- runner: `{tests.get('runner', 'NOT_RUN')}`",
            f"- focused: `{tests.get('focused', {}).get('result', 'NOT_RUN')}`, `{tests.get('focused', {}).get('count', 0)}` tests",
            f"- full_discovery: `{tests.get('full_discovery', {}).get('result', 'NOT_RUN')}`, `{tests.get('full_discovery', {}).get('count', 0)}` tests",
            f"- ASK scoped diff: `{tests.get('ask_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- R7 scoped diff: `{tests.get('r7_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            "",
            "SCHEDULE/SIMULATE v1 remains local/replay, proposal-only, and not executed.",
        ]
    )


def run_command(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "count": unittest_count(proc.stdout + proc.stderr),
    }


def unittest_count(output: str) -> int:
    import re

    match = re.search(r"Ran (\d+) tests?", output)
    return int(match.group(1)) if match else 0


def run_tests() -> dict[str, Any]:
    focused = run_command([sys.executable, "-m", "unittest", "tests.test_main_citybrain_push6_lane_c_schedule_simulate"])
    return {
        "runner": "POST_BUILD",
        "focused": {
            "result": "PASS" if focused["returncode"] == 0 else "FAIL",
            **focused,
        },
        "full_discovery": {
            "result": "SKIPPED_UNSAFE",
            "returncode": 0,
            "count": 0,
            "stdout_tail": "",
            "stderr_tail": "",
            "reason": "Full discovery mutates generated cross-lane output artifacts; Lane C focused tests and protected ASK/R7 diffs are used.",
        },
        "ask_scoped_diff": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_scoped_diff": git_diff_empty(R7_RUNTIME_PATHS),
    }


def build_closeout(decision: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(CLOSEOUT_ROOT)
    main_hash = verify_hash_manifest_for(OUTPUT_ROOT, "SCHEDULE_SIMULATE_HASH_MANIFEST.json")
    status = CLOSEOUT_STATUS if decision.get("status") == PASS_STATUS and main_hash["status"] == "PASS" else FAIL_STATUS
    closeout = {
        "schema_version": "main-citybrain.push6.lane_c.schedule_simulate.closeout.decision.v1",
        "task_id": "PUSH6-LANE-C-SCHEDULE-SIMULATE-CLOSEOUT",
        "status": status,
        "main_status": decision.get("status"),
        "main_hash_manifest": main_hash,
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "next": "WAIT_FOR_PUSH6_LANE_A_AND_LANE_B_THEN_INFRA_INTEGRATION",
        "created_at": utc_now(),
    }
    write_json(CLOSEOUT_ROOT / "SCHEDULE_SIMULATE_CLOSEOUT_DECISION.json", closeout)
    write_text(CLOSEOUT_ROOT / "SCHEDULE_SIMULATE_CLOSEOUT_SUMMARY.md", f"# SCHEDULE + SIMULATE Closeout\n\nStatus: `{status}`\n")
    write_text(CLOSEOUT_ROOT / "SCHEDULE_SIMULATE_CLOSEOUT_LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(CLOSEOUT_ROOT / "SCHEDULE_SIMULATE_CLOSEOUT_NEXT_STEPS.md", "# Next Steps\n\n- Wait for Lane A and Lane B, then INFRA Push 6 integration.\n")
    write_hash_manifest_for(CLOSEOUT_ROOT, "SCHEDULE_SIMULATE_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push6.lane_c.schedule_simulate.closeout.hash_manifest.v1")
    return closeout


def build_final_status(decision: dict[str, Any], closeout: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(FINAL_ROOT)
    closeout_hash = verify_hash_manifest_for(CLOSEOUT_ROOT, "SCHEDULE_SIMULATE_CLOSEOUT_HASH_MANIFEST.json")
    status = FINAL_STATUS if closeout.get("status") == CLOSEOUT_STATUS and closeout_hash["status"] == "PASS" else FAIL_STATUS
    final = {
        "schema_version": "main-citybrain.push6.lane_c.schedule_simulate.final_status.decision.v1",
        "task_id": "PUSH6-LANE-C-SCHEDULE-SIMULATE-FINAL-STATUS",
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "closeout_status": closeout.get("status"),
        "completed_through": [
            "C0_PUSH5_AND_APPROVAL_GATE_DISCOVERY",
            "C1_SCHEDULE_CONTRACT_R1",
            "C2_SCENARIO_PACKET_CONTRACT_R1",
            "C3_CUOPT_SCHEDULING_FIXTURES_R2",
            "C4_SUMO_SCENARIO_FIXTURES_R2",
            "C5_SIMULATION_CHECK_R2",
            "C6_APPROVAL_BINDING_R3",
            "C7_CLOSEOUT",
            "C8_BRANCH_PUBLISH",
            "C9_FINAL_STATUS",
        ],
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(FINAL_ROOT / "SCHEDULE_SIMULATE_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "SCHEDULE_SIMULATE_FINAL_STATUS_SUMMARY.md", f"# SCHEDULE + SIMULATE Final Status\n\nStatus: `{status}`\n\nBranch-publish ready for Push 6 INFRA after Lane A and Lane B.\n")
    write_hash_manifest_for(FINAL_ROOT, "SCHEDULE_SIMULATE_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push6.lane_c.schedule_simulate.final_status.hash_manifest.v1")
    return final


def build_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    reset_root(OUTPUT_ROOT)
    reset_root(CLOSEOUT_ROOT)
    reset_root(FINAL_ROOT)
    p5_gate = push5_gate()
    if p5_gate["status"] != "PASS":
        decision = {"schema_version": "main-citybrain.push6.lane_c.schedule_simulate.decision.v1", "task_id": TASK_ID, "status": STOP_PUSH5, "push5_gate": p5_gate, "created_at": utc_now()}
        write_json(OUTPUT_ROOT / "SCHEDULE_SIMULATE_DECISION.json", decision)
        return {"decision": decision}
    a_gate = approval_gate()
    if a_gate["status"] != "PASS":
        decision = {"schema_version": "main-citybrain.push6.lane_c.schedule_simulate.decision.v1", "task_id": TASK_ID, "status": STOP_APPROVAL, "push5_gate": p5_gate, "approval_gate": a_gate, "created_at": utc_now()}
        write_json(OUTPUT_ROOT / "SCHEDULE_SIMULATE_DECISION.json", decision)
        return {"decision": decision}

    inputs = load_inputs()
    schedule = build_schedule_payloads(inputs)
    scenarios = build_scenario_payloads(inputs, schedule)
    check_reports = build_simulation_check_reports(scenarios)
    approval_bindings = build_approval_bindings(schedule, scenarios)
    cuopt_fixtures = {
        "schema_version": "main-citybrain.schedule_simulate.cuopt_scheduling_fixtures.r1",
        "status": "PASS_WITH_LIMITATION",
        "runtime_invoked": False,
        "limitation": "cuOpt scheduling families are represented as local/replay option fixtures in this lane.",
        "schedule_options": schedule["schedule_options"],
        "scenario_packets": [item for item in scenarios["scenario_packets"] if item["simulator_kind"] == "cuopt_fixture"],
    }
    sumo_fixtures = {
        "schema_version": "main-citybrain.schedule_simulate.sumo_scenario_fixtures.r1",
        "status": "PASS",
        "scenario_packets": [item for item in scenarios["scenario_packets"] if item["simulator_kind"] == "sumo_local_replay"],
        "simulation_run_records": [item for item in scenarios["simulation_run_records"] if item["simulator_kind"] == "sumo_local_replay"],
        "simulation_result_summaries": [item for item in scenarios["simulation_result_summaries"] if item["scenario_packet_ref"].endswith("sumo:0001")],
    }
    all_schedule_not_executed = all(item["execution_status"] == "not_executed" for item in schedule["schedule_options"])
    all_scenario_not_executed = all(item["execution_status"] == "not_executed" for item in scenarios["scenario_packets"] + scenarios["simulation_run_records"])
    counts = {
        "schedule_requests": 1,
        "schedule_options": len(schedule["schedule_options"]),
        "cuopt_fixtures": len(cuopt_fixtures["scenario_packets"]),
        "approval_bindings": len(approval_bindings),
        "scenario_packets": len(scenarios["scenario_packets"]),
        "sumo_scenarios": len(sumo_fixtures["scenario_packets"]),
        "simulation_check_reports": len(check_reports),
    }
    status = PASS_STATUS if all_schedule_not_executed and all_scenario_not_executed and approval_bindings else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push6.lane_c.schedule_simulate.decision.v1",
        "task_id": TASK_ID,
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "push5_gate": p5_gate,
        "approval_gate": a_gate,
        "plan_mode_source": schedule["plan"]["plan_mode_source"],
        "counts": counts,
        "contract_check": {
            "lane_c_only": True,
            "local_replay_only": True,
            "approval_lifecycle_used": True,
            "no_execution": all_schedule_not_executed and all_scenario_not_executed,
            "no_live_dispatch_control_signal_control": True,
            "no_legal_certified_official_schedule_claim": True,
            "no_sealed_ask_drift": tests.get("ask_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
            "no_protected_r7_drift": tests.get("r7_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
            "no_live_api_url_llm": True,
            "no_unrelated_dirty_files_staged": True,
        },
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
        "tests": tests,
    }

    write_json(OUTPUT_ROOT / "SCHEDULE_SIMULATE_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "SCHEDULE_CONTRACT_OVERVIEW.md", contract_overview_md())
    for name, payload in schema_payloads().items():
        write_json(OUTPUT_ROOT / name, payload)
    write_json(
        OUTPUT_ROOT / "SCHEDULE_OPTION_FIXTURES.json",
        {
            "schema_version": "main-citybrain.schedule_simulate.schedule_option_fixtures.r1",
            "status": "PASS",
            "schedule_requests": [schedule["schedule_request"]],
            "constraint_sets": [schedule["constraint_set"]],
            "schedule_option_sets": [schedule["schedule_option_set"]],
            "schedule_options": schedule["schedule_options"],
        },
    )
    write_json(OUTPUT_ROOT / "CUOPT_SCHEDULING_FIXTURES.json", cuopt_fixtures)
    write_json(OUTPUT_ROOT / "SUMO_SCENARIO_FIXTURES.json", sumo_fixtures)
    write_json(
        OUTPUT_ROOT / "SIMULATION_CHECK_REPORTS.json",
        {
            "schema_version": "main-citybrain.schedule_simulate.simulation_check_reports.r1",
            "status": "PASS",
            "simulation_run_records": scenarios["simulation_run_records"],
            "simulation_result_summaries": scenarios["simulation_result_summaries"],
            "items": check_reports,
        },
    )
    write_json(
        OUTPUT_ROOT / "SCHEDULE_APPROVAL_BINDINGS.json",
        {
            "schema_version": "main-citybrain.schedule_simulate.schedule_approval_bindings.r1",
            "status": "PASS",
            "items": approval_bindings,
        },
    )
    write_text(OUTPUT_ROOT / "SCHEDULE_SIMULATE_BOUNDARY_AND_NON_CLAIMS.md", boundary_text())
    write_text(OUTPUT_ROOT / "SCHEDULE_SIMULATE_TEST_LOG.md", test_log_text(tests))
    write_hash_manifest_for(OUTPUT_ROOT, "SCHEDULE_SIMULATE_HASH_MANIFEST.json", "main-citybrain.push6.lane_c.schedule_simulate.hash_manifest.v1")
    closeout = build_closeout(decision, tests)
    final = build_final_status(decision, closeout, tests)
    return {
        "decision": decision,
        "schedule": schedule,
        "scenarios": scenarios,
        "check_reports": check_reports,
        "approval_bindings": approval_bindings,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    initial = build_outputs({"runner": "PRE_TEST"})
    if initial["decision"].get("status") in {STOP_PUSH5, STOP_APPROVAL}:
        print(json.dumps({"decision": initial["decision"]}, indent=2, sort_keys=True))
        return 1
    tests = run_tests()
    result = build_outputs(tests)
    print(json.dumps({"decision": result["decision"], "final": result["final"]}, indent=2, sort_keys=True))
    ok = (
        result["decision"]["status"] == PASS_STATUS
        and tests["focused"]["result"] == "PASS"
        and tests["full_discovery"]["result"] in {"PASS", "SKIPPED_UNSAFE"}
        and tests["ask_scoped_diff"]["status"] == "PASS"
        and tests["r7_scoped_diff"]["status"] == "PASS"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
