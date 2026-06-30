from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "A5-D7B live citywide query harness"
HERO_BLOCK_KEY = "1-01060"
LOCAL_OUTPUT_DIR = Path("outputs/a5d7b_live_citywide_query_v1")
LOCAL_A5D7_DIR = Path("outputs/a5d7_citywide_briefings_v1")
LOCAL_A4D3B_DIR = Path("outputs/a4d3b_citywide_roundtrip_borough5")
SPARK_HOST = os.environ.get("CITYBRAIN_SPARK_HOST", "spark")
FACE_HOST = os.environ.get("CITYBRAIN_FACE_HOST", "txr-4070")
SPARK_ROOT = "/home/txr/works/citybrain-a5d7b-live-citywide-query"
FACE_ROOT = "/data/citybrain/from_spark"
FACE_API_ROOT = "/data/citybrain/from_spark/a5d7b_live_citywide_query"
SPARK_URL = os.environ.get("CITYBRAIN_SPARK_URL", "http://192.168.1.103:8095")
FACE_URL = os.environ.get("CITYBRAIN_FACE_URL", "http://192.168.1.48:8080")
FACE_API_BASE_URL = os.environ.get("CITYBRAIN_FACE_API_BASE_URL", "http://192.168.1.48:8093")
FACE_API_URL = f"{FACE_API_BASE_URL.rstrip('/')}/api/briefing"
SPARK_PYTHON = "/home/txr/works/nemo-agent-toolkit/.venv/bin/python"
SPARK_WRAPPER = "txr_citybrain_a5d7b_spark_live_citywide_query.py"
FACE_API = "txr_citybrain_a5d7b_4070_briefing_api.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(value) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(cmd: list[str], *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    if check and completed.returncode != 0:
        raise RuntimeError(
            "command failed\n"
            f"cmd: {' '.join(cmd)}\n"
            f"returncode: {completed.returncode}\n"
            f"stdout: {completed.stdout[-4000:]}\n"
            f"stderr: {completed.stderr[-4000:]}"
        )
    return completed


def remote(host: str, command: str, *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return run(["ssh", host, command], check=check, timeout=timeout)


def scp(src: str, dst: str, *, timeout: int | None = None) -> None:
    run(["scp", src, dst], timeout=timeout)


def http_json(url: str, timeout: int = 180) -> tuple[int, dict[str, Any]]:
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
    except (OSError, ValueError) as exc:
        return 0, {"status": "FAIL", "error": str(exc), "url": url}


def remote_sha256(host: str, path: str) -> str:
    result = remote(host, f"sha256sum {path}", timeout=300)
    return result.stdout.split()[0]


def ensure_archives() -> dict[str, Any]:
    LOCAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    archives = {
        "a5d7_citywide_briefings_v1": LOCAL_OUTPUT_DIR / "a5d7_citywide_briefings_v1.tar.gz",
        "a4d3b_citywide_roundtrip_borough5": LOCAL_OUTPUT_DIR / "a4d3b_citywide_roundtrip_borough5.tar.gz",
    }
    if not LOCAL_A5D7_DIR.exists():
        raise FileNotFoundError(f"missing {LOCAL_A5D7_DIR}")
    if not LOCAL_A4D3B_DIR.exists():
        raise FileNotFoundError(f"missing {LOCAL_A4D3B_DIR}")
    if not archives["a5d7_citywide_briefings_v1"].exists():
        run(["tar", "-C", "outputs", "-czf", str(archives["a5d7_citywide_briefings_v1"]), "a5d7_citywide_briefings_v1"], timeout=1800)
    if not archives["a4d3b_citywide_roundtrip_borough5"].exists():
        run(["tar", "-C", "outputs", "-czf", str(archives["a4d3b_citywide_roundtrip_borough5"]), "a4d3b_citywide_roundtrip_borough5"], timeout=600)
    return {
        name: {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for name, path in archives.items()
    }


def sync_archives(archive_info: dict[str, Any]) -> dict[str, Any]:
    sync: dict[str, Any] = {"method": "scp archive transfer; rsync unavailable in Windows shell", "targets": {}}
    for host, root in [(SPARK_HOST, SPARK_ROOT + "/data"), (FACE_HOST, FACE_ROOT)]:
        remote(host, f"mkdir -p {root} /tmp/citybrain-a5d7b", timeout=60)
        host_result: dict[str, Any] = {}
        for name, info in archive_info.items():
            local_path = Path(info["path"])
            remote_archive = f"/tmp/citybrain-a5d7b/{local_path.name}"
            scp(str(local_path), f"{host}:{remote_archive}", timeout=1800)
            remote_hash = remote_sha256(host, remote_archive)
            remote(host, f"tar -C {root} -xzf {remote_archive}", timeout=1800)
            host_result[name] = {
                "remote_archive": remote_archive,
                "local_sha256": info["sha256"],
                "remote_sha256": remote_hash,
                "hash_match": remote_hash == info["sha256"],
                "extracted_to": root,
            }
        sync["targets"][host] = host_result
    return sync


def deploy_spark_wrapper() -> dict[str, Any]:
    scp(SPARK_WRAPPER, f"{SPARK_HOST}:{SPARK_ROOT}/{SPARK_WRAPPER}", timeout=120)
    command = (
        f"mkdir -p {SPARK_ROOT}/logs {SPARK_ROOT}/outputs && "
        "docker start nim-llm-demo >/dev/null 2>&1 || true && "
        f"if [ -f {SPARK_ROOT}/spark_wrapper.pid ]; then kill $(cat {SPARK_ROOT}/spark_wrapper.pid) >/dev/null 2>&1 || true; fi; "
        f"nohup {SPARK_PYTHON} {SPARK_ROOT}/{SPARK_WRAPPER} --serve "
        f"--bundle-dir {SPARK_ROOT}/data/a5d7_citywide_briefings_v1 "
        f"--summary {SPARK_ROOT}/data/a4d3b_citywide_roundtrip_borough5/A4D3B_CITYWIDE_ROUNDTRIP_BOROUGH5.json "
        f"--output-dir {SPARK_ROOT}/outputs --host 0.0.0.0 --port 8095 "
        f"> {SPARK_ROOT}/logs/spark_wrapper.log 2>&1 & echo $! > {SPARK_ROOT}/spark_wrapper.pid"
    )
    remote(SPARK_HOST, command, timeout=120)
    health = wait_health(f"{SPARK_URL}/health", timeout_s=900)
    return {"spark_url": SPARK_URL, "health": health}


def deploy_face_api_and_frontend() -> dict[str, Any]:
    remote(FACE_HOST, f"mkdir -p {FACE_API_ROOT}", timeout=60)
    scp(FACE_API, f"{FACE_HOST}:{FACE_API_ROOT}/{FACE_API}", timeout=120)
    command = (
        f"if [ -f {FACE_API_ROOT}/briefing_api.pid ]; then kill $(cat {FACE_API_ROOT}/briefing_api.pid) >/dev/null 2>&1 || true; fi; "
        f"nohup python3 {FACE_API_ROOT}/{FACE_API} --serve --host 0.0.0.0 --port 8093 "
        f"--precomputed-dir {FACE_ROOT}/a5d7_citywide_briefings_v1 --spark-base-url {SPARK_URL} "
        f"> {FACE_API_ROOT}/briefing_api.log 2>&1 & echo $! > {FACE_API_ROOT}/briefing_api.pid"
    )
    remote(FACE_HOST, command, timeout=120)
    patched_main = LOCAL_OUTPUT_DIR / "frontend_patch" / "main.js"
    patched_styles = LOCAL_OUTPUT_DIR / "frontend_patch" / "styles.css"
    if patched_main.exists() and patched_styles.exists():
        scp(str(patched_main), f"{FACE_HOST}:/home/txr/txr_workspace/citybrain-face/src/main.js", timeout=120)
        scp(str(patched_styles), f"{FACE_HOST}:/home/txr/txr_workspace/citybrain-face/src/styles.css", timeout=120)
        remote(FACE_HOST, "cd /home/txr/txr_workspace/citybrain-face && npm run build", timeout=600)
        remote(FACE_HOST, "rsync -a /home/txr/txr_workspace/citybrain-face/dist/ /srv/citybrain/current/", timeout=300)
    health = wait_health(f"{FACE_API_BASE_URL}/health", timeout_s=120)
    return {"face_url": FACE_URL, "briefing_api_url": FACE_API_URL, "health": health}


def wait_health(url: str, timeout_s: int) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    last_status = 0
    last_payload: dict[str, Any] = {}
    while time.time() < deadline:
        last_status, last_payload = http_json(url, timeout=30)
        if last_status == 200 and last_payload.get("status") == "PASS":
            return {"status": "PASS", "http_status": last_status, "payload": last_payload}
        time.sleep(5)
    return {"status": "FAIL", "http_status": last_status, "payload": last_payload}


def select_random_blocks(count: int = 5) -> list[str]:
    status, payload = http_json(f"{SPARK_URL}/random-blocks?count=25", timeout=60)
    if status == 200 and payload.get("status") == "PASS":
        blocks = [b for b in payload.get("blocks", []) if b != HERO_BLOCK_KEY]
        return blocks[:count]
    index = read_json(LOCAL_A5D7_DIR / "block_index.json")
    blocks = [key for key in index if key != HERO_BLOCK_KEY]
    rng = random.Random(7502)
    rng.shuffle(blocks)
    return blocks[:count]


def fetch_briefing(base_url: str, block_key: str, mode: str) -> tuple[int, dict[str, Any]]:
    query = urllib.parse.urlencode({"block": block_key, "mode": mode})
    return http_json(f"{base_url}?{query}", timeout=240)


def counts_from(payload: dict[str, Any]) -> dict[str, Any]:
    counts = (payload.get("deterministic_answer") or {}).get("counts") or {}
    return {
        "node_count": counts.get("node_count"),
        "edge_count": counts.get("edge_count"),
        "complaint_count": counts.get("complaint_count"),
        "critical_complaint_count": counts.get("critical_complaint_count"),
        "permit_count": counts.get("permit_count"),
    }


def run_gate() -> dict[str, Any]:
    report: dict[str, Any] = {
        "task": TASK_NAME,
        "created_utc": utc_now(),
        "hero_block": HERO_BLOCK_KEY,
        "spark_url": SPARK_URL,
        "face_url": FACE_URL,
    }
    spark_health_status, spark_health = http_json(f"{SPARK_URL}/health", timeout=60)
    face_health_status, face_health = http_json(f"{FACE_API_BASE_URL}/health", timeout=60)
    report["endpoint_health"] = {
        "spark_http_status": spark_health_status,
        "spark": spark_health,
        "face_http_status": face_health_status,
        "face": face_health,
    }

    pre_status, pre = fetch_briefing(FACE_API_URL, HERO_BLOCK_KEY, "precomputed")
    live_status, live = fetch_briefing(f"{SPARK_URL}/briefing", HERO_BLOCK_KEY, "live")
    report["hero_parity"] = {
        "precomputed_http_status": pre_status,
        "live_http_status": live_status,
        "precomputed_status": pre.get("status"),
        "live_status": live.get("status"),
        "precomputed_counts": counts_from(pre),
        "live_counts": counts_from(live),
        "counts_match": counts_from(pre) == counts_from(live),
        "grounding_status": live.get("grounding_result", {}).get("status"),
        "nim_health_before_call": live.get("nim_call", {}).get("health", {}).get("status"),
    }

    random_results = []
    for block in select_random_blocks(5):
        health_status, health = http_json(f"{SPARK_URL}/health", timeout=60)
        status, payload = fetch_briefing(f"{SPARK_URL}/briefing", block, "live")
        gates = payload.get("grounding_result", {}).get("gates", [])
        isolation = next((gate for gate in gates if gate.get("gate") == "A5D7B-SUBJECT-ISOLATION"), {})
        random_results.append(
            {
                "block_key": block,
                "pre_call_health_http_status": health_status,
                "pre_call_nim_health": health.get("nim_health", {}).get("status"),
                "http_status": status,
                "status": payload.get("status"),
                "grounding_status": payload.get("grounding_result", {}).get("status"),
                "nim_call_status": payload.get("nim_call", {}).get("status"),
                "nim_used_text": payload.get("nim_call", {}).get("used_text"),
                "leaked_tokens": isolation.get("leaked_tokens", []),
                "counts": counts_from(payload),
            }
        )
    report["random_citywide_live_blocks"] = random_results

    neg_status, neg = fetch_briefing(f"{SPARK_URL}/briefing", "9-99999", "live")
    report["negative_invalid_block"] = {
        "http_status": neg_status,
        "status": neg.get("status"),
        "error": neg.get("error"),
        "deterministic_executed": neg.get("deterministic_executed"),
        "rejected_before_deterministic_execution": neg.get("rejected_before_deterministic_execution"),
    }

    round_status, round_payload = fetch_briefing(FACE_API_URL, HERO_BLOCK_KEY, "live")
    html_status = 0
    try:
        with urllib.request.urlopen(f"{FACE_URL}/briefing?block={HERO_BLOCK_KEY}&mode=live", timeout=60) as response:
            html_status = int(response.status)
    except OSError:
        html_status = 0
    report["roundtrip_laptop_browser_to_4070_to_spark_to_nim"] = {
        "api_http_status": round_status,
        "api_status": round_payload.get("status"),
        "origin_chain": round_payload.get("origin_chain"),
        "nim_status": round_payload.get("nim_call", {}).get("status"),
        "grounding_status": round_payload.get("grounding_result", {}).get("status"),
        "html_http_status": html_status,
    }

    checks = {
        "spark_health": spark_health_status == 200 and spark_health.get("status") == "PASS",
        "face_health": face_health_status == 200 and face_health.get("status") == "PASS",
        "hero_parity": report["hero_parity"]["counts_match"] and live.get("status") == "PASS",
        "five_random": len(random_results) == 5
        and all(item["status"] == "PASS" and item["grounding_status"] == "PASS" and not item["leaked_tokens"] for item in random_results),
        "negative": neg_status == 404 and neg.get("deterministic_executed") is False,
        "roundtrip": round_status == 200 and round_payload.get("status") == "PASS" and html_status == 200,
    }
    report["checks"] = checks
    report["status"] = "PASS" if all(checks.values()) else "FAIL"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--skip-deploy", action="store_true")
    args = parser.parse_args(argv)

    report: dict[str, Any] = {"task": TASK_NAME, "created_utc": utc_now()}
    archive_info = ensure_archives()
    report["archive_hashes"] = archive_info
    if not args.skip_sync:
        report["data_sync"] = sync_archives(archive_info)
    if not args.skip_deploy:
        report["spark_deploy"] = deploy_spark_wrapper()
        report["face_deploy"] = deploy_face_api_and_frontend()
    gate = run_gate()
    report.update(gate)
    write_json(LOCAL_OUTPUT_DIR / "A5D7B_HARNESS_REPORT.json", report)
    write_json(LOCAL_OUTPUT_DIR / "snapshot" / "a5d7b_live_citywide_query_v1.json", report)
    sums = {
        "A5D7B_HARNESS_REPORT.json": sha256_file(LOCAL_OUTPUT_DIR / "A5D7B_HARNESS_REPORT.json"),
        "snapshot/a5d7b_live_citywide_query_v1.json": sha256_file(LOCAL_OUTPUT_DIR / "snapshot" / "a5d7b_live_citywide_query_v1.json"),
        **{Path(info["path"]).name: info["sha256"] for info in archive_info.values()},
    }
    write_json(LOCAL_OUTPUT_DIR / "SHA256SUMS.json", sums)
    print(pretty_json({"status": report["status"], "report": str(LOCAL_OUTPUT_DIR / "A5D7B_HARNESS_REPORT.json")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
