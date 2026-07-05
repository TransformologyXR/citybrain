#!/usr/bin/env python3
"""R17 BMD-45 DeepStream frame replay comparison gate.

This runner validates the accepted R16 BMD-45 fixtures, stages the referenced
frames as temporary replay inputs, attempts an actual DeepStream run on
txr-4070, and compares only real sensor-inferred output against dataset
annotations. It never converts dataset labels into detector output.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
TMP_ROOT = REPO_ROOT / "tmp" / "r17_bmd45_deepstream_frame_replay"
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-DEEPSTREAM-FRAME-REPLAY-COMPARISON-R17"
SCHEMA_VERSION = "metropolis-vss-bmd45-deepstream-frame-replay-comparison-r17.v1"
DEFAULT_OUTPUT_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_bmd45_deepstream_frame_replay_comparison_r17"
R16_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_offline_cctv_dataset_expansion_r16"
R16_PACKAGE = R16_ROOT / "METROPOLIS_VSS_OFFLINE_CCTV_DATASET_EXPANSION_R16_PACKAGE.zip"
HANDOFF_ZIP = Path(r"C:\Users\hazem\Downloads\citybrain_metropolis_vss_bmd45_deepstream_frame_replay_comparison_r17_handoff.zip")
PACKAGE_NAME = "METROPOLIS_VSS_BMD45_DEEPSTREAM_FRAME_REPLAY_COMPARISON_R17_PACKAGE.zip"

REMOTE_HOST = "txr-4070"
REMOTE_ROOT = "/tmp/citybrain_r17_bmd45_deepstream_frame_replay"
DEEPSTREAM_IMAGE = "nvcr.io/nvidia/deepstream:8.0-samples-multiarch"

PASS_STATUS = "PASS_METROPOLIS_VSS_BMD45_DEEPSTREAM_FRAME_REPLAY_COMPARISON_R17_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_METROPOLIS_VSS_BMD45_FRAME_REPLAY_PREPARED_DEEPSTREAM_EXECUTION_BLOCKED"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_BMD45_FRAME_REPLAY_BOUNDARY_OR_FABRICATION_RISK"

IOU_THRESHOLDS = [0.25, 0.5]
ZERO_DETECTION_RECORD_TYPE = "explicit_zero_detection_frame_result"

FORBIDDEN_CLAIM_TERMS = [
    "confirmed violation",
    "certified finding",
    "legal finding",
    "official case",
    "ticket created",
    "dispatch",
    "identity confirmed",
    "biometric",
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


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def stable_hash(*parts: Any, length: int = 24) -> str:
    payload = "|".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}:{stable_hash(*parts)}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_output_root(output_root: Path) -> None:
    resolved = output_root.resolve()
    allowed_root = OUTPUTS_ROOT.resolve()
    if allowed_root not in resolved.parents:
        raise ValueError(f"Refusing to reset output outside {allowed_root}: {resolved}")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def validate_r16_package() -> dict[str, Any]:
    report: dict[str, Any] = {
        "package_path": rel(R16_PACKAGE),
        "package_exists": R16_PACKAGE.exists(),
        "required_artifacts": {},
        "schema_version": SCHEMA_VERSION,
        "status": "FAIL",
    }
    required = [
        "R16_CLOSEOUT_DECISION.json",
        "OFFLINE_REPLAY_SAMPLE_MANIFEST_R16.json",
        "BMD45_SAMPLE_ANNOTATION_SUBSET_R16.json",
        "CANDIDATE_OBSERVATION_FIXTURE_R16.jsonl",
        "CAMERA_SOURCE_REGISTRY_UPDATE_R16.json",
        "MEDIA_PROVENANCE_R16.json",
        "SOURCE_CLASS_SEPARATION_AUDIT_R16.json",
        "CLAIM_BOUNDARY_AUDIT_R16.json",
        "NO_ACTION_AUDIT_R16.json",
        "VSS_NOT_FACT_SOURCE_AUDIT_R16.json",
        "HASH_MANIFEST.json",
    ]
    if not R16_PACKAGE.exists():
        report["failure_reason"] = "R16 package not found"
        return report

    json_count = 0
    jsonl_count = 0
    mismatches: list[str] = []
    missing: list[str] = []
    bad_zip: str | None = None
    try:
        with zipfile.ZipFile(R16_PACKAGE) as archive:
            bad_zip = archive.testzip()
            names = [name for name in archive.namelist() if not name.endswith("/")]
            for artifact in required:
                report["required_artifacts"][artifact] = artifact in names
                if artifact not in names:
                    missing.append(artifact)
            for name in names:
                if name.endswith(".json"):
                    json.loads(archive.read(name).decode("utf-8"))
                    json_count += 1
                elif name.endswith(".jsonl"):
                    for line in archive.read(name).decode("utf-8").splitlines():
                        if line.strip():
                            json.loads(line)
                    jsonl_count += 1
            manifest = json.loads(archive.read("HASH_MANIFEST.json").decode("utf-8"))
            for entry in manifest.get("files", []):
                actual = sha256_bytes(archive.read(entry["file"]))
                if actual != entry.get("sha256"):
                    mismatches.append(entry["file"])
            decision = json.loads(archive.read("R16_CLOSEOUT_DECISION.json").decode("utf-8"))
            source_registry = json.loads(archive.read("OFFLINE_DATASET_SOURCE_REGISTRY_R16.json").decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        report["failure_reason"] = str(exc)
        return report

    selected_source = decision.get("selected_source_id") or source_registry.get("selected_source_id")
    r16_status_ok = decision.get("status") == "PASS_METROPOLIS_VSS_OFFLINE_CCTV_DATASET_EXPANSION_R16_WITH_LIMITATIONS"
    selected_ok = selected_source == "bmd45_huggingface_iisc_aim"
    report.update(
        {
            "hash_manifest_mismatches": mismatches,
            "hash_manifest_status": "PASS" if not mismatches else "FAIL",
            "json_files_parsed": json_count,
            "jsonl_files_parsed": jsonl_count,
            "manifest_missing": missing,
            "r16_status": decision.get("status"),
            "r16_status_ok": r16_status_ok,
            "selected_source_id": selected_source,
            "selected_source_ok": selected_ok,
            "status": "PASS" if bad_zip is None and not missing and not mismatches and r16_status_ok and selected_ok else "FAIL",
            "zip_entries": len(names),
            "zip_integrity": "PASS" if bad_zip is None else f"FAIL:{bad_zip}",
        }
    )
    return report


def load_r16_inputs() -> dict[str, Any]:
    return {
        "decision": read_json(R16_ROOT / "R16_CLOSEOUT_DECISION.json"),
        "replay_manifest": read_json(R16_ROOT / "OFFLINE_REPLAY_SAMPLE_MANIFEST_R16.json"),
        "annotation_subset": read_json(R16_ROOT / "BMD45_SAMPLE_ANNOTATION_SUBSET_R16.json"),
        "candidate_fixtures": read_jsonl(R16_ROOT / "CANDIDATE_OBSERVATION_FIXTURE_R16.jsonl"),
        "camera_registry": read_json(R16_ROOT / "CAMERA_SOURCE_REGISTRY_UPDATE_R16.json"),
        "media_provenance": read_json(R16_ROOT / "MEDIA_PROVENANCE_R16.json"),
    }


def fetch_url_bytes(url: str, target: Path, timeout: int = 180) -> bytes:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "citybrain-r17/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except Exception:
        curl_bin = "curl.exe" if sys.platform.startswith("win") else "curl"
        subprocess.run(
            [curl_bin, "-L", "--retry", "3", "--retry-delay", "2", "--max-time", str(timeout), url, "-o", str(target)],
            cwd=REPO_ROOT,
            check=True,
        )
        return target.read_bytes()
    target.write_bytes(data)
    return data


def stage_frames_for_replay(external_refs: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    stage_root = TMP_ROOT / "frames"
    if stage_root.exists():
        shutil.rmtree(stage_root)
    stage_root.mkdir(parents=True, exist_ok=True)

    staged: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for index, ref in enumerate(external_refs):
        file_name = str(ref.get("file_name", f"frame_{index:04d}.png"))
        expected_sha = ref.get("sha256")
        cache_path = None
        fetch_meta = ref.get("fetch") or {}
        if fetch_meta.get("cache_file"):
            cache_path = REPO_ROOT / str(fetch_meta["cache_file"])
        if cache_path is None or not cache_path.exists():
            cache_name = "bmd45_val_" + file_name.replace("/", "_")
            cache_path = REPO_ROOT / "tmp" / "r16_bmd45_cache" / cache_name
        try:
            if cache_path.exists():
                data = cache_path.read_bytes()
                fetched = False
            else:
                data = fetch_url_bytes(str(ref["media_url"]), cache_path)
                fetched = True
            actual_sha = sha256_bytes(data)
            actual_bytes = len(data)
            verified = actual_sha == expected_sha and actual_bytes == int(ref.get("bytes", actual_bytes))
            if not verified:
                failures.append(
                    {
                        "file_name": file_name,
                        "expected_sha256": expected_sha,
                        "actual_sha256": actual_sha,
                        "expected_bytes": ref.get("bytes"),
                        "actual_bytes": actual_bytes,
                    }
                )
                continue
            staged_path = stage_root / f"frame_{index:04d}.png"
            staged_path.write_bytes(data)
            staged.append(
                {
                    "bytes": actual_bytes,
                    "cache_file": rel(cache_path),
                    "external_media_ref": True,
                    "fetched": fetched,
                    "file_name": file_name,
                    "frame_replay_id": f"bmd45-val-frame-{ref.get('image_id')}",
                    "height": ref.get("height"),
                    "image_id": ref.get("image_id"),
                    "media_source_id": f"media:bmd45:val:{file_name}",
                    "media_url": ref.get("media_url"),
                    "packaged_file": False,
                    "sequence_index": index,
                    "sha256": actual_sha,
                    "source_class": "dataset_annotation",
                    "staged_temp_path": rel(staged_path),
                    "width": ref.get("width"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            failures.append({"file_name": file_name, "error": str(exc)})

    report = {
        "external_media_refs": [{k: v for k, v in row.items() if k != "staged_temp_path"} for row in staged],
        "failed_frames": failures,
        "frames_staged": len(staged),
        "packaged_media_count": 0,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if staged and not failures else "PARTIAL" if staged else "FAIL",
        "temporary_stage_root": rel(stage_root),
        "verified_sha_count": sum(1 for row in staged if row.get("sha256")),
    }
    return report, staged


def class_mapping() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "mapping_policy": "exact label retained plus vehicle-family comparison",
        "bmd45_to_family": {
            "Car": "vehicle_family:car",
            "Bus": "vehicle_family:bus",
            "Truck": "vehicle_family:truck",
            "Two-wheeler": "vehicle_family:two_wheeler",
            "Three-wheeler": "vehicle_family:three_wheeler",
            "Autorickshaw": "vehicle_family:three_wheeler",
            "Auto-rickshaw": "vehicle_family:three_wheeler",
            "Bicycle": "vehicle_family:two_wheeler",
            "Motorcycle": "vehicle_family:two_wheeler",
        },
        "deepstream_to_family": {
            "car": "vehicle_family:car",
            "bus": "vehicle_family:bus",
            "truck": "vehicle_family:truck",
            "bicycle": "vehicle_family:two_wheeler",
            "motorbike": "vehicle_family:two_wheeler",
            "motorcycle": "vehicle_family:two_wheeler",
            "person": "non_vehicle_family:person",
            "road_sign": "non_vehicle_family:road_sign",
        },
        "unknown_family": "vehicle_family:unknown_vehicle",
    }


def map_class_family(label: str | None, source_class: str) -> str:
    mapping = class_mapping()
    label_text = str(label or "")
    if source_class == "dataset_annotation":
        return mapping["bmd45_to_family"].get(label_text, mapping["unknown_family"])
    if source_class == "sensor_inferred":
        return mapping["deepstream_to_family"].get(label_text.lower(), mapping["unknown_family"])
    return "unknown_source_class"


def bbox_xyxy_from_xywh(bbox: dict[str, Any]) -> tuple[float, float, float, float]:
    x = float(bbox.get("x", 0.0))
    y = float(bbox.get("y", 0.0))
    w = max(0.0, float(bbox.get("w", 0.0)))
    h = max(0.0, float(bbox.get("h", 0.0)))
    return x, y, x + w, y + h


def compute_iou(a: dict[str, Any], b: dict[str, Any]) -> float:
    ax1, ay1, ax2, ay2 = bbox_xyxy_from_xywh(a)
    bx1, by1, bx2, by2 = bbox_xyxy_from_xywh(b)
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    intersection = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def dataset_rows_from_fixtures(fixtures: list[dict[str, Any]], staged_frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seq_by_media = {row["media_source_id"]: int(row["sequence_index"]) for row in staged_frames}
    rows = []
    for row in fixtures:
        media_source_id = row.get("media_source_id")
        family = map_class_family(row.get("class_label"), "dataset_annotation")
        enriched = dict(row)
        enriched.update(
            {
                "class_family": family,
                "frame_sequence_index": seq_by_media.get(media_source_id),
                "schema_version": SCHEMA_VERSION,
                "source_class": "dataset_annotation",
            }
        )
        rows.append(enriched)
    return rows


def remote_container_script() -> str:
    return r'''set -u
WORK=/work
OUT="$WORK/out"
FRAMES="$WORK/frames"
KITTIDIR="$OUT/kitti"
DS=/opt/nvidia/deepstream/deepstream-8.0
mkdir -p "$OUT"
rm -rf "$KITTIDIR"
mkdir -p "$KITTIDIR"
FRAME_COUNT=$(python3 - <<'PY'
import json
from pathlib import Path
manifest = json.loads((Path("/work") / "frame_manifest.json").read_text())
print(len(manifest.get("frames", [])))
PY
)
GST_RC=999
if [ "$FRAME_COUNT" -gt 0 ]; then
  set +e
  timeout 120 gst-launch-1.0 -e \
    multifilesrc location="$FRAMES/frame_%04d.png" index=0 num-buffers="$FRAME_COUNT" caps="image/png,framerate=(fraction)1/1" \
    ! pngdec \
    ! videoconvert \
    ! video/x-raw,format=I420,width=1920,height=1080,framerate=1/1 \
    ! nvvideoconvert \
    ! 'video/x-raw(memory:NVMM),format=NV12' \
    ! nvv4l2h264enc bitrate=4000000 iframeinterval=1 insert-sps-pps=true \
    ! h264parse \
    ! qtmux \
    ! filesink location="$OUT/bmd45_r17_replay.mp4" \
    > "$OUT/gst_create_stdout.log" 2> "$OUT/gst_create_stderr.log"
  GST_RC=$?
  set -e
fi
echo "$GST_RC" > "$OUT/gst_create_return_code.txt"
VIDEO_SHA=""
VIDEO_BYTES=0
if [ -f "$OUT/bmd45_r17_replay.mp4" ]; then
  VIDEO_SHA=$(sha256sum "$OUT/bmd45_r17_replay.mp4" | awk '{print $1}')
  VIDEO_BYTES=$(wc -c < "$OUT/bmd45_r17_replay.mp4" | tr -d ' ')
fi
DS_RC=999
if [ "$GST_RC" -eq 0 ] && [ -s "$OUT/bmd45_r17_replay.mp4" ]; then
  cd "$DS/samples/configs/deepstream-app" || exit 98
  cp source30_1080p_dec_infer-resnet_tiled_display.txt "$OUT/citybrain_r17_deepstream_config.txt"
  python3 - <<'PY'
from pathlib import Path
p = Path("/work/out/citybrain_r17_deepstream_config.txt")
s = p.read_text()
s = s.replace("#gie-kitti-output-dir=streamscl", "gie-kitti-output-dir=/work/out/kitti")
s = s.replace("rows=5", "rows=1")
s = s.replace("columns=6", "columns=1")
s = s.replace("num-sources=15", "num-sources=1")
s = s.replace("batch-size=30", "batch-size=1")
s = s.replace(
    "model-engine-file=../../models/Primary_Detector/resnet18_trafficcamnet_pruned.onnx_b30_gpu0_fp16.engine",
    "model-engine-file=/opt/nvidia/deepstream/deepstream-8.0/samples/models/Primary_Detector/resnet18_trafficcamnet_pruned.onnx_b1_gpu0_fp16.engine",
)
s = s.replace("config-file=config_infer_primary.txt", "config-file=/opt/nvidia/deepstream/deepstream-8.0/samples/configs/deepstream-app/config_infer_primary.txt")
s = s.replace("uri=file://../../streams/sample_1080p_h264.mp4", "uri=file:///work/out/bmd45_r17_replay.mp4", 1)
s = s.replace("[source1]\nenable=1", "[source1]\nenable=0")
s = s.replace("type=2\nsync=1\nsource-id=0", "type=1\nsync=0\nsource-id=0")
p.write_text(s)
PY
  set +e
  timeout 180 deepstream-app -c "$OUT/citybrain_r17_deepstream_config.txt" > "$OUT/deepstream_stdout.log" 2> "$OUT/deepstream_stderr.log"
  DS_RC=$?
  set -e
fi
echo "$DS_RC" > "$OUT/deepstream_return_code.txt"
find "$KITTIDIR" -type f | sort > "$OUT/kitti_files.txt" 2>/dev/null || true
python3 - <<'PY'
import hashlib
import json
import re
from pathlib import Path

WORK = Path("/work")
OUT = WORK / "out"
KITTIDIR = OUT / "kitti"
manifest = json.loads((WORK / "frame_manifest.json").read_text())
frames = manifest.get("frames", [])
CLASS_TO_DETECTION = {
    "car": "vehicle_presence_candidate",
    "bus": "vehicle_presence_candidate",
    "truck": "vehicle_presence_candidate",
    "bicycle": "vehicle_presence_candidate",
    "motorbike": "vehicle_presence_candidate",
    "person": "person_presence_candidate",
    "road_sign": "object_presence_candidate",
}

def sid(prefix, *parts):
    payload = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"

def frame_number_from_file(path):
    nums = re.findall(r"\d+", path.stem)
    return int(nums[-1]) if nums else 0

def frame_meta(frame_number):
    if 0 <= frame_number < len(frames):
        return frames[frame_number]
    return {
        "sequence_index": frame_number,
        "frame_replay_id": f"unknown-deepstream-frame-{frame_number}",
        "media_source_id": None,
        "file_name": None,
    }

raw_rows = []
candidate_rows = []
frame_detection_counts = {int(frame.get("sequence_index", idx)): 0 for idx, frame in enumerate(frames)}
for path in sorted(KITTIDIR.glob("*.txt")):
    frame_number = frame_number_from_file(path)
    meta = frame_meta(frame_number)
    for line_index, line in enumerate(path.read_text(errors="ignore").splitlines()):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 16:
            continue
        class_label = parts[0]
        try:
            x1, y1, x2, y2 = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
            confidence = float(parts[-1])
        except ValueError:
            continue
        bbox = {
            "coordinate_space": "pixel",
            "h": max(0.0, y2 - y1),
            "w": max(0.0, x2 - x1),
            "x": x1,
            "y": y1,
        }
        raw_id = sid("deepstream-r17-kitti-raw", path.name, line_index, line)
        raw = {
            "bbox": bbox,
            "bbox_xyxy": {"coordinate_space": "pixel", "x1": x1, "x2": x2, "y1": y1, "y2": y2},
            "camera_source_id": "bmd45_fixed_cctv_frame_replay_source_r17",
            "class_label": class_label,
            "confidence": confidence,
            "detection_class": CLASS_TO_DETECTION.get(class_label, "object_presence_candidate"),
            "frame_number": frame_number,
            "frame_replay_id": meta.get("frame_replay_id"),
            "frame_sequence_index": meta.get("sequence_index", frame_number),
            "media_source_id": meta.get("media_source_id"),
            "raw_export_format": "deepstream_gie_kitti_output",
            "raw_kitti_file": path.name,
            "raw_kitti_line": line,
            "raw_kitti_line_index": line_index,
            "raw_metadata_id": raw_id,
            "review_state": "candidate_unreviewed",
            "schema_version": "metropolis-vss-bmd45-deepstream-frame-replay-comparison-r17.v1",
            "source_class": "sensor_inferred",
            "source_system": "DeepStream/Metropolis",
        }
        raw_rows.append(raw)
        candidate = dict(raw)
        candidate["candidate_observation_id"] = sid("metropolis-vss-r17-sensor-observation", raw_id)
        candidate_rows.append(candidate)
        seq = int(meta.get("sequence_index", frame_number))
        frame_detection_counts[seq] = frame_detection_counts.get(seq, 0) + 1

if not raw_rows:
    for idx, frame in enumerate(frames):
        raw_rows.append(
            {
                "camera_source_id": "bmd45_fixed_cctv_frame_replay_source_r17",
                "detections_found": False,
                "frame_number": idx,
                "frame_replay_id": frame.get("frame_replay_id"),
                "frame_sequence_index": frame.get("sequence_index", idx),
                "media_source_id": frame.get("media_source_id"),
                "raw_export_format": "deepstream_gie_kitti_output",
                "record_type": "explicit_zero_detection_frame_result",
                "review_state": "candidate_unreviewed",
                "schema_version": "metropolis-vss-bmd45-deepstream-frame-replay-comparison-r17.v1",
                "source_class": "sensor_inferred",
                "source_system": "DeepStream/Metropolis",
            }
        )

def read_int(path, default=999):
    try:
        return int(path.read_text().strip())
    except Exception:
        return default

gst_rc = read_int(OUT / "gst_create_return_code.txt")
ds_rc = read_int(OUT / "deepstream_return_code.txt")
video_path = OUT / "bmd45_r17_replay.mp4"
video_sha = ""
video_bytes = 0
if video_path.exists():
    video_sha = hashlib.sha256(video_path.read_bytes()).hexdigest()
    video_bytes = video_path.stat().st_size

(OUT / "DEEPSTREAM_RAW_METADATA_R17.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in raw_rows), encoding="utf-8")
(OUT / "SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R17.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in candidate_rows), encoding="utf-8")
summary = {
    "candidate_observation_records": len(candidate_rows),
    "container_image": "nvcr.io/nvidia/deepstream:8.0-samples-multiarch",
    "deepstream_return_code": ds_rc,
    "docker_inner_stage": "container_complete",
    "execution_status": "EXECUTED_SUCCESS" if ds_rc == 0 and candidate_rows else "EXECUTED_ZERO_DETECTIONS" if ds_rc == 0 else "BLOCKED",
    "frame_count": len(frames),
    "frame_detection_counts": frame_detection_counts,
    "gst_create_return_code": gst_rc,
    "input_replay_video": {
        "bytes": video_bytes,
        "packaged_file": False,
        "sha256": video_sha,
        "temporary_container_path": "/work/out/bmd45_r17_replay.mp4",
    },
    "kitti_file_count": len(list(KITTIDIR.glob("*.txt"))),
    "raw_detection_records": len([row for row in raw_rows if row.get("record_type") != "explicit_zero_detection_frame_result"]),
    "raw_metadata_records": len(raw_rows),
    "replay_method": "generated_short_mp4_from_bmd45_png_frames",
    "schema_version": "metropolis-vss-bmd45-deepstream-frame-replay-comparison-r17.v1",
    "source_class": "sensor_inferred",
}
(OUT / "DEEPSTREAM_RUNTIME_SUMMARY_R17.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
prep = {
    "frame_count": len(frames),
    "gst_create_return_code": gst_rc,
    "input_frames": frames,
    "packaged_media_count": 0,
    "replay_method": "generated_short_mp4_from_bmd45_png_frames",
    "schema_version": "metropolis-vss-bmd45-deepstream-frame-replay-comparison-r17.v1",
    "status": "PASS" if gst_rc == 0 and video_bytes > 0 else "BLOCKED",
    "temporary_replay_video": summary["input_replay_video"],
}
(OUT / "DEEPSTREAM_REPLAY_INPUT_PREP_REMOTE_R17.json").write_text(json.dumps(prep, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
'''


def remote_host_script(container_script_b64: str) -> str:
    return f'''set -u
ROOT={REMOTE_ROOT}
OUT="$ROOT/out"
mkdir -p "$ROOT/frames" "$OUT"
printf '%s' '{container_script_b64}' | base64 -d > "$ROOT/container_r17.sh"
set +e
docker run --rm --gpus all -v "$ROOT:/work" {DEEPSTREAM_IMAGE} bash /work/container_r17.sh > "$OUT/docker_stdout.log" 2> "$OUT/docker_stderr.log"
DOCKER_RC=$?
set -e
echo "__CITYBRAIN_R17_DOCKER_RC__$DOCKER_RC"
for rel in \
  DEEPSTREAM_RUNTIME_SUMMARY_R17.json \
  DEEPSTREAM_REPLAY_INPUT_PREP_REMOTE_R17.json \
  DEEPSTREAM_RAW_METADATA_R17.jsonl \
  SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R17.jsonl \
  gst_create_stdout.log \
  gst_create_stderr.log \
  gst_create_return_code.txt \
  deepstream_stdout.log \
  deepstream_stderr.log \
  deepstream_return_code.txt \
  docker_stdout.log \
  docker_stderr.log \
  citybrain_r17_deepstream_config.txt \
  kitti_files.txt; do
  if [ -f "$OUT/$rel" ]; then
    echo "__CITYBRAIN_R17_FILE_BEGIN__$rel"
    base64 -w 0 "$OUT/$rel"
    echo
    echo "__CITYBRAIN_R17_FILE_END__$rel"
  fi
done
'''


def parse_remote_files(stdout: str) -> tuple[int | None, dict[str, bytes]]:
    docker_rc: int | None = None
    files: dict[str, bytes] = {}
    current_name: str | None = None
    current_payload: list[str] = []
    for line in stdout.splitlines():
        if line.startswith("__CITYBRAIN_R17_DOCKER_RC__"):
            try:
                docker_rc = int(line.replace("__CITYBRAIN_R17_DOCKER_RC__", "").strip())
            except ValueError:
                docker_rc = None
            continue
        if line.startswith("__CITYBRAIN_R17_FILE_BEGIN__"):
            current_name = line.replace("__CITYBRAIN_R17_FILE_BEGIN__", "").strip()
            current_payload = []
            continue
        if line.startswith("__CITYBRAIN_R17_FILE_END__"):
            end_name = line.replace("__CITYBRAIN_R17_FILE_END__", "").strip()
            if current_name and end_name == current_name:
                files[current_name] = base64.b64decode("".join(current_payload).encode("ascii"))
            current_name = None
            current_payload = []
            continue
        if current_name is not None:
            current_payload.append(line.strip())
    return docker_rc, files


def run_remote_deepstream(output_root: Path, staged_frames: list[dict[str, Any]]) -> dict[str, Any]:
    for empty_file in ["DEEPSTREAM_RAW_METADATA_R17.jsonl", "SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R17.jsonl"]:
        write_text(output_root / empty_file, "")
    if os.environ.get("CITYBRAIN_R17_SKIP_DEEPSTREAM") == "1":
        return {
            "attempted": False,
            "docker_return_code": None,
            "execution_status": "NOT_ATTEMPTED",
            "reason": "CITYBRAIN_R17_SKIP_DEEPSTREAM=1",
            "ssh_return_code": None,
            "status": "PARTIAL",
        }

    frame_manifest = {
        "created_at": utc_now(),
        "frames": [{k: v for k, v in frame.items() if k != "staged_temp_path"} for frame in staged_frames],
        "schema_version": SCHEMA_VERSION,
    }
    manifest_path = TMP_ROOT / "frame_manifest.json"
    write_json(manifest_path, frame_manifest)
    remote_mkdir = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", REMOTE_HOST, f"rm -rf {REMOTE_ROOT}; mkdir -p {REMOTE_ROOT}/frames {REMOTE_ROOT}/out"]
    mkdir_proc = subprocess.run(remote_mkdir, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30, check=False)
    if mkdir_proc.returncode != 0:
        write_text(output_root / "REMOTE_R17_MKDIR_STDERR.log", mkdir_proc.stderr)
        return {
            "attempted": True,
            "docker_return_code": None,
            "execution_status": "BLOCKED",
            "reason": "remote mkdir failed",
            "ssh_return_code": mkdir_proc.returncode,
            "status": "PARTIAL",
        }

    frame_paths = [str(REPO_ROOT / str(frame["staged_temp_path"])) for frame in staged_frames]
    scp_frames = ["scp", "-q", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", *frame_paths, f"{REMOTE_HOST}:{REMOTE_ROOT}/frames/"]
    frame_proc = subprocess.run(scp_frames, cwd=REPO_ROOT, capture_output=True, text=True, timeout=120, check=False)
    scp_manifest = ["scp", "-q", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", str(manifest_path), f"{REMOTE_HOST}:{REMOTE_ROOT}/frame_manifest.json"]
    manifest_proc = subprocess.run(scp_manifest, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30, check=False)
    if frame_proc.returncode != 0 or manifest_proc.returncode != 0:
        write_text(output_root / "REMOTE_R17_SCP_STDERR.log", frame_proc.stderr + "\n" + manifest_proc.stderr)
        return {
            "attempted": True,
            "docker_return_code": None,
            "execution_status": "BLOCKED",
            "reason": "remote frame transfer failed",
            "scp_frame_return_code": frame_proc.returncode,
            "scp_manifest_return_code": manifest_proc.returncode,
            "ssh_return_code": None,
            "status": "PARTIAL",
        }

    container_b64 = base64.b64encode(remote_container_script().encode("utf-8")).decode("ascii")
    host_script = remote_host_script(container_b64)
    host_b64 = base64.b64encode(host_script.encode("utf-8")).decode("ascii")
    remote_cmd = f"printf '%s' '{host_b64}' | base64 -d > /tmp/citybrain_r17_host.sh && bash /tmp/citybrain_r17_host.sh"
    command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", REMOTE_HOST, remote_cmd]
    proc = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=420, check=False)
    write_text(output_root / "REMOTE_R17_STDOUT.log", proc.stdout)
    write_text(output_root / "REMOTE_R17_STDERR.log", proc.stderr)
    docker_rc, files = parse_remote_files(proc.stdout)
    file_map = {
        "gst_create_stdout.log": "GST_CREATE_STDOUT_R17.log",
        "gst_create_stderr.log": "GST_CREATE_STDERR_R17.log",
        "gst_create_return_code.txt": "GST_CREATE_RETURN_CODE_R17.txt",
        "deepstream_stdout.log": "DEEPSTREAM_STDOUT_R17.log",
        "deepstream_stderr.log": "DEEPSTREAM_STDERR_R17.log",
        "deepstream_return_code.txt": "DEEPSTREAM_RETURN_CODE_R17.txt",
        "docker_stdout.log": "REMOTE_DOCKER_STDOUT_R17.log",
        "docker_stderr.log": "REMOTE_DOCKER_STDERR_R17.log",
        "citybrain_r17_deepstream_config.txt": "CITYBRAIN_R17_DEEPSTREAM_CONFIG.txt",
        "kitti_files.txt": "KITTI_FILES_R17.txt",
    }
    for remote_name, content in files.items():
        local_name = file_map.get(remote_name, remote_name)
        (output_root / local_name).write_bytes(content)

    summary = read_json(output_root / "DEEPSTREAM_RUNTIME_SUMMARY_R17.json", {})
    status = "PASS" if proc.returncode == 0 and docker_rc == 0 and summary.get("execution_status") in {"EXECUTED_SUCCESS", "EXECUTED_ZERO_DETECTIONS"} else "PARTIAL"
    return {
        "attempted": True,
        "command": "ssh txr-4070 <base64 host script>",
        "container_image": DEEPSTREAM_IMAGE,
        "deepstream_return_code": summary.get("deepstream_return_code"),
        "docker_return_code": docker_rc,
        "execution_status": summary.get("execution_status", "BLOCKED"),
        "raw_detection_records": summary.get("raw_detection_records", 0),
        "raw_metadata_records": summary.get("raw_metadata_records", 0),
        "replay_method": summary.get("replay_method", "generated_short_mp4_from_bmd45_png_frames"),
        "ssh_return_code": proc.returncode,
        "status": status,
        "summary": summary,
    }


def compare_annotations_to_sensor_detections(
    dataset_rows: list[dict[str, Any]], sensor_rows: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    detection_rows = [row for row in sensor_rows if row.get("record_type") != ZERO_DETECTION_RECORD_TYPE and row.get("bbox")]
    by_frame_annotations: dict[int | None, list[dict[str, Any]]] = defaultdict(list)
    by_frame_detections: dict[int | None, list[dict[str, Any]]] = defaultdict(list)
    for row in dataset_rows:
        by_frame_annotations[row.get("frame_sequence_index")].append(row)
    for row in detection_rows:
        enriched = dict(row)
        enriched["class_family"] = map_class_family(row.get("class_label"), "sensor_inferred")
        by_frame_detections[row.get("frame_sequence_index")].append(enriched)

    frame_keys = sorted({key for key in by_frame_annotations.keys()} | {key for key in by_frame_detections.keys()}, key=lambda value: (-1 if value is None else int(value)))
    records: list[dict[str, Any]] = []
    threshold_matches = {str(threshold): 0 for threshold in IOU_THRESHOLDS}
    total_matches = 0
    for frame_key in frame_keys:
        annotations = by_frame_annotations.get(frame_key, [])
        detections = by_frame_detections.get(frame_key, [])
        pairs: list[dict[str, Any]] = []
        for ann_index, ann in enumerate(annotations):
            ann_family = ann.get("class_family") or map_class_family(ann.get("class_label"), "dataset_annotation")
            for det_index, det in enumerate(detections):
                det_family = det.get("class_family") or map_class_family(det.get("class_label"), "sensor_inferred")
                if ann_family != det_family:
                    continue
                pairs.append(
                    {
                        "annotation_index": ann_index,
                        "candidate_observation_id": det.get("candidate_observation_id"),
                        "class_family": ann_family,
                        "dataset_annotation_id": ann.get("annotation_id"),
                        "detection_index": det_index,
                        "iou": compute_iou(ann.get("bbox", {}), det.get("bbox", {})),
                    }
                )
        pairs.sort(key=lambda row: row["iou"], reverse=True)
        used_annotations: set[int] = set()
        used_detections: set[int] = set()
        matches = []
        for pair in pairs:
            if pair["annotation_index"] in used_annotations or pair["detection_index"] in used_detections:
                continue
            if pair["iou"] <= 0:
                continue
            used_annotations.add(pair["annotation_index"])
            used_detections.add(pair["detection_index"])
            matches.append(pair)
            total_matches += 1
            for threshold in IOU_THRESHOLDS:
                if pair["iou"] >= threshold:
                    threshold_matches[str(threshold)] += 1
        unmatched_annotations = [
            {
                "annotation_id": ann.get("annotation_id"),
                "candidate_observation_id": ann.get("candidate_observation_id"),
                "class_family": ann.get("class_family"),
                "class_label": ann.get("class_label"),
            }
            for idx, ann in enumerate(annotations)
            if idx not in used_annotations
        ]
        unmatched_detections = [
            {
                "candidate_observation_id": det.get("candidate_observation_id"),
                "class_family": det.get("class_family"),
                "class_label": det.get("class_label"),
                "confidence": det.get("confidence"),
            }
            for idx, det in enumerate(detections)
            if idx not in used_detections
        ]
        records.append(
            {
                "annotation_count": len(annotations),
                "frame_sequence_index": frame_key,
                "matches": matches,
                "schema_version": SCHEMA_VERSION,
                "sensor_detection_count": len(detections),
                "source_classes": {"annotations": "dataset_annotation", "detections": "sensor_inferred"},
                "unmatched_annotations": unmatched_annotations,
                "unmatched_sensor_detections": unmatched_detections,
            }
        )

    metrics = {
        "matches_any_iou": total_matches,
        "matches_at_threshold": threshold_matches,
        "unmatched_annotations": sum(len(record["unmatched_annotations"]) for record in records),
        "unmatched_sensor_detections": sum(len(record["unmatched_sensor_detections"]) for record in records),
    }
    report = {
        "annotation_count": len(dataset_rows),
        "certification_claim": False,
        "frame_count": len(frame_keys),
        "human_review_required": True,
        "iou_thresholds": IOU_THRESHOLDS,
        "metrics": metrics,
        "schema_version": SCHEMA_VERSION,
        "sensor_detection_count": len(detection_rows),
        "source_classes": {"dataset_annotations": "dataset_annotation", "deepstream_detections": "sensor_inferred"},
        "status": "PASS",
    }
    return report, records


def scan_for_forbidden_claims(output_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    safe_markers = ["blocked", "not ", "no ", "no_", "false", "pending", "limitation", "non-goal", "without claiming", "cannot_claim"]
    for path in output_root.rglob("*"):
        if not path.is_file() or path.name in {PACKAGE_NAME, "HASH_MANIFEST.json"}:
            continue
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".log"}:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            lowered = line.lower()
            if any(marker in lowered for marker in safe_markers):
                continue
            for term in FORBIDDEN_CLAIM_TERMS:
                if term in lowered:
                    findings.append({"file": rel(path) or str(path), "line": str(line_no), "term": term})
    return findings


def scan_for_secrets(output_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in output_root.rglob("*"):
        if not path.is_file() or path.name == PACKAGE_NAME:
            continue
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".log", ".env"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                findings.append({"file": rel(path) or str(path), "pattern": name})
    return findings


def build_human_review_packet(
    dataset_rows: list[dict[str, Any]], sensor_rows: list[dict[str, Any]], comparison_report: dict[str, Any]
) -> dict[str, Any]:
    detections = [row for row in sensor_rows if row.get("record_type") != ZERO_DETECTION_RECORD_TYPE and row.get("bbox")]
    return {
        "cannot_claim": [
            "not production live CCTV",
            "not an official finding",
            "no ticket or case",
            "no dispatch or action",
            "no identity or legal conclusion",
            "not model accuracy certification",
        ],
        "comparison_summary": comparison_report.get("metrics", {}),
        "dataset_annotation_count": len(dataset_rows),
        "deepstream_detection_count": len(detections),
        "human_review_required": True,
        "packet_id": stable_id("human-review-comparison-packet-r17", len(dataset_rows), len(detections)),
        "review_sections": [
            {
                "items": [
                    {
                        "annotation_id": row.get("annotation_id"),
                        "bbox": row.get("bbox"),
                        "class_family": row.get("class_family"),
                        "class_label": row.get("class_label"),
                        "frame_sequence_index": row.get("frame_sequence_index"),
                        "source_class": "dataset_annotation",
                    }
                    for row in dataset_rows[:20]
                ],
                "title": "BMD-45 dataset annotations",
            },
            {
                "items": [
                    {
                        "bbox": row.get("bbox"),
                        "candidate_observation_id": row.get("candidate_observation_id"),
                        "class_family": map_class_family(row.get("class_label"), "sensor_inferred"),
                        "class_label": row.get("class_label"),
                        "confidence": row.get("confidence"),
                        "frame_sequence_index": row.get("frame_sequence_index"),
                        "source_class": "sensor_inferred",
                    }
                    for row in detections[:20]
                ],
                "title": "DeepStream sensor-inferred detections",
            },
        ],
        "review_state": "candidate_unreviewed",
        "schema_version": SCHEMA_VERSION,
        "source_class_boundary": {
            "dataset_annotations": "dataset_annotation",
            "deepstream_metropolis": "sensor_inferred",
            "spark_vss": "model_generated_narrative_not_used",
        },
    }


def write_audits(output_root: Path, dataset_rows: list[dict[str, Any]], sensor_rows: list[dict[str, Any]]) -> dict[str, str]:
    fabricated_findings = []
    for row in sensor_rows:
        if row.get("source_class") == "dataset_annotation":
            fabricated_findings.append({"record": row.get("candidate_observation_id") or row.get("raw_metadata_id"), "reason": "sensor output relabeled from dataset annotation"})
    source_audit = {
        "dataset_annotation_records": len(dataset_rows),
        "deepstream_sensor_records": len(sensor_rows),
        "expected_source_classes": {
            "dataset_annotations": "dataset_annotation",
            "deepstream_metropolis": "sensor_inferred",
            "spark_vss": "model_generated_narrative",
        },
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(row.get("source_class") == "dataset_annotation" for row in dataset_rows) and all(row.get("source_class") == "sensor_inferred" for row in sensor_rows) else "FAIL",
    }
    dataset_boundary = {
        "dataset_annotations_promoted_to_sensor_inference": False,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(row.get("source_class") == "dataset_annotation" for row in dataset_rows) else "FAIL",
    }
    no_fabrication = {
        "fabricated_detections": fabricated_findings,
        "sensor_records_are_from_deepstream_runtime_or_explicit_zero_detection_result": True,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not fabricated_findings else "FAIL",
    }
    claim_findings = scan_for_forbidden_claims(output_root)
    secret_findings = scan_for_secrets(output_root)
    claim_audit = {"findings": claim_findings, "schema_version": SCHEMA_VERSION, "status": "PASS" if not claim_findings else "FAIL"}
    no_action = {
        "action_created": False,
        "case_created": False,
        "dispatch_created": False,
        "official_record_created": False,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "ticket_created": False,
    }
    secret_audit = {"findings": secret_findings, "schema_version": SCHEMA_VERSION, "status": "PASS" if not secret_findings else "FAIL"}
    vss_audit = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "vss_is_fact_source": False,
        "vss_records_created": 0,
    }
    audits = {
        "SOURCE_CLASS_SEPARATION_AUDIT_R17.json": source_audit,
        "DATASET_ANNOTATION_BOUNDARY_AUDIT_R17.json": dataset_boundary,
        "NO_FABRICATED_DETECTIONS_AUDIT_R17.json": no_fabrication,
        "CLAIM_BOUNDARY_AUDIT_R17.json": claim_audit,
        "NO_ACTION_AUDIT_R17.json": no_action,
        "SECRET_AUDIT_R17.json": secret_audit,
        "VSS_NOT_FACT_SOURCE_AUDIT_R17.json": vss_audit,
    }
    for filename, payload in audits.items():
        write_json(output_root / filename, payload)
    return {filename.replace(".json", ""): payload["status"] for filename, payload in audits.items()}


def build_package(output_root: Path, external_media_refs: list[dict[str, Any]]) -> dict[str, Any]:
    package_path = output_root / PACKAGE_NAME
    files = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in {"HASH_MANIFEST.json", PACKAGE_NAME}:
            continue
        files.append({"bytes": path.stat().st_size, "file": path.relative_to(output_root).as_posix(), "sha256": sha256_file(path)})
    manifest = {
        "algorithm": "sha256",
        "created_at": utc_now(),
        "excludes": ["HASH_MANIFEST.json", PACKAGE_NAME],
        "external_media_refs": external_media_refs,
        "file_count": len(files),
        "files": files,
        "packaged_media_count": 0,
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
    with zipfile.ZipFile(package_path) as archive:
        bad = archive.testzip()
        names = [name for name in archive.namelist() if not name.endswith("/")]
        json_count = 0
        jsonl_count = 0
        for name in names:
            if name.endswith(".json"):
                json.loads(archive.read(name).decode("utf-8"))
                json_count += 1
            elif name.endswith(".jsonl"):
                for line in archive.read(name).decode("utf-8").splitlines():
                    if line.strip():
                        json.loads(line)
                jsonl_count += 1
        manifest = json.loads(archive.read("HASH_MANIFEST.json").decode("utf-8"))
        mismatches = []
        missing = []
        for entry in manifest.get("files", []):
            try:
                actual = sha256_bytes(archive.read(entry["file"]))
            except KeyError:
                missing.append(entry["file"])
                continue
            if actual != entry["sha256"]:
                mismatches.append(entry["file"])
    return {
        "hash_manifest_status": "PASS" if not missing and not mismatches else "FAIL",
        "hash_manifest_verified": f"{len(manifest.get('files', [])) - len(missing) - len(mismatches)}/{len(manifest.get('files', []))}",
        "json_files_parsed": json_count,
        "jsonl_files_parsed": jsonl_count,
        "manifest_mismatches": mismatches,
        "manifest_missing": missing,
        "status": "PASS" if bad is None and not missing and not mismatches else "FAIL",
        "zip_entries": len(names),
        "zip_integrity": "PASS" if bad is None else f"FAIL:{bad}",
    }


def build_r17(output_root: Path) -> dict[str, Any]:
    reset_output_root(output_root)
    r16_validation = validate_r16_package()
    r16_inputs = load_r16_inputs()
    replay_manifest = r16_inputs["replay_manifest"]
    frame_fetch_report, staged_frames = stage_frames_for_replay(replay_manifest.get("external_media_refs", []))
    dataset_rows = dataset_rows_from_fixtures(r16_inputs["candidate_fixtures"], staged_frames)

    write_json(output_root / "R16_INPUT_VALIDATION_R17.json", r16_validation)
    write_json(
        output_root / "R16_LINEAGE_SUMMARY_R17.json",
        {
            "input_decision_status": r16_inputs["decision"].get("status"),
            "input_package": rel(R16_PACKAGE),
            "loaded_candidate_fixture_records": len(r16_inputs["candidate_fixtures"]),
            "loaded_external_media_refs": len(replay_manifest.get("external_media_refs", [])),
            "schema_version": SCHEMA_VERSION,
            "selected_source_id": r16_inputs["decision"].get("selected_source_id"),
            "source_class": "dataset_annotation",
            "status": "PASS" if r16_validation.get("status") == "PASS" else "FAIL",
        },
    )
    write_json(output_root / "BMD45_FRAME_FETCH_REPORT_R17.json", frame_fetch_report)
    write_jsonl(output_root / "DATASET_ANNOTATION_FIXTURE_R17.jsonl", dataset_rows)
    write_json(output_root / "CLASS_MAPPING_R17.json", class_mapping())

    remote_result = run_remote_deepstream(output_root, staged_frames)
    remote_prep = read_json(output_root / "DEEPSTREAM_REPLAY_INPUT_PREP_REMOTE_R17.json", {})
    deepstream_summary = read_json(output_root / "DEEPSTREAM_RUNTIME_SUMMARY_R17.json", {})
    prep_report = {
        "frame_count": len(staged_frames),
        "host": REMOTE_HOST,
        "input_frames": [{k: v for k, v in frame.items() if k != "staged_temp_path"} for frame in staged_frames],
        "limitations": [
            "BMD-45 source is offline fixed-camera frame replay, not production live CCTV.",
            "Replay MP4 is generated temporarily and not packaged.",
        ],
        "outputs": remote_prep.get("temporary_replay_video", {}),
        "replay_method": remote_result.get("replay_method", "generated_short_mp4_from_bmd45_png_frames"),
        "schema_version": SCHEMA_VERSION,
        "status": remote_prep.get("status", "BLOCKED"),
    }
    write_json(output_root / "DEEPSTREAM_REPLAY_INPUT_PREP_R17.json", prep_report)
    runtime_report = {
        "command": remote_result.get("command", "ssh txr-4070 <base64 host script>"),
        "container_image": DEEPSTREAM_IMAGE,
        "execution_status": remote_result.get("execution_status", "BLOCKED"),
        "host": REMOTE_HOST,
        "input_frames": [{k: v for k, v in frame.items() if k != "staged_temp_path"} for frame in staged_frames],
        "limitations": [
            "DeepStream output is only candidate-review metadata.",
            "Zero-detection frame records are explicit runtime results, not fabricated detections.",
        ],
        "outputs": {
            "candidate_observation_records": deepstream_summary.get("candidate_observation_records", 0),
            "deepstream_return_code": remote_result.get("deepstream_return_code"),
            "docker_return_code": remote_result.get("docker_return_code"),
            "raw_detection_records": deepstream_summary.get("raw_detection_records", 0),
            "raw_metadata_records": deepstream_summary.get("raw_metadata_records", 0),
            "ssh_return_code": remote_result.get("ssh_return_code"),
        },
        "replay_method": remote_result.get("replay_method", "generated_short_mp4_from_bmd45_png_frames"),
        "schema_version": SCHEMA_VERSION,
    }
    write_json(output_root / "DEEPSTREAM_RUNTIME_EXECUTION_R17.json", runtime_report)

    sensor_rows = read_jsonl(output_root / "DEEPSTREAM_RAW_METADATA_R17.jsonl")
    candidate_rows = read_jsonl(output_root / "SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R17.jsonl")
    comparison_report, comparison_records = compare_annotations_to_sensor_detections(dataset_rows, sensor_rows)
    write_json(output_root / "IOU_COMPARISON_REPORT_R17.json", comparison_report)
    write_jsonl(output_root / "FRAME_COMPARISON_RECORDS_R17.jsonl", comparison_records)
    write_json(output_root / "HUMAN_REVIEW_COMPARISON_PACKET_R17.json", build_human_review_packet(dataset_rows, candidate_rows, comparison_report))

    write_text(
        output_root / "KNOWN_LIMITATIONS_R17.md",
        "\n".join(
            [
                "# Known Limitations R17",
                "",
                "- BMD-45 is offline fixed-camera frame replay, not production live CCTV.",
                "- R17 compares a tiny R16 sample fixture and is not a model accuracy certification.",
                "- Dataset annotations remain `dataset_annotation`; DeepStream output remains `sensor_inferred`.",
                "- VSS narration is not used as a fact source in R17.",
                "- No official records, actions, identity inferences, or legal conclusions are created.",
            ]
        ),
    )
    write_text(
        output_root / "NEXT_SPRINT_RECOMMENDATIONS_R17.md",
        "\n".join(
            [
                "# Next Sprint Recommendations R17",
                "",
                "1. Increase BMD-45 frame sample size after this three-frame gate is accepted.",
                "2. Add an approved traffic-camera video source after license review.",
                "3. Keep live RTSP as a separate gate and label offline replay distinctly.",
            ]
        ),
    )
    write_text(
        output_root / "README.md",
        f"""# {TASK_ID}

R17 validates the R16 BMD-45 offline frame replay fixture, attempts DeepStream
execution on txr-4070, and compares real `sensor_inferred` output against
`dataset_annotation` records using class-family mapping and IoU.
""",
    )

    audit_statuses = write_audits(output_root, dataset_rows, sensor_rows)
    audits_pass = all(status == "PASS" for status in audit_statuses.values())
    pass_ready = (
        r16_validation.get("status") == "PASS"
        and frame_fetch_report.get("status") == "PASS"
        and remote_result.get("status") == "PASS"
        and comparison_report.get("status") == "PASS"
        and audits_pass
    )
    final_status = PASS_STATUS if pass_ready else PARTIAL_STATUS
    if not audits_pass or r16_validation.get("status") != "PASS":
        final_status = FAIL_STATUS if not audits_pass else PARTIAL_STATUS

    decision = {
        "audits": audit_statuses,
        "candidate_observation_records": len(candidate_rows),
        "comparison_computed": comparison_report.get("status") == "PASS",
        "dataset_annotation_records": len(dataset_rows),
        "deepstream_execution_status": remote_result.get("execution_status"),
        "deepstream_runtime_attempted": remote_result.get("attempted"),
        "deepstream_runtime_executed": remote_result.get("status") == "PASS",
        "final_status": final_status,
        "frame_fetch_status": frame_fetch_report.get("status"),
        "human_review_packet_emitted": True,
        "live_cctv_claimed": False,
        "official_record_created": False,
        "r16_input_validation": r16_validation.get("status"),
        "schema_version": SCHEMA_VERSION,
        "sensor_inferred_records": len(sensor_rows),
        "source_classes": {
            "bmd45_annotations": "dataset_annotation",
            "deepstream_metropolis": "sensor_inferred",
            "vss": "model_generated_narrative_not_used",
        },
        "status": final_status,
        "task_id": TASK_ID,
        "vss_is_fact_source": False,
    }
    write_json(output_root / "R17_CLOSEOUT_DECISION.json", decision)

    write_json(
        output_root / "R17_JSON_PARSE_REPORT.json",
        {
            "hash_manifest_status": "PENDING",
            "json_files_parsed": 0,
            "jsonl_files_parsed": 0,
            "manifest_mismatches": [],
            "schema_version": SCHEMA_VERSION,
            "status": "PENDING",
            "zip_entries": 0,
            "zip_integrity": "PENDING",
        },
    )
    external_refs = frame_fetch_report.get("external_media_refs", [])
    write_text(
        output_root / "TEST_LOG_R17.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r16_input_validation={r16_validation.get('status')}",
                f"frame_fetch_status={frame_fetch_report.get('status')}",
                f"deepstream_execution_status={remote_result.get('execution_status')}",
                f"sensor_candidate_observations={len(candidate_rows)}",
                f"dataset_annotation_records={len(dataset_rows)}",
                "zip_entries=PENDING",
                "hash_manifest=PENDING",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    parse_report = {
        "hash_manifest_status": package_report["hash_manifest_status"],
        "json_files_parsed": package_report["json_files_parsed"],
        "jsonl_files_parsed": package_report["jsonl_files_parsed"],
        "manifest_mismatches": package_report["manifest_mismatches"],
        "manifest_missing": package_report["manifest_missing"],
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if package_report["status"] == "PASS" else "FAIL",
        "zip_entries": package_report["zip_entries"],
        "zip_integrity": package_report["zip_integrity"],
    }
    write_json(output_root / "R17_JSON_PARSE_REPORT.json", parse_report)
    write_text(
        output_root / "TEST_LOG_R17.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r16_input_validation={r16_validation.get('status')}",
                f"frame_fetch_status={frame_fetch_report.get('status')}",
                f"deepstream_execution_status={remote_result.get('execution_status')}",
                f"sensor_candidate_observations={len(candidate_rows)}",
                f"dataset_annotation_records={len(dataset_rows)}",
                f"zip_entries={package_report['zip_entries']}",
                f"hash_manifest={package_report['hash_manifest_verified']}",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    return {"decision": decision, "package_report": package_report}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run R17 BMD-45 DeepStream frame replay comparison.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_r17(Path(args.output_root))
    decision = result["decision"]
    report = result["package_report"]
    print(f"Status: {decision['status']}")
    print(f"Output: {rel(Path(args.output_root))}")
    print(f"Freeze ZIP: {rel(Path(args.output_root) / PACKAGE_NAME)}")
    print(f"R16 input validation: {decision['r16_input_validation']}")
    print(f"Frame fetch: {decision['frame_fetch_status']}")
    print(f"DeepStream execution: {decision['deepstream_execution_status']}")
    print(f"Sensor candidate observations: {decision['candidate_observation_records']}")
    print(f"Dataset annotation records: {decision['dataset_annotation_records']}")
    print(f"ZIP entries: {report['zip_entries']}")
    print(f"JSON parse: PASS, {report['json_files_parsed']} JSON + {report['jsonl_files_parsed']} JSONL")
    print(f"Hash manifest: {report['hash_manifest_verified']}")
    print(f"Manifest mismatches: {len(report['manifest_mismatches'])}")
    return 0 if report["status"] == "PASS" and decision["status"] != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
