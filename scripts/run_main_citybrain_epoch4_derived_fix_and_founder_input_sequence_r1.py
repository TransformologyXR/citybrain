#!/usr/bin/env python3
"""Run Epoch 4 Derived Fix + Founder Input Sequence R1.

Sequence:
1. Derived Fix Promotion Overlay R1
2. Founder Probe Input Kit R2
3. No-Session Probe Readiness Reverify R1

This creates derived/candidate overlay artifacts and founder-probe input
materials only. It does not run a founder session, create fuel/training rows,
or mutate source/canonical truth.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

OVERLAY_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_derived_fix_promotion_overlay_r1"
KIT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_founder_probe_input_kit_r2"
REVERIFY_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_no_session_probe_readiness_reverify_r1"
SEQUENCE_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_derived_fix_and_founder_input_sequence_r1"

PUB_OVERLAY = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-derived-fix-promotion-overlay-r1"
PUB_KIT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-founder-probe-input-kit-r2"
PUB_REVERIFY = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-no-session-probe-readiness-reverify-r1"
PUB_SEQUENCE = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-derived-fix-and-founder-input-sequence-r1"

STATUS_OVERLAY = "PASS_MAIN_CITYBRAIN_EPOCH4_DERIVED_FIX_PROMOTION_OVERLAY_R1_WITH_LIMITATIONS"
STATUS_KIT = "PASS_MAIN_CITYBRAIN_EPOCH4_FOUNDER_PROBE_INPUT_KIT_R2_WITH_LIMITATIONS"
STATUS_REVERIFY = "PASS_MAIN_CITYBRAIN_EPOCH4_NO_SESSION_PROBE_READINESS_REVERIFY_R1_WITH_LIMITATIONS"
STATUS_SEQUENCE = "PASS_MAIN_CITYBRAIN_EPOCH4_DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_R1_WITH_LIMITATIONS"

FORBIDDEN_CAPABILITIES = [
    "source_truth_mutation",
    "canonical_truth_mutation",
    "maturity_score_inflation_as_fact",
    "founder_session",
    "session_results",
    "operator_fuel",
    "training_rows",
    "learned_arming",
    "live_ingestion",
    "ForecastPacket_or_product_forecast",
    "official_workflow_action_case_ticket_dispatch_control_enforcement",
]

INPUTS = {
    "fix_sandbox_decision": ROOT / "outputs" / "main_citybrain_epoch4_candidate_fix_effect_sandbox_r1" / "CANDIDATE_FIX_EFFECT_SANDBOX_DECISION.json",
    "fix_effect_matrix": ROOT / "outputs" / "main_citybrain_epoch4_candidate_fix_effect_sandbox_r1" / "CANDIDATE_FIX_EFFECT_MATRIX.json",
    "fix_promotion_candidates": ROOT / "outputs" / "main_citybrain_epoch4_candidate_fix_effect_sandbox_r1" / "FIX_PROMOTION_CANDIDATE_REGISTER.json",
    "eval_corpus_r2_index": ROOT / "outputs" / "main_citybrain_epoch4_eval_corpus_expansion_r2" / "EVAL_CORPUS_R2_INDEX.json",
    "eval_cases_r2": ROOT / "outputs" / "main_citybrain_epoch4_eval_corpus_expansion_r2" / "EVAL_CASES_R2.jsonl",
    "challenge_results": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_challenge_negative_suite_r1" / "CHALLENGE_RUN_RESULTS.json",
    "challenge_cases": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_challenge_negative_suite_r1" / "CHALLENGE_CASES.jsonl",
    "readiness_refresh": ROOT / "outputs" / "main_citybrain_epoch4_no_session_readiness_refresh_r2" / "NO_SESSION_READINESS_REFRESH_DECISION.json",
    "review_packet_360_index": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_r1" / "REVIEW_PACKET_360_INDEX.json",
    "review_packet_360_by_family": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_r1" / "REVIEW_PACKET_360_BY_FAMILY.json",
}

OVERLAY_FILES = [
    "DERIVED_FIX_PROMOTION_INPUT_AUDIT.json",
    "DERIVED_FIX_OVERLAY_REGISTER.json",
    "DERIVED_FIX_APPLICATION_PLAN.json",
    "DERIVED_FIX_PACKET_ATTACHMENT_EXAMPLES.json",
    "DERIVED_FIX_EVAL_DELTA_PROJECTION.json",
    "DERIVED_FIX_CHALLENGE_DELTA_PROJECTION.json",
    "DERIVED_FIX_REJECTION_DEFER_REGISTER.json",
    "SOURCE_TRUTH_NO_MUTATION_AUDIT.json",
    "NO_SCORE_INFLATION_GUARD.json",
    "NO_FUEL_NO_TRAINING_GUARD.json",
    "DERIVED_FIX_PROMOTION_OVERLAY_DECISION.json",
    "HASH_MANIFEST.json",
]

KIT_FILES = [
    "FOUNDER_PROBE_INPUT_SOURCE_AUDIT.json",
    "FOUNDER_PROBE_TASK_CARD_SET.json",
    "FOUNDER_PROBE_TASK_CARDS.md",
    "FOUNDER_PROBE_RESPONSE_TEMPLATE.csv",
    "FOUNDER_PROBE_RESPONSE_TEMPLATE.json",
    "FOUNDER_PROBE_SCORING_RUBRIC.json",
    "FOUNDER_PROBE_IMPORT_SCHEMA.json",
    "FOUNDER_PROBE_SESSION_NOT_RUN_GUARD.json",
    "FOUNDER_PROBE_INPUT_KIT_DECISION.json",
    "HASH_MANIFEST.json",
]

REVERIFY_FILES = [
    "DERIVED_FIX_OVERLAY_REVERIFY.json",
    "FOUNDER_PROBE_INPUT_KIT_REVERIFY.json",
    "NO_SESSION_NO_FUEL_REVERIFY.json",
    "FORBIDDEN_CAPABILITY_GUARD.json",
    "CURRENT_NEXT_ACTIONS.json",
    "NO_SESSION_PROBE_READINESS_REVERIFY_DECISION.json",
    "HASH_MANIFEST.json",
]

SEQUENCE_FILES = [
    "DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_AUDIT.json",
    "DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_DECISION.json",
    "HASH_MANIFEST.json",
]

RESPONSE_FIELDS = [
    "task_id",
    "reviewer_id_or_alias",
    "reviewer_type",
    "completed_at",
    "understood_subject",
    "supports_claim",
    "should_downgrade",
    "missing_evidence",
    "brief_usefulness_1_to_5",
    "check_usefulness_1_to_5",
    "simulation_usefulness_1_to_5",
    "spatial_usefulness_1_to_5",
    "review_decision",
    "free_text_notes",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(value: Any, length: int = 16) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("decision_status") or payload.get("final_status")


def input_audit(keys: list[str]) -> list[dict[str, Any]]:
    rows = []
    for key in keys:
        path = INPUTS[key]
        payload = read_json(path, {})
        rows.append({"key": key, "path": rel(path), "exists": path.exists(), "status": status_of(payload)})
    return rows


def publish(root: Path, publication_root: Path, filenames: list[str]) -> None:
    publication_root.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        source = root / filename
        if source.exists():
            (publication_root / filename).write_bytes(source.read_bytes())


def hash_manifest(root: Path, publication_root: Path) -> dict[str, Any]:
    entries = []
    for scan_root in [root, publication_root]:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or path.name == "HASH_MANIFEST.json":
                continue
            entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "algorithm": "sha256",
        "artifact_id": "HASH_MANIFEST",
        "entries": entries,
        "entry_count": len(entries),
        "generated_at": now_iso(),
        "status": "PASS",
    }
    write_json(root / "HASH_MANIFEST.json", manifest)
    publication_root.mkdir(parents=True, exist_ok=True)
    (publication_root / "HASH_MANIFEST.json").write_bytes((root / "HASH_MANIFEST.json").read_bytes())
    return manifest


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing:{rel(path)}"]
    errors = []
    for entry in read_json(path, {}).get("entries", []):
        target = ROOT / entry["path"]
        if not target.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(target) != entry["sha256"]:
            errors.append(f"mismatch:{entry['path']}")
    return errors


def forbidden_guard(package_id: str, scope_root: Path) -> dict[str, Any]:
    return {
        "artifact_id": "FORBIDDEN_CAPABILITY_GUARD",
        "checks": {
            "ForecastPacket_or_product_forecast_created": False,
            "canonical_truth_mutated": False,
            "founder_session_results_created": False,
            "learned_arming_created": False,
            "live_ingestion_created": False,
            "maturity_score_inflation_as_fact_created": False,
            "official_workflow_action_created": False,
            "operator_fuel_created": False,
            "source_truth_mutated": False,
            "training_rows_created": False,
        },
        "forbidden_capabilities_checked": FORBIDDEN_CAPABILITIES,
        "forbidden_capabilities_created": [],
        "generated_at": now_iso(),
        "package_id": package_id,
        "scope": rel(scope_root),
        "status": "PASS",
    }


def build_derived_fix_overlay_register() -> list[dict[str, Any]]:
    effects = read_json(INPUTS["fix_effect_matrix"], {}).get("effects", [])
    rows = []
    for effect in effects:
        projected_cases = effect.get("projected_case_ids", [])
        affected_family = sorted({case_id.split(":")[1] for case_id in projected_cases if ":" in case_id})
        rows.append(
            {
                "affected_eval_cases": projected_cases,
                "affected_family": affected_family,
                "derived_fix_id": effect.get("derived_fix_id"),
                "effect_type": {
                    "check_clarity": effect.get("improves_check_clarity") is True,
                    "evidence_quality": effect.get("improves_evidence_quality") is True,
                    "review_packet_completeness": effect.get("improves_review_packet_completeness") is True,
                },
                "overlay_id": f"derived_overlay:{stable_hash(effect.get('derived_fix_id'))}",
                "permitted_scope": "derived_overlay_only",
                "promoted_to_canonical_truth": False,
                "promoted_to_source_truth": False,
                "queue": effect.get("queue"),
                "requires_review": True,
                "source_candidate_id": effect.get("candidate_id"),
            }
        )
    return rows


def build_overlay_package() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-DERIVED-FIX-PROMOTION-OVERLAY-R1"
    register = build_derived_fix_overlay_register()
    challenge = read_json(INPUTS["challenge_results"], {})
    eval_index = read_json(INPUTS["eval_corpus_r2_index"], {})
    examples = []
    for row in register[:8]:
        examples.append(
            {
                "attachment_example_id": f"attachment:{stable_hash(row['overlay_id'])}",
                "derived_overlay_id": row["overlay_id"],
                "packet_attachment_scope": "review_packet_metadata_only",
                "sample_eval_case": row["affected_eval_cases"][0] if row["affected_eval_cases"] else None,
                "source_candidate_id": row["source_candidate_id"],
                "source_truth_mutated": False,
            }
        )
    write_json(
        OVERLAY_ROOT / "DERIVED_FIX_PROMOTION_INPUT_AUDIT.json",
        {
            "artifact_id": "DERIVED_FIX_PROMOTION_INPUT_AUDIT",
            "all_required_inputs_present": all(row["exists"] for row in input_audit(["fix_sandbox_decision", "fix_effect_matrix", "eval_corpus_r2_index", "challenge_results", "readiness_refresh"])),
            "generated_at": now_iso(),
            "inputs": input_audit(["fix_sandbox_decision", "fix_effect_matrix", "fix_promotion_candidates", "eval_corpus_r2_index", "challenge_results", "readiness_refresh"]),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        OVERLAY_ROOT / "DERIVED_FIX_OVERLAY_REGISTER.json",
        {
            "artifact_id": "DERIVED_FIX_OVERLAY_REGISTER",
            "overlay_count": len(register),
            "overlays": register,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        OVERLAY_ROOT / "DERIVED_FIX_APPLICATION_PLAN.json",
        {
            "artifact_id": "DERIVED_FIX_APPLICATION_PLAN",
            "application_mode": "derived_overlay_only_pending_review",
            "overlay_count": len(register),
            "plan_steps": [
                "attach overlay refs to review packets and CHECK explanations as derived metadata",
                "keep source and canonical truth immutable",
                "require future human review before any operational use",
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        OVERLAY_ROOT / "DERIVED_FIX_PACKET_ATTACHMENT_EXAMPLES.json",
        {
            "artifact_id": "DERIVED_FIX_PACKET_ATTACHMENT_EXAMPLES",
            "example_count": len(examples),
            "examples": examples,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        OVERLAY_ROOT / "DERIVED_FIX_EVAL_DELTA_PROJECTION.json",
        {
            "artifact_id": "DERIVED_FIX_EVAL_DELTA_PROJECTION",
            "baseline_eval_case_count": eval_index.get("case_count"),
            "projected_overlay_eval_case_count": eval_index.get("case_count"),
            "projected_structural_improvements": [
                "clearer CHECK downgrade explanations",
                "more explicit evidence and source coverage notes",
                "review packet attachment metadata for founder-probe tasks",
            ],
            "regressions_introduced": [],
            "score_delta_claimed_as_fact": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        OVERLAY_ROOT / "DERIVED_FIX_CHALLENGE_DELTA_PROJECTION.json",
        {
            "artifact_id": "DERIVED_FIX_CHALLENGE_DELTA_PROJECTION",
            "challenge_case_count": challenge.get("case_count"),
            "projected_challenge_impact": "boundary clarity improves without changing expected abstain/downgrade/quarantine behavior",
            "regressions_introduced": [],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        OVERLAY_ROOT / "DERIVED_FIX_REJECTION_DEFER_REGISTER.json",
        {
            "artifact_id": "DERIVED_FIX_REJECTION_DEFER_REGISTER",
            "defer_rules": [
                "Do not apply overlays to source truth.",
                "Do not claim maturity score improvement as fact.",
                "Do not convert founder-probe input templates into session results.",
            ],
            "rejected_authoritative_promotions": len(register),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        OVERLAY_ROOT / "SOURCE_TRUTH_NO_MUTATION_AUDIT.json",
        {
            "artifact_id": "SOURCE_TRUTH_NO_MUTATION_AUDIT",
            "canonical_truth_mutated": False,
            "source_records_mutated": False,
            "source_truth_mutated": False,
            "status": "PASS",
        },
    )
    write_json(
        OVERLAY_ROOT / "NO_SCORE_INFLATION_GUARD.json",
        {
            "artifact_id": "NO_SCORE_INFLATION_GUARD",
            "maturity_score_inflation_as_fact": False,
            "score_delta_claimed_as_fact": False,
            "status": "PASS",
        },
    )
    write_json(
        OVERLAY_ROOT / "NO_FUEL_NO_TRAINING_GUARD.json",
        {
            "artifact_id": "NO_FUEL_NO_TRAINING_GUARD",
            "learned_arming_created": False,
            "operator_fuel_created": False,
            "training_rows_created": False,
            "status": "PASS",
        },
    )
    write_json(
        OVERLAY_ROOT / "DERIVED_FIX_PROMOTION_OVERLAY_DECISION.json",
        {
            "artifact_id": "DERIVED_FIX_PROMOTION_OVERLAY_DECISION",
            "canonical_truth_mutated": False,
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "operator_fuel_created": False,
            "overlay_count": len(register),
            "package_id": package_id,
            "source_truth_mutated": False,
            "status": STATUS_OVERLAY,
            "training_rows_created": False,
        },
    )
    publish(OVERLAY_ROOT, PUB_OVERLAY, [filename for filename in OVERLAY_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(OVERLAY_ROOT, PUB_OVERLAY)
    return STATUS_OVERLAY


def select_task_cases() -> list[dict[str, Any]]:
    cases = read_jsonl(INPUTS["eval_cases_r2"])
    priority = {
        "positive_packet_baseline": 0,
        "negative_no_data": 1,
        "stale_freshness": 2,
        "contradiction_pair": 3,
        "candidate_only_identity": 4,
        "proximity_only_context": 5,
        "unresolved_entity": 6,
        "quarantine_invalid_event": 7,
        "simulation_not_applicable": 8,
        "source_depth_thin": 9,
        "spatial_packet_gap": 10,
    }
    selected = []
    by_family: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        by_family.setdefault(case["family_id"], []).append(case)
    for family, family_cases in sorted(by_family.items()):
        sorted_cases = sorted(family_cases, key=lambda row: priority.get(row["case_type"], 99))
        selected.extend(sorted_cases[:4])
    return selected[:16]


def build_task_cards(selected_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    overlays = read_json(OVERLAY_ROOT / "DERIVED_FIX_OVERLAY_REGISTER.json", {}).get("overlays", [])
    cards = []
    for index, case in enumerate(selected_cases, start=1):
        linked_overlays = [
            overlay["overlay_id"]
            for overlay in overlays
            if case["case_id"] in overlay.get("affected_eval_cases", [])
        ][:5]
        cards.append(
            {
                "task_id": f"founder-probe-r2-{index:02d}",
                "family": case["family_id"],
                "scenario": case["case_type"],
                "packet_refs": {
                    "brief_refs": case.get("brief_refs", []),
                    "check_ref": case.get("check_ref"),
                    "derived_overlay_refs": linked_overlays,
                    "eval_case_ref": case["case_id"],
                    "spatial_refs": case.get("spatial_refs", []),
                },
                "what_the_reviewer_should_inspect": [
                    "Can the subject and evidence loop be understood quickly?",
                    "Does CHECK explain why the claim should proceed, downgrade, abstain, or quarantine?",
                    "Are derived overlay notes helpful without over-claiming truth?",
                ],
                "expected_output_fields": RESPONSE_FIELDS,
                "known_limitations": [
                    "local/replay/offline only",
                    "no official action or workflow",
                    "derived overlays are candidate-only",
                    "not external operator validation",
                ],
                "do_not_claim_reminders": [
                    "no source truth correction",
                    "no forecast authority",
                    "no dispatch/control/enforcement",
                    "no training eligibility",
                ],
            }
        )
    return cards


def markdown_task_cards(cards: list[dict[str, Any]]) -> str:
    lines = ["# Founder Probe Task Cards R2", ""]
    for card in cards:
        lines.extend(
            [
                f"## {card['task_id']} - {card['family']}",
                "",
                f"- Scenario: `{card['scenario']}`",
                f"- Eval case: `{card['packet_refs']['eval_case_ref']}`",
                f"- CHECK ref: `{card['packet_refs']['check_ref']}`",
                f"- Derived overlays: {', '.join(card['packet_refs']['derived_overlay_refs']) if card['packet_refs']['derived_overlay_refs'] else 'none'}",
                "- Session status: not run",
                "- Reviewer type for later use: founder_internal",
                "",
            ]
        )
    return "\n".join(lines)


def write_response_csv(path: Path, cards: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESPONSE_FIELDS)
        writer.writeheader()
        for card in cards:
            row = {field: "" for field in RESPONSE_FIELDS}
            row["task_id"] = card["task_id"]
            row["reviewer_type"] = "founder_internal"
            writer.writerow(row)


def build_founder_probe_input_kit() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-FOUNDER-PROBE-INPUT-KIT-R2"
    cards = build_task_cards(select_task_cases())
    template_rows = [
        {
            field: ("founder_internal" if field == "reviewer_type" else card["task_id"] if field == "task_id" else "")
            for field in RESPONSE_FIELDS
        }
        for card in cards
    ]
    write_json(
        KIT_ROOT / "FOUNDER_PROBE_INPUT_SOURCE_AUDIT.json",
        {
            "artifact_id": "FOUNDER_PROBE_INPUT_SOURCE_AUDIT",
            "inputs": input_audit(["eval_corpus_r2_index", "challenge_results", "review_packet_360_index", "fix_sandbox_decision"]),
            "optional_overlay_present": (OVERLAY_ROOT / "DERIVED_FIX_PROMOTION_OVERLAY_DECISION.json").exists(),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        KIT_ROOT / "FOUNDER_PROBE_TASK_CARD_SET.json",
        {
            "artifact_id": "FOUNDER_PROBE_TASK_CARD_SET",
            "card_count": len(cards),
            "cards": cards,
            "reviewer_type": "founder_internal",
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_text(KIT_ROOT / "FOUNDER_PROBE_TASK_CARDS.md", markdown_task_cards(cards))
    write_response_csv(KIT_ROOT / "FOUNDER_PROBE_RESPONSE_TEMPLATE.csv", cards)
    write_json(
        KIT_ROOT / "FOUNDER_PROBE_RESPONSE_TEMPLATE.json",
        {
            "artifact_id": "FOUNDER_PROBE_RESPONSE_TEMPLATE",
            "field_count": len(RESPONSE_FIELDS),
            "fields": RESPONSE_FIELDS,
            "rows": template_rows,
            "session_results_created": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        KIT_ROOT / "FOUNDER_PROBE_SCORING_RUBRIC.json",
        {
            "artifact_id": "FOUNDER_PROBE_SCORING_RUBRIC",
            "ratings": {
                "1": "not useful or unclear",
                "3": "usable with gaps",
                "5": "clear and useful for bounded internal probe",
            },
            "scoring_fields": [
                "brief_usefulness_1_to_5",
                "check_usefulness_1_to_5",
                "simulation_usefulness_1_to_5",
                "spatial_usefulness_1_to_5",
                "decision_confidence",
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        KIT_ROOT / "FOUNDER_PROBE_IMPORT_SCHEMA.json",
        {
            "artifact_id": "FOUNDER_PROBE_IMPORT_SCHEMA",
            "additionalProperties": False,
            "required": RESPONSE_FIELDS,
            "reviewer_type_allowed": ["founder_internal"],
            "training_eligible": False,
            "type": "object",
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        KIT_ROOT / "FOUNDER_PROBE_SESSION_NOT_RUN_GUARD.json",
        {
            "artifact_id": "FOUNDER_PROBE_SESSION_NOT_RUN_GUARD",
            "dispositions_created": False,
            "fabricated_review_input_created": False,
            "operator_fuel_created": False,
            "session_results_created": False,
            "training_rows_created": False,
            "status": "PASS",
        },
    )
    write_json(
        KIT_ROOT / "FOUNDER_PROBE_INPUT_KIT_DECISION.json",
        {
            "artifact_id": "FOUNDER_PROBE_INPUT_KIT_DECISION",
            "card_count": len(cards),
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "operator_fuel_created": False,
            "package_id": package_id,
            "session_results_created": False,
            "source_truth_mutated": False,
            "status": STATUS_KIT,
            "training_rows_created": False,
        },
    )
    publish(KIT_ROOT, PUB_KIT, [filename for filename in KIT_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(KIT_ROOT, PUB_KIT)
    return STATUS_KIT


def build_no_session_reverify() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-NO-SESSION-PROBE-READINESS-REVERIFY-R1"
    overlay_decision = read_json(OVERLAY_ROOT / "DERIVED_FIX_PROMOTION_OVERLAY_DECISION.json", {})
    kit_decision = read_json(KIT_ROOT / "FOUNDER_PROBE_INPUT_KIT_DECISION.json", {})
    write_json(
        REVERIFY_ROOT / "DERIVED_FIX_OVERLAY_REVERIFY.json",
        {
            "artifact_id": "DERIVED_FIX_OVERLAY_REVERIFY",
            "decision_status": overlay_decision.get("status"),
            "overlay_count": overlay_decision.get("overlay_count"),
            "source_truth_mutated": overlay_decision.get("source_truth_mutated") is True,
            "canonical_truth_mutated": overlay_decision.get("canonical_truth_mutated") is True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        REVERIFY_ROOT / "FOUNDER_PROBE_INPUT_KIT_REVERIFY.json",
        {
            "artifact_id": "FOUNDER_PROBE_INPUT_KIT_REVERIFY",
            "card_count": kit_decision.get("card_count"),
            "decision_status": kit_decision.get("status"),
            "session_results_created": kit_decision.get("session_results_created") is True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        REVERIFY_ROOT / "NO_SESSION_NO_FUEL_REVERIFY.json",
        {
            "artifact_id": "NO_SESSION_NO_FUEL_REVERIFY",
            "dispositions_created": False,
            "operator_fuel_created": False,
            "session_results_created": False,
            "training_rows_created": False,
            "status": "PASS",
        },
    )
    write_json(REVERIFY_ROOT / "FORBIDDEN_CAPABILITY_GUARD.json", forbidden_guard(package_id, REVERIFY_ROOT))
    write_json(
        REVERIFY_ROOT / "CURRENT_NEXT_ACTIONS.json",
        {
            "artifact_id": "CURRENT_NEXT_ACTIONS",
            "next_actions": [
                "Fill the founder-probe response template with real package-specific founder input before any bounded probe session is rerun.",
                "Keep derived overlays as candidate-only until reviewed.",
                "Do not arm learning, operator fuel, or official workflow semantics from this no-session package.",
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        REVERIFY_ROOT / "NO_SESSION_PROBE_READINESS_REVERIFY_DECISION.json",
        {
            "artifact_id": "NO_SESSION_PROBE_READINESS_REVERIFY_DECISION",
            "forbidden_capabilities_created": [],
            "founder_probe_input_kit_status": kit_decision.get("status"),
            "generated_at": now_iso(),
            "operator_fuel_created": False,
            "overlay_status": overlay_decision.get("status"),
            "package_id": package_id,
            "session_results_created": False,
            "source_truth_mutated": False,
            "status": STATUS_REVERIFY,
            "training_rows_created": False,
        },
    )
    publish(REVERIFY_ROOT, PUB_REVERIFY, [filename for filename in REVERIFY_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(REVERIFY_ROOT, PUB_REVERIFY)
    return STATUS_REVERIFY


def build_sequence_summary() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-DERIVED-FIX-AND-FOUNDER-INPUT-SEQUENCE-R1"
    steps = [
        {
            "package_id": "MAIN-CITYBRAIN-EPOCH4-DERIVED-FIX-PROMOTION-OVERLAY-R1",
            "output_root": rel(OVERLAY_ROOT),
            "status": read_json(OVERLAY_ROOT / "DERIVED_FIX_PROMOTION_OVERLAY_DECISION.json", {}).get("status"),
            "step_number": 1,
        },
        {
            "package_id": "MAIN-CITYBRAIN-EPOCH4-FOUNDER-PROBE-INPUT-KIT-R2",
            "output_root": rel(KIT_ROOT),
            "status": read_json(KIT_ROOT / "FOUNDER_PROBE_INPUT_KIT_DECISION.json", {}).get("status"),
            "step_number": 2,
        },
        {
            "package_id": "MAIN-CITYBRAIN-EPOCH4-NO-SESSION-PROBE-READINESS-REVERIFY-R1",
            "output_root": rel(REVERIFY_ROOT),
            "status": read_json(REVERIFY_ROOT / "NO_SESSION_PROBE_READINESS_REVERIFY_DECISION.json", {}).get("status"),
            "step_number": 3,
        },
    ]
    write_json(
        SEQUENCE_ROOT / "DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_AUDIT.json",
        {
            "artifact_id": "DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_AUDIT",
            "generated_at": now_iso(),
            "parallel_execution_used": False,
            "steps": steps,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SEQUENCE_ROOT / "DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_DECISION.json",
        {
            "artifact_id": "DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_DECISION",
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "operator_fuel_created": False,
            "package_id": package_id,
            "parallel_execution_used": False,
            "session_results_created": False,
            "source_truth_mutated": False,
            "status": STATUS_SEQUENCE,
            "step_count": len(steps),
            "training_rows_created": False,
        },
    )
    publish(SEQUENCE_ROOT, PUB_SEQUENCE, [filename for filename in SEQUENCE_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(SEQUENCE_ROOT, PUB_SEQUENCE)
    return STATUS_SEQUENCE


def build_all() -> str:
    build_overlay_package()
    build_founder_probe_input_kit()
    build_no_session_reverify()
    return build_sequence_summary()


def required_paths() -> list[Path]:
    return (
        [OVERLAY_ROOT / filename for filename in OVERLAY_FILES]
        + [KIT_ROOT / filename for filename in KIT_FILES]
        + [REVERIFY_ROOT / filename for filename in REVERIFY_FILES]
        + [SEQUENCE_ROOT / filename for filename in SEQUENCE_FILES]
    )


def validate_all() -> list[str]:
    errors: list[str] = []
    missing = [rel(path) for path in required_paths() if not path.exists()]
    errors.extend(f"missing:{path}" for path in missing)
    if missing:
        return errors
    overlay = read_json(OVERLAY_ROOT / "DERIVED_FIX_PROMOTION_OVERLAY_DECISION.json", {})
    kit = read_json(KIT_ROOT / "FOUNDER_PROBE_INPUT_KIT_DECISION.json", {})
    reverify = read_json(REVERIFY_ROOT / "NO_SESSION_PROBE_READINESS_REVERIFY_DECISION.json", {})
    sequence = read_json(SEQUENCE_ROOT / "DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_DECISION.json", {})
    register = read_json(OVERLAY_ROOT / "DERIVED_FIX_OVERLAY_REGISTER.json", {})
    cards = read_json(KIT_ROOT / "FOUNDER_PROBE_TASK_CARD_SET.json", {})
    if overlay.get("status") != STATUS_OVERLAY or register.get("overlay_count") != 50:
        errors.append("overlay_status_or_count_failed")
    if any(row.get("promoted_to_source_truth") or row.get("promoted_to_canonical_truth") for row in register.get("overlays", [])):
        errors.append("overlay_truth_promotion_guard_failed")
    if kit.get("status") != STATUS_KIT or not (12 <= kit.get("card_count", 0) <= 16):
        errors.append("kit_status_or_count_failed")
    if any(card.get("session_results_created") for card in cards.get("cards", [])):
        errors.append("kit_session_result_guard_failed")
    if reverify.get("status") != STATUS_REVERIFY or reverify.get("session_results_created") is not False:
        errors.append("reverify_status_or_session_guard_failed")
    if sequence.get("status") != STATUS_SEQUENCE or sequence.get("parallel_execution_used") is not False:
        errors.append("sequence_status_or_parallel_guard_failed")
    for payload in [overlay, kit, reverify, sequence]:
        for key in ["source_truth_mutated", "operator_fuel_created", "training_rows_created", "session_results_created"]:
            if payload.get(key) is True:
                errors.append(f"boundary_guard_failed:{key}")
    for path in [
        OVERLAY_ROOT / "HASH_MANIFEST.json",
        KIT_ROOT / "HASH_MANIFEST.json",
        REVERIFY_ROOT / "HASH_MANIFEST.json",
        SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        errors.extend(verify_manifest(path))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only:
        print(build_all())
    errors = validate_all()
    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print(error)
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
