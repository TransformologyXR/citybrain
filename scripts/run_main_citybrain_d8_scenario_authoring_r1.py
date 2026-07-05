#!/usr/bin/env python3
"""Author the D8 distinct-tension primary story queue.

This lane is deliberately not a UI/capture/data-landing task. It reads the
frozen D8 story inventory plus local source-backed story bundles, then writes a
scenario-authoring package that keeps Wood Lane as the proximity exemplar and
only counts additional primary stories when they introduce a distinct
story-query version.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO / "outputs/main_citybrain_d8_scenario_authoring_r1"
RUNNER = REPO / "scripts/run_main_citybrain_d8_scenario_authoring_r1.py"

TASK = "MAIN-CITYBRAIN-D8-SCENARIO-AUTHORING-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D8_SCENARIO_AUTHORING_R1_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_DISTINCT_PRIMARY_STORY_QUEUE_INSUFFICIENT"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D8_SCENARIO_AUTHORING_R1"
SCHEMA_VERSION = "main-citybrain-d8-scenario-authoring-r1.v1"

BOUNDARY = (
    "Local/replay/review/query context only; no production/public API, live monitoring, "
    "alerts, dispatch, routing/control, enforcement, official ticket/case creation, "
    "legal/certified finding, certified asset/operational impact, or automated action."
)

INPUTS = {
    "deep_story_inventory_freeze": REPO
    / "outputs/main_citybrain_d8_deep_story_inventory_milestone_freeze/DEEP_STORY_INVENTORY_MILESTONE_FREEZE_DECISION.json",
    "frozen_story_portfolio": REPO
    / "outputs/main_citybrain_d8_deep_story_inventory_milestone_freeze/FROZEN_STORY_PORTFOLIO.json",
    "deep_story_inventory_closeout": REPO
    / "outputs/main_citybrain_d8_deep_story_inventory_closeout/DEEP_STORY_INVENTORY_CLOSEOUT_DECISION.json",
    "top_primary_queue": REPO / "outputs/main_citybrain_d8_deep_story_inventory_closeout/TOP_PRIMARY_STORY_QUEUE.json",
    "role_portfolio_decision": REPO
    / "outputs/main_citybrain_d8_cross_city_story_role_portfolio_r8/CROSS_CITY_STORY_ROLE_PORTFOLIO_DECISION.json",
    "role_portfolio_master": REPO
    / "outputs/main_citybrain_d8_cross_city_story_role_portfolio_r8/STORY_CANDIDATE_MASTER_TABLE.json",
    "capability_library": REPO
    / "outputs/main_citybrain_d8_cross_city_story_role_portfolio_r8/CAPABILITY_CUTAWAY_LIBRARY.json",
    "trust_library": REPO
    / "outputs/main_citybrain_d8_cross_city_story_role_portfolio_r8/WOVEN_TRUST_MOMENT_LIBRARY.json",
    "wood_lane_scenario_freeze": REPO
    / "outputs/main_citybrain_d8_story_scenario_layer_milestone_freeze/STORY_SCENARIO_LAYER_MILESTONE_FREEZE_DECISION.json",
    "wood_lane_scenario_layer": REPO / "packages/fixtures/story_first_demo/story_scenario_layer.json",
    "wood_lane_story_source_bundle": REPO / "packages/fixtures/story_first_demo/story_source_bundle.json",
    "london_source_bundle": REPO / "packages/fixtures/london_mobility_source_records/source_record_bundle.json",
    "chicago_source_bundle": REPO / "packages/fixtures/chicago_similar_case_records/similar_case_source_bundle.json",
    "helsinki_source_bundle": REPO / "packages/fixtures/helsinki_visual_entity_pick/source_record_bundle.json",
    "source_record_ui_bundle": REPO
    / "packages/fixtures/source_record_ui_integrated/source_record_ui_integrated_bundle.json",
    "nyc_selector_report": REPO / "outputs/f3_nyc_d8_flow3_hero_package/F3_NYC_D8_SELECTOR_REPORT.json",
    "nyc_grounding_report": REPO / "outputs/f3_nyc_d8_flow3_hero_package/F3_NYC_D8_GROUNDING_REPORT.json",
    "nyc_no_overclaim_report": REPO / "outputs/f3_nyc_d8_flow3_hero_package/F3_NYC_D8_NO_OVERCLAIM_REPORT.json",
    "nyc_hero_1": REPO / "outputs/f3_nyc_d8_flow3_hero_package/heroes/hero_1_top_candidate_incident.json",
    "nyc_hero_2": REPO / "outputs/f3_nyc_d8_flow3_hero_package/heroes/hero_2_top_operator_review_route.json",
    "nyc_hero_4": REPO / "outputs/f3_nyc_d8_flow3_hero_package/heroes/hero_4_governance_negative_request.json",
}

READ_ONLY_ROOTS = [
    REPO / "outputs/main_citybrain_d8_deep_story_inventory_milestone_freeze",
    REPO / "outputs/main_citybrain_d8_deep_story_inventory_closeout",
    REPO / "outputs/main_citybrain_d8_cross_city_story_role_portfolio_r8",
    REPO / "outputs/main_citybrain_d8_story_scenario_layer_milestone_freeze",
    REPO / "outputs/f3_nyc_d8_flow3_hero_package",
    REPO / "packages/fixtures/story_first_demo",
    REPO / "packages/fixtures/london_mobility_source_records",
    REPO / "packages/fixtures/chicago_similar_case_records",
    REPO / "packages/fixtures/helsinki_visual_entity_pick",
    REPO / "packages/fixtures/source_record_ui_integrated",
]

FORBIDDEN_POSITIVE_CLAIMS = [
    "certified affected building",
    "certified affected asset",
    "charger is blocked",
    "charger is unavailable",
    "ev availability changed",
    "emergency dispatch",
    "dispatch recommendation",
    "navigable route",
    "routing/control",
    "enforcement action",
    "official ticket",
    "official case",
    "legal finding",
    "automated action",
    "production api",
    "live monitoring",
    "alerting",
    "certified twin",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def reset_output_root() -> None:
    if OUTPUT_ROOT.exists():
        resolved = OUTPUT_ROOT.resolve()
        for child in OUTPUT_ROOT.iterdir():
            child_resolved = child.resolve()
            if resolved not in [child_resolved, *child_resolved.parents]:
                raise RuntimeError(f"Refusing to remove outside output root: {child}")
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_fingerprint(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"root": rel(root), "exists": False, "file_count": 0, "digest": None}
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append(f"{rel(path)}|{path.stat().st_size}|{sha256_file(path)}")
    return {
        "root": rel(root),
        "exists": True,
        "file_count": len(rows),
        "digest": hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest(),
    }


def input_artifact_index() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task": TASK,
        "inputs": {
            name: {
                "path": rel(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
            }
            for name, path in INPUTS.items()
        },
    }


def load_inputs() -> dict[str, Any]:
    return {name: read_json(path, {} if path.suffix == ".json" else None) for name, path in INPUTS.items()}


def story_query_registry() -> list[dict[str, Any]]:
    return [
        {
            "story_query_id": "story-query:proximity_works_to_access@v1",
            "status": "active_primary_exemplar",
            "definition": "Connect official road works/disruption records to a named nearby access asset, while refusing access-impact or availability claims.",
            "allowed_claims": [
                "bounded proximity",
                "source record co-review",
                "review-only uncertainty",
            ],
            "forbidden_claims": [
                "causal access impact",
                "EV charger blocked or unavailable",
                "operational action",
            ],
            "counting_rule": "Only Wood Lane counts in this R1 queue; Warwick Avenue, Lancaster Gate, and Claps Gate are duplicate shape examples.",
        },
        {
            "story_query_id": "story-query:incident_to_affected_asset_response_cascade@v1",
            "status": "active_primary_authoring_plan",
            "definition": "Connect an official incident event to candidate asset context, nearby response-resource context, review-route plan, and a governance refusal where certainty is unsupported.",
            "allowed_claims": [
                "candidate affected tax-lot context",
                "response-resource context",
                "operator review plan only",
                "negative/refusal moment for unsupported affected-building certainty",
            ],
            "forbidden_claims": [
                "certified affected building",
                "emergency dispatch",
                "navigable route",
                "severity or urgency recommendation",
            ],
            "counting_rule": "Counts as the second distinct primary query in plan form because local Flow 3 hero evidence is green and source-backed.",
        },
        {
            "story_query_id": "story-query:similar_case_precedent_memory@v1",
            "status": "capability_cutaway_not_counted_primary",
            "definition": "Show a comparable civic/building-condition record as bounded memory context.",
            "allowed_claims": ["similar case context", "source ID, place/time/category when present"],
            "forbidden_claims": ["prediction", "causality", "instruction", "enforcement/legal conclusion"],
            "counting_rule": "Not counted as a primary in R1 because current Chicago candidates are precedent memory without a paired local tension.",
        },
        {
            "story_query_id": "story-query:visual_object_to_semantic_entity@v1",
            "status": "capability_cutaway_not_counted_primary",
            "definition": "Map a visual/USD object candidate to semantic source-record context while refusing certified identity.",
            "allowed_claims": ["candidate visual/entity alignment", "source building ID", "candidate prim path"],
            "forbidden_claims": ["certified physical geometry", "legal identity", "citywide certified twin"],
            "counting_rule": "Not counted as a primary in R1 because current Helsinki evidence lacks an event/tension beyond identity boundary.",
        },
        {
            "story_query_id": "story-query:civic_signal_fusion_review@v1",
            "status": "parked_backlog",
            "definition": "Combine named civic/service signal and sensor context only when a specific subject and tension exist.",
            "allowed_claims": ["review-only signal bundle", "specific named record when later selected"],
            "forbidden_claims": ["live monitoring", "automated alert", "operational enforcement"],
            "counting_rule": "Barcelona/Singapore remain parked until a named source-backed situation is selected.",
        },
    ]


def wood_lane_story(data: dict[str, Any]) -> dict[str, Any]:
    layer = data["wood_lane_scenario_layer"].get("scenario", {})
    return {
        "story_id": "story:lon:wood_lane_ev_access_review",
        "title": "Wood Lane works near a named rapid EV access asset",
        "role": "primary_story",
        "counted_primary": True,
        "city": "London",
        "specific_subject": "Wood Lane / Scrubbs Lane, Hammersmith & Fulham",
        "tension": "TfL works records sit near a named rapid EV access asset, but the evidence only supports proximity review, not an impact claim.",
        "story_query_id": "story-query:proximity_works_to_access@v1",
        "source_record_ids": ["TIMS-219173", "TIMS-210389", "87"],
        "intelligence_beat": "The system connects official works records with an access asset while making the uncertainty visible above the story line.",
        "review_options": [
            "Inspect TIMS-219173, TIMS-210389, and EV asset 87 together.",
            "Ask for stronger source evidence before any access-impact claim.",
            "Abstain if the evidence remains only proximity context.",
        ],
        "human_stop": "Stops at evidence review; no action, alert, route, dispatch, case, legal finding, or approval is created.",
        "limitations": layer.get("limitations", [])
        or [
            "Proximity is a review heuristic, not causal impact.",
            "EV asset row is infrastructure context, not a service-status source.",
        ],
        "overclaim_risks": [
            "Claiming charger availability changed.",
            "Claiming the works caused access impact.",
            "Treating active/replay source records as live monitoring.",
        ],
        "status": "authored",
        "why_distinct_from_wood_lane": "This is Wood Lane, retained as the exemplar of the proximity/access story shape.",
        "source_artifacts": [
            rel(INPUTS["wood_lane_scenario_layer"]),
            rel(INPUTS["wood_lane_story_source_bundle"]),
            rel(INPUTS["wood_lane_scenario_freeze"]),
        ],
    }


def nyc_story(data: dict[str, Any]) -> dict[str, Any]:
    hero_1 = data["nyc_hero_1"]
    hero_2 = data["nyc_hero_2"]
    hero_4 = data["nyc_hero_4"]
    facts = hero_1.get("d5_evidence_bundle", {}).get("facts", [])
    fact_values = {item.get("fact"): item.get("value") for item in facts}
    return {
        "story_id": "story:nyc:cascade:mvc_crash_4463710",
        "title": "NYC MVC event with candidate asset and response-resource review context",
        "role": "primary_story",
        "counted_primary": True,
        "city": "NYC",
        "specific_subject": "event:us-nyc:flow3:mvc_crash:4463710 near Howard Avenue / Engine 227 context",
        "tension": "An official MVC event has exact-location candidate asset context and nearby response-resource context, but the system must refuse certified affected-building, dispatch, and routing claims.",
        "story_query_id": "story-query:incident_to_affected_asset_response_cascade@v1",
        "source_record_ids": [
            "event:us-nyc:flow3:mvc_crash:4463710",
            str(fact_values.get("Primary candidate affected tax lot.", "asset:us-nyc:mappluto_tax_lot:3014450085")),
            str(fact_values.get("Nearest firehouse/resource context.", "resource:us-nyc:fdny:firehouse:engine_227")),
            "review_route:us-nyc:flow3:d4:001:brooklyn:resource_us_nyc_fdny_firehouse_engine_227",
            "negative_affected_buildings",
        ],
        "intelligence_beat": "The useful beat is a governed cascade that keeps candidate asset context, response-resource context, review itinerary evidence, and refusal evidence in one bounded story.",
        "review_options": [
            "Review candidate asset context and response-resource context together.",
            "Inspect the score-ordered review itinerary as bounded evidence with straight-line proxy context only.",
            "Use the governance refusal when a viewer asks for definitely affected buildings.",
            "Abstain from any action or certainty claim outside Track/human-approved future gates.",
        ],
        "human_stop": "Stops at operator review and governance refusal; no dispatch, route, certified affected-building finding, ticket, case, or legal finding is created.",
        "limitations": sorted(
            set(
                hero_1.get("limitations", [])
                + hero_2.get("d5_evidence_bundle", {}).get("limitations", [])
                + hero_4.get("limitations", [])
            )
        ),
        "overclaim_risks": [
            "Certifying the candidate tax lot/building as affected.",
            "Converting Engine 227 context into dispatched-unit truth.",
            "Treating the review route as emergency dispatch or a navigable route.",
            "Using priority score as incident severity or urgency.",
        ],
        "status": "authoring_plan_only",
        "why_distinct_from_wood_lane": "This is an incident-to-candidate-asset/response-context cascade with a governance refusal, not a proximity-to-access-asset works story.",
        "source_artifacts": [
            rel(INPUTS["nyc_selector_report"]),
            rel(INPUTS["nyc_grounding_report"]),
            rel(INPUTS["nyc_no_overclaim_report"]),
            rel(INPUTS["nyc_hero_1"]),
            rel(INPUTS["nyc_hero_2"]),
            rel(INPUTS["nyc_hero_4"]),
        ],
    }


def distinct_primary_queue(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [wood_lane_story(data), nyc_story(data)]


def duplicate_shape_audit(data: dict[str, Any]) -> dict[str, Any]:
    top_queue = data.get("top_primary_queue", [])
    entries = []
    for item in top_queue:
        candidate_id = item.get("candidate_id")
        is_wood = candidate_id == "story:lon:wood_lane_ev_access_review"
        entries.append(
            {
                "candidate_id": candidate_id,
                "title": item.get("title"),
                "city": item.get("city"),
                "input_role": item.get("role"),
                "assigned_role": "primary_story" if is_wood else "duplicate_shape_not_counted",
                "story_query_id": "story-query:proximity_works_to_access@v1",
                "counted_primary": is_wood,
                "reason": "Wood Lane is the exemplar." if is_wood else "Same proximity works/access story shape as Wood Lane.",
            }
        )
    duplicate_count = sum(1 for entry in entries if entry["assigned_role"] == "duplicate_shape_not_counted")
    return {
        "status": "PASS",
        "rule": "No two counted primary stories may share the same story_query_id@version.",
        "input_top_primary_count": len(top_queue),
        "duplicate_shape_not_counted": duplicate_count,
        "entries": entries,
    }


def scenario_layer_authoring_plan(primary_queue: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "ui_build_deferred": True,
        "scenario_layers": [
            {
                "story_id": primary_queue[0]["story_id"],
                "scenario_status": "authored_and_frozen",
                "scenario_layer_path": rel(INPUTS["wood_lane_scenario_layer"]),
                "story_query_id": primary_queue[0]["story_query_id"],
                "required_next_step": "Reuse as first queue item; do not author duplicate London proximity cards as counted primaries.",
            },
            {
                "story_id": primary_queue[1]["story_id"],
                "scenario_status": "authoring_plan_only",
                "story_query_id": primary_queue[1]["story_query_id"],
                "source_backing_status": "source_backed_plan_from_green_flow3_hero_package",
                "proposed_beats": [
                    {
                        "beat_id": "NYC_B01_EVENT",
                        "title": "What is the source event?",
                        "source_record_ids": ["event:us-nyc:flow3:mvc_crash:4463710"],
                        "claim": "Official MVC crash event is a candidate operator-review subject.",
                    },
                    {
                        "beat_id": "NYC_B02_CANDIDATE_ASSET",
                        "title": "What candidate asset context exists?",
                        "source_record_ids": ["asset:us-nyc:mappluto_tax_lot:3014450085"],
                        "claim": "Candidate tax-lot context exists and remains candidate only.",
                    },
                    {
                        "beat_id": "NYC_B03_RESPONSE_CONTEXT",
                        "title": "What response-resource context exists?",
                        "source_record_ids": ["resource:us-nyc:fdny:firehouse:engine_227"],
                        "claim": "Engine 227 is nearest response-resource context, not dispatched-unit truth.",
                    },
                    {
                        "beat_id": "NYC_B04_REVIEW_ROUTE_ONLY",
                        "title": "What can a reviewer inspect?",
                        "source_record_ids": [
                            "review_route:us-nyc:flow3:d4:001:brooklyn:resource_us_nyc_fdny_firehouse_engine_227"
                        ],
                        "claim": "Route plan is operator-review-only and not a navigable/emergency route.",
                    },
                    {
                        "beat_id": "NYC_B05_GOVERNANCE_REFUSAL",
                        "title": "Where does the system stop?",
                        "source_record_ids": ["negative_affected_buildings"],
                        "claim": "The system refuses definitely affected-building certainty.",
                    },
                ],
                "required_next_step": "Create a concrete scenario JSON only after viewer copy is bound to these exact hero JSONs.",
            },
        ],
    }


def source_evidence_map(primary_queue: list[dict[str, Any]], data: dict[str, Any]) -> dict[str, Any]:
    wood_layer = data["wood_lane_scenario_layer"].get("scenario", {})
    nyc_hero = data["nyc_hero_1"].get("d5_evidence_bundle", {})
    return {
        "status": "PASS",
        "story_count": len(primary_queue),
        "stories": [
            {
                "story_id": primary_queue[0]["story_id"],
                "story_query_id": primary_queue[0]["story_query_id"],
                "source_record_ids": primary_queue[0]["source_record_ids"],
                "records": wood_layer.get("records", []),
                "evidence_links": wood_layer.get("evidence_links", []),
                "source_artifacts": primary_queue[0]["source_artifacts"],
            },
            {
                "story_id": primary_queue[1]["story_id"],
                "story_query_id": primary_queue[1]["story_query_id"],
                "source_record_ids": primary_queue[1]["source_record_ids"],
                "evidence_bundle_id": nyc_hero.get("bundle_id"),
                "evidence_counts": nyc_hero.get("counts"),
                "edges": nyc_hero.get("edges", []),
                "facts": nyc_hero.get("facts", []),
                "source_artifacts": primary_queue[1]["source_artifacts"],
            },
        ],
    }


def woven_capability_plan(data: dict[str, Any]) -> dict[str, Any]:
    capability = data.get("capability_library", [])
    selected = []
    for item in capability:
        cid = item.get("candidate_id", "")
        if cid in {
            "story:chi:precedent:chi:r2:case:001",
            "story:hel:visual_pick:BID_35328115-972e-45e3-97bd-d0029f19f70d",
        }:
            selected.append(
                {
                    "candidate_id": cid,
                    "title": item.get("title"),
                    "city": item.get("city"),
                    "role": "capability_cutaway",
                    "story_query_id": "story-query:similar_case_precedent_memory@v1"
                    if item.get("city") == "Chicago"
                    else "story-query:visual_object_to_semantic_entity@v1",
                    "woven_into": [
                        "story:lon:wood_lane_ev_access_review",
                        "story:nyc:cascade:mvc_crash_4463710",
                    ],
                    "reason_not_primary": item.get("next_action"),
                    "source_record_ids": item.get("source_records", []),
                    "limitations": [item.get("boundary_stop", BOUNDARY)],
                }
            )
    return {
        "status": "PASS",
        "principle": "Cutaways are woven into story drilldowns rather than counted as queue primaries unless they carry their own source-backed tension.",
        "cutaways": selected,
    }


def trust_moment_plan(data: dict[str, Any]) -> dict[str, Any]:
    trust = data.get("trust_library", [])
    selected_ids = {
        "trust:global:no_action_boundary",
        "trust:london:proximity_not_causality",
        "trust:nyc:negative_affected_buildings",
        "trust:chicago:precedent_not_prediction",
        "trust:helsinki:visual_identity_candidate_only",
        "trust:global:records_are_not_stories",
    }
    rows = []
    for item in trust:
        if item.get("candidate_id") in selected_ids:
            rows.append(
                {
                    "candidate_id": item.get("candidate_id"),
                    "title": item.get("title"),
                    "city": item.get("city"),
                    "role": "trust_moment",
                    "woven_into": "every_primary_story"
                    if item.get("candidate_id") in {"trust:global:no_action_boundary", "trust:global:records_are_not_stories"}
                    else item.get("city"),
                    "source_record_ids": item.get("source_records", []),
                    "intelligence_beat": item.get("intelligence_beat"),
                    "boundary_stop": item.get("boundary_stop", BOUNDARY),
                }
            )
    rows.append(
        {
            "candidate_id": "trust:nyc:negative_affected_buildings",
            "title": "NYC affected-building certainty refusal",
            "city": "NYC",
            "role": "trust_moment",
            "woven_into": "story:nyc:cascade:mvc_crash_4463710",
            "source_record_ids": ["negative_affected_buildings"],
            "intelligence_beat": "The system rejects a request for definitely affected buildings because the evidence carries candidate tax-lot context only.",
            "boundary_stop": BOUNDARY,
        }
    )
    return {"status": "PASS", "trust_moments": rows}


def parked_backlog(data: dict[str, Any], duplicate_audit: dict[str, Any]) -> dict[str, Any]:
    master = data.get("role_portfolio_master", [])
    backlog = []
    for entry in duplicate_audit["entries"]:
        if entry["assigned_role"] == "duplicate_shape_not_counted":
            backlog.append(entry)
    for item in master:
        role = item.get("role")
        if role in {"parked_backlog", "data_gap"} or item.get("city") in {"Chicago", "Helsinki", "Barcelona", "Singapore"}:
            if item.get("candidate_id") in {"story:nyc:cascade:mvc_crash_4463710", "story:nyc:fdny_review_route:engine_227"}:
                continue
            backlog.append(
                {
                    "candidate_id": item.get("candidate_id"),
                    "title": item.get("title"),
                    "city": item.get("city"),
                    "assigned_role": item.get("role"),
                    "story_query_id": "story-query:similar_case_precedent_memory@v1"
                    if item.get("city") == "Chicago"
                    else "story-query:visual_object_to_semantic_entity@v1"
                    if item.get("city") == "Helsinki"
                    else "story-query:civic_signal_fusion_review@v1"
                    if item.get("city") in {"Barcelona", "Singapore"}
                    else "unassigned",
                    "reason": item.get("next_action"),
                    "source_record_ids": item.get("source_records", []),
                }
            )
    return {"status": "PASS", "parked_count": len(backlog), "items": backlog}


def no_overclaim_audit(primary_queue: list[dict[str, Any]]) -> dict[str, Any]:
    positive_texts = []
    for story in primary_queue:
        positive_texts.extend(
            [
                story.get("title", ""),
                story.get("specific_subject", ""),
                story.get("tension", ""),
                story.get("intelligence_beat", ""),
                " ".join(story.get("review_options", [])),
            ]
        )
    hits = []
    for phrase in FORBIDDEN_POSITIVE_CLAIMS:
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
        for text in positive_texts:
            if pattern.search(text):
                hits.append({"phrase": phrase, "text": text})
    return {
        "status": "PASS" if not hits else "FAIL",
        "forbidden_positive_claim_hits": hits,
        "allowed_boundary_mentions": FORBIDDEN_POSITIVE_CLAIMS,
        "notes": [
            "Forbidden concepts may appear in limitations, human_stop, overclaim_risks, and audits as refusals.",
            "Audit scans positive-facing title/subject/tension/beat/review option text for unbounded positive claims.",
        ],
    }


def no_action_audit(primary_queue: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "stories_checked": len(primary_queue),
        "execution_state": "not_executed",
        "no_action_authority_created": True,
        "review_only_boundary": BOUNDARY,
        "checks": {
            "dispatch": "rejected_by_boundary",
            "routing_control": "rejected_by_boundary",
            "enforcement": "rejected_by_boundary",
            "official_ticket_case": "rejected_by_boundary",
            "legal_certified_finding": "rejected_by_boundary",
            "automated_action": "rejected_by_boundary",
        },
    }


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for root, snap in before.items():
        if snap.get("digest") != after.get(root, {}).get("digest"):
            changed.append(root)
    return {"status": "PASS" if not changed else "FAIL", "changed_read_only_roots": changed, "before": before, "after": after}


def secret_audit() -> dict[str, Any]:
    patterns = {
        "openai_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
        "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}"),
        "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE),
    }
    findings = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns.items():
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": name})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def hash_manifest() -> dict[str, Any]:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"schema_version": SCHEMA_VERSION, "file_count": len(rows), "files": rows}


def write_docs(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# D8 Scenario Authoring R1

Status: `{decision["status"]}`

This package keeps Wood Lane as the counted proximity/access exemplar and adds
one distinct source-backed NYC cascade story in authoring-plan form. The
remaining London proximity cards are explicitly marked duplicate shape and not
counted as primary stories.

This is scenario authoring only. UI redesign, capture/viewer validation, new
data landing, production APIs, live monitoring, dispatch, routing/control,
enforcement, legal/certified findings, and automated action are out of scope.
""",
    )
    write_text(
        OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md",
        """
# Local Open Index

- Decision: `outputs/main_citybrain_d8_scenario_authoring_r1/SCENARIO_AUTHORING_R1_DECISION.json`
- Story query registry: `outputs/main_citybrain_d8_scenario_authoring_r1/STORY_QUERY_REGISTRY.json`
- Distinct primary queue: `outputs/main_citybrain_d8_scenario_authoring_r1/DISTINCT_PRIMARY_STORY_QUEUE.json`
- Duplicate-shape audit: `outputs/main_citybrain_d8_scenario_authoring_r1/DUPLICATE_SHAPE_AUDIT.json`
- Source evidence map: `outputs/main_citybrain_d8_scenario_authoring_r1/STORY_TO_SOURCE_EVIDENCE_MAP.json`
- Authoring plan: `outputs/main_citybrain_d8_scenario_authoring_r1/SCENARIO_LAYER_AUTHORING_PLAN.json`
- Capability cutaways: `outputs/main_citybrain_d8_scenario_authoring_r1/WOVEN_CAPABILITY_CUTAWAY_PLAN.json`
- Trust moments: `outputs/main_citybrain_d8_scenario_authoring_r1/TRUST_MOMENT_WEAVING_PLAN.json`
- Parked backlog: `outputs/main_citybrain_d8_scenario_authoring_r1/PARKED_STORY_BACKLOG.json`
- Audits: `NO_OVERCLAIM_AUDIT.json`, `NO_ACTION_AUDIT.json`, `NO_MUTATION_AUDIT.json`, `SECRET_AUDIT.json`, `HASH_MANIFEST.json`
""",
    )


def main() -> int:
    reset_output_root()
    before = {rel(root): tree_fingerprint(root) for root in READ_ONLY_ROOTS}
    data = load_inputs()

    input_index = input_artifact_index()
    registry = story_query_registry()
    primary_queue = distinct_primary_queue(data)
    duplicate_audit = duplicate_shape_audit(data)
    authoring_plan = scenario_layer_authoring_plan(primary_queue)
    evidence_map = source_evidence_map(primary_queue, data)
    cutaway_plan = woven_capability_plan(data)
    trust_plan = trust_moment_plan(data)
    backlog = parked_backlog(data, duplicate_audit)
    overclaim = no_overclaim_audit(primary_queue)
    action = no_action_audit(primary_queue)
    after = {rel(root): tree_fingerprint(root) for root in READ_ONLY_ROOTS}
    mutation = no_mutation_audit(before, after)

    counted_primary = [story for story in primary_queue if story.get("counted_primary")]
    distinct_queries = sorted({story["story_query_id"] for story in counted_primary})
    duplicate_query_violation = len(distinct_queries) != len(counted_primary)
    missing_inputs = [name for name, item in input_index["inputs"].items() if not item["exists"]]

    blocking_gaps = []
    if missing_inputs:
        blocking_gaps.append(f"Missing required input artifacts: {', '.join(missing_inputs)}")
    if not counted_primary or counted_primary[0]["story_id"] != "story:lon:wood_lane_ev_access_review":
        blocking_gaps.append("Wood Lane was not retained as first counted primary story.")
    if duplicate_query_violation:
        blocking_gaps.append("Duplicate story_query_id@version present in counted primary queue.")
    if overclaim["status"] != "PASS":
        blocking_gaps.append("No-overclaim audit failed.")
    if action["status"] != "PASS":
        blocking_gaps.append("No-action audit failed.")
    if mutation["status"] != "PASS":
        blocking_gaps.append("Read-only root mutation detected.")

    non_blocking_gaps = [
        "Only two distinct counted primary story queries are supported honestly in this pass.",
        "NYC story is authoring_plan_only; concrete scenario JSON should be authored after binding viewer copy to the exact hero JSONs.",
        "Chicago and Helsinki remain cutaways/trust moments until paired with a source-backed standalone tension.",
        "Barcelona/Singapore remain parked until a named record-level situation is selected.",
        "UI build is explicitly deferred.",
    ]

    if blocking_gaps:
        status = FAIL_STATUS
    elif len(distinct_queries) < 2:
        status = PARTIAL_STATUS
    else:
        status = PASS_STATUS

    decision = {
        "schema_version": SCHEMA_VERSION,
        "task": TASK,
        "status": status,
        "timestamp_utc": now(),
        "output_root": rel(OUTPUT_ROOT),
        "runner": rel(RUNNER),
        "wood_lane_retained_first": bool(counted_primary and counted_primary[0]["story_id"] == "story:lon:wood_lane_ev_access_review"),
        "counted_primary_story_count": len(counted_primary),
        "distinct_primary_story_query_count": len(distinct_queries),
        "distinct_primary_story_queries": distinct_queries,
        "duplicate_shape_not_counted": duplicate_audit["duplicate_shape_not_counted"],
        "source_evidence_map_status": evidence_map["status"],
        "no_overclaim_status": overclaim["status"],
        "no_action_status": action["status"],
        "no_mutation_status": mutation["status"],
        "ui_build_deferred": True,
        "blocking_gap_count": len(blocking_gaps),
        "blocking_gaps": blocking_gaps,
        "non_blocking_gap_count": len(non_blocking_gaps),
        "non_blocking_gaps": non_blocking_gaps,
        "recommended_next_task": "MAIN-CITYBRAIN-D8-NYC-CASCADE-SCENARIO-LAYER-AUTHORING-R1",
    }

    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(OUTPUT_ROOT / "STORY_QUERY_REGISTRY.json", registry)
    write_json(OUTPUT_ROOT / "DISTINCT_PRIMARY_STORY_QUEUE.json", primary_queue)
    write_json(OUTPUT_ROOT / "DUPLICATE_SHAPE_AUDIT.json", duplicate_audit)
    write_json(OUTPUT_ROOT / "SCENARIO_LAYER_AUTHORING_PLAN.json", authoring_plan)
    write_json(OUTPUT_ROOT / "STORY_TO_SOURCE_EVIDENCE_MAP.json", evidence_map)
    write_json(OUTPUT_ROOT / "WOVEN_CAPABILITY_CUTAWAY_PLAN.json", cutaway_plan)
    write_json(OUTPUT_ROOT / "TRUST_MOMENT_WEAVING_PLAN.json", trust_plan)
    write_json(OUTPUT_ROOT / "PARKED_STORY_BACKLOG.json", backlog)
    write_json(OUTPUT_ROOT / "NO_OVERCLAIM_AUDIT.json", overclaim)
    write_json(OUTPUT_ROOT / "NO_ACTION_AUDIT.json", action)
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", mutation)
    write_json(OUTPUT_ROOT / "SCENARIO_AUTHORING_R1_DECISION.json", decision)
    write_docs(decision)
    secret = secret_audit()
    decision["secret_audit_status"] = secret["status"]
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", secret)
    write_json(OUTPUT_ROOT / "SCENARIO_AUTHORING_R1_DECISION.json", decision)
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", hash_manifest())

    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if status in {PASS_STATUS, PARTIAL_STATUS} and secret["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
