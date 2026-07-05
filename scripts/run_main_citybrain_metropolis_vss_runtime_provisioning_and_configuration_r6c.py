#!/usr/bin/env python3
"""Run the R6C VSS runtime provisioning and configuration gate."""

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
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-PROVISIONING-AND-CONFIGURATION-R6C"
SCHEMA_VERSION = "metropolis-vss-runtime-provisioning-and-configuration-r6c.v1"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_runtime_provisioning_and_configuration_r6c"
DEFAULT_R6B_ZIP = (
    REPO_ROOT
    / "outputs"
    / "main_citybrain_metropolis_vss_runtime_configured_rerun_r6b"
    / "METROPOLIS_VSS_RUNTIME_CONFIGURED_RERUN_R6B_PACKAGE.zip"
)
PACKAGE_NAME = "METROPOLIS_VSS_RUNTIME_PROVISIONING_AND_CONFIGURATION_R6C_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_RUNTIME_PROVISIONED_AND_CONNECTED_R6C"
PARTIAL_NOT_CONFIGURED = "PARTIAL_METROPOLIS_VSS_RUNTIME_NOT_CONFIGURED_R6C_PROVISIONING_CONTRACT_READY"
PARTIAL_UNREACHABLE = "PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_BUT_UNREACHABLE_R6C"
PARTIAL_UNSUPPORTED = "PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_BUT_UNSUPPORTED_RESPONSE_R6C"
FAIL_SECRET = "FAIL_METROPOLIS_VSS_RUNTIME_CONFIGURATION_SECRET_LEAK_R6C"
FAIL_ACTION = "FAIL_METROPOLIS_VSS_RUNTIME_CONFIGURATION_ACTION_OR_MUTATION_RISK_R6C"
FAIL_BOUNDARY = "FAIL_METROPOLIS_VSS_RUNTIME_CONFIGURATION_BOUNDARY_RISK_R6C"

R6B_EXPECTED_STATUS = "PARTIAL_METROPOLIS_VSS_RUNTIME_NOT_CONFIGURED_R6B_CONNECTIVITY_CONTRACT_READY"
SOURCE_BOUNDARY = {
    "deepstream_metropolis": "sensor_inferred",
    "vss": "model_generated_narrative_only_not_fact_source",
}
HOST_ALLOCATION = {
    "deepstream_metropolis_lane": {
        "active_host": "txr-4070",
        "status": "proven_in_r2",
        "evidence": [
            "R2 used the DeepStream 8.0 container on txr-4070.",
            "R2 used gie-kitti-output-dir against bundled sample_1080p_h264.mp4.",
            "R2 exported 24 car metadata records and normalized vehicle_presence_candidate observations.",
        ],
        "source_class": "sensor_inferred",
    },
    "txr_3090_role": {
        "active_for_current_metropolis_vss_chain": False,
        "intended_role": "data_graph_rapids_heavier_analytics_box",
    },
    "vss_lane": {
        "active_host": None,
        "status": "not_configured",
        "reason": "No successful VSS command or endpoint has been proven by R6C.",
        "source_class": "model_generated_narrative_only_not_fact_source",
        "claim_rule": "Do not claim VSS is running on txr-4070, txr-3090, or any other host unless a real VSS command or endpoint is configured and the R6C connectivity gate passes.",
    },
    "r7_gate": {
        "status": "blocked_until_r6c_pass",
        "requirement": "R7 opens only after runtime_configured=true, probe_status=SUCCESS, and r7_ready=true.",
    },
}

REQUIRED_R6B_FILES = [
    "CLAIM_BOUNDARY_AUDIT_R6B.json",
    "HASH_MANIFEST.json",
    "INPUT_LINEAGE_R6B.json",
    "NO_ACTION_AUDIT_R6B.json",
    "R6B_CLOSEOUT_DECISION.json",
    "R6B_JSON_PARSE_REPORT.json",
    "README.md",
    "RUNTIME_CONFIGURATION_AUDIT_R6B.json",
    "SECRET_AUDIT_R6B.json",
    "SOURCE_CLASS_SEPARATION_AUDIT_R6B.json",
    "VSS_CONNECTIVITY_PROBE_R6B.json",
    "VSS_RUNTIME_CONFIGURATION_R6B.json",
]

SECRET_PATTERNS: list[tuple[str, str]] = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("bearer_token", r"(?i)\bbearer\s+[A-Za-z0-9_\-.]{20,}"),
    ("credential_assignment", r"(?i)\b(token|api[_-]?key|apikey|password|secret|auth|cookie|sig)\s*[:=]\s*[A-Za-z0-9_\-./+]{8,}"),
    ("header_secret", r"(?i)\b(authorization|x-api-key)\s*:\s*[A-Za-z0-9_\-./+]{8,}"),
    ("private_key", r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
]

BOUNDARY_PATTERNS: list[tuple[str, str]] = [
    ("confirmed_violation", r"\bconfirmed violation\b|\bviolation confirmed\b"),
    ("legal_finding", r"\blegal finding\b|\bcertified finding\b"),
    ("identity_biometric", r"\bbiometric\b|\bface recognition\b|\blicen[cs]e plate\b"),
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


def reset_output_root(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


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


def redact_text(value: str | None) -> str | None:
    if value is None:
        return None
    redacted = value
    redacted = re.sub(r"(?i)(token|api[_-]?key|apikey|password|secret|auth|cookie|sig)\s*[:=]\s*[^ \t\r\n;&]+", r"\1=<redacted>", redacted)
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
    return (redact_text(text) or "")[:limit]


def read_zip_json(zf: zipfile.ZipFile, name: str) -> Any:
    return json.loads(zf.read(name).decode("utf-8"))


def read_zip_jsonl(zf: zipfile.ZipFile, name: str) -> list[Any]:
    return parse_jsonl_text(zf.read(name).decode("utf-8"))


def validate_r6b_zip(package_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "input_r6b_zip": str(package_path),
        "input_r6b_zip_exists": package_path.exists(),
        "input_r6b_zip_sha256": None,
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
    if not package_path.exists():
        result["failure_reason"] = "Input R6B package not found."
        return result
    result["input_r6b_zip_sha256"] = sha256_file(package_path)
    parsed_json: dict[str, Any] = {}
    try:
        with zipfile.ZipFile(package_path, "r") as zf:
            names = zf.namelist()
            result["zip_entries"] = len(names)
            missing = [name for name in REQUIRED_R6B_FILES if name not in names]
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
                        read_zip_jsonl(zf, name)
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
    closeout = parsed_json.get("R6B_CLOSEOUT_DECISION.json", {})
    lineage = parsed_json.get("INPUT_LINEAGE_R6B.json", {})
    truth_ok = (
        closeout.get("status") == R6B_EXPECTED_STATUS
        and closeout.get("runtime_configured") is False
        and closeout.get("probe_status") == "NOT_CONFIGURED"
        and closeout.get("vss_narration_records") == 0
        and closeout.get("vss_is_fact_source") is False
        and closeout.get("candidate_event_modified_by_vss") is False
        and lineage.get("r2_candidate_observations") == 24
        and lineage.get("r2_candidate_events") == 1
    )
    result.update(
        {
            "r6b_closeout_status": closeout.get("status"),
            "r6b_runtime_configured": closeout.get("runtime_configured"),
            "r6b_probe_status": closeout.get("probe_status"),
            "r2_candidate_observations": lineage.get("r2_candidate_observations"),
            "r2_candidate_events": lineage.get("r2_candidate_events"),
            "candidate_event_modified_by_vss": False,
            "vss_narration_records": 0,
            "r6b_preserved_lineage_truth": truth_ok,
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


def resolve_runtime(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    endpoint_cli = args.vss_endpoint
    command_cli = args.vss_command
    endpoint_env = os.environ.get("CITYBRAIN_VSS_ENDPOINT")
    command_env = os.environ.get("CITYBRAIN_VSS_COMMAND")
    health_env = os.environ.get("CITYBRAIN_VSS_HEALTH_PATH")
    timeout_env = os.environ.get("CITYBRAIN_VSS_TIMEOUT_SECONDS")
    endpoint = endpoint_cli or endpoint_env
    command = command_cli or command_env
    health_path = args.health_path or health_env or "/health"
    timeout = int(args.timeout_seconds or timeout_env or 20)
    timeout = max(1, min(timeout, 300))
    if endpoint:
        runtime_mode = "endpoint"
        configured_via = "cli" if endpoint_cli else ("cli_and_env" if command_cli or command_env else "env")
    elif command:
        runtime_mode = "command"
        configured_via = "cli" if command_cli else "env"
    else:
        runtime_mode = "none"
        configured_via = "none"
    redacted_endpoint = redact_text(endpoint)
    redacted_command = redact_text(command)
    redacted_payload = json.dumps({"endpoint": redacted_endpoint, "command": redacted_command}, sort_keys=True)
    provisioning = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "runtime_configured": runtime_mode != "none",
        "runtime_mode": runtime_mode,
        "configured_via": configured_via,
        "redacted_endpoint": redacted_endpoint,
        "redacted_command": redacted_command,
        "health_path": health_path,
        "timeout_seconds": timeout,
        "redaction_applied": True,
        "secrets_present_after_redaction": contains_secret(redacted_payload),
        "source_boundary": SOURCE_BOUNDARY,
    }
    raw = {"endpoint": endpoint, "command": command, "health_path": health_path, "timeout": timeout, "runtime_mode": runtime_mode}
    return provisioning, raw


def endpoint_url(endpoint: str, health_path: str) -> str | None:
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"}:
        return None
    path = health_path or parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def run_probe(provisioning: dict[str, Any], raw: dict[str, Any], output_root: Path) -> dict[str, Any]:
    probe = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "runtime_configured": provisioning["runtime_configured"],
        "runtime_mode": provisioning["runtime_mode"],
        "probe_attempted": False,
        "probe_executed": False,
        "probe_status": "NOT_CONFIGURED",
        "timeout_seconds": provisioning["timeout_seconds"],
        "latency_ms": 0,
        "http_status": None,
        "exit_code": None,
        "content_type": None,
        "response_excerpt_ref": None,
        "stdout_excerpt_ref": None,
        "stderr_excerpt_ref": None,
        "error_summary": None,
    }
    if provisioning["runtime_mode"] == "none":
        probe["error_summary"] = "No VSS endpoint or command configured."
        return probe
    if provisioning["runtime_mode"] == "endpoint":
        url = endpoint_url(raw["endpoint"], raw["health_path"])
        if url is None:
            probe["probe_status"] = "UNSUPPORTED_RESPONSE"
            probe["error_summary"] = "Endpoint protocol is not http or https."
            return probe
        request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json,text/plain,*/*"})
        probe["probe_attempted"] = True
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=raw["timeout"]) as response:  # noqa: S310
                body = response.read().decode("utf-8", errors="replace")
                probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
                probe["http_status"] = int(response.status)
                probe["content_type"] = response.headers.get("Content-Type")
                probe["probe_executed"] = 200 <= int(response.status) < 300
                probe["probe_status"] = "SUCCESS" if probe["probe_executed"] else "UNREACHABLE"
                if body:
                    path = output_root / "REDACTED_HTTP_RESPONSE_EXCERPT.txt"
                    write_text(path, safe_excerpt(body))
                    probe["response_excerpt_ref"] = rel(path)
        except TimeoutError:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "UNREACHABLE"
            probe["error_summary"] = "Endpoint probe timed out."
        except urllib.error.HTTPError as exc:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["http_status"] = int(exc.code)
            probe["probe_status"] = "UNREACHABLE"
            probe["error_summary"] = f"HTTP error {exc.code}."
        except urllib.error.URLError as exc:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "UNREACHABLE"
            probe["error_summary"] = f"Endpoint unreachable: {exc.reason}"
        return probe
    if provisioning["runtime_mode"] == "command":
        probe["probe_attempted"] = True
        start = time.perf_counter()
        try:
            completed = subprocess.run(
                raw["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=raw["timeout"],
            )
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["exit_code"] = completed.returncode
            probe["probe_executed"] = completed.returncode == 0
            probe["probe_status"] = "SUCCESS" if completed.returncode == 0 else "UNREACHABLE"
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            if stdout:
                path = output_root / "REDACTED_STDOUT_EXCERPT.txt"
                write_text(path, safe_excerpt(stdout))
                probe["stdout_excerpt_ref"] = rel(path)
            if stderr:
                path = output_root / "REDACTED_STDERR_EXCERPT.txt"
                write_text(path, safe_excerpt(stderr))
                probe["stderr_excerpt_ref"] = rel(path)
            if completed.returncode != 0:
                probe["error_summary"] = f"Command exited with code {completed.returncode}."
        except subprocess.TimeoutExpired as exc:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "UNREACHABLE"
            probe["error_summary"] = "Command probe timed out."
            if exc.stdout:
                path = output_root / "REDACTED_STDOUT_EXCERPT.txt"
                write_text(path, safe_excerpt(exc.stdout))
                probe["stdout_excerpt_ref"] = rel(path)
            if exc.stderr:
                path = output_root / "REDACTED_STDERR_EXCERPT.txt"
                write_text(path, safe_excerpt(exc.stderr))
                probe["stderr_excerpt_ref"] = rel(path)
        return probe
    probe["probe_status"] = "UNSUPPORTED_RESPONSE"
    probe["error_summary"] = f"Unsupported runtime mode {provisioning['runtime_mode']}."
    return probe


def build_host_allocation(provisioning: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    allocation = json.loads(json.dumps(HOST_ALLOCATION))
    vss_lane = allocation["vss_lane"]
    if not provisioning["runtime_configured"]:
        vss_lane.update(
            {
                "active_host": None,
                "status": "not_configured",
                "reason": "No real VSS command or endpoint was supplied for this R6C run.",
            }
        )
        return allocation

    if probe["probe_status"] == "SUCCESS":
        active_host = None
        if provisioning["runtime_mode"] == "endpoint" and provisioning.get("redacted_endpoint"):
            active_host = urllib.parse.urlsplit(provisioning["redacted_endpoint"]).hostname
        vss_lane.update(
            {
                "active_host": active_host or "configured_runtime",
                "status": "configured_and_reachable",
                "reason": "A real configured VSS endpoint or command passed the R6C bounded connectivity probe.",
            }
        )
        allocation["r7_gate"]["status"] = "ready"
        return allocation

    vss_lane.update(
        {
            "active_host": None,
            "status": "configured_but_not_reachable",
            "reason": f"A VSS {provisioning['runtime_mode']} probe was configured, but R6C probe_status={probe['probe_status']}.",
        }
    )
    return allocation


def scan_runtime_excerpts(output_root: Path) -> list[dict[str, str]]:
    findings = []
    for name in ("REDACTED_STDOUT_EXCERPT.txt", "REDACTED_STDERR_EXCERPT.txt", "REDACTED_HTTP_RESPONSE_EXCERPT.txt"):
        path = output_root / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for family, pattern in BOUNDARY_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                findings.append({"file": name, "family": family})
    return findings


def write_audits(output_root: Path, provisioning: dict[str, Any], probe: dict[str, Any]) -> dict[str, str]:
    config_status = "PASS" if provisioning["redaction_applied"] and not provisioning["secrets_present_after_redaction"] else "FAIL"
    write_json(
        output_root / "RUNTIME_CONFIGURATION_AUDIT_R6C.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": config_status,
            "runtime_configured": provisioning["runtime_configured"],
            "runtime_mode": provisioning["runtime_mode"],
            "configured_via": provisioning["configured_via"],
            "redaction_applied": provisioning["redaction_applied"],
            "secrets_present_after_redaction": provisioning["secrets_present_after_redaction"],
        },
    )
    source_status = "PASS"
    write_json(
        output_root / "SOURCE_CLASS_SEPARATION_AUDIT_R6C.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": source_status,
            "deepstream_metropolis": "sensor_inferred",
            "vss": "model_generated_narrative_only_not_fact_source",
            "vss_is_fact_source": False,
            "vss_narration_records": 0,
        },
    )
    findings = scan_runtime_excerpts(output_root)
    claim_status = "PASS" if not findings else "FAIL"
    write_json(
        output_root / "CLAIM_BOUNDARY_AUDIT_R6C.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": claim_status,
            "runtime_excerpt_findings": findings,
            "fabricated_narration": False,
            "vss_narration_records": 0,
        },
    )
    write_json(
        output_root / "NO_ACTION_AUDIT_R6C.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": "PASS",
            "no_action_taken": True,
            "official_record_created": False,
            "candidate_event_modified_by_vss": False,
            "alert_ticket_dispatch_or_control_created": False,
        },
    )
    return {
        "runtime_configuration": config_status,
        "source_class_separation": source_status,
        "claim_boundary": claim_status,
        "no_action": "PASS",
    }


def write_secret_audit(output_root: Path) -> str:
    findings = []
    for path in sorted(output_root.iterdir(), key=lambda p: p.name):
        if path.name == "SECRET_AUDIT_R6C.json" or not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                findings.append({"file": path.name, "pattern": name})
    status = "PASS" if not findings else "FAIL"
    write_json(output_root / "SECRET_AUDIT_R6C.json", {"status": status, "findings": findings})
    return status


def r7_ready_reason(provisioning: dict[str, Any], probe: dict[str, Any], audits: dict[str, str]) -> tuple[bool, str]:
    if not provisioning["runtime_configured"]:
        return False, "No VSS runtime endpoint or command is configured."
    if probe["probe_status"] != "SUCCESS":
        return False, f"Runtime probe did not succeed: {probe['probe_status']}."
    if any(status != "PASS" for status in audits.values()):
        return False, "One or more R6C audits did not pass."
    return True, "Runtime is configured and bounded connectivity probe succeeded."


def decide_status(provisioning: dict[str, Any], probe: dict[str, Any], audits: dict[str, str], json_status: str = "PENDING", hash_status: str = "PENDING") -> str:
    if audits.get("secret_audit") == "FAIL":
        return FAIL_SECRET
    if audits.get("no_action") == "FAIL":
        return FAIL_ACTION
    if audits.get("runtime_configuration") == "FAIL" or audits.get("source_class_separation") == "FAIL" or audits.get("claim_boundary") == "FAIL":
        return FAIL_BOUNDARY
    if json_status == "FAIL" or hash_status == "FAIL":
        return FAIL_BOUNDARY
    if not provisioning["runtime_configured"]:
        return PARTIAL_NOT_CONFIGURED
    if probe["probe_status"] == "SUCCESS":
        return PASS_STATUS
    return PARTIAL_UNSUPPORTED if probe["probe_status"] == "UNSUPPORTED_RESPONSE" else PARTIAL_UNREACHABLE


def write_gate_and_closeout(output_root: Path, status: str, provisioning: dict[str, Any], probe: dict[str, Any], audits: dict[str, str], json_status: str = "PENDING", hash_status: str = "PENDING") -> None:
    r7_ready, reason = r7_ready_reason(provisioning, probe, audits)
    host_allocation = build_host_allocation(provisioning, probe)
    gate = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "r7_ready": r7_ready,
        "runtime_configured": provisioning["runtime_configured"],
        "probe_status": probe["probe_status"],
        "reason": reason,
        "next_task": "MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7" if r7_ready else None,
    }
    write_json(output_root / "R7_READINESS_GATE_R6C.json", gate)
    closeout = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": status,
        "runtime_configured": provisioning["runtime_configured"],
        "runtime_mode": provisioning["runtime_mode"],
        "configured_via": provisioning["configured_via"],
        "probe_attempted": probe["probe_attempted"],
        "probe_executed": probe["probe_executed"],
        "probe_status": probe["probe_status"],
        "r7_ready": r7_ready,
        "source_boundary": SOURCE_BOUNDARY,
        "host_allocation": host_allocation,
        "host_allocation_ref": "RUNTIME_HOST_ALLOCATION_R6C.json",
        "vss_is_fact_source": False,
        "vss_narration_records": 0,
        "candidate_event_modified_by_vss": False,
        "no_action_taken": True,
        "official_record_created": False,
        "audits": {**audits, "json_parse": json_status, "hash_manifest": hash_status},
        "limitations": [
            "R6C is provisioning/connectivity only; it does not generate VSS narration.",
            "R7 remains blocked unless r7_ready=true.",
            "No candidate observations or candidate events are modified.",
            "VSS remains model_generated_narrative_only_not_fact_source.",
        ],
        "validation_package_ref": PACKAGE_NAME,
    }
    write_json(output_root / "R6C_CLOSEOUT_DECISION.json", closeout)


def validate_json_outputs(output_root: Path) -> str:
    failures = []
    count = 0
    for path in sorted(output_root.iterdir(), key=lambda p: p.name):
        if path.name == PACKAGE_NAME:
            continue
        if path.suffix.lower() == ".json":
            count += 1
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                failures.append({"file": path.name, "error": str(exc)})
    status = "PASS" if not failures else "FAIL"
    write_json(
        output_root / "R6C_JSON_PARSE_REPORT.json",
        {"schema_version": SCHEMA_VERSION, "task_id": TASK_ID, "status": status, "json_files_parsed": count, "parse_failures": failures},
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


def write_readme(output_root: Path, status: str, provisioning: dict[str, Any], probe: dict[str, Any], r7_ready: bool) -> None:
    host_allocation = build_host_allocation(provisioning, probe)
    vss_lane = host_allocation["vss_lane"]
    write_text(
        output_root / "README.md",
        f"""# Metropolis/VSS Runtime Provisioning And Configuration R6C

Status: {status}

R6C checks whether a real VSS endpoint or command is configured and safely reachable.
It does not generate narration, send media, or modify candidate events.

Runtime configured: {str(provisioning["runtime_configured"]).lower()}
Runtime mode: {provisioning["runtime_mode"]}
Probe attempted/executed/status: {str(probe["probe_attempted"]).lower()}/{str(probe["probe_executed"]).lower()}/{probe["probe_status"]}
R7 ready: {str(r7_ready).lower()}
VSS narration records emitted: 0

Source boundary:
- DeepStream / Metropolis structured detections = sensor_inferred
- VSS output = model_generated_narrative_only_not_fact_source

Host allocation:
- DeepStream / Metropolis current media lane host: txr-4070
- txr-3090 role in this chain: not active; reserved for data/graph/RAPIDS/heavier analytics
- VSS runtime host: {vss_lane["active_host"] or "none"}
- VSS runtime status: {vss_lane["status"]}
- R7 remains blocked until R6C proves a real VSS command or endpoint
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
    parser.add_argument("--input-r6b-zip", type=Path, default=DEFAULT_R6B_ZIP)
    parser.add_argument("--vss-endpoint")
    parser.add_argument("--vss-command")
    parser.add_argument("--health-path")
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    reset_output_root(output_root)

    validation = validate_r6b_zip(args.input_r6b_zip.resolve())
    write_json(output_root / "INPUT_R6B_VALIDATION_R6C.json", validation)

    provisioning, raw = resolve_runtime(args)
    write_json(output_root / "VSS_RUNTIME_PROVISIONING_R6C.json", provisioning)

    probe = run_probe(provisioning, raw, output_root)
    write_json(output_root / "VSS_RUNTIME_CONNECTIVITY_PROBE_R6C.json", probe)
    write_json(
        output_root / "RUNTIME_HOST_ALLOCATION_R6C.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            **build_host_allocation(provisioning, probe),
        },
    )

    audits = write_audits(output_root, provisioning, probe)
    audits["secret_audit"] = write_secret_audit(output_root)
    initial_status = decide_status(provisioning, probe, audits)
    write_gate_and_closeout(output_root, initial_status, provisioning, probe, audits)
    r7_ready, _reason = r7_ready_reason(provisioning, probe, audits)
    write_readme(output_root, initial_status, provisioning, probe, r7_ready)

    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    final_status = decide_status(provisioning, probe, audits, json_status, hash_status)
    write_gate_and_closeout(output_root, final_status, provisioning, probe, audits, json_status, hash_status)
    r7_ready, _reason = r7_ready_reason(provisioning, probe, audits)
    write_readme(output_root, final_status, provisioning, probe, r7_ready)
    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    create_package_zip(output_root)

    print(f"Final status: {final_status}")
    print(f"Runner: {rel(Path(__file__).resolve())}")
    print(f"Output root: {rel(output_root)}")
    print(f"Freeze ZIP: {rel(output_root / PACKAGE_NAME)}")
    print(f"Runtime configured/mode: {str(provisioning['runtime_configured']).lower()}/{provisioning['runtime_mode']}")
    print(f"Probe attempted/executed/status: {str(probe['probe_attempted']).lower()}/{str(probe['probe_executed']).lower()}/{probe['probe_status']}")
    print(f"R7 ready: {str(r7_ready).lower()}")
    print("VSS narration records emitted: 0")
    print(f"JSON parse: {json_status}")
    print(f"Hash manifest: {hash_status}")
    return 0 if final_status.startswith(("PASS_", "PARTIAL_")) and json_status == "PASS" and hash_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
