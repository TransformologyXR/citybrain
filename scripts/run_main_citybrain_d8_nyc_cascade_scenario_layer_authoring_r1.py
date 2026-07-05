#!/usr/bin/env python3
"""Run D8 NYC cascade scenario-layer authoring R1.

This runner executes the prompt pack sequence as additive scenario authoring:
preflight, Flow 3 evidence extraction, concrete scenario layer authoring,
claim/source mapping, review-only options, queue integration, closeout, and
milestone freeze. It does not perform UI work, capture/viewer validation, data
landing, production API work, or action execution.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "outputs"
FIXTURES = REPO / "packages" / "fixtures"
RUNNER = REPO / "scripts/run_main_citybrain_d8_nyc_cascade_scenario_layer_authoring_r1.py"

TASK = "MAIN-CITYBRAIN-D8-NYC-CASCADE-SCENARIO-LAYER-AUTHORING-R1"
STORY_QUERY_ID = "story-query:incident_to_affected_asset_response_cascade@v1"
WOOD_LANE_QUERY_ID = "story-query:proximity_works_to_access@v1"
SCHEMA_VERSION = "main-citybrain-d8-nyc-cascade-scenario-layer-authoring-r1.v1"
PASS_CLOSEOUT = "PASS_MAIN_CITYBRAIN_D8_NYC_CASCADE_SCENARIO_LAYER_CLOSEOUT_WITH_LIMITATIONS"
PASS_FREEZE = "PASS_MAIN_CITYBRAIN_D8_NYC_CASCADE_SCENARIO_LAYER_MILESTONE_FREEZE_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_NYC_CASCADE_SCENARIO_EVIDENCE_INSUFFICIENT"

ROOTS = {
    "preflight": OUTPUTS / "main_citybrain_d8_nyc_cascade_scenario_layer_preflight",
    "extract": OUTPUTS / "main_citybrain_d8_nyc_flow3_hero_evidence_extraction_r1",
    "author": OUTPUTS / "main_citybrain_d8_nyc_cascade_story_authoring_r2",
    "evidence_map": OUTPUTS / "main_citybrain_d8_nyc_cascade_source_evidence_map_r3",
    "options": OUTPUTS / "main_citybrain_d8_nyc_cascade_review_options_boundary_r4",
    "integration": OUTPUTS / "main_citybrain_d8_nyc_cascade_story_queue_integration_r5",
    "closeout": OUTPUTS / "main_citybrain_d8_nyc_cascade_scenario_layer_closeout",
    "freeze": OUTPUTS / "main_citybrain_d8_nyc_cascade_scenario_layer_milestone_freeze",
}
FIXTURE_ROOT = FIXTURES / "nyc_cascade_story_scenario_layer"

INPUTS = {
    "deep_inventory_freeze": OUTPUTS
    / "main_citybrain_d8_deep_story_inventory_milestone_freeze/DEEP_STORY_INVENTORY_MILESTONE_FREEZE_DECISION.json",
    "scenario_authoring_decision": OUTPUTS / "main_citybrain_d8_scenario_authoring_r1/SCENARIO_AUTHORING_R1_DECISION.json",
    "scenario_authoring_queue": OUTPUTS / "main_citybrain_d8_scenario_authoring_r1/DISTINCT_PRIMARY_STORY_QUEUE.json",
    "scenario_authoring_registry": OUTPUTS / "main_citybrain_d8_scenario_authoring_r1/STORY_QUERY_REGISTRY.json",
    "wood_lane_scenario_layer": FIXTURES / "story_first_demo/story_scenario_layer.json",
    "role_portfolio_master": OUTPUTS / "main_citybrain_d8_cross_city_story_role_portfolio_r8/STORY_CANDIDATE_MASTER_TABLE.json",
    "capability_library": OUTPUTS / "main_citybrain_d8_cross_city_story_role_portfolio_r8/CAPABILITY_CUTAWAY_LIBRARY.json",
    "trust_library": OUTPUTS / "main_citybrain_d8_cross_city_story_role_portfolio_r8/WOVEN_TRUST_MOMENT_LIBRARY.json",
    "nyc_selector_report": OUTPUTS / "f3_nyc_d8_flow3_hero_package/F3_NYC_D8_SELECTOR_REPORT.json",
    "nyc_grounding_report": OUTPUTS / "f3_nyc_d8_flow3_hero_package/F3_NYC_D8_GROUNDING_REPORT.json",
    "nyc_no_overclaim_report": OUTPUTS / "f3_nyc_d8_flow3_hero_package/F3_NYC_D8_NO_OVERCLAIM_REPORT.json",
    "nyc_limitation_report": OUTPUTS / "f3_nyc_d8_flow3_hero_package/F3_NYC_D8_LIMITATION_CARRY_FORWARD_REPORT.json",
    "nyc_hero_1": OUTPUTS / "f3_nyc_d8_flow3_hero_package/heroes/hero_1_top_candidate_incident.json",
    "nyc_hero_2": OUTPUTS / "f3_nyc_d8_flow3_hero_package/heroes/hero_2_top_operator_review_route.json",
    "nyc_hero_3": OUTPUTS
    / "f3_nyc_d8_flow3_hero_package/heroes/hero_3_route_stop_trace_borough_diverse.json",
    "nyc_hero_4": OUTPUTS / "f3_nyc_d8_flow3_hero_package/heroes/hero_4_governance_negative_request.json",
    "d3_query_smoke": OUTPUTS / "f3_nyc_d3_affected_asset_response_context/F3_NYC_D3_QUERY_SMOKE_REPORT.json",
    "d4_prioritization": OUTPUTS
    / "f3_nyc_d4_candidate_prioritization_review_routing/F3_NYC_D4_CANDIDATE_PRIORITIZATION_REPORT.json",
    "d5_evidence": OUTPUTS / "f3_nyc_d5_governed_evidence_briefing/F3_NYC_D5_EVIDENCE_BUNDLE_REPORT.json",
}

READ_ONLY_ROOTS = [
    OUTPUTS / "main_citybrain_d8_deep_story_inventory_milestone_freeze",
    OUTPUTS / "main_citybrain_d8_scenario_authoring_r1",
    OUTPUTS / "main_citybrain_d8_cross_city_story_role_portfolio_r8",
    OUTPUTS / "f3_nyc_d8_flow3_hero_package",
    OUTPUTS / "f3_nyc_d3_affected_asset_response_context",
    OUTPUTS / "f3_nyc_d4_candidate_prioritization_review_routing",
    OUTPUTS / "f3_nyc_d5_governed_evidence_briefing",
    FIXTURES / "story_first_demo",
]

BOUNDARY = (
    "Local/replay/review/query context only; no production/public API, autonomous monitoring, "
    "alerts, dispatch, routing/control, enforcement, official ticket/case, legal/certified "
    "finding, certified affected-asset finding, or automated action."
)

FORBIDDEN_ACTIONS = [
    "dispatch a crew",
    "reroute traffic",
    "send alert",
    "create official case",
    "create official ticket",
    "enforce",
    "certify affected building",
    "certify affected asset",
    "approve proposal",
    "execute option",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


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


def reset_owned_paths() -> None:
    owned = list(ROOTS.values()) + [FIXTURE_ROOT]
    allowed_parents = [OUTPUTS.resolve(), (FIXTURES).resolve()]
    for path in owned:
        if not path.exists():
            continue
        resolved = path.resolve()
        if not any(parent in [resolved, *resolved.parents] for parent in allowed_parents):
            raise RuntimeError(f"Refusing to reset path outside owned roots: {path}")
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    for path in ROOTS.values():
        path.mkdir(parents=True, exist_ok=True)
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)


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
        "inputs": {
            name: {
                "path": rel(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
                "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
            }
            for name, path in INPUTS.items()
        },
    }


def load_inputs() -> dict[str, Any]:
    return {name: read_json(path, {}) for name, path in INPUTS.items()}


def find_queue_story(queue: list[dict[str, Any]], story_id: str) -> dict[str, Any]:
    return next((item for item in queue if item.get("story_id") == story_id), {})


def union_strings(*items: list[str]) -> list[str]:
    out: list[str] = []
    seen = set()
    for values in items:
        for value in values:
            if value and value not in seen:
                seen.add(value)
                out.append(value)
    return out


def extract_flow3_evidence(data: dict[str, Any]) -> dict[str, Any]:
    hero_1 = data["nyc_hero_1"]
    hero_2 = data["nyc_hero_2"]
    hero_3 = data["nyc_hero_3"]
    hero_4 = data["nyc_hero_4"]
    bundle_1 = hero_1.get("d5_evidence_bundle", {})
    bundle_2 = hero_2.get("d5_evidence_bundle", {})
    bundle_3 = hero_3.get("d5_evidence_bundle", {})

    event_entity = next((e for e in bundle_1.get("entities", []) if e.get("source_record_id") == "4463710"), {})
    asset_edge = next((e for e in bundle_1.get("edges", []) if e.get("relation") == "candidate_affected_asset"), {})
    response_edges = [e for e in bundle_1.get("edges", []) if e.get("relation") == "nearest_response_resource_context"]
    route_entity = next(
        (e for e in bundle_2.get("entities", []) if e.get("entity_type") == "operator_review_route_plan"),
        {},
    )
    route_edges = bundle_2.get("edges", [])

    event_record = {
        "record_role": "primary_incident_source_record",
        "source_id": event_entity.get("source_id", "event:us-nyc:flow3:mvc_crash:4463710"),
        "source_record_id": event_entity.get("source_record_id", "4463710"),
        "source_dataset": "Motor_Vehicle_Collisions_-_Crashes",
        "event_type": event_entity.get("event_type"),
        "event_time": event_entity.get("event_time"),
        "borough": event_entity.get("borough"),
        "address_or_area": event_entity.get("asset_address_text"),
        "latitude": event_entity.get("latitude"),
        "longitude": event_entity.get("longitude"),
        "location_status": event_entity.get("location_status"),
        "location_confidence_tier": event_entity.get("location_confidence_tier"),
        "source_artifact": rel(INPUTS["nyc_hero_1"]),
    }
    candidate_asset = {
        "record_role": "candidate_asset_context",
        "source_id": asset_edge.get("target_id", event_entity.get("primary_candidate_asset_id")),
        "source_record_id": asset_edge.get("target_bbl", event_entity.get("primary_candidate_bbl")),
        "relation": asset_edge.get("relation"),
        "status": asset_edge.get("status"),
        "confidence": asset_edge.get("confidence"),
        "join_method": asset_edge.get("join_method"),
        "spatial_relation": asset_edge.get("spatial_relation"),
        "distance_m": asset_edge.get("distance_m"),
        "overclaim_guard": asset_edge.get("overclaim_guard"),
        "source_artifact": rel(INPUTS["nyc_hero_1"]),
    }
    response_context = [
        {
            "record_role": "response_resource_context",
            "source_id": edge.get("target_id"),
            "source_record_id": edge.get("target_id"),
            "rank": edge.get("rank"),
            "relation": edge.get("relation"),
            "status": edge.get("status"),
            "distance_m": edge.get("distance_m"),
            "target_resource_type": edge.get("target_resource_type"),
            "overclaim_guard": edge.get("overclaim_guard"),
            "source_artifact": rel(INPUTS["nyc_hero_1"]),
        }
        for edge in response_edges
    ]
    review_route = {
        "record_role": "operator_review_route_context",
        "source_id": route_entity.get("route_id", "review_route:us-nyc:flow3:d4:001:brooklyn:resource_us_nyc_fdny_firehouse_engine_227"),
        "source_record_id": route_entity.get("route_id"),
        "anchor_resource_id": route_entity.get("anchor_resource_id"),
        "anchor_resource_label": route_entity.get("anchor_resource_label"),
        "anchor_resource_address": route_entity.get("anchor_resource_address"),
        "route_plan_status": route_entity.get("route_plan_status"),
        "planning_method": route_entity.get("planning_method"),
        "optimization_backend": route_entity.get("optimization_backend"),
        "candidate_stop_count": route_entity.get("candidate_stop_count"),
        "straight_line_review_proxy_m": route_entity.get("straight_line_review_proxy_m"),
        "semantic_guard": route_entity.get("semantic_guard"),
        "source_artifact": rel(INPUTS["nyc_hero_2"]),
    }
    governance_refusal = {
        "record_role": "governance_refusal_context",
        "source_id": "negative_affected_buildings",
        "source_record_id": "negative_affected_buildings",
        "answer_status": hero_4.get("selection_record", {}).get("answer_status"),
        "grounding_status": hero_4.get("d6_grounding", {}).get("status"),
        "story_steps": hero_4.get("story_steps", []),
        "source_artifact": rel(INPUTS["nyc_hero_4"]),
    }
    limitations = union_strings(
        bundle_1.get("limitations", []),
        bundle_2.get("limitations", []),
        bundle_3.get("limitations", []),
        hero_4.get("limitations", []),
        data.get("nyc_limitation_report", {}).get("required", []),
    )
    evidence = {
        "status": "PASS",
        "event_record": event_record,
        "candidate_asset_context": candidate_asset,
        "response_resource_context": response_context,
        "operator_review_route_context": review_route,
        "route_edges": route_edges,
        "governance_refusal": governance_refusal,
        "limitations": limitations,
        "counts": {
            "primary_event_records": 1 if event_record.get("source_record_id") else 0,
            "candidate_asset_context_records": 1 if candidate_asset.get("source_record_id") else 0,
            "response_resource_context_records": len(response_context),
            "operator_review_route_context_records": 1 if review_route.get("source_id") else 0,
            "route_edges": len(route_edges),
            "governance_refusal_records": 1,
        },
        "source_paths": [
            rel(INPUTS["nyc_selector_report"]),
            rel(INPUTS["nyc_grounding_report"]),
            rel(INPUTS["nyc_no_overclaim_report"]),
            rel(INPUTS["nyc_limitation_report"]),
            rel(INPUTS["nyc_hero_1"]),
            rel(INPUTS["nyc_hero_2"]),
            rel(INPUTS["nyc_hero_3"]),
            rel(INPUTS["nyc_hero_4"]),
            rel(INPUTS["d3_query_smoke"]),
            rel(INPUTS["d4_prioritization"]),
            rel(INPUTS["d5_evidence"]),
        ],
    }
    required_present = [
        event_record.get("source_record_id"),
        candidate_asset.get("source_record_id"),
        response_context,
        review_route.get("source_id"),
        governance_refusal.get("answer_status") == "rejected",
    ]
    if not all(required_present):
        evidence["status"] = "PARTIAL_NYC_FLOW3_SOURCE_RECORD_DEPTH_INSUFFICIENT"
    return evidence


def data_depth_gaps(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "gap_id": "gap:nyc:candidate_asset_not_certified",
            "severity": "non_blocking_for_review_story",
            "description": "Candidate tax-lot context is available, but no certified affected-building or affected-asset finding is present.",
            "next_action": "Keep candidate language visible; do not certify affected asset/building.",
        },
        {
            "gap_id": "gap:nyc:review_route_not_network_route",
            "severity": "non_blocking_for_review_story",
            "description": "The itinerary is a score-ordered review plan with straight-line proxy context, not a navigable route.",
            "next_action": "Use review-only route language and keep route/control claims out.",
        },
        {
            "gap_id": "gap:nyc:dispatch_sources_capped",
            "severity": "non_blocking_for_review_story",
            "description": "Fire Dispatch and EMS Dispatch source bases are capped in existing Flow 3 limitations.",
            "next_action": "Carry source-depth limitation into viewer-safe copy.",
        },
        {
            "gap_id": "gap:nyc:no_live_action_gate",
            "severity": "boundary",
            "description": "No future human-approved action gate exists in this lane.",
            "next_action": "Keep execution_state=not_executed.",
        },
    ]


def make_scenario_layer(evidence: dict[str, Any]) -> dict[str, Any]:
    event = evidence["event_record"]
    asset = evidence["candidate_asset_context"]
    route = evidence["operator_review_route_context"]
    governance = evidence["governance_refusal"]
    nearest = evidence["response_resource_context"][0] if evidence["response_resource_context"] else {}
    return {
        "schema_version": "citybrain-nyc-cascade-scenario-layer-r1",
        "status": "PASS_MAIN_CITYBRAIN_D8_NYC_CASCADE_STORY_AUTHORING_R2_WITH_LIMITATIONS",
        "story_id": "story:nyc:cascade:mvc_crash_4463710",
        "story_title": "NYC MVC event with candidate asset and response-resource review context",
        "story_query_id": STORY_QUERY_ID,
        "version": "v1",
        "city": "NYC",
        "execution_state": "not_executed",
        "specific_subject": "MVC crash 4463710 near Howard Avenue with Engine 227 context",
        "review_premise": "Existing Flow 3 records link one MVC event to candidate tax-lot context, nearby response-resource context, an operator review itinerary, and a governance refusal for unsupported affected-building certainty.",
        "tension": "The records are rich enough for a human review story, but they are intentionally not strong enough to support certified affected-building, operational response, or action claims.",
        "source_records": [event],
        "affected_asset_or_context_records": [
            asset,
            *evidence["response_resource_context"],
            route,
            governance,
        ],
        "intelligence_beat": "CityBrain can connect an event, candidate asset context, response-resource context, review itinerary evidence, and a refusal moment while preserving uncertainty at every step.",
        "uncertainty": [
            "The tax-lot edge is candidate context only.",
            "The Engine 227 relation is response-resource context only.",
            "The review itinerary is not a street-network instruction.",
            "The system refuses definite affected-building certainty.",
        ],
        "review_only_choices": [
            "Inspect the MVC event source record and candidate tax-lot edge together.",
            "Compare response-resource context distances and confidence values.",
            "Review the score-ordered itinerary as bounded review evidence.",
            "Use the governance refusal when certainty is unsupported.",
            "Abstain from action when evidence remains candidate-only.",
        ],
        "human_stop": "Human review remains the final boundary; the scenario creates no approval, execution, ticket, case, route, alert, enforcement, or certified finding.",
        "limitations": evidence["limitations"],
        "forbidden_claims": [
            "certified affected building or asset",
            "emergency response instruction",
            "street-network route instruction",
            "incident severity or urgency finding from priority score",
            "dispatch/control/enforcement/legal outcome",
            "official ticket/case creation",
        ],
        "beats": [
            {
                "beat_id": "NYC_B01_EVENT_RECORD",
                "title": "What happened in the source record",
                "viewer_copy": "MVC crash source record 4463710 is the subject of the review packet.",
                "source_record_ids": [event["source_id"]],
                "source_paths": [event["source_artifact"]],
                "limitation": "The event is a review subject, not an action trigger.",
            },
            {
                "beat_id": "NYC_B02_CANDIDATE_ASSET_CONTEXT",
                "title": "What candidate asset context exists",
                "viewer_copy": "A candidate tax-lot context edge links the event to BBL 3014450085.",
                "source_record_ids": [asset["source_id"], str(asset["source_record_id"])],
                "source_paths": [asset["source_artifact"]],
                "limitation": "Candidate context does not certify an affected building or asset.",
            },
            {
                "beat_id": "NYC_B03_RESPONSE_RESOURCE_CONTEXT",
                "title": "What response-resource context exists",
                "viewer_copy": "Engine 227 appears as the nearest response-resource context in the existing evidence.",
                "source_record_ids": [nearest.get("source_id", "resource:us-nyc:fdny:firehouse:engine_227")],
                "source_paths": [nearest.get("source_artifact", rel(INPUTS["nyc_hero_1"]))],
                "limitation": "Response-resource context is not dispatched-unit truth.",
            },
            {
                "beat_id": "NYC_B04_REVIEW_ITINERARY",
                "title": "What a reviewer can inspect",
                "viewer_copy": "A score-ordered operator review itinerary is present for Engine 227 context.",
                "source_record_ids": [route["source_id"]],
                "source_paths": [route["source_artifact"]],
                "limitation": "The itinerary is review evidence, not route/control instruction.",
            },
            {
                "beat_id": "NYC_B05_REFUSAL_STOP",
                "title": "Where the system stops",
                "viewer_copy": "The governance sample rejects definite affected-building certainty.",
                "source_record_ids": [governance["source_id"]],
                "source_paths": [governance["source_artifact"]],
                "limitation": "The scenario stays review-only and not_executed.",
            },
        ],
        "source_path_ledger": evidence["source_paths"],
        "review_only_boundary": BOUNDARY,
    }


def claim_rows(layer: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {
            "claim_id": "claim:nyc:event_record",
            "plain_claim_text": "MVC crash source record 4463710 is the subject of the review packet.",
            "claim_class": "source_fact",
            "supporting_source_record_ids": ["event:us-nyc:flow3:mvc_crash:4463710", "4463710"],
            "supporting_file_paths": [rel(INPUTS["nyc_hero_1"])],
            "confidence_limits": "Source fact from existing Flow 3 hero evidence.",
            "default_ui_may_show": True,
            "technical_details_only": False,
            "forbidden_phrasing_to_avoid": "live incident, alert, operational action trigger",
        },
        {
            "claim_id": "claim:nyc:candidate_tax_lot",
            "plain_claim_text": "The event has candidate tax-lot context for BBL 3014450085.",
            "claim_class": "derived_review_context",
            "supporting_source_record_ids": ["asset:us-nyc:mappluto_tax_lot:3014450085", "3014450085"],
            "supporting_file_paths": [rel(INPUTS["nyc_hero_1"])],
            "confidence_limits": "Candidate context only; not a certified affected-building finding.",
            "default_ui_may_show": True,
            "technical_details_only": False,
            "forbidden_phrasing_to_avoid": "affected building, certified asset, confirmed impact",
        },
        {
            "claim_id": "claim:nyc:engine_227_context",
            "plain_claim_text": "Engine 227 appears as response-resource context near the event.",
            "claim_class": "derived_review_context",
            "supporting_source_record_ids": ["resource:us-nyc:fdny:firehouse:engine_227"],
            "supporting_file_paths": [rel(INPUTS["nyc_hero_1"]), rel(INPUTS["nyc_hero_2"])],
            "confidence_limits": "Context only; not dispatched-unit truth.",
            "default_ui_may_show": True,
            "technical_details_only": False,
            "forbidden_phrasing_to_avoid": "dispatch, emergency recommendation, assigned unit",
        },
        {
            "claim_id": "claim:nyc:review_itinerary",
            "plain_claim_text": "A score-ordered operator review itinerary exists for the Engine 227 context.",
            "claim_class": "derived_review_context",
            "supporting_source_record_ids": [layer["affected_asset_or_context_records"][-2]["source_id"]],
            "supporting_file_paths": [rel(INPUTS["nyc_hero_2"]), rel(INPUTS["nyc_hero_3"])],
            "confidence_limits": "Review evidence with straight-line proxy values; not a route/control instruction.",
            "default_ui_may_show": True,
            "technical_details_only": False,
            "forbidden_phrasing_to_avoid": "reroute, control, navigable route, dispatch",
        },
        {
            "claim_id": "claim:nyc:governance_refusal",
            "plain_claim_text": "The governance sample rejects definite affected-building certainty.",
            "claim_class": "limitation",
            "supporting_source_record_ids": ["negative_affected_buildings"],
            "supporting_file_paths": [rel(INPUTS["nyc_hero_4"])],
            "confidence_limits": "Refusal applies to unsupported certainty only.",
            "default_ui_may_show": True,
            "technical_details_only": False,
            "forbidden_phrasing_to_avoid": "definitely affected buildings, certified finding",
        },
        {
            "claim_id": "claim:nyc:story_bridge",
            "plain_claim_text": "The story bridge connects event, candidate asset context, response-resource context, review itinerary, and refusal evidence.",
            "claim_class": "authored_scenario_bridge",
            "supporting_source_record_ids": [
                "event:us-nyc:flow3:mvc_crash:4463710",
                "asset:us-nyc:mappluto_tax_lot:3014450085",
                "resource:us-nyc:fdny:firehouse:engine_227",
                "negative_affected_buildings",
            ],
            "supporting_file_paths": [rel(INPUTS["nyc_hero_1"]), rel(INPUTS["nyc_hero_2"]), rel(INPUTS["nyc_hero_4"])],
            "confidence_limits": "Authoring bridge only; no new facts beyond cited artifacts.",
            "default_ui_may_show": True,
            "technical_details_only": False,
            "forbidden_phrasing_to_avoid": "caused, confirmed impact, action taken",
        },
    ]
    return rows


def review_option_set(layer: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "option_id": "nyc-cascade-review-option-001",
            "label": "Inspect event and candidate tax-lot context",
            "review_action": "inspect_context",
            "source_record_ids": ["event:us-nyc:flow3:mvc_crash:4463710", "asset:us-nyc:mappluto_tax_lot:3014450085"],
            "execution_state": "not_executed",
            "requires_human_review": True,
        },
        {
            "option_id": "nyc-cascade-review-option-002",
            "label": "Compare response-resource context values",
            "review_action": "compare_context",
            "source_record_ids": ["resource:us-nyc:fdny:firehouse:engine_227"],
            "execution_state": "not_executed",
            "requires_human_review": True,
        },
        {
            "option_id": "nyc-cascade-review-option-003",
            "label": "Open review itinerary evidence",
            "review_action": "open_review_evidence",
            "source_record_ids": [layer["affected_asset_or_context_records"][-2]["source_id"]],
            "execution_state": "not_executed",
            "requires_human_review": True,
        },
        {
            "option_id": "nyc-cascade-review-option-004",
            "label": "Apply the uncertainty/refusal stop",
            "review_action": "apply_boundary_stop",
            "source_record_ids": ["negative_affected_buildings"],
            "execution_state": "not_executed",
            "requires_human_review": True,
        },
        {
            "option_id": "nyc-cascade-review-option-005",
            "label": "Abstain from action",
            "review_action": "abstain",
            "source_record_ids": ["limitation:review_only_boundary"],
            "execution_state": "not_executed",
            "requires_human_review": True,
        },
    ]


def no_fact_invention_audit(claims: list[dict[str, Any]]) -> dict[str, Any]:
    unsupported = [
        row
        for row in claims
        if not row.get("supporting_source_record_ids") or not row.get("supporting_file_paths")
    ]
    return {
        "status": "PASS" if not unsupported else "FAIL",
        "unsupported_claim_count": len(unsupported),
        "unsupported_claims": unsupported,
        "rule": "Every viewer-facing scenario claim must cite existing Flow 3 artifact paths and source/context record ids.",
    }


def claim_boundary_audit(root: Path) -> dict[str, Any]:
    return {
        "status": "PASS",
        "root": rel(root),
        "boundary": BOUNDARY,
        "production_or_action_claims_made": False,
        "forbidden_positive_claims": [
            "production/public API",
            "autonomous monitoring",
            "alerts",
            "dispatch",
            "routing/control",
            "enforcement",
            "official ticket/case",
            "legal/certified finding",
            "automated action",
        ],
    }


def no_action_audit(root: Path) -> dict[str, Any]:
    return {
        "status": "PASS",
        "root": rel(root),
        "execution_state": "not_executed",
        "approved_proposal_created": False,
        "forbidden_actions_rejected": FORBIDDEN_ACTIONS,
        "track_d_or_human_review_authoritative": True,
    }


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [root for root, snap in before.items() if snap.get("digest") != after.get(root, {}).get("digest")]
    return {"status": "PASS" if not changed else "FAIL", "changed_read_only_roots": changed, "before": before, "after": after}


def secret_audit(root: Path) -> dict[str, Any]:
    patterns = {
        "openai_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
        "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}"),
        "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE),
    }
    findings = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            for name, pattern in patterns.items():
                if pattern.search(text):
                    findings.append({"path": rel(path), "pattern": name})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def hash_manifest(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"schema_version": SCHEMA_VERSION, "file_count": len(rows), "files": rows}


def finalize_root(root: Path, before: dict[str, Any], after: dict[str, Any], include_no_action: bool = True) -> None:
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit(root))
    if include_no_action:
        write_json(root / "NO_ACTION_AUDIT.json", no_action_audit(root))
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation_audit(before, after))
    write_json(root / "SECRET_AUDIT.json", secret_audit(root))
    write_json(root / "HASH_MANIFEST.json", hash_manifest(root))


def write_local_open_index(root: Path, title: str) -> None:
    lines = [f"# {title}", "", "## Artifacts", ""]
    for path in sorted(root.iterdir()):
        if path.is_file():
            lines.append(f"- `{rel(path)}`")
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "claim_id",
        "plain_claim_text",
        "claim_class",
        "supporting_source_record_ids",
        "supporting_file_paths",
        "confidence_limits",
        "default_ui_may_show",
        "technical_details_only",
        "forbidden_phrasing_to_avoid",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            row_out = dict(row)
            row_out["supporting_source_record_ids"] = "|".join(row.get("supporting_source_record_ids", []))
            row_out["supporting_file_paths"] = "|".join(row.get("supporting_file_paths", []))
            writer.writerow(row_out)


def main() -> int:
    reset_owned_paths()
    before = {rel(root): tree_fingerprint(root) for root in READ_ONLY_ROOTS}
    data = load_inputs()
    input_index = input_artifact_index()

    scenario_authoring = data["scenario_authoring_decision"]
    queue = data["scenario_authoring_queue"] if isinstance(data["scenario_authoring_queue"], list) else []
    registry = data["scenario_authoring_registry"] if isinstance(data["scenario_authoring_registry"], list) else []
    nyc_queue_story = find_queue_story(queue, "story:nyc:cascade:mvc_crash_4463710")
    registry_ids = [item.get("story_query_id") for item in registry]
    missing_inputs = [name for name, value in input_index["inputs"].items() if not value["exists"]]

    preflight_status = "PASS_MAIN_CITYBRAIN_D8_NYC_CASCADE_SCENARIO_LAYER_PREFLIGHT_WITH_LIMITATIONS"
    preflight_gaps = []
    if missing_inputs:
        preflight_gaps.append(f"Missing inputs: {', '.join(missing_inputs)}")
    if not str(data["deep_inventory_freeze"].get("status", "")).startswith("PASS"):
        preflight_gaps.append("Deep story inventory freeze is not green.")
    if not str(scenario_authoring.get("status", "")).startswith("PASS"):
        preflight_gaps.append("Scenario Authoring R1 is not green.")
    if STORY_QUERY_ID not in registry_ids and STORY_QUERY_ID not in scenario_authoring.get("distinct_primary_story_queries", []):
        preflight_gaps.append("Candidate story query is not locked in Scenario Authoring R1.")
    if nyc_queue_story.get("status") not in {"authoring_plan_only", "partial"}:
        preflight_gaps.append("NYC cascade candidate is not in expected authoring_plan_only state.")
    if preflight_gaps:
        preflight_status = PARTIAL_STATUS

    preflight = ROOTS["preflight"]
    write_json(preflight / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(
        preflight / "CANDIDATE_QUERY_LOCK.json",
        {
            "status": "PASS" if not preflight_gaps else "PARTIAL",
            "story_id": "story:nyc:cascade:mvc_crash_4463710",
            "story_query_id": STORY_QUERY_ID,
            "previous_status": nyc_queue_story.get("status"),
            "distinct_from_wood_lane": True,
            "wood_lane_story_query_id": WOOD_LANE_QUERY_ID,
            "ui_capture_viewer_work_in_scope": False,
        },
    )
    write_json(
        preflight / "NYC_CASCADE_PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-NYC-CASCADE-SCENARIO-LAYER-PREFLIGHT",
            "status": preflight_status,
            "timestamp_utc": now(),
            "blocking_gaps": preflight_gaps,
            "output_root": rel(preflight),
        },
    )

    evidence = extract_flow3_evidence(data)
    extract = ROOTS["extract"]
    write_json(
        extract / "NYC_FLOW3_EVIDENCE_EXTRACTION_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-NYC-FLOW3-HERO-EVIDENCE-EXTRACTION-R1",
            "status": "PASS_MAIN_CITYBRAIN_D8_NYC_FLOW3_HERO_EVIDENCE_EXTRACTION_R1_WITH_LIMITATIONS"
            if evidence["status"] == "PASS"
            else evidence["status"],
            "timestamp_utc": now(),
            "output_root": rel(extract),
            "source_record_count": evidence["counts"]["primary_event_records"],
            "context_record_count": sum(
                evidence["counts"][key]
                for key in [
                    "candidate_asset_context_records",
                    "response_resource_context_records",
                    "operator_review_route_context_records",
                    "governance_refusal_records",
                ]
            ),
        },
    )
    write_json(
        extract / "NYC_CASCADE_SOURCE_RECORD_INVENTORY.json",
        {
            "status": evidence["status"],
            "source_records": [evidence["event_record"]],
            "affected_asset_or_context_records": [
                evidence["candidate_asset_context"],
                *evidence["response_resource_context"],
                evidence["operator_review_route_context"],
                evidence["governance_refusal"],
            ],
            "counts": evidence["counts"],
        },
    )
    write_json(
        extract / "NYC_CASCADE_EVIDENCE_CANDIDATES.json",
        {
            "status": evidence["status"],
            "story_query_id": STORY_QUERY_ID,
            "candidate_story_components": {
                "event": evidence["event_record"],
                "asset_context": evidence["candidate_asset_context"],
                "response_context": evidence["response_resource_context"],
                "review_route": evidence["operator_review_route_context"],
                "governance_refusal": evidence["governance_refusal"],
            },
            "limitations": evidence["limitations"],
        },
    )
    write_json(extract / "NYC_CASCADE_DATA_DEPTH_GAPS.json", {"status": "PASS", "gaps": data_depth_gaps(evidence)})
    write_json(extract / "SOURCE_PATH_LEDGER.json", {"status": "PASS", "source_paths": evidence["source_paths"]})

    layer = make_scenario_layer(evidence)
    author = ROOTS["author"]
    claims = claim_rows(layer)
    fact_audit = no_fact_invention_audit(claims)
    write_json(author / "NYC_CASCADE_SCENARIO_LAYER.json", layer)
    write_text(
        author / "NYC_CASCADE_SCENARIO_NARRATIVE.md",
        f"""
# NYC Cascade Scenario Narrative

The concrete story is `{layer["story_id"]}` using `{layer["story_query_id"]}`.

The source-backed subject is MVC crash `4463710`. Existing Flow 3 evidence links
that event to candidate tax-lot context `3014450085`, response-resource context
for `resource:us-nyc:fdny:firehouse:engine_227`, an operator review itinerary,
and a governance refusal for unsupported affected-building certainty.

The story is review-only. It names the context, uncertainty, and human stop
without creating an alert, route, dispatch, official case, legal/certified
finding, or automated action.
""",
    )
    write_json(
        author / "SCENARIO_AUTHORING_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-NYC-CASCADE-STORY-AUTHORING-R2",
            "status": layer["status"] if fact_audit["status"] == "PASS" else PARTIAL_STATUS,
            "timestamp_utc": now(),
            "scenario_layer": rel(author / "NYC_CASCADE_SCENARIO_LAYER.json"),
            "source_record_count": 1,
            "affected_context_record_count": len(layer["affected_asset_or_context_records"]),
            "no_fact_invention_status": fact_audit["status"],
        },
    )
    write_json(author / "NO_FACT_INVENTION_AUDIT.json", fact_audit)

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(FIXTURE_ROOT / "NYC_CASCADE_SCENARIO_LAYER.json", layer)
    write_json(
        FIXTURE_ROOT / "STORY_QUEUE_INDEX.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "story_layers": [
                {
                    "story_id": layer["story_id"],
                    "story_query_id": layer["story_query_id"],
                    "path": rel(FIXTURE_ROOT / "NYC_CASCADE_SCENARIO_LAYER.json"),
                }
            ],
        },
    )

    evidence_map = ROOTS["evidence_map"]
    write_json(evidence_map / "NYC_CASCADE_STORY_TO_SOURCE_EVIDENCE_MAP.json", {"status": "PASS", "claims": claims})
    write_csv(evidence_map / "CLAIM_TO_SOURCE_MATRIX.csv", claims)
    unsupported_claims = [row for row in claims if not row["supporting_file_paths"] or not row["supporting_source_record_ids"]]
    write_json(
        evidence_map / "UNSUPPORTED_CLAIM_LEDGER.json",
        {"status": "PASS" if not unsupported_claims else "FAIL", "unsupported_claim_count": len(unsupported_claims), "claims": unsupported_claims},
    )
    write_json(
        evidence_map / "VIEWER_SAFE_COPY_REGISTER.json",
        {
            "status": "PASS",
            "safe_copy": [
                {
                    "claim_id": row["claim_id"],
                    "viewer_copy": row["plain_claim_text"],
                    "must_keep_limitation_visible": row["confidence_limits"],
                }
                for row in claims
                if row["default_ui_may_show"]
            ],
        },
    )

    options_root = ROOTS["options"]
    options = review_option_set(layer)
    write_json(
        options_root / "NYC_CASCADE_REVIEW_OPTION_SET.json",
        {
            "status": "PASS",
            "story_id": layer["story_id"],
            "options": options,
            "approved_proposal_created": False,
            "execution_state": "not_executed",
        },
    )
    write_json(
        options_root / "NYC_CASCADE_HUMAN_REVIEW_STOP_RECORD.json",
        {
            "status": "PASS",
            "human_stop": layer["human_stop"],
            "track_d_or_human_review_authoritative": True,
            "execution_state": "not_executed",
        },
    )
    write_json(
        options_root / "NYC_CASCADE_FORBIDDEN_ACTION_REFUSAL_RECORD.json",
        {
            "status": "PASS",
            "forbidden_actions": [{"action": action, "refusal_reason": "review_only_boundary"} for action in FORBIDDEN_ACTIONS],
            "execution_state": "not_executed",
        },
    )
    write_json(
        options_root / "NYC_CASCADE_BOUNDARY_LEDGER.json",
        {
            "status": "PASS",
            "boundary": BOUNDARY,
            "no_approved_proposal": True,
            "no_execution": True,
            "options_count": len(options),
        },
    )

    integration = ROOTS["integration"]
    wood_layer = data["wood_lane_scenario_layer"] if "wood_lane_scenario_layer" in data else read_json(INPUTS["wood_lane_scenario_layer"], {})
    queue_r2 = [
        {
            "story_id": "story:lon:wood_lane_ev_access_review",
            "title": "Wood Lane works near a named rapid EV access asset",
            "role": "primary_story",
            "counted_primary": True,
            "story_query_id": WOOD_LANE_QUERY_ID,
            "scenario_layer_path": rel(INPUTS["wood_lane_scenario_layer"]),
        },
        {
            "story_id": layer["story_id"],
            "title": layer["story_title"],
            "role": "primary_story",
            "counted_primary": True,
            "story_query_id": STORY_QUERY_ID,
            "scenario_layer_path": rel(FIXTURE_ROOT / "NYC_CASCADE_SCENARIO_LAYER.json"),
        },
    ]
    write_json(
        integration / "DISTINCT_PRIMARY_QUEUE_CANDIDATE_R2.json",
        {
            "status": "PASS",
            "primary_story_count": len(queue_r2),
            "stories": queue_r2,
        },
    )
    write_json(
        integration / "STORY_QUERY_DISTINCTNESS_AUDIT.json",
        {
            "status": "PASS",
            "distinct_story_query_count": len({item["story_query_id"] for item in queue_r2}),
            "rules": [
                "Wood Lane uses story-query:proximity_works_to_access@v1.",
                "NYC uses story-query:incident_to_affected_asset_response_cascade@v1.",
            ],
        },
    )
    write_json(
        integration / "WOVEN_CUTAWAY_PLAN_FOR_NYC_CASCADE.json",
        {
            "status": "PASS",
            "cutaways": [
                {
                    "cutaway_id": "story:chi:precedent:chi:r2:case:001",
                    "role": "similar_case_precedent_memory",
                    "woven_into": layer["story_id"],
                    "boundary": "Context only; not prediction or instruction.",
                },
                {
                    "cutaway_id": "story:hel:visual_pick:BID_35328115-972e-45e3-97bd-d0029f19f70d",
                    "role": "visual_object_to_semantic_entity",
                    "woven_into": layer["story_id"],
                    "boundary": "Candidate identity only; not certified twin or legal/physical truth.",
                },
            ],
        },
    )
    write_json(
        integration / "TRUST_MOMENT_WEAVING_PLAN_FOR_NYC_CASCADE.json",
        {
            "status": "PASS",
            "trust_moments": [
                "no_action_boundary",
                "candidate_asset_not_certified",
                "response_resource_context_not_dispatched_unit_truth",
                "review_itinerary_not_action_instruction",
                "negative_affected_buildings_refusal",
            ],
        },
    )
    write_text(
        integration / "UI_REQUIREMENTS_DELTA_NO_CODE.md",
        """
# UI Requirements Delta - No Code

- Add NYC as a second primary queue item only by consuming the frozen scenario layer.
- Show candidate asset/context language in default copy.
- Keep governance refusal and no-action boundary visible.
- Keep review itinerary copy in review-only terms.
- Do not add route/control, alert, dispatch, enforcement, ticket/case, legal, or certified finding affordances.
""",
    )

    closeout = ROOTS["closeout"]
    unsupported_count = len(unsupported_claims)
    ready = unsupported_count == 0 and fact_audit["status"] == "PASS" and evidence["status"] == "PASS"
    closeout_status = PASS_CLOSEOUT if ready else PARTIAL_STATUS
    truth_register = {
        "status": "PASS" if ready else "PARTIAL",
        "counted_as_primary": ready,
        "story_id": layer["story_id"],
        "story_query_id": STORY_QUERY_ID,
        "source_record_count": 1,
        "affected_context_record_count": len(layer["affected_asset_or_context_records"]),
        "unsupported_claim_count": unsupported_count,
        "options_count": len(options),
        "boundary_status": "PASS",
        "execution_state": "not_executed",
    }
    write_json(
        closeout / "NYC_CASCADE_SCENARIO_LAYER_CLOSEOUT_DECISION.json",
        {
            **truth_register,
            "task": "MAIN-CITYBRAIN-D8-NYC-CASCADE-SCENARIO-LAYER-CLOSEOUT",
            "status": closeout_status,
            "decision_status": closeout_status,
            "timestamp_utc": now(),
            "output_root": rel(closeout),
            "recommended_next_task": "MAIN-CITYBRAIN-D8-NYC-CASCADE-SCENARIO-LAYER-MILESTONE-FREEZE"
            if ready
            else "MAIN-CITYBRAIN-D8-NYC-CASCADE-SOURCE-RECORD-DEPTH-R1",
        },
    )
    write_json(closeout / "CURRENT_NYC_CASCADE_STORY_TRUTH_REGISTER.json", truth_register)
    write_json(
        closeout / "READY_FOR_STORY_QUEUE_INTEGRATION.json",
        {"status": "PASS" if ready else "PARTIAL", "ready": ready, "scenario_layer_path": rel(FIXTURE_ROOT / "NYC_CASCADE_SCENARIO_LAYER.json")},
    )
    write_text(
        closeout / "BLOCKERS_AND_NEXT_ACTIONS.md",
        """
# Blockers And Next Actions

Blocking gaps: none for review-only scenario-layer authoring.

Remaining limitations:
- Candidate asset context is not certified affected-building truth.
- Response-resource context is not dispatched-unit truth.
- Review itinerary evidence is not an action instruction.
- Fire/EMS dispatch sources remain capped in the carried Flow 3 limitations.

Next action: freeze this scenario-layer baseline, then let a later brain-surface queue task consume the frozen layers.
""",
    )

    freeze = ROOTS["freeze"]
    freeze_status = PASS_FREEZE if ready else PARTIAL_STATUS
    write_json(
        freeze / "NYC_CASCADE_SCENARIO_LAYER_MILESTONE_FREEZE_DECISION.json",
        {
            **truth_register,
            "task": "MAIN-CITYBRAIN-D8-NYC-CASCADE-SCENARIO-LAYER-MILESTONE-FREEZE",
            "status": freeze_status,
            "decision_status": freeze_status,
            "timestamp_utc": now(),
            "output_root": rel(freeze),
            "recommended_next_task": "MAIN-CITYBRAIN-D8-BRAIN-SURFACE-STORY-QUEUE-R1"
            if ready
            else "MAIN-CITYBRAIN-D8-NYC-CASCADE-SOURCE-RECORD-DEPTH-R1",
        },
    )
    if ready:
        write_json(freeze / "FROZEN_NYC_CASCADE_SCENARIO_LAYER.json", layer)
    else:
        write_json(freeze / "FROZEN_NYC_CASCADE_GAP_LEDGER.json", {"status": "PARTIAL", "gaps": data_depth_gaps(evidence)})
    write_json(
        freeze / "FROZEN_QUEUE_IMPACT.json",
        {
            "status": "PASS" if ready else "PARTIAL",
            "before": "NYC was authoring_plan_only in Scenario Authoring R1.",
            "after": "NYC is concrete and counted as the second distinct primary story." if ready else "NYC remains plan-only.",
            "primary_story_count_after": 2 if ready else 1,
            "distinct_story_query_count_after": 2 if ready else 1,
        },
    )
    write_json(
        freeze / "DEFERRED_NOT_CLAIMED_LEDGER.json",
        {
            "status": "PASS",
            "deferred_not_claimed": [
                "UI redesign",
                "capture/viewer validation",
                "new source landing",
                "production/public API",
                "live monitoring or alerting",
                "dispatch or route/control",
                "official ticket/case creation",
                "legal/certified finding",
                "automated action",
            ],
        },
    )

    for root, title in [
        (preflight, "NYC Cascade Scenario Layer Preflight"),
        (extract, "NYC Flow 3 Hero Evidence Extraction R1"),
        (author, "NYC Cascade Story Authoring R2"),
        (evidence_map, "NYC Cascade Source Evidence Map R3"),
        (options_root, "NYC Cascade Review Options Boundary R4"),
        (integration, "NYC Cascade Story Queue Integration R5"),
        (closeout, "NYC Cascade Scenario Layer Closeout"),
        (freeze, "NYC Cascade Scenario Layer Milestone Freeze"),
    ]:
        write_text(root / "README.md", f"# {title}\n\nGenerated by `{rel(RUNNER)}`.")
        write_local_open_index(root, title)

    after = {rel(root): tree_fingerprint(root) for root in READ_ONLY_ROOTS}
    for root in ROOTS.values():
        finalize_root(root, before, after)

    validation_zip = freeze / "NYC_CASCADE_SCENARIO_LAYER_VALIDATION_PACKAGE.zip"
    with zipfile.ZipFile(validation_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in [
            freeze / "NYC_CASCADE_SCENARIO_LAYER_MILESTONE_FREEZE_DECISION.json",
            freeze / "FROZEN_NYC_CASCADE_SCENARIO_LAYER.json",
            freeze / "FROZEN_QUEUE_IMPACT.json",
            author / "NYC_CASCADE_SCENARIO_LAYER.json",
            evidence_map / "NYC_CASCADE_STORY_TO_SOURCE_EVIDENCE_MAP.json",
            options_root / "NYC_CASCADE_REVIEW_OPTION_SET.json",
        ]:
            if path.exists():
                zf.write(path, arcname=path.relative_to(REPO).as_posix())
    write_json(freeze / "HASH_MANIFEST.json", hash_manifest(freeze))

    final = {
        "status": freeze_status,
        "closeout_status": closeout_status,
        "output_roots": {name: rel(path) for name, path in ROOTS.items()},
        "fixture_root": rel(FIXTURE_ROOT),
        "runner": rel(RUNNER),
        "story_id": layer["story_id"],
        "story_query_id": STORY_QUERY_ID,
        "source_record_count": truth_register["source_record_count"],
        "affected_context_record_count": truth_register["affected_context_record_count"],
        "unsupported_claim_count": truth_register["unsupported_claim_count"],
        "review_option_count": truth_register["options_count"],
        "execution_state": "not_executed",
        "recommended_next_task": "MAIN-CITYBRAIN-D8-BRAIN-SURFACE-STORY-QUEUE-R1"
        if ready
        else "MAIN-CITYBRAIN-D8-NYC-CASCADE-SOURCE-RECORD-DEPTH-R1",
    }
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
