from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "F3-NYC-D8 Flow 3 Hero Package"
DEFAULT_OUTPUT_DIR = "outputs/f3_nyc_d8_flow3_hero_package"
DEFAULT_D7_DIR = "outputs/f3_nyc_d7_live_face_layer_route_map_trace"
DEFAULT_D6_DIR = "outputs/f3_nyc_d6_live_spark_nim_replay"
DEFAULT_D5_DIR = "outputs/f3_nyc_d5_governed_evidence_briefing"
DEFAULT_D4_DIR = "outputs/f3_nyc_d4_candidate_prioritization_review_routing"
DEFAULT_D3_DIR = "outputs/f3_nyc_d3_affected_asset_response_context"
DEFAULT_D2C_DIR = "outputs/f3_nyc_d2c_capped_working_set_refresh"
DEFAULT_D2_DIR = "outputs/f3_nyc_d2_fdny_incident_response_slice_ingest"
REMOTE_HOST = "txr-4070"
REMOTE_ROOT = "/srv/citybrain/current"
DEFAULT_BASE_URL = "http://192.168.1.48:8080"

BOUNDARY_LINES = [
    "D8 heroes are selected deterministically from D4/D5/D6/D7 evidence, not by memory or manual preference.",
    "Candidate tax-lot context is not a certified affected building.",
    "Candidate affected-asset context is not certified affected-asset truth.",
    "Operator-review routes are not emergency dispatch.",
    "D8 does not provide navigable routing.",
    "Firehouse/resource context is not dispatched-unit truth.",
    "Fire Dispatch is capped at 2,000,000 rows unless 11,819,520 rows are present.",
    "EMS Dispatch is capped at 3,000,000 rows unless 29,572,156 rows are present.",
    "D8 is a hero package over governed D5/D6/D7 evidence, not final full-source Flow 3 completion.",
    "D6 live Spark/NIM narration may narrate D5 evidence but may not compute counts or add facts.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\bcertified affected buildings?\s+(?:is|are|were|identified|confirmed)\b",
    r"\b(?:is|are|were|identified as|confirmed as)\s+(?:a\s+|the\s+)?certified affected buildings?\b",
    r"\bcertified affected assets?\s+(?:is|are|were|identified|confirmed)\b",
    r"\bemergency dispatch recommendations?\s+(?:is|are|were|ready|available|provided)\b",
    r"\bemergency dispatch route\s+(?:is|ready|available|provided)\b",
    r"\bnavigable (?:emergency )?routes?\s+(?:is|are|were|ready|available|provided)\b",
    r"\bfull fire dispatch source completion\s+(?:is|ready|available|provided|complete)\b",
    r"\bfull ems source completion\s+(?:is|ready|available|provided|complete)\b",
    r"\bhero selected by llm\b",
    r"\bhand-picked hero\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        if pd.isna(value) is True:
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            pass
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return value


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return [clean_value(row) for row in df.to_dict(orient="records")]


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "F3-NYC-D8-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "f3_nyc_d8" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["heroes", "reports", "face_payload", "_route_payload"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def input_snapshot(paths: list[Path]) -> dict[str, Any]:
    out = {}
    for root in paths:
        if not root.exists():
            out[str(root)] = {"exists": False}
            continue
        files = [root] if root.is_file() else [p for p in sorted(root.rglob("*")) if p.is_file() and p.suffix.lower() not in {".part", ".tmp"}]
        for path in files:
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            digest = None
            if stat.st_size < 250_000_000:
                try:
                    digest = sha256_file(path)
                except FileNotFoundError:
                    continue
            out[str(path)] = {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest}
    return out


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")[:80] or "unknown"


def d6_briefings(d6_dir: Path) -> dict[str, str]:
    rows = read_json(d6_dir / "samples" / "live_sample_nim_briefings.json", [])
    return {row.get("request_id"): row.get("content", "") for row in rows if isinstance(row, dict)}


def d6_grounding(d6_dir: Path) -> dict[str, dict[str, Any]]:
    report = read_json(d6_dir / "F3_NYC_D6_GROUNDING_REPORT.json", {})
    return {row.get("request_id"): row for row in report.get("results", []) if isinstance(row, dict)}


def load_inputs(d4_dir: Path, d5_dir: Path, d6_dir: Path, d7_dir: Path) -> dict[str, Any]:
    canonical = d4_dir / "canonical"
    return {
        "candidates": pd.read_parquet(canonical / "f3_nyc_d4_prioritized_incident_candidates.parquet"),
        "routes": pd.read_parquet(canonical / "f3_nyc_d4_operator_review_routes.parquet"),
        "stops": pd.read_parquet(canonical / "f3_nyc_d4_route_stops.parquet"),
        "edges": pd.read_parquet(canonical / "f3_nyc_d4_review_plan_edges.parquet"),
        "d5_candidate": read_json(d5_dir / "evidence" / "evidence_bundle_candidate_profile.json", {}),
        "d5_route": read_json(d5_dir / "evidence" / "evidence_bundle_route_profile.json", {}),
        "d5_trace": read_json(d5_dir / "evidence" / "evidence_bundle_route_stop_trace.json", {}),
        "d5_limitations": read_json(d5_dir / "evidence" / "evidence_bundle_source_limitations.json", {}),
        "d6_briefings": d6_briefings(d6_dir),
        "d6_grounding": d6_grounding(d6_dir),
        "d7_status": read_json(d7_dir / "F3_NYC_D7_HARNESS_REPORT.json", {}),
        "d7_face_status": read_json(d7_dir / "face_payload" / "flow3_status.json", {}),
    }


def has_value(row: pd.Series, key: str) -> bool:
    value = row.get(key)
    if value is None:
        return False
    try:
        return not bool(pd.isna(value))
    except Exception:
        return True


def bundle_query(bundle: dict[str, Any]) -> dict[str, Any]:
    query = bundle.get("query", {})
    return query if isinstance(query, dict) else {}


def bundle_route_id(bundle: dict[str, Any]) -> str:
    query = bundle_query(bundle)
    return str(query.get("route_id") or query.get("subject") or query.get("subject_id") or "")


def bundle_subject(bundle: dict[str, Any]) -> str:
    query = bundle_query(bundle)
    return str(query.get("subject") or query.get("subject_id") or query.get("route_id") or bundle.get("bundle_id", ""))


def bundle_sequence(bundle: dict[str, Any]) -> int | None:
    value = bundle_query(bundle).get("sequence")
    try:
        return int(value)
    except Exception:
        return None


def bundle_mentions(bundle: dict[str, Any], subject: str) -> bool:
    if not subject:
        return False
    return subject in json.dumps(bundle, ensure_ascii=False)


def select_heroes(data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates: pd.DataFrame = data["candidates"]
    routes: pd.DataFrame = data["routes"]
    stops: pd.DataFrame = data["stops"]
    grounding = data["d6_grounding"]
    briefings = data["d6_briefings"]

    h1_pool = candidates[
        (candidates["location_status"] == "latlon_exact")
        & candidates["primary_candidate_asset_id"].notna()
        & candidates["nearest_resource_id"].notna()
        & candidates["operator_review_priority_score"].notna()
    ].copy()
    h1_pool = h1_pool.sort_values(["operator_review_priority_score", "source_id"], ascending=[False, True])
    h1 = h1_pool.iloc[0]

    d5_candidate_subject = bundle_subject(data["d5_candidate"])
    d5_route_subject = bundle_subject(data["d5_route"])
    d5_route_id = bundle_route_id(data["d5_route"])
    d5_trace_subject = bundle_subject(data["d5_trace"])
    d5_trace_route_id = bundle_route_id(data["d5_trace"])
    d5_trace_sequence = bundle_sequence(data["d5_trace"])
    exact_route_pool = routes[routes["route_id"] == d5_route_id].copy() if d5_route_id else routes.iloc[0:0].copy()
    if not exact_route_pool.empty and grounding.get("route", {}).get("status") == "PASS":
        route_pool = exact_route_pool
        h2_rule = "highest route with exact D5 route_profile and D6 route grounding"
        h2_preference_status = (
            "3+ stop route preference not applied because exact D5/D6 route grounding is only available for this route"
            if (routes["candidate_stop_count"] >= 3).any() and int(exact_route_pool.iloc[0].get("candidate_stop_count", 0)) < 3
            else "3+ stop route preference satisfied under exact D5/D6 grounding"
        )
    else:
        route_pool = routes[routes["candidate_stop_count"] >= 3].copy()
        h2_rule = "highest max_priority_score/mean_priority_score route with at least 3 stops; exact D5/D6 route subject unavailable"
        h2_preference_status = "fallback_without_exact_d5_d6_route_grounding"
        if route_pool.empty:
            route_pool = routes.copy()
            h2_rule = "no route had at least 3 stops, so highest max_priority_score/mean_priority_score route was selected"
            h2_preference_status = "fallback_no_3plus_route_and_no_exact_d5_d6_route_grounding"
    route_pool = route_pool.sort_values(["max_priority_score", "mean_priority_score", "candidate_stop_count", "route_id"], ascending=[False, False, False, True])
    h2 = route_pool.iloc[0]
    h2_stops = stops[stops["route_id"] == h2["route_id"]].sort_values(["sequence", "source_id"])

    stop_join = stops.merge(
        candidates[["source_id", "borough", "location_status", "asset_edge_status", "nearest_resource_id", "primary_candidate_asset_id"]],
        on="source_id",
        how="left",
        suffixes=("", "_candidate"),
    )
    h1_borough = h1.get("borough")
    exact_trace_pool = stop_join[
        (stop_join["route_id"] == d5_trace_route_id)
        & (stop_join["sequence"] == d5_trace_sequence)
    ].copy() if d5_trace_route_id and d5_trace_sequence is not None else stop_join.iloc[0:0].copy()
    diff_pool = stop_join[
        (stop_join["source_id"] != h1["source_id"])
        & stop_join["event_latitude"].notna()
        & stop_join["event_longitude"].notna()
        & stop_join["primary_candidate_asset_id"].notna()
        & stop_join["nearest_resource_id"].notna()
        & stop_join["borough"].notna()
        & (stop_join["borough"].astype(str).str.upper() != str(h1_borough).upper())
    ].copy()
    h3_rule = "highest-scoring route stop with official coordinates, candidate tax-lot context, resource context, and a different borough than Hero 1"
    h3_preference_status = "different-borough preference applied"
    if not exact_trace_pool.empty and grounding.get("stop_trace", {}).get("status") == "PASS":
        diff_pool = exact_trace_pool
        h3_rule = "route stop with exact D5 route_stop_trace and D6 stop_trace grounding"
        h3_preference_status = (
            "different-borough preference not applied because exact D5/D6 trace grounding is only available for this route stop"
            if str(exact_trace_pool.iloc[0].get("borough", "")).upper() == str(h1_borough).upper()
            else "different-borough preference satisfied under exact D5/D6 trace grounding"
        )
    elif diff_pool.empty:
        diff_pool = stop_join[
            (stop_join["source_id"] != h1["source_id"])
            & stop_join["event_latitude"].notna()
            & stop_join["event_longitude"].notna()
            & stop_join["primary_candidate_asset_id"].notna()
            & stop_join["nearest_resource_id"].notna()
        ].copy()
        h3_rule = "no different-borough complete stop was available, so highest complete non-Hero-1 stop was selected"
        h3_preference_status = "fallback_without_exact_d5_d6_trace_grounding"
    diff_pool = diff_pool.sort_values(["operator_review_priority_score", "sequence", "source_id"], ascending=[False, True, True])
    h3 = diff_pool.iloc[0]
    h3_candidate = candidates[candidates["source_id"] == h3["source_id"]]
    h3_route = routes[routes["route_id"] == h3["route_id"]]
    h3_selected_subject = d5_trace_subject if not exact_trace_pool.empty and d5_trace_subject else str(h3["source_id"])

    heroes = [
        {
            "hero_id": "hero_1_top_candidate_incident",
            "title": "Top Candidate Incident",
            "hero_type": "positive_operational",
            "selected_subject_id": clean_value(h1["source_id"]),
            "selector_rule": "highest operator_review_priority_score candidate with official lat/lon, candidate tax-lot context, and resource context",
            "why_selected": [
                f"operator_review_priority_score={clean_value(h1['operator_review_priority_score'])}",
                f"location_status={clean_value(h1['location_status'])}",
                f"primary_candidate_bbl={clean_value(h1['primary_candidate_bbl'])}",
                f"nearest_resource_id={clean_value(h1['nearest_resource_id'])}",
                "D5 candidate_profile EvidenceBundle exact subject matches selected top candidate." if str(h1["source_id"]) in json.dumps(data["d5_candidate"], ensure_ascii=False) else "D5 candidate_profile EvidenceBundle grounds the candidate profile query type.",
                f"D6 candidate grounding status={grounding.get('candidate', {}).get('status')}",
                f"D7 live face status={data['d7_status'].get('status')}",
            ],
            "story_steps": [
                "MVC crash with official lat/lon",
                "candidate MapPLUTO tax-lot context within 30m",
                "nearest firehouse/resource context",
                "D5 EvidenceBundle",
                "D6 live NIM briefing",
                "D7 face-layer candidate profile",
            ],
            "selection_record": clean_value(h1.to_dict()),
            "d5_evidence_bundle": data["d5_candidate"],
            "d6_live_nim_briefing": briefings.get("candidate", ""),
            "d6_grounding": grounding.get("candidate", {}),
            "d7_links": ["/flow3", "/api/flow3/candidates"],
            "limitations": BOUNDARY_LINES,
        },
        {
            "hero_id": "hero_2_top_operator_review_route",
            "title": "Top Operator Review Route",
            "hero_type": "positive_operational",
            "selected_subject_id": clean_value(h2["route_id"]),
            "selector_rule": h2_rule,
            "why_selected": [
                f"max_priority_score={clean_value(h2['max_priority_score'])}",
                f"mean_priority_score={clean_value(h2['mean_priority_score'])}",
                f"candidate_stop_count={clean_value(h2['candidate_stop_count'])}",
                h2_preference_status,
                f"exact_d5_route_id={d5_route_id}",
                f"D5 route_profile grounding subject/reference={d5_route_subject}",
                f"D6 route grounding status={grounding.get('route', {}).get('status')}",
                f"D7 live face status={data['d7_status'].get('status')}",
            ],
            "story_steps": [
                "prioritized candidate pool",
                "score-ordered operator-review route",
                "route stops",
                "route profile briefing",
                "live NIM narration",
                "face-layer route view",
            ],
            "selection_record": clean_value(h2.to_dict()),
            "route_stops": records(h2_stops),
            "d5_evidence_bundle": data["d5_route"],
            "d6_live_nim_briefing": briefings.get("route", ""),
            "d6_grounding": grounding.get("route", {}),
            "d7_links": ["/flow3", "/api/flow3/routes"],
            "limitations": BOUNDARY_LINES,
        },
        {
            "hero_id": "hero_3_route_stop_trace_borough_diverse",
            "title": "Route-Stop Trace / Borough-Diverse Candidate",
            "hero_type": "positive_operational",
            "selected_subject_id": clean_value(h3_selected_subject),
            "selector_rule": h3_rule,
            "why_selected": [
                f"operator_review_priority_score={clean_value(h3['operator_review_priority_score'])}",
                f"borough={clean_value(h3.get('borough'))}",
                f"hero_1_borough={clean_value(h1_borough)}",
                h3_preference_status,
                f"route_stop_event_id={clean_value(h3['source_id'])}",
                f"primary_candidate_bbl={clean_value(h3['primary_candidate_bbl'])}",
                f"nearest_resource_id={clean_value(h3['nearest_resource_id'])}",
                f"D5 route_stop_trace grounding subject/reference={d5_trace_subject}",
                f"D6 route-stop trace grounding status={grounding.get('stop_trace', {}).get('status')}",
                f"D7 live face status={data['d7_status'].get('status')}",
            ],
            "story_steps": [
                "one route stop",
                "why it was included",
                "candidate tax-lot context",
                "resource context",
                "limitations",
                "live NIM trace",
            ],
            "selection_record": clean_value(h3.to_dict()),
            "candidate_record": clean_value(h3_candidate.iloc[0].to_dict()) if not h3_candidate.empty else {},
            "route_record": clean_value(h3_route.iloc[0].to_dict()) if not h3_route.empty else {},
            "d5_evidence_bundle": data["d5_trace"],
            "d6_live_nim_briefing": briefings.get("stop_trace", ""),
            "d6_grounding": grounding.get("stop_trace", {}),
            "d7_links": ["/flow3", "/api/flow3/route-stop-trace"],
            "limitations": BOUNDARY_LINES,
        },
        {
            "hero_id": "hero_4_governance_negative_request",
            "title": "Governance Hero: Definitely Affected Buildings Request",
            "hero_type": "optional_governance",
            "selected_subject_id": "negative_affected_buildings",
            "selector_rule": "use D6 negative request sample for unsupported affected-building certainty claim",
            "why_selected": [
                "D6 negative request exists for: Which buildings were definitely affected?",
                f"D6 negative grounding status={grounding.get('negative_affected_buildings', {}).get('status')}",
                "Expected answer is rejected/bounded because D3 has candidate tax-lot context only.",
            ],
            "story_steps": [
                "operator asks for definitely affected buildings",
                "D6 rejects or bounds the request",
                "D8 shows candidate tax-lot context only",
                "no certified affected-building claim is made",
            ],
            "selection_record": {"request_id": "negative_affected_buildings", "answer_status": "rejected"},
            "d6_live_nim_briefing": briefings.get("negative_affected_buildings", ""),
            "d6_grounding": grounding.get("negative_affected_buildings", {}),
            "d7_links": ["/api/flow3/live-nim-briefings", "/api/flow3/source-limitations"],
            "limitations": BOUNDARY_LINES,
        },
    ]
    selector = {
        "status": "PASS",
        "selection_mode": "deterministic_ranked_selector",
        "manual_ids_supplied": False,
        "inputs": {
            "candidate_rows": int(len(candidates)),
            "route_rows": int(len(routes)),
            "route_stop_rows": int(len(stops)),
        },
        "preference_limitations": {
            "hero_2_route_preference_status": h2_preference_status,
            "hero_3_borough_diversity_status": h3_preference_status,
        },
        "selected_hero_ids": [hero["hero_id"] for hero in heroes],
        "selected_subject_ids": {hero["hero_id"]: hero["selected_subject_id"] for hero in heroes},
    }
    return heroes, selector


def hero_markdown(hero: dict[str, Any]) -> str:
    lines = [
        f"# {hero['title']}",
        "",
        f"Hero ID: `{hero['hero_id']}`",
        f"Subject: `{hero['selected_subject_id']}`",
        f"Type: `{hero['hero_type']}`",
        "",
        "## Why Selected",
        *[f"- {item}" for item in hero.get("why_selected", [])],
        "",
        "## Story",
        *[f"- {item}" for item in hero.get("story_steps", [])],
        "",
        "## Boundary",
        *[f"- {item}" for item in hero.get("limitations", [])],
    ]
    return "\n".join(lines) + "\n"


def write_hero_artifacts(output_dir: Path, heroes: list[dict[str, Any]], selector: dict[str, Any]) -> dict[str, Any]:
    hero_dir = output_dir / "heroes"
    index = {"status": "PASS", "selector": selector, "heroes": []}
    for hero in heroes:
        base = hero_dir / hero["hero_id"]
        write_json(base.with_suffix(".json"), hero)
        write_text(base.with_suffix(".md"), hero_markdown(hero))
        index["heroes"].append(
            {
                "hero_id": hero["hero_id"],
                "title": hero["title"],
                "hero_type": hero["hero_type"],
                "selected_subject_id": hero["selected_subject_id"],
                "json": f"heroes/{hero['hero_id']}.json",
                "markdown": f"heroes/{hero['hero_id']}.md",
            }
        )
    write_json(hero_dir / "hero_index.json", index)
    write_json(output_dir / "face_payload" / "flow3_heroes.json", index)
    return {"status": "PASS", "hero_count": len(heroes), "required_positive_hero_count": sum(1 for h in heroes if h["hero_type"] == "positive_operational"), "optional_hero_count": sum(1 for h in heroes if h["hero_type"] == "optional_governance")}


def heroes_html(hero_index: dict[str, Any]) -> str:
    cards = []
    for hero in hero_index["heroes"]:
        cards.append(
            "<article class=\"card\">"
            f"<p class=\"eyebrow\">{html.escape(hero['hero_type'])}</p>"
            f"<h2>{html.escape(hero['title'])}</h2>"
            f"<p><b>Subject:</b> {html.escape(str(hero['selected_subject_id']))}</p>"
            f"<a href=\"/api/flow3/heroes/{html.escape(hero['hero_id'])}\">Hero JSON</a>"
            "</article>"
        )
    boundary = "".join(f"<li>{html.escape(line)}</li>" for line in BOUNDARY_LINES)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NYC Flow 3 Hero Package</title>
  <style>
    body {{ margin:0; font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#f6f8fb; color:#182333; }}
    header {{ background:#17202f; color:#f7fbff; padding:22px; }}
    main {{ padding:18px; display:grid; gap:14px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; }}
    .card,.panel {{ background:white; border:1px solid #d9e1ea; border-radius:6px; padding:14px; }}
    .eyebrow {{ color:#617083; text-transform:uppercase; font-size:11px; letter-spacing:.08em; }}
    a {{ color:#1d5b9f; }}
  </style>
</head>
<body>
<header>
  <p class="eyebrow">F3-NYC-D8</p>
  <h1>Flow 3 Hero Package</h1>
  <p>Three deterministic operational heroes plus one optional governance hero, selected from D4/D5/D6/D7 evidence.</p>
  <nav><a href="/flow3">Flow 3 Face</a> | <a href="/api/flow3/heroes">Hero API</a></nav>
</header>
<main>
  <section class="grid">{''.join(cards)}</section>
  <section class="panel"><h2>Boundary</h2><ul>{boundary}</ul></section>
</main>
</body>
</html>
"""


def stage_route_payload(output_dir: Path, hero_index: dict[str, Any], heroes: list[dict[str, Any]]) -> dict[str, Any]:
    root = output_dir / "_route_payload"
    write_text(root / "flow3" / "heroes" / "index.html", heroes_html(hero_index))
    api = root / "api" / "flow3" / "heroes"
    write_json(root / "api" / "flow3" / "heroes.json", hero_index)
    write_text(api / "index.html", json.dumps(clean_value(hero_index), indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    for hero in heroes:
        write_json(api / hero["hero_id"], hero)
        write_json(api / f"{hero['hero_id']}.json", hero)
    return {
        "status": "PASS",
        "ui_routes": {"/flow3/heroes": "flow3/heroes/index.html"},
        "api_routes": {"/api/flow3/heroes.json": "api/flow3/heroes.json", **{f"/api/flow3/heroes/{h['hero_id']}": f"api/flow3/heroes/{h['hero_id']}" for h in heroes}},
    }


def run_cmd(args: list[str], timeout: int = 120) -> dict[str, Any]:
    rec = {"cmd": args, "status": "attempted"}
    try:
        proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        rec.update({"returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:], "status": "PASS" if proc.returncode == 0 else "FAIL"})
    except Exception as exc:
        rec.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    return rec


def publish_4070(output_dir: Path, publish: bool) -> dict[str, Any]:
    if not publish:
        return {"gate": "F3-NYC-D8-4070-PUBLISH", "status": "NOT_RUN"}
    root = output_dir / "_route_payload"
    mkdir = run_cmd(["ssh", REMOTE_HOST, f"mkdir -p {REMOTE_ROOT}/flow3 {REMOTE_ROOT}/api/flow3"], timeout=60)
    copy_heroes = run_cmd(["scp", "-r", str(root / "flow3" / "heroes"), f"{REMOTE_HOST}:{REMOTE_ROOT}/flow3/"], timeout=180)
    copy_api = run_cmd(["scp", "-r", str(root / "api" / "flow3" / "heroes"), f"{REMOTE_HOST}:{REMOTE_ROOT}/api/flow3/"], timeout=180)
    copy_api_json = run_cmd(["scp", str(root / "api" / "flow3" / "heroes.json"), f"{REMOTE_HOST}:{REMOTE_ROOT}/api/flow3/heroes.json"], timeout=120)
    chmod = run_cmd(["ssh", REMOTE_HOST, f"chmod -R a+rX {REMOTE_ROOT}/flow3/heroes {REMOTE_ROOT}/api/flow3/heroes {REMOTE_ROOT}/api/flow3/heroes.json"], timeout=60)
    after = run_cmd(["ssh", REMOTE_HOST, f"find {REMOTE_ROOT}/flow3/heroes {REMOTE_ROOT}/api/flow3/heroes -maxdepth 2 -type f | sort"], timeout=60)
    ok = all(row.get("status") == "PASS" for row in [mkdir, copy_heroes, copy_api, copy_api_json, chmod, after])
    return {"gate": "F3-NYC-D8-4070-PUBLISH", "status": "PASS" if ok else "FAIL", "remote_host": REMOTE_HOST, "remote_root": REMOTE_ROOT, "mkdir": mkdir, "copy_heroes": copy_heroes, "copy_api": copy_api, "copy_api_json": copy_api_json, "chmod": chmod, "after": after}


def http_get(url: str, timeout: int = 15) -> dict[str, Any]:
    rec = {"url": url, "status": "attempted"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CityBrain-F3-NYC-D8/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read(512000)
            text = data.decode("utf-8", errors="replace")
        rec.update({"http_status": response.status, "content_type": response.headers.get("content-type"), "bytes_read": len(data), "text_sample": text[:4000], "status": "PASS" if response.status == 200 else "FAIL"})
    except urllib.error.HTTPError as exc:
        rec.update({"http_status": exc.code, "status": "FAIL", "error": str(exc)})
    except Exception as exc:
        rec.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    return rec


def smoke_endpoints(base_url: str, heroes: list[dict[str, Any]], publish: dict[str, Any]) -> dict[str, Any]:
    if publish.get("status") != "PASS":
        return {"gate": "F3-NYC-D8-LIVE-ENDPOINT-SMOKE", "status": "FAIL", "reason": "publish_not_pass"}
    endpoints = ["/flow3/heroes", "/api/flow3/heroes.json"] + [f"/api/flow3/heroes/{hero['hero_id']}" for hero in heroes]
    attempts = [http_get(base_url.rstrip("/") + endpoint) for endpoint in endpoints]
    joined = "\n".join(row.get("text_sample", "") for row in attempts)
    checks = {
        "hero_1_present": "hero_1_top_candidate_incident" in joined,
        "hero_2_present": "hero_2_top_operator_review_route" in joined,
        "hero_3_present": "hero_3_route_stop_trace_borough_diverse" in joined,
        "optional_governance_present": "hero_4_governance_negative_request" in joined,
        "boundary_present": "not a certified affected building" in joined or "not certified affected building" in joined,
        "dispatch_boundary_present": "not emergency dispatch" in joined,
        "source_caps_present": "2,000,000" in joined and "29,572,156" in joined,
    }
    passed = [row for row in attempts if row.get("status") == "PASS"]
    return {"gate": "F3-NYC-D8-LIVE-ENDPOINT-SMOKE", "status": "PASS" if len(passed) == len(attempts) and all(checks.values()) else "FAIL", "endpoints": endpoints, "attempts": attempts, "live_endpoints_attempted": len(attempts), "live_endpoints_passed": len(passed), "checks": checks}


def grounding_report(heroes: list[dict[str, Any]]) -> dict[str, Any]:
    hmap = {hero["hero_id"]: hero for hero in heroes}
    h1 = hmap["hero_1_top_candidate_incident"]
    h2 = hmap["hero_2_top_operator_review_route"]
    h3 = hmap["hero_3_route_stop_trace_borough_diverse"]
    h4 = hmap["hero_4_governance_negative_request"]
    checks = {
        "minimum_three_positive_heroes": sum(1 for hero in heroes if hero["hero_type"] == "positive_operational") >= 3,
        "h1_top_score": h1["selection_record"].get("operator_review_priority_score") == 93.076,
        "h1_d5_subject_aligned": bundle_mentions(h1.get("d5_evidence_bundle", {}), h1["selected_subject_id"]),
        "h1_d6_grounding_pass": h1.get("d6_grounding", {}).get("status") == "PASS",
        "h2_d5_subject_aligned": bundle_mentions(h2.get("d5_evidence_bundle", {}), h2["selected_subject_id"]),
        "h2_d6_grounding_pass": h2.get("d6_grounding", {}).get("status") == "PASS",
        "h2_three_stop_preference_accounted": "3+ stop route preference" in " ".join(h2.get("why_selected", [])),
        "h3_d5_trace_subject_aligned": bundle_subject(h3.get("d5_evidence_bundle", {})) == h3["selected_subject_id"],
        "h3_d5_event_grounded": bundle_mentions(h3.get("d5_evidence_bundle", {}), h3.get("candidate_record", {}).get("source_id", "")),
        "h3_d6_grounding_pass": h3.get("d6_grounding", {}).get("status") == "PASS",
        "h3_borough_preference_accounted": "different-borough preference" in " ".join(h3.get("why_selected", [])),
        "h4_rejected": h4.get("d6_grounding", {}).get("answer_status") == "rejected",
    }
    return {"gate": "F3-NYC-D8-GROUNDING", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def limitation_report(output_dir: Path) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".md", ".html"})
    missing = [line for line in BOUNDARY_LINES if line not in text]
    return {"gate": "F3-NYC-D8-LIMITATION-CARRY-FORWARD", "status": "PASS" if not missing else "FAIL", "missing": missing, "required": BOUNDARY_LINES}


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".md", ".html", ".py"}).lower()
    findings = []
    for pattern in FORBIDDEN_POSITIVE_PATTERNS:
        if re.search(pattern, text):
            findings.append(pattern)
    return {"gate": "F3-NYC-D8-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "forbidden_positive_claims_found": findings}


def write_docs(output_dir: Path, status: str) -> None:
    write_text(
        output_dir / "README.md",
        "# F3-NYC-D8 Flow 3 Hero Package\n\n"
        f"Status: `{status}`\n\n"
        "D8 emits three required deterministic operational heroes and one optional governance hero.\n\n"
        "## Boundary\n"
        + "\n".join(f"- {line}" for line in BOUNDARY_LINES)
        + "\n",
    )
    write_text(
        output_dir / "F3_NYC_D8_ADAPTER_HANDOVER.md",
        "# F3-NYC-D8 Adapter Handover\n\n"
        "Serve `/flow3/heroes` and `/api/flow3/heroes*` from the generated static payloads. D8 does not replace the D7 face; it adds hero packaging on top.\n\n"
        + "\n".join(f"- {line}" for line in BOUNDARY_LINES)
        + "\n",
    )


def run_f3_nyc_d8_gate(
    d7_dir: str,
    d6_dir: str,
    d5_dir: str,
    d4_dir: str,
    d3_dir: str,
    d2c_dir: str,
    d2_dir: str,
    output_dir: str,
    base_url: str = DEFAULT_BASE_URL,
    publish_4070: bool = True,
) -> dict:
    d7_path = Path(d7_dir)
    d6_path = Path(d6_dir)
    d5_path = Path(d5_dir)
    d4_path = Path(d4_dir)
    d3_path = Path(d3_dir)
    d2c_path = Path(d2c_dir)
    d2_path = Path(d2_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)
    watch = [d7_path, d6_path, d5_path, d4_path, d3_path, d2c_path, d2_path]
    before = input_snapshot(watch)

    precond = {
        "d7_status": read_json(d7_path / "F3_NYC_D7_HARNESS_REPORT.json", {}).get("status"),
        "d6_status": read_json(d6_path / "F3_NYC_D6_HARNESS_REPORT.json", {}).get("status"),
        "d5_status": read_json(d5_path / "F3_NYC_D5_HARNESS_REPORT.json", {}).get("status"),
        "d4_status": read_json(d4_path / "F3_NYC_D4_HARNESS_REPORT.json", {}).get("status"),
        "d3_status": read_json(d3_path / "F3_NYC_D3_HARNESS_REPORT.json", {}).get("status"),
        "d2c_status": read_json(d2c_path / "F3_NYC_D2C_HARNESS_REPORT.json", {}).get("status"),
        "d2_status": read_json(d2_path / "F3_NYC_D2_HARNESS_REPORT.json", {}).get("status"),
    }
    precond["status"] = "PASS" if precond == {
        "d7_status": "PASS",
        "d6_status": "PASS",
        "d5_status": "PASS_WITH_GOVERNED_DETERMINISTIC_BRIEFINGS",
        "d4_status": "PASS_WITH_OPERATOR_REVIEW_ROUTING_LIMITATION",
        "d3_status": "PASS_WITH_LOCATION_CONFIDENCE_TIERS",
        "d2c_status": "PASS_WITH_CAPPED_WORKING_SET",
        "d2_status": "PASS_WITH_BOUNDED_SAMPLE",
    } else "FAIL"
    data = load_inputs(d4_path, d5_path, d6_path, d7_path)
    heroes, selector = select_heroes(data)
    package = write_hero_artifacts(output_path, heroes, selector)
    hero_index = read_json(output_path / "heroes" / "hero_index.json", {})
    route_stage = stage_route_payload(output_path, hero_index, heroes)
    publish = globals()["publish_4070"](output_path, publish_4070)
    smoke = smoke_endpoints(base_url, heroes, publish)
    grounding = grounding_report(heroes)
    write_docs(output_path, "PENDING")
    limits = limitation_report(output_path)
    overclaim = no_overclaim_report(output_path)
    after = input_snapshot(watch)
    no_mutation = {"gate": "F3-NYC-D8-NO-MUTATION", "status": "PASS" if before == after else "FAIL", "watched_paths": [str(path) for path in watch]}

    write_json(output_path / "F3_NYC_D8_INPUT_INVENTORY.json", {"preconditions": precond, "inputs": [str(path) for path in watch]})
    write_json(output_path / "F3_NYC_D8_SELECTOR_REPORT.json", selector)
    write_json(output_path / "F3_NYC_D8_HERO_PACKAGE_REPORT.json", package)
    write_json(output_path / "F3_NYC_D8_ROUTE_REPORT.json", route_stage)
    write_json(output_path / "F3_NYC_D8_ENDPOINT_SMOKE_REPORT.json", smoke)
    write_json(output_path / "F3_NYC_D8_GROUNDING_REPORT.json", grounding)
    write_json(output_path / "F3_NYC_D8_LIMITATION_CARRY_FORWARD_REPORT.json", limits)
    write_json(output_path / "F3_NYC_D8_NO_OVERCLAIM_REPORT.json", overclaim)
    write_json(output_path / "reports" / "selected_hero_ids.json", selector)
    write_json(output_path / "reports" / "endpoint_status.json", smoke)
    write_json(output_path / "reports" / "route_config_before_after.json", publish)
    write_json(output_path / "reports" / "no_mutation.json", no_mutation)
    write_json(output_path / "reports" / "rollback_instructions.json", {"status": "PASS", "commands": [f"ssh {REMOTE_HOST} 'rm -rf {REMOTE_ROOT}/flow3/heroes {REMOTE_ROOT}/api/flow3/heroes {REMOTE_ROOT}/api/flow3/heroes.json'"]})

    gates = {
        "F3-NYC-D8-PRECOND": precond["status"],
        "F3-NYC-D8-SELECTOR": selector["status"],
        "F3-NYC-D8-HERO-PACKAGE": package["status"],
        "F3-NYC-D8-4070-PUBLISH": publish["status"],
        "F3-NYC-D8-LIVE-ENDPOINT-SMOKE": smoke["status"],
        "F3-NYC-D8-GROUNDING": grounding["status"],
        "F3-NYC-D8-LIMITATION-CARRY-FORWARD": limits["status"],
        "F3-NYC-D8-NO-OVERCLAIM": overclaim["status"],
        "F3-NYC-D8-NO-MUTATION": no_mutation["status"],
    }
    status = "PASS" if all(v == "PASS" for v in gates.values()) else "FAIL"
    write_docs(output_path, status)
    hashes = write_hashes(output_path)
    gates["F3-NYC-D8-HASHES"] = hashes["status"]
    status = "PASS" if all(v == "PASS" for v in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "gates": gates,
        "preconditions": precond,
        "selector": selector,
        "hero_package": package,
        "publish_4070": publish,
        "endpoint_smoke": smoke,
        "grounding": grounding,
        "limitation_carry_forward": limits,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
        "output": str(output_path),
        "hashes": {"sha256s_path": "SHA256SUMS.json", "note": "SHA256SUMS.json covers all generated outputs except itself."},
    }
    write_json(output_path / "F3_NYC_D8_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--d7-dir", default=DEFAULT_D7_DIR)
    parser.add_argument("--d6-dir", default=DEFAULT_D6_DIR)
    parser.add_argument("--d5-dir", default=DEFAULT_D5_DIR)
    parser.add_argument("--d4-dir", default=DEFAULT_D4_DIR)
    parser.add_argument("--d3-dir", default=DEFAULT_D3_DIR)
    parser.add_argument("--d2c-dir", default=DEFAULT_D2C_DIR)
    parser.add_argument("--d2-dir", default=DEFAULT_D2_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--publish-4070", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d8_gate(
        d7_dir=args.d7_dir,
        d6_dir=args.d6_dir,
        d5_dir=args.d5_dir,
        d4_dir=args.d4_dir,
        d3_dir=args.d3_dir,
        d2c_dir=args.d2c_dir,
        d2_dir=args.d2_dir,
        output_dir=args.output_dir,
        base_url=args.base_url,
        publish_4070=args.publish_4070,
    )
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Heroes emitted: {report['hero_package']['hero_count']}")
    print(f"Positive heroes: {report['hero_package']['required_positive_hero_count']}")
    print(f"4070 publish: {report['publish_4070']['status']}")
    print(f"Live endpoints passed: {report['endpoint_smoke'].get('live_endpoints_passed', 0)} / {report['endpoint_smoke'].get('live_endpoints_attempted', 0)}")
    print(f"Grounding: {report['grounding']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
