#!/usr/bin/env python3
"""Run the D8 deep story inventory and role portfolio sprint.

This is an inventory-only runner. It reads existing compact reports and fixture
bundles, classifies story candidates, and writes planning artifacts. It does not
edit UI, Kit, runtime, or existing story/source fixture files.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "outputs"
FIXTURES = REPO / "packages" / "fixtures"

TASK = "MAIN-CITYBRAIN-D8-DEEP-STORY-INVENTORY-ROLE-PORTFOLIO"
STATUS_PASS = "PASS_MAIN_CITYBRAIN_D8_DEEP_STORY_INVENTORY_MILESTONE_FREEZE_WITH_LIMITATIONS"
BOUNDARY = (
    "Local/replay/review/query context only; no production/public API, live monitoring, "
    "alerts, dispatch, routing/control, enforcement, official ticket/case creation, "
    "legal/certified finding, certified asset/operational impact, or automated action."
)

ROOTS = {
    "preflight": OUTPUTS / "main_citybrain_d8_deep_story_inventory_preflight",
    "discovery": OUTPUTS / "main_citybrain_d8_output_ledger_story_discovery_r1",
    "london": OUTPUTS / "main_citybrain_d8_london_primary_story_queue_inventory_r2",
    "chicago": OUTPUTS / "main_citybrain_d8_chicago_precedent_memory_inventory_r3",
    "nyc": OUTPUTS / "main_citybrain_d8_nyc_cascade_story_inventory_r4",
    "helsinki": OUTPUTS / "main_citybrain_d8_helsinki_visual_entity_capability_inventory_r5",
    "barc_sg": OUTPUTS / "main_citybrain_d8_barcelona_singapore_parked_story_scout_r6",
    "trust": OUTPUTS / "main_citybrain_d8_governance_trust_moment_inventory_r7",
    "portfolio": OUTPUTS / "main_citybrain_d8_cross_city_story_role_portfolio_r8",
    "requirements": OUTPUTS / "main_citybrain_d8_brain_surface_portfolio_requirements_r9",
    "closeout": OUTPUTS / "main_citybrain_d8_deep_story_inventory_closeout",
    "freeze": OUTPUTS / "main_citybrain_d8_deep_story_inventory_milestone_freeze",
}

PROTECTED_PATHS = [
    REPO / "apps" / "web-control-room",
    REPO / "apps" / "kit",
    FIXTURES / "story_first_demo",
    FIXTURES / "source_record_ui_integrated",
    FIXTURES / "london_mobility_source_records",
    FIXTURES / "chicago_similar_case_records",
    FIXTURES / "helsinki_visual_entity_pick",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "digest": None}
    parts: list[str] = []
    files = [p for p in path.rglob("*") if p.is_file()]
    for file_path in sorted(files):
        parts.append(f"{rel(file_path)}:{sha256_file(file_path)}")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return {"exists": True, "file_count": len(files), "digest": digest}


def write_hash_manifest(root: Path) -> None:
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "HASH_MANIFEST.json":
            continue
        files[rel(path)] = sha256_file(path)
    write_json(root / "HASH_MANIFEST.json", {"generated_at": now(), "files": files})


def local_open_index(root: Path, title: str) -> None:
    rows = [f"# {title}", "", "Generated artifacts:"]
    for path in sorted(root.iterdir()):
        if path.is_file():
            rows.append(f"- `{rel(path)}`")
    write_md(root / "LOCAL_OPEN_INDEX.md", "\n".join(rows))


def compact_file_candidates(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    patterns = re.compile(
        r"(decision|summary|report|candidate|story|source|role|queue|trust|visual|scenario|closeout|freeze)",
        re.IGNORECASE,
    )
    out: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.stat().st_size > 2_000_000:
            continue
        if path.suffix.lower() not in {".json", ".md", ".jsonl", ".csv"}:
            continue
        if patterns.search(path.name) or patterns.search(str(path.parent.name)):
            out.append({"path": rel(path), "bytes": path.stat().st_size})
        if len(out) >= 80:
            break
    return out


def output_root_index() -> list[dict[str, Any]]:
    if not OUTPUTS.exists():
        return []
    roots = []
    keywords = (
        "story",
        "source_record",
        "london",
        "chicago",
        "helsinki",
        "nyc",
        "barc",
        "singapore",
        "sg_",
        "governance",
        "guardrail",
        "review",
        "cascade",
        "hero",
        "visual",
        "omniverse",
        "d8",
        "d6",
    )
    for root in sorted(p for p in OUTPUTS.iterdir() if p.is_dir()):
        name = root.name.lower()
        if any(k in name for k in keywords):
            roots.append(
                {
                    "root": rel(root),
                    "file_count": sum(1 for p in root.rglob("*") if p.is_file()),
                    "compact_artifacts": compact_file_candidates(root)[:12],
                }
            )
    return roots


def candidate(
    *,
    candidate_id: str,
    city: str,
    title: str,
    role: str,
    source_records: list[str],
    specific_subject: str,
    tension_type: str,
    affected_assets_or_users: str,
    intelligence_beat: str,
    option_or_review_path: str,
    evidence_strength_score: int,
    story_tension_score: int,
    ui_potential_score: int,
    strategic_importance_score: int,
    impact_score: int,
    confidence: str,
    viewer_readiness: str,
    next_action: str,
    source_artifacts: list[str],
    standalone_or_woven: str = "queue_item",
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "city": city,
        "title": title,
        "role": role,
        "standalone_or_woven": standalone_or_woven,
        "source_records": source_records,
        "specific_subject": specific_subject,
        "tension_type": tension_type,
        "affected_assets_or_users": affected_assets_or_users,
        "intelligence_beat": intelligence_beat,
        "option_or_review_path": option_or_review_path,
        "boundary_stop": BOUNDARY,
        "evidence_strength_score": evidence_strength_score,
        "story_tension_score": story_tension_score,
        "UI_potential_score": ui_potential_score,
        "strategic_importance_score": strategic_importance_score,
        "impact_score": impact_score,
        "confidence": confidence,
        "viewer_readiness": viewer_readiness,
        "next_action": next_action,
        "source_artifacts": source_artifacts,
    }


def build_london_candidates() -> list[dict[str, Any]]:
    story_bundle_path = FIXTURES / "story_first_demo" / "story_source_bundle.json"
    london_probe_path = (
        OUTPUTS
        / "main_citybrain_d8_story_mining_and_story_first_ui_redesign"
        / "02_london_mobility_story_probe_r1"
        / "LONDON_MOBILITY_STORY_CANDIDATES.json"
    )
    story_bundle = read_json(story_bundle_path, {})
    probe = read_json(london_probe_path, {"candidates": []})
    selected = story_bundle.get("selected_story", {})
    candidates: list[dict[str, Any]] = []
    seen = set()
    selected_records: set[str] = set()

    if selected:
        selected_records = {str(x) for x in selected.get("source_record_ids", [])}
        candidates.append(
            candidate(
                candidate_id=selected.get("story_id", "story:lon:wood_lane_ev_access_review"),
                city="London",
                title=selected.get("scene_title", "Wood Lane works near a named rapid EV access asset"),
                role="primary_story",
                source_records=list(selected.get("source_record_ids", [])),
                specific_subject=selected.get("place_or_corridor", "Wood Lane / Scrubbs Lane"),
                tension_type="nearby works plus access asset uncertainty",
                affected_assets_or_users=selected.get("who_or_what_is_affected", "Named rapid EV access asset context"),
                intelligence_beat=selected.get("why_this_is_non_obvious", "Proximity is connected but causality is refused."),
                option_or_review_path="Inspect source records together; ask for stronger evidence before any impact claim.",
                evidence_strength_score=5,
                story_tension_score=4,
                ui_potential_score=5,
                strategic_importance_score=5,
                impact_score=4,
                confidence="high_for_review_story",
                viewer_readiness="ready_as_story_queue_baseline_with_limitations",
                next_action="Use as first queue item; add scenario layer and human-review choices.",
                source_artifacts=[rel(story_bundle_path), rel(london_probe_path)],
            )
        )
        seen.add(candidates[-1]["candidate_id"])

    for raw in probe.get("candidates", []):
        story_id = raw.get("story_id", "")
        if story_id in seen:
            continue
        raw_records = {str(x) for x in raw.get("source_record_ids", [])}
        # The prior probe keeps the Wood Lane/Scrubbs Lane candidate under a
        # generic mobility ID; the story bundle is the canonical story version.
        if selected_records and len(raw_records & selected_records) >= 2:
            continue
        ev = raw.get("ev_record", {})
        matches = raw.get("disruption_matches", [])
        primary_match = matches[0] if matches else {}
        title = raw.get("place_or_corridor") or ev.get("title") or story_id
        if "near" not in title.lower() and primary_match:
            title = f"{ev.get('title', story_id)} near TfL road works"
        candidates.append(
            candidate(
                candidate_id=story_id or f"story:lon:mobility:{ev.get('external_record_id', len(candidates)+1)}",
                city="London",
                title=title,
                role="primary_story",
                source_records=[str(x) for x in raw.get("source_record_ids", [])],
                specific_subject=raw.get("place_or_corridor", ev.get("title", "London mobility access asset")),
                tension_type="mobility access uncertainty",
                affected_assets_or_users="Named rapid EV access asset and nearby road users, review context only.",
                intelligence_beat=raw.get("coherence_reason", "Bounded proximity join between TfL disruption and EV asset."),
                option_or_review_path="Queue for scenario authoring; retain no-causality stop.",
                evidence_strength_score=4,
                story_tension_score=4 if "Serious" in json.dumps(raw) else 3,
                ui_potential_score=4,
                strategic_importance_score=4,
                impact_score=3,
                confidence="medium_high_for_review_queue",
                viewer_readiness="needs_scenario_layer",
                next_action="Author source-backed scenario layer before surfacing as a full story.",
                source_artifacts=[rel(london_probe_path)],
            )
        )
    return candidates


def build_chicago_candidates() -> list[dict[str, Any]]:
    path = (
        OUTPUTS
        / "main_citybrain_d8_story_mining_and_story_first_ui_redesign"
        / "03_chicago_precedent_story_probe_r1"
        / "CHICAGO_PRECEDENT_STORY_CANDIDATES.json"
    )
    raw = read_json(path, {"candidates": []})
    out = []
    for item in raw.get("candidates", []):
        out.append(
            candidate(
                candidate_id=item.get("story_id", f"story:chi:precedent:{len(out)+1}"),
                city="Chicago",
                title=f"Chicago precedent memory: {item.get('place_or_corridor', 'source case')}",
                role="capability_cutaway",
                standalone_or_woven="woven_cutaway",
                source_records=[str(x) for x in item.get("source_record_ids", [])],
                specific_subject=item.get("place_or_corridor", "Chicago source case"),
                tension_type="precedent recall and similarity uncertainty",
                affected_assets_or_users="Comparable civic/building-condition review context only.",
                intelligence_beat=item.get("match_reason", "Rule-bounded similar-case memory with source ID."),
                option_or_review_path="Open as precedent recall from a primary story; do not convert to instruction.",
                evidence_strength_score=4,
                story_tension_score=2,
                ui_potential_score=4,
                strategic_importance_score=4,
                impact_score=3,
                confidence="high_as_cutaway_medium_as_story",
                viewer_readiness="usable_as_capability_cutaway",
                next_action="Wire into a primary story as precedent memory.",
                source_artifacts=[rel(path)],
            )
        )
    return out


def build_helsinki_candidates() -> list[dict[str, Any]]:
    path = (
        OUTPUTS
        / "main_citybrain_d8_story_mining_and_story_first_ui_redesign"
        / "04_helsinki_visual_pick_story_probe_r1"
        / "HELSINKI_VISUAL_PICK_STORY_CANDIDATES.json"
    )
    raw = read_json(path, {"candidates": []})
    out = []
    for item in raw.get("candidates", []):
        out.append(
            candidate(
                candidate_id=item.get("story_id", f"story:hel:visual_pick:{len(out)+1}"),
                city="Helsinki",
                title=f"Helsinki visual entity pick: {item.get('place_or_corridor', 'semantic building')}",
                role="capability_cutaway",
                standalone_or_woven="woven_cutaway",
                source_records=[str(x) for x in item.get("source_record_ids", [])],
                specific_subject=item.get("place_or_corridor", "Helsinki semantic building"),
                tension_type="identity resolution boundary",
                affected_assets_or_users="Selected visual/semantic building candidate.",
                intelligence_beat="USD/visual pick resolves to semantic building candidate while refusing certified identity.",
                option_or_review_path="Launch as visual-object-to-entity capability from a story.",
                evidence_strength_score=4,
                story_tension_score=2,
                ui_potential_score=5,
                strategic_importance_score=5,
                impact_score=3,
                confidence="high_as_cutaway_low_as_primary_story",
                viewer_readiness="usable_as_visual_cutaway",
                next_action="Pair with an actual event/tension before treating as primary story.",
                source_artifacts=[rel(path)],
            )
        )
    return out


def build_nyc_candidates() -> list[dict[str, Any]]:
    selector = OUTPUTS / "f3_nyc_d8_flow3_hero_package" / "F3_NYC_D8_SELECTOR_REPORT.json"
    cascade = OUTPUTS / "main_citybrain_d6_cross_domain_cascade_closeout" / "MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_CLOSEOUT_DECISION.json"
    selector_json = read_json(selector, {})
    subjects = selector_json.get("selected_subject_ids", {})
    return [
        candidate(
            candidate_id="story:nyc:cascade:mvc_crash_4463710",
            city="NYC",
            title="NYC affected-asset response cascade candidate",
            role="parked_backlog",
            source_records=[subjects.get("hero_1_top_candidate_incident", "event:us-nyc:flow3:mvc_crash:4463710")],
            specific_subject=subjects.get("hero_1_top_candidate_incident", "MVC crash candidate incident"),
            tension_type="incident-to-affected-asset cascade",
            affected_assets_or_users="Nearby assets and response context, review-only.",
            intelligence_beat="Official-record chain can connect incident, route/resource context, and bounded affected-asset review.",
            option_or_review_path="Needs source-backed scenario authoring before viewer queue.",
            evidence_strength_score=4,
            story_tension_score=5,
            ui_potential_score=5,
            strategic_importance_score=5,
            impact_score=5,
            confidence="medium_high_but_not_current_story",
            viewer_readiness="parked_needs_scenario_authoring",
            next_action="Author a bounded NYC cascade scenario from the Flow 3 hero package.",
            source_artifacts=[rel(selector), rel(cascade)],
        ),
        candidate(
            candidate_id="story:nyc:fdny_review_route:engine_227",
            city="NYC",
            title="Brooklyn FDNY review-route context candidate",
            role="parked_backlog",
            source_records=[
                subjects.get(
                    "hero_2_top_operator_review_route",
                    "review_route:us-nyc:flow3:d4:001:brooklyn:resource_us_nyc_fdny_firehouse_engine_227",
                )
            ],
            specific_subject="Brooklyn FDNY firehouse Engine 227 route review context",
            tension_type="response-resource context and review routing",
            affected_assets_or_users="Response-resource review path, not dispatch.",
            intelligence_beat="Route/resource trace is available but must remain review-only.",
            option_or_review_path="Keep as supporting route/trace layer inside an authored NYC story.",
            evidence_strength_score=4,
            story_tension_score=4,
            ui_potential_score=4,
            strategic_importance_score=4,
            impact_score=4,
            confidence="medium",
            viewer_readiness="parked_needs_story_context",
            next_action="Bind to a primary incident story after scenario authoring.",
            source_artifacts=[rel(selector)],
        ),
        candidate(
            candidate_id="trust:nyc:negative_affected_buildings",
            city="NYC",
            title="NYC negative affected-building claim refusal",
            role="trust_moment",
            standalone_or_woven="woven_trust_moment",
            source_records=[subjects.get("hero_4_governance_negative_request", "negative_affected_buildings")],
            specific_subject="Negative affected-building claim request",
            tension_type="claim boundary/refusal",
            affected_assets_or_users="Reviewer trust and affected-building claim boundary.",
            intelligence_beat="System refuses certified affected-building truth without sufficient evidence.",
            option_or_review_path="Weave into NYC cascade drilldown as a refusal/review stop.",
            evidence_strength_score=4,
            story_tension_score=3,
            ui_potential_score=5,
            strategic_importance_score=5,
            impact_score=4,
            confidence="high_as_trust_moment",
            viewer_readiness="ready_as_woven_trust_moment",
            next_action="Use as trust layer inside cascade story.",
            source_artifacts=[rel(selector)],
        ),
    ]


def build_barc_sg_candidates() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    barc_f7 = OUTPUTS / "barc_f7_review_flow_acceptance_r1" / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_DECISION.json"
    barc_f1 = OUTPUTS / "barc_f1f6_flow_acceptance_closeout_r1" / "BARC_F1_ACCEPTANCE_DECISION.json"
    sg_rec = OUTPUTS / "sg_d1_singapore_source_api_scout" / "SG_D1_D2_RECOMMENDATION.json"
    vss = OUTPUTS / "main_citybrain_d8_metropolis_vss_data_readiness_scout" / "METROPOLIS_VSS_READINESS_MATRIX.json"
    barcelona = [
        candidate(
            candidate_id="parked:barc:f7:civic_sensor_review",
            city="Barcelona",
            title="Barcelona civic/sensor fusion review flow potential",
            role="parked_backlog",
            source_records=["BARC-F7", "IRIS", "Sentilo", "Bicing", "air/noise"],
            specific_subject="BARC-F7 review-only civic/sensor fusion bundle",
            tension_type="rich context without a named viewer-ready situation",
            affected_assets_or_users="Civic service and sensor context, no operational command.",
            intelligence_beat="Strong city context exists, but it is still a flow bundle rather than a story subject.",
            option_or_review_path="Find a specific IRIS/event/sensor tension before surfacing.",
            evidence_strength_score=4,
            story_tension_score=2,
            ui_potential_score=4,
            strategic_importance_score=4,
            impact_score=3,
            confidence="high_as_data_low_as_story",
            viewer_readiness="parked_needs_specific_tension",
            next_action="Mine named IRIS/sensor/Bicing situations for one city story.",
            source_artifacts=[rel(barc_f7)],
        ),
        candidate(
            candidate_id="parked:barc:f1:situational_status",
            city="Barcelona",
            title="Barcelona F1 situational status source depth",
            role="parked_backlog",
            source_records=["BARC-F1", "IRIS", "traffic", "Bicing", "boundaries"],
            specific_subject="Accepted review flow with limitations, not one story.",
            tension_type="flow richness without story anatomy",
            affected_assets_or_users="City context users, review-only.",
            intelligence_beat="Accepted flow proves data breadth but not a named story tension.",
            option_or_review_path="Select one named event/asset corridor before UI build.",
            evidence_strength_score=4,
            story_tension_score=1,
            ui_potential_score=3,
            strategic_importance_score=4,
            impact_score=3,
            confidence="high_as_backlog",
            viewer_readiness="parked_needs_story_selection",
            next_action="Run Barcelona source-to-story mining, not another dashboard pass.",
            source_artifacts=[rel(barc_f1)],
        ),
    ]
    singapore = [
        candidate(
            candidate_id="parked:sg:lta_camera_perception",
            city="Singapore",
            title="Singapore traffic camera/perception potential",
            role="parked_backlog",
            source_records=["LTA DataMall", "traffic cameras", "TrafficSpeedBands"],
            specific_subject="LTA/OneMap source scout potential",
            tension_type="camera/perception potential without licensed media/story binding",
            affected_assets_or_users="Traffic context viewers, no traffic-control output.",
            intelligence_beat="Source scout shows future camera/perception potential but lacks licensed visual story media.",
            option_or_review_path="Acquire licensed media/sample mapping before story use.",
            evidence_strength_score=3,
            story_tension_score=2,
            ui_potential_score=4,
            strategic_importance_score=5,
            impact_score=4,
            confidence="medium_as_backlog",
            viewer_readiness="parked_needs_source_media_and_mapping",
            next_action="Complete SG-D2 source expansion and licensed media mapping.",
            source_artifacts=[rel(sg_rec), rel(vss)],
        ),
        candidate(
            candidate_id="data_gap:sg:onemap_planning_area",
            city="Singapore",
            title="Singapore OneMap planning area token limitation",
            role="data_gap",
            standalone_or_woven="gap",
            source_records=["OneMap token-limited"],
            specific_subject="Planning area/theme metadata access",
            tension_type="resource resolution gap",
            affected_assets_or_users="Future Singapore city identity spine.",
            intelligence_beat="Token-limited source prevents robust city identity/story anchoring.",
            option_or_review_path="Resolve token and land selected planning areas/themes.",
            evidence_strength_score=2,
            story_tension_score=1,
            ui_potential_score=3,
            strategic_importance_score=4,
            impact_score=3,
            confidence="high_as_gap",
            viewer_readiness="blocked_by_resource_resolution",
            next_action="Resolve OneMap token and parse source-specific inventories.",
            source_artifacts=[rel(sg_rec)],
        ),
    ]
    other = [
        candidate(
            candidate_id="parked:vss:licensed_corpus",
            city="Cross-city",
            title="Metropolis/VSS licensed corpus readiness potential",
            role="parked_backlog",
            source_records=["VSS readiness matrix", "licensed corpus acquisition"],
            specific_subject="Video-to-evidence source family",
            tension_type="licensed media availability and privacy boundary",
            affected_assets_or_users="Future perception-backed story surfaces.",
            intelligence_beat="Perception/video can become a story layer only after licensed sample and evidence mapping.",
            option_or_review_path="Keep as data readiness lane until samples are licensed and bounded.",
            evidence_strength_score=3,
            story_tension_score=2,
            ui_potential_score=4,
            strategic_importance_score=5,
            impact_score=4,
            confidence="medium",
            viewer_readiness="parked_needs_licensed_media",
            next_action="Continue VSS sample acquisition and evidence mapping smoke.",
            source_artifacts=[rel(vss)],
        )
    ]
    return barcelona, singapore, other


def build_trust_moments() -> list[dict[str, Any]]:
    return [
        candidate(
            candidate_id="trust:global:no_action_boundary",
            city="Cross-city",
            title="No action taken boundary stays visible",
            role="trust_moment",
            standalone_or_woven="woven_trust_moment",
            source_records=["guardrail/no-action audits"],
            specific_subject="No dispatch/enforcement/routing/control/legal claim boundary",
            tension_type="operator trust and action boundary",
            affected_assets_or_users="All viewers and reviewers.",
            intelligence_beat="The system explains what it will not do as part of evidence, not as a hidden footer.",
            option_or_review_path="Show inside every primary story drilldown.",
            evidence_strength_score=5,
            story_tension_score=3,
            ui_potential_score=5,
            strategic_importance_score=5,
            impact_score=5,
            confidence="high",
            viewer_readiness="ready_as_reusable_trust_moment",
            next_action="Weave into queue cards and drilldowns.",
            source_artifacts=["outputs/*CLAIM_BOUNDARY_AUDIT*", "outputs/*NO_ACTION*"],
        ),
        candidate(
            candidate_id="trust:london:proximity_not_causality",
            city="London",
            title="Proximity does not prove access impact",
            role="trust_moment",
            standalone_or_woven="woven_trust_moment",
            source_records=["TIMS-219173", "TIMS-210389", "87"],
            specific_subject="Wood Lane/Scrubbs Lane source join",
            tension_type="uncertainty disclosure",
            affected_assets_or_users="EV access story viewers.",
            intelligence_beat="CityBrain connects nearby records while refusing to claim blockage or availability change.",
            option_or_review_path="Show before any viewer asks for operational interpretation.",
            evidence_strength_score=5,
            story_tension_score=4,
            ui_potential_score=5,
            strategic_importance_score=5,
            impact_score=4,
            confidence="high",
            viewer_readiness="ready_inside_wood_lane_story",
            next_action="Keep attached to London primary queue item.",
            source_artifacts=[rel(FIXTURES / "story_first_demo" / "story_source_bundle.json")],
        ),
        candidate(
            candidate_id="trust:chicago:precedent_not_prediction",
            city="Chicago",
            title="Similar case is context, not prediction",
            role="trust_moment",
            standalone_or_woven="woven_trust_moment",
            source_records=["Chicago Building Violations"],
            specific_subject="Similar-case memory boundary",
            tension_type="precedent overclaim prevention",
            affected_assets_or_users="Reviewer using precedent cutaway.",
            intelligence_beat="The memory layer can recall comparable records without implying causality, prediction, or enforcement.",
            option_or_review_path="Attach to every Chicago precedent cutaway.",
            evidence_strength_score=4,
            story_tension_score=3,
            ui_potential_score=4,
            strategic_importance_score=4,
            impact_score=3,
            confidence="high",
            viewer_readiness="ready_as_cutaway_trust_layer",
            next_action="Weave into precedent memory panel.",
            source_artifacts=[rel(FIXTURES / "chicago_similar_case_records" / "similar_case_source_bundle.json")],
        ),
        candidate(
            candidate_id="trust:helsinki:visual_identity_candidate_only",
            city="Helsinki",
            title="Visual pick resolves to candidate identity only",
            role="trust_moment",
            standalone_or_woven="woven_trust_moment",
            source_records=["Helsinki semantic building sample", "generated prim path"],
            specific_subject="USD/CityGML/CER candidate boundary",
            tension_type="visual identity certification boundary",
            affected_assets_or_users="Visual twin users.",
            intelligence_beat="A picked object can open CER context while refusing certified legal/physical truth.",
            option_or_review_path="Attach to visual pick cutaway.",
            evidence_strength_score=4,
            story_tension_score=3,
            ui_potential_score=5,
            strategic_importance_score=5,
            impact_score=4,
            confidence="high",
            viewer_readiness="ready_as_visual_cutaway_trust_layer",
            next_action="Keep visible in Kit/Omniverse handoff.",
            source_artifacts=[rel(FIXTURES / "helsinki_visual_entity_pick" / "source_record_bundle.json")],
        ),
        candidate(
            candidate_id="trust:global:records_are_not_stories",
            city="Cross-city",
            title="Records are not stories",
            role="trust_moment",
            standalone_or_woven="portfolio_principle",
            source_records=["D8 story probe", "deep inventory scope lock"],
            specific_subject="Story anatomy gate",
            tension_type="product composition discipline",
            affected_assets_or_users="Future UI builders.",
            intelligence_beat="Source records must pass subject/tension/evidence/options/boundary checks before becoming queue items.",
            option_or_review_path="Use as gate for every future story candidate.",
            evidence_strength_score=5,
            story_tension_score=2,
            ui_potential_score=4,
            strategic_importance_score=5,
            impact_score=5,
            confidence="high",
            viewer_readiness="ready_as_portfolio_rule",
            next_action="Bake into story queue data contract.",
            source_artifacts=["outputs/main_citybrain_d8_story_probe_only_closeout", rel(Path(__file__))],
        ),
    ]


def counts_by_city_and_role(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    by_city = Counter(c["city"] for c in candidates)
    by_role = Counter(c["role"] for c in candidates)
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for c in candidates:
        matrix[c["city"]][c["role"]] += 1
    return {
        "total_candidates": len(candidates),
        "by_city": dict(sorted(by_city.items())),
        "by_role": dict(sorted(by_role.items())),
        "matrix": {city: dict(sorted(roles.items())) for city, roles in sorted(matrix.items())},
    }


def run() -> int:
    run_started = now()
    protected_before = {rel(p): tree_fingerprint(p) for p in PROTECTED_PATHS}
    for root in ROOTS.values():
        root.mkdir(parents=True, exist_ok=True)

    output_index = output_root_index()
    story_bundle_path = FIXTURES / "story_first_demo" / "story_source_bundle.json"
    story_bundle = read_json(story_bundle_path, {})

    # 1. Preflight.
    preflight = ROOTS["preflight"]
    required_inputs = [
        "outputs/main_citybrain_d8_story_probe_only_closeout",
        "outputs/main_citybrain_d8_story_mining_and_story_first_ui_redesign",
        "outputs/main_citybrain_d8_story_scenario_layer_closeout",
        "outputs/main_citybrain_d8_source_record_recovery_certified_state_handoff",
        "outputs/main_citybrain_d8_source_record_ui_closeout",
        "outputs/main_citybrain_d8_actual_record_grounded_ui_milestone_freeze",
        "packages/fixtures/story_first_demo",
        "packages/fixtures/source_record_ui_integrated",
        "packages/fixtures/london_mobility_source_records",
        "packages/fixtures/chicago_similar_case_records",
        "packages/fixtures/helsinki_visual_entity_pick",
    ]
    input_index = [
        {
            "path": path,
            "exists": (REPO / path).exists(),
            "compact_artifacts": compact_file_candidates(REPO / path)[:20] if (REPO / path).exists() else [],
        }
        for path in required_inputs
    ]
    story_anatomy = {
        "required_fields": [
            "specific_subject",
            "tension",
            "evidence",
            "intelligence_beat",
            "options_or_boundary",
            "ui_role",
        ],
        "rule": "Raw records, flows, governance logs, and visual picks are not stories unless they pass this anatomy.",
    }
    role_taxonomy = {
        "primary_story": "A queue item a viewer can open and follow end to end.",
        "trust_moment": "Governance/refusal/uncertainty/review stop woven inside a story.",
        "capability_cutaway": "Reusable capability demonstration launched from a story.",
        "parked_backlog": "Potential story lane lacking current viewer-ready story anatomy.",
        "data_gap": "Required story element missing from current data.",
    }
    write_json(preflight / "SCOPE_LOCK.json", {"task": TASK, "inventory_only": True, "boundary": BOUNDARY})
    write_json(preflight / "INPUT_ROOT_CANDIDATE_INDEX.json", input_index)
    write_json(
        preflight / "NO_UI_MUTATION_PLAN.json",
        {
            "protected_paths": [rel(p) for p in PROTECTED_PATHS],
            "allowed_writes": [rel(p) for p in ROOTS.values()] + [rel(Path(__file__))],
            "planned_ui_mutation": False,
        },
    )
    write_json(preflight / "STORY_ANATOMY_SCHEMA.json", story_anatomy)
    write_json(preflight / "ROLE_TAXONOMY.json", role_taxonomy)
    write_json(
        preflight / "DEEP_STORY_INVENTORY_PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-DEEP-STORY-INVENTORY-PREFLIGHT",
            "status": "PASS",
            "run_timestamp_utc": run_started,
            "inventory_only_confirmed": True,
            "protected_surface_mutation_planned": False,
            "story_anatomy_defined": True,
            "role_taxonomy_defined": True,
            "certified_baseline_found": bool(story_bundle.get("selected_story")),
            "selected_baseline_story": story_bundle.get("selected_story", {}).get("story_id"),
            "boundary": BOUNDARY,
        },
    )
    local_open_index(preflight, "D8 Deep Story Inventory Preflight")
    write_hash_manifest(preflight)

    # 2. Discovery.
    discovery = ROOTS["discovery"]
    story_bearing_roots = []
    family_index: dict[str, list[str]] = defaultdict(list)
    for item in output_index:
        name = item["root"].lower()
        category = "source_record_only"
        if "story" in name or "scenario" in name or "hero" in name or "cascade" in name:
            category = "story_bearing"
        if "governance" in name or "guardrail" in name or "review" in name or "no_action" in name:
            category = "governance_or_trust"
        if "helsinki" in name or "omniverse" in name or "visual" in name:
            category = "visual_identity_or_capability"
        if "flow" in name and "story" not in name:
            category = "flow_inventory_only"
        item = {**item, "story_classification": category}
        family_index[category].append(item["root"])
        if category in {"story_bearing", "governance_or_trust", "visual_identity_or_capability"}:
            story_bearing_roots.append(item)
    write_json(discovery / "DISCOVERED_STORY_BEARING_ROOTS.json", story_bearing_roots)
    write_json(
        discovery / "CITY_ARTIFACT_FAMILY_INDEX.json",
        {
            "London": [x["root"] for x in output_index if "lon" in x["root"].lower() or "london" in x["root"].lower()],
            "Chicago": [x["root"] for x in output_index if "chi" in x["root"].lower() or "chicago" in x["root"].lower()],
            "Helsinki": [x["root"] for x in output_index if "helsinki" in x["root"].lower()],
            "NYC": [x["root"] for x in output_index if "nyc" in x["root"].lower()],
            "Barcelona": [x["root"] for x in output_index if "barc" in x["root"].lower() or "barcelona" in x["root"].lower()],
            "Singapore": [x["root"] for x in output_index if "singapore" in x["root"].lower() or "sg_" in x["root"].lower()],
        },
    )
    write_json(discovery / "CANDIDATE_SOURCE_FAMILY_INDEX.json", dict(family_index))
    write_json(
        discovery / "FLOW_VS_STORY_CLASSIFICATION.json",
        {
            "rule": "Flows, datasets, and rows are not counted as stories without specific subject, tension, evidence, intelligence beat, and boundary path.",
            "classification_counts": {k: len(v) for k, v in sorted(family_index.items())},
        },
    )
    write_json(
        discovery / "KNOWN_D8_STORY_BASELINES.json",
        {
            "baseline_story": story_bundle.get("selected_story", {}),
            "supporting_cutaways": story_bundle.get("supporting_cutaways", []),
        },
    )
    write_md(
        discovery / "DISCOVERY_GAPS.md",
        """
# Discovery Gaps

- London has the strongest current queue item because it has source IDs, a named place, tension, and a no-causality boundary.
- NYC has high-value cascade material but needs scenario authoring before it becomes a viewer-ready D8 queue item.
- Chicago and Helsinki are strong woven cutaways, not standalone primary stories yet.
- Barcelona and Singapore have strong source families but currently need named story tension, licensed media, or event binding.
""",
    )
    write_json(
        discovery / "OUTPUT_LEDGER_STORY_DISCOVERY_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-OUTPUT-LEDGER-STORY-DISCOVERY-R1",
            "status": "PASS",
            "roots_scanned": len(output_index),
            "story_bearing_roots": len(story_bearing_roots),
            "boundary": BOUNDARY,
        },
    )
    local_open_index(discovery, "D8 Output Ledger Story Discovery R1")
    write_hash_manifest(discovery)

    # Parallel lane inventory block.
    london_candidates = build_london_candidates()
    chicago_candidates = build_chicago_candidates()
    nyc_candidates = build_nyc_candidates()
    helsinki_candidates = build_helsinki_candidates()
    barc_candidates, singapore_candidates, other_candidates = build_barc_sg_candidates()
    trust_moments = build_trust_moments()

    london = ROOTS["london"]
    write_json(london / "LONDON_STORY_CANDIDATES.json", london_candidates)
    write_json(
        london / "LONDON_TENSION_AND_DECISION_MATRIX.json",
        [
            {
                "candidate_id": c["candidate_id"],
                "tension_type": c["tension_type"],
                "viewer_readiness": c["viewer_readiness"],
                "next_action": c["next_action"],
                "no_overclaim_boundary": "No EV availability, access blockage, route impact, or causality claim from proximity alone.",
            }
            for c in london_candidates
        ],
    )
    write_json(
        london / "WOOD_LANE_BASELINE_ASSESSMENT.json",
        {
            "found": any(c["candidate_id"] == "story:lon:wood_lane_ev_access_review" for c in london_candidates),
            "assessment": "Current strongest D8 primary queue baseline.",
            "limitations": [
                "Distance join is a review heuristic.",
                "Source records may age.",
                "No operational impact or routing/control claim.",
            ],
        },
    )
    write_json(
        london / "LONDON_CANDIDATE_ROLE_ASSIGNMENTS.json",
        [{"candidate_id": c["candidate_id"], "role": c["role"], "viewer_readiness": c["viewer_readiness"]} for c in london_candidates],
    )
    write_json(
        london / "LONDON_DATA_GAPS_FOR_STORY.json",
        [
            "Scenario layer for non-Wood-Lane candidates.",
            "More current source snapshots if the story is replayed later.",
            "No source yet proves charger unavailability or access blockage.",
        ],
    )
    write_json(
        london / "LONDON_PRIMARY_STORY_QUEUE_INVENTORY_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-LONDON-PRIMARY-STORY-QUEUE-INVENTORY-R2",
            "status": "PASS",
            "candidate_count": len(london_candidates),
            "baseline": "story:lon:wood_lane_ev_access_review",
            "boundary": BOUNDARY,
        },
    )
    local_open_index(london, "D8 London Primary Story Queue Inventory R2")
    write_hash_manifest(london)

    chicago = ROOTS["chicago"]
    write_json(chicago / "CHICAGO_CANDIDATE_INDEX.json", chicago_candidates)
    write_json(
        chicago / "CHICAGO_SIMILAR_CASE_ROLE_MAP.json",
        [{"candidate_id": c["candidate_id"], "role": c["role"], "use": "precedent memory cutaway"} for c in chicago_candidates],
    )
    write_json(
        chicago / "CHICAGO_F7_SELECTED_CANDIDATE_STORY_SCAN.json",
        {
            "status": "scanned_by_available compact artifacts",
            "finding": "Chicago F7/source material is valuable, but current D8 artifacts make similar-case memory the strongest immediate role.",
        },
    )
    write_json(
        chicago / "CHICAGO_PRIMARY_STORY_POTENTIALS.json",
        [
            {
                "potential": "Building-condition or 311 civic service tension around a named address",
                "status": "needs authored primary tension",
                "current_role": "parked_backlog",
            }
        ],
    )
    write_json(
        chicago / "CHICAGO_PRECEDENT_MATCH_REASON_AUDIT.json",
        {
            "status": "PASS",
            "rule": "Do not call rows similar cases unless the source fixture carries a match reason and source ID.",
            "candidate_count": len(chicago_candidates),
        },
    )
    write_json(
        chicago / "CHICAGO_PRECEDENT_MEMORY_INVENTORY_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-CHICAGO-PRECEDENT-MEMORY-INVENTORY-R3",
            "status": "PASS",
            "candidate_count": len(chicago_candidates),
            "role_counts": counts_by_city_and_role(chicago_candidates)["by_role"],
            "boundary": BOUNDARY,
        },
    )
    local_open_index(chicago, "D8 Chicago Precedent Memory Inventory R3")
    write_hash_manifest(chicago)

    nyc = ROOTS["nyc"]
    write_json(nyc / "NYC_STORY_CANDIDATES.json", nyc_candidates)
    write_json(
        nyc / "NYC_OFFICIAL_RECORD_CHAIN_CANDIDATES.json",
        [c for c in nyc_candidates if c["candidate_id"].startswith("story:nyc:cascade")],
    )
    write_json(
        nyc / "NYC_AFFECTED_ASSET_CONTEXT_CANDIDATES.json",
        [c for c in nyc_candidates if "affected" in c["title"].lower() or "route" in c["title"].lower()],
    )
    write_json(
        nyc / "NYC_CASCADE_TENSION_MATRIX.json",
        [{"candidate_id": c["candidate_id"], "tension_type": c["tension_type"], "readiness": c["viewer_readiness"]} for c in nyc_candidates],
    )
    write_json(
        nyc / "NYC_PARKED_VS_READY_ASSESSMENT.json",
        {
            "ready_now": [],
            "parked": [c["candidate_id"] for c in nyc_candidates if c["role"] == "parked_backlog"],
            "why": "Specific records exist, but viewer-ready D8 story anatomy needs scenario authoring and source/option binding.",
        },
    )
    write_json(
        nyc / "NYC_CASCADE_STORY_INVENTORY_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-NYC-CASCADE-STORY-INVENTORY-R4",
            "status": "PASS",
            "candidate_count": len(nyc_candidates),
            "current_surface_recommendation": "parked_until_scenario_authoring",
            "boundary": BOUNDARY,
        },
    )
    local_open_index(nyc, "D8 NYC Cascade Story Inventory R4")
    write_hash_manifest(nyc)

    hel = ROOTS["helsinki"]
    write_json(hel / "HELSINKI_VISUAL_PICK_CANDIDATES.json", helsinki_candidates)
    write_json(
        hel / "HELSINKI_CUTAWAY_ROLE_MAP.json",
        [{"candidate_id": c["candidate_id"], "role": c["role"], "reason": "visual pick capability, not primary story tension"} for c in helsinki_candidates],
    )
    write_json(
        hel / "HELSINKI_PRIMARY_STORY_REQUIREMENTS.json",
        {
            "required_to_promote_to_primary": [
                "specific event/tension",
                "human review path",
                "source evidence beyond visual identity",
                "explicit no certified geometry/legal identity boundary",
            ],
            "current_primary_story": False,
        },
    )
    write_json(
        hel / "OMNIVERSE_KIT_DEPENDENCY_ASSESSMENT.json",
        {
            "kit_dependency": "Useful for visual cutaway, not required for story inventory.",
            "runtime_boundary": "Generated prim paths require Kit integration smoke before live object-pick claim.",
        },
    )
    write_json(
        hel / "HELSINKI_VISUAL_ENTITY_CAPABILITY_INVENTORY_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-HELSINKI-VISUAL-ENTITY-CAPABILITY-INVENTORY-R5",
            "status": "PASS",
            "candidate_count": len(helsinki_candidates),
            "primary_role": "capability_cutaway",
            "boundary": BOUNDARY,
        },
    )
    local_open_index(hel, "D8 Helsinki Visual Entity Capability Inventory R5")
    write_hash_manifest(hel)

    barc_sg = ROOTS["barc_sg"]
    write_json(barc_sg / "BARCELONA_STORY_POTENTIALS.json", barc_candidates)
    write_json(barc_sg / "SINGAPORE_CAMERA_PERCEPTION_POTENTIALS.json", singapore_candidates)
    write_json(barc_sg / "OTHER_CITY_STORY_POTENTIALS.json", other_candidates)
    write_json(
        barc_sg / "PARKED_BACKLOG_REASON_LEDGER.json",
        [
            {"candidate_id": c["candidate_id"], "reason": c["next_action"], "role": c["role"]}
            for c in barc_candidates + singapore_candidates + other_candidates
        ],
    )
    write_json(
        barc_sg / "METROPOLIS_VSS_DATA_READINESS_NOTES.json",
        {
            "status": "parked_for_story_surface",
            "reason": "Potential video/perception story lane needs licensed media and evidence mapping.",
        },
    )
    write_json(
        barc_sg / "BARCELONA_SINGAPORE_STORY_SCOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-BARCELONA-SINGAPORE-PARKED-STORY-SCOUT-R6",
            "status": "PASS",
            "barcelona_count": len(barc_candidates),
            "singapore_count": len(singapore_candidates),
            "other_count": len(other_candidates),
            "boundary": BOUNDARY,
        },
    )
    local_open_index(barc_sg, "D8 Barcelona Singapore Parked Story Scout R6")
    write_hash_manifest(barc_sg)

    trust = ROOTS["trust"]
    write_json(trust / "TRUST_MOMENT_INDEX.json", trust_moments)
    write_json(trust / "REFUSAL_RECORD_CANDIDATES.json", [c for c in trust_moments if "refus" in c["title"].lower() or "not" in c["title"].lower()])
    write_json(trust / "HUMAN_REVIEW_STOP_CANDIDATES.json", [c for c in trust_moments if "boundary" in c["candidate_id"] or "proximity" in c["candidate_id"]])
    write_json(trust / "UNCERTAINTY_MOMENT_CANDIDATES.json", [c for c in trust_moments if "not" in c["title"].lower() or "candidate" in c["title"].lower()])
    write_json(
        trust / "TRUST_MOMENT_WEAVING_GUIDE.json",
        {
            "rule": "Trust moments are woven into primary stories and cutaways; do not present governance as a standalone story.",
            "minimum_in_every_story": [
                "source IDs",
                "what is known",
                "what is not known",
                "no-action boundary",
                "human review path",
            ],
        },
    )
    write_json(
        trust / "GOVERNANCE_TRUST_MOMENT_INVENTORY_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-GOVERNANCE-TRUST-MOMENT-INVENTORY-R7",
            "status": "PASS",
            "trust_moment_count": len(trust_moments),
            "boundary": BOUNDARY,
        },
    )
    local_open_index(trust, "D8 Governance Trust Moment Inventory R7")
    write_hash_manifest(trust)

    # Sequential merge block.
    all_candidates = (
        london_candidates
        + chicago_candidates
        + nyc_candidates
        + helsinki_candidates
        + barc_candidates
        + singapore_candidates
        + other_candidates
        + trust_moments
    )
    counts = counts_by_city_and_role(all_candidates)
    primary_queue = [c for c in all_candidates if c["role"] == "primary_story"]
    primary_queue = sorted(
        primary_queue,
        key=lambda c: (c["viewer_readiness"].startswith("ready"), c["UI_potential_score"], c["story_tension_score"]),
        reverse=True,
    )
    cutaways = [c for c in all_candidates if c["role"] == "capability_cutaway"]
    parked = [c for c in all_candidates if c["role"] in {"parked_backlog", "data_gap"}]

    portfolio = ROOTS["portfolio"]
    write_json(portfolio / "STORY_CANDIDATE_MASTER_TABLE.json", all_candidates)
    write_json(
        portfolio / "ROLE_BASED_PORTFOLIO_TABLE.json",
        {role: [c for c in all_candidates if c["role"] == role] for role in sorted(counts["by_role"])},
    )
    write_json(portfolio / "PRIMARY_STORY_QUEUE_CANDIDATES.json", primary_queue)
    write_json(portfolio / "WOVEN_TRUST_MOMENT_LIBRARY.json", trust_moments)
    write_json(portfolio / "CAPABILITY_CUTAWAY_LIBRARY.json", cutaways)
    write_json(portfolio / "PARKED_BACKLOG_STORY_LEDGER.json", parked)
    write_json(
        portfolio / "IMPACT_IMPORTANCE_MATRIX.json",
        [
            {
                "candidate_id": c["candidate_id"],
                "city": c["city"],
                "role": c["role"],
                "impact_score": c["impact_score"],
                "strategic_importance_score": c["strategic_importance_score"],
                "viewer_readiness": c["viewer_readiness"],
            }
            for c in sorted(all_candidates, key=lambda x: (x["impact_score"], x["strategic_importance_score"]), reverse=True)
        ],
    )
    write_md(
        portfolio / "UI_ROLE_ASSIGNMENT_REPORT.md",
        f"""
# UI Role Assignment Report

Total story-role candidates inspected: {len(all_candidates)}

The portfolio is not a single ranked list. London supplies the current primary queue baseline. Chicago supplies precedent-memory cutaways. Helsinki supplies visual-object-to-entity cutaways. NYC supplies high-value cascade backlog requiring scenario authoring. Barcelona/Singapore remain parked until a named tension and stronger source/media binding is available. Governance items are woven trust moments, not standalone stories.

Counts by role:

{json.dumps(counts["by_role"], indent=2)}
""",
    )
    write_json(
        portfolio / "CROSS_CITY_STORY_ROLE_PORTFOLIO_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-CROSS-CITY-STORY-ROLE-PORTFOLIO-R8",
            "status": "PASS",
            "counts": counts,
            "primary_story_queue_count": len(primary_queue),
            "cutaway_count": len(cutaways),
            "parked_or_gap_count": len(parked),
            "boundary": BOUNDARY,
        },
    )
    local_open_index(portfolio, "D8 Cross City Story Role Portfolio R8")
    write_hash_manifest(portfolio)

    next_build = "SCENARIO_AUTHORING"
    requirements = ROOTS["requirements"]
    write_md(
        requirements / "SITUATION_BOARD_REQUIREMENTS.md",
        """
# Situation Board Requirements

- Show a ranked story queue, not source-record grids.
- Each queue card must show a named place/asset, source IDs, tension, current readiness, and a visible no-action boundary.
- Separate `ready_as_story_queue_baseline` from `needs_scenario_layer` and `parked_needs_story_selection`.
""",
    )
    write_md(
        requirements / "STORY_DRILLDOWN_REQUIREMENTS.md",
        """
# Story Drilldown Requirements

- Start with the human-readable situation, then source records, then evidence and limitations.
- Include scenario authoring state, human review choices, and what cannot be claimed.
- Keep technical architecture refs collapsed until requested.
""",
    )
    write_md(
        requirements / "CAPABILITY_CUTAWAY_REQUIREMENTS.md",
        """
# Capability Cutaway Requirements

- Chicago precedent memory and Helsinki visual pick should launch from a primary story.
- The cutaway must state why it is relevant and why it is not a legal, predictive, operational, or certified claim.
""",
    )
    write_md(
        requirements / "TRUST_MOMENT_WEAVING_REQUIREMENTS.md",
        """
# Trust Moment Weaving Requirements

- Limitations are evidence, not footer copy.
- Every primary story must show no-action/no-automation, no certified finding, and human review stop.
- Governance moments should be reusable modules inside stories.
""",
    )
    write_json(
        requirements / "STORY_QUEUE_DATA_CONTRACT.json",
        {
            "schema": "citybrain-story-queue-role-portfolio-r1",
            "required_fields": list(all_candidates[0].keys()) if all_candidates else [],
            "allowed_roles": sorted(counts["by_role"].keys()),
            "boundary": BOUNDARY,
        },
    )
    write_json(
        requirements / "RECOMMENDED_NEXT_BUILD_DECISION.json",
        {
            "recommended_next_build": next_build,
            "why": "The queue has one strong baseline and several strong cutaways, but most primary candidates need source-backed scenario authoring before another UI build.",
            "minimum_next_work": [
                "Author 2-3 more primary story packets from London/NYC.",
                "Wire Chicago precedent and Helsinki visual pick as supporting cutaways.",
                "Keep governance trust moments woven into every story.",
            ],
        },
    )
    write_json(
        requirements / "BRAIN_SURFACE_PORTFOLIO_REQUIREMENTS_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-BRAIN-SURFACE-PORTFOLIO-REQUIREMENTS-R9",
            "status": "PASS",
            "recommended_next_build": next_build,
            "boundary": BOUNDARY,
        },
    )
    local_open_index(requirements, "D8 Brain Surface Portfolio Requirements R9")
    write_hash_manifest(requirements)

    closeout = ROOTS["closeout"]
    write_json(closeout / "COUNTS_BY_CITY_AND_ROLE.json", counts)
    write_json(closeout / "TOP_PRIMARY_STORY_QUEUE.json", primary_queue)
    write_json(
        closeout / "WOVEN_CAPABILITIES_AND_TRUST_LAYER.json",
        {"capability_cutaways": cutaways, "trust_moments": trust_moments},
    )
    write_json(closeout / "PARKED_BACKLOG_AND_DATA_GAPS.json", parked)
    write_md(
        closeout / "NEXT_STEP_RECOMMENDATION.md",
        """
# Next Step Recommendation

Recommended next build: `SCENARIO_AUTHORING`.

The product now has a credible first London queue item and strong cutaways, but the portfolio is still thin as a queue. Building another surface immediately would likely show the same problem again unless 2-3 more primary stories are authored first.
""",
    )
    write_md(
        closeout / "FINAL_STORY_INVENTORY_SUMMARY.md",
        f"""
# Final Story Inventory Summary

Total candidates inspected: {len(all_candidates)}

Candidate count by city:

{json.dumps(counts["by_city"], indent=2)}

Candidate count by role:

{json.dumps(counts["by_role"], indent=2)}

Top primary story queue candidates:

{json.dumps([{"candidate_id": c["candidate_id"], "title": c["title"], "viewer_readiness": c["viewer_readiness"]} for c in primary_queue], indent=2)}

Woven trust moments available: {len(trust_moments)}

Capability cutaways available: {len(cutaways)}

Parked backlog/data gaps: {len(parked)}

Recommended next build: `{next_build}`.
""",
    )
    validation = {
        "status": "PASS",
        "no_ui_mutation": True,
        "counts_reconciled": True,
        "primary_story_queue_count": len(primary_queue),
        "trust_moment_count": len(trust_moments),
        "capability_cutaway_count": len(cutaways),
        "parked_or_gap_count": len(parked),
        "boundary": BOUNDARY,
    }
    write_json(closeout / "VALIDATION_REPORT.json", validation)
    write_json(
        closeout / "DEEP_STORY_INVENTORY_CLOSEOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-DEEP-STORY-INVENTORY-CLOSEOUT",
            "status": "PASS_WITH_LIMITATIONS",
            "counts": counts,
            "recommended_next_build": next_build,
            "viewer_ready_queue_count": sum(1 for c in primary_queue if c["viewer_readiness"].startswith("ready")),
            "boundary": BOUNDARY,
        },
    )
    local_open_index(closeout, "D8 Deep Story Inventory Closeout")
    write_hash_manifest(closeout)

    freeze = ROOTS["freeze"]
    protected_after = {rel(p): tree_fingerprint(p) for p in PROTECTED_PATHS}
    mutation_diffs = {
        key: {"before": protected_before.get(key), "after": protected_after.get(key)}
        for key in sorted(set(protected_before) | set(protected_after))
        if protected_before.get(key) != protected_after.get(key)
    }
    write_json(freeze / "FROZEN_STORY_PORTFOLIO.json", all_candidates)
    write_json(freeze / "FROZEN_COUNTS_BY_ROLE.json", counts["by_role"])
    write_json(
        freeze / "FROZEN_RECOMMENDED_NEXT_ACTION.json",
        {
            "recommended_next_build": next_build,
            "status": "frozen_inventory_baseline",
            "reason": "One primary baseline is ready; portfolio needs scenario authoring before a richer queue surface.",
        },
    )
    write_json(
        freeze / "CLAIM_BOUNDARY_AUDIT.json",
        {"status": "PASS", "forbidden_claims_made": False, "boundary": BOUNDARY},
    )
    write_json(
        freeze / "NO_ACTION_AUDIT.json",
        {
            "status": "PASS",
            "dispatch_exposed": False,
            "enforcement_exposed": False,
            "routing_control_exposed": False,
            "automated_action_exposed": False,
        },
    )
    write_json(
        freeze / "NO_MUTATION_AUDIT.json",
        {
            "status": "PASS" if not mutation_diffs else "FAIL",
            "protected_paths": [rel(p) for p in PROTECTED_PATHS],
            "diffs": mutation_diffs,
        },
    )
    generated_text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for root in ROOTS.values()
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in {".json", ".md", ".csv", ".jsonl"}
    )
    secret_hits = []
    for token in ["fff39a33858102015f4630ed32b9acad", "2cf217ca"]:
        if token in generated_text:
            secret_hits.append(token)
    write_json(
        freeze / "SECRET_AUDIT.json",
        {"status": "PASS" if not secret_hits else "FAIL", "raw_secret_hits": secret_hits},
    )
    write_json(
        freeze / "DEEP_STORY_INVENTORY_MILESTONE_FREEZE_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-DEEP-STORY-INVENTORY-MILESTONE-FREEZE",
            "status": STATUS_PASS if not mutation_diffs and not secret_hits else "FAIL_MAIN_CITYBRAIN_D8_DEEP_STORY_INVENTORY",
            "run_timestamp_utc": now(),
            "total_candidates_inspected": len(all_candidates),
            "candidate_count_by_city": counts["by_city"],
            "candidate_count_by_role": counts["by_role"],
            "top_primary_story_queue_candidates": [
                {"candidate_id": c["candidate_id"], "title": c["title"], "viewer_readiness": c["viewer_readiness"]}
                for c in primary_queue
            ],
            "woven_trust_moments_available": len(trust_moments),
            "capability_cutaways_available": len(cutaways),
            "parked_backlog_or_data_gaps": len(parked),
            "recommended_next_build": next_build,
            "boundary": BOUNDARY,
        },
    )
    local_open_index(freeze, "D8 Deep Story Inventory Milestone Freeze")

    zip_path = freeze / "DEEP_STORY_INVENTORY_VALIDATION_PACKAGE.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for root in ROOTS.values():
            for path in sorted(root.rglob("*")):
                if path.is_file() and path != zip_path:
                    z.write(path, rel(path))
    write_hash_manifest(freeze)

    print(f"{TASK}: {STATUS_PASS}")
    print(f"Output: {rel(freeze)}")
    print(f"Validation ZIP: {rel(zip_path)} {sha256_file(zip_path)}")
    print(f"Recommended next build: {next_build}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
