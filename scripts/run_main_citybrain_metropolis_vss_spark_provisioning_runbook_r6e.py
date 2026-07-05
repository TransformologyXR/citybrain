"""Run the R6E Spark VSS provisioning runbook gate."""

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
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-PROVISIONING-RUNBOOK-R6E"
SCHEMA_VERSION = "metropolis-vss-spark-provisioning-runbook-r6e.v1"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_spark_provisioning_runbook_r6e"
PACKAGE_NAME = "METROPOLIS_VSS_SPARK_PROVISIONING_RUNBOOK_R6E_PACKAGE.zip"

R2_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_object_metadata_export_r2"
R6D_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_spark_split_host_readiness_r6d"

PASS_STATUS = "PASS_METROPOLIS_VSS_SPARK_RUNTIME_CONFIGURED_R6E_R7_READY"
PARTIAL_NOT_CONFIGURED = "PARTIAL_METROPOLIS_VSS_SPARK_RUNTIME_NOT_CONFIGURED_R6E_PROVISIONING_RUNBOOK_READY"
PARTIAL_UNREACHABLE = "PARTIAL_METROPOLIS_VSS_SPARK_RUNTIME_UNREACHABLE_R6E"
PARTIAL_UNSAFE = "PARTIAL_METROPOLIS_VSS_SPARK_RUNTIME_RESPONSE_UNSAFE_R6E"
FAIL_BOUNDARY = "FAIL_METROPOLIS_VSS_SPARK_RUNTIME_SECRET_OR_BOUNDARY_RISK_R6E"
FAIL_FACT_SOURCE = "FAIL_METROPOLIS_VSS_SPARK_RUNTIME_VSS_FACT_SOURCE_CLAIM_R6E"

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
]

FACT_SOURCE_PATTERNS: list[tuple[str, str]] = [
    ("vss_sensor_inferred", r"(?i)\bvss\b.{0,80}\bsensor[_ -]?inferred\b"),
    ("vss_fact_source", r"(?i)\bvss\b.{0,80}\b(fact source|source of truth|detected|confirmed|verified)\b"),
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


def reset_output_root(path: Path) -> None:
    resolved = path.resolve()
    expected = (REPO_ROOT / "outputs").resolve()
    if expected not in resolved.parents:
        raise RuntimeError(f"Refusing to reset output root outside outputs: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    mapping = read_json(R2_ROOT / "MEDIA_TO_CANDIDATE_EVENT_MAPPING_R2.json")
    export = read_json(R2_ROOT / "DEEPSTREAM_OBJECT_METADATA_EXPORT_REPORT.json")
    event = mapping.get("candidate_event", {})
    return {
        "r2_root": rel(R2_ROOT),
        "r2_status": closeout.get("status"),
        "deepstream_host": export.get("remote_host") or "txr-4070",
        "candidate_observations": closeout.get("candidate_observations_emitted") or export.get("normalized_object_metadata_records"),
        "candidate_events": closeout.get("candidate_events_emitted"),
        "candidate_event_id": event.get("candidate_event_id"),
        "candidate_observation_ids": event.get("source_observation_ids", []),
        "media_source_ref": closeout.get("media_source_selected") or export.get("media_source_selected"),
        "zone_id": event.get("zone_id") or closeout.get("zone_selected"),
        "class_label": closeout.get("class_label_selected") or export.get("class_label_selected"),
        "detection_class": closeout.get("detection_class_selected") or export.get("detection_class_selected"),
        "confidence_summary": event.get("confidence_summary"),
        "evidence_bundle_ref": event.get("evidence_bundle_ref"),
        "source_class": event.get("source_class") or "sensor_inferred",
        "no_action_taken": event.get("no_action_taken") is not False,
        "official_record_created": bool(event.get("official_record_created")),
    }


def load_r6d_lineage() -> dict[str, Any]:
    closeout = read_json(R6D_ROOT / "R6D_CLOSEOUT_DECISION.json")
    return {
        "r6d_root": rel(R6D_ROOT),
        "r6d_status": closeout.get("status"),
        "spark_vss_runtime_configured": closeout.get("spark_vss_runtime_configured"),
        "spark_vss_probe_status": closeout.get("spark_vss_probe_status"),
        "r7_ready": closeout.get("r7_ready"),
        "vss_narration_records": closeout.get("vss_narration_records", 0),
        "candidate_event_modified_by_vss": closeout.get("candidate_event_modified_by_vss", False),
    }


def resolve_config(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    endpoint_cli = args.spark_vss_endpoint
    command_cli = args.spark_vss_command
    endpoint_env = os.environ.get("CITYBRAIN_SPARK_VSS_ENDPOINT")
    command_env = os.environ.get("CITYBRAIN_SPARK_VSS_COMMAND")
    endpoint = endpoint_cli or endpoint_env
    command = command_cli or command_env
    timeout = max(1, min(int(args.timeout_seconds), 180))
    max_response_bytes = max(1024, min(int(args.max_response_bytes), 1024 * 1024))
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
        "spark_vss_mode": mode,
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
        "max_response_bytes": max_response_bytes,
        "redaction_applied": True,
        "secrets_present_after_redaction": contains_secret(redacted_payload),
        "source_boundary": SOURCE_BOUNDARY,
    }
    raw = {"endpoint": endpoint, "command": command, "mode": mode, "timeout": timeout, "max_response_bytes": max_response_bytes}
    return config, raw


def build_bounded_probe_payload(r2: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": "vss-r6e-probe-001",
        "mode": "bounded_narration_probe",
        "evidence_context": {
            "candidate_event_id": r2.get("candidate_event_id"),
            "candidate_observation_count": r2.get("candidate_observations"),
            "candidate_observation_ids": r2.get("candidate_observation_ids", []),
            "source_class": "sensor_inferred",
            "allowed_narration_role": "model_generated_narrative_only",
            "class_label": r2.get("class_label"),
            "detection_class": r2.get("detection_class"),
            "zone_id": r2.get("zone_id"),
            "evidence_bundle_ref": r2.get("evidence_bundle_ref"),
            "limitations": [
                "Candidate metadata only; human review required.",
                "Do not infer identity, legal status, intent, violation confirmation, or operational action.",
                "Do not add new counts or detections beyond supplied structured metadata.",
            ],
        },
    }


def response_is_safe(payload: Any) -> tuple[bool, list[str]]:
    flags: list[str] = []
    text = json.dumps(payload, sort_keys=True) if not isinstance(payload, str) else payload
    for family, pattern in BOUNDARY_PATTERNS + FACT_SOURCE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            flags.append(family)
    if isinstance(payload, dict):
        source_class = payload.get("source_class")
        if source_class != "model_generated_narrative":
            flags.append("missing_model_generated_narrative_source_class")
        if payload.get("candidate_event_modified") is True:
            flags.append("candidate_event_modified")
        if payload.get("official_record_created") is True or payload.get("action_created") is True:
            flags.append("official_or_action_created")
    else:
        flags.append("response_not_json_object")
    return not flags, flags


def run_probe(config: dict[str, Any], raw: dict[str, Any], output_root: Path, r2: dict[str, Any]) -> dict[str, Any]:
    probe = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "spark_vss_runtime_configured": config["spark_vss_runtime_configured"],
        "spark_vss_mode": config["spark_vss_mode"],
        "probe_attempted": False,
        "probe_executed": False,
        "probe_status": "NOT_CONFIGURED",
        "r7_ready": False,
        "health_probe": {"required": True, "status": "NOT_CONFIGURED"},
        "bounded_payload_probe": {"required_before_r7": True, "status": "NOT_CONFIGURED"},
        "timeout_seconds_default": config["timeout_seconds"],
        "max_response_bytes_default": config["max_response_bytes"],
        "latency_ms": 0,
        "http_status": None,
        "exit_code": None,
        "response_shape_safe": False,
        "guardrail_flags": [],
        "error_summary": None,
        "narration_records_emitted": 0,
        "candidate_event_modified_by_vss": False,
        "official_record_created": False,
        "action_created": False,
        "bounded_probe_payload_ref": None,
    }
    if raw["mode"] == "none":
        probe["error_summary"] = "No Spark VSS endpoint or command configured."
        return probe

    payload = build_bounded_probe_payload(r2)
    payload_path = output_root / "SPARK_VSS_BOUNDED_PROBE_PAYLOAD_R6E.json"
    write_json(payload_path, payload)
    probe["bounded_probe_payload_ref"] = "SPARK_VSS_BOUNDED_PROBE_PAYLOAD_R6E.json"
    probe["probe_attempted"] = True
    start = time.perf_counter()

    if raw["mode"] == "http_endpoint":
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            raw["endpoint"],
            data=data,
            method="POST",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=raw["timeout"]) as response:  # noqa: S310
                body = response.read(raw["max_response_bytes"] + 1).decode("utf-8", errors="replace")
                probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
                probe["http_status"] = int(response.status)
                probe["probe_executed"] = 200 <= int(response.status) < 300
                probe["health_probe"]["status"] = "SUCCESS" if probe["probe_executed"] else "FAILED"
                if len(body.encode("utf-8")) > raw["max_response_bytes"]:
                    probe["guardrail_flags"].append("response_too_large")
                response_payload = json.loads(body)
                safe, flags = response_is_safe(response_payload)
                probe["response_shape_safe"] = safe
                probe["guardrail_flags"].extend(flags)
                excerpt = output_root / "REDACTED_SPARK_VSS_RESPONSE_EXCERPT_R6E.txt"
                write_text(excerpt, redact_text(body[:1200]) or "")
                probe["response_excerpt_ref"] = rel(excerpt)
                if probe["probe_executed"] and safe and not probe["guardrail_flags"]:
                    probe["probe_status"] = "SUCCESS"
                    probe["bounded_payload_probe"]["status"] = "SUCCESS"
                    probe["r7_ready"] = True
                    probe["narration_records_emitted"] = 1
                else:
                    probe["probe_status"] = "UNSAFE_RESPONSE"
                    probe["bounded_payload_probe"]["status"] = "UNSAFE_RESPONSE"
        except TimeoutError:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "TIMEOUT"
            probe["health_probe"]["status"] = "TIMEOUT"
            probe["bounded_payload_probe"]["status"] = "NOT_EXECUTED"
            probe["error_summary"] = "Spark VSS endpoint probe timed out."
        except urllib.error.HTTPError as exc:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["http_status"] = int(exc.code)
            probe["probe_status"] = "FAILED"
            probe["health_probe"]["status"] = "FAILED"
            probe["bounded_payload_probe"]["status"] = "NOT_EXECUTED"
            probe["error_summary"] = f"HTTP error {exc.code}."
        except Exception as exc:  # noqa: BLE001
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "FAILED"
            probe["health_probe"]["status"] = "FAILED"
            probe["bounded_payload_probe"]["status"] = "NOT_EXECUTED"
            probe["error_summary"] = f"Endpoint probe failed: {exc}"
        return probe

    if raw["mode"] == "command_wrapper":
        input_path = output_root / "SPARK_VSS_BOUNDED_PROBE_PAYLOAD_R6E.json"
        output_path = output_root / "SPARK_VSS_COMMAND_RESPONSE_R6E.json"
        command = raw["command"]
        if "{input_json}" in command or "{output_json}" in command:
            command = command.replace("{input_json}", str(input_path)).replace("{output_json}", str(output_path))
        try:
            completed = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=raw["timeout"])
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["exit_code"] = completed.returncode
            probe["probe_executed"] = completed.returncode == 0
            probe["health_probe"]["status"] = "SUCCESS" if completed.returncode == 0 else "FAILED"
            if completed.stdout:
                stdout_path = output_root / "REDACTED_SPARK_VSS_STDOUT_EXCERPT_R6E.txt"
                write_text(stdout_path, redact_text(completed.stdout[:1200]) or "")
                probe["stdout_excerpt_ref"] = rel(stdout_path)
            if completed.stderr:
                stderr_path = output_root / "REDACTED_SPARK_VSS_STDERR_EXCERPT_R6E.txt"
                write_text(stderr_path, redact_text(completed.stderr[:1200]) or "")
                probe["stderr_excerpt_ref"] = rel(stderr_path)
            response_text = output_path.read_text(encoding="utf-8") if output_path.exists() else completed.stdout
            response_payload = json.loads(response_text)
            safe, flags = response_is_safe(response_payload)
            probe["response_shape_safe"] = safe
            probe["guardrail_flags"].extend(flags)
            if completed.returncode == 0 and safe and not probe["guardrail_flags"]:
                probe["probe_status"] = "SUCCESS"
                probe["bounded_payload_probe"]["status"] = "SUCCESS"
                probe["r7_ready"] = True
                probe["narration_records_emitted"] = 1
            else:
                probe["probe_status"] = "UNSAFE_RESPONSE" if completed.returncode == 0 else "FAILED"
                probe["bounded_payload_probe"]["status"] = probe["probe_status"]
                if completed.returncode != 0:
                    probe["error_summary"] = f"Command exited with code {completed.returncode}."
        except subprocess.TimeoutExpired:
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "TIMEOUT"
            probe["health_probe"]["status"] = "TIMEOUT"
            probe["bounded_payload_probe"]["status"] = "NOT_EXECUTED"
            probe["error_summary"] = "Spark VSS command probe timed out."
        except Exception as exc:  # noqa: BLE001
            probe["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            probe["probe_status"] = "FAILED"
            probe["health_probe"]["status"] = "FAILED"
            probe["bounded_payload_probe"]["status"] = "NOT_EXECUTED"
            probe["error_summary"] = f"Command probe failed: {exc}"
        return probe

    probe["probe_status"] = "FAILED"
    probe["error_summary"] = f"Unsupported Spark VSS mode: {raw['mode']}"
    return probe


def build_host_allocation(config: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    vss_status = "installing_or_not_configured"
    if config["spark_vss_runtime_configured"] and probe["probe_status"] == "SUCCESS":
        vss_status = "configured_and_probe_success"
    elif config["spark_vss_runtime_configured"]:
        vss_status = f"configured_but_probe_{probe['probe_status'].lower()}"
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "host_allocation": {
            "deepstream_metropolis": {
                "host": "txr-4070",
                "source_class": "sensor_inferred",
                "status": "proven_by_r2",
                "evidence": [
                    "DeepStream 8.0 container",
                    "gie-kitti-output-dir",
                    "container bundled samples/streams/sample_1080p_h264.mp4",
                    "24 car records normalized to vehicle_presence_candidate",
                ],
            },
            "vss": {
                "host": "Spark / DGX Spark",
                "source_class": "model_generated_narrative_only_not_fact_source",
                "status": vss_status,
            },
            "txr-3090": {
                "active_for_this_chain": False,
                "role": "data_graph_rapids_heavier_analytics",
            },
        },
        "r7_gate": "ready" if probe["r7_ready"] else "blocked_until_spark_vss_connectivity_success",
    }


def write_markdown_artifacts(output_root: Path, config: dict[str, Any], probe: dict[str, Any], r2: dict[str, Any]) -> None:
    write_text(
        output_root / "SPARK_VSS_PROVISIONING_RUNBOOK_R6E.md",
        f"""# Spark VSS Provisioning Runbook - R6E

## Goal

Expose one safe Spark VSS invocation path for the Metropolis/VSS media lane:
an HTTP endpoint or a command wrapper. VSS output is always
`model_generated_narrative` only and never a fact source.

## Locked Host Truth

- `txr-4070`: DeepStream / Metropolis, `sensor_inferred`, proven by R2.
- `Spark / DGX Spark`: intended VSS runtime host.
- `txr-3090`: inactive for this chain.

## Current Runtime State

- Spark VSS configured: `{str(config["spark_vss_runtime_configured"]).lower()}`
- Mode: `{config["spark_vss_mode"]}`
- Probe status: `{probe["probe_status"]}`
- R7 ready: `{str(probe["r7_ready"]).lower()}`

## R2 Evidence Summary

- Candidate event: `{r2.get("candidate_event_id")}`
- Candidate observations: `{r2.get("candidate_observations")}`
- Class: `{r2.get("class_label")}`
- Detection class: `{r2.get("detection_class")}`
- Evidence bundle: `{r2.get("evidence_bundle_ref")}`

## Required Spark Install Facts

- Spark hostname/IP or alias.
- VSS service, container, or wrapper name.
- Serving mode: endpoint or command.
- Model/runtime version.
- Port/path or command path.
- Auth mode, with secrets stored outside artifacts.
- Reachability from this runner host.
- Health probe result.
- Bounded sample probe result.

## R7 Gate

Open R7 only when the Spark VSS command or endpoint is configured, the probe
returns `SUCCESS`, the response is bounded and safe, and all audits pass.
""",
    )
    write_text(
        output_root / "SPARK_VSS_ENDPOINT_CHECKLIST_R6E.md",
        """# Spark VSS Endpoint Checklist - R6E

- [ ] Endpoint URL known.
- [ ] Endpoint reachable from the runner host.
- [ ] Auth method known; secrets are not written to artifacts.
- [ ] Health route available or bounded probe works.
- [ ] Timeout configured.
- [ ] Max response size configured.
- [ ] Response JSON parseable.
- [ ] Response includes `source_class=model_generated_narrative`.
- [ ] Response does not include detection, legal, identity, or action claims.
- [ ] R7 readiness gate can be derived deterministically.
""",
    )
    write_text(
        output_root / "SPARK_VSS_COMMAND_WRAPPER_CHECKLIST_R6E.md",
        """# Spark VSS Command Wrapper Checklist - R6E

- [ ] Command path known.
- [ ] Command executable by runner context.
- [ ] Input mode known: stdin or JSON file.
- [ ] Output mode known: stdout or JSON file.
- [ ] Timeout configured.
- [ ] stderr captured safely.
- [ ] Non-zero exit handled as partial or fail.
- [ ] Secrets redacted.
- [ ] Output JSON parseable.
- [ ] Output classified as `model_generated_narrative`.
- [ ] No candidate-event mutation.
""",
    )
    write_text(
        output_root / "SPARK_VSS_RUNTIME_CONFIG_TEMPLATE.env.example",
        """# Spark VSS runtime config for R6E/R7 gates.
# Fill exactly one invocation path. Keep secrets outside generated artifacts.

CITYBRAIN_SPARK_VSS_ENDPOINT=
CITYBRAIN_SPARK_VSS_COMMAND=
CITYBRAIN_SPARK_VSS_TIMEOUT_SECONDS=30
CITYBRAIN_SPARK_VSS_MAX_RESPONSE_BYTES=65536

# Optional examples:
# CITYBRAIN_SPARK_VSS_ENDPOINT=http://spark:38111/v1/probe
# CITYBRAIN_SPARK_VSS_COMMAND=python /path/to/vss_wrapper.py --input-json {input_json} --output-json {output_json}
""",
    )


def write_status_and_gate(output_root: Path, config: dict[str, Any], probe: dict[str, Any]) -> None:
    write_json(
        output_root / "SPARK_VSS_PROVISIONING_STATUS_R6E.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "spark_vss_runtime_configured": config["spark_vss_runtime_configured"],
            "spark_vss_mode": config["spark_vss_mode"],
            "install_state": "configured_probe_success" if probe["probe_status"] == "SUCCESS" else "external_install_in_progress_or_unknown",
            "probe_attempted": probe["probe_attempted"],
            "probe_executed": probe["probe_executed"],
            "probe_status": probe["probe_status"],
            "narration_records_emitted": probe["narration_records_emitted"],
            "candidate_event_modified_by_vss": probe["candidate_event_modified_by_vss"],
            "official_record_created": probe["official_record_created"],
            "action_created": probe["action_created"],
            "runtime_config": config,
        },
    )
    write_json(
        output_root / "SPARK_VSS_CONNECTIVITY_PROBE_PLAN_R6E.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "probe_plan": {
                "health_probe": probe["health_probe"],
                "bounded_payload_probe": probe["bounded_payload_probe"],
                "payload_source": "R2 candidate event and observation summary only",
                "forbidden": ["new detections", "fact-source claims", "official conclusions", "identity claims", "actions"],
                "timeout_seconds_default": config["timeout_seconds"],
                "max_response_bytes_default": config["max_response_bytes"],
            },
            "current_probe_result": probe,
        },
    )
    write_json(
        output_root / "R7_READINESS_GATE_R6E.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "r7_ready": probe["r7_ready"],
            "reason": "Spark VSS probe returned SUCCESS and all response-shape guardrails passed."
            if probe["r7_ready"]
            else f"Spark VSS is not ready for R7: probe_status={probe['probe_status']}.",
            "next_task_when_ready": "MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7" if probe["r7_ready"] else None,
        },
    )


def write_audits(output_root: Path, config: dict[str, Any], probe: dict[str, Any], host_allocation: dict[str, Any]) -> dict[str, str]:
    host_ok = (
        host_allocation["host_allocation"]["deepstream_metropolis"]["host"] == "txr-4070"
        and host_allocation["host_allocation"]["vss"]["host"] == "Spark / DGX Spark"
        and host_allocation["host_allocation"]["txr-3090"]["active_for_this_chain"] is False
    )
    source_ok = (
        host_allocation["host_allocation"]["deepstream_metropolis"]["source_class"] == "sensor_inferred"
        and host_allocation["host_allocation"]["vss"]["source_class"] == "model_generated_narrative_only_not_fact_source"
    )
    fact_findings = []
    boundary_findings = []
    for name in (
        "REDACTED_SPARK_VSS_RESPONSE_EXCERPT_R6E.txt",
        "REDACTED_SPARK_VSS_STDOUT_EXCERPT_R6E.txt",
        "REDACTED_SPARK_VSS_STDERR_EXCERPT_R6E.txt",
    ):
        path = output_root / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for family, pattern in FACT_SOURCE_PATTERNS:
            if re.search(pattern, text):
                fact_findings.append({"file": name, "family": family})
        for family, pattern in BOUNDARY_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                boundary_findings.append({"file": name, "family": family})
    no_action_ok = (
        probe["candidate_event_modified_by_vss"] is False
        and probe["official_record_created"] is False
        and probe["action_created"] is False
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
        secret_findings.append({"file": "SPARK_VSS_PROVISIONING_STATUS_R6E.json", "family": "redaction_failed"})

    write_json(output_root / "HOST_ALLOCATION_AUDIT_R6E.json", {"status": "PASS" if host_ok else "FAIL", "host_allocation": host_allocation})
    write_json(output_root / "SOURCE_CLASS_SEPARATION_AUDIT_R6E.json", {"status": "PASS" if source_ok else "FAIL", "source_boundary": SOURCE_BOUNDARY})
    write_json(output_root / "CLAIM_BOUNDARY_AUDIT_R6E.json", {"status": "PASS" if not boundary_findings else "FAIL", "findings": boundary_findings})
    write_json(output_root / "VSS_FACT_SOURCE_AUDIT_R6E.json", {"status": "PASS" if not fact_findings else "FAIL", "findings": fact_findings})
    write_json(
        output_root / "NO_ACTION_AUDIT_R6E.json",
        {
            "status": "PASS" if no_action_ok else "FAIL",
            "candidate_event_modified_by_vss": probe["candidate_event_modified_by_vss"],
            "official_record_created": probe["official_record_created"],
            "action_created": probe["action_created"],
        },
    )
    write_json(output_root / "SECRET_REDACTION_AUDIT_R6E.json", {"status": "PASS" if not secret_findings else "FAIL", "findings": secret_findings})
    return {
        "host_allocation": "PASS" if host_ok else "FAIL",
        "source_class_separation": "PASS" if source_ok else "FAIL",
        "claim_boundary": "PASS" if not boundary_findings else "FAIL",
        "vss_fact_source": "PASS" if not fact_findings else "FAIL",
        "no_action": "PASS" if no_action_ok else "FAIL",
        "secret": "PASS" if not secret_findings else "FAIL",
    }


def decide_status(config: dict[str, Any], probe: dict[str, Any], audits: dict[str, str], json_status: str = "PENDING", hash_status: str = "PENDING") -> str:
    if audits.get("vss_fact_source") == "FAIL":
        return FAIL_FACT_SOURCE
    if any(value == "FAIL" for value in audits.values()) or json_status == "FAIL" or hash_status == "FAIL":
        return FAIL_BOUNDARY
    if config["spark_vss_runtime_configured"] and probe["probe_status"] == "SUCCESS" and probe["r7_ready"]:
        return PASS_STATUS
    if config["spark_vss_runtime_configured"] and probe["probe_status"] in {"UNSAFE_RESPONSE"}:
        return PARTIAL_UNSAFE
    if config["spark_vss_runtime_configured"]:
        return PARTIAL_UNREACHABLE
    return PARTIAL_NOT_CONFIGURED


def write_closeout(
    output_root: Path,
    status: str,
    config: dict[str, Any],
    probe: dict[str, Any],
    audits: dict[str, str],
    r2: dict[str, Any],
    r6d: dict[str, Any],
    json_status: str = "PENDING",
    hash_status: str = "PENDING",
) -> None:
    write_json(
        output_root / "R6E_CLOSEOUT_DECISION.json",
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "final_status": status,
            "spark_vss_runtime_configured": config["spark_vss_runtime_configured"],
            "spark_vss_mode": config["spark_vss_mode"],
            "probe_attempted": probe["probe_attempted"],
            "probe_executed": probe["probe_executed"],
            "probe_status": probe["probe_status"],
            "r7_ready": probe["r7_ready"],
            "narration_records_emitted": probe["narration_records_emitted"],
            "candidate_event_modified_by_vss": probe["candidate_event_modified_by_vss"],
            "official_record_created": probe["official_record_created"],
            "action_created": probe["action_created"],
            "r2_lineage": r2,
            "r6d_lineage": r6d,
            "audits": {**audits, "json_parse": json_status, "hash_manifest": hash_status},
            "source_boundary": SOURCE_BOUNDARY,
            "validation_package_ref": PACKAGE_NAME,
        },
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
        output_root / "JSON_PARSE_REPORT_R6E.json",
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
    parser.add_argument("--spark-vss-endpoint")
    parser.add_argument("--spark-vss-command")
    parser.add_argument("--timeout-seconds", type=int, default=int(os.environ.get("CITYBRAIN_SPARK_VSS_TIMEOUT_SECONDS", "30")))
    parser.add_argument("--max-response-bytes", type=int, default=int(os.environ.get("CITYBRAIN_SPARK_VSS_MAX_RESPONSE_BYTES", "65536")))
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    reset_output_root(output_root)

    r2 = load_r2_lineage()
    r6d = load_r6d_lineage()
    config, raw = resolve_config(args)
    probe = run_probe(config, raw, output_root, r2)
    host_allocation = build_host_allocation(config, probe)

    write_markdown_artifacts(output_root, config, probe, r2)
    write_json(output_root / "RUNTIME_HOST_ALLOCATION_R6E.json", host_allocation)
    write_status_and_gate(output_root, config, probe)

    audits = write_audits(output_root, config, probe, host_allocation)
    status = decide_status(config, probe, audits)
    write_closeout(output_root, status, config, probe, audits, r2, r6d)

    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    status = decide_status(config, probe, audits, json_status, hash_status)
    write_closeout(output_root, status, config, probe, audits, r2, r6d, json_status, hash_status)
    json_status = validate_json_outputs(output_root)
    hash_status = write_hash_manifest(output_root)
    create_package_zip(output_root)

    print(f"Final status: {status}")
    print(f"Runner: {rel(Path(__file__))}")
    print(f"Output root: {rel(output_root)}")
    print(f"Freeze ZIP: {rel(output_root / PACKAGE_NAME)}")
    print(f"Spark VSS configured/mode: {str(config['spark_vss_runtime_configured']).lower()}/{config['spark_vss_mode']}")
    print(f"Probe attempted/executed/status: {str(probe['probe_attempted']).lower()}/{str(probe['probe_executed']).lower()}/{probe['probe_status']}")
    print(f"R7 ready: {str(probe['r7_ready']).lower()}")
    print(f"Narration records emitted: {probe['narration_records_emitted']}")
    print(f"JSON parse: {json_status}")
    print(f"Hash manifest: {hash_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
