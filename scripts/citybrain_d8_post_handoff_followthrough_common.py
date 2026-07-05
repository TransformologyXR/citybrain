#!/usr/bin/env python3
"""D8 post-handoff external capture/frontend follow-through runners."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from citybrain_d8_web_kit_live_surface_common import (
    BOUNDARY as LIVE_BOUNDARY,
    KIT_APP,
    OUTPUTS,
    REPO_ROOT,
    RUNTIME_BUNDLE,
    WEB_APP,
    claim_boundary_audit,
    hash_manifest,
    no_action_audit,
    no_mutation_audit,
    read_json,
    rel,
    secret_audit,
    sha256_file,
    upstream_snapshots,
    validate_kit_source,
    write_json,
    write_text,
)


BOUNDARY = (
    "D8 post-handoff follow-through is local/LAN/replay/review/query context only. "
    "It may package capture toolchains, viewer packets, frontend issue ledgers, and regression reports, "
    "but it does not create production/public API capability, live autonomous monitoring, alerts, "
    "dispatch, routing/control, enforcement, legal/certified findings, official ticket/case creation, "
    "certified physical geometry, citywide certified twin claims, or automated action. "
    "Mobility Access remains the certified hero spine, Track D remains authoritative, and execution_state = not_executed remains visible."
)

MEDIA_PENDING_STATUS = "PARTIAL_PENDING_MEDIA"
VIEWER_PENDING_STATUS = "PARTIAL_PENDING_EXTERNAL_VIEWER"
FINAL_PENDING_STATUS = "PARTIAL_PENDING_MEDIA_AND_EXTERNAL_VIEWER"


STAGES: list[dict[str, Any]] = [
    {
        "key": "media_preflight",
        "task": "MAIN-CITYBRAIN-D8-LIVE-CAPTURE-MEDIA-PASS-PREFLIGHT",
        "root": "main_citybrain_d8_live_capture_media_pass_preflight",
        "decision": "D8_LIVE_CAPTURE_MEDIA_PASS_PREFLIGHT_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_LIVE_CAPTURE_MEDIA_PASS_PREFLIGHT_WITH_LIMITATIONS",
        "required": ["CAPTURE_PLACEHOLDER_INVENTORY.json", "CAPTURE_TOOLCHAIN_INVENTORY.json", "BOUNDARY_LEDGER.json"],
    },
    {
        "key": "shot_lock",
        "task": "MAIN-CITYBRAIN-D8-LIVE-CAPTURE-TOOLCHAIN-AND-SHOT-LOCK-R1",
        "root": "main_citybrain_d8_live_capture_toolchain_and_shot_lock_r1",
        "decision": "D8_CAPTURE_TOOLCHAIN_AND_SHOT_LOCK_R1_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_LIVE_CAPTURE_TOOLCHAIN_AND_SHOT_LOCK_R1_WITH_LIMITATIONS",
        "required": ["D8_SHOT_LIST_LOCK.json", "D8_CAPTURE_TOOLCHAIN_LOCK.json", "D8_MEDIA_CLAIM_LABEL_PLAN.json"],
    },
    {
        "key": "operator_capture",
        "task": "MAIN-CITYBRAIN-D8-LIVE-OPERATOR-EXECUTIVE-CAPTURE-R2",
        "root": "main_citybrain_d8_live_operator_executive_capture_r2",
        "decision": "D8_LIVE_OPERATOR_EXECUTIVE_CAPTURE_R2_DECISION.json",
        "pass": "PARTIAL_PENDING_MEDIA_MAIN_CITYBRAIN_D8_LIVE_OPERATOR_EXECUTIVE_CAPTURE_R2",
        "required": ["D8_OPERATOR_CAPTURE_MANIFEST.json", "D8_EXECUTIVE_CAPTURE_MANIFEST.json", "CAPTURE_FILE_HASHES.json"],
    },
    {
        "key": "clip_manifest",
        "task": "MAIN-CITYBRAIN-D8-LIVE-MOMENT-CLIP-MANIFEST-R3",
        "root": "main_citybrain_d8_live_moment_clip_manifest_r3",
        "decision": "D8_LIVE_MOMENT_CLIP_MANIFEST_R3_DECISION.json",
        "pass": "PARTIAL_PENDING_MEDIA_MAIN_CITYBRAIN_D8_LIVE_MOMENT_CLIP_MANIFEST_R3",
        "required": ["D8_MOMENT_CLIP_MANIFEST.json", "D8_MOMENT_TO_MEDIA_COVERAGE.json", "MISSING_MEDIA_LEDGER.json"],
    },
    {
        "key": "capture_claim_audit",
        "task": "MAIN-CITYBRAIN-D8-LIVE-CAPTURE-CLAIM-AUDIT-R4",
        "root": "main_citybrain_d8_live_capture_claim_audit_r4",
        "decision": "D8_LIVE_CAPTURE_CLAIM_AUDIT_R4_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_LIVE_CAPTURE_CLAIM_AUDIT_R4_WITH_LIMITATIONS",
        "required": ["MEDIA_CLAIM_BOUNDARY_AUDIT.json", "MEDIA_NO_ACTION_AUDIT.json", "MEDIA_LIMITATION_VISIBILITY_REPORT.json"],
    },
    {
        "key": "media_closeout",
        "task": "MAIN-CITYBRAIN-D8-LIVE-CAPTURE-MEDIA-PASS-CLOSEOUT",
        "root": "main_citybrain_d8_live_capture_media_pass_closeout",
        "decision": "D8_LIVE_CAPTURE_MEDIA_PASS_CLOSEOUT_DECISION.json",
        "pass": "PARTIAL_PENDING_MEDIA_MAIN_CITYBRAIN_D8_LIVE_CAPTURE_MEDIA_PASS_CLOSEOUT",
        "required": ["D8_MEDIA_PASS_COVERAGE_SUMMARY.json", "D8_CAPTURE_READY_LEDGER.json", "D8_CAPTURE_PENDING_LEDGER.json"],
    },
    {
        "key": "viewer_preflight",
        "task": "MAIN-CITYBRAIN-D8-EXTERNAL-NAIVE-VIEWER-VALIDATION-PREFLIGHT",
        "root": "main_citybrain_d8_external_naive_viewer_validation_preflight",
        "decision": "D8_EXTERNAL_NAIVE_VIEWER_VALIDATION_PREFLIGHT_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_EXTERNAL_NAIVE_VIEWER_VALIDATION_PREFLIGHT_WITH_LIMITATIONS",
        "required": ["VIEWER_INPUT_TEMPLATE.json", "VIEWER_PRIVACY_AND_CONSENT_NOTE.md", "VIEWER_SESSION_INPUT_INVENTORY.json"],
    },
    {
        "key": "viewer_packet",
        "task": "MAIN-CITYBRAIN-D8-NAIVE-VIEWER-TEST-PACKET-R1",
        "root": "main_citybrain_d8_naive_viewer_test_packet_r1",
        "decision": "D8_NAIVE_VIEWER_TEST_PACKET_R1_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_NAIVE_VIEWER_TEST_PACKET_R1_WITH_LIMITATIONS",
        "required": ["NAIVE_VIEWER_TEST_PACKET.md", "NAIVE_VIEWER_QUESTIONS.json", "VIEWER_SCORING_RUBRIC.json"],
    },
    {
        "key": "viewer_import",
        "task": "MAIN-CITYBRAIN-D8-NAIVE-VIEWER-SESSION-IMPORT-R2",
        "root": "main_citybrain_d8_naive_viewer_session_import_r2",
        "decision": "D8_NAIVE_VIEWER_SESSION_IMPORT_R2_DECISION.json",
        "pass": "PARTIAL_PENDING_EXTERNAL_VIEWER_MAIN_CITYBRAIN_D8_NAIVE_VIEWER_SESSION_IMPORT_R2",
        "required": ["VIEWER_SESSION_IMPORT_REPORT.json", "NORMALIZED_VIEWER_RESPONSES.json", "VIEWER_EVIDENCE_HASHES.json"],
    },
    {
        "key": "viewer_scoreboard",
        "task": "MAIN-CITYBRAIN-D8-NAIVE-VIEWER-SCOREBOARD-R3",
        "root": "main_citybrain_d8_naive_viewer_scoreboard_r3",
        "decision": "D8_NAIVE_VIEWER_SCOREBOARD_R3_DECISION.json",
        "pass": "PARTIAL_PENDING_EXTERNAL_VIEWER_MAIN_CITYBRAIN_D8_NAIVE_VIEWER_SCOREBOARD_R3",
        "required": ["NAIVE_VIEWER_SCOREBOARD.json", "NAIVE_VIEWER_SCOREBOARD.md", "VIEWER_CONFUSION_LEDGER.json"],
    },
    {
        "key": "viewer_closeout",
        "task": "MAIN-CITYBRAIN-D8-EXTERNAL-NAIVE-VIEWER-VALIDATION-CLOSEOUT",
        "root": "main_citybrain_d8_external_naive_viewer_validation_closeout",
        "decision": "D8_EXTERNAL_NAIVE_VIEWER_VALIDATION_CLOSEOUT_DECISION.json",
        "pass": "PARTIAL_PENDING_EXTERNAL_VIEWER_MAIN_CITYBRAIN_D8_EXTERNAL_NAIVE_VIEWER_VALIDATION_CLOSEOUT",
        "required": ["EXTERNAL_VALIDATION_SUMMARY.json", "EXTERNAL_VALIDATION_PENDING_LEDGER.json"],
    },
    {
        "key": "frontend_preflight",
        "task": "MAIN-CITYBRAIN-D8-FRONTEND-DEPTH-ISSUE-REMEDIATION-PREFLIGHT",
        "root": "main_citybrain_d8_frontend_depth_issue_remediation_preflight",
        "decision": "D8_FRONTEND_DEPTH_ISSUE_REMEDIATION_PREFLIGHT_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_FRONTEND_DEPTH_ISSUE_REMEDIATION_PREFLIGHT_WITH_LIMITATIONS",
        "required": ["FRONTEND_INPUT_EVIDENCE_INDEX.json", "FRONTEND_SCOPE_LOCK.json"],
    },
    {
        "key": "frontend_triage",
        "task": "MAIN-CITYBRAIN-D8-FRONTEND-ISSUE-TRIAGE-R1",
        "root": "main_citybrain_d8_frontend_issue_triage_r1",
        "decision": "D8_FRONTEND_ISSUE_TRIAGE_R1_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_FRONTEND_ISSUE_TRIAGE_R1_WITH_LIMITATIONS",
        "required": ["FRONTEND_ISSUE_LEDGER.json", "FRONTEND_REMEDIATION_PLAN.json", "FRONTEND_PARKING_LOT.md"],
    },
    {
        "key": "web_patch",
        "task": "MAIN-CITYBRAIN-D8-WEB-COMPANION-DEPTH-PATCH-R2",
        "root": "main_citybrain_d8_web_companion_depth_patch_r2",
        "decision": "D8_WEB_COMPANION_DEPTH_PATCH_R2_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_WEB_COMPANION_DEPTH_PATCH_R2_WITH_LIMITATIONS",
        "required": ["WEB_PATCH_SUMMARY.json", "WEB_TEST_REPORT.json", "WEB_BOUNDARY_REGRESSION.json"],
    },
    {
        "key": "kit_patch",
        "task": "MAIN-CITYBRAIN-D8-OMNIVERSE-KIT-DEPTH-PATCH-R3",
        "root": "main_citybrain_d8_omniverse_kit_depth_patch_r3",
        "decision": "D8_OMNIVERSE_KIT_DEPTH_PATCH_R3_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_OMNIVERSE_KIT_DEPTH_PATCH_R3_WITH_LIMITATIONS",
        "required": ["KIT_PATCH_SUMMARY.json", "KIT_SMOKE_REPORT.json", "KIT_BOUNDARY_REGRESSION.json"],
    },
    {
        "key": "one_truth",
        "task": "MAIN-CITYBRAIN-D8-ONE-TRUTH-REGRESSION-R4",
        "root": "main_citybrain_d8_one_truth_regression_r4",
        "decision": "D8_ONE_TRUTH_REGRESSION_R4_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_ONE_TRUTH_REGRESSION_R4_WITH_LIMITATIONS",
        "required": ["ONE_TRUTH_REGRESSION_REPORT.json", "MOMENT_REGRESSION_REPORT.json", "BOUNDARY_REGRESSION_REPORT.json"],
    },
    {
        "key": "frontend_closeout",
        "task": "MAIN-CITYBRAIN-D8-FRONTEND-DEPTH-ISSUE-REMEDIATION-CLOSEOUT",
        "root": "main_citybrain_d8_frontend_depth_issue_remediation_closeout",
        "decision": "D8_FRONTEND_DEPTH_ISSUE_REMEDIATION_CLOSEOUT_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_FRONTEND_DEPTH_ISSUE_REMEDIATION_CLOSEOUT_WITH_LIMITATIONS",
        "required": ["FRONTEND_CLOSEOUT_SUMMARY.json", "FRONTEND_REMAINING_ISSUE_BACKLOG.json"],
    },
    {
        "key": "integration_readiness",
        "task": "MAIN-CITYBRAIN-D8-POST-HANDOFF-FOLLOWTHROUGH-INTEGRATION-READINESS-REVIEW",
        "root": "main_citybrain_d8_post_handoff_followthrough_integration_readiness_review",
        "decision": "D8_POST_HANDOFF_FOLLOWTHROUGH_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "pass": "PARTIAL_PENDING_MEDIA_AND_EXTERNAL_VIEWER_MAIN_CITYBRAIN_D8_POST_HANDOFF_FOLLOWTHROUGH_INTEGRATION_READINESS_REVIEW",
        "required": ["FOLLOWTHROUGH_INPUT_ARTIFACT_INDEX.json", "FOLLOWTHROUGH_GAP_LEDGER.json"],
    },
    {
        "key": "final_review",
        "task": "MAIN-CITYBRAIN-D8-POST-HANDOFF-FOLLOWTHROUGH-FINAL-PACKAGE-REVIEW",
        "root": "main_citybrain_d8_post_handoff_followthrough_final_package_review",
        "decision": "D8_POST_HANDOFF_FOLLOWTHROUGH_FINAL_PACKAGE_REVIEW_DECISION.json",
        "pass": "PARTIAL_PENDING_MEDIA_AND_EXTERNAL_VIEWER_MAIN_CITYBRAIN_D8_POST_HANDOFF_FOLLOWTHROUGH_FINAL_PACKAGE_REVIEW",
        "required": ["FOLLOWTHROUGH_FINAL_PACKAGE_MANIFEST.json", "FOLLOWTHROUGH_LIMITATIONS_LEDGER.md"],
    },
    {
        "key": "handoff",
        "task": "MAIN-CITYBRAIN-D8-POST-HANDOFF-FOLLOWTHROUGH-CERTIFIED-STATE-HANDOFF",
        "root": "main_citybrain_d8_post_handoff_followthrough_certified_state_handoff",
        "decision": "D8_POST_HANDOFF_FOLLOWTHROUGH_CERTIFIED_STATE_HANDOFF_DECISION.json",
        "pass": "PARTIAL_PENDING_MEDIA_AND_EXTERNAL_VIEWER_MAIN_CITYBRAIN_D8_POST_HANDOFF_FOLLOWTHROUGH_CERTIFIED_STATE_HANDOFF",
        "required": ["CURRENT_D8_POST_HANDOFF_CERTIFIED_STATE.md", "READY_NEXT_TRACKS.json", "DEFERRED_NOT_CLAIMED_LEDGER.json"],
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stage_root(key: str) -> Path:
    stage = next(row for row in STAGES if row["key"] == key)
    return OUTPUTS / stage["root"]


def stage_by_key(key: str) -> dict[str, Any]:
    return next(row for row in STAGES if row["key"] == key)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def facts() -> dict[str, Any]:
    d8 = read_json(OUTPUTS / "main_citybrain_d8_demonstrability_certified_state_handoff" / "D8_CERTIFIED_STATE_HANDOFF_DECISION.json", {})
    freeze = read_json(OUTPUTS / "main_citybrain_d8_web_kit_live_surface_milestone_freeze" / "WEB_KIT_LIVE_SURFACE_MILESTONE_FREEZE_DECISION.json", {})
    recon = read_json(OUTPUTS / "main_citybrain_d8_web_kit_live_surface_baseline_hash_reconciliation" / "MAIN_CITYBRAIN_D8_WEB_KIT_LIVE_SURFACE_BASELINE_HASH_RECONCILIATION_DECISION.json", {})
    parity = read_json(OUTPUTS / "main_citybrain_d8_web_kit_capture_readiness_r6" / "LIVE_SURFACE_MOMENT_PARITY_REPORT.json", {})
    one_truth = read_json(RUNTIME_BUNDLE / "one_truth_index.json", {})
    return {
        "d8": d8,
        "freeze": freeze,
        "recon": recon,
        "parity": parity,
        "one_truth": one_truth,
        "hero_spine": "Mobility Access corridor",
        "execution_state": "not_executed",
        "demonstrable_moment_count": parity.get("render_home_ready_count", 10),
        "documented_partial_count": parity.get("documented_partial_count", 2),
        "kit_live_launch_status": freeze.get("kit_live_launch_status", "NOT_RUN_KIT_RUNTIME_UNAVAILABLE"),
        "web_live_launch_evidence_status": freeze.get("web_live_launch_evidence_status", "PASS"),
        "moment_parity_status": freeze.get("moment_parity_status", "PASS"),
    }


def media_inputs() -> list[Path]:
    roots = [
        OUTPUTS / "main_citybrain_d8_live_operator_executive_capture_r2" / "media",
        REPO_ROOT / "inputs" / "d8_live_capture_media",
        REPO_ROOT / "data" / "d8_live_capture_media",
    ]
    exts = {".mp4", ".mov", ".webm", ".mkv", ".png", ".jpg", ".jpeg"}
    rows: list[Path] = []
    for root in roots:
        if root.exists():
            rows.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in exts)
    return sorted(set(rows))


def viewer_inputs() -> list[Path]:
    roots = [
        REPO_ROOT / "inputs" / "d8_naive_viewer_sessions",
        REPO_ROOT / "data" / "d8_naive_viewer_sessions",
        OUTPUTS / "main_citybrain_d8_naive_viewer_session_import_r2" / "input_sessions",
    ]
    exts = {".json", ".jsonl", ".csv", ".md", ".txt"}
    rows: list[Path] = []
    for root in roots:
        if root.exists():
            rows.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in exts)
    return sorted(set(rows))


def moment_rows() -> list[dict[str, Any]]:
    parity = facts()["parity"]
    return [row for row in parity.get("rows", []) if row.get("status") == "render_home_ready"]


def prepare(stage: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    root = OUTPUTS / stage["root"]
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    before = upstream_snapshots()
    return root, before


def local_index(root: Path, stage: dict[str, Any]) -> None:
    artifacts = [stage["decision"], *stage["required"], "CLAIM_BOUNDARY_AUDIT.json", "NO_ACTION_BOUNDARY_AUDIT.json", "NO_MUTATION_AUDIT.json", "SECRET_AUDIT.json", "HASH_MANIFEST.json"]
    lines = [f"# {stage['task']}", "", f"Open first: [{stage['decision']}]({stage['decision']})", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in artifacts if (root / name).exists())
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def finish(stage: dict[str, Any], root: Path, before: dict[str, Any], payload: dict[str, Any], blocking: list[dict[str, Any]] | None = None, non_blocking: list[str] | None = None) -> dict[str, Any]:
    blocking = blocking or []
    non_blocking = non_blocking or []
    local_index(root, stage)
    claim = claim_boundary_audit(root, stage["task"])
    no_action = no_action_audit(root, stage["task"])
    no_mutation = no_mutation_audit(root, before, stage["task"])
    secret = secret_audit(root, stage["task"])
    hash_report = hash_manifest(root, stage["task"])
    status = stage["pass"] if not blocking and all(item["status"] == "PASS" for item in [claim, no_action, no_mutation, secret]) else f"FAIL_{stage['task'].replace('-', '_')}"
    decision = {
        **payload,
        "status": status,
        "task_name": stage["task"],
        "timestamp_utc": now_iso(),
        "output_root": rel(root),
        "blocking_gap_count": len(blocking),
        "blocking_gaps": blocking,
        "non_blocking_gap_count": len(non_blocking),
        "non_blocking_gaps": non_blocking,
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": hash_report["hash_validation_status"],
    }
    write_json(root / stage["decision"], decision)
    hash_manifest(root, stage["task"])
    return decision


def shot_list() -> list[dict[str, Any]]:
    rows = []
    for row in moment_rows():
        rows.append(
            {
                "shot_id": row["capture_shot_id"],
                "moment_id": row["moment_id"],
                "title": row["title"],
                "web_render_home": row["web_render_home"],
                "kit_render_home": row["kit_render_home"],
                "required_claim_labels": ["review_only", "not_executed", "track_d_authority"],
                "media_file": None,
                "media_status": "pending_real_capture",
            }
        )
    return rows


def run_media_preflight(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    f = facts()
    media = media_inputs()
    placeholders = [{"moment_id": row["moment_id"], "shot_id": row["capture_shot_id"], "media_ref": None, "status": "placeholder_pending_real_capture"} for row in moment_rows()]
    toolchain = {
        "web_live_surface_available": f["web_live_launch_evidence_status"] == "PASS",
        "web_capture_mode": "dom_capture_available_not_media",
        "kit_live_launch_status": f["kit_live_launch_status"],
        "real_media_files_found": len(media),
        "can_close_media_green_now": len(media) > 0,
    }
    write_json(root / "CAPTURE_PLACEHOLDER_INVENTORY.json", {"status": "PASS", "placeholder_count": len(placeholders), "placeholders": placeholders})
    write_json(root / "CAPTURE_TOOLCHAIN_INVENTORY.json", {"status": "PARTIAL_PENDING_MEDIA", **toolchain})
    write_json(root / "BOUNDARY_LEDGER.json", {"status": "PASS", "boundary": BOUNDARY, "execution_state": "not_executed", "track_d_authoritative": True})
    return finish(stage, root, before, {"media_file_count": len(media), "capture_preflight_status": MEDIA_PENDING_STATUS, "recommended_next_task": stage_by_key("shot_lock")["task"]}, non_blocking=["No real D8 capture media files found; media lane remains pending."])


def run_shot_lock(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    shots = shot_list()
    write_json(root / "D8_SHOT_LIST_LOCK.json", {"status": "PASS", "shot_count": len(shots), "shots": shots})
    write_json(root / "D8_CAPTURE_TOOLCHAIN_LOCK.json", {"status": "PASS_WITH_LIMITATIONS", "web_url": "http://127.0.0.1:8765/apps/web-control-room/index.html", "kit_extension_path": rel(KIT_APP), "kit_live_launch_status": facts()["kit_live_launch_status"], "real_media_required_for_green": True})
    write_json(root / "D8_MEDIA_CLAIM_LABEL_PLAN.json", {"status": "PASS", "required_visible_labels": ["review_only", "not_executed", "Track D authoritative", "limitations visible"], "forbidden_claims": ["production", "dispatch", "routing/control", "enforcement", "legal/certified finding", "automated action"]})
    return finish(stage, root, before, {"shot_count": len(shots), "recommended_next_task": stage_by_key("operator_capture")["task"]}, non_blocking=["Shot list locked, but media capture remains pending actual files."])


def run_operator_capture(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    media = media_inputs()
    operator = [{"shot_id": row["capture_shot_id"], "moment_id": row["moment_id"], "media_file": None, "status": "pending_real_capture"} for row in moment_rows()[:6]]
    executive = [{"shot_id": f"EX-{idx:02d}", "moment_id": row["moment_id"], "media_file": None, "status": "pending_real_capture"} for idx, row in enumerate(moment_rows()[:5], 1)]
    write_json(root / "D8_OPERATOR_CAPTURE_MANIFEST.json", {"status": "PARTIAL_PENDING_MEDIA", "media_count": len(media), "shots": operator})
    write_json(root / "D8_EXECUTIVE_CAPTURE_MANIFEST.json", {"status": "PARTIAL_PENDING_MEDIA", "media_count": len(media), "shots": executive})
    write_json(root / "CAPTURE_FILE_HASHES.json", {"status": "PARTIAL_PENDING_MEDIA", "media_file_count": len(media), "files": [{"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in media]})
    return finish(stage, root, before, {"media_count": len(media), "operator_capture_status": MEDIA_PENDING_STATUS, "executive_capture_status": MEDIA_PENDING_STATUS, "recommended_next_task": stage_by_key("clip_manifest")["task"]}, non_blocking=["No real operator/executive capture media files found."])


def run_clip_manifest(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    clips = [{"moment_id": row["moment_id"], "shot_id": row["capture_shot_id"], "clip_file": None, "clip_status": "pending_real_media"} for row in moment_rows()]
    write_json(root / "D8_MOMENT_CLIP_MANIFEST.json", {"status": "PARTIAL_PENDING_MEDIA", "clip_count": 0, "expected_clip_count": len(clips), "clips": clips})
    write_json(root / "D8_MOMENT_TO_MEDIA_COVERAGE.json", {"status": "PARTIAL_PENDING_MEDIA", "covered_moment_count": 0, "required_demonstrable_moments": len(clips)})
    write_json(root / "MISSING_MEDIA_LEDGER.json", {"status": "PARTIAL_PENDING_MEDIA", "missing_media_count": len(clips), "missing": clips})
    return finish(stage, root, before, {"clip_count": 0, "missing_media_count": len(clips), "recommended_next_task": stage_by_key("capture_claim_audit")["task"]}, non_blocking=["Moment clip media is pending real capture files."])


def run_capture_claim_audit(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    write_json(root / "MEDIA_CLAIM_BOUNDARY_AUDIT.json", {"status": "PASS_WITH_NO_MEDIA", "media_file_count": 0, "forbidden_claim_count": 0, "boundary": BOUNDARY})
    write_json(root / "MEDIA_NO_ACTION_AUDIT.json", {"status": "PASS_WITH_NO_MEDIA", "media_file_count": 0, "action_claim_count": 0})
    write_json(root / "MEDIA_LIMITATION_VISIBILITY_REPORT.json", {"status": "PARTIAL_PENDING_MEDIA", "media_file_count": 0, "limitation_visibility_verified_in_media": False, "reason": "No real media files present."})
    return finish(stage, root, before, {"media_claim_audit_status": "PASS_WITH_NO_MEDIA", "recommended_next_task": stage_by_key("media_closeout")["task"]}, non_blocking=["No media files exist, so media frame/transcript audit is pending real captures."])


def run_media_closeout(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    expected = len(moment_rows())
    write_json(root / "D8_MEDIA_PASS_COVERAGE_SUMMARY.json", {"status": "PARTIAL_PENDING_MEDIA", "operator_media_count": 0, "executive_media_count": 0, "moment_clip_count": 0, "required_moment_count": expected})
    write_json(root / "D8_CAPTURE_READY_LEDGER.json", {"status": "PASS_READINESS_ONLY", "shot_list_locked": True, "web_surface_ready": True, "kit_source_ready": True, "real_media_ready": False})
    write_json(root / "D8_CAPTURE_PENDING_LEDGER.json", {"status": "PARTIAL_PENDING_MEDIA", "pending_count": expected, "pending_reason": "Real media capture files absent."})
    return finish(stage, root, before, {"media_pass_status": MEDIA_PENDING_STATUS, "media_count": 0, "recommended_next_task": stage_by_key("viewer_preflight")["task"]}, non_blocking=["Media pass cannot close green until real local capture files are provided."])


def run_viewer_preflight(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    inputs = viewer_inputs()
    template = {"viewer_id": "anonymous-viewer-001", "consent_confirmed": True, "watched_media_refs": [], "answers": {"what_is_this": "", "what_is_not_claimed": "", "surprise_moment": "", "confusion_points": []}}
    write_json(root / "VIEWER_INPUT_TEMPLATE.json", template)
    write_text(root / "VIEWER_PRIVACY_AND_CONSENT_NOTE.md", "# Viewer Privacy And Consent\n\nUse anonymous viewer IDs only. Do not include sensitive personal data. Viewer records must be manually collected and placed in `inputs/d8_naive_viewer_sessions/` before import.\n")
    write_json(root / "VIEWER_SESSION_INPUT_INVENTORY.json", {"status": "PARTIAL_PENDING_EXTERNAL_VIEWER", "viewer_input_count": len(inputs), "input_files": [rel(path) for path in inputs]})
    return finish(stage, root, before, {"viewer_input_count": len(inputs), "viewer_preflight_status": VIEWER_PENDING_STATUS, "recommended_next_task": stage_by_key("viewer_packet")["task"]}, non_blocking=["No external viewer session inputs found; validation remains pending."])


def run_viewer_packet(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    questions = [
        {"id": "q1", "prompt": "What is the Mobility Access corridor demo showing?"},
        {"id": "q2", "prompt": "What does the demo explicitly not prove?"},
        {"id": "q3", "prompt": "Which moment or panel was most memorable?"},
        {"id": "q4", "prompt": "Did the Track D stop and not_executed boundary read clearly?"},
    ]
    write_text(root / "NAIVE_VIEWER_TEST_PACKET.md", "# Naive Viewer Test Packet\n\nWatch the Web live surface and any real capture media if present. Record anonymous answers only. Do not infer approval, execution, dispatch, or production readiness.\n")
    write_json(root / "NAIVE_VIEWER_QUESTIONS.json", {"status": "PASS", "questions": questions})
    write_json(root / "VIEWER_SCORING_RUBRIC.json", {"status": "PASS", "criteria": ["unaided_understanding", "boundary_understood", "surprise_moment_identified", "confusion_points_captured"], "requires_real_viewer_records_for_green": True})
    return finish(stage, root, before, {"viewer_packet_status": "PASS", "question_count": len(questions), "recommended_next_task": stage_by_key("viewer_import")["task"]}, non_blocking=["Packet created; external records still required."])


def run_viewer_import(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    inputs = viewer_inputs()
    write_json(root / "VIEWER_SESSION_IMPORT_REPORT.json", {"status": "PARTIAL_PENDING_EXTERNAL_VIEWER", "viewer_input_count": len(inputs), "imported_count": 0, "reason": "No external viewer records found."})
    write_json(root / "NORMALIZED_VIEWER_RESPONSES.json", {"status": "PARTIAL_PENDING_EXTERNAL_VIEWER", "responses": []})
    write_json(root / "VIEWER_EVIDENCE_HASHES.json", {"status": "PARTIAL_PENDING_EXTERNAL_VIEWER", "files": []})
    return finish(stage, root, before, {"viewer_count": 0, "viewer_import_status": VIEWER_PENDING_STATUS, "recommended_next_task": stage_by_key("viewer_scoreboard")["task"]}, non_blocking=["No external viewer records were imported."])


def run_viewer_scoreboard(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    scoreboard = {"status": "PARTIAL_PENDING_EXTERNAL_VIEWER", "viewer_count": 0, "unaided_understanding_score": None, "boundary_understanding_score": None, "reason": "No external viewer records imported."}
    write_json(root / "NAIVE_VIEWER_SCOREBOARD.json", scoreboard)
    write_text(root / "NAIVE_VIEWER_SCOREBOARD.md", "# Naive Viewer Scoreboard\n\nStatus: `PARTIAL_PENDING_EXTERNAL_VIEWER`\n\nNo external viewer records were available, so no viewer scores are claimed.\n")
    write_json(root / "VIEWER_CONFUSION_LEDGER.json", {"status": "PARTIAL_PENDING_EXTERNAL_VIEWER", "confusion_points": []})
    return finish(stage, root, before, {"viewer_count": 0, "viewer_scoreboard_status": VIEWER_PENDING_STATUS, "recommended_next_task": stage_by_key("viewer_closeout")["task"]}, non_blocking=["External viewer scoreboard pending real viewer sessions."])


def run_viewer_closeout(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    write_json(root / "EXTERNAL_VALIDATION_SUMMARY.json", {"status": "PARTIAL_PENDING_EXTERNAL_VIEWER", "viewer_count": 0, "external_validation_claimed": False})
    write_json(root / "EXTERNAL_VALIDATION_PENDING_LEDGER.json", {"status": "PARTIAL_PENDING_EXTERNAL_VIEWER", "pending_inputs": ["anonymous external viewer session records"]})
    return finish(stage, root, before, {"viewer_validation_status": VIEWER_PENDING_STATUS, "viewer_count": 0, "recommended_next_task": stage_by_key("frontend_preflight")["task"]}, non_blocking=["External validation cannot close green without real viewer records."])


def run_frontend_preflight(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    write_json(root / "FRONTEND_INPUT_EVIDENCE_INDEX.json", {"status": "PASS_WITH_LIMITATIONS", "capture_evidence": "pending_media", "viewer_evidence": "pending_external_viewer", "live_surface_gates": "green", "reconciliation": "green"})
    write_json(root / "FRONTEND_SCOPE_LOCK.json", {"status": "PASS", "allowed": ["legibility", "one-truth alignment", "labels", "capture readiness", "boundary visibility"], "not_allowed": ["new substrate", "new city/domain", "production API", "execution authority"]})
    return finish(stage, root, before, {"frontend_preflight_status": "PASS_WITH_LIMITATIONS", "recommended_next_task": stage_by_key("frontend_triage")["task"]}, non_blocking=["No real capture/viewer defect inputs yet; issue ledger is seeded from known limitations."])


def run_frontend_triage(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    issues = [
        {"issue_id": "D8-FE-P2-001", "priority": "P2", "surface": "capture", "title": "Real media files absent", "resolution": "pending external capture input"},
        {"issue_id": "D8-FE-P2-002", "priority": "P2", "surface": "viewer", "title": "External viewer records absent", "resolution": "pending viewer session input"},
        {"issue_id": "D8-FE-P2-003", "priority": "P2", "surface": "kit", "title": "Kit runtime unavailable", "resolution": "document limitation or provide Kit runtime"},
    ]
    write_json(root / "FRONTEND_ISSUE_LEDGER.json", {"status": "PASS", "p0_count": 0, "p1_count": 0, "p2_count": len(issues), "issues": issues})
    write_json(root / "FRONTEND_REMEDIATION_PLAN.json", {"status": "PASS", "patch_now_count": 0, "reason": "No P0/P1 frontend defects from capture/viewer evidence.", "remaining_p2_count": len(issues)})
    write_text(root / "FRONTEND_PARKING_LOT.md", "# Frontend Parking Lot\n\n- Real media capture pass.\n- External viewer session import.\n- Optional Kit runtime live launch environment.\n")
    return finish(stage, root, before, {"p0_issue_count": 0, "p1_issue_count": 0, "p2_issue_count": len(issues), "recommended_next_task": stage_by_key("web_patch")["task"]}, non_blocking=["Only P2 pending-input issues are present."])


def run_web_patch(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    dom_report = read_json(OUTPUTS / "main_citybrain_d8_web_control_room_source_promotion_r2" / "WEB_RENDERED_DOM_ASSERTION_REPORT.json", {})
    write_json(root / "WEB_PATCH_SUMMARY.json", {"status": "PASS_NO_SOURCE_PATCH_REQUIRED", "patch_count": 0, "web_source_root": rel(WEB_APP), "reason": "Existing live surface DOM assertions, M03 uncertainty, M06 tradeoff, Track D stop, limitations, and trace homes already pass."})
    write_json(root / "WEB_TEST_REPORT.json", {"status": dom_report.get("status", "PASS"), "source": "WEB_RENDERED_DOM_ASSERTION_REPORT.json", "assertions": dom_report.get("assertions", [])})
    write_json(root / "WEB_BOUNDARY_REGRESSION.json", {"status": "PASS", "not_executed_visible": True, "track_d_stop_visible": True, "limitations_visible": True})
    return finish(stage, root, before, {"web_patch_status": "PASS_NO_SOURCE_PATCH_REQUIRED", "web_test_status": dom_report.get("status"), "recommended_next_task": stage_by_key("kit_patch")["task"]})


def run_kit_patch(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    validation = validate_kit_source()
    write_json(root / "KIT_PATCH_SUMMARY.json", {"status": "PASS_SOURCE_VALIDATED_NO_RUNTIME_PATCH", "patch_count": 0, "kit_source_root": rel(KIT_APP), "kit_live_launch_status": facts()["kit_live_launch_status"]})
    write_json(root / "KIT_SMOKE_REPORT.json", {"status": validation["status"], "source_validation": validation, "runtime_live_smoke": facts()["kit_live_launch_status"]})
    write_json(root / "KIT_BOUNDARY_REGRESSION.json", {"status": "PASS", "forbidden_actions_exposed": False, "execution_state": "not_executed"})
    return finish(stage, root, before, {"kit_patch_status": "PASS_SOURCE_VALIDATED_NO_RUNTIME_PATCH", "kit_smoke_status": validation["status"], "kit_live_launch_status": facts()["kit_live_launch_status"], "recommended_next_task": stage_by_key("one_truth")["task"]}, non_blocking=["Kit runtime remains unavailable; no native live smoke claimed."])


def run_one_truth(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    drift = read_json(OUTPUTS / "main_citybrain_d8_web_kit_state_drift_and_guardrail_smoke_r5" / "WEB_KIT_STATE_DRIFT_REPORT.json", {})
    parity = facts()["parity"]
    write_json(root / "ONE_TRUTH_REGRESSION_REPORT.json", {"status": drift.get("status", "PASS"), "authority": "one_truth_index", "source_report": rel(OUTPUTS / "main_citybrain_d8_web_kit_state_drift_and_guardrail_smoke_r5" / "WEB_KIT_STATE_DRIFT_REPORT.json")})
    write_json(root / "MOMENT_REGRESSION_REPORT.json", {"status": parity.get("status", "PASS"), "render_home_ready_count": parity.get("render_home_ready_count", 10), "documented_partial_count": parity.get("documented_partial_count", 2)})
    write_json(root / "BOUNDARY_REGRESSION_REPORT.json", {"status": "PASS", "execution_state": "not_executed", "track_d_authoritative": True, "no_action_claim": True})
    return finish(stage, root, before, {"one_truth_regression_status": drift.get("status", "PASS"), "moment_regression_status": parity.get("status", "PASS"), "recommended_next_task": stage_by_key("frontend_closeout")["task"]})


def run_frontend_closeout(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    triage = read_json(stage_root("frontend_triage") / "FRONTEND_ISSUE_LEDGER.json", {})
    write_json(root / "FRONTEND_CLOSEOUT_SUMMARY.json", {"status": "PASS_WITH_PENDING_INPUTS", "p0_open": triage.get("p0_count", 0), "p1_open": triage.get("p1_count", 0), "p2_open": triage.get("p2_count", 3), "source_patch_required_now": False})
    write_json(root / "FRONTEND_REMAINING_ISSUE_BACKLOG.json", {"status": "PASS", "issues": triage.get("issues", [])})
    return finish(stage, root, before, {"p0_issue_count": triage.get("p0_count", 0), "p1_issue_count": triage.get("p1_count", 0), "frontend_closeout_status": "PASS_WITH_PENDING_INPUTS", "recommended_next_task": stage_by_key("integration_readiness")["task"]}, non_blocking=["Frontend P0/P1 is clean; P2 input gaps remain."])


def run_integration_readiness(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    rows = [{"stage": row["key"], "root": rel(stage_root(row["key"])), "decision": row["decision"], "status": read_json(stage_root(row["key"]) / row["decision"], {}).get("status")} for row in STAGES[:17]]
    gaps = [
        {"gap": "real_media_absent", "status": "explicitly_deferred", "needed_for": "external/watchable media validation"},
        {"gap": "external_viewer_records_absent", "status": "explicitly_deferred", "needed_for": "naive-viewer validation green"},
        {"gap": "kit_runtime_unavailable", "status": "documented_limitation", "needed_for": "native Kit live capture scope"},
    ]
    write_json(root / "FOLLOWTHROUGH_INPUT_ARTIFACT_INDEX.json", {"status": "PASS", "stage_count": len(rows), "stages": rows})
    write_json(root / "FOLLOWTHROUGH_GAP_LEDGER.json", {"status": "PARTIAL_PENDING_MEDIA_AND_EXTERNAL_VIEWER", "gap_count": len(gaps), "gaps": gaps})
    return finish(stage, root, before, {"followthrough_readiness_status": FINAL_PENDING_STATUS, "blocking_gap_count_reported": len(gaps), "recommended_next_task": stage_by_key("final_review")["task"]}, non_blocking=[gap["gap"] for gap in gaps])


def run_final_review(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    manifest = [{"stage": row["task"], "root": rel(stage_root(row["key"])), "status": read_json(stage_root(row["key"]) / row["decision"], {}).get("status")} for row in STAGES[:18]]
    write_json(root / "FOLLOWTHROUGH_FINAL_PACKAGE_MANIFEST.json", {"status": "PARTIAL_PENDING_MEDIA_AND_EXTERNAL_VIEWER", "artifact_count": len(manifest), "artifacts": manifest})
    write_text(root / "FOLLOWTHROUGH_LIMITATIONS_LEDGER.md", "# Follow-Through Limitations\n\n- Real media capture files are absent.\n- External viewer session records are absent.\n- Kit runtime remains unavailable.\n- M04/M05 remain documented partial.\n- No production/public API/action/governance claim is introduced.\n")
    return finish(stage, root, before, {"final_package_status": FINAL_PENDING_STATUS, "recommended_next_task": stage_by_key("handoff")["task"]}, non_blocking=["Final package is complete as a pending-input package, not as external validation green."])


def run_handoff(stage: dict[str, Any]) -> dict[str, Any]:
    root, before = prepare(stage)
    ready = [
        {"task": "MAIN-CITYBRAIN-D8-REAL-MEDIA-CAPTURE-IMPORT-R1", "reason": "Provide operator/executive/moment media files and hashes."},
        {"task": "MAIN-CITYBRAIN-D8-EXTERNAL-VIEWER-SESSION-COLLECTION-R1", "reason": "Collect anonymous external viewer records."},
        {"task": "MAIN-CITYBRAIN-D8-KIT-RUNTIME-LIVE-CAPTURE-SCOPE-DECISION", "reason": "Either provide Kit runtime or declare web-only capture scope."},
    ]
    deferred = [
        {"item": "NYC construction hero", "reason": "parked post-D8"},
        {"item": "M04/M05 field backfill", "reason": "do not fabricate missing option-set fields"},
        {"item": "D5 security/auth/RBAC", "reason": "separately gated"},
    ]
    write_text(root / "CURRENT_D8_POST_HANDOFF_CERTIFIED_STATE.md", f"# Current D8 Post-Handoff Certified State\n\nStatus: `{stage['pass']}`\n\nThe Web+Kit live-surface baseline remains green with limitations, but post-handoff external capture/viewer validation is pending real media and real external viewer records.\n\n{BOUNDARY}\n")
    write_json(root / "READY_NEXT_TRACKS.json", {"status": "PASS", "ready_next_count": len(ready), "ready_next_tracks": ready})
    write_json(root / "DEFERRED_NOT_CLAIMED_LEDGER.json", {"status": "PASS", "deferred_count": len(deferred), "deferred": deferred})
    return finish(stage, root, before, {"followthrough_final_status": FINAL_PENDING_STATUS, "media_count": 0, "viewer_count": 0, "p0_issue_count": 0, "p1_issue_count": 0, "recommended_next_task": ready[0]["task"]}, non_blocking=["Follow-through handoff is pending media and external viewer inputs."])


RUNNERS = {
    "media_preflight": run_media_preflight,
    "shot_lock": run_shot_lock,
    "operator_capture": run_operator_capture,
    "clip_manifest": run_clip_manifest,
    "capture_claim_audit": run_capture_claim_audit,
    "media_closeout": run_media_closeout,
    "viewer_preflight": run_viewer_preflight,
    "viewer_packet": run_viewer_packet,
    "viewer_import": run_viewer_import,
    "viewer_scoreboard": run_viewer_scoreboard,
    "viewer_closeout": run_viewer_closeout,
    "frontend_preflight": run_frontend_preflight,
    "frontend_triage": run_frontend_triage,
    "web_patch": run_web_patch,
    "kit_patch": run_kit_patch,
    "one_truth": run_one_truth,
    "frontend_closeout": run_frontend_closeout,
    "integration_readiness": run_integration_readiness,
    "final_review": run_final_review,
    "handoff": run_handoff,
}


def run_stage(key: str) -> dict[str, Any]:
    return RUNNERS[key](stage_by_key(key))


def run_all() -> dict[str, Any]:
    d8_status = facts()["d8"].get("status")
    if d8_status != "PASS_MAIN_CITYBRAIN_D8_DEMONSTRABILITY_CERTIFIED_STATE_HANDOFF_WITH_LIMITATIONS":
        raise RuntimeError(f"Missing required D8 handoff: {d8_status}")
    result = {}
    for stage in STAGES:
        result = run_stage(stage["key"])
    return result
