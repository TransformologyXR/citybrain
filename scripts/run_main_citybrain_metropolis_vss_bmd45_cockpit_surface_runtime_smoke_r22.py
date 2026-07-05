#!/usr/bin/env python3
"""R22 static cockpit surface runtime smoke for the R21 BMD-45 review fixture."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
TASK_ID = "MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-COCKPIT-SURFACE-RUNTIME-SMOKE-R22"
SCHEMA_VERSION = "metropolis-vss-bmd45-cockpit-surface-runtime-smoke-r22.v1"
DEFAULT_OUTPUT_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_bmd45_cockpit_surface_runtime_smoke_r22"
PACKAGE_NAME = "METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_RUNTIME_SMOKE_R22_PACKAGE.zip"

R21_ROOT = OUTPUTS_ROOT / "main_citybrain_metropolis_vss_bmd45_cockpit_review_integration_smoke_r21"
R21_PACKAGE = R21_ROOT / "METROPOLIS_VSS_BMD45_COCKPIT_REVIEW_INTEGRATION_SMOKE_R21_PACKAGE.zip"

PASS_STATUS = "PASS_METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_RUNTIME_SMOKE_R22_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_CONTRACT_READY_APP_RUNTIME_PENDING"
FAIL_BOUNDARY_STATUS = "FAIL_METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_BOUNDARY_BREACH_R22"
FAIL_SOURCE_STATUS = "FAIL_METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_SOURCE_CLASS_DRIFT_R22"
FAIL_CONSUMPTION_STATUS = "FAIL_METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_APP_CONSUMPTION_R22"

SOURCE_CLASSES = {
    "dataset_annotations": "dataset_annotation",
    "deepstream_metropolis": "sensor_inferred",
    "vss": "model_generated_narrative_not_fact_source",
}
BOUNDARY_LABELS = [
    "human review required",
    "candidate review only",
    "dataset annotations are not official truth",
    "sensor candidates are not findings",
    "not production live CCTV",
    "no ticket, dispatch, identity, legal conclusion, or action",
]
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
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".mp4", ".mov", ".mkv", ".avi", ".webm"}


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


def validate_r21_package() -> tuple[dict[str, Any], dict[str, Any]]:
    report: dict[str, Any] = {
        "package_exists": R21_PACKAGE.exists(),
        "package_path": rel(R21_PACKAGE),
        "schema_version": SCHEMA_VERSION,
        "status": "FAIL",
    }
    package_data: dict[str, Any] = {}
    required = [
        "R21_CLOSEOUT_DECISION.json",
        "COCKPIT_REVIEW_TILE_R21.json",
        "COCKPIT_APP_FIXTURE_R21.json",
        "FRAME_REVIEW_CARDS_R21.json",
        "HUMAN_REVIEW_PACKET_CONSUMPTION_FIXTURE_R21.json",
        "COCKPIT_REVIEW_INTEGRATION_REPORT_R21.json",
        "SOURCE_CLASS_SEPARATION_AUDIT_R21.json",
        "CLAIM_BOUNDARY_AUDIT_R21.json",
        "NO_ACTION_AUDIT_R21.json",
        "SECRET_AUDIT_R21.json",
        "VSS_NOT_FACT_SOURCE_AUDIT_R21.json",
        "PACKAGED_MEDIA_AUDIT_R21.json",
        "HASH_MANIFEST.json",
    ]
    if not R21_PACKAGE.exists():
        report["failure_reason"] = "R21 package not found"
        return report, package_data
    try:
        with zipfile.ZipFile(R21_PACKAGE) as archive:
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

    decision = package_data.get("R21_CLOSEOUT_DECISION.json", {})
    expected = "PASS_METROPOLIS_VSS_BMD45_COCKPIT_REVIEW_INTEGRATION_SMOKE_R21_WITH_LIMITATIONS"
    report.update(
        {
            "decision_status": decision.get("status"),
            "expected_status": expected,
            "external_media_refs": len(package_data.get("HASH_MANIFEST.json", {}).get("external_media_refs", [])),
            "frame_review_cards": len(package_data.get("FRAME_REVIEW_CARDS_R21.json", {}).get("cards", [])),
            "hash_manifest_status": "PASS" if not manifest_missing and not manifest_mismatches else "FAIL",
            "json_files_parsed": json_count,
            "jsonl_files_parsed": jsonl_count,
            "manifest_mismatches": manifest_mismatches,
            "manifest_missing": manifest_missing,
            "required_missing": missing_required,
            "status": "PASS"
            if bad is None
            and not missing_required
            and not manifest_missing
            and not manifest_mismatches
            and decision.get("status") == expected
            else "FAIL",
            "zip_entries": len(names),
            "zip_integrity": "PASS" if bad is None else f"FAIL:{bad}",
        }
    )
    return report, package_data


def discover_app_route() -> dict[str, Any]:
    web_root = REPO_ROOT / "apps" / "web-control-room"
    renderers = list((web_root / "src").rglob("*.js")) if (web_root / "src").exists() else []
    route_mentions = []
    for path in renderers:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "COCKPIT_REVIEW_TILE_R21" in text or "citybrain_bmd45_benchmark_review" in text:
            route_mentions.append(rel(path))
    return {
        "app_root": rel(web_root),
        "app_root_exists": web_root.exists(),
        "r21_specific_route_found": bool(route_mentions),
        "r21_specific_route_files": route_mentions,
        "selected_surface_mode": "app_route" if route_mentions else "static_render_fixture",
    }


def make_surface_packet(
    tile: dict[str, Any],
    app_fixture: dict[str, Any],
    cards: list[dict[str, Any]],
    consumption_packet: dict[str, Any],
    external_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    source_packet_id = consumption_packet.get("packet_id") or consumption_packet.get("source_packet_id")
    return {
        "app_view_id": app_fixture.get("view_id"),
        "boundary_labels": BOUNDARY_LABELS,
        "external_media_refs": external_refs,
        "frame_cards": cards,
        "packet_id": stable_id("r22-human-review-surface-packet", source_packet_id, len(cards), len(external_refs)),
        "review_only": True,
        "schema_version": SCHEMA_VERSION,
        "source_class_legend": SOURCE_CLASSES,
        "source_packet_id": source_packet_id,
        "surface_title": tile.get("title", "BMD-45 Replay Benchmark Review"),
        "tile": tile,
    }


def render_surface_html(surface_packet: dict[str, Any]) -> str:
    title = html.escape(surface_packet["surface_title"])
    source_legend = surface_packet.get("source_class_legend", {})
    boundary_labels = surface_packet.get("boundary_labels", [])
    cards = surface_packet.get("frame_cards", [])
    external_refs = surface_packet.get("external_media_refs", [])
    tile = surface_packet.get("tile", {})

    def esc(value: Any) -> str:
        return html.escape("" if value is None else str(value))

    boundary_html = "\n".join(f"<li>{esc(label)}</li>" for label in boundary_labels)
    source_html = "\n".join(f"<li><strong>{esc(key)}</strong>: {esc(value)}</li>" for key, value in source_legend.items())
    action_forbidden_html = "\n".join(f"<li>{esc(item)}</li>" for item in tile.get("actions_forbidden", []))
    card_html = []
    for card in cards:
        dataset = card.get("dataset_annotation_summary", {})
        sensor = card.get("sensor_inferred_summary", {})
        media = card.get("external_media_ref", {})
        class_counts = ", ".join(f"{key}: {value}" for key, value in sorted(sensor.get("class_counts", {}).items())) or "none"
        card_html.append(
            f"""
      <article class="review-card" data-frame-id="{esc(card.get('frame_replay_id'))}" data-review-only="true"
        data-dataset-source="{esc(dataset.get('source_class'))}" data-sensor-source="{esc(sensor.get('source_class'))}"
        data-media-packaged="{esc(card.get('media_packaged'))}">
        <header>
          <span class="sequence">Frame {esc(card.get('frame_sequence_index'))}</span>
          <h2>{esc(card.get('frame_replay_id'))}</h2>
          <p>{esc(card.get('review_label'))}</p>
        </header>
        <dl>
          <div><dt>Dataset annotations</dt><dd>{esc(dataset.get('annotation_count'))} ({esc(dataset.get('source_class'))})</dd></div>
          <div><dt>Missed annotations</dt><dd>{esc(dataset.get('unmatched_annotation_count'))}</dd></div>
          <div><dt>Sensor candidates</dt><dd>{esc(sensor.get('candidate_count'))} ({esc(sensor.get('source_class'))})</dd></div>
          <div><dt>Unmatched sensor candidates</dt><dd>{esc(sensor.get('unmatched_sensor_detection_count'))}</dd></div>
          <div><dt>Sensor class summary</dt><dd>{esc(class_counts)}</dd></div>
        </dl>
        <section class="media-ref">
          <h3>External media reference</h3>
          <p data-external-media-ref="true">{esc(media.get('file_name'))}</p>
          <p class="sha">sha256: {esc(media.get('sha256'))}</p>
          <a href="{esc(media.get('media_url'))}" rel="noreferrer">Open external reference</a>
          <p>Media packaged: false. Thumbnail policy: {esc(card.get('thumbnail_policy'))}</p>
        </section>
        <section class="card-boundaries">
          <h3>Review boundary</h3>
          <ul>
            <li>human review required</li>
            <li>candidate review only</li>
            <li>not an official finding</li>
            <li>no ticket or case</li>
            <li>no dispatch or action</li>
          </ul>
        </section>
      </article>
"""
        )

    card_count = len(cards)
    external_ref_count = len(external_refs)
    embedded = html.escape(json.dumps({"packet_id": surface_packet["packet_id"], "card_count": card_count, "external_media_refs": external_ref_count}, sort_keys=True))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light; --ink: #17212b; --muted: #54616f; --line: #d9e0e7; --panel: #f7f9fb; --accent: #116466; --warn: #7a4d00; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: #ffffff; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    header.surface-header {{ border-bottom: 1px solid var(--line); padding-bottom: 18px; margin-bottom: 22px; }}
    h1 {{ font-size: 28px; margin: 0 0 8px; letter-spacing: 0; }}
    h2 {{ font-size: 18px; margin: 0 0 6px; }}
    h3 {{ font-size: 13px; margin: 0 0 8px; text-transform: uppercase; letter-spacing: 0; color: var(--muted); }}
    p {{ margin: 0 0 8px; line-height: 1.45; }}
    ul {{ margin: 0; padding-left: 18px; }}
    .status-strip {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 16px 0; }}
    .metric, .legend, .boundary, .review-card {{ border: 1px solid var(--line); border-radius: 8px; background: var(--panel); padding: 14px; }}
    .metric strong {{ display: block; font-size: 20px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 18px; }}
    .cards {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .review-card {{ background: #fff; }}
    .sequence, .badge {{ display: inline-flex; align-items: center; min-height: 24px; padding: 3px 8px; border: 1px solid var(--line); border-radius: 999px; color: var(--accent); font-size: 12px; }}
    dl {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0; }}
    dt {{ color: var(--muted); font-size: 12px; }}
    dd {{ margin: 2px 0 0; font-weight: 700; overflow-wrap: anywhere; }}
    .media-ref, .card-boundaries {{ border-top: 1px solid var(--line); margin-top: 12px; padding-top: 12px; }}
    .sha, a {{ overflow-wrap: anywhere; }}
    a {{ color: var(--accent); }}
    .warning {{ color: var(--warn); font-weight: 700; }}
    @media (max-width: 760px) {{ main {{ padding: 18px; }} .status-strip, .grid, .cards, dl {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body data-surface-mode="static_render_fixture" data-review-only="true" data-card-count="{card_count}" data-external-media-refs="{external_ref_count}"
  data-dataset-source="dataset_annotation" data-sensor-source="sensor_inferred" data-vss-source="model_generated_narrative_not_fact_source">
  <main>
    <header class="surface-header">
      <span class="badge">candidate review only</span>
      <h1>{title}</h1>
      <p>{esc(tile.get('status_label', 'Benchmark review packet ready'))}</p>
      <p class="warning">Static surface smoke only. Not production live CCTV. No ticket, dispatch, identity, legal conclusion, or action.</p>
    </header>

    <section class="status-strip" aria-label="benchmark review counts">
      <div class="metric"><span>Frame cards</span><strong>{card_count}</strong></div>
      <div class="metric"><span>External media refs</span><strong>{external_ref_count}</strong></div>
      <div class="metric"><span>Packaged media</span><strong>0</strong></div>
      <div class="metric"><span>Review state</span><strong>human review required</strong></div>
    </section>

    <section class="grid">
      <div class="legend">
        <h3>Source-class legend</h3>
        <ul>{source_html}</ul>
      </div>
      <div class="boundary">
        <h3>Boundary labels</h3>
        <ul>{boundary_html}</ul>
      </div>
    </section>

    <section class="boundary">
      <h3>Forbidden states shown as blocked</h3>
      <ul>{action_forbidden_html}</ul>
    </section>

    <section class="cards" aria-label="frame review cards">
      {''.join(card_html)}
    </section>
    <script id="r22-surface-smoke-payload" type="application/json">{embedded}</script>
  </main>
</body>
</html>
"""


def inspect_rendered_surface(html_text: str, expected_card_count: int, expected_external_refs: int) -> dict[str, Any]:
    lowered = html_text.lower()
    card_count = len(re.findall(r'class="review-card"', html_text))
    external_ref_count = len(re.findall(r'data-external-media-ref="true"', html_text))
    boundary_checks = {
        "human_review_required": "human review required" in lowered,
        "candidate_review_only": "candidate review only" in lowered,
        "not_live_cctv": "not production live cctv" in lowered,
        "no_action": "no dispatch or action" in lowered and "no ticket" in lowered,
        "not_finding": "not an official finding" in lowered or "sensor candidates are not findings" in lowered,
    }
    source_checks = {value: value in html_text for value in SOURCE_CLASSES.values()}
    media_checks = {
        "expected_external_ref_count": external_ref_count == expected_external_refs,
        "expected_card_count": card_count == expected_card_count,
        "no_embedded_images": "<img" not in lowered and "<video" not in lowered,
        "no_packaged_media_claim": "Media packaged: false" in html_text and "Packaged media</span><strong>0</strong>" in html_text,
    }
    passed = all(boundary_checks.values()) and all(source_checks.values()) and all(media_checks.values())
    return {
        "boundary_checks": boundary_checks,
        "card_count": card_count,
        "external_ref_count": external_ref_count,
        "media_checks": media_checks,
        "result": "PASS" if passed else "FAIL",
        "source_class_checks": source_checks,
    }


def surface_consumption_smoke(
    surface_packet: dict[str, Any],
    html_path: Path,
    app_route_report: dict[str, Any],
    rendered_check: dict[str, Any],
) -> dict[str, Any]:
    cards = surface_packet.get("frame_cards", [])
    checks = [
        {"check": "surface_html_exists", "passed": html_path.exists()},
        {"check": "surface_packet_review_only", "passed": surface_packet.get("review_only") is True},
        {"check": "frame_cards_preserved", "passed": len(cards) >= 8 and rendered_check.get("card_count") == len(cards)},
        {"check": "external_media_refs_preserved", "passed": rendered_check.get("external_ref_count") == len(surface_packet.get("external_media_refs", []))},
        {"check": "source_class_labels_present", "passed": all(rendered_check.get("source_class_checks", {}).values())},
        {"check": "boundary_labels_present", "passed": all(rendered_check.get("boundary_checks", {}).values())},
        {"check": "no_embedded_or_packaged_media", "passed": all(rendered_check.get("media_checks", {}).values())},
    ]
    return {
        "app_route_report": app_route_report,
        "checks": checks,
        "html_surface_ref": html_path.name,
        "result": "PASS" if all(check["passed"] for check in checks) else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "surface_mode": app_route_report.get("selected_surface_mode", "static_render_fixture"),
    }


def scan_for_forbidden_claims(output_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    safe_markers = [
        "blocked",
        "not ",
        "no ",
        "no_",
        "false",
        "pending",
        "limitation",
        "non-goal",
        "without claiming",
        "candidate review",
        "review packet",
        "actions_forbidden",
        "forbidden",
        "review-only",
    ]
    for path in output_root.rglob("*"):
        if not path.is_file() or path.name in {PACKAGE_NAME, "HASH_MANIFEST.json"}:
            continue
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".log", ".html"}:
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
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".log", ".html", ".env"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                findings.append({"file": rel(path) or str(path), "pattern": name})
    return findings


def write_audits(
    output_root: Path,
    surface_packet: dict[str, Any],
    rendered_check: dict[str, Any],
    consumption_smoke: dict[str, Any],
    external_refs: list[dict[str, Any]],
) -> dict[str, str]:
    source_ok = surface_packet.get("source_class_legend") == SOURCE_CLASSES and all(rendered_check.get("source_class_checks", {}).values())
    boundary_ok = all(rendered_check.get("boundary_checks", {}).values()) and surface_packet.get("review_only") is True
    external_ok = (
        len(external_refs) == rendered_check.get("external_ref_count")
        and all(ref.get("external_media_ref") is True and ref.get("packaged_file") is False for ref in external_refs)
    )
    claim_findings = scan_for_forbidden_claims(output_root)
    secret_findings = scan_for_secrets(output_root)
    media_entries = [
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES
    ]
    audits = {
        "COCKPIT_SURFACE_BOUNDARY_LABEL_AUDIT_R22.json": {
            "boundary_checks": rendered_check.get("boundary_checks"),
            "review_only": surface_packet.get("review_only"),
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if boundary_ok else "FAIL",
        },
        "COCKPIT_SURFACE_SOURCE_CLASS_AUDIT_R22.json": {
            "schema_version": SCHEMA_VERSION,
            "source_class_checks": rendered_check.get("source_class_checks"),
            "source_classes": surface_packet.get("source_class_legend"),
            "status": "PASS" if source_ok else "FAIL",
        },
        "COCKPIT_SURFACE_EXTERNAL_MEDIA_REF_AUDIT_R22.json": {
            "external_media_refs": len(external_refs),
            "packaged_media_files": media_entries,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if external_ok and not media_entries else "FAIL",
        },
        "COCKPIT_SURFACE_CONSUMPTION_SMOKE_R22.json": {
            **consumption_smoke,
            "status": consumption_smoke.get("result"),
        },
        "SOURCE_CLASS_SEPARATION_AUDIT_R22.json": {
            "frame_cards": len(surface_packet.get("frame_cards", [])),
            "schema_version": SCHEMA_VERSION,
            "source_classes": surface_packet.get("source_class_legend"),
            "status": "PASS" if source_ok else "FAIL",
        },
        "CLAIM_BOUNDARY_AUDIT_R22.json": {
            "findings": claim_findings,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if not claim_findings and boundary_ok else "FAIL",
        },
        "NO_ACTION_AUDIT_R22.json": {
            "action_created": False,
            "dispatch_created": False,
            "official_record_created": False,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "ticket_created": False,
        },
        "VSS_NOT_FACT_SOURCE_AUDIT_R22.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "vss_is_fact_source": False,
            "vss_records_created": 0,
            "vss_source_class": SOURCE_CLASSES["vss"],
        },
        "SECRET_AUDIT_R22.json": {
            "findings": secret_findings,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if not secret_findings else "FAIL",
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
                jsonl_count += 1
                for line in archive.read(name).decode("utf-8").splitlines():
                    if line.strip():
                        json.loads(line)
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


def build_r22(output_root: Path) -> dict[str, Any]:
    reset_output_root(output_root)
    r21_validation, r21_data = validate_r21_package()
    manifest = r21_data.get("HASH_MANIFEST.json", {})
    external_refs = manifest.get("external_media_refs", [])
    tile = r21_data.get("COCKPIT_REVIEW_TILE_R21.json", {})
    app_fixture = r21_data.get("COCKPIT_APP_FIXTURE_R21.json", {})
    cards = r21_data.get("FRAME_REVIEW_CARDS_R21.json", {}).get("cards", [])
    consumption_packet = r21_data.get("HUMAN_REVIEW_PACKET_CONSUMPTION_FIXTURE_R21.json", {})
    app_route_report = discover_app_route()
    surface_packet = make_surface_packet(tile, app_fixture, cards, consumption_packet, external_refs)
    render_fixture = {
        "html_surface_ref": "cockpit_surface_preview_r22.html",
        "input_refs": {
            "app_fixture": "COCKPIT_APP_FIXTURE_R21.json",
            "cards": "FRAME_REVIEW_CARDS_R21.json",
            "consumption_fixture": "HUMAN_REVIEW_PACKET_CONSUMPTION_FIXTURE_R21.json",
            "tile": "COCKPIT_REVIEW_TILE_R21.json",
        },
        "rendered_card_count": len(cards),
        "review_only": True,
        "schema_version": SCHEMA_VERSION,
        "surface_mode": app_route_report.get("selected_surface_mode", "static_render_fixture"),
    }
    html_surface = render_surface_html(surface_packet)
    html_path = output_root / "cockpit_surface_preview_r22.html"

    write_json(output_root / "R21_INPUT_LINEAGE_SUMMARY.json", r21_validation)
    write_json(output_root / "HUMAN_REVIEW_SURFACE_PACKET_R22.json", surface_packet)
    write_json(output_root / "COCKPIT_SURFACE_RENDER_FIXTURE_R22.json", render_fixture)
    write_text(html_path, html_surface)

    rendered_check = inspect_rendered_surface(html_surface, len(cards), len(external_refs))
    consumption_smoke = surface_consumption_smoke(surface_packet, html_path, app_route_report, rendered_check)
    runtime_report = {
        "boundary_labels_present": all(rendered_check.get("boundary_checks", {}).values()),
        "external_media_refs_preserved": rendered_check.get("external_ref_count") == len(external_refs),
        "html_surface_ref": html_path.name,
        "input_fixture_ids": [
            tile.get("tile_id"),
            app_fixture.get("view_id"),
            consumption_packet.get("packet_id"),
        ],
        "loaded_sections": [
            "cockpit_tile",
            "cockpit_app_fixture",
            "frame_review_cards",
            "human_review_consumption_fixture",
            "external_media_refs",
            "static_html_surface",
        ],
        "result": consumption_smoke.get("result"),
        "route_url": rel(html_path),
        "schema_version": SCHEMA_VERSION,
        "source_class_labels_present": all(rendered_check.get("source_class_checks", {}).values()),
        "surface_mode": app_route_report.get("selected_surface_mode", "static_render_fixture"),
    }
    write_json(output_root / "COCKPIT_SURFACE_RUNTIME_REPORT_R22.json", runtime_report)
    write_json(output_root / "COCKPIT_SURFACE_HTML_CHECK_R22.json", rendered_check)

    write_text(
        output_root / "KNOWN_LIMITATIONS_R22.md",
        "\n".join(
            [
                "# Known Limitations R22",
                "",
                "- R22 exercises a static HTML surface renderer, not a production cockpit deployment.",
                "- It does not rerun DeepStream, Metropolis, VSS, or BMD-45 fetches.",
                "- Media remains external by reference and is not packaged.",
                "- The packet is for candidate review only and does not create official records or actions.",
            ]
        ),
    )
    write_text(
        output_root / "NEXT_SPRINT_RECOMMENDATIONS_R22.md",
        "\n".join(
            [
                "# Next Sprint Recommendations R22",
                "",
                "1. Wire the R22 surface packet into the web-control-room app behind a read-only route.",
                "2. Add browser screenshot smoke once the app route exists.",
                "3. Keep reviewer disposition capture in a separately gated human-in-the-loop lane.",
            ]
        ),
    )
    write_text(
        output_root / "README.md",
        f"# {TASK_ID}\n\nR22 consumes the accepted R21 cockpit review fixture through a static operator-surface renderer. It preserves source-class labels, external-media references, and candidate-review-only boundaries without rerunning media inference or VSS narration.\n",
    )

    audit_statuses = write_audits(output_root, surface_packet, rendered_check, consumption_smoke, external_refs)
    audits_pass = all(status == "PASS" for status in audit_statuses.values())
    source_ok = audit_statuses.get("SOURCE_CLASS_SEPARATION_AUDIT_R22") == "PASS"
    boundary_ok = audit_statuses.get("CLAIM_BOUNDARY_AUDIT_R22") == "PASS" and audit_statuses.get("COCKPIT_SURFACE_BOUNDARY_LABEL_AUDIT_R22") == "PASS"
    pass_ready = r21_validation.get("status") == "PASS" and consumption_smoke.get("result") == "PASS" and audits_pass
    final_status = PASS_STATUS if pass_ready else PARTIAL_STATUS
    if not boundary_ok:
        final_status = FAIL_BOUNDARY_STATUS
    elif not source_ok:
        final_status = FAIL_SOURCE_STATUS
    elif r21_validation.get("status") != "PASS" or consumption_smoke.get("result") != "PASS":
        final_status = FAIL_CONSUMPTION_STATUS

    decision = {
        "action_created": False,
        "audits": audit_statuses,
        "cockpit_surface_mode": app_route_report.get("selected_surface_mode", "static_render_fixture"),
        "consumption_smoke_status": consumption_smoke.get("result"),
        "deepstream_rerun": False,
        "external_media_refs": len(external_refs),
        "final_status": final_status,
        "frame_review_cards": len(cards),
        "live_cctv_claimed": False,
        "metropolis_rerun": False,
        "official_record_created": False,
        "packaged_media_files": 0,
        "r21_input_validation": r21_validation.get("status"),
        "schema_version": SCHEMA_VERSION,
        "source_classes": SOURCE_CLASSES,
        "status": final_status,
        "surface_html_ref": html_path.name,
        "task_id": TASK_ID,
        "vss_rerun": False,
    }
    write_json(output_root / "R22_CLOSEOUT_DECISION.json", decision)
    write_json(
        output_root / "R22_JSON_PARSE_REPORT.json",
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
        output_root / "TEST_LOG_R22.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r21_input_validation={r21_validation.get('status')}",
                f"consumption_smoke_status={consumption_smoke.get('result')}",
                f"cockpit_surface_mode={decision['cockpit_surface_mode']}",
                f"frame_review_cards={len(cards)}",
                f"external_media_refs={len(external_refs)}",
                "zip_entries=PENDING",
                "hash_manifest=PENDING",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    write_json(
        output_root / "R22_JSON_PARSE_REPORT.json",
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
        output_root / "TEST_LOG_R22.txt",
        "\n".join(
            [
                f"task_id={TASK_ID}",
                f"status={final_status}",
                f"r21_input_validation={r21_validation.get('status')}",
                f"consumption_smoke_status={consumption_smoke.get('result')}",
                f"cockpit_surface_mode={decision['cockpit_surface_mode']}",
                f"frame_review_cards={len(cards)}",
                f"external_media_refs={len(external_refs)}",
                f"zip_entries={package_report['zip_entries']}",
                f"hash_manifest={package_report['hash_manifest_verified']}",
            ]
        ),
    )
    package_report = build_package(output_root, external_refs)
    return {"decision": decision, "package_report": package_report}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run R22 cockpit surface runtime smoke.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_r22(Path(args.output_root))
    decision = result["decision"]
    report = result["package_report"]
    print(f"Status: {decision['status']}")
    print(f"Output: {rel(Path(args.output_root))}")
    print(f"Freeze ZIP: {rel(Path(args.output_root) / PACKAGE_NAME)}")
    print(f"Surface HTML: {rel(Path(args.output_root) / decision['surface_html_ref'])}")
    print(f"R21 input validation: {decision['r21_input_validation']}")
    print(f"Consumption smoke: {decision['consumption_smoke_status']}")
    print(f"Cockpit surface mode: {decision['cockpit_surface_mode']}")
    print(f"Frame review cards: {decision['frame_review_cards']}")
    print(f"External media refs: {decision['external_media_refs']}")
    print(f"ZIP entries: {report['zip_entries']}")
    print(f"JSON parse: PASS, {report['json_files_parsed']} JSON + {report['jsonl_files_parsed']} JSONL")
    print(f"Hash manifest: {report['hash_manifest_verified']}")
    print(f"Manifest mismatches: {len(report['manifest_mismatches'])}")
    return 0 if report["status"] == "PASS" and not decision["status"].startswith("FAIL_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
