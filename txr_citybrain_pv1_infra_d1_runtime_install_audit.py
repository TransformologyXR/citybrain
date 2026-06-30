from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_OUTPUT_DIR = "outputs/pv1_infra_d1_runtime_install_audit"
EXPECTED_NIM_MODEL = "meta/llama-3.1-8b-instruct"
GENERATED_AT_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

BOUNDARIES = [
    "PV1-INFRA-D1 is an audit and placement task.",
    "PV1-INFRA-D1 does not install heavy runtimes automatically.",
    "PV1-INFRA-D1 does not complete Platform v1.",
    "PV1-INFRA-D1 does not start event fabric, simulator, HITL, personas, or perception.",
    "Spark remains the brain/orchestration box.",
    "3090 remains the data/SDF/simulation box.",
    "4070 remains the face/perception box.",
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

REQUIRED_TOP_LEVEL_ARTIFACTS = [
    "README.md",
    "PV1_INFRA_D1_HARNESS_REPORT.json",
    "PV1_INFRA_D1_MACHINE_INVENTORY.json",
    "PV1_INFRA_D1_RUNTIME_PLACEMENT_REPORT.json",
    "PV1_INFRA_D1_SPARK_AUDIT.json",
    "PV1_INFRA_D1_3090_AUDIT.json",
    "PV1_INFRA_D1_4070_AUDIT.json",
    "PV1_INFRA_D1_5090_LOCAL_AUDIT.json",
    "PV1_INFRA_D1_SDF_READINESS_REPORT.json",
    "PV1_INFRA_D1_EVENT_FABRIC_READINESS_REPORT.json",
    "PV1_INFRA_D1_SUMO_READINESS_REPORT.json",
    "PV1_INFRA_D1_PERSONA_HITL_READINESS_REPORT.json",
    "PV1_INFRA_D1_GUARDRAIL_READINESS_REPORT.json",
    "PV1_INFRA_D1_PERCEPTION_DEFERRAL_REPORT.json",
    "PV1_INFRA_D1_INSTALL_GAP_REPORT.json",
    "PV1_INFRA_D1_SAFE_INSTALL_PLAN.md",
    "PV1_INFRA_D1_NO_OVERCLAIM_REPORT.json",
    "PV1_INFRA_D1_NO_MUTATION_REPORT.json",
    "PV1_INFRA_D1_ADAPTER_HANDOVER.md",
    "SHA256SUMS.json",
]

REQUIRED_REPORT_ARTIFACTS = [
    "ssh_probe_results.json",
    "docker_gpu_probe_results.json",
    "nvidia_smi_results.json",
    "python_env_probe_results.json",
    "service_endpoint_probe_results.json",
    "port_probe_results.json",
    "filesystem_layout_report.json",
    "recommended_next_runtime_tasks.json",
]

MODULE_IMPORTS = {
    "pydantic": "pydantic",
    "jsonschema": "jsonschema",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "httpx": "httpx",
    "jinja2": "jinja2",
    "numpy": "numpy",
    "pandas": "pandas",
    "polars": "polars",
    "pyarrow": "pyarrow",
    "duckdb": "duckdb",
    "geopandas": "geopandas",
    "shapely": "shapely",
    "pyogrio": "pyogrio",
    "pyproj": "pyproj",
    "networkx": "networkx",
    "tqdm": "tqdm",
    "rich": "rich",
    "cudf": "cudf",
    "cugraph": "cugraph",
    "cuspatial": "cuspatial",
    "nat": "nat",
    "nemo_agent_toolkit": "nemo_agent_toolkit",
    "nemoguardrails": "nemoguardrails",
}


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


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for file_path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        if file_path.name == "SHA256SUMS.json":
            continue
        hashes[file_path.relative_to(output_dir).as_posix()] = sha256_file(file_path)
    write_json(output_dir / "SHA256SUMS.json", hashes)
    return hashes


def now_ms() -> int:
    return int(time.time() * 1000)


def truncate(text: str, limit: int = 12000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def redact(text: str) -> str:
    patterns = [
        re.compile(r"(?i)(password|api[_ -]?key|token|secret|credential)\s*[:=]\s*([^\s,;]+)"),
        re.compile(r"(?i)(bearer)\s+([A-Za-z0-9._\-]{12,})"),
        re.compile(r"nvapi-[A-Za-z0-9_\-]{12,}"),
    ]
    value = text
    for pattern in patterns:
        value = pattern.sub(lambda m: f"{m.group(1)}=<redacted>" if m.groups() else "<redacted>", value)
    return value


def run_cmd(args: list[str], timeout: int = 20) -> dict[str, Any]:
    started = now_ms()
    try:
        proc = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
        return {
            "command": args,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout": redact(truncate(proc.stdout)),
            "stderr": redact(truncate(proc.stderr)),
            "duration_ms": now_ms() - started,
        }
    except FileNotFoundError as exc:
        return {
            "command": args,
            "returncode": None,
            "ok": False,
            "stdout": "",
            "stderr": str(exc),
            "duration_ms": now_ms() - started,
        }
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


def ssh_cmd(host: str, command: str, timeout: int = 20) -> dict[str, Any]:
    return run_cmd(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6", host, command], timeout=timeout)


def probe_ssh(machine: str, candidates: list[str]) -> dict[str, Any]:
    attempts = []
    for candidate in candidates:
        result = ssh_cmd(candidate, "hostname; uname -a; uname -m; whoami", timeout=10)
        attempts.append({"candidate": candidate, "result": result})
        if result["ok"]:
            lines = [line.strip() for line in result["stdout"].splitlines() if line.strip()]
            return {
                "machine": machine,
                "status": "PASS",
                "selected_host": candidate,
                "hostname": lines[0] if len(lines) > 0 else None,
                "uname": lines[1] if len(lines) > 1 else None,
                "arch": lines[2] if len(lines) > 2 else None,
                "user": lines[3] if len(lines) > 3 else None,
                "attempts": attempts,
            }
    return {"machine": machine, "status": "SSH_UNAVAILABLE", "selected_host": None, "attempts": attempts}


def http_probe(url: str, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 8) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method)
    started = now_ms()
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read(512_000).decode("utf-8", errors="replace")
            parsed = None
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = None
            return {
                "url": url,
                "method": method,
                "ok": 200 <= response.status < 400,
                "status_code": response.status,
                "body": redact(truncate(body)),
                "json": parsed,
                "duration_ms": now_ms() - started,
            }
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "url": url,
            "method": method,
            "ok": False,
            "status_code": exc.code,
            "body": redact(truncate(body)),
            "json": None,
            "stderr": str(exc),
            "duration_ms": now_ms() - started,
        }
    except Exception as exc:
        return {
            "url": url,
            "method": method,
            "ok": False,
            "status_code": None,
            "body": "",
            "json": None,
            "stderr": str(exc),
            "duration_ms": now_ms() - started,
        }


def parse_json_from_stdout(result: dict[str, Any]) -> Any:
    if not result.get("ok"):
        return None
    text = result.get("stdout", "").strip()
    try:
        return json.loads(text)
    except Exception:
        return None


def python_import_code(modules: list[str]) -> str:
    pairs = {name: MODULE_IMPORTS[name] for name in modules}
    return (
        "import importlib.util, importlib.metadata as m, json;"
        f"mods={json.dumps(pairs, sort_keys=True)};"
        "out={};"
        "any_missing=False;"
        "\nfor name, mod in mods.items():\n"
        "    spec=importlib.util.find_spec(mod)\n"
        "    if spec is None:\n"
        "        out[name]={'present':False,'version':None}\n"
        "    else:\n"
        "        try: ver=m.version(name)\n"
        "        except Exception:\n"
        "            try: ver=m.version(mod)\n"
        "            except Exception: ver='unknown'\n"
        "        out[name]={'present':True,'version':ver}\n"
        "print(json.dumps(out, sort_keys=True))"
    )


def local_python_probe(modules: list[str]) -> dict[str, Any]:
    result = run_cmd([sys.executable, "-c", python_import_code(modules)], timeout=20)
    return {"python": sys.executable, "result": result, "modules": parse_json_from_stdout(result)}


def remote_python_probe(host: str | None, python_candidates: list[str], modules: list[str]) -> dict[str, Any]:
    if not host:
        return {"status": "NOT_PROBED", "reason": "SSH unavailable", "candidates": python_candidates}
    code = python_import_code(modules).replace("'", "'\"'\"'")
    attempts = []
    for py in python_candidates:
        cmd = f"if command -v {py} >/dev/null 2>&1 || test -x {py}; then {py} -c '{code}'; else echo PYTHON_CANDIDATE_MISSING; exit 127; fi"
        result = ssh_cmd(host, cmd, timeout=30)
        attempts.append({"python": py, "result": result, "modules": parse_json_from_stdout(result)})
        if result["ok"] and parse_json_from_stdout(result):
            return {"status": "PASS", "selected_python": py, "attempts": attempts, "modules": parse_json_from_stdout(result)}
    return {"status": "MISSING", "selected_python": None, "attempts": attempts, "modules": None}


def remote_probe(host: str | None, label: str, command: str, timeout: int = 20) -> dict[str, Any]:
    if not host:
        return {"label": label, "status": "NOT_PROBED", "reason": "SSH unavailable"}
    result = ssh_cmd(host, command, timeout=timeout)
    return {"label": label, "status": "PASS" if result["ok"] else "FAIL", "result": result}


def command_status_from_probe(probe: dict[str, Any]) -> str:
    if probe.get("status") == "NOT_PROBED":
        return "NOT_PROBED"
    return "PASS" if probe.get("result", {}).get("ok") else "MISSING"


def module_status(probe: dict[str, Any], required: list[str]) -> str:
    modules = probe.get("modules") or {}
    if not modules:
        return "UNKNOWN" if probe.get("status") == "NOT_PROBED" else "MISSING"
    return "PASS" if all((modules.get(name) or {}).get("present") for name in required) else "MISSING"


def any_module_present(probe: dict[str, Any], names: list[str]) -> bool:
    modules = probe.get("modules") or {}
    return any((modules.get(name) or {}).get("present") for name in names)


def runtime_present(probe: dict[str, Any], positive_markers: list[str]) -> bool:
    text = ((probe.get("result") or {}).get("stdout") or "") + "\n" + ((probe.get("result") or {}).get("stderr") or "")
    lowered = text.lower()
    if not lowered.strip():
        return False
    if "command not found" in lowered or "no such file" in lowered:
        image_lines = [line for line in lowered.splitlines() if any(marker in line for marker in positive_markers) and "command not found" not in line]
        return bool(image_lines)
    return any(marker in lowered for marker in positive_markers)


def local_path_report(project_root: Path) -> dict[str, Any]:
    paths = {
        "project_root": project_root,
        "sdf_umbrella": project_root / "outputs/pv1_sdf_synthetic_data_factory",
        "sdf_pack": project_root / "data_synthetic/pv1_sdf/packs/sdf_chi_near_west_side_v1",
        "a9_snapshot": project_root / "outputs/a9_wire_e2e_g1_snapshot",
        "chicago_outputs": project_root / "outputs",
        "sdf_replay_packs": project_root / "data_synthetic/pv1_sdf/packs/sdf_chi_near_west_side_v1/replay_packs",
        "sdf_action_proposals": project_root / "data_synthetic/pv1_sdf/packs/sdf_chi_near_west_side_v1/truth/synthetic_action_proposals.parquet",
    }
    return {name: {"path": str(path), "exists": path.exists(), "is_dir": path.is_dir()} for name, path in paths.items()}


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def list_files(path: Path, patterns: list[str] | None = None, limit: int = 200) -> list[str]:
    if not path.exists():
        return []
    files: list[Path] = []
    if patterns:
        for pattern in patterns:
            files.extend(path.rglob(pattern))
    else:
        files = list(path.rglob("*"))
    return [str(p) for p in sorted(set(files)) if p.is_file()][:limit]


def evidence_counts(project_root: Path) -> dict[str, Any]:
    outputs = project_root / "outputs"
    evidence_files = list_files(outputs, ["*evidence*.json", "*Evidence*.json", "*grounding*.json"], limit=500)
    city_hits = {
        "nyc": sum(1 for path in evidence_files if "nyc" in path.lower() or "a5" in path.lower()),
        "london": sum(1 for path in evidence_files if "lon" in path.lower() or "london" in path.lower()),
        "chicago": sum(1 for path in evidence_files if "chi" in path.lower() or "chicago" in path.lower()),
    }
    return {"evidence_file_count": len(evidence_files), "city_hits": city_hits, "sample_files": evidence_files[:30]}


def build_runtime_placement() -> dict[str, Any]:
    return {
        "status": "PASS_RUNTIME_AUDIT",
        "boundaries": BOUNDARIES,
        "assignments": {
            "Spark": {
                "required_now": ["NIM", "NeMo Agent Toolkit or existing wrapper runtime", "NeMo Guardrails or install gap", "lightweight tool wrapper Python env"],
                "required_later": ["live guardrail gate", "Incident/Plan orchestrator", "persona narration wrapper"],
                "explicitly_not_here": ["RAPIDS", "SDF bulk generation", "SUMO", "DeepStream/Triton"],
            },
            "3090": {
                "required_now": ["SDF Python env", "data/replay filesystem", "RAPIDS/cudf/cugraph/cuspatial if available"],
                "required_next": ["event-fabric materializer", "replay/current-state processor", "SUMO install candidate"],
                "required_later": ["cuOpt for real optimization families"],
                "explicitly_not_here": ["face layer", "NIM primary runtime"],
            },
            "4070": {
                "required_now": ["Caddy/Node face serving", "citybrain face deploy path"],
                "required_next": ["synthetic/replay face route placeholders"],
                "required_later": ["Triton/DeepStream minimum perception path"],
                "explicitly_not_here": ["SDF bulk generation", "SUMO", "NIM primary runtime"],
            },
            "5090 laptop": {
                "required_now": ["control/orchestration", "manual 3D/Omniverse work"],
                "required_next": ["bridge/publish artifacts"],
                "explicitly_not_here": ["production hosting"],
            },
        },
    }


def final_print_block(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"PV1-INFRA-D1 Platform v1 Runtime Placement + Install Audit: {result['status']}",
            "",
            f"Spark audit: {result['spark_audit']['audit_status']}",
            f"Spark NIM: {result['spark_audit']['nim_status']}",
            f"Spark NeMo Agent Toolkit: {result['spark_audit']['nemo_agent_toolkit_status']}",
            f"Spark Guardrails: {result['spark_audit']['guardrails_status']}",
            "",
            f"3090 audit: {result['box3090_audit']['audit_status']}",
            f"3090 Docker GPU: {result['box3090_audit']['docker_gpu_status']}",
            f"3090 RAPIDS: {result['box3090_audit']['rapids_status']}",
            f"3090 SDF env: {result['box3090_audit']['sdf_env_status']}",
            f"3090 SUMO: {result['box3090_audit']['sumo_status']}",
            "",
            f"4070 audit: {result['box4070_audit']['audit_status']}",
            f"4070 face layer: {result['box4070_audit']['face_layer_status']}",
            f"4070 synthetic route placeholders: {result['box4070_audit']['synthetic_routes_status']}",
            f"4070 Triton/DeepStream: {result['box4070_audit']['perception_runtime_status']}",
            "",
            f"Local audit: {result['local_audit']['audit_status']}",
            f"SDF readiness: {result['sdf_readiness']['status']}",
            f"Event fabric readiness: {result['event_fabric_readiness']['status']}",
            f"Guardrail readiness: {result['guardrail_readiness']['status']}",
            f"Persona/HITL readiness: {result['persona_hitl_readiness']['status']}",
            f"Install gaps: {result['install_gap_report']['gap_count']}",
            f"No-overclaim: {result['no_overclaim_report']['status']}",
            f"No-mutation: {result['no_mutation_report']['status']}",
            "",
            f"Output: {result['output_dir_relative']}",
        ]
    )


def write_safe_install_plan(path: Path, gap_report: dict[str, Any]) -> None:
    lines = [
        "# PV1-INFRA-D1 Safe Install Plan",
        "",
        *[f"- {boundary}" for boundary in BOUNDARIES],
        "",
        "This plan records install candidates only. No install action was executed by PV1-INFRA-D1.",
        "",
        "## Priorities",
        "",
    ]
    for gap in gap_report["gaps"]:
        if gap["classification"] in {"NEEDED_NEXT", "BLOCKER_NOW"}:
            lines.append(f"- {gap['classification']}: {gap['machine']} - {gap['component']}: {gap['recommendation']}")
    lines.extend(
        [
            "",
            "## Deferred",
            "",
        ]
    )
    for gap in gap_report["gaps"]:
        if gap["classification"] == "DEFERRED":
            lines.append(f"- {gap['machine']} - {gap['component']}: {gap['recommendation']}")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Keep Spark lean: brain, NIM, NeMo, guardrail gate, and tool orchestration.",
            "- Put graph, replay, simulation, and SDF batch work on 3090.",
            "- Put face routes, map serving, and later perception on 4070.",
            "- Start event fabric file-backed with SDF JSONL replay packs before choosing Kafka, Redpanda, or Redis Streams.",
            "- Treat SUMO as the PV1-D10/D11/D12 install candidate, not a PV1-INFRA-D1 requirement.",
        ]
    )
    write_text(path, "\n".join(lines))


def make_adapter_handover(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# PV1-INFRA-D1 Adapter Handover",
        "",
        *[f"- {boundary}" for boundary in BOUNDARIES],
        "",
        "## Runtime Split",
        "",
        "- Spark: brain, governed narration, guardrails, and one-public-tool orchestration.",
        "- 3090: SDF/data/replay/graph/simulation preparation.",
        "- 4070: face layer, map/briefing/trace serving, and later perception runtime.",
        "- 5090 laptop: controller workspace and manual 3D preparation.",
        "",
        "## Next Runtime Tasks",
        "",
    ]
    for task in result["recommended_next_runtime_tasks"]["tasks"]:
        lines.append(f"- {task['machine']}: {task['task']} ({task['classification']})")
    lines.extend(
        [
            "",
            "## Key Audit Outputs",
            "",
            "- Harness: PV1_INFRA_D1_HARNESS_REPORT.json",
            "- Placement: PV1_INFRA_D1_RUNTIME_PLACEMENT_REPORT.json",
            "- Install gaps: PV1_INFRA_D1_INSTALL_GAP_REPORT.json",
            "- Safe plan: PV1_INFRA_D1_SAFE_INSTALL_PLAN.md",
        ]
    )
    write_text(path, "\n".join(lines))


def run_pv1_infra_d1_gate(
    project_root: str,
    output_dir: str,
    spark_host: str = "192.168.1.103",
    box3090_host: str = "192.168.1.148",
    box4070_host: str = "192.168.1.48",
    run_ssh_probes: bool = True,
    run_live_endpoint_probes: bool = True,
    audit_only: bool = True,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = (root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    reports_dir = out / "reports"
    out.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    baseline_paths = {
        "sdf_umbrella": root / "outputs/pv1_sdf_synthetic_data_factory",
        "sdf_pack": root / "data_synthetic/pv1_sdf/packs/sdf_chi_near_west_side_v1",
        "a9_snapshot": root / "outputs/a9_wire_e2e_g1_snapshot",
    }
    baseline_before = {name: tree_fingerprint(path) for name, path in baseline_paths.items()}

    path_report = local_path_report(root)
    sdf_report = read_json(root / "outputs/pv1_sdf_synthetic_data_factory/PV1_SDF_UMBRELLA_HARNESS_REPORT.json", {})
    precond_ok = bool(path_report["sdf_umbrella"]["exists"] and path_report["sdf_pack"]["exists"] and sdf_report.get("status") == "PASS_SYNTHETIC_DATA_FACTORY_D1_D6")

    ssh_results = {
        "spark": {"status": "NOT_PROBED"},
        "3090": {"status": "NOT_PROBED"},
        "4070": {"status": "NOT_PROBED"},
    }
    if run_ssh_probes:
        ssh_results["spark"] = probe_ssh("Spark", ["spark", "dgx-spark", "txr-spark", spark_host])
        ssh_results["3090"] = probe_ssh("3090", ["txr-3090", box3090_host])
        ssh_results["4070"] = probe_ssh("4070", ["txr-4070", box4070_host])

    spark_ssh = ssh_results["spark"].get("selected_host")
    box3090_ssh = ssh_results["3090"].get("selected_host")
    box4070_ssh = ssh_results["4070"].get("selected_host")

    nvidia_smi_results = {
        "spark": remote_probe(spark_ssh, "nvidia-smi", "nvidia-smi", timeout=20),
        "3090": remote_probe(box3090_ssh, "nvidia-smi", "nvidia-smi", timeout=20),
        "4070": remote_probe(box4070_ssh, "nvidia-smi", "nvidia-smi", timeout=20),
        "local": {"label": "nvidia-smi", "result": run_cmd(["nvidia-smi"], timeout=10)},
    }
    docker_version = {
        "spark": remote_probe(spark_ssh, "docker --version", "docker --version", timeout=12),
        "3090": remote_probe(box3090_ssh, "docker --version", "docker --version", timeout=12),
        "4070": remote_probe(box4070_ssh, "docker --version", "docker --version", timeout=12),
        "local": {"label": "docker --version", "result": run_cmd(["docker", "--version"], timeout=10)},
    }
    docker_ps = {
        "spark": remote_probe(spark_ssh, "docker ps", "docker ps --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'", timeout=20),
        "3090": remote_probe(box3090_ssh, "docker ps", "docker ps --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'", timeout=20),
        "4070": remote_probe(box4070_ssh, "docker ps", "docker ps --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'", timeout=20),
    }
    docker_images = {
        "3090": remote_probe(box3090_ssh, "docker image ls", "docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}}' | head -200", timeout=25),
        "4070": remote_probe(box4070_ssh, "docker image ls", "docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}}' | head -200", timeout=25),
    }
    docker_gpu_probe = {
        "spark": {
            "nvidia_smi": nvidia_smi_results["spark"],
            "docker_version": docker_version["spark"],
            "docker_ps": docker_ps["spark"],
            "status": "PASS" if nvidia_smi_results["spark"].get("status") == "PASS" and docker_version["spark"].get("status") == "PASS" else "NOT_PROBED",
            "note": "No GPU container was started by this audit.",
        },
        "3090": {
            "nvidia_smi": nvidia_smi_results["3090"],
            "docker_version": docker_version["3090"],
            "nvidia_container_toolkit": remote_probe(box3090_ssh, "nvidia container toolkit", "nvidia-container-cli --version 2>/dev/null || nvidia-container-runtime --version 2>/dev/null || docker info 2>/dev/null | grep -i nvidia", timeout=15),
            "status": "PASS" if nvidia_smi_results["3090"].get("status") == "PASS" and docker_version["3090"].get("status") == "PASS" else ("NOT_PROBED" if not box3090_ssh else "FAIL"),
            "note": "No GPU container was started by this audit.",
        },
        "4070": {
            "nvidia_smi": nvidia_smi_results["4070"],
            "docker_version": docker_version["4070"],
            "nvidia_container_toolkit": remote_probe(box4070_ssh, "nvidia container toolkit", "nvidia-container-cli --version 2>/dev/null || nvidia-container-runtime --version 2>/dev/null || docker info 2>/dev/null | grep -i nvidia", timeout=15),
            "status": "PASS" if nvidia_smi_results["4070"].get("status") == "PASS" and docker_version["4070"].get("status") == "PASS" else ("NOT_PROBED" if not box4070_ssh else "FAIL"),
            "note": "No GPU container was started by this audit.",
        },
    }

    python_env_probes = {
        "spark_tool_wrappers": remote_python_probe(
            spark_ssh,
            ["/home/txr/works/nemo-agent-toolkit/.venv/bin/python", "/home/txr/works/citybrain-guardrails-gate/.venv/bin/python", "python3"],
            ["pydantic", "jsonschema", "fastapi", "uvicorn", "httpx", "jinja2", "numpy", "nat", "nemoguardrails"],
        ),
        "3090_sdf": remote_python_probe(
            box3090_ssh,
            ["/data/citybrain/.venv/bin/python", "/home/txr/works/citybrain/.venv/bin/python", "python3"],
            ["pandas", "polars", "pyarrow", "duckdb", "geopandas", "shapely", "pyogrio", "pyproj", "networkx", "jsonschema", "pydantic", "tqdm", "rich", "numpy", "cudf", "cugraph", "cuspatial"],
        ),
        "4070_face": remote_python_probe(box4070_ssh, ["python3"], ["pydantic", "jsonschema", "fastapi", "uvicorn", "httpx", "jinja2", "numpy"]),
        "local": local_python_probe(["pydantic", "jsonschema", "numpy", "pandas", "pyarrow"]),
    }

    spark_nim_models = http_probe(f"http://{spark_host}:8000/v1/models") if run_live_endpoint_probes else {"ok": False, "status": "NOT_PROBED"}
    if not spark_nim_models.get("ok") and spark_ssh:
        remote_nim = remote_probe(spark_ssh, "remote NIM /v1/models", "curl -fsS http://127.0.0.1:8000/v1/models", timeout=12)
        try:
            remote_nim_json = json.loads(remote_nim.get("result", {}).get("stdout", "{}"))
        except Exception:
            remote_nim_json = None
        spark_nim_models = {
            "url": "ssh:spark:http://127.0.0.1:8000/v1/models",
            "ok": remote_nim.get("status") == "PASS",
            "status_code": 200 if remote_nim.get("status") == "PASS" else None,
            "json": remote_nim_json,
            "remote_probe": remote_nim,
        }
    spark_chat_probe = (
        http_probe(
            f"http://{spark_host}:8000/v1/chat/completions",
            method="POST",
            payload={"model": EXPECTED_NIM_MODEL, "messages": [{"role": "user", "content": "health"}], "max_tokens": 2, "temperature": 0},
            timeout=20,
        )
        if run_live_endpoint_probes and spark_nim_models.get("ok")
        else {"status": "NOT_PROBED", "reason": "models probe not ok or live endpoint probes disabled"}
    )
    guardrail_http_probe = http_probe(f"http://{spark_host}:8010/health") if run_live_endpoint_probes else {"status": "NOT_PROBED"}
    if not guardrail_http_probe.get("ok") and spark_ssh:
        remote_guard = remote_probe(spark_ssh, "remote guardrail /health", "curl -fsS http://127.0.0.1:8010/health", timeout=12)
        try:
            remote_guard_json = json.loads(remote_guard.get("result", {}).get("stdout", "{}"))
        except Exception:
            remote_guard_json = None
        guardrail_http_probe = {
            "url": "ssh:spark:http://127.0.0.1:8010/health",
            "ok": remote_guard.get("status") == "PASS",
            "status_code": 200 if remote_guard.get("status") == "PASS" else None,
            "json": remote_guard_json,
            "remote_probe": remote_guard,
        }

    service_endpoint_probes = {
        "spark_nim_models": spark_nim_models,
        "spark_chat": spark_chat_probe,
        "spark_guardrails_health": guardrail_http_probe,
        "4070": {},
    }
    for route in ["/status.json", "/map/", "/london", "/chicago", "/chicago/heroes", "/api/chicago/heroes", "/synthetic", "/api/synthetic/status"]:
        service_endpoint_probes["4070"][route] = http_probe(f"http://{box4070_host}:8080{route}", timeout=10) if run_live_endpoint_probes else {"status": "NOT_PROBED"}

    port_probe_results = {
        "spark": remote_probe(spark_ssh, "listening ports", "ss -ltnp | head -120", timeout=12),
        "3090": remote_probe(box3090_ssh, "listening ports", "ss -ltnp | head -120", timeout=12),
        "4070": remote_probe(box4070_ssh, "listening ports", "ss -ltnp | head -120", timeout=12),
        "local": {"label": "local netstat", "result": run_cmd(["netstat", "-ano"], timeout=10)},
    }

    spark_nat_probe = remote_probe(
        spark_ssh,
        "NeMo Agent Toolkit",
        "/home/txr/works/nemo-agent-toolkit/.venv/bin/nat --version 2>/dev/null || nat --version 2>/dev/null || /home/txr/works/nemo-agent-toolkit/.venv/bin/python -c 'import nat; print(\"nat import ok\")' 2>/dev/null || python3 -c 'import nat; print(\"nat import ok\")'",
        timeout=20,
    )
    spark_guardrails_probe = remote_probe(
        spark_ssh,
        "NeMo Guardrails",
        "/home/txr/works/citybrain-guardrails-gate/.venv/bin/nemoguardrails --version 2>/dev/null || nemoguardrails --version 2>/dev/null || /home/txr/works/citybrain-guardrails-gate/.venv/bin/python -c 'import nemoguardrails; print(\"nemoguardrails import ok\")' 2>/dev/null || python3 -c 'import nemoguardrails; print(\"nemoguardrails import ok\")'",
        timeout=20,
    )
    spark_wrapper_probe = remote_probe(
        spark_ssh,
        "CityBrain wrapper one public tool",
        "grep -c '@register_function' /home/txr/works/citybrain-a5d6-live-replay/nat_citybrain_a5d6_live_plugin/citybrain_a5d6_nat_live/register.py 2>/dev/null; grep -c 'FunctionInfo.from_fn' /home/txr/works/citybrain-a5d6-live-replay/nat_citybrain_a5d6_live_plugin/citybrain_a5d6_nat_live/register.py 2>/dev/null; test -f /home/txr/works/citybrain-a5d6-live-replay/remote_results/d5_live_wrapper_outputs/nat_tool_invocations/hero.json",
        timeout=12,
    )

    model_ids = []
    if isinstance(spark_nim_models.get("json"), dict):
        model_ids = [entry.get("id") for entry in spark_nim_models["json"].get("data", []) if isinstance(entry, dict)]
    spark_nim_status = "PASS" if spark_nim_models.get("ok") and EXPECTED_NIM_MODEL in model_ids else ("FAIL" if run_live_endpoint_probes else "NOT_PROBED")
    spark_tool_env_status = module_status(python_env_probes["spark_tool_wrappers"], ["pydantic", "jsonschema", "fastapi", "uvicorn", "httpx", "jinja2"])
    spark_nat_status = "PASS" if spark_nat_probe.get("status") == "PASS" else ("UNKNOWN" if not spark_ssh else "MISSING")
    spark_guardrails_status = "PASS" if spark_guardrails_probe.get("status") == "PASS" or guardrail_http_probe.get("ok") else ("UNKNOWN" if not spark_ssh else "MISSING")
    spark_audit_status = "PASS" if spark_nim_status == "PASS" and spark_nat_status == "PASS" else ("SSH_UNAVAILABLE" if not spark_ssh else "FAIL")
    spark_audit = {
        "status": "PASS_RUNTIME_AUDIT" if spark_audit_status == "PASS" else "PASS_WITH_SSH_LIMITATIONS" if spark_audit_status == "SSH_UNAVAILABLE" else "FAIL",
        "audit_status": spark_audit_status,
        "boundaries": BOUNDARIES,
        "ssh": ssh_results["spark"],
        "nvidia_smi": nvidia_smi_results["spark"],
        "docker_version": docker_version["spark"],
        "docker_ps": docker_ps["spark"],
        "nim_status": spark_nim_status,
        "nim_models": model_ids,
        "nim_models_probe": spark_nim_models,
        "chat_probe": spark_chat_probe,
        "nemo_agent_toolkit_status": spark_nat_status,
        "nemo_agent_toolkit_probe": spark_nat_probe,
        "guardrails_status": spark_guardrails_status,
        "guardrails_probe": spark_guardrails_probe,
        "guardrails_health_probe": guardrail_http_probe,
        "tool_wrapper_python_env_status": spark_tool_env_status,
        "tool_wrapper_python_env_probe": python_env_probes["spark_tool_wrappers"],
        "citybrain_tool_contract_probe": spark_wrapper_probe,
        "explicitly_not_assigned": ["RAPIDS", "cuGraph", "cuOpt", "SUMO", "SDF bulk generation", "DeepStream/Triton"],
    }

    remote_3090_fs = remote_probe(
        box3090_ssh,
        "3090 filesystem",
        "for p in /data/citybrain /data/citybrain/outputs /data/citybrain/synthetic /data/citybrain/replay; do if test -e \"$p\"; then echo \"$p PASS\"; else echo \"$p MISSING\"; fi; done",
        timeout=12,
    )
    sumo_probe = remote_probe(box3090_ssh, "SUMO", "sumo --version 2>&1 | head -1; netconvert --version 2>&1 | head -1; duarouter --version 2>&1 | head -1", timeout=15)
    cuopt_probe = remote_probe(box3090_ssh, "cuOpt", "docker image ls --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -Ei 'cuopt|nvidia/cuopt' || true; docker ps --format '{{.Names}} {{.Image}}' 2>/dev/null | grep -Ei 'cuopt|nvidia/cuopt' || true", timeout=15)
    rapids_text = (docker_images["3090"].get("result", {}).get("stdout") or "").lower()
    rapids_import_present = any_module_present(python_env_probes["3090_sdf"], ["cudf", "cugraph", "cuspatial"])
    rapids_status = "PASS" if rapids_import_present or "rapids" in rapids_text else ("UNKNOWN" if not box3090_ssh else "MISSING")
    sdf_env_required = ["pandas", "pyarrow", "duckdb", "networkx", "jsonschema", "pydantic", "tqdm", "numpy"]
    sdf_env_status = module_status(python_env_probes["3090_sdf"], sdf_env_required)
    sumo_status = "PASS" if sumo_probe.get("status") == "PASS" and "not found" not in (sumo_probe.get("result", {}).get("stderr", "") + sumo_probe.get("result", {}).get("stdout", "")).lower() else ("DEFERRED" if box3090_ssh else "UNKNOWN")
    box3090_audit_status = "SSH_UNAVAILABLE" if not box3090_ssh else "PASS"
    box3090_audit = {
        "status": "PASS_WITH_SSH_LIMITATIONS" if not box3090_ssh else "PASS_RUNTIME_AUDIT",
        "audit_status": box3090_audit_status,
        "boundaries": BOUNDARIES,
        "ssh": ssh_results["3090"],
        "nvidia_smi": nvidia_smi_results["3090"],
        "docker_version": docker_version["3090"],
        "docker_ps": docker_ps["3090"],
        "docker_images": docker_images["3090"],
        "docker_gpu_status": docker_gpu_probe["3090"]["status"],
        "docker_gpu_probe": docker_gpu_probe["3090"],
        "rapids_status": rapids_status,
        "sdf_env_status": sdf_env_status,
        "sdf_env_probe": python_env_probes["3090_sdf"],
        "filesystem_probe": remote_3090_fs,
        "sumo_status": sumo_status,
        "sumo_probe": sumo_probe,
        "cuopt_probe": cuopt_probe,
        "explicitly_not_assigned": ["face layer", "NIM primary runtime"],
    }

    node_probe = remote_probe(box4070_ssh, "node npm pnpm", "node --version 2>/dev/null; npm --version 2>/dev/null; pnpm --version 2>/dev/null", timeout=15)
    caddy_probe = remote_probe(box4070_ssh, "caddy", "caddy version 2>/dev/null || command -v caddy || true", timeout=12)
    webroot_probe = remote_probe(
        box4070_ssh,
        "web roots",
        "for p in /var/www /srv /opt/citybrain /home/txr/CityBrain /home/txr/citybrain /home/txr/works /home/txr/DMAgent-4070; do if test -e \"$p\"; then echo \"$p\"; fi; done",
        timeout=12,
    )
    triton_probe = remote_probe(box4070_ssh, "triton", "tritonserver --version 2>&1 | head -2; docker image ls --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -Ei 'triton' || true", timeout=15)
    deepstream_probe = remote_probe(box4070_ssh, "deepstream", "deepstream-app --version 2>&1 | head -2; docker image ls --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -Ei 'deepstream' || true", timeout=15)
    route_statuses = {route: ("PASS" if probe.get("ok") else "MISSING") for route, probe in service_endpoint_probes["4070"].items()}
    face_routes = ["/status.json", "/map/", "/london", "/chicago", "/chicago/heroes", "/api/chicago/heroes"]
    synthetic_routes = ["/synthetic", "/api/synthetic/status"]
    face_layer_status = "PASS" if any(route_statuses.get(route) == "PASS" for route in face_routes) else ("NOT_PROBED" if not run_live_endpoint_probes else "FAIL")
    synthetic_routes_status = "PASS" if all(route_statuses.get(route) == "PASS" for route in synthetic_routes) else "DEFERRED"
    triton_present = runtime_present(triton_probe, ["tritonserver", "triton"])
    deepstream_present = runtime_present(deepstream_probe, ["deepstream-app", "deepstream"])
    perception_runtime_status = "PASS" if triton_present and deepstream_present else "DEFERRED"
    box4070_audit_status = "SSH_UNAVAILABLE" if not box4070_ssh else "PASS"
    box4070_audit = {
        "status": "PASS_WITH_SSH_LIMITATIONS" if not box4070_ssh else "PASS_RUNTIME_AUDIT",
        "audit_status": box4070_audit_status,
        "boundaries": BOUNDARIES,
        "ssh": ssh_results["4070"],
        "nvidia_smi": nvidia_smi_results["4070"],
        "docker_version": docker_version["4070"],
        "docker_ps": docker_ps["4070"],
        "node_probe": node_probe,
        "caddy_probe": caddy_probe,
        "webroot_probe": webroot_probe,
        "http_route_statuses": route_statuses,
        "http_probes": service_endpoint_probes["4070"],
        "face_layer_status": face_layer_status,
        "synthetic_routes_status": synthetic_routes_status,
        "synthetic_routes_note": "SYNTHETIC_ROUTES_NOT_YET_INSTALLED" if synthetic_routes_status != "PASS" else "SYNTHETIC_ROUTES_PRESENT",
        "triton_probe": triton_probe,
        "triton_present": triton_present,
        "deepstream_probe": deepstream_probe,
        "deepstream_present": deepstream_present,
        "perception_runtime_status": perception_runtime_status,
        "explicitly_not_assigned": ["SDF bulk generation", "SUMO", "NIM primary runtime"],
    }

    local_git = run_cmd(["git", "status", "--short"], timeout=15)
    disk = shutil.disk_usage(root)
    local_node = {"node": run_cmd(["node", "--version"], timeout=8), "npm": run_cmd(["npm", "--version"], timeout=8), "pnpm": run_cmd(["pnpm", "--version"], timeout=8)}
    local_audit = {
        "status": "PASS_RUNTIME_AUDIT",
        "audit_status": "PASS" if root.exists() and precond_ok else "FAIL",
        "boundaries": BOUNDARIES,
        "python": {"executable": sys.executable, "version": sys.version, "platform": platform.platform(), "machine": platform.machine()},
        "project_root": str(root),
        "git_status": local_git,
        "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
        "paths": path_report,
        "node": local_node,
        "docker": docker_version["local"],
        "nvidia_smi": nvidia_smi_results["local"],
        "python_env_probe": python_env_probes["local"],
    }

    filesystem_layout_report = {
        "status": "PASS" if precond_ok else "FAIL",
        "boundaries": BOUNDARIES,
        "local_paths": path_report,
        "remote_3090": remote_3090_fs,
        "remote_4070_webroots": webroot_probe,
    }

    replay_pack_dir = root / "data_synthetic/pv1_sdf/packs/sdf_chi_near_west_side_v1/replay_packs"
    replay_packs = list(replay_pack_dir.glob("*.jsonl")) if replay_pack_dir.exists() else []
    sdf_readiness = {
        "status": "PASS" if precond_ok and len(replay_packs) >= 8 else "FAIL",
        "readiness": "SDF_READY_FOR_FILE_BACKED_REPLAY" if precond_ok else "SDF_BASELINE_MISSING",
        "boundaries": BOUNDARIES,
        "sdf_report_status": sdf_report.get("status"),
        "counts": sdf_report.get("counts", {}),
        "replay_pack_count": len(replay_packs),
        "sdf_pack": str(root / "data_synthetic/pv1_sdf/packs/sdf_chi_near_west_side_v1"),
    }
    event_fabric_readiness = {
        "status": "PASS" if len(replay_packs) >= 8 else "FAIL",
        "readiness": "EVENT_FABRIC_READY_FILE_BACKED" if len(replay_packs) >= 8 else "EVENT_FABRIC_REPLAY_PACKS_MISSING",
        "boundaries": BOUNDARIES,
        "jsonl_replay_pack_count": len(replay_packs),
        "current_state_materializer_candidate": "Python file-backed materializer",
        "filesystem_backed_replay_reports": True,
        "recommendation": "Start PV1 event fabric as file-backed JSONL replay/current-state materializer. Delay Redpanda/Kafka/Redis decision until file-backed semantics pass.",
    }
    sumo_readiness = {
        "status": "PASS",
        "SUMO_INSTALLED": "PASS" if sumo_status == "PASS" else "UNKNOWN" if not box3090_ssh else "FAIL",
        "SUMO_NEEDED_FOR": "PV1-D10/D11/D12",
        "RECOMMENDED_FIRST_NETWORK": "Chicago Near West Side OR NYC hero-neighbourhood",
        "INSTALL_ACTION": "deferred install plan, not executed",
        "boundaries": BOUNDARIES,
        "probe": sumo_probe,
    }
    guardrail_readiness_status = "PASS" if spark_nim_status == "PASS" and spark_nat_status == "PASS" and spark_guardrails_status == "PASS" else ("NEEDED_NEXT" if spark_nim_status == "PASS" and spark_nat_status == "PASS" else "FAIL")
    guardrail_readiness = {
        "status": guardrail_readiness_status,
        "boundaries": BOUNDARIES,
        "needs": {
            "NeMo Guardrails": spark_guardrails_status,
            "accepted_query_path": "PASS" if spark_wrapper_probe.get("status") == "PASS" else "UNKNOWN",
            "rejected_query_path": "PASS" if guardrail_http_probe.get("ok") else "UNKNOWN",
            "logs_audit_path": "PASS" if guardrail_http_probe.get("ok") else "UNKNOWN",
            "one_public_tool_discipline": "PASS" if spark_wrapper_probe.get("status") == "PASS" else "UNKNOWN",
        },
        "spark_guardrail_health": guardrail_http_probe,
    }
    ecounts = evidence_counts(root)
    persona_hitl_readiness = {
        "status": "PASS" if sdf_readiness["status"] == "PASS" else "NEEDED_NEXT",
        "persona_status": "PERSONA_READY_FOR_CONTRACT" if sdf_readiness["status"] == "PASS" else "PERSONA_NEEDS_FIXTURES",
        "hitl_status": "HITL_READY_FOR_SCHEMA_AND_STUB" if sdf_readiness["status"] == "PASS" else "HITL_NEEDS_FIXTURES",
        "boundaries": BOUNDARIES,
        "evidence_bundles": ecounts,
        "sdf_action_proposals": path_report["sdf_action_proposals"],
        "sdf_replay_plan_candidate": {"path": str(replay_pack_dir / "replay_plan_mode_candidate.jsonl"), "exists": (replay_pack_dir / "replay_plan_mode_candidate.jsonl").exists()},
        "face_layer_capability": face_layer_status,
    }
    perception_deferral = {
        "status": "PASS",
        "boundaries": BOUNDARIES,
        "Triton": "DEFERRED_OR_MISSING" if perception_runtime_status != "PASS" else "PASS",
        "DeepStream": "DEFERRED_OR_MISSING" if perception_runtime_status != "PASS" else "PASS",
        "needed_for": "future perception path, not SDF/event-fabric next step",
        "triton_probe": triton_probe,
        "deepstream_probe": deepstream_probe,
    }

    gaps: list[dict[str, Any]] = []

    def add_gap(machine: str, component: str, classification: str, evidence: str, recommendation: str) -> None:
        gaps.append(
            {
                "machine": machine,
                "component": component,
                "classification": classification,
                "evidence": evidence,
                "recommendation": recommendation,
            }
        )

    add_gap("Spark", "NIM LLM runtime", "ALREADY_PRESENT" if spark_nim_status == "PASS" else "BLOCKER_NOW", spark_nim_status, "Keep pinned; do not recreate during audit.")
    add_gap("Spark", "NeMo Agent Toolkit", "ALREADY_PRESENT" if spark_nat_status == "PASS" else "BLOCKER_NOW", spark_nat_status, "Install/repair NAT wrapper runtime only if missing.")
    add_gap("Spark", "NeMo Guardrails", "ALREADY_PRESENT" if spark_guardrails_status == "PASS" else "NEEDED_NEXT", spark_guardrails_status, "Install or repair the dedicated live guardrail gate before PV1-D19/D20.")
    add_gap("Spark", "tool-wrapper Python env", "ALREADY_PRESENT" if spark_tool_env_status == "PASS" else "NEEDED_NEXT", spark_tool_env_status, "Provide pydantic/jsonschema/FastAPI/httpx/Jinja2 wrapper env.")
    add_gap("3090", "SSH reachability", "UNKNOWN" if not box3090_ssh else "ALREADY_PRESENT", ssh_results["3090"].get("status", "UNKNOWN"), "Restore SSH/network reachability for live data-factory audits.")
    add_gap("3090", "RAPIDS/cuDF/cuGraph/cuSpatial", "ALREADY_PRESENT" if rapids_status == "PASS" else "NEEDED_NEXT", rapids_status, "Prepare RAPIDS container/env on 3090 for graph/spatial acceleration when PV1 graph/replay requires it.")
    add_gap("3090", "SDF/data Python env", "ALREADY_PRESENT" if sdf_env_status == "PASS" else "NEEDED_NEXT", sdf_env_status, "Install data stack in a project venv or container; do not use system Python.")
    add_gap("3090", "SUMO", "ALREADY_PRESENT" if sumo_status == "PASS" else "NEEDED_NEXT", sumo_status, "Defer SUMO install until PV1-D10/D11/D12 simulator bridge.")
    add_gap("3090", "cuOpt", "OPTIONAL", "not started by audit", "Use later for real optimization families; do not start unless explicitly scoped.")
    add_gap("4070", "face layer serving", "ALREADY_PRESENT" if face_layer_status == "PASS" else "NEEDED_NEXT", face_layer_status, "Restore Caddy/Node routes for map/status/briefing surfaces if missing.")
    add_gap("4070", "synthetic/replay routes", "ALREADY_PRESENT" if synthetic_routes_status == "PASS" else "NEEDED_NEXT", synthetic_routes_status, "Add placeholder routes for SDF/replay visualization.")
    add_gap("4070", "Triton/DeepStream", "DEFERRED", perception_runtime_status, "Defer until minimum perception path is explicitly started.")
    add_gap("Event fabric", "Redpanda/Kafka/Redis Streams", "DEFERRED", "file-backed event fabric recommended first", "Delay broker choice until JSONL semantics pass.")
    add_gap("Future retrieval", "NeMo Retriever/cuVS", "DEFERRED", "not required for PV1-INFRA-D1", "Evaluate after event fabric/current-state semantics stabilize.")
    add_gap("Future generation", "Cosmos", "DEFERRED", "not required for PV1-INFRA-D1", "Evaluate only for later simulation/media generation scope.")
    add_gap("Future curation", "NeMo Curator", "DEFERRED", "not required for PV1-INFRA-D1", "Evaluate only when large-scale corpus curation becomes explicit.")

    install_gap_report = {
        "status": "PASS_WITH_INSTALL_GAPS" if any(g["classification"] in {"NEEDED_NEXT", "UNKNOWN"} for g in gaps) else "PASS_RUNTIME_AUDIT",
        "boundaries": BOUNDARIES,
        "gap_count": sum(1 for g in gaps if g["classification"] != "ALREADY_PRESENT"),
        "gaps": gaps,
    }
    recommended_next_runtime_tasks = {
        "status": "PASS",
        "boundaries": BOUNDARIES,
        "tasks": [
            {"machine": "3090", "task": "Restore/prove SSH reachability, then repeat RAPIDS/SDF/SUMO probes.", "classification": "NEEDED_NEXT" if not box3090_ssh else "OPTIONAL"},
            {"machine": "3090", "task": "Start PV1 event fabric as file-backed JSONL replay/current-state materializer.", "classification": "NEEDED_NEXT"},
            {"machine": "4070", "task": "Add synthetic/replay route placeholders for face-layer visualization.", "classification": "NEEDED_NEXT" if synthetic_routes_status != "PASS" else "ALREADY_PRESENT"},
            {"machine": "3090", "task": "Prepare SUMO install plan for PV1-D10/D11/D12.", "classification": "NEEDED_NEXT"},
            {"machine": "Spark", "task": "Keep NIM/NAT/Guardrails pinned and lean; integrate future live action-policy gate through one public tool.", "classification": "ALREADY_PRESENT" if guardrail_readiness_status == "PASS" else "NEEDED_NEXT"},
        ],
    }

    machine_inventory = {
        "status": "PASS_WITH_SSH_LIMITATIONS" if not box3090_ssh else "PASS_RUNTIME_AUDIT",
        "boundaries": BOUNDARIES,
        "machines": {
            "spark": {"role": "brain / NIM / NeMo / Guardrails / tool-orchestration", "ip": spark_host, "ssh": ssh_results["spark"], "audit": {"nim": spark_nim_status, "nat": spark_nat_status, "guardrails": spark_guardrails_status}},
            "3090": {"role": "data factory / RAPIDS / cuGraph / cuSpatial / cuOpt / SDF / future SUMO", "ip": box3090_host, "ssh": ssh_results["3090"], "audit": {"rapids": rapids_status, "sdf_env": sdf_env_status, "sumo": sumo_status}},
            "4070": {"role": "face layer / Caddy / Node / map / trace / briefing / future perception", "ip": box4070_host, "ssh": ssh_results["4070"], "audit": {"face_layer": face_layer_status, "synthetic_routes": synthetic_routes_status, "perception": perception_runtime_status}},
            "5090_local": {"role": "controller / Codex workspace / Omniverse/manual 3D preparation", "audit": {"local": local_audit["audit_status"]}},
        },
    }

    runtime_placement = build_runtime_placement()
    reports = {
        "PV1_INFRA_D1_MACHINE_INVENTORY.json": machine_inventory,
        "PV1_INFRA_D1_RUNTIME_PLACEMENT_REPORT.json": runtime_placement,
        "PV1_INFRA_D1_SPARK_AUDIT.json": spark_audit,
        "PV1_INFRA_D1_3090_AUDIT.json": box3090_audit,
        "PV1_INFRA_D1_4070_AUDIT.json": box4070_audit,
        "PV1_INFRA_D1_5090_LOCAL_AUDIT.json": local_audit,
        "PV1_INFRA_D1_SDF_READINESS_REPORT.json": sdf_readiness,
        "PV1_INFRA_D1_EVENT_FABRIC_READINESS_REPORT.json": event_fabric_readiness,
        "PV1_INFRA_D1_SUMO_READINESS_REPORT.json": sumo_readiness,
        "PV1_INFRA_D1_PERSONA_HITL_READINESS_REPORT.json": persona_hitl_readiness,
        "PV1_INFRA_D1_GUARDRAIL_READINESS_REPORT.json": guardrail_readiness,
        "PV1_INFRA_D1_PERCEPTION_DEFERRAL_REPORT.json": perception_deferral,
        "PV1_INFRA_D1_INSTALL_GAP_REPORT.json": install_gap_report,
        "reports/ssh_probe_results.json": {"status": machine_inventory["status"], "boundaries": BOUNDARIES, "results": ssh_results},
        "reports/docker_gpu_probe_results.json": {"status": "PASS", "boundaries": BOUNDARIES, "results": docker_gpu_probe},
        "reports/nvidia_smi_results.json": {"status": "PASS", "boundaries": BOUNDARIES, "results": nvidia_smi_results},
        "reports/python_env_probe_results.json": {"status": "PASS", "boundaries": BOUNDARIES, "results": python_env_probes},
        "reports/service_endpoint_probe_results.json": {"status": "PASS", "boundaries": BOUNDARIES, "results": service_endpoint_probes},
        "reports/port_probe_results.json": {"status": "PASS", "boundaries": BOUNDARIES, "results": port_probe_results},
        "reports/filesystem_layout_report.json": filesystem_layout_report,
        "reports/recommended_next_runtime_tasks.json": recommended_next_runtime_tasks,
    }
    for rel, payload in reports.items():
        write_json(out / rel, payload)

    write_safe_install_plan(out / "PV1_INFRA_D1_SAFE_INSTALL_PLAN.md", install_gap_report)

    top_level_without_hash = [name for name in REQUIRED_TOP_LEVEL_ARTIFACTS if name not in {"SHA256SUMS.json", "PV1_INFRA_D1_HARNESS_REPORT.json", "README.md", "PV1_INFRA_D1_NO_OVERCLAIM_REPORT.json", "PV1_INFRA_D1_NO_MUTATION_REPORT.json", "PV1_INFRA_D1_ADAPTER_HANDOVER.md"}]
    artifact_status = all((out / name).exists() for name in top_level_without_hash) and all((reports_dir / name).exists() for name in REQUIRED_REPORT_ARTIFACTS)

    baseline_after = {name: tree_fingerprint(path) for name, path in baseline_paths.items()}
    no_mutation_status = "PASS" if baseline_before == baseline_after else "FAIL"
    no_mutation_report = {
        "status": no_mutation_status,
        "boundaries": BOUNDARIES,
        "audit_only": audit_only,
        "accepted_baseline_before": baseline_before,
        "accepted_baseline_after": baseline_after,
        "mutated_accepted_outputs": [name for name in baseline_before if baseline_before[name] != baseline_after[name]],
        "note": "Only PV1-INFRA-D1 output artifacts are written by this harness.",
    }
    write_json(out / "PV1_INFRA_D1_NO_MUTATION_REPORT.json", no_mutation_report)

    # Write a temporary harness-free adapter handover after the result shell is assembled below.
    gates = [
        {"gate": "PV1-INFRA-D1-PRECOND", "status": "PASS" if precond_ok else "FAIL"},
        {"gate": "PV1-INFRA-D1-MACHINE-INVENTORY", "status": machine_inventory["status"]},
        {"gate": "PV1-INFRA-D1-SPARK-AUDIT", "status": spark_audit["status"]},
        {"gate": "PV1-INFRA-D1-3090-AUDIT", "status": box3090_audit["status"]},
        {"gate": "PV1-INFRA-D1-4070-AUDIT", "status": box4070_audit["status"]},
        {"gate": "PV1-INFRA-D1-LOCAL-AUDIT", "status": local_audit["status"]},
        {"gate": "PV1-INFRA-D1-RUNTIME-PLACEMENT", "status": runtime_placement["status"]},
        {"gate": "PV1-INFRA-D1-SDF-READINESS", "status": "PASS_RUNTIME_AUDIT" if sdf_readiness["status"] == "PASS" else "FAIL"},
        {"gate": "PV1-INFRA-D1-EVENT-FABRIC-READINESS", "status": "PASS_RUNTIME_AUDIT" if event_fabric_readiness["status"] == "PASS" else "FAIL"},
        {"gate": "PV1-INFRA-D1-SUMO-READINESS", "status": "PASS_WITH_INSTALL_GAPS" if sumo_readiness["SUMO_INSTALLED"] != "PASS" else "PASS_RUNTIME_AUDIT"},
        {"gate": "PV1-INFRA-D1-GUARDRAIL-READINESS", "status": "PASS_RUNTIME_AUDIT" if guardrail_readiness_status == "PASS" else "PASS_WITH_INSTALL_GAPS" if guardrail_readiness_status == "NEEDED_NEXT" else "FAIL"},
        {"gate": "PV1-INFRA-D1-PERSONA-HITL-READINESS", "status": "PASS_RUNTIME_AUDIT" if persona_hitl_readiness["status"] == "PASS" else "PASS_WITH_INSTALL_GAPS"},
        {"gate": "PV1-INFRA-D1-INSTALL-GAPS", "status": install_gap_report["status"]},
        {"gate": "PV1-INFRA-D1-NO-MUTATION", "status": "PASS_RUNTIME_AUDIT" if no_mutation_status == "PASS" else "FAIL"},
        {"gate": "PV1-INFRA-D1-HASHES", "status": "PENDING"},
    ]
    allowed_gate_statuses = {"PASS_RUNTIME_AUDIT", "PASS_WITH_INSTALL_GAPS", "PASS_WITH_SSH_LIMITATIONS"}
    blocking_fail = any(g["status"] == "FAIL" for g in gates)
    overall_status = "FAIL" if blocking_fail or not artifact_status else "PASS_WITH_INSTALL_GAPS" if install_gap_report["gap_count"] else "PASS_RUNTIME_AUDIT"

    result_shell = {
        "status": overall_status,
        "generated_at_utc": GENERATED_AT_UTC,
        "audit_only": audit_only,
        "output_dir": str(out),
        "output_dir_relative": str(Path(output_dir)),
        "boundaries": BOUNDARIES,
        "spark_audit": spark_audit,
        "box3090_audit": box3090_audit,
        "box4070_audit": box4070_audit,
        "local_audit": local_audit,
        "sdf_readiness": sdf_readiness,
        "event_fabric_readiness": event_fabric_readiness,
        "guardrail_readiness": guardrail_readiness,
        "persona_hitl_readiness": persona_hitl_readiness,
        "install_gap_report": install_gap_report,
        "recommended_next_runtime_tasks": recommended_next_runtime_tasks,
        "no_mutation_report": no_mutation_report,
    }
    make_adapter_handover(out / "PV1_INFRA_D1_ADAPTER_HANDOVER.md", result_shell)

    readme = [
        "# PV1-INFRA-D1 Runtime Placement + Install Audit",
        "",
        *[f"- {boundary}" for boundary in BOUNDARIES],
        "",
        f"Status: {overall_status}",
        "",
        "This audit records runtime placement, health checks, and installation gaps for the Platform v1 next steps.",
        "",
        "## Key Result",
        "",
        "- Spark is the brain/orchestration runtime.",
        "- 3090 is the data/SDF/simulation runtime.",
        "- 4070 is the face/perception runtime.",
        "- 5090 laptop remains the controller workspace.",
        "",
        "## Reports",
        "",
    ]
    readme.extend(f"- {name}" for name in REQUIRED_TOP_LEVEL_ARTIFACTS if name != "README.md")
    write_text(out / "README.md", "\n".join(readme))

    # No-overclaim scan runs after all prose reports except harness/hash are present.
    overclaim_hits = []
    for file_path in sorted(p for p in out.rglob("*") if p.is_file()):
        if file_path.name in {"PV1_INFRA_D1_NO_OVERCLAIM_REPORT.json", "SHA256SUMS.json"}:
            continue
        text = file_path.read_text(encoding="utf-8", errors="replace")
        for phrase in FORBIDDEN_OVERCLAIMS:
            if phrase.lower() in text.lower():
                overclaim_hits.append({"file": file_path.relative_to(out).as_posix(), "phrase_hash": hashlib.sha256(phrase.encode("utf-8")).hexdigest()})
    no_overclaim_report = {
        "status": "PASS" if not overclaim_hits else "FAIL",
        "boundaries": BOUNDARIES,
        "forbidden_overclaim_hit_count": len(overclaim_hits),
        "hits": overclaim_hits,
        "note": "Forbidden claim phrases are tracked by hash to avoid restating them in the artifact.",
    }
    write_json(out / "PV1_INFRA_D1_NO_OVERCLAIM_REPORT.json", no_overclaim_report)
    gates.insert(-1, {"gate": "PV1-INFRA-D1-NO-OVERCLAIM", "status": "PASS_RUNTIME_AUDIT" if no_overclaim_report["status"] == "PASS" else "FAIL"})
    if no_overclaim_report["status"] != "PASS":
        overall_status = "FAIL"

    hashes = write_hashes(out)
    for gate in gates:
        if gate["gate"] == "PV1-INFRA-D1-HASHES":
            gate["status"] = "PASS_RUNTIME_AUDIT" if hashes else "FAIL"
    if any(g["status"] == "FAIL" for g in gates):
        overall_status = "FAIL"
    elif overall_status != "FAIL":
        overall_status = "PASS_WITH_INSTALL_GAPS" if install_gap_report["gap_count"] else "PASS_RUNTIME_AUDIT"

    harness_report = {
        "status": overall_status,
        "generated_at_utc": GENERATED_AT_UTC,
        "audit_only": audit_only,
        "boundaries": BOUNDARIES,
        "allowed_gate_statuses": sorted(allowed_gate_statuses),
        "gates": gates,
        "artifact_status": "PASS" if artifact_status else "FAIL",
        "required_top_level_artifacts": REQUIRED_TOP_LEVEL_ARTIFACTS,
        "required_report_artifacts": REQUIRED_REPORT_ARTIFACTS,
        "machine_inventory_status": machine_inventory["status"],
        "install_gap_count": install_gap_report["gap_count"],
        "output_dir": str(out),
        "output_dir_relative": str(Path(output_dir)),
    }
    write_json(out / "PV1_INFRA_D1_HARNESS_REPORT.json", harness_report)
    hashes = write_hashes(out)

    result = dict(result_shell)
    result.update(
        {
            "status": overall_status,
            "machine_inventory": machine_inventory,
            "runtime_placement": runtime_placement,
            "sumo_readiness": sumo_readiness,
            "perception_deferral": perception_deferral,
            "no_overclaim_report": no_overclaim_report,
            "no_mutation_report": no_mutation_report,
            "harness_report": harness_report,
            "hashes": hashes,
        }
    )
    result["final_print"] = final_print_block(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-INFRA-D1 runtime placement and install audit.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--spark-host", default="192.168.1.103")
    parser.add_argument("--box3090-host", default="192.168.1.148")
    parser.add_argument("--box4070-host", default="192.168.1.48")
    parser.add_argument("--run-ssh-probes", action="store_true")
    parser.add_argument("--run-live-endpoint-probes", action="store_true")
    parser.add_argument("--audit-only", action="store_true", default=True)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_pv1_infra_d1_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        spark_host=args.spark_host,
        box3090_host=args.box3090_host,
        box4070_host=args.box4070_host,
        run_ssh_probes=args.run_ssh_probes,
        run_live_endpoint_probes=args.run_live_endpoint_probes,
        audit_only=args.audit_only,
    )
    print(result["final_print"])
    print(json.dumps({"status": result["status"], "output_dir": result["output_dir"]}, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS_RUNTIME_AUDIT", "PASS_WITH_INSTALL_GAPS", "PASS_WITH_SSH_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
