#!/usr/bin/env python3
"""Run the R6 VSS runtime configuration and connectivity gate."""

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
TASK_NAME = "MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-CONFIGURATION-AND-CONNECTIVITY-R6"
SCHEMA_VERSION = "metropolis-vss-runtime-configuration-and-connectivity-r6.v1"
CONFIG_SCHEMA_VERSION = "metropolis-vss-runtime-configuration-r6.v1"
PROBE_SCHEMA_VERSION = "metropolis-vss-runtime-connectivity-probe-r6.v1"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_runtime_configuration_and_connectivity_r6"
DEFAULT_R5_PACKAGE = (
    REPO_ROOT
    / "outputs"
    / "main_citybrain_metropolis_vss_narration_runtime_configured_smoke_r5"
    / "METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_PACKAGE.zip"
)
PACKAGE_NAME = "METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_WITH_LIMITATIONS"
PARTIAL_NOT_CONFIGURED_STATUS = "PARTIAL_METROPOLIS_VSS_RUNTIME_NOT_CONFIGURED_R6_CONNECTIVITY_CONTRACT_READY"
PARTIAL_CONNECTIVITY_FAILED_STATUS = "PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_CONNECTIVITY_FAILED_R6"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_RUNTIME_CONFIGURATION_BOUNDARY_BREACH_R6"
R5_EXPECTED_STATUS = "PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NOT_CONFIGURED_R5_GUARDRAILS_READY"

REQUIRED_R5_FILES = [
    "CHECK_NARRATION_SUFFICIENCY_REPORT_R5.json",
    "CLAIM_BOUNDARY_AUDIT_R5.json",
    "HASH_MANIFEST.json",
    "HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R5.json",
    "INPUT_R4_PACKAGE_VALIDATION_R5.json",
    "JSON_PARSE_REPORT_R5.json",
    "MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R5.json",
    "METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_CLOSEOUT_DECISION.json",
    "METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_DECISION.json",
    "NO_ACTION_AUDIT_R5.json",
    "README.md",
    "SECRET_AUDIT_R5.json",
    "SOURCE_CLASS_SEPARATION_AUDIT_R5.json",
    "VSS_INPUT_PACKET_R5.json",
    "VSS_NARRATION_GUARDRAIL_REPORT_R5.json",
    "VSS_NARRATION_NORMALIZATION_REPORT_R5.json",
    "VSS_NARRATION_SIDECARS_R5.jsonl",
    "VSS_PROSE_VS_DETECTION_CONFLICT_AUDIT_R5.json",
    "VSS_RAW_RESPONSE_CAPTURE_R5.json",
    "VSS_RUNTIME_ADAPTER_CONFIG_R5.json",
    "VSS_RUNTIME_EXECUTION_REPORT_R5.json",
]

FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    ("confirmed_violation", r"\b(confirmed violation|violation confirmed)\b"),
    ("legal_or_certified_finding", r"\b(legal finding|certified finding|finding of violation)\b"),
    ("identity_or_biometric", r"\b(identity inferred|identified person|biometric|face recognition|license plate)\b"),
    ("official_case_or_ticket", r"\b(official case|official ticket|ticket created|case created)\b"),
    ("dispatch_routing_control_enforcement", r"\b(dispatch|route command|control command|enforcement|enforce)\b"),
    ("alert_or_automated_action", r"\b(alert operator to act|automated action|autonomous action)\b"),
]

SECRET_PATTERNS: list[tuple[str, str]] = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("bearer_token", r"(?i)\bbearer\s+[A-Za-z0-9_\-.]{20,}"),
    ("credential_assignment", r"(?i)\b(token|api[_-]?key|apikey|password|secret)\s*[:=]\s*[A-Za-z0-9_\-./+]{8,}"),
    ("authorization_header", r"(?i)\b(authorization|x-api-key)\s*:\s*[A-Za-z0-9_\-./+]{8,}"),
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def redact_text(value: str | None) -> str | None:
    if value is None:
        return None
    redacted = value
    redacted = re.sub(r"(?i)(token|api[_-]?key|apikey|password|secret)\s*[:=]\s*[^ \t\r\n;&]+", r"\1=<redacted>", redacted)
    redacted = re.sub(r"(?i)(authorization|x-api-key)\s*:\s*[^ \t\r\n;&]+", r"\1: <redacted>", redacted)
    redacted = re.sub(r"(?i)bearer\s+[A-Za-z0-9_\-.]+", "Bearer <redacted>", redacted)
    parsed = urllib.parse.urlsplit(redacted)
    if parsed.scheme in {"http", "https"}:
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc += f":{parsed.port}"
        return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path or "/", "", ""))
    return redacted


def contains_secret(text: str) -> bool:
    return any(re.search(pattern, text) for _name, pattern in SECRET_PATTERNS)


def snippet(text: str, limit: int = 2000) -> str:
    clean = redact_text(text) or ""
    return clean[:limit]


def str_to_bool(value: str | bool | None, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def read_zip_json(zf: zipfile.ZipFile, name: str) -> Any:
    return json.loads(zf.read(name).decode("utf-8"))


def read_zip_jsonl(zf: zipfile.ZipFile, name: str) -> list[Any]:
    return parse_jsonl_text(zf.read(name).decode("utf-8"))


def validate_r5_package(package_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "input_r5_package": str(package_path),
        "input_r5_package_exists": package_path.exists(),
        "status": "FAIL",
        "zip_entries": 0,
        "required_files_present": False,
        "missing_required_files": [],
        "json_files_parsed": 0,
        "jsonl_files_parsed": 0,
        "json_parse_failures": [],
        "jsonl_parse_failures": [],
        "jsonl_record_counts": {},
        "hash_manifest": {
            "status": "NOT_RUN",
            "manifest_file_count": 0,
            "verified": 0,
            "missing": [],
            "mismatches": [],
        },
    }
    if not package_path.exists():
        result["failure_reason"] = "Input R5 package not found."
        return result
    result["input_r5_package_sha256"] = sha256_file(package_path)

    parsed_json: dict[str, Any] = {}
    parsed_jsonl: dict[str, list[Any]] = {}
    try:
        with zipfile.ZipFile(package_path, "r") as zf:
            names = zf.namelist()
            result["zip_entries"] = len(names)
            missing_required = [name for name in REQUIRED_R5_FILES if name not in names]
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
                        rows = read_zip_jsonl(zf, name)
                        parsed_jsonl[name] = rows
                        result["jsonl_files_parsed"] += 1
                        result["jsonl_record_counts"][name] = len(rows)
                    except Exception as exc:  # noqa: BLE001
                        result["jsonl_parse_failures"].append({"file": name, "error": str(exc)})
            if "HASH_MANIFEST.json" in names:
                manifest = parsed_json.get("HASH_MANIFEST.json") or read_zip_json(zf, "HASH_MANIFEST.json")
                files = manifest.get("files", [])
                result["hash_manifest"]["manifest_file_count"] = len(files)
                for item in files:
                    name = item.get("file") or item.get("path")
                    if not name:
                        result["hash_manifest"]["missing"].append("<blank path>")
                        continue
                    if name not in names:
                        result["hash_manifest"]["missing"].append(name)
                        continue
                    actual = sha256_bytes(zf.read(name))
                    if actual != item.get("sha256"):
                        result["hash_manifest"]["mismatches"].append(
                            {"file": name, "expected": item.get("sha256"), "actual": actual}
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

    closeout = parsed_json.get("METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_CLOSEOUT_DECISION.json", {})
    truth_ok = (
        closeout.get("status") == R5_EXPECTED_STATUS
        and closeout.get("r2_candidate_observations") == 24
        and closeout.get("r2_candidate_events") == 1
        and closeout.get("structured_detection_source_class") == "sensor_inferred"
        and closeout.get("vss_is_fact_source") is False
        and closeout.get("candidate_event_modified_by_vss") is False
        and closeout.get("no_action_taken") is True
        and closeout.get("official_record_created") is False
        and closeout.get("vss_narration_records") == 0
    )
    result.update(
        {
            "r5_closeout_status": closeout.get("status"),
            "r5_runtime_status": closeout.get("runtime_status"),
            "r5_runtime_configured": bool(closeout.get("runtime_configured")),
            "vss_runtime_attempted": bool(closeout.get("vss_runtime_attempted")),
            "vss_runtime_executed": bool(closeout.get("vss_runtime_executed")),
            "vss_narration_records": closeout.get("vss_narration_records"),
            "r2_candidate_observations": closeout.get("r2_candidate_observations"),
            "r2_candidate_events": closeout.get("r2_candidate_events"),
            "structured_detection_source_class": closeout.get("structured_detection_source_class"),
            "vss_output_source_class": closeout.get("vss_output_source_class"),
            "vss_is_fact_source": closeout.get("vss_is_fact_source"),
            "candidate_event_modified_by_vss": closeout.get("candidate_event_modified_by_vss"),
            "no_action_taken": closeout.get("no_action_taken"),
            "official_record_created": closeout.get("official_record_created"),
            "r5_preserved_r2_truth": truth_ok,
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


def resolve_runtime_config(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    command_cli = args.vss_command
    endpoint_cli = args.vss_endpoint
    command_env = os.environ.get("CITYBRAIN_VSS_COMMAND")
    endpoint_env = os.environ.get("CITYBRAIN_VSS_ENDPOINT")
    timeout_env = os.environ.get("CITYBRAIN_VSS_TIMEOUT_SECONDS")
    health_env = os.environ.get("CITYBRAIN_VSS_HEALTH_PATH")
    version_env = os.environ.get("CITYBRAIN_VSS_VERSION_PATH")

    command = command_cli or command_env
    endpoint = endpoint_cli or endpoint_env
    command_source = "cli" if command_cli else ("env" if command_env else "none")
    endpoint_source = "cli" if endpoint_cli else ("env" if endpoint_env else "none")
    timeout_seconds = int(args.vss_timeout_seconds or timeout_env or 20)
    timeout_seconds = max(1, min(timeout_seconds, 300))
    health_path = args.vss_health_path or health_env or "/health"
    version_path = args.vss_version_path or version_env or "/version"
    allow_localhost_only = str_to_bool(args.allow_localhost_only, True)

    if command and endpoint:
        if command_source == "cli":
            selected_mode = "both_configured_prefer_cli"
            effective_probe = "command"
            reason = "Both command and endpoint configured; explicit CLI command takes precedence."
        elif endpoint_source == "cli":
            selected_mode = "both_configured_prefer_endpoint"
            effective_probe = "endpoint"
            reason = "Both command and endpoint configured; explicit CLI endpoint takes precedence."
        else:
            selected_mode = "both_configured_prefer_endpoint"
            effective_probe = "endpoint"
            reason = "Both configured from environment; endpoint preferred for connectivity probe."
    elif command:
        selected_mode = "command"
        effective_probe = "command"
        reason = "Command runtime configured."
    elif endpoint:
        selected_mode = "endpoint"
        effective_probe = "endpoint"
        reason = "Endpoint runtime configured."
    else:
        selected_mode = "not_configured"
        effective_probe = "not_configured"
        reason = "No command or endpoint configured."

    redacted_command = redact_text(command)
    redacted_endpoint = redact_text(endpoint)
    safe_payload = json.dumps({"command": redacted_command, "endpoint": redacted_endpoint}, sort_keys=True)
    config = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "runtime_configured": selected_mode != "not_configured",
        "selected_mode": selected_mode,
        "selected_mode_reason": reason,
        "effective_probe_mode": effective_probe,
        "config_sources": {
            "command": command_source,
            "endpoint": endpoint_source,
            "timeout_seconds": "cli" if args.vss_timeout_seconds else ("env" if timeout_env else "default"),
            "health_path": "cli" if args.vss_health_path else ("env" if health_env else "default"),
            "version_path": "cli" if args.vss_version_path else ("env" if version_env else "default"),
        },
        "redacted_command": redacted_command,
        "redacted_endpoint": redacted_endpoint,
        "redaction_applied": True,
        "secrets_present_after_redaction": contains_secret(safe_payload),
        "timeout_seconds": timeout_seconds,
        "health_path": health_path,
        "version_path": version_path,
        "allow_localhost_only": allow_localhost_only,
        "non_local_endpoint_explicitly_configured": False,
    }
    raw = {
        "command": command,
        "endpoint": endpoint,
        "effective_probe_mode": effective_probe,
        "timeout_seconds": timeout_seconds,
        "health_path": health_path,
        "version_path": version_path,
        "allow_localhost_only": allow_localhost_only,
    }
    return config, raw


def is_local_endpoint(endpoint: str | None) -> bool:
    if not endpoint:
        return False
    parsed = urllib.parse.urlsplit(endpoint)
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"} or host.startswith("127.")


def endpoint_probe_urls(endpoint: str, health_path: str, version_path: str) -> list[str]:
    parsed = urllib.parse.urlsplit(endpoint)
    base_path = parsed.path if parsed.path and parsed.path != "/" else ""
    paths = []
    for candidate in (health_path, version_path, base_path or "/"):
        if not candidate:
            continue
        if not candidate.startswith("/"):
            candidate = "/" + candidate
        if candidate not in paths:
            paths.append(candidate)
    return [urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", "")) for path in paths]


def run_probe(config: dict[str, Any], raw: dict[str, Any], output_root: Path) -> dict[str, Any]:
    mode = config["selected_mode"]
    effective = raw["effective_probe_mode"]
    report: dict[str, Any] = {
        "schema_version": PROBE_SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "attempted": False,
        "executed": False,
        "probe_status": "NOT_CONFIGURED",
        "runtime_mode": mode,
        "effective_probe_mode": effective,
        "latency_ms": None,
        "exit_code": None,
        "http_status": None,
        "stdout_snippet_ref": None,
        "stderr_snippet_ref": None,
        "response_snippet_ref": None,
        "error_summary": None,
        "probe_target_redacted": config.get("redacted_command") or config.get("redacted_endpoint"),
    }
    if effective == "not_configured":
        report["latency_ms"] = 0
        report["error_summary"] = "No VSS command or endpoint configured."
        return report

    if effective == "command":
        command = raw["command"]
        start = time.perf_counter()
        report["attempted"] = True
        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=raw["timeout_seconds"],
            )
            report["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            stdout_snippet = snippet(completed.stdout or "")
            stderr_snippet = snippet(completed.stderr or "")
            if stdout_snippet:
                stdout_path = output_root / "VSS_RUNTIME_STDOUT_SNIPPET_R6.txt"
                write_text(stdout_path, stdout_snippet)
                report["stdout_snippet_ref"] = rel(stdout_path)
            if stderr_snippet:
                stderr_path = output_root / "VSS_RUNTIME_STDERR_SNIPPET_R6.txt"
                write_text(stderr_path, stderr_snippet)
                report["stderr_snippet_ref"] = rel(stderr_path)
            report["exit_code"] = completed.returncode
            report["executed"] = completed.returncode == 0
            report["probe_status"] = "PASS" if completed.returncode == 0 else "FAILED"
            if completed.returncode != 0:
                report["error_summary"] = f"Command probe exited with code {completed.returncode}."
        except subprocess.TimeoutExpired as exc:
            report["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            report["probe_status"] = "TIMEOUT"
            report["error_summary"] = "Command probe timed out."
            stdout_snippet = snippet(exc.stdout or "")
            stderr_snippet = snippet(exc.stderr or "")
            if stdout_snippet:
                stdout_path = output_root / "VSS_RUNTIME_STDOUT_SNIPPET_R6.txt"
                write_text(stdout_path, stdout_snippet)
                report["stdout_snippet_ref"] = rel(stdout_path)
            if stderr_snippet:
                stderr_path = output_root / "VSS_RUNTIME_STDERR_SNIPPET_R6.txt"
                write_text(stderr_path, stderr_snippet)
                report["stderr_snippet_ref"] = rel(stderr_path)
        except Exception as exc:  # noqa: BLE001
            report["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            report["probe_status"] = "ERROR"
            report["error_summary"] = f"Command probe error: {exc}"
        return report

    if effective == "endpoint":
        endpoint = raw["endpoint"]
        if config.get("allow_localhost_only") and not is_local_endpoint(endpoint):
            report["latency_ms"] = 0
            report["probe_status"] = "FAILED"
            report["error_summary"] = "Endpoint is non-local and allow_localhost_only is true; probe not attempted."
            return report
        config["non_local_endpoint_explicitly_configured"] = not is_local_endpoint(endpoint)
        urls = endpoint_probe_urls(endpoint, raw["health_path"], raw["version_path"])
        last_error = None
        for url in urls:
            start = time.perf_counter()
            report["attempted"] = True
            request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json,text/plain,*/*"})
            try:
                with urllib.request.urlopen(request, timeout=raw["timeout_seconds"]) as response:  # noqa: S310
                    body = response.read().decode("utf-8", errors="replace")
                    report["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
                    report["http_status"] = int(response.status)
                    report["executed"] = 200 <= int(response.status) < 300
                    report["probe_status"] = "PASS" if report["executed"] else "FAILED"
                    report["probed_url_redacted"] = redact_text(url)
                    if body:
                        response_path = output_root / "VSS_RUNTIME_RESPONSE_SNIPPET_R6.txt"
                        write_text(response_path, snippet(body))
                        report["response_snippet_ref"] = rel(response_path)
                    return report
            except TimeoutError:
                report["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
                report["probe_status"] = "TIMEOUT"
                last_error = "Endpoint probe timed out."
            except urllib.error.HTTPError as exc:
                report["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
                report["http_status"] = int(exc.code)
                report["probe_status"] = "FAILED"
                last_error = f"HTTP error {exc.code}."
            except urllib.error.URLError as exc:
                report["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
                report["probe_status"] = "FAILED"
                last_error = f"Endpoint probe failed: {exc.reason}"
        report["error_summary"] = last_error or "Endpoint probe failed."
        return report

    report["latency_ms"] = 0
    report["probe_status"] = "ERROR"
    report["error_summary"] = f"Unsupported effective probe mode: {effective}"
    return report


def scan_for_forbidden_text(output_root: Path) -> list[dict[str, str]]:
    findings = []
    for path in sorted(output_root.iterdir(), key=lambda p: p.name):
        if path.name not in {
            "VSS_RUNTIME_STDOUT_SNIPPET_R6.txt",
            "VSS_RUNTIME_STDERR_SNIPPET_R6.txt",
            "VSS_RUNTIME_RESPONSE_SNIPPET_R6.txt",
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for family, pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                findings.append({"file": path.name, "family": family})
    return findings


def write_audits(output_root: Path, validation: dict[str, Any], config: dict[str, Any], probe: dict[str, Any]) -> dict[str, str]:
    source_status = "PASS" if validation.get("structured_detection_source_class") == "sensor_inferred" else "FAIL"
    write_json(
        output_root / "SOURCE_CLASS_SEPARATION_AUDIT_R6.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": source_status,
            "structured_detection_source_class": "sensor_inferred",
            "vss_output_source_class": "model_generated_narrative",
            "connectivity_metadata_source_class": "runtime_configuration_evidence",
            "vss_is_fact_source": False,
            "vss_narration_records": 0,
        },
    )

    forbidden = scan_for_forbidden_text(output_root)
    claim_status = "PASS" if not forbidden else "FAIL"
    write_json(
        output_root / "CLAIM_BOUNDARY_AUDIT_R6.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": claim_status,
            "forbidden_claim_findings": forbidden,
            "fabricated_narration": False,
            "vss_narration_records": 0,
        },
    )

    write_json(
        output_root / "NO_ACTION_AUDIT_R6.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": "PASS",
            "no_action_taken": True,
            "official_record_created": False,
            "candidate_event_modified_by_vss": False,
            "dispatch_or_control_created": False,
        },
    )

    guardrail_status = "PASS" if claim_status == "PASS" and not config.get("secrets_present_after_redaction") else "FAIL"
    write_json(
        output_root / "VSS_CONFIGURATION_GUARDRAIL_REPORT_R6.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": guardrail_status,
            "runtime_configured": config["runtime_configured"],
            "selected_mode": config["selected_mode"],
            "probe_status": probe["probe_status"],
            "no_narration_fabricated": True,
            "vss_narration_records": 0,
            "redaction_applied": config["redaction_applied"],
            "secrets_present_after_redaction": config["secrets_present_after_redaction"],
            "forbidden_claim_findings": forbidden,
        },
    )

    check_status = "PASS" if probe["probe_status"] == "PASS" else "PARTIAL"
    if guardrail_status == "FAIL" or source_status == "FAIL":
        check_status = "FAIL"
    write_json(
        output_root / "CHECK_RUNTIME_CONNECTIVITY_REPORT_R6.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": check_status,
            "dimension_results": [
                {"dimension": "R5 package validation", "status": validation.get("status"), "value": validation.get("r5_closeout_status")},
                {"dimension": "runtime configured", "status": "PASS" if config["runtime_configured"] else "PARTIAL", "value": config["selected_mode"]},
                {"dimension": "probe attempted", "status": "PASS" if probe["attempted"] else "PARTIAL", "value": probe["attempted"]},
                {"dimension": "probe executed", "status": "PASS" if probe["executed"] else "PARTIAL", "value": probe["executed"]},
                {"dimension": "probe status", "status": probe["probe_status"], "value": probe.get("error_summary")},
                {"dimension": "secret redaction", "status": "PASS" if not config["secrets_present_after_redaction"] else "FAIL", "value": "redacted"},
                {"dimension": "source-class separation", "status": source_status, "value": "sensor_inferred / model_generated_narrative / runtime_configuration_evidence"},
                {"dimension": "no-action boundary", "status": "PASS", "value": "no_action_taken=true"},
            ],
        },
    )
    return {
        "source_class": source_status,
        "claim_boundary": claim_status,
        "no_action": "PASS",
        "configuration_guardrail": guardrail_status,
        "check_runtime_connectivity": check_status,
    }


def write_secret_audit(output_root: Path) -> str:
    findings: list[dict[str, str]] = []
    for path in sorted(output_root.iterdir(), key=lambda p: p.name):
        if path.name == "SECRET_AUDIT_R6.json":
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                findings.append({"file": path.name, "pattern": name})
    status = "PASS" if not findings else "FAIL"
    write_json(output_root / "SECRET_AUDIT_R6.json", {"status": status, "findings": findings})
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
        output_root / "JSON_PARSE_REPORT_R6.json",
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
    config: dict[str, Any],
    probe: dict[str, Any],
    audits: dict[str, str],
    json_status: str = "PENDING",
    hash_status: str = "PENDING",
) -> str:
    if validation.get("status") != "PASS":
        return FAIL_STATUS
    if json_status == "FAIL" or hash_status == "FAIL" or any(status == "FAIL" for status in audits.values()):
        return FAIL_STATUS
    if not config["runtime_configured"]:
        return PARTIAL_NOT_CONFIGURED_STATUS
    if probe["attempted"] and probe["executed"] and probe["probe_status"] == "PASS":
        return PASS_STATUS
    return PARTIAL_CONNECTIVITY_FAILED_STATUS


def write_readiness(output_root: Path, config: dict[str, Any], probe: dict[str, Any], status: str) -> None:
    write_json(
        output_root / "VSS_RUNTIME_READINESS_DECISION_R6.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_name": TASK_NAME,
            "status": "READY" if status == PASS_STATUS else "NOT_READY",
            "final_status": status,
            "runtime_configured": config["runtime_configured"],
            "runtime_mode": config["selected_mode"],
            "probe_attempted": probe["attempted"],
            "probe_executed": probe["executed"],
            "probe_status": probe["probe_status"],
            "next_when_ready": "MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7",
        },
    )


def write_decisions(
    output_root: Path,
    status: str,
    validation: dict[str, Any],
    config: dict[str, Any],
    probe: dict[str, Any],
    audits: dict[str, str],
    json_status: str = "PENDING",
    hash_status: str = "PENDING",
) -> None:
    decision = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": status,
        "runtime_configured": config["runtime_configured"],
        "runtime_mode": config["selected_mode"],
        "probe_attempted": probe["attempted"],
        "probe_executed": probe["executed"],
        "probe_status": probe["probe_status"],
        "structured_detection_source_class": "sensor_inferred",
        "vss_output_source_class": "model_generated_narrative",
        "connectivity_metadata_source_class": "runtime_configuration_evidence",
        "vss_is_fact_source": False,
        "vss_narration_records": 0,
        "candidate_event_modified_by_vss": False,
        "no_action_taken": True,
        "official_record_created": False,
        "input_r5_package_validation_status": validation.get("status"),
        "r5_closeout_status": validation.get("r5_closeout_status"),
        "audits": {**audits, "json_parse": json_status, "hash_manifest": hash_status},
        "limitations": [
            "R6 validates runtime configuration/connectivity only; it does not prove narration quality.",
            "R6 emits zero narration records and does not modify candidate observations or events.",
            "DeepStream/Metropolis metadata remains sensor_inferred.",
            "VSS output remains model_generated_narrative and is not a fact source.",
            "No official record, ticket, dispatch, control, enforcement, alert-command, or action is created.",
        ],
        "validation_package_ref": PACKAGE_NAME,
    }
    write_json(output_root / "METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_DECISION.json", decision)
    write_json(output_root / "METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_CLOSEOUT_DECISION.json", decision)


def write_readme(output_root: Path, status: str, config: dict[str, Any], probe: dict[str, Any]) -> None:
    write_text(
        output_root / "README.md",
        f"""# Metropolis/VSS Runtime Configuration And Connectivity R6

Status: {status}

R6 checks whether a VSS runtime command or endpoint is configured and reachable. It does not
perform a narration quality run and emits zero narration records.

Runtime configured: {str(config["runtime_configured"]).lower()}
Runtime mode: {config["selected_mode"]}
Probe attempted/executed: {str(probe["attempted"]).lower()}/{str(probe["executed"]).lower()}
Probe status: {probe["probe_status"]}

Source-class boundary:
- DeepStream/Metropolis structured metadata = sensor_inferred
- VSS runtime output = model_generated_narrative
- R6 connectivity metadata = runtime_configuration_evidence

No action was taken and no official record was created.
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
    parser.add_argument("--input-r5-package", type=Path, default=DEFAULT_R5_PACKAGE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--vss-command")
    parser.add_argument("--vss-endpoint")
    parser.add_argument("--vss-timeout-seconds", type=int)
    parser.add_argument("--vss-health-path")
    parser.add_argument("--vss-version-path")
    parser.add_argument("--allow-localhost-only", default="true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    reset_output_root(output_root)

    validation = validate_r5_package(args.input_r5_package.resolve())
    write_json(output_root / "R5_PACKAGE_VALIDATION_R6.json", validation)

    config, raw_config = resolve_runtime_config(args)
    write_json(output_root / "VSS_RUNTIME_CONFIGURATION_R6.json", config)

    probe = run_probe(config, raw_config, output_root)
    write_json(output_root / "VSS_RUNTIME_CONNECTIVITY_PROBE_R6.json", probe)

    audits = write_audits(output_root, validation, config, probe)
    audits["secret"] = write_secret_audit(output_root)
    initial_status = decide_status(validation, config, probe, audits)
    write_readiness(output_root, config, probe, initial_status)
    write_decisions(output_root, initial_status, validation, config, probe, audits)
    write_readme(output_root, initial_status, config, probe)

    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    final_status = decide_status(validation, config, probe, audits, json_status, hash_status)
    write_readiness(output_root, config, probe, final_status)
    write_decisions(output_root, final_status, validation, config, probe, audits, json_status, hash_status)
    write_readme(output_root, final_status, config, probe)
    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    create_package_zip(output_root)

    print(f"Final status: {final_status}")
    print(f"Runner: {rel(Path(__file__).resolve())}")
    print(f"Output root: {rel(output_root)}")
    print(f"Freeze ZIP: {rel(output_root / PACKAGE_NAME)}")
    print(f"Runtime configured/mode: {str(config['runtime_configured']).lower()}/{config['selected_mode']}")
    print(f"Probe attempted/executed/status: {str(probe['attempted']).lower()}/{str(probe['executed']).lower()}/{probe['probe_status']}")
    print("VSS narration records emitted: 0")
    print(f"JSON parse: {json_status}")
    print(f"Hash manifest: {hash_status}")
    return 0 if final_status.startswith(("PASS_", "PARTIAL_")) and json_status == "PASS" and hash_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
