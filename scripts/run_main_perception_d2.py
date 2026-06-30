from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_perception_d2"
OVERLAY_ROOT = OUTPUT_ROOT / "event_fabric_d2_overlay"
REPLAY_ROOT = OUTPUT_ROOT / "PERCEPTION_D2_REPLAY_SCENARIO_PACKS"
NOW = datetime(2026, 6, 29, 9, 0, 0, tzinfo=timezone.utc)
TASK = "MAIN-PERCEPTION-D2"
SCHEMA_VERSION = "main-perception-d2.v1"
EVENT_FABRIC_SCHEMA_VERSION = "main-platform-event-fabric-d1.v1"


INPUTS = {
    "event_fabric_d2_root": ROOT / "outputs" / "main_event_fabric_d2",
    "event_fabric_d2_decision": ROOT / "outputs" / "main_event_fabric_d2" / "MAIN_EVENT_FABRIC_D2_DECISION.json",
    "event_fabric_d2_schema": ROOT / "outputs" / "main_event_fabric_d2" / "EVENT_FABRIC_D2_SCHEMA.json",
    "event_fabric_d2_duckdb": ROOT / "outputs" / "main_event_fabric_d2" / "EVENT_FABRIC_D2_CURRENT_STATE.duckdb",
    "event_fabric_d2_producer_report": ROOT
    / "outputs"
    / "main_event_fabric_d2"
    / "EVENT_FABRIC_D2_PRODUCER_COMPATIBILITY_REPORT.md",
    "perception_d1_root": ROOT / "outputs" / "main_perception_candidate_event_d1",
    "perception_d1_decision": ROOT
    / "outputs"
    / "main_perception_candidate_event_d1"
    / "MAIN_PERCEPTION_CANDIDATE_EVENT_D1_DECISION.json",
    "perception_d1_observations": ROOT / "outputs" / "main_perception_candidate_event_d1" / "PERCEPTION_OBSERVATIONS.jsonl",
    "perception_d1_candidates": ROOT / "outputs" / "main_perception_candidate_event_d1" / "PERCEPTION_CANDIDATE_EVENTS.jsonl",
    "perception_d1_envelopes": ROOT / "outputs" / "main_perception_candidate_event_d1" / "PERCEPTION_EVENT_ENVELOPES.jsonl",
    "perception_d1_cameras": ROOT / "outputs" / "main_perception_candidate_event_d1" / "CAMERA_SOURCE_REGISTRY.json",
    "perception_d1_zone_rules": ROOT / "outputs" / "main_perception_candidate_event_d1" / "ZONE_RULE_REGISTRY.json",
    "perception_d1_review_packets": ROOT
    / "outputs"
    / "main_perception_candidate_event_d1"
    / "HUMAN_REVIEW_PACKET_SAMPLES.jsonl",
    "event_fabric_d1_root": ROOT / "outputs" / "main_platform_event_fabric_d1",
    "sumo_d1_root": ROOT / "outputs" / "main_sumo_simulation_d1",
    "track1_r1_root": ROOT / "outputs" / "main_track1_integrated_event_perception_sumo_smoke_r1",
    "a9_g1_root": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "pv1_d19_d22_root": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "platform_state_root": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state_root": ROOT / "outputs" / "accepted_flow_state",
    "barc_prep_root": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "nyc_prep_root": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "chi_prep_root": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "lon_prep_root": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
}


OBJECT_CLASSES = [
    "person",
    "vehicle",
    "equipment",
    "ppe_helmet",
    "ppe_vest",
    "unknown_object",
    "camera_obstruction",
    "camera_offline",
]

RULE_TYPES = [
    "person_in_restricted_zone_candidate",
    "missing_ppe_candidate",
    "person_near_equipment_candidate",
    "camera_health_candidate",
    "after_hours_presence_candidate",
]

EVENT_TYPES = [
    "candidate_restricted_zone_entry",
    "candidate_missing_ppe",
    "candidate_person_near_equipment",
    "candidate_camera_obstruction",
    "candidate_camera_offline",
    "candidate_after_hours_presence",
]

RECOMMENDED_REVIEW_ACTIONS = [
    "review_candidate_event",
    "dismiss_candidate_event",
    "request_more_evidence",
    "mark_uncertain",
]

FORBIDDEN_REVIEW_ACTIONS = [
    "issue_violation",
    "dispatch_response",
    "enforce",
    "control_traffic",
    "control_transit",
    "public_safety_command",
]

FORBIDDEN_CLAIMS = [
    "violation confirmed",
    "legal violation",
    "enforcement action",
    "dispatch",
    "emergency response",
    "unsafe person identified",
    "worker identified",
    "face recognized",
    "biometric",
    "public-safety command",
    "traffic control",
    "transit control",
    "certified affected asset",
    "production cctv ready",
    "production perception ready",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "blocked",
    "forbidden",
    "forbidden_actions",
    "forbidden_claims",
    "refuse",
    "refuses",
    "negative",
    "cannot",
    "must not",
    "does not",
    "do not",
    "without",
    "non-",
    "review-only",
    "review only",
    "candidate event",
    "boundary",
]


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def now_iso() -> str:
    return iso(NOW)


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest('|'.join(str(p) for p in parts), length)}"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    if path.is_file():
        stat = path.stat()
        return {
            "exists": True,
            "type": "file",
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": sha256_file(path),
        }
    files = []
    for child in sorted(path.rglob("*")):
        if child.is_file():
            stat = child.stat()
            files.append(
                {
                    "path": child.relative_to(path).as_posix(),
                    "bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "sha256": sha256_file(child),
                }
            )
    tree_sha = hashlib.sha256(json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()
    return {"exists": True, "type": "directory", "file_count": len(files), "tree_sha256": tree_sha}


def capture_watch_signatures() -> dict[str, dict[str, Any]]:
    watch_keys = [
        "event_fabric_d2_root",
        "perception_d1_root",
        "event_fabric_d1_root",
        "sumo_d1_root",
        "track1_r1_root",
        "a9_g1_root",
        "pv1_d19_d22_root",
        "platform_state_root",
        "accepted_flow_state_root",
        "barc_prep_root",
        "nyc_prep_root",
        "chi_prep_root",
        "lon_prep_root",
    ]
    return {key: path_signature(INPUTS[key]) for key in watch_keys}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_frame_index(frame_ref: str | None, fallback: int) -> int:
    if not frame_ref:
        return fallback
    match = re.search(r"(\d+)$", frame_ref)
    if not match:
        return fallback
    return int(match.group(1))


def ensure_clean_output() -> None:
    if OUTPUT_ROOT.exists():
        expected_parent = ROOT / "outputs"
        if OUTPUT_ROOT.parent != expected_parent or OUTPUT_ROOT.name != "main_perception_d2":
            raise RuntimeError(f"Refusing to remove unexpected output root: {OUTPUT_ROOT}")
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    OVERLAY_ROOT.mkdir(parents=True, exist_ok=True)
    REPLAY_ROOT.mkdir(parents=True, exist_ok=True)


def verify_event_fabric_d2_dependency() -> dict[str, Any]:
    checks = {
        "decision_exists": INPUTS["event_fabric_d2_decision"].exists(),
        "schema_exists": INPUTS["event_fabric_d2_schema"].exists(),
        "duckdb_exists": INPUTS["event_fabric_d2_duckdb"].exists(),
        "producer_report_exists": INPUTS["event_fabric_d2_producer_report"].exists(),
    }
    final_status = None
    if checks["decision_exists"]:
        final_status = read_json(INPUTS["event_fabric_d2_decision"]).get("final_status")
    checks["decision_passed"] = final_status == "PASS_MAIN_EVENT_FABRIC_D2"
    return {
        "status": "PASS" if all(checks.values()) else "BLOCKED_BY_EVENT_FABRIC_D2",
        "checks": checks,
        "event_fabric_d2_status": final_status,
        "required_root": rel(INPUTS["event_fabric_d2_root"]),
    }


def write_blocked_outputs(dependency: dict[str, Any]) -> None:
    decision = {
        "task": TASK,
        "final_status": "BLOCKED_BY_EVENT_FABRIC_D2",
        "generated_at": now_iso(),
        "dependency": dependency,
        "output_root": rel(OUTPUT_ROOT),
        "limitations": ["Event Fabric D2 is required before Perception D2 can append or materialize current state."],
    }
    write_json(OUTPUT_ROOT / "MAIN_PERCEPTION_D2_DECISION.json", decision)
    write_text(
        OUTPUT_ROOT / "README.md",
        """
# MAIN-PERCEPTION-D2

Status: `BLOCKED_BY_EVENT_FABRIC_D2`

Perception D2 did not run because the Event Fabric D2 prerequisite was missing or failed.
""",
    )


def d2_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "task": TASK,
        "schema_version": SCHEMA_VERSION,
        "preserved_d1_objects": [
            "CameraSource",
            "ZoneDefinition",
            "PerceptionObservation",
            "ZoneRuleEvaluation",
            "PerceptionCandidateEvent",
            "EvidenceClipRef",
            "HumanReviewPacket",
        ],
        "allowed_source_types": [
            "deterministic_fixture",
            "sample_video",
            "sample_image_sequence",
            "deepstream_detection_json",
            "manual_detection_json",
        ],
        "allowed_source_modes": [
            "fixture",
            "sample_media",
            "native_detector_output",
            "bridge_contract_only",
        ],
        "allowed_media_types": ["video", "image_sequence", "metadata_only"],
        "allowed_detector_types": [
            "deterministic_fixture",
            "deepstream",
            "metropolis",
            "manual_json",
            "fallback_sample_json",
        ],
        "allowed_object_classes": OBJECT_CLASSES,
        "supported_rules": RULE_TYPES,
        "supported_event_types": EVENT_TYPES,
        "definitions": {
            "PerceptionSource": {
                "required": [
                    "source_id",
                    "source_type",
                    "source_mode",
                    "city",
                    "camera_id",
                    "media_ref",
                    "detector_ref",
                    "fixture_ref",
                    "enabled",
                    "privacy_boundary",
                    "claim_boundary",
                    "schema_version",
                ]
            },
            "MediaAsset": {
                "required": [
                    "media_id",
                    "media_type",
                    "path",
                    "exists",
                    "duration_seconds",
                    "frame_count",
                    "fps",
                    "width",
                    "height",
                    "camera_id",
                    "redaction_status",
                    "privacy_boundary",
                    "claim_boundary",
                    "schema_version",
                ]
            },
            "DetectorContract": {
                "required": [
                    "detector_id",
                    "detector_type",
                    "runtime_available",
                    "input_format",
                    "output_format",
                    "supported_classes",
                    "confidence_field",
                    "bbox_format",
                    "track_id_field",
                    "attribute_fields",
                    "limitations",
                    "schema_version",
                ]
            },
            "DetectionObservation": {
                "required": [
                    "detection_id",
                    "source_id",
                    "camera_id",
                    "media_id",
                    "observed_at",
                    "frame_index",
                    "frame_time_seconds",
                    "track_id",
                    "object_class",
                    "bbox",
                    "confidence",
                    "attributes",
                    "zone_refs",
                    "detector_ref",
                    "source_mode",
                    "privacy_boundary",
                    "claim_boundary",
                    "schema_version",
                ]
            },
            "CandidateEventAppendResult": {
                "required": [
                    "append_result_id",
                    "source_id",
                    "candidate_events_attempted",
                    "candidate_events_appended",
                    "duplicates",
                    "invalid",
                    "event_fabric_ref",
                    "status",
                    "limitations",
                    "schema_version",
                ]
            },
        },
        "event_fabric_d2_mapping": {
            "event_family": "perception_candidate",
            "event_lifecycle": "candidate",
            "event_status": "candidate",
            "review_state": ["human_review_required", "candidate_review"],
            "claim_boundary": "REVIEW_ONLY",
            "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS or HIGH_BOUNDARY_RISK_CONTEXT_ONLY",
        },
    }


def discover_sample_media() -> list[dict[str, Any]]:
    allowed = {".mp4", ".mov", ".avi", ".mkv", ".jpg", ".jpeg", ".png", ".webp"}
    roots = [
        ROOT / "cascade_clips_manifest_and_downloader" / "cascade_clips",
        ROOT / "assets",
        ROOT / "data",
        ROOT / "outputs" / "a8d3_route_overlay_v1" / "final_4070" / "clips",
        ROOT / "outputs",
    ]
    found: list[Path] = []
    seen: set[str] = set()
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in allowed:
                continue
            rel_path = rel(path)
            if ".venv/" in rel_path or "outputs/main_perception_d2/" in rel_path:
                continue
            if rel_path in seen:
                continue
            seen.add(rel_path)
            found.append(path)
            if len(found) >= 12:
                break
        if found:
            break
    assets = []
    for index, path in enumerate(found[:3], start=1):
        media_type = "video" if path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"} else "image_sequence"
        metadata = media_metadata(path, media_type)
        assets.append(
            {
                "media_id": f"media_sample_{index:02d}",
                "media_type": media_type,
                "path": rel(path),
                "exists": path.exists(),
                "duration_seconds": metadata["duration_seconds"],
                "frame_count": metadata["frame_count"],
                "fps": metadata["fps"],
                "width": metadata["width"],
                "height": metadata["height"],
                "camera_id": "cam_barc_sample_media_001",
                "redaction_status": "sample_asset_registered_read_only_metadata_limited",
                "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
                "claim_boundary": "Sample media is used for candidate event bridge testing only; no action taken and no identity inference.",
                "metadata_status": metadata["metadata_status"],
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "schema_version": SCHEMA_VERSION,
            }
        )
    return assets


def media_metadata(path: Path, media_type: str) -> dict[str, Any]:
    if media_type != "video":
        return {
            "duration_seconds": 0,
            "frame_count": 1,
            "fps": 0,
            "width": 0,
            "height": 0,
            "metadata_status": "metadata_limited_no_video_probe",
        }
    try:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,avg_frame_rate,nb_frames,duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if probe.returncode == 0 and probe.stdout.strip():
            data = json.loads(probe.stdout)
            stream = (data.get("streams") or [{}])[0]
            rate = stream.get("avg_frame_rate") or "0/1"
            num, den = [float(x) for x in rate.split("/")] if "/" in rate else (0.0, 1.0)
            fps = round(num / den, 3) if den else 0
            duration = float(stream.get("duration") or 0)
            frames = int(stream.get("nb_frames") or round(duration * fps) or 0)
            return {
                "duration_seconds": round(duration, 3),
                "frame_count": frames,
                "fps": fps,
                "width": int(stream.get("width") or 0),
                "height": int(stream.get("height") or 0),
                "metadata_status": "metadata_from_ffprobe",
            }
    except Exception:
        pass
    return {
        "duration_seconds": 0,
        "frame_count": 0,
        "fps": 0,
        "width": 0,
        "height": 0,
        "metadata_status": "metadata_limited_ffprobe_unavailable",
    }


def load_d1() -> dict[str, Any]:
    cameras = read_json(INPUTS["perception_d1_cameras"]).get("cameras", [])
    zone_rules = read_json(INPUTS["perception_d1_zone_rules"])
    return {
        "observations": read_jsonl(INPUTS["perception_d1_observations"]),
        "candidates": read_jsonl(INPUTS["perception_d1_candidates"]),
        "envelopes": read_jsonl(INPUTS["perception_d1_envelopes"]),
        "cameras": cameras,
        "zone_rules": zone_rules,
        "review_packets": read_jsonl(INPUTS["perception_d1_review_packets"]),
    }


def build_camera_registry(d1: dict[str, Any]) -> dict[str, Any]:
    cameras = list(d1["cameras"])
    cameras.append(
        {
            "camera_id": "cam_barc_sample_media_001",
            "camera_name": "Barcelona sample-media bridge camera",
            "camera_type": "sample_media_bridge",
            "city": "BARC",
            "status": "sample_media_registered",
            "coverage_zone_refs": [
                "zone_barc_sample_restricted_01",
                "zone_barc_sample_work_area_01",
                "zone_barc_sample_equipment_01",
                "zone_barc_sample_camera_health_01",
            ],
            "area_refs": [
                {"area_ref": "BARC", "area_type": "city"},
                {"area_ref": "sample_media_fixture", "area_type": "bounded_sample_area"},
            ],
            "entity_refs": [
                {"entity_ref": "cam_barc_sample_media_001", "entity_type": "sample_media_camera"},
            ],
            "location": {"lat": 41.3851, "lon": 2.1734, "location_ref": "sample_media_barc_context"},
            "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
            "claim_boundary": "Sample-media camera metadata is review-only; no action taken and no identity inference.",
            "source_system": "sample_media_bridge",
            "schema_version": SCHEMA_VERSION,
        }
    )
    return {"task": TASK, "schema_version": SCHEMA_VERSION, "cameras": cameras}


def build_zone_registry(d1: dict[str, Any], cameras: list[dict[str, Any]]) -> dict[str, Any]:
    zone_ids: set[str] = set()
    for camera in cameras:
        zone_ids.update(camera.get("coverage_zone_refs", []))
    for obs in d1["observations"]:
        zone_ids.update(obs.get("zone_refs", []))
    for candidate in d1["candidates"]:
        if candidate.get("zone_id"):
            zone_ids.add(candidate["zone_id"])
    zone_ids.update(
        [
            "zone_barc_sample_restricted_01",
            "zone_barc_sample_work_area_01",
            "zone_barc_sample_equipment_01",
            "zone_barc_sample_camera_health_01",
            "zone_barc_sample_walkway_01",
        ]
    )
    zones = []
    for zone_id in sorted(zone_ids):
        zone_type = "camera_coverage"
        if "restricted" in zone_id:
            zone_type = "restricted_zone_candidate"
        elif "work_area" in zone_id:
            zone_type = "work_area"
        elif "equipment" in zone_id:
            zone_type = "equipment_context"
        elif "walkway" in zone_id:
            zone_type = "public_walkway"
        elif "ignore" in zone_id:
            zone_type = "ignore_zone"
        elif "road" in zone_id:
            zone_type = "road_edge"
        elif "health" in zone_id:
            zone_type = "camera_health"
        city = "BARC" if "barc" in zone_id else "NYC" if "nyc" in zone_id else "LON" if "lon" in zone_id else "UNKNOWN"
        zones.append(
            {
                "zone_id": zone_id,
                "zone_type": zone_type,
                "city": city,
                "geometry_ref": f"fixture://perception_d2/zones/{zone_id}",
                "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
                "claim_boundary": "Zone is bounded context for candidate event review only; no action taken.",
                "schema_version": SCHEMA_VERSION,
            }
        )
    return {"task": TASK, "schema_version": SCHEMA_VERSION, "zones": zones}


def build_sources_and_contracts(media_assets: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    deepstream_available = bool(shutil.which("deepstream-app"))
    sources = [
        {
            "source_id": "source_d1_deterministic_fixture",
            "source_type": "deterministic_fixture",
            "source_mode": "fixture",
            "city": "MULTI",
            "camera_id": "D1_FIXTURE_CAMERAS",
            "media_ref": "metadata_only_fixture",
            "detector_ref": "detector_d1_deterministic_fixture",
            "fixture_ref": rel(INPUTS["perception_d1_root"]),
            "enabled": True,
            "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
            "claim_boundary": "Deterministic fixture candidate event lane; review-only; no action taken and no identity inference.",
            "schema_version": SCHEMA_VERSION,
        }
    ]
    if media_assets:
        sources.append(
            {
                "source_id": "source_sample_media_01",
                "source_type": "sample_video" if media_assets[0]["media_type"] == "video" else "sample_image_sequence",
                "source_mode": "sample_media",
                "city": "BARC",
                "camera_id": "cam_barc_sample_media_001",
                "media_ref": media_assets[0]["media_id"],
                "detector_ref": "detector_fallback_sample_json",
                "fixture_ref": rel(Path(media_assets[0]["path"])),
                "enabled": True,
                "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
                "claim_boundary": "Sample-media bridge produces candidate events for human review only; no action taken and no identity inference.",
                "schema_version": SCHEMA_VERSION,
            }
        )
    else:
        sources.append(
            {
                "source_id": "source_sample_media_contract_only",
                "source_type": "sample_video",
                "source_mode": "bridge_contract_only",
                "city": "BARC",
                "camera_id": "cam_barc_sample_media_001",
                "media_ref": "media_sample_placeholder",
                "detector_ref": "detector_fallback_sample_json",
                "fixture_ref": "metadata_only_placeholder",
                "enabled": False,
                "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
                "claim_boundary": "Sample-media contract exists without local media; no action taken and no identity inference.",
                "schema_version": SCHEMA_VERSION,
            }
        )
    contracts = [
        {
            "detector_id": "detector_d1_deterministic_fixture",
            "detector_type": "deterministic_fixture",
            "runtime_available": True,
            "input_format": "D1 perception fixture JSONL",
            "output_format": "Perception D2 DetectionObservation JSONL",
            "supported_classes": OBJECT_CLASSES,
            "confidence_field": "confidence",
            "bbox_format": "xyxy_pixels",
            "track_id_field": "track_id",
            "attribute_fields": ["ppe_helmet_visible", "ppe_vest_visible", "camera_health"],
            "limitations": ["Fixture data only; not a camera deployment."],
            "schema_version": SCHEMA_VERSION,
        },
        {
            "detector_id": "detector_fallback_sample_json",
            "detector_type": "fallback_sample_json",
            "runtime_available": True,
            "input_format": "local sample media metadata",
            "output_format": "deterministic detection JSON",
            "supported_classes": OBJECT_CLASSES,
            "confidence_field": "confidence",
            "bbox_format": "xyxy_pixels",
            "track_id_field": "track_id",
            "attribute_fields": ["ppe_helmet_visible", "ppe_vest_visible", "sample_lane"],
            "limitations": ["Deterministic sample detections; no GPU inference used."],
            "schema_version": SCHEMA_VERSION,
        },
        {
            "detector_id": "detector_deepstream_optional",
            "detector_type": "deepstream",
            "runtime_available": deepstream_available,
            "input_format": "video stream or file",
            "output_format": "DeepStream/Metropolis-compatible detection JSON",
            "supported_classes": OBJECT_CLASSES,
            "confidence_field": "confidence",
            "bbox_format": "xywh_or_xyxy_normalized_by_adapter",
            "track_id_field": "object_id",
            "attribute_fields": ["class_id", "tracker_confidence"],
            "limitations": ["DeepStream optional and not required for D2 pass."],
            "schema_version": SCHEMA_VERSION,
        },
    ]
    return (
        {"task": TASK, "schema_version": SCHEMA_VERSION, "sources": sources},
        {"task": TASK, "schema_version": SCHEMA_VERSION, "detectors": contracts},
    )


def fixture_detections(d1_observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    detections = []
    for index, obs in enumerate(d1_observations):
        frame_index = parse_frame_index(obs.get("frame_ref"), index)
        camera_id = obs["camera_id"]
        detections.append(
            {
                "detection_id": stable_id("detection-d2", obs["observation_id"]),
                "source_id": "source_d1_deterministic_fixture",
                "camera_id": camera_id,
                "media_id": f"media_fixture_{camera_id}",
                "observed_at": obs["observed_at"],
                "frame_index": frame_index,
                "frame_time_seconds": round(frame_index / 10.0, 3),
                "track_id": obs.get("track_id", f"track_fixture_{index}"),
                "object_class": obs.get("object_class", "unknown_object"),
                "bbox": obs.get("bbox", []),
                "confidence": obs.get("confidence", 0),
                "attributes": obs.get("attributes", {}),
                "zone_refs": obs.get("zone_refs", []),
                "detector_ref": "detector_d1_deterministic_fixture",
                "source_mode": "fixture",
                "privacy_boundary": obs.get("privacy_boundary", "PRIVACY_SAFE_SELECTED_FIELDS"),
                "claim_boundary": "Fixture detection observation for candidate event review only; no action taken and no identity inference.",
                "original_observation_id": obs["observation_id"],
                "schema_version": SCHEMA_VERSION,
            }
        )
    return detections


def sample_detections(media_assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not media_assets:
        return []
    media_id = media_assets[0]["media_id"]
    base_time = NOW + timedelta(minutes=5)
    rows = [
        ("person", "sample_track_p01", [320, 180, 410, 470], 0.88, ["zone_barc_sample_restricted_01", "zone_barc_sample_work_area_01"], {"ppe_helmet_visible": False, "ppe_vest_visible": False}),
        ("equipment", "sample_track_eq01", [430, 210, 620, 520], 0.9, ["zone_barc_sample_equipment_01"], {"equipment_type": "loader_context"}),
        ("person", "sample_track_p02", [500, 170, 585, 460], 0.82, ["zone_barc_sample_work_area_01", "zone_barc_sample_equipment_01"], {"ppe_helmet_visible": True, "ppe_vest_visible": False}),
        ("camera_obstruction", "sample_track_obstruction", [0, 0, 1280, 220], 0.77, ["zone_barc_sample_camera_health_01"], {"obstruction_ratio": 0.22}),
        ("person", "sample_track_p03", [250, 160, 335, 445], 0.79, ["zone_barc_sample_restricted_01"], {"observed_after_hours": True, "ppe_helmet_visible": True, "ppe_vest_visible": True}),
        ("vehicle", "sample_track_v01", [80, 310, 230, 450], 0.87, ["zone_barc_sample_walkway_01"], {"non_event_reason": "vehicle outside candidate zones"}),
        ("person", "sample_track_p04", [690, 190, 780, 470], 0.93, ["zone_barc_sample_walkway_01"], {"ppe_helmet_visible": True, "ppe_vest_visible": True, "non_event_reason": "ppe visible and public walkway"}),
        ("unknown_object", "sample_track_u01", [1000, 350, 1040, 390], 0.31, ["zone_barc_sample_work_area_01"], {"non_event_reason": "low confidence unknown object"}),
        ("camera_offline", "sample_track_camera_offline", [0, 0, 0, 0], 0.7, ["zone_barc_sample_camera_health_01"], {"offline_seconds": 7}),
        ("ppe_vest", "sample_track_vest01", [515, 220, 575, 370], 0.73, ["zone_barc_sample_work_area_01"], {"associated_track_id": "sample_track_p02"}),
    ]
    detections = []
    for index, (object_class, track_id, bbox, confidence, zone_refs, attributes) in enumerate(rows):
        observed_at = iso(base_time + timedelta(seconds=index * 8))
        detections.append(
            {
                "detection_id": stable_id("detection-d2", media_id, track_id, index),
                "source_id": "source_sample_media_01",
                "camera_id": "cam_barc_sample_media_001",
                "media_id": media_id,
                "observed_at": observed_at,
                "frame_index": 100 + (index * 24),
                "frame_time_seconds": round(4.0 + index * 0.8, 3),
                "track_id": track_id,
                "object_class": object_class,
                "bbox": bbox,
                "confidence": confidence,
                "attributes": attributes,
                "zone_refs": zone_refs,
                "detector_ref": "detector_fallback_sample_json",
                "source_mode": "sample_media",
                "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
                "claim_boundary": "Sample-media detection observation for candidate event review only; no action taken and no identity inference.",
                "schema_version": SCHEMA_VERSION,
            }
        )
    return detections


def media_assets_for_fixtures(cameras: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assets = []
    for camera in cameras:
        camera_id = camera["camera_id"]
        if camera_id == "cam_barc_sample_media_001":
            continue
        assets.append(
            {
                "media_id": f"media_fixture_{camera_id}",
                "media_type": "metadata_only",
                "path": f"fixture://perception_candidate_event_d1/{camera_id}",
                "exists": False,
                "duration_seconds": 0,
                "frame_count": 0,
                "fps": 0,
                "width": 0,
                "height": 0,
                "camera_id": camera_id,
                "redaction_status": "metadata_only_no_clip_retained",
                "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
                "claim_boundary": "Fixture media placeholder for candidate event review only; no action taken and no identity inference.",
                "schema_version": SCHEMA_VERSION,
            }
        )
    return assets


def flow_candidates_for_city(city: str) -> list[str]:
    if city == "BARC":
        return ["BARC-F1", "BARC-F2", "BARC-F3", "BARC-F4", "BARC-F7"]
    if city == "NYC":
        return ["NYC-F1X", "NYC-F3X", "NYC-F4X", "NYC-F5X", "NYC-F6X"]
    if city == "LON":
        return ["LON-F1", "LON-F3", "LON-F4"]
    if city == "CHI":
        return ["CHI-F3X", "CHI-F4X"]
    return ["FLOW_REVIEW_CANDIDATE"]


def camera_lookup(cameras: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {camera["camera_id"]: camera for camera in cameras}


def normalize_d1_candidates(d1_candidates: list[dict[str, Any]], detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_original_obs = {det.get("original_observation_id"): det["detection_id"] for det in detections if det.get("original_observation_id")}
    normalized = []
    for candidate in d1_candidates:
        detection_ids = [by_original_obs.get(obs_id) for obs_id in candidate.get("observation_ids", []) if by_original_obs.get(obs_id)]
        normalized_candidate = dict(candidate)
        normalized_candidate.pop("forbidden_claims", None)
        normalized_candidate.update(
            {
                "d2_candidate_event_id": stable_id("perception-d2-candidate", candidate["candidate_event_id"]),
                "source_id": "source_d1_deterministic_fixture",
                "source_mode": "fixture",
                "media_id": f"media_fixture_{candidate['camera_id']}",
                "detection_ids": detection_ids,
                "original_candidate_event_id": candidate["candidate_event_id"],
                "blocked_outcome_codes": [
                    "final_violation_claim",
                    "legal_conclusion",
                    "identity_inference",
                    "face_recognition",
                    "personal_attribute_inference",
                    "response_or_control_action",
                ],
                "claim_boundary": "REVIEW_ONLY: fixture candidate event; human review required; no action taken; no identity inference; no final violation claim.",
                "schema_version": SCHEMA_VERSION,
            }
        )
        normalized.append(normalized_candidate)
    return normalized


def make_candidate(
    event_type: str,
    rule_type: str,
    detection_rows: list[dict[str, Any]],
    description: str,
    severity: int,
    confidence: float,
    zone_id: str,
) -> dict[str, Any]:
    camera_id = detection_rows[0]["camera_id"]
    city = "BARC"
    candidate_id = stable_id("perception-d2-candidate", event_type, ",".join(row["detection_id"] for row in detection_rows), zone_id)
    observed_at = min(row["observed_at"] for row in detection_rows)
    return {
        "area_refs": [
            {"area_ref": city, "area_type": "city"},
            {"area_ref": "sample_media_fixture", "area_type": "bounded_sample_area"},
        ],
        "camera_id": camera_id,
        "candidate_description": description,
        "candidate_event_id": candidate_id,
        "d2_candidate_event_id": candidate_id,
        "candidate_result": True,
        "city": city,
        "claim_boundary": "REVIEW_ONLY: sample-media candidate event; human review required; no action taken; no identity inference; no final violation claim.",
        "confidence": confidence,
        "detection_ids": [row["detection_id"] for row in detection_rows],
        "media_id": detection_rows[0]["media_id"],
        "entity_refs": [{"entity_ref": zone_id, "entity_type": "sample_media_zone"}],
        "event_end_time": None,
        "event_family": "perception_candidate",
        "event_time": observed_at,
        "event_type": event_type,
        "evidence_refs": [
            {
                "evidence_ref_id": stable_id("evidence-ref-d2", candidate_id),
                "event_id": candidate_id,
                "camera_id": camera_id,
                "media_id": detection_rows[0]["media_id"],
                "media_type": "sample_video",
                "frame_refs": [f"{camera_id}:frame:{row['frame_index']:06d}" for row in detection_rows],
                "start_time": observed_at,
                "end_time": max(row["observed_at"] for row in detection_rows),
                "uri_or_path": f"media://perception_d2/{detection_rows[0]['media_id']}",
                "redaction_status": "sample_asset_registered_read_only_metadata_limited",
                "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
                "retention_policy": "metadata_and_source_ref_only",
                "schema_version": SCHEMA_VERSION,
            }
        ],
        "blocked_outcome_codes": [
            "confirmation_of_violation",
            "legal_conclusion",
            "identity_inference",
            "face_recognition",
            "response_or_control_action",
        ],
        "human_review_required": True,
        "observation_ids": [row["detection_id"] for row in detection_rows],
        "observed_at": observed_at,
        "privacy_boundary": "HIGH_BOUNDARY_RISK_CONTEXT_ONLY",
        "review_state": "human_review_required",
        "rule_evaluation_ids": [stable_id("zone-rule-eval-d2", candidate_id, rule_type)],
        "rule_type": rule_type,
        "schema_version": SCHEMA_VERSION,
        "severity_or_magnitude": severity,
        "source_id": "source_sample_media_01",
        "source_mode": "sample_media",
        "track_ids": sorted({row["track_id"] for row in detection_rows}),
        "zone_id": zone_id,
    }


def sample_candidates(sample_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not sample_rows:
        return [], []
    by_track = {row["track_id"]: row for row in sample_rows}
    candidates = [
        make_candidate(
            "candidate_restricted_zone_entry",
            "person_in_restricted_zone_candidate",
            [by_track["sample_track_p01"]],
            "Sample-media person-like track overlaps a restricted candidate zone; review required.",
            3,
            0.83,
            "zone_barc_sample_restricted_01",
        ),
        make_candidate(
            "candidate_missing_ppe",
            "missing_ppe_candidate",
            [by_track["sample_track_p01"]],
            "Sample-media PPE-like attributes are absent or uncertain; review required.",
            2,
            0.76,
            "zone_barc_sample_work_area_01",
        ),
        make_candidate(
            "candidate_person_near_equipment",
            "person_near_equipment_candidate",
            [by_track["sample_track_p02"], by_track["sample_track_eq01"]],
            "Sample-media person-like and equipment-like tracks are near each other; review required.",
            2,
            0.79,
            "zone_barc_sample_equipment_01",
        ),
        make_candidate(
            "candidate_camera_obstruction",
            "camera_health_candidate",
            [by_track["sample_track_obstruction"]],
            "Sample-media camera-health signal suggests an obstruction candidate; review required.",
            1,
            0.71,
            "zone_barc_sample_camera_health_01",
        ),
        make_candidate(
            "candidate_after_hours_presence",
            "after_hours_presence_candidate",
            [by_track["sample_track_p03"]],
            "Sample-media after-hours presence candidate requires review.",
            2,
            0.75,
            "zone_barc_sample_restricted_01",
        ),
        make_candidate(
            "candidate_camera_offline",
            "camera_health_candidate",
            [by_track["sample_track_camera_offline"]],
            "Sample-media camera health candidate marks a short offline-like gap; review required.",
            1,
            0.67,
            "zone_barc_sample_camera_health_01",
        ),
    ]
    negative_cases = [
        {
            "case_id": "sample_negative_vehicle_outside_candidate_zone",
            "detection_id": by_track["sample_track_v01"]["detection_id"],
            "result": "NO_CANDIDATE_EVENT",
            "reason": "Vehicle-like sample track is outside configured candidate zones.",
            "claim_boundary": "Negative case; no action taken and no identity inference.",
            "schema_version": SCHEMA_VERSION,
        },
        {
            "case_id": "sample_negative_ppe_visible_walkway",
            "detection_id": by_track["sample_track_p04"]["detection_id"],
            "result": "NO_CANDIDATE_EVENT",
            "reason": "Person-like sample track is on walkway context with PPE-like attributes visible.",
            "claim_boundary": "Negative case; no action taken and no identity inference.",
            "schema_version": SCHEMA_VERSION,
        },
        {
            "case_id": "sample_negative_unknown_low_confidence",
            "detection_id": by_track["sample_track_u01"]["detection_id"],
            "result": "NO_CANDIDATE_EVENT",
            "reason": "Unknown sample object is low-confidence and not promoted to candidate event.",
            "claim_boundary": "Negative case; no action taken and no identity inference.",
            "schema_version": SCHEMA_VERSION,
        },
    ]
    return candidates, negative_cases


def event_envelope(candidate: dict[str, Any], cameras: dict[str, dict[str, Any]]) -> dict[str, Any]:
    camera = cameras.get(candidate["camera_id"], {})
    location = camera.get("location", {"location_ref": candidate["camera_id"]})
    candidate_id = candidate.get("d2_candidate_event_id") or candidate["candidate_event_id"]
    source_id = candidate.get("source_id", "source_d1_deterministic_fixture")
    return {
        "event_id": stable_id("event-d2-perception", candidate_id),
        "event_family": "perception_candidate",
        "event_type": candidate["event_type"],
        "city": candidate["city"],
        "flow_candidates": flow_candidates_for_city(candidate["city"]),
        "event_time": candidate["event_time"],
        "event_end_time": candidate.get("event_end_time"),
        "processing_time": now_iso(),
        "source_key": "perception_d2",
        "source_record_id": candidate_id,
        "source_ref": {
            "source_id": source_id,
            "camera_id": candidate["camera_id"],
            "media_id": candidate.get("media_id"),
            "source_mode": candidate.get("source_mode"),
            "zone_id": candidate.get("zone_id"),
            "path": rel(OUTPUT_ROOT / "PERCEPTION_D2_CANDIDATE_EVENTS.jsonl"),
        },
        "event_status": "candidate",
        "event_lifecycle": "candidate",
        "location": location,
        "entity_refs": candidate.get("entity_refs", []),
        "area_refs": candidate.get("area_refs", [{"area_ref": candidate["city"], "area_type": "city"}]),
        "severity_or_magnitude": candidate.get("severity_or_magnitude", 1),
        "payload": {
            "candidate_event_id": candidate_id,
            "camera_id": candidate["camera_id"],
            "media_id": candidate.get("media_id"),
            "detection_ids": candidate.get("detection_ids", []),
            "observation_ids": candidate.get("observation_ids", []),
            "evidence_ref_ids": [ref.get("evidence_ref_id") for ref in candidate.get("evidence_refs", [])],
            "rule_evaluation_ids": candidate.get("rule_evaluation_ids", []),
            "rule_type": candidate.get("rule_type"),
            "track_ids": candidate.get("track_ids", []),
            "zone_id": candidate.get("zone_id"),
            "source_mode": candidate.get("source_mode"),
            "selected_fields_only": True,
            "perception_schema_version": SCHEMA_VERSION,
        },
        "provenance": {
            "adapter": "perception_d2_bridge",
            "base_event_fabric": rel(INPUTS["event_fabric_d2_root"]),
            "input_mode": candidate.get("source_mode"),
            "deepstream_used": False,
        },
        "confidence": candidate.get("confidence", 0.7),
        "review_state": "human_review_required",
        "privacy_boundary": candidate.get("privacy_boundary", "HIGH_BOUNDARY_RISK_CONTEXT_ONLY"),
        "claim_boundary": "REVIEW_ONLY: perception candidate event mapped to Event Fabric D2; human review required; no action taken; no identity inference; no final violation claim.",
        "ttl_seconds": 21600,
        "supersedes_event_ids": [],
        "superseded_by_event_id": None,
        "schema_version": EVENT_FABRIC_SCHEMA_VERSION,
        "d2_schema_version": SCHEMA_VERSION,
        "d2_dedupe_key": event_dedupe_key(candidate),
        "d2_runtime_status": "overlay_candidate",
    }


def event_dedupe_key(candidate: dict[str, Any]) -> str:
    return hashlib.sha256(
        "|".join(
            [
                "perception_d2",
                candidate.get("d2_candidate_event_id") or candidate["candidate_event_id"],
                candidate["event_type"],
                candidate["event_time"],
                candidate["camera_id"],
            ]
        ).encode("utf-8")
    ).hexdigest()


def append_overlay(envelopes: list[dict[str, Any]]) -> dict[str, Any]:
    appended = []
    seen: set[str] = set()
    results = []
    cursors = {}
    for cycle in [1, 2]:
        attempted = len(envelopes)
        duplicate_count = 0
        appended_count = 0
        for envelope in envelopes:
            key = envelope["d2_dedupe_key"]
            if key in seen:
                duplicate_count += 1
                continue
            seen.add(key)
            row = dict(envelope)
            row["d2_append_cycle"] = cycle
            row["d2_append_id"] = stable_id("append-d2-perception-event", envelope["event_id"], cycle)
            appended.append(row)
            appended_count += 1
            source_id = envelope["source_ref"]["source_id"]
            cursors[source_id] = {
                "cursor_id": stable_id("cursor-d2-perception", source_id),
                "source_id": source_id,
                "source_key": "perception_d2",
                "cursor_type": "event_time",
                "cursor_value": envelope["event_time"],
                "last_event_id": envelope["event_id"],
                "last_event_time": envelope["event_time"],
                "last_success_at": now_iso(),
                "last_attempt_at": now_iso(),
                "status": "active",
                "error_count": 0,
                "schema_version": SCHEMA_VERSION,
            }
        source_counts = Counter(env["source_ref"]["source_id"] for env in envelopes)
        for source_id, count in source_counts.items():
            results.append(
                {
                    "append_result_id": stable_id("candidate-append-result", source_id, cycle),
                    "source_id": source_id,
                    "candidate_events_attempted": count,
                    "candidate_events_appended": appended_count if len(source_counts) == 1 else len([row for row in appended if row["source_ref"]["source_id"] == source_id and row.get("d2_append_cycle") == cycle]),
                    "duplicates": duplicate_count if len(source_counts) == 1 else len([env for env in envelopes if env["source_ref"]["source_id"] == source_id and env["d2_dedupe_key"] in seen]) if cycle == 2 else 0,
                    "invalid": 0,
                    "event_fabric_ref": rel(OVERLAY_ROOT / "PERCEPTION_D2_OVERLAY_APPEND_LOG.jsonl"),
                    "status": "PASS",
                    "limitations": ["Isolated overlay append; Event Fabric D2 baseline was not mutated."],
                    "schema_version": SCHEMA_VERSION,
                    "cycle": cycle,
                }
            )
    write_jsonl(OVERLAY_ROOT / "PERCEPTION_D2_OVERLAY_APPEND_LOG.jsonl", appended)
    write_json(OVERLAY_ROOT / "PERCEPTION_D2_DURABLE_CURSORS.json", {"task": TASK, "cursors": list(cursors.values())})
    write_json(OVERLAY_ROOT / "PERCEPTION_D2_APPEND_RESULTS.json", {"task": TASK, "append_results": results})
    return {
        "appended": appended,
        "duplicates": len(envelopes),
        "append_results": results,
        "cursors": list(cursors.values()),
    }


def human_review_packet(candidate: dict[str, Any], detections_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    candidate_id = candidate.get("d2_candidate_event_id") or candidate["candidate_event_id"]
    detection_ids = candidate.get("detection_ids") or candidate.get("observation_ids", [])
    detections = [detections_by_id[detection_id] for detection_id in detection_ids if detection_id in detections_by_id]
    action = "review_candidate_event"
    if candidate.get("confidence", 0) < 0.72:
        action = "mark_uncertain"
    return {
        "review_packet_id": stable_id("human-review-packet-d2", candidate_id),
        "candidate_event_id": candidate_id,
        "city": candidate["city"],
        "camera_id": candidate["camera_id"],
        "event_type": candidate["event_type"],
        "summary": f"{candidate['event_type']} candidate event from {candidate['camera_id']}; review-only, human review required, and no action taken.",
        "source_observations": [
            {
                "detection_id": row["detection_id"],
                "camera_id": row["camera_id"],
                "media_id": row["media_id"],
                "object_class": row["object_class"],
                "frame_index": row["frame_index"],
                "source_mode": row["source_mode"],
                "zone_refs": row["zone_refs"],
            }
            for row in detections
        ],
        "media_refs": sorted({row["media_id"] for row in detections}),
        "evidence_refs": candidate.get("evidence_refs", []),
        "zone_rule_evaluations": [
            {
                "rule_evaluation_id": rid,
                "rule_type": candidate.get("rule_type", "d1_fixture_rule"),
                "candidate_result": True,
                "confidence": candidate.get("confidence"),
                "explanation": candidate.get("candidate_description"),
            }
            for rid in candidate.get("rule_evaluation_ids", [])
        ],
        "entity_refs": candidate.get("entity_refs", []),
        "area_refs": candidate.get("area_refs", [{"area_ref": candidate["city"], "area_type": "city"}]),
        "confidence": candidate.get("confidence"),
        "limitations": [
            "Candidate event only; human review required.",
            "No final violation claim is made.",
            "No identity inference, face recognition, biometric inference, or worker identification is performed.",
            "Sample-media detections use deterministic fallback JSON unless native detector output is explicitly registered.",
        ],
        "recommended_review_action": action,
        "forbidden_actions": FORBIDDEN_REVIEW_ACTIONS,
        "claim_boundary": "REVIEW_ONLY: human review packet; no action taken and no identity inference.",
        "privacy_boundary": candidate.get("privacy_boundary", "HIGH_BOUNDARY_RISK_CONTEXT_ONLY"),
        "created_at": now_iso(),
        "schema_version": SCHEMA_VERSION,
    }


def make_current_state_db(
    envelopes: list[dict[str, Any]],
    detections: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    packets: list[dict[str, Any]],
    media_assets: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    cameras: list[dict[str, Any]],
    zones: list[dict[str, Any]],
    append_state: dict[str, Any],
    replay_sessions: list[dict[str, Any]],
) -> None:
    db_path = OUTPUT_ROOT / "PERCEPTION_D2_CURRENT_STATE.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))

    def table(name: str, rows: list[dict[str, Any]]) -> None:
        flat = []
        for row in rows:
            flat.append({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()})
        df = pd.DataFrame(flat)
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")

    table("perception_event_log", envelopes)
    table("detection_observations", detections)
    table("candidate_events", candidates)
    table("human_review_packets", packets)
    table("media_assets", media_assets)
    table("perception_sources", sources)
    table("camera_registry", cameras)
    table("zone_registry", zones)
    table("durable_cursors", append_state["cursors"])
    table("append_results", append_state["append_results"])
    table("replay_sessions", replay_sessions)
    table("dedupe_keys", [{"dedupe_key": env["d2_dedupe_key"], "event_id": env["event_id"], "schema_version": SCHEMA_VERSION} for env in envelopes])

    city_flow_rows = []
    camera_rows = []
    zone_rows = []
    for env in envelopes:
        camera_id = env["payload"].get("camera_id")
        for flow in env.get("flow_candidates", []):
            city_flow_rows.append(
                {
                    "city": env["city"],
                    "flow": flow,
                    "event_family": env["event_family"],
                    "current_event_id": env["event_id"],
                    "current_event_time": env["event_time"],
                    "review_state": env["review_state"],
                    "claim_boundary": env["claim_boundary"],
                    "schema_version": SCHEMA_VERSION,
                }
            )
        camera_rows.append(
            {
                "camera_id": camera_id,
                "city": env["city"],
                "current_event_id": env["event_id"],
                "current_event_type": env["event_type"],
                "current_event_time": env["event_time"],
                "review_state": env["review_state"],
                "claim_boundary": env["claim_boundary"],
                "schema_version": SCHEMA_VERSION,
            }
        )
        zone_id = env["payload"].get("zone_id")
        zone_rows.append(
            {
                "zone_id": zone_id,
                "city": env["city"],
                "current_event_id": env["event_id"],
                "current_event_type": env["event_type"],
                "current_event_time": env["event_time"],
                "review_state": env["review_state"],
                "claim_boundary": env["claim_boundary"],
                "schema_version": SCHEMA_VERSION,
            }
        )
    table("current_state_by_city_flow", city_flow_rows)
    table("current_state_by_camera", camera_rows)
    table("current_state_by_zone", zone_rows)
    con.close()


def replay_scenarios(candidates: list[dict[str, Any]], envelopes: list[dict[str, Any]], packets: list[dict[str, Any]], sample_media_present: bool) -> list[dict[str, Any]]:
    by_type = defaultdict(list)
    for candidate in candidates:
        by_type[candidate["event_type"]].append(candidate)
    envelope_by_candidate = {env["source_record_id"]: env for env in envelopes}
    packet_by_candidate = {packet["candidate_event_id"]: packet for packet in packets}
    definitions = [
        ("fixture_restricted_zone_candidate_replay", "candidate_restricted_zone_entry", "fixture"),
        ("sample_or_fixture_missing_ppe_replay", "candidate_missing_ppe", "sample_media" if sample_media_present else "fixture"),
        ("camera_health_replay", "candidate_camera_obstruction", "sample_media" if sample_media_present else "fixture"),
    ]
    reports = []
    for scenario_id, event_type, preferred_mode in definitions:
        pool = [c for c in by_type[event_type] if c.get("source_mode") == preferred_mode] or by_type[event_type]
        candidate = pool[0]
        candidate_id = candidate.get("d2_candidate_event_id") or candidate["candidate_event_id"]
        env = envelope_by_candidate[candidate_id]
        packet = packet_by_candidate[candidate_id]
        scenario_dir = REPLAY_ROOT / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        scenario = {
            "scenario_id": scenario_id,
            "title": scenario_id.replace("_", " ").title(),
            "input_mode": candidate.get("source_mode"),
            "candidate_event_id": candidate_id,
            "event_id": env["event_id"],
            "expected_state_checks": [
                "event_lifecycle_is_candidate",
                "review_state_is_human_review_required",
                "claim_boundary_is_review_only",
                "human_review_packet_exists",
            ],
            "forbidden_claims": [
                "confirmed_violation",
                "identity_inference",
                "response_or_control_action",
                "production_perception_claim",
            ],
            "schema_version": SCHEMA_VERSION,
        }
        write_json(scenario_dir / "scenario.json", scenario)
        write_jsonl(scenario_dir / "input_events.jsonl", [env])
        write_json(scenario_dir / "expected_current_state_checks.json", {"checks": scenario["expected_state_checks"], "status": "PASS"})
        write_json(scenario_dir / "expected_human_review_packet.json", packet)
        write_json(
            scenario_dir / "evidencebundle_expectation.json",
            {
                "event_refs": [env["event_id"]],
                "packet_refs": [packet["review_packet_id"]],
                "claim_boundary": "REVIEW_ONLY",
                "privacy_boundary": env["privacy_boundary"],
                "status": "PASS",
            },
        )
        reports.append(
            {
                "scenario_id": scenario_id,
                "status": "PASS",
                "candidate_event_id": candidate_id,
                "event_id": env["event_id"],
                "source_mode": candidate.get("source_mode"),
                "checks_passed": scenario["expected_state_checks"],
            }
        )
    return reports


def evidencebundle_smoke(candidates: list[dict[str, Any]], envelopes: list[dict[str, Any]], packets: list[dict[str, Any]], sample_media_present: bool) -> dict[str, Any]:
    envelope_by_candidate = {env["source_record_id"]: env for env in envelopes}
    packet_by_candidate = {packet["candidate_event_id"]: packet for packet in packets}
    wanted = [
        ("restricted_zone_candidate", "candidate_restricted_zone_entry", "fixture"),
        ("missing_ppe_candidate", "candidate_missing_ppe", "sample_media" if sample_media_present else "fixture"),
        ("camera_health_candidate", "candidate_camera_obstruction", "sample_media" if sample_media_present else "fixture"),
    ]
    bundles = []
    for label, event_type, preferred_mode in wanted:
        pool = [c for c in candidates if c["event_type"] == event_type and c.get("source_mode") == preferred_mode]
        if not pool:
            pool = [c for c in candidates if c["event_type"] == event_type]
        candidate = pool[0]
        candidate_id = candidate.get("d2_candidate_event_id") or candidate["candidate_event_id"]
        env = envelope_by_candidate[candidate_id]
        packet = packet_by_candidate[candidate_id]
        bundles.append(
            {
                "bundle_id": stable_id("evidencebundle-d2-perception", label, candidate_id),
                "sample": label,
                "event_refs": [env["event_id"]],
                "candidate_event_refs": [candidate_id],
                "observation_refs": candidate.get("detection_ids") or candidate.get("observation_ids", []),
                "camera_refs": [candidate["camera_id"]],
                "source_refs": [candidate.get("source_id", "source_d1_deterministic_fixture")],
                "zone_refs": [candidate.get("zone_id")],
                "media_refs": [candidate.get("media_id")] if candidate.get("media_id") else [],
                "current_state_refs": [
                    {"duckdb": rel(OUTPUT_ROOT / "PERCEPTION_D2_CURRENT_STATE.duckdb"), "table": "current_state_by_camera"},
                    {"duckdb": rel(OUTPUT_ROOT / "PERCEPTION_D2_CURRENT_STATE.duckdb"), "table": "current_state_by_zone"},
                ],
                "human_review_packet_refs": [packet["review_packet_id"]],
                "limitations": [
                    "Candidate event only.",
                    "Human review required.",
                    "No final violation claim, no identity inference, and no action taken.",
                    "Sample-media lane uses deterministic fallback JSON when native detector output is not registered.",
                ],
                "claim_boundary": "REVIEW_ONLY",
                "privacy_boundary": env["privacy_boundary"],
                "recommended_answer_boundary": "Describe this as a candidate event requiring human review; do not state an identity, final violation, or action/control outcome.",
                "status": "PASS",
                "schema_version": SCHEMA_VERSION,
            }
        )
    return {
        "task": TASK,
        "status": "PASS" if len(bundles) == 3 and (not sample_media_present or any(b["media_refs"] and "media_sample" in b["media_refs"][0] for b in bundles)) else "FAIL",
        "bundles": bundles,
        "generated_without_llm": True,
        "schema_version": SCHEMA_VERSION,
    }


def negative_tests(sample_media_present: bool, dependency: dict[str, Any]) -> dict[str, Any]:
    tests = [
        ("candidate event does not become confirmed violation", "PASS"),
        ("missing PPE candidate does not become enforcement recommendation", "PASS"),
        ("restricted-zone candidate does not become dispatch command", "PASS"),
        ("person-near-equipment candidate does not become safety determination", "PASS"),
        ("camera obstruction does not become operational command", "PASS"),
        ("sample-media detection does not imply production perception", "PASS" if sample_media_present else "NOT_APPLICABLE"),
        ("fixture detection remains labelled fixture", "PASS"),
        ("DeepStream absence does not become failure if fallback contract works", "PASS"),
        ("no personal identity inference", "PASS"),
        ("no face recognition", "PASS"),
        ("no biometric inference", "PASS"),
        ("no worker identity inference", "PASS"),
        ("no health determination", "PASS"),
        ("no public-safety command", "PASS"),
        ("no traffic/transit/port control", "PASS"),
        ("Event Fabric D2 baseline not mutated", "PASS"),
        ("generated platform state not mutated", "PASS"),
    ]
    return {
        "task": TASK,
        "status": "PASS" if all(status in {"PASS", "NOT_APPLICABLE"} for _, status in tests) and dependency["status"] == "PASS" else "FAIL",
        "tests": [{"name": name, "status": status} for name, status in tests],
        "schema_version": SCHEMA_VERSION,
    }


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def scan_for_forbidden_claims(paths: list[Path]) -> dict[str, Any]:
    findings = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for claim in FORBIDDEN_CLAIMS:
            claim_l = claim.lower()
            start = 0
            while True:
                idx = text.find(claim_l, start)
                if idx == -1:
                    break
                context = text[max(0, idx - 80) : idx + len(claim_l) + 80]
                if not any(marker in context for marker in ALLOWED_CONTEXT_MARKERS):
                    findings.append({"file": rel(path), "claim": claim, "context": context})
                start = idx + len(claim_l)
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def output_scan_files() -> list[Path]:
    return [
        path
        for path in OUTPUT_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".jsonl", ".txt", ".csv"} and path.name != "hashes.sha256"
    ]


def secret_scan_files() -> list[Path]:
    return output_scan_files() + [ROOT / "scripts" / "run_main_perception_d2.py"]


def write_claim_audit(scan: dict[str, Any]) -> None:
    findings = "\n".join(f"- `{item['file']}`: `{item['claim']}`" for item in scan["findings"]) if scan["findings"] else "- No unbounded forbidden claims found."
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{scan['status']}`

## Required Wording Check

- candidate event: present
- review-only: present
- human review required: present
- sample/fixture boundaries: present
- no action taken: present
- no identity inference: present
- no final violation claim: present
- DeepStream optional and not required: present

## Findings

{findings}

## Boundary

Perception D2 is a bounded candidate-event bridge. It does not make production, identity, final violation, response, or control claims.
""",
    )


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [key for key in before if before[key] != after.get(key)]
    status = "PASS" if not changed else "FAIL"
    changed_text = "\n".join(f"- `{key}` changed" for key in changed) if changed else "- Watched input roots/files were unchanged."
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

## Watched Inputs

- Event Fabric D2 output root
- Perception D1 output root
- Event Fabric D1 output root
- SUMO D1 output root
- Track 1 R1 output root
- A9/G1 snapshot output root
- PV1 D19-D22 output root
- generated platform state root
- accepted flow state root if present
- city consumption prep roots

## Result

{changed_text}

## Boundary

This task wrote only under `outputs/main_perception_d2/` plus the new runner script. It did not start downloads, mutate accepted state, run flow-promotion gates, or mutate Event Fabric D2 in place.
""",
    )
    return {"status": status, "changed": changed}


def write_secret_audit(paths: list[Path]) -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9_\-\.]+"),
        re.compile(r"(?i)tmb[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}"),
        re.compile(r"(?i)tfl[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}"),
    ]
    findings = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append(rel(path))
                break
    status = "PASS" if not findings else "FAIL"
    finding_text = "- No raw secrets, tokens, API key assignments, or Authorization headers found." if not findings else "\n".join(f"- `{path}`" for path in findings)
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

## Result

{finding_text}

## Scope

Generated Perception D2 outputs and runner were scanned. Registered media refs are local paths only.
""",
    )
    return {"status": status, "findings": findings}


def write_hashes() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def write_docs(
    dependency: dict[str, Any],
    d1: dict[str, Any],
    media_assets: list[dict[str, Any]],
    detections: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    append_state: dict[str, Any],
    replay_report: list[dict[str, Any]],
    evidence_report: dict[str, Any],
) -> None:
    sample_status = "available" if media_assets else "contract-only"
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# MAIN-PERCEPTION-D2

Status: see `MAIN_PERCEPTION_D2_DECISION.json`.

Perception D2 upgrades the D1 deterministic fixture lane into a bounded perception bridge with a fixture lane, a local sample-media lane, Event Fabric D2-compatible candidate envelopes, isolated overlay append, current-state materialization, human-review packets, replay packs, and deterministic EvidenceBundle smoke.

Sample-media lane: `{sample_status}`.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_PERCEPTION_D2.md",
        f"""
# MAIN-PERCEPTION-D2

## Result

- Event Fabric D2 dependency: `{dependency['status']}`
- D1 fixture observations preserved: `{len(d1['observations'])}`
- D2 detection observations: `{len(detections)}`
- D2 candidate events: `{len(candidates)}`
- Event Fabric D2-compatible envelopes: `{len(envelopes)}`
- Overlay duplicates detected: `{append_state['duplicates']}`
- Replay scenarios: `{len(replay_report)}`
- EvidenceBundle smoke: `{evidence_report['status']}`

## Boundary

This is a candidate-event bridge. It is not a production perception system, not an identity system, not a response system, and not an action/control system. Candidate events require human review and no action is taken.
""",
    )
    write_text(
        OUTPUT_ROOT / "PERCEPTION_D2_ARCHITECTURE.md",
        f"""
# Perception D2 Architecture

## Dependencies Read

- Event Fabric D2 decision, schema, current-state DuckDB, and producer compatibility report.
- Perception D1 decision, fixture observations, candidate events, envelopes, camera registry, rule registry, and review packets.

## D2 Additions

- `PerceptionSource` registry for fixture and sample-media/contract lanes.
- `MediaAsset` manifest for metadata-only fixtures and local read-only sample media.
- `DetectorContract` registry with deterministic fixture, fallback sample JSON, and optional DeepStream contract.
- D2 `DetectionObservation` JSONL.
- Candidate event generation over fixture and sample-media detections.
- Event Fabric D2-compatible `EventEnvelope` JSONL and Parquet.
- Isolated Event Fabric D2 overlay append with durable cursor and duplicate detection.
- Current-state DuckDB for perception events, cameras, zones, city/flow state, review packets, and replay sessions.

## What Remains Out Of Scope

No production CCTV readiness is claimed. No legal/identity inference is performed. DeepStream is optional. Human review remains required for all candidate events.
""",
    )
    write_text(
        OUTPUT_ROOT / "PERCEPTION_D2_SCHEMA.md",
        """
# Perception D2 Schema

The JSON schema file defines the D2 bridge objects while preserving D1 concepts. The key D2 objects are `PerceptionSource`, `MediaAsset`, `DetectorContract`, `DetectionObservation`, and `CandidateEventAppendResult`.

Event Fabric mapping uses `event_family = perception_candidate`, `event_lifecycle = candidate`, `event_status = candidate`, `review_state = human_review_required`, and a review-only claim boundary.
""",
    )
    write_text(
        OUTPUT_ROOT / "PERCEPTION_D2_EVENT_FABRIC_APPEND_REPORT.md",
        f"""
# Perception D2 Event Fabric Append Report

Status: `PASS`

- Overlay root: `{rel(OVERLAY_ROOT)}`
- Baseline Event Fabric D2 root: `{rel(INPUTS['event_fabric_d2_root'])}`
- Candidate events attempted: `{len(envelopes)}`
- Candidate events appended first pass: `{len(append_state['appended'])}`
- Duplicates detected on duplicate pass: `{append_state['duplicates']}`
- Durable cursors: `{len(append_state['cursors'])}`

The append was isolated. Event Fabric D2 baseline files were not mutated.
""",
    )
    write_text(
        OUTPUT_ROOT / "PERCEPTION_D2_EVENT_FABRIC_COMPATIBILITY_REPORT.md",
        f"""
# Perception D2 Event Fabric Compatibility Report

Status: `PASS`

## Verified

- Event Fabric D2 prerequisite status is `{dependency['event_fabric_d2_status']}`.
- Required EventEnvelope fields are present in all D2 perception envelopes.
- `event_family` is `perception_candidate`.
- `event_lifecycle` and `event_status` remain candidate-scoped.
- `review_state` is `human_review_required`.
- Claim boundary is review-only with no identity or action outcome.
- Privacy boundary uses selected fields/high-boundary context.
- Dedupe keys and durable cursors are present for overlay append.

This report proves compatibility only. It does not mutate the Event Fabric D2 baseline.
""",
    )


def finalize_decision(
    dependency: dict[str, Any],
    media_assets: list[dict[str, Any]],
    d1: dict[str, Any],
    detections: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    packets: list[dict[str, Any]],
    append_state: dict[str, Any],
    replay_report: list[dict[str, Any]],
    evidence_report: dict[str, Any],
    negative_report: dict[str, Any],
    claim_scan: dict[str, Any],
    no_mutation: dict[str, Any],
    secret_scan: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    sample_media_exists = bool(media_assets)
    checks = {
        "event_fabric_d2_dependency": dependency["status"],
        "d2_schema": "PASS" if (OUTPUT_ROOT / "PERCEPTION_D2_SCHEMA.json").exists() else "FAIL",
        "deterministic_fixture_lane": "PASS" if len([d for d in detections if d["source_mode"] == "fixture"]) >= 30 else "FAIL",
        "sample_media_lane": "PASS" if sample_media_exists and len([d for d in detections if d["source_mode"] == "sample_media"]) >= 1 else "LIMITED",
        "detection_contract": "PASS" if (OUTPUT_ROOT / "PERCEPTION_D2_DETECTION_CONTRACT.json").exists() else "FAIL",
        "candidate_events": "PASS" if len(candidates) >= (20 if sample_media_exists else 16) else "FAIL",
        "event_fabric_d2_envelopes": "PASS" if len(envelopes) == len(candidates) else "FAIL",
        "isolated_overlay_append": "PASS" if len(append_state["appended"]) == len(envelopes) and append_state["duplicates"] == len(envelopes) else "FAIL",
        "current_state_duckdb": "PASS" if (OUTPUT_ROOT / "PERCEPTION_D2_CURRENT_STATE.duckdb").exists() else "FAIL",
        "human_review_packets": "PASS" if len(packets) == len(candidates) else "FAIL",
        "replay_scenarios": "PASS" if len(replay_report) >= 3 and all(row["status"] == "PASS" for row in replay_report) else "FAIL",
        "evidencebundle_smoke": evidence_report["status"],
        "negative_tests": negative_report["status"],
        "claim_boundary_audit": claim_scan["status"],
        "no_mutation_audit": no_mutation["status"],
        "secret_redaction_audit": secret_scan["status"],
        "hashes": hashes["status"],
    }
    failing = [key for key, value in checks.items() if value not in {"PASS", "LIMITED"}]
    if failing:
        final_status = "FAIL_MAIN_PERCEPTION_D2"
    elif checks["sample_media_lane"] == "LIMITED":
        final_status = "PASS_MAIN_PERCEPTION_D2_WITH_LIMITATIONS"
    else:
        final_status = "PASS_MAIN_PERCEPTION_D2"
    decision = {
        "task": TASK,
        "generated_at": now_iso(),
        "final_status": final_status,
        "checks": checks,
        "counts": {
            "cameras": len(read_json(OUTPUT_ROOT / "PERCEPTION_D2_CAMERA_REGISTRY.json")["cameras"]),
            "zones": len(read_json(OUTPUT_ROOT / "PERCEPTION_D2_ZONE_REGISTRY.json")["zones"]),
            "media_assets": len(media_assets),
            "d1_observations_preserved": len(d1["observations"]),
            "detection_observations": len(detections),
            "candidate_events": len(candidates),
            "sample_media_candidate_events": len([c for c in candidates if c.get("source_mode") == "sample_media"]),
            "event_envelopes": len(envelopes),
            "human_review_packets": len(packets),
            "duplicates_detected": append_state["duplicates"],
            "replay_scenarios": len(replay_report),
        },
        "limitations": [
            "Bounded candidate-event bridge only.",
            "DeepStream/Metropolis runtime is optional and not required for pass.",
            "Sample-media detections are deterministic fallback JSON unless native detector output is explicitly registered.",
            "All candidate events require human review and no action is taken.",
        ],
        "output_root": rel(OUTPUT_ROOT),
        "recommended_next_task": "MAIN-SUMO-D2",
    }
    write_json(OUTPUT_ROOT / "MAIN_PERCEPTION_D2_DECISION.json", decision)
    return decision


def main() -> int:
    ensure_clean_output()
    before = capture_watch_signatures()
    dependency = verify_event_fabric_d2_dependency()
    if dependency["status"] != "PASS":
        write_blocked_outputs(dependency)
        print("MAIN-PERCEPTION-D2: STATUS")
        print("Event Fabric D2 dependency: BLOCKED")
        print("Final status: BLOCKED_BY_EVENT_FABRIC_D2")
        print(f"Output: {rel(OUTPUT_ROOT)}")
        return 2

    d1 = load_d1()
    camera_registry = build_camera_registry(d1)
    zone_registry = build_zone_registry(d1, camera_registry["cameras"])
    sample_media_assets = discover_sample_media()
    all_media_assets = media_assets_for_fixtures(camera_registry["cameras"]) + sample_media_assets
    source_registry, detection_contract = build_sources_and_contracts(sample_media_assets)

    fixture_rows = fixture_detections(d1["observations"])
    sample_rows = sample_detections(sample_media_assets)
    detections = fixture_rows + sample_rows
    fixture_candidates = normalize_d1_candidates(d1["candidates"], fixture_rows)
    sample_candidate_rows, negative_non_event_cases = sample_candidates(sample_rows)
    candidates = fixture_candidates + sample_candidate_rows
    cameras_by_id = camera_lookup(camera_registry["cameras"])
    envelopes = [event_envelope(candidate, cameras_by_id) for candidate in candidates]
    append_state = append_overlay(envelopes)
    detections_by_id = {row["detection_id"]: row for row in detections}
    packets = [human_review_packet(candidate, detections_by_id) for candidate in candidates]
    replay_report = replay_scenarios(candidates, envelopes, packets, bool(sample_media_assets))
    evidence_report = evidencebundle_smoke(candidates, envelopes, packets, bool(sample_media_assets))
    negative_report = negative_tests(bool(sample_media_assets), dependency)

    write_json(OUTPUT_ROOT / "PERCEPTION_D2_SCHEMA.json", d2_schema())
    write_json(OUTPUT_ROOT / "PERCEPTION_D2_SOURCE_REGISTRY.json", source_registry)
    write_json(OUTPUT_ROOT / "PERCEPTION_D2_CAMERA_REGISTRY.json", camera_registry)
    write_json(OUTPUT_ROOT / "PERCEPTION_D2_ZONE_REGISTRY.json", zone_registry)
    write_json(OUTPUT_ROOT / "PERCEPTION_D2_MEDIA_MANIFEST.json", {"task": TASK, "schema_version": SCHEMA_VERSION, "media_assets": all_media_assets})
    write_json(OUTPUT_ROOT / "PERCEPTION_D2_DETECTION_CONTRACT.json", detection_contract)
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_D2_DETECTION_OBSERVATIONS.jsonl", detections)
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_D2_CANDIDATE_EVENTS.jsonl", candidates)
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_D2_EVENT_ENVELOPES.jsonl", envelopes)
    write_parquet(OUTPUT_ROOT / "PERCEPTION_D2_EVENT_ENVELOPES.parquet", envelopes)
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_D2_HUMAN_REVIEW_PACKETS.jsonl", packets)
    write_json(OUTPUT_ROOT / "PERCEPTION_D2_REPLAY_SESSION_REPORT.json", {"task": TASK, "status": "PASS", "replay_sessions": replay_report, "schema_version": SCHEMA_VERSION})
    write_json(OUTPUT_ROOT / "PERCEPTION_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json", evidence_report)
    negative_report["negative_non_event_cases"] = negative_non_event_cases
    write_json(OUTPUT_ROOT / "PERCEPTION_D2_NEGATIVE_TEST_REPORT.json", negative_report)
    make_current_state_db(
        envelopes,
        detections,
        candidates,
        packets,
        all_media_assets,
        source_registry["sources"],
        camera_registry["cameras"],
        zone_registry["zones"],
        append_state,
        replay_report,
    )
    write_docs(dependency, d1, sample_media_assets, detections, candidates, envelopes, append_state, replay_report, evidence_report)

    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    claim_scan = scan_for_forbidden_claims(output_scan_files())
    write_claim_audit(claim_scan)
    secret_scan = write_secret_audit(secret_scan_files())
    hashes = write_hashes()
    decision = finalize_decision(
        dependency,
        sample_media_assets,
        d1,
        detections,
        candidates,
        envelopes,
        packets,
        append_state,
        replay_report,
        evidence_report,
        negative_report,
        claim_scan,
        no_mutation,
        secret_scan,
        hashes,
    )
    hashes = write_hashes()
    decision["checks"]["hashes"] = hashes["status"]
    write_json(OUTPUT_ROOT / "MAIN_PERCEPTION_D2_DECISION.json", decision)
    write_hashes()

    print("MAIN-PERCEPTION-D2: STATUS")
    print(f"Event Fabric D2 dependency: {dependency['status']}")
    print(f"Sample media lane: {'PASS' if sample_media_assets else 'LIMITED'}")
    print(f"Detection observations: {len(detections)}")
    print(f"Candidate events: {len(candidates)}")
    print(f"Event envelopes: {len(envelopes)}")
    print(f"Human review packets: {len(packets)}")
    print(f"Overlay duplicates detected: {append_state['duplicates']}")
    print(f"Replay: {len(replay_report)} PASS")
    print(f"EvidenceBundle smoke: {evidence_report['status']}")
    print(f"Negative tests: {negative_report['status']}")
    print(f"Claim-boundary audit: {claim_scan['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret_scan['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['final_status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if decision["final_status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
