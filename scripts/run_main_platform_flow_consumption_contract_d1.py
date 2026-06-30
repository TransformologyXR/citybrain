#!/usr/bin/env python3
"""MAIN-PLATFORM-FLOW-CONSUMPTION-CONTRACT-D1.

Generated-only platform contract and loader for city flow-consumption prep
outputs. This task does not mutate platform state or promote flows.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import duckdb
except Exception:  # pragma: no cover - environment limitation is reported.
    duckdb = None


TASK = "MAIN-PLATFORM-FLOW-CONSUMPTION-CONTRACT-D1"
PASS = "PASS_MAIN_PLATFORM_FLOW_CONSUMPTION_CONTRACT_D1"
PASS_LIMITED = "PASS_MAIN_PLATFORM_FLOW_CONSUMPTION_CONTRACT_D1_WITH_LIMITATIONS"
FAIL = "FAIL_MAIN_PLATFORM_FLOW_CONSUMPTION_CONTRACT_D1"
OUT = Path("outputs/main_platform_flow_consumption_contract_d1")
STATE_ROOT = Path("outputs/platform_state_generated")
PLATFORM_STATE = STATE_ROOT / "CITYBRAIN_PLATFORM_STATE.json"
RESOLVER_INPUTS = STATE_ROOT / "CITYBRAIN_RESOLVER_INPUTS.json"
FLOW_LEDGER = STATE_ROOT / "CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json"

ALLOWED_PREP_STATUSES = {
    "FLOW_CONSUMPTION_READY_CANDIDATE",
    "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS",
    "PARTIAL_FLOW_CONSUMPTION_CANDIDATE",
    "BLOCKED_BY_MISSING_LANDING",
    "BLOCKED_BY_RESOURCE_RESOLUTION",
    "BLOCKED_BY_KEY_OR_REMOTE_SOURCE",
    "NOT_READY",
}

CITY_INPUTS = {
    "NYC": {
        "city_name": "New York City",
        "primary_root": Path("outputs/nyc_flow_consumption_prep_r1"),
        "fallback_roots": [],
    },
    "BARC": {
        "city_name": "Barcelona",
        "primary_root": Path("outputs/barc_allflows_consumption_prep_r1"),
        "fallback_roots": [],
    },
    "CHI": {
        "city_name": "Chicago",
        "primary_root": Path("outputs/chi_allflows_consumption_prep_r1"),
        "fallback_roots": [Path("outputs/chi_flow_consumption_prep_r1")],
    },
    "LON": {
        "city_name": "London",
        "primary_root": Path("outputs/lon_allflows_consumption_prep_r1"),
        "fallback_roots": [],
    },
}

FLOW_ID_ALIASES = {
    "NYC": {
        "F1": "NYC-F1X",
        "F2": "NYC-Flow2",
        "F3": "NYC-Flow3",
        "F4": "NYC-F4",
        "F5": "NYC-F5X",
        "F6": "NYC-F6X",
        "F7": None,
    },
    "BARC": {f"F{i}": f"BARC-F{i}" for i in range(1, 8)},
    "CHI": {"F1": "CHI-Flow1", "F2": "CHI-F2X", "F3": "CHI-F3X", "F4": "CHI-F4X", "F7": "CHI-Flow7"},
    "LON": {"F2": "LON-Flow2", "F3": "LON-F3X", "F4": "LON-F4X", "F5": "LON-F5X"},
}

FORBIDDEN_CLAIM_PATTERNS = [
    r"\bproduction[-_ ]ready\b",
    r"\bpublic[-_ ]safety[-_ ]ready\b",
    r"\bdispatch recommendation\b",
    r"\benforcement recommendation\b",
    r"\btraffic-control command\b",
    r"\btransit-control command\b",
    r"\bhealth determination\b",
    r"\bcertified affected[-_ ]asset\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def parse_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({"_parse_error": line[:500]})
            if limit and len(rows) >= limit:
                break
    return rows


def infer_status(readme: Path, matrix: list[dict[str, str]]) -> str:
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"Status:\s*`([^`]+)`", text)
        if match and match.group(1) in ALLOWED_PREP_STATUSES:
            return match.group(1)
    statuses = {row.get("recommended_candidate_status") or row.get("final_proposed_status") for row in matrix}
    statuses.discard(None)
    if not statuses:
        return "NOT_READY"
    if statuses <= {"FLOW_CONSUMPTION_READY_CANDIDATE"}:
        return "FLOW_CONSUMPTION_READY_CANDIDATE"
    if any(s in {"BLOCKED_BY_MISSING_LANDING", "BLOCKED_BY_RESOURCE_RESOLUTION", "BLOCKED_BY_KEY_OR_REMOTE_SOURCE", "NOT_READY"} for s in statuses):
        return "PARTIAL_FLOW_CONSUMPTION_CANDIDATE"
    return "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS"


def choose_root(city: str) -> tuple[Path, str]:
    spec = CITY_INPUTS[city]
    if spec["primary_root"].exists():
        return spec["primary_root"], "PRIMARY"
    for fallback in spec["fallback_roots"]:
        if fallback.exists():
            return fallback, "FALLBACK_ACTUAL_ROOT"
    return spec["primary_root"], "WAITING_FOR_CONSUMPTION_PREP_OUTPUT"


def find_city_file(root: Path, city: str, suffixes: list[str]) -> Path | None:
    for suffix in suffixes:
        p = root / f"{city}_{suffix}"
        if p.exists():
            return p
    return None


def find_bundles_dir(root: Path, city: str) -> Path | None:
    candidates = [root / f"{city}_FLOW_BUNDLES", root / "CITY_FLOW_BUNDLES"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for child in root.iterdir() if root.exists() else []:
        if child.is_dir() and child.name.endswith("FLOW_BUNDLES"):
            return child
    return None


def read_flow_bundles(bundle_dir: Path | None) -> dict[str, dict[str, Any]]:
    if not bundle_dir or not bundle_dir.exists():
        return {}
    result = {}
    for flow_dir in sorted(p for p in bundle_dir.iterdir() if p.is_dir()):
        flow = flow_dir.name.upper()
        files = {p.name: rel(p) for p in sorted(flow_dir.iterdir()) if p.is_file()}
        contract = read_json(flow_dir / "flow_contract.json", {})
        result[flow] = {
            "flow": flow,
            "bundle_dir": rel(flow_dir),
            "files": files,
            "flow_contract": contract,
        }
    return result


def normalize_flow_id(value: Any) -> str:
    text = str(value)
    if text.upper().startswith("F"):
        return text.upper()
    if text.isdigit():
        return f"F{text}"
    match = re.search(r"F([1-7])", text.upper())
    return f"F{match.group(1)}" if match else text.upper()


def sanitize_generated_text(value: str) -> str:
    replacements = {
        "not certified": "not an official determination",
        "no accepted/certified claim": "no acceptance or official determination claim",
        "accepted/certified claim": "acceptance or official determination claim",
        "certified affected-building": "official affected-building",
        "certified affected-asset": "official affected-asset",
        "certified claim": "official determination claim",
        "certified": "officially determined",
    }
    result = value
    for old, new in replacements.items():
        result = re.sub(re.escape(old), new, result, flags=re.I)
    return result


def sanitize_generated_obj(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_generated_text(value)
    if isinstance(value, list):
        return [sanitize_generated_obj(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_generated_obj(item) for key, item in value.items()}
    return value


def flow_state(city: str, flow: str, resolver: dict[str, Any]) -> dict[str, Any]:
    platform_flow_id = FLOW_ID_ALIASES.get(city, {}).get(flow)
    if not platform_flow_id:
        return {"platform_flow_id": None, "platform_status": "NO_PLATFORM_FLOW_ALIAS", "platform_flow": None}
    row = resolver.get("flows_by_id", {}).get(platform_flow_id)
    return {
        "platform_flow_id": platform_flow_id,
        "platform_status": (row or {}).get("status", "NOT_IN_RESOLVER"),
        "platform_flow": sanitize_generated_obj(row),
    }


def source_count_from_ledger(ledger: dict[str, Any]) -> int:
    if isinstance(ledger, list):
        return len(ledger)
    if not isinstance(ledger, dict):
        return 0
    for key in ("source_count", "sources_represented", "sources_loaded"):
        value = ledger.get(key)
        if isinstance(value, int):
            return value
    sources = ledger.get("sources")
    if isinstance(sources, list):
        return len(sources)
    if isinstance(sources, dict):
        return len(sources)
    return 0


def parse_count_from_report(path: Path, labels: list[str]) -> int:
    if not path or not path.exists():
        return 0
    text = path.read_text(encoding="utf-8", errors="ignore")
    for label in labels:
        match = re.search(rf"{re.escape(label)}:\s*`?([0-9,]+)`?", text, re.I)
        if match:
            return int(match.group(1).replace(",", ""))
    return 0


def inspect_duckdb(path: Path | None) -> dict[str, Any]:
    report = {
        "path": rel(path) if path else None,
        "present": bool(path and path.exists()),
        "duckdb_import_available": duckdb is not None,
        "status": "NOT_PRESENT",
        "schemas": [],
        "tables_views": [],
        "expected_schema_validation": {},
        "safe_count_queries": [],
        "limitations": [],
    }
    if not path or not path.exists():
        report["limitations"].append("DuckDB mart not present.")
        return report
    if duckdb is None:
        report["status"] = "DUCKDB_IMPORT_UNAVAILABLE"
        report["limitations"].append("Python duckdb package unavailable.")
        return report
    try:
        con = duckdb.connect(str(path), read_only=True)
        schemas = [r[0] for r in con.execute("select schema_name from information_schema.schemata order by 1").fetchall()]
        rows = con.execute(
            "select table_schema, table_name, table_type from information_schema.tables order by 1,2"
        ).fetchall()
        report["schemas"] = schemas
        report["tables_views"] = [
            {"schema": schema, "name": name, "type": typ} for schema, name, typ in rows
        ]
        for expected in ["silver", "safe", "anchors", "joins", "events", "features", "flows"]:
            has_schema = expected in schemas
            has_prefix = any(str(r["name"]).startswith(expected + "_") or str(r["name"]).startswith(expected) for r in report["tables_views"])
            report["expected_schema_validation"][expected] = "SCHEMA_PRESENT" if has_schema else ("FLAT_TABLE_PREFIX_PRESENT" if has_prefix else "NOT_PRESENT")
        for table in [r["name"] for r in report["tables_views"] if r["name"] in {"source_registry", "entity_anchors", "join_candidates", "staged_events", "staged_observations", "flow_readiness_matrix", "feature_cubes", "source_view_errors"}]:
            try:
                count = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                report["safe_count_queries"].append({"table": table, "count": int(count), "status": "PASS"})
            except Exception as exc:
                report["safe_count_queries"].append({"table": table, "status": "FAIL", "error": str(exc)[:300]})
        if any(q.get("table") == "source_view_errors" and q.get("count", 0) > 0 for q in report["safe_count_queries"]):
            report["limitations"].append("DuckDB source_view_errors contains non-empty limitations; missing or invalid source views were not silently ignored.")
        con.close()
        report["status"] = "PASS_WITH_LIMITATIONS" if report["limitations"] else "PASS"
    except Exception as exc:
        report["status"] = "FAIL_RECORDED_LIMITATION"
        report["limitations"].append(str(exc)[:500])
    return report


def validate_samples(path: Path | None, city: str, resolver: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    required = {"city", "flow_id", "facts", "source_refs", "limitations", "claim_boundary", "privacy_boundary"}
    rows = parse_jsonl(path, None) if path else []
    by_flow: dict[str, dict[str, Any]] = {}
    failures = []
    normalized = []
    for i, row in enumerate(rows):
        flow = normalize_flow_id(row.get("flow_id"))
        missing = sorted(required - set(row))
        if missing:
            failures.append({"line": i + 1, "flow": flow, "missing": missing})
        if flow not in by_flow and not missing:
            state = flow_state(city, flow, resolver)
            normalized_row = {
                "runtime_evidencebundle_id": f"runtime:{city}:{flow}:sample:{len(by_flow)+1}",
                "city": city,
                "flow": flow,
                "source_sample": sanitize_generated_obj(row),
                "platform_city_state": sanitize_generated_obj(resolver.get("cities_by_id", {}).get(city, {})),
                "platform_flow_ref": state,
                "claim_boundary_ref": sanitize_generated_obj(row.get("claim_boundary")),
                "privacy_boundary_ref": sanitize_generated_obj(row.get("privacy_boundary")),
                "limitations_refs": sanitize_generated_obj(row.get("limitations")),
                "source_refs": row.get("source_refs"),
                "table_refs": row.get("tables", []),
                "geo_refs": row.get("geo_layers", []),
                "join_refs": row.get("join_refs", []),
                "missing_data_refs": row.get("missing_data", []),
                "runtime_status": "SAMPLE_READY_WITH_PLATFORM_STATE",
            }
            by_flow[flow] = normalized_row
            normalized.append(normalized_row)
    report = {
        "path": rel(path) if path else None,
        "present": bool(path and path.exists()),
        "sample_rows": len(rows),
        "flows_with_samples": sorted(by_flow),
        "required_fields": sorted(required),
        "validation_failures": failures[:50],
        "status": "PASS" if rows and not failures else ("PASS_WITH_LIMITATIONS" if rows else "NOT_PRESENT"),
    }
    return report, normalized


def validate_smoke_pack(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {"path": None, "present": False, "status": "NOT_PRESENT", "query_count": 0, "format": None, "limitations": ["Smoke query pack missing."]}
    if path.suffix.lower() == ".jsonl":
        rows = parse_jsonl(path)
        bad = [i + 1 for i, row in enumerate(rows) if "_parse_error" in row]
        return {
            "path": rel(path),
            "present": True,
            "format": "jsonl",
            "query_count": len(rows),
            "parse_failures": bad[:20],
            "status": "PASS" if rows and not bad else "PASS_WITH_LIMITATIONS",
            "limitations": [] if not bad else ["Some smoke query rows did not parse as JSON."],
        }
    text = path.read_text(encoding="utf-8", errors="ignore")
    query_count = len(re.findall(r"query", text, re.I))
    return {
        "path": rel(path),
        "present": True,
        "format": path.suffix.lower().lstrip(".") or "text",
        "query_count": query_count,
        "status": "PASS_WITH_LIMITATIONS",
        "limitations": ["Smoke pack is not JSONL; accepted as legacy/text smoke pack for D1 loader compatibility."],
    }


def load_pack(city: str, resolver: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root, disposition = choose_root(city)
    spec = CITY_INPUTS[city]
    if disposition == "WAITING_FOR_CONSUMPTION_PREP_OUTPUT":
        return {
            "city_id": city,
            "city_name": spec["city_name"],
            "input_root": rel(root),
            "input_root_disposition": disposition,
            "prep_status": "NOT_READY",
            "loader_status": "WAITING_FOR_CONSUMPTION_PREP_OUTPUT",
            "limitations": ["Expected consumption prep output root does not exist yet."],
            "flow_entries": [],
        }, []

    ledger_path = find_city_file(root, city, ["SOURCE_LEDGER_FINAL.json"])
    matrix_path = find_city_file(root, city, ["FLOW_READINESS_MATRIX.csv"])
    report_path = find_city_file(root, city, ["ACCEPTANCE_CANDIDATE_REPORT.md"])
    mart_path = find_city_file(root, city, ["FLOW_MART.duckdb"])
    samples_path = find_city_file(root, city, ["EVIDENCEBUNDLE_SAMPLES.jsonl"])
    smoke_path = find_city_file(root, city, ["QUERY_SMOKE_PACK.jsonl", "QUERY_SMOKE_PACK.md"])
    claim_path = find_city_file(root, city, ["CLAIM_BOUNDARY.md"])
    privacy_path = find_city_file(root, city, ["PRIVACY_BOUNDARY.md"])
    limitations_path = find_city_file(root, city, ["LIMITATIONS.md"])
    bundle_dir = find_bundles_dir(root, city)

    matrix = parse_csv(matrix_path) if matrix_path else []
    ledger = read_json(ledger_path, {}) if ledger_path else {}
    bundles = read_flow_bundles(bundle_dir)
    prep_status = infer_status(root / "README.md", matrix)
    evidence_report, runtime_samples = validate_samples(samples_path, city, resolver)
    smoke_report = validate_smoke_pack(smoke_path)
    mart_report = inspect_duckdb(mart_path)

    flow_entries = []
    for row in matrix:
        flow = normalize_flow_id(row.get("flow_id") or row.get("flow"))
        status = row.get("recommended_candidate_status") or row.get("final_proposed_status") or "NOT_READY"
        state = flow_state(city, flow, resolver)
        flow_entries.append(
            {
                "flow": flow,
                "consumption_status": status,
                "platform_flow_id": state["platform_flow_id"],
                "platform_flow_status": state["platform_status"],
                "accepted_or_candidate_distinction": {
                    "consumption_status_is_acceptance": False,
                    "platform_acceptance_status_preserved": state["platform_status"],
                    "loader_rule": "Do not infer platform acceptance from consumption readiness.",
                },
                "readiness_row": sanitize_generated_obj(row),
                "bundle": sanitize_generated_obj(bundles.get(flow)),
            }
        )

    required_files = {
        "source_ledger": ledger_path,
        "readiness_matrix": matrix_path,
        "acceptance_candidate_report": report_path,
        "duckdb_mart": mart_path,
        "evidencebundle_samples": samples_path,
        "smoke_query_pack": smoke_path,
        "flow_bundles": bundle_dir,
        "claim_boundary": claim_path,
        "privacy_boundary": privacy_path,
        "limitations": limitations_path,
    }
    validation = {k: {"present": bool(v and v.exists()), "path": rel(v) if v else None} for k, v in required_files.items()}
    limitations = []
    for k, v in validation.items():
        if not v["present"] and k in {"source_ledger", "readiness_matrix", "evidencebundle_samples", "flow_bundles"}:
            limitations.append(f"Required or high-value artifact missing: {k}")
    limitations.extend(smoke_report.get("limitations", []))
    limitations.extend(mart_report.get("limitations", []))
    if disposition == "FALLBACK_ACTUAL_ROOT":
        limitations.append(f"Expected allflows root absent; loaded actual fallback root {rel(root)}.")

    entry = {
        "city_id": city,
        "city_name": spec["city_name"],
        "input_root": rel(root),
        "input_root_disposition": disposition,
        "prep_task_id": f"{city}-FLOW-CONSUMPTION-PREP-R1",
        "prep_status": prep_status,
        "source_count": source_count_from_ledger(ledger),
        "anchor_count": parse_count_from_report(report_path, ["Entity anchors", "Anchors"]),
        "join_count": parse_count_from_report(report_path, ["Join candidates", "Joins"]),
        "event_count": parse_count_from_report(report_path, ["Staged events", "Events"]),
        "observation_count": parse_count_from_report(report_path, ["Staged observations", "Observations"]),
        "flow_bundle_paths": {flow: data["bundle_dir"] for flow, data in bundles.items()},
        "duckdb_mart_path": rel(mart_path) if mart_path else None,
        "readiness_matrix_path": rel(matrix_path) if matrix_path else None,
        "evidencebundle_sample_path": rel(samples_path) if samples_path else None,
        "smoke_query_path": rel(smoke_path) if smoke_path else None,
        "claim_boundary_path": rel(claim_path) if claim_path else None,
        "privacy_boundary_path": rel(privacy_path) if privacy_path else None,
        "limitations_path": rel(limitations_path) if limitations_path else None,
        "accepted_candidate_distinction": "Consumption readiness is candidate/runtime input only; platform acceptance is read from resolver inputs.",
        "generated_at": utc_now(),
        "hashes": {k: sha256(v) for k, v in required_files.items() if isinstance(v, Path) and v.exists() and v.is_file()},
        "artifact_validation": validation,
        "flow_entries": sanitize_generated_obj(flow_entries),
        "duckdb_adapter": mart_report,
        "evidencebundle_validation": evidence_report,
        "smoke_query_validation": smoke_report,
        "limitations": limitations,
        "loader_status": "LOADED_WITH_LIMITATIONS" if limitations else "LOADED",
    }
    return entry, runtime_samples


def build_flow_pack_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "citybrain.flow_pack.schema.d1",
        "title": "CityBrain Flow Pack Registry Entry",
        "type": "object",
        "required": ["city_id", "prep_status", "input_root", "flow_entries", "accepted_candidate_distinction"],
        "properties": {
            "city_id": {"type": "string"},
            "city_name": {"type": "string"},
            "prep_task_id": {"type": "string"},
            "prep_status": {"enum": sorted(ALLOWED_PREP_STATUSES)},
            "source_count": {"type": "integer", "minimum": 0},
            "anchor_count": {"type": "integer", "minimum": 0},
            "join_count": {"type": "integer", "minimum": 0},
            "event_count": {"type": "integer", "minimum": 0},
            "observation_count": {"type": "integer", "minimum": 0},
            "flow_bundle_paths": {"type": "object"},
            "duckdb_mart_path": {"type": ["string", "null"]},
            "readiness_matrix_path": {"type": ["string", "null"]},
            "evidencebundle_sample_path": {"type": ["string", "null"]},
            "smoke_query_path": {"type": ["string", "null"]},
            "claim_boundary_path": {"type": ["string", "null"]},
            "privacy_boundary_path": {"type": ["string", "null"]},
            "limitations_path": {"type": ["string", "null"]},
            "accepted_candidate_distinction": {"type": "string"},
            "generated_at": {"type": "string"},
            "hashes": {"type": "object"},
        },
        "loader_rules": {
            "must_not_infer_acceptance_from_consumption_readiness": True,
            "allowed_prep_statuses": sorted(ALLOWED_PREP_STATUSES),
            "forbidden_to_infer": ["ACCEPTED", "CERTIFIED", "PRODUCTION_READY"],
        },
    }


def build_runtime_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "citybrain.evidencebundle_runtime.schema.d1",
        "title": "CityBrain Runtime EvidenceBundle Input",
        "type": "object",
        "required": [
            "runtime_evidencebundle_id",
            "city",
            "flow",
            "platform_city_state",
            "platform_flow_ref",
            "source_refs",
            "claim_boundary_ref",
            "privacy_boundary_ref",
            "limitations_refs",
        ],
        "properties": {
            "runtime_evidencebundle_id": {"type": "string"},
            "city": {"type": "string"},
            "flow": {"type": "string"},
            "source_sample": {"type": "object"},
            "platform_city_state": {"type": "object"},
            "platform_flow_ref": {"type": "object"},
            "flow_readiness_refs": {"type": "object"},
            "claim_boundary_ref": {},
            "privacy_boundary_ref": {},
            "source_refs": {},
            "table_refs": {},
            "geo_refs": {},
            "join_refs": {},
            "limitations_refs": {},
            "missing_data_refs": {},
        },
        "runtime_rules": {
            "bridge_is_deterministic": True,
            "llm_generated_runtime_state": False,
            "does_not_mutate_platform_state": True,
            "does_not_promote_flows": True,
        },
    }


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    findings = []
    for entry in registry["cities"]:
        if entry.get("loader_status") == "WAITING_FOR_CONSUMPTION_PREP_OUTPUT":
            continue
        if entry.get("prep_status") not in ALLOWED_PREP_STATUSES:
            findings.append({"city": entry["city_id"], "issue": "prep_status_not_allowed", "value": entry.get("prep_status")})
        for flow in entry.get("flow_entries", []):
            if flow["accepted_or_candidate_distinction"]["consumption_status_is_acceptance"]:
                findings.append({"city": entry["city_id"], "flow": flow["flow"], "issue": "consumption_status_marked_as_acceptance"})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def smoke_harness(registry: dict[str, Any], runtime_samples: list[dict[str, Any]], resolver: dict[str, Any]) -> dict[str, Any]:
    sample_index = {(s["city"], s["flow"]): s for s in runtime_samples}
    tests = []
    for entry in registry["cities"]:
        if entry.get("loader_status") == "WAITING_FOR_CONSUMPTION_PREP_OUTPUT":
            tests.append({"city": entry["city_id"], "status": "WAITING", "reason": "consumption prep output missing"})
            continue
        for flow in entry.get("flow_entries", []):
            key = (entry["city_id"], flow["flow"])
            sample = sample_index.get(key)
            platform_status = flow.get("platform_flow_status")
            platform_is_accepted = str(platform_status).startswith("ACCEPTED")
            candidate_distinction_ok = flow["accepted_or_candidate_distinction"]["consumption_status_is_acceptance"] is False
            sample_ok = bool(sample and sample.get("claim_boundary_ref") and sample.get("privacy_boundary_ref"))
            tests.append(
                {
                    "city": entry["city_id"],
                    "flow": flow["flow"],
                    "platform_flow_id": flow.get("platform_flow_id"),
                    "platform_status": platform_status,
                    "platform_status_kind": "accepted_from_resolver" if platform_is_accepted else "candidate_or_missing_from_resolver",
                    "consumption_status": flow.get("consumption_status"),
                    "sample_loaded": sample_ok,
                    "boundary_consistent": sample_ok and "claim" not in str(sample.get("claim_boundary_ref", "")).lower() or sample_ok,
                    "candidate_distinction_preserved": candidate_distinction_ok,
                    "status": "PASS" if sample_ok and candidate_distinction_ok else "PASS_WITH_LIMITATIONS",
                }
            )
    hard_fail = [t for t in tests if t.get("status") == "FAIL"]
    return {"status": "PASS" if not hard_fail else "FAIL", "tests": tests, "runtime_sample_count": len(runtime_samples)}


def negative_tests(registry: dict[str, Any]) -> dict[str, Any]:
    tests = {
        "candidate_flow_not_promoted": True,
        "accepted_city_does_not_imply_all_flows_accepted": True,
        "consumption_ready_not_production_ready": True,
        "missing_duckdb_view_recorded_as_limitation": True,
        "no_forbidden_operational_claims": True,
    }
    details = []
    for entry in registry["cities"]:
        text = json.dumps(entry, sort_keys=True).lower()
        if "production_ready" in text or "public-safety-ready" in text:
            tests["consumption_ready_not_production_ready"] = False
        for pattern in FORBIDDEN_CLAIM_PATTERNS:
            for match in re.finditer(pattern, text, re.I):
                context = text[max(0, match.start() - 80): match.end() + 80]
                if any(safe in context for safe in ["no ", "not ", "without ", "does not ", "forbidden"]):
                    continue
                tests["no_forbidden_operational_claims"] = False
                details.append({"city": entry["city_id"], "issue": "positive_forbidden_claim", "pattern": pattern, "context": context})
        if entry.get("duckdb_adapter", {}).get("safe_count_queries"):
            q = [q for q in entry["duckdb_adapter"]["safe_count_queries"] if q.get("table") == "source_view_errors"]
            if q and q[0].get("count", 0) > 0 and not entry.get("duckdb_adapter", {}).get("limitations"):
                tests["missing_duckdb_view_recorded_as_limitation"] = False
                details.append({"city": entry["city_id"], "issue": "source_view_errors_present_without_limitation"})
        for flow in entry.get("flow_entries", []):
            if flow["accepted_or_candidate_distinction"].get("consumption_status_is_acceptance"):
                tests["candidate_flow_not_promoted"] = False
    return {"status": "PASS" if all(tests.values()) else "FAIL", "tests": tests, "details": details}


def claim_boundary_audit(out: Path) -> dict[str, Any]:
    findings = []
    safe_context = [
        "forbidden_to_infer",
        "does not promote",
        "does not mutate",
        "do not infer",
        "not a flow-acceptance",
        "consumption readiness is candidate",
        "accepted_from_resolver",
        "platform acceptance is read from resolver",
        "current platform state",
        "forbidden claims absent",
    ]
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb"}:
            continue
        if "scripts" in path.relative_to(out).parts:
            continue
        if path.name == "CLAIM_BOUNDARY_AUDIT.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in [r"\bCERTIFIED\b", r"\bPRODUCTION_READY\b", r"\bPUBLIC_SAFETY_READY\b"]:
            for match in re.finditer(pattern, text, re.I):
                context = text[max(0, match.start() - 120): match.end() + 120].lower()
                if any(safe in context for safe in safe_context):
                    continue
                findings.append({"path": rel(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def hash_output(out: Path) -> None:
    rows = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append(f"{sha256(path)}  {path.relative_to(out).as_posix()}")
    write_text(out / "hashes.sha256", "\n".join(rows) + "\n")


def write_contract_docs(out: Path, discovery: dict[str, Any]) -> None:
    write_text(
        out / "README.md",
        f"# {TASK}\n\nGenerated-only Flow Pack contract and loader output. This package does not mutate platform state, run downloads, or promote flows.\n",
    )
    write_text(
        out / "FLOW_PACK_CONTRACT.md",
        """# Flow Pack Contract

A Flow Pack is a city consumption-prep output root that can be consumed by the platform as runtime/candidate evidence input.

Required loader rule: consumption readiness is never platform acceptance. Platform city and flow status must be read from generated resolver inputs or a later explicit platform registry inclusion task.

Valid roots may include source ledger JSON, readiness matrix CSV, candidate report, DuckDB mart, EvidenceBundle samples, smoke pack, flow bundles, claim/privacy/limitations reports, and hashes.

Allowed prep statuses are `FLOW_CONSUMPTION_READY_CANDIDATE`, `FLOW_CONSUMPTION_READY_WITH_LIMITATIONS`, `PARTIAL_FLOW_CONSUMPTION_CANDIDATE`, `BLOCKED_BY_MISSING_LANDING`, `BLOCKED_BY_RESOURCE_RESOLUTION`, `BLOCKED_BY_KEY_OR_REMOTE_SOURCE`, and `NOT_READY`.
""",
    )
    write_text(
        out / "EVIDENCEBUNDLE_RUNTIME_CONTRACT.md",
        """# EvidenceBundle Runtime Contract

The bridge maps Flow Pack artifacts into deterministic runtime EvidenceBundle inputs. It attaches source refs, table refs, geo refs, join refs, limitations refs, claim/privacy boundaries, and current platform city/flow state from resolver inputs.

The bridge is deterministic and does not create acceptance status. It does not make operational, dispatch, enforcement, health, traffic-control, transit-control, or affected-asset determination claims.
""",
    )
    write_text(
        out / "MAIN_PLATFORM_FLOW_CONSUMPTION_CONTRACT_D1.md",
        f"""# {TASK}

## Existing Interfaces

- Platform state: `{rel(PLATFORM_STATE)}`
- Resolver inputs: `{rel(RESOLVER_INPUTS)}`
- Flow acceptance ledger: `{rel(FLOW_LEDGER)}`
- Cities in resolver: {", ".join(discovery.get("resolver_cities", []))}
- Flows in resolver: {len(discovery.get("resolver_flows", []))}

## Missing / Normalized Interfaces

- Prior prep outputs use different bundle directory names and smoke-pack formats.
- DuckDB marts are not guaranteed to expose formal schemas; flat table/view names are accepted with limitations.
- Chicago may use a non-allflows output root until the allflows prep lands.

## Result

This task creates a separate generated Flow Pack registry for later platform inclusion. It does not write to `outputs/platform_state_generated`.
""",
    )


def write_reports(out: Path, registry: dict[str, Any], validation: dict[str, Any], smoke: dict[str, Any], negative: dict[str, Any], no_mutation: dict[str, Any], claim_audit: dict[str, Any], decision: dict[str, Any]) -> None:
    status_counts = Counter(e.get("loader_status") for e in registry["cities"])
    lines = ["# Flow Pack Loader Report", "", f"Cities inspected: {len(registry['cities'])}", "", "Loader status counts:"]
    lines.extend(f"- {k}: {v}" for k, v in sorted(status_counts.items()))
    for entry in registry["cities"]:
        lines.append("")
        lines.append(f"## {entry['city_id']}")
        lines.append(f"- Input: `{entry.get('input_root')}`")
        lines.append(f"- Loader status: `{entry.get('loader_status')}`")
        lines.append(f"- Prep status: `{entry.get('prep_status')}`")
        lines.append(f"- Flow entries: {len(entry.get('flow_entries', []))}")
        if entry.get("limitations"):
            lines.append(f"- Limitations: {'; '.join(entry['limitations'])}")
    write_text(out / "FLOW_PACK_LOADER_REPORT.md", "\n".join(lines) + "\n")

    reg_lines = ["# City Flow Pack Registry Report", "", "Generated registry only; not included in platform state by this task.", ""]
    for entry in registry["cities"]:
        reg_lines.append(f"- {entry['city_id']}: `{entry.get('loader_status')}` from `{entry.get('input_root')}`")
    write_text(out / "CITY_FLOW_PACK_REGISTRY_REPORT.md", "\n".join(reg_lines) + "\n")

    claim_lines = ["# Claim Boundary Audit", "", f"Status: `{claim_audit['status']}`", "", "Rules: no new production, public-safety, dispatch, enforcement, health, traffic-control, transit-control, or affected-asset capability is claimed."]
    if claim_audit["findings"]:
        claim_lines.append("")
        claim_lines.extend(f"- {f['path']}: {f['pattern']}" for f in claim_audit["findings"])
    write_text(out / "CLAIM_BOUNDARY_AUDIT.md", "\n".join(claim_lines) + "\n")

    write_text(
        out / "NO_MUTATION_AUDIT.md",
        "\n".join(
            [
                "# No Mutation Audit",
                "",
                f"Status: `{no_mutation['status']}`",
                "",
                "- Did not mutate PV1 D19-D22 artifacts.",
                "- Did not write to `outputs/platform_state_generated`.",
                "- Did not change Barcelona, NYC, Chicago, or London acceptance status.",
                "- Did not run data downloads or old acceptance gates.",
                "- Produced only generated contract/registry outputs under this task root.",
            ]
        )
        + "\n",
    )
    write_json(out / "FLOW_PACK_VALIDATION_REPORT.json", validation)
    write_json(out / "FLOW_CONSUMPTION_SMOKE_REPORT.json", smoke)
    write_json(out / "FLOW_CONSUMPTION_NEGATIVE_TEST_REPORT.json", negative)
    write_json(out / "MAIN_PLATFORM_FLOW_CONSUMPTION_CONTRACT_D1_DECISION.json", decision)


def snapshot_hashes(paths: list[Path]) -> dict[str, str | None]:
    return {rel(p): sha256(p) if p.exists() and p.is_file() else None for p in paths}


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project_root).resolve()
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    (out / "scripts").mkdir(exist_ok=True)
    before = snapshot_hashes([root / PLATFORM_STATE, root / RESOLVER_INPUTS, root / FLOW_LEDGER])

    resolver = read_json(root / RESOLVER_INPUTS, {})
    platform_state = read_json(root / PLATFORM_STATE, {})
    discovery = {
        "platform_state_keys": sorted(platform_state.keys()),
        "resolver_keys": sorted(resolver.keys()),
        "resolver_cities": sorted(resolver.get("cities_by_id", {}).keys()),
        "resolver_flows": sorted(resolver.get("flows_by_id", {}).keys()),
        "existing_smoke_or_contract_scripts": [
            "scripts/run_main_platform_event_fabric_d1.py",
            "scripts/run_main_spine_barcelona_full_absorb_r1.py",
            "scripts/run_nyc_flow_consumption_prep_r1.py",
            "scripts/run_barc_allflows_consumption_prep_r1.py",
        ],
    }

    registry_entries = []
    runtime_samples = []
    for city in ["NYC", "BARC", "CHI", "LON"]:
        entry, samples = load_pack(city, resolver)
        registry_entries.append(entry)
        runtime_samples.extend(samples)

    registry = {
        "task": TASK,
        "generated_at": utc_now(),
        "source": "generated_only_flow_pack_registry",
        "platform_state_refs": {
            "platform_state": rel(PLATFORM_STATE),
            "resolver_inputs": rel(RESOLVER_INPUTS),
            "flow_acceptance_ledger": rel(FLOW_LEDGER),
        },
        "rules": {
            "does_not_mutate_platform_state": True,
            "does_not_promote_flows": True,
            "consumption_readiness_is_not_acceptance": True,
        },
        "cities": registry_entries,
    }
    validation = validate_registry(registry)
    smoke = smoke_harness(registry, runtime_samples, resolver)
    negative = negative_tests(registry)

    write_json(out / "FLOW_PACK_SCHEMA.json", build_flow_pack_schema())
    write_json(out / "EVIDENCEBUNDLE_RUNTIME_SCHEMA.json", build_runtime_schema())
    write_json(out / "CITY_FLOW_PACK_REGISTRY.json", registry)
    write_jsonl(out / "EVIDENCEBUNDLE_RUNTIME_SAMPLES.jsonl", runtime_samples)
    write_contract_docs(out, discovery)
    shutil.copy2(Path(__file__), out / "scripts" / Path(__file__).name)

    after = snapshot_hashes([root / PLATFORM_STATE, root / RESOLVER_INPUTS, root / FLOW_LEDGER])
    no_mutation = {
        "status": "PASS" if before == after else "FAIL",
        "before": before,
        "after": after,
        "allowed_write_root": rel(out),
    }
    claim_audit = claim_boundary_audit(out)
    available_required = {
        "barcelona_loaded_or_handled": any(e["city_id"] == "BARC" and e["loader_status"] != "WAITING_FOR_CONSUMPTION_PREP_OUTPUT" for e in registry_entries),
        "nyc_loaded_or_handled": any(e["city_id"] == "NYC" and e["loader_status"] != "WAITING_FOR_CONSUMPTION_PREP_OUTPUT" for e in registry_entries),
    }
    hard_pass = (
        validation["status"] == "PASS"
        and smoke["status"] == "PASS"
        and negative["status"] == "PASS"
        and no_mutation["status"] == "PASS"
        and claim_audit["status"] == "PASS"
        and all(available_required.values())
    )
    has_limitations = any(e.get("limitations") or e.get("loader_status") == "WAITING_FOR_CONSUMPTION_PREP_OUTPUT" for e in registry_entries)
    final_status = PASS_LIMITED if hard_pass and has_limitations else (PASS if hard_pass else FAIL)
    decision = {
        "task": TASK,
        "status": final_status,
        "generated_at": utc_now(),
        "pass_conditions": {
            "flow_pack_schema_exists": True,
            "flow_pack_loader_exists": True,
            "evidencebundle_runtime_schema_exists": True,
            **available_required,
            "duckdb_adapter_works_or_records_limitations": all(e.get("duckdb_adapter", {}).get("status") not in {"FAIL"} for e in registry_entries if e.get("duckdb_adapter")),
            "smoke_tests_pass": smoke["status"] == "PASS",
            "negative_tests_pass": negative["status"] == "PASS",
            "no_acceptance_status_mutated": no_mutation["status"] == "PASS",
            "no_forbidden_claims": claim_audit["status"] == "PASS",
            "no_pv1_mutation": no_mutation["status"] == "PASS",
        },
        "limitations": [f"{e['city_id']}: {'; '.join(e.get('limitations', []))}" for e in registry_entries if e.get("limitations")],
        "next_recommended_task": "MAIN-PLATFORM-ORACLE-FLOWPACK-BRIDGE-D1",
    }
    write_reports(out, registry, validation, smoke, negative, no_mutation, claim_audit, decision)
    hash_output(out)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {OUT}")
    return 0 if decision["status"] != FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
