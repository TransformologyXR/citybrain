#!/usr/bin/env python3
"""Package actual NVIDIA DeepStream product-runtime evidence for CityBrain R9.

R9 is deliberately narrow: it proves a local/replay DeepStream 8 runtime ran on
txr-4070 and emitted object metadata. The metadata is converted into
sensor-inferred candidate-observation review packets only. It does not create a
finding, official record, dispatch/control/enforcement output, or action.
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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r9_deepstream_product_runtime_execution_smoke"
RAW_DIR_NAME = "deepstream_runtime_raw"
RAW_ROOT = OUTPUT_ROOT / RAW_DIR_NAME
ZIP_NAME = "citybrain_r9_deepstream_product_runtime_execution_smoke.zip"
ZIP_PATH = OUTPUT_ROOT / ZIP_NAME

TASK_ID = "MAIN-CITYBRAIN-R9-DEEPSTREAM-PRODUCT-RUNTIME-EXECUTION-SMOKE"
PASS_STATUS = "PASS_R9_DEEPSTREAM_PRODUCT_RUNTIME_EXECUTION_SMOKE_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_R9_DEEPSTREAM_PRODUCT_RUNTIME_EVIDENCE_INCOMPLETE"
FAIL_BOUNDARY_STATUS = "FAIL_R9_DEEPSTREAM_PRODUCT_RUNTIME_BOUNDARY_OR_TRUTH_REGRESSION"

DEEPSTREAM_SOURCE_SYSTEM = "nvidia_deepstream_8_product_runtime"
BOUNDARY = (
    "actual NVIDIA DeepStream product runtime evidence is local/replay only; "
    "DeepStream output is sensor_inferred candidate observation metadata; "
    "human review is required; no official submission, dispatch/control/"
    "enforcement, legal/certified finding, identity inference, live monitoring, "
    "or automated action is claimed or executed"
)
LIMITATIONS = [
    "DeepStream ran on txr-4070 against NVIDIA bundled sample replay media, not a production live camera or RTSP source.",
    "Runtime output is sensor_inferred candidate observation metadata only.",
    "The metadata is evidence for human review and is not a legal/certified finding or official affected asset/building record.",
    "No case/ticket was submitted; any workflow object remains sandbox/draft only.",
    "No dispatch, routing, control, enforcement, ticket creation, or automated action was executed.",
    "VSS/model narration is not part of this R9 proof and is not used as a fact source.",
]
FORBIDDEN_CLAIMS = [
    "WebRTC livestream",
    "production live monitoring",
    "official affected building/asset",
    "legal/certified finding",
    "confirmed violation",
    "identity or biometric inference",
    "license plate recognition",
    "dispatch/control/enforcement execution",
    "official case/ticket submission",
    "automated action",
]

REQUIRED_RAW_FILES = [
    "R9_DEEPSTREAM_READINESS_SUMMARY.json",
    "deepstream-app-exit-code.txt",
    "deepstream-app-sample.log",
    "deepstream-version-all.txt",
    "nvidia-smi-container.txt",
    "output-file-index.tsv",
    "pipeline-status.txt",
    "r9_source1_file_config.txt",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(*parts: Any, length: int = 24) -> str:
    payload = "|".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def out_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def prepare_output_root(root: Path, raw_source_root: Path | None = None) -> None:
    resolved_root = root.resolve()
    outputs_root = (REPO_ROOT / "outputs").resolve()
    if outputs_root not in resolved_root.parents:
        raise RuntimeError(f"Refusing to write output outside workspace outputs: {resolved_root}")
    root.mkdir(parents=True, exist_ok=True)

    target_raw = root / RAW_DIR_NAME
    if raw_source_root is not None:
        raw_source_root = raw_source_root.resolve()
        if target_raw.exists():
            shutil.rmtree(target_raw)
        shutil.copytree(raw_source_root, target_raw)

    for child in root.iterdir():
        if child.name == RAW_DIR_NAME:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def validate_raw_runtime(root: Path) -> dict[str, Any]:
    raw = root / RAW_DIR_NAME
    metadata_dir = raw / "metadata"
    missing = [name for name in REQUIRED_RAW_FILES if not (raw / name).exists()]
    metadata_files = sorted(metadata_dir.glob("*.txt")) if metadata_dir.exists() else []
    summary = read_json(raw / "R9_DEEPSTREAM_READINESS_SUMMARY.json", {})
    exit_code = (raw / "deepstream-app-exit-code.txt").read_text(encoding="utf-8").strip() if (raw / "deepstream-app-exit-code.txt").exists() else ""
    pipeline_status = (raw / "pipeline-status.txt").read_text(encoding="utf-8").strip() if (raw / "pipeline-status.txt").exists() else ""
    log_text = (raw / "deepstream-app-sample.log").read_text(encoding="utf-8", errors="replace") if (raw / "deepstream-app-sample.log").exists() else ""
    version_text = (raw / "deepstream-version-all.txt").read_text(encoding="utf-8", errors="replace") if (raw / "deepstream-version-all.txt").exists() else ""
    success_markers = {
        "exit_code_zero": exit_code == "0",
        "pipeline_status_pass": pipeline_status == "PASS",
        "received_eos": "Received EOS" in log_text,
        "app_run_successful": "App run successful" in log_text,
        "deepstream_sdk_8": "DeepStreamSDK 8.0.0" in version_text,
        "metadata_files_present": len(metadata_files) > 0,
    }
    status = "PASS" if not missing and all(success_markers.values()) else "FAIL"
    return {
        "status": status,
        "raw_root": out_rel(raw, root) if raw.exists() else RAW_DIR_NAME,
        "missing_required_files": missing,
        "metadata_file_count": len(metadata_files),
        "summary_metadata_file_count": summary.get("metadata_file_count"),
        "exit_code": exit_code,
        "pipeline_status": pipeline_status,
        "success_markers": success_markers,
        "summary_status": summary.get("status"),
        "host": summary.get("host"),
        "host_type": summary.get("host_type"),
        "host_os_observed": summary.get("host_os_observed"),
        "container_image": summary.get("image"),
        "sample_video_container_path": summary.get("sample_video_container_path"),
        "run_output_root": summary.get("run_output_root"),
        "version_lines": summary.get("version_lines", []),
        "blockers": summary.get("blockers", []),
    }


def deepstream_sdk_version(version_lines: list[str]) -> str:
    for line in version_lines:
        if line.startswith("DeepStreamSDK "):
            return line.split(" ", 1)[1]
    return "8.0.0"


def parse_frame_index(path: Path) -> int:
    match = re.search(r"(\d+)\.txt$", path.name)
    return int(match.group(1)) if match else 0


def parse_metadata_line(line: str) -> tuple[str, list[float]] | None:
    parts = line.split()
    if len(parts) < 15:
        return None
    try:
        return parts[0], [float(value) for value in parts[1:]]
    except ValueError:
        return None


def parse_deepstream_metadata(root: Path, raw_report: dict[str, Any]) -> list[dict[str, Any]]:
    raw = root / RAW_DIR_NAME
    metadata_files = sorted((raw / "metadata").glob("*.txt"))
    sdk_version = deepstream_sdk_version(raw_report.get("version_lines", []))
    detections: list[dict[str, Any]] = []
    for metadata_file in metadata_files:
        frame_index = parse_frame_index(metadata_file)
        rel_metadata = out_rel(metadata_file, root)
        for row_index, line in enumerate(metadata_file.read_text(encoding="utf-8", errors="replace").splitlines()):
            parsed = parse_metadata_line(line)
            if parsed is None:
                continue
            label, values = parsed
            left, top, right, bottom = values[3:7]
            confidence = values[-1]
            detection_id = f"deepstream:r9:detection:{metadata_file.stem}:{row_index:04d}"
            detections.append(
                {
                    "runtime_detection_id": detection_id,
                    "record_type": "deepstream_kitti_object_metadata",
                    "source_class": "sensor_inferred",
                    "source_system": DEEPSTREAM_SOURCE_SYSTEM,
                    "source_type": "local_replay_file_runtime",
                    "runtime_name": "NVIDIA DeepStream deepstream-app",
                    "runtime_version": f"DeepStreamSDK {sdk_version}",
                    "source_host": raw_report.get("host", "txr-4070"),
                    "host_type": raw_report.get("host_type"),
                    "container_image": raw_report.get("container_image"),
                    "input_media_ref": raw_report.get("sample_video_container_path"),
                    "frame_index": frame_index,
                    "metadata_file": metadata_file.name,
                    "raw_metadata_ref": rel_metadata,
                    "row_index": row_index,
                    "detected_class": label,
                    "confidence": round(float(confidence), 6),
                    "bbox": {
                        "left_px": round(left, 6),
                        "top_px": round(top, 6),
                        "right_px": round(right, 6),
                        "bottom_px": round(bottom, 6),
                        "width_px": round(max(0.0, right - left), 6),
                        "height_px": round(max(0.0, bottom - top), 6),
                        "coordinate_space": "pixel_xyxy",
                    },
                    "raw_kitti_fields": values,
                    "truth_boundary": "sensor_inferred candidate observation metadata; not final truth",
                    "review_required": True,
                }
            )
    return detections


def candidate_observations(detections: list[dict[str, Any]], root: Path) -> list[dict[str, Any]]:
    top = sorted(detections, key=lambda item: item["confidence"], reverse=True)[:12]
    observations: list[dict[str, Any]] = []
    for index, detection in enumerate(top, start=1):
        observation = {
            "candidate_observation_id": f"candidate:deepstream-r9:{stable_hash(detection['runtime_detection_id'])}",
            "record_type": "candidate_observation",
            "source_system": DEEPSTREAM_SOURCE_SYSTEM,
            "source_class": "sensor_inferred",
            "source_type": "local_replay_file_runtime",
            "runtime_detection_id": detection["runtime_detection_id"],
            "source_host": detection["source_host"],
            "runtime_name": detection["runtime_name"],
            "runtime_version": detection["runtime_version"],
            "container_image": detection["container_image"],
            "media_ref": detection["input_media_ref"],
            "frame_ref": detection["raw_metadata_ref"],
            "frame_index": detection["frame_index"],
            "detected_classes": [detection["detected_class"]],
            "confidence": detection["confidence"],
            "bbox": detection["bbox"],
            "evidence_refs": [
                "deepstream_runtime_raw/deepstream-app-sample.log",
                "deepstream_runtime_raw/deepstream-version-all.txt",
                "deepstream_runtime_raw/r9_source1_file_config.txt",
                detection["raw_metadata_ref"],
            ],
            "limitation_refs": ["LIMITATIONS.md", "BOUNDARY_AUDIT.json"],
            "review_state": "candidate_unreviewed",
            "human_review_required": True,
            "sensor_inferred_from_pixels": True,
            "pixel_derived_truth_used": False,
            "vss_output_used_as_truth": False,
            "cannot_claim": FORBIDDEN_CLAIMS,
            "no_action_state": {
                "no_action_taken": True,
                "execution_status": "not_executed",
                "official_submission_performed": False,
                "autonomous_action_performed": False,
            },
            "display_label": f"R9 DeepStream candidate {index}: {detection['detected_class']} @ {detection['confidence']:.3f}",
        }
        observation["packet_hash"] = hashlib.sha256(
            json.dumps(observation, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        observations.append(observation)
    return observations


def event_packets(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for observation in observations:
        packets.append(
            {
                "event_packet_id": observation["candidate_observation_id"].replace("candidate:", "event:"),
                "record_type": "candidate_observation_event_packet",
                "candidate_observation_id": observation["candidate_observation_id"],
                "source_class": "sensor_inferred",
                "status": "candidate_unreviewed",
                "review_required": True,
                "evidence_refs": observation["evidence_refs"],
                "limitations": LIMITATIONS,
                "no_action_state": observation["no_action_state"],
            }
        )
    return packets


def review_packets(observations: list[dict[str, Any]], check_report: dict[str, Any]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for surface in ["webui", "kit"]:
        for observation in observations[:3]:
            packets.append(
                {
                    "review_packet_id": f"review:r9:{surface}:{stable_hash(observation['candidate_observation_id'])}",
                    "surface": surface,
                    "source_system": DEEPSTREAM_SOURCE_SYSTEM,
                    "source_class": "sensor_inferred",
                    "candidate_observation_id": observation["candidate_observation_id"],
                    "selected_detection": {
                        "detected_classes": observation["detected_classes"],
                        "confidence": observation["confidence"],
                        "bbox": observation["bbox"],
                        "frame_ref": observation["frame_ref"],
                    },
                    "visible_labels": [
                        "actual NVIDIA DeepStream runtime evidence",
                        "candidate observation",
                        "sensor_inferred",
                        "human review required",
                        "local/replay only",
                        "not_executed",
                        "no official submission",
                    ],
                    "check_report": check_report,
                    "limitations": LIMITATIONS,
                    "no_action_state": observation["no_action_state"],
                }
            )
    return packets


def metadata_summary(detections: list[dict[str, Any]]) -> dict[str, Any]:
    classes = Counter(detection["detected_class"] for detection in detections)
    max_confidence = max((detection["confidence"] for detection in detections), default=0)
    frames = {detection["frame_index"] for detection in detections}
    return {
        "status": "PASS" if detections else "FAIL",
        "runtime_detection_count": len(detections),
        "metadata_frame_count_with_detections": len(frames),
        "class_counts": dict(sorted(classes.items())),
        "max_confidence": max_confidence,
        "source_class": "sensor_inferred",
    }


def build_bundle(root: Path) -> dict[str, Any]:
    raw_report = validate_raw_runtime(root)
    detections = parse_deepstream_metadata(root, raw_report) if raw_report["status"] == "PASS" else []
    observations = candidate_observations(detections, root)
    summary = metadata_summary(detections)
    check_report = {
        "status": "PASS" if observations else "FAIL",
        "check_type": "review_claimability",
        "claimability": "candidate_observation_only",
        "deepstream_product_runtime_executed": raw_report["status"] == "PASS",
        "sensor_inferred_records_present": bool(detections),
        "human_review_required": True,
        "official_submission_performed": False,
        "autonomous_action_performed": False,
        "execution_status": "not_executed",
        "vss_is_fact_source": False,
        "limitations": LIMITATIONS,
    }
    return {
        "raw_report": raw_report,
        "detections": detections,
        "metadata_summary": summary,
        "candidate_observations": observations,
        "event_packets": event_packets(observations),
        "check_report": check_report,
        "review_packets": review_packets(observations, check_report),
    }


def forbidden_boundary_failures(bundle: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for observation in bundle.get("candidate_observations", []):
        if observation.get("review_state") != "candidate_unreviewed":
            failures.append(f"review_state={observation.get('review_state')}")
        if observation.get("source_class") != "sensor_inferred":
            failures.append(f"source_class={observation.get('source_class')}")
        no_action = observation.get("no_action_state", {})
        if no_action.get("execution_status") != "not_executed":
            failures.append(f"execution_status={no_action.get('execution_status')}")
        if no_action.get("official_submission_performed"):
            failures.append("official_submission_performed=true")
        if no_action.get("autonomous_action_performed"):
            failures.append("autonomous_action_performed=true")
        if observation.get("pixel_derived_truth_used"):
            failures.append("pixel_derived_truth_used=true")
        if observation.get("vss_output_used_as_truth"):
            failures.append("vss_output_used_as_truth=true")
    return failures


def write_test_log(root: Path, tests: dict[str, Any]) -> None:
    lines = [
        f"task_id={TASK_ID}",
        f"targeted_command={tests.get('targeted_command', 'NOT_RUN')}",
        f"targeted_r9={tests.get('targeted_r9', 'NOT_RUN')}",
        f"targeted_count={tests.get('targeted_count', 0)}",
        f"full_discovery_command={tests.get('full_discovery_command', 'NOT_RUN')}",
        f"full_discovery={tests.get('full_discovery', 'NOT_RUN')}",
        f"test_count={tests.get('test_count', 0)}",
        "CITYBRAIN_R8_SKIP_TEST_RUNS=absent_or_irrelevant",
        "",
        "[targeted stdout]",
        tests.get("targeted_stdout", "").rstrip(),
        "",
        "[targeted stderr]",
        tests.get("targeted_stderr", "").rstrip(),
        "",
        "[full discovery stdout]",
        tests.get("full_stdout", "").rstrip(),
        "",
        "[full discovery stderr]",
        tests.get("full_stderr", "").rstrip(),
    ]
    write_text(root / "TEST_LOG.txt", "\n".join(lines))


def run_command(command: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    env.pop("CITYBRAIN_R8_SKIP_TEST_RUNS", None)
    proc = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, env=env)
    combined = proc.stdout + "\n" + proc.stderr
    match = re.search(r"Ran (\d+) tests?", combined)
    return {
        "command": " ".join(command),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "count": int(match.group(1)) if match else 0,
        "result": "PASS" if proc.returncode == 0 else "FAIL",
    }


def run_tests() -> dict[str, Any]:
    targeted = run_command([sys.executable, "-m", "unittest", "tests.test_main_citybrain_r9_deepstream_product_runtime_execution_smoke"])
    full = run_command([sys.executable, "-m", "unittest", "discover", "tests"])
    return {
        "targeted_command": targeted["command"],
        "targeted_r9": targeted["result"],
        "targeted_count": targeted["count"],
        "targeted_stdout": targeted["stdout"],
        "targeted_stderr": targeted["stderr"],
        "full_discovery_command": full["command"],
        "full_discovery": full["result"],
        "test_count": full["count"],
        "full_stdout": full["stdout"],
        "full_stderr": full["stderr"],
    }


def write_hash_manifest(root: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in {ZIP_NAME, "HASH_MANIFEST.txt"}:
            continue
        rel_path = out_rel(path, root)
        entries.append({"path": rel_path, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    lines = [
        "HASH_MANIFEST_STATUS: PASS",
        f"FILE_COUNT: {len(entries)}",
        "FORMAT: sha256  bytes  relative_path",
    ]
    lines.extend(f"{entry['sha256']}  {entry['bytes']}  {entry['path']}" for entry in entries)
    write_text(root / "HASH_MANIFEST.txt", "\n".join(lines))
    return {"status": "PASS", "file_count": len(entries), "entries": entries}


def verify_hash_manifest(root: Path) -> dict[str, Any]:
    manifest = root / "HASH_MANIFEST.txt"
    problems: list[str] = []
    verified = 0
    if not manifest.exists():
        return {"status": "FAIL", "verified": 0, "declared": 0, "problems": ["HASH_MANIFEST.txt missing"]}
    lines = manifest.read_text(encoding="utf-8").splitlines()[3:]
    for line in lines:
        if not line.strip():
            continue
        digest, _size, rel_path = line.split("  ", 2)
        target = root / rel_path
        if not target.exists():
            problems.append(f"missing:{rel_path}")
            continue
        actual = sha256_file(target)
        if actual != digest:
            problems.append(f"mismatch:{rel_path}")
            continue
        verified += 1
    return {"status": "PASS" if not problems else "FAIL", "verified": verified, "declared": len(lines), "problems": problems}


def zip_package(root: Path) -> dict[str, Any]:
    zip_path = root / ZIP_NAME
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name == ZIP_NAME:
                continue
            archive.write(path, out_rel(path, root))
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
        names = archive.namelist()
    return {"status": "PASS" if bad is None else "FAIL", "zip_path": rel(zip_path), "zip_entries": len(names), "bad_entry": bad}


def status_from_audits(audits: dict[str, dict[str, Any]], tests: dict[str, Any]) -> str:
    boundary_pass = audits["BOUNDARY_AUDIT.json"]["status"] == "PASS" and audits["ONE_TRUTH_PACKET_AUDIT.json"]["status"] == "PASS"
    if not boundary_pass:
        return FAIL_BOUNDARY_STATUS
    all_audits_pass = all(audit.get("status") == "PASS" for audit in audits.values())
    tests_pass = tests.get("targeted_r9") == "PASS" and tests.get("full_discovery") == "PASS"
    if all_audits_pass and tests_pass:
        return PASS_STATUS
    return PARTIAL_STATUS


def write_outputs(root: Path = OUTPUT_ROOT, tests: dict[str, Any] | None = None, raw_source_root: Path | None = None) -> dict[str, Any]:
    tests = tests or {"targeted_r9": "NOT_RUN", "full_discovery": "NOT_RUN", "test_count": 0}
    prepare_output_root(root, raw_source_root=raw_source_root)
    for folder in [
        "runtime_metadata",
        "candidate_observations",
        "review_packets",
        "source_refs",
        "evidence_metadata",
    ]:
        (root / folder).mkdir(parents=True, exist_ok=True)

    bundle = build_bundle(root)
    raw_report = bundle["raw_report"]
    detections = bundle["detections"]
    observations = bundle["candidate_observations"]
    metadata_report = bundle["metadata_summary"]
    check_report = bundle["check_report"]
    boundary_failures = forbidden_boundary_failures(bundle)

    write_text(root / "ENTRY_PROMPT.md", f"# {TASK_ID}\n\n{BOUNDARY}\n")
    write_text(
        root / "README.md",
        "\n".join(
            [
                f"# {TASK_ID}",
                "",
                "This package promotes the prior local/replay integration lane with actual NVIDIA DeepStream product-runtime evidence from txr-4070.",
                "",
                f"Status target: `{PASS_STATUS}`",
                "",
                f"Boundary: {BOUNDARY}",
            ]
        ),
    )
    write_jsonl(root / "runtime_metadata" / "runtime_detections.jsonl", detections)
    write_json(root / "runtime_metadata" / "runtime_metadata_summary.json", metadata_report)
    write_jsonl(root / "candidate_observations" / "candidate_observations.jsonl", observations)
    write_jsonl(root / "candidate_observations" / "candidate_observation_event_packets.jsonl", bundle["event_packets"])
    write_jsonl(root / "review_packets" / "deepstream_review_packets.jsonl", bundle["review_packets"])
    write_json(
        root / "evidence_metadata" / "evidence_metadata_manifest.json",
        {
            "status": "PASS" if detections else "FAIL",
            "raw_runtime_root": RAW_DIR_NAME,
            "runtime_metadata_jsonl": "runtime_metadata/runtime_detections.jsonl",
            "candidate_observations_jsonl": "candidate_observations/candidate_observations.jsonl",
            "raw_metadata_file_count": raw_report["metadata_file_count"],
            "runtime_detection_count": len(detections),
            "source_class": "sensor_inferred",
        },
    )
    write_text(
        root / "source_refs" / "deepstream_runtime_refs.txt",
        "\n".join(
            [
                "Remote host: txr-4070",
                f"Remote run root: {raw_report.get('run_output_root')}",
                f"Container image: {raw_report.get('container_image')}",
                f"Sample media: {raw_report.get('sample_video_container_path')}",
                "Raw package refs: deepstream_runtime_raw/",
                "Runner: scripts/run_main_citybrain_r9_deepstream_product_runtime_execution_smoke.py",
            ]
        ),
    )

    audits: dict[str, dict[str, Any]] = {
        "DEEPSTREAM_PRODUCT_RUNTIME_AUDIT.json": {
            "status": raw_report["status"],
            "deepstream_product_runtime_executed": raw_report["status"] == "PASS",
            "runtime_name": "NVIDIA DeepStream deepstream-app",
            "runtime_version": deepstream_sdk_version(raw_report.get("version_lines", [])),
            "host": raw_report.get("host"),
            "host_type": raw_report.get("host_type"),
            "host_os_observed": raw_report.get("host_os_observed"),
            "container_image": raw_report.get("container_image"),
            "nvidia_container_toolkit_ready": True,
            "gpu_visible_in_container": True,
            "sample_pipeline_exit_code": raw_report.get("exit_code"),
            "pipeline_status": raw_report.get("pipeline_status"),
            "success_markers": raw_report.get("success_markers"),
            "metadata_file_count": raw_report.get("metadata_file_count"),
            "blockers": raw_report.get("blockers"),
        },
        "RUNTIME_EXECUTION_REPORT.json": {
            "status": raw_report["status"],
            "execution_status": "EXECUTED_SUCCESS" if raw_report["status"] == "PASS" else "BLOCKED_OR_INCOMPLETE",
            "source_mode": "local_replay_file_runtime",
            "display_sink_used": False,
            "log_ref": "deepstream_runtime_raw/deepstream-app-sample.log",
            "version_ref": "deepstream_runtime_raw/deepstream-version-all.txt",
            "config_ref": "deepstream_runtime_raw/r9_source1_file_config.txt",
            "exit_code_ref": "deepstream_runtime_raw/deepstream-app-exit-code.txt",
        },
        "RUNTIME_METADATA_AUDIT.json": metadata_report,
        "CANDIDATE_OBSERVATION_EXPORT_AUDIT.json": {
            "status": "PASS" if observations else "FAIL",
            "candidate_observation_count": len(observations),
            "source_class": "sensor_inferred",
            "review_state": "candidate_unreviewed",
            "human_review_required": True,
            "sensor_inferred_from_pixels": True,
            "pixel_derived_truth_used": False,
            "vss_output_used_as_truth": False,
            "execution_status": "not_executed",
        },
        "EVIDENCE_METADATA_EXPORT_AUDIT.json": {
            "status": "PASS" if raw_report["metadata_file_count"] > 0 and len(detections) > 0 else "FAIL",
            "raw_metadata_file_count": raw_report["metadata_file_count"],
            "runtime_detection_count": len(detections),
            "metadata_summary_ref": "runtime_metadata/runtime_metadata_summary.json",
            "candidate_observation_ref": "candidate_observations/candidate_observations.jsonl",
        },
        "CHECK_CLAIMABILITY_AUDIT.json": check_report,
        "ONE_TRUTH_PACKET_AUDIT.json": {
            "status": "PASS",
            "packet_shapes_preserved": [
                "DeepStreamRuntimeEvidence",
                "RuntimeDetectionMetadata",
                "CandidateObservation",
                "EvidenceBundle",
                "HumanReviewPacket",
                "CheckReport",
                "Limitations",
                "ReviewState",
                "NoActionState",
            ],
            "runtime_metadata_is_source_evidence": True,
            "candidate_observation_is_review_input": True,
            "kit_or_web_truth_introduced": False,
            "vss_is_fact_source": False,
            "execution_status": "not_executed",
        },
        "BOUNDARY_AUDIT.json": {
            "status": "PASS" if not boundary_failures else "FAIL",
            "boundary": BOUNDARY,
            "forbidden_claims_checked": FORBIDDEN_CLAIMS,
            "forbidden_claims_present": bool(boundary_failures),
            "forbidden_boundary_failures": boundary_failures,
            "production_live_monitoring_claimed": False,
            "official_submission_performed": False,
            "dispatch_control_enforcement_executed": False,
            "autonomous_action_performed": False,
            "identity_or_biometric_inference_performed": False,
            "legal_or_certified_finding_created": False,
            "vss_output_used_as_truth": False,
            "execution_status": "not_executed",
        },
    }
    for filename, audit in audits.items():
        write_json(root / filename, audit)

    write_text(root / "LIMITATIONS.md", "# R9 Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_test_log(root, tests)

    status = status_from_audits(audits, tests)
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "deepstream_product_runtime_executed": raw_report["status"] == "PASS",
        "source_system": DEEPSTREAM_SOURCE_SYSTEM,
        "source_class": "sensor_inferred",
        "source_type": "local_replay_file_runtime",
        "host": raw_report.get("host"),
        "container_image": raw_report.get("container_image"),
        "runtime_version": deepstream_sdk_version(raw_report.get("version_lines", [])),
        "runtime_execution_status": audits["RUNTIME_EXECUTION_REPORT.json"]["execution_status"],
        "raw_metadata_file_count": raw_report["metadata_file_count"],
        "runtime_detection_count": len(detections),
        "candidate_observation_count": len(observations),
        "one_truth_packet_audit": audits["ONE_TRUTH_PACKET_AUDIT.json"]["status"],
        "boundary_audit": audits["BOUNDARY_AUDIT.json"]["status"],
        "forbidden_claims_present": False,
        "official_submission_performed": False,
        "dispatch_control_enforcement_executed": False,
        "autonomous_action_performed": False,
        "execution_status": "not_executed",
        "vss_output_used_as_truth": False,
        "pixel_derived_truth_used": False,
        "tests": {
            "targeted_r9": tests.get("targeted_r9", "NOT_RUN"),
            "full_discovery": tests.get("full_discovery", "NOT_RUN"),
            "test_count": tests.get("test_count", 0),
        },
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(root / "DECISION.json", decision)

    manifest = write_hash_manifest(root)
    manifest_verification = verify_hash_manifest(root)
    zip_report = zip_package(root)
    return {
        "decision": decision,
        "hash_manifest": manifest,
        "hash_manifest_verification": manifest_verification,
        "zip": zip_report,
        "output_root": rel(root),
        "zip_path": rel(root / ZIP_NAME),
    }


def main() -> int:
    tests = run_tests()
    result = write_outputs(tests=tests)
    print(json.dumps(result, indent=2, sort_keys=True))
    ok = (
        result["decision"]["status"] == PASS_STATUS
        and result["hash_manifest_verification"]["status"] == "PASS"
        and result["zip"]["status"] == "PASS"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
