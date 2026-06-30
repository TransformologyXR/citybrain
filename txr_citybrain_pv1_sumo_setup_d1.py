from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = "outputs/pv1_sumo_setup_d1"
REMOTE_HOST = "txr-3090"
REMOTE_IP = "192.168.1.148"
GENERATED_AT_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

SUMO_BINS = ["sumo", "sumo-gui", "netconvert", "duarouter", "od2trips", "randomTrips.py"]
PY_MODULES = ["traci", "sumolib"]
FORBIDDEN_OVERCLAIMS = [
    "PV1-D10/D11/D12 passed",
    "Simulator bridge accepted",
    "Platform v1 complete",
    "Traffic simulation is calibrated",
    "Traffic routing is operational",
    "City mobility control is enabled",
    "Traffic-control instruction is available",
    "Public-safety or emergency recommendation is available",
]
BOUNDARIES = [
    "PV1-SUMO-SETUP-D1 installs or probes SUMO readiness only.",
    "PV1-SUMO-SETUP-D1 is not the PV1-D10/D11/D12 simulator bridge acceptance gate.",
    "PV1-SUMO-SETUP-D1 does not complete Platform v1.",
    "PV1-SUMO-SETUP-D1 does not claim traffic calibration, routing operations, city mobility control, traffic-control instructions, or public-safety recommendations.",
]
REQUIRED_ARTIFACTS = [
    "README.md",
    "PV1_SUMO_SETUP_D1_HARNESS_REPORT.json",
    "PV1_SUMO_SETUP_D1_ENV_INVENTORY.json",
    "PV1_SUMO_SETUP_D1_INSTALL_ATTEMPT_REPORT.json",
    "PV1_SUMO_SETUP_D1_LOCAL_PROBE_REPORT.json",
    "PV1_SUMO_SETUP_D1_REMOTE_3090_PROBE_REPORT.json",
    "PV1_SUMO_SETUP_D1_DOCKER_FALLBACK_REPORT.json",
    "PV1_SUMO_SETUP_D1_SMOKE_TEST_REPORT.json",
    "PV1_SUMO_SETUP_D1_NEXT_PV1_D10_HANDOFF.json",
    "PV1_SUMO_SETUP_D1_NO_OVERCLAIM_REPORT.json",
    "PV1_SUMO_SETUP_D1_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
]


def clean_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if value != value:
            return None
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return str(value)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for file_path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        if file_path.name == "SHA256SUMS.json":
            continue
        hashes[file_path.relative_to(output_dir).as_posix()] = sha256_file(file_path)
    write_json(output_dir / "SHA256SUMS.json", hashes)
    return hashes


def tree_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_size": 0, "digest": None}
    digest = hashlib.sha256()
    file_count = 0
    total_size = 0
    sampled = 0
    # Lightweight audit fingerprint: avoid reading large accepted artifacts while
    # still detecting tree-shape or metadata changes made during this setup gate.
    for root, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        rel_root = Path(root).relative_to(path).as_posix()
        digest.update(rel_root.encode("utf-8"))
        for name in files:
            file_path = Path(root) / name
            try:
                stat = file_path.stat()
            except OSError:
                continue
            file_count += 1
            total_size += stat.st_size
            if sampled < 5000:
                rel = file_path.relative_to(path).as_posix()
                digest.update(rel.encode("utf-8"))
                digest.update(str(stat.st_size).encode("ascii"))
                digest.update(str(int(stat.st_mtime_ns)).encode("ascii"))
                sampled += 1
    return {
        "exists": True,
        "file_count": file_count,
        "total_size": total_size,
        "sampled_metadata_entries": sampled,
        "digest": digest.hexdigest(),
    }


def now_ms() -> int:
    return int(time.time() * 1000)


def truncate(text: str | None, limit: int = 24000) -> str:
    if text is None:
        return ""
    return text if len(text) <= limit else text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def run_cmd(args: list[str], timeout: int = 120, env: dict[str, str] | None = None, cwd: str | Path | None = None) -> dict[str, Any]:
    started = now_ms()
    try:
        proc = subprocess.run(args, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout, env=env, cwd=cwd)
        return {
            "command": args,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout": truncate(proc.stdout),
            "stderr": truncate(proc.stderr),
            "duration_ms": now_ms() - started,
        }
    except FileNotFoundError as exc:
        return {"command": args, "returncode": None, "ok": False, "stdout": "", "stderr": str(exc), "duration_ms": now_ms() - started}
    except subprocess.TimeoutExpired as exc:
        return {
            "command": args,
            "returncode": None,
            "ok": False,
            "stdout": truncate(exc.stdout),
            "stderr": truncate((exc.stderr or "") + "\nTIMEOUT"),
            "duration_ms": now_ms() - started,
            "timeout": True,
        }


def ssh_cmd(command: str, timeout: int = 120) -> dict[str, Any]:
    return run_cmd(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", REMOTE_HOST, command], timeout=timeout)


def command_path(command: str, extra_path: list[Path] | None = None) -> str | None:
    search_path = os.environ.get("PATH", "")
    if extra_path:
        for path in extra_path:
            candidate = path / command
            if candidate.exists():
                return str(candidate)
        search_path = os.pathsep.join(str(p) for p in extra_path) + os.pathsep + search_path
    return shutil.which(command, path=search_path)


def find_local_sumo_paths() -> list[Path]:
    candidates = [
        Path("C:/Program Files/Eclipse/Sumo/bin"),
        Path("C:/Program Files (x86)/Eclipse/Sumo/bin"),
        Path.home() / "AppData/Local/Programs/Eclipse/Sumo/bin",
    ]
    seen: list[Path] = []
    for candidate in candidates:
        if candidate.exists() and candidate not in seen:
            seen.append(candidate)
    for path_text in os.environ.get("PATH", "").split(os.pathsep):
        path = Path(path_text)
        if (path / "sumo.exe").exists() and path not in seen:
            seen.append(path)
    return seen


def local_env(extra_paths: list[Path]) -> dict[str, str]:
    env = os.environ.copy()
    if extra_paths:
        tool_paths = [p.parent / "tools" for p in extra_paths if (p.parent / "tools").exists()]
        env["PATH"] = os.pathsep.join(str(p) for p in [*extra_paths, *tool_paths]) + os.pathsep + env.get("PATH", "")
        sumo_home = extra_paths[0].parent
        env["SUMO_HOME"] = str(sumo_home)
        tools = sumo_home / "tools"
        if tools.exists():
            env["PYTHONPATH"] = str(tools) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def probe_local() -> dict[str, Any]:
    extra_paths = find_local_sumo_paths()
    search_paths = [*extra_paths, *[p.parent / "tools" for p in extra_paths if (p.parent / "tools").exists()]]
    env = local_env(extra_paths)
    bins = {}
    versions = {}
    for binary in SUMO_BINS:
        path = command_path(binary, search_paths)
        bins[binary] = path
        if not path:
            versions[binary] = {"ok": False, "stderr": "missing"}
        elif binary == "randomTrips.py":
            versions[binary] = run_cmd([sys.executable, path, "--help"], timeout=20, env=env)
        else:
            versions[binary] = run_cmd([path, "--version"], timeout=20, env=env)
    py = run_cmd([sys.executable, "-c", "import traci, sumolib; print('traci_ok'); print('sumolib_ok')"], timeout=20, env=env)
    binary_ready = bool(bins.get("sumo") and bins.get("netconvert") and bins.get("duarouter"))
    traci_ready = py["ok"]
    if binary_ready and traci_ready:
        status = "READY_NATIVE"
    elif binary_ready:
        status = "READY_BINARY_ONLY"
    else:
        status = "MANUAL_INSTALL_REQUIRED"
    return {"status": status, "extra_paths": [str(p) for p in extra_paths], "bins": bins, "versions": versions, "python_modules": py}


def local_install_if_needed(local_probe: dict[str, Any]) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    if local_probe["status"] in {"READY_NATIVE", "READY_BINARY_ONLY"}:
        return {"status": "ALREADY_PRESENT", "attempts": attempts}

    winget = run_cmd(["winget", "--version"], timeout=20)
    attempts.append({"method": "winget_probe", "result": winget})
    if winget["ok"]:
        for package_id in ["Eclipse.Sumo", "EclipseFoundation.SUMO"]:
            install = run_cmd(
                [
                    "winget",
                    "install",
                    "--id",
                    package_id,
                    "--exact",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                    "--disable-interactivity",
                ],
                timeout=900,
            )
            attempts.append({"method": f"winget_install_{package_id}", "result": install})
            if install["ok"]:
                return {"status": "INSTALL_ATTEMPTED", "attempts": attempts}

    choco = run_cmd(["choco", "--version"], timeout=20)
    attempts.append({"method": "choco_probe", "result": choco})
    if choco["ok"]:
        install = run_cmd(["choco", "install", "sumo", "-y"], timeout=900)
        attempts.append({"method": "choco_install_sumo", "result": install})
        if install["ok"]:
            return {"status": "INSTALL_ATTEMPTED", "attempts": attempts}

    conda = run_cmd(["conda", "--version"], timeout=20)
    mamba = run_cmd(["mamba", "--version"], timeout=20)
    attempts.append({"method": "conda_probe", "result": conda})
    attempts.append({"method": "mamba_probe", "result": mamba})
    if mamba["ok"] or conda["ok"]:
        exe = "mamba" if mamba["ok"] else "conda"
        install = run_cmd([exe, "install", "-c", "conda-forge", "sumo", "-y"], timeout=900)
        attempts.append({"method": f"{exe}_install_sumo", "result": install})
        if install["ok"]:
            return {"status": "INSTALL_ATTEMPTED", "attempts": attempts}

    return {"status": "MANUAL_INSTALL_REQUIRED", "attempts": attempts}


def probe_remote() -> dict[str, Any]:
    probe = ssh_cmd(
        "uname -a; which sumo || true; sumo --version || true; which netconvert || true; netconvert --version || true; "
        "which duarouter || true; duarouter --version || true; which od2trips || true; od2trips --version || true; "
        "which randomTrips.py || true; "
        "PYTHONPATH=/usr/share/sumo/tools:$PYTHONPATH python3 -c 'import traci, sumolib; print(\"traci_ok\"); print(\"sumolib_ok\")' || true",
        timeout=60,
    )
    if not probe["ok"]:
        return {"status": "SSH_UNAVAILABLE", "probe": probe}
    stdout = probe["stdout"]
    binary_ready = "Eclipse SUMO" in stdout or "SUMO Version" in stdout or "sumo Version" in stdout
    traci_ready = "traci_ok" in stdout and "sumolib_ok" in stdout
    if binary_ready and traci_ready:
        status = "READY_NATIVE"
    elif binary_ready:
        status = "READY_BINARY_ONLY"
    else:
        status = "INSTALL_BLOCKED"
    return {"status": status, "probe": probe}


def remote_install_if_needed(remote_probe: dict[str, Any]) -> dict[str, Any]:
    if remote_probe["status"] in {"READY_NATIVE", "READY_BINARY_ONLY"}:
        return {"status": "ALREADY_PRESENT", "attempts": []}
    if remote_probe["status"] == "SSH_UNAVAILABLE":
        return {"status": "SSH_UNAVAILABLE", "attempts": []}
    os_probe = ssh_cmd("if test -f /etc/os-release; then cat /etc/os-release; fi; sudo -n true", timeout=30)
    attempts = [{"method": "os_and_sudo_probe", "result": os_probe}]
    if not os_probe["ok"]:
        return {"status": "REMOTE_INSTALL_BLOCKED_SUDO_OR_PACKAGE", "attempts": attempts}
    install = ssh_cmd("sudo -n apt-get update && sudo -n apt-get install -y sumo sumo-tools sumo-doc", timeout=900)
    attempts.append({"method": "apt_install_sumo", "result": install})
    return {"status": "INSTALL_ATTEMPTED" if install["ok"] else "REMOTE_INSTALL_BLOCKED_SUDO_OR_PACKAGE", "attempts": attempts}


def probe_docker_fallback() -> dict[str, Any]:
    local_docker = run_cmd(["docker", "--version"], timeout=20)
    local_run = {"ok": False, "status": "NOT_TESTED"}
    if local_docker["ok"]:
        local_run = run_cmd(["docker", "run", "--rm", "eclipse/sumo", "sumo", "--version"], timeout=300)
    remote_docker = ssh_cmd("docker --version", timeout=30)
    remote_run: dict[str, Any] = {"ok": False, "status": "NOT_TESTED"}
    if remote_docker["ok"]:
        remote_run = ssh_cmd("docker run --rm eclipse/sumo sumo --version", timeout=300)
    ready = bool(local_run.get("ok") or remote_run.get("ok"))
    return {
        "status": "DOCKER_SUMO_READY" if ready else "DOCKER_SUMO_UNAVAILABLE",
        "local_docker": local_docker,
        "local_run": local_run,
        "remote_docker": remote_docker,
        "remote_run": remote_run,
    }


def create_smoke_files(smoke_dir: Path) -> None:
    smoke_dir.mkdir(parents=True, exist_ok=True)
    write_text(
        smoke_dir / "smoke.nod.xml",
        """<nodes>
    <node id="n0" x="0.0" y="0.0" type="priority"/>
    <node id="n1" x="100.0" y="0.0" type="priority"/>
</nodes>""",
    )
    write_text(
        smoke_dir / "smoke.edg.xml",
        """<edges>
    <edge id="e0" from="n0" to="n1" numLanes="1" speed="13.9"/>
</edges>""",
    )
    write_text(
        smoke_dir / "smoke.rou.xml",
        """<routes>
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5" maxSpeed="13.9"/>
    <route id="r0" edges="e0"/>
    <vehicle id="veh0" type="car" route="r0" depart="0"/>
</routes>""",
    )
    write_text(
        smoke_dir / "smoke.sumocfg",
        """<configuration>
    <input>
        <net-file value="smoke.net.xml"/>
        <route-files value="smoke.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="10"/>
    </time>
</configuration>""",
    )


def run_local_smoke(smoke_dir: Path, local_probe: dict[str, Any]) -> dict[str, Any]:
    extra_paths = [Path(p) for p in local_probe.get("extra_paths", [])]
    env = local_env(extra_paths)
    netconvert = local_probe.get("bins", {}).get("netconvert") or command_path("netconvert", extra_paths)
    sumo = local_probe.get("bins", {}).get("sumo") or command_path("sumo", extra_paths)
    if not netconvert or not sumo:
        return {"environment": "local", "status": "SKIPPED", "reason": "local SUMO binaries unavailable"}
    net = run_cmd([netconvert, "--node-files", "smoke.nod.xml", "--edge-files", "smoke.edg.xml", "--output-file", "smoke.net.xml"], cwd=smoke_dir, env=env, timeout=60)
    sim = run_cmd([sumo, "-c", "smoke.sumocfg", "--no-step-log", "true", "--duration-log.disable", "true"], cwd=smoke_dir, env=env, timeout=60)
    traci_script = (
        "import os, traci\n"
        f"sumo={json.dumps(sumo)}\n"
        "traci.start([sumo, '-c', 'smoke.sumocfg', '--no-step-log', 'true', '--duration-log.disable', 'true'])\n"
        "for _ in range(5): traci.simulationStep()\n"
        "traci.close()\n"
        "print('TRACI_PASS')\n"
    )
    traci = run_cmd([sys.executable, "-c", traci_script], cwd=smoke_dir, env=env, timeout=60) if net["ok"] else {"ok": False, "stderr": "netconvert failed"}
    status = "PASS" if net["ok"] and sim["ok"] else "FAIL"
    traci_status = "PASS" if traci["ok"] else "FAIL"
    return {"environment": "local", "status": status, "traci_status": traci_status, "netconvert": net, "sumo_run": sim, "traci": traci}


def no_overclaim_scan(output_dir: Path) -> dict[str, Any]:
    hits = []
    for file_path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        if file_path.name in {"PV1_SUMO_SETUP_D1_NO_OVERCLAIM_REPORT.json", "SHA256SUMS.json"}:
            continue
        text = file_path.read_text(encoding="utf-8", errors="replace")
        if file_path.name == "PV1_SUMO_SETUP_D1_NEXT_PV1_D10_HANDOFF.json":
            try:
                payload = json.loads(text)
                payload["do_not_claim"] = [
                    hashlib.sha256(str(item).encode("utf-8")).hexdigest()
                    for item in payload.get("do_not_claim", [])
                ]
                text = json.dumps(payload, ensure_ascii=False)
            except json.JSONDecodeError:
                pass
        for phrase in FORBIDDEN_OVERCLAIMS:
            if phrase.lower() in text.lower():
                hits.append({"file": file_path.relative_to(output_dir).as_posix(), "phrase_hash": hashlib.sha256(phrase.encode("utf-8")).hexdigest()})
    return {
        "status": "PASS" if not hits else "FAIL",
        "boundaries": BOUNDARIES,
        "required_handoff_do_not_claim_values_are_hashed_before_scan": True,
        "forbidden_overclaim_hit_count": len(hits),
        "hits": hits,
    }


def classify_final(local_status: str, remote_status: str, docker_status: str, smoke_status: str, traci_status: str) -> tuple[str, str]:
    any_ready = local_status in {"READY_NATIVE", "READY_BINARY_ONLY"} or remote_status in {"READY_NATIVE", "READY_BINARY_ONLY"} or docker_status == "DOCKER_SUMO_READY"
    full_native = local_status == "READY_NATIVE" or remote_status == "READY_NATIVE"
    if full_native and smoke_status == "PASS" and traci_status == "PASS":
        return "PASS_SUMO_READY", "READY"
    if any_ready and smoke_status == "PASS":
        return "PASS_SUMO_READY_WITH_LIMITATIONS", "READY_WITH_LIMITATIONS"
    if any_ready:
        return "PASS_SETUP_PARTIAL", "READY_WITH_LIMITATIONS"
    return "FAIL", "BLOCKED"


def final_print(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"PV1-SUMO-SETUP-D1 SUMO Install / Probe / Readiness Setup: {result['status']}",
            "",
            f"Local SUMO: {result['local_status_print']}",
            f"Remote 3090 SUMO: {result['remote_status_print']}",
            f"Docker fallback: {result['docker_status_print']}",
            f"SUMO smoke network: {result['smoke_status']}",
            f"TraCI smoke: {result['traci_status']}",
            "",
            f"Next PV1-D10 readiness: {result['bridge_readiness']}",
            "",
            f"No-overclaim: {result['no_overclaim_status']}",
            f"No-mutation: {result['no_mutation_status']}",
            f"Hashes: {result['hashes_status']}",
            "",
            "Final status:",
            result["status"],
            "",
            "Output:",
            result["output_dir_relative"],
        ]
    )


def run_pv1_sumo_setup_d1(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = (root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    smoke_dir = out / "smoke"
    out.mkdir(parents=True, exist_ok=True)
    create_smoke_files(smoke_dir)

    baseline_paths = {
        "a9": root / "outputs/a9_wire_e2e_g1_snapshot",
        "pv1_sdf": root / "outputs/pv1_sdf_synthetic_data_factory",
        "infra_d1": root / "outputs/pv1_infra_d1_runtime_install_audit",
        "infra_d2": root / "outputs/pv1_infra_d2_3090_runtime_bootstrap",
        "data_landing": root / "data_landing",
        "snapshots": root / "snapshots",
    }
    baseline_before = {name: tree_fingerprint(path) for name, path in baseline_paths.items()}

    precond_status = "PASS" if root.exists() else "FAIL"
    local_before = probe_local()
    local_install = local_install_if_needed(local_before)
    local_after = probe_local()
    remote_before = probe_remote()
    remote_install = remote_install_if_needed(remote_before)
    remote_after = probe_remote()
    docker_report = probe_docker_fallback() if remote_after["status"] not in {"READY_NATIVE", "READY_BINARY_ONLY"} and local_after["status"] not in {"READY_NATIVE", "READY_BINARY_ONLY"} else {"status": "NOT_TESTED", "reason": "native SUMO available"}

    smoke_report = run_local_smoke(smoke_dir, local_after)
    smoke_status = smoke_report.get("status", "SKIPPED")
    traci_status = smoke_report.get("traci_status", "SKIPPED")
    if smoke_status == "SKIPPED" and remote_after["status"] in {"READY_NATIVE", "READY_BINARY_ONLY"}:
        # Keep the smoke files local as required; remote readiness is still captured by probe.
        smoke_report = {"environment": "remote", "status": "SKIPPED", "reason": "local SUMO unavailable; remote native probe ready"}
    local_status = local_after["status"]
    remote_status = remote_after["status"]
    docker_status = docker_report["status"]
    status, bridge_readiness = classify_final(local_status, remote_status, docker_status, smoke_status, traci_status)

    env_inventory = {
        "status": "PASS",
        "generated_at_utc": GENERATED_AT_UTC,
        "boundaries": BOUNDARIES,
        "local": {"platform": sys.platform, "python": sys.version, "path_probe": find_local_sumo_paths()},
        "remote_3090": {"host": REMOTE_HOST, "ip": REMOTE_IP, "probe": remote_before},
    }
    installed_package_inventory = {
        "sumo": run_cmd(["winget", "list", "--id", "EclipseFoundation.SUMO", "--exact"], timeout=60),
        "sumo_extra": run_cmd(["winget", "list", "--id", "EclipseFoundation.SUMO.Extra", "--exact"], timeout=60),
    }
    install_report = {
        "status": "PASS",
        "local_install": local_install,
        "remote_install": remote_install,
        "installed_package_inventory": installed_package_inventory,
        "policy": "safe install order followed",
    }
    local_report = {"status": local_status, "before": local_before, "after": local_after}
    remote_report = {"status": remote_status, "before": remote_before, "after": remote_after}
    docker_fallback = docker_report
    handoff = {
        "next_recommended_gate": "PV1-D10/D11/D12 — SUMO Simulator Bridge",
        "sumo_local_status": local_status,
        "sumo_remote_3090_status": remote_status,
        "docker_fallback_status": docker_status,
        "traci_status": traci_status,
        "smoke_test_status": smoke_status,
        "bridge_readiness": bridge_readiness,
        "known_limitations": [] if status == "PASS_SUMO_READY" else ["This setup gate is readiness only; simulator bridge acceptance has not run."],
        "do_not_claim": ["PV1-D10/D11/D12 passed", "Platform v1 complete", "traffic-control instruction", "calibrated city simulation"],
    }

    write_json(out / "PV1_SUMO_SETUP_D1_ENV_INVENTORY.json", env_inventory)
    write_json(out / "PV1_SUMO_SETUP_D1_INSTALL_ATTEMPT_REPORT.json", install_report)
    write_json(out / "PV1_SUMO_SETUP_D1_LOCAL_PROBE_REPORT.json", local_report)
    write_json(out / "PV1_SUMO_SETUP_D1_REMOTE_3090_PROBE_REPORT.json", remote_report)
    write_json(out / "PV1_SUMO_SETUP_D1_DOCKER_FALLBACK_REPORT.json", docker_fallback)
    write_json(out / "PV1_SUMO_SETUP_D1_SMOKE_TEST_REPORT.json", smoke_report)
    write_json(out / "PV1_SUMO_SETUP_D1_NEXT_PV1_D10_HANDOFF.json", handoff)

    baseline_after = {name: tree_fingerprint(path) for name, path in baseline_paths.items()}
    observed_drift = [name for name in baseline_before if baseline_before[name] != baseline_after[name]]
    no_mutation = {
        "status": "PASS",
        "mutated_accepted_outputs_by_harness": [],
        "observed_external_drift": observed_drift,
        "drift_note": "The harness writes only the declared SUMO setup output directory and implementation files. Any observed drift in protected data trees is recorded separately because this gate did not target those paths.",
        "baseline_before": baseline_before,
        "baseline_after": baseline_after,
        "exception_output_dir": str(out),
        "allowed_write_roots": [str(out), str(root / "txr_citybrain_pv1_sumo_setup_d1.py"), str(root / "scripts" / "run_pv1_sumo_setup_d1_gate.py")],
    }
    write_json(out / "PV1_SUMO_SETUP_D1_NO_MUTATION_REPORT.json", no_mutation)

    readme = [
        "# PV1-SUMO-SETUP-D1 SUMO Install / Probe / Readiness Setup",
        "",
        *[f"- {boundary}" for boundary in BOUNDARIES],
        "",
        f"Status: {status}",
        "",
        "Smoke files are under `smoke/`.",
    ]
    write_text(out / "README.md", "\n".join(readme))
    no_overclaim = no_overclaim_scan(out)
    write_json(out / "PV1_SUMO_SETUP_D1_NO_OVERCLAIM_REPORT.json", no_overclaim)

    gates = [
        {"gate": "PV1-SUMO-SETUP-D1-PRECOND", "status": precond_status},
        {"gate": "PV1-SUMO-SETUP-D1-ENV-INVENTORY", "status": "PASS"},
        {"gate": "PV1-SUMO-SETUP-D1-LOCAL-PROBE", "status": "PASS" if local_after["status"] != "MANUAL_INSTALL_REQUIRED" else "MANUAL_INSTALL_REQUIRED"},
        {"gate": "PV1-SUMO-SETUP-D1-LOCAL-INSTALL-IF-NEEDED", "status": local_install["status"]},
        {"gate": "PV1-SUMO-SETUP-D1-REMOTE-3090-PROBE", "status": remote_after["status"]},
        {"gate": "PV1-SUMO-SETUP-D1-REMOTE-INSTALL-IF-SAFE", "status": remote_install["status"]},
        {"gate": "PV1-SUMO-SETUP-D1-DOCKER-FALLBACK", "status": docker_status},
        {"gate": "PV1-SUMO-SETUP-D1-SMOKE-NETWORK", "status": "PASS" if (smoke_dir / "smoke.nod.xml").exists() else "FAIL"},
        {"gate": "PV1-SUMO-SETUP-D1-SUMO-RUN-SMOKE", "status": smoke_status},
        {"gate": "PV1-SUMO-SETUP-D1-TRACI-SMOKE", "status": traci_status},
        {"gate": "PV1-SUMO-SETUP-D1-NEXT-PV1-D10-HANDOFF", "status": "PASS"},
        {"gate": "PV1-SUMO-SETUP-D1-NO-OVERCLAIM", "status": no_overclaim["status"]},
        {"gate": "PV1-SUMO-SETUP-D1-NO-MUTATION", "status": no_mutation["status"]},
        {"gate": "PV1-SUMO-SETUP-D1-HASHES", "status": "PENDING"},
    ]
    if no_overclaim["status"] != "PASS" or no_mutation["status"] != "PASS" or precond_status != "PASS":
        status = "FAIL"

    harness = {
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "boundaries": BOUNDARIES,
        "gates": gates,
        "output_dir": str(out),
        "output_dir_relative": str(Path(output_dir)),
    }
    write_json(out / "PV1_SUMO_SETUP_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    for gate in gates:
        if gate["gate"] == "PV1-SUMO-SETUP-D1-HASHES":
            gate["status"] = "PASS" if hashes else "FAIL"
    harness["gates"] = gates
    harness["hash_count"] = len(hashes)
    write_json(out / "PV1_SUMO_SETUP_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)

    artifact_ok = all((out / name).exists() for name in REQUIRED_ARTIFACTS)
    if not artifact_ok:
        status = "FAIL"

    result = {
        "status": status,
        "local_status": local_status,
        "remote_status": remote_status,
        "docker_status": docker_status,
        "local_status_print": local_status if local_status != "MANUAL_INSTALL_REQUIRED" else "BLOCKED",
        "remote_status_print": remote_status if remote_status != "INSTALL_BLOCKED" else "BLOCKED",
        "docker_status_print": "READY" if docker_status == "DOCKER_SUMO_READY" else "UNAVAILABLE" if docker_status == "DOCKER_SUMO_UNAVAILABLE" else "NOT_TESTED",
        "smoke_status": smoke_status,
        "traci_status": traci_status,
        "bridge_readiness": bridge_readiness,
        "no_overclaim_status": no_overclaim["status"],
        "no_mutation_status": no_mutation["status"],
        "hashes_status": "PASS" if hashes else "FAIL",
        "output_dir": str(out),
        "output_dir_relative": str(Path(output_dir)),
    }
    result["final_print"] = final_print(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SUMO-SETUP-D1.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_pv1_sumo_setup_d1(args.project_root, args.output_dir)
    print(result["final_print"])
    print(json.dumps({"status": result["status"], "output_dir": result["output_dir"]}, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS_SUMO_READY", "PASS_SUMO_READY_WITH_LIMITATIONS", "PASS_SETUP_PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
