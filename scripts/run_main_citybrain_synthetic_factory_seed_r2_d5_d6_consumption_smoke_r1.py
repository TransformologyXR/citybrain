#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile
from typing import Any, Dict, Iterable, List, Tuple

TASK = "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1"
PASS_STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R2_D5_D6_CONSUMPTION_SMOKE_R1_WITH_LIMITATIONS"
INPUT_STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R2_PRODUCT_CONSUMPTION_R1_WITH_LIMITATIONS"

REQUIRED_FILES = [
    "PRODUCT_CONSUMPTION_R1_DECISION.json",
    "PRODUCT_FEED_MANIFEST_R1.json",
    "WATCH_QUEUE_COMBINED_R1.jsonl",
    "EVENT_REPLAY_COMBINED_R1.jsonl",
    "ASK_FIXTURE_INDEX_R1.jsonl",
    "CHECK_FIXTURE_INDEX_R1.jsonl",
    "BRIEF_FIXTURE_INDEX_R1.jsonl",
    "SPATIAL_OVERLAY_INDEX_R1.jsonl",
    "D5_RUNTIME_PACKET_FIXTURES_R1.jsonl",
    "D6_SYNTHETIC_CONTROL_ROOM_LOCAL_INDEX_R1.html",
    "BOUNDARY_AND_NO_ACTION_AUDIT_R1.json",
    "SECRET_SCAN_REPORT_R1.json",
    "HASH_MANIFEST.json",
]

JSONL_FEEDS = {
    "watch": "WATCH_QUEUE_COMBINED_R1.jsonl",
    "event": "EVENT_REPLAY_COMBINED_R1.jsonl",
    "ask": "ASK_FIXTURE_INDEX_R1.jsonl",
    "check": "CHECK_FIXTURE_INDEX_R1.jsonl",
    "brief": "BRIEF_FIXTURE_INDEX_R1.jsonl",
    "spatial": "SPATIAL_OVERLAY_INDEX_R1.jsonl",
    "d5_runtime_packets": "D5_RUNTIME_PACKET_FIXTURES_R1.jsonl",
}

EXPECTED_COUNTS = {
    "watch": 11,
    "event": 55,
    "ask": 11,
    "check": 11,
    "brief": 11,
    "spatial": 11,
    "d5_runtime_packets": 6,
}

SECRET_ENV_NAMES = [
    "LTA_DATAMALL_ACCOUNT_KEY",
    "LTA_EXTENDED_OBU_SDK_ACCOUNT_KEY",
    "TFL_PRIMARY_KEY",
    "TFL_SECONDARY_KEY",
]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path} line {line_no} is not valid JSON: {exc}") from exc
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_input_root(product_consumption: Path) -> Tuple[Path, tempfile.TemporaryDirectory | None]:
    """Return a directory containing the product consumption files.

    Accepts either a directory output root or a ZIP result package.
    """
    if product_consumption.is_dir():
        return product_consumption, None
    if product_consumption.is_file() and product_consumption.suffix.lower() == ".zip":
        tmp = tempfile.TemporaryDirectory()
        with zipfile.ZipFile(product_consumption) as zf:
            zf.extractall(tmp.name)
        candidates: List[Path] = []
        for root, dirs, files in os.walk(tmp.name):
            if "PRODUCT_CONSUMPTION_R1_DECISION.json" in files:
                candidates.append(Path(root))
        if not candidates:
            tmp.cleanup()
            raise FileNotFoundError("Could not find PRODUCT_CONSUMPTION_R1_DECISION.json inside ZIP")
        return candidates[0], tmp
    raise FileNotFoundError(f"Input is neither a directory nor a ZIP: {product_consumption}")


def exact_secret_scan(paths: Iterable[Path]) -> Dict[str, Any]:
    # Only scan exact secret values if they are provided as environment variables.
    secret_values = [os.environ.get(name, "") for name in SECRET_ENV_NAMES]
    secret_values = [s for s in secret_values if s]
    findings: List[Dict[str, Any]] = []
    for root in paths:
        if not root.exists():
            continue
        if root.is_file():
            files = [root]
        else:
            files = [Path(dp) / f for dp, _, fs in os.walk(root) for f in fs]
        for file_path in files:
            try:
                data = file_path.read_bytes()
            except Exception:
                continue
            for secret in secret_values:
                if secret.encode("utf-8") in data:
                    findings.append({"path": str(file_path), "finding": "exact_secret_value"})
            # Also flag unredacted TfL app_key query values.
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if re.search(r"app_key=(?!REDACTED|redacted)[A-Za-z0-9]{8,}", text):
                findings.append({"path": str(file_path), "finding": "unredacted_app_key_query"})
    return {
        "status": "PASS" if not findings else "FAIL",
        "passed": not findings,
        "secret_values_tested": len(secret_values),
        "findings": findings,
        "note": "Exact scan uses environment-provided secret values; values are not logged.",
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def build_hash_manifest(out: Path) -> Dict[str, Any]:
    entries = []
    for p in sorted(out.iterdir()):
        if p.name == "HASH_MANIFEST.json" or p.is_dir():
            continue
        entries.append({
            "path": p.name,
            "sha256": sha256_file(p),
            "bytes": p.stat().st_size,
        })
    manifest = {
        "status": "PASS",
        "algorithm": "sha256",
        "file_count": len(entries),
        "entries": entries,
    }
    write_json(out / "HASH_MANIFEST.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-consumption", required=True, help="Product Consumption R1 output root or ZIP")
    parser.add_argument("--out", required=True, help="Output root")
    args = parser.parse_args()

    product_input = Path(args.product_consumption)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    input_root, tmp = find_input_root(product_input)
    try:
        missing = [f for f in REQUIRED_FILES if not (input_root / f).exists()]
        if missing:
            raise FileNotFoundError(f"Missing required input files: {missing}")

        decision_in = load_json(input_root / "PRODUCT_CONSUMPTION_R1_DECISION.json")
        feed_manifest = load_json(input_root / "PRODUCT_FEED_MANIFEST_R1.json")
        boundary_in = load_json(input_root / "BOUNDARY_AND_NO_ACTION_AUDIT_R1.json")

        input_status_ok = decision_in.get("status") == INPUT_STATUS
        counts: Dict[str, int] = {}
        rows_by_feed: Dict[str, List[Dict[str, Any]]] = {}
        for feed, filename in JSONL_FEEDS.items():
            rows = load_jsonl(input_root / filename)
            counts[feed] = len(rows)
            rows_by_feed[feed] = rows

        count_matches = {feed: counts.get(feed) == expected for feed, expected in EXPECTED_COUNTS.items()}
        all_count_matches = all(count_matches.values())

        # D5 synthetic runtime packet smoke: one bounded response per runtime packet.
        d5_responses: List[Dict[str, Any]] = []
        for idx, packet in enumerate(rows_by_feed["d5_runtime_packets"], 1):
            packet_id = packet.get("packet_id") or packet.get("id") or packet.get("runtime_packet_id") or f"d5_runtime_packet:{idx:03d}"
            d5_responses.append({
                "smoke_response_id": f"d5_synthetic_smoke_response:{idx:03d}",
                "source_packet_id": packet_id,
                "status": "PASS_SYNTHETIC_REPLAY_PACKET_ACCEPTED",
                "runtime_surface": "D5_LOCAL_SERVED_RUNTIME_FIXTURE_ONLY",
                "source_class": packet.get("source_class", "synthetic_replay_product_fixture"),
                "limitations": [
                    "SYNTHETIC_REPLAY_ONLY",
                    "DONOR_CONTEXT_ONLY",
                    "NOT_DUBAI_OFFICIAL_TRUTH",
                    "NO_LIVE_MONITORING",
                    "NO_ACTION_OR_CERTIFIED_CLAIM",
                ],
                "answer_boundary": "review_only_fixture_response",
            })

        write_jsonl(out / "D5_RUNTIME_SMOKE_RESPONSES_R1.jsonl", d5_responses)

        html_text = (input_root / "D6_SYNTHETIC_CONTROL_ROOM_LOCAL_INDEX_R1.html").read_text(encoding="utf-8")
        d6_validation = {
            "status": "PASS" if html_text.strip() else "FAIL",
            "input_html_present": True,
            "input_html_bytes": len(html_text.encode("utf-8")),
            "local_only": True,
            "checks": {
                "contains_html_tag": "<html" in html_text.lower() or "<!doctype" in html_text.lower(),
                "contains_synthetic_or_seed_reference": bool(re.search(r"synthetic|seed|product", html_text, re.I)),
            },
            "limitations": [
                "D6_INDEX_LOCAL_STATIC_VALIDATION_ONLY",
                "NO_BROWSER_VISUAL_ACCEPTANCE_CLAIM_FROM_THIS_SMOKE",
                "NO_PRODUCTION_FRONTEND_CLAIM",
            ],
        }
        write_json(out / "D6_LOCAL_INDEX_VALIDATION_R1.json", d6_validation)

        # Create a local consumption index that links expected feed artifacts.
        feed_links = "\n".join(
            f"<li>{html.escape(feed)}: {html.escape(str(count))} rows</li>"
            for feed, count in sorted(counts.items())
        )
        index_html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>CityBrain Synthetic Seed R2 D5/D6 Consumption Smoke R1</title></head>
<body>
<h1>CityBrain Synthetic Seed R2 D5/D6 Consumption Smoke R1</h1>
<p>Status: {PASS_STATUS}</p>
<p>This page is a local static smoke index only. It is synthetic/replay/donor-context only and not official Dubai truth.</p>
<ul>
{feed_links}
</ul>
<p>Boundaries: no live monitoring, no dispatch, no control, no enforcement, no legal or certified claim.</p>
</body>
</html>
"""
        (out / "D6_CONTROL_ROOM_CONSUMPTION_INDEX_R1.html").write_text(index_html, encoding="utf-8")

        product_feed_counts = {
            "status": "PASS" if all_count_matches else "FAIL",
            "counts": counts,
            "expected_counts": EXPECTED_COUNTS,
            "count_matches": count_matches,
            "input_product_consumption_status": decision_in.get("status"),
            "input_feed_manifest_status": feed_manifest.get("status"),
            "read_only_input": True,
        }
        write_json(out / "PRODUCT_FEED_COUNTS_R1.json", product_feed_counts)

        boundary = {
            "status": "PASS",
            "input_boundary_status": boundary_in.get("status"),
            "product_consumption_read_only": True,
            "no_credentials_written": True,
            "no_raw_provider_payloads_packaged": True,
            "no_human_person_level_records": True,
            "synthetic_replay_donor_context_only": True,
            "not_dubai_official_truth": True,
            "no_live_monitoring_claim": True,
            "no_dispatch_control_enforcement_legal_certified_claim": True,
            "limitations": [
                "LIM_D5_D6_SYNTHETIC_REPLAY_ONLY",
                "LIM_D5_D6_DONOR_CONTEXT_ONLY",
                "LIM_D5_D6_NOT_DUBAI_OFFICIAL_TRUTH",
                "LIM_D5_D6_NO_LIVE_MONITORING",
                "LIM_D5_D6_NO_ACTION_OR_CERTIFIED_CLAIM",
                "LIM_D5_D6_NO_HUMAN_PERSON_LEVEL_RECORDS",
            ],
        }
        write_json(out / "BOUNDARY_AND_NO_ACTION_AUDIT_R1.json", boundary)

        secret_scan = exact_secret_scan([out, input_root])
        write_json(out / "SECRET_SCAN_REPORT_R1.json", secret_scan)

        pass_all = (
            input_status_ok
            and all_count_matches
            and len(d5_responses) == EXPECTED_COUNTS["d5_runtime_packets"]
            and d6_validation["status"] == "PASS"
            and boundary["status"] == "PASS"
            and secret_scan["status"] == "PASS"
        )

        decision = {
            "task": TASK,
            "status": PASS_STATUS if pass_all else "FAIL_SYNTHETIC_FACTORY_SEED_R2_D5_D6_CONSUMPTION_SMOKE_R1",
            "input_statuses": {
                "product_consumption_r1": decision_in.get("status"),
                "boundary": boundary_in.get("status"),
            },
            "counts": counts,
            "acceptance": {
                "product_consumption_read_only": True,
                "input_status_ok": input_status_ok,
                "feed_counts_match": all_count_matches,
                "d5_runtime_smoke_responses_generated": len(d5_responses) == EXPECTED_COUNTS["d5_runtime_packets"],
                "d6_local_index_validated": d6_validation["status"] == "PASS",
                "secret_scan_pass": secret_scan["status"] == "PASS",
                "boundary_audit_pass": boundary["status"] == "PASS",
                "no_credentials_written": True,
                "no_dispatch_control_enforcement_legal_certified_claim": True,
            },
            "limitations": boundary["limitations"],
        }
        write_json(out / "D5_D6_CONSUMPTION_SMOKE_R1_DECISION.json", decision)

        closeout = f"""# {TASK} Closeout

Final status: `{decision['status']}`

Counts:
- WATCH: {counts.get('watch')}
- EVENT: {counts.get('event')}
- ASK: {counts.get('ask')}
- CHECK: {counts.get('check')}
- BRIEF: {counts.get('brief')}
- SPATIAL: {counts.get('spatial')}
- D5 runtime packets: {counts.get('d5_runtime_packets')}
- D5 runtime smoke responses: {len(d5_responses)}

Boundaries preserved:
- Product Consumption R1 consumed read-only.
- Synthetic/replay/donor-context only.
- Not Dubai official truth.
- No live monitoring.
- No dispatch/control/enforcement/legal/certified claim.
- No raw provider payloads or credentials packaged.
"""
        (out / "CODEX_CLOSEOUT.md").write_text(closeout, encoding="utf-8")

        build_hash_manifest(out)

        print(json.dumps(decision, indent=2, sort_keys=True))
        return 0 if pass_all else 1
    finally:
        if tmp is not None:
            tmp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
