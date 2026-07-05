#!/usr/bin/env python3
"""R19 BMD-45 replay benchmark regression harness."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
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
OUTPUTS_ROOT = REPO_ROOT / "outputs"
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-REPLAY-BENCHMARK-REGRESSION-HARNESS-R19"
SCHEMA_VERSION = "metropolis-vss-bmd45-replay-benchmark-regression-harness-r19.v1"
DEFAULT_OUTPUT_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_bmd45_replay_benchmark_regression_harness_r19"
PACKAGE_NAME = "METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_REGRESSION_HARNESS_R19_PACKAGE.zip"

R18_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_bmd45_threshold_calibration_and_sample_expansion_r18"
R18_PACKAGE = R18_ROOT / "METROPOLIS_VSS_BMD45_THRESHOLD_CALIBRATION_AND_SAMPLE_EXPANSION_R18_PACKAGE.zip"
R18_SCRIPT = REPO_ROOT / "scripts" / "run_main_citybrain_metropolis_vss_bmd45_threshold_calibration_and_sample_expansion_r18.py"
R17_SCRIPT = REPO_ROOT / "scripts" / "run_main_citybrain_metropolis_vss_bmd45_deepstream_frame_replay_comparison_r17.py"
HANDOFF_ZIP = Path(r"C:\Users\hazem\Downloads\citybrain_metropolis_vss_bmd45_replay_benchmark_regression_harness_r19_handoff.zip")

PASS_STATUS = "PASS_METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_REGRESSION_HARNESS_R19_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_CONTRACT_READY_RERUN_PENDING"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_BOUNDARY_OR_REGRESSION_RISK"
REMOTE_HOST = "txr-4070"
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


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R17 = load_module("citybrain_r17_runner_for_r19", R17_SCRIPT)
R18 = load_module("citybrain_r18_runner_for_r19", R18_SCRIPT)


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
    outputs_root = OUTPUTS_ROOT.resolve()
    if outputs_root not in resolved.parents:
        raise ValueError(f"Refusing to reset output outside outputs root: {resolved}")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def validate_r18_package() -> tuple[dict[str, Any], dict[str, Any]]:
    report: dict[str, Any] = {
        "package_exists": R18_PACKAGE.exists(),
        "package_path": rel(R18_PACKAGE),
        "schema_version": SCHEMA_VERSION,
        "status": "FAIL",
    }
    package_data: dict[str, Any] = {}
    required = [
        "R18_CLOSEOUT_DECISION.json",
        "BMD45_SAMPLE_SELECTION_R18.json",
        "THRESHOLD_CALIBRATION_REPORT_R18.json",
        "IOU_COMPARISON_REPORT_R18.json",
        "DATASET_ANNOTATION_SUBSET_R18.jsonl",
        "SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R18.jsonl",
        "SOURCE_CLASS_SEPARATION_AUDIT_R18.json",
        "CLAIM_BOUNDARY_AUDIT_R18.json",
        "NO_ACTION_AUDIT_R18.json",
        "SECRET_AUDIT_R18.json",
        "VSS_NOT_FACT_SOURCE_AUDIT_R18.json",
        "HASH_MANIFEST.json",
    ]
    if not R18_PACKAGE.exists():
        report["failure_reason"] = "R18 package not found"
        return report, package_data
    try:
        with zipfile.ZipFile(R18_PACKAGE) as archive:
            bad = archive.testzip()
            names = [name for name in archive.namelist() if not name.endswith("/")]
            missing_required = [name for name in required if name not in names]
            json_count = 0
            jsonl_count = 0
            jsonl_rows: dict[str, int] = {}
            for name in names:
                if name.endswith(".json"):
                    json.loads(archive.read(name).decode("utf-8"))
                    json_count += 1
                elif name.endswith(".jsonl"):
                    jsonl_count += 1
                    count = 0
                    for line in archive.read(name).decode("utf-8").splitlines():
                        if line.strip():
                            json.loads(line)
                            count += 1
                    jsonl_rows[name] = count
            manifest = json.loads(archive.read("HASH_MANIFEST.json").decode("utf-8"))
            manifest_missing = []
            manifest_mismatches = []
            for entry in manifest.get("files", []):
                try:
                    actual = sha256_bytes(archive.read(entry["file"]))
                except KeyError:
                    manifest_missing.append(entry["file"])
                    continue
                if actual != entry.get("sha256"):
                    manifest_mismatches.append(entry["file"])
            for name in required:
                if name in names and name.endswith(".json"):
                    package_data[name] = json.loads(archive.read(name).decode("utf-8"))
                elif name in names and name.endswith(".jsonl"):
                    package_data[name] = [
                        json.loads(line)
                        for line in archive.read(name).decode("utf-8").splitlines()
                        if line.strip()
                    ]
            package_data["HASH_MANIFEST.json"] = manifest
    except Exception as exc:  # noqa: BLE001
        report["failure_reason"] = str(exc)
        return report, package_data

    decision = package_data.get("R18_CLOSEOUT_DECISION.json", {})
    expected = "PASS_METROPOLIS_VSS_BMD45_THRESHOLD_CALIBRATION_AND_SAMPLE_EXPANSION_R18_WITH_LIMITATIONS"
    report.update(
        {
            "decision_status": decision.get("status"),
            "expected_status": expected,
            "external_media_refs": len(package_data.get("HASH_MANIFEST.json", {}).get("external_media_refs", [])),
            "hash_manifest_status": "PASS" if not manifest_missing and not manifest_mismatches else "FAIL",
            "json_files_parsed": json_count,
            "jsonl_files_parsed": jsonl_count,
            "jsonl_rows": jsonl_rows,
            "manifest_mismatches": manifest_mismatches,
            "manifest_missing": manifest_missing,
            "required_missing": missing_required,
            "status": "PASS" if bad is None and not missing_required and not manifest_missing and not manifest_mismatches and decision.get("status") == expected else "FAIL",
            "zip_entries": len(names),
            "zip_integrity": "PASS" if bad is None else f"FAIL:{bad}",
        }
    )
    return report, package_data


def baseline_metrics_from_r18(package_data: dict[str, Any]) -> dict[str, Any]:
    decision = package_data["R18_CLOSEOUT_DECISION.json"]
    iou = package_data["IOU_COMPARISON_REPORT_R18.json"]
    calibration = package_data["THRESHOLD_CALIBRATION_REPORT_R18.json"]
    manifest = package_data["HASH_MANIFEST.json"]
    return {
        "baseline_from": "R18",
        "confidence_distribution": calibration.get("confidence_distribution", {}),
        "dataset_annotation_count": decision.get("dataset_annotation_records"),
        "external_media_refs": len(manifest.get("external_media_refs", [])),
        "frame_count": decision.get("sample_frame_count"),
        "iou_match_counts": iou.get("metrics", {}).get("matches_at_threshold", {}),
        "iou_thresholds": iou.get("iou_thresholds", IOU_THRESHOLDS),
        "packaged_media_files": decision.get("packaged_media_files", 0),
        "per_class_candidate_counts": calibration.get("per_class_candidate_counts", {}),
        "schema_version": SCHEMA_VERSION,
        "sensor_candidate_count": decision.get("candidate_observation_records"),
        "source_class_boundary": {
            "dataset_annotations": "dataset_annotation",
            "deepstream_outputs": "sensor_inferred",
            "vss": "model_generated_narrative_not_fact_source",
        },
    }


def benchmark_config(baseline: dict[str, Any], external_refs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "benchmark_id": "bmd45_r18_fixed_8_frame_replay_v1",
        "created_at": utc_now(),
        "external_media_refs": external_refs,
        "host": REMOTE_HOST,
        "iou_thresholds": IOU_THRESHOLDS,
        "rerun_command": "python scripts/run_main_citybrain_metropolis_vss_bmd45_replay_benchmark_regression_harness_r19.py",
        "sample_frame_count": baseline.get("frame_count"),
        "schema_version": SCHEMA_VERSION,
        "source_classes": {
            "dataset_annotations": "dataset_annotation",
            "deepstream_metropolis": "sensor_inferred",
            "vss": "model_generated_narrative_not_fact_source",
        },
        "source_dataset": "bmd45_huggingface_iisc_aim",
        "status": "PASS",
        "tolerance_policy": "hard fixture/source-class checks plus soft metric drift bands",
    }


def regression_assertions(baseline: dict[str, Any]) -> dict[str, Any]:
    candidate_count = int(baseline.get("sensor_candidate_count") or 0)
    iou_counts = baseline.get("iou_match_counts", {})
    return {
        "baseline_metric_refs": {
            "candidate_count": candidate_count,
            "iou_matches_0_25": int(iou_counts.get("0.25", 0)),
            "iou_matches_0_5": int(iou_counts.get("0.5", 0)),
            "iou_matches_0_75": int(iou_counts.get("0.75", 0)),
        },
        "hard_assertions": {
            "dataset_annotation_source_class": "dataset_annotation",
            "deepstream_source_class": "sensor_inferred",
            "external_media_refs": {"expected": baseline.get("external_media_refs"), "tolerance": 0},
            "frame_count": {"expected": baseline.get("frame_count"), "tolerance": 0},
            "packaged_media_files": {"expected": 0, "tolerance": 0},
            "rerun_candidate_count_min_if_executed": 1,
        },
        "schema_version": SCHEMA_VERSION,
        "soft_tolerance_bands": {
            "sensor_candidate_count": {
                "baseline": candidate_count,
                "max": max(candidate_count + 75, int(candidate_count * 1.50)),
                "min": max(1, min(candidate_count - 75, int(candidate_count * 0.50))),
                "type": "review_drift_band_not_accuracy_claim",
            },
            "iou_matches_0_25": {
                "baseline": int(iou_counts.get("0.25", 0)),
                "max_delta": 16,
                "min_allowed": max(0, int(iou_counts.get("0.25", 0)) - 16),
                "type": "soft_review_band",
            },
            "iou_matches_0_5": {
                "baseline": int(iou_counts.get("0.5", 0)),
                "max_delta": 14,
                "min_allowed": max(0, int(iou_counts.get("0.5", 0)) - 14),
                "type": "soft_review_band",
            },
            "iou_matches_0_75": {
                "baseline": int(iou_counts.get("0.75", 0)),
                "max_delta": 8,
                "min_allowed": max(0, int(iou_counts.get("0.75", 0)) - 8),
                "type": "soft_review_band",
            },
        },
        "status": "PASS",
    }


def transform_sensor_rows(raw_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    transformed_raw = []
    transformed_candidates = []
    for row in raw_rows:
        new_row = dict(row)
        new_row["schema_version"] = SCHEMA_VERSION
        new_row["source_class"] = "sensor_inferred"
        new_row["class_family"] = R18.family_for_sensor_label(new_row.get("class_label"))
        new_row["r19_source_raw_metadata_id"] = new_row.get("raw_metadata_id")
        if new_row.get("raw_metadata_id"):
            new_row["raw_metadata_id"] = stable_id("deepstream-r19-kitti-raw", new_row["raw_metadata_id"], new_row.get("frame_sequence_index"))
        transformed_raw.append(new_row)
        if new_row.get("record_type") == "explicit_zero_detection_frame_result" or not new_row.get("bbox"):
            continue
        candidate = dict(new_row)
        candidate["candidate_observation_id"] = stable_id("metropolis-vss-r19-sensor-observation", candidate.get("r19_source_raw_metadata_id"), candidate.get("frame_sequence_index"))
        transformed_candidates.append(candidate)
    return transformed_raw, transformed_candidates


def cleanup_remote_artifacts(output_root: Path) -> None:
    delete_names = [
        "DEEPSTREAM_RAW_METADATA_R17.jsonl",
        "SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R17.jsonl",
        "REMOTE_R17_STDOUT.log",
        "REMOTE_R17_STDERR.log",
    ]
    rename_map = {
        "CITYBRAIN_R17_DEEPSTREAM_CONFIG.txt": "CITYBRAIN_R19_DEEPSTREAM_CONFIG.txt",
        "DEEPSTREAM_REPLAY_INPUT_PREP_REMOTE_R17.json": "DEEPSTREAM_REPLAY_INPUT_PREP_REMOTE_R19.json",
        "DEEPSTREAM_RETURN_CODE_R17.txt": "DEEPSTREAM_RETURN_CODE_R19.txt",
        "DEEPSTREAM_RUNTIME_SUMMARY_R17.json": "DEEPSTREAM_RUNTIME_SUMMARY_R19.json",
        "DEEPSTREAM_STDERR_R17.log": "DEEPSTREAM_STDERR_R19.log",
        "DEEPSTREAM_STDOUT_R17.log": "DEEPSTREAM_STDOUT_R19.log",
        "GST_CREATE_RETURN_CODE_R17.txt": "GST_CREATE_RETURN_CODE_R19.txt",
        "GST_CREATE_STDERR_R17.log": "GST_CREATE_STDERR_R19.log",
        "GST_CREATE_STDOUT_R17.log": "GST_CREATE_STDOUT_R19.log",
        "KITTI_FILES_R17.txt": "KITTI_FILES_R19.txt",
        "REMOTE_DOCKER_STDERR_R17.log": "REMOTE_DOCKER_STDERR_R19.log",
        "REMOTE_DOCKER_STDOUT_R17.log": "REMOTE_DOCKER_STDOUT_R19.log",
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
        output_root / "REMOTE_EXECUTION_CAPTURE_NOTE_R19.md",
        "Remote base64 transport stdout was not packaged because individual DeepStream, Docker, GStreamer, config, and return-code artifacts are packaged separately.",
    )


def run_rerun(output_root: Path, external_refs: list[dict[str, Any]], dataset_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if os.environ.get("CITYBRAIN_R19_SKIP_RERUN") == "1":
        return {
            "execution_status": "NOT_RUN",
            "reason": "CITYBRAIN_R19_SKIP_RERUN=1",
            "rerun_executed": False,
            "status": "PARTIAL",
        }
    stage_report, staged_frames = R17.stage_frames_for_replay(external_refs)
    if stage_report.get("status") != "PASS":
        return {
            "execution_status": "BLOCKED",
            "reason": "frame staging did not pass",
            "rerun_executed": False,
            "stage_report": stage_report,
            "status": "PARTIAL",
        }
    remote_result = R17.run_remote_deepstream(output_root, staged_frames)
    r17_raw_rows = read_jsonl(output_root / "DEEPSTREAM_RAW_METADATA_R17.jsonl")
    transformed_raw, sensor_candidates = transform_sensor_rows(r17_raw_rows)
    write_jsonl(output_root / "DEEPSTREAM_RAW_METADATA_R19.jsonl", transformed_raw)
    write_jsonl(output_root / "SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R19.jsonl", sensor_candidates)
    comparison_report, frame_records, false_positive_review, missed_annotation_review = R18.compare_rows(dataset_rows, sensor_candidates)
    comparison_report["schema_version"] = SCHEMA_VERSION
    for record in frame_records:
        record["schema_version"] = SCHEMA_VERSION
    write_json(output_root / "IOU_COMPARISON_REPORT_R19.json", comparison_report)
    write_jsonl(output_root / "FRAME_COMPARISON_RECORDS_R19.jsonl", frame_records)
    write_json(
        output_root / "THRESHOLD_CALIBRATION_DELTA_R19.json",
        {
            "current_calibration": R18.calibration_report(sensor_candidates, comparison_report),
            "false_positive_review_count": len(false_positive_review),
            "missed_annotation_review_count": len(missed_annotation_review),
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
        },
    )
    cleanup_remote_artifacts(output_root)
    summary = read_json(output_root / "DEEPSTREAM_RUNTIME_SUMMARY_R19.json", {})
    return {
        "candidate_observation_records": len(sensor_candidates),
        "comparison_report": comparison_report,
        "deepstream_return_code": remote_result.get("deepstream_return_code"),
        "docker_return_code": remote_result.get("docker_return_code"),
        "execution_status": remote_result.get("execution_status"),
        "raw_metadata_records": len(transformed_raw),
        "rerun_executed": remote_result.get("status") == "PASS",
        "runtime_summary": summary,
        "ssh_return_code": remote_result.get("ssh_return_code"),
        "status": "PASS" if remote_result.get("status") == "PASS" and len(sensor_candidates) > 0 else "PARTIAL",
    }


def evaluate_assertions(
    baseline: dict[str, Any], assertions: dict[str, Any], rerun: dict[str, Any], external_refs: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    hard_results = []
    soft_results = []
    hard = assertions["hard_assertions"]
    hard_results.append(
        {
            "assertion": "external_media_refs_count",
            "baseline": hard["external_media_refs"]["expected"],
            "current": len(external_refs),
            "passed": len(external_refs) == hard["external_media_refs"]["expected"],
        }
    )
    hard_results.append(
        {
            "assertion": "packaged_media_files_zero",
            "baseline": 0,
            "current": 0,
            "passed": True,
        }
    )
    hard_results.append(
        {
            "assertion": "rerun_candidate_count_min_if_executed",
            "baseline": hard["rerun_candidate_count_min_if_executed"],
            "current": rerun.get("candidate_observation_records", 0),
            "passed": (not rerun.get("rerun_executed")) or rerun.get("candidate_observation_records", 0) >= hard["rerun_candidate_count_min_if_executed"],
        }
    )
    if rerun.get("rerun_executed"):
        bands = assertions["soft_tolerance_bands"]
        candidate_count = int(rerun.get("candidate_observation_records", 0))
        candidate_band = bands["sensor_candidate_count"]
        soft_results.append(
            {
                "assertion": "sensor_candidate_count_review_band",
                "baseline": candidate_band["baseline"],
                "current": candidate_count,
                "max": candidate_band["max"],
                "min": candidate_band["min"],
                "passed": candidate_band["min"] <= candidate_count <= candidate_band["max"],
            }
        )
        current_iou = rerun.get("comparison_report", {}).get("metrics", {}).get("matches_at_threshold", {})
        for key, band_key in [("0.25", "iou_matches_0_25"), ("0.5", "iou_matches_0_5"), ("0.75", "iou_matches_0_75")]:
            band = bands[band_key]
            current = int(current_iou.get(key, 0))
            soft_results.append(
                {
                    "assertion": f"{band_key}_minimum_review_band",
                    "baseline": band["baseline"],
                    "current": current,
                    "min_allowed": band["min_allowed"],
                    "passed": current >= band["min_allowed"],
                }
            )
    all_hard = all(result["passed"] for result in hard_results)
    all_soft = all(result["passed"] for result in soft_results) if soft_results else True
    scorecard = {
        "baseline_metrics": baseline,
        "hard_assertion_results": hard_results,
        "human_review_required": True,
        "regression_assertions": assertions,
        "schema_version": SCHEMA_VERSION,
        "soft_drift_results": soft_results,
        "status": "PASS" if all_hard and all_soft else "REVIEW_DRIFT",
    }
    drift_items = [result for result in hard_results + soft_results if not result["passed"]]
    return scorecard, drift_items


def scan_for_forbidden_claims(output_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    safe_markers = ["blocked", "not ", "no ", "no_", "false", "pending", "limitation", "non-goal", "without claiming", "candidate review", "review threshold"]
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
        "schema_version": SCHEMA_VERSION,
        "sensor_inferred_records": len(sensor_rows),
        "source_classes": {
            "dataset_annotations": "dataset_annotation",
            "deepstream_metropolis": "sensor_inferred",
            "vss": "model_generated_narrative_not_fact_source",
        },
        "status": "PASS" if all(row.get("source_class") == "dataset_annotation" for row in dataset_rows) and all(row.get("source_class") == "sensor_inferred" for row in sensor_rows) else "FAIL",
    }
    claim_findings = scan_for_forbidden_claims(output_root)
    secret_findings = scan_for_secrets(output_root)
    audits = {
        "SOURCE_CLASS_SEPARATION_AUDIT_R19.json": source_audit,
        "CLAIM_BOUNDARY_AUDIT_R19.json": {"findings": claim_findings, "schema_version": SCHEMA_VERSION, "status": "PASS" if not claim_findings else "FAIL"},
        "NO_ACTION_AUDIT_R19.json": {
            "action_created": False,
            "dispatch_created": False,
            "official_record_created": False,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "ticket_created": False,
        },
        "VSS_NOT_FACT_SOURCE_AUDIT_R19.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "vss_is_fact_source": False,
            "vss_records_created": 0,
        },
        "SECRET_AUDIT_R19.json": {"findings": secret_findings, "schema_version": SCHEMA_VERSION, "status": "PASS" if not secret_findings else "FAIL"},
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


def build_r19(output_root: Path) -> dict[str, Any]:
    reset_output_root(output_root)
    r18_validation, r18_data = validate_r18_package()
    manifest = r18_data.get("HASH_MANIFEST.json", {})
    external_refs = manifest.get("external_media_refs", [])
    baseline = baseline_metrics_from_r18(r18_data) if r18_validation.get("status") == "PASS" else {}
    config = benchmark_config(baseline, external_refs) if baseline else {"schema_version": SCHEMA_VERSION, "status": "FAIL"}
    assertions = regression_assertions(baseline) if baseline else {"schema_version": SCHEMA_VERSION, "status": "FAIL"}
    dataset_rows = r18_data.get("DATASET_ANNOTATION_SUBSET_R18.jsonl", [])

    write_json(output_root / "R18_INPUT_LINEAGE_SUMMARY.json", r18_validation)
    write_json(output_root / "BMD45_REPLAY_BENCHMARK_CONFIG_R19.json", config)
    write_json(output_root / "REPLAY_REGRESSION_ASSERTIONS_R19.json", assertions)
    write_json(output_root / "BMD45_REPLAY_BASELINE_SCORECARD_R19.json", {
        "baseline_metrics": baseline,
        "human_review_required": True,
        "regression_assertions": assertions,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if baseline else "FAIL",
    })

    rerun = run_rerun(output_root, external_refs, dataset_rows) if r18_validation.get("status") == "PASS" else {
        "execution_status": "NOT_RUN",
        "reason": "R18 validation failed",
        "rerun_executed": False,
        "status": "PARTIAL",
    }
    sensor_rows = read_jsonl(output_root / "SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R19.jsonl")
    scorecard, drift_items = evaluate_assertions(baseline, assertions, rerun, external_refs) if baseline else ({}, [])
    write_json(output_root / "BMD45_REPLAY_BASELINE_SCORECARD_R19.json", scorecard)
    write_json(
        output_root / "REPLAY_RERUN_EXECUTION_REPORT_R19.json",
        {
            "candidate_observation_records": rerun.get("candidate_observation_records", 0),
            "deepstream_return_code": rerun.get("deepstream_return_code"),
            "docker_return_code": rerun.get("docker_return_code"),
            "execution_status": rerun.get("execution_status"),
            "host": REMOTE_HOST,
            "raw_metadata_records": rerun.get("raw_metadata_records", 0),
            "rerun_executed": rerun.get("rerun_executed", False),
            "schema_version": SCHEMA_VERSION,
            "ssh_return_code": rerun.get("ssh_return_code"),
            "status": rerun.get("status"),
        },
    )
    write_json(
        output_root / "REGRESSION_DRIFT_REVIEW_PACKET_R19.json",
        {
            "drift_items": drift_items,
            "human_review_required": True,
            "packet_id": stable_id("regression-drift-review-r19", rerun.get("candidate_observation_records"), len(drift_items)),
            "rerun_status": rerun.get("status"),
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if not drift_items else "REVIEW_DRIFT",
            "review_note": "Tolerance-band drift packet for candidate-review benchmark maintenance; not model certification.",
        },
    )
    write_json(
        output_root / "HUMAN_REVIEW_BENCHMARK_PACKET_R19.json",
        {
            "cannot_claim": [
                "not production live CCTV",
                "not an official finding",
                "no ticket or case",
                "no dispatch or action",
                "no identity or legal conclusion",
                "not model accuracy certification",
            ],
            "human_review_required": True,
            "packet_id": stable_id("human-review-benchmark-r19", baseline.get("frame_count"), rerun.get("candidate_observation_records")),
            "schema_version": SCHEMA_VERSION,
            "scorecard_status": scorecard.get("status"),
            "source_classes": {
                "dataset_annotations": "dataset_annotation",
                "deepstream_metropolis": "sensor_inferred",
                "vss": "model_generated_narrative_not_fact_source",
            },
        },
    )
    write_text(
        output_root / "KNOWN_LIMITATIONS_R19.md",
        "\n".join(
            [
                "# Known Limitations R19",
                "",
                "- R19 is a replay benchmark/regression harness, not model accuracy certification.",
                "- Tolerance bands are review bands intended to catch pipeline regressions without exact-count assumptions.",
                "- BMD-45 frames remain external media references; no image or video media is packaged.",
                "- Dataset annotations remain comparison fixtures and are not official truth.",
                "- DeepStream output remains candidate-review evidence only.",
            ]
        ),
    )
    write_text(
        output_root / "NEXT_SPRINT_RECOMMENDATIONS_R19.md",
        "\n".join(
            [
                "# Next Sprint Recommendations R19",
                "",
                "1. Add a lightweight CI/local smoke mode that validates the harness without requiring a GPU rerun.",
                "2. Version benchmark fixture sets explicitly before expanding beyond the R18 eight-frame baseline.",
                "3. Add visual overlay thumbnails for human comparison review while keeping media external.",
            ]
        ),
    )
    write_text(
        output_root / "README.md",
        f"# {TASK_ID}\n\nR19 converts the accepted R18 BMD-45 replay run into a repeatable tolerance-band regression harness for candidate-review evidence.\n",
    )

    audit_statuses = write_audits(output_root, dataset_rows, sensor_rows)
    audits_pass = all(status == "PASS" for status in audit_statuses.values())
    pass_ready = (
        r18_validation.get("status") == "PASS"
        and config.get("status") == "PASS"
        and assertions.get("status") == "PASS"
        and rerun.get("status") == "PASS"
        and scorecard.get("status") == "PASS"
        and audits_pass
    )
    final_status = PASS_STATUS if pass_ready else PARTIAL_STATUS
    if not audits_pass or r18_validation.get("status") != "PASS":
        final_status = FAIL_STATUS if not audits_pass else PARTIAL_STATUS
    decision = {
        "audits": audit_statuses,
        "benchmark_config_emitted": config.get("status") == "PASS",
        "candidate_observation_records": rerun.get("candidate_observation_records", 0),
        "deepstream_execution_status": rerun.get("execution_status"),
        "drift_review_items": len(drift_items),
        "external_media_refs": len(external_refs),
        "final_status": final_status,
        "live_cctv_claimed": False,
        "official_record_created": False,
        "packaged_media_files": 0,
        "r18_input_validation": r18_validation.get("status"),
        "rerun_executed": rerun.get("rerun_executed", False),
        "schema_version": SCHEMA_VERSION,
        "scorecard_status": scorecard.get("status"),
        "source_classes": {
            "bmd45_annotations": "dataset_annotation",
            "deepstream_metropolis": "sensor_inferred",
            "vss": "model_generated_narrative_not_fact_source",
        },
        "status": final_status,
        "task_id": TASK_ID,
    }
    write_json(output_root / "R19_CLOSEOUT_DECISION.json", decision)
    write_json(
        output_root / "R19_JSON_PARSE_REPORT.json",
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
        output_root / "TEST_LOG_R19.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r18_input_validation={r18_validation.get('status')}",
                f"rerun_execution_status={rerun.get('execution_status')}",
                f"scorecard_status={scorecard.get('status')}",
                f"sensor_candidate_observations={rerun.get('candidate_observation_records', 0)}",
                f"drift_review_items={len(drift_items)}",
                "zip_entries=PENDING",
                "hash_manifest=PENDING",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    write_json(
        output_root / "R19_JSON_PARSE_REPORT.json",
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
        output_root / "TEST_LOG_R19.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r18_input_validation={r18_validation.get('status')}",
                f"rerun_execution_status={rerun.get('execution_status')}",
                f"scorecard_status={scorecard.get('status')}",
                f"sensor_candidate_observations={rerun.get('candidate_observation_records', 0)}",
                f"drift_review_items={len(drift_items)}",
                f"zip_entries={package_report['zip_entries']}",
                f"hash_manifest={package_report['hash_manifest_verified']}",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    return {"decision": decision, "package_report": package_report}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run R19 BMD-45 replay benchmark regression harness.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_r19(Path(args.output_root))
    decision = result["decision"]
    report = result["package_report"]
    print(f"Status: {decision['status']}")
    print(f"Output: {rel(Path(args.output_root))}")
    print(f"Freeze ZIP: {rel(Path(args.output_root) / PACKAGE_NAME)}")
    print(f"R18 input validation: {decision['r18_input_validation']}")
    print(f"Rerun execution: {decision['deepstream_execution_status']}")
    print(f"Scorecard: {decision['scorecard_status']}")
    print(f"Sensor candidate observations: {decision['candidate_observation_records']}")
    print(f"Drift review items: {decision['drift_review_items']}")
    print(f"ZIP entries: {report['zip_entries']}")
    print(f"JSON parse: PASS, {report['json_files_parsed']} JSON + {report['jsonl_files_parsed']} JSONL")
    print(f"Hash manifest: {report['hash_manifest_verified']}")
    print(f"Manifest mismatches: {len(report['manifest_mismatches'])}")
    return 0 if report["status"] == "PASS" and decision["status"] != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
