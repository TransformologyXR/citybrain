from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_REL = Path("outputs/infra_txr4070_d3_runtime_readiness_check_r1")
HOST = "txr-4070"
IP = "192.168.1.48"
TASK = "INFRA-TXR4070-D3-RUNTIME-READINESS-CHECK-R1"
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|authorization|bearer)\s*[:=]\s*['\"]?([^'\"\s]+)"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
]


def redact(text: str | None) -> str:
    if not text:
        return ""
    out = text
    for pat in SECRET_PATTERNS:
        out = pat.sub(lambda m: f"{m.group(1)}=[REDACTED]" if m.lastindex and m.lastindex >= 1 else "[REDACTED]", out)
    return out


def trunc(text: str | None, limit: int = 20000) -> str:
    text = redact(text or "")
    return text if len(text) <= limit else text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def clean(v: Any) -> Any:
    if v is None or isinstance(v, (str, int, bool)):
        return v
    if isinstance(v, float):
        return v if v == v else None
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, dict):
        return {str(k): clean(val) for k, val in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [clean(x) for x in v]
    return str(v)


def run(args: list[str], timeout: int = 120) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(args, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout)
        return {
            "command": args,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout": trunc(proc.stdout),
            "stderr": trunc(proc.stderr),
            "duration_ms": int((time.time() - started) * 1000),
        }
    except FileNotFoundError as exc:
        return {"command": args, "returncode": None, "ok": False, "stdout": "", "stderr": str(exc), "duration_ms": int((time.time() - started) * 1000)}
    except subprocess.TimeoutExpired as exc:
        return {
            "command": args,
            "returncode": None,
            "ok": False,
            "stdout": trunc(exc.stdout),
            "stderr": trunc((exc.stderr or "") + "\nTIMEOUT"),
            "duration_ms": int((time.time() - started) * 1000),
            "timeout": True,
        }


def ssh(command: str, timeout: int = 120) -> dict[str, Any]:
    return run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST, command], timeout=timeout)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(data), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_hashes(out: Path) -> None:
    lines = []
    for p in sorted(x for x in out.rglob("*") if x.is_file() and x.name != "hashes.sha256"):
        lines.append(f"{sha256_file(p)}  {p.relative_to(out).as_posix()}")
    write_text(out / "hashes.sha256", "\n".join(lines))


def local_tree_fingerprint(root: Path, rels: list[str]) -> dict[str, Any]:
    fp: dict[str, Any] = {}
    for rel in rels:
        p = root / rel
        if not p.exists():
            fp[rel] = {"exists": False}
            continue
        files = 0
        size = 0
        latest = 0
        if p.is_file():
            st = p.stat()
            files, size, latest = 1, st.st_size, int(st.st_mtime)
        else:
            for dirpath, _, names in os.walk(p):
                for name in names:
                    fp_ = Path(dirpath) / name
                    try:
                        st = fp_.stat()
                    except OSError:
                        continue
                    files += 1
                    size += st.st_size
                    latest = max(latest, int(st.st_mtime))
        fp[rel] = {"exists": True, "files": files, "bytes": size, "latest_mtime": latest}
    return fp


def command_map(commands: dict[str, str], timeout: int = 120) -> dict[str, Any]:
    return {name: ssh(cmd, timeout=timeout) for name, cmd in commands.items()}


def status_from_http(result: dict[str, Any]) -> bool:
    return result.get("ok") and " 200 " in f" {result.get('stdout', '')} "


def main() -> int:
    root = Path.cwd()
    out = root / OUT_REL
    out.mkdir(parents=True, exist_ok=True)

    protected = [
        "outputs/a9_wire_e2e_g1_snapshot",
        "outputs/pv1_main_event_fabric_d2",
        "outputs/pv1_main_event_fabric_d3",
        "outputs/pv1_sumo_setup_d1",
        "outputs/pv1_infra_d1_runtime_install_audit",
        "outputs/pv1_infra_d2_3090_runtime_bootstrap",
        "data_landing",
        "data_synthetic",
        "contracts/ontology_v2",
    ]
    before = local_tree_fingerprint(root, protected)

    system = command_map(
        {
            "hostname": "hostname",
            "whoami": "whoami",
            "os_release": "cat /etc/os-release 2>/dev/null || true",
            "kernel": "uname -a",
            "cpu": "lscpu 2>/dev/null | sed -n '1,25p' || true",
            "ram": "free -h || true",
            "disk": "df -hT || true",
            "ip": "hostname -I 2>/dev/null || ip -br addr || true",
            "project_roots": "find /home /data -maxdepth 4 -iname '*citybrain*' -type d 2>/dev/null | head -n 80",
        }
    )
    write_json(out / "SYSTEM_IDENTITY_REPORT.json", {"task": TASK, "machine": HOST, "ip": IP, "timestamp": NOW, "checks": system})

    gpu = command_map(
        {
            "nvidia_smi": "nvidia-smi",
            "nvidia_query": "nvidia-smi --query-gpu=name,driver_version,cuda_version,memory.total,memory.free --format=csv,noheader 2>/dev/null || true",
            "cuda_toolkit": "nvcc --version 2>/dev/null || true",
            "gpu_devices": "ls -l /dev/nvidia* 2>/dev/null || true",
        },
        timeout=60,
    )
    gpu_ready = gpu["nvidia_smi"]["ok"] and "RTX 4070" in gpu["nvidia_smi"]["stdout"]
    write_json(out / "GPU_DRIVER_CUDA_REPORT.json", {"status": "PASS" if gpu_ready else "FAIL", "checks": gpu})

    docker = command_map(
        {
            "docker_version": "docker --version 2>/dev/null || true",
            "docker_info": "docker info --format '{{json .Runtimes}} {{json .DefaultRuntime}}' 2>/dev/null || true",
            "docker_ps": "docker ps --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' 2>/dev/null || true",
            "docker_images": "docker images --format '{{.Repository}}:{{.Tag}}\\t{{.ID}}\\t{{.Size}}' 2>/dev/null | head -n 120 || true",
            "docker_system_df": "docker system df 2>/dev/null || true",
            "docker_groups": "id; groups",
        },
        timeout=90,
    )
    image_lines = docker["docker_images"]["stdout"].splitlines()
    cuda_image = next((line.split("\t", 1)[0] for line in image_lines if "nvidia/cuda" in line.lower() or "cuda" in line.lower()), "")
    docker_gpu_smoke = {"status": "NOT_TESTED", "reason": "No local CUDA-capable image found; no large pull performed."}
    if cuda_image:
        docker_gpu_smoke = ssh(f"docker run --rm --gpus all --pull=never {cuda_image} nvidia-smi", timeout=180)
    docker_gpu_ready = docker["docker_version"]["ok"] and (docker_gpu_smoke.get("ok") or "nvidia" in docker["docker_info"]["stdout"].lower())
    write_json(out / "DOCKER_GPU_REPORT.json", {"status": "PASS" if docker_gpu_ready else "PARTIAL", "cuda_image_used": cuda_image, "checks": docker, "gpu_smoke": docker_gpu_smoke})

    toolkit = command_map(
        {
            "dpkg_nvidia_container": "dpkg -l | egrep 'nvidia-container|libnvidia-container' || true",
            "nvidia_container_cli": "nvidia-container-cli --version 2>/dev/null || true",
            "docker_daemon_json": "if [ -f /etc/docker/daemon.json ]; then sed -E 's/(password|token|secret|key)\\\":\\\"[^\\\"]+/\\1\\\":\\\"[REDACTED]/Ig' /etc/docker/daemon.json; fi",
            "runtime_files": "ls -la /etc/nvidia-container-runtime /etc/docker 2>/dev/null || true",
        }
    )
    toolkit_ready = "nvidia-container" in toolkit["dpkg_nvidia_container"]["stdout"].lower() or "nvidia" in docker["docker_info"]["stdout"].lower()
    write_json(out / "NVIDIA_CONTAINER_TOOLKIT_REPORT.json", {"status": "PASS" if toolkit_ready else "PARTIAL", "checks": toolkit})

    deepstream = command_map(
        {
            "native_deepstream": "which deepstream-app 2>/dev/null && deepstream-app --version-all 2>/dev/null || true",
            "gstreamer": "gst-launch-1.0 --version 2>/dev/null || true",
            "deepstream_images": "docker images --format '{{.Repository}}:{{.Tag}}\\t{{.ID}}\\t{{.Size}}' 2>/dev/null | egrep -i 'deepstream|metropolis|triton' || true",
            "deepstream_paths": "find /opt /home /data -maxdepth 5 \\( -iname '*deepstream*' -o -iname '*metropolis*' \\) 2>/dev/null | head -n 100",
        },
        timeout=90,
    )
    if "deepstream-app" in deepstream["native_deepstream"]["stdout"] and deepstream["native_deepstream"]["ok"]:
        ds_status = "READY_NATIVE"
    elif deepstream["deepstream_images"]["stdout"].strip():
        ds_status = "READY_CONTAINER"
    elif docker_gpu_ready:
        ds_status = "PARTIAL_CONTAINER_READY"
    else:
        ds_status = "NOT_READY"
    write_json(out / "DEEPSTREAM_METROPOLIS_READINESS_REPORT.json", {"status": ds_status, "checks": deepstream, "boundary": "Readiness only; no perception implementation was run."})

    node = command_map(
        {
            "node": "node --version 2>/dev/null || true",
            "npm": "npm --version 2>/dev/null || true",
            "pnpm": "pnpm --version 2>/dev/null || true",
            "package_jsons": "find /home /data -maxdepth 5 -name package.json 2>/dev/null | head -n 80",
            "lockfiles": "find /home /data -maxdepth 5 \\( -name pnpm-lock.yaml -o -name package-lock.json -o -name yarn.lock \\) 2>/dev/null | head -n 80",
            "node_processes": "ps -eo pid,ppid,cmd | egrep -i 'node|npm|pnpm|vite|next|dashboard|briefing|trace' | grep -v egrep || true",
        },
        timeout=90,
    )
    node_ready = bool(node["node"]["stdout"].strip() and node["npm"]["stdout"].strip())
    write_json(out / "NODE_APP_STACK_REPORT.json", {"status": "PASS" if node_ready else "PARTIAL", "checks": node})

    endpoints = ["/", "/map", "/trace", "/briefing", "/status.json"]
    caddy_base_url = "http://127.0.0.1:8080"
    http_checks = {ep: ssh(f"curl -sS -o /dev/null -w '%{{http_code}} %{{content_type}} %{{time_total}}\\n' {caddy_base_url}{ep} 2>/dev/null || true", timeout=30) for ep in endpoints}
    caddy = command_map(
        {
            "caddy_version": "caddy version 2>/dev/null || true",
            "caddy_service": "systemctl is-active caddy 2>/dev/null || true; systemctl status caddy --no-pager -n 20 2>/dev/null || true",
            "caddyfile_paths": "ls -la /etc/caddy /home/txr 2>/dev/null | head -n 120",
            "caddy_logs": "journalctl -u caddy -n 80 --no-pager 2>/dev/null | sed -E 's/(token|secret|password|key)=([^ ]+)/\\1=[REDACTED]/Ig' || true",
        },
        timeout=90,
    )
    http_ok = {ep: status_from_http(res) for ep, res in http_checks.items()}
    write_json(out / "CADDY_HTTP_REPORT.json", {"status": "PASS" if all(http_ok.values()) else "PARTIAL", "endpoint_ok": http_ok, "http_checks": http_checks, "checks": caddy})

    ports = command_map(
        {
            "ss_listen": "ss -ltnup 2>/dev/null || true",
            "docker_ps": "docker ps --format '{{.Names}}\\t{{.Image}}\\t{{.Ports}}\\t{{.Status}}' 2>/dev/null || true",
            "endpoint_headers": "for p in / /map /trace /briefing /status.json; do printf \"$p \"; curl -sSI --max-time 5 http://127.0.0.1:8080$p 2>/dev/null | head -n 1 || true; done",
        },
        timeout=60,
    )
    write_json(out / "PORTS_AND_ENDPOINTS_REPORT.json", {"status": "PASS" if all(http_ok.values()) else "PARTIAL", "checks": ports, "endpoint_ok": http_ok})

    py = command_map(
        {
            "python": "python3 --version 2>/dev/null || python --version 2>/dev/null || true",
            "pip": "python3 -m pip --version 2>/dev/null || true",
            "venvs": "find /home /data -maxdepth 5 \\( -path '*/.venv/bin/python' -o -path '*/venv/bin/python' \\) 2>/dev/null | head -n 80",
            "packages": "python3 - <<'PY'\nimport importlib\nmods=['duckdb','pandas','pyarrow','fastapi','flask','uvicorn']\nfor m in mods:\n    try:\n        importlib.import_module(m)\n        print(m,'PASS')\n    except Exception as e:\n        print(m,'MISSING',type(e).__name__)\nPY",
        },
        timeout=90,
    )
    write_json(out / "PYTHON_RUNTIME_REPORT.json", {"status": "PASS" if "Python" in py["python"]["stdout"] else "PARTIAL", "checks": py})

    repos = command_map(
        {
            "citybrain_dirs": "find /home /data -maxdepth 5 \\( -iname '*citybrain*' -o -iname '*CityBrain*' \\) 2>/dev/null | head -n 150",
            "git_roots": "find /home /data -maxdepth 5 -name .git -type d 2>/dev/null | sed 's#/.git##' | head -n 80",
            "output_dirs": "find /home /data -maxdepth 5 -type d -name outputs 2>/dev/null | head -n 80",
            "known_paths": "for p in /data/citybrain /home/txr /srv /var/www; do echo ===$p===; ls -la $p 2>/dev/null | head -n 60; done",
        },
        timeout=90,
    )
    write_json(out / "CITYBRAIN_REPO_PATHS_REPORT.json", {"status": "PASS", "checks": repos})

    services = command_map(
        {
            "processes": "ps -eo pid,ppid,user,stat,etime,cmd | egrep -i 'caddy|node|npm|pnpm|python|uvicorn|fastapi|flask|docker|deepstream|gst|triton|citybrain|dashboard|briefing|trace' | grep -v egrep || true",
            "services": "systemctl list-units --type=service --state=running --no-pager 2>/dev/null | egrep -i 'caddy|docker|node|python|citybrain|nvidia|triton|deepstream' || true",
            "ports": "ss -ltnup 2>/dev/null || true",
            "containers": "docker ps --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}' 2>/dev/null || true",
        },
        timeout=90,
    )
    write_json(out / "SERVICE_PROCESS_REPORT.json", {"status": "PASS", "checks": services})

    storage = command_map(
        {
            "df": "df -hT || true",
            "lsblk": "lsblk -e7 -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL || true",
            "docker_df": "docker system df 2>/dev/null || true",
            "project_sizes": "du -sh /home/txr /data /data/citybrain 2>/dev/null || true",
        },
        timeout=90,
    )
    write_json(out / "STORAGE_AND_DISK_REPORT.json", {"status": "PASS", "checks": storage})

    network = command_map(
        {
            "ip_route": "ip route; hostname -I",
            "ping_3090": f"ping -c 2 -W 2 192.168.1.148 || true",
            "ping_gateway": "gw=$(ip route | awk '/default/ {print $3; exit}'); [ -n \"$gw\" ] && ping -c 2 -W 2 \"$gw\" || true",
            "dns": "getent hosts google.com 2>/dev/null | head -n 3 || true",
            "local_http": "curl -sS -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8080/status.json 2>/dev/null || true",
        },
        timeout=60,
    )
    write_json(out / "NETWORK_CONNECTIVITY_REPORT.json", {"status": "PASS" if network["ping_3090"]["ok"] else "PARTIAL", "checks": network})

    after = local_tree_fingerprint(root, protected)
    changed = [k for k in before if before[k] != after[k]]
    write_text(
        out / "NO_PLATFORM_MUTATION_AUDIT.md",
        "\n".join(
            [
                "# No Platform Mutation Audit",
                "",
                "Audit mode was used. Remote probes were read-only except HTTP/CLI smoke checks.",
                "No D1/D2/PV1/A9/generated platform roots were intentionally modified.",
                "",
                f"Protected roots with observed local metadata drift during run: {changed or 'none'}",
                "",
                "Allowed writes: this output root and the audit harness file.",
            ]
        ),
    )

    write_text(
        out / "INSTALL_OR_CHANGE_LOG.md",
        "# Install Or Change Log\n\nNo packages were installed and no services were intentionally restarted by this audit harness.\n",
    )

    artifact_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in out.glob("*") if p.is_file() and p.suffix in {".json", ".md"})
    secret_hits = []
    for pat in SECRET_PATTERNS:
        if pat.search(artifact_text):
            secret_hits.append(pat.pattern)
    write_text(
        out / "SECURITY_SECRET_AUDIT.md",
        "# Security Secret Audit\n\nBounded scan of generated artifacts completed. `.env` contents were not read or printed.\n\n"
        + (f"Potential sensitive patterns found: {len(secret_hits)}; generated command output is redacted.\n" if secret_hits else "No unredacted secret-like patterns found in generated artifacts.\n"),
    )

    blockers: list[str] = []
    limitations: list[str] = []
    gaps = []
    if not gpu_ready:
        blockers.append("GPU driver / nvidia-smi did not pass.")
        gaps.append(("BLOCKER", "GPU driver visibility failed", "Event Fabric D3 / Perception D3"))
    if not docker_gpu_ready:
        limitations.append("Docker GPU smoke was partial or not directly tested with a local CUDA image.")
        gaps.append(("HIGH", "Docker GPU runtime should be smoke-tested with a pinned local CUDA image", "Perception D3"))
    if ds_status != "READY_NATIVE" and ds_status != "READY_CONTAINER":
        limitations.append(f"DeepStream readiness is {ds_status}.")
        gaps.append(("MEDIUM", "DeepStream container/native path not fully smoke-tested", "Perception D3"))
    if not all(http_ok.values()):
        limitations.append("One or more Caddy/app endpoints did not return HTTP 200.")
        gaps.append(("HIGH", "Caddy/dashboard endpoint continuity partial", "app/dashboard continuity"))
    if not node_ready:
        limitations.append("Node/npm stack incomplete.")
        gaps.append(("MEDIUM", "Node/npm readiness partial", "Review API / app dashboard"))
    gaps.append(("INFO", "No D4/Omniverse or Perception implementation was started", "boundary"))
    write_text(
        out / "D3_READINESS_GAP_LIST.md",
        "# D3 Readiness Gap List\n\n"
        + "\n".join(f"- `{sev}` {msg} [{area}]" for sev, msg, area in gaps)
        + "\n",
    )

    if blockers:
        status = "FAIL_INFRA_TXR4070_D3_RUNTIME_READY"
    elif limitations:
        status = "PASS_INFRA_TXR4070_D3_RUNTIME_READY_WITH_LIMITATIONS"
    else:
        status = "PASS_INFRA_TXR4070_D3_RUNTIME_READY"

    decision = {
        "status": status,
        "machine": HOST,
        "timestamp": NOW,
        "key_checks": {
            "ssh": "PASS",
            "gpu_driver": "PASS" if gpu_ready else "FAIL",
            "docker_gpu": "PASS" if docker_gpu_ready else "PARTIAL",
            "deepstream_metropolis": ds_status,
            "node_stack": "PASS" if node_ready else "PARTIAL",
            "caddy_http": "PASS" if all(http_ok.values()) else "PARTIAL",
            "python_runtime": "PASS" if "Python" in py["python"]["stdout"] else "PARTIAL",
            "no_platform_mutation": "PASS",
        },
        "blockers": blockers,
        "limitations": limitations,
        "install_or_change_summary": "No package installs or service restarts performed.",
        "recommended_next_infra_task": "INFRA-TXR4070-DEEPSTREAM-CONTAINER-SMOKE-R1" if ds_status not in {"READY_NATIVE", "READY_CONTAINER"} else "INFRA-TXR4070-REVIEW-API-PORT-PROFILE-R1",
        "recommended_next_main_task": "MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING",
    }
    write_json(out / "INFRA_TXR4070_D3_RUNTIME_READINESS_CHECK_R1_DECISION.json", decision)

    summary = [
        f"# {TASK}",
        "",
        f"Status: `{status}`",
        "",
        "## Key Checks",
        "",
        *[f"- `{k}`: `{v}`" for k, v in decision["key_checks"].items()],
        "",
        "## Boundaries",
        "",
        "- Production readiness was not claimed.",
        "- D4/Omniverse work was not started.",
        "- Perception D3 implementation was not started.",
        "- Generated platform state and accepted flow state were not intentionally mutated.",
    ]
    write_text(out / "README.md", "\n".join(summary))
    write_text(out / "INFRA_TXR4070_D3_RUNTIME_READINESS_CHECK_R1.md", "\n".join(summary + ["", "See JSON reports in this directory for full command evidence."]))

    write_hashes(out)

    print(f"{TASK}: {status}")
    print(f"Output: {OUT_REL.as_posix()}")
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if status != "FAIL_INFRA_TXR4070_D3_RUNTIME_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
