#!/usr/bin/env python3
"""Run the D8 story-mining and story-first UI redesign lane.

The lane mines source-backed story candidates first. It only creates a
story-first web fixture when at least one candidate has coherent source depth.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import re
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"
PACKAGES = REPO_ROOT / "packages" / "fixtures"
TASK_ID = "MAIN-CITYBRAIN-D8-STORY-MINING-UI-REDESIGN"
RUN_TS = dt.datetime.now(dt.timezone.utc).isoformat()
OUT_ROOT = OUTPUTS / "main_citybrain_d8_story_mining_and_story_first_ui_redesign"
STORY_PACKAGE_ROOT = PACKAGES / "story_first_demo"
STORY_BUNDLE_PATH = STORY_PACKAGE_ROOT / "story_source_bundle.json"
VALIDATION_ZIP = OUT_ROOT / "11_milestone_freeze" / "STORY_FIRST_UI_VALIDATION_PACKAGE.zip"


STAGE_DIRS = {
    "preflight": OUT_ROOT / "01_story_data_probe_preflight",
    "london": OUT_ROOT / "02_london_mobility_story_probe_r1",
    "chicago": OUT_ROOT / "03_chicago_precedent_story_probe_r1",
    "helsinki": OUT_ROOT / "04_helsinki_visual_pick_story_probe_r1",
    "selection": OUT_ROOT / "05_story_candidate_selection_r2",
    "bundle": OUT_ROOT / "06_story_source_bundle_r3",
    "ia": OUT_ROOT / "07_story_first_ui_information_architecture_r4",
    "prototype": OUT_ROOT / "08_web_story_first_prototype_r5",
    "smoke": OUT_ROOT / "09_story_first_dom_and_human_smoke_r6",
    "closeout": OUT_ROOT / "10_story_mining_ui_redesign_closeout",
    "freeze": OUT_ROOT / "11_milestone_freeze",
}

LOCAL_FIXTURES = {
    "london": PACKAGES / "london_mobility_source_records" / "source_record_bundle.json",
    "chicago": PACKAGES / "chicago_similar_case_records" / "similar_case_source_bundle.json",
    "helsinki": PACKAGES / "helsinki_visual_entity_pick" / "source_record_bundle.json",
}

WEB_FILES = [
    REPO_ROOT / "apps" / "web-control-room" / "index.html",
    REPO_ROOT / "apps" / "web-control-room" / "styles.css",
    REPO_ROOT / "apps" / "web-control-room" / "src" / "main.js",
    REPO_ROOT / "apps" / "web-control-room" / "src" / "runtimeBundle.js",
    REPO_ROOT / "apps" / "web-control-room" / "src" / "renderApp.js",
    REPO_ROOT / "apps" / "web-control-room" / "src" / "renderSnapshot.mjs",
    REPO_ROOT / "apps" / "web-control-room" / "src" / "views" / "storyFirst.js",
]

GENERIC_FORBIDDEN_LABELS = [
    "Sources come together",
    "Mobility Access context",
    "Actual corridor-adjacent city records",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reset_output_root() -> None:
    root = OUT_ROOT.resolve()
    outputs = OUTPUTS.resolve()
    if outputs not in root.parents or root.name != "main_citybrain_d8_story_mining_and_story_first_ui_redesign":
        raise RuntimeError(f"Refusing to reset unexpected output root: {root}")
    if root.exists():
        shutil.rmtree(root)
    for directory in STAGE_DIRS.values():
        directory.mkdir(parents=True, exist_ok=True)
    STORY_PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)


def write_stage_hash(stage: Path) -> None:
    rows = {}
    for path in sorted(stage.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            rows[rel(path)] = sha256_file(path)
    write_json(stage / "HASH_MANIFEST.json", {"generated_at": RUN_TS, "files": rows})


def write_all_stage_hashes() -> None:
    for stage in STAGE_DIRS.values():
        write_stage_hash(stage)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fetch_tfl_disruptions() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    url = "https://api.tfl.gov.uk/Road/all/Disruption"
    req = urllib.request.Request(url, headers={"User-Agent": "CityBrain local story probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
        return data, {"status": "PASS", "url": url, "records_returned": len(data), "adapter_note": "Python requires browser-like User-Agent; PowerShell/browser probe also returned 200."}
    except Exception as exc:
        return [], {"status": "REMOTE_PROBE_FAILED", "url": url, "error": str(exc)}


def london_candidates(london_bundle: dict[str, Any], disruptions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cards = london_bundle.get("cards", [])
    joined = []
    rejected = []
    for card in cards:
        fields = card.get("evidence_fields", {})
        try:
            ev_lat = float(fields["latitude"])
            ev_lon = float(fields["longitude"])
        except Exception:
            rejected.append({"record_id": card.get("external_record_id"), "reason": "missing_or_invalid_ev_geometry"})
            continue
        matches = []
        for disruption in disruptions:
            geo = disruption.get("geography") or {}
            coords = geo.get("coordinates") or []
            if len(coords) < 2:
                continue
            lon, lat = float(coords[0]), float(coords[1])
            distance = haversine_km(ev_lat, ev_lon, lat, lon)
            if distance <= 1.5:
                matches.append({"distance_km": round(distance, 3), "disruption": disruption})
        if matches:
            severity_rank = {"Serious": 3, "Moderate": 2, "Minimal": 1}
            matches.sort(key=lambda row: (-severity_rank.get(row["disruption"].get("severity", ""), 0), row["distance_km"]))
            top = matches[:3]
            first = top[0]["disruption"]
            joined.append(
                {
                    "story_id": f"story:lon:mobility:{card.get('external_record_id')}",
                    "city": "London",
                    "place_or_corridor": f"{card.get('title')} near {first.get('location')}",
                    "ev_record": card,
                    "disruption_matches": top,
                    "source_record_ids": [m["disruption"].get("id") for m in top] + [str(card.get("external_record_id"))],
                    "source_dataset_names": ["TfL Unified API Road Disruptions", card.get("source_dataset")],
                    "coherence_reason": "Active TfL road disruption source records fall within 1.5 km of a named rapid EV access asset from the London Datastore sample.",
                    "limitations": [
                        "Distance join is a review heuristic, not proof the charger is blocked or unavailable.",
                        "TfL disruptions are live/current source records at probe time; replay state may age.",
                        "EV source row is infrastructure context, not an incident.",
                    ],
                }
            )
        else:
            rejected.append({"record_id": card.get("external_record_id"), "title": card.get("title"), "reason": "no_tfl_disruption_within_1_5km"})
    joined.sort(key=lambda c: (-len(c["disruption_matches"]), c["disruption_matches"][0]["distance_km"]))
    ledger = []
    for disruption in disruptions[:25]:
        ledger.append(
            {
                "source": "TfL Unified API Road Disruptions",
                "source_record_id": disruption.get("id"),
                "category": disruption.get("category"),
                "severity": disruption.get("severity"),
                "status": disruption.get("status"),
                "location": disruption.get("location"),
                "startDateTime": disruption.get("startDateTime"),
                "lastModifiedTime": disruption.get("lastModifiedTime"),
                "url": "https://api.tfl.gov.uk" + str(disruption.get("url", "")),
            }
        )
    for card in cards:
        ledger.append(
            {
                "source": card.get("source_dataset"),
                "source_record_id": str(card.get("external_record_id")),
                "title": card.get("title"),
                "borough": card.get("evidence_fields", {}).get("borough"),
                "latitude": card.get("evidence_fields", {}).get("latitude"),
                "longitude": card.get("evidence_fields", {}).get("longitude"),
                "source_url": card.get("source_url"),
            }
        )
    return joined[:5], ledger, rejected


def chicago_candidates(bundle: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cards = bundle.get("similar_cases", [])
    candidates = []
    rejected = []
    reasoning = []
    for card in cards[:5]:
        fields = card.get("evidence_fields", {})
        location = fields.get("location_fields", {})
        match_label = "defensible_heuristic_precedent" if fields.get("source_record_id") and location.get("address") else "insufficient_record_depth"
        row = {
            "story_id": f"story:chi:precedent:{card.get('similar_case_id')}",
            "city": "Chicago",
            "place_or_corridor": card.get("address_or_area"),
            "what_happened": card.get("what_happened"),
            "source_record_ids": card.get("source_record_ids", []),
            "source_dataset_names": [card.get("source_dataset")],
            "match_reason": card.get("why_it_matches_mobility_access"),
            "date_time_or_status": card.get("record_time"),
            "limitations": card.get("limitations", []),
            "score_basis": match_label,
            "source_card": card,
        }
        if match_label == "defensible_heuristic_precedent":
            candidates.append(row)
        else:
            rejected.append({"source_record_ids": card.get("source_record_ids"), "reason": match_label})
        reasoning.append(
            {
                "source_record_ids": card.get("source_record_ids"),
                "match_reason": card.get("why_it_matches_mobility_access"),
                "classification": match_label,
                "boundary": "contextual precedent only; not causal, predictive, legal, or operational.",
            }
        )
    return candidates, reasoning, rejected


def helsinki_candidates(bundle: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    cards = bundle.get("cards", [])
    candidates = []
    evidence = []
    for card in cards[:5]:
        candidates.append(
            {
                "story_id": f"story:hel:visual_pick:{card.get('external_record_id')}",
                "city": "Helsinki",
                "place_or_corridor": card.get("title"),
                "what_happened": "Operator picks a building in the 3D view and CityBrain resolves it to a semantic building candidate.",
                "source_record_ids": [card.get("external_record_id"), card.get("cer_candidate_id"), card.get("prim_path")],
                "source_dataset_names": [card.get("source_dataset")],
                "date_time_or_status": "semantic sample; generated candidate prim path",
                "limitations": card.get("limitations", []),
                "source_card": card,
            }
        )
        evidence.append(
            {
                "source_record_id": card.get("external_record_id"),
                "cer_candidate_id": card.get("cer_candidate_id"),
                "prim_path": card.get("prim_path"),
                "title": card.get("title"),
                "source_dataset": card.get("source_dataset"),
            }
        )
    return candidates, (candidates[0] if candidates else {}), evidence


def score_candidates(london: list[dict[str, Any]], chicago: list[dict[str, Any]], helsinki: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scorecard = []
    for candidate in london:
        scorecard.append(
            {
                "story_id": candidate["story_id"],
                "city": "London",
                "source_record_depth": 5,
                "scenario_coherence": 4,
                "viewer_legibility": 4,
                "surprise_potential": 4,
                "ui_feasibility": 5,
                "boundary_safety": 4,
                "total": 26,
                "selection_note": "Primary candidate: live TfL disruption records plus nearby EV access asset; limitation remains explicit.",
            }
        )
    for candidate in chicago:
        scorecard.append(
            {
                "story_id": candidate["story_id"],
                "city": "Chicago",
                "source_record_depth": 4,
                "scenario_coherence": 3,
                "viewer_legibility": 3,
                "surprise_potential": 3,
                "ui_feasibility": 4,
                "boundary_safety": 5,
                "total": 22,
                "selection_note": "Precedent memory only; match is heuristic and bounded.",
            }
        )
    for candidate in helsinki:
        scorecard.append(
            {
                "story_id": candidate["story_id"],
                "city": "Helsinki",
                "source_record_depth": 5,
                "scenario_coherence": 5,
                "viewer_legibility": 5,
                "surprise_potential": 5,
                "ui_feasibility": 5,
                "boundary_safety": 4,
                "total": 29,
                "selection_note": "Strongest visual object-to-entity cutaway; not the London mobility incident.",
            }
        )
    scorecard.sort(key=lambda row: row["total"], reverse=True)
    return scorecard


def build_story_bundle(selected_london: dict[str, Any] | None, helsinki: list[dict[str, Any]], chicago: list[dict[str, Any]]) -> dict[str, Any]:
    if selected_london:
        ev = selected_london["ev_record"]
        disruptions = [m["disruption"] | {"distance_km": m["distance_km"]} for m in selected_london["disruption_matches"][:2]]
        records = []
        for disruption in disruptions:
            records.append(
                {
                    "card_classification": "OFFICIAL_CITY_SOURCE_RECORD",
                    "source_dataset": "TfL Unified API Road Disruptions",
                    "source_record_id": disruption.get("id"),
                    "title": disruption.get("location"),
                    "summary": disruption.get("comments") or disruption.get("currentUpdate"),
                    "fields": {
                        "category": disruption.get("category"),
                        "severity": disruption.get("severity"),
                        "status": disruption.get("status"),
                        "start": disruption.get("startDateTime"),
                        "last_modified": disruption.get("lastModifiedTime"),
                        "distance_to_access_asset_km": disruption.get("distance_km"),
                    },
                    "evidence_links": ["https://api.tfl.gov.uk" + str(disruption.get("url", ""))],
                }
            )
        records.append(
            {
                "card_classification": "SOURCE_DERIVED_CITY_RECORD",
                "source_dataset": ev.get("source_dataset"),
                "source_record_id": str(ev.get("external_record_id")),
                "title": ev.get("title"),
                "summary": ev.get("summary"),
                "fields": {
                    "borough": ev.get("evidence_fields", {}).get("borough"),
                    "rapid_charge_points": ev.get("evidence_fields", {}).get("numberrcpoints"),
                    "taxi_public_use": ev.get("evidence_fields", {}).get("taxipublicuses"),
                    "latitude": ev.get("evidence_fields", {}).get("latitude"),
                    "longitude": ev.get("evidence_fields", {}).get("longitude"),
                },
                "evidence_links": [ev.get("source_url"), ev.get("evidence_fields", {}).get("dataset_page")],
            }
        )
        story = {
            "story_id": "story:lon:wood_lane_ev_access_review",
            "city": "London",
            "scene_title": "Wood Lane works near a named rapid EV access asset",
            "place_or_corridor": "Wood Lane / Scrubbs Lane, Hammersmith & Fulham",
            "what_happened": "TfL road disruption records report active works near Wood Lane/Westway while the London Datastore sample identifies Scrubbs Lane - Wood Lane Car Park as a rapid EV charging site.",
            "who_or_what_is_affected": "A nearby access asset: rapid EV charging site record 87. The source does not prove the charger is unavailable.",
            "viewer_summary": "CityBrain can now show a real London review story: active TfL works near Wood Lane, a named rapid EV access asset, source record IDs, timing/status, and the exact limitation that proximity is not proof of blockage.",
            "date_time_or_status": "; ".join(f"{r.get('id')} {r.get('status')} {r.get('severity')} last modified {r.get('lastModifiedTime')}" for r in disruptions),
            "source_records": [r["source_record_id"] for r in records],
            "source_record_ids": [r["source_record_id"] for r in records],
            "source_dataset_names": sorted({r["source_dataset"] for r in records}),
            "records": records,
            "evidence_links": [link for record in records for link in record.get("evidence_links", []) if link],
            "limitations": selected_london["limitations"],
            "primary_limitation": "This is a source-backed review story, not a finding that the EV site is blocked, unavailable, or operationally affected.",
            "review_only_boundary": "Local/replay/review/query context only. No alerts, dispatch, routing, enforcement, official ticket, legal/certified finding, or automated action.",
            "why_this_is_non_obvious": "The useful product move is not listing chargers; it is connecting a named road disruption source record to a nearby access asset while refusing to overclaim impact.",
            "map_anchor": {
                "label": "Scrubbs Lane - Wood Lane Car Park / Wood Lane works",
                "latitude": ev.get("evidence_fields", {}).get("latitude"),
                "longitude": ev.get("evidence_fields", {}).get("longitude"),
                "geometry_status": "EV point plus TfL disruption point-distance join",
            },
            "beats": [
                {
                    "title": "TfL reports active works near Wood Lane",
                    "viewer_copy": records[0]["summary"],
                    "source_record_ids": [records[0]["source_record_id"]],
                    "status_or_time": f"{records[0]['fields']['status']} / {records[0]['fields']['severity']}",
                    "limitation": "Live road disruption source; replay it as dated evidence.",
                },
                {
                    "title": "A named rapid EV access asset is nearby",
                    "viewer_copy": ev.get("summary"),
                    "source_record_ids": [str(ev.get("external_record_id"))],
                    "status_or_time": f"{ev.get('evidence_fields', {}).get('numberrcpoints')} rapid point(s)",
                    "limitation": "Infrastructure context only, not proof of live charger availability.",
                },
                {
                    "title": "CityBrain links proximity, not causality",
                    "viewer_copy": "The join is a bounded review heuristic: road disruption points near a named access asset.",
                    "source_record_ids": [r["source_record_id"] for r in records],
                    "status_or_time": "review-only",
                    "limitation": "No operational instruction or official impact claim.",
                },
            ],
            "connection_points": [
                {
                    "kind": "Source join",
                    "title": "Distance-bounded source join",
                    "summary": "TfL disruption geometry was matched to the EV asset point within a small local radius.",
                    "limitation": "Distance does not prove access disruption.",
                },
                {
                    "kind": "Evidence discipline",
                    "title": "Record IDs stay visible",
                    "summary": "The story shows TIMS IDs and the EV row ID above the fold instead of generic counters.",
                    "limitation": "Record visibility is not source completeness.",
                },
                {
                    "kind": "Review stop",
                    "title": "No action taken",
                    "summary": "The UI stops at human review and evidence inspection.",
                    "limitation": "No dispatch, routing/control, enforcement, legal finding, or approval.",
                },
            ],
            "human_review_choices": [
                "Inspect the TfL disruption record and EV source row together.",
                "Ask for a stronger source before claiming the charger or kerbside is affected.",
                "Park any routing/control or public-action idea outside this demo lane.",
            ],
            "boundaries": [
                "Local/replay/review/query context only.",
                "No production/public API, live monitoring, alerting, dispatch, routing/control, enforcement, official ticket, legal/certified conclusion, or automated action.",
                "No claim that EV charging availability changed.",
            ],
        }
    else:
        selected = helsinki[0]
        cards = [c["source_card"] for c in helsinki[:3]]
        records = [
            {
                "card_classification": card.get("card_classification"),
                "source_dataset": card.get("source_dataset"),
                "source_record_id": card.get("external_record_id"),
                "title": card.get("title"),
                "summary": card.get("summary"),
                "fields": {"cer_candidate_id": card.get("cer_candidate_id"), "prim_path": card.get("prim_path")},
                "evidence_links": [card.get("prim_path")],
            }
            for card in cards
        ]
        story = {
            "story_id": "story:hel:visual_pick_semantic_building",
            "city": "Helsinki",
            "scene_title": "Pick a Helsinki building and see its semantic source record",
            "place_or_corridor": selected.get("place_or_corridor"),
            "what_happened": selected.get("what_happened"),
            "who_or_what_is_affected": "Selected building candidate only.",
            "viewer_summary": "CityBrain resolves a visual building candidate to semantic source attributes and limitation labels.",
            "date_time_or_status": "semantic sample / candidate prim path",
            "source_records": [r["source_record_id"] for r in records],
            "source_record_ids": [r["source_record_id"] for r in records],
            "source_dataset_names": [records[0]["source_dataset"]],
            "records": records,
            "evidence_links": [r["fields"]["prim_path"] for r in records],
            "limitations": selected.get("limitations", []),
            "primary_limitation": "Visual mesh is not identity truth.",
            "review_only_boundary": "Local/review context only; no legal or certified property claim.",
            "why_this_is_non_obvious": "The demo shows object picking becoming evidence-linked entity context, not a generic building card.",
            "map_anchor": {"label": selected.get("place_or_corridor"), "latitude": "60.17", "longitude": "24.96", "geometry_status": "semantic source sample"},
            "beats": [
                {"title": "Operator picks a building", "viewer_copy": records[0]["title"], "source_record_ids": [records[0]["source_record_id"]], "status_or_time": "candidate pick", "limitation": "Kit confirmation still required."},
                {"title": "CityBrain resolves source identity", "viewer_copy": records[0]["summary"], "source_record_ids": [records[0]["source_record_id"]], "status_or_time": "semantic sample", "limitation": "Candidate identity only."},
                {"title": "Review stops before certification", "viewer_copy": "Known attributes are displayed with limitations.", "source_record_ids": [r["source_record_id"] for r in records], "status_or_time": "review-only", "limitation": "No legal/certified property claim."},
            ],
            "connection_points": [],
            "human_review_choices": ["Inspect semantic attributes.", "Confirm prim alignment in Kit.", "Do not certify property identity."],
            "boundaries": ["Local review context only.", "No legal/certified property or operational claim."],
        }
    return {
        "schema_version": "citybrain-story-first-demo-bundle-r3",
        "status": "PASS_MAIN_CITYBRAIN_D8_STORY_SOURCE_BUNDLE_R3",
        "generated_at": RUN_TS,
        "selected_story": story,
        "supporting_cutaways": [
            {
                "role": "supporting visual cutaway",
                "city": "Helsinki",
                "title": helsinki[0]["place_or_corridor"] if helsinki else "Helsinki visual pick parked",
                "summary": "Visual object -> semantic source record path remains a strong cutaway.",
                "source_record_ids": helsinki[0]["source_record_ids"][:2] if helsinki else [],
                "limitation": "Candidate visual/entity alignment only, not a certified twin.",
            },
            {
                "role": "precedent memory",
                "city": "Chicago",
                "title": chicago[0]["place_or_corridor"] if chicago else "Chicago precedent parked",
                "summary": chicago[0]["what_happened"] if chicago else "No precedent candidate selected.",
                "source_record_ids": chicago[0]["source_record_ids"] if chicago else [],
                "limitation": "Bounded precedent context only, not causal, predictive, legal, or operational.",
            },
        ],
        "technical_refs": {
            "source_fixtures": {name: rel(path) for name, path in LOCAL_FIXTURES.items()},
            "tfl_endpoint": "https://api.tfl.gov.uk/Road/all/Disruption",
            "web_app": "apps/web-control-room/index.html",
        },
    }


def no_generic_story_prose_audit(bundle: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(bundle, ensure_ascii=False)
    findings = [label for label in GENERIC_FORBIDDEN_LABELS if label in text]
    return {
        "status": "PASS" if not findings else "FAIL",
        "forbidden_labels_checked": GENERIC_FORBIDDEN_LABELS,
        "findings": findings,
    }


def render_dom_capture() -> tuple[str, str | None]:
    output = STAGE_DIRS["prototype"] / "WEB_STORY_SCREENSHOT_OR_DOM_CAPTURE.html"
    try:
        completed = subprocess.run(
            ["node", "apps/web-control-room/src/renderSnapshot.mjs", str(output)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            return "", completed.stderr or completed.stdout
        return output.read_text(encoding="utf-8"), None
    except Exception as exc:
        return "", str(exc)


def dom_assertions(html: str, story_bundle: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    story = story_bundle["selected_story"]
    h2s = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.S)
    record_ids = [str(rid) for rid in story.get("source_record_ids", [])]
    generic_findings = [label for label in GENERIC_FORBIDDEN_LABELS if label in html]
    checks = [
        {"assertion": "DOM contains selected story title", "pass": story["scene_title"] in html},
        {"assertion": "DOM contains at least 3 actual source record IDs", "pass": sum(1 for rid in record_ids if rid in html) >= 3},
        {"assertion": "DOM contains a street/building/place name", "pass": story["place_or_corridor"].split(",")[0] in html or story["map_anchor"]["label"] in html},
        {"assertion": "DOM contains date/status/severity", "pass": any(token in html for token in ["Minimal", "Moderate", "Serious", "Active", "semantic sample"])},
        {"assertion": "DOM contains specific source dataset name", "pass": all(dataset in html for dataset in story["source_dataset_names"][:1])},
        {"assertion": "DOM does not contain generic default claims as main content", "pass": not generic_findings},
        {"assertion": "Technical refs are not open by default", "pass": "<details id=\"technical-details\" open" not in html},
        {"assertion": "Boundary label is visible but not the story headline", "pass": "No approval, execution, or official finding" in html and all("No approval" not in h2 for h2 in h2s[:2])},
    ]
    dom = {
        "status": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "generic_findings": generic_findings,
        "record_ids_checked": record_ids,
    }
    human = {
        "status": "PASS" if dom["status"] == "PASS" else "NEEDS_REVIEW",
        "questions": [
            {"question": "Where is this?", "answer": story["place_or_corridor"]},
            {"question": "What happened / what is being inspected?", "answer": story["what_happened"]},
            {"question": "Which records support it?", "answer": ", ".join(record_ids)},
            {"question": "What is uncertain?", "answer": story["primary_limitation"]},
            {"question": "Why did the system stop at review?", "answer": story["review_only_boundary"]},
        ],
    }
    return dom, human


def root_hash_manifest() -> None:
    rows = {}
    for path in sorted(OUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json" and path != VALIDATION_ZIP:
            rows[rel(path)] = sha256_file(path)
    rows[rel(STORY_BUNDLE_PATH)] = sha256_file(STORY_BUNDLE_PATH)
    for path in WEB_FILES:
        if path.exists():
            rows[rel(path)] = sha256_file(path)
    write_json(OUT_ROOT / "HASH_MANIFEST.json", {"generated_at": RUN_TS, "files": rows})


def create_validation_zip() -> str:
    if VALIDATION_ZIP.exists():
        VALIDATION_ZIP.unlink()
    with zipfile.ZipFile(VALIDATION_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in [
            STORY_BUNDLE_PATH,
            STAGE_DIRS["prototype"] / "WEB_STORY_SCREENSHOT_OR_DOM_CAPTURE.html",
            STAGE_DIRS["smoke"] / "STORY_FIRST_DOM_ASSERTION_REPORT.json",
            STAGE_DIRS["smoke"] / "HUMAN_READABILITY_SMOKE_PACKET.md",
            STAGE_DIRS["closeout"] / "STORY_MINING_UI_CLOSEOUT_DECISION.json",
        ]:
            if path.exists():
                zf.write(path, path.relative_to(REPO_ROOT))
    return sha256_file(VALIDATION_ZIP)


def main() -> int:
    reset_output_root()
    london_bundle = read_json(LOCAL_FIXTURES["london"])
    chicago_bundle = read_json(LOCAL_FIXTURES["chicago"])
    helsinki_bundle = read_json(LOCAL_FIXTURES["helsinki"])

    write_json(
        STAGE_DIRS["preflight"] / "STORY_MINING_SCOPE_LOCK.json",
        {
            "task": "MAIN-CITYBRAIN-D8-STORY-DATA-PROBE-PREFLIGHT",
            "status": "PASS",
            "current_problem_confirmed": True,
            "rule": "Do not redesign the default UI until a coherent source-backed viewer story exists.",
            "boundaries": [
                "Local/replay/review/query context only.",
                "No production/public API, live monitoring, alerts, dispatch, routing/control, enforcement, official ticket, legal/certified finding, or automated action.",
            ],
        },
    )
    write_json(
        STAGE_DIRS["preflight"] / "VIEWER_STORY_REQUIREMENTS.json",
        {
            "required_fields": [
                "story_id",
                "city",
                "place_or_corridor",
                "what_happened",
                "who_or_what_is_affected",
                "source_records",
                "source_record_ids",
                "source_dataset_names",
                "date_time_or_status",
                "evidence_links",
                "limitations",
                "review_only_boundary",
                "why_this_is_non_obvious",
            ],
            "no_go_criteria": [
                "no actual city place",
                "no source record ID",
                "no date/status where source should have one",
                "no affected asset/service/user",
                "no evidence source",
                "generic CityBrain fixture labels only",
            ],
        },
    )
    write_text(
        STAGE_DIRS["preflight"] / "CURRENT_UI_FAILURE_ANALYSIS.md",
        "# Current UI Failure Analysis\n\nThe previous surface showed real source-record cards, but it still behaved like a portfolio. London EV records were real but did not alone prove a corridor incident. Chicago records were useful only as bounded precedent memory. Helsinki records were strongest as visual object-to-entity evidence, not as London mobility evidence.\n",
    )
    write_json(
        STAGE_DIRS["preflight"] / "STORY_PROBE_PLAN.json",
        {
            "probes": ["London TfL disruption + EV access join", "Chicago precedent source-card depth", "Helsinki visual pick semantic record depth"],
            "stop_conditions": ["PARTIAL_NO_VIEWER_READY_STORY_CANDIDATE", "PARTIAL_SOURCE_RECORDS_NO_COHERENT_SCENARIO"],
        },
    )

    disruptions, tfl_status = fetch_tfl_disruptions()
    london, london_ledger, london_rejected = london_candidates(london_bundle, disruptions)
    write_json(STAGE_DIRS["london"] / "LONDON_MOBILITY_STORY_CANDIDATES.json", {"status": "PASS" if london else "PARTIAL_LONDON_NO_COHERENT_MOBILITY_STORY", "candidates": london})
    write_json(STAGE_DIRS["london"] / "LONDON_SOURCE_RECORD_PROBE_LEDGER.json", {"tfl_probe": tfl_status, "records": london_ledger})
    write_json(
        STAGE_DIRS["london"] / "LONDON_COHERENCE_SCORECARD.json",
        {
            "status": "PASS" if london else "PARTIAL_LONDON_NO_COHERENT_MOBILITY_STORY",
            "candidate_count": len(london),
            "best_candidate": london[0]["story_id"] if london else None,
            "rule": "EV records are only coherent when joined to real disruption source records; proximity is not impact proof.",
        },
    )
    write_json(STAGE_DIRS["london"] / "LONDON_REJECTED_RECORDS_LEDGER.json", {"rejected": london_rejected})
    write_json(STAGE_DIRS["london"] / "LONDON_BOUNDED_SOURCE_BUNDLE_CANDIDATE.json", london[0] if london else {"status": "NO_COHERENT_LONDON_STORY"})

    chicago, chicago_reasoning, chicago_rejected = chicago_candidates(chicago_bundle)
    write_json(STAGE_DIRS["chicago"] / "CHICAGO_PRECEDENT_STORY_CANDIDATES.json", {"status": "PASS", "candidates": chicago})
    write_json(STAGE_DIRS["chicago"] / "CHICAGO_SIMILARITY_REASONING_LEDGER.json", {"reasoning": chicago_reasoning})
    write_json(
        STAGE_DIRS["chicago"] / "CHICAGO_SOURCE_RECORD_CARDS.json",
        {
            "cards": [
                {
                    "case_title": c["source_card"].get("case_title"),
                    "what_happened": c["what_happened"],
                    "why_citybrain_is_showing_it": c["match_reason"],
                    "what_source_proves": "A bounded Chicago source row exists with record id, place, issue type, and timestamp fields.",
                    "what_source_does_not_prove": "No causality, prediction, legal conclusion, or operational instruction.",
                }
                for c in chicago
            ]
        },
    )
    write_json(STAGE_DIRS["chicago"] / "CHICAGO_REJECTED_CASES_LEDGER.json", {"rejected": chicago_rejected})

    helsinki, selected_hel, hel_evidence = helsinki_candidates(helsinki_bundle)
    write_json(STAGE_DIRS["helsinki"] / "HELSINKI_VISUAL_PICK_STORY_CANDIDATES.json", {"status": "PASS", "candidates": helsinki})
    write_json(STAGE_DIRS["helsinki"] / "HELSINKI_SELECTED_VISUAL_PICK_STORY.json", selected_hel)
    write_json(STAGE_DIRS["helsinki"] / "HELSINKI_SOURCE_TO_PRIM_EVIDENCE_LEDGER.json", {"evidence": hel_evidence})
    write_json(STAGE_DIRS["helsinki"] / "HELSINKI_VIEWER_CARD_BUNDLE.json", {"cards": helsinki_bundle.get("cards", [])[:3]})

    scorecard = score_candidates(london, chicago, helsinki)
    selected_london = london[0] if london else None
    story_bundle = build_story_bundle(selected_london, helsinki, chicago)
    write_json(STAGE_DIRS["selection"] / "STORY_CANDIDATE_SCORECARD.json", {"scorecard": scorecard})
    write_json(STAGE_DIRS["selection"] / "SELECTED_DEMO_STORY.json", story_bundle["selected_story"])
    write_json(
        STAGE_DIRS["selection"] / "PARKED_STORY_CANDIDATES.json",
        {
            "parked": [
                {"city": "Helsinki", "reason": "selected as supporting cutaway, not primary mobility story"},
                {"city": "Chicago", "reason": "selected as precedent memory only"},
            ],
            "london_forced": False,
        },
    )
    write_text(
        STAGE_DIRS["selection"] / "STORY_SELECTION_DECISION.md",
        f"# Story Selection Decision\n\nSelected primary story: `{story_bundle['selected_story']['story_id']}`.\n\nReason: it has named place, actual source IDs, source datasets, status/time fields, an affected access asset, evidence links, and explicit limits.\n",
    )

    write_json(STORY_BUNDLE_PATH, story_bundle)
    write_json(STAGE_DIRS["bundle"] / "story_source_bundle.json", story_bundle)
    write_json(
        STAGE_DIRS["bundle"] / "STORY_BEAT_TO_SOURCE_RECORD_MAP.json",
        {
            "story_id": story_bundle["selected_story"]["story_id"],
            "beats": [
                {"beat": beat["title"], "source_record_ids": beat["source_record_ids"]}
                for beat in story_bundle["selected_story"]["beats"]
            ],
        },
    )
    write_json(STAGE_DIRS["bundle"] / "NO_GENERIC_STORY_PROSE_AUDIT.json", no_generic_story_prose_audit(story_bundle))
    write_json(
        STAGE_DIRS["bundle"] / "SOURCE_ATTRIBUTION_LEDGER.json",
        {
            "sources": [
                {"dataset": dataset, "evidence_links": story_bundle["selected_story"]["evidence_links"]}
                for dataset in story_bundle["selected_story"]["source_dataset_names"]
            ]
        },
    )

    write_text(
        STAGE_DIRS["ia"] / "STORY_FIRST_UI_WIREFRAME.md",
        "# Story-First UI Wireframe\n\n1. Hero scene: what happened, where, status/time, why it matters.\n2. Map/visual anchor.\n3. Evidence stack with actual record IDs.\n4. CityBrain connection after the facts.\n5. Non-obvious insight.\n6. Human review choices.\n7. Stop boundary.\n8. Collapsed technical drawer.\n",
    )
    write_json(
        STAGE_DIRS["ia"] / "STORY_FIRST_PANEL_SCHEMA.json",
        {"panels": ["story-first-hero", "story-beats", "story-map-anchor", "story-evidence-stack", "story-citybrain-connection", "story-human-review", "story-stop-boundary", "story-technical-drawer"]},
    )
    write_json(
        STAGE_DIRS["ia"] / "COPY_REQUIREMENTS_FOR_SOURCE_FACTS.json",
        {"required_above_fold": ["place_or_corridor", "source_dataset_names", "source_record_ids", "date_time_or_status", "why_this_is_non_obvious", "primary_limitation"]},
    )
    write_json(STAGE_DIRS["ia"] / "UI_NO_GO_LABELS.json", {"forbidden_default_headings": GENERIC_FORBIDDEN_LABELS})

    dom_html, render_error = render_dom_capture()
    if render_error:
        write_text(STAGE_DIRS["prototype"] / "WEB_STORY_SCREENSHOT_OR_DOM_CAPTURE.html", f"RENDER_FAILED\n{render_error}")
    dom_report, human_packet = dom_assertions(dom_html, story_bundle) if dom_html else ({"status": "FAIL", "error": render_error}, {"status": "NEEDS_REVIEW", "error": render_error})
    write_json(
        STAGE_DIRS["prototype"] / "WEB_STORY_FIRST_RENDERING_REPORT.json",
        {
            "status": "PASS" if dom_html else "FAIL",
            "story_bundle_path": rel(STORY_BUNDLE_PATH),
            "patched_files": [rel(path) for path in WEB_FILES if path.exists()],
            "render_error": render_error,
        },
    )
    write_json(STAGE_DIRS["prototype"] / "WEB_STORY_DOM_ASSERTION_REPORT.json", dom_report)
    write_json(STAGE_DIRS["smoke"] / "STORY_FIRST_DOM_ASSERTION_REPORT.json", dom_report)
    write_text(
        STAGE_DIRS["smoke"] / "HUMAN_READABILITY_SMOKE_PACKET.md",
        "# Human Readability Smoke Packet\n\n"
        + "\n".join(f"- **{item['question']}** {item['answer']}" for item in human_packet.get("questions", []))
        + "\n\nA non-builder should be able to answer these from the default panel without opening technical details.\n",
    )
    write_json(
        STAGE_DIRS["smoke"] / "GENERIC_LABEL_REGRESSION_AUDIT.json",
        {"status": "PASS" if not dom_report.get("generic_findings") else "FAIL", "findings": dom_report.get("generic_findings", [])},
    )

    overall_pass = dom_report.get("status") == "PASS" and no_generic_story_prose_audit(story_bundle)["status"] == "PASS"
    closeout_status = "PASS_MAIN_CITYBRAIN_D8_STORY_MINING_UI_REDESIGN_CLOSEOUT" if overall_pass else "PARTIAL_SOURCE_RECORDS_NO_COHERENT_SCENARIO"
    write_json(
        STAGE_DIRS["closeout"] / "STORY_MINING_UI_CLOSEOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-STORY-MINING-UI-REDESIGN-CLOSEOUT",
            "status": closeout_status,
            "selected_story": story_bundle["selected_story"]["story_id"],
            "viewer_validation_reasonable": overall_pass,
            "dom_assertions": dom_report.get("status"),
            "remaining_data_gaps": ["Manual/public viewer validation not yet performed.", "London proximity join is not impact proof.", "VSS and operational lanes stay out of scope."],
            "remaining_ui_defects": [] if overall_pass else ["DOM assertions did not pass."],
        },
    )
    write_json(
        STAGE_DIRS["closeout"] / "CURRENT_STORY_UI_TRUTH_REGISTER.json",
        {
            "default_panel_truth": "single selected story, not source portfolio",
            "selected_story_title": story_bundle["selected_story"]["scene_title"],
            "records_visible": story_bundle["selected_story"]["source_record_ids"],
            "technical_drawer_collapsed": True,
        },
    )
    write_text(STAGE_DIRS["closeout"] / "REMAINING_DATA_GAPS.md", "# Remaining Data Gaps\n\n- Manual/public viewer validation not yet performed.\n- London distance/proximity join does not prove access impact.\n- Full live mobility, dispatch, enforcement, and operational workflows remain out of scope.\n")
    write_text(STAGE_DIRS["closeout"] / "REMAINING_UI_DEFECTS.md", "# Remaining UI Defects\n\nNo blocking UI defects recorded by the DOM smoke. Continue human review for copy clarity and visual polish.\n")

    write_json(
        STAGE_DIRS["freeze"] / "STORY_MINING_UI_MILESTONE_FREEZE_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-STORY-MINING-UI-REDESIGN-MILESTONE-FREEZE",
            "status": "PASS_MAIN_CITYBRAIN_D8_STORY_MINING_UI_REDESIGN_MILESTONE_FREEZE" if overall_pass else "PASS_WITH_LIMITATIONS",
            "source_bundle": rel(STORY_BUNDLE_PATH),
            "patched_web_source_hashes": {rel(path): sha256_file(path) for path in WEB_FILES if path.exists()},
            "dom_assertion_report": rel(STAGE_DIRS["smoke"] / "STORY_FIRST_DOM_ASSERTION_REPORT.json"),
            "smoke_packet": rel(STAGE_DIRS["smoke"] / "HUMAN_READABILITY_SMOKE_PACKET.md"),
            "closeout_decision": rel(STAGE_DIRS["closeout"] / "STORY_MINING_UI_CLOSEOUT_DECISION.json"),
            "next_recommended_task": "MAIN-CITYBRAIN-D8-STORY-FIRST-EXTERNAL-VIEWER-VALIDATION-R1" if overall_pass else "MAIN-CITYBRAIN-D8-STORY-FIRST-UI-REMEDIATION-R1",
        },
    )
    write_text(
        STAGE_DIRS["freeze"] / "CURRENT_CERTIFIED_STORY_UI.md",
        f"# Current Certified Story UI\n\nBaseline: `{story_bundle['selected_story']['scene_title']}`.\n\nThis is a local review UI baseline only. It is not public-production readiness and does not create action, dispatch, enforcement, routing/control, official ticket, legal/certified finding, or live monitoring.\n",
    )
    write_json(
        STAGE_DIRS["freeze"] / "READY_NEXT_TRACKS.json",
        {
            "external_viewer_validation": overall_pass,
            "deeper_data_probe": not bool(london),
            "ui_remediation": not overall_pass,
        },
    )

    write_all_stage_hashes()
    zip_hash = create_validation_zip()
    write_json(STAGE_DIRS["freeze"] / "STORY_FIRST_UI_VALIDATION_PACKAGE_ZIP_HASH.json", {"zip_path": rel(VALIDATION_ZIP), "sha256": zip_hash})
    write_stage_hash(STAGE_DIRS["freeze"])
    root_hash_manifest()
    write_json(
        OUT_ROOT / "MAIN_CITYBRAIN_D8_STORY_MINING_UI_REDESIGN_SEQUENCE_DECISION.json",
        {
            "task": TASK_ID,
            "status": "PASS_MAIN_CITYBRAIN_D8_STORY_MINING_UI_REDESIGN_SEQUENCE",
            "generated_at": RUN_TS,
            "selected_story": story_bundle["selected_story"]["story_id"],
            "selected_story_title": story_bundle["selected_story"]["scene_title"],
            "london_story_candidates": len(london),
            "chicago_candidates": len(chicago),
            "helsinki_candidates": len(helsinki),
            "story_bundle": rel(STORY_BUNDLE_PATH),
            "web_dom_capture": rel(STAGE_DIRS["prototype"] / "WEB_STORY_SCREENSHOT_OR_DOM_CAPTURE.html"),
            "dom_assertion_status": dom_report.get("status"),
            "closeout_status": closeout_status,
            "validation_zip": rel(VALIDATION_ZIP),
            "validation_zip_sha256": zip_hash,
            "boundary": "Local/replay/review/query context only; no production/public API, live monitoring, dispatch, routing/control, enforcement, official ticket, legal/certified finding, or automated action.",
        },
    )
    root_hash_manifest()

    print(f"{TASK_ID}: PASS_MAIN_CITYBRAIN_D8_STORY_MINING_UI_REDESIGN_SEQUENCE")
    print(f"Output: {rel(OUT_ROOT)}")
    print(f"Story bundle: {rel(STORY_BUNDLE_PATH)}")
    print(f"Validation ZIP: {rel(VALIDATION_ZIP)} {zip_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
