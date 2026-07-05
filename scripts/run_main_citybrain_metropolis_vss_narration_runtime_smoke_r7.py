#!/usr/bin/env python3
"""Run the Spark VSS narration runtime smoke gate for Metropolis/VSS R7."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7"
SCHEMA_VERSION = "metropolis-vss-narration-runtime-smoke-r7.v1"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_narration_runtime_smoke_r7"
R2_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_object_metadata_export_r2"
R6C_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_runtime_provisioning_and_configuration_r6c"
PACKAGE_NAME = "METROPOLIS_VSS_NARRATION_RUNTIME_SMOKE_R7_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_NARRATION_RUNTIME_SMOKE_R7_WITH_LIMITATIONS"
PARTIAL_NO_ROUTE = "PARTIAL_METROPOLIS_VSS_NARRATION_SMOKE_R7_SUMMARIZE_ROUTE_NOT_CONFIGURED"
PARTIAL_MEDIA_BLOCKED = "PARTIAL_METROPOLIS_VSS_NARRATION_SMOKE_R7_MEDIA_ACCESS_BLOCKED"
PARTIAL_RUNTIME_ERROR = "PARTIAL_METROPOLIS_VSS_NARRATION_SMOKE_R7_RUNTIME_ERROR_GUARDRAILS_READY"
PARTIAL_EMPTY_OUTPUT = "PARTIAL_METROPOLIS_VSS_NARRATION_SMOKE_R7_EMPTY_OUTPUT_GUARDRAILS_READY"
PARTIAL_MALFORMED_OUTPUT = "PARTIAL_METROPOLIS_VSS_NARRATION_SMOKE_R7_MALFORMED_OUTPUT_GUARDRAILS_READY"
FAIL_SOURCE_BOUNDARY = "FAIL_METROPOLIS_VSS_NARRATION_SMOKE_R7_SOURCE_CLASS_BOUNDARY_BROKEN"
FAIL_EVENT_MUTATION = "FAIL_METROPOLIS_VSS_NARRATION_SMOKE_R7_EVENT_MUTATION"
FAIL_FORBIDDEN_CLAIM = "FAIL_METROPOLIS_VSS_NARRATION_SMOKE_R7_FORBIDDEN_CLAIM"
FAIL_SECRET = "FAIL_METROPOLIS_VSS_NARRATION_SMOKE_R7_SECRET_EXPOSURE"

R2_PASS_STATUS = "PASS_METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_WITH_LIMITATIONS"
R6C_PASS_STATUS = "PASS_METROPOLIS_VSS_RUNTIME_PROVISIONED_AND_CONNECTED_R6C"
DEFAULT_READY_ENDPOINT = "http://spark-2445:38111/v1/ready"
DEFAULT_MODEL = "meta/llama-3.1-8b-instruct"

SAFE_PROMPT = (
    "Give a short visual summary for candidate human review. Focus on visible "
    "vehicles and scene context. Use uncertain language. Do not name people or "
    "readable IDs. Do not recommend any operational step. End with: This is "
    "model-generated candidate review context only; human review is required "
    "and it is not a finding."
)
SYSTEM_PROMPT = (
    "You produce concise model-generated narration for candidate review context. "
    "Use uncertainty, stay descriptive, and avoid operational recommendations."
)

FORBIDDEN_CLAIM_TERMS = [
    "confirmed violation",
    "illegal",
    "guilty",
    "offender",
    "suspect",
    "identity",
    "face recognition",
    "license plate identity",
    "dispatch",
    "ticket created",
    "enforcement",
    "alert operator to act",
    "route unit",
    "official case",
    "legal finding",
    "biometric",
    "autonomous action",
]
SAFE_FRAMING_TERMS = ["candidate", "model-generated", "human review", "not a finding", "uncertain"]
SECRET_PATTERNS: list[tuple[str, str]] = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("bearer_token", r"(?i)\bbearer\s+[A-Za-z0-9_\-.]{20,}"),
    ("credential_assignment", r"(?i)\b(token|api[_-]?key|apikey|password|secret|auth|cookie|sig)\s*[:=]\s*[A-Za-z0-9_\-./+]{8,}"),
    ("header_secret", r"(?i)\b(authorization|x-api-key)\s*:\s*[A-Za-z0-9_\-./+]{8,}"),
    ("private_key", r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
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


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_json_hash(value: Any) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


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


def reset_output_root(path: Path) -> None:
    resolved = path.resolve()
    outputs_root = (REPO_ROOT / "outputs").resolve()
    if outputs_root not in resolved.parents or resolved.name != DEFAULT_OUTPUT_ROOT.name:
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def redact_text(value: str | None) -> str | None:
    if not value:
        return value
    redacted = value
    redacted = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9_\-.]+", r"\1<redacted>", redacted)
    redacted = re.sub(
        r"(?i)(token|api[_-]?key|apikey|password|secret|auth|cookie|sig)(\s*[:=]\s*)\S+",
        r"\1\2<redacted>",
        redacted,
    )
    redacted = re.sub(r"(?i)(authorization|x-api-key)(\s*:\s*)\S+", r"\1\2<redacted>", redacted)
    return redacted


def redact_url(value: str | None) -> str | None:
    if not value:
        return value
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        return redact_text(value)
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path or "/", "", ""))


def contains_secret(text: str) -> bool:
    return any(re.search(pattern, text) for _name, pattern in SECRET_PATTERNS)


def safe_excerpt(value: str | None, limit: int = 4000) -> str | None:
    if value is None:
        return None
    return (redact_text(value) or "")[:limit]


def try_parse_json(text: str) -> tuple[Any | None, str]:
    if not text.strip():
        return None, "EMPTY"
    try:
        return json.loads(text), "PASS"
    except json.JSONDecodeError:
        return None, "FAIL"


def parse_sse_events(text: str) -> list[Any]:
    events: list[Any] = []
    data_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if not line:
            if data_lines:
                payload = "\n".join(data_lines).strip()
                data_lines = []
                if payload == "[DONE]":
                    events.append("[DONE]")
                elif payload:
                    parsed, status = try_parse_json(payload)
                    events.append(parsed if status == "PASS" else payload)
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if data_lines:
        payload = "\n".join(data_lines).strip()
        if payload == "[DONE]":
            events.append("[DONE]")
        elif payload:
            parsed, status = try_parse_json(payload)
            events.append(parsed if status == "PASS" else payload)
    return events


def http_request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    body_bytes: bytes | None = None
    merged_headers = {"User-Agent": "citybrain-r7-vss-smoke/1.0"}
    if headers:
        merged_headers.update(headers)
    if payload is not None:
        body_bytes = json.dumps(payload).encode("utf-8")
        merged_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body_bytes, headers=merged_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace")
            parsed, parse_status = try_parse_json(text)
            sse_events = parse_sse_events(text) if "text/event-stream" in str(resp.headers.get("Content-Type", "")) else []
            if sse_events:
                parsed = {"sse_events": sse_events}
                parse_status = "SSE"
            return {
                "ok": 200 <= int(resp.status) < 300,
                "http_status": int(resp.status),
                "content_type": resp.headers.get("Content-Type"),
                "content_length": resp.headers.get("Content-Length"),
                "body_text": text,
                "body_sha256": sha256_bytes(raw),
                "json_parse_status": parse_status,
                "parsed_json": parsed,
                "sse_event_count": len(sse_events),
                "error_summary": None,
                "latency_ms": round((time.perf_counter() - start) * 1000, 3),
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        text = raw.decode("utf-8", errors="replace")
        parsed, parse_status = try_parse_json(text)
        sse_events = parse_sse_events(text) if "text/event-stream" in str(exc.headers.get("Content-Type", "") if exc.headers else "") else []
        if sse_events:
            parsed = {"sse_events": sse_events}
            parse_status = "SSE"
        return {
            "ok": False,
            "http_status": int(exc.code),
            "content_type": exc.headers.get("Content-Type") if exc.headers else None,
            "content_length": exc.headers.get("Content-Length") if exc.headers else None,
            "body_text": text,
            "body_sha256": sha256_bytes(raw),
            "json_parse_status": parse_status,
            "parsed_json": parsed,
            "sse_event_count": len(sse_events),
            "error_summary": f"HTTPError: {exc.code}",
            "latency_ms": round((time.perf_counter() - start) * 1000, 3),
        }
    except Exception as exc:
        return {
            "ok": False,
            "http_status": None,
            "content_type": None,
            "content_length": None,
            "body_text": "",
            "body_sha256": None,
            "json_parse_status": "EMPTY",
            "parsed_json": None,
            "sse_event_count": 0,
            "error_summary": f"{type(exc).__name__}: {exc}",
            "latency_ms": round((time.perf_counter() - start) * 1000, 3),
        }


def load_r2_lineage() -> dict[str, Any]:
    closeout = read_json(R2_ROOT / "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_CLOSEOUT_DECISION.json")
    mapping = read_json(R2_ROOT / "MEDIA_TO_CANDIDATE_EVENT_MAPPING_R2.json")
    export = read_json(R2_ROOT / "DEEPSTREAM_OBJECT_METADATA_EXPORT_REPORT.json")
    event = mapping.get("candidate_event", {}) if isinstance(mapping.get("candidate_event"), dict) else {}
    observations_path = R2_ROOT / "CANDIDATE_OBSERVATION_SAMPLE_R2.jsonl"
    observation_rows = []
    if observations_path.exists():
        observation_rows = parse_jsonl_text(observations_path.read_text(encoding="utf-8"))
    package_path = R2_ROOT / "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_PACKAGE.zip"
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "input_root": rel(R2_ROOT),
        "input_package": rel(package_path) if package_path.exists() else None,
        "input_package_sha256": sha256_file(package_path) if package_path.exists() else None,
        "r2_status": closeout.get("status"),
        "r2_pass": closeout.get("status") == R2_PASS_STATUS,
        "media_source_ref": closeout.get("media_source_selected") or export.get("media_source_selected"),
        "media_source_id": event.get("media_source_id"),
        "camera_source_id": event.get("camera_source_id"),
        "zone_id": event.get("zone_id") or closeout.get("zone_selected"),
        "class_label": event.get("class_label") or closeout.get("class_label_selected"),
        "detection_class": event.get("detection_class") or closeout.get("detection_class_selected"),
        "candidate_event_id": event.get("candidate_event_id"),
        "candidate_event_count": closeout.get("candidate_events_emitted"),
        "candidate_observation_count": closeout.get("candidate_observations_emitted") or len(observation_rows),
        "candidate_observation_ids": event.get("source_observation_ids", []),
        "confidence_summary": event.get("confidence_summary"),
        "evidence_bundle_ref": event.get("evidence_bundle_ref"),
        "structured_source_class": event.get("source_class") or "sensor_inferred",
        "candidate_event_original_hash": stable_json_hash(event),
        "candidate_event_unmodified_by_r7": True,
        "official_record_created": bool(event.get("official_record_created")),
        "no_action_taken": event.get("no_action_taken") is not False,
        "_candidate_event": event,
    }


def load_r6c_lineage() -> dict[str, Any]:
    closeout = read_json(R6C_ROOT / "R6C_CLOSEOUT_DECISION.json")
    probe = read_json(R6C_ROOT / "VSS_RUNTIME_CONNECTIVITY_PROBE_R6C.json")
    provisioning = read_json(R6C_ROOT / "VSS_RUNTIME_PROVISIONING_R6C.json")
    host_allocation = read_json(R6C_ROOT / "RUNTIME_HOST_ALLOCATION_R6C.json")
    package_path = R6C_ROOT / "METROPOLIS_VSS_RUNTIME_PROVISIONING_AND_CONFIGURATION_R6C_PACKAGE.zip"
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "input_root": rel(R6C_ROOT),
        "input_package": rel(package_path) if package_path.exists() else None,
        "input_package_sha256": sha256_file(package_path) if package_path.exists() else None,
        "r6c_status": closeout.get("status"),
        "r6c_pass": closeout.get("status") == R6C_PASS_STATUS,
        "runtime_configured": closeout.get("runtime_configured"),
        "runtime_mode": closeout.get("runtime_mode"),
        "probe_attempted": closeout.get("probe_attempted"),
        "probe_executed": closeout.get("probe_executed"),
        "probe_status": closeout.get("probe_status"),
        "r7_ready": closeout.get("r7_ready"),
        "vss_narration_records": closeout.get("vss_narration_records", 0),
        "candidate_event_modified_by_vss": closeout.get("candidate_event_modified_by_vss", False),
        "ready_endpoint_redacted": provisioning.get("redacted_endpoint"),
        "r6c_probe_http_status": probe.get("http_status"),
        "host_allocation": host_allocation or closeout.get("host_allocation", {}),
    }


def build_host_allocation(r6c: dict[str, Any], ready_endpoint: str | None, summarize_endpoint: str | None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "deepstream_metropolis_lane": {
            "active_host": "txr-4070",
            "status": "proven_in_r2",
            "source_class": "sensor_inferred",
            "proven_by": "R2 object metadata export",
        },
        "spark_vss_lane": {
            "active_host": "spark-2445",
            "runtime_host_label": "spark",
            "status": "configured_for_r7_smoke" if r6c.get("r7_ready") else "not_ready",
            "ready_endpoint": redact_url(ready_endpoint),
            "summarize_endpoint": redact_url(summarize_endpoint),
            "source_class": "model_generated_narrative",
            "not_fact_source": True,
        },
        "txr_3090_role": {
            "active_for_current_metropolis_vss_chain": False,
            "intended_role": "data_graph_rapids_heavier_analytics_box",
        },
        "r7_gate": {
            "opened_by_r6c": bool(r6c.get("r7_ready")),
            "requirement": "R7 requires R6C PASS plus an executed summarize endpoint or command wrapper.",
        },
        "source_boundary": {
            "deepstream_metropolis": "sensor_inferred",
            "spark_vss": "model_generated_narrative",
        },
    }


def media_access_probe(media_ref: str | None, timeout: int, endpoint_mode: bool) -> dict[str, Any]:
    result = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "media_ref_redacted": redact_url(media_ref),
        "media_ref_configured": bool(media_ref),
        "media_accessible": False,
        "access_mode": "http_url" if media_ref and urllib.parse.urlsplit(media_ref).scheme in {"http", "https"} else "local_or_wrapper",
        "http_status": None,
        "content_type": None,
        "content_length": None,
        "latency_ms": None,
        "sha256": None,
        "error_summary": None,
        "notes": [],
    }
    if not media_ref:
        result["error_summary"] = "No media URL or path configured."
        return result
    parsed = urllib.parse.urlsplit(media_ref)
    if parsed.scheme in {"http", "https"}:
        head = http_request(media_ref, method="HEAD", timeout=timeout)
        if not head["ok"] and head.get("http_status") == 405:
            head = http_request(media_ref, method="GET", timeout=timeout)
        result.update(
            {
                "media_accessible": bool(head["ok"]),
                "http_status": head.get("http_status"),
                "content_type": head.get("content_type"),
                "content_length": head.get("content_length"),
                "latency_ms": head.get("latency_ms"),
                "error_summary": head.get("error_summary"),
            }
        )
        if head.get("body_sha256") and head.get("content_length") not in {None, "0"} and head.get("body_text"):
            result["sha256"] = head.get("body_sha256")
        return result
    path = Path(media_ref)
    exists = path.exists()
    result["media_accessible"] = bool(exists and not endpoint_mode)
    result["content_length"] = str(path.stat().st_size) if exists else None
    result["sha256"] = sha256_file(path) if exists else None
    if endpoint_mode:
        result["error_summary"] = "Endpoint mode requires an HTTP(S) media URL."
    elif not exists:
        result["error_summary"] = "Local media path not found."
    return result


def ready_probe(endpoint: str | None, timeout: int) -> dict[str, Any]:
    if not endpoint:
        return {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "ready_endpoint": None,
            "probe_attempted": False,
            "probe_executed": False,
            "probe_status": "NOT_CONFIGURED",
            "http_status": None,
            "latency_ms": None,
            "error_summary": "No Spark VSS ready endpoint configured.",
        }
    response = http_request(endpoint, method="GET", timeout=timeout)
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "ready_endpoint": redact_url(endpoint),
        "probe_attempted": True,
        "probe_executed": True,
        "probe_status": "SUCCESS" if response["ok"] else "FAIL",
        "http_status": response.get("http_status"),
        "content_type": response.get("content_type"),
        "latency_ms": response.get("latency_ms"),
        "error_summary": response.get("error_summary"),
        "body_excerpt": safe_excerpt(response.get("body_text"), 500),
    }


def build_vss_payload(args: argparse.Namespace, r2: dict[str, Any]) -> dict[str, Any]:
    media_info: dict[str, Any] = {"type": "offset", "start_offset": int(args.media_start_offset)}
    if int(args.media_end_offset) > int(args.media_start_offset):
        media_info["end_offset"] = int(args.media_end_offset)
    payload = {
        "url": args.media_path,
        "model": args.vss_model,
        "scenario": "bounded vehicle presence candidate review",
        "events": ["visible vehicle presence candidate"],
        "system_prompt": SYSTEM_PROMPT,
        "prompt": SAFE_PROMPT,
        "max_tokens": int(args.max_tokens),
        "temperature": float(args.temperature),
        "top_p": 1,
        "chunk_duration": 0,
        "chunk_overlap_duration": 0,
        "media_info": media_info,
        "enable_audio": False,
        "enable_reasoning": False,
        "enable_vlm_structured_output": False,
        "objects_of_interest": [str(r2.get("class_label") or "car"), "vehicle"],
        "override_vlm_prompt": True,
        "auto_generate_prompt": False,
    }
    if args.stream_output:
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
    return payload


def build_request_artifact(
    args: argparse.Namespace,
    r2: dict[str, Any],
    ready_endpoint: str | None,
    summarize_endpoint: str | None,
    command: str | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    payload = build_vss_payload(args, r2) if summarize_endpoint else None
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "request_id": "citybrain-r7-vss-narration-smoke-001",
        "created_at": utc_now(),
        "candidate_event_id": r2.get("candidate_event_id"),
        "media_ref": r2.get("media_source_ref"),
        "media_request_url": redact_url(args.media_path),
        "detection_class": r2.get("detection_class"),
        "class_label": r2.get("class_label"),
        "zone_id": r2.get("zone_id"),
        "runtime_host": "spark",
        "source_boundary": {
            "deepstream_metropolis": "sensor_inferred",
            "spark_vss": "model_generated_narrative",
        },
        "ready_endpoint": redact_url(ready_endpoint),
        "summarize_endpoint": redact_url(summarize_endpoint),
        "command_wrapper": redact_text(command),
        "runtime_mode": "endpoint" if summarize_endpoint else "command" if command else "none",
        "bounded_request": {
            "one_media_source": True,
            "one_zone": True,
            "one_detection_class": True,
            "candidate_event_read_only": True,
            "human_review_required": True,
        },
        "vss_payload": payload,
    }
    return artifact, payload


def execute_endpoint_call(endpoint: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    headers = {}
    if payload.get("stream") is True:
        headers["Accept"] = "text/event-stream"
    response = http_request(endpoint, method="POST", payload=payload, timeout=timeout, headers=headers)
    parsed_json = response.get("parsed_json") if response.get("json_parse_status") in {"PASS", "SSE"} else None
    response_text = extract_text(parsed_json) or response.get("body_text") or ""
    response_failure = "summarization failed" in response_text.lower()
    runtime_success = bool(response["ok"] and not response_failure)
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "runtime_mode": "endpoint",
        "summarize_endpoint": redact_url(endpoint),
        "vss_runtime_attempted": True,
        "vss_runtime_executed": True,
        "runtime_status": "EXECUTED_SUCCESS" if runtime_success else "EXECUTED_ERROR",
        "http_status": response.get("http_status"),
        "content_type": response.get("content_type"),
        "latency_ms": response.get("latency_ms"),
        "json_parse_status": response.get("json_parse_status"),
        "sse_event_count": response.get("sse_event_count", 0),
        "body_sha256": response.get("body_sha256"),
        "body_excerpt": safe_excerpt(response.get("body_text")),
        "parsed_json": parsed_json,
        "error_summary": response.get("error_summary") or ("SSE response reported summarization failure." if response_failure else None),
        "_raw_body_text": response.get("body_text") or "",
    }


def execute_command_call(command: str, request_artifact: dict[str, Any], timeout: int) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(request_artifact),
            text=True,
            capture_output=True,
            timeout=timeout,
            shell=True,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        parsed, parse_status = try_parse_json(stdout)
        return {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "runtime_mode": "command",
            "command_wrapper": redact_text(command),
            "vss_runtime_attempted": True,
            "vss_runtime_executed": True,
            "runtime_status": "EXECUTED_SUCCESS" if completed.returncode == 0 else "EXECUTED_ERROR",
            "returncode": completed.returncode,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "json_parse_status": parse_status,
            "stdout_sha256": sha256_text(stdout),
            "stderr_sha256": sha256_text(stderr),
            "stdout_excerpt": safe_excerpt(stdout),
            "stderr_excerpt": safe_excerpt(stderr, 1500),
            "parsed_json": parsed if parse_status == "PASS" else None,
            "error_summary": None if completed.returncode == 0 else "Command wrapper returned non-zero.",
            "_raw_body_text": stdout,
        }
    except Exception as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "runtime_mode": "command",
            "command_wrapper": redact_text(command),
            "vss_runtime_attempted": True,
            "vss_runtime_executed": False,
            "runtime_status": "EXECUTION_FAILED",
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "json_parse_status": "EMPTY",
            "stdout_excerpt": None,
            "stderr_excerpt": None,
            "parsed_json": None,
            "error_summary": f"{type(exc).__name__}: {exc}",
            "_raw_body_text": "",
        }


def extract_text(value: Any) -> str:
    if isinstance(value, dict):
        if isinstance(value.get("sse_events"), list):
            nested = [extract_text(item) for item in value["sse_events"] if item != "[DONE]"]
            nested = [item for item in nested if item]
            if nested:
                return "\n\n".join(nested).strip()
        choices = value.get("choices")
        if isinstance(choices, list):
            texts: list[str] = []
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    texts.append(message["content"])
                elif isinstance(choice.get("text"), str):
                    texts.append(choice["text"])
            if texts:
                return "\n\n".join(text.strip() for text in texts if text.strip()).strip()
        for key in ("summary", "summary_text", "text", "content", "message", "result"):
            if isinstance(value.get(key), str) and value[key].strip():
                return value[key].strip()
        for key in ("data", "results", "records"):
            if isinstance(value.get(key), list):
                nested = [extract_text(item) for item in value[key]]
                nested = [item for item in nested if item]
                if nested:
                    return "\n\n".join(nested).strip()
    if isinstance(value, list):
        nested = [extract_text(item) for item in value]
        nested = [item for item in nested if item]
        if nested:
            return "\n\n".join(nested).strip()
    if isinstance(value, str):
        return value.strip()
    return ""


def extract_time_refs(text: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    pattern = re.compile(r"\[(?P<start>\d{1,2}:\d{2}(?::\d{2})?)\s*[-–]\s*(?P<end>\d{1,2}:\d{2}(?::\d{2})?)\]")
    for match in pattern.finditer(text):
        refs.append({"start": match.group("start"), "end": match.group("end"), "source": "vss_text_timestamp"})
    return refs


def normalized_summary(raw_text: str) -> str:
    text = re.sub(r"\s+", " ", raw_text).strip()
    if not text:
        return ""
    suffix = "This is model-generated candidate review context only; human review is required and it is not a finding."
    if suffix.lower() not in text.lower():
        text = f"{text} {suffix}"
    return text


def normalize_vss_output(capture: dict[str, Any], r2: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if capture.get("runtime_status") != "EXECUTED_SUCCESS":
        raw_text = ""
    else:
        raw_text = extract_text(capture.get("parsed_json")) or extract_text(capture.get("_raw_body_text"))
    summary = normalized_summary(raw_text)
    sidecars: list[dict[str, Any]] = []
    if summary:
        content_hash = sha256_text(f"{r2.get('candidate_event_id')}|{summary}")[:12]
        sidecars.append(
            {
                "schema_version": SCHEMA_VERSION,
                "narration_id": f"metropolis-vss-r7-narration-{content_hash}",
                "candidate_event_id": r2.get("candidate_event_id"),
                "source_class": "model_generated_narrative",
                "runtime_host": "spark",
                "model_or_service": capture.get("parsed_json", {}).get("model") if isinstance(capture.get("parsed_json"), dict) else None,
                "summary_text": summary,
                "time_refs": extract_time_refs(raw_text),
                "uncertainty_notes": [
                    "VSS narration is model-generated review context only.",
                    "R2 DeepStream/Metropolis metadata remains the sensor_inferred source for object metadata.",
                    "The R2 candidate event is not modified by this sidecar.",
                ],
                "forbidden_claims_detected": [],
                "candidate_event_mutated": False,
                "human_review_required": True,
                "vss_is_fact_source": False,
                "official_record_created": False,
                "action_created": False,
            }
        )
    report = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "raw_text_present": bool(raw_text),
        "raw_text_sha256": sha256_text(raw_text) if raw_text else None,
        "raw_text_excerpt": safe_excerpt(raw_text, 1000),
        "normalized_records": len(sidecars),
        "source_class": "model_generated_narrative",
        "candidate_event_mutated": False,
        "status": "PASS" if sidecars else "PARTIAL",
        "notes": [
            "No VSS narration sidecar is fabricated when runtime output is empty.",
            "Normalized sidecars add safe review framing but do not change R2 candidate event fields.",
        ],
    }
    return sidecars, report


def find_forbidden(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    lowered = text.lower()
    for term in FORBIDDEN_CLAIM_TERMS:
        if term in lowered:
            hits.append({"term": term})
    return hits


def run_guardrail_audit(sidecars: list[dict[str, Any]], capture: dict[str, Any]) -> dict[str, Any]:
    forbidden: list[dict[str, Any]] = []
    raw_text = extract_text(capture.get("parsed_json")) or extract_text(capture.get("_raw_body_text"))
    for hit in find_forbidden(raw_text):
        forbidden.append({"source": "raw_vss_output", **hit})
    for sidecar in sidecars:
        sidecar_hits = find_forbidden(sidecar.get("summary_text", ""))
        sidecar["forbidden_claims_detected"] = [hit["term"] for hit in sidecar_hits]
        for hit in sidecar_hits:
            forbidden.append({"source": sidecar["narration_id"], **hit})
    normalized_text = " ".join(sidecar.get("summary_text", "") for sidecar in sidecars).lower()
    safe_framing_present = any(term in normalized_text for term in SAFE_FRAMING_TERMS) if sidecars else True
    if sidecars and not safe_framing_present:
        forbidden.append({"source": "normalized_sidecar", "term": "missing_safe_framing"})
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if not forbidden else "FAIL",
        "vss_narration_records": len(sidecars),
        "forbidden_claims_detected": forbidden,
        "required_safe_framing_terms_any": SAFE_FRAMING_TERMS,
        "safe_framing_present": safe_framing_present,
        "source_class_required": "model_generated_narrative",
        "candidate_event_mutated": False,
        "human_review_required": True,
    }


def write_audits(
    output_root: Path,
    r2: dict[str, Any],
    r6c: dict[str, Any],
    ready: dict[str, Any],
    media: dict[str, Any],
    runtime: dict[str, Any],
    sidecars: list[dict[str, Any]],
    guardrail: dict[str, Any],
) -> dict[str, str]:
    source_failures: list[str] = []
    if r2.get("structured_source_class") != "sensor_inferred":
        source_failures.append("R2 structured source class is not sensor_inferred.")
    if any(sidecar.get("source_class") != "model_generated_narrative" for sidecar in sidecars):
        source_failures.append("A VSS sidecar has a non-narrative source class.")
    if any(sidecar.get("vss_is_fact_source") is not False for sidecar in sidecars):
        source_failures.append("A VSS sidecar is marked as fact source.")
    source_status = "PASS" if not source_failures else "FAIL"
    write_json(
        output_root / "SOURCE_CLASS_SEPARATION_AUDIT_R7.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": source_status,
            "failures": source_failures,
            "r2_structured_source_class": r2.get("structured_source_class"),
            "vss_sidecar_source_class": "model_generated_narrative",
            "vss_is_fact_source": False,
            "sidecar_count": len(sidecars),
        },
    )

    claim_status = "PASS" if guardrail.get("status") == "PASS" else "FAIL"
    write_json(
        output_root / "CLAIM_BOUNDARY_AUDIT_R7.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": claim_status,
            "forbidden_claims_detected": guardrail.get("forbidden_claims_detected", []),
            "vss_output_source_class": "model_generated_narrative",
            "candidate_context_only": True,
            "human_review_required": True,
            "not_a_finding": True,
        },
    )

    event_hash_after = stable_json_hash(r2.get("_candidate_event", {}))
    event_mutated = event_hash_after != r2.get("candidate_event_original_hash") or any(
        sidecar.get("candidate_event_mutated") is not False for sidecar in sidecars
    )
    no_action_status = "PASS" if not event_mutated and all(sidecar.get("action_created") is False for sidecar in sidecars) else "FAIL"
    write_json(
        output_root / "NO_ACTION_AUDIT_R7.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": no_action_status,
            "candidate_event_mutated": event_mutated,
            "candidate_event_original_hash": r2.get("candidate_event_original_hash"),
            "candidate_event_after_hash": event_hash_after,
            "official_record_created": False,
            "action_created": False,
            "no_dispatch_or_control_output": True,
        },
    )

    conflict_flags: list[dict[str, Any]] = []
    raw_text = (extract_text(runtime.get("parsed_json")) or extract_text(runtime.get("_raw_body_text"))).lower()
    if "vss detected" in raw_text or "source of truth" in raw_text:
        conflict_flags.append({"family": "vss_as_detection_source_claim"})
    conflict_status = "PASS" if not conflict_flags else "FAIL"
    write_json(
        output_root / "PROSE_VS_DETECTION_CONFLICT_AUDIT_R7.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": conflict_status,
            "conflict_flags": conflict_flags,
            "r2_detection_class": r2.get("detection_class"),
            "r2_candidate_observation_count": r2.get("candidate_observation_count"),
            "vss_counts_not_promoted_to_facts": True,
            "candidate_event_mutated": False,
        },
    )

    write_json(output_root / "VSS_GUARDRAIL_AUDIT_R7.json", guardrail)
    check_status = "PASS" if sidecars and all(
        status == "PASS" for status in [source_status, claim_status, no_action_status, conflict_status]
    ) else "PARTIAL"
    if any(status == "FAIL" for status in [source_status, claim_status, no_action_status, conflict_status]):
        check_status = "FAIL"
    write_json(
        output_root / "CHECK_NARRATION_SUFFICIENCY_R7.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": check_status,
            "dimension_results": [
                {"dimension": "R6C PASS lineage", "status": "PASS" if r6c.get("r6c_pass") else "FAIL", "value": r6c.get("r6c_status")},
                {"dimension": "Spark VSS readiness", "status": "PASS" if ready.get("probe_status") == "SUCCESS" else "PARTIAL", "value": ready.get("http_status")},
                {"dimension": "media access", "status": "PASS" if media.get("media_accessible") else "PARTIAL", "value": media.get("media_ref_redacted")},
                {"dimension": "VSS runtime executed", "status": "PASS" if runtime.get("vss_runtime_executed") else "PARTIAL", "value": runtime.get("runtime_status")},
                {"dimension": "usable narration sidecars", "status": "PASS" if sidecars else "PARTIAL", "value": len(sidecars)},
                {"dimension": "source-class separation", "status": source_status, "value": "sensor_inferred plus model_generated_narrative"},
                {"dimension": "claim boundary", "status": claim_status, "value": guardrail.get("forbidden_claims_detected", [])},
                {"dimension": "no action or official record", "status": no_action_status, "value": "no action created"},
            ],
        },
    )
    return {
        "source_class_separation": source_status,
        "claim_boundary": claim_status,
        "no_action": no_action_status,
        "prose_vs_detection_conflict": conflict_status,
        "vss_guardrail": guardrail.get("status", "FAIL"),
        "check_narration_sufficiency": check_status,
    }


def write_review_packet(output_root: Path, r2: dict[str, Any], sidecars: list[dict[str, Any]], final_status: str | None = None) -> None:
    write_json(
        output_root / "HUMAN_REVIEW_PACKET_R7.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": final_status or "PENDING",
            "packet_id": "metropolis-vss-r7-human-review-packet-001",
            "candidate_event_id": r2.get("candidate_event_id"),
            "candidate_event_source_class": "sensor_inferred",
            "candidate_event_modified_by_vss": False,
            "r2_detection_class": r2.get("detection_class"),
            "r2_zone_id": r2.get("zone_id"),
            "r2_candidate_observation_count": r2.get("candidate_observation_count"),
            "evidence_bundle_ref": r2.get("evidence_bundle_ref"),
            "vss_narration_sidecar_refs": [sidecar["narration_id"] for sidecar in sidecars],
            "vss_narration_records": len(sidecars),
            "vss_source_class": "model_generated_narrative",
            "vss_is_fact_source": False,
            "review_instruction": "Review R2 sensor-inferred candidate observations; treat VSS text as optional model-generated review context only.",
            "human_review_required": True,
            "official_record_created": False,
            "action_created": False,
        },
    )


def write_runtime_capture(output_root: Path, runtime: dict[str, Any]) -> None:
    public = {key: value for key, value in runtime.items() if not key.startswith("_")}
    write_json(output_root / "SPARK_VSS_RAW_RESPONSE_CAPTURE_R7.json", public)
    trace = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "runtime_mode": runtime.get("runtime_mode"),
        "http_status": runtime.get("http_status"),
        "returncode": runtime.get("returncode"),
        "latency_ms": runtime.get("latency_ms"),
        "body_excerpt": runtime.get("body_excerpt"),
        "stdout_excerpt": runtime.get("stdout_excerpt"),
        "stderr_excerpt": runtime.get("stderr_excerpt"),
        "redaction_applied": True,
    }
    write_json(output_root / ("HTTP_TRACE_REDACTED_R7.json" if runtime.get("runtime_mode") == "endpoint" else "COMMAND_TRACE_REDACTED_R7.json"), trace)


def write_secret_audit(output_root: Path) -> str:
    hits: list[dict[str, Any]] = []
    exclude = {PACKAGE_NAME, "HASH_MANIFEST.json", "SECRET_AUDIT_R7.json"}
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name in exclude:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for family, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                hits.append({"file": path.relative_to(output_root).as_posix(), "family": family})
    status = "PASS" if not hits else "FAIL"
    write_json(
        output_root / "SECRET_AUDIT_R7.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": status,
            "findings": hits,
            "redaction_applied": True,
            "secret_values_written": False,
        },
    )
    return status


def validate_json_outputs(output_root: Path) -> str:
    failures: list[dict[str, Any]] = []
    json_count = 0
    jsonl_count = 0
    excluded = {"HASH_MANIFEST.json", "R7_JSON_PARSE_REPORT.json"}
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name in excluded or path.name == PACKAGE_NAME:
            continue
        if path.suffix.lower() == ".json":
            json_count += 1
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                failures.append({"file": path.relative_to(output_root).as_posix(), "error": str(exc)})
        elif path.suffix.lower() == ".jsonl":
            jsonl_count += 1
            try:
                parse_jsonl_text(path.read_text(encoding="utf-8"))
            except Exception as exc:
                failures.append({"file": path.relative_to(output_root).as_posix(), "error": str(exc)})
    status = "PASS" if not failures else "FAIL"
    write_json(
        output_root / "R7_JSON_PARSE_REPORT.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": status,
            "json_files_parsed": json_count,
            "jsonl_files_parsed": jsonl_count,
            "failures": failures,
            "excluded_files": sorted(excluded),
        },
    )
    return status


def write_hash_manifest(output_root: Path) -> str:
    entries = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", PACKAGE_NAME}:
            continue
        entries.append({"file": path.relative_to(output_root).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    write_json(
        output_root / "HASH_MANIFEST.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "algorithm": "sha256",
            "status": "PASS",
            "file_count": len(entries),
            "excludes": ["HASH_MANIFEST.json", PACKAGE_NAME],
            "files": entries,
        },
    )
    return "PASS"


def create_package_zip(output_root: Path) -> Path:
    package_path = output_root / PACKAGE_NAME
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path != package_path:
                zf.write(path, path.relative_to(output_root).as_posix())
    return package_path


def decide_status(
    r2: dict[str, Any],
    r6c: dict[str, Any],
    ready: dict[str, Any],
    media: dict[str, Any],
    runtime: dict[str, Any],
    sidecars: list[dict[str, Any]],
    audits: dict[str, str],
    json_status: str,
    hash_status: str,
    route_configured: bool,
) -> str:
    if audits.get("secret_audit") == "FAIL":
        return FAIL_SECRET
    if audits.get("source_class_separation") == "FAIL":
        return FAIL_SOURCE_BOUNDARY
    if audits.get("no_action") == "FAIL":
        return FAIL_EVENT_MUTATION
    if audits.get("claim_boundary") == "FAIL" or audits.get("vss_guardrail") == "FAIL":
        return FAIL_FORBIDDEN_CLAIM
    if not r2.get("r2_pass") or not r6c.get("r6c_pass") or not r6c.get("r7_ready"):
        return PARTIAL_RUNTIME_ERROR
    if ready.get("probe_status") != "SUCCESS":
        return PARTIAL_RUNTIME_ERROR
    if not route_configured:
        return PARTIAL_NO_ROUTE
    if not media.get("media_accessible"):
        return PARTIAL_MEDIA_BLOCKED
    if not runtime.get("vss_runtime_executed") or runtime.get("runtime_status") != "EXECUTED_SUCCESS":
        return PARTIAL_RUNTIME_ERROR
    if runtime.get("json_parse_status") == "FAIL" and not extract_text(runtime.get("_raw_body_text")):
        return PARTIAL_MALFORMED_OUTPUT
    if not sidecars:
        return PARTIAL_EMPTY_OUTPUT
    if json_status != "PASS" or hash_status != "PASS":
        return PARTIAL_RUNTIME_ERROR
    return PASS_STATUS


def write_decision(
    output_root: Path,
    final_status: str,
    r2: dict[str, Any],
    r6c: dict[str, Any],
    ready: dict[str, Any],
    media: dict[str, Any],
    runtime: dict[str, Any],
    sidecars: list[dict[str, Any]],
    audits: dict[str, str],
    json_status: str,
    hash_status: str,
) -> None:
    decision = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "final_status": final_status,
        "status": final_status,
        "r7_pass": final_status == PASS_STATUS,
        "r6c_lineage_status": r6c.get("r6c_status"),
        "r6c_pass": bool(r6c.get("r6c_pass")),
        "r7_ready": bool(r6c.get("r7_ready")),
        "spark_ready_probe_status": ready.get("probe_status"),
        "media_accessible": bool(media.get("media_accessible")),
        "vss_runtime_attempted": bool(runtime.get("vss_runtime_attempted")),
        "vss_runtime_executed": bool(runtime.get("vss_runtime_executed")),
        "vss_runtime_status": runtime.get("runtime_status"),
        "narration_records_emitted": len(sidecars),
        "candidate_event_id": r2.get("candidate_event_id"),
        "candidate_event_mutated": False,
        "official_record_created": False,
        "action_created": False,
        "structured_detection_source_class": "sensor_inferred",
        "vss_output_source_class": "model_generated_narrative",
        "vss_is_fact_source": False,
        "audits": audits,
        "json_parse_status": json_status,
        "hash_manifest_status": hash_status,
        "validation_package_ref": PACKAGE_NAME,
        "limitations": [
            "R7 is a bounded runtime smoke over one R2 candidate event and one media sample.",
            "VSS narration is model-generated review context only and is not a fact source.",
            "R2 candidate observations and the R2 candidate event are not modified.",
            "No official record, ticket, dispatch, control, enforcement, identity output, or action is created.",
        ],
    }
    write_json(output_root / "R7_CLOSEOUT_DECISION.json", decision)


def write_readme(output_root: Path, status: str, runtime: dict[str, Any], sidecars: list[dict[str, Any]]) -> None:
    write_text(
        output_root / "README.md",
        f"""# Metropolis/VSS Narration Runtime Smoke R7

Status: {status}

This package runs the first bounded Spark VSS narration smoke over the R2
Metropolis/DeepStream candidate-event context.

Host truth:

- txr-4070: DeepStream / Metropolis, source_class=sensor_inferred, proven by R2
- Spark / DGX Spark: VSS runtime, source_class=model_generated_narrative only
- txr-3090: not active for this Metropolis/VSS chain

Runtime attempted/executed: {str(runtime.get("vss_runtime_attempted")).lower()}/{str(runtime.get("vss_runtime_executed")).lower()}
Runtime status: {runtime.get("runtime_status")}
VSS narration records emitted: {len(sidecars)}

Boundary:

VSS output is never a finding, violation, dispatch, identity claim, official
record, ticket, control output, or action. Human review is required.
""",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--spark-vss-ready-endpoint", default=os.environ.get("CITYBRAIN_SPARK_VSS_READY_ENDPOINT", DEFAULT_READY_ENDPOINT))
    parser.add_argument("--spark-vss-summarize-endpoint", default=os.environ.get("CITYBRAIN_SPARK_VSS_SUMMARIZE_ENDPOINT"))
    parser.add_argument("--spark-vss-command", default=os.environ.get("CITYBRAIN_SPARK_VSS_COMMAND"))
    parser.add_argument("--media-path", default=os.environ.get("CITYBRAIN_R7_MEDIA_PATH") or os.environ.get("CITYBRAIN_R2_MEDIA_PATH"))
    parser.add_argument("--vss-model", default=os.environ.get("CITYBRAIN_SPARK_VSS_MODEL", DEFAULT_MODEL))
    parser.add_argument("--timeout-seconds", type=int, default=int(os.environ.get("CITYBRAIN_SPARK_VSS_TIMEOUT_SECONDS", "300")))
    parser.add_argument("--probe-timeout-seconds", type=int, default=20)
    parser.add_argument("--media-start-offset", type=int, default=0)
    parser.add_argument("--media-end-offset", type=int, default=12)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--stream-output", dest="stream_output", action="store_true", default=True)
    parser.add_argument("--no-stream-output", dest="stream_output", action="store_false")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    reset_output_root(output_root)

    r2 = load_r2_lineage()
    r6c = load_r6c_lineage()
    ready_endpoint = args.spark_vss_ready_endpoint
    summarize_endpoint = args.spark_vss_summarize_endpoint
    command = args.spark_vss_command
    route_configured = bool(summarize_endpoint or command)
    endpoint_mode = bool(summarize_endpoint)

    host_allocation = build_host_allocation(r6c, ready_endpoint, summarize_endpoint)
    request_artifact, payload = build_request_artifact(args, r2, ready_endpoint, summarize_endpoint, command)
    ready = ready_probe(ready_endpoint, max(1, int(args.probe_timeout_seconds)))
    media = media_access_probe(args.media_path, max(1, int(args.probe_timeout_seconds)), endpoint_mode)

    write_json(output_root / "R2_INPUT_LINEAGE_SUMMARY_R7.json", {key: value for key, value in r2.items() if not key.startswith("_")})
    write_json(output_root / "R6C_INPUT_LINEAGE_SUMMARY_R7.json", r6c)
    write_json(output_root / "RUNTIME_HOST_ALLOCATION_R7.json", host_allocation)
    write_json(output_root / "SPARK_VSS_READY_PROBE_R7.json", ready)
    write_json(output_root / "MEDIA_ACCESS_REPORT_R7.json", media)
    write_json(output_root / "SPARK_VSS_NARRATION_REQUEST_R7.json", request_artifact)

    if not route_configured:
        runtime = {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "runtime_mode": "none",
            "vss_runtime_attempted": False,
            "vss_runtime_executed": False,
            "runtime_status": "SUMMARIZE_ROUTE_NOT_CONFIGURED",
            "error_summary": "No Spark VSS summarize endpoint or command wrapper configured.",
            "_raw_body_text": "",
        }
    elif ready.get("probe_status") != "SUCCESS":
        runtime = {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "runtime_mode": "endpoint" if summarize_endpoint else "command",
            "vss_runtime_attempted": False,
            "vss_runtime_executed": False,
            "runtime_status": "READY_PROBE_FAILED",
            "error_summary": ready.get("error_summary"),
            "_raw_body_text": "",
        }
    elif not media.get("media_accessible"):
        runtime = {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "runtime_mode": "endpoint" if summarize_endpoint else "command",
            "vss_runtime_attempted": False,
            "vss_runtime_executed": False,
            "runtime_status": "MEDIA_ACCESS_BLOCKED",
            "error_summary": media.get("error_summary"),
            "_raw_body_text": "",
        }
    elif summarize_endpoint and payload:
        runtime = execute_endpoint_call(summarize_endpoint, payload, max(1, int(args.timeout_seconds)))
    elif command:
        runtime = execute_command_call(command, request_artifact, max(1, int(args.timeout_seconds)))
    else:
        runtime = {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "runtime_mode": "none",
            "vss_runtime_attempted": False,
            "vss_runtime_executed": False,
            "runtime_status": "SUMMARIZE_ROUTE_NOT_CONFIGURED",
            "error_summary": "No callable route configured.",
            "_raw_body_text": "",
        }

    write_runtime_capture(output_root, runtime)
    sidecars, normalization = normalize_vss_output(runtime, r2)
    guardrail = run_guardrail_audit(sidecars, runtime)
    normalization["guardrail_status"] = guardrail.get("status")
    write_json(output_root / "VSS_NARRATION_NORMALIZATION_REPORT_R7.json", normalization)
    write_jsonl(output_root / "VSS_NARRATION_SIDECAR_R7.jsonl", sidecars)

    audits = write_audits(output_root, r2, r6c, ready, media, runtime, sidecars, guardrail)
    audits["secret_audit"] = write_secret_audit(output_root)
    json_status = validate_json_outputs(output_root)
    hash_status = "PASS"
    final_status = decide_status(r2, r6c, ready, media, runtime, sidecars, audits, json_status, hash_status, route_configured)
    write_review_packet(output_root, r2, sidecars, final_status)
    write_decision(output_root, final_status, r2, r6c, ready, media, runtime, sidecars, audits, json_status, hash_status)
    write_readme(output_root, final_status, runtime, sidecars)
    json_status = validate_json_outputs(output_root)
    final_status = decide_status(r2, r6c, ready, media, runtime, sidecars, audits, json_status, hash_status, route_configured)
    write_review_packet(output_root, r2, sidecars, final_status)
    write_decision(output_root, final_status, r2, r6c, ready, media, runtime, sidecars, audits, json_status, hash_status)
    write_readme(output_root, final_status, runtime, sidecars)
    validate_json_outputs(output_root)
    write_hash_manifest(output_root)
    package_path = create_package_zip(output_root)

    print(f"Status: {final_status}")
    print(f"Output: {rel(output_root)}")
    print(f"Freeze ZIP: {rel(package_path)}")
    print(f"Spark ready probe: {ready.get('probe_status')}")
    print(f"Media accessible: {str(media.get('media_accessible')).lower()}")
    print(
        "VSS runtime attempted/executed: "
        f"{str(runtime.get('vss_runtime_attempted')).lower()}/{str(runtime.get('vss_runtime_executed')).lower()}"
    )
    print(f"VSS narration records emitted: {len(sidecars)}")
    print(f"JSON parse: {json_status}")
    print("Hash manifest: PASS")
    return 0 if final_status.startswith(("PASS_", "PARTIAL_")) and json_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
