#!/usr/bin/env python3
"""Run Property/Planning Domain Pack R1 end-to-end."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from citybrain_domain_pack_r1_common import DomainConfig, run_domain_pack

sys.dont_write_bytecode = True


CONFIG = DomainConfig(
    domain_key="property_planning",
    task_name="MAIN-CITYBRAIN-D4X-PROPERTY-PLANNING-DOMAIN-PACK-R1-END-TO-END",
    output_dir="outputs/main_citybrain_d4x_property_planning_domain_pack_r1_end_to_end",
    prefix="PROPERTY_PLANNING",
    pass_status="PASS_MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS",
    data_first_status="PASS_PROPERTY_PLANNING_DOMAIN_PACK_R1_DATA_FIRST_WITH_LIMITATIONS",
    waiting_status="WAITING_ON_PROPERTY_PLANNING_INPUT_ROOTS",
    fail_status="FAIL_MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_DOMAIN_PACK_R1_END_TO_END",
    expected_score_key="property_planning_readiness_score",
    recommended_next_task="MAIN-CITYBRAIN-D4X-PROPERTY-PLANNING-R7-EDGE-EXTENSION-AND-CLOSEOUT-R1",
    keywords=(
        "property", "planning", "permit", "parcel", "transaction", "zoning", "land",
        "development", "dld", "dm", "cadastre", "address", "plot", "building",
        "asset", "cer", "seg", "pluto", "uprn", "toid",
    ),
    entity_types=(
        "planning_subject_asset", "parcel_context", "building_context",
        "unit_or_premise_context", "property_record_context", "planning_case_context",
        "permit_context", "transaction_context", "development_project_context",
        "zoning_or_land_use_context", "source_property_record", "source_planning_record",
        "evidence_item", "limitation_item", "review_state_record",
        "property_planning_episode", "cer_context", "seg_context",
        "kit_handoff_context", "data_first_property_placeholder",
        "boundary_challenge_record",
    ),
    relationship_types=(
        "property_context_references_asset", "planning_context_references_asset",
        "parcel_context_contains_building_context", "building_context_contains_unit_context",
        "permit_context_applies_to_asset", "transaction_context_mentions_property_context",
        "development_project_context_affects_area", "planning_context_has_evidence",
        "planning_context_has_limitation", "planning_context_requires_review",
        "property_context_maps_to_cer", "property_context_maps_to_seg",
        "property_context_appears_in_episode", "property_context_available_for_d6_display",
        "data_first_placeholder_for_property_planning_domain",
    ),
    event_types=(
        "planning_case_context", "permit_reference_context",
        "property_transaction_context", "development_project_context",
        "zoning_or_land_use_context", "asset_identity_property_context",
        "limitation_only_property_context", "data_first_property_context",
        "boundary_challenge_property_context",
    ),
    scope_lines=(
        "planning/property context only",
        "no approval/rejection decision",
        "no legal property finding",
        "no ownership/certified title claim",
        "no valuation/certified financial claim",
        "no enforcement/action output",
        "no production DLD/DM integration",
    ),
    packet_extra_fields=(
        "parcel_refs", "building_refs", "unit_refs", "planning_case_refs",
        "permit_refs", "transaction_refs", "project_refs",
    ),
    min_context_label="Property/planning",
    negative_tests=(
        "permit approval/rejection claim rejected",
        "legal property finding rejected",
        "ownership/title truth rejected",
        "valuation/certified financial claim rejected",
        "source ID legal truth rejected",
        "missing evidence rejected",
        "missing limitation rejected",
        "source mutation rejected",
        "product surface mutation rejected",
        "public API claim rejected",
        "external LLM truth claim rejected",
    ),
    limitations=(
        "No permit approval, rejection, ownership, title, valuation, or legal property finding.",
        "Cadastre/parcel/address/source IDs are context only unless a bounded source explicitly says otherwise.",
        "Planning and property records require source strengthening before stronger claims.",
    ),
)


def main() -> int:
    decision = run_domain_pack(CONFIG, Path(__file__).resolve())
    print(json.dumps({
        "status": decision["status"],
        "domain_packet_count": decision["domain_packet_count"],
        "episode_candidate_count": decision["episode_candidate_count"],
        "r7_edge_extension_candidate_count": decision["r7_edge_extension_candidate_count"],
        "recommended_next_task": decision["recommended_next_task"],
    }, indent=2))
    return 0 if decision["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
