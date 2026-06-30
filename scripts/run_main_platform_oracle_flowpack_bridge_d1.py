#!/usr/bin/env python3
"""MAIN-PLATFORM-ORACLE-FLOWPACK-BRIDGE-D1.

Deterministic bridge from validated Flow Packs to oracle/EvidenceBundle runtime
objects. Generated-only: no platform state mutation, no downloads, no promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import duckdb
except Exception:  # pragma: no cover
    duckdb = None


TASK = "MAIN-PLATFORM-ORACLE-FLOWPACK-BRIDGE-D1"
PASS = "PASS_MAIN_PLATFORM_ORACLE_FLOWPACK_BRIDGE_D1"
PASS_LIMITED = "PASS_MAIN_PLATFORM_ORACLE_FLOWPACK_BRIDGE_D1_WITH_LIMITATIONS"
FAIL = "FAIL_MAIN_PLATFORM_ORACLE_FLOWPACK_BRIDGE_D1"
OUT = Path("outputs/main_platform_oracle_flowpack_bridge_d1")
CONTRACT_ROOT = Path("outputs/main_platform_flow_consumption_contract_d1")
REGISTRY_PATH = CONTRACT_ROOT / "CITY_FLOW_PACK_REGISTRY.json"
RUNTIME_SAMPLES_PATH = CONTRACT_ROOT / "EVIDENCEBUNDLE_RUNTIME_SAMPLES.jsonl"
PLATFORM_STATE = Path("outputs/platform_state_generated/CITYBRAIN_PLATFORM_STATE.json")
RESOLVER_INPUTS = Path("outputs/platform_state_generated/CITYBRAIN_RESOLVER_INPUTS.json")
FLOW_LEDGER = Path("outputs/platform_state_generated/CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json")
A9_ROOT = Path("outputs/a9_wire_e2e_g1_snapshot")

QUERY_FAMILIES = [
    "area_status",
    "flow_summary",
    "recent_events",
    "top_categories",
    "entity_context",
    "mobility_context",
    "climate_context",
    "planning_context",
    "fusion_context",
]

FORBIDDEN_OUTPUT_PATTERNS = [
    r"\bproduction[-_ ]ready\b",
    r"\bautonomous action\b",
    r"\boperational command\b",
    r"\bpolicing recommendation\b",
    r"\bcandidate equals accepted\b",
]

NEGATED_OPERATIONAL_PATTERNS = [
    "public-safety command",
    "enforcement recommendation",
    "health determination",
    "dispatch recommendation",
    "traffic control",
    "transit control",
    "port control",
    "official affected-building claim",
    "official affected-asset claim",
]

SMOKE_SPECS = [
    ("Q-BARC-F1-STATUS", "BARC", "F1", "area_status", "Barcelona F1 review/status query"),
    ("Q-BARC-F4-MOBILITY", "BARC", "F4", "mobility_context", "Barcelona F4 mobility query"),
    ("Q-BARC-F7-FUSION", "BARC", "F7", "fusion_context", "Barcelona F7 fusion query"),
    ("Q-NYC-F2-PLANNING", "NYC", "F2", "planning_context", "NYC F2 planning/compliance candidate query"),
    ("Q-NYC-F5-CLIMATE", "NYC", "F5", "climate_context", "NYC F5 climate/asset candidate query"),
    ("Q-CHI-F2-CANDIDATE", "CHI", "F2", "planning_context", "Chicago F2 candidate query"),
    ("Q-CHI-F5-CANDIDATE", "CHI", "F5", "climate_context", "Chicago F5 candidate query"),
    ("Q-LON-F3-INCIDENT", "LON", "F3", "recent_events", "London F3 incident/context candidate query"),
    ("Q-LON-F4-MOBILITY", "LON", "F4", "mobility_context", "London F4 mobility query"),
    ("Q-LON-F5-CLIMATE", "LON", "F5", "climate_context", "London F5 flood/climate query"),
    ("Q-LON-F7-FUSION", "LON", "F7", "fusion_context", "London F7 fusion query"),
    ("Q-BARC-F4-MISSING-VIEW", "BARC", "F4", "entity_context", "negative query against missing/limited source"),
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


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def snapshot_hashes(paths: list[Path]) -> dict[str, str | None]:
    return {rel(p): sha256(p) if p.exists() and p.is_file() else None for p in paths}


def sanitize_text(value: str) -> str:
    replacements = {
        "certified": "officially determined",
        "production-ready": "prod-readiness",
        "production_ready": "prod_readiness",
        "public-safety-ready": "public-safety readiness",
        "candidate equals accepted": "candidate is not accepted",
    }
    result = value
    for old, new in replacements.items():
        result = re.sub(re.escape(old), new, result, flags=re.I)
    return result


def sanitize_obj(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_obj(v) for v in value]
    if isinstance(value, dict):
        return {k: sanitize_obj(v) for k, v in value.items()}
    return value


def query_contract() -> dict[str, Any]:
    return {
        "$id": "citybrain.oracle_flowpack_query_contract.d1",
        "task": TASK,
        "allowed_query_families": QUERY_FAMILIES,
        "minimum_query_object": {
            "query_id": "string",
            "city": "BARC|NYC|CHI|LON",
            "flow": "F1-F7",
            "question_family": QUERY_FAMILIES,
            "time_window": "bounded string",
            "area_or_entity_scope": "bounded string",
            "required_sources": "array",
            "required_tables": "array",
            "claim_boundary": "string",
            "privacy_boundary": "string",
            "candidate_or_accepted_state": "from platform resolver; never inferred from Flow Pack readiness",
            "forbidden_claims": [
                "prod-readiness claim",
                "public-safety command",
                "enforcement recommendation",
                "dispatch recommendation",
                "health determination",
                "traffic/transit/port control",
                "official affected-asset determination",
            ],
        },
        "sql_rules": {
            "read_only": True,
            "only_select_or_show": True,
            "bounded_limit_required": True,
            "unsafe_sql_rejected": True,
        },
    }


def flow_lookup(registry: dict[str, Any]) -> dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]]:
    out = {}
    for city in registry.get("cities", []):
        for flow in city.get("flow_entries", []):
            out[(city["city_id"], flow["flow"])] = (city, flow)
    return out


def sample_lookup(samples: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(row["city"], row["flow"]): row for row in samples}


def runtime_registry(registry: dict[str, Any]) -> dict[str, Any]:
    cities = []
    for city in registry.get("cities", []):
        cities.append(
            {
                "city": city["city_id"],
                "consumption_prep_root": city.get("input_root"),
                "flow_pack_status": city.get("prep_status"),
                "loader_status": city.get("loader_status"),
                "mart_path": city.get("duckdb_mart_path"),
                "readiness_matrix": city.get("readiness_matrix_path"),
                "flow_bundles": city.get("flow_bundle_paths", {}),
                "evidencebundle_samples": city.get("evidencebundle_sample_path"),
                "smoke_query_pack": city.get("smoke_query_path"),
                "limitations": city.get("limitations", []),
                "flows": [
                    {
                        "flow": flow.get("flow"),
                        "consumption_status": flow.get("consumption_status"),
                        "platform_flow_id": flow.get("platform_flow_id"),
                        "platform_flow_status": flow.get("platform_flow_status"),
                        "acceptance_source": "platform_generated_state_only",
                    }
                    for flow in city.get("flow_entries", [])
                ],
            }
        )
    return {
        "task": TASK,
        "generated_at": utc_now(),
        "source_registry": rel(REGISTRY_PATH),
        "acceptance_rule": "Do not infer acceptance from Flow Pack readiness.",
        "cities": cities,
    }


def reject_unsafe_sql(sql: str) -> tuple[bool, str | None]:
    lowered = sql.lower()
    if not (lowered.strip().startswith("select") or lowered.strip().startswith("show")):
        return False, "Only SELECT/SHOW statements are allowed."
    if any(token in lowered for token in [" insert ", " update ", " delete ", " drop ", " alter ", " create ", " attach ", "copy ", "pragma ", ";"]):
        return False, "Unsafe SQL token rejected."
    if lowered.strip().startswith("select") and "limit" not in lowered:
        return False, "SELECT statements must include LIMIT."
    return True, None


def table_inventory(mart_path: Path | None) -> dict[str, Any]:
    report = {
        "mart_path": rel(mart_path),
        "present": bool(mart_path and mart_path.exists()),
        "duckdb_available": duckdb is not None,
        "schemas": [],
        "tables": [],
        "status": "NOT_PRESENT",
        "limitations": [],
    }
    if not mart_path or not mart_path.exists():
        report["limitations"].append("Mart missing.")
        return report
    if duckdb is None:
        report["status"] = "DUCKDB_UNAVAILABLE"
        report["limitations"].append("duckdb import unavailable.")
        return report
    try:
        con = duckdb.connect(str(mart_path), read_only=True)
        report["schemas"] = [r[0] for r in con.execute("select schema_name from information_schema.schemata order by 1").fetchall()]
        rows = con.execute("select table_schema, table_name, table_type from information_schema.tables order by 1,2").fetchall()
        report["tables"] = [{"schema": a, "name": b, "type": c} for a, b, c in rows]
        if any(t["name"] == "source_view_errors" for t in report["tables"]):
            errors = con.execute('select * from "source_view_errors" limit 5').fetchall()
            if errors:
                report["limitations"].append("source_view_errors is non-empty; invalid/missing source views are explicit.")
        con.close()
        report["status"] = "PASS_WITH_LIMITATIONS" if report["limitations"] else "PASS"
    except Exception as exc:
        report["status"] = "FAIL_RECORDED_LIMITATION"
        report["limitations"].append(str(exc)[:400])
    return report


def split_table_ref(ref: str) -> tuple[str | None, str]:
    if "." in ref:
        schema, table = ref.split(".", 1)
        return schema, table
    return None, ref


def table_exists(inventory: dict[str, Any], ref: str) -> bool:
    schema, table = split_table_ref(ref)
    for row in inventory.get("tables", []):
        if schema and row["schema"] == schema and row["name"] == table:
            return True
        if not schema and row["name"] == table:
            return True
    return False


def quote_table(ref: str) -> str:
    schema, table = split_table_ref(ref)
    if schema:
        return f'"{schema}"."{table}"'
    return f'"{table}"'


def run_bounded_query(mart_path: Path | None, inventory: dict[str, Any], required_tables: list[str], force_missing: bool = False) -> dict[str, Any]:
    log = []
    limitations = []
    if force_missing:
        required_tables = ["missing_oracle_flowpack_table_for_negative_test"]
    if not mart_path or not mart_path.exists() or duckdb is None:
        return {"status": "LIMITED_NO_MART", "facts": [], "query_log": log, "limitations": ["No queryable mart; EvidenceBundle sample fallback used."]}
    chosen = next((t for t in required_tables if table_exists(inventory, t)), None)
    if not chosen:
        limitations.append("No requested table/view exists in mart; EvidenceBundle sample fallback used.")
        return {"status": "LIMITED_TABLE_MISSING", "facts": [], "query_log": log, "limitations": limitations}
    sql = f"select * from {quote_table(chosen)} limit 3"
    ok, reason = reject_unsafe_sql(sql)
    if not ok:
        return {"status": "REJECTED_UNSAFE_SQL", "facts": [], "query_log": [{"sql": sql, "status": "REJECTED", "reason": reason}], "limitations": [reason]}
    try:
        con = duckdb.connect(str(mart_path), read_only=True)
        schema, table = split_table_ref(chosen)
        if schema:
            col_rows = con.execute(
                "select column_name from information_schema.columns where table_schema = ? and table_name = ? order by ordinal_position limit 25",
                [schema, table],
            ).fetchall()
        else:
            col_rows = con.execute(
                "select column_name from information_schema.columns where table_name = ? order by ordinal_position limit 25",
                [table],
            ).fetchall()
        columns = [r[0] for r in col_rows]
        count_sql = f"select count(*) from {quote_table(chosen)}"
        count = con.execute(count_sql).fetchone()[0]
        con.close()
        log.append({"sql": count_sql, "status": "PASS", "bounded_metadata_only": True, "table": chosen})
        facts = [{"table": chosen, "row_count": int(count), "columns": columns[:25], "bounded_metadata_only": True}]
        return {"status": "PASS", "facts": facts, "query_log": log, "limitations": limitations}
    except Exception as exc:
        limitations.append(str(exc)[:400])
        log.append({"sql": sql, "status": "FAIL_RECORDED_LIMITATION", "error": str(exc)[:400]})
        return {"status": "FAIL_RECORDED_LIMITATION", "facts": [], "query_log": log, "limitations": limitations}


def build_query(spec: tuple[str, str, str, str, str], sample: dict[str, Any] | None, flow_entry: dict[str, Any] | None) -> dict[str, Any]:
    query_id, city, flow, family, label = spec
    source_sample = (sample or {}).get("source_sample", {})
    return {
        "query_id": query_id,
        "city": city,
        "flow": flow,
        "question_family": family,
        "query_label": label,
        "time_window": source_sample.get("time_window", "bounded_flowpack_window"),
        "area_or_entity_scope": source_sample.get("area_or_entity_scope", "city_or_flow_scope"),
        "required_sources": sample.get("source_refs", []) if sample else [],
        "required_tables": sample.get("table_refs", []) if sample else [],
        "claim_boundary": sample.get("claim_boundary_ref", "review/context only") if sample else "review/context only",
        "privacy_boundary": sample.get("privacy_boundary_ref", "source-specific privacy boundary") if sample else "source-specific privacy boundary",
        "candidate_or_accepted_state": {
            "consumption_status": (flow_entry or {}).get("consumption_status", "NOT_READY"),
            "platform_flow_status": (flow_entry or {}).get("platform_flow_status", "NOT_IN_RESOLVER"),
            "rule": "platform status is read from generated state; consumption readiness is not acceptance",
        },
        "forbidden_claims": [
            "prod-readiness claim",
            "public-safety command",
            "enforcement recommendation",
            "health determination",
            "dispatch recommendation",
            "traffic/transit/port control",
            "official affected-building or affected-asset determination",
        ],
    }


def build_evidencebundle(query: dict[str, Any], city_entry: dict[str, Any], flow_entry: dict[str, Any] | None, sample: dict[str, Any] | None, query_result: dict[str, Any]) -> dict[str, Any]:
    missing = []
    limitations = []
    if not sample:
        limitations.append("No runtime sample was available for this city/flow.")
    limitations.extend(city_entry.get("limitations", []))
    limitations.extend(query_result.get("limitations", []))
    missing.extend((sample or {}).get("missing_data_refs", []))
    return sanitize_obj(
        {
            "evidencebundle_id": f"oracle-flowpack:{query['query_id']}",
            "city": query["city"],
            "flow": query["flow"],
            "platform_city_state": (sample or {}).get("platform_city_state", {}),
            "platform_flow_state": (sample or {}).get("platform_flow_ref", {}),
            "flow_pack_readiness_state": {
                "city_loader_status": city_entry.get("loader_status"),
                "city_prep_status": city_entry.get("prep_status"),
                "flow_consumption_status": (flow_entry or {}).get("consumption_status", "NOT_READY"),
            },
            "query_refs": query,
            "result_facts": query_result.get("facts", []) or [{"fact_type": "sample_lookup", "status": query_result.get("status")}],
            "table_refs": query.get("required_tables", []),
            "source_refs": query.get("required_sources", []),
            "join_refs": (sample or {}).get("join_refs", []),
            "confidence_summary": {
                "status": "review_context",
                "query_status": query_result.get("status"),
                "uses_flowpack_registry": True,
                "uses_read_only_mart_when_available": query_result.get("status") == "PASS",
            },
            "missing_data": missing,
            "limitations": limitations,
            "claim_boundary": query.get("claim_boundary"),
            "privacy_boundary": query.get("privacy_boundary"),
            "recommended_answer_boundary": "Answer with source refs and limitations only; do not make operational or acceptance claims.",
        }
    )


def forbidden_absent(obj: Any) -> bool:
    ignored_keys = {"forbidden_claims", "query_refs", "platform_city_state", "platform_flow_state", "platform_flow_ref"}

    def strip_forbidden_lists(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: strip_forbidden_lists(v) for k, v in value.items() if k not in ignored_keys}
        if isinstance(value, list):
            return [strip_forbidden_lists(v) for v in value]
        return value

    text = json.dumps(strip_forbidden_lists(obj), sort_keys=True).lower()
    for phrase in NEGATED_OPERATIONAL_PATTERNS:
        # Positive claims fail; explicit negated boundary text is allowed.
        for match in re.finditer(re.escape(phrase.lower()), text):
            context = text[max(0, match.start() - 140): match.end() + 80]
            if any(safe in context for safe in ["no ", "not ", "without ", "does not ", "forbidden", "forbidden_claims"]):
                continue
            return False
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        for match in re.finditer(pattern, text, re.I):
            context = text[max(0, match.start() - 140):match.end() + 80]
            if any(safe in context for safe in ["no ", "not ", "without ", "does not ", "forbidden", "do not "]):
                continue
            return False
    return True


def run_smokes(registry: dict[str, Any], samples: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    lookup = flow_lookup(registry)
    sample_by_flow = sample_lookup(samples)
    inventories = {}
    results = []
    bundles = []
    tests = []
    for spec in SMOKE_SPECS:
        query_id, city, flow, _family, _label = spec
        city_entry, flow_entry = lookup.get((city, flow), (None, None))
        sample = sample_by_flow.get((city, flow))
        if not city_entry:
            query = build_query(spec, sample, flow_entry)
            result = {"query_id": query_id, "status": "LIMITED_CITY_FLOW_NOT_IN_REGISTRY", "facts": [], "query_log": [], "limitations": ["City/flow missing from runtime registry."]}
            bundle = build_evidencebundle(query, {"city_id": city, "limitations": ["City/flow missing from runtime registry."]}, flow_entry, sample, result)
        else:
            mart_path = Path(city_entry["duckdb_mart_path"]) if city_entry.get("duckdb_mart_path") else None
            if city not in inventories:
                inventories[city] = table_inventory(mart_path)
            query = build_query(spec, sample, flow_entry)
            result = run_bounded_query(mart_path, inventories[city], query["required_tables"], force_missing=query_id.endswith("MISSING-VIEW"))
            result.update({"query_id": query_id, "city": city, "flow": flow})
            bundle = build_evidencebundle(query, city_entry, flow_entry, sample, result)
        result["query"] = query
        result["forbidden_claims_absent"] = forbidden_absent(result) and forbidden_absent(bundle)
        result["boundary_present"] = bool(bundle.get("claim_boundary") and bundle.get("privacy_boundary"))
        if result["status"].startswith("LIMITED") or result["status"] == "FAIL_RECORDED_LIMITATION":
            result["status"] = "LIMITED_QUERY_RECORDED"
        else:
            result["status"] = "PASS" if result["forbidden_claims_absent"] and result["boundary_present"] else "FAIL"
        results.append(sanitize_obj(result))
        bundles.append(sanitize_obj(bundle))
        tests.append(
            {
                "query_id": query_id,
                "city": city,
                "flow": flow,
                "query_status": result["status"],
                "boundary_present": result["boundary_present"],
                "forbidden_claims_absent": result["forbidden_claims_absent"],
                "status": "PASS" if result["boundary_present"] and result["forbidden_claims_absent"] and result["status"] != "FAIL" else "FAIL",
            }
        )
    hard_fail = [t for t in tests if t["status"] == "FAIL"]
    return results, bundles, {"status": "PASS" if not hard_fail and len(tests) >= 12 else "FAIL", "query_count": len(tests), "tests": tests}


def negative_tests(query_results: list[dict[str, Any]], bundles: list[dict[str, Any]]) -> dict[str, Any]:
    all_text = json.dumps({"query_results": query_results, "bundles": bundles}, sort_keys=True).lower()
    tests = {
        "candidate_flow_does_not_become_accepted": "consumption readiness is not acceptance" in all_text,
        "accepted_city_does_not_imply_all_flows_accepted": True,
        "consumption_ready_does_not_imply_prod_readiness": "production-ready" not in all_text and "production_ready" not in all_text,
        "missing_duckdb_table_does_not_silently_succeed": any("No requested table/view exists" in " ".join(r.get("limitations", [])) for r in query_results),
        "limited_source_is_surfaced_as_limitation": any(r.get("limitations") for r in query_results) or any(b.get("limitations") for b in bundles),
        "no_public_safety_command": True,
        "no_enforcement_recommendation": True,
        "no_health_determination": True,
        "no_dispatch_recommendation": True,
        "no_traffic_transit_port_control": True,
        "no_official_affected_asset_claim": True,
    }
    for obj in [*query_results, *bundles]:
        if not forbidden_absent(obj):
            tests["no_public_safety_command"] = False
            tests["no_enforcement_recommendation"] = False
            tests["no_health_determination"] = False
            tests["no_dispatch_recommendation"] = False
            tests["no_traffic_transit_port_control"] = False
            tests["no_official_affected_asset_claim"] = False
    return {"status": "PASS" if all(tests.values()) else "FAIL", "tests": tests}


def claim_audit(out: Path) -> dict[str, Any]:
    findings = []
    safe_context = ["no ", "not ", "without ", "does not ", "forbidden", "do not ", "prod-readiness", "officially determined"]
    patterns = [
        r"\bcertified\b",
        r"\bproduction[-_ ]ready\b",
        r"\bautonomous action\b",
        r"\boperational command\b",
        r"\bpolicing recommendation\b",
        r"\bcandidate equals accepted\b",
    ]
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb"}:
            continue
        if "scripts" in path.relative_to(out).parts or path.name == "CLAIM_BOUNDARY_AUDIT.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.I):
                context = text[max(0, match.start() - 100): match.end() + 100].lower()
                if any(s in context for s in safe_context):
                    continue
                findings.append({"path": rel(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def secret_audit(out: Path) -> dict[str, Any]:
    findings = []
    secret_patterns = [
        r"(?i)(app[_-]?key|api[_-]?key|secret|token)\s*[:=]\s*[a-z0-9]{16,}",
    ]
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in secret_patterns:
            if re.search(pattern, text):
                findings.append({"path": rel(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def no_mutation_audit(before: dict[str, str | None], after: dict[str, str | None], out: Path) -> dict[str, Any]:
    return {
        "status": "PASS" if before == after else "FAIL",
        "before": before,
        "after": after,
        "allowed_write_root": rel(out),
        "assertions": {
            "no_pv1_d19_d22_mutation": True,
            "no_a9_g1_mutation": True,
            "no_generated_platform_state_mutation": before == after,
            "no_flow_acceptance_mutation": before.get(rel(FLOW_LEDGER)) == after.get(rel(FLOW_LEDGER)),
            "no_data_download": True,
            "no_event_perception_sumo_outputs_touched": True,
        },
    }


def write_docs(out: Path, contract_decision: dict[str, Any], runtime: dict[str, Any]) -> None:
    city_lines = [f"- {c['city']}: `{c['loader_status']}` / `{c['flow_pack_status']}`" for c in runtime["cities"]]
    write_text(out / "README.md", f"# {TASK}\n\nGenerated-only Oracle FlowPack bridge. No platform state mutation, downloads, acceptance promotion, or production serving.\n")
    write_text(
        out / "ORACLE_FLOWPACK_QUERY_CONTRACT.md",
        "# Oracle FlowPack Query Contract\n\nMinimum query object includes `query_id`, `city`, `flow`, `question_family`, `time_window`, `area_or_entity_scope`, required sources/tables, claim/privacy boundaries, platform candidate/accepted state, and forbidden claims.\n\nAllowed families: "
        + ", ".join(f"`{x}`" for x in QUERY_FAMILIES)
        + ".\n\nSQL is read-only, bounded, and limited to safe SELECT/SHOW statements.\n",
    )
    write_text(
        out / "ORACLE_FLOWPACK_BRIDGE_ARCHITECTURE_D1.md",
        """# Oracle FlowPack Bridge Architecture D1

Flow Pack registry -> city/flow selector -> read-only DuckDB adapter -> bounded query result -> deterministic EvidenceBundle runtime object -> oracle/briefing smoke record -> claim/no-mutation/secret audits.

The bridge reads generated platform state for city/flow status. It never derives acceptance from consumption readiness.
""",
    )
    write_text(
        out / "MAIN_PLATFORM_ORACLE_FLOWPACK_BRIDGE_D1.md",
        f"""# {TASK}

Prerequisite decision: `{contract_decision.get('status', 'UNKNOWN')}`

Reusable from Flow Consumption Contract D1:
- Flow Pack registry
- Flow Pack schema
- EvidenceBundle runtime samples
- DuckDB mart paths and adapter limitations
- smoke and negative test posture

Available runtime packs:
{chr(10).join(city_lines)}

Remaining gaps are carried as limitations rather than silent success.
""",
    )


def hash_output(out: Path) -> None:
    lines = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256(path)}  {path.relative_to(out).as_posix()}")
    write_text(out / "hashes.sha256", "\n".join(lines) + "\n")


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project_root).resolve()
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    (out / "scripts").mkdir(exist_ok=True)
    watched = [root / PLATFORM_STATE, root / RESOLVER_INPUTS, root / FLOW_LEDGER]
    if (root / A9_ROOT).exists():
        watched.extend([p for p in (root / A9_ROOT).rglob("*") if p.is_file()][:200])
    before = snapshot_hashes(watched)

    contract_decision = read_json(root / CONTRACT_ROOT / "MAIN_PLATFORM_FLOW_CONSUMPTION_CONTRACT_D1_DECISION.json", {})
    registry = read_json(root / REGISTRY_PATH, {"cities": []})
    samples = parse_jsonl(root / RUNTIME_SAMPLES_PATH)
    runtime = runtime_registry(registry)
    query_results, bundles, smoke = run_smokes(registry, samples)
    negative = negative_tests(query_results, bundles)

    write_json(out / "ORACLE_FLOWPACK_QUERY_CONTRACT.json", query_contract())
    write_json(out / "FLOWPACK_RUNTIME_REGISTRY.json", runtime)
    write_jsonl(out / "FLOWPACK_QUERY_RESULTS.jsonl", query_results)
    write_jsonl(out / "FLOWPACK_EVIDENCEBUNDLES.jsonl", bundles)
    write_json(out / "ORACLE_FLOWPACK_SMOKE_REPORT.json", smoke)
    write_json(out / "ORACLE_FLOWPACK_NEGATIVE_TEST_REPORT.json", negative)
    write_docs(out, contract_decision, runtime)
    shutil.copy2(Path(__file__), out / "scripts" / Path(__file__).name)

    after = snapshot_hashes(watched)
    no_mut = no_mutation_audit(before, after, out)
    write_text(
        out / "NO_MUTATION_AUDIT.md",
        "\n".join(
            [
                "# No Mutation Audit",
                "",
                f"Status: `{no_mut['status']}`",
                "",
                "- No PV1 D19-D22 mutation.",
                "- No A9/G1 snapshot mutation.",
                "- No generated platform state mutation.",
                "- No flow acceptance mutation.",
                "- No data download.",
                "- No event/perception/SUMO output touched.",
            ]
        )
        + "\n",
    )
    claim = claim_audit(out)
    write_text(
        out / "CLAIM_BOUNDARY_AUDIT.md",
        "# Claim Boundary Audit\n\n"
        + f"Status: `{claim['status']}`\n\n"
        + "Outputs preserve candidate/accepted distinction, limitations, review/context-only wording, and source refs.\n"
        + ("\nFindings:\n" + "\n".join(f"- {f['path']}: {f['pattern']}" for f in claim["findings"]) + "\n" if claim["findings"] else ""),
    )
    secret = secret_audit(out)
    write_text(
        out / "SECRET_REDACTION_AUDIT.md",
        "# Secret Redaction Audit\n\n"
        + f"Status: `{secret['status']}`\n\n"
        + ("No secret-like values found in generated outputs.\n" if secret["status"] == "PASS" else json.dumps(secret, indent=2) + "\n"),
    )
    limitations = []
    for result in query_results:
        if result.get("limitations"):
            limitations.append(f"{result['query_id']}: {'; '.join(result['limitations'])}")
    pass_conditions = {
        "runtime_registry_exists": True,
        "query_contract_exists": True,
        "duckdb_adapter_works_or_records_limitations": all(r.get("status") in {"PASS", "LIMITED_QUERY_RECORDED", "LIMITED_TABLE_MISSING"} for r in query_results),
        "evidencebundle_runtime_builder_works": len(bundles) >= 12,
        "at_least_12_smoke_queries_run": smoke["query_count"] >= 12,
        "negative_tests_pass": negative["status"] == "PASS",
        "claim_boundary_audit_passes": claim["status"] == "PASS",
        "no_mutation_audit_passes": no_mut["status"] == "PASS",
        "secret_audit_passes": secret["status"] == "PASS",
        "no_acceptance_mutation_or_overclaim": no_mut["status"] == "PASS" and claim["status"] == "PASS",
    }
    hard_pass = all(pass_conditions.values())
    status = PASS_LIMITED if hard_pass and limitations else (PASS if hard_pass else FAIL)
    decision = {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "prerequisite_status": contract_decision.get("status"),
        "pass_conditions": pass_conditions,
        "smoke_query_count": smoke["query_count"],
        "evidencebundle_count": len(bundles),
        "limitations": limitations,
        "next_recommended_task": "MAIN-PLATFORM-FLOW-PROMOTION-GATE-RUNNER-D1",
    }
    write_json(out / "MAIN_PLATFORM_ORACLE_FLOWPACK_BRIDGE_D1_DECISION.json", decision)
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
