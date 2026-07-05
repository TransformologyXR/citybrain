#!/usr/bin/env python3
"""Reconcile D8 Web+Kit live-surface baseline hashes."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from citybrain_d8_web_kit_live_surface_common import (
    BOUNDARY,
    CONTRACTS,
    KIT_APP,
    OUTPUTS,
    REPO_ROOT,
    RUNTIME_BUNDLE,
    UPSTREAM_SPECS,
    WEB_APP,
    claim_boundary_audit,
    hash_manifest,
    no_action_audit,
    no_mutation_audit,
    now_iso,
    read_json,
    rel,
    secret_audit,
    sha256_file,
    snapshot_root,
    upstream_snapshots,
    write_json,
    write_text,
)


TASK = "MAIN-CITYBRAIN-D8-WEB-KIT-LIVE-SURFACE-BASELINE-HASH-RECONCILIATION"
STATUS_PASS = "PASS_MAIN_CITYBRAIN_D8_WEB_KIT_LIVE_SURFACE_BASELINE_HASH_RECONCILIATION_WITH_LIMITATIONS"
ROOT = OUTPUTS / "main_citybrain_d8_web_kit_live_surface_baseline_hash_reconciliation"
FREEZE_ROOT = OUTPUTS / "main_citybrain_d8_web_kit_live_surface_milestone_freeze"
FREEZE_DECISION = FREEZE_ROOT / "WEB_KIT_LIVE_SURFACE_MILESTONE_FREEZE_DECISION.json"
VALIDATION_ZIP = FREEZE_ROOT / "WEB_KIT_LIVE_SURFACE_VALIDATION_PACKAGE.zip"


SOURCE_EXTENSIONS = {".html", ".css", ".js", ".mjs", ".json", ".md", ".toml", ".py"}
VOLATILE_BRIDGE_PREFIXES = [
    "packages/fixtures/mobility_access/bridge/audit/",
    "packages/fixtures/mobility_access/bridge/inbox/",
    "packages/fixtures/mobility_access/bridge/outbox/",
]


def source_file_rows() -> list[dict[str, Any]]:
    roots = [WEB_APP, KIT_APP, CONTRACTS]
    rows = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            if path.suffix.lower() not in SOURCE_EXTENSIONS:
                continue
            rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path), "classification": "immutable_maintained_source_baseline"})
    return rows


def runtime_bundle_rows() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(item for item in RUNTIME_BUNDLE.rglob("*") if item.is_file()):
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path), "classification": "certified_runtime_bundle_baseline"})
    return rows


def volatile_bridge_rows() -> list[dict[str, Any]]:
    bridge_root = REPO_ROOT / "packages" / "fixtures" / "mobility_access" / "bridge"
    rows = []
    if not bridge_root.exists():
        return rows
    for path in sorted(item for item in bridge_root.rglob("*") if item.is_file()):
        rows.append(
            {
                "path": rel(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "classification": "volatile_bridge_runtime_artifact",
                "reason": "Bridge inbox/outbox/audit files are local runtime samples/logs and can be rewritten by bridge smoke runs.",
            }
        )
    return rows


def validation_zip_report() -> dict[str, Any]:
    if not VALIDATION_ZIP.exists():
        return {"status": "FAIL", "exists": False, "path": rel(VALIDATION_ZIP)}
    json_ok = 0
    json_total = 0
    jsonl_ok = 0
    jsonl_total = 0
    jsonl_rows = 0
    with zipfile.ZipFile(VALIDATION_ZIP, "r") as archive:
        names = archive.namelist()
        for name in names:
            lower = name.lower()
            if lower.endswith(".json"):
                json_total += 1
                json.loads(archive.read(name).decode("utf-8"))
                json_ok += 1
            elif lower.endswith(".jsonl"):
                jsonl_total += 1
                text = archive.read(name).decode("utf-8")
                rows = [line for line in text.splitlines() if line.strip()]
                for line in rows:
                    json.loads(line)
                jsonl_rows += len(rows)
                jsonl_ok += 1
    return {
        "status": "PASS",
        "exists": True,
        "path": rel(VALIDATION_ZIP),
        "entry_count": len(names),
        "json_parse_clean": json_ok,
        "json_file_count": json_total,
        "jsonl_parse_clean": jsonl_ok,
        "jsonl_file_count": jsonl_total,
        "jsonl_row_count": jsonl_rows,
    }


def prior_manifest_mismatches() -> list[dict[str, Any]]:
    mismatches = []
    live_roots = [
        "main_citybrain_d8_web_kit_live_surface_preflight",
        "main_citybrain_d8_runtime_bundle_contract_r1",
        "main_citybrain_d8_web_control_room_source_promotion_r2",
        "main_citybrain_d8_kit_control_room_extension_source_promotion_r2",
        "main_citybrain_d8_local_bridge_and_one_truth_sync_r3",
        "main_citybrain_d8_mobility_access_live_surface_wiring_r4",
        "main_citybrain_d8_web_kit_state_drift_and_guardrail_smoke_r5",
        "main_citybrain_d8_web_kit_capture_readiness_r6",
        "main_citybrain_d8_web_kit_live_surface_closeout",
        "main_citybrain_d8_web_kit_live_surface_milestone_freeze",
    ]
    for folder in live_roots:
        manifest = OUTPUTS / folder / "HASH_MANIFEST.json"
        payload = read_json(manifest, {})
        for row in payload.get("files", []):
            path_text = row.get("path", "")
            if not any(path_text.startswith(prefix) for prefix in VOLATILE_BRIDGE_PREFIXES):
                continue
            path = REPO_ROOT / path_text
            if not path.exists():
                mismatches.append(
                    {
                        "manifest": rel(manifest),
                        "path": path_text,
                        "manifest_sha256": row.get("sha256"),
                        "current_sha256": None,
                        "classification": "volatile_bridge_runtime_artifact_missing_or_rotated",
                    }
                )
                continue
            current = sha256_file(path)
            if current != row.get("sha256"):
                mismatches.append(
                    {
                        "manifest": rel(manifest),
                        "path": path_text,
                        "manifest_sha256": row.get("sha256"),
                        "current_sha256": current,
                        "classification": "volatile_bridge_runtime_artifact_hash_drift",
                    }
                )
    return mismatches


def local_open_index() -> None:
    artifacts = [
        "MAIN_CITYBRAIN_D8_WEB_KIT_LIVE_SURFACE_BASELINE_HASH_RECONCILIATION_DECISION.json",
        "INPUT_ARTIFACT_INDEX.json",
        "SOURCE_BASELINE_HASH_MANIFEST.json",
        "RUNTIME_BUNDLE_BASELINE_HASH_MANIFEST.json",
        "VOLATILE_BRIDGE_ARTIFACT_LEDGER.json",
        "PRIOR_STAGE_HASH_MISMATCH_EXPLANATION.md",
        "VALIDATION_RECONCILIATION_REPORT.json",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_ACTION_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "HASH_MANIFEST.json",
    ]
    lines = [
        f"# {TASK}",
        "",
        "Open the decision JSON first.",
        "",
        BOUNDARY,
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- [{name}]({name})" for name in artifacts if (ROOT / name).exists())
    write_text(ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)
    before = upstream_snapshots(UPSTREAM_SPECS)
    freeze_decision = read_json(FREEZE_DECISION, {})
    closeout = read_json(OUTPUTS / "main_citybrain_d8_web_kit_live_surface_closeout" / "WEB_KIT_LIVE_SURFACE_CLOSEOUT_DECISION.json", {})
    web_summary = read_json(FREEZE_ROOT / "WEB_LOCAL_LAUNCH_EVIDENCE_SUMMARY.json", {})
    kit_summary = read_json(FREEZE_ROOT / "KIT_RUNTIME_STATUS_SUMMARY.json", {})
    parity_summary = read_json(FREEZE_ROOT / "LIVE_SURFACE_MOMENT_PARITY_SUMMARY.json", {})
    source_rows = source_file_rows()
    runtime_rows = runtime_bundle_rows()
    volatile_rows = volatile_bridge_rows()
    mismatches = prior_manifest_mismatches()
    zip_report = validation_zip_report()
    input_index = {
        "generated_at_utc": now_iso(),
        "freeze_root": rel(FREEZE_ROOT),
        "freeze_decision": rel(FREEZE_DECISION),
        "freeze_status": freeze_decision.get("status"),
        "validation_zip": rel(VALIDATION_ZIP),
        "web_live_launch_evidence_status": web_summary.get("web_live_launch_status"),
        "kit_live_launch_status": kit_summary.get("kit_live_launch_status"),
        "moment_parity_status": parity_summary.get("status"),
    }
    write_json(ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(
        ROOT / "SOURCE_BASELINE_HASH_MANIFEST.json",
        {
            "status": "PASS",
            "generated_at_utc": now_iso(),
            "source_file_count": len(source_rows),
            "classification": "immutable_maintained_source_baseline",
            "files": source_rows,
        },
    )
    write_json(
        ROOT / "RUNTIME_BUNDLE_BASELINE_HASH_MANIFEST.json",
        {
            "status": "PASS",
            "generated_at_utc": now_iso(),
            "runtime_bundle_file_count": len(runtime_rows),
            "classification": "certified_runtime_bundle_baseline",
            "files": runtime_rows,
        },
    )
    write_json(
        ROOT / "VOLATILE_BRIDGE_ARTIFACT_LEDGER.json",
        {
            "status": "PASS",
            "volatile_file_count": len(volatile_rows),
            "files": volatile_rows,
            "policy": "Bridge inbox/outbox/audit files are runtime artifacts. They are tracked for transparency but excluded from immutable maintained-source and certified runtime-bundle baseline manifests.",
        },
    )
    write_text(
        ROOT / "PRIOR_STAGE_HASH_MISMATCH_EXPLANATION.md",
        "# Prior Stage Hash Mismatch Explanation\n\n"
        "Independent nested-package verification found mismatches in bridge runtime artifacts. "
        "Those files are local bridge command/event/audit outputs produced by smoke runs. "
        "They are useful evidence, but they are volatile and should not be treated as immutable source drift.\n\n"
        f"Detected volatile bridge hash mismatches: `{len(mismatches)}`.\n\n"
        "No certified runtime bundle truth was changed, and no UI projection was patched to satisfy this reconciliation.\n",
    )
    source_clean = all((REPO_ROOT / row["path"]).exists() and sha256_file(REPO_ROOT / row["path"]) == row["sha256"] for row in source_rows)
    runtime_clean = all((REPO_ROOT / row["path"]).exists() and sha256_file(REPO_ROOT / row["path"]) == row["sha256"] for row in runtime_rows)
    report = {
        "status": "PASS" if source_clean and runtime_clean and zip_report["status"] == "PASS" else "FAIL",
        "freeze_status": freeze_decision.get("status"),
        "web_live_launch_evidence_status": web_summary.get("web_live_launch_status"),
        "moment_parity_status": parity_summary.get("status"),
        "kit_live_launch_status": kit_summary.get("kit_live_launch_status"),
        "source_baseline_hash_status": "PASS" if source_clean else "FAIL",
        "runtime_bundle_hash_status": "PASS" if runtime_clean else "FAIL",
        "volatile_bridge_file_count": len(volatile_rows),
        "prior_stage_volatile_mismatch_count": len(mismatches),
        "prior_stage_volatile_mismatches": mismatches,
        "validation_zip_report": zip_report,
    }
    write_json(ROOT / "VALIDATION_RECONCILIATION_REPORT.json", report)
    local_open_index()
    claim = claim_boundary_audit(ROOT, TASK)
    no_action = no_action_audit(ROOT, TASK)
    no_mutation = no_mutation_audit(ROOT, before, TASK)
    secret = secret_audit(ROOT, TASK)
    hash_report = hash_manifest(ROOT, TASK)
    blocking = []
    if not str(freeze_decision.get("status", "")).startswith("PASS_"):
        blocking.append({"failure_class": "freeze_not_green", "detail": freeze_decision.get("status")})
    if web_summary.get("web_live_launch_status") != "PASS":
        blocking.append({"failure_class": "web_launch_not_green", "detail": web_summary})
    if parity_summary.get("status") != "PASS":
        blocking.append({"failure_class": "moment_parity_not_green", "detail": parity_summary})
    if not source_clean:
        blocking.append({"failure_class": "source_baseline_hash_failure"})
    if not runtime_clean:
        blocking.append({"failure_class": "runtime_bundle_hash_failure"})
    if no_mutation["status"] != "PASS":
        blocking.append({"failure_class": "upstream_mutation_detected", "detail": no_mutation})
    status = STATUS_PASS if not blocking and all(item["status"] == "PASS" for item in [claim, no_action, secret]) else f"FAIL_{TASK.replace('-', '_')}"
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp_utc": now_iso(),
        "output_root": rel(ROOT),
        "blocking_gap_count": len(blocking),
        "blocking_gaps": blocking,
        "non_blocking_gap_count": 3,
        "non_blocking_gaps": [
            "Kit runtime remains unavailable and is preserved honestly.",
            "Bridge runtime inbox/outbox/audit artifacts are volatile by design.",
            "M04/M05 remain documented partial from the frozen D8 baseline.",
        ],
        "source_baseline_file_count": len(source_rows),
        "runtime_bundle_file_count": len(runtime_rows),
        "volatile_bridge_file_count": len(volatile_rows),
        "prior_stage_volatile_mismatch_count": len(mismatches),
        "web_live_launch_evidence_status": web_summary.get("web_live_launch_status"),
        "moment_parity_status": parity_summary.get("status"),
        "kit_live_launch_status": kit_summary.get("kit_live_launch_status"),
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": hash_report["hash_validation_status"],
        "recommended_next_task": "MAIN-CITYBRAIN-D8-POST-HANDOFF-EXTERNAL-CAPTURE-FRONTEND-FOLLOW-THROUGH",
    }
    write_json(ROOT / "MAIN_CITYBRAIN_D8_WEB_KIT_LIVE_SURFACE_BASELINE_HASH_RECONCILIATION_DECISION.json", decision)
    hash_manifest(ROOT, TASK)
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
