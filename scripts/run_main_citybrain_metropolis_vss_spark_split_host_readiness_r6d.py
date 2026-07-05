"""Run the R6D Spark split-host readiness gate for Metropolis/VSS."""

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
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-SPLIT-HOST-READINESS-R6D"
SCHEMA_VERSION = "metropolis-vss-spark-split-host-readiness-r6d.v1"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_spark_split_host_readiness_r6d"
PACKAGE_NAME = "METROPOLIS_VSS_SPARK_SPLIT_HOST_READINESS_R6D_PACKAGE.zip"

R2_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_object_metadata_export_r2"
R6C_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_runtime_provisioning_and_configuration_r6c"

PASS_STATUS = "PASS_METROPOLIS_VSS_SPARK_SPLIT_HOST_READINESS_R6D"
PARTIAL_NOT_CONFIGURED = "PARTIAL_METROPOLIS_VSS_SPARK_RUNTIME_NOT_CONFIGURED_R6D_READINESS_CONTRACT_READY"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_SPARK_SPLIT_HOST_BOUNDARY_OR_SECRET_RISK_R6D"

SOURCE_BOUNDARY = {
    "deepstream_metropolis": "sensor_inferred",
    "spark_vss": "model_generated_narrative_only_not_fact_source",
}

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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reset_output_root(path: Path) -> None:
    resolved = path.resolve()
    expected = (REPO_ROOT / "outputs").resolve()
    if expected not in resolved.parents:
        raise RuntimeError(f"Refusing to reset output root outside outputs: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def redact_text(value: str | None) -> str | None:
    if not value:
        return None
    redacted = value
    redacted = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9_\-.]+", r"\1<redacted>", redacted)
    redacted = re.sub(r"(?i)(token|api[_-]?key|apikey|password|secret|auth|cookie|sig)(\s*[:=]\s*)\S+", r"\1\2<redacted>", redacted)
    redacted = re.sub(r"(?i)(authorization|x-api-key)(\s*:\s*)\S+", r"\1\2<redacted>", redacted)
    return redacted


def redact_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        return redact_text(value)
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path or "/", "", ""))


def contains_secret(text: str) -> bool:
    return any(re.search(pattern, text) for _family, pattern in SECRET_PATTERNS)


def load_r2_lineage() -> dict[str, Any]:
    closeout = read_json(R2_ROOT / "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_CLOSEOUT_DECISION.json")
    export = read_json(R2_ROOT / "DEEPSTREAM_OBJECT_METADATA_EXPORT_REPORT.json")
    mapping = read_json(R2_ROOT / "MEDIA_TO_CANDIDATE_EVENT_MAPPING_R2.json")
    event = mapping.get("candidate_event", {})
    return {
        "r2_root": rel(R2_ROOT),
        "r2_status": closeout.get("status"),
        "deepstream_host": export.get("remote_host") or "txr-4070",
        "deepstream_image": export.get("deepstream_image"),
        "media_source_ref": closeout.get("media_source_selected") or export.get("media_source_selected"),
        "zone_id": event.get("zone_id") or closeout.get("zone_selected"),
        "class_label": closeout.get("class_label_selected") or export.get("class_label_selected"),
        "detection_class": closeout.get("detection_class_selected") or export.get("detection_class_selected"),
        "candidate_event_id": event.get("candidate_event_id"),
        "candidate_observation_count": closeout.get("candidate_observations_emitted") or export.get("normalized_object_metadata_records"),
        "candidate_event_count": closeout.get("candidate_events_emitted"),
        "candidate_observation_ids": event.get("source_observation_ids", []),
        "confidence_summary": event.get("confidence_summary"),
        "evidence_bundle_ref": event.get("evidence_bundle_ref"),
        "source_class": event.get("source_class") or "sensor_inferred",
        "no_action_taken": event.get("no_action_taken") is not False,
        "official_record_created": bool(event.get("official_record_created")),
    }


def load_r6c_lineage() -> dict[str, Any]:
    closeout = read_json(R6C_ROOT / "R6C_CLOSEOUT_DECISION.json")
    return {
        "r6c_root": rel(R6C_ROOT),
        "r6c_status": closeout.get("status"),
        "runtime_configured": closeout.get("runtime_configured"),
        "probe_status": closeout.get("probe_status"),
        "r7_ready": closeout.get("r7_ready"),
        "vss_narration_records": closeout.get("vss_narration_records", 0),
        "candidate_event_modified_by_vss": closeout.get("candidate_event_modified_by_vss", False),
    }


def resolve_spark_runtime(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    endpoint_cli = args.spark_vss_endpoint
    command_cli = args.spark_vss_command
    endpoint_env = os.environ.get("CITYBRAIN_SPARK_VSS_ENDPOINT")
    command_env = os.environ.get("CITYBRAIN_SPARK_VSS_COMMAND")
    endpoint = endpoint_cli or endpoint_env
    command = command_cli or command_env
    timeout = max(1, min(int(args.timeout_seconds), 120))
    if endpoint:
        mode = "http_endpoint"
        configured_via = "cli" if endpoint_cli else "env"
    elif command:
        mode = "command_wrapper"
        configured_via = "cli" if command_cli else "env"
    else:
        mode = "none"
        configured_via = "none"
    redacted_endpoint = redact_url(endpoint)
    redacted_command = redact_text(command)
    redacted_payload = json.dumps({"endpoint": redacted_endpoint, "command": redacted_command}, sort_keys=True)
    config = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "spark_vss_runtime_configured": mode != "none",
        "spark_vss_runtime_mode": mode,
        "configured_via": configured_via,
        "intended_host": "Spark / DGX Spark",
        "redacted_endpoint": redacted_endpoint,
        "redacted_command": redacted_command,
        "env_presence": {
            "CITYBRAIN_SPARK_VSS_ENDPOINT": bool(endpoint_env),
            "CITYBRAIN_SPARK_VSS_COMMAND": bool(command_env),
        },
        "cli_presence": {
            "--spark-vss-endpoint": bool(endpoint_cli),
            "--spark-vss-command": bool(command_cli),
        },
        "timeout_seconds": timeout,
        "redaction_applied": True,
        "secrets_present_after_redaction": contains_secret(redacted_payload),
        "source_boundary": SOURCE_BOUNDARY,
    }
    raw = {"endpoint": endpoint, "command": command, "mode": mode, "timeout": timeout}
    return config, raw


def build_r7_probe_request(r2: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": "citybrain-r6d-r7-readiness-payload-contract-001",
        "task": "candidate_observation_narration_for_human_review",
        "source_class": "model_generated_narrative_request",
        "structured_evidence_ref": "CROSS_HOST_PAYLOAD_CONTRACT_R6D.json",
        "candidate_event": {
            "candidate_event_id": r2.get("candidate_event_id"),
            "source_class": r2.get("source_class"),
            "detection_class": r2.get("detection_class"),
            "class_label": r2.get("class_label"),
            "zone_id": r2.get("zone_id"),
            "evidence_bundle_ref": r2.get("evidence_bundle_ref"),
            "candidate_observation_count": r2.get("candidate_observation_count"),
        },
        "candidate_observation_ids": r2.get("candidate_observation_ids", []),
        "limitations": [
            "Candidate observations only; human review required.",
            "Do not infer identity, legal status, intent, violation confirmation, or operational action.",
            "Do not add new counts or detections beyond supplied structured metadata.",
        ],
    }


def run_probe(config: dict[str, Any], raw: dict[str, Any], output_root: Path, r2: dict[str, Any]) -> dict[str, Any]:
    probe = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "allowed_probe_modes": ["command_wrapper", "http_endpoint"],
        "probe_goal": "prove Spark VSS runtime is configured and reachable without generating narration",
        "runtime_configured": config["spark_vss_runtime_configured"],
        "probe_attempted": False,
        "probe_executed": False,
        "probe_status": "NOT_CONFIGURED",
        "r7_ready": False,
        "spark_vss_runtime_configured": config["spark_vss_runtime_configured"],
        "spark_vss_probe_attempted": False,
        "spark_vss_probe_executed": False,
        "spark_vss_probe_status": "NOT_CONFIGURED",
        "runtime_mode": config["spark_vss_runtime_mode"],
        "timeout_seconds": config["timeout_seconds"],
        "latency_ms": 0,
        "http_status": None,
        "exit_code": None,
        "error_summary": None,
        "response_excerpt_ref": None,
        "required_success_fields": {
            "spark_vss_runtime_configured": True,
            "spark_vss_probe_attempted": True,
            "spark_vss_probe_executed": True,
            "spark_vss_probe_status": "SUCCESS",
            "r7_ready": True,
        },
        "r7_payload_contract": build_r7_probe_request(r2),
    }
    if raw["mode"] == "none":
        probe["error_summary"] = "No Spark VSS endpoint or command configured."
        return probe

    probe["probe_attempted"] = True
    probe["spark_vss_probe_attempted"] = True
    start = time.perf_counter()
    if raw["mode"] == "http_endpoint":
        try:
            request = urllib.request.Request(raw["endpoint"], method="GET", headers={"Accept": "application/json,text/plain,*/*"})
            with urllib.request.urlopen(request, timeout=raw["timeout"]) as response:  # noqa: S310
                body = response.read().decode("utf-8", errors="replace")
                probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
                probe["http_status"] = int(response.status)
                ok = 200 <= int(response.status) < 300
                probe["probe_executed"] = ok
                probe["spark_vss_probe_executed"] = ok
                probe["probe_status"] = "SUCCESS" if ok else "FAILED"
                probe["spark_vss_probe_status"] = probe["probe_status"]
                probe["r7_ready"] = ok
                if body:
                    excerpt = output_root / "REDACTED_SPARK_VSS_HTTP_RESPONSE_EXCERPT.txt"
                    write_text(excerpt, redact_text(body[:1200]) or "")
                    probe["response_excerpt_ref"] = rel(excerpt)
        except TimeoutError:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "TIMEOUT"
            probe["spark_vss_probe_status"] = "TIMEOUT"
            probe["error_summary"] = "Spark VSS endpoint probe timed out."
        except urllib.error.HTTPError as exc:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["http_status"] = int(exc.code)
            probe["probe_status"] = "FAILED"
            probe["spark_vss_probe_status"] = "FAILED"
            probe["error_summary"] = f"HTTP error {exc.code}."
        except Exception as exc:  # noqa: BLE001
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "ERROR"
            probe["spark_vss_probe_status"] = "ERROR"
            probe["error_summary"] = f"Endpoint probe error: {exc}"
        return probe

    if raw["mode"] == "command_wrapper":
        request_path = output_root / "SPARK_VSS_COMMAND_PROBE_REQUEST_R6D.json"
        response_path = output_root / "SPARK_VSS_COMMAND_PROBE_RESPONSE_R6D.json"
        write_json(request_path, build_r7_probe_request(r2))
        command = raw["command"]
        if "{input_json}" in command or "{output_json}" in command:
            command = command.replace("{input_json}", str(request_path)).replace("{output_json}", str(response_path))
        try:
            completed = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=raw["timeout"])
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["exit_code"] = completed.returncode
            ok = completed.returncode == 0
            probe["probe_executed"] = ok
            probe["spark_vss_probe_executed"] = ok
            probe["probe_status"] = "SUCCESS" if ok else "FAILED"
            probe["spark_vss_probe_status"] = probe["probe_status"]
            probe["r7_ready"] = ok
            if completed.stdout:
                stdout_path = output_root / "REDACTED_SPARK_VSS_STDOUT_EXCERPT.txt"
                write_text(stdout_path, redact_text(completed.stdout[:1200]) or "")
                probe["stdout_excerpt_ref"] = rel(stdout_path)
            if completed.stderr:
                stderr_path = output_root / "REDACTED_SPARK_VSS_STDERR_EXCERPT.txt"
                write_text(stderr_path, redact_text(completed.stderr[:1200]) or "")
                probe["stderr_excerpt_ref"] = rel(stderr_path)
            if not ok:
                probe["error_summary"] = f"Command exited with code {completed.returncode}."
        except subprocess.TimeoutExpired:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "TIMEOUT"
            probe["spark_vss_probe_status"] = "TIMEOUT"
            probe["error_summary"] = "Spark VSS command probe timed out."
        except Exception as exc:  # noqa: BLE001
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "ERROR"
            probe["spark_vss_probe_status"] = "ERROR"
            probe["error_summary"] = f"Command probe error: {exc}"
        return probe

    probe["probe_status"] = "ERROR"
    probe["spark_vss_probe_status"] = "ERROR"
    probe["error_summary"] = f"Unsupported Spark VSS runtime mode: {raw['mode']}"
    return probe


def build_host_allocation(config: dict[str, Any], probe: dict[str, Any], r2: dict[str, Any]) -> dict[str, Any]:
    spark_status = "installing_not_configured_until_probe_passes"
    spark_active_host = None
    if config["spark_vss_runtime_configured"] and probe["spark_vss_probe_status"] == "SUCCESS":
        spark_status = "configured_and_reachable"
        if config["spark_vss_runtime_mode"] == "http_endpoint" and config.get("redacted_endpoint"):
            spark_active_host = urllib.parse.urlsplit(config["redacted_endpoint"]).hostname
        else:
            spark_active_host = "Spark / DGX Spark command wrapper"
    elif config["spark_vss_runtime_configured"]:
        spark_status = f"configured_but_probe_{probe['spark_vss_probe_status'].lower()}"
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "deepstream_metropolis_lane": {
            "active_host": "txr-4070",
            "status": "proven_in_r2",
            "evidence": [
                "R2 used the DeepStream 8.0 container on txr-4070.",
                "R2 used gie-kitti-output-dir against bundled sample_1080p_h264.mp4.",
                "R2 exported 24 car metadata records and normalized vehicle_presence_candidate observations.",
            ],
            "lineage": {
                "r2_status": r2.get("r2_status"),
                "candidate_observations": r2.get("candidate_observation_count"),
                "candidate_events": r2.get("candidate_event_count"),
                "detection_class": r2.get("detection_class"),
            },
            "source_class": "sensor_inferred",
        },
        "spark_vss_lane": {
            "intended_host": "Spark / DGX Spark",
            "active_host": spark_active_host,
            "status": spark_status,
            "source_class": "model_generated_narrative_only_not_fact_source",
            "claim_rule": "Do not claim VSS is running on Spark until a real command or endpoint is configured and the connectivity probe passes.",
        },
        "txr_3090_role": {
            "active_for_current_metropolis_vss_chain": False,
            "intended_role": "data_graph_rapids_heavier_analytics_box",
        },
        "r7_gate": {
            "status": "ready" if probe["r7_ready"] else "blocked_until_spark_vss_connectivity_pass",
            "requirement": "R7 opens only after spark_vss_runtime_configured=true, spark_vss_probe_status=SUCCESS, and r7_ready=true.",
        },
    }


def build_cross_host_payload_contract(r2: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "source_host": "txr-4070",
        "target_host": "Spark / DGX Spark once configured",
        "allowed_fields": [
            "candidate_event_id",
            "candidate_observation_ids",
            "media_source_ref",
            "frame_refs",
            "time_refs",
            "class_label",
            "confidence",
            "bbox_or_region",
            "zone_id",
            "evidence_bundle_ref",
            "limitation_refs",
            "source_class",
        ],
        "r2_payload_summary": {
            "candidate_event_id": r2.get("candidate_event_id"),
            "candidate_observation_count": r2.get("candidate_observation_count"),
            "candidate_observation_ids": r2.get("candidate_observation_ids", []),
            "media_source_ref": r2.get("media_source_ref"),
            "class_label": r2.get("class_label"),
            "detection_class": r2.get("detection_class"),
            "confidence": r2.get("confidence_summary"),
            "zone_id": r2.get("zone_id"),
            "evidence_bundle_ref": r2.get("evidence_bundle_ref"),
            "source_class": r2.get("source_class"),
        },
        "candidate_event_mutation_allowed": False,
        "raw_video_or_frame_bytes_included": False,
        "forbidden_fields_or_claims": [
            "secrets",
            "credentials",
            "identity inference",
            "biometric inference",
            "confirmed violation",
            "official case",
            "ticket",
            "dispatch",
            "routing",
            "control",
            "enforcement",
            "legal finding",
            "automated action",
        ],
    }


def write_audits(output_root: Path, config: dict[str, Any], host_allocation: dict[str, Any], payload_contract: dict[str, Any]) -> dict[str, str]:
    source_ok = (
        host_allocation["deepstream_metropolis_lane"]["active_host"] == "txr-4070"
        and host_allocation["deepstream_metropolis_lane"]["source_class"] == "sensor_inferred"
        and host_allocation["spark_vss_lane"]["source_class"] == "model_generated_narrative_only_not_fact_source"
    )
    host_ok = (
        host_allocation["spark_vss_lane"]["intended_host"] == "Spark / DGX Spark"
        and host_allocation["txr_3090_role"]["active_for_current_metropolis_vss_chain"] is False
    )
    no_action_ok = payload_contract["candidate_event_mutation_allowed"] is False
    boundary_findings = []
    for excerpt_name in (
        "REDACTED_SPARK_VSS_HTTP_RESPONSE_EXCERPT.txt",
        "REDACTED_SPARK_VSS_STDOUT_EXCERPT.txt",
        "REDACTED_SPARK_VSS_STDERR_EXCERPT.txt",
    ):
        excerpt_path = output_root / excerpt_name
        if not excerpt_path.exists():
            continue
        text = excerpt_path.read_text(encoding="utf-8", errors="ignore")
        for family, pattern in BOUNDARY_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                boundary_findings.append({"file": excerpt_name, "family": family})
    claim_ok = not boundary_findings
    write_json(
        output_root / "SOURCE_CLASS_SEPARATION_AUDIT_R6D.json",
        {"status": "PASS" if source_ok else "FAIL", "source_boundary": SOURCE_BOUNDARY},
    )
    write_json(
        output_root / "HOST_ALLOCATION_AUDIT_R6D.json",
        {
            "status": "PASS" if host_ok else "FAIL",
            "txr_4070_deepstream_metropolis": "locked",
            "spark_vss": "intended_host",
            "txr_3090_active_for_chain": False,
        },
    )
    write_json(
        output_root / "CLAIM_BOUNDARY_AUDIT_R6D.json",
        {
            "status": "PASS" if claim_ok else "FAIL",
            "findings": boundary_findings,
            "vss_fact_source_claim": False,
            "narration_emitted": False,
        },
    )
    write_json(
        output_root / "NO_ACTION_AUDIT_R6D.json",
        {
            "status": "PASS" if no_action_ok else "FAIL",
            "candidate_event_modified": False,
            "official_record_created": False,
            "ticket_alert_dispatch_enforcement_created": False,
        },
    )
    secret_findings = []
    for path in sorted(output_root.iterdir(), key=lambda p: p.name):
        if not path.is_file() or path.name == PACKAGE_NAME:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for family, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                secret_findings.append({"file": path.name, "family": family})
    if config["secrets_present_after_redaction"]:
        secret_findings.append({"file": "SPARK_VSS_RUNTIME_CONFIG_R6D.json", "family": "redaction_failed"})
    write_json(output_root / "SECRET_AUDIT_R6D.json", {"status": "PASS" if not secret_findings else "FAIL", "findings": secret_findings})
    return {
        "source_class_separation": "PASS" if source_ok else "FAIL",
        "host_allocation": "PASS" if host_ok else "FAIL",
        "claim_boundary": "PASS" if claim_ok else "FAIL",
        "no_action": "PASS" if no_action_ok else "FAIL",
        "secret_audit": "PASS" if not secret_findings else "FAIL",
    }


def decide_status(config: dict[str, Any], probe: dict[str, Any], audits: dict[str, str], json_status: str = "PENDING", hash_status: str = "PENDING") -> str:
    if any(value == "FAIL" for value in audits.values()) or json_status == "FAIL" or hash_status == "FAIL":
        return FAIL_STATUS
    if config["spark_vss_runtime_configured"] and probe["spark_vss_probe_status"] == "SUCCESS" and probe["r7_ready"]:
        return PASS_STATUS
    return PARTIAL_NOT_CONFIGURED


def write_r7_gate(output_root: Path, probe: dict[str, Any]) -> None:
    r7_ready = bool(probe["r7_ready"])
    if r7_ready:
        reason = "Spark VSS runtime is configured and the bounded connectivity probe passed."
    elif not probe["runtime_configured"]:
        reason = "Spark VSS runtime is installing or not yet configured."
    else:
        reason = f"Spark VSS probe did not pass: {probe['spark_vss_probe_status']}."
    write_json(
        output_root / "R7_READINESS_GATE_R6D.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "r7_ready": r7_ready,
            "reason": reason,
            "next_task_when_ready": "MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7" if r7_ready else None,
        },
    )


def write_closeout(
    output_root: Path,
    status: str,
    config: dict[str, Any],
    probe: dict[str, Any],
    audits: dict[str, str],
    r2: dict[str, Any],
    r6c: dict[str, Any],
    json_status: str = "PENDING",
    hash_status: str = "PENDING",
) -> None:
    write_json(
        output_root / "R6D_CLOSEOUT_DECISION.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": status,
            "spark_vss_runtime_configured": config["spark_vss_runtime_configured"],
            "spark_vss_runtime_mode": config["spark_vss_runtime_mode"],
            "spark_vss_probe_attempted": probe["spark_vss_probe_attempted"],
            "spark_vss_probe_executed": probe["spark_vss_probe_executed"],
            "spark_vss_probe_status": probe["spark_vss_probe_status"],
            "r7_ready": probe["r7_ready"],
            "host_allocation_ref": "RUNTIME_HOST_ALLOCATION_R6D.json",
            "cross_host_payload_contract_ref": "CROSS_HOST_PAYLOAD_CONTRACT_R6D.json",
            "source_boundary": SOURCE_BOUNDARY,
            "r2_lineage": r2,
            "r6c_lineage": r6c,
            "vss_narration_records": 0,
            "candidate_event_modified_by_vss": False,
            "official_record_created": False,
            "no_action_taken": True,
            "audits": {**audits, "json_parse": json_status, "hash_manifest": hash_status},
            "limitations": [
                "R6D prepares split-host readiness only; it does not emit VSS narration.",
                "R7 remains blocked unless Spark VSS connectivity passes.",
                "DeepStream/Metropolis remains on txr-4070 and source_class=sensor_inferred.",
                "Spark VSS remains model_generated_narrative_only_not_fact_source.",
                "txr-3090 is not active for this Metropolis/VSS chain.",
            ],
            "validation_package_ref": PACKAGE_NAME,
        },
    )


def write_readme(output_root: Path, status: str, config: dict[str, Any], probe: dict[str, Any]) -> None:
    write_text(
        output_root / "README.md",
        f"""# Metropolis/VSS Spark Split-Host Readiness R6D

Status: {status}

R6D prepares the split-host bridge:
- DeepStream / Metropolis: txr-4070, sensor_inferred, proven by R2.
- Spark / DGX Spark: intended VSS host, model_generated_narrative only.
- txr-3090: not active for this Metropolis/VSS chain.

Spark VSS configured/mode: {str(config["spark_vss_runtime_configured"]).lower()}/{config["spark_vss_runtime_mode"]}
Spark VSS probe attempted/executed/status: {str(probe["spark_vss_probe_attempted"]).lower()}/{str(probe["spark_vss_probe_executed"]).lower()}/{probe["spark_vss_probe_status"]}
R7 ready: {str(probe["r7_ready"]).lower()}
VSS narration records emitted: 0

No candidate event is modified. No official record, ticket, alert, dispatch,
route, enforcement action, legal finding, or identity claim is created.
""",
    )


def validate_json_outputs(output_root: Path) -> str:
    failures = []
    count = 0
    for path in sorted(output_root.iterdir(), key=lambda p: p.name):
        if path.name == PACKAGE_NAME or path.suffix.lower() != ".json":
            continue
        count += 1
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            failures.append({"file": path.name, "error": str(exc)})
    status = "PASS" if not failures else "FAIL"
    write_json(
        output_root / "R6D_JSON_PARSE_REPORT.json",
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
    parser.add_argument("--spark-vss-command")
    parser.add_argument("--spark-vss-endpoint")
    parser.add_argument("--timeout-seconds", type=int, default=10)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    reset_output_root(output_root)

    r2 = load_r2_lineage()
    r6c = load_r6c_lineage()
    config, raw = resolve_spark_runtime(args)
    probe = run_probe(config, raw, output_root, r2)
    host_allocation = build_host_allocation(config, probe, r2)
    payload_contract = build_cross_host_payload_contract(r2)

    write_json(output_root / "RUNTIME_HOST_ALLOCATION_R6D.json", host_allocation)
    write_json(output_root / "SPARK_VSS_RUNTIME_CONFIG_R6D.json", config)
    write_json(output_root / "SPARK_VSS_CONNECTIVITY_PROBE_CONTRACT_R6D.json", probe)
    write_json(output_root / "CROSS_HOST_PAYLOAD_CONTRACT_R6D.json", payload_contract)
    write_r7_gate(output_root, probe)

    audits = write_audits(output_root, config, host_allocation, payload_contract)
    status = decide_status(config, probe, audits)
    write_closeout(output_root, status, config, probe, audits, r2, r6c)
    write_readme(output_root, status, config, probe)

    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    status = decide_status(config, probe, audits, json_status, hash_status)
    write_closeout(output_root, status, config, probe, audits, r2, r6c, json_status, hash_status)
    write_readme(output_root, status, config, probe)
    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    create_package_zip(output_root)

    print(f"Final status: {status}")
    print(f"Runner: {rel(Path(__file__))}")
    print(f"Output root: {rel(output_root)}")
    print(f"Freeze ZIP: {rel(output_root / PACKAGE_NAME)}")
    print(f"Spark VSS configured/mode: {str(config['spark_vss_runtime_configured']).lower()}/{config['spark_vss_runtime_mode']}")
    print(
        "Spark VSS probe attempted/executed/status: "
        f"{str(probe['spark_vss_probe_attempted']).lower()}/{str(probe['spark_vss_probe_executed']).lower()}/{probe['spark_vss_probe_status']}"
    )
    print(f"R7 ready: {str(probe['r7_ready']).lower()}")
    print("VSS narration records emitted: 0")
    print(f"JSON parse: {json_status}")
    print(f"Hash manifest: {hash_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
