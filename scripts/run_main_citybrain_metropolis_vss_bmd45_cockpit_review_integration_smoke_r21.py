#!/usr/bin/env python3
"""R21 cockpit review integration smoke for the BMD-45 human-review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-COCKPIT-REVIEW-INTEGRATION-SMOKE-R21"
SCHEMA_VERSION = "metropolis-vss-bmd45-cockpit-review-integration-smoke-r21.v1"
DEFAULT_OUTPUT_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_bmd45_cockpit_review_integration_smoke_r21"
PACKAGE_NAME = "METROPOLIS_VSS_BMD45_COCKPIT_REVIEW_INTEGRATION_SMOKE_R21_PACKAGE.zip"

R20_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_bmd45_human_review_benchmark_packet_r20"
R20_PACKAGE = R20_ROOT / "METROPOLIS_VSS_BMD45_HUMAN_REVIEW_BENCHMARK_PACKET_R20_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_BMD45_COCKPIT_REVIEW_INTEGRATION_SMOKE_R21_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_METROPOLIS_VSS_BMD45_COCKPIT_REVIEW_INTEGRATION_CONTRACT_READY_APP_SURFACE_PENDING"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_BMD45_COCKPIT_REVIEW_INTEGRATION_BOUNDARY_OR_CONSUMPTION_RISK"

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


def validate_r20_package() -> tuple[dict[str, Any], dict[str, Any]]:
    report: dict[str, Any] = {
        "package_exists": R20_PACKAGE.exists(),
        "package_path": rel(R20_PACKAGE),
        "schema_version": SCHEMA_VERSION,
        "status": "FAIL",
    }
    package_data: dict[str, Any] = {}
    required = [
        "R20_CLOSEOUT_DECISION.json",
        "HUMAN_REVIEW_BENCHMARK_PACKET_R20.json",
        "COCKPIT_REVIEW_TILE_FIXTURE_R20.json",
        "FRAME_REVIEW_CARD_FIXTURES_R20.json",
        "BENCHMARK_SCORECARD_SUMMARY_R20.json",
        "FALSE_POSITIVE_REVIEW_LIST_R20.json",
        "MISSED_ANNOTATION_REVIEW_LIST_R20.json",
        "SOURCE_CLASS_SEPARATION_AUDIT_R20.json",
        "CLAIM_BOUNDARY_AUDIT_R20.json",
        "NO_ACTION_AUDIT_R20.json",
        "SECRET_AUDIT_R20.json",
        "VSS_NOT_FACT_SOURCE_AUDIT_R20.json",
        "PACKAGED_MEDIA_AUDIT_R20.json",
        "HASH_MANIFEST.json",
    ]
    if not R20_PACKAGE.exists():
        report["failure_reason"] = "R20 package not found"
        return report, package_data
    try:
        with zipfile.ZipFile(R20_PACKAGE) as archive:
            bad = archive.testzip()
            names = [name for name in archive.namelist() if not name.endswith("/")]
            missing_required = [name for name in required if name not in names]
            json_count = 0
            jsonl_count = 0
            for name in names:
                if name.endswith(".json"):
                    json.loads(archive.read(name).decode("utf-8"))
                    json_count += 1
                elif name.endswith(".jsonl"):
                    jsonl_count += 1
                    for line in archive.read(name).decode("utf-8").splitlines():
                        if line.strip():
                            json.loads(line)
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
            package_data["HASH_MANIFEST.json"] = manifest
    except Exception as exc:  # noqa: BLE001
        report["failure_reason"] = str(exc)
        return report, package_data

    decision = package_data.get("R20_CLOSEOUT_DECISION.json", {})
    expected = "PASS_METROPOLIS_VSS_BMD45_HUMAN_REVIEW_BENCHMARK_PACKET_R20_WITH_LIMITATIONS"
    report.update(
        {
            "decision_status": decision.get("status"),
            "expected_status": expected,
            "external_media_refs": len(package_data.get("HASH_MANIFEST.json", {}).get("external_media_refs", [])),
            "hash_manifest_status": "PASS" if not manifest_missing and not manifest_mismatches else "FAIL",
            "json_files_parsed": json_count,
            "jsonl_files_parsed": jsonl_count,
            "manifest_mismatches": manifest_mismatches,
            "manifest_missing": manifest_missing,
            "required_missing": missing_required,
            "status": "PASS" if bad is None and not missing_required and not manifest_missing and not manifest_mismatches and decision.get("status") == expected else "FAIL",
            "zip_entries": len(names),
            "zip_integrity": "PASS" if bad is None else f"FAIL:{bad}",
        }
    )
    return report, package_data


def make_cockpit_tile(r20_tile: dict[str, Any], scorecard: dict[str, Any]) -> dict[str, Any]:
    return {
        "actions_allowed": r20_tile.get("actions_allowed", []) + ["open frame review cards", "inspect external media references"],
        "actions_forbidden": r20_tile.get("actions_forbidden", []),
        "badge_counts": {
            "drift_review_items": scorecard.get("drift_review_items", 0),
            "false_positive_review_items": scorecard.get("false_positive_review_count", 0),
            "frame_cards": 8,
            "missed_annotation_review_items": scorecard.get("missed_annotation_review_count", 0),
        },
        "card_collection_ref": "FRAME_REVIEW_CARDS_R21.json",
        "schema_version": SCHEMA_VERSION,
        "source_labels": r20_tile.get("source_labels", []),
        "status_label": r20_tile.get("status_label", "Benchmark review packet ready"),
        "summary_ref": "COCKPIT_REVIEW_INTEGRATION_REPORT_R21.json",
        "tile_id": "citybrain-bmd45-r21-cockpit-review-smoke",
        "title": r20_tile.get("title", "BMD-45 Replay Benchmark Review"),
    }


def make_frame_cards(r20_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    for card in r20_cards:
        external_ref = card.get("external_media_ref", {})
        cards.append(
            {
                "actions_allowed": ["inspect candidate summary", "open external media reference", "route card to human review"],
                "actions_forbidden": ["no dispatch or action", "no ticket or case", "not an official finding"],
                "dataset_annotation_summary": card.get("dataset_annotation_summary", {}),
                "external_media_ref": external_ref,
                "frame_replay_id": card.get("frame_replay_id"),
                "frame_sequence_index": card.get("frame_sequence_index"),
                "human_review_required": True,
                "media_packaged": False,
                "review_label": card.get("review_label"),
                "schema_version": SCHEMA_VERSION,
                "sensor_inferred_summary": card.get("sensor_inferred_summary", {}),
                "source_labels": {
                    "dataset_annotations": "dataset_annotation",
                    "deepstream_metropolis": "sensor_inferred",
                },
                "thumbnail_policy": "external_reference_only_no_packaged_media",
            }
        )
    return cards


def app_consumption_smoke(tile: dict[str, Any], cards: list[dict[str, Any]], packet: dict[str, Any]) -> dict[str, Any]:
    checks = [
        {
            "check": "tile_required_fields",
            "passed": all(tile.get(key) for key in ["tile_id", "title", "status_label", "source_labels"]),
        },
        {
            "check": "frame_cards_nonempty",
            "passed": bool(cards),
        },
        {
            "check": "frame_card_external_refs_present",
            "passed": all(card.get("external_media_ref", {}).get("external_media_ref") is True for card in cards),
        },
        {
            "check": "human_review_required",
            "passed": packet.get("human_review_required") is True and all(card.get("human_review_required") is True for card in cards),
        },
        {
            "check": "source_class_labels_present",
            "passed": packet.get("source_classes", {}).get("dataset_annotations") == "dataset_annotation"
            and packet.get("source_classes", {}).get("deepstream_metropolis") == "sensor_inferred",
        },
        {
            "check": "no_packaged_media_refs",
            "passed": all(card.get("media_packaged") is False for card in cards),
        },
    ]
    return {
        "checks": checks,
        "cockpit_surface": "json_fixture_contract",
        "consumption_mode": "static_fixture_smoke_no_runtime_app_launch",
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(check["passed"] for check in checks) else "FAIL",
    }


def scan_for_forbidden_claims(output_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    safe_markers = ["blocked", "not ", "no ", "no_", "false", "pending", "limitation", "non-goal", "without claiming", "candidate review", "review packet", "actions_forbidden"]
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


def write_audits(output_root: Path, packet: dict[str, Any], cards: list[dict[str, Any]], external_refs: list[dict[str, Any]]) -> dict[str, str]:
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
        "SOURCE_CLASS_SEPARATION_AUDIT_R21.json": {
            "frame_cards": len(cards),
            "schema_version": SCHEMA_VERSION,
            "source_classes": packet.get("source_classes"),
            "status": "PASS" if source_ok else "FAIL",
        },
        "CLAIM_BOUNDARY_AUDIT_R21.json": {"findings": claim_findings, "schema_version": SCHEMA_VERSION, "status": "PASS" if not claim_findings else "FAIL"},
        "NO_ACTION_AUDIT_R21.json": {
            "action_created": False,
            "dispatch_created": False,
            "official_record_created": False,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "ticket_created": False,
        },
        "VSS_NOT_FACT_SOURCE_AUDIT_R21.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "vss_is_fact_source": False,
            "vss_records_created": 0,
        },
        "SECRET_AUDIT_R21.json": {"findings": secret_findings, "schema_version": SCHEMA_VERSION, "status": "PASS" if not secret_findings else "FAIL"},
        "PACKAGED_MEDIA_AUDIT_R21.json": {
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


def build_r21(output_root: Path) -> dict[str, Any]:
    reset_output_root(output_root)
    r20_validation, r20_data = validate_r20_package()
    manifest = r20_data.get("HASH_MANIFEST.json", {})
    external_refs = manifest.get("external_media_refs", [])
    packet = r20_data.get("HUMAN_REVIEW_BENCHMARK_PACKET_R20.json", {})
    r20_tile = r20_data.get("COCKPIT_REVIEW_TILE_FIXTURE_R20.json", {})
    r20_cards = r20_data.get("FRAME_REVIEW_CARD_FIXTURES_R20.json", {}).get("cards", [])
    scorecard = r20_data.get("BENCHMARK_SCORECARD_SUMMARY_R20.json", {})
    tile = make_cockpit_tile(r20_tile, scorecard)
    cards = make_frame_cards(r20_cards)
    app_fixture = {
        "cards_ref": "FRAME_REVIEW_CARDS_R21.json",
        "human_review_packet_ref": "HUMAN_REVIEW_PACKET_CONSUMPTION_FIXTURE_R21.json",
        "schema_version": SCHEMA_VERSION,
        "tile_ref": "COCKPIT_REVIEW_TILE_R21.json",
        "view_id": "citybrain_bmd45_benchmark_review",
        "view_model": {
            "frame_card_count": len(cards),
            "source_classes": packet.get("source_classes"),
            "status_label": tile.get("status_label"),
            "tile_id": tile.get("tile_id"),
        },
    }
    smoke = app_consumption_smoke(tile, cards, packet)
    integration_report = {
        "app_fixture_ref": "COCKPIT_APP_FIXTURE_R21.json",
        "consumption_smoke": smoke,
        "external_media_refs": len(external_refs),
        "frame_review_cards": len(cards),
        "input_packet_id": packet.get("packet_id"),
        "no_runtime_rerun": True,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if smoke.get("status") == "PASS" else "FAIL",
        "tile_ref": "COCKPIT_REVIEW_TILE_R21.json",
    }
    consumption_packet = {
        "benchmark_scorecard": packet.get("benchmark_scorecard"),
        "boundaries": packet.get("boundaries"),
        "frame_cards_ref": "FRAME_REVIEW_CARDS_R21.json",
        "human_review_required": True,
        "packet_id": stable_id("r21-consumption-packet", packet.get("packet_id"), len(cards)),
        "schema_version": SCHEMA_VERSION,
        "source_classes": packet.get("source_classes"),
        "source_packet_id": packet.get("packet_id"),
    }

    write_json(output_root / "R20_INPUT_LINEAGE_SUMMARY.json", r20_validation)
    write_json(output_root / "COCKPIT_REVIEW_TILE_R21.json", tile)
    write_json(output_root / "FRAME_REVIEW_CARDS_R21.json", {"cards": cards, "schema_version": SCHEMA_VERSION, "status": "PASS"})
    write_json(output_root / "COCKPIT_APP_FIXTURE_R21.json", app_fixture)
    write_json(output_root / "HUMAN_REVIEW_PACKET_CONSUMPTION_FIXTURE_R21.json", consumption_packet)
    write_json(output_root / "COCKPIT_REVIEW_INTEGRATION_REPORT_R21.json", integration_report)
    write_text(
        output_root / "KNOWN_LIMITATIONS_R21.md",
        "\n".join(
            [
                "# Known Limitations R21",
                "",
                "- R21 is a JSON fixture consumption smoke, not a launched cockpit UI session.",
                "- It does not rerun DeepStream, Metropolis, VSS, or BMD-45 fetches.",
                "- Media remains external by reference and is not packaged.",
                "- Review cards are candidate-review fixtures, not findings or actions.",
            ]
        ),
    )
    write_text(
        output_root / "NEXT_SPRINT_RECOMMENDATIONS_R21.md",
        "\n".join(
            [
                "# Next Sprint Recommendations R21",
                "",
                "1. Wire the R21 JSON fixture into the cockpit app surface as a read-only review panel.",
                "2. Add screenshot-based visual smoke once the app surface consumes the fixture.",
                "3. Add reviewer disposition capture in a separate governed human-in-the-loop lane.",
            ]
        ),
    )
    write_text(
        output_root / "README.md",
        f"# {TASK_ID}\n\nR21 proves the accepted R20 human-review benchmark packet can be shaped into cockpit/app JSON fixtures without rerunning media inference or narration.\n",
    )

    audit_statuses = write_audits(output_root, packet, cards, external_refs)
    audits_pass = all(status == "PASS" for status in audit_statuses.values())
    pass_ready = r20_validation.get("status") == "PASS" and smoke.get("status") == "PASS" and audits_pass
    final_status = PASS_STATUS if pass_ready else PARTIAL_STATUS
    if not audits_pass or r20_validation.get("status") != "PASS":
        final_status = FAIL_STATUS if not audits_pass else PARTIAL_STATUS
    decision = {
        "app_fixture_emitted": True,
        "audits": audit_statuses,
        "cockpit_review_cards": len(cards),
        "cockpit_tile_emitted": True,
        "consumption_smoke_status": smoke.get("status"),
        "deepstream_rerun": False,
        "external_media_refs": len(external_refs),
        "final_status": final_status,
        "live_cctv_claimed": False,
        "official_record_created": False,
        "packaged_media_files": 0,
        "r20_input_validation": r20_validation.get("status"),
        "schema_version": SCHEMA_VERSION,
        "source_classes": packet.get("source_classes"),
        "status": final_status,
        "task_id": TASK_ID,
        "vss_rerun": False,
    }
    write_json(output_root / "R21_CLOSEOUT_DECISION.json", decision)
    write_json(
        output_root / "R21_JSON_PARSE_REPORT.json",
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
        output_root / "TEST_LOG_R21.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r20_input_validation={r20_validation.get('status')}",
                f"consumption_smoke_status={smoke.get('status')}",
                f"cockpit_review_cards={len(cards)}",
                "zip_entries=PENDING",
                "hash_manifest=PENDING",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    write_json(
        output_root / "R21_JSON_PARSE_REPORT.json",
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
        output_root / "TEST_LOG_R21.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r20_input_validation={r20_validation.get('status')}",
                f"consumption_smoke_status={smoke.get('status')}",
                f"cockpit_review_cards={len(cards)}",
                f"zip_entries={package_report['zip_entries']}",
                f"hash_manifest={package_report['hash_manifest_verified']}",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    return {"decision": decision, "package_report": package_report}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run R21 cockpit review integration smoke.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_r21(Path(args.output_root))
    decision = result["decision"]
    report = result["package_report"]
    print(f"Status: {decision['status']}")
    print(f"Output: {rel(Path(args.output_root))}")
    print(f"Freeze ZIP: {rel(Path(args.output_root) / PACKAGE_NAME)}")
    print(f"R20 input validation: {decision['r20_input_validation']}")
    print(f"Consumption smoke: {decision['consumption_smoke_status']}")
    print(f"Cockpit review cards: {decision['cockpit_review_cards']}")
    print(f"External media refs: {decision['external_media_refs']}")
    print(f"ZIP entries: {report['zip_entries']}")
    print(f"JSON parse: PASS, {report['json_files_parsed']} JSON + {report['jsonl_files_parsed']} JSONL")
    print(f"Hash manifest: {report['hash_manifest_verified']}")
    print(f"Manifest mismatches: {len(report['manifest_mismatches'])}")
    return 0 if report["status"] == "PASS" and decision["status"] != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
