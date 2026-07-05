#!/usr/bin/env python3
"""Run the R5 configured VSS narration runtime smoke gate."""

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
TASK_NAME = "MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-CONFIGURED-SMOKE-R5"
SCHEMA_VERSION = "metropolis-vss-narration-runtime-configured-smoke-r5.v1"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_narration_runtime_configured_smoke_r5"
DEFAULT_R4_ZIP = (
    REPO_ROOT
    / "outputs"
    / "main_citybrain_metropolis_vss_narration_runtime_integration_r4"
    / "METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_PACKAGE.zip"
)
PACKAGE_NAME = "METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_WITH_LIMITATIONS"
PARTIAL_NOT_CONFIGURED_STATUS = "PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NOT_CONFIGURED_R5_GUARDRAILS_READY"
PARTIAL_EXECUTION_FAILED_STATUS = "PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_EXECUTION_FAILED_R5_GUARDRAILS_READY"
PARTIAL_NO_USABLE_PROSE_STATUS = "PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NO_USABLE_PROSE_R5_GUARDRAILS_READY"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_NARRATION_RUNTIME_R5_BOUNDARY_OR_FABRICATION"

R4_EXPECTED_STATUS = "PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NOT_CONFIGURED_R4_GUARDRAILS_READY"
VISIBLE_LABEL = "Candidate observation\nVSS narration only\nHuman review required\nNot a finding\nNo action taken"

REQUIRED_R4_FILES = [
    "CHECK_NARRATION_SUFFICIENCY_REPORT_R4.json",
    "CLAIM_BOUNDARY_AUDIT_R4.json",
    "HASH_MANIFEST.json",
    "HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R4.json",
    "INPUT_R3_PACKAGE_VALIDATION_R4.json",
    "JSON_PARSE_REPORT_R4.json",
    "MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R4.json",
    "METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_CLOSEOUT_DECISION.json",
    "METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_DECISION.json",
    "NO_ACTION_AUDIT_R4.json",
    "SECRET_AUDIT_R4.json",
    "SOURCE_CLASS_SEPARATION_AUDIT_R4.json",
    "VSS_INPUT_PACKET_R4.json",
    "VSS_NARRATION_GUARDRAIL_REPORT_R4.json",
    "VSS_NARRATION_NORMALIZATION_REPORT_R4.json",
    "VSS_NARRATION_SIDECARS_R4.jsonl",
    "VSS_PROSE_VS_DETECTION_CONFLICT_AUDIT_R4.json",
    "VSS_RUNTIME_ADAPTER_CONFIG_R4.json",
    "VSS_RUNTIME_EXECUTION_REPORT_R4.json",
]

FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    ("confirmed_violation", r"\b(confirmed violation|violation confirmed|illegal activity|offence|offense)\b"),
    ("legal_or_certified_finding", r"\b(legal finding|certified finding|finding of violation|legally confirmed|guilty)\b"),
    ("identity_or_biometric_inference", r"\b(identified person|person identified|suspect|offender|biometric|identity match)\b"),
    ("face_or_license_plate_recognition", r"\b(face recognition|face recognized|license plate|licence plate|plate number|plate recognized)\b"),
    ("official_case_or_ticket", r"\b(official ticket|ticket created|case created|official case|citation issued|fine issued)\b"),
    ("dispatch_routing_control_enforcement", r"\b(dispatch|route crew|route responders|routing command|traffic control|enforcement action|enforce)\b"),
    ("operational_alert_command", r"\b(alert operator to act|send alert|alert sent|operator must act)\b"),
    ("automated_action", r"\b(autonomous action|automated action|auto action|automatically ticket|automatically dispatch)\b"),
    ("production_live_monitoring", r"\b(production monitoring|live cctv|live monitoring|real-time surveillance)\b"),
    ("vss_as_fact_source", r"\b(vss sensor|vss detected|vss confirms|vss proves|fact source|source of truth)\b"),
    ("new_detection_claim", r"\b(new object detected|new detection|vss found|vss detected)\b"),
]

UNSUPPORTED_OBJECT_TERMS = [
    "person",
    "pedestrian",
    "bicycle",
    "road sign",
    "road_sign",
    "truck",
    "bus",
    "motorcycle",
]

SECRET_PATTERNS: list[tuple[str, str]] = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("bearer_token", r"(?i)\bbearer\s+[A-Za-z0-9_\-.]{20,}"),
    ("generic_api_key", r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*[A-Za-z0-9_\-]{12,}"),
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
    rows: list[Any] = []
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


def validate_r4_package(r4_zip: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "r4_zip": str(r4_zip),
        "r4_zip_exists": r4_zip.exists(),
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
            "missing": [],
            "mismatches": [],
        },
    }
    if not r4_zip.exists():
        result["failure_reason"] = "R4 package zip not found."
        return result

    result["r4_zip_sha256"] = sha256_file(r4_zip)
    parsed_json: dict[str, Any] = {}
    parsed_jsonl: dict[str, list[Any]] = {}

    try:
        with zipfile.ZipFile(r4_zip, "r") as zf:
            names = zf.namelist()
            result["zip_entries"] = len(names)
            missing_required = [name for name in REQUIRED_R4_FILES if name not in names]
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

    closeout = parsed_json.get("METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_CLOSEOUT_DECISION.json", {})
    json_parse = parsed_json.get("JSON_PARSE_REPORT_R4.json", {})
    evidence = parsed_json.get("MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R4.json", {})
    human_packet = parsed_json.get("HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R4.json", {})
    sidecar_rows = parsed_jsonl.get("VSS_NARRATION_SIDECARS_R4.jsonl", [])

    truth_ok = (
        closeout.get("status") == R4_EXPECTED_STATUS
        and closeout.get("r2_candidate_observations") == 24
        and closeout.get("r2_candidate_events") == 1
        and closeout.get("structured_detection_source_class") == "sensor_inferred"
        and closeout.get("vss_output_source_class") == "model_generated_narrative"
        and closeout.get("vss_is_fact_source") is False
        and closeout.get("candidate_event_modified_by_vss") is False
        and evidence.get("source_class") == "sensor_inferred"
        and human_packet.get("human_review_required") is True
        and len(sidecar_rows) == 0
    )
    result.update(
        {
            "r4_closeout_status": closeout.get("status"),
            "r4_runtime_status": closeout.get("runtime_status"),
            "r4_runtime_configured": bool(closeout.get("runtime_configured", False)),
            "r4_json_parse_status": json_parse.get("status"),
            "vss_runtime_attempted": bool(closeout.get("vss_runtime_attempted")),
            "vss_runtime_executed": bool(closeout.get("vss_runtime_executed")),
            "vss_narration_records": int(closeout.get("vss_narration_records", 0) or 0),
            "r2_candidate_observations": closeout.get("r2_candidate_observations"),
            "r2_candidate_events": closeout.get("r2_candidate_events"),
            "structured_detection_source_class": closeout.get("structured_detection_source_class"),
            "vss_output_source_class": closeout.get("vss_output_source_class"),
            "vss_is_fact_source": closeout.get("vss_is_fact_source"),
            "candidate_event_modified_by_vss": closeout.get("candidate_event_modified_by_vss"),
            "human_review_required": closeout.get("human_review_required"),
            "no_action_taken": closeout.get("no_action_taken"),
            "official_record_created": closeout.get("official_record_created"),
            "r4_preserved_r2_truth": truth_ok,
            "_parsed_json": parsed_json,
            "_parsed_jsonl": parsed_jsonl,
        }
    )
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


def context_from_r4(validation: dict[str, Any]) -> dict[str, Any]:
    parsed = validation.get("_parsed_json", {})
    closeout = parsed.get("METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_CLOSEOUT_DECISION.json", {})
    evidence = parsed.get("MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R4.json", {})
    human_packet = parsed.get("HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R4.json", {})
    input_packet = parsed.get("VSS_INPUT_PACKET_R4.json", {})
    metadata = input_packet.get("r2_object_metadata_summary", {})
    evidence_frame = evidence.get("evidence_frame", {})
    evidence_clip = evidence.get("evidence_clip", {})
    return {
        "media_source": evidence_clip.get("clip_ref") or metadata.get("media_source"),
        "candidate_event_ref": human_packet.get("candidate_event_ref")
        or (evidence.get("candidate_event_refs") or [None])[0],
        "evidence_bundle_ref": human_packet.get("evidence_bundle_ref") or evidence.get("bundle_id"),
        "candidate_observation_refs": evidence.get("candidate_observation_refs")
        or human_packet.get("candidate_observation_refs", []),
        "object_metadata_refs": evidence.get("object_metadata_refs") or human_packet.get("object_metadata_refs", []),
        "object_metadata_count": closeout.get("r2_candidate_observations") or metadata.get("object_metadata_count", 24),
        "candidate_observation_count": closeout.get("r2_candidate_observations") or metadata.get("candidate_observation_count", 24),
        "candidate_event_count": closeout.get("r2_candidate_events", 1),
        "zone": metadata.get("zone") or human_packet.get("model_source_provenance", {}).get("zone_id"),
        "class_label": metadata.get("class_label") or human_packet.get("model_source_provenance", {}).get("class_label"),
        "detection_class": metadata.get("detection_class") or human_packet.get("model_source_provenance", {}).get("detection_class"),
        "structured_detection_source_class": "sensor_inferred",
        "structured_detection_source": "DeepStream/Metropolis R2 object metadata",
        "frame_ref": evidence_frame.get("frame_ref"),
        "frame_number": evidence_frame.get("frame_number"),
        "frame_time_ms": evidence_frame.get("frame_time_ms"),
        "bbox": evidence_frame.get("bbox"),
        "candidate_label": VISIBLE_LABEL,
        "raw_r4_evidence_bundle": evidence,
        "raw_r4_human_packet": human_packet,
    }


def build_vss_input_packet(ctx: dict[str, Any], dry_run_label: str | None) -> dict[str, Any]:
    packet = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "created_at": utc_now(),
        "media_ref": ctx["media_source"],
        "selected_candidate_event_ref": ctx["candidate_event_ref"],
        "evidence_bundle_ref": ctx["evidence_bundle_ref"],
        "candidate_observation_refs": ctx["candidate_observation_refs"],
        "object_metadata_summary": {
            "structured_detection_source": ctx["structured_detection_source"],
            "structured_detection_source_class": "sensor_inferred",
            "zone": ctx["zone"],
            "class_label": ctx["class_label"],
            "detection_class": ctx["detection_class"],
            "object_metadata_count": ctx["object_metadata_count"],
            "candidate_observation_count": ctx["candidate_observation_count"],
            "candidate_event_count": ctx["candidate_event_count"],
            "frame_ref": ctx["frame_ref"],
            "frame_number": ctx["frame_number"],
            "frame_time_ms": ctx["frame_time_ms"],
            "bbox": ctx["bbox"],
        },
        "limitations": [
            "One R4 package, one candidate event, one bounded zone, one object class.",
            "R2 DeepStream/Metropolis metadata is the only sensor_inferred source.",
            "VSS may narrate only and must not infer new facts, counts, identity, legal findings, tickets, or actions.",
            "Human review is required; this is not a finding.",
        ],
        "instruction": (
            "Narrate only the bounded candidate-observation evidence. Treat VSS output as "
            "model_generated_narrative, not as a sensor or fact source. Do not add detections, "
            "object counts, identity, legal findings, tickets, dispatch/control/enforcement, "
            "production-monitoring, or live-CCTV claims."
        ),
        "required_safe_language": [
            "candidate observation",
            "VSS narration only",
            "human review required",
            "not a finding",
            "no action taken",
        ],
    }
    if dry_run_label:
        packet["dry_run_label"] = dry_run_label
    return packet


def resolve_runtime_config(args: argparse.Namespace) -> dict[str, Any]:
    command = args.vss_command or os.environ.get("CITYBRAIN_VSS_COMMAND")
    endpoint = args.vss_endpoint or os.environ.get("CITYBRAIN_VSS_ENDPOINT")
    command_source = "cli" if args.vss_command else ("env" if os.environ.get("CITYBRAIN_VSS_COMMAND") else "none")
    endpoint_source = "cli" if args.vss_endpoint else ("env" if os.environ.get("CITYBRAIN_VSS_ENDPOINT") else "none")
    if command:
        mode = "command"
    elif endpoint:
        mode = "endpoint"
    else:
        mode = "not_configured"
    timeout = max(1, int(args.timeout_sec or 120))
    return {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "runtime_configured": mode in {"command", "endpoint"},
        "runtime_mode": mode,
        "command_source": command_source,
        "endpoint_source": endpoint_source,
        "redacted": True,
        "timeout_sec": timeout,
        "max_narration_records": max(1, int(args.max_narration_records or 1)),
        "notes": ["Runtime command and endpoint values are redacted from package artifacts."],
        "_command": command,
        "_endpoint": endpoint,
    }


def safe_config(config: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in config.items() if not k.startswith("_")}


def execute_runtime(config: dict[str, Any], input_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    output_path = output_root / "VSS_RUNTIME_COMMAND_OUTPUT_R5.json"
    stdout_path = output_root / "VSS_RUNTIME_STDOUT_R5.txt"
    stderr_path = output_root / "VSS_RUNTIME_STDERR_R5.txt"
    mode = config["runtime_mode"]
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "runtime_mode": mode,
        "runtime_configured": config["runtime_configured"],
        "runtime_status": "NOT_CONFIGURED",
        "vss_runtime_attempted": False,
        "vss_runtime_executed": False,
        "timeout_sec": config["timeout_sec"],
        "returncode_or_http_status": None,
        "input_packet_ref": rel(input_path),
        "stdout_ref": None,
        "stderr_ref": None,
        "output_json_ref": None,
        "response_body_ref": None,
        "runtime_redacted": True,
    }
    capture: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "runtime_mode": mode,
        "runtime_status": "NOT_CONFIGURED",
        "captured": False,
        "capture_source": None,
        "stdout_text": "",
        "stderr_text": "",
        "output_file_text": "",
        "response_body_text": "",
        "notes": [],
    }
    if mode == "not_configured":
        note = "No --vss-command, --vss-endpoint, CITYBRAIN_VSS_COMMAND, or CITYBRAIN_VSS_ENDPOINT was configured."
        report["blocked_reason"] = note
        capture["notes"].append(note)
        return report, capture

    if mode == "command":
        command = config.get("_command") or ""
        if "{input_json}" not in command or "{output_json}" not in command:
            note = "Configured command did not contain both {input_json} and {output_json}; not executed for safety."
            report.update({"runtime_status": "CONFIGURED_NOT_ATTEMPTED", "blocked_reason": note})
            capture.update({"runtime_status": "CONFIGURED_NOT_ATTEMPTED", "notes": [note]})
            return report, capture

        rendered = command.format(input_json=str(input_path), output_json=str(output_path))
        report["vss_runtime_attempted"] = True
        env = os.environ.copy()
        env["CITYBRAIN_VSS_INPUT_PACKET"] = str(input_path)
        env["CITYBRAIN_VSS_OUTPUT_PACKET"] = str(output_path)
        try:
            completed = subprocess.run(
                rendered,
                shell=True,
                capture_output=True,
                text=True,
                timeout=config["timeout_sec"],
                env=env,
            )
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            write_text(stdout_path, stdout)
            write_text(stderr_path, stderr)
            output_text = output_path.read_text(encoding="utf-8", errors="replace") if output_path.exists() else ""
            report.update(
                {
                    "runtime_status": "ATTEMPTED_EXECUTED" if completed.returncode == 0 else "ATTEMPTED_FAILED",
                    "vss_runtime_executed": completed.returncode == 0,
                    "returncode_or_http_status": completed.returncode,
                    "stdout_ref": rel(stdout_path),
                    "stderr_ref": rel(stderr_path),
                    "output_json_ref": rel(output_path) if output_path.exists() else None,
                }
            )
            capture.update(
                {
                    "runtime_status": report["runtime_status"],
                    "captured": bool(output_text.strip() or stdout.strip()),
                    "capture_source": "output_json" if output_text.strip() else ("stdout" if stdout.strip() else None),
                    "stdout_text": stdout,
                    "stderr_text": stderr,
                    "output_file_text": output_text,
                }
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or "Runtime command timed out."
            write_text(stdout_path, stdout)
            write_text(stderr_path, stderr)
            report.update(
                {
                    "runtime_status": "ATTEMPTED_TIMEOUT",
                    "vss_runtime_attempted": True,
                    "stdout_ref": rel(stdout_path),
                    "stderr_ref": rel(stderr_path),
                    "blocked_reason": "Runtime command timed out.",
                }
            )
            capture.update(
                {
                    "runtime_status": "ATTEMPTED_TIMEOUT",
                    "captured": bool(stdout.strip()),
                    "capture_source": "stdout" if stdout.strip() else None,
                    "stdout_text": stdout,
                    "stderr_text": stderr,
                }
            )
        return report, capture

    if mode == "endpoint":
        report["vss_runtime_attempted"] = True
        response_path = output_root / "VSS_RUNTIME_RESPONSE_BODY_R5.txt"
        packet = json.loads(input_path.read_text(encoding="utf-8"))
        request = urllib.request.Request(
            config["_endpoint"],
            data=json.dumps(packet).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=config["timeout_sec"]) as response:  # noqa: S310
                body = response.read().decode("utf-8", errors="replace")
                write_text(response_path, body)
                status_code = int(response.status)
                ok = 200 <= status_code < 300
                report.update(
                    {
                        "runtime_status": "ATTEMPTED_EXECUTED" if ok else "ATTEMPTED_FAILED",
                        "vss_runtime_executed": ok,
                        "returncode_or_http_status": status_code,
                        "response_body_ref": rel(response_path),
                    }
                )
                capture.update(
                    {
                        "runtime_status": report["runtime_status"],
                        "captured": bool(body.strip()),
                        "capture_source": "response_body" if body.strip() else None,
                        "response_body_text": body,
                    }
                )
        except TimeoutError:
            write_text(response_path, "")
            report.update(
                {
                    "runtime_status": "ATTEMPTED_TIMEOUT",
                    "response_body_ref": rel(response_path),
                    "blocked_reason": "Runtime endpoint timed out.",
                }
            )
            capture.update({"runtime_status": "ATTEMPTED_TIMEOUT", "notes": ["Runtime endpoint timed out."]})
        except urllib.error.URLError as exc:
            write_text(response_path, str(exc))
            report.update(
                {
                    "runtime_status": "ATTEMPTED_FAILED",
                    "response_body_ref": rel(response_path),
                    "blocked_reason": f"Runtime endpoint failed: {exc}",
                }
            )
            capture.update(
                {
                    "runtime_status": "ATTEMPTED_FAILED",
                    "response_body_text": str(exc),
                    "notes": ["Runtime endpoint failed; endpoint URL redacted."],
                }
            )
        return report, capture

    report["runtime_status"] = "ATTEMPTED_FAILED"
    report["blocked_reason"] = f"Unsupported runtime mode: {mode}"
    capture["runtime_status"] = "ATTEMPTED_FAILED"
    capture["notes"].append(report["blocked_reason"])
    return report, capture


def raw_text_for_normalization(capture: dict[str, Any]) -> str:
    for key in ("output_file_text", "response_body_text", "stdout_text"):
        text = capture.get(key)
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def parse_runtime_rows(raw_text: str) -> tuple[list[Any], str]:
    if not raw_text.strip():
        return [], "empty"
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, list):
            return parsed, "json_array"
        return [parsed], "json_object"
    except json.JSONDecodeError:
        pass
    try:
        rows = parse_jsonl_text(raw_text)
        if rows:
            return rows, "jsonl"
    except ValueError:
        pass
    return [{"text": raw_text}], "plain_text"


def extract_text(row: Any) -> str:
    if isinstance(row, str):
        return row.strip()
    if isinstance(row, dict):
        for key in ("narration_text", "text", "narration", "caption", "summary", "response", "generated_text"):
            val = row.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def normalize_vss_output(
    capture: dict[str, Any],
    ctx: dict[str, Any],
    runtime_report: dict[str, Any],
    max_records: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_text = raw_text_for_normalization(capture)
    rows, detected_format = parse_runtime_rows(raw_text)
    sidecars: list[dict[str, Any]] = []
    dropped = 0
    for idx, row in enumerate(rows[:max_records], start=1):
        text = extract_text(row)
        if not text:
            dropped += 1
            continue
        uncertainty_notes = [
            "VSS narration is model_generated_narrative only.",
            "Human review required before interpretation outside the candidate-observation lane.",
        ]
        if isinstance(row, dict):
            row_notes = row.get("uncertainty_notes") or row.get("limitations") or row.get("notes")
            if isinstance(row_notes, list):
                uncertainty_notes.extend(str(note) for note in row_notes)
        payload = {
            "event": ctx["candidate_event_ref"],
            "bundle": ctx["evidence_bundle_ref"],
            "text": text,
            "runtime": runtime_report.get("runtime_mode"),
        }
        sidecars.append(
            {
                "schema_version": SCHEMA_VERSION,
                "task_name": TASK_NAME,
                "narration_id": stable_id("metropolis-vss-r5-narration", payload),
                "source_class": "model_generated_narrative",
                "vss_is_fact_source": False,
                "candidate_event_ref": ctx["candidate_event_ref"],
                "evidence_bundle_ref": ctx["evidence_bundle_ref"],
                "supported_candidate_observation_refs": ctx["candidate_observation_refs"],
                "narration_text": text,
                "uncertainty_notes": uncertainty_notes,
                "claim_boundary_label": VISIBLE_LABEL,
                "runtime_mode": runtime_report.get("runtime_mode"),
                "created_at": utc_now(),
                "human_review_required": True,
                "not_a_finding": True,
                "no_action_taken": True,
                "official_record_created": False,
                "candidate_event_modified_by_vss": False,
                "forbidden_claims_detected": [],
                "conflict_flags": [],
            }
        )
    if len(rows) > max_records:
        dropped += len(rows) - max_records
    report = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "input_format_detected": detected_format,
        "raw_records_seen": len(rows),
        "max_narration_records": max_records,
        "normalized_records": len(sidecars),
        "dropped_records": dropped,
        "status": "PASS" if sidecars else "PARTIAL",
        "notes": ["No VSS narration is fabricated. Empty or unusable runtime output emits zero sidecars."],
    }
    return sidecars, report


def run_guardrails(sidecars: list[dict[str, Any]], raw_capture: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    forbidden: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    allowed_counts = {int(ctx.get("object_metadata_count") or 0), int(ctx.get("candidate_observation_count") or 0)}
    texts = [(sidecar["narration_id"], sidecar.get("narration_text", "")) for sidecar in sidecars]
    if raw_text_for_normalization(raw_capture):
        texts.append(("raw_capture", raw_text_for_normalization(raw_capture)))

    for source_id, text in texts:
        lowered = text.lower()
        for family, pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                forbidden.append({"source": source_id, "family": family})
        for term in UNSUPPORTED_OBJECT_TERMS:
            if term in lowered:
                conflicts.append({"source": source_id, "family": "new_detection_class_invented_by_vss", "term": term})
        for match in re.finditer(r"\b(\d+)\s+(cars?|vehicles?|objects?|detections?)\b", lowered):
            count = int(match.group(1))
            if count > 1 and count not in allowed_counts:
                conflicts.append({"source": source_id, "family": "object_count_override_from_prose", "count": count})

    for sidecar in sidecars:
        sidecar_forbidden = [f["family"] for f in forbidden if f["source"] == sidecar["narration_id"]]
        sidecar_conflicts = [c["family"] for c in conflicts if c["source"] == sidecar["narration_id"]]
        sidecar["forbidden_claims_detected"] = sidecar_forbidden
        sidecar["conflict_flags"] = sidecar_conflicts

    status = "PASS" if not forbidden and not conflicts else "FAIL"
    return {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": status,
        "vss_narration_records": len(sidecars),
        "forbidden_claims_detected": forbidden,
        "conflict_flags": conflicts,
        "candidate_event_modified_by_vss": False,
        "vss_is_fact_source": False,
        "human_review_required": True,
        "not_a_finding": True,
        "no_action_taken": True,
        "official_record_created": False,
        "checks": [
            {"check": "no_confirmed_violation_legal_identity_action_or_live_claim", "status": "PASS" if not forbidden else "FAIL"},
            {"check": "no_new_detections_or_count_override", "status": "PASS" if not conflicts else "FAIL"},
            {"check": "source_class_model_generated_narrative", "status": "PASS"},
            {"check": "candidate_event_not_modified_by_vss", "status": "PASS"},
        ],
    }


def write_audits(
    output_root: Path,
    sidecars: list[dict[str, Any]],
    ctx: dict[str, Any],
    runtime_report: dict[str, Any],
    guardrail_report: dict[str, Any],
) -> dict[str, str]:
    source_status = "PASS" if all(s.get("source_class") == "model_generated_narrative" for s in sidecars) else "FAIL"
    write_json(
        output_root / "SOURCE_CLASS_SEPARATION_AUDIT_R5.json",
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
    conflict_status = "PASS" if not guardrail_report["conflict_flags"] else "FAIL"
    write_json(
        output_root / "VSS_PROSE_VS_DETECTION_CONFLICT_AUDIT_R5.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": conflict_status,
            "r2_class_label": ctx["class_label"],
            "r2_object_count": ctx["object_metadata_count"],
            "conflict_flags": guardrail_report["conflict_flags"],
        },
    )
    claim_status = "PASS" if not guardrail_report["forbidden_claims_detected"] else "FAIL"
    write_json(
        output_root / "CLAIM_BOUNDARY_AUDIT_R5.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": claim_status,
            "candidate_label": VISIBLE_LABEL,
            "forbidden_claims_detected": guardrail_report["forbidden_claims_detected"],
            "human_review_required": True,
            "not_a_finding": True,
        },
    )
    no_action_status = "PASS" if all(s.get("no_action_taken") is True for s in sidecars) else "FAIL"
    write_json(
        output_root / "NO_ACTION_AUDIT_R5.json",
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
        output_root / "CHECK_NARRATION_SUFFICIENCY_REPORT_R5.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": check_status,
            "dimension_results": [
                {"dimension": "R4 package validation", "status": "PASS", "value": "guarded partial accepted"},
                {
                    "dimension": "VSS runtime configured",
                    "status": "PASS" if runtime_report["runtime_configured"] else "PARTIAL",
                    "value": runtime_report["runtime_mode"],
                },
                {
                    "dimension": "VSS runtime executed",
                    "status": "PASS" if runtime_report["vss_runtime_executed"] else "PARTIAL",
                    "value": runtime_report["runtime_status"],
                },
                {"dimension": "usable narration sidecars", "status": "PASS" if sidecars else "PARTIAL", "value": len(sidecars)},
                {"dimension": "claim boundary", "status": claim_status, "value": guardrail_report["forbidden_claims_detected"]},
                {"dimension": "prose-vs-detection conflicts", "status": conflict_status, "value": guardrail_report["conflict_flags"]},
                {"dimension": "human-review stop", "status": "PASS", "value": "human_review_required=true"},
                {"dimension": "no-action boundary", "status": no_action_status, "value": "no_action_taken=true"},
            ],
        },
    )
    return {
        "source_class": source_status,
        "prose_vs_detection_conflict": conflict_status,
        "vss_guardrail": guardrail_report["status"],
        "claim_boundary": claim_status,
        "no_action": no_action_status,
        "check_narration_sufficiency": check_status,
    }


def write_review_artifacts(output_root: Path, sidecars: list[dict[str, Any]], ctx: dict[str, Any]) -> None:
    bundle = dict(ctx["raw_r4_evidence_bundle"])
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
    write_json(output_root / "MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R5.json", bundle)
    packet = dict(ctx["raw_r4_human_packet"])
    packet.update(
        {
            "schema_version": SCHEMA_VERSION,
            "candidate_label": VISIBLE_LABEL,
            "review_prompt": (
                "Review the R2 structured vehicle-presence candidate event. "
                "If R5 VSS narration is attached, treat it as model-generated narrative only, not as a fact source."
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
    write_json(output_root / "HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R5.json", packet)


def write_secret_audit(output_root: Path) -> str:
    findings: list[dict[str, str]] = []
    for path in sorted(output_root.iterdir(), key=lambda p: p.name):
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                findings.append({"file": path.name, "pattern": name})
    status = "PASS" if not findings else "FAIL"
    write_json(output_root / "SECRET_AUDIT_R5.json", {"status": status, "findings": findings})
    return status


def validate_json_outputs(output_root: Path) -> str:
    failures: list[dict[str, str]] = []
    json_count = 0
    jsonl_count = 0
    for path in sorted(output_root.iterdir(), key=lambda p: p.name):
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
        output_root / "JSON_PARSE_REPORT_R5.json",
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
    write_json(
        output_root / "HASH_MANIFEST.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "algorithm": "sha256",
            "generated_at": utc_now(),
            "status": "PASS",
            "file_count": len(files),
            "files": files,
            "excludes": ["HASH_MANIFEST.json", PACKAGE_NAME],
        },
    )
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
        return FAIL_STATUS
    if json_status == "FAIL" or hash_status == "FAIL" or any(status == "FAIL" for status in audits.values()):
        return FAIL_STATUS
    if not runtime.get("runtime_configured"):
        return PARTIAL_NOT_CONFIGURED_STATUS
    if runtime.get("runtime_status") != "ATTEMPTED_EXECUTED":
        return PARTIAL_EXECUTION_FAILED_STATUS
    if not sidecars:
        return PARTIAL_NO_USABLE_PROSE_STATUS
    return PASS_STATUS


def write_decisions(
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
        "input_r4_package_validation_status": validation.get("status"),
        "runtime_status": runtime.get("runtime_status"),
        "runtime_mode": runtime.get("runtime_mode"),
        "runtime_configured": bool(runtime.get("runtime_configured")),
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
        "r4_closeout_status": validation.get("r4_closeout_status"),
        "r2_candidate_observations": validation.get("r2_candidate_observations"),
        "r2_candidate_events": validation.get("r2_candidate_events"),
        "limitations": [
            "R5 consumes one R4 package and one R2/R4 candidate event only.",
            "PASS requires a real configured command or endpoint to execute and produce usable VSS prose.",
            "DeepStream/Metropolis structured metadata remains the only sensor_inferred object-detection source.",
            "VSS narration remains model_generated_narrative only and is not a fact source.",
            "No finding, identity, official record, ticket, dispatch, control, enforcement, alert-command, or automated action is created.",
        ],
        "validation_package_ref": PACKAGE_NAME,
    }
    write_json(output_root / "METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_DECISION.json", decision)
    write_json(output_root / "METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_CLOSEOUT_DECISION.json", decision)


def write_readme(output_root: Path, status: str, runtime: dict[str, Any], sidecars: list[dict[str, Any]]) -> None:
    write_text(
        output_root / "README.md",
        f"""# Metropolis/VSS Narration Runtime Configured Smoke R5

Status: {status}

R5 validates the R4 guarded partial and attempts a configured VSS narration smoke when
`--vss-command`, `--vss-endpoint`, `CITYBRAIN_VSS_COMMAND`, or `CITYBRAIN_VSS_ENDPOINT`
is available.

Runtime mode: {runtime.get("runtime_mode")}
Runtime status: {runtime.get("runtime_status")}
VSS runtime attempted/executed: {str(runtime.get("vss_runtime_attempted")).lower()}/{str(runtime.get("vss_runtime_executed")).lower()}
VSS narration records emitted: {len(sidecars)}

DeepStream/Metropolis structured metadata remains `sensor_inferred`. VSS prose is
`model_generated_narrative` only, human review is required, this is not a finding,
and no action is taken.
""",
    )


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
    parser.add_argument("--input-r4-zip", type=Path, default=DEFAULT_R4_ZIP)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--vss-command")
    parser.add_argument("--vss-endpoint")
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--max-narration-records", type=int, default=1)
    parser.add_argument("--dry-run-label")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    reset_output_root(output_root)

    validation = validate_r4_package(args.input_r4_zip.resolve())
    validation_safe = safe_validation(validation)
    write_json(output_root / "INPUT_R4_PACKAGE_VALIDATION_R5.json", validation_safe)

    if validation.get("status") == "PASS":
        ctx = context_from_r4(validation)
    else:
        ctx = {
            "media_source": None,
            "candidate_event_ref": None,
            "evidence_bundle_ref": None,
            "candidate_observation_refs": [],
            "object_metadata_refs": [],
            "object_metadata_count": 0,
            "candidate_observation_count": 0,
            "candidate_event_count": 0,
            "zone": None,
            "class_label": None,
            "detection_class": None,
            "structured_detection_source_class": "sensor_inferred",
            "structured_detection_source": "DeepStream/Metropolis R2 object metadata",
            "frame_ref": None,
            "frame_number": None,
            "frame_time_ms": None,
            "bbox": None,
            "raw_r4_evidence_bundle": {},
            "raw_r4_human_packet": {},
        }

    input_packet = build_vss_input_packet(ctx, args.dry_run_label)
    input_path = output_root / "VSS_INPUT_PACKET_R5.json"
    write_json(input_path, input_packet)

    config = resolve_runtime_config(args)
    write_json(output_root / "VSS_RUNTIME_ADAPTER_CONFIG_R5.json", safe_config(config))
    runtime_report, raw_capture = execute_runtime(config, input_path, output_root)
    write_json(output_root / "VSS_RUNTIME_EXECUTION_REPORT_R5.json", runtime_report)
    write_json(output_root / "VSS_RAW_RESPONSE_CAPTURE_R5.json", raw_capture)

    sidecars, normalization_report = normalize_vss_output(
        raw_capture,
        ctx,
        runtime_report,
        max(1, int(args.max_narration_records or 1)),
    )
    guardrail_report = run_guardrails(sidecars, raw_capture, ctx)
    normalization_report["guardrail_status"] = guardrail_report["status"]
    write_json(output_root / "VSS_NARRATION_NORMALIZATION_REPORT_R5.json", normalization_report)
    write_json(output_root / "VSS_NARRATION_GUARDRAIL_REPORT_R5.json", guardrail_report)
    write_jsonl(output_root / "VSS_NARRATION_SIDECARS_R5.jsonl", sidecars)

    write_review_artifacts(output_root, sidecars, ctx)
    audits = write_audits(output_root, sidecars, ctx, runtime_report, guardrail_report)
    audits["secret"] = write_secret_audit(output_root)

    initial_status = decide_status(validation, runtime_report, sidecars, audits)
    write_decisions(output_root, initial_status, validation_safe, runtime_report, sidecars, audits)
    write_readme(output_root, initial_status, runtime_report, sidecars)

    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    final_status = decide_status(validation, runtime_report, sidecars, audits, json_status, hash_status)
    write_decisions(output_root, final_status, validation_safe, runtime_report, sidecars, audits, json_status, hash_status)
    write_readme(output_root, final_status, runtime_report, sidecars)
    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    create_package_zip(output_root)

    print(f"Final status: {final_status}")
    print(f"Runner: {rel(Path(__file__).resolve())}")
    print(f"Output root: {rel(output_root)}")
    print(f"Freeze ZIP: {rel(output_root / PACKAGE_NAME)}")
    print(f"VSS runtime attempted/executed: {str(runtime_report.get('vss_runtime_attempted')).lower()}/{str(runtime_report.get('vss_runtime_executed')).lower()}")
    print(f"VSS narration records emitted: {len(sidecars)}")
    print(f"JSON parse: {json_status}")
    print(f"Hash manifest: {hash_status}")
    return 0 if final_status.startswith(("PASS_", "PARTIAL_")) and json_status == "PASS" and hash_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
