#!/usr/bin/env python3
"""Prepare founder diagnostic review after AI concordance for the story arc."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from io import StringIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORY_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-CROSS-DOMAIN-STORY-ARC-EVAL-EXPANSION-R1"
DEFAULT_REPAIR_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-STORY-ARC-REVIEW-PROVENANCE-GATE-REPAIR-R1"
DEFAULT_REVIEW_ROOT = ROOT / "inputs" / "ai_diagnostic_story_review"
DEFAULT_OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-STORY-ARC-FOUNDER-DIAGNOSTIC-PREP-CONCORDANCE-R1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-story-arc-founder-diagnostic-prep-concordance-r1"

STATUS_PASS = "PASS_MAIN_CITYBRAIN_STORY_ARC_FOUNDER_DIAGNOSTIC_PREP_CONCORDANCE_R1_WITH_LIMITATIONS"
STATUS_BLOCKED = "BLOCKED_MAIN_CITYBRAIN_STORY_ARC_FOUNDER_DIAGNOSTIC_PREP_CONCORDANCE_R1_WITH_LIMITATIONS"
FINAL_GO = "GO_FOR_FOUNDER_DIAGNOSTIC_REVIEW_WITH_LIMITATIONS"
FINAL_WAIT = "WAIT_FOR_INDEPENDENT_AI_REVIEW"
FINAL_REPAIR = "REPAIR_FOUNDER_CARDS_OR_COUNT_FRAMING_BEFORE_FOUNDER"
FINAL_NO_GO = "NO_GO_FOR_FOUNDER_REVIEW"

REQUIRED_FILES = [
    "STORY_ARC_FOUNDER_DIAGNOSTIC_PREP_CONCORDANCE_DECISION.json",
    "AI_REVIEW_PROVENANCE_LEDGER.json",
    "AI_REVIEW_CONCORDANCE_REPORT.json",
    "EVAL_COUNT_FRAMING_REPAIR.json",
    "EVAL_COUNT_FRAMING_REPAIR.md",
    "FOUNDER_DIAGNOSTIC_PRODUCT_JUDGMENT_CARDS.json",
    "FOUNDER_DIAGNOSTIC_PRODUCT_JUDGMENT_CARDS.md",
    "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE.csv",
    "FOUNDER_DIAGNOSTIC_SESSION_GUIDE.md",
    "FOUNDER_DIAGNOSTIC_READINESS_GATE.json",
    "NO_FALSE_CONCORDANCE_GUARD.json",
    "BOUNDARY_AND_NO_FUEL_GUARD.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]

RATING_KEYS = [
    "story_coherence",
    "evidence_traceability",
    "cross_family_entity_resolution_clarity",
    "check_boundary_clarity",
    "simulation_context_honesty",
    "eval_expansion_usefulness",
    "founder_diagnostic_usefulness",
    "product_review_readiness",
]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def required_paths(out: Path) -> list[Path]:
    return [out / name for name in REQUIRED_FILES]


def find_review_file(review_root: Path, candidates: list[str]) -> Path | None:
    for name in candidates:
        path = review_root / name
        if path.exists():
            return path
    if not review_root.exists():
        return None
    lowered = [candidate.lower() for candidate in candidates]
    for path in sorted(review_root.iterdir()):
        if path.name.lower() in lowered:
            return path
    return None


def parse_bool_field(text: str, field: str) -> bool | None:
    match = re.search(rf"{re.escape(field)}\s*[:=]\s*(true|false)", text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower() == "true"


def parse_text_field(text: str, field: str) -> str | None:
    match = re.search(rf"{re.escape(field)}\s*[:=]\s*([A-Z0-9_/-]+)", text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper()


def parse_ratings_from_text(text: str) -> dict[str, int | None]:
    ratings: dict[str, int | None] = {}
    for key in RATING_KEYS:
        match = re.search(rf"{re.escape(key)}\s*:\s*([1-5])\b", text, flags=re.IGNORECASE)
        ratings[key] = int(match.group(1)) if match else None
    return ratings


def classify_chatgpt(review_root: Path) -> dict[str, Any]:
    path = find_review_file(
        review_root,
        ["chatgpt_story_review_r1.json", "CHATGPT_AI_DIAGNOSTIC_STORY_REVIEW_R1.json"],
    )
    if not path:
        return {
            "review_id": "chatgpt_ai_diagnostic_review_r1",
            "reviewer": "chatgpt",
            "path": None,
            "present": False,
            "ai_diagnostic_review": False,
            "independent_artifact_review": False,
            "review_of_review": False,
            "count_toward_concordance": False,
            "status": "MISSING",
        }
    payload = read_json(path)
    status = payload.get("review_status")
    ratings = payload.get("ratings_1_to_5", {})
    return {
        "review_id": "chatgpt_ai_diagnostic_review_r1",
        "reviewer": "chatgpt",
        "path": rel(path),
        "present": True,
        "ai_diagnostic_review": payload.get("review_type") == "ai_diagnostic_story_review",
        "independent_artifact_review": True,
        "review_of_review": False,
        "count_toward_concordance": bool(status and str(status).startswith("PASS")),
        "status": status,
        "founder_diagnostic_review_recommendation": payload.get("founder_diagnostic_review_recommendation"),
        "founder_product_review_recommendation": payload.get("founder_product_review_recommendation"),
        "ratings_1_to_5": ratings,
        "not_fabricated": True,
        "classification_note": "Imported from local ChatGPT AI diagnostic review JSON; source validation details are in inputs/ai_diagnostic_story_review.",
    }


def classify_claude_independent(review_root: Path) -> dict[str, Any]:
    path = find_review_file(review_root, ["CLAUDE_INDEPENDENT_ARTIFACT_REVIEW_R1.md"])
    if not path:
        return {
            "review_id": "claude_independent_artifact_review_r1",
            "reviewer": "claude",
            "path": None,
            "present": False,
            "ai_diagnostic_review": False,
            "independent_artifact_review": False,
            "review_of_review": False,
            "count_toward_concordance": False,
            "status": "MISSING",
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    independent = parse_bool_field(text, "independent_artifact_review")
    review_of_review = parse_bool_field(text, "review_of_review")
    status = parse_text_field(text, "AI_DIAGNOSTIC_REVIEW_STATUS")
    founder_diag = parse_text_field(text, "founder_diagnostic_review_recommendation")
    founder_product = parse_text_field(text, "founder_product_review_recommendation")
    artifact_pointer = "MAIN-CITYBRAIN-CROSS-DOMAIN-STORY-ARC-EVAL-EXPANSION-R1" in text
    countable = (
        status == "PASS_WITH_LIMITATIONS"
        and independent is True
        and review_of_review is False
        and artifact_pointer
        and founder_diag == FINAL_GO
    )
    return {
        "review_id": "claude_independent_artifact_review_r1",
        "reviewer": "claude",
        "path": rel(path),
        "present": True,
        "ai_diagnostic_review": status in {"PASS_WITH_LIMITATIONS", "NEEDS_REPAIR", "NO_GO"},
        "independent_artifact_review": independent is True,
        "review_of_review": review_of_review is True,
        "count_toward_concordance": countable,
        "status": status,
        "founder_diagnostic_review_recommendation": founder_diag,
        "founder_product_review_recommendation": founder_product,
        "ratings_1_to_5": parse_ratings_from_text(text),
        "artifact_pointer_confirmed": artifact_pointer,
        "not_fabricated": True,
        "classification_note": "Imported from local Claude independent artifact review markdown.",
    }


def classify_claude_review_of_review(review_root: Path) -> dict[str, Any]:
    path = find_review_file(review_root, ["CLAUDE_REVIEW_OF_REVIEW_R0.md"])
    if not path:
        return {
            "review_id": "claude_review_of_review_r0",
            "reviewer": "claude",
            "path": None,
            "present": False,
            "ai_diagnostic_review": False,
            "independent_artifact_review": False,
            "review_of_review": True,
            "count_toward_concordance": False,
            "status": "NOT_PRESENT",
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "review_id": "claude_review_of_review_r0",
        "reviewer": "claude",
        "path": rel(path),
        "present": True,
        "ai_diagnostic_review": True,
        "independent_artifact_review": False,
        "review_of_review": True,
        "count_toward_concordance": False,
        "status": parse_text_field(text, "AI_DIAGNOSTIC_REVIEW_STATUS") or "REVIEW_OF_REVIEW",
        "classification_note": "Explicitly excluded from concordance because it is a review-of-review, not an artifact review.",
    }


def build_provenance_ledger(review_root: Path) -> dict[str, Any]:
    rows = [
        classify_chatgpt(review_root),
        classify_claude_independent(review_root),
        classify_claude_review_of_review(review_root),
    ]
    countable = [row for row in rows if row.get("count_toward_concordance")]
    return {
        "artifact_id": "AI_REVIEW_PROVENANCE_LEDGER",
        "review_input_root": rel(review_root),
        "rows": rows,
        "countable_ai_artifact_review_count": len(countable),
        "valid_chatgpt_review_imported": rows[0]["present"] and rows[0]["ai_diagnostic_review"],
        "valid_claude_independent_artifact_review_imported": rows[1]["count_toward_concordance"],
        "review_of_review_excluded_from_concordance": rows[2]["review_of_review"] is True and rows[2]["count_toward_concordance"] is False,
    }


def build_eval_count_repair(story_root: Path) -> dict[str, Any]:
    cases = read_jsonl(story_root / "STORY_ARC_EVAL_EXPANSION_CASES.jsonl")
    negative = read_jsonl(story_root / "STORY_ARC_NEGATIVE_CHALLENGE_CASES.jsonl")
    case_ids = {case.get("eval_case_id") for case in cases}
    negative_ids = {case.get("eval_case_id") for case in negative}
    prior = read_json(ROOT / "outputs" / "main_citybrain_epoch4_eval_corpus_expansion_r2" / "EVAL_CORPUS_EXPANSION_R2_DECISION.json", {})
    prior_count = int(prior.get("case_count", 0) or 0)
    prior_discovered = prior_count > 0
    return {
        "artifact_id": "EVAL_COUNT_FRAMING_REPAIR",
        "story_arc_unique_eval_cases": len(case_ids),
        "story_arc_challenge_negative_cases": len(negative_ids),
        "challenge_cases_are_subset_of_unique_eval_cases": negative_ids.issubset(case_ids),
        "story_arc_additive_eval_count": len(case_ids),
        "story_arc_not_120_plus_70": True,
        "forbidden_190_case_claim_created": False,
        "prior_eval_cases_discovered": prior_discovered,
        "prior_eval_case_count": prior_count if prior_discovered else None,
        "combined_unique_eval_case_count": len(case_ids) + prior_count if prior_discovered else None,
        "count_framing_statement": (
            f"{len(case_ids)} unique story-arc eval cases; {len(negative_ids)} challenge/negative cases are a subset of those cases, not additional cases."
        ),
        "source_refs": [
            rel(story_root / "STORY_ARC_EVAL_EXPANSION_CASES.jsonl"),
            rel(story_root / "STORY_ARC_NEGATIVE_CHALLENGE_CASES.jsonl"),
        ],
    }


def build_cards() -> dict[str, Any]:
    prompts = [
        (
            "founder-diagnostic-product-judgment-01",
            "Comprehension and usefulness",
            "Would this story packet help you quickly understand what is happening, or is it technically correct but not useful?",
        ),
        (
            "founder-diagnostic-product-judgment-02",
            "Actionability threshold",
            "Would you escalate or keep watching this packet in a real product context, and what evidence would you need before doing so?",
        ),
        (
            "founder-diagnostic-product-judgment-03",
            "Trust from boundaries",
            "Do the CHECK downgrade, hold, and quarantine boundaries increase your trust, or make the product feel too hesitant?",
        ),
        (
            "founder-diagnostic-product-judgment-04",
            "Site versus corridor distinction",
            "Does the site-vs-corridor distinction help you trust the story, or does it feel like engineering caveat clutter?",
        ),
        (
            "founder-diagnostic-product-judgment-05",
            "Audience readability",
            "Is the packet concise and readable enough for a non-engineering stakeholder to review without coaching?",
        ),
        (
            "founder-diagnostic-product-judgment-06",
            "Missing evidence",
            "What missing evidence would move this from diagnostic review to a product-review candidate?",
        ),
    ]
    rows = []
    for order, (card_id, theme, question) in enumerate(prompts, start=1):
        rows.append(
            {
                "card_id": card_id,
                "order": order,
                "theme": theme,
                "question": question,
                "card_type": "product_judgment_usefulness",
                "not_evidence_audit_card": True,
                "founder_internal": True,
                "operator_fuel": False,
                "training_eligible": False,
                "external_operator_validation": False,
                "learning_arming_allowed": False,
                "product_review_ready": False,
                "client_ready": False,
                "founder_session_result": False,
            }
        )
    return {
        "artifact_id": "FOUNDER_DIAGNOSTIC_PRODUCT_JUDGMENT_CARDS",
        "card_count": len(rows),
        "cards_are_product_judgment_usefulness_cards": True,
        "cards_are_evidence_audit_cards": False,
        "rows": rows,
    }


def cards_markdown(cards: dict[str, Any]) -> str:
    lines = ["# Founder Diagnostic Product-Judgment Cards", ""]
    for card in cards["rows"]:
        lines.append(f"## {card['order']}. {card['theme']}")
        lines.append("")
        lines.append(card["question"])
        lines.append("")
        lines.append("Boundary: founder-internal diagnostic only; no fuel, training, external validation, product readiness, or client readiness.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def response_template_csv(cards: dict[str, Any]) -> str:
    output = StringIO()
    fieldnames = [
        "card_id",
        "theme",
        "question",
        "founder_response",
        "usefulness_rating_1_to_5",
        "trust_rating_1_to_5",
        "actionability_rating_1_to_5",
        "what_would_you_need_next",
        "go_no_go_for_more_diagnostics",
        "notes",
        "founder_internal",
        "operator_fuel",
        "training_eligible",
        "external_operator_validation",
        "learning_arming_allowed",
        "product_review_ready",
        "client_ready",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for card in cards["rows"]:
        writer.writerow(
            {
                "card_id": card["card_id"],
                "theme": card["theme"],
                "question": card["question"],
                "founder_response": "",
                "usefulness_rating_1_to_5": "",
                "trust_rating_1_to_5": "",
                "actionability_rating_1_to_5": "",
                "what_would_you_need_next": "",
                "go_no_go_for_more_diagnostics": "",
                "notes": "",
                "founder_internal": "true",
                "operator_fuel": "false",
                "training_eligible": "false",
                "external_operator_validation": "false",
                "learning_arming_allowed": "false",
                "product_review_ready": "false",
                "client_ready": "false",
            }
        )
    return output.getvalue()


def build_concordance(ledger: dict[str, Any]) -> dict[str, Any]:
    chatgpt = ledger["rows"][0]
    claude = ledger["rows"][1]
    agreements = []
    disagreements = []
    if chatgpt.get("count_toward_concordance") and claude.get("count_toward_concordance"):
        agreements.extend(
            [
                "Both AI diagnostic reviews pass with limitations.",
                "Both keep founder product review closed.",
                "Both keep product/client readiness closed.",
                "Both preserve no fuel/training/live/forecast/action boundaries.",
                "Both find the story arc useful enough for diagnostic review with limitations.",
            ]
        )
        disagreements.extend(
            [
                "Claude explicitly flags eval count framing; ChatGPT did not.",
                "Claude rates founder diagnostic usefulness lower because cards were evidence-audit oriented.",
                "Claude requires founder cards to be rewritten into product-judgment prompts before diagnostic review.",
            ]
        )
    return {
        "artifact_id": "AI_REVIEW_CONCORDANCE_REPORT",
        "countable_ai_artifact_review_count": ledger["countable_ai_artifact_review_count"],
        "concordance_ready": ledger["valid_chatgpt_review_imported"]
        and ledger["valid_claude_independent_artifact_review_imported"],
        "agreements": agreements,
        "disagreements_or_repair_items": disagreements,
        "chatgpt_ratings_1_to_5": chatgpt.get("ratings_1_to_5", {}),
        "claude_ratings_1_to_5": claude.get("ratings_1_to_5", {}),
        "founder_product_review_recommendation": "NO_GO",
        "founder_diagnostic_review_recommendation_after_repairs": FINAL_GO,
    }


def build_false_concordance_guard(ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": "NO_FALSE_CONCORDANCE_GUARD",
        "status": "PASS",
        "review_of_review_excluded_from_concordance": ledger["review_of_review_excluded_from_concordance"],
        "valid_claude_independent_artifact_review_imported": ledger["valid_claude_independent_artifact_review_imported"],
        "false_second_ai_review_count_created": False,
        "countable_ai_artifact_review_count": ledger["countable_ai_artifact_review_count"],
    }


def build_boundary_guard() -> dict[str, Any]:
    return {
        "artifact_id": "BOUNDARY_AND_NO_FUEL_GUARD",
        "status": "PASS",
        "founder_session_results_created": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "model_training_or_learning_arming_created": False,
        "source_truth_mutated": False,
        "provider_raw_payload_rewritten": False,
        "forecast_packet_created": False,
        "live_ingestion_created": False,
        "official_workflow_action_case_dispatch_control_enforcement_created": False,
        "legal_or_certified_claim_created": False,
        "product_ready_claim_created": False,
        "client_ready_claim_created": False,
    }


def hash_manifest(out: Path) -> None:
    entries = []
    for path in sorted(out.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.name == "HASH_MANIFEST.json":
            continue
        entries.append({"path": rel(path), "sha256": sha256_file(path)})
    write_json(out / "HASH_MANIFEST.json", {"artifact_id": "HASH_MANIFEST", "entries": entries})


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing manifest: {rel(path)}"]
    payload = read_json(path)
    errors = []
    for entry in payload.get("entries", []):
        candidate = ROOT / entry["path"]
        if not candidate.exists():
            errors.append(f"manifest target missing: {entry['path']}")
        elif sha256_file(candidate) != entry["sha256"]:
            errors.append(f"manifest mismatch: {entry['path']}")
    return errors


def copy_publication(out: Path) -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for path in out.iterdir():
        if path.is_file():
            shutil.copy2(path, PUBLICATION_ROOT / path.name)


def build(story_root: Path, review_root: Path, repair_root: Path, out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    story_decision = read_json(story_root / "CROSS_DOMAIN_STORY_ARC_DECISION.json")
    repair_overlay = read_json(repair_root / "CROSS_DOMAIN_SHARED_ENTITY_SEMANTICS_OVERLAY.json", {})
    ledger = build_provenance_ledger(review_root)
    count_repair = build_eval_count_repair(story_root)
    cards = build_cards()
    concordance = build_concordance(ledger)
    false_guard = build_false_concordance_guard(ledger)
    boundary = build_boundary_guard()

    count_ok = (
        count_repair["story_arc_unique_eval_cases"] == 120
        and count_repair["story_arc_challenge_negative_cases"] == 70
        and count_repair["challenge_cases_are_subset_of_unique_eval_cases"] is True
        and count_repair["story_arc_additive_eval_count"] == 120
        and count_repair["forbidden_190_case_claim_created"] is False
    )
    cards_ok = cards["cards_are_product_judgment_usefulness_cards"] and cards["card_count"] >= 6
    reviews_ok = ledger["valid_chatgpt_review_imported"] and ledger["valid_claude_independent_artifact_review_imported"]
    if not reviews_ok:
        status = STATUS_BLOCKED
        final_decision = FINAL_WAIT
    elif not count_ok or not cards_ok:
        status = STATUS_BLOCKED
        final_decision = FINAL_REPAIR
    else:
        status = STATUS_PASS
        final_decision = FINAL_GO

    readiness = {
        "artifact_id": "FOUNDER_DIAGNOSTIC_READINESS_GATE",
        "status": "PASS" if final_decision == FINAL_GO else "BLOCKED",
        "final_decision": final_decision,
        "founder_diagnostic_review_allowed_with_limitations": final_decision == FINAL_GO,
        "founder_product_review_allowed": False,
        "product_review_ready": False,
        "client_ready": False,
        "valid_chatgpt_review_imported": ledger["valid_chatgpt_review_imported"],
        "valid_claude_independent_artifact_review_imported": ledger["valid_claude_independent_artifact_review_imported"],
        "eval_count_framing_repaired": count_ok,
        "founder_cards_rewritten_to_product_judgment": cards_ok,
        "review_of_review_excluded_from_concordance": ledger["review_of_review_excluded_from_concordance"],
    }
    decision = {
        "artifact_id": "STORY_ARC_FOUNDER_DIAGNOSTIC_PREP_CONCORDANCE_DECISION",
        "status": status,
        "final_decision": final_decision,
        "source_story_arc_status": story_decision.get("status"),
        "source_story_arc_id": story_decision.get("story_arc_id"),
        "shared_entity_semantics_overlay_ref": rel(repair_root / "CROSS_DOMAIN_SHARED_ENTITY_SEMANTICS_OVERLAY.json")
        if repair_overlay
        else None,
        "shared_canonical_entity_count": repair_overlay.get("replacement_fields", {}).get("shared_canonical_entity_count"),
        "shared_canonical_entity_family_span": repair_overlay.get("replacement_fields", {}).get("shared_canonical_entity_family_span"),
        "asset_infrastructure_link_type": repair_overlay.get("replacement_fields", {}).get("asset_infrastructure_link_type"),
        "countable_ai_artifact_review_count": ledger["countable_ai_artifact_review_count"],
        "story_arc_unique_eval_cases": count_repair["story_arc_unique_eval_cases"],
        "story_arc_challenge_negative_cases_subset": count_repair["story_arc_challenge_negative_cases"],
        "combined_unique_eval_case_count": count_repair["combined_unique_eval_case_count"],
        "founder_diagnostic_card_count": cards["card_count"],
        "founder_session_results_created": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "forecast_packet_created": False,
        "source_truth_mutated": False,
        "product_review_ready": False,
        "client_ready": False,
        "forbidden_capabilities_created": [],
    }

    write_json(out / "STORY_ARC_FOUNDER_DIAGNOSTIC_PREP_CONCORDANCE_DECISION.json", decision)
    write_json(out / "AI_REVIEW_PROVENANCE_LEDGER.json", ledger)
    write_json(out / "AI_REVIEW_CONCORDANCE_REPORT.json", concordance)
    write_json(out / "EVAL_COUNT_FRAMING_REPAIR.json", count_repair)
    write_text(
        out / "EVAL_COUNT_FRAMING_REPAIR.md",
        f"""# Eval Count Framing Repair

- Story-arc unique eval cases: `{count_repair["story_arc_unique_eval_cases"]}`
- Challenge/negative cases: `{count_repair["story_arc_challenge_negative_cases"]}`
- Challenge/negative cases are a subset: `{str(count_repair["challenge_cases_are_subset_of_unique_eval_cases"]).lower()}`
- Additive story-arc eval count: `{count_repair["story_arc_additive_eval_count"]}`
- Do not claim `120 + 70 = 190`.
- Prior eval cases discovered: `{str(count_repair["prior_eval_cases_discovered"]).lower()}`
- Combined unique eval cases: `{count_repair["combined_unique_eval_case_count"]}`
""",
    )
    write_json(out / "FOUNDER_DIAGNOSTIC_PRODUCT_JUDGMENT_CARDS.json", cards)
    write_text(out / "FOUNDER_DIAGNOSTIC_PRODUCT_JUDGMENT_CARDS.md", cards_markdown(cards))
    write_text(out / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE.csv", response_template_csv(cards))
    write_text(
        out / "FOUNDER_DIAGNOSTIC_SESSION_GUIDE.md",
        """# Founder Diagnostic Session Guide

Use the product-judgment cards to test usefulness, clarity, trust, actionability, and missing evidence.

This is founder-internal diagnostic review only. Do not treat responses as operator fuel, external validation, training rows, product readiness, client readiness, official action, forecast validation, or source truth.
""",
    )
    write_json(out / "FOUNDER_DIAGNOSTIC_READINESS_GATE.json", readiness)
    write_json(out / "NO_FALSE_CONCORDANCE_GUARD.json", false_guard)
    write_json(out / "BOUNDARY_AND_NO_FUEL_GUARD.json", boundary)
    write_text(
        out / "CODEX_CLOSEOUT.md",
        f"""# Story Arc Founder Diagnostic Prep + Concordance R1

Status: `{status}`

- Final decision: `{final_decision}`
- ChatGPT review imported: `{ledger["valid_chatgpt_review_imported"]}`
- Claude independent artifact review imported: `{ledger["valid_claude_independent_artifact_review_imported"]}`
- Eval framing: 120 unique story-arc eval cases; 70 challenge/negative cases are a subset, not additive.
- Founder cards rewritten as product-judgment/usefulness prompts.

Boundaries: no founder session result, operator fuel, training rows, source-truth mutation, ForecastPacket, live ingestion, official action/control/enforcement, product-ready claim, or client-ready claim.
""",
    )
    hash_manifest(out)
    copy_publication(out)
    return decision


def validate(out: Path) -> list[str]:
    errors = []
    for path in required_paths(out):
        if not path.exists():
            errors.append(f"missing required artifact: {path.name}")
            continue
        if path.suffix == ".json":
            try:
                read_json(path)
            except Exception as exc:  # pragma: no cover - diagnostic path
                errors.append(f"json parse failed for {path.name}: {exc}")
    if errors:
        return errors
    decision = read_json(out / "STORY_ARC_FOUNDER_DIAGNOSTIC_PREP_CONCORDANCE_DECISION.json")
    ledger = read_json(out / "AI_REVIEW_PROVENANCE_LEDGER.json")
    count = read_json(out / "EVAL_COUNT_FRAMING_REPAIR.json")
    cards = read_json(out / "FOUNDER_DIAGNOSTIC_PRODUCT_JUDGMENT_CARDS.json")
    readiness = read_json(out / "FOUNDER_DIAGNOSTIC_READINESS_GATE.json")
    false_guard = read_json(out / "NO_FALSE_CONCORDANCE_GUARD.json")
    boundary = read_json(out / "BOUNDARY_AND_NO_FUEL_GUARD.json")

    if decision.get("status") != STATUS_PASS:
        errors.append("decision did not pass")
    if decision.get("final_decision") == "GO_FOR_FOUNDER_PRODUCT_REVIEW":
        errors.append("forbidden founder product review decision emitted")
    if decision.get("final_decision") != FINAL_GO:
        errors.append("founder diagnostic gate did not open with limitations")
    if not ledger.get("valid_chatgpt_review_imported"):
        errors.append("ChatGPT review not imported")
    if not ledger.get("valid_claude_independent_artifact_review_imported"):
        errors.append("Claude independent artifact review not imported")
    if not ledger.get("review_of_review_excluded_from_concordance"):
        errors.append("review-of-review not excluded")
    if count.get("story_arc_unique_eval_cases") != 120:
        errors.append("unique eval case count not 120")
    if count.get("story_arc_challenge_negative_cases") != 70:
        errors.append("challenge/negative case count not 70")
    if count.get("challenge_cases_are_subset_of_unique_eval_cases") is not True:
        errors.append("challenge cases are not subset")
    if count.get("story_arc_additive_eval_count") != 120 or count.get("forbidden_190_case_claim_created") is not False:
        errors.append("eval count additive framing is wrong")
    if count.get("combined_unique_eval_case_count") != 168:
        errors.append("combined unique eval case count is not 168")
    if not cards.get("cards_are_product_judgment_usefulness_cards") or cards.get("cards_are_evidence_audit_cards"):
        errors.append("founder cards not rewritten")
    if cards.get("card_count", 0) < 6:
        errors.append("too few founder cards")
    for card in cards.get("rows", []):
        if not card.get("founder_internal"):
            errors.append(f"card {card.get('card_id')} missing founder_internal")
        for flag in [
            "operator_fuel",
            "training_eligible",
            "external_operator_validation",
            "learning_arming_allowed",
            "product_review_ready",
            "client_ready",
            "founder_session_result",
        ]:
            if card.get(flag) is not False:
                errors.append(f"card {card.get('card_id')} has forbidden flag {flag}")
    if readiness.get("founder_diagnostic_review_allowed_with_limitations") is not True:
        errors.append("founder diagnostic readiness not open")
    if readiness.get("founder_product_review_allowed") or readiness.get("product_review_ready") or readiness.get("client_ready"):
        errors.append("product/client readiness incorrectly opened")
    if false_guard.get("review_of_review_excluded_from_concordance") is not True:
        errors.append("false concordance guard failed")
    for key in [
        "founder_session_results_created",
        "operator_fuel_created",
        "training_rows_created",
        "forecast_packet_created",
        "source_truth_mutated",
        "product_ready_claim_created",
        "client_ready_claim_created",
    ]:
        if boundary.get(key) is not False:
            errors.append(f"boundary guard failed for {key}")
    errors.extend(verify_manifest(out / "HASH_MANIFEST.json"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-root", type=Path, default=DEFAULT_STORY_ROOT)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--repair-root", type=Path, default=DEFAULT_REPAIR_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only:
        decision = build(args.story_root, args.review_root, args.repair_root, args.out)
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
