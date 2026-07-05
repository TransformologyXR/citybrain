#!/usr/bin/env python3
"""Run the R6B configured VSS runtime connectivity rerun gate."""

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
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-CONFIGURED-RERUN-R6B"
SCHEMA_VERSION = "metropolis-vss-runtime-configured-rerun-r6b.v1"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_runtime_configured_rerun_r6b"
DEFAULT_R6_ZIP = (
    REPO_ROOT
    / "outputs"
    / "main_citybrain_metropolis_vss_runtime_configuration_and_connectivity_r6"
    / "METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_PACKAGE.zip"
)
PACKAGE_NAME = "METROPOLIS_VSS_RUNTIME_CONFIGURED_RERUN_R6B_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6B"
PARTIAL_NOT_CONFIGURED = "PARTIAL_METROPOLIS_VSS_RUNTIME_NOT_CONFIGURED_R6B_CONNECTIVITY_CONTRACT_READY"
PARTIAL_UNREACHABLE = "PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_BUT_UNREACHABLE_R6B"
PARTIAL_TIMED_OUT = "PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_BUT_TIMED_OUT_R6B"
PARTIAL_UNSUPPORTED = "PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_BUT_UNSUPPORTED_PROTOCOL_R6B"
FAIL_SECRET_OR_BOUNDARY = "FAIL_METROPOLIS_VSS_RUNTIME_CONFIGURATION_SECRET_OR_BOUNDARY_RISK_R6B"
FAIL_OVERCLAIMED = "FAIL_METROPOLIS_VSS_RUNTIME_PROBE_OVERCLAIMED_R6B"
FAIL_MUTATED_EVENT = "FAIL_METROPOLIS_VSS_RUNTIME_MUTATED_CANDIDATE_EVENT_R6B"
FAIL_SOURCE_CLASS = "FAIL_METROPOLIS_VSS_SOURCE_CLASS_SEPARATION_RISK_R6B"

R6_EXPECTED_STATUS = "PARTIAL_METROPOLIS_VSS_RUNTIME_NOT_CONFIGURED_R6_CONNECTIVITY_CONTRACT_READY"
SOURCE_BOUNDARY = {
    "deepstream_metropolis": "sensor_inferred",
    "vss": "model_generated_narrative_only_not_fact_source",
}

REQUIRED_R6_FILES = [
    "CHECK_RUNTIME_CONNECTIVITY_REPORT_R6.json",
    "CLAIM_BOUNDARY_AUDIT_R6.json",
    "HASH_MANIFEST.json",
    "JSON_PARSE_REPORT_R6.json",
    "METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_CLOSEOUT_DECISION.json",
    "METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_DECISION.json",
    "NO_ACTION_AUDIT_R6.json",
    "R5_PACKAGE_VALIDATION_R6.json",
    "README.md",
    "SECRET_AUDIT_R6.json",
    "SOURCE_CLASS_SEPARATION_AUDIT_R6.json",
    "VSS_CONFIGURATION_GUARDRAIL_REPORT_R6.json",
    "VSS_RUNTIME_CONFIGURATION_R6.json",
    "VSS_RUNTIME_CONNECTIVITY_PROBE_R6.json",
    "VSS_RUNTIME_READINESS_DECISION_R6.json",
]

SECRET_PATTERNS: list[tuple[str, str]] = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("bearer_token", r"(?i)\bbearer\s+[A-Za-z0-9_\-.]{20,}"),
    ("credential_assignment", r"(?i)\b(token|api[_-]?key|apikey|password|secret|auth|cookie)\s*[:=]\s*[A-Za-z0-9_\-./+]{8,}"),
    ("header_secret", r"(?i)\b(authorization|x-api-key)\s*:\s*[A-Za-z0-9_\-./+]{8,}"),
    ("private_key", r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
]

BOUNDARY_RUNTIME_PATTERNS: list[tuple[str, str]] = [
    ("confirmed_violation", r"\bconfirmed violation\b|\bviolation confirmed\b"),
    ("legal_finding", r"\blegal finding\b|\bcertified finding\b"),
    ("identity_biometric", r"\bidentity\b|\bbiometric\b|\bface recognition\b|\blicen[cs]e plate\b"),
    ("official_case_ticket", r"\bofficial case\b|\bofficial ticket\b|\bticket created\b|\bcase created\b"),
    ("action_command", r"\bdispatch\b|\brouting\b|\bcontrol command\b|\benforcement\b|\bautomated action\b"),
    ("fact_source", r"\bfact source\b|\bsource of truth\b|\bvss detected\b|\bvss confirms\b"),
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


def reset_output_root(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def redact_text(value: str | None, enabled: bool = True) -> str | None:
    if value is None:
        return None
    if not enabled:
        return value
    redacted = value
    redacted = re.sub(r"(?i)(token|api[_-]?key|apikey|password|secret|auth|cookie)\s*[:=]\s*[^ \t\r\n;&]+", r"\1=<redacted>", redacted)
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


def safe_excerpt(text: str, limit: int = 1600) -> str:
    return (redact_text(text, True) or "")[:limit]


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


def validate_r6_zip(r6_zip: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "r6_zip": str(r6_zip),
        "r6_zip_exists": r6_zip.exists(),
        "r6_zip_sha256": None,
        "status": "FAIL",
        "zip_entries": 0,
        "required_files_present": False,
        "missing_required_files": [],
        "json_files_parsed": 0,
        "jsonl_files_parsed": 0,
        "json_parse_failures": [],
        "jsonl_parse_failures": [],
        "hash_manifest": {"status": "NOT_RUN", "manifest_file_count": 0, "verified": 0, "missing": [], "mismatches": []},
    }
    if not r6_zip.exists():
        result["failure_reason"] = "R6 freeze ZIP not found."
        return result
    result["r6_zip_sha256"] = sha256_file(r6_zip)
    parsed_json: dict[str, Any] = {}
    parsed_jsonl: dict[str, list[Any]] = {}
    try:
        with zipfile.ZipFile(r6_zip, "r") as zf:
            names = zf.namelist()
            result["zip_entries"] = len(names)
            missing = [name for name in REQUIRED_R6_FILES if name not in names]
            result["missing_required_files"] = missing
            result["required_files_present"] = not missing
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
            manifest = parsed_json.get("HASH_MANIFEST.json", {})
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

    closeout = parsed_json.get("METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_CLOSEOUT_DECISION.json", {})
    r5_validation = parsed_json.get("R5_PACKAGE_VALIDATION_R6.json", {})
    r6_truth_ok = (
        closeout.get("status") == R6_EXPECTED_STATUS
        and closeout.get("runtime_configured") is False
        and closeout.get("probe_attempted") is False
        and closeout.get("probe_executed") is False
        and closeout.get("probe_status") == "NOT_CONFIGURED"
        and closeout.get("vss_narration_records") == 0
        and closeout.get("vss_is_fact_source") is False
        and closeout.get("candidate_event_modified_by_vss") is False
        and r5_validation.get("status") == "PASS"
        and r5_validation.get("r2_candidate_observations") == 24
        and r5_validation.get("r2_candidate_events") == 1
    )
    result.update(
        {
            "r6_closeout_status": closeout.get("status"),
            "r6_runtime_configured": closeout.get("runtime_configured"),
            "r6_probe_status": closeout.get("probe_status"),
            "r6_probe_attempted": closeout.get("probe_attempted"),
            "r6_probe_executed": closeout.get("probe_executed"),
            "r5_validation_status": r5_validation.get("status"),
            "r2_candidate_observations": r5_validation.get("r2_candidate_observations"),
            "r2_candidate_events": r5_validation.get("r2_candidate_events"),
            "r6_preserved_lineage_truth": r6_truth_ok,
            "_closeout": closeout,
            "_r5_validation": r5_validation,
        }
    )
    result["status"] = (
        "PASS"
        if result["required_files_present"]
        and not result["json_parse_failures"]
        and not result["jsonl_parse_failures"]
        and result["hash_manifest"]["status"] == "PASS"
        and r6_truth_ok
        else "FAIL"
    )
    return result


def public_validation(validation: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in validation.items() if not k.startswith("_")}


def resolve_config(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    command_cli = args.vss_command
    endpoint_cli = args.vss_endpoint
    command_env = os.environ.get("CITYBRAIN_VSS_COMMAND")
    endpoint_env = os.environ.get("CITYBRAIN_VSS_ENDPOINT")
    timeout_env = os.environ.get("CITYBRAIN_VSS_TIMEOUT_SECONDS")
    probe_mode_env = os.environ.get("CITYBRAIN_VSS_PROBE_MODE")
    health_path_env = os.environ.get("CITYBRAIN_VSS_HEALTH_PATH")
    redact_env = os.environ.get("CITYBRAIN_VSS_REDACT_CONFIG")

    command = command_cli or command_env
    endpoint = endpoint_cli or endpoint_env
    redact_enabled = str_to_bool(args.redact_runtime_config if args.redact_runtime_config is not None else redact_env, True)
    timeout = int(args.vss_timeout_seconds or timeout_env or 20)
    timeout = max(1, min(timeout, 300))
    health_path = args.vss_health_path or health_path_env or "/health"
    probe_mode = args.vss_probe_mode or probe_mode_env or "connectivity_only"

    command_source = "cli" if command_cli else ("environment" if command_env else "none")
    endpoint_source = "cli" if endpoint_cli else ("environment" if endpoint_env else "none")
    if command and endpoint:
        runtime_mode = "command" if command_source == "cli" else "endpoint"
        configured_via = "mixed"
        selected_reason = "Both command and endpoint configured; CLI command wins when present, otherwise endpoint wins."
    elif command:
        runtime_mode = "command"
        configured_via = command_source
        selected_reason = "Command configured."
    elif endpoint:
        runtime_mode = "endpoint"
        configured_via = endpoint_source
        selected_reason = "Endpoint configured."
    else:
        runtime_mode = "none"
        configured_via = "none"
        selected_reason = "No command or endpoint configured."

    redacted_command = redact_text(command, redact_enabled)
    redacted_endpoint = redact_text(endpoint, redact_enabled)
    redacted_payload = json.dumps({"command": redacted_command, "endpoint": redacted_endpoint}, sort_keys=True)
    config = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "runtime_configured": runtime_mode in {"command", "endpoint"},
        "runtime_mode": runtime_mode,
        "configured_via": configured_via,
        "config_sources": {
            "command": command_source,
            "endpoint": endpoint_source,
            "timeout_seconds": "cli" if args.vss_timeout_seconds else ("environment" if timeout_env else "default"),
            "probe_mode": "cli" if args.vss_probe_mode else ("environment" if probe_mode_env else "default"),
            "health_path": "cli" if args.vss_health_path else ("environment" if health_path_env else "default"),
            "redaction": "cli" if args.redact_runtime_config is not None else ("environment" if redact_env else "default"),
        },
        "redacted_command": redacted_command,
        "redacted_endpoint": redacted_endpoint,
        "redaction_applied": redact_enabled,
        "secrets_present_after_redaction": contains_secret(redacted_payload),
        "timeout_seconds": timeout,
        "probe_mode": probe_mode,
        "health_path": health_path,
        "selected_mode_reason": selected_reason,
        "source_boundary": SOURCE_BOUNDARY,
    }
    raw = {
        "command": command,
        "endpoint": endpoint,
        "runtime_mode": runtime_mode,
        "timeout_seconds": timeout,
        "health_path": health_path,
    }
    return config, raw


def endpoint_probe_url(endpoint: str, health_path: str) -> str | None:
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"}:
        return None
    path = health_path or parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def run_probe(config: dict[str, Any], raw: dict[str, Any], output_root: Path) -> dict[str, Any]:
    logs_dir = output_root / "logs"
    runtime_mode = config["runtime_mode"]
    probe = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "runtime_configured": config["runtime_configured"],
        "runtime_mode": runtime_mode,
        "configured_via": config["configured_via"],
        "probe_attempted": False,
        "probe_executed": False,
        "probe_status": "NOT_CONFIGURED",
        "timeout_seconds": config["timeout_seconds"],
        "latency_ms": None,
        "exit_code": None,
        "http_status": None,
        "stdout_excerpt_ref": None,
        "stderr_excerpt_ref": None,
        "response_excerpt_ref": None,
        "stdout_length": 0,
        "stderr_length": 0,
        "response_length": 0,
        "content_type": None,
        "error_summary": None,
        "redaction_applied": config["redaction_applied"],
        "source_boundary": SOURCE_BOUNDARY,
    }
    if runtime_mode == "none":
        probe["latency_ms"] = 0
        probe["error_summary"] = "No VSS command or endpoint configured."
        return probe

    if runtime_mode == "command":
        probe["probe_attempted"] = True
        start = time.perf_counter()
        try:
            completed = subprocess.run(
                raw["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=config["timeout_seconds"],
            )
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["exit_code"] = completed.returncode
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            probe["stdout_length"] = len(stdout)
            probe["stderr_length"] = len(stderr)
            if stdout:
                path = logs_dir / "vss_probe_stdout_excerpt.txt"
                write_text(path, safe_excerpt(stdout))
                probe["stdout_excerpt_ref"] = rel(path)
            if stderr:
                path = logs_dir / "vss_probe_stderr_excerpt.txt"
                write_text(path, safe_excerpt(stderr))
                probe["stderr_excerpt_ref"] = rel(path)
            probe["probe_executed"] = completed.returncode == 0
            probe["probe_status"] = "SUCCESS" if completed.returncode == 0 else "UNREACHABLE"
            if completed.returncode != 0:
                probe["error_summary"] = f"Command exited with code {completed.returncode}."
        except subprocess.TimeoutExpired as exc:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "TIMEOUT"
            probe["error_summary"] = "Command probe timed out."
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if stdout:
                path = logs_dir / "vss_probe_stdout_excerpt.txt"
                write_text(path, safe_excerpt(stdout))
                probe["stdout_excerpt_ref"] = rel(path)
                probe["stdout_length"] = len(stdout)
            if stderr:
                path = logs_dir / "vss_probe_stderr_excerpt.txt"
                write_text(path, safe_excerpt(stderr))
                probe["stderr_excerpt_ref"] = rel(path)
                probe["stderr_length"] = len(stderr)
        except Exception as exc:  # noqa: BLE001
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "ERROR"
            probe["error_summary"] = f"Command probe error: {exc}"
        return probe

    if runtime_mode == "endpoint":
        url = endpoint_probe_url(raw["endpoint"], config["health_path"])
        if url is None:
            probe["latency_ms"] = 0
            probe["probe_status"] = "UNSUPPORTED_PROTOCOL"
            probe["error_summary"] = "Endpoint scheme is not http or https."
            return probe
        probe["probe_attempted"] = True
        start = time.perf_counter()
        request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json,text/plain,*/*"})
        try:
            with urllib.request.urlopen(request, timeout=config["timeout_seconds"]) as response:  # noqa: S310
                body = response.read().decode("utf-8", errors="replace")
                probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
                probe["http_status"] = int(response.status)
                probe["content_type"] = response.headers.get("Content-Type")
                probe["response_length"] = len(body)
                probe["probe_executed"] = 200 <= int(response.status) < 300
                probe["probe_status"] = "SUCCESS" if probe["probe_executed"] else "UNREACHABLE"
                if body:
                    path = logs_dir / "vss_probe_response_excerpt.txt"
                    write_text(path, safe_excerpt(body))
                    probe["response_excerpt_ref"] = rel(path)
        except TimeoutError:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "TIMEOUT"
            probe["error_summary"] = "Endpoint probe timed out."
        except urllib.error.HTTPError as exc:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["http_status"] = int(exc.code)
            probe["probe_status"] = "UNREACHABLE"
            probe["error_summary"] = f"HTTP error {exc.code}."
        except urllib.error.URLError as exc:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "UNREACHABLE"
            probe["error_summary"] = f"Endpoint probe failed: {exc.reason}"
        except Exception as exc:  # noqa: BLE001
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "ERROR"
            probe["error_summary"] = f"Endpoint probe error: {exc}"
        return probe

    probe["latency_ms"] = 0
    probe["probe_status"] = "UNSUPPORTED_PROTOCOL"
    probe["error_summary"] = f"Unsupported runtime mode: {runtime_mode}"
    return probe


def runtime_excerpt_findings(output_root: Path) -> list[dict[str, str]]:
    findings = []
    logs_dir = output_root / "logs"
    if not logs_dir.exists():
        return findings
    for path in logs_dir.iterdir():
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for family, pattern in BOUNDARY_RUNTIME_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                findings.append({"file": rel(path), "family": family})
    return findings


def write_audits(output_root: Path, config: dict[str, Any], probe: dict[str, Any], lineage: dict[str, Any]) -> dict[str, str]:
    runtime_boundary_findings = runtime_excerpt_findings(output_root)
    source_status = "PASS"
    if lineage.get("r2_candidate_observations") != 24 or lineage.get("r2_candidate_events") != 1:
        source_status = "FAIL"
    write_json(
        output_root / "SOURCE_CLASS_SEPARATION_AUDIT_R6B.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": source_status,
            "deepstream_metropolis": "sensor_inferred",
            "vss": "model_generated_narrative_only_not_fact_source",
            "vss_is_fact_source": False,
            "vss_narration_records": 0,
            "candidate_event_modified_by_vss": False,
        },
    )

    claim_status = "PASS" if not runtime_boundary_findings else "FAIL"
    write_json(
        output_root / "CLAIM_BOUNDARY_AUDIT_R6B.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": claim_status,
            "runtime_excerpt_findings": runtime_boundary_findings,
            "fabricated_narration": False,
            "vss_narration_records": 0,
        },
    )
    write_json(
        output_root / "NO_ACTION_AUDIT_R6B.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": "PASS",
            "no_action_taken": True,
            "official_record_created": False,
            "candidate_event_modified_by_vss": False,
            "dispatch_or_control_created": False,
        },
    )
    config_audit_status = "PASS" if config["redaction_applied"] and not config["secrets_present_after_redaction"] else "FAIL"
    write_json(
        output_root / "RUNTIME_CONFIGURATION_AUDIT_R6B.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": config_audit_status,
            "runtime_configured": config["runtime_configured"],
            "runtime_mode": config["runtime_mode"],
            "configured_via": config["configured_via"],
            "redaction_applied": config["redaction_applied"],
            "secrets_present_after_redaction": config["secrets_present_after_redaction"],
            "probe_status": probe["probe_status"],
            "connectivity_only": True,
        },
    )
    return {
        "runtime_configuration": config_audit_status,
        "source_class": source_status,
        "claim_boundary": claim_status,
        "no_action": "PASS",
    }


def write_secret_audit(output_root: Path) -> str:
    findings: list[dict[str, str]] = []
    for path in sorted(output_root.rglob("*"), key=lambda p: str(p)):
        if not path.is_file() or path.name == "SECRET_AUDIT_R6B.json":
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                findings.append({"file": rel(path), "pattern": name})
    status = "PASS" if not findings else "FAIL"
    write_json(output_root / "SECRET_AUDIT_R6B.json", {"status": status, "findings": findings})
    return status


def build_lineage(validation: dict[str, Any]) -> dict[str, Any]:
    lineage = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "lineage_preserved": {
            "r2_object_metadata_export": validation.get("r2_candidate_observations") == 24,
            "r3_guarded_partial": True,
            "r4_runtime_integration_partial": True,
            "r5_configured_smoke_partial": True,
            "r6_configuration_connectivity_partial": validation.get("r6_closeout_status") == R6_EXPECTED_STATUS,
        },
        "r6_package": {
            "path": validation.get("r6_zip"),
            "sha256": validation.get("r6_zip_sha256"),
            "status": validation.get("r6_closeout_status"),
            "hash_manifest": validation.get("hash_manifest"),
        },
        "r5_validation_status": validation.get("r5_validation_status"),
        "r2_candidate_observations": validation.get("r2_candidate_observations"),
        "r2_candidate_events": validation.get("r2_candidate_events"),
        "candidate_event_modified_by_vss": False,
        "vss_narration_records": 0,
        "vss_is_fact_source": False,
    }
    return lineage


def decide_status(validation: dict[str, Any], config: dict[str, Any], probe: dict[str, Any], audits: dict[str, str], json_status: str = "PENDING", hash_status: str = "PENDING") -> str:
    if validation.get("status") != "PASS":
        return FAIL_SOURCE_CLASS
    if audits.get("secret") == "FAIL" or audits.get("runtime_configuration") == "FAIL":
        return FAIL_SECRET_OR_BOUNDARY
    if audits.get("claim_boundary") == "FAIL":
        return FAIL_OVERCLAIMED
    if audits.get("source_class") == "FAIL":
        return FAIL_SOURCE_CLASS
    if json_status == "FAIL" or hash_status == "FAIL":
        return FAIL_SECRET_OR_BOUNDARY
    if not config["runtime_configured"]:
        return PARTIAL_NOT_CONFIGURED
    if probe["probe_status"] == "SUCCESS" and probe["probe_attempted"] and probe["probe_executed"]:
        return PASS_STATUS
    if probe["probe_status"] == "TIMEOUT":
        return PARTIAL_TIMED_OUT
    if probe["probe_status"] == "UNSUPPORTED_PROTOCOL":
        return PARTIAL_UNSUPPORTED
    return PARTIAL_UNREACHABLE


def write_closeout(output_root: Path, status: str, config: dict[str, Any], probe: dict[str, Any], lineage: dict[str, Any], audits: dict[str, str], json_status: str = "PENDING", hash_status: str = "PENDING") -> None:
    closeout = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": status,
        "runtime_configured": config["runtime_configured"],
        "runtime_mode": config["runtime_mode"],
        "configured_via": config["configured_via"],
        "probe_attempted": probe["probe_attempted"],
        "probe_executed": probe["probe_executed"],
        "probe_status": probe["probe_status"],
        "redaction_applied": config["redaction_applied"],
        "source_boundary": SOURCE_BOUNDARY,
        "vss_is_fact_source": False,
        "vss_narration_records": 0,
        "candidate_event_modified_by_vss": False,
        "no_action_taken": True,
        "official_record_created": False,
        "lineage_summary": {
            "r2_candidate_observations": lineage.get("r2_candidate_observations"),
            "r2_candidate_events": lineage.get("r2_candidate_events"),
            "r6_package_status": lineage.get("r6_package", {}).get("status"),
        },
        "audits": {**audits, "json_parse": json_status, "hash_manifest": hash_status},
        "limitations": [
            "R6B is a connectivity gate only; it does not generate or validate VSS narration.",
            "No candidate observations or candidate events are modified.",
            "PASS requires an explicit real VSS command or endpoint supplied by CLI or environment.",
            "VSS remains model_generated_narrative only and is not a fact source.",
        ],
        "validation_package_ref": PACKAGE_NAME,
    }
    write_json(output_root / "R6B_CLOSEOUT_DECISION.json", closeout)


def write_readme(output_root: Path, status: str, config: dict[str, Any], probe: dict[str, Any]) -> None:
    write_text(
        output_root / "README.md",
        f"""# Metropolis/VSS Runtime Configured Rerun R6B

Status: {status}

R6B reruns the runtime configuration/connectivity gate. It does not generate VSS
narration, does not upload media, and does not modify candidate observations/events.

Runtime configured: {str(config["runtime_configured"]).lower()}
Runtime mode: {config["runtime_mode"]}
Configured via: {config["configured_via"]}
Probe attempted/executed/status: {str(probe["probe_attempted"]).lower()}/{str(probe["probe_executed"]).lower()}/{probe["probe_status"]}
VSS narration records emitted: 0

Source boundary:
- DeepStream / Metropolis structured metadata = sensor_inferred
- VSS runtime text = model_generated_narrative only, and only in later narration tasks
""",
    )


def validate_json_outputs(output_root: Path) -> str:
    failures: list[dict[str, str]] = []
    json_count = 0
    for path in sorted(output_root.rglob("*"), key=lambda p: str(p)):
        if not path.is_file() or path.name == PACKAGE_NAME:
            continue
        if path.suffix.lower() == ".json":
            json_count += 1
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                failures.append({"file": rel(path), "error": str(exc)})
    status = "PASS" if not failures else "FAIL"
    write_json(
        output_root / "R6B_JSON_PARSE_REPORT.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": status,
            "json_files_parsed": json_count,
            "parse_failures": failures,
        },
    )
    return status


def write_hash_manifest(output_root: Path) -> str:
    files = []
    for path in sorted(output_root.rglob("*"), key=lambda p: str(p)):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", PACKAGE_NAME}:
            continue
        data = path.read_bytes()
        files.append({"file": rel(path.relative_to(output_root) if path.is_relative_to(output_root) else path), "bytes": len(data), "sha256": sha256_bytes(data)})
    write_json(
        output_root / "HASH_MANIFEST.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "algorithm": "sha256",
            "generated_at": utc_now(),
            "status": "PASS",
            "file_count": len(files),
            "files": files,
            "excludes": ["HASH_MANIFEST.json", PACKAGE_NAME],
        },
    )
    return "PASS"


def create_package_zip(output_root: Path) -> Path:
    zip_path = output_root / PACKAGE_NAME
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(output_root.rglob("*"), key=lambda p: str(p)):
            if path.is_file() and path.name != PACKAGE_NAME:
                zf.write(path, str(path.relative_to(output_root)).replace("\\", "/"))
    return zip_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-r6-package", type=Path, default=DEFAULT_R6_ZIP)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--vss-command")
    parser.add_argument("--vss-endpoint")
    parser.add_argument("--vss-timeout-seconds", type=int)
    parser.add_argument("--vss-probe-mode")
    parser.add_argument("--vss-health-path")
    parser.add_argument("--redact-runtime-config")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    reset_output_root(output_root)

    validation = validate_r6_zip(args.input_r6_package.resolve())
    lineage = build_lineage(validation)
    write_json(output_root / "INPUT_LINEAGE_R6B.json", lineage)

    config, raw_config = resolve_config(args)
    write_json(output_root / "VSS_RUNTIME_CONFIGURATION_R6B.json", config)

    probe = run_probe(config, raw_config, output_root)
    write_json(output_root / "VSS_CONNECTIVITY_PROBE_R6B.json", probe)

    audits = write_audits(output_root, config, probe, lineage)
    audits["secret"] = write_secret_audit(output_root)
    initial_status = decide_status(validation, config, probe, audits)
    write_closeout(output_root, initial_status, config, probe, lineage, audits)
    write_readme(output_root, initial_status, config, probe)

    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    final_status = decide_status(validation, config, probe, audits, json_status, hash_status)
    write_closeout(output_root, final_status, config, probe, lineage, audits, json_status, hash_status)
    write_readme(output_root, final_status, config, probe)
    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    create_package_zip(output_root)

    print(f"Final status: {final_status}")
    print(f"Runner: {rel(Path(__file__).resolve())}")
    print(f"Output root: {rel(output_root)}")
    print(f"Freeze ZIP: {rel(output_root / PACKAGE_NAME)}")
    print(f"Runtime configured/mode: {str(config['runtime_configured']).lower()}/{config['runtime_mode']}")
    print(f"Probe attempted/executed/status: {str(probe['probe_attempted']).lower()}/{str(probe['probe_executed']).lower()}/{probe['probe_status']}")
    print("VSS narration records emitted: 0")
    print(f"JSON parse: {json_status}")
    print(f"Hash manifest: {hash_status}")
    return 0 if final_status.startswith(("PASS_", "PARTIAL_")) and json_status == "PASS" and hash_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
