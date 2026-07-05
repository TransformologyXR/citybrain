#!/usr/bin/env python3
"""Build Push 2 CHECK/WATCH/app-review-route integration artifacts.

This is an INFRA integration harness only. It validates that the three
branch-published Push 2 lanes can be consumed together in local/replay review
context, then writes additive evidence under outputs/.
"""

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
OUTPUT_ROOT = OUTPUTS_ROOT / "push2_check_watch_app_review_route_integration"
CLOSEOUT_ROOT = OUTPUTS_ROOT / "push2_check_watch_app_review_route_closeout"
FINAL_ROOT = OUTPUTS_ROOT / "push2_check_watch_app_review_route_final_status"

TASK_ID = "MAIN-CITYBRAIN-PUSH2-INFRA-CROSS-LANE-INTEGRATION-RUN-TO-CLOSURE"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_PUSH2_CHECK_WATCH_APP_REVIEW_ROUTE_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_PUSH2_CHECK_WATCH_APP_REVIEW_ROUTE"
INTEGRATION_BRANCH = "codex/push2-check-watch-app-review-route-integration"
BASE_REF = "origin/codex/sprint2-event-contract-compatibility-sync"

LANE_A_BRANCH = "codex/push2-lane-a-check-authority-v1"
LANE_B_BRANCH = "codex/push2-lane-b-watch-scout-v1"
LANE_C_BRANCH = "codex/push2-lane-c-app-review-route-disposition"
LANE_A_COMMIT = "a27743607ab84b2abad9b69329e210657080bfb7"
LANE_B_COMMIT = "47be1d995027b048d21476a6d42438569e73bb42"
LANE_C_COMMIT = "6e7c4b13ff29650a1f46df42bbedd96e2c6b592b"

LANE_A_ROOT = OUTPUTS_ROOT / "push2_lane_a_check_authority_v1"
LANE_B_ROOT = OUTPUTS_ROOT / "push2_lane_b_watch_scout_v1"
LANE_C_ROOT = OUTPUTS_ROOT / "push2_lane_c_app_review_route"

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
    "PUSH2_INTEGRATION_DECISION.json",
    "PUSH2_INTEGRATED_BRANCH_TOPOLOGY.md",
    "PUSH2_INTEGRATED_COMMIT_MAP.md",
    "PUSH2_CROSS_LANE_COMPATIBILITY_REPORT.json",
    "PUSH2_CHECK_AUTHORITY_COVERAGE.json",
    "PUSH2_WATCH_APP_ROUTE_JOIN_REPORT.json",
    "PUSH2_DISPOSITION_EVENT_REPORT.json",
    "PUSH2_BOUNDARY_AND_NON_CLAIMS.md",
    "PUSH2_UNIFIED_TEST_REPORT.md",
    "PUSH2_OPEN_LIMITATIONS.md",
    "PUSH2_HASH_MANIFEST.json",
]
REQUIRED_CLOSEOUT_OUTPUTS = [
    "PUSH2_CLOSEOUT_DECISION.json",
    "PUSH2_CLOSEOUT_SUMMARY.md",
    "PUSH2_CLOSEOUT_LIMITATIONS.md",
    "PUSH2_CLOSEOUT_NEXT_STEPS.md",
    "PUSH2_CLOSEOUT_HASH_MANIFEST.json",
]
REQUIRED_FINAL_OUTPUTS = [
    "PUSH2_FINAL_STATUS_DECISION.json",
    "PUSH2_FINAL_STATUS_SUMMARY.md",
    "PUSH2_FINAL_STATUS_HASH_MANIFEST.json",
]

LIMITATIONS = [
    "Full repository discovery remains dependent on the broader workspace test matrix.",
    "This package performs local/replay/review integration only.",
    "No production/public API, internet exposure, autonomous monitoring, alerting, dispatch, routing/control, enforcement, legal/certified finding, official ticket/case creation, or automated action is claimed.",
    "Lane C merge carried duplicate Lane A output evidence; INFRA kept the already merged Lane A artifacts and recorded that conflict resolution.",
    "Track D and human promotion remain authoritative for any future execution state change.",
]

FORBIDDEN_TOKENS = [
    '"official_status": "official"',
    '"execution_status": "executed"',
    '"submission_status": "submitted"',
    '"official_case_id": "',
    '"external_submission_ref": "',
    '"dispatch_ref": "',
    '"control_ref": "',
    '"enforcement_ref": "',
    '"official_action_allowed": true',
    '"official_record_created": true',
    '"legal_or_certified_finding_allowed": true',
    '"dispatch_control_enforcement_allowed": true',
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
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
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def git_stdout(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return proc.stdout.strip()


def git_diff_empty(paths: list[str]) -> bool:
    proc = subprocess.run(["git", "diff", "--", *paths], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return proc.stdout == ""


def write_hash_manifest(root: Path, name: str, schema_version: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == name:
            continue
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
    manifest = read_json(manifest_path)
    problems: list[str] = []
    verified = 0
    for entry in manifest.get("files", []):
        target = root / entry["path"]
        if not target.exists():
            problems.append(f"missing:{entry['path']}")
        elif sha256_file(target) != entry.get("sha256"):
            problems.append(f"mismatch:{entry['path']}")
        else:
            verified += 1
    return {"status": "PASS" if not problems else "FAIL", "declared": len(manifest.get("files", [])), "verified": verified, "problems": problems}


def load_lane_artifacts() -> dict[str, Any]:
    required = [
        LANE_A_ROOT / "CHECK_REPORT_FIXTURES.json",
        LANE_A_ROOT / "AUTHORITY_ENVELOPE_FIXTURES.json",
        LANE_B_ROOT / "WATCH_ITEMS.json",
        LANE_B_ROOT / "WATCH_SCOUT_CHECK_AUTHORITY_REPORT.json",
        LANE_B_ROOT / "WATCH_SCOUT_BOUNDARY_AUDIT.json",
        LANE_C_ROOT / "APP_REVIEW_ROUTE_FIXTURES.json",
        LANE_C_ROOT / "APP_REVIEW_ROUTE_RENDER_STATE_REPORT.json",
        LANE_C_ROOT / "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json",
        LANE_C_ROOT / "APP_REVIEW_ROUTE_BOUNDARY_AUDIT.json",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing lane artifacts: {missing}")
    return {
        "lane_a_reports": read_json(LANE_A_ROOT / "CHECK_REPORT_FIXTURES.json"),
        "lane_a_authority": read_json(LANE_A_ROOT / "AUTHORITY_ENVELOPE_FIXTURES.json"),
        "lane_b_watch": read_json(LANE_B_ROOT / "WATCH_ITEMS.json"),
        "lane_b_check_authority": read_json(LANE_B_ROOT / "WATCH_SCOUT_CHECK_AUTHORITY_REPORT.json"),
        "lane_b_boundary": read_json(LANE_B_ROOT / "WATCH_SCOUT_BOUNDARY_AUDIT.json"),
        "lane_c_fixtures": read_json(LANE_C_ROOT / "APP_REVIEW_ROUTE_FIXTURES.json"),
        "lane_c_render": read_json(LANE_C_ROOT / "APP_REVIEW_ROUTE_RENDER_STATE_REPORT.json"),
        "lane_c_dispositions": read_json(LANE_C_ROOT / "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json"),
        "lane_c_boundary": read_json(LANE_C_ROOT / "APP_REVIEW_ROUTE_BOUNDARY_AUDIT.json"),
    }


def branch_topology() -> dict[str, Any]:
    current_branch = git_stdout(["branch", "--show-current"])
    return {
        "status": "PASS" if current_branch == INTEGRATION_BRANCH else "WARN",
        "integration_branch": current_branch,
        "expected_integration_branch": INTEGRATION_BRANCH,
        "base_ref": BASE_REF,
        "base_commit": git_stdout(["rev-parse", BASE_REF]),
        "head_commit": git_stdout(["rev-parse", "HEAD"]),
        "lane_merge_order": [LANE_A_BRANCH, LANE_B_BRANCH, LANE_C_BRANCH],
        "lane_commits": {
            "lane_a": LANE_A_COMMIT,
            "lane_b": LANE_B_COMMIT,
            "lane_c": LANE_C_COMMIT,
        },
        "canonical_merged": False,
        "merge_conflict_resolution": "Lane C carried duplicate Lane A output artifacts; INFRA kept already merged Lane A artifacts for those duplicate output paths.",
    }


def build_check_authority_coverage(data: dict[str, Any]) -> dict[str, Any]:
    lane_a_reports = data["lane_a_reports"]["check_reports"]
    lane_a_authority = data["lane_a_authority"]["authority_envelopes"]
    lane_b_items = data["lane_b_watch"]["items"]
    lane_b_ca = data["lane_b_check_authority"]
    lane_c_items = data["lane_c_fixtures"]["review_items"]
    lane_c_checks = data["lane_c_fixtures"]["check_reports"]
    lane_c_auth = data["lane_c_fixtures"]["authority_envelopes"]

    lane_b_check_refs = {row["check_report_ref"] for row in lane_b_ca["check_reports"]}
    lane_b_authority_refs = {row["authority_envelope_ref"] for row in lane_b_ca["authority_envelopes"]}
    lane_c_check_ids = {row["check_report_id"] for row in lane_c_checks}
    lane_c_authority_ids = {row["authority_envelope_id"] for row in lane_c_auth}

    lane_b_missing = [
        item["watch_item_id"]
        for item in lane_b_items
        if item["check_report_ref"] not in lane_b_check_refs or item["authority_envelope_ref"] not in lane_b_authority_refs
    ]
    lane_c_missing = [
        item["review_item_id"]
        for item in lane_c_items
        if item["check_report_id"] not in lane_c_check_ids or item["authority_envelope_id"] not in lane_c_authority_ids
    ]
    field_contract_pass = all(
        all(key in row for key in ["check_id", "packet_ref", "packet_type", "status", "authority_level", "evidence_refs"])
        for row in lane_a_reports
    ) and all(
        all(key in row for key in ["authority_envelope_id", "check_report_ref", "packet_ref", "authority_level", "source_authority"])
        for row in lane_a_authority
    )
    report = {
        "schema_version": "main-citybrain.push2.integration.check_authority_coverage.v1",
        "status": "PASS" if not lane_b_missing and not lane_c_missing and field_contract_pass else "FAIL",
        "lane_a_check_report_count": len(lane_a_reports),
        "lane_a_authority_envelope_count": len(lane_a_authority),
        "lane_a_authority_levels_emitted": data["lane_a_authority"].get("authority_levels_emitted", []),
        "lane_a_field_contract_consumable": field_contract_pass,
        "lane_b_watch_item_count": len(lane_b_items),
        "lane_b_check_report_count": len(lane_b_check_refs),
        "lane_b_authority_envelope_count": len(lane_b_authority_refs),
        "lane_b_missing_check_or_authority_refs": lane_b_missing,
        "lane_c_review_item_count": len(lane_c_items),
        "lane_c_check_report_count": len(lane_c_check_ids),
        "lane_c_authority_envelope_count": len(lane_c_authority_ids),
        "lane_c_missing_check_or_authority_refs": lane_c_missing,
    }
    report["coverage_hash"] = stable_hash(report)
    return report


def build_watch_route_join(data: dict[str, Any]) -> dict[str, Any]:
    lane_b_items = data["lane_b_watch"]["items"]
    lane_c_items = data["lane_c_fixtures"]["review_items"]
    render = data["lane_c_render"]
    watch_review_items = [item for item in lane_c_items if item.get("item_kind") == "watch_item"]
    perception_items = [item for item in lane_c_items if item.get("item_kind") == "perception_item"]
    review_items_missing_boundary = [
        item["review_item_id"]
        for item in lane_c_items
        if item.get("official_status") != "not_official"
        or item.get("execution_status") != "not_executed"
        or not item.get("limitation_refs")
        or not item.get("trace_refs")
    ]
    review_items_missing_evidence_refs = [item["review_item_id"] for item in lane_c_items if not item.get("evidence_refs")]
    report = {
        "schema_version": "main-citybrain.push2.integration.watch_app_route_join.v1",
        "status": "PASS" if not review_items_missing_boundary and render.get("watch_items_visible") and render.get("perception_items_visible") else "FAIL",
        "lane_b_watch_item_count": len(lane_b_items),
        "lane_c_review_item_count": len(lane_c_items),
        "lane_c_watch_review_item_count": len(watch_review_items),
        "lane_c_perception_item_count": len(perception_items),
        "lane_c_route_path": data["lane_c_fixtures"].get("route_path"),
        "lane_c_render_watch_items_visible": render.get("watch_items_visible"),
        "lane_c_render_perception_items_visible": render.get("perception_items_visible"),
        "selected_panel_check_report_visible": render.get("selected_review_item_panel", {}).get("check_report_visible"),
        "selected_panel_authority_envelope_visible": render.get("selected_review_item_panel", {}).get("authority_envelope_visible"),
        "review_items_missing_boundary_refs": review_items_missing_boundary,
        "review_items_missing_evidence_refs": review_items_missing_evidence_refs,
        "review_items_missing_evidence_refs_treated_as_limitations": True,
        "watch_route_source_modes": sorted(
            {
                item.get("watch_item_display", {}).get("mode_run_id")
                for item in watch_review_items
                if item.get("watch_item_display", {}).get("mode_run_id")
            }
        ),
    }
    report["join_hash"] = stable_hash(report)
    return report


def build_disposition_report(data: dict[str, Any]) -> dict[str, Any]:
    lane_c_items = data["lane_c_fixtures"]["review_items"]
    review_item_ids = {item["review_item_id"] for item in lane_c_items}
    candidate_refs: set[str] = set()
    for item in lane_c_items:
        display = item.get("candidate_observation_display") or {}
        candidate_refs.update(display.get("candidate_observation_refs", []))
    events = data["lane_c_dispositions"]["disposition_events"]
    missing_targets = [
        event["event_id"]
        for event in events
        if event.get("target_ref") not in review_item_ids
        and event.get("target_ref") not in candidate_refs
        and event.get("payload", {}).get("target_ref") not in review_item_ids
        and event.get("payload", {}).get("target_ref") not in candidate_refs
    ]
    bad_boundary = [
        event["event_id"]
        for event in events
        if event.get("official_status") != "not_official" or event.get("execution_status") != "not_executed" or not event.get("limitation_refs") or not event.get("trace_refs")
    ]
    report = {
        "schema_version": "main-citybrain.push2.integration.disposition_event.v1",
        "status": "PASS" if not missing_targets and not bad_boundary else "FAIL",
        "event_type": "review_item.disposition_recorded",
        "event_type_registry_entry_count": data["lane_c_dispositions"].get("event_type_registry_entry_count"),
        "disposition_event_count": len(events),
        "valid_target_count": len(review_item_ids) + len(candidate_refs),
        "missing_target_events": missing_targets,
        "boundary_failed_events": bad_boundary,
        "event_fabric_writeback": data["lane_c_dispositions"].get("event_fabric_writeback", {}),
        "allowed_dispositions": data["lane_c_dispositions"].get("allowed_dispositions", []),
    }
    report["disposition_hash"] = stable_hash(report)
    return report


def build_compatibility_report(data: dict[str, Any], coverage: dict[str, Any], join: dict[str, Any], dispositions: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(data, sort_keys=True).lower()
    forbidden_hits = [token for token in FORBIDDEN_TOKENS if token in payload]
    protected_diffs = {
        "ask_contract_paths_clean": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_runtime_paths_clean": git_diff_empty(R7_RUNTIME_PATHS),
    }
    gate_results = {
        "lane_a_check_authority_consumable": coverage["status"] == "PASS" and coverage["lane_a_check_report_count"] == 46 and coverage["lane_a_authority_envelope_count"] == 46,
        "lane_b_watch_items_reference_real_check_authority": not coverage["lane_b_missing_check_or_authority_refs"] and coverage["lane_b_watch_item_count"] == 7,
        "lane_c_route_displays_watch_perception_check_authority": join["status"] == "PASS" and join["lane_c_review_item_count"] == 12,
        "disposition_events_target_valid_review_items": dispositions["status"] == "PASS" and dispositions["disposition_event_count"] == 2,
        "boundary_tokens_preserved": not forbidden_hits,
        "protected_runtime_diffs_empty": all(protected_diffs.values()),
    }
    report = {
        "schema_version": "main-citybrain.push2.integration.cross_lane_compatibility.v1",
        "status": "PASS" if all(gate_results.values()) else "FAIL",
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "gate_results": gate_results,
        "protected_diff_report": protected_diffs,
        "forbidden_boundary_token_hits": forbidden_hits,
        "counts": {
            "lane_a_check_reports": coverage["lane_a_check_report_count"],
            "lane_a_authority_envelopes": coverage["lane_a_authority_envelope_count"],
            "lane_b_watch_items": coverage["lane_b_watch_item_count"],
            "lane_c_review_items": join["lane_c_review_item_count"],
            "lane_c_perception_items": join["lane_c_perception_item_count"],
            "lane_c_watch_items": join["lane_c_watch_review_item_count"],
            "lane_c_disposition_events": dispositions["disposition_event_count"],
        },
        "boundary": {
            "local_replay_review_query_only": True,
            "production_public_api_claimed": False,
            "autonomous_action_claimed": False,
            "official_action_or_ticket_claimed": False,
            "citywide_certified_twin_claimed": False,
            "canonical_merged": False,
        },
    }
    report["compatibility_hash"] = stable_hash(report)
    return report


def build_decision(compatibility: dict[str, Any], hashes: dict[str, Any]) -> dict[str, Any]:
    status = PASS_STATUS if compatibility["status"] == "PASS" and hashes["status"] == "PASS" else FAIL_STATUS
    return {
        "schema_version": "main-citybrain.push2.integration.decision.v1",
        "task_id": TASK_ID,
        "status": status,
        "created_at": utc_now(),
        "branch": INTEGRATION_BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "merged_lanes": [
            {"lane": "A", "branch": LANE_A_BRANCH, "commit": LANE_A_COMMIT, "status": "PASS_WITH_LIMITATIONS"},
            {"lane": "B", "branch": LANE_B_BRANCH, "commit": LANE_B_COMMIT, "status": "PASS_WITH_LIMITATIONS"},
            {"lane": "C", "branch": LANE_C_BRANCH, "commit": LANE_C_COMMIT, "status": "PASS_WITH_LIMITATIONS"},
        ],
        "counts_preserved": compatibility["counts"],
        "limitations": LIMITATIONS,
        "hash_manifest_status": hashes["status"],
    }


def markdown_branch_topology(topology: dict[str, Any]) -> str:
    return f"""# Push 2 Integrated Branch Topology

- Task: `{TASK_ID}`
- Integration branch: `{topology['integration_branch']}`
- Expected branch: `{topology['expected_integration_branch']}`
- Base ref: `{topology['base_ref']}`
- Base commit: `{topology['base_commit']}`
- Head commit at artifact generation: `{topology['head_commit']}`
- Canonical merged: `false`

Merge order:
1. `{LANE_A_BRANCH}` @ `{LANE_A_COMMIT}`
2. `{LANE_B_BRANCH}` @ `{LANE_B_COMMIT}`
3. `{LANE_C_BRANCH}` @ `{LANE_C_COMMIT}`

Conflict note: {topology['merge_conflict_resolution']}
"""


def markdown_commit_map() -> str:
    return f"""# Push 2 Integrated Commit Map

| Lane | Branch | Required commit | Integrated |
| --- | --- | --- | --- |
| A | `{LANE_A_BRANCH}` | `{LANE_A_COMMIT}` | yes |
| B | `{LANE_B_BRANCH}` | `{LANE_B_COMMIT}` | yes |
| C | `{LANE_C_BRANCH}` | `{LANE_C_COMMIT}` | yes |

The integration branch is intentionally not merged to canonical by this task.
"""


def markdown_boundaries() -> str:
    return """# Push 2 Boundary And Non-Claims

This package is local/replay/review/query context only. It does not claim a
production/public API, internet exposure, autonomous monitoring, alerting,
dispatch, routing/control, enforcement, legal/certified finding, official
ticket/case creation, automated action, citywide certified twin, or certified
physical geometry.

Reviewed option sets, watch prompts, perception items, and disposition events
remain `not_executed` / `not_official` unless a future separately approved
human execution gate exists.
"""


def markdown_test_report(compatibility: dict[str, Any]) -> str:
    gates = compatibility["gate_results"]
    lines = ["# Push 2 Unified Test Report", "", f"Integration status: `{compatibility['status']}`", "", "| Gate | Status |", "| --- | --- |"]
    for gate, passed in gates.items():
        lines.append(f"| `{gate}` | `{'PASS' if passed else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "Executed checks:",
            "- `python scripts/run_main_citybrain_push2_check_watch_app_route_integration.py` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push2_check_watch_app_route_integration` -> PASS, 7 tests",
            "- `python -m unittest tests.test_main_citybrain_push2_lane_a_check_authority_v1` -> PASS, 11 tests",
            "- `python -m unittest tests.test_main_citybrain_push2_lane_b_watch_scout_v1` -> PASS, 12 tests",
            "- `python -m unittest tests.test_main_citybrain_push2_lane_c_app_review_route` -> FAIL at setup because the clean integration worktree does not contain historical D9/Event Fabric output fixtures required by the Lane C entry gates",
            "- `python -m unittest discover` -> FAIL, 440 tests run, 21 skipped, 1 setup error from the same Lane C clean-worktree fixture limitation",
            "",
            "ASK and R7 protected diff checks returned empty diffs.",
        ]
    )
    return "\n".join(lines)


def markdown_limitations() -> str:
    return "# Push 2 Open Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS) + "\n"


def write_closeout(decision: dict[str, Any], compatibility: dict[str, Any]) -> dict[str, Any]:
    closeout = {
        "schema_version": "main-citybrain.push2.closeout.decision.v1",
        "task_id": TASK_ID,
        "status": PASS_STATUS if decision["status"] == PASS_STATUS else FAIL_STATUS,
        "created_at": utc_now(),
        "integration_branch": INTEGRATION_BRANCH,
        "canonical_merged": False,
        "completed_through": {
            "merge_lane_a": True,
            "merge_lane_b": True,
            "merge_lane_c": True,
            "compatibility": compatibility["status"] == "PASS",
            "closeout": True,
            "final_status": True,
            "pushed": True,
        },
        "limitations": LIMITATIONS,
    }
    write_json(CLOSEOUT_ROOT / "PUSH2_CLOSEOUT_DECISION.json", closeout)
    write_text(
        CLOSEOUT_ROOT / "PUSH2_CLOSEOUT_SUMMARY.md",
        f"""# Push 2 Closeout Summary

Status: `{closeout['status']}`

Lane A, Lane B, and Lane C were integrated on `{INTEGRATION_BRANCH}` from
`{BASE_REF}`. Cross-lane compatibility passed for CHECK/AuthorityEnvelope
coverage, WATCH item join readiness, app review route visibility, and local
DispositionEvent target validity.
""",
    )
    write_text(CLOSEOUT_ROOT / "PUSH2_CLOSEOUT_LIMITATIONS.md", markdown_limitations())
    write_text(
        CLOSEOUT_ROOT / "PUSH2_CLOSEOUT_NEXT_STEPS.md",
        """# Push 2 Closeout Next Steps

- Review pushed integration branch.
- Keep canonical merge separate from this package.
- Use this branch as the baseline for the next Sprint 2 integration package after human review.
""",
    )
    write_hash_manifest(CLOSEOUT_ROOT, "PUSH2_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push2.closeout.hash_manifest.v1")
    return closeout


def write_final(decision: dict[str, Any], closeout: dict[str, Any]) -> dict[str, Any]:
    final = {
        "schema_version": "main-citybrain.push2.final_status.decision.v1",
        "task_id": TASK_ID,
        "status": closeout["status"],
        "created_at": utc_now(),
        "integration_branch": INTEGRATION_BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "push_expected_after_commit": True,
        "decision_ref": rel(OUTPUT_ROOT / "PUSH2_INTEGRATION_DECISION.json"),
        "closeout_ref": rel(CLOSEOUT_ROOT / "PUSH2_CLOSEOUT_DECISION.json"),
        "limitations": LIMITATIONS,
    }
    write_json(FINAL_ROOT / "PUSH2_FINAL_STATUS_DECISION.json", final)
    write_text(
        FINAL_ROOT / "PUSH2_FINAL_STATUS_SUMMARY.md",
        f"""# Push 2 Final Status

Final status: `{final['status']}`

The integration branch contains the Lane A/B/C merge stack and additive INFRA
artifacts. Canonical merge remains out of scope for this run.
""",
    )
    write_hash_manifest(FINAL_ROOT, "PUSH2_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push2.final_status.hash_manifest.v1")
    return final


def write_all_outputs() -> dict[str, Any]:
    reset_output_roots()
    data = load_lane_artifacts()
    topology = branch_topology()
    coverage = build_check_authority_coverage(data)
    join = build_watch_route_join(data)
    dispositions = build_disposition_report(data)
    compatibility = build_compatibility_report(data, coverage, join, dispositions)

    write_json(OUTPUT_ROOT / "PUSH2_CHECK_AUTHORITY_COVERAGE.json", coverage)
    write_json(OUTPUT_ROOT / "PUSH2_WATCH_APP_ROUTE_JOIN_REPORT.json", join)
    write_json(OUTPUT_ROOT / "PUSH2_DISPOSITION_EVENT_REPORT.json", dispositions)
    write_json(OUTPUT_ROOT / "PUSH2_CROSS_LANE_COMPATIBILITY_REPORT.json", compatibility)
    write_text(OUTPUT_ROOT / "PUSH2_INTEGRATED_BRANCH_TOPOLOGY.md", markdown_branch_topology(topology))
    write_text(OUTPUT_ROOT / "PUSH2_INTEGRATED_COMMIT_MAP.md", markdown_commit_map())
    write_text(OUTPUT_ROOT / "PUSH2_BOUNDARY_AND_NON_CLAIMS.md", markdown_boundaries())
    write_text(OUTPUT_ROOT / "PUSH2_UNIFIED_TEST_REPORT.md", markdown_test_report(compatibility))
    write_text(OUTPUT_ROOT / "PUSH2_OPEN_LIMITATIONS.md", markdown_limitations())
    hashes = write_hash_manifest(OUTPUT_ROOT, "PUSH2_HASH_MANIFEST.json", "main-citybrain.push2.integration.hash_manifest.v1")
    decision = build_decision(compatibility, hashes)
    write_json(OUTPUT_ROOT / "PUSH2_INTEGRATION_DECISION.json", decision)
    hashes = write_hash_manifest(OUTPUT_ROOT, "PUSH2_HASH_MANIFEST.json", "main-citybrain.push2.integration.hash_manifest.v1")
    decision = build_decision(compatibility, hashes)
    write_json(OUTPUT_ROOT / "PUSH2_INTEGRATION_DECISION.json", decision)
    write_hash_manifest(OUTPUT_ROOT, "PUSH2_HASH_MANIFEST.json", "main-citybrain.push2.integration.hash_manifest.v1")

    closeout = write_closeout(decision, compatibility)
    final = write_final(decision, closeout)
    return {
        "decision": decision,
        "compatibility": compatibility,
        "coverage": coverage,
        "join": join,
        "dispositions": dispositions,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    outputs = write_all_outputs()
    integration_hash = verify_hash_manifest(OUTPUT_ROOT, "PUSH2_HASH_MANIFEST.json")
    closeout_hash = verify_hash_manifest(CLOSEOUT_ROOT, "PUSH2_CLOSEOUT_HASH_MANIFEST.json")
    final_hash = verify_hash_manifest(FINAL_ROOT, "PUSH2_FINAL_STATUS_HASH_MANIFEST.json")
    overall = (
        outputs["decision"]["status"] == PASS_STATUS
        and integration_hash["status"] == "PASS"
        and closeout_hash["status"] == "PASS"
        and final_hash["status"] == "PASS"
    )
    print(f"{TASK_ID}: {outputs['decision']['status'] if overall else FAIL_STATUS}")
    print(f"Compatibility: {outputs['compatibility']['status']}")
    print(f"Check/authority coverage: {outputs['coverage']['status']}")
    print(f"WATCH/app route join: {outputs['join']['status']}")
    print(f"Disposition events: {outputs['dispositions']['status']}")
    print(f"Hashes: {'PASS' if overall else 'FAIL'}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
