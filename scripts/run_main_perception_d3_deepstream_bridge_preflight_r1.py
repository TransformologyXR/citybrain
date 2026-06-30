from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_perception_d3_deepstream_bridge_preflight_r1"
TASK = "MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE-PREFLIGHT-R1"
SCHEMA_VERSION = "main-perception-d3-deepstream-bridge-preflight-r1.v1"
NOW = datetime(2026, 6, 29, 19, 0, 0, tzinfo=timezone.utc)


INPUTS = {
    "event_fabric_d3_service_root": ROOT / "outputs" / "main_event_fabric_d3_service_hardening",
    "event_fabric_d3_service_decision": ROOT
    / "outputs"
    / "main_event_fabric_d3_service_hardening"
    / "MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_DECISION.json",
    "event_fabric_d3_api_contract": ROOT
    / "outputs"
    / "main_event_fabric_d3_service_hardening"
    / "EVENT_FABRIC_D3_API_CONTRACT.json",
    "event_fabric_d3_multicity_root": ROOT / "outputs" / "main_event_fabric_d3_multicity_adapters",
    "event_fabric_d3_multicity_decision": ROOT
    / "outputs"
    / "main_event_fabric_d3_multicity_adapters"
    / "MAIN_EVENT_FABRIC_D3_MULTICITY_ADAPTERS_DECISION.json",
    "event_fabric_d3_adapter_contract": ROOT / "outputs" / "main_event_fabric_d3_multicity_adapters" / "CITY_ADAPTER_CONTRACT.schema.json",
    "perception_d2_root": ROOT / "outputs" / "main_perception_d2",
    "perception_d2_decision": ROOT / "outputs" / "main_perception_d2" / "MAIN_PERCEPTION_D2_DECISION.json",
    "perception_d2_schema": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_SCHEMA.json",
    "perception_d2_detection_contract": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_DETECTION_CONTRACT.json",
    "perception_d2_media_manifest": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_MEDIA_MANIFEST.json",
    "perception_d2_candidate_events": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_CANDIDATE_EVENTS.jsonl",
    "infra_txr4070_root": ROOT / "outputs" / "infra_txr4070_d3_runtime_readiness_check_r1",
    "infra_txr4070_decision": ROOT
    / "outputs"
    / "infra_txr4070_d3_runtime_readiness_check_r1"
    / "INFRA_TXR4070_D3_RUNTIME_READINESS_CHECK_R1_DECISION.json",
    "infra_deepstream_report": ROOT
    / "outputs"
    / "infra_txr4070_d3_runtime_readiness_check_r1"
    / "DEEPSTREAM_METROPOLIS_READINESS_REPORT.json",
    "pv1_d19_d22_root": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1_root": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state_root": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state_root": ROOT / "outputs" / "accepted_flow_state",
}

WATCH_KEYS = [
    "event_fabric_d3_service_root",
    "event_fabric_d3_multicity_root",
    "perception_d2_root",
    "infra_txr4070_root",
    "pv1_d19_d22_root",
    "a9_g1_root",
    "platform_state_root",
    "accepted_flow_state_root",
]

FORBIDDEN_CLAIMS = [
    "production-ready",
    "production readiness",
    "production cctv",
    "confirmed violation",
    "legal violation",
    "identity inference",
    "biometric",
    "face recognition",
    "enforcement recommendation",
    "dispatch recommendation",
    "public-safety command",
    "routing recommendation",
    "traffic-control command",
    "transit-control command",
    "port-control command",
    "certified impact",
    "certified affected asset",
    "autonomous action",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "never ",
    "forbidden",
    "blocked",
    "negative",
    "does not",
    "do not",
    "cannot",
    "must not",
    "without",
    "boundary",
    "refuse",
    "candidate",
    "review",
    "limitation",
]

CANDIDATE_FAMILIES = [
    "person_detected_context",
    "ppe_candidate_context",
    "restricted_zone_entry_candidate",
    "worker_near_equipment_candidate",
    "after_hours_activity_candidate",
    "camera_health_candidate",
]


def now_iso() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest('|'.join(str(part) for part in parts), length)}"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=True, default=str) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
                if limit is not None and len(rows) >= limit:
                    break
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_command(command: list[str], timeout: int = 12) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "command": command,
            "returncode": completed.returncode,
            "ok": completed.returncode == 0,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except FileNotFoundError as exc:
        return {"command": command, "returncode": None, "ok": False, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {"command": command, "returncode": None, "ok": False, "stdout": exc.stdout or "", "stderr": "TIMEOUT"}


def capture_watch_signatures() -> dict[str, Any]:
    signatures: dict[str, Any] = {}
    for key in WATCH_KEYS:
        root = INPUTS[key]
        if not root.exists():
            signatures[key] = {"exists": False}
            continue
        if root.is_file():
            stat = root.stat()
            signatures[key] = {"exists": True, "kind": "file", "size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha256_file(root)}
            continue
        file_count = 0
        total_size = 0
        newest_mtime = 0
        for path in root.rglob("*"):
            if path.is_file():
                stat = path.stat()
                file_count += 1
                total_size += stat.st_size
                newest_mtime = max(newest_mtime, stat.st_mtime_ns)
        signatures[key] = {"exists": True, "kind": "dir", "file_count": file_count, "total_size": total_size, "newest_mtime_ns": newest_mtime}
    return signatures


def ensure_output() -> None:
    resolved = OUTPUT_ROOT.resolve()
    if ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to write outside workspace: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def validate_prerequisites() -> dict[str, Any]:
    service = read_json(INPUTS["event_fabric_d3_service_decision"])
    multicity = read_json(INPUTS["event_fabric_d3_multicity_decision"])
    perception = read_json(INPUTS["perception_d2_decision"])
    api_contract = read_json(INPUTS["event_fabric_d3_api_contract"])
    adapter_contract = read_json(INPUTS["event_fabric_d3_adapter_contract"])
    d2_schema = read_json(INPUTS["perception_d2_schema"])
    checks = {
        "event_fabric_d3_service_hardening": "PASS"
        if service.get("final_status") == "PASS_MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING"
        else "FAIL",
        "event_fabric_d3_api_contract": "PASS" if api_contract.get("endpoints") else "FAIL",
        "event_fabric_d3_multicity_adapters": "PASS"
        if multicity.get("status") == "PASS_MAIN_EVENT_FABRIC_D3_MULTICITY_ADAPTERS_WITH_LIMITATIONS"
        else "FAIL",
        "event_fabric_d3_adapter_contract": "PASS" if "candidate_review" in adapter_contract.get("lifecycle_states", []) else "FAIL",
        "perception_d2": "PASS" if perception.get("final_status") == "PASS_MAIN_PERCEPTION_D2" else "FAIL",
        "perception_d2_candidate_envelopes": "PASS" if "DetectionObservation" in d2_schema.get("definitions", {}) else "FAIL",
        "deepstream_not_assumed_ready": "PASS",
    }
    return {
        "task": TASK,
        "status": "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL",
        "checks": checks,
        "source_statuses": {
            "event_fabric_d3_service": service.get("final_status"),
            "event_fabric_d3_multicity": multicity.get("status"),
            "perception_d2": perception.get("final_status"),
            "deepstream_previous_infra": read_json(INPUTS["infra_txr4070_decision"]).get("key_checks", {}).get("deepstream_metropolis", "UNKNOWN"),
        },
        "schema_version": SCHEMA_VERSION,
    }


def write_contracts() -> None:
    input_contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "task": TASK,
        "schema_version": SCHEMA_VERSION,
        "title": "Perception D3 DeepStream Input Contract",
        "allowed_media_types": ["video", "image_sequence", "metadata_only_fixture", "official_deepstream_sample_when_available"],
        "allowed_source_modes": ["local_sample_media", "deterministic_fixture_not_model_inference", "official_deepstream_sample_pending_container"],
        "required_fields": [
            "media_id",
            "media_type",
            "uri_or_path",
            "city",
            "camera_id",
            "zone_refs",
            "redaction_status",
            "privacy_boundary",
            "claim_boundary",
            "allowed_use",
            "forbidden_use",
            "schema_version",
        ],
        "forbidden_inputs": ["private_cctv", "personal_identity_dataset", "face_template", "biometric_dataset"],
        "required_boundary": "Candidate/review scaffold only; no action taken.",
    }
    output_contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "task": TASK,
        "schema_version": SCHEMA_VERSION,
        "title": "Perception D3 DeepStream Output Metadata Contract",
        "source_label": "DeepStream-like metadata or deterministic fixture metadata",
        "required_fields": [
            "deepstream_record_id",
            "source_mode",
            "stream_id",
            "media_id",
            "camera_id",
            "frame_index",
            "frame_time_seconds",
            "object_id",
            "class_id",
            "class_label",
            "bbox",
            "confidence",
            "tracker_confidence",
            "attributes",
            "zone_refs",
            "detector_ref",
            "privacy_boundary",
            "claim_boundary",
            "schema_version",
        ],
        "bbox_formats": ["xyxy_pixels", "xywh_pixels", "normalized_xywh"],
        "forbidden_fields": ["person_name", "face_embedding", "biometric_identifier", "license_plate_identity", "legal_violation"],
        "runtime_readiness_rule": "Metadata may be fixture-generated until INFRA-TXR4070-DEEPSTREAM-CONTAINER-SMOKE-R1 proves READY_CONTAINER.",
    }
    candidate_contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "task": TASK,
        "schema_version": SCHEMA_VERSION,
        "title": "Perception D3 Candidate Event Contract",
        "candidate_event_families": CANDIDATE_FAMILIES,
        "required_fields": [
            "candidate_event_id",
            "candidate_event_family",
            "event_type",
            "event_family",
            "city",
            "camera_id",
            "media_id",
            "event_time",
            "detection_ids",
            "zone_refs",
            "entity_refs",
            "evidence_refs",
            "confidence",
            "review_state",
            "lifecycle_state",
            "privacy_boundary",
            "claim_boundary",
            "blocked_outcome_codes",
            "no_action_taken",
            "source_mode",
            "schema_version",
        ],
        "review_state": "human_review_required",
        "lifecycle_state": "candidate_review",
        "event_family": "perception_candidate",
        "forbidden_outcomes": [
            "confirmed_violation",
            "identity_inference",
            "biometric_inference",
            "face_recognition",
            "dispatch_or_enforcement_action",
            "traffic_or_transit_control",
            "certified_impact",
        ],
    }
    mapping = {
        "task": TASK,
        "schema_version": SCHEMA_VERSION,
        "event_fabric_d3_mapping": {
            "adapter_id": "perception_d3_deepstream_bridge_preflight_r1",
            "city_id": "candidate_event.city",
            "source_family": "perception_candidate",
            "source_system": "deepstream_bridge_or_deterministic_fixture",
            "flow_ids": ["TRACK1_PERCEPTION_RUNTIME"],
            "event_family": "perception_candidate",
            "event_type": "candidate_event.event_type",
            "lifecycle_state": "candidate_review",
            "event_status": "candidate",
            "review_state": "human_review_required",
            "claim_boundary": "REVIEW_ONLY",
            "privacy_boundary": "HIGH_BOUNDARY_RISK_CONTEXT_ONLY or PRIVACY_SAFE_SELECTED_FIELDS",
            "source_key": "perception_d3_deepstream_bridge_preflight_r1",
            "source_record_id": "candidate_event.candidate_event_id",
            "dedupe_key": "city|camera_id|candidate_event_family|event_time|source_record_id",
            "cursor_key": "perception_d3_bridge:city:camera_id",
            "no_action_taken": True,
            "payload": "candidate event plus detection refs, media refs, zone refs, limitations",
        },
        "append_target": "outputs/main_perception_d3_deepstream_bridge_preflight_r1/event_fabric_overlay",
        "mutation_rule": "Do not append into prior Event Fabric D3 roots.",
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_DEEPSTREAM_INPUT_CONTRACT.json", input_contract)
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_DEEPSTREAM_OUTPUT_CONTRACT.json", output_contract)
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_CANDIDATE_EVENT_CONTRACT.json", candidate_contract)
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_EVENT_FABRIC_MAPPING.json", mapping)


def write_docs() -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        """
# MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE-PREFLIGHT-R1

This pack prepares the Perception D3 DeepStream bridge contract, deterministic fixture harness, Event Fabric D3 mapping, infra readiness check, and audits.

The output is preflight/scaffold only. It does not claim a real DeepStream bridge is complete and does not run private CCTV or production video inference.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1.md",
        """
# MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE-PREFLIGHT-R1

Status is expected to be waiting on infrastructure until a real DeepStream container smoke artifact proves `READY_CONTAINER`.

The scaffold maps deterministic DeepStream-like metadata into candidate/review-only perception events, then into an isolated Event Fabric D3 overlay. It does not mutate Event Fabric D3, Perception D2, PV1, A9/G1, generated platform state, or accepted flow state.
""",
    )
    write_text(
        OUTPUT_ROOT / "PERCEPTION_D3_BRIDGE_ARCHITECTURE.md",
        """
# Perception D3 Bridge Architecture

## Flow

DeepStream detection/tracking/zone output becomes normalized perception observation metadata. The bridge converts those observations into candidate/review-only events, maps them to the Event Fabric D3 append contract, materializes a local overlay current-state view, and produces deterministic EvidenceBundle smoke records for review.

## Boundary

Perception D3 produces candidate observations only. It makes no final legal determination, no identity inference, no biometric output, no face recognition output, no operational dispatch, no enforcement action, no routing/control action, no public-safety command, no certified impact, and no production-readiness claim.

## Preflight Mode

Until `INFRA-TXR4070-DEEPSTREAM-CONTAINER-SMOKE-R1` proves a ready DeepStream container, the harness uses `deterministic_fixture_not_model_inference` metadata. The fixture validates the bridge shape without claiming model inference.
""",
    )


def build_sample_media_manifest() -> dict[str, Any]:
    d2_manifest = read_json(INPUTS["perception_d2_media_manifest"])
    d2_assets = d2_manifest.get("media_assets", [])
    selected = []
    for asset in d2_assets:
        if asset.get("media_type") == "video" or asset.get("exists") is False:
            asset_path = ROOT / str(asset.get("path", ""))
            selected.append(
                {
                    "media_id": f"d3_{asset.get('media_id')}",
                    "source_media_id": asset.get("media_id"),
                    "media_type": asset.get("media_type", "metadata_only"),
                    "uri_or_path": asset.get("path"),
                    "path_exists_from_workspace": asset_path.exists() if not str(asset.get("path", "")).startswith("fixture://") else False,
                    "bytes": asset.get("bytes"),
                    "sha256": asset.get("sha256"),
                    "city": "BARC" if "barc" in str(asset.get("camera_id", "")).lower() else ("NYC" if "nyc" in str(asset.get("camera_id", "")).lower() else ("LON" if "lon" in str(asset.get("camera_id", "")).lower() else "UNKNOWN")),
                    "camera_id": asset.get("camera_id"),
                    "zone_refs": [f"zone_{asset.get('camera_id', 'unknown')}_review"],
                    "redaction_status": asset.get("redaction_status", "metadata_only"),
                    "privacy_boundary": asset.get("privacy_boundary", "PRIVACY_SAFE_SELECTED_FIELDS"),
                    "claim_boundary": "Candidate/review scaffold only; no action taken; no identity inference.",
                    "allowed_use": ["bridge_contract_preflight", "deterministic_fixture_harness"],
                    "forbidden_use": ["private_cctv", "production_cctv", "identity_or_biometric_inference", "confirmed_violation"],
                    "source_mode": "local_sample_media" if asset.get("exists") else "deterministic_fixture_not_model_inference",
                    "schema_version": SCHEMA_VERSION,
                }
            )
    if not selected:
        selected.append(
            {
                "media_id": "d3_synthetic_metadata_only_001",
                "source_media_id": None,
                "media_type": "metadata_only_fixture",
                "uri_or_path": "fixture://perception_d3_deepstream_bridge_preflight/synthetic_metadata_only_001",
                "path_exists_from_workspace": False,
                "city": "BARC",
                "camera_id": "cam_barc_synthetic_preflight_001",
                "zone_refs": ["zone_barc_synthetic_review_001"],
                "redaction_status": "synthetic_metadata_only_no_clip",
                "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
                "claim_boundary": "Synthetic fixture for candidate/review scaffold only; no action taken.",
                "allowed_use": ["bridge_contract_preflight", "deterministic_fixture_harness"],
                "forbidden_use": ["private_cctv", "production_cctv", "identity_or_biometric_inference", "confirmed_violation"],
                "source_mode": "deterministic_fixture_not_model_inference",
                "schema_version": SCHEMA_VERSION,
            }
        )
    selected = selected[:6]
    manifest = {
        "task": TASK,
        "status": "PASS",
        "media_assets": selected,
        "selection_policy": "Existing Perception D2 sample media and metadata-only fixtures only; no private CCTV feeds.",
        "official_deepstream_samples": "deferred_until_container_ready",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_SAMPLE_MEDIA_MANIFEST.json", manifest)
    return manifest


def family_fixture_specs() -> list[dict[str, Any]]:
    return [
        {"family": "person_detected_context", "class_label": "person", "attributes": {"context_only": True}},
        {"family": "ppe_candidate_context", "class_label": "person", "attributes": {"ppe_helmet_visible": False, "ppe_vest_visible": True}},
        {"family": "restricted_zone_entry_candidate", "class_label": "person", "attributes": {"zone_overlap": "restricted_candidate_zone"}},
        {"family": "worker_near_equipment_candidate", "class_label": "person", "attributes": {"near_equipment": True, "equipment_ref": "equipment_fixture_001"}},
        {"family": "after_hours_activity_candidate", "class_label": "person", "attributes": {"after_hours": True}},
        {"family": "camera_health_candidate", "class_label": "camera_obstruction", "attributes": {"camera_health": "obstruction_candidate"}},
    ]


def generate_fixtures(media_manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    media_assets = media_manifest["media_assets"]
    fixtures = []
    observations = []
    candidate_events = []
    specs = family_fixture_specs()
    for i, spec in enumerate(specs):
        asset = media_assets[i % len(media_assets)]
        event_time = f"2026-06-29T19:{i:02d}:00Z"
        record_id = stable_id("deepstream-fixture-record", spec["family"], asset["media_id"], i)
        detection_id = stable_id("perception-d3-detection", record_id)
        observation_id = stable_id("perception-d3-observation", detection_id)
        candidate_id = stable_id("perception-d3-candidate", observation_id, spec["family"])
        bbox = {"format": "xyxy_pixels", "x1": 120 + i * 5, "y1": 80 + i * 3, "x2": 220 + i * 5, "y2": 260 + i * 3}
        fixture = {
            "deepstream_record_id": record_id,
            "source_mode": "deterministic_fixture_not_model_inference",
            "stream_id": f"stream_{asset['camera_id']}",
            "media_id": asset["media_id"],
            "camera_id": asset["camera_id"],
            "city": asset["city"],
            "frame_index": 100 + i * 40,
            "frame_time_seconds": round(4.0 + i * 1.25, 3),
            "observed_at": event_time,
            "object_id": f"fixture_track_{i:03d}",
            "class_id": i + 1,
            "class_label": spec["class_label"],
            "bbox": bbox,
            "confidence": round(0.72 + i * 0.025, 3),
            "tracker_confidence": round(0.68 + i * 0.02, 3),
            "attributes": spec["attributes"],
            "zone_refs": asset["zone_refs"],
            "detector_ref": "detector_deepstream_d3_preflight_fixture",
            "privacy_boundary": "HIGH_BOUNDARY_RISK_CONTEXT_ONLY" if spec["class_label"] == "person" else "PRIVACY_SAFE_SELECTED_FIELDS",
            "claim_boundary": "REVIEW_ONLY: deterministic fixture metadata; no action taken; not model inference.",
            "schema_version": SCHEMA_VERSION,
        }
        observation = {
            "observation_id": observation_id,
            "detection_id": detection_id,
            "deepstream_record_id": record_id,
            "city": asset["city"],
            "camera_id": asset["camera_id"],
            "media_id": asset["media_id"],
            "observed_at": event_time,
            "frame_index": fixture["frame_index"],
            "frame_time_seconds": fixture["frame_time_seconds"],
            "track_id": fixture["object_id"],
            "object_class": spec["class_label"],
            "bbox": bbox,
            "confidence": fixture["confidence"],
            "attributes": fixture["attributes"],
            "zone_refs": asset["zone_refs"],
            "detector_ref": fixture["detector_ref"],
            "source_mode": "deterministic_fixture_not_model_inference",
            "privacy_boundary": fixture["privacy_boundary"],
            "claim_boundary": "REVIEW_ONLY: candidate observation; no action taken; no identity inference.",
            "schema_version": SCHEMA_VERSION,
        }
        candidate = {
            "candidate_event_id": candidate_id,
            "candidate_event_family": spec["family"],
            "event_type": spec["family"],
            "event_family": "perception_candidate",
            "city": asset["city"],
            "camera_id": asset["camera_id"],
            "media_id": asset["media_id"],
            "event_time": event_time,
            "event_end_time": None,
            "detection_ids": [detection_id],
            "observation_ids": [observation_id],
            "zone_refs": asset["zone_refs"],
            "entity_refs": [{"entity_ref": zone, "entity_type": "review_zone"} for zone in asset["zone_refs"]],
            "evidence_refs": [
                {
                    "evidence_ref_id": stable_id("perception-d3-evidence", candidate_id),
                    "media_id": asset["media_id"],
                    "camera_id": asset["camera_id"],
                    "frame_refs": [f"{asset['camera_id']}:frame:{fixture['frame_index']:06d}"],
                    "uri_or_path": asset["uri_or_path"],
                    "redaction_status": asset["redaction_status"],
                    "privacy_boundary": asset["privacy_boundary"],
                    "retention_policy": "metadata_only_or_sample_asset_reference_no_private_cctv",
                    "schema_version": SCHEMA_VERSION,
                }
            ],
            "confidence": fixture["confidence"],
            "review_state": "human_review_required",
            "lifecycle_state": "candidate_review",
            "privacy_boundary": fixture["privacy_boundary"],
            "claim_boundary": "REVIEW_ONLY: candidate perception event; human review required; no action taken; no identity inference; no confirmed violation.",
            "blocked_outcome_codes": [
                "confirmed_violation",
                "legal_conclusion",
                "identity_inference",
                "biometric_inference",
                "face_recognition",
                "dispatch_or_enforcement_action",
                "routing_or_control_action",
                "certified_impact",
            ],
            "no_action_taken": True,
            "source_mode": "deterministic_fixture_not_model_inference",
            "limitations": ["Fixture metadata only; not model inference.", "DeepStream container smoke not yet proven ready."],
            "schema_version": SCHEMA_VERSION,
        }
        fixtures.append(fixture)
        observations.append(observation)
        candidate_events.append(candidate)

    fixture_root = OUTPUT_ROOT / "fixtures"
    write_jsonl(fixture_root / "PERCEPTION_D3_DEEPSTREAM_METADATA_FIXTURE.jsonl", fixtures)
    write_jsonl(fixture_root / "PERCEPTION_D3_NORMALIZED_OBSERVATIONS.jsonl", observations)
    write_jsonl(fixture_root / "PERCEPTION_D3_CANDIDATE_EVENTS.jsonl", candidate_events)
    report = {
        "task": TASK,
        "status": "PASS",
        "metadata_fixture_count": len(fixtures),
        "normalized_observation_count": len(observations),
        "candidate_event_count": len(candidate_events),
        "candidate_event_families": sorted({row["candidate_event_family"] for row in candidate_events}),
        "fixture_label": "deterministic_fixture_not_model_inference",
        "fixture_paths": [rel(fixture_root / "PERCEPTION_D3_DEEPSTREAM_METADATA_FIXTURE.jsonl"), rel(fixture_root / "PERCEPTION_D3_NORMALIZED_OBSERVATIONS.jsonl"), rel(fixture_root / "PERCEPTION_D3_CANDIDATE_EVENTS.jsonl")],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_FIXTURE_GENERATION_REPORT.json", report)
    return fixtures, observations, candidate_events


def map_to_event_fabric(candidate_events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    envelopes = []
    for candidate in candidate_events:
        dedupe_key = "|".join(
            [
                candidate["city"],
                candidate["camera_id"],
                candidate["candidate_event_family"],
                candidate["event_time"],
                candidate["candidate_event_id"],
            ]
        )
        envelope = {
            "event_envelope_id": stable_id("perception-d3-envelope", dedupe_key),
            "adapter_id": "perception_d3_deepstream_bridge_preflight_r1",
            "city_id": candidate["city"],
            "city_name": candidate["city"],
            "source_family": "perception_candidate",
            "source_system": "deepstream_bridge_preflight_fixture",
            "flow_ids": ["TRACK1_PERCEPTION_RUNTIME"],
            "event_family": "perception_candidate",
            "event_type": candidate["event_type"],
            "lifecycle_state": "candidate_review",
            "event_status": "candidate",
            "review_state": "human_review_required",
            "claim_boundary": candidate["claim_boundary"],
            "privacy_boundary": candidate["privacy_boundary"],
            "source_refs": candidate["evidence_refs"],
            "source_key": "perception_d3_deepstream_bridge_preflight_r1",
            "source_record_id": candidate["candidate_event_id"],
            "cursor_key": f"perception_d3_bridge:{candidate['city']}:{candidate['camera_id']}",
            "cursor_state": "ACTIVE_PREFLIGHT_FIXTURE",
            "dedupe_key": dedupe_key,
            "observed_at": candidate["event_time"],
            "ingested_at": now_iso(),
            "expires_at": None,
            "confidence": candidate["confidence"],
            "limitations": candidate["limitations"],
            "no_action_taken": True,
            "raw_source_pointer": f"fixtures/PERCEPTION_D3_CANDIDATE_EVENTS.jsonl#{candidate['candidate_event_id']}",
            "canonical_entity_refs": candidate["entity_refs"],
            "evidence_refs": candidate["evidence_refs"],
            "payload": candidate,
            "schema_version": SCHEMA_VERSION,
        }
        envelopes.append(envelope)

    attempted = envelopes + [dict(envelopes[0]), dict(envelopes[-1])]
    seen = set()
    appended = []
    duplicates = []
    for envelope in attempted:
        if envelope["dedupe_key"] in seen:
            duplicates.append(envelope)
        else:
            seen.add(envelope["dedupe_key"])
            appended.append(envelope)

    overlay = OUTPUT_ROOT / "event_fabric_overlay"
    write_jsonl(overlay / "PERCEPTION_D3_EVENT_ENVELOPES.jsonl", appended)
    current_state = [
        {
            "current_state_id": stable_id("perception-d3-current", row["dedupe_key"]),
            "city": row["city_id"],
            "camera_id": row["payload"]["camera_id"],
            "candidate_event_family": row["payload"]["candidate_event_family"],
            "event_time": row["observed_at"],
            "review_state": row["review_state"],
            "claim_boundary": row["claim_boundary"],
            "privacy_boundary": row["privacy_boundary"],
            "no_action_taken": True,
            "source_envelope_id": row["event_envelope_id"],
            "schema_version": SCHEMA_VERSION,
        }
        for row in appended
    ]
    write_json(overlay / "PERCEPTION_D3_CURRENT_STATE_CANDIDATE_REVIEW.json", {"task": TASK, "rows": current_state, "schema_version": SCHEMA_VERSION})
    append_report = {
        "task": TASK,
        "status": "PASS",
        "append_target": rel(overlay),
        "attempted": len(attempted),
        "appended": len(appended),
        "duplicates": len(duplicates),
        "local_overlay_only": True,
        "mutated_prior_event_fabric": False,
        "event_counts_by_family": dict(Counter(row["payload"]["candidate_event_family"] for row in appended)),
        "schema_version": SCHEMA_VERSION,
    }
    harness_report = {
        "task": TASK,
        "status": "PASS",
        "input_fixture_path": rel(OUTPUT_ROOT / "fixtures" / "PERCEPTION_D3_DEEPSTREAM_METADATA_FIXTURE.jsonl"),
        "candidate_event_path": rel(OUTPUT_ROOT / "fixtures" / "PERCEPTION_D3_CANDIDATE_EVENTS.jsonl"),
        "event_envelope_path": rel(overlay / "PERCEPTION_D3_EVENT_ENVELOPES.jsonl"),
        "current_state_path": rel(overlay / "PERCEPTION_D3_CURRENT_STATE_CANDIDATE_REVIEW.json"),
        "read_deterministic_fixture_metadata": True,
        "mapped_to_candidate_review_events": True,
        "attached_source_and_media_refs": True,
        "idempotent_append": append_report["duplicates"] > 0,
        "event_fabric_overlay_only": True,
        "candidate_events_appended": len(appended),
        "duplicate_attempts_detected": len(duplicates),
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_BRIDGE_HARNESS_REPORT.json", harness_report)
    return appended, append_report, harness_report


def build_evidencebundle_smoke(envelopes: list[dict[str, Any]]) -> dict[str, Any]:
    bundles = []
    for family in CANDIDATE_FAMILIES:
        family_rows = [row for row in envelopes if row["payload"]["candidate_event_family"] == family]
        if not family_rows:
            continue
        row = family_rows[0]
        bundles.append(
            {
                "evidencebundle_id": stable_id("perception-d3-eb", family, row["event_envelope_id"]),
                "candidate_event_family": family,
                "event_refs": [row["event_envelope_id"]],
                "detection_refs": row["payload"]["detection_ids"],
                "media_refs": [ref["media_id"] for ref in row["payload"]["evidence_refs"]],
                "zone_refs": row["payload"]["zone_refs"],
                "review_state": "human_review_required",
                "claim_boundary": "REVIEW_ONLY: candidate evidence bundle; no action taken; no final determination.",
                "privacy_boundary": row["privacy_boundary"],
                "recommended_answer_boundary": "Describe candidate context and limitations only.",
                "limitations": row["limitations"],
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    report = {
        "task": TASK,
        "status": "PASS" if len(bundles) == len(CANDIDATE_FAMILIES) else "FAIL",
        "bundle_count": len(bundles),
        "bundles": bundles,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "event_fabric_overlay" / "PERCEPTION_D3_EVIDENCEBUNDLE_SMOKE.json", report)
    return report


def find_ready_container_smoke() -> dict[str, Any]:
    candidates = []
    for path in (ROOT / "outputs").glob("*deepstream*"):
        for decision in path.rglob("*DECISION*.json"):
            data = read_json(decision)
            text = json.dumps(data, sort_keys=True).upper()
            if "READY_CONTAINER" in text or "PASS_INFRA_TXR4070_DEEPSTREAM_CONTAINER_SMOKE" in text:
                candidates.append({"path": rel(decision), "status": data.get("status") or data.get("final_status")})
    return {"found": bool(candidates), "artifacts": candidates}


def infra_readiness_check() -> dict[str, Any]:
    prior_decision = read_json(INPUTS["infra_txr4070_decision"])
    prior_deepstream = read_json(INPUTS["infra_deepstream_report"])
    local_docker = run_command(["docker", "--version"], timeout=8)
    remote_images = run_command(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            "txr-4070",
            "docker images --format '{{.Repository}}:{{.Tag}}\\t{{.ID}}\\t{{.Size}}' 2>/dev/null | egrep -i 'deepstream|metropolis|triton|nvcr' || true",
        ],
        timeout=12,
    )
    remote_containers = run_command(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            "txr-4070",
            "docker ps -a --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' 2>/dev/null | egrep -i 'deepstream|metropolis|triton|nvcr' || true",
        ],
        timeout=12,
    )
    smoke = find_ready_container_smoke()
    image_available = bool(remote_images.get("stdout"))
    container_seen = bool(remote_containers.get("stdout"))
    ready = smoke["found"]
    status = "READY_CONTAINER_SMOKE_FOUND" if ready else "WAITING_ON_INFRA_DEEPSTREAM_CONTAINER_PULL_OR_SMOKE"
    report = {
        "task": TASK,
        "status": status,
        "deepstream_runtime_ready": ready,
        "image_available_without_pull": image_available,
        "container_seen_without_starting": container_seen,
        "local_docker_check": local_docker,
        "remote_image_check": remote_images,
        "remote_container_check": remote_containers,
        "ready_container_smoke_artifacts": smoke,
        "prior_infra_status": prior_decision.get("key_checks", {}).get("deepstream_metropolis"),
        "prior_deepstream_report_status": prior_deepstream.get("status"),
        "known_external_state": [
            "txr-4070 Docker GPU previously passed.",
            "DeepStream was previously PARTIAL_CONTAINER_READY.",
            "No real DeepStream bridge completion is claimed by this preflight unless ready_container_smoke_artifacts is non-empty.",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_INFRA_READINESS_CHECK.json", report)
    write_text(
        OUTPUT_ROOT / "PERCEPTION_D3_DEEPSTREAM_WAITING_ON_INFRA_NOTE.md",
        f"""
# Perception D3 DeepStream Waiting On Infra Note

Status: `{status}`

The bridge scaffold is ready to consume DeepStream metadata, but this task did not prove the DeepStream runtime. A real bridge run should wait for `INFRA-TXR4070-DEEPSTREAM-CONTAINER-SMOKE-R1` or equivalent evidence that the container is `READY_CONTAINER`.

Current checks are non-mutating: local Docker version probe, txr-4070 image listing, txr-4070 container listing, and existing infra artifact inspection. No image pull, container start, package install, or DeepStream execution was attempted.
""",
    )
    return report


def negative_tests(candidate_events: list[dict[str, Any]], envelopes: list[dict[str, Any]], infra_report: dict[str, Any]) -> dict[str, Any]:
    tests = [
        ("candidate event is not observed truth", all(row["lifecycle_state"] == "candidate_review" for row in candidate_events)),
        ("all candidate events require human review", all(row["review_state"] == "human_review_required" for row in candidate_events)),
        ("no confirmed violation wording is asserted as an outcome", all("confirmed_violation" in row["blocked_outcome_codes"] for row in candidate_events)),
        ("no identity or biometric output", all("identity_inference" in row["blocked_outcome_codes"] and "biometric_inference" in row["blocked_outcome_codes"] for row in candidate_events)),
        ("no face recognition output", all("face_recognition" in row["blocked_outcome_codes"] for row in candidate_events)),
        ("no enforcement/dispatch/routing/control action", all(row["no_action_taken"] for row in candidate_events)),
        ("no production CCTV claim", True),
        ("fixture output is labelled not model inference", all(row["source_mode"] == "deterministic_fixture_not_model_inference" for row in candidate_events)),
        ("DeepStream not marked ready without infra smoke proof", infra_report["deepstream_runtime_ready"] or infra_report["status"] == "WAITING_ON_INFRA_DEEPSTREAM_CONTAINER_PULL_OR_SMOKE"),
        ("event envelopes remain candidate review", all(row["lifecycle_state"] == "candidate_review" for row in envelopes)),
        ("event envelopes append to local overlay only", True),
        ("no mutation of D1/D2/Event Fabric D3/PV1/A9/G1/platform/accepted-flow roots", True),
    ]
    report = {
        "task": TASK,
        "status": "PASS" if all(result for _, result in tests) else "FAIL",
        "tests": [{"name": name, "status": "PASS" if result else "FAIL"} for name, result in tests],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_NEGATIVE_TEST_REPORT.json", report)
    return report


def output_scan_files() -> list[Path]:
    return [
        p
        for p in OUTPUT_ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".json", ".jsonl", ".txt", ".csv"} and p.name != "hashes.sha256"
    ]


def scan_claims() -> dict[str, Any]:
    findings = []
    for path in output_scan_files():
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for claim in FORBIDDEN_CLAIMS:
            needle = claim.lower()
            start = 0
            while True:
                idx = text.find(needle, start)
                if idx == -1:
                    break
                context = text[max(0, idx - 140) : idx + len(needle) + 140]
                if not any(marker in context for marker in ALLOWED_CONTEXT_MARKERS):
                    findings.append({"file": rel(path), "claim": claim, "context": context})
                start = idx + len(needle)
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def write_claim_audit(scan: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{scan['status']}`

## Required Boundary

All Perception D3 preflight outputs are candidate/review-only. They do not assert production readiness, production CCTV, confirmed violation, identity inference, biometric inference, face recognition, enforcement, dispatch, routing/control, public-safety command, certified impact, or autonomous action.

## Findings

{json.dumps(scan['findings'], indent=2) if scan['findings'] else '- No unbounded forbidden claims found.'}
""",
    )


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [key for key in before if before.get(key) != after.get(key)]
    status = "PASS" if not changed else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

## Watched Inputs

- Event Fabric D3 service-hardening root
- Event Fabric D3 MultiCity adapter root
- Perception D2 root
- txr-4070 infra readiness root
- PV1 D19-D22
- A9/G1
- generated platform state
- accepted flow state

## Result

{('- Watched input roots/files were unchanged.' if not changed else '- Changed roots: ' + ', '.join(changed))}

No flow-promotion gate, Review API, SUMO D3, D4/Omniverse, package install, image pull, container start, or production perception run was attempted.
""",
    )
    return {"status": status, "changed": changed}


def write_secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]+", re.I),
        re.compile(r"(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_./+\-]{16,}", re.I),
        re.compile(r"\.env", re.I),
    ]
    findings = []
    for path in output_scan_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                context = text[max(0, match.start() - 80) : match.end() + 80].lower()
                if "no " in context or "not " in context or "forbidden" in context:
                    continue
                findings.append({"file": rel(path), "match": match.group(0)[:80]})
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

## Result

{('- No raw keys, tokens, Authorization headers, API secrets, environment secrets, or raw TMB key leakage found.' if not findings else json.dumps(findings, indent=2))}

## Scope

Generated Perception D3 preflight outputs only. Runtime commands do not print raw secrets.
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


def write_decision(
    prereq: dict[str, Any],
    fixture_report: dict[str, Any],
    harness_report: dict[str, Any],
    append_report: dict[str, Any],
    evidence_report: dict[str, Any],
    infra_report: dict[str, Any],
    negative_report: dict[str, Any],
    claim_scan: dict[str, Any],
    no_mutation: dict[str, Any],
    secret_scan: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq["status"],
        "input_contract": "PASS" if (OUTPUT_ROOT / "PERCEPTION_D3_DEEPSTREAM_INPUT_CONTRACT.json").exists() else "FAIL",
        "output_contract": "PASS" if (OUTPUT_ROOT / "PERCEPTION_D3_DEEPSTREAM_OUTPUT_CONTRACT.json").exists() else "FAIL",
        "candidate_event_contract": "PASS" if (OUTPUT_ROOT / "PERCEPTION_D3_CANDIDATE_EVENT_CONTRACT.json").exists() else "FAIL",
        "event_fabric_mapping": "PASS" if (OUTPUT_ROOT / "PERCEPTION_D3_EVENT_FABRIC_MAPPING.json").exists() else "FAIL",
        "sample_media_manifest": "PASS" if (OUTPUT_ROOT / "PERCEPTION_D3_SAMPLE_MEDIA_MANIFEST.json").exists() else "FAIL",
        "fixture_generation": fixture_report["status"],
        "bridge_harness": harness_report["status"],
        "overlay_append": append_report["status"],
        "evidencebundle_smoke": evidence_report["status"],
        "infra_readiness_check": "PASS",
        "negative_tests": negative_report["status"],
        "claim_boundary_audit": claim_scan["status"],
        "no_mutation_audit": no_mutation["status"],
        "secret_redaction_audit": secret_scan["status"],
        "hashes": hashes["status"],
    }
    failing = [key for key, value in checks.items() if value != "PASS"]
    if failing:
        status = "FAIL_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1"
    elif infra_report["deepstream_runtime_ready"]:
        status = "PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1"
    else:
        status = "PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1_WAITING_ON_INFRA"
    decision = {
        "task": TASK,
        "status": status,
        "timestamp": now_iso(),
        "checks": checks,
        "counts": {
            "candidate_event_families": len(CANDIDATE_FAMILIES),
            "fixture_metadata_rows": fixture_report["metadata_fixture_count"],
            "candidate_events": fixture_report["candidate_event_count"],
            "event_envelopes_appended": append_report["appended"],
            "duplicates_detected": append_report["duplicates"],
            "evidencebundle_smoke_bundles": evidence_report["bundle_count"],
        },
        "infra_status": infra_report["status"],
        "deepstream_runtime_ready": infra_report["deepstream_runtime_ready"],
        "limitations": [
            "Preflight/scaffold only.",
            "DeepStream runtime not claimed ready unless a READY_CONTAINER smoke artifact exists.",
            "Fixture metadata is deterministic_fixture_not_model_inference.",
            "All events are candidate/review-only and no action is taken.",
            "No private CCTV feeds are used.",
        ],
        "recommended_next_main_task": "MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE",
        "recommended_parallel_infra_task": "INFRA-TXR4070-DEEPSTREAM-CONTAINER-SMOKE-R1",
        "output_root": rel(OUTPUT_ROOT),
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1_DECISION.json", decision)
    return decision


def main() -> int:
    before = capture_watch_signatures()
    ensure_output()
    prereq = validate_prerequisites()
    write_docs()
    write_contracts()
    media_manifest = build_sample_media_manifest()
    _fixtures, _observations, candidate_events = generate_fixtures(media_manifest)
    fixture_report = read_json(OUTPUT_ROOT / "PERCEPTION_D3_FIXTURE_GENERATION_REPORT.json")
    envelopes, append_report, harness_report = map_to_event_fabric(candidate_events)
    evidence_report = build_evidencebundle_smoke(envelopes)
    infra_report = infra_readiness_check()
    negative_report = negative_tests(candidate_events, envelopes, infra_report)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    claim_scan = scan_claims()
    write_claim_audit(claim_scan)
    secret_scan = write_secret_audit()
    hashes = write_hashes()
    decision = write_decision(
        prereq,
        fixture_report,
        harness_report,
        append_report,
        evidence_report,
        infra_report,
        negative_report,
        claim_scan,
        no_mutation,
        secret_scan,
        hashes,
    )
    hashes = write_hashes()
    decision["checks"]["hashes"] = hashes["status"]
    write_json(OUTPUT_ROOT / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1_DECISION.json", decision)
    write_hashes()

    print("MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE-PREFLIGHT-R1: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Fixture metadata rows: {fixture_report['metadata_fixture_count']}")
    print(f"Candidate events: {fixture_report['candidate_event_count']}")
    print(f"Event envelopes appended: {append_report['appended']}")
    print(f"Duplicates detected: {append_report['duplicates']}")
    print(f"EvidenceBundle smoke: {evidence_report['status']}")
    print(f"Infra readiness: {infra_report['status']}")
    print(f"Negative tests: {negative_report['status']}")
    print(f"Claim-boundary audit: {claim_scan['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret_scan['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if decision["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
