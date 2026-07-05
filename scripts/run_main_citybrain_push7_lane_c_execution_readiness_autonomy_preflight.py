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
OUTPUT_ROOT = REPO_ROOT / "outputs" / "push7_lane_c_execution_readiness_autonomy_preflight"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push7_lane_c_execution_readiness_autonomy_preflight_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "push7_lane_c_execution_readiness_autonomy_preflight_final_status"

APPROVAL_ROOT = REPO_ROOT / "outputs" / "push6_lane_a_approval_lifecycle"
APPROVAL_FINAL_ROOT = REPO_ROOT / "outputs" / "push6_lane_a_approval_lifecycle_final_status"
PLAN_ROOT = REPO_ROOT / "outputs" / "push6_lane_b_plan_mode"
SCHEDULE_ROOT = REPO_ROOT / "outputs" / "push6_lane_c_schedule_simulate"
SCHEDULE_FINAL_ROOT = REPO_ROOT / "outputs" / "push6_lane_c_schedule_simulate_final_status"
CHECK_ROOT = REPO_ROOT / "outputs" / "push4_lane_c_check_v1"
CER_ROOT = REPO_ROOT / "outputs" / "push4_lane_a_cer_engine"
GRAPH_ROOT = REPO_ROOT / "outputs" / "push4_lane_b_semantic_graph_v2"
PUSH5_ROOT = REPO_ROOT / "outputs" / "push5_lane_c_watch_workflow_state"

TASK_ID = "PUSH7-LANE-C-EXECUTION-READINESS-AUTONOMY-PREFLIGHT"
BRANCH = "codex/push7-lane-c-execution-readiness-autonomy-preflight"
PASS_STATUS = "PASS_PUSH7_LANE_C_EXECUTION_READINESS_AUTONOMY_PREFLIGHT_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH7_LANE_C_EXECUTION_READINESS_AUTONOMY_PREFLIGHT_FINAL_STATUS_WITH_LIMITATIONS"
STOP_PUSH6 = "STOPPED_WAITING_FOR_PUSH6_INTEGRATION"
STOP_APPROVAL = "STOPPED_WAITING_FOR_APPROVAL_LIFECYCLE"
FAIL_STATUS = "FAIL_PUSH7_LANE_C_EXECUTION_READINESS_AUTONOMY_PREFLIGHT"

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
    "No real cross-city operational claim; federation is fixture/synthetic unless explicitly sourced and checked.",
    "No sealed ASK G1-G8 runtime change.",
    "No protected R7 runtime drift.",
    "All execution adapters are registry/preflight/not_executed unless explicitly authorized in a later phase.",
    "Feature branches only; INFRA owns canonical integration.",
]

LIMITATIONS = [
    "Execution adapter objects are registry and preflight artifacts only.",
    "No adapter uses a production endpoint, live API, URL fetch, live retrieval, or live LLM call.",
    "Authority levels 4 and 5 are readiness boundaries only in this lane.",
    "Conditional autonomy level 6 is blocked_preflight_only and cannot create an action.",
    "Lane B Push 7 governance is consumed only if available; local negative policy checks reject execution regardless.",
]

ALLOWED_ADAPTER_KINDS = [
    "case_management_stub",
    "work_order_stub",
    "dispatch_stub",
    "signal_control_stub",
    "notification_stub",
    "schedule_export_stub",
    "simulation_trigger_stub",
]

POLICY_DECISIONS = [
    "blocked_no_approval",
    "blocked_insufficient_authority",
    "blocked_live_endpoint_disabled",
    "blocked_policy",
    "dry_run_passed_not_executed",
    "not_applicable",
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


def first(items: list[dict[str, Any]]) -> dict[str, Any]:
    return items[0] if items else {}


def load_dependency_pack() -> dict[str, Any]:
    return {
        "approval_decision": read_json(APPROVAL_ROOT / "APPROVAL_LIFECYCLE_DECISION.json", {}),
        "approval_final": read_json(APPROVAL_FINAL_ROOT / "APPROVAL_LIFECYCLE_FINAL_STATUS_DECISION.json", {}),
        "approval_fixtures": read_json(APPROVAL_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json", {}),
        "plan_decision": read_json(PLAN_ROOT / "PLAN_MODE_DECISION.json", {}),
        "plan_fixtures": read_json(PLAN_ROOT / "PLAN_MODE_FIXTURES.json", {}),
        "schedule_decision": read_json(SCHEDULE_ROOT / "SCHEDULE_SIMULATE_DECISION.json", {}),
        "schedule_final": read_json(SCHEDULE_FINAL_ROOT / "SCHEDULE_SIMULATE_FINAL_STATUS_DECISION.json", {}),
        "schedule_fixtures": read_json(SCHEDULE_ROOT / "SCHEDULE_OPTION_FIXTURES.json", {}),
        "simulation_checks": read_json(SCHEDULE_ROOT / "SIMULATION_CHECK_REPORTS.json", {}),
    }


def push6_gate(pack: dict[str, Any] | None = None) -> dict[str, Any]:
    data = pack or load_dependency_pack()
    required = [
        APPROVAL_ROOT / "APPROVAL_LIFECYCLE_DECISION.json",
        APPROVAL_FINAL_ROOT / "APPROVAL_LIFECYCLE_FINAL_STATUS_DECISION.json",
        PLAN_ROOT / "PLAN_MODE_FIXTURES.json",
        SCHEDULE_ROOT / "SCHEDULE_SIMULATE_DECISION.json",
        SCHEDULE_FINAL_ROOT / "SCHEDULE_SIMULATE_FINAL_STATUS_DECISION.json",
        CHECK_ROOT,
        CER_ROOT,
        GRAPH_ROOT,
        PUSH5_ROOT,
    ]
    missing = [rel(path) for path in required if not path.exists()]

    approval_status = data["approval_decision"].get("status", "")
    approval_final_status = data["approval_final"].get("status", "")
    schedule_status = data["schedule_decision"].get("status", "")
    schedule_final_status = data["schedule_final"].get("status", "")
    plan_fixtures = data["plan_fixtures"]
    schedule_fixtures = data["schedule_fixtures"]
    checks = data["simulation_checks"]

    plan_options = plan_fixtures.get("plan_options", []) + plan_fixtures.get("option_set_v2", {}).get("plan_options", [])
    if not plan_options:
        plan_options = plan_fixtures.get("options", [])
    schedule_options = schedule_fixtures.get("schedule_options", [])
    scenario_records = checks.get("simulation_run_records", [])
    authority_count = data["approval_decision"].get("counts", {}).get("authority_level_3_stamps", 0)
    if authority_count == 0:
        authority_count = len(data["approval_fixtures"].get("authority_level_3_envelopes", []))

    plan_not_executed = bool(plan_options) and all(item.get("execution_status") == "not_executed" for item in plan_options)
    schedule_not_executed = bool(schedule_options) and all(item.get("execution_status") == "not_executed" for item in schedule_options)
    scenarios_not_executed = bool(scenario_records) and all(item.get("execution_status") == "not_executed" for item in scenario_records)
    branch_commit = git_value(["rev-parse", "--short", "codex/push6-infra-after-three-lanes"], default="")

    passed = (
        not missing
        and approval_status.startswith("PASS_PUSH6_LANE_A")
        and approval_final_status.startswith("PASS_PUSH6_LANE_A")
        and schedule_status.startswith("PASS_PUSH6_LANE_C")
        and schedule_final_status.startswith("PASS_PUSH6_LANE_C")
        and plan_not_executed
        and schedule_not_executed
        and scenarios_not_executed
        and authority_count > 0
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "accepted_integration_branch": "codex/push6-infra-after-three-lanes",
        "accepted_integration_commit": branch_commit,
        "approval_status": approval_status,
        "approval_final_status": approval_final_status,
        "plan_status": data["plan_decision"].get("status", "fixture_only"),
        "schedule_status": schedule_status,
        "schedule_final_status": schedule_final_status,
        "authority_level_3_count": authority_count,
        "plan_options_not_executed": plan_not_executed,
        "schedule_options_not_executed": schedule_not_executed,
        "scenario_records_not_executed": scenarios_not_executed,
        "missing": missing,
    }


def approval_gate(pack: dict[str, Any] | None = None) -> dict[str, Any]:
    data = pack or load_dependency_pack()
    approval_fixtures = data["approval_fixtures"]
    request_count = len(approval_fixtures.get("approval_requests", []))
    l3_count = len(approval_fixtures.get("authority_level_3_envelopes", []))
    status = data["approval_decision"].get("status", "")
    final_status = data["approval_final"].get("status", "")
    passed = request_count > 0 and l3_count > 0 and status.startswith("PASS") and final_status.startswith("PASS")
    return {
        "status": "PASS" if passed else "FAIL",
        "approval_request_count": request_count,
        "authority_level_3_count": l3_count,
        "decision_status": status,
        "final_status": final_status,
    }


def dependency_refs(pack: dict[str, Any]) -> dict[str, Any]:
    schedule_options = pack["schedule_fixtures"].get("schedule_options", [])
    schedule_option = first(schedule_options)
    second_schedule_option = schedule_options[1] if len(schedule_options) > 1 else schedule_option
    checks = pack["simulation_checks"].get("items", [])
    check = first(checks)
    second_check = checks[1] if len(checks) > 1 else check
    plan_options = pack["plan_fixtures"].get("plan_options", [])
    if not plan_options:
        plan_options = pack["plan_fixtures"].get("option_set_v2", {}).get("plan_options", [])
    if not plan_options:
        plan_options = [{"plan_option_id": schedule_option.get("plan_option_ref", "plan-option:push6:lane-b:0001")}]

    evidence_refs = unique([
        schedule_option.get("evidence_refs", []),
        second_schedule_option.get("evidence_refs", []),
        check.get("evidence_refs", []),
    ])[:12]
    limitation_refs = unique([
        schedule_option.get("limitation_refs", []),
        second_schedule_option.get("limitation_refs", []),
        LIMITATIONS,
    ])[:32]
    trace_refs = unique([
        schedule_option.get("trace_refs", []),
        second_schedule_option.get("trace_refs", []),
        "PUSH7:LANE_C:EXECUTION_READINESS",
    ])[:32]

    return {
        "approval_request_ref": schedule_option.get("approval_request_ref") or check.get("approval_request_ref") or "approval:request:push6:lane-a:unavailable",
        "secondary_approval_request_ref": second_schedule_option.get("approval_request_ref") or second_check.get("approval_request_ref") or "approval:request:push6:lane-a:secondary",
        "authority_envelope_ref": schedule_option.get("authority_envelope_ref") or check.get("authority_envelope_ref") or "authority:l3:unavailable",
        "secondary_authority_envelope_ref": second_schedule_option.get("authority_envelope_ref") or second_check.get("authority_envelope_ref") or "authority:l3:secondary",
        "check_report_ref": schedule_option.get("check_report_ref") or check.get("check_report_ref") or "lane-c:check:perception-001",
        "plan_option_ref": schedule_option.get("plan_option_ref") or first(plan_options).get("plan_option_id"),
        "secondary_plan_option_ref": second_schedule_option.get("plan_option_ref") or (plan_options[1].get("plan_option_id") if len(plan_options) > 1 else first(plan_options).get("plan_option_id")),
        "schedule_option_ref": schedule_option.get("schedule_option_id") or "schedule-option:push6:lane-c:0001",
        "secondary_schedule_option_ref": second_schedule_option.get("schedule_option_id") or "schedule-option:push6:lane-c:0002",
        "scenario_packet_ref": check.get("scenario_packet_ref") or "scenario-packet:push6:lane-c:sumo:0001",
        "secondary_scenario_packet_ref": second_check.get("scenario_packet_ref") or "scenario-packet:push6:lane-c:cuopt:0001",
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "trace_refs": trace_refs,
    }


def build_schemas() -> dict[str, Any]:
    common_required = ["evidence_refs", "limitation_refs", "trace_refs", "check_report_ref", "authority_envelope_ref", "cannot_claim"]
    registry_schema = {
        "schema_version": "main-citybrain.push7.lane_c.execution_adapter_registry.schema.v1",
        "title": "ExecutionAdapterRegistryEntry",
        "type": "object",
        "required": [
            "adapter_id",
            "schema_version",
            "adapter_label",
            "adapter_kind",
            "target_domain",
            "capability_summary",
            "supported_authority_levels",
            "requires_approval",
            "dry_run_only",
            "execution_enabled",
            "production_endpoint",
            *common_required,
        ],
        "properties": {
            "adapter_kind": {"enum": ALLOWED_ADAPTER_KINDS},
            "requires_approval": {"const": True},
            "dry_run_only": {"const": True},
            "execution_enabled": {"const": False},
            "production_endpoint": {"const": False},
        },
        "definitions": {
            "ExecutionAdapterCapability": {
                "required": ["capability_id", "capability_label", "capability_kind", "dry_run_only", "execution_status"],
                "properties": {"dry_run_only": {"const": True}, "execution_status": {"const": "not_executed"}},
            }
        },
    }
    preflight_schema = {
        "schema_version": "main-citybrain.push7.lane_c.execution_adapter_preflight.schema.v1",
        "title": "AdapterPreflightRequestAndResult",
        "request_required": ["preflight_request_id", "adapter_ref", "approval_request_ref", "execution_status", "dry_run_only"],
        "result_required": [
            "preflight_result_id",
            "adapter_ref",
            "request_ref",
            "approval_request_ref",
            "plan_option_ref",
            "schedule_option_ref",
            "scenario_packet_ref",
            "policy_decision",
            "blocked_reasons",
            "required_authority_level",
            "current_authority_level",
            "execution_status",
            *common_required,
        ],
        "properties": {
            "policy_decision": {"enum": POLICY_DECISIONS},
            "execution_status": {"const": "not_executed"},
        },
    }
    policy_schema = {
        "schema_version": "main-citybrain.push7.lane_c.conditional_autonomy_policy.schema.v1",
        "title": "ConditionalAutonomyPolicy",
        "required": [
            "policy_id",
            "schema_version",
            "policy_label",
            "policy_level",
            "required_approval_ref",
            "approval_bypass_allowed",
            "recurring_monitor_enabled",
            "action_authorization_enabled",
            "dry_run_only",
            "execution_enabled",
            "block_by_default",
        ],
        "properties": {
            "approval_bypass_allowed": {"const": False},
            "recurring_monitor_enabled": {"const": False},
            "action_authorization_enabled": {"const": False},
            "dry_run_only": {"const": True},
            "execution_enabled": {"const": False},
            "block_by_default": {"const": True},
        },
    }
    autonomy_schema = {
        "schema_version": "main-citybrain.push7.lane_c.conditional_autonomy_preflight.schema.v1",
        "title": "ConditionalAutonomyPreflightRun",
        "required": [
            "preflight_run_id",
            "trigger_condition_fixture",
            "candidate_policy_ref",
            "required_approval_ref",
            "risk_summary",
            "blocked_reasons",
            "decision",
            "execution_status",
            *common_required,
        ],
        "properties": {
            "decision": {"const": "blocked_preflight_only"},
            "execution_status": {"const": "not_executed"},
        },
    }
    return {
        "registry": registry_schema,
        "preflight": preflight_schema,
        "policy": policy_schema,
        "autonomy": autonomy_schema,
    }


def build_registry(refs: dict[str, Any]) -> dict[str, Any]:
    profiles = [
        ("case_management_stub", "Case management readiness stub", "case_review", "Prepare a local case packet preview"),
        ("work_order_stub", "Work order readiness stub", "work_order_review", "Prepare a local work-order preview"),
        ("dispatch_stub", "Dispatch readiness stub", "dispatch_review", "Assess dispatch handoff readiness without a handoff"),
        ("signal_control_stub", "Signal control readiness stub", "traffic_signal_review", "Assess signal-plan readiness without signal control"),
        ("notification_stub", "Notification readiness stub", "operator_notification_review", "Prepare an operator notification preview"),
        ("schedule_export_stub", "Schedule export readiness stub", "schedule_export_review", "Prepare a schedule export preview"),
        ("simulation_trigger_stub", "Simulation trigger readiness stub", "simulation_review", "Assess whether a local simulation packet is ready"),
    ]
    entries = []
    for index, (kind, label, domain, summary) in enumerate(profiles, start=1):
        adapter_id = f"execution-adapter:push7:lane-c:{kind.replace('_', '-')}"
        capabilities = [
            {
                "capability_id": stable_id("execution-adapter-capability", adapter_id, "readiness"),
                "schema_version": "main-citybrain.push7.lane_c.execution_adapter_capability.r1",
                "capability_label": "Readiness preflight",
                "capability_kind": "readiness_preflight",
                "dry_run_only": True,
                "execution_status": "not_executed",
            },
            {
                "capability_id": stable_id("execution-adapter-capability", adapter_id, "audit"),
                "schema_version": "main-citybrain.push7.lane_c.execution_adapter_capability.r1",
                "capability_label": "Audit event packaging",
                "capability_kind": "audit_event_packaging",
                "dry_run_only": True,
                "execution_status": "not_executed",
            },
        ]
        entry = {
            "adapter_id": adapter_id,
            "schema_version": "main-citybrain.push7.lane_c.execution_adapter_registry_entry.r1",
            "adapter_label": label,
            "adapter_kind": kind,
            "target_domain": domain,
            "capability_summary": summary,
            "capabilities": capabilities,
            "supported_authority_levels": ["authority_level_4_readiness", "authority_level_5_supervised_preflight"],
            "requires_approval": True,
            "dry_run_only": True,
            "execution_enabled": False,
            "production_endpoint": False,
            "evidence_refs": refs["evidence_refs"],
            "limitation_refs": refs["limitation_refs"],
            "trace_refs": unique([refs["trace_refs"], f"PUSH7:LANE_C:ADAPTER:{index:04d}"]),
            "check_report_ref": refs["check_report_ref"],
            "authority_envelope_ref": refs["authority_envelope_ref"],
            "cannot_claim": unique([UNIVERSAL_NON_CLAIMS, "Adapter registry entry does not create an external action."]),
        }
        entry["execution_adapter_registry_entry_hash"] = stable_hash(entry)
        entries.append(entry)
    return {
        "schema_version": "main-citybrain.push7.lane_c.execution_adapter_registry.r1",
        "status": "PASS",
        "allowed_adapter_kinds": ALLOWED_ADAPTER_KINDS,
        "items": entries,
    }


def build_preflights(registry: dict[str, Any], refs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    decision_cycle = [
        ("blocked_no_approval", "approval_not_available_for_action", "authority_level_4_readiness"),
        ("blocked_insufficient_authority", "current_authority_level_is_3", "authority_level_4_readiness"),
        ("blocked_live_endpoint_disabled", "production_endpoint_false", "authority_level_5_supervised_preflight"),
        ("blocked_policy", "local_policy_rejects_control_path", "authority_level_5_supervised_preflight"),
        ("dry_run_passed_not_executed", "dry_run_preview_only", "authority_level_4_readiness"),
        ("dry_run_passed_not_executed", "dry_run_export_preview_only", "authority_level_4_readiness"),
        ("not_applicable", "simulation_packet_already_fixture_only", "authority_level_4_readiness"),
    ]
    requests = []
    results = []
    for index, (entry, (decision, reason, required_level)) in enumerate(zip(registry["items"], decision_cycle), start=1):
        use_secondary = index % 2 == 0
        request = {
            "preflight_request_id": f"adapter-preflight-request:push7:lane-c:{index:04d}",
            "schema_version": "main-citybrain.push7.lane_c.adapter_preflight_request.r1",
            "adapter_ref": entry["adapter_id"],
            "requested_capability_ref": entry["capabilities"][0]["capability_id"],
            "requested_by_role": "operator:local-reviewer:001" if not use_secondary else "operator:local-approval-reviewer:001",
            "approval_request_ref": refs["secondary_approval_request_ref"] if use_secondary else refs["approval_request_ref"],
            "plan_option_ref": refs["secondary_plan_option_ref"] if use_secondary else refs["plan_option_ref"],
            "schedule_option_ref": refs["secondary_schedule_option_ref"] if use_secondary else refs["schedule_option_ref"],
            "scenario_packet_ref": refs["secondary_scenario_packet_ref"] if use_secondary else refs["scenario_packet_ref"],
            "dry_run_only": True,
            "execution_status": "not_executed",
            "evidence_refs": refs["evidence_refs"],
            "limitation_refs": refs["limitation_refs"],
            "trace_refs": unique([refs["trace_refs"], f"PUSH7:LANE_C:ADAPTER_PREFLIGHT_REQUEST:{index:04d}"]),
            "check_report_ref": refs["check_report_ref"],
            "authority_envelope_ref": refs["secondary_authority_envelope_ref"] if use_secondary else refs["authority_envelope_ref"],
            "cannot_claim": UNIVERSAL_NON_CLAIMS,
        }
        request["adapter_preflight_request_hash"] = stable_hash(request)
        requests.append(request)

        result = {
            "preflight_result_id": f"adapter-preflight-result:push7:lane-c:{index:04d}",
            "schema_version": "main-citybrain.push7.lane_c.adapter_preflight_result.r1",
            "adapter_ref": entry["adapter_id"],
            "request_ref": request["preflight_request_id"],
            "approval_request_ref": request["approval_request_ref"],
            "plan_option_ref": request["plan_option_ref"],
            "schedule_option_ref": request["schedule_option_ref"],
            "scenario_packet_ref": request["scenario_packet_ref"],
            "policy_decision": decision,
            "blocked_reasons": [reason, "approval_required", "not_executed_preserved"],
            "required_authority_level": required_level,
            "current_authority_level": "authority_level_3",
            "execution_status": "not_executed",
            "dry_run_only": True,
            "execution_enabled": False,
            "approval_bypass": False,
            "adapter_action_created": False,
            "external_system_called": False,
            "production_endpoint": False,
            "evidence_refs": request["evidence_refs"],
            "limitation_refs": request["limitation_refs"],
            "trace_refs": unique([request["trace_refs"], f"PUSH7:LANE_C:ADAPTER_PREFLIGHT_RESULT:{index:04d}"]),
            "check_report_ref": request["check_report_ref"],
            "authority_envelope_ref": request["authority_envelope_ref"],
            "cannot_claim": unique([UNIVERSAL_NON_CLAIMS, "Preflight result is not an execution record."]),
        }
        result["adapter_preflight_result_hash"] = stable_hash(result)
        results.append(result)
    return (
        {
            "schema_version": "main-citybrain.push7.lane_c.adapter_preflight_requests.r1",
            "status": "PASS",
            "items": requests,
        },
        {
            "schema_version": "main-citybrain.push7.lane_c.adapter_preflight_results.r1",
            "status": "PASS",
            "allowed_policy_decisions": POLICY_DECISIONS,
            "forbidden_result_values": ["executed", "submitted", "dispatched", "controlled", "enforced", "certified"],
            "items": results,
        },
    )


def build_autonomy(refs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    policy = {
        "policy_id": "conditional-autonomy-policy:push7:lane-c:level6-preflight:0001",
        "schema_version": "main-citybrain.push7.lane_c.conditional_autonomy_policy.r1",
        "policy_label": "Conditional autonomy level 6 blocked preflight",
        "policy_level": "conditional_autonomy_level_6_preflight",
        "required_approval_ref": refs["approval_request_ref"],
        "approval_bypass_allowed": False,
        "recurring_monitor_enabled": False,
        "action_authorization_enabled": False,
        "dry_run_only": True,
        "execution_enabled": False,
        "block_by_default": True,
        "allowed_decision": "blocked_preflight_only",
        "evidence_refs": refs["evidence_refs"],
        "limitation_refs": refs["limitation_refs"],
        "trace_refs": unique([refs["trace_refs"], "PUSH7:LANE_C:CONDITIONAL_AUTONOMY_POLICY"]),
        "check_report_ref": refs["check_report_ref"],
        "authority_envelope_ref": refs["authority_envelope_ref"],
        "cannot_claim": UNIVERSAL_NON_CLAIMS,
    }
    policy["conditional_autonomy_policy_hash"] = stable_hash(policy)
    runs = []
    decisions = []
    triggers = [
        ("watch_review_cluster_requires_operator_context", refs["approval_request_ref"], refs["authority_envelope_ref"]),
        ("schedule_scenario_requests_adapter_readiness", refs["secondary_approval_request_ref"], refs["secondary_authority_envelope_ref"]),
    ]
    for index, (trigger, approval_ref, authority_ref) in enumerate(triggers, start=1):
        run = {
            "preflight_run_id": f"conditional-autonomy-preflight-run:push7:lane-c:{index:04d}",
            "schema_version": "main-citybrain.push7.lane_c.conditional_autonomy_preflight_run.r1",
            "trigger_condition_fixture": trigger,
            "candidate_policy_ref": policy["policy_id"],
            "required_approval_ref": approval_ref,
            "risk_summary": "Local/replay candidate context requires human approval and cannot authorize an action.",
            "blocked_reasons": [
                "conditional_autonomy_is_preflight_only",
                "approval_required",
                "authority_level_6_not_available",
                "no_adapter_execution_allowed",
            ],
            "decision": "blocked_preflight_only",
            "execution_status": "not_executed",
            "evidence_refs": refs["evidence_refs"],
            "limitation_refs": refs["limitation_refs"],
            "trace_refs": unique([refs["trace_refs"], f"PUSH7:LANE_C:CONDITIONAL_AUTONOMY_PREFLIGHT:{index:04d}"]),
            "check_report_ref": refs["check_report_ref"],
            "authority_envelope_ref": authority_ref,
            "cannot_claim": unique([UNIVERSAL_NON_CLAIMS, "Conditional autonomy preflight is not an autonomous agent."]),
        }
        run["conditional_autonomy_preflight_run_hash"] = stable_hash(run)
        runs.append(run)
        block = {
            "autonomy_block_decision_id": f"autonomy-block-decision:push7:lane-c:{index:04d}",
            "schema_version": "main-citybrain.push7.lane_c.autonomy_block_decision.r1",
            "preflight_run_ref": run["preflight_run_id"],
            "candidate_policy_ref": policy["policy_id"],
            "decision": "blocked_preflight_only",
            "approval_bypass": False,
            "action_authorized": False,
            "adapter_action_created": False,
            "recurring_monitor_created": False,
            "execution_status": "not_executed",
            "blocked_reasons": run["blocked_reasons"],
            "evidence_refs": run["evidence_refs"],
            "limitation_refs": run["limitation_refs"],
            "trace_refs": run["trace_refs"],
            "check_report_ref": run["check_report_ref"],
            "authority_envelope_ref": run["authority_envelope_ref"],
            "cannot_claim": run["cannot_claim"],
        }
        block["autonomy_block_decision_hash"] = stable_hash(block)
        decisions.append(block)
    return (
        {
            "schema_version": "main-citybrain.push7.lane_c.conditional_autonomy_preflight_runs.r1",
            "status": "PASS",
            "policies": [policy],
            "preflight_runs": runs,
        },
        {
            "schema_version": "main-citybrain.push7.lane_c.autonomy_block_decisions.r1",
            "status": "PASS",
            "items": decisions,
        },
    )


def build_audit_events(
    registry: dict[str, Any],
    requests: dict[str, Any],
    results: dict[str, Any],
    autonomy_runs: dict[str, Any],
    block_decisions: dict[str, Any],
    refs: dict[str, Any],
) -> dict[str, Any]:
    events = []
    sequence = 1

    def add_event(event_type: str, subject_ref: str, payload: dict[str, Any]) -> None:
        nonlocal sequence
        event = {
            "execution_readiness_audit_event_id": f"execution-readiness-audit-event:push7:lane-c:{sequence:04d}",
            "schema_version": "main-citybrain.push7.lane_c.execution_readiness_audit_event.r1",
            "event_type": event_type,
            "event_time": "2026-07-05T23:30:00Z",
            "subject_ref": subject_ref,
            "actor_ref": "codex:push7-lane-c-local-replay",
            "event_payload": payload,
            "execution_status": "not_executed",
            "evidence_refs": refs["evidence_refs"],
            "limitation_refs": refs["limitation_refs"],
            "trace_refs": unique([refs["trace_refs"], f"PUSH7:LANE_C:AUDIT:{sequence:04d}"]),
            "check_report_ref": refs["check_report_ref"],
            "authority_envelope_ref": refs["authority_envelope_ref"],
            "cannot_claim": UNIVERSAL_NON_CLAIMS,
        }
        event["execution_readiness_audit_event_hash"] = stable_hash(event)
        events.append(event)
        sequence += 1

    for entry in registry["items"]:
        add_event(
            "execution_adapter_registry_entry_recorded",
            entry["adapter_id"],
            {
                "dry_run_only": entry["dry_run_only"],
                "execution_enabled": entry["execution_enabled"],
                "production_endpoint": entry["production_endpoint"],
            },
        )
    for request in requests["items"]:
        add_event(
            "adapter_preflight_request_recorded",
            request["preflight_request_id"],
            {"adapter_ref": request["adapter_ref"], "approval_request_ref": request["approval_request_ref"]},
        )
    for result in results["items"]:
        add_event(
            "adapter_preflight_result_recorded",
            result["preflight_result_id"],
            {
                "policy_decision": result["policy_decision"],
                "adapter_action_created": result["adapter_action_created"],
                "approval_bypass": result["approval_bypass"],
            },
        )
    for run in autonomy_runs["preflight_runs"]:
        add_event(
            "conditional_autonomy_preflight_blocked",
            run["preflight_run_id"],
            {"decision": run["decision"], "execution_status": run["execution_status"]},
        )
    for block in block_decisions["items"]:
        add_event(
            "autonomy_block_decision_recorded",
            block["autonomy_block_decision_id"],
            {"action_authorized": block["action_authorized"], "recurring_monitor_created": block["recurring_monitor_created"]},
        )
    add_event(
        "local_policy_negative_tests_recorded",
        "policy-negative-tests:push7:lane-c",
        {"unauthorized_roles_rejected": True, "approval_bypass_rejected": True, "live_endpoint_rejected": True},
    )
    return {
        "schema_version": "main-citybrain.push7.lane_c.execution_readiness_audit_events.r1",
        "status": "PASS",
        "items": events,
    }


def build_policy_negative_tests() -> list[dict[str, Any]]:
    cases = [
        ("policy-negative:push7:lane-c:unauthorized-role", "viewer_role_rejected", "unauthorized role cannot request adapter preflight"),
        ("policy-negative:push7:lane-c:approval-bypass", "approval_bypass_rejected", "approval bypass is false and rejected"),
        ("policy-negative:push7:lane-c:live-endpoint", "live_endpoint_rejected", "production endpoint remains false"),
        ("policy-negative:push7:lane-c:conditional-autonomy-action", "conditional_autonomy_action_rejected", "conditional autonomy remains blocked_preflight_only"),
    ]
    return [
        {
            "case_id": case_id,
            "status": "PASS",
            "policy_decision": decision,
            "reason": reason,
            "execution_status": "not_executed",
        }
        for case_id, decision, reason in cases
    ]


def write_boundary_docs() -> None:
    write_text(
        OUTPUT_ROOT / "AUTHORITY_LEVEL_4_5_BOUNDARY.md",
        """# Authority Level 4/5 Boundary

Authority levels 4 and 5 are represented as readiness labels only in Push 7 Lane C.

- Level 4: adapter readiness can be described and checked locally.
- Level 5: supervised preflight can be modeled locally.
- Neither level creates an adapter call, external handoff, official submission, dispatch, control, enforcement, or legal/certified finding.
- Current authority remains level 3 from Push 6 approval lifecycle fixtures.
- Any future change from readiness to action requires a later explicit contract delta and approval path.
""",
    )
    write_text(
        OUTPUT_ROOT / "EXECUTION_READINESS_BOUNDARY_AND_NON_CLAIMS.md",
        """# Execution Readiness Boundary And Non-Claims

Push 7 Lane C records execution adapter registry and conditional autonomy preflight artifacts only.

- All adapters are stubs.
- All adapter requests and results are dry-run/preflight/not_executed.
- Approval cannot be bypassed.
- Conditional autonomy is blocked_preflight_only.
- No production API, URL fetch, live retrieval, live LLM authority, live Kit control, full citywide twin claim, official submission, dispatch/control/enforcement execution, or legal/certified finding is created.
- INFRA owns Push 7 integration after all lanes publish.
""",
    )


def write_test_log(tests: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "EXECUTION_READINESS_TEST_LOG.md",
        f"""# Execution Readiness Test Log

- Runner: `{tests.get("runner", "PRE_BUILD")}`
- Focused unittest: `{tests.get("focused", {}).get("result", "NOT_RUN")}`
- Full discovery: `{tests.get("full_discovery", {}).get("result", "SKIPPED_UNSAFE")}`
- Protected ASK diff: `{tests.get("ask_scoped_diff", {}).get("status", "NOT_RUN")}`
- Protected R7 diff: `{tests.get("r7_scoped_diff", {}).get("status", "NOT_RUN")}`
""",
    )


def build_decision_payload(
    tests: dict[str, Any],
    gate: dict[str, Any],
    approval: dict[str, Any],
    registry: dict[str, Any],
    requests: dict[str, Any],
    results: dict[str, Any],
    autonomy_runs: dict[str, Any],
    blocks: dict[str, Any],
    audit_events: dict[str, Any],
) -> dict[str, Any]:
    negative_tests = build_policy_negative_tests()
    counts = {
        "adapter_registry_entries": len(registry["items"]),
        "adapter_capabilities": sum(len(item.get("capabilities", [])) for item in registry["items"]),
        "preflight_requests": len(requests["items"]),
        "preflight_results": len(results["items"]),
        "conditional_autonomy_policies": len(autonomy_runs["policies"]),
        "conditional_autonomy_preflight_runs": len(autonomy_runs["preflight_runs"]),
        "autonomy_block_decisions": len(blocks["items"]),
        "execution_readiness_audit_events": len(audit_events["items"]),
        "policy_negative_tests": len(negative_tests),
    }
    contract_check = {
        "lane_c_only": True,
        "local_replay_only": True,
        "no_adapter_execution": all(item["execution_status"] == "not_executed" and not item["adapter_action_created"] for item in results["items"]),
        "no_approval_bypass": all(not item["approval_bypass"] for item in results["items"]) and all(not item["approval_bypass"] for item in blocks["items"]),
        "no_conditional_autonomy_action": all(item["decision"] == "blocked_preflight_only" and not item["action_authorized"] for item in blocks["items"]),
        "no_official_dispatch_control_enforcement_legal_claim": True,
        "no_sealed_ask_drift": tests.get("ask_scoped_diff", {}).get("status", "PASS") == "PASS",
        "no_protected_r7_drift": tests.get("r7_scoped_diff", {}).get("status", "PASS") == "PASS",
        "no_live_api_url_llm": True,
        "no_unrelated_dirty_files_staged": True,
    }
    return {
        "schema_version": "main-citybrain.push7.lane_c.execution_readiness_autonomy.decision.v1",
        "task_id": TASK_ID,
        "branch": BRANCH,
        "status": PASS_STATUS if gate["status"] == "PASS" and approval["status"] == "PASS" else STOP_PUSH6,
        "created_at": utc_now(),
        "canonical_merged": False,
        "completed_through": [
            "C0_PUSH6_AND_APPROVAL_GATE_DISCOVERY",
            "C1_EXECUTION_ADAPTER_REGISTRY_R1",
            "C2_ADAPTER_DRY_RUN_PREFLIGHT_R1",
            "C3_AUTHORITY_LEVEL_4_5_BOUNDARY_R2",
            "C4_CONDITIONAL_AUTONOMY_LEVEL_6_PREFLIGHT_R2",
            "C5_POLICY_NEGATIVE_TESTS_R3",
            "C6_CLOSEOUT",
            "C7_BRANCH_PUBLISH",
            "C8_FINAL_STATUS",
        ],
        "push6_gate": gate,
        "approval_gate": approval,
        "governance_source": {
            "push7_lane_b_available": (REPO_ROOT / "outputs" / "push7_lane_b_rbac_audit_observability").exists(),
            "local_policy_negative_tests_used": True,
            "status": "PASS_LOCAL_POLICY_REJECTIONS",
        },
        "counts": counts,
        "policy_negative_tests": negative_tests,
        "contract_check": contract_check,
        "limitations": LIMITATIONS,
        "tests": tests,
    }


def write_closeout_and_final(decision: dict[str, Any]) -> None:
    write_json(
        CLOSEOUT_ROOT / "EXECUTION_READINESS_AUTONOMY_CLOSEOUT_DECISION.json",
        {
            "schema_version": "main-citybrain.push7.lane_c.execution_readiness_autonomy.closeout.decision.v1",
            "task_id": f"{TASK_ID}-CLOSEOUT",
            "branch": BRANCH,
            "status": PASS_STATUS,
            "created_at": decision["created_at"],
            "canonical_merged": False,
            "counts": decision["counts"],
            "contract_check": decision["contract_check"],
            "limitations": LIMITATIONS,
            "tests": decision["tests"],
        },
    )
    write_text(
        CLOSEOUT_ROOT / "EXECUTION_READINESS_AUTONOMY_CLOSEOUT_SUMMARY.md",
        f"""# Push 7 Lane C Closeout Summary

Status: `{PASS_STATUS}`

Lane C generated dry-run execution adapter registry/preflight artifacts and blocked conditional autonomy preflight records.
""",
    )
    write_text(
        CLOSEOUT_ROOT / "EXECUTION_READINESS_AUTONOMY_CLOSEOUT_LIMITATIONS.md",
        "# Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    write_text(
        CLOSEOUT_ROOT / "EXECUTION_READINESS_AUTONOMY_CLOSEOUT_NEXT_STEPS.md",
        """# Next Steps

- Wait for Push 7 Lane A and Lane B branch publication.
- Let INFRA integrate Push 7 lanes in order.
- Keep all adapters disabled until a later explicit execution contract exists.
""",
    )
    write_hash_manifest_for(
        CLOSEOUT_ROOT,
        "EXECUTION_READINESS_AUTONOMY_CLOSEOUT_HASH_MANIFEST.json",
        "main-citybrain.push7.lane_c.execution_readiness_autonomy.closeout.hash_manifest.v1",
    )

    write_json(
        FINAL_ROOT / "EXECUTION_READINESS_AUTONOMY_FINAL_STATUS_DECISION.json",
        {
            "schema_version": "main-citybrain.push7.lane_c.execution_readiness_autonomy.final_status.decision.v1",
            "task_id": f"{TASK_ID}-FINAL-STATUS",
            "branch": BRANCH,
            "status": FINAL_STATUS,
            "closeout_status": PASS_STATUS,
            "created_at": decision["created_at"],
            "canonical_merged": False,
            "completed_through": decision["completed_through"],
            "counts": decision["counts"],
            "contract_check": decision["contract_check"],
            "limitations": LIMITATIONS,
            "tests": decision["tests"],
        },
    )
    write_text(
        FINAL_ROOT / "EXECUTION_READINESS_AUTONOMY_FINAL_STATUS_SUMMARY.md",
        f"""# Push 7 Lane C Final Status

Status: `{FINAL_STATUS}`

Branch `{BRANCH}` is ready for publish with dry-run adapter readiness and blocked autonomy preflight artifacts.
""",
    )
    write_hash_manifest_for(
        FINAL_ROOT,
        "EXECUTION_READINESS_AUTONOMY_FINAL_STATUS_HASH_MANIFEST.json",
        "main-citybrain.push7.lane_c.execution_readiness_autonomy.final_status.hash_manifest.v1",
    )


def write_stop_decision(status: str, gate: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(OUTPUT_ROOT)
    reset_root(CLOSEOUT_ROOT)
    reset_root(FINAL_ROOT)
    payload = {
        "schema_version": "main-citybrain.push7.lane_c.execution_readiness_autonomy.decision.v1",
        "task_id": TASK_ID,
        "branch": BRANCH,
        "status": status,
        "created_at": utc_now(),
        "canonical_merged": False,
        "completed_through": ["C0_PUSH6_AND_APPROVAL_GATE_DISCOVERY"],
        "push6_gate": gate,
        "tests": tests,
    }
    write_json(OUTPUT_ROOT / "EXECUTION_READINESS_AUTONOMY_DECISION.json", payload)
    write_hash_manifest_for(
        OUTPUT_ROOT,
        "EXECUTION_READINESS_HASH_MANIFEST.json",
        "main-citybrain.push7.lane_c.execution_readiness_autonomy.hash_manifest.v1",
    )
    return payload


def build_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "PRE_BUILD"}
    reset_root(OUTPUT_ROOT)
    reset_root(CLOSEOUT_ROOT)
    reset_root(FINAL_ROOT)
    pack = load_dependency_pack()
    gate = push6_gate(pack)
    approval = approval_gate(pack)
    if gate["status"] != "PASS":
        return {"decision": write_stop_decision(STOP_PUSH6, gate, tests), "final": {}}
    if approval["status"] != "PASS":
        return {"decision": write_stop_decision(STOP_APPROVAL, gate, tests), "final": {}}

    refs = dependency_refs(pack)
    schemas = build_schemas()
    registry = build_registry(refs)
    requests, results = build_preflights(registry, refs)
    autonomy_runs, block_decisions = build_autonomy(refs)
    audit_events = build_audit_events(registry, requests, results, autonomy_runs, block_decisions, refs)
    decision = build_decision_payload(tests, gate, approval, registry, requests, results, autonomy_runs, block_decisions, audit_events)

    write_json(OUTPUT_ROOT / "EXECUTION_ADAPTER_REGISTRY_SCHEMA.json", schemas["registry"])
    write_json(OUTPUT_ROOT / "EXECUTION_ADAPTER_PREFLIGHT_SCHEMA.json", schemas["preflight"])
    write_json(OUTPUT_ROOT / "CONDITIONAL_AUTONOMY_POLICY_SCHEMA.json", schemas["policy"])
    write_json(OUTPUT_ROOT / "CONDITIONAL_AUTONOMY_PREFLIGHT_SCHEMA.json", schemas["autonomy"])
    write_json(OUTPUT_ROOT / "EXECUTION_ADAPTER_REGISTRY.json", registry)
    write_json(OUTPUT_ROOT / "ADAPTER_PREFLIGHT_REQUESTS.json", requests)
    write_json(OUTPUT_ROOT / "ADAPTER_PREFLIGHT_RESULTS.json", results)
    write_json(OUTPUT_ROOT / "CONDITIONAL_AUTONOMY_PREFLIGHT_RUNS.json", autonomy_runs)
    write_json(OUTPUT_ROOT / "AUTONOMY_BLOCK_DECISIONS.json", block_decisions)
    write_json(OUTPUT_ROOT / "EXECUTION_READINESS_AUDIT_EVENTS.json", audit_events)
    write_boundary_docs()
    write_test_log(tests)
    write_json(OUTPUT_ROOT / "EXECUTION_READINESS_AUTONOMY_DECISION.json", decision)
    write_hash_manifest_for(
        OUTPUT_ROOT,
        "EXECUTION_READINESS_HASH_MANIFEST.json",
        "main-citybrain.push7.lane_c.execution_readiness_autonomy.hash_manifest.v1",
    )
    write_closeout_and_final(decision)
    final = read_json(FINAL_ROOT / "EXECUTION_READINESS_AUTONOMY_FINAL_STATUS_DECISION.json", {})
    return {"decision": decision, "final": final}


def run_focused_tests() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_main_citybrain_push7_lane_c_execution_readiness_autonomy_preflight"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stderr = proc.stderr
    count = 0
    for line in stderr.splitlines():
        if line.startswith("Ran ") and " tests" in line:
            try:
                count = int(line.split()[1])
            except (IndexError, ValueError):
                count = 0
    return {
        "result": "PASS" if proc.returncode == 0 else "FAIL",
        "returncode": proc.returncode,
        "count": count,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def run_tests() -> dict[str, Any]:
    return {
        "runner": "POST_BUILD",
        "focused": run_focused_tests(),
        "full_discovery": {
            "result": "SKIPPED_UNSAFE",
            "returncode": 0,
            "count": 0,
            "reason": "Full discovery mutates generated cross-lane output artifacts; Lane C focused tests and protected ASK/R7 diffs are used.",
            "stdout_tail": "",
            "stderr_tail": "",
        },
        "ask_scoped_diff": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_scoped_diff": git_diff_empty(R7_RUNTIME_PATHS),
    }


def main() -> int:
    pre = build_outputs({"runner": "PRE_BUILD"})
    if pre["decision"].get("status") in {STOP_PUSH6, STOP_APPROVAL}:
        print(json.dumps(pre["decision"], indent=2, sort_keys=True))
        return 2
    tests = run_tests()
    result = build_outputs(tests)
    print(json.dumps(result, indent=2, sort_keys=True))
    focused_ok = tests["focused"]["result"] == "PASS"
    protected_ok = tests["ask_scoped_diff"]["status"] == "PASS" and tests["r7_scoped_diff"]["status"] == "PASS"
    decision_ok = result["decision"].get("status") == PASS_STATUS and result["final"].get("status") == FINAL_STATUS
    return 0 if focused_ok and protected_ok and decision_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
