#!/usr/bin/env python3
"""Run Building Compliance Domain Pack R1 end-to-end."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from citybrain_domain_pack_r1_common import DomainConfig, run_domain_pack

sys.dont_write_bytecode = True


CONFIG = DomainConfig(
    domain_key="building_compliance",
    task_name="MAIN-CITYBRAIN-D4X-BUILDING-COMPLIANCE-DOMAIN-PACK-R1-END-TO-END",
    output_dir="outputs/main_citybrain_d4x_building_compliance_domain_pack_r1_end_to_end",
    prefix="BUILDING_COMPLIANCE",
    pass_status="PASS_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS",
    data_first_status="PASS_BUILDING_COMPLIANCE_DOMAIN_PACK_R1_DATA_FIRST_WITH_LIMITATIONS",
    waiting_status="WAITING_ON_BUILDING_COMPLIANCE_INPUT_ROOTS",
    fail_status="FAIL_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_DOMAIN_PACK_R1_END_TO_END",
    expected_score_key="building_compliance_readiness_score",
    recommended_next_task="MAIN-CITYBRAIN-D4X-BUILDING-COMPLIANCE-R7-EDGE-EXTENSION-AND-CLOSEOUT-R1",
    keywords=(
        "building", "compliance", "inspection", "violation", "permit", "construction",
        "civic", "review", "asset", "lod2", "usd", "cer", "seg", "incident",
    ),
    entity_types=(
        "compliance_subject_asset", "building_asset", "inspection_context",
        "violation_candidate_context", "permit_context", "civic_review_context",
        "source_compliance_record", "evidence_item", "limitation_item",
        "review_state_record", "compliance_episode", "asset_binding_context",
        "cer_context", "seg_context", "d6_display_context", "kit_handoff_context",
        "data_first_compliance_placeholder", "boundary_challenge_record",
    ),
    relationship_types=(
        "asset_has_compliance_context", "asset_has_inspection_context",
        "asset_has_violation_candidate_context", "asset_has_permit_context",
        "asset_has_civic_review_context", "compliance_context_has_evidence",
        "compliance_context_has_limitation", "compliance_context_requires_review",
        "compliance_context_appears_in_episode", "compliance_context_maps_to_cer",
        "compliance_context_maps_to_seg", "compliance_context_has_asset_binding",
        "compliance_context_available_for_d6_display",
        "data_first_placeholder_for_compliance_domain",
    ),
    event_types=(
        "inspection_review_context", "violation_candidate_review_context",
        "permit_reference_context", "civic_service_compliance_context",
        "asset_identity_compliance_context", "limitation_only_compliance_context",
        "data_first_compliance_context", "boundary_challenge_compliance_context",
    ),
    scope_lines=(
        "review/context-only",
        "no legal finding",
        "no confirmed violation",
        "no enforcement",
        "no permit approval/rejection",
        "no certified compliance status",
        "no autonomous monitoring/alerts",
        "no action outputs",
    ),
    packet_extra_fields=("inspection_refs", "violation_candidate_refs", "permit_refs", "civic_review_refs"),
    min_context_label="Building compliance",
    negative_tests=(
        "confirmed violation claim rejected",
        "legal finding rejected",
        "enforcement/dispatch claim rejected",
        "permit approval/rejection claim rejected",
        "certified compliance status rejected",
        "source ID legal truth rejected",
        "missing evidence rejected",
        "missing limitation rejected",
        "source mutation rejected",
        "product surface mutation rejected",
        "public API claim rejected",
        "external LLM truth claim rejected",
    ),
    limitations=(
        "No inspection/violation/legal status is inferred from asset context.",
        "Permit and compliance references remain candidate/context only.",
        "Building source IDs are not ownership, legal, or certified truth.",
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
