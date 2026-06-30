from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = "outputs/pv1_infra_d2_3090_runtime_bootstrap"
REMOTE_HOST = "txr-3090"
REMOTE_ROOT = "/data/citybrain"
REMOTE_VENV = "/data/citybrain/envs/pv1-data"
GENERATED_AT_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

REMOTE_DIRS = [
    "/data/citybrain/outputs",
    "/data/citybrain/synthetic",
    "/data/citybrain/replay",
    "/data/citybrain/envs",
    "/data/citybrain/logs",
    "/data/citybrain/manifests",
]

PYTHON_PACKAGES = [
    "pandas",
    "polars",
    "pyarrow",
    "duckdb",
    "geopandas",
    "shapely",
    "pyogrio",
    "pyproj",
    "networkx",
    "jsonschema",
    "pydantic",
    "tqdm",
    "rich",
    "numpy",
]

SYNC_PLAN = [
    {
        "source": "data_synthetic/pv1_sdf/packs/sdf_chi_near_west_side_v1",
        "target": "/data/citybrain/synthetic/pv1_sdf/packs/sdf_chi_near_west_side_v1",
    },
    {
        "source": "outputs/pv1_sdf_synthetic_data_factory",
        "target": "/data/citybrain/outputs/pv1_sdf_synthetic_data_factory",
    },
    {
        "source": "outputs/pv1_d3d4_cross_city_ontology_v2_gate",
        "target": "/data/citybrain/outputs/pv1_d3d4_cross_city_ontology_v2_gate",
    },
]

BOUNDARIES = [
    "PV1-INFRA-D2 bootstraps 3090 runtime layout and the SDF/data environment only.",
    "PV1-INFRA-D2 does not mutate accepted outputs.",
    "PV1-INFRA-D2 does not reinstall GPU drivers, CUDA, Docker, or RAPIDS.",
    "PV1-INFRA-D2 does not install SUMO.",
    "PV1-INFRA-D2 does not stop running containers.",
    "PV1-INFRA-D2 does not complete Platform v1.",
    "SDF remains synthetic [S] data, not real observed data.",
]

FORBIDDEN_OVERCLAIMS = [
    "Platform v1 complete",
    "all runtimes installed",
    "perception complete",
    "SUMO wired",
    "event fabric live",
    "HITL complete",
    "personas complete",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "PV1_INFRA_D2_HARNESS_REPORT.json",
    "PV1_INFRA_D2_3090_LAYOUT_REPORT.json",
    "PV1_INFRA_D2_REMOTE_COMMAND_LOG.json",
    "PV1_INFRA_D2_PYTHON_ENV_REPORT.json",
    "PV1_INFRA_D2_SDF_SYNC_PLAN.json",
    "PV1_INFRA_D2_REPLAY_READINESS_REPORT.json",
    "PV1_INFRA_D2_SUMO_DEFERRAL_REPORT.json",
    "PV1_INFRA_D2_NO_OVERCLAIM_REPORT.json",
    "PV1_INFRA_D2_NO_MUTATION_REPORT.json",
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
    for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = file_path.relative_to(path).as_posix()
        size = file_path.stat().st_size
        file_count += 1
        total_size += size
        digest.update(rel.encode("utf-8"))
        digest.update(str(size).encode("ascii"))
        digest.update(sha256_file(file_path).encode("ascii"))
    return {"exists": True, "file_count": file_count, "total_size": total_size, "digest": digest.hexdigest()}


def now_ms() -> int:
    return int(time.time() * 1000)


def truncate(text: str, limit: int = 20000) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def redact(text: str) -> str:
    if text is None:
        return ""
    value = text
    patterns = [
        re.compile(r"(?i)(password|api[_ -]?key|token|secret|credential)\s*[:=]\s*([^\s,;]+)"),
        re.compile(r"(?i)(bearer)\s+([A-Za-z0-9._\-]{12,})"),
        re.compile(r"nvapi-[A-Za-z0-9_\-]{12,}"),
    ]
    for pattern in patterns:
        value = pattern.sub(lambda m: f"{m.group(1)}=<redacted>" if m.groups() else "<redacted>", value)
    return value


def run_local(args: list[str], timeout: int = 60) -> dict[str, Any]:
    started = now_ms()
    try:
        proc = subprocess.run(args, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout)
        return {
            "command": args,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout": redact(truncate(proc.stdout)),
            "stderr": redact(truncate(proc.stderr)),
            "duration_ms": now_ms() - started,
        }
    except FileNotFoundError as exc:
        return {"command": args, "returncode": None, "ok": False, "stdout": "", "stderr": str(exc), "duration_ms": now_ms() - started}
    except subprocess.TimeoutExpired as exc:
        return {
            "command": args,
            "returncode": None,
            "ok": False,
            "stdout": redact(truncate(exc.stdout or "")),
            "stderr": redact(truncate((exc.stderr or "") + "\nTIMEOUT")),
            "duration_ms": now_ms() - started,
            "timeout": True,
        }


def ssh_command(host: str, command: str, timeout: int = 60, log: list[dict[str, Any]] | None = None, label: str | None = None) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    result = run_local(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, command], timeout=timeout)
    entry = {"label": label or command, "host": host, "started_at": started_at, "result": result}
    if log is not None:
        log.append(entry)
    return entry


def ssh_script(host: str, script: str, timeout: int = 60, log: list[dict[str, Any]] | None = None, label: str | None = None) -> dict[str, Any]:
    encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
    return ssh_command(host, f"printf '%s' '{encoded}' | base64 -d | bash", timeout=timeout, log=log, label=label)


def parse_import_probe(stdout: str) -> dict[str, dict[str, Any]]:
    modules: dict[str, dict[str, Any]] = {}
    for raw_line in stdout.splitlines():
        parts = raw_line.strip().split(maxsplit=2)
        if not parts:
            continue
        name = parts[0]
        status = parts[1] if len(parts) > 1 else "FAIL"
        modules[name] = {"status": status, "detail": parts[2] if len(parts) > 2 else ""}
    return modules


def final_print_block(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"PV1-INFRA-D2 3090 Runtime Layout + SDF/Data Environment Bootstrap: {result['status']}",
            "",
            f"SSH: {result['ssh_status']}",
            f"Directory layout: {result['directory_layout_status']}",
            f"Python env: {result['python_env_status']}",
            f"Replay readiness: {result['replay_readiness_status']}",
            f"SDF sync plan: {result['sync_plan_status']}",
            f"SUMO deferred: {result['sumo_deferred_status']}",
            f"No-overclaim: {result['no_overclaim_status']}",
            f"No-mutation: {result['no_mutation_status']}",
            f"Hashes: {result['hashes_status']}",
            "",
            f"Output: {result['output_dir_relative']}",
        ]
    )


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def make_readme(path: Path, status: str) -> None:
    lines = [
        "# PV1-INFRA-D2 3090 Runtime Layout + SDF/Data Environment Bootstrap",
        "",
        *[f"- {boundary}" for boundary in BOUNDARIES],
        "",
        f"Status: {status}",
        "",
        "This gate creates the safe 3090 runtime directory layout and a project-local SDF/data Python environment.",
        "It also records a sync plan only; no large SDF data sync is run unless `--run-sync` is explicitly provided.",
    ]
    write_text(path, "\n".join(lines))


def no_overclaim_scan(output_dir: Path) -> dict[str, Any]:
    hits = []
    for file_path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        if file_path.name in {"PV1_INFRA_D2_NO_OVERCLAIM_REPORT.json", "SHA256SUMS.json"}:
            continue
        text = file_path.read_text(encoding="utf-8", errors="replace")
        for phrase in FORBIDDEN_OVERCLAIMS:
            if phrase.lower() in text.lower():
                hits.append({"file": file_path.relative_to(output_dir).as_posix(), "phrase_hash": hashlib.sha256(phrase.encode("utf-8")).hexdigest()})
    return {
        "status": "PASS" if not hits else "FAIL",
        "boundaries": BOUNDARIES,
        "forbidden_overclaim_hit_count": len(hits),
        "hits": hits,
        "note": "Forbidden phrases are represented by hash to avoid repeating overclaim text.",
    }


def run_pv1_infra_d2_gate(
    project_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    remote_host: str = REMOTE_HOST,
    run_sync: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = (root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    command_log: list[dict[str, Any]] = []

    accepted_paths = {
        "sdf_umbrella": root / "outputs/pv1_sdf_synthetic_data_factory",
        "sdf_pack": root / "data_synthetic/pv1_sdf/packs/sdf_chi_near_west_side_v1",
        "infra_d1": root / "outputs/pv1_infra_d1_runtime_install_audit",
    }
    baseline_before = {name: tree_fingerprint(path) for name, path in accepted_paths.items()}

    infra_d1 = read_json(root / "outputs/pv1_infra_d1_runtime_install_audit/PV1_INFRA_D1_HARNESS_REPORT.json", {})
    sdf_report = read_json(root / "outputs/pv1_sdf_synthetic_data_factory/PV1_SDF_UMBRELLA_HARNESS_REPORT.json", {})
    precond_ok = (
        infra_d1.get("status") == "PASS_WITH_INSTALL_GAPS"
        and accepted_paths["sdf_umbrella"].exists()
        and accepted_paths["sdf_pack"].exists()
        and sdf_report.get("status") == "PASS_SYNTHETIC_DATA_FACTORY_D1_D6"
    )

    ssh_probe = ssh_command(remote_host, "hostname; uname -a; whoami", timeout=20, log=command_log, label="ssh-preflight")
    ssh_status = "PASS" if ssh_probe["result"]["ok"] else "FAIL"

    mkdir_script = "\n".join(
        [
            "set -euo pipefail",
            *(f"mkdir -p {d}" for d in REMOTE_DIRS),
            "for p in " + " ".join(REMOTE_DIRS) + "; do if test -d \"$p\"; then echo \"$p PASS\"; else echo \"$p FAIL\"; fi; done",
        ]
    )
    mkdir_probe = ssh_script(remote_host, mkdir_script, timeout=30, log=command_log, label="create-runtime-directories") if ssh_status == "PASS" else {"result": {"ok": False, "stdout": ""}}

    venv_script = f"""
set -euo pipefail
if test ! -x {REMOTE_VENV}/bin/python; then
  python3 -m venv {REMOTE_VENV}
  echo VENV_CREATED
else
  echo VENV_EXISTS
fi
{REMOTE_VENV}/bin/python -m pip install --upgrade pip setuptools wheel
{REMOTE_VENV}/bin/python -m pip install {' '.join(PYTHON_PACKAGES)}
"""
    venv_install = ssh_script(remote_host, venv_script, timeout=900, log=command_log, label="create-venv-and-install-packages") if ssh_status == "PASS" else {"result": {"ok": False, "stdout": "", "stderr": "SSH unavailable"}}

    import_probe_code = "\n".join(
        [
            "import importlib",
            f"mods = {json.dumps(PYTHON_PACKAGES)}",
            "for m in mods:",
            "    try:",
            "        mod = importlib.import_module(m)",
            "        ver = getattr(mod, '__version__', 'unknown')",
            "        print(m, 'PASS', ver)",
            "    except Exception as e:",
            "        print(m, 'FAIL', repr(e))",
        ]
    )
    import_probe_script = f"{REMOTE_VENV}/bin/python - <<'PY'\n{import_probe_code}\nPY"
    import_probe = ssh_script(remote_host, import_probe_script, timeout=120, log=command_log, label="python-import-probe") if ssh_status == "PASS" else {"result": {"ok": False, "stdout": ""}}
    module_results = parse_import_probe(import_probe["result"].get("stdout", ""))
    missing_packages = [pkg for pkg in PYTHON_PACKAGES if module_results.get(pkg, {}).get("status") != "PASS"]
    python_env_status = "PASS" if not missing_packages and import_probe["result"].get("ok") else "PARTIAL" if module_results else "FAIL"
    python_env_gate_status = "PASS" if python_env_status == "PASS" else "PYTHON_ENV_PARTIAL" if python_env_status == "PARTIAL" else "FAIL"

    probes = {
        "hostname": ssh_command(remote_host, "hostname", timeout=20, log=command_log, label="probe-hostname") if ssh_status == "PASS" else None,
        "uname": ssh_command(remote_host, "uname -a", timeout=20, log=command_log, label="probe-uname") if ssh_status == "PASS" else None,
        "nvidia_smi": ssh_command(remote_host, "nvidia-smi", timeout=30, log=command_log, label="probe-nvidia-smi") if ssh_status == "PASS" else None,
        "docker_version": ssh_command(remote_host, "docker --version", timeout=20, log=command_log, label="probe-docker-version") if ssh_status == "PASS" else None,
        "docker_ps": ssh_command(remote_host, "docker ps --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}'", timeout=20, log=command_log, label="probe-docker-ps") if ssh_status == "PASS" else None,
        "ls_data_citybrain": ssh_command(remote_host, "ls -lah /data/citybrain", timeout=20, log=command_log, label="probe-layout-ls") if ssh_status == "PASS" else None,
        "find_data_citybrain": ssh_command(remote_host, "find /data/citybrain -maxdepth 2 -type d | sort", timeout=20, log=command_log, label="probe-layout-find") if ssh_status == "PASS" else None,
    }

    remote_dirs_status = {}
    for line in (mkdir_probe["result"].get("stdout") or "").splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[0].startswith("/data/citybrain"):
            remote_dirs_status[parts[0]] = parts[1]
    directory_layout_status = "PASS" if all(remote_dirs_status.get(d) == "PASS" for d in REMOTE_DIRS) else "FAIL"

    replay_probe = ssh_script(
        remote_host,
        f"set -euo pipefail\nfor p in /data/citybrain/replay /data/citybrain/synthetic /data/citybrain/manifests; do test -d \"$p\" && echo \"$p PASS\" || echo \"$p FAIL\"; done",
        timeout=20,
        log=command_log,
        label="replay-readiness-probe",
    ) if ssh_status == "PASS" else {"result": {"ok": False, "stdout": ""}}
    replay_readiness_status = "PASS" if replay_probe["result"].get("ok") and "FAIL" not in replay_probe["result"].get("stdout", "") else "FAIL"

    sync_entries = []
    for entry in SYNC_PLAN:
        source = root / entry["source"]
        sync_entries.append(
            {
                **entry,
                "source_exists": source.exists(),
                "target_prepared_parent": str(Path(entry["target"]).parent).replace("\\", "/"),
                "action": "PLAN_ONLY" if not run_sync else "SYNC_REQUESTED",
            }
        )
    sync_plan_status = "PASS" if sync_entries and all(item["action"] == "PLAN_ONLY" for item in sync_entries) else "FAIL"
    sync_execution = {"run_sync": run_sync, "status": "NOT_RUN", "reason": "No sync was run because --run-sync was not provided."}
    if run_sync:
        sync_execution = {"run_sync": run_sync, "status": "REFUSED", "reason": "This harness records the plan; data movement is intentionally not implemented here."}
        sync_plan_status = "FAIL"

    sumo_deferred_report = {
        "status": "PASS",
        "boundaries": BOUNDARIES,
        "SUMO_INSTALLED": "NOT_PROBED_FOR_INSTALL",
        "SUMO_NEEDED_FOR": "PV1-D10/D11/D12",
        "INSTALL_ACTION": "DEFERRED_NOT_EXECUTED",
        "note": "PV1-INFRA-D2 prepares the 3090 layout and Python SDF/data environment only.",
    }
    sumo_deferred_status = "PASS"

    layout_report = {
        "status": directory_layout_status,
        "boundaries": BOUNDARIES,
        "remote_host": remote_host,
        "remote_root": REMOTE_ROOT,
        "created_or_verified_dirs": remote_dirs_status,
        "mkdir_probe": mkdir_probe,
        "post_setup_probes": probes,
    }
    python_env_report = {
        "status": python_env_gate_status,
        "python_env_status": python_env_status,
        "boundaries": BOUNDARIES,
        "remote_host": remote_host,
        "venv_path": REMOTE_VENV,
        "packages_requested": PYTHON_PACKAGES,
        "missing_packages": missing_packages,
        "install_probe": venv_install,
        "import_probe": import_probe,
        "module_results": module_results,
    }
    sync_plan_report = {
        "status": sync_plan_status,
        "boundaries": BOUNDARIES,
        "run_sync": run_sync,
        "entries": sync_entries,
        "sync_execution": sync_execution,
        "note": "Do not sync large data unless an explicit future --run-sync implementation is approved.",
    }
    replay_report = {
        "status": replay_readiness_status,
        "boundaries": BOUNDARIES,
        "remote_host": remote_host,
        "replay_root": "/data/citybrain/replay",
        "synthetic_root": "/data/citybrain/synthetic",
        "manifest_root": "/data/citybrain/manifests",
        "probe": replay_probe,
        "ready_for": ["file-backed replay packs", "future event-fabric materializer"],
    }

    baseline_after = {name: tree_fingerprint(path) for name, path in accepted_paths.items()}
    no_mutation_report = {
        "status": "PASS" if baseline_before == baseline_after else "FAIL",
        "boundaries": BOUNDARIES,
        "accepted_baseline_before": baseline_before,
        "accepted_baseline_after": baseline_after,
        "mutated_accepted_outputs": [name for name in baseline_before if baseline_before[name] != baseline_after[name]],
        "note": "PV1-INFRA-D2 writes only its own output directory locally and creates safe 3090 runtime directories/venv remotely.",
    }

    write_json(out / "PV1_INFRA_D2_3090_LAYOUT_REPORT.json", layout_report)
    write_json(out / "PV1_INFRA_D2_PYTHON_ENV_REPORT.json", python_env_report)
    write_json(out / "PV1_INFRA_D2_SDF_SYNC_PLAN.json", sync_plan_report)
    write_json(out / "PV1_INFRA_D2_REPLAY_READINESS_REPORT.json", replay_report)
    write_json(out / "PV1_INFRA_D2_SUMO_DEFERRAL_REPORT.json", sumo_deferred_report)
    write_json(out / "PV1_INFRA_D2_NO_MUTATION_REPORT.json", no_mutation_report)
    write_json(out / "PV1_INFRA_D2_REMOTE_COMMAND_LOG.json", {"status": "PASS" if ssh_status == "PASS" else "FAIL", "boundaries": BOUNDARIES, "commands": command_log})

    no_overclaim_report = no_overclaim_scan(out)
    write_json(out / "PV1_INFRA_D2_NO_OVERCLAIM_REPORT.json", no_overclaim_report)

    final_status = "PASS_3090_RUNTIME_BOOTSTRAPPED"
    if not precond_ok or ssh_status != "PASS" or directory_layout_status != "PASS" or replay_readiness_status != "PASS" or sync_plan_status != "PASS" or no_mutation_report["status"] != "PASS" or no_overclaim_report["status"] != "PASS":
        final_status = "FAIL"
    elif python_env_status != "PASS":
        final_status = "PASS_WITH_PYTHON_ENV_LIMITATIONS"

    gates = [
        {"gate": "PV1-INFRA-D2-PRECOND", "status": "PASS" if precond_ok else "FAIL"},
        {"gate": "PV1-INFRA-D2-SSH", "status": ssh_status},
        {"gate": "PV1-INFRA-D2-DIRECTORY-LAYOUT", "status": directory_layout_status},
        {"gate": "PV1-INFRA-D2-PYTHON-ENV", "status": python_env_status},
        {"gate": "PV1-INFRA-D2-REPLAY-READINESS", "status": replay_readiness_status},
        {"gate": "PV1-INFRA-D2-SYNC-PLAN", "status": sync_plan_status},
        {"gate": "PV1-INFRA-D2-SUMO-DEFERRED", "status": sumo_deferred_status},
        {"gate": "PV1-INFRA-D2-NO-OVERCLAIM", "status": no_overclaim_report["status"]},
        {"gate": "PV1-INFRA-D2-NO-MUTATION", "status": no_mutation_report["status"]},
        {"gate": "PV1-INFRA-D2-HASHES", "status": "PENDING"},
    ]

    make_readme(out / "README.md", final_status)
    harness_report = {
        "status": final_status,
        "generated_at_utc": GENERATED_AT_UTC,
        "boundaries": BOUNDARIES,
        "remote_host": remote_host,
        "remote_root": REMOTE_ROOT,
        "venv_path": REMOTE_VENV,
        "run_sync": run_sync,
        "gates": gates,
        "output_dir": str(out),
        "output_dir_relative": str(Path(output_dir)),
    }
    write_json(out / "PV1_INFRA_D2_HARNESS_REPORT.json", harness_report)
    hashes = write_hashes(out)
    for gate in gates:
        if gate["gate"] == "PV1-INFRA-D2-HASHES":
            gate["status"] = "PASS" if hashes else "FAIL"
    harness_report["gates"] = gates
    harness_report["hash_count"] = len(hashes)
    write_json(out / "PV1_INFRA_D2_HARNESS_REPORT.json", harness_report)
    hashes = write_hashes(out)

    artifact_status = all((out / name).exists() for name in REQUIRED_ARTIFACTS)
    result = {
        "status": final_status if artifact_status else "FAIL",
        "generated_at_utc": GENERATED_AT_UTC,
        "boundaries": BOUNDARIES,
        "ssh_status": ssh_status,
        "directory_layout_status": directory_layout_status,
        "python_env_status": python_env_status,
        "python_env_gate_status": python_env_gate_status,
        "missing_packages": missing_packages,
        "replay_readiness_status": replay_readiness_status,
        "sync_plan_status": sync_plan_status,
        "sumo_deferred_status": sumo_deferred_status,
        "no_overclaim_status": no_overclaim_report["status"],
        "no_mutation_status": no_mutation_report["status"],
        "hashes_status": "PASS" if hashes else "FAIL",
        "artifact_status": "PASS" if artifact_status else "FAIL",
        "output_dir": str(out),
        "output_dir_relative": str(Path(output_dir)),
    }
    result["final_print"] = final_print_block(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-INFRA-D2 3090 runtime layout bootstrap.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--remote-host", default=REMOTE_HOST)
    parser.add_argument("--run-sync", action="store_true")
    args = parser.parse_args()
    result = run_pv1_infra_d2_gate(project_root=args.project_root, output_dir=args.output_dir, remote_host=args.remote_host, run_sync=args.run_sync)
    print(result["final_print"])
    print(json.dumps({"status": result["status"], "output_dir": result["output_dir"], "missing_packages": result["missing_packages"]}, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS_3090_RUNTIME_BOOTSTRAPPED", "PASS_WITH_PYTHON_ENV_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
