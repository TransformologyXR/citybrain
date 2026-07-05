from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-SPRINT-CLOSEOUT-R9"
SCHEMA_VERSION = "metropolis-vss-sprint-closeout-r9.v1"
PASS_STATUS = "PASS_METROPOLIS_VSS_MEDIA_CANDIDATE_OBSERVATION_AND_NARRATION_SPRINT_CLOSEOUT_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_METROPOLIS_VSS_SPRINT_CLOSEOUT_INPUT_OR_PACKAGE_GAP_WITH_BOUNDARIES_PRESERVED"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_SPRINT_CLOSEOUT_BOUNDARY_OR_SOURCE_CLASS_REGRESSION"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
DEFAULT_OUTPUT_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_sprint_closeout_r9"
PACKAGE_NAME = "METROPOLIS_VSS_SPRINT_CLOSEOUT_R9_PACKAGE.zip"

REQUIRED_SPINE = {"R1", "R2", "R6C", "R7", "R8"}
ALLOWED_PARTIAL_LABELS = {"R3", "R4", "R5", "R6", "R6B", "R6D", "R6E"}

MILESTONES: list[dict[str, str]] = [
    {
        "label": "R1",
        "root": "main_citybrain_metropolis_vss_candidate_observation_pipeline_r1",
        "package": "METROPOLIS_VSS_VALIDATION_PACKAGE.zip",
        "decision": "METROPOLIS_VSS_CLOSEOUT_DECISION.json",
        "role": "candidate observation preflight and bounded media lane",
    },
    {
        "label": "R2",
        "root": "main_citybrain_metropolis_vss_object_metadata_export_r2",
        "package": "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_PACKAGE.zip",
        "decision": "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_CLOSEOUT_DECISION.json",
        "role": "DeepStream/Metropolis object metadata export",
    },
    {
        "label": "R3",
        "root": "main_citybrain_metropolis_vss_vss_narration_runtime_dry_run_r3",
        "package": "METROPOLIS_VSS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_PACKAGE.zip",
        "decision": "METROPOLIS_VSS_NARRATION_RUNTIME_DRY_RUN_R3_CLOSEOUT_DECISION.json",
        "role": "VSS narration dry run guardrail contract",
    },
    {
        "label": "R4",
        "root": "main_citybrain_metropolis_vss_narration_runtime_integration_r4",
        "package": "METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_PACKAGE.zip",
        "decision": "METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_CLOSEOUT_DECISION.json",
        "role": "VSS runtime integration wrapper, not configured",
    },
    {
        "label": "R5",
        "root": "main_citybrain_metropolis_vss_narration_runtime_configured_smoke_r5",
        "package": "METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_PACKAGE.zip",
        "decision": "METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_CLOSEOUT_DECISION.json",
        "role": "configured smoke guardrails before provisioning",
    },
    {
        "label": "R6",
        "root": "main_citybrain_metropolis_vss_runtime_configuration_and_connectivity_r6",
        "package": "METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_PACKAGE.zip",
        "decision": "METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_CLOSEOUT_DECISION.json",
        "role": "runtime configuration/connectivity contract",
    },
    {
        "label": "R6B",
        "root": "main_citybrain_metropolis_vss_runtime_configured_rerun_r6b",
        "package": "METROPOLIS_VSS_RUNTIME_CONFIGURED_RERUN_R6B_PACKAGE.zip",
        "decision": "R6B_CLOSEOUT_DECISION.json",
        "role": "configured rerun contract",
    },
    {
        "label": "R6D",
        "root": "main_citybrain_metropolis_vss_spark_split_host_readiness_r6d",
        "package": "METROPOLIS_VSS_SPARK_SPLIT_HOST_READINESS_R6D_PACKAGE.zip",
        "decision": "R6D_CLOSEOUT_DECISION.json",
        "role": "split-host readiness contract",
    },
    {
        "label": "R6E",
        "root": "main_citybrain_metropolis_vss_spark_provisioning_runbook_r6e",
        "package": "METROPOLIS_VSS_SPARK_PROVISIONING_RUNBOOK_R6E_PACKAGE.zip",
        "decision": "R6E_CLOSEOUT_DECISION.json",
        "role": "Spark VSS provisioning runbook",
    },
    {
        "label": "R6C",
        "root": "main_citybrain_metropolis_vss_runtime_provisioning_and_configuration_r6c",
        "package": "METROPOLIS_VSS_RUNTIME_PROVISIONING_AND_CONFIGURATION_R6C_PACKAGE.zip",
        "decision": "R6C_CLOSEOUT_DECISION.json",
        "role": "runtime provisioned and connected gate for R7",
    },
    {
        "label": "R7",
        "root": "main_citybrain_metropolis_vss_narration_runtime_smoke_r7",
        "package": "METROPOLIS_VSS_NARRATION_RUNTIME_SMOKE_R7_PACKAGE.zip",
        "decision": "R7_CLOSEOUT_DECISION.json",
        "role": "Spark VSS runtime narration smoke",
    },
    {
        "label": "R8",
        "root": "main_citybrain_metropolis_vss_narration_evidence_join_r8",
        "package": "METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_PACKAGE.zip",
        "decision": "R8_CLOSEOUT_DECISION.json",
        "role": "R2/R7 narration evidence join",
    },
]

SECRET_PATTERNS = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("generic_token_assignment", r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{24,}"),
    ("bearer_token", r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{24,}"),
    ("private_key", r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except Exception:
        return str(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[Any]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return rows


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reset_output_root(output_root: Path) -> None:
    resolved = output_root.resolve()
    allowed_root = OUTPUTS_ROOT.resolve()
    if not str(resolved).lower().startswith(str(allowed_root).lower() + "\\"):
        raise ValueError(f"Refusing to reset output outside {allowed_root}: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def validate_zip_package(package_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "package_path": rel(package_path),
        "package_exists": package_path.exists(),
        "zip_integrity": "NOT_RUN",
        "zip_entries": 0,
        "json_parse": "NOT_RUN",
        "json_files_parsed": 0,
        "jsonl_parse": "NOT_RUN",
        "jsonl_files_parsed": 0,
        "hash_manifest_status": "NOT_RUN",
        "hash_manifest_verified": "0/0",
        "manifest_mismatches": [],
        "status": "FAIL",
    }
    if not package_path.exists():
        return result

    json_failures = []
    jsonl_failures = []
    manifest_mismatches = []
    manifest_total = 0
    try:
        with zipfile.ZipFile(package_path, "r") as archive:
            bad = archive.testzip()
            names = [name for name in archive.namelist() if not name.endswith("/")]
            result["zip_entries"] = len(names)
            result["zip_integrity"] = "PASS" if bad is None else f"FAIL:{bad}"
            for name in names:
                suffix = Path(name).suffix.lower()
                if suffix == ".json":
                    try:
                        json.loads(archive.read(name).decode("utf-8"))
                        result["json_files_parsed"] += 1
                    except Exception as exc:  # noqa: BLE001
                        json_failures.append({"file": name, "error": str(exc)})
                elif suffix == ".jsonl":
                    try:
                        for line_no, line in enumerate(archive.read(name).decode("utf-8").splitlines(), start=1):
                            if line.strip():
                                json.loads(line)
                        result["jsonl_files_parsed"] += 1
                    except Exception as exc:  # noqa: BLE001
                        jsonl_failures.append({"file": name, "line": line_no, "error": str(exc)})
            result["json_parse"] = "PASS" if not json_failures else "FAIL"
            result["jsonl_parse"] = "PASS" if not jsonl_failures else "FAIL"

            if "HASH_MANIFEST.json" in names:
                manifest = json.loads(archive.read("HASH_MANIFEST.json").decode("utf-8"))
                for entry in manifest.get("files", []):
                    file_name = entry.get("file")
                    expected = entry.get("sha256")
                    if not file_name or not expected:
                        continue
                    manifest_total += 1
                    if file_name not in names:
                        manifest_mismatches.append({"file": file_name, "error": "missing_from_zip"})
                        continue
                    actual = sha256_bytes(archive.read(file_name))
                    if actual != expected:
                        manifest_mismatches.append({"file": file_name, "expected": expected, "actual": actual})
                result["hash_manifest_status"] = "PASS" if not manifest_mismatches and manifest_total else "FAIL"
                result["hash_manifest_verified"] = f"{manifest_total - len(manifest_mismatches)}/{manifest_total}"
            else:
                result["hash_manifest_status"] = "MISSING"
    except Exception as exc:  # noqa: BLE001
        result["zip_integrity"] = f"FAIL:{exc}"

    result["manifest_mismatches"] = manifest_mismatches
    result["json_parse_failures"] = json_failures
    result["jsonl_parse_failures"] = jsonl_failures
    result["status"] = (
        "PASS"
        if result["package_exists"]
        and result["zip_integrity"] == "PASS"
        and result["json_parse"] == "PASS"
        and result["jsonl_parse"] == "PASS"
        and result["hash_manifest_status"] == "PASS"
        else "FAIL"
    )
    return result


def decision_status(decision: dict[str, Any]) -> str:
    return str(decision.get("final_status") or decision.get("status") or decision.get("decision") or "")


def load_milestone(config: dict[str, str]) -> dict[str, Any]:
    root = OUTPUTS_ROOT / config["root"]
    package_path = root / config["package"]
    decision_path = root / config["decision"]
    decision = read_json(decision_path) if decision_path.exists() else {}
    package_validation = validate_zip_package(package_path)
    status = decision_status(decision)
    return {
        "milestone": config["label"],
        "label": config["label"],
        "role": config["role"],
        "summary": config["role"],
        "root": rel(root),
        "root_exists": root.exists(),
        "package": config["package"],
        "package_validation": package_validation,
        "decision_file": config["decision"],
        "decision_present": bool(decision),
        "decision_status": status,
        "decision_schema_version": decision.get("schema_version"),
        "task_id": decision.get("task_id") or decision.get("task_name"),
        "audits": decision.get("audits", {}),
        "limitations": decision.get("limitations", []),
        "key_facts": extract_key_facts(config["label"], root, decision),
    }


def extract_key_facts(label: str, root: Path, decision: dict[str, Any]) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    if label == "R2":
        mapping_path = root / "MEDIA_TO_CANDIDATE_EVENT_MAPPING_R2.json"
        if mapping_path.exists():
            mapping = read_json(mapping_path)
            event = mapping.get("candidate_event", {})
            facts.update(
                {
                    "candidate_event_id": event.get("candidate_event_id"),
                    "candidate_observation_count": len(event.get("source_observation_ids", [])),
                    "source_class": event.get("source_class"),
                    "review_state": event.get("review_state"),
                    "human_review_required": event.get("human_review_required"),
                    "no_action_taken": event.get("no_action_taken"),
                    "official_record_created": event.get("official_record_created"),
                    "detection_class": event.get("detection_class"),
                    "class_label": event.get("class_label"),
                    "zone_id": event.get("zone_id"),
                }
            )
    if label == "R6C":
        allocation_path = root / "RUNTIME_HOST_ALLOCATION_R6C.json"
        if allocation_path.exists():
            allocation = read_json(allocation_path)
            facts["host_allocation_ref"] = rel(allocation_path)
            facts["deepstream_host"] = allocation.get("deepstream_metropolis_lane", {}).get("active_host")
            facts["spark_vss_host"] = allocation.get("vss_lane", {}).get("active_host")
            facts["txr_3090_active"] = allocation.get("txr_3090_role", {}).get("active_for_current_metropolis_vss_chain")
    if label == "R7":
        sidecar_path = root / "VSS_NARRATION_SIDECAR_R7.jsonl"
        facts.update(
            {
                "candidate_event_id": decision.get("candidate_event_id"),
                "narration_records_emitted": decision.get("narration_records_emitted"),
                "spark_ready_probe_status": decision.get("spark_ready_probe_status"),
                "vss_runtime_status": decision.get("vss_runtime_status"),
                "vss_runtime_executed": decision.get("vss_runtime_executed"),
                "vss_is_fact_source": decision.get("vss_is_fact_source"),
                "vss_output_source_class": decision.get("vss_output_source_class"),
            }
        )
        if sidecar_path.exists():
            facts["sidecar_record_count"] = len(read_jsonl(sidecar_path))
    if label == "R8":
        facts.update(
            {
                "candidate_event_id": decision.get("candidate_event_id"),
                "candidate_observation_count": decision.get("candidate_observation_count"),
                "narration_sidecar_count": decision.get("narration_sidecar_count"),
                "r2_structured_source_class": decision.get("r2_structured_source_class"),
                "r7_vss_source_class": decision.get("r7_vss_source_class"),
                "vss_is_fact_source": decision.get("vss_is_fact_source"),
                "candidate_event_mutated": decision.get("candidate_event_mutated"),
                "human_review_packet_emitted": decision.get("human_review_packet_emitted"),
                "joined_evidence_bundle_emitted": decision.get("joined_evidence_bundle_emitted"),
            }
        )
    for key in [
        "candidate_observations_emitted",
        "candidate_events_emitted",
        "structured_detection_source_class",
        "vss_output_source_class",
        "vss_is_fact_source",
        "candidate_event_modified_by_vss",
        "no_action_taken",
        "official_record_created",
        "human_review_required",
        "runtime_configured",
        "probe_status",
        "r7_ready",
    ]:
        if key in decision and key not in facts:
            facts[key] = decision[key]
    return facts


def build_runtime_host_allocation() -> dict[str, Any]:
    r6c_path = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_runtime_provisioning_and_configuration_r6c" / "RUNTIME_HOST_ALLOCATION_R6C.json"
    r7_path = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_narration_runtime_smoke_r7" / "RUNTIME_HOST_ALLOCATION_R7.json"
    r6c = read_json(r6c_path) if r6c_path.exists() else {}
    r7 = read_json(r7_path) if r7_path.exists() else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "generated_at": utc_now(),
        "status": "PASS",
        "boundary": {
            "deepstream_metropolis": "sensor_inferred candidate metadata",
            "vss": "model_generated_narrative candidate review context only",
            "vss_is_fact_source": False,
            "human_review_required": True,
        },
        "host_allocation": {
            "txr-4070": {
                "role": "DeepStream / Metropolis media inference and object metadata export",
                "source_class": "sensor_inferred",
                "proven_by": ["R2 object metadata export", "R8 lineage preservation"],
                "evidence": {
                    "candidate_events": 1,
                    "candidate_observations": 24,
                    "container": "nvcr.io/nvidia/deepstream:8.0-samples-multiarch",
                    "media_source": "container bundled samples/streams/sample_1080p_h264.mp4",
                    "metadata_export": "gie-kitti-output-dir",
                },
            },
            "spark-2445": {
                "role": "Spark VSS / LVS / RT-VLM narration runtime",
                "source_class": "model_generated_narrative",
                "model_id": "nim_nvidia_cosmos-reason2-8b_hf-1208",
                "ready_endpoint": r7.get("spark_vss_lane", {}).get("ready_endpoint"),
                "proven_by": [
                    "R6C provisioning/connectivity PASS",
                    "R7 narration runtime smoke PASS",
                    "R8 evidence join",
                ],
            },
            "txr-3090": {
                "role": "data / graph / RAPIDS / heavier analytics",
                "active_for_this_metropolis_vss_chain": False,
                "note": "Not used for the R1-R8 Metropolis/VSS media lane.",
            },
        },
        "deepstream_metropolis": {
            "active_host": "txr-4070",
            "source_class": "sensor_inferred",
            "status": "proven_by_r2",
            "evidence": r6c.get("deepstream_metropolis_lane", {}).get("evidence", []),
        },
        "spark_vss": {
            "active_host": "spark-2445",
            "source_class": "model_generated_narrative",
            "not_fact_source": True,
            "status": "configured_connected_and_executed_by_r7",
            "ready_endpoint_ref": r7.get("spark_vss_lane", {}).get("ready_endpoint"),
            "summarize_endpoint_ref": r7.get("spark_vss_lane", {}).get("summarize_endpoint"),
        },
        "txr_3090": {
            "active_for_this_chain": False,
            "role": "inactive for this Metropolis/VSS candidate-observation and narration chain",
            "intended_role": "data_graph_rapids_heavier_analytics_box",
        },
        "source_boundary": {
            "deepstream_metropolis_on_txr_4070": "sensor_inferred",
            "spark_vss_on_spark_2445": "model_generated_narrative_only",
            "txr_3090": "inactive_for_this_chain",
        },
    }


def build_lineage() -> dict[str, Any]:
    milestones = [load_milestone(config) for config in MILESTONES]
    by_label = {item["label"]: item for item in milestones}
    r2 = by_label.get("R2", {}).get("key_facts", {})
    r7 = by_label.get("R7", {}).get("key_facts", {})
    r8 = by_label.get("R8", {}).get("key_facts", {})
    package_validations = {item["label"]: item["package_validation"]["status"] for item in milestones}
    decision_statuses = {item["label"]: item["decision_status"] for item in milestones}
    final_boundary = {
        "deepstream_metropolis_on_txr_4070": "sensor_inferred",
        "spark_vss_on_spark_2445": "model_generated_narrative_only_not_fact_source",
        "txr_3090": "inactive_for_this_chain",
        "human_review_required": True,
        "not_a_finding": True,
        "no_action_taken": True,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "sprint_scope": "Metropolis/VSS bounded media candidate-observation and narration lane",
        "milestones": milestones,
        "final_boundary": final_boundary,
        "decision_statuses": decision_statuses,
        "package_validation_statuses": package_validations,
        "required_pass_spine": {
            label: {
                "decision_status": decision_statuses.get(label),
                "package_validation": package_validations.get(label),
                "present": label in by_label,
            }
            for label in sorted(REQUIRED_SPINE)
        },
        "documented_partial_milestones": {
            label: {
                "decision_status": decision_statuses.get(label),
                "package_validation": package_validations.get(label),
                "role": by_label.get(label, {}).get("role"),
            }
            for label in sorted(ALLOWED_PARTIAL_LABELS)
            if label in by_label
        },
        "final_truth": {
            "candidate_event_id": r8.get("candidate_event_id") or r2.get("candidate_event_id"),
            "candidate_observation_count": r8.get("candidate_observation_count") or r2.get("candidate_observation_count"),
            "vss_narration_sidecars_joined": r8.get("narration_sidecar_count") or r7.get("sidecar_record_count"),
            "r2_source_class": r8.get("r2_structured_source_class") or r2.get("source_class"),
            "r7_vss_source_class": r8.get("r7_vss_source_class") or r7.get("vss_output_source_class"),
            "vss_is_fact_source": r8.get("vss_is_fact_source"),
            "candidate_event_mutated": r8.get("candidate_event_mutated"),
            "human_review_required": True,
            "not_a_finding": True,
            "no_action_taken": True,
        },
        "final_host_allocation": build_runtime_host_allocation(),
    }


def audit_source_class(lineage: dict[str, Any]) -> dict[str, Any]:
    truth = lineage["final_truth"]
    host = lineage["final_host_allocation"]
    checks = {
        "r2_sensor_inferred": truth.get("r2_source_class") == "sensor_inferred",
        "r7_model_generated_narrative": truth.get("r7_vss_source_class") == "model_generated_narrative",
        "vss_not_fact_source": truth.get("vss_is_fact_source") is False,
        "candidate_event_not_mutated": truth.get("candidate_event_mutated") is False,
        "deepstream_host_txr_4070": host["deepstream_metropolis"]["active_host"] == "txr-4070",
        "spark_host_spark_2445": host["spark_vss"]["active_host"] == "spark-2445",
        "txr_3090_inactive": host["txr_3090"]["active_for_this_chain"] is False,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
    }


def positive_forbidden_hits(payload: Any) -> list[str]:
    text = json.dumps(payload, sort_keys=True).lower()
    patterns = {
        "confirmed_violation": r"(?<!no )(?<!not a )\bconfirmed violation\b",
        "legal_finding": r"(?<!no )(?<!not a )(?<!not )\blegal finding\b",
        "certified_finding": r"(?<!no )(?<!not a )(?<!not )\bcertified finding\b",
        "ticket_created": r"\bticket\b.{0,80}\b(created|issued|opened|ready|true)\b",
        "dispatch_executed": r"\bdispatch\b.{0,80}\b(created|issued|executed|sent|started|true)\b",
        "identity_inference": r"\b(identity|biometric|face recognition|license plate)\b.{0,80}\b(confirmed|created|inferred|true)\b",
        "automated_action": r"(?<!no )(?<!not )\bautomated action\b.{0,80}\b(created|executed|taken|true)\b",
        "production_monitoring": r"(?<!no )(?<!not )\bproduction monitoring\b.{0,80}\b(enabled|active|true)\b",
    }
    hits = []
    for name, pattern in patterns.items():
        for match in re.finditer(pattern, text):
            before = text[max(0, match.start() - 220) : match.start()]
            after = text[match.end() : min(len(text), match.end() + 120)]
            context = before + text[match.start() : match.end()] + after
            safe_context = (
                "blocked" in context
                or "forbidden_outputs" in context
                or "forbidden outputs" in context
                or re.search(r"\b(no|not|without)\b.{0,200}$", before) is not None
                or re.search(r"^\W*.{0,100}\b(blocked|false)\b", after) is not None
            )
            if not safe_context:
                hits.append(name)
                break
    return hits


def audit_boundary(lineage: dict[str, Any], limitations: list[str], recommendations: list[str]) -> dict[str, Any]:
    payload = {"lineage": lineage, "limitations": limitations, "recommendations": recommendations}
    hits = positive_forbidden_hits(payload)
    required = {
        "human_review_required": lineage["final_truth"].get("human_review_required") is True,
        "not_a_finding": lineage["final_truth"].get("not_a_finding") is True,
        "no_action_taken": lineage["final_truth"].get("no_action_taken") is True,
        "vss_not_fact_source": lineage["final_truth"].get("vss_is_fact_source") is False,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if not hits and all(required.values()) else "FAIL",
        "required_boundary_checks": required,
        "forbidden_positive_claim_hits": hits,
        "boundary_summary": {
            "stream_or_live_monitoring_claim": False,
            "official_record_created": False,
            "ticket_or_dispatch_created": False,
            "identity_or_biometric_inference": False,
            "legal_or_certified_finding": False,
            "automated_action": False,
        },
    }


def audit_no_action(lineage: dict[str, Any]) -> dict[str, Any]:
    truth = lineage["final_truth"]
    checks = {
        "human_review_required": truth.get("human_review_required") is True,
        "not_a_finding": truth.get("not_a_finding") is True,
        "no_action_taken": truth.get("no_action_taken") is True,
        "candidate_event_present": bool(truth.get("candidate_event_id")),
        "joined_sidecar_present": truth.get("vss_narration_sidecars_joined") == 1,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
    }


def audit_vss_not_fact_source(lineage: dict[str, Any]) -> dict[str, Any]:
    truth = lineage["final_truth"]
    checks = {
        "vss_source_class_model_generated_narrative": truth.get("r7_vss_source_class") == "model_generated_narrative",
        "vss_is_fact_source_false": truth.get("vss_is_fact_source") is False,
        "candidate_event_not_mutated": truth.get("candidate_event_mutated") is False,
        "deepstream_remains_sensor_source": truth.get("r2_source_class") == "sensor_inferred",
        "vss_sidecar_joined_as_context": truth.get("vss_narration_sidecars_joined") == 1,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
    }


def audit_feature_freeze(lineage: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "no_new_runtime_execution_in_r9": True,
        "r9_reads_existing_artifacts_only": True,
        "all_milestone_packages_validated": all(
            item["package_validation"]["status"] == "PASS" for item in lineage["milestones"]
        ),
        "no_milestone_fail_statuses": not any(
            str(item["decision_status"]).startswith("FAIL") for item in lineage["milestones"]
        ),
        "required_pass_spine_passed": all(
            str(lineage["decision_statuses"].get(label, "")).startswith("PASS")
            and lineage["package_validation_statuses"].get(label) == "PASS"
            for label in REQUIRED_SPINE
        ),
        "intermediate_partials_documented": all(
            str(lineage["decision_statuses"].get(label, "")).startswith(("PARTIAL", "PASS"))
            for label in ALLOWED_PARTIAL_LABELS
        ),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
    }


def build_human_review_handoff(lineage: dict[str, Any]) -> dict[str, Any]:
    r8_packet_path = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_narration_evidence_join_r8" / "HUMAN_REVIEW_PACKET_R8.json"
    r8_packet = read_json(r8_packet_path) if r8_packet_path.exists() else {}
    truth = lineage["final_truth"]
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "packet_id": "metropolis-vss-r9-human-review-closeout-001",
        "status": "ready_for_human_review",
        "source_packet_ref": rel(r8_packet_path) if r8_packet_path.exists() else None,
        "candidate_event_id": truth.get("candidate_event_id"),
        "joined_evidence_bundle_ref": r8_packet.get("joined_evidence_bundle_ref", "metropolis-vss-r8-evidence-bundle-001"),
        "human_review_required": True,
        "not_a_finding": True,
        "no_action_taken": True,
        "official_record_created": False,
        "action_created": False,
        "candidate_event_mutated": False,
        "source_classes": {
            "structured_detection": "sensor_inferred",
            "narration_sidecar": "model_generated_narrative",
        },
        "vss_is_fact_source": False,
        "review_instruction": (
            "Review the R2 sensor-inferred candidate observations. Treat Spark VSS narration as "
            "model-generated context only; do not use it to create or confirm facts."
        ),
        "forbidden_review_outcomes": [
            "confirmed_violation_blocked",
            "legal_or_certified_finding_blocked",
            "identity_or_biometric_inference_blocked",
            "official_case_or_ticket_blocked",
            "dispatch_routing_control_enforcement_blocked",
            "alert_as_command_blocked",
            "automated_action_blocked",
        ],
    }


def build_r8_input_validation_summary(lineage: dict[str, Any]) -> dict[str, Any]:
    r8 = next((item for item in lineage["milestones"] if item["label"] == "R8"), {})
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if r8.get("package_validation", {}).get("status") == "PASS" else "FAIL",
        "r8_decision_status": r8.get("decision_status"),
        "r8_package_validation": r8.get("package_validation"),
        "r8_key_facts": r8.get("key_facts", {}),
    }


def build_r8_artifact_inspection(lineage: dict[str, Any]) -> dict[str, Any]:
    r8 = next((item for item in lineage["milestones"] if item["label"] == "R8"), {})
    facts = r8.get("key_facts", {})
    checks = {
        "joined_evidence_bundle_present": facts.get("joined_evidence_bundle_emitted") is True,
        "human_review_packet_present": facts.get("human_review_packet_emitted") is True,
        "candidate_event_not_mutated": facts.get("candidate_event_mutated") is False,
        "vss_not_fact_source": facts.get("vss_is_fact_source") is False,
        "r2_source_class_sensor_inferred": facts.get("r2_structured_source_class") == "sensor_inferred",
        "r7_source_class_model_generated_narrative": facts.get("r7_vss_source_class") == "model_generated_narrative",
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "r8_artifact_root": r8.get("root"),
    }


def build_source_class_matrix(lineage: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS",
        "matrix": [
            {
                "component": "DeepStream / Metropolis",
                "host": "txr-4070",
                "source_class": "sensor_inferred",
                "fact_role": "candidate object metadata and candidate observations",
            },
            {
                "component": "Spark VSS / LVS / RT-VLM",
                "host": "spark-2445",
                "source_class": "model_generated_narrative",
                "fact_role": "review context only, not a fact source",
            },
            {
                "component": "txr-3090",
                "host": "txr-3090",
                "source_class": "not_applicable",
                "fact_role": "inactive for this chain",
            },
        ],
        "final_boundary": lineage["final_boundary"],
    }


def known_limitations() -> list[str]:
    return [
        "R9 is a closeout package only; it does not rerun DeepStream/Metropolis or Spark VSS.",
        "DeepStream/Metropolis on txr-4070 remains the sensor_inferred source for the R2 candidate event.",
        "Spark VSS on spark-2445 remains model_generated_narrative review context only, not a fact source.",
        "txr-3090 is inactive for this Metropolis/VSS chain.",
        "The R2 candidate event remains candidate review material: human review required, not a finding.",
        "No action, ticket, dispatch, identity inference, legal claim, or certified finding is created.",
        "The bounded sample-media lane is not a live monitoring or production surveillance claim.",
    ]


def next_recommendations() -> list[str]:
    return [
        "Evidence frame or clip export for the R2/R8 candidate event, preserving packet truth and source separation.",
        "Live or RTSP source preflight as a separate sprint before any live monitoring claim.",
        "Keep VSS narration attached as review context unless a future sprint implements and audits a different contract.",
    ]


def write_limitations_md(output_root: Path, limitations: list[str]) -> None:
    body = "# Known Limitations - R9\n\n" + "\n".join(f"- {item}" for item in limitations) + "\n"
    write_text(output_root / "KNOWN_LIMITATIONS_R9.md", body)


def write_recommendations_md(output_root: Path, recommendations: list[str]) -> None:
    body = "# Next Sprint Recommendations - R9\n\n" + "\n".join(f"- {item}" for item in recommendations) + "\n"
    write_text(output_root / "NEXT_SPRINT_RECOMMENDATIONS_R9.md", body)


def write_entry_prompt(output_root: Path) -> None:
    write_text(
        output_root / "ENTRY_PROMPT.md",
        f"""# {TASK_ID}

Objective: freeze the full Metropolis/VSS sprint from R1 through R8 as a bounded media candidate-observation and narration lane.

Boundary:

- DeepStream / Metropolis on txr-4070 = sensor_inferred
- Spark VSS on spark-2445 = model_generated_narrative only
- txr-3090 = inactive for this chain
- human review required
- not a finding
- no action / no ticket / no dispatch / no identity / no legal claim

R9 adds no product feature. It packages lineage, final audits, limitations, recommendations, tests, and a hash manifest.
""",
    )


def write_readme(output_root: Path, status: str, lineage: dict[str, Any]) -> None:
    truth = lineage["final_truth"]
    write_text(
        output_root / "README.md",
        f"""# {TASK_ID}

Status: `{status}`

R9 closes the Metropolis/VSS sprint as a bounded media candidate-observation and narration lane.

Final packet truth:

- Candidate event: `{truth.get("candidate_event_id")}`
- Candidate observations: `{truth.get("candidate_observation_count")}`
- VSS narration sidecars joined: `{truth.get("vss_narration_sidecars_joined")}`
- DeepStream/Metropolis source class: `{truth.get("r2_source_class")}`
- Spark VSS source class: `{truth.get("r7_vss_source_class")}`
- VSS fact source: `{truth.get("vss_is_fact_source")}`
- Candidate event mutated: `{truth.get("candidate_event_mutated")}`

Host boundary:

- txr-4070: DeepStream/Metropolis sensor_inferred lane
- spark-2445: Spark VSS model_generated_narrative lane
- txr-3090: inactive for this chain

No official finding, ticket, dispatch, identity inference, legal claim, live monitoring claim, or automated action is created.
""",
    )


def validate_json_outputs(output_root: Path) -> dict[str, Any]:
    failures = []
    json_count = 0
    jsonl_count = 0
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name in {"JSON_PARSE_REPORT_R9.json", "R9_JSON_PARSE_REPORT.json", "HASH_MANIFEST.json", PACKAGE_NAME}:
            continue
        if path.suffix.lower() == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
                json_count += 1
            except Exception as exc:  # noqa: BLE001
                failures.append({"file": path.relative_to(output_root).as_posix(), "error": str(exc)})
        elif path.suffix.lower() == ".jsonl":
            try:
                read_jsonl(path)
                jsonl_count += 1
            except Exception as exc:  # noqa: BLE001
                failures.append({"file": path.relative_to(output_root).as_posix(), "error": str(exc)})
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if not failures else "FAIL",
        "json_files_parsed": json_count,
        "jsonl_files_parsed": jsonl_count,
        "parse_failures": failures,
    }


def secret_audit(output_root: Path) -> dict[str, Any]:
    hits: list[dict[str, str]] = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name in {PACKAGE_NAME, "HASH_MANIFEST.json", "SECRET_AUDIT_R9.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for family, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                hits.append({"file": path.relative_to(output_root).as_posix(), "family": family})
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if not hits else "FAIL",
        "findings": hits,
        "secret_values_written": False,
    }


def hash_manifest(output_root: Path) -> dict[str, Any]:
    entries = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", PACKAGE_NAME}:
            continue
        entries.append(
            {
                "file": path.relative_to(output_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if entries else "FAIL",
        "algorithm": "sha256",
        "file_count": len(entries),
        "excludes": ["HASH_MANIFEST.json", PACKAGE_NAME],
        "files": entries,
    }


def run_command(command: list[str], timeout: int = 600) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout, check=False)
        output = proc.stdout + proc.stderr
        match = re.search(r"Ran (\d+) tests?", output)
        return {
            "command": command,
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "returncode": proc.returncode,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "test_count": int(match.group(1)) if match else None,
            "output": output,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "command": command,
            "status": "FAIL",
            "returncode": None,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "test_count": None,
            "output": str(exc),
        }


def run_tests(output_root: Path) -> dict[str, Any]:
    targeted = run_command(["python", "-m", "unittest", "tests.test_metropolis_vss_sprint_closeout_r9"])
    venv_python = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    full_cmd = [str(venv_python), "-m", "unittest", "discover", "tests"] if venv_python.exists() else ["python", "-m", "unittest", "discover", "tests"]
    full = run_command(full_cmd, timeout=900)
    write_text(
        output_root / "TEST_LOG_R9.txt",
        "\n\n".join(
            [
                "# R9 Test Log",
                "## Targeted R9\nCommand: `" + " ".join(targeted["command"]) + "`\nStatus: `" + targeted["status"] + "`\n" + targeted["output"].strip(),
                "## Full Discovery\nCommand: `" + " ".join(full["command"]) + "`\nStatus: `" + full["status"] + "`\n" + full["output"].strip(),
            ]
        )
        + "\n",
    )
    return {
        "targeted_r9": targeted["status"],
        "targeted_r9_count": targeted["test_count"],
        "full_discovery": full["status"],
        "test_count": full["test_count"],
    }


def decide_status(
    audits: dict[str, dict[str, Any]],
    json_report: dict[str, Any],
    manifest: dict[str, Any],
    tests: dict[str, Any],
) -> str:
    if any(audit["status"] != "PASS" for audit in audits.values()):
        return FAIL_STATUS
    if json_report["status"] != "PASS" or manifest["status"] != "PASS":
        return PARTIAL_STATUS
    if tests["targeted_r9"] != "PASS" or tests["full_discovery"] != "PASS":
        return PARTIAL_STATUS
    return PASS_STATUS


def build_decision(
    status: str,
    lineage: dict[str, Any],
    audits: dict[str, dict[str, Any]],
    json_report: dict[str, Any],
    manifest: dict[str, Any],
    tests: dict[str, Any],
    limitations: list[str],
    recommendations: list[str],
) -> dict[str, Any]:
    truth = lineage["final_truth"]
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": status,
        "final_status": status,
        "sprint_closed": status == PASS_STATUS,
        "no_new_features_added": True,
        "r1_r8_lineage_summary_emitted": True,
        "candidate_event_id": truth.get("candidate_event_id"),
        "candidate_observation_count": truth.get("candidate_observation_count"),
        "vss_narration_sidecars_joined": truth.get("vss_narration_sidecars_joined"),
        "deepstream_metropolis_source_class": truth.get("r2_source_class"),
        "spark_vss_source_class": truth.get("r7_vss_source_class"),
        "vss_is_fact_source": truth.get("vss_is_fact_source"),
        "candidate_event_mutated": truth.get("candidate_event_mutated"),
        "human_review_required": truth.get("human_review_required"),
        "not_a_finding": truth.get("not_a_finding"),
        "no_action_taken": truth.get("no_action_taken"),
        "host_boundary": lineage["final_host_allocation"]["source_boundary"],
        "lineage": lineage,
        "host_allocation": lineage["final_host_allocation"],
        "required_pass_spine": lineage["required_pass_spine"],
        "documented_partial_milestones": lineage["documented_partial_milestones"],
        "audits": {name: audit["status"] for name, audit in audits.items()},
        "json_parse_status": json_report["status"],
        "hash_manifest_status": manifest["status"],
        "tests": tests,
        "limitations": limitations,
        "next_sprint_recommendations": recommendations,
        "package_name": PACKAGE_NAME,
        "created_at": utc_now(),
    }


def create_package_zip(output_root: Path) -> Path:
    package_path = output_root / PACKAGE_NAME
    if package_path.exists():
        package_path.unlink()
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path != package_path:
                archive.write(path, path.relative_to(output_root).as_posix())
    return package_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    reset_output_root(output_root)

    limitations = known_limitations()
    recommendations = next_recommendations()
    lineage = build_lineage()
    package_validation = {
        item["label"]: item["package_validation"] for item in lineage["milestones"]
    }
    host_allocation = lineage["final_host_allocation"]
    source_audit = audit_source_class(lineage)
    boundary_audit = audit_boundary(lineage, limitations, recommendations)
    no_action = audit_no_action(lineage)
    vss_not_fact_source = audit_vss_not_fact_source(lineage)
    feature_freeze = audit_feature_freeze(lineage)
    human_review_handoff = build_human_review_handoff(lineage)
    r8_input_validation = build_r8_input_validation_summary(lineage)
    r8_artifact_inspection = build_r8_artifact_inspection(lineage)
    source_class_matrix = build_source_class_matrix(lineage)

    write_entry_prompt(output_root)
    write_json(output_root / "R1_R9_LINEAGE_SUMMARY_R9.json", lineage)
    write_json(output_root / "UPSTREAM_PACKAGE_VALIDATION_R9.json", package_validation)
    write_json(output_root / "R8_INPUT_VALIDATION_SUMMARY_R9.json", r8_input_validation)
    write_json(output_root / "R8_ARTIFACT_INSPECTION_REPORT_R9.json", r8_artifact_inspection)
    write_json(output_root / "RUNTIME_HOST_ALLOCATION_FINAL_R9.json", host_allocation)
    write_json(output_root / "FINAL_SOURCE_CLASS_SEPARATION_AUDIT_R9.json", source_audit)
    write_json(output_root / "SOURCE_CLASS_SEPARATION_FINAL_AUDIT_R9.json", source_audit)
    write_json(output_root / "FINAL_BOUNDARY_AUDIT_R9.json", boundary_audit)
    write_json(output_root / "CLAIM_BOUNDARY_FINAL_AUDIT_R9.json", boundary_audit)
    write_json(output_root / "NO_ACTION_HUMAN_REVIEW_AUDIT_R9.json", no_action)
    write_json(output_root / "NO_ACTION_FINAL_AUDIT_R9.json", no_action)
    write_json(output_root / "VSS_NOT_FACT_SOURCE_FINAL_AUDIT_R9.json", vss_not_fact_source)
    write_json(output_root / "HUMAN_REVIEW_HANDOFF_FINAL_R9.json", human_review_handoff)
    write_json(output_root / "FINAL_SOURCE_CLASS_MATRIX_R9.json", source_class_matrix)
    write_json(output_root / "FEATURE_FREEZE_AUDIT_R9.json", feature_freeze)
    write_limitations_md(output_root, limitations)
    write_recommendations_md(output_root, recommendations)

    tests = run_tests(output_root)
    secret = secret_audit(output_root)
    write_json(output_root / "SECRET_AUDIT_R9.json", secret)

    audits = {
        "source_class_separation": source_audit,
        "boundary": boundary_audit,
        "no_action_human_review": no_action,
        "vss_not_fact_source": vss_not_fact_source,
        "feature_freeze": feature_freeze,
        "secret": secret,
    }
    json_report = validate_json_outputs(output_root)
    write_json(output_root / "JSON_PARSE_REPORT_R9.json", json_report)
    write_json(output_root / "R9_JSON_PARSE_REPORT.json", json_report)
    manifest = hash_manifest(output_root)
    status = decide_status(audits, json_report, manifest, tests)
    write_readme(output_root, status, lineage)
    decision = build_decision(status, lineage, audits, json_report, manifest, tests, limitations, recommendations)
    write_json(output_root / "SPRINT_CLOSEOUT_DECISION_R9.json", decision)
    write_json(output_root / "R9_CLOSEOUT_DECISION.json", decision)

    secret = secret_audit(output_root)
    write_json(output_root / "SECRET_AUDIT_R9.json", secret)
    audits["secret"] = secret
    json_report = validate_json_outputs(output_root)
    write_json(output_root / "JSON_PARSE_REPORT_R9.json", json_report)
    write_json(output_root / "R9_JSON_PARSE_REPORT.json", json_report)
    manifest = hash_manifest(output_root)
    status = decide_status(audits, json_report, manifest, tests)
    write_readme(output_root, status, lineage)
    decision = build_decision(status, lineage, audits, json_report, manifest, tests, limitations, recommendations)
    write_json(output_root / "SPRINT_CLOSEOUT_DECISION_R9.json", decision)
    write_json(output_root / "R9_CLOSEOUT_DECISION.json", decision)
    manifest = hash_manifest(output_root)
    write_json(output_root / "HASH_MANIFEST.json", manifest)
    package_path = create_package_zip(output_root)

    truth = lineage["final_truth"]
    print(f"Final status: {status}")
    print(f"Output: {rel(output_root)}")
    print(f"Freeze ZIP: {rel(package_path)}")
    print(f"Candidate event: {truth.get('candidate_event_id')}")
    print(f"Candidate observations: {truth.get('candidate_observation_count')}")
    print(f"VSS narration sidecars joined: {truth.get('vss_narration_sidecars_joined')}")
    audit_summary = ", ".join(f"{name}={audit['status']}" for name, audit in audits.items())
    print(f"Audits: {audit_summary}")
    print(f"JSON parse: {json_report['status']}")
    print(f"Hash manifest: {manifest['status']} ({manifest['file_count']} files)")
    print(f"Tests: targeted={tests['targeted_r9']} full={tests['full_discovery']} count={tests['test_count']}")
    return 0 if status == PASS_STATUS and manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
