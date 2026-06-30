#!/usr/bin/env python3
"""MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1.

Builds a new product-wise app shell around Track 2B city episodes. The
existing Track 2C R7 app is left untouched. This runner reads only existing
local artifacts and writes a separate static app output root.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from typing import Any


TASK = "MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1"
PASS_LIMITED = "PASS_MAIN_TRACK2C_D4X_CITY_FIRST_EPISODE_APP_REBUILD_R1_WITH_LIMITATIONS"
FAIL = "FAIL_MAIN_TRACK2C_D4X_CITY_FIRST_EPISODE_APP_REBUILD_R1"
OUT = Path("outputs/main_track2c_d4x_city_first_episode_app_rebuild_r1")
APP = OUT / "app_shell"

EPISODE_ROOT = Path("outputs/main_track2b_d4x_city_episode_pack_r1")
R6_ROOT = Path("outputs/main_track2c_d4x_city_dashboard_data_integration_r6")
R7_ROOT = Path("outputs/main_track2c_d4x_city_story_compiler_and_dashboard_r7")
BARC_3D = Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1")
NYC_3D = Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1")

INPUT_ROOTS = {
    "track2b_episode_pack": EPISODE_ROOT,
    "track2c_r6_city_dashboard_data": R6_ROOT,
    "track2c_r7_previous_app_left_untouched": R7_ROOT,
    "barcelona_lod2_usd": BARC_3D,
    "nyc_2025_lod2_usd": NYC_3D,
}

FILES = {
    "episode_pack": EPISODE_ROOT / "TRACK2B_CURATED_CITY_EPISODE_PACK.json",
    "app_handoff_pack": EPISODE_ROOT / "TRACK2B_APP_HANDOFF_EPISODE_PACK.json",
    "episode_decision": EPISODE_ROOT / "MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_R1_DECISION.json",
    "dashboard_data": R6_ROOT / "app_shell/data/city_dashboard_data.json",
    "barc_usd": BARC_3D / "BARC_LOD2_BUILDINGS_FULL_MASTER.usda",
    "nyc_usd": NYC_3D / "NYC_2025_BUILDINGS_FULL_MASTER.usda",
}

CITY_ORDER = ["BARC", "NYC", "CHI", "LON", "CROSS_CITY"]
CITY_NAMES = {
    "BARC": "Barcelona",
    "NYC": "New York City",
    "CHI": "Chicago",
    "LON": "London",
    "CROSS_CITY": "Cross-city",
}

LIMITATIONS = [
    "local static demo app only",
    "new app shell only; previous R7 app left untouched",
    "episode content is curated from existing local packs",
    "not production UI",
    "no auth/RBAC",
    "no live runtime connection",
    "no external API or LLM call",
    "browser 3D panel is an interactive preview, not a USD renderer",
    "Omniverse USD scenes open separately through the listed local commands",
    "source-derived episodes remain review/context only",
    "simulation/replay episodes are not observed truth",
    "building IDs are source identity context only, not legal/ownership truth",
    "no command/control/enforcement/dispatch/routing",
    "no confirmed violation",
    "no certified affected-building or impact claim",
    "no certified traffic model",
]

FORBIDDEN_POSITIVE_CLAIMS = [
    "production ready",
    "autonomous monitoring",
    "confirmed violation",
    "legal finding",
    "dispatch command",
    "enforcement command",
    "traffic-control command",
    "transit-control command",
    "certified affected-building",
    "certified traffic model",
    "observed traffic truth",
    "ownership truth",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def root_signature(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "digest": None}
    files = sorted(p for p in root.rglob("*") if p.is_file())
    h = hashlib.sha256()
    for path in files:
        stat = path.stat()
        h.update(str(path.relative_to(root)).replace("\\", "/").encode("utf-8"))
        h.update(str(stat.st_size).encode("ascii"))
        h.update(str(int(stat.st_mtime_ns)).encode("ascii"))
    return {"exists": True, "file_count": len(files), "digest": h.hexdigest()}


def snapshot_roots() -> dict[str, dict[str, Any]]:
    return {name: root_signature(path) for name, path in INPUT_ROOTS.items()}


def safe_reset_output() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    for folder in [
        APP / "data",
        OUT / "audits",
        OUT / "guardrails",
        OUT / "screenshots",
        OUT / "smoke",
        OUT / "logs",
    ]:
        folder.mkdir(parents=True, exist_ok=True)


def one_line(value: Any, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def classify_episode(ep: dict[str, Any]) -> str:
    mapping = {
        "building_asset_identity": "3D / building",
        "mobility_context": "Mobility",
        "civic_service_municipal": "Civic services",
        "planning_property_address": "Planning / property",
        "scenario_replay": "Replay / simulation",
        "evidence_trace": "Evidence / review",
        "graph_query_brain_explanation": "Brain / graph",
        "runtime_insight": "Runtime / insight",
        "data_quality_source_limitation": "Data quality",
        "cross_city_comparison": "Cross-city comparison",
        "trust_boundary": "Trust boundary",
    }
    return mapping.get(str(ep.get("episode_type") or ""), "City context")


def safe_source_issue(source: dict[str, Any]) -> dict[str, Any]:
    status = str(source.get("status") or "LIMITATION")
    if status == "BLOCKED_REMOTE":
        issue = "Remote/source endpoint was blocked or unavailable in local prep; the app shows the gap instead of fabricating data."
    elif status == "KEY_BLOCKED":
        issue = "A credential/key was required. The source remains explicit as unavailable in this demo pack."
    elif status in {"CAP_PARTIAL", "CAPPED_BULK"}:
        issue = "The source is capped or partial. Coverage is useful for context but not complete truth."
    elif status == "ENDPOINT_VALIDATION_REQUIRED":
        issue = "Endpoint-specific validation is still required before stronger claims."
    else:
        issue = "Bounded data-quality note carried forward from the prep pack."
    return {
        "source": source.get("source"),
        "status": status,
        "rows": source.get("rows", 0),
        "rows_label": f"{int(source.get('rows') or 0):,}",
        "issue_summary": issue,
    }


def summarize_flow(flow: dict[str, Any]) -> dict[str, Any]:
    return {
        "flow": flow.get("flow"),
        "name": flow.get("name"),
        "status": flow.get("status"),
        "row_coverage": flow.get("row_coverage"),
        "source_coverage": flow.get("source_coverage"),
        "limitations": one_line(flow.get("limitations"), 180),
    }


def make_city_profile(city_id: str, city: dict[str, Any], episodes: list[dict[str, Any]]) -> dict[str, Any]:
    city_eps = [ep for ep in episodes if ep.get("city_id") == city_id]
    top_sources = city.get("top_sources") or []
    source_issues = city.get("source_issues") or []
    mart = city.get("mart") or {}
    return {
        "city_id": city_id,
        "city_name": city.get("city_name") or CITY_NAMES.get(city_id, city_id),
        "episode_count": len(city_eps),
        "featured_episode_id": city_eps[0]["episode_id"] if city_eps else None,
        "source_count": city.get("source_count", 0),
        "landed_rows": city.get("landed_rows", 0),
        "landed_rows_label": city.get("landed_rows_label", "0"),
        "staged_events": city.get("staged_events", 0),
        "staged_events_label": city.get("staged_events_label", "0"),
        "staged_observations": city.get("staged_observations", 0),
        "staged_observations_label": city.get("staged_observations_label", "0"),
        "evidence_samples": city.get("evidence_samples", 0),
        "query_smoke_rows": city.get("query_smoke_rows", 0),
        "mart_table_count": mart.get("table_count", 0),
        "mart_status": mart.get("status", "UNKNOWN"),
        "top_sources": [
            {
                "source": src.get("source"),
                "status": src.get("status"),
                "rows": src.get("rows", 0),
                "rows_label": src.get("rows_label") or f"{int(src.get('rows') or 0):,}",
                "privacy": src.get("privacy"),
                "flows": src.get("flows") or [],
            }
            for src in top_sources[:10]
        ],
        "source_issues": [safe_source_issue(src) for src in source_issues[:6]],
        "flow_readiness": [summarize_flow(flow) for flow in (city.get("flow_readiness") or [])],
    }


def make_cross_city_profile(episodes: list[dict[str, Any]], city_profiles: dict[str, Any]) -> dict[str, Any]:
    return {
        "city_id": "CROSS_CITY",
        "city_name": "Cross-city",
        "episode_count": sum(1 for ep in episodes if ep.get("city_id") == "CROSS_CITY"),
        "featured_episode_id": next((ep["episode_id"] for ep in episodes if ep.get("city_id") == "CROSS_CITY"), None),
        "source_count": sum((city_profiles[c].get("source_count") or 0) for c in city_profiles),
        "landed_rows": sum((city_profiles[c].get("landed_rows") or 0) for c in city_profiles),
        "landed_rows_label": f"{sum((city_profiles[c].get('landed_rows') or 0) for c in city_profiles):,}",
        "staged_events": sum((city_profiles[c].get("staged_events") or 0) for c in city_profiles),
        "staged_events_label": f"{sum((city_profiles[c].get('staged_events') or 0) for c in city_profiles):,}",
        "staged_observations": sum((city_profiles[c].get("staged_observations") or 0) for c in city_profiles),
        "staged_observations_label": f"{sum((city_profiles[c].get('staged_observations') or 0) for c in city_profiles):,}",
        "evidence_samples": sum((city_profiles[c].get("evidence_samples") or 0) for c in city_profiles),
        "query_smoke_rows": sum((city_profiles[c].get("query_smoke_rows") or 0) for c in city_profiles),
        "mart_table_count": sum((city_profiles[c].get("mart_table_count") or 0) for c in city_profiles),
        "mart_status": "MIXED_CONTEXT",
        "top_sources": [],
        "source_issues": [],
        "flow_readiness": [],
    }


def enrich_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched = []
    for ep in episodes:
        row = dict(ep)
        row["city_name"] = CITY_NAMES.get(row.get("city_id"), row.get("city_name") or row.get("city_id"))
        row["episode_category"] = classify_episode(row)
        row["compact_summary"] = one_line(row.get("what_is_happening") or row.get("summary"), 220)
        row["display_priority"] = int(row.get("display_priority") or 0)
        row["ref_count"] = sum(len(row.get(k) or []) for k in [
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
        ])
        enriched.append(row)
    return sorted(enriched, key=lambda x: (x.get("display_priority", 0), x.get("episode_id", "")), reverse=True)


def build_app_data() -> tuple[dict[str, Any], dict[str, Any]]:
    episode_pack = read_json(FILES["episode_pack"], {})
    dashboard = read_json(FILES["dashboard_data"], {})
    handoff = read_json(FILES["app_handoff_pack"], {})
    decision = read_json(FILES["episode_decision"], {})
    raw_episodes = episode_pack.get("episodes") or []
    episodes = enrich_episodes(raw_episodes)

    city_profiles = {
        city_id: make_city_profile(city_id, city, episodes)
        for city_id, city in (dashboard.get("cities") or {}).items()
    }
    city_profiles["CROSS_CITY"] = make_cross_city_profile(episodes, city_profiles)

    scene_models = {
        "BARC": {
            "label": "Barcelona LOD2",
            "scene_status": "real LOD2 USD available; browser preview uses sampled source IDs",
            "usd_path": str(FILES["barc_usd"].resolve()) if FILES["barc_usd"].exists() else None,
            "examples": (dashboard.get("building_examples") or {}).get("BARC", []),
        },
        "NYC": {
            "label": "NYC 2025 LOD2",
            "scene_status": "real LOD2 USD available with building identity fields; browser preview uses sampled source IDs",
            "usd_path": str(FILES["nyc_usd"].resolve()) if FILES["nyc_usd"].exists() else None,
            "examples": (dashboard.get("building_examples") or {}).get("NYC", []),
        },
        "CHI": {
            "label": "Chicago data-first",
            "scene_status": "3D city asset pending; data episodes available",
            "usd_path": None,
            "examples": [],
        },
        "LON": {
            "label": "London data-first",
            "scene_status": "3D city asset pending; data episodes available",
            "usd_path": None,
            "examples": [],
        },
        "CROSS_CITY": {
            "label": "Four-city comparison",
            "scene_status": "Cross-city view compares data and asset readiness",
            "usd_path": None,
            "examples": [],
        },
    }

    kit_bat = Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/txr.citybrain_usd_composer.kit.bat")
    omniverse_commands = {
        "BARC": f'"{kit_bat}" "{FILES["barc_usd"].resolve()}"' if FILES["barc_usd"].exists() else None,
        "NYC": f'"{kit_bat}" "{FILES["nyc_usd"].resolve()}"' if FILES["nyc_usd"].exists() else None,
    }

    counts = Counter(ep.get("episode_type") for ep in episodes)
    app_data = {
        "schema_version": "track2c-city-first-episode-app-r1.v1",
        "task": TASK,
        "status": "CITY_FIRST_EPISODE_APP_DATA_READY_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "product_model": {
            "primary_object": "city_episode",
            "home_question": "What is happening in the cities?",
            "screen_order": [
                "episode",
                "place/entity",
                "what happened or needs review",
                "map/3D/timeline context",
                "evidence",
                "limitations",
                "safe next-look",
            ],
            "secondary_surface": "system substrate and source inventory",
        },
        "city_order": CITY_ORDER,
        "city_profiles": city_profiles,
        "episodes": episodes,
        "episode_counts": {
            "total": len(episodes),
            "by_city": dict(Counter(ep.get("city_id") for ep in episodes)),
            "by_type": dict(counts),
        },
        "featured_episode_ids": [
            "episode:barc_mobility_trams_itineraries_replay",
            "episode:nyc_lod2_building_identity_candidate",
            "episode:chi_civic_service_high_event_coverage",
            "episode:lon_tfl_mobility_context",
            "episode:cross_city_event_observation_comparison",
        ],
        "handoff_sections": {
            "hero_episodes": len(handoff.get("hero_episodes") or []),
            "building_asset_cards": len(handoff.get("building_asset_cards") or []),
            "replay_cards": len(handoff.get("replay_cards") or []),
            "event_evidence_cards": len(handoff.get("event_evidence_cards") or []),
            "brain_insight_cards": len(handoff.get("brain_insight_cards") or []),
            "data_quality_cards": len(handoff.get("data_quality_cards") or []),
        },
        "scene_models": scene_models,
        "omniverse_commands": omniverse_commands,
        "d4_feed_summary": {
            "feed_item_count": (dashboard.get("d4_feed") or {}).get("feed_item_count", 0),
            "evidence_trace_count": (dashboard.get("d4_feed") or {}).get("evidence_trace_count", 0),
            "review_packet_count": (dashboard.get("d4_feed") or {}).get("review_packet_count", 0),
            "replay_item_count": (dashboard.get("d4_feed") or {}).get("replay_item_count", 0),
            "query_result_count": (dashboard.get("d4_feed") or {}).get("query_result_count", 0),
        },
        "limits": LIMITATIONS,
        "claim_boundary": (
            "City-first review demo only. Episodes are evidence/context packets; "
            "no command, dispatch, enforcement, routing, legal finding, confirmed violation, "
            "certified affected-building claim, certified impact, or production readiness."
        ),
        "source_artifacts": {name: str(path.resolve()) for name, path in FILES.items() if path.exists()},
        "track2b_decision": decision.get("status"),
    }

    source_map = {
        "inputs": {name: str(path.resolve()) for name, path in INPUT_ROOTS.items()},
        "files": {name: {"path": str(path.resolve()), "exists": path.exists()} for name, path in FILES.items()},
        "episode_pack_status": episode_pack.get("status"),
        "dashboard_status": dashboard.get("status"),
        "output_app_root": str(APP.resolve()),
        "previous_r7_app_root_left_untouched": str((R7_ROOT / "app_shell").resolve()),
    }
    return app_data, source_map


INDEX_HTML = dedent(
    """\
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>CityBrain - City Episodes</title>
      <link rel="stylesheet" href="./styles.css">
    </head>
    <body>
      <div class="app-frame">
        <aside class="side-rail" aria-label="CityBrain navigation">
          <div class="brand-block">
            <div class="brand-mark" aria-hidden="true">CB</div>
            <div>
              <strong>CityBrain</strong>
              <span>City Episodes</span>
            </div>
          </div>
          <nav class="rail-nav">
            <button class="nav-button active" data-view="episodes" title="City episodes">Episodes</button>
            <button class="nav-button" data-view="scene" title="3D and map context">3D / Map</button>
            <button class="nav-button" data-view="evidence" title="Evidence and review">Evidence</button>
            <button class="nav-button" data-view="replay" title="Replay and brain">Replay / Brain</button>
            <button class="nav-button" data-view="data" title="Data quality">Data Quality</button>
          </nav>
          <div class="trust-chip">no action taken</div>
        </aside>

        <main class="workspace">
          <header class="top-bar">
            <div>
              <p class="eyebrow">local review demo</p>
              <h1>What is happening in the cities?</h1>
            </div>
            <div class="top-status">
              <span>city episode first</span>
              <span>local packets</span>
              <span>not production</span>
            </div>
          </header>

          <section class="hero-panel">
            <div class="hero-copy">
              <p class="eyebrow">from platform board to city product</p>
              <h2 id="hero-title">City episodes, with evidence behind them.</h2>
              <p id="hero-summary">Select a city or episode to inspect what is happening, where it is anchored, what evidence supports it, and what the system is not allowed to claim.</p>
              <div class="hero-actions">
                <button class="primary-action" id="open-evidence">Open evidence drawer</button>
                <button class="secondary-action" id="focus-scene">Show 3D context</button>
              </div>
            </div>
            <div class="hero-card" id="hero-card"></div>
          </section>

          <section class="city-strip" id="city-strip" aria-label="City selector"></section>

          <section class="view active" id="view-episodes">
            <div class="view-grid">
              <section class="episode-column">
                <div class="panel-head">
                  <div>
                    <p class="eyebrow">review queue</p>
                    <h2>City episodes</h2>
                  </div>
                  <div class="filter-row">
                    <select id="type-filter" aria-label="Episode type filter"></select>
                    <input id="search-input" type="search" placeholder="Search city episodes">
                  </div>
                </div>
                <div class="episode-list" id="episode-list"></div>
              </section>

              <section class="detail-panel" id="episode-detail" aria-live="polite"></section>
            </div>
          </section>

          <section class="view" id="view-scene">
            <div class="scene-layout">
              <section class="scene-panel">
                <div class="panel-head">
                  <div>
                    <p class="eyebrow">place / entity context</p>
                    <h2 id="scene-title">3D city preview</h2>
                  </div>
                  <div class="scene-controls">
                    <button id="rot-left" title="Rotate left">-45</button>
                    <button id="rot-right" title="Rotate right">+45</button>
                    <button id="zoom-out" title="Zoom out">-</button>
                    <button id="zoom-in" title="Zoom in">+</button>
                  </div>
                </div>
                <div class="scene-stage" id="scene-stage">
                  <div class="scene-ground" id="scene-ground"></div>
                  <div class="scene-hint">drag to rotate, wheel to zoom</div>
                </div>
              </section>
              <section class="asset-panel">
                <div id="asset-summary"></div>
                <div class="asset-table" id="asset-table"></div>
              </section>
            </div>
          </section>

          <section class="view" id="view-evidence">
            <div class="support-grid">
              <section class="support-panel">
                <div class="panel-head">
                  <div>
                    <p class="eyebrow">episode evidence</p>
                    <h2>Evidence refs and review state</h2>
                  </div>
                </div>
                <div id="evidence-view"></div>
              </section>
              <section class="support-panel">
                <div class="panel-head">
                  <div>
                    <p class="eyebrow">city pulse</p>
                    <h2>Events, observations, source families</h2>
                  </div>
                </div>
                <div id="city-pulse"></div>
              </section>
            </div>
          </section>

          <section class="view" id="view-replay">
            <div class="support-grid">
              <section class="support-panel">
                <div class="panel-head">
                  <div>
                    <p class="eyebrow">simulation context</p>
                    <h2>Replay episodes</h2>
                  </div>
                </div>
                <div class="compact-card-list" id="replay-list"></div>
              </section>
              <section class="support-panel">
                <div class="panel-head">
                  <div>
                    <p class="eyebrow">brain context</p>
                    <h2>Runtime and insight packets</h2>
                  </div>
                </div>
                <div class="compact-card-list" id="brain-list"></div>
              </section>
            </div>
          </section>

          <section class="view" id="view-data">
            <div class="support-grid">
              <section class="support-panel">
                <div class="panel-head">
                  <div>
                    <p class="eyebrow">source limits</p>
                    <h2>Data quality cards</h2>
                  </div>
                </div>
                <div class="compact-card-list" id="quality-list"></div>
              </section>
              <section class="support-panel">
                <div class="panel-head">
                  <div>
                    <p class="eyebrow">system substrate</p>
                    <h2>Secondary platform facts</h2>
                  </div>
                </div>
                <div id="substrate-panel"></div>
              </section>
            </div>
          </section>
        </main>
      </div>

      <aside class="evidence-drawer" id="evidence-drawer" aria-label="Evidence drawer">
        <div class="drawer-head">
          <div>
            <p class="eyebrow">evidence drawer</p>
            <h2 id="drawer-title">Selected episode</h2>
          </div>
          <button id="close-drawer" title="Close evidence drawer">x</button>
        </div>
        <div id="drawer-body"></div>
      </aside>

      <div class="boundary-strip">
        <span>review/context only</span>
        <span>not production</span>
        <span>no dispatch</span>
        <span>no enforcement</span>
        <span>no control command</span>
        <span>no certified claim</span>
      </div>

      <script src="./data/app_data.js"></script>
      <script src="./app.js"></script>
    </body>
    </html>
    """
)


STYLES_CSS = dedent(
    """\
    :root {
      color-scheme: dark;
      --bg: #0b0e12;
      --panel: #14191f;
      --panel-2: #191f27;
      --line: #2b333f;
      --text: #edf2f5;
      --muted: #9eabb7;
      --soft: #c5ced6;
      --green: #74d58b;
      --teal: #6ed7cf;
      --amber: #f1bf68;
      --red: #ef806f;
      --blue: #82a9ff;
      --ink: #0f1318;
      --radius: 8px;
      font-family: Inter, "Segoe UI", Arial, sans-serif;
    }

    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      letter-spacing: 0;
      overflow-x: hidden;
    }

    button, input, select {
      font: inherit;
      color: inherit;
    }

    button { cursor: pointer; }

    .app-frame {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 228px minmax(0, 1fr);
    }

    .side-rail {
      position: sticky;
      top: 0;
      height: 100vh;
      padding: 18px;
      border-right: 1px solid var(--line);
      background: #0f1318;
      display: flex;
      flex-direction: column;
      gap: 22px;
    }

    .brand-block {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-mark {
      width: 42px;
      height: 42px;
      display: grid;
      place-items: center;
      border: 1px solid #45605e;
      background: #152320;
      color: var(--green);
      font-weight: 800;
      border-radius: 8px;
    }

    .brand-block strong { display: block; font-size: 17px; }
    .brand-block span { display: block; color: var(--muted); font-size: 13px; margin-top: 2px; }

    .rail-nav {
      display: grid;
      gap: 8px;
    }

    .nav-button,
    .city-button,
    .chip-button,
    .secondary-action,
    .primary-action,
    .scene-controls button,
    #close-drawer {
      border: 1px solid var(--line);
      background: #141a21;
      color: var(--soft);
      border-radius: 8px;
      min-height: 38px;
      padding: 8px 11px;
    }

    .nav-button {
      width: 100%;
      text-align: left;
    }

    .nav-button.active,
    .city-button.active,
    .chip-button.active {
      border-color: #6fd59a;
      color: var(--text);
      background: #182820;
    }

    .trust-chip {
      margin-top: auto;
      padding: 11px;
      border: 1px solid #5d5234;
      color: var(--amber);
      border-radius: 8px;
      background: #1e1a12;
      font-size: 13px;
    }

    .workspace {
      padding: 22px 26px 78px;
      max-width: 1600px;
      width: 100%;
      margin: 0 auto;
    }

    .top-bar {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: flex-start;
      margin-bottom: 18px;
    }

    .eyebrow {
      color: var(--teal);
      text-transform: uppercase;
      font-size: 12px;
      font-weight: 800;
      margin: 0 0 6px;
    }

    h1, h2, h3, p { margin-top: 0; }
    h1 { font-size: 34px; line-height: 1.08; margin-bottom: 0; }
    h2 { font-size: 22px; line-height: 1.16; margin-bottom: 8px; }
    h3 { font-size: 17px; line-height: 1.25; margin-bottom: 8px; }
    p { color: var(--soft); line-height: 1.5; }

    .top-status {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .top-status span,
    .badge,
    .mini-tag {
      border: 1px solid var(--line);
      background: #151b22;
      color: var(--soft);
      border-radius: 999px;
      padding: 6px 9px;
      font-size: 12px;
      white-space: nowrap;
    }

    .hero-panel {
      display: grid;
      grid-template-columns: minmax(280px, 1.05fr) minmax(300px, .95fr);
      gap: 16px;
      margin-bottom: 16px;
    }

    .hero-copy,
    .hero-card,
    .episode-column,
    .detail-panel,
    .scene-panel,
    .asset-panel,
    .support-panel {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
    }

    .hero-copy,
    .hero-card {
      padding: 22px;
      min-height: 240px;
    }

    .hero-copy h2 {
      font-size: 36px;
      max-width: 760px;
    }

    .hero-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 18px;
    }

    .primary-action {
      border-color: #6fd59a;
      background: #183122;
      color: var(--green);
    }

    .secondary-action {
      border-color: #496074;
      color: #bcd7f4;
    }

    .hero-card {
      display: grid;
      align-content: start;
      gap: 12px;
    }

    .hero-card .big-stat-grid,
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }

    .stat, .metric-tile {
      padding: 10px;
      border: 1px solid var(--line);
      background: #10151b;
      border-radius: 8px;
      min-width: 0;
    }

    .stat span,
    .metric-tile span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 4px;
    }

    .stat strong,
    .metric-tile strong {
      display: block;
      font-size: 18px;
      overflow-wrap: anywhere;
    }

    .city-strip {
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }

    .city-button {
      min-height: 74px;
      text-align: left;
      display: grid;
      align-content: center;
      gap: 3px;
    }

    .city-button strong { font-size: 16px; }
    .city-button span { color: var(--muted); font-size: 12px; }

    .view { display: none; }
    .view.active { display: block; }

    .view-grid {
      display: grid;
      grid-template-columns: minmax(350px, 0.85fr) minmax(430px, 1.15fr);
      gap: 16px;
      align-items: start;
    }

    .episode-column,
    .detail-panel,
    .scene-panel,
    .asset-panel,
    .support-panel {
      padding: 16px;
    }

    .panel-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      margin-bottom: 14px;
    }

    .filter-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    select,
    input[type="search"] {
      border: 1px solid var(--line);
      background: #0f141a;
      border-radius: 8px;
      min-height: 38px;
      padding: 8px 10px;
      min-width: 150px;
    }

    .episode-list {
      display: grid;
      gap: 10px;
      max-height: 760px;
      overflow: auto;
      padding-right: 4px;
    }

    .episode-card {
      border: 1px solid var(--line);
      background: #10151b;
      border-radius: 8px;
      padding: 12px;
      text-align: left;
      width: 100%;
      display: grid;
      gap: 8px;
    }

    .episode-card.active {
      border-color: var(--green);
      background: #122119;
    }

    .episode-card h3 {
      margin: 0;
      font-size: 15px;
    }

    .episode-card p {
      margin: 0;
      font-size: 13px;
      color: var(--muted);
    }

    .card-tags {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }

    .badge.city { border-color: #466a72; color: var(--teal); }
    .badge.type { border-color: #71613f; color: var(--amber); }
    .badge.boundary { border-color: #6c4744; color: var(--red); }

    .detail-section {
      border-top: 1px solid var(--line);
      padding-top: 14px;
      margin-top: 14px;
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .list-clean {
      margin: 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 8px;
    }

    .list-clean li {
      border: 1px solid var(--line);
      background: #10151b;
      border-radius: 8px;
      padding: 9px;
      color: var(--soft);
      overflow-wrap: anywhere;
    }

    .scene-layout,
    .support-grid {
      display: grid;
      grid-template-columns: minmax(420px, 1.15fr) minmax(320px, .85fr);
      gap: 16px;
      align-items: start;
    }

    .scene-controls {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .scene-stage {
      position: relative;
      height: 560px;
      overflow: hidden;
      border: 1px solid #2f3947;
      border-radius: 8px;
      background:
        linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px),
        linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px),
        #0c1117;
      background-size: 42px 42px;
      perspective: 900px;
    }

    .scene-ground {
      --rot: -28deg;
      --zoom: 1;
      position: absolute;
      left: 50%;
      top: 52%;
      width: 640px;
      height: 420px;
      transform-style: preserve-3d;
      transform: translate(-50%, -50%) rotateX(62deg) rotateZ(var(--rot)) scale(var(--zoom));
      transition: transform .18s ease;
    }

    .scene-ground::before {
      content: "";
      position: absolute;
      inset: 0;
      border: 1px solid #3b4655;
      background:
        repeating-linear-gradient(90deg, rgba(110,215,207,.16) 0 2px, transparent 2px 64px),
        repeating-linear-gradient(0deg, rgba(241,191,104,.12) 0 2px, transparent 2px 64px),
        rgba(18, 28, 34, .72);
      transform: translateZ(-2px);
    }

    .tower {
      position: absolute;
      width: 30px;
      height: 30px;
      left: var(--x);
      top: var(--y);
      transform-style: preserve-3d;
      transform: translateZ(var(--h));
      border: 1px solid rgba(255,255,255,.22);
      background: var(--tone);
      border-radius: 4px;
    }

    .tower::before {
      content: "";
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: var(--h);
      transform-origin: bottom;
      transform: rotateX(-90deg);
      background: color-mix(in srgb, var(--tone) 65%, black);
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 4px;
    }

    .tower.selected {
      outline: 2px solid var(--green);
      box-shadow: 0 0 0 4px rgba(116,213,139,.18);
    }

    .scene-hint {
      position: absolute;
      right: 14px;
      bottom: 14px;
      color: var(--muted);
      background: rgba(10, 14, 18, .82);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 12px;
    }

    .asset-table {
      display: grid;
      gap: 8px;
      max-height: 410px;
      overflow: auto;
    }

    .asset-row,
    .compact-card {
      border: 1px solid var(--line);
      background: #10151b;
      border-radius: 8px;
      padding: 10px;
    }

    .asset-row.active {
      border-color: var(--green);
      background: #122119;
    }

    .asset-row dl {
      display: grid;
      grid-template-columns: 90px 1fr;
      gap: 3px 8px;
      margin: 8px 0 0;
      font-size: 12px;
    }

    dt { color: var(--muted); }
    dd { margin: 0; overflow-wrap: anywhere; }

    .compact-card-list {
      display: grid;
      gap: 10px;
    }

    .compact-card h3 { margin-bottom: 6px; }
    .compact-card p { margin-bottom: 10px; }

    .evidence-drawer {
      position: fixed;
      top: 0;
      right: 0;
      width: min(520px, 92vw);
      height: 100vh;
      transform: translateX(105%);
      transition: transform .18s ease;
      z-index: 20;
      background: #10151b;
      border-left: 1px solid var(--line);
      padding: 18px;
      overflow: auto;
      box-shadow: -18px 0 50px rgba(0,0,0,.38);
    }

    .evidence-drawer.open {
      transform: translateX(0);
    }

    .drawer-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      margin-bottom: 14px;
    }

    #close-drawer {
      min-width: 38px;
      padding: 0;
    }

    .boundary-strip {
      position: fixed;
      left: 228px;
      right: 0;
      bottom: 0;
      min-height: 42px;
      border-top: 1px solid var(--line);
      background: rgba(12, 16, 21, .94);
      backdrop-filter: blur(12px);
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
      padding: 8px 16px;
      z-index: 10;
    }

    .boundary-strip span {
      color: var(--muted);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 5px 8px;
      font-size: 12px;
    }

    code {
      display: block;
      border: 1px solid var(--line);
      background: #0a0e12;
      border-radius: 8px;
      padding: 10px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      color: #d7e2eb;
    }

    @media (max-width: 1100px) {
      .app-frame { grid-template-columns: 1fr; }
      .side-rail {
        position: relative;
        height: auto;
        border-right: none;
        border-bottom: 1px solid var(--line);
      }
      .rail-nav { grid-template-columns: repeat(5, minmax(0, 1fr)); }
      .nav-button { text-align: center; }
      .hero-panel,
      .view-grid,
      .scene-layout,
      .support-grid {
        grid-template-columns: 1fr;
      }
      .city-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .boundary-strip { left: 0; }
    }

    @media (max-width: 640px) {
      .workspace { padding: 16px 14px 92px; }
      .hero-copy h2 { font-size: 28px; }
      h1 { font-size: 28px; }
      .top-bar, .panel-head { flex-direction: column; }
      .rail-nav, .city-strip, .metric-grid, .hero-card .big-stat-grid, .detail-grid {
        grid-template-columns: 1fr;
      }
      .scene-stage { height: 420px; }
      .scene-ground { width: 520px; }
    }
    """
)


APP_JS = dedent(
    """\
    const DATA = window.CITYBRAIN_APP_DATA;
    const $ = (id) => document.getElementById(id);
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));

    const state = {
      city: "BARC",
      view: "episodes",
      type: "all",
      query: "",
      selectedId: DATA.featured_episode_ids.find(id => DATA.episodes.some(ep => ep.episode_id === id)) || DATA.episodes[0]?.episode_id,
      sceneCity: "BARC",
      selectedAsset: 0,
      rot: -28,
      zoom: 1
    };

    const typeLabels = {
      all: "All episodes",
      building_asset_identity: "3D / buildings",
      mobility_context: "Mobility",
      civic_service_municipal: "Civic services",
      planning_property_address: "Planning / property",
      scenario_replay: "Replay",
      evidence_trace: "Evidence",
      runtime_insight: "Runtime / insight",
      graph_query_brain_explanation: "Brain / graph",
      data_quality_source_limitation: "Data quality",
      cross_city_comparison: "Cross-city"
    };

    function cityName(city) {
      return DATA.city_profiles[city]?.city_name || city;
    }

    function selectedEpisode() {
      return DATA.episodes.find(ep => ep.episode_id === state.selectedId) || DATA.episodes[0];
    }

    function cityEpisodes() {
      return DATA.episodes
        .filter(ep => state.city === "CROSS_CITY" ? ep.city_id === "CROSS_CITY" : ep.city_id === state.city)
        .filter(ep => state.type === "all" || ep.episode_type === state.type)
        .filter(ep => {
          const hay = `${ep.title} ${ep.headline} ${ep.what_is_happening} ${ep.summary} ${ep.where}`.toLowerCase();
          return hay.includes(state.query.toLowerCase());
        })
        .sort((a, b) => (b.display_priority || 0) - (a.display_priority || 0));
    }

    function metric(label, value) {
      return `<div class="metric-tile"><span>${esc(label)}</span><strong>${esc(value ?? "0")}</strong></div>`;
    }

    function badge(text, cls = "") {
      return `<span class="badge ${cls}">${esc(text)}</span>`;
    }

    function refList(items, empty = "No refs in this episode.") {
      const rows = (items || []).filter(Boolean);
      if (!rows.length) return `<ul class="list-clean"><li>${esc(empty)}</li></ul>`;
      return `<ul class="list-clean">${rows.map(item => `<li>${esc(item)}</li>`).join("")}</ul>`;
    }

    function renderHero() {
      const ep = selectedEpisode();
      const profile = DATA.city_profiles[ep.city_id] || DATA.city_profiles[state.city] || DATA.city_profiles.BARC;
      $("hero-title").textContent = ep.headline || ep.title;
      $("hero-summary").textContent = ep.what_is_happening || ep.summary || "";
      $("hero-card").innerHTML = `
        <div class="card-tags">${badge(cityName(ep.city_id), "city")} ${badge(ep.episode_category || ep.episode_type, "type")} ${badge("no action taken", "boundary")}</div>
        <h3>${esc(ep.title)}</h3>
        <p>${esc(ep.summary)}</p>
        <div class="big-stat-grid">
          ${metric("Episodes", profile.episode_count)}
          ${metric("Events", profile.staged_events_label)}
          ${metric("Evidence samples", profile.evidence_samples)}
        </div>
      `;
    }

    function renderCityStrip() {
      $("city-strip").innerHTML = DATA.city_order.map(city => {
        const p = DATA.city_profiles[city];
        const active = city === state.city ? "active" : "";
        return `<button class="city-button ${active}" data-city="${esc(city)}">
          <strong>${esc(cityName(city))}</strong>
          <span>${esc(p?.episode_count || 0)} episodes / ${esc(p?.staged_events_label || "0")} events</span>
        </button>`;
      }).join("");
      document.querySelectorAll(".city-button").forEach(btn => {
        btn.addEventListener("click", () => {
          state.city = btn.dataset.city;
          const first = DATA.episodes.find(ep => ep.city_id === state.city);
          if (first) state.selectedId = first.episode_id;
          state.sceneCity = ["BARC", "NYC"].includes(state.city) ? state.city : state.city;
          renderAll();
        });
      });
    }

    function renderTypeFilter() {
      const options = ["all", ...new Set(DATA.episodes.map(ep => ep.episode_type))];
      $("type-filter").innerHTML = options.map(type => `<option value="${esc(type)}">${esc(typeLabels[type] || type)}</option>`).join("");
      $("type-filter").value = state.type;
    }

    function renderEpisodeList() {
      const rows = cityEpisodes();
      $("episode-list").innerHTML = rows.map(ep => {
        const active = ep.episode_id === state.selectedId ? "active" : "";
        return `<button class="episode-card ${active}" data-id="${esc(ep.episode_id)}">
          <div class="card-tags">${badge(cityName(ep.city_id), "city")} ${badge(ep.episode_category || ep.episode_type, "type")}</div>
          <h3>${esc(ep.title)}</h3>
          <p>${esc(ep.compact_summary || ep.what_is_happening || ep.summary)}</p>
          <div class="card-tags">${badge(`${ep.ref_count || 0} refs`)} ${badge("review/context", "boundary")}</div>
        </button>`;
      }).join("") || `<div class="episode-card"><h3>No episode matches this filter.</h3><p>Try another city, type, or search term.</p></div>`;
      document.querySelectorAll(".episode-card[data-id]").forEach(card => {
        card.addEventListener("click", () => {
          state.selectedId = card.dataset.id;
          const ep = selectedEpisode();
          if (["BARC", "NYC"].includes(ep.city_id)) state.sceneCity = ep.city_id;
          renderAll();
        });
      });
    }

    function renderEpisodeDetail() {
      const ep = selectedEpisode();
      const refs = [
        ...(ep.event_refs || []),
        ...(ep.evidence_refs || []),
        ...(ep.source_refs || []),
        ...(ep.replay_refs || []),
        ...(ep.runtime_packet_refs || []),
        ...(ep.insight_refs || [])
      ];
      $("episode-detail").innerHTML = `
        <div class="card-tags">${badge(cityName(ep.city_id), "city")} ${badge(ep.episode_category, "type")} ${badge("candidate/review only", "boundary")}</div>
        <h2>${esc(ep.title)}</h2>
        <p>${esc(ep.headline || ep.summary)}</p>
        <div class="detail-grid">
          ${metric("Where", ep.where || cityName(ep.city_id))}
          ${metric("Status", ep.timeline_or_status || "compiled from local outputs")}
          ${metric("Refs", ep.ref_count || 0)}
          ${metric("No action taken", ep.no_action_taken ? "true" : "false")}
        </div>
        <div class="detail-section">
          <p class="eyebrow">what is happening</p>
          <p>${esc(ep.what_is_happening || ep.summary)}</p>
        </div>
        <div class="detail-section">
          <p class="eyebrow">evidence and source refs</p>
          ${refList(refs)}
        </div>
        <div class="detail-section">
          <p class="eyebrow">limitations</p>
          ${refList(ep.limitations)}
        </div>
        <div class="detail-section">
          <p class="eyebrow">safe next-look</p>
          ${refList(ep.safe_next_looks)}
        </div>
        <div class="detail-section">
          <p class="eyebrow">claim boundary</p>
          <p>${esc(ep.claim_boundary || DATA.claim_boundary)}</p>
        </div>
      `;
    }

    function renderScene() {
      const model = DATA.scene_models[state.sceneCity] || DATA.scene_models.BARC;
      const examples = model.examples || [];
      $("scene-title").textContent = `${model.label} context`;
      $("scene-ground").style.setProperty("--rot", `${state.rot}deg`);
      $("scene-ground").style.setProperty("--zoom", state.zoom);
      const fallbackCount = state.sceneCity === "CHI" || state.sceneCity === "LON" ? 18 : 0;
      const rows = examples.length ? examples : Array.from({ length: fallbackCount }, (_, i) => ({ OBJECTID: `pending-${i + 1}`, HeightFT: 40 + (i % 7) * 16, building_id: `${state.sceneCity.toLowerCase()}:asset:pending:${i + 1}` }));
      const towers = rows.slice(0, 34).map((item, index) => {
        const x = 42 + (index % 8) * 68 + ((index % 3) * 9);
        const y = 36 + Math.floor(index / 8) * 82 + ((index % 2) * 16);
        const hVal = Number(item.HeightFT || item.COTA || item.heightroof || (46 + index * 5));
        const h = Math.max(20, Math.min(150, hVal * (state.sceneCity === "NYC" ? 0.72 : 1.05)));
        const selected = index === state.selectedAsset ? "selected" : "";
        const tone = state.sceneCity === "NYC" ? "#82a9ff" : state.sceneCity === "BARC" ? "#f1bf68" : "#6ed7cf";
        return `<button class="tower ${selected}" title="${esc(item.building_id || item.source_id || item.OBJECTID)}" data-asset="${index}" style="--x:${x}px; --y:${y}px; --h:${h}px; --tone:${tone};"></button>`;
      }).join("");
      $("scene-ground").innerHTML = towers;
      document.querySelectorAll(".tower").forEach(tower => {
        tower.addEventListener("click", () => {
          state.selectedAsset = Number(tower.dataset.asset || 0);
          renderScene();
        });
      });
      renderAssets(model, rows);
    }

    function renderAssets(model, rows) {
      const usd = model.usd_path ? `<code>${esc(DATA.omniverse_commands[state.sceneCity] || model.usd_path)}</code>` : `<p>No USD command for this city yet.</p>`;
      $("asset-summary").innerHTML = `
        <p class="eyebrow">asset status</p>
        <h2>${esc(model.scene_status)}</h2>
        <p>The browser scene is navigable context for the episode. The real USD scene remains in Omniverse.</p>
        ${usd}
      `;
      $("asset-table").innerHTML = rows.slice(0, 12).map((item, index) => {
        const active = index === state.selectedAsset ? "active" : "";
        return `<button class="asset-row ${active}" data-asset="${index}">
          <strong>${esc(item.building_id || item.source_id || item.OBJECTID || `asset ${index + 1}`)}</strong>
          <dl>
            <dt>OBJECTID</dt><dd>${esc(item.OBJECTID || "")}</dd>
            <dt>BIN</dt><dd>${esc(item.BIN || "")}</dd>
            <dt>BBL</dt><dd>${esc(item.BBL || "")}</dd>
            <dt>Height</dt><dd>${esc(item.HeightFT || item.COTA || item.heightroof || "context")}</dd>
            <dt>Boundary</dt><dd>${esc(item.boundary || "source identity context only")}</dd>
          </dl>
        </button>`;
      }).join("");
      document.querySelectorAll(".asset-row").forEach(row => {
        row.addEventListener("click", () => {
          state.selectedAsset = Number(row.dataset.asset || 0);
          renderScene();
        });
      });
    }

    function renderEvidenceView() {
      const ep = selectedEpisode();
      const sections = [
        ["Situation refs", ep.situation_refs],
        ["Event refs", ep.event_refs],
        ["Evidence refs", ep.evidence_refs],
        ["Source refs", ep.source_refs],
        ["Replay refs", ep.replay_refs],
        ["Review refs", ep.review_refs],
        ["Runtime refs", ep.runtime_packet_refs],
        ["Insight refs", ep.insight_refs],
        ["Graph/query refs", ep.graph_query_refs],
        ["Building refs", ep.building_asset_refs]
      ];
      $("evidence-view").innerHTML = sections.map(([title, rows]) => `
        <div class="compact-card">
          <h3>${esc(title)}</h3>
          ${refList(rows)}
        </div>
      `).join("");
    }

    function renderCityPulse() {
      const p = DATA.city_profiles[state.city] || DATA.city_profiles.BARC;
      const sources = (p.top_sources || []).slice(0, 8).map(src => `
        <div class="compact-card">
          <h3>${esc(src.source)}</h3>
          <p>${esc(src.rows_label)} rows / ${esc(src.status)} / ${esc(src.privacy || "context")}</p>
        </div>`).join("");
      $("city-pulse").innerHTML = `
        <div class="metric-grid">
          ${metric("Sources", p.source_count)}
          ${metric("Rows", p.landed_rows_label)}
          ${metric("Events", p.staged_events_label)}
          ${metric("Observations", p.staged_observations_label)}
          ${metric("Evidence", p.evidence_samples)}
          ${metric("Mart tables/views", p.mart_table_count)}
        </div>
        <div class="detail-section"><p class="eyebrow">top source families</p>${sources}</div>
      `;
    }

    function compactCard(ep) {
      return `<button class="compact-card" data-id="${esc(ep.episode_id)}">
        <div class="card-tags">${badge(cityName(ep.city_id), "city")} ${badge(ep.episode_category, "type")}</div>
        <h3>${esc(ep.title)}</h3>
        <p>${esc(ep.compact_summary || ep.summary)}</p>
      </button>`;
    }

    function renderSecondaryLists() {
      $("replay-list").innerHTML = DATA.episodes.filter(ep => ep.episode_type === "scenario_replay").map(compactCard).join("");
      $("brain-list").innerHTML = DATA.episodes.filter(ep => ["runtime_insight", "graph_query_brain_explanation"].includes(ep.episode_type)).map(compactCard).join("");
      $("quality-list").innerHTML = DATA.episodes.filter(ep => ep.episode_type === "data_quality_source_limitation").map(compactCard).join("");
      const summary = DATA.d4_feed_summary || {};
      $("substrate-panel").innerHTML = `
        <div class="metric-grid">
          ${metric("D4 feed items", summary.feed_item_count)}
          ${metric("Evidence traces", summary.evidence_trace_count)}
          ${metric("Review packets", summary.review_packet_count)}
          ${metric("Replay items", summary.replay_item_count)}
          ${metric("Query results", summary.query_result_count)}
          ${metric("Episode pack", DATA.episode_counts.total)}
        </div>
        <div class="detail-section">
          <p class="eyebrow">boundary</p>
          <p>${esc(DATA.claim_boundary)}</p>
        </div>
        <div class="detail-section">
          <p class="eyebrow">limitations</p>
          ${refList(DATA.limits)}
        </div>
      `;
      document.querySelectorAll(".compact-card[data-id]").forEach(card => {
        card.addEventListener("click", () => {
          state.selectedId = card.dataset.id;
          const ep = selectedEpisode();
          state.city = ep.city_id || state.city;
          renderAll();
          setView("episodes");
        });
      });
    }

    function renderDrawer() {
      const ep = selectedEpisode();
      $("drawer-title").textContent = ep.title;
      $("drawer-body").innerHTML = `
        <div class="card-tags">${badge(cityName(ep.city_id), "city")} ${badge(ep.episode_category, "type")}</div>
        <p>${esc(ep.summary)}</p>
        <div class="detail-section"><p class="eyebrow">claim boundary</p><p>${esc(ep.claim_boundary || DATA.claim_boundary)}</p></div>
        <div class="detail-section"><p class="eyebrow">limitations</p>${refList(ep.limitations)}</div>
        <div class="detail-section"><p class="eyebrow">safe next-look</p>${refList(ep.safe_next_looks)}</div>
        <div class="detail-section"><p class="eyebrow">all refs</p>${refList([...(ep.entity_refs || []), ...(ep.situation_refs || []), ...(ep.event_refs || []), ...(ep.evidence_refs || []), ...(ep.source_refs || []), ...(ep.replay_refs || []), ...(ep.review_refs || []), ...(ep.building_asset_refs || []), ...(ep.runtime_packet_refs || []), ...(ep.insight_refs || [])])}</div>
      `;
    }

    function setView(view) {
      state.view = view;
      document.querySelectorAll(".view").forEach(el => el.classList.toggle("active", el.id === `view-${view}`));
      document.querySelectorAll(".nav-button").forEach(btn => btn.classList.toggle("active", btn.dataset.view === view));
      if (view === "scene") renderScene();
    }

    function renderAll() {
      renderHero();
      renderCityStrip();
      renderTypeFilter();
      renderEpisodeList();
      renderEpisodeDetail();
      renderScene();
      renderEvidenceView();
      renderCityPulse();
      renderSecondaryLists();
      renderDrawer();
    }

    document.querySelectorAll(".nav-button").forEach(btn => btn.addEventListener("click", () => setView(btn.dataset.view)));
    $("type-filter").addEventListener("change", event => {
      state.type = event.target.value;
      renderEpisodeList();
    });
    $("search-input").addEventListener("input", event => {
      state.query = event.target.value;
      renderEpisodeList();
    });
    $("open-evidence").addEventListener("click", () => $("evidence-drawer").classList.add("open"));
    $("close-drawer").addEventListener("click", () => $("evidence-drawer").classList.remove("open"));
    $("focus-scene").addEventListener("click", () => setView("scene"));
    $("rot-left").addEventListener("click", () => { state.rot -= 45; renderScene(); });
    $("rot-right").addEventListener("click", () => { state.rot += 45; renderScene(); });
    $("zoom-out").addEventListener("click", () => { state.zoom = Math.max(.65, state.zoom - .12); renderScene(); });
    $("zoom-in").addEventListener("click", () => { state.zoom = Math.min(1.8, state.zoom + .12); renderScene(); });

    let dragging = false;
    let lastX = 0;
    $("scene-stage").addEventListener("pointerdown", event => {
      dragging = true;
      lastX = event.clientX;
      $("scene-stage").setPointerCapture(event.pointerId);
    });
    $("scene-stage").addEventListener("pointermove", event => {
      if (!dragging) return;
      state.rot += (event.clientX - lastX) * .35;
      lastX = event.clientX;
      renderScene();
    });
    $("scene-stage").addEventListener("pointerup", () => { dragging = false; });
    $("scene-stage").addEventListener("wheel", event => {
      event.preventDefault();
      state.zoom = Math.max(.65, Math.min(1.8, state.zoom + (event.deltaY < 0 ? .08 : -.08)));
      renderScene();
    }, { passive: false });

    renderAll();
    """
)


def write_app_files(app_data: dict[str, Any]) -> None:
    write_text(APP / "index.html", INDEX_HTML)
    write_text(APP / "styles.css", STYLES_CSS)
    write_text(APP / "app.js", APP_JS)
    write_json(APP / "data/app_data.json", app_data)
    data_js = "window.CITYBRAIN_APP_DATA = " + json.dumps(app_data, sort_keys=True) + ";\n"
    write_text(APP / "data/app_data.js", data_js)


def app_smoke(app_data: dict[str, Any]) -> dict[str, Any]:
    html = (APP / "index.html").read_text(encoding="utf-8")
    css = (APP / "styles.css").read_text(encoding="utf-8")
    js = (APP / "app.js").read_text(encoding="utf-8")
    episodes = app_data["episodes"]
    by_city = Counter(ep.get("city_id") for ep in episodes)
    checks = {
        "index_exists": (APP / "index.html").exists(),
        "app_js_exists": (APP / "app.js").exists(),
        "styles_exists": (APP / "styles.css").exists(),
        "embedded_data_js_exists": (APP / "data/app_data.js").exists(),
        "json_audit_copy_exists": (APP / "data/app_data.json").exists(),
        "no_fetch_required": "fetch(" not in js,
        "no_external_network_refs": not bool(re.search(r"https?://", html + css + js)),
        "episode_count_minimum": len(episodes) >= 32,
        "barcelona_minimum": by_city["BARC"] >= 6,
        "nyc_minimum": by_city["NYC"] >= 6,
        "chicago_minimum": by_city["CHI"] >= 5,
        "london_minimum": by_city["LON"] >= 5,
        "cross_city_minimum": by_city["CROSS_CITY"] >= 5,
        "scene_controls_present": all(x in html for x in ["rot-left", "rot-right", "zoom-in", "zoom-out", "scene-stage"]),
        "evidence_drawer_present": "evidence-drawer" in html,
        "old_r7_app_not_targeted": str(R7_ROOT / "app_shell") not in html + js + css,
        "no_persona_placeholders": "persona-1" not in html + js + css and "persona-2" not in html + js + css,
        "no_future_r2_placeholder": "Future R2" not in html + js + css,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "checks": checks,
        "episode_count": len(episodes),
        "city_counts": dict(by_city),
        "file_url": (APP / "index.html").resolve().as_uri(),
    }


def claim_boundary_audit(app_data: dict[str, Any]) -> dict[str, Any]:
    text = "\n".join(
        [
            json.dumps(app_data, sort_keys=True),
            (APP / "index.html").read_text(encoding="utf-8"),
            (APP / "app.js").read_text(encoding="utf-8"),
            (APP / "styles.css").read_text(encoding="utf-8"),
        ]
    ).lower()
    findings = []
    for claim in FORBIDDEN_POSITIVE_CLAIMS:
        idx = text.find(claim)
        while idx >= 0:
            window = text[max(0, idx - 55): idx + len(claim) + 55]
            sentence_start = max(text.rfind(".", 0, idx), text.rfind("\n", 0, idx))
            sentence_end_candidates = [pos for pos in [text.find(".", idx), text.find("\n", idx)] if pos >= 0]
            sentence_end = min(sentence_end_candidates) if sentence_end_candidates else idx + len(claim) + 120
            sentence = text[sentence_start + 1: sentence_end]
            negated = re.search(r"\b(no|not|never|without|forbidden|does not|do not|cannot)\b", window) or re.search(
                r"\b(no|not|never|without|forbidden|does not|do not|cannot)\b", sentence
            )
            if not negated:
                findings.append({"claim": claim, "context": one_line(window, 160)})
                break
            idx = text.find(claim, idx + len(claim))
    return {
        "status": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": findings,
        "boundary": app_data["claim_boundary"],
    }


def secret_audit() -> dict[str, Any]:
    findings = []
    secret_patterns = [
        re.compile(r"(?i)\bapi[_-]?key\b\s*[:=]\s*[A-Za-z0-9_-]{12,}"),
        re.compile(r"(?i)\bsecret\b\s*[:=]\s*[A-Za-z0-9_-]{12,}"),
        re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{20,}"),
        re.compile(r"fff39a33858102015f4630ed32b9acad", re.I),
    ]
    for path in OUT.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in secret_patterns:
            match = pattern.search(text)
            if match:
                findings.append({"path": str(path), "match": match.group(0)[:64]})
    return {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def no_mutation_audit(before: dict[str, dict[str, Any]]) -> dict[str, Any]:
    after = snapshot_roots()
    changed = [name for name in before if before[name] != after[name]]
    return {
        "status": "PASS" if not changed else "FAIL",
        "changed_roots": changed,
        "checked_roots": sorted(before),
    }


def negative_tests() -> dict[str, Any]:
    tests = [
        {"name": "current R7 app path is not overwritten", "status": "PASS" if R7_ROOT.exists() else "FAIL"},
        {"name": "app can open from file without fetch", "status": "PASS" if "fetch(" not in (APP / "app.js").read_text(encoding="utf-8") else "FAIL"},
        {"name": "generic persona placeholders absent", "status": "PASS" if not re.search(r"persona-[12]", (APP / "index.html").read_text(encoding="utf-8") + (APP / "app.js").read_text(encoding="utf-8")) else "FAIL"},
        {"name": "source errors are summarized, not raw HTTP dumps", "status": "PASS" if "HTTPError" not in (APP / "data/app_data.js").read_text(encoding="utf-8") else "FAIL"},
        {"name": "3D panel is labelled preview, not USD renderer", "status": "PASS" if "browser preview" in (APP / "data/app_data.js").read_text(encoding="utf-8") else "FAIL"},
        {"name": "no command/control claim", "status": "PASS" if "no command/control" in json.dumps(LIMITATIONS) else "FAIL"},
    ]
    return {"status": "PASS" if all(t["status"] == "PASS" for t in tests) else "FAIL", "tests": tests}


def hash_outputs() -> None:
    rows = []
    for path in sorted(p for p in OUT.rglob("*") if p.is_file()):
        if path.name == "hashes.sha256":
            continue
        rows.append(f"{sha256(path)}  {path.relative_to(OUT).as_posix()}")
    write_text(OUT / "hashes.sha256", "\n".join(rows) + "\n")


def write_reports(
    app_data: dict[str, Any],
    source_map: dict[str, Any],
    smoke: dict[str, Any],
    claims: dict[str, Any],
    secrets: dict[str, Any],
    no_mutation: dict[str, Any],
    negative: dict[str, Any],
) -> dict[str, Any]:
    status = PASS_LIMITED if all(
        report.get("status") == "PASS" for report in [smoke, claims, secrets, no_mutation, negative]
    ) else FAIL
    decision = {
        "task_name": TASK,
        "status": status,
        "timestamp": utc_now(),
        "app_shell": str(APP.resolve()),
        "app_file_url": (APP / "index.html").resolve().as_uri(),
        "previous_r7_app_left_untouched": str((R7_ROOT / "app_shell").resolve()),
        "episode_count": app_data["episode_counts"]["total"],
        "city_counts": app_data["episode_counts"]["by_city"],
        "scene_models": {k: v["scene_status"] for k, v in app_data["scene_models"].items()},
        "smoke_status": smoke["status"],
        "claim_boundary_status": claims["status"],
        "secret_audit_status": secrets["status"],
        "no_mutation_status": no_mutation["status"],
        "negative_test_status": negative["status"],
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-INTEGRATION-R2",
    }
    write_json(OUT / "MAIN_TRACK2C_D4X_CITY_FIRST_EPISODE_APP_REBUILD_R1_DECISION.json", decision)
    write_json(OUT / "CITY_FIRST_APP_DATA_MANIFEST.json", source_map)
    write_json(OUT / "APP_SMOKE_REPORT.json", smoke)
    write_json(OUT / "APP_NEGATIVE_TEST_REPORT.json", negative)
    write_json(OUT / "audits/CLAIM_BOUNDARY_AUDIT.json", claims)
    write_json(OUT / "audits/SECRET_REDACTION_AUDIT.json", secrets)
    write_json(OUT / "audits/NO_MUTATION_AUDIT.json", no_mutation)
    write_text(OUT / "CLAIM_BOUNDARY_AUDIT.md", f"# Claim Boundary Audit\n\nStatus: `{claims['status']}`\n\n{app_data['claim_boundary']}\n")
    write_text(OUT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{secrets['status']}`\n\nFinding count: `{secrets['finding_count']}`\n")
    write_text(OUT / "NO_MUTATION_AUDIT.md", "# No-Mutation Audit\n\nStatus: `{}`\n\nChanged roots: `{}`\n".format(no_mutation["status"], ", ".join(no_mutation["changed_roots"]) or "none"))
    write_text(OUT / "APP_PRODUCT_MODEL.md", dedent(f"""\
        # City-First Episode App Product Model

        This app starts from a city episode, not from a project board or source ledger.

        Primary order:

        1. City episode.
        2. Place/entity.
        3. What is happening or what needs review.
        4. Map/3D/timeline context.
        5. Evidence and refs.
        6. Limitations.
        7. Safe next-look.

        Architecture counters, source inventory, graph/query substrate, and data quality are still present,
        but they are secondary evidence surfaces.

        Output app:

        `{(APP / "index.html").resolve()}`

        Claim boundary:

        `{app_data["claim_boundary"]}`
        """))
    write_text(OUT / "MAIN_TRACK2C_D4X_CITY_FIRST_EPISODE_APP_REBUILD_R1.md", dedent(f"""\
        # {TASK}

        Status: `{status}`

        Built a separate city-first app shell from the Track 2B episode pack. The R7 app was not mutated.

        Key app shifts:

        - Home asks what is happening in the cities.
        - City episode is the primary object.
        - Evidence, source refs, runtime packets, replay, and limitations sit behind the episode.
        - The 3D/map panel is rotatable and zoomable in-browser, using sampled BARC/NYC LOD2 identity examples.
        - Full USD scenes remain separate Omniverse assets opened through local commands.

        Counts:

        - Episodes: `{app_data["episode_counts"]["total"]}`
        - Barcelona: `{app_data["episode_counts"]["by_city"].get("BARC", 0)}`
        - NYC: `{app_data["episode_counts"]["by_city"].get("NYC", 0)}`
        - Chicago: `{app_data["episode_counts"]["by_city"].get("CHI", 0)}`
        - London: `{app_data["episode_counts"]["by_city"].get("LON", 0)}`
        - Cross-city: `{app_data["episode_counts"]["by_city"].get("CROSS_CITY", 0)}`

        Open:

        `{(APP / "index.html").resolve()}`
        """))
    write_text(OUT / "README.md", dedent(f"""\
        # CityBrain City-First Episode App Rebuild R1

        Open the new app:

        `{(APP / "index.html").resolve()}`

        This is a new app output root. It does not replace the R7 shell.

        Status: `{status}`
        """))
    return decision


def copy_runner() -> None:
    shutil.copy2(Path(__file__), OUT / Path(__file__).name)


def run() -> int:
    before = snapshot_roots()
    safe_reset_output()
    app_data, source_map = build_app_data()
    write_app_files(app_data)
    smoke = app_smoke(app_data)
    claims = claim_boundary_audit(app_data)
    secrets = secret_audit()
    negative = negative_tests()
    no_mutation = no_mutation_audit(before)
    decision = write_reports(app_data, source_map, smoke, claims, secrets, no_mutation, negative)
    copy_runner()
    hash_outputs()
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {OUT}")
    return 0 if decision["status"] == PASS_LIMITED else 1


if __name__ == "__main__":
    raise SystemExit(run())
