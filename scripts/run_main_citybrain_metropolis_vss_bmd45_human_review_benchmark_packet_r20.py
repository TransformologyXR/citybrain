#!/usr/bin/env python3
"""R20 human-review benchmark packet for the BMD-45 replay harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-HUMAN-REVIEW-BENCHMARK-PACKET-R20"
SCHEMA_VERSION = "metropolis-vss-bmd45-human-review-benchmark-packet-r20.v1"
DEFAULT_OUTPUT_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_bmd45_human_review_benchmark_packet_r20"
PACKAGE_NAME = "METROPOLIS_VSS_BMD45_HUMAN_REVIEW_BENCHMARK_PACKET_R20_PACKAGE.zip"

R19_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_bmd45_replay_benchmark_regression_harness_r19"
R19_PACKAGE = R19_ROOT / "METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_REGRESSION_HARNESS_R19_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_BMD45_HUMAN_REVIEW_BENCHMARK_PACKET_R20_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_METROPOLIS_VSS_BMD45_HUMAN_REVIEW_PACKET_CONTRACT_READY_APP_INTEGRATION_PENDING"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_BMD45_HUMAN_REVIEW_PACKET_BOUNDARY_OR_SOURCE_CLASS_RISK"

FORBIDDEN_CLAIM_TERMS = [
    "confirmed violation",
    "certified finding",
    "legal finding",
    "official case",
    "ticket created",
    "dispatch",
    "identity confirmed",
    "biometric",
    "automated action",
    "production live cctv",
]
SECRET_PATTERNS = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("bearer_token", r"(?i)\bbearer\s+[A-Za-z0-9_\-.]{20,}"),
    ("credential_assignment", r"(?i)\b(token|api[_-]?key|apikey|password|secret|auth|cookie|sig)\s*[:=]\s*[A-Za-z0-9_\-./+]{8,}"),
    ("private_key", r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_output_root(output_root: Path) -> None:
    resolved = output_root.resolve()
    outputs_root = OUTPUTS_ROOT.resolve()
    if outputs_root not in resolved.parents:
        raise ValueError(f"Refusing to reset output outside outputs root: {resolved}")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def validate_r19_package() -> tuple[dict[str, Any], dict[str, Any]]:
    report: dict[str, Any] = {
        "package_exists": R19_PACKAGE.exists(),
        "package_path": rel(R19_PACKAGE),
        "schema_version": SCHEMA_VERSION,
        "status": "FAIL",
    }
    package_data: dict[str, Any] = {}
    required = [
        "R19_CLOSEOUT_DECISION.json",
        "BMD45_REPLAY_BASELINE_SCORECARD_R19.json",
        "BMD45_REPLAY_BENCHMARK_CONFIG_R19.json",
        "REPLAY_RERUN_EXECUTION_REPORT_R19.json",
        "REGRESSION_DRIFT_REVIEW_PACKET_R19.json",
        "THRESHOLD_CALIBRATION_DELTA_R19.json",
        "IOU_COMPARISON_REPORT_R19.json",
        "FRAME_COMPARISON_RECORDS_R19.jsonl",
        "SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R19.jsonl",
        "SOURCE_CLASS_SEPARATION_AUDIT_R19.json",
        "CLAIM_BOUNDARY_AUDIT_R19.json",
        "NO_ACTION_AUDIT_R19.json",
        "SECRET_AUDIT_R19.json",
        "VSS_NOT_FACT_SOURCE_AUDIT_R19.json",
        "HASH_MANIFEST.json",
    ]
    if not R19_PACKAGE.exists():
        report["failure_reason"] = "R19 package not found"
        return report, package_data
    try:
        with zipfile.ZipFile(R19_PACKAGE) as archive:
            bad = archive.testzip()
            names = [name for name in archive.namelist() if not name.endswith("/")]
            missing_required = [name for name in required if name not in names]
            json_count = 0
            jsonl_count = 0
            jsonl_rows: dict[str, int] = {}
            for name in names:
                if name.endswith(".json"):
                    json.loads(archive.read(name).decode("utf-8"))
                    json_count += 1
                elif name.endswith(".jsonl"):
                    jsonl_count += 1
                    count = 0
                    for line in archive.read(name).decode("utf-8").splitlines():
                        if line.strip():
                            json.loads(line)
                            count += 1
                    jsonl_rows[name] = count
            manifest = json.loads(archive.read("HASH_MANIFEST.json").decode("utf-8"))
            manifest_missing = []
            manifest_mismatches = []
            for entry in manifest.get("files", []):
                try:
                    actual = sha256_bytes(archive.read(entry["file"]))
                except KeyError:
                    manifest_missing.append(entry["file"])
                    continue
                if actual != entry.get("sha256"):
                    manifest_mismatches.append(entry["file"])
            for name in required:
                if name in names and name.endswith(".json"):
                    package_data[name] = json.loads(archive.read(name).decode("utf-8"))
                elif name in names and name.endswith(".jsonl"):
                    package_data[name] = [
                        json.loads(line)
                        for line in archive.read(name).decode("utf-8").splitlines()
                        if line.strip()
                    ]
            package_data["HASH_MANIFEST.json"] = manifest
    except Exception as exc:  # noqa: BLE001
        report["failure_reason"] = str(exc)
        return report, package_data

    decision = package_data.get("R19_CLOSEOUT_DECISION.json", {})
    expected = "PASS_METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_REGRESSION_HARNESS_R19_WITH_LIMITATIONS"
    report.update(
        {
            "decision_status": decision.get("status"),
            "expected_status": expected,
            "external_media_refs": len(package_data.get("HASH_MANIFEST.json", {}).get("external_media_refs", [])),
            "hash_manifest_status": "PASS" if not manifest_missing and not manifest_mismatches else "FAIL",
            "json_files_parsed": json_count,
            "jsonl_files_parsed": jsonl_count,
            "jsonl_rows": jsonl_rows,
            "manifest_mismatches": manifest_mismatches,
            "manifest_missing": manifest_missing,
            "required_missing": missing_required,
            "status": "PASS" if bad is None and not missing_required and not manifest_missing and not manifest_mismatches and decision.get("status") == expected else "FAIL",
            "zip_entries": len(names),
            "zip_integrity": "PASS" if bad is None else f"FAIL:{bad}",
        }
    )
    return report, package_data


def frame_cards(
    frame_records: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    external_refs: list[dict[str, Any]],
    calibration: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates_by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        candidates_by_frame[int(row.get("frame_sequence_index", -1))].append(row)
    ref_by_sequence = {int(ref.get("sequence_index", -1)): ref for ref in external_refs}
    cards = []
    for record in sorted(frame_records, key=lambda item: int(item.get("frame_sequence_index", -1))):
        frame = int(record.get("frame_sequence_index", -1))
        frame_candidates = candidates_by_frame.get(frame, [])
        class_counts = Counter(str(row.get("class_label")) for row in frame_candidates)
        confidence_values = [float(row.get("confidence", 0.0)) for row in frame_candidates if row.get("confidence") is not None]
        confidence_summary = {
            "candidate_count": len(confidence_values),
            "max": round(max(confidence_values), 6) if confidence_values else None,
            "min": round(min(confidence_values), 6) if confidence_values else None,
        }
        review_label = "Review unmatched candidates and missed annotations" if record.get("unmatched_annotation_count") or record.get("unmatched_sensor_detection_count") else "Benchmark frame within matched review band"
        cards.append(
            {
                "confidence_summary": confidence_summary,
                "dataset_annotation_summary": {
                    "annotation_count": record.get("annotation_count", 0),
                    "source_class": "dataset_annotation",
                    "unmatched_annotation_count": record.get("unmatched_annotation_count", 0),
                },
                "external_media_ref": ref_by_sequence.get(frame, {}),
                "frame_replay_id": ref_by_sequence.get(frame, {}).get("frame_replay_id", f"bmd45-r20-frame-{frame}"),
                "frame_sequence_index": frame,
                "iou_summary": {
                    "match_count": len(record.get("matches", [])),
                    "max_iou": round(max([float(match.get("iou", 0.0)) for match in record.get("matches", [])] or [0.0]), 6),
                },
                "review_label": review_label,
                "schema_version": SCHEMA_VERSION,
                "sensor_inferred_summary": {
                    "candidate_count": record.get("sensor_detection_count", len(frame_candidates)),
                    "class_counts": dict(sorted(class_counts.items())),
                    "source_class": "sensor_inferred",
                    "unmatched_sensor_detection_count": record.get("unmatched_sensor_detection_count", 0),
                },
                "threshold_band_labels": calibration.get("recommended_confidence_threshold_bands", {}),
            }
        )
    return cards


def review_lists(frame_records: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    matched_ids = {
        str(match.get("candidate_observation_id"))
        for record in frame_records
        for match in record.get("matches", [])
    }
    false_positive = [
        {
            "candidate_observation_id": row.get("candidate_observation_id"),
            "class_family": row.get("class_family"),
            "class_label": row.get("class_label"),
            "confidence": row.get("confidence"),
            "frame_sequence_index": row.get("frame_sequence_index"),
            "review_note": "Unmatched sensor_inferred candidate in benchmark packet; candidate review only.",
            "source_class": "sensor_inferred",
        }
        for row in candidates
        if str(row.get("candidate_observation_id")) not in matched_ids
    ]
    missed = []
    for record in frame_records:
        matched_annotation_ids = {match.get("annotation_id") for match in record.get("matches", [])}
        unmatched_count = int(record.get("unmatched_annotation_count", 0))
        for index in range(unmatched_count):
            missed.append(
                {
                    "frame_sequence_index": record.get("frame_sequence_index"),
                    "review_note": "Dataset annotation unmatched by sensor_inferred candidate in benchmark packet; candidate review only.",
                    "source_class": "dataset_annotation",
                    "unmatched_annotation_index": index,
                    "known_matched_annotation_ids": sorted(matched_annotation_ids),
                }
            )
    return false_positive, missed


def scan_for_forbidden_claims(output_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    safe_markers = ["blocked", "not ", "no ", "no_", "false", "pending", "limitation", "non-goal", "without claiming", "candidate review", "review packet"]
    for path in output_root.rglob("*"):
        if not path.is_file() or path.name in {PACKAGE_NAME, "HASH_MANIFEST.json"}:
            continue
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".log"}:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            lowered = line.lower()
            if any(marker in lowered for marker in safe_markers):
                continue
            for term in FORBIDDEN_CLAIM_TERMS:
                if term in lowered:
                    findings.append({"file": rel(path) or str(path), "line": str(line_no), "term": term})
    return findings


def scan_for_secrets(output_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in output_root.rglob("*"):
        if not path.is_file() or path.name == PACKAGE_NAME:
            continue
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".log", ".env"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                findings.append({"file": rel(path) or str(path), "pattern": name})
    return findings


def write_audits(output_root: Path, packet: dict[str, Any], external_refs: list[dict[str, Any]]) -> dict[str, str]:
    frame_cards_payload = packet.get("frame_cards", [])
    source_ok = packet.get("source_classes") == {
        "dataset_annotations": "dataset_annotation",
        "deepstream_metropolis": "sensor_inferred",
        "vss": "model_generated_narrative_not_fact_source",
    }
    claim_findings = scan_for_forbidden_claims(output_root)
    secret_findings = scan_for_secrets(output_root)
    media_entries = [
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".mp4", ".mov", ".mkv", ".avi"}
    ]
    audits = {
        "SOURCE_CLASS_SEPARATION_AUDIT_R20.json": {
            "frame_cards": len(frame_cards_payload),
            "schema_version": SCHEMA_VERSION,
            "source_classes": packet.get("source_classes"),
            "status": "PASS" if source_ok else "FAIL",
        },
        "CLAIM_BOUNDARY_AUDIT_R20.json": {"findings": claim_findings, "schema_version": SCHEMA_VERSION, "status": "PASS" if not claim_findings else "FAIL"},
        "NO_ACTION_AUDIT_R20.json": {
            "action_created": False,
            "dispatch_created": False,
            "official_record_created": False,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "ticket_created": False,
        },
        "VSS_NOT_FACT_SOURCE_AUDIT_R20.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "vss_is_fact_source": False,
            "vss_records_created": 0,
        },
        "SECRET_AUDIT_R20.json": {"findings": secret_findings, "schema_version": SCHEMA_VERSION, "status": "PASS" if not secret_findings else "FAIL"},
        "PACKAGED_MEDIA_AUDIT_R20.json": {
            "external_media_refs": len(external_refs),
            "packaged_media_files": media_entries,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if not media_entries else "FAIL",
        },
    }
    for filename, payload in audits.items():
        write_json(output_root / filename, payload)
    return {filename.replace(".json", ""): payload["status"] for filename, payload in audits.items()}


def build_package(output_root: Path, external_refs: list[dict[str, Any]]) -> dict[str, Any]:
    package_path = output_root / PACKAGE_NAME
    files = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in {"HASH_MANIFEST.json", PACKAGE_NAME}:
            continue
        files.append({"bytes": path.stat().st_size, "file": path.relative_to(output_root).as_posix(), "sha256": sha256_file(path)})
    manifest = {
        "algorithm": "sha256",
        "created_at": utc_now(),
        "excludes": ["HASH_MANIFEST.json", PACKAGE_NAME],
        "external_media_refs": external_refs,
        "file_count": len(files),
        "files": files,
        "packaged_media_count": 0,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
    }
    write_json(output_root / "HASH_MANIFEST.json", manifest)
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_root.rglob("*")):
            if path.is_file() and path.name != PACKAGE_NAME:
                archive.write(path, path.relative_to(output_root).as_posix())
    return validate_package(package_path)


def validate_package(package_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(package_path) as archive:
        bad = archive.testzip()
        names = [name for name in archive.namelist() if not name.endswith("/")]
        json_count = 0
        jsonl_count = 0
        for name in names:
            if name.endswith(".json"):
                json.loads(archive.read(name).decode("utf-8"))
                json_count += 1
            elif name.endswith(".jsonl"):
                for line in archive.read(name).decode("utf-8").splitlines():
                    if line.strip():
                        json.loads(line)
                jsonl_count += 1
        manifest = json.loads(archive.read("HASH_MANIFEST.json").decode("utf-8"))
        missing = []
        mismatches = []
        for entry in manifest.get("files", []):
            try:
                data = archive.read(entry["file"])
            except KeyError:
                missing.append(entry["file"])
                continue
            if sha256_bytes(data) != entry.get("sha256"):
                mismatches.append(entry["file"])
    return {
        "hash_manifest_status": "PASS" if not missing and not mismatches else "FAIL",
        "hash_manifest_verified": f"{len(manifest.get('files', [])) - len(missing) - len(mismatches)}/{len(manifest.get('files', []))}",
        "json_files_parsed": json_count,
        "jsonl_files_parsed": jsonl_count,
        "manifest_mismatches": mismatches,
        "manifest_missing": missing,
        "status": "PASS" if bad is None and not missing and not mismatches else "FAIL",
        "zip_entries": len(names),
        "zip_integrity": "PASS" if bad is None else f"FAIL:{bad}",
    }


def build_r20(output_root: Path) -> dict[str, Any]:
    reset_output_root(output_root)
    r19_validation, r19_data = validate_r19_package()
    manifest = r19_data.get("HASH_MANIFEST.json", {})
    external_refs = manifest.get("external_media_refs", [])
    scorecard = r19_data.get("BMD45_REPLAY_BASELINE_SCORECARD_R19.json", {})
    comparison = r19_data.get("IOU_COMPARISON_REPORT_R19.json", {})
    calibration_delta = r19_data.get("THRESHOLD_CALIBRATION_DELTA_R19.json", {})
    calibration = calibration_delta.get("current_calibration", {})
    frame_records = r19_data.get("FRAME_COMPARISON_RECORDS_R19.jsonl", [])
    candidates = r19_data.get("SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R19.jsonl", [])
    drift_packet = r19_data.get("REGRESSION_DRIFT_REVIEW_PACKET_R19.json", {})
    cards = frame_cards(frame_records, candidates, external_refs, calibration)
    false_positive, missed_annotations = review_lists(frame_records, candidates)

    source_classes = {
        "dataset_annotations": "dataset_annotation",
        "deepstream_metropolis": "sensor_inferred",
        "vss": "model_generated_narrative_not_fact_source",
    }
    score_summary = {
        "benchmark_status": scorecard.get("status"),
        "confidence_band_summary": calibration.get("confidence_distribution", {}).get("bands", {}),
        "dataset_annotation_count": comparison.get("annotation_count"),
        "drift_review_items": len(drift_packet.get("drift_items", [])),
        "false_positive_review_count": len(false_positive),
        "iou_match_counts": comparison.get("metrics", {}).get("matches_at_threshold", {}),
        "missed_annotation_review_count": len(missed_annotations),
        "schema_version": SCHEMA_VERSION,
        "sensor_candidate_count": comparison.get("sensor_detection_count"),
        "source_classes": source_classes,
        "status": "PASS",
    }
    cockpit_tile = {
        "actions_allowed": [
            "inspect candidate-review packet",
            "compare dataset_annotation and sensor_inferred summaries",
            "route to human review queue",
        ],
        "actions_forbidden": [
            "no dispatch or action",
            "no ticket or case",
            "no identity or legal conclusion",
            "not production live CCTV",
        ],
        "source_labels": [
            "BMD-45 labels: dataset_annotation",
            "DeepStream/Metropolis: sensor_inferred",
            "VSS: model_generated_narrative_not_fact_source",
        ],
        "status_label": "Benchmark review packet ready",
        "tile_id": "citybrain-bmd45-r20-human-review-benchmark",
        "title": "BMD-45 Replay Benchmark Review",
    }
    packet = {
        "benchmark_scorecard": score_summary,
        "boundaries": [
            "Human review required",
            "Dataset annotations are not official truth",
            "Sensor candidates are not findings",
            "No live CCTV claim",
            "No ticket, dispatch, identity, legal conclusion, or action",
        ],
        "external_media_refs": external_refs,
        "frame_cards": cards,
        "human_review_required": True,
        "packet_id": stable_id("human-review-benchmark-packet-r20", len(cards), len(candidates), len(false_positive), len(missed_annotations)),
        "review_lists": {
            "false_positive_candidates_ref": "FALSE_POSITIVE_REVIEW_LIST_R20.json",
            "missed_annotations_ref": "MISSED_ANNOTATION_REVIEW_LIST_R20.json",
        },
        "schema_version": SCHEMA_VERSION,
        "source_classes": source_classes,
        "source_task": "MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-REPLAY-BENCHMARK-REGRESSION-HARNESS-R19",
    }

    write_json(output_root / "R19_INPUT_LINEAGE_SUMMARY.json", r19_validation)
    write_json(output_root / "BENCHMARK_SCORECARD_SUMMARY_R20.json", score_summary)
    write_json(output_root / "FRAME_REVIEW_CARD_FIXTURES_R20.json", {"cards": cards, "schema_version": SCHEMA_VERSION, "status": "PASS"})
    write_json(output_root / "FALSE_POSITIVE_REVIEW_LIST_R20.json", {"items": false_positive, "schema_version": SCHEMA_VERSION, "status": "PASS"})
    write_json(output_root / "MISSED_ANNOTATION_REVIEW_LIST_R20.json", {"items": missed_annotations, "schema_version": SCHEMA_VERSION, "status": "PASS"})
    write_json(output_root / "COCKPIT_REVIEW_TILE_FIXTURE_R20.json", cockpit_tile)
    write_json(output_root / "HUMAN_REVIEW_BENCHMARK_PACKET_R20.json", packet)
    write_text(
        output_root / "KNOWN_LIMITATIONS_R20.md",
        "\n".join(
            [
                "# Known Limitations R20",
                "",
                "- R20 is a review packet and cockpit fixture layer only; it does not rerun DeepStream or VSS.",
                "- BMD-45 media remains external by reference and is not packaged.",
                "- Dataset annotations are comparison fixtures, not official truth.",
                "- Sensor candidates are review evidence only, not findings or actions.",
            ]
        ),
    )
    write_text(
        output_root / "NEXT_SPRINT_RECOMMENDATIONS_R20.md",
        "\n".join(
            [
                "# Next Sprint Recommendations R20",
                "",
                "1. Add visual overlay thumbnails as external or generated review assets without packaging source media.",
                "2. Wire the JSON cockpit tile fixture into the app review surface.",
                "3. Add reviewer disposition capture as a separate human-in-the-loop lane.",
            ]
        ),
    )
    write_text(
        output_root / "README.md",
        f"# {TASK_ID}\n\nR20 turns the accepted R19 BMD-45 replay benchmark into an operator-facing human-review packet and cockpit fixture. It does not rerun DeepStream or VSS.\n",
    )

    audit_statuses = write_audits(output_root, packet, external_refs)
    audits_pass = all(status == "PASS" for status in audit_statuses.values())
    pass_ready = (
        r19_validation.get("status") == "PASS"
        and bool(cards)
        and bool(packet)
        and bool(cockpit_tile)
        and audits_pass
    )
    final_status = PASS_STATUS if pass_ready else PARTIAL_STATUS
    if not audits_pass or r19_validation.get("status") != "PASS":
        final_status = FAIL_STATUS if not audits_pass else PARTIAL_STATUS
    decision = {
        "audits": audit_statuses,
        "cockpit_fixture_emitted": bool(cockpit_tile),
        "external_media_refs": len(external_refs),
        "final_status": final_status,
        "frame_review_cards": len(cards),
        "human_review_packet_emitted": bool(packet),
        "live_cctv_claimed": False,
        "official_record_created": False,
        "packaged_media_files": 0,
        "r19_input_validation": r19_validation.get("status"),
        "schema_version": SCHEMA_VERSION,
        "source_classes": source_classes,
        "status": final_status,
        "task_id": TASK_ID,
    }
    write_json(output_root / "R20_CLOSEOUT_DECISION.json", decision)
    write_json(
        output_root / "R20_JSON_PARSE_REPORT.json",
        {
            "hash_manifest_status": "PENDING",
            "json_files_parsed": 0,
            "jsonl_files_parsed": 0,
            "manifest_mismatches": [],
            "schema_version": SCHEMA_VERSION,
            "status": "PENDING",
            "zip_entries": 0,
            "zip_integrity": "PENDING",
        },
    )
    write_text(
        output_root / "TEST_LOG_R20.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r19_input_validation={r19_validation.get('status')}",
                f"frame_review_cards={len(cards)}",
                f"false_positive_review_items={len(false_positive)}",
                f"missed_annotation_review_items={len(missed_annotations)}",
                "zip_entries=PENDING",
                "hash_manifest=PENDING",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    write_json(
        output_root / "R20_JSON_PARSE_REPORT.json",
        {
            "hash_manifest_status": package_report["hash_manifest_status"],
            "json_files_parsed": package_report["json_files_parsed"],
            "jsonl_files_parsed": package_report["jsonl_files_parsed"],
            "manifest_mismatches": package_report["manifest_mismatches"],
            "manifest_missing": package_report["manifest_missing"],
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if package_report["status"] == "PASS" else "FAIL",
            "zip_entries": package_report["zip_entries"],
            "zip_integrity": package_report["zip_integrity"],
        },
    )
    write_text(
        output_root / "TEST_LOG_R20.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r19_input_validation={r19_validation.get('status')}",
                f"frame_review_cards={len(cards)}",
                f"false_positive_review_items={len(false_positive)}",
                f"missed_annotation_review_items={len(missed_annotations)}",
                f"zip_entries={package_report['zip_entries']}",
                f"hash_manifest={package_report['hash_manifest_verified']}",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    return {"decision": decision, "package_report": package_report}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run R20 BMD-45 human-review benchmark packet.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_r20(Path(args.output_root))
    decision = result["decision"]
    report = result["package_report"]
    print(f"Status: {decision['status']}")
    print(f"Output: {rel(Path(args.output_root))}")
    print(f"Freeze ZIP: {rel(Path(args.output_root) / PACKAGE_NAME)}")
    print(f"R19 input validation: {decision['r19_input_validation']}")
    print(f"Frame review cards: {decision['frame_review_cards']}")
    print(f"External media refs: {decision['external_media_refs']}")
    print(f"ZIP entries: {report['zip_entries']}")
    print(f"JSON parse: PASS, {report['json_files_parsed']} JSON + {report['jsonl_files_parsed']} JSONL")
    print(f"Hash manifest: {report['hash_manifest_verified']}")
    print(f"Manifest mismatches: {len(report['manifest_mismatches'])}")
    return 0 if report["status"] == "PASS" and decision["status"] != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
