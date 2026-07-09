#!/usr/bin/env python3
"""Gate founder/operator story selection quality before review rendering."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-STORY-SELECTION-QUALITY-GATE-R1"
PUB = ROOT / "publications" / "epoch4" / "main-citybrain-founder-story-selection-quality-gate-r1"

STATUS_PASS = "PASS_MAIN_CITYBRAIN_FOUNDER_STORY_SELECTION_QUALITY_GATE_R1_WITH_LIMITATIONS"
STATUS_NOT_ENOUGH = "NOT_ENOUGH_FOUNDER_GRADE_STORIES_WITH_LIMITATIONS"

INPUT_ROOTS = {
    "operator_view_rendering": ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-OPERATOR-VIEW-CARD-RENDERING-R1",
    "operator_view_publication": ROOT / "publications" / "epoch4" / "main-citybrain-founder-operator-view-card-rendering-r1",
    "evidence_inline_repair": ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-CARD-EVIDENCE-INLINING-REPAIR-R1",
    "story_batch_discovery": ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-READABLE-STORY-BATCH-DISCOVERY-HTML-R1",
    "cross_domain_story_arc": ROOT / "outputs" / "MAIN-CITYBRAIN-CROSS-DOMAIN-STORY-ARC-EVAL-EXPANSION-R1",
    "review_quality_cards": ROOT / "outputs" / "main_citybrain_epoch4_review_pack_quality_upgrade_r4_r1",
    "seed_r3_adapter_corpus": ROOT / "outputs" / "MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1",
    "expanded_cadence": ROOT / "outputs" / "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-EXPANDED-CORPUS-CADENCE-REPLAY-MINING-R2",
    "mobility_native_repair": ROOT / "outputs" / "MAIN-CITYBRAIN-REVIEW-PACKET-360-MOBILITY-NATIVE-REPAIR-R1",
}

REQUIRED = [
    "FOUNDER_STORY_SELECTION_QUALITY_GATE_DECISION.json",
    "FOUNDER_STORY_SELECTION_QUALITY_MATRIX.json",
    "FOUNDER_STORY_SELECTION_LEDGER.json",
    "FOUNDER_REVIEWABLE_MAIN_SET.json",
    "DIAGNOSTIC_APPENDIX_CARDS.json",
    "FOUNDER_STORY_CLASSIFICATION_COUNTS.json",
    "FOUNDER_STORY_SELECTION_QUALITY_GATE_REPORT.md",
    "FOUNDER_STORY_SELECTION_QUALITY_GATE_REPORT.html",
    "SOURCE_DISCOVERY_REPORT.json",
    "QUALITY_GATE_GUARD.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]

CLASSIFICATIONS = [
    "founder_reviewable_watch_candidate",
    "founder_reviewable_need_more_candidate",
    "diagnostic_boundary_case",
    "negative_abstain_case",
    "not_reviewable_due_to_missing_place",
    "not_reviewable_due_to_missing_freshness",
    "not_reviewable_due_to_thin_source_depth",
    "not_reviewable_due_to_no_human_readable_consequence",
]

PASS_BAR = {
    "minimum_main_cards": 10,
    "minimum_watch_or_review_worthy": 5,
    "minimum_cross_domain_cards": 2,
    "minimum_honest_abstain_or_ignore_cards": 2,
    "maximum_need_more_cards_in_main": 3,
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_operator_cards() -> list[dict[str, Any]]:
    payload = read_json(INPUT_ROOTS["operator_view_rendering"] / "FOUNDER_OPERATOR_STORY_CARDS_INLINE.json", {"cards": []})
    return payload.get("cards", [])


def is_unknown(value: str) -> bool:
    return str(value or "").strip().upper().startswith("UNKNOWN")


def freshness_known(card: dict[str, Any]) -> bool:
    return any(not is_unknown(note.get("timestamp_or_freshness", "")) for note in card.get("evidence_snapshot", []))


def place_known(card: dict[str, Any]) -> bool:
    anchor = card.get("place_anchor", {})
    return not is_unknown(anchor.get("human_label", ""))


def has_map_ref(card: dict[str, Any]) -> bool:
    anchor = card.get("place_anchor", {})
    return not is_unknown(anchor.get("map_or_geometry_ref", ""))


def evidence_count(card: dict[str, Any]) -> int:
    return len(card.get("evidence_snapshot", []))


def has_strong_single_source(card: dict[str, Any]) -> bool:
    if evidence_count(card) != 1:
        return False
    note = card["evidence_snapshot"][0]
    source_class = str(note.get("source_class", "")).lower()
    note_text = str(note.get("source_note_text", ""))
    if is_unknown(note.get("timestamp_or_freshness", "")) or is_unknown(note.get("entity_or_place_label", "")):
        return False
    if any(token in source_class for token in ["synthetic", "derived fixture", "scenario"]):
        return False
    return len(note_text.strip()) >= 80


def has_human_consequence(card: dict[str, Any]) -> bool:
    line = str(card.get("so_what_line", "")).strip()
    if not line.startswith("So what:"):
        return False
    generic = "this may be worth triage only if the visible evidence is enough"
    return generic not in line.lower()


def is_diagnostic_fixture(card: dict[str, Any]) -> bool:
    body = json.dumps(card).lower()
    title = str(card.get("verdict_line", "")).lower()
    return any(
        marker in body or marker in title
        for marker in [
            "diagnostic",
            "baseline",
            "no data",
            "no-data",
            "stale",
            "contradiction",
            "synthetic",
            "dirty source",
            "derived fixture",
            "local synthetic",
        ]
    )


def is_honest_abstain(card: dict[str, Any]) -> bool:
    body = json.dumps(card).lower()
    verdict = card.get("operator_verdict_suggestion")
    return verdict == "ignore_for_now" or any(token in body for token in ["ignore for now", "abstain", "no data", "stale", "contradiction"])


def confidence_level(card: dict[str, Any]) -> str:
    return str(card.get("confidence_plain_english", "low")).split(" - ", 1)[0].strip().lower()


def score_card(card: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    verdict = card.get("operator_verdict_suggestion")
    level = confidence_level(card)

    if verdict == "watch_this":
        score += 20
        reasons.append("watch verdict")
    elif verdict == "need_more_before_deciding":
        score += 8
        reasons.append("need-more verdict")
    elif verdict == "ignore_for_now":
        score += 6
        reasons.append("honest ignore verdict")

    if level == "high":
        score += 25
        reasons.append("high confidence")
    elif level == "medium":
        score += 15
        reasons.append("medium confidence")
    else:
        score -= 15
        reasons.append("low confidence")

    if place_known(card):
        score += 15
        reasons.append("human-readable place")
    else:
        score -= 30
        reasons.append("missing human-readable place")

    if has_map_ref(card):
        score += 8
        reasons.append("map or geometry ref present")
    else:
        score -= 8
        reasons.append("map or geometry ref missing")

    if freshness_known(card):
        score += 15
        reasons.append("freshness or timestamp visible")
    else:
        score -= 25
        reasons.append("freshness missing")

    if evidence_count(card) >= 2:
        score += 20
        reasons.append("two or more evidence notes")
    elif has_strong_single_source(card):
        score += 12
        reasons.append("one strong named source note")
    else:
        score -= 18
        reasons.append("thin source depth")

    if has_human_consequence(card):
        score += 10
        reasons.append("clear so-what")
    else:
        score -= 20
        reasons.append("weak or missing so-what")

    if card.get("suggested_review_next_step"):
        score += 8
        reasons.append("next review step present")
    else:
        score -= 20
        reasons.append("next review step missing")

    if card.get("card_type") == "cross_domain_story":
        score += 10
        reasons.append("cross-domain card")

    if is_diagnostic_fixture(card):
        score -= 18
        reasons.append("diagnostic/challenge fixture")

    return score, reasons


def classify_card(card: dict[str, Any]) -> dict[str, Any]:
    score, reasons = score_card(card)
    level = confidence_level(card)
    verdict = card.get("operator_verdict_suggestion")
    classification = "diagnostic_boundary_case"

    if not place_known(card):
        classification = "not_reviewable_due_to_missing_place"
    elif not freshness_known(card):
        classification = "not_reviewable_due_to_missing_freshness"
    elif not has_human_consequence(card):
        classification = "not_reviewable_due_to_no_human_readable_consequence"
    elif evidence_count(card) < 2 and not has_strong_single_source(card):
        classification = "not_reviewable_due_to_thin_source_depth"
    elif is_honest_abstain(card):
        classification = "negative_abstain_case"
    elif is_diagnostic_fixture(card):
        classification = "diagnostic_boundary_case"
    elif verdict == "watch_this" and level in {"medium", "high"}:
        classification = "founder_reviewable_watch_candidate"
    elif verdict == "need_more_before_deciding" and level in {"medium", "high"}:
        classification = "founder_reviewable_need_more_candidate"

    return {
        "card_id": card.get("card_id"),
        "card_type": card.get("card_type"),
        "title_or_verdict": card.get("verdict_line"),
        "operator_verdict_suggestion": verdict,
        "confidence_level": level,
        "classification": classification,
        "quality_score": score,
        "score_reasons": reasons,
        "founder_grade_criteria": {
            "human_readable_place": place_known(card),
            "map_or_geometry_ref_present": has_map_ref(card),
            "freshness_or_timestamp_present": freshness_known(card),
            "evidence_note_count": evidence_count(card),
            "has_two_notes_or_strong_named_source": evidence_count(card) >= 2 or has_strong_single_source(card),
            "clear_so_what": has_human_consequence(card),
            "clear_next_review_step": bool(card.get("suggested_review_next_step")),
            "plain_confidence_reason": bool(card.get("confidence_plain_english") and " - " in card.get("confidence_plain_english", "")),
            "diagnostic_fixture": is_diagnostic_fixture(card),
        },
    }


def select_main_set(cards: list[dict[str, Any]], matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {card.get("card_id"): card for card in cards}
    allowed = {
        "founder_reviewable_watch_candidate",
        "founder_reviewable_need_more_candidate",
        "negative_abstain_case",
    }
    eligible = [row for row in matrix if row["classification"] in allowed]
    eligible.sort(key=lambda row: row["quality_score"], reverse=True)
    selected = []
    need_more_count = 0
    for row in eligible:
        if row["operator_verdict_suggestion"] == "need_more_before_deciding" and need_more_count >= PASS_BAR["maximum_need_more_cards_in_main"]:
            continue
        selected.append(by_id[row["card_id"]])
        if row["operator_verdict_suggestion"] == "need_more_before_deciding":
            need_more_count += 1
    return selected


def acceptance_metrics(cards: list[dict[str, Any]], matrix: list[dict[str, Any]], selected: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["classification"] for row in matrix)
    selected_ids = {card["card_id"] for card in selected}
    selected_rows = [row for row in matrix if row["card_id"] in selected_ids]
    selected_counts = Counter(row["classification"] for row in selected_rows)
    need_more_in_selected = sum(1 for card in selected if card.get("operator_verdict_suggestion") == "need_more_before_deciding")
    watch_or_review = selected_counts["founder_reviewable_watch_candidate"] + selected_counts["founder_reviewable_need_more_candidate"]
    cross_domain = sum(1 for card in selected if card.get("card_type") == "cross_domain_story")
    honest_abstain = selected_counts["negative_abstain_case"]
    pass_bar_met = (
        len(selected) >= PASS_BAR["minimum_main_cards"]
        and watch_or_review >= PASS_BAR["minimum_watch_or_review_worthy"]
        and cross_domain >= PASS_BAR["minimum_cross_domain_cards"]
        and honest_abstain >= PASS_BAR["minimum_honest_abstain_or_ignore_cards"]
        and need_more_in_selected <= PASS_BAR["maximum_need_more_cards_in_main"]
    )
    blockers = []
    if len(selected) < PASS_BAR["minimum_main_cards"]:
        blockers.append(f"only {len(selected)} founder-grade main candidates; need {PASS_BAR['minimum_main_cards']}")
    if watch_or_review < PASS_BAR["minimum_watch_or_review_worthy"]:
        blockers.append(f"only {watch_or_review} watch/review-worthy candidates; need {PASS_BAR['minimum_watch_or_review_worthy']}")
    if cross_domain < PASS_BAR["minimum_cross_domain_cards"]:
        blockers.append(f"only {cross_domain} cross-domain candidates; need {PASS_BAR['minimum_cross_domain_cards']}")
    if honest_abstain < PASS_BAR["minimum_honest_abstain_or_ignore_cards"]:
        blockers.append(f"only {honest_abstain} honest abstain/ignore candidates; need {PASS_BAR['minimum_honest_abstain_or_ignore_cards']}")
    if need_more_in_selected > PASS_BAR["maximum_need_more_cards_in_main"]:
        blockers.append(f"{need_more_in_selected} need-more cards in main set; max {PASS_BAR['maximum_need_more_cards_in_main']}")
    return {
        "candidate_count": len(cards),
        "classification_counts": dict(counts),
        "selected_main_candidate_count": len(selected),
        "selected_classification_counts": dict(selected_counts),
        "selected_watch_or_review_worthy_count": watch_or_review,
        "selected_cross_domain_count": cross_domain,
        "selected_honest_abstain_or_ignore_count": honest_abstain,
        "selected_need_more_count": need_more_in_selected,
        "pass_bar": PASS_BAR,
        "pass_bar_met": pass_bar_met,
        "blockers": blockers,
    }


def source_discovery(cards: list[dict[str, Any]]) -> dict[str, Any]:
    files = {
        "operator_cards_json": INPUT_ROOTS["operator_view_rendering"] / "FOUNDER_OPERATOR_STORY_CARDS_INLINE.json",
        "evidence_inline_index": INPUT_ROOTS["evidence_inline_repair"] / "FOUNDER_CARD_EVIDENCE_INLINE_INDEX.json",
        "story_batch_index": INPUT_ROOTS["story_batch_discovery"] / "FOUNDER_STORY_BATCH_INDEX.json",
        "cross_domain_events": INPUT_ROOTS["cross_domain_story_arc"] / "CROSS_DOMAIN_STORY_ARC_EVENTS.jsonl",
        "seed_r3_feed": INPUT_ROOTS["seed_r3_adapter_corpus"] / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl",
    }
    return {
        "artifact_id": "SOURCE_DISCOVERY_REPORT",
        "input_roots": [{"key": key, "path": rel(path), "exists": path.exists()} for key, path in INPUT_ROOTS.items()],
        "key_files": [{"key": key, "path": rel(path), "exists": path.exists()} for key, path in files.items()],
        "candidate_cards_loaded_from": rel(files["operator_cards_json"]),
        "candidate_cards_loaded": len(cards),
        "scan_scope_note": "Gate uses existing rendered operator cards as candidates and records upstream story/card roots for provenance; it does not fabricate or repair source material.",
    }


def render_report_md(decision: dict[str, Any], metrics: dict[str, Any]) -> str:
    lines = [
        "# Founder Story Selection Quality Gate R1",
        "",
        f"Status: `{decision['status']}`",
        "",
        "## Result",
        "",
        "Do not run founder review on the current batch unless this gate passes.",
        "",
        "## Acceptance Bar",
        "",
    ]
    for key, value in PASS_BAR.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Metrics", ""])
    for key in [
        "candidate_count",
        "selected_main_candidate_count",
        "selected_watch_or_review_worthy_count",
        "selected_cross_domain_count",
        "selected_honest_abstain_or_ignore_count",
        "selected_need_more_count",
    ]:
        lines.append(f"- {key}: `{metrics[key]}`")
    lines.extend(["", "## Blockers", ""])
    if metrics["blockers"]:
        lines.extend(f"- {item}" for item in metrics["blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Classification Counts", ""])
    for key in CLASSIFICATIONS:
        lines.append(f"- {key}: `{metrics['classification_counts'].get(key, 0)}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This gate only classifies and selects candidate cards. It does not run founder review, create fuel/training rows, mutate source truth, or claim product/client readiness.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_report_html(decision: dict[str, Any], metrics: dict[str, Any], matrix: list[dict[str, Any]]) -> str:
    rows = []
    for row in sorted(matrix, key=lambda item: item["quality_score"], reverse=True):
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['card_id']))}</td>"
            f"<td>{html.escape(row['classification'])}</td>"
            f"<td>{row['quality_score']}</td>"
            f"<td>{html.escape(str(row['operator_verdict_suggestion']))}</td>"
            f"<td>{html.escape(str(row['confidence_level']))}</td>"
            f"<td>{html.escape('; '.join(row['score_reasons']))}</td>"
            "</tr>"
        )
    blockers = "".join(f"<li>{html.escape(item)}</li>" for item in metrics["blockers"]) or "<li>none</li>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Founder Story Selection Quality Gate</title>
<style>
body{{font-family:Arial,sans-serif;margin:0;background:#f6f7fb;color:#1f2937;line-height:1.45}}
main{{max-width:1180px;margin:0 auto;padding:28px}}
.hero{{background:#fff;border:1px solid #d9e1ec;border-radius:8px;padding:22px;margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;background:#fff;border:1px solid #d9e1ec}}
th,td{{text-align:left;vertical-align:top;border-bottom:1px solid #e5ebf2;padding:8px}}
th{{background:#edf2f7}}
.status{{font-weight:bold}}
</style>
</head>
<body><main>
<section class="hero">
<h1>Founder Story Selection Quality Gate</h1>
<p class="status">Status: {html.escape(decision['status'])}</p>
<p>Do not run founder review on the current batch unless this gate passes.</p>
<p>Main candidates selected: {metrics['selected_main_candidate_count']} / required {PASS_BAR['minimum_main_cards']}.</p>
<h2>Blockers</h2><ul>{blockers}</ul>
</section>
<table>
<thead><tr><th>Card</th><th>Classification</th><th>Score</th><th>Verdict</th><th>Confidence</th><th>Reasons</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</main></body></html>
"""


def hash_manifest(out: Path) -> None:
    entries = []
    for path in sorted(out.iterdir(), key=lambda item: item.name):
        if path.name == "HASH_MANIFEST.json" or not path.is_file():
            continue
        entries.append({"path": rel(path), "sha256": sha256_file(path)})
    write_json(out / "HASH_MANIFEST.json", {"artifact_id": "HASH_MANIFEST", "entries": entries})


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing manifest: {rel(path)}"]
    errors = []
    payload = read_json(path)
    for entry in payload.get("entries", []):
        target = ROOT / entry["path"]
        if not target.exists():
            errors.append(f"manifest target missing: {entry['path']}")
        elif sha256_file(target) != entry["sha256"]:
            errors.append(f"manifest mismatch: {entry['path']}")
    return errors


def copy_publication(out: Path) -> None:
    PUB.mkdir(parents=True, exist_ok=True)
    for path in out.iterdir():
        if path.is_file():
            shutil.copy2(path, PUB / path.name)


def build(out: Path = OUT) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    cards = load_operator_cards()
    matrix = [classify_card(card) for card in cards]
    selected = select_main_set(cards, matrix)
    selected_ids = {card["card_id"] for card in selected}
    diagnostic = [card for card in cards if card["card_id"] not in selected_ids]
    metrics = acceptance_metrics(cards, matrix, selected)
    status = STATUS_PASS if metrics["pass_bar_met"] else STATUS_NOT_ENOUGH
    decision = {
        "artifact_id": "FOUNDER_STORY_SELECTION_QUALITY_GATE_DECISION",
        "task_id": "MAIN-CITYBRAIN-FOUNDER-STORY-SELECTION-QUALITY-GATE-R1",
        "status": status,
        "founder_review_allowed": status == STATUS_PASS,
        "operator_rendering_allowed_for_founder_batch": status == STATUS_PASS,
        "do_not_run_founder_review_on_current_batch": status != STATUS_PASS,
        "metrics": metrics,
        "next_recommended_task": "SOURCE_OR_STORY_EXPANSION_BEFORE_FOUNDER_REVIEW"
        if status != STATUS_PASS
        else "RENDER_FOUNDER_BATCH_FROM_SELECTED_MAIN_SET",
    }
    ledger = {
        "artifact_id": "FOUNDER_STORY_SELECTION_LEDGER",
        "selection_policy": "Select founder-grade candidates only; move diagnostic, challenge, thin, unknown-place, and unknown-freshness cards to appendix.",
        "selected_main_card_ids": sorted(selected_ids),
        "diagnostic_appendix_card_ids": sorted(card["card_id"] for card in diagnostic),
    }
    guard = {
        "artifact_id": "QUALITY_GATE_GUARD",
        "status": "PASS",
        "founder_review_executed": False,
        "founder_session_result_created": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "source_truth_mutated": False,
        "forecast_packet_created": False,
        "product_review_ready_claim": False,
        "client_ready_claim": False,
        "official_action_created": False,
        "weak_cards_moved_to_appendix": True,
        "main_set_padded_with_weak_cards": False,
    }
    write_json(out / "FOUNDER_STORY_SELECTION_QUALITY_GATE_DECISION.json", decision)
    write_json(out / "FOUNDER_STORY_SELECTION_QUALITY_MATRIX.json", {"artifact_id": "FOUNDER_STORY_SELECTION_QUALITY_MATRIX", "rows": matrix})
    write_json(out / "FOUNDER_STORY_SELECTION_LEDGER.json", ledger)
    write_json(out / "FOUNDER_REVIEWABLE_MAIN_SET.json", {"artifact_id": "FOUNDER_REVIEWABLE_MAIN_SET", "status": status, "cards": selected})
    write_json(out / "DIAGNOSTIC_APPENDIX_CARDS.json", {"artifact_id": "DIAGNOSTIC_APPENDIX_CARDS", "cards": diagnostic})
    write_json(out / "FOUNDER_STORY_CLASSIFICATION_COUNTS.json", {"artifact_id": "FOUNDER_STORY_CLASSIFICATION_COUNTS", **metrics})
    write_json(out / "SOURCE_DISCOVERY_REPORT.json", source_discovery(cards))
    write_json(out / "QUALITY_GATE_GUARD.json", guard)
    write_text(out / "FOUNDER_STORY_SELECTION_QUALITY_GATE_REPORT.md", render_report_md(decision, metrics))
    write_text(out / "FOUNDER_STORY_SELECTION_QUALITY_GATE_REPORT.html", render_report_html(decision, metrics, matrix))
    write_text(
        out / "CODEX_CLOSEOUT.md",
        f"""# Founder Story Selection Quality Gate R1

Status: `{status}`

- Candidate cards scanned: `{metrics['candidate_count']}`
- Founder-grade main candidates selected: `{metrics['selected_main_candidate_count']}`
- Watch/review-worthy selected: `{metrics['selected_watch_or_review_worthy_count']}`
- Cross-domain selected: `{metrics['selected_cross_domain_count']}`
- Honest abstain/ignore selected: `{metrics['selected_honest_abstain_or_ignore_count']}`
- Need-more selected: `{metrics['selected_need_more_count']}`

Blockers:
{chr(10).join('- ' + item for item in metrics['blockers']) if metrics['blockers'] else '- none'}

Boundaries: classification and selection gate only; no founder review, no session result, no fuel/training rows, no source-truth mutation, no ForecastPacket, no official action/control/enforcement, and no product/client-ready claim.
""",
    )
    hash_manifest(out)
    copy_publication(out)
    return decision


def validate(out: Path = OUT) -> list[str]:
    errors = []
    for name in REQUIRED:
        path = out / name
        if not path.exists():
            errors.append(f"missing required output: {name}")
        elif path.suffix == ".json":
            try:
                read_json(path)
            except Exception as exc:  # pragma: no cover
                errors.append(f"json parse failed for {name}: {exc}")
    if errors:
        return errors
    decision = read_json(out / "FOUNDER_STORY_SELECTION_QUALITY_GATE_DECISION.json")
    matrix = read_json(out / "FOUNDER_STORY_SELECTION_QUALITY_MATRIX.json")
    main = read_json(out / "FOUNDER_REVIEWABLE_MAIN_SET.json")
    appendix = read_json(out / "DIAGNOSTIC_APPENDIX_CARDS.json")
    counts = read_json(out / "FOUNDER_STORY_CLASSIFICATION_COUNTS.json")
    guard = read_json(out / "QUALITY_GATE_GUARD.json")

    rows = matrix.get("rows", [])
    if not rows:
        errors.append("no candidate cards were classified")
    bad_classes = [row["classification"] for row in rows if row["classification"] not in CLASSIFICATIONS]
    if bad_classes:
        errors.append(f"unknown classification labels: {bad_classes}")
    if decision["status"] == STATUS_PASS and not counts.get("pass_bar_met"):
        errors.append("PASS status without pass bar met")
    if decision["status"] == STATUS_NOT_ENOUGH and counts.get("pass_bar_met"):
        errors.append("NOT_ENOUGH status even though pass bar was met")
    if decision["status"] == STATUS_NOT_ENOUGH and not decision.get("do_not_run_founder_review_on_current_batch"):
        errors.append("not-enough status did not block founder review")
    if decision["status"] == STATUS_PASS and len(main.get("cards", [])) < PASS_BAR["minimum_main_cards"]:
        errors.append("PASS with too few main cards")
    if len(main.get("cards", [])) + len(appendix.get("cards", [])) != len(rows):
        errors.append("main plus appendix count does not equal classified rows")
    if not counts.get("blockers") and decision["status"] == STATUS_NOT_ENOUGH:
        errors.append("not-enough status without blockers")
    for key, value in {
        "founder_review_executed": False,
        "founder_session_result_created": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "source_truth_mutated": False,
        "forecast_packet_created": False,
        "product_review_ready_claim": False,
        "client_ready_claim": False,
        "official_action_created": False,
        "main_set_padded_with_weak_cards": False,
    }.items():
        if guard.get(key) is not value:
            errors.append(f"guard mismatch for {key}")
    if not (PUB / "FOUNDER_STORY_SELECTION_QUALITY_GATE_REPORT.html").exists():
        errors.append("publication report missing")
    errors.extend(verify_manifest(out / "HASH_MANIFEST.json"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only:
        decision = build(args.out)
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
