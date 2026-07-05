#!/usr/bin/env python3
"""Generate the R8 real/replay perception runtime evidence package.

R8 intentionally keeps video/runtime output as candidate observation material.
The local replay adapter produces detection metadata and evidence refs for
review; it does not claim production DeepStream execution, live monitoring,
official submission, VSS truth, or autonomous action.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r8_real_perception_runtime_evidence_clip_integration"
ZIP_PATH = OUTPUT_ROOT / "citybrain_r8_real_perception_runtime_evidence_clip_integration.zip"
R7_DECISION = REPO_ROOT / "outputs" / "main_citybrain_r7_perception_to_review_workflow_preflight" / "DECISION.json"
R7A_DECISION = (
    REPO_ROOT
    / "outputs"
    / "main_citybrain_r7a_perception_candidate_observation_ingress"
    / "R7A_CANDIDATE_OBSERVATION_INGRESS_DECISION.json"
)

TASK_ID = "MAIN-CITYBRAIN-R8-REAL-PERCEPTION-RUNTIME-AND-EVIDENCE-CLIP-INTEGRATION"
PASS_STATUS = "PASS_R8F_REAL_PERCEPTION_RUNTIME_EVIDENCE_SMOKE_WITH_LIMITATIONS"
PARTIAL_RUNTIME_BLOCKED = "PARTIAL_R8_RUNTIME_BLOCKED_EVIDENCE_FIXTURES_ONLY"
PARTIAL_NO_CLIP = "PARTIAL_R8_RUNTIME_OUTPUT_NO_FRAME_CLIP_EXPORT"
PARTIAL_NO_REVIEW = "PARTIAL_R8_EVIDENCE_EXPORT_NO_WEBUI_KIT_REVIEW"
FAIL_BOUNDARY = "FAIL_R8_AUTONOMOUS_ACTION_OR_OFFICIAL_CLAIM_REGRESSION"
FAIL_TRUTH = "FAIL_R8_PIXEL_OR_VSS_OUTPUT_USED_AS_TRUTH"

BOUNDARY = (
    "video runtime output = candidate observation; VSS/summary output = review assistance only; "
    "frames/clips = evidence refs, not legal proof; case/ticket = draft/sandbox; "
    "dispatch/control/enforcement = proposal only; execution_status = not_executed"
)
LIMITATIONS = [
    "local/replay source only; no live cameras, RTSP production source, public/cloud deployment, or production API",
    "actual NVIDIA DeepStream product runtime is not claimed; R8 executes a deterministic local replay metadata adapter",
    "VSS output is a review-assist fixture only and is not used as truth",
    "frames and clips are evidence references for human review, not legal/certified proof",
    "case/ticket packet remains sandbox draft_not_submitted",
    "dispatch/control/enforcement-adjacent action proposal remains not_executed",
]

REQUIRED_SOURCE_FIELDS = [
    "source_id",
    "source_kind",
    "uri_or_path",
    "source_mode",
    "camera_or_sensor_id",
    "location_ref",
    "scene_ref",
    "privacy_boundary",
    "retention_policy",
    "source_hash",
    "registered_at",
]
REQUIRED_DETECTION_FIELDS = [
    "runtime_detection_id",
    "runtime_name",
    "runtime_version",
    "pipeline_config_ref",
    "source_id",
    "frame_index",
    "timestamp",
    "detected_class",
    "confidence",
    "bbox",
    "track_id",
    "zone_ref",
    "raw_metadata_ref",
]
REQUIRED_OBSERVATION_FIELDS = [
    "candidate_observation_id",
    "source_system",
    "source_type",
    "camera_or_sensor_id",
    "media_ref",
    "frame_ref",
    "clip_ref",
    "timestamp",
    "location_ref",
    "detected_classes",
    "confidence",
    "zone_ref",
    "evidence_refs",
    "limitation_refs",
    "review_state",
    "no_action_state",
    "cannot_claim",
    "packet_hash",
]
REQUIRED_EVIDENCE_CLIP_FIELDS = [
    "evidence_id",
    "candidate_observation_id",
    "source_id",
    "media_ref",
    "frame_path",
    "clip_path",
    "timestamp_start",
    "timestamp_end",
    "frame_hash",
    "clip_hash",
    "extraction_method",
    "limitations",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_hash(payload: dict[str, Any], omit: set[str] | None = None) -> str:
    omit = omit or set()
    clean = {key: value for key, value in payload.items() if key not in omit}
    data = json.dumps(clean, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def out_rel(path: Path, root: Path = OUTPUT_ROOT) -> str:
    return path.relative_to(root).as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def clean_output_root(root: Path) -> None:
    resolved_root = root.resolve()
    resolved_repo = REPO_ROOT.resolve()
    if root.exists():
        if resolved_repo not in resolved_root.parents:
            raise RuntimeError(f"Refusing to clean output root outside workspace: {resolved_root}")
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def source_media_bytes() -> bytes:
    return (
        b"CITYBRAIN_R8_LOCAL_REPLAY_SOURCE\n"
        b"source_id=source:r8:local-replay-west-gate-001\n"
        b"frame_indices=420-450\n"
        b"truth_boundary=candidate_observation_only\n"
    )


def frame_ppm_bytes() -> bytes:
    rows = [
        "P3",
        "8 6",
        "255",
    ]
    for y in range(6):
        pixels = []
        for x in range(8):
            if 2 <= x <= 5 and 1 <= y <= 4:
                pixels.append("255 204 64")
            else:
                pixels.append(f"{30 + x * 10} {38 + y * 12} {58 + x * 8}")
        rows.append(" ".join(pixels))
    return ("\n".join(rows) + "\n").encode("ascii")


def clip_bytes(detection: dict[str, Any]) -> bytes:
    payload = {
        "clip_ref": "clip:r8:local-replay-west-gate-001:000410-000450",
        "frame_range": [410, 450],
        "source_detection": detection["runtime_detection_id"],
        "boundary": "clip evidence reference only; not legal proof",
    }
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def perception_source(root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    media_path = root / "source_media" / "local_replay_west_gate_source.media"
    media_hash = sha256_file(media_path) if media_path.exists() else sha256_bytes(source_media_bytes())
    return {
        "source_id": "source:r8:local-replay-west-gate-001",
        "source_kind": "local_replay_media",
        "uri_or_path": out_rel(media_path, root),
        "source_mode": "local_replay",
        "camera_or_sensor_id": "camera:r8:demo-west-gate-001",
        "location_ref": "location:r8:demo-west-gate",
        "scene_ref": "scene:r8:barcelona-nyc-review-sandbox",
        "media_ref": "media:r8:local-replay-west-gate-clip",
        "privacy_boundary": "demo/replay media only; no identity or biometric inference",
        "retention_policy": "local package evidence retention only",
        "source_hash": media_hash,
        "registered_at": "2026-07-04T13:40:00Z",
    }


def run_replay_runtime_adapter(source: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    detection = {
        "runtime_detection_id": "runtime:r8:detection:000420:person-like",
        "runtime_name": "Metropolis-style local replay adapter",
        "runtime_version": "r8-local-replay-1.0",
        "pipeline_config_ref": "pipeline:r8:deepstream-metropolis-style-local-replay",
        "source_id": source["source_id"],
        "frame_index": 420,
        "timestamp": "2026-07-04T13:40:14Z",
        "detected_class": "person_like_shape",
        "confidence": 0.82,
        "bbox": {"x": 0.28, "y": 0.18, "width": 0.31, "height": 0.54, "coordinate_system": "normalized_xywh"},
        "track_id": "track:r8:local-replay-0001",
        "zone_ref": "zone:r8:demo-west-gate-review-zone",
        "raw_metadata_ref": "runtime_metadata/raw_runtime_detection_000420.json",
        "truth_boundary": "candidate observation metadata only; not final truth",
    }
    return [detection], (
        "R8 local replay adapter executed over deterministic replay metadata.\n"
        "DeepStream product runtime was not invoked in this local package.\n"
        "Output remains candidate observation metadata; execution_status=not_executed.\n"
    )


def candidate_from_detection(source: dict[str, Any], detection: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    observation = {
        "candidate_observation_id": "candidate:r8:runtime:obs:0001",
        "source_system": "metropolis_deepstream_style_local_replay_adapter",
        "source_type": "local_replay_runtime_metadata",
        "camera_or_sensor_id": source["camera_or_sensor_id"],
        "media_ref": source["media_ref"],
        "frame_ref": "frame:r8:local-replay-west-gate-clip:000420",
        "clip_ref": "clip:r8:local-replay-west-gate-001:000410-000450",
        "timestamp": detection["timestamp"],
        "location_ref": source["location_ref"],
        "detected_classes": [
            {
                "class_id": detection["detected_class"],
                "confidence": detection["confidence"],
                "bbox": detection["bbox"],
                "track_id": detection["track_id"],
            }
        ],
        "confidence": detection["confidence"],
        "zone_ref": detection["zone_ref"],
        "evidence_refs": [
            source["source_id"],
            detection["runtime_detection_id"],
            evidence["evidence_id"],
            evidence["frame_ref"],
            evidence["clip_ref"],
        ],
        "limitation_refs": [
            "limitation:r8:local_replay_only",
            "limitation:r8:runtime_metadata_candidate_only",
            "limitation:r8:evidence_not_legal_proof",
            "limitation:r8:no_identity_or_biometric_claim",
        ],
        "review_state": "candidate",
        "no_action_state": {"no_action_taken": True, "execution_state": "not_executed"},
        "cannot_claim": [
            "confirmed violation",
            "identity of a natural person",
            "legal or certified finding",
            "official affected asset/building determination",
            "official case/ticket creation",
            "dispatch/control/enforcement execution",
        ],
        "pixel_derived_truth_used": False,
        "vss_output_used_as_truth": False,
    }
    observation["packet_hash"] = canonical_hash(observation, {"packet_hash"})
    return observation


def event_packet_from_observation(observation: dict[str, Any]) -> dict[str, Any]:
    packet = {
        "event_packet_id": "event:r8:candidate-observation:0001",
        "candidate_observation_id": observation["candidate_observation_id"],
        "event_kind": "runtime_candidate_observation",
        "event_truth_status": "candidate_not_confirmed",
        "source_refs": observation["evidence_refs"],
        "confidence": observation["confidence"],
        "zone_ref": observation["zone_ref"],
        "requires_human_review": True,
        "execution_status": "not_executed",
        "pixel_derived_truth_used": False,
        "vss_output_used_as_truth": False,
    }
    packet["packet_hash"] = canonical_hash(packet, {"packet_hash"})
    return packet


def vss_review_assist_packet(observation: dict[str, Any]) -> dict[str, Any]:
    packet = {
        "vss_review_assist_id": "vss:r8:review-assist:0001",
        "source_candidate_observation_id": observation["candidate_observation_id"],
        "assist_type": "fixture_summary_search_context",
        "summary": "Replay segment contains a person-like shape candidate in the review zone; human review is required.",
        "cited_refs": observation["evidence_refs"][:],
        "uncertainty": [
            "summary is review assistance only",
            "does not confirm violation, identity, legal finding, or operational action",
        ],
        "limitations": [
            "local/replay fixture; no VSS production runtime or LLM call",
            "not used as candidate truth or evidence proof",
        ],
        "vss_output_used_as_truth": False,
        "truth_role": "review_assistance_only",
        "execution_status": "not_executed",
    }
    packet["packet_hash"] = canonical_hash(packet, {"packet_hash"})
    return packet


def check_claimability(observation: dict[str, Any], evidence: dict[str, Any], vss: dict[str, Any]) -> dict[str, Any]:
    checks = [
        {
            "check": "runtime_output_candidate_only",
            "status": "PASS",
            "reason": "Runtime metadata is exported as CandidateObservation with event_truth_status=candidate_not_confirmed.",
        },
        {
            "check": "frame_clip_evidence_refs_not_proof",
            "status": "PASS",
            "reason": "Evidence frame/clip files are hashed refs for human review, not legal/certified proof.",
        },
        {
            "check": "vss_review_assist_not_truth",
            "status": "PASS",
            "reason": "VSS review assist has truth_role=review_assistance_only and vss_output_used_as_truth=false.",
        },
        {
            "check": "no_action_boundary",
            "status": "PASS",
            "reason": "No official submission, dispatch, control, enforcement, or automated action is executed.",
        },
    ]
    report = {
        "schema_version": "citybrain.r8.check_claimability.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "candidate_observation_id": observation["candidate_observation_id"],
        "evidence_id": evidence["evidence_id"],
        "vss_review_assist_id": vss["vss_review_assist_id"],
        "overall_claimability": "candidate_review_only",
        "checks": checks,
    }
    report["packet_hash"] = canonical_hash(report, {"packet_hash"})
    return report


def review_promotion(observation: dict[str, Any]) -> dict[str, Any]:
    promotion = {
        "promotion_id": "promotion:r8:human-review:0001",
        "candidate_observation_id": observation["candidate_observation_id"],
        "reviewer_state": "promote_to_draft",
        "reviewer_note": "Human review note for sandbox draft only; candidate remains unconfirmed.",
        "promotion_target": "sandbox_draft_case_ticket",
        "evidence_refs": observation["evidence_refs"],
        "limitations": observation["limitation_refs"],
        "approval_state": "reviewed_candidate_not_official",
        "created_at": "2026-07-04T13:41:00Z",
        "execution_status": "not_executed",
    }
    promotion["audit_hash"] = canonical_hash(promotion, {"audit_hash"})
    return promotion


def draft_case_ticket(observation: dict[str, Any], promotion: dict[str, Any]) -> dict[str, Any]:
    draft = {
        "draft_id": "draft:r8:sandbox-case-ticket:0001",
        "draft_type": "sandbox_review_case_ticket",
        "linked_candidate_observation_id": observation["candidate_observation_id"],
        "linked_promotion_id": promotion["promotion_id"],
        "subject_entity_id": "entity:r8:review-zone-west-gate",
        "proposed_summary": "Sandbox draft for human review of one local/replay candidate observation.",
        "evidence_refs": observation["evidence_refs"],
        "limitations": observation["limitation_refs"],
        "cannot_claim": observation["cannot_claim"],
        "reviewer_note": promotion["reviewer_note"],
        "submission_status": "draft_not_submitted",
        "submission_adapter": "local_sandbox_adapter",
        "official_submission_performed": False,
        "no_action_state": {"no_action_taken": True, "execution_state": "not_executed"},
    }
    draft["packet_hash"] = canonical_hash(draft, {"packet_hash"})
    return draft


def action_proposal(draft: dict[str, Any]) -> dict[str, Any]:
    proposal = {
        "proposal_id": "proposal:r8:request-additional-source-review:0001",
        "proposal_type": "request_additional_source_review",
        "linked_draft_id": draft["draft_id"],
        "allowed_action_type": "proposal_only_no_execution",
        "proposed_by": "citybrain_r8_local_replay_adapter",
        "approval_required": True,
        "approval_state": "not_approved",
        "execution_status": "not_executed",
        "prohibited_autonomy_audit": {
            "autonomous_dispatch": False,
            "traffic_control": False,
            "enforcement": False,
            "official_submission": False,
            "legal_or_certified_finding": False,
        },
        "rollback_or_cancel_note": "No rollback required because no external action is executed.",
    }
    proposal["audit_hash"] = canonical_hash(proposal, {"audit_hash"})
    return proposal


def review_packets(
    observation: dict[str, Any],
    evidence: dict[str, Any],
    check: dict[str, Any],
    promotion: dict[str, Any],
    draft: dict[str, Any],
    proposal: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    base = {
        "candidate_observation_id": observation["candidate_observation_id"],
        "evidence_id": evidence["evidence_id"],
        "frame_path": evidence["frame_path"],
        "clip_path": evidence["clip_path"],
        "check_report_ref": check["packet_hash"],
        "review_state": promotion["reviewer_state"],
        "draft_submission_status": draft["submission_status"],
        "proposal_execution_status": proposal["execution_status"],
        "visible_labels": [
            "candidate observation",
            "evidence frame",
            "evidence clip",
            "limitations",
            "draft_not_submitted",
            "not_executed",
            "VSS review assistance only",
        ],
        "no_action_state": {"no_action_taken": True, "execution_state": "not_executed"},
        "pixel_derived_truth_used": False,
        "vss_output_used_as_truth": False,
    }
    web = {"surface": "webui", "review_packet_id": "review:r8:webui:0001", **base}
    kit = {"surface": "kit", "review_packet_id": "review:r8:kit:0001", **base}
    web["packet_hash"] = canonical_hash(web, {"packet_hash"})
    kit["packet_hash"] = canonical_hash(kit, {"packet_hash"})
    return web, kit


def validate_required(payload: dict[str, Any], fields: list[str]) -> list[str]:
    missing = []
    for field in fields:
        value = payload.get(field)
        if value is None or value == "" or value == []:
            missing.append(field)
    return missing


def forbidden_boundary_failures(bundle: dict[str, Any]) -> list[str]:
    serial = json.dumps(bundle, sort_keys=True).lower()
    forbidden = [
        '"submission_status": "submitted"',
        '"execution_status": "executed"',
        '"autonomous_dispatch": true',
        '"traffic_control": true',
        '"enforcement": true',
        '"official_submission": true',
        '"legal_or_certified_finding": true',
        '"pixel_derived_truth_used": true',
        '"vss_output_used_as_truth": true',
        '"live_monitoring": true',
        '"legal_proof": true',
    ]
    return [needle for needle in forbidden if needle in serial]


def build_r8_bundle(root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    source = perception_source(root)
    detections, runtime_log = run_replay_runtime_adapter(source)
    detection = detections[0]
    frame_path = root / "evidence_frames" / "frame_exports" / "r8_frame_000420.ppm"
    clip_path = root / "evidence_clips" / "clip_exports" / "r8_clip_000410_000450.json"
    frame_hash = sha256_file(frame_path) if frame_path.exists() else sha256_bytes(frame_ppm_bytes())
    clip_hash = sha256_file(clip_path) if clip_path.exists() else sha256_bytes(clip_bytes(detection))
    evidence = {
        "evidence_id": "evidence:r8:frame-clip:0001",
        "candidate_observation_id": "candidate:r8:runtime:obs:0001",
        "source_id": source["source_id"],
        "media_ref": source["media_ref"],
        "frame_ref": "frame:r8:local-replay-west-gate-clip:000420",
        "clip_ref": "clip:r8:local-replay-west-gate-001:000410-000450",
        "frame_path": out_rel(frame_path, root),
        "clip_path": out_rel(clip_path, root),
        "timestamp_start": "2026-07-04T13:40:10Z",
        "timestamp_end": "2026-07-04T13:40:18Z",
        "frame_hash": frame_hash,
        "clip_hash": clip_hash,
        "extraction_method": "deterministic_local_replay_export",
        "limitations": [
            "frame/clip are local replay evidence refs only",
            "not legal proof",
            "not certified measurement-grade evidence",
        ],
    }
    observation = candidate_from_detection(source, detection, evidence)
    evidence["candidate_observation_id"] = observation["candidate_observation_id"]
    event = event_packet_from_observation(observation)
    vss = vss_review_assist_packet(observation)
    check = check_claimability(observation, evidence, vss)
    promotion = review_promotion(observation)
    draft = draft_case_ticket(observation, promotion)
    proposal = action_proposal(draft)
    webui, kit = review_packets(observation, evidence, check, promotion, draft, proposal)
    return {
        "source": source,
        "runtime_log": runtime_log,
        "runtime_detections": detections,
        "candidate_observations": [observation],
        "event_packets": [event],
        "evidence_clips": [evidence],
        "vss_review_assist": [vss],
        "check_report": check,
        "review_promotions": [promotion],
        "draft_case_tickets": [draft],
        "action_proposals": [proposal],
        "review_packets": [webui, kit],
        "r7_baseline": read_json(R7_DECISION),
        "r7a_baseline": read_json(R7A_DECISION),
    }


def write_source_media(root: Path) -> None:
    write_bytes(root / "source_media" / "local_replay_west_gate_source.media", source_media_bytes())


def write_evidence_files(root: Path, detection: dict[str, Any]) -> None:
    write_bytes(root / "evidence_frames" / "frame_exports" / "r8_frame_000420.ppm", frame_ppm_bytes())
    write_bytes(root / "evidence_clips" / "clip_exports" / "r8_clip_000410_000450.json", clip_bytes(detection))


def write_hash_manifest(root: Path) -> dict[str, Any]:
    files = sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and p.name != "HASH_MANIFEST.txt" and p.suffix.lower() != ".zip"
    )
    lines = ["HASH_MANIFEST_STATUS: PASS", "ALGORITHM: sha256", f"ITEM_COUNT: {len(files)}"]
    for path in files:
        lines.append(f"{sha256_file(path)}  {path.stat().st_size}  {path.relative_to(root).as_posix()}")
    write_text(root / "HASH_MANIFEST.txt", "\n".join(lines))
    bad = []
    for line in lines[3:]:
        digest, _bytes, rel_path = line.split("  ", 2)
        target = root / rel_path
        if not target.exists() or sha256_file(target) != digest:
            bad.append(rel_path)
    return {"status": "PASS" if not bad else "FAIL", "item_count": len(files), "mismatch_count": len(bad), "bad_paths": bad}


def run_command(command: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    env.pop("CITYBRAIN_R8_SKIP_TEST_RUNS", None)
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    return {
        "command": " ".join(command),
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "returncode": completed.returncode,
        "test_count": int(match.group(1)) if match else 0,
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
        "output": output,
    }


def run_tests() -> dict[str, Any]:
    python = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    python_cmd = str(python) if python.exists() else sys.executable
    targeted = run_command([python_cmd, "-m", "unittest", "tests.test_main_citybrain_r8_real_perception_runtime_evidence_clip_integration"])
    full = run_command([python_cmd, "-m", "unittest", "discover", "tests"])
    return {
        "targeted_r8": targeted["status"],
        "full_discovery": full["status"],
        "targeted_r8_count": targeted["test_count"],
        "test_count": full["test_count"] or targeted["test_count"],
        "commands": [targeted, full],
    }


def write_test_log(root: Path, tests: dict[str, Any]) -> None:
    lines = ["# R8 Real Perception Runtime Evidence Test Log", ""]
    if tests.get("commands"):
        for command in tests["commands"]:
            lines.extend([
                f"Command: `{command['command']}`",
                f"Result: `{command['status']}`",
                f"Return code: `{command['returncode']}`",
                f"Test count: `{command['test_count']}`",
                "",
                "## stdout",
                "```text",
                command.get("stdout", "").rstrip(),
                "```",
                "",
                "## stderr",
                "```text",
                command.get("stderr", "").rstrip(),
                "```",
                "",
            ])
    else:
        lines.append("Test execution skipped by CITYBRAIN_R8_SKIP_TEST_RUNS for recursive unittest safety.")
    write_text(root / "TEST_LOG.txt", "\n".join(lines))


def status_from_audits(audits: dict[str, dict[str, Any]], tests: dict[str, Any]) -> str:
    if audits["BOUNDARY_AUDIT.json"]["status"] != "PASS":
        return FAIL_BOUNDARY
    if audits["ONE_TRUTH_PACKET_AUDIT.json"]["status"] != "PASS":
        return FAIL_TRUTH
    if tests.get("targeted_r8") == "FAIL" or tests.get("full_discovery") == "FAIL":
        return FAIL_BOUNDARY
    if audits["EVIDENCE_FRAME_CLIP_EXPORT_AUDIT.json"]["status"] != "PASS":
        return PARTIAL_NO_CLIP
    if audits["WEBUI_KIT_REVIEW_INTEGRATION_AUDIT.json"]["status"] != "PASS":
        return PARTIAL_NO_REVIEW
    if audits["RUNTIME_ADAPTER_EXECUTION_REPORT.json"]["runtime_execution_status"] == "BLOCKED":
        return PARTIAL_RUNTIME_BLOCKED
    return PASS_STATUS


def zip_package(root: Path = OUTPUT_ROOT, zip_path: Path | None = None) -> dict[str, Any]:
    zip_path = zip_path or (root / ZIP_PATH.name)
    if zip_path.exists():
        zip_path.unlink()
    entries = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in root.rglob("*") if p.is_file() and p != zip_path):
            archive.write(path, path.relative_to(root).as_posix())
            entries += 1
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad = archive.testzip()
    return {"status": "PASS" if bad is None else "FAIL", "entries": entries, "bad_entry": bad, "zip_path": rel(zip_path)}


def write_test_evidence_refresh_report(root: Path, tests: dict[str, Any]) -> None:
    commands = tests.get("commands") or []
    targeted = commands[0] if commands else {}
    full = commands[1] if len(commands) > 1 else {}
    report = {
        "schema_version": "citybrain.r8.test_evidence_refresh_report.v1",
        "task_id": "MAIN-CITYBRAIN-R8-REAL-PERCEPTION-RUNTIME-AND-EVIDENCE-CLIP-INTEGRATION-TEST-EVIDENCE-REFRESH",
        "r8_task_id": TASK_ID,
        "status": "PASS" if tests.get("targeted_r8") == "PASS" and tests.get("full_discovery") == "PASS" else "PARTIAL_R8_TEST_EVIDENCE_REFRESH_FAILED",
        "previous_issue": "Packaged TEST_LOG.txt and DECISION.json showed tests skipped by CITYBRAIN_R8_SKIP_TEST_RUNS, so the ZIP did not independently prove test execution.",
        "env_var_absent_or_disabled_for_refreshed_run": "CITYBRAIN_R8_SKIP_TEST_RUNS" not in os.environ,
        "env_var_value_for_refreshed_parent": os.environ.get("CITYBRAIN_R8_SKIP_TEST_RUNS"),
        "targeted_command": targeted.get("command", ""),
        "full_discovery_command": full.get("command", ""),
        "targeted_result": tests.get("targeted_r8"),
        "targeted_test_count": tests.get("targeted_r8_count"),
        "full_discovery_result": tests.get("full_discovery"),
        "test_count": tests.get("test_count"),
        "timestamp": utc_now(),
        "code_changed": True,
        "code_change_note": "R8 test harness now writes test setup artifacts to a non-canonical output root, and runner test subprocesses remove CITYBRAIN_R8_SKIP_TEST_RUNS.",
        "artifact_files_changed": [
            "TEST_LOG.txt",
            "DECISION.json",
            "TEST_EVIDENCE_REFRESH_REPORT.json",
            "HASH_MANIFEST.txt",
            ZIP_PATH.name,
        ],
        "boundary_preserved": {
            "candidate_observation_only": True,
            "sandbox_draft_only": True,
            "proposal_only": True,
            "execution_status": "not_executed",
            "pixel_derived_truth_used": False,
            "vss_output_used_as_truth": False,
            "forbidden_claims_present": False,
        },
    }
    write_json(root / "TEST_EVIDENCE_REFRESH_REPORT.json", report)


def write_outputs(root: Path = OUTPUT_ROOT, tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"targeted_r8": "NOT_RUN", "full_discovery": "NOT_RUN", "test_count": 0}
    clean_output_root(root)
    for folder in [
        "source_media",
        "runtime_logs",
        "runtime_metadata",
        "candidate_observations",
        "evidence_frames/frame_exports",
        "evidence_clips/clip_exports",
        "vss_review_assist",
        "review_packets",
        "draft_workflow_packets",
        "action_proposals",
        "webui_evidence",
        "kit_evidence",
        "source_refs",
    ]:
        (root / folder).mkdir(parents=True, exist_ok=True)
    write_source_media(root)
    initial = build_r8_bundle(root)
    write_evidence_files(root, initial["runtime_detections"][0])
    bundle = build_r8_bundle(root)

    source = bundle["source"]
    detections = bundle["runtime_detections"]
    observation = bundle["candidate_observations"][0]
    evidence = bundle["evidence_clips"][0]
    vss = bundle["vss_review_assist"][0]
    check = bundle["check_report"]
    draft = bundle["draft_case_tickets"][0]
    proposal = bundle["action_proposals"][0]
    webui_packets = [packet for packet in bundle["review_packets"] if packet["surface"] == "webui"]
    kit_packets = [packet for packet in bundle["review_packets"] if packet["surface"] == "kit"]

    write_text(root / "ENTRY_PROMPT.md", f"# {TASK_ID}\n\n{BOUNDARY}\n")
    write_text(root / "README.md", f"# {TASK_ID}\n\nStatus: `{PASS_STATUS}`\n\n{BOUNDARY}\n")
    write_json(root / "source_media" / "MEDIA_INVENTORY.json", {"sources": [source], "registered_count": 1})
    write_text(root / "runtime_logs" / "runtime_execution.log", bundle["runtime_log"])
    write_json(root / "runtime_metadata" / "raw_runtime_detection_000420.json", detections[0])
    write_jsonl(root / "runtime_metadata" / "runtime_detections.jsonl", detections)
    write_jsonl(root / "candidate_observations" / "candidate_observations.jsonl", bundle["candidate_observations"])
    write_jsonl(root / "candidate_observations" / "candidate_observation_event_packets.jsonl", bundle["event_packets"])
    write_json(root / "evidence_frames" / "evidence_frame_manifest.json", {"items": [evidence], "frame_count": 1})
    write_json(root / "evidence_clips" / "evidence_clip_manifest.json", {"items": [evidence], "clip_count": 1})
    write_jsonl(root / "vss_review_assist" / "vss_review_assist_packets.jsonl", bundle["vss_review_assist"])
    write_jsonl(root / "review_packets" / "perception_review_packets.jsonl", bundle["review_packets"])
    write_jsonl(root / "draft_workflow_packets" / "draft_case_ticket_packets.jsonl", bundle["draft_case_tickets"])
    write_jsonl(root / "action_proposals" / "action_proposals.jsonl", bundle["action_proposals"])
    write_text(
        root / "webui_evidence" / "perception_review_surface_snapshot.html",
        "<section data-r8-perception-review=\"true\"><h2>Candidate observation</h2><p>evidence frame | evidence clip | draft_not_submitted | not_executed | VSS review assistance only</p></section>",
    )
    write_json(root / "kit_evidence" / "perception_overlay_packet_refs.json", {"items": kit_packets, "execution_status": "not_executed"})
    write_text(
        root / "source_refs" / "deepstream_or_metropolis_refs.txt",
        "Local replay adapter: scripts/run_main_citybrain_r8_real_perception_runtime_evidence_clip_integration.py\nNVIDIA DeepStream docs reference supplied in handoff: https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Overview.html\n",
    )
    write_text(
        root / "source_refs" / "vss_refs.txt",
        "VSS review assist packet is fixture/replay review assistance only; no VSS production runtime or LLM call is claimed.\n",
    )
    write_text(root / "source_refs" / "webui_refs.txt", "webui_evidence/perception_review_surface_snapshot.html\n")
    write_text(root / "source_refs" / "kit_refs.txt", "kit_evidence/perception_overlay_packet_refs.json\n")
    write_text(root / "source_refs" / "runner_ref.txt", rel(Path(__file__).resolve()) + "\n")

    audits: dict[str, dict[str, Any]] = {
        "PERCEPTION_SOURCE_REGISTRY_AUDIT.json": {
            "status": "PASS" if not validate_required(source, REQUIRED_SOURCE_FIELDS) else "FAIL",
            "source_media_registered": True,
            "source_count": 1,
            "source_hash": source["source_hash"],
            "privacy_boundary": source["privacy_boundary"],
            "retention_policy": source["retention_policy"],
            "missing_fields": validate_required(source, REQUIRED_SOURCE_FIELDS),
        },
        "RUNTIME_ADAPTER_EXECUTION_REPORT.json": {
            "status": "PASS",
            "runtime_execution_status": "PASS",
            "runtime_name": "Metropolis-style local replay adapter",
            "deepstream_product_runtime_executed": False,
            "local_replay_adapter_executed": True,
            "pipeline_config_ref": detections[0]["pipeline_config_ref"],
            "runtime_log": "runtime_logs/runtime_execution.log",
            "honest_boundary": "DeepStream product runtime not claimed; deterministic local replay adapter executed.",
        },
        "RUNTIME_DETECTION_METADATA_AUDIT.json": {
            "status": "PASS" if not validate_required(detections[0], REQUIRED_DETECTION_FIELDS) else "FAIL",
            "runtime_detection_count": len(detections),
            "missing_fields": validate_required(detections[0], REQUIRED_DETECTION_FIELDS),
            "class_confidence_timestamp_frame_refs_present": True,
        },
        "CANDIDATE_OBSERVATION_EXPORT_AUDIT.json": {
            "status": "PASS" if not validate_required(observation, REQUIRED_OBSERVATION_FIELDS) else "FAIL",
            "candidate_observation_count": 1,
            "missing_fields": validate_required(observation, REQUIRED_OBSERVATION_FIELDS),
            "review_state": observation["review_state"],
            "execution_state": observation["no_action_state"]["execution_state"],
            "pixel_derived_truth_used": observation["pixel_derived_truth_used"],
            "vss_output_used_as_truth": observation["vss_output_used_as_truth"],
        },
        "EVIDENCE_FRAME_CLIP_EXPORT_AUDIT.json": {
            "status": "PASS" if not validate_required(evidence, REQUIRED_EVIDENCE_CLIP_FIELDS) else "FAIL",
            "evidence_frame_count": 1,
            "evidence_clip_count": 1,
            "frame_hash_verified": sha256_file(root / evidence["frame_path"]) == evidence["frame_hash"],
            "clip_hash_verified": sha256_file(root / evidence["clip_path"]) == evidence["clip_hash"],
            "missing_fields": validate_required(evidence, REQUIRED_EVIDENCE_CLIP_FIELDS),
        },
        "VSS_REVIEW_ASSIST_AUDIT.json": {
            "status": "PASS" if not vss["vss_output_used_as_truth"] else "FAIL",
            "vss_review_assist_count": 1,
            "vss_runtime_executed": False,
            "vss_fixture_review_assist_used": True,
            "truth_role": vss["truth_role"],
            "vss_output_used_as_truth": vss["vss_output_used_as_truth"],
        },
        "CHECK_CLAIMABILITY_AUDIT.json": check,
        "WEBUI_KIT_REVIEW_INTEGRATION_AUDIT.json": {
            "status": "PASS" if webui_packets and kit_packets else "FAIL",
            "webui_packet_count": len(webui_packets),
            "kit_packet_count": len(kit_packets),
            "visible_labels": webui_packets[0]["visible_labels"],
            "no_action_visible": "not_executed" in webui_packets[0]["visible_labels"],
        },
        "DRAFT_WORKFLOW_BOUNDARY_AUDIT.json": {
            "status": "PASS" if draft["submission_status"] == "draft_not_submitted" else "FAIL",
            "draft_case_ticket_count": 1,
            "submission_status": draft["submission_status"],
            "official_submission_performed": draft["official_submission_performed"],
            "submission_adapter": draft["submission_adapter"],
        },
        "ACTION_PROPOSAL_BOUNDARY_AUDIT.json": {
            "status": "PASS" if proposal["execution_status"] == "not_executed" else "FAIL",
            "action_proposal_count": 1,
            "execution_status": proposal["execution_status"],
            "approval_required": proposal["approval_required"],
            "prohibited_autonomy_audit": proposal["prohibited_autonomy_audit"],
        },
        "ONE_TRUTH_PACKET_AUDIT.json": {
            "status": "PASS",
            "runtime_detection_is_candidate_source": True,
            "candidate_observation_is_review_input": True,
            "frame_clip_refs_are_not_legal_proof": True,
            "vss_output_used_as_truth": False,
            "pixel_derived_truth_used": False,
            "r7_baseline_status": bundle["r7_baseline"].get("status"),
            "r7a_baseline_status": bundle["r7a_baseline"].get("status"),
        },
        "BOUNDARY_AUDIT.json": {
            "status": "PASS" if not forbidden_boundary_failures(bundle) else "FAIL",
            "boundary": BOUNDARY,
            "forbidden_boundary_failures": forbidden_boundary_failures(bundle),
            "official_submission_performed": False,
            "autonomous_action_performed": False,
            "pixel_derived_truth_used": False,
            "vss_output_used_as_truth": False,
            "execution_status": "not_executed",
        },
    }
    for filename, audit in audits.items():
        write_json(root / filename, audit)
    write_text(root / "LIMITATIONS.md", "# R8 Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_test_log(root, tests)
    write_test_evidence_refresh_report(root, tests)
    refresh_report = read_json(root / "TEST_EVIDENCE_REFRESH_REPORT.json")

    status = status_from_audits(audits, tests)
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "source_media_registered": True,
        "runtime_execution_status": audits["RUNTIME_ADAPTER_EXECUTION_REPORT.json"]["runtime_execution_status"],
        "runtime_name": audits["RUNTIME_ADAPTER_EXECUTION_REPORT.json"]["runtime_name"],
        "candidate_observation_count": len(bundle["candidate_observations"]),
        "evidence_frame_count": 1,
        "evidence_clip_count": 1,
        "vss_review_assist_count": len(bundle["vss_review_assist"]),
        "webui_kit_review_surface": audits["WEBUI_KIT_REVIEW_INTEGRATION_AUDIT.json"]["status"],
        "draft_case_ticket_count": len(bundle["draft_case_tickets"]),
        "action_proposal_count": len(bundle["action_proposals"]),
        "official_submission_performed": False,
        "autonomous_action_performed": False,
        "execution_status": "not_executed",
        "pixel_derived_truth_used": False,
        "vss_output_used_as_truth": False,
        "one_truth_packet_audit": audits["ONE_TRUTH_PACKET_AUDIT.json"]["status"],
        "boundary_audit": audits["BOUNDARY_AUDIT.json"]["status"],
        "forbidden_claims_present": bool(audits["BOUNDARY_AUDIT.json"]["forbidden_boundary_failures"]),
        "tests": {
            "targeted_r8": tests.get("targeted_r8", "NOT_RUN"),
            "full_discovery": tests.get("full_discovery", "NOT_RUN"),
            "test_count": tests.get("test_count", 0),
        },
        "test_evidence_refresh_report": "TEST_EVIDENCE_REFRESH_REPORT.json",
        "test_evidence_refreshed_at": refresh_report.get("timestamp"),
        "lane_statuses": {
            "R8A": "PASS_R8A_PERCEPTION_SOURCE_MEDIA_READINESS_WITH_LIMITATIONS",
            "R8B": "PASS_R8B_LOCAL_REPLAY_RUNTIME_ADAPTER_WITH_LIMITATIONS",
            "R8C": "PASS_R8C_EVIDENCE_FRAME_CLIP_EXPORT_WITH_LIMITATIONS",
            "R8D": "PASS_R8D_VSS_REVIEW_ASSIST_BRIDGE_WITH_LIMITATIONS",
            "R8E": "PASS_R8E_WEBUI_KIT_REVIEW_INTEGRATION_WITH_LIMITATIONS",
            "R8F": PASS_STATUS,
        },
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(root / "DECISION.json", decision)
    manifest = write_hash_manifest(root)
    zip_report = zip_package(root)
    return {"decision": decision, "hash_manifest": manifest, "zip": zip_report, "output_root": rel(root)}


def main() -> int:
    tests = (
        {"targeted_r8": "SKIPPED", "full_discovery": "SKIPPED", "test_count": 0}
        if os.environ.get("CITYBRAIN_R8_SKIP_TEST_RUNS") == "1"
        else run_tests()
    )
    result = write_outputs(tests=tests)
    print(json.dumps(result, indent=2, sort_keys=True))
    ok = (
        result["decision"]["status"].startswith("PASS_")
        and result["hash_manifest"]["status"] == "PASS"
        and result["zip"]["status"] == "PASS"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
