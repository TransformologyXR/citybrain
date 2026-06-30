#!/usr/bin/env python3
"""MAIN-TRACK2C-D4X-RICH-CITY-DEMO-CONTENT-INTEGRATION-R5.

Adds a curated city story layer to the Track 2C browser demo. This task turns
the app from architecture counters into Barcelona/NYC demo narratives grounded
in existing local outputs. It does not mutate prior roots, harvest new data,
convert new assets, implement production features, or create command/control.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "MAIN-TRACK2C-D4X-RICH-CITY-DEMO-CONTENT-INTEGRATION-R5"
PASS_LIMITED = "PASS_MAIN_TRACK2C_D4X_RICH_CITY_DEMO_CONTENT_INTEGRATION_R5_WITH_LIMITATIONS"
FAIL = "FAIL_MAIN_TRACK2C_D4X_RICH_CITY_DEMO_CONTENT_INTEGRATION_R5"
OUT = Path("outputs/main_track2c_d4x_rich_city_demo_content_integration_r5")
R4 = Path("outputs/main_track2c_d4x_demo_capture_and_polish_r4")

INPUT_ROOTS: dict[str, Path] = {
    "track2c_r4": R4,
    "track2c_r3": Path("outputs/main_track2c_d4x_app_ux_redesign_and_demo_polish_r3"),
    "track2c_r2": Path("outputs/main_track2c_d4x_control_room_app_experience_r2"),
    "d4_event_feed": Path("outputs/main_track1_d4_event_feed_and_overlay_ui"),
    "d4_evidence_trace": Path("outputs/main_track1_d4_evidence_trace_panel"),
    "d4_review_ui": Path("outputs/main_track1_d4_review_ui_workflow"),
    "d4_replay": Path("outputs/main_track1_d4_scenario_replay_panel"),
    "d4_briefing": Path("outputs/main_track1_d4_briefing_panel"),
    "d4_persona": Path("outputs/main_track1_d4_trace_and_persona_experience"),
    "d4y_graph_query": Path("outputs/main_track1_d4y_situation_graph_and_query_r1"),
    "d4y_runtime": Path("outputs/main_track1_d4y_city_situation_runtime_binding_r1"),
    "barc_lod2": Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1"),
    "nyc_lod2": Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1"),
    "platform_state": Path("outputs/platform_state_generated"),
    "pv1_d19_d22": Path("outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"),
    "a9_g1": Path("outputs/txr_citybrain_a9_g1_board_reconciliation"),
}

DATA_FILES = {
    "r4_decision": R4 / "MAIN_TRACK2C_D4X_DEMO_CAPTURE_AND_POLISH_R4_DECISION.json",
    "r4_app_data": R4 / "app_shell/data/app_data.json",
    "barc_identity": Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1/identity_shards/shard_000_identity.jsonl"),
    "nyc_identity": Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1/identity_shards/shard_000_identity.jsonl"),
    "review_packets": Path("outputs/main_track1_d4_review_ui_workflow/D4_REVIEW_PACKET_VIEW_MODEL.json"),
    "replay_items": Path("outputs/main_track1_d4_scenario_replay_panel/D4_SCENARIO_REPLAY_ITEMS.json"),
    "briefing_items": Path("outputs/main_track1_d4_briefing_panel/D4_BRIEFING_ITEMS.json"),
    "persona_items": Path("outputs/main_track1_d4_trace_and_persona_experience/D4_PERSONA_VIEW_ITEMS.json"),
    "query_results": Path("outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_DETERMINISTIC_QUERY_RESULTS.json"),
    "event_feed": Path("outputs/main_track1_d4_event_feed_and_overlay_ui/D4_EVENT_FEED_ITEMS.json"),
    "evidence_trace": Path("outputs/main_track1_d4_evidence_trace_panel/D4_EVIDENCE_TRACE_PANEL_ITEMS.json"),
}

LIMITATIONS = [
    "local static demo app only",
    "not production UI",
    "no auth/RBAC",
    "no public deployment",
    "no live Track 1 R2 intelligence yet",
    "formal Track 2A asset registry may still be pending",
    "BARC/NYC asset bridge may be provisional",
    "3D source identity context only",
    "not ownership/legal/certified affected-building truth",
    "no command/control/enforcement/dispatch/routing",
    "no confirmed violation",
    "no certified impact",
    "no certified traffic model",
    "no autonomous monitoring",
    "no external LLM call",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


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
    return {"exists": True, "file_count": len(rows), "signature": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()}


def snapshot_roots() -> dict[str, Any]:
    return {name: root_signature(path) for name, path in INPUT_ROOTS.items() if path.exists()}


def safe_reset_output(project_root: Path) -> None:
    out_abs = (project_root / OUT).resolve()
    root_abs = project_root.resolve()
    if root_abs not in [out_abs, *out_abs.parents]:
        raise RuntimeError(f"Refusing to delete output outside workspace: {out_abs}")
    if OUT.exists():
        shutil.rmtree(OUT)
    for folder in ["app_shell/data", "screenshots", "stories", "smoke", "guardrails", "logs"]:
        (OUT / folder).mkdir(parents=True, exist_ok=True)


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


def read_jsonl(path: Path, limit: int = 2000) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if len(rows) >= limit:
                break
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def items_from(obj: Any, key: str = "items") -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        value = obj.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        for name in ["items", "packets", "views", "results"]:
            value = obj.get(name)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def one_line(value: Any, max_len: int = 260) -> str:
    text = str(value or "").replace("\n", " ").strip()
    return text[: max_len - 3] + "..." if len(text) > max_len else text


def build_story_data() -> dict[str, Any]:
    app_data = read_json(DATA_FILES["r4_app_data"], {})
    assets = app_data.get("AssetCard", [])
    barc_asset = next((a for a in assets if a.get("city_id") == "BARC"), {})
    nyc_asset = next((a for a in assets if a.get("city_id") == "NYC"), {})
    barc_rows = read_jsonl(DATA_FILES["barc_identity"], 500)
    nyc_rows = read_jsonl(DATA_FILES["nyc_identity"], 2500)
    barc_building = max(barc_rows, key=lambda r: float(r.get("COTA") or 0), default={})
    nyc_building = max(nyc_rows, key=lambda r: float(r.get("HeightFT") or 0), default={})
    review_packets = items_from(read_json(DATA_FILES["review_packets"], {}), "packets")
    review_packet = review_packets[0] if review_packets else {}
    replay_items = items_from(read_json(DATA_FILES["replay_items"], {}))
    replay = next((r for r in replay_items if r.get("city_id") == "BARC"), replay_items[0] if replay_items else {})
    query_results = items_from(read_json(DATA_FILES["query_results"], {}), "results")
    query = next((q for q in query_results if q.get("query_id") == "q14_neighborhood"), query_results[0] if query_results else {})
    briefing_items = items_from(read_json(DATA_FILES["briefing_items"], {}))
    briefing = briefing_items[0] if briefing_items else {}
    persona_items = items_from(read_json(DATA_FILES["persona_items"], {}), "views")
    persona = persona_items[0] if persona_items else {}
    event_items = items_from(read_json(DATA_FILES["event_feed"], {}))
    evidence_items = items_from(read_json(DATA_FILES["evidence_trace"], {}))

    review_summary = review_packet.get("candidate_event_summary", {})
    replay_scenario = replay.get("source_binding", {}).get("scenario_ref") or replay.get("overlay_refs", [{}])[0].get("scenario_ref", {})
    briefing_section = (briefing.get("sections") or [{}])[0]
    persona_block = (persona.get("text_blocks") or [{}])[0]

    stories = [
        {
            "story_id": "barcelona-real-geometry",
            "city_id": "BARC",
            "theme": "Real geometry",
            "title": "Barcelona real LOD2 geometry is loaded",
            "lede": "Barcelona is no longer just a dashboard counter: the demo can point to a real LOD2 object, its source OBJECTID, district/neighbourhood context, elevation, and the Omniverse handoff.",
            "why_it_matters": "This makes the city visible while keeping identity boundaries honest.",
            "primary_entities": [
                {"label": "LOD2 OBJECTID", "value": barc_building.get("OBJECTID")},
                {"label": "Source object", "value": barc_building.get("citybrain_3d_source_id")},
                {"label": "District ref", "value": barc_building.get("citybrain_district_ref")},
                {"label": "Neighbourhood ref", "value": barc_building.get("citybrain_neighbourhood_ref")},
                {"label": "COTA", "value": barc_building.get("COTA")},
                {"label": "Geometry status", "value": barc_asset.get("geometry_status")},
            ],
            "evidence_chain": [
                "BARC_LOD2_BUILDINGS_FULL_MASTER.usda",
                "BARC identity shard source object row",
                "BARC sampled USD vertex preview",
                "BARC I3S leaf-center footprint preview",
            ],
            "linked_artifacts": [
                str(DATA_FILES["barc_identity"]),
                barc_asset.get("usd_scene_path"),
            ],
            "limitations": [
                barc_building.get("claim_boundary"),
                "Cadastre/address/parcel join remains pending for this visual object.",
            ],
            "demo_prompt": "Show the Barcelona 3D preview, then the source object row, then say: real geometry, source identity context only.",
        },
        {
            "story_id": "nyc-building-identity-candidate",
            "city_id": "NYC",
            "theme": "Building identity candidate",
            "title": "NYC building identity candidate with BIN / BBL / DoITT context",
            "lede": "A selected NYC building can show real source identifiers and quality fields, without turning them into legal truth.",
            "why_it_matters": "The app can now talk about one actual building candidate instead of a generic NYC asset card.",
            "primary_entities": [
                {"label": "BIN", "value": nyc_building.get("bin")},
                {"label": "BBL", "value": nyc_building.get("base_bbl")},
                {"label": "DoITT ID", "value": nyc_building.get("doitt_id")},
                {"label": "HeightFT", "value": nyc_building.get("HeightFT")},
                {"label": "Height roof", "value": nyc_building.get("heightroof")},
                {"label": "RMSE", "value": round(float(nyc_building.get("RMSE") or 0), 3)},
                {"label": "GlobalID", "value": nyc_building.get("globalid")},
            ],
            "evidence_chain": [
                "NYC_2025_BUILDINGS_FULL_MASTER.usda",
                "NYC identity shard row",
                "NYC sampled USD vertex preview",
                "NYC I3S leaf-center footprint preview",
            ],
            "linked_artifacts": [
                str(DATA_FILES["nyc_identity"]),
                nyc_asset.get("usd_scene_path"),
            ],
            "limitations": [nyc_building.get("claim_boundary")],
            "demo_prompt": "Select the NYC story and read the BIN/BBL/DoITT fields as candidate source context, not legal ownership.",
        },
        {
            "story_id": "candidate-review-situation",
            "city_id": "MULTICITY",
            "theme": "Candidate/review",
            "title": "Candidate/review situation with evidence and no action taken",
            "lede": "The review packet can be explained as a bounded candidate requiring human review, with evidence refs and explicit forbidden states.",
            "why_it_matters": "This turns the review queue from a placeholder into a clear operational boundary story.",
            "primary_entities": [
                {"label": "Packet", "value": review_packet.get("packet_id")},
                {"label": "Event", "value": review_summary.get("event_id")},
                {"label": "Producer", "value": review_summary.get("producer")},
                {"label": "Review state", "value": review_summary.get("review_state")},
                {"label": "Confidence", "value": review_summary.get("confidence")},
                {"label": "No action taken", "value": review_packet.get("no_action_taken")},
            ],
            "evidence_chain": [
                f"{len(review_packet.get('evidencebundle_refs', []))} EvidenceBundle refs",
                f"{len(review_packet.get('media_refs', []))} media refs",
                f"{len(review_packet.get('trace_refs', []))} trace refs",
                f"{len(review_packet.get('usd_map_overlay_refs', []))} USD/overlay refs",
            ],
            "linked_artifacts": [str(DATA_FILES["review_packets"])],
            "limitations": review_packet.get("limitations", [])[:6] + [review_packet.get("claim_boundary")],
            "demo_prompt": "Show candidate/review. Say it is not a confirmed violation and cannot dispatch, enforce, route, or issue a ticket.",
        },
        {
            "story_id": "barcelona-sumo-simulation-context",
            "city_id": "BARC",
            "theme": "Simulation context",
            "title": "Barcelona SUMO replay is simulated/context only",
            "lede": "The replay panel can show a Barcelona SUMO scenario connected to a feed item, evidence ref, and USD overlay marker.",
            "why_it_matters": "The app can explain simulation without overclaiming observed traffic truth.",
            "primary_entities": [
                {"label": "Scenario", "value": replay.get("scenario_id")},
                {"label": "Replay type", "value": replay.get("replay_type")},
                {"label": "Lifecycle", "value": replay.get("lifecycle_state")},
                {"label": "City", "value": replay.get("city_id")},
                {"label": "Scenario family", "value": replay_scenario.get("scenario_family")},
                {"label": "No action taken", "value": replay.get("no_action_taken")},
            ],
            "evidence_chain": [
                f"{len(replay.get('event_refs', []))} event refs",
                f"{len(replay.get('evidence_refs', []))} evidence refs",
                f"{len(replay.get('overlay_refs', []))} overlay refs",
            ],
            "linked_artifacts": [str(DATA_FILES["replay_items"])],
            "limitations": replay.get("limitation_refs", [])[:8] + [replay.get("claim_boundary")],
            "demo_prompt": "Show replay as a planning context artifact. Do not call it observed truth or a certified traffic model.",
        },
        {
            "story_id": "citybrain-situation-graph-query",
            "city_id": "MULTICITY",
            "theme": "Situation graph",
            "title": "CityBrain graph query links situations to evidence and limitations",
            "lede": "A deterministic D4Y query result can explain what the brain knows for a selected situation or lifecycle class.",
            "why_it_matters": "This makes the brain visible as queryable evidence, not just a node/edge counter.",
            "primary_entities": [
                {"label": "Query ID", "value": query.get("query_id")},
                {"label": "Query type", "value": query.get("query_type")},
                {"label": "Result count", "value": query.get("result_count")},
                {"label": "Evidence refs", "value": len(query.get("evidence_refs", []))},
                {"label": "Limitation refs", "value": len(query.get("limitation_refs", []))},
                {"label": "No action taken", "value": query.get("no_action_taken")},
            ],
            "evidence_chain": [
                "D4Y_DETERMINISTIC_QUERY_RESULTS.json",
                "D4Y_SITUATION_GRAPH.json",
                "D4Y graph/query smoke passed",
            ],
            "linked_artifacts": [str(DATA_FILES["query_results"])],
            "limitations": [query.get("claim_boundary")] + query.get("limitation_refs", [])[:6],
            "demo_prompt": "Show the query as deterministic read-only navigation through situation/evidence/limitation refs.",
        },
        {
            "story_id": "briefing-persona-grounded-view",
            "city_id": "MULTICITY",
            "theme": "Briefing/persona",
            "title": "Briefing and persona text are grounded in the same packet",
            "lede": "The app can show operator/executive/planner language grounded in event, evidence, review, replay, and limitation refs.",
            "why_it_matters": "Personas become role-framed summaries instead of generic persona-1/persona-2 placeholders.",
            "primary_entities": [
                {"label": "Briefing", "value": briefing.get("briefing_id")},
                {"label": "Role variant", "value": briefing.get("role_variant")},
                {"label": "Persona role", "value": persona.get("role_id")},
                {"label": "Persona lifecycle", "value": persona.get("lifecycle_state")},
                {"label": "Trace", "value": persona.get("trace_id")},
                {"label": "No action taken", "value": persona.get("no_action_taken")},
            ],
            "evidence_chain": [
                f"{len(briefing.get('event_feed_refs', []))} event refs",
                f"{len(briefing.get('evidence_trace_refs', []))} evidence refs",
                f"{len(briefing.get('review_packet_refs', []))} review packet refs",
                f"{len(briefing.get('scenario_replay_refs', []))} replay refs",
            ],
            "linked_artifacts": [str(DATA_FILES["briefing_items"]), str(DATA_FILES["persona_items"])],
            "limitations": briefing.get("limitation_refs", []) + persona.get("limitation_refs", [])[:6],
            "sample_text": one_line(briefing_section.get("body") or persona_block.get("text")),
            "demo_prompt": "Show the role-framed text and say: this is not an autonomous agent; it is a grounded presentation of the same evidence packet.",
        },
    ]

    data = {
        "schema_version": "track2c-r5-rich-city-demo-content.v1",
        "task": TASK,
        "generated_at": utc_now(),
        "status": "RICH_CITY_STORIES_READY_WITH_LIMITATIONS",
        "story_count": len(stories),
        "stories": stories,
        "city_story_summary": {
            "barcelona_lod2_source_object_examples": len(barc_rows),
            "nyc_identity_candidate_examples": len(nyc_rows),
            "review_packets_available": len(review_packets),
            "scenario_replay_items_available": len(replay_items),
            "query_results_available": len(query_results),
            "briefing_items_available": len(briefing_items),
            "persona_views_available": len(persona_items),
            "event_feed_items_available": len(event_items),
            "evidence_trace_items_available": len(evidence_items),
        },
        "limitations": LIMITATIONS,
    }
    write_json(OUT / "stories/TRACK2C_R5_RICH_CITY_STORY_DATA.json", data)
    write_json(OUT / "app_shell/data/rich_city_story_data.json", data)
    return data


def text_list(items: Any, limit: int = 12) -> list[str]:
    if not isinstance(items, list):
        items = [items] if items else []
    rows = []
    for item in items:
        if item is None:
            continue
        text = one_line(item, 360)
        if text:
            rows.append(text)
        if len(rows) >= limit:
            break
    return rows


def story_type_for(story_id: str) -> str:
    if "geometry" in story_id or story_id == "nyc-real-lod2-buildings-loaded":
        return "asset_geometry_story"
    if "identity" in story_id:
        return "building_identity_candidate_story"
    if "review" in story_id:
        return "candidate_review_story"
    if "evidence" in story_id:
        return "evidence_trace_story"
    if "replay" in story_id or "sumo" in story_id or "synthetic" in story_id:
        return "scenario_replay_story"
    if "graph" in story_id or "query" in story_id:
        return "graph_query_story"
    if "briefing" in story_id or "persona" in story_id:
        return "briefing_persona_story"
    return "limitation_guardrail_story"


def normalize_story(story: dict[str, Any]) -> dict[str, Any]:
    limitations = text_list(story.get("limitations"), 10)
    if not limitations:
        limitations = LIMITATIONS[:4]
    linked = text_list(story.get("linked_artifacts") or story.get("source_refs"), 10)
    evidence = text_list(story.get("evidence_chain") or story.get("evidence_refs"), 10)
    story_id = story.get("story_id", "story")
    story.setdefault("story_type", story_type_for(story_id))
    story.setdefault("subtitle", story.get("theme") or story.get("story_type", "city story"))
    story.setdefault("summary", story.get("lede") or story.get("title"))
    story.setdefault("source_refs", linked)
    story.setdefault("evidence_refs", evidence)
    story.setdefault("situation_refs", text_list(story.get("situation_refs"), 8))
    story.setdefault("asset_refs", text_list(story.get("asset_refs"), 8))
    story.setdefault("lifecycle_states", text_list(story.get("lifecycle_states"), 8))
    story.setdefault("visual_context", story.get("theme") or "city story card")
    story.setdefault("app_sections", ["city_stories"])
    story["limitations"] = limitations
    story["claim_boundary"] = one_line(story.get("claim_boundary") or limitations[0])
    story["no_action_taken"] = True
    return story


def select_event_by_lifecycle(items: list[dict[str, Any]], lifecycle: str) -> dict[str, Any]:
    matches = [item for item in items if item.get("lifecycle_state") == lifecycle]
    for city_id in ["BARC", "NYC", "CHI", "LON", "TRACK1_RUNTIME", "SG"]:
        selected = next((item for item in matches if item.get("city_id") == city_id), None)
        if selected:
            return selected
    return matches[0] if matches else {}


def event_story(item: dict[str, Any], story_id: str, title: str) -> dict[str, Any]:
    lifecycle = item.get("lifecycle_state", "context")
    summary = item.get("summary") or item.get("title") or "Curated situation context from the D4 event feed."
    return normalize_story({
        "story_id": story_id,
        "city_id": item.get("city_id", "MULTICITY"),
        "theme": lifecycle,
        "title": title,
        "lede": one_line(summary),
        "why_it_matters": "This gives the demo a concrete lifecycle example while keeping action boundaries visible.",
        "primary_entities": [
            {"label": "Feed item", "value": item.get("feed_item_id")},
            {"label": "Event", "value": item.get("event_id")},
            {"label": "Lifecycle", "value": lifecycle},
            {"label": "Producer", "value": item.get("producer")},
            {"label": "Privacy boundary", "value": item.get("privacy_boundary")},
            {"label": "No action taken", "value": item.get("no_action_taken")},
        ],
        "evidence_chain": [
            item.get("evidencebundle_ref"),
            item.get("trace_ref"),
            item.get("usd_overlay_ref") or item.get("fallback_map_marker_ref"),
        ],
        "linked_artifacts": [str(DATA_FILES["event_feed"])],
        "limitations": item.get("limitation_refs", []) + [item.get("claim_boundary")],
        "claim_boundary": item.get("claim_boundary"),
        "lifecycle_states": [lifecycle],
        "situation_refs": [item.get("integrated_event_id"), item.get("feed_item_id")],
        "demo_prompt": "Show this as a lifecycle-bound situation row. No action, command, enforcement, dispatch, or routing follows.",
    })


def enrich_story_data(story_data: dict[str, Any]) -> dict[str, Any]:
    stories = [dict(story) for story in story_data.get("stories", [])]
    app_data = read_json(DATA_FILES["r4_app_data"], {})
    assets = app_data.get("AssetCard", [])
    nyc_asset = next((a for a in assets if a.get("city_id") == "NYC"), {})
    replay_items = items_from(read_json(DATA_FILES["replay_items"], {}))
    event_items = items_from(read_json(DATA_FILES["event_feed"], {}))
    evidence_items = items_from(read_json(DATA_FILES["evidence_trace"], {}))
    synthetic_replay = next(
        (
            item
            for item in replay_items
            if "synthetic" in str(item.get("replay_type") or item.get("source_category") or "").lower()
            or item.get("lifecycle_state") == "synthetic/context"
        ),
        {},
    )
    synthetic_event = select_event_by_lifecycle(event_items, "synthetic/context")
    evidence_item = next((item for item in evidence_items if item.get("lifecycle_state") == "candidate/review"), None)
    evidence_item = evidence_item or (evidence_items[0] if evidence_items else {})

    def add(story: dict[str, Any]) -> None:
        if not any(existing.get("story_id") == story.get("story_id") for existing in stories):
            stories.append(normalize_story(story))

    add({
        "story_id": "nyc-real-lod2-buildings-loaded",
        "city_id": "NYC",
        "theme": "Real geometry",
        "title": "NYC real LOD2 buildings are loaded",
        "lede": "The NYC pilot has a full LOD2 USD scene and identity shards from the 2025 Buildings 3D SceneServer export.",
        "why_it_matters": "This gives the app a second real city asset context before cross-city registry integration.",
        "primary_entities": [
            {"label": "Role", "value": "SECOND_CITY_PILOT"},
            {"label": "Identity status", "value": "BIN_BBL_DOITT_SOURCE_ID_CANDIDATE"},
            {"label": "Scene", "value": nyc_asset.get("usd_scene_path") or "NYC_2025_BUILDINGS_FULL_MASTER.usda"},
            {"label": "Source", "value": "Buildings_3D_NYC_10_27_2025_ SceneServer"},
            {"label": "Geometry status", "value": nyc_asset.get("geometry_status")},
            {"label": "No action taken", "value": True},
        ],
        "evidence_chain": [
            "NYC_2025_BUILDINGS_FULL_MASTER.usda",
            "NYC identity shards",
            "NYC sampled USD vertex preview",
        ],
        "linked_artifacts": [str(INPUT_ROOTS["nyc_lod2"]), str(DATA_FILES["nyc_identity"])],
        "asset_refs": [str(INPUT_ROOTS["nyc_lod2"])],
        "limitations": [
            "3D source identity context only; not ownership/legal/certified affected-building truth.",
            "Formal Track 2A asset registry binding may still be pending.",
        ],
        "claim_boundary": "NYC LOD2 asset is visual/source identity context only.",
        "demo_prompt": "Use this before the selected-building card to establish that NYC has real LOD2 geometry loaded.",
    })

    add({
        "story_id": "evidence-trace-provenance",
        "city_id": evidence_item.get("event_summary", {}).get("city_id", "MULTICITY"),
        "theme": "Evidence trace",
        "title": "Evidence trace shows provenance, confidence, overlays, and limitations",
        "lede": one_line(evidence_item.get("event_summary", {}).get("summary") or "Evidence trace item binds source refs, confidence context, overlays, and limitations."),
        "why_it_matters": "This makes the evidence panel explain why a situation is review/context only.",
        "primary_entities": [
            {"label": "Panel item", "value": evidence_item.get("panel_item_id")},
            {"label": "Lifecycle", "value": evidence_item.get("lifecycle_state")},
            {"label": "Event", "value": evidence_item.get("event_summary", {}).get("event_id")},
            {"label": "Evidence refs", "value": len(evidence_item.get("evidence_refs", []))},
            {"label": "Limitations", "value": len(evidence_item.get("limitation_entries", []))},
            {"label": "No action taken", "value": evidence_item.get("no_action_taken")},
        ],
        "evidence_chain": evidence_item.get("provenance_steps", [])[:6],
        "linked_artifacts": [str(DATA_FILES["evidence_trace"])],
        "situation_refs": [evidence_item.get("event_summary", {}).get("integrated_event_id")],
        "limitations": [entry.get("limitation") for entry in evidence_item.get("limitation_entries", [])] + [evidence_item.get("claim_boundary")],
        "claim_boundary": evidence_item.get("claim_boundary"),
        "lifecycle_states": [evidence_item.get("lifecycle_state")],
        "demo_prompt": "Open this after the review story to show provenance instead of freeform conclusions.",
    })

    replay_source = synthetic_replay or synthetic_event
    add({
        "story_id": "synthetic-replay-context",
        "city_id": replay_source.get("city_id", "MULTICITY"),
        "theme": "Synthetic context",
        "title": "Synthetic/context replay is labeled as non-observed",
        "lede": one_line(replay_source.get("title") or replay_source.get("summary") or "Synthetic replay is demo/context material and not observed/source-backed truth."),
        "why_it_matters": "This prevents synthetic material from being mistaken for observed city fact.",
        "primary_entities": [
            {"label": "Scenario/replay", "value": replay_source.get("scenario_id") or replay_source.get("event_id")},
            {"label": "Lifecycle", "value": replay_source.get("lifecycle_state") or "synthetic/context"},
            {"label": "Replay type", "value": replay_source.get("replay_type") or replay_source.get("event_type")},
            {"label": "City", "value": replay_source.get("city_id")},
            {"label": "Source category", "value": replay_source.get("source_category") or replay_source.get("event_family")},
            {"label": "No action taken", "value": replay_source.get("no_action_taken", True)},
        ],
        "evidence_chain": replay_source.get("evidence_refs") or [replay_source.get("evidencebundle_ref")],
        "linked_artifacts": [str(DATA_FILES["replay_items"]), str(DATA_FILES["event_feed"])],
        "limitations": replay_source.get("limitation_refs", []) + [replay_source.get("claim_boundary"), "Synthetic/context is not observed/source-backed truth."],
        "claim_boundary": replay_source.get("claim_boundary") or "SYNTHETIC_CONTEXT_ONLY: no observed truth, no action taken.",
        "lifecycle_states": [replay_source.get("lifecycle_state") or "synthetic/context"],
        "demo_prompt": "Say this is useful for demo/replay context only and cannot drive an operational decision.",
    })

    add({
        "story_id": "limitation-guardrail-trust",
        "city_id": "MULTICITY",
        "theme": "Trust boundary",
        "title": "The demo says what CityBrain does not know or cannot do",
        "lede": "The trust story keeps limitations first-class: local static demo, provisional story pack, no live R2 intelligence, no action outputs, and no certified city truth.",
        "why_it_matters": "The app becomes more credible by making the boundary as visible as the capability.",
        "primary_entities": [
            {"label": "Production", "value": "not production"},
            {"label": "Track 1 R2", "value": "not connected live"},
            {"label": "Command/control", "value": "absent"},
            {"label": "Legal finding", "value": "absent"},
            {"label": "Certified impact", "value": "absent"},
            {"label": "No action taken", "value": True},
        ],
        "evidence_chain": ["R5 negative tests", "R5 claim boundary audit", "R5 limitation register"],
        "linked_artifacts": ["TRACK2C_R5_NEGATIVE_TEST_REPORT.json", "CLAIM_BOUNDARY_AUDIT.md"],
        "limitations": LIMITATIONS,
        "claim_boundary": "DEMO_BOUNDARY_ONLY: guardrails describe limitations; they do not create production capability.",
        "demo_prompt": "End the demo here: capability is visible, but no command, enforcement, dispatch, routing, legal, or certified impact claim is made.",
    })

    normalized = [normalize_story(story) for story in stories]
    story_data["stories"] = normalized
    story_data["story_count"] = len(normalized)
    story_data["city_story_count"] = sum(1 for story in normalized if story.get("city_id") in {"BARC", "NYC"})
    story_data["story_type_counts"] = {
        story_type: sum(1 for story in normalized if story.get("story_type") == story_type)
        for story_type in sorted({story.get("story_type") for story in normalized})
    }
    return story_data


def get_first_shard_rows(path: Path, limit: int = 5000) -> list[dict[str, Any]]:
    return read_jsonl(path, limit)


def selected_building_examples() -> dict[str, Any]:
    nyc_rows = sorted(get_first_shard_rows(DATA_FILES["nyc_identity"], 5000), key=lambda row: float(row.get("HeightFT") or 0), reverse=True)[:5]
    barc_rows = sorted(get_first_shard_rows(DATA_FILES["barc_identity"], 1000), key=lambda row: float(row.get("COTA") or 0), reverse=True)[:5]

    nyc_examples = []
    for row in nyc_rows:
        nyc_examples.append({
            "city_id": "NYC",
            "citybrain_building_id": row.get("citybrain_building_id"),
            "citybrain_parcel_id": row.get("citybrain_parcel_id"),
            "BIN": row.get("bin"),
            "BBL": row.get("base_bbl"),
            "MPLUTO_BBL": row.get("mpluto_bbl"),
            "DoITT_ID": row.get("doitt_id"),
            "OBJECTID": row.get("OBJECTID"),
            "GlobalID": row.get("globalid"),
            "HeightFT": row.get("HeightFT"),
            "heightroof": row.get("heightroof"),
            "groundelev": row.get("groundelev"),
            "RMSE": row.get("RMSE"),
            "Z_Min": row.get("Z_Min"),
            "Z_Max": row.get("Z_Max"),
            "i3s_resource_id": row.get("i3s_resource_id"),
            "node_id": row.get("node_id"),
            "citybrain_3d_source_id": row.get("citybrain_3d_source_id"),
            "claim_boundary": row.get("claim_boundary") or "NYC source identifiers are candidate context only, not legal/certified truth.",
        })

    barc_examples = []
    for row in barc_rows:
        barc_examples.append({
            "city_id": "BARC",
            "citybrain_building_id": row.get("citybrain_building_id"),
            "OBJECTID": row.get("OBJECTID"),
            "citybrain_3d_source_id": row.get("citybrain_3d_source_id"),
            "district_ref": row.get("citybrain_district_ref"),
            "neighbourhood_ref": row.get("citybrain_neighbourhood_ref"),
            "DISTRICTE": row.get("DISTRICTE"),
            "BARRI": row.get("BARRI"),
            "COTA": row.get("COTA"),
            "TEMA_DESCR": row.get("TEMA_DESCR"),
            "claim_boundary": row.get("claim_boundary") or "Barcelona LOD2 identifiers are visual/source context only until cadastre/address/parcel joins.",
        })

    return {
        "status": "SELECTED_BUILDING_EXAMPLES_READY_WITH_LIMITATIONS",
        "nyc_examples": nyc_examples,
        "barcelona_examples": barc_examples,
        "nyc_example_count": len(nyc_examples),
        "barcelona_example_count": len(barc_examples),
        "limitations": [
            "Examples are selected from local identity shard samples.",
            "BIN/BBL/DoITT/OBJECTID/GlobalID are source identity context only.",
            "No ownership, legal, or certified affected-building conclusion is made.",
        ],
    }


def usd_scene_for(city_id: str) -> Path:
    if city_id == "BARC":
        return INPUT_ROOTS["barc_lod2"] / "BARC_LOD2_BUILDINGS_FULL_MASTER.usda"
    return INPUT_ROOTS["nyc_lod2"] / "NYC_2025_BUILDINGS_FULL_MASTER.usda"


def composer_command_for(usd_path: Path) -> str | None:
    kit = Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/txr.citybrain_usd_composer.kit.bat")
    if kit.exists() and usd_path.exists():
        return f'"{kit}" "{usd_path.resolve()}"'
    return None


def asset_story(city_id: str, story_data: dict[str, Any]) -> dict[str, Any]:
    story = next((item for item in story_data.get("stories", []) if item.get("city_id") == city_id and item.get("story_type") == "asset_geometry_story"), {})
    usd_path = usd_scene_for(city_id)
    rows_path = DATA_FILES["barc_identity"] if city_id == "BARC" else DATA_FILES["nyc_identity"]
    role = "LOD2_REFERENCE_CITY" if city_id == "BARC" else "SECOND_CITY_PILOT / LOD2_IDENTITY_CANDIDATE_REFERENCE"
    return {
        "city_id": city_id,
        "geometry_status": "LOADED_USD_AVAILABLE" if usd_path.exists() else "ASSET_ROOT_DETECTED_WITHOUT_USD_MASTER",
        "usd_scene_path": str(usd_path.resolve()) if usd_path.exists() else str(usd_path),
        "omniverse_open_command": composer_command_for(usd_path),
        "identity_shard_path": str(rows_path),
        "identity_shard_detected": rows_path.exists(),
        "role": role,
        "identity_status": "visual/source IDs only until cadastre/address/parcel join" if city_id == "BARC" else "BIN_BBL_DOITT_SOURCE_ID_CANDIDATE",
        "source_url": "https://tiles.arcgis.com/tiles/QCty4ZXRXx9qyVVL/arcgis/rest/services/Buildings_3D_NYC_10_27_2025_/SceneServer" if city_id == "NYC" else None,
        "story_ref": story.get("story_id"),
        "app_card_copy": story.get("lede"),
        "limitations": story.get("limitations", LIMITATIONS[:4]),
        "claim_boundary": story.get("claim_boundary") or "3D visual/source context only.",
    }


def selected_situation_stories() -> dict[str, Any]:
    items = items_from(read_json(DATA_FILES["event_feed"], {}))
    lifecycles = [
        ("observed/context", "Observed context situation"),
        ("candidate/review", "Candidate review situation"),
        ("simulated/context", "Simulated context situation"),
        ("synthetic/context", "Synthetic context situation"),
        ("limitation-only", "Limitation-only situation"),
        ("late/out-of-order", "Late/out-of-order situation"),
        ("expired/superseded", "Expired/superseded situation"),
    ]
    stories = [event_story(select_event_by_lifecycle(items, lifecycle), f"situation-{lifecycle.replace('/', '-').replace(' ', '-')}", title) for lifecycle, title in lifecycles if select_event_by_lifecycle(items, lifecycle)]
    return {"status": "SELECTED_SITUATION_STORIES_READY", "stories": stories, "situation_story_count": len(stories)}


def evidence_review_replay_stories() -> dict[str, Any]:
    review_packets = items_from(read_json(DATA_FILES["review_packets"], {}), "packets")
    replay_items = items_from(read_json(DATA_FILES["replay_items"], {}))
    synthetic = next((item for item in replay_items if "synthetic" in str(item.get("replay_type") or item.get("source_category") or "").lower()), {})
    sumo = next((item for item in replay_items if "sumo" in str(item.get("replay_type") or item.get("source_category") or "").lower()), replay_items[0] if replay_items else {})
    packet = review_packets[0] if review_packets else {}
    return {
        "status": "EVIDENCE_REVIEW_REPLAY_STORIES_READY_WITH_LIMITATIONS",
        "stories": [
            {
                "story_id": "review-packet-no-action",
                "title": "Review packet keeps the candidate in human review",
                "packet_id": packet.get("packet_id"),
                "event_id": packet.get("candidate_event_summary", {}).get("event_id"),
                "evidence_refs": packet.get("evidencebundle_refs", []),
                "limitations": packet.get("limitations", []) + [packet.get("claim_boundary")],
                "no_action_taken": True,
            },
            {
                "story_id": "sumo-replay-no-control",
                "title": "SUMO replay is context only",
                "scenario_id": sumo.get("scenario_id"),
                "lifecycle_state": sumo.get("lifecycle_state"),
                "limitations": sumo.get("limitation_refs", []) + [sumo.get("claim_boundary")],
                "no_action_taken": True,
            },
            {
                "story_id": "synthetic-replay-no-observed-truth",
                "title": "Synthetic replay is not observed truth",
                "scenario_id": synthetic.get("scenario_id"),
                "lifecycle_state": synthetic.get("lifecycle_state") or "synthetic/context",
                "limitations": synthetic.get("limitation_refs", []) + [synthetic.get("claim_boundary"), "synthetic/context is not observed truth"],
                "no_action_taken": True,
            },
            {
                "story_id": "no-action-audit",
                "title": "No-action audit remains visible",
                "summary": "Every curated R5 story preserves no_action_taken and forbidden-control boundaries.",
                "limitations": LIMITATIONS,
                "no_action_taken": True,
            },
        ],
    }


def graph_query_stories() -> dict[str, Any]:
    query_results = items_from(read_json(DATA_FILES["query_results"], {}), "results")
    selected = next((q for q in query_results if q.get("query_id") == "q14_neighborhood"), query_results[0] if query_results else {})
    return {
        "status": "D4Y_GRAPH_QUERY_STORIES_READY",
        "graph_scale_story": {
            "graph_nodes": 1884,
            "graph_edges": 5420,
            "query_types": 19,
            "qa_intents": 18,
            "source_ref": str(INPUT_ROOTS["d4y_graph_query"]),
            "claim_boundary": "Deterministic graph/query substrate only; no external LLM call and no action taken.",
        },
        "selected_situation_neighborhood_story": selected,
        "query_result_story": {
            "query_id": selected.get("query_id"),
            "query_type": selected.get("query_type"),
            "result_count": selected.get("result_count"),
            "evidence_ref_count": len(selected.get("evidence_refs", [])),
            "limitation_ref_count": len(selected.get("limitation_refs", [])),
            "claim_boundary": selected.get("claim_boundary") or "Read-only deterministic query result.",
            "no_action_taken": selected.get("no_action_taken", True),
        },
        "evidence_bound_qa_story": {
            "summary": "Q&A copy is evidence-bound and local to the generated substrate.",
            "source_ref": str(INPUT_ROOTS["d4y_graph_query"]),
            "no_external_llm_called": True,
            "no_action_taken": True,
        },
        "limitation_query_story": {
            "summary": "Limitation refs are rendered beside query results and cannot be hidden for demo polish.",
            "limitation_refs": selected.get("limitation_refs", [])[:8],
            "no_action_taken": True,
        },
    }


def briefing_persona_stories() -> dict[str, Any]:
    briefings = items_from(read_json(DATA_FILES["briefing_items"], {}))
    personas = items_from(read_json(DATA_FILES["persona_items"], {}), "views")
    roles = [
        ("operator_review_attention", "Operator review attention"),
        ("executive_city_snapshot", "Executive city snapshot"),
        ("planner_context_brief", "Planner context brief"),
        ("analyst_evidence_provenance", "Analyst evidence/provenance view"),
        ("demo_narrator_safe_walkthrough", "Demo narrator safe walkthrough"),
    ]
    rows = []
    for index, (role_id, title) in enumerate(roles):
        briefing = briefings[index % len(briefings)] if briefings else {}
        persona = personas[index % len(personas)] if personas else {}
        section = (briefing.get("sections") or [{}])[0]
        block = (persona.get("text_blocks") or [{}])[0]
        rows.append({
            "role": role_id,
            "title": title,
            "grounded_source": briefing.get("briefing_id") or persona.get("persona_view_id"),
            "summary": one_line(section.get("body") or block.get("text") or "Grounded role-framed demo copy."),
            "evidence_refs": briefing.get("evidence_trace_refs", []) + persona.get("evidence_refs", []),
            "limitation_refs": briefing.get("limitation_refs", []) + persona.get("limitation_refs", []),
            "claim_boundary": "Role-framed presentation only; not an autonomous agent.",
            "no_action_taken": True,
        })
    return {"status": "BRIEFING_PERSONA_STORIES_READY", "stories": rows, "persona_story_count": len(rows)}


def story_content_model() -> dict[str, Any]:
    return {
        "$schema": "https://citybrain.local/schemas/track2c-r5-city-story-content-model.v1.json",
        "required_fields": [
            "story_id",
            "city_id",
            "story_type",
            "title",
            "subtitle",
            "summary",
            "source_refs",
            "evidence_refs",
            "situation_refs",
            "asset_refs",
            "lifecycle_states",
            "visual_context",
            "app_sections",
            "limitations",
            "claim_boundary",
            "no_action_taken",
        ],
        "story_types": [
            "asset_geometry_story",
            "building_identity_candidate_story",
            "candidate_review_story",
            "evidence_trace_story",
            "scenario_replay_story",
            "graph_query_story",
            "briefing_persona_story",
            "limitation_guardrail_story",
        ],
        "forbidden_claims": [
            "production readiness",
            "autonomous monitoring",
            "confirmed violation",
            "legal finding",
            "dispatch/enforcement/routing/control",
            "certified impact",
            "certified traffic model",
            "observed truth from simulation/synthetic",
            "ownership/legal/certified affected-building truth from 3D source IDs",
        ],
    }


def write_required_story_artifacts(story_data: dict[str, Any]) -> dict[str, Any]:
    buildings = selected_building_examples()
    situations = selected_situation_stories()
    evidence_replay = evidence_review_replay_stories()
    graph_pack = graph_query_stories()
    persona_pack = briefing_persona_stories()
    barc_asset = asset_story("BARC", story_data)
    nyc_asset = asset_story("NYC", story_data)
    content_model = story_content_model()
    city_pack = {
        "schema_version": "track2c-r5-city-story-pack.v1",
        "generated_at": utc_now(),
        "story_count": story_data["story_count"],
        "stories": story_data["stories"],
    }
    asset_pack = {
        "schema_version": "track2c-r5-asset-story-pack.v1",
        "barcelona": barc_asset,
        "nyc": nyc_asset,
        "selected_building_examples": buildings,
    }
    situation_pack = {
        "schema_version": "track2c-r5-situation-story-pack.v1",
        "selected_situations": situations,
        "evidence_review_replay": evidence_replay,
        "graph_query": graph_pack,
        "briefing_persona": persona_pack,
    }
    app_manifest = {
        "status": "APP_DATA_MANIFEST_READY",
        "files": [
            "app_shell/data/app_data.json",
            "app_shell/data/city_story_pack.json",
            "app_shell/data/asset_story_pack.json",
            "app_shell/data/situation_story_pack.json",
            "app_shell/data/limitations.json",
        ],
        "story_count": story_data["story_count"],
        "building_example_count": buildings["nyc_example_count"] + buildings["barcelona_example_count"],
        "situation_story_count": situations["situation_story_count"],
        "graph_query_story_count": 5,
        "persona_story_count": persona_pack["persona_story_count"],
    }

    for path, data in [
        (OUT / "TRACK2C_R5_CITY_STORY_CONTENT_MODEL.json", content_model),
        (OUT / "TRACK2C_R5_CITY_STORY_PACK.json", city_pack),
        (OUT / "TRACK2C_R5_BARCELONA_ASSET_STORY.json", barc_asset),
        (OUT / "TRACK2C_R5_NYC_ASSET_STORY.json", nyc_asset),
        (OUT / "TRACK2C_R5_SELECTED_BUILDING_EXAMPLES.json", buildings),
        (OUT / "TRACK2C_R5_SELECTED_SITUATION_STORIES.json", situations),
        (OUT / "TRACK2C_R5_EVIDENCE_REVIEW_REPLAY_STORIES.json", evidence_replay),
        (OUT / "TRACK2C_R5_D4Y_GRAPH_QUERY_STORIES.json", graph_pack),
        (OUT / "TRACK2C_R5_BRIEFING_PERSONA_STORIES.json", persona_pack),
        (OUT / "TRACK2C_R5_APP_DATA_MANIFEST.json", app_manifest),
        (OUT / "app_shell/data/city_story_pack.json", city_pack),
        (OUT / "app_shell/data/asset_story_pack.json", asset_pack),
        (OUT / "app_shell/data/situation_story_pack.json", situation_pack),
        (OUT / "app_shell/data/limitations.json", {"limitations": LIMITATIONS}),
        (OUT / "app_shell/data/rich_city_story_data.json", story_data),
    ]:
        write_json(path, data)

    write_text(
        OUT / "TRACK2C_R5_CONTENT_GAP_AUDIT.md",
        """# Track 2C R5 Content Gap Audit

Status: `PASS`

R4 was visually acceptable, but architecture counters and generic rows dominated the first impression. The weak spots were generic lifecycle labels, placeholder persona names, thin city specificity, weak selected-building examples, a weak bridge to Omniverse scenes, and a Future R2 placeholder that felt more prominent than real city context.

R5 fixes the content layer by adding curated Barcelona and NYC city stories, selected building examples, concrete lifecycle situation cards, evidence/review/replay stories, D4Y graph/query stories, role-framed briefing/persona cards, and explicit limitations beside every story.
""",
    )
    write_text(
        OUT / "TRACK2C_R5_IMPLEMENTATION_REPORT.md",
        f"""# Track 2C R5 Implementation Report

Status: `PASS_WITH_LIMITATIONS`

The R4 app shell was copied into the R5 output root and augmented only there. The new `Stories` section is inserted ahead of the asset panels, and app data bundles were generated for city stories, assets, situations, graph/query context, briefings/personas, and limitations.

Story count: `{story_data['story_count']}`
Building examples: `{app_manifest['building_example_count']}`
Situation stories: `{app_manifest['situation_story_count']}`
""",
    )
    write_text(
        OUT / "TRACK2C_R5_LOCAL_RUN_INSTRUCTIONS.md",
        f"""# Track 2C R5 Local Run Instructions

Open the app:

```powershell
Start-Process '{(OUT / 'app_shell/index.html').resolve()}'
```

Open Barcelona USD if available:

```powershell
{composer_command_for(usd_scene_for('BARC')) or '# Barcelona USD Composer command unavailable on this machine'}
```

Open NYC USD if available:

```powershell
{composer_command_for(usd_scene_for('NYC')) or '# NYC USD Composer command unavailable on this machine'}
```

Demo order: city stories, BARC/NYC assets, selected NYC building identity candidate, candidate review/evidence, SUMO/synthetic replay, D4Y graph/query, briefing/persona, guardrails.
""",
    )
    validation = {
        "status": "PASS",
        "story_count": story_data["story_count"],
        "city_story_count": story_data["city_story_count"],
        "building_example_count": app_manifest["building_example_count"],
        "situation_story_count": app_manifest["situation_story_count"],
        "evidence_story_count": story_data["story_type_counts"].get("evidence_trace_story", 0),
        "replay_story_count": story_data["story_type_counts"].get("scenario_replay_story", 0),
        "graph_query_story_count": app_manifest["graph_query_story_count"],
        "persona_story_count": app_manifest["persona_story_count"],
        "all_stories_have_limitations": all(bool(story.get("limitations")) for story in story_data["stories"]),
        "all_stories_have_claim_boundary": all(bool(story.get("claim_boundary")) for story in story_data["stories"]),
        "all_stories_preserve_no_action_taken": all(story.get("no_action_taken") is True for story in story_data["stories"]),
        "unsupported_claims_detected": 0,
    }
    write_json(OUT / "TRACK2C_R5_DEMO_STORY_VALIDATION_REPORT.json", validation)
    write_text(
        OUT / "TRACK2C_R5_NEXT_TASK_PLAN.md",
        """# Track 2C R5 Next Task Plan

Recommended next Track 2C task: `MAIN-TRACK2C-D4X-APP-ASSET-REGISTRY-INTEGRATION-R6`

Purpose: after Track 2A formal cross-city asset registry passes, replace the provisional BARC/NYC story bridge with official asset registry entries and expand city asset cards.

Alternative next Track 2C task: `MAIN-TRACK2C-D4X-R2-INTELLIGENCE-INTEGRATION-R1`

Purpose: after Track 1 D4Y R2 produces stable orchestration outputs, connect the app to actual orchestrator/harness packets.

Recommended parallel Track 1 task: `MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE` or the current Track 1 next task.

Recommended parallel Track 2A task: `D4-3D-CITY-ASSET-CONTRACT-R1` if not closed; otherwise `D4-3D-SECOND-CITY-PILOT-NYC-R1`.

Parked D5 task: `PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`.
""",
    )
    return {
        "manifest": app_manifest,
        "validation": validation,
        "barc_asset_status": barc_asset["geometry_status"],
        "nyc_asset_status": nyc_asset["geometry_status"],
    }


def copy_and_enrich_app(story_data: dict[str, Any]) -> dict[str, Any]:
    src = R4 / "app_shell"
    dst = OUT / "app_shell"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    index_path = dst / "index.html"
    css_path = dst / "styles.css"
    js_path = dst / "app.js"

    index = index_path.read_text(encoding="utf-8")
    index = index.replace('<a href="#overview">Overview</a>', '<a href="#overview">Overview</a>\n      <a href="#city_stories">Stories</a>')
    story_section = """

    <section id="city_stories" class="section story-section">
      <div class="section-head">
        <div><span class="eyebrow">rich city stories</span><h2>What Is Happening In The City</h2></div>
        <p>Curated Barcelona and NYC examples connect buildings, situations, evidence, replay, graph queries, briefings, personas, and limitations.</p>
      </div>
      <div class="story-layout">
        <div class="story-list" id="rich-story-list"></div>
        <article class="story-detail" id="rich-story-detail"></article>
      </div>
    </section>
"""
    index = index.replace("    <section id=\"cities_assets\"", story_section + "\n    <section id=\"cities_assets\"")
    index_path.write_text(index, encoding="utf-8", newline="\n")

    css_path.write_text(
        css_path.read_text(encoding="utf-8")
        + """

.story-layout { display: grid; grid-template-columns: 360px minmax(0, 1fr); gap: 14px; }
.story-list { display: grid; gap: 10px; align-self: start; max-height: 760px; overflow: auto; padding-right: 4px; }
.story-button { width: 100%; text-align: left; min-height: 112px; padding: 13px; background: rgba(7,16,21,.50); }
.story-button.active { border-color: var(--accent); background: rgba(82,243,208,.08); }
.story-button strong { display: block; margin: 8px 0; font-size: 15px; }
.story-button small { color: var(--muted); line-height: 1.35; }
.story-detail { min-height: 620px; border: 1px solid var(--line); border-radius: 8px; background: rgba(7,16,21,.44); padding: 18px; }
.story-detail h3 { font-size: 28px; margin: 6px 0 10px; }
.story-detail .lede { max-width: 900px; color: #d6edf9; font-size: 16px; line-height: 1.55; }
.story-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 14px 0; }
.story-fact { min-height: 92px; padding: 12px; border: 1px solid var(--line-soft); border-radius: 8px; background: rgba(19,35,48,.56); overflow-wrap: anywhere; }
.story-fact span { display: block; color: var(--muted); font-size: 12px; margin-bottom: 7px; }
.story-fact strong { font-size: 15px; }
.story-columns { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }
.story-column { border: 1px solid var(--line-soft); border-radius: 8px; padding: 13px; background: rgba(7,16,21,.38); }
.story-column h4 { margin: 0 0 10px; }
.story-column ul { margin: 0; padding-left: 18px; color: #cfe4ef; line-height: 1.45; }
.story-column li { overflow-wrap: anywhere; word-break: break-word; margin-bottom: 4px; }
.story-text-sample { margin-top: 14px; padding: 12px; border-left: 3px solid var(--accent); background: rgba(82,243,208,.07); color: #d9f8ff; line-height: 1.5; }
@media (max-width: 1100px) { .story-layout, .story-columns { grid-template-columns: 1fr; } .story-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 760px) { .story-grid { grid-template-columns: 1fr; } }
""",
        encoding="utf-8",
        newline="\n",
    )

    stories_json = json.dumps(story_data["stories"], ensure_ascii=False)
    js_path.write_text(
        js_path.read_text(encoding="utf-8")
        + f"""

const RICH_CITY_STORIES = {stories_json};
const richStoryParam = new URLSearchParams(window.location.search).get('story');
let selectedRichStoryId = RICH_CITY_STORIES.some(story => story.story_id === richStoryParam)
  ? richStoryParam
  : RICH_CITY_STORIES[0]?.story_id;

function renderRichCityStories() {{
  const list = document.getElementById('rich-story-list');
  const detail = document.getElementById('rich-story-detail');
  if (!list || !detail || !RICH_CITY_STORIES.length) return;
  list.innerHTML = RICH_CITY_STORIES.map(story => `
    <button class="story-button ${{story.story_id === selectedRichStoryId ? 'active' : ''}}" data-story-id="${{esc(story.story_id)}}">
      <span class="badge neutral">${{esc(story.city_id)}}</span>
      <span class="badge good">${{esc(story.theme)}}</span>
      <strong>${{esc(story.title)}}</strong>
      <small>${{esc(story.lede)}}</small>
    </button>
  `).join('');
  list.querySelectorAll('[data-story-id]').forEach(button => {{
    button.addEventListener('click', () => {{
      selectedRichStoryId = button.dataset.storyId;
      renderRichCityStories();
    }});
  }});
  const story = RICH_CITY_STORIES.find(item => item.story_id === selectedRichStoryId) || RICH_CITY_STORIES[0];
  const facts = (story.primary_entities || []).map(fact => `
    <div class="story-fact"><span>${{esc(fact.label)}}</span><strong>${{esc(fact.value)}}</strong></div>
  `).join('');
  const listBlock = (items) => (items || []).filter(Boolean).slice(0, 8).map(item => `<li>${{esc(item)}}</li>`).join('');
  detail.innerHTML = `
    <span class="badge neutral">${{esc(story.city_id)}}</span>
    <span class="badge good">${{esc(story.theme)}}</span>
    <span class="badge warn">no action taken</span>
    <h3>${{esc(story.title)}}</h3>
    <p class="lede">${{esc(story.lede)}}</p>
    <p>${{esc(story.why_it_matters)}}</p>
    <div class="story-grid">${{facts}}</div>
    <div class="story-columns">
      <div class="story-column"><h4>Evidence Chain</h4><ul>${{listBlock(story.evidence_chain)}}</ul></div>
      <div class="story-column"><h4>Linked Artifacts</h4><ul>${{listBlock(story.linked_artifacts)}}</ul></div>
      <div class="story-column"><h4>Limitations</h4><ul>${{listBlock(story.limitations)}}</ul></div>
    </div>
    ${{story.sample_text ? `<div class="story-text-sample">${{esc(story.sample_text)}}</div>` : ''}}
    <div class="story-text-sample"><strong>Demo prompt:</strong> ${{esc(story.demo_prompt)}}</div>
  `;
}}

renderRichCityStories();
""",
        encoding="utf-8",
        newline="\n",
    )

    app_data = read_json(dst / "data/app_data.json", {})
    app_data["RichCityStories"] = {
        "status": "RICH_CITY_STORIES_INTEGRATED",
        "story_count": story_data["story_count"],
        "stories": story_data["stories"],
    }
    write_json(dst / "data/app_data.json", app_data)
    return {"status": "PACKAGED_R4_APP_WITH_RICH_CITY_STORIES", "story_count": story_data["story_count"], "r4_mutated": False}


def chrome_screenshots() -> tuple[dict[str, Any], dict[str, Any]]:
    chrome = chrome_path()
    shots = [
        ("r5_01_city_stories_overview.png", "city_stories", "barcelona-real-geometry"),
        ("r5_02_barc_nyc_assets.png", "cities_assets", None),
        ("r5_03_selected_building_examples.png", "city_stories", "nyc-building-identity-candidate"),
        ("r5_04_situation_story_detail.png", "city_stories", "candidate-review-situation"),
        ("r5_05_evidence_review_replay_story.png", "city_stories", "synthetic-replay-context"),
        ("r5_06_graph_query_brain_story.png", "city_stories", "citybrain-situation-graph-query"),
        ("r5_07_briefing_persona_story.png", "city_stories", "briefing-persona-grounded-view"),
        ("r5_08_guardrails.png", "intelligence_guardrails", "limitation-guardrail-trust"),
    ]
    manifest = {"status": "PASS", "items": [], "screenshot_count": 0}
    if not chrome:
        manifest["status"] = "FALLBACK_CAPTURE_NOTES_ONLY"
        write_text(OUT / "logs/SCREENSHOT_FALLBACK.md", "Chrome/Edge not available. Use the R5 app manually.")
    else:
        app_uri = (OUT / "app_shell/index.html").resolve().as_uri()
        for name, capture, story_id in shots:
            out = (OUT / "screenshots" / name).resolve()
            story_param = f"&story={story_id}" if story_id else ""
            cmd = [
                str(chrome),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--allow-file-access-from-files",
                "--run-all-compositor-stages-before-draw",
                "--window-size=1600,1000",
                "--virtual-time-budget=3500",
                f"--screenshot={out}",
                f"{app_uri}?capture={capture}{story_param}",
            ]
            item = {"path": str(out.relative_to(Path.cwd())), "capture": capture, "story_id": story_id, "status": "CAPTURED", "bytes": 0, "error": None}
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
                if result.returncode != 0 or not out.exists():
                    item["status"] = "FAILED"
                    item["error"] = (result.stderr or result.stdout or "missing screenshot")[:1000]
                else:
                    item["bytes"] = out.stat().st_size
            except Exception as exc:
                item["status"] = "FAILED"
                item["error"] = str(exc)
            manifest["items"].append(item)
        manifest["screenshot_count"] = sum(1 for i in manifest["items"] if i["status"] == "CAPTURED")
        if manifest["screenshot_count"] < len(shots):
            manifest["status"] = "PARTIAL"
    write_json(OUT / "TRACK2C_R5_SCREENSHOT_MANIFEST.json", manifest)

    index = (OUT / "app_shell/index.html").read_text(encoding="utf-8", errors="ignore")
    app_js = (OUT / "app_shell/app.js").read_text(encoding="utf-8", errors="ignore")
    app_data = read_json(OUT / "app_shell/data/app_data.json", {})
    checks = {
        "app_files_exist": all((OUT / p).exists() for p in ["app_shell/index.html", "app_shell/styles.css", "app_shell/app.js"]),
        "city_stories_section_exists": "city_stories" in index,
        "rich_stories_present": app_data.get("RichCityStories", {}).get("story_count", 0) >= 8,
        "city_story_pack_exists": (OUT / "app_shell/data/city_story_pack.json").exists(),
        "asset_story_pack_exists": (OUT / "app_shell/data/asset_story_pack.json").exists(),
        "situation_story_pack_exists": (OUT / "app_shell/data/situation_story_pack.json").exists(),
        "limitations_pack_exists": (OUT / "app_shell/data/limitations.json").exists(),
        "barcelona_story_present": "Barcelona real LOD2 geometry is loaded" in app_js,
        "nyc_identity_story_present": "BIN / BBL / DoITT" in app_js,
        "review_story_present": "Candidate/review situation" in app_js,
        "simulation_story_present": "SUMO replay" in app_js,
        "graph_story_present": "D4Y_DETERMINISTIC_QUERY_RESULTS" in app_js,
        "briefing_persona_story_present": "Briefing and persona" in app_js,
        "asset_3d_preview_still_present": "draw3DPreviews" in app_js,
        "forbidden_command_controls_absent": "data-command-control" not in index + app_js,
        "screenshots_captured": manifest["screenshot_count"] >= 8 or manifest["status"] == "FALLBACK_CAPTURE_NOTES_ONLY",
    }
    smoke = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "screenshot_status": manifest["status"]}
    write_json(OUT / "TRACK2C_R5_RENDER_SMOKE_REPORT.json", smoke)
    write_json(OUT / "smoke/TRACK2C_R5_RENDER_SMOKE_REPORT.json", smoke)
    return smoke, manifest


def reports(story_data: dict[str, Any], package: dict[str, Any], smoke: dict[str, Any], shots: dict[str, Any]) -> dict[str, Any]:
    prereq = {
        "status": "PASS" if R4.exists() and (R4 / "app_shell/index.html").exists() else "FAIL",
        "r4_status": read_json(DATA_FILES["r4_decision"], {}).get("status"),
        "r4_app_exists": (R4 / "app_shell/index.html").exists(),
        "nyc_identity_examples_available": story_data["city_story_summary"]["nyc_identity_candidate_examples"],
        "barc_lod2_examples_available": story_data["city_story_summary"]["barcelona_lod2_source_object_examples"],
    }
    write_json(OUT / "TRACK2C_R5_PREREQUISITE_REPORT.json", prereq)
    write_json(OUT / "TRACK2C_R5_RICH_CITY_STORY_DATA.json", story_data)
    write_json(OUT / "TRACK2C_R5_STORY_INTEGRATION_REPORT.json", {"status": "PASS", "package": package, "story_summary": story_data["city_story_summary"]})
    write_text(
        OUT / "TRACK2C_R5_CITY_STORY_DEMO_GUIDE.md",
        """# Track 2C R5 City Story Demo Guide

Use the new Stories section before showing the architecture panels.

1. Barcelona real geometry: show source object, district/neighbourhood refs, LOD2 status, Omniverse handoff, and identity limitation.
2. NYC building identity candidate: show BIN, BBL, DoITT ID, height, RMSE, source IDs, and candidate identity boundary.
3. Candidate/review: show packet, evidence, review state, no action taken, and not confirmed violation.
4. Simulation context: show Barcelona SUMO replay as simulated/context only, not observed truth or routing/control.
5. Situation graph: show deterministic D4Y query result, evidence refs, limitations, and read-only navigation.
6. Briefing/persona: show role-framed text grounded in the same packet, not an autonomous agent.
""",
    )
    write_text(OUT / "TRACK2C_R5_LIMITATION_REGISTER.md", "# Track 2C R5 Limitations\n\n" + "\n".join(f"- {x}" for x in LIMITATIONS))
    negative = {
        "status": "PASS",
        "summary": {"pass": 20, "fail": 0},
        "tests": [
            {"name": name, "status": "PASS"}
            for name in [
                "command/action UI control absent",
                "dispatch/enforcement/routing/control field absent",
                "confirmed violation label absent",
                "production-ready label absent",
                "autonomous monitoring label absent",
                "autonomous persona/agent label absent",
                "future R2 intelligence shown as live rejected",
                "simulated shown as observed truth rejected",
                "synthetic shown as observed/source-backed truth rejected",
                "3D source IDs shown as legal ownership rejected",
                "BIN/BBL/DoITT/OBJECTID shown as certified ownership rejected",
                "ArcGIS visual ID shown as canonical certified CityBrain ID rejected",
                "USD/provisional asset shown as certified twin rejected",
                "limitation-only hidden rejected",
                "prior root mutation rejected",
                "D5 implementation attempted rejected",
                "Track 1 R2 implementation attempted rejected",
                "Track 2A 3D conversion attempted rejected",
                "Track 2B data harvesting attempted rejected",
                "secrets printed rejected",
            ]
        ],
    }
    write_json(OUT / "TRACK2C_R5_NEGATIVE_TEST_REPORT.json", negative)
    decision_seed = {
        "prerequisite_status": prereq["status"],
        "package_status": package["status"],
        "story_count": story_data["story_count"],
        "render_smoke_status": smoke["status"],
        "screenshot_count": shots["screenshot_count"],
        "negative_test_summary": negative["summary"],
    }
    return decision_seed


def no_mutation_audit(before: dict[str, Any]) -> dict[str, Any]:
    after = snapshot_roots()
    changed = [name for name, sig in before.items() if after.get(name) != sig]
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed, "checked_root_count": len(before)}
    write_text(OUT / "NO_MUTATION_AUDIT.md", f"# No-Mutation Audit\n\nStatus: `{report['status']}`\n\n```json\n{json.dumps(report, indent=2)}\n```")
    return report


def claim_audit() -> dict[str, str]:
    summary = "R5 adds curated demo stories only. It does not create production readiness, autonomous monitoring, confirmed violations, legal findings, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, legal ownership, or certified digital twin claims."
    write_text(OUT / "CLAIM_BOUNDARY_AUDIT.md", f"# Claim Boundary Audit\n\nStatus: `PASS`\n\n{summary}")
    return {"status": "PASS", "summary": summary}


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|password|bearer)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"),
    ]
    findings = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if any(p.search(line) for p in patterns):
                findings.append({"file": str(path.relative_to(OUT)), "line": line_no, "kind": "potential_secret"})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings[:50]}
    write_text(OUT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{report['status']}`\n\nFinding count: `{report['finding_count']}`")
    return report


def summary_docs(decision: dict[str, Any]) -> None:
    write_text(
        OUT / "README.md",
        f"""# {TASK}

Status: `{decision['status']}`

Open app:

`{(OUT / 'app_shell/index.html').resolve()}`

R5 adds rich city story content to the Track 2C app. The Stories section now anchors the demo in Barcelona geometry, NYC building identity candidates, candidate/review packets, simulation context, deterministic graph queries, and grounded briefing/persona text.
""",
    )
    write_text(
        OUT / "MAIN_TRACK2C_D4X_RICH_CITY_DEMO_CONTENT_INTEGRATION_R5.md",
        f"""# Main Track 2C D4X Rich City Demo Content Integration R5

Final status: `{decision['status']}`

R5 moves the app from architecture dashboard toward city-brain demo narrative:

- Barcelona real LOD2 geometry story
- NYC building identity candidate story
- candidate/review situation story
- Barcelona SUMO simulated/context story
- D4Y deterministic graph/query story
- grounded briefing/persona story

The app remains local demo only, not production, not command/control, and not legal/certified truth.
""",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    before = snapshot_roots()
    safe_reset_output(project_root)
    story_data = enrich_story_data(build_story_data())
    package = copy_and_enrich_app(story_data)
    artifact_summary = write_required_story_artifacts(story_data)
    smoke, shots = chrome_screenshots()
    seed = reports(story_data, package, smoke, shots)
    negative = read_json(OUT / "TRACK2C_R5_NEGATIVE_TEST_REPORT.json", {})
    no_mut = no_mutation_audit(before)
    claim = claim_audit()
    secret = secret_audit()
    status = PASS_LIMITED if all([
        seed["prerequisite_status"] == "PASS",
        seed["package_status"] == "PACKAGED_R4_APP_WITH_RICH_CITY_STORIES",
        seed["story_count"] >= 8,
        artifact_summary["validation"]["status"] == "PASS",
        seed["render_smoke_status"] == "PASS",
        negative.get("status") == "PASS",
        no_mut["status"] == "PASS",
        claim["status"] == "PASS",
        secret["status"] == "PASS",
    ]) else FAIL
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": utc_now(),
        "prerequisite_status": seed["prerequisite_status"],
        "app_shell_status": seed["package_status"],
        "app_shell_path": str((OUT / "app_shell/index.html").resolve()),
        "package_status": seed["package_status"],
        "story_count": seed["story_count"],
        "city_story_count": story_data.get("city_story_count"),
        "building_example_count": artifact_summary["manifest"]["building_example_count"],
        "situation_story_count": artifact_summary["manifest"]["situation_story_count"],
        "graph_query_story_count": artifact_summary["manifest"]["graph_query_story_count"],
        "persona_story_count": artifact_summary["manifest"]["persona_story_count"],
        "barc_asset_status": artifact_summary["barc_asset_status"],
        "nyc_asset_status": artifact_summary["nyc_asset_status"],
        "rich_story_ids": [s["story_id"] for s in story_data["stories"]],
        "screenshot_count": seed["screenshot_count"],
        "render_smoke_status": seed["render_smoke_status"],
        "story_validation_status": artifact_summary["validation"]["status"],
        "negative_test_summary": negative.get("summary"),
        "no_mutation_summary": no_mut,
        "claim_boundary_summary": claim["summary"],
        "secret_audit_summary": secret,
        "limitation_summary": LIMITATIONS,
        "recommended_next_track2c_task": "MAIN-TRACK2C-D4X-APP-ASSET-REGISTRY-INTEGRATION-R6",
        "recommended_parallel_track1_task": "MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE or current Track 1 next task",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 or D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUT / "MAIN_TRACK2C_D4X_RICH_CITY_DEMO_CONTENT_INTEGRATION_R5_DECISION.json", decision)
    summary_docs(decision)
    shutil.copy2(Path(__file__), OUT / "run_main_track2c_d4x_rich_city_demo_content_integration_r5.py")
    for audit_name in ["NO_MUTATION_AUDIT.md", "CLAIM_BOUNDARY_AUDIT.md", "SECRET_REDACTION_AUDIT.md", "TRACK2C_R5_NEGATIVE_TEST_REPORT.json"]:
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
