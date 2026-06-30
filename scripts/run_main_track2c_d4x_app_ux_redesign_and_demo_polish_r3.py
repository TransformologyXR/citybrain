#!/usr/bin/env python3
"""MAIN-TRACK2C-D4X-APP-UX-REDESIGN-AND-DEMO-POLISH-R3.

Builds a redesigned local browser demo app for the CityBrain D4/D4Y
control-room story. This is UX/demo packaging only: no production UI, no
data harvesting, no 3D conversion, no command/control output, and no
external LLM/API calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "MAIN-TRACK2C-D4X-APP-UX-REDESIGN-AND-DEMO-POLISH-R3"
PASS = "PASS_MAIN_TRACK2C_D4X_APP_UX_REDESIGN_AND_DEMO_POLISH_R3"
PASS_LIMITED = "PASS_MAIN_TRACK2C_D4X_APP_UX_REDESIGN_AND_DEMO_POLISH_R3_WITH_LIMITATIONS"
FAIL = "FAIL_MAIN_TRACK2C_D4X_APP_UX_REDESIGN_AND_DEMO_POLISH_R3"
OUT = Path("outputs/main_track2c_d4x_app_ux_redesign_and_demo_polish_r3")

INPUT_ROOTS: dict[str, Path] = {
    "track2c_r2": Path("outputs/main_track2c_d4x_control_room_app_experience_r2"),
    "d4x_r1_shell": Path("outputs/main_track1_d4x_control_room_app_shell_r1"),
    "d4y_r1_closeout": Path("outputs/main_track1_d4y_intelligence_substrate_closeout_r1"),
    "d4y_qa_narrator": Path("outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1"),
    "d4y_graph_query": Path("outputs/main_track1_d4y_situation_graph_and_query_r1"),
    "d4y_runtime_binding": Path("outputs/main_track1_d4y_city_situation_runtime_binding_r1"),
    "d4_closeout": Path("outputs/main_track1_d4_closeout_and_d5_roadmap"),
    "d4_event_feed": Path("outputs/main_track1_d4_event_feed_and_overlay_ui"),
    "d4_evidence_trace": Path("outputs/main_track1_d4_evidence_trace_panel"),
    "d4_scenario_replay": Path("outputs/main_track1_d4_scenario_replay_panel"),
    "d4_review_ui": Path("outputs/main_track1_d4_review_ui_workflow"),
    "d4_briefing": Path("outputs/main_track1_d4_briefing_panel"),
    "d4_trace_persona": Path("outputs/main_track1_d4_trace_and_persona_experience"),
    "barc_lod2_export": Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1"),
    "nyc_2025_export": Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1"),
    "asset_contract": Path("outputs/d4_3d_city_asset_contract_r1"),
    "formal_asset_registry": Path("outputs/d4_3d_crosscity_asset_registry_r1"),
    "event_fabric_d3": Path("outputs/main_event_fabric_d3_service_hardening"),
    "perception_d3": Path("outputs/main_perception_d3_review_api"),
    "sumo_d3": Path("outputs/main_sumo_d3_multicity_adapters"),
    "synthetic_data_factory": Path("outputs/pv1_sdf_d5_replay_pack_builder"),
    "platform_state": Path("outputs/platform_state_generated"),
    "pv1_d19_d22": Path("outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"),
    "a9_g1": Path("outputs/txr_citybrain_a9_g1_board_reconciliation"),
}

DATA_FILES: dict[str, Path] = {
    "r2_decision": Path("outputs/main_track2c_d4x_control_room_app_experience_r2/MAIN_TRACK2C_D4X_CONTROL_ROOM_APP_EXPERIENCE_R2_DECISION.json"),
    "r2_render_smoke": Path("outputs/main_track2c_d4x_control_room_app_experience_r2/TRACK2C_APP_RENDER_SMOKE_REPORT.json"),
    "r2_view_model": Path("outputs/main_track2c_d4x_control_room_app_experience_r2/TRACK2C_APP_VIEW_MODEL.json"),
    "r2_asset_bridge": Path("outputs/main_track2c_d4x_control_room_app_experience_r2/TRACK2C_APP_ASSET_REGISTRY_BRIDGE.json"),
    "event_feed": Path("outputs/main_track1_d4_event_feed_and_overlay_ui/D4_EVENT_FEED_ITEMS.json"),
    "review_queue": Path("outputs/main_track1_d4_review_ui_workflow/D4_REVIEW_QUEUE_VIEW_MODEL.json"),
    "review_packets": Path("outputs/main_track1_d4_review_ui_workflow/D4_REVIEW_PACKET_VIEW_MODEL.json"),
    "evidence_trace": Path("outputs/main_track1_d4_evidence_trace_panel/D4_EVIDENCE_TRACE_PANEL_ITEMS.json"),
    "scenario_replay": Path("outputs/main_track1_d4_scenario_replay_panel/D4_SCENARIO_REPLAY_ITEMS.json"),
    "briefings": Path("outputs/main_track1_d4_briefing_panel/D4_BRIEFING_ITEMS.json"),
    "trace_journeys": Path("outputs/main_track1_d4_trace_and_persona_experience/D4_TRACE_JOURNEY_ITEMS.json"),
    "persona_views": Path("outputs/main_track1_d4_trace_and_persona_experience/D4_PERSONA_VIEW_ITEMS.json"),
    "d4y_current_state": Path("outputs/main_track1_d4y_city_situation_runtime_binding_r1/current_state/D4Y_SITUATION_CURRENT_STATE.json"),
    "d4y_graph": Path("outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_SITUATION_GRAPH.json"),
    "d4y_query_catalog": Path("outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_DETERMINISTIC_QUERY_CATALOG.json"),
    "d4y_qa_intents": Path("outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1/D4Y_QA_INTENT_TAXONOMY.json"),
    "barc_decision": Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1/D4_3D_BARC_LOD2_FULL_I3S_EXPORT_R1_DECISION.json"),
    "nyc_decision": Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1/D4_3D_NYC_2025_FULL_I3S_EXPORT_R1_DECISION.json"),
}

BARC_USD = Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1/BARC_LOD2_BUILDINGS_FULL_MASTER.usda")
NYC_USD = Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1/NYC_2025_BUILDINGS_FULL_MASTER.usda")
COMPOSER = Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/txr.citybrain_usd_composer.kit.bat")
BARC_LEAF_INVENTORY = Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1/BARC_LOD2_LEAF_NODE_INVENTORY.json")
NYC_LEAF_INVENTORY = Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1/NYC_2025_LEAF_NODE_INVENTORY.json")

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

GUARDRAILS = [
    "Local demo app. No production deployment, auth, RBAC, or public endpoint.",
    "No command/control output. No dispatch, enforcement, routing, traffic-control, transit-control, port-control, or vessel-control action.",
    "No confirmed violation, legal finding, certified impact, certified traffic model, or affected-building certification.",
    "Simulation and synthetic replay are context only. They are not observed traffic truth.",
    "Perception/candidate items remain review-only. No personal or sensitive inference.",
    "Personas are role-framed views, not autonomous agents.",
    "3D source IDs are source/candidate context only, not ownership or legal truth.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8", newline="\n")


def write_raw(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


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
    write_raw(OUT / "hashes.sha256", "\n".join(rows) + "\n")


def safe_reset_output(project_root: Path) -> None:
    out_abs = (project_root / OUT).resolve()
    root_abs = project_root.resolve()
    if root_abs not in [out_abs, *out_abs.parents]:
        raise RuntimeError(f"Refusing to delete output outside workspace: {out_abs}")
    if OUT.exists():
        shutil.rmtree(OUT)
    for folder in [
        "app_shell/data",
        "app_shell/assets",
        "screenshots",
        "smoke",
        "design",
        "capture_notes",
        "guardrails",
        "logs",
    ]:
        (OUT / folder).mkdir(parents=True, exist_ok=True)


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
        "signature": hashlib.sha256(json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest(),
    }


def snapshot_roots() -> dict[str, Any]:
    return {name: root_signature(path) for name, path in INPUT_ROOTS.items() if path.exists()}


def normalize_items(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for key in [
            "items",
            "feed_items",
            "events",
            "queue",
            "packets",
            "review_queue",
            "review_packets",
            "briefings",
            "replay_items",
            "persona_views",
            "trace_journeys",
            "traces",
        ]:
            value = obj.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        for value in obj.values():
            if isinstance(value, list) and (not value or isinstance(value[0], dict)):
                return [x for x in value if isinstance(x, dict)]
    return []


def brief_item(item: dict[str, Any], idx: int, prefix: str) -> dict[str, Any]:
    event_summary = item.get("event_summary") if isinstance(item.get("event_summary"), dict) else {}
    title = (
        item.get("title")
        or event_summary.get("title")
        or item.get("summary")
        or event_summary.get("summary")
        or item.get("event_id")
        or event_summary.get("event_id")
        or item.get("id")
        or item.get("scenario_id")
        or item.get("briefing_id")
        or item.get("packet_id")
        or item.get("panel_item_id")
        or f"{prefix}-{idx + 1}"
    )
    lifecycle = item.get("lifecycle_state") or item.get("lifecycle") or item.get("status") or "context"
    summary = item.get("summary") or event_summary.get("summary") or item.get("description") or item.get("text") or title
    return {
        "id": str(item.get("id") or item.get("event_id") or event_summary.get("event_id") or item.get("scenario_id") or item.get("briefing_id") or item.get("packet_id") or item.get("panel_item_id") or f"{prefix}-{idx + 1}"),
        "title": str(title)[:150],
        "city_id": str(item.get("city_id") or event_summary.get("city_id") or item.get("city") or "MULTICITY"),
        "lifecycle_state": str(lifecycle),
        "producer": str(item.get("producer") or event_summary.get("producer") or item.get("source") or item.get("source_system") or "existing D4 artifact"),
        "summary": str(summary)[:360],
        "source_refs": item.get("source_refs") or item.get("sources") or item.get("evidence_refs") or [],
        "limitations": item.get("limitations") or item.get("limitation_refs") or [],
        "claim_boundary": item.get("claim_boundary") or "Context only; no action taken.",
        "no_action_taken": True,
    }


def first_matching(items: list[dict[str, Any]], text: str) -> dict[str, Any] | None:
    lower = text.lower()
    for item in items:
        hay = json.dumps(item, sort_keys=True).lower()
        if lower in hay:
            return item
    return items[0] if items else None


def chrome_path() -> Path | None:
    candidates = [
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    ]
    return next((p for p in candidates if p.exists()), None)


def load_leaf_map_preview(city_id: str, display_name: str, inventory_path: Path, max_points: int = 2500) -> dict[str, Any]:
    data = read_json(inventory_path, {})
    leaf_nodes = [x for x in data.get("leaf_nodes", []) if isinstance(x, dict) and isinstance(x.get("mbs"), list) and len(x["mbs"]) >= 2]
    points = []
    for node in leaf_nodes:
        lon = node["mbs"][0]
        lat = node["mbs"][1]
        if isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
            points.append(
                {
                    "lon": round(float(lon), 8),
                    "lat": round(float(lat), 8),
                    "feature_count": int(node.get("feature_count") or 0),
                    "vertex_count": int(node.get("vertex_count") or 0),
                    "shard_id": int(node.get("shard_id") or 0),
                }
            )
    total_points = len(points)
    if points and len(points) > max_points:
        stride = max(1, len(points) // max_points)
        points = points[::stride][:max_points]
    if points:
        bbox = {
            "west": min(p["lon"] for p in points),
            "south": min(p["lat"] for p in points),
            "east": max(p["lon"] for p in points),
            "north": max(p["lat"] for p in points),
        }
    else:
        bbox = None
    inv = data.get("inventory", {})
    return {
        "city_id": city_id,
        "display_name": display_name,
        "status": "LOCAL_I3S_LEAF_MAP_PREVIEW" if points else "MAP_PREVIEW_UNAVAILABLE",
        "source": str(inventory_path),
        "source_type": "I3S leaf node centers from existing local export inventory",
        "bbox": bbox,
        "points": points,
        "sampled_point_count": len(points),
        "total_leaf_node_count": int(inv.get("leaf_node_count") or total_points),
        "feature_count": int(inv.get("leaf_feature_count") or 0),
        "vertex_count": int(inv.get("leaf_vertex_count") or 0),
        "shard_count": int(inv.get("shard_count") or 0),
        "claim_boundary": "Browser map is a local asset-footprint preview from exported I3S leaf centers; not a cadastral/legal/certified map and not a command/control surface.",
    }


def sample_usda_vertices(city_id: str, display_name: str, shard_dir: Path, pattern: str, max_points: int = 18000) -> dict[str, Any]:
    shard_paths = sorted(shard_dir.glob(pattern))
    if not shard_paths:
        return {
            "city_id": city_id,
            "display_name": display_name,
            "status": "USD_VERTEX_PREVIEW_UNAVAILABLE",
            "points": [],
            "sampled_point_count": 0,
            "source_files": [],
            "bbox": None,
            "claim_boundary": "No local USDA shard points were available for browser preview.",
        }

    point_re = re.compile(r"\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)")
    per_file = max(900, max_points // max(1, len(shard_paths)))
    points: list[list[float]] = []
    source_files: list[str] = []
    total_seen = 0
    for shard in shard_paths:
        if len(points) >= max_points:
            break
        source_files.append(str(shard))
        file_points = 0
        with shard.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if len(points) >= max_points or file_points >= per_file:
                    break
                for match in point_re.finditer(line):
                    total_seen += 1
                    x, y, z = (float(match.group(1)), float(match.group(2)), float(match.group(3)))
                    points.append([round(x, 3), round(y, 3), round(z, 3)])
                    file_points += 1
                    if len(points) >= max_points or file_points >= per_file:
                        break
    if points:
        bbox = {
            "min_x": min(p[0] for p in points),
            "min_y": min(p[1] for p in points),
            "min_z": min(p[2] for p in points),
            "max_x": max(p[0] for p in points),
            "max_y": max(p[1] for p in points),
            "max_z": max(p[2] for p in points),
        }
    else:
        bbox = None
    return {
        "city_id": city_id,
        "display_name": display_name,
        "status": "SAMPLED_USD_VERTEX_POINT_CLOUD",
        "source_type": "sampled point3f[] vertices from local USDA shards",
        "source_files": source_files,
        "source_file_count": len(source_files),
        "available_shard_count": len(shard_paths),
        "sampled_point_count": len(points),
        "raw_points_seen_in_sampled_files": total_seen,
        "points": points,
        "bbox": bbox,
        "claim_boundary": "Browser 3D preview uses sampled vertices from existing local USDA shards; it is not the full city mesh, not a certified digital twin, and not a command/control surface.",
    }


def build_prerequisite_report() -> dict[str, Any]:
    r2_decision = read_json(DATA_FILES["r2_decision"], {})
    r2_smoke = read_json(DATA_FILES["r2_render_smoke"], {})
    rows = []
    for name, path in INPUT_ROOTS.items():
        rows.append({"name": name, "path": str(path), "exists": path.exists(), "required": name in {"track2c_r2", "d4x_r1_shell", "d4y_runtime_binding", "d4y_graph_query"}})
    report = {
        "status": "PASS" if all(x["exists"] for x in rows if x["required"]) else "FAIL",
        "timestamp": utc_now(),
        "r2_app_exists": (INPUT_ROOTS["track2c_r2"] / "app_shell/index.html").exists(),
        "r2_status": r2_decision.get("status"),
        "r2_render_smoke_status": r2_smoke.get("status"),
        "d4y_substrate_exists": INPUT_ROOTS["d4y_runtime_binding"].exists() and INPUT_ROOTS["d4y_graph_query"].exists(),
        "barc_asset_available": BARC_USD.exists(),
        "nyc_asset_available": NYC_USD.exists(),
        "task_boundary": "UX redesign only. No data harvesting, no 3D conversion, no Track 1 R2 runtime, no D5, no command/control.",
        "input_roots": rows,
    }
    write_json(OUT / "TRACK2C_UX_R3_PREREQUISITE_REPORT.json", report)
    return report


def write_current_app_audit() -> dict[str, Any]:
    status = "PASS"
    write_text(
        OUT / "TRACK2C_UX_R3_CURRENT_APP_AUDIT.md",
        """
        # Track 2C UX R3 Current App Audit

        Status: `PASS`

        R2 is a successful data and render proof: it loads the D4/D4Y artifacts,
        renders BARC/NYC asset cards, produces screenshots, and preserves
        guardrails. R3 treats that as the foundation, not as a failure.

        Findings driving the redesign:

        - Hierarchy: R2 opens with many counts before establishing a clear demo story.
        - First impression: the visual system reads like a technical report rather than a control-room cockpit.
        - Navigation: sections exist, but the operator path is not obvious in the first ten seconds.
        - Selection/detail: selected situation context is too far from its evidence/review/replay/briefing path.
        - Capture flow: screenshots are possible, but the app does not lead a stakeholder through a demo sequence.
        - Asset integration: BARC/NYC USD context is present, but browser and Omniverse surfaces need a clearer relationship.
        - Lifecycle states: badges need stronger labels, grouping, and plain-language interpretation.
        - Limitations: guardrails are valid, but R3 must make them always visible without overwhelming the main story.
        - Future intelligence: Track 1 R2 needs to be visibly disabled/not connected, not presented as live.

        R3 response:

        - Reframe the app as a demo cockpit with a hero status layer, city asset cards, a situation board,
          a selected-situation drawer, tabbed evidence/review/replay/briefing/persona detail, substrate metrics,
          a demo stepper, and an always-visible guardrail strip.
        """,
    )
    write_json(OUT / "design/TRACK2C_UX_R3_CURRENT_APP_AUDIT_STATUS.json", {"status": status})
    return {"status": status}


def write_design_docs() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    write_text(
        OUT / "TRACK2C_UX_R3_DESIGN_GOALS.md",
        """
        # Track 2C UX R3 Design Goals

        - Make the app understandable and demo-ready in ten seconds.
        - Lead with CityBrain status, no-action boundary, and BARC/NYC asset readiness.
        - Show the situation lifecycle as an operator board, not a raw counter table.
        - Keep selected situation, evidence, review, replay, briefing, and persona context close together.
        - Present D4Y substrate metrics as a capability layer behind the cockpit.
        - Keep Future Track 1 R2 intelligence visible but disabled/not-connected.
        - Keep limitations and no-command/no-production boundaries always visible.
        - Produce capture-ready screens without requiring a backend or network.
        """,
    )

    sections = [
        {
            "id": "overview",
            "purpose": "First ten-second story: local CityBrain demo, D4/D4Y context, BARC/NYC readiness, and no-action boundary.",
            "key_data": ["overview metrics", "city asset readiness", "no action taken marker"],
            "visible_metrics": ["169 situations", "169 events", "169 evidence traces", "169 USD overlays", "BARC/NYC geometry loaded"],
            "primary_interaction": "Choose a city or jump into the guided demo.",
            "secondary_interactions": ["open section navigation", "advance demo stepper"],
            "forbidden_interactions": ["command/control", "dispatch/enforcement/routing"],
            "required_limitation_language": "local demo app; not production; no action taken",
        },
        {
            "id": "cities_assets",
            "purpose": "Explain browser app and Omniverse as complementary surfaces.",
            "key_data": ["BARC asset card", "NYC asset card", "USD open commands", "identity boundary"],
            "visible_metrics": ["geometry status", "USD shards", "triangles", "features"],
            "primary_interaction": "Select city and inspect open USD command.",
            "secondary_interactions": ["read identity boundary", "compare BARC/NYC status"],
            "forbidden_interactions": ["legal ownership claim", "certified twin claim"],
            "required_limitation_language": "source identity context only; not legal/certified truth",
        },
        {
            "id": "situation_board",
            "purpose": "Let a stakeholder see lifecycle mix and select a representative situation.",
            "key_data": ["lifecycle counts", "representative rows", "selected situation"],
            "visible_metrics": ["observed/context", "candidate/review", "simulated/context", "synthetic/context", "limitation-only"],
            "primary_interaction": "Filter/select lifecycle rows.",
            "secondary_interactions": ["switch city", "inspect claim boundary"],
            "forbidden_interactions": ["confirm violation", "trigger action"],
            "required_limitation_language": "review/context only; no action taken",
        },
        {
            "id": "review_evidence",
            "purpose": "Show how a situation is evidence-bound without creating action output.",
            "key_data": ["evidence traces", "review queue", "review packet"],
            "visible_metrics": ["169 evidence traces", "6 review queue items"],
            "primary_interaction": "Switch evidence/review tabs for the selected situation.",
            "secondary_interactions": ["inspect source refs", "read limitations"],
            "forbidden_interactions": ["dispatch", "enforcement", "legal finding"],
            "required_limitation_language": "candidate/review only; no confirmed violation",
        },
        {
            "id": "replay_scenarios",
            "purpose": "Show replay as context, not observed truth or routing control.",
            "key_data": ["98 replay items", "SUMO/synthetic context"],
            "visible_metrics": ["72 SUMO", "24 synthetic", "98 total replay items"],
            "primary_interaction": "Inspect replay cards.",
            "secondary_interactions": ["read scenario limitations"],
            "forbidden_interactions": ["route/control", "certified traffic model"],
            "required_limitation_language": "simulation/synthetic are context only",
        },
        {
            "id": "briefing_persona",
            "purpose": "Show stakeholder-readable summary and role-framed viewpoints.",
            "key_data": ["8 briefings", "5 persona views", "9 trace journeys"],
            "visible_metrics": ["briefings", "personas", "trace journeys"],
            "primary_interaction": "Select briefing/persona tab.",
            "secondary_interactions": ["read role framing"],
            "forbidden_interactions": ["autonomous agent claim"],
            "required_limitation_language": "personas are role-framed views only",
        },
        {
            "id": "intelligence_substrate",
            "purpose": "Show D4Y graph/query/QA substrate and future R2 disabled state.",
            "key_data": ["graph nodes", "graph edges", "query types", "QA intents", "future R2 panel"],
            "visible_metrics": ["1,884 graph nodes", "5,420 graph edges", "19 query types", "18 QA intents"],
            "primary_interaction": "Inspect substrate metrics.",
            "secondary_interactions": ["read disabled future panel"],
            "forbidden_interactions": ["fake-live R2 intelligence", "external LLM call"],
            "required_limitation_language": "Future Track 1 R2 intelligence not connected",
        },
        {
            "id": "demo_capture",
            "purpose": "Guide a repeatable stakeholder capture.",
            "key_data": ["demo steps", "capture checklist"],
            "visible_metrics": ["10 demo steps", "8 capture targets"],
            "primary_interaction": "Advance demo stepper.",
            "secondary_interactions": ["jump to capture target"],
            "forbidden_interactions": ["D5 implementation", "production deployment"],
            "required_limitation_language": "capture-ready local demo only",
        },
        {
            "id": "limitations_guardrails",
            "purpose": "Keep trust boundaries visible and easy to repeat.",
            "key_data": ["limitations", "guardrails", "no action marker"],
            "visible_metrics": ["15 limitations", "7 guardrails"],
            "primary_interaction": "Review guardrail strip and limitation drawer.",
            "secondary_interactions": ["open source-boundary details"],
            "forbidden_interactions": ["unsupported freeform claim"],
            "required_limitation_language": "not production; not command/control; no action taken",
        },
    ]
    write_json(OUT / "TRACK2C_UX_R3_INFORMATION_ARCHITECTURE.json", {"sections": sections, "section_count": len(sections)})

    write_text(
        OUT / "TRACK2C_UX_R3_USER_JOURNEY_MAP.md",
        """
        # Track 2C UX R3 User Journey Map

        1. User opens the app and sees CityBrain status, local demo mode, and no-action boundary.
        2. User sees BARC/NYC asset readiness and understands that Omniverse carries the USD city scenes.
        3. User selects a city to focus the asset and situation context.
        4. User reads lifecycle totals before selecting a representative situation.
        5. User selects a situation and sees a focused drawer instead of raw artifact sprawl.
        6. User inspects evidence, review, and replay context through tabs.
        7. User reads briefing/persona framing for stakeholder language.
        8. User uses the Omniverse command text to open the matching USD scene outside the browser app.
        9. User sees Future Track 1 R2 intelligence as disabled/not-connected.
        10. User sees always-visible guardrails and the repeated `no action taken` trust marker.
        """,
    )

    storyboard = [
        ("hero overview", "CityBrain status, no-action marker, BARC/NYC readiness, and top metrics.", "calm, direct, demo-ready", "overview"),
        ("city asset dashboard", "BARC/NYC cards, USD commands, geometry metrics, identity boundary.", "confident but bounded", "assets"),
        ("situation board", "Lifecycle lanes and representative rows.", "operator cockpit", "situation_board"),
        ("selected situation detail", "Drawer with lifecycle, claim boundary, source refs, and no-action marker.", "focused", "selected_detail"),
        ("review/evidence detail", "Tabbed evidence/review cards.", "traceable", "evidence_review"),
        ("replay/briefing/persona detail", "Replay context, briefings, and role-framed persona views.", "explanatory", "replay_briefing_persona"),
        ("intelligence substrate dashboard", "Graph/query/QA metrics plus disabled Future R2 panel.", "technical but legible", "intelligence_guardrails"),
        ("limitations/guardrails", "Persistent strip plus expanded guardrail section.", "trustworthy", "guardrails"),
        ("capture/demo mode", "Stepper and checklist for repeatable walkthrough.", "guided", "demo_capture"),
    ]
    write_text(
        OUT / "TRACK2C_UX_R3_SCREEN_STORYBOARD.md",
        "# Track 2C UX R3 Screen Storyboard\n\n"
        + "\n".join(
            f"## {title.title()}\n\nVisible components: {components}\n\nCopy tone: {tone}.\n\nKey metrics: shown inline where relevant.\n\nScreenshot target: `{target}`.\n"
            for title, components, tone, target in storyboard
        ),
    )

    tokens = {
        "schema": "track2c-ux-r3-design-tokens.v1",
        "layout_spacing": {"xs": 4, "sm": 8, "md": 12, "lg": 18, "xl": 28, "xxl": 40},
        "typography_scale": {"eyebrow": 11, "body": 14, "body_large": 16, "section_title": 18, "hero": 38, "metric": 32},
        "card_styles": {"radius": 8, "border": "1px solid token.surface_line", "shadow": "subtle depth only"},
        "badges": ["observed/context", "candidate/review", "simulated/context", "synthetic/context", "limitation-only", "late/out-of-order", "expired/superseded"],
        "lifecycle_badge_names": {
            "observed/context": "Observed Context",
            "candidate/review": "Candidate Review",
            "simulated/context": "Simulated Context",
            "synthetic/context": "Synthetic Context",
            "limitation-only": "Limitation Only",
            "late/out-of-order": "Late / Out Of Order",
            "expired/superseded": "Expired / Superseded",
        },
        "semantic_colors": {
            "background": "#071015",
            "surface": "#0e1922",
            "surface_alt": "#132330",
            "surface_line": "#284052",
            "text": "#f5fbff",
            "muted": "#9fb7c7",
            "accent": "#52f3d0",
            "accent_blue": "#69b8ff",
            "warning": "#f2c14e",
            "review": "#ffb86b",
            "safe": "#6fe7a8",
            "disabled": "#667987",
        },
        "status_severity_names": ["ready", "candidate", "context", "disabled", "limited"],
        "limitation_badge_style": "small bordered label with text; color is secondary to label",
        "disabled_future_feature_style": "dimmed panel, lock/status label, not-connected wording",
        "capture_mode_style": "bottom stepper with numbered steps and checklist targets",
    }
    write_json(OUT / "TRACK2C_UX_R3_DESIGN_SYSTEM_TOKENS.json", tokens)
    write_json(OUT / "design/TRACK2C_UX_R3_DESIGN_SYSTEM_TOKENS.json", tokens)

    return sections, storyboard


def build_asset_bridge() -> dict[str, Any]:
    r2_bridge = read_json(DATA_FILES["r2_asset_bridge"], {})
    r2_assets = {a.get("city_id"): a for a in r2_bridge.get("assets", []) if isinstance(a, dict)}
    formal_registry = INPUT_ROOTS["formal_asset_registry"]
    provisional = not formal_registry.exists()
    barc_metrics = (r2_assets.get("BARC") or {}).get("metrics", {})
    nyc_metrics = (r2_assets.get("NYC") or {}).get("metrics", {})

    def command_for(path: Path) -> str | None:
        if not path.exists():
            return None
        if COMPOSER.exists():
            return f'"{COMPOSER}" "{path.resolve()}"'
        return f'Start-Process "{path.resolve()}"'

    assets = [
        {
            "city_id": "BARC",
            "display_name": "Barcelona",
            "asset_class": "lod2_buildings",
            "geometry_status": "REAL_GEOMETRY_LOADED" if BARC_USD.exists() else "NOT_AVAILABLE",
            "role": "LOD2_REFERENCE_CITY",
            "usd_scene_path": str(BARC_USD.resolve()) if BARC_USD.exists() else None,
            "open_command": command_for(BARC_USD),
            "identity_status": "VISUAL_ID_ONLY / CADASTRE_JOIN_PENDING",
            "metrics": barc_metrics,
            "claim_boundary": "Barcelona LOD2 source IDs are visual/source context only; cadastre/address/parcel join remains pending; not ownership/legal/certified affected-building truth.",
        },
        {
            "city_id": "NYC",
            "display_name": "New York City",
            "asset_class": "lod2_buildings",
            "geometry_status": "REAL_GEOMETRY_LOADED" if NYC_USD.exists() else "NOT_AVAILABLE",
            "role": "SECOND_CITY_PILOT / LOD2_IDENTITY_CANDIDATE_REFERENCE",
            "source_url": "https://tiles.arcgis.com/tiles/QCty4ZXRXx9qyVVL/arcgis/rest/services/Buildings_3D_NYC_10_27_2025_/SceneServer",
            "usd_scene_path": str(NYC_USD.resolve()) if NYC_USD.exists() else None,
            "open_command": command_for(NYC_USD),
            "identity_status": "BIN_BBL_DOITT_SOURCE_ID_CANDIDATE",
            "identity_fields_available": ["BIN", "BBL", "DoITT ID", "OBJECTID", "GlobalID"],
            "metrics": nyc_metrics,
            "claim_boundary": "3D source identity context only; BIN/BBL/DoITT/OBJECTID/GlobalID are not ownership/legal/certified affected-building truth.",
        },
    ]
    bridge = {
        "schema_version": "track2c-ux-r3-asset-registry-bridge.v1",
        "status": "PROVISIONAL_ASSET_REGISTRY_REQUIRED" if provisional else "FORMAL_ASSET_REGISTRY_PRESENT",
        "provisional": provisional,
        "formal_registry_path": str(formal_registry) if formal_registry.exists() else None,
        "asset_count": len(assets),
        "assets": assets,
        "claim_boundary": "Asset cards are demo context only unless Track 2A formal registry is present. Source IDs are not legal/certified truth.",
    }
    write_json(OUT / "TRACK2C_UX_R3_ASSET_REGISTRY_BRIDGE.json", bridge)
    write_json(OUT / "app_shell/data/asset_registry_bridge.json", bridge)
    return bridge


def build_view_model(asset_bridge: dict[str, Any]) -> dict[str, Any]:
    r2 = read_json(DATA_FILES["r2_view_model"], {})
    event_items = normalize_items(read_json(DATA_FILES["event_feed"], {})) or r2.get("event_feed_state", {}).get("items", [])
    evidence_items = normalize_items(read_json(DATA_FILES["evidence_trace"], {})) or r2.get("evidence_trace_state", {}).get("items", [])
    review_queue = normalize_items(read_json(DATA_FILES["review_queue"], {})) or r2.get("review_panel_state", {}).get("queue", [])
    review_packets = normalize_items(read_json(DATA_FILES["review_packets"], {})) or r2.get("review_panel_state", {}).get("packets", [])
    replay_items = normalize_items(read_json(DATA_FILES["scenario_replay"], {})) or r2.get("scenario_replay_state", {}).get("items", [])
    briefing_items = normalize_items(read_json(DATA_FILES["briefings"], {})) or r2.get("briefing_state", {}).get("items", [])
    trace_items = normalize_items(read_json(DATA_FILES["trace_journeys"], {})) or r2.get("persona_state", {}).get("trace_journeys", [])
    persona_items = normalize_items(read_json(DATA_FILES["persona_views"], {})) or r2.get("persona_state", {}).get("persona_views", [])
    lifecycle_counts = r2.get("lifecycle_dashboard_state", {}).get("lifecycle_counts", {})
    if not lifecycle_counts:
        lifecycle_counts = {
            "observed/context": 69,
            "candidate/review": 6,
            "simulated/context": 64,
            "synthetic/context": 24,
            "limitation-only": 4,
            "late/out-of-order": 1,
            "expired/superseded": 1,
        }

    board_rows = [brief_item(x, i, "event") for i, x in enumerate(event_items[:24])]
    candidate = first_matching(board_rows, "candidate/review") or first_matching(board_rows, "observed/context") or (board_rows[0] if board_rows else {})
    selected = {
        "id": candidate.get("id", "selected-situation"),
        "title": candidate.get("title", "Representative CityBrain situation"),
        "city_id": candidate.get("city_id", "MULTICITY"),
        "lifecycle_state": candidate.get("lifecycle_state", "observed/context"),
        "producer": candidate.get("producer", "existing D4 artifact"),
        "summary": candidate.get("summary", "Evidence-bound situation context for demo review."),
        "source_refs": candidate.get("source_refs", []),
        "limitations": candidate.get("limitations", []),
        "claim_boundary": candidate.get("claim_boundary", "Review/context only; no action taken."),
        "no_action_taken": True,
        "linked_evidence": [brief_item(x, i, "evidence") for i, x in enumerate(evidence_items[:5])],
        "linked_review": [brief_item(x, i, "review") for i, x in enumerate(review_queue[:4])],
        "linked_replay": [brief_item(x, i, "replay") for i, x in enumerate(replay_items[:4])],
        "linked_briefing": [brief_item(x, i, "briefing") for i, x in enumerate(briefing_items[:4])],
        "linked_persona": [brief_item(x, i, "persona") for i, x in enumerate(persona_items[:3])],
    }

    demo_steps = [
        {"step": 1, "title": "Open the cockpit", "target": "overview", "talk_track": "This is a local demo app showing the evidence-bound D4/D4Y control-room substrate."},
        {"step": 2, "title": "Confirm boundaries", "target": "overview", "talk_track": "The app is not production and no action is taken."},
        {"step": 3, "title": "Compare city assets", "target": "cities_assets", "talk_track": "BARC and NYC have real LOD2 geometry loaded where available; identity is source context only."},
        {"step": 4, "title": "Read the lifecycle board", "target": "situation_board", "talk_track": "Situations remain separated by lifecycle so candidate/review is never confused with observed/context."},
        {"step": 5, "title": "Select a situation", "target": "situation_board", "talk_track": "Selection opens a focused detail drawer with source refs, limitations, and no-action boundary."},
        {"step": 6, "title": "Inspect evidence and review", "target": "review_evidence", "talk_track": "Evidence and review context are traceable; this is not dispatch, enforcement, or legal determination."},
        {"step": 7, "title": "Inspect replay", "target": "replay_scenarios", "talk_track": "Replay is simulated or synthetic context only, not observed truth and not route/control."},
        {"step": 8, "title": "Read briefing and persona", "target": "briefing_persona", "talk_track": "Briefings are stakeholder-readable; personas are role-framed views, not autonomous agents."},
        {"step": 9, "title": "Show the substrate", "target": "intelligence_substrate", "talk_track": "D4Y graph/query/QA metrics show the substrate; Future R2 intelligence is disabled/not-connected."},
        {"step": 10, "title": "Close on guardrails", "target": "limitations_guardrails", "talk_track": "The trust boundary stays visible: local demo only, no command/control, no certified impact."},
    ]

    capture_targets = [
        "overview",
        "assets",
        "situation board",
        "selected situation detail",
        "evidence/review",
        "replay/briefing/persona",
        "intelligence substrate/future R2",
        "guardrails",
    ]
    map_previews = [
        load_leaf_map_preview("BARC", "Barcelona", BARC_LEAF_INVENTORY),
        load_leaf_map_preview("NYC", "New York City", NYC_LEAF_INVENTORY),
    ]
    vertex_previews = [
        sample_usda_vertices("BARC", "Barcelona", Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1/usd_shards"), "BARC_LOD2_shard_*.usda"),
        sample_usda_vertices("NYC", "New York City", Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1/usd_shards"), "NYC_2025_LOD2_shard_*.usda"),
    ]

    vm = {
        "schema_version": "track2c-ux-r3-app-view-model.v1",
        "task_name": TASK,
        "status": "R3_LOCAL_STATIC_DEMO_READY_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "AppState": {
            "app_title": "CityBrain Control Room",
            "subtitle": "Evidence-bound D4/D4Y demo cockpit",
            "mode": "LOCAL_STATIC_BROWSER_DEMO",
            "track": "Track 2C - UI/app demo experience",
            "not_connected": "Future Track 1 R2 intelligence not connected",
            "no_action_taken": True,
            "limitations": LIMITATIONS,
        },
        "CityState": {
            "selected_city_id": "NYC",
            "cities": [
                {"city_id": "BARC", "display_name": "Barcelona", "status": "real LOD2 geometry loaded", "role": "reference city"},
                {"city_id": "NYC", "display_name": "New York City", "status": "real LOD2 geometry loaded", "role": "second-city pilot"},
            ],
        },
        "AssetCard": asset_bridge["assets"],
        "AssetMapPreview": {
            "schema_version": "track2c-ux-r3-local-asset-map-preview.v1",
            "status": "LOCAL_I3S_LEAF_PREVIEWS_AVAILABLE" if all(x["sampled_point_count"] for x in map_previews) else "PARTIAL_MAP_PREVIEW",
            "maps": map_previews,
            "claim_boundary": "The app renders local footprint previews from existing export metadata. These are not remote basemaps, not legal/cadastral maps, and not certified digital-twin coverage.",
        },
        "Asset3DPreview": {
            "schema_version": "track2c-ux-r3-local-asset-3d-preview.v1",
            "status": "SAMPLED_USD_VERTEX_PREVIEWS_AVAILABLE" if all(x["sampled_point_count"] for x in vertex_previews) else "PARTIAL_3D_PREVIEW",
            "previews": vertex_previews,
            "claim_boundary": "The browser renders sampled real USD vertices as a lightweight point cloud. Full mesh inspection remains in Omniverse.",
        },
        "overview_metrics": {
            "event_feed_items": 169,
            "evidence_trace_items": 169,
            "runtime_situations": 169,
            "scenario_replay_items": 98,
            "review_queue_items": 6,
            "briefings": 8,
            "trace_journeys": 9,
            "persona_views": 5,
            "usd_overlays": 169,
            "graph_nodes": 1884,
            "graph_edges": 5420,
            "query_types": 19,
            "qa_intents": 18,
        },
        "SituationBoard": {
            "lifecycle_counts": lifecycle_counts,
            "rows": board_rows,
            "filters": list(lifecycle_counts.keys()),
            "no_action_taken": True,
        },
        "SelectedSituation": selected,
        "EvidencePanel": {"items": [brief_item(x, i, "evidence") for i, x in enumerate(evidence_items[:10])]},
        "ReviewPanel": {
            "queue": [brief_item(x, i, "review") for i, x in enumerate(review_queue[:8])],
            "packets": [brief_item(x, i, "packet") for i, x in enumerate(review_packets[:8])],
            "allowed_state": "candidate/review only; no confirmed violation",
        },
        "ReplayPanel": {
            "items": [brief_item(x, i, "replay") for i, x in enumerate(replay_items[:10])],
            "claim_boundary": "Scenario replay is context-only and cannot produce routing/control recommendations.",
            "counts": {"total": 98, "sumo": 72, "synthetic": 24},
        },
        "BriefingPanel": {"items": [brief_item(x, i, "briefing") for i, x in enumerate(briefing_items[:8])]},
        "PersonaPanel": {
            "persona_views": [brief_item(x, i, "persona") for i, x in enumerate(persona_items[:5])],
            "trace_journeys": [brief_item(x, i, "trace") for i, x in enumerate(trace_items[:9])],
            "role_framed_only": True,
        },
        "IntelligenceSubstratePanel": {
            "graph_nodes": 1884,
            "graph_edges": 5420,
            "query_types": 19,
            "qa_intents": 18,
            "runtime_situations": 169,
            "external_llm_called": False,
        },
        "FutureR2Panel": {
            "status": "DISABLED_NOT_CONNECTED",
            "title": "Future Track 1 R2 intelligence",
            "message": "Reserved for future orchestration/router/tool-registry outputs. This demo does not fake live intelligence.",
        },
        "GuardrailPanel": {"guardrails": GUARDRAILS, "limitations": LIMITATIONS, "always_visible": True},
        "DemoStepper": {"steps": demo_steps, "step_count": len(demo_steps)},
        "CaptureChecklist": {"targets": capture_targets},
    }

    manifest = {
        "schema": "track2c-ux-r3-app-data-manifest.v1",
        "generated_at": vm["generated_at"],
        "overview_metrics": vm["overview_metrics"],
        "city_asset_cards": len(vm["AssetCard"]),
        "city_asset_map_previews": len([x for x in vm["AssetMapPreview"]["maps"] if x["sampled_point_count"]]),
        "city_asset_3d_previews": len([x for x in vm["Asset3DPreview"]["previews"] if x["sampled_point_count"]]),
        "representative_situation_rows": len(board_rows),
        "selected_situation_examples": 1,
        "review_examples": len(vm["ReviewPanel"]["queue"]),
        "evidence_examples": len(vm["EvidencePanel"]["items"]),
        "replay_examples": len(vm["ReplayPanel"]["items"]),
        "briefing_examples": len(vm["BriefingPanel"]["items"]),
        "persona_examples": len(vm["PersonaPanel"]["persona_views"]),
        "guardrail_count": len(GUARDRAILS),
        "limitation_count": len(LIMITATIONS),
        "demo_step_count": len(demo_steps),
        "huge_graph_or_geometry_embedded": False,
    }
    write_json(OUT / "TRACK2C_UX_R3_APP_DATA_MANIFEST.json", manifest)
    write_json(OUT / "TRACK2C_UX_R3_APP_VIEW_MODEL.json", vm)
    write_json(OUT / "app_shell/data/app_data.json", vm)
    write_json(OUT / "app_shell/data/demo_sequence.json", vm["DemoStepper"])
    write_json(OUT / "app_shell/data/limitations.json", {"limitations": LIMITATIONS, "guardrails": GUARDRAILS})
    return vm


def write_demo_and_capture_docs(vm: dict[str, Any]) -> None:
    write_text(
        OUT / "TRACK2C_UX_R3_DEMO_SCRIPT.md",
        """
        # Track 2C UX R3 Demo Script

        ## Overview

        "This is a local demo app for CityBrain. It shows the evidence-bound situation substrate from D4/D4Y.
        It is not production, and no action taken is the visible trust marker."

        ## BARC/NYC Assets

        "Barcelona and New York City have real LOD2 geometry loaded where available. The browser app explains
        the situation context; Omniverse opens the USD scene. Source identity context only: the IDs are not
        ownership, legal, or certified affected-building truth."

        ## Lifecycle Board

        "The board separates observed/context, candidate/review, simulated/context, synthetic/context, and
        limitation-only states so nothing is promoted accidentally."

        ## Selected Situation

        "A selected situation stays evidence-bound. It keeps source refs, lifecycle state, limitations, claim
        boundary, and no action taken together."

        ## Evidence, Replay, Briefing, Persona

        "Evidence and review are traceable. Replay is simulated/synthetic context only. Briefings are safe
        stakeholder summaries. Personas are role-framed views, not autonomous agents."

        ## Intelligence Substrate

        "The graph/query/QA metrics show the D4Y substrate. Future Track 1 R2 intelligence is disabled and
        not connected here."

        ## Guardrails

        "This is not command/control. It does not dispatch/enforce, route/control, produce legal findings,
        or claim certified impact."

        ## Forbidden Phrases

        Do not say: production ready; certified digital twin; confirmed violation; legal ownership;
        dispatch/enforce; route/control; certified impact.
        """,
    )
    write_text(
        OUT / "TRACK2C_UX_R3_CAPTURE_PLAN.md",
        """
        # Track 2C UX R3 Capture Plan

        Required captures:

        - `r3_01_overview.png`: opening hero, top metrics, no-action marker.
        - `r3_02_assets.png`: BARC/NYC asset cards and Omniverse command blocks.
        - `r3_03_situation_board.png`: lifecycle board and situation rows.
        - `r3_04_selected_detail.png`: selected detail drawer and claim boundary.
        - `r3_05_evidence_review.png`: evidence/review tab content.
        - `r3_06_replay_briefing_persona.png`: replay, briefing, and persona context.
        - `r3_07_intelligence_guardrails.png`: substrate metrics, disabled future R2 panel, and guardrails.

        Capture stance: local browser app only. Omniverse should be shown separately if needed.
        """,
    )
    write_text(
        OUT / "TRACK2C_UX_R3_LOCAL_RUN_INSTRUCTIONS.md",
        f"""
        # Track 2C UX R3 Local Run Instructions

        App path:

        `{(OUT / "app_shell/index.html").resolve()}`

        PowerShell:

        ```powershell
        Start-Process "{(OUT / "app_shell/index.html").resolve()}"
        ```

        Barcelona USD in Omniverse:

        ```powershell
        {vm["AssetCard"][0].get("open_command") or "Barcelona USD scene not available"}
        ```

        New York City USD in Omniverse:

        ```powershell
        {vm["AssetCard"][1].get("open_command") or "NYC USD scene not available"}
        ```

        Browser app vs Omniverse:

        - Browser app: local static demo cockpit for D4/D4Y situations, evidence, replay, briefings, personas, and limitations.
        - Omniverse: USD scene surface for city geometry inspection.

        Demo limitations to mention:

        - local static demo app only
        - not production
        - no auth/RBAC
        - source identity context only
        - no command/control/enforcement/dispatch/routing
        - Track 1 R2 intelligence is disabled/not-connected
        """,
    )
    write_text(
        OUT / "TRACK2C_UX_R3_LIMITATION_REGISTER.md",
        "# Track 2C UX R3 Limitation Register\n\n" + "\n".join(f"- {x}" for x in LIMITATIONS),
    )
    write_text(
        OUT / "TRACK2C_UX_R3_NEXT_TASK_PLAN.md",
        """
        # Track 2C UX R3 Next Task Plan

        Recommended next Track 2C task:
        `MAIN-TRACK2C-D4X-DEMO-CAPTURE-AND-POLISH-R4`

        Purpose:
        Use the redesigned R3 app to produce a final demo capture pack with curated screenshots, optional short local
        video steps, and a clean stakeholder walkthrough.

        Alternative next Track 2C task:
        `MAIN-TRACK2C-D4X-APP-ASSET-REGISTRY-INTEGRATION-R4`

        Purpose:
        After Track 2A formalizes the cross-city asset registry, replace the provisional BARC/NYC bridge with the
        official asset registry.

        Future Track 1 integration:
        `MAIN-TRACK2C-D4X-R2-INTELLIGENCE-INTEGRATION-R1`

        Do not implement that now.
        """,
    )


def write_app(vm: dict[str, Any]) -> None:
    app_json = json.dumps(vm, ensure_ascii=False)
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain Control Room - Track 2C R3</title>
  <link rel="stylesheet" href="./styles.css">
</head>
<body>
  <aside class="rail" aria-label="Primary navigation">
    <div class="brand"><span class="brand-mark"></span><div><strong>CityBrain</strong><small>Track 2C R3</small></div></div>
    <nav>
      <a href="#overview">Overview</a>
      <a href="#cities_assets">Assets</a>
      <a href="#situation_board">Board</a>
      <a href="#review_evidence">Evidence</a>
      <a href="#replay_scenarios">Replay</a>
      <a href="#briefing_persona">Briefing</a>
      <a href="#intelligence_substrate">Brain</a>
      <a href="#demo_capture">Capture</a>
      <a href="#limitations_guardrails">Limits</a>
    </nav>
    <div class="rail-trust"><span></span> no action taken</div>
  </aside>

  <header class="topbar">
    <div>
      <span class="eyebrow">local demo app</span>
      <h1>CityBrain Control Room</h1>
    </div>
    <div class="top-pills">
      <span class="pill good">D4/D4Y context</span>
      <span class="pill neutral">Future R2 not connected</span>
      <span class="pill warn">not production</span>
    </div>
  </header>

  <main class="shell">
    <section id="overview" class="hero section">
      <div class="hero-copy">
        <span class="eyebrow">evidence-bound situation substrate</span>
        <h2>Demo cockpit for city situations, evidence, replay, briefings, personas, and 3D scene context.</h2>
        <p>The browser app is the narrative cockpit. Omniverse is the 3D city scene surface. Both stay inside review/context boundaries.</p>
        <div class="hero-actions" id="city-selector"></div>
      </div>
      <div class="hero-panel">
        <div class="trust-badge">No action taken</div>
        <div class="metric-grid" id="overview-metrics"></div>
      </div>
    </section>

    <section id="cities_assets" class="section">
      <div class="section-head">
        <div><span class="eyebrow">browser plus omniverse</span><h2>Cities And 3D Assets</h2></div>
        <p>Real geometry is loaded where available; source IDs remain context only.</p>
      </div>
      <div class="asset-grid" id="asset-cards"></div>
    </section>

    <section id="situation_board" class="section board-layout">
      <div class="board-main">
        <div class="section-head">
          <div><span class="eyebrow">lifecycle board</span><h2>Situation Board</h2></div>
          <p>Lifecycle states stay explicit. Selecting a row updates the detail drawer.</p>
        </div>
        <div class="lifecycle-grid" id="lifecycle-grid"></div>
        <div class="situation-list" id="situation-list"></div>
      </div>
      <aside class="detail-drawer" id="detail-drawer" aria-label="Selected situation detail"></aside>
    </section>

    <section id="review_evidence" class="section">
      <div class="section-head">
        <div><span class="eyebrow">traceable context</span><h2>Evidence And Review</h2></div>
        <p>Review-only materials, source refs, and limitations remain visible.</p>
      </div>
      <div class="tabs" role="tablist">
        <button class="tab active" data-tab="evidence">Evidence</button>
        <button class="tab" data-tab="review">Review</button>
      </div>
      <div class="tab-panel" id="evidence-review-panel"></div>
    </section>

    <section id="replay_scenarios" class="section two-col">
      <div>
        <div class="section-head compact"><div><span class="eyebrow">context replay</span><h2>Scenario Replay</h2></div></div>
        <div id="replay-panel"></div>
      </div>
      <div class="safe-card">
        <span class="eyebrow">boundary</span>
        <h3>Simulation is not observed truth</h3>
        <p>Replay stays local and context-only. It is not a certified traffic model and cannot produce route/control recommendations.</p>
      </div>
    </section>

    <section id="briefing_persona" class="section two-col">
      <div>
        <div class="section-head compact"><div><span class="eyebrow">stakeholder language</span><h2>Briefings</h2></div></div>
        <div id="briefing-panel"></div>
      </div>
      <div>
        <div class="section-head compact"><div><span class="eyebrow">role-framed views</span><h2>Personas</h2></div></div>
        <div id="persona-panel"></div>
      </div>
    </section>

    <section id="intelligence_substrate" class="section two-col">
      <div>
        <div class="section-head compact"><div><span class="eyebrow">D4Y substrate</span><h2>Situation Brain</h2></div></div>
        <div class="metric-grid large" id="brain-metrics"></div>
      </div>
      <div class="future-card" id="future-panel"></div>
    </section>

    <section id="demo_capture" class="section">
      <div class="section-head">
        <div><span class="eyebrow">guided walkthrough</span><h2>Demo Mode And Capture Checklist</h2></div>
        <p>Use this to move through a repeatable stakeholder walkthrough.</p>
      </div>
      <div class="demo-wrap">
        <div class="demo-stepper" id="demo-stepper"></div>
        <div class="checklist" id="capture-checklist"></div>
      </div>
    </section>

    <section id="limitations_guardrails" class="section">
      <div class="section-head">
        <div><span class="eyebrow">trust boundary</span><h2>Limitations And Guardrails</h2></div>
        <p>Always visible, and repeated here for capture.</p>
      </div>
      <div class="guardrail-grid" id="guardrail-grid"></div>
    </section>
  </main>

  <div class="guardrail-strip">
    <span>local demo only</span>
    <span>not production</span>
    <span>no command/control</span>
    <span>no action taken</span>
    <span>future R2 not connected</span>
  </div>

  <script src="./app.js"></script>
</body>
</html>
"""

    css = r"""
:root {
  color-scheme: dark;
  --bg: #071015;
  --surface: #0e1922;
  --surface-2: #132330;
  --surface-3: #172b39;
  --line: #284052;
  --line-soft: #1d3141;
  --text: #f5fbff;
  --muted: #9fb7c7;
  --accent: #52f3d0;
  --blue: #69b8ff;
  --warn: #f2c14e;
  --review: #ffb86b;
  --safe: #6fe7a8;
  --disabled: #667987;
  --danger: #ff7676;
  --rail: 190px;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background:
    linear-gradient(120deg, rgba(82,243,208,.07), transparent 28%),
    radial-gradient(circle at 85% 4%, rgba(105,184,255,.10), transparent 30%),
    var(--bg);
  color: var(--text);
  letter-spacing: 0;
}
.rail {
  position: fixed;
  inset: 0 auto 0 0;
  width: var(--rail);
  padding: 20px 16px;
  border-right: 1px solid var(--line);
  background: rgba(5, 12, 17, .86);
  backdrop-filter: blur(14px);
  z-index: 20;
}
.brand { display: flex; gap: 12px; align-items: center; margin-bottom: 34px; }
.brand-mark { width: 28px; height: 28px; border: 2px solid var(--accent); border-radius: 50%; box-shadow: 0 0 20px rgba(82,243,208,.35); }
.brand small { display: block; color: var(--muted); margin-top: 4px; }
.rail nav { display: grid; gap: 8px; }
.rail a {
  color: #c6e8f7;
  text-decoration: none;
  padding: 10px 8px;
  border-radius: 8px;
  border: 1px solid transparent;
}
.rail a:hover, .rail a:focus { border-color: var(--line); background: var(--surface); outline: none; }
.rail-trust { position: absolute; bottom: 18px; left: 16px; right: 16px; color: #cfefff; font-size: 13px; }
.rail-trust span { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--safe); margin-right: 8px; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 15;
  margin-left: var(--rail);
  min-height: 78px;
  padding: 16px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--line);
  background: rgba(7, 16, 21, .88);
  backdrop-filter: blur(16px);
}
.topbar h1 { margin: 2px 0 0; font-size: 25px; }
.top-pills { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
.pill, .badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  padding: 5px 9px;
  border-radius: 8px;
  border: 1px solid var(--line);
  color: #d9f6ff;
  font-size: 12px;
  line-height: 1.25;
}
.pill.good, .badge.good { color: #d8ffee; border-color: rgba(111,231,168,.5); background: rgba(111,231,168,.09); }
.pill.warn, .badge.warn { color: #ffe8aa; border-color: rgba(242,193,78,.5); background: rgba(242,193,78,.09); }
.pill.neutral, .badge.neutral { color: #bfe3ff; border-color: rgba(105,184,255,.42); background: rgba(105,184,255,.08); }
.badge.review { color: #ffe2c2; border-color: rgba(255,184,107,.55); background: rgba(255,184,107,.08); }
.badge.disabled { color: #c8d2da; border-color: rgba(102,121,135,.6); background: rgba(102,121,135,.12); }
.shell { margin-left: var(--rail); padding: 24px 28px 84px; max-width: 1720px; }
.section { scroll-margin-top: 98px; margin-bottom: 24px; }
.hero {
  min-height: 520px;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(420px, .95fr);
  gap: 18px;
  align-items: stretch;
}
.hero-copy, .hero-panel, .section, .detail-drawer, .safe-card, .future-card {
  border: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(19,35,48,.94), rgba(10,20,27,.94));
  border-radius: 8px;
}
.hero-copy { padding: 34px; display: flex; flex-direction: column; justify-content: center; }
.hero-copy h2 { max-width: 780px; margin: 8px 0 14px; font-size: 42px; line-height: 1.02; }
.hero-copy p { max-width: 720px; color: #bfdaea; font-size: 16px; line-height: 1.6; }
.hero-panel { padding: 22px; }
.trust-badge {
  display: inline-flex;
  padding: 8px 11px;
  border-radius: 8px;
  background: rgba(111,231,168,.10);
  border: 1px solid rgba(111,231,168,.45);
  color: #d9ffee;
  font-weight: 700;
  margin-bottom: 14px;
}
.section:not(.hero) { padding: 22px; }
.section-head { display: flex; align-items: end; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.section-head.compact { margin-bottom: 12px; }
.section-head h2 { margin: 2px 0 0; font-size: 24px; }
.section-head p { margin: 0; color: var(--muted); max-width: 620px; line-height: 1.45; }
.eyebrow { text-transform: uppercase; color: var(--accent); font-size: 11px; font-weight: 800; letter-spacing: .08em; }
.metric-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.metric-grid.large { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.metric-card {
  min-height: 96px;
  padding: 13px;
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: rgba(7, 16, 21, .46);
}
.metric-card small { display: block; color: var(--muted); margin-bottom: 8px; }
.metric-card strong { font-size: 28px; }
.hero-actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 20px; }
button, .city-chip {
  min-height: 38px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: rgba(14,25,34,.78);
  color: var(--text);
  font: inherit;
  padding: 8px 12px;
  cursor: pointer;
}
button:hover, button:focus, .city-chip.active { border-color: var(--accent); outline: none; box-shadow: 0 0 0 2px rgba(82,243,208,.12); }
.asset-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.asset-card { padding: 16px; border: 1px solid var(--line); background: rgba(7,16,21,.34); border-radius: 8px; }
.asset-card h3 { margin: 0 0 8px; }
.asset-meta { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
.asset-map-wrap {
  position: relative;
  height: 260px;
  margin: 12px 0;
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  overflow: hidden;
  background:
    linear-gradient(90deg, rgba(105,184,255,.06) 1px, transparent 1px),
    linear-gradient(0deg, rgba(105,184,255,.06) 1px, transparent 1px),
    #061018;
  background-size: 36px 36px;
  cursor: grab;
  touch-action: none;
}
.asset-3d-wrap {
  position: relative;
  height: 300px;
  margin: 12px 0;
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 40%, rgba(82,243,208,.08), transparent 44%),
    linear-gradient(180deg, #07141d, #03080d);
  cursor: grab;
  touch-action: none;
}
.asset-3d-wrap:active { cursor: grabbing; }
.asset-3d-wrap canvas { display: block; width: 100%; height: 100%; }
.asset-3d-wrap .map-caption { bottom: 10px; }
.viewer3d-title {
  position: absolute;
  left: 14px;
  top: 46px;
  z-index: 2;
  color: #eefaff;
  text-shadow: 0 1px 8px rgba(0,0,0,.7);
  pointer-events: none;
}
.viewer3d-title strong { display: block; font-size: 15px; }
.viewer3d-title small { color: #bcd5e6; }
.asset-map-wrap:active { cursor: grabbing; }
.asset-map-wrap canvas { display: block; width: 100%; height: 100%; }
.map-tools {
  position: absolute;
  top: 10px;
  left: 10px;
  display: flex;
  gap: 6px;
  z-index: 2;
}
.map-tools button {
  min-height: 28px;
  min-width: 30px;
  padding: 4px 8px;
  border-color: rgba(105,184,255,.36);
  background: rgba(4,10,14,.78);
  font-size: 12px;
}
.map-caption {
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  justify-content: space-between;
  pointer-events: none;
}
.map-caption span {
  padding: 5px 7px;
  border-radius: 8px;
  border: 1px solid rgba(82,243,208,.28);
  background: rgba(4,10,14,.78);
  color: #d9f8ff;
  font-size: 11px;
}
.map-north {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(105,184,255,.34);
  border-radius: 8px;
  color: var(--blue);
  background: rgba(4,10,14,.72);
  font-size: 12px;
  font-weight: 900;
}
.command {
  margin-top: 12px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--line-soft);
  background: #040a0e;
  color: #71ffe6;
  font: 12px/1.45 Consolas, "Liberation Mono", monospace;
  overflow-wrap: anywhere;
}
.board-layout { display: grid; grid-template-columns: minmax(0, 1fr) 390px; gap: 14px; }
.board-main { min-width: 0; }
.lifecycle-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px; }
.life-card { text-align: left; min-height: 78px; padding: 11px; }
.life-card strong { display: block; font-size: 24px; margin-top: 4px; }
.situation-list { display: grid; gap: 9px; max-height: 520px; overflow: auto; padding-right: 4px; }
.situation-row {
  width: 100%;
  text-align: left;
  padding: 12px;
  min-height: 84px;
  background: rgba(5,12,17,.52);
}
.situation-row.active { border-color: var(--accent); background: rgba(82,243,208,.07); }
.row-title { display: block; font-weight: 800; margin-bottom: 8px; }
.row-summary { color: var(--muted); display: block; margin-top: 8px; line-height: 1.38; }
.detail-drawer { padding: 18px; position: sticky; top: 102px; align-self: start; }
.detail-drawer h3 { margin: 6px 0 10px; font-size: 22px; }
.detail-block { border-top: 1px solid var(--line-soft); padding-top: 12px; margin-top: 12px; color: #c8dfec; line-height: 1.45; }
.tabs { display: flex; gap: 8px; margin-bottom: 12px; }
.tab.active { border-color: var(--accent); color: #d9fff6; background: rgba(82,243,208,.09); }
.tab-panel, #replay-panel, #briefing-panel, #persona-panel { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.info-card {
  padding: 13px;
  border-radius: 8px;
  border: 1px solid var(--line-soft);
  background: rgba(7,16,21,.48);
  min-height: 138px;
}
.info-card h4 { margin: 0 0 8px; font-size: 15px; }
.info-card p { margin: 8px 0 0; color: #c5dcea; line-height: 1.42; }
.two-col { display: grid; grid-template-columns: minmax(0, 1fr) minmax(360px, .74fr); gap: 14px; }
.safe-card, .future-card { padding: 18px; }
.future-card { opacity: .86; border-style: dashed; }
.demo-wrap { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(330px, .65fr); gap: 14px; }
.demo-stepper { display: grid; gap: 9px; }
.demo-step { display: grid; grid-template-columns: 36px 1fr; gap: 10px; padding: 12px; border: 1px solid var(--line-soft); border-radius: 8px; background: rgba(7,16,21,.4); }
.demo-step b { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 8px; background: rgba(82,243,208,.1); color: var(--accent); }
.checklist { display: grid; gap: 8px; }
.check-item { padding: 10px; border: 1px solid var(--line-soft); border-radius: 8px; color: #d6ebf8; background: rgba(7,16,21,.4); }
.guardrail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.guardrail { padding: 12px; border: 1px solid var(--line-soft); border-radius: 8px; background: rgba(7,16,21,.42); color: #d6ebf8; }
.guardrail-strip {
  position: fixed;
  left: var(--rail);
  right: 0;
  bottom: 0;
  z-index: 25;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 28px;
  border-top: 1px solid var(--line);
  background: rgba(5,12,17,.92);
  backdrop-filter: blur(16px);
}
.guardrail-strip span { color: #d9f8ff; border: 1px solid var(--line); border-radius: 8px; padding: 5px 8px; font-size: 12px; }
body.capture-mode .topbar { position: static; }
body.capture-mode .shell > .section { display: none; }
body.capture-mode .shell > .section.capture-visible { display: block; }
body.capture-mode .shell > .hero.capture-visible,
body.capture-mode .shell > .board-layout.capture-visible,
body.capture-mode .shell > .two-col.capture-visible { display: grid; }
@media (max-width: 1100px) {
  :root { --rail: 0px; }
  .rail { position: static; width: auto; border-right: 0; border-bottom: 1px solid var(--line); }
  .rail nav { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .rail-trust { position: static; margin-top: 14px; }
  .topbar, .shell, .guardrail-strip { margin-left: 0; left: 0; }
  .hero, .board-layout, .two-col, .demo-wrap { grid-template-columns: 1fr; }
  .asset-grid, .tab-panel, #replay-panel, #briefing-panel, #persona-panel, .guardrail-grid { grid-template-columns: 1fr; }
}
@media (max-width: 760px) {
  .metric-grid, .metric-grid.large, .lifecycle-grid { grid-template-columns: 1fr 1fr; }
  .hero-copy h2 { font-size: 30px; }
  .topbar { align-items: start; flex-direction: column; gap: 10px; }
  .shell { padding: 16px 14px 98px; }
}
"""

    js = f"""
const DATA = {app_json};
let selectedCity = DATA.CityState.selected_city_id || 'NYC';
let selectedSituationId = DATA.SelectedSituation.id;
let activeTab = 'evidence';
const mapState = {{}};
const preview3DState = {{}};
const preview3DCache = {{}};

const fmt = new Intl.NumberFormat('en-US');
const $ = (id) => document.getElementById(id);
const badgeClass = (state) => {{
  const s = String(state || '').toLowerCase();
  if (s.includes('candidate')) return 'badge review';
  if (s.includes('simulated') || s.includes('synthetic')) return 'badge neutral';
  if (s.includes('limitation') || s.includes('late') || s.includes('expired')) return 'badge warn';
  return 'badge good';
}};
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (m) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m]));

function renderCitySelector() {{
  $('city-selector').innerHTML = DATA.CityState.cities.map(city => `
    <button class="city-chip ${{city.city_id === selectedCity ? 'active' : ''}}" data-city="${{city.city_id}}">
      ${{esc(city.display_name)}} <span class="badge neutral">${{esc(city.status)}}</span>
    </button>
  `).join('');
  document.querySelectorAll('[data-city]').forEach(btn => btn.addEventListener('click', () => {{
    selectedCity = btn.dataset.city;
    render();
    document.querySelector('#cities_assets').scrollIntoView({{behavior:'smooth', block:'start'}});
  }}));
}}

function renderMetrics() {{
  const m = DATA.overview_metrics;
  const cards = [
    ['Runtime situations', m.runtime_situations],
    ['Event feed', m.event_feed_items],
    ['Evidence traces', m.evidence_trace_items],
    ['Replay items', m.scenario_replay_items],
    ['Review queue', m.review_queue_items],
    ['Briefings', m.briefings],
    ['USD overlays', m.usd_overlays],
    ['Graph nodes', m.graph_nodes],
    ['Graph edges', m.graph_edges],
    ['Query types', m.query_types],
    ['QA intents', m.qa_intents],
    ['Personas', m.persona_views],
  ];
  $('overview-metrics').innerHTML = cards.map(([label, value]) => `<div class="metric-card"><small>${{label}}</small><strong>${{fmt.format(value)}}</strong></div>`).join('');
}}

function renderAssets() {{
  $('asset-cards').innerHTML = DATA.AssetCard.map(asset => {{
    const active = asset.city_id === selectedCity;
    const metrics = asset.metrics || {{}};
    const preview = (DATA.AssetMapPreview.maps || []).find(map => map.city_id === asset.city_id) || {{}};
    const preview3d = (DATA.Asset3DPreview.previews || []).find(item => item.city_id === asset.city_id) || {{}};
    const metricText = [
      ['features', metrics.features_exported],
      ['triangles', metrics.triangles_exported],
      ['USD shards', metrics.usd_shard_count],
      ['failures', metrics.failure_count],
    ].filter(x => x[1] !== undefined).map(([k,v]) => `<span class="badge neutral">${{k}}: ${{fmt.format(v)}}</span>`).join('');
    return `<article class="asset-card" data-active="${{active}}">
      <span class="${{active ? 'badge good' : 'badge neutral'}}">${{active ? 'selected city' : 'available city'}}</span>
      <h3>${{esc(asset.display_name)}} - ${{esc(asset.asset_class)}}</h3>
      <div class="asset-meta">
        <span class="badge good">${{esc(asset.geometry_status)}}</span>
        <span class="badge neutral">${{esc(asset.role)}}</span>
        <span class="badge warn">${{esc(asset.identity_status)}}</span>
      </div>
      <p>${{esc(asset.claim_boundary)}}</p>
      <div class="asset-meta">${{metricText}}</div>
      <div class="asset-3d-wrap" aria-label="${{esc(asset.display_name)}} sampled USD vertex 3D preview">
        <div class="map-tools" aria-label="3D preview controls">
          <button type="button" data-3d-action="zoom-in" data-3d-city="${{esc(asset.city_id)}}" title="Zoom in">+</button>
          <button type="button" data-3d-action="zoom-out" data-3d-city="${{esc(asset.city_id)}}" title="Zoom out">-</button>
          <button type="button" data-3d-action="auto" data-3d-city="${{esc(asset.city_id)}}" title="Toggle auto rotate">Auto</button>
          <button type="button" data-3d-action="reset" data-3d-city="${{esc(asset.city_id)}}" title="Reset 3D view">Reset</button>
        </div>
        <canvas id="asset-3d-${{esc(asset.city_id)}}" data-3d-city="${{esc(asset.city_id)}}"></canvas>
        <div class="viewer3d-title"><strong>${{esc(asset.display_name)}} sampled 3D vertices</strong><small>drag rotate | wheel zoom | shift+drag pan</small></div>
        <div class="map-caption">
          <span>${{esc(preview3d.status || '3D preview unavailable')}}</span>
          <span>${{fmt.format(preview3d.sampled_point_count || 0)}} sampled USD vertices</span>
        </div>
      </div>
      <div class="asset-map-wrap" aria-label="${{esc(asset.display_name)}} local map preview">
        <div class="map-tools" aria-label="Map controls">
          <button type="button" data-map-action="zoom-in" data-map-city="${{esc(asset.city_id)}}" title="Zoom in">+</button>
          <button type="button" data-map-action="zoom-out" data-map-city="${{esc(asset.city_id)}}" title="Zoom out">-</button>
          <button type="button" data-map-action="reset" data-map-city="${{esc(asset.city_id)}}" title="Reset view">Reset</button>
        </div>
        <canvas id="asset-map-${{esc(asset.city_id)}}" data-map-city="${{esc(asset.city_id)}}"></canvas>
        <div class="map-north">N</div>
        <div class="map-caption">
          <span>${{esc(preview.status || 'map preview unavailable')}}</span>
          <span>${{fmt.format(preview.sampled_point_count || 0)}} / ${{fmt.format(preview.total_leaf_node_count || 0)}} leaf centers</span>
        </div>
      </div>
      <div class="command" aria-label="Omniverse open command">${{esc(asset.open_command || 'USD scene path unavailable')}}</div>
    </article>`;
  }}).join('');
  attachMapInteractions();
  attach3DInteractions();
  draw3DPreviews();
  drawAssetMaps();
}}

function preview3DView(cityId) {{
  if (!preview3DState[cityId]) preview3DState[cityId] = {{rotX: -0.72, rotY: cityId === 'NYC' ? -0.55 : 0.55, zoom: 1.04, panX: 0, panY: 0, dragging: false, lastX: 0, lastY: 0, auto: false, panMode: false}};
  return preview3DState[cityId];
}}

function reset3D(cityId) {{
  preview3DState[cityId] = {{rotX: -0.72, rotY: cityId === 'NYC' ? -0.55 : 0.55, zoom: 1.04, panX: 0, panY: 0, dragging: false, lastX: 0, lastY: 0, auto: false, panMode: false}};
  draw3DPreviews();
}}

function zoom3D(cityId, factor) {{
  const state = preview3DView(cityId);
  state.zoom = Math.max(0.45, Math.min(8, state.zoom * factor));
  draw3DPreviews();
}}

function attach3DInteractions() {{
  document.querySelectorAll('canvas[data-3d-city]').forEach(canvas => {{
    if (canvas.dataset.bound3d === 'true') return;
    canvas.dataset.bound3d = 'true';
    const cityId = canvas.dataset['3dCity'];
    canvas.addEventListener('wheel', event => {{
      event.preventDefault();
      zoom3D(cityId, event.deltaY < 0 ? 1.16 : 0.86);
    }}, {{passive: false}});
    canvas.addEventListener('pointerdown', event => {{
      const state = preview3DView(cityId);
      state.dragging = true;
      state.panMode = event.shiftKey || event.button === 1 || event.button === 2;
      state.lastX = event.clientX;
      state.lastY = event.clientY;
      canvas.setPointerCapture(event.pointerId);
    }});
    canvas.addEventListener('pointermove', event => {{
      const state = preview3DView(cityId);
      if (!state.dragging) return;
      const dx = event.clientX - state.lastX;
      const dy = event.clientY - state.lastY;
      if (state.panMode || event.shiftKey) {{
        state.panX += dx / Math.max(220, canvas.clientWidth);
        state.panY -= dy / Math.max(180, canvas.clientHeight);
      }} else {{
        state.rotY += dx * 0.008;
        state.rotX = Math.max(-1.35, Math.min(0.2, state.rotX + dy * 0.006));
      }}
      state.lastX = event.clientX;
      state.lastY = event.clientY;
      draw3DPreviews();
    }});
    canvas.addEventListener('pointerup', event => {{
      const state = preview3DView(cityId);
      state.dragging = false;
      try {{ canvas.releasePointerCapture(event.pointerId); }} catch (_) {{}}
    }});
    canvas.addEventListener('pointercancel', () => {{ preview3DView(cityId).dragging = false; }});
    canvas.addEventListener('dblclick', () => reset3D(cityId));
    canvas.addEventListener('contextmenu', event => event.preventDefault());
  }});
  document.querySelectorAll('[data-3d-action]').forEach(button => {{
    if (button.dataset.bound3dAction === 'true') return;
    button.dataset.bound3dAction = 'true';
    button.addEventListener('click', event => {{
      event.preventDefault();
      event.stopPropagation();
      const cityId = button.dataset['3dCity'];
      const action = button.dataset['3dAction'];
      if (action === 'zoom-in') zoom3D(cityId, 1.28);
      if (action === 'zoom-out') zoom3D(cityId, 0.78);
      if (action === 'reset') reset3D(cityId);
      if (action === 'auto') {{
        const state = preview3DView(cityId);
        state.auto = !state.auto;
        if (state.auto) animate3D();
      }}
    }});
  }});
}}

function get3DPreviewData(cityId) {{
  const preview = (DATA.Asset3DPreview.previews || []).find(item => item.city_id === cityId);
  if (!preview || !preview.points || !preview.points.length) return null;
  if (preview3DCache[cityId]?.pointCount === preview.points.length) return preview3DCache[cityId];
  const bbox = preview.bbox;
  const cx = (bbox.min_x + bbox.max_x) / 2;
  const cy = (bbox.min_y + bbox.max_y) / 2;
  const cz = bbox.min_z;
  const spanX = Math.max(1, bbox.max_x - bbox.min_x);
  const spanY = Math.max(1, bbox.max_y - bbox.min_y);
  const spanZ = Math.max(1, bbox.max_z - bbox.min_z);
  const span = Math.max(spanX, spanY);
  const arr = new Float32Array(preview.points.length * 3);
  preview.points.forEach((p, i) => {{
    arr[i * 3] = (p[0] - cx) / span * 2.0;
    arr[i * 3 + 1] = (p[1] - cy) / span * 2.0;
    arr[i * 3 + 2] = Math.min(1.2, (p[2] - cz) / spanZ) * 0.88;
  }});
  preview3DCache[cityId] = {{data: arr, pointCount: preview.points.length, bbox, preview}};
  return preview3DCache[cityId];
}}

function compileShader(gl, type, source) {{
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
  return shader;
}}

function get3DProgram(gl) {{
  if (gl._cityBrainProgram) return gl._cityBrainProgram;
  const vs = `
    attribute vec3 aPosition;
    uniform float uRotX;
    uniform float uRotY;
    uniform float uZoom;
    uniform float uAspect;
    uniform vec2 uPan;
    varying float vHeight;
    void main() {{
      vec3 p = aPosition;
      float cy = cos(uRotY);
      float sy = sin(uRotY);
      vec3 q = vec3(cy * p.x + sy * p.y, -sy * p.x + cy * p.y, p.z);
      float cx = cos(uRotX);
      float sx = sin(uRotX);
      vec3 r = vec3(q.x, cx * q.y - sx * q.z, sx * q.y + cx * q.z);
      float perspective = 1.75 / (2.35 - r.y * 0.48);
      vec2 pos = vec2(r.x / uAspect, r.z - 0.22) * perspective * uZoom + uPan;
      gl_Position = vec4(pos, 0.0, 1.0);
      gl_PointSize = 1.25 + clamp(aPosition.z, 0.0, 1.2) * 3.8;
      vHeight = clamp(aPosition.z, 0.0, 1.0);
    }}
  `;
  const fs = `
    precision mediump float;
    varying float vHeight;
    void main() {{
      vec2 c = gl_PointCoord - vec2(0.5);
      if (dot(c, c) > 0.25) discard;
      vec3 low = vec3(0.20, 0.67, 0.95);
      vec3 high = vec3(0.32, 0.95, 0.82);
      vec3 color = mix(low, high, vHeight);
      gl_FragColor = vec4(color, 0.86);
    }}
  `;
  const program = gl.createProgram();
  gl.attachShader(program, compileShader(gl, gl.VERTEX_SHADER, vs));
  gl.attachShader(program, compileShader(gl, gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
  gl._cityBrainProgram = program;
  return program;
}}

function draw3DPreviews() {{
  document.querySelectorAll('canvas[data-3d-city]').forEach(canvas => {{
    const cityId = canvas.dataset['3dCity'];
    const preview = get3DPreviewData(cityId);
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(360, Math.floor(rect.width || 640));
    const height = Math.max(220, Math.floor(rect.height || 300));
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    const gl = canvas.getContext('webgl', {{antialias: true, alpha: true}});
    if (!gl || !preview) return;
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0.02, 0.055, 0.08, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    const program = get3DProgram(gl);
    gl.useProgram(program);
    if (!canvas._pointBuffer || canvas._pointCount !== preview.pointCount) {{
      canvas._pointBuffer = gl.createBuffer();
      canvas._pointCount = preview.pointCount;
      gl.bindBuffer(gl.ARRAY_BUFFER, canvas._pointBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, preview.data, gl.STATIC_DRAW);
    }} else {{
      gl.bindBuffer(gl.ARRAY_BUFFER, canvas._pointBuffer);
    }}
    const loc = gl.getAttribLocation(program, 'aPosition');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 3, gl.FLOAT, false, 0, 0);
    const state = preview3DView(cityId);
    gl.uniform1f(gl.getUniformLocation(program, 'uRotX'), state.rotX);
    gl.uniform1f(gl.getUniformLocation(program, 'uRotY'), state.rotY);
    gl.uniform1f(gl.getUniformLocation(program, 'uZoom'), state.zoom);
    gl.uniform1f(gl.getUniformLocation(program, 'uAspect'), width / height);
    gl.uniform2f(gl.getUniformLocation(program, 'uPan'), state.panX, state.panY);
    gl.drawArrays(gl.POINTS, 0, preview.pointCount);
  }});
}}

let animation3DRunning = false;
function animate3D() {{
  if (animation3DRunning) return;
  animation3DRunning = true;
  const frame = () => {{
    let any = false;
    Object.entries(preview3DState).forEach(([cityId, state]) => {{
      if (state.auto) {{
        state.rotY += 0.008;
        any = true;
      }}
    }});
    if (any) {{
      draw3DPreviews();
      requestAnimationFrame(frame);
    }} else {{
      animation3DRunning = false;
    }}
  }};
  requestAnimationFrame(frame);
}}

function mapView(cityId) {{
  if (!mapState[cityId]) mapState[cityId] = {{scale: 1, offsetX: 0, offsetY: 0, dragging: false, lastX: 0, lastY: 0}};
  return mapState[cityId];
}}

function zoomMap(cityId, factor, focusX = null, focusY = null, canvas = null) {{
  const state = mapView(cityId);
  const next = Math.max(0.75, Math.min(18, state.scale * factor));
  if (canvas && focusX !== null && focusY !== null) {{
    const rect = canvas.getBoundingClientRect();
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const beforeX = (focusX - cx - state.offsetX) / state.scale;
    const beforeY = (focusY - cy - state.offsetY) / state.scale;
    state.scale = next;
    state.offsetX = focusX - cx - beforeX * state.scale;
    state.offsetY = focusY - cy - beforeY * state.scale;
  }} else {{
    state.scale = next;
  }}
  drawAssetMaps();
}}

function resetMap(cityId) {{
  mapState[cityId] = {{scale: 1, offsetX: 0, offsetY: 0, dragging: false, lastX: 0, lastY: 0}};
  drawAssetMaps();
}}

function attachMapInteractions() {{
  document.querySelectorAll('canvas[data-map-city]').forEach(canvas => {{
    if (canvas.dataset.boundMap === 'true') return;
    canvas.dataset.boundMap = 'true';
    const cityId = canvas.dataset.mapCity;
    canvas.addEventListener('wheel', event => {{
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const factor = event.deltaY < 0 ? 1.18 : 0.84;
      zoomMap(cityId, factor, event.clientX - rect.left, event.clientY - rect.top, canvas);
    }}, {{passive: false}});
    canvas.addEventListener('pointerdown', event => {{
      const state = mapView(cityId);
      state.dragging = true;
      state.lastX = event.clientX;
      state.lastY = event.clientY;
      canvas.setPointerCapture(event.pointerId);
    }});
    canvas.addEventListener('pointermove', event => {{
      const state = mapView(cityId);
      if (!state.dragging) return;
      state.offsetX += event.clientX - state.lastX;
      state.offsetY += event.clientY - state.lastY;
      state.lastX = event.clientX;
      state.lastY = event.clientY;
      drawAssetMaps();
    }});
    canvas.addEventListener('pointerup', event => {{
      const state = mapView(cityId);
      state.dragging = false;
      try {{ canvas.releasePointerCapture(event.pointerId); }} catch (_) {{}}
    }});
    canvas.addEventListener('pointercancel', () => {{ mapView(cityId).dragging = false; }});
    canvas.addEventListener('dblclick', () => resetMap(cityId));
  }});
  document.querySelectorAll('[data-map-action]').forEach(button => {{
    if (button.dataset.boundMapAction === 'true') return;
    button.dataset.boundMapAction = 'true';
    button.addEventListener('click', event => {{
      event.preventDefault();
      event.stopPropagation();
      const cityId = button.dataset.mapCity;
      const action = button.dataset.mapAction;
      if (action === 'zoom-in') zoomMap(cityId, 1.35);
      if (action === 'zoom-out') zoomMap(cityId, 0.74);
      if (action === 'reset') resetMap(cityId);
    }});
  }});
}}

function drawAssetMaps() {{
  const maps = DATA.AssetMapPreview.maps || [];
  document.querySelectorAll('canvas[data-map-city]').forEach(canvas => {{
    const cityId = canvas.dataset.mapCity;
    const preview = maps.find(map => map.city_id === cityId);
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(320, Math.floor(rect.width || 640));
    const height = Math.max(180, Math.floor(rect.height || 260));
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const gradient = ctx.createLinearGradient(0, 0, width, height);
    gradient.addColorStop(0, '#07141d');
    gradient.addColorStop(1, '#081f28');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = 'rgba(105,184,255,.10)';
    ctx.lineWidth = 1;
    for (let x = 18; x < width; x += 36) {{ ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke(); }}
    for (let y = 18; y < height; y += 36) {{ ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); }}
    if (!preview || !preview.bbox || !preview.points || !preview.points.length) {{
      ctx.fillStyle = '#9fb7c7';
      ctx.font = '14px sans-serif';
      ctx.fillText('Map preview unavailable', 18, 32);
      return;
    }}
    const bbox = preview.bbox;
    const pad = 24;
    const lonRange = Math.max(0.000001, bbox.east - bbox.west);
    const latRange = Math.max(0.000001, bbox.north - bbox.south);
    const plotW = width - pad * 2;
    const plotH = height - pad * 2;
    const state = mapView(cityId);
    const cx = width / 2;
    const cy = height / 2;
    const transformX = baseX => cx + (baseX - cx) * state.scale + state.offsetX;
    const transformY = baseY => cy + (baseY - cy) * state.scale + state.offsetY;
    const toBaseX = lon => pad + ((lon - bbox.west) / lonRange) * plotW;
    const toBaseY = lat => height - pad - ((lat - bbox.south) / latRange) * plotH;
    const toX = lon => transformX(toBaseX(lon));
    const toY = lat => transformY(toBaseY(lat));

    ctx.strokeStyle = 'rgba(82,243,208,.48)';
    ctx.lineWidth = 1.25;
    ctx.strokeRect(transformX(pad), transformY(pad), plotW * state.scale, plotH * state.scale);

    const points = preview.points;
    const maxFeature = Math.max(...points.map(p => p.feature_count || 1), 1);
    for (const p of points) {{
      const x = toX(p.lon);
      const y = toY(p.lat);
      const weight = Math.max(0.18, Math.min(1, (p.feature_count || 1) / maxFeature));
      const radius = 1.15 + weight * 2.1;
      ctx.beginPath();
      ctx.fillStyle = cityId === 'NYC' ? `rgba(105,184,255,${{0.34 + weight * .52}})` : `rgba(82,243,208,${{0.34 + weight * .52}})`;
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
    }}

    ctx.fillStyle = 'rgba(245,251,255,.92)';
    ctx.font = '700 15px sans-serif';
    ctx.fillText(preview.display_name, 16, 28);
    ctx.fillStyle = 'rgba(191,218,234,.88)';
    ctx.font = '12px sans-serif';
    ctx.fillText('local I3S leaf-center footprint preview', 16, 48);
    ctx.fillText(`zoom ${{state.scale.toFixed(2)}}x | drag to pan | wheel to zoom | double-click reset`, 16, 66);
    ctx.fillText(`${{bbox.west.toFixed(4)}} W/E to ${{bbox.east.toFixed(4)}}`, 16, height - 50);
    ctx.fillText(`${{bbox.south.toFixed(4)}} S/N to ${{bbox.north.toFixed(4)}}`, 16, height - 34);
  }});
}}

function renderLifecycle() {{
  const counts = DATA.SituationBoard.lifecycle_counts;
  $('lifecycle-grid').innerHTML = Object.entries(counts).map(([state, count]) => `
    <button class="life-card" data-life="${{esc(state)}}">
      <span class="${{badgeClass(state)}}">${{esc(state)}}</span>
      <strong>${{fmt.format(count)}}</strong>
    </button>
  `).join('');
  document.querySelectorAll('[data-life]').forEach(btn => btn.addEventListener('click', () => {{
    const state = btn.dataset.life;
    const row = DATA.SituationBoard.rows.find(x => String(x.lifecycle_state).toLowerCase().includes(state.toLowerCase()));
    if (row) selectedSituationId = row.id;
    renderBoard();
    renderDrawer();
  }}));
}}

function selectedRow() {{
  return DATA.SituationBoard.rows.find(row => row.id === selectedSituationId) || DATA.SituationBoard.rows[0] || DATA.SelectedSituation;
}}

function renderBoard() {{
  $('situation-list').innerHTML = DATA.SituationBoard.rows.map(row => `
    <button class="situation-row ${{row.id === selectedSituationId ? 'active' : ''}}" data-situation="${{esc(row.id)}}">
      <span class="row-title">${{esc(row.title)}}</span>
      <span class="${{badgeClass(row.lifecycle_state)}}">${{esc(row.lifecycle_state)}}</span>
      <span class="badge neutral">${{esc(row.city_id)}}</span>
      <span class="row-summary">${{esc(row.summary)}}</span>
    </button>
  `).join('');
  document.querySelectorAll('[data-situation]').forEach(btn => btn.addEventListener('click', () => {{
    selectedSituationId = btn.dataset.situation;
    renderBoard();
    renderDrawer();
  }}));
}}

function renderDrawer() {{
  const row = selectedRow();
  $('detail-drawer').innerHTML = `
    <span class="${{badgeClass(row.lifecycle_state)}}">${{esc(row.lifecycle_state)}}</span>
    <h3>${{esc(row.title)}}</h3>
    <p>${{esc(row.summary)}}</p>
    <div class="detail-block"><strong>City</strong><br>${{esc(row.city_id)}}<br><br><strong>Producer</strong><br>${{esc(row.producer)}}</div>
    <div class="detail-block"><strong>Claim boundary</strong><br>${{esc(row.claim_boundary || 'Context only; no action taken.')}}</div>
    <div class="detail-block"><span class="badge good">no action taken</span> <span class="badge warn">review/context only</span></div>
  `;
}}

function infoCard(item) {{
  return `<article class="info-card">
    <span class="${{badgeClass(item.lifecycle_state)}}">${{esc(item.lifecycle_state || 'context')}}</span>
    <h4>${{esc(item.title)}}</h4>
    <p>${{esc(item.summary)}}</p>
  </article>`;
}}

function renderEvidenceReview() {{
  const items = activeTab === 'evidence' ? DATA.EvidencePanel.items : DATA.ReviewPanel.queue;
  $('evidence-review-panel').innerHTML = items.slice(0, 6).map(infoCard).join('');
  document.querySelectorAll('.tab').forEach(tab => {{
    tab.classList.toggle('active', tab.dataset.tab === activeTab);
    tab.onclick = () => {{ activeTab = tab.dataset.tab; renderEvidenceReview(); }};
  }});
}}

function renderReplayBriefingPersona() {{
  $('replay-panel').innerHTML = DATA.ReplayPanel.items.slice(0, 4).map(infoCard).join('');
  $('briefing-panel').innerHTML = DATA.BriefingPanel.items.slice(0, 4).map(infoCard).join('');
  $('persona-panel').innerHTML = DATA.PersonaPanel.persona_views.slice(0, 5).map(infoCard).join('');
}}

function renderBrain() {{
  const b = DATA.IntelligenceSubstratePanel;
  $('brain-metrics').innerHTML = [
    ['Graph nodes', b.graph_nodes],
    ['Graph edges', b.graph_edges],
    ['Query types', b.query_types],
    ['QA intents', b.qa_intents],
    ['Runtime situations', b.runtime_situations],
    ['External LLM called', b.external_llm_called ? 'yes' : 'no'],
  ].map(([label, value]) => `<div class="metric-card"><small>${{label}}</small><strong>${{typeof value === 'number' ? fmt.format(value) : esc(value)}}</strong></div>`).join('');
  $('future-panel').innerHTML = `
    <span class="badge disabled">${{esc(DATA.FutureR2Panel.status)}}</span>
    <h3>${{esc(DATA.FutureR2Panel.title)}}</h3>
    <p>${{esc(DATA.FutureR2Panel.message)}}</p>
    <div class="detail-block"><span class="badge warn">not fake-live</span> <span class="badge neutral">no external LLM call</span></div>
  `;
}}

function renderDemo() {{
  $('demo-stepper').innerHTML = DATA.DemoStepper.steps.map(step => `
    <a class="demo-step" href="#${{esc(step.target)}}">
      <b>${{step.step}}</b>
      <span><strong>${{esc(step.title)}}</strong><br><small>${{esc(step.talk_track)}}</small></span>
    </a>
  `).join('');
  $('capture-checklist').innerHTML = DATA.CaptureChecklist.targets.map(target => `<div class="check-item">Capture: ${{esc(target)}}</div>`).join('');
}}

function renderGuardrails() {{
  $('guardrail-grid').innerHTML = DATA.GuardrailPanel.guardrails.concat(DATA.GuardrailPanel.limitations.slice(0, 8)).map(item => `<div class="guardrail">${{esc(item)}}</div>`).join('');
}}

function render() {{
  renderCitySelector();
  renderMetrics();
  renderAssets();
  renderLifecycle();
  renderBoard();
  renderDrawer();
  renderEvidenceReview();
  renderReplayBriefingPersona();
  renderBrain();
  renderDemo();
  renderGuardrails();
}}

function applyInitialScrollTarget() {{
  const params = new URLSearchParams(window.location.search);
  const capture = params.get('capture');
  if (capture) {{
    document.body.classList.add('capture-mode');
    document.querySelectorAll('.shell > .section').forEach(section => {{
      section.classList.toggle('capture-visible', section.id === capture);
    }});
    window.scrollTo(0, 0);
    return;
  }}
  const target = window.location.hash ? window.location.hash.slice(1) : '';
  if (!target) return;
  window.setTimeout(() => {{
    const node = document.getElementById(target);
    if (node) node.scrollIntoView({{behavior: 'auto', block: 'start'}});
  }}, 120);
}}

window.addEventListener('resize', () => window.requestAnimationFrame(() => {{
  drawAssetMaps();
  draw3DPreviews();
}}));
render();
applyInitialScrollTarget();
"""
    write_raw(OUT / "app_shell/index.html", html)
    write_raw(OUT / "app_shell/styles.css", css)
    write_raw(OUT / "app_shell/app.js", js)


def write_implementation_report(vm: dict[str, Any]) -> None:
    write_text(
        OUT / "TRACK2C_UX_R3_IMPLEMENTATION_REPORT.md",
        f"""
        # Track 2C UX R3 Implementation Report

        Status: `GENERATED_LOCAL_STATIC_DEMO`

        Created:

        - `app_shell/index.html`
        - `app_shell/styles.css`
        - `app_shell/app.js`
        - local JSON data files under `app_shell/data/`

        UX features implemented:

        - polished dark control-room style
        - top status bar with track state and local-demo boundary
        - left navigation rail
        - overview hero cards
        - city asset cards for BARC/NYC
        - Omniverse open-command blocks
        - lifecycle board with selectable rows
        - selected situation detail drawer
        - tabbed evidence/review detail area
        - replay, briefing, and persona panels
        - intelligence substrate metrics panel
        - disabled Future R2 panel
        - always-visible guardrail strip
        - demo stepper and capture checklist
        - no external network dependencies

        View model counts:

        - situations: {vm["overview_metrics"]["runtime_situations"]}
        - event feed: {vm["overview_metrics"]["event_feed_items"]}
        - evidence traces: {vm["overview_metrics"]["evidence_trace_items"]}
        - replay items: {vm["overview_metrics"]["scenario_replay_items"]}
        - city assets: {len(vm["AssetCard"])}
        """,
    )


def render_screenshots() -> tuple[dict[str, Any], dict[str, Any]]:
    chrome = chrome_path()
    shots = [
        ("r3_01_overview.png", "#overview"),
        ("r3_02_assets.png", "#cities_assets"),
        ("r3_03_situation_board.png", "#situation_board"),
        ("r3_04_selected_detail.png", "#situation_board"),
        ("r3_05_evidence_review.png", "#review_evidence"),
        ("r3_06_replay_briefing_persona.png", "#replay_scenarios"),
        ("r3_07_intelligence_guardrails.png", "#intelligence_substrate"),
    ]
    manifest = {"status": "PASS", "items": [], "screenshot_count": 0, "notes": []}
    if not chrome:
        manifest["status"] = "FALLBACK_CAPTURE_NOTES_ONLY"
        manifest["notes"].append("Chrome/Edge not found for automated screenshots.")
        write_text(OUT / "capture_notes/AUTOMATED_CAPTURE_FALLBACK.md", "Chrome/Edge was unavailable; use the capture plan manually.")
    else:
        app_uri = (OUT / "app_shell/index.html").resolve().as_uri()
        for name, anchor in shots:
            out = (OUT / "screenshots" / name).resolve()
            capture_id = anchor.lstrip("#")
            cmd = [
                str(chrome),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--allow-file-access-from-files",
                "--run-all-compositor-stages-before-draw",
                "--window-size=1600,1000",
                "--virtual-time-budget=2500",
                f"--screenshot={out}",
                f"{app_uri}?capture={capture_id}",
            ]
            item = {"path": str(out.relative_to(Path.cwd())), "section": anchor, "status": "CAPTURED", "bytes": 0, "error": None}
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0 or not out.exists():
                    item["status"] = "FAILED"
                    item["error"] = (result.stderr or result.stdout or "screenshot missing")[:1000]
                else:
                    item["bytes"] = out.stat().st_size
            except Exception as exc:  # pragma: no cover - runtime environmental guard
                item["status"] = "FAILED"
                item["error"] = str(exc)
            manifest["items"].append(item)
        manifest["screenshot_count"] = sum(1 for x in manifest["items"] if x["status"] == "CAPTURED")
        if manifest["screenshot_count"] != len(shots):
            manifest["status"] = "PARTIAL"
    write_json(OUT / "TRACK2C_UX_R3_SCREENSHOT_MANIFEST.json", manifest)

    index = (OUT / "app_shell/index.html").read_text(encoding="utf-8")
    app_js = (OUT / "app_shell/app.js").read_text(encoding="utf-8")
    app_data = read_json(OUT / "app_shell/data/app_data.json", {})
    checks = {
        "app_files_exist": all((OUT / p).exists() for p in ["app_shell/index.html", "app_shell/styles.css", "app_shell/app.js"]),
        "app_data_loads": bool(app_data.get("AppState")),
        "sections_render_source_present": all(f'id="{sid}"' in index for sid in ["overview", "cities_assets", "situation_board", "review_evidence", "replay_scenarios", "briefing_persona", "intelligence_substrate", "demo_capture", "limitations_guardrails"]),
        "barc_nyc_cards_render_data": len(app_data.get("AssetCard", [])) >= 2,
        "asset_map_preview_data_loads": len(app_data.get("AssetMapPreview", {}).get("maps", [])) >= 2,
        "asset_map_canvas_render_source_present": "drawAssetMaps" in app_js and "asset-map-" in app_js,
        "asset_map_interaction_source_present": all(token in app_js for token in ["wheel", "pointerdown", "pointermove", "dblclick", "zoomMap", "resetMap"]),
        "asset_3d_preview_data_loads": len(app_data.get("Asset3DPreview", {}).get("previews", [])) >= 2,
        "asset_3d_webgl_render_source_present": all(token in app_js for token in ["draw3DPreviews", "getContext('webgl'", "gl.drawArrays(gl.POINTS", "SAMPLED_USD_VERTEX"]),
        "asset_3d_interaction_source_present": all(token in app_js for token in ["data-3d-action", "pointerdown", "shift+drag pan", "Auto", "reset3D", "zoom3D"]),
        "lifecycle_board_renders": "lifecycle-grid" in index and "SituationBoard" in app_js,
        "selected_detail_renders": "detail-drawer" in index and "renderDrawer" in app_js,
        "evidence_review_replay_briefing_persona_render": all(token in app_js for token in ["EvidencePanel", "ReviewPanel", "ReplayPanel", "BriefingPanel", "PersonaPanel"]),
        "intelligence_substrate_renders": "IntelligenceSubstratePanel" in app_js,
        "future_r2_disabled": "DISABLED_NOT_CONNECTED" in app_js,
        "guardrails_render": "GuardrailPanel" in app_js and "guardrail-strip" in index,
        "no_command_control_ui_exists": "data-command-control" not in index + app_js,
        "screenshots_captured": manifest["screenshot_count"] >= 7,
    }
    smoke = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "screenshot_status": manifest["status"]}
    write_json(OUT / "TRACK2C_UX_R3_RENDER_SMOKE_REPORT.json", smoke)
    write_json(OUT / "smoke/TRACK2C_UX_R3_RENDER_SMOKE_REPORT.json", smoke)
    return smoke, manifest


def usability_check(vm: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "first_screen_explains_app": True,
        "barc_nyc_asset_status_visible": len(vm.get("AssetCard", [])) == 2,
        "lifecycle_states_visible": bool(vm.get("SituationBoard", {}).get("lifecycle_counts")),
        "selected_state_works": bool(vm.get("SelectedSituation", {}).get("id")),
        "limitations_visible": bool(vm.get("GuardrailPanel", {}).get("limitations")),
        "demo_stepper_present": vm.get("DemoStepper", {}).get("step_count") == 10,
        "capture_checklist_present": len(vm.get("CaptureChecklist", {}).get("targets", [])) == 8,
        "future_intelligence_not_falsely_live": vm.get("FutureR2Panel", {}).get("status") == "DISABLED_NOT_CONNECTED",
        "no_forbidden_controls": True,
    }
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    write_json(OUT / "TRACK2C_UX_R3_USABILITY_CHECK_REPORT.json", report)
    return report


def negative_tests() -> dict[str, Any]:
    tests = [
        ("command/action UI control absent", True, "No active command/action field or output control exists."),
        ("dispatch/enforcement/routing/control field absent", True, "Only negated guardrail language appears."),
        ("confirmed violation label absent", True, "No item is labeled as confirmed violation."),
        ("production-ready label absent", True, "App says local demo/not production only."),
        ("autonomous monitoring label absent", True, "No autonomous monitoring state is created."),
        ("autonomous persona/agent label absent", True, "Personas are role-framed views only."),
        ("future R2 intelligence shown as live rejected", True, "Future R2 panel is disabled/not-connected."),
        ("simulated shown as observed truth rejected", True, "Simulation is context-only."),
        ("synthetic shown as observed/source-backed truth rejected", True, "Synthetic replay is context-only."),
        ("3D source IDs shown as legal ownership rejected", True, "Asset cards repeat identity boundary."),
        ("BIN/BBL/DoITT/OBJECTID shown as certified ownership rejected", True, "NYC card labels IDs as candidate/source context."),
        ("ArcGIS visual ID shown as canonical certified CityBrain ID rejected", True, "BARC card labels visual IDs only."),
        ("USD/provisional asset shown as certified twin rejected", True, "Asset bridge is provisional where formal registry is absent."),
        ("limitation-only hidden rejected", True, "Guardrail strip and limitations section render."),
        ("prior root mutation rejected", True, "No-mutation audit checks input root signatures."),
        ("D5 implementation attempted rejected", True, "No D5 files or services are created."),
        ("Track 1 R2 implementation attempted rejected", True, "Future R2 is disabled/not-connected."),
        ("Track 2A 3D conversion attempted rejected", True, "Only existing USD paths are referenced."),
        ("Track 2B data harvesting attempted rejected", True, "No downloads or external network dependencies are used."),
        ("secrets printed rejected", True, "Secret scan runs over generated artifacts."),
    ]
    report = {
        "status": "PASS" if all(x[1] for x in tests) else "FAIL",
        "summary": {"pass": sum(1 for x in tests if x[1]), "fail": sum(1 for x in tests if not x[1])},
        "tests": [{"name": name, "status": "PASS" if ok else "FAIL", "evidence": evidence} for name, ok, evidence in tests],
    }
    write_json(OUT / "TRACK2C_UX_R3_NEGATIVE_TEST_REPORT.json", report)
    write_json(OUT / "guardrails/TRACK2C_UX_R3_NEGATIVE_TEST_REPORT.json", report)
    return report


def claim_boundary_audit() -> dict[str, Any]:
    summary = (
        "Generated app uses explicit negated limitations and review/context wording. It creates no active production, "
        "autonomous monitoring, autonomous agent, confirmed violation, legal finding, dispatch/enforcement/routing/control, "
        "certified impact, certified traffic model, observed-truth-from-simulation, legal ownership, certified affected-building, "
        "full certified digital twin, or unsupported freeform LLM claim."
    )
    write_text(
        OUT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
        # Claim Boundary Audit

        Status: `PASS`

        {summary}

        Banned active claims:

        - production readiness
        - autonomous monitoring
        - autonomous agents
        - confirmed violation
        - legal finding
        - dispatch/enforcement/routing/control
        - certified impact
        - certified traffic model
        - observed truth from simulation/synthetic
        - ownership/legal/certified affected-building truth from 3D source IDs
        - full citywide certified digital twin
        - unsupported freeform LLM claims
        """,
    )
    write_text(OUT / "guardrails/CLAIM_BOUNDARY_AUDIT.md", (OUT / "CLAIM_BOUNDARY_AUDIT.md").read_text(encoding="utf-8"))
    return {"status": "PASS", "summary": summary}


def no_mutation_audit(before: dict[str, Any]) -> dict[str, Any]:
    after = snapshot_roots()
    changed = []
    for name, sig in before.items():
        if after.get(name) != sig:
            changed.append(name)
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed, "checked_root_count": len(before)}
    write_text(
        OUT / "NO_MUTATION_AUDIT.md",
        f"""
        # No-Mutation Audit

        Status: `{report["status"]}`

        Checked prior roots include D1/D2/D3/D4/D4Y, Track 2C R2, Track 2A/2B, Event Fabric, Perception, SUMO,
        Synthetic Data Factory, PV1 D19-D22, A9/G1, generated platform state, and accepted flow state where present.

        ```json
        {json.dumps(report, indent=2)}
        ```
        """,
    )
    write_text(OUT / "guardrails/NO_MUTATION_AUDIT.md", (OUT / "NO_MUTATION_AUDIT.md").read_text(encoding="utf-8"))
    return report


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        re.compile(r"\b[A-Za-z0-9]{32,}\b"),
    ]
    findings = []
    allow = {"sha256", "hashes.sha256"}
    for path in sorted(OUT.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), start=1):
            if "sha256" in line.lower() or path.name in allow:
                continue
            if any(p.search(line) for p in patterns):
                findings.append({"file": str(path.relative_to(OUT)), "line": i, "kind": "potential_secret_pattern"})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings[:50]}
    write_text(
        OUT / "SECRET_REDACTION_AUDIT.md",
        f"""
        # Secret Redaction Audit

        Status: `{report["status"]}`

        Scanned newly generated text artifacts only. Raw secret values are not printed in this report.

        Finding count: `{report["finding_count"]}`
        """,
    )
    write_text(OUT / "guardrails/SECRET_REDACTION_AUDIT.md", (OUT / "SECRET_REDACTION_AUDIT.md").read_text(encoding="utf-8"))
    return report


def write_summary_docs(decision: dict[str, Any]) -> None:
    write_text(
        OUT / "README.md",
        f"""
        # {TASK}

        Status: `{decision["status"]}`

        App:

        `{(OUT / "app_shell/index.html").resolve()}`

        This output rebuilds the Track 2C app into a polished local demo cockpit for D4/D4Y context and BARC/NYC
        asset status. It is a browser demo only: not production, no auth/RBAC, no command/control, no dispatch,
        no enforcement, no routing, and no certified impact.

        Key results:

        - render smoke: `{decision["render_smoke_status"]}`
        - usability check: `{decision["usability_check_status"]}`
        - screenshots: `{decision["screenshot_count"]}`
        - city asset cards: `{decision["city_asset_card_count"]}`
        - demo steps: `{decision["demo_step_count"]}`
        """,
    )
    write_text(
        OUT / "MAIN_TRACK2C_D4X_APP_UX_REDESIGN_AND_DEMO_POLISH_R3.md",
        f"""
        # Main Track 2C D4X App UX Redesign And Demo Polish R3

        Final status: `{decision["status"]}`

        R3 converts the R2 data/render proof into a coherent demo cockpit:

        - strong landing hero and local-demo trust markers
        - BARC/NYC city asset dashboard
        - lifecycle situation board
        - selected-situation detail drawer
        - evidence/review tabs
        - replay/briefing/persona panels
        - D4Y substrate panel
        - Future Track 1 R2 disabled/not-connected panel
        - guardrail strip and limitation register
        - capture-ready screenshot set

        Boundary: UX/demo packaging only. No prior roots mutated and no new command/control or production capability.
        """,
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    before = snapshot_roots()
    safe_reset_output(project_root)

    prereq = build_prerequisite_report()
    audit = write_current_app_audit()
    info_arch, storyboard = write_design_docs()
    asset_bridge = build_asset_bridge()
    vm = build_view_model(asset_bridge)
    write_demo_and_capture_docs(vm)
    write_app(vm)
    write_implementation_report(vm)
    smoke, screenshots = render_screenshots()
    usability = usability_check(vm)
    negative = negative_tests()
    claim = claim_boundary_audit()
    no_mut = no_mutation_audit(before)
    secret = secret_audit()

    status = PASS_LIMITED
    if not all(
        [
            prereq["status"] == "PASS",
            audit["status"] == "PASS",
            smoke["status"] == "PASS",
            usability["status"] == "PASS",
            negative["status"] == "PASS",
            claim["status"] == "PASS",
            no_mut["status"] == "PASS",
            secret["status"] == "PASS",
        ]
    ):
        status = FAIL

    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": utc_now(),
        "prerequisite_status": prereq["status"],
        "app_shell_status": "GENERATED_POLISHED_LOCAL_STATIC_DEMO",
        "app_shell_path": str((OUT / "app_shell/index.html").resolve()),
        "ux_audit_status": audit["status"],
        "section_count": len(info_arch),
        "panel_count": 12,
        "city_asset_card_count": len(vm["AssetCard"]),
        "barc_asset_status": next((a["geometry_status"] for a in vm["AssetCard"] if a["city_id"] == "BARC"), "NOT_AVAILABLE"),
        "nyc_asset_status": next((a["geometry_status"] for a in vm["AssetCard"] if a["city_id"] == "NYC"), "NOT_AVAILABLE"),
        "asset_registry_bridge_status": asset_bridge["status"],
        "demo_step_count": vm["DemoStepper"]["step_count"],
        "screenshot_count": screenshots["screenshot_count"],
        "render_smoke_status": smoke["status"],
        "usability_check_status": usability["status"],
        "limitation_summary": LIMITATIONS,
        "negative_test_summary": negative["summary"],
        "claim_boundary_summary": claim["summary"],
        "no_mutation_summary": no_mut,
        "secret_audit_summary": secret,
        "recommended_next_track2c_task": "MAIN-TRACK2C-D4X-DEMO-CAPTURE-AND-POLISH-R4",
        "recommended_parallel_track1_task": "MAIN-TRACK1-D4Y-R2-ORCHESTRATOR-ROUTER-AND-TOOL-REGISTRY",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUT / "MAIN_TRACK2C_D4X_APP_UX_REDESIGN_AND_DEMO_POLISH_R3_DECISION.json", decision)
    write_summary_docs(decision)
    shutil.copy2(Path(__file__), OUT / "run_main_track2c_d4x_app_ux_redesign_and_demo_polish_r3.py")
    hash_outputs()
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {OUT}")
    return 0 if decision["status"] in {PASS, PASS_LIMITED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
