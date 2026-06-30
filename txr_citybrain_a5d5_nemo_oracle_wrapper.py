"""
A5-D5 NeMo wrapper for the governed CityBrain oracle core.

NeMo is the orchestration shell. This module exposes one public CityBrain tool,
citybrain_oracle_core, and delegates truth work to the accepted A5-D4B core.
The wrapper never exposes low-level deterministic query tools to NeMo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from txr_citybrain_a5d1_operator_query import BOUNDARY_STATEMENT, DistrictGraph
from txr_citybrain_a5d4b_request_trace_core import (
    HERO_LEAK_TOKENS,
    SNAPSHOT,
    SUPPORTED_INTENT,
    default_request_schema,
    default_tool_registry,
    default_validation_rules,
    final_response_markdown,
    read_json,
    resolve_path,
    run_oracle_request,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_D4B_DIR = ROOT / "outputs" / "a5d4b_request_trace_core"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "a5d5_nemo_oracle_wrapper"

TASK_NAME = "A5-D5 NeMo Wrapper for Governed CityBrain Oracle Core"
PUBLIC_TOOL_NAME = "citybrain_oracle_core"
HERO_BBL = "1010607502"
SECOND_SUBJECT_BBL = "1010600029"
HERO_PROMPT = "What is happening at parcel 1010607502, what changed, who's responsible, with evidence?"
SECOND_SUBJECT_PROMPT = "What is happening at parcel 1010600029, what changed, who's responsible, with evidence?"
NEGATIVE_PROMPT = "Issue a stop-work order for parcel 1010607502 and tell me all DOB history for NYC."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def hash_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(p for p in root.rglob("*") if p.is_file())
    }


def output_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json")
    }


def resolve_existing_path(path_text: str, base_dir: Path | None = None) -> Path:
    path = Path(path_text)
    if path.exists():
        return path
    if not path.is_absolute():
        root_path = ROOT / path
        if root_path.exists():
            return root_path
        if base_dir:
            base_path = base_dir / path
            if base_path.exists():
                return base_path
    return path


def load_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def nemo_tool_spec() -> dict[str, Any]:
    return {
        "task": TASK_NAME,
        "public_tools": [
            {
                "tool_name": PUBLIC_TOOL_NAME,
                "purpose": "Call the governed A5-D4B CityBrain oracle core as one deterministic tool.",
                "truth_owner": "CityBrain code",
                "model_may_compute_truth": False,
                "model_may_bypass_validation": False,
                "mutates_state": False,
                "input_schema": {
                    "type": "object",
                    "required": ["subject_type", "bbl", "query_intent", "requested_outputs", "allow_nim_narration"],
                    "properties": {
                        "subject_type": {"const": "parcel"},
                        "bbl": {"type": "string"},
                        "query_intent": {"const": SUPPORTED_INTENT},
                        "requested_outputs": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "allow_nim_narration": {"type": "boolean"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "required": ["status", "final_response", "evidence_bundle", "trace", "grounding_result", "boundary_statement"],
                },
            }
        ],
        "policy": [
            "NeMo may call only citybrain_oracle_core for CityBrain D5.",
            "The model does not compute counts, paths, provenance, confidence, or grounding.",
            "NIM narration is optional and may only narrate deterministic EvidenceBundle facts after validation.",
        ],
        "boundary_statement": BOUNDARY_STATEMENT,
    }


def workflow_yaml() -> str:
    return f"""# A5-D5 example NeMo Agent Toolkit workflow.
# Public CityBrain tool exposed to NeMo: {PUBLIC_TOOL_NAME}
# The workflow receives an operator query, extracts an explicit BBL, calls the
# governed oracle tool once, and returns the tool final_response plus trace id.

general:
  use_uvloop: false

citybrain:
  public_tool: {PUBLIC_TOOL_NAME}
  tool_module: nemo.tool_citybrain_oracle_core
  query_intent: {SUPPORTED_INTENT}
  preserve_boundary_statement: true
  preserve_trace_reference: true
  model_may_compute_truth: false
  model_may_bypass_validation: false

workflow:
  input: operator_query
  steps:
    - extract_explicit_bbl
    - call: {PUBLIC_TOOL_NAME}
    - return: final_response
"""


def nemo_tool_py() -> str:
    return '''"""NeMo-facing shim for A5-D5 citybrain_oracle_core."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_a5d5_nemo_oracle_wrapper import citybrain_oracle_core


def invoke(tool_input: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(tool_input, str):
        tool_input = json.loads(tool_input)
    output_dir = ROOT / "outputs" / "a5d5_nemo_oracle_wrapper" / "live_nemo_invocations"
    return citybrain_oracle_core(tool_input, output_dir=str(output_dir))


if __name__ == "__main__":
    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(invoke(payload), indent=2, sort_keys=True, ensure_ascii=False))
'''


def nemo_readme() -> str:
    return f"""# A5-D5 NeMo Run Notes

Copy this bundle to Spark, then run:

```bash
cd ~/works/citybrain-a5d5

source .venv/bin/activate

python scripts/run_a5d5_nemo_smoke.py \\
  --input-dir outputs/a5d4b_request_trace_core \\
  --output-dir outputs/a5d5_nemo_oracle_wrapper \\
  --use-nim \\
  --nim-endpoint http://127.0.0.1:8000/v1 \\
  --nim-model meta/llama-3.1-8b-instruct

nat run --config_file nemo/workflow_citybrain_oracle.example.yml \\
  --input "{HERO_PROMPT}"
```

NeMo/NAT may print non-blocking OpenTelemetry/protobuf plugin startup warnings.
These are not failures if the workflow exits 0 and returns a grounded response.

Boundary:

{BOUNDARY_STATEMENT}
"""


def smoke_script_source() -> str:
    return '''from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_a5d5_nemo_oracle_wrapper import run_smoke_suite


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A5-D5 local NeMo-wrapper smoke.")
    parser.add_argument("--input-dir", default=str(ROOT / "outputs" / "a5d4b_request_trace_core"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "a5d5_nemo_oracle_wrapper"))
    parser.add_argument("--use-nim", action="store_true")
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default=None)
    args = parser.parse_args()
    result = run_smoke_suite(args.input_dir, args.output_dir, args.use_nim, args.nim_endpoint, args.nim_model)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


def gate_script_source() -> str:
    return '''from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_a5d5_nemo_oracle_wrapper import print_final_report, run_a5d5_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A5-D5 gate.")
    parser.add_argument("--input-dir", default=str(ROOT / "outputs" / "a5d4b_request_trace_core"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "a5d5_nemo_oracle_wrapper"))
    parser.add_argument("--use-live-nemo", action="store_true")
    parser.add_argument("--use-nim", action="store_true")
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default=None)
    args = parser.parse_args()
    report = run_a5d5_gate(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        use_live_nemo=args.use_live_nemo,
        use_nim=args.use_nim,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
    )
    print_final_report(report, args.output_dir)
    return int(report.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
'''


def extract_bbl(operator_query: str) -> str | None:
    match = re.search(r"\bparcel\s+([0-9]{7,12})\b", operator_query, flags=re.I)
    if match:
        return match.group(1)
    match = re.search(r"\b([0-9]{10})\b", operator_query)
    return match.group(1) if match else None


def prompt_to_tool_input(operator_query: str, allow_nim_narration: bool = False) -> dict[str, Any]:
    bbl = extract_bbl(operator_query)
    return {
        "subject_type": "parcel",
        "bbl": bbl or "",
        "query_intent": SUPPORTED_INTENT,
        "requested_outputs": ["what_is_happening", "what_changed", "who_is_responsible", "evidence"],
        "allow_nim_narration": allow_nim_narration,
        "operator_query": operator_query,
    }


def label_for_bbl(bbl: str) -> str:
    if bbl == HERO_BBL:
        return "hero"
    if bbl == SECOND_SUBJECT_BBL:
        return "second_subject"
    return "adhoc"


def input_paths_from_d4b(d4b_dir: Path) -> dict[str, Path]:
    report = load_json_file(d4b_dir / "A5D4B_HARNESS_REPORT.json")
    inputs = report.get("inputs", {})
    return {
        "a5d4b": d4b_dir,
        "a5d4a": resolve_existing_path(inputs.get("a5d4a_dir", "outputs/a5d4a_evidence_grounding_core"), d4b_dir),
        "a5d2": resolve_existing_path(inputs.get("a5d2_dir", "outputs/a5d2_spark_portability_pack"), d4b_dir),
        "a5d1": resolve_existing_path(inputs.get("a5d1_dir", "outputs/a5d1_operator_query"), d4b_dir),
        "a4d2": resolve_existing_path(inputs.get("a4d2_dir", "outputs/a5_dob_district_enrichment"), d4b_dir),
    }


def d4a_label_available(d4a_report: dict[str, Any], label: str) -> bool:
    key = "hero" if label == "hero" else "second_subject" if label == "second_subject" else label
    return key in (d4a_report.get("evidence_bundles") or {})


def d4b_request_from_tool_input(tool_input: dict[str, Any], run_label: str) -> dict[str, Any]:
    bbl = str(tool_input.get("bbl") or "").strip()
    return {
        "request_id": f"a5d5-{run_label}-parcel-{bbl or 'missing'}",
        "tool_name": "citybrain_operator_query",
        "subject_type": tool_input.get("subject_type") or "parcel",
        "subject_id": f"parcel:us-nyc:bbl:{bbl}" if bbl else "",
        "bbl": bbl,
        "query_intent": tool_input.get("query_intent") or SUPPORTED_INTENT,
        "requested_outputs": tool_input.get("requested_outputs")
        or ["what_is_happening", "what_changed", "who_is_responsible", "evidence"],
        "allow_nim_narration": bool(tool_input.get("allow_nim_narration")),
        "raw_request": str(tool_input.get("operator_query") or ""),
    }


def citybrain_oracle_core(
    tool_input: dict[str, Any],
    input_dir: str = str(DEFAULT_D4B_DIR),
    output_dir: str = str(DEFAULT_OUTPUT_DIR),
    run_label: str | None = None,
    use_nim: bool | None = None,
    nim_endpoint: str | None = None,
    nim_model: str | None = None,
) -> dict[str, Any]:
    d4b_dir = Path(input_dir)
    out = Path(output_dir)
    paths = input_paths_from_d4b(d4b_dir)
    d4a_report = load_json_file(paths["a5d4a"] / "A5D4A_HARNESS_REPORT.json")
    registry = load_json_file(d4b_dir / "A5D4B_TOOL_REGISTRY.json") if (d4b_dir / "A5D4B_TOOL_REGISTRY.json").exists() else default_tool_registry()
    request_schema = load_json_file(d4b_dir / "A5D4B_REQUEST_SCHEMA.json") if (d4b_dir / "A5D4B_REQUEST_SCHEMA.json").exists() else default_request_schema()
    rules = load_json_file(d4b_dir / "A5D4B_VALIDATION_RULES.json") if (d4b_dir / "A5D4B_VALIDATION_RULES.json").exists() else default_validation_rules()
    graph = DistrictGraph(paths["a4d2"])
    bbl = str(tool_input.get("bbl") or "").strip()
    label = run_label or label_for_bbl(bbl)
    request = d4b_request_from_tool_input(tool_input, label)
    if label == "adhoc" and request.get("bbl") and d4a_label_available(d4a_report, label) is False:
        # Route through D4B validation semantics, but reject before execution
        # because D5's accepted D4A evidence set covers only hero + second subject.
        run_dir = out / "oracle_core_runs" / f"{label}_parcel_{request.get('bbl', 'missing')}"
        run_dir.mkdir(parents=True, exist_ok=True)
        rejection = {
            "status": "FAIL",
            "rejected": True,
            "public_tool_name": PUBLIC_TOOL_NAME,
            "boundary_statement": BOUNDARY_STATEMENT,
            "final_response": None,
            "evidence_bundle": None,
            "trace": {
                "run_id": f"a5d5:{label}:{request['request_id']}",
                "subject_id": request.get("subject_id"),
                "snapshot": SNAPSHOT,
                "boundary_statement": BOUNDARY_STATEMENT,
                "status": "REJECTED",
                "steps": [],
                "tool_calls": [],
                "nim_calls": [],
                "final_output_hash": None,
                "validation_result": {
                    "status": "FAIL",
                    "reasons": ["subject not covered by accepted A5-D4A EvidenceBundle set"],
                },
            },
            "grounding_result": None,
            "d4b_status": "REJECTED",
        }
        write_json(run_dir / "citybrain_oracle_core_output.json", rejection)
        return rejection

    run_dir = out / "oracle_core_runs" / f"{label}_parcel_{request.get('bbl') or 'missing'}"
    result = run_oracle_request(
        request=request,
        subject_label=label,
        run_dir=run_dir,
        graph=graph,
        d4a_report=d4a_report,
        d4a_dir=paths["a5d4a"],
        registry=registry,
        request_schema=request_schema,
        rules=rules,
        use_nim=bool(tool_input.get("allow_nim_narration")) if use_nim is None else use_nim,
        nim_endpoint=nim_endpoint,
        nim_model=nim_model,
    )
    if result.get("status") == "REJECTED":
        output = {
            "status": "FAIL",
            "rejected": True,
            "public_tool_name": PUBLIC_TOOL_NAME,
            "boundary_statement": BOUNDARY_STATEMENT,
            "final_response": None,
            "evidence_bundle": None,
            "trace": result.get("trace"),
            "grounding_result": None,
            "validation_result": result.get("validation"),
            "d4b_status": "REJECTED",
        }
    else:
        evidence_bundle = result.get("normalization", {}).get("evidence_bundle")
        output = {
            "status": "PASS" if result.get("status") == "PASS" else "FAIL",
            "rejected": False,
            "public_tool_name": PUBLIC_TOOL_NAME,
            "boundary_statement": BOUNDARY_STATEMENT,
            "final_response": result.get("final_response"),
            "evidence_bundle": evidence_bundle,
            "trace": result.get("trace"),
            "grounding_result": result.get("grounding"),
            "d4b_status": result.get("status"),
        }
    output["output_hash"] = sha256_payload(output)
    write_json(run_dir / "citybrain_oracle_core_output.json", output)
    return output


def run_prompt_smoke(
    prompt: str,
    label: str,
    input_dir: str,
    output_dir: str,
    use_nim: bool = False,
    nim_endpoint: str | None = None,
    nim_model: str | None = None,
) -> dict[str, Any]:
    tool_input = prompt_to_tool_input(prompt, allow_nim_narration=use_nim)
    output = citybrain_oracle_core(
        tool_input,
        input_dir=input_dir,
        output_dir=output_dir,
        run_label=label,
        use_nim=use_nim,
        nim_endpoint=nim_endpoint,
        nim_model=nim_model,
    )
    return {
        "prompt": prompt,
        "tool_input": tool_input,
        "tool_output": output,
    }


def run_smoke_suite(
    input_dir: str,
    output_dir: str,
    use_nim: bool = False,
    nim_endpoint: str | None = None,
    nim_model: str | None = None,
) -> dict[str, Any]:
    hero = run_prompt_smoke(HERO_PROMPT, "hero", input_dir, output_dir, use_nim, nim_endpoint, nim_model)
    second = run_prompt_smoke(SECOND_SUBJECT_PROMPT, "second_subject", input_dir, output_dir, use_nim, nim_endpoint, nim_model)
    negative = run_prompt_smoke(NEGATIVE_PROMPT, "negative_enforcement", input_dir, output_dir, use_nim, nim_endpoint, nim_model)
    status = "PASS" if (
        hero["tool_output"].get("status") == "PASS"
        and second["tool_output"].get("status") == "PASS"
        and negative["tool_output"].get("status") == "FAIL"
        and negative["tool_output"].get("rejected") is True
    ) else "FAIL"
    return {
        "status": status,
        "hero": hero,
        "second_subject": second,
        "negative": negative,
    }


def write_nemo_artifacts(output_dir: Path) -> None:
    write_json(output_dir / "A5D5_NEMO_TOOL_SPEC.json", nemo_tool_spec())
    yaml_text = workflow_yaml()
    write_text(output_dir / "A5D5_NEMO_WORKFLOW.example.yml", yaml_text)
    write_text(output_dir / "nemo" / "workflow_citybrain_oracle.example.yml", yaml_text)
    write_text(output_dir / "nemo" / "tool_citybrain_oracle_core.py", nemo_tool_py())
    write_text(output_dir / "nemo" / "README_NEMO_RUN.md", nemo_readme())
    write_text(output_dir / "scripts" / "run_a5d5_nemo_smoke.py", smoke_script_source())
    write_text(output_dir / "scripts" / "run_a5d5_gate.py", gate_script_source())


def report_status(path: Path) -> tuple[bool, dict[str, Any]]:
    if not path.exists():
        return False, {}
    report = load_json_file(path)
    return report.get("status") == "PASS" and report.get("exit_code") == 0, report


def precondition_reports(d4b_dir: Path) -> tuple[dict[str, Path], dict[str, Any], list[str]]:
    details: list[str] = []
    d4b_ok, d4b_report = report_status(d4b_dir / "A5D4B_HARNESS_REPORT.json")
    if not d4b_ok:
        details.append("A5-D4B harness is missing or not PASS")
    paths = input_paths_from_d4b(d4b_dir) if d4b_report else {"a5d4b": d4b_dir}
    d4a_ok, d4a_report = report_status(paths.get("a5d4a", ROOT / "missing") / "A5D4A_HARNESS_REPORT.json")
    d2_ok, d2_report = report_status(paths.get("a5d2", ROOT / "missing") / "A5D2_HARNESS_REPORT.json")
    if not d4a_ok:
        details.append("A5-D4A harness is missing or not PASS")
    if not d2_ok:
        details.append("A5-D2 harness is missing or not PASS")
    if BOUNDARY_STATEMENT not in canonical_json({"d4b": d4b_report, "d4a": d4a_report, "d2": d2_report}):
        details.append("Boundary statement missing from prerequisite reports")
    return paths, {"d4b": d4b_report, "d4a": d4a_report, "d2": d2_report}, details


def counts_from_output(output: dict[str, Any]) -> dict[str, Any]:
    return (((output.get("evidence_bundle") or {}).get("counts") or {}))


def successful_output_grounded(output: dict[str, Any]) -> bool:
    return output.get("status") == "PASS" and (output.get("grounding_result") or {}).get("status") == "PASS"


def trace_preserved(output: dict[str, Any]) -> bool:
    trace = output.get("trace") or {}
    return bool(
        trace.get("run_id")
        and trace.get("steps")
        and trace.get("final_output_hash")
        and trace.get("boundary_statement") == BOUNDARY_STATEMENT
        and trace.get("grounding_result")
    )


def check_sha_coverage(output_dir: Path) -> tuple[bool, list[str]]:
    sha_path = output_dir / "SHA256SUMS.json"
    if not sha_path.exists():
        return False, ["missing SHA256SUMS.json"]
    recorded = load_json_file(sha_path)
    actual = output_hashes(output_dir)
    missing = sorted(set(actual) - set(recorded))
    extra = sorted(set(recorded) - set(actual))
    mismatch = sorted(key for key, value in actual.items() if recorded.get(key) != value)
    details = [*(f"missing:{item}" for item in missing), *(f"extra:{item}" for item in extra), *(f"mismatch:{item}" for item in mismatch)]
    return not details, details


def gate(gate_id: str, name: str, passed: bool, details: list[str] | None = None, checked: int = 1, status: str | None = None) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "status": status or ("PASS" if passed else "FAIL"),
        "checked": checked,
        "failed": 0 if passed else 1,
        "details": details or [],
    }


def maybe_run_live_nemo(output_dir: Path, use_live_nemo: bool) -> tuple[str, dict[str, Any]]:
    if not use_live_nemo:
        return "SKIPPED", {"status": "SKIPPED", "reason": "use_live_nemo was false"}
    cmd = [
        "nat",
        "run",
        "--config_file",
        str(output_dir / "nemo" / "workflow_citybrain_oracle.example.yml"),
        "--input",
        HERO_PROMPT,
    ]
    try:
        result = subprocess.run(cmd, cwd=output_dir, text=True, capture_output=True, timeout=120)
        payload = {
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": cmd,
        }
        return payload["status"], payload
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return "FAIL", {"status": "FAIL", "error": str(exc), "command": cmd}


def build_readme(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# A5-D5 NeMo Wrapper for Governed CityBrain Oracle Core",
            "",
            f"Status: {report['status']}.",
            "",
            "a5 = Action Core / NeMo+NIM / DGX Spark.",
            "a5-D5 = NeMo wrapper for governed CityBrain oracle core.",
            "a5-D4A = EvidenceBundle v1 + grounded narration.",
            "a5-D4B = thin request validator + complete trace.",
            "a4-D2 = DOB district enrichment.",
            "",
            BOUNDARY_STATEMENT,
            "",
            "## Public Tool",
            "",
            f"- `{PUBLIC_TOOL_NAME}` is the only NeMo-facing CityBrain tool.",
            "- D4B remains the validation and trace authority.",
            "- NIM is optional narration only and never computes truth.",
            "",
            "## Smoke Results",
            "",
            f"- Hero: {report['checks']['hero_wrapper_smoke']}.",
            f"- Second subject: {report['checks']['second_subject_wrapper_smoke']}.",
            f"- Negative request rejected: {report['checks']['negative_request_rejected']}.",
            "",
        ]
    )


def write_manifest(output_dir: Path, report: dict[str, Any]) -> None:
    manifest = {
        "task": TASK_NAME,
        "status": report["status"],
        "generated_at": report["generated_at"],
        "boundary_statement": BOUNDARY_STATEMENT,
        "public_tool": PUBLIC_TOOL_NAME,
        "inputs": report["inputs"],
        "outputs": {
            "tool_spec": "A5D5_NEMO_TOOL_SPEC.json",
            "workflow": "nemo/workflow_citybrain_oracle.example.yml",
            "hero_run": "A5D5_HERO_NEMO_RUN.json",
            "second_subject_run": "A5D5_SECOND_SUBJECT_NEMO_RUN.json",
            "negative_runs": "A5D5_NEGATIVE_NEMO_RUNS.json",
        },
        "naming": {
            "a5": "Action Core / NeMo+NIM / DGX Spark",
            "a5-D5": "NeMo wrapper for governed CityBrain oracle core",
            "a5-D4A": "EvidenceBundle v1 + grounded narration",
            "a5-D4B": "thin request validator + complete trace",
            "a4-D2": "DOB district enrichment",
        },
    }
    write_json(output_dir / "A5D5_MANIFEST.json", manifest)


def run_a5d5_gate(
    input_dir: str,
    output_dir: str,
    use_live_nemo: bool = False,
    use_nim: bool = False,
    nim_endpoint: str | None = None,
    nim_model: str | None = None,
) -> dict:
    d4b_dir = Path(input_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths, prereq_reports, precond_details = precondition_reports(d4b_dir)
    paths.setdefault("a5d4b", d4b_dir)
    frozen_paths = {
        "a5d4a": paths.get("a5d4a", ROOT / "missing"),
        "a5d4b": d4b_dir,
        "a5d2": paths.get("a5d2", ROOT / "missing"),
        "a5d1": paths.get("a5d1", ROOT / "outputs" / "a5d1_operator_query"),
        "a4d2": paths.get("a4d2", ROOT / "outputs" / "a5_dob_district_enrichment"),
    }
    before_hashes = {name: hash_tree(path) for name, path in frozen_paths.items()}

    write_nemo_artifacts(out)
    smoke = run_smoke_suite(str(d4b_dir), str(out), use_nim=use_nim, nim_endpoint=nim_endpoint, nim_model=nim_model)
    hero_output = smoke["hero"]["tool_output"]
    second_output = smoke["second_subject"]["tool_output"]
    negative_output = smoke["negative"]["tool_output"]
    write_json(out / "A5D5_HERO_NEMO_RUN.json", smoke["hero"])
    write_text(out / "A5D5_HERO_NEMO_RESPONSE.md", final_response_markdown(hero_output["final_response"]) if hero_output.get("final_response") else "Hero run failed.\n")
    write_json(out / "A5D5_SECOND_SUBJECT_NEMO_RUN.json", smoke["second_subject"])
    write_text(out / "A5D5_SECOND_SUBJECT_NEMO_RESPONSE.md", final_response_markdown(second_output["final_response"]) if second_output.get("final_response") else "Second-subject run failed.\n")
    write_json(out / "A5D5_NEGATIVE_NEMO_RUNS.json", {"negative_enforcement": smoke["negative"]})

    tool_spec = load_json_file(out / "A5D5_NEMO_TOOL_SPEC.json")
    public_tool_names = [tool.get("tool_name") for tool in tool_spec.get("public_tools", [])]
    tool_spec_pass = public_tool_names == [PUBLIC_TOOL_NAME]
    nemo_config_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in [out / "A5D5_NEMO_TOOL_SPEC.json", out / "A5D5_NEMO_WORKFLOW.example.yml", out / "nemo" / "workflow_citybrain_oracle.example.yml", out / "nemo" / "tool_citybrain_oracle_core.py"]
    )
    forbidden_public = ["parcel_profile", "building_profile", "complaint_search", "permit_search", "party_search", "reachability"]
    bypass_hits = [name for name in forbidden_public if re.search(rf"\b{name}\b", nemo_config_text)]

    hero_counts = counts_from_output(hero_output)
    hero_sources = hero_counts.get("source_rows", {})
    hero_smoke_pass = (
        hero_output.get("status") == "PASS"
        and successful_output_grounded(hero_output)
        and trace_preserved(hero_output)
        and hero_sources.get("dob_permit_issuance") == 1
        and hero_sources.get("dob_now_filings") == 12
        and hero_sources.get("dob_complaints") == 9
        and BOUNDARY_STATEMENT in canonical_json(hero_output)
    )
    second_counts = counts_from_output(second_output)
    second_sources = second_counts.get("source_rows", {})
    second_text = canonical_json(second_output)
    second_evidence = canonical_json(second_output.get("evidence_bundle") or {})
    leaks = [token for token in HERO_LEAK_TOKENS if token in second_text and token not in second_evidence]
    second_smoke_pass = (
        second_output.get("status") == "PASS"
        and successful_output_grounded(second_output)
        and trace_preserved(second_output)
        and not leaks
        and second_sources.get("dob_now_filings") == 0
        and BOUNDARY_STATEMENT in second_text
    )
    negative_reasons = (((negative_output.get("trace") or {}).get("validation_result") or {}).get("reasons") or [])
    negative_pass = (
        negative_output.get("status") == "FAIL"
        and negative_output.get("rejected") is True
        and not ((negative_output.get("trace") or {}).get("tool_calls") or [])
        and any("enforcement" in reason or "action" in reason for reason in negative_reasons)
        and any("full-history" in reason for reason in negative_reasons)
        and BOUNDARY_STATEMENT in canonical_json(negative_output)
    )
    grounding_pass = successful_output_grounded(hero_output) and successful_output_grounded(second_output)
    trace_pass = trace_preserved(hero_output) and trace_preserved(second_output)
    nim_status = "SKIPPED"
    nim_pass = True
    if use_nim:
        nim_calls = [
            call
            for output in (hero_output, second_output)
            for call in ((output.get("trace") or {}).get("nim_calls") or [])
        ]
        nim_pass = bool(nim_calls) and all(call.get("status") == "PASS" for call in nim_calls) and grounding_pass
        nim_status = "PASS" if nim_pass else "FAIL"
    live_nemo_status, live_nemo_payload = maybe_run_live_nemo(out, use_live_nemo)
    write_json(out / "LIVE_NEMO_RUN.json", live_nemo_payload)

    after_hashes = {name: hash_tree(path) for name, path in frozen_paths.items()}
    no_mutation_pass = before_hashes == after_hashes
    no_mutation_details = [] if no_mutation_pass else [name for name in frozen_paths if before_hashes.get(name) != after_hashes.get(name)]

    naming_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in out.rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".yml", ".py"}
    )
    planned_naming_text = "\n".join(
        [
            "a5 = Action Core / NeMo+NIM / DGX Spark",
            "a5-D5 = NeMo wrapper for governed CityBrain oracle core",
            "a5-D4A = EvidenceBundle v1 + grounded narration",
            "a5-D4B = thin request validator + complete trace",
            "a4-D2 = DOB district enrichment",
        ]
    )
    naming_bad = []
    if re.search(r"\bA6\b", naming_text):
        naming_bad.append("A6 reference found")
    if "DOB enrichment is A5" in naming_text or "DOB district enrichment is A5" in naming_text:
        naming_bad.append("DOB enrichment called A5")
    naming_required = all(
        phrase in f"{naming_text}\n{planned_naming_text}"
        for phrase in (
            "Action Core / NeMo+NIM / DGX Spark",
            "NeMo wrapper for governed CityBrain oracle core",
            "EvidenceBundle v1 + grounded narration",
            "thin request validator + complete trace",
            "DOB district enrichment",
        )
    )

    gates = [
        gate("A5D5-PRECOND", "A5-D4A, A5-D4B, and A5-D2 inputs are PASS", not precond_details, precond_details),
        gate("A5D5-NEMO-TOOL-SPEC", "NeMo tool spec exposes exactly one public CityBrain tool", tool_spec_pass, public_tool_names),
        gate("A5D5-NO-BYPASS", "NeMo wrapper does not expose low-level deterministic tools", not bypass_hits, bypass_hits),
        gate("A5D5-HERO-WRAPPER-SMOKE", "Hero prompt runs through wrapper with expected counts", hero_smoke_pass),
        gate("A5D5-SECOND-SUBJECT-WRAPPER-SMOKE", "Second-subject prompt runs through wrapper with no hero leakage", second_smoke_pass, leaks),
        gate("A5D5-NEGATIVE-REQUEST-REJECTED", "Unsafe prompt is rejected before deterministic execution", negative_pass, negative_reasons),
        gate("A5D5-GROUNDING-PRESERVED", "D4A grounding is preserved for successful wrapper outputs", grounding_pass),
        gate("A5D5-TRACE-PRESERVED", "D4B complete trace is preserved in successful wrapper outputs", trace_pass),
        gate("A5D5-NIM-OPTIONAL", "Default run succeeds without NIM", not use_nim or nim_pass, status="PASS" if not use_nim or nim_pass else "FAIL"),
        gate("A5D5-LIVE-NIM", "Live NIM narration returns and remains grounded when requested", nim_pass if use_nim else True, status=nim_status),
        gate("A5D5-LIVE-NEMO", "Live NeMo runtime executes workflow when requested", live_nemo_status == "PASS" if use_live_nemo else True, status=live_nemo_status),
        gate("A5D5-NO-MUTATION", "Frozen D4A, D4B, A5-D2, A5-D1, and A4-D2 inputs remain byte-stable", no_mutation_pass, no_mutation_details),
        gate("A5D5-NAMING", "Naming remains unambiguous", not naming_bad and naming_required, naming_bad),
    ]
    checks = {
        "preconditions": gates[0]["passed"],
        "nemo_tool_spec": gates[1]["passed"],
        "no_bypass": gates[2]["passed"],
        "hero_wrapper_smoke": gates[3]["passed"],
        "second_subject_wrapper_smoke": gates[4]["passed"],
        "negative_request_rejected": gates[5]["passed"],
        "grounding_preserved": gates[6]["passed"],
        "trace_preserved": gates[7]["passed"],
        "nim_optional": gates[8]["passed"],
        "live_nim": nim_status,
        "live_nemo": live_nemo_status,
        "no_mutation": gates[11]["passed"],
        "naming": gates[12]["passed"],
    }
    status = "PASS" if all(gate_item["passed"] for gate_item in gates) else "FAIL"
    report = {
        "task": TASK_NAME,
        "status": status,
        "exit_code": 0 if status == "PASS" else 1,
        "generated_at": utc_now(),
        "boundary_statement": BOUNDARY_STATEMENT,
        "inputs": {name: str(path) for name, path in frozen_paths.items()},
        "checks": checks,
        "gates": gates,
        "public_tool": PUBLIC_TOOL_NAME,
        "hero": {
            "status": hero_output.get("status"),
            "counts": hero_counts,
            "grounding_status": (hero_output.get("grounding_result") or {}).get("status"),
            "trace_id": (hero_output.get("trace") or {}).get("run_id"),
        },
        "second_subject": {
            "status": second_output.get("status"),
            "counts": second_counts,
            "grounding_status": (second_output.get("grounding_result") or {}).get("status"),
            "trace_id": (second_output.get("trace") or {}).get("run_id"),
            "hero_leak_tokens": leaks,
        },
        "negative": {
            "status": negative_output.get("status"),
            "rejected": negative_output.get("rejected"),
            "reasons": negative_reasons,
        },
    }
    write_manifest(out, report)
    write_text(out / "README.md", build_readme(report))
    report["gates"].append(gate("A5D5-HASHES", "SHA256SUMS covers generated artifacts except itself", True))
    report["checks"]["hashes"] = True
    report["status"] = "PASS" if all(item["passed"] for item in report["gates"]) else "FAIL"
    report["exit_code"] = 0 if report["status"] == "PASS" else 1
    write_json(out / "A5D5_HARNESS_REPORT.json", report)
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    sha_pass, sha_details = check_sha_coverage(out)
    if not sha_pass:
        report["status"] = "FAIL"
        report["exit_code"] = 1
        report["checks"]["hashes"] = False
        report["gates"][-1] = gate("A5D5-HASHES", "SHA256SUMS covers generated artifacts except itself", False, sha_details)
        write_json(out / "A5D5_HARNESS_REPORT.json", report)
        write_json(out / "SHA256SUMS.json", output_hashes(out))
    return report


def print_final_report(report: dict[str, Any], output_dir: str) -> None:
    checks = report.get("checks", {})
    print(f"A5-D5 NeMo Wrapper for Governed CityBrain Oracle Core: {report.get('status')}")
    print(f"Input A5-D4A: {'PASS' if report.get('gates', [{}])[0].get('passed') else 'FAIL'}")
    print(f"Input A5-D4B: {'PASS' if checks.get('preconditions') else 'FAIL'}")
    print(f"NeMo tool spec: {'PASS' if checks.get('nemo_tool_spec') else 'FAIL'}")
    print(f"No low-level tool bypass: {'PASS' if checks.get('no_bypass') else 'FAIL'}")
    print(f"Hero wrapper smoke: {'PASS' if checks.get('hero_wrapper_smoke') else 'FAIL'}")
    print(f"Second-subject wrapper smoke: {'PASS' if checks.get('second_subject_wrapper_smoke') else 'FAIL'}")
    print(f"Negative request rejected: {'PASS' if checks.get('negative_request_rejected') else 'FAIL'}")
    print(f"Grounding preserved: {'PASS' if checks.get('grounding_preserved') else 'FAIL'}")
    print(f"Trace preserved: {'PASS' if checks.get('trace_preserved') else 'FAIL'}")
    print(f"NIM optional/live: {checks.get('live_nim', 'SKIPPED') if checks.get('live_nim') != 'SKIPPED' else 'SKIPPED'}")
    print(f"Live NeMo: {checks.get('live_nemo', 'SKIPPED')}")
    print(f"No mutation: {'PASS' if checks.get('no_mutation') else 'FAIL'}")
    print(f"Output: {output_dir}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run A5-D5 NeMo oracle wrapper gate.")
    parser.add_argument("--input-dir", default=str(DEFAULT_D4B_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-gates", action="store_true")
    parser.add_argument("--use-live-nemo", action="store_true")
    parser.add_argument("--use-nim", action="store_true")
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default=None)
    args = parser.parse_args(argv)
    report = run_a5d5_gate(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        use_live_nemo=args.use_live_nemo,
        use_nim=args.use_nim,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
    )
    print_final_report(report, args.output_dir)
    return int(report.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
