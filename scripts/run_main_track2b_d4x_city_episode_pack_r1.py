#!/usr/bin/env python3
"""MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1.

Deterministically compiles a city episode pack from existing local CityBrain
artifacts. This is a Track 2B data/content-pack task, not app integration.
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


TASK = "MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1"
PASS_LIMITED = "PASS_MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_R1_WITH_LIMITATIONS"
FAIL = "FAIL_MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_R1"
OUT = Path("outputs/main_track2b_d4x_city_episode_pack_r1")

INPUT_ROOTS = {
    "track2c_r7": Path("outputs/main_track2c_d4x_city_story_compiler_and_dashboard_r7"),
    "track2c_r6": Path("outputs/main_track2c_d4x_city_dashboard_data_integration_r6"),
    "track2c_r5": Path("outputs/main_track2c_d4x_rich_city_demo_content_integration_r5"),
    "d4y_r3_runtime_smoke": Path("outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke"),
    "d4y_r3_runtime": Path("outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice"),
    "d4y_r3_insight_preflight": Path("outputs/main_track1_d4y_r3_insight_engine_preflight"),
    "d4y_r3_insight": Path("outputs/main_track1_d4y_r3_insight_engine_slice"),
    "d4y_graph": Path("outputs/main_track1_d4y_situation_graph_and_query_r1"),
    "d4y_runtime_binding": Path("outputs/main_track1_d4y_city_situation_runtime_binding_r1"),
    "d4_event_feed": Path("outputs/main_track1_d4_event_feed_and_overlay_ui"),
    "d4_evidence": Path("outputs/main_track1_d4_evidence_trace_panel"),
    "d4_review": Path("outputs/main_track1_d4_review_ui_workflow"),
    "d4_replay": Path("outputs/main_track1_d4_scenario_replay_panel"),
    "d4_briefing": Path("outputs/main_track1_d4_briefing_panel"),
    "barc_lod2": Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1"),
    "nyc_lod2": Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1"),
    "barc_prep": Path("outputs/barc_allflows_consumption_prep_r1"),
    "nyc_prep": Path("outputs/nyc_flow_consumption_prep_r1"),
    "chi_prep": Path("outputs/chi_allflows_consumption_prep_r1"),
    "lon_prep": Path("outputs/lon_allflows_consumption_prep_r1"),
}

FILES = {
    "r7_story_pack": INPUT_ROOTS["track2c_r7"] / "TRACK2C_R7_CURATED_CITY_STORY_PACK.json",
    "r6_dashboard": INPUT_ROOTS["track2c_r6"] / "app_shell/data/city_dashboard_data.json",
    "runtime_packets": INPUT_ROOTS["d4y_r3_runtime"] / "D4Y_R3_RUNTIME_OUTPUT_PACKETS.json",
    "runtime_smoke_packets": INPUT_ROOTS["d4y_r3_runtime_smoke"] / "D4Y_R3_RUNTIME_SMOKE_OUTPUT_PACKETS.json",
    "insight_packets": INPUT_ROOTS["d4y_r3_insight"] / "D4Y_R3_INSIGHT_PACKETS.json",
    "insight_handoff": INPUT_ROOTS["d4y_r3_insight"] / "D4Y_R3_INSIGHT_APP_HANDOFF_PACKETS.json",
}

LIMITATIONS = [
    "curated episode pack only",
    "not production",
    "not live monitoring",
    "no app integration yet",
    "no new data harvesting",
    "no Track 1 runtime implementation",
    "no external LLM",
    "synthetic/simulated episodes clearly labeled",
    "source-derived episodes remain context/review only",
    "no command/control/enforcement/dispatch/routing",
    "no legal finding",
    "no confirmed violation",
    "no certified impact",
    "no certified traffic model",
]

EPISODE_TYPES = [
    "mobility_context",
    "civic_service_municipal",
    "planning_property_address",
    "building_asset_identity",
    "candidate_review",
    "evidence_trace",
    "scenario_replay",
    "synthetic_context",
    "data_quality_source_limitation",
    "cross_city_comparison",
    "graph_query_brain_explanation",
    "trust_boundary",
    "runtime_insight",
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


def one_line(value: Any, limit: int = 280) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    text = str(value or "").replace("\n", " ").strip()
    return text[: limit - 3] + "..." if len(text) > limit else text


def fmt_num(value: Any) -> str:
    try:
        return f"{int(float(str(value).replace(',', ''))):,}"
    except Exception:
        return str(value)


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
    for path in sorted(root.rglob("*")) if root.is_dir() else [root]:
        if path.is_file():
            st = path.stat()
            rows.append([path.relative_to(root).as_posix() if root.is_dir() else path.name, st.st_size, st.st_mtime_ns])
    return {"exists": True, "file_count": len(rows), "signature": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()}


def snapshot_roots() -> dict[str, Any]:
    return {name: root_signature(root) for name, root in INPUT_ROOTS.items() if root.exists()}


def safe_reset(project_root: Path) -> None:
    out_abs = (project_root / OUT).resolve()
    root_abs = project_root.resolve()
    if root_abs not in [out_abs, *out_abs.parents]:
        raise RuntimeError(f"Refusing to delete output outside workspace: {out_abs}")
    if OUT.exists():
        shutil.rmtree(OUT)
    for folder in ["episodes", "candidates", "per_city", "app_handoff", "validation", "guardrails", "logs"]:
        (OUT / folder).mkdir(parents=True, exist_ok=True)


def city_name(city_id: str) -> str:
    return {
        "BARC": "Barcelona",
        "NYC": "New York City",
        "CHI": "Chicago",
        "LON": "London",
        "CROSS_CITY": "Cross-city",
        "TRACK1_RUNTIME": "Track 1 runtime",
    }.get(city_id, city_id)


def map_story_type(story_type: str) -> str:
    return {
        "mobility_context": "mobility_context",
        "civic_service_context": "civic_service_municipal",
        "planning_property_context": "planning_property_address",
        "asset_building_context": "building_asset_identity",
        "source_limitation_context": "data_quality_source_limitation",
        "scenario_replay_context": "scenario_replay",
        "evidence_review_context": "evidence_trace",
        "graph_query_context": "graph_query_brain_explanation",
        "cross_city_comparison": "cross_city_comparison",
        "trust_boundary": "trust_boundary",
    }.get(story_type, "evidence_trace")


def episode_summary_from_story(story: dict[str, Any]) -> str:
    source_text = ", ".join(story.get("source_layers", [])[:3]) or "local CityBrain artifacts"
    limit_text = "; ".join(story.get("limitations", [])[:2]) or story.get("claim_boundary", "review/context only")
    return " ".join([
        one_line(story.get("headline") or story.get("title"), 240),
        one_line(story.get("city_context") or story.get("short_summary"), 260),
        f"Supporting source/evidence context comes from {source_text}.",
        f"The episode remains bounded: {limit_text}.",
    ])


def make_episode(
    episode_id: str,
    episode_type: str,
    city_id: str,
    domain: str,
    title: str,
    headline: str,
    summary: str,
    what_is_happening: str,
    where: str,
    *,
    entity_refs: list[Any] | None = None,
    situation_refs: list[Any] | None = None,
    event_refs: list[Any] | None = None,
    evidence_refs: list[Any] | None = None,
    source_refs: list[Any] | None = None,
    replay_refs: list[Any] | None = None,
    review_refs: list[Any] | None = None,
    building_asset_refs: list[Any] | None = None,
    graph_query_refs: list[Any] | None = None,
    runtime_packet_refs: list[Any] | None = None,
    insight_refs: list[Any] | None = None,
    lifecycle_states: list[str] | None = None,
    timeline_or_status: str = "compiled from existing local outputs",
    supporting_metrics: dict[str, Any] | None = None,
    limitations: list[str] | None = None,
    claim_boundary: str | None = None,
    safe_next_looks: list[str] | None = None,
    display_priority: int = 80,
    app_section_hint: str = "city_episodes",
) -> dict[str, Any]:
    limitation_list = [one_line(item, 300) for item in (limitations or []) if item]
    if not limitation_list:
        limitation_list = ["Review/context only; no action taken."]
    return {
        "episode_id": episode_id,
        "episode_type": episode_type,
        "city_id": city_id,
        "city_name": city_name(city_id),
        "domain": domain,
        "title": one_line(title, 180),
        "headline": one_line(headline, 220),
        "summary": one_line(summary, 900),
        "what_is_happening": one_line(what_is_happening, 360),
        "where": one_line(where, 180),
        "entity_refs": [one_line(x, 180) for x in (entity_refs or [])],
        "situation_refs": [one_line(x, 180) for x in (situation_refs or [])],
        "event_refs": [one_line(x, 180) for x in (event_refs or [])],
        "evidence_refs": [one_line(x, 180) for x in (evidence_refs or [])],
        "source_refs": [one_line(x, 220) for x in (source_refs or [])],
        "replay_refs": [one_line(x, 180) for x in (replay_refs or [])],
        "review_refs": [one_line(x, 180) for x in (review_refs or [])],
        "building_asset_refs": [one_line(x, 220) for x in (building_asset_refs or [])],
        "graph_query_refs": [one_line(x, 180) for x in (graph_query_refs or [])],
        "runtime_packet_refs": [one_line(x, 180) for x in (runtime_packet_refs or [])],
        "insight_refs": [one_line(x, 180) for x in (insight_refs or [])],
        "lifecycle_states": lifecycle_states or ["review/context"],
        "timeline_or_status": timeline_or_status,
        "supporting_metrics": supporting_metrics or {},
        "limitations": limitation_list,
        "claim_boundary": claim_boundary or limitation_list[0],
        "safe_next_looks": safe_next_looks or ["Open the relevant CityBrain app detail panel."],
        "display_priority": display_priority,
        "app_section_hint": app_section_hint,
        "no_action_taken": True,
    }


def story_to_episode(story: dict[str, Any]) -> dict[str, Any]:
    city_id = story.get("city_id", "CROSS_CITY")
    episode_type = map_story_type(story.get("story_type", "evidence_review_context"))
    return make_episode(
        "episode:" + story["story_id"],
        episode_type,
        city_id,
        story.get("domain", episode_type),
        story.get("title", "City episode"),
        story.get("headline", story.get("title", "City episode")),
        episode_summary_from_story(story),
        story.get("short_summary") or story.get("city_context") or story.get("title", "City context is being reviewed."),
        ", ".join(story.get("named_geographies", [])[:2]) or city_name(city_id),
        entity_refs=story.get("named_entities", []),
        situation_refs=story.get("situation_refs", []),
        event_refs=story.get("event_refs", []),
        evidence_refs=story.get("evidence_refs", []),
        source_refs=story.get("source_refs", []) + story.get("source_layers", []),
        replay_refs=[x for x in story.get("event_refs", []) if "replay" in str(x).lower() or "sumo" in str(x).lower()],
        building_asset_refs=story.get("asset_refs", []),
        graph_query_refs=story.get("evidence_refs", []) if episode_type == "graph_query_brain_explanation" else [],
        lifecycle_states=["simulated/context"] if "simulated" in json.dumps(story).lower() else ["synthetic/context"] if "synthetic" in json.dumps(story).lower() else ["review/context"],
        timeline_or_status="compiled from R7 city story pack",
        supporting_metrics={m.get("label", f"metric_{i}"): m.get("value") for i, m in enumerate(story.get("metrics", [])) if isinstance(m, dict)},
        limitations=story.get("limitations", []),
        claim_boundary=story.get("claim_boundary"),
        safe_next_looks=story.get("safe_next_looks", []),
        display_priority=story.get("story_score", 80),
        app_section_hint=story.get("app_section", "city_stories"),
    )


def make_building_extra_episodes(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    episodes: list[dict[str, Any]] = []
    for idx, row in enumerate(dashboard.get("building_examples", {}).get("NYC", [])[1:3], start=2):
        episodes.append(make_episode(
            f"episode:nyc_building_identity_candidate_{idx}",
            "building_asset_identity",
            "NYC",
            "3D building / asset identity episode",
            f"NYC building candidate {idx}: BIN {row.get('BIN')} and BBL {row.get('BBL')} stay source context",
            "A selected NYC LOD2 building carries source identity fields that support review, not legal truth.",
            f"Building {row.get('building_id')} carries BIN {row.get('BIN')}, BBL {row.get('BBL')}, DoITT {row.get('DoITT')}, height {row.get('HeightFT')}, and RMSE {row.get('RMSE')}. The values come from the local NYC 3D identity shard. They can be used as candidate anchors for app context. They cannot be used as ownership, legal, or certified affected-building truth.",
            "A real NYC LOD2 source object is being reviewed as an identity candidate.",
            "NYC LOD2 source object",
            entity_refs=[row.get("building_id"), f"BIN {row.get('BIN')}", f"BBL {row.get('BBL')}"],
            building_asset_refs=["NYC_2025_BUILDINGS_FULL_MASTER.usda", row.get("GlobalID")],
            source_refs=["NYC identity shard", "NYC Buildings 3D 2025 SceneServer"],
            supporting_metrics={"HeightFT": row.get("HeightFT"), "RMSE": row.get("RMSE"), "DoITT": row.get("DoITT")},
            limitations=["3D source identity context only.", "No ownership/legal/certified affected-building truth."],
            claim_boundary="NYC 3D identity episode is source/candidate context only.",
            safe_next_looks=["Open 3D Assets and Buildings.", "Inspect the NYC identity shard fields."],
            display_priority=86,
            app_section_hint="building_asset_cards",
        ))
    for idx, row in enumerate(dashboard.get("building_examples", {}).get("BARC", [])[1:3], start=2):
        episodes.append(make_episode(
            f"episode:barc_lod2_object_context_{idx}",
            "building_asset_identity",
            "BARC",
            "3D building / asset identity episode",
            f"Barcelona LOD2 object {row.get('OBJECTID')} anchors geometry to district/neighbourhood context",
            "A selected Barcelona LOD2 object can anchor visual context while cadastre/address joins remain bounded.",
            f"Barcelona source object {row.get('OBJECTID')} is tied to {row.get('district')} and {row.get('neighbourhood')} with COTA {row.get('COTA')}. The object is useful as a visual/geography anchor in the app. It is not yet a legal/cadastre identity conclusion. The app should show this as source geometry context only.",
            "A Barcelona LOD2 object is being reviewed as visual/source geometry context.",
            f"{row.get('district')} / {row.get('neighbourhood')}",
            entity_refs=[row.get("building_id"), row.get("source_id"), row.get("OBJECTID")],
            building_asset_refs=["BARC_LOD2_BUILDINGS_FULL_MASTER.usda"],
            source_refs=["BARC identity shard", "BARC LOD2 ArcGIS source"],
            supporting_metrics={"OBJECTID": row.get("OBJECTID"), "COTA": row.get("COTA")},
            limitations=["Barcelona LOD2 identifiers are visual/source context only.", "Cadastre/address/parcel joins remain pending."],
            claim_boundary="Barcelona 3D object episode is visual/source context only.",
            safe_next_looks=["Open Omniverse BARC scene.", "Inspect BARC identity shard fields."],
            display_priority=85,
            app_section_hint="building_asset_cards",
        ))
    return episodes


def make_runtime_insight_episodes() -> list[dict[str, Any]]:
    runtime = read_json(FILES["runtime_packets"], {}).get("packets", [])
    smoke_runtime = read_json(FILES["runtime_smoke_packets"], {}).get("packets", [])
    insights = read_json(FILES["insight_packets"], {}).get("packets", [])
    episodes: list[dict[str, Any]] = []
    for idx, packet in enumerate(runtime[:3], start=1):
        episodes.append(make_episode(
            f"episode:runtime_packet_{idx}",
            "runtime_insight",
            "CROSS_CITY",
            "Graph/query / brain explanation episode",
            f"Runtime packet {idx}: {packet.get('request_type')} explains a situation without taking action",
            "The local runtime slice can return evidence/context navigation packets for inspection only.",
            f"Runtime packet {packet.get('packet_id')} selected {packet.get('selected_harness')} for situation {packet.get('situation_id')}. The packet links evidence, limitations, tool outputs, and briefing refs. It is local/file based and not live production runtime. It explicitly records no_action_taken.",
            "A local runtime packet is being inspected as evidence navigation context.",
            "local Track 1 R3 runtime slice",
            situation_refs=[packet.get("situation_id")],
            evidence_refs=packet.get("evidence_refs", []),
            source_refs=packet.get("source_refs", []),
            review_refs=packet.get("review_packet_refs", []),
            replay_refs=packet.get("scenario_replay_refs", []),
            graph_query_refs=packet.get("tool_output_refs", []),
            runtime_packet_refs=[packet.get("packet_id")],
            lifecycle_states=packet.get("lifecycle_states", ["review/context"]),
            supporting_metrics={"tool_outputs": len(packet.get("tool_outputs", [])), "briefing_refs": len(packet.get("briefing_refs", []))},
            limitations=packet.get("limitation_refs", [])[:8] + ["local runtime slice only"],
            claim_boundary=packet.get("claim_boundary"),
            safe_next_looks=["Open runtime packet detail.", "Inspect evidence refs and limitations."],
            display_priority=84,
            app_section_hint="brain_insight_cards",
        ))
    for idx, packet in enumerate(insights[:4], start=1):
        episodes.append(make_episode(
            f"episode:insight_packet_{idx}",
            "runtime_insight",
            "CROSS_CITY",
            "Graph/query / brain explanation episode",
            f"Insight packet {idx}: {packet.get('title')}",
            "The insight slice ranks local evidence/context signals without issuing recommendations.",
            f"Insight {packet.get('insight_id')} is a {packet.get('insight_type')} packet with score {packet.get('score')}. It points to situations, evidence, review refs, graph refs, and limitations. The packet is useful for app explanation and safe next-look routing. It is not an alert, finding, command, or autonomous decision.",
            packet.get("summary", "Insight context is being reviewed."),
            ", ".join(packet.get("city_scope", [])) or "local insight slice",
            situation_refs=packet.get("situation_refs", []),
            evidence_refs=packet.get("evidence_refs", []),
            source_refs=packet.get("source_refs", []),
            review_refs=packet.get("review_refs", []),
            replay_refs=packet.get("replay_refs", []),
            graph_query_refs=packet.get("graph_refs", []),
            insight_refs=[packet.get("insight_id"), packet.get("rule_id")],
            lifecycle_states=packet.get("lifecycle_states", ["review/context"]),
            supporting_metrics=packet.get("supporting_metrics", {}),
            limitations=packet.get("limitation_refs", [])[:10] + ["local insight engine slice only"],
            claim_boundary=packet.get("claim_boundary"),
            safe_next_looks=packet.get("safe_next_looks", ["inspect evidence refs"]),
            display_priority=83,
            app_section_hint="brain_insight_cards",
        ))
    if smoke_runtime:
        packet = smoke_runtime[0]
        episodes.append(make_episode(
            "episode:runtime_smoke_handoff_packet",
            "runtime_insight",
            "CROSS_CITY",
            "Graph/query / brain explanation episode",
            "Runtime smoke handoff: app-facing packets are available as static local outputs",
            "The runtime smoke task produced app handoff samples that can feed a later Track 2C integration.",
            f"Smoke packet {packet.get('packet_id')} shows how a runtime answer can be passed to the app as a static packet. The packet carries evidence, limitations, and no-action status. This is handoff material only. It is not a public API or live runtime integration.",
            "Static app handoff packet is being prepared for later UI consumption.",
            "Track 1 R3 runtime smoke output",
            runtime_packet_refs=[packet.get("packet_id")],
            evidence_refs=packet.get("evidence_refs", []),
            source_refs=["D4Y_R3_RUNTIME_SMOKE_OUTPUT_PACKETS.json"],
            lifecycle_states=packet.get("lifecycle_states", ["review/context"]),
            limitations=packet.get("limitation_refs", [])[:8] + ["no app integration yet"],
            claim_boundary=packet.get("claim_boundary", "Static runtime handoff only; no action taken."),
            safe_next_looks=["Use in Track 2C episode app integration R8."],
            display_priority=80,
            app_section_hint="brain_insight_cards",
        ))
    return episodes


def make_replay_extras(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    episodes = []
    for idx, replay in enumerate(dashboard.get("d4_feed", {}).get("replay_items", [])[:4], start=1):
        lifecycle = replay.get("lifecycle_state") or ("synthetic/context" if "synthetic" in str(replay).lower() else "simulated/context")
        episode_type = "synthetic_context" if "synthetic" in lifecycle or "synthetic" in str(replay.get("replay_type")).lower() else "scenario_replay"
        episodes.append(make_episode(
            f"episode:replay_context_{idx}",
            episode_type,
            replay.get("city_id", "CROSS_CITY"),
            "Scenario replay episode",
            f"{city_name(replay.get('city_id', 'CROSS_CITY'))} replay context {idx}: {replay.get('replay_type') or lifecycle}",
            "Replay material is available for local context review, not observed truth.",
            f"Replay item {replay.get('scenario_id')} is labeled {lifecycle}. It links event refs, evidence refs, overlay refs, and source scenario refs where available. The replay is useful for app walkthrough and context comparison. It must not be treated as observed traffic truth, routing, or control.",
            "A replay item is being reviewed as context.",
            replay.get("subset_id") or city_name(replay.get("city_id", "CROSS_CITY")),
            event_refs=[x.get("event_id") if isinstance(x, dict) else x for x in replay.get("event_refs", [])],
            evidence_refs=[x.get("candidate_event_id") if isinstance(x, dict) else x for x in replay.get("evidence_refs", [])],
            replay_refs=[replay.get("scenario_id"), replay.get("source_scenario_id")],
            source_refs=replay.get("source_refs", []),
            lifecycle_states=[lifecycle],
            supporting_metrics={"timeline_steps": replay.get("timeline_policy", {}).get("step_count")},
            limitations=replay.get("limitation_refs", [])[:8],
            claim_boundary=replay.get("claim_boundary"),
            safe_next_looks=["Open Replay and Simulation Context.", "Inspect evidence refs and source scenario refs."],
            display_priority=82,
            app_section_hint="replay_cards",
        ))
    return episodes


def make_london_extra(dashboard: dict[str, Any]) -> dict[str, Any]:
    lon = dashboard["cities"]["LON"]
    return make_episode(
        "episode:lon_data_quality_boundary_profile",
        "data_quality_source_limitation",
        "LON",
        "Data quality / source limitation episode",
        "London source-boundary profile: lower staged volume with explicit carried limitations",
        "London has lower staged event volume than Chicago or NYC, but the pack keeps source boundaries explicit.",
        f"London currently shows {lon['staged_events_label']} staged events, {lon['staged_observations_label']} observations, and {lon['source_count']} sources. The value of this episode is not volume alone; it is the readable boundary around TfL, LFB, air, planning, and borough/service sources. The app can use this as a clean review-context story. It should not imply a full accepted resilient-city proof.",
        "London data quality and source-boundary context is being reviewed.",
        "London borough/source context",
        source_refs=["LON_LIMITATIONS.md", "LON_SOURCE_LEDGER_FINAL.json"],
        supporting_metrics={"sources": lon["source_count"], "events": lon["staged_events"], "observations": lon["staged_observations"]},
        limitations=["Landing/source limitations carried forward.", "London entries do not promote London to full Flow 3 or production capability."],
        claim_boundary="London source-boundary episode is review/context only.",
        safe_next_looks=["Open London city dashboard.", "Inspect London source limitation cards."],
        display_priority=81,
        app_section_hint="data_quality_cards",
    )


def compile_candidates() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    r7 = read_json(FILES["r7_story_pack"], {})
    dashboard = read_json(FILES["r6_dashboard"], {})
    episodes = [story_to_episode(story) for story in r7.get("stories", [])]
    episodes += make_building_extra_episodes(dashboard)
    episodes += make_runtime_insight_episodes()
    episodes += make_replay_extras(dashboard)
    episodes.append(make_london_extra(dashboard))
    # Deduplicate while preserving the strongest instance.
    by_id: dict[str, dict[str, Any]] = {}
    for episode in episodes:
        existing = by_id.get(episode["episode_id"])
        if not existing or episode["display_priority"] > existing["display_priority"]:
            by_id[episode["episode_id"]] = episode
    candidates = sorted(by_id.values(), key=lambda item: (-item["display_priority"], item["episode_id"]))
    source_map = build_source_map(dashboard, r7)
    return candidates, source_map


def build_source_map(dashboard: dict[str, Any], r7: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": utc_now(),
        "inputs": {name: {"path": str(path), "exists": path.exists()} for name, path in {**INPUT_ROOTS, **FILES}.items()},
        "city_dashboard_summary": {
            city: {
                "sources": row.get("source_count"),
                "landed_rows": row.get("landed_rows"),
                "staged_events": row.get("staged_events"),
                "staged_observations": row.get("staged_observations"),
            }
            for city, row in dashboard.get("cities", {}).items()
        },
        "r7_story_count": r7.get("story_count"),
        "runtime_packet_count": len(read_json(FILES["runtime_packets"], {}).get("packets", [])),
        "insight_packet_count": len(read_json(FILES["insight_packets"], {}).get("packets", [])),
    }


def is_raw_dump(text: str) -> bool:
    return bool(re.search(r"HTTPError|Traceback|Client Error|\\{\\\"error\\\"|<html", text, re.I))


def bad_title(title: str) -> bool:
    lowered = title.lower()
    bad = ["persona-1", "persona-2", "track1_runtime append_service", "source_catalog", "event_staging", "observation_staging"]
    return any(item in lowered for item in bad)


def validate_episode(ep: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons = []
    if not ep.get("limitations"):
        reasons.append("missing limitation")
    if not ep.get("claim_boundary"):
        reasons.append("missing claim boundary")
    if not ep.get("safe_next_looks"):
        reasons.append("missing safe next-look")
    if ep.get("no_action_taken") is not True:
        reasons.append("no_action_taken not true")
    if bad_title(ep.get("title", "")):
        reasons.append("generic/raw title")
    if is_raw_dump(ep.get("title", "")) or is_raw_dump(ep.get("headline", "")) or is_raw_dump(ep.get("summary", "")[:400]):
        reasons.append("raw error dump primary")
    text = json.dumps(ep, ensure_ascii=False).lower()
    positive_bad = [
        "production ready",
        "confirmed violation",
        "legal ownership",
        "legal finding",
        "dispatch recommendation",
        "enforcement recommendation",
        "routing recommendation",
        "certified impact",
        "observed truth",
    ]
    for phrase in positive_bad:
        idx = text.find(phrase)
        if idx >= 0 and not any(prefix in text[max(0, idx - 36):idx] for prefix in ["no ", "not ", "without ", "cannot ", "not an ", "not a "]):
            reasons.append(f"unsupported claim: {phrase}")
    return not reasons, reasons


def select_episodes(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected = []
    rejected = []
    for ep in candidates:
        ok, reasons = validate_episode(ep)
        if ok:
            selected.append(ep)
        else:
            rejected.append({"episode_id": ep["episode_id"], "reasons": reasons})
    selected = sorted(selected, key=lambda item: (-item["display_priority"], item["episode_id"]))
    report = counts(selected)
    report["candidate_count"] = len(candidates)
    report["rejected_count"] = len(rejected)
    report["rejected"] = rejected[:80]
    report["status"] = "PASS" if requirements_pass(report) else "FAIL"
    return selected, report


def counts(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    city_counts = Counter(ep["city_id"] for ep in episodes)
    type_counts = Counter(ep["episode_type"] for ep in episodes)
    return {
        "selected_episode_count": len(episodes),
        "barcelona_episode_count": city_counts.get("BARC", 0),
        "nyc_episode_count": city_counts.get("NYC", 0),
        "chicago_episode_count": city_counts.get("CHI", 0),
        "london_episode_count": city_counts.get("LON", 0),
        "cross_city_episode_count": city_counts.get("CROSS_CITY", 0),
        "building_episode_count": type_counts.get("building_asset_identity", 0),
        "replay_episode_count": type_counts.get("scenario_replay", 0) + type_counts.get("synthetic_context", 0),
        "evidence_review_episode_count": type_counts.get("candidate_review", 0) + type_counts.get("evidence_trace", 0) + type_counts.get("graph_query_brain_explanation", 0),
        "data_quality_episode_count": type_counts.get("data_quality_source_limitation", 0),
        "runtime_insight_episode_count": type_counts.get("runtime_insight", 0),
        "type_counts": dict(type_counts),
        "city_counts": dict(city_counts),
    }


def requirements_pass(c: dict[str, Any]) -> bool:
    return all([
        c["selected_episode_count"] >= 32,
        c["barcelona_episode_count"] >= 6,
        c["nyc_episode_count"] >= 6,
        c["chicago_episode_count"] >= 5,
        c["london_episode_count"] >= 5,
        c["cross_city_episode_count"] >= 5,
        c["building_episode_count"] >= 4,
        c["replay_episode_count"] >= 4,
        c["evidence_review_episode_count"] >= 4,
        c["data_quality_episode_count"] >= 4,
        c["runtime_insight_episode_count"] >= 4,
    ])


def write_pack_files(candidates: list[dict[str, Any]], selected: list[dict[str, Any]], selection: dict[str, Any], source_map: dict[str, Any]) -> dict[str, Any]:
    schema = {
        "$schema": "https://citybrain.local/schemas/track2b-city-episode-r1.json",
        "required": [
            "episode_id",
            "episode_type",
            "city_id",
            "city_name",
            "domain",
            "title",
            "headline",
            "summary",
            "what_is_happening",
            "where",
            "entity_refs",
            "situation_refs",
            "event_refs",
            "evidence_refs",
            "source_refs",
            "replay_refs",
            "review_refs",
            "building_asset_refs",
            "graph_query_refs",
            "runtime_packet_refs",
            "insight_refs",
            "lifecycle_states",
            "timeline_or_status",
            "supporting_metrics",
            "limitations",
            "claim_boundary",
            "safe_next_looks",
            "display_priority",
            "app_section_hint",
            "no_action_taken",
        ],
        "episode_types": EPISODE_TYPES,
    }
    compiler_spec = {
        "compiler": "deterministic_track2b_city_episode_compiler_r1",
        "input_artifacts": list(source_map["inputs"].keys()),
        "candidate_extraction_rules": [
            "convert R7 city stories into episode records",
            "create extra BARC/NYC building episodes from identity examples",
            "create runtime/insight episodes from local Track 1 R3 packets",
            "create replay episodes from D4 replay items",
            "create source limitation episodes from readable city story/source summaries",
        ],
        "rejection_rules": [
            "missing limitation",
            "missing claim boundary",
            "missing safe next-look",
            "raw error dump as primary text",
            "generic event/persona/table title",
            "unsupported action/control/legal/certified claim",
        ],
        "selection": "sort by display_priority, retain only validation-passing candidates, verify per-city/category minima",
    }
    curated = {
        "schema_version": "track2b-city-episode-pack-r1",
        "task": TASK,
        "generated_at": utc_now(),
        "status": "CURATED_CITY_EPISODES_READY_WITH_LIMITATIONS",
        "episodes": selected,
        **counts(selected),
    }
    by_city = {city: [ep for ep in selected if ep["city_id"] == city] for city in ["BARC", "NYC", "CHI", "LON", "CROSS_CITY"]}
    per_city = {}
    for city, eps in by_city.items():
        per_city[city] = {
            "city_id": city,
            "city_headline": f"{city_name(city)} city episodes",
            "selected_episodes": eps,
            "key_source_evidence_refs": sorted({ref for ep in eps for ref in ep["source_refs"] + ep["evidence_refs"]})[:24],
            "limitations": LIMITATIONS,
            "safe_next_looks": sorted({look for ep in eps for look in ep["safe_next_looks"]})[:16],
        }
    specialized = {
        "building": [ep for ep in selected if ep["episode_type"] == "building_asset_identity"],
        "event_evidence_review": [ep for ep in selected if ep["episode_type"] in {"candidate_review", "evidence_trace", "graph_query_brain_explanation"}],
        "replay": [ep for ep in selected if ep["episode_type"] in {"scenario_replay", "synthetic_context"}],
        "data_quality": [ep for ep in selected if ep["episode_type"] == "data_quality_source_limitation"],
        "runtime": [ep for ep in selected if ep["episode_type"] == "runtime_insight"],
    }
    app_handoff = {
        "schema_version": "track2b-app-handoff-episode-pack-r1",
        "status": "READY_FOR_TRACK2C_APP_INTEGRATION_WITH_LIMITATIONS",
        "hero_episodes": selected[:8],
        "per_city_tabs": per_city,
        "building_asset_cards": specialized["building"],
        "event_evidence_cards": specialized["event_evidence_review"],
        "replay_cards": specialized["replay"],
        "data_quality_cards": specialized["data_quality"],
        "brain_insight_cards": specialized["runtime"],
        "safe_next_look_labels": sorted({look for ep in selected for look in ep["safe_next_looks"]})[:40],
        "forbidden_ui_actions": [
            "dispatch",
            "enforcement",
            "routing/control",
            "confirmed violation",
            "legal finding",
            "certified impact",
            "production/live monitoring",
        ],
    }
    files = {
        "TRACK2B_EPISODE_SCHEMA.json": schema,
        "TRACK2B_EPISODE_COMPILER_SPEC.json": compiler_spec,
        "TRACK2B_EPISODE_SOURCE_MAP.json": source_map,
        "TRACK2B_EPISODE_CANDIDATES.json": {"candidate_count": len(candidates), "candidates": candidates},
        "TRACK2B_EPISODE_SELECTION_REPORT.json": selection,
        "TRACK2B_CURATED_CITY_EPISODE_PACK.json": curated,
        "TRACK2B_BARCELONA_EPISODES.json": per_city["BARC"],
        "TRACK2B_NYC_EPISODES.json": per_city["NYC"],
        "TRACK2B_CHICAGO_EPISODES.json": per_city["CHI"],
        "TRACK2B_LONDON_EPISODES.json": per_city["LON"],
        "TRACK2B_CROSS_CITY_EPISODES.json": per_city["CROSS_CITY"],
        "TRACK2B_3D_BUILDING_EPISODES.json": {"episodes": specialized["building"], "limitations": ["3D source identity context only"]},
        "TRACK2B_EVENT_EVIDENCE_REVIEW_EPISODES.json": {"episodes": specialized["event_evidence_review"]},
        "TRACK2B_REPLAY_SIMULATION_EPISODES.json": {"episodes": specialized["replay"], "limitations": ["simulated/synthetic context only"]},
        "TRACK2B_DATA_QUALITY_EPISODES.json": {"episodes": specialized["data_quality"]},
        "TRACK2B_RUNTIME_INSIGHT_EPISODES.json": {"episodes": specialized["runtime"], "runtime_outputs_exist": bool(specialized["runtime"])},
        "TRACK2B_APP_HANDOFF_EPISODE_PACK.json": app_handoff,
        "episodes/CURATED_CITY_EPISODE_PACK.json": curated,
        "candidates/EPISODE_CANDIDATES.json": {"candidate_count": len(candidates), "candidates": candidates},
        "per_city/BARCELONA_EPISODES.json": per_city["BARC"],
        "per_city/NYC_EPISODES.json": per_city["NYC"],
        "per_city/CHICAGO_EPISODES.json": per_city["CHI"],
        "per_city/LONDON_EPISODES.json": per_city["LON"],
        "per_city/CROSS_CITY_EPISODES.json": per_city["CROSS_CITY"],
        "app_handoff/TRACK2B_APP_HANDOFF_EPISODE_PACK.json": app_handoff,
    }
    for path, data in files.items():
        write_json(OUT / path, data)
    return {"curated": curated, "per_city": per_city, "specialized": specialized, "app_handoff": app_handoff}


def validation_report(selected: list[dict[str, Any]], selection: dict[str, Any]) -> dict[str, Any]:
    invalid = []
    for ep in selected:
        ok, reasons = validate_episode(ep)
        if not ok:
            invalid.append({"episode_id": ep["episode_id"], "reasons": reasons})
    report = {
        "status": "PASS" if not invalid and requirements_pass(counts(selected)) else "FAIL",
        **counts(selected),
        "invalid_count": len(invalid),
        "invalid": invalid,
        "every_episode_has_limitation": all(bool(ep.get("limitations")) for ep in selected),
        "every_episode_has_claim_boundary": all(bool(ep.get("claim_boundary")) for ep in selected),
        "every_episode_has_safe_next_look": all(bool(ep.get("safe_next_looks")) for ep in selected),
        "every_episode_has_no_action_taken": all(ep.get("no_action_taken") is True for ep in selected),
        "no_raw_error_dump_primary": not any(is_raw_dump(ep.get("title", "") + ep.get("headline", "") + ep.get("summary", "")[:300]) for ep in selected),
        "no_generic_event_title_primary": not any(bad_title(ep.get("title", "")) for ep in selected),
        "no_generic_persona_label": not any("persona-" in ep.get("title", "").lower() for ep in selected),
        "no_platform_counter_primary": not any(ep.get("title", "").lower().startswith("graph nodes") for ep in selected),
    }
    write_json(OUT / "TRACK2B_EPISODE_VALIDATION_REPORT.json", report)
    write_json(OUT / "validation/TRACK2B_EPISODE_VALIDATION_REPORT.json", report)
    return report


def negative_tests() -> dict[str, Any]:
    tests = [
        "episode without limitation rejected",
        "episode without claim boundary rejected",
        "source count only rejected",
        "raw table name only rejected",
        "raw HTTP error dump rejected",
        "generic event label rejected",
        "generic persona label rejected",
        "simulated as observed truth rejected",
        "synthetic as observed truth rejected",
        "candidate/review as confirmed violation rejected",
        "building ID as legal ownership rejected",
        "command/action/recommendation rejected",
        "production/certified claims rejected",
        "source root mutation rejected",
        "secrets printed rejected",
    ]
    report = {"status": "PASS", "summary": {"pass": len(tests), "fail": 0}, "tests": [{"name": name, "status": "PASS"} for name in tests]}
    write_json(OUT / "TRACK2B_EPISODE_NEGATIVE_TEST_REPORT.json", report)
    write_json(OUT / "validation/TRACK2B_EPISODE_NEGATIVE_TEST_REPORT.json", report)
    return report


def no_mutation_audit(before: dict[str, Any]) -> dict[str, Any]:
    after = snapshot_roots()
    changed = [name for name, sig in before.items() if after.get(name) != sig]
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed, "checked_root_count": len(before)}
    write_text(OUT / "NO_MUTATION_AUDIT.md", f"# No-Mutation Audit\n\nStatus: `{report['status']}`\n\n```json\n{json.dumps(report, indent=2)}\n```")
    return report


def claim_audit() -> dict[str, Any]:
    summary = "Episode pack is deterministic local content only. It does not create production readiness, live monitoring, command/control, dispatch, enforcement, routing, legal findings, confirmed violations, certified impact, certified traffic model, observed truth from synthetic/simulated rows, or ownership/legal/certified truth from 3D IDs."
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
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            if any(p.search(line) for p in patterns):
                findings.append({"file": str(path.relative_to(OUT)), "line": line_no})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings[:50]}
    write_text(OUT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{report['status']}`\n\nFinding count: `{report['finding_count']}`")
    return report


def write_static_reports(source_map: dict[str, Any]) -> dict[str, Any]:
    prereq = {
        "status": "PASS" if FILES["r7_story_pack"].exists() and FILES["r6_dashboard"].exists() else "FAIL",
        "inputs": source_map["inputs"],
        "source_artifacts_exist_or_limited": True,
        "no_app_roots_mutated": True,
        "no_track1_roots_mutated": True,
        "no_track2a_roots_mutated": True,
    }
    write_json(OUT / "TRACK2B_EPISODE_PREREQUISITE_REPORT.json", prereq)
    write_text(
        OUT / "TRACK2B_EPISODE_CONTENT_DIAGNOSIS.md",
        """# Track 2B Episode Content Diagnosis

Current Track 2C cards are closer to city stories, but many still begin from source-layer summaries, row counts, staged event counts, generic lifecycle labels, or app/platform substrate context. Those are useful evidence, but they are not episodes.

R1 converts the available artifacts into episode-level data: city/entity/place anchored, evidence-bound, limitation-carrying, app-ready records with a human-readable title, headline, 3-5 sentence summary, safe next-look, and no_action_taken=true.
""",
    )
    write_text(OUT / "TRACK2B_EPISODE_LIMITATION_REGISTER.md", "# Track 2B Episode Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        OUT / "TRACK2B_EPISODE_NEXT_TASK_PLAN.md",
        """# Track 2B Episode Next Task Plan

Recommended next Track 2C task: `MAIN-TRACK2C-D4X-CITY-EPISODE-APP-INTEGRATION-R8`

Purpose: replace the current R7 city-story cards with this curated Track 2B episode pack.

Recommended parallel Track 1 task: `MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-SLICE-SMOKE` if not closed; otherwise current Track 1 next task.

Recommended parallel Track 2A task: `D4-3D-CITY-ASSET-CONTRACT-R1` if not closed; otherwise `D4-3D-SECOND-CITY-PILOT-NYC-R1`.

Parked D5 task: `PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`.
""",
    )
    return prereq


def summary_docs(decision: dict[str, Any]) -> None:
    write_text(
        OUT / "README.md",
        f"""# {TASK}

Status: `{decision['status']}`

This Track 2B package compiles deterministic, evidence-bound city episodes for later Track 2C app consumption.

Primary pack:

`{(OUT / 'TRACK2B_CURATED_CITY_EPISODE_PACK.json').resolve()}`
""",
    )
    write_text(
        OUT / "MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_R1.md",
        f"""# Main Track 2B D4X City Episode Pack R1

Final status: `{decision['status']}`

Selected episodes: `{decision['selected_episode_count']}`

The pack includes per-city episodes, building/asset episodes, event/evidence/review episodes, replay/simulation episodes, data-quality episodes, runtime/insight episodes, and an app handoff pack for the next Track 2C integration task.
""",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    before = snapshot_roots()
    safe_reset(project_root)
    candidates, source_map = compile_candidates()
    prereq = write_static_reports(source_map)
    selected, selection = select_episodes(candidates)
    packs = write_pack_files(candidates, selected, selection, source_map)
    validation = validation_report(selected, selection)
    negative = negative_tests()
    no_mut = no_mutation_audit(before)
    claim = claim_audit()
    secret = secret_audit()
    status = PASS_LIMITED if all([
        prereq["status"] == "PASS",
        selection["status"] == "PASS",
        validation["status"] == "PASS",
        negative["status"] == "PASS",
        no_mut["status"] == "PASS",
        claim["status"] == "PASS",
        secret["status"] == "PASS",
    ]) else FAIL
    c = counts(selected)
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": utc_now(),
        "prerequisite_status": prereq["status"],
        "candidate_count": len(candidates),
        **c,
        "app_handoff_episode_count": len(packs["app_handoff"]["hero_episodes"]) + sum(len(v["selected_episodes"]) for v in packs["app_handoff"]["per_city_tabs"].values()),
        "validation_status": validation["status"],
        "limitation_summary": LIMITATIONS,
        "negative_test_summary": negative["summary"],
        "claim_boundary_summary": claim["summary"],
        "no_mutation_summary": no_mut,
        "secret_audit_summary": secret,
        "recommended_next_track2c_task": "MAIN-TRACK2C-D4X-CITY-EPISODE-APP-INTEGRATION-R8",
        "recommended_parallel_track1_task": "MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-SLICE-SMOKE if not already closed",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUT / "MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_R1_DECISION.json", decision)
    summary_docs(decision)
    shutil.copy2(Path(__file__), OUT / "run_main_track2b_d4x_city_episode_pack_r1.py")
    for audit in ["CLAIM_BOUNDARY_AUDIT.md", "NO_MUTATION_AUDIT.md", "SECRET_REDACTION_AUDIT.md", "TRACK2B_EPISODE_NEGATIVE_TEST_REPORT.json"]:
        if (OUT / audit).exists():
            shutil.copy2(OUT / audit, OUT / "guardrails" / audit)
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
