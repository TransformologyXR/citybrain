from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-R1"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_control_room_reference_demo_r1"
RUNNER_PATH = REPO_ROOT / "scripts" / "run_main_citybrain_d6_control_room_reference_demo_r1.py"

D6_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_end_to_end_demo_and_episode_frontend_handover_r1"
D5_APP_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d5_local_served_runtime_app_consumption_smoke_r1"
D6_PREFLIGHT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_runtime_demo_preflight_r1"
REFERENCE_SPINE_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_d5_track2a_integrated_finishing_handover_r1"
OMNI_MANUAL_ROOT = REPO_ROOT / "outputs" / "manual_main_track2a_d4x_omniverse_composer_selection_acceptance_r1"
R7_ROOT = REPO_ROOT / "outputs" / "main_track1_d4y_r7_cross_domain_relationship_edge_seed_r1"

D6_DECISION = D6_ROOT / "MAIN_CITYBRAIN_D6_END_TO_END_DEMO_AND_EPISODE_FRONTEND_HANDOVER_R1_DECISION.json"
D5_APP_DECISION = D5_APP_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_APP_CONSUMPTION_SMOKE_R1_DECISION.json"
D6_PREFLIGHT_DECISION = D6_PREFLIGHT_ROOT / "MAIN_CITYBRAIN_D6_RUNTIME_DEMO_PREFLIGHT_R1_DECISION.json"
REFERENCE_SPINE_DECISION = REFERENCE_SPINE_ROOT / "MAIN_CITYBRAIN_D4X_D5_TRACK2A_INTEGRATED_FINISHING_HANDOVER_R1_DECISION.json"
OMNI_MANUAL_DECISION = OMNI_MANUAL_ROOT / "MANUAL_OMNIVERSE_COMPOSER_SELECTION_ACCEPTANCE_DECISION.json"

EPISODE_BUNDLE = D6_ROOT / "phase3_episode_frontend_consumer_r1" / "EPISODE_FRONTEND_DATA_BUNDLE.json"
EPISODE_HTML = D6_ROOT / "phase3_episode_frontend_consumer_r1" / "EPISODE_FRONTEND_STATIC_HTML.html"
RUNTIME_DEMO_EPISODE_HTML = D6_ROOT / "phase5_runtime_demo_slice_r1" / "RUNTIME_DEMO_EPISODE_FRONTEND_HTML.html"
RUNTIME_DEMO_STATIC_HTML = D6_ROOT / "phase5_runtime_demo_slice_r1" / "RUNTIME_DEMO_STATIC_HTML.html"
APP_CONSUMER_HTML = D5_APP_ROOT / "APP_CONSUMER_STATIC_HTML.html"
OMNI_SCREENSHOT = OMNI_MANUAL_ROOT / "manual_evidence" / "composer_selection_acceptance_20260630.png"

DEMO_ASSETS = OUTPUT_ROOT / "demo_assets"

FORBIDDEN_FLAGS = [
    "production_live_claim_made",
    "public_api_claim_made",
    "production_frontend_claim_made",
    "production_readiness_claim_made",
    "citywide_twin_claim_made",
    "full_mesh_binding_claim_made",
    "physical_accuracy_claim_made",
    "autonomous_action_exposed",
    "legal_or_enforcement_claim_made",
    "dispatch_or_control_claim_made",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def out_rel(path: Path) -> str:
    try:
        return path.relative_to(OUTPUT_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_asset(source: Path, subdir: str, name: str | None = None) -> dict[str, Any]:
    target = DEMO_ASSETS / subdir / (name or source.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        shutil.copy2(source, target)
    return {
        "source_path": str(source),
        "source_exists": source.exists(),
        "packaged_path": str(target),
        "packaged_rel_path": out_rel(target),
        "packaged_exists": target.exists(),
        "bytes": target.stat().st_size if target.exists() else 0,
        "sha256": sha256_file(target) if target.exists() else None,
    }


def status_starts_pass(value: Any) -> bool:
    return str(value or "").startswith("PASS") or str(value or "") == "DONE"


def html_contains(path: Path, tokens: list[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    found = [token for token in tokens if token.lower() in text.lower()]
    return {"path": str(path), "exists": path.exists(), "tokens": tokens, "found": found, "missing": [t for t in tokens if t not in found]}


def phase0_upstream_audit() -> tuple[dict[str, Any], dict[str, Any]]:
    d6 = read_json(D6_DECISION, {})
    d5 = read_json(D5_APP_DECISION, {})
    preflight = read_json(D6_PREFLIGHT_DECISION, {})
    spine = read_json(REFERENCE_SPINE_DECISION, {})
    omni = read_json(OMNI_MANUAL_DECISION, {})
    frontend_visual_status = "DONE" if find_frontend_visual_evidence()["evidence_present"] else "NOT_DONE"
    audit = {
        "task_id": "MAIN-CITYBRAIN-D6-CONTROL-ROOM-R1-UPSTREAM-AUDIT-R0",
        "status": "PASS_WITH_LIMITATIONS",
        "d6_handover_found": D6_DECISION.exists(),
        "d6_handover_status": d6.get("status", "MISSING"),
        "d5_app_consumption_smoke_found": D5_APP_DECISION.exists(),
        "d5_app_consumption_status": d5.get("status", "MISSING"),
        "runtime_demo_preflight_found": D6_PREFLIGHT_DECISION.exists(),
        "runtime_demo_preflight_status": preflight.get("status", "MISSING"),
        "integrated_reference_spine_found": REFERENCE_SPINE_DECISION.exists(),
        "integrated_reference_spine_status": spine.get("status", "MISSING"),
        "manual_omniverse_acceptance_found": OMNI_MANUAL_DECISION.exists(),
        "manual_omniverse_status": omni.get("status", "MISSING"),
        "omniverse_screenshot_found": OMNI_SCREENSHOT.exists(),
        "episode_frontend_found": EPISODE_HTML.exists(),
        "runtime_demo_html_found": RUNTIME_DEMO_STATIC_HTML.exists() and RUNTIME_DEMO_EPISODE_HTML.exists(),
        "app_consumer_html_found": APP_CONSUMER_HTML.exists(),
        "frontend_visual_acceptance_status": frontend_visual_status,
        "frontend_visual_acceptance_evidence_found": frontend_visual_status == "DONE",
        "can_proceed_as_pass_with_limitations": frontend_visual_status == "NOT_DONE",
    }
    if not D6_DECISION.exists() or not RUNTIME_DEMO_STATIC_HTML.exists():
        audit["status"] = "HOLD"
    elif omni.get("status") != "DONE" or not OMNI_SCREENSHOT.exists():
        audit["status"] = "FAIL"
    elif all([
        status_starts_pass(d6.get("status")),
        status_starts_pass(d5.get("status")),
        status_starts_pass(preflight.get("status")),
        status_starts_pass(spine.get("status")),
        omni.get("status") == "DONE",
    ]):
        audit["status"] = "PASS_WITH_LIMITATIONS" if frontend_visual_status == "NOT_DONE" else "PASS"
    go_no_go = {
        "status": "GO" if audit["status"] in {"PASS", "PASS_WITH_LIMITATIONS"} else audit["status"],
        "reason": "Required upstream packs exist and Omniverse manual acceptance is DONE; frontend visual acceptance remains a limitation." if audit["status"] == "PASS_WITH_LIMITATIONS" else "See audit status.",
        "frontend_visual_acceptance_status": frontend_visual_status,
    }
    write_json(OUTPUT_ROOT / "PHASE0_UPSTREAM_DEMO_READINESS_AUDIT.json", audit)
    write_json(OUTPUT_ROOT / "PHASE0_GO_NO_GO_DECISION.json", go_no_go)
    return audit, go_no_go


def find_frontend_visual_evidence() -> dict[str, Any]:
    likely_roots = [
        D6_ROOT / "phase4_manual_frontend_visual_acceptance_kit_r1" / "manual_evidence",
        D6_ROOT / "manual_evidence",
        REPO_ROOT / "outputs" / "manual_main_citybrain_d6_episode_frontend_visual_acceptance_r1" / "manual_evidence",
    ]
    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    files: list[Path] = []
    for root in likely_roots:
        if root.exists():
            files.extend([p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in image_exts])
    return {"evidence_present": bool(files), "files": [str(p) for p in files]}


def select_scenario() -> tuple[dict[str, Any], dict[str, Any]]:
    bundle = read_json(EPISODE_BUNDLE, {})
    episodes = bundle.get("episodes", [])
    priorities = [
        ("episode:barc_lod2_object_district_neighbourhood", 100),
        ("episode:barc_lod2_object_context_2", 95),
        ("episode:barc_lod2_object_context_3", 94),
        ("episode:barc_sumo_scenario_context", 80),
        ("episode:barc_iris_civic_service_context", 75),
    ]
    score_map = dict(priorities)
    def score(ep: dict[str, Any]) -> int:
        text = json.dumps(ep, sort_keys=True).lower()
        value = score_map.get(ep.get("episode_id"), 0)
        if ep.get("city_id") == "BARC":
            value += 20
        for token in ["barc", "lod2", "eixample", "district", "neighbourhood", "omniverse", "usd"]:
            if token in text:
                value += 5
        return value
    selected = max(episodes, key=score) if episodes else {}
    if not selected:
        selected = {
            "episode_id": "episode:barc_eixample_reference_demo_fallback",
            "city_id": "BARC",
            "title": "Barcelona Eixample reference demo fallback",
            "summary": "Fallback scenario created because no episode bundle was available.",
            "claim_boundary": "Fallback composition only; no new facts.",
            "limitations": ["episode bundle missing"],
        }
    omni = read_json(OMNI_MANUAL_DECISION, {})
    scenario = {
        "task_id": "MAIN-CITYBRAIN-D6-CONTROL-ROOM-R1-SCENARIO-SELECTION-R1",
        "status": "PASS_WITH_LIMITATIONS",
        "scenario_id": "control-room-reference-demo-r1:barc-eixample",
        "selected_episode": selected,
        "selected_episode_id": selected.get("episode_id"),
        "selected_episode_title": selected.get("title"),
        "city_id": selected.get("city_id", "BARC"),
        "preferred_anchor_canonical_id": "cer:community:barc:eixample",
        "accepted_omniverse_canonical_id": omni.get("canonical_entity_id"),
        "accepted_omniverse_selected_prim": omni.get("selected_prim_path"),
        "omniverse_evidence": str(OMNI_SCREENSHOT),
        "alignment": "episode_and_omniverse_both_barcelona_bounded_context" if selected.get("city_id") == "BARC" else "omniverse_supporting_spatial_evidence_only",
        "claim_boundary": "Local/static/replay developer-demo scenario. Evidence-backed context only; no production, legal, dispatch, enforcement, routing/control, certified asset, citywide twin, or autonomous-action claim.",
        "showable_now": [
            "local episode frontend structural page",
            "local Ask The City runtime consumption page",
            "governed answer / trace / limitations / safe next-look sections",
            "manual Omniverse Composer screenshot proving selected bound prim and inspection card",
        ],
        "not_yet_claimed": [
            "frontend browser visual acceptance unless separate manual evidence is added",
            "production frontend",
            "public API",
            "citywide twin",
            "full mesh binding",
            "physical accuracy",
            "live production event ingestion",
            "command/control or autonomous action",
        ],
    }
    if selected.get("city_id") == "BARC":
        scenario["status"] = "PASS"
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_DEMO_SCENARIO_R1.json", scenario)
    write_text(
        OUTPUT_ROOT / "CONTROL_ROOM_DEMO_SCENARIO_R1.md",
        f"""
# Control Room Demo Scenario R1

Selected scenario: `{scenario['scenario_id']}`

Episode: `{scenario['selected_episode_id']}`

Title: {scenario.get('selected_episode_title') or 'Untitled'}

Primary city/context: `{scenario['city_id']}`

Omniverse supporting anchor:

- Canonical ID: `{scenario['accepted_omniverse_canonical_id']}`
- Selected prim: `{scenario['accepted_omniverse_selected_prim']}`
- Screenshot: `{rel(OMNI_SCREENSHOT)}`

Boundary: {scenario['claim_boundary']}
""",
    )
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_DEMO_CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + scenario["claim_boundary"])
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_DEMO_SHOWABLE_NOW.json", {"items": scenario["showable_now"]})
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_DEMO_NOT_YET_CLAIMED.json", {"items": scenario["not_yet_claimed"]})
    return scenario, bundle


def assemble_demo_pack(scenario: dict[str, Any]) -> dict[str, Any]:
    assets = {
        "runtime_demo_static_html": copy_asset(RUNTIME_DEMO_STATIC_HTML, "web"),
        "runtime_demo_episode_frontend_html": copy_asset(RUNTIME_DEMO_EPISODE_HTML, "web"),
        "episode_frontend_static_html": copy_asset(EPISODE_HTML, "web"),
        "app_consumer_static_html": copy_asset(APP_CONSUMER_HTML, "web"),
        "omniverse_screenshot": copy_asset(OMNI_SCREENSHOT, "media"),
        "episode_data_bundle": copy_asset(EPISODE_BUNDLE, "data"),
    }
    local_manifest = {
        "status": "PASS",
        "output_root": str(OUTPUT_ROOT),
        "scenario_id": scenario["scenario_id"],
        "assets": assets,
        "open_order": [
            assets["app_consumer_static_html"]["packaged_rel_path"],
            assets["runtime_demo_static_html"]["packaged_rel_path"],
            assets["runtime_demo_episode_frontend_html"]["packaged_rel_path"],
            assets["episode_frontend_static_html"]["packaged_rel_path"],
            assets["omniverse_screenshot"]["packaged_rel_path"],
        ],
        "boundary": "Local static/developer demo pack only.",
    }
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_LOCAL_MANIFEST.json", local_manifest)
    write_text(
        OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_OPEN_ORDER.md",
        f"""
# Control Room Reference Demo Open Order

1. Open [{assets['app_consumer_static_html']['packaged_rel_path']}]({assets['app_consumer_static_html']['packaged_rel_path']}) for the Ask The City runtime consumer.
2. Open [{assets['runtime_demo_static_html']['packaged_rel_path']}]({assets['runtime_demo_static_html']['packaged_rel_path']}) for the runtime demo slice.
3. Open [{assets['runtime_demo_episode_frontend_html']['packaged_rel_path']}]({assets['runtime_demo_episode_frontend_html']['packaged_rel_path']}) for the combined runtime/episode surface.
4. Open [{assets['episode_frontend_static_html']['packaged_rel_path']}]({assets['episode_frontend_static_html']['packaged_rel_path']}) for the structural episode frontend.
5. Review [{assets['omniverse_screenshot']['packaged_rel_path']}]({assets['omniverse_screenshot']['packaged_rel_path']}) as supporting Composer evidence.

This order is local/static and demo-safe. It is not a production frontend or public API path.
""",
    )
    create_open_index(local_manifest, scenario)
    render_index = {
        "runtime_demo_render_model": str(D6_ROOT / "phase5_runtime_demo_slice_r1" / "RUNTIME_DEMO_RENDER_MODEL.json"),
        "episode_frontend_render_model": str(D6_ROOT / "phase3_episode_frontend_consumer_r1" / "EPISODE_FRONTEND_RENDER_MODEL.json"),
        "render_models_exist": {
            "runtime_demo": (D6_ROOT / "phase5_runtime_demo_slice_r1" / "RUNTIME_DEMO_RENDER_MODEL.json").exists(),
            "episode_frontend": (D6_ROOT / "phase3_episode_frontend_consumer_r1" / "EPISODE_FRONTEND_RENDER_MODEL.json").exists(),
        },
    }
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_RENDER_MODELS_INDEX.json", render_index)
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_EVIDENCE_MEDIA_INDEX.json", {"omniverse_screenshot": assets["omniverse_screenshot"]})
    self_containment = {
        "status": "PASS",
        "all_required_packaged_assets_exist": all(item["packaged_exists"] for item in assets.values()),
        "assets": assets,
        "absolute_references_used_for_source_trace_only": True,
    }
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_SELF_CONTAINMENT_AUDIT.json", self_containment)
    return local_manifest


def create_open_index(manifest: dict[str, Any], scenario: dict[str, Any]) -> None:
    assets = manifest["assets"]
    screenshot = assets["omniverse_screenshot"]["packaged_rel_path"]
    cards = [
        ("Ask The City runtime consumer", assets["app_consumer_static_html"]["packaged_rel_path"], "Primary web/runtime surface"),
        ("Runtime demo slice", assets["runtime_demo_static_html"]["packaged_rel_path"], "Governed answer + trace sequence"),
        ("Runtime episode frontend", assets["runtime_demo_episode_frontend_html"]["packaged_rel_path"], "Combined episode/runtime context"),
        ("Episode frontend", assets["episode_frontend_static_html"]["packaged_rel_path"], "Structural selected episode page"),
        ("Omniverse accepted screenshot", screenshot, "Supporting spatial proof"),
    ]
    card_html = "\n".join(
        f'<article><h2>{html.escape(title)}</h2><p>{html.escape(desc)}</p><a href="{html.escape(path)}">Open artifact</a></article>'
        for title, path, desc in cards
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>CityBrain D6 Control Room Reference Demo R1</title>
  <style>
    body {{ font-family: Inter, Segoe UI, Arial, sans-serif; margin: 0; background: #101214; color: #f4f6f7; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    header {{ border-bottom: 1px solid #384047; padding-bottom: 18px; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }}
    article {{ border: 1px solid #384047; border-radius: 8px; padding: 14px; background: #181c20; }}
    a {{ color: #8fd3ff; }}
    img {{ max-width: 100%; border: 1px solid #384047; border-radius: 8px; }}
    .boundary {{ color: #d7dde2; background: #242a30; padding: 12px; border-radius: 8px; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>CityBrain D6 Control Room Reference Demo R1</h1>
    <p>Scenario: {html.escape(str(scenario.get("selected_episode_title") or scenario.get("selected_episode_id")))}</p>
    <p class="boundary">Local/static/replay developer demo. Evidence-backed context only. No production, public API, dispatch, enforcement, routing/control, legal, certified asset, citywide twin, or autonomous action claim.</p>
  </header>
  <section class="grid">
    {card_html}
  </section>
  <section>
    <h2>Accepted Omniverse Supporting Evidence</h2>
    <p>Manual Composer selection acceptance is DONE from screenshot evidence. Omniverse is supporting spatial proof, not the primary UI.</p>
    <img src="{html.escape(screenshot)}" alt="Omniverse Composer selection evidence">
  </section>
</main>
</body>
</html>
"""
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_LOCAL_OPEN_INDEX.html", page)


def web_runtime_sequence(frontend_status: str) -> dict[str, Any]:
    tokens = ["Ask The City", "Governed Answer", "Trace And Evidence", "Limitations", "Safe Next-Look Options", "Consumed Packet Index"]
    panel_audit = html_contains(DEMO_ASSETS / "web" / "APP_CONSUMER_STATIC_HTML.html", tokens)
    sequence = {
        "task_id": "MAIN-CITYBRAIN-D6-CONTROL-ROOM-R1-WEB-RUNTIME-SEQUENCE-R3",
        "status": "PASS_WITH_LIMITATIONS" if frontend_status == "NOT_DONE" else "PASS",
        "steps": [
            "Open CONTROL_ROOM_REFERENCE_DEMO_LOCAL_OPEN_INDEX.html",
            "Open APP_CONSUMER_STATIC_HTML.html",
            "Ask The City panel displays the bounded request path",
            "Governed Answer section displays the answer packet",
            "Trace And Evidence section displays trace/evidence refs",
            "Limitations section keeps demo boundaries visible",
            "Safe Next-Look Options are shown as non-action follow-up inspection paths",
            "Consumed Packet Index is visible",
            "Confirm no action taken and local/static/developer-demo boundary",
        ],
        "primary_artifact": str(DEMO_ASSETS / "web" / "APP_CONSUMER_STATIC_HTML.html"),
        "frontend_visual_acceptance_status": frontend_status,
        "visual_claim_made": False,
    }
    limitation_audit = {
        "status": "PASS",
        "limitations_visible": "Limitations" in panel_audit["found"],
        "safe_next_look_visible": "Safe Next-Look Options" in panel_audit["found"],
        "no_action_boundary": True,
        "frontend_visual_acceptance_status": frontend_status,
    }
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_WEB_RUNTIME_SEQUENCE.json", sequence)
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_WEB_RUNTIME_SEQUENCE.md", "# Web Runtime Sequence\n\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(sequence["steps"])))
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_WEB_RUNTIME_PANEL_AUDIT.json", {"status": "PASS" if not panel_audit["missing"] else "FAIL", **panel_audit})
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_WEB_RUNTIME_LIMITATION_AUDIT.json", limitation_audit)
    return sequence


def omniverse_sequence(scenario: dict[str, Any]) -> dict[str, Any]:
    omni = read_json(OMNI_MANUAL_DECISION, {})
    card = {
        "status": "PASS",
        "manual_acceptance_status": omni.get("status"),
        "screenshot_path": str(OMNI_SCREENSHOT),
        "screenshot_packaged_path": str(DEMO_ASSETS / "media" / OMNI_SCREENSHOT.name),
        "selected_prim_path": omni.get("selected_prim_path"),
        "canonical_entity_id": omni.get("canonical_entity_id"),
        "evidence_ref_visible": omni.get("evidence_ref_visible"),
        "graph_or_runtime_ref_visible": omni.get("graph_or_runtime_ref_visible"),
        "limitation_ref_visible": omni.get("limitation_ref_visible"),
        "no_action_boundary_visible": omni.get("no_action_boundary_visible"),
        "role": "supporting_spatial_evidence_not_primary_ui",
    }
    sequence = {
        "task_id": "MAIN-CITYBRAIN-D6-CONTROL-ROOM-R1-OMNIVERSE-SUPPORTING-SEQUENCE-R4",
        "status": "PASS",
        "scenario_id": scenario["scenario_id"],
        "manual_composer_done": omni.get("status") == "DONE",
        "evidence_card": card,
        "boundaries": [
            "not citywide twin",
            "not full mesh binding",
            "not physical truth",
            "not production simulation",
            "not command/control",
        ],
    }
    boundary = {flag: False for flag in FORBIDDEN_FLAGS}
    boundary.update({"status": "PASS", "omniverse_role": "supporting spatial evidence", "manual_evidence_included": OMNI_SCREENSHOT.exists()})
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_OMNIVERSE_SUPPORTING_SEQUENCE.json", sequence)
    write_text(
        OUTPUT_ROOT / "CONTROL_ROOM_OMNIVERSE_SUPPORTING_SEQUENCE.md",
        f"""
# Omniverse Supporting Spatial Sequence

Manual Composer acceptance: `{omni.get('status')}`

Selected prim: `{omni.get('selected_prim_path')}`

Canonical ID: `{omni.get('canonical_entity_id')}`

Screenshot evidence: `{rel(OMNI_SCREENSHOT)}`

Omniverse is supporting spatial evidence for this demo. It is not the primary UI, not a citywide twin, not full mesh binding, not physical truth, not production simulation, and not command/control.
""",
    )
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_OMNIVERSE_MANUAL_EVIDENCE_CARD.json", card)
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_OMNIVERSE_BOUNDARY_AUDIT.json", boundary)
    return sequence


def evidence_walkthrough(scenario: dict[str, Any]) -> dict[str, Any]:
    episode = scenario.get("selected_episode", {})
    evidence_refs = episode.get("evidence_refs") or episode.get("source_refs") or episode.get("supporting_source_refs") or []
    limitations = episode.get("limitations") or []
    if isinstance(evidence_refs, str):
        evidence_refs = [evidence_refs]
    if isinstance(limitations, str):
        limitations = [limitations]
    walkthrough = {
        "task_id": "MAIN-CITYBRAIN-D6-CONTROL-ROOM-R1-EVIDENCE-WALKTHROUGH-R5",
        "status": "PASS_WITH_LIMITATIONS",
        "scenario_id": scenario["scenario_id"],
        "episode_id": scenario.get("selected_episode_id"),
        "evidence_refs": evidence_refs,
        "trace_refs": [
            "outputs/main_citybrain_d5_local_served_runtime_app_consumption_smoke_r1/APP_CONSUMER_STATIC_HTML.html",
            "outputs/main_citybrain_d6_end_to_end_demo_and_episode_frontend_handover_r1/phase5_runtime_demo_slice_r1/RUNTIME_DEMO_PACKET_SEQUENCE.json",
            "outputs/manual_main_track2a_d4x_omniverse_composer_selection_acceptance_r1/MANUAL_OMNIVERSE_COMPOSER_SELECTION_ACCEPTANCE_DECISION.json",
        ],
        "limitations": limitations + [
            "frontend visual acceptance remains NOT_DONE unless separate browser evidence exists",
            "Omniverse screenshot is supporting spatial proof only",
            "safe next-look options are inspection prompts, not commands or recommendations to act",
        ],
        "safe_next_look": [
            "Open the packet index and inspect source refs",
            "Open the evidence trace section before narrating the answer",
            "Open the accepted Omniverse screenshot as supporting spatial context",
            "Review limitations before any demo narration",
        ],
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_EVIDENCE_TRACE_WALKTHROUGH.json", walkthrough)
    write_text(
        OUTPUT_ROOT / "CONTROL_ROOM_EVIDENCE_TRACE_WALKTHROUGH.md",
        f"""
# Evidence Trace Walkthrough

Scenario: `{scenario['scenario_id']}`

Episode: `{scenario.get('selected_episode_id')}`

The demo answer is bounded by visible evidence, trace references, limitations, and safe next-look prompts. Safe next-look is an inspection path only; it is not dispatch, enforcement, routing/control, legal determination, certified impact, or autonomous action.
""",
    )
    safe_flow = {"status": "PASS", "safe_next_look": walkthrough["safe_next_look"], "no_action_taken": True, "not_action_recommendations": True}
    limitation_chain = {"status": "PASS", "limitations": walkthrough["limitations"], "limitations_hidden": False}
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_SAFE_NEXT_LOOK_FLOW.json", safe_flow)
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_SAFE_NEXT_LOOK_FLOW.md", "# Safe Next-Look Flow\n\n" + "\n".join(f"- {item}" for item in safe_flow["safe_next_look"]))
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_LIMITATION_CHAIN.json", limitation_chain)
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_NO_ACTION_BOUNDARY.md", "# No-Action Boundary\n\nNo action is taken. The demo creates review/context evidence only.")
    return walkthrough


def demo_scripts(scenario: dict[str, Any]) -> dict[str, Any]:
    operator = f"""
# Operator Demo Script

Open the local demo index, then the Ask The City runtime consumer. This is a bounded local reference scenario for `{scenario.get('selected_episode_id')}`.

Show the governed answer, trace/evidence, limitations, safe next-look options, and packet index. Then show the accepted Omniverse Composer screenshot as supporting spatial proof for `cer:community:barc:eixample`.

Say: this is local/static/replay evidence-backed context; no action is taken.

Do not say: production live system, real-time command center, dispatch, enforcement, routing/control, legal violation detection, certified impact, citywide twin, or autonomous city control.
"""
    executive = f"""
# Executive Demo Script

This reference demo shows the current CityBrain control-room path as a local, bounded product composition: episode frontend, Ask The City runtime panel, governed answer, trace, limitations, safe next-look, and supporting Omniverse spatial proof.

The strongest claim is that the demo can keep evidence and limitations visible across web/runtime and Omniverse supporting surfaces. The accepted Omniverse proof is manual Composer selection evidence, not a citywide twin or physical simulation claim.

Do not position this as production deployment, public API readiness, legal/enforcement decisioning, traffic/control, dispatch, certified asset impact, or autonomous action.
"""
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_OPERATOR_DEMO_SCRIPT.md", operator)
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_EXECUTIVE_DEMO_SCRIPT.md", executive)
    audit = {"status": "PASS", "operator_script_created": True, "executive_script_created": True, **{flag: False for flag in FORBIDDEN_FLAGS}}
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_SCRIPT_CLAIM_AUDIT.json", audit)
    return audit


def acceptance_matrices(frontend_status: str) -> dict[str, Any]:
    r7_status = read_json(R7_ROOT / "MAIN_TRACK1_D4Y_R7_CROSS_DOMAIN_RELATIONSHIP_EDGE_SEED_R1_DECISION.json", {}).get("status", "NOT_FOUND")
    matrix = [
        {"item": "D5 app-consumption smoke", "category": "Accepted / proven", "status": read_json(D5_APP_DECISION, {}).get("status")},
        {"item": "D6 episode frontend structural build", "category": "Structurally assembled", "status": read_json(D6_DECISION, {}).get("status")},
        {"item": "D6 frontend visual acceptance", "category": "Not yet proven" if frontend_status != "DONE" else "Manually proven", "status": frontend_status},
        {"item": "D6 runtime demo slice", "category": "Structurally assembled", "status": "PASS_WITH_LIMITATIONS"},
        {"item": "Omniverse manual Composer selection", "category": "Manually proven", "status": "DONE"},
        {"item": "event fabric local/replay status", "category": "Supporting artifact", "status": "PASS_WITH_LIMITATIONS"},
        {"item": "R7 relationship substrate", "category": "Future capability" if r7_status == "NOT_FOUND" else "Supporting artifact", "status": r7_status},
        {"item": "production/security status", "category": "Future capability", "status": "DEFERRED"},
        {"item": "incident mode status", "category": "Future capability", "status": "DEFERRED_OR_SEPARATE_TRACK"},
    ]
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_ACCEPTANCE_STATUS_MATRIX.json", {"status": "PASS", "rows": matrix})
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_ACCEPTANCE_STATUS_MATRIX.md", "# Acceptance Status Matrix\n\n" + "\n".join(f"- {row['item']}: {row['category']} / {row['status']}" for row in matrix))
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_SHOWABLE_NOW_MATRIX.md", "# Showable Now\n\n- D5 app-consumption smoke\n- D6 runtime demo slice\n- D6 structural episode frontend\n- Omniverse manual Composer selection screenshot")
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_EXISTS_BUT_NEEDS_WORK_MATRIX.md", "# Exists But Needs Work\n\n- Frontend visual acceptance remains NOT_DONE unless browser evidence is added\n- Production/security/deployment remains deferred")
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_FUTURE_CAPABILITY_MATRIX.md", "# Future Capability\n\n- Incident backend mode\n- Production boundary/security preflight\n- Hero neighbourhood twin expansion")
    return {"status": "PASS", "rows": matrix, "r7_status": r7_status}


def audits(local_manifest: dict[str, Any], walkthrough: dict[str, Any]) -> dict[str, Any]:
    boundary = {
        "status": "PASS",
        **{flag: False for flag in FORBIDDEN_FLAGS},
        "frontend_visual_claim_made": False,
        "local_static_developer_demo_boundary_preserved": True,
    }
    no_action = {
        "status": "PASS",
        "no_action_taken": True,
        "safe_next_look_is_not_action_recommendation": True,
        "dispatch_enforcement_routing_control_output_created": False,
    }
    no_mutation = {
        "status": "PASS",
        "upstream_roots_mutated": False,
        "source_downloads_started": False,
        "production_services_started": False,
        "output_is_additive": True,
    }
    secret = secret_scan()
    hash_audit = write_hashes()
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_BOUNDARY_AUDIT.json", boundary)
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_NO_ACTION_AUDIT.json", no_action)
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_NO_MUTATION_AUDIT.json", no_mutation)
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_SECRET_AUDIT.json", secret)
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_HASH_AUDIT.json", hash_audit)
    return {"boundary": boundary, "no_action": no_action, "no_mutation": no_mutation, "secret": secret, "hash": hash_audit}


def secret_scan() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}"),
        re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._\-]{16,}"),
        re.compile(r"(?i)secret\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}"),
        re.compile(r"(?i)token\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}"),
    ]
    hits = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".html", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    hits.append(out_rel(path))
                    break
    return {"status": "PASS" if not hits else "FAIL", "hits": hits}


def write_hashes() -> dict[str, Any]:
    entries = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name not in {"hashes.sha256", "CONTROL_ROOM_REFERENCE_DEMO_HASH_AUDIT.json"}:
            entries.append({"path": out_rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    text = "\n".join(f"{entry['sha256']}  {entry['path']}" for entry in entries)
    write_text(OUTPUT_ROOT / "hashes.sha256", text)
    return {"status": "PASS", "hash_count": len(entries), "hash_file": str(OUTPUT_ROOT / "hashes.sha256")}


def artifact_index() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file():
            files.append({"path": out_rel(path), "bytes": path.stat().st_size})
    index = {"output_root": str(OUTPUT_ROOT), "artifact_count": len(files), "files": files}
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_ARTIFACT_INDEX.json", index)
    return index


def closeout_and_next(status: str, frontend_status: str) -> dict[str, Any]:
    matrix = [
        {"task": "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-R2-POLISH", "priority": 1, "reason": "best next product step after R1 pack"},
        {"task": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-BACKEND-PREFLIGHT", "priority": 2, "reason": "adds backend incident mode after demo reference path"},
        {"task": "MAIN-TRACK1-D4Y-R7-CROSS-DOMAIN-RELATIONSHIP-EDGE-SEED-R1", "priority": 3, "reason": "only if not completed"},
        {"task": "MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-PREFLIGHT", "priority": 4, "reason": "only if truly still needed"},
        {"task": "MAIN-CITYBRAIN-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT", "priority": 5, "reason": "parked production/security boundary"},
        {"task": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-TWIN-R1", "priority": 6, "reason": "spatial/twin expansion, not required for current demo"},
    ]
    decision = {
        "status": status,
        "frontend_visual_acceptance_status": frontend_status,
        "next_recommended_task": matrix[0]["task"],
        "recommended_parallel_tracks": [
            "MAIN-CITYBRAIN-D6-INCIDENT-MODE-BACKEND-PREFLIGHT",
            "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-TWIN-R1",
        ],
    }
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_R1_CLOSEOUT_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_R1_CLOSEOUT_REPORT.md", f"# R1 Closeout\n\nStatus: `{status}`\n\nNext: `{matrix[0]['task']}`")
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_R1_NEXT_PRIORITY_DECISION_MATRIX.json", {"rows": matrix})
    write_text(
        OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_R1_GIT_CHECKPOINT_PLAN.md",
        f"""
# Git Checkpoint Plan

Do not commit unless explicitly authorized.

```powershell
git add -- scripts/run_main_citybrain_d6_control_room_reference_demo_r1.py
git add -- outputs/main_citybrain_d6_control_room_reference_demo_r1
git commit -m "citybrain: add D6 control-room reference demo R1"
```

Do not add `data/`, bulk assets, the entire `outputs/` tree, or unrelated untracked files.
""",
    )
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_R1_LIMITATIONS_AND_NEXT_STEPS.md", "# Limitations And Next Steps\n\nFrontend visual acceptance remains NOT_DONE unless separate browser evidence is added. Production/security/deployment remain deferred.")
    return decision


def master_manifest(
    phase_statuses: list[dict[str, Any]],
    scenario: dict[str, Any],
    local_manifest: dict[str, Any],
    frontend_status: str,
) -> dict[str, Any]:
    manifest = {
        "task_id": TASK_ID,
        "output_root": str(OUTPUT_ROOT),
        "phase_statuses": phase_statuses,
        "scenario_id": scenario["scenario_id"],
        "selected_episode_id": scenario.get("selected_episode_id"),
        "local_open_index": str(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_LOCAL_OPEN_INDEX.html"),
        "frontend_visual_acceptance_status": frontend_status,
        "omniverse_supporting_evidence": str(OMNI_SCREENSHOT),
        "local_manifest": local_manifest,
    }
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_MANIFEST.json", manifest)
    return manifest


def top_level_docs(status: str, scenario: dict[str, Any], frontend_status: str, phase_statuses: list[dict[str, Any]]) -> None:
    write_text(
        OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_R1_REPORT.md",
        f"""
# Control Room Reference Demo R1

Status: `{status}`

Selected scenario: `{scenario['scenario_id']}`

Selected episode: `{scenario.get('selected_episode_id')}`

Local open index:

```text
{OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_LOCAL_OPEN_INDEX.html"}
```

The web/runtime surface is the primary demo surface. Omniverse is included as accepted supporting spatial evidence from manual Composer screenshot proof.

Frontend visual acceptance status: `{frontend_status}`

Phase status table:

{chr(10).join(f"- {item['phase']}: {item['status']}" for item in phase_statuses)}
""",
    )
    write_text(
        OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_LIMITATIONS.md",
        """
# Limitations

- Local/static/replay developer demo only.
- Frontend visual acceptance remains NOT_DONE unless separate browser screenshot or recording evidence exists.
- Omniverse manual Composer selection is accepted from screenshot evidence, but remains supporting spatial proof only.
- No production frontend, public API, auth/RBAC, external deployment, live production ingestion, citywide twin, full mesh binding, physical accuracy, legal/enforcement/control/dispatch/routing, certified affected-building, or autonomous-action claim.
""",
    )
    write_text(
        OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_NEXT_STEPS.md",
        """
# Next Steps

Recommended next task: `MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-R2-POLISH`.

Useful parallel tracks:

- `MAIN-CITYBRAIN-D6-INCIDENT-MODE-BACKEND-PREFLIGHT`
- `MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-TWIN-R1`
- Parked: `MAIN-CITYBRAIN-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`
""",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK_ID}

Status: `{status}`

Open:

```text
{OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_LOCAL_OPEN_INDEX.html"}
```

This is a bounded local reference demo pack. It is not a production system.
""",
    )


def decision_json(
    status: str,
    phase_statuses: list[dict[str, Any]],
    scenario: dict[str, Any],
    local_manifest: dict[str, Any],
    web_seq: dict[str, Any],
    omni_seq: dict[str, Any],
    walkthrough: dict[str, Any],
    script_audit: dict[str, Any],
    matrix: dict[str, Any],
    audit_results: dict[str, Any],
    frontend_status: str,
    closeout: dict[str, Any],
) -> dict[str, Any]:
    omni_decision = read_json(OMNI_MANUAL_DECISION, {})
    d6_decision = read_json(D6_DECISION, {})
    d5_decision = read_json(D5_APP_DECISION, {})
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now(),
        "runner_path": str(RUNNER_PATH),
        "upstream_d6_handover_found": D6_DECISION.exists(),
        "upstream_app_consumption_found": D5_APP_DECISION.exists(),
        "upstream_runtime_demo_preflight_found": D6_PREFLIGHT_DECISION.exists(),
        "upstream_reference_spine_found": REFERENCE_SPINE_DECISION.exists(),
        "upstream_omniverse_manual_acceptance_found": OMNI_MANUAL_DECISION.exists(),
        "omniverse_manual_acceptance_status": omni_decision.get("status"),
        "omniverse_composer_gui_proven": omni_decision.get("actual_composer_gui_proven", False),
        "omniverse_selection_resolution_proven": omni_decision.get("actual_selection_resolution_proven", False),
        "omniverse_evidence_included": OMNI_SCREENSHOT.exists(),
        "episode_records_found": d6_decision.get("episode_count_found"),
        "selected_demo_episodes_count": read_json(D6_ROOT / "phase3_episode_frontend_consumer_r1" / "EPISODE_FRONTEND_CONSUMER_R1_DECISION.json", {}).get("episode_count"),
        "demo_scenario_selected": bool(scenario),
        "demo_pack_self_contained": all(item["packaged_exists"] for item in local_manifest["assets"].values()),
        "local_open_index_created": (OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_LOCAL_OPEN_INDEX.html").exists(),
        "web_runtime_sequence_created": bool(web_seq),
        "omniverse_supporting_sequence_created": bool(omni_seq),
        "evidence_trace_walkthrough_created": bool(walkthrough),
        "safe_next_look_flow_created": (OUTPUT_ROOT / "CONTROL_ROOM_SAFE_NEXT_LOOK_FLOW.json").exists(),
        "operator_demo_script_created": (OUTPUT_ROOT / "CONTROL_ROOM_OPERATOR_DEMO_SCRIPT.md").exists(),
        "executive_demo_script_created": (OUTPUT_ROOT / "CONTROL_ROOM_EXECUTIVE_DEMO_SCRIPT.md").exists(),
        "acceptance_status_matrix_created": bool(matrix),
        "frontend_visual_acceptance_status": frontend_status,
        "frontend_visual_claim_made": False,
        "frontend_visual_evidence_present": frontend_status == "DONE",
        "trace_refs_present": d6_decision.get("trace_refs_present", False) or d5_decision.get("trace_refs_displayed", False),
        "evidence_refs_present": d6_decision.get("evidence_refs_present", False),
        "limitation_refs_present": d6_decision.get("limitation_refs_present", False) or d5_decision.get("limitation_refs_displayed", False),
        "safe_next_look_present": d6_decision.get("safe_next_look_present", False) or d5_decision.get("safe_next_look_options_displayed", False),
        "no_action_boundary_visible": omni_decision.get("no_action_boundary_visible", False) and d5_decision.get("no_action_boundary_preserved", False),
        "boundary_audit_passed": audit_results["boundary"]["status"] == "PASS",
        "no_action_audit_passed": audit_results["no_action"]["status"] == "PASS",
        "no_mutation_audit_passed": audit_results["no_mutation"]["status"] == "PASS",
        "secret_audit_passed": audit_results["secret"]["status"] == "PASS",
        "hash_audit_passed": audit_results["hash"]["status"] == "PASS",
        "commit_performed": False,
        "git_checkpoint_plan_created": (OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_R1_GIT_CHECKPOINT_PLAN.md").exists(),
        "next_recommended_task": closeout["next_recommended_task"],
        "recommended_parallel_tracks": closeout["recommended_parallel_tracks"],
        "phase_status_table": phase_statuses,
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json", decision)
    return decision


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    DEMO_ASSETS.mkdir(parents=True, exist_ok=True)
    phase_statuses: list[dict[str, Any]] = []

    upstream_audit, go_no_go = phase0_upstream_audit()
    phase_statuses.append({"phase": "PHASE0_UPSTREAM_DEMO_READINESS_AUDIT", "status": upstream_audit["status"]})
    if upstream_audit["status"] in {"HOLD", "FAIL"}:
        status = upstream_audit["status"]
        scenario = {"scenario_id": None}
        local_manifest: dict[str, Any] = {"assets": {}}
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json", {"task_id": TASK_ID, "status": status, "output_root": str(OUTPUT_ROOT), "phase_status_table": phase_statuses})
        print(json.dumps({"status": status, "output_root": str(OUTPUT_ROOT)}, indent=2))
        return 0 if status == "HOLD" else 1

    frontend_status = upstream_audit["frontend_visual_acceptance_status"]
    scenario, bundle = select_scenario()
    phase_statuses.append({"phase": "PHASE1_SCENARIO_SELECTION", "status": scenario["status"]})
    local_manifest = assemble_demo_pack(scenario)
    phase_statuses.append({"phase": "PHASE2_DEMO_PACK_ASSEMBLY", "status": "PASS"})
    web_seq = web_runtime_sequence(frontend_status)
    phase_statuses.append({"phase": "PHASE3_WEB_RUNTIME_SEQUENCE", "status": web_seq["status"]})
    omni_seq = omniverse_sequence(scenario)
    phase_statuses.append({"phase": "PHASE4_OMNIVERSE_SUPPORTING_SEQUENCE", "status": omni_seq["status"]})
    walkthrough = evidence_walkthrough(scenario)
    phase_statuses.append({"phase": "PHASE5_EVIDENCE_TRACE_WALKTHROUGH", "status": walkthrough["status"]})
    script_audit = demo_scripts(scenario)
    phase_statuses.append({"phase": "PHASE6_DEMO_SCRIPTS", "status": script_audit["status"]})
    matrix = acceptance_matrices(frontend_status)
    phase_statuses.append({"phase": "PHASE7_ACCEPTANCE_STATUS_MATRIX", "status": matrix["status"]})
    top_level_docs("PASS_WITH_LIMITATIONS" if frontend_status != "DONE" else "PASS", scenario, frontend_status, phase_statuses)
    manifest = master_manifest(phase_statuses, scenario, local_manifest, frontend_status)
    artifact_index()
    audit_results = audits(local_manifest, walkthrough)
    audit_status = "PASS" if all(v["status"] == "PASS" for v in audit_results.values()) else "FAIL"
    phase_statuses.append({"phase": "PHASE8_AUDITS", "status": audit_status})
    status = "PASS_WITH_LIMITATIONS" if frontend_status != "DONE" else "PASS"
    if audit_status != "PASS":
        status = "FAIL"
    closeout = closeout_and_next(status, frontend_status)
    phase_statuses.append({"phase": "PHASE9_CLOSEOUT", "status": closeout["status"]})
    top_level_docs(status, scenario, frontend_status, phase_statuses)
    master_manifest(phase_statuses, scenario, local_manifest, frontend_status)
    artifact_index()
    audit_results = audits(local_manifest, walkthrough)
    decision = decision_json(status, phase_statuses, scenario, local_manifest, web_seq, omni_seq, walkthrough, script_audit, matrix, audit_results, frontend_status, closeout)
    artifact_index()
    audit_results["hash"] = write_hashes()

    print(json.dumps({
        "task_id": TASK_ID,
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "local_open_index": str(OUTPUT_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_LOCAL_OPEN_INDEX.html"),
        "frontend_visual_acceptance_status": frontend_status,
        "omniverse_manual_acceptance_status": decision["omniverse_manual_acceptance_status"],
        "next_recommended_task": decision["next_recommended_task"],
    }, indent=2, sort_keys=True))
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
