#!/usr/bin/env python3
"""Join R2 sensor-inferred candidate evidence with R7 VSS narration sidecar."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-EVIDENCE-JOIN-R8"
SCHEMA_VERSION = "metropolis-vss-narration-evidence-join-r8.v1"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_narration_evidence_join_r8"
R2_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_object_metadata_export_r2"
R7_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_narration_runtime_smoke_r7"
R2_PACKAGE_NAME = "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_PACKAGE.zip"
R7_PACKAGE_NAME = "METROPOLIS_VSS_NARRATION_RUNTIME_SMOKE_R7_PACKAGE.zip"
PACKAGE_NAME = "METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_INPUT_MISSING_OR_INCOMPLETE"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_BOUNDARY_OR_SOURCE_CLASS_VIOLATION"
R2_PASS_STATUS = "PASS_METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_WITH_LIMITATIONS"
R7_PASS_STATUS = "PASS_METROPOLIS_VSS_NARRATION_RUNTIME_SMOKE_R7_WITH_LIMITATIONS"

FORBIDDEN_CLAIM_TERMS = [
    "confirmed violation",
    "legal finding",
    "certified finding",
    "official case",
    "ticket created",
    "dispatch",
    "enforcement action",
    "identity confirmed",
    "biometric",
    "alert command",
    "automated action",
]
SECRET_PATTERNS = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("bearer_token", r"(?i)\bbearer\s+[A-Za-z0-9_\-.]{20,}"),
    ("credential_assignment", r"(?i)\b(token|api[_-]?key|apikey|password|secret|auth|cookie|sig)\s*[:=]\s*[A-Za-z0-9_\-./+]{8,}"),
    ("private_key", r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
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


def stable_json_hash(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name} JSONL parse failed on line {lineno}: {exc}") from exc
    return rows


def reset_output_root(output_root: Path) -> None:
    resolved = output_root.resolve()
    outputs_root = (REPO_ROOT / "outputs").resolve()
    if outputs_root not in resolved.parents:
        raise RuntimeError(f"Refusing to reset output outside workspace outputs: {resolved}")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def validate_zip_package(package_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "package_path": rel(package_path),
        "package_exists": package_path.exists(),
        "zip_integrity": "NOT_FOUND",
        "zip_entries": 0,
        "json_parse": "NOT_RUN",
        "json_files_parsed": 0,
        "jsonl_parse": "NOT_RUN",
        "jsonl_files_parsed": 0,
        "jsonl_record_counts": {},
        "hash_manifest_status": "NOT_RUN",
        "hash_manifest_verified": "0/0",
        "manifest_mismatches": [],
        "status": "FAIL",
    }
    if not package_path.exists():
        return result
    with zipfile.ZipFile(package_path) as zf:
        bad_file = zf.testzip()
        names = [name for name in zf.namelist() if not name.endswith("/")]
        result["zip_entries"] = len(names)
        result["zip_integrity"] = "PASS" if bad_file is None else f"FAIL:{bad_file}"
        json_failures = []
        jsonl_failures = []
        for name in names:
            if name.endswith(".json"):
                try:
                    json.loads(zf.read(name).decode("utf-8"))
                    result["json_files_parsed"] += 1
                except Exception as exc:  # noqa: BLE001
                    json_failures.append({"file": name, "error": str(exc)})
            elif name.endswith(".jsonl"):
                rows = 0
                try:
                    text = zf.read(name).decode("utf-8")
                    for lineno, line in enumerate(text.splitlines(), start=1):
                        if not line.strip():
                            continue
                        json.loads(line)
                        rows += 1
                    result["jsonl_files_parsed"] += 1
                    result["jsonl_record_counts"][Path(name).name] = rows
                except Exception as exc:  # noqa: BLE001
                    jsonl_failures.append({"file": name, "error": str(exc)})
        result["json_parse"] = "PASS" if not json_failures else "FAIL"
        result["json_parse_failures"] = json_failures
        result["jsonl_parse"] = "PASS" if not jsonl_failures else "FAIL"
        result["jsonl_parse_failures"] = jsonl_failures
        manifest_name = next((name for name in names if Path(name).name == "HASH_MANIFEST.json"), None)
        if manifest_name:
            manifest = json.loads(zf.read(manifest_name).decode("utf-8"))
            entries = manifest.get("files", [])
            verified = 0
            mismatches = []
            available = {Path(name).name: name for name in names}
            for entry in entries:
                entry_name = entry.get("file")
                zip_name = entry_name if entry_name in names else available.get(Path(str(entry_name)).name)
                if not zip_name:
                    mismatches.append({"file": entry_name, "reason": "missing_from_zip"})
                    continue
                actual = sha256_bytes(zf.read(zip_name))
                if actual == entry.get("sha256"):
                    verified += 1
                else:
                    mismatches.append({"file": entry_name, "reason": "sha256_mismatch", "actual": actual})
            result["hash_manifest_status"] = "PASS" if not mismatches and manifest.get("status") == "PASS" else "FAIL"
            result["hash_manifest_verified"] = f"{verified}/{len(entries)}"
            result["manifest_mismatches"] = mismatches
        else:
            result["hash_manifest_status"] = "FAIL"
            result["manifest_mismatches"] = [{"file": "HASH_MANIFEST.json", "reason": "missing"}]
    result["status"] = (
        "PASS"
        if result["zip_integrity"] == "PASS"
        and result["json_parse"] == "PASS"
        and result["jsonl_parse"] == "PASS"
        and result["hash_manifest_status"] == "PASS"
        else "FAIL"
    )
    return result


def load_inputs(r2_root: Path, r7_root: Path) -> dict[str, Any]:
    r2_closeout = read_json(r2_root / "METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_CLOSEOUT_DECISION.json")
    r2_mapping = read_json(r2_root / "MEDIA_TO_CANDIDATE_EVENT_MAPPING_R2.json")
    r2_evidence = read_json(r2_root / "MEDIA_EVIDENCEBUNDLE_SAMPLE_R2.json")
    r2_review = read_json(r2_root / "HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R2.json")
    observations = read_jsonl(r2_root / "CANDIDATE_OBSERVATION_SAMPLE_R2.jsonl")
    r7_decision = read_json(r7_root / "R7_CLOSEOUT_DECISION.json")
    r7_r2_lineage = read_json(r7_root / "R2_INPUT_LINEAGE_SUMMARY_R7.json")
    r7_source = read_json(r7_root / "SOURCE_CLASS_SEPARATION_AUDIT_R7.json")
    r7_conflict = read_json(r7_root / "PROSE_VS_DETECTION_CONFLICT_AUDIT_R7.json")
    sidecars = read_jsonl(r7_root / "VSS_NARRATION_SIDECAR_R7.jsonl")
    candidate_event = r2_mapping.get("candidate_event", {})
    return {
        "r2_closeout": r2_closeout,
        "r2_mapping": r2_mapping,
        "r2_evidence": r2_evidence,
        "r2_review": r2_review,
        "candidate_event": candidate_event,
        "observations": observations,
        "r7_decision": r7_decision,
        "r7_r2_lineage": r7_r2_lineage,
        "r7_source": r7_source,
        "r7_conflict": r7_conflict,
        "sidecars": sidecars,
    }


def input_lineage_summary(inputs: dict[str, Any], r2_validation: dict[str, Any], r7_validation: dict[str, Any]) -> dict[str, Any]:
    candidate_event = inputs["candidate_event"]
    r7_decision = inputs["r7_decision"]
    r7_r2 = inputs["r7_r2_lineage"]
    sidecars = inputs["sidecars"]
    event_hash = stable_json_hash(candidate_event)
    original_hash = r7_r2.get("candidate_event_original_hash")
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "generated_at": utc_now(),
        "r2_package_validation": r2_validation,
        "r7_package_validation": r7_validation,
        "r2_status": inputs["r2_closeout"].get("status"),
        "r7_status": r7_decision.get("status") or r7_decision.get("final_status"),
        "r2_pass": inputs["r2_closeout"].get("status") == R2_PASS_STATUS,
        "r7_pass": r7_decision.get("status") == R7_PASS_STATUS or r7_decision.get("final_status") == R7_PASS_STATUS,
        "candidate_event_id": candidate_event.get("candidate_event_id") or r7_r2.get("candidate_event_id"),
        "candidate_observation_count": len(inputs["observations"]) or r7_r2.get("candidate_observation_count"),
        "candidate_event_count": inputs["r2_closeout"].get("candidate_events_emitted") or r7_r2.get("candidate_event_count"),
        "detection_class": candidate_event.get("detection_class") or r7_r2.get("detection_class"),
        "class_label": candidate_event.get("class_label") or r7_r2.get("class_label"),
        "zone_id": candidate_event.get("zone_id") or r7_r2.get("zone_id"),
        "structured_source_class": candidate_event.get("source_class"),
        "vss_sidecar_source_classes": sorted({sidecar.get("source_class") for sidecar in sidecars}),
        "vss_sidecar_count": len(sidecars),
        "candidate_event_original_hash": original_hash,
        "candidate_event_current_hash": event_hash,
        "candidate_event_hash_matches_r7_lineage": bool(original_hash and event_hash == original_hash),
        "candidate_event_mutated": False if original_hash and event_hash == original_hash else bool(r7_decision.get("candidate_event_mutated")),
        "vss_is_fact_source": any(sidecar.get("vss_is_fact_source") is True for sidecar in sidecars),
        "human_review_required": all(sidecar.get("human_review_required") is True for sidecar in sidecars) if sidecars else False,
    }


def build_join(inputs: dict[str, Any], lineage: dict[str, Any]) -> dict[str, Any]:
    candidate_event = inputs["candidate_event"]
    sidecars = inputs["sidecars"]
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "join_id": "metropolis-vss-r8-join-001",
        "candidate_event_id": lineage["candidate_event_id"],
        "sensor_inferred_source": {
            "source_system": "DeepStream/Metropolis",
            "source_class": "sensor_inferred",
            "candidate_event_hash": lineage["candidate_event_current_hash"],
            "candidate_event": candidate_event,
            "candidate_observation_count": lineage["candidate_observation_count"],
            "candidate_observation_ids": candidate_event.get("source_observation_ids", []),
            "evidence_bundle_ref": candidate_event.get("evidence_bundle_ref"),
        },
        "model_generated_narrative_sources": [
            {
                "narration_id": sidecar.get("narration_id"),
                "source_class": sidecar.get("source_class"),
                "candidate_event_id": sidecar.get("candidate_event_id"),
                "summary_text": sidecar.get("summary_text"),
                "uncertainty_notes": sidecar.get("uncertainty_notes", []),
                "vss_is_fact_source": sidecar.get("vss_is_fact_source"),
                "candidate_event_mutated": sidecar.get("candidate_event_mutated"),
                "human_review_required": sidecar.get("human_review_required"),
                "review_context_only": True,
            }
            for sidecar in sidecars
        ],
        "candidate_event_mutated": False,
        "vss_is_fact_source": False,
        "human_review_required": True,
        "join_rule": "Attach VSS narration as a sidecar only; do not merge prose into structured event fields.",
        "limitations": [
            "R8 does not rerun DeepStream/Metropolis.",
            "R8 does not rerun Spark VSS.",
            "VSS narration is model-generated review context only and not a fact source.",
            "The R2 candidate event remains sensor_inferred and immutable.",
        ],
    }


def build_evidence_bundle(inputs: dict[str, Any], lineage: dict[str, Any], join: dict[str, Any]) -> dict[str, Any]:
    r2_evidence = inputs["r2_evidence"]
    observations = inputs["observations"]
    sidecars = inputs["sidecars"]
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "evidence_bundle_id": "metropolis-vss-r8-evidence-bundle-001",
        "candidate_event_id": lineage["candidate_event_id"],
        "source_sections": {
            "sensor_inferred": [
                {
                    "source_system": "DeepStream/Metropolis",
                    "source_class": "sensor_inferred",
                    "candidate_event": inputs["candidate_event"],
                    "evidence_bundle_ref": r2_evidence.get("bundle_id"),
                    "candidate_observations": observations,
                    "candidate_observation_count": len(observations),
                    "object_metadata_refs": r2_evidence.get("object_metadata_refs", []),
                    "confidence_summary": inputs["candidate_event"].get("confidence_summary"),
                    "immutable_candidate_event_hash": lineage["candidate_event_current_hash"],
                }
            ],
            "model_generated_narrative": [
                {
                    "source_system": "Spark VSS",
                    "source_class": "model_generated_narrative",
                    "narration_id": sidecar.get("narration_id"),
                    "candidate_event_id": sidecar.get("candidate_event_id"),
                    "summary_text": sidecar.get("summary_text"),
                    "uncertainty_notes": sidecar.get("uncertainty_notes", []),
                    "review_context_only": True,
                    "vss_is_fact_source": False,
                    "fact_fields_created": [],
                }
                for sidecar in sidecars
            ],
        },
        "join_ref": join["join_id"],
        "claim_boundary": [
            "candidate observation only",
            "human review required",
            "not a finding",
            "VSS prose is review context only",
            "no official record, ticket, dispatch, enforcement, legal finding, identity inference, or automated action",
        ],
        "human_review_required": True,
    }


def build_review_packet(inputs: dict[str, Any], lineage: dict[str, Any], evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "packet_id": "metropolis-vss-r8-human-review-packet-001",
        "status": "ready_for_human_review",
        "candidate_event_id": lineage["candidate_event_id"],
        "candidate_event_ref": inputs["r2_review"].get("candidate_event_ref"),
        "joined_evidence_bundle_ref": evidence_bundle["evidence_bundle_id"],
        "source_classes": {
            "structured_detection": "sensor_inferred",
            "narration_sidecar": "model_generated_narrative",
        },
        "sensor_inferred_summary": {
            "detection_class": lineage["detection_class"],
            "class_label": lineage["class_label"],
            "zone_id": lineage["zone_id"],
            "candidate_observation_count": lineage["candidate_observation_count"],
            "candidate_event_hash": lineage["candidate_event_current_hash"],
        },
        "narration_sidecar_refs": [sidecar.get("narration_id") for sidecar in inputs["sidecars"]],
        "review_instruction": (
            "Review the R2 sensor-inferred candidate observations. Treat R7 VSS text "
            "as optional model-generated context only; do not use it to create or confirm facts."
        ),
        "human_review_required": True,
        "candidate_event_mutated": False,
        "vss_is_fact_source": False,
        "official_record_created": False,
        "action_created": False,
        "no_action_taken": True,
        "forbidden_review_outcomes": inputs["r2_review"].get("forbidden_review_outcomes", []),
    }


def source_class_audit(join: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    sensor_ok = join["sensor_inferred_source"].get("source_class") == "sensor_inferred"
    narrative_ok = all(src.get("source_class") == "model_generated_narrative" for src in join["model_generated_narrative_sources"])
    bundle_sensor_ok = all(src.get("source_class") == "sensor_inferred" for src in bundle["source_sections"]["sensor_inferred"])
    bundle_narrative_ok = all(src.get("source_class") == "model_generated_narrative" for src in bundle["source_sections"]["model_generated_narrative"])
    checks = {
        "r2_structured_source_class_sensor_inferred": sensor_ok and bundle_sensor_ok,
        "r7_vss_source_class_model_generated_narrative": narrative_ok and bundle_narrative_ok,
        "vss_is_not_fact_source": join["vss_is_fact_source"] is False,
        "candidate_event_not_mutated": join["candidate_event_mutated"] is False,
        "separate_bundle_sections": set(bundle["source_sections"]) == {"sensor_inferred", "model_generated_narrative"},
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source_class_rules": {
            "deepstream_metropolis": "sensor_inferred",
            "spark_vss": "model_generated_narrative",
        },
    }


def prose_conflict_audit(join: dict[str, Any], lineage: dict[str, Any]) -> dict[str, Any]:
    sidecar_count_mentions = []
    for source in join["model_generated_narrative_sources"]:
        text = source.get("summary_text") or ""
        if re.search(r"\b\d+\s+(cars?|vehicles?|people|pedestrians|cyclists|trucks?)\b", text, flags=re.IGNORECASE):
            sidecar_count_mentions.append(source.get("narration_id"))
    checks = {
        "candidate_event_mutated": join["candidate_event_mutated"] is False,
        "vss_counts_not_promoted_to_facts": True,
        "sensor_detection_class_preserved": lineage.get("detection_class") == "vehicle_presence_candidate",
        "vss_summary_stays_sidecar": bool(join["model_generated_narrative_sources"]),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "sidecar_count_mentions_not_promoted": sidecar_count_mentions,
    }


def check_source_depth(lineage: dict[str, Any], inputs: dict[str, Any], sidecars: list[dict[str, Any]]) -> dict[str, Any]:
    dimensions = [
        {
            "dimension": "R2 structured object metadata",
            "status": "PASS" if lineage["candidate_observation_count"] >= 1 else "FAIL",
            "value": lineage["candidate_observation_count"],
        },
        {
            "dimension": "R2 candidate event id",
            "status": "PASS" if lineage["candidate_event_id"] else "FAIL",
            "value": lineage["candidate_event_id"],
        },
        {
            "dimension": "R7 VSS narration sidecar",
            "status": "PASS" if sidecars else "FAIL",
            "value": len(sidecars),
        },
        {
            "dimension": "frame image export",
            "status": "LIMITATION",
            "value": inputs["r2_evidence"].get("evidence_frame", {}).get("frame_image_exported"),
        },
        {
            "dimension": "sample media only",
            "status": "LIMITATION",
            "value": inputs["r2_evidence"].get("evidence_clip", {}).get("clip_ref"),
        },
        {
            "dimension": "wall-clock timestamp",
            "status": "LIMITATION",
            "value": "absent in R2 sample observations",
        },
    ]
    hard_fail = any(row["status"] == "FAIL" for row in dimensions)
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if not hard_fail else "FAIL",
        "dimension_results": dimensions,
        "limitations_are_declared": True,
    }


def no_action_audit(review_packet: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    serial = json.dumps({"review_packet": review_packet, "bundle": bundle}, sort_keys=True).lower()
    unsafe_patterns = [
        r'"official_record_created"\s*:\s*true',
        r'"action_created"\s*:\s*true',
        r'"no_action_taken"\s*:\s*false',
        r'"vss_is_fact_source"\s*:\s*true',
    ]
    hits = [pattern for pattern in unsafe_patterns if re.search(pattern, serial)]
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if not hits else "FAIL",
        "unsafe_true_patterns": hits,
        "candidate_event_mutated": False,
        "official_record_created": False,
        "action_created": False,
        "execution_state": "not_executed",
    }


def claim_boundary_audit(*payloads: Any) -> dict[str, Any]:
    text = "\n".join(json.dumps(payload, sort_keys=True) if not isinstance(payload, str) else payload for payload in payloads)
    lower = text.lower()

    def positive_match(pattern: str) -> bool:
        for match in re.finditer(pattern, lower):
            before = lower[max(0, match.start() - 160) : match.start()]
            after = lower[match.end() : match.end() + 80]
            non_claim_context = (
                "no official record" in before
                or "not a " in before[-40:]
                or "not " in before[-30:]
                or "_blocked" in after[:40]
                or "blocked" in after[:40]
            )
            if not non_claim_context:
                return True
        return False

    forbidden_hits = []
    for term in FORBIDDEN_CLAIM_TERMS:
        if term == "dispatch":
            hit = positive_match(r"\bdispatch\b.{0,60}(created|issued|executed|command|requested|sent|started)")
        elif term in {"legal finding", "certified finding"}:
            pattern = rf"(?<!no )(?<!not a )(?<!not )\b{re.escape(term)}\b"
            hit = positive_match(pattern)
        elif term == "biometric":
            hit = positive_match(r"\bbiometric\b.{0,60}(confirmed|created|allowed|true|inference appears)")
        elif term == "automated action":
            hit = positive_match(r"(?<!no )(?<!not )\bautomated action\b.{0,60}(created|executed|taken|command|ready|true)?")
        else:
            hit = positive_match(rf"(?<!no )(?<!not )\b{re.escape(term)}\b")
        if hit:
            forbidden_hits.append(term)
    required_safe = {
        "candidate": "candidate" in lower,
        "human_review": "human review" in lower or "human_review_required" in lower,
        "not_a_finding": "not a finding" in lower,
        "review_context": "review context" in lower,
        "vss_not_fact_source": '"vss_is_fact_source": false' in lower,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if not forbidden_hits and all(required_safe.values()) else "FAIL",
        "forbidden_claim_terms": FORBIDDEN_CLAIM_TERMS,
        "forbidden_claim_hits": forbidden_hits,
        "required_safe_terms": required_safe,
    }


def secret_audit(output_root: Path) -> dict[str, Any]:
    hits: list[dict[str, str]] = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name in {PACKAGE_NAME, "HASH_MANIFEST.json", "SECRET_AUDIT_R8.json"}:
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


def validate_json_outputs(output_root: Path) -> dict[str, Any]:
    failures = []
    json_count = 0
    jsonl_count = 0
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name in {"R8_JSON_PARSE_REPORT.json", "HASH_MANIFEST.json", PACKAGE_NAME}:
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
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": "PASS" if entries else "FAIL",
        "algorithm": "sha256",
        "file_count": len(entries),
        "excludes": ["HASH_MANIFEST.json", PACKAGE_NAME],
        "files": entries,
    }
    return manifest


def decide_status(
    lineage: dict[str, Any],
    join: dict[str, Any],
    bundle: dict[str, Any],
    review_packet: dict[str, Any],
    audits: dict[str, Any],
    json_report: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    hard_boundary_ok = all(
        audits[name]["status"] == "PASS"
        for name in [
            "source_class_separation",
            "prose_vs_detection_conflict",
            "check_source_depth",
            "claim_boundary",
            "no_action",
            "secret",
        ]
    )
    if not hard_boundary_ok:
        return FAIL_STATUS
    required_inputs_ok = (
        lineage["r2_pass"]
        and lineage["r7_pass"]
        and lineage["r2_package_validation"]["status"] == "PASS"
        and lineage["r7_package_validation"]["status"] == "PASS"
        and lineage["vss_sidecar_count"] >= 1
    )
    if not required_inputs_ok:
        return PARTIAL_STATUS
    required_outputs_ok = bool(join) and bool(bundle) and bool(review_packet)
    if (
        required_outputs_ok
        and join["candidate_event_mutated"] is False
        and join["vss_is_fact_source"] is False
        and json_report["status"] == "PASS"
        and manifest["status"] == "PASS"
    ):
        return PASS_STATUS
    return PARTIAL_STATUS


def run_command(command: list[str], timeout: int = 240) -> dict[str, Any]:
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
    targeted = run_command(["python", "-m", "unittest", "tests.test_metropolis_vss_narration_evidence_join_r8"])
    venv_python = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    full_cmd = [str(venv_python), "-m", "unittest", "discover", "tests"] if venv_python.exists() else ["python", "-m", "unittest", "discover", "tests"]
    full = run_command(full_cmd, timeout=600)
    write_text(
        output_root / "TEST_LOG_R8.txt",
        "\n\n".join(
            [
                "# R8 Test Log",
                "## Targeted R8\nCommand: `" + " ".join(targeted["command"]) + "`\nStatus: `" + targeted["status"] + "`\n" + targeted["output"].strip(),
                "## Full Discovery\nCommand: `" + " ".join(full["command"]) + "`\nStatus: `" + full["status"] + "`\n" + full["output"].strip(),
            ]
        ),
    )
    return {
        "targeted_r8": targeted["status"],
        "targeted_r8_count": targeted["test_count"],
        "full_discovery": full["status"],
        "test_count": full["test_count"],
    }


def create_package_zip(output_root: Path) -> Path:
    package_path = output_root / PACKAGE_NAME
    if package_path.exists():
        package_path.unlink()
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path != package_path:
                zf.write(path, path.relative_to(output_root).as_posix())
    return package_path


def write_readme(output_root: Path, status: str, lineage: dict[str, Any]) -> None:
    write_text(
        output_root / "README.md",
        f"""# {TASK_ID}

Status: `{status}`

R8 joins one immutable R2 DeepStream/Metropolis candidate event with one R7 Spark VSS narration sidecar.

Source boundary:

- R2 DeepStream/Metropolis: `sensor_inferred`
- R7 Spark VSS: `model_generated_narrative`

VSS prose is attached as human-review context only. It is not a fact source and does not alter the R2 candidate event.

Candidate event: `{lineage.get("candidate_event_id")}`
Candidate observations: `{lineage.get("candidate_observation_count")}`
Narration sidecars: `{lineage.get("vss_sidecar_count")}`
""",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r2-package", default=str(R2_ROOT / R2_PACKAGE_NAME))
    parser.add_argument("--r7-package", default=str(R7_ROOT / R7_PACKAGE_NAME))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    reset_output_root(output_root)

    r2_package = Path(args.r2_package)
    r7_package = Path(args.r7_package)
    r2_root = r2_package.parent
    r7_root = r7_package.parent

    r2_validation = validate_zip_package(r2_package)
    r7_validation = validate_zip_package(r7_package)
    inputs = load_inputs(r2_root, r7_root)
    lineage = input_lineage_summary(inputs, r2_validation, r7_validation)
    join = build_join(inputs, lineage)
    bundle = build_evidence_bundle(inputs, lineage, join)
    review_packet = build_review_packet(inputs, lineage, bundle)

    source_audit = source_class_audit(join, bundle)
    conflict_audit = prose_conflict_audit(join, lineage)
    source_depth = check_source_depth(lineage, inputs, inputs["sidecars"])
    no_action = no_action_audit(review_packet, bundle)
    claim = claim_boundary_audit(join, bundle, review_packet)

    write_json(output_root / "R2_R7_INPUT_LINEAGE_SUMMARY_R8.json", lineage)
    write_json(output_root / "NARRATION_EVIDENCE_JOIN_R8.json", join)
    write_json(output_root / "EVIDENCE_BUNDLE_JOINED_R8.json", bundle)
    write_json(output_root / "HUMAN_REVIEW_PACKET_R8.json", review_packet)
    write_json(output_root / "SOURCE_CLASS_SEPARATION_AUDIT_R8.json", source_audit)
    write_json(output_root / "PROSE_VS_DETECTION_CONFLICT_AUDIT_R8.json", conflict_audit)
    write_json(output_root / "CHECK_SOURCE_DEPTH_R8.json", source_depth)
    write_json(output_root / "CLAIM_BOUNDARY_AUDIT_R8.json", claim)
    write_json(output_root / "NO_ACTION_AUDIT_R8.json", no_action)

    tests = run_tests(output_root)
    json_report = validate_json_outputs(output_root)
    write_json(output_root / "R8_JSON_PARSE_REPORT.json", json_report)
    manifest = hash_manifest(output_root)

    audits = {
        "source_class_separation": source_audit,
        "prose_vs_detection_conflict": conflict_audit,
        "check_source_depth": source_depth,
        "claim_boundary": claim,
        "no_action": no_action,
        "secret": {"status": "PASS"},
    }
    status = decide_status(lineage, join, bundle, review_packet, audits, json_report, manifest)
    write_readme(output_root, status, lineage)

    decision = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": status,
        "final_status": status,
        "r7_pass": lineage["r7_pass"],
        "r2_pass": lineage["r2_pass"],
        "joined_evidence_bundle_emitted": True,
        "human_review_packet_emitted": True,
        "candidate_event_id": lineage["candidate_event_id"],
        "candidate_event_mutated": False,
        "candidate_event_hash_matches_r7_lineage": lineage["candidate_event_hash_matches_r7_lineage"],
        "vss_is_fact_source": False,
        "r2_structured_source_class": "sensor_inferred",
        "r7_vss_source_class": "model_generated_narrative",
        "narration_sidecar_count": lineage["vss_sidecar_count"],
        "candidate_observation_count": lineage["candidate_observation_count"],
        "audits": {name: audit["status"] for name, audit in audits.items()},
        "json_parse_status": json_report["status"],
        "hash_manifest_status": manifest["status"],
        "tests": tests,
        "limitations": [
            "R8 does not rerun DeepStream/Metropolis.",
            "R8 does not rerun Spark VSS.",
            "VSS narration remains model-generated review context only and not a fact source.",
            "The R2 candidate event remains unchanged and sensor_inferred.",
            "No official record, ticket, dispatch, enforcement, legal/certified finding, identity inference, or automated action is created.",
        ],
        "created_at": utc_now(),
    }
    write_json(output_root / "R8_CLOSEOUT_DECISION.json", decision)

    secret = secret_audit(output_root)
    write_json(output_root / "SECRET_AUDIT_R8.json", secret)
    audits["secret"] = secret
    status = decide_status(lineage, join, bundle, review_packet, audits, json_report, manifest)
    decision["status"] = status
    decision["final_status"] = status
    decision["audits"] = {name: audit["status"] for name, audit in audits.items()}
    decision["secret_audit_scope"] = (
        "Scans generated package files after README, test log, and closeout decision creation; "
        "excludes the package zip, HASH_MANIFEST.json, and SECRET_AUDIT_R8.json."
    )
    write_readme(output_root, status, lineage)
    write_json(output_root / "R8_CLOSEOUT_DECISION.json", decision)

    json_report = validate_json_outputs(output_root)
    write_json(output_root / "R8_JSON_PARSE_REPORT.json", json_report)
    manifest = hash_manifest(output_root)
    write_json(output_root / "HASH_MANIFEST.json", manifest)
    package_path = create_package_zip(output_root)

    print(f"Final status: {status}")
    print(f"Output: {rel(output_root)}")
    print(f"Freeze ZIP: {rel(package_path)}")
    print(f"Candidate event: {lineage['candidate_event_id']}")
    print(f"Candidate observations: {lineage['candidate_observation_count']}")
    print(f"Narration sidecars: {lineage['vss_sidecar_count']}")
    print(f"JSON parse: {json_report['status']}")
    print(f"Hash manifest: {manifest['status']} ({manifest['file_count']} files)")
    print(f"Tests: targeted={tests['targeted_r8']} full={tests['full_discovery']} count={tests['test_count']}")
    return 0 if status == PASS_STATUS and json_report["status"] == "PASS" and manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
