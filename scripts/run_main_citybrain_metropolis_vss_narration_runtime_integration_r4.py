#!/usr/bin/env python3
"""Run the R4 VSS narration runtime integration gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_NAME = "MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-INTEGRATION-R4"
SCHEMA_VERSION = "metropolis-vss-narration-runtime-integration-r4.v1"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_narration_runtime_integration_r4"
DEFAULT_R3_ZIP = (
    REPO_ROOT
    / "outputs"
    / "main_citybrain_metropolis_vss_vss_narration_runtime_dry_run_r3"
    / "METROPOLIS_VSS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_PACKAGE.zip"
)
PACKAGE_NAME = "METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_WITH_LIMITATIONS"
PARTIAL_NOT_CONFIGURED_STATUS = "PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NOT_CONFIGURED_R4_GUARDRAILS_READY"
PARTIAL_NO_USABLE_OUTPUT_STATUS = "PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_EXECUTED_NO_USABLE_OUTPUT_R4"
PARTIAL_TIMEOUT_STATUS = "PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_TIMEOUT_R4"
FAIL_BOUNDARY_STATUS = "FAIL_METROPOLIS_VSS_NARRATION_RUNTIME_BOUNDARY_VIOLATION_R4"
FAIL_SOURCE_CLASS_STATUS = "FAIL_METROPOLIS_VSS_NARRATION_RUNTIME_SOURCE_CLASS_DRIFT_R4"
FAIL_PACKAGE_STATUS = "FAIL_METROPOLIS_VSS_NARRATION_RUNTIME_PACKAGE_INVALID_R4"

R3_EXPECTED_STATUS = "PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_BLOCKED_GUARDRAILS_READY"
VISIBLE_LABEL = "Candidate observation\nVSS narration only\nHuman review required\nNot a finding\nNo action taken"

REQUIRED_R3_FILES = [
    "CHECK_NARRATION_SUFFICIENCY_REPORT_R3.json",
    "CLAIM_BOUNDARY_AUDIT_R3.json",
    "HASH_MANIFEST.json",
    "HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R3.json",
    "INPUT_R2_PACKAGE_VALIDATION_R3.json",
    "JSON_PARSE_REPORT_R3.json",
    "MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R3.json",
    "METROPOLIS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_CLOSEOUT_DECISION.json",
    "METROPOLIS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_DECISION.json",
    "NO_ACTION_AUDIT_R3.json",
    "SECRET_AUDIT_R3.json",
    "SOURCE_CLASS_SEPARATION_AUDIT_R3.json",
    "VSS_INPUT_PACKET_R3.json",
    "VSS_NARRATION_GUARDRAIL_REPORT_R3.json",
    "VSS_NARRATION_OUTPUT_SAMPLE_R3.jsonl",
    "VSS_PROSE_VS_DETECTION_CONFLICT_AUDIT_R3.json",
    "VSS_RUNTIME_DRY_RUN_REPORT_R3.json",
]

FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    ("confirmed_violation", r"\b(confirmed violation|violation confirmed|illegal activity|offence|offense)\b"),
    ("legal_or_certified_finding", r"\b(legal finding|certified finding|finding of violation|legally confirmed|guilty)\b"),
    ("official_case_or_ticket", r"\b(ticket created|case created|official case|citation issued|fine issued)\b"),
    ("identity_or_biometric_inference", r"\b(identified person|person identified|suspect|offender|biometric|identity match)\b"),
    ("face_or_license_plate_recognition", r"\b(face recognized|face recognition|license plate|licence plate|plate number|plate recognized)\b"),
    ("dispatch_routing_control_enforcement", r"\b(dispatch|route responders|routing command|traffic control|enforcement action|enforce)\b"),
    ("alert_as_command", r"\b(alert operator to act|send alert|alert sent|operator must act)\b"),
    ("automated_action", r"\b(automated action|auto action|automatically ticket|automatically dispatch)\b"),
    ("production_monitoring_or_live_cctv_claim", r"\b(live cctv|production monitoring|live monitoring|real-time surveillance)\b"),
    ("vss_as_sensor_or_fact_source", r"\b(vss sensor|vss detected|vss confirms|vss proves|fact source|source of truth)\b"),
    ("unsupported_wall_clock_timestamp", r"\b20\d\d-\d\d-\d\d[t ][0-2]\d:[0-5]\d\b|\b\d{1,2}:\d{2}\s?(am|pm)\b"),
]

SECRET_PATTERNS: list[tuple[str, str]] = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("generic_api_key", r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*[A-Za-z0-9_\-]{12,}"),
    ("bearer_token", r"(?i)\bbearer\s+[A-Za-z0-9_\-.]{20,}"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}:{sha256_bytes(raw)[:24]}"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_jsonl_text(text: str) -> list[Any]:
    rows = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSONL parse failed on line {lineno}: {exc}") from exc
    return rows


def reset_output_root(output_root: Path) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def read_zip_json(zf: zipfile.ZipFile, name: str) -> Any:
    return json.loads(zf.read(name).decode("utf-8"))


def read_zip_jsonl(zf: zipfile.ZipFile, name: str) -> list[Any]:
    return parse_jsonl_text(zf.read(name).decode("utf-8"))


def validate_r3_zip(r3_zip: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "r3_zip": str(r3_zip),
        "r3_zip_exists": r3_zip.exists(),
        "status": "FAIL",
        "zip_entries": 0,
        "required_files_present": False,
        "missing_required_files": [],
        "json_files_parsed": 0,
        "jsonl_files_parsed": 0,
        "json_parse_failures": [],
        "jsonl_parse_failures": [],
        "hash_manifest": {
            "status": "NOT_RUN",
            "verified": 0,
            "manifest_file_count": 0,
            "mismatches": [],
            "missing": [],
        },
    }
    if not r3_zip.exists():
        result["failure_reason"] = "R3 package zip not found."
        return result

    result["r3_zip_sha256"] = sha256_file(r3_zip)
    parsed_json: dict[str, Any] = {}
    parsed_jsonl: dict[str, list[Any]] = {}

    try:
        with zipfile.ZipFile(r3_zip, "r") as zf:
            names = zf.namelist()
            result["zip_entries"] = len(names)
            missing_required = [name for name in REQUIRED_R3_FILES if name not in names]
            result["missing_required_files"] = missing_required
            result["required_files_present"] = not missing_required

            for name in names:
                lower = name.lower()
                if lower.endswith(".json"):
                    try:
                        parsed_json[name] = read_zip_json(zf, name)
                        result["json_files_parsed"] += 1
                    except Exception as exc:  # noqa: BLE001
                        result["json_parse_failures"].append({"file": name, "error": str(exc)})
                elif lower.endswith(".jsonl"):
                    try:
                        parsed_jsonl[name] = read_zip_jsonl(zf, name)
                        result["jsonl_files_parsed"] += 1
                    except Exception as exc:  # noqa: BLE001
                        result["jsonl_parse_failures"].append({"file": name, "error": str(exc)})

            if "HASH_MANIFEST.json" in names:
                manifest = parsed_json.get("HASH_MANIFEST.json") or read_zip_json(zf, "HASH_MANIFEST.json")
                files = manifest.get("files", [])
                result["hash_manifest"]["manifest_file_count"] = len(files)
                for item in files:
                    file_name = item.get("file") or item.get("path")
                    if not file_name:
                        result["hash_manifest"]["missing"].append("<blank manifest path>")
                        continue
                    if file_name not in names:
                        result["hash_manifest"]["missing"].append(file_name)
                        continue
                    actual = sha256_bytes(zf.read(file_name))
                    if actual != item.get("sha256"):
                        result["hash_manifest"]["mismatches"].append(
                            {"file": file_name, "expected": item.get("sha256"), "actual": actual}
                        )
                    else:
                        result["hash_manifest"]["verified"] += 1
                result["hash_manifest"]["status"] = (
                    "PASS"
                    if not result["hash_manifest"]["missing"] and not result["hash_manifest"]["mismatches"]
                    else "FAIL"
                )
    except zipfile.BadZipFile as exc:
        result["failure_reason"] = f"Bad zip file: {exc}"
        return result

    closeout = parsed_json.get("METROPOLIS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_CLOSEOUT_DECISION.json", {})
    runtime_report = parsed_json.get("VSS_RUNTIME_DRY_RUN_REPORT_R3.json", {})
    input_r2 = parsed_json.get("INPUT_R2_PACKAGE_VALIDATION_R3.json", {})
    evidence = parsed_json.get("MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R3.json", {})
    human_packet = parsed_json.get("HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R3.json", {})

    truth_ok = (
        closeout.get("status") == R3_EXPECTED_STATUS
        and closeout.get("structured_detection_source_class") == "sensor_inferred"
        and closeout.get("vss_output_source_class") == "model_generated_narrative"
        and closeout.get("vss_is_fact_source") is False
        and closeout.get("candidate_event_modified_by_vss") is False
        and closeout.get("candidate_observation_count") == 24
        and input_r2.get("status") == "PASS"
        and evidence.get("source_class") == "sensor_inferred"
        and human_packet.get("human_review_required") is True
    )
    result["r3_closeout_status"] = closeout.get("status")
    result["r3_runtime_status"] = runtime_report.get("status")
    result["r3_runtime_blocked_reason"] = runtime_report.get("blocked_reason")
    result["r2_validation_status"] = input_r2.get("status")
    result["r2_scope"] = input_r2.get("r2_scope", {})
    result["r2_candidate_observations"] = closeout.get("candidate_observation_count")
    result["r2_candidate_events"] = 1 if closeout.get("candidate_event_ref") else 0
    result["r3_preserved_r2_truth"] = truth_ok
    result["vss_runtime_attempted"] = bool(runtime_report.get("vss_runtime_attempted"))
    result["vss_runtime_executed"] = bool(runtime_report.get("vss_runtime_executed"))
    result["vss_output_records"] = len(parsed_jsonl.get("VSS_NARRATION_OUTPUT_SAMPLE_R3.jsonl", []))
    result["_parsed_json"] = parsed_json
    result["_parsed_jsonl"] = parsed_jsonl
    result["status"] = (
        "PASS"
        if result["required_files_present"]
        and not result["json_parse_failures"]
        and not result["jsonl_parse_failures"]
        and result["hash_manifest"]["status"] == "PASS"
        and truth_ok
        else "FAIL"
    )
    return result


def safe_validation(validation: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in validation.items() if not k.startswith("_")}


def build_context(validation: dict[str, Any]) -> dict[str, Any]:
    parsed = validation.get("_parsed_json", {})
    closeout = parsed.get("METROPOLIS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_CLOSEOUT_DECISION.json", {})
    evidence = parsed.get("MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R3.json", {})
    human_packet = parsed.get("HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R3.json", {})
    input_r2 = parsed.get("INPUT_R2_PACKAGE_VALIDATION_R3.json", {})
    scope = input_r2.get("r2_scope", {})
    return {
        "media_source": closeout.get("media_source") or scope.get("media_source"),
        "zone": closeout.get("zone") or scope.get("zone"),
        "detection_class": closeout.get("detection_class") or scope.get("detection_class"),
        "class_label": closeout.get("class_label") or scope.get("class_label"),
        "object_metadata_count": closeout.get("object_metadata_count", 24),
        "candidate_observation_count": closeout.get("candidate_observation_count", 24),
        "candidate_event_ref": closeout.get("candidate_event_ref")
        or (evidence.get("candidate_event_refs") or [None])[0],
        "evidence_bundle_ref": closeout.get("evidence_bundle_ref") or evidence.get("bundle_id"),
        "candidate_observation_refs": evidence.get("candidate_observation_refs")
        or human_packet.get("candidate_observation_refs", []),
        "object_metadata_refs": evidence.get("object_metadata_refs") or human_packet.get("object_metadata_refs", []),
        "structured_detection_source": closeout.get(
            "structured_detection_source", "DeepStream/Metropolis R2 object metadata"
        ),
        "structured_detection_source_class": closeout.get("structured_detection_source_class", "sensor_inferred"),
        "vss_output_source_class": "model_generated_narrative",
        "vss_is_fact_source": False,
        "candidate_label": VISIBLE_LABEL,
        "raw_r3_evidence_bundle": evidence,
        "raw_r3_human_packet": human_packet,
        "raw_r3_closeout": closeout,
    }


def build_input_packet(ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "created_at": utc_now(),
        "input_scope": {
            "one_r3_package": True,
            "one_r2_evidence_bundle": True,
            "one_candidate_event": True,
            "one_vss_runtime_adapter": True,
        },
        "media_ref": ctx["media_source"],
        "candidate_event_ref": ctx["candidate_event_ref"],
        "evidence_bundle_ref": ctx["evidence_bundle_ref"],
        "r2_object_metadata_summary": {
            "source": ctx["structured_detection_source"],
            "source_class": ctx["structured_detection_source_class"],
            "zone": ctx["zone"],
            "detection_class": ctx["detection_class"],
            "class_label": ctx["class_label"],
            "object_metadata_count": ctx["object_metadata_count"],
            "candidate_observation_count": ctx["candidate_observation_count"],
        },
        "candidate_observation_refs": ctx["candidate_observation_refs"],
        "object_metadata_refs_sample": ctx["object_metadata_refs"][:5],
        "candidate_label": VISIBLE_LABEL,
        "source_class_rules": {
            "structured_detection_source_class": "sensor_inferred",
            "vss_output_source_class": "model_generated_narrative",
            "vss_is_fact_source": False,
            "candidate_event_modified_by_vss": False,
        },
        "human_review_required": True,
        "official_record_created": False,
        "no_action_taken": True,
        "forbidden_claims": [
            "confirmed violation",
            "legal or certified finding",
            "official case or ticket",
            "identity, biometric, face, or license-plate recognition",
            "dispatch, routing, control, enforcement, alert-command, or automated action",
            "production monitoring or live CCTV claim",
            "VSS as sensor, official record, or fact source",
            "new object detections not present in R2",
            "object counts that override R2 metadata",
            "wall-clock timestamps not present in R2",
        ],
    }


def runtime_config(args: argparse.Namespace) -> dict[str, Any]:
    env_timeout = os.environ.get("CITYBRAIN_VSS_TIMEOUT_SEC")
    timeout = args.timeout_sec
    if env_timeout and args.timeout_sec == 120:
        try:
            timeout = int(env_timeout)
        except ValueError:
            timeout = args.timeout_sec
    timeout = max(1, min(int(timeout), 3600))
    command = args.vss_command or os.environ.get("CITYBRAIN_VSS_COMMAND")
    endpoint = args.vss_endpoint or os.environ.get("CITYBRAIN_VSS_ENDPOINT")
    command_source = "cli" if args.vss_command else ("env" if os.environ.get("CITYBRAIN_VSS_COMMAND") else "none")
    endpoint_source = "cli" if args.vss_endpoint else ("env" if os.environ.get("CITYBRAIN_VSS_ENDPOINT") else "none")
    if args.dry_run:
        mode = "dry_run"
    elif command:
        mode = "command"
    elif endpoint:
        mode = "endpoint"
    else:
        mode = "not_configured"
    return {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "runtime_mode": mode,
        "runtime_configured": mode in {"command", "endpoint"},
        "timeout_sec": timeout,
        "redacted": True,
        "command_source": command_source,
        "endpoint_source": endpoint_source,
        "notes": ["Runtime command/endpoint values are redacted from package outputs."],
        "_command": command,
        "_endpoint": endpoint,
    }


def safe_config(config: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in config.items() if not k.startswith("_")}


def execute_runtime(config: dict[str, Any], input_packet_path: Path, output_root: Path) -> dict[str, Any]:
    mode = config["runtime_mode"]
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "runtime_ref": stable_id("vss-runtime-r4", {"mode": mode, "input": rel(input_packet_path)}),
        "runtime_mode": mode,
        "runtime_status": "NOT_CONFIGURED",
        "vss_runtime_attempted": False,
        "vss_runtime_executed": False,
        "timeout_sec": config["timeout_sec"],
        "input_packet_ref": rel(input_packet_path),
        "stdout_ref": None,
        "stderr_ref": None,
        "response_body_ref": None,
        "returncode_or_http_status": None,
        "runtime_endpoint_or_command_redacted": True,
        "raw_output_text": "",
    }
    if mode == "dry_run":
        report.update(
            {
                "runtime_status": "DRY_RUN",
                "blocked_reason": "Dry-run requested; runtime adapter validated without execution.",
            }
        )
        return report
    if mode == "not_configured":
        report["blocked_reason"] = (
            "No --vss-command, --vss-endpoint, CITYBRAIN_VSS_COMMAND, or CITYBRAIN_VSS_ENDPOINT was configured."
        )
        return report
    if mode == "command":
        report["vss_runtime_attempted"] = True
        stdout_path = output_root / "VSS_RUNTIME_STDOUT_R4.txt"
        stderr_path = output_root / "VSS_RUNTIME_STDERR_R4.txt"
        env = os.environ.copy()
        env["CITYBRAIN_VSS_INPUT_PACKET"] = str(input_packet_path)
        try:
            completed = subprocess.run(
                config["_command"],
                shell=True,
                text=True,
                capture_output=True,
                timeout=config["timeout_sec"],
                env=env,
            )
            write_text(stdout_path, completed.stdout or "")
            write_text(stderr_path, completed.stderr or "")
            report.update(
                {
                    "stdout_ref": rel(stdout_path),
                    "stderr_ref": rel(stderr_path),
                    "returncode_or_http_status": completed.returncode,
                    "runtime_status": "EXECUTED" if completed.returncode == 0 else "FAILED",
                    "vss_runtime_executed": completed.returncode == 0,
                    "raw_output_text": completed.stdout or "",
                }
            )
        except subprocess.TimeoutExpired as exc:
            write_text(stdout_path, exc.stdout or "")
            write_text(stderr_path, exc.stderr or "Runtime command timed out.")
            report.update(
                {
                    "stdout_ref": rel(stdout_path),
                    "stderr_ref": rel(stderr_path),
                    "runtime_status": "TIMEOUT",
                    "blocked_reason": "Runtime command timed out.",
                    "raw_output_text": exc.stdout or "",
                }
            )
        return report
    if mode == "endpoint":
        report["vss_runtime_attempted"] = True
        response_path = output_root / "VSS_RUNTIME_RESPONSE_BODY_R4.txt"
        packet = json.loads(input_packet_path.read_text(encoding="utf-8"))
        body = json.dumps(packet).encode("utf-8")
        request = urllib.request.Request(
            config["_endpoint"],
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=config["timeout_sec"]) as response:  # noqa: S310
                response_body = response.read().decode("utf-8", errors="replace")
                write_text(response_path, response_body)
                status_code = int(response.status)
                report.update(
                    {
                        "response_body_ref": rel(response_path),
                        "returncode_or_http_status": status_code,
                        "runtime_status": "EXECUTED" if 200 <= status_code < 300 else "FAILED",
                        "vss_runtime_executed": 200 <= status_code < 300,
                        "raw_output_text": response_body,
                    }
                )
        except TimeoutError:
            write_text(response_path, "")
            report.update(
                {
                    "response_body_ref": rel(response_path),
                    "runtime_status": "TIMEOUT",
                    "blocked_reason": "Runtime endpoint timed out.",
                }
            )
        except urllib.error.URLError as exc:
            write_text(response_path, str(exc))
            report.update(
                {
                    "response_body_ref": rel(response_path),
                    "runtime_status": "FAILED",
                    "blocked_reason": f"Runtime endpoint failed: {exc}",
                }
            )
        return report
    report["runtime_status"] = "FAILED"
    report["blocked_reason"] = f"Unsupported runtime mode: {mode}"
    return report


def coerce_output_rows(raw_text: str) -> tuple[list[Any], str]:
    text = (raw_text or "").strip()
    if not text:
        return [], "empty"
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed, "json_array"
        return [parsed], "json_object"
    except json.JSONDecodeError:
        pass
    try:
        rows = parse_jsonl_text(text)
        if rows:
            return rows, "jsonl"
    except ValueError:
        pass
    return [{"narration_text": text}], "plain_text"


def text_from_row(row: Any) -> str:
    if isinstance(row, str):
        return row
    if isinstance(row, dict):
        for key in ("narration_text", "generated_text", "text", "narration", "summary", "answer"):
            val = row.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def normalize_sidecars(
    runtime_report: dict[str, Any],
    ctx: dict[str, Any],
    max_records: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, source_format = coerce_output_rows(runtime_report.get("raw_output_text", ""))
    sidecars: list[dict[str, Any]] = []
    dropped = 0
    for idx, row in enumerate(rows[: max(0, max_records)], start=1):
        text = text_from_row(row)
        if not text:
            dropped += 1
            continue
        uncertainty_notes = []
        supported_refs = ctx["candidate_observation_refs"]
        if isinstance(row, dict):
            notes = row.get("uncertainty_notes") or row.get("uncertainties") or row.get("notes")
            if isinstance(notes, list):
                uncertainty_notes = [str(note) for note in notes]
            refs = row.get("supported_candidate_observation_refs")
            if isinstance(refs, list):
                supported_refs = [str(ref) for ref in refs if str(ref) in ctx["candidate_observation_refs"]]
        payload = {
            "idx": idx,
            "event": ctx["candidate_event_ref"],
            "bundle": ctx["evidence_bundle_ref"],
            "text": text,
        }
        sidecars.append(
            {
                "narration_id": stable_id("metropolis-vss-r4-narration", payload),
                "source_class": "model_generated_narrative",
                "input_candidate_event_ref": ctx["candidate_event_ref"],
                "input_evidence_bundle_ref": ctx["evidence_bundle_ref"],
                "supported_candidate_observation_refs": supported_refs,
                "narration_text": text,
                "uncertainty_notes": uncertainty_notes,
                "claim_boundary_label": VISIBLE_LABEL,
                "vss_runtime_ref": runtime_report["runtime_ref"],
                "runtime_mode": runtime_report["runtime_mode"],
                "created_at": utc_now(),
                "guardrail_status": "NEEDS_REVIEW",
                "unsupported_claims": [],
                "conflict_flags": [],
                "human_review_required": True,
                "official_record_created": False,
                "no_action_taken": True,
            }
        )
    if len(rows) > max_records:
        dropped += len(rows) - max_records
    report = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "input_format_detected": source_format,
        "raw_records_seen": len(rows),
        "max_narration_records": max_records,
        "normalized_records": len(sidecars),
        "dropped_records": dropped,
        "status": "PASS" if sidecars else "PARTIAL",
        "notes": [
            "VSS output is normalized as model_generated_narrative only.",
            "No narration is fabricated when runtime output is empty or runtime is not configured.",
        ],
    }
    return sidecars, report


def audit_sidecars(sidecars: list[dict[str, Any]], ctx: dict[str, Any]) -> dict[str, Any]:
    allowed_classes = {str(ctx.get("class_label", "")).lower(), "vehicle", "vehicles", "car", "cars"}
    unsupported_object_terms = ["person", "pedestrian", "bicycle", "road sign", "road_sign", "truck", "bus", "motorcycle"]
    allowed_counts = {int(ctx.get("object_metadata_count") or 0), int(ctx.get("candidate_observation_count") or 0)}
    unsupported_claims: list[dict[str, Any]] = []
    conflict_flags: list[dict[str, Any]] = []

    for sidecar in sidecars:
        text = sidecar.get("narration_text", "")
        lowered = text.lower()
        for family, pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                unsupported_claims.append({"narration_id": sidecar["narration_id"], "family": family})
        for term in unsupported_object_terms:
            if term in lowered and term not in allowed_classes:
                conflict_flags.append(
                    {
                        "narration_id": sidecar["narration_id"],
                        "family": "new_object_detection_not_in_r2",
                        "term": term,
                    }
                )
        count_matches = re.findall(r"\b\d+\b", text)
        for raw_num in count_matches:
            num = int(raw_num)
            if num > 1 and num not in allowed_counts:
                conflict_flags.append(
                    {
                        "narration_id": sidecar["narration_id"],
                        "family": "object_count_override",
                        "count": num,
                    }
                )
        if sidecar.get("source_class") != "model_generated_narrative":
            unsupported_claims.append({"narration_id": sidecar["narration_id"], "family": "source_class_drift"})
        if sidecar.get("official_record_created") is not False or sidecar.get("no_action_taken") is not True:
            unsupported_claims.append({"narration_id": sidecar["narration_id"], "family": "action_or_record_drift"})

    status = "PASS" if not unsupported_claims and not conflict_flags else "FAIL"
    for sidecar in sidecars:
        sidecar_claims = [c["family"] for c in unsupported_claims if c["narration_id"] == sidecar["narration_id"]]
        sidecar_flags = [c["family"] for c in conflict_flags if c["narration_id"] == sidecar["narration_id"]]
        sidecar["unsupported_claims"] = sidecar_claims
        sidecar["conflict_flags"] = sidecar_flags
        sidecar["guardrail_status"] = "PASS" if not sidecar_claims and not sidecar_flags else "FAIL"

    return {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": status,
        "vss_narration_records": len(sidecars),
        "unsupported_claims": unsupported_claims,
        "conflict_flags": conflict_flags,
        "checks": [
            {"check": "source_class_model_generated_narrative", "status": "PASS" if status == "PASS" else "FAIL"},
            {"check": "no_vss_fact_source_claim", "status": "PASS" if not unsupported_claims else "FAIL"},
            {"check": "no_new_object_classes_added_by_vss", "status": "PASS" if not conflict_flags else "FAIL"},
            {"check": "no_object_count_override", "status": "PASS" if not conflict_flags else "FAIL"},
            {"check": "no_identity_legal_action_or_live_claims", "status": "PASS" if not unsupported_claims else "FAIL"},
        ],
        "candidate_event_modified_by_vss": False,
        "human_review_required": True,
        "official_record_created": False,
        "no_action_taken": True,
        "vss_is_fact_source": False,
    }


def write_audit_files(
    output_root: Path,
    sidecars: list[dict[str, Any]],
    ctx: dict[str, Any],
    runtime_report: dict[str, Any],
    guardrail_report: dict[str, Any],
) -> dict[str, str]:
    conflict_status = "PASS" if not guardrail_report["conflict_flags"] else "FAIL"
    write_json(
        output_root / "VSS_PROSE_VS_DETECTION_CONFLICT_AUDIT_R4.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": conflict_status,
            "r2_class_label": ctx["class_label"],
            "r2_object_metadata_count": ctx["object_metadata_count"],
            "vss_narration_records": len(sidecars),
            "conflict_flags": guardrail_report["conflict_flags"],
        },
    )

    source_status = (
        "PASS"
        if ctx["structured_detection_source_class"] == "sensor_inferred"
        and all(s.get("source_class") == "model_generated_narrative" for s in sidecars)
        else "FAIL"
    )
    write_json(
        output_root / "SOURCE_CLASS_SEPARATION_AUDIT_R4.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": source_status,
            "structured_detection_source_class": "sensor_inferred",
            "vss_output_source_class": "model_generated_narrative",
            "vss_is_fact_source": False,
            "vss_narration_records": len(sidecars),
        },
    )

    claim_status = "PASS" if not guardrail_report["unsupported_claims"] else "FAIL"
    write_json(
        output_root / "CLAIM_BOUNDARY_AUDIT_R4.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": claim_status,
            "candidate_label": VISIBLE_LABEL,
            "unsupported_claims": guardrail_report["unsupported_claims"],
            "human_review_required": True,
            "not_a_finding": True,
        },
    )

    no_action_status = (
        "PASS"
        if all(s.get("no_action_taken") is True and s.get("official_record_created") is False for s in sidecars)
        else "FAIL"
    )
    write_json(
        output_root / "NO_ACTION_AUDIT_R4.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": no_action_status,
            "no_action_taken": True,
            "official_record_created": False,
            "candidate_event_modified_by_vss": False,
        },
    )

    check_status = "PASS" if sidecars and guardrail_report["status"] == "PASS" else "PARTIAL"
    if guardrail_report["status"] == "FAIL":
        check_status = "FAIL"
    write_json(
        output_root / "CHECK_NARRATION_SUFFICIENCY_REPORT_R4.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": check_status,
            "dimension_results": [
                {"dimension": "R3 package validation", "status": "PASS", "value": "R3 partial guardrails ready"},
                {
                    "dimension": "VSS runtime availability",
                    "status": "PASS" if runtime_report["runtime_status"] == "EXECUTED" else "PARTIAL",
                    "value": runtime_report["runtime_status"],
                },
                {
                    "dimension": "usable narration sidecars",
                    "status": "PASS" if sidecars else "PARTIAL",
                    "value": len(sidecars),
                },
                {
                    "dimension": "source-class separation",
                    "status": source_status,
                    "value": "sensor_inferred detections; model_generated_narrative VSS",
                },
                {
                    "dimension": "claim boundary",
                    "status": claim_status,
                    "value": guardrail_report["unsupported_claims"],
                },
                {
                    "dimension": "human-review stop",
                    "status": "PASS",
                    "value": "human_review_required=true",
                },
                {
                    "dimension": "no-action/no-official-record boundary",
                    "status": no_action_status,
                    "value": "no_action_taken=true; official_record_created=false",
                },
            ],
        },
    )
    return {
        "source_class": source_status,
        "claim_boundary": claim_status,
        "no_action": no_action_status,
        "vss_guardrail": guardrail_report["status"],
        "prose_vs_detection_conflict": conflict_status,
        "check_narration_sufficiency": check_status,
    }


def write_review_artifacts(
    output_root: Path,
    sidecars: list[dict[str, Any]],
    ctx: dict[str, Any],
) -> None:
    bundle = dict(ctx["raw_r3_evidence_bundle"])
    bundle.update(
        {
            "schema_version": SCHEMA_VERSION,
            "candidate_label": VISIBLE_LABEL,
            "vss_narration_status": "attached" if sidecars else "not_configured_not_attached",
            "vss_narration_sidecar_refs": [s["narration_id"] for s in sidecars],
            "vss_narration_sidecar_ref": sidecars[0]["narration_id"] if sidecars else None,
            "vss_output_source_class": "model_generated_narrative",
            "vss_is_fact_source": False,
            "candidate_event_modified_by_vss": False,
            "human_review_required": True,
            "official_record_created": False,
            "no_action_taken": True,
        }
    )
    write_json(output_root / "MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R4.json", bundle)

    packet = dict(ctx["raw_r3_human_packet"])
    packet.update(
        {
            "schema_version": SCHEMA_VERSION,
            "candidate_label": VISIBLE_LABEL,
            "review_prompt": (
                "Review the R2 structured vehicle-presence candidates. "
                "Treat any R4 VSS narration sidecar as model-generated review wording only, not as a fact source."
            ),
            "vss_narration_status": "attached" if sidecars else "not_configured_not_attached",
            "vss_narration_sidecar_refs": [s["narration_id"] for s in sidecars],
            "vss_narration_sidecar_ref": sidecars[0]["narration_id"] if sidecars else None,
            "human_review_required": True,
            "official_record_created": False,
            "no_action_taken": True,
            "status": "ready_for_human_review",
        }
    )
    write_json(output_root / "HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R4.json", packet)


def write_secret_audit(output_root: Path) -> str:
    findings: list[dict[str, str]] = []
    for path in output_root.iterdir():
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                findings.append({"file": path.name, "pattern": name})
    status = "PASS" if not findings else "FAIL"
    write_json(output_root / "SECRET_AUDIT_R4.json", {"status": status, "findings": findings})
    return status


def validate_json_outputs(output_root: Path) -> str:
    failures: list[dict[str, str]] = []
    json_count = 0
    jsonl_count = 0
    for path in sorted(output_root.iterdir()):
        if path.name == PACKAGE_NAME:
            continue
        if path.suffix.lower() == ".json":
            json_count += 1
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                failures.append({"file": path.name, "error": str(exc)})
        elif path.suffix.lower() == ".jsonl":
            jsonl_count += 1
            try:
                parse_jsonl_text(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                failures.append({"file": path.name, "error": str(exc)})
    status = "PASS" if not failures else "FAIL"
    write_json(
        output_root / "JSON_PARSE_REPORT_R4.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": status,
            "json_files_parsed": json_count,
            "jsonl_files_parsed": jsonl_count,
            "parse_failures": failures,
        },
    )
    return status


def write_hash_manifest(output_root: Path) -> str:
    files = []
    for path in sorted(output_root.iterdir(), key=lambda p: p.name):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", PACKAGE_NAME}:
            continue
        data = path.read_bytes()
        files.append({"file": path.name, "bytes": len(data), "sha256": sha256_bytes(data)})
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "algorithm": "sha256",
        "generated_at": utc_now(),
        "status": "PASS",
        "file_count": len(files),
        "files": files,
        "excludes": ["HASH_MANIFEST.json", PACKAGE_NAME],
    }
    write_json(output_root / "HASH_MANIFEST.json", manifest)
    return "PASS"


def decide_status(
    validation: dict[str, Any],
    runtime: dict[str, Any],
    sidecars: list[dict[str, Any]],
    audits: dict[str, str],
    json_status: str = "PENDING",
    hash_status: str = "PENDING",
) -> str:
    if validation.get("status") != "PASS":
        return FAIL_PACKAGE_STATUS
    if audits.get("source_class") == "FAIL":
        return FAIL_SOURCE_CLASS_STATUS
    if any(status == "FAIL" for status in audits.values()):
        return FAIL_BOUNDARY_STATUS
    if json_status == "FAIL" or hash_status == "FAIL":
        return FAIL_PACKAGE_STATUS
    if runtime["runtime_status"] == "TIMEOUT":
        return PARTIAL_TIMEOUT_STATUS
    if runtime["runtime_status"] in {"NOT_CONFIGURED", "DRY_RUN"}:
        return PARTIAL_NOT_CONFIGURED_STATUS
    if runtime["runtime_status"] == "EXECUTED" and not sidecars:
        return PARTIAL_NO_USABLE_OUTPUT_STATUS
    if runtime["runtime_status"] == "EXECUTED" and sidecars:
        return PASS_STATUS
    return PARTIAL_NO_USABLE_OUTPUT_STATUS


def write_decision(
    output_root: Path,
    status: str,
    validation: dict[str, Any],
    runtime: dict[str, Any],
    sidecars: list[dict[str, Any]],
    audits: dict[str, str],
    json_status: str = "PENDING",
    hash_status: str = "PENDING",
) -> None:
    decision = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": status,
        "runtime_status": runtime["runtime_status"],
        "vss_runtime_attempted": bool(runtime.get("vss_runtime_attempted")),
        "vss_runtime_executed": bool(runtime.get("vss_runtime_executed")),
        "vss_narration_records": len(sidecars),
        "structured_detection_source_class": "sensor_inferred",
        "vss_output_source_class": "model_generated_narrative",
        "vss_is_fact_source": False,
        "candidate_event_modified_by_vss": False,
        "human_review_required": True,
        "no_action_taken": True,
        "official_record_created": False,
        "audits": {**audits, "json_parse": json_status, "hash_manifest": hash_status},
        "input_r3_package_validation_status": validation.get("status"),
        "r3_closeout_status": validation.get("r3_closeout_status"),
        "r2_candidate_observations": validation.get("r2_candidate_observations"),
        "r2_candidate_events": validation.get("r2_candidate_events"),
        "limitations": [
            "R4 consumes one R3 package and one R2 candidate event only.",
            "DeepStream/Metropolis structured metadata remains the only sensor_inferred source.",
            "VSS narration is model_generated_narrative only and is not a fact source.",
            "No finding, identity, official record, ticket, dispatch, control, enforcement, alert-command, or automated action is created.",
            "R2 sample media remains bounded sample-media evidence, not live CCTV.",
        ],
        "validation_package_ref": PACKAGE_NAME,
    }
    write_json(output_root / "METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_DECISION.json", decision)
    write_json(output_root / "METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_CLOSEOUT_DECISION.json", decision)


def write_readme(output_root: Path, status: str, runtime: dict[str, Any], sidecars: list[dict[str, Any]]) -> None:
    text = f"""# Metropolis/VSS Narration Runtime Integration R4

Status: {status}

This package implements a bounded VSS narration runtime adapter over the R3 evidence context.
DeepStream/Metropolis object metadata remains `sensor_inferred`; VSS output is only
`model_generated_narrative` and is not a fact source.

Runtime status: {runtime["runtime_status"]}
VSS runtime attempted/executed: {str(runtime.get("vss_runtime_attempted")).lower()}/{str(runtime.get("vss_runtime_executed")).lower()}
VSS narration records emitted: {len(sidecars)}

Visible label:

```text
{VISIBLE_LABEL}
```

No official record was created and no action was taken.
"""
    write_text(output_root / "README.md", text)


def create_package_zip(output_root: Path) -> Path:
    zip_path = output_root / PACKAGE_NAME
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(output_root.iterdir(), key=lambda p: p.name):
            if path.is_file() and path.name != PACKAGE_NAME:
                zf.write(path, path.name)
    return zip_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-r3-zip", type=Path, default=DEFAULT_R3_ZIP)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--vss-command")
    parser.add_argument("--vss-endpoint")
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--max-narration-records", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    reset_output_root(output_root)

    validation = validate_r3_zip(args.input_r3_zip.resolve())
    validation_safe = safe_validation(validation)
    write_json(output_root / "INPUT_R3_PACKAGE_VALIDATION_R4.json", validation_safe)

    ctx = build_context(validation) if validation.get("status") == "PASS" else {
        "media_source": None,
        "zone": None,
        "detection_class": None,
        "class_label": None,
        "object_metadata_count": 0,
        "candidate_observation_count": 0,
        "candidate_event_ref": None,
        "evidence_bundle_ref": None,
        "candidate_observation_refs": [],
        "object_metadata_refs": [],
        "structured_detection_source": "DeepStream/Metropolis R2 object metadata",
        "structured_detection_source_class": "sensor_inferred",
        "raw_r3_evidence_bundle": {},
        "raw_r3_human_packet": {},
    }
    input_packet = build_input_packet(ctx)
    write_json(output_root / "VSS_INPUT_PACKET_R4.json", input_packet)

    config = runtime_config(args)
    write_json(output_root / "VSS_RUNTIME_ADAPTER_CONFIG_R4.json", safe_config(config))
    runtime = execute_runtime(config, output_root / "VSS_INPUT_PACKET_R4.json", output_root)
    raw_output = runtime.pop("raw_output_text", "")
    runtime_report = dict(runtime)
    write_json(output_root / "VSS_RUNTIME_EXECUTION_REPORT_R4.json", runtime_report)
    runtime["raw_output_text"] = raw_output

    sidecars, normalization_report = normalize_sidecars(runtime, ctx, args.max_narration_records)
    guardrail_report = audit_sidecars(sidecars, ctx)
    normalization_report["guardrail_status"] = guardrail_report["status"]
    write_json(output_root / "VSS_NARRATION_NORMALIZATION_REPORT_R4.json", normalization_report)
    write_json(output_root / "VSS_NARRATION_GUARDRAIL_REPORT_R4.json", guardrail_report)
    write_jsonl(output_root / "VSS_NARRATION_SIDECARS_R4.jsonl", sidecars)

    audits = write_audit_files(output_root, sidecars, ctx, runtime_report, guardrail_report)
    write_review_artifacts(output_root, sidecars, ctx)
    secret_status = write_secret_audit(output_root)
    audits["secret"] = secret_status

    initial_status = decide_status(validation, runtime_report, sidecars, audits)
    write_decision(output_root, initial_status, validation_safe, runtime_report, sidecars, audits)
    write_readme(output_root, initial_status, runtime_report, sidecars)
    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    final_status = decide_status(validation, runtime_report, sidecars, audits, json_status, hash_status)
    write_decision(output_root, final_status, validation_safe, runtime_report, sidecars, audits, json_status, hash_status)
    write_readme(output_root, final_status, runtime_report, sidecars)
    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    create_package_zip(output_root)

    print(f"Final status: {final_status}")
    print(f"Runner: {rel(Path(__file__).resolve())}")
    print(f"Output root: {rel(output_root)}")
    print(f"Freeze ZIP: {rel(output_root / PACKAGE_NAME)}")
    print(
        "VSS runtime attempted/executed: "
        f"{str(runtime_report.get('vss_runtime_attempted')).lower()}/"
        f"{str(runtime_report.get('vss_runtime_executed')).lower()}"
    )
    print(f"VSS narration records emitted: {len(sidecars)}")
    print(f"JSON parse: {json_status}")
    print(f"Hash manifest: {hash_status}")
    return 0 if final_status.startswith(("PASS_", "PARTIAL_")) and json_status == "PASS" and hash_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
