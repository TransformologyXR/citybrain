from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


TASK_NAME = "A5-D7B 4070 briefing bridge"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8093
DEFAULT_SPARK_BASE_URL = os.environ.get("CITYBRAIN_SPARK_BRIEFING_URL", "http://192.168.1.103:8095")
DEFAULT_PRECOMPUTED_DIR = Path(
    os.environ.get("CITYBRAIN_A5D7_PRECOMPUTED_DIR", "/data/citybrain/from_spark/a5d7_citywide_briefings_v1")
)
HERO_BLOCK_KEY = "1-01060"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_block_key(value: str) -> str:
    value = str(value or "").strip()
    if not re.fullmatch(r"[1-5]-\d{5}", value):
        raise ValueError("block must use active citywide block_key format like 1-01060")
    return value


def send_http_json(url: str, timeout: int = 120) -> tuple[int, dict[str, Any]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except ValueError:
            payload = {"status": "FAIL", "error": body}
        return int(exc.code), payload


def index_entry(block_key: str, precomputed_dir: Path) -> dict[str, Any] | None:
    index_path = precomputed_dir / "block_index.json"
    if not index_path.exists():
        return None
    index = read_json(index_path)
    entry = index.get(block_key)
    return entry if isinstance(entry, dict) else None


def precomputed_paths(block_key: str, precomputed_dir: Path) -> dict[str, Path] | None:
    entry = index_entry(block_key, precomputed_dir)
    if entry:
        return {
            "evidence": precomputed_dir / str(entry.get("evidence", "")),
            "briefing": precomputed_dir / str(entry.get("briefing", "")),
            "trace": precomputed_dir / str(entry.get("trace", "")),
        }
    fallback = {
        "evidence": precomputed_dir / "evidence_json" / f"block_{block_key}_evidence.json",
        "briefing": precomputed_dir / "briefings" / f"block_{block_key}_briefing.md",
        "trace": precomputed_dir / "traces" / f"block_{block_key}_trace.json",
    }
    if fallback["evidence"].exists() or fallback["briefing"].exists():
        return fallback
    return None


def load_precomputed(block_key: str, precomputed_dir: Path) -> dict[str, Any]:
    try:
        block_key = clean_block_key(block_key)
    except ValueError as exc:
        return {
            "status": "FAIL",
            "http_status": 404,
            "error": str(exc),
            "block_key": str(block_key),
            "rejected_before_deterministic_execution": True,
            "deterministic_executed": False,
        }
    paths = precomputed_paths(block_key, precomputed_dir)
    if not paths or not paths["evidence"].exists() or not paths["briefing"].exists():
        return {
            "status": "FAIL",
            "http_status": 404,
            "error": "precomputed A5D7 briefing/evidence not found for block",
            "block_key": block_key,
            "precomputed_dir": str(precomputed_dir),
            "rejected_before_deterministic_execution": True,
            "deterministic_executed": False,
        }
    evidence = read_json(paths["evidence"])
    briefing = paths["briefing"].read_text(encoding="utf-8")
    trace = read_json(paths["trace"]) if paths["trace"].exists() else evidence.get("trace")
    subject = evidence.get("subject") or {}
    metrics = evidence.get("metrics") or {}
    payload = {
        "task": TASK_NAME,
        "status": "PASS",
        "http_status": 200,
        "mode": "precomputed",
        "block_key": block_key,
        "subject_id": subject.get("subject_id") or f"block:us-nyc:tax_block:{block_key}",
        "subject_label": "hero_block" if block_key == HERO_BLOCK_KEY else "citywide_block",
        "source": "a5d7_task2a_static_briefing",
        "source_paths": {key: str(path) for key, path in paths.items() if path.exists()},
        "deterministic_answer": {
            "counts": {
                "node_count": metrics.get("node_count"),
                "edge_count": metrics.get("edge_count"),
                "complaint_count": metrics.get("complaint_count"),
                "critical_complaint_count": metrics.get("critical_complaint_count"),
                "permit_count": metrics.get("permit_count"),
                "source_rows": {
                    "dob_now_filings": metrics.get("dob_now_filing_count"),
                    "dob_permit_issuance": metrics.get("dob_permit_issuance_count"),
                },
            },
            "top_contractors": (evidence.get("top_contractors") or [])[:3],
            "geometry": {
                "bbox": subject.get("bbox"),
                "centroid": subject.get("representative_point"),
                "geometry_label": (evidence.get("governance") or {}).get("geometry_caveat"),
            },
            "evidence_bundle_hash": evidence.get("normalized_hash"),
        },
        "evidence_bundle": evidence,
        "trace": trace,
        "narration": briefing,
        "grounding_result": {
            "status": index_entry(block_key, precomputed_dir).get("grounding_status", "PASS")
            if index_entry(block_key, precomputed_dir)
            else "PASS"
        },
        "generated_at": utc_now(),
    }
    payload["output_hash"] = sha256_payload(payload)
    return payload


def proxy_live(block_key: str, spark_base_url: str) -> tuple[int, dict[str, Any]]:
    query = urllib.parse.urlencode({"block": block_key, "mode": "live"})
    url = f"{spark_base_url.rstrip('/')}/briefing?{query}"
    status, payload = send_http_json(url, timeout=180)
    payload["origin_chain"] = ["4070:/api/briefing", "spark:/briefing", "spark:NIM"]
    payload["spark_url"] = url
    return status, payload


class BriefingHandler(BaseHTTPRequestHandler):
    precomputed_dir: Path = DEFAULT_PRECOMPUTED_DIR
    spark_base_url: str = DEFAULT_SPARK_BASE_URL

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path in {"/health", "/api/briefing/health"}:
                status, spark_health = send_http_json(f"{self.spark_base_url.rstrip('/')}/health", timeout=30)
                payload = {
                    "task": TASK_NAME,
                    "status": "PASS" if status == 200 and self.precomputed_dir.exists() else "FAIL",
                    "generated_at": utc_now(),
                    "precomputed_dir": str(self.precomputed_dir),
                    "precomputed_dir_exists": self.precomputed_dir.exists(),
                    "block_index_exists": (self.precomputed_dir / "block_index.json").exists(),
                    "spark_base_url": self.spark_base_url,
                    "spark_health_http_status": status,
                    "spark_health": spark_health,
                }
                self.send_json(200 if payload["status"] == "PASS" else 503, payload)
                return
            if parsed.path in {"/api/briefing", "/briefing"}:
                block_key = params.get("block", params.get("block_key", [""]))[0]
                mode = params.get("mode", ["precomputed"])[0] or "precomputed"
                if mode not in {"precomputed", "live"}:
                    self.send_json(400, {"status": "FAIL", "error": "mode must be precomputed or live"})
                    return
                if mode == "live":
                    status, payload = proxy_live(block_key, self.spark_base_url)
                else:
                    payload = load_precomputed(block_key, self.precomputed_dir)
                    status = int(payload.get("http_status") or 500)
                self.send_json(status, payload)
                return
            self.send_json(404, {"status": "FAIL", "error": "not found"})
        except Exception as exc:  # explicit for harnesses
            self.send_json(500, {"status": "FAIL", "error": str(exc), "path": parsed.path})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


def serve(args: argparse.Namespace) -> int:
    BriefingHandler.precomputed_dir = Path(args.precomputed_dir)
    BriefingHandler.spark_base_url = args.spark_base_url
    server = ThreadingHTTPServer((args.host, args.port), BriefingHandler)
    print(f"{TASK_NAME} listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--precomputed-dir", default=str(DEFAULT_PRECOMPUTED_DIR))
    parser.add_argument("--spark-base-url", default=DEFAULT_SPARK_BASE_URL)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--block")
    parser.add_argument("--mode", choices=["precomputed", "live"], default="precomputed")
    args = parser.parse_args()
    if args.serve:
        return serve(args)
    if args.block:
        if args.mode == "live":
            status, payload = proxy_live(args.block, args.spark_base_url)
        else:
            payload = load_precomputed(args.block, Path(args.precomputed_dir))
            status = int(payload.get("http_status") or 500)
        print(pretty_json(payload))
        return 0 if status == 200 and payload.get("status") == "PASS" else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
