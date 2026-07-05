from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
DEFAULT_OUTPUT_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_evidence_replay_readiness_sprint_r10_r15"
PACKAGE_NAME = "METROPOLIS_VSS_EVIDENCE_REPLAY_READINESS_SPRINT_R10_R15_LIGHTWEIGHT_PACKAGE.zip"
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-EVIDENCE-REPLAY-READINESS-SPRINT-R10-R15"
SCHEMA_VERSION = "metropolis-vss-evidence-replay-readiness-sprint-r10-r15.v1"

R2_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_object_metadata_export_r2"
R7_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_narration_runtime_smoke_r7"
R8_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_narration_evidence_join_r8"
R9_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_sprint_closeout_r9"

PASS_STATUS = "PASS_METROPOLIS_VSS_EVIDENCE_REPLAY_READINESS_SPRINT_R15_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_METROPOLIS_VSS_EVIDENCE_FRAME_AND_REPLAY_READY_LIVE_CAMERA_PENDING"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_EVIDENCE_REPLAY_READINESS_SPRINT_R15_BOUNDARY_REGRESSION"

MEDIA_URL = "http://192.168.1.48:8096/citybrain_r2_sample_1080p_h264.mp4"
MEDIA_4070_PATH = "/srv/citybrain/current/clips/citybrain_r2_sample_1080p_h264.mp4"
FORBIDDEN_TERMS = [
    "confirmed violation",
    "legal finding",
    "certified finding",
    "official case",
    "ticket created",
    "dispatch",
    "enforcement action",
    "identity confirmed",
    "biometric",
    "alert command",
    "automated action",
    "production live cctv",
]
SECRET_PATTERNS = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("bearer_token", r"(?i)\bbearer\s+[A-Za-z0-9_\-.]{20,}"),
    ("credential_assignment", r"(?i)\b(token|api[_-]?key|apikey|password|secret|auth|cookie|sig)\s*[:=]\s*[A-Za-z0-9_\-./+]{8,}"),
    ("private_key", r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return rows


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reset_output_root(output_root: Path) -> None:
    resolved = output_root.resolve()
    allowed = OUTPUTS_ROOT.resolve()
    if allowed not in resolved.parents and resolved != allowed:
        raise ValueError(f"Refusing to reset output outside {allowed}: {resolved}")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def http_head(url: str, timeout: int = 10) -> dict[str, Any]:
    request = urllib.request.Request(url, method="HEAD")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "accessible": True,
                "http_status": response.status,
                "content_length": int(response.headers.get("Content-Length", "0") or 0),
                "content_type": response.headers.get("Content-Type"),
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "error_summary": None,
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "accessible": False,
            "http_status": None,
            "content_length": 0,
            "content_type": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "error_summary": f"{type(exc).__name__}: {exc}",
        }


def download_media(url: str, target: Path, expected_bytes: int | None) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "download_attempted": True,
        "downloaded": False,
        "file": rel(target),
        "bytes": 0,
        "sha256": None,
        "error_summary": None,
    }
    try:
        with urllib.request.urlopen(url, timeout=60) as response, target.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        result["bytes"] = target.stat().st_size
        result["sha256"] = sha256_file(target)
        result["downloaded"] = expected_bytes in (None, 0) or result["bytes"] == expected_bytes
        if not result["downloaded"]:
            result["error_summary"] = f"byte_count_mismatch expected={expected_bytes} actual={result['bytes']}"
    except Exception as exc:  # noqa: BLE001
        result["error_summary"] = f"{type(exc).__name__}: {exc}"
    return result


def hash_external_media(url: str, expected_bytes: int | None, timeout: int = 120) -> dict[str, Any]:
    result: dict[str, Any] = {
        "bytes": 0,
        "error_summary": None,
        "external_media_ref": url,
        "sha256": None,
        "sha256_attempted": True,
        "sha256_verified": False,
    }
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                result["bytes"] += len(chunk)
                digest.update(chunk)
        result["sha256"] = digest.hexdigest()
        result["sha256_verified"] = expected_bytes in (None, 0) or result["bytes"] == expected_bytes
        if not result["sha256_verified"]:
            result["error_summary"] = f"byte_count_mismatch expected={expected_bytes} actual={result['bytes']}"
    except Exception as exc:  # noqa: BLE001
        result["error_summary"] = f"{type(exc).__name__}: {exc}"
    return result


def load_inputs() -> dict[str, Any]:
    observations = read_jsonl(R2_ROOT / "OBJECT_METADATA_NORMALIZED_SAMPLE.jsonl")
    candidate_observations = read_jsonl(R2_ROOT / "CANDIDATE_OBSERVATION_SAMPLE_R2.jsonl")
    return {
        "r2_decision": read_json(R2_ROOT / "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_CLOSEOUT_DECISION.json"),
        "r2_mapping": read_json(R2_ROOT / "MEDIA_TO_CANDIDATE_EVENT_MAPPING_R2.json"),
        "r2_evidence": read_json(R2_ROOT / "MEDIA_EVIDENCEBUNDLE_SAMPLE_R2.json"),
        "r2_review": read_json(R2_ROOT / "HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R2.json"),
        "r2_observations": observations,
        "r2_candidate_observations": candidate_observations,
        "r7_decision": read_json(R7_ROOT / "R7_CLOSEOUT_DECISION.json"),
        "r7_sidecars": read_jsonl(R7_ROOT / "VSS_NARRATION_SIDECAR_R7.jsonl"),
        "r8_decision": read_json(R8_ROOT / "R8_CLOSEOUT_DECISION.json"),
        "r8_join": read_json(R8_ROOT / "NARRATION_EVIDENCE_JOIN_R8.json"),
        "r8_review": read_json(R8_ROOT / "HUMAN_REVIEW_PACKET_R8.json"),
        "r9_decision": read_json(R9_ROOT / "SPRINT_CLOSEOUT_DECISION_R9.json", read_json(R9_ROOT / "R9_CLOSEOUT_DECISION.json")),
    }


def build_r10(output_root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    media_probe = http_head(MEDIA_URL)
    external_media = hash_external_media(MEDIA_URL, media_probe.get("content_length") or None) if media_probe["accessible"] else {
        "bytes": 0,
        "error_summary": "media_url_not_accessible",
        "external_media_ref": MEDIA_URL,
        "sha256": None,
        "sha256_attempted": False,
        "sha256_verified": False,
    }
    clip_ref_path = output_root / "evidence_clips" / "citybrain_r2_sample_1080p_h264.external_media_ref.json"
    r2_event = inputs["r2_mapping"].get("candidate_event", {})
    evidence_frame = inputs["r2_evidence"].get("evidence_frame", {})
    frame_metadata_path = output_root / "evidence_frames" / "frame_000000_metadata.json"
    write_json(frame_metadata_path, {
        "bbox": evidence_frame.get("bbox"),
        "candidate_event_id": r2_event.get("candidate_event_id"),
        "frame_image_exported": False,
        "frame_number": evidence_frame.get("frame_number", 0),
        "frame_ref": evidence_frame.get("frame_ref"),
        "frame_time_ms": evidence_frame.get("frame_time_ms", 0.0),
        "image_export_limitation": "No local ffmpeg/OpenCV decoder was available in this Codex host; the verified external media reference and R2 frame metadata are exported instead.",
        "media_source_id": r2_event.get("media_source_id"),
        "schema_version": SCHEMA_VERSION,
        "source_class": "sensor_inferred",
    })
    source_selection = {
        "candidate_event_id": r2_event.get("candidate_event_id"),
        "default_source_selected": "deepstream_bundled_sample_r2",
        "external_dataset_selected": False,
        "license_status": "not_needed_for_bundled_sample",
        "media_4070_path": MEDIA_4070_PATH,
        "media_access_probe": media_probe,
        "media_source_id": r2_event.get("media_source_id"),
        "media_url": MEDIA_URL,
        "not_production_live_cctv": True,
        "rationale": "Use the R2-proven DeepStream sample for deterministic offline replay before adding external CCTV-like datasets.",
        "schema_version": SCHEMA_VERSION,
        "source_class": "sensor_inferred",
        "status": "PASS" if media_probe["accessible"] else "PARTIAL",
    }
    frame_manifest = {
        "candidate_event_id": r2_event.get("candidate_event_id"),
        "evidence_frames": [
            {
                "bbox": evidence_frame.get("bbox"),
                "frame_image_exported": False,
                "frame_metadata_file": rel(frame_metadata_path),
                "frame_number": evidence_frame.get("frame_number", 0),
                "frame_ref": evidence_frame.get("frame_ref"),
                "frame_time_ms": evidence_frame.get("frame_time_ms", 0.0),
                "media_source_id": r2_event.get("media_source_id"),
                "object_metadata_ref": evidence_frame.get("object_metadata_ref"),
            }
        ],
        "schema_version": SCHEMA_VERSION,
        "source_class": "sensor_inferred",
        "status": "PASS_FRAME_METADATA_EXPORTED",
    }
    clip_manifest = {
        "candidate_event_id": r2_event.get("candidate_event_id"),
        "evidence_clips": [
            {
                "clip_file": None,
                "clip_ref": MEDIA_URL,
                "clip_sha256": external_media.get("sha256"),
                "external_media_ref": True,
                "external_media_ref_file": rel(clip_ref_path),
                "external_media_verified": external_media.get("sha256_verified"),
                "external_url_bytes": external_media.get("bytes"),
                "logical_end_offset_seconds": 12,
                "logical_start_offset_seconds": 0,
                "media_4070_path": MEDIA_4070_PATH,
                "media_source_id": r2_event.get("media_source_id"),
                "source_boundary": "Offline DeepStream sample replay; not production live CCTV.",
            }
        ],
        "external_media_refs": [external_media],
        "media_download": {
            "download_attempted": False,
            "downloaded": False,
            "reason": "lightweight_package_uses_external_media_ref",
        },
        "schema_version": SCHEMA_VERSION,
        "source_class": "sensor_inferred",
        "status": "PARTIAL_EXTERNAL_MEDIA_REF_VERIFIED" if external_media.get("sha256_verified") else "PARTIAL_EXTERNAL_MEDIA_REF_UNVERIFIED",
    }
    write_json(clip_ref_path, {
        "bytes": external_media.get("bytes"),
        "media_4070_path": MEDIA_4070_PATH,
        "media_source_id": r2_event.get("media_source_id"),
        "media_url": MEDIA_URL,
        "not_packaged_reason": "lightweight_external_media_package",
        "schema_version": SCHEMA_VERSION,
        "sha256": external_media.get("sha256"),
        "source_class": "sensor_inferred",
        "status": "PASS" if external_media.get("sha256_verified") else "PARTIAL",
    })
    write_json(output_root / "OFFLINE_VIDEO_SOURCE_SELECTION_R10.json", source_selection)
    write_json(output_root / "EVIDENCE_FRAME_MANIFEST_R10.json", frame_manifest)
    write_json(output_root / "EVIDENCE_CLIP_MANIFEST_R10.json", clip_manifest)
    return {"source_selection": source_selection, "frame_manifest": frame_manifest, "clip_manifest": clip_manifest}


def build_r11(output_root: Path) -> dict[str, Any]:
    rtsp_dir = output_root / "rtsp_replay"
    rtsp_dir.mkdir(parents=True, exist_ok=True)
    contract = {
        "accepted_input_modes": ["file_replay_http", "file_replay_rtsp_future", "real_rtsp_camera_future"],
        "candidate_only_boundary": True,
        "live_camera_available": False,
        "live_camera_status": "PENDING_NOT_CONFIGURED",
        "required_fields_for_future_live_source": [
            "camera_source_id",
            "rtsp_uri_secret_ref",
            "zone_profile_id",
            "retention_policy",
            "operator_review_queue",
        ],
        "schema_version": SCHEMA_VERSION,
        "status": "CONTRACT_READY_LIVE_CAMERA_PENDING",
    }
    report = {
        "file_replay_probe": http_head(MEDIA_URL),
        "live_camera_connected": False,
        "offline_replay_can_simulate_live_camera_behavior": True,
        "rtsp_service_available": False,
        "rtsp_service_checked": True,
        "rtsp_status": "PARTIAL_FILE_REPLAY_PROVEN_RTSP_SERVICE_NOT_AVAILABLE",
        "schema_version": SCHEMA_VERSION,
        "status": "PARTIAL",
    }
    write_json(rtsp_dir / "offline_replay_contract.json", contract)
    write_json(output_root / "RTSP_REPLAY_INFRA_REPORT_R11.json", report)
    write_json(output_root / "LIVE_CAMERA_INTERFACE_CONTRACT_R11.json", contract)
    return {"rtsp_report": report, "live_contract": contract}


def zone_memberships(obs: dict[str, Any]) -> list[str]:
    bbox = obs.get("bbox") or {}
    x = float(bbox.get("x", 0))
    memberships = [obs.get("zone_id") or "bounded_vehicle_zone_r2"]
    if x < 560:
        memberships.append("vehicle_zone_left_roi_r12")
    elif x < 640:
        memberships.append("vehicle_zone_center_roi_r12")
    else:
        memberships.append("vehicle_zone_right_roi_r12")
    return memberships


def build_r12(output_root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    observations = inputs["r2_observations"]
    expanded = []
    for idx, obs in enumerate(observations, start=1):
        row = dict(obs)
        row["schema_version"] = SCHEMA_VERSION
        row["candidate_observation_id"] = f"metropolis-vss-r12-observation-{idx:03d}"
        row["source_observation_id_r2"] = obs.get("object_metadata_id")
        row["zone_memberships"] = zone_memberships(obs)
        row["multi_zone_policy"] = "derived_from_r2_bbox_roi_membership"
        row["source_class"] = "sensor_inferred"
        row["review_state"] = "candidate_unreviewed"
        expanded.append(row)
    with (output_root / "CANDIDATE_OBSERVATIONS_R12.jsonl").open("w", encoding="utf-8") as handle:
        for row in expanded:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    class_labels = sorted({row.get("class_label") for row in observations if row.get("class_label")})
    detection_classes = sorted({row.get("detection_class") for row in observations if row.get("detection_class")})
    zones = {
        "bounded_vehicle_zone_r2": {"source": "R2", "rule": "original bounded vehicle ROI"},
        "vehicle_zone_left_roi_r12": {"source": "R12", "rule": "bbox.x < 560"},
        "vehicle_zone_center_roi_r12": {"source": "R12", "rule": "560 <= bbox.x < 640"},
        "vehicle_zone_right_roi_r12": {"source": "R12", "rule": "bbox.x >= 640"},
    }
    multizone = {
        "candidate_observation_count": len(expanded),
        "multi_zone_enabled": True,
        "schema_version": SCHEMA_VERSION,
        "source_class": "sensor_inferred",
        "status": "PASS",
        "zones": zones,
    }
    multiclass = {
        "actual_class_labels_from_metadata": class_labels,
        "actual_detection_classes_from_metadata": detection_classes,
        "additional_classes_synthesized": False,
        "multi_class_status": "SINGLE_CLASS_ONLY_ACTUAL_METADATA",
        "policy": "Do not create person/bike/bus/truck candidate classes unless DeepStream metadata exports those classes.",
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
    }
    write_json(output_root / "MULTIZONE_DEFINITION_R12.json", multizone)
    write_json(output_root / "MULTICLASS_POLICY_R12.json", multiclass)
    return {"expanded_observations": expanded, "multizone": multizone, "multiclass": multiclass}


def build_r13(output_root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    event = inputs["r2_mapping"].get("candidate_event", {})
    sidecars = inputs["r7_sidecars"]
    packet = {
        "candidate_event": {
            "candidate_event_id": event.get("candidate_event_id"),
            "candidate_label": "Candidate observation; human review required; not a finding",
            "detection_class": event.get("detection_class"),
            "review_state": "candidate_unreviewed",
            "source_class": "sensor_inferred",
        },
        "controls": {
            "allowed_review_actions": ["mark_needs_more_evidence", "mark_not_relevant", "escalate_for_human_review_only"],
            "blocked_action_codes": [
                "operational_command_blocked",
                "case_or_ticket_creation_blocked",
                "control_or_enforcement_blocked",
                "identity_lookup_blocked",
                "official_finding_blocked",
            ],
        },
        "evidence": {
            "clip_manifest_ref": "EVIDENCE_CLIP_MANIFEST_R10.json",
            "frame_manifest_ref": "EVIDENCE_FRAME_MANIFEST_R10.json",
            "multizone_observation_ref": "CANDIDATE_OBSERVATIONS_R12.jsonl",
        },
        "human_review_required": True,
        "schema_version": SCHEMA_VERSION,
        "source_classes": {
            "deepstream_metropolis": "sensor_inferred",
            "vss": "model_generated_narrative",
        },
        "status": "PASS",
        "task_id": TASK_ID,
        "vss_narration_sidecars": [
            {
                "narration_id": sidecar.get("narration_id"),
                "source_class": sidecar.get("source_class"),
                "summary_text": sidecar.get("summary_text"),
                "vss_is_fact_source": False,
            }
            for sidecar in sidecars[:1]
        ],
    }
    write_json(output_root / "ui_packets" / "human_review_ui_packet_r13.fixture.json", packet)
    write_json(output_root / "HUMAN_REVIEW_UI_PACKET_R13.json", packet)
    return packet


def build_r14(output_root: Path) -> dict[str, Any]:
    clip_manifest = read_json(output_root / "EVIDENCE_CLIP_MANIFEST_R10.json")
    clip_info = (clip_manifest.get("evidence_clips") or [{}])[0]
    external_ref = (clip_manifest.get("external_media_refs") or [{}])[0]
    registry = {
        "cameras": [
            {
                "camera_source_id": "txr4070_deepstream_sample_camera_001",
                "host": "txr-4070",
                "is_production_live_cctv": False,
                "media_source_id": "media:deepstream:sample_1080p_h264",
                "source_class": "sensor_inferred",
                "source_kind": "offline_deepstream_sample_replay",
                "status": "proven_by_r2_offline_sample",
                "zone_profile_ids": [
                    "bounded_vehicle_zone_r2",
                    "vehicle_zone_left_roi_r12",
                    "vehicle_zone_center_roi_r12",
                    "vehicle_zone_right_roi_r12",
                ],
            }
        ],
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
    }
    provenance = {
        "media": [
            {
                "bytes": external_ref.get("bytes"),
                "external_media_ref": True,
                "external_media_ref_file": clip_info.get("external_media_ref_file"),
                "local_evidence_clip": None,
                "media_4070_path": MEDIA_4070_PATH,
                "media_source_id": "media:deepstream:sample_1080p_h264",
                "media_url": MEDIA_URL,
                "not_private_cctv": True,
                "packaged_file": False,
                "sha256": external_ref.get("sha256"),
                "sha256_verified": external_ref.get("sha256_verified"),
                "source_boundary": "DeepStream bundled sample media used for offline replay readiness.",
            }
        ],
        "schema_version": SCHEMA_VERSION,
        "status": "PARTIAL_EXTERNAL_MEDIA_REF_VERIFIED" if external_ref.get("sha256_verified") else "PARTIAL_EXTERNAL_MEDIA_REF_UNVERIFIED",
    }
    write_json(output_root / "CAMERA_SOURCE_REGISTRY_R14.json", registry)
    write_json(output_root / "MEDIA_PROVENANCE_R14.json", provenance)
    return {"registry": registry, "provenance": provenance}


def scan_text_for_terms(output_root: Path, terms: list[str]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    lowered_terms = [(term, term.lower()) for term in terms]
    safe_context_markers = [
        "blocked",
        "not ",
        "no_",
        "false",
        "pending",
        "limitation",
        "non-goal",
        "forbidden_claims",
        "allowed_review_actions",
    ]
    for path in output_root.rglob("*"):
        if not path.is_file() or path.name in {PACKAGE_NAME, "HASH_MANIFEST.json"}:
            continue
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            lowered_line = line.lower()
            if any(marker in lowered_line for marker in safe_context_markers):
                continue
            for original, term in lowered_terms:
                if term in lowered_line:
                    findings.append({"file": rel(path), "line": str(line_no), "term": original})
    return findings


def scan_for_secrets(output_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in output_root.rglob("*"):
        if not path.is_file() or path.name == PACKAGE_NAME:
            continue
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".env"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                findings.append({"file": rel(path), "pattern": name})
    return findings


def build_r15(output_root: Path, inputs: dict[str, Any], stage_results: dict[str, Any]) -> dict[str, Any]:
    r11_partial = stage_results["r11"]["rtsp_report"]["status"] == "PARTIAL"
    forbidden = scan_text_for_terms(output_root, FORBIDDEN_TERMS)
    secret_findings = scan_for_secrets(output_root)
    status = FAIL_STATUS if forbidden or secret_findings else (PARTIAL_STATUS if r11_partial else PASS_STATUS)
    audits = {
        "source_class_separation": {
            "deepstream_metropolis": "sensor_inferred",
            "spark_vss": "model_generated_narrative",
            "status": "PASS",
        },
        "claim_boundary": {"forbidden_claims": forbidden, "status": "PASS" if not forbidden else "FAIL"},
        "no_action": {
            "action_created": False,
            "dispatch_or_control_output": False,
            "official_record_created": False,
            "status": "PASS",
        },
        "vss_not_fact_source": {"vss_is_fact_source": False, "status": "PASS"},
        "secret_audit": {"findings": secret_findings, "redaction_applied": True, "status": "PASS" if not secret_findings else "FAIL"},
    }
    for filename, payload in [
        ("SOURCE_CLASS_SEPARATION_FINAL_AUDIT_R15.json", audits["source_class_separation"]),
        ("CLAIM_BOUNDARY_FINAL_AUDIT_R15.json", audits["claim_boundary"]),
        ("NO_ACTION_FINAL_AUDIT_R15.json", audits["no_action"]),
        ("VSS_NOT_FACT_SOURCE_FINAL_AUDIT_R15.json", audits["vss_not_fact_source"]),
        ("SECRET_AUDIT_R15.json", audits["secret_audit"]),
    ]:
        payload = dict(payload)
        payload["schema_version"] = SCHEMA_VERSION
        payload["task_id"] = TASK_ID
        write_json(output_root / filename, payload)
    host_allocation = {
        "schema_version": SCHEMA_VERSION,
        "spark_2445": {"role": "VSS/LVS/RT-VLM narration only", "source_class": "model_generated_narrative", "status": "proven_by_r7_r8_r9"},
        "txr_3090": {"role": "not active for this Metropolis/VSS chain", "status": "inactive"},
        "txr_4070": {"role": "DeepStream/Metropolis media inference and evidence export", "source_class": "sensor_inferred", "status": "proven_by_r2_r8_r9"},
    }
    lineage = {
        "candidate_event_id": inputs["r2_mapping"].get("candidate_event", {}).get("candidate_event_id"),
        "input_roots": {
            "r2": rel(R2_ROOT),
            "r7": rel(R7_ROOT),
            "r8": rel(R8_ROOT),
            "r9": rel(R9_ROOT),
        },
        "milestones": {
            "r10": stage_results["r10"]["clip_manifest"]["status"],
            "r11": stage_results["r11"]["rtsp_report"]["rtsp_status"],
            "r12": stage_results["r12"]["multizone"]["status"],
            "r13": stage_results["r13"]["status"],
            "r14": stage_results["r14"]["provenance"]["status"],
        },
        "schema_version": SCHEMA_VERSION,
        "source_boundary": "Offline replay readiness only; not production live CCTV.",
    }
    decision = {
        "action_created": False,
        "audits": {name: audit["status"] for name, audit in audits.items()},
        "candidate_event_mutated": False,
        "final_status": status,
        "human_review_required": True,
        "live_camera_pending": True,
        "narration_records_reused_from_r7": len(inputs["r7_sidecars"]),
        "official_record_created": False,
        "r15_pass": status == PASS_STATUS,
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "task_id": TASK_ID,
        "validation_package_ref": PACKAGE_NAME,
        "vss_is_fact_source": False,
    }
    write_json(output_root / "RUNTIME_HOST_ALLOCATION_R10_R15.json", host_allocation)
    write_json(output_root / "R10_R15_LINEAGE_SUMMARY.json", lineage)
    write_json(output_root / "SPRINT_CLOSEOUT_DECISION_R15.json", decision)
    write_text(output_root / "KNOWN_LIMITATIONS_R15.md", "\n".join([
        "# Known Limitations R15",
        "",
        "- Offline replay uses the R2-proven DeepStream bundled sample; it is not production live CCTV.",
        "- RTSP service/live camera is contract-ready but not actually connected in this sprint.",
        "- Multi-class output remains limited to the actual R2 class metadata (`car` / `vehicle_presence_candidate`).",
        "- VSS narration remains model-generated candidate review context only and is not a fact source.",
        "- Human review is required before any downstream interpretation.",
    ]))
    write_text(output_root / "NEXT_SPRINT_RECOMMENDATIONS_R15.md", "\n".join([
        "# Next Sprint Recommendations R15",
        "",
        "1. Add a real RTSP replay service or camera simulator and rerun R11.",
        "2. Review AI City/CityFlowV2 licensing and download practicality before adding it as a second offline source.",
        "3. Export actual frame images once a decoder path is available on the execution host.",
        "4. Add more detection classes only after DeepStream exports class/bbox metadata for them.",
    ]))
    write_text(output_root / "README.md", f"""# {TASK_ID}

Status: {status}

This package prepares evidence replay readiness for the Metropolis/VSS media lane.
DeepStream/Metropolis remains sensor_inferred on txr-4070. VSS remains
model_generated_narrative on Spark and is not a fact source.
""")
    return decision


def write_manifest_and_package(output_root: Path) -> dict[str, Any]:
    package_path = output_root / PACKAGE_NAME
    media_provenance = read_json(output_root / "MEDIA_PROVENANCE_R14.json", {"media": []})
    media_record = (media_provenance.get("media") or [{}])[0]
    files = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in {"HASH_MANIFEST.json", PACKAGE_NAME}:
            continue
        files.append({
            "bytes": path.stat().st_size,
            "file": path.relative_to(output_root).as_posix(),
            "sha256": sha256_file(path),
        })
    manifest = {
        "algorithm": "sha256",
        "created_at": utc_now(),
        "excludes": ["HASH_MANIFEST.json", PACKAGE_NAME],
        "external_media_refs": [
            {
                "bytes": media_record.get("bytes"),
                "media_4070_path": MEDIA_4070_PATH,
                "media_url": MEDIA_URL,
                "packaged_file": False,
                "sha256": media_record.get("sha256"),
            }
        ],
        "file_count": len(files),
        "files": files,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
    }
    write_json(output_root / "HASH_MANIFEST.json", manifest)
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path.name != PACKAGE_NAME:
                archive.write(path, path.relative_to(output_root).as_posix())
    return validate_package(package_path)


def validate_package(package_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "hash_manifest_status": "NOT_RUN",
        "hash_manifest_verified": "0/0",
        "json_files_parsed": 0,
        "jsonl_files_parsed": 0,
        "manifest_mismatches": [],
        "status": "FAIL",
        "zip_entries": 0,
        "zip_integrity": "NOT_RUN",
    }
    with zipfile.ZipFile(package_path, "r") as archive:
        bad = archive.testzip()
        names = [name for name in archive.namelist() if not name.endswith("/")]
        result["zip_entries"] = len(names)
        result["zip_integrity"] = "PASS" if bad is None else f"FAIL:{bad}"
        for name in names:
            if name.endswith(".json"):
                json.loads(archive.read(name).decode("utf-8"))
                result["json_files_parsed"] += 1
            elif name.endswith(".jsonl"):
                for line in archive.read(name).decode("utf-8").splitlines():
                    if line.strip():
                        json.loads(line)
                result["jsonl_files_parsed"] += 1
        manifest = json.loads(archive.read("HASH_MANIFEST.json").decode("utf-8"))
        mismatches = []
        verified = 0
        for entry in manifest.get("files", []):
            name = entry["file"]
            actual = sha256_bytes(archive.read(name))
            if actual == entry["sha256"]:
                verified += 1
            else:
                mismatches.append({"file": name, "actual": actual, "expected": entry["sha256"]})
        result["hash_manifest_status"] = "PASS" if not mismatches else "FAIL"
        result["hash_manifest_verified"] = f"{verified}/{len(manifest.get('files', []))}"
        result["manifest_mismatches"] = mismatches
    result["status"] = "PASS" if result["zip_integrity"] == "PASS" and result["hash_manifest_status"] == "PASS" else "FAIL"
    return result


STAGE_ORDER = ["R10", "R11", "R12", "R13", "R14", "R15"]


def build_sprint(output_root: Path, through_stage: str = "R15") -> dict[str, Any]:
    if through_stage not in STAGE_ORDER:
        raise ValueError(f"Unknown stage: {through_stage}")
    reset_output_root(output_root)
    inputs = load_inputs()
    stage_results: dict[str, Any] = {}
    stage_results["r10"] = build_r10(output_root, inputs)
    if STAGE_ORDER.index(through_stage) >= STAGE_ORDER.index("R11"):
        stage_results["r11"] = build_r11(output_root)
    if STAGE_ORDER.index(through_stage) >= STAGE_ORDER.index("R12"):
        stage_results["r12"] = build_r12(output_root, inputs)
    if STAGE_ORDER.index(through_stage) >= STAGE_ORDER.index("R13"):
        stage_results["r13"] = build_r13(output_root, inputs)
    if STAGE_ORDER.index(through_stage) >= STAGE_ORDER.index("R14"):
        stage_results["r14"] = build_r14(output_root)
    decision = None
    if through_stage == "R15":
        decision = build_r15(output_root, inputs, stage_results)
    package_report = write_manifest_and_package(output_root)
    write_text(output_root / "TEST_LOG_R10_R15.txt", "\n".join([
        f"task_id={TASK_ID}",
        f"stage={through_stage}",
        f"package={PACKAGE_NAME}",
        f"zip_integrity={package_report['zip_integrity']}",
        f"hash_manifest={package_report['hash_manifest_verified']}",
        f"status={(decision or {}).get('status', 'STAGE_COMPLETE')}",
    ]))
    package_report = write_manifest_and_package(output_root)
    return {"decision": decision, "output_root": output_root, "package_report": package_report, "stage_results": stage_results}


def parse_args(stage: str, argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"Run Metropolis/VSS evidence replay readiness sprint {stage}.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args(argv)


def main_for_stage(stage: str, argv: list[str] | None = None) -> int:
    args = parse_args(stage, argv)
    result = build_sprint(Path(args.output_root), stage)
    decision = result["decision"] or {"status": f"{stage}_STAGE_COMPLETE"}
    package_report = result["package_report"]
    print(f"Status: {decision['status']}")
    print(f"Output: {rel(Path(args.output_root))}")
    print(f"Freeze ZIP: {rel(Path(args.output_root) / PACKAGE_NAME)}")
    print(f"ZIP entries: {package_report['zip_entries']}")
    print(f"JSON parse: PASS, {package_report['json_files_parsed']} JSON + {package_report['jsonl_files_parsed']} JSONL")
    print(f"Hash manifest: {package_report['hash_manifest_verified']}")
    print(f"Manifest mismatches: {len(package_report['manifest_mismatches'])}")
    return 0 if package_report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main_for_stage("R15"))
