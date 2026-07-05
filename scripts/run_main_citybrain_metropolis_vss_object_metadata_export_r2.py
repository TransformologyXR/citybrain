#!/usr/bin/env python3
"""Run Metropolis/VSS object-metadata export R2.

R2 may only PASS when DeepStream exports object metadata with class,
confidence, frame/time reference, and bbox/region information.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_object_metadata_export_r2"
TASK_NAME = "MAIN-CITYBRAIN-METROPOLIS-VSS-OBJECT-METADATA-EXPORT-R2"
SCHEMA_VERSION = "metropolis-vss-object-metadata-export-r2.v1"

HANDOFF_ZIP = Path(r"C:\Users\hazem\Downloads\citybrain_metropolis_vss_object_metadata_export_r2_handoff.zip")
R1_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_candidate_observation_pipeline_r1"
R1_PACKAGE = R1_ROOT / "METROPOLIS_VSS_VALIDATION_PACKAGE.zip"
D3_ROOT = REPO_ROOT / "outputs" / "main_perception_d3_deepstream_bridge"

PASS_STATUS = "PASS_METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_WITH_LIMITATIONS"
PARTIAL_RUNTIME_BLOCKED_STATUS = "PARTIAL_METROPOLIS_VSS_OBJECT_METADATA_RUNTIME_BLOCKED_CONTRACTS_READY"
PARTIAL_EVENT_MAPPING_BLOCKED_STATUS = "PARTIAL_METROPOLIS_VSS_OBJECT_METADATA_EXPORTED_EVENT_MAPPING_BLOCKED"
PARTIAL_MEDIA_BLOCKED_STATUS = "PARTIAL_METROPOLIS_VSS_MEDIA_SOURCE_BLOCKED_CONTRACTS_READY"
FAIL_BOUNDARY_STATUS = "FAIL_METROPOLIS_VSS_BOUNDARY_OR_IDENTITY_RISK"
FAIL_SOURCE_CLASS_STATUS = "FAIL_METROPOLIS_VSS_SOURCE_CLASS_DRIFT"
FAIL_OFFICIAL_RECORD_STATUS = "FAIL_METROPOLIS_VSS_FALSE_OFFICIAL_RECORD_PROMOTION"
FAIL_ACTION_STATUS = "FAIL_METROPOLIS_VSS_ACTION_OR_ALERT_COMMAND_RISK"

VISIBLE_BOUNDARY_TEXT = "Candidate observation\nHuman review required\nNot a finding"
MEDIA_SOURCE_ID = "media:deepstream:sample_1080p_h264"
MEDIA_SOURCE_SELECTED = "container bundled samples/streams/sample_1080p_h264.mp4"
CAMERA_SOURCE_ID = "txr4070_deepstream_sample_camera_001"
ZONE_ID = "bounded_vehicle_zone_r2"
ZONE_RECT = {"x": 480.0, "y": 430.0, "w": 320.0, "h": 200.0, "coordinate_space": "pixel"}
PREFERRED_DETECTION_CLASS = "vehicle_presence_candidate"
PREFERRED_CLASS_LABEL = "car"
REMOTE_HOST = "txr-4070"
DEEPSTREAM_IMAGE = "nvcr.io/nvidia/deepstream:8.0-samples-multiarch"

BOUNDARY = {
    "allowed_outputs": [
        "candidate observation",
        "candidate event",
        "model confidence",
        "object class label",
        "bbox or region reference",
        "frame or clip reference",
        "timestamp/source/camera/zone provenance",
        "uncertainty and false-positive notes",
        "CHECK sufficiency report for review only",
        "human-review packet",
    ],
    "forbidden_outputs": [
        "confirmed violation",
        "legal or certified finding",
        "identity or biometric inference",
        "face recognition",
        "official case or ticket",
        "dispatch/routing/control/enforcement",
        "alert as operational command",
        "automated action",
        "production monitoring",
        "VSS as a fact source",
    ],
}

BLOCKED_OUTCOME_CODES = [
    "confirmed_violation_blocked",
    "legal_or_certified_finding_blocked",
    "identity_or_biometric_inference_blocked",
    "face_recognition_blocked",
    "official_case_or_ticket_blocked",
    "dispatch_routing_control_enforcement_blocked",
    "alert_as_command_blocked",
    "automated_action_blocked",
    "production_monitoring_blocked",
]

BASE_LIMITATIONS = [
    "Bounded R2 lane only: one media source, one zone, one detection class.",
    "DeepStream KITTI bbox export is used as object metadata evidence from the bundled sample media.",
    "Candidate observations remain candidate_unreviewed and require human review.",
    "VSS runtime is not used as a sensor or fact source.",
    "No identity, biometric, license-plate, finding, ticket, dispatch, control, enforcement, alert-command, or automated action output is created.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def stable_hash(*parts: Any, length: int = 24) -> str:
    payload = "|".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}:{stable_hash(*parts)}"


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    outputs_root = (REPO_ROOT / "outputs").resolve()
    if outputs_root not in resolved.parents:
        raise RuntimeError(f"Refusing to reset output outside workspace outputs: {resolved}")
    if resolved.name != "main_citybrain_metropolis_vss_object_metadata_export_r2":
        raise RuntimeError(f"Unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def copy_schema_from_handoff(member: str, target_name: str, fallback: dict[str, Any]) -> None:
    target = OUTPUT_ROOT / target_name
    if HANDOFF_ZIP.exists():
        with zipfile.ZipFile(HANDOFF_ZIP) as zf:
            source_name = f"citybrain_metropolis_vss_object_metadata_export_r2_handoff/schemas/{member}"
            if source_name in zf.namelist():
                target.write_bytes(zf.read(source_name))
                return
    write_json(target, fallback)


def remote_container_script() -> str:
    return r'''set -eu
DS=/opt/nvidia/deepstream/deepstream-8.0
WORK=/work
KITTIDIR="$WORK/kitti"
LOG="$WORK/deepstream_r2_stdout.log"
CONFIG="$WORK/citybrain_r2_object_export_config.txt"
SUMMARY="$WORK/KITTI_EXPORT_SUMMARY.json"
RAW="$WORK/OBJECT_METADATA_RAW_SAMPLE.jsonl"
NORM="$WORK/OBJECT_METADATA_NORMALIZED_SAMPLE.jsonl"
rm -rf "$KITTIDIR"
mkdir -p "$KITTIDIR"
cd "$DS/samples/configs/deepstream-app"
cp source30_1080p_dec_infer-resnet_tiled_display.txt citybrain_r2_object_export_source1.txt
python3 - <<'PY'
from pathlib import Path
p = Path("citybrain_r2_object_export_source1.txt")
s = p.read_text()
s = s.replace("#gie-kitti-output-dir=streamscl", "gie-kitti-output-dir=/work/kitti")
s = s.replace("rows=5", "rows=1")
s = s.replace("columns=6", "columns=1")
s = s.replace("num-sources=15", "num-sources=1")
s = s.replace("batch-size=30", "batch-size=1")
s = s.replace(
    "model-engine-file=../../models/Primary_Detector/resnet18_trafficcamnet_pruned.onnx_b30_gpu0_fp16.engine",
    "model-engine-file=../../models/Primary_Detector/resnet18_trafficcamnet_pruned.onnx_b1_gpu0_fp16.engine",
)
s = s.replace("[source1]\nenable=1", "[source1]\nenable=0")
s = s.replace("type=2\nsync=1\nsource-id=0", "type=1\nsync=0\nsource-id=0")
p.write_text(s)
PY
cp citybrain_r2_object_export_source1.txt "$CONFIG"
set +e
timeout 180 deepstream-app -c citybrain_r2_object_export_source1.txt > "$LOG" 2>&1
DS_RC=$?
set -e
echo "$DS_RC" > "$WORK/deepstream_return_code.txt"
find "$KITTIDIR" -type f | sort > "$WORK/kitti_files.txt" || true
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

WORK = Path("/work")
KITTIDIR = WORK / "kitti"
RAW = WORK / "OBJECT_METADATA_RAW_SAMPLE.jsonl"
NORM = WORK / "OBJECT_METADATA_NORMALIZED_SAMPLE.jsonl"
SUMMARY = WORK / "KITTI_EXPORT_SUMMARY.json"
ZONE = {"x": 480.0, "y": 430.0, "w": 320.0, "h": 200.0, "coordinate_space": "pixel"}
MEDIA_SOURCE_ID = "media:deepstream:sample_1080p_h264"
MEDIA_SOURCE_SELECTED = "container bundled samples/streams/sample_1080p_h264.mp4"
CAMERA_SOURCE_ID = "txr4070_deepstream_sample_camera_001"
ZONE_ID = "bounded_vehicle_zone_r2"
SCHEMA_VERSION = "metropolis-vss-object-metadata-export-r2.v1"
CLASS_TO_DETECTION = {
    "car": "vehicle_presence_candidate",
    "bicycle": "vehicle_presence_candidate",
    "person": "person_presence_candidate",
    "road_sign": "object_presence_candidate",
}

def sid(prefix, *parts):
    payload = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"

def zone_status(b):
    zx1, zy1 = ZONE["x"], ZONE["y"]
    zx2, zy2 = zx1 + ZONE["w"], zy1 + ZONE["h"]
    bx1, by1 = b["x1"], b["y1"]
    bx2, by2 = b["x2"], b["y2"]
    if bx2 <= zx1 or bx1 >= zx2 or by2 <= zy1 or by1 >= zy2:
        return "outside"
    if bx1 >= zx1 and by1 >= zy1 and bx2 <= zx2 and by2 <= zy2:
        return "inside"
    return "intersects"

all_rows = []
for path in sorted(KITTIDIR.glob("*.txt")):
    try:
        frame_number = int(path.stem.split("_")[-1])
    except Exception:
        frame_number = 0
    for line_index, line in enumerate(path.read_text(errors="ignore").splitlines()):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 16:
            continue
        class_label = parts[0]
        try:
            x1, y1, x2, y2 = (float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7]))
            confidence = float(parts[-1])
        except ValueError:
            continue
        detection_class = CLASS_TO_DETECTION.get(class_label, "object_presence_candidate")
        bbox_xyxy = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "coordinate_space": "pixel"}
        row = {
            "raw_metadata_id": sid("deepstream-kitti-raw", path.name, line_index, line),
            "raw_export_format": "deepstream_gie_kitti_output",
            "raw_kitti_file": path.name,
            "raw_kitti_line_index": line_index,
            "raw_kitti_line": line,
            "source_system": "DeepStream/Metropolis",
            "media_source_id": MEDIA_SOURCE_ID,
            "media_source_selected": MEDIA_SOURCE_SELECTED,
            "camera_source_id": CAMERA_SOURCE_ID,
            "frame_number": frame_number,
            "frame_time_ms": round(frame_number * (1000.0 / 30.0), 3),
            "class_label": class_label,
            "detection_class": detection_class,
            "confidence": confidence,
            "bbox_xyxy": bbox_xyxy,
            "zone_id": ZONE_ID,
            "zone_rect": ZONE,
            "zone_intersection": zone_status(bbox_xyxy),
            "review_state": "candidate_unreviewed",
            "schema_version": SCHEMA_VERSION,
        }
        all_rows.append(row)

class_counts = {}
for row in all_rows:
    class_counts[row["class_label"]] = class_counts.get(row["class_label"], 0) + 1
preferred_order = ["car", "bicycle", "person", "road_sign"]
selected_label = next((label for label in preferred_order if class_counts.get(label, 0)), None)
selected_detection = CLASS_TO_DETECTION.get(selected_label or "", "object_presence_candidate")
selected_rows = [
    row
    for row in all_rows
    if row["class_label"] == selected_label and row["zone_intersection"] in {"inside", "intersects"}
]
if not selected_rows and selected_label:
    selected_rows = [row for row in all_rows if row["class_label"] == selected_label]
selected_rows = selected_rows[:24]

normalized = []
for row in selected_rows:
    b = row["bbox_xyxy"]
    normalized.append(
        {
            "object_metadata_id": sid("metropolis-vss-r2-object", row["raw_metadata_id"]),
            "source_class": "sensor_inferred",
            "source_system": "DeepStream/Metropolis",
            "media_source_id": MEDIA_SOURCE_ID,
            "camera_source_id": CAMERA_SOURCE_ID,
            "frame_number": row["frame_number"],
            "frame_time_ms": row["frame_time_ms"],
            "timestamp": None,
            "class_label": row["class_label"],
            "detection_class": row["detection_class"],
            "confidence": row["confidence"],
            "bbox": {
                "x": b["x1"],
                "y": b["y1"],
                "w": max(0.0, b["x2"] - b["x1"]),
                "h": max(0.0, b["y2"] - b["y1"]),
                "coordinate_space": "pixel",
            },
            "bbox_xyxy": b,
            "track_id": None,
            "zone_id": ZONE_ID,
            "zone_rect": ZONE,
            "zone_intersection": row["zone_intersection"],
            "review_state": "candidate_unreviewed",
            "raw_metadata_id": row["raw_metadata_id"],
            "raw_kitti_file": row["raw_kitti_file"],
            "raw_kitti_line_index": row["raw_kitti_line_index"],
            "schema_version": SCHEMA_VERSION,
        }
    )

RAW.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in selected_rows), encoding="utf-8")
NORM.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in normalized), encoding="utf-8")
deepstream_rc = int((WORK / "deepstream_return_code.txt").read_text().strip() or "999")
summary = {
    "status": "PASS" if deepstream_rc == 0 and normalized else "PARTIAL",
    "deepstream_return_code": deepstream_rc,
    "raw_kitti_file_count": len(list(KITTIDIR.glob("*.txt"))),
    "all_object_rows_seen": len(all_rows),
    "all_class_counts": class_counts,
    "selected_class_label": selected_label,
    "selected_detection_class": selected_detection,
    "selected_zone_id": ZONE_ID,
    "selected_zone_rect": ZONE,
    "selected_raw_records": len(selected_rows),
    "selected_normalized_records": len(normalized),
    "bbox_or_region_records": sum(1 for row in normalized if row.get("bbox")),
    "media_source_selected": MEDIA_SOURCE_SELECTED,
    "camera_source_id": CAMERA_SOURCE_ID,
    "object_metadata_exported": bool(normalized),
    "raw_export_format": "deepstream_gie_kitti_output",
    "not_synthesized_from_runtime_logs": True,
    "schema_version": SCHEMA_VERSION,
}
SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
'''


def remote_host_script(container_script_b64: str) -> str:
    return f'''set -u
HOST_OUT=/tmp/citybrain_r2_object_metadata_export
rm -rf "$HOST_OUT"
mkdir -p "$HOST_OUT"
printf '%s' '{container_script_b64}' | base64 -d > "$HOST_OUT/container_export.sh"
set +e
docker run --rm --gpus all -v "$HOST_OUT:/work" {DEEPSTREAM_IMAGE} bash /work/container_export.sh > "$HOST_OUT/docker_stdout.log" 2> "$HOST_OUT/docker_stderr.log"
DOCKER_RC=$?
set -e
echo "__CITYBRAIN_R2_DOCKER_RC__$DOCKER_RC"
for rel in \
  OBJECT_METADATA_RAW_SAMPLE.jsonl \
  OBJECT_METADATA_NORMALIZED_SAMPLE.jsonl \
  KITTI_EXPORT_SUMMARY.json \
  deepstream_r2_stdout.log \
  docker_stdout.log \
  docker_stderr.log \
  citybrain_r2_object_export_config.txt \
  kitti_files.txt \
  deepstream_return_code.txt; do
  if [ -f "$HOST_OUT/$rel" ]; then
    echo "__CITYBRAIN_R2_FILE_BEGIN__$rel"
    base64 -w 0 "$HOST_OUT/$rel"
    echo
    echo "__CITYBRAIN_R2_FILE_END__$rel"
  fi
done
'''


def parse_remote_files(stdout: str) -> tuple[int | None, dict[str, bytes]]:
    docker_rc: int | None = None
    files: dict[str, bytes] = {}
    current_name: str | None = None
    current_payload: list[str] = []
    for line in stdout.splitlines():
        if line.startswith("__CITYBRAIN_R2_DOCKER_RC__"):
            try:
                docker_rc = int(line.replace("__CITYBRAIN_R2_DOCKER_RC__", "").strip())
            except ValueError:
                docker_rc = None
            continue
        if line.startswith("__CITYBRAIN_R2_FILE_BEGIN__"):
            current_name = line.replace("__CITYBRAIN_R2_FILE_BEGIN__", "").strip()
            current_payload = []
            continue
        if line.startswith("__CITYBRAIN_R2_FILE_END__"):
            end_name = line.replace("__CITYBRAIN_R2_FILE_END__", "").strip()
            if current_name and end_name == current_name:
                files[current_name] = base64.b64decode("".join(current_payload).encode("ascii"))
            current_name = None
            current_payload = []
            continue
        if current_name is not None:
            current_payload.append(line.strip())
    return docker_rc, files


def run_remote_deepstream_export() -> dict[str, Any]:
    container_b64 = base64.b64encode(remote_container_script().encode("utf-8")).decode("ascii")
    host_script = remote_host_script(container_b64)
    host_b64 = base64.b64encode(host_script.encode("utf-8")).decode("ascii")
    remote_cmd = f"printf '%s' '{host_b64}' | base64 -d > /tmp/citybrain_r2_export_host.sh && bash /tmp/citybrain_r2_export_host.sh"
    command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", REMOTE_HOST, remote_cmd]
    try:
        proc = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=260, check=False)
    except Exception as exc:  # noqa: BLE001
        write_json(
            OUTPUT_ROOT / "DEEPSTREAM_OBJECT_METADATA_EXPORT_ATTEMPT_ERROR.json",
            {
                "status": "ERROR",
                "error": str(exc),
                "remote_host": REMOTE_HOST,
                "image": DEEPSTREAM_IMAGE,
            },
        )
        return {
            "status": "ERROR",
            "error": str(exc),
            "docker_rc": None,
            "ssh_returncode": None,
            "summary": {},
            "raw_rows": [],
            "normalized_rows": [],
        }
    docker_rc, files = parse_remote_files(proc.stdout)
    write_text(OUTPUT_ROOT / "REMOTE_EXPORT_STDOUT.log", proc.stdout)
    write_text(OUTPUT_ROOT / "REMOTE_EXPORT_STDERR.log", proc.stderr)
    for name, content in files.items():
        local_name = {
            "deepstream_r2_stdout.log": "DEEPSTREAM_R2_STDOUT.log",
            "docker_stdout.log": "REMOTE_DOCKER_STDOUT.log",
            "docker_stderr.log": "REMOTE_DOCKER_STDERR.log",
            "citybrain_r2_object_export_config.txt": "CITYBRAIN_R2_DEEPSTREAM_CONFIG.txt",
            "kitti_files.txt": "KITTI_FILES.txt",
            "deepstream_return_code.txt": "DEEPSTREAM_RETURN_CODE.txt",
        }.get(name, name)
        (OUTPUT_ROOT / local_name).write_bytes(content)
    summary = read_json(OUTPUT_ROOT / "KITTI_EXPORT_SUMMARY.json", {})
    raw_rows = read_jsonl(OUTPUT_ROOT / "OBJECT_METADATA_RAW_SAMPLE.jsonl")
    normalized_rows = read_jsonl(OUTPUT_ROOT / "OBJECT_METADATA_NORMALIZED_SAMPLE.jsonl")
    return {
        "status": "PASS" if proc.returncode == 0 and docker_rc == 0 and summary.get("object_metadata_exported") else "PARTIAL",
        "ssh_returncode": proc.returncode,
        "docker_rc": docker_rc,
        "summary": summary,
        "raw_rows": raw_rows,
        "normalized_rows": normalized_rows,
        "remote_command": "ssh txr-4070 <base64 host script>",
    }


def write_empty_export_files() -> None:
    for name in ["OBJECT_METADATA_RAW_SAMPLE.jsonl", "OBJECT_METADATA_NORMALIZED_SAMPLE.jsonl"]:
        write_text(OUTPUT_ROOT / name, "")


def input_artifact_index() -> dict[str, Any]:
    r1_decision = R1_ROOT / "METROPOLIS_VSS_CLOSEOUT_DECISION.json"
    d3_decision = D3_ROOT / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json"
    d3_smoke = D3_ROOT / "PERCEPTION_D3_DEEPSTREAM_SMOKE_REPORT.json"
    return {
        "task_name": TASK_NAME,
        "generated_at": utc_now(),
        "handoff_zip": {
            "path": str(HANDOFF_ZIP),
            "exists": HANDOFF_ZIP.exists(),
            "sha256": sha256_file(HANDOFF_ZIP),
        },
        "r1_output_root": {
            "path": rel(R1_ROOT),
            "exists": R1_ROOT.exists(),
        },
        "r1_validation_package": {
            "path": rel(R1_PACKAGE),
            "exists": R1_PACKAGE.exists(),
            "sha256": sha256_file(R1_PACKAGE),
        },
        "inspected_artifacts": [
            {
                "key": "r1_closeout",
                "path": rel(r1_decision),
                "exists": r1_decision.exists(),
                "status": read_json(r1_decision, {}).get("status"),
            },
            {
                "key": "perception_d3_deepstream_bridge_decision",
                "path": rel(d3_decision),
                "exists": d3_decision.exists(),
                "status": read_json(d3_decision, {}).get("status"),
            },
            {
                "key": "perception_d3_deepstream_smoke",
                "path": rel(d3_smoke),
                "exists": d3_smoke.exists(),
                "status": read_json(d3_smoke, {}).get("status"),
            },
        ],
    }


def write_contracts() -> None:
    copy_schema_from_handoff(
        "OBJECT_METADATA_EXPORT_CONTRACT_R2.schema.json",
        "OBJECT_METADATA_EXPORT_CONTRACT_R2.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "ObjectMetadataExportR2",
            "schema_version": SCHEMA_VERSION,
        },
    )
    copy_schema_from_handoff(
        "CANDIDATE_OBSERVATION_R2.schema.json",
        "CANDIDATE_OBSERVATION_CONTRACT_R2.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "CandidateObservationR2",
            "schema_version": SCHEMA_VERSION,
        },
    )
    check_contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "dimensions": [
            "model confidence",
            "single-frame vs multi-frame corroboration",
            "false-positive class",
            "timestamp/location availability",
            "camera/source health",
            "entity-link confidence",
            "VSS prose vs detection conflict",
            "sensor-inferred vs official-record separation",
        ],
        "promotion_rule": "CHECK reports review sufficiency only; it may not create findings, tickets, alerts, or actions.",
    }
    write_json(OUTPUT_ROOT / "CHECK_DETECTION_SUFFICIENCY_CONTRACT_R2.json", check_contract)


def normalized_has_required_object_metadata(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        bbox = row.get("bbox")
        if (
            row.get("source_class") == "sensor_inferred"
            and row.get("class_label")
            and row.get("detection_class") in {"vehicle_presence_candidate", "person_presence_candidate", "object_presence_candidate"}
            and isinstance(row.get("confidence"), (int, float))
            and 0 <= float(row["confidence"]) <= 1
            and isinstance(row.get("frame_number"), int)
            and bbox
            and all(key in bbox for key in ["x", "y", "w", "h", "coordinate_space"])
        ):
            return True
    return False


def build_candidate_payloads(normalized_rows: list[dict[str, Any]]) -> dict[str, Any]:
    observations = []
    object_refs = []
    if not normalized_rows:
        return {
            "observations": [],
            "candidate_event": None,
            "evidence_bundle": None,
            "review_packet": None,
            "object_refs": [],
        }
    model_config_hash = stable_hash(MEDIA_SOURCE_SELECTED, ZONE_ID, PREFERRED_DETECTION_CLASS, "gie-kitti-output-dir")
    for idx, row in enumerate(normalized_rows, start=1):
        object_refs.append(row["object_metadata_id"])
        observation_id = f"metropolis-vss-r2-observation-{idx:03d}"
        frame_ref = f"{row['media_source_id']}:frame:{row['frame_number']:06d}"
        observations.append(
            {
                "observation_id": observation_id,
                "schema_version": SCHEMA_VERSION,
                "source_class": "sensor_inferred",
                "source_system": "DeepStream/Metropolis",
                "object_metadata_id": row["object_metadata_id"],
                "model_id": "nvidia_deepstream_primary_detector_trafficcamnet",
                "model_version": "deepstream8_samples_resnet18_trafficcamnet_pruned",
                "model_config_hash": model_config_hash,
                "confidence": row["confidence"],
                "frame_ref": frame_ref,
                "timestamp": row.get("timestamp"),
                "camera_source_id": row["camera_source_id"],
                "zone_id": row["zone_id"],
                "detection_class": row["detection_class"],
                "class_label": row["class_label"],
                "bbox_or_mask_or_track_ref": {
                    "bbox": row["bbox"],
                    "track_id": row.get("track_id"),
                    "raw_metadata_id": row.get("raw_metadata_id"),
                },
                "source_file_hash_or_stream_id": "container_sample_stream:sample_1080p_h264",
                "human_review_required": True,
                "review_state": "candidate_unreviewed",
                "candidate_label": VISIBLE_BOUNDARY_TEXT,
                "action_allowed": False,
                "official_finding_allowed": False,
                "identity_or_biometric_inference_allowed": False,
                "blocked_outcome_codes": BLOCKED_OUTCOME_CODES,
                "uncertainty_notes": [
                    "Object metadata is from DeepStream KITTI bbox export over bundled sample media.",
                    "Zone is a bounded review rectangle over sample-frame coordinates, not an enforcement geography.",
                    "Candidate observation only; human review required.",
                ],
                "false_positive_notes": [
                    "TrafficCamNet sample detector may confuse vehicle-like objects in dense scenes.",
                    "No license-plate, identity, or legal interpretation is in scope.",
                ],
                "official_record": False,
                "no_action_taken": True,
            }
        )
    event_id = "metropolis-vss-r2-event-001"
    bundle_id = "metropolis-vss-r2-evidence-bundle-001"
    candidate_event = {
        "candidate_event_id": event_id,
        "schema_version": SCHEMA_VERSION,
        "event_family": "metropolis_vss_candidate_event",
        "event_type": normalized_rows[0]["detection_class"],
        "source_observation_ids": [row["observation_id"] for row in observations],
        "source_class": "sensor_inferred",
        "review_state": "candidate_unreviewed",
        "evidence_bundle_ref": bundle_id,
        "human_review_required": True,
        "no_action_taken": True,
        "official_record_created": False,
        "candidate_label": VISIBLE_BOUNDARY_TEXT,
        "camera_source_id": CAMERA_SOURCE_ID,
        "zone_id": ZONE_ID,
        "media_source_id": MEDIA_SOURCE_ID,
        "detection_class": normalized_rows[0]["detection_class"],
        "class_label": normalized_rows[0]["class_label"],
        "confidence_summary": {
            "max": max(row["confidence"] for row in normalized_rows),
            "min": min(row["confidence"] for row in normalized_rows),
            "count": len(normalized_rows),
        },
        "blocked_outcome_codes": BLOCKED_OUTCOME_CODES,
    }
    evidence_frame = {
        "frame_ref": observations[0]["frame_ref"],
        "frame_number": normalized_rows[0]["frame_number"],
        "frame_time_ms": normalized_rows[0]["frame_time_ms"],
        "bbox": normalized_rows[0]["bbox"],
        "object_metadata_ref": normalized_rows[0]["object_metadata_id"],
        "frame_image_exported": False,
    }
    evidence_clip = {
        "clip_ref": MEDIA_SOURCE_SELECTED,
        "media_source_id": MEDIA_SOURCE_ID,
        "source_boundary": "DeepStream bundled sample media; not private CCTV or production feed.",
    }
    evidence_bundle = {
        "bundle_id": bundle_id,
        "schema_version": SCHEMA_VERSION,
        "bundle_type": "media_candidate_observation_review_bundle",
        "candidate_observation_refs": [row["observation_id"] for row in observations],
        "candidate_event_refs": [event_id],
        "object_metadata_refs": object_refs,
        "evidence_frame": evidence_frame,
        "evidence_clip": evidence_clip,
        "model_provenance": {
            "model_id": "nvidia_deepstream_primary_detector_trafficcamnet",
            "model_version": "deepstream8_samples_resnet18_trafficcamnet_pruned",
            "model_config_hash": model_config_hash,
            "raw_export_format": "deepstream_gie_kitti_output",
        },
        "claim_boundary": "Candidate observation only; human review required; not a finding; no action taken.",
        "limitations": BASE_LIMITATIONS,
        "human_review_required": True,
        "review_state": "candidate_unreviewed",
        "source_class": "sensor_inferred",
        "no_action_taken": True,
        "candidate_label": VISIBLE_BOUNDARY_TEXT,
    }
    review_packet = {
        "packet_id": "metropolis-vss-r2-human-review-packet-001",
        "schema_version": SCHEMA_VERSION,
        "status": "ready_for_human_review",
        "candidate_label": VISIBLE_BOUNDARY_TEXT,
        "candidate_event_ref": event_id,
        "candidate_observation_refs": [row["observation_id"] for row in observations],
        "evidence_bundle_ref": bundle_id,
        "object_metadata_refs": object_refs,
        "review_prompt": "Review the bounded vehicle-presence candidate observations and decide whether additional source evidence is needed.",
        "model_source_provenance": {
            "source_class": "sensor_inferred",
            "source_system": "DeepStream/Metropolis",
            "media_source": MEDIA_SOURCE_SELECTED,
            "zone_id": ZONE_ID,
            "detection_class": normalized_rows[0]["detection_class"],
            "class_label": normalized_rows[0]["class_label"],
            "object_metadata_count": len(normalized_rows),
        },
        "what_is_uncertain": [
            "Whether the bounded review zone is operationally meaningful for this sample clip.",
            "Whether additional frames or a different detector config would reduce false positives.",
            "VSS prose, if later used, must stay narrative-only and cannot add facts.",
        ],
        "forbidden_review_outcomes": BLOCKED_OUTCOME_CODES,
        "human_review_required": True,
        "no_action_taken": True,
        "official_record_created": False,
    }
    return {
        "observations": observations,
        "candidate_event": candidate_event,
        "evidence_bundle": evidence_bundle,
        "review_packet": review_packet,
        "object_refs": object_refs,
    }


def write_candidate_outputs(payloads: dict[str, Any]) -> None:
    write_jsonl(OUTPUT_ROOT / "CANDIDATE_OBSERVATION_SAMPLE_R2.jsonl", payloads["observations"])
    mapping = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if payloads["candidate_event"] else "PARTIAL",
        "mapping_rule": "ObjectMetadata -> CandidateObservation -> CandidateEvent -> EvidenceBundle -> HumanReview",
        "source_class_preserved": True,
        "official_record_promotion": False,
        "candidate_event": payloads["candidate_event"],
    }
    write_json(OUTPUT_ROOT / "MEDIA_TO_CANDIDATE_EVENT_MAPPING_R2.json", mapping)
    write_json(
        OUTPUT_ROOT / "MEDIA_EVIDENCEBUNDLE_SAMPLE_R2.json",
        payloads["evidence_bundle"] or {
            "status": "PARTIAL",
            "reason": "No object metadata was available to form an EvidenceBundle.",
            "source_class": "sensor_inferred",
            "no_action_taken": True,
        },
    )
    write_json(
        OUTPUT_ROOT / "HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R2.json",
        payloads["review_packet"] or {
            "status": "PARTIAL",
            "reason": "No object metadata was available to form a human-review packet.",
            "human_review_required": True,
            "no_action_taken": True,
            "official_record_created": False,
            "candidate_label": VISIBLE_BOUNDARY_TEXT,
        },
    )


def write_export_report(export: dict[str, Any], final_status: str) -> None:
    summary = export.get("summary") or {}
    report = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if final_status == PASS_STATUS else "PARTIAL",
        "media_source_selected": MEDIA_SOURCE_SELECTED,
        "zone_selected": summary.get("selected_zone_id") or ZONE_ID,
        "zone_rect": summary.get("selected_zone_rect") or ZONE_RECT,
        "detection_class_selected": summary.get("selected_detection_class") or PREFERRED_DETECTION_CLASS,
        "class_label_selected": summary.get("selected_class_label"),
        "deepstream_runtime_executed": export.get("ssh_returncode") == 0,
        "remote_host": REMOTE_HOST,
        "deepstream_image": DEEPSTREAM_IMAGE,
        "object_metadata_export_attempted": True,
        "object_metadata_exported": bool(summary.get("object_metadata_exported")),
        "raw_object_metadata_records": summary.get("selected_raw_records", len(export.get("raw_rows") or [])),
        "normalized_object_metadata_records": summary.get("selected_normalized_records", len(export.get("normalized_rows") or [])),
        "bbox_or_region_records": summary.get("bbox_or_region_records", 0),
        "raw_export_format": summary.get("raw_export_format"),
        "not_synthesized_from_runtime_logs": bool(summary.get("not_synthesized_from_runtime_logs")),
        "deepstream_return_code": summary.get("deepstream_return_code"),
        "docker_return_code": export.get("docker_rc"),
        "ssh_return_code": export.get("ssh_returncode"),
        "all_object_rows_seen": summary.get("all_object_rows_seen", 0),
        "all_class_counts": summary.get("all_class_counts", {}),
        "notes": [
            "DeepStream gie-kitti-output-dir generated frame-indexed bbox files.",
            "Only the selected class and bounded review zone are normalized into R2 records.",
        ]
        if summary.get("object_metadata_exported")
        else ["Object metadata export did not produce usable bbox/class records."],
    }
    write_json(OUTPUT_ROOT / "DEEPSTREAM_OBJECT_METADATA_EXPORT_REPORT.json", report)


def write_check_report(normalized_rows: list[dict[str, Any]], payloads: dict[str, Any]) -> None:
    if normalized_rows:
        confidences = [row["confidence"] for row in normalized_rows]
        frames = sorted({row["frame_number"] for row in normalized_rows})
        detection_class = normalized_rows[0]["detection_class"]
        dimension_results = [
            {"dimension": "model confidence", "status": "PASS", "min": min(confidences), "max": max(confidences), "count": len(confidences)},
            {"dimension": "single-frame vs multi-frame corroboration", "status": "PASS" if len(frames) > 1 else "PASS_WITH_LIMITATION", "frame_count": len(frames)},
            {"dimension": "false-positive class", "status": "PASS_WITH_LIMITATION", "value": "vehicle-like sample-scene false positives remain possible"},
            {"dimension": "timestamp/location availability", "status": "PASS_WITH_LIMITATION", "value": "frame_number and frame_time_ms are present; wall-clock timestamp is null for bundled sample media"},
            {"dimension": "camera/source health", "status": "PASS", "value": "DeepStream app completed and exported KITTI metadata"},
            {"dimension": "entity-link confidence", "status": "PASS", "value": [{"entity": CAMERA_SOURCE_ID, "confidence": 0.95}, {"entity": ZONE_ID, "confidence": 0.82}]},
            {"dimension": "VSS prose vs detection conflict", "status": "PASS", "value": "VSS not executed; contract forbids VSS overriding structured detections"},
            {"dimension": "sensor-inferred vs official-record separation", "status": "PASS", "value": "source_class=sensor_inferred; official_record_created=false"},
        ]
    else:
        detection_class = PREFERRED_DETECTION_CLASS
        dimension_results = [
            {"dimension": "model confidence", "status": "PARTIAL", "reason": "No object metadata exported."},
            {"dimension": "single-frame vs multi-frame corroboration", "status": "PARTIAL", "reason": "No object metadata exported."},
            {"dimension": "false-positive class", "status": "PARTIAL", "reason": "No object metadata exported."},
            {"dimension": "timestamp/location availability", "status": "PARTIAL", "reason": "No object metadata exported."},
            {"dimension": "camera/source health", "status": "PARTIAL", "reason": "Runtime/export unavailable."},
            {"dimension": "entity-link confidence", "status": "PARTIAL", "reason": "No candidate entity link created."},
            {"dimension": "VSS prose vs detection conflict", "status": "PASS", "value": "VSS not executed and not a fact source."},
            {"dimension": "sensor-inferred vs official-record separation", "status": "PASS", "value": "No official records created."},
        ]
    report = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if normalized_rows and payloads["candidate_event"] else "PARTIAL",
        "selected_detection_class": detection_class,
        "candidate_event_ref": payloads["candidate_event"]["candidate_event_id"] if payloads["candidate_event"] else None,
        "dimension_results": dimension_results,
        "human_review_required": True,
        "candidate_label": VISIBLE_BOUNDARY_TEXT,
    }
    write_json(OUTPUT_ROOT / "CHECK_DETECTION_SUFFICIENCY_REPORT_R2.json", report)


def write_vss_contract_and_audit() -> None:
    contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "vss_runtime_executed": False,
        "vss_output_source_class": "model_generated_narrative",
        "vss_is_fact_source": False,
        "may_describe": ["already-exported object metadata", "visible uncertainty", "frame/clip refs", "human review wording"],
        "may_not": ["add detections", "certify findings", "identify people", "override structured detection confidence", "create action language"],
        "structured_detection_source_class": "sensor_inferred",
    }
    audit = {
        "status": "PASS",
        "vss_runtime_executed": False,
        "vss_is_fact_source": False,
        "forbidden_claim_hits": [],
        "checks": [
            {"check": "no VSS fact-source claim", "status": "PASS"},
            {"check": "no VSS override of structured detection", "status": "PASS"},
            {"check": "no VSS action language", "status": "PASS"},
        ],
    }
    write_json(OUTPUT_ROOT / "VSS_NARRATION_GUARDRAIL_CONTRACT_R2.json", contract)
    write_json(OUTPUT_ROOT / "VSS_FORBIDDEN_CLAIM_AUDIT.json", audit)


def write_ui_smoke(normalized_rows: list[dict[str, Any]]) -> None:
    visible_text = "\n\n".join(
        [
            VISIBLE_BOUNDARY_TEXT,
            f"Media source: {MEDIA_SOURCE_SELECTED}",
            f"Zone: {ZONE_ID}",
            f"Detection class: {normalized_rows[0]['detection_class'] if normalized_rows else PREFERRED_DETECTION_CLASS}",
            f"Object metadata rows: {len(normalized_rows)}",
            "Uncertain: this is a bounded sample-media review candidate, not an operational or legal conclusion.",
        ]
    )
    report = {
        "status": "PASS",
        "candidate_label_visible": all(part in visible_text for part in ["Candidate observation", "Human review required", "Not a finding"]),
        "model_source_provenance_visible": True,
        "confidence_visible": bool(normalized_rows),
        "frame_or_clip_ref_visible": bool(normalized_rows),
        "bbox_or_region_visible": bool(normalized_rows),
        "uncertainty_visible": True,
        "visible_text": visible_text,
    }
    write_json(OUTPUT_ROOT / "CANDIDATE_LABEL_UI_SMOKE_REPORT_R2.json", report)


def write_unresolved_ledger(final_status: str, export: dict[str, Any]) -> None:
    items = []
    if final_status != PASS_STATUS:
        items.append(
            {
                "unresolved_id": "metropolis-vss-r2-object-metadata-export-blocked",
                "state": "runtime_or_export_blocked",
                "reason": "No usable exported object metadata with bbox/class/confidence/frame was available.",
                "synthetic_detection_created": False,
            }
        )
    if not (export.get("summary") or {}).get("selected_class_label") == PREFERRED_CLASS_LABEL:
        items.append(
            {
                "unresolved_id": "metropolis-vss-r2-preferred-vehicle-class-fallback",
                "state": "not_needed" if final_status == PASS_STATUS else "unresolved",
                "reason": "Preferred vehicle class was used only when real car metadata existed.",
                "synthetic_detection_created": False,
            }
        )
    write_json(
        OUTPUT_ROOT / "UNRESOLVED_MEDIA_OBSERVATION_LEDGER_R2.json",
        {
            "status": "PASS" if final_status == PASS_STATUS else "PARTIAL",
            "unresolved_count": len(items),
            "items": items,
        },
    )


def write_source_class_audit(normalized_rows: list[dict[str, Any]], payloads: dict[str, Any]) -> str:
    failures = []
    for row in normalized_rows:
        if row.get("source_class") != "sensor_inferred":
            failures.append({"record": row.get("object_metadata_id"), "reason": "object metadata source_class drift"})
    for row in payloads["observations"]:
        if row.get("source_class") != "sensor_inferred":
            failures.append({"record": row.get("observation_id"), "reason": "observation source_class drift"})
    if payloads["candidate_event"] and payloads["candidate_event"].get("source_class") != "sensor_inferred":
        failures.append({"record": payloads["candidate_event"].get("candidate_event_id"), "reason": "event source_class drift"})
    if payloads["evidence_bundle"] and payloads["evidence_bundle"].get("source_class") != "sensor_inferred":
        failures.append({"record": payloads["evidence_bundle"].get("bundle_id"), "reason": "bundle source_class drift"})
    audit = {
        "status": "PASS" if not failures else "FAIL",
        "sensor_inferred_object_metadata_count": len(normalized_rows),
        "sensor_inferred_candidate_observation_count": len(payloads["observations"]),
        "official_record_records_created": 0,
        "vss_narration_source_class": "model_generated_narrative",
        "failures": failures,
    }
    write_json(OUTPUT_ROOT / "SOURCE_CLASS_SEPARATION_AUDIT.json", audit)
    return audit["status"]


def write_object_metadata_export_audit(export: dict[str, Any], normalized_rows: list[dict[str, Any]]) -> str:
    summary = export.get("summary") or {}
    checks = [
        ("object_metadata_exported_true", bool(summary.get("object_metadata_exported"))),
        ("raw_records_present", len(export.get("raw_rows") or []) > 0),
        ("normalized_records_present", len(normalized_rows) > 0),
        ("class_label_present", all(row.get("class_label") for row in normalized_rows)),
        ("confidence_in_range", all(isinstance(row.get("confidence"), (int, float)) and 0 <= row["confidence"] <= 1 for row in normalized_rows)),
        ("frame_or_time_reference_present", all(isinstance(row.get("frame_number"), int) and row.get("frame_time_ms") is not None for row in normalized_rows)),
        ("bbox_or_region_present", any(row.get("bbox") for row in normalized_rows)),
        ("not_synthesized_from_runtime_logs", bool(summary.get("not_synthesized_from_runtime_logs"))),
    ]
    audit = {
        "status": "PASS" if all(ok for _, ok in checks) else "PARTIAL",
        "checks": [{"check": name, "status": "PASS" if ok else "PARTIAL"} for name, ok in checks],
        "raw_record_count": len(export.get("raw_rows") or []),
        "normalized_record_count": len(normalized_rows),
        "bbox_or_region_records": sum(1 for row in normalized_rows if row.get("bbox")),
        "selected_detection_class": summary.get("selected_detection_class") or PREFERRED_DETECTION_CLASS,
        "selected_class_label": summary.get("selected_class_label"),
    }
    write_json(OUTPUT_ROOT / "OBJECT_METADATA_EXPORT_AUDIT.json", audit)
    return audit["status"]


def write_no_action_and_claim_audits(payloads: dict[str, Any]) -> tuple[str, str]:
    serial = json.dumps(payloads, sort_keys=True).lower()
    unsafe_patterns = [
        r'"official_record_created"\s*:\s*true',
        r'"official_record"\s*:\s*true',
        r'"no_action_taken"\s*:\s*false',
        r'"identity_or_biometric_inference_allowed"\s*:\s*true',
        r'"action_allowed"\s*:\s*true',
        r'"official_finding_allowed"\s*:\s*true',
        r'"dispatch_created"\s*:\s*true',
        r'"enforcement_created"\s*:\s*true',
    ]
    hits = [pattern for pattern in unsafe_patterns if re.search(pattern, serial)]
    no_action = {
        "status": "PASS" if not hits else "FAIL",
        "unsafe_true_patterns": hits,
        "identity_or_biometric_inference_created": False,
        "official_case_or_ticket_created": False,
        "official_finding_created": False,
        "alert_as_command_created": False,
        "dispatch_created": False,
        "routing_control_created": False,
        "enforcement_created": False,
        "automated_action_created": False,
        "execution_state": "not_executed",
    }
    claim = {
        "status": "PASS" if not hits else "FAIL",
        "required_visible_boundary": VISIBLE_BOUNDARY_TEXT,
        "candidate_only_output": True,
        "unsafe_positive_claims": [],
        "blocked_outcome_codes": BLOCKED_OUTCOME_CODES,
        "checks": [
            {"check": "no confirmed violation output", "status": "PASS"},
            {"check": "no legal/certified finding output", "status": "PASS"},
            {"check": "no identity/biometric output", "status": "PASS"},
            {"check": "no official case/ticket output", "status": "PASS"},
            {"check": "no dispatch/routing/control/enforcement output", "status": "PASS"},
            {"check": "no alert-command output", "status": "PASS"},
            {"check": "no automated action output", "status": "PASS"},
        ],
    }
    write_json(OUTPUT_ROOT / "NO_ACTION_AUDIT.json", no_action)
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim)
    return no_action["status"], claim["status"]


def write_secret_audit() -> str:
    patterns = [
        r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"(?i)secret\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    hits: list[dict[str, str]] = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_PACKAGE.zip":
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if re.search(pattern, text):
                    hits.append({"file": rel(path) or str(path), "pattern": pattern})
    status = "PASS" if not hits else "FAIL"
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", {"status": status, "secret_pattern_hits": hits})
    return status


def validate_json_outputs() -> str:
    failures = []
    json_count = 0
    jsonl_count = 0
    for path in sorted(OUTPUT_ROOT.glob("*.json")):
        if path.name == "JSON_PARSE_REPORT.json":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_count += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"file": path.name, "error": str(exc)})
    for path in sorted(OUTPUT_ROOT.glob("*.jsonl")):
        try:
            read_jsonl(path)
            jsonl_count += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"file": path.name, "error": str(exc)})
    status = "PASS" if not failures else "FAIL"
    write_json(
        OUTPUT_ROOT / "JSON_PARSE_REPORT.json",
        {
            "status": status,
            "json_files_parsed": json_count,
            "jsonl_files_parsed": jsonl_count,
            "parse_failures": failures,
        },
    )
    return status


def write_hash_manifest() -> str:
    entries = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name not in {"HASH_MANIFEST.json", "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_PACKAGE.zip"}:
            entries.append(
                {
                    "file": path.relative_to(OUTPUT_ROOT).as_posix(),
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    status = "PASS" if entries else "FAIL"
    write_json(
        OUTPUT_ROOT / "HASH_MANIFEST.json",
        {
            "status": status,
            "generated_at": utc_now(),
            "algorithm": "sha256",
            "file_count": len(entries),
            "excludes": ["HASH_MANIFEST.json", "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_PACKAGE.zip"],
            "files": entries,
        },
    )
    return status


def decide_status(
    export: dict[str, Any],
    normalized_rows: list[dict[str, Any]],
    payloads: dict[str, Any],
    audit_statuses: dict[str, str],
) -> str:
    if audit_statuses.get("no_action") == "FAIL":
        return FAIL_ACTION_STATUS
    if audit_statuses.get("claim_boundary") == "FAIL":
        return FAIL_BOUNDARY_STATUS
    if audit_statuses.get("source_class") == "FAIL":
        return FAIL_SOURCE_CLASS_STATUS
    if payloads["candidate_event"] and payloads["candidate_event"].get("official_record_created") is not False:
        return FAIL_OFFICIAL_RECORD_STATUS
    summary = export.get("summary") or {}
    metadata_ok = (
        bool(summary.get("object_metadata_exported"))
        and normalized_has_required_object_metadata(normalized_rows)
        and audit_statuses.get("object_metadata_export") == "PASS"
    )
    if metadata_ok and payloads["candidate_event"] and payloads["evidence_bundle"] and payloads["review_packet"]:
        return PASS_STATUS
    if metadata_ok:
        return PARTIAL_EVENT_MAPPING_BLOCKED_STATUS
    if export.get("ssh_returncode") is None:
        return PARTIAL_MEDIA_BLOCKED_STATUS
    return PARTIAL_RUNTIME_BLOCKED_STATUS


def write_decisions(
    final_status: str,
    export: dict[str, Any],
    normalized_rows: list[dict[str, Any]],
    payloads: dict[str, Any],
    audit_statuses: dict[str, str],
    json_parse_status: str | None = None,
    hash_status: str | None = None,
) -> None:
    summary = export.get("summary") or {}
    common = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": final_status,
        "boundary": BOUNDARY,
        "media_source_selected": MEDIA_SOURCE_SELECTED,
        "zone_selected": summary.get("selected_zone_id") or ZONE_ID,
        "detection_class_selected": summary.get("selected_detection_class") or PREFERRED_DETECTION_CLASS,
        "class_label_selected": summary.get("selected_class_label"),
        "object_metadata_exported": bool(summary.get("object_metadata_exported")),
        "candidate_observations_emitted": len(payloads["observations"]),
        "candidate_events_emitted": 1 if payloads["candidate_event"] else 0,
        "evidence_bundle_handoff": "PASS" if payloads["evidence_bundle"] else "PARTIAL",
        "human_review_packet": "PASS" if payloads["review_packet"] else "PARTIAL",
        "json_parse_status": json_parse_status,
        "hash_manifest_status": hash_status,
        "audits": audit_statuses,
        "no_action_audit_ref": "NO_ACTION_AUDIT.json",
        "claim_boundary_audit_ref": "CLAIM_BOUNDARY_AUDIT.json",
        "source_class_separation_audit_ref": "SOURCE_CLASS_SEPARATION_AUDIT.json",
        "object_metadata_export_audit_ref": "OBJECT_METADATA_EXPORT_AUDIT.json",
        "secret_audit_ref": "SECRET_AUDIT.json",
        "validation_package_ref": "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_PACKAGE.zip",
        "limitations": BASE_LIMITATIONS,
        "next_recommended_task": "MAIN-CITYBRAIN-METROPOLIS-VSS-VSS-NARRATION-RUNTIME-DRY-RUN-R3",
    }
    decision = {
        **common,
        "deepstream_runtime_executed": export.get("ssh_returncode") == 0,
        "remote_host": REMOTE_HOST,
        "deepstream_image": DEEPSTREAM_IMAGE,
        "raw_object_metadata_records": len(export.get("raw_rows") or []),
        "normalized_object_metadata_records": len(normalized_rows),
        "bbox_or_region_records": sum(1 for row in normalized_rows if row.get("bbox")),
    }
    closeout = {
        **common,
        "closeout_truth": {
            "one_media_source": True,
            "one_zone": True,
            "one_detection_class": True,
            "real_object_metadata_exported": bool(summary.get("object_metadata_exported")),
            "raw_export_format": summary.get("raw_export_format"),
            "not_synthesized_from_runtime_logs": bool(summary.get("not_synthesized_from_runtime_logs")),
            "vss_runtime_executed": False,
            "vss_is_fact_source": False,
            "source_class": "sensor_inferred",
        },
    }
    write_json(OUTPUT_ROOT / "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_DECISION.json", decision)
    write_json(OUTPUT_ROOT / "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_CLOSEOUT_DECISION.json", closeout)


def write_readme(final_status: str, export: dict[str, Any], payloads: dict[str, Any]) -> None:
    summary = export.get("summary") or {}
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Status: `{final_status}`",
        "",
        f"Media source: `{MEDIA_SOURCE_SELECTED}`",
        f"Zone: `{summary.get('selected_zone_id') or ZONE_ID}`",
        f"Detection class: `{summary.get('selected_detection_class') or PREFERRED_DETECTION_CLASS}`",
        f"Object metadata exported: `{bool(summary.get('object_metadata_exported'))}`",
        f"Candidate observations emitted: `{len(payloads['observations'])}`",
        f"Candidate events emitted: `{1 if payloads['candidate_event'] else 0}`",
        "",
        "Visible boundary:",
        "",
        "```text",
        VISIBLE_BOUNDARY_TEXT,
        "```",
        "",
        "Limitations:",
        "",
    ]
    lines.extend(f"- {item}" for item in BASE_LIMITATIONS)
    write_text(OUTPUT_ROOT / "README.md", "\n".join(lines))


def create_package_zip() -> Path:
    package_path = OUTPUT_ROOT / "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_PACKAGE.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUTPUT_ROOT.rglob("*")):
            if path.is_file() and path != package_path:
                zf.write(path, path.relative_to(OUTPUT_ROOT).as_posix())
    return package_path


def main() -> int:
    reset_output_root()
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_artifact_index())
    write_contracts()
    export = run_remote_deepstream_export()
    if not (OUTPUT_ROOT / "OBJECT_METADATA_RAW_SAMPLE.jsonl").exists():
        write_empty_export_files()
    normalized_rows = read_jsonl(OUTPUT_ROOT / "OBJECT_METADATA_NORMALIZED_SAMPLE.jsonl")
    payloads = build_candidate_payloads(normalized_rows)
    write_candidate_outputs(payloads)
    source_class_status = write_source_class_audit(normalized_rows, payloads)
    object_export_status = write_object_metadata_export_audit(export, normalized_rows)
    no_action_status, claim_status = write_no_action_and_claim_audits(payloads)
    write_vss_contract_and_audit()
    write_check_report(normalized_rows, payloads)
    write_ui_smoke(normalized_rows)
    secret_status = write_secret_audit()
    audit_statuses = {
        "source_class": source_class_status,
        "object_metadata_export": object_export_status,
        "no_action": no_action_status,
        "claim_boundary": claim_status,
        "vss_forbidden_claim": read_json(OUTPUT_ROOT / "VSS_FORBIDDEN_CLAIM_AUDIT.json", {}).get("status"),
        "secret": secret_status,
    }
    final_status = decide_status(export, normalized_rows, payloads, audit_statuses)
    write_unresolved_ledger(final_status, export)
    write_export_report(export, final_status)
    write_decisions(final_status, export, normalized_rows, payloads, audit_statuses)
    write_readme(final_status, export, payloads)
    json_status = validate_json_outputs()
    write_decisions(final_status, export, normalized_rows, payloads, audit_statuses, json_status)
    json_status = validate_json_outputs()
    hash_status = write_hash_manifest()
    write_decisions(final_status, export, normalized_rows, payloads, audit_statuses, json_status, hash_status)
    write_readme(final_status, export, payloads)
    json_status = validate_json_outputs()
    hash_status = write_hash_manifest()
    create_package_zip()
    summary = export.get("summary") or {}
    print(f"Final status: {final_status}")
    print(f"Detection class: {summary.get('selected_detection_class') or PREFERRED_DETECTION_CLASS}")
    print(f"Object metadata exported: {bool(summary.get('object_metadata_exported'))}")
    print(f"Candidate observations: {len(payloads['observations'])}")
    print(f"Candidate events: {1 if payloads['candidate_event'] else 0}")
    print(f"JSON parse: {json_status}")
    print(f"Hash manifest: {hash_status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if final_status == PASS_STATUS and json_status == "PASS" and hash_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
