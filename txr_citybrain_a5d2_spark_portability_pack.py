"""
A5-D2 Spark/NIM/NeMo portability pack builder.

This packages the green A5-D1 deterministic operator-query slice for transfer
to DGX Spark. The bundle remains canonical-first: deterministic truth comes
from A5-D1 over frozen a4·D2 artifacts, while NIM is an optional narration layer.
"""

from __future__ import annotations

import argparse
import json
import hashlib
import os
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_A5D1_DIR = ROOT / "outputs" / "a5d1_operator_query"
DEFAULT_A4D2_DIR = ROOT / "outputs" / "a5_dob_district_enrichment"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "a5d2_spark_portability_pack"

BOUNDARY_STATEMENT = (
    "DOB enrichment is built from the current harvested DOB subset, capped and "
    "deduped across sample/chunk files, not full NYC DOB history. Counts are subset counts."
)

TASK_LABEL = "A5-D2 Spark/NIM/NeMo Portability Pack"
SPINE_NAMING = {
    "a5": "a5 = Action Core / NeMo+NIM / DGX Spark",
    "a5_d1": "a5·D1 = deterministic operator query",
    "a5_d2": "a5·D2 = Spark portability pack",
    "a4_d2": "a4·D2 = DOB district enrichment",
}
HERO_BBL = "1010607502"
HERO_BIN = "1026676"
HERO_COMPLAINT = "event:us-nyc:dob_complaint:1366080"
EXPECTED_HERO_COUNTS = {
    "dob_permit_issuance": 1,
    "dob_now_filings": 12,
    "dob_complaints": 9,
}
REQUIRED_QUERY_TYPES = {
    "parcel_profile",
    "building_profile",
    "complaint_search",
    "permit_search",
    "party_search",
    "reachability",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(p for p in root.rglob("*") if p.is_file())
    }


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def run_command(args: list[str], cwd: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        env=env,
    )
    return {
        "cmd": args,
        "cwd": cwd.as_posix(),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def gate(gate_id: str, name: str, passed: bool, details: list[str] | None = None, checked: int = 1) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "checked": checked,
        "failed": 0 if passed else 1,
        "details": details or [],
    }


def nim_module_source() -> str:
    source = r'''
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from typing import Any


BOUNDARY_STATEMENT = __BOUNDARY__


def _grounding_inputs(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    counts = evidence_bundle.get("counts") or {}
    selected_counts = {
        key: counts.get(key)
        for key in sorted(counts)
        if key in {
            "linked_buildings",
            "linked_permits",
            "linked_dob_complaints",
            "linked_parties",
            "source_rows",
            "matching_complaints",
            "matching_permits",
            "matching_parties",
            "resolution_method_counts",
            "party_confidence_tiers",
            "paths_found",
            "reached_entity_types",
            "hero_relation_sequence",
        }
    }
    return {
        "boundary_statement": BOUNDARY_STATEMENT,
        "query_id": evidence_bundle.get("query_id"),
        "query_type": evidence_bundle.get("query_type"),
        "answer_facts": evidence_bundle.get("answer_facts") or [],
        "counts": selected_counts,
        "warnings": evidence_bundle.get("warnings") or [],
        "provenance_summary": evidence_bundle.get("provenance_summary") or [],
        "confidence_summary": evidence_bundle.get("confidence_summary") or [],
    }


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _empty_result(mode: str, model: str | None, endpoint: str | None, grounding_hash: str, warnings: list[str]) -> dict:
    return {
        "enabled": False,
        "mode": mode,
        "model": model,
        "endpoint": endpoint,
        "text": None,
        "grounding_inputs_hash": grounding_hash,
        "boundary_statement": BOUNDARY_STATEMENT,
        "warnings": warnings,
    }


def narrate_evidence_bundle(
    evidence_bundle: dict,
    nim_endpoint: str | None = None,
    nim_model: str | None = None,
    timeout_s: int = 60,
    dry_run: bool = False,
) -> dict:
    """Return optional narration over deterministic A5-D1 evidence only.

    The narration layer is not allowed to compute counts, alter graph paths, or
    invent entities. It receives only answer_facts, selected counts, warnings,
    provenance/confidence summaries, and the subset boundary statement.
    """
    grounding = _grounding_inputs(evidence_bundle)
    grounding_hash = _hash_payload(grounding)
    if dry_run:
        fact_count = len(grounding.get("answer_facts") or [])
        return {
            "enabled": True,
            "mode": "dry_run",
            "model": nim_model or "dry-run",
            "endpoint": nim_endpoint,
            "text": (
                f"Dry-run narration grounded in {fact_count} deterministic facts. "
                f"{BOUNDARY_STATEMENT}"
            ),
            "grounding_inputs_hash": grounding_hash,
            "boundary_statement": BOUNDARY_STATEMENT,
            "warnings": [],
        }
    if not nim_endpoint:
        return _empty_result("disabled", nim_model, nim_endpoint, grounding_hash, ["NIM endpoint not configured."])

    endpoint = nim_endpoint.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint = f"{endpoint}/v1/chat/completions"
    prompt = (
        "Narrate only from this JSON grounding payload. Do not compute counts, "
        "invent entities, invent dates, invent parties, or override deterministic evidence.\n\n"
        + json.dumps(grounding, indent=2, sort_keys=True, ensure_ascii=False)
    )
    request_payload = {
        "model": nim_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You narrate TXR City Brain evidence without adding facts."},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = payload["choices"][0]["message"]["content"]
        return {
            "enabled": True,
            "mode": "nim",
            "model": nim_model,
            "endpoint": nim_endpoint,
            "text": text,
            "grounding_inputs_hash": grounding_hash,
            "boundary_statement": BOUNDARY_STATEMENT,
            "warnings": [],
        }
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as exc:
        return _empty_result("failed", nim_model, nim_endpoint, grounding_hash, [f"NIM narration failed gracefully: {exc}"])
'''
    return source.replace("__BOUNDARY__", repr(BOUNDARY_STATEMENT)).lstrip()


def a5d1_smoke_script() -> str:
    return r'''
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BUNDLE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUNDLE_ROOT))

from txr_citybrain_a5d1_operator_query import run_a5d1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A5-D1 deterministic smoke from the portability bundle.")
    parser.add_argument("--input-dir", default="data/a4d2_snapshot")
    parser.add_argument("--output-dir", default="smoke_outputs/a5d1_local_smoke")
    parser.add_argument("--no-nim", action="store_true")
    args = parser.parse_args()

    input_dir = (BUNDLE_ROOT / args.input_dir).resolve()
    output_dir = (BUNDLE_ROOT / args.output_dir).resolve()
    report = run_a5d1(
        input_dir,
        output_dir,
        nim={"disabled": True, "endpoint": None, "model": None},
    )
    print(json.dumps({
        "status": report.get("status"),
        "exit_code": report.get("exit_code"),
        "output_dir": output_dir.as_posix(),
        "boundary_statement": report.get("boundary_statement"),
    }, indent=2, sort_keys=True))
    return int(report.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
'''.lstrip()


def nim_smoke_script() -> str:
    return r'''
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BUNDLE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUNDLE_ROOT))

from txr_citybrain_nim_narration import narrate_evidence_bundle


def load_bundle(bundle_root: Path, evidence_path: str | None) -> dict:
    if evidence_path:
        path = (bundle_root / evidence_path).resolve()
    else:
        path = bundle_root / "data" / "a5d1_outputs" / "evidence_bundles" / "q01_parcel_profile_d98017ca.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run optional NIM narration smoke.")
    parser.add_argument("--bundle-dir", default=str(BUNDLE_ROOT))
    parser.add_argument("--evidence-bundle", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default="citybrain-nim-smoke")
    parser.add_argument("--timeout-s", type=int, default=5)
    parser.add_argument("--output-file", default=None)
    args = parser.parse_args()

    bundle_root = Path(args.bundle_dir).resolve()
    evidence = load_bundle(bundle_root, args.evidence_bundle)
    before_facts = json.dumps(evidence.get("answer_facts", []), sort_keys=True)
    narration = narrate_evidence_bundle(
        evidence,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
        timeout_s=args.timeout_s,
        dry_run=args.dry_run,
    )
    after_facts = json.dumps(evidence.get("answer_facts", []), sort_keys=True)
    payload = {
        "status": "PASS" if before_facts == after_facts and narration.get("mode") in {"dry_run", "disabled", "failed", "nim"} else "FAIL",
        "deterministic_facts_unchanged": before_facts == after_facts,
        "llm_narration": narration,
        "boundary_statement": evidence.get("boundary_statement"),
    }
    default_name = "nim_dry_run_narration.json" if args.dry_run else "nim_fail_safe_narration.json"
    output_file = Path(args.output_file) if args.output_file else bundle_root / "smoke_outputs" / default_name
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''.lstrip()


def spark_smoke_script() -> str:
    return r'''
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BUNDLE_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Spark-ready Parquet smoke.")
    parser.add_argument("--data-dir", default="data/a4d2_snapshot")
    parser.add_argument("--output-file", default="smoke_outputs/spark_smoke.json")
    args = parser.parse_args()

    data_dir = (BUNDLE_ROOT / args.data_dir).resolve()
    entity_path = data_dir / "canonical_entities.parquet"
    edge_path = data_dir / "canonical_edges.parquet"
    mode = "pandas_fallback"
    error = None
    try:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.master("local[1]").appName("citybrain-a5d2-smoke").getOrCreate()
        entities = spark.read.parquet(str(entity_path)).count()
        edges = spark.read.parquet(str(edge_path)).count()
        spark.stop()
        mode = "pyspark"
    except Exception as exc:
        error = str(exc)
        import pandas as pd

        entities = len(pd.read_parquet(entity_path))
        edges = len(pd.read_parquet(edge_path))
    payload = {
        "status": "PASS" if entities == 302 and edges == 296 else "FAIL",
        "mode": mode,
        "fallback_error": error,
        "entities": entities,
        "edges": edges,
        "expected": {"entities": 302, "edges": 296},
    }
    output_file = (BUNDLE_ROOT / args.output_file).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''.lstrip()


def bundle_gate_script() -> str:
    return r'''
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


BUNDLE_ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str]) -> dict:
    proc = subprocess.run(args, cwd=str(BUNDLE_ROOT), text=True, capture_output=True)
    return {"cmd": args, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local A5-D2 portability smoke gates from the unpacked bundle.")
    parser.parse_args()
    checks = {
        "a5d1_local_smoke": run([sys.executable, "scripts/run_a5d1_local_smoke.py", "--no-nim"]),
        "nim_dry_run": run([sys.executable, "scripts/run_nim_narration_smoke.py", "--dry-run"]),
        "nim_fail_safe": run([
            sys.executable,
            "scripts/run_nim_narration_smoke.py",
            "--nim-endpoint",
            "http://127.0.0.1:9",
            "--nim-model",
            "broken-smoke",
            "--timeout-s",
            "2",
        ]),
        "spark_smoke": run([sys.executable, "scripts/run_spark_smoke.py"]),
    }
    status = "PASS" if all(item["returncode"] == 0 for item in checks.values()) else "FAIL"
    payload = {"status": status, "checks": checks}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''.lstrip()


def docs(output_dir: Path) -> dict[str, str]:
    return {
        "README.md": f"""
# A5-D2 Spark/NIM/NeMo Portability Pack

{BOUNDARY_STATEMENT}

## Naming

- {SPINE_NAMING['a5']}.
- {SPINE_NAMING['a5_d1']}.
- {SPINE_NAMING['a5_d2']}.
- {SPINE_NAMING['a4_d2']}.

This pack prepares the green a5·D1 deterministic operator-query slice for DGX Spark transfer and optional NIM narration. It does not rename the operator query to A6, and it treats a4·D2 as the frozen DOB district enrichment input.

## Contents

- `bundle/` contains the portable code, smoke scripts, configs, and scoped data snapshots.
- `SPARK_RUNBOOK.md` contains the copy/run steps.
- `NIM_NARRATION_CONTRACT.md` defines the optional narration wrapper.
- `NEMO_AGENT_CONTRACT.md` defines the future single-tool NeMo agent contract.
- `A5D2_HARNESS_REPORT.json` records the portability gate results.

## Status

Run `python scripts/run_a5d2_portability_gate.py --input-dir outputs/a5d1_operator_query --a4d2-dir outputs/a5_dob_district_enrichment --output-dir outputs/a5d2_spark_portability_pack` from the repo root to rebuild and validate this pack.

Output directory: `{output_dir.as_posix()}`
""",
        "SPARK_RUNBOOK.md": f"""
# Spark Runbook

{BOUNDARY_STATEMENT}

## Naming

- {SPINE_NAMING['a5']}.
- {SPINE_NAMING['a5_d1']}.
- {SPINE_NAMING['a5_d2']}.
- {SPINE_NAMING['a4_d2']}.

## Steps

1. Copy `outputs/a5d2_spark_portability_pack/bundle/` to the DGX Spark host.
2. Create a Python environment, for example `python -m venv .venv`.
3. Install requirements. If the Spark host has no internet access, copy wheel files separately and install from that offline wheelhouse. Use `pip install -r requirements-dev-smoke.txt` for deterministic smoke, and `pip install -r requirements-spark.txt` where PySpark is needed.
4. Run deterministic smoke: `python scripts/run_a5d1_local_smoke.py --no-nim`.
5. Run the A5-D1 gate from the bundle: `python txr_citybrain_a5d1_operator_query.py --input-dir data/a4d2_snapshot --output-dir smoke_outputs/a5d1_cli_gate --run-gates --no-nim`.
6. Run NIM dry-run narration smoke: `python scripts/run_nim_narration_smoke.py --dry-run`.
7. Configure a real NIM endpoint by copying `config/nim_config.example.json` and filling in endpoint/model outside source control.
8. Run real NIM narration smoke: `python scripts/run_nim_narration_smoke.py --nim-endpoint <url> --nim-model <model>`.
9. Optionally wrap with NeMo Agent Toolkit using the contract in `NEMO_AGENT_CONTRACT.md`; the first agent has one deterministic tool only.
10. Capture output hashes with `python scripts/run_a5d2_portability_gate.py` and archive `SHA256SUMS.json`.
""",
        "NIM_NARRATION_CONTRACT.md": f"""
# NIM Narration Contract

{BOUNDARY_STATEMENT}

## Purpose

NIM narration is optional for {SPINE_NAMING['a5']}. It narrates the deterministic evidence produced by a5·D1; it does not compute truth.

## Callable

```python
def narrate_evidence_bundle(
    evidence_bundle: dict,
    nim_endpoint: str | None = None,
    nim_model: str | None = None,
    timeout_s: int = 60,
    dry_run: bool = False,
) -> dict:
    ...
```

## Rules

- `dry_run=True` returns deterministic mock narration.
- Missing `nim_endpoint` returns `mode: disabled` without failing deterministic gates.
- Failed NIM calls return `mode: failed` with warnings.
- NIM must not compute counts.
- NIM must not invent entities, edges, dates, parties, or source counts.
- The prompt includes the subset boundary statement.
- The prompt includes only `answer_facts`, selected `counts`, selected `warnings`, and provenance/confidence summaries.
- Output is stored separately under `llm_narration`, never mixed into deterministic facts.
""",
        "NEMO_AGENT_CONTRACT.md": f"""
# NeMo Agent Contract

{BOUNDARY_STATEMENT}

## Purpose

The first NeMo Agent Toolkit wrapper for a5 uses exactly one deterministic tool over the a5·D1 operator-query layer. The agent may decide which query to run, but it must not compute truth.

## Tool

Name: `citybrain_operator_query`

Input:

```json
{{
  "query_type": "parcel_profile | building_profile | complaint_search | permit_search | party_search | reachability",
  "parameters": {{}},
  "include_narration": false
}}
```

Output:

```json
{{
  "status": "PASS | FAIL",
  "evidence_bundle": {{}},
  "deterministic_answer": {{}},
  "optional_nim_narration": {{}},
  "boundary_statement": "{BOUNDARY_STATEMENT}"
}}
```

## Allowed Behavior

- Choose a supported query type.
- Call `citybrain_operator_query`.
- Request optional NIM narration over deterministic evidence.

## Forbidden Behavior

- Compute counts.
- Alter counts, paths, source refs, confidence, or provenance.
- Invent entities, edges, dates, parties, or source counts.
- Override deterministic evidence.
- Rename a4·D2 DOB district enrichment as a5 or call the operator query A6.

## Failure Behavior

If deterministic retrieval fails, return `status: FAIL` and the evidence bundle warnings. If NIM fails, preserve the deterministic answer and return NIM failure metadata.

## Expected First Spark Smoke Test

Run `python scripts/run_a5d1_local_smoke.py --no-nim`, then call `citybrain_operator_query` for the hero parcel `1010607502` and verify `1 / 12 / 9` source-row counts.
""",
    }


def config_payloads() -> dict[str, str]:
    return {
        "bundle/requirements-spark.txt": "pandas>=2.0\npyarrow>=14.0\npydantic>=2.0\npyspark>=3.5\n",
        "bundle/requirements-dev-smoke.txt": "pandas>=2.0\npyarrow>=14.0\npydantic>=2.0\n",
        "bundle/.env.example": "NIM_ENDPOINT=\nNIM_MODEL=\nCITYBRAIN_BOUNDARY_STATEMENT=\""
        + BOUNDARY_STATEMENT
        + "\"\n",
        "bundle/config/nim_config.example.json": json.dumps(
            {
                "boundary_statement": BOUNDARY_STATEMENT,
                "nim_endpoint": "http://localhost:8000",
                "nim_model": "replace-with-nim-model",
                "timeout_s": 60,
                "mode": "optional_narration_only",
            },
            indent=2,
        )
        + "\n",
        "bundle/config/nemo_agent_config.example.yaml": f"""# {TASK_LABEL}
boundary_statement: "{BOUNDARY_STATEMENT}"
agent:
  name: citybrain_action_core_a5d2
  purpose: deterministic operator query with optional NIM narration
tools:
  - name: citybrain_operator_query
    input_schema:
      query_type: parcel_profile | building_profile | complaint_search | permit_search | party_search | reachability
      parameters: object
      include_narration: boolean
    output_schema:
      status: PASS | FAIL
      evidence_bundle: object
      deterministic_answer: object
      optional_nim_narration: object
      boundary_statement: string
rules:
  - The agent may choose query type and call the deterministic tool.
  - The agent must not compute truth, alter counts, invent paths, or override deterministic evidence.
  - NIM narration is optional and grounded only in deterministic evidence.
""",
    }


def create_bundle(input_dir: Path, a4d2_dir: Path, output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    bundle = output_dir / "bundle"
    (bundle / "config").mkdir(parents=True, exist_ok=True)
    (bundle / "data").mkdir(parents=True, exist_ok=True)
    (bundle / "scripts").mkdir(parents=True, exist_ok=True)

    for rel, text in docs(output_dir).items():
        write_text(output_dir / rel, text)

    copy_file(ROOT / "txr_citybrain_a5d1_operator_query.py", bundle / "txr_citybrain_a5d1_operator_query.py")
    copy_file(ROOT / "txr_citybrain_schema_v1.py", bundle / "txr_citybrain_schema_v1.py")
    copy_file(ROOT / "txr_citybrain_harness.py", bundle / "txr_citybrain_harness.py")
    write_text(bundle / "txr_citybrain_nim_narration.py", nim_module_source())

    for rel, text in config_payloads().items():
        write_text(output_dir / rel, text)
    copy_file(input_dir / "query_catalog.json", bundle / "config" / "query_catalog.json")

    a4_snapshot = bundle / "data" / "a4d2_snapshot"
    a4_snapshot.mkdir(parents=True, exist_ok=True)
    a4_files = [
        "harness_report_a5.json",
        "a5_enrichment_summary.json",
        "district_cut_manifest.json",
        "canonical_entities.parquet",
        "canonical_edges.parquet",
        "graph_projection_nodes.parquet",
        "graph_projection_edges.parquet",
        "scenario_trace_hero_flow.json",
    ]
    for name in a4_files:
        copy_file(a4d2_dir / name, a4_snapshot / name)
    if (a4d2_dir / "snapshot").exists():
        copy_tree(a4d2_dir / "snapshot", a4_snapshot / "snapshot")

    copy_tree(input_dir, bundle / "data" / "a5d1_outputs")

    write_text(bundle / "scripts" / "run_a5d1_local_smoke.py", a5d1_smoke_script())
    write_text(bundle / "scripts" / "run_a5d2_portability_gate.py", bundle_gate_script())
    write_text(bundle / "scripts" / "run_nim_narration_smoke.py", nim_smoke_script())
    write_text(bundle / "scripts" / "run_spark_smoke.py", spark_smoke_script())


def manifest_payload(input_dir: Path, a4d2_dir: Path, output_dir: Path, input_hashes_before: dict[str, str], a4_hashes_before: dict[str, str]) -> dict[str, Any]:
    return {
        "task": TASK_LABEL,
        "generated_at": utc_now(),
        "boundary_statement": BOUNDARY_STATEMENT,
        "naming": SPINE_NAMING,
        "input_a5d1_dir": input_dir.as_posix(),
        "input_a4d2_dir": a4d2_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
        "frozen_input_hashes": {
            "a5d1": input_hashes_before,
            "a4d2": a4_hashes_before,
        },
        "bundle_contents": [
            "txr_citybrain_a5d1_operator_query.py",
            "txr_citybrain_schema_v1.py",
            "txr_citybrain_harness.py",
            "txr_citybrain_nim_narration.py",
            "requirements-spark.txt",
            "requirements-dev-smoke.txt",
            ".env.example",
            "config/nim_config.example.json",
            "config/nemo_agent_config.example.yaml",
            "config/query_catalog.json",
            "data/a4d2_snapshot/",
            "data/a5d1_outputs/",
            "scripts/run_a5d1_local_smoke.py",
            "scripts/run_a5d2_portability_gate.py",
            "scripts/run_nim_narration_smoke.py",
            "scripts/run_spark_smoke.py",
        ],
        "raw_data_policy": "No raw full DOB harvest files are included; only scoped canonical snapshots and A5-D1 outputs are copied.",
    }


def load_clean_parcel_counts(clean_output_dir: Path) -> dict[str, Any]:
    sample = read_json(clean_output_dir / "sample_query_results.json")
    for result in sample.get("results", []):
        if result.get("query_type") == "parcel_profile":
            return result["evidence_bundle"]["counts"]["source_rows"]
    return {}


def load_query_types(clean_output_dir: Path) -> set[str]:
    sample = read_json(clean_output_dir / "sample_query_results.json")
    return {result.get("query_type") for result in sample.get("results", [])}


def scan_text_files(root: Path) -> str:
    chunks: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".yaml", ".yml", ".txt", ".example"}:
            try:
                chunks.append(path.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                continue
    return "\n".join(chunks)


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(p for p in output_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"):
        hashes[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(
        output_dir / "SHA256SUMS.json",
        {
            "task": TASK_LABEL,
            "boundary_statement": BOUNDARY_STATEMENT,
            "generated_at": utc_now(),
            "hashes": hashes,
        },
    )
    return hashes


def run_a5d2_portability_gate_with_a4d2(input_dir: str, a4d2_dir: str, output_dir: str) -> dict:
    input_path = Path(input_dir).resolve()
    a4_path = Path(a4d2_dir).resolve()
    output_path = Path(output_dir).resolve()
    input_hashes_before = hash_tree(input_path)
    a4_hashes_before = hash_tree(a4_path)

    create_bundle(input_path, a4_path, output_path)
    write_json(output_path / "A5D2_SPARK_PORT_MANIFEST.json", manifest_payload(input_path, a4_path, output_path, input_hashes_before, a4_hashes_before))

    a5d1_report = read_json(input_path / "a5d1_harness_report.json")
    gates: list[dict[str, Any]] = []
    precond_pass = (
        (input_path / "a5d1_harness_report.json").exists()
        and a5d1_report.get("status") == "PASS"
        and a5d1_report.get("exit_code") == 0
        and a5d1_report.get("a4_d2_status_consumed") == "PASS"
        and a5d1_report.get("a2_preflight_consumed") == "PASS"
        and a5d1_report.get("a4_regression_consumed") == "PASS"
        and BOUNDARY_STATEMENT in json.dumps(a5d1_report)
    )
    gates.append(gate("A5D2-PRECOND", "A5-D1 and consumed a4·D2/a2/a4 statuses are green", precond_pass))

    required = [
        "README.md",
        "A5D2_SPARK_PORT_MANIFEST.json",
        "SPARK_RUNBOOK.md",
        "NIM_NARRATION_CONTRACT.md",
        "NEMO_AGENT_CONTRACT.md",
        "bundle/txr_citybrain_a5d1_operator_query.py",
        "bundle/txr_citybrain_schema_v1.py",
        "bundle/txr_citybrain_harness.py",
        "bundle/txr_citybrain_nim_narration.py",
        "bundle/requirements-spark.txt",
        "bundle/requirements-dev-smoke.txt",
        "bundle/.env.example",
        "bundle/config/nim_config.example.json",
        "bundle/config/nemo_agent_config.example.yaml",
        "bundle/config/query_catalog.json",
        "bundle/data/a4d2_snapshot/canonical_entities.parquet",
        "bundle/data/a4d2_snapshot/canonical_edges.parquet",
        "bundle/data/a5d1_outputs/a5d1_harness_report.json",
        "bundle/scripts/run_a5d1_local_smoke.py",
        "bundle/scripts/run_a5d2_portability_gate.py",
        "bundle/scripts/run_nim_narration_smoke.py",
        "bundle/scripts/run_spark_smoke.py",
    ]
    missing = [rel for rel in required if not (output_path / rel).exists()]
    gates.append(gate("A5D2-BUNDLE-COMPLETE", "Bundle contains required code, config, docs, data, and scripts", not missing, missing, checked=len(required)))

    disallowed_paths = []
    for path in output_path.rglob("*"):
        rel = path.relative_to(output_path).as_posix().lower()
        if path.is_file() and (
            "citybrain_data_harvest_pack" in rel
            or "/raw/" in f"/{rel}/"
            or rel.endswith(".csv")
            or rel.endswith(".zip")
            or rel.endswith(".gdb")
        ):
            disallowed_paths.append(rel)
        if path.is_file() and path.stat().st_size > 75 * 1024 * 1024:
            disallowed_paths.append(f"{rel} exceeds portability size guard")
    gates.append(gate("A5D2-NO-RAW-DATA-BLOAT", "No raw harvest files or large unnecessary data copied", not disallowed_paths, disallowed_paths))

    bundle = output_path / "bundle"
    clean_cmd = run_command(
        [sys.executable, "scripts/run_a5d1_local_smoke.py", "--input-dir", "data/a4d2_snapshot", "--output-dir", "smoke_outputs/a5d1_clean_run", "--no-nim"],
        cwd=bundle,
    )
    clean_output = bundle / "smoke_outputs" / "a5d1_clean_run"
    clean_pass = clean_cmd["returncode"] == 0 and (clean_output / "a5d1_harness_report.json").exists()
    gates.append(gate("A5D2-CLEAN-RUN", "Deterministic A5-D1 smoke runs from bundle path", clean_pass, [] if clean_pass else [clean_cmd["stdout"], clean_cmd["stderr"]]))

    hero_counts = load_clean_parcel_counts(clean_output) if clean_pass else {}
    hero_pass = all(hero_counts.get(key) == value for key, value in EXPECTED_HERO_COUNTS.items())
    gates.append(gate("A5D2-HERO-COUNTS", "Clean-run hero parcel counts match A5-D1", hero_pass, [] if hero_pass else [f"hero_counts={hero_counts}"]))

    query_types = load_query_types(clean_output) if clean_pass else set()
    missing_query_types = sorted(REQUIRED_QUERY_TYPES - query_types)
    gates.append(gate("A5D2-QUERY-COVERAGE", "Clean run exercises required query types", not missing_query_types, missing_query_types, checked=len(REQUIRED_QUERY_TYPES)))

    dry_cmd = run_command([sys.executable, "scripts/run_nim_narration_smoke.py", "--dry-run"], cwd=bundle)
    dry_output = bundle / "smoke_outputs" / "nim_dry_run_narration.json"
    dry_payload = read_json(dry_output) if dry_output.exists() else {}
    dry_pass = (
        dry_cmd["returncode"] == 0
        and dry_payload.get("status") == "PASS"
        and dry_payload.get("deterministic_facts_unchanged") is True
        and dry_payload.get("llm_narration", {}).get("mode") == "dry_run"
    )
    gates.append(gate("A5D2-NIM-DRY-RUN", "Dry-run NIM narration produces grounded metadata", dry_pass, [] if dry_pass else [dry_cmd["stdout"], dry_cmd["stderr"]]))

    fail_cmd = run_command(
        [
            sys.executable,
            "scripts/run_nim_narration_smoke.py",
            "--nim-endpoint",
            "http://127.0.0.1:9",
            "--nim-model",
            "broken-smoke",
            "--timeout-s",
            "2",
        ],
        cwd=bundle,
    )
    fail_output = bundle / "smoke_outputs" / "nim_fail_safe_narration.json"
    fail_payload = read_json(fail_output) if fail_output.exists() else {}
    fail_pass = (
        fail_cmd["returncode"] == 0
        and fail_payload.get("status") == "PASS"
        and fail_payload.get("deterministic_facts_unchanged") is True
        and fail_payload.get("llm_narration", {}).get("mode") == "failed"
        and clean_pass
    )
    gates.append(gate("A5D2-NIM-FAIL-SAFE", "Broken NIM endpoint fails gracefully without breaking deterministic query", fail_pass, [] if fail_pass else [fail_cmd["stdout"], fail_cmd["stderr"]]))

    spark_cmd = run_command([sys.executable, "scripts/run_spark_smoke.py"], cwd=bundle)
    spark_output = bundle / "smoke_outputs" / "spark_smoke.json"
    spark_payload = read_json(spark_output) if spark_output.exists() else {}

    nemo_text = (output_path / "NEMO_AGENT_CONTRACT.md").read_text(encoding="utf-8") if (output_path / "NEMO_AGENT_CONTRACT.md").exists() else ""
    yaml_text = (bundle / "config" / "nemo_agent_config.example.yaml").read_text(encoding="utf-8") if (bundle / "config" / "nemo_agent_config.example.yaml").exists() else ""
    nemo_pass = (
        "citybrain_operator_query" in nemo_text
        and "citybrain_operator_query" in yaml_text
        and nemo_text.count("citybrain_operator_query") >= 1
        and "must not compute truth" in nemo_text
    )
    gates.append(gate("A5D2-NEMO-CONTRACT", "NeMo single deterministic tool contract exists", nemo_pass))

    boundary_files = [
        "README.md",
        "SPARK_RUNBOOK.md",
        "A5D2_SPARK_PORT_MANIFEST.json",
        "NIM_NARRATION_CONTRACT.md",
        "NEMO_AGENT_CONTRACT.md",
        "bundle/smoke_outputs/nim_dry_run_narration.json",
    ]
    boundary_missing = [
        rel
        for rel in boundary_files
        if not (output_path / rel).exists() or BOUNDARY_STATEMENT not in (output_path / rel).read_text(encoding="utf-8")
    ]
    gates.append(gate("A5D2-BOUNDARY", "Boundary statement preserved in human-facing and narration artifacts", not boundary_missing, boundary_missing, checked=len(boundary_files)))

    combined = scan_text_files(output_path)
    bad_phrases = ["A5 DOB enrichment", "DOB enrichment is A5", "DOB district enrichment is A5", "A6 operator query", "operator query is A6"]
    naming_pass = (
        all(value in combined for value in SPINE_NAMING.values())
        and not any(phrase in combined for phrase in bad_phrases)
    )
    gates.append(gate("A5D2-NAMING", "a5/a5·D1/a5·D2/a4·D2 names are unambiguous", naming_pass, [] if naming_pass else ["required naming text missing or collision phrase found"]))

    input_hashes_after = hash_tree(input_path)
    a4_hashes_after = hash_tree(a4_path)
    no_mutation_pass = input_hashes_before == input_hashes_after and a4_hashes_before == a4_hashes_after
    gates.append(gate("A5D2-NO-MUTATION", "Frozen A5-D1 and a4·D2 inputs are byte-stable", no_mutation_pass))

    audit = {
        "task": TASK_LABEL,
        "boundary_statement": BOUNDARY_STATEMENT,
        "naming": SPINE_NAMING,
        "clean_run": clean_cmd,
        "spark_smoke": spark_cmd,
        "spark_smoke_payload": spark_payload,
        "nim_dry_run": dry_payload,
        "nim_fail_safe": fail_payload,
        "hero_counts": hero_counts,
        "query_types": sorted(query_types),
        "no_raw_data_bloat_details": disallowed_paths,
        "input_hashes_unchanged": no_mutation_pass,
    }
    write_json(output_path / "PORTABILITY_AUDIT.json", audit)

    status_without_hash = "PASS" if all(item["passed"] for item in gates) else "FAIL"
    report = {
        "task": TASK_LABEL,
        "boundary_statement": BOUNDARY_STATEMENT,
        "naming": SPINE_NAMING,
        "status": status_without_hash,
        "exit_code": 0 if status_without_hash == "PASS" else 1,
        "input_a5d1": a5d1_report.get("status"),
        "input_a4d2": a5d1_report.get("a4_d2_status_consumed"),
        "output": output_path.as_posix(),
        "checks": {
            "preconditions": gates[0]["passed"],
            "bundle_complete": gates[1]["passed"],
            "clean_run_from_bundle": clean_pass,
            "hero_counts": hero_pass,
            "query_coverage": not missing_query_types,
            "nim_dry_run": dry_pass,
            "nim_fail_safe": fail_pass,
            "nemo_contract": nemo_pass,
            "boundary": not boundary_missing,
            "naming": naming_pass,
            "no_mutation": no_mutation_pass,
        },
        "hero": {
            "parcel": HERO_BBL,
            "building": HERO_BIN,
            "complaint": HERO_COMPLAINT,
            "counts": hero_counts,
            "path": "resolves_to -> subject_of_permit -> performed_by -> has_building",
        },
        "gates": gates,
    }
    write_json(output_path / "A5D2_HARNESS_REPORT.json", report)
    hashes = write_hashes(output_path)
    expected_hash_files = sorted(
        path.relative_to(output_path).as_posix()
        for path in output_path.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.json"
    )
    hash_pass = sorted(hashes) == expected_hash_files and (output_path / "SHA256SUMS.json").exists()
    hash_gate = gate("A5D2-HASHES", "SHA256SUMS covers all generated files except itself", hash_pass, [] if hash_pass else ["hash coverage mismatch"], checked=len(expected_hash_files))
    gates.append(hash_gate)
    final_status = "PASS" if all(item["passed"] for item in gates) else "FAIL"
    report["status"] = final_status
    report["exit_code"] = 0 if final_status == "PASS" else 1
    report["checks"]["hashes"] = hash_pass
    report["gates"] = gates
    write_json(output_path / "A5D2_HARNESS_REPORT.json", report)
    write_hashes(output_path)
    return report


def run_a5d2_portability_gate(input_dir: str, output_dir: str) -> dict:
    return run_a5d2_portability_gate_with_a4d2(input_dir, str(DEFAULT_A4D2_DIR), output_dir)


def print_report(report: dict[str, Any]) -> None:
    checks = report.get("checks", {})
    lines = [
        f"{TASK_LABEL}: {report.get('status')}",
        f"Input A5-D1: {report.get('input_a5d1')}",
        f"Input A4-D2: {report.get('input_a4d2')}",
        f"Output: {report.get('output')}",
        "",
        "Checks:",
        f"- preconditions: {'PASS' if checks.get('preconditions') else 'FAIL'}",
        f"- bundle complete: {'PASS' if checks.get('bundle_complete') else 'FAIL'}",
        f"- clean run from bundle: {'PASS' if checks.get('clean_run_from_bundle') else 'FAIL'}",
        f"- hero counts: {'PASS' if checks.get('hero_counts') else 'FAIL'}",
        f"- query coverage: {'PASS' if checks.get('query_coverage') else 'FAIL'}",
        f"- NIM dry-run: {'PASS' if checks.get('nim_dry_run') else 'FAIL'}",
        f"- NIM fail-safe: {'PASS' if checks.get('nim_fail_safe') else 'FAIL'}",
        f"- NeMo contract: {'PASS' if checks.get('nemo_contract') else 'FAIL'}",
        f"- boundary: {'PASS' if checks.get('boundary') else 'FAIL'}",
        f"- naming: {'PASS' if checks.get('naming') else 'FAIL'}",
        f"- hashes: {'PASS' if checks.get('hashes') else 'FAIL'}",
    ]
    failed = [item for item in report.get("gates", []) if not item.get("passed")]
    if failed:
        lines.extend(["", "Failed gates:"])
        lines.extend(f"- {item['gate_id']}: {item.get('details')}" for item in failed)
    print("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_LABEL)
    parser.add_argument("--input-dir", default=str(DEFAULT_A5D1_DIR))
    parser.add_argument("--a4d2-dir", default=str(DEFAULT_A4D2_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)
    report = run_a5d2_portability_gate_with_a4d2(args.input_dir, args.a4d2_dir, args.output_dir)
    print_report(report)
    return int(report.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
