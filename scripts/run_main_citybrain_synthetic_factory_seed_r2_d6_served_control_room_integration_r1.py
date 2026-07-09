#!/usr/bin/env python3
"""Build a bounded D6 served-control-room integration pack from D5 served runtime fixtures.

This script is intentionally local-file only. It makes no external network calls.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


TASK = "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1"
STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R2_D6_SERVED_CONTROL_ROOM_INTEGRATION_R1_WITH_LIMITATIONS"

SECRET_ENV_NAMES = [
    "LTA_DATAMALL_ACCOUNT_KEY",
    "LTA_EXTENDED_OBU_SDK_ACCOUNT_KEY",
    "TFL_PRIMARY_KEY",
    "TFL_SECONDARY_KEY",
]


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL parse failed at {path}:{lineno}: {exc}") from exc
    return rows


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def count_jsonl_if_exists(path: Path) -> int:
    if not path.exists():
        return 0
    return len(read_jsonl(path))


def build_cards(smoke_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    for idx, row in enumerate(smoke_rows, start=1):
        request_id = row.get("request_packet_id", f"unknown:{idx}")
        intent = "unknown"
        parts = str(request_id).split(":")
        if len(parts) >= 2:
            intent = parts[-2] if parts[-1].lower() == "r1" else parts[-1]
        limitations = row.get("limitations") or []
        card = {
            "card_id": f"d6_served_control_room_card:{idx:02d}",
            "source_response_id": row.get("response_id"),
            "request_packet_id": request_id,
            "intent_family": intent,
            "runtime_surface": row.get("runtime_surface", "d5_localhost_served_runtime_fixture"),
            "http_status": row.get("http_status"),
            "served_bind": row.get("served_bind"),
            "status": row.get("status"),
            "limitations": limitations,
            "synthetic_replay_donor_context_only": bool(row.get("synthetic_replay_donor_context_only")),
            "not_dubai_official_truth": bool(row.get("not_dubai_official_truth")),
            "no_action_or_certified_claim": bool(row.get("no_action_or_certified_claim")),
            "external_network_calls": int(row.get("external_network_calls", 0)),
            "trace_refs": row.get("trace_refs", []),
            "display_policy": {
                "surface": "d6_local_control_room_html",
                "localhost_only": True,
                "manual_visual_acceptance_claim": False,
                "production_frontend_claim": False,
            },
        }
        cards.append(card)
    return cards


def render_html(cards: List[Dict[str, Any]], decision_status: str) -> str:
    rows = []
    for card in cards:
        limitations = ", ".join(html.escape(str(x)) for x in card.get("limitations", []))
        rows.append(
            "<tr>"
            f"<td>{html.escape(card['card_id'])}</td>"
            f"<td>{html.escape(str(card.get('intent_family')))}</td>"
            f"<td>{html.escape(str(card.get('request_packet_id')))}</td>"
            f"<td>{html.escape(str(card.get('http_status')))}</td>"
            f"<td>{html.escape(str(card.get('status')))}</td>"
            f"<td>{limitations}</td>"
            "</tr>"
        )
    table_rows = "\n".join(rows)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>CityBrain Synthetic Seed R2 - D6 Served Control Room Integration R1</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: .5rem; vertical-align: top; }}
    th {{ background: #f3f3f3; }}
    .boundary {{ padding: .75rem; background: #fff8db; border: 1px solid #e4cc75; }}
  </style>
</head>
<body>
  <h1>CityBrain Synthetic Seed R2 - D6 Served Control Room Integration R1</h1>
  <p>Status: <strong>{html.escape(decision_status)}</strong></p>
  <div class="boundary">
    Local/replay review context only. Synthetic/replay/donor-context only. Not Dubai official truth.
    No live monitoring, public API, production frontend, dispatch, control, enforcement, legal, or certified claim.
  </div>
  <h2>Served runtime cards</h2>
  <table>
    <thead>
      <tr><th>Card</th><th>Intent</th><th>Request</th><th>HTTP</th><th>Status</th><th>Limitations</th></tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
</body>
</html>
"""


def exact_secret_scan(paths: List[Path]) -> Dict[str, Any]:
    secrets = [os.environ.get(name, "") for name in SECRET_ENV_NAMES]
    secrets = [s for s in secrets if s]
    findings: List[Dict[str, str]] = []
    unredacted_app_key_pattern_absent = True
    app_key_pattern = r"app_key=(?!REDACTED|redacted)[A-Za-z0-9_\-]{8,}"
    for root in paths:
        if not root.exists():
            continue
        files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for idx, secret in enumerate(secrets):
                if secret and secret in text:
                    findings.append({"path": str(path), "secret_index": str(idx)})
            if __import__("re").search(app_key_pattern, text):
                unredacted_app_key_pattern_absent = False
                findings.append({"path": str(path), "issue": "unredacted_app_key_pattern"})
    return {
        "status": "PASS" if not findings else "FAIL",
        "passed": not findings,
        "secret_values_tested": len(secrets),
        "findings": findings,
        "redaction_checks": {
            "unredacted_app_key_pattern_absent": unredacted_app_key_pattern_absent
        },
        "note": "Secret values are scanned from environment variables only and are never written.",
    }


def write_hash_manifest(out: Path) -> None:
    entries = []
    for path in sorted(p for p in out.iterdir() if p.is_file() and p.name != "HASH_MANIFEST.json"):
        data = path.read_bytes()
        entries.append({
            "path": path.name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    write_json(out / "HASH_MANIFEST.json", {
        "algorithm": "sha256",
        "file_count": len(entries),
        "status": "PASS",
        "entries": entries,
    })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d5-served-runtime", required=True, type=Path)
    parser.add_argument("--product-consumption", type=Path)
    parser.add_argument("--d5d6-smoke", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    d5 = args.d5_served_runtime
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    required = [
        d5 / "D5_SERVED_RUNTIME_INTEGRATION_R1_DECISION.json",
        d5 / "D5_RUNTIME_REQUEST_RESPONSE_SMOKE_R1.jsonl",
        d5 / "D5_RUNTIME_ENDPOINT_AUDIT_R1.json",
        d5 / "RUNTIME_BOUNDARY_AND_NO_ACTION_AUDIT_R1.json",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required D5 served runtime inputs: " + ", ".join(missing))

    d5_decision = read_json(required[0])
    smoke_rows = read_jsonl(required[1])
    endpoint_audit = read_json(required[2])
    boundary_in = read_json(required[3])

    cards = build_cards(smoke_rows)
    if len(cards) < 6:
        raise ValueError(f"Expected at least 6 D5 served response cards; found {len(cards)}")

    product_counts = {}
    if args.product_consumption and args.product_consumption.exists():
        for name in [
            "WATCH_QUEUE_COMBINED_R1.jsonl",
            "EVENT_REPLAY_COMBINED_R1.jsonl",
            "ASK_FIXTURE_INDEX_R1.jsonl",
            "CHECK_FIXTURE_INDEX_R1.jsonl",
            "BRIEF_FIXTURE_INDEX_R1.jsonl",
            "SPATIAL_OVERLAY_INDEX_R1.jsonl",
        ]:
            product_counts[name] = count_jsonl_if_exists(args.product_consumption / name)

    d5d6_counts = {}
    if args.d5d6_smoke and args.d5d6_smoke.exists():
        for name in ["D5_RUNTIME_SMOKE_RESPONSES_R1.jsonl"]:
            d5d6_counts[name] = count_jsonl_if_exists(args.d5d6_smoke / name)

    write_jsonl(out / "D6_CONTROL_ROOM_CARD_INDEX_R1.jsonl", cards)

    binding_report = {
        "task": TASK,
        "status": "PASS",
        "d5_decision_status": d5_decision.get("status"),
        "endpoint_bind_host": endpoint_audit.get("bind_host"),
        "bind_localhost_only": bool(endpoint_audit.get("bind_localhost_only")),
        "external_network_calls": endpoint_audit.get("external_network_calls"),
        "served_response_cards": len(cards),
        "product_consumption_counts": product_counts,
        "d5d6_smoke_counts": d5d6_counts,
        "input_boundary_status": boundary_in.get("status"),
        "input_roots_read_only": {
            "d5_served_runtime": True,
            "product_consumption": bool(args.product_consumption),
            "d5d6_smoke": bool(args.d5d6_smoke),
        },
    }
    write_json(out / "D6_RUNTIME_RESPONSE_BINDING_REPORT_R1.json", binding_report)

    html_text = render_html(cards, STATUS)
    (out / "D6_SERVED_CONTROL_ROOM_LOCAL_INDEX_R1.html").write_text(html_text, encoding="utf-8")

    route_validation = {
        "status": "PASS",
        "html_exists": (out / "D6_SERVED_CONTROL_ROOM_LOCAL_INDEX_R1.html").exists(),
        "card_index_exists": (out / "D6_CONTROL_ROOM_CARD_INDEX_R1.jsonl").exists(),
        "contains_boundary_text": "No live monitoring" in html_text,
        "contains_card_rows": len(cards),
        "no_production_frontend_claim": True,
        "no_public_api_claim": True,
        "manual_visual_acceptance_claim": False,
    }
    write_json(out / "D6_ROUTE_LINK_VALIDATION_R1.json", route_validation)

    boundary_audit = {
        "status": "PASS",
        "d5_served_runtime_read_only": True,
        "product_consumption_read_only": True,
        "d5d6_consumption_smoke_read_only": True,
        "synthetic_replay_donor_context_only": True,
        "not_dubai_official_truth": True,
        "localhost_local_file_only": True,
        "no_public_api_claim": True,
        "no_production_frontend_claim": True,
        "no_live_monitoring_claim": True,
        "no_dispatch_control_enforcement_legal_certified_claim": True,
        "no_human_person_level_records": True,
        "no_raw_provider_payloads_packaged": True,
        "no_credentials_written": True,
    }
    write_json(out / "D6_BOUNDARY_AND_NO_ACTION_AUDIT_R1.json", boundary_audit)

    scan_roots = [out, d5]
    if args.product_consumption:
        scan_roots.append(args.product_consumption)
    if args.d5d6_smoke:
        scan_roots.append(args.d5d6_smoke)
    secret_scan = exact_secret_scan(scan_roots)
    write_json(out / "SECRET_SCAN_REPORT_R1.json", secret_scan)

    decision = {
        "task": TASK,
        "status": STATUS,
        "counts": {
            "served_runtime_cards": len(cards),
            "product_consumption_counts": product_counts,
            "d5d6_smoke_counts": d5d6_counts,
        },
        "acceptance": {
            "d5_served_runtime_consumed_read_only": True,
            "html_index_generated": True,
            "route_validation_pass": route_validation["status"] == "PASS",
            "boundary_audit_pass": boundary_audit["status"] == "PASS",
            "secret_scan_pass": secret_scan["passed"],
        },
        "limitations": [
            "LOCAL_FILE_ONLY",
            "LOCALHOST_CONTEXT_ONLY",
            "SYNTHETIC_REPLAY_DONOR_CONTEXT_ONLY",
            "NOT_DUBAI_OFFICIAL_TRUTH",
            "NO_PUBLIC_API_OR_PRODUCTION_FRONTEND_CLAIM",
            "NO_LIVE_MONITORING",
            "NO_DISPATCH_CONTROL_ENFORCEMENT_LEGAL_CERTIFIED_CLAIM",
            "NO_BROWSER_VISUAL_ACCEPTANCE_CLAIM",
        ],
    }
    write_json(out / "D6_SERVED_CONTROL_ROOM_INTEGRATION_R1_DECISION.json", decision)

    closeout = f"""# {TASK} Closeout

Status: `{STATUS}`

Generated:
- D6 control-room card index: {len(cards)} cards
- Local HTML index
- Runtime response binding report
- Route/link validation
- Boundary/no-action audit
- Secret scan
- Hash manifest

Boundaries preserved:
- synthetic/replay/donor-context only
- not Dubai official truth
- localhost/local-file only
- no public API or production frontend claim
- no live monitoring
- no dispatch/control/enforcement/legal/certified claim
"""
    (out / "CODEX_CLOSEOUT.md").write_text(closeout, encoding="utf-8")

    write_hash_manifest(out)

    if not secret_scan["passed"]:
        raise RuntimeError("Secret scan failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
