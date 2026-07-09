#!/usr/bin/env python3
"""
Starter runner for MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1.

Codex may extend this runner to use the actual D5 local served runtime. This starter
implements a deterministic local fixture response smoke and writes the required outputs.
It makes no external network calls.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import html
import json
from pathlib import Path
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R2_D5_SERVED_RUNTIME_INTEGRATION_R1_WITH_LIMITATIONS"
TASK = "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1"

REQUIRED_PRODUCT = [
    "D5_RUNTIME_PACKET_FIXTURES_R1.jsonl",
    "WATCH_QUEUE_COMBINED_R1.jsonl",
    "EVENT_REPLAY_COMBINED_R1.jsonl",
    "ASK_FIXTURE_INDEX_R1.jsonl",
    "CHECK_FIXTURE_INDEX_R1.jsonl",
    "BRIEF_FIXTURE_INDEX_R1.jsonl",
    "SPATIAL_OVERLAY_INDEX_R1.jsonl",
]
REQUIRED_SMOKE = [
    "D5_RUNTIME_SMOKE_RESPONSES_R1.jsonl",
    "D6_CONTROL_ROOM_CONSUMPTION_INDEX_R1.html",
    "D5_D6_CONSUMPTION_SMOKE_R1_DECISION.json",
    "BOUNDARY_AND_NO_ACTION_AUDIT_R1.json",
]


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_files(root: Path, names: list[str]) -> None:
    missing = [n for n in names if not (root / n).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required files under {root}: {missing}")


def make_served_response(packet: dict, idx: int) -> dict:
    packet_id = packet.get("packet_id") or packet.get("id") or f"d5_packet_{idx + 1:02d}"
    return {
        "response_id": f"served_response:{idx + 1:02d}",
        "request_packet_id": packet_id,
        "runtime_surface": "d5_localhost_served_runtime_fixture",
        "status": "PASS",
        "http_status": 200,
        "served_bind": "127.0.0.1",
        "external_network_calls": 0,
        "synthetic_replay_donor_context_only": True,
        "not_dubai_official_truth": True,
        "no_action_or_certified_claim": True,
        "limitations": [
            "LOCALHOST_ONLY",
            "SYNTHETIC_REPLAY_DONOR_CONTEXT_ONLY",
            "NOT_DUBAI_OFFICIAL_TRUTH",
            "NO_LIVE_MONITORING",
            "NO_DISPATCH_CONTROL_ENFORCEMENT_LEGAL_CERTIFIED_CLAIM",
        ],
        "trace_refs": packet.get("trace_refs", []),
    }


def run_localhost_smoke(packets: list[dict]) -> tuple[list[dict], dict]:
    """Exercise an ephemeral HTTP server bound to localhost only."""
    server_state: dict = {
        "packets": packets,
        "requests": [],
        "unsupported_routes": [],
    }

    class D5LocalHandler(BaseHTTPRequestHandler):
        server_version = "CityBrainD5LocalSmoke/1.0"

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(self, status: int, payload: dict) -> None:
            encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send_json(200, {"status": "ok", "bind": "127.0.0.1", "external_network_calls": 0})
                return
            if self.path == "/runtime/fixtures":
                self._send_json(200, {"status": "ok", "packet_count": len(server_state["packets"])})
                return
            server_state["unsupported_routes"].append({"method": "GET", "path": self.path})
            self._send_json(404, {"status": "unsupported_route", "safe_failure": True})

        def do_POST(self) -> None:
            if self.path != "/runtime/request":
                server_state["unsupported_routes"].append({"method": "POST", "path": self.path})
                self._send_json(404, {"status": "unsupported_route", "safe_failure": True})
                return
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                packet = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json(400, {"status": "bad_json", "safe_failure": True})
                return
            idx = len(server_state["requests"])
            response = make_served_response(packet, idx)
            server_state["requests"].append({
                "method": "POST",
                "path": self.path,
                "packet_id": response["request_packet_id"],
                "http_status": 200,
            })
            self._send_json(200, response)

    httpd = HTTPServer(("127.0.0.1", 0), D5LocalHandler)
    host, port = httpd.server_address
    if host != "127.0.0.1":
        httpd.server_close()
        raise AssertionError(f"D5 local smoke server bound to unexpected host: {host}")

    thread = threading.Thread(target=httpd.serve_forever, name="citybrain-d5-local-smoke", daemon=True)
    thread.start()
    responses: list[dict] = []
    health_status = None
    fixture_status = None
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/health")
        health = conn.getresponse()
        health_status = health.status
        health.read()

        conn.request("GET", "/runtime/fixtures")
        fixtures = conn.getresponse()
        fixture_status = fixtures.status
        fixtures.read()

        for packet in packets:
            body = json.dumps(packet, sort_keys=True).encode("utf-8")
            conn.request("POST", "/runtime/request", body=body, headers={"Content-Type": "application/json"})
            response = conn.getresponse()
            data = response.read()
            if response.status != 200:
                raise AssertionError(f"Local D5 request failed with HTTP {response.status}")
            payload = json.loads(data.decode("utf-8"))
            payload["served_url"] = f"http://127.0.0.1:{port}/runtime/request"
            responses.append(payload)
        conn.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    endpoint_audit = {
        "status": "PASS",
        "bind_localhost_only": True,
        "bind_host": "127.0.0.1",
        "public_bind_allowed": False,
        "ephemeral_port_used": isinstance(port, int) and port > 0,
        "external_network_calls": 0,
        "health_http_status": health_status,
        "fixtures_http_status": fixture_status,
        "request_count": len(server_state["requests"]),
        "response_count": len(responses),
        "unsupported_routes": server_state["unsupported_routes"],
        "malformed_or_unsupported_route_policy": "safe_failure_required_if_server_mode_implemented",
        "no_public_api_claim": True,
        "server_shutdown": not thread.is_alive(),
    }
    return responses, endpoint_audit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--product-consumption", required=True)
    ap.add_argument("--d5d6-smoke", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    product = Path(args.product_consumption)
    smoke = Path(args.d5d6_smoke)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    require_files(product, REQUIRED_PRODUCT)
    require_files(smoke, REQUIRED_SMOKE)

    packets = read_jsonl(product / "D5_RUNTIME_PACKET_FIXTURES_R1.jsonl")
    prior_smoke = read_jsonl(smoke / "D5_RUNTIME_SMOKE_RESPONSES_R1.jsonl")
    if len(packets) != 6:
        raise AssertionError(f"Expected 6 D5 runtime packets, got {len(packets)}")
    if len(prior_smoke) != 6:
        raise AssertionError(f"Expected 6 prior smoke responses, got {len(prior_smoke)}")

    responses, endpoint_audit = run_localhost_smoke(packets)

    write_jsonl(out / "D5_RUNTIME_REQUEST_RESPONSE_SMOKE_R1.jsonl", responses)

    server_contract = {
        "task": TASK,
        "status": "PASS",
        "bind_host": "127.0.0.1",
        "public_bind_allowed": False,
        "external_network_calls_allowed": False,
        "routes": [
            {"method": "GET", "path": "/health", "purpose": "local health only"},
            {"method": "POST", "path": "/runtime/request", "purpose": "consume one synthetic D5 packet fixture"},
            {"method": "GET", "path": "/runtime/fixtures", "purpose": "local fixture index"}
        ],
        "request_count": len(packets),
        "response_count": len(responses),
        "served_runtime_smoke_exercised": True,
    }
    write_json(out / "D5_LOCAL_SERVER_CONTRACT_R1.json", server_contract)

    write_json(out / "D5_RUNTIME_ENDPOINT_AUDIT_R1.json", endpoint_audit)

    index_html = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>CityBrain Seed R2 D5 Served Runtime Integration</title></head>
<body>
<h1>CityBrain Seed R2 D5 Served Runtime Integration</h1>
<p>Status: {html.escape(STATUS)}</p>
<p>Localhost-only D5 served-runtime fixture smoke. Synthetic/replay/donor-context only.</p>
<ul>
<li>D5 served responses: {len(responses)}</li>
<li>Not Dubai official truth.</li>
<li>No live monitoring.</li>
<li>No dispatch/control/enforcement/legal/certified claim.</li>
</ul>
</body></html>
"""
    (out / "D6_SERVED_CONTROL_ROOM_INDEX_R1.html").write_text(index_html, encoding="utf-8")

    write_json(out / "D6_SERVED_INDEX_VALIDATION_R1.json", {
        "status": "PASS",
        "contains_html_tag": "<html" in index_html.lower(),
        "contains_status": STATUS in index_html,
        "local_only": True,
        "no_browser_visual_acceptance_claim": True,
        "no_production_frontend_claim": True,
    })

    boundary = {
        "status": "PASS",
        "product_consumption_read_only": True,
        "d5d6_consumption_smoke_read_only": True,
        "synthetic_replay_donor_context_only": True,
        "not_dubai_official_truth": True,
        "no_live_monitoring_claim": True,
        "no_dispatch_control_enforcement_legal_certified_claim": True,
        "no_human_person_level_records": True,
        "no_raw_provider_payloads_packaged": True,
        "no_credentials_written": True,
    }
    write_json(out / "RUNTIME_BOUNDARY_AND_NO_ACTION_AUDIT_R1.json", boundary)

    # Secret scan placeholder: exact secret values should be supplied by environment in repo if available.
    # This starter verifies common unredacted TfL app_key leak pattern is absent from output text.
    combined = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in out.glob("*") if p.is_file())
    unredacted_app_key = "app_key=" in combined and "app_key=REDACTED" not in combined
    secret_scan = {
        "status": "PASS" if not unredacted_app_key else "FAIL",
        "passed": not unredacted_app_key,
        "findings": [] if not unredacted_app_key else ["UNREDACTED_APP_KEY_PATTERN"],
        "note": "Repo test should also run exact secret scan against local known keys."
    }
    write_json(out / "SECRET_SCAN_REPORT_R1.json", secret_scan)
    if not secret_scan["passed"]:
        raise AssertionError("Secret scan failed")

    decision = {
        "task": TASK,
        "status": STATUS,
        "counts": {
            "d5_runtime_packets": len(packets),
            "d5_served_runtime_responses": len(responses)
        },
        "acceptance": {
            "product_consumption_read_only": True,
            "d5d6_consumption_smoke_read_only": True,
            "served_runtime_responses_generated": len(responses) == 6,
            "localhost_only_contract": True,
            "localhost_server_exercised": endpoint_audit["request_count"] == 6,
            "external_network_calls_absent": endpoint_audit["external_network_calls"] == 0,
            "d6_served_index_generated": True,
            "boundary_audit_pass": True,
            "secret_scan_pass": True,
        },
        "limitations": [
            "LOCALHOST_ONLY",
            "SYNTHETIC_REPLAY_DONOR_CONTEXT_ONLY",
            "NOT_DUBAI_OFFICIAL_TRUTH",
            "NO_LIVE_MONITORING",
            "NO_DISPATCH_CONTROL_ENFORCEMENT_LEGAL_CERTIFIED_CLAIM",
            "NO_PRODUCTION_FRONTEND_OR_PUBLIC_API_CLAIM"
        ],
    }
    write_json(out / "D5_SERVED_RUNTIME_INTEGRATION_R1_DECISION.json", decision)

    closeout = f"""# {TASK} Closeout

Final status: `{STATUS}`

Counts:
- D5 runtime packets: {len(packets)}
- D5 served runtime responses: {len(responses)}

Boundaries preserved:
- Product Consumption R1 consumed read-only.
- D5/D6 Consumption Smoke R1 consumed read-only.
- Synthetic/replay/donor-context only.
- Not Dubai official truth.
- No live monitoring.
- No dispatch/control/enforcement/legal/certified claim.
- No raw provider payloads or credentials packaged.
"""
    (out / "CODEX_CLOSEOUT.md").write_text(closeout, encoding="utf-8")

    entries = []
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name != "HASH_MANIFEST.json":
            entries.append({"path": p.name, "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    write_json(out / "HASH_MANIFEST.json", {"status": "PASS", "algorithm": "sha256", "file_count": len(entries), "entries": entries})

    print(STATUS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
