from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_D3A_DIR = ROOT / "outputs" / "a4d3a_multidistrict_projection"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "a4d3a_live_nemo_nim_briefings"
DEFAULT_REMOTE_HOST = "spark"
DEFAULT_REMOTE_DIR = "/home/txr/works/citybrain-a4d3a-live-briefings"
DEFAULT_NAT_VENV = "/home/txr/works/nemo-agent-toolkit/.venv"
DEFAULT_NIM_ENDPOINT = "http://127.0.0.1:8000/v1"
DEFAULT_NIM_MODEL = "meta/llama-3.1-8b-instruct"

BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped "
    "depending on local harvest status. Discovery and projection counts are not claims about "
    "complete NYC history unless the dataset is marked full in the inventory."
)

DISTRICT_PROMPTS = {
    "1-01060": "What is happening in district 1-01060? Give the operator briefing with evidence.",
    "1-01158": "What is happening in district 1-01158? Give the operator briefing with evidence.",
    "2-02316": "What is happening in district 2-02316? Give the operator briefing with evidence.",
}

FORBIDDEN_LOW_LEVEL_TOOLS = [
    "parcel_profile",
    "building_profile",
    "complaint_search",
    "permit_search",
    "party_search",
    "reachability",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 900) -> dict[str, Any]:
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


def top_party_lists(district_dir: Path) -> dict[str, list[dict[str, Any]]]:
    entities = [json.loads(v) for v in pd.read_parquet(district_dir / "canonical_entities.parquet")["record_json"]]
    edges = [json.loads(v) for v in pd.read_parquet(district_dir / "canonical_edges.parquet")["record_json"]]
    by_id = {entity["canonical_id"]: entity for entity in entities}
    buckets: dict[str, list[tuple[str, str, str, float | None]]] = {
        "performed_by": [],
        "designed_by": [],
        "involves_party": [],
    }
    for edge in edges:
        relation = edge.get("relation")
        if relation not in buckets:
            continue
        party = by_id.get(edge.get("dst_ref"), {})
        name = party.get("name")
        if not name:
            continue
        conf = edge.get("confidence") or {}
        buckets[relation].append((name, edge.get("role") or relation, conf.get("method"), conf.get("score")))

    def top(items: list[tuple[str, str, str, float | None]]) -> list[dict[str, Any]]:
        counts = Counter(items)
        return [
            {"name": key[0], "role": key[1], "confidence_method": key[2], "confidence_score": key[3], "edge_count": count}
            for key, count in counts.most_common(5)
        ]

    return {
        "top_contractors_performed_by": top(buckets["performed_by"]),
        "top_applicants_designed_by": top(buckets["designed_by"]),
        "top_involved_parties": top(buckets["involves_party"]),
    }


def complaint_profile(district_dir: Path) -> dict[str, Any]:
    entities = [json.loads(v) for v in pd.read_parquet(district_dir / "canonical_entities.parquet")["record_json"]]
    complaints = [e for e in entities if e["canonical_id"].startswith("event:us-nyc:dob_complaint:")]
    categories = Counter((e.get("ext") or {}).get("nyc.dob_complaint_category") for e in complaints)
    types = Counter(e.get("type") for e in complaints)
    severities = Counter(e.get("severity") for e in complaints)
    return {
        "top_complaint_categories": [{"category": k, "count": v} for k, v in categories.most_common(8)],
        "top_complaint_types": [{"type": k, "count": v} for k, v in types.most_common(8)],
        "severity_counts": dict(sorted(severities.items())),
    }


def build_evidence(d3a_dir: Path) -> dict[str, Any]:
    combined = read_json(d3a_dir / "a4d3a_districts_v1.json")
    evidence: dict[str, Any] = {
        "task": "a4-D3a live NeMo/NIM district briefings",
        "generated_at": utc_now(),
        "boundary_statement": BOUNDARY_STATEMENT,
        "d3a_status": combined.get("status"),
        "completion_checks": combined.get("completion_checks"),
        "districts": {},
        "model_rules": [
            "Use only this evidence.",
            "Do not invent counts, parties, categories, dates, or causal claims.",
            "Write as a non-technical city operations briefing.",
            "Preserve the boundary statement.",
            "Say if a fact is a subset/projection count.",
        ],
    }
    for district in combined.get("districts", []):
        block = district["district_id"]
        district_dir = d3a_dir / "districts" / block
        harness = read_json(district_dir / "harness_report.json")
        drift = read_json(district_dir / "drift_test_report.json")
        profile = complaint_profile(district_dir)
        parties = top_party_lists(district_dir)
        summary = {
            key: district.get(key)
            for key in [
                "parcel_count",
                "building_count",
                "permit_count",
                "complaint_count",
                "critical_complaint_count",
                "critical_complaint_definition",
                "canonical_critical_severity_count",
                "unique_jobs",
                "unique_contractors",
                "now_issuance_ratio",
                "complaint_job_ratio",
                "critical_complaint_share",
                "projection_nodes",
                "projection_edges",
                "source_row_counts",
                "party_role_mix",
                "complaint_resolution_method_split",
                "known_limitations",
            ]
        }
        share = float(summary["critical_complaint_share"] or 0)
        summary["critical_complaint_share_percent_4dp"] = round(share * 100, 4)
        summary["critical_complaint_share_percent_2dp"] = round(share * 100, 2)
        approved_facts = [
            f"district_id: {block}",
            f"district_role: {district['district_role']}",
            f"parcel_count: {summary['parcel_count']}",
            f"building_count: {summary['building_count']}",
            f"permit_count: {summary['permit_count']}",
            f"complaint_count: {summary['complaint_count']}",
            f"critical_complaint_count: {summary['critical_complaint_count']}",
            f"critical_complaint_share: {summary['critical_complaint_share']}",
            f"critical_complaint_share_percent_4dp: {summary['critical_complaint_share_percent_4dp']}",
            f"critical_complaint_share_percent_2dp: {summary['critical_complaint_share_percent_2dp']}",
            f"now_issuance_ratio: {summary['now_issuance_ratio']}",
            f"complaint_job_ratio: {summary['complaint_job_ratio']}",
            f"unique_contractors: {summary['unique_contractors']}",
            f"projection_nodes: {summary['projection_nodes']}",
            f"projection_edges: {summary['projection_edges']}",
            f"district_status: {harness.get('status')}",
            f"drift_test_status: {drift.get('status')}",
            f"drift_failed_as_expected: {drift.get('failed_as_expected')}",
            f"boundary_statement: {BOUNDARY_STATEMENT}",
        ]
        for item in profile["top_complaint_categories"][:5]:
            approved_facts.append(f"complaint_category {item['category']}: {item['count']}")
        for item in profile["top_complaint_types"][:5]:
            approved_facts.append(f"complaint_type {item['type']}: {item['count']}")
        for bucket in ["top_contractors_performed_by", "top_applicants_designed_by", "top_involved_parties"]:
            for item in parties[bucket][:3]:
                approved_facts.append(
                    f"{bucket}: {item['name']} role {item['role']} edge_count {item['edge_count']} confidence_method {item['confidence_method']} confidence_score {item['confidence_score']}"
                )
        evidence["districts"][block] = {
            "district_id": block,
            "district_role": district["district_role"],
            "summary": summary,
            "complaint_profile": profile,
            "party_profile": parties,
            "approved_facts": approved_facts,
            "gates": {
                "district_status": harness.get("status"),
                "required_gate_status": harness.get("required_gate_status"),
                "local_traversal": harness.get("local_traversal"),
                "drift_test": {
                    "status": drift.get("status"),
                    "failed_as_expected": drift.get("failed_as_expected"),
                    "failed_gates": drift.get("failed_gates"),
                },
            },
            "operator_question": DISTRICT_PROMPTS[block],
            "boundary_statement": BOUNDARY_STATEMENT,
        }
    evidence["evidence_hash"] = sha256_bytes(canonical_json(evidence).encode("utf-8"))
    return evidence


def nat_plugin_py() -> str:
    return r'''from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pydantic import Field

from nat.plugin_api import Builder
from nat.plugin_api import FunctionBaseConfig
from nat.plugin_api import FunctionInfo
from nat.plugin_api import LLMFrameworkEnum
from nat.plugin_api import register_function


class CityBrainDistrictBriefingConfig(FunctionBaseConfig, name="citybrain_district_briefing"):
    evidence_path: str = Field(description="Path to deterministic D3a district evidence JSON.")
    output_dir: str = Field(description="Where live district briefing invocations are written.")
    nim_endpoint: str = Field(default="http://127.0.0.1:8000/v1")
    nim_model: str = Field(default="meta/llama-3.1-8b-instruct")
    timeout_s: int = Field(default=120)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _extract_block(text: str) -> str:
    for block in ["1-01060", "1-01158", "2-02316"]:
        if block in text:
            return block
    match = re.search(r"\b[12]-0?\d{4,5}\b", text)
    if match:
        return match.group(0)
    return "1-01060"


def _nim_chat(endpoint: str, model: str, messages: list[dict], timeout_s: int) -> dict:
    url = endpoint.rstrip("/") + "/chat/completions"
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 900,
        }
    ).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = payload["choices"][0]["message"]["content"]
        return {"status": "PASS", "text": text, "raw_response": payload}
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        return {"status": "FAIL", "text": "", "error": str(exc)}


def _messages(block: str, evidence: dict) -> list[dict]:
    district = evidence["districts"][block]
    compact = {
        "boundary_statement": evidence["boundary_statement"],
        "d3a_status": evidence["d3a_status"],
        "completion_checks": evidence["completion_checks"],
        "district_id": block,
        "district_role": district["district_role"],
        "approved_facts": district["approved_facts"],
        "summary": district["summary"],
        "complaint_profile": district["complaint_profile"],
        "party_profile": district["party_profile"],
        "gates": district["gates"],
    }
    system = (
        "You are CityBrain's evidence-bound briefing narrator. "
        "The code has already computed every number. You must not compute or invent facts. "
        "Use only the provided evidence JSON. Write for a non-technical city operations reader. "
        "Use short paragraphs or bullets. Preserve the boundary statement exactly inside this district answer. "
        "Copy numeric values exactly as written in the evidence. Do not round, soften, or reinterpret decimals. "
        "If you use a percentage, use only the supplied critical_complaint_share_percent_4dp or "
        "critical_complaint_share_percent_2dp value exactly. "
        "Do not write that any party is responsible for a complaint; write only that the party is connected in the evidence. "
        "If you mention a party, count, category, confidence, ratio, or gate, it must appear in the approved_facts list."
    )
    user = (
        f"Operator question: {district['operator_question']}\n\n"
        "Write the model answer for this district. Include: what is happening, what makes this district notable, "
        "who appears responsible or connected in the evidence, gate/drift status, and what to review next. "
        "Do not mention full NYC history. End the answer with a paragraph beginning exactly `Boundary: ` followed by "
        "the exact boundary statement from the evidence.\n\n"
        "STRICT FACT RULES:\n"
        "- Use only facts from approved_facts.\n"
        "- Copy numeric values exactly. For example, if approved_facts says 0.423077, write 0.423077; if it says 42.31, write 42.31.\n"
        "- Do not add percentages, totals, dates, party names, or cause/effect claims that are not in approved_facts.\n"
        "- Prefer the phrase `connected in the evidence` for parties.\n\n"
        "Evidence JSON:\n"
        + json.dumps(compact, indent=2, sort_keys=True, ensure_ascii=False)
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


@register_function(config_type=CityBrainDistrictBriefingConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def citybrain_district_briefing_function(config: CityBrainDistrictBriefingConfig, _builder: Builder):
    async def _citybrain_district_briefing(operator_query: str) -> str:
        query = str(operator_query)
        evidence_path = Path(config.evidence_path)
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        block = _extract_block(query)
        output_dir = Path(config.output_dir)
        invocation_dir = output_dir / "invocations"
        invocation_dir.mkdir(parents=True, exist_ok=True)
        messages = _messages(block, evidence)
        nim = _nim_chat(config.nim_endpoint, config.nim_model, messages, config.timeout_s)
        record = {
            "timestamp": _utc_now(),
            "public_tool_name": "citybrain_district_briefing",
            "operator_query": query,
            "district_id": block,
            "status": nim["status"],
            "nim_model": config.nim_model,
            "nim_endpoint": config.nim_endpoint,
            "evidence_hash": evidence.get("evidence_hash") or _hash(evidence),
            "grounding_inputs_hash": _hash({"block": block, "messages": messages}),
            "model_answer": nim.get("text", ""),
            "nim_error": nim.get("error"),
            "evidence_used": evidence["districts"].get(block),
        }
        invocation_path = invocation_dir / f"{block}.json"
        invocation_path.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        return json.dumps(
            {
                "status": nim["status"],
                "public_tool_name": "citybrain_district_briefing",
                "district_id": block,
                "invocation_path": str(invocation_path),
                "evidence_hash": record["evidence_hash"],
            },
            sort_keys=True,
            ensure_ascii=False,
        )

    yield FunctionInfo.from_fn(
        _citybrain_district_briefing,
        description=(
            "Single CityBrain D3a briefing tool. It reads deterministic multi-district projection evidence "
            "and calls NIM only to narrate that evidence."
        ),
    )
'''


def nat_pyproject() -> str:
    return """[build-system]\nrequires = [\"setuptools>=64\"]\nbuild-backend = \"setuptools.build_meta\"\n\n[project]\nname = \"citybrain-a4d3a-district-briefing-nat\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11,<3.14\"\ndescription = \"CityBrain A4-D3a district briefing NAT plugin\"\n\n[project.entry-points.'nat.components']\ncitybrain_a4d3a_district_briefing = \"citybrain_a4d3a_district_briefing.register\"\n"""


def nat_workflow(remote_dir: str, nim_endpoint: str, nim_model: str) -> str:
    return f"""workflow:\n  _type: citybrain_district_briefing\n  evidence_path: {remote_dir}/evidence/district_evidence.json\n  output_dir: {remote_dir}/remote_results\n  nim_endpoint: {nim_endpoint}\n  nim_model: {nim_model}\n  timeout_s: 120\n"""


def remote_runner_py() -> str:
    return r'''from __future__ import annotations

import argparse
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PROMPTS = {
    "1-01060": "What is happening in district 1-01060? Give the operator briefing with evidence.",
    "1-01158": "What is happening in district 1-01158? Give the operator briefing with evidence.",
    "2-02316": "What is happening in district 2-02316? Give the operator briefing with evidence.",
}
BOUNDARY = "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped depending on local harvest status. Discovery and projection counts are not claims about complete NYC history unless the dataset is marked full in the inventory."
FORBIDDEN_LOW_LEVEL_TOOLS = ["parcel_profile", "building_profile", "complaint_search", "permit_search", "party_search", "reachability"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd: list[str], cwd: Path, timeout: int = 300) -> dict:
    started = utc_now()
    try:
        result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)
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


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote-root", required=True)
    ap.add_argument("--nat-venv", required=True)
    args = ap.parse_args()
    root = Path(args.remote_root)
    nat = Path(args.nat_venv) / "bin" / "nat"
    py = Path(args.nat_venv) / "bin" / "python"
    results = root / "remote_results"
    results.mkdir(parents=True, exist_ok=True)

    plugin_dir = root / "nat_citybrain_a4d3a_district_briefing"
    install = run([str(py), "-m", "pip", "install", "-e", str(plugin_dir)], root, timeout=300)
    transcript = {"generated_at": utc_now(), "plugin_install": install, "runs": {}, "configured_public_tools": ["citybrain_district_briefing"]}
    if install["status"] != "PASS":
        write_json(results / "LIVE_TRANSCRIPT.json", transcript)
        return 1

    for block, prompt in PROMPTS.items():
        proc = run([str(nat), "run", "--config_file", str(root / "workflow_citybrain_district_briefing.yml"), "--input", prompt], root, timeout=300)
        proc["stdout_clean"] = strip_ansi(proc.get("stdout", ""))
        proc["stderr_clean"] = strip_ansi(proc.get("stderr", ""))
        invocation_path = results / "invocations" / f"{block}.json"
        invocation = read_json(invocation_path) if invocation_path.exists() else {}
        transcript["runs"][block] = {
            "prompt": prompt,
            "nat_process": proc,
            "observed_nemo_tool_calls": ["citybrain_district_briefing"] if invocation else [],
            "invocation": invocation,
        }

    answers_md = ["# A4-D3a Live NeMo/NIM District Briefings", "", BOUNDARY, ""]
    for block in PROMPTS:
        invocation = transcript["runs"].get(block, {}).get("invocation", {})
        answers_md.extend([f"## {block}", "", invocation.get("model_answer") or "(no model answer)", ""])
    (results / "MODEL_ANSWERS.md").write_text("\n".join(answers_md), encoding="utf-8")

    tool_audit = {
        "configured_public_tools": ["citybrain_district_briefing"],
        "forbidden_low_level_public_hits": [tool for tool in FORBIDDEN_LOW_LEVEL_TOOLS if tool in json.dumps(transcript)],
        "run_tool_calls": {block: transcript["runs"][block]["observed_nemo_tool_calls"] for block in transcript["runs"]},
    }
    write_json(results / "NEMO_TOOL_CALL_AUDIT.json", tool_audit)
    write_json(results / "LIVE_TRANSCRIPT.json", transcript)
    with zipfile.ZipFile(root / "remote_results.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for path in results.rglob("*"):
            if path.is_file():
                z.write(path, path.relative_to(root))
    ok = all(run_data["nat_process"]["status"] == "PASS" and run_data["invocation"].get("status") == "PASS" for run_data in transcript["runs"].values())
    ok = ok and not tool_audit["forbidden_low_level_public_hits"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


def create_remote_bundle(output_dir: Path, evidence: dict[str, Any], remote_dir: str, nim_endpoint: str, nim_model: str) -> Path:
    bundle_dir = output_dir / "remote_bundle"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)
    evidence_dir = bundle_dir / "evidence"
    evidence_dir.mkdir()
    write_json(evidence_dir / "district_evidence.json", evidence)
    plugin = bundle_dir / "nat_citybrain_a4d3a_district_briefing"
    package = plugin / "citybrain_a4d3a_district_briefing"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "register.py").write_text(nat_plugin_py(), encoding="utf-8")
    (plugin / "pyproject.toml").write_text(nat_pyproject(), encoding="utf-8")
    (bundle_dir / "workflow_citybrain_district_briefing.yml").write_text(nat_workflow(remote_dir, nim_endpoint, nim_model), encoding="utf-8")
    (bundle_dir / "run_remote_district_briefings.py").write_text(remote_runner_py(), encoding="utf-8")
    zip_path = output_dir / "a4d3a_live_briefing_remote_bundle.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in bundle_dir.rglob("*"):
            if path.is_file():
                z.write(path, path.relative_to(bundle_dir))
    return zip_path


def extract_remote_results(output_dir: Path, remote_zip: Path) -> Path:
    target = output_dir / "spark_remote_results"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    with zipfile.ZipFile(remote_zip) as z:
        z.extractall(target)
    return target / "remote_results"


def extract_numbers_and_ids(text: str) -> set[str]:
    tokens = set(re.findall(r"\b\d+(?:\.\d+)?\b", text))
    tokens.update(re.findall(r"\b[12]-0\d{4}\b", text))
    tokens.update(re.findall(r"\b[A-Z]{1,4}-\d{6,7}\b", text))
    return tokens


def grounding_report(evidence: dict[str, Any], transcript: dict[str, Any]) -> dict[str, Any]:
    evidence_blob = canonical_json(evidence)
    results = {}
    for block, run in transcript.get("runs", {}).items():
        answer = (run.get("invocation") or {}).get("model_answer", "")
        tokens = sorted(extract_numbers_and_ids(answer))
        unsupported = [token for token in tokens if token not in evidence_blob]
        boundary_ok = BOUNDARY_STATEMENT in answer
        results[block] = {
            "status": "PASS" if not unsupported and boundary_ok else "FAIL",
            "checked_tokens": tokens,
            "unsupported_tokens": unsupported,
            "boundary_present": boundary_ok,
        }
    return {
        "status": "PASS" if results and all(item["status"] == "PASS" for item in results.values()) else "FAIL",
        "rule": "Every extracted number/license/block token in the model answer must appear in deterministic D3a evidence; boundary must be present.",
        "results": results,
        "boundary_statement": BOUNDARY_STATEMENT,
    }


def write_pin_readme(output_dir: Path, harness: dict[str, Any]) -> None:
    lines = [
        "# A4-D3a Live NeMo/NIM District Briefings",
        "",
        f"Status: **{harness['status']}**",
        "",
        BOUNDARY_STATEMENT,
        "",
        "This pinned run sends the deterministic a4-D3a three-district projection evidence to a Spark-side NeMo/NAT workflow function, which calls the local NIM-served Llama model for evidence-only narration.",
        "",
        "Public NeMo tool: `citybrain_district_briefing`.",
        "",
        "## Artifacts",
        "",
        "- `DISTRICT_EVIDENCE_INPUT.json`",
        "- `LIVE_TRANSCRIPT.json`",
        "- `MODEL_ANSWERS.md`",
        "- `GROUNDING_REPORT.json`",
        "- `NEMO_TOOL_CALL_AUDIT.json`",
        "- `HARNESS_REPORT.json`",
        "",
    ]
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def output_hashes(output_dir: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            hashes[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    return hashes


def run_live_briefings(
    d3a_dir: str | Path = DEFAULT_D3A_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    remote_host: str = DEFAULT_REMOTE_HOST,
    remote_dir: str = DEFAULT_REMOTE_DIR,
    nat_venv: str = DEFAULT_NAT_VENV,
    nim_endpoint: str = DEFAULT_NIM_ENDPOINT,
    nim_model: str = DEFAULT_NIM_MODEL,
) -> dict[str, Any]:
    d3a = Path(d3a_dir)
    out = Path(output_dir)
    if not d3a.is_absolute():
        d3a = ROOT / d3a
    if not out.is_absolute():
        out = ROOT / out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    evidence = build_evidence(d3a)
    write_json(out / "DISTRICT_EVIDENCE_INPUT.json", evidence)
    bundle_zip = create_remote_bundle(out, evidence, remote_dir, nim_endpoint, nim_model)

    commands = {
        "ssh_probe": run_cmd(["ssh", remote_host, f"hostname && test -x {nat_venv}/bin/nat && curl -sS --max-time 10 {nim_endpoint}/models >/dev/null"]),
        "remote_prepare": run_cmd(["ssh", remote_host, f"python3 -c \"import pathlib, shutil; p=pathlib.Path('{remote_dir}'); assert str(p).startswith('/home/txr/works/'); shutil.rmtree(p, ignore_errors=True); p.mkdir(parents=True, exist_ok=True)\""]),
        "scp_bundle": run_cmd(["scp", str(bundle_zip), f"{remote_host}:{remote_dir}/remote_bundle.zip"]),
        "remote_extract": run_cmd(["ssh", remote_host, f"cd {remote_dir} && python3 -m zipfile -e remote_bundle.zip ."]),
        "remote_run": run_cmd(["ssh", remote_host, f"cd {remote_dir} && {nat_venv}/bin/python run_remote_district_briefings.py --remote-root {remote_dir} --nat-venv {nat_venv}"], timeout=1200),
        "scp_back": run_cmd(["scp", f"{remote_host}:{remote_dir}/remote_results.zip", str(out / "remote_results.zip")]),
    }

    remote_results_dir: Path | None = None
    transcript: dict[str, Any] = {}
    tool_audit: dict[str, Any] = {}
    if (out / "remote_results.zip").exists():
        remote_results_dir = extract_remote_results(out, out / "remote_results.zip")
        transcript_path = remote_results_dir / "LIVE_TRANSCRIPT.json"
        audit_path = remote_results_dir / "NEMO_TOOL_CALL_AUDIT.json"
        answers_path = remote_results_dir / "MODEL_ANSWERS.md"
        if transcript_path.exists():
            transcript = read_json(transcript_path)
            write_json(out / "LIVE_TRANSCRIPT.json", transcript)
        if audit_path.exists():
            tool_audit = read_json(audit_path)
            write_json(out / "NEMO_TOOL_CALL_AUDIT.json", tool_audit)
        if answers_path.exists():
            shutil.copy2(answers_path, out / "MODEL_ANSWERS.md")

    ground = grounding_report(evidence, transcript) if transcript else {"status": "FAIL", "reason": "missing transcript"}
    write_json(out / "GROUNDING_REPORT.json", ground)

    runs_ok = transcript and all(
        run.get("nat_process", {}).get("status") == "PASS" and (run.get("invocation") or {}).get("status") == "PASS"
        for run in transcript.get("runs", {}).values()
    )
    tool_ok = tool_audit and tool_audit.get("configured_public_tools") == ["citybrain_district_briefing"] and not tool_audit.get("forbidden_low_level_public_hits")
    status = "PASS" if all(cmd["status"] == "PASS" for cmd in commands.values()) and runs_ok and tool_ok and ground.get("status") == "PASS" else "FAIL"

    harness = {
        "task": "a4-D3a live NeMo/NIM district briefing pin",
        "status": status,
        "exit_code": 0 if status == "PASS" else 1,
        "generated_at": utc_now(),
        "boundary_statement": BOUNDARY_STATEMENT,
        "inputs": {"d3a_dir": str(d3a), "evidence_hash": evidence["evidence_hash"]},
        "spark": {"remote_host": remote_host, "remote_dir": remote_dir, "nat_venv": nat_venv, "nim_endpoint": nim_endpoint, "nim_model": nim_model},
        "checks": {
            "spark_nim_reachable": commands["ssh_probe"]["status"] == "PASS",
            "remote_run": commands["remote_run"]["status"] == "PASS",
            "all_three_model_answers": bool(transcript) and set(transcript.get("runs", {}).keys()) == set(DISTRICT_PROMPTS.keys()) and runs_ok,
            "nemo_single_tool": bool(tool_ok),
            "grounding": ground.get("status") == "PASS",
            "boundary": BOUNDARY_STATEMENT in (out / "MODEL_ANSWERS.md").read_text(encoding="utf-8") if (out / "MODEL_ANSWERS.md").exists() else False,
        },
        "remote_commands": commands,
        "grounding_report": ground,
        "tool_audit": tool_audit,
    }
    write_json(out / "HARNESS_REPORT.json", harness)
    write_pin_readme(out, harness)
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live Spark NeMo/NIM briefings for a4-D3a districts.")
    parser.add_argument("--d3a-dir", default=str(DEFAULT_D3A_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--remote-host", default=DEFAULT_REMOTE_HOST)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--nat-venv", default=DEFAULT_NAT_VENV)
    parser.add_argument("--nim-endpoint", default=DEFAULT_NIM_ENDPOINT)
    parser.add_argument("--nim-model", default=DEFAULT_NIM_MODEL)
    args = parser.parse_args()
    report = run_live_briefings(args.d3a_dir, args.output_dir, args.remote_host, args.remote_dir, args.nat_venv, args.nim_endpoint, args.nim_model)
    print(f"a4-D3a Live NeMo/NIM District Briefings: {report['status']}")
    print(f"Output: {args.output_dir}")
    for key, value in report["checks"].items():
        print(f"- {key}: {'PASS' if value else 'FAIL'}")
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
