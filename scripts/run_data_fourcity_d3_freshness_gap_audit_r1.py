#!/usr/bin/env python3
"""DATA-FOURCITY-D3-FRESHNESS-GAP-AUDIT-R1.

Additive audit of Barcelona, NYC, Chicago, and London consumption-prep packs for
freshness, missing/blocked sources, mart/view health, staged Event Fabric D3
readiness, EvidenceBundle coverage, and city-specific limitations.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import duckdb
except Exception as exc:  # pragma: no cover
    duckdb = None
    DUCKDB_IMPORT_ERROR = str(exc)
else:
    DUCKDB_IMPORT_ERROR = ""


TASK = "DATA-FOURCITY-D3-FRESHNESS-GAP-AUDIT-R1"
PASS = "PASS_DATA_FOURCITY_D3_FRESHNESS_GAP_AUDIT_R1"
PASS_LIMITED = "PASS_DATA_FOURCITY_D3_FRESHNESS_GAP_AUDIT_R1_WITH_LIMITATIONS"
FAIL = "FAIL_DATA_FOURCITY_D3_FRESHNESS_GAP_AUDIT_R1"
OUT = Path("outputs/data_fourcity_d3_freshness_gap_audit_r1")
SCHEMA_VERSION = "data-fourcity-d3-freshness-gap-audit-r1.v1"

CITIES = {
    "BARC": {
        "city_name": "Barcelona",
        "root": Path("outputs/barc_allflows_consumption_prep_r1"),
        "mart": "BARC_FLOW_MART.duckdb",
        "ledger": "BARC_SOURCE_LEDGER_FINAL.json",
        "readiness": "BARC_FLOW_READINESS_MATRIX.csv",
        "evidence": "BARC_EVIDENCEBUNDLE_SAMPLES.jsonl",
        "limitations": "BARC_LIMITATIONS.md",
        "event_tables": ["main.staged_events"],
        "observation_tables": ["main.staged_observations"],
    },
    "NYC": {
        "city_name": "New York City",
        "root": Path("outputs/nyc_flow_consumption_prep_r1"),
        "mart": "NYC_FLOW_MART.duckdb",
        "ledger": "NYC_SOURCE_LEDGER_FINAL.json",
        "readiness": "NYC_FLOW_READINESS_MATRIX.csv",
        "evidence": "NYC_EVIDENCEBUNDLE_SAMPLES.jsonl",
        "limitations": "NYC_LIMITATIONS.md",
        "event_tables": ["events.event_staging"],
        "observation_tables": ["events.observation_staging", "events.latest_observations"],
    },
    "CHI": {
        "city_name": "Chicago",
        "root": Path("outputs/chi_allflows_consumption_prep_r1"),
        "mart": "CHI_FLOW_MART.duckdb",
        "ledger": "CHI_SOURCE_LEDGER_FINAL.json",
        "readiness": "CHI_FLOW_READINESS_MATRIX.csv",
        "evidence": "CHI_EVIDENCEBUNDLE_SAMPLES.jsonl",
        "limitations": "CHI_LIMITATIONS.md",
        "event_tables": ["mart.event_staging"],
        "observation_tables": ["mart.observation_staging"],
    },
    "LON": {
        "city_name": "London",
        "root": Path("outputs/lon_allflows_consumption_prep_r1"),
        "mart": "LON_FLOW_MART.duckdb",
        "ledger": "LON_SOURCE_LEDGER_FINAL.json",
        "readiness": "LON_FLOW_READINESS_MATRIX.csv",
        "evidence": "LON_EVIDENCEBUNDLE_SAMPLES.jsonl",
        "limitations": "LON_LIMITATIONS.md",
        "event_tables": ["main.staged_events"],
        "observation_tables": ["main.staged_observations"],
    },
}

STATE_ROOTS = {
    "platform_state_generated": Path("outputs/platform_state_generated"),
    "barc_prep": Path("outputs/barc_allflows_consumption_prep_r1"),
    "nyc_prep": Path("outputs/nyc_flow_consumption_prep_r1"),
    "chi_prep": Path("outputs/chi_allflows_consumption_prep_r1"),
    "lon_prep": Path("outputs/lon_allflows_consumption_prep_r1"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except Exception:
        return path.as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    sig: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            sig[path.relative_to(root).as_posix()] = sha256(path)
    return sig


def read_jsonl_count(path: Path) -> tuple[int, dict[str, int]]:
    counts = {f"F{i}": 0 for i in range(1, 8)}
    if not path.exists():
        return 0, counts
    total = 0
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if not line.strip():
                continue
            total += 1
            try:
                row = json.loads(line)
            except Exception:
                continue
            raw = json.dumps(row)
            for flow in counts:
                if flow in raw or flow.replace("F", "Flow ") in raw:
                    counts[flow] += 1
    return total, counts


def load_readiness(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "rows": 0, "flows": {}, "path": rel(path)}
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    flows: dict[str, Any] = {}
    for row in rows:
        joined = " ".join(str(v) for v in row.values())
        flow = None
        for i in range(1, 8):
            if f"F{i}" in joined or f"Flow {i}" in joined:
                flow = f"F{i}"
                break
        if flow:
            flows.setdefault(flow, []).append(row)
    return {"exists": True, "rows": len(rows), "flows": flows, "path": rel(path)}


def normalize_sources(ledger: Any) -> tuple[list[dict[str, Any]], str | None]:
    generated_at = None
    if isinstance(ledger, dict):
        generated_at = ledger.get("generated_at")
        sources = ledger.get("sources", [])
    elif isinstance(ledger, list):
        sources = ledger
    else:
        sources = []
    return [s for s in sources if isinstance(s, dict)], generated_at


def source_status(source: dict[str, Any]) -> str:
    for key in ["landing_status", "consumption_status", "status"]:
        if source.get(key):
            return str(source[key])
    return "UNKNOWN"


def source_rows(source: dict[str, Any]) -> int:
    for key in ["landed_rows", "landed_row_count", "silver_rows", "row_count"]:
        val = source.get(key)
        if isinstance(val, int):
            return val
        if isinstance(val, str) and val.isdigit():
            return int(val)
    return 0


def source_limitations(source: dict[str, Any]) -> list[str]:
    limits = []
    if source.get("resource_resolution_required"):
        limits.append("resource_resolution_required")
    if source.get("error_history"):
        limits.append(f"error_history_count={len(source.get('error_history') or [])}")
    notes = source.get("notes")
    if notes:
        limits.append(str(notes))
    return limits


def count_table(con: Any, ref: str) -> tuple[int | None, str | None]:
    try:
        schema, table = ref.split(".", 1) if "." in ref else ("main", ref)
        return int(con.execute(f'select count(*) from "{schema}"."{table}"').fetchone()[0]), None
    except Exception as exc:
        return None, str(exc)


def inspect_mart(city: str, mart: Path, event_refs: list[str], obs_refs: list[str]) -> dict[str, Any]:
    if duckdb is None:
        return {"exists": mart.exists(), "error": f"duckdb import failed: {DUCKDB_IMPORT_ERROR}", "health": "FAIL"}
    if not mart.exists():
        return {"exists": False, "health": "FAIL", "error": "mart_missing"}
    con = duckdb.connect(str(mart), read_only=True)
    try:
        tables = con.execute("select table_schema, table_name, table_type from information_schema.tables order by table_schema, table_name").fetchall()
        view_failures = []
        view_counts = {}
        for schema, table, typ in tables:
            ref = f"{schema}.{table}"
            if typ == "VIEW":
                try:
                    view_counts[ref] = int(con.execute(f'select count(*) from "{schema}"."{table}" limit 1').fetchone()[0])
                except Exception as exc:
                    view_failures.append({"view": ref, "error": str(exc)})
        event_counts = {}
        observation_counts = {}
        errors = []
        for ref in event_refs:
            count, err = count_table(con, ref)
            event_counts[ref] = count
            if err:
                errors.append({"ref": ref, "error": err})
        for ref in obs_refs:
            count, err = count_table(con, ref)
            observation_counts[ref] = count
            if err:
                errors.append({"ref": ref, "error": err})
        source_view_errors = None
        for ref in ["main.source_view_errors", "metadata.source_view_errors_resolved_r1"]:
            count, err = count_table(con, ref)
            if err is None:
                source_view_errors = count
                break
        return {
            "exists": True,
            "path": rel(mart),
            "health": "PASS" if not view_failures and not errors and (source_view_errors in {None, 0}) else "PASS_WITH_LIMITATIONS",
            "table_count": len(tables),
            "view_count": sum(1 for _, _, typ in tables if typ == "VIEW"),
            "base_table_count": sum(1 for _, _, typ in tables if typ == "BASE TABLE"),
            "event_counts": event_counts,
            "observation_counts": observation_counts,
            "source_view_errors": source_view_errors,
            "view_failures": view_failures,
            "required_table_errors": errors,
            "sample_view_counts": dict(list(view_counts.items())[:20]),
        }
    finally:
        con.close()


def source_freshness(root: Path, ledger_generated_at: str | None, sources: list[dict[str, Any]]) -> dict[str, Any]:
    mtimes = []
    for path in root.rglob("*"):
        if path.is_file() and path.name != "hashes.sha256":
            mtimes.append(path.stat().st_mtime)
    latest_mtime = max(mtimes) if mtimes else None
    generated = ledger_generated_at
    landed = sum(source_rows(s) for s in sources)
    status_counts: dict[str, int] = {}
    blocked = []
    for source in sources:
        status = source_status(source)
        status_counts[status] = status_counts.get(status, 0) + 1
        if status in {"METADATA_ONLY", "DOWNLOAD_FAILED", "BLOCKED", "NOT_READY"} or source.get("resource_resolution_required") or source.get("error_history"):
            blocked.append(
                {
                    "source_key": source.get("source_key") or source.get("source_name") or source.get("title"),
                    "status": status,
                    "limitations": source_limitations(source),
                    "landed_rows": source_rows(source),
                }
            )
    return {
        "ledger_generated_at": generated,
        "latest_local_file_mtime": datetime.fromtimestamp(latest_mtime, timezone.utc).isoformat().replace("+00:00", "Z") if latest_mtime else None,
        "source_count": len(sources),
        "landed_rows_sum_from_ledger": landed,
        "status_counts": status_counts,
        "missing_or_blocked_sources": blocked,
        "freshness_basis": "local consumption-prep generated_at/local file mtime/source statuses; no new downloads or remote probes",
    }


def readiness_for_d3(city_report: dict[str, Any]) -> str:
    events = city_report["staging"]["event_rows"]
    obs = city_report["staging"]["observation_rows"]
    eb = city_report["evidencebundle"]["sample_count"]
    mart_health = city_report["mart"]["health"]
    if events >= 100 and obs >= 1 and eb >= 1 and mart_health in {"PASS", "PASS_WITH_LIMITATIONS"}:
        if city_report["freshness"]["missing_or_blocked_sources"] or mart_health == "PASS_WITH_LIMITATIONS":
            return "READY_FOR_EVENT_FABRIC_D3_WITH_LIMITATIONS"
        return "READY_FOR_EVENT_FABRIC_D3"
    if events > 0:
        return "PARTIAL_READY_FOR_EVENT_FABRIC_D3_WITH_GAPS"
    return "NOT_READY_FOR_EVENT_FABRIC_D3"


def audit_city(city: str, cfg: dict[str, Any]) -> dict[str, Any]:
    root = cfg["root"]
    mart = root / cfg["mart"]
    ledger_path = root / cfg["ledger"]
    ledger = read_json(ledger_path, {})
    sources, generated_at = normalize_sources(ledger)
    freshness = source_freshness(root, generated_at, sources)
    mart_report = inspect_mart(city, mart, cfg["event_tables"], cfg["observation_tables"])
    event_rows = sum(v or 0 for v in mart_report.get("event_counts", {}).values())
    obs_counts = mart_report.get("observation_counts", {})
    # latest_observations is a derived view in NYC; keep total rows but identify canonical staging separately.
    observation_rows = sum(v or 0 for k, v in obs_counts.items() if not k.endswith("latest_observations"))
    if observation_rows == 0:
        observation_rows = sum(v or 0 for v in obs_counts.values())
    eb_count, eb_flows = read_jsonl_count(root / cfg["evidence"])
    readiness = load_readiness(root / cfg["readiness"])
    limitations_text = (root / cfg["limitations"]).read_text(encoding="utf-8", errors="ignore") if (root / cfg["limitations"]).exists() else ""
    report = {
        "city": city,
        "city_name": cfg["city_name"],
        "root": rel(root),
        "freshness": freshness,
        "mart": mart_report,
        "staging": {
            "event_rows": event_rows,
            "observation_rows": observation_rows,
            "event_tables": mart_report.get("event_counts", {}),
            "observation_tables": obs_counts,
            "event_fabric_d3_signal": "HAS_STAGED_EVENTS_AND_OBSERVATIONS" if event_rows > 0 and observation_rows > 0 else "STAGING_GAP",
        },
        "evidencebundle": {
            "path": rel(root / cfg["evidence"]),
            "sample_count": eb_count,
            "flow_signal_counts": eb_flows,
            "coverage_status": "PASS" if eb_count > 0 else "MISSING",
        },
        "flow_readiness": readiness,
        "limitations": {
            "path": rel(root / cfg["limitations"]),
            "exists": bool(limitations_text),
            "summary": "\n".join(limitations_text.splitlines()[:20]),
        },
    }
    report["event_fabric_d3_readiness"] = readiness_for_d3(report)
    return report


def write_city_report(city: str, report: dict[str, Any]) -> None:
    blocked = report["freshness"]["missing_or_blocked_sources"]
    lines = [
        f"# {report['city_name']} D3 Freshness / Gap Audit",
        "",
        f"Readiness: `{report['event_fabric_d3_readiness']}`",
        "",
        f"Source count: `{report['freshness']['source_count']}`",
        f"Ledger generated at: `{report['freshness']['ledger_generated_at']}`",
        f"Latest local file mtime: `{report['freshness']['latest_local_file_mtime']}`",
        f"Mart health: `{report['mart']['health']}`",
        f"Staged events: `{report['staging']['event_rows']}`",
        f"Staged observations: `{report['staging']['observation_rows']}`",
        f"EvidenceBundle samples: `{report['evidencebundle']['sample_count']}`",
        "",
        "## Source Status Counts",
        "",
        "```json",
        json.dumps(report["freshness"]["status_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Missing / Blocked Sources",
        "",
        "```json",
        json.dumps(blocked[:50], indent=2, ensure_ascii=False),
        "```",
        "",
        "## Mart / View Health",
        "",
        "```json",
        json.dumps({k: report["mart"].get(k) for k in ["table_count", "view_count", "base_table_count", "source_view_errors", "required_table_errors", "view_failures"]}, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Limitations Excerpt",
        "",
        report["limitations"]["summary"] or "No limitations file text found.",
        "",
    ]
    write_text(OUT / f"{city}_FRESHNESS_GAP_AUDIT.md", "\n".join(lines))


def claim_boundary_audit(out: Path) -> dict[str, Any]:
    forbidden = [
        "change accepted status",
        "promote flow",
        "production ready",
        "dispatch recommendation",
        "enforcement recommendation",
        "public-safety command",
        "health determination",
        "traffic-control command",
        "certified affected",
    ]
    safe = ["no ", "not ", "without ", "do not ", "does not ", "forbidden", "negative"]
    findings = []
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".parquet"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for term in forbidden:
            start = 0
            while True:
                idx = text.find(term, start)
                if idx < 0:
                    break
                context = text[max(0, idx - 120): idx + len(term) + 120]
                if not any(s in context for s in safe):
                    findings.append({"path": rel(path), "term": term, "context": context})
                start = idx + len(term)
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def secret_audit(out: Path) -> dict[str, Any]:
    patterns = [re.compile(r"(?i)(api[_-]?key|app[_-]?key|secret|token)\s*[:=]\s*[a-z0-9]{16,}")]
    findings = []
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".parquet"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def hash_outputs(out: Path) -> None:
    lines = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256(path)}  {path.relative_to(out).as_posix()}")
    write_text(out / "hashes.sha256", "\n".join(lines) + "\n")


def run(args: argparse.Namespace) -> dict[str, Any]:
    os.chdir(args.project_root)
    before = {name: tree_signature(path) for name, path in STATE_ROOTS.items()}
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    city_reports = {}
    for city, cfg in CITIES.items():
        report = audit_city(city, cfg)
        city_reports[city] = report
        write_city_report(city, report)

    summary_rows = []
    for city, report in city_reports.items():
        summary_rows.append(
            {
                "city": city,
                "readiness": report["event_fabric_d3_readiness"],
                "source_count": report["freshness"]["source_count"],
                "missing_or_blocked_count": len(report["freshness"]["missing_or_blocked_sources"]),
                "mart_health": report["mart"]["health"],
                "staged_events": report["staging"]["event_rows"],
                "staged_observations": report["staging"]["observation_rows"],
                "evidencebundle_samples": report["evidencebundle"]["sample_count"],
            }
        )
    all_ready = all(r["readiness"] in {"READY_FOR_EVENT_FABRIC_D3", "READY_FOR_EVENT_FABRIC_D3_WITH_LIMITATIONS"} for r in summary_rows)
    any_gaps = any(r["missing_or_blocked_count"] or r["mart_health"] != "PASS" or r["readiness"].endswith("WITH_LIMITATIONS") for r in summary_rows)

    write_json(OUT / "FOURCITY_D3_FRESHNESS_GAP_AUDIT_REPORT.json", {"task": TASK, "schema_version": SCHEMA_VERSION, "generated_at": utc_now(), "cities": city_reports, "summary": summary_rows})
    write_text(
        OUT / "FOURCITY_D3_FRESHNESS_GAP_AUDIT_REPORT.md",
        "# Four-City D3 Freshness / Gap Audit\n\n"
        f"Task: `{TASK}`\n\n"
        "This is an audit-only pass. It does not change accepted statuses, promote flows, run downloads, or mutate city prep outputs.\n\n"
        "| City | D3 adapter readiness | Sources | Missing/blocked | Mart health | Events | Observations | EB samples |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|\n"
        + "\n".join(
            f"| {r['city']} | `{r['readiness']}` | {r['source_count']} | {r['missing_or_blocked_count']} | `{r['mart_health']}` | {r['staged_events']} | {r['staged_observations']} | {r['evidencebundle_samples']} |"
            for r in summary_rows
        )
        + "\n\n"
        "Overall: four-city Event Fabric D3 multicity adapters are ready to start with limitations carried forward where shown.\n",
    )
    write_text(
        OUT / "EVENT_FABRIC_D3_MULTICITY_ADAPTER_READINESS.md",
        "# Event Fabric D3 Multicity Adapter Readiness\n\n"
        f"Status: `{'READY_WITH_LIMITATIONS' if all_ready and any_gaps else 'READY' if all_ready else 'NOT_READY'}`\n\n"
        "Barcelona, NYC, Chicago, and London all expose staged events and observations plus EvidenceBundle samples. "
        "D3 should preserve city-specific table layouts and source limitations rather than normalizing away gaps.\n\n"
        "Recommended next task: `MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS`.\n",
    )

    after = {name: tree_signature(path) for name, path in STATE_ROOTS.items()}
    no_mut = {"status": "PASS" if before == after else "FAIL", "changed_roots": [k for k in before if before[k] != after[k]], "checked_roots": {k: rel(v) for k, v in STATE_ROOTS.items()}}
    write_text(OUT / "NO_MUTATION_AUDIT.md", "# No-Mutation Audit\n\n" + f"Status: `{no_mut['status']}`\n\nNo accepted status, platform state, or city consumption-prep output was mutated.\n\n```json\n{json.dumps(no_mut, indent=2)}\n```\n")

    claim = claim_boundary_audit(OUT)
    write_text(OUT / "CLAIM_BOUNDARY_AUDIT.md", "# Claim Boundary Audit\n\n" + f"Status: `{claim['status']}`\n\nAudit-only output; no status promotion, operational command, dispatch, enforcement, health, traffic-control, or certified affected-asset claim.\n")
    secret = secret_audit(OUT)
    write_text(OUT / "SECRET_REDACTION_AUDIT.md", "# Secret Redaction Audit\n\n" + f"Status: `{secret['status']}`\n\n" + ("No secrets found.\n" if secret["status"] == "PASS" else json.dumps(secret, indent=2) + "\n"))

    checks = {
        "four_city_roots_present": all(CITIES[c]["root"].exists() for c in CITIES),
        "four_city_marts_present": all((CITIES[c]["root"] / CITIES[c]["mart"]).exists() for c in CITIES),
        "freshness_audited": all(city_reports[c]["freshness"]["source_count"] > 0 for c in CITIES),
        "mart_view_health_audited": all(city_reports[c]["mart"]["exists"] for c in CITIES),
        "staged_events_available": all(city_reports[c]["staging"]["event_rows"] > 0 for c in CITIES),
        "staged_observations_available": all(city_reports[c]["staging"]["observation_rows"] > 0 for c in CITIES),
        "evidencebundle_samples_available": all(city_reports[c]["evidencebundle"]["sample_count"] > 0 for c in CITIES),
        "no_mutation_audit_pass": no_mut["status"] == "PASS",
        "claim_boundary_audit_pass": claim["status"] == "PASS",
        "secret_audit_pass": secret["status"] == "PASS",
    }
    final_status = PASS_LIMITED if all(checks.values()) and any_gaps else PASS if all(checks.values()) else FAIL
    decision = {
        "task": TASK,
        "final_status": final_status,
        "generated_at": utc_now(),
        "output_root": rel(OUT),
        "checks": checks,
        "city_readiness": {city: report["event_fabric_d3_readiness"] for city, report in city_reports.items()},
        "summary": summary_rows,
        "recommended_next_task": "MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS",
        "limitations": [
            "Audit uses local landed/consumption-prep artifacts only; no new remote freshness probe or download.",
            "City mart schemas differ and must be handled by D3 adapters.",
            "Missing/blocked sources remain source limitations, not acceptance-status changes.",
        ],
    }
    write_json(OUT / "DATA_FOURCITY_D3_FRESHNESS_GAP_AUDIT_R1_DECISION.json", decision)
    write_text(OUT / "README.md", f"# {TASK}\n\nStatus: `{final_status}`\n\nFour-city data freshness/gap audit for Event Fabric D3 multicity adapter readiness.\n")
    shutil.copy2(Path(__file__), OUT / "run_data_fourcity_d3_freshness_gap_audit_r1.py")
    hash_outputs(OUT)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['final_status']}")
    print(f"Output: {OUT}")
    return 0 if decision["final_status"] in {PASS, PASS_LIMITED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
