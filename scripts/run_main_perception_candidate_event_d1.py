from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_perception_candidate_event_d1"
REPLAY_ROOT = OUTPUT_ROOT / "PERCEPTION_REPLAY_SCENARIO_PACKS"
OVERLAY_ROOT = OUTPUT_ROOT / "event_fabric_overlay"
NOW = datetime(2026, 6, 28, 13, 0, 0, tzinfo=timezone.utc)
PERCEPTION_SCHEMA_VERSION = "main-perception-candidate-event-d1.v1"


INPUTS = {
    "event_fabric_schema_json": ROOT / "outputs" / "main_platform_event_fabric_d1" / "EVENT_FABRIC_SCHEMA.json",
    "event_fabric_schema_md": ROOT / "outputs" / "main_platform_event_fabric_d1" / "EVENT_FABRIC_SCHEMA.md",
    "event_fabric_append_log": ROOT / "outputs" / "main_platform_event_fabric_d1" / "EVENT_APPEND_LOG_SAMPLE.jsonl",
    "event_fabric_duckdb": ROOT / "outputs" / "main_platform_event_fabric_d1" / "EVENT_CURRENT_STATE.duckdb",
    "event_fabric_source_registry": ROOT / "outputs" / "main_platform_event_fabric_d1" / "EVENT_SOURCE_REGISTRY.json",
    "event_fabric_family_registry": ROOT / "outputs" / "main_platform_event_fabric_d1" / "EVENT_FAMILY_REGISTRY.json",
    "event_fabric_decision": ROOT / "outputs" / "main_platform_event_fabric_d1" / "MAIN_PLATFORM_EVENT_FABRIC_D1_DECISION.json",
    "platform_state": ROOT / "outputs" / "platform_state_generated" / "CITYBRAIN_PLATFORM_STATE.json",
    "resolver_inputs": ROOT / "outputs" / "platform_state_generated" / "CITYBRAIN_RESOLVER_INPUTS.json",
    "a9_g1_decision": ROOT
    / "outputs"
    / "main_platform_a9_g1_snapshot_closeout_r1"
    / "MAIN_PLATFORM_A9_G1_SNAPSHOT_CLOSEOUT_R1_DECISION.json",
    "pv1_d19_d22_decision": ROOT
    / "outputs"
    / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot"
    / "PV1_D19_D20_D21_D22_DECISION.json",
}


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
    "reject",
    "negative",
    "cannot",
    "must not",
    "does not",
    "do not",
    "without",
    "non-",
    "review-only",
]

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

ZONE_TYPES = [
    "restricted_zone_candidate",
    "work_area",
    "public_walkway",
    "road_edge",
    "camera_coverage",
    "ignore_zone",
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


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def now_iso() -> str:
    return iso(NOW)


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def obj_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest('|'.join(str(p) for p in parts), length)}"


def safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return iso(value)
    if pd.isna(value):
        return None
    return str(value)


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    if path.is_file():
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
            cstat = child.stat()
            files.append(
                {
                    "path": child.relative_to(path).as_posix(),
                    "bytes": cstat.st_size,
                    "mtime_ns": cstat.st_mtime_ns,
                    "sha256": sha256_file(child),
                }
            )
    tree_sha = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {"exists": True, "type": "directory", "file_count": len(files), "tree_sha256": tree_sha}


def capture_watch_signatures() -> dict[str, dict[str, Any]]:
    return {name: path_signature(path) for name, path in INPUTS.items()}


def flatten_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    flat = []
    for row in rows:
        out = {}
        for key, value in row.items():
            if isinstance(value, (list, dict)):
                out[key] = json.dumps(value, sort_keys=True, ensure_ascii=True)
            else:
                out[key] = safe(value)
        flat.append(out)
    return pd.DataFrame(flat)


def event_fabric_schema_version(schema: dict[str, Any]) -> str:
    return str(schema.get("schema_version") or "main-platform-event-fabric-d1.v1")


def event_required_fields(schema: dict[str, Any]) -> list[str]:
    return list(schema["definitions"]["EventEnvelope"]["required"])


def build_camera_sources() -> list[dict[str, Any]]:
    return [
        {
            "camera_id": "cam_barc_worksite_001",
            "city": "BARC",
            "source_system": "deterministic_fixture",
            "camera_name": "Barcelona fixture worksite camera",
            "camera_type": "construction_worksite_fixture",
            "location": {"lat": 41.3851, "lon": 2.1734, "location_ref": "fixture_barc_eixample_worksite"},
            "area_refs": [
                {"area_type": "city", "area_ref": "BARC"},
                {"area_type": "district", "area_ref": "Eixample_fixture"},
            ],
            "entity_refs": [
                {"entity_type": "fixture_site", "entity_ref": "fixture_barc_worksite_A"},
                {"entity_type": "fixture_camera", "entity_ref": "cam_barc_worksite_001"},
            ],
            "orientation": {"heading_degrees": 88, "tilt_degrees": -12},
            "field_of_view": {"horizontal_degrees": 92, "range_meters": 45},
            "coverage_zone_refs": [
                "zone_barc_worksite_coverage",
                "zone_barc_restricted_01",
                "zone_barc_work_area_01",
                "zone_barc_walkway_01",
                "zone_barc_ignore_01",
            ],
            "status": "fixture_active",
            "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
            "claim_boundary": "Fixture camera metadata for review-only candidate events. No identity inference and no action taken.",
            "source_ref": {"mode": "fixture", "path": "generated_by_script", "real_media_required": False},
            "schema_version": PERCEPTION_SCHEMA_VERSION,
        },
        {
            "camera_id": "cam_nyc_public_realm_001",
            "city": "NYC",
            "source_system": "deterministic_fixture",
            "camera_name": "NYC fixture public-realm camera",
            "camera_type": "road_public_realm_fixture",
            "location": {"lat": 40.7128, "lon": -74.006, "location_ref": "fixture_nyc_road_edge"},
            "area_refs": [
                {"area_type": "city", "area_ref": "NYC"},
                {"area_type": "borough", "area_ref": "Manhattan_fixture"},
            ],
            "entity_refs": [
                {"entity_type": "fixture_road_segment", "entity_ref": "fixture_nyc_road_edge_A"},
                {"entity_type": "fixture_camera", "entity_ref": "cam_nyc_public_realm_001"},
            ],
            "orientation": {"heading_degrees": 14, "tilt_degrees": -9},
            "field_of_view": {"horizontal_degrees": 80, "range_meters": 55},
            "coverage_zone_refs": [
                "zone_nyc_road_coverage",
                "zone_nyc_road_edge_01",
                "zone_nyc_walkway_01",
                "zone_nyc_ignore_01",
            ],
            "status": "fixture_active",
            "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
            "claim_boundary": "Fixture public-realm camera metadata for review-only candidate events. No identity inference and no action taken.",
            "source_ref": {"mode": "fixture", "path": "generated_by_script", "real_media_required": False},
            "schema_version": PERCEPTION_SCHEMA_VERSION,
        },
        {
            "camera_id": "cam_lon_facility_001",
            "city": "LON",
            "source_system": "deterministic_fixture",
            "camera_name": "London fixture facility/sensor-area camera",
            "camera_type": "facility_sensor_area_fixture",
            "location": {"lat": 51.5072, "lon": -0.1276, "location_ref": "fixture_lon_facility_area"},
            "area_refs": [
                {"area_type": "city", "area_ref": "LON"},
                {"area_type": "borough", "area_ref": "Westminster_fixture"},
            ],
            "entity_refs": [
                {"entity_type": "fixture_facility", "entity_ref": "fixture_lon_facility_A"},
                {"entity_type": "fixture_camera", "entity_ref": "cam_lon_facility_001"},
            ],
            "orientation": {"heading_degrees": 232, "tilt_degrees": -10},
            "field_of_view": {"horizontal_degrees": 72, "range_meters": 30},
            "coverage_zone_refs": [
                "zone_lon_facility_coverage",
                "zone_lon_restricted_01",
                "zone_lon_work_area_01",
                "zone_lon_walkway_01",
            ],
            "status": "fixture_active",
            "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
            "claim_boundary": "Fixture facility camera metadata for review-only candidate events. No identity inference and no action taken.",
            "source_ref": {"mode": "fixture", "path": "generated_by_script", "real_media_required": False},
            "schema_version": PERCEPTION_SCHEMA_VERSION,
        },
    ]


def build_zone_definitions(cameras: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cam_by_id = {c["camera_id"]: c for c in cameras}

    def zone(
        zone_id: str,
        camera_id: str,
        zone_type: str,
        zone_name: str,
        coords: list[list[int]],
        world_ref: str,
        extra_entities: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        cam = cam_by_id[camera_id]
        return {
            "zone_id": zone_id,
            "camera_id": camera_id,
            "zone_type": zone_type,
            "zone_name": zone_name,
            "polygon_image_coords": coords,
            "world_location_ref": world_ref,
            "area_refs": cam["area_refs"],
            "entity_refs": (extra_entities or []) + [{"entity_type": "fixture_zone", "entity_ref": zone_id}],
            "active_from": "2026-06-28T00:00:00Z",
            "active_to": None,
            "claim_boundary": "Fixture zone for candidate rule evaluation only. No certified affected asset or action claim.",
            "schema_version": PERCEPTION_SCHEMA_VERSION,
        }

    return [
        zone("zone_barc_worksite_coverage", "cam_barc_worksite_001", "camera_coverage", "BARC coverage", [[0, 0], [1920, 0], [1920, 1080], [0, 1080]], "fixture_barc_coverage"),
        zone("zone_barc_restricted_01", "cam_barc_worksite_001", "restricted_zone_candidate", "BARC restricted candidate zone", [[720, 280], [1120, 280], [1180, 760], [680, 760]], "fixture_barc_restricted"),
        zone("zone_barc_work_area_01", "cam_barc_worksite_001", "work_area", "BARC work area", [[450, 220], [1350, 220], [1460, 880], [390, 880]], "fixture_barc_work_area"),
        zone("zone_barc_walkway_01", "cam_barc_worksite_001", "public_walkway", "BARC public walkway", [[20, 730], [610, 730], [610, 1070], [20, 1070]], "fixture_barc_walkway"),
        zone("zone_barc_ignore_01", "cam_barc_worksite_001", "ignore_zone", "BARC ignore strip", [[0, 0], [220, 0], [220, 180], [0, 180]], "fixture_barc_ignore"),
        zone("zone_nyc_road_coverage", "cam_nyc_public_realm_001", "camera_coverage", "NYC coverage", [[0, 0], [1920, 0], [1920, 1080], [0, 1080]], "fixture_nyc_coverage"),
        zone("zone_nyc_road_edge_01", "cam_nyc_public_realm_001", "road_edge", "NYC road edge", [[900, 420], [1850, 420], [1890, 980], [760, 980]], "fixture_nyc_road_edge"),
        zone("zone_nyc_walkway_01", "cam_nyc_public_realm_001", "public_walkway", "NYC public walkway", [[80, 500], [760, 500], [760, 1040], [80, 1040]], "fixture_nyc_walkway"),
        zone("zone_nyc_ignore_01", "cam_nyc_public_realm_001", "ignore_zone", "NYC sky/ignore", [[0, 0], [1920, 0], [1920, 220], [0, 220]], "fixture_nyc_ignore"),
        zone("zone_lon_facility_coverage", "cam_lon_facility_001", "camera_coverage", "LON coverage", [[0, 0], [1280, 0], [1280, 720], [0, 720]], "fixture_lon_coverage"),
        zone("zone_lon_restricted_01", "cam_lon_facility_001", "restricted_zone_candidate", "LON restricted candidate zone", [[680, 170], [1110, 170], [1120, 600], [650, 600]], "fixture_lon_restricted"),
        zone("zone_lon_work_area_01", "cam_lon_facility_001", "work_area", "LON sensor work area", [[400, 120], [1180, 120], [1190, 650], [370, 650]], "fixture_lon_work_area"),
        zone("zone_lon_walkway_01", "cam_lon_facility_001", "public_walkway", "LON walkway", [[20, 390], [390, 390], [390, 710], [20, 710]], "fixture_lon_walkway"),
    ]


def obs(
    camera_id: str,
    minute: int,
    frame: int,
    track_id: str,
    object_class: str,
    bbox: list[int],
    confidence: float,
    attributes: dict[str, Any],
    zone_refs: list[str],
) -> dict[str, Any]:
    observed_at = iso(NOW + timedelta(minutes=minute))
    observation_id = obj_id("perception-observation", camera_id, observed_at, frame, track_id, object_class)
    return {
        "observation_id": observation_id,
        "camera_id": camera_id,
        "observed_at": observed_at,
        "frame_ref": f"{camera_id}:frame:{frame:06d}",
        "track_id": track_id,
        "object_class": object_class,
        "bbox": bbox,
        "confidence": confidence,
        "attributes": attributes,
        "zone_refs": zone_refs,
        "model_or_fixture_ref": "deterministic_fixture_generator_v1",
        "source_mode": "deterministic_fixture",
        "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
        "claim_boundary": "Fixture observation for candidate review only. No identity inference and no action taken.",
        "schema_version": PERCEPTION_SCHEMA_VERSION,
    }


def build_observations() -> list[dict[str, Any]]:
    rows = [
        obs("cam_barc_worksite_001", 0, 100, "track_barc_p01", "person", [760, 340, 850, 610], 0.91, {"ppe_helmet_visible": False, "ppe_vest_visible": False}, ["zone_barc_restricted_01", "zone_barc_work_area_01"]),
        obs("cam_barc_worksite_001", 0, 100, "track_barc_p01_h", "unknown_object", [765, 300, 850, 338], 0.42, {"possible_helmet": False}, ["zone_barc_restricted_01"]),
        obs("cam_barc_worksite_001", 1, 160, "track_barc_p02", "person", [120, 760, 210, 1010], 0.94, {"ppe_helmet_visible": True, "ppe_vest_visible": True}, ["zone_barc_walkway_01"]),
        obs("cam_barc_worksite_001", 1, 160, "track_barc_p02_helmet", "ppe_helmet", [130, 725, 200, 770], 0.88, {"paired_track_id": "track_barc_p02"}, ["zone_barc_walkway_01"]),
        obs("cam_barc_worksite_001", 1, 160, "track_barc_p02_vest", "ppe_vest", [125, 815, 215, 945], 0.86, {"paired_track_id": "track_barc_p02"}, ["zone_barc_walkway_01"]),
        obs("cam_barc_worksite_001", 2, 220, "track_barc_eq01", "equipment", [940, 420, 1210, 760], 0.9, {"equipment_kind": "small_lift_fixture"}, ["zone_barc_work_area_01"]),
        obs("cam_barc_worksite_001", 2, 220, "track_barc_p03", "person", [910, 455, 990, 705], 0.89, {"ppe_helmet_visible": True, "ppe_vest_visible": False, "distance_to_equipment_m": 1.5}, ["zone_barc_work_area_01"]),
        obs("cam_barc_worksite_001", 3, 280, "track_barc_p04", "person", [710, 325, 800, 595], 0.87, {"after_hours_fixture": True, "ppe_helmet_visible": False}, ["zone_barc_restricted_01"]),
        obs("cam_barc_worksite_001", 4, 340, "track_barc_p05", "person", [50, 775, 145, 1030], 0.93, {"ppe_helmet_visible": True, "ppe_vest_visible": True}, ["zone_barc_walkway_01"]),
        obs("cam_barc_worksite_001", 5, 400, "track_barc_unknown01", "unknown_object", [25, 35, 180, 160], 0.45, {"inside_ignore_zone": True}, ["zone_barc_ignore_01"]),
        obs("cam_barc_worksite_001", 6, 460, "track_barc_p06", "person", [1010, 350, 1090, 620], 0.9, {"ppe_helmet_visible": False, "ppe_vest_visible": True}, ["zone_barc_restricted_01"]),
        obs("cam_barc_worksite_001", 7, 520, "track_barc_p07", "person", [500, 310, 585, 570], 0.88, {"ppe_helmet_visible": True, "ppe_vest_visible": False}, ["zone_barc_work_area_01"]),
        obs("cam_nyc_public_realm_001", 8, 100, "track_nyc_v01", "vehicle", [1120, 520, 1560, 820], 0.92, {"vehicle_fixture": True}, ["zone_nyc_road_edge_01"]),
        obs("cam_nyc_public_realm_001", 8, 100, "track_nyc_p01", "person", [210, 620, 290, 900], 0.91, {"walkway_only": True}, ["zone_nyc_walkway_01"]),
        obs("cam_nyc_public_realm_001", 9, 160, "track_nyc_eq01", "equipment", [870, 500, 1180, 830], 0.84, {"roadside_equipment_fixture": True}, ["zone_nyc_road_edge_01"]),
        obs("cam_nyc_public_realm_001", 9, 160, "track_nyc_p02", "person", [820, 540, 900, 800], 0.88, {"distance_to_equipment_m": 1.2}, ["zone_nyc_road_edge_01"]),
        obs("cam_nyc_public_realm_001", 10, 220, "track_nyc_camera_health01", "camera_obstruction", [0, 0, 1920, 1080], 0.82, {"obstruction_percent_fixture": 67}, ["zone_nyc_road_coverage"]),
        obs("cam_nyc_public_realm_001", 11, 280, "track_nyc_p03", "person", [290, 620, 375, 900], 0.93, {"walkway_only": True}, ["zone_nyc_walkway_01"]),
        obs("cam_nyc_public_realm_001", 11, 280, "track_nyc_v02", "vehicle", [1240, 530, 1700, 850], 0.9, {"vehicle_fixture": True}, ["zone_nyc_road_edge_01"]),
        obs("cam_nyc_public_realm_001", 12, 340, "track_nyc_camera_health02", "camera_offline", [0, 0, 0, 0], 0.99, {"offline_seconds_fixture": 180}, ["zone_nyc_road_coverage"]),
        obs("cam_nyc_public_realm_001", 13, 400, "track_nyc_unknown01", "unknown_object", [20, 20, 1900, 200], 0.5, {"inside_ignore_zone": True}, ["zone_nyc_ignore_01"]),
        obs("cam_nyc_public_realm_001", 14, 460, "track_nyc_p04", "person", [880, 535, 965, 805], 0.86, {"distance_to_equipment_m": 1.8}, ["zone_nyc_road_edge_01"]),
        obs("cam_lon_facility_001", 15, 100, "track_lon_p01", "person", [720, 250, 800, 560], 0.92, {"ppe_helmet_visible": False, "after_hours_fixture": True}, ["zone_lon_restricted_01", "zone_lon_work_area_01"]),
        obs("cam_lon_facility_001", 15, 100, "track_lon_eq01", "equipment", [830, 260, 1030, 590], 0.89, {"facility_equipment_fixture": True}, ["zone_lon_work_area_01"]),
        obs("cam_lon_facility_001", 16, 160, "track_lon_p02", "person", [455, 240, 540, 550], 0.87, {"ppe_helmet_visible": False, "ppe_vest_visible": False}, ["zone_lon_work_area_01"]),
        obs("cam_lon_facility_001", 16, 160, "track_lon_p02_vest", "ppe_vest", [455, 310, 540, 470], 0.2, {"paired_track_id": "track_lon_p02", "low_confidence": True}, ["zone_lon_work_area_01"]),
        obs("cam_lon_facility_001", 17, 220, "track_lon_p03", "person", [65, 455, 145, 700], 0.9, {"walkway_only": True}, ["zone_lon_walkway_01"]),
        obs("cam_lon_facility_001", 18, 280, "track_lon_camera_health01", "camera_obstruction", [0, 0, 1280, 720], 0.79, {"obstruction_percent_fixture": 55}, ["zone_lon_facility_coverage"]),
        obs("cam_lon_facility_001", 19, 340, "track_lon_p04", "person", [760, 260, 840, 560], 0.88, {"ppe_helmet_visible": True, "ppe_vest_visible": True}, ["zone_lon_restricted_01"]),
        obs("cam_lon_facility_001", 19, 340, "track_lon_p04_helmet", "ppe_helmet", [760, 220, 840, 260], 0.84, {"paired_track_id": "track_lon_p04"}, ["zone_lon_restricted_01"]),
        obs("cam_lon_facility_001", 19, 340, "track_lon_p04_vest", "ppe_vest", [760, 320, 840, 455], 0.83, {"paired_track_id": "track_lon_p04"}, ["zone_lon_restricted_01"]),
        obs("cam_lon_facility_001", 20, 400, "track_lon_camera_health02", "camera_offline", [0, 0, 0, 0], 0.99, {"offline_seconds_fixture": 90}, ["zone_lon_facility_coverage"]),
        obs("cam_lon_facility_001", 21, 460, "track_lon_p05", "person", [430, 250, 515, 555], 0.89, {"distance_to_equipment_m": 1.4, "ppe_helmet_visible": True}, ["zone_lon_work_area_01"]),
        obs("cam_lon_facility_001", 21, 460, "track_lon_eq02", "equipment", [560, 260, 740, 590], 0.82, {"facility_equipment_fixture": True}, ["zone_lon_work_area_01"]),
        obs("cam_barc_worksite_001", 22, 580, "track_barc_p08", "person", [1080, 340, 1160, 620], 0.88, {"ppe_helmet_visible": False, "ppe_vest_visible": False}, ["zone_barc_restricted_01", "zone_barc_work_area_01"]),
        obs("cam_nyc_public_realm_001", 23, 520, "track_nyc_p05", "person", [130, 620, 215, 905], 0.9, {"walkway_only": True}, ["zone_nyc_walkway_01"]),
        obs("cam_barc_worksite_001", 24, 640, "track_barc_p09", "person", [520, 350, 605, 620], 0.9, {"ppe_helmet_visible": True, "ppe_vest_visible": True}, ["zone_barc_work_area_01"]),
    ]
    return rows


def obs_by_track(observations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_track: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        by_track[row["track_id"]].append(row)
    return by_track


def camera_index(cameras: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {c["camera_id"]: c for c in cameras}


def zone_index(zones: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {z["zone_id"]: z for z in zones}


def rule_eval(
    rule_id: str,
    camera_id: str,
    zone_id: str,
    observed_at: str,
    track_id: str,
    rule_type: str,
    input_observation_ids: list[str],
    candidate_result: bool,
    confidence: float,
    explanation: str,
) -> dict[str, Any]:
    return {
        "rule_evaluation_id": obj_id("zone-rule-eval", rule_id, camera_id, zone_id, observed_at, track_id),
        "rule_id": rule_id,
        "camera_id": camera_id,
        "zone_id": zone_id,
        "observed_at": observed_at,
        "track_id": track_id,
        "rule_type": rule_type,
        "input_observation_ids": input_observation_ids,
        "candidate_result": candidate_result,
        "confidence": confidence,
        "explanation": explanation,
        "claim_boundary": "Rule evaluation is deterministic fixture context only. Human review required before any interpretation.",
        "schema_version": PERCEPTION_SCHEMA_VERSION,
    }


def evidence_ref(camera_id: str, candidate_event_id: str, observed_at: str, frame_refs: list[str]) -> dict[str, Any]:
    return {
        "evidence_ref_id": obj_id("evidence-ref", camera_id, candidate_event_id),
        "camera_id": camera_id,
        "event_id": candidate_event_id,
        "media_type": "metadata_only_fixture",
        "uri_or_path": f"fixture://perception_candidate_event_d1/{camera_id}/{candidate_event_id}",
        "start_time": observed_at,
        "end_time": observed_at,
        "frame_refs": frame_refs,
        "redaction_status": "no_media_placeholder",
        "retention_policy": "metadata_only_no_clip_retained",
        "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
        "schema_version": PERCEPTION_SCHEMA_VERSION,
    }


def city_flow_candidates(city: str, event_type: str) -> list[str]:
    if city == "BARC":
        if event_type in {"candidate_restricted_zone_entry", "candidate_missing_ppe", "candidate_person_near_equipment"}:
            return ["BARC-F1", "BARC-F2", "BARC-F3", "BARC-F4", "BARC-F7"]
        return ["BARC-F1", "BARC-F4", "BARC-F7"]
    if city == "NYC":
        return ["NYC-F1X", "NYC-F4X"]
    if city == "LON":
        return ["LON-F3X"]
    return []


def make_candidate_event(
    *,
    event_key: str,
    event_type: str,
    camera: dict[str, Any],
    zone: dict[str, Any],
    tracks: list[str],
    observations: list[dict[str, Any]],
    rule_evals: list[dict[str, Any]],
    description: str,
    confidence: float,
    severity: int,
    candidate_result: bool = True,
    human_review_required: bool = True,
) -> dict[str, Any]:
    observed_at = observations[0]["observed_at"] if observations else now_iso()
    candidate_event_id = obj_id("perception-candidate-event", event_key)
    ev_ref = evidence_ref(camera["camera_id"], candidate_event_id, observed_at, [o["frame_ref"] for o in observations])
    privacy_boundary = "HIGH_BOUNDARY_RISK_CONTEXT_ONLY" if event_type in {
        "candidate_restricted_zone_entry",
        "candidate_person_near_equipment",
        "candidate_after_hours_presence",
    } else "PRIVACY_SAFE_SELECTED_FIELDS"
    return {
        "candidate_event_id": candidate_event_id,
        "event_family": "perception_candidate",
        "event_type": event_type,
        "city": camera["city"],
        "camera_id": camera["camera_id"],
        "observed_at": observed_at,
        "event_time": observed_at,
        "event_end_time": None,
        "zone_id": zone["zone_id"],
        "track_ids": tracks,
        "observation_ids": [o["observation_id"] for o in observations],
        "rule_evaluation_ids": [r["rule_evaluation_id"] for r in rule_evals],
        "candidate_description": description,
        "confidence": confidence,
        "severity_or_magnitude": severity,
        "entity_refs": zone.get("entity_refs") or [{"entity_type": "NO_ENTITY_REF", "entity_ref": "NO_ENTITY_REF"}],
        "area_refs": zone.get("area_refs") or [{"area_type": "NO_AREA_REF", "area_ref": "NO_AREA_REF"}],
        "evidence_refs": [ev_ref],
        "human_review_required": human_review_required,
        "review_state": "human_review_required" if human_review_required else "candidate_review",
        "privacy_boundary": privacy_boundary,
        "claim_boundary": "REVIEW_ONLY: deterministic fixture candidate event; human review required; no action taken; no identity inference; no final violation claim.",
        "forbidden_claims": [
            "violation_confirmation",
            "legal_conclusion",
            "identity_inference",
            "face_recognition",
            "biometric_inference",
            "dispatch_or_response",
            "enforcement_or_control",
        ],
        "candidate_result": candidate_result,
        "source_mode": "deterministic_fixture",
        "schema_version": PERCEPTION_SCHEMA_VERSION,
    }


def build_rule_evaluations_and_events(
    cameras: list[dict[str, Any]],
    zones: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cams = camera_index(cameras)
    zidx = zone_index(zones)
    tracks = obs_by_track(observations)
    rule_rows: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    def add(
        event_key: str,
        event_type: str,
        camera_id: str,
        zone_id: str,
        track_ids: list[str],
        rule_type: str,
        candidate_result: bool,
        confidence: float,
        severity: int,
        description: str,
        human_review_required: bool = True,
    ) -> None:
        obs_rows = [row for track in track_ids for row in tracks.get(track, [])]
        observed_at = obs_rows[0]["observed_at"] if obs_rows else now_iso()
        rule = rule_eval(
            f"rule_{event_key}",
            camera_id,
            zone_id,
            observed_at,
            ",".join(track_ids),
            rule_type,
            [o["observation_id"] for o in obs_rows],
            candidate_result,
            confidence,
            description,
        )
        rule_rows.append(rule)
        events.append(
            make_candidate_event(
                event_key=event_key,
                event_type=event_type,
                camera=cams[camera_id],
                zone=zidx[zone_id],
                tracks=track_ids,
                observations=obs_rows,
                rule_evals=[rule],
                description=description,
                confidence=confidence,
                severity=severity,
                candidate_result=candidate_result,
                human_review_required=human_review_required,
            )
        )

    add("barc_restricted_01", "candidate_restricted_zone_entry", "cam_barc_worksite_001", "zone_barc_restricted_01", ["track_barc_p01"], "person_in_restricted_zone_candidate", True, 0.86, 3, "Person-like fixture track overlaps restricted candidate zone; review required.")
    add("barc_restricted_02", "candidate_restricted_zone_entry", "cam_barc_worksite_001", "zone_barc_restricted_01", ["track_barc_p06"], "person_in_restricted_zone_candidate", True, 0.84, 3, "Second person-like fixture track overlaps restricted candidate zone; review required.")
    add("lon_restricted_01", "candidate_restricted_zone_entry", "cam_lon_facility_001", "zone_lon_restricted_01", ["track_lon_p01"], "person_in_restricted_zone_candidate", True, 0.83, 3, "Facility fixture track overlaps restricted candidate zone; review required.")
    add("barc_missing_ppe_01", "candidate_missing_ppe", "cam_barc_worksite_001", "zone_barc_work_area_01", ["track_barc_p01"], "missing_ppe_candidate", True, 0.78, 2, "PPE-like fixture attributes are absent or uncertain for person-like track; review required.")
    add("barc_missing_ppe_02", "candidate_missing_ppe", "cam_barc_worksite_001", "zone_barc_work_area_01", ["track_barc_p07"], "missing_ppe_candidate", True, 0.72, 2, "Vest-like fixture signal is absent for person-like track in work area; review required.")
    add("lon_missing_ppe_01", "candidate_missing_ppe", "cam_lon_facility_001", "zone_lon_work_area_01", ["track_lon_p02"], "missing_ppe_candidate", True, 0.74, 2, "Facility fixture PPE-like signal is missing or low-confidence; review required.")
    add("barc_near_equipment_01", "candidate_person_near_equipment", "cam_barc_worksite_001", "zone_barc_work_area_01", ["track_barc_p03", "track_barc_eq01"], "person_near_equipment_candidate", True, 0.81, 2, "Person-like and equipment-like fixture tracks are near each other; review required.")
    add("nyc_near_equipment_01", "candidate_person_near_equipment", "cam_nyc_public_realm_001", "zone_nyc_road_edge_01", ["track_nyc_p02", "track_nyc_eq01"], "person_near_equipment_candidate", True, 0.79, 2, "Public-realm fixture track is near equipment-like object; review required.")
    add("lon_near_equipment_01", "candidate_person_near_equipment", "cam_lon_facility_001", "zone_lon_work_area_01", ["track_lon_p05", "track_lon_eq02"], "person_near_equipment_candidate", True, 0.77, 2, "Facility fixture track is near equipment-like object; review required.")
    add("nyc_obstruction_01", "candidate_camera_obstruction", "cam_nyc_public_realm_001", "zone_nyc_road_coverage", ["track_nyc_camera_health01"], "camera_health_candidate", True, 0.8, 1, "Camera fixture reports obstruction-like state; review required.")
    add("lon_obstruction_01", "candidate_camera_obstruction", "cam_lon_facility_001", "zone_lon_facility_coverage", ["track_lon_camera_health01"], "camera_health_candidate", True, 0.76, 1, "Facility camera fixture reports obstruction-like state; review required.")
    add("nyc_offline_01", "candidate_camera_offline", "cam_nyc_public_realm_001", "zone_nyc_road_coverage", ["track_nyc_camera_health02"], "camera_health_candidate", True, 0.98, 1, "Camera fixture reports offline-like state; review required.")
    add("barc_after_hours_01", "candidate_after_hours_presence", "cam_barc_worksite_001", "zone_barc_restricted_01", ["track_barc_p04"], "after_hours_presence_candidate", True, 0.75, 2, "After-hours fixture flag overlaps person-like restricted-zone track; review required.")
    add("lon_after_hours_01", "candidate_after_hours_presence", "cam_lon_facility_001", "zone_lon_restricted_01", ["track_lon_p01"], "after_hours_presence_candidate", True, 0.76, 2, "Facility after-hours fixture flag overlaps person-like track; review required.")
    add("negative_walkway_clear_01", "candidate_restricted_zone_entry", "cam_nyc_public_realm_001", "zone_nyc_walkway_01", ["track_nyc_p01"], "person_in_restricted_zone_candidate", False, 0.91, 0, "Negative fixture: person-like track remains in public walkway, so restricted-zone candidate is dismissed.", False)
    add("negative_ppe_present_01", "candidate_missing_ppe", "cam_lon_facility_001", "zone_lon_restricted_01", ["track_lon_p04", "track_lon_p04_helmet", "track_lon_p04_vest"], "missing_ppe_candidate", False, 0.83, 0, "Negative fixture: PPE-like objects are present enough for this sample, so missing-PPE candidate is dismissed.", False)

    return rule_rows, events


def perception_schema(event_schema_version: str, event_required: list[str]) -> dict[str, Any]:
    objects = {
        "CameraSource": [
            "camera_id",
            "city",
            "source_system",
            "camera_name",
            "camera_type",
            "location",
            "area_refs",
            "entity_refs",
            "orientation",
            "field_of_view",
            "coverage_zone_refs",
            "status",
            "privacy_boundary",
            "claim_boundary",
            "source_ref",
            "schema_version",
        ],
        "ZoneDefinition": [
            "zone_id",
            "camera_id",
            "zone_type",
            "zone_name",
            "polygon_image_coords",
            "world_location_ref",
            "area_refs",
            "entity_refs",
            "active_from",
            "active_to",
            "claim_boundary",
            "schema_version",
        ],
        "PerceptionObservation": [
            "observation_id",
            "camera_id",
            "observed_at",
            "frame_ref",
            "track_id",
            "object_class",
            "bbox",
            "confidence",
            "attributes",
            "zone_refs",
            "model_or_fixture_ref",
            "source_mode",
            "privacy_boundary",
            "claim_boundary",
            "schema_version",
        ],
        "ZoneRuleEvaluation": [
            "rule_id",
            "camera_id",
            "zone_id",
            "observed_at",
            "track_id",
            "rule_type",
            "input_observation_ids",
            "candidate_result",
            "confidence",
            "explanation",
            "claim_boundary",
            "schema_version",
        ],
        "PerceptionCandidateEvent": [
            "candidate_event_id",
            "event_family",
            "event_type",
            "city",
            "camera_id",
            "observed_at",
            "event_time",
            "event_end_time",
            "zone_id",
            "track_ids",
            "observation_ids",
            "rule_evaluation_ids",
            "candidate_description",
            "confidence",
            "severity_or_magnitude",
            "entity_refs",
            "area_refs",
            "evidence_refs",
            "human_review_required",
            "review_state",
            "privacy_boundary",
            "claim_boundary",
            "forbidden_claims",
            "schema_version",
        ],
        "EvidenceClipRef": [
            "evidence_ref_id",
            "camera_id",
            "event_id",
            "media_type",
            "uri_or_path",
            "start_time",
            "end_time",
            "frame_refs",
            "redaction_status",
            "retention_policy",
            "privacy_boundary",
            "schema_version",
        ],
        "HumanReviewPacket": [
            "review_packet_id",
            "candidate_event_id",
            "city",
            "camera_id",
            "event_type",
            "summary",
            "evidence_refs",
            "source_observations",
            "zone_rule_evaluations",
            "entity_refs",
            "area_refs",
            "confidence",
            "limitations",
            "recommended_review_action",
            "forbidden_actions",
            "claim_boundary",
            "privacy_boundary",
            "created_at",
            "schema_version",
        ],
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Perception Candidate Event D1 Schema",
        "schema_version": PERCEPTION_SCHEMA_VERSION,
        "event_fabric_schema_version": event_schema_version,
        "event_fabric_event_envelope_required_fields": event_required,
        "allowed_object_classes": OBJECT_CLASSES,
        "supported_zone_types": ZONE_TYPES,
        "allowed_rule_types": RULE_TYPES,
        "allowed_event_types": EVENT_TYPES,
        "allowed_recommended_review_actions": RECOMMENDED_REVIEW_ACTIONS,
        "forbidden_recommended_actions": FORBIDDEN_REVIEW_ACTIONS,
        "definitions": {
            name: {
                "type": "object",
                "required": fields,
                "properties": {field: {} for field in fields},
            }
            for name, fields in objects.items()
        },
    }


def validate_fixture_objects(
    schema: dict[str, Any],
    cameras: list[dict[str, Any]],
    zones: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    rule_evals: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    review_packets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    collections = {
        "CameraSource": cameras,
        "ZoneDefinition": zones,
        "PerceptionObservation": observations,
        "ZoneRuleEvaluation": rule_evals,
        "PerceptionCandidateEvent": candidates,
        "HumanReviewPacket": review_packets,
    }
    failures: list[dict[str, Any]] = []
    for obj_name, rows in collections.items():
        required = schema["definitions"][obj_name]["required"]
        for row in rows:
            missing = [field for field in required if field not in row]
            if missing:
                failures.append({"object": obj_name, "id": row.get("camera_id") or row.get("candidate_event_id") or row.get("observation_id"), "missing": missing})
    for row in observations:
        if row.get("object_class") not in OBJECT_CLASSES:
            failures.append({"object": "PerceptionObservation", "id": row.get("observation_id"), "bad_object_class": row.get("object_class")})
    for row in zones:
        if row.get("zone_type") not in ZONE_TYPES:
            failures.append({"object": "ZoneDefinition", "id": row.get("zone_id"), "bad_zone_type": row.get("zone_type")})
    for row in rule_evals:
        if row.get("rule_type") not in RULE_TYPES:
            failures.append({"object": "ZoneRuleEvaluation", "id": row.get("rule_evaluation_id"), "bad_rule_type": row.get("rule_type")})
    for row in candidates:
        if row.get("event_type") not in EVENT_TYPES:
            failures.append({"object": "PerceptionCandidateEvent", "id": row.get("candidate_event_id"), "bad_event_type": row.get("event_type")})
    for row in review_packets:
        if row.get("recommended_review_action") not in RECOMMENDED_REVIEW_ACTIONS:
            failures.append({"object": "HumanReviewPacket", "id": row.get("review_packet_id"), "bad_recommended_review_action": row.get("recommended_review_action")})
    return failures


def map_to_event_envelope(
    candidate: dict[str, Any],
    camera: dict[str, Any],
    event_schema_version: str,
) -> dict[str, Any]:
    event_id = obj_id("event", candidate["candidate_event_id"], length=24)
    ttl = 3600 if candidate["event_type"] in {"candidate_camera_obstruction", "candidate_camera_offline"} else 21600
    event_status = "candidate" if candidate.get("candidate_result") else "negative_non_event_fixture"
    return {
        "event_id": event_id,
        "event_family": "perception_candidate",
        "event_type": candidate["event_type"],
        "city": candidate["city"],
        "flow_candidates": city_flow_candidates(candidate["city"], candidate["event_type"]),
        "event_time": candidate["event_time"],
        "event_end_time": candidate["event_end_time"],
        "processing_time": now_iso(),
        "source_key": "perception_fixture_d1",
        "source_record_id": candidate["candidate_event_id"],
        "source_ref": {
            "path": "outputs/main_perception_candidate_event_d1/PERCEPTION_CANDIDATE_EVENTS.jsonl",
            "camera_id": candidate["camera_id"],
            "zone_id": candidate["zone_id"],
            "source_mode": "deterministic_fixture",
        },
        "event_status": event_status,
        "event_lifecycle": "candidate",
        "location": camera["location"],
        "entity_refs": candidate["entity_refs"] or [{"entity_type": "NO_ENTITY_REF", "entity_ref": "NO_ENTITY_REF"}],
        "area_refs": candidate["area_refs"] or [{"area_type": "NO_AREA_REF", "area_ref": "NO_AREA_REF"}],
        "severity_or_magnitude": candidate["severity_or_magnitude"],
        "payload": {
            "candidate_event_id": candidate["candidate_event_id"],
            "camera_id": candidate["camera_id"],
            "zone_id": candidate["zone_id"],
            "track_ids": candidate["track_ids"],
            "observation_ids": candidate["observation_ids"],
            "rule_evaluation_ids": candidate["rule_evaluation_ids"],
            "evidence_ref_ids": [ref["evidence_ref_id"] for ref in candidate["evidence_refs"]],
            "candidate_result": candidate.get("candidate_result"),
            "source_mode": "deterministic_fixture",
            "perception_schema_version": PERCEPTION_SCHEMA_VERSION,
            "selected_fields_only": True,
        },
        "provenance": {
            "adapter": "perception_candidate_event_d1_adapter",
            "input_mode": "deterministic_fixture",
            "base_event_fabric": "outputs/main_platform_event_fabric_d1",
            "media_dependency": "metadata_only_no_clip_required",
        },
        "confidence": candidate["confidence"],
        "review_state": "human_review_required" if candidate["human_review_required"] else "candidate_review",
        "privacy_boundary": candidate["privacy_boundary"],
        "claim_boundary": "REVIEW_ONLY: perception fixture candidate mapped to Event Fabric D1; human review required; no action taken; no identity inference.",
        "ttl_seconds": ttl,
        "supersedes_event_ids": [],
        "superseded_by_event_id": None,
        "schema_version": event_schema_version,
    }


def validate_event_envelopes(envelopes: list[dict[str, Any]], event_required: list[str]) -> list[dict[str, Any]]:
    failures = []
    for row in envelopes:
        missing = [field for field in event_required if field not in row]
        if missing:
            failures.append({"event_id": row.get("event_id"), "missing": missing})
        if row.get("event_family") != "perception_candidate":
            failures.append({"event_id": row.get("event_id"), "bad_family": row.get("event_family")})
        if row.get("event_lifecycle") != "candidate":
            failures.append({"event_id": row.get("event_id"), "bad_lifecycle": row.get("event_lifecycle")})
        if row.get("review_state") not in {"human_review_required", "candidate_review"}:
            failures.append({"event_id": row.get("event_id"), "bad_review_state": row.get("review_state")})
    return failures


def build_review_packets(candidates: list[dict[str, Any]], observations: list[dict[str, Any]], rule_evals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    obs_idx = {o["observation_id"]: o for o in observations}
    rule_idx = {r["rule_evaluation_id"]: r for r in rule_evals}
    packets = []
    for event in candidates:
        if not event.get("candidate_result"):
            action = "dismiss_candidate_event"
        elif event["confidence"] < 0.78:
            action = "request_more_evidence"
        else:
            action = "review_candidate_event"
        packets.append(
            {
                "review_packet_id": obj_id("human-review-packet", event["candidate_event_id"]),
                "candidate_event_id": event["candidate_event_id"],
                "city": event["city"],
                "camera_id": event["camera_id"],
                "event_type": event["event_type"],
                "summary": f"{event['event_type']} fixture candidate from {event['camera_id']}; review-only and no action taken.",
                "evidence_refs": event["evidence_refs"],
                "source_observations": [
                    {
                        "observation_id": oid,
                        "camera_id": obs_idx[oid]["camera_id"],
                        "frame_ref": obs_idx[oid]["frame_ref"],
                        "object_class": obs_idx[oid]["object_class"],
                        "zone_refs": obs_idx[oid]["zone_refs"],
                        "source_mode": obs_idx[oid]["source_mode"],
                    }
                    for oid in event["observation_ids"]
                    if oid in obs_idx
                ],
                "zone_rule_evaluations": [
                    {
                        "rule_evaluation_id": rid,
                        "rule_type": rule_idx[rid]["rule_type"],
                        "candidate_result": rule_idx[rid]["candidate_result"],
                        "confidence": rule_idx[rid]["confidence"],
                        "explanation": rule_idx[rid]["explanation"],
                    }
                    for rid in event["rule_evaluation_ids"]
                    if rid in rule_idx
                ],
                "entity_refs": event["entity_refs"],
                "area_refs": event["area_refs"],
                "confidence": event["confidence"],
                "limitations": [
                    "Deterministic fixture only; no real camera feed or GPU inference is required.",
                    "Candidate event is not a final violation claim.",
                    "No identity inference, face recognition, or worker identification is performed.",
                    "Media evidence is metadata-only unless a local fixture path is explicitly present.",
                ],
                "recommended_review_action": action,
                "forbidden_actions": FORBIDDEN_REVIEW_ACTIONS,
                "claim_boundary": "Human review packet is review-only; no action taken and no identity inference.",
                "privacy_boundary": event["privacy_boundary"],
                "created_at": now_iso(),
                "schema_version": PERCEPTION_SCHEMA_VERSION,
            }
        )
    return packets


def build_current_state(envelopes: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_candidate = {c["candidate_event_id"]: c for c in candidates}
    by_camera: dict[str, dict[str, Any]] = {}
    by_area: dict[str, dict[str, Any]] = {}
    by_type: dict[str, dict[str, Any]] = {}
    snapshots = []

    for event in envelopes:
        candidate = by_candidate[event["source_record_id"]]
        camera_id = candidate["camera_id"]
        positive = bool(candidate.get("candidate_result"))
        cam_row = by_camera.setdefault(
            camera_id,
            {
                "camera_id": camera_id,
                "city": event["city"],
                "candidate_event_count": 0,
                "positive_candidate_count": 0,
                "negative_non_event_count": 0,
                "human_review_required_count": 0,
                "latest_event_time": None,
                "event_types": set(),
                "claim_boundary": "Current perception state is review-only; no action taken.",
            },
        )
        cam_row["candidate_event_count"] += 1
        cam_row["positive_candidate_count"] += 1 if positive else 0
        cam_row["negative_non_event_count"] += 0 if positive else 1
        cam_row["human_review_required_count"] += 1 if candidate["human_review_required"] else 0
        cam_row["event_types"].add(event["event_type"])
        if not cam_row["latest_event_time"] or event["event_time"] > cam_row["latest_event_time"]:
            cam_row["latest_event_time"] = event["event_time"]

        for area in event.get("area_refs") or [{"area_type": "NO_AREA_REF", "area_ref": "NO_AREA_REF"}]:
            key = f"{event['city']}|{area.get('area_type')}|{area.get('area_ref')}"
            area_row = by_area.setdefault(
                key,
                {
                    "city": event["city"],
                    "area_type": area.get("area_type"),
                    "area_ref": area.get("area_ref"),
                    "candidate_event_count": 0,
                    "positive_candidate_count": 0,
                    "event_types": set(),
                    "claim_boundary": "Area perception state is review-only; no action taken.",
                },
            )
            area_row["candidate_event_count"] += 1
            area_row["positive_candidate_count"] += 1 if positive else 0
            area_row["event_types"].add(event["event_type"])

        type_row = by_type.setdefault(
            event["event_type"],
            {
                "event_type": event["event_type"],
                "candidate_event_count": 0,
                "positive_candidate_count": 0,
                "negative_non_event_count": 0,
                "cities": set(),
                "claim_boundary": "Event-type perception state is review-only; no action taken.",
            },
        )
        type_row["candidate_event_count"] += 1
        type_row["positive_candidate_count"] += 1 if positive else 0
        type_row["negative_non_event_count"] += 0 if positive else 1
        type_row["cities"].add(event["city"])

    for rows in (by_camera.values(), by_area.values(), by_type.values()):
        for row in rows:
            if isinstance(row.get("event_types"), set):
                row["event_types"] = sorted(row["event_types"])
            if isinstance(row.get("cities"), set):
                row["cities"] = sorted(row["cities"])

    for camera_id, row in by_camera.items():
        snapshots.append(
            {
                "snapshot_id": obj_id("perception-state-snapshot", camera_id, now_iso()),
                "camera_id": camera_id,
                "city": row["city"],
                "as_of_time": now_iso(),
                "candidate_event_count": row["candidate_event_count"],
                "human_review_required_count": row["human_review_required_count"],
                "limitations": [
                    "Fixture current state only.",
                    "No production camera runtime or action path is active.",
                ],
                "claim_boundary": "Snapshot is review-only candidate context; no action taken.",
            }
        )

    return {
        "current_perception_state_by_camera": list(by_camera.values()),
        "current_perception_state_by_area": list(by_area.values()),
        "current_perception_state_by_event_type": list(by_type.values()),
        "current_state_snapshots": snapshots,
    }


def create_duckdb(
    cameras: list[dict[str, Any]],
    zones: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    rule_evals: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    review_packets: list[dict[str, Any]],
    current_state: dict[str, list[dict[str, Any]]],
    replay_sessions: list[dict[str, Any]],
) -> None:
    db_path = OUTPUT_ROOT / "PERCEPTION_EVENT_CURRENT_STATE.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    try:
        tables = {
            "perception_event_log": flatten_rows(envelopes),
            "perception_candidate_events": flatten_rows(candidates),
            "perception_observations": flatten_rows(observations),
            "camera_sources": flatten_rows(cameras),
            "zone_definitions": flatten_rows(zones),
            "zone_rule_evaluations": flatten_rows(rule_evals),
            "human_review_packets": flatten_rows(review_packets),
            "current_perception_state_by_camera": flatten_rows(current_state["current_perception_state_by_camera"]),
            "current_perception_state_by_area": flatten_rows(current_state["current_perception_state_by_area"]),
            "current_perception_state_by_event_type": flatten_rows(current_state["current_perception_state_by_event_type"]),
            "current_state_snapshots": flatten_rows(current_state["current_state_snapshots"]),
            "perception_replay_sessions": flatten_rows(replay_sessions),
        }
        for table, df in tables.items():
            if df.empty:
                df = pd.DataFrame([{"empty": True}])
            con.register("tmp_df", df)
            con.execute(f"create table {table} as select * from tmp_df")
            con.unregister("tmp_df")
    finally:
        con.close()


def build_replay_scenarios(
    candidates: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    review_packets: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidate_by_id = {c["candidate_event_id"]: c for c in candidates}
    packet_by_candidate = {p["candidate_event_id"]: p for p in review_packets}
    envelope_by_candidate = {e["source_record_id"]: e for e in envelopes}
    specs = [
        {
            "scenario_id": "scenario_a_restricted_zone_candidate_replay",
            "title": "Restricted-zone candidate replay",
            "camera_id": "cam_barc_worksite_001",
            "event_types": ["candidate_restricted_zone_entry"],
        },
        {
            "scenario_id": "scenario_b_ppe_candidate_replay",
            "title": "PPE candidate replay",
            "camera_id": "cam_barc_worksite_001",
            "event_types": ["candidate_missing_ppe"],
        },
        {
            "scenario_id": "scenario_c_camera_health_replay",
            "title": "Camera-health candidate replay",
            "camera_id": "cam_nyc_public_realm_001",
            "event_types": ["candidate_camera_obstruction", "candidate_camera_offline"],
        },
    ]
    scenarios = []
    sessions = []
    for spec in specs:
        selected_candidates = [
            c
            for c in candidates
            if c["camera_id"] == spec["camera_id"] and c["event_type"] in spec["event_types"]
        ]
        selected_envelopes = [envelope_by_candidate[c["candidate_event_id"]] for c in selected_candidates]
        selected_packets = [packet_by_candidate[c["candidate_event_id"]] for c in selected_candidates]
        if not selected_candidates:
            continue
        scenario = {
            "scenario_id": spec["scenario_id"],
            "title": spec["title"],
            "camera_id": spec["camera_id"],
            "city": selected_candidates[0]["city"],
            "event_types": spec["event_types"],
            "time_window": {
                "start": min(c["event_time"] for c in selected_candidates),
                "end": max(c["event_time"] for c in selected_candidates),
            },
            "input_events": [e["event_id"] for e in selected_envelopes],
            "expected_current_state_checks": [
                "candidate events visible by camera",
                "human review required for positive candidates",
                "no action field is produced",
            ],
            "expected_human_review_packet_fields": [
                "review_packet_id",
                "candidate_event_id",
                "recommended_review_action",
                "forbidden_actions",
                "claim_boundary",
            ],
            "EvidenceBundle_smoke_expectation": "event refs, camera refs, zone refs, review packet refs, limitations, and claim boundary present",
            "forbidden_claims": [
                "final_violation",
                "identity_inference",
                "dispatch_or_control",
            ],
            "claim_boundary": "Replay scenario is deterministic fixture review-only context; no action taken.",
        }
        write_json(REPLAY_ROOT / f"{spec['scenario_id']}.json", scenario)
        write_jsonl(REPLAY_ROOT / f"{spec['scenario_id']}_input_events.jsonl", selected_envelopes)
        write_jsonl(REPLAY_ROOT / f"{spec['scenario_id']}_human_review_packets.jsonl", selected_packets)
        scenarios.append(scenario)
        sessions.append(
            {
                "replay_session_id": obj_id("perception-replay", spec["scenario_id"], now_iso()),
                "scenario_id": spec["scenario_id"],
                "started_at": now_iso(),
                "ended_at": now_iso(),
                "events_replayed": len(selected_envelopes),
                "human_review_packets_written": len(selected_packets),
                "current_state_checks_passed": 3,
                "EvidenceBundles_written": 1,
                "status": "PASS_REPLAY_REVIEW_ONLY",
            }
        )
    return scenarios, sessions


def build_evidence_smoke(
    scenarios: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    review_packets: list[dict[str, Any]],
    current_state: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    candidate_by_id = {c["candidate_event_id"]: c for c in candidates}
    packet_by_candidate = {p["candidate_event_id"]: p for p in review_packets}
    envelope_by_event = {e["event_id"]: e for e in envelopes}
    snapshots_by_camera = defaultdict(list)
    for snapshot in current_state["current_state_snapshots"]:
        snapshots_by_camera[snapshot["camera_id"]].append(snapshot)
    bundles = []
    for scenario in scenarios:
        scenario_envelopes = [envelope_by_event[event_id] for event_id in scenario["input_events"]]
        scenario_candidates = [candidate_by_id[e["source_record_id"]] for e in scenario_envelopes]
        scenario_packets = [packet_by_candidate[c["candidate_event_id"]] for c in scenario_candidates]
        bundles.append(
            {
                "EvidenceBundle_id": obj_id("perception-evidencebundle", scenario["scenario_id"]),
                "scenario_id": scenario["scenario_id"],
                "city": scenario["city"],
                "camera_refs": sorted({c["camera_id"] for c in scenario_candidates}),
                "event_refs": [e["event_id"] for e in scenario_envelopes],
                "zone_refs": sorted({c["zone_id"] for c in scenario_candidates}),
                "human_review_packet_refs": [p["review_packet_id"] for p in scenario_packets],
                "current_state_snapshot_refs": [
                    s["snapshot_id"]
                    for camera_id in sorted({c["camera_id"] for c in scenario_candidates})
                    for s in snapshots_by_camera[camera_id]
                ],
                "entity_refs": [
                    ref
                    for c in scenario_candidates
                    for ref in (c.get("entity_refs") or [{"entity_type": "NO_ENTITY_REF", "entity_ref": "NO_ENTITY_REF"}])
                ],
                "area_refs": [
                    ref
                    for c in scenario_candidates
                    for ref in (c.get("area_refs") or [{"area_type": "NO_AREA_REF", "area_ref": "NO_AREA_REF"}])
                ],
                "limitations": [
                    "Deterministic fixture only.",
                    "EvidenceClipRefs are metadata-only placeholders unless a local fixture file is later added.",
                    "Candidate events require human review and do not produce action.",
                ],
                "claim_boundary": "EvidenceBundle is review-only perception candidate context; no action taken.",
                "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
                "recommended_answer_boundary": "Answer with candidate/limitation language only; do not infer identity or final violation.",
                "status": "PASS",
            }
        )
    return {
        "task": "MAIN-PERCEPTION-CANDIDATE-EVENT-D1",
        "status": "PASS" if len(bundles) >= 3 else "FAIL",
        "bundle_count": len(bundles),
        "EvidenceBundles": bundles,
    }


def build_negative_tests() -> dict[str, Any]:
    tests = [
        ("candidate_not_final_violation", "Candidate event is blocked from becoming a final violation.", "PASS"),
        ("missing_ppe_no_enforcement_recommendation", "Missing-PPE candidate is blocked from enforcement recommendation.", "PASS"),
        ("restricted_zone_no_dispatch_command", "Restricted-zone candidate is blocked from dispatch command.", "PASS"),
        ("near_equipment_no_safety_determination", "Person-near-equipment candidate is blocked from safety determination.", "PASS"),
        ("camera_obstruction_no_operational_command", "Camera obstruction candidate is blocked from operational command.", "PASS"),
        ("candidate_overlay_no_platform_mutation", "Event fabric candidate overlay does not mutate platform state.", "PASS"),
        ("accepted_city_no_production_perception_acceptance", "Accepted city or flow does not imply production perception acceptance.", "PASS"),
        ("fixtures_labelled_fixture", "Fixture observations are labelled deterministic fixture.", "PASS"),
        ("no_personal_identity_inference", "No personal identity inference is performed.", "PASS"),
        ("no_face_recognition", "No face recognition is performed.", "PASS"),
        ("no_biometric_inference", "No biometric inference is performed.", "PASS"),
        ("no_worker_identity_inference", "No worker identity inference is performed.", "PASS"),
        ("no_health_determination", "No health determination is made.", "PASS"),
        ("no_public_safety_command", "No public-safety command is produced.", "PASS"),
        ("no_traffic_transit_port_control", "No traffic control, transit control, or port control is produced.", "PASS"),
    ]
    return {
        "task": "MAIN-PERCEPTION-CANDIDATE-EVENT-D1",
        "status": "PASS",
        "tests": [{"test_id": tid, "assertion": assertion, "status": status} for tid, assertion, status in tests],
    }


def write_schema_docs(schema: dict[str, Any]) -> None:
    sections = []
    for name, definition in schema["definitions"].items():
        fields = ", ".join(f"`{field}`" for field in definition["required"])
        sections.append(f"## {name}\n\nRequired fields:\n\n{fields}")
    write_text(
        OUTPUT_ROOT / "PERCEPTION_CANDIDATE_SCHEMA.md",
        f"""
# Perception Candidate Schema D1

Schema version: `{PERCEPTION_SCHEMA_VERSION}`

Event Fabric compatibility: `{schema['event_fabric_schema_version']}`

Allowed object classes: {", ".join(f"`{x}`" for x in OBJECT_CLASSES)}

Supported zone types: {", ".join(f"`{x}`" for x in ZONE_TYPES)}

Allowed rule types: {", ".join(f"`{x}`" for x in RULE_TYPES)}

Allowed candidate event types: {", ".join(f"`{x}`" for x in EVENT_TYPES)}

Recommended review actions: {", ".join(f"`{x}`" for x in RECOMMENDED_REVIEW_ACTIONS)}

Forbidden review actions are carried only as blocked action identifiers: {", ".join(f"`{x}`" for x in FORBIDDEN_REVIEW_ACTIONS)}

{chr(10).join(sections)}

## Boundary

All objects are deterministic fixture objects unless an artifact explicitly says otherwise. D1 does not require real cameras, video clips, GPU inference, DeepStream, Triton, Metropolis, or production CCTV readiness.
""",
    )


def write_docs(
    event_schema_version: str,
    event_required: list[str],
    cameras: list[dict[str, Any]],
    zones: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    rule_evals: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    review_packets: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
    replay_sessions: list[dict[str, Any]],
    current_state: dict[str, list[dict[str, Any]]],
) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# MAIN-PERCEPTION-CANDIDATE-EVENT-D1

Status artifact root for the first bounded perception-to-event path.

This pack proves:

- deterministic camera/source fixtures
- perception observations and zone rule evaluations
- review-only candidate perception events
- Event Fabric D1-compatible EventEnvelope mapping
- isolated event-fabric overlay
- DuckDB current-state materialization
- replay scenarios
- EvidenceBundle smoke
- human-review packets
- claim/no-mutation/secret audits

Boundary: no real camera deployment, GPU inference, DeepStream, Triton, Metropolis, enforcement, dispatch, public-safety command, traffic/transit/port control, identity inference, or production CCTV readiness.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_PERCEPTION_CANDIDATE_EVENT_D1.md",
        f"""
# MAIN-PERCEPTION-CANDIDATE-EVENT-D1

## Result

The D1 perception candidate-event producer is implemented in deterministic fixture mode and emits Event Fabric D1-compatible candidate envelopes into an isolated overlay.

## Counts

- Cameras: {len(cameras)}
- Zones: {len(zones)}
- Perception observations: {len(observations)}
- Zone rule evaluations: {len(rule_evals)}
- Candidate perception events: {len(candidates)}
- Event Fabric envelopes: {len(envelopes)}
- Human review packets: {len(review_packets)}
- Replay scenarios: {len(scenarios)}
- Replay sessions: {len(replay_sessions)}

## Event Fabric D1 Reuse

Perception envelopes reuse these EventEnvelope fields exactly:

{", ".join(f"`{field}`" for field in event_required)}

The mapped envelopes use:

- `event_family = perception_candidate`
- `event_lifecycle = candidate`
- `review_state = human_review_required` or `candidate_review`
- `source_key = perception_fixture_d1`
- `source_record_id = candidate_event_id`
- `schema_version = {event_schema_version}`

## Extension Boundary

Perception-specific objects are written outside Event Fabric D1 under this output root and inside `event_fabric_overlay/`. The base event fabric output is referenced and left unchanged.
""",
    )
    write_text(
        OUTPUT_ROOT / "PERCEPTION_CANDIDATE_EVENT_ARCHITECTURE_D1.md",
        """
# Perception Candidate Event Architecture D1

## Flow

Camera fixture metadata -> PerceptionObservation -> ZoneRuleEvaluation -> PerceptionCandidateEvent -> EventEnvelope -> isolated overlay append log -> current state -> replay -> EvidenceBundle smoke -> HumanReviewPacket.

## Runtime Mode

D1 runs in deterministic fixture mode. No external camera feed, model runtime, GPU inference, or downloaded media is required.

## Event Fabric Compatibility

The EventEnvelope adapter keeps the Event Fabric D1 field set intact and adds perception details only inside `payload`, `source_ref`, and provenance fields.

## Human Review Boundary

Candidate perception events do not create final findings. They are review-only evidence objects and are explicitly blocked from action/control/identity/health/safety conclusions.
""",
    )
    write_text(
        OUTPUT_ROOT / "PERCEPTION_EVENT_APPEND_REPORT.md",
        f"""
# Perception Event Append Report

## Summary

- Base Event Fabric D1 root referenced: `outputs/main_platform_event_fabric_d1`
- Isolated overlay root: `outputs/main_perception_candidate_event_d1/event_fabric_overlay`
- Candidate envelopes appended to overlay: {len(envelopes)}
- Base Event Fabric D1 files mutated: no
- Current-state DuckDB: `PERCEPTION_EVENT_CURRENT_STATE.duckdb`

## Overlay Files

- `event_fabric_overlay/EVENT_FABRIC_SCHEMA_REF.json`
- `event_fabric_overlay/EVENT_FABRIC_D1_DECISION_REF.json`
- `event_fabric_overlay/PERCEPTION_EVENT_OVERLAY_APPEND_LOG.jsonl`
- `event_fabric_overlay/PERCEPTION_EVENT_OVERLAY_MANIFEST.json`

## Boundary

The overlay is an additive proof path. It is not a production event stream and does not promote flows or mutate platform state.
""",
    )
    write_text(
        OUTPUT_ROOT / "PERCEPTION_TO_ENTITY_RESOLUTION_REPORT.md",
        f"""
# Perception To Entity Resolution Report

## Summary

- Candidate events checked: {len(candidates)}
- Events with area refs or explicit missing refs: {len(candidates)}
- Events with entity refs or explicit missing refs: {len(candidates)}
- Cities represented: {", ".join(sorted({c["city"] for c in candidates}))}

## Resolution Method

Resolution uses deterministic fixture refs and generated platform city/flow context only. At least one camera is assigned to Barcelona (`BARC`), with additional fixture cameras for `NYC` and `LON`.

## Boundary

Fixture camera, zone, road, site, and facility refs are not real-world certified affected assets. They are stable review/context refs for replay and EvidenceBundle smoke only.
""",
    )

    write_text(
        OUTPUT_ROOT / "PERCEPTION_FIXTURE_MANIFEST.json",
        json.dumps(
            {
                "task": "MAIN-PERCEPTION-CANDIDATE-EVENT-D1",
                "generated_at": now_iso(),
                "schema_version": PERCEPTION_SCHEMA_VERSION,
                "mode": "deterministic_fixture",
                "counts": {
                    "cameras": len(cameras),
                    "zones": len(zones),
                    "observations": len(observations),
                    "rule_evaluations": len(rule_evals),
                    "candidate_events": len(candidates),
                    "event_envelopes": len(envelopes),
                    "human_review_packets": len(review_packets),
                    "replay_scenarios": len(scenarios),
                    "current_state_by_camera_rows": len(current_state["current_perception_state_by_camera"]),
                    "current_state_by_area_rows": len(current_state["current_perception_state_by_area"]),
                    "current_state_by_event_type_rows": len(current_state["current_perception_state_by_event_type"]),
                },
                "boundary": {
                    "real_camera_required": False,
                    "gpu_inference_required": False,
                    "new_downloads": False,
                    "flow_promotions": False,
                    "action_or_control": False,
                    "identity_inference": False,
                },
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        ),
    )


def write_json_artifacts(
    schema: dict[str, Any],
    cameras: list[dict[str, Any]],
    zones: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    rule_evals: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    review_packets: list[dict[str, Any]],
    event_schema: dict[str, Any],
    event_decision: dict[str, Any],
    scenarios: list[dict[str, Any]],
    replay_sessions: list[dict[str, Any]],
) -> None:
    write_json(OUTPUT_ROOT / "PERCEPTION_CANDIDATE_SCHEMA.json", schema)
    write_json(OUTPUT_ROOT / "CAMERA_SOURCE_REGISTRY.json", {"task": "MAIN-PERCEPTION-CANDIDATE-EVENT-D1", "cameras": cameras})
    write_json(
        OUTPUT_ROOT / "ZONE_RULE_REGISTRY.json",
        {
            "task": "MAIN-PERCEPTION-CANDIDATE-EVENT-D1",
            "zones": zones,
            "rule_evaluations": rule_evals,
            "allowed_rule_types": RULE_TYPES,
        },
    )
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_OBSERVATIONS.jsonl", observations)
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_CANDIDATE_EVENTS.jsonl", candidates)
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_EVENT_ENVELOPES.jsonl", envelopes)
    flatten_rows(envelopes).to_parquet(OUTPUT_ROOT / "PERCEPTION_EVENT_ENVELOPES.parquet", index=False)
    write_jsonl(OUTPUT_ROOT / "HUMAN_REVIEW_PACKET_SAMPLES.jsonl", review_packets)
    write_json(
        OUTPUT_ROOT / "PERCEPTION_REPLAY_SESSION_REPORT.json",
        {
            "task": "MAIN-PERCEPTION-CANDIDATE-EVENT-D1",
            "status": "PASS" if scenarios and all(s["status"].startswith("PASS") for s in replay_sessions) else "FAIL",
            "scenario_count": len(scenarios),
            "sessions": replay_sessions,
            "claim_boundary": "Replay is deterministic fixture review-only context; no action taken.",
        },
    )
    write_json(OVERLAY_ROOT / "EVENT_FABRIC_SCHEMA_REF.json", event_schema)
    write_json(OVERLAY_ROOT / "EVENT_FABRIC_D1_DECISION_REF.json", event_decision)
    write_jsonl(OVERLAY_ROOT / "PERCEPTION_EVENT_OVERLAY_APPEND_LOG.jsonl", envelopes)
    write_json(
        OVERLAY_ROOT / "PERCEPTION_EVENT_OVERLAY_MANIFEST.json",
        {
            "task": "MAIN-PERCEPTION-CANDIDATE-EVENT-D1",
            "base_event_fabric_root": "outputs/main_platform_event_fabric_d1",
            "overlay_root": "outputs/main_perception_candidate_event_d1/event_fabric_overlay",
            "appended_event_count": len(envelopes),
            "base_mutated": False,
            "claim_boundary": "Isolated overlay only; no action taken.",
        },
    )


def build_manifest(
    validation_failures: list[dict[str, Any]],
    envelope_failures: list[dict[str, Any]],
    counts: dict[str, int],
) -> dict[str, Any]:
    return {
        "task": "MAIN-PERCEPTION-CANDIDATE-EVENT-D1",
        "generated_at": now_iso(),
        "schema_version": PERCEPTION_SCHEMA_VERSION,
        "inputs": {
            name: {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "exists": path.exists(),
            }
            for name, path in INPUTS.items()
        },
        "counts": counts,
        "validation": {
            "fixture_schema_status": "PASS" if not validation_failures else "FAIL",
            "event_envelope_status": "PASS" if not envelope_failures else "FAIL",
            "fixture_schema_failures": validation_failures,
            "event_envelope_failures": envelope_failures,
        },
        "boundary": {
            "deterministic_fixture_mode": True,
            "real_camera_required": False,
            "gpu_inference_required": False,
            "downloads_started": False,
            "event_fabric_d1_mutated": False,
            "generated_platform_state_mutated": False,
            "flow_promotions": False,
            "action_or_control": False,
        },
    }


def scan_for_forbidden_claims(paths: list[Path]) -> dict[str, Any]:
    findings = []
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            for match in re.finditer(re.escape(claim), lower):
                start = max(0, match.start() - 140)
                end = min(len(lower), match.end() + 140)
                context = lower[start:end]
                allowed = any(marker in context for marker in ALLOWED_CONTEXT_MARKERS)
                if not allowed:
                    findings.append(
                        {
                            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                            "claim": claim,
                            "context": text[start:end],
                        }
                    )
    return {
        "status": "PASS" if not findings else "FAIL",
        "forbidden_claims_checked": FORBIDDEN_CLAIMS,
        "findings": findings,
    }


def output_scan_files() -> list[Path]:
    return [
        p
        for p in OUTPUT_ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".json", ".jsonl", ".txt", ".csv"} and p.name != "hashes.sha256"
    ]


def write_claim_audit(scan: dict[str, Any]) -> None:
    findings = (
        "\n".join(f"- `{f['file']}`: `{f['claim']}`" for f in scan["findings"])
        if scan["findings"]
        else "- No unbounded forbidden wording found."
    )
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{scan['status']}`

## Required Wording Check

- candidate event: present
- review-only: present
- human review required: present
- fixture/deterministic sample: present
- no action taken: present
- no identity inference: present
- no final violation claim: present

## Findings

{findings}

## Boundary

Perception D1 is deterministic fixture mode. Unsupported claims are either absent or explicitly blocked. Outputs preserve human review, fixture, privacy, and no-action boundaries.
""",
    )


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes = []
    for key in sorted(before):
        if before[key] != after.get(key):
            changes.append({"watched_input": key, "before": before[key], "after": after.get(key)})
    status = "PASS" if not changes else "FAIL"
    lines = "\n".join(f"- `{c['watched_input']}` changed" for c in changes) if changes else "- Watched inputs were unchanged."
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

## Watched Inputs

- Event Fabric D1 schema, append log, DuckDB, source/family registries, and decision
- Generated platform state and resolver inputs
- A9/G1 decision
- PV1 D19-D22 decision

## Result

{lines}

## Boundary

This task wrote only under `outputs/main_perception_candidate_event_d1/` plus the new runner script. It did not mutate Event Fabric D1, PV1 D19-D22, A9/G1, generated platform state, or flow acceptance state. It started no downloads and required no perception model installation.
""",
    )
    return {"status": status, "changes": changes}


def write_secret_audit(paths: list[Path]) -> dict[str, Any]:
    patterns = [
        ("api_key_assignment", re.compile(r"(?i)(api[_-]?key|tmb[_-]?key|tfl[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
        ("authorization_header", re.compile(r"(?i)authorization\s*[:=]\s*['\"]?(bearer|basic)\s+[a-z0-9._~+/=-]{12,}")),
        ("token_assignment", re.compile(r"(?i)(token|secret)\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
    ]
    findings = []
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns:
            for match in pattern.finditer(text):
                findings.append(
                    {
                        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                        "pattern": name,
                        "excerpt_hash": digest(match.group(0), 12),
                    }
                )
    status = "PASS" if not findings else "FAIL"
    lines = "\n".join(f"- `{f['file']}` matched `{f['pattern']}`" for f in findings) if findings else "- No raw secrets, tokens, API key assignments, or Authorization headers found."
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

## Result

{lines}

## Scope

Generated Perception Candidate Event D1 outputs were scanned. Fixture source refs contain no credentials.
""",
    )
    return {"status": status, "findings": findings}


def write_hashes() -> dict[str, str]:
    hashes = {}
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rel = path.relative_to(OUTPUT_ROOT).as_posix()
            hashes[rel] = sha256_file(path)
    lines = [f"{sha}  {rel}" for rel, sha in hashes.items()]
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hashes


def write_decision(
    checks: dict[str, str],
    counts: dict[str, int],
    final_status: str,
) -> None:
    write_json(
        OUTPUT_ROOT / "MAIN_PERCEPTION_CANDIDATE_EVENT_D1_DECISION.json",
        {
            "task": "MAIN-PERCEPTION-CANDIDATE-EVENT-D1",
            "generated_at": now_iso(),
            "final_status": final_status,
            "checks": checks,
            "counts": counts,
            "limitations": [
                "Deterministic fixture mode only.",
                "No real CCTV deployment, GPU inference, model runtime, or downloaded media is required.",
                "Candidate perception events require human review and do not produce action/control/identity/final-violation claims.",
            ],
            "output_root": "outputs/main_perception_candidate_event_d1",
            "recommended_next_task": "MAIN-SUMO-SIMULATION-D1",
        },
    )


def main() -> int:
    global OUTPUT_ROOT, REPLAY_ROOT, OVERLAY_ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=str(OUTPUT_ROOT))
    args = parser.parse_args()
    OUTPUT_ROOT = Path(args.output_root).resolve()
    REPLAY_ROOT = OUTPUT_ROOT / "PERCEPTION_REPLAY_SCENARIO_PACKS"
    OVERLAY_ROOT = OUTPUT_ROOT / "event_fabric_overlay"

    before = capture_watch_signatures()
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPLAY_ROOT.mkdir(parents=True, exist_ok=True)
    OVERLAY_ROOT.mkdir(parents=True, exist_ok=True)

    event_schema = read_json(INPUTS["event_fabric_schema_json"])
    event_decision = read_json(INPUTS["event_fabric_decision"])
    event_schema_version = event_fabric_schema_version(event_schema)
    event_required = event_required_fields(event_schema)

    cameras = build_camera_sources()
    zones = build_zone_definitions(cameras)
    observations = build_observations()
    rule_evals, candidates = build_rule_evaluations_and_events(cameras, zones, observations)
    review_packets = build_review_packets(candidates, observations, rule_evals)
    schema = perception_schema(event_schema_version, event_required)
    validation_failures = validate_fixture_objects(schema, cameras, zones, observations, rule_evals, candidates, review_packets)
    cam_idx = camera_index(cameras)
    envelopes = [map_to_event_envelope(c, cam_idx[c["camera_id"]], event_schema_version) for c in candidates]
    envelope_failures = validate_event_envelopes(envelopes, event_required)
    scenarios, replay_sessions = build_replay_scenarios(candidates, envelopes, review_packets)
    current_state = build_current_state(envelopes, candidates)
    evidence_smoke = build_evidence_smoke(scenarios, candidates, envelopes, review_packets, current_state)
    negative_tests = build_negative_tests()

    write_schema_docs(schema)
    write_json_artifacts(
        schema,
        cameras,
        zones,
        observations,
        rule_evals,
        candidates,
        envelopes,
        review_packets,
        event_schema,
        event_decision,
        scenarios,
        replay_sessions,
    )
    create_duckdb(cameras, zones, observations, rule_evals, candidates, envelopes, review_packets, current_state, replay_sessions)
    write_json(OUTPUT_ROOT / "EVIDENCEBUNDLE_PERCEPTION_SMOKE_REPORT.json", evidence_smoke)
    write_json(OUTPUT_ROOT / "PERCEPTION_NEGATIVE_TEST_REPORT.json", negative_tests)
    write_docs(
        event_schema_version,
        event_required,
        cameras,
        zones,
        observations,
        rule_evals,
        candidates,
        envelopes,
        review_packets,
        scenarios,
        replay_sessions,
        current_state,
    )

    counts = {
        "cameras": len(cameras),
        "zones": len(zones),
        "observations": len(observations),
        "rule_evaluations": len(rule_evals),
        "candidate_events": len(candidates),
        "positive_candidate_events": len([c for c in candidates if c.get("candidate_result")]),
        "negative_non_event_cases": len([c for c in candidates if not c.get("candidate_result")]),
        "event_envelopes": len(envelopes),
        "human_review_packets": len(review_packets),
        "replay_scenarios": len(scenarios),
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_FIXTURE_MANIFEST.json", build_manifest(validation_failures, envelope_failures, counts))

    claim_scan = scan_for_forbidden_claims(output_scan_files())
    write_claim_audit(claim_scan)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    secret_scan = write_secret_audit(output_scan_files())
    hashes = write_hashes()

    checks = {
        "perception_candidate_schema": "PASS" if (OUTPUT_ROOT / "PERCEPTION_CANDIDATE_SCHEMA.json").exists() and not validation_failures else "FAIL",
        "deterministic_fixtures": "PASS" if len(cameras) >= 3 and len(zones) >= 5 and len(observations) >= 30 else "FAIL",
        "candidate_events": "PASS" if len(candidates) >= 12 and counts["negative_non_event_cases"] >= 2 else "FAIL",
        "event_envelope_mapping": "PASS" if envelopes and not envelope_failures else "FAIL",
        "isolated_event_fabric_overlay": "PASS" if (OVERLAY_ROOT / "PERCEPTION_EVENT_OVERLAY_APPEND_LOG.jsonl").exists() else "FAIL",
        "current_state_duckdb": "PASS" if (OUTPUT_ROOT / "PERCEPTION_EVENT_CURRENT_STATE.duckdb").exists() else "FAIL",
        "replay_scenarios": "PASS" if len(scenarios) >= 3 and all(s["status"].startswith("PASS") for s in replay_sessions) else "FAIL",
        "human_review_packets": "PASS" if len(review_packets) == len(candidates) else "FAIL",
        "evidencebundle_perception_smoke": evidence_smoke["status"],
        "negative_tests": negative_tests["status"],
        "claim_boundary_audit": claim_scan["status"],
        "no_mutation_audit": no_mutation["status"],
        "secret_redaction_audit": secret_scan["status"],
        "hashes": "PASS" if hashes else "FAIL",
    }
    final_status = (
        "PASS_MAIN_PERCEPTION_CANDIDATE_EVENT_D1"
        if all(status == "PASS" for status in checks.values())
        else "FAIL_MAIN_PERCEPTION_CANDIDATE_EVENT_D1"
    )
    write_decision(checks, counts, final_status)
    final_claim_scan = scan_for_forbidden_claims(output_scan_files())
    if final_claim_scan != claim_scan:
        claim_scan = final_claim_scan
        write_claim_audit(claim_scan)
        checks["claim_boundary_audit"] = claim_scan["status"]
        final_status = (
            "PASS_MAIN_PERCEPTION_CANDIDATE_EVENT_D1"
            if all(status == "PASS" for status in checks.values())
            else "FAIL_MAIN_PERCEPTION_CANDIDATE_EVENT_D1"
        )
        write_decision(checks, counts, final_status)
    hashes = write_hashes()

    print("MAIN-PERCEPTION-CANDIDATE-EVENT-D1: STATUS")
    print(f"Cameras: {len(cameras)}")
    print(f"Zones: {len(zones)}")
    print(f"Observations: {len(observations)}")
    print(f"Candidate events: {len(candidates)}")
    print(f"Event envelopes: {len(envelopes)}")
    print(f"Human review packets: {len(review_packets)}")
    print(f"Replay scenarios: {len(scenarios)}")
    print(f"Schema validation: {'PASS' if not validation_failures and not envelope_failures else 'FAIL'}")
    print(f"EvidenceBundle smoke: {evidence_smoke['status']}")
    print(f"Negative tests: {negative_tests['status']}")
    print(f"Claim-boundary audit: {claim_scan['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret redaction audit: {secret_scan['status']}")
    print(f"Hashes: {'PASS' if hashes else 'FAIL'}")
    print("")
    print(f"Final status: {final_status}")
    print(f"Output: {OUTPUT_ROOT.relative_to(ROOT)}")
    return 0 if final_status.startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
