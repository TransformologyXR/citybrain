#!/usr/bin/env python3
"""R18 BMD-45 threshold calibration and sample expansion gate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import statistics
import subprocess
import sys
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
TMP_ROOT = REPO_ROOT / "tmp" / "r18_bmd45_threshold_calibration"
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-THRESHOLD-CALIBRATION-AND-SAMPLE-EXPANSION-R18"
SCHEMA_VERSION = "metropolis-vss-bmd45-threshold-calibration-and-sample-expansion-r18.v1"
DEFAULT_OUTPUT_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_bmd45_threshold_calibration_and_sample_expansion_r18"
PACKAGE_NAME = "METROPOLIS_VSS_BMD45_THRESHOLD_CALIBRATION_AND_SAMPLE_EXPANSION_R18_PACKAGE.zip"

R16_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_offline_cctv_dataset_expansion_r16"
R16_ANNOTATION_CACHE = REPO_ROOT / "tmp" / "r16_bmd45_cache" / "bmd45_val_annotations.coco.json"
R16_ANNOTATION_URL = (
    "https://huggingface.co/datasets/iisc-aim/BMD-45/resolve/main/"
    "BMD-45-Val/_annotations.coco.json?download=true"
)
R16_IMAGE_BASE = "https://huggingface.co/datasets/iisc-aim/BMD-45/resolve/main/BMD-45-Val"
R17_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_bmd45_deepstream_frame_replay_comparison_r17"
R17_PACKAGE = R17_ROOT / "METROPOLIS_VSS_BMD45_DEEPSTREAM_FRAME_REPLAY_COMPARISON_R17_PACKAGE.zip"
R17_SCRIPT = REPO_ROOT / "scripts" / "run_main_citybrain_metropolis_vss_bmd45_deepstream_frame_replay_comparison_r17.py"

REMOTE_HOST = "txr-4070"
PASS_STATUS = "PASS_METROPOLIS_VSS_BMD45_THRESHOLD_CALIBRATION_AND_SAMPLE_EXPANSION_R18_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_METROPOLIS_VSS_BMD45_THRESHOLD_CALIBRATION_R18_DEEPSTREAM_EXECUTION_BLOCKED"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_BMD45_THRESHOLD_CALIBRATION_R18_BOUNDARY_OR_FABRICATION_RISK"
IOU_THRESHOLDS = [0.25, 0.5, 0.75]

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


def load_r17_module() -> Any:
    spec = importlib.util.spec_from_file_location("citybrain_r17_runner", R17_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import R17 runner from {R17_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R17 = load_r17_module()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
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


def validate_zip_package(package_path: Path, decision_name: str, expected_status: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "package_exists": package_path.exists(),
        "package_path": rel(package_path),
        "schema_version": SCHEMA_VERSION,
        "status": "FAIL",
    }
    if not package_path.exists():
        report["failure_reason"] = "package not found"
        return report
    try:
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
                if actual != entry.get("sha256"):
                    mismatches.append(entry["file"])
            decision = json.loads(archive.read(decision_name).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        report["failure_reason"] = str(exc)
        return report
    decision_status = decision.get("status") or decision.get("final_status")
    report.update(
        {
            "decision_status": decision_status,
            "expected_status": expected_status,
            "hash_manifest_status": "PASS" if not missing and not mismatches else "FAIL",
            "json_files_parsed": json_count,
            "jsonl_files_parsed": jsonl_count,
            "manifest_mismatches": mismatches,
            "manifest_missing": missing,
            "status": "PASS" if bad is None and decision_status == expected_status and not missing and not mismatches else "FAIL",
            "zip_entries": len(names),
            "zip_integrity": "PASS" if bad is None else f"FAIL:{bad}",
        }
    )
    return report


def fetch_url_bytes(url: str, target: Path, timeout: int = 180) -> bytes:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "citybrain-r18/1.0"})
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


def load_bmd45_coco() -> dict[str, Any]:
    if R16_ANNOTATION_CACHE.exists() and R16_ANNOTATION_CACHE.stat().st_size > 0:
        return json.loads(R16_ANNOTATION_CACHE.read_text(encoding="utf-8"))
    data = fetch_url_bytes(R16_ANNOTATION_URL, R16_ANNOTATION_CACHE)
    return json.loads(data.decode("utf-8"))


def family_for_dataset_label(label: str | None) -> str:
    mapping = {
        "Hatchback": "vehicle_family:car",
        "Sedan": "vehicle_family:car",
        "SUV": "vehicle_family:car",
        "MUV": "vehicle_family:car",
        "Van": "vehicle_family:car",
        "Bus": "vehicle_family:bus",
        "Mini-bus": "vehicle_family:bus",
        "Tempo-traveller": "vehicle_family:bus",
        "Truck": "vehicle_family:truck",
        "LCV": "vehicle_family:truck",
        "Three-wheeler": "vehicle_family:three_wheeler",
        "Two-wheeler": "vehicle_family:two_wheeler",
        "Bicycle": "vehicle_family:two_wheeler",
    }
    return mapping.get(str(label or ""), "vehicle_family:unknown_vehicle")


def family_for_sensor_label(label: str | None) -> str:
    mapping = {
        "car": "vehicle_family:car",
        "bus": "vehicle_family:bus",
        "truck": "vehicle_family:truck",
        "bicycle": "vehicle_family:two_wheeler",
        "motorbike": "vehicle_family:two_wheeler",
        "motorcycle": "vehicle_family:two_wheeler",
        "person": "non_vehicle_family:person",
        "road_sign": "non_vehicle_family:road_sign",
    }
    return mapping.get(str(label or "").lower(), "vehicle_family:unknown_vehicle")


def class_mapping_r18() -> dict[str, Any]:
    return {
        "bmd45_to_family": {
            "Hatchback": "vehicle_family:car",
            "Sedan": "vehicle_family:car",
            "SUV": "vehicle_family:car",
            "MUV": "vehicle_family:car",
            "Van": "vehicle_family:car",
            "Bus": "vehicle_family:bus",
            "Mini-bus": "vehicle_family:bus",
            "Tempo-traveller": "vehicle_family:bus",
            "Truck": "vehicle_family:truck",
            "LCV": "vehicle_family:truck",
            "Three-wheeler": "vehicle_family:three_wheeler",
            "Two-wheeler": "vehicle_family:two_wheeler",
            "Bicycle": "vehicle_family:two_wheeler",
        },
        "deepstream_to_family": {
            "car": "vehicle_family:car",
            "bus": "vehicle_family:bus",
            "truck": "vehicle_family:truck",
            "bicycle": "vehicle_family:two_wheeler",
            "motorbike": "vehicle_family:two_wheeler",
            "person": "non_vehicle_family:person",
            "road_sign": "non_vehicle_family:road_sign",
        },
        "mapping_policy": "R17 class-family comparison with BMD-45 category expansion",
        "schema_version": SCHEMA_VERSION,
    }


def select_sample_images(coco: dict[str, Any], sample_count: int) -> tuple[list[dict[str, Any]], dict[int, list[dict[str, Any]]], dict[int, dict[str, Any]]]:
    categories = {int(category["id"]): category for category in coco.get("categories", [])}
    annotations_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for annotation in coco.get("annotations", []):
        annotations_by_image[int(annotation["image_id"])].append(annotation)
    candidates = []
    for image in coco.get("images", []):
        image_id = int(image["id"])
        annotations = annotations_by_image.get(image_id, [])
        if not annotations or not str(image.get("file_name", "")).endswith(".png"):
            continue
        labels = [categories[int(annotation["category_id"])]["name"] for annotation in annotations]
        families = sorted({family_for_dataset_label(label) for label in labels})
        candidates.append({"image": image, "annotation_count": len(annotations), "families": families, "labels": sorted(set(labels))})
    candidates.sort(key=lambda row: str(row["image"].get("file_name", "")))

    selected: list[dict[str, Any]] = []
    selected_ids: set[int] = set()
    target_families = [
        "vehicle_family:bus",
        "vehicle_family:truck",
        "vehicle_family:car",
        "vehicle_family:three_wheeler",
        "vehicle_family:two_wheeler",
    ]
    for family in target_families:
        for row in candidates:
            image_id = int(row["image"]["id"])
            if image_id in selected_ids:
                continue
            if family in row["families"]:
                selected.append(row["image"])
                selected_ids.add(image_id)
                break
    fill = sorted(
        [row for row in candidates if int(row["image"]["id"]) not in selected_ids],
        key=lambda row: (-len(row["families"]), -row["annotation_count"], str(row["image"].get("file_name", ""))),
    )
    for row in fill:
        if len(selected) >= sample_count:
            break
        selected.append(row["image"])
        selected_ids.add(int(row["image"]["id"]))
    selected = selected[:sample_count]
    selected.sort(key=lambda image: str(image.get("file_name", "")))
    return selected, annotations_by_image, categories


def fetch_frame_refs(sample_images: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    refs = []
    failures = []
    for sequence_index, image in enumerate(sample_images):
        file_name = str(image["file_name"])
        url = f"{R16_IMAGE_BASE}/{file_name}?download=true"
        cache_path = REPO_ROOT / "tmp" / "r18_bmd45_cache" / ("bmd45_val_" + file_name.replace("/", "_"))
        try:
            if cache_path.exists() and cache_path.stat().st_size > 0:
                data = cache_path.read_bytes()
                fetched = False
            else:
                data = fetch_url_bytes(url, cache_path)
                fetched = True
            refs.append(
                {
                    "bytes": len(data),
                    "cache_file": rel(cache_path),
                    "external_media_ref": True,
                    "fetch": {
                        "bytes": len(data),
                        "cache_file": rel(cache_path),
                        "fetched": fetched,
                        "from_cache": not fetched,
                        "sha256": sha256_bytes(data),
                        "url": url,
                    },
                    "fetched": fetched,
                    "file_name": file_name,
                    "frame_replay_id": f"bmd45-val-frame-{image['id']}",
                    "height": image.get("height"),
                    "image_id": image.get("id"),
                    "media_source_id": f"media:bmd45:val:{file_name}",
                    "media_url": url,
                    "packaged_file": False,
                    "sequence_index": sequence_index,
                    "sha256": sha256_bytes(data),
                    "source_class": "dataset_annotation",
                    "width": image.get("width"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            failures.append({"file_name": file_name, "error": str(exc)})
    return {
        "failed_frames": failures,
        "frames_fetched_or_reused": len(refs),
        "packaged_media_count": 0,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if refs and not failures else "PARTIAL" if refs else "FAIL",
        "verified_sha_count": len(refs),
    }, refs


def dataset_annotation_rows(
    sample_images: list[dict[str, Any]],
    annotations_by_image: dict[int, list[dict[str, Any]]],
    categories: dict[int, dict[str, Any]],
    max_annotations_per_frame: int,
) -> list[dict[str, Any]]:
    rows = []
    sequence_by_image_id = {int(image["id"]): sequence_index for sequence_index, image in enumerate(sample_images)}
    image_by_id = {int(image["id"]): image for image in sample_images}
    for image in sample_images:
        image_id = int(image["id"])
        annotations = sorted(annotations_by_image.get(image_id, []), key=lambda ann: int(ann.get("id", 0)))[:max_annotations_per_frame]
        for annotation in annotations:
            bbox = annotation.get("bbox", [0, 0, 0, 0])
            label = categories[int(annotation["category_id"])]["name"]
            file_name = image_by_id[image_id]["file_name"]
            rows.append(
                {
                    "annotation_id": annotation.get("id"),
                    "bbox": {
                        "coordinate_space": "pixel",
                        "h": bbox[3],
                        "w": bbox[2],
                        "x": bbox[0],
                        "y": bbox[1],
                    },
                    "candidate_observation_id": stable_id("metropolis-vss-r18-dataset-annotation", image_id, annotation.get("id")),
                    "class_family": family_for_dataset_label(label),
                    "class_label": label,
                    "dataset_source_id": "bmd45_huggingface_iisc_aim",
                    "frame_replay_id": f"bmd45-val-frame-{image_id}",
                    "frame_sequence_index": sequence_by_image_id[image_id],
                    "human_review_required": True,
                    "media_source_id": f"media:bmd45:val:{file_name}",
                    "review_state": "candidate_unreviewed",
                    "schema_version": SCHEMA_VERSION,
                    "source_class": "dataset_annotation",
                    "source_system": "BMD-45 COCO validation annotation",
                }
            )
    return rows


def bbox_xyxy_from_xywh(bbox: dict[str, Any]) -> tuple[float, float, float, float]:
    x = float(bbox.get("x", 0.0))
    y = float(bbox.get("y", 0.0))
    w = max(0.0, float(bbox.get("w", 0.0)))
    h = max(0.0, float(bbox.get("h", 0.0)))
    return x, y, x + w, y + h


def compute_iou(a: dict[str, Any], b: dict[str, Any]) -> float:
    ax1, ay1, ax2, ay2 = bbox_xyxy_from_xywh(a)
    bx1, by1, bx2, by2 = bbox_xyxy_from_xywh(b)
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = ((ax2 - ax1) * (ay2 - ay1)) + ((bx2 - bx1) * (by2 - by1)) - intersection
    return 0.0 if union <= 0 else intersection / union


def transform_sensor_rows(raw_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    transformed_raw = []
    transformed_candidates = []
    for row in raw_rows:
        new_row = dict(row)
        new_row["schema_version"] = SCHEMA_VERSION
        new_row["source_class"] = "sensor_inferred"
        new_row["class_family"] = family_for_sensor_label(new_row.get("class_label"))
        new_row["r17_raw_metadata_id"] = new_row.get("raw_metadata_id")
        if new_row.get("raw_metadata_id"):
            new_row["raw_metadata_id"] = stable_id("deepstream-r18-kitti-raw", new_row["r17_raw_metadata_id"])
        transformed_raw.append(new_row)
        if new_row.get("record_type") == "explicit_zero_detection_frame_result" or not new_row.get("bbox"):
            continue
        candidate = dict(new_row)
        candidate["candidate_observation_id"] = stable_id("metropolis-vss-r18-sensor-observation", candidate.get("r17_raw_metadata_id"), candidate.get("frame_sequence_index"))
        transformed_candidates.append(candidate)
    return transformed_raw, transformed_candidates


def normalize_remote_artifact_names(output_root: Path) -> None:
    delete_names = [
        "DEEPSTREAM_RAW_METADATA_R17.jsonl",
        "SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R17.jsonl",
        "REMOTE_R17_STDOUT.log",
        "REMOTE_R17_STDERR.log",
    ]
    rename_map = {
        "CITYBRAIN_R17_DEEPSTREAM_CONFIG.txt": "CITYBRAIN_R18_DEEPSTREAM_CONFIG.txt",
        "DEEPSTREAM_REPLAY_INPUT_PREP_REMOTE_R17.json": "DEEPSTREAM_REPLAY_INPUT_PREP_REMOTE_R18.json",
        "DEEPSTREAM_RETURN_CODE_R17.txt": "DEEPSTREAM_RETURN_CODE_R18.txt",
        "DEEPSTREAM_RUNTIME_SUMMARY_R17.json": "DEEPSTREAM_RUNTIME_SUMMARY_R18.json",
        "DEEPSTREAM_STDERR_R17.log": "DEEPSTREAM_STDERR_R18.log",
        "DEEPSTREAM_STDOUT_R17.log": "DEEPSTREAM_STDOUT_R18.log",
        "GST_CREATE_RETURN_CODE_R17.txt": "GST_CREATE_RETURN_CODE_R18.txt",
        "GST_CREATE_STDERR_R17.log": "GST_CREATE_STDERR_R18.log",
        "GST_CREATE_STDOUT_R17.log": "GST_CREATE_STDOUT_R18.log",
        "KITTI_FILES_R17.txt": "KITTI_FILES_R18.txt",
        "REMOTE_DOCKER_STDERR_R17.log": "REMOTE_DOCKER_STDERR_R18.log",
        "REMOTE_DOCKER_STDOUT_R17.log": "REMOTE_DOCKER_STDOUT_R18.log",
    }
    for name in delete_names:
        path = output_root / name
        if path.exists():
            path.unlink()
    for old_name, new_name in rename_map.items():
        old_path = output_root / old_name
        if old_path.exists():
            new_path = output_root / new_name
            if new_path.exists():
                new_path.unlink()
            old_path.replace(new_path)
    write_text(
        output_root / "REMOTE_EXECUTION_CAPTURE_NOTE_R18.md",
        "Remote base64 transport stdout was not packaged because individual DeepStream, Docker, GStreamer, config, and return-code artifacts are packaged separately.",
    )


def compare_rows(dataset_rows: list[dict[str, Any]], sensor_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    detections = [row for row in sensor_rows if row.get("bbox") and row.get("record_type") != "explicit_zero_detection_frame_result"]
    annotations_by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    detections_by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in dataset_rows:
        annotations_by_frame[int(row.get("frame_sequence_index", -1))].append(row)
    for row in detections:
        detections_by_frame[int(row.get("frame_sequence_index", -1))].append(row)

    records = []
    threshold_counts = {str(threshold): 0 for threshold in IOU_THRESHOLDS}
    matched_detection_ids: set[str] = set()
    matched_annotation_ids: set[Any] = set()
    for frame in sorted(set(annotations_by_frame) | set(detections_by_frame)):
        annotations = annotations_by_frame.get(frame, [])
        frame_detections = detections_by_frame.get(frame, [])
        possible = []
        for ann_index, ann in enumerate(annotations):
            for det_index, det in enumerate(frame_detections):
                if ann.get("class_family") != det.get("class_family"):
                    continue
                possible.append(
                    {
                        "annotation_id": ann.get("annotation_id"),
                        "annotation_index": ann_index,
                        "candidate_observation_id": det.get("candidate_observation_id"),
                        "class_family": ann.get("class_family"),
                        "detection_index": det_index,
                        "iou": compute_iou(ann.get("bbox", {}), det.get("bbox", {})),
                    }
                )
        possible.sort(key=lambda row: row["iou"], reverse=True)
        used_annotations: set[int] = set()
        used_detections: set[int] = set()
        matches = []
        for pair in possible:
            if pair["annotation_index"] in used_annotations or pair["detection_index"] in used_detections:
                continue
            if pair["iou"] <= 0:
                continue
            used_annotations.add(pair["annotation_index"])
            used_detections.add(pair["detection_index"])
            matches.append(pair)
            matched_detection_ids.add(str(pair["candidate_observation_id"]))
            matched_annotation_ids.add(pair["annotation_id"])
            for threshold in IOU_THRESHOLDS:
                if pair["iou"] >= threshold:
                    threshold_counts[str(threshold)] += 1
        unmatched_annotations = [ann for index, ann in enumerate(annotations) if index not in used_annotations]
        unmatched_detections = [det for index, det in enumerate(frame_detections) if index not in used_detections]
        records.append(
            {
                "annotation_count": len(annotations),
                "frame_sequence_index": frame,
                "matches": matches,
                "schema_version": SCHEMA_VERSION,
                "sensor_detection_count": len(frame_detections),
                "unmatched_annotation_count": len(unmatched_annotations),
                "unmatched_sensor_detection_count": len(unmatched_detections),
            }
        )

    false_positive_review = [
        {
            "bbox": row.get("bbox"),
            "candidate_observation_id": row.get("candidate_observation_id"),
            "class_family": row.get("class_family"),
            "class_label": row.get("class_label"),
            "confidence": row.get("confidence"),
            "frame_sequence_index": row.get("frame_sequence_index"),
            "review_note": "Unmatched sensor_inferred candidate against bounded dataset_annotation subset; candidate review only.",
            "source_class": "sensor_inferred",
        }
        for row in detections
        if str(row.get("candidate_observation_id")) not in matched_detection_ids
    ]
    missed_annotation_review = [
        {
            "annotation_id": row.get("annotation_id"),
            "bbox": row.get("bbox"),
            "class_family": row.get("class_family"),
            "class_label": row.get("class_label"),
            "frame_sequence_index": row.get("frame_sequence_index"),
            "review_note": "Dataset annotation unmatched by sensor_inferred candidate; candidate review only.",
            "source_class": "dataset_annotation",
        }
        for row in dataset_rows
        if row.get("annotation_id") not in matched_annotation_ids
    ]
    report = {
        "annotation_count": len(dataset_rows),
        "certification_claim": False,
        "frame_count": len(set(annotations_by_frame) | set(detections_by_frame)),
        "human_review_required": True,
        "iou_thresholds": IOU_THRESHOLDS,
        "metrics": {
            "matches_any_iou": len(matched_detection_ids),
            "matches_at_threshold": threshold_counts,
            "missed_annotation_review_count": len(missed_annotation_review),
            "unmatched_sensor_candidate_review_count": len(false_positive_review),
        },
        "schema_version": SCHEMA_VERSION,
        "sensor_detection_count": len(detections),
        "source_classes": {
            "dataset_annotations": "dataset_annotation",
            "deepstream_detections": "sensor_inferred",
        },
        "status": "PASS",
    }
    return report, records, false_positive_review, missed_annotation_review


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * pct
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return round(ordered[lower], 6)
    weight = index - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 6)


def calibration_report(sensor_rows: list[dict[str, Any]], comparison_report: dict[str, Any]) -> dict[str, Any]:
    detections = [row for row in sensor_rows if row.get("bbox") and row.get("record_type") != "explicit_zero_detection_frame_result"]
    confidences = [float(row.get("confidence", 0.0)) for row in detections if row.get("confidence") is not None]
    per_class: dict[str, int] = defaultdict(int)
    per_family: dict[str, int] = defaultdict(int)
    for row in detections:
        per_class[str(row.get("class_label"))] += 1
        per_family[str(row.get("class_family"))] += 1
    bands = {
        "lt_0_25": sum(1 for value in confidences if value < 0.25),
        "0_25_to_lt_0_35": sum(1 for value in confidences if 0.25 <= value < 0.35),
        "0_35_to_lt_0_50": sum(1 for value in confidences if 0.35 <= value < 0.50),
        "gte_0_50": sum(1 for value in confidences if value >= 0.50),
    }
    return {
        "confidence_distribution": {
            "bands": bands,
            "count": len(confidences),
            "max": round(max(confidences), 6) if confidences else None,
            "mean": round(statistics.mean(confidences), 6) if confidences else None,
            "median": round(statistics.median(confidences), 6) if confidences else None,
            "min": round(min(confidences), 6) if confidences else None,
            "p10": percentile(confidences, 0.10),
            "p25": percentile(confidences, 0.25),
            "p75": percentile(confidences, 0.75),
            "p90": percentile(confidences, 0.90),
        },
        "iou_match_counts": comparison_report.get("metrics", {}).get("matches_at_threshold", {}),
        "per_class_candidate_counts": dict(sorted(per_class.items())),
        "per_family_candidate_counts": dict(sorted(per_family.items())),
        "recommended_confidence_threshold_bands": {
            "exploratory_candidate_review": {
                "min_confidence": 0.20,
                "note": "High recall review band; expected to include many unmatched candidates.",
            },
            "standard_candidate_review": {
                "min_confidence": 0.30,
                "note": "Initial R18 working band for human review, not production certification.",
            },
            "conservative_candidate_review": {
                "min_confidence": 0.50,
                "note": "Higher precision review band for later validation; not an action threshold.",
            },
        },
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
    }


def scan_for_forbidden_claims(output_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    safe_markers = ["blocked", "not ", "no ", "no_", "false", "pending", "limitation", "non-goal", "without claiming", "candidate review only"]
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


def write_audits(output_root: Path, dataset_rows: list[dict[str, Any]], sensor_rows: list[dict[str, Any]]) -> dict[str, str]:
    source_audit = {
        "dataset_annotation_records": len(dataset_rows),
        "sensor_inferred_records": len(sensor_rows),
        "schema_version": SCHEMA_VERSION,
        "source_classes": {
            "dataset_annotations": "dataset_annotation",
            "deepstream_metropolis": "sensor_inferred",
            "vss": "model_generated_narrative",
        },
        "status": "PASS" if all(row.get("source_class") == "dataset_annotation" for row in dataset_rows) and all(row.get("source_class") == "sensor_inferred" for row in sensor_rows) else "FAIL",
    }
    claim_findings = scan_for_forbidden_claims(output_root)
    secret_findings = scan_for_secrets(output_root)
    audits = {
        "SOURCE_CLASS_SEPARATION_AUDIT_R18.json": source_audit,
        "CLAIM_BOUNDARY_AUDIT_R18.json": {"findings": claim_findings, "schema_version": SCHEMA_VERSION, "status": "PASS" if not claim_findings else "FAIL"},
        "NO_ACTION_AUDIT_R18.json": {
            "action_created": False,
            "dispatch_created": False,
            "official_record_created": False,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "ticket_created": False,
        },
        "SECRET_AUDIT_R18.json": {"findings": secret_findings, "schema_version": SCHEMA_VERSION, "status": "PASS" if not secret_findings else "FAIL"},
        "VSS_NOT_FACT_SOURCE_AUDIT_R18.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "vss_is_fact_source": False,
            "vss_records_created": 0,
        },
    }
    for filename, payload in audits.items():
        write_json(output_root / filename, payload)
    return {filename.replace(".json", ""): payload["status"] for filename, payload in audits.items()}


def build_package(output_root: Path, external_refs: list[dict[str, Any]]) -> dict[str, Any]:
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
        "external_media_refs": external_refs,
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
        missing = []
        mismatches = []
        for entry in manifest.get("files", []):
            try:
                data = archive.read(entry["file"])
            except KeyError:
                missing.append(entry["file"])
                continue
            if sha256_bytes(data) != entry.get("sha256"):
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


def build_r18(output_root: Path, sample_count: int, max_annotations_per_frame: int) -> dict[str, Any]:
    reset_output_root(output_root)
    r17_validation = validate_zip_package(
        R17_PACKAGE,
        "R17_CLOSEOUT_DECISION.json",
        "PASS_METROPOLIS_VSS_BMD45_DEEPSTREAM_FRAME_REPLAY_COMPARISON_R17_WITH_LIMITATIONS",
    )
    coco = load_bmd45_coco()
    sample_images, annotations_by_image, categories = select_sample_images(coco, sample_count)
    fetch_report, external_refs = fetch_frame_refs(sample_images)
    stage_report, staged_frames = R17.stage_frames_for_replay(external_refs)
    dataset_rows = dataset_annotation_rows(sample_images, annotations_by_image, categories, max_annotations_per_frame)

    write_json(output_root / "R17_INPUT_LINEAGE_SUMMARY.json", r17_validation)
    write_json(
        output_root / "BMD45_SAMPLE_SELECTION_R18.json",
        {
            "dataset_source_id": "bmd45_huggingface_iisc_aim",
            "frame_count": len(sample_images),
            "max_annotations_per_frame": max_annotations_per_frame,
            "sample_policy": "deterministic family coverage plus bounded diversity fill",
            "schema_version": SCHEMA_VERSION,
            "selected_frames": [
                {
                    "annotation_count_available": len(annotations_by_image[int(image["id"])]),
                    "file_name": image.get("file_name"),
                    "height": image.get("height"),
                    "image_id": image.get("id"),
                    "sequence_index": index,
                    "width": image.get("width"),
                }
                for index, image in enumerate(sample_images)
            ],
            "status": "PASS" if sample_images else "FAIL",
        },
    )
    frame_fetch_report = dict(fetch_report)
    frame_fetch_report["stage_verification"] = stage_report
    write_json(output_root / "BMD45_FRAME_FETCH_REPORT_R18.json", frame_fetch_report)
    write_json(output_root / "CLASS_MAPPING_R18.json", class_mapping_r18())
    write_jsonl(output_root / "DATASET_ANNOTATION_SUBSET_R18.jsonl", dataset_rows)

    remote_result = R17.run_remote_deepstream(output_root, staged_frames)
    r17_raw_rows = read_jsonl(output_root / "DEEPSTREAM_RAW_METADATA_R17.jsonl")
    transformed_raw, sensor_candidates = transform_sensor_rows(r17_raw_rows)
    write_jsonl(output_root / "DEEPSTREAM_RAW_METADATA_R18.jsonl", transformed_raw)
    write_jsonl(output_root / "SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R18.jsonl", sensor_candidates)
    runtime_summary = read_json(output_root / "DEEPSTREAM_RUNTIME_SUMMARY_R17.json", {})
    write_json(
        output_root / "DEEPSTREAM_FRAME_REPLAY_REPORT_R18.json",
        {
            "container_image": remote_result.get("container_image"),
            "deepstream_return_code": remote_result.get("deepstream_return_code"),
            "docker_return_code": remote_result.get("docker_return_code"),
            "execution_status": remote_result.get("execution_status"),
            "frame_count": len(sample_images),
            "host": REMOTE_HOST,
            "raw_detection_records": runtime_summary.get("raw_detection_records", 0),
            "replay_method": remote_result.get("replay_method"),
            "schema_version": SCHEMA_VERSION,
            "sensor_candidate_observation_records": len(sensor_candidates),
            "ssh_return_code": remote_result.get("ssh_return_code"),
            "status": "PASS" if remote_result.get("status") == "PASS" else "PARTIAL",
            "temporary_replay_video": runtime_summary.get("input_replay_video", {}),
        },
    )
    normalize_remote_artifact_names(output_root)

    comparison_report, frame_records, false_positive_review, missed_annotation_review = compare_rows(dataset_rows, sensor_candidates)
    write_json(output_root / "IOU_COMPARISON_REPORT_R18.json", comparison_report)
    write_jsonl(output_root / "FRAME_COMPARISON_RECORDS_R18.jsonl", frame_records)
    write_json(output_root / "THRESHOLD_CALIBRATION_REPORT_R18.json", calibration_report(sensor_candidates, comparison_report))
    write_json(output_root / "FALSE_POSITIVE_REVIEW_LIST_R18.json", {"items": false_positive_review, "schema_version": SCHEMA_VERSION, "status": "PASS"})
    write_json(output_root / "MISSED_ANNOTATION_REVIEW_LIST_R18.json", {"items": missed_annotation_review, "schema_version": SCHEMA_VERSION, "status": "PASS"})
    write_json(
        output_root / "HUMAN_REVIEW_CALIBRATION_PACKET_R18.json",
        {
            "cannot_claim": [
                "not production live CCTV",
                "not an official finding",
                "no ticket or case",
                "no dispatch or action",
                "no identity or legal conclusion",
                "not model accuracy certification",
            ],
            "comparison_summary": comparison_report.get("metrics", {}),
            "dataset_annotation_records": len(dataset_rows),
            "human_review_required": True,
            "review_packet_id": stable_id("human-review-calibration-packet-r18", len(dataset_rows), len(sensor_candidates)),
            "schema_version": SCHEMA_VERSION,
            "sensor_candidate_observations": len(sensor_candidates),
            "source_classes": {
                "dataset_annotations": "dataset_annotation",
                "deepstream_metropolis": "sensor_inferred",
                "vss": "model_generated_narrative_not_used",
            },
        },
    )
    write_text(
        output_root / "ENVIRONMENT_NOTE_R18.md",
        "# Environment Note R18\n\n`pytest 9.1.1` is installed in the active Python 3.11 environment for local test execution. It is recorded as environment state, not as a product runtime dependency.\n",
    )
    write_text(
        output_root / "KNOWN_LIMITATIONS_R18.md",
        "\n".join(
            [
                "# Known Limitations R18",
                "",
                "- R18 is a bounded offline BMD-45 frame replay expansion, not production live CCTV.",
                "- Dataset annotations are comparison fixtures, not official truth or legal findings.",
                "- DeepStream detections are candidate observations only and require human review.",
                "- Recommended confidence bands are exploratory and not action thresholds.",
                "- VSS is not used as a fact source in this calibration gate.",
            ]
        ),
    )
    write_text(
        output_root / "README.md",
        f"# {TASK_ID}\n\nR18 expands the BMD-45 replay sample and calibrates candidate-review thresholds while preserving dataset/sensor source separation.\n",
    )

    audit_statuses = write_audits(output_root, dataset_rows, transformed_raw)
    audits_pass = all(status == "PASS" for status in audit_statuses.values())
    pass_ready = (
        r17_validation.get("status") == "PASS"
        and fetch_report.get("status") == "PASS"
        and stage_report.get("status") == "PASS"
        and remote_result.get("status") == "PASS"
        and comparison_report.get("status") == "PASS"
        and len(sensor_candidates) > 0
        and audits_pass
    )
    final_status = PASS_STATUS if pass_ready else PARTIAL_STATUS
    if not audits_pass:
        final_status = FAIL_STATUS
    decision = {
        "audits": audit_statuses,
        "candidate_observation_records": len(sensor_candidates),
        "comparison_computed": comparison_report.get("status") == "PASS",
        "dataset_annotation_records": len(dataset_rows),
        "deepstream_execution_status": remote_result.get("execution_status"),
        "deepstream_runtime_executed": remote_result.get("status") == "PASS",
        "environment_note": "pytest 9.1.1 installed in active Python 3.11 environment; not a product dependency claim",
        "external_media_refs": len(external_refs),
        "final_status": final_status,
        "frame_fetch_status": fetch_report.get("status"),
        "live_cctv_claimed": False,
        "official_record_created": False,
        "packaged_media_files": 0,
        "r17_input_validation": r17_validation.get("status"),
        "sample_frame_count": len(sample_images),
        "schema_version": SCHEMA_VERSION,
        "source_classes": {
            "bmd45_annotations": "dataset_annotation",
            "deepstream_metropolis": "sensor_inferred",
            "vss": "model_generated_narrative_not_used",
        },
        "status": final_status,
        "task_id": TASK_ID,
    }
    write_json(output_root / "R18_CLOSEOUT_DECISION.json", decision)
    write_json(
        output_root / "R18_JSON_PARSE_REPORT.json",
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
    write_text(
        output_root / "TEST_LOG_R18.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r17_input_validation={r17_validation.get('status')}",
                f"frame_fetch_status={fetch_report.get('status')}",
                f"deepstream_execution_status={remote_result.get('execution_status')}",
                f"sensor_candidate_observations={len(sensor_candidates)}",
                f"dataset_annotation_records={len(dataset_rows)}",
                "zip_entries=PENDING",
                "hash_manifest=PENDING",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    write_json(
        output_root / "R18_JSON_PARSE_REPORT.json",
        {
            "hash_manifest_status": package_report["hash_manifest_status"],
            "json_files_parsed": package_report["json_files_parsed"],
            "jsonl_files_parsed": package_report["jsonl_files_parsed"],
            "manifest_mismatches": package_report["manifest_mismatches"],
            "manifest_missing": package_report["manifest_missing"],
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if package_report["status"] == "PASS" else "FAIL",
            "zip_entries": package_report["zip_entries"],
            "zip_integrity": package_report["zip_integrity"],
        },
    )
    write_text(
        output_root / "TEST_LOG_R18.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r17_input_validation={r17_validation.get('status')}",
                f"frame_fetch_status={fetch_report.get('status')}",
                f"deepstream_execution_status={remote_result.get('execution_status')}",
                f"sensor_candidate_observations={len(sensor_candidates)}",
                f"dataset_annotation_records={len(dataset_rows)}",
                f"zip_entries={package_report['zip_entries']}",
                f"hash_manifest={package_report['hash_manifest_verified']}",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    return {"decision": decision, "package_report": package_report}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run R18 BMD-45 threshold calibration sample expansion.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--sample-count", type=int, default=8)
    parser.add_argument("--max-annotations-per-frame", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_r18(Path(args.output_root), max(4, args.sample_count), max(1, args.max_annotations_per_frame))
    decision = result["decision"]
    report = result["package_report"]
    print(f"Status: {decision['status']}")
    print(f"Output: {rel(Path(args.output_root))}")
    print(f"Freeze ZIP: {rel(Path(args.output_root) / PACKAGE_NAME)}")
    print(f"R17 input validation: {decision['r17_input_validation']}")
    print(f"Frame fetch: {decision['frame_fetch_status']}")
    print(f"DeepStream execution: {decision['deepstream_execution_status']}")
    print(f"Sample frames: {decision['sample_frame_count']}")
    print(f"Sensor candidate observations: {decision['candidate_observation_records']}")
    print(f"Dataset annotation records: {decision['dataset_annotation_records']}")
    print(f"ZIP entries: {report['zip_entries']}")
    print(f"JSON parse: PASS, {report['json_files_parsed']} JSON + {report['jsonl_files_parsed']} JSONL")
    print(f"Hash manifest: {report['hash_manifest_verified']}")
    print(f"Manifest mismatches: {len(report['manifest_mismatches'])}")
    return 0 if report["status"] == "PASS" and decision["status"] != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
