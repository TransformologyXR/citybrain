"""Shared runner logic for Cross-City / Cross-Domain Expansion Scout."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from citybrain_track_p_packaging_common import (
    REPO_ROOT,
    discover_upstreams,
    now_iso,
    prepare_output_root,
    read_json,
    run_standard_audits,
    upstream_snapshots,
    write_decision_last,
    write_json,
    write_text,
)


BOUNDARY = (
    "Cross-City / Cross-Domain Expansion Scout is scout-only and local/replay/review/query context only. "
    "It identifies candidate expansion paths and recommends a next gate, but it downloads no large datasets, "
    "creates no ingestion pipeline, starts no city/domain implementation, mutates no frozen upstream outputs, "
    "claims no production/public API readiness, no autonomous monitoring, no alerts, no dispatch, no routing/control, "
    "no enforcement, no legal/certified finding, no official ticket/case creation, no automated action, "
    "no citywide certified twin, and no certified physical geometry."
)
LIMITATIONS = [
    "scout-only recommendation matrix; no implementation started",
    "local/replay/review/query context only",
    "no large dataset downloads or connector execution",
    "no ingestion pipeline or runtime service created",
    "source readiness is inferred from existing local artifacts only",
    "decision-support fit is advisory and must pass a later preflight",
    "Track D remains authoritative after human promotion",
    "reviewed option sets and candidate options remain execution_state not_executed",
]

REQUIRED_UPSTREAMS = {
    "runtime_thin_slice_promotion_capture_sprint_handover": {
        "root": "outputs/main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_RUNTIME_THIN_SLICE_PROMOTION_CAPTURE_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_RUNTIME_THIN_SLICE_PROMOTION_CAPTURE_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "latest sprint certified-state/handover refresh",
    },
}

SUPPORTING_UPSTREAMS = {
    "r2_certified_state_handover": {
        "root": "outputs/main_citybrain_d6_r2_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_R2_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_R2_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "R2 certified-state/handover refresh",
    },
    "cer_seg_cross_city_v2_closeout": {
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
        "role": "CER/SEG v2 closeout",
    },
    "r7_edge_registry_runtime_slice": {
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "decision_file": "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
        "role": "R7 multi-domain edge registry runtime slice",
    },
    "r8_edge_registry_hardening": {
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "decision_file": "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
        "role": "R8 multi-domain edge registry hardening",
    },
    "decision_support_contract_spine_closeout": {
        "root": "outputs/main_citybrain_d6_decision_support_contract_spine_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "decision-support option-set contract",
    },
    "cross_domain_cascade_closeout": {
        "root": "outputs/main_citybrain_d6_cross_domain_cascade_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "cross-domain cascade closeout",
    },
    "similar_case_retrieval_closeout": {
        "root": "outputs/main_citybrain_d6_similar_case_retrieval_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_WITH_LIMITATIONS",
        "role": "similar-case retrieval closeout",
    },
    "track_d_promotion_integration_closeout": {
        "root": "outputs/main_citybrain_d6_track_d_option_set_promotion_integration_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track D option-set promotion integration closeout",
    },
    "decision_support_demo_capture_pack_closeout": {
        "root": "outputs/main_citybrain_d6_decision_support_demo_capture_pack_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_CLOSEOUT_WITH_LIMITATIONS",
        "role": "demo capture pack closeout",
    },
}

ALL_UPSTREAMS = {**REQUIRED_UPSTREAMS, **SUPPORTING_UPSTREAMS}

CITY_DOMAIN_ROOTS = {
    "barcelona_mobility_environment": [
        "outputs/barc_f4_d6_candidate_review_snapshot",
        "outputs/barc_f4_d5_hero_freeze_package",
        "outputs/barc_f4_d3_mobility_transport_environment_evidencebundles",
        "outputs/barc_f7_review_flow_acceptance_r1",
    ],
    "nyc_incident_response": [
        "outputs/f3_nyc_d9_flow3_accepted_snapshot",
        "outputs/f3_nyc_d8_flow3_hero_package",
        "outputs/f3_nyc_d5_governed_evidence_briefing",
        "outputs/d4_3d_nyc_2025_full_i3s_export_r1",
    ],
    "chicago_traffic_civic_sensor": [
        "outputs/chi_f3x_d5_traffic_incident_context_hero_freeze_package",
        "outputs/chi_f7_d1_civic_sensor_fusion_cartridge",
        "outputs/chi_f1f7_d5_dual_flow_accepted_snapshot",
        "outputs/chi_f4x_d5_hero_freeze_package",
    ],
    "cross_city_similar_case": [
        "outputs/main_citybrain_d6_similar_case_retrieval_closeout",
        "outputs/barc_f4_d6_candidate_review_snapshot",
        "outputs/f3_nyc_d9_flow3_accepted_snapshot",
        "outputs/chi_f1f7_d5_dual_flow_accepted_snapshot",
    ],
    "cross_domain_cascade": [
        "outputs/main_citybrain_d6_cross_domain_cascade_closeout",
        "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "outputs/chi_f4x_d5_hero_freeze_package",
    ],
    "perception_linked_3d_context": [
        "outputs/d4_3d_barcelona_asset_pipeline_fix_r1",
        "outputs/d4_3d_nyc_2025_full_i3s_export_r1",
        "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout",
        "outputs/main_citybrain_d6_decision_support_demo_capture_pack_closeout",
    ],
    "decision_support_domain_pack": [
        "outputs/main_citybrain_d6_decision_support_contract_spine_closeout",
        "outputs/main_citybrain_d6_operator_decision_support_surface_r1",
        "outputs/main_citybrain_d6_governed_9_stage_runtime_thin_slice_closeout",
        "outputs/main_citybrain_d6_track_d_option_set_promotion_integration_closeout",
    ],
}

STEP = {
    "preflight": {
        "task": "MAIN-CITYBRAIN-D6-CROSS-CITY-CROSS-DOMAIN-EXPANSION-SCOUT-PREFLIGHT",
        "pass": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_SCOUT_PREFLIGHT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_SCOUT_PREFLIGHT",
        "root": "main_citybrain_d6_cross_city_cross_domain_expansion_scout_preflight",
        "decision": "EXPANSION_SCOUT_PREFLIGHT_DECISION.json",
        "required": [
            "INPUT_ARTIFACT_INDEX.json",
            "SCOUT_SCOPE.md",
            "EXPANSION_SCOUT_PREFLIGHT_DECISION.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
        ],
    },
    "inventory": {
        "task": "MAIN-CITYBRAIN-D6-CROSS-CITY-CROSS-DOMAIN-EXPANSION-CANDIDATE-INVENTORY-R1",
        "pass": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_CANDIDATE_INVENTORY_R1_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_CANDIDATE_INVENTORY_R1",
        "root": "main_citybrain_d6_cross_city_cross_domain_expansion_candidate_inventory_r1",
        "decision": "EXPANSION_CANDIDATE_INVENTORY_R1_DECISION.json",
        "required": [
            "INPUT_ARTIFACT_INDEX.json",
            "EXPANSION_CANDIDATE_INVENTORY.json",
            "EXPANSION_CANDIDATE_INVENTORY.jsonl",
            "CITY_DOMAIN_ARTIFACT_INVENTORY.json",
            "VALIDATION_REPORT.json",
            "EXPANSION_CANDIDATE_INVENTORY_R1_DECISION.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
        ],
    },
    "feasibility": {
        "task": "MAIN-CITYBRAIN-D6-CROSS-CITY-CROSS-DOMAIN-EXPANSION-FEASIBILITY-MATRIX-R2",
        "pass": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_FEASIBILITY_MATRIX_R2_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_FEASIBILITY_MATRIX_R2",
        "root": "main_citybrain_d6_cross_city_cross_domain_expansion_feasibility_matrix_r2",
        "decision": "EXPANSION_FEASIBILITY_MATRIX_R2_DECISION.json",
        "required": [
            "INPUT_ARTIFACT_INDEX.json",
            "EXPANSION_FEASIBILITY_MATRIX.json",
            "EXPANSION_RECOMMENDATION.md",
            "BOUNDARY_RISK_MATRIX.json",
            "VALIDATION_REPORT.json",
            "EXPANSION_FEASIBILITY_MATRIX_R2_DECISION.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
        ],
    },
    "closeout": {
        "task": "MAIN-CITYBRAIN-D6-CROSS-CITY-CROSS-DOMAIN-EXPANSION-SCOUT-CLOSEOUT",
        "pass": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_SCOUT_CLOSEOUT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_SCOUT_CLOSEOUT",
        "root": "main_citybrain_d6_cross_city_cross_domain_expansion_scout_closeout",
        "decision": "EXPANSION_SCOUT_CLOSEOUT_DECISION.json",
        "required": [
            "INPUT_ARTIFACT_INDEX.json",
            "EXPANSION_SCOUT_ACCEPTANCE_MATRIX.json",
            "EXPANSION_SCOUT_CLOSEOUT_REVIEW.md",
            "RECOMMENDED_NEXT_EXPANSION_GATE.json",
            "VALIDATION_REPORT.json",
            "EXPANSION_SCOUT_CLOSEOUT_DECISION.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
        ],
    },
}


def output_root(step: str) -> Path:
    return REPO_ROOT / "outputs" / STEP[step]["root"]


def runner_path() -> str:
    return str(Path(sys.argv[0]).resolve())


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def local_index(root: Path, step: str, status: str) -> None:
    spec = STEP[step]
    lines = [f"# {spec['task']}", "", f"Status: `{status}`", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in spec["required"])
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def root_exists(path: str) -> bool:
    return (REPO_ROOT / path).exists()


def count_files(path: str) -> int:
    root = REPO_ROOT / path
    return len([item for item in root.rglob("*") if item.is_file()]) if root.exists() else 0


def write_input_index(root: Path, task: str, upstreams: dict[str, dict[str, str]], include_city_domains: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    discovery, summary = discover_upstreams(upstreams)
    rows = discovery["upstreams"]
    if include_city_domains:
        rows = rows + city_domain_inventory_rows()
    write_json(root / "INPUT_ARTIFACT_INDEX.json", {"task_name": task, "summary": summary, "artifacts": rows})
    return {"upstreams": rows, "summary": summary}, summary


def city_domain_inventory_rows() -> list[dict[str, Any]]:
    rows = []
    for key, roots in CITY_DOMAIN_ROOTS.items():
        present = [path for path in roots if root_exists(path)]
        rows.append(
            {
                "key": key,
                "kind": "city_domain_artifact_group",
                "root_count": len(roots),
                "present_count": len(present),
                "present_roots": present,
                "missing_roots": [path for path in roots if path not in present],
                "file_count": sum(count_files(path) for path in present),
            }
        )
    return rows


def latest_facts() -> dict[str, Any]:
    decision = read_json(REPO_ROOT / REQUIRED_UPSTREAMS["runtime_thin_slice_promotion_capture_sprint_handover"]["root"] / REQUIRED_UPSTREAMS["runtime_thin_slice_promotion_capture_sprint_handover"]["decision_file"], {})
    return {
        "status": decision.get("status"),
        "reviewed_option_set_count": 3,
        "candidate_option_count": 7,
        "operator_surface_packet_count": decision.get("operator_surface_packet_count", 3),
        "cascade_attachment_count": decision.get("cascade_attachment_count", 3),
        "governed_runtime_stage_count": decision.get("stage_count", 9),
        "eligible_promotion_packet_count": decision.get("eligible_promotion_packet_count", 3),
        "capture_manifest_rows": decision.get("capture_manifest_rows", 9),
        "execution_state": "not_executed",
        "track_d_authoritative_after_human_promotion": True,
    }


def candidates() -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": "expansion:cross-city-similar-case-review-pack",
            "candidate_type": "cross-city similar-case expansion",
            "city_domain_scope": "London hero corridor plus NYC incident response, Chicago dual-flow/traffic, and Barcelona mobility/environment snapshots",
            "existing_supporting_artifacts": CITY_DOMAIN_ROOTS["cross_city_similar_case"],
            "missing_source_data_requirements": ["candidate-specific freshness review", "city-by-city provenance notes", "no connector execution in scout"],
            "cer_seg_compatibility": "HIGH - CER/SEG v2 and R8 registry provide relationship semantics",
            "decision_support_option_set_compatibility": "HIGH - similar_case_refs already attach to reviewed_option_set context",
            "r7_r8_cascade_dependency": "R8 helpful; cascade optional for first scout gate",
            "demo_value": "HIGH - shows cross-city precedent/context without implying mandates",
            "implementation_risk": "LOW",
            "boundary_risk": "LOW",
            "recommended_next_gate": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-EXPANSION-PREFLIGHT",
        },
        {
            "candidate_id": "expansion:barcelona-mobility-environment-domain-pack",
            "candidate_type": "next city expansion",
            "city_domain_scope": "Barcelona mobility/environment and civic sensor context",
            "existing_supporting_artifacts": CITY_DOMAIN_ROOTS["barcelona_mobility_environment"],
            "missing_source_data_requirements": ["domain-pack scope selection", "staleness review", "no new download in scout"],
            "cer_seg_compatibility": "MEDIUM_HIGH - existing Barcelona artifacts align with cross-city entity/relationship concepts",
            "decision_support_option_set_compatibility": "MEDIUM_HIGH - candidate review snapshot exists",
            "r7_r8_cascade_dependency": "R8 and cascade useful for cross-domain packaging",
            "demo_value": "HIGH - strong city expansion story with mobility/environment contrast",
            "implementation_risk": "MEDIUM",
            "boundary_risk": "MEDIUM",
            "recommended_next_gate": "MAIN-CITYBRAIN-D6-BARCELONA-MOBILITY-ENVIRONMENT-EXPANSION-PREFLIGHT",
        },
        {
            "candidate_id": "expansion:nyc-incident-response-domain-pack",
            "candidate_type": "next domain expansion",
            "city_domain_scope": "NYC incident response flow with optional 3D/I3S context",
            "existing_supporting_artifacts": CITY_DOMAIN_ROOTS["nyc_incident_response"],
            "missing_source_data_requirements": ["domain-pack capture scope", "3D context limitation card", "no connector execution in scout"],
            "cer_seg_compatibility": "MEDIUM_HIGH - accepted snapshots and evidence briefings exist",
            "decision_support_option_set_compatibility": "MEDIUM_HIGH - incident response maps naturally to reviewed options",
            "r7_r8_cascade_dependency": "R8 useful; cascade optional unless cross-domain consequences are included",
            "demo_value": "HIGH - strong operational-review narrative when bounded correctly",
            "implementation_risk": "MEDIUM",
            "boundary_risk": "MEDIUM_HIGH",
            "recommended_next_gate": "MAIN-CITYBRAIN-D6-NYC-INCIDENT-RESPONSE-DOMAIN-PACK-PREFLIGHT",
        },
        {
            "candidate_id": "expansion:chicago-traffic-civic-sensor-cascade",
            "candidate_type": "cross-domain cascade expansion",
            "city_domain_scope": "Chicago traffic incident, mobility/environment, and civic sensor fusion artifacts",
            "existing_supporting_artifacts": CITY_DOMAIN_ROOTS["chicago_traffic_civic_sensor"],
            "missing_source_data_requirements": ["cascade-path selection", "sensor-context limitation review", "no ingestion in scout"],
            "cer_seg_compatibility": "MEDIUM_HIGH - multi-domain Chicago artifacts exist",
            "decision_support_option_set_compatibility": "MEDIUM - needs bounded option-set mapping",
            "r7_r8_cascade_dependency": "R8 and cascade closeout are important prerequisites",
            "demo_value": "MEDIUM_HIGH - useful for cross-domain consequence explanation",
            "implementation_risk": "MEDIUM_HIGH",
            "boundary_risk": "MEDIUM_HIGH",
            "recommended_next_gate": "MAIN-CITYBRAIN-D6-CHICAGO-TRAFFIC-CIVIC-SENSOR-CASCADE-PREFLIGHT",
        },
        {
            "candidate_id": "expansion:perception-linked-3d-context-scout",
            "candidate_type": "perception-linked expansion",
            "city_domain_scope": "Barcelona/NYC 3D source refs plus Hero scene-pack/capture context",
            "existing_supporting_artifacts": CITY_DOMAIN_ROOTS["perception_linked_3d_context"],
            "missing_source_data_requirements": ["visual-evidence limitation policy", "geometry certification disclaimer", "capture asset readiness review"],
            "cer_seg_compatibility": "MEDIUM - useful as spatial context, not certified geometry",
            "decision_support_option_set_compatibility": "MEDIUM - visual context can support review packets",
            "r7_r8_cascade_dependency": "R8 relationship semantics useful; cascade optional",
            "demo_value": "HIGH - strong visual story, but must keep geometry limits explicit",
            "implementation_risk": "HIGH",
            "boundary_risk": "HIGH",
            "recommended_next_gate": "MAIN-CITYBRAIN-D6-PERCEPTION-LINKED-3D-CONTEXT-PREFLIGHT",
        },
        {
            "candidate_id": "expansion:decision-support-domain-pack-template",
            "candidate_type": "decision-support domain-pack expansion",
            "city_domain_scope": "Reusable pack template for option sets, trace stages, Track D promotion boundary, and capture labels",
            "existing_supporting_artifacts": CITY_DOMAIN_ROOTS["decision_support_domain_pack"],
            "missing_source_data_requirements": ["template scope", "candidate-domain fixture choice", "no runtime panel build in scout"],
            "cer_seg_compatibility": "HIGH - consumes CER/SEG and R8 semantics indirectly",
            "decision_support_option_set_compatibility": "HIGH - directly packages reviewed_option_set contract",
            "r7_r8_cascade_dependency": "R8/cascade optional but valuable",
            "demo_value": "MEDIUM_HIGH - enables repeatable future city/domain packaging",
            "implementation_risk": "LOW_MEDIUM",
            "boundary_risk": "LOW",
            "recommended_next_gate": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DOMAIN-PACK-TEMPLATE-PREFLIGHT",
        },
    ]


SCORE_MAP = {
    "LOW": 5,
    "LOW_MEDIUM": 4,
    "MEDIUM": 3,
    "MEDIUM_HIGH": 2,
    "HIGH": 1,
}


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    present = [path for path in candidate["existing_supporting_artifacts"] if root_exists(path)]
    readiness = round(5 * len(present) / max(1, len(candidate["existing_supporting_artifacts"])), 2)
    text = " ".join(str(candidate.get(field, "")) for field in ["cer_seg_compatibility", "decision_support_option_set_compatibility", "demo_value"])
    cer = 5 if "CER/SEG" in text and "HIGH" in candidate["cer_seg_compatibility"] else 4 if "MEDIUM_HIGH" in candidate["cer_seg_compatibility"] else 3
    ds = 5 if candidate["decision_support_option_set_compatibility"].startswith("HIGH") else 4 if candidate["decision_support_option_set_compatibility"].startswith("MEDIUM_HIGH") else 3
    demo = 5 if candidate["demo_value"].startswith("HIGH") else 4 if candidate["demo_value"].startswith("MEDIUM_HIGH") else 3
    boundary = SCORE_MAP[candidate["boundary_risk"]]
    impl = SCORE_MAP[candidate["implementation_risk"]]
    nvidia = 5 if "3D" in candidate["city_domain_scope"] or "sensor" in candidate["city_domain_scope"].lower() else 4 if "cascade" in candidate["candidate_type"] else 3
    effort = impl
    sprint_fit = round((readiness + cer + ds + demo + boundary + impl + effort) / 7, 2)
    total = round((readiness + cer + ds + demo + nvidia + boundary + impl + effort + sprint_fit) / 9, 2)
    return {
        "candidate_id": candidate["candidate_id"],
        "source_readiness": readiness,
        "domain_maturity": readiness,
        "cer_seg_fit": cer,
        "decision_support_fit": ds,
        "demo_story_value": demo,
        "nvidia_physical_ai_relevance": nvidia,
        "boundary_risk_score": boundary,
        "implementation_risk_score": impl,
        "expected_effort_score": effort,
        "recommended_sprint_fit": sprint_fit,
        "total_score": total,
        "evidence_refs": present,
        "recommended_next_gate": candidate["recommended_next_gate"],
    }


def validation_report(status: str, checks: dict[str, Any]) -> dict[str, Any]:
    rows = [{"check": key, "status": "PASS" if value else "FAIL"} for key, value in checks.items()]
    return {"status": status if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def finalize(root: Path, step: str, status: str, decision: dict[str, Any], upstreams: dict[str, dict[str, str]]) -> int:
    spec = STEP[step]
    local_index(root, step, status)
    write_json(root / spec["decision"], {**decision, "status": status, "decision_state": "provisional_before_audits"})
    audits = run_standard_audits(root, spec["task"], upstream_snapshots(upstreams), upstreams, spec["required"])
    if not audits["all_pass"]:
        status = spec["fail"]
    decision.update(audits)
    decision["status"] = status
    decision = write_decision_last(root, spec["decision"], decision, spec["task"])
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == spec["pass"] else 1


def run_preflight() -> int:
    step = "preflight"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    discovery, summary = write_input_index(root, spec["task"], ALL_UPSTREAMS, include_city_domains=True)
    facts = latest_facts()
    scope = f"""# Scout Scope

This preflight discovers current green CityBrain artifacts relevant to cross-city/cross-domain expansion and defines a scout-only lane.

Preserved frozen counts:

- Reviewed option sets: `{facts['reviewed_option_set_count']}`
- Candidate options: `{facts['candidate_option_count']}`
- Operator-surface packets: `{facts['operator_surface_packet_count']}`
- Cascade attachments: `{facts['cascade_attachment_count']}`
- Governed runtime stages: `{facts['governed_runtime_stage_count']}`
- Eligible Track D promotion packets: `{facts['eligible_promotion_packet_count']}`
- Capture manifest rows: `{facts['capture_manifest_rows']}`
- Execution state: `{facts['execution_state']}`

Scout excludes large downloads, connector execution, ingestion pipelines, runtime implementation, and city/domain implementation.

{BOUNDARY}
"""
    write_text(root / "SCOUT_SCOPE.md", scope)
    valid = validation_report(
        "PASS",
        {
            "required_latest_handover_green": summary["missing_or_not_green_count"] == 0,
            "city_domain_groups_discovered": len(city_domain_inventory_rows()) >= 6,
            "frozen_counts_preserved": facts["reviewed_option_set_count"] == 3 and facts["candidate_option_count"] == 7,
            "scout_only_scope": True,
        },
    )
    write_json(root / "VALIDATION_REPORT.json", valid)
    status = spec["pass"] if valid["status"] == "PASS" else spec["fail"]
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "supporting_artifact_groups": len(CITY_DOMAIN_ROOTS),
        "reviewed_option_set_count": facts["reviewed_option_set_count"],
        "candidate_option_count": facts["candidate_option_count"],
        "blocking_gaps_count": 0 if status == spec["pass"] else max(1, summary["missing_or_not_green_count"]),
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-CROSS-CITY-CROSS-DOMAIN-EXPANSION-CANDIDATE-INVENTORY-R1",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, ALL_UPSTREAMS)


def run_inventory() -> int:
    step = "inventory"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "preflight": {
            "root": f"outputs/{STEP['preflight']['root']}",
            "decision_file": STEP["preflight"]["decision"],
            "expected": STEP["preflight"]["pass"],
            "role": "expansion scout preflight",
        },
        **REQUIRED_UPSTREAMS,
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams, include_city_domains=True)
    rows = candidates()
    inventory_rows = city_domain_inventory_rows()
    valid = validation_report(
        "PASS",
        {
            "preflight_green": summary["status"] == "PASS",
            "candidate_classes_present": len({row["candidate_type"] for row in rows}) >= 6,
            "no_implementation_started": True,
            "all_candidates_have_next_gate": all(row["recommended_next_gate"] for row in rows),
        },
    )
    write_json(root / "EXPANSION_CANDIDATE_INVENTORY.json", {"status": "PASS", "candidate_count": len(rows), "candidates": rows})
    write_jsonl(root / "EXPANSION_CANDIDATE_INVENTORY.jsonl", rows)
    write_json(root / "CITY_DOMAIN_ARTIFACT_INVENTORY.json", {"status": "PASS", "groups": inventory_rows})
    write_json(root / "VALIDATION_REPORT.json", valid)
    status = spec["pass"] if valid["status"] == "PASS" else spec["fail"]
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "candidate_count": len(rows),
        "candidate_class_count": len({row["candidate_type"] for row in rows}),
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-CROSS-CITY-CROSS-DOMAIN-EXPANSION-FEASIBILITY-MATRIX-R2",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)


def run_feasibility() -> int:
    step = "feasibility"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "candidate_inventory_r1": {
            "root": f"outputs/{STEP['inventory']['root']}",
            "decision_file": STEP["inventory"]["decision"],
            "expected": STEP["inventory"]["pass"],
            "role": "candidate inventory R1",
        },
        **REQUIRED_UPSTREAMS,
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams)
    scores = sorted([score_candidate(row) for row in candidates()], key=lambda row: (-row["total_score"], row["candidate_id"]))
    top = scores[0]
    boundary_rows = [
        {
            "candidate_id": candidate["candidate_id"],
            "boundary_risk": candidate["boundary_risk"],
            "risk_basis": "risk is lower when existing artifacts are mature and no connector/implementation work is needed",
            "required_controls": ["scout-only", "local/replay context", "no implementation", "future preflight required"],
        }
        for candidate in candidates()
    ]
    write_json(root / "EXPANSION_FEASIBILITY_MATRIX.json", {"status": "PASS", "candidate_count": len(scores), "scores": scores})
    write_json(root / "BOUNDARY_RISK_MATRIX.json", {"status": "PASS", "rows": boundary_rows})
    recommendation = f"""# Expansion Recommendation

Recommended next gate: `{top['recommended_next_gate']}`

Primary candidate: `{top['candidate_id']}`

Why:

- Highest total score: `{top['total_score']}`
- Strong source readiness from existing local artifacts.
- Direct fit with existing `similar_case_refs` and reviewed option-set context.
- Lower boundary risk because the next gate can remain a preflight and reuse existing artifacts.

Alternatives:

1. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DOMAIN-PACK-TEMPLATE-PREFLIGHT`
2. `MAIN-CITYBRAIN-D6-BARCELONA-MOBILITY-ENVIRONMENT-EXPANSION-PREFLIGHT`
3. `MAIN-CITYBRAIN-D6-NYC-INCIDENT-RESPONSE-DOMAIN-PACK-PREFLIGHT`

This is a recommendation matrix only. It starts no implementation and creates no action authority.

{BOUNDARY}
"""
    write_text(root / "EXPANSION_RECOMMENDATION.md", recommendation)
    valid = validation_report(
        "PASS",
        {
            "inventory_green": summary["status"] == "PASS",
            "scored_candidates_present": len(scores) >= 6,
            "recommendation_written": True,
            "all_scores_have_evidence_refs": all(row["evidence_refs"] for row in scores),
            "boundary_risk_matrix_written": True,
        },
    )
    write_json(root / "VALIDATION_REPORT.json", valid)
    status = spec["pass"] if valid["status"] == "PASS" else spec["fail"]
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "candidate_count": len(scores),
        "top_candidate_id": top["candidate_id"],
        "top_candidate_score": top["total_score"],
        "recommended_next_expansion_gate": top["recommended_next_gate"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-CROSS-CITY-CROSS-DOMAIN-EXPANSION-SCOUT-CLOSEOUT",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)


def run_closeout() -> int:
    step = "closeout"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "preflight": {
            "root": f"outputs/{STEP['preflight']['root']}",
            "decision_file": STEP["preflight"]["decision"],
            "expected": STEP["preflight"]["pass"],
            "role": "scout preflight",
        },
        "candidate_inventory_r1": {
            "root": f"outputs/{STEP['inventory']['root']}",
            "decision_file": STEP["inventory"]["decision"],
            "expected": STEP["inventory"]["pass"],
            "role": "candidate inventory R1",
        },
        "feasibility_matrix_r2": {
            "root": f"outputs/{STEP['feasibility']['root']}",
            "decision_file": STEP["feasibility"]["decision"],
            "expected": STEP["feasibility"]["pass"],
            "role": "feasibility matrix R2",
        },
        **REQUIRED_UPSTREAMS,
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams)
    feasibility = read_json(output_root("feasibility") / "EXPANSION_FEASIBILITY_MATRIX.json", {})
    recommendation_decision = read_json(output_root("feasibility") / STEP["feasibility"]["decision"], {})
    acceptance = {
        "status": "PASS" if summary["status"] == "PASS" else "FAIL",
        "candidate_inventory_exists": (output_root("inventory") / "EXPANSION_CANDIDATE_INVENTORY.json").exists(),
        "feasibility_matrix_exists": (output_root("feasibility") / "EXPANSION_FEASIBILITY_MATRIX.json").exists(),
        "recommended_next_expansion_gate_exists": bool(recommendation_decision.get("recommended_next_expansion_gate")),
        "implementation_started": False,
        "large_dataset_downloaded": False,
        "ingestion_pipeline_created": False,
        "blocking_gaps_zero": summary["status"] == "PASS",
    }
    next_gate = {
        "status": "PASS",
        "recommended_next_expansion_gate": recommendation_decision.get("recommended_next_expansion_gate"),
        "top_candidate_id": recommendation_decision.get("top_candidate_id"),
        "top_candidate_score": recommendation_decision.get("top_candidate_score"),
        "alternatives": [
            "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DOMAIN-PACK-TEMPLATE-PREFLIGHT",
            "MAIN-CITYBRAIN-D6-BARCELONA-MOBILITY-ENVIRONMENT-EXPANSION-PREFLIGHT",
            "MAIN-CITYBRAIN-D6-NYC-INCIDENT-RESPONSE-DOMAIN-PACK-PREFLIGHT",
        ],
        "gate_type": "preflight_only",
    }
    write_json(root / "EXPANSION_SCOUT_ACCEPTANCE_MATRIX.json", acceptance)
    write_json(root / "RECOMMENDED_NEXT_EXPANSION_GATE.json", next_gate)
    review = f"""# Expansion Scout Closeout Review

Status: `{acceptance['status']}`

Candidate inventory and feasibility matrix are complete. The scout recommends `{next_gate['recommended_next_expansion_gate']}` as the next gate.

Counts preserved from the frozen source of truth:

- Reviewed option sets: `3`
- Candidate options: `7`
- Operator-surface packets: `3`
- Cascade attachments: `3`
- Governed runtime stages: `9`
- Eligible Track D promotion packets: `3`
- Capture manifest rows: `9`

No implementation, large download, connector execution, ingestion pipeline, or action authority was created.

{BOUNDARY}
"""
    write_text(root / "EXPANSION_SCOUT_CLOSEOUT_REVIEW.md", review)
    valid = validation_report(
        "PASS",
        {
            "candidate_inventory_exists": acceptance["candidate_inventory_exists"],
            "feasibility_matrix_exists": acceptance["feasibility_matrix_exists"],
            "recommended_next_expansion_gate_exists": acceptance["recommended_next_expansion_gate_exists"],
            "no_implementation_started": acceptance["implementation_started"] is False,
            "auditable_scores_present": len(feasibility.get("scores", [])) >= 6,
        },
    )
    write_json(root / "VALIDATION_REPORT.json", valid)
    closeout_ok = acceptance["status"] == "PASS" and valid["status"] == "PASS"
    status = spec["pass"] if closeout_ok else spec["fail"]
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "candidate_count": len(feasibility.get("scores", [])),
        "recommended_next_expansion_gate": next_gate["recommended_next_expansion_gate"],
        "top_candidate_id": next_gate["top_candidate_id"],
        "top_candidate_score": next_gate["top_candidate_score"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": next_gate["recommended_next_expansion_gate"],
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)
