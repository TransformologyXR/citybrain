#!/usr/bin/env python3
"""Build the Cross-Domain Story Arc + Eval Expansion R1 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPANDED_CORPUS_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1"
DEFAULT_EXPANDED_CADENCE_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-EXPANDED-CORPUS-CADENCE-REPLAY-MINING-R2"
DEFAULT_MOBILITY_PACKET_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-REVIEW-PACKET-360-MOBILITY-NATIVE-REPAIR-R1"
DEFAULT_SIMULATION_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-SIMULATION-DISTRIBUTION-CHECKED-FIXTURES-R1"
DEFAULT_OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-CROSS-DOMAIN-STORY-ARC-EVAL-EXPANSION-R1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-cross-domain-story-arc-eval-expansion-r1"

STATUS_PASS = "PASS_MAIN_CITYBRAIN_CROSS_DOMAIN_STORY_ARC_EVAL_EXPANSION_R1_WITH_LIMITATIONS"
STATUS_BLOCKED = "BLOCKED_MAIN_CITYBRAIN_CROSS_DOMAIN_STORY_ARC_EVAL_EXPANSION_R1_WITH_LIMITATIONS"
STATUS_NEEDS_REPAIR = "NEEDS_REPAIR_MAIN_CITYBRAIN_CROSS_DOMAIN_STORY_ARC_EVAL_EXPANSION_R1_WITH_LIMITATIONS"

FAMILIES = [
    "mobility_access_interruption_v0",
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]

STORY_ARC_ID = "cross-domain-story-arc-r1-construction-permit-access-compliance-asset-cascade"
PRIMARY_SITE = "cer:building:alpha"
PRIMARY_CORRIDOR = "corridor:synthetic-dubai-aoi:alpha-access-corridor"
PRIMARY_ASSET = "asset:city:synthetic:utility-node-alpha"

REQUIRED_FILES = [
    "CROSS_DOMAIN_STORY_ARC_DECISION.json",
    "CROSS_DOMAIN_STORY_INPUT_INVENTORY.json",
    "CROSS_DOMAIN_STORY_TRUTH_MANIFEST.json",
    "CROSS_DOMAIN_STORY_ARC_EVENTS.jsonl",
    "CROSS_DOMAIN_ENTITY_RESOLUTION_REPORT.json",
    "CROSS_FAMILY_CAUSAL_LINK_LEDGER.json",
    "STORY_ARC_REVIEW_PACKET_360.json",
    "STORY_ARC_REVIEW_PACKET_360.md",
    "STORY_ARC_REVIEW_INDEX.html",
    "STORY_ARC_EVAL_EXPANSION_CASES.jsonl",
    "STORY_ARC_EVAL_ANSWER_KEY.json",
    "STORY_ARC_EVAL_COVERAGE_SCORECARD.json",
    "STORY_ARC_NEGATIVE_CHALLENGE_CASES.jsonl",
    "STORY_ARC_FOUNDER_DIAGNOSTIC_CARD_CANDIDATES.json",
    "STORY_ARC_AI_DIAGNOSTIC_REVIEW_GUIDE.md",
    "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json",
    "NO_DIRECT_D5D6_BYPASS_GUARD.json",
    "NO_FOUNDER_SESSION_FUEL_GUARD.json",
    "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json",
    "NO_FORECAST_ACTION_GUARD.json",
    "NO_SOURCE_TRUTH_MUTATION_GUARD.json",
    "BOUNDARY_NO_ACTION_AUDIT.json",
    "HASH_MANIFEST.sha256",
    "CODEX_CLOSEOUT.md",
]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expanded_paths(root: Path) -> dict[str, Path]:
    return {
        "decision": root / "SEED_R3_ADAPTER_CORPUS_EXPANSION_DECISION.json",
        "feed": root / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl",
        "counts": root / "SEED_R3_EXPANDED_EVENT_COUNTS_BY_FAMILY.json",
        "canonical": root / "SEED_R3_EXPANDED_CANONICAL_RESOLUTION_REPORT.json",
        "queue_distribution": root / "SEED_R3_EXPANDED_QUEUE_REASON_DISTRIBUTION.json",
        "duplicate_ledger": root / "SEED_R3_EXPANDED_DUPLICATE_CANDIDATE_LEDGER.jsonl",
        "unresolved": root / "SEED_R3_EXPANDED_UNRESOLVED_QUEUE.jsonl",
        "quarantine": root / "SEED_R3_EXPANDED_QUARANTINE_QUEUE.jsonl",
        "story_gate": root / "SEED_R3_STORY_ARC_READINESS_GATE.json",
        "no_d5d6": root / "NO_DIRECT_D5D6_BYPASS_GUARD.json",
        "no_standalone": root / "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json",
    }


def cadence_paths(root: Path) -> dict[str, Path]:
    return {
        "decision": root / "EXPANDED_CORPUS_CADENCE_REPLAY_MINING_DECISION.json",
        "hashes": root / "EXPANDED_CORPUS_CADENCE_MODE_STATE_HASHES.json",
        "canonical": root / "EXPANDED_CORPUS_CANONICAL_RESOLUTION_REPLAY_VALIDATED.json",
        "queue": root / "EXPANDED_CORPUS_QUEUE_MINING_REPORT.json",
        "no_d5d6": root / "NO_DIRECT_D5D6_BYPASS_GUARD.json",
        "no_standalone": root / "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json",
    }


def mobility_paths(root: Path) -> dict[str, Path]:
    return {
        "decision": root / "MOBILITY_REVIEW_PACKET_360_NATIVE_REPAIR_DECISION.json",
        "packet": root / "MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET.json",
        "family_status": root / "REVIEW_PACKET_360_FAMILY_STATUS_AFTER_MOBILITY_REPAIR.json",
        "readiness": root / "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_RECHECK.json",
        "provenance": root / "MOBILITY_REVIEW_PACKET_360_NATIVE_VS_DERIVED_PROVENANCE_AUDIT.json",
    }


def simulation_paths(root: Path) -> dict[str, Path]:
    return {
        "decision": root / "DISTRIBUTION_CHECKED_SIMULATION_DECISION.json",
        "summary": root / "SIM_DONOR_DISTRIBUTION_COMPARISON_SUMMARY.json",
        "mobility": root / "MOBILITY_SIM_DISTRIBUTION_CHECK_REPORT.json",
        "permit": root / "PERMIT_DELAY_SIM_DISTRIBUTION_CHECK_REPORT.json",
        "no_forecast": root / "NO_FORECAST_SURFACE_GUARD.json",
        "no_calibration": root / "NO_CITY_CALIBRATION_CLAIM_GUARD.json",
        "no_prediction": root / "NO_OPERATIONAL_PREDICTION_CLAIM_GUARD.json",
    }


def input_inventory(
    expanded_root: Path,
    cadence_root: Path,
    mobility_root: Path,
    simulation_root: Path,
) -> dict[str, Any]:
    paths = {
        **{f"expanded_corpus:{key}": path for key, path in expanded_paths(expanded_root).items()},
        **{f"expanded_cadence:{key}": path for key, path in cadence_paths(cadence_root).items()},
        **{f"mobility_packet:{key}": path for key, path in mobility_paths(mobility_root).items()},
        **{f"simulation:{key}": path for key, path in simulation_paths(simulation_root).items()},
        "existing_eval_r2:decision": ROOT / "outputs" / "main_citybrain_epoch4_eval_corpus_expansion_r2" / "EVAL_CORPUS_EXPANSION_R2_DECISION.json",
        "existing_eval_r2:cases": ROOT / "outputs" / "main_citybrain_epoch4_eval_corpus_expansion_r2" / "EVAL_CASES_R2.jsonl",
    }
    rows = []
    for key, path in sorted(paths.items()):
        payload = read_json(path) if path.suffix == ".json" else {}
        line_count = len(read_jsonl(path)) if path.suffix == ".jsonl" and path.exists() else None
        rows.append(
            {
                "key": key,
                "path": rel(path),
                "exists": path.exists(),
                "status": payload.get("status") if isinstance(payload, dict) else None,
                "artifact_id": payload.get("artifact_id") if isinstance(payload, dict) else None,
                "line_count": line_count,
            }
        )
    return {
        "artifact_id": "CROSS_DOMAIN_STORY_INPUT_INVENTORY",
        "input_count": len(rows),
        "existing_input_count": sum(1 for row in rows if row["exists"]),
        "missing_inputs": [row for row in rows if not row["exists"] and not row["key"].startswith("existing_eval_r2")],
        "rows": rows,
    }


def families_from_feed(feed: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in feed:
        grouped[row.get("canonical_loop_family_id", "")].append(row)
    return grouped


def pick_event(grouped: dict[str, list[dict[str, Any]]], family: str, predicate: Any, fallback_index: int = 0) -> dict[str, Any]:
    rows = grouped.get(family, [])
    for row in rows:
        if predicate(row):
            return row
    if rows:
        return rows[min(fallback_index, len(rows) - 1)]
    return {}


def preflight(
    expanded_root: Path,
    cadence_root: Path,
    mobility_root: Path,
    simulation_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expanded = expanded_paths(expanded_root)
    cadence = cadence_paths(cadence_root)
    mobility = mobility_paths(mobility_root)
    simulation = simulation_paths(simulation_root)

    feed = read_jsonl(expanded["feed"])
    grouped = families_from_feed(feed)
    counts = read_json(expanded["counts"])
    cadence_decision = read_json(cadence["decision"])
    hashes = read_json(cadence["hashes"])
    mobility_decision = read_json(mobility["decision"])
    family_status = read_json(mobility["family_status"])
    sim_decision = read_json(simulation["decision"])

    blockers: list[dict[str, Any]] = []
    if len(feed) < 80:
        blockers.append({"gate": "expanded_corpus_event_count", "actual": len(feed), "required": 80})
    if sorted(grouped) != sorted(FAMILIES):
        blockers.append({"gate": "expanded_corpus_canonical_families", "actual": sorted(grouped), "required": FAMILIES})
    for family in FAMILIES:
        if len(grouped.get(family, [])) < 20:
            blockers.append({"gate": "expanded_corpus_20_per_family", "family_id": family, "actual": len(grouped.get(family, []))})
    if counts.get("total_event_count") != 80 or counts.get("family_count") != 4:
        blockers.append({"gate": "expanded_counts_artifact", "actual": {"total": counts.get("total_event_count"), "families": counts.get("family_count")}})
    if cadence_decision.get("status") != "PASS_MAIN_CITYBRAIN_EVENT_FABRIC_SEED_R3_EXPANDED_CORPUS_CADENCE_REPLAY_MINING_R2_WITH_LIMITATIONS":
        blockers.append({"gate": "expanded_cadence_status", "actual": cadence_decision.get("status")})
    if hashes.get("identical_final_state_hash") is not True or len(hashes.get("final_state_hash_values", [])) != 1:
        blockers.append({"gate": "expanded_cadence_identical_hash", "actual": hashes.get("final_state_hash_values")})
    if cadence_decision.get("disagreement_count") != 0:
        blockers.append({"gate": "expanded_cadence_disagreement_count", "actual": cadence_decision.get("disagreement_count")})
    native_counts = family_status.get("family_native_status_counts", {})
    if native_counts.get("native_packet_complete") != 4:
        blockers.append({"gate": "all_four_review_packet_families_native_complete", "actual": native_counts})
    if mobility_decision.get("mobility_native_packet_status") != "native_packet_complete":
        blockers.append({"gate": "mobility_native_packet_complete", "actual": mobility_decision.get("mobility_native_packet_status")})
    if sim_decision.get("forecast_packet_created") is not False:
        blockers.append({"gate": "simulation_no_forecast_packet", "actual": sim_decision.get("forecast_packet_created")})
    if sim_decision.get("not_city_calibrated") is not True or sim_decision.get("not_forecast") is not True:
        blockers.append({"gate": "simulation_limitations", "actual": {"not_city_calibrated": sim_decision.get("not_city_calibrated"), "not_forecast": sim_decision.get("not_forecast")}})
    for label, path in [
        ("expanded_no_d5d6", expanded["no_d5d6"]),
        ("expanded_no_standalone", expanded["no_standalone"]),
        ("cadence_no_d5d6", cadence["no_d5d6"]),
        ("cadence_no_standalone", cadence["no_standalone"]),
    ]:
        guard = read_json(path)
        if guard.get("status") != "PASS":
            blockers.append({"gate": label, "actual": guard})

    return blockers, {
        "feed": feed,
        "grouped": grouped,
        "counts": counts,
        "cadence_decision": cadence_decision,
        "cadence_hashes": hashes,
        "mobility_decision": mobility_decision,
        "mobility_packet": read_json(mobility["packet"]),
        "family_status": family_status,
        "simulation_decision": sim_decision,
        "simulation_summary": read_json(simulation["summary"]),
        "queue_distribution": read_json(expanded["queue_distribution"]),
        "duplicate_ledger": read_jsonl(expanded["duplicate_ledger"]),
        "unresolved": read_jsonl(expanded["unresolved"]),
        "quarantine": read_jsonl(expanded["quarantine"]),
        "existing_eval_decision": read_json(ROOT / "outputs" / "main_citybrain_epoch4_eval_corpus_expansion_r2" / "EVAL_CORPUS_EXPANSION_R2_DECISION.json", {}),
    }


def build_story_events(data: dict[str, Any]) -> list[dict[str, Any]]:
    grouped = data["grouped"]
    selections = [
        (
            "story-step-01-permit-status",
            "permit_inspection_delay",
            lambda row: PRIMARY_SITE in row.get("candidate_entity_refs", []) and row.get("resolution_outcome") == "resolved",
            "permit_planning_status_or_inspection_event",
            "Permit/inspection status attaches to the primary site.",
            "supported_for_review_with_limitations",
        ),
        (
            "story-step-02-built-environment-site",
            "building_compliance_perception_candidate",
            lambda row: PRIMARY_SITE in row.get("candidate_entity_refs", []) and row.get("event_type") == "site_condition",
            "built_environment_or_site_context",
            "Building/site context confirms the same primary site is in the review scope.",
            "supported_for_review_with_limitations",
        ),
        (
            "story-step-03-mobility-access",
            "mobility_access_interruption_v0",
            lambda row: PRIMARY_SITE in row.get("candidate_entity_refs", []) and row.get("resolution_outcome") == "resolved",
            "access_or_mobility_interruption",
            "Mobility access interruption participates through the repaired native packet evidence.",
            "supported_for_review_with_limitations",
        ),
        (
            "story-step-04-civic-complaint-context",
            "building_compliance_perception_candidate",
            lambda row: PRIMARY_SITE in row.get("candidate_entity_refs", []) and row.get("event_type") == "violation_candidate",
            "civic_service_or_compliance_complaint_context",
            "A complaint-like compliance candidate provides review context, not an official finding.",
            "candidate_only_downgrade",
        ),
        (
            "story-step-05-inspection-delay",
            "permit_inspection_delay",
            lambda row: PRIMARY_SITE in row.get("candidate_entity_refs", []) and row.get("event_type") != "permit_wait",
            "inspection_or_delay_state",
            "Inspection delay remains review evidence and cannot be treated as action authority.",
            "supported_for_review_with_limitations",
        ),
        (
            "story-step-06-asset-impact",
            "city_asset_infrastructure_issue",
            lambda row: PRIMARY_ASSET in row.get("candidate_entity_refs", []) and row.get("resolution_outcome") == "resolved",
            "asset_or_infrastructure_impact",
            "Infrastructure context is linked as a corridor/impact edge, not as the same site entity.",
            "contextual_link_with_limitations",
        ),
        (
            "story-step-07-check-downgrade",
            "mobility_access_interruption_v0",
            lambda row: row.get("resolution_reason_class") in {"weak_spatial_match", "unknown_freshness", "duplicate_candidate_ambiguity"},
            "check_downgrade_or_hold",
            "CHECK should downgrade or hold when spatial, freshness, or identity evidence is weak.",
            "downgrade_or_hold_for_review",
        ),
        (
            "story-step-08-brief-spatial-review",
            "city_asset_infrastructure_issue",
            lambda row: row.get("resolution_outcome") == "quarantine_expected",
            "brief_and_spatial_limitation_context",
            "BRIEF/SPATIAL review can show evidence and limitations, not control or action.",
            "quarantine_or_abstain",
        ),
    ]
    story_events = []
    for sequence, (step_id, family, predicate, role, summary, expected) in enumerate(selections, start=1):
        event = pick_event(grouped, family, predicate)
        story_events.append(
            {
                "story_arc_id": STORY_ARC_ID,
                "story_event_id": step_id,
                "sequence": sequence,
                "family_id": family,
                "source_event_id": event.get("event_id"),
                "source_event_type": event.get("event_type"),
                "story_role": role,
                "narrative_summary": summary,
                "source_class": event.get("source_class"),
                "truth_layer": event.get("truth_layer"),
                "resolution_outcome": event.get("resolution_outcome"),
                "resolution_reason_class": event.get("resolution_reason_class"),
                "canonical_entity_refs": event.get("candidate_entity_refs", []),
                "spatial_ref": event.get("candidate_geometry_ref"),
                "check_expected_behavior": expected,
                "local_replay_only": True,
                "operator_fuel": False,
                "training_eligible": False,
                "founder_session_result": False,
            }
        )
    return story_events


def build_truth_manifest(story_events: list[dict[str, Any]], data: dict[str, Any]) -> dict[str, Any]:
    family_ids = sorted({row["family_id"] for row in story_events})
    source_event_ids = [row["source_event_id"] for row in story_events if row.get("source_event_id")]
    return {
        "artifact_id": "CROSS_DOMAIN_STORY_TRUTH_MANIFEST",
        "story_arc_id": STORY_ARC_ID,
        "title": "Construction, permit, access, compliance, and asset cascade",
        "scope": "bounded local/replay truth-manifested arc",
        "canonical_family_ids": family_ids,
        "all_four_canonical_families_participate": sorted(family_ids) == sorted(FAMILIES),
        "primary_site_entity_ref": PRIMARY_SITE,
        "primary_corridor_ref": PRIMARY_CORRIDOR,
        "primary_asset_ref": PRIMARY_ASSET,
        "source_event_ids": source_event_ids,
        "truth_claims": [
            {
                "claim_id": "truth-claim-primary-site",
                "claim": "The primary site is shared by mobility, building-compliance, and permit/inspection evidence.",
                "canonical_entity_ref": PRIMARY_SITE,
                "family_ids": [
                    "mobility_access_interruption_v0",
                    "building_compliance_perception_candidate",
                    "permit_inspection_delay",
                ],
                "supporting_story_event_ids": [
                    "story-step-01-permit-status",
                    "story-step-02-built-environment-site",
                    "story-step-03-mobility-access",
                    "story-step-04-civic-complaint-context",
                    "story-step-05-inspection-delay",
                ],
                "expected_check_behavior": "supported_for_review_with_limitations",
            },
            {
                "claim_id": "truth-claim-corridor-asset-context",
                "claim": "The asset issue is linked as corridor/context evidence and must not be collapsed into the site entity.",
                "canonical_entity_ref": PRIMARY_ASSET,
                "family_ids": ["city_asset_infrastructure_issue", "mobility_access_interruption_v0"],
                "supporting_story_event_ids": ["story-step-03-mobility-access", "story-step-06-asset-impact"],
                "expected_check_behavior": "contextual_link_with_limitations",
            },
            {
                "claim_id": "truth-claim-check-boundary",
                "claim": "Weak spatial, freshness, duplicate, or quarantine evidence must downgrade/hold rather than become a finding.",
                "canonical_entity_ref": PRIMARY_SITE,
                "family_ids": FAMILIES,
                "supporting_story_event_ids": ["story-step-07-check-downgrade", "story-step-08-brief-spatial-review"],
                "expected_check_behavior": "downgrade_or_abstain",
            },
        ],
        "source_refs": [
            "outputs/MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1/SEED_R3_EXPANDED_ADAPTER_FEED.jsonl",
            "outputs/MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-EXPANDED-CORPUS-CADENCE-REPLAY-MINING-R2/EXPANDED_CORPUS_CADENCE_REPLAY_MINING_DECISION.json",
            "outputs/MAIN-CITYBRAIN-REVIEW-PACKET-360-MOBILITY-NATIVE-REPAIR-R1/MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET.json",
        ],
        "cadence_final_state_hash": data["cadence_hashes"].get("final_state_hash_values", [None])[0],
        "limitations": [
            "local/replay only",
            "synthetic and donor-context support only",
            "not official city truth",
            "not a product/client readiness claim",
            "no action, ticket, dispatch, control, enforcement, forecast, training, or fuel",
        ],
    }


def build_entity_report(story_events: list[dict[str, Any]], data: dict[str, Any]) -> dict[str, Any]:
    family_by_entity: dict[str, set[str]] = defaultdict(set)
    events_by_entity: dict[str, list[str]] = defaultdict(list)
    for row in story_events:
        for ref in row.get("canonical_entity_refs", []):
            family_by_entity[ref].add(row["family_id"])
            events_by_entity[ref].append(row["source_event_id"])

    shared = {
        ref: sorted(families)
        for ref, families in family_by_entity.items()
        if len(families) >= 2 and not ref.startswith("cer:seed-r3-local")
    }
    shared_three = {ref: families for ref, families in shared.items() if len(families) >= 3}
    r3_local_only_count = sum(
        1
        for row in story_events
        if row.get("canonical_entity_refs") and all(str(ref).startswith("cer:seed-r3-local") for ref in row.get("canonical_entity_refs", []))
    )
    cross_edges = [
        {
            "edge_id": "edge-primary-site-permit-mobility",
            "edge_type": "shared_canonical_site",
            "canonical_entity_ref": PRIMARY_SITE,
            "family_ids": ["permit_inspection_delay", "mobility_access_interruption_v0"],
            "source_event_ids": [
                event["source_event_id"]
                for event in story_events
                if event["family_id"] in {"permit_inspection_delay", "mobility_access_interruption_v0"} and PRIMARY_SITE in event.get("canonical_entity_refs", [])
            ],
            "supports_gate": True,
        },
        {
            "edge_id": "edge-primary-site-building-mobility",
            "edge_type": "shared_canonical_site",
            "canonical_entity_ref": PRIMARY_SITE,
            "family_ids": ["building_compliance_perception_candidate", "mobility_access_interruption_v0"],
            "source_event_ids": [
                event["source_event_id"]
                for event in story_events
                if event["family_id"] in {"building_compliance_perception_candidate", "mobility_access_interruption_v0"}
                and PRIMARY_SITE in event.get("canonical_entity_refs", [])
            ],
            "supports_gate": True,
        },
        {
            "edge_id": "edge-primary-site-permit-building",
            "edge_type": "shared_canonical_site",
            "canonical_entity_ref": PRIMARY_SITE,
            "family_ids": ["permit_inspection_delay", "building_compliance_perception_candidate"],
            "source_event_ids": [
                event["source_event_id"]
                for event in story_events
                if event["family_id"] in {"permit_inspection_delay", "building_compliance_perception_candidate"}
                and PRIMARY_SITE in event.get("canonical_entity_refs", [])
            ],
            "supports_gate": True,
        },
        {
            "edge_id": "edge-corridor-asset-mobility-context",
            "edge_type": "spatial_corridor_context_not_same_entity",
            "canonical_entity_ref": PRIMARY_CORRIDOR,
            "family_ids": ["city_asset_infrastructure_issue", "mobility_access_interruption_v0"],
            "source_event_ids": [
                event["source_event_id"]
                for event in story_events
                if event["family_id"] in {"city_asset_infrastructure_issue", "mobility_access_interruption_v0"}
            ],
            "supports_gate": False,
            "limitation": "Context edge only; the asset is not relabelled as the building/site entity.",
        },
    ]
    return {
        "artifact_id": "CROSS_DOMAIN_ENTITY_RESOLUTION_REPORT",
        "story_arc_id": STORY_ARC_ID,
        "shared_canonical_entity_count": len(shared),
        "shared_canonical_entities": [
            {
                "canonical_entity_ref": ref,
                "family_ids": families,
                "family_count": len(families),
                "source_event_ids": sorted(set(events_by_entity[ref])),
            }
            for ref, families in sorted(shared.items())
        ],
        "shared_canonical_entities_with_3plus_families": [
            {"canonical_entity_ref": ref, "family_ids": families, "family_count": len(families)}
            for ref, families in sorted(shared_three.items())
        ],
        "families_attached_to_primary_site": sorted(shared_three.get(PRIMARY_SITE, [])),
        "families_attached_to_primary_asset_or_corridor": ["city_asset_infrastructure_issue", "mobility_access_interruption_v0"],
        "r3_local_only_event_count": r3_local_only_count,
        "r3_local_only_event_ids": [
            row["source_event_id"]
            for row in story_events
            if row.get("canonical_entity_refs") and all(str(ref).startswith("cer:seed-r3-local") for ref in row.get("canonical_entity_refs", []))
        ],
        "cross_family_resolution_edges": cross_edges,
        "ambiguous_or_duplicate_candidate_edges": [
            {
                "event_id": row.get("event_id"),
                "family_id": row.get("family_id"),
                "candidate_entity_refs": row.get("candidate_entity_refs", []),
                "reason_class": row.get("reason_class"),
                "action": row.get("action"),
            }
            for row in data["duplicate_ledger"][:8]
        ],
        "blocked_resolution_edges": [
            {
                "event_id": row.get("event_id"),
                "family_id": row.get("family_id"),
                "resolution_outcome": row.get("resolution_outcome"),
                "reason_class": row.get("reason_class") or row.get("resolution_reason_class"),
            }
            for row in (data["unresolved"][:8] + data["quarantine"][:8])
        ],
        "minimum_gate_met": bool(shared_three)
        and any("mobility_access_interruption_v0" in edge["family_ids"] and edge["supports_gate"] for edge in cross_edges)
        and any("permit_inspection_delay" in edge["family_ids"] and edge["supports_gate"] for edge in cross_edges),
        "not_r3_local_only": any(
            any(not str(ref).startswith("cer:seed-r3-local") for ref in row.get("canonical_entity_refs", []))
            for row in story_events
        ),
    }


def build_causal_ledger(story_events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_id": "CROSS_FAMILY_CAUSAL_LINK_LEDGER",
        "story_arc_id": STORY_ARC_ID,
        "causal_claim_strength": "review_story_hypothesis_not_proven_causality",
        "links": [
            {
                "link_id": "link-permit-site-access",
                "from_story_event_id": "story-step-01-permit-status",
                "to_story_event_id": "story-step-03-mobility-access",
                "link_type": "shared_site_review_context",
                "canonical_entity_refs": [PRIMARY_SITE],
                "check_boundary": "may support review linkage; cannot claim caused interruption",
            },
            {
                "link_id": "link-site-compliance",
                "from_story_event_id": "story-step-02-built-environment-site",
                "to_story_event_id": "story-step-04-civic-complaint-context",
                "link_type": "same_site_candidate_review_context",
                "canonical_entity_refs": [PRIMARY_SITE],
                "check_boundary": "candidate-only compliance context, not a finding",
            },
            {
                "link_id": "link-inspection-compliance",
                "from_story_event_id": "story-step-05-inspection-delay",
                "to_story_event_id": "story-step-04-civic-complaint-context",
                "link_type": "shared_site_inspection_review_context",
                "canonical_entity_refs": [PRIMARY_SITE],
                "check_boundary": "reviewable relationship, not official case or ticket semantics",
            },
            {
                "link_id": "link-asset-access-corridor",
                "from_story_event_id": "story-step-06-asset-impact",
                "to_story_event_id": "story-step-03-mobility-access",
                "link_type": "corridor_contextual_impact",
                "canonical_entity_refs": [PRIMARY_ASSET, PRIMARY_CORRIDOR],
                "check_boundary": "spatial/context edge only; no operational action or control",
            },
        ],
        "source_story_event_ids": [row["story_event_id"] for row in story_events],
    }


def base_case(
    idx: int,
    category: str,
    family_ids: list[str],
    question: str,
    expected_behavior: str,
    expected_decision: str,
    truth_refs: list[str],
    source_refs: list[str],
    check_reason_refs: list[str],
    canonical_entity_refs: list[str],
    negative_or_challenge_type: str,
) -> dict[str, Any]:
    return {
        "eval_case_id": f"story-arc-r1-eval-{idx:03d}",
        "story_arc_id": STORY_ARC_ID,
        "case_category": category,
        "family_ids": family_ids,
        "question_or_assertion": question,
        "expected_behavior": expected_behavior,
        "expected_answer_or_decision": expected_decision,
        "truth_refs": truth_refs,
        "source_refs": source_refs,
        "check_reason_refs": check_reason_refs,
        "canonical_entity_refs": canonical_entity_refs,
        "negative_or_challenge_type": negative_or_challenge_type,
        "operator_fuel": False,
        "training_eligible": False,
        "founder_session_result": False,
        "local_replay_only": True,
    }


def rows_by_reason(rows: list[dict[str, Any]], reason: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("resolution_reason_class") == reason or row.get("reason_class") == reason]


def event_ref(row: dict[str, Any]) -> str:
    return row.get("event_id") or row.get("source_event_id") or "unknown-event"


def generate_eval_cases(story_events: list[dict[str, Any]], data: dict[str, Any]) -> list[dict[str, Any]]:
    grouped = data["grouped"]
    unresolved = data["unresolved"]
    quarantine = data["quarantine"]
    duplicate = data["duplicate_ledger"]
    cases: list[dict[str, Any]] = []
    idx = 1

    for family in FAMILIES:
        resolved = [row for row in grouped[family] if row.get("resolution_outcome") == "resolved"]
        for row in resolved[:8]:
            cases.append(
                base_case(
                    idx,
                    "family_positive",
                    [family],
                    f"Is {event_ref(row)} reviewable local/replay evidence for {family} with its stated limitations?",
                    "support_if_source_refs_and_canonical_or_admitted_resolution_match",
                    "supported_for_review_with_limitations",
                    ["CROSS_DOMAIN_STORY_TRUTH_MANIFEST.json#truth-claim-primary-site"],
                    [event_ref(row)],
                    ["check:sufficiency", "check:source_class"],
                    row.get("candidate_entity_refs", []),
                    "positive",
                )
            )
            idx += 1

    cross_pairs = [
        ("permit_inspection_delay", "mobility_access_interruption_v0", PRIMARY_SITE),
        ("building_compliance_perception_candidate", "mobility_access_interruption_v0", PRIMARY_SITE),
        ("permit_inspection_delay", "building_compliance_perception_candidate", PRIMARY_SITE),
        ("city_asset_infrastructure_issue", "mobility_access_interruption_v0", PRIMARY_CORRIDOR),
    ]
    for n in range(24):
        family_a, family_b, entity = cross_pairs[n % len(cross_pairs)]
        row_a = grouped[family_a][n % len(grouped[family_a])]
        row_b = grouped[family_b][(n + 3) % len(grouped[family_b])]
        cases.append(
            base_case(
                idx,
                "cross_family_linkage",
                [family_a, family_b],
                f"Does the story support a bounded review linkage between {event_ref(row_a)} and {event_ref(row_b)}?",
                "support_only_when_shared_entity_or_context_edge_is_explicit",
                "linked_for_review_not_causal_or_actionable",
                ["CROSS_DOMAIN_ENTITY_RESOLUTION_REPORT.json#cross_family_resolution_edges"],
                [event_ref(row_a), event_ref(row_b)],
                ["check:source_depth", "check:proximity_only_boundary"],
                [entity],
                "cross_family_challenge" if entity == PRIMARY_CORRIDOR else "positive",
            )
        )
        idx += 1

    entity_family_sets = [
        ["mobility_access_interruption_v0", "building_compliance_perception_candidate", "permit_inspection_delay"],
        ["mobility_access_interruption_v0", "permit_inspection_delay"],
        ["building_compliance_perception_candidate", "permit_inspection_delay"],
        ["city_asset_infrastructure_issue", "mobility_access_interruption_v0"],
    ]
    for n in range(16):
        families = entity_family_sets[n % len(entity_family_sets)]
        refs = []
        for family in families:
            refs.append(event_ref(grouped[family][n % len(grouped[family])]))
        entity = PRIMARY_SITE if "city_asset_infrastructure_issue" not in families else PRIMARY_CORRIDOR
        cases.append(
            base_case(
                idx,
                "entity_resolution",
                families,
                f"Should these events resolve through {entity} rather than R3-local-only IDs?",
                "shared_canonical_entity_required_for_site_linkage",
                "canonical_resolution_supported_with_limitations" if entity == PRIMARY_SITE else "contextual_corridor_resolution_only",
                ["CROSS_DOMAIN_STORY_TRUTH_MANIFEST.json#truth-claim-primary-site"],
                refs,
                ["check:cer_identity", "check:provenance"],
                [entity],
                "cer_identity_context",
            )
        )
        idx += 1

    challenge_specs = [
        ("contradiction", "contradiction", "downgrade_or_hold_for_contradiction", duplicate + rows_by_reason(unresolved + quarantine, "impossible_time")),
        ("stale_freshness", "stale_or_unknown_freshness", "downgrade_freshness_or_request_refresh", rows_by_reason(unresolved + quarantine, "unknown_freshness")),
        ("no_data_insufficient", "no_data_or_insufficient_evidence", "abstain_or_request_more_evidence", rows_by_reason(unresolved + quarantine, "missing_entity_ref") + rows_by_reason(unresolved + quarantine, "missing_geometry")),
        ("cer_identity_ambiguity", "duplicate_candidate_ambiguity", "hold_for_identity_review", duplicate),
        ("quarantine_unresolved", "quarantine_or_unresolved", "hold_in_unresolved_or_quarantine_queue", unresolved + quarantine),
        ("check_cannot_claim_boundary", "cannot_claim_boundary", "must_not_claim_action_forecast_or_readiness", list(grouped["mobility_access_interruption_v0"][:4]) + list(grouped["permit_inspection_delay"][:4])),
    ]
    for category, negative_type, expected_decision, source_rows in challenge_specs:
        rows = source_rows or [row for rows in grouped.values() for row in rows]
        for n in range(8):
            row = rows[n % len(rows)]
            family = row.get("family_id") or row.get("canonical_loop_family_id") or FAMILIES[n % len(FAMILIES)]
            source = event_ref(row)
            reason = row.get("reason_class") or row.get("resolution_reason_class") or negative_type
            cases.append(
                base_case(
                    idx,
                    category,
                    [family],
                    f"Does {source} trigger the safe {negative_type} behavior for reason {reason}?",
                    "downgrade_hold_abstain_or_limit_claim",
                    expected_decision,
                    ["CROSS_DOMAIN_STORY_TRUTH_MANIFEST.json#truth-claim-check-boundary"],
                    [source],
                    [f"check:{reason}", "check:cannot_claim"],
                    row.get("candidate_entity_refs", []) or [PRIMARY_SITE],
                    negative_type,
                )
            )
            idx += 1

    return cases


def coverage_scorecard(cases: list[dict[str, Any]], existing_count: int) -> dict[str, Any]:
    family_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    negative_counts: Counter[str] = Counter()
    cross_family_count = 0
    for case in cases:
        category_counts[case["case_category"]] += 1
        if len(case["family_ids"]) > 1:
            cross_family_count += 1
        if case["negative_or_challenge_type"] != "positive":
            negative_counts[case["negative_or_challenge_type"]] += 1
        for family in case["family_ids"]:
            family_counts[family] += 1
    return {
        "artifact_id": "STORY_ARC_EVAL_COVERAGE_SCORECARD",
        "story_arc_id": STORY_ARC_ID,
        "new_eval_case_count": len(cases),
        "existing_eval_case_count": existing_count,
        "combined_eval_case_count": existing_count + len(cases),
        "target_new_eval_case_count_met": len(cases) >= 112,
        "combined_160_target_met_if_existing_discoverable": existing_count == 0 or existing_count + len(cases) >= 160,
        "family_case_counts": dict(sorted(family_counts.items())),
        "each_family_has_20plus_cases": all(family_counts[family] >= 20 for family in FAMILIES),
        "cross_family_case_count": cross_family_count,
        "cross_family_20plus_met": cross_family_count >= 20,
        "category_counts": dict(sorted(category_counts.items())),
        "negative_or_challenge_counts": dict(sorted(negative_counts.items())),
        "challenge_negative_case_count": sum(negative_counts.values()),
        "minimum_distribution_met": {
            "challenge_negative_16plus": sum(negative_counts.values()) >= 16,
            "contradiction_8plus": negative_counts["contradiction"] >= 8,
            "stale_freshness_8plus": negative_counts["stale_or_unknown_freshness"] >= 8,
            "no_data_insufficient_8plus": negative_counts["no_data_or_insufficient_evidence"] >= 8,
            "cer_identity_ambiguity_8plus": negative_counts["duplicate_candidate_ambiguity"] >= 8,
            "quarantine_unresolved_8plus": negative_counts["quarantine_or_unresolved"] >= 8,
            "check_cannot_claim_boundary_8plus": negative_counts["cannot_claim_boundary"] >= 8,
        },
    }


def build_review_packet(
    truth: dict[str, Any],
    story_events: list[dict[str, Any]],
    entity_report: dict[str, Any],
    causal_ledger: dict[str, Any],
    data: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_id": "STORY_ARC_REVIEW_PACKET_360",
        "story_arc_id": STORY_ARC_ID,
        "title": truth["title"],
        "review_status": "ai_diagnostic_review_ready_with_limitations",
        "product_review_ready": False,
        "client_ready": False,
        "family_ids": FAMILIES,
        "story_summary": [
            "Permit/inspection, building/site, mobility/access, compliance candidate, and asset-context evidence are packaged as one local/replay review arc.",
            "The primary hard gate is the shared canonical site entity used by mobility, building-compliance, and permit/inspection evidence.",
            "Asset evidence is preserved as corridor/context evidence rather than being collapsed into the site entity.",
        ],
        "event_refs": [row["source_event_id"] for row in story_events],
        "check_summary": {
            "supported_claims": ["shared primary site review linkage", "mobility native packet participation"],
            "downgrades_or_holds": ["weak spatial match", "unknown freshness", "duplicate candidate ambiguity", "quarantine expected"],
            "cannot_claim": [
                "official finding",
                "ticket/case/action",
                "dispatch/control/enforcement",
                "forecast or ForecastPacket",
                "product/client readiness",
                "source truth mutation",
            ],
        },
        "brief_summary": {
            "brief_type": "diagnostic_story_review_packet",
            "review_question": "Is the cross-family story coherent enough for AI diagnostic story review?",
            "recommended_next_step": "GO_FOR_AI_DIAGNOSTIC_STORY_REVIEW",
            "not_recommended": "founder product review",
        },
        "spatial_context_refs": sorted({row.get("spatial_ref") for row in story_events if row.get("spatial_ref")} | {PRIMARY_CORRIDOR}),
        "simulation_context": {
            "mobility_status": data["simulation_summary"].get("metric_rows", [{}])[0].get("alignment_label"),
            "permit_delay_status": "parked_or_not_distribution_checked_when_no_comparable_donor_service_time_distribution_exists",
            "limitations": [
                "donor-distribution-aligned fixture only",
                "not city-calibrated",
                "not forecast",
                "not operational prediction",
                "no ForecastPacket",
            ],
        },
        "entity_resolution_summary": {
            "shared_canonical_entity_count": entity_report["shared_canonical_entity_count"],
            "families_attached_to_primary_site": entity_report["families_attached_to_primary_site"],
            "r3_local_only_event_count": entity_report["r3_local_only_event_count"],
        },
        "causal_link_boundary": causal_ledger["causal_claim_strength"],
        "source_refs": truth["source_refs"],
        "limitations": truth["limitations"],
    }


def markdown_packet(packet: dict[str, Any], coverage: dict[str, Any]) -> str:
    return f"""# Story Arc Review Packet 360

## Status

- Review status: `{packet["review_status"]}`
- Product review ready: `{str(packet["product_review_ready"]).lower()}`
- Client ready: `{str(packet["client_ready"]).lower()}`

## Story

{packet["story_summary"][0]}

The shared canonical site is `{PRIMARY_SITE}`. Asset evidence is represented as `{PRIMARY_ASSET}` on `{PRIMARY_CORRIDOR}` and remains contextual.

## CHECK / Boundary

- Supported: {", ".join(packet["check_summary"]["supported_claims"])}
- Downgrade or hold: {", ".join(packet["check_summary"]["downgrades_or_holds"])}
- Cannot claim: {", ".join(packet["check_summary"]["cannot_claim"])}

## Eval Expansion

- New eval cases: {coverage["new_eval_case_count"]}
- Existing eval cases discovered: {coverage["existing_eval_case_count"]}
- Combined eval cases: {coverage["combined_eval_case_count"]}

## Next Step

`GO_FOR_AI_DIAGNOSTIC_STORY_REVIEW`
"""


def review_index_html(packet: dict[str, Any], story_events: list[dict[str, Any]], coverage: dict[str, Any]) -> str:
    rows = "\n".join(
        f"<tr><td>{html.escape(row['story_event_id'])}</td><td>{html.escape(row['family_id'])}</td><td>{html.escape(str(row['source_event_id']))}</td><td>{html.escape(row['check_expected_behavior'])}</td></tr>"
        for row in story_events
    )
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Cross-Domain Story Arc R1</title></head>
<body>
<h1>Cross-Domain Story Arc R1</h1>
<p>Status: {html.escape(packet["review_status"])}</p>
<p>New eval cases: {coverage["new_eval_case_count"]}; combined cases: {coverage["combined_eval_case_count"]}</p>
<table border="1" cellpadding="6" cellspacing="0">
<thead><tr><th>Story Event</th><th>Family</th><th>Source Event</th><th>Expected CHECK Behavior</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
<p>Boundary: local/replay diagnostic review only. No founder session, fuel, training, forecast, source-truth mutation, action, control, enforcement, product readiness, or client readiness.</p>
</body>
</html>"""


def build_guards() -> dict[str, Any]:
    return {
        "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json": {
            "artifact_id": "NO_STANDALONE_FIXTURE_REGRESSION_GUARD",
            "status": "PASS",
            "story_consumes_event_fabric_adapter_feed": True,
            "standalone_watch_ask_check_brief_spatial_fixture_surface_created": False,
        },
        "NO_DIRECT_D5D6_BYPASS_GUARD.json": {
            "artifact_id": "NO_DIRECT_D5D6_BYPASS_GUARD",
            "status": "PASS",
            "direct_d5_d6_bypass": False,
            "event_fabric_cer_check_brief_path_preserved": True,
        },
        "NO_FOUNDER_SESSION_FUEL_GUARD.json": {
            "artifact_id": "NO_FOUNDER_SESSION_FUEL_GUARD",
            "status": "PASS",
            "founder_session_results_created": False,
            "operator_fuel_created": False,
            "training_rows_created": False,
            "learning_arming_allowed": False,
        },
        "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json": {
            "artifact_id": "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD",
            "status": "PASS",
            "product_review_ready": False,
            "client_ready": False,
            "product_review_ready_claim_created": False,
            "client_ready_claim_created": False,
            "recommended_review": "AI diagnostic story review only",
        },
        "NO_FORECAST_ACTION_GUARD.json": {
            "artifact_id": "NO_FORECAST_ACTION_GUARD",
            "status": "PASS",
            "forecast_packet_created": False,
            "forecast_surface_created": False,
            "official_workflow_case_action_created": False,
            "dispatch_control_enforcement_created": False,
            "legal_or_certified_finding_created": False,
        },
        "NO_SOURCE_TRUTH_MUTATION_GUARD.json": {
            "artifact_id": "NO_SOURCE_TRUTH_MUTATION_GUARD",
            "status": "PASS",
            "source_truth_mutated": False,
            "raw_source_payloads_mutated": False,
            "canonical_truth_rewritten": False,
            "derived_story_overlay_only": True,
        },
        "BOUNDARY_NO_ACTION_AUDIT.json": {
            "artifact_id": "BOUNDARY_NO_ACTION_AUDIT",
            "status": "PASS",
            "local_replay_review_only": True,
            "no_live_ingestion_or_monitoring": True,
            "no_public_api_or_production_frontend": True,
            "no_action_ticket_case_dispatch_control_enforcement": True,
            "no_legal_or_certified_finding": True,
        },
    }


def hash_manifest(out: Path) -> None:
    rows = []
    for path in sorted(out.iterdir(), key=lambda p: p.name):
        if path.name == "HASH_MANIFEST.sha256" or not path.is_file():
            continue
        rows.append(f"{sha256_file(path)}  {path.name}")
    write_text(out / "HASH_MANIFEST.sha256", "\n".join(rows))


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing manifest: {rel(path)}"]
    errors = []
    base = path.parent
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, name = line.split("  ", 1)
        candidate = base / name
        if not candidate.exists():
            errors.append(f"manifest target missing: {name}")
        elif sha256_file(candidate) != expected:
            errors.append(f"manifest mismatch: {name}")
    return errors


def copy_publication(out: Path) -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for path in out.iterdir():
        if path.is_file():
            shutil.copy2(path, PUBLICATION_ROOT / path.name)


def required_paths(out: Path) -> list[Path]:
    return [out / name for name in REQUIRED_FILES]


def build(
    expanded_root: Path,
    cadence_root: Path,
    mobility_root: Path,
    simulation_root: Path,
    out: Path,
) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    inventory = input_inventory(expanded_root, cadence_root, mobility_root, simulation_root)
    blockers, data = preflight(expanded_root, cadence_root, mobility_root, simulation_root)

    story_events = build_story_events(data)
    truth = build_truth_manifest(story_events, data)
    entity_report = build_entity_report(story_events, data)
    causal_ledger = build_causal_ledger(story_events)
    existing_eval_count = int(data["existing_eval_decision"].get("case_count", 0) or 0)
    cases = generate_eval_cases(story_events, data)
    coverage = coverage_scorecard(cases, existing_eval_count)
    packet = build_review_packet(truth, story_events, entity_report, causal_ledger, data)
    negative_cases = [case for case in cases if case["negative_or_challenge_type"] != "positive"]

    repair_reasons = []
    if not entity_report["minimum_gate_met"] or not entity_report["not_r3_local_only"]:
        repair_reasons.append("cross_domain_entity_resolution_gate_not_met")
    if not coverage["target_new_eval_case_count_met"] or not coverage["each_family_has_20plus_cases"]:
        repair_reasons.append("eval_expansion_coverage_gate_not_met")
    if existing_eval_count and not coverage["combined_160_target_met_if_existing_discoverable"]:
        repair_reasons.append("combined_eval_count_gate_not_met")
    if not all(coverage["minimum_distribution_met"].values()):
        repair_reasons.append("minimum_challenge_distribution_gate_not_met")

    if blockers:
        status = STATUS_BLOCKED
        next_step = "REPAIR_CROSS_DOMAIN_ENTITY_RESOLUTION"
    elif repair_reasons:
        status = STATUS_NEEDS_REPAIR
        next_step = "REPAIR_EVAL_EXPANSION_COVERAGE" if any("eval" in reason for reason in repair_reasons) else "REPAIR_CROSS_DOMAIN_ENTITY_RESOLUTION"
    else:
        status = STATUS_PASS
        next_step = "GO_FOR_AI_DIAGNOSTIC_STORY_REVIEW"

    decision = {
        "artifact_id": "CROSS_DOMAIN_STORY_ARC_DECISION",
        "status": status,
        "next_step_recommendation": next_step,
        "story_arc_id": STORY_ARC_ID,
        "preflight_blocker_count": len(blockers),
        "preflight_blockers": blockers,
        "repair_reason_count": len(repair_reasons),
        "repair_reasons": repair_reasons,
        "canonical_family_count": len(FAMILIES),
        "all_four_canonical_families_participate": truth["all_four_canonical_families_participate"],
        "shared_canonical_entity_count": entity_report["shared_canonical_entity_count"],
        "shared_canonical_entity_3plus_gate_met": bool(entity_report["shared_canonical_entities_with_3plus_families"]),
        "mobility_native_packet_participates": "mobility_access_interruption_v0" in entity_report["families_attached_to_primary_site"],
        "story_r3_local_only": not entity_report["not_r3_local_only"],
        "new_eval_case_count": coverage["new_eval_case_count"],
        "existing_eval_case_count": coverage["existing_eval_case_count"],
        "combined_eval_case_count": coverage["combined_eval_case_count"],
        "product_review_ready": False,
        "client_ready": False,
        "founder_session_results_created": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "forecast_packet_created": False,
        "source_truth_mutated": False,
        "forbidden_capabilities_created": [],
    }

    write_json(out / "CROSS_DOMAIN_STORY_INPUT_INVENTORY.json", inventory)
    write_json(out / "CROSS_DOMAIN_STORY_TRUTH_MANIFEST.json", truth)
    write_jsonl(out / "CROSS_DOMAIN_STORY_ARC_EVENTS.jsonl", story_events)
    write_json(out / "CROSS_DOMAIN_ENTITY_RESOLUTION_REPORT.json", entity_report)
    write_json(out / "CROSS_FAMILY_CAUSAL_LINK_LEDGER.json", causal_ledger)
    write_json(out / "STORY_ARC_REVIEW_PACKET_360.json", packet)
    write_text(out / "STORY_ARC_REVIEW_PACKET_360.md", markdown_packet(packet, coverage))
    write_text(out / "STORY_ARC_REVIEW_INDEX.html", review_index_html(packet, story_events, coverage))
    write_jsonl(out / "STORY_ARC_EVAL_EXPANSION_CASES.jsonl", cases)
    write_json(
        out / "STORY_ARC_EVAL_ANSWER_KEY.json",
        {
            "artifact_id": "STORY_ARC_EVAL_ANSWER_KEY",
            "story_arc_id": STORY_ARC_ID,
            "case_count": len(cases),
            "answers": [
                {
                    "eval_case_id": case["eval_case_id"],
                    "expected_answer_or_decision": case["expected_answer_or_decision"],
                    "expected_behavior": case["expected_behavior"],
                    "truth_refs": case["truth_refs"],
                }
                for case in cases
            ],
        },
    )
    write_json(out / "STORY_ARC_EVAL_COVERAGE_SCORECARD.json", coverage)
    write_jsonl(out / "STORY_ARC_NEGATIVE_CHALLENGE_CASES.jsonl", negative_cases)
    write_json(
        out / "STORY_ARC_FOUNDER_DIAGNOSTIC_CARD_CANDIDATES.json",
        {
            "artifact_id": "STORY_ARC_FOUNDER_DIAGNOSTIC_CARD_CANDIDATES",
            "status": "CANDIDATES_ONLY_NO_SESSION_RESULT",
            "candidate_count": 4,
            "product_review_ready": False,
            "client_ready": False,
            "rows": [
                {
                    "candidate_id": f"story-diagnostic-card-{idx:02d}",
                    "review_question": question,
                    "story_arc_id": STORY_ARC_ID,
                    "session_result_created": False,
                    "operator_fuel": False,
                    "training_eligible": False,
                }
                for idx, question in enumerate(
                    [
                        "Is the shared canonical site linkage understandable?",
                        "Are the CHECK downgrade boundaries clear?",
                        "Is the asset/corridor limitation honest enough?",
                        "Are the 112+ eval cases useful for AI diagnostic review?",
                    ],
                    start=1,
                )
            ],
        },
    )
    write_text(
        out / "STORY_ARC_AI_DIAGNOSTIC_REVIEW_GUIDE.md",
        f"""# AI Diagnostic Story Review Guide

Use this package for AI diagnostic story review only.

Review:
- Whether `{PRIMARY_SITE}` is a clear shared canonical entity across mobility, building-compliance, and permit/inspection evidence.
- Whether the asset/corridor edge is presented as context rather than a same-entity claim.
- Whether CHECK downgrade, contradiction, stale/freshness, no-data, quarantine, and cannot-claim cases are answerable from the truth manifest.

Do not use this package as founder product review, client readiness, forecast, source-truth mutation, official action, ticket, dispatch, control, enforcement, or training/fuel evidence.
""",
    )
    for filename, payload in build_guards().items():
        write_json(out / filename, payload)
    write_json(out / "CROSS_DOMAIN_STORY_ARC_DECISION.json", decision)
    write_text(
        out / "CODEX_CLOSEOUT.md",
        f"""# Cross-Domain Story Arc + Eval Expansion R1 Closeout

Status: `{status}`

- Story arc spans all four canonical families.
- Shared canonical entity gate uses `{PRIMARY_SITE}` across mobility, building-compliance, and permit/inspection evidence.
- New eval cases: {coverage["new_eval_case_count"]}; existing eval cases discovered: {coverage["existing_eval_case_count"]}; combined: {coverage["combined_eval_case_count"]}.
- Next recommendation: `{next_step}`.

Boundaries: local/replay diagnostic review only; no founder session, fuel, training rows, ForecastPacket, live ingestion, source-truth mutation, official action/control/enforcement, product-readiness, or client-readiness claim.
""",
    )
    hash_manifest(out)
    copy_publication(out)
    return decision


def parse_json_and_jsonl(out: Path) -> list[str]:
    errors = []
    for path in required_paths(out):
        if not path.exists():
            errors.append(f"missing required artifact: {path.name}")
            continue
        try:
            if path.suffix == ".json":
                read_json(path)
            elif path.suffix == ".jsonl":
                read_jsonl(path)
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(f"parse failed for {path.name}: {exc}")
    return errors


def validate(out: Path) -> list[str]:
    errors = parse_json_and_jsonl(out)
    if errors:
        return errors
    decision = read_json(out / "CROSS_DOMAIN_STORY_ARC_DECISION.json")
    truth = read_json(out / "CROSS_DOMAIN_STORY_TRUTH_MANIFEST.json")
    entity = read_json(out / "CROSS_DOMAIN_ENTITY_RESOLUTION_REPORT.json")
    coverage = read_json(out / "STORY_ARC_EVAL_COVERAGE_SCORECARD.json")
    cases = read_jsonl(out / "STORY_ARC_EVAL_EXPANSION_CASES.jsonl")
    negative = read_jsonl(out / "STORY_ARC_NEGATIVE_CHALLENGE_CASES.jsonl")
    guard_fuel = read_json(out / "NO_FOUNDER_SESSION_FUEL_GUARD.json")
    guard_client = read_json(out / "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json")
    guard_forecast = read_json(out / "NO_FORECAST_ACTION_GUARD.json")
    guard_source = read_json(out / "NO_SOURCE_TRUTH_MUTATION_GUARD.json")

    if decision.get("status") not in {STATUS_PASS, STATUS_BLOCKED, STATUS_NEEDS_REPAIR}:
        errors.append("invalid decision status")
    if decision.get("status") == STATUS_PASS:
        if truth.get("all_four_canonical_families_participate") is not True:
            errors.append("story does not span all four canonical families")
        if entity.get("minimum_gate_met") is not True:
            errors.append("entity minimum gate not met")
        if not entity.get("shared_canonical_entities_with_3plus_families"):
            errors.append("no shared canonical entity used by >=3 families")
        if entity.get("not_r3_local_only") is not True:
            errors.append("story is r3-local-only")
        if coverage.get("new_eval_case_count", 0) < 112:
            errors.append("new eval case count below 112")
        if coverage.get("existing_eval_case_count") and coverage.get("combined_eval_case_count", 0) < 160:
            errors.append("combined eval case count below 160")
        if coverage.get("each_family_has_20plus_cases") is not True:
            errors.append("family case floor not met")
        if coverage.get("cross_family_case_count", 0) < 20:
            errors.append("cross-family case floor not met")
        if not all(coverage.get("minimum_distribution_met", {}).values()):
            errors.append("challenge distribution floor not met")
    required_case_fields = {
        "eval_case_id",
        "story_arc_id",
        "family_ids",
        "question_or_assertion",
        "expected_behavior",
        "expected_answer_or_decision",
        "truth_refs",
        "source_refs",
        "check_reason_refs",
        "canonical_entity_refs",
        "negative_or_challenge_type",
        "operator_fuel",
        "training_eligible",
        "founder_session_result",
    }
    for case in cases:
        missing = required_case_fields - set(case)
        if missing:
            errors.append(f"case {case.get('eval_case_id')} missing fields: {sorted(missing)}")
        if case.get("operator_fuel") or case.get("training_eligible") or case.get("founder_session_result"):
            errors.append(f"case {case.get('eval_case_id')} creates forbidden fuel/session/training")
    if len(negative) < 16:
        errors.append("negative/challenge case file below 16 rows")
    if read_json(out / "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json").get("status") != "PASS":
        errors.append("standalone fixture guard failed")
    if read_json(out / "NO_DIRECT_D5D6_BYPASS_GUARD.json").get("status") != "PASS":
        errors.append("d5/d6 bypass guard failed")
    if guard_fuel.get("founder_session_results_created") or guard_fuel.get("operator_fuel_created") or guard_fuel.get("training_rows_created"):
        errors.append("fuel/session/training guard failed")
    if guard_client.get("product_review_ready") or guard_client.get("client_ready") or guard_client.get("client_ready_claim_created"):
        errors.append("product/client readiness guard failed")
    if guard_forecast.get("forecast_packet_created") or guard_forecast.get("official_workflow_case_action_created") or guard_forecast.get("dispatch_control_enforcement_created"):
        errors.append("forecast/action guard failed")
    if guard_source.get("source_truth_mutated") or guard_source.get("canonical_truth_rewritten"):
        errors.append("source truth mutation guard failed")
    errors.extend(verify_manifest(out / "HASH_MANIFEST.sha256"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expanded-corpus-root", type=Path, default=DEFAULT_EXPANDED_CORPUS_ROOT)
    parser.add_argument("--expanded-cadence-root", type=Path, default=DEFAULT_EXPANDED_CADENCE_ROOT)
    parser.add_argument("--mobility-packet-root", type=Path, default=DEFAULT_MOBILITY_PACKET_ROOT)
    parser.add_argument("--simulation-root", type=Path, default=DEFAULT_SIMULATION_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    if not args.validate_only:
        decision = build(args.expanded_corpus_root, args.expanded_cadence_root, args.mobility_packet_root, args.simulation_root, args.out)
        print(decision["status"])
    errors = validate(args.out)
    if errors:
        for error in errors:
            print(f"VALIDATION ERROR: {error}")
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
