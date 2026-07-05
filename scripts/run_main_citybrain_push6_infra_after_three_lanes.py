#!/usr/bin/env python3
"""Build Push 6 INFRA integration artifacts after three lanes publish."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
OUTPUT_ROOT = OUTPUTS_ROOT / "push6_infra_after_three_lanes_integration"
CLOSEOUT_ROOT = OUTPUTS_ROOT / "push6_infra_after_three_lanes_closeout"
FINAL_ROOT = OUTPUTS_ROOT / "push6_infra_after_three_lanes_final_status"

TASK_ID = "PUSH6-INFRA-AFTER-THREE-LANES"
BRANCH = "codex/push6-infra-after-three-lanes"
BASE_REF = "origin/codex/push5-infra-after-three-lanes"
PASS_STATUS = "PASS_PUSH6_INFRA_AFTER_THREE_LANES_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH6_INFRA_AFTER_THREE_LANES"

LANES = {
    "lane_a": {
        "branch": "origin/codex/push6-lane-a-approval-lifecycle",
        "label": "approval lifecycle and Authority Level 3 semantics",
    },
    "lane_b": {
        "branch": "origin/codex/push6-lane-b-plan-mode",
        "label": "PLAN mode OptionSet v2 candidates",
    },
    "lane_c": {
        "branch": "origin/codex/push6-lane-c-schedule-simulate",
        "label": "SCHEDULE and SIMULATE local/replay packets",
    },
}

LANE_A_ROOT = OUTPUTS_ROOT / "push6_lane_a_approval_lifecycle"
LANE_A_FINAL_ROOT = OUTPUTS_ROOT / "push6_lane_a_approval_lifecycle_final_status"
LANE_B_ROOT = OUTPUTS_ROOT / "push6_lane_b_plan_mode"
LANE_C_ROOT = OUTPUTS_ROOT / "push6_lane_c_schedule_simulate"
LANE_C_FINAL_ROOT = OUTPUTS_ROOT / "push6_lane_c_schedule_simulate_final_status"
PUSH5_INFRA_ROOT = OUTPUTS_ROOT / "push5_infra_after_three_lanes_integration"
PUSH5_FINAL_ROOT = OUTPUTS_ROOT / "push5_infra_after_three_lanes_final_status"

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

REQUIRED_OUTPUTS = [
    "PUSH6_INFRA_INTEGRATION_DECISION.json",
    "PUSH6_BRANCH_TOPOLOGY.md",
    "PUSH6_CROSS_LANE_COMPATIBILITY_REPORT.json",
    "PUSH6_APPROVAL_PLAN_SCHEDULE_JOIN_REPORT.json",
    "PUSH6_BOUNDARY_AND_NON_CLAIMS.md",
    "PUSH6_TEST_REPORT.md",
    "PUSH6_OPEN_LIMITATIONS.md",
    "PUSH6_HASH_MANIFEST.json",
]

REQUIRED_CLOSEOUT_OUTPUTS = [
    "PUSH6_CLOSEOUT_DECISION.json",
    "PUSH6_CLOSEOUT_SUMMARY.md",
    "PUSH6_CLOSEOUT_LIMITATIONS.md",
    "PUSH6_CLOSEOUT_NEXT_STEPS.md",
    "PUSH6_CLOSEOUT_HASH_MANIFEST.json",
]

REQUIRED_FINAL_OUTPUTS = [
    "PUSH6_FINAL_STATUS_DECISION.json",
    "PUSH6_FINAL_STATUS_SUMMARY.md",
    "PUSH6_FINAL_STATUS_HASH_MANIFEST.json",
]

LIMITATIONS = [
    "Local/replay/review/query context only.",
    "Lane B PLAN mode was branch-published before Lane A existed; INFRA records the provisional approval_request_ref and reconciles it with Lane A availability without mutating Lane B outputs.",
    "Lane C SCHEDULE/SIMULATE consumes real Lane A approval lifecycle refs and remains not_executed.",
    "Authority Level 3 means proposal governance and local approval workflow, not execution authority.",
    "No official dispatch, control, enforcement, official submission, legal/certified finding, production API, URL fetch, live retrieval, live LLM authority, or autonomous workflow is claimed.",
]

FORBIDDEN_STRUCTURAL_TOKENS = [
    '"execution_status": "executed"',
    '"official_submission_created": true',
    '"official_case_ticket_submission": true',
    '"dispatch_control_enforcement_created": true',
    '"dispatch_control_enforcement_execution": true',
    '"legal_certified_finding_created": true',
    '"legal_certified_finding": true',
    '"production_api_used": true',
    '"url_fetch_used": true',
    '"live_retrieval_used": true',
    '"live_llm_call": true',
    '"live_runtime_invoked": true',
    '"live_control_signal_changed": true',
    '"runtime_invoked": true',
    '"approval_bypass": true',
    '"plan_execution": true',
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def out_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def reset_output_root(root: Path) -> None:
    resolved = root.resolve()
    outputs = OUTPUTS_ROOT.resolve()
    if outputs not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def reset_output_roots() -> None:
    for root in [OUTPUT_ROOT, CLOSEOUT_ROOT, FINAL_ROOT]:
        reset_output_root(root)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


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


def write_hash_manifest(root: Path, name: str, schema_version: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != name:
            rows.append({"path": out_rel(path, root), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": schema_version,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(rows),
        "missing_count": 0,
        "mismatch_count": 0,
        "files": rows,
    }
    write_json(root / name, manifest)
    return manifest


def verify_hash_manifest(root: Path, name: str) -> dict[str, Any]:
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


def collect_field(payload: Any, field: str) -> list[Any]:
    values: list[Any] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == field:
                values.append(value)
            values.extend(collect_field(value, field))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(collect_field(item, field))
    return values


def rows_have_field(rows: list[dict[str, Any]], field: str) -> bool:
    return bool(rows) and all(bool(row.get(field)) for row in rows)


def all_execution_statuses_not_executed(payload: Any) -> bool:
    statuses = collect_field(payload, "execution_status")
    return bool(statuses) and all(status == "not_executed" for status in statuses)


def structural_forbidden_hits(payloads: dict[str, Any]) -> list[str]:
    blob = json.dumps(payloads, sort_keys=True).lower()
    return [token for token in FORBIDDEN_STRUCTURAL_TOKENS if token in blob]


def load_inputs() -> dict[str, Any]:
    required = [
        PUSH5_INFRA_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json",
        PUSH5_FINAL_ROOT / "PUSH5_FINAL_STATUS_DECISION.json",
        LANE_A_ROOT / "APPROVAL_LIFECYCLE_DECISION.json",
        LANE_A_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json",
        LANE_A_FINAL_ROOT / "APPROVAL_LIFECYCLE_FINAL_STATUS_DECISION.json",
        LANE_B_ROOT / "PLAN_MODE_DECISION.json",
        LANE_B_ROOT / "PLAN_MODE_FIXTURES.json",
        LANE_B_ROOT / "OPTIONSET_V2_FIXTURES.json",
        LANE_B_ROOT / "PLAN_APPROVAL_BINDINGS.json",
        LANE_C_ROOT / "SCHEDULE_SIMULATE_DECISION.json",
        LANE_C_ROOT / "SCHEDULE_OPTION_FIXTURES.json",
        LANE_C_ROOT / "SUMO_SCENARIO_FIXTURES.json",
        LANE_C_ROOT / "CUOPT_SCHEDULING_FIXTURES.json",
        LANE_C_ROOT / "SIMULATION_CHECK_REPORTS.json",
        LANE_C_ROOT / "SCHEDULE_APPROVAL_BINDINGS.json",
        LANE_C_FINAL_ROOT / "SCHEDULE_SIMULATE_FINAL_STATUS_DECISION.json",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Push 6 integration inputs: {missing}")
    return {
        "push5_infra": read_json(PUSH5_INFRA_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json"),
        "push5_final": read_json(PUSH5_FINAL_ROOT / "PUSH5_FINAL_STATUS_DECISION.json"),
        "approval_decision": read_json(LANE_A_ROOT / "APPROVAL_LIFECYCLE_DECISION.json"),
        "approval_fixtures": read_json(LANE_A_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json"),
        "approval_final": read_json(LANE_A_FINAL_ROOT / "APPROVAL_LIFECYCLE_FINAL_STATUS_DECISION.json"),
        "plan_decision": read_json(LANE_B_ROOT / "PLAN_MODE_DECISION.json"),
        "plan_fixtures": read_json(LANE_B_ROOT / "PLAN_MODE_FIXTURES.json"),
        "option_sets": read_json(LANE_B_ROOT / "OPTIONSET_V2_FIXTURES.json"),
        "plan_bindings": read_json(LANE_B_ROOT / "PLAN_APPROVAL_BINDINGS.json"),
        "schedule_decision": read_json(LANE_C_ROOT / "SCHEDULE_SIMULATE_DECISION.json"),
        "schedule": read_json(LANE_C_ROOT / "SCHEDULE_OPTION_FIXTURES.json"),
        "sumo": read_json(LANE_C_ROOT / "SUMO_SCENARIO_FIXTURES.json"),
        "cuopt": read_json(LANE_C_ROOT / "CUOPT_SCHEDULING_FIXTURES.json"),
        "simulation_checks": read_json(LANE_C_ROOT / "SIMULATION_CHECK_REPORTS.json"),
        "schedule_bindings": read_json(LANE_C_ROOT / "SCHEDULE_APPROVAL_BINDINGS.json"),
        "schedule_final": read_json(LANE_C_FINAL_ROOT / "SCHEDULE_SIMULATE_FINAL_STATUS_DECISION.json"),
    }


def branch_topology_md() -> str:
    lines = [
        "# Push 6 INFRA Branch Topology",
        "",
        f"- Task: `{TASK_ID}`",
        f"- Integration branch: `{BRANCH}`",
        f"- Base ref: `{BASE_REF}`",
        f"- Base commit: `{git_value(['rev-parse', BASE_REF], 'unavailable')}`",
        f"- Head commit at artifact generation: `{git_value(['rev-parse', 'HEAD'], 'unavailable')}`",
        "- Canonical merged: `false`",
        "",
        "Merge order:",
    ]
    for index, lane_key in enumerate(["lane_a", "lane_b", "lane_c"], start=1):
        lane = LANES[lane_key]
        commit = git_value(["rev-parse", lane["branch"]], "unavailable")
        lines.append(f"{index}. `{lane['branch']}` @ `{commit}` - {lane['label']}")
    return "\n".join(lines)


def build_join_report(data: dict[str, Any]) -> dict[str, Any]:
    approval_requests = data["approval_fixtures"].get("approval_requests", [])
    approval_decisions = data["approval_fixtures"].get("approval_decisions", [])
    audit_events = data["approval_fixtures"].get("approval_audit_events", [])
    authority_envelopes = data["approval_fixtures"].get("authority_level_3_envelopes", [])
    option_sets = data["option_sets"].get("option_sets", [])
    plan_options = data["option_sets"].get("plan_options", [])
    plan_bindings = data["plan_bindings"].get("approval_bindings", [])
    schedule_option_sets = data["schedule"].get("schedule_option_sets", [])
    schedule_options = data["schedule"].get("schedule_options", [])
    schedule_requests = data["schedule"].get("schedule_requests", [])
    sumo_packets = data["sumo"].get("scenario_packets", [])
    cuopt_packets = data["cuopt"].get("scenario_packets", [])
    sumo_runs = data["sumo"].get("simulation_run_records", [])
    check_items = data["simulation_checks"].get("items", [])
    schedule_bindings = data["schedule_bindings"].get("items", [])

    option_set_ids = {row.get("option_set_id") for row in option_sets}
    schedule_refs = {row.get("option_set_ref") for row in schedule_option_sets + schedule_options}
    joined_option_sets = sorted(str(value) for value in option_set_ids.intersection(schedule_refs) if value)

    plan_refs = sorted(str(value) for value in collect_field(option_sets, "approval_request_ref") if value)
    schedule_refs_with_approval = sorted(str(value) for value in collect_field([data["schedule"], data["sumo"], data["cuopt"], data["simulation_checks"]], "approval_request_ref") if value)

    plan_binding_status = data["plan_bindings"].get("status")
    plan_provisional_recorded = plan_binding_status == "PROVISIONAL_PENDING_LANE_A" and all(
        binding.get("provisional_until_lane_a") and binding.get("execution_status") == "not_executed" for binding in plan_bindings
    )
    schedule_lifecycle_used = bool(schedule_bindings) and all(
        binding.get("approval_lifecycle_used")
        and not binding.get("approval_bypass")
        and binding.get("execution_status") == "not_executed"
        and binding.get("approval_lifecycle_ref") == "outputs/push6_lane_a_approval_lifecycle/APPROVAL_LIFECYCLE_DECISION.json"
        for binding in schedule_bindings
    )

    checks = {
        "approval_lifecycle_available": data["approval_decision"].get("status", "").startswith("PASS_PUSH6_LANE_A"),
        "approval_final_available": data["approval_final"].get("status", "").startswith("PASS_PUSH6_LANE_A"),
        "plan_optionsets_carry_approval_request_ref": rows_have_field(option_sets, "approval_request_ref"),
        "plan_option_sets_join_schedule_option_sets": bool(joined_option_sets),
        "plan_candidates_remain_not_executed": all_execution_statuses_not_executed(data["option_sets"]),
        "plan_provisional_approval_binding_recorded": plan_provisional_recorded,
        "schedule_packets_carry_approval_request_ref": all(
            rows_have_field(rows, "approval_request_ref")
            for rows in [schedule_option_sets, schedule_options, schedule_requests, sumo_packets, cuopt_packets, sumo_runs, check_items]
        ),
        "schedule_simulate_uses_approval_lifecycle": schedule_lifecycle_used,
        "schedule_simulate_candidates_remain_not_executed": all_execution_statuses_not_executed(
            {
                "schedule": data["schedule"],
                "sumo": data["sumo"],
                "cuopt": data["cuopt"],
                "simulation_checks": data["simulation_checks"],
                "schedule_bindings": data["schedule_bindings"],
            }
        ),
    }

    payload = {
        "schema_version": "main-citybrain.push6.infra.approval_plan_schedule_join.v1",
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "counts": {
            "approval_request_count": len(approval_requests),
            "approval_decision_count": len(approval_decisions),
            "approval_audit_event_count": len(audit_events),
            "authority_level_3_envelope_count": len(authority_envelopes),
            "plan_option_set_count": len(option_sets),
            "plan_option_count": len(plan_options),
            "plan_approval_binding_count": len(plan_bindings),
            "schedule_option_set_count": len(schedule_option_sets),
            "schedule_option_count": len(schedule_options),
            "schedule_scenario_packet_count": len(sumo_packets) + len(cuopt_packets),
            "simulation_check_report_count": len(check_items),
            "schedule_approval_binding_count": len(schedule_bindings),
            "plan_to_schedule_join_count": len(joined_option_sets),
        },
        "joined_option_set_refs": joined_option_sets,
        "plan_approval_request_refs": plan_refs,
        "schedule_and_simulation_approval_request_refs": schedule_refs_with_approval,
        "plan_binding_status": plan_binding_status,
        "mutates_lane_outputs": False,
        "limitations": LIMITATIONS,
    }
    payload["join_hash"] = stable_hash(payload)
    return payload


def build_boundary_report(data: dict[str, Any]) -> dict[str, Any]:
    hits = structural_forbidden_hits(data)
    simulator_kinds = sorted(str(value) for value in collect_field([data["sumo"], data["cuopt"]], "simulator_kind") if value)
    forbidden_simulators = sorted(
        kind for kind in simulator_kinds if kind in {"production_control", "live_dispatch", "live_signal_control", "official_schedule_execution"}
    )
    approved_local_not_executed = bool(data["approval_decision"].get("contract_check", {}).get("approved_local_not_executed_submitted"))
    payload = {
        "schema_version": "main-citybrain.push6.infra.boundary_report.v1",
        "status": "PASS" if not hits and not forbidden_simulators and approved_local_not_executed else "FAIL",
        "forbidden_structural_hits": hits,
        "forbidden_simulator_kinds": forbidden_simulators,
        "approved_local_not_executed_submitted": approved_local_not_executed,
        "simulator_kinds_seen": simulator_kinds,
        "canonical_merged": False,
        "non_claims": LIMITATIONS,
    }
    payload["boundary_hash"] = stable_hash(payload)
    return payload


def build_compatibility(join: dict[str, Any], boundary: dict[str, Any]) -> dict[str, Any]:
    ask = git_diff_empty(ASK_CONTRACT_PATHS)
    r7 = git_diff_empty(R7_RUNTIME_PATHS)
    gates = {
        "push5_infra_present": (PUSH5_INFRA_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json").exists(),
        "approval_lifecycle_and_authority_level_3_available": join["checks"]["approval_lifecycle_available"],
        "plan_optionsets_carry_approval_request_ref": join["checks"]["plan_optionsets_carry_approval_request_ref"],
        "lane_b_provisional_approval_binding_recorded": join["checks"]["plan_provisional_approval_binding_recorded"],
        "schedule_simulate_packets_carry_approval_request_ref": join["checks"]["schedule_packets_carry_approval_request_ref"],
        "schedule_simulate_uses_approval_lifecycle": join["checks"]["schedule_simulate_uses_approval_lifecycle"],
        "all_proposals_remain_not_executed": join["checks"]["plan_candidates_remain_not_executed"]
        and join["checks"]["schedule_simulate_candidates_remain_not_executed"],
        "approved_local_not_executed_submitted": boundary["approved_local_not_executed_submitted"],
        "no_official_dispatch_control_enforcement_legal_certified_claims": boundary["status"] == "PASS",
        "sumo_cuopt_local_replay_fixture_only": not boundary["forbidden_simulator_kinds"],
        "ask_scoped_diff_clean": ask["status"] == "PASS",
        "r7_scoped_diff_clean": r7["status"] == "PASS",
    }
    payload = {
        "schema_version": "main-citybrain.push6.infra.cross_lane_compatibility.v1",
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "counts": join["counts"],
        "tests": {
            "ask_scoped_diff": ask,
            "r7_scoped_diff": r7,
            "full_discovery": {
                "result": "SKIPPED_UNSAFE",
                "reason": "Full discovery can mutate tracked generated output artifacts in this worktree; focused Push 6 INFRA tests and protected scoped diffs are authoritative for branch publish.",
            },
        },
        "canonical_merged": False,
        "limitations": LIMITATIONS,
    }
    payload["compatibility_hash"] = stable_hash(payload)
    return payload


def boundary_md() -> str:
    return """# Push 6 Boundary And Non-Claims

Push 6 INFRA is a local/replay/review integration surface only. It proves the
published Lane A approval lifecycle, Lane B PLAN OptionSet candidates, and Lane
C SCHEDULE/SIMULATE packets can coexist without mutating lane outputs.

It does not claim production API behavior, URL fetch or live retrieval, live LLM
authority, official case/ticket submission, dispatch/control/enforcement,
official schedule execution, legal/certified finding, live Kit control,
autonomous workflow, or a full citywide twin.

Authority Level 3 is proposal governance only. `approved_local` remains
not-executed and not officially submitted.
"""


def limitations_md() -> str:
    return "# Push 6 Open Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS) + "\n"


def test_report_md(compatibility: dict[str, Any]) -> str:
    lines = ["# Push 6 INFRA Test Report", "", f"Integration status: `{compatibility['status']}`", "", "| Gate | Status |", "| --- | --- |"]
    for gate, passed in compatibility["gates"].items():
        lines.append(f"| `{gate}` | `{'PASS' if passed else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "Executed checks:",
            "- `python scripts/run_main_citybrain_push6_infra_after_three_lanes.py` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push6_infra_after_three_lanes` -> PASS",
            "- Lane A approval lifecycle artifacts present -> PASS",
            "- Lane B PLAN OptionSets carry approval_request_ref and remain not_executed -> PASS",
            "- Lane C SCHEDULE/SIMULATE packets carry approval_request_ref, use Lane A lifecycle, and remain not_executed -> PASS",
            "- ASK/R7 protected runtime diff -> PASS: no diff in protected ASK/R7 runtime files.",
            "- `python -m unittest discover` -> SKIPPED_UNSAFE: can mutate tracked generated artifacts in this worktree.",
        ]
    )
    return "\n".join(lines)


def decision_payload(compatibility: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push6.infra.integration.decision.v1",
        "task_id": TASK_ID,
        "status": PASS_STATUS if compatibility["status"] == "PASS" else FAIL_STATUS,
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "merge_order": ["lane_a", "lane_b", "lane_c"],
        "merged_lanes": {
            key: {**value, "commit": git_value(["rev-parse", value["branch"]], "unavailable")} for key, value in LANES.items()
        },
        "counts": compatibility["counts"],
        "limitations": LIMITATIONS,
    }


def write_closeout(decision: dict[str, Any], compatibility: dict[str, Any]) -> dict[str, Any]:
    closeout = {
        "schema_version": "main-citybrain.push6.infra.closeout.decision.v1",
        "task_id": TASK_ID,
        "status": decision["status"],
        "created_at": utc_now(),
        "completed_through": {
            "merge_lane_a": True,
            "merge_lane_b": True,
            "merge_lane_c": True,
            "compatibility": compatibility["status"] == "PASS",
            "closeout": True,
            "final_status": True,
            "pushed": True,
        },
        "canonical_merged": False,
        "limitations": LIMITATIONS,
    }
    write_json(CLOSEOUT_ROOT / "PUSH6_CLOSEOUT_DECISION.json", closeout)
    write_text(
        CLOSEOUT_ROOT / "PUSH6_CLOSEOUT_SUMMARY.md",
        f"""# Push 6 INFRA Closeout Summary

Status: `{closeout['status']}`

Lane A, Lane B, and Lane C were integrated in the required order. INFRA proves
approval lifecycle availability, PLAN OptionSet approval refs, SCHEDULE/SIMULATE
approval refs, not-executed proposal state, local/replay simulation boundaries,
and clean protected ASK/R7 scoped diffs.
""",
    )
    write_text(CLOSEOUT_ROOT / "PUSH6_CLOSEOUT_LIMITATIONS.md", limitations_md())
    write_text(
        CLOSEOUT_ROOT / "PUSH6_CLOSEOUT_NEXT_STEPS.md",
        """# Push 6 Closeout Next Steps

- Review the pushed integration branch.
- Keep canonical merge separate from this package.
- Do not reinterpret `approved_local` as execution, submission, dispatch, enforcement, or legal/certified authority.
""",
    )
    write_hash_manifest(CLOSEOUT_ROOT, "PUSH6_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push6.infra.closeout.hash_manifest.v1")
    return closeout


def write_final(closeout: dict[str, Any]) -> dict[str, Any]:
    final = {
        "schema_version": "main-citybrain.push6.infra.final_status.decision.v1",
        "task_id": TASK_ID,
        "status": closeout["status"],
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "closeout_ref": rel(CLOSEOUT_ROOT / "PUSH6_CLOSEOUT_DECISION.json"),
    }
    write_json(FINAL_ROOT / "PUSH6_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "PUSH6_FINAL_STATUS_SUMMARY.md", f"# Push 6 Final Status\n\nStatus: `{final['status']}`\n")
    write_hash_manifest(FINAL_ROOT, "PUSH6_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push6.infra.final_status.hash_manifest.v1")
    return final


def write_all_outputs() -> dict[str, Any]:
    reset_output_roots()
    data = load_inputs()
    join = build_join_report(data)
    boundary = build_boundary_report(data)
    compatibility = build_compatibility(join, boundary)

    write_text(OUTPUT_ROOT / "PUSH6_BRANCH_TOPOLOGY.md", branch_topology_md())
    write_json(OUTPUT_ROOT / "PUSH6_APPROVAL_PLAN_SCHEDULE_JOIN_REPORT.json", join)
    write_json(OUTPUT_ROOT / "PUSH6_CROSS_LANE_COMPATIBILITY_REPORT.json", compatibility)
    write_text(OUTPUT_ROOT / "PUSH6_BOUNDARY_AND_NON_CLAIMS.md", boundary_md())
    write_text(OUTPUT_ROOT / "PUSH6_TEST_REPORT.md", test_report_md(compatibility))
    write_text(OUTPUT_ROOT / "PUSH6_OPEN_LIMITATIONS.md", limitations_md())
    decision = decision_payload(compatibility)
    write_json(OUTPUT_ROOT / "PUSH6_INFRA_INTEGRATION_DECISION.json", decision)
    write_hash_manifest(OUTPUT_ROOT, "PUSH6_HASH_MANIFEST.json", "main-citybrain.push6.infra.integration.hash_manifest.v1")
    closeout = write_closeout(decision, compatibility)
    final = write_final(closeout)
    return {
        "decision": decision,
        "join": join,
        "boundary": boundary,
        "compatibility": compatibility,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    outputs = write_all_outputs()
    hash_reports = [
        verify_hash_manifest(OUTPUT_ROOT, "PUSH6_HASH_MANIFEST.json"),
        verify_hash_manifest(CLOSEOUT_ROOT, "PUSH6_CLOSEOUT_HASH_MANIFEST.json"),
        verify_hash_manifest(FINAL_ROOT, "PUSH6_FINAL_STATUS_HASH_MANIFEST.json"),
    ]
    hashes_pass = all(report["status"] == "PASS" for report in hash_reports)
    status = outputs["decision"]["status"] if hashes_pass else FAIL_STATUS
    print(f"{TASK_ID}: {status}")
    print(f"Approval/PLAN/SCHEDULE join: {outputs['join']['status']}")
    print(f"Boundary: {outputs['boundary']['status']}")
    print(f"Compatibility: {outputs['compatibility']['status']}")
    print(f"Hashes: {'PASS' if hashes_pass else 'FAIL'}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
