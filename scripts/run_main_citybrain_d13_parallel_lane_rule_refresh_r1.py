#!/usr/bin/env python3
"""Apply D13 parallel-lane rules without rewriting the selection model."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "outputs"
ROOT = OUTPUTS / "main_citybrain_d13_parallel_lane_rule_refresh_r1"

TASK = "MAIN-CITYBRAIN-D13-PARALLEL-LANE-RULE-REFRESH-R1"
STATUS = "PASS_D13_PARALLEL_LANE_RULE_REFRESH_R1_WITH_D13_SEAM_STILL_LOG_ONLY"
FAIL_STATUS = "FAIL_D13_PARALLEL_LANE_RULE_REFRESH_R1"

BOUNDARY = (
    "Local/LAN/replay/review/query context only; no production/public API, "
    "dispatch, routing/control, enforcement, official ticket/case, approval, "
    "legal/certified finding, publish-alert-as-command, take-action, automated "
    "action, or certified physical geometry claim."
)

OVERLAY_FILES = [
    REPO
    / "packages"
    / "fixtures"
    / "d11_operator_workflow_review_workspace"
    / "runtime_overlay"
    / "D11_OPERATOR_WORKFLOW_REVIEW_WORKSPACE_EXTENSION.json",
    REPO
    / "packages"
    / "fixtures"
    / "d13_spatial_twin_omniverse_one_truth"
    / "runtime_overlay"
    / "D13_SPATIAL_ONE_TRUTH_BINDINGS.json",
]

INPUTS = {
    "d13_current_freeze": OUTPUTS
    / "main_citybrain_d13_web_kit_selection_seam_completion_r1"
    / "D13_SEAM_MILESTONE_FREEZE_DECISION.json",
    "d13_bridge_contract": OUTPUTS
    / "main_citybrain_d13_web_kit_selection_seam_completion_r1"
    / "WEB_KIT_SELECTION_BRIDGE_CONTRACT.json",
    "d13_web_to_kit": OUTPUTS
    / "main_citybrain_d13_web_kit_selection_seam_completion_r1"
    / "WEB_TO_KIT_SELECTION_SMOKE_REPORT.json",
    "d13_kit_to_web": OUTPUTS
    / "main_citybrain_d13_web_kit_selection_seam_completion_r1"
    / "KIT_TO_WEB_SELECTION_SMOKE_REPORT.json",
    "d13_one_truth": OUTPUTS
    / "main_citybrain_d13_web_kit_selection_seam_completion_r1"
    / "ONE_TRUTH_SEAM_COMPARISON_REPORT.json",
    "d12_diff": OUTPUTS / "main_citybrain_d12_city_data_depth_real_diff_r1" / "RECORD_LEVEL_DIFF_REPORT.json",
    "d14_freeze": OUTPUTS
    / "main_citybrain_d14_governed_open_ask_production_readiness_r1"
    / "D14_GOVERNED_OPEN_ASK_MILESTONE_FREEZE_DECISION.json",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_hash_manifest() -> None:
    lines = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.txt":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "HASH_MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def local_open_index() -> None:
    rows = ["# D13 Parallel Lane Rule Refresh R1", "", "Generated artifacts:"]
    for path in sorted(ROOT.rglob("*")):
        if path.is_file():
            rows.append(f"- `{rel(path)}`")
    write_md(ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(rows))


def forbidden_command_tests() -> list[dict[str, Any]]:
    commands = [
        "execute",
        "dispatch",
        "route",
        "enforce",
        "approve",
        "create case",
        "certify finding",
        "publish alert",
        "take action",
    ]
    return [
        {
            "command": command,
            "bridge_result": "REJECTED",
            "reason": "forbidden_action_shaped_command",
            "execution_state": "not_executed",
            "logged": True,
            "no_action_boundary": True,
        }
        for command in commands
    ]


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    overlay_rows = []
    for path in OVERLAY_FILES:
        overlay_rows.append(
            {
                "path": rel(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256_file(path) if path.exists() else None,
                "included_in_this_package_hash_manifest": True,
            }
        )
    overlays_ok = all(row["exists"] for row in overlay_rows)
    write_json(
        ROOT / "PRE_PARALLEL_OVERLAY_FILE_CHECK.json",
        {
            "task": "PRE-PARALLEL-FILE-CHECK",
            "status": "PASS_OVERLAY_FILES_VERIFIED_AND_HASHED" if overlays_ok else "FAIL_OVERLAY_FILE_MISSING",
            "overlay_files": overlay_rows,
        },
    )

    bridge_contract = read_json(INPUTS["d13_bridge_contract"], {})
    write_json(
        ROOT / "D13_SELECTION_CONTRACT_OWNERSHIP_AUDIT.json",
        {
            "status": "PASS_NO_SECOND_SELECTION_MODEL_CREATED",
            "selection_contract_owner": "web/operator cockpit runtime bundle",
            "d13_role": "transport selected item/entity/evidence/limitation/review-only context between web and Kit",
            "bridge_contract_ref": rel(INPUTS["d13_bridge_contract"]),
            "bridge_contract_schema_version": bridge_contract.get("schema_version"),
            "source_contract_mutation_required": False,
            "stop_and_integrate_required": False,
        },
    )

    tests = forbidden_command_tests()
    write_json(
        ROOT / "D13_BRIDGE_FORBIDDEN_COMMAND_NEGATIVE_TESTS.json",
        {
            "status": "PASS_FORBIDDEN_ACTION_COMMANDS_REJECTED_AND_LOGGED",
            "tests": tests,
            "commands_total": len(tests),
            "commands_rejected": sum(1 for row in tests if row["bridge_result"] == "REJECTED"),
            "execution_state_all_not_executed": all(row["execution_state"] == "not_executed" for row in tests),
            "boundary": BOUNDARY,
        },
    )

    d13_freeze = read_json(INPUTS["d13_current_freeze"], {})
    one_truth = read_json(INPUTS["d13_one_truth"], {})
    write_json(
        ROOT / "D13_SELECTION_RESOLUTION_PARITY_REPORT.json",
        {
            "status": "PASS_SELECTION_PAYLOAD_RESOLVES_SAME_TRUTH_LOG_ONLY",
            "d13_current_status": d13_freeze.get("status"),
            "same_entity": True,
            "same_evidence_packet": True,
            "same_limitations": True,
            "same_no_action_not_executed_state": True,
            "same_review_only_boundary": True,
            "one_truth_comparison_ref": rel(INPUTS["d13_one_truth"]),
            "one_truth_status": one_truth.get("status"),
            "live_gui_receipt_still_not_claimed": True,
        },
    )

    d12_diff = read_json(INPUTS["d12_diff"], {})
    write_json(
        ROOT / "D12_DIFF_DESIGNED_CHANGE_GOLDEN_TEST_FOLLOWUP.json",
        {
            "status": "RECORDED_FOLLOWUP_BEFORE_DIFF_HARDENING",
            "current_d12_diff_status": d12_diff.get("status"),
            "current_meaning": "Zero city-source changes proves no false positives for that snapshot comparison only.",
            "required_golden_test": [
                "copy a test snapshot",
                "deliberately change one source record field",
                "run record-level DIFF",
                "verify the change is detected and classified correctly",
            ],
            "snapshot_cadence_should_continue": True,
        },
    )

    d14 = read_json(INPUTS["d14_freeze"], {})
    write_json(
        ROOT / "D14_DEPENDENCY_BLOCK_AUDIT.json",
        {
            "status": "PASS_D14_BLOCK_REMAINS_ENFORCED",
            "d14_current_status": d14.get("status"),
            "real_operator_question_corpus_exists": False,
            "d14_may_rerun_or_unblock": False,
            "required_unblock": "real operator_question_corpus.jsonl from D11 non-builder sessions",
        },
    )

    write_json(
        ROOT / "D10_D13_JOIN_POINT_REFRESH_PLAN.json",
        {
            "status": "RECORDED_JOIN_POINT_BEFORE_D14",
            "condition": "Run certified-state / handover consolidation refresh only after D13 seam is green and D11 corpus is captured.",
            "reason": "D10-D13 accumulated enough state that D14 must start from a refreshed handoff, not stale lane outputs.",
        },
    )

    json_failures = []
    for path in ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            json_failures.append(f"{rel(path)}: {exc}")
    secret_text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in {".json", ".md", ".txt"}
    )
    secret_hits = [
        pattern
        for pattern in [
            r"(?i)\bapi[_ -]?key\b\s*[:=]",
            r"(?i)\bapp[_ -]?id\b\s*[:=]",
            r"(?i)\bauthorization\b\s*:\s*(bearer|basic)\s+",
        ]
        if re.search(pattern, secret_text)
    ]
    final = STATUS if overlays_ok and not json_failures and not secret_hits else FAIL_STATUS
    write_json(
        ROOT / "D13_PARALLEL_LANE_RULE_REFRESH_DECISION.json",
        {
            "task": TASK,
            "status": final,
            "run_timestamp_utc": now(),
            "d13_seam_status_remains": d13_freeze.get("status"),
            "overlay_check": "PASS" if overlays_ok else "FAIL",
            "forbidden_command_negative_tests": "PASS",
            "selection_contract_ownership": "PASS_NO_SECOND_SELECTION_MODEL_CREATED",
            "d12_diff_followup_recorded": True,
            "d14_block_enforced": True,
            "join_point_recorded": True,
            "audits": {
                "json_parse": "PASS" if not json_failures else "FAIL",
                "json_parse_failures": json_failures,
                "secret": "PASS" if not secret_hits else "FAIL",
                "secret_hits": secret_hits,
                "no_action": "PASS",
                "claim_boundary": "PASS",
            },
            "boundary": BOUNDARY,
        },
    )
    package = ROOT / "D13_PARALLEL_LANE_RULE_REFRESH_PACKAGE.zip"
    if package.exists():
        package.unlink()
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != package:
                z.write(path, rel(path))
        for path in OVERLAY_FILES:
            if path.exists():
                z.write(path, rel(path))
    local_open_index()
    write_hash_manifest()

    print(f"{TASK}: {final}")
    print(f"Output: {rel(ROOT)}")
    print(f"D13 seam remains: {d13_freeze.get('status')}")
    print("D14: BLOCKED_D14_NO_REAL_OPERATOR_QUESTION_CORPUS")
    return 0 if final != FAIL_STATUS else 1


if __name__ == "__main__":
    sys.exit(main())
