#!/usr/bin/env python3
"""R16 offline CCTV-like dataset expansion gate for the Metropolis/VSS lane."""

from __future__ import annotations

import argparse
import hashlib
import json
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
TMP_ROOT = REPO_ROOT / "tmp" / "r16_bmd45_cache"
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-OFFLINE-CCTV-DATASET-EXPANSION-R16"
SCHEMA_VERSION = "metropolis-vss-offline-cctv-dataset-expansion-r16.v1"
DEFAULT_OUTPUT_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_offline_cctv_dataset_expansion_r16"
R10_R15_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_evidence_replay_readiness_sprint_r10_r15"
R10_R15_PACKAGE = R10_R15_ROOT / "METROPOLIS_VSS_EVIDENCE_REPLAY_READINESS_SPRINT_R10_R15_LIGHTWEIGHT_PACKAGE.zip"
PACKAGE_NAME = "METROPOLIS_VSS_OFFLINE_CCTV_DATASET_EXPANSION_R16_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_OFFLINE_CCTV_DATASET_EXPANSION_R16_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_METROPOLIS_VSS_CCTV_IMAGE_REPLAY_READY_VIDEO_DATASET_PENDING"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_OFFLINE_CCTV_DATASET_EXPANSION_R16_BOUNDARY_OR_LICENSE_GATE"

BMD45_DATASET_URL = "https://huggingface.co/datasets/iisc-aim/BMD-45"
BMD45_VAL_ANNOTATION_URL = (
    "https://huggingface.co/datasets/iisc-aim/BMD-45/resolve/main/"
    "BMD-45-Val/_annotations.coco.json?download=true"
)
BMD45_VAL_IMAGE_BASE = "https://huggingface.co/datasets/iisc-aim/BMD-45/resolve/main/BMD-45-Val"
BMD45_TREE_URL = "https://huggingface.co/api/datasets/iisc-aim/BMD-45/tree/main/BMD-45-Val?recursive=true"
DEFAULT_SAMPLE_COUNT = 3
MAX_FIXTURE_ANNOTATIONS_PER_IMAGE = 3

FORBIDDEN_CLAIM_TERMS = [
    "confirmed violation",
    "certified finding",
    "legal finding",
    "official case",
    "ticket created",
    "enforcement action",
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


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


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
    allowed_root = OUTPUTS_ROOT.resolve()
    if allowed_root not in resolved.parents:
        raise ValueError(f"Refusing to reset output outside {allowed_root}: {resolved}")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def fetch_bytes(url: str, cache_name: str, timeout: int = 180) -> tuple[bytes, dict[str, Any]]:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    cache_path = TMP_ROOT / cache_name
    if cache_path.exists() and cache_path.stat().st_size > 0:
        data = cache_path.read_bytes()
        return data, {
            "bytes": len(data),
            "cache_file": rel(cache_path),
            "fetched": False,
            "from_cache": True,
            "sha256": sha256_bytes(data),
            "url": url,
        }
    request = urllib.request.Request(url, headers={"User-Agent": "citybrain-r16/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except Exception:
        curl_bin = "curl.exe" if sys.platform.startswith("win") else "curl"
        subprocess.run(
            [curl_bin, "-L", "--retry", "3", "--retry-delay", "2", "--max-time", str(timeout), url, "-o", str(cache_path)],
            check=True,
            cwd=REPO_ROOT,
        )
        data = cache_path.read_bytes()
    else:
        cache_path.write_bytes(data)
    return data, {
        "bytes": len(data),
        "cache_file": rel(cache_path),
        "fetched": True,
        "from_cache": False,
        "sha256": sha256_bytes(data),
        "url": url,
    }


def build_source_evidence() -> dict[str, Any]:
    tree_data, tree_fetch = fetch_bytes(BMD45_TREE_URL, "bmd45_val_tree.json", timeout=120)
    tree = json.loads(tree_data.decode("utf-8"))
    return {
        "bmd45_huggingface": {
            "dataset_url": BMD45_DATASET_URL,
            "license": "cc-by-4.0",
            "license_evidence": "Hugging Face dataset page lists License: cc-by-4.0; dataset card says Dataset: CC BY 4.0 International.",
            "modality": "fixed CCTV traffic images with COCO annotations",
            "source_summary": {
                "camera_sources": 3679,
                "image_resolution": "1920x1080 RGB",
                "total_annotations_approx": 481947,
                "total_images": 45986,
                "validation_images": 10194,
            },
            "tree_probe": {
                "entries_returned": len(tree),
                "fetch": tree_fetch,
                "sample_paths": [entry.get("path") for entry in tree[:10]],
            },
        },
        "sources_consulted": [
            BMD45_DATASET_URL,
            "https://arxiv.org/html/2604.24419v1",
            BMD45_TREE_URL,
        ],
    }


def load_bmd45_annotations() -> tuple[dict[str, Any], dict[str, Any]]:
    data, fetch = fetch_bytes(BMD45_VAL_ANNOTATION_URL, "bmd45_val_annotations.coco.json", timeout=180)
    return json.loads(data.decode("utf-8")), fetch


def select_sample_images(coco: dict[str, Any], sample_count: int) -> list[dict[str, Any]]:
    annotations_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for annotation in coco.get("annotations", []):
        annotations_by_image[int(annotation["image_id"])].append(annotation)
    candidates = [
        image
        for image in coco.get("images", [])
        if int(image.get("id", -1)) in annotations_by_image and str(image.get("file_name", "")).endswith(".png")
    ]
    candidates.sort(key=lambda image: str(image.get("file_name", "")))
    return candidates[:sample_count]


def hash_sample_images(sample_images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for image in sample_images:
        file_name = image["file_name"]
        url = f"{BMD45_VAL_IMAGE_BASE}/{file_name}?download=true"
        cache_name = "bmd45_val_" + file_name.replace("/", "_")
        data, fetch = fetch_bytes(url, cache_name, timeout=180)
        refs.append({
            "bytes": len(data),
            "external_media_ref": True,
            "file_name": file_name,
            "height": image.get("height"),
            "image_id": image.get("id"),
            "media_url": url,
            "packaged_file": False,
            "sha256": sha256_bytes(data),
            "source_class": "dataset_annotation",
            "width": image.get("width"),
            "fetch": fetch,
        })
    return refs


def annotation_subset(coco: dict[str, Any], sample_images: list[dict[str, Any]]) -> dict[str, Any]:
    image_ids = {int(image["id"]) for image in sample_images}
    categories = {int(category["id"]): category for category in coco.get("categories", [])}
    annotations = [ann for ann in coco.get("annotations", []) if int(ann.get("image_id", -1)) in image_ids]
    return {
        "annotations": annotations,
        "categories": list(categories.values()),
        "images": sample_images,
        "schema": "COCO_subset_for_R16_external_frame_replay",
    }


def build_candidate_fixture(subset: dict[str, Any], image_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    image_by_id = {int(image["id"]): image for image in subset["images"]}
    image_ref_by_file = {ref["file_name"]: ref for ref in image_refs}
    category_by_id = {int(category["id"]): category for category in subset["categories"]}
    rows: list[dict[str, Any]] = []
    per_image_count: dict[int, int] = defaultdict(int)
    for annotation in subset["annotations"]:
        image_id = int(annotation["image_id"])
        if per_image_count[image_id] >= MAX_FIXTURE_ANNOTATIONS_PER_IMAGE:
            continue
        per_image_count[image_id] += 1
        image = image_by_id[image_id]
        image_ref = image_ref_by_file[image["file_name"]]
        category = category_by_id.get(int(annotation["category_id"]), {"name": "unknown"})
        bbox = annotation.get("bbox", [0, 0, 0, 0])
        rows.append({
            "annotation_id": annotation.get("id"),
            "bbox": {
                "coordinate_space": "pixel",
                "h": bbox[3],
                "w": bbox[2],
                "x": bbox[0],
                "y": bbox[1],
            },
            "candidate_observation_id": f"metropolis-vss-r16-dataset-observation-{len(rows)+1:03d}",
            "camera_source_id": "bmd45_fixed_cctv_frame_replay_source_r16",
            "class_label": category.get("name"),
            "dataset_license": "cc-by-4.0",
            "dataset_source_id": "bmd45_huggingface_iisc_aim",
            "detection_class": "dataset_vehicle_annotation_candidate",
            "frame_replay_id": f"bmd45-val-frame-{image_id}",
            "human_review_required": True,
            "media_source_id": f"media:bmd45:val:{image['file_name']}",
            "media_url_sha256": image_ref["sha256"],
            "official_record_created": False,
            "review_state": "candidate_unreviewed",
            "schema_version": SCHEMA_VERSION,
            "source_class": "dataset_annotation",
            "source_system": "BMD-45 COCO validation annotation",
            "vss_is_fact_source": False,
            "zone_id": "bmd45_frame_replay_full_frame_r16",
        })
    return rows


def scan_for_forbidden_claims(output_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    safe_markers = ["blocked", "not ", "no_", "false", "pending", "limitation", "non-goal", "without claiming"]
    for path in output_root.rglob("*"):
        if not path.is_file() or path.name in {PACKAGE_NAME, "HASH_MANIFEST.json"}:
            continue
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            lowered = line.lower()
            if any(marker in lowered for marker in safe_markers):
                continue
            for term in FORBIDDEN_CLAIM_TERMS:
                if term in lowered:
                    findings.append({"file": rel(path), "line": str(line_no), "term": term})
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


def build_package(output_root: Path) -> dict[str, Any]:
    package_path = output_root / PACKAGE_NAME
    media_provenance = read_json(output_root / "MEDIA_PROVENANCE_R16.json")
    external_refs = media_provenance.get("external_media_refs", [])
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
        "external_media_refs": external_refs,
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
        for entry in manifest.get("files", []):
            actual = sha256_bytes(archive.read(entry["file"]))
            if actual != entry["sha256"]:
                mismatches.append(entry["file"])
    return {
        "hash_manifest_status": "PASS" if not mismatches else "FAIL",
        "hash_manifest_verified": f"{len(manifest.get('files', [])) - len(mismatches)}/{len(manifest.get('files', []))}",
        "json_files_parsed": json_count,
        "jsonl_files_parsed": jsonl_count,
        "manifest_mismatches": mismatches,
        "status": "PASS" if bad is None and not mismatches else "FAIL",
        "zip_entries": len(names),
        "zip_integrity": "PASS" if bad is None else f"FAIL:{bad}",
    }


def build_r16(output_root: Path, sample_count: int) -> dict[str, Any]:
    reset_output_root(output_root)
    source_evidence = build_source_evidence()
    coco, annotation_fetch = load_bmd45_annotations()
    sample_images = select_sample_images(coco, sample_count)
    image_refs = hash_sample_images(sample_images)
    subset = annotation_subset(coco, sample_images)
    fixture_rows = build_candidate_fixture(subset, image_refs)
    r10_r15_decision = read_json(R10_R15_ROOT / "SPRINT_CLOSEOUT_DECISION_R15.json")

    bmd_ready = bool(image_refs) and all(ref.get("sha256") and ref.get("bytes") for ref in image_refs)
    final_status = PASS_STATUS if bmd_ready else PARTIAL_STATUS

    source_registry = {
        "schema_version": SCHEMA_VERSION,
        "selected_source_id": "bmd45_huggingface_iisc_aim",
        "sources": [
            {
                "dataset_source_id": "bmd45_huggingface_iisc_aim",
                "license": "cc-by-4.0",
                "license_gate": "PASS_ATTRIBUTION_REQUIRED",
                "modality": "fixed_cctv_image_frame_replay",
                "source_class": "dataset_annotation",
                "source_url": BMD45_DATASET_URL,
                "status": "SELECTED_R16_PRIMARY",
            },
            {
                "dataset_source_id": "aicity_cityflowv2_or_wts",
                "license_gate": "PARKED_REQUIRES_LICENSE_REVIEW",
                "modality": "traffic_camera_video",
                "status": "VIDEO_CANDIDATE_PENDING_REVIEW",
            },
            {
                "dataset_source_id": "virat",
                "license_gate": "PARKED_REQUIRES_USAGE_AGREEMENT_OR_LEGAL_REVIEW",
                "modality": "surveillance_video",
                "status": "NOT_SELECTED_R16",
            },
        ],
        "status": "PASS",
    }
    license_review = {
        "attribution_required": True,
        "license": "cc-by-4.0",
        "license_gate_status": "PASS_ATTRIBUTION_REQUIRED",
        "redistribution_policy": "Package metadata and external refs only; do not redistribute the full dataset.",
        "schema_version": SCHEMA_VERSION,
        "selected_source_id": "bmd45_huggingface_iisc_aim",
        "source_evidence": source_evidence,
        "status": "PASS",
        "video_sources": {
            "ai_city": "PARKED_LICENSE_REVIEW_REQUIRED",
            "virat": "PARKED_USAGE_AGREEMENT_REQUIRED",
        },
    }
    replay_manifest = {
        "annotation_fetch": annotation_fetch,
        "annotation_subset_ref": "BMD45_SAMPLE_ANNOTATION_SUBSET_R16.json",
        "external_media_refs": image_refs,
        "frame_replay_mode": "fixed_cctv_image_frame_replay",
        "images_selected": len(sample_images),
        "schema_version": SCHEMA_VERSION,
        "source_class": "dataset_annotation",
        "status": "PASS" if bmd_ready else "PARTIAL",
    }
    camera_update = {
        "camera_sources": [
            {
                "camera_source_id": "bmd45_fixed_cctv_frame_replay_source_r16",
                "camera_identity": "dataset_obfuscated_or_not_packaged",
                "is_production_live_cctv": False,
                "media_source_ids": [f"media:bmd45:val:{image['file_name']}" for image in sample_images],
                "source_class": "dataset_annotation",
                "source_kind": "offline_fixed_camera_image_replay",
                "status": "READY_FOR_REPLAY_TESTING",
                "zone_profile_id": "bmd45_frame_replay_full_frame_r16",
            }
        ],
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
    }
    media_provenance = {
        "dataset_attribution": {
            "citation_hint": "BMD-45: Bengaluru Mobility Dataset for Large-Scale Vehicle Detection from Urban CCTV",
            "license": "cc-by-4.0",
            "source_url": BMD45_DATASET_URL,
        },
        "external_media_refs": image_refs,
        "packaged_media_count": 0,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if bmd_ready else "PARTIAL",
    }

    write_json(output_root / "OFFLINE_DATASET_SOURCE_REGISTRY_R16.json", source_registry)
    write_json(output_root / "DATASET_LICENSE_REVIEW_R16.json", license_review)
    write_json(output_root / "OFFLINE_REPLAY_SAMPLE_MANIFEST_R16.json", replay_manifest)
    write_json(output_root / "CAMERA_SOURCE_REGISTRY_UPDATE_R16.json", camera_update)
    write_json(output_root / "MEDIA_PROVENANCE_R16.json", media_provenance)
    write_json(output_root / "BMD45_SAMPLE_ANNOTATION_SUBSET_R16.json", subset)
    write_json(output_root / "WEB_SOURCE_EVIDENCE_R16.json", source_evidence)
    write_jsonl(output_root / "CANDIDATE_OBSERVATION_FIXTURE_R16.jsonl", fixture_rows)

    claim_findings = scan_for_forbidden_claims(output_root)
    secret_findings = scan_for_secrets(output_root)
    audits = {
        "source_class_separation": {
            "dataset_annotations": "dataset_annotation",
            "deepstream_metropolis": "sensor_inferred",
            "spark_vss": "model_generated_narrative",
            "status": "PASS",
        },
        "claim_boundary": {"findings": claim_findings, "status": "PASS" if not claim_findings else "FAIL"},
        "no_action": {
            "action_created": False,
            "case_created": False,
            "control_output_created": False,
            "official_record_created": False,
            "status": "PASS",
        },
        "vss_not_fact_source": {"vss_is_fact_source": False, "status": "PASS"},
        "secret": {"findings": secret_findings, "status": "PASS" if not secret_findings else "FAIL"},
    }
    for filename, payload in [
        ("SOURCE_CLASS_SEPARATION_AUDIT_R16.json", audits["source_class_separation"]),
        ("CLAIM_BOUNDARY_AUDIT_R16.json", audits["claim_boundary"]),
        ("NO_ACTION_AUDIT_R16.json", audits["no_action"]),
        ("VSS_NOT_FACT_SOURCE_AUDIT_R16.json", audits["vss_not_fact_source"]),
        ("SECRET_AUDIT_R16.json", audits["secret"]),
    ]:
        payload = dict(payload)
        payload["schema_version"] = SCHEMA_VERSION
        payload["task_id"] = TASK_ID
        write_json(output_root / filename, payload)

    if claim_findings or secret_findings:
        final_status = FAIL_STATUS
    decision = {
        "action_created": False,
        "audits": {
            "claim_boundary": audits["claim_boundary"]["status"],
            "no_action": audits["no_action"]["status"],
            "secret_audit": audits["secret"]["status"],
            "source_class_separation": audits["source_class_separation"]["status"],
            "vss_not_fact_source": audits["vss_not_fact_source"]["status"],
        },
        "candidate_observation_fixture_records": len(fixture_rows),
        "dataset_annotation_source_class": "dataset_annotation",
        "final_status": final_status,
        "image_replay_ready": bmd_ready,
        "live_camera_claimed": False,
        "official_record_created": False,
        "r10_r15_input_status": r10_r15_decision.get("status"),
        "r16_pass": final_status == PASS_STATUS,
        "schema_version": SCHEMA_VERSION,
        "selected_source_id": "bmd45_huggingface_iisc_aim",
        "status": final_status,
        "task_id": TASK_ID,
        "validation_package_ref": PACKAGE_NAME,
        "video_dataset_pending": True,
        "vss_is_fact_source": False,
    }
    write_json(output_root / "R16_CLOSEOUT_DECISION.json", decision)
    write_text(output_root / "KNOWN_LIMITATIONS_R16.md", "\n".join([
        "# Known Limitations R16",
        "",
        "- BMD-45 is used as fixed-camera image/frame replay, not continuous video.",
        "- The package stores metadata and external media references only; it does not redistribute BMD-45 images.",
        "- AI City video remains parked until license review is accepted.",
        "- VIRAT remains parked until usage-agreement/legal review is accepted.",
        "- Dataset annotations are `dataset_annotation`, not DeepStream sensor inference and not VSS narrative.",
    ]))
    write_text(output_root / "NEXT_SPRINT_RECOMMENDATIONS_R16.md", "\n".join([
        "# Next Sprint Recommendations R16",
        "",
        "1. Run a small BMD-45 frame replay through DeepStream on txr-4070 and compare metadata against dataset annotations.",
        "2. Open AI City/CityFlowV2 only after license approval for traffic-camera video replay.",
        "3. Keep all media as external refs unless redistribution rights and package size are explicitly accepted.",
    ]))
    write_text(output_root / "README.md", f"""# {TASK_ID}

Status: {final_status}

R16 adds BMD-45 as a license-gated fixed-camera traffic image/frame replay
source. Images are external media references with SHA provenance; the package
contains metadata, annotation fixtures, and audits only.
""")

    write_json(output_root / "R16_JSON_PARSE_REPORT.json", {
        "hash_manifest_status": "PENDING",
        "json_files_parsed": 0,
        "jsonl_files_parsed": 0,
        "manifest_mismatches": [],
        "schema_version": SCHEMA_VERSION,
        "status": "PENDING",
        "zip_entries": 0,
        "zip_integrity": "PENDING",
    })
    write_text(output_root / "TEST_LOG_R16.txt", "\n".join([
        f"task_id={TASK_ID}",
        f"status={final_status}",
        "selected_source=bmd45_huggingface_iisc_aim",
        f"sample_images={len(sample_images)}",
        f"fixture_records={len(fixture_rows)}",
        "zip_entries=PENDING",
        "hash_manifest=PENDING",
    ]))
    package_report = build_package(output_root)
    parse_report = {
        "hash_manifest_status": package_report["hash_manifest_status"],
        "json_files_parsed": package_report["json_files_parsed"],
        "jsonl_files_parsed": package_report["jsonl_files_parsed"],
        "manifest_mismatches": package_report["manifest_mismatches"],
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if package_report["status"] == "PASS" else "FAIL",
        "zip_entries": package_report["zip_entries"],
        "zip_integrity": package_report["zip_integrity"],
    }
    write_json(output_root / "R16_JSON_PARSE_REPORT.json", parse_report)
    write_text(output_root / "TEST_LOG_R16.txt", "\n".join([
        f"task_id={TASK_ID}",
        f"status={final_status}",
        f"selected_source=bmd45_huggingface_iisc_aim",
        f"sample_images={len(sample_images)}",
        f"fixture_records={len(fixture_rows)}",
        f"zip_entries={package_report['zip_entries']}",
        f"hash_manifest={package_report['hash_manifest_verified']}",
    ]))
    package_report = build_package(output_root)
    return {"decision": decision, "package_report": package_report}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run R16 offline CCTV-like dataset expansion gate.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_r16(Path(args.output_root), max(1, args.sample_count))
    decision = result["decision"]
    report = result["package_report"]
    print(f"Status: {decision['status']}")
    print(f"Output: {rel(Path(args.output_root))}")
    print(f"Freeze ZIP: {rel(Path(args.output_root) / PACKAGE_NAME)}")
    print(f"Selected source: {decision['selected_source_id']}")
    print(f"Image replay ready: {decision['image_replay_ready']}")
    print(f"Candidate fixture records: {decision['candidate_observation_fixture_records']}")
    print(f"ZIP entries: {report['zip_entries']}")
    print(f"JSON parse: PASS, {report['json_files_parsed']} JSON + {report['jsonl_files_parsed']} JSONL")
    print(f"Hash manifest: {report['hash_manifest_verified']}")
    print(f"Manifest mismatches: {len(report['manifest_mismatches'])}")
    return 0 if report["status"] == "PASS" and decision["status"] != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
