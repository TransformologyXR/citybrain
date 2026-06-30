"""
A5-D6 live NeMo/NIM replay gate for the governed CityBrain oracle wrapper.

This gate copies the accepted D5/D4 inputs to DGX Spark, registers exactly one
NeMo Agent Toolkit function named citybrain_oracle_core, runs hero/second/
negative prompts through live NAT + NIM, and pulls the replay transcript back.
"""

from __future__ import annotations

import argparse
import hashlib
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from txr_citybrain_a5d1_operator_query import BOUNDARY_STATEMENT
from txr_citybrain_a5d5_nemo_oracle_wrapper import (
    HERO_PROMPT,
    NEGATIVE_PROMPT,
    PUBLIC_TOOL_NAME,
    SECOND_SUBJECT_PROMPT,
    canonical_json,
    hash_tree,
    load_json_file,
    output_hashes,
    sha256_file,
    sha256_payload,
    write_json,
    write_text,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_D5_DIR = ROOT / "outputs" / "a5d5_nemo_oracle_wrapper"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "a5d6_live_nemo_nim_replay"
DEFAULT_REMOTE_HOST = "spark"
DEFAULT_REMOTE_DIR = "/home/txr/works/citybrain-a5d6-live-replay"
DEFAULT_NAT_VENV = "/home/txr/works/nemo-agent-toolkit/.venv"
DEFAULT_NIM_ENDPOINT = "http://127.0.0.1:8000/v1"
DEFAULT_NIM_MODEL = "meta/llama-3.1-8b-instruct"
TASK_NAME = "A5-D6 Live NeMo/NIM Replay Gate"

LOW_LEVEL_TOOL_NAMES = [
    "parcel_profile",
    "building_profile",
    "complaint_search",
    "permit_search",
    "party_search",
    "reachability",
]

REMOTE_REQUIRED_OUTPUTS = [
    "a5_dob_district_enrichment",
    "a5d1_operator_query",
    "a5d2_spark_portability_pack",
    "a5d4a_evidence_grounding_core",
    "a5d4b_request_trace_core",
    "a5d5_nemo_oracle_wrapper",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 600) -> dict[str, Any]:
    started = utc_now()
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return {
            "command": cmd,
            "cwd": str(cwd) if cwd else None,
            "started_at": started,
            "finished_at": utc_now(),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "status": "PASS" if result.returncode == 0 else "FAIL",
        }
    except subprocess.SubprocessError as exc:
        return {
            "command": cmd,
            "cwd": str(cwd) if cwd else None,
            "started_at": started,
            "finished_at": utc_now(),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "status": "FAIL",
        }


def report_pass(path: Path) -> tuple[bool, dict[str, Any]]:
    if not path.exists():
        return False, {}
    payload = load_json_file(path)
    return payload.get("status") == "PASS" and payload.get("exit_code") == 0, payload


def input_paths_from_d5(d5_dir: Path) -> dict[str, Path]:
    d5_report = load_json_file(d5_dir / "A5D5_HARNESS_REPORT.json")
    inputs = d5_report.get("inputs", {})
    paths = {
        "a5d5": d5_dir,
        "a5d4a": ROOT / "outputs" / "a5d4a_evidence_grounding_core",
        "a5d4b": ROOT / "outputs" / "a5d4b_request_trace_core",
        "a5d2": ROOT / "outputs" / "a5d2_spark_portability_pack",
        "a5d1": ROOT / "outputs" / "a5d1_operator_query",
        "a4d2": ROOT / "outputs" / "a5_dob_district_enrichment",
    }
    mapping = {
        "a5d4a": inputs.get("a5d4a"),
        "a5d4b": inputs.get("a5d4b"),
        "a5d2": inputs.get("a5d2"),
        "a5d1": inputs.get("a5d1"),
        "a4d2": inputs.get("a4d2"),
    }
    for key, value in mapping.items():
        if not value:
            continue
        candidate = Path(value)
        if candidate.exists():
            paths[key] = candidate
        else:
            root_candidate = ROOT / value
            if root_candidate.exists():
                paths[key] = root_candidate
    return paths


def preconditions(d5_dir: Path) -> tuple[bool, dict[str, Path], dict[str, Any], list[str]]:
    details: list[str] = []
    paths = input_paths_from_d5(d5_dir) if (d5_dir / "A5D5_HARNESS_REPORT.json").exists() else {"a5d5": d5_dir}
    checks = {
        "a5d5": report_pass(d5_dir / "A5D5_HARNESS_REPORT.json"),
        "a5d4a": report_pass(paths.get("a5d4a", ROOT / "missing") / "A5D4A_HARNESS_REPORT.json"),
        "a5d4b": report_pass(paths.get("a5d4b", ROOT / "missing") / "A5D4B_HARNESS_REPORT.json"),
        "a5d2": report_pass(paths.get("a5d2", ROOT / "missing") / "A5D2_HARNESS_REPORT.json"),
    }
    reports = {key: value[1] for key, value in checks.items()}
    for key, (ok, _) in checks.items():
        if not ok:
            details.append(f"{key} harness report missing or not PASS")
    combined = canonical_json(reports)
    if BOUNDARY_STATEMENT not in combined:
        details.append("boundary statement missing from prerequisite reports")
    d5_report = reports.get("a5d5") or {}
    if d5_report.get("checks", {}).get("live_nim") not in {"SKIPPED", True}:
        details.append("D5 live NIM prerequisite state is unexpected")
    return not details, paths, reports, details


def copytree_clean(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def patch_copied_reports(project_root: Path) -> None:
    d4b_report_path = project_root / "outputs" / "a5d4b_request_trace_core" / "A5D4B_HARNESS_REPORT.json"
    if d4b_report_path.exists():
        report = load_json_file(d4b_report_path)
        report["inputs"] = {
            "a4d2_dir": "outputs/a5_dob_district_enrichment",
            "a5d1_dir": "outputs/a5d1_operator_query",
            "a5d2_dir": "outputs/a5d2_spark_portability_pack",
            "a5d4a_dir": "outputs/a5d4a_evidence_grounding_core",
        }
        write_json(d4b_report_path, report)

    d4a_report_path = project_root / "outputs" / "a5d4a_evidence_grounding_core" / "A5D4A_HARNESS_REPORT.json"
    if d4a_report_path.exists():
        report = load_json_file(d4a_report_path)
        report["inputs"] = {
            "a4d2_dir": "outputs/a5_dob_district_enrichment",
            "a5d1_dir": "outputs/a5d1_operator_query",
        }
        for entry in (report.get("evidence_bundles") or {}).values():
            for key, value in list(entry.items()):
                if isinstance(value, str) and "outputs" in value:
                    entry[key] = value.replace("\\", "/")
        write_json(d4a_report_path, report)


def nat_plugin_py() -> str:
    return r'''"""Live NAT wrapper exposing exactly one CityBrain tool."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import Field

from nat.plugin_api import Builder
from nat.plugin_api import FunctionBaseConfig
from nat.plugin_api import FunctionInfo
from nat.plugin_api import LLMFrameworkEnum
from nat.plugin_api import register_function


class CityBrainOracleCoreConfig(FunctionBaseConfig, name="citybrain_oracle_core"):
    project_root: str = Field(description="Path to the copied CityBrain project root.")
    input_dir: str = Field(description="Path to copied A5-D4B accepted input.")
    output_dir: str = Field(description="Path where D5 wrapper outputs are written.")
    nim_endpoint: str = Field(default="http://127.0.0.1:8000/v1")
    nim_model: str = Field(default="meta/llama-3.1-8b-instruct")
    allow_nim_narration: bool = Field(default=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _label(operator_query: str, bbl: str) -> str:
    text = operator_query.lower()
    if "stop-work" in text or "stop work" in text or "all dob history" in text or "full nyc history" in text:
        return "negative_enforcement"
    if bbl == "1010607502":
        return "hero"
    if bbl == "1010600029":
        return "second_subject"
    return "adhoc"


def _counts(output: dict) -> dict:
    bundle = output.get("evidence_bundle") or {}
    return bundle.get("counts") or {}


@register_function(config_type=CityBrainOracleCoreConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def citybrain_oracle_core_function(config: CityBrainOracleCoreConfig, _builder: Builder):
    async def _citybrain_oracle_core(operator_query: str) -> str:
        """Call the governed CityBrain oracle core once for the original operator request."""

        query_text = str(operator_query)
        if query_text.strip().startswith("{"):
            try:
                parsed = ast.literal_eval(query_text)
                if isinstance(parsed, dict):
                    query_text = str(parsed.get("operator_query") or parsed.get("query") or query_text)
            except (SyntaxError, ValueError):
                pass
        project_root = Path(config.project_root)
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from txr_citybrain_a5d5_nemo_oracle_wrapper import citybrain_oracle_core
        from txr_citybrain_a5d5_nemo_oracle_wrapper import prompt_to_tool_input

        tool_input = prompt_to_tool_input(query_text, allow_nim_narration=config.allow_nim_narration)
        bbl = str(tool_input.get("bbl") or "")
        run_label = _label(query_text, bbl)
        output = citybrain_oracle_core(
            tool_input,
            input_dir=config.input_dir,
            output_dir=config.output_dir,
            run_label=run_label,
            use_nim=config.allow_nim_narration,
            nim_endpoint=config.nim_endpoint,
            nim_model=config.nim_model,
        )

        invocation_dir = Path(config.output_dir) / "nat_tool_invocations"
        invocation_dir.mkdir(parents=True, exist_ok=True)
        invocation_path = invocation_dir / f"{run_label}.json"
        summary = {
            "timestamp": _utc_now(),
            "public_tool_name": "citybrain_oracle_core",
            "operator_query": query_text,
            "bbl": bbl,
            "run_label": run_label,
            "status": output.get("status"),
            "rejected": output.get("rejected"),
            "counts": _counts(output),
            "grounding_status": (output.get("grounding_result") or {}).get("status"),
            "trace_id": (output.get("trace") or {}).get("run_id"),
            "nim_call_statuses": [call.get("status") for call in ((output.get("trace") or {}).get("nim_calls") or [])],
            "output": output,
        }
        invocation_path.write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        return json.dumps(
            {
                "status": "PASS",
                "oracle_status": summary["status"],
                "rejected": summary["rejected"],
                "public_tool_name": summary["public_tool_name"],
                "run_label": summary["run_label"],
                "counts": summary["counts"],
                "grounding_status": summary["grounding_status"],
                "trace_id": summary["trace_id"],
                "invocation_path": str(invocation_path),
            },
            sort_keys=True,
            ensure_ascii=False,
        )

    yield FunctionInfo.from_fn(
        _citybrain_oracle_core,
        description=(
            "The only public CityBrain tool. Call exactly once with the complete original operator "
            "request. It validates the request, executes deterministic CityBrain evidence retrieval, "
            "uses NIM only for evidence-bound narration, and returns a trace-backed summary."
        ),
    )
'''


def nat_pyproject() -> str:
    return """[build-system]\nrequires = [\"setuptools>=64\"]\nbuild-backend = \"setuptools.build_meta\"\n\n[project]\nname = \"citybrain-a5d6-nat-live\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11,<3.14\"\ndescription = \"A5-D6 live CityBrain NAT wrapper\"\n\n[project.entry-points.'nat.components']\ncitybrain_a5d6_nat_live = \"citybrain_a5d6_nat_live.register\"\n"""


def nat_workflow(remote_dir: str, nim_endpoint: str, nim_model: str) -> str:
    project_root = f"{remote_dir}/citybrain_project"
    output_dir = f"{remote_dir}/remote_results/d5_live_wrapper_outputs"
    return f"""workflow:\n  _type: citybrain_oracle_core\n  project_root: {project_root}\n  input_dir: {project_root}/outputs/a5d4b_request_trace_core\n  output_dir: {output_dir}\n  nim_endpoint: {nim_endpoint}\n  nim_model: {nim_model}\n  allow_nim_narration: true\n"""


def remote_runner_py() -> str:
    return r'''from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROMPTS = {
    "hero": "What is happening at parcel 1010607502, what changed, who's responsible, with evidence?",
    "second_subject": "What is happening at parcel 1010600029, what changed, who's responsible, with evidence?",
    "negative": "Issue a stop-work order for parcel 1010607502 and tell me all DOB history for NYC.",
}
BOUNDARY = "DOB enrichment is built from the current harvested DOB subset, capped and deduped across sample/chunk files, not full NYC DOB history. Counts are subset counts."
LOW_LEVEL_TOOLS = ["parcel_profile", "building_profile", "complaint_search", "permit_search", "party_search", "reachability"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def patch_reports(project_root: Path) -> None:
    d4b = project_root / "outputs/a5d4b_request_trace_core/A5D4B_HARNESS_REPORT.json"
    if d4b.exists():
        payload = read_json(d4b)
        payload["inputs"] = {
            "a4d2_dir": "outputs/a5_dob_district_enrichment",
            "a5d1_dir": "outputs/a5d1_operator_query",
            "a5d2_dir": "outputs/a5d2_spark_portability_pack",
            "a5d4a_dir": "outputs/a5d4a_evidence_grounding_core",
        }
        write_json(d4b, payload)
    d4a = project_root / "outputs/a5d4a_evidence_grounding_core/A5D4A_HARNESS_REPORT.json"
    if d4a.exists():
        payload = read_json(d4a)
        payload["inputs"] = {
            "a4d2_dir": "outputs/a5_dob_district_enrichment",
            "a5d1_dir": "outputs/a5d1_operator_query",
        }
        for entry in (payload.get("evidence_bundles") or {}).values():
            for key, value in list(entry.items()):
                if isinstance(value, str):
                    entry[key] = value.replace("\\", "/")
        write_json(d4a, payload)


def run(cmd: list[str], cwd: Path, env: dict | None = None, timeout: int = 300) -> dict:
    started = utc_now()
    try:
        result = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
        return {
            "command": cmd,
            "cwd": str(cwd),
            "started_at": started,
            "finished_at": utc_now(),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "status": "PASS" if result.returncode == 0 else "FAIL",
        }
    except subprocess.SubprocessError as exc:
        return {
            "command": cmd,
            "cwd": str(cwd),
            "started_at": started,
            "finished_at": utc_now(),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "status": "FAIL",
        }


def tool_call_names(stdout: str, stderr: str) -> list[str]:
    text = strip_ansi(stdout + "\n" + stderr)
    names = []
    for match in re.findall(r"Workflow Type:\s*([A-Za-z0-9_]+)", text):
        names.append(match.strip())
    for match in re.findall(r"Calling tools:\s*([A-Za-z0-9_, -]+)", text):
        for piece in re.split(r"[, ]+", match.strip()):
            if piece:
                names.append(piece)
    for match in re.findall(r"Action:\s*([A-Za-z0-9_]+)", text):
        names.append(match.strip())
    return sorted(set(names))


def run_one(label: str, prompt: str, remote_root: Path, nat_bin: Path, env: dict) -> dict:
    command = [str(nat_bin), "run", "--config_file", str(remote_root / "workflow_citybrain_oracle_live.yml"), "--input", prompt]
    proc = run(command, remote_root, env=env, timeout=300)
    invocation_label = "negative_enforcement" if label == "negative" else label
    invocation_path = remote_root / "remote_results/d5_live_wrapper_outputs/nat_tool_invocations" / f"{invocation_label}.json"
    invocation = read_json(invocation_path) if invocation_path.exists() else {}
    return {
        "label": label,
        "prompt": prompt,
        "nat_process": proc,
        "nat_stdout_clean": strip_ansi(proc.get("stdout", "")),
        "nat_stderr_clean": strip_ansi(proc.get("stderr", "")),
        "observed_nemo_tool_calls": tool_call_names(proc.get("stdout", ""), proc.get("stderr", "")),
        "tool_invocation_path": str(invocation_path),
        "tool_invocation": invocation,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-root", required=True)
    parser.add_argument("--nat-venv", required=True)
    args = parser.parse_args()

    remote_root = Path(args.remote_root)
    nat_venv = Path(args.nat_venv)
    nat_python = nat_venv / "bin/python"
    nat_bin = nat_venv / "bin/nat"
    project_root = remote_root / "citybrain_project"
    results_dir = remote_root / "remote_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    patch_reports(project_root)

    dependency_check = run(
        [
            str(nat_python),
            "-c",
            "import pandas, pyarrow, yaml, pydantic; print(pandas.__version__); print(pyarrow.__version__)",
        ],
        remote_root,
        timeout=60,
    )
    dependency_install = {"status": "SKIPPED", "reason": "dependencies already import"}
    if dependency_check.get("returncode") != 0 and "pyarrow" in (dependency_check.get("stderr") or ""):
        dependency_install = run([str(nat_python), "-m", "pip", "install", "pyarrow"], remote_root, timeout=300)
        dependency_check = run(
            [
                str(nat_python),
                "-c",
                "import pandas, pyarrow, yaml, pydantic; print(pandas.__version__); print(pyarrow.__version__)",
            ],
            remote_root,
            timeout=60,
        )
    install = run([str(nat_python), "-m", "pip", "install", "-e", str(remote_root / "nat_citybrain_a5d6_live_plugin")], remote_root, timeout=180)

    env = os.environ.copy()
    env["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
    env["PYTHONUNBUFFERED"] = "1"
    runs = {label: run_one(label, prompt, remote_root, nat_bin, env) for label, prompt in PROMPTS.items()}

    workflow_text = (remote_root / "workflow_citybrain_oracle_live.yml").read_text(encoding="utf-8")
    public_tool_names = re.findall(r"tool_names:\s*\[([^\]]+)\]", workflow_text)
    configured_tools = []
    for entry in public_tool_names:
        configured_tools.extend(piece.strip() for piece in entry.split(",") if piece.strip())
    if not configured_tools:
        workflow_type = re.search(r"workflow:\s*\n\s*_type:\s*([A-Za-z0-9_]+)", workflow_text)
        if workflow_type:
            configured_tools = [workflow_type.group(1)]

    audit = {
        "configured_public_tools": configured_tools,
        "forbidden_low_level_public_hits": [name for name in LOW_LEVEL_TOOLS if re.search(rf"\b{name}\b", workflow_text)],
        "run_tool_calls": {label: run.get("observed_nemo_tool_calls", []) for label, run in runs.items()},
        "plugin_tool": "citybrain_oracle_core",
        "boundary_statement": BOUNDARY,
    }
    grounding = {}
    for label, run_payload in runs.items():
        output = (run_payload.get("tool_invocation") or {}).get("output") or {}
        counts = ((output.get("evidence_bundle") or {}).get("counts") or {})
        trace = output.get("trace") or {}
        grounding[label] = {
            "status": output.get("status"),
            "rejected": output.get("rejected"),
            "grounding_status": (output.get("grounding_result") or {}).get("status"),
            "trace_id": trace.get("run_id"),
            "counts": counts,
            "nim_calls": trace.get("nim_calls") or [],
            "tool_calls": trace.get("tool_calls") or [],
            "validation_result": trace.get("validation_result"),
            "boundary_present": BOUNDARY in json.dumps(output, sort_keys=True, ensure_ascii=False),
        }
    transcript = {
        "task": "A5-D6 Live NeMo/NIM Replay Gate",
        "generated_at": utc_now(),
        "dependency_check": dependency_check,
        "dependency_install": dependency_install,
        "plugin_install": install,
        "nemo_tool_call_audit": audit,
        "groundedness_report": grounding,
        "runs": runs,
    }
    write_json(results_dir / "A5D6_LIVE_TRANSCRIPT.json", transcript)
    write_json(results_dir / "A5D6_GROUNDEDNESS_REPORT.json", grounding)
    write_json(results_dir / "A5D6_NEMO_TOOL_CALL_AUDIT.json", audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def build_remote_bundle(output_dir: Path, paths: dict[str, Path], remote_dir: str, nim_endpoint: str, nim_model: str) -> Path:
    bundle = output_dir / "remote_bundle"
    if bundle.exists():
        shutil.rmtree(bundle)
    project = bundle / "citybrain_project"
    project.mkdir(parents=True, exist_ok=True)
    for source in sorted(ROOT.glob("txr_citybrain_*.py")):
        if source.name == Path(__file__).name:
            continue
        shutil.copy2(source, project / source.name)
    outputs_dir = project / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    source_outputs = {
        "a5_dob_district_enrichment": paths["a4d2"],
        "a5d1_operator_query": paths["a5d1"],
        "a5d2_spark_portability_pack": paths["a5d2"],
        "a5d4a_evidence_grounding_core": paths["a5d4a"],
        "a5d4b_request_trace_core": paths["a5d4b"],
        "a5d5_nemo_oracle_wrapper": paths["a5d5"],
    }
    for name in REMOTE_REQUIRED_OUTPUTS:
        copytree_clean(source_outputs[name], outputs_dir / name)
    patch_copied_reports(project)

    plugin_pkg = bundle / "nat_citybrain_a5d6_live_plugin"
    package_dir = plugin_pkg / "citybrain_a5d6_nat_live"
    package_dir.mkdir(parents=True, exist_ok=True)
    write_text(plugin_pkg / "pyproject.toml", nat_pyproject())
    write_text(package_dir / "__init__.py", "")
    write_text(package_dir / "register.py", nat_plugin_py())
    write_text(bundle / "workflow_citybrain_oracle_live.yml", nat_workflow(remote_dir, nim_endpoint, nim_model))
    write_text(bundle / "run_live_replay_remote.py", remote_runner_py())
    return bundle


def zip_dir(source: Path, dest_zip: Path) -> None:
    if dest_zip.exists():
        dest_zip.unlink()
    with zipfile.ZipFile(dest_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            archive.write(path, path.relative_to(source).as_posix())


def extract_zip(source_zip: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source_zip) as archive:
        archive.extractall(dest)


def collect_remote_results(output_dir: Path, remote_host: str, remote_dir: str) -> tuple[dict[str, Any], dict[str, Any]]:
    zip_remote_cmd = [
        "ssh",
        remote_host,
        f"cd {remote_dir} && python3 -m zipfile -c remote_results.zip remote_results",
    ]
    zip_cmd = run_cmd(zip_remote_cmd, timeout=300)
    local_zip = output_dir / "remote_results.zip"
    scp_cmd = run_cmd(["scp", f"{remote_host}:{remote_dir}/remote_results.zip", str(local_zip)], timeout=300)
    if local_zip.exists():
        extract_zip(local_zip, output_dir / "spark_remote_results")
    return zip_cmd, scp_cmd


def source_contains_low_level_public_tools(bundle: Path) -> list[str]:
    texts = []
    for rel in [
        "workflow_citybrain_oracle_live.yml",
        "nat_citybrain_a5d6_live_plugin/citybrain_a5d6_nat_live/register.py",
        "nat_citybrain_a5d6_live_plugin/pyproject.toml",
    ]:
        path = bundle / rel
        if path.exists():
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
    text = "\n".join(texts)
    return [name for name in LOW_LEVEL_TOOL_NAMES if re.search(rf"\b{name}\b", text)]


def counts_from_live(run: dict[str, Any]) -> dict[str, Any]:
    output = ((run.get("tool_invocation") or {}).get("output") or {})
    bundle = output.get("evidence_bundle") or {}
    return bundle.get("counts") or {}


def live_output(run: dict[str, Any]) -> dict[str, Any]:
    return ((run.get("tool_invocation") or {}).get("output") or {})


def all_live_tool_calls_are_single_public(transcript: dict[str, Any]) -> tuple[bool, list[str]]:
    details: list[str] = []
    audit = transcript.get("nemo_tool_call_audit") or {}
    configured = audit.get("configured_public_tools") or []
    if configured != [PUBLIC_TOOL_NAME]:
        details.append(f"configured tools are {configured}")
    for label, calls in (audit.get("run_tool_calls") or {}).items():
        if calls != [PUBLIC_TOOL_NAME]:
            details.append(f"{label} observed calls {calls}")
    return not details, details


def no_low_level_bypass(transcript: dict[str, Any], bundle: Path) -> tuple[bool, list[str]]:
    details = source_contains_low_level_public_tools(bundle)
    audit_hits = ((transcript.get("nemo_tool_call_audit") or {}).get("forbidden_low_level_public_hits") or [])
    details.extend(f"audit:{hit}" for hit in audit_hits)
    return not details, details


def gate(gate_id: str, name: str, passed: bool, details: list[str] | None = None, status: str | None = None) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "status": status or ("PASS" if passed else "FAIL"),
        "checked": 1,
        "failed": 0 if passed else 1,
        "details": details or [],
    }


def build_readme(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# A5-D6 Live NeMo/NIM Replay Gate",
            "",
            f"Status: {report['status']}.",
            "",
            "a5 = Action Core / NeMo+NIM / DGX Spark.",
            "a5-D6 = live NeMo/NIM replay gate over the accepted D5 governed wrapper.",
            "a5-D5 = NeMo wrapper for governed CityBrain oracle core.",
            "a5-D4B = thin request validator + complete trace.",
            "a4-D2 = DOB district enrichment.",
            "",
            BOUNDARY_STATEMENT,
            "",
            "## Live Replay",
            "",
            f"- Spark host: `{report['spark']['remote_host']}`.",
            f"- Remote directory: `{report['spark']['remote_dir']}`.",
            f"- Public NeMo tool: `{PUBLIC_TOOL_NAME}` only.",
            f"- Hero live status: `{report['live_summary']['hero']['status']}`.",
            f"- Second-subject live status: `{report['live_summary']['second_subject']['status']}`.",
            f"- Negative request: `{report['live_summary']['negative']['status']}`.",
            "",
            "NAT may emit non-blocking OpenTelemetry/protobuf plugin warnings on this Spark environment. D6 sets `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` for the live run.",
            "",
        ]
    )


def run_a5d6_gate(
    input_dir: str = str(DEFAULT_D5_DIR),
    output_dir: str = str(DEFAULT_OUTPUT_DIR),
    remote_host: str = DEFAULT_REMOTE_HOST,
    remote_dir: str = DEFAULT_REMOTE_DIR,
    nat_venv: str = DEFAULT_NAT_VENV,
    nim_endpoint: str = DEFAULT_NIM_ENDPOINT,
    nim_model: str = DEFAULT_NIM_MODEL,
) -> dict[str, Any]:
    d5_dir = Path(input_dir)
    out = Path(output_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    precond_ok, paths, prereq_reports, precond_details = preconditions(d5_dir)
    paths["a5d5"] = d5_dir
    frozen_paths = {
        "a5d5": paths["a5d5"],
        "a5d4b": paths["a5d4b"],
        "a5d4a": paths["a5d4a"],
        "a5d2": paths["a5d2"],
        "a5d1": paths["a5d1"],
        "a4d2": paths["a4d2"],
    }
    before_hashes = {name: hash_tree(path) for name, path in frozen_paths.items()}

    ssh_probe = run_cmd(["ssh", remote_host, "hostname && whoami && test -x /home/txr/works/nemo-agent-toolkit/.venv/bin/nat"], timeout=60)
    nim_probe = run_cmd(["ssh", remote_host, "curl -sS --max-time 10 http://127.0.0.1:8000/v1/models"], timeout=60)
    bundle = build_remote_bundle(out, paths, remote_dir, nim_endpoint, nim_model)
    bundle_zip = out / "a5d6_remote_bundle.zip"
    zip_dir(bundle, bundle_zip)

    remote_prepare = run_cmd(
        [
            "ssh",
            remote_host,
            (
                "python3 -c \"import pathlib, shutil; "
                f"p=pathlib.Path('{remote_dir}'); "
                f"assert str(p).startswith('/home/txr/works/'); "
                "shutil.rmtree(p, ignore_errors=True); p.mkdir(parents=True, exist_ok=True)\""
            ),
        ],
        timeout=120,
    )
    scp_bundle = run_cmd(["scp", str(bundle_zip), f"{remote_host}:{remote_dir}/remote_bundle.zip"], timeout=300)
    remote_extract = run_cmd(["ssh", remote_host, f"cd {remote_dir} && python3 -m zipfile -e remote_bundle.zip ."], timeout=300)
    remote_run = run_cmd(
        [
            "ssh",
            remote_host,
            f"cd {remote_dir} && {nat_venv}/bin/python run_live_replay_remote.py --remote-root {remote_dir} --nat-venv {nat_venv}",
        ],
        timeout=1200,
    )
    zip_back, scp_back = collect_remote_results(out, remote_host, remote_dir)

    transcript_path = out / "spark_remote_results" / "remote_results" / "A5D6_LIVE_TRANSCRIPT.json"
    grounding_path = out / "spark_remote_results" / "remote_results" / "A5D6_GROUNDEDNESS_REPORT.json"
    audit_path = out / "spark_remote_results" / "remote_results" / "A5D6_NEMO_TOOL_CALL_AUDIT.json"
    transcript = load_json_file(transcript_path) if transcript_path.exists() else {}
    grounding_report = load_json_file(grounding_path) if grounding_path.exists() else {}
    tool_audit = load_json_file(audit_path) if audit_path.exists() else {}
    runs = transcript.get("runs") or {}

    hero = runs.get("hero") or {}
    second = runs.get("second_subject") or {}
    negative = runs.get("negative") or {}
    hero_output = live_output(hero)
    second_output = live_output(second)
    negative_output = live_output(negative)
    hero_counts = counts_from_live(hero)
    second_counts = counts_from_live(second)
    hero_sources = hero_counts.get("source_rows", {})
    second_sources = second_counts.get("source_rows", {})
    hero_pass = (
        (hero.get("nat_process") or {}).get("returncode") == 0
        and hero_output.get("status") == "PASS"
        and (hero_output.get("grounding_result") or {}).get("status") == "PASS"
        and hero_sources.get("dob_permit_issuance") == 1
        and hero_sources.get("dob_now_filings") == 12
        and hero_sources.get("dob_complaints") == 9
        and BOUNDARY_STATEMENT in canonical_json(hero_output)
    )
    second_text = canonical_json(second_output)
    second_pass = (
        (second.get("nat_process") or {}).get("returncode") == 0
        and second_output.get("status") == "PASS"
        and (second_output.get("grounding_result") or {}).get("status") == "PASS"
        and second_sources.get("dob_permit_issuance") == 5
        and second_sources.get("dob_now_filings") == 0
        and second_sources.get("dob_complaints") == 6
        and "1010607502" not in second_text
        and BOUNDARY_STATEMENT in second_text
    )
    negative_trace = negative_output.get("trace") or {}
    negative_reasons = ((negative_trace.get("validation_result") or {}).get("reasons") or [])
    negative_pass = (
        (negative.get("nat_process") or {}).get("returncode") == 0
        and negative_output.get("status") == "FAIL"
        and negative_output.get("rejected") is True
        and not (negative_trace.get("tool_calls") or [])
        and any("full-history" in reason for reason in negative_reasons)
        and any("enforcement" in reason or "action" in reason for reason in negative_reasons)
        and BOUNDARY_STATEMENT in canonical_json(negative_output)
    )

    live_nim_details: list[str] = []
    for label, output in [("hero", hero_output), ("second_subject", second_output)]:
        calls = ((output.get("trace") or {}).get("nim_calls") or [])
        if not calls:
            live_nim_details.append(f"{label} had no NIM calls")
        elif not all(call.get("status") == "PASS" and call.get("mode") == "nim" for call in calls):
            live_nim_details.append(f"{label} NIM calls not all PASS: {calls}")
    live_nim_pass = not live_nim_details
    single_tool_pass, single_tool_details = all_live_tool_calls_are_single_public(transcript)
    no_bypass_pass, no_bypass_details = no_low_level_bypass({"nemo_tool_call_audit": tool_audit}, bundle)
    remote_ok = all(cmd.get("status") == "PASS" for cmd in [ssh_probe, nim_probe, remote_prepare, scp_bundle, remote_extract, remote_run, zip_back, scp_back])
    remote_details = [
        name
        for name, cmd in [
            ("ssh_probe", ssh_probe),
            ("nim_probe", nim_probe),
            ("remote_prepare", remote_prepare),
            ("scp_bundle", scp_bundle),
            ("remote_extract", remote_extract),
            ("remote_run", remote_run),
            ("zip_back", zip_back),
            ("scp_back", scp_back),
        ]
        if cmd.get("status") != "PASS"
    ]

    after_hashes = {name: hash_tree(path) for name, path in frozen_paths.items()}
    no_mutation_pass = before_hashes == after_hashes
    no_mutation_details = [name for name in frozen_paths if before_hashes.get(name) != after_hashes.get(name)]
    owned_text_paths = [
        out / "README.md",
        out / "A5D6_MANIFEST.json",
        out / "A5D6_HARNESS_REPORT.json",
        out / "A5D6_LIVE_TRANSCRIPT.json",
        out / "A5D6_GROUNDEDNESS_REPORT.json",
        out / "A5D6_NEMO_TOOL_CALL_AUDIT.json",
        out / "remote_bundle" / "workflow_citybrain_oracle_live.yml",
        out / "remote_bundle" / "run_live_replay_remote.py",
        out / "remote_bundle" / "nat_citybrain_a5d6_live_plugin" / "citybrain_a5d6_nat_live" / "register.py",
    ]
    boundary_outputs_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in owned_text_paths
        if path.exists()
    )
    boundary_pass = BOUNDARY_STATEMENT in boundary_outputs_text and BOUNDARY_STATEMENT in canonical_json(transcript)
    naming_bad = []
    if re.search(r"\bA6\b", boundary_outputs_text):
        naming_bad.append("A6 reference found")
    if "DOB enrichment is A5" in boundary_outputs_text or "DOB district enrichment is A5" in boundary_outputs_text:
        naming_bad.append("DOB enrichment called A5")

    gates = [
        gate("A5D6-PRECOND", "Accepted D5, D4A, D4B, and D2 inputs are PASS", precond_ok, precond_details),
        gate("A5D6-SPARK-SSH", "Spark SSH, NIM endpoint, and NAT venv are reachable", remote_ok, remote_details),
        gate("A5D6-LIVE-NEMO-SINGLE-TOOL", "Live NeMo/NAT calls only citybrain_oracle_core", single_tool_pass, single_tool_details),
        gate("A5D6-NO-LOW-LEVEL-BYPASS", "No low-level query tools are exposed to NeMo", no_bypass_pass, no_bypass_details),
        gate("A5D6-LIVE-NIM", "D5 governed wrapper records successful live NIM narration calls", live_nim_pass, live_nim_details),
        gate("A5D6-HERO-GROUNDED", "Hero live replay remains grounded with expected counts", hero_pass),
        gate("A5D6-SECOND-SUBJECT-GROUNDED", "Second-subject live replay remains grounded without hero leakage", second_pass),
        gate("A5D6-NEGATIVE-REJECTED", "Negative request rejects before deterministic execution", negative_pass, negative_reasons),
        gate("A5D6-TRANSCRIPT-SAVED", "Live transcript, tool-call audit, and groundedness report are saved", transcript_path.exists() and grounding_path.exists() and audit_path.exists()),
        gate("A5D6-BOUNDARY", "Boundary statement is preserved in human/result artifacts", boundary_pass),
        gate("A5D6-NO-MUTATION", "Accepted local input artifacts remain byte-stable", no_mutation_pass, no_mutation_details),
        gate("A5D6-NAMING", "Naming remains unambiguous", not naming_bad, naming_bad),
    ]

    checks = {g["gate_id"].lower().replace("a5d6-", "").replace("-", "_"): g["passed"] for g in gates}
    live_summary = {
        "hero": {
            "status": hero_output.get("status"),
            "grounding_status": (hero_output.get("grounding_result") or {}).get("status"),
            "source_rows": hero_sources,
            "nemo_tool_calls": (tool_audit.get("run_tool_calls") or {}).get("hero"),
            "nim_calls": [call.get("status") for call in ((hero_output.get("trace") or {}).get("nim_calls") or [])],
        },
        "second_subject": {
            "status": second_output.get("status"),
            "grounding_status": (second_output.get("grounding_result") or {}).get("status"),
            "source_rows": second_sources,
            "nemo_tool_calls": (tool_audit.get("run_tool_calls") or {}).get("second_subject"),
            "nim_calls": [call.get("status") for call in ((second_output.get("trace") or {}).get("nim_calls") or [])],
        },
        "negative": {
            "status": negative_output.get("status"),
            "rejected": negative_output.get("rejected"),
            "nemo_tool_calls": (tool_audit.get("run_tool_calls") or {}).get("negative"),
            "deterministic_tool_calls": negative_trace.get("tool_calls") or [],
            "reasons": negative_reasons,
        },
    }

    report = {
        "task": TASK_NAME,
        "status": "PASS" if all(g["passed"] for g in gates) else "FAIL",
        "exit_code": 0 if all(g["passed"] for g in gates) else 1,
        "generated_at": utc_now(),
        "boundary_statement": BOUNDARY_STATEMENT,
        "inputs": {key: str(path) for key, path in frozen_paths.items()},
        "spark": {
            "remote_host": remote_host,
            "remote_dir": remote_dir,
            "nat_venv": nat_venv,
            "nim_endpoint": nim_endpoint,
            "nim_model": nim_model,
        },
        "checks": checks,
        "gates": gates,
        "live_summary": live_summary,
        "nemo_tool_call_audit": tool_audit,
        "groundedness_report_path": str(grounding_path),
        "transcript_path": str(transcript_path),
        "remote_commands": {
            "ssh_probe": ssh_probe,
            "nim_probe": nim_probe,
            "remote_prepare": remote_prepare,
            "scp_bundle": scp_bundle,
            "remote_extract": remote_extract,
            "remote_run": remote_run,
            "zip_back": zip_back,
            "scp_back": scp_back,
        },
        "prerequisite_reports": {
            key: {
                "status": report.get("status"),
                "exit_code": report.get("exit_code"),
            }
            for key, report in prereq_reports.items()
        },
    }
    write_json(out / "A5D6_LIVE_TRANSCRIPT.json", transcript)
    write_json(out / "A5D6_GROUNDEDNESS_REPORT.json", grounding_report)
    write_json(out / "A5D6_NEMO_TOOL_CALL_AUDIT.json", tool_audit)
    write_json(out / "A5D6_MANIFEST.json", {
        "task": TASK_NAME,
        "status": report["status"],
        "generated_at": report["generated_at"],
        "boundary_statement": BOUNDARY_STATEMENT,
        "public_nemo_tool": PUBLIC_TOOL_NAME,
        "spark": report["spark"],
        "outputs": {
            "harness_report": "A5D6_HARNESS_REPORT.json",
            "live_transcript": "A5D6_LIVE_TRANSCRIPT.json",
            "groundedness_report": "A5D6_GROUNDEDNESS_REPORT.json",
            "tool_call_audit": "A5D6_NEMO_TOOL_CALL_AUDIT.json",
        },
        "naming": {
            "a5": "Action Core / NeMo+NIM / DGX Spark",
            "a5-D6": "live NeMo/NIM replay gate",
            "a5-D5": "NeMo wrapper for governed CityBrain oracle core",
            "a5-D4B": "thin request validator + complete trace",
            "a4-D2": "DOB district enrichment",
        },
    })
    write_text(out / "README.md", build_readme(report))
    write_json(out / "A5D6_HARNESS_REPORT.json", report)
    write_json(out / "SHA256SUMS.json", output_hashes(out))

    sha_ok = True
    sha_details: list[str] = []
    recorded = load_json_file(out / "SHA256SUMS.json")
    actual = output_hashes(out)
    for key, value in actual.items():
        if recorded.get(key) != value:
            sha_ok = False
            sha_details.append(key)
    sha_gate = gate("A5D6-HASHES", "SHA256SUMS covers generated artifacts except itself", sha_ok, sha_details)
    report["gates"].append(sha_gate)
    report["checks"]["hashes"] = sha_gate["passed"]
    report["status"] = "PASS" if all(g["passed"] for g in report["gates"]) else "FAIL"
    report["exit_code"] = 0 if report["status"] == "PASS" else 1
    write_json(out / "A5D6_HARNESS_REPORT.json", report)
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    return report


def print_report(report: dict[str, Any]) -> None:
    checks = report.get("checks", {})
    live = report.get("live_summary", {})
    print(f"A5-D6 Live NeMo/NIM Replay Gate: {report.get('status')}")
    print(f"Input A5-D5: {report.get('prerequisite_reports', {}).get('a5d5', {}).get('status')}")
    print(f"Spark host: {report.get('spark', {}).get('remote_host')}")
    print(f"Output: {DEFAULT_OUTPUT_DIR}")
    print("")
    print("Checks:")
    for key in [
        "precond",
        "spark_ssh",
        "live_nemo_single_tool",
        "no_low_level_bypass",
        "live_nim",
        "hero_grounded",
        "second_subject_grounded",
        "negative_rejected",
        "transcript_saved",
        "boundary",
        "no_mutation",
        "naming",
        "hashes",
    ]:
        print(f"- {key.replace('_', ' ')}: {'PASS' if checks.get(key) else 'FAIL'}")
    print("")
    print(f"Hero source rows: {((live.get('hero') or {}).get('source_rows') or {})}")
    print(f"Second-subject source rows: {((live.get('second_subject') or {}).get('source_rows') or {})}")
    print(f"Negative rejected: {(live.get('negative') or {}).get('rejected')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A5-D6 live NeMo/NIM replay gates.")
    parser.add_argument("--input-dir", default=str(DEFAULT_D5_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--remote-host", default=DEFAULT_REMOTE_HOST)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--nat-venv", default=DEFAULT_NAT_VENV)
    parser.add_argument("--nim-endpoint", default=DEFAULT_NIM_ENDPOINT)
    parser.add_argument("--nim-model", default=DEFAULT_NIM_MODEL)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_a5d6_gate(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        remote_host=args.remote_host,
        remote_dir=args.remote_dir,
        nat_venv=args.nat_venv,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
    )
    print_report(report)
    return int(report.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
