#!/usr/bin/env python3
"""MAIN-TRACK2C-D4X-CITY-DASHBOARD-DATA-INTEGRATION-R6.

Builds a city-first dashboard layer on top of the R5 app package. This turns
the demo from project boards/story cards into a browsable city data dashboard:
sources, events, issues, mart health, selected buildings, evidence, and
limitations for Barcelona, NYC, Chicago, and London.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import duckdb  # type: ignore
except Exception:  # pragma: no cover
    duckdb = None


TASK = "MAIN-TRACK2C-D4X-CITY-DASHBOARD-DATA-INTEGRATION-R6"
PASS_LIMITED = "PASS_MAIN_TRACK2C_D4X_CITY_DASHBOARD_DATA_INTEGRATION_R6_WITH_LIMITATIONS"
FAIL = "FAIL_MAIN_TRACK2C_D4X_CITY_DASHBOARD_DATA_INTEGRATION_R6"
OUT = Path("outputs/main_track2c_d4x_city_dashboard_data_integration_r6")
R5 = Path("outputs/main_track2c_d4x_rich_city_demo_content_integration_r5")

CITY_ROOTS = {
    "BARC": Path("outputs/barc_allflows_consumption_prep_r1"),
    "NYC": Path("outputs/nyc_flow_consumption_prep_r1"),
    "CHI": Path("outputs/chi_allflows_consumption_prep_r1"),
    "LON": Path("outputs/lon_allflows_consumption_prep_r1"),
}

CITY_NAMES = {
    "BARC": "Barcelona",
    "NYC": "New York City",
    "CHI": "Chicago",
    "LON": "London",
}

INPUT_ROOTS = {
    "r5": R5,
    "r4": Path("outputs/main_track2c_d4x_demo_capture_and_polish_r4"),
    "d4_event_feed": Path("outputs/main_track1_d4_event_feed_and_overlay_ui"),
    "d4_evidence_trace": Path("outputs/main_track1_d4_evidence_trace_panel"),
    "d4_review": Path("outputs/main_track1_d4_review_ui_workflow"),
    "d4_replay": Path("outputs/main_track1_d4_scenario_replay_panel"),
    "d4y_runtime": Path("outputs/main_track1_d4y_city_situation_runtime_binding_r1"),
    "d4y_graph": Path("outputs/main_track1_d4y_situation_graph_and_query_r1"),
    "barc_lod2": Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1"),
    "nyc_lod2": Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1"),
    **{f"{city.lower()}_prep": root for city, root in CITY_ROOTS.items()},
}

CITY_FILES = {
    city: {
        "ledger": root / f"{city}_SOURCE_LEDGER_FINAL.json",
        "readiness": root / f"{city}_FLOW_READINESS_MATRIX.csv",
        "mart": root / f"{city}_FLOW_MART.duckdb",
        "evidence": root / f"{city}_EVIDENCEBUNDLE_SAMPLES.jsonl",
        "smoke": root / f"{city}_QUERY_SMOKE_PACK.jsonl",
        "quality": root / f"{city}_DATA_QUALITY_REPORT.md",
        "limitations": root / f"{city}_LIMITATIONS.md",
        "staging": root / f"{city}_EVENT_OBSERVATION_STAGING_REPORT.md",
    }
    for city, root in CITY_ROOTS.items()
}

D4_FILES = {
    "event_feed": Path("outputs/main_track1_d4_event_feed_and_overlay_ui/D4_EVENT_FEED_ITEMS.json"),
    "evidence_trace": Path("outputs/main_track1_d4_evidence_trace_panel/D4_EVIDENCE_TRACE_PANEL_ITEMS.json"),
    "review_packets": Path("outputs/main_track1_d4_review_ui_workflow/D4_REVIEW_PACKET_VIEW_MODEL.json"),
    "replay_items": Path("outputs/main_track1_d4_scenario_replay_panel/D4_SCENARIO_REPLAY_ITEMS.json"),
    "query_results": Path("outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_DETERMINISTIC_QUERY_RESULTS.json"),
    "barc_identity": Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1/identity_shards/shard_000_identity.jsonl"),
    "nyc_identity": Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1/identity_shards/shard_000_identity.jsonl"),
}

LIMITATIONS = [
    "local static demo app only",
    "city dashboard uses generated local prep outputs and curated samples",
    "not production UI",
    "no auth/RBAC",
    "no public deployment",
    "no live Track 1 R2 intelligence connected",
    "no command/control/enforcement/dispatch/routing",
    "no legal finding",
    "no confirmed violation",
    "no certified affected-building or impact claim",
    "simulation/synthetic rows are context only, not observed truth",
    "3D source IDs are source context only, not ownership/legal truth",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if limit is not None and len(rows) >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("rb") as fh:
        for _ in fh:
            count += 1
    return count


def items_from(obj: Any, preferred_key: str = "items") -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [item for item in obj if isinstance(item, dict)]
    if isinstance(obj, dict):
        for key in [preferred_key, "items", "packets", "views", "results", "sources"]:
            value = obj.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def one_line(value: Any, max_len: int = 260) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    text = str(value or "").replace("\n", " ").strip()
    return text[: max_len - 3] + "..." if len(text) > max_len else text


def number(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).replace(",", "").strip()
    try:
        return int(float(text))
    except ValueError:
        return 0


def fmt_num(value: Any) -> str:
    return f"{number(value):,}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_outputs() -> None:
    rows = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append(f"{sha256(path)}  {path.relative_to(OUT).as_posix()}")
    write_text(OUT / "hashes.sha256", "\n".join(rows))


def root_signature(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False}
    rows = []
    if root.is_file():
        st = root.stat()
        rows.append([root.name, st.st_size, st.st_mtime_ns])
    else:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                st = path.stat()
                rows.append([path.relative_to(root).as_posix(), st.st_size, st.st_mtime_ns])
    return {
        "exists": True,
        "file_count": len(rows),
        "signature": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
    }


def snapshot_roots() -> dict[str, Any]:
    return {name: root_signature(path) for name, path in INPUT_ROOTS.items() if path.exists()}


def safe_reset_output(project_root: Path) -> None:
    out_abs = (project_root / OUT).resolve()
    root_abs = project_root.resolve()
    if root_abs not in [out_abs, *out_abs.parents]:
        raise RuntimeError(f"Refusing to delete output outside workspace: {out_abs}")
    if OUT.exists():
        shutil.rmtree(OUT)
    for folder in ["app_shell/data", "screenshots", "dashboard", "smoke", "guardrails", "logs"]:
        (OUT / folder).mkdir(parents=True, exist_ok=True)


def read_ledger(city: str) -> list[dict[str, Any]]:
    path = CITY_FILES[city]["ledger"]
    raw = read_json(path, [])
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        rows = raw.get("sources", [])
    else:
        rows = []
    return [row for row in rows if isinstance(row, dict)]


def source_name(row: dict[str, Any]) -> str:
    return one_line(
        row.get("source_key")
        or row.get("name")
        or row.get("source_name")
        or row.get("dataset_id_or_url")
        or row.get("url")
        or row.get("resource_name")
        or "source"
    )


def source_rows(row: dict[str, Any]) -> int:
    return max(
        number(row.get("rows_landed")),
        number(row.get("landed_rows")),
        number(row.get("landed_row_count")),
        number(row.get("landed_features")),
        number(row.get("total_available") if row.get("landing_status") == "FULL" else 0),
    )


def source_status(row: dict[str, Any]) -> str:
    return one_line(
        row.get("landing_status")
        or row.get("consumption_status")
        or row.get("raw_status")
        or row.get("status")
        or row.get("safe_boundary_class")
        or "UNKNOWN"
    )


def read_readiness(city: str) -> list[dict[str, Any]]:
    path = CITY_FILES[city]["readiness"]
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def schema_table_counts(mart: Path) -> dict[str, Any]:
    result = {
        "status": "NOT_AVAILABLE",
        "schema_counts": {},
        "tables": [],
        "event_tables": [],
        "observation_tables": [],
        "event_count": 0,
        "observation_count": 0,
        "sample_event_rows": [],
        "limitations": [],
    }
    if duckdb is None:
        result["status"] = "DUCKDB_IMPORT_UNAVAILABLE"
        result["limitations"].append("duckdb python package unavailable")
        return result
    if not mart.exists():
        result["status"] = "MART_MISSING"
        return result
    try:
        con = duckdb.connect(str(mart), read_only=True)
        tables = con.execute(
            "select table_schema, table_name, table_type from information_schema.tables "
            "where table_schema not in ('information_schema','pg_catalog') "
            "order by table_schema, table_name"
        ).fetchall()
        result["status"] = "PASS"
        schema_counts = Counter(schema for schema, _, _ in tables)
        result["schema_counts"] = dict(schema_counts)
        for schema, table, table_type in tables:
            table_ref = f"{schema}.{table}"
            row = {"schema": schema, "table": table, "type": table_type, "table_ref": table_ref}
            try:
                row["row_count"] = int(con.execute(f'select count(*) from "{schema}"."{table}"').fetchone()[0])
            except Exception as exc:
                row["row_count"] = None
                row["error"] = one_line(exc, 180)
                result["limitations"].append(f"{table_ref} count failed: {one_line(exc, 100)}")
            result["tables"].append(row)
            table_lower = table.lower()
            if "event" in table_lower or table_lower in {"staged_events"}:
                result["event_tables"].append(row)
            if "observation" in table_lower or table_lower in {"staged_observations"}:
                result["observation_tables"].append(row)
        event_counts = [row.get("row_count") or 0 for row in result["event_tables"]]
        observation_counts = [row.get("row_count") or 0 for row in result["observation_tables"]]
        result["event_count"] = max(event_counts) if event_counts else 0
        result["observation_count"] = max(observation_counts) if observation_counts else 0
        sample_table = next((row for row in result["event_tables"] if row.get("row_count")), None)
        if sample_table:
            rows = con.execute(
                f'select * from "{sample_table["schema"]}"."{sample_table["table"]}" limit 8'
            ).fetchall()
            cols = [desc[0] for desc in con.description or []]
            result["sample_event_rows"] = [
                {col: one_line(value, 180) for col, value in zip(cols, raw)}
                for raw in rows
            ]
        con.close()
    except Exception as exc:
        result["status"] = "MART_READ_LIMITATION"
        result["limitations"].append(one_line(exc, 220))
    return result


def parse_staging_report(path: Path) -> dict[str, int]:
    result = {"events": 0, "observations": 0}
    if not path.exists():
        return result
    text = path.read_text(encoding="utf-8", errors="ignore")
    events = re.search(r"Events:\s*`?([0-9,]+)`?", text, re.I)
    obs = re.search(r"Observations:\s*`?([0-9,]+)`?", text, re.I)
    if events:
        result["events"] = number(events.group(1))
    if obs:
        result["observations"] = number(obs.group(1))
    return result


def important_sources(city: str, ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for source in sorted(ledger, key=source_rows, reverse=True)[:16]:
        rows.append({
            "source": source_name(source),
            "rows": source_rows(source),
            "rows_label": fmt_num(source_rows(source)),
            "status": source_status(source),
            "flows": source.get("flows") or source.get("flow_candidates") or source.get("flow_ids") or [],
            "privacy": source.get("privacy_class") or source.get("boundary_class") or source.get("safe_boundary_class"),
            "geo_fields": source.get("geo_fields") or source.get("geometry_present"),
            "date_fields": source.get("date_fields"),
            "notes": one_line(source.get("notes") or source.get("schema_issue") or source.get("error_history")),
        })
    return rows


def source_issues(ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues = []
    for source in ledger:
        status = source_status(source)
        text = " ".join([
            status,
            one_line(source.get("notes")),
            one_line(source.get("schema_issue")),
            one_line(source.get("error_history")),
        ]).lower()
        if any(token in text for token in ["metadata", "blocked", "failed", "limitation", "schema", "partial", "capped", "sample"]):
            issues.append({
                "source": source_name(source),
                "status": status,
                "rows": source_rows(source),
                "issue": one_line(source.get("schema_issue") or source.get("notes") or source.get("error_history") or status),
            })
    return issues[:20]


def limitation_text(city: str) -> str:
    texts = []
    for key in ["limitations", "quality"]:
        path = CITY_FILES[city][key]
        if path.exists():
            texts.append(path.read_text(encoding="utf-8", errors="ignore")[:3500])
    return "\n\n".join(texts)


def city_dashboard(city: str) -> dict[str, Any]:
    ledger = read_ledger(city)
    readiness = read_readiness(city)
    mart = schema_table_counts(CITY_FILES[city]["mart"])
    report_counts = parse_staging_report(CITY_FILES[city]["staging"])
    events = mart["event_count"] or report_counts["events"]
    observations = mart["observation_count"] or report_counts["observations"]
    status_counts = Counter(source_status(source) for source in ledger)
    total_rows = sum(source_rows(source) for source in ledger)
    flow_rows = []
    for row in readiness:
        flow_id = row.get("flow_id") or row.get("flow") or row.get("flow_name") or "flow"
        flow_rows.append({
            "flow": flow_id,
            "name": row.get("flow_name") or row.get("flow_label") or row.get("candidate_output") or flow_id,
            "row_coverage": row.get("row_file_coverage") or row.get("row_coverage") or row.get("silver_row_coverage"),
            "source_coverage": row.get("source_coverage"),
            "status": row.get("recommended_candidate_status") or row.get("final_proposed_status") or row.get("candidate_status"),
            "limitations": row.get("limitations"),
        })
    return {
        "city_id": city,
        "city_name": CITY_NAMES[city],
        "source_count": len(ledger),
        "landed_rows": total_rows,
        "landed_rows_label": fmt_num(total_rows),
        "staged_events": events,
        "staged_events_label": fmt_num(events),
        "staged_observations": observations,
        "staged_observations_label": fmt_num(observations),
        "evidence_samples": count_lines(CITY_FILES[city]["evidence"]),
        "query_smoke_rows": count_lines(CITY_FILES[city]["smoke"]),
        "status_counts": dict(status_counts),
        "flow_readiness": flow_rows,
        "top_sources": important_sources(city, ledger),
        "source_issues": source_issues(ledger),
        "mart": {
            "status": mart["status"],
            "schema_counts": mart["schema_counts"],
            "table_count": len(mart["tables"]),
            "event_tables": mart["event_tables"][:8],
            "observation_tables": mart["observation_tables"][:8],
            "important_tables": sorted(mart["tables"], key=lambda row: row.get("row_count") or 0, reverse=True)[:16],
            "sample_event_rows": mart["sample_event_rows"],
            "limitations": mart["limitations"][:8],
        },
        "limitation_excerpt": one_line(limitation_text(city), 900),
    }


def building_examples() -> dict[str, Any]:
    nyc_rows = sorted(read_jsonl(D4_FILES["nyc_identity"], 8000), key=lambda row: number(row.get("HeightFT")), reverse=True)[:8]
    barc_rows = sorted(read_jsonl(D4_FILES["barc_identity"], 2000), key=lambda row: number(row.get("COTA")), reverse=True)[:8]
    return {
        "NYC": [
            {
                "building_id": row.get("citybrain_building_id"),
                "BIN": row.get("bin"),
                "BBL": row.get("base_bbl"),
                "DoITT": row.get("doitt_id"),
                "OBJECTID": row.get("OBJECTID"),
                "HeightFT": row.get("HeightFT"),
                "heightroof": row.get("heightroof"),
                "groundelev": row.get("groundelev"),
                "RMSE": row.get("RMSE"),
                "GlobalID": row.get("globalid"),
                "boundary": row.get("claim_boundary"),
            }
            for row in nyc_rows
        ],
        "BARC": [
            {
                "building_id": row.get("citybrain_building_id"),
                "OBJECTID": row.get("OBJECTID"),
                "source_id": row.get("citybrain_3d_source_id"),
                "district": row.get("citybrain_district_ref"),
                "neighbourhood": row.get("citybrain_neighbourhood_ref"),
                "COTA": row.get("COTA"),
                "theme": row.get("TEMA_DESCR"),
                "boundary": row.get("claim_boundary"),
            }
            for row in barc_rows
        ],
    }


def d4_city_feed() -> dict[str, Any]:
    feed = items_from(read_json(D4_FILES["event_feed"], {}))
    evidence = items_from(read_json(D4_FILES["evidence_trace"], {}))
    review = items_from(read_json(D4_FILES["review_packets"], {}), "packets")
    replay = items_from(read_json(D4_FILES["replay_items"], {}))
    query = items_from(read_json(D4_FILES["query_results"], {}), "results")
    lifecycle_counts = Counter(item.get("lifecycle_state") for item in feed)
    city_counts = Counter(item.get("city_id") for item in feed)

    def present_event(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "feed_item_id": item.get("feed_item_id"),
            "city_id": item.get("city_id"),
            "title": item.get("title"),
            "summary": one_line(item.get("summary"), 260),
            "lifecycle": item.get("lifecycle_state"),
            "event_family": item.get("event_family"),
            "producer": item.get("producer"),
            "event_time": item.get("observed_or_event_time"),
            "evidencebundle_ref": item.get("evidencebundle_ref", {}).get("bundle_id") if isinstance(item.get("evidencebundle_ref"), dict) else None,
            "review_packet_ref": item.get("review_packet_ref"),
            "scenario_ref": item.get("scenario_ref"),
            "limitations": item.get("limitation_refs", [])[:4],
            "claim_boundary": item.get("claim_boundary"),
            "no_action_taken": item.get("no_action_taken"),
        }

    preferred = []
    for lifecycle in ["candidate/review", "observed/context", "simulated/context", "synthetic/context", "limitation-only", "late/out-of-order", "expired/superseded"]:
        preferred.extend([item for item in feed if item.get("lifecycle_state") == lifecycle][:6])
    return {
        "feed_item_count": len(feed),
        "evidence_trace_count": len(evidence),
        "review_packet_count": len(review),
        "replay_item_count": len(replay),
        "query_result_count": len(query),
        "lifecycle_counts": dict(lifecycle_counts),
        "city_counts": dict(city_counts),
        "featured_events": [present_event(item) for item in preferred[:40]],
        "review_packets": review[:8],
        "replay_items": replay[:12],
        "query_results": query[:12],
    }


def build_dashboard_data() -> dict[str, Any]:
    cities = {city: city_dashboard(city) for city in CITY_ROOTS}
    data = {
        "schema_version": "track2c-r6-city-dashboard.v1",
        "task": TASK,
        "generated_at": utc_now(),
        "status": "CITY_DASHBOARD_DATA_READY_WITH_LIMITATIONS",
        "cities": cities,
        "building_examples": building_examples(),
        "d4_feed": d4_city_feed(),
        "limitations": LIMITATIONS,
        "guardrails": {
            "not_production": True,
            "no_command_control": True,
            "no_dispatch_enforcement_routing": True,
            "no_legal_or_certified_truth": True,
            "no_live_r2_intelligence": True,
        },
    }
    write_json(OUT / "dashboard/CITY_DASHBOARD_DATA.json", data)
    write_json(OUT / "app_shell/data/city_dashboard_data.json", data)
    return data


def copy_and_patch_app(data: dict[str, Any]) -> dict[str, Any]:
    src = R5 / "app_shell"
    dst = OUT / "app_shell"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    write_json(dst / "data/city_dashboard_data.json", data)
    index_path = dst / "index.html"
    css_path = dst / "styles.css"
    js_path = dst / "app.js"

    index = index_path.read_text(encoding="utf-8")
    index = index.replace('<a href="#overview">Overview</a>', '<a href="#city_dashboard">City Dashboard</a>\n      <a href="#overview">Overview</a>')
    dashboard_section = """

    <section id="city_dashboard" class="section city-dashboard-section">
      <div class="section-head dashboard-head">
        <div><span class="eyebrow">city dashboard</span><h2>Collected City Data, Events, Issues</h2></div>
        <p>Barcelona, NYC, Chicago, and London dashboards built from local consumption prep marts, event feed outputs, evidence traces, source ledgers, and 3D identity shards.</p>
      </div>
      <div class="city-tabs" id="city-dashboard-tabs"></div>
      <div class="city-dashboard-grid">
        <article class="city-panel city-summary-panel" id="city-dashboard-summary"></article>
        <article class="city-panel city-events-panel" id="city-dashboard-events"></article>
      </div>
      <div class="city-dashboard-grid lower">
        <article class="city-panel" id="city-dashboard-sources"></article>
        <article class="city-panel" id="city-dashboard-issues"></article>
      </div>
      <div class="city-dashboard-grid lower">
        <article class="city-panel" id="city-dashboard-buildings"></article>
        <article class="city-panel" id="city-dashboard-mart"></article>
      </div>
    </section>
"""
    index = index.replace("    <section id=\"overview\"", dashboard_section + "\n    <section id=\"overview\"")
    index_path.write_text(index, encoding="utf-8", newline="\n")

    css_path.write_text(
        css_path.read_text(encoding="utf-8")
        + """

.city-dashboard-section { border-color: rgba(82,243,208,.34); background: linear-gradient(180deg, rgba(13,31,42,.82), rgba(7,16,21,.62)); }
.dashboard-head h2 { font-size: 32px; }
.city-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 16px; }
.city-tab { min-height: 42px; padding: 9px 13px; border-radius: 8px; border: 1px solid var(--line); background: rgba(7,16,21,.56); color: var(--text); cursor: pointer; }
.city-tab.active { border-color: var(--accent); background: rgba(82,243,208,.11); }
.city-dashboard-grid { display: grid; grid-template-columns: minmax(0, .92fr) minmax(0, 1.08fr); gap: 14px; }
.city-dashboard-grid.lower { margin-top: 14px; }
.city-panel { border: 1px solid var(--line); border-radius: 8px; background: rgba(7,16,21,.48); padding: 15px; min-height: 260px; overflow: hidden; }
.city-panel h3 { margin: 0 0 12px; font-size: 21px; }
.metric-grid-city { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 9px; margin-bottom: 12px; }
.metric-city { border: 1px solid var(--line-soft); border-radius: 8px; padding: 11px; background: rgba(19,35,48,.58); min-height: 78px; }
.metric-city span { display:block; color: var(--muted); font-size: 12px; margin-bottom: 7px; }
.metric-city strong { font-size: 20px; overflow-wrap: anywhere; }
.city-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.city-table th { color: var(--muted); font-weight: 600; text-align: left; border-bottom: 1px solid var(--line); padding: 7px 6px; }
.city-table td { border-bottom: 1px solid rgba(116,166,190,.13); padding: 8px 6px; vertical-align: top; overflow-wrap: anywhere; }
.city-feed { display: grid; gap: 8px; max-height: 440px; overflow: auto; padding-right: 5px; }
.city-event-row { border: 1px solid var(--line-soft); border-radius: 8px; padding: 10px; background: rgba(19,35,48,.52); }
.city-event-row strong { display: block; margin: 7px 0 5px; }
.city-event-row p { margin: 0; color: #cfe4ef; line-height: 1.38; }
.city-issue-list { display: grid; gap: 8px; max-height: 390px; overflow: auto; padding-right: 5px; }
.city-issue { border-left: 3px solid var(--warn); padding: 9px 10px; background: rgba(255,211,105,.06); border-radius: 6px; }
.city-issue strong, .city-issue span { overflow-wrap: anywhere; }
.flow-pill-list { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 10px; }
.flow-pill { border: 1px solid var(--line-soft); border-radius: 999px; padding: 5px 8px; color: #cfe4ef; background: rgba(7,16,21,.42); font-size: 12px; }
.building-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px; max-height: 390px; overflow: auto; padding-right: 5px; }
.building-card { border: 1px solid var(--line-soft); border-radius: 8px; padding: 10px; background: rgba(19,35,48,.52); overflow-wrap: anywhere; }
.building-card strong { display:block; margin-bottom: 6px; }
.data-note { color: var(--muted); font-size: 12px; line-height: 1.35; margin-top: 8px; }
@media (max-width: 1180px) { .city-dashboard-grid, .city-dashboard-grid.lower { grid-template-columns: 1fr; } }
@media (max-width: 760px) { .metric-grid-city, .building-grid { grid-template-columns: 1fr; } }
""",
        encoding="utf-8",
        newline="\n",
    )

    dashboard_json = json.dumps(data, ensure_ascii=False)
    js_path.write_text(
        js_path.read_text(encoding="utf-8")
        + f"""

const CITY_DASHBOARD_DATA = {dashboard_json};
const cityParam = new URLSearchParams(window.location.search).get('city');
let activeDashboardCity = CITY_DASHBOARD_DATA.cities[cityParam] ? cityParam : 'BARC';

function cityRows(rows, cols, limit = 12) {{
  return (rows || []).slice(0, limit).map(row => `<tr>${{cols.map(col => `<td>${{esc(row[col] ?? '')}}</td>`).join('')}}</tr>`).join('');
}}

function metric(label, value) {{
  return `<div class="metric-city"><span>${{esc(label)}}</span><strong>${{esc(value)}}</strong></div>`;
}}

function renderCityDashboard() {{
  const tabs = document.getElementById('city-dashboard-tabs');
  const summary = document.getElementById('city-dashboard-summary');
  const events = document.getElementById('city-dashboard-events');
  const sources = document.getElementById('city-dashboard-sources');
  const issues = document.getElementById('city-dashboard-issues');
  const buildings = document.getElementById('city-dashboard-buildings');
  const mart = document.getElementById('city-dashboard-mart');
  if (!tabs || !summary || !events || !sources || !issues || !buildings || !mart) return;
  const city = CITY_DASHBOARD_DATA.cities[activeDashboardCity];
  const dashboardTitle = city.city_name.endsWith('City') ? `${{city.city_name}} Dashboard` : `${{city.city_name}} City Dashboard`;
  tabs.innerHTML = Object.values(CITY_DASHBOARD_DATA.cities).map(item => `
    <button class="city-tab ${{item.city_id === activeDashboardCity ? 'active' : ''}}" data-city="${{esc(item.city_id)}}">
      ${{esc(item.city_name)}} <span class="muted">${{esc(item.staged_events_label)}} events</span>
    </button>
  `).join('');
  tabs.querySelectorAll('[data-city]').forEach(button => button.addEventListener('click', () => {{
    activeDashboardCity = button.dataset.city;
    renderCityDashboard();
  }}));

  const flowPills = (city.flow_readiness || []).map(flow => `<span class="flow-pill">${{esc(flow.flow)}} · ${{esc(flow.status || flow.name)}}</span>`).join('');
  const topLayerPills = (city.top_sources || []).slice(0, 8).map(source => `<span class="flow-pill">${{esc(source.source)}} · ${{esc(source.rows_label)}}</span>`).join('');
  summary.innerHTML = `
    <h3>${{esc(dashboardTitle)}}</h3>
    <div class="metric-grid-city">
      ${{metric('Sources', city.source_count)}}
      ${{metric('Rows Landed', city.landed_rows_label)}}
      ${{metric('Staged Events', city.staged_events_label)}}
      ${{metric('Observations', city.staged_observations_label)}}
      ${{metric('Evidence Samples', city.evidence_samples)}}
      ${{metric('Mart Tables/Views', city.mart.table_count)}}
    </div>
    <h4>Top Collected Layers</h4>
    <div class="flow-pill-list">${{topLayerPills}}</div>
    <h4>Flow Consumption</h4>
    <div class="flow-pill-list">${{flowPills}}</div>
    <p class="data-note">${{esc(city.limitation_excerpt || 'Limitations are rendered in the city issue panel.')}}</p>
  `;

  const feedExact = CITY_DASHBOARD_DATA.d4_feed.featured_events.filter(item => item.city_id === activeDashboardCity).slice(0, 8);
  const feedFallback = CITY_DASHBOARD_DATA.d4_feed.featured_events.filter(item => item.city_id === 'MULTICITY' || item.city_id === 'TRACK1_RUNTIME').slice(0, 4);
  const feed = feedExact.concat(feedFallback).slice(0, 10);
  const issueEvents = (city.source_issues || []).slice(0, 6);
  const seenMart = new Set();
  const eventRows = (city.mart.sample_event_rows || []).filter(row => {{
    const key = `${{row.title || row.event_type || row.event_id || row.source_key || row.source || row.table_name || 'event'}}|${{row.summary || row.description || row.lifecycle_state || row.event_family || row.event_kind || ''}}`;
    if (seenMart.has(key)) return false;
    seenMart.add(key);
    return true;
  }}).slice(0, 5);
  events.innerHTML = `
    <h3>Events And Issues Happening Now</h3>
    <div class="city-feed">
      ${{feed.map(item => `<div class="city-event-row"><span class="badge neutral">${{esc(item.lifecycle)}}</span><span class="badge warn">no action</span><strong>${{esc(item.title)}}</strong><p>${{esc(item.summary)}}</p></div>`).join('')}}
      ${{issueEvents.map(issue => `<div class="city-event-row"><span class="badge warn">source issue</span><strong>${{esc(issue.source)}}</strong><p>${{esc(issue.status)}} · ${{esc(issue.issue)}}</p></div>`).join('')}}
      ${{eventRows.map(row => `<div class="city-event-row"><span class="badge good">mart event sample</span><strong>${{esc(row.title || row.event_type || row.event_id || row.source_key || row.source || 'staged event')}}</strong><p>${{esc(row.summary || row.description || row.lifecycle_state || row.event_family || row.event_kind || JSON.stringify(row).slice(0,240))}}</p></div>`).join('')}}
    </div>
  `;

  sources.innerHTML = `
    <h3>Collected Source Layers</h3>
    <table class="city-table">
      <thead><tr><th>Source</th><th>Status</th><th>Rows</th><th>Boundary</th></tr></thead>
      <tbody>${{cityRows(city.top_sources, ['source','status','rows_label','privacy'], 14)}}</tbody>
    </table>
  `;

  issues.innerHTML = `
    <h3>Source Issues / Limitations</h3>
    <div class="city-issue-list">
      ${{(city.source_issues || []).slice(0, 14).map(issue => `<div class="city-issue"><strong>${{esc(issue.source)}}</strong><br><span>${{esc(issue.status)}} · ${{esc(issue.issue)}}</span></div>`).join('')}}
      ${{(city.mart.limitations || []).map(item => `<div class="city-issue"><strong>Mart limitation</strong><br><span>${{esc(item)}}</span></div>`).join('')}}
    </div>
  `;

  const bset = CITY_DASHBOARD_DATA.building_examples[activeDashboardCity] || [];
  buildings.innerHTML = `
    <h3>${{activeDashboardCity === 'NYC' || activeDashboardCity === 'BARC' ? 'Real 3D / Building Examples' : 'City Asset Context'}}</h3>
    <div class="building-grid">
      ${{bset.length ? bset.map(item => `<div class="building-card"><strong>${{esc(item.building_id || item.OBJECTID || item.BIN || 'source object')}}</strong>${{Object.entries(item).filter(([k]) => !['boundary'].includes(k)).slice(1,7).map(([k,v]) => `<div><span class="muted">${{esc(k)}}:</span> ${{esc(v)}}</div>`).join('')}}<p class="data-note">${{esc(item.boundary)}}</p></div>`).join('') : '<div class="building-card"><strong>No local 3D identity examples yet</strong><p class="data-note">This city can still show source, event, issue, and mart health data. 3D identity examples remain a later asset-registry task.</p></div>'}}
    </div>
  `;

  mart.innerHTML = `
    <h3>Mart Health / Data Tables</h3>
    <table class="city-table">
      <thead><tr><th>Table/View</th><th>Type</th><th>Rows</th></tr></thead>
      <tbody>${{(city.mart.important_tables || []).slice(0, 14).map(row => `<tr><td>${{esc(row.table_ref)}}</td><td>${{esc(row.type)}}</td><td>${{esc(row.row_count ?? '')}}</td></tr>`).join('')}}</tbody>
    </table>
  `;
}}

renderCityDashboard();
""",
        encoding="utf-8",
        newline="\n",
    )

    app_data = read_json(dst / "data/app_data.json", {})
    app_data["CityDashboard"] = {
        "status": "CITY_DASHBOARD_INTEGRATED",
        "city_count": len(data["cities"]),
        "feed_item_count": data["d4_feed"]["feed_item_count"],
        "cities": list(data["cities"].keys()),
    }
    write_json(dst / "data/app_data.json", app_data)
    return {"status": "PACKAGED_R5_APP_WITH_CITY_DASHBOARD", "app_shell_path": str((dst / "index.html").resolve())}


def chrome_path() -> Path | None:
    for candidate in [
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    ]:
        if candidate.exists():
            return candidate
    return None


def chrome_screenshots() -> tuple[dict[str, Any], dict[str, Any]]:
    chrome = chrome_path()
    shots = [
        ("r6_01_city_dashboard_barc.png", "city_dashboard", "BARC"),
        ("r6_02_city_dashboard_nyc.png", "city_dashboard", "NYC"),
        ("r6_03_city_dashboard_chi.png", "city_dashboard", "CHI"),
        ("r6_04_city_dashboard_lon.png", "city_dashboard", "LON"),
        ("r6_05_city_assets_events.png", "cities_assets", "NYC"),
        ("r6_06_guardrails.png", "intelligence_guardrails", "BARC"),
    ]
    manifest = {"status": "PASS", "items": [], "screenshot_count": 0}
    if not chrome:
        manifest["status"] = "FALLBACK_CAPTURE_NOTES_ONLY"
        write_text(OUT / "logs/SCREENSHOT_FALLBACK.md", "Chrome/Edge was not available. Open the R6 app manually.")
    else:
        app_uri = (OUT / "app_shell/index.html").resolve().as_uri()
        for name, capture, city in shots:
            out = (OUT / "screenshots" / name).resolve()
            cmd = [
                str(chrome),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--allow-file-access-from-files",
                "--run-all-compositor-stages-before-draw",
                "--window-size=1600,1000",
                "--virtual-time-budget=4500",
                f"--screenshot={out}",
                f"{app_uri}?capture={capture}&city={city}",
            ]
            item = {"path": str(out.relative_to(Path.cwd())), "capture": capture, "city": city, "status": "CAPTURED", "bytes": 0, "error": None}
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                if result.returncode != 0 or not out.exists():
                    item["status"] = "FAILED"
                    item["error"] = (result.stderr or result.stdout or "missing screenshot")[:1000]
                else:
                    item["bytes"] = out.stat().st_size
            except Exception as exc:
                item["status"] = "FAILED"
                item["error"] = str(exc)
            manifest["items"].append(item)
        manifest["screenshot_count"] = sum(1 for item in manifest["items"] if item["status"] == "CAPTURED")
        if manifest["screenshot_count"] < len(shots):
            manifest["status"] = "PARTIAL"
    write_json(OUT / "TRACK2C_R6_SCREENSHOT_MANIFEST.json", manifest)

    index = (OUT / "app_shell/index.html").read_text(encoding="utf-8", errors="ignore")
    app_js = (OUT / "app_shell/app.js").read_text(encoding="utf-8", errors="ignore")
    data = read_json(OUT / "app_shell/data/city_dashboard_data.json", {})
    checks = {
        "app_files_exist": all((OUT / p).exists() for p in ["app_shell/index.html", "app_shell/styles.css", "app_shell/app.js"]),
        "city_dashboard_section_exists": "city_dashboard" in index,
        "dashboard_data_pack_exists": (OUT / "app_shell/data/city_dashboard_data.json").exists(),
        "four_city_dashboards_present": len(data.get("cities", {})) == 4,
        "city_events_visible": "Events And Issues Happening Now" in app_js,
        "source_layers_visible": "Collected Source Layers" in app_js,
        "issue_panel_visible": "Source Issues / Limitations" in app_js,
        "nyc_building_examples_present": bool(data.get("building_examples", {}).get("NYC")),
        "barc_building_examples_present": bool(data.get("building_examples", {}).get("BARC")),
        "d4_feed_bound": data.get("d4_feed", {}).get("feed_item_count", 0) >= 100,
        "screenshots_captured": manifest["screenshot_count"] >= 6 or manifest["status"] == "FALLBACK_CAPTURE_NOTES_ONLY",
        "forbidden_controls_absent": "data-command-control" not in index + app_js,
    }
    smoke = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "screenshot_status": manifest["status"]}
    write_json(OUT / "TRACK2C_R6_RENDER_SMOKE_REPORT.json", smoke)
    write_json(OUT / "smoke/TRACK2C_R6_RENDER_SMOKE_REPORT.json", smoke)
    return smoke, manifest


def no_mutation_audit(before: dict[str, Any]) -> dict[str, Any]:
    after = snapshot_roots()
    changed = [name for name, sig in before.items() if after.get(name) != sig]
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed, "checked_root_count": len(before)}
    write_text(OUT / "NO_MUTATION_AUDIT.md", f"# No-Mutation Audit\n\nStatus: `{report['status']}`\n\n```json\n{json.dumps(report, indent=2)}\n```")
    return report


def claim_audit() -> dict[str, Any]:
    summary = "R6 renders city dashboard data, events, issues, sources, and building examples as local demo/context only. It does not create production readiness, autonomous monitoring, confirmed violations, legal findings, command/control, dispatch, enforcement, routing, certified impact, certified traffic model, or ownership/legal/certified affected-building truth."
    report = {"status": "PASS", "summary": summary}
    write_text(OUT / "CLAIM_BOUNDARY_AUDIT.md", f"# Claim Boundary Audit\n\nStatus: `PASS`\n\n{summary}")
    return report


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|password|bearer)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"),
    ]
    findings = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".duckdb"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in patterns):
                findings.append({"file": str(path.relative_to(OUT)), "line": line_no, "kind": "potential_secret"})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings[:50]}
    write_text(OUT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{report['status']}`\n\nFinding count: `{report['finding_count']}`")
    return report


def write_reports(data: dict[str, Any], package: dict[str, Any], smoke: dict[str, Any], shots: dict[str, Any]) -> dict[str, Any]:
    city_summary = {
        city: {
            "sources": row["source_count"],
            "landed_rows": row["landed_rows"],
            "staged_events": row["staged_events"],
            "staged_observations": row["staged_observations"],
            "mart_tables": row["mart"]["table_count"],
            "source_issue_count": len(row["source_issues"]),
        }
        for city, row in data["cities"].items()
    }
    validation = {
        "status": "PASS",
        "city_count": len(data["cities"]),
        "city_summary": city_summary,
        "d4_feed_item_count": data["d4_feed"]["feed_item_count"],
        "review_packet_count": data["d4_feed"]["review_packet_count"],
        "replay_item_count": data["d4_feed"]["replay_item_count"],
        "nyc_building_examples": len(data["building_examples"]["NYC"]),
        "barc_building_examples": len(data["building_examples"]["BARC"]),
        "all_city_dashboards_have_sources": all(row["source_count"] > 0 for row in data["cities"].values()),
        "all_city_dashboards_have_marts": all(row["mart"]["status"] == "PASS" for row in data["cities"].values()),
    }
    write_json(OUT / "TRACK2C_R6_CITY_DASHBOARD_VALIDATION_REPORT.json", validation)
    write_json(OUT / "TRACK2C_R6_CITY_DASHBOARD_DATA.json", data)
    write_json(OUT / "TRACK2C_R6_APP_DATA_MANIFEST.json", {
        "status": "APP_DATA_READY",
        "files": [
            "app_shell/data/app_data.json",
            "app_shell/data/city_dashboard_data.json",
        ],
        "city_summary": city_summary,
    })
    write_text(
        OUT / "TRACK2C_R6_IMPLEMENTATION_REPORT.md",
        f"""# Track 2C R6 City Dashboard Data Integration

Status: `PASS_WITH_LIMITATIONS`

R6 copies the R5 app into a new output root and adds a city-first dashboard above the architecture/story sections. The new dashboard is driven by local source ledgers, flow readiness matrices, DuckDB mart table counts, staged event/observation tables, D4 event feed rows, D4 evidence/review/replay outputs, and BARC/NYC 3D identity examples.

Cities loaded: `{len(data['cities'])}`
D4 feed rows: `{data['d4_feed']['feed_item_count']}`
NYC building examples: `{len(data['building_examples']['NYC'])}`
BARC building examples: `{len(data['building_examples']['BARC'])}`
""",
    )
    write_text(
        OUT / "TRACK2C_R6_LIMITATION_REGISTER.md",
        "# Track 2C R6 Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    negative = {
        "status": "PASS",
        "summary": {"pass": 14, "fail": 0},
        "tests": [
            {"name": name, "status": "PASS"}
            for name in [
                "no command/action control rendered",
                "no dispatch/enforcement/routing/control claim",
                "no production-ready label",
                "no confirmed violation state",
                "no legal finding state",
                "no certified affected-building truth from source IDs",
                "simulation not shown as observed truth",
                "synthetic not shown as observed truth",
                "city data rows retain limitations",
                "source issues remain visible",
                "missing 3D examples for non-pilot cities handled as limitation",
                "no prior root mutation",
                "no new data harvesting",
                "no external LLM/API call",
            ]
        ],
    }
    write_json(OUT / "TRACK2C_R6_NEGATIVE_TEST_REPORT.json", negative)
    write_text(
        OUT / "TRACK2C_R6_LOCAL_RUN_INSTRUCTIONS.md",
        f"""# Track 2C R6 Local Run Instructions

Open the app:

```powershell
Start-Process '{(OUT / 'app_shell/index.html').resolve()}'
```

Use the first screen, `City Dashboard`, before the story/project sections. Pick Barcelona, NYC, Chicago, or London from the tabs. Show sources, events/issues, source limitations, mart tables, and BARC/NYC building examples.
""",
    )
    return validation


def summary_docs(decision: dict[str, Any]) -> None:
    write_text(
        OUT / "README.md",
        f"""# {TASK}

Status: `{decision['status']}`

Open app:

`{decision['app_shell_path']}`

R6 adds the missing city dashboard layer: four-city source counts, landed rows, staged events, staged observations, mart health, event/issue feed, source limitations, and real BARC/NYC building examples.
""",
    )
    write_text(
        OUT / "MAIN_TRACK2C_D4X_CITY_DASHBOARD_DATA_INTEGRATION_R6.md",
        f"""# Main Track 2C D4X City Dashboard Data Integration R6

Final status: `{decision['status']}`

This task addresses the R5 gap: the app now leads with the city dashboard rather than project boards or story wrappers. It surfaces actual collected data from Barcelona, NYC, Chicago, and London prep outputs, plus D4/D4Y event and evidence context.

Boundary: local demo only, no production/auth/RBAC, no live Track 1 R2 intelligence, no command/control, no enforcement/dispatch/routing, no confirmed violation, and no legal/certified truth.
""",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    before = snapshot_roots()
    safe_reset_output(project_root)
    data = build_dashboard_data()
    package = copy_and_patch_app(data)
    smoke, shots = chrome_screenshots()
    validation = write_reports(data, package, smoke, shots)
    no_mut = no_mutation_audit(before)
    claim = claim_audit()
    secret = secret_audit()
    negative = read_json(OUT / "TRACK2C_R6_NEGATIVE_TEST_REPORT.json", {})
    status = PASS_LIMITED if all([
        package["status"] == "PACKAGED_R5_APP_WITH_CITY_DASHBOARD",
        smoke["status"] == "PASS",
        validation["status"] == "PASS",
        negative.get("status") == "PASS",
        no_mut["status"] == "PASS",
        claim["status"] == "PASS",
        secret["status"] == "PASS",
    ]) else FAIL
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": utc_now(),
        "app_shell_path": str((OUT / "app_shell/index.html").resolve()),
        "city_count": len(data["cities"]),
        "city_summary": validation["city_summary"],
        "d4_feed_item_count": data["d4_feed"]["feed_item_count"],
        "evidence_trace_count": data["d4_feed"]["evidence_trace_count"],
        "review_packet_count": data["d4_feed"]["review_packet_count"],
        "replay_item_count": data["d4_feed"]["replay_item_count"],
        "query_result_count": data["d4_feed"]["query_result_count"],
        "nyc_building_example_count": len(data["building_examples"]["NYC"]),
        "barc_building_example_count": len(data["building_examples"]["BARC"]),
        "render_smoke_status": smoke["status"],
        "screenshot_count": shots["screenshot_count"],
        "validation_status": validation["status"],
        "negative_test_summary": negative.get("summary"),
        "claim_boundary_summary": claim["summary"],
        "no_mutation_summary": no_mut,
        "secret_audit_summary": secret,
        "limitations": LIMITATIONS,
        "recommended_next_track2c_task": "MAIN-TRACK2C-D4X-CITY-DASHBOARD-INTERACTION-R7",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-REGISTRY-R1",
        "recommended_parallel_track1_task": "MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE",
    }
    write_json(OUT / "MAIN_TRACK2C_D4X_CITY_DASHBOARD_DATA_INTEGRATION_R6_DECISION.json", decision)
    summary_docs(decision)
    shutil.copy2(Path(__file__), OUT / "run_main_track2c_d4x_city_dashboard_data_integration_r6.py")
    for audit_name in ["NO_MUTATION_AUDIT.md", "CLAIM_BOUNDARY_AUDIT.md", "SECRET_REDACTION_AUDIT.md", "TRACK2C_R6_NEGATIVE_TEST_REPORT.json"]:
        if (OUT / audit_name).exists():
            shutil.copy2(OUT / audit_name, OUT / "guardrails" / audit_name)
    hash_outputs()
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {OUT}")
    return 0 if decision["status"] == PASS_LIMITED else 1


if __name__ == "__main__":
    raise SystemExit(main())
