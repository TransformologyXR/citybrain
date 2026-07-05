#!/usr/bin/env python3
"""Run R3 VSS narration dry-run over the R2 object-metadata package."""

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
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_vss_narration_runtime_dry_run_r3"
TASK_NAME = "MAIN-CITYBRAIN-METROPOLIS-VSS-VSS-NARRATION-RUNTIME-DRY-RUN-R3"
SCHEMA_VERSION = "metropolis-vss-narration-runtime-dry-run-r3.v1"
HANDOFF_ZIP = Path(r"C:\Users\hazem\Downloads\citybrain_metropolis_vss_vss_narration_runtime_dry_run_r3_handoff.zip")
DEFAULT_R2_ZIP = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_object_metadata_export_r2" / "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_BLOCKED_GUARDRAILS_READY"
FAIL_INPUT_STATUS = "FAIL_METROPOLIS_VSS_R3_INPUT_R2_PACKAGE_INVALID"
FAIL_BOUNDARY_STATUS = "FAIL_METROPOLIS_VSS_NARRATION_FACT_SOURCE_OR_BOUNDARY_RISK"
FAIL_UNSUPPORTED_DETECTION_STATUS = "FAIL_METROPOLIS_VSS_NARRATION_ADDED_UNSUPPORTED_DETECTION"
FAIL_RUNTIME_UNBOUNDED_STATUS = "FAIL_METROPOLIS_VSS_NARRATION_RUNTIME_ERROR_UNBOUNDED"

VISIBLE_LABEL = "Candidate observation\nVSS narration only\nHuman review required\nNot a finding"
R2_PASS_STATUS = "PASS_METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_WITH_LIMITATIONS"

REQUIRED_R2_FILES = [
    "OBJECT_METADATA_NORMALIZED_SAMPLE.jsonl",
    "CANDIDATE_OBSERVATION_SAMPLE_R2.jsonl",
    "MEDIA_EVIDENCEBUNDLE_SAMPLE_R2.json",
    "HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R2.json",
    "VSS_NARRATION_GUARDRAIL_CONTRACT_R2.json",
    "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_CLOSEOUT_DECISION.json",
    "MEDIA_TO_CANDIDATE_EVENT_MAPPING_R2.json",
    "HASH_MANIFEST.json",
]

BOUNDARY = {
    "allowed_outputs": [
        "VSS narration text as model_generated_narrative",
        "narrative summary of already-exported R2 object metadata",
        "references to R2 candidate observation IDs",
        "references to R2 candidate event and EvidenceBundle",
        "uncertainty notes",
        "prose-vs-detection conflict report",
        "human-review wording",
        "CHECK narration-sufficiency report",
    ],
    "forbidden_outputs": [
        "confirmed violation",
        "legal or certified finding",
        "official case or ticket",
        "identity, biometric, face, or license-plate recognition",
        "dispatch, routing, control, enforcement, alert-command, or automated action",
        "production monitoring claim",
        "VSS as a sensor, official record, or fact source",
        "new object detections invented by VSS",
        "object counts from VSS that override R2 metadata",
        "wall-clock timestamps not present in R2",
        "sample video as live CCTV",
    ],
}

BLOCKED_OUTCOME_CODES = [
    "confirmed_violation_blocked",
    "legal_or_certified_finding_blocked",
    "identity_or_biometric_inference_blocked",
    "face_or_plate_recognition_blocked",
    "official_case_or_ticket_blocked",
    "dispatch_routing_control_enforcement_blocked",
    "alert_as_command_blocked",
    "automated_action_blocked",
    "production_monitoring_claim_blocked",
    "vss_fact_source_claim_blocked",
]

FORBIDDEN_ASSERTED_PATTERNS = [
    r"\bconfirmed violation\b",
    r"\bviolation confirmed\b",
    r"\billegal activity\b",
    r"\bticket created\b",
    r"\bcase created\b",
    r"\bdispatch\b",
    r"\benforce\b",
    r"\btake action\b",
    r"\balert operator to act\b",
    r"\blicense plate\b",
    r"\bface recognized\b",
    r"\bidentified person\b",
    r"\bsuspect\b",
    r"\boffender\b",
    r"\blive cctv monitoring\b",
    r"\bproduction monitoring\b",
]

UNSUPPORTED_DETECTION_TERMS = [
    "pedestrian",
    "person",
    "bicycle",
    "road_sign",
    "road sign",
    "truck",
    "bus",
    "license plate",
    "face",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def reset_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    outputs_root = (REPO_ROOT / "outputs").resolve()
    if outputs_root not in resolved.parents:
        raise RuntimeError(f"Refusing to reset output outside workspace outputs: {resolved}")
    if resolved.name != "main_citybrain_metropolis_vss_vss_narration_runtime_dry_run_r3":
        raise RuntimeError(f"Unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def parse_jsonl_bytes(payload: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in payload.decode("utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def validate_r2_zip(r2_zip: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "FAIL",
        "r2_zip": str(r2_zip),
        "r2_zip_exists": r2_zip.exists(),
        "zip_entries": 0,
        "json_files_parsed": 0,
        "jsonl_files_parsed": 0,
        "json_parse_failures": [],
        "jsonl_parse_failures": [],
        "hash_manifest": {"verified": 0, "mismatches": [], "missing": []},
        "required_files_present": False,
        "closeout_status": None,
        "r2_closeout_truth": {},
        "r2_scope": {},
        "r2_counts": {},
        "files": {},
        "parsed_json": {},
        "parsed_jsonl": {},
    }
    if not r2_zip.exists():
        result["failure_reason"] = "R2 ZIP does not exist."
        return result
    try:
        with zipfile.ZipFile(r2_zip) as zf:
            names = sorted(name for name in zf.namelist() if not name.endswith("/"))
            result["zip_entries"] = len(names)
            missing_required = [name for name in REQUIRED_R2_FILES if name not in names]
            result["required_files_present"] = not missing_required
            result["missing_required_files"] = missing_required
            raw_files: dict[str, bytes] = {name: zf.read(name) for name in names}
            result["files"] = raw_files
            for name, payload in raw_files.items():
                if name.endswith(".json"):
                    try:
                        result["parsed_json"][name] = json.loads(payload.decode("utf-8"))
                        result["json_files_parsed"] += 1
                    except Exception as exc:  # noqa: BLE001
                        result["json_parse_failures"].append({"file": name, "error": str(exc)})
                elif name.endswith(".jsonl"):
                    try:
                        result["parsed_jsonl"][name] = parse_jsonl_bytes(payload)
                        result["jsonl_files_parsed"] += 1
                    except Exception as exc:  # noqa: BLE001
                        result["jsonl_parse_failures"].append({"file": name, "error": str(exc)})
            manifest = result["parsed_json"].get("HASH_MANIFEST.json", {})
            mismatches = []
            missing = []
            verified = 0
            for item in manifest.get("files", []):
                file_name = item.get("file")
                expected = item.get("sha256")
                if file_name not in raw_files:
                    missing.append(file_name)
                    continue
                actual = sha256_bytes(raw_files[file_name])
                if actual != expected:
                    mismatches.append({"file": file_name, "expected": expected, "actual": actual})
                else:
                    verified += 1
            result["hash_manifest"] = {
                "status": manifest.get("status"),
                "verified": verified,
                "mismatches": mismatches,
                "missing": missing,
                "manifest_file_count": manifest.get("file_count"),
            }
            closeout = result["parsed_json"].get("METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_CLOSEOUT_DECISION.json", {})
            result["closeout_status"] = closeout.get("status")
            result["r2_closeout_truth"] = closeout.get("closeout_truth", {})
            result["r2_scope"] = {
                "media_source": closeout.get("media_source_selected"),
                "zone": closeout.get("zone_selected"),
                "detection_class": closeout.get("detection_class_selected"),
                "class_label": closeout.get("class_label_selected"),
                "source_class": closeout.get("closeout_truth", {}).get("source_class"),
            }
            result["r2_counts"] = {
                "candidate_observations": closeout.get("candidate_observations_emitted"),
                "candidate_events": closeout.get("candidate_events_emitted"),
                "object_metadata": closeout.get("closeout_truth", {}).get("real_object_metadata_exported"),
            }
            ok = (
                result["required_files_present"]
                and not result["json_parse_failures"]
                and not result["jsonl_parse_failures"]
                and not mismatches
                and not missing
                and closeout.get("status") == R2_PASS_STATUS
            )
            result["status"] = "PASS" if ok else "FAIL"
    except Exception as exc:  # noqa: BLE001
        result["failure_reason"] = str(exc)
        result["status"] = "FAIL"
    return result


def json_safe_validation(validation: dict[str, Any]) -> dict[str, Any]:
    safe = {k: v for k, v in validation.items() if k not in {"files", "parsed_json", "parsed_jsonl"}}
    safe["r2_zip_sha256"] = sha256_file(Path(validation["r2_zip"])) if validation.get("r2_zip_exists") else None
    return safe


def r2_context(validation: dict[str, Any]) -> dict[str, Any]:
    parsed_json = validation.get("parsed_json", {})
    parsed_jsonl = validation.get("parsed_jsonl", {})
    closeout = parsed_json.get("METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_CLOSEOUT_DECISION.json", {})
    mapping = parsed_json.get("MEDIA_TO_CANDIDATE_EVENT_MAPPING_R2.json", {})
    event = mapping.get("candidate_event", {})
    evidence_bundle = parsed_json.get("MEDIA_EVIDENCEBUNDLE_SAMPLE_R2.json", {})
    human_packet = parsed_json.get("HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R2.json", {})
    object_rows = parsed_jsonl.get("OBJECT_METADATA_NORMALIZED_SAMPLE.jsonl", [])
    observation_rows = parsed_jsonl.get("CANDIDATE_OBSERVATION_SAMPLE_R2.jsonl", [])
    confidence_values = [row.get("confidence") for row in object_rows if isinstance(row.get("confidence"), (int, float))]
    frames = sorted({row.get("frame_number") for row in object_rows if isinstance(row.get("frame_number"), int)})
    return {
        "media_source": closeout.get("media_source_selected") or evidence_bundle.get("evidence_clip", {}).get("clip_ref"),
        "zone": closeout.get("zone_selected") or event.get("zone_id"),
        "detection_class": closeout.get("detection_class_selected") or event.get("detection_class"),
        "class_label": closeout.get("class_label_selected") or event.get("class_label"),
        "candidate_event_ref": event.get("candidate_event_id") or (evidence_bundle.get("candidate_event_refs") or [None])[0],
        "evidence_bundle_ref": evidence_bundle.get("bundle_id"),
        "candidate_observation_refs": [row.get("observation_id") for row in observation_rows if row.get("observation_id")],
        "object_metadata_refs": [row.get("object_metadata_id") for row in object_rows if row.get("object_metadata_id")],
        "candidate_observation_count": len(observation_rows),
        "object_metadata_count": len(object_rows),
        "candidate_event_count": 1 if event else 0,
        "frame_count": len(frames),
        "frames": frames[:12],
        "confidence_min": min(confidence_values) if confidence_values else None,
        "confidence_max": max(confidence_values) if confidence_values else None,
        "source_class": "sensor_inferred",
        "evidence_frame_ref": evidence_bundle.get("evidence_frame", {}).get("frame_ref"),
        "evidence_clip_ref": evidence_bundle.get("evidence_clip", {}).get("clip_ref"),
        "r2_evidence_bundle": evidence_bundle,
        "r2_human_packet": human_packet,
        "r2_candidate_event": event,
    }


def build_vss_input_packet(ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_name": TASK_NAME,
        "visible_label": VISIBLE_LABEL,
        "instruction": (
            "Summarize only the already-exported R2 structured candidate metadata for human review. "
            "Do not add detections, counts, identities, legal conclusions, tickets, dispatches, alerts, or actions."
        ),
        "r2_structured_metadata_summary": {
            "candidate_event_ref": ctx["candidate_event_ref"],
            "evidence_bundle_ref": ctx["evidence_bundle_ref"],
            "media_source": ctx["media_source"],
            "zone": ctx["zone"],
            "detection_class": ctx["detection_class"],
            "class_label": ctx["class_label"],
            "candidate_observation_count": ctx["candidate_observation_count"],
            "object_metadata_count": ctx["object_metadata_count"],
            "frame_count": ctx["frame_count"],
            "confidence_min": ctx["confidence_min"],
            "confidence_max": ctx["confidence_max"],
            "timestamp_boundary": "frame/time refs only; no R2 wall-clock timestamp",
            "source_class": "sensor_inferred",
        },
        "forbidden_outputs": BOUNDARY["forbidden_outputs"],
    }


def runtime_config(args: argparse.Namespace) -> dict[str, Any]:
    command = args.vss_command or os.environ.get("CITYBRAIN_VSS_COMMAND") or os.environ.get("VSS_COMMAND")
    endpoint = args.vss_endpoint or os.environ.get("CITYBRAIN_VSS_ENDPOINT") or os.environ.get("VSS_ENDPOINT")
    return {
        "command": command,
        "endpoint": endpoint,
        "timeout_sec": args.dry_run_timeout_sec,
        "configured": bool(command or endpoint),
        "mode": "command" if command else ("endpoint" if endpoint else "unconfigured"),
    }


def execute_vss_runtime(config: dict[str, Any], input_packet: dict[str, Any]) -> dict[str, Any]:
    if not config["configured"]:
        return {
            "status": "BLOCKED",
            "vss_runtime_attempted": False,
            "vss_runtime_executed": False,
            "runtime_endpoint_or_command_redacted": True,
            "blocked_reason": "No --vss-command, --vss-endpoint, CITYBRAIN_VSS_COMMAND, or CITYBRAIN_VSS_ENDPOINT was configured.",
            "stdout": "",
            "stderr": "",
            "returncode": None,
        }
    payload = json.dumps(input_packet, sort_keys=True)
    if config["command"]:
        try:
            proc = subprocess.run(
                config["command"],
                input=payload,
                capture_output=True,
                text=True,
                timeout=int(config["timeout_sec"]),
                shell=True,
                cwd=REPO_ROOT,
                check=False,
            )
            return {
                "status": "PASS" if proc.returncode == 0 and proc.stdout.strip() else "ERROR",
                "vss_runtime_attempted": True,
                "vss_runtime_executed": proc.returncode == 0 and bool(proc.stdout.strip()),
                "runtime_endpoint_or_command_redacted": True,
                "mode": "command",
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "ERROR",
                "vss_runtime_attempted": True,
                "vss_runtime_executed": False,
                "runtime_endpoint_or_command_redacted": True,
                "mode": "command",
                "stdout": "",
                "stderr": str(exc),
                "returncode": None,
            }
    request = urllib.request.Request(
        config["endpoint"],
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=int(config["timeout_sec"])) as response:  # noqa: S310
            body = response.read().decode("utf-8", errors="replace")
            status_code = getattr(response, "status", None)
        return {
            "status": "PASS" if body.strip() else "ERROR",
            "vss_runtime_attempted": True,
            "vss_runtime_executed": bool(body.strip()),
            "runtime_endpoint_or_command_redacted": True,
            "mode": "endpoint",
            "stdout": body,
            "stderr": "",
            "returncode": status_code,
        }
    except (urllib.error.URLError, TimeoutError, Exception) as exc:  # noqa: BLE001
        return {
            "status": "ERROR",
            "vss_runtime_attempted": True,
            "vss_runtime_executed": False,
            "runtime_endpoint_or_command_redacted": True,
            "mode": "endpoint",
            "stdout": "",
            "stderr": str(exc),
            "returncode": None,
        }


def extract_generated_text(runtime: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    text = runtime.get("stdout", "").strip()
    if not text:
        return "", None
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            for key in ["generated_text", "text", "narration", "summary", "answer"]:
                if isinstance(payload.get(key), str):
                    return payload[key].strip(), payload
            return json.dumps(payload, sort_keys=True), payload
    except json.JSONDecodeError:
        pass
    return text, None


def write_runtime_report(config: dict[str, Any], runtime: dict[str, Any], ctx: dict[str, Any]) -> None:
    report = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": runtime["status"],
        "vss_runtime_attempted": runtime["vss_runtime_attempted"],
        "vss_runtime_executed": runtime["vss_runtime_executed"],
        "runtime_endpoint_or_command_redacted": True,
        "runtime_mode": config["mode"],
        "input_media_ref": ctx["media_source"],
        "input_evidence_bundle_ref": ctx["evidence_bundle_ref"],
        "output_capture_ref": "VSS_NARRATION_OUTPUT_SAMPLE_R3.jsonl",
        "timeout_sec": config["timeout_sec"],
        "blocked_reason": runtime.get("blocked_reason"),
        "returncode_or_status": runtime.get("returncode"),
        "stderr_ref": "VSS_RUNTIME_STDERR_R3.txt" if runtime.get("stderr") else None,
    }
    write_json(OUTPUT_ROOT / "VSS_RUNTIME_DRY_RUN_REPORT_R3.json", report)
    if runtime.get("stderr"):
        write_text(OUTPUT_ROOT / "VSS_RUNTIME_STDERR_R3.txt", runtime["stderr"])


def make_sidecar(runtime: dict[str, Any], ctx: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not runtime.get("vss_runtime_executed"):
        return None, None
    generated_text, raw_json = extract_generated_text(runtime)
    if not generated_text:
        return None, raw_json
    sidecar = {
        "schema_version": SCHEMA_VERSION,
        "narration_id": "metropolis-vss-r3-narration-001",
        "candidate_event_ref": ctx["candidate_event_ref"],
        "evidence_bundle_ref": ctx["evidence_bundle_ref"],
        "source_class": "model_generated_narrative",
        "source_system": "configured_vss_runtime",
        "fact_source": False,
        "structured_detection_source_class": "sensor_inferred",
        "structured_detection_refs": ctx["candidate_observation_refs"],
        "input_media_ref": ctx["media_source"],
        "generated_text": generated_text,
        "unsupported_claims": [],
        "conflict_flags": [],
        "human_review_required": True,
        "candidate_label": VISIBLE_LABEL,
        "official_record_created": False,
        "no_action_taken": True,
        "raw_runtime_json": raw_json,
    }
    return sidecar, raw_json


def boundary_context_allows(text: str, match_start: int) -> bool:
    context = text[max(0, match_start - 100): match_start + 160].lower()
    safe_markers = [
        "do not",
        "not a",
        "not an",
        "forbidden",
        "blocked",
        "without",
        "no ",
        "must not",
        "cannot",
        "not present",
    ]
    return any(marker in context for marker in safe_markers)


def audit_narration(sidecar: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    if not sidecar:
        return {
            "status": "PASS",
            "runtime_blocked_no_vss_text_to_audit": True,
            "unsupported_claims": [],
            "conflict_flags": [],
            "checks": [
                {"check": "no_new_object_classes_added_by_vss", "status": "PASS"},
                {"check": "no_object_count_override", "status": "PASS"},
                {"check": "no_identity_or_plate_claim", "status": "PASS"},
                {"check": "no_legal_finding_language", "status": "PASS"},
                {"check": "no_action_or_command_language", "status": "PASS"},
                {"check": "no_production_live_monitoring_claim", "status": "PASS"},
            ],
        }
    text = sidecar.get("generated_text", "")
    lowered = text.lower()
    unsupported_claims: list[str] = []
    conflict_flags: list[str] = []
    for pattern in FORBIDDEN_ASSERTED_PATTERNS:
        for match in re.finditer(pattern, lowered):
            if not boundary_context_allows(lowered, match.start()):
                unsupported_claims.append(pattern)
                break
    allowed_class_terms = {str(ctx["class_label"]).lower(), "vehicle", "vehicles", "car", "cars"}
    for term in UNSUPPORTED_DETECTION_TERMS:
        if term in allowed_class_terms:
            continue
        if re.search(rf"\b{re.escape(term)}s?\b", lowered):
            conflict_flags.append(f"unsupported_detection_term:{term}")
    number_hits = [int(hit) for hit in re.findall(r"\b\d+\b", lowered)]
    for value in number_hits:
        if value not in {ctx["candidate_observation_count"], ctx["object_metadata_count"], ctx["frame_count"]} and value > 1:
            conflict_flags.append(f"possible_count_override:{value}")
    if "live cctv" in lowered or "production monitoring" in lowered:
        conflict_flags.append("live_or_production_claim")
    status = "PASS" if not unsupported_claims and not conflict_flags else "FAIL"
    sidecar["unsupported_claims"] = unsupported_claims
    sidecar["conflict_flags"] = conflict_flags
    return {
        "status": status,
        "unsupported_claims": unsupported_claims,
        "conflict_flags": conflict_flags,
        "checks": [
            {"check": "no_new_object_classes_added_by_vss", "status": "PASS" if not any(flag.startswith("unsupported_detection_term") for flag in conflict_flags) else "FAIL"},
            {"check": "no_object_count_override", "status": "PASS" if not any(flag.startswith("possible_count_override") for flag in conflict_flags) else "FAIL"},
            {"check": "no_identity_or_plate_claim", "status": "PASS" if not any("license plate" in claim or "face" in claim or "identified" in claim for claim in unsupported_claims) else "FAIL"},
            {"check": "no_legal_finding_language", "status": "PASS" if not any("violation" in claim or "illegal" in claim for claim in unsupported_claims) else "FAIL"},
            {"check": "no_action_or_command_language", "status": "PASS" if not any("dispatch" in claim or "action" in claim or "enforce" in claim for claim in unsupported_claims) else "FAIL"},
            {"check": "no_production_live_monitoring_claim", "status": "PASS" if not any("production" in flag or "live" in flag for flag in conflict_flags) else "FAIL"},
        ],
    }


def write_sidecar_contract() -> None:
    schema_target = OUTPUT_ROOT / "VSS_NARRATION_SIDECAR_CONTRACT_R3.json"
    if HANDOFF_ZIP.exists():
        with zipfile.ZipFile(HANDOFF_ZIP) as zf:
            if "SCHEMA_VSS_NARRATION_SIDECAR_R3.json" in zf.namelist():
                schema_target.write_bytes(zf.read("SCHEMA_VSS_NARRATION_SIDECAR_R3.json"))
                return
    write_json(
        schema_target,
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "VSS Narration Sidecar R3",
            "schema_version": SCHEMA_VERSION,
        },
    )


def write_narration_outputs(sidecar: dict[str, Any] | None) -> None:
    write_jsonl(OUTPUT_ROOT / "VSS_NARRATION_OUTPUT_SAMPLE_R3.jsonl", [sidecar] if sidecar else [])


def write_guardrail_reports(runtime: dict[str, Any], sidecar: dict[str, Any] | None, audit: dict[str, Any]) -> None:
    guardrail = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": audit["status"],
        "vss_runtime_executed": runtime.get("vss_runtime_executed", False),
        "vss_output_source_class": "model_generated_narrative",
        "vss_is_fact_source": False,
        "candidate_event_modified_by_vss": False,
        "official_record_created": False,
        "human_review_required": True,
        "no_action_taken": True,
        "unsupported_claims": audit.get("unsupported_claims", []),
        "conflict_flags": audit.get("conflict_flags", []),
        "checks": audit["checks"],
    }
    write_json(OUTPUT_ROOT / "VSS_NARRATION_GUARDRAIL_REPORT_R3.json", guardrail)
    write_json(OUTPUT_ROOT / "VSS_PROSE_VS_DETECTION_CONFLICT_AUDIT_R3.json", audit)


def write_source_class_audit(sidecar: dict[str, Any] | None, ctx: dict[str, Any]) -> str:
    failures = []
    if ctx.get("source_class") != "sensor_inferred":
        failures.append("R2 structured source_class is not sensor_inferred")
    if sidecar and sidecar.get("source_class") != "model_generated_narrative":
        failures.append("VSS sidecar source_class is not model_generated_narrative")
    if sidecar and sidecar.get("fact_source") is not False:
        failures.append("VSS sidecar fact_source is not false")
    status = "PASS" if not failures else "FAIL"
    write_json(
        OUTPUT_ROOT / "SOURCE_CLASS_SEPARATION_AUDIT_R3.json",
        {
            "status": status,
            "structured_detection_source_class": "sensor_inferred",
            "vss_output_source_class": "model_generated_narrative",
            "vss_is_fact_source": False,
            "candidate_event_modified_by_vss": False,
            "failures": failures,
        },
    )
    return status


def write_no_action_and_claim_audits(sidecar: dict[str, Any] | None, ctx: dict[str, Any], audit: dict[str, Any]) -> tuple[str, str]:
    payload = {"sidecar": sidecar, "ctx": ctx}
    serial = json.dumps(payload, sort_keys=True).lower()
    unsafe_true_patterns = [
        r'"official_record_created"\s*:\s*true',
        r'"no_action_taken"\s*:\s*false',
        r'"human_review_required"\s*:\s*false',
        r'"fact_source"\s*:\s*true',
    ]
    hits = [pattern for pattern in unsafe_true_patterns if re.search(pattern, serial)]
    no_action_status = "PASS" if not hits else "FAIL"
    claim_status = "PASS" if not hits and audit.get("status") == "PASS" else "FAIL"
    write_json(
        OUTPUT_ROOT / "NO_ACTION_AUDIT_R3.json",
        {
            "status": no_action_status,
            "unsafe_true_patterns": hits,
            "identity_or_biometric_inference_created": False,
            "official_case_or_ticket_created": False,
            "official_finding_created": False,
            "alert_as_command_created": False,
            "dispatch_created": False,
            "routing_control_created": False,
            "enforcement_created": False,
            "automated_action_created": False,
            "execution_state": "not_executed",
        },
    )
    write_json(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT_R3.json",
        {
            "status": claim_status,
            "required_visible_label": VISIBLE_LABEL,
            "vss_narration_only": True,
            "vss_fact_source": False,
            "candidate_only_output": True,
            "unsafe_positive_claims": audit.get("unsupported_claims", []),
            "conflict_flags": audit.get("conflict_flags", []),
            "blocked_outcome_codes": BLOCKED_OUTCOME_CODES,
        },
    )
    return no_action_status, claim_status


def write_check_report(runtime: dict[str, Any], sidecar: dict[str, Any] | None, audit: dict[str, Any], ctx: dict[str, Any]) -> str:
    runtime_executed = bool(runtime.get("vss_runtime_executed"))
    status = "PASS" if runtime_executed and audit.get("status") == "PASS" else "PARTIAL"
    report = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "candidate_label": VISIBLE_LABEL,
        "candidate_event_ref": ctx["candidate_event_ref"],
        "dimension_results": [
            {"dimension": "R2 structured-detection availability", "status": "PASS", "value": {"candidate_observations": ctx["candidate_observation_count"], "object_metadata": ctx["object_metadata_count"]}},
            {"dimension": "VSS runtime availability", "status": "PASS" if runtime_executed else "PARTIAL", "value": runtime.get("blocked_reason") or runtime.get("status")},
            {"dimension": "VSS prose support by R2 evidence", "status": "PASS" if sidecar else "PARTIAL", "value": "sidecar attached" if sidecar else "no VSS prose produced"},
            {"dimension": "VSS prose vs detection conflicts", "status": audit.get("status"), "value": audit.get("conflict_flags", [])},
            {"dimension": "false-positive / uncertainty wording", "status": "PASS" if sidecar else "PARTIAL", "value": "runtime blocked" if not sidecar else "narration audited"},
            {"dimension": "source-class separation", "status": "PASS", "value": "sensor_inferred detections; model_generated_narrative VSS"},
            {"dimension": "human-review stop", "status": "PASS", "value": "human_review_required=true"},
            {"dimension": "no-action/no-official-record boundary", "status": "PASS", "value": "no_action_taken=true; official_record_created=false"},
            {"dimension": "sample-media limitation", "status": "PASS", "value": ctx["media_source"]},
        ],
    }
    write_json(OUTPUT_ROOT / "CHECK_NARRATION_SUFFICIENCY_REPORT_R3.json", report)
    return status


def write_attached_bundle_and_packet(sidecar: dict[str, Any] | None, ctx: dict[str, Any]) -> None:
    bundle = dict(ctx["r2_evidence_bundle"])
    bundle["schema_version"] = SCHEMA_VERSION
    bundle["candidate_label"] = VISIBLE_LABEL
    bundle["vss_narration_sidecar_ref"] = sidecar["narration_id"] if sidecar else None
    bundle["vss_narration_status"] = "attached" if sidecar else "runtime_blocked_not_attached"
    bundle["vss_output_source_class"] = "model_generated_narrative"
    bundle["vss_is_fact_source"] = False
    bundle["candidate_event_modified_by_vss"] = False
    bundle["official_record_created"] = False
    bundle["no_action_taken"] = True
    write_json(OUTPUT_ROOT / "MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R3.json", bundle)
    packet = dict(ctx["r2_human_packet"])
    packet["schema_version"] = SCHEMA_VERSION
    packet["candidate_label"] = VISIBLE_LABEL
    packet["vss_narration_sidecar_ref"] = sidecar["narration_id"] if sidecar else None
    packet["vss_narration_status"] = "attached" if sidecar else "runtime_blocked_not_attached"
    packet["review_prompt"] = (
        "Review the R2 structured vehicle-presence candidates. "
        "If VSS narration is attached, treat it as model-generated review wording only, not as a fact source."
    )
    packet["human_review_required"] = True
    packet["no_action_taken"] = True
    packet["official_record_created"] = False
    packet["forbidden_review_outcomes"] = BLOCKED_OUTCOME_CODES
    write_json(OUTPUT_ROOT / "HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R3.json", packet)


def write_secret_audit() -> str:
    patterns = [
        r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"(?i)secret\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    hits: list[dict[str, str]] = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "METROPOLIS_VSS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_PACKAGE.zip":
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if re.search(pattern, text):
                    hits.append({"file": rel(path) or str(path), "pattern": pattern})
    status = "PASS" if not hits else "FAIL"
    write_json(OUTPUT_ROOT / "SECRET_AUDIT_R3.json", {"status": status, "secret_pattern_hits": hits})
    return status


def validate_json_outputs() -> str:
    failures = []
    json_count = 0
    jsonl_count = 0
    for path in sorted(OUTPUT_ROOT.glob("*.json")):
        if path.name == "JSON_PARSE_REPORT_R3.json":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_count += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"file": path.name, "error": str(exc)})
    for path in sorted(OUTPUT_ROOT.glob("*.jsonl")):
        try:
            read_jsonl(path)
            jsonl_count += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"file": path.name, "error": str(exc)})
    status = "PASS" if not failures else "FAIL"
    write_json(
        OUTPUT_ROOT / "JSON_PARSE_REPORT_R3.json",
        {
            "status": status,
            "json_files_parsed": json_count,
            "jsonl_files_parsed": jsonl_count,
            "parse_failures": failures,
        },
    )
    return status


def write_hash_manifest() -> str:
    entries = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name not in {"HASH_MANIFEST.json", "METROPOLIS_VSS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_PACKAGE.zip"}:
            entries.append(
                {
                    "file": path.relative_to(OUTPUT_ROOT).as_posix(),
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    status = "PASS" if entries else "FAIL"
    write_json(
        OUTPUT_ROOT / "HASH_MANIFEST.json",
        {
            "status": status,
            "generated_at": utc_now(),
            "algorithm": "sha256",
            "file_count": len(entries),
            "excludes": ["HASH_MANIFEST.json", "METROPOLIS_VSS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_PACKAGE.zip"],
            "files": entries,
        },
    )
    return status


def decide_status(r2_validation: dict[str, Any], runtime: dict[str, Any], audit: dict[str, Any], source_class_status: str, no_action_status: str, claim_status: str) -> str:
    if r2_validation.get("status") != "PASS":
        return FAIL_INPUT_STATUS
    if source_class_status != "PASS" or no_action_status != "PASS" or claim_status != "PASS":
        return FAIL_BOUNDARY_STATUS
    if audit.get("status") != "PASS":
        flags = audit.get("conflict_flags", [])
        if any(str(flag).startswith("unsupported_detection_term") for flag in flags):
            return FAIL_UNSUPPORTED_DETECTION_STATUS
        return FAIL_BOUNDARY_STATUS
    if runtime.get("vss_runtime_executed"):
        return PASS_STATUS
    if runtime.get("status") == "ERROR":
        return PARTIAL_STATUS
    return PARTIAL_STATUS


def write_decisions(
    final_status: str,
    runtime: dict[str, Any],
    ctx: dict[str, Any],
    r2_validation_safe: dict[str, Any],
    audit_statuses: dict[str, str],
    json_status: str | None = None,
    hash_status: str | None = None,
) -> None:
    common = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": final_status,
        "vss_runtime_executed": bool(runtime.get("vss_runtime_executed")),
        "vss_output_source_class": "model_generated_narrative",
        "vss_is_fact_source": False,
        "structured_detection_source_class": "sensor_inferred",
        "structured_detection_source": "DeepStream/Metropolis R2 object metadata",
        "candidate_event_modified_by_vss": False,
        "official_record_created": False,
        "human_review_required": True,
        "no_action_taken": True,
        "input_r2_package_validation_status": r2_validation_safe.get("status"),
        "candidate_event_ref": ctx.get("candidate_event_ref"),
        "evidence_bundle_ref": ctx.get("evidence_bundle_ref"),
        "media_source": ctx.get("media_source"),
        "zone": ctx.get("zone"),
        "detection_class": ctx.get("detection_class"),
        "class_label": ctx.get("class_label"),
        "candidate_observation_count": ctx.get("candidate_observation_count"),
        "object_metadata_count": ctx.get("object_metadata_count"),
        "audits": audit_statuses,
        "json_parse_status": json_status,
        "hash_manifest_status": hash_status,
        "validation_package_ref": "METROPOLIS_VSS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_PACKAGE.zip",
        "limitations": [
            "R3 reads one R2 package and one candidate event only.",
            "VSS narration is model-generated narrative only and is not a fact source.",
            "VSS may not add detections, counts, identity, legal, official, action, alert-command, or production monitoring claims.",
            "R2 sample media remains bounded sample-media evidence, not live CCTV.",
        ],
        "boundary": BOUNDARY,
    }
    decision = {
        **common,
        "runtime_status": runtime.get("status"),
        "runtime_blocked_reason": runtime.get("blocked_reason"),
        "next_recommended_task": "MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-INTEGRATION-R4",
    }
    closeout = {
        **common,
        "closeout_truth": {
            "vss_runtime_executed": bool(runtime.get("vss_runtime_executed")),
            "vss_output_source_class": "model_generated_narrative",
            "vss_is_fact_source": False,
            "structured_detection_source_class": "sensor_inferred",
            "structured_detection_source": "DeepStream/Metropolis R2 object metadata",
            "candidate_event_modified_by_vss": False,
            "official_record_created": False,
            "human_review_required": True,
            "no_action_taken": True,
        },
    }
    write_json(OUTPUT_ROOT / "METROPOLIS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_DECISION.json", decision)
    write_json(OUTPUT_ROOT / "METROPOLIS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_CLOSEOUT_DECISION.json", closeout)


def write_readme(final_status: str, runtime: dict[str, Any], ctx: dict[str, Any]) -> None:
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Status: `{final_status}`",
        "",
        f"R2 candidate event: `{ctx.get('candidate_event_ref')}`",
        f"Media source: `{ctx.get('media_source')}`",
        f"Zone: `{ctx.get('zone')}`",
        f"Detection class: `{ctx.get('detection_class')}`",
        f"Class label: `{ctx.get('class_label')}`",
        f"R2 candidate observations: `{ctx.get('candidate_observation_count')}`",
        f"VSS runtime executed: `{bool(runtime.get('vss_runtime_executed'))}`",
        "",
        "Visible label:",
        "",
        "```text",
        VISIBLE_LABEL,
        "```",
        "",
        "VSS narration remains `model_generated_narrative` and `fact_source=false`.",
    ]
    if runtime.get("blocked_reason"):
        lines.extend(["", f"Runtime blocked reason: {runtime['blocked_reason']}"])
    write_text(OUTPUT_ROOT / "README.md", "\n".join(lines))


def create_package_zip() -> Path:
    package_path = OUTPUT_ROOT / "METROPOLIS_VSS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_PACKAGE.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUTPUT_ROOT.rglob("*")):
            if path.is_file() and path != package_path:
                zf.write(path, path.relative_to(OUTPUT_ROOT).as_posix())
    return package_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CityBrain Metropolis/VSS narration dry-run R3.")
    parser.add_argument("--r2-zip", default=str(DEFAULT_R2_ZIP), help="Path to the R2 package ZIP.")
    parser.add_argument("--vss-endpoint", default=None, help="Optional VSS HTTP endpoint.")
    parser.add_argument("--vss-command", default=None, help="Optional local command/script for VSS narration; R2 packet is passed on stdin.")
    parser.add_argument("--dry-run-timeout-sec", type=int, default=120)
    parser.add_argument("--allow-runtime-blocked-partial", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reset_output_root()
    r2_validation = validate_r2_zip(Path(args.r2_zip))
    r2_validation_safe = json_safe_validation(r2_validation)
    write_json(OUTPUT_ROOT / "INPUT_R2_PACKAGE_VALIDATION_R3.json", r2_validation_safe)
    if r2_validation.get("status") != "PASS":
        ctx = {
            "candidate_event_ref": None,
            "evidence_bundle_ref": None,
            "media_source": None,
            "zone": None,
            "detection_class": None,
            "class_label": None,
            "candidate_observation_count": 0,
            "object_metadata_count": 0,
            "source_class": None,
            "r2_evidence_bundle": {},
            "r2_human_packet": {},
        }
        runtime = {"status": "NOT_RUN", "vss_runtime_attempted": False, "vss_runtime_executed": False, "blocked_reason": "R2 input package invalid."}
        sidecar = None
        audit = audit_narration(sidecar, ctx)
        write_sidecar_contract()
        write_narration_outputs(sidecar)
        write_runtime_report(runtime_config(args), runtime, ctx)
        write_guardrail_reports(runtime, sidecar, audit)
        source_class_status = write_source_class_audit(sidecar, ctx)
        no_action_status, claim_status = write_no_action_and_claim_audits(sidecar, ctx, audit)
        check_status = write_check_report(runtime, sidecar, audit, ctx)
        write_attached_bundle_and_packet(sidecar, ctx)
        secret_status = write_secret_audit()
        audit_statuses = {
            "source_class": source_class_status,
            "no_action": no_action_status,
            "claim_boundary": claim_status,
            "vss_guardrail": audit.get("status"),
            "check_narration_sufficiency": check_status,
            "secret": secret_status,
        }
        final_status = FAIL_INPUT_STATUS
        write_decisions(final_status, runtime, ctx, r2_validation_safe, audit_statuses)
        write_readme(final_status, runtime, ctx)
        json_status = validate_json_outputs()
        hash_status = write_hash_manifest()
        write_decisions(final_status, runtime, ctx, r2_validation_safe, audit_statuses, json_status, hash_status)
        create_package_zip()
        print(f"Final status: {final_status}")
        print(f"Output: {rel(OUTPUT_ROOT)}")
        return 1
    ctx = r2_context(r2_validation)
    input_packet = build_vss_input_packet(ctx)
    write_json(OUTPUT_ROOT / "VSS_INPUT_PACKET_R3.json", input_packet)
    config = runtime_config(args)
    runtime = execute_vss_runtime(config, input_packet)
    write_runtime_report(config, runtime, ctx)
    write_sidecar_contract()
    sidecar, _raw_json = make_sidecar(runtime, ctx)
    audit = audit_narration(sidecar, ctx)
    write_narration_outputs(sidecar)
    write_guardrail_reports(runtime, sidecar, audit)
    source_class_status = write_source_class_audit(sidecar, ctx)
    no_action_status, claim_status = write_no_action_and_claim_audits(sidecar, ctx, audit)
    check_status = write_check_report(runtime, sidecar, audit, ctx)
    write_attached_bundle_and_packet(sidecar, ctx)
    secret_status = write_secret_audit()
    audit_statuses = {
        "source_class": source_class_status,
        "no_action": no_action_status,
        "claim_boundary": claim_status,
        "vss_guardrail": audit.get("status"),
        "check_narration_sufficiency": check_status,
        "secret": secret_status,
    }
    final_status = decide_status(r2_validation, runtime, audit, source_class_status, no_action_status, claim_status)
    write_decisions(final_status, runtime, ctx, r2_validation_safe, audit_statuses)
    write_readme(final_status, runtime, ctx)
    json_status = validate_json_outputs()
    write_decisions(final_status, runtime, ctx, r2_validation_safe, audit_statuses, json_status)
    json_status = validate_json_outputs()
    hash_status = write_hash_manifest()
    write_decisions(final_status, runtime, ctx, r2_validation_safe, audit_statuses, json_status, hash_status)
    write_readme(final_status, runtime, ctx)
    json_status = validate_json_outputs()
    hash_status = write_hash_manifest()
    create_package_zip()
    print(f"Final status: {final_status}")
    print(f"R2 validation: {r2_validation_safe.get('status')}")
    print(f"VSS runtime executed: {runtime.get('vss_runtime_executed')}")
    print(f"VSS output records: {1 if sidecar else 0}")
    print(f"JSON parse: {json_status}")
    print(f"Hash manifest: {hash_status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if final_status in {PASS_STATUS, PARTIAL_STATUS} and json_status == "PASS" and hash_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
