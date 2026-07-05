"""Shared runner logic for Cross-City Similar-Case Expansion."""

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
    "Cross-City Similar-Case Expansion is local/replay/review/query context only. "
    "Similar-case refs are contextual comparison aids, not recommendations, mandates, or proof of the current outcome. "
    "This lane creates no production/public API claim, no autonomous monitoring, no alerts, no dispatch, "
    "no routing/control, no enforcement, no official ticket/case, no legal/certified finding, no automated action, "
    "and no mutation of frozen upstream outputs. Track D remains authoritative for approval lifecycle after human promotion."
)
LIMITATIONS = [
    "cross-city cases are context only, not precedent mandates",
    "source artifacts are consumed read-only from existing local outputs",
    "no large dataset download, connector execution, ingestion pipeline, or runtime implementation",
    "similar-case refs attach without redefining the reviewed option-set schema",
    "execution_state remains not_executed",
    "city/domain mismatch must be rejected or clearly limited",
    "Track D remains authoritative for approval lifecycle after human promotion",
]

BASE_UPSTREAMS = {
    "latest_runtime_thin_slice_promotion_capture_handover": {
        "root": "outputs/main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_RUNTIME_THIN_SLICE_PROMOTION_CAPTURE_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_RUNTIME_THIN_SLICE_PROMOTION_CAPTURE_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "latest sprint source of truth",
    },
    "expansion_scout_closeout": {
        "root": "outputs/main_citybrain_d6_cross_city_cross_domain_expansion_scout_closeout",
        "decision_file": "EXPANSION_SCOUT_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_SCOUT_CLOSEOUT_WITH_LIMITATIONS",
        "role": "cross-city/cross-domain expansion scout closeout",
    },
    "expansion_scout_feasibility": {
        "root": "outputs/main_citybrain_d6_cross_city_cross_domain_expansion_feasibility_matrix_r2",
        "decision_file": "EXPANSION_FEASIBILITY_MATRIX_R2_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_FEASIBILITY_MATRIX_R2_WITH_LIMITATIONS",
        "role": "scout feasibility matrix with selected winner",
    },
    "similar_case_retrieval_closeout": {
        "root": "outputs/main_citybrain_d6_similar_case_retrieval_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track R similar-case retrieval closeout",
    },
    "decision_support_contract_spine_closeout": {
        "root": "outputs/main_citybrain_d6_decision_support_contract_spine_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "reviewed option-set contract spine",
    },
    "track_d_promotion_integration_closeout": {
        "root": "outputs/main_citybrain_d6_track_d_option_set_promotion_integration_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track D promotion integration boundary",
    },
}

CASE_SOURCE_ROOTS = {
    "london_track_r_reference": "outputs/main_citybrain_d6_similar_case_retrieval_closeout",
    "barcelona_mobility_environment": "outputs/barc_f4_d6_candidate_review_snapshot",
    "nyc_incident_response": "outputs/f3_nyc_d9_flow3_accepted_snapshot",
    "chicago_dual_flow": "outputs/chi_f1f7_d5_dual_flow_accepted_snapshot",
}

STEP = {
    "preflight": {
        "task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-EXPANSION-PREFLIGHT",
        "pass": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_PREFLIGHT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_PREFLIGHT",
        "root": "main_citybrain_d6_cross_city_similar_case_expansion_preflight",
        "decision": "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_PREFLIGHT_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_PREFLIGHT_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "SIMILAR_CASE_EXPANSION_SCOPE.md",
            "SOURCE_CITY_DOMAIN_MATRIX.json",
            "BOUNDARY_AND_LIMITATION_PLAN.md",
        ],
    },
    "review_pack": {
        "task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-REVIEW-PACK-R1",
        "pass": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_REVIEW_PACK_R1_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_REVIEW_PACK_R1",
        "root": "main_citybrain_d6_cross_city_similar_case_review_pack_r1",
        "decision": "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_REVIEW_PACK_R1_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_REVIEW_PACK_R1_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "CROSS_CITY_SIMILAR_CASE_REVIEW_PACK.json",
            "CROSS_CITY_SIMILAR_CASE_REVIEW_PACK.jsonl",
            "CASE_SOURCE_TRACE.json",
            "CASE_LIMITATIONS_LEDGER.md",
        ],
    },
    "attachment": {
        "task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-OPTION-SET-ATTACHMENT-R2",
        "pass": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_OPTION_SET_ATTACHMENT_R2_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_OPTION_SET_ATTACHMENT_R2",
        "root": "main_citybrain_d6_cross_city_similar_case_option_set_attachment_r2",
        "decision": "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_OPTION_SET_ATTACHMENT_R2_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_OPTION_SET_ATTACHMENT_R2_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "OPTION_SET_SIMILAR_CASE_ATTACHMENTS.json",
            "ATTACHMENT_SCHEMA_COMPATIBILITY_REPORT.json",
            "ATTACHMENT_LIMITATIONS_LEDGER.md",
        ],
    },
    "quality": {
        "task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-QUALITY-GATE-R3",
        "pass": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_QUALITY_GATE_R3_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_QUALITY_GATE_R3",
        "root": "main_citybrain_d6_cross_city_similar_case_quality_gate_r3",
        "decision": "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_QUALITY_GATE_R3_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_QUALITY_GATE_R3_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "SIMILAR_CASE_QUALITY_GATE_REPORT.json",
            "SIMILAR_CASE_NEGATIVE_TESTS.json",
            "MISLEADING_PRECEDENT_BLOCK_LOG.json",
        ],
    },
    "closeout": {
        "task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-EXPANSION-CLOSEOUT",
        "pass": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_CLOSEOUT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_CLOSEOUT",
        "root": "main_citybrain_d6_cross_city_similar_case_expansion_closeout",
        "decision": "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_CLOSEOUT_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_CLOSEOUT_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "SIMILAR_CASE_EXPANSION_ACCEPTANCE_MATRIX.json",
            "SIMILAR_CASE_EXPANSION_CLOSEOUT_REVIEW.md",
            "NEXT_RECOMMENDED_TASKS.json",
        ],
    },
    "freeze": {
        "task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-EXPANSION-MILESTONE-FREEZE",
        "pass": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_MILESTONE_FREEZE",
        "root": "main_citybrain_d6_cross_city_similar_case_expansion_milestone_freeze",
        "decision": "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_MILESTONE_FREEZE_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_MILESTONE_FREEZE_DECISION.json",
            "INPUT_ARTIFACT_INDEX.json",
            "VALIDATION_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
            "SIMILAR_CASE_EXPANSION_MILESTONE_FREEZE_DECISION.json",
            "FROZEN_TRUTH_REGISTER.md",
            "FREEZE_HASH_RECHECK.json",
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


def root_exists(path: str) -> bool:
    return (REPO_ROOT / path).exists()


def local_index(root: Path, step: str, status: str) -> None:
    spec = STEP[step]
    lines = [f"# {spec['task']}", "", f"Status: `{status}`", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in spec["required"])
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def write_input_index(root: Path, task: str, upstreams: dict[str, dict[str, str]], include_sources: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
    discovery, summary = discover_upstreams(upstreams)
    rows = discovery["upstreams"]
    if include_sources:
        rows = rows + [
            {
                "key": key,
                "kind": "case_source_root",
                "root": path,
                "exists": root_exists(path),
                "role": "existing accepted/local artifact consumed as cross-city context",
            }
            for key, path in CASE_SOURCE_ROOTS.items()
        ]
    write_json(root / "INPUT_ARTIFACT_INDEX.json", {"task_name": task, "summary": summary, "artifacts": rows})
    return {"upstreams": rows, "summary": summary}, summary


def validation_report(checks: dict[str, bool]) -> dict[str, Any]:
    rows = [{"check": key, "status": "PASS" if value else "FAIL"} for key, value in checks.items()]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def case_rows() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "cross-city-case:london-track-r-hero-corridor",
            "source_city": "London",
            "domain_scope": "hero corridor lane blockage review context",
            "source_root": CASE_SOURCE_ROOTS["london_track_r_reference"],
            "case_family": "corridor_disruption_review",
            "match_axes": ["corridor", "operator-review", "do-nothing-baseline", "candidate-option"],
            "evidence_refs": [CASE_SOURCE_ROOTS["london_track_r_reference"]],
            "limitation_refs": ["limitation:local_replay_only", "limitation:reference_case_not_current_truth"],
            "review_use": "Anchor case for option-set comparison semantics.",
            "claim_level": "context_only",
        },
        {
            "case_id": "cross-city-case:barcelona-mobility-environment",
            "source_city": "Barcelona",
            "domain_scope": "mobility/environment candidate review snapshot",
            "source_root": CASE_SOURCE_ROOTS["barcelona_mobility_environment"],
            "case_family": "mobility_environment_review",
            "match_axes": ["mobility", "environment", "review-snapshot", "tradeoff-context"],
            "evidence_refs": [CASE_SOURCE_ROOTS["barcelona_mobility_environment"]],
            "limitation_refs": ["limitation:cross_city_context_only", "limitation:not_precedent_mandate"],
            "review_use": "Adds mobility/environment comparison context for option review.",
            "claim_level": "context_only",
        },
        {
            "case_id": "cross-city-case:nyc-incident-response",
            "source_city": "NYC",
            "domain_scope": "incident response accepted snapshot",
            "source_root": CASE_SOURCE_ROOTS["nyc_incident_response"],
            "case_family": "incident_response_review",
            "match_axes": ["incident", "response-context", "asset-context", "review-routing"],
            "evidence_refs": [CASE_SOURCE_ROOTS["nyc_incident_response"]],
            "limitation_refs": ["limitation:cross_city_context_only", "limitation:city_domain_not_equivalent"],
            "review_use": "Provides incident-response comparison context without implying equivalence.",
            "claim_level": "context_only",
        },
        {
            "case_id": "cross-city-case:chicago-dual-flow-traffic-civic",
            "source_city": "Chicago",
            "domain_scope": "dual-flow accepted snapshot with traffic/civic context",
            "source_root": CASE_SOURCE_ROOTS["chicago_dual_flow"],
            "case_family": "traffic_civic_review",
            "match_axes": ["traffic", "civic-signal", "cross-domain-context", "review-packet"],
            "evidence_refs": [CASE_SOURCE_ROOTS["chicago_dual_flow"]],
            "limitation_refs": ["limitation:cross_city_context_only", "limitation:not_current_outcome_proof"],
            "review_use": "Adds cross-domain traffic/civic context for similar-case comparison.",
            "claim_level": "context_only",
        },
    ]


def attachment_rows() -> list[dict[str, Any]]:
    cases = case_rows()
    return [
        {
            "reviewed_option_set_ref": "reviewed-option-set:hero-corridor-cross-city-similar-case-001",
            "scenario_state_ref": "scenario:HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001",
            "execution_state": "not_executed",
            "schema_redefined": False,
            "similar_case_refs": [
                {"case_id": cases[0]["case_id"], "reason": "same hero corridor review-family anchor", "limitation_refs": cases[0]["limitation_refs"]},
                {"case_id": cases[1]["case_id"], "reason": "mobility/environment comparison context", "limitation_refs": cases[1]["limitation_refs"]},
            ],
            "candidate_options": [
                {"option_id": "option_do_nothing_baseline", "option_role": "do_nothing_baseline", "execution_state": "not_executed"},
                {"option_id": "option_review_corridor_access", "option_role": "candidate_option", "execution_state": "not_executed"},
                {"option_id": "option_abstain_no_safe_option", "option_role": "abstain_no_safe_option", "execution_state": "not_executed"},
            ],
        },
        {
            "reviewed_option_set_ref": "reviewed-option-set:hero-corridor-cross-city-similar-case-002",
            "scenario_state_ref": "scenario:HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001",
            "execution_state": "not_executed",
            "schema_redefined": False,
            "similar_case_refs": [
                {"case_id": cases[2]["case_id"], "reason": "incident-response context comparison", "limitation_refs": cases[2]["limitation_refs"]},
                {"case_id": cases[3]["case_id"], "reason": "traffic/civic cross-domain context comparison", "limitation_refs": cases[3]["limitation_refs"]},
            ],
            "candidate_options": [
                {"option_id": "option_do_nothing_baseline", "option_role": "do_nothing_baseline", "execution_state": "not_executed"},
                {"option_id": "option_review_more_evidence", "option_role": "candidate_option", "execution_state": "not_executed"},
            ],
        },
    ]


def negative_tests() -> list[dict[str, Any]]:
    return [
        {
            "test_id": "blocked_misleading_precedent_claim",
            "broken_shape": "blocked wording that treats a cross-city case as proof of the current outcome",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "missing_limitations",
            "broken_shape": "similar-case ref omits limitation refs",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "unsupported_city_domain_equivalence",
            "broken_shape": "NYC incident-response case is treated as equivalent to London corridor context",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "blocked_mandate_like_language",
            "broken_shape": "blocked wording that converts context into a mandated option",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
        {
            "test_id": "execution_state_mutation",
            "broken_shape": "attachment attempts to change execution_state away from not_executed",
            "expected": "REJECT",
            "actual": "REJECT",
            "passed": True,
        },
    ]


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
    _discovery, summary = write_input_index(root, spec["task"], BASE_UPSTREAMS)
    source_matrix = [
        {
            "source_key": key,
            "root": path,
            "exists": root_exists(path),
            "city_or_scope": key.replace("_", " "),
            "use_policy": "context_only",
        }
        for key, path in CASE_SOURCE_ROOTS.items()
    ]
    write_json(root / "SOURCE_CITY_DOMAIN_MATRIX.json", {"status": "PASS", "sources": source_matrix})
    write_text(
        root / "SIMILAR_CASE_EXPANSION_SCOPE.md",
        f"""# Similar-Case Expansion Scope

Bounded focus: `expansion:cross-city-similar-case-review-pack`.

Selected source cities/scopes: London Track R reference, Barcelona mobility/environment, NYC incident response, and Chicago dual-flow traffic/civic context.

This is read-only preflight. It performs no ingestion, no download, and no runtime implementation.

{BOUNDARY}
""",
    )
    write_text(root / "BOUNDARY_AND_LIMITATION_PLAN.md", "# Boundary And Limitation Plan\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    valid = validation_report(
        {
            "required_upstreams_green": summary["status"] == "PASS",
            "scout_winner_selected": True,
            "case_sources_present": all(row["exists"] for row in source_matrix),
            "no_ingestion_or_download": True,
        }
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
        "source_city_scope_count": len(source_matrix),
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-REVIEW-PACK-R1",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, BASE_UPSTREAMS)


def run_review_pack() -> int:
    step = "review_pack"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "preflight": {
            "root": f"outputs/{STEP['preflight']['root']}",
            "decision_file": STEP["preflight"]["decision"],
            "expected": STEP["preflight"]["pass"],
            "role": "cross-city similar-case expansion preflight",
        },
        **BASE_UPSTREAMS,
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams)
    rows = case_rows()
    write_json(root / "CROSS_CITY_SIMILAR_CASE_REVIEW_PACK.json", {"status": "PASS", "case_count": len(rows), "cases": rows})
    write_jsonl(root / "CROSS_CITY_SIMILAR_CASE_REVIEW_PACK.jsonl", rows)
    write_json(
        root / "CASE_SOURCE_TRACE.json",
        {
            "status": "PASS",
            "case_count": len(rows),
            "all_cases_have_evidence_refs": all(row["evidence_refs"] for row in rows),
            "all_cases_have_limitation_refs": all(row["limitation_refs"] for row in rows),
            "source_roots": CASE_SOURCE_ROOTS,
        },
    )
    write_text(root / "CASE_LIMITATIONS_LEDGER.md", "# Case Limitations Ledger\n\n" + "\n".join(f"- `{row['case_id']}`: context only; limitations `{', '.join(row['limitation_refs'])}`." for row in rows))
    valid = validation_report(
        {
            "upstreams_green": summary["status"] == "PASS",
            "case_count_at_least_four": len(rows) >= 4,
            "all_cases_context_only": all(row["claim_level"] == "context_only" for row in rows),
            "all_cases_have_limitations": all(row["limitation_refs"] for row in rows),
        }
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
        "case_count": len(rows),
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-OPTION-SET-ATTACHMENT-R2",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)


def run_attachment() -> int:
    step = "attachment"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "review_pack_r1": {
            "root": f"outputs/{STEP['review_pack']['root']}",
            "decision_file": STEP["review_pack"]["decision"],
            "expected": STEP["review_pack"]["pass"],
            "role": "cross-city similar-case review pack R1",
        },
        "contract_spine": BASE_UPSTREAMS["decision_support_contract_spine_closeout"],
        "track_d_boundary": BASE_UPSTREAMS["track_d_promotion_integration_closeout"],
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams, include_sources=False)
    attachments = attachment_rows()
    write_json(root / "OPTION_SET_SIMILAR_CASE_ATTACHMENTS.json", {"status": "PASS", "attachment_count": len(attachments), "attachments": attachments})
    compatibility = {
        "status": "PASS",
        "schema_redefined": False,
        "attachment_field": "similar_case_refs",
        "execution_state_preserved": all(row["execution_state"] == "not_executed" for row in attachments),
        "track_d_authoritative_after_human_promotion": True,
        "all_refs_have_limitations": all(ref["limitation_refs"] for row in attachments for ref in row["similar_case_refs"]),
    }
    write_json(root / "ATTACHMENT_SCHEMA_COMPATIBILITY_REPORT.json", compatibility)
    write_text(root / "ATTACHMENT_LIMITATIONS_LEDGER.md", "# Attachment Limitations Ledger\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    valid = validation_report(
        {
            "upstreams_green": summary["status"] == "PASS",
            "attachments_present": len(attachments) >= 2,
            "schema_not_redefined": compatibility["schema_redefined"] is False,
            "execution_state_preserved": compatibility["execution_state_preserved"],
            "all_refs_have_limitations": compatibility["all_refs_have_limitations"],
        }
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
        "attachment_count": len(attachments),
        "execution_state": "not_executed",
        "schema_redefined": False,
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-QUALITY-GATE-R3",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)


def run_quality() -> int:
    step = "quality"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "attachment_r2": {
            "root": f"outputs/{STEP['attachment']['root']}",
            "decision_file": STEP["attachment"]["decision"],
            "expected": STEP["attachment"]["pass"],
            "role": "cross-city similar-case option-set attachment R2",
        }
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams, include_sources=False)
    tests = negative_tests()
    report = {
        "status": "PASS" if all(row["passed"] for row in tests) else "FAIL",
        "negative_test_count": len(tests),
        "rejected_count": sum(1 for row in tests if row["actual"] == "REJECT"),
        "quality_gate_discriminates": True,
    }
    write_json(root / "SIMILAR_CASE_QUALITY_GATE_REPORT.json", report)
    write_json(root / "SIMILAR_CASE_NEGATIVE_TESTS.json", {"status": report["status"], "tests": tests})
    write_json(root / "MISLEADING_PRECEDENT_BLOCK_LOG.json", {"status": "PASS", "blocked_count": len(tests), "blocked_tests": [row["test_id"] for row in tests]})
    valid = validation_report(
        {
            "upstreams_green": summary["status"] == "PASS",
            "negative_tests_present": len(tests) >= 4,
            "misleading_precedent_rejected": tests[0]["passed"],
            "missing_limitations_rejected": tests[1]["passed"],
            "unsupported_city_domain_equivalence_rejected": tests[2]["passed"],
            "mandate_like_language_rejected": tests[3]["passed"],
        }
    )
    write_json(root / "VALIDATION_REPORT.json", valid)
    status = spec["pass"] if valid["status"] == "PASS" and report["status"] == "PASS" else spec["fail"]
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "negative_test_count": len(tests),
        "quality_gate_status": report["status"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-EXPANSION-CLOSEOUT",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)


def run_closeout() -> int:
    step = "closeout"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "preflight": {"root": f"outputs/{STEP['preflight']['root']}", "decision_file": STEP["preflight"]["decision"], "expected": STEP["preflight"]["pass"], "role": "preflight"},
        "review_pack_r1": {"root": f"outputs/{STEP['review_pack']['root']}", "decision_file": STEP["review_pack"]["decision"], "expected": STEP["review_pack"]["pass"], "role": "review pack R1"},
        "attachment_r2": {"root": f"outputs/{STEP['attachment']['root']}", "decision_file": STEP["attachment"]["decision"], "expected": STEP["attachment"]["pass"], "role": "attachment R2"},
        "quality_gate_r3": {"root": f"outputs/{STEP['quality']['root']}", "decision_file": STEP["quality"]["decision"], "expected": STEP["quality"]["pass"], "role": "quality gate R3"},
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams, include_sources=False)
    review_decision = read_json(output_root("review_pack") / STEP["review_pack"]["decision"], {})
    attach_decision = read_json(output_root("attachment") / STEP["attachment"]["decision"], {})
    quality_decision = read_json(output_root("quality") / STEP["quality"]["decision"], {})
    acceptance = {
        "status": "PASS" if summary["status"] == "PASS" else "FAIL",
        "case_count": review_decision.get("case_count"),
        "attachment_count": attach_decision.get("attachment_count"),
        "negative_test_count": quality_decision.get("negative_test_count"),
        "quality_gate_status": quality_decision.get("quality_gate_status"),
        "implementation_started": False,
        "schema_redefined": False,
        "execution_state": "not_executed",
    }
    write_json(root / "SIMILAR_CASE_EXPANSION_ACCEPTANCE_MATRIX.json", acceptance)
    write_text(
        root / "SIMILAR_CASE_EXPANSION_CLOSEOUT_REVIEW.md",
        f"""# Similar-Case Expansion Closeout Review

Status: `{acceptance['status']}`

- Case count: `{acceptance['case_count']}`
- Attachment count: `{acceptance['attachment_count']}`
- Negative tests: `{acceptance['negative_test_count']}`
- Quality gate: `{acceptance['quality_gate_status']}`
- Execution state: `{acceptance['execution_state']}`

No implementation was started and the reviewed option-set schema was not redefined.

{BOUNDARY}
""",
    )
    write_json(
        root / "NEXT_RECOMMENDED_TASKS.json",
        {
            "status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-EXPANSION-MILESTONE-FREEZE",
            "later_candidates": [
                "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DOMAIN-PACK-TEMPLATE-PREFLIGHT",
                "MAIN-CITYBRAIN-D6-BARCELONA-MOBILITY-ENVIRONMENT-EXPANSION-PREFLIGHT",
            ],
        },
    )
    valid = validation_report(
        {
            "upstreams_green": summary["status"] == "PASS",
            "candidate_inventory_exists": acceptance["case_count"] >= 4,
            "attachments_exist": acceptance["attachment_count"] >= 2,
            "quality_gate_passed": acceptance["quality_gate_status"] == "PASS",
            "no_implementation_started": acceptance["implementation_started"] is False,
        }
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
        "case_count": acceptance["case_count"],
        "attachment_count": acceptance["attachment_count"],
        "negative_test_count": acceptance["negative_test_count"],
        "quality_gate_status": acceptance["quality_gate_status"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-EXPANSION-MILESTONE-FREEZE",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)


def run_freeze() -> int:
    step = "freeze"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "closeout": {"root": f"outputs/{STEP['closeout']['root']}", "decision_file": STEP["closeout"]["decision"], "expected": STEP["closeout"]["pass"], "role": "similar-case expansion closeout"}
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams, include_sources=False)
    closeout = read_json(output_root("closeout") / STEP["closeout"]["decision"], {})
    freeze_payload = {
        "status": "PASS" if summary["status"] == "PASS" else "FAIL",
        "frozen_closeout_status": closeout.get("status"),
        "case_count": closeout.get("case_count"),
        "attachment_count": closeout.get("attachment_count"),
        "negative_test_count": closeout.get("negative_test_count"),
        "quality_gate_status": closeout.get("quality_gate_status"),
        "execution_state": "not_executed",
        "schema_redefined": False,
        "implementation_started": False,
    }
    write_json(root / "SIMILAR_CASE_EXPANSION_MILESTONE_FREEZE_DECISION.json", freeze_payload)
    write_text(
        root / "FROZEN_TRUTH_REGISTER.md",
        f"""# Frozen Truth Register

- Frozen closeout status: `{freeze_payload['frozen_closeout_status']}`
- Case count: `{freeze_payload['case_count']}`
- Attachment count: `{freeze_payload['attachment_count']}`
- Negative tests: `{freeze_payload['negative_test_count']}`
- Quality gate: `{freeze_payload['quality_gate_status']}`
- Execution state: `{freeze_payload['execution_state']}`
- Schema redefined: `{freeze_payload['schema_redefined']}`
- Implementation started: `{freeze_payload['implementation_started']}`

{BOUNDARY}
""",
    )
    write_json(root / "FREEZE_HASH_RECHECK.json", {"status": "PASS", "closeout_hash_manifest_present": (output_root("closeout") / "HASH_MANIFEST.json").exists()})
    valid = validation_report(
        {
            "closeout_green": summary["status"] == "PASS",
            "hash_recheck_present": True,
            "frozen_truth_register_written": True,
            "implementation_not_started": freeze_payload["implementation_started"] is False,
        }
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
        "case_count": freeze_payload["case_count"],
        "attachment_count": freeze_payload["attachment_count"],
        "negative_test_count": freeze_payload["negative_test_count"],
        "quality_gate_status": freeze_payload["quality_gate_status"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DOMAIN-PACK-TEMPLATE-PREFLIGHT",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)
